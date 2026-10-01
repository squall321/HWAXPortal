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


def _login(c, email, *, admin=False, name=None):
    # 이름 기본값이 이메일(ASCII)이라 비ASCII 이름 경로를 한 번도 안 탔다 — 한글 이름 사용자만 500 이었다(5차 §1-c).
    c.post("/auth/local/signup", json={"email": email, "name": name or email, "password": "pw123456"})
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


def test_자격_중계는_접속_원장에_자동_갱신으로_남는다(make):
    """이 중계를 부르는 것은 화면의 StePrimer(로그인 뒤 저절로) 하나다 — 사람의 진입으로 적으면 기본 화면이
    로그인마다 'ste 진입' 으로 덮인다(접속 이력 검토 1차)."""
    fake = _FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200})
    c = make(fake)
    h = _boss(c)
    assert c.post("/systems/ste/credential", headers=h).status_code == 200
    rows = app.state.agent_audit.query_access(email="boss@corp.com", service="ste", since=0, include_auto=True)
    assert rows and rows[0]["detail"] == "primer"
    assert not app.state.agent_audit.query_access(email="boss@corp.com", service="ste", since=0)


# ── 한글 이름(5차 요청서 §1 — cae00 145회 500) ─────────────────────────────────
def test_한글_이름_사용자도_자격을_받고_이름이_그대로_건너간다(make):
    """httpx 는 헤더 값을 ascii 로 인코딩한다 — 한글 이름이면 UnicodeEncodeError 로 500 이었다. 이름은 퍼센트 인코딩해 보내고
    ste 가 되푼다(docs/change-request-5 D-1)."""
    from urllib.parse import unquote
    fake = _FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200})
    c = make(fake)
    r = c.post("/systems/ste/credential", headers=_login(c, "boss@corp.com", name="홍길동"))
    assert r.status_code == 200, r.text
    sent = fake.calls[-1][1]["x-heax-user-name"]
    assert sent.isascii() and unquote(sent) == "홍길동"


def test_ASCII_이름은_한_글자도_안_바뀐다(make):
    """옛 판 ste(unquote 없음)가 남아 있어도 ASCII 이름 사용자에게는 아무 변화가 없어야 한다."""
    fake = _FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200})
    c = make(fake)
    assert c.post("/systems/ste/credential",
                  headers=_login(c, "boss@corp.com", name="Koo Park (CAE) a&b")).status_code == 200
    assert fake.calls[-1][1]["x-heax-user-name"] == "Koo Park (CAE) a&b"


def test_헤더_인코딩이_터져도_500_이_아니라_502(make, monkeypatch):
    """§1-b — UnicodeEncodeError 는 httpx.HTTPError 가 아니라 except 를 빠져나가 핸들링 없는 500 이 됐다.
    이름 인코딩을 일부러 끄고(다른 헤더 값이 비ASCII 가 되는 날의 모양) 설계대로 502 인지 본다."""
    from app.auth.routes import ste_credential as mod
    monkeypatch.setattr(mod, "_header_name", lambda name: name)
    c = make(_FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200}))
    assert c.post("/systems/ste/credential", headers=_login(c, "boss@corp.com", name="홍길동")).status_code == 502


# ── 이름 대체 사슬(6차 요청 §4-B-1) — 운영 ADFS 는 이름 Claim 이 없다 ─────────────────────────
def test_세션에_이름이_없으면_원장_이름이_ste_로_건너간다(make):
    """세션 JWT 가 이름을 박아 들고 다닌다 — /auth/me 만 고치면 ste 헤더는 빈 값으로 갔다. 요청마다 원장을 읽는 자리(deps.entitled)에서
    대체하면 ste 헤더도 같이 따라온다(재로그인 불필요)."""
    from urllib.parse import unquote

    from app.auth.cookies import SESSION_COOKIE
    from app.auth.provider import Principal
    fake = _FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200})
    c = make(fake)
    h = _login(c, "boss@corp.com", name="홍길동")                    # 원장 이름 = 홍길동
    no_name = Principal(subject="boss@corp.com", email="boss@corp.com", display_name=None, groups=["portal-admin"])
    c.cookies.set(SESSION_COOKIE, app.state.jwt_service.issue_session(no_name))   # SAML 처럼 이름 없는 세션
    assert c.post("/systems/ste/credential", headers=h).status_code == 200
    assert unquote(fake.calls[-1][1]["x-heax-user-name"]) == "홍길동"


def test_이름_자리에_이메일이_박힌_토큰도_원장_이름으로_낫는다(make):
    """PAT 은 이름이 없으면 이메일을 박는다(pat_verify) — 그 값이 진리값이라 원장 이름에 닿지 못했다(6차 검토 2차)."""
    from urllib.parse import unquote

    from app.auth.cookies import SESSION_COOKIE
    from app.auth.provider import Principal
    fake = _FakeSte(200, {"access_token": STE_TOKEN, "expires_in": 43200})
    c = make(fake)
    h = _login(c, "boss@corp.com", name="홍길동")
    as_email = Principal(subject="boss@corp.com", email="boss@corp.com", display_name="Boss@Corp.com", groups=[])
    c.cookies.set(SESSION_COOKIE, app.state.jwt_service.issue_session(as_email))
    assert c.post("/systems/ste/credential", headers=h).status_code == 200
    assert unquote(fake.calls[-1][1]["x-heax-user-name"]) == "홍길동"
