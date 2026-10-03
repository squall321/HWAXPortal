# RA 사람별 위임(ste 방식) — 포털이 RA 를 직접 부르는 곳(PPT 가져오기)이 그 사람 토큰을 그 자리에서 받는지
"""docs/sso-delegation PLAN §2-2. 고정하는 것.

  · 계약 — 헤더 넷(비밀·이메일·퍼센트 인코딩한 이름·client=hwax-portal), RA 봉투(`{success, data:{…}}`) 깊이 찾기.
  · **실패는 None** — 꺼짐(비밀 없음·RA 404)·거부·연결 실패 어느 쪽이든 부르는 쪽이 등록 토큰으로 내려가거나 이유를 말한다.
  · 비밀·토큰은 로그에 안 남는다.
  · PPT 가져오기 — 위임 토큰을 먼저 쓰고, 부서 헤더는 사람이 고른 조직이 있을 때만 싣는다(없으면 RA 가 홈 부서로 정한다).
"""
import logging
import time
from types import SimpleNamespace
from urllib.parse import unquote

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth import ra_sso
from app.auth.provider import Principal
from app.auth.user_store import UserStore
from app.config import Settings, get_settings

SECRET = "ra-sso-test-secret-0123456789abcdef"
TOKEN = "ra-jwt-for-kim-0123456789"
_REAL_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def _fresh_cache():
    ra_sso._CACHE.clear()
    ra_sso._OFF_LOGGED = False
    yield
    ra_sso._CACHE.clear()
    ra_sso._OFF_LOGGED = False


def _settings(**kw) -> Settings:
    kw.setdefault("ra_base_url", "http://ra.test")
    kw.setdefault("ra_sso_secret", SECRET)
    return Settings(_env_file=None, **kw)


def _mock_ra(monkeypatch, handler):
    """포털 코드가 만드는 AsyncClient 를 MockTransport 로 바꾼다 — 시험이 진짜 RA 를 치면 안 된다."""
    seen: list[httpx.Request] = []

    def _h(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return handler(req)

    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(_h), **kw))
    return seen


def _ok(token=TOKEN, expires_in=43200):
    return lambda req: httpx.Response(200, json={"success": True, "data": {
        "access_token": token, "token_type": "bearer", "expires_in": expires_in, "needs_workspace": False}})


# ── 계약 ─────────────────────────────────────────────────────────────────────
@pytest.mark.anyio
async def test_headers_follow_the_contract_and_the_korean_name_is_percent_encoded(monkeypatch):
    """httpx 는 헤더를 ascii 로 인코딩한다 — 한글 이름을 그대로 실으면 ste 중계에서처럼 UnicodeEncodeError 로 터진다."""
    seen = _mock_ra(monkeypatch, _ok())
    got = await ra_sso.ra_user_token(_settings(), email="Kim@Corp.com", name="김철수")
    assert got == TOKEN
    (req,) = seen
    assert req.method == "POST" and str(req.url) == "http://ra.test/api/auth/sso"
    assert req.headers["X-Heax-Gateway-Secret"] == SECRET
    assert req.headers["X-Heax-User-Email"] == "kim@corp.com"
    assert req.headers["X-Heax-User-Name"].isascii() and unquote(req.headers["X-Heax-User-Name"]) == "김철수"
    # 게이트웨이(gateway)와 다른 이름 — 발급이 서로를 회수하지 않게 가른다
    assert req.headers["X-Heax-Client"] == "hwax-portal"


@pytest.mark.anyio
async def test_ra_sso_url_overrides_the_default(monkeypatch):
    seen = _mock_ra(monkeypatch, _ok())
    await ra_sso.ra_user_token(_settings(ra_sso_url="http://other.test/x/sso"), email="a@x.com")
    assert str(seen[0].url) == "http://other.test/x/sso"


@pytest.mark.anyio
async def test_disabled_without_a_secret_and_never_calls_ra(monkeypatch):
    seen = _mock_ra(monkeypatch, _ok())
    assert await ra_sso.ra_user_token(_settings(ra_sso_secret=""), email="a@x.com") is None
    assert await ra_sso.ra_user_token(_settings(ra_sso_secret="   "), email="a@x.com") is None
    assert await ra_sso.ra_user_token(_settings(), email="") is None
    assert seen == []


@pytest.mark.anyio
async def test_a_bare_token_shape_is_found_too(monkeypatch):
    """봉투가 없는 맨 모델(ste·TestScope 관례)도 같은 독자로 읽는다 — 게이트웨이 `_mint_user_pat` 과 같은 규칙."""
    _mock_ra(monkeypatch, lambda req: httpx.Response(200, json={"access_token": "bare-tok", "expires_in": 600}))
    assert await ra_sso.ra_user_token(_settings(), email="a@x.com") == "bare-tok"


# ── 캐시 ─────────────────────────────────────────────────────────────────────
@pytest.mark.anyio
async def test_the_token_is_cached_per_email_until_forgotten(monkeypatch):
    """RA 는 발급마다 접속 이력에 한 줄을 남긴다 — PPT 를 연달아 올릴 때마다 받으면 그 사람의 RA 로그인이 부푼다."""
    seen = _mock_ra(monkeypatch, _ok())
    s = _settings()
    assert await ra_sso.ra_user_token(s, email="a@x.com") == TOKEN
    assert await ra_sso.ra_user_token(s, email="A@X.com") == TOKEN
    assert len(seen) == 1, "같은 사람(대소문자만 다름)이면 다시 받지 않는다"
    await ra_sso.ra_user_token(s, email="b@x.com")
    assert len(seen) == 2, "다른 사람은 따로 받는다"
    ra_sso.forget("A@x.com")
    await ra_sso.ra_user_token(s, email="a@x.com")
    assert len(seen) == 3, "RA 가 거절한 토큰(401)을 잊으면 다음 호출이 새로 받는다"


@pytest.mark.anyio
async def test_cache_ends_before_the_token_does(monkeypatch):
    """만료 직전 토큰을 쓰지 않는다 — expires_in 보다 2분 일찍, 그래도 11시간을 넘기지 않는다."""
    _mock_ra(monkeypatch, _ok(expires_in=3600))
    now = time.monotonic()
    await ra_sso.ra_user_token(_settings(), email="a@x.com")
    exp = ra_sso._CACHE["a@x.com"][1] - now
    assert 3600 - ra_sso.EARLY_S - 5 < exp <= 3600 - ra_sso.EARLY_S + 1

    ra_sso._CACHE.clear()
    _mock_ra(monkeypatch, _ok(expires_in=7 * 24 * 3600))
    now = time.monotonic()
    await ra_sso.ra_user_token(_settings(), email="a@x.com")
    assert ra_sso._CACHE["a@x.com"][1] - now <= ra_sso.MAX_TTL_S + 1


@pytest.mark.anyio
async def test_a_nearly_expired_or_odd_expiry_is_handled(monkeypatch):
    seen = _mock_ra(monkeypatch, _ok(expires_in=60))
    s = _settings()
    assert await ra_sso.ra_user_token(s, email="a@x.com") == TOKEN
    assert "a@x.com" not in ra_sso._CACHE, "2분도 안 남은 토큰은 캐시하지 않는다"
    await ra_sso.ra_user_token(s, email="a@x.com")
    assert len(seen) == 2
    # bool·문자열이면 수명을 모르는 것이다 — 상한만 쓴다(True 를 1초로 읽지 않는다)
    for odd in (True, "43200", None):
        ra_sso._CACHE.clear()
        _mock_ra(monkeypatch, _ok(expires_in=odd))
        now = time.monotonic()
        await ra_sso.ra_user_token(s, email="a@x.com")
        assert ra_sso._CACHE["a@x.com"][1] - now > ra_sso.MAX_TTL_S - 5, odd


# ── 실패는 None, 비밀·토큰은 로그에 없다 ─────────────────────────────────────
@pytest.mark.anyio
async def test_ra_side_off_404_is_none_and_logged_once(monkeypatch, caplog):
    """RA 가 아직 위임을 안 켰다(HEAX_SSO_SECRET 없음) — 설정 상태라 매번 남기면 소음이다."""
    caplog.set_level(logging.INFO, logger="hwax.ra_sso")
    seen = _mock_ra(monkeypatch, lambda req: httpx.Response(404, json={"detail": "Not Found"}))
    s = _settings()
    assert await ra_sso.ra_user_token(s, email="a@x.com") is None
    assert await ra_sso.ra_user_token(s, email="a@x.com") is None
    assert len(seen) == 2, "꺼짐은 캐시하지 않는다 — RA 가 켜면 바로 쓰인다"
    offs = [r for r in caplog.records if "404" in r.getMessage()]
    assert len(offs) == 1 and offs[0].levelno == logging.INFO


@pytest.mark.anyio
@pytest.mark.parametrize("resp", [
    httpx.Response(401, json={"detail": "bad secret"}),
    httpx.Response(403, json={"detail": "disabled"}),
    httpx.Response(500, text="boom"),
    httpx.Response(200, text="<html>not json</html>"),
    httpx.Response(200, json={"success": True, "data": {"access_token": "  "}}),
])
async def test_errors_are_none_with_a_warning_and_no_secret_in_logs(monkeypatch, caplog, resp):
    caplog.set_level(logging.DEBUG, logger="hwax.ra_sso")
    _mock_ra(monkeypatch, lambda req: resp)
    assert await ra_sso.ra_user_token(_settings(), email="a@x.com") is None
    assert "a@x.com" not in ra_sso._CACHE
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert SECRET not in caplog.text


@pytest.mark.anyio
async def test_a_connection_error_is_none(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG, logger="hwax.ra_sso")

    def _down(req):
        raise httpx.ConnectError("refused", request=req)

    _mock_ra(monkeypatch, _down)
    assert await ra_sso.ra_user_token(_settings(), email="a@x.com") is None
    assert "ConnectError" in caplog.text and SECRET not in caplog.text


@pytest.mark.anyio
async def test_the_issued_token_is_not_logged(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG, logger="hwax.ra_sso")
    _mock_ra(monkeypatch, _ok())
    await ra_sso.ra_user_token(_settings(), email="a@x.com", name="김철수")
    assert TOKEN not in caplog.text and SECRET not in caplog.text


# ── PPT 가져오기(포털이 RA 를 직접 부르는 곳) ───────────────────────────────
class _Store:
    def __init__(self, conn=None):
        self.conn = conn

    def get_connection(self, *, email, service):
        assert service == "reportarchive"
        return dict(self.conn) if self.conn else None


class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)


PPTX_OK = {"success": True, "data": {"draft": {"title": "t", "pages": [{"name": "p1"}]}, "warnings": []}}


def _ra_handler(*, sso=None, pptx=None):
    def h(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/auth/sso":
            return (sso or _ok())(req)
        assert req.url.path == "/api/imports/pptx", req.url
        return (pptx or (lambda r: httpx.Response(201, json=PPTX_OK)))(req)
    return h


async def _dispatch(monkeypatch, tmp_path, settings, conn=None):
    """`_dispatch_inner` 의 RA 분기만 — 스테이징·권한·챗 PAT·게이트웨이 호출은 가짜로 바꾼다."""
    from app.agent import routes as R

    f = tmp_path / "a.pptx"
    f.write_bytes(b"PK\x03\x04 fake pptx")
    calls = []

    async def _mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, args))
        return {"ok": True}

    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "staged_path", lambda *a, **k: f)
    monkeypatch.setattr(R._upload, "mcp_call", _mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        user_store=_Store(conn), agent_audit=_Audit(), keystore=None)))
    body = R.UploadDispatchReq(staging_id="s1", filename="a.pptx", destination="reportarchive")
    principal = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수")
    out = await R._dispatch_inner(req, body, principal, settings)
    return out, calls


def _pptx_reqs(seen):
    return [r for r in seen if r.url.path == "/api/imports/pptx"]


@pytest.mark.anyio
async def test_ppt_import_uses_the_delegated_token_and_omits_the_workspace(monkeypatch, tmp_path):
    """ste 방식 — 등록 토큰이 없어도 그 사람 명의로 간다. 부서 헤더를 안 싣는다 — RA 가 그 사람 홈 부서로 정한다(ra-request §3)."""
    seen = _mock_ra(monkeypatch, _ra_handler())
    out, calls = await _dispatch(monkeypatch, tmp_path, _settings(), conn=None)
    assert out["stage"] == "done" and out["pages"] == 1
    (imp,) = _pptx_reqs(seen)
    assert imp.headers["Authorization"] == f"Bearer {TOKEN}"
    assert "X-Workspace-Slug" not in imp.headers
    assert [t for t, _ in calls] == ["create_report_draft"]


@pytest.mark.anyio
async def test_ppt_import_prefers_the_delegated_token_but_keeps_a_chosen_workspace(monkeypatch, tmp_path):
    seen = _mock_ra(monkeypatch, _ra_handler())
    await _dispatch(monkeypatch, tmp_path, _settings(), conn={"token": "rat_stored", "workspace": "mx"})
    (imp,) = _pptx_reqs(seen)
    assert imp.headers["Authorization"] == f"Bearer {TOKEN}", "위임이 켜져 있으면 등록 토큰보다 위임이 먼저다"
    assert imp.headers["X-Workspace-Slug"] == "mx"


@pytest.mark.anyio
async def test_without_the_secret_it_is_todays_registered_token(monkeypatch, tmp_path):
    seen = _mock_ra(monkeypatch, _ra_handler())
    await _dispatch(monkeypatch, tmp_path, _settings(ra_sso_secret=""), conn={"token": "rat_stored", "workspace": "dev"})
    assert [r.url.path for r in seen] == ["/api/imports/pptx"], "비밀이 없으면 위임을 부르지도 않는다"
    assert seen[0].headers["Authorization"] == "Bearer rat_stored" and seen[0].headers["X-Workspace-Slug"] == "dev"


@pytest.mark.anyio
async def test_ra_refusing_the_delegation_falls_back_to_a_registered_token(monkeypatch, tmp_path):
    seen = _mock_ra(monkeypatch, _ra_handler(sso=lambda r: httpx.Response(404)))
    out, _ = await _dispatch(monkeypatch, tmp_path, _settings(), conn={"token": "rat_stored", "workspace": ""})
    assert out["stage"] == "done"
    assert _pptx_reqs(seen)[0].headers["Authorization"] == "Bearer rat_stored"


@pytest.mark.anyio
async def test_neither_path_says_which_one_to_fix(monkeypatch, tmp_path):
    """켜져 있는데 RA 가 거절한 것과, 꺼져 있는데 등록이 없는 것은 사람이 할 일이 다르다."""
    from app.auth.errors import AuthError

    _mock_ra(monkeypatch, _ra_handler(sso=lambda r: httpx.Response(401)))
    with pytest.raises(AuthError) as on:
        await _dispatch(monkeypatch, tmp_path, _settings(), conn=None)
    assert on.value.status_code == 502 and "RA 쪽 위임 상태" in on.value.message
    assert "외부 연결" not in on.value.message, "위임 모드 화면에는 토큰 붙여넣기가 없다 — 거기로 보내지 않는다"

    with pytest.raises(AuthError) as off:
        await _dispatch(monkeypatch, tmp_path, _settings(ra_sso_secret=""), conn=None)
    assert off.value.status_code == 400 and "개인 토큰 › 외부 연결" in off.value.message


@pytest.mark.anyio
async def test_a_revoked_cached_token_is_reminted_once(monkeypatch, tmp_path):
    """캐시해 둔 위임 토큰을 RA 가 401 로 거절하면(회수·비밀 교체) 한 번만 새로 받아 다시 보낸다 — 게이트웨이와 같은 규칙."""
    ra_sso._CACHE["kim@corp.com"] = ("revoked-tok", time.monotonic() + 3600)

    def pptx(req):
        if req.headers["Authorization"] == "Bearer revoked-tok":
            return httpx.Response(401, json={"detail": "revoked"})
        return httpx.Response(201, json=PPTX_OK)

    seen = _mock_ra(monkeypatch, _ra_handler(pptx=pptx))
    out, _ = await _dispatch(monkeypatch, tmp_path, _settings(), conn=None)
    assert out["stage"] == "done"
    assert [r.url.path for r in seen] == ["/api/imports/pptx", "/api/auth/sso", "/api/imports/pptx"]
    assert seen[-1].headers["Authorization"] == f"Bearer {TOKEN}"


# ── 화면이 RA 카드를 가르는 값 ───────────────────────────────────────────────
@pytest.fixture()
def portal(tmp_path):
    from app.main import app

    made = []

    def make(**over):
        s = Settings(user_store_path=str(tmp_path / "u.sqlite"), local_bootstrap_admins="boss@corp.com", **over)
        app.dependency_overrides[get_settings] = lambda: s
        from app.auth.routes.local import _rl
        _rl.clear()
        c = TestClient(app)
        c.__enter__()
        app.state.user_store = UserStore(s)
        made.append(c)
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "B", "password": "pw123456"})
        assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200
        return c

    yield make
    for c in made:
        c.__exit__(None, None, None)
    app.dependency_overrides.pop(get_settings, None)


def test_connections_list_carries_the_reportarchive_mode(portal):
    on = portal(ra_sso_secret=SECRET).get("/auth/connections")
    assert on.status_code == 200
    body = on.json()
    assert body["reportarchive_mode"] == "sso"
    assert "reportarchive" in body, "기존 키·모양은 그대로다"
    assert SECRET not in on.text, "값은 비밀의 있고 없음뿐이다"
    assert portal(ra_sso_secret="").get("/auth/connections").json()["reportarchive_mode"] == "token"
