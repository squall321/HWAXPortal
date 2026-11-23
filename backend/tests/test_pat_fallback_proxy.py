# PAT 발급 응답이 박스의 사내 프록시(HWAX_FALLBACK_PROXY)를 싣는지 — 설치 배치의 npm 폴백 주소를 공개 리포에서 걷어 냈다(사용자 결정 11-24)
#
# 토큰 화면은 발급 응답의 fallback_proxy 를 buildSetupBat 에 넘긴다(배치 산출물은 test_setup_bat). 주소는 로그인 · CSRF 를 지난
# 발급 응답에만 싣고, 게이트웨이 · 앱이 부르는 교환 응답에는 없다. 시험 주소는 문서용 예약 대역(TEST-NET-2)만 쓴다.
import pytest
from fastapi.testclient import TestClient

from app.auth.routes.pat import PatCreated
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PROXY = "http://198.51.100.20:8080"


@pytest.fixture(params=[(PROXY, PROXY), (f"  {PROXY}\n", PROXY), ("", "")], ids=["값", "앞뒤빈칸", "없음"])
def client(request, tmp_path):
    raw, want = request.param
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"),
                 jwt_keys_dir=str(tmp_path / "keys"),
                 local_bootstrap_admins="a@corp.com",
                 hwax_fallback_proxy=raw)
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        c.want = want
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(client) -> dict:
    client.post("/auth/local/signup",
                json={"email": "a@corp.com", "name": "A", "password": "pw123456"})
    client.post("/auth/local/login", json={"email": "a@corp.com", "password": "pw123456"})
    return {"X-CSRF-Token": client.cookies.get("hwax_csrf")}


def test_발급_응답이_박스의_사내_프록시를_싣는다(client):
    r = client.post("/auth/pat", json={"name": "claude"}, headers=_login(client))
    assert r.status_code == 200, r.text
    assert r.json()["fallback_proxy"] == client.want, "비면 빈 글자 — 배치는 폴백 없이 직결만 본다"


def test_로그인하지_않으면_주소를_주지_않는다(client):
    r = client.post("/auth/pat", json={"name": "claude"})
    assert r.status_code in (401, 403)
    assert "198.51.100.20" not in r.text


def test_교환_응답에는_주소_칸이_없다():
    """교환은 게이트웨이 · 앱이 원 PAT 로 부른다 — 배치를 만드는 자리가 아니다."""
    assert "fallback_proxy" not in PatCreated.model_fields
