# 로컬 이메일 계정 — 저장소 단위 + API 흐름(가입→승인→로그인→관리자 가드) 시험
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore, hash_password, verify_password
from app.config import Settings, get_settings
from app.main import app


# ── 저장소 단위 ──────────────────────────────────────────────────────────────
def _store(tmp_path) -> UserStore:
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"))
    return UserStore(s)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pw!")
    assert verify_password("s3cret-pw!", h)
    assert not verify_password("wrong", h)
    assert not verify_password("s3cret-pw!", "garbage")


def test_signup_pending_then_approve(tmp_path):
    st = _store(tmp_path)
    r = st.signup(email="A@Corp.com ", name="A", password="pw123456", bootstrap_admins=[])
    assert r == {"email": "a@corp.com", "status": "pending"}
    with pytest.raises(ValueError):  # pending 은 로그인 불가
        st.verify_login(email="a@corp.com", password="pw123456")
    assert st.approve("a@corp.com", by="admin@corp.com", groups=["mes-user"])
    u = st.verify_login(email="a@corp.com", password="pw123456")
    assert u["groups"] == ["mes-user"]
    assert not st.approve("a@corp.com", by="x")  # 이미 active — 재승인 불가


def test_bootstrap_first_admin(tmp_path):
    st = _store(tmp_path)
    r = st.signup(email="boss@corp.com", name="B", password="pw123456",
                  bootstrap_admins=["boss@corp.com"])
    assert r["status"] == "active"
    assert st.verify_login(email="boss@corp.com", password="pw123456")["groups"] == ["portal-admin"]
    # 두 번째 가입자는 명단에 있어도 pending — 부트스트랩은 빈 테이블에서만
    r2 = st.signup(email="second@corp.com", name="C", password="pw123456",
                   bootstrap_admins=["second@corp.com"])
    assert r2["status"] == "pending"


def test_lockout_after_failures(tmp_path):
    st = _store(tmp_path)
    st.signup(email="u@corp.com", name="U", password="pw123456", bootstrap_admins=["u@corp.com"])
    for _ in range(4):
        with pytest.raises(ValueError, match="bad credentials"):
            st.verify_login(email="u@corp.com", password="nope")
    with pytest.raises(ValueError, match="locked"):  # 5번째에서 잠금
        st.verify_login(email="u@corp.com", password="nope")
    with pytest.raises(ValueError, match="locked"):  # 맞는 비번도 잠금 중엔 거부
        st.verify_login(email="u@corp.com", password="pw123456")
    st.set_password("u@corp.com", "pw7890123")  # 재설정이 잠금 해제
    assert st.verify_login(email="u@corp.com", password="pw7890123")


def test_bootstrap_survives_prior_sso_rows(tmp_path):
    st = _store(tmp_path)
    st.note_sso_login(email="mock@corp.com", name="Mock")  # SSO 가 먼저 원장 행을 만들어도
    r = st.signup(email="boss@corp.com", name="B", password="pw123456",
                  bootstrap_admins=["boss@corp.com"])
    assert r["status"] == "active"  # 로컬 계정 0 이면 부트스트랩 창은 열려 있다


def test_sso_link_keeps_account(tmp_path):
    st = _store(tmp_path)
    st.signup(email="p@corp.com", name="P", password="pw123456", bootstrap_admins=["p@corp.com"])
    st.note_sso_login(email="p@corp.com", name="P")   # SSO 전환
    u = st.get("p@corp.com")
    assert u["auth_source"] == "sso"
    assert u["pw_hash"]                                # 계정·비번 해시 잔존
    st.note_sso_login(email="new@corp.com", name="N")  # 미가입자는 원장에 생성
    assert st.get("new@corp.com")["status"] == "active"


# ── API 흐름 ────────────────────────────────────────────────────────────────
@pytest.fixture()
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"),
                 local_bootstrap_admins="boss@corp.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()  # IP rate-limit 이 모듈 전역이라 테스트 간 누적을 끊는다
    with TestClient(app) as c:
        # lifespan 이 실설정으로 user_store 를 만들므로 **컨텍스트 진입 후** 교체해야 한다.
        # 진입 전에 심으면 lifespan 이 덮어써 실DB(data/users.sqlite)에 테스트가 기록된다(실사고).
        app.state.user_store = UserStore(s)
        yield c
    app.dependency_overrides.pop(get_settings, None)


def test_api_signup_login_flow(client):
    r = client.post("/auth/local/signup", json={
        "email": "boss@corp.com", "name": "Boss", "password": "pw123456"})
    assert r.status_code == 200 and r.json()["status"] == "active"  # 부트스트랩 관리자

    r = client.post("/auth/local/signup", json={
        "email": "user@corp.com", "name": "User", "password": "pw123456"})
    assert r.json()["status"] == "pending"

    r = client.post("/auth/local/login", json={"email": "user@corp.com", "password": "pw123456"})
    assert r.status_code == 401  # 승인 전

    r = client.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"})
    assert r.status_code == 200
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "boss@corp.com"
    assert "portal-admin" in me.json()["groups"]

    csrf = client.cookies.get("hwax_csrf")
    r = client.post("/auth/local/users/user@corp.com/approve", json={"groups": []},
                    headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200

    r = client.post("/auth/local/login", json={"email": "user@corp.com", "password": "pw123456"})
    assert r.status_code == 200
    assert client.get("/auth/me").json()["email"] == "user@corp.com"

    # 일반 사용자는 관리자 API 403
    r = client.get("/auth/local/users")
    assert r.status_code == 403


def test_api_wrong_password_401(client):
    client.post("/auth/local/signup", json={
        "email": "boss@corp.com", "name": "Boss", "password": "pw123456"})
    r = client.post("/auth/local/login", json={"email": "boss@corp.com", "password": "wrong!!!"})
    assert r.status_code == 401
    assert "invalid" in r.json().get("detail", r.text).lower()
