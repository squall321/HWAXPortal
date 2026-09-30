# 서비스별 접속 이력 — 로그인·타일 진입 원장, 로그인 연결 ID 쿠키, 관리자 조회, 정문 요청 요약(docs/access-history)
#
# 주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
import gzip
import logging
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.agent.audit import AuditLog
from app.auth import access_log
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PC = ("203.0.113.5", 50000)


@pytest.fixture()
def env(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins="boss@corp.com",
                 agent_audit_log_path=str(tmp_path / "audit.sqlite"),
                 nginx_access_log_path=str(tmp_path / "logs" / "nginx-access.log"))
    (tmp_path / "logs").mkdir()
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app, client=PC) as c:
        app.state.user_store = UserStore(s)            # 컨텍스트 진입 후 교체(실DB 오염 방지)
        app.state.agent_audit = AuditLog(s)
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": "pw123456"})
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": "pw123456"})
        h = _login(c, "boss@corp.com")
        assert c.post("/auth/local/users/user@corp.com/approve", json={"groups": []}, headers=h).status_code == 200
        yield c, s, tmp_path
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email, pw="pw123456"):
    r = c.post("/auth/local/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _rows(**kw):
    return app.state.agent_audit.query_access(since=0, include_auto=True, **kw)


def test_로그인하면_원장에_주소와_연결_ID_가_남고_쿠키로도_준다(env):
    c, _, _ = env
    _login(c, "user@corp.com")
    row = _rows(email="user@corp.com", event="login")[0]
    assert (row["service"], row["detail"], row["ip"]) == ("portal", "local", "203.0.113.5")
    assert row["uid"] and c.cookies.get("hwax_uid") == row["uid"], "nginx 가 적는 쿠키 값과 원장의 값이 같아야 이어진다"
    first = row["uid"]
    _login(c, "user@corp.com")
    assert _rows(email="user@corp.com", event="login")[0]["uid"] != first, "로그인마다 새 값"


def test_로그인_실패도_시도한_이메일과_주소로_남는다(env):
    c, _, _ = env
    r = c.post("/auth/local/login", json={"email": "user@corp.com", "password": "wrong-pass"})
    assert r.status_code == 401
    row = _rows(email="user@corp.com", event="login_fail")[0]
    assert row["ip"] == "203.0.113.5" and row["detail"].startswith("local:")


def test_타일_진입과_클릭이_서비스별로_남고_자동_갱신은_기본에서_숨는다(env):
    c, _, _ = env
    h = _login(c, "boss@corp.com")                    # 관리자는 모든 타일이 보인다
    assert c.post("/systems/heax-hub/launch", headers=h).status_code == 200
    assert c.post("/systems/heax-hub/launch?via=primer", headers=h).status_code == 200
    assert c.post("/systems/spdm/open", headers=h).status_code == 200
    got = [(r["event"], r["service"], r["detail"]) for r in _rows(email="boss@corp.com") if r["event"] != "login"]
    assert got == [("open", "spdm", None), ("launch", "heax-hub", "primer"), ("launch", "heax-hub", None)]
    uid = c.cookies.get("hwax_uid")
    assert all(r["uid"] == uid for r in _rows(email="boss@corp.com")[:3]), "진입 줄에도 연결 ID"
    shown = app.state.agent_audit.query_access(email="boss@corp.com", since=0)
    assert ("launch", "heax-hub", "primer") not in [(r["event"], r["service"], r["detail"]) for r in shown], \
        "화면의 SSO 미리 로그인은 45분마다 저절로 쌓인다 — 기본 조회에서 뺀다"


def test_보이지_않는_타일은_클릭_기록도_거절한다(env):
    c, _, _ = env
    h = _login(c, "user@corp.com")
    assert c.post("/systems/no-such-tile/open", headers=h).status_code == 404
    assert c.post("/systems/spdm/open").status_code == 403, "CSRF 없이는 못 쓴다"
    assert not _rows(event="open")


def test_로그아웃하면_연결_ID_쿠키도_지운다(env):
    c, _, _ = env
    h = _login(c, "user@corp.com")
    assert c.cookies.get("hwax_uid")
    c.post("/auth/logout", headers=h)
    assert not c.cookies.get("hwax_uid")


def test_원장_쓰기가_실패해도_로그인은_되고_경고가_남는다(env, monkeypatch, caplog):
    """부기록이다. 다만 조용히 삼키지 않는다 — 포털은 INFO 가 버려지고 WARNING 은 남는다(D-4)."""
    c, _, _ = env

    def boom(**_kw):
        raise OSError("disk full")
    monkeypatch.setattr(app.state.agent_audit, "record_access", boom)
    with caplog.at_level(logging.WARNING):
        _login(c, "user@corp.com")
    assert any("access log write failed" in r.getMessage() for r in caplog.records)


def test_관리자만_원장을_본다(env):
    c, _, _ = env
    _login(c, "user@corp.com")
    assert c.get("/auth/admin/access").status_code == 403
    _login(c, "boss@corp.com")
    body = c.get("/auth/admin/access", params={"email": "user@corp.com"}).json()
    assert body["rows"] and all(r["email"] == "user@corp.com" for r in body["rows"])


def _nginx_line(ts, ip, path, uid, status=200):
    t = ts.astimezone(timezone(timedelta(hours=9))).isoformat(timespec="seconds")   # nginx 는 로컬 시간대로 적는다
    return f'{ip} "-" [{t}] "GET {path}" {status} 12 "Mozilla/5.0" "{uid}"\n'


def test_계정별_정문_요청을_서비스별로_묶는다(env):
    """정문 로그의 연결 ID 칸을 원장의 login 행과 이어 그 사람의 모든 서비스 요청을 찾는다 — 회전본(.gz)까지(D-5)."""
    c, s, tmp = env
    _login(c, "user@corp.com")
    uid = c.cookies.get("hwax_uid")
    now = datetime.now(timezone.utc)
    log = tmp / "logs" / "nginx-access.log"
    log.write_text(
        _nginx_line(now, "203.0.113.5", "/heax-hub/assets/app.js", uid)
        + _nginx_line(now, "203.0.113.5", "/apps/step_forge/api/x", uid)
        + _nginx_line(now, "198.51.100.7", "/ai-data-hub/api/q", uid)
        + _nginx_line(now, "203.0.113.9", "/heax-hub/", "someone-else")                     # 남의 연결 ID
        + '203.0.113.5 "-" [2026-09-01T00:00:00+09:00] "GET /heax-hub/" 200 1 "UA"\n'         # 옛 형식(칸 없음)
        + _nginx_line(now - timedelta(days=30), "203.0.113.5", "/signalforge/", uid))        # 창 밖
    with gzip.open(tmp / "logs" / "nginx-access.log-20260929.gz", "wt") as g:
        g.write(_nginx_line(now - timedelta(days=1), "203.0.113.5", "/mcp-gw/mcp", uid)
                + _nginx_line(now - timedelta(days=1), "203.0.113.5", "/", uid))
    _login(c, "boss@corp.com")
    body = c.get("/auth/admin/access/requests", params={"email": "user@corp.com", "days": 7}).json()
    by = {r["service"]: r for r in body["services"]}
    assert set(by) == {"heax-hub", "apps/step_forge", "ai-data-hub", "mcp-gw", "portal"}
    assert by["ai-data-hub"]["ips"] == ["198.51.100.7"] and by["heax-hub"]["requests"] == 1
    assert body["uid_column"] and body["logins"] >= 1 and len(body["recent"]) == 5 and not body["note"]
    assert c.get("/auth/admin/access/requests", params={"email": "user@corp.com", "days": 30}).status_code == 422, \
        "nginx 로그는 14일만 남는다 — 그보다 긴 창은 거짓 '없음' 이다"


def test_정문_로그에_연결_ID_칸이_없으면_그렇다고_말한다(env):
    c, _, tmp = env
    _login(c, "user@corp.com")
    (tmp / "logs" / "nginx-access.log").write_text('203.0.113.5 "-" [2026-09-30T00:00:00+09:00] "GET /" 200 1 "UA"\n')
    _login(c, "boss@corp.com")
    body = c.get("/auth/admin/access/requests", params={"email": "user@corp.com"}).json()
    assert body["services"] == [] and not body["uid_column"] and "nginx" in body["note"], \
        "재기동 전이라 칸이 없는 것을 '요청 없음' 으로 보이면 안 된다"


@pytest.mark.parametrize("host,want", [
    ("203.0.113.5", "203.0.113.5"), ("testclient", ""), (None, ""), ('fe80::1%evil "x"', ""),
    ("::ffff:203.0.113.4", "203.0.113.4"), ("2001:DB8::1", "2001:db8::1"),
])
def test_주소_형식만_적는다(host, want):
    assert access_log.clean_ip(host) == want


def test_시험은_운영_감사_원장에_쓰지_않는다():
    """conftest 가 기동 경로를 임시 파일로 돌린다 — 없으면 시험 로그인이 운영 접속 이력에 섞인다."""
    path = get_settings().resolve(get_settings().agent_audit_log_path)
    assert "hwax-test-audit-" in path and "/data/" not in os.path.realpath(path)
