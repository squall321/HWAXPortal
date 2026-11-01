# 이용 통계 M1 — 포털 안 원장을 읽을 때 세는 관리자 통계와 그 밑의 agent_audit ts 색인(docs/ops-dashboard)
#
# 계정은 example.com 시험 신원만, 주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
# 원장은 모두 임시 폴더에 만든다. 셈을 보는 시험은 now 를 박아 builder 를 바로 부르고, 문(관리자) · 기간 · 루프 밖은 API 로 본다.
import asyncio
import json
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import usage_stats
from app.agent.audit import AuditLog
from app.agent.conv_store import ConversationStore
from app.auth.cookies import CSRF_COOKIE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.routine_store import RoutineStore
from app.procedures.store import ProceduresStore
from app.usage_stats import KST

PW = "pw123456"
PC = ("203.0.113.5", 50000)
URL = "/auth/admin/usage"
# 2026-11-02(월) 12:00 KST — 주의 첫날이라 주 경계를 함께 본다
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=KST).timestamp()

# 색인이 생기기 전 판의 agent_audit 표 — 운영 박스의 원장은 이 꼴로 이미 있다(CREATE TABLE IF NOT EXISTS 는 고치지 않는다)
_OLD_AUDIT_DDL = (
    "CREATE TABLE agent_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, principal TEXT NOT NULL,"
    " chat_id TEXT, event TEXT NOT NULL, tool TEXT, status TEXT, meta TEXT)"
)


def _indexes(path, table: str) -> set[str]:
    with closing(sqlite3.connect(path)) as c:
        return {r[1] for r in c.execute(f"PRAGMA index_list({table})")}


def _kst(y, mo, d, h=0, mi=0, s=0) -> int:
    return int(datetime(y, mo, d, h, mi, s, tzinfo=KST).timestamp())


def _settings(tmp_path, **kw) -> Settings:
    base = {"user_store_path": str(tmp_path / "users.sqlite"), "agent_audit_log_path": str(tmp_path / "audit.sqlite"),
            "token_store_path": str(tmp_path / "tokens.sqlite"), "conv_store_path": str(tmp_path / "conv.sqlite"),
            "procedures_store_path": str(tmp_path / "procedures.sqlite"), "conn_key_path": str(tmp_path / "conn.key"),
            "local_bootstrap_admins": "boss@example.com", "usage_exclude_accounts": ""}
    return Settings(_env_file=None, **{**base, **kw})       # 박스의 backend/.env(USAGE_EXCLUDE_ACCOUNTS 등)가 시험에 끼지 않게


class Box:
    """원장 다섯을 임시 폴더에 만들고(저장소가 스키마를 깐다) 시각을 박은 줄을 바로 넣는다."""

    def __init__(self, tmp_path, **kw):
        self.s = _settings(tmp_path, **kw)
        AuditLog(self.s).close()
        UserStore(self.s)
        TokenStore(self.s)
        ConversationStore(self.s)
        ps = ProceduresStore(self.s)
        RoutineStore(ps)
        ps.close()
        self.paths = {"audit": self.s.agent_audit_log_path, "users": self.s.user_store_path, "tokens": self.s.token_store_path,
                      "conv": self.s.conv_store_path, "procedures": self.s.procedures_store_path}

    def sql(self, which: str, stmt: str, rows) -> None:
        with closing(sqlite3.connect(self.paths[which])) as c, c:
            c.executemany(stmt, rows)

    def access(self, *rows) -> None:      # (ts, email, event, service, detail[, ip])
        self.sql("audit", "INSERT INTO access_log (ts, email, event, service, detail, ip, ua, uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [(*r[:5], r[5] if len(r) > 5 else None, None, None) for r in rows])

    def audit(self, *rows) -> None:       # (ts, principal, event[, status, meta])
        self.sql("audit", "INSERT INTO agent_audit (ts, principal, event, status, meta) VALUES (?, ?, ?, ?, ?)",
                 [(r[0], r[1], r[2], r[3] if len(r) > 3 else None, json.dumps(r[4]) if len(r) > 4 and r[4] else None)
                  for r in rows])

    def user(self, email, *, created=None, status="active", affiliation="", department="", dept_id="") -> None:
        self.sql("users", "INSERT INTO users (email, name, status, created_at, affiliation, department, dept_id)"
                          " VALUES (?, ?, ?, ?, ?, ?, ?)",
                 [(email, email.split("@")[0], status, created or int(NOW) - 86400 * 100, affiliation, department, dept_id)])

    def build(self, days=30, now=NOW, labels=None) -> dict:
        return usage_stats.build(self.s, days=days, now=now, labels=labels)


def _row(sec: dict, **match) -> dict:
    return next(r for r in sec["rows"] if all(r.get(k) == v for k, v in match.items()))


# ── 색인 ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_옛_원장을_열면_agent_audit_에_ts_색인이_생기고_줄은_그대로다(tmp_path):
    db = tmp_path / "agent_audit.sqlite"
    with closing(sqlite3.connect(db)) as c, c:
        c.execute(_OLD_AUDIT_DDL)
        c.executemany("INSERT INTO agent_audit (ts, principal, event) VALUES (?, ?, ?)",
                      [(1_700_000_000 + i, "a@example.com", "chat_start") for i in range(50)])
    assert "agent_audit_ts" not in _indexes(db, "agent_audit"), "전제 — 옛 원장에는 색인이 없다"
    s = Settings(agent_audit_log_path=str(db))
    AuditLog(s).close()
    assert "agent_audit_ts" in _indexes(db, "agent_audit")
    AuditLog(s).close()                                   # 다시 열어도(재기동마다) 그대로 — IF NOT EXISTS
    with closing(sqlite3.connect(db)) as c:
        assert c.execute("SELECT COUNT(*) FROM agent_audit").fetchone()[0] == 50
        plan = " ".join(str(r) for r in c.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM agent_audit WHERE ts >= ? AND ts < ?", (0, 1)))
    assert "agent_audit_ts" in plan, f"기간으로 자르는 읽기가 색인을 타지 않는다 — {plan}"


def test_감사_접속_읽기는_모두_ts_색인을_탄다(tmp_path, monkeypatch):
    """원장 전체를 훑는 읽기가 하나도 없어야 한다 — 통계가 쌓인 운영 원장에서 읽을 때마다 표 전체를 돌지 않게."""
    box = Box(tmp_path)
    box.access((int(NOW) - 60, "a@example.com", "login", "portal", "local"))
    box.audit((int(NOW) - 60, "a@example.com", "chat_start"))
    seen: list[str] = []
    real = usage_stats._ro

    def traced(path):
        c = real(path)
        c.set_trace_callback(seen.append)
        return c
    monkeypatch.setattr(usage_stats, "_ro", traced)
    box.build(days=400)
    hits = [q for q in seen if "FROM agent_audit" in q or "FROM access_log" in q]
    assert len(hits) >= 10, hits
    with closing(sqlite3.connect(box.paths["audit"])) as c:
        for q in hits:
            plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + q)]
            assert not any(p.startswith(("SCAN agent_audit", "SCAN access_log")) for p in plan), f"{q}\n→ {plan}"


# ── 문 ────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def env(tmp_path, monkeypatch):
    """boss = 원장 관리자(첫 가입) · user = 활성 일반 사용자. 저장소는 기동 뒤 임시 원장으로 바꾼다."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    box = Box(tmp_path)
    app.dependency_overrides[get_settings] = lambda: box.s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app, client=PC) as c:
        keep = (app.state.user_store, app.state.agent_audit, app.state.token_store)
        app.state.user_store, app.state.agent_audit, app.state.token_store = UserStore(box.s), AuditLog(box.s), TokenStore(box.s)
        for email in ("boss@example.com", "user@example.com"):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
        assert app.state.user_store.approve("user@example.com", by="boss@example.com", groups=[])
        yield c, box
        app.state.user_store, app.state.agent_audit, app.state.token_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


def test_관리자만_본다_CAEG_의_별표를_가진_사람도_403(env):
    c, _ = env
    c.cookies.clear()
    assert c.get(URL).status_code == 401
    hb = _login(c, "boss@example.com")
    assert c.patch("/auth/access/users/user@example.com", json={"affiliation": "CAEG"}, headers=hb).status_code == 200
    _login(c, "user@example.com")
    ents = c.get("/auth/me").json()["entitlements"]
    assert {"feat:deliberation", "feat:procedures", "feat:routines"} <= set(ents), \
        f"전제 — CAEG 의 '*' 가 기능 키를 모두 연다(그래서 feat: 키로는 못 막는다) — {ents}"
    assert c.get(URL).status_code == 403
    _login(c, "boss@example.com")
    r = c.get(URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert {"generated_at", "range", "excluded", "sections"} <= body.keys()
    assert body["sections"] and all({"rows", "note"} <= v.keys() and v["note"] for v in body["sections"].values())


def test_기간은_1_에서_400_일로_붙잡고_기본은_30일이다(env):
    c, _ = env
    _login(c, "boss@example.com")
    today = datetime.fromtimestamp(time.time(), KST).date()
    r = c.get(URL).json()["range"]
    assert (r["days"], r["clamped"], len(r["axis"])) == (30, False, 30)
    assert (r["first_day"], r["last_day"]) == ((today - timedelta(days=29)).isoformat(), today.isoformat())
    big = c.get(URL, params={"days": 100000}).json()["range"]
    assert (big["days"], big["requested_days"], big["clamped"], len(big["axis"])) == (400, 100000, True, 400)
    for low in (0, -5):
        r = c.get(URL, params={"days": low}).json()["range"]
        assert (r["days"], r["clamped"], r["axis"]) == (1, True, [today.isoformat()])
    assert c.get(URL, params={"days": "many"}).status_code == 422


def test_기간_밖의_줄은_세지_않는다(tmp_path):
    box = Box(tmp_path)
    w = usage_stats.Window.of(30, NOW)
    box.access((w.since - 1, "old@example.com", "login", "portal", "local"),       # 첫날 KST 자정 1초 전
               (w.since, "edge@example.com", "login", "portal", "local"))
    got = box.build(days=30)["sections"]["logins_daily"]["totals"]
    assert (got["logins"], got["accounts"]) == (1, 1)
    assert box.build(days=31)["sections"]["logins_daily"]["totals"]["logins"] == 2


def test_셈은_이벤트_루프_밖에서_돈다(env, monkeypatch):
    """원장을 읽는 동안 포털의 모든 요청이 서지 않게 — 스레드에서 돌면 거기에는 도는 이벤트 루프가 없다."""
    c, _ = env
    real, seen = usage_stats.build, []

    def probe(*a, **kw):
        try:
            asyncio.get_running_loop()
            seen.append("loop")
        except RuntimeError:
            seen.append("thread")
        return real(*a, **kw)
    monkeypatch.setattr(usage_stats, "build", probe)
    _login(c, "boss@example.com")
    assert c.get(URL).status_code == 200 and seen == ["thread"]


# ── 거르기 ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_자동_예열_줄은_타일_진입에도_로그인에도_세지_않는다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 3600
    box.access((t, "a@example.com", "login", "portal", "sso"),
               *[(t + i, "a@example.com", "launch", "heax-hub", "primer") for i in range(3)],
               (t + 10, "a@example.com", "launch", "heax-hub", None),
               (t + 11, "b@example.com", "open", "spdm", None))
    sec = box.build()["sections"]
    tiles = sec["tiles"]
    assert tiles["totals"] == {"entries": 2, "accounts": 2}
    assert (_row(tiles, service="heax-hub")["entries"], _row(tiles, service="spdm")["open"]) == (1, 1)
    assert _row(tiles, service="heax-hub")["daily"][-1] == 1
    assert sec["logins_daily"]["totals"]["logins"] == 1


def test_뺄_계정은_모든_칸에서_빠지고_무엇을_뺐는지_말한다(tmp_path):
    box = Box(tmp_path, usage_exclude_accounts=" Tester@Example.com , svc-bot@example.com")
    t = int(NOW) - 7200
    for who in ("tester@example.com", "real@example.com"):
        box.user(who, created=t, affiliation="CAEG")
        box.access((t, who, "login", "portal", "local"), (t + 1, who, "launch", "heax-hub", None))
        box.audit((t, who, "chat_start"), (t + 1, who, "chat_done", "ok"), (t + 2, who, "deck_create", "ok"))
        box.sql("conv", "INSERT INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(f"c-{who}", who, "t", "chat", "web", t, t)])
        box.sql("procedures", "INSERT INTO runs (id, owner_sub, run_by, origin, state, started_at) VALUES (?, ?, ?, ?, ?, ?)",
                [(f"r-{who}", who, who, "manual", "done", t)])
        box.sql("procedures", "INSERT INTO routine_runs (id, owner_sub, routine_id, version_id, version_no, title, inputs_json, plan_json,"
                              " executor, state, started_at, deadline) VALUES (?, ?, 'x', 'v', 1, 't', '{}', '{}', 'chat', 'done', ?, ?)",
                [(f"rr-{who}", who, t, t + 60)])
        box.sql("tokens", "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked) VALUES (?, ?, ?, 'n', '[]', '[]', ?, ?, 0)",
                [(f"j-{who}", who, who, t, t + 86400 * 90)])
        box.sql("users", "INSERT INTO access_requests (email, key, status, created_at) VALUES (?, 'feat:routines', 'pending', ?)", [(who, t)])
        box.sql("users", "INSERT INTO connections (email, service, token, created_at) VALUES (?, 'reportarchive', 'x', ?)", [(who, t)])
    r = box.build()
    sec = r["sections"]
    assert r["excluded"]["accounts"] == ["svc-bot@example.com", "tester@example.com"]
    assert "USAGE_EXCLUDE_ACCOUNTS" in r["excluded"]["note"] and "2개" in r["excluded"]["note"]
    assert sec["logins_daily"]["totals"]["accounts"] == 1 and sec["tiles"]["totals"] == {"entries": 1, "accounts": 1}
    assert sec["chat_daily"]["totals"]["chatters"] == 1 and sec["chat_daily"]["totals"]["turns"] == 1
    assert [e["n"] for e in sec["events"]["rows"]] == [1]
    assert sec["conversations"]["totals"][0]["n"] == 1
    assert sec["procedure_runs"]["completion"]["n"] == 1 and sec["routine_runs"]["completion"]["n"] == 1
    assert sec["pats_live"]["rows"] == [{"kind": "personal", "n": 1, "owners": 1}]
    assert sec["access_requests"]["rows"][0]["n"] == 1 and sec["connections"]["rows"][0]["n"] == 1
    assert _row(sec["accounts_status"], status="active")["n"] == 1
    assert sum(r["n"] for r in sec["accounts_new"]["rows"] if r["n"]) == 1


def test_빼는_계정이_없으면_그렇게_말한다(tmp_path):
    ex = Box(tmp_path).build()["excluded"]
    assert ex["accounts"] == [] and "뺀 계정은 없다" in ex["note"] and ex["primer"] is True


def test_IP_UA_질의_메시지_글_부서_코드는_싣지_않는다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 600
    box.user("a@example.com", created=t, affiliation="CAEG", department="비밀 부서명", dept_id="DEPT-90210")
    box.sql("audit", "INSERT INTO access_log (ts, email, event, service, ip, ua, uid, detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(t, "a@example.com", "login", "portal", "203.0.113.77", "Secret-Agent-UA/1.0", "uid-0123456789ab", "local")])
    box.audit((t, "a@example.com", "chat_error", "error", {"upstream": 422, "detail": "질의 원문이 여기 있다"}),
              (t, "a@example.com", "chat_error", "error", {"reason": "agent_unreachable", "exc": "http://203.0.113.88:9009 refused"}),
              (t, "a@example.com", "upload_dispatch", "failed", {"error": "파일 이름 비밀.xlsx"}))
    box.sql("conv", "INSERT INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [("c1", "a@example.com", "대화 제목 비밀", "chat", "web", t, t)])
    box.sql("conv", "INSERT INTO messages (id, conversation_id, seq, role, content, ts) VALUES ('m1', 'c1', 0, 'user', '메시지 본문 비밀', ?)",
            [(t,)])
    blob = json.dumps(box.build(), ensure_ascii=False)
    for secret in ("203.0.113.77", "Secret-Agent-UA", "uid-0123456789ab", "질의 원문", "203.0.113.88", "파일 이름 비밀",
                   "대화 제목 비밀", "메시지 본문 비밀", "비밀 부서명", "DEPT-90210"):
        assert secret not in blob, secret


def test_챗_오류는_정해진_까닭_코드만_센다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 600
    box.audit((t, "a@example.com", "chat_error", "error", {"reason": "agent_unreachable", "exc": "x"}),
              (t, "a@example.com", "chat_error", "error", {"upstream": 422, "detail": "y"}),
              (t, "a@example.com", "chat_error", "rejected", {"reason": "max_concurrent_chats"}),
              (t, "a@example.com", "chat_error", "error", {"reason": "Free text! with spaces"}),
              (t, "a@example.com", "chat_error", "error"))
    rows = box.build()["sections"]["chat_errors"]["rows"]
    assert {r["reason"]: r["n"] for r in rows} == {"agent_unreachable": 1, "agent_422": 1, "max_concurrent_chats": 1, "unknown": 2}


# ── 날 · 칸 ────────────────────────────────────────────────────────────────────────────────────────────────
def test_날과_주는_KST_로_가른다(tmp_path):
    """UTC 로는 둘 다 11-01 이다 — KST 로는 일요일 23:59:59 과 월요일 00:30 이라 날도 주도 갈린다."""
    box = Box(tmp_path)
    sun, mon = _kst(2026, 11, 1, 23, 59, 59), _kst(2026, 11, 2, 0, 30)
    assert datetime.fromtimestamp(sun, UTC).date() == datetime.fromtimestamp(mon, UTC).date(), "전제 — UTC 로는 같은 날"
    box.access((sun, "a@example.com", "login", "portal", "local"), (mon, "b@example.com", "login", "portal", "sso"))
    box.audit((sun, "a@example.com", "chat_start"), (mon, "b@example.com", "chat_start"))
    box.sql("conv", "INSERT INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) VALUES (?, ?, 't', 'chat', 'web', ?, ?)",
            [("c1", "a@example.com", sun, sun), ("c2", "b@example.com", mon, mon)])
    sec = box.build(days=7)["sections"]
    assert (_row(sec["logins_daily"], day="2026-11-01")["accounts"], _row(sec["logins_daily"], day="2026-11-02")["accounts"]) == (1, 1)
    assert (_row(sec["chat_daily"], day="2026-11-01")["turns"], _row(sec["chat_daily"], day="2026-11-02")["turns"]) == (1, 1)
    assert sorted((r["day"], r["n"]) for r in sec["conversations"]["rows"]) == [("2026-11-01", 1), ("2026-11-02", 1)]
    weeks = {r["week"]: r["accounts"] for r in sec["logins_weekly"]["rows"]}
    assert weeks == {"2026-10-26": 1, "2026-11-02": 1}, "주는 월요일(KST)에 시작한다"
    assert {r["month"]: r["accounts"] for r in sec["logins_monthly"]["rows"]} == {"2026-10": None, "2026-11": 2}, \
        "원장의 첫 줄(11-01) 전 달은 기록 전이다"


def test_원장의_첫_줄_전_날은_0_이_아니라_null(tmp_path):
    box = Box(tmp_path)
    box.access((_kst(2026, 10, 30, 9), "a@example.com", "login", "portal", "local"))
    rows = box.build(days=7)["sections"]["logins_daily"]["rows"]
    assert [r["logins"] for r in rows] == [None, None, None, 1, 0, 0, 0]       # 10-27 ~ 11-02, 첫 줄은 10-30
    weekly = box.build(days=14)["sections"]["logins_weekly"]["rows"]
    assert weekly[0] == {"week": "2026-10-19", "accounts": None, "partial": False}, "기록 전 칸은 값이 없을 뿐 — 일부만이 아니다"
    assert weekly[1] == {"week": "2026-10-26", "accounts": 1, "partial": True}, "원장이 그 주 중간에 시작했다"


def test_로그인은_수단과_실패를_가르고_DAU_는_서로_다른_계정이다(tmp_path):
    box = Box(tmp_path)
    t = _kst(2026, 11, 2, 9)
    box.access((t, "a@example.com", "login", "portal", "sso"), (t + 1, "a@example.com", "login", "portal", "sso:aff:map:CAEG"),
               (t + 2, "b@example.com", "login", "portal", "local"), (t + 3, "c@example.com", "login_fail", "portal", "local:locked"),
               (t + 4, "d@example.com", "login_fail", "portal", "sso:disabled"))
    sec = box.build(days=7)["sections"]
    today = _row(sec["logins_daily"], day="2026-11-02")
    assert (today["logins"], today["failures"], today["accounts"], today["sso"], today["local"]) == (3, 2, 2, 2, 1)
    assert {r["method"]: (r["logins"], r["failures"], r["accounts"]) for r in sec["logins_method"]["rows"]} == \
        {"sso": (2, 1, 1), "local": (1, 1, 1)}
    assert "로그인 기준" in sec["logins_daily"]["note"]


def test_소속은_5명_미만이면_기타로_접는다(tmp_path):
    box = Box(tmp_path)
    for i in range(6):
        box.user(f"c{i}@example.com", affiliation="CAEG", status="active" if i else "pending")
    for i in range(2):
        box.user(f"l{i}@example.com", affiliation="LAB")
    box.user("none@example.com")
    sec = box.build(labels={"affiliation": {"CAEG": "CAE그룹"}})["sections"]["accounts_affiliation"]
    assert sec["rows"] == [{"affiliation": "CAEG", "label": "CAE그룹", "n": 6, "active": 5},
                           {"affiliation": None, "label": "기타", "n": 3, "active": 3, "folded": 2}]
    assert "k = 5" in sec["note"]


def test_PAT_은_살아_있는_것만_세고_지워지는_줄을_말한다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 3600
    live, gone = t + 86400 * 30, t - 1
    box.sql("tokens", "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked, parent_jti)"
                      " VALUES (?, ?, ?, 'n', '[]', '[]', ?, ?, ?, ?)",
            [("p1", "a@example.com", "a@example.com", t, live, 0, None), ("p2", "b@example.com", "b@example.com", t, live, 0, None),
             ("x1", "a@example.com", "a@example.com", t, live, 0, "p1"), ("rv", "a@example.com", "a@example.com", t, live, 1, None),
             ("ex", "c@example.com", "c@example.com", t - 86400 * 100, gone, 0, None)])
    sec = box.build()["sections"]
    assert sec["pats_live"]["rows"] == [{"kind": "personal", "n": 2, "owners": 2}, {"kind": "exchanged", "n": 1, "owners": 1}]
    assert sum(r["n"] for r in sec["pats_weekly"]["rows"]) == 4, "만료 전 행은 폐기된 것까지 주마다 센다"
    assert "지워" in sec["pats_weekly"]["note"]


def test_완주율은_끝난_실행_가운데_done_의_몫이다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 3600
    box.sql("procedures", "INSERT INTO runs (id, owner_sub, run_by, origin, state, started_at) VALUES (?, 'a@example.com', 'a@example.com', ?, ?, ?)",
            [(f"r{i}", o, s, t) for i, (o, s) in enumerate([("manual", "done"), ("manual", "done"), ("manual", "failed"),
                                                            ("manual", "running"), ("replay", "gated")])])
    box.sql("procedures", "INSERT INTO routine_runs (id, owner_sub, routine_id, version_id, version_no, title, inputs_json, plan_json,"
                          " executor, state, started_at, deadline) VALUES (?, 'a@example.com', 'x', 'v', 1, 't', '{}', '{}', ?, ?, ?, ?)",
            [(f"q{i}", e, s, t, t + 60) for i, (e, s) in enumerate([("chat", "done"), ("chat", "interrupted"), ("mcp", "waiting")])])
    sec = box.build()["sections"]
    manual = _row(sec["procedure_runs"], origin="manual")
    assert (manual["n"], manual["done"], manual["ended"], manual["completion"]) == (4, 2, 3, 0.667)
    assert _row(sec["procedure_runs"], origin="replay")["completion"] is None, "끝난 실행이 없으면 비율도 없다"
    assert sec["routine_runs"]["completion"] == {"n": 3, "done": 1, "ended": 2, "completion": 0.5}


def test_권한_요청은_키별로_승인까지_걸린_때의_중앙값을_낸다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 86400 * 3
    box.sql("users", "INSERT INTO access_requests (email, key, status, created_at, decided_at) VALUES (?, ?, ?, ?, ?)",
            [("a@example.com", "feat:routines", "approved", t, t + 3600), ("b@example.com", "feat:routines", "approved", t, t + 3 * 3600),
             ("c@example.com", "feat:routines", "pending", t, None), ("d@example.com", "plat:x", "rejected", t, t + 60)])
    rows = box.build(labels={"key": {"feat:routines": "분석 루틴"}})["sections"]["access_requests"]["rows"]
    assert rows[0] == {"key": "feat:routines", "label": "분석 루틴", "n": 3, "pending": 1, "approved": 2, "rejected": 0, "median_hours": 2.0}
    assert rows[1]["median_hours"] is None


def test_원장_하나를_못_읽어도_다른_칸은_내고_없는_원장을_만들지_않는다(tmp_path):
    box = Box(tmp_path)
    missing = tmp_path / "missing-procedures.sqlite"            # 폴더는 있다 — 쓰는 연결이면 여기서 빈 파일이 생긴다
    box.s = _settings(tmp_path, procedures_store_path=str(missing))
    box.access((int(NOW) - 60, "a@example.com", "login", "portal", "local"))
    sec = box.build()["sections"]
    assert sec["procedure_runs"]["error"] and sec["routine_runs"]["error"] and sec["procedure_runs"]["rows"] == []
    assert sec["logins_daily"]["totals"]["logins"] == 1 and not sec["logins_daily"].get("error")
    assert not missing.exists(), "읽기 전용 — 없는 원장을 만들지 않는다"
