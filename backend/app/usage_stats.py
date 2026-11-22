# 관리자 이용 통계 — 포털 안 원장(접속 · 감사 · 계정 · 대화 · 절차/루틴 · PAT)을 읽기 전용으로 열어 읽을 때 센다(docs/ops-dashboard M1)
"""M1 은 새로 적지 않는다. 이미 있는 원장을 기간(KST 날)으로 잘라 센다 — 날마다 접어 두는 표는 M2 다(PLAN §2.4).

규칙.
  · 원장은 설정의 경로로만 찾고 읽기 전용(mode=ro)으로 연다. 쓰는 저장소의 연결 · 잠금을 쥐지 않는다(seat_review_harvest 와 같은 길).
    부르는 쪽(라우트)이 이벤트 루프 밖(스레드)에서 부른다.
  · 날은 KST(UTC+9 — 서머타임이 없어 고정 오프셋이 정확하다)로 가르고, 주는 월요일에 시작한다. 기간은 오늘을 끝으로 한 N 일이고
    N 은 1 ~ 400(기본 30)으로 붙잡아 맞춘다. 감사 · 접속 · 대화 · 실행 · 요청 읽기는 모두 그 기간으로 자른다(ts 색인).
    지금 상태를 세는 칸(계정 상태 · 소속 · 살아 있는 PAT · 연결)은 작은 표를 통째로 보고, 기간과 무관하다고 note 가 말한다.
  · 자동 SSO 예열(access_log detail=primer — 45분마다 저절로 쌓인다)은 늘 빼고, 설정 USAGE_EXCLUDE_ACCOUNTS 의 계정(시험 · 서비스)도 뺀다.
  · 싣지 않는 것 — IP · UA · 연결 ID · 질의 · 메시지 글 · 감사 meta 의 글(상류 사유 · 예외) · 부서 · 부서 코드. 챗 오류는 정해진 까닭 코드만 센다.
  · 칸마다 {rows, note}. note 는 그 수를 읽는 법(기록 틈 · 로그인 기준 · PAT 삭제)을 말한다. 원장 하나를 못 읽어도 다른 칸은 낸다(error).
  · 원장의 첫 줄보다 앞선 날은 null 이다(기록 전 — 0 이 아니다).

M2 — 날마다 접어 둔 표(usage_daily · usage_actor_daily — app/usage_fold.py 가 감사 원장 파일 안에 쓴다)에서 읽는 칸이 더해졌다. 원천을 가로지른
쓴 사람(DAU · WAU · MAU) · MCP 도구 호출 · MCP 심의 잡 · RA 초안 · 정문 요청 · 날마다 찍은 PAT 수 · 접기 상태다. 접은 표가 아직 없으면 그 칸은
pending 이고, 원천의 첫 날보다 앞선 날은 여기서도 null 이다. 사람 줄(usage_actor_daily)의 뺄 계정은 읽을 때 빼고, 합계 줄은 접을 때의 목록이다.
"""
import hashlib
import json
import re
import sqlite3
import statistics
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import ExitStack, closing
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.config import Settings

KST = timezone(timedelta(hours=9))
_OFF = 9 * 3600
DEFAULT_DAYS = 30
MAX_DAYS = 400
K_MIN = 5                       # 계정이 이보다 적은 소속 칸은 '기타'로 접는다(PLAN §2.3 · OD-4 가 남긴 기본값)
SETTING = "USAGE_EXCLUDE_ACCOUNTS"
_CHAT_IN = "('chat_start', 'chat_done', 'chat_error')"     # 챗 턴의 사건 셋(SQL 글자)
_REASON = re.compile(r"[a-z0-9_]{1,40}")          # 챗 오류 까닭 — 코드가 적는 정해진 낱말만. 그 밖은 unknown
# 감사 사건의 갈래 — 이름 머리로 가른다. 앞이 먼저다(docx_report 는 docx).
FAMILIES = (("upload", ("upload_", "pc_")), ("deck", ("deck_",)), ("wiki", ("wiki_",)),
            ("card_review", ("card_review_",)), ("docx", ("docx",)), ("panel", ("panel_",)), ("delib", ("delib_",)))
_PROC_OPEN = ("queued", "running", "gated")         # 절차 실행 — 아직 끝나지 않은 상태(완주율의 분모에서 뺀다)
_ROUTINE_OPEN = ("queued", "running", "waiting")    # 루틴 실행 — interrupted 는 원장이 끝난 시각을 적는 쪽이라 끝난 것으로 센다
# 접속 원장의 기간 · 예열 거르기(audit.query_access 의 include_auto=False 와 같은 조건)
_ACCESS = "ts >= ? AND ts < ? AND (detail IS NULL OR detail != 'primer')"
# ── 접어 둔 표(M2) — 접는 쪽(app/usage_fold.py)과 함께 쓰는 값 ──
FOLD_SOURCES = (("portal", "포털 원장(사람 줄 · 새 대화 · 낸 PAT)"), ("snapshot", "지금 상태(오늘의 PAT · 연결 · 계정 · 허가)"), ("nginx", "정문 접근 로그"),
                ("gateway", "게이트웨이(MCP 도구 호출)"), ("agent", "에이전트 서버(MCP 심의 잡 · LLM 토큰)"))
FOLD_NOCOVER = "nocover"                    # 정문 로그가 그날을 덮지 않는다 — 접은 기록만 있고 값은 없다(기록 전과 같다)
RA_DRAFT_TOOL = "create_report_draft"       # Report Archive 초안을 만드는 도구의 원래 이름 — 성공 호출이 RA 초안 하나다
# 지연 칸의 위 끝(ms) — 게이트웨이 usage_rollup.LAT_LE_MS 와 같다(접는 쪽이 창구의 rules.lat_le_ms 와 견주고 시험이 형제 리포와 견준다)
LAT_LE_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000, 120000, 300000, 600000)
TOP_TOOLS = 30
# 사람 줄의 갈래 — engine 은 호출자가 빈 엔진 호출을 그 일의 사람에게 이은 것(감사 전용 머리 — 검증하지 않은 주장, OD-52)
_ACTOR_GROUPS = ("login", "chat", "tile", "mcp", "engine", "delib", "nginx")
PEOPLE_MAX = 1000               # 사람별 표의 줄 상한 — 넘으면 truncated
LLM_KINDS = ("chat", "think", "delib", "routine", "card_review", "other")
_FOLD_PENDING = ("아직 접은 적이 없다 — 포털이 뜬 뒤 첫 접기가 돌면 채워진다(기동 30초 뒤 · 그 뒤 USAGE_FOLD_S 초마다 — 0 이면 접지 않는다).")


def _day(col: str) -> str:
    return f"date({col} + {_OFF}, 'unixepoch')"


def _week(col: str) -> str:
    """그 주의 월요일(KST) — 'weekday 0' 은 그날이나 다음 일요일로, 거기서 엿새 앞이 월요일이다."""
    return f"date({col} + {_OFF}, 'unixepoch', 'weekday 0', '-6 days')"


def _month(col: str) -> str:
    return f"strftime('%Y-%m', {col} + {_OFF}, 'unixepoch')"


def kst_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, KST).date().isoformat()


def clamp_days(days: int) -> int:
    return max(1, min(int(days), MAX_DAYS))


@dataclass(frozen=True)
class Window:
    """오늘(KST)을 끝으로 한 N 일. since 는 첫날 KST 자정(포함), until 은 지금 + 1초(제외)."""
    days: int
    first: date
    last: date
    since: int
    until: int

    @classmethod
    def of(cls, days: int, now: float) -> "Window":
        last = datetime.fromtimestamp(now, KST).date()
        first = last - timedelta(days=days - 1)
        since = int(datetime(first.year, first.month, first.day, tzinfo=KST).timestamp())
        return cls(days, first, last, since, int(now) + 1)

    def axis(self) -> list[str]:
        return [(self.first + timedelta(days=i)).isoformat() for i in range(self.days)]

    def weeks(self) -> list[tuple[str, date, date]]:
        start, out = self.first - timedelta(days=self.first.weekday()), []
        while start <= self.last:
            out.append((start.isoformat(), start, start + timedelta(days=6)))
            start += timedelta(days=7)
        return out

    def months(self) -> list[tuple[str, date, date]]:
        start, out = self.first.replace(day=1), []
        while start <= self.last:
            nxt = (start + timedelta(days=32)).replace(day=1)
            out.append((start.strftime("%Y-%m"), start, nxt - timedelta(days=1)))
            start = nxt
        return out


@dataclass
class _Ctx:
    w: Window
    now: int
    ex: list[str]
    labels: dict = field(default_factory=dict)
    refresh_h: int = 8
    memo: dict = field(default_factory=dict)        # 접어 둔 표에서 읽은 줄 — 칸 여럿이 같은 줄을 쓴다(한 번만 읽는다)


def excluded_accounts(settings: Settings) -> list[str]:
    raw = getattr(settings, "usage_exclude_accounts", "") or ""
    return sorted({a.strip().lower() for a in raw.split(",") if a.strip()})


def fingerprint(ex: list[str]) -> str:
    """뺄 계정 목록의 지문 — 접은 날이 어느 목록으로 셌는지(목록이 없으면 빈 글자)."""
    return hashlib.sha1(",".join(sorted(ex)).encode("utf-8")).hexdigest()[:12] if ex else ""


def _not_in(ex: list[str], *cols: str) -> tuple[str, list[str]]:
    """빼는 계정 조건 — 칸마다 소문자로 견준다(NULL 칸은 빈 글자로 — NOT IN 이 NULL 줄까지 버리지 않게)."""
    if not ex:
        return "", []
    marks = ",".join("?" * len(ex))
    return "".join(f" AND lower(COALESCE({c}, '')) NOT IN ({marks})" for c in cols), [a for _ in cols for a in ex]


def _first_day(c: sqlite3.Connection, table: str, col: str = "ts") -> str | None:
    v = c.execute(f"SELECT MIN({col}) FROM {table}").fetchone()[0]  # noqa: S608 — 표 · 칸 이름은 이 파일의 고정 글자
    return kst_day(v) if v is not None else None


def _buckets(spans: list[tuple[str, date, date]], w: Window, first: str | None, got: dict) -> list[dict]:
    """주 · 달 칸 — 기록 전 칸은 None(partial 은 값이 있는 칸에만 — 거짓), 기간 앞뒤에 걸치거나 아직 끝나지 않았거나 기록이 그 칸
    중간에 시작했으면 partial."""
    f = date.fromisoformat(first) if first else None
    out = []
    for key, start, end in spans:
        if f is None or end < f:
            out.append({"key": key, "value": None, "partial": False})
            continue
        partial = start < w.first or end >= w.last or start < f
        out.append({"key": key, "value": got.get(key, 0), "partial": partial})
    return out


# ── 계정(users) ──────────────────────────────────────────────────────────────────────────────────────────
def _accounts_status(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    rows = c.execute(f"SELECT status, COUNT(*) FROM users WHERE 1=1{q} GROUP BY status", a).fetchall()
    order = {"active": 0, "pending": 1, "disabled": 2}
    out = sorted(({"status": s, "n": n} for s, n in rows), key=lambda r: (order.get(r["status"], 9), r["status"]))
    return {"rows": out, "note": "지금 상태다(기간과 무관). active 는 쓰는 계정, pending 은 승인을 기다리는 가입, disabled 는 정지다."}


def _accounts_affiliation(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    rows = c.execute(f"SELECT affiliation, COUNT(*), SUM(status = 'active') FROM users WHERE 1=1{q} GROUP BY affiliation",
                     a).fetchall()
    labels = x.labels.get("affiliation") or {}
    keep, other, folded = [], {"n": 0, "active": 0}, 0
    for aff, n, active in rows:
        if n < K_MIN:
            other["n"] += n
            other["active"] += active or 0
            folded += 1
            continue
        keep.append({"affiliation": aff, "label": labels.get(aff, aff) if aff else "(소속 없음)", "n": n, "active": active or 0})
    keep.sort(key=lambda r: (-r["n"], r["label"]))
    if folded:
        keep.append({"affiliation": None, "label": "기타", "n": other["n"], "active": other["active"], "folded": folded})
    return {"rows": keep, "k": K_MIN,
            "note": f"지금 소속이다(기간과 무관 · 관리자가 정한 소속 — 부서 칸 · 부서 코드는 싣지 않는다). 계정이 {K_MIN}명 미만인 칸은 "
                    f"'기타'로 접었다(k = {K_MIN} — 소속 없음도 같은 규칙). active 는 그중 쓰는 계정이다."}


def _accounts_new(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    got = dict(c.execute(f"SELECT {_week('created_at')} k, COUNT(*) FROM users WHERE created_at >= ? AND created_at < ?{q} "
                         "GROUP BY k", (x.w.since, x.w.until, *a)).fetchall())
    rows = [{"week": b["key"], "n": b["value"], "partial": b["partial"]}
            for b in _buckets(x.w.weeks(), x.w, x.w.first.isoformat(), got)]
    return {"rows": rows,
            "note": "원장에 계정 행이 처음 생긴 주다(로컬은 가입, SSO 는 첫 로그인). 주는 월요일에 시작한다(KST) — 기간 앞뒤에 걸치거나 "
                    "아직 끝나지 않은 주는 partial 이다."}


# ── 로그인 · 타일 진입(access_log) ─────────────────────────────────────────────────────────────────────────
def _logins_daily(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    args = (x.w.since, x.w.until, *a)
    cols = ("SUM(event = 'login'), SUM(event = 'login_fail'), COUNT(DISTINCT CASE WHEN event = 'login' THEN email END),"
            " SUM(event = 'login' AND detail LIKE 'sso%'), SUM(event = 'login' AND detail LIKE 'local%')")
    where = f"FROM access_log WHERE {_ACCESS} AND event IN ('login', 'login_fail'){q}"
    got = {r[0]: r[1:] for r in c.execute(f"SELECT {_day('ts')} d, {cols} {where} GROUP BY d", args)}
    first = _first_day(c, "access_log")
    keys = ("logins", "failures", "accounts", "sso", "local")
    rows = []
    for d in x.w.axis():
        if first is None or d < first:
            rows.append({"day": d, **dict.fromkeys(keys)})
        else:
            rows.append({"day": d, **dict(zip(keys, got.get(d, (0,) * 5), strict=True))})
    t = c.execute(f"SELECT {cols} {where}", args).fetchone()
    return {"rows": rows, "first_day": first,
            "totals": {"logins": t[0] or 0, "failures": t[1] or 0, "accounts": t[2] or 0, "sso": t[3] or 0, "local": t[4] or 0},
            "note": f"로그인 기준이다 — 쓰는 동안 세션이 저절로 이어져(쉬는 상한 {x.refresh_h}시간) 며칠씩 다시 로그인하지 않는 사람이 있고, "
                    "PAT · 개인 Claude 로만 쓴 사람은 빠진다. 그래서 실제로 쓴 사람보다 적게 센다. accounts 는 그날 로그인한 서로 다른 "
                    "계정(DAU)이다. 로그인 실패의 계정은 시도한 이메일이다(주장일 뿐). 자동 SSO 예열은 뺐다. "
                    + (f"원장의 첫 줄({first}) 전 날은 기록이 없다(null)." if first else "원장에 줄이 없다.")}


def _logins_span(c: sqlite3.Connection, x: _Ctx, unit: str) -> dict:
    q, a = _not_in(x.ex, "email")
    expr, spans = (_week("ts"), x.w.weeks()) if unit == "week" else (_month("ts"), x.w.months())
    got = dict(c.execute(f"SELECT {expr} k, COUNT(DISTINCT email) FROM access_log WHERE {_ACCESS} AND event = 'login'{q} "
                         "GROUP BY k", (x.w.since, x.w.until, *a)).fetchall())
    rows = [{unit: b["key"], "accounts": b["value"], "partial": b["partial"]}
            for b in _buckets(spans, x.w, _first_day(c, "access_log"), got)]
    what = "주(월요일에 시작)" if unit == "week" else "달"
    return {"rows": rows,
            "note": f"같은 {what}에 로그인한 서로 다른 계정이다({'WAU' if unit == 'week' else 'MAU'} — 로그인 기준). 기간 앞뒤에 걸치거나 "
                    "아직 끝나지 않았거나 원장이 그 중간에 시작한 칸은 partial 이고, 원장 전 칸은 null 이다."}


def _logins_method(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    m = "CASE WHEN detail LIKE 'sso%' THEN 'sso' WHEN detail LIKE 'local%' THEN 'local' ELSE 'other' END"
    rows = c.execute(f"SELECT {m} m, SUM(event = 'login'), SUM(event = 'login_fail'),"
                     " COUNT(DISTINCT CASE WHEN event = 'login' THEN email END)"
                     f" FROM access_log WHERE {_ACCESS} AND event IN ('login', 'login_fail'){q} GROUP BY m",
                     (x.w.since, x.w.until, *a)).fetchall()
    order = {"sso": 0, "local": 1, "other": 2}
    out = sorted(({"method": k, "logins": lg, "failures": fl, "accounts": ac} for k, lg, fl, ac in rows),
                 key=lambda r: order[r["method"]])
    return {"rows": out, "note": "로그인 줄의 수단(sso · local)으로 가른다. 둘 다 아닌 줄은 other 다."}


def _tiles(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    args = (x.w.since, x.w.until, *a)
    where = f"FROM access_log WHERE {_ACCESS} AND event IN ('launch', 'open'){q}"
    per_day = c.execute(f"SELECT COALESCE(service, ''), {_day('ts')} d, COUNT(*), COUNT(DISTINCT email) {where} GROUP BY 1, d",
                        args).fetchall()
    per_svc = c.execute(f"SELECT COALESCE(service, ''), COUNT(*), COUNT(DISTINCT email), SUM(event = 'launch'), SUM(event = 'open') "
                        f"{where} GROUP BY 1", args).fetchall()
    total = c.execute(f"SELECT COUNT(*), COUNT(DISTINCT email) {where}", args).fetchone()
    first = _first_day(c, "access_log")
    axis = x.w.axis()
    labels = x.labels.get("service") or {}
    daily: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
    for svc, d, n, acc in per_day:
        daily[svc][d] = (n, acc)
    rows = []
    for svc, n, acc, launch, opened in per_svc:
        by = daily[svc]
        rows.append({"service": svc, "label": labels.get(svc, svc), "entries": n, "accounts": acc, "launch": launch, "open": opened,
                     "daily": [None if first is None or d < first else by.get(d, (0, 0))[0] for d in axis],
                     "daily_accounts": [None if first is None or d < first else by.get(d, (0, 0))[1] for d in axis]})
    rows.sort(key=lambda r: (-r["entries"], r["service"]))
    return {"rows": rows, "first_day": first, "totals": {"entries": total[0] or 0, "accounts": total[1] or 0},
            "note": "타일로 서비스에 들어간 수다 — launch 는 포털이 진입 토큰을 낸 것(하위 서비스가 받았는지는 모른다), open 은 프록시 · "
                    "외부 타일을 누른 것. 서비스 안에서 다시 들어간 것 · 허브 앱 열기 · 주소로 바로 간 것은 없다. daily 는 기간의 날마다다. "
                    "자동 SSO 예열은 뺐다."}


# ── 포털 사건(agent_audit) ──────────────────────────────────────────────────────────────────────────────────
def _chat_daily(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "principal")
    args = (x.w.since, x.w.until, *a)
    cols = ("SUM(event = 'chat_start'), SUM(event = 'chat_done'), SUM(event = 'chat_error'),"
            " COUNT(DISTINCT CASE WHEN event = 'chat_start' THEN lower(principal) END)")
    where = f"FROM agent_audit WHERE ts >= ? AND ts < ? AND event IN {_CHAT_IN}{q}"
    got = {r[0]: r[1:] for r in c.execute(f"SELECT {_day('ts')} d, {cols} {where} GROUP BY d", args)}
    first = _first_day(c, "agent_audit")
    keys = ("turns", "done", "errors", "chatters")
    rows = [{"day": d, **(dict.fromkeys(keys) if first is None or d < first else dict(zip(keys, got.get(d, (0,) * 4), strict=True)))}
            for d in x.w.axis()]
    t = c.execute(f"SELECT {cols} {where}", args).fetchone()
    return {"rows": rows, "first_day": first, "totals": dict(zip(keys, (v or 0 for v in t), strict=True)),
            "note": "포털 챗 턴이다(웹 · PAT — 시작 줄). 챗 · 심의 · 띵킹 · 루틴을 함께 센다(종류는 아래 '턴 종류' 칸). done 은 끝까지 "
                    "간 턴, errors 는 오류로 끝난 턴이다(동시 상한 거절은 시작 줄 없이 오류만 남는다). chatters 는 그날 턴을 시작한 서로 다른 "
                    "계정이다. " + (f"원장의 첫 줄({first}) 전 날은 null 이다." if first else "원장에 줄이 없다.")}


def _chat_errors(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "principal")
    rows = c.execute("SELECT CASE WHEN json_valid(meta) THEN json_extract(meta, '$.reason') END,"
                     " CASE WHEN json_valid(meta) THEN json_extract(meta, '$.upstream') END, COUNT(*)"
                     f" FROM agent_audit WHERE ts >= ? AND ts < ? AND event = 'chat_error'{q} GROUP BY 1, 2",
                     (x.w.since, x.w.until, *a)).fetchall()
    counts: dict[str, int] = defaultdict(int)
    for reason, upstream, n in rows:
        if isinstance(reason, str) and _REASON.fullmatch(reason):
            counts[reason] += n
        elif isinstance(upstream, int) and 100 <= upstream <= 599:
            counts[f"agent_{upstream}"] += n
        else:
            counts["unknown"] += n
    out = sorted(({"reason": k, "n": n} for k, n in counts.items()), key=lambda r: (-r["n"], r["reason"]))
    return {"rows": out,
            "note": "챗 오류의 까닭 코드만 센다(상류 응답 본문 · 예외 글은 싣지 않는다). agent_<번호> 는 에이전트 서버가 그 HTTP 상태로 답한 턴, "
                    "unknown 은 까닭 칸이 없는 줄이다."}


_TURN_KINDS = ("chat", "think", "delib", "routine")
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}")      # 중계가 싣는 모델 이름의 꼴(app/agent/routes.py _TURN_MODEL_OK)


def _chat_kinds(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "principal")
    kinds: dict[str, int] = defaultdict(int)
    models: dict[str, int] = defaultdict(int)
    unknown, since = 0, None
    for ts, meta in c.execute(f"SELECT ts, meta FROM agent_audit WHERE ts >= ? AND ts < ? AND event = 'chat_done'{q}",
                              (x.w.since, x.w.until, *a)):
        try:
            m = json.loads(meta) if meta else None
        except ValueError:
            m = None
        kind = m.get("kind") if isinstance(m, dict) else None
        if kind not in _TURN_KINDS:
            unknown += 1
            continue
        kinds[kind] += 1
        since = ts if since is None or ts < since else since
        seen = m.get("models")
        for name in {n for n in (seen if isinstance(seen, list) else []) if isinstance(n, str) and _MODEL.fullmatch(n)}:
            models[name] += 1
    return {"rows": sorted(({"kind": k, "turns": n} for k, n in kinds.items()), key=lambda r: (-r["turns"], r["kind"])),
            "models": sorted(({"model": k, "turns": n} for k, n in models.items()), key=lambda r: (-r["turns"], r["model"])),
            "unknown": unknown, "since": kst_day(since) if since is not None else None,
            "note": "끝까지 간 턴(chat_done)의 종류다 — chat 은 일반 챗, think 는 띵킹(전문가들이 각자 답함), delib 는 웹에서 연 심의, routine 은 "
                    "분석 루틴이다. 보낸 요청이 아니라 그 턴에 실제로 흐른 사건으로 가른다. models 는 그 턴에 쓰인 모델마다의 턴 수다(한 턴이 "
                    "모델 여럿을 쓰면 여럿에 든다). unknown 은 종류를 적기 전의 턴이다 — 이 판의 포털이 뜬 뒤 끝난 턴부터 적힌다"
                    + (f"(기간 안의 첫 줄 {kst_day(since)})." if since is not None else ".") + " 오류로 끝난 턴은 들지 않는다."}


def family_of(event: str) -> str:
    return next((k for k, heads in FAMILIES if event.startswith(heads)), "other")


def _events(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "principal")
    rows = c.execute(f"SELECT event, COALESCE(status, ''), COUNT(*) FROM agent_audit WHERE ts >= ? AND ts < ? "
                     f"AND event NOT IN {_CHAT_IN}{q} GROUP BY 1, 2", (x.w.since, x.w.until, *a)).fetchall()
    order = {k: i for i, (k, _) in enumerate(FAMILIES)}
    out = sorted(({"family": family_of(e), "event": e, "status": s, "n": n} for e, s, n in rows),
                 key=lambda r: (order.get(r["family"], len(order)), r["event"], -r["n"], r["status"]))
    return {"rows": out,
            "note": "챗 밖의 포털 사건이다(업로드 · PC 도우미 · 발표자료 · 위키 · 카드 대조 · 대화 내보내기 · 앱 패널 · 심의 멈춤 · 그 밖). "
                    "상태는 적힌 그대로다 — 빈 칸은 그 사건이 상태를 적지 않는 줄이다(위키 보내기 성공 등). 사건마다 적기 시작한 날이 다르다."}


# ── 대화(conversations) ────────────────────────────────────────────────────────────────────────────────────
def _conversations(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "owner_sub")
    args = (x.w.since, x.w.until, *a)
    where = f"FROM conversations WHERE created_at >= ? AND created_at < ?{q}"
    daily = c.execute(f"SELECT {_day('created_at')} d, kind, source, COUNT(*) {where} GROUP BY d, kind, source ORDER BY d",
                      args).fetchall()
    totals = c.execute(f"SELECT kind, source, COUNT(*), COUNT(DISTINCT lower(owner_sub)) {where} GROUP BY kind, source", args).fetchall()
    oldest = _first_day(c, "conversations", "created_at")
    return {"rows": [{"day": d, "kind": k, "source": s, "n": n} for d, k, s, n in daily],
            "totals": sorted(({"kind": k, "source": s, "n": n, "owners": o} for k, s, n, o in totals), key=lambda r: -r["n"]),
            "oldest_day": oldest,
            "note": "만든 날 기준 대화 수다(종류 chat · deliberation · risk-review 등 × 출처 web · mcp). 주인이 지운 대화는 빠진다 — 남은 가장 "
                    f"오래된 대화는 {oldest or '없음'} 이다. 메시지 수 · 글은 세지 않는다. 날이 빠진 줄은 0 이다."}


# ── 절차 · 루틴(procedures.sqlite) ─────────────────────────────────────────────────────────────────────────
def _pivot(rows: list[tuple[str, str, int]], name: str, open_states: tuple[str, ...]) -> tuple[list[dict], dict]:
    by: dict[str, dict[str, int]] = defaultdict(dict)
    for key, state, n in rows:
        by[key][state] = n

    def _one(states: dict[str, int]) -> dict:
        done = states.get("done", 0)
        ended = sum(n for s, n in states.items() if s not in open_states)
        return {"n": sum(states.values()), "done": done, "ended": ended, "completion": round(done / ended, 3) if ended else None}

    out = sorted(({name: k, "states": v, **_one(v)} for k, v in by.items()), key=lambda r: (-r["n"], r[name]))
    allstates: dict[str, int] = defaultdict(int)
    for v in by.values():
        for s, n in v.items():
            allstates[s] += n
    return out, _one(allstates)


def _procedure_runs(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "owner_sub", "run_by")
    rows = c.execute(f"SELECT origin, state, COUNT(*) FROM runs WHERE started_at >= ? AND started_at < ?{q} GROUP BY 1, 2",
                     (x.w.since, x.w.until, *a)).fetchall()
    out, overall = _pivot(rows, "origin", _PROC_OPEN)
    return {"rows": out, "completion": overall,
            "note": "기간 안에 시작한 절차 실행이다(출처 manual · replay · batch 등 × 상태). completion 은 끝난 실행 가운데 done 의 몫이다 — "
                    "도는 중 · 게이트에 멈춘 실행은 분모에서 뺀다(재기동에 끊긴 실행은 failed 로 끝난다)."}


def _routine_runs(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "owner_sub")
    rows = c.execute(f"SELECT executor, state, COUNT(*) FROM routine_runs WHERE started_at >= ? AND started_at < ?{q} GROUP BY 1, 2",
                     (x.w.since, x.w.until, *a)).fetchall()
    out, overall = _pivot(rows, "executor", _ROUTINE_OPEN)
    ra = c.execute(f"SELECT COUNT(*) FROM routine_runs WHERE started_at >= ? AND started_at < ? AND COALESCE(ra_report_id, '') != ''{q}",
                   (x.w.since, x.w.until, *a)).fetchone()[0]
    return {"rows": out, "completion": overall, "ra_drafts": ra,
            "note": "기간 안에 시작한 분석 루틴 실행이다(실행기 mcp · chat · web × 상태). completion 은 끝난 실행 가운데 done 의 몫이다 — "
                    "도는 중 · 사람을 기다리는 실행은 빼고, interrupted(실행자가 사라짐)는 끝난 쪽으로 센다. ra_drafts 는 그 가운데 "
                    "Report Archive 초안까지 간 실행이다."}


# ── PAT(token_store) ──────────────────────────────────────────────────────────────────────────────────────
def _pats_live(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "sub", "email")
    rows = c.execute(f"SELECT parent_jti IS NULL, COUNT(*), COUNT(DISTINCT lower(sub)) FROM pat WHERE revoked = 0 AND exp >= ?{q} "
                     "GROUP BY 1", (x.now, *a)).fetchall()
    out = sorted(({"kind": "personal" if own else "exchanged", "n": n, "owners": o} for own, n, o in rows),
                 key=lambda r: r["kind"] != "personal")
    return {"rows": out,
            "note": "지금 살아 있는 PAT 이다(폐기 · 만료 빼고 — 기간과 무관). personal 은 토큰 화면에서 사람이 낸 것, exchanged 는 그것을 "
                    "바꿔 받은 것(토큰 교환)이다. 챗 · 절차가 요청마다 찍는 짧은 PAT 은 원장에 적지 않는다."}


def _pats_weekly(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "sub", "email")
    got: dict[str, tuple[int, int]] = {
        k: (n, p) for k, n, p in c.execute(f"SELECT {_week('created')} k, COUNT(*), SUM(parent_jti IS NULL) FROM pat "
                                           f"WHERE created >= ? AND created < ?{q} GROUP BY k", (x.w.since, x.w.until, *a))}
    rows = []
    for b in _buckets(x.w.weeks(), x.w, x.w.first.isoformat(), {k: v[0] for k, v in got.items()}):
        rows.append({"week": b["key"], "n": b["value"], "personal": got.get(b["key"], (0, 0))[1], "partial": b["partial"]})
    return {"rows": rows,
            "note": "주마다 낸 PAT 이다 — 원장에 아직 남은 행만 센다. 만료된 PAT 은 원장에서 지워지므로(폐기 목록을 낼 때 함께 지운다) 지난 주일수록 "
                    "적게 보인다. 날마다 찍어 두는 수는 M2 다."}


# ── 권한 수요(access_requests · connections) ───────────────────────────────────────────────────────────────
def _access_requests(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    labels = x.labels.get("key") or {}
    by: dict[str, dict] = {}
    for key, status, created, decided in c.execute(
            f"SELECT key, status, created_at, decided_at FROM access_requests WHERE created_at >= ? AND created_at < ?{q}",
            (x.w.since, x.w.until, *a)):
        r = by.setdefault(key, {"key": key, "label": labels.get(key, key), "n": 0, "pending": 0, "approved": 0, "rejected": 0, "_lat": []})
        r["n"] += 1
        if status in ("pending", "approved", "rejected"):
            r[status] += 1
        if status == "approved" and decided is not None and decided >= created:
            r["_lat"].append(decided - created)
    rows = []
    for r in by.values():
        lat = r.pop("_lat")
        rows.append({**r, "median_hours": round(statistics.median(lat) / 3600, 1) if lat else None})
    rows.sort(key=lambda r: (-r["n"], r["key"]))
    return {"rows": rows,
            "note": "기간 안에 들어온 권한 요청이다(기능 · 플랫폼 키별). median_hours 는 승인된 요청이 결정까지 걸린 시간의 중앙값이다."}


def _connections(c: sqlite3.Connection, x: _Ctx) -> dict:
    q, a = _not_in(x.ex, "email")
    rows = c.execute(f"SELECT service, COUNT(*), SUM(created_at >= ?) FROM connections WHERE 1=1{q} GROUP BY service",
                     (x.w.since, *a)).fetchall()
    out = sorted(({"service": s, "n": n, "new": new or 0} for s, n, new in rows), key=lambda r: (-r["n"], r["service"]))
    return {"rows": out,
            "note": "지금 등록된 외부 연결이다(사람 × 서비스 — 기간과 무관). new 는 기간 안에 등록하거나 다시 등록한 수다(다시 등록하면 시각이 새로 "
                    "적힌다). 지운 연결은 빠진다."}


# ── 접어 둔 표에서 읽는 칸(M2 — usage_daily · usage_actor_daily · usage_fold, 감사 원장 파일 안) ──────────────────────────────────────
def _has_fold(c: sqlite3.Connection) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'usage_fold'").fetchone() is not None


def _pending() -> dict:
    return {"rows": [], "pending": True, "note": _FOLD_PENDING}


def _fold_meta(c: sqlite3.Connection, x: _Ctx, source: str) -> dict:
    """그 원천의 접은 범위 — first(값이 있는 첫 날) · last · 오늘을 접은 때 · 마지막 시도의 실패 까닭."""
    key = ("meta", source)
    if key not in x.memo:
        first, last = c.execute("SELECT MIN(day), MAX(day) FROM usage_fold WHERE source = ? AND day != '*' AND note != ?",
                                (source, FOLD_NOCOVER)).fetchone()
        today = c.execute("SELECT folded_at FROM usage_fold WHERE source = ? AND day = ?", (source, x.w.last.isoformat())).fetchone()
        star = c.execute("SELECT folded_at, note FROM usage_fold WHERE source = ? AND day = '*'", (source,)).fetchone()
        x.memo[key] = {"first": first, "last": last, "today_at": today[0] if today else None,
                       "attempt_at": star[0] if star else None, "error": (star[1] or None) if star else None}
    return x.memo[key]


def _fold_rows(c: sqlite3.Connection, x: _Ctx, source: str) -> list[tuple[str, str, dict, float]]:
    """기간 안의 접은 줄 (날, 지표, 칸, 값) — 칸(JSON)은 같은 글자를 한 번만 푼다."""
    key = ("rows", source)
    if key not in x.memo:
        seen: dict[str, dict] = {"": {}}
        out = []
        for day, metric, dims, value in c.execute("SELECT day, metric, dims, value FROM usage_daily WHERE source = ? AND day >= ? AND day <= ?",
                                                  (source, x.w.first.isoformat(), x.w.last.isoformat())):
            if dims not in seen:
                try:
                    d = json.loads(dims)
                except ValueError:
                    d = None
                seen[dims] = d if isinstance(d, dict) else {}
            out.append((day, metric, seen[dims], value))
        x.memo[key] = out
    return x.memo[key]


def _actor_rows(c: sqlite3.Connection, x: _Ctx) -> list[tuple[str, str, str, int]]:
    """기간 안의 사람 줄 (날, 이메일, 갈래, 수) — 뺄 계정은 여기서 뺀다."""
    if "actors" not in x.memo:
        q, a = _not_in(x.ex, "email")
        x.memo["actors"] = c.execute(f"SELECT day, email, source, n FROM usage_actor_daily WHERE day >= ? AND day <= ?{q}",
                                     (x.w.first.isoformat(), x.w.last.isoformat(), *a)).fetchall()
    return x.memo["actors"]


def _group_of(source: str) -> str:
    if source == "ra-for" or source.startswith("mcp-for"):
        return "engine"
    return "mcp" if source == "ra" or source.startswith("mcp") else source


def _via_of(source: str) -> str:
    """사람 줄 갈래 → 자격(via) — mcp-<via> · mcp-for-<via> · mcp · mcp-for."""
    for head in ("mcp-for-", "mcp-"):
        if source.startswith(head):
            return source[len(head):]
    return ""


def _series(axis: list[str], first: str | None, got: dict) -> list:
    """날마다 값 — 원천의 첫 날보다 앞선 날은 None(기록 전), 그 뒤의 빈 날은 0."""
    return [None if first is None or d < first else got.get(d, 0) for d in axis]


def _today_note(meta: dict) -> str:
    at = meta.get("today_at")
    if not at:
        return " 오늘은 아직 접지 않았다(값이 0 으로 보인다)."
    return f" 오늘은 {datetime.fromtimestamp(at, KST):%H:%M} 에 접은 데까지다(아직 안 끝난 날)."


def _stale(meta: dict) -> str:
    return f" 마지막 접기가 실패했다 — {meta['error']}" if meta.get("error") else ""


def _week_key(day: str) -> str:
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).isoformat()


def quantile(counts: list, q: float) -> float | None:
    """칸마다의 수 → 분위수(ms) 어림 — 칸 안 선형 보간(게이트웨이 usage_rollup.quantile 과 같은 셈). 표본이 없으면 None."""
    total = sum(counts)
    if total <= 0:
        return None
    target, seen = q * total, 0
    for i, n in enumerate(counts):
        if n <= 0:
            continue
        if seen + n >= target:
            if i >= len(LAT_LE_MS):
                return LAT_LE_MS[-1]
            lo = LAT_LE_MS[i - 1] if i else 0
            return round(lo + (LAT_LE_MS[i] - lo) * max(0.0, target - seen) / n, 1)
        seen += n
    return LAT_LE_MS[-1]


def _fold_status(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    fp = fingerprint(x.ex)
    rows = []
    for source, label in FOLD_SOURCES:
        m = _fold_meta(c, x, source)
        days, other, closed = c.execute("SELECT COUNT(*), SUM(ex != ?), MAX(CASE WHEN final = 1 THEN day END) FROM usage_fold"
                                        " WHERE source = ? AND day != '*' AND note != ?", (fp, source, FOLD_NOCOVER)).fetchone()
        rows.append({"source": source, "label": label, "first_day": m["first"], "last_day": m["last"], "closed_through": closed,
                     "days": days or 0, "other_list_days": other or 0, "attempt_at": m["attempt_at"], "error": m["error"]})
    return {"rows": rows,
            "note": "날마다 접어 둔 표의 상태다. 오늘은 돌 때마다 다시 접고, 끝난 날은 사흘 동안 날마다 한 번 다시 접은 뒤 닫는다(closed_through — 닫힌 "
                    "날은 다시 세지 않아 그 뒤에 지워진 대화 · PAT · 정문 로그로 줄지 않는다). error 는 그 원천의 마지막 접기가 실패한 까닭이다 — "
                    "그동안 그 칸은 앞서 접은 데까지만 보인다. other_list_days 는 지금과 다른 뺄 계정 목록으로 접은 날 수다(게이트웨이 · 에이전트 "
                    "서버는 다음 접기에 다시 접고, 포털 · 정문 쪽 닫힌 날은 그대로 둔다)."}


def _active(c: sqlite3.Connection, x: _Ctx) -> dict:
    """원천을 가로지른 쓴 사람 — 날 · 주 · 달마다 서로 다른 이메일(한 번만 셈해 세 칸이 나눠 쓴다)."""
    if "active" in x.memo:
        return x.memo["active"]
    first = c.execute("SELECT MIN(day) FROM usage_actor_daily").fetchone()[0]
    day_all: dict[str, set] = defaultdict(set)
    day_grp: dict[tuple[str, str], set] = defaultdict(set)
    week: dict[str, set] = defaultdict(set)
    month: dict[str, set] = defaultdict(set)
    everyone: set = set()
    grp_all: dict[str, set] = defaultdict(set)
    for day, email, source, _n in _actor_rows(c, x):
        g = _group_of(source)
        day_all[day].add(email)
        day_grp[(day, g)].add(email)
        week[_week_key(day)].add(email)
        month[day[:7]].add(email)
        everyone.add(email)
        grp_all[g].add(email)
    x.memo["active"] = {"first": first, "day_all": day_all, "day_grp": day_grp, "week": week, "month": month,
                        "everyone": everyone, "grp_all": grp_all}
    return x.memo["active"]


_ACTIVE_NOTE = ("원천을 가로지른 쓴 사람이다 — 그날 로그인했거나 · 챗 턴을 시작했거나 · 타일로 들어갔거나 · MCP 도구를 불렀거나(개인 Claude · 포털 챗 · "
                "절차) · 엔진이 그 사람의 일로 도구를 불렀거나(engine — 감사 전용 머리, 검증하지 않은 주장) · MCP 심의를 맡겼거나 · 정문을 지난 요청이 "
                "그 사람의 로그인 연결 ID 로 이어진 서로 다른 계정. 로그인 기준(위)과 달리 며칠씩 "
                "다시 로그인하지 않는 사람도 든다. 정문 요청은 귀속이지 증명이 아니고(쿠키), 접기 전에 회전으로 사라진 로그의 날에는 빠진다. ")


def _active_daily(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    a = _active(c, x)
    rows = []
    for d in x.w.axis():
        if a["first"] is None or d < a["first"]:
            rows.append({"day": d, "people": None, **dict.fromkeys(_ACTOR_GROUPS)})
        else:
            rows.append({"day": d, "people": len(a["day_all"].get(d, ())), **{g: len(a["day_grp"].get((d, g), ())) for g in _ACTOR_GROUPS}})
    return {"rows": rows, "first_day": a["first"],
            "totals": {"people": len(a["everyone"]), **{g: len(a["grp_all"].get(g, ())) for g in _ACTOR_GROUPS}},
            "note": _ACTIVE_NOTE + "people 는 그날의 서로 다른 계정(DAU), 나머지 칸은 갈래마다의 계정이다(한 사람이 여러 갈래에 든다). "
                    + (f"접어 둔 첫 날({a['first']}) 전은 null 이다." if a["first"] else "접어 둔 사람 줄이 아직 없다.")
                    + _today_note(_fold_meta(c, x, "portal")) + " 사람 줄은 400일 뒤 지운다."}


def _active_span(c: sqlite3.Connection, x: _Ctx, unit: str) -> dict:
    if not _has_fold(c):
        return _pending()
    a = _active(c, x)
    got = {k: len(v) for k, v in a["week" if unit == "week" else "month"].items()}
    rows = [{unit: b["key"], "people": b["value"], "partial": b["partial"]}
            for b in _buckets(x.w.weeks() if unit == "week" else x.w.months(), x.w, a["first"], got)]
    return {"rows": rows,
            "note": f"같은 {'주(월요일에 시작)' if unit == 'week' else '달'}에 쓴 서로 다른 계정이다({'WAU' if unit == 'week' else 'MAU'} — 원천을 가로질러). "
                    "기간 앞뒤에 걸치거나 아직 끝나지 않았거나 접어 둔 줄이 그 중간에 시작한 칸은 partial 이고, 그 전 칸은 null 이다."}


def _mcp(c: sqlite3.Connection, x: _Ctx) -> dict:
    """게이트웨이 줄을 한 번 모은다 — 날 · via · 앱 · 도구마다."""
    if "mcp" in x.memo:
        return x.memo["mcp"]
    zero = lambda: {"calls": 0, "status_calls": 0, "err_app": 0, "err_gate": 0, "cache": 0, "big": 0, "chars": 0}  # noqa: E731
    day: dict[str, dict] = defaultdict(zero)
    via: dict[str, dict] = defaultdict(zero)
    app: dict[str, dict] = defaultdict(zero)
    tool: dict[tuple[str, str], dict] = defaultdict(zero)
    lat_app: dict[str, list] = defaultdict(lambda: [0] * (len(LAT_LE_MS) + 1))
    lat_tool: dict[tuple[str, str], list] = defaultdict(lambda: [0] * (len(LAT_LE_MS) + 1))
    status_tools: set = set()
    auth: dict[str, int] = defaultdict(int)
    anon: dict[str, int] = defaultdict(int)
    for_calls: dict[str, int] = defaultdict(int)
    ra_day: dict[str, int] = defaultdict(int)
    ra_via: dict[str, int] = defaultdict(int)
    for d, metric, dims, v in _fold_rows(c, x, "gateway"):
        n = int(v)
        if metric == "auth_fail":
            auth[str(dims.get("reason") or "other")] += n
            continue
        if metric == "anon_calls":
            anon[str(dims.get("via") or "")] += n
            continue
        if metric == "for_calls":
            for_calls[str(dims.get("via") or "")] += n
            continue
        a, t, vi = str(dims.get("app") or ""), str(dims.get("tool") or ""), str(dims.get("via") or "")
        if metric == "lat":
            le = dims.get("le")
            if isinstance(le, int) and 0 <= le <= len(LAT_LE_MS):
                lat_app[a][le] += n
                lat_tool[(a, t)][le] += n
            continue
        if metric not in ("calls", "err_app", "err_gate", "cache", "big", "chars"):
            continue
        k = metric
        if metric == "calls" and dims.get("st"):
            k = "status_calls"
            status_tools.add((a, t))
        for bucket in (day[d], via[vi], app[a], tool[(a, t)]):
            bucket[k] += n
        if t == RA_DRAFT_TOOL and metric in ("calls", "err_app", "err_gate"):
            sign = 1 if metric == "calls" else -1           # 성공 호출 = 호출 − 실패
            ra_day[d] += sign * n
            ra_via[vi] += sign * n
    people_day: dict[str, set] = defaultdict(set)
    people_via: dict[str, set] = defaultdict(set)
    people_for_via: dict[str, set] = defaultdict(set)
    people_for: set = set()
    people_ra: set = set()
    people_ra_for: set = set()
    ra_named = ra_named_for = 0
    everyone: set = set()
    for d, email, source, n in _actor_rows(c, x):
        if source == "ra":
            people_ra.add(email)
            ra_named += n
        elif source == "ra-for":
            people_ra_for.add(email)
            ra_named_for += n
        elif source.startswith("mcp-for"):
            people_for_via[_via_of(source)].add(email)
            people_for.add(email)
        elif source.startswith("mcp"):
            people_day[d].add(email)
            people_via[_via_of(source)].add(email)
            everyone.add(email)
    x.memo["mcp"] = {"day": day, "via": via, "app": app, "tool": tool, "lat_app": lat_app, "lat_tool": lat_tool, "status_tools": status_tools,
                     "auth": auth, "anon": anon, "for_calls": for_calls, "ra_day": ra_day, "ra_via": ra_via, "people_day": people_day,
                     "people_via": people_via, "people_for_via": people_for_via, "people_for": people_for, "people_ra": people_ra,
                     "people_ra_for": people_ra_for, "ra_named": ra_named, "ra_named_for": ra_named_for, "everyone": everyone}
    return x.memo["mcp"]


def _field_first(c: sqlite3.Connection) -> dict[str, str]:
    """게이트웨이 감사의 칸(caller · via · ip · chars)이 처음 나온 날 — 접는 쪽이 그 날의 줄로 적어 둔다(창보다 오래됐으면 없다)."""
    out: dict[str, str] = {}
    for day, dims in c.execute("SELECT day, dims FROM usage_daily WHERE source = 'gateway' AND metric = 'field_first'"):
        try:
            k = json.loads(dims).get("field")
        except (ValueError, AttributeError):
            continue
        if isinstance(k, str) and (k not in out or day < out[k]):
            out[k] = day
    return out


def _errs(b: dict) -> dict:
    total = b["calls"] + b["status_calls"]
    bad = b["err_app"] + b["err_gate"]
    return {"errors_app": b["err_app"], "errors_gate": b["err_gate"], "error_rate": round(bad / total, 3) if total else None}


def _mcp_daily(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    m, meta = _mcp(c, x), _fold_meta(c, x, "gateway")
    rows = []
    for d in x.w.axis():
        if meta["first"] is None or d < meta["first"]:
            rows.append({"day": d, "calls": None, "status_calls": None, "errors": None, "people": None})
        else:
            b = m["day"].get(d)
            rows.append({"day": d, "calls": b["calls"] if b else 0, "status_calls": b["status_calls"] if b else 0,
                         "errors": (b["err_app"] + b["err_gate"]) if b else 0, "people": len(m["people_day"].get(d, ()))})
    tot = {k: sum(b[k] for b in m["day"].values()) for k in ("calls", "status_calls", "err_app", "err_gate", "cache", "big")}
    return {"rows": rows, "first_day": meta["first"],
            "totals": {"calls": tot["calls"], "status_calls": tot["status_calls"], "errors_app": tot["err_app"], "errors_gate": tot["err_gate"],
                       "cache": tot["cache"], "big": tot["big"], "people": len(m["everyone"]), "anon_calls": sum(m["anon"].values()),
                       "for_calls": sum(m["for_calls"].values()), "people_for": len(m["people_for"])},
            "note": "게이트웨이를 지난 MCP 도구 호출이다(게이트웨이 감사 원장을 날마다 접은 것). calls 는 상태 묻기 도구(deliberate_status 등)를 뺀 "
                    "호출, status_calls 는 상태 묻기다(되풀이라 호출 수를 부풀린다). errors 는 실패한 호출(앱 쪽 + 관문 쪽), people 은 그날 도구를 "
                    "부른 서로 다른 계정이다 — 호출자가 적힌 줄만 사람으로 센다. 호출자가 빈 엔진 호출 가운데 에이전트 서버가 '누구의 일' 감사 머리를 "
                    "실은 것은 for_calls · people_for(그 일의 사람 — 검증하지 않은 주장, 위조되면 이 수만 틀린다)이고, 그 머리도 없는 줄이 "
                    "anon_calls 다. 캐시 적중도 호출 한 번이다. "
                    + (f"감사 원장의 첫 날({meta['first']}) 전은 null 이다." if meta["first"] else "접어 둔 날이 아직 없다.")
                    + _today_note(meta) + _stale(meta)}


def _mcp_via(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    m = _mcp(c, x)
    rows = [{"via": v, "calls": b["calls"], "status_calls": b["status_calls"], **_errs(b), "people": len(m["people_via"].get(v, ())),
             "anon_calls": m["anon"].get(v, 0), "for_calls": m["for_calls"].get(v, 0), "people_for": len(m["people_for_via"].get(v, ()))}
            for v, b in m["via"].items()]
    rows.sort(key=lambda r: (-(r["calls"] + r["status_calls"]), r["via"]))
    since = _field_first(c).get("via")
    return {"rows": rows, "via_since": since,
            "note": "어느 자격으로 들어온 호출인가 — pat 은 개인 Claude(와 사람 PAT 로 도는 서버 앱), chat 은 포털 챗, procedure 는 절차 실행기, "
                    "mcp-app 은 앱 패널, gw-token 은 에이전트 서버(심의 엔진 · 좌석 조회), service 는 박스 작업, ticket 은 그림 · 키트 받기다. "
                    "people 은 그 자격으로 부른 서로 다른 계정, for_calls · people_for 는 호출자가 빈 줄 가운데 '누구의 일' 감사 머리로 사람에게 이은 "
                    "줄과 그 사람 수(엔진 — 검증하지 않은 주장), anon_calls 는 그 머리도 없는 줄이다. "
                    + (f"via 칸은 {since} 부터 적혔다 — 그 전 호출은 빈 칸으로 든다." if since else "빈 칸은 via 를 적기 전의 호출이다.")}


def _mcp_apps(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    m = _mcp(c, x)
    tools: dict[str, int] = defaultdict(int)
    for a, _t in m["tool"]:
        tools[a] += 1
    rows = [{"app": a, "calls": b["calls"], "status_calls": b["status_calls"], **_errs(b), "cache": b["cache"], "big": b["big"],
             "tools": tools[a], "ms_p50": quantile(m["lat_app"][a], 0.5), "ms_p95": quantile(m["lat_app"][a], 0.95)}
            for a, b in m["app"].items()]
    rows.sort(key=lambda r: (-(r["calls"] + r["status_calls"]), r["app"]))
    return {"rows": rows, "approx": True,
            "note": "앱(게이트웨이 백엔드 키)마다의 호출이다. 실패는 앱 쪽(앱이 오류로 답했거나 기한을 넘김)과 관문 쪽(게이트웨이가 권한 · 울타리 · "
                    "모르는 도구 · 사람 자격으로 막음)으로 가른다. cache 는 캐시 적중, big 은 큰 응답(10만 자 이상), tools 는 불린 도구 수다. "
                    "p50 · p95 는 백엔드에 다녀온 성공 호출의 걸린 시간(ms)이고 칸 안 보간 어림이다(≈). 빈 앱 칸은 게이트웨이가 모르는 도구 "
                    "호출이다."}


def _mcp_tools(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    m = _mcp(c, x)
    rows = [{"app": a, "tool": t, "status": (a, t) in m["status_tools"], "calls": b["calls"] + b["status_calls"], **_errs(b),
             "cache": b["cache"], "big": b["big"], "ms_p50": quantile(m["lat_tool"][(a, t)], 0.5),
             "ms_p95": quantile(m["lat_tool"][(a, t)], 0.95)} for (a, t), b in m["tool"].items()]
    rows.sort(key=lambda r: (-r["calls"], r["app"], r["tool"]))
    return {"rows": rows[:TOP_TOOLS], "total_tools": len(rows), "approx": True,
            "note": f"많이 불린 도구 {TOP_TOOLS}개다(원래 이름 — 겹침 접두 · 호출 별칭은 접었다). status 는 상태 묻기 도구다. 주소가 든 이름"
                    "(rest_call · resources/read)은 주소를 뗐고, 게이트웨이가 모르는 도구는 (unknown) 한 칸이다."}


def _mcp_auth(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    m = _mcp(c, x)
    rows = sorted(({"reason": r, "n": n} for r, n in m["auth"].items()), key=lambda r: (-r["n"], r["reason"]))
    return {"rows": rows,
            "note": "/mcp 인증 실패다(도구 호출에 들지 않는다). expired 는 서명은 맞고 수명이 끝난 토큰, unverified-token 은 틀렸거나 검증하지 못한 "
                    "토큰, no-bearer 는 토큰 없이 온 요청이다. 검증되지 않은 토큰이라 누구인지는 모른다."}


def _mcp_personal_weekly(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    week: dict[str, set] = defaultdict(set)
    for d, email, source, _n in _actor_rows(c, x):
        if source == "mcp-pat":
            week[_week_key(d)].add(email)
    first = _field_first(c).get("via") or _fold_meta(c, x, "gateway")["first"]
    rows = [{"week": b["key"], "people": b["value"], "partial": b["partial"]}
            for b in _buckets(x.w.weeks(), x.w, first, {k: len(v) for k, v in week.items()})]
    return {"rows": rows,
            "note": "주마다 개인 PAT 로 MCP 도구를 부른 서로 다른 계정이다(개인 Claude — via=pat). 사람 PAT 로 도는 서버 앱의 호출도 여기에 섞인다. "
                    "via 칸을 적기 전의 주는 null 이다."}


def _delib_jobs(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    meta = _fold_meta(c, x, "agent")
    kinds: dict[str, dict] = {}
    daily: dict[str, int] = defaultdict(int)
    anon = 0
    for d, metric, dims, v in _fold_rows(c, x, "agent"):
        if metric == "anon_jobs":
            anon += int(v)
            continue
        k = kinds.setdefault(str(dims.get("kind") or ""), {"n": 0, "states": defaultdict(int), "external": 0, "with_report": 0, "seats": 0,
                                                           "seated": 0, "rounds": 0, "dur_s": 0.0, "dur_n": 0})
        if metric == "jobs":
            k["n"] += int(v)
            k["states"][str(dims.get("status") or "")] += int(v)
            k["external"] += int(v) if dims.get("llm") == "external" else 0
            daily[d] += int(v)
        elif metric == "jobs_report":
            k["with_report"] += int(v)
        elif metric in ("seats", "seated", "rounds", "dur_n"):
            k[metric] += int(v)
        elif metric == "dur_s":
            k["dur_s"] += v
    rows = [{"kind": name, "n": k["n"], "done": k["states"].get("done", 0), "states": dict(k["states"]), "external": k["external"],
             "with_report": k["with_report"], "seats_avg": round(k["seats"] / k["seated"], 1) if k["seated"] else None,
             "rounds_avg": round(k["rounds"] / k["seated"], 1) if k["seated"] else None,
             "minutes_avg": round(k["dur_s"] / k["dur_n"] / 60, 1) if k["dur_n"] else None} for name, k in kinds.items() if k["n"]]
    rows.sort(key=lambda r: (-r["n"], r["kind"]))
    people = {email for _d, email, source, _n in _actor_rows(c, x) if source == "delib"}
    return {"rows": rows, "daily": _series(x.w.axis(), meta["first"], daily), "first_day": meta["first"],
            "totals": {"jobs": sum(r["n"] for r in rows), "with_report": sum(r["with_report"] for r in rows), "people": len(people),
                       "anon_jobs": anon},
            "note": "MCP 로 맡긴 심의 잡이다(에이전트 서버의 잡 원장 — 개인 Claude 의 deliberate_start · 심의 묶음). 웹 챗에서 연 심의는 이 원장에 남지 "
                    "않아 빠진다(위 챗 턴에 든다). 잡은 줄을 서거나 돌기 시작한 날에 든다. with_report 는 Report Archive 보고서가 붙은 잡, "
                    "external 은 판단 LLM 이 외부 응답자(Claude)였던 잡, seats_avg · rounds_avg 는 좌석이 앉은 잡의 평균, minutes_avg 는 끝난 잡이 "
                    "돈 시간의 평균(분)이다. anon_jobs 는 주인이 적히지 않은 잡이다. "
                    + (f"잡 원장의 첫 날({meta['first']}) 전은 null 이다." if meta["first"] else "접어 둔 날이 아직 없다.")
                    + _today_note(meta) + _stale(meta)}


def _ra_drafts(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    m, meta = _mcp(c, x), _fold_meta(c, x, "gateway")
    total = sum(m["ra_day"].values())
    reports = sum(int(v) for _d, metric, _dims, v in _fold_rows(c, x, "agent") if metric == "jobs_report")
    return {"rows": [{"day": d, "n": n} for d, n in zip(x.w.axis(), _series(x.w.axis(), meta["first"], m["ra_day"]), strict=True)],
            "by_via": sorted(({"via": v, "n": n} for v, n in m["ra_via"].items() if n), key=lambda r: (-r["n"], r["via"])),
            "totals": {"drafts": total, "people": len(m["people_ra"]), "named": m["ra_named"], "named_for": m["ra_named_for"],
                       "people_for": len(m["people_ra_for"]), "unnamed": max(0, total - m["ra_named"] - m["ra_named_for"]),
                       "delib_reports": reports},
            "note": f"Report Archive 초안이다 — 게이트웨이를 지난 {RA_DRAFT_TOOL} 의 성공 호출(챗의 /보고서 · 심의 보고서 · 루틴 · 개인 Claude 모두 이 "
                    "도구로 만든다). people · named 는 호출자가 적힌 초안, people_for · named_for 는 호출자가 빈 엔진 호출을 '누구의 일' 감사 머리로 "
                    "사람에게 이은 초안(검증하지 않은 주장)이고, unnamed 는 둘 다 아닌 초안이다. delib_reports 는 MCP 심의 잡 가운데 보고서가 붙은 수다(에이전트 서버의 잡 원장). 포털이 "
                    "게이트웨이를 거치지 않고 넣는 보고서(문서 정밀 변환 등)는 들지 않는다." + _stale(meta)}


def _front_door(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    meta = _fold_meta(c, x, "nginx")
    axis = x.w.axis()
    labels = x.labels.get("service") or {}
    req: dict[str, dict[str, int]] = defaultdict(dict)
    ppl: dict[str, dict[str, int]] = defaultdict(dict)
    loose = 0
    for d, metric, dims, v in _fold_rows(c, x, "nginx"):
        if metric == "unattributed":
            loose += int(v)
        elif metric in ("requests", "people"):
            (req if metric == "requests" else ppl)[str(dims.get("service") or "")][d] = int(v)
    rows = [{"service": s, "label": labels.get(s, s), "requests": sum(by.values()), "days": len(by),
             "people_max": max(ppl[s].values(), default=0), "daily": _series(axis, meta["first"], by)} for s, by in req.items()]
    rows.sort(key=lambda r: (-r["requests"], r["service"]))
    people = {email for _d, email, source, _n in _actor_rows(c, x) if source == "nginx"}
    return {"rows": rows, "first_day": meta["first"],
            "totals": {"requests": sum(r["requests"] for r in rows), "unattributed": loose, "people": len(people)},
            "note": "정문(nginx)을 지난 요청을 서비스마다 센 것이다 — apps/<앱> 은 허브에 올린 앱 하나하나다(타일 진입 원장에 없는 '허브 앱 열기' 가 "
                    "여기서 보인다). 로그인 연결 ID(쿠키)가 접속 원장의 로그인 줄과 이어진 요청만 세고(귀속이지 증명이 아니다), 이어지지 않은 요청"
                    "(로그인 전 · 스캐너 · PAT)은 unattributed 다. people_max 는 하루에 가장 많이 든 사람 수, days 는 요청이 있던 날 수다. 정문 로그는 "
                    "14일 뒤 사라져 접어 둔 날부터만 남는다. "
                    + (f"접어 둔 첫 날({meta['first']}) 전은 null 이다." if meta["first"] else "접어 둔 날이 아직 없다.")
                    + _today_note(meta) + _stale(meta)}


def _snapshots(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    snap: dict[str, dict] = {}
    for d, metric, dims, v in _fold_rows(c, x, "snapshot"):
        r = snap.setdefault(d, {"pats_live": 0, "pats_personal": 0, "pats_exchanged": 0, "connections": 0, "accounts_active": 0, "grants": 0})
        if metric == "pats_live":
            r["pats_live"] += int(v)
            r["pats_personal" if dims.get("kind") == "personal" else "pats_exchanged"] += int(v)
        elif metric == "connections":
            r["connections"] += int(v)
        elif metric == "accounts" and dims.get("status") == "active":
            r["accounts_active"] += int(v)
        elif metric == "grants":
            r["grants"] += int(v)
    issued: dict[str, int] = defaultdict(int)
    for d, metric, _dims, v in _fold_rows(c, x, "portal"):
        if metric == "pat_issued":
            issued[d] += int(v)
    first = _fold_meta(c, x, "portal")["first"]
    blank = dict.fromkeys(("pats_live", "pats_personal", "pats_exchanged", "connections", "accounts_active", "grants"))
    rows = [{"day": d, **(snap.get(d) or blank), "pats_issued": None if first is None or d < first else issued.get(d, 0)} for d in x.w.axis()]
    return {"rows": rows, "days": len(snap),
            "note": "날마다 찍어 둔 '지금 상태' 다 — 살아 있는 PAT(폐기 · 만료 빼고) · 외부 연결 · 쓰는 계정 · 개별 허가(소속 밖으로 한 사람에게 연 "
                    "기능 · 플랫폼 키의 수 — 쓰는 계정의 것). 그날 포털이 마지막으로 접은 때의 값이고, "
                    "찍지 못한 날(접기 전 · 포털이 내려가 있던 날)은 null 이다 — 지난 날의 상태는 다시 셀 수 없다. pats_issued 는 그날 낸 PAT 이다 — "
                    "닫힌 날의 수는 그 뒤에 만료로 지워져도 남는다."}


def _conversations_kept(c: sqlite3.Connection, x: _Ctx) -> dict:
    if not _has_fold(c):
        return _pending()
    got: dict[tuple[str, str], int] = defaultdict(int)
    for _d, metric, dims, v in _fold_rows(c, x, "portal"):
        if metric == "conversations":
            got[(str(dims.get("kind") or ""), str(dims.get("source") or ""))] += int(v)
    rows = sorted(({"kind": k, "source": s, "n": n} for (k, s), n in got.items()), key=lambda r: (-r["n"], r["kind"], r["source"]))
    return {"rows": rows,
            "note": "접어 둔 새 대화 수다(만든 날 기준 · 종류 × 출처). 닫힌 날(사흘 지난 날)의 수는 그 뒤에 주인이 대화를 지워도 남는다 — 위의 "
                    "대화 칸(지금 남은 대화)과 차이가 지운 대화다. 접기 전에 이미 지워진 대화는 여기에도 없다."}


def _has_table(c: sqlite3.Connection, name: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def _llm_since(c: sqlite3.Connection) -> str | None:
    """에이전트 서버가 사람별 LLM 토큰을 적기 시작한 날 — 접는 쪽이 그 날의 표지 줄로 남긴다(그 전 날은 0 이 아니라 기록 전이다)."""
    got = c.execute("SELECT MIN(day) FROM usage_daily WHERE source = 'agent' AND metric = 'llm_since'").fetchone()
    return got[0] if got else None


def _llm_people(c: sqlite3.Connection, x: _Ctx) -> dict[str, dict]:
    """기간 안의 사람별 LLM 토큰(usage_llm_daily — 뺄 계정은 여기서 뺀다) — {이메일: {calls, unknown, tokens_in, tokens_out, cache_read}}."""
    if "llm_people" not in x.memo:
        out: dict[str, dict] = {}
        if _has_table(c, "usage_llm_daily"):
            q, a = _not_in(x.ex, "email")
            for email, calls, unknown, tin, tout, cache in c.execute(
                    "SELECT email, SUM(calls), SUM(unknown), SUM(tokens_in), SUM(tokens_out), SUM(cache_read) FROM usage_llm_daily"
                    f" WHERE day >= ? AND day <= ? AND email != ''{q} GROUP BY email", (x.w.first.isoformat(), x.w.last.isoformat(), *a)):
                out[email] = {"calls": calls, "unknown": unknown, "tokens_in": tin, "tokens_out": tout, "cache_read": cache}
        x.memo["llm_people"] = out
    return x.memo["llm_people"]


def _people(c: sqlite3.Connection, x: _Ctx) -> dict:
    """사람별 이용 — 관리자 화면에서 이메일이 나오는 유일한 칸(사용자 결정 2026-11-22 · OD-55). 사람 줄(usage_actor_daily)과 사람별 LLM 토큰
    (usage_llm_daily)을 기간으로 더한다. 뺄 계정은 읽을 때 뺀다 · 두 표 모두 400일 보존."""
    if not _has_fold(c):
        return _pending()
    labels = x.labels.get("affiliation") or {}
    keys = ("login", "chat", "tile", "mcp", "engine", "ra", "delib", "nginx")
    per: dict[str, dict] = {}

    def row(email: str) -> dict:
        return per.setdefault(email, {"email": email, "affiliation": "", "days": set(), **dict.fromkeys(keys, 0)})
    for day, email, source, n in _actor_rows(c, x):
        r = row(email)
        r["days"].add(day)
        if source in ("ra", "ra-for"):
            r["ra"] += n                # RA 초안 — 도구 호출(mcp · engine)에 이미 든 호출 가운데 초안을 만든 수다
        else:
            r[_group_of(source)] += n
    q, a = _not_in(x.ex, "email")
    for email, aff in c.execute(f"SELECT email, affiliation FROM usage_actor_daily WHERE day >= ? AND day <= ? AND affiliation != ''{q}"
                                " ORDER BY day", (x.w.first.isoformat(), x.w.last.isoformat(), *a)):
        if email in per:
            per[email]["affiliation"] = aff                     # 기간 안의 가장 늦은 날의 소속(그때의 소속)
    for email, t in _llm_people(c, x).items():
        row(email).update({f"llm_{k}": v for k, v in t.items()})
    rows = []
    for r in per.values():
        days = sorted(r.pop("days"))
        aff = r["affiliation"]
        rows.append({**r, "affiliation_label": labels.get(aff, aff) if aff else "", "active_days": len(days),
                     "first_day": days[0] if days else None, "last_day": days[-1] if days else None,
                     **{f"llm_{k}": r.get(f"llm_{k}", 0) for k in ("calls", "unknown", "tokens_in", "tokens_out", "cache_read")}})
    rows.sort(key=lambda r: (-r["active_days"], -(r["chat"] + r["mcp"] + r["delib"] + r["llm_calls"]), r["email"]))
    return {"rows": rows[:PEOPLE_MAX], "total": len(rows), "truncated": len(rows) > PEOPLE_MAX,
            "note": "사람마다 기간 안의 이용이다 — 관리자 화면에서 이메일이 나오는 칸은 이것 하나다(사용자 결정 2026-11-22). login · chat · tile 은 그 "
                    "사건 수, mcp 는 그 사람이 부른 MCP 도구 호출, engine 은 호출자가 빈 엔진 호출을 '누구의 일' 감사 머리로 그 사람에게 이은 수(검증하지 "
                    "않은 주장), ra 는 그 가운데 Report Archive 초안, delib 은 MCP 로 맡긴 심의 잡, nginx 는 정문 요청, llm_* 는 에이전트 서버가 그 사람의 "
                    "일로 부른 LLM 호출과 토큰이다(llm_unknown 은 사용량이 오지 않은 호출). active_days 는 무엇이든 쓴 날 수, affiliation 은 기간 안 "
                    "마지막 날의 소속이다. 사람 줄과 토큰은 400일 뒤 지운다."
                    + (f" 상위 {PEOPLE_MAX}명만 실었다(전체 {len(rows)}명)." if len(rows) > PEOPLE_MAX else "")}


def _llm_tokens(c: sqlite3.Connection, x: _Ctx) -> dict:
    """사람을 뺀 LLM 토큰 합 — 종류 × 모델 · 날마다(usage_daily — 접을 때 뺄 계정을 뺐다)."""
    if not _has_fold(c):
        return _pending()
    meta, since = _fold_meta(c, x, "agent"), _llm_since(c)
    by: dict[tuple[str, str], dict] = {}
    daily: dict[str, int] = defaultdict(int)
    names = {"llm_calls": "calls", "llm_unknown": "unknown", "llm_in": "tokens_in", "llm_out": "tokens_out", "llm_cache": "cache_read"}
    for d, metric, dims, v in _fold_rows(c, x, "agent"):
        k = names.get(metric)
        if k is None:
            continue
        r = by.setdefault((str(dims.get("kind") or "other"), str(dims.get("model") or "(unknown)")),
                          dict.fromkeys(("calls", "unknown", "tokens_in", "tokens_out", "cache_read"), 0))
        r[k] += int(v)
        if k in ("tokens_in", "tokens_out"):
            daily[d] += int(v)
    order = {k: i for i, k in enumerate(LLM_KINDS)}
    rows = sorted(({"kind": k, "model": m, **r} for (k, m), r in by.items()),
                  key=lambda r: (order.get(r["kind"], len(order)), -(r["tokens_in"] + r["tokens_out"]), r["model"]))
    tot = {k: sum(r[k] for r in rows) for k in ("calls", "unknown", "tokens_in", "tokens_out", "cache_read")}
    return {"rows": rows, "daily": _series(x.w.axis(), since, daily), "since": since,
            "totals": {**tot, "people": len(_llm_people(c, x))},
            "note": "에이전트 서버가 부른 LLM 호출의 토큰이다(챗 · 띵킹 · 심의 · 루틴 · 카드 대조 · 그 밖 × 모델). daily 는 날마다 입력 + 출력 토큰이다. "
                    "unknown 은 사용량이 오지 않은 호출이다 — 흘려 받는 호출(에이전트 서버 LLM_STREAM_USAGE 를 켜기 전) · 외부 응답자(Claude 워크플로)는 "
                    "토큰을 모른다(지어내지 않는다). 다른 서비스(AIDataHub · SignalForge 등)가 같은 LLM 을 바로 부른 것은 들지 않는다. "
                    + (f"에이전트 서버가 적기 시작한 날({since}) 전은 null 이다." if since else
                       "에이전트 서버가 아직 토큰을 내지 않았다(그쪽이 이 판보다 낡았거나 아직 접지 않았다) — 날마다 칸은 null 이다.")
                    + _today_note(meta) + _stale(meta)}


# 칸 이름 · 원장 · 셈 — 이 차례로 낸다(화면도 이 차례다)
_SECTIONS: tuple[tuple[str, str, Callable[[sqlite3.Connection, _Ctx], dict]], ...] = (
    ("logins_daily", "audit", _logins_daily),
    ("logins_weekly", "audit", lambda c, x: _logins_span(c, x, "week")),
    ("logins_monthly", "audit", lambda c, x: _logins_span(c, x, "month")),
    ("logins_method", "audit", _logins_method),
    ("accounts_status", "users", _accounts_status),
    ("accounts_affiliation", "users", _accounts_affiliation),
    ("accounts_new", "users", _accounts_new),
    ("tiles", "audit", _tiles),
    ("chat_daily", "audit", _chat_daily),
    ("chat_kinds", "audit", _chat_kinds),
    ("chat_errors", "audit", _chat_errors),
    ("events", "audit", _events),
    ("conversations", "conv", _conversations),
    ("procedure_runs", "procedures", _procedure_runs),
    ("routine_runs", "procedures", _routine_runs),
    ("pats_live", "tokens", _pats_live),
    ("pats_weekly", "tokens", _pats_weekly),
    ("access_requests", "users", _access_requests),
    ("connections", "users", _connections),
    # ── 접어 둔 표(M2) ──
    ("fold_status", "audit", _fold_status),
    ("active_daily", "audit", _active_daily),
    ("active_weekly", "audit", lambda c, x: _active_span(c, x, "week")),
    ("active_monthly", "audit", lambda c, x: _active_span(c, x, "month")),
    ("mcp_daily", "audit", _mcp_daily),
    ("mcp_via", "audit", _mcp_via),
    ("mcp_apps", "audit", _mcp_apps),
    ("mcp_tools", "audit", _mcp_tools),
    ("mcp_auth", "audit", _mcp_auth),
    ("mcp_personal_weekly", "audit", _mcp_personal_weekly),
    ("delib_jobs", "audit", _delib_jobs),
    ("ra_drafts", "audit", _ra_drafts),
    ("front_door", "audit", _front_door),
    ("snapshots", "audit", _snapshots),
    ("conversations_kept", "audit", _conversations_kept),
    ("llm_tokens", "audit", _llm_tokens),
    ("people", "audit", _people),
)


def _sources(settings: Settings) -> dict[str, str]:
    """원장 → 설정의 경로(포털 저장소가 여는 바로 그 설정이다 — 경로를 따로 두지 않는다)."""
    return {"audit": settings.agent_audit_log_path, "users": settings.user_store_path, "tokens": settings.token_store_path,
            "conv": settings.conv_store_path, "procedures": settings.procedures_store_path}


def _ro(path: str) -> sqlite3.Connection:
    """읽기 전용 연결 — 없는 파일을 만들지 않고, 쓰지 못한다. 잠금 대기는 sqlite3 기본(5초)."""
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def _broken(exc: Exception) -> dict:
    return {"rows": [], "error": True, "note": f"이 원장을 읽지 못했다 — {type(exc).__name__}: {str(exc)[:160]}"}


def build(settings: Settings, *, days: int = DEFAULT_DAYS, now: float | None = None, labels: dict | None = None) -> dict:
    """관리자 이용 통계 한 판. 이벤트 루프 밖에서 부른다(원장마다 읽기 전용 연결을 이 스레드에서 열고 닫는다).

    labels — {"service": 타일 id → 이름, "affiliation": 소속 id → 라벨, "key": 권한 키 → 라벨}(없으면 id 그대로)."""
    now = time.time() if now is None else now
    eff = clamp_days(days)
    w = Window.of(eff, now)
    ex = excluded_accounts(settings)
    x = _Ctx(w=w, now=int(now), ex=ex, labels=labels or {}, refresh_h=max(1, round(settings.jwt_refresh_ttl / 3600)))
    sections: dict[str, dict] = {}
    with ExitStack() as stack:
        conns: dict[str, sqlite3.Connection | Exception] = {}
        for name, rel in _sources(settings).items():
            try:
                conns[name] = stack.enter_context(closing(_ro(settings.resolve(rel))))
            except sqlite3.Error as exc:
                conns[name] = exc
        for name, src, fn in _SECTIONS:
            c = conns[src]
            if isinstance(c, Exception):
                sections[name] = _broken(c)
                continue
            try:
                sections[name] = fn(c, x)
            except sqlite3.Error as exc:
                sections[name] = _broken(exc)
    return {
        "generated_at": int(now),
        "range": {"days": eff, "requested_days": days, "clamped": eff != days, "max_days": MAX_DAYS, "default_days": DEFAULT_DAYS,
                  "first_day": w.first.isoformat(), "last_day": w.last.isoformat(), "since": w.since, "until": w.until,
                  "tz": "Asia/Seoul", "axis": w.axis()},
        "excluded": {"accounts": ex, "setting": SETTING, "primer": True,
                     "note": ("자동 SSO 예열 줄(primer)은 늘 뺀다. "
                              + (f"설정 {SETTING} 의 계정 {len(ex)}개(시험 · 서비스 계정)를 모든 칸에서 뺐다 — 이메일과 주체로 견준다. 날마다 "
                                 "접어 둔 합계(MCP · 심의 · 정문 · 새 대화 · PAT)는 접을 때의 목록으로 셌다 — 목록을 바꾸면 게이트웨이 · 에이전트 서버 "
                                 "쪽은 다음 접기에 지난 날까지 다시 세고, 포털 · 정문 쪽은 아직 닫히지 않은 날부터 반영된다(접기 상태 칸)."
                                 if ex else f"뺀 계정은 없다 — 시험 · 서비스 계정을 빼려면 backend/.env 의 {SETTING} 에 쉼표로 적고 포털을 다시 "
                                            "띄운다."))},
        "sections": sections,
    }
