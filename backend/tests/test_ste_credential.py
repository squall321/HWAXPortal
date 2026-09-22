# ste 자격 중계 — 포털 로그인이 곧 ste 로그인이 되게 하되, **아무나는 아니게**
"""왜 이 시험인가. 이 엔드포인트는 ste 의 관리자 승인제를 대신한다 — 여기서 막지 않으면
포털에 로그인한 모든 사람이 ste 계정을 얻는다. 그래서 인가(타일이 보이는가)와
정지 처리, 그리고 **실패를 실패로 내는 것**을 고정한다.

특히 마지막이 이 리포의 반복 결함이다. 다운스트림이 죽어 있을 때 조용히 빈 토큰을
돌려주면, 브라우저는 자격을 받은 줄 알고 ste 로 갔다가 로그인 화면을 본다 — 원인이
어디에도 안 남는다. 그래서 502 로 낸다.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

STE_TOKEN = "ste_pat_abcdefghijklmnop"


class _FakeSte:
    """ste 백엔드 대역. 마지막으로 받은 헤더를 들고 있어 무엇이 건너갔는지 볼 수 있다."""

    def __init__(self, status=200, body=None):
        self.status, self.body = status, (body or {})
        self.calls: list[tuple[str, dict]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((str(request.url), dict(request.headers)))
        if self.status == 0:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(self.status, json=self.body)


@pytest.fixture()
def make(tmp_path, monkeypatch):
    created: list = []

    def _make(fake: _FakeSte | None, *, secret="ste-test-secret"):
        s = Settings(user_store_path=str(tmp_path / f"u{len(created)}.sqlite"),
                     local_bootstrap_admins="boss@corp.com",
                     ste_sso_secret=secret,
                     ste_base_url="http://ste.test/ste")
        app.dependency_overrides[get_settings] = lambda: s
        from app.auth.routes import ste_credential as mod
        from app.auth.routes.local import _rl
        _rl.clear()
        if fake is not None:
            transport = httpx.MockTransport(fake.handler)
            real = httpx.AsyncClient

            def _patched(*a, **kw):
                kw["transport"] = transport
                return real(*a, **kw)

            monkeypatch.setattr(mod.httpx, "AsyncClient", _patched)
        c = TestClient(app)
        c.__enter__()
        app.state.user_store = UserStore(s)
        created.append(c)
        return c

    yield _make
    for c in created:
        c.__exit__(None, None, None)
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email, *, admin=False):
    c.post("/auth/local/signup", json={"email": email, "name": email, "password": "pw123456"})
    assert c.post("/auth/local/login",
                  json={"email": email, "password": "pw123456"}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _boss(c):
    """부트스트랩 관리자 — 첫 가입자라 즉시 active 다(다른 계정은 승인 대기일 수 있다)."""
    return _login(c, "boss@corp.com")


def _plain_user(c):
    """**허가 없는 정당한 사용자.** 관리자가 그룹 없이 승인한 사람이라 로그인은 되지만
    플랫폼 허가가 없어 타일이 하나도 안 보인다(access-control 규약)."""
    hb = _boss(c)
    c.post("/auth/local/signup",
           json={"email": "plain@corp.com", "name": "P", "password": "pw123456"})
    assert c.post("/auth/local/users/plain@corp.com/approve",
                  json={"groups": []}, headers=hb).status_code == 200
    c.post("/auth/local/logout", headers=hb)
    assert c.post("/auth/local/login",
                  json={"email": "plain@corp.com", "password": "pw123456"}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


# ── 되는 길 ─────────────────────────────────────────────────────────────────
def test_relays_the_token_and_passes_identity(make):
    fake = _FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200})
    c = make(fake)
    h = _boss(c)

    r = c.post("/systems/ste/credential", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["token"] == STE_TOKEN

    url, headers = fake.calls[-1]
    assert url.endswith("/api/auth/sso")
    assert headers["x-heax-user-email"] == "boss@corp.com"
    assert headers["x-heax-gateway-secret"] == "ste-test-secret"


def test_the_token_never_rides_in_the_url(make):
    """접근 로그에 사용자 자격이 평문으로 남지 않게 — 본문으로만 오간다."""
    fake = _FakeSte(200, {"access_token": STE_TOKEN})
    c = make(fake)
    r = c.post("/systems/ste/credential", headers=_boss(c))
    assert STE_TOKEN not in str(r.request.url)
    assert STE_TOKEN not in fake.calls[-1][0]


# ── 막히는 길 ───────────────────────────────────────────────────────────────
def test_anonymous_is_rejected(make):
    c = make(_FakeSte(200, {"access_token": STE_TOKEN}))
    assert c.post("/systems/ste/credential").status_code in (401, 403)


def test_csrf_is_required(make):
    fake = _FakeSte(200, {"access_token": STE_TOKEN})
    c = make(fake)
    _boss(c)
    r = c.post("/systems/ste/credential")           # CSRF 헤더 없이
    assert r.status_code in (401, 403)
    assert not fake.calls, "인가 전에 ste 를 부르면 안 된다"


def test_without_the_platform_grant_there_is_no_credential(make):
    """**이 시험이 이 파일의 이유다.** 이 한 줄(visible_systems)이 ste 의 관리자 승인제를
    대신한다 — 빠지면 포털에 로그인한 모든 사람이 ste 계정을 얻는다."""
    fake = _FakeSte(200, {"access_token": STE_TOKEN})
    c = make(fake)
    h = _plain_user(c)
    assert c.get("/systems").json() == [], "전제 확인 — 이 사람에겐 타일이 없다"

    r = c.post("/systems/ste/credential", headers=h)
    assert r.status_code == 404, r.text
    assert not fake.calls, "인가에서 막혔으면 ste 를 부르지도 말아야 한다"


def test_disabled_downstream_account_is_surfaced(make):
    """ste 가 정지시킨 계정은 403 그대로 전한다 — 조용히 200 으로 바꾸지 않는다."""
    c = make(_FakeSte(403, {"detail": "비활성화된 계정이다"}))
    assert c.post("/systems/ste/credential", headers=_boss(c)).status_code == 403


def test_unconfigured_relay_is_404(make):
    """시크릿이 없으면 기능이 꺼진 것이다 — 브라우저가 할 일은 조용히 넘어가는 것."""
    c = make(None, secret="")
    assert c.post("/systems/ste/credential", headers=_boss(c)).status_code == 404


# ── 실패를 실패로 낸다 ──────────────────────────────────────────────────────
def test_ste_unreachable_is_502_not_an_empty_token(make):
    c = make(_FakeSte(0))
    r = c.post("/systems/ste/credential", headers=_boss(c))
    assert r.status_code == 502
    assert "token" not in r.json()


def test_ste_refusal_is_502(make):
    c = make(_FakeSte(500, {"detail": "boom"}))
    assert c.post("/systems/ste/credential", headers=_boss(c)).status_code == 502


def test_empty_token_from_ste_is_502(make):
    """200 인데 토큰이 비어 있는 것이 가장 위험하다 — 성공처럼 생긴 실패다."""
    c = make(_FakeSte(200, {"access_token": "", "expires_in": 1}))
    assert c.post("/systems/ste/credential", headers=_boss(c)).status_code == 502


# ── 회수 ────────────────────────────────────────────────────────────────────
def test_revoke_calls_ste_and_never_blocks_logout(make):
    fake = _FakeSte(200, {"ok": True, "revoked": 1})
    c = make(fake)
    r = c.post("/systems/ste/credential/revoke", headers=_boss(c))
    assert r.status_code == 200 and r.json()["revoked"] is True
    assert fake.calls[-1][0].endswith("/api/auth/sso/revoke")


def test_revoke_survives_a_dead_ste(make):
    """회수가 안 됐다고 로그아웃을 막으면 사용자가 나갈 수 없다."""
    c = make(_FakeSte(0))
    r = c.post("/systems/ste/credential/revoke", headers=_boss(c))
    assert r.status_code == 200 and r.json()["revoked"] is False
