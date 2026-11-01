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
"""
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


def excluded_accounts(settings: Settings) -> list[str]:
    raw = getattr(settings, "usage_exclude_accounts", "") or ""
    return sorted({a.strip().lower() for a in raw.split(",") if a.strip()})


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
            "note": "포털 챗 턴이다(웹 · PAT — 시작 줄). 챗 · 심의 · 띵킹 · 루틴을 가르지 않는다(턴 종류를 적지 않는다 — M3). done 은 끝까지 "
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
    return {"rows": out, "completion": overall,
            "note": "기간 안에 시작한 분석 루틴 실행이다(실행기 mcp · chat · web × 상태). completion 은 끝난 실행 가운데 done 의 몫이다 — "
                    "도는 중 · 사람을 기다리는 실행은 빼고, interrupted(실행자가 사라짐)는 끝난 쪽으로 센다."}


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
    ("chat_errors", "audit", _chat_errors),
    ("events", "audit", _events),
    ("conversations", "conv", _conversations),
    ("procedure_runs", "procedures", _procedure_runs),
    ("routine_runs", "procedures", _routine_runs),
    ("pats_live", "tokens", _pats_live),
    ("pats_weekly", "tokens", _pats_weekly),
    ("access_requests", "users", _access_requests),
    ("connections", "users", _connections),
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
                              + (f"설정 {SETTING} 의 계정 {len(ex)}개(시험 · 서비스 계정)를 모든 칸에서 뺐다 — 이메일과 주체로 견준다."
                                 if ex else f"뺀 계정은 없다 — 시험 · 서비스 계정을 빼려면 backend/.env 의 {SETTING} 에 쉼표로 적고 포털을 다시 "
                                            "띄운다."))},
        "sections": sections,
    }
