# 로그인 수명 — 갱신이 refresh·CSRF 쿠키도 다시 내어 쓰는 동안 8시간에 끊기지 않는지, 쉬는 상한은 그대로인지(K2-6)
"""세션은 로그인 8시간 뒤에 끝났다. 갱신 쿠키와 CSRF 쿠키가 둘 다 로그인 때 받은 max_age(jwt_refresh_ttl) 로 살고,
/auth/refresh 는 액세스 쿠키만 다시 줬기 때문이다. 8시간이 지나면 CSRF 쿠키가 없어 갱신이 403 이 되고, 화면은
http_401 만 되풀이했다(docs/request_1015.md K2, 10-14 실측 124건).

사용자 결정(10-15) — 갱신 때 연장한다. 갱신이 refresh 토큰을 새로 내고 CSRF 쿠키는 값은 그대로 수명만 늘린다.
쉬는 상한은 그대로다 — refresh 를 jwt_refresh_ttl 안에 한 번도 안 부르면 토큰도 쿠키도 끝난다. 만료·CSRF 검사도 그대로다.
"""
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.access.policy import ADMIN_GROUP
from app.auth import jwt_service as jwt_mod
from app.auth import user_store as store_mod
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
        # 계정은 한 시간 전에 만들어졌다 — 몇십 초 전에 낸 refresh 가 '행이 생기기 전에 낸 토큰' 으로 걸리지 않아야
        # 정지 시각 규칙을 따로 볼 수 있다(행 생성 시각 규칙은 지운 뒤 다시 생긴 행 시험이 따로 본다).
        real = store_mod._now
        with monkeypatch.context() as m:
            m.setattr(store_mod, "_now", lambda: real() - 3600)
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


# ── 원장 대조(K2-6 후속, 조정자 결정 10-15) — 갱신이 세션을 늘리므로 정지·삭제된 계정은 갱신에서 끝난다 ────────────────
# 정지는 그 시각까지 낸 refresh 를 죽인다 — 되살려도 그 전에 낸 refresh 는 다시 살지 않는다(PAT 의 revoke_all_for 와 같은 뜻).
def _minted(monkeypatch, seconds_ago: int, email: str = "user@corp.com") -> str:
    """seconds_ago 초 전에 낸 refresh(아직 유효) — 낸 시각(iat)을 정지·행 생성 시각과 견주려고 서명 시계를 뒤로 돌린다."""
    real = jwt_mod._now
    with monkeypatch.context() as m:
        m.setattr(jwt_mod, "_now", lambda: real() - timedelta(seconds=seconds_ago))
        return _refresh_token(email, ["mes-user"], ttl=3600)


def _suspend_ago(monkeypatch, seconds_ago: int, email: str = "user@corp.com", how: str = "suspend") -> None:
    """seconds_ago 초 전에 정지 — 관리자 화면의 정지(suspend)와 저장소의 set_status("disabled") 둘 다 정지 시각을 남겨야 한다."""
    real = store_mod._now
    with monkeypatch.context() as m:
        m.setattr(store_mod, "_now", lambda: real() - seconds_ago)
        store = app.state.user_store
        assert (store.suspend(email) == "set") if how == "suspend" else store.set_status(email, "disabled")


def test_정지된_계정은_갱신이_401_이고_쿠키를_다시_내지_않는다(box, monkeypatch):
    c, _s = box
    assert c.post("/auth/refresh", headers=_wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=600))).status_code == 200
    _suspend_ago(monkeypatch, 10)
    # 정지 **뒤에** 낸 토큰이라도 — 정지 시각이 아니라 지금 상태(disabled)로 막는다
    r = c.post("/auth/refresh", headers=_wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=600)))
    assert r.status_code == 401, "정지된 계정의 세션을 갱신이 계속 늘린다"
    assert not ({REFRESH_COOKIE, CSRF_COOKIE, SESSION_COOKIE} & set(_set_cookies(r)))


@pytest.mark.parametrize("how", ["suspend", "set_status"])
def test_되살려도_정지_전에_받은_refresh_는_다시_살지_않는다(box, monkeypatch, how):
    c, _s = box
    store = app.state.user_store
    old = _minted(monkeypatch, 20)                     # 20초 전에 받은 refresh — 수명은 아직 남았다
    _suspend_ago(monkeypatch, 10, how=how)             # 10초 전에 정지
    assert store.set_status("user@corp.com", "active")  # 지금 되살림
    r = c.post("/auth/refresh", headers=_wear(c, old))
    assert r.status_code == 401, "되살린 계정의 정지 전 refresh 가 다시 산다(훔쳐 간 사본도 같이 산다)"
    # 되살린 뒤 새로 로그인한 세션은 그대로 늘어난다
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": "user@corp.com", "password": PW}).status_code == 200
    assert c.post("/auth/refresh", headers={"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}).status_code == 200


def test_정지와_같은_초에_낸_refresh_도_받지_않는다(box, monkeypatch):
    """iat·정지 시각은 초 단위다 — 같은 초면 정지 전·후를 못 가르므로 받지 않는 쪽으로 둔다(되살아나는 틈을 남기지 않는다)."""
    c, _s = box
    t = int(datetime.now(tz=UTC).timestamp()) - 30
    with monkeypatch.context() as m:
        m.setattr(jwt_mod, "_now", lambda: datetime.fromtimestamp(t, tz=UTC))
        old = _refresh_token("user@corp.com", ["mes-user"], ttl=3600)
    with monkeypatch.context() as m:
        m.setattr(store_mod, "_now", lambda: t)
        assert app.state.user_store.suspend("user@corp.com") == "set"
    assert app.state.user_store.set_status("user@corp.com", "active")
    assert c.post("/auth/refresh", headers=_wear(c, old)).status_code == 401


def test_원장을_못_읽으면_갱신을_받지_않는다(box, monkeypatch):
    """SSO 콜백과 같은 규칙 — 원장이 고장 난 동안 정지가 통째로 풀리면 안 된다."""
    c, _s = box

    def boom(_email):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(app.state.user_store, "get", boom)
    assert c.post("/auth/refresh", headers=_wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=600))).status_code == 401
    monkeypatch.setattr(app.state, "user_store", None)
    assert c.post("/auth/refresh", headers=_wear(c, _refresh_token("user@corp.com", ["mes-user"], ttl=600))).status_code == 401


def test_원장에_없는_계정은_갱신이_401_이다(box):
    """원장에는 지우는 기능이 없다 — 행이 없는 것이 '지워진 계정' 이다. 정지할 행이 없으니 갱신이 끝없이 늘릴 수 없게 막는다."""
    c, _s = box
    assert c.post("/auth/refresh", headers=_wear(c, _refresh_token("ghost@corp.com", ["mes-user"], ttl=600))).status_code == 401


def test_지운_뒤_다시_생긴_행은_그_전에_낸_refresh_를_받지_않는다(box, monkeypatch):
    """사람이 DB 에서 지운 행을 그 사람의 다음 SSO 로그인이 새로 만들면, 지우기 전에 낸 refresh 가 다시 사는 길이다.
    행이 생긴 시각(created_at)보다 먼저 낸 토큰은 받지 않는다."""
    c, _s = box
    store = app.state.user_store
    old = _minted(monkeypatch, 20)
    with store._lock:
        store._conn.execute("DELETE FROM users WHERE email = ?", ("user@corp.com",))
        store._commit()
    assert c.post("/auth/refresh", headers=_wear(c, old)).status_code == 401
    store.note_sso_login(email="user@corp.com", name="User")
    assert store.get("user@corp.com")["status"] == "active"
    assert c.post("/auth/refresh", headers=_wear(c, old)).status_code == 401, "지우기 전에 낸 refresh 가 다시 산다"


def test_정지_시각_칸이_없던_원장의_정지된_행에도_정지_시각을_채운다(tmp_path, monkeypatch):
    """칸이 생기기 전에 정지된 계정은 정지 시각이 0 이라 되살린 뒤 그 전에 낸 refresh 를 가를 수 없다 — 처음 열 때 한 번 채운다."""
    path = tmp_path / "u.sqlite"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE users (email TEXT PRIMARY KEY, name TEXT NOT NULL, pw_hash TEXT, "
                 "groups TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL DEFAULT 'pending', "
                 "auth_source TEXT NOT NULL DEFAULT 'local', created_at INTEGER NOT NULL, approved_at INTEGER, "
                 "approved_by TEXT, last_login_at INTEGER, failed_count INTEGER NOT NULL DEFAULT 0, "
                 "locked_until INTEGER NOT NULL DEFAULT 0)")
    conn.execute("INSERT INTO users (email, name, status, created_at) VALUES ('on@corp.com', 'On', 'active', 1700000000)")
    conn.execute("INSERT INTO users (email, name, status, created_at) VALUES ('off@corp.com', 'Off', 'disabled', 1700000000)")
    conn.commit()
    conn.close()
    before = int(datetime.now(tz=UTC).timestamp())
    first = UserStore(Settings(_env_file=None, user_store_path=str(path))).get("off@corp.com")
    assert "disabled_at" in first, "정지 시각 칸이 없다 — 되살린 뒤 정지 전에 낸 refresh 를 가를 수 없다"
    assert first["disabled_at"] >= before, "정지된 옛 행의 정지 시각이 비었다"
    real = store_mod._now
    monkeypatch.setattr(store_mod, "_now", lambda: real() + 100)   # 재기동은 나중에 일어난다
    again = UserStore(Settings(_env_file=None, user_store_path=str(path)))
    assert again.get("off@corp.com")["disabled_at"] == first["disabled_at"], "다시 열 때마다 정지 시각을 밀면 안 된다"
    assert again.get("on@corp.com")["disabled_at"] == 0
