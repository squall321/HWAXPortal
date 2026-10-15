# 로그인 수명 — 갱신이 refresh·CSRF 쿠키도 다시 내어 쓰는 동안 8시간에 끊기지 않는지, 쉬는 상한은 그대로인지(K2-6)
"""세션은 로그인 8시간 뒤에 끝났다. 갱신 쿠키와 CSRF 쿠키가 둘 다 로그인 때 받은 max_age(jwt_refresh_ttl) 로 살고,
/auth/refresh 는 액세스 쿠키만 다시 줬기 때문이다. 8시간이 지나면 CSRF 쿠키가 없어 갱신이 403 이 되고, 화면은
http_401 만 되풀이했다(docs/request_1015.md K2, 10-14 실측 124건).

사용자 결정(10-15) — 갱신 때 연장한다. 갱신이 refresh 토큰을 새로 내고 CSRF 쿠키는 값은 그대로 수명만 늘린다.
쉬는 상한은 그대로다 — refresh 를 jwt_refresh_ttl 안에 한 번도 안 부르면 토큰도 쿠키도 끝난다. 만료·CSRF 검사도 그대로다.
"""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.access.policy import ADMIN_GROUP
from app.auth.cookies import CSRF_COOKIE, REFRESH_COOKIE, SESSION_COOKIE
from app.auth.jwt_service import SESSION_AUDIENCE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PW = "pw123456"


@pytest.fixture()
def box(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), local_bootstrap_admins="boss@corp.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.token_store)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)   # 기동 뒤 교체 — 실 저장소를 안 쓴다
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": PW})
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=["mes-user"])
        yield c, s
        app.state.user_store, app.state.token_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _refresh_token(email: str, groups: list[str], ttl: int) -> str:
    """로그인한 지 오래돼 수명이 ttl 초만 남은 refresh — 포털 키로 직접 서명한다."""
    return app.state.jwt_service._encode(
        {"sub": email, "aud": SESSION_AUDIENCE, "email": email, "name": None, "groups": groups}, ttl=ttl, typ="refresh")


def _wear(c, refresh: str, csrf: str = "csrf-value-1") -> dict:
    c.cookies.clear()
    c.cookies.set(REFRESH_COOKIE, refresh)
    c.cookies.set(CSRF_COOKIE, csrf)
    return {"X-CSRF-Token": csrf}


def _set_cookies(r) -> dict[str, str]:
    """응답이 내린 Set-Cookie — 이름 → 머리 줄 전체(값·Max-Age·Path·HttpOnly 를 같이 본다)."""
    return {h.split("=", 1)[0]: h for h in r.headers.get_list("set-cookie")}


def _attr(header: str, name: str) -> str | None:
    for part in header.split(";")[1:]:
        k, _, v = part.strip().partition("=")
        if k.lower() == name.lower():
            return v
    return None


def test_갱신은_refresh_토큰을_새로_내어_쉬는_상한부터_다시_센다(box):
    c, s = box
    h = _wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=60))   # 로그인 8시간이 거의 다 됐다
    r = c.post("/auth/refresh", headers=h)
    assert r.status_code == 200, r.text
    got = _set_cookies(r)
    assert REFRESH_COOKIE in got, "갱신이 refresh 를 다시 내지 않으면 로그인 8시간에 끊긴다"
    new = got[REFRESH_COOKIE].split(";", 1)[0].split("=", 1)[1]
    claims = app.state.jwt_service.verify_refresh(new)
    left = claims["exp"] - datetime.now(tz=UTC).timestamp()
    assert s.jwt_refresh_ttl - 30 <= left <= s.jwt_refresh_ttl, f"새 refresh 의 남은 수명 {left:.0f}초"
    assert claims["sub"] == "user@corp.com" and claims["groups"] == ["mes-user"]
    assert _attr(got[REFRESH_COOKIE], "Max-Age") == str(s.jwt_refresh_ttl)
    assert _attr(got[REFRESH_COOKIE], "Path") == "/auth", "refresh 는 /auth 경로 쿠키다 — 경로가 바뀌면 두 벌이 생긴다"
    assert "httponly" in got[REFRESH_COOKIE].lower()
    assert SESSION_COOKIE in got, "액세스 쿠키는 지금처럼 다시 낸다"


def test_갱신은_CSRF_쿠키를_같은_값으로_수명만_늘린다(box):
    """값을 바꾸면 이미 떠 있는 다른 탭이 들고 있는 헤더 값과 어긋난다. 수명을 안 늘리면 8시간 뒤 갱신이 CSRF 403 이 된다."""
    c, s = box
    h = _wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=60), csrf="tab-csrf-xyz")
    r = c.post("/auth/refresh", headers=h)
    assert r.status_code == 200, r.text
    got = _set_cookies(r)
    assert CSRF_COOKIE in got, "CSRF 쿠키 수명을 안 늘리면 로그인 8시간 뒤 갱신이 403 이다"
    assert got[CSRF_COOKIE].split(";", 1)[0] == f"{CSRF_COOKIE}=tab-csrf-xyz"
    assert _attr(got[CSRF_COOKIE], "Max-Age") == str(s.jwt_refresh_ttl)
    assert "httponly" not in got[CSRF_COOKIE].lower(), "SPA 가 읽어 헤더로 되싣는 쿠키다"


def test_갱신으로_되살린_refresh_에도_관리자_표지를_박지_않는다(box):
    """갱신이 refresh 를 다시 내면 옛 토큰의 그룹이 계속 이어진다 — 표지가 섞여 있으면 그것까지 끝없이 이어진다."""
    c, _s = box
    h = _wear(c, _refresh_token("user@corp.com", [ADMIN_GROUP, "mes-user"], ttl=60))
    r = c.post("/auth/refresh", headers=h)
    assert r.status_code == 200, r.text
    got = _set_cookies(r)
    assert REFRESH_COOKIE in got
    new = got[REFRESH_COOKIE].split(";", 1)[0].split("=", 1)[1]
    assert app.state.jwt_service.verify_refresh(new)["groups"] == ["mes-user"]


def test_쉬는_상한과_CSRF_검사는_그대로다(box):
    """연장은 '갱신할 때' 만이다 — 수명이 다한 refresh 로는 갱신이 안 되고(401) 쿠키도 다시 내리지 않는다. CSRF 도 그대로 본다."""
    c, _s = box
    h = _wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=-5))
    r = c.post("/auth/refresh", headers=h)
    assert r.status_code == 401
    assert not ({REFRESH_COOKIE, CSRF_COOKIE, SESSION_COOKIE} & set(_set_cookies(r))), "만료된 refresh 로 수명을 늘렸다"
    _wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=600))
    assert c.post("/auth/refresh").status_code == 403, "CSRF 헤더 없이 갱신됐다"
    c.cookies.clear()
    c.cookies.set(CSRF_COOKIE, "t")
    assert c.post("/auth/refresh", headers={"X-CSRF-Token": "t"}).status_code == 401, "refresh 없이 갱신됐다"


def test_로그인부터_갱신까지_이어진다(box):
    """실제 흐름 — 로그인이 준 쿠키로 갱신하면 새 refresh·같은 CSRF 가 오고, 그 쿠키로 다시 갱신된다."""
    c, _s = box
    assert c.post("/auth/local/login", json={"email": "user@corp.com", "password": PW}).status_code == 200
    csrf = c.cookies.get(CSRF_COOKIE)
    old = next(k.value for k in c.cookies.jar if k.name == REFRESH_COOKIE)
    r = c.post("/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200, r.text
    got = _set_cookies(r)
    assert REFRESH_COOKIE in got and got[CSRF_COOKIE].split(";", 1)[0] == f"{CSRF_COOKIE}={csrf}"
    assert next(k.value for k in c.cookies.jar if k.name == REFRESH_COOKIE) != old, "브라우저가 새 refresh 를 받지 않았다"
    assert c.post("/auth/refresh", headers={"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}).status_code == 200
    assert c.get("/auth/me").json()["email"] == "user@corp.com"
