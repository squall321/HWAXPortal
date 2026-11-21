# 이용 통계의 날마다 접는 표(usage_daily · usage_actor_daily) — 포털 원장 · 정문 로그 · 게이트웨이 · 에이전트 서버를 KST 날로 접어 둔다(docs/ops-dashboard M2)
"""M1 은 원장을 읽을 때 센다. 그런데 사라지는 원천이 있고(만료 PAT · 지운 대화 · 정문 로그 14일) 포털이 열 수 없는 원천이 있다(게이트웨이 감사 ·
에이전트 서버 잡 원장). 그래서 날마다 접어 감사 원장 파일(agent_audit.sqlite — 이미 등록된 자료 칸 · 이미 백업된다) 안의 표에 둔다(PLAN §2.4).

표.
  · usage_daily(day, source, metric, dims, value) — 날 × 원천 × 지표 × 칸(JSON, 열쇠 정렬)마다 수. 사람(이메일)은 싣지 않는다.
  · usage_actor_daily(day, email, source, n, affiliation) — 날 × 사람 × 갈래마다 수와 그때의 소속. 관리자만 읽는다 · 400일 뒤 지운다(OD-4).
  · usage_fold(day, source, folded_at, final, ex, note) — 접은 기록. day='*' 는 그 원천의 마지막 시도(note 가 실패 까닭)다.

원천(source).
  · portal — 접속 · 감사 원장의 사람 줄(login · chat · tile)과 사라지는 수(날마다 새 대화 · 낸 PAT).
  · snapshot — 오늘의 '지금 상태'(살아 있는 PAT · 외부 연결 · 계정 · 개별 허가). 오늘 날에만 적는다 — 지난 날은 다시 셀 수 없다.
  · nginx — 정문 접근 로그의 서비스별 요청 · 사람(로그인 연결 ID 로 잇는다 — 귀속이지 증명이 아니다).
  · gateway — 게이트웨이 창구 POST /usage-rollup(MCP 도구 호출 · 인증 실패 · 사람별 호출 수 · RA 초안).
  · agent — 에이전트 서버 창구 POST /usage-rollup(MCP 심의 잡).

언제.
  · 오늘은 돌 때마다 다시 접는다(아직 안 끝난 날 — final 0). 끝난 날은 사흘 동안 날마다 한 번 다시 접고(끝난 날 + 앞 이틀 — 늦게 끝난 잡 · 실행이
    든다) 사흘째에 닫는다(final 1). 닫힌 날은 다시 접지 않는다 — 그 뒤에 지워진 대화 · PAT · 정문 로그가 수를 줄이지 않는다.
  · 기록이 없는 날은 원천의 첫 날부터(400일 안에서) 채운다 — 기동 때 밀린 날이 그렇게 채워진다. 같은 날을 다시 접어도 같은 줄이다(지우고 넣는다).
  · 뺄 계정(USAGE_EXCLUDE_ACCOUNTS)은 접을 때 뺀다(usage_daily 는 사람을 싣지 않아 읽을 때 뺄 수 없다). 게이트웨이 · 에이전트 서버는 그쪽 원장이
    무기한이라 목록이 바뀌면 닫힌 날도 다시 접는다. 포털 · 정문 쪽은 닫힌 날을 다시 세지 않는다(사라진 줄을 잃는다). 사람 줄은 읽을 때 뺀다.

실패. 접기는 요청과 떨어진 백그라운드 작업이다 — 원천 하나가 실패해도(게이트웨이가 낡았다 · 닿지 않는다) 다른 원천은 접고, 포털 기동 · 요청을 막지
않는다. 실패 까닭은 usage_fold 의 day='*' 줄과 로그에 남고 화면이 보인다. sqlite 일은 이벤트 루프 밖(스레드)에서, 제 연결로 한다 — 감사 쓰기의 연결 ·
파이썬 잠금을 빌리지 않고, 쓰는 트랜잭션은 날 하나씩 짧게 연다.
"""
from __future__ import annotations

import asyncio
import bisect
import contextlib
import gzip
import json
import logging
import sqlite3
import time
import zlib
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from app.auth.cookies import UID_MAX_AGE
from app.auth.routes.access_history import _LINE, NGINX_KEEP_DAYS, _log_files, _service_of
from app.config import Settings
from app.usage_stats import (
    _ACCESS,
    FOLD_NOCOVER,
    KST,
    LAT_LE_MS,
    MAX_DAYS,
    RA_DRAFT_TOOL,
    _day,
    _not_in,
    _ro,
    excluded_accounts,
    fingerprint,
    kst_day,
)

logger = logging.getLogger(__name__)

SOURCES = ("portal", "snapshot", "nginx", "gateway", "agent")
SETTLE_DAYS = 3                 # 끝난 날은 사흘째에 닫는다(끝난 날 + 앞 이틀 — PLAN §2.4)
RETAIN_ACTOR_DAYS = MAX_DAYS    # 사람별 줄의 보존(OD-4 — 400일)
FIRST_DELAY_S = 30.0            # 기동 뒤 첫 접기까지 — 기동을 붙들지 않는다
REMOTE_ASKS = 12                # 한 번 도는 동안 그쪽에 묻는 횟수의 위쪽(되채우기 조각 · 게이트웨이가 원장을 덜 접어 다시 묻는 것) — 남으면 다음에 잇는다
SPAN_DAYS = 60                  # 한 물음의 기간 — 400일 되채우기를 한 답으로 받지 않는다
GATEWAY_TIMEOUT_S = 90.0        # 게이트웨이의 한 물음은 20초까지 접는다(usage_rollup.BUDGET_S) — 그보다 넉넉히
AGENT_TIMEOUT_S = 60.0
REPEAT_EVERY = 24               # 같은 실패가 이어질 때 다시 적는 간격(도는 횟수)
PATH = "/usage-rollup"
NOCOVER = FOLD_NOCOVER          # 정문 로그가 그날을 덮지 않는다(회전으로 사라졌다) — 접은 기록만 두고 값은 없다

SCHEMA = (
    "CREATE TABLE IF NOT EXISTS usage_daily (day TEXT NOT NULL, source TEXT NOT NULL, metric TEXT NOT NULL, dims TEXT NOT NULL DEFAULT '',"
    " value REAL NOT NULL, PRIMARY KEY (day, source, metric, dims)) WITHOUT ROWID",
    "CREATE TABLE IF NOT EXISTS usage_actor_daily (day TEXT NOT NULL, email TEXT NOT NULL, source TEXT NOT NULL, n INTEGER NOT NULL,"
    " affiliation TEXT NOT NULL DEFAULT '', PRIMARY KEY (day, email, source)) WITHOUT ROWID",
    "CREATE TABLE IF NOT EXISTS usage_fold (day TEXT NOT NULL, source TEXT NOT NULL, folded_at INTEGER NOT NULL, final INTEGER NOT NULL,"
    " ex TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', PRIMARY KEY (day, source)) WITHOUT ROWID",
)
# 원천이 쓰는 사람 줄의 갈래 — 그 원천의 날을 다시 접을 때 이 갈래만 지운다
_ACTOR_WHERE = {
    "portal": "source IN ('login', 'chat', 'tile')",
    "snapshot": "0",
    "nginx": "source = 'nginx'",
    "gateway": "(source = 'ra' OR source = 'mcp' OR source LIKE 'mcp-%')",
    "agent": "source = 'delib'",
}
_REFOLD_ON_EX = {"gateway", "agent"}        # 원장이 무기한이라 뺄 계정 목록이 바뀌면 닫힌 날도 다시 접는다
_HTTP_WHY = {
    401: "공유 비밀(GATEWAY_SHARED_TOKEN)이 그쪽 것과 다르다(HTTP 401)",
    403: "그쪽이 서비스 호출로 받지 않았다(HTTP 403)",
    404: "그쪽 판이 낡았다 — 이용 통계 창구(/usage-rollup)가 없다(HTTP 404 · 업데이트 · 재기동 뒤 채워진다)",
    405: "그쪽 판이 낡았다 — 이용 통계 창구(/usage-rollup)가 없다(HTTP 405 · 업데이트 · 재기동 뒤 채워진다)",
    503: "그쪽에 공유 비밀이 없다(HTTP 503)",
}


class FoldError(Exception):
    """원천 하나를 접지 못한 까닭 — 사람이 읽는 글(비밀 · 주소는 싣지 않는다)."""


@dataclass
class DayFold:
    """한 날 · 한 원천의 접은 줄 — rows 는 (지표, 칸, 값), actors 는 (이메일, 갈래, 수, 그때의 소속)."""
    rows: list[tuple[str, dict, float]] = field(default_factory=list)
    actors: list[tuple[str, str, int, str]] = field(default_factory=list)
    note: str = ""


def dims_text(dims: dict) -> str:
    return json.dumps(dims, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if dims else ""


def _midnight(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=KST).timestamp())


def connect(settings: Settings) -> sqlite3.Connection:
    """접는 표를 쓰는 제 연결 — 감사 원장 파일 안에 표를 만든다(없으면). 잠금은 30초까지 기다린다."""
    path = Path(settings.resolve(settings.agent_audit_log_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0, isolation_level=None)
    for ddl in SCHEMA:
        conn.execute(ddl)
    return conn


def _done(conn: sqlite3.Connection, source: str) -> dict[str, tuple[int, int, str, str]]:
    return {d: (at, fin, ex, note) for d, at, fin, ex, note in conn.execute(
        "SELECT day, folded_at, final, ex, note FROM usage_fold WHERE source = ? AND day != '*'", (source,))}


def due_days(done: dict, first: str | None, today: date, fp: str, *, refold_ex: bool, floor: date | None = None) -> list[str]:
    """다시 접을 날 — 기록이 없는 날 · 오늘 · 닫히지 않았고 오늘 아직 안 접은 날 · (무기한 원천이면) 다른 목록으로 접은 날. first 가 없으면 없다."""
    if not first:
        return []
    lo = max(date.fromisoformat(first), today - timedelta(days=MAX_DAYS - 1), floor or date.min)
    start_today = _midnight(today)
    out, d = [], lo
    while d <= today:
        rec = done.get(d.isoformat())
        if rec is None or d == today or (not rec[1] and rec[0] < start_today) or (refold_ex and rec[2] != fp):
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def write_day(conn: sqlite3.Connection, source: str, day: str, fold: DayFold, *, today: date, fp: str, now: float) -> None:
    """한 날 · 한 원천을 바꿔 쓴다(지우고 넣는다 — 다시 접어도 같은 줄). 닫는 판정은 여기서 한다."""
    final = int((today - date.fromisoformat(day)).days >= SETTLE_DAYS)
    rows: dict[tuple[str, str], float] = defaultdict(float)
    for metric, dims, value in fold.rows:
        rows[(metric, dims_text(dims))] += value
    actors: dict[tuple[str, str], list] = {}
    for email, kind, n, aff in fold.actors:
        a = actors.setdefault((email, kind), [0, ""])
        a[0] += n
        a[1] = aff or a[1]
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM usage_daily WHERE day = ? AND source = ?", (day, source))
        conn.executemany("INSERT INTO usage_daily VALUES (?, ?, ?, ?, ?)", [(day, source, m, d, v) for (m, d), v in rows.items() if v])
        conn.execute(f"DELETE FROM usage_actor_daily WHERE day = ? AND {_ACTOR_WHERE[source]}", (day,))  # noqa: S608 — 고정 글자
        conn.executemany("INSERT OR REPLACE INTO usage_actor_daily VALUES (?, ?, ?, ?, ?)",
                         [(day, e, k, n, aff[:80]) for (e, k), (n, aff) in actors.items() if n > 0])
        conn.execute("INSERT OR REPLACE INTO usage_fold VALUES (?, ?, ?, ?, ?, ?)", (day, source, int(now), final, fp, fold.note[:200]))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def mark(conn: sqlite3.Connection, source: str, now: float, error: str = "") -> None:
    """그 원천의 마지막 시도 — 실패면 까닭을 남기고, 되면 비운다(day='*')."""
    conn.execute("INSERT OR REPLACE INTO usage_fold VALUES ('*', ?, ?, 0, '', ?)", (source, int(now), error[:300]))


def _affiliations(settings: Settings) -> dict[str, str]:
    """이메일 → 지금 소속(접는 때의 값이 '그때의 소속' 이다). 못 읽으면 빈 표."""
    try:
        with closing(_ro(settings.resolve(settings.user_store_path))) as c:
            return {str(e).lower(): str(a or "") for e, a in c.execute("SELECT email, affiliation FROM users")}
    except sqlite3.Error:
        return {}


def _email(v) -> str:
    s = str(v or "").strip().lower()
    return s if "@" in s and len(s) <= 200 else ""


# ── portal — 접속 · 감사의 사람 줄 · 사라지는 수 ───────────────────────────────────────────────────────────────────────────────────
def _portal_first(settings: Settings) -> str | None:
    """포털 원장들의 가장 이른 줄의 날(KST)."""
    marks = []
    for attr, sql in (("agent_audit_log_path", "SELECT MIN(ts) FROM access_log"), ("agent_audit_log_path", "SELECT MIN(ts) FROM agent_audit"),
                      ("conv_store_path", "SELECT MIN(created_at) FROM conversations"), ("token_store_path", "SELECT MIN(created) FROM pat")):
        try:
            with closing(_ro(settings.resolve(getattr(settings, attr)))) as c:
                v = c.execute(sql).fetchone()[0]
        except sqlite3.Error:
            continue
        if v is not None:
            marks.append(v)
    return kst_day(min(marks)) if marks else None


def portal_days(settings: Settings, days: list[str], ex: list[str]) -> dict[str, DayFold]:
    """포털 원장에서 그 날들을 센다 — 사람 줄(login · chat · tile — 뺄 계정은 읽을 때 뺀다)과 사라지는 수(새 대화 · 낸 PAT — 접을 때 뺀다)."""
    out = {d: DayFold() for d in days}
    if not days:
        return out
    lo, hi = _midnight(date.fromisoformat(days[0])), _midnight(date.fromisoformat(days[-1]) + timedelta(days=1))
    aff = _affiliations(settings)
    with closing(_ro(settings.resolve(settings.agent_audit_log_path))) as c:
        for d, email, n_login, n_tile in c.execute(
                f"SELECT {_day('ts')} d, lower(email), SUM(event = 'login'), SUM(event IN ('launch', 'open')) FROM access_log"
                f" WHERE {_ACCESS} AND event IN ('login', 'launch', 'open') GROUP BY d, 2", (lo, hi)):
            e = _email(email)
            if d in out and e:
                out[d].actors += [(e, "login", n_login or 0, aff.get(e, "")), (e, "tile", n_tile or 0, aff.get(e, ""))]
        for d, who, n in c.execute(f"SELECT {_day('ts')} d, lower(principal), COUNT(*) FROM agent_audit WHERE ts >= ? AND ts < ?"
                                   " AND event = 'chat_start' GROUP BY d, 2", (lo, hi)):
            e = _email(who)
            if d in out and e:
                out[d].actors.append((e, "chat", n, aff.get(e, "")))
    try:
        q, a = _not_in(ex, "owner_sub")
        with closing(_ro(settings.resolve(settings.conv_store_path))) as c:
            for d, kind, src, n, owners in c.execute(
                    f"SELECT {_day('created_at')} d, kind, source, COUNT(*), COUNT(DISTINCT lower(owner_sub)) FROM conversations"
                    f" WHERE created_at >= ? AND created_at < ?{q} GROUP BY d, kind, source", (lo, hi, *a)):
                if d in out:
                    dims = {"kind": str(kind)[:40], "source": str(src)[:20]}
                    out[d].rows += [("conversations", dims, n), ("conv_owners", dims, owners)]
        q, a = _not_in(ex, "sub", "email")
        with closing(_ro(settings.resolve(settings.token_store_path))) as c:
            for d, own, n in c.execute(f"SELECT {_day('created')} d, parent_jti IS NULL, COUNT(*) FROM pat WHERE created >= ? AND created < ?{q}"
                                       " GROUP BY d, 2", (lo, hi, *a)):
                if d in out:
                    out[d].rows.append(("pat_issued", {"kind": "personal" if own else "exchanged"}, n))
    except sqlite3.Error as exc:
        raise FoldError(f"대화 · 토큰 원장을 읽지 못했다({type(exc).__name__})") from exc
    return out


def snapshot_day(settings: Settings, now: float, ex: list[str]) -> DayFold:
    """오늘의 '지금 상태' — 살아 있는 PAT · 외부 연결 · 계정 상태 · 개별 허가(뺄 계정은 뺀다). 지난 날의 값은 다시 셀 수 없어 오늘에만 적는다."""
    fold = DayFold()
    q, a = _not_in(ex, "sub", "email")
    with closing(_ro(settings.resolve(settings.token_store_path))) as c:
        for own, n, owners in c.execute(f"SELECT parent_jti IS NULL, COUNT(*), COUNT(DISTINCT lower(sub)) FROM pat WHERE revoked = 0"
                                        f" AND exp >= ?{q} GROUP BY 1", (int(now), *a)):
            dims = {"kind": "personal" if own else "exchanged"}
            fold.rows += [("pats_live", dims, n), ("pat_owners", dims, owners)]
    q, a = _not_in(ex, "email")
    with closing(_ro(settings.resolve(settings.user_store_path))) as c:
        for svc, n in c.execute(f"SELECT service, COUNT(*) FROM connections WHERE 1=1{q} GROUP BY service", a):
            fold.rows.append(("connections", {"service": str(svc)[:60]}, n))
        for status, n in c.execute(f"SELECT status, COUNT(*) FROM users WHERE 1=1{q} GROUP BY status", a):
            fold.rows.append(("accounts", {"status": str(status)[:20]}, n))
        granted: dict[str, int] = defaultdict(int)          # 개별 허가(소속 밖으로 한 사람에게 연 기능 · 플랫폼 키) — 쓰는 계정의 것만
        for (raw,) in c.execute(f"SELECT grants FROM users WHERE status = 'active'{q}", a):
            try:
                keys = json.loads(raw or "[]")
            except ValueError:
                continue
            for k in {str(k) for k in keys} if isinstance(keys, list) else ():
                granted[k[:80]] += 1
        fold.rows += [("grants", {"key": k}, n) for k, n in granted.items()]
    return fold


# ── nginx — 정문 접근 로그 ───────────────────────────────────────────────────────────────────────────────────────────────────────
def nginx_days(settings: Settings, days: list[str], ex: list[str], service_ids: set[str]) -> tuple[dict[str, DayFold], float | None, int]:
    """정문 로그에서 그 날들을 센다 → (날마다 접은 줄, 읽은 로그의 가장 이른 줄의 시각, 못 읽은 파일 수). 로그인 연결 ID(hwax_uid)를 접속 원장의
    로그인 줄과 이어 사람에게 붙인다 — 붙지 않는 요청(로그인 전 · 스캐너 · PAT)은 수만 센다."""
    out = {d: DayFold() for d in days}
    if not days:
        return out, None, 0
    want = set(days)
    lo = _midnight(date.fromisoformat(days[0]))
    logins: dict[str, list[tuple[int, str]]] = defaultdict(list)
    with closing(_ro(settings.resolve(settings.agent_audit_log_path))) as c:
        for uid, email, ts in c.execute("SELECT uid, lower(email), ts FROM access_log WHERE ts >= ? AND event = 'login' AND uid IS NOT NULL"
                                        " ORDER BY ts", (lo - UID_MAX_AGE,)):
            logins[uid].append((ts, email))
    aff = _affiliations(settings)
    skip = set(ex)
    req: dict[tuple[str, str], int] = defaultdict(int)
    people: dict[tuple[str, str], set] = defaultdict(set)
    per_person: dict[tuple[str, str], int] = defaultdict(int)
    loose: dict[str, int] = defaultdict(int)
    earliest, failed = None, 0
    for f in _log_files(Path(settings.resolve(settings.nginx_access_log_path)), lo):
        opener = gzip.open if f.suffix == ".gz" else open
        try:
            with opener(f, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = _LINE.match(line)
                    if not m:
                        continue
                    _ip, t, _method, path, _status, uid = m.groups()
                    try:
                        ts = datetime.fromisoformat(t).timestamp()
                    except ValueError:
                        continue
                    earliest = ts if earliest is None or ts < earliest else earliest
                    d = kst_day(ts)
                    if d not in want:
                        continue
                    seen = logins.get(uid)
                    if not seen:
                        loose[d] += 1
                        continue
                    i = bisect.bisect_right(seen, (int(ts), "￿")) - 1      # 그 요청보다 앞선 마지막 로그인(없으면 가장 이른 것)
                    who = _email(seen[max(i, 0)][1])
                    if not who:
                        loose[d] += 1
                        continue
                    per_person[(d, who)] += 1
                    if who in skip:
                        continue
                    svc = _service_of(path, service_ids)[:80]
                    req[(d, svc)] += 1
                    people[(d, svc)].add(who)
        except (OSError, EOFError, zlib.error, UnicodeDecodeError):
            failed += 1
    for (d, svc), n in req.items():
        out[d].rows += [("requests", {"service": svc}, n), ("people", {"service": svc}, len(people[(d, svc)]))]
    for d, n in loose.items():
        out[d].rows.append(("unattributed", {}, n))
    for (d, who), n in per_person.items():
        out[d].actors.append((who, "nginx", n, aff.get(who, "")))
    return out, earliest, failed


# ── gateway · agent — 공유 비밀 창구 ────────────────────────────────────────────────────────────────────────────────────────────────
def gateway_days(resp: dict, days: list[str], aff: dict[str, str]) -> dict[str, DayFold]:
    """게이트웨이 창구의 답 → 날마다 접은 줄. 꼴이 다르면 FoldError."""
    try:
        if list((resp.get("rules") or {}).get("lat_le_ms") or []) != list(LAT_LE_MS):
            raise FoldError("게이트웨이의 지연 칸이 포털의 것과 다르다 — 두 리포의 판이 어긋났다(usage_rollup.LAT_LE_MS · usage_stats.LAT_LE_MS)")
        out = {d: DayFold() for d in days}
        for k, d in (resp.get("fields") or {}).items():         # 칸이 처음 나온 날 — 그 날의 줄로 적어 둔다(화면이 '그 전은 기록 전' 이라 말한다)
            if d in out:
                out[d].rows.append(("field_first", {"field": str(k)[:20]}, 1))
        for r in resp["calls"]:
            f = out.get(r["day"])
            if f is None:
                continue
            key = {"app": str(r["backend"]), "tool": str(r["tool"]), "via": str(r["via"])}
            f.rows += [("calls", {**key, "st": 1} if r.get("status") else key, r["calls"]), ("err_app", key, r["errors_app"]),
                       ("err_gate", key, r["errors_gate"]), ("cache", key, r["cache"]), ("big", key, r["big"]), ("chars", key, r["chars"])]
            for i, n in enumerate(r.get("lat") or []):
                if n:
                    f.rows.append(("lat", {"app": key["app"], "tool": key["tool"], "le": i}, n))
        for r in resp.get("auth") or []:
            if r["day"] in out:
                out[r["day"]].rows.append(("auth_fail", {"reason": str(r["reason"])[:40]}, r["n"]))
        for r in resp.get("anon") or []:
            if r["day"] in out:
                out[r["day"]].rows.append(("anon_calls", {"via": str(r["via"])}, r["n"]))
        for r in resp["actors"]:
            e = _email(r["caller"])
            if r["day"] in out and e:
                via = str(r["via"])
                out[r["day"]].actors.append((e, f"mcp-{via}" if via else "mcp", int(r["n"]), aff.get(e, "")))
        for r in resp.get("actor_tools") or []:
            e = _email(r["caller"])
            if r["day"] in out and e and r["tool"] == RA_DRAFT_TOOL:
                out[r["day"]].actors.append((e, "ra", int(r["n"]), aff.get(e, "")))
        return out
    except (KeyError, TypeError, ValueError) as exc:
        raise FoldError(f"게이트웨이 답의 꼴이 다르다({type(exc).__name__})") from exc


def agent_days(resp: dict, days: list[str], aff: dict[str, str]) -> dict[str, DayFold]:
    """에이전트 서버 창구의 답 → 날마다 접은 줄. 소속은 잡을 연 때의 값(없으면 지금 원장의 값)."""
    try:
        out = {d: DayFold() for d in days}
        for r in resp["jobs"]:
            f = out.get(r["day"])
            if f is None:
                continue
            kind = {"kind": str(r["kind"])}
            f.rows += [("jobs", {**kind, "status": str(r["status"]), "llm": str(r.get("llm") or "glm")}, r["n"]),
                       ("jobs_report", kind, r["with_report"]), ("seats", kind, r["seats"]), ("seated", kind, r["seated"]),
                       ("rounds", kind, r["rounds"]), ("dur_s", kind, r["dur_s"]), ("dur_n", kind, r["dur_n"])]
        for r in resp.get("anon") or []:
            if r["day"] in out:
                out[r["day"]].rows.append(("anon_jobs", {}, r["n"]))
        for r in resp["actors"]:
            e = _email(r["user"])
            if r["day"] in out and e:
                out[r["day"]].actors.append((e, "delib", int(r["n"]), str(r.get("aff") or "") or aff.get(e, "")))
        return out
    except (KeyError, TypeError, ValueError) as exc:
        raise FoldError(f"에이전트 서버 답의 꼴이 다르다({type(exc).__name__})") from exc


async def ask(client: httpx.AsyncClient, base: str, token: str, body: dict, timeout: float, who: str) -> dict:
    """공유 비밀 창구에 한 번 묻는다 → 답(JSON 객체). 실패는 FoldError(까닭) — 비밀 · 주소는 싣지 않는다."""
    if not token:
        raise FoldError("공유 비밀(GATEWAY_SHARED_TOKEN)이 없어 묻지 않는다")
    if not base:
        raise FoldError(f"{who} 주소가 없다")
    try:
        r = await client.post(f"{base.rstrip('/')}{PATH}", json=body, headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
    except httpx.HTTPError as exc:
        raise FoldError(f"{who}에 닿지 못했다({type(exc).__name__})") from exc
    if r.status_code != 200:
        raise FoldError(_HTTP_WHY.get(r.status_code, f"{who} 답이 HTTP {r.status_code} 이다"))
    try:
        data = r.json()
    except ValueError:
        data = None
    if not isinstance(data, dict) or data.get("contract") != 1:
        raise FoldError(f"{who} 답의 꼴이 다르다(contract 1 이 아니다)")
    return data


# ── 한 번 돌기 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _write_many(settings: Settings, source: str, folds: dict[str, DayFold], *, today: date, fp: str, now: float) -> int:
    with closing(connect(settings)) as conn:
        for day in sorted(folds):
            write_day(conn, source, day, folds[day], today=today, fp=fp, now=now)
        mark(conn, source, now)
    return len(folds)


def _state(settings: Settings, source: str) -> dict:
    with closing(connect(settings)) as conn:
        return _done(conn, source)


def _fold_portal(settings: Settings, now: float, ex: list[str], fp: str) -> int:
    today = datetime.fromtimestamp(now, KST).date()
    days = due_days(_state(settings, "portal"), _portal_first(settings), today, fp, refold_ex=False)
    return _write_many(settings, "portal", portal_days(settings, days, ex), today=today, fp=fp, now=now)


def _fold_snapshot(settings: Settings, now: float, ex: list[str], fp: str) -> int:
    today = datetime.fromtimestamp(now, KST).date()
    return _write_many(settings, "snapshot", {today.isoformat(): snapshot_day(settings, now, ex)}, today=today, fp=fp, now=now)


def _fold_nginx(settings: Settings, now: float, ex: list[str], fp: str, service_ids: set[str]) -> int:
    today = datetime.fromtimestamp(now, KST).date()
    log = Path(settings.resolve(settings.nginx_access_log_path))
    if not (log.parent.is_dir() and any(log.parent.glob(log.name + "*"))):
        raise FoldError("정문 접근 로그가 없다(NGINX_ACCESS_LOG_PATH) — 정문 nginx 를 쓰지 않는 박스면 이 칸은 비어 있다")
    done = _state(settings, "nginx")
    first = min(done) if done else (today - timedelta(days=NGINX_KEEP_DAYS)).isoformat()
    days = due_days(done, first, today, fp, refold_ex=False, floor=today - timedelta(days=NGINX_KEEP_DAYS))
    folds, earliest, failed = nginx_days(settings, days, ex, service_ids)
    keep: dict[str, DayFold] = {}
    for d, f in folds.items():
        start = _midnight(date.fromisoformat(d))
        if earliest is None or start + 86400 <= earliest:
            if d not in done or done[d][3] == NOCOVER:  # 로그가 그날을 덮지 않는다 — 그렇다고만 적는다. 접어 둔 값이 있는 날은 건드리지 않는다
                keep[d] = DayFold(note=NOCOVER)
            continue
        if start < earliest:
            if d in done and done[d][3] != NOCOVER:     # 앞이 잘린 날을 다시 세면 줄어든다 — 앞서 접은 값을 둔다
                continue
            f.note = "일부만 — 정문 로그가 이날 중간부터 있다"
        if failed:
            f.note = (f.note + " · " if f.note else "") + f"로그 파일 {failed}개를 끝까지 못 읽었다"
        keep[d] = f
    return _write_many(settings, "nginx", keep, today=today, fp=fp, now=now)


async def _fold_remote(settings: Settings, source: str, now: float, ex: list[str], fp: str, client: httpx.AsyncClient) -> int:
    """게이트웨이 · 에이전트 서버 — 다시 접을 날을 앞에서부터 SPAN_DAYS 일씩 묻고 그 날들만 바꿔 쓴다. 처음에는 오늘 하루를 물어 그쪽 원장의 첫 날을
    안다(400일을 한 답으로 받지 않는다). 게이트웨이가 원장을 다 못 접었으면(complete=false) 그 답은 쓰지 않고 다시 묻는다 — 한 번 도는 동안
    REMOTE_ASKS 번까지, 남으면 다음에 잇는다."""
    today = datetime.fromtimestamp(now, KST).date()
    gateway = source == "gateway"
    base = (getattr(settings, "mcp_gateway_url", "") if gateway else getattr(settings, "agent_server_url", "")) or ""
    who = "게이트웨이" if gateway else "에이전트 서버"
    written, first_known, behind = 0, None, ""
    for _ in range(REMOTE_ASKS):
        done = await asyncio.to_thread(_state, settings, source)
        first = min(done) if done else first_known
        days = due_days(done, first, today, fp, refold_ex=True) if first else None
        if days is None:
            span = [today.isoformat()]
        else:
            last = (date.fromisoformat(days[0]) + timedelta(days=SPAN_DAYS - 1)).isoformat()
            span = [d for d in days if d <= last]
        body = {"since": span[0], "until": span[-1], "exclude": ex}
        if gateway:
            body["actor_tools"] = [RA_DRAFT_TOOL]
        resp = await ask(client, base, settings.gateway_shared_token, body, GATEWAY_TIMEOUT_S if gateway else AGENT_TIMEOUT_S, who)
        if not bool(resp.get("complete", True)):
            # 그쪽이 원장을 아직 다 접지 못했다(큰 감사 원장의 첫 물음) — 덜 접은 수를 접어 두지 않는다(닫힌 날이 모자란 채 굳는다). 물을 때마다
            # 그쪽이 이어 접으므로 다시 묻는다.
            behind = str(resp.get("scanned_through") or "")[:16].replace("T", " ")
            continue
        if days is None:
            first_known = ((resp.get("audit") or {}) if gateway else (resp.get("ledger") or {})).get("first_day")
            if not first_known:                         # 그쪽 원장이 비어 있다 — 접을 날이 없다(되면 됐다고 적는다)
                return written + await asyncio.to_thread(_write_many, settings, source, {}, today=today, fp=fp, now=now)
            continue
        aff = await asyncio.to_thread(_affiliations, settings)
        folds = (gateway_days if gateway else agent_days)(resp, span, aff)
        written += await asyncio.to_thread(_write_many, settings, source, folds, today=today, fp=fp, now=now)
        if span[-1] == days[-1]:
            return written
    if behind:
        raise FoldError(f"{who}가 원장을 아직 접는 중이다({behind} 까지 접었다) — 다 접으면 채워진다(다음에 잇는다)")
    raise FoldError(f"{who}의 날을 아직 다 채우지 못했다 — 접은 데까지 채웠고 다음에 잇는다")


def _prune(settings: Settings, now: float) -> int:
    cut = (datetime.fromtimestamp(now, KST).date() - timedelta(days=RETAIN_ACTOR_DAYS - 1)).isoformat()     # 오늘까지 400일을 둔다
    with closing(connect(settings)) as conn:
        return conn.execute("DELETE FROM usage_actor_daily WHERE day < ?", (cut,)).rowcount


def _mark_error(settings: Settings, source: str, now: float, error: str) -> None:
    with closing(connect(settings)) as conn:
        mark(conn, source, now, error)


async def run_once(app, settings: Settings, *, now: float | None = None, client: httpx.AsyncClient | None = None) -> dict:
    """한 번 접는다 → {원천: 접은 날 수 또는 {"error": 까닭}}. 예외를 내지 않는다 — 원천 하나의 실패가 다른 원천을 막지 않는다."""
    now = time.time() if now is None else now
    ex = excluded_accounts(settings)
    fp = fingerprint(ex)
    try:
        ids = {s.id for s in app.state.catalog.all()} | {"mcp-gw"}
    except Exception:  # noqa: BLE001 — 타일 목록을 못 읽어도 접는다(서비스가 portal 로 뭉친다)
        ids = {"mcp-gw"}
    own = client is None
    cli = client or httpx.AsyncClient()
    out: dict = {}
    try:
        steps = (("portal", lambda: asyncio.to_thread(_fold_portal, settings, now, ex, fp)),
                 ("snapshot", lambda: asyncio.to_thread(_fold_snapshot, settings, now, ex, fp)),
                 ("nginx", lambda: asyncio.to_thread(_fold_nginx, settings, now, ex, fp, ids)),
                 ("gateway", lambda: _fold_remote(settings, "gateway", now, ex, fp, cli)),
                 ("agent", lambda: _fold_remote(settings, "agent", now, ex, fp, cli)))
        for source, step in steps:
            try:
                out[source] = await step()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — 까닭을 남기고 다음 원천으로
                why = str(exc) if isinstance(exc, FoldError) else f"{type(exc).__name__}: {str(exc)[:160]}"
                out[source] = {"error": why}
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(_mark_error, settings, source, now, why)
        with contextlib.suppress(Exception):
            await asyncio.to_thread(_prune, settings, now)
    finally:
        if own:
            await cli.aclose()
    return out


async def run(app, settings: Settings, every: float) -> None:
    """기동 뒤 조금 있다가 한 번, 그 뒤 every 초마다 — 끌 때(cancel)까지. 실패는 까닭이 바뀔 때와 REPEAT_EVERY 번마다 경고로 적는다."""
    last, fails = None, 0
    delay = min(every, FIRST_DELAY_S)
    while True:
        await asyncio.sleep(delay)
        delay = every
        out = await run_once(app, settings)
        errs = "; ".join(f"{s} — {v['error']}" for s, v in out.items() if isinstance(v, dict)) or None
        if errs:
            fails += 1
            if errs != last or fails % REPEAT_EVERY == 0:
                logger.warning("이용 통계 접기 — 못 접은 원천이 있다(%d번째 · 다음에 다시 접는다): %s", fails, errs)
        else:
            if last:
                logger.warning("이용 통계 접기 — 모든 원천을 다시 접었다(%d번 실패 뒤)", fails)
            fails = 0
        last = errs
        app.state.usage_fold_last = {"at": time.time(), "result": out}


def start(app, settings: Settings) -> asyncio.Task | None:
    """기동 때 — 손잡이(USAGE_FOLD_S)가 0 이하면 띄우지 않는다(None — 접어 둔 표는 그대로 읽힌다)."""
    every = int(getattr(settings, "usage_fold_s", 0) or 0)
    if every <= 0:
        logger.info("이용 통계 접기 — USAGE_FOLD_S=0 이라 날마다 접지 않는다(관리자 이용 통계의 MCP · 심의 · 정문 칸이 채워지지 않는다)")
        return None
    return asyncio.get_running_loop().create_task(run(app, settings, float(every)), name="usage-fold")


async def stop(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
