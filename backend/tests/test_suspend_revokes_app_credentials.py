# 사용자를 정지하면 앱 쪽 자격도 회수한다 — 포털 PAT 만 폐기해 ste·RA·게이트웨이가 든 그 사람 토큰은 그대로 남았다(8차 요청 §7)
"""정지 분기는 포털 PAT 만 폐기했다. 그 사람이 ste 에서 받은 토큰(12시간), 포털이 메모리에 든 RA 위임 토큰, 게이트웨이가
든 그 사람 명의 토큰·연결·권한 캐시는 만료될 때까지 남았다.

여기서 고정하는 것.
  · 셋을 모두 시도한다 — ste `POST /api/auth/sso/revoke`(이메일만, X-Heax-Client 는 hwax-portal) · RA 캐시 · 게이트웨이
    `POST /conn-invalidate`. 대상은 **정지된 사람**이다(누른 관리자가 아니다).
  · best-effort 다 — 하나가 실패해도 나머지는 가고, 정지는 그대로 적용된다. 실패는 WARNING 으로 남는다(INFO 는 버려진다).
  · 그 박스에 꺼진 연동(비밀 없음)은 부르지 않고 실패로도 적지 않는다.

ste·게이트웨이는 HTTP 대역으로 받는다(실제 서비스를 부르지 않는다). 원장·토큰 저장소는 임시 폴더에 만든다.
"""
import logging
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth import ra_sso
from app.auth.cookies import CSRF_COOKIE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PW = "pw123456"
STE_SECRET = "ste-test-secret-0000"
GW_SECRET = "gw-test-secret-0000"


class _Net:
    """ste 와 게이트웨이의 대역. 받은 요청을 순서대로 적고, 고장 내라고 한 쪽은 그렇게 답한다."""

    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.broken: dict[str, str] = {}          # host → refuse | boom | <HTTP 상태>
        self.status_at_call: list[str] = []       # 요청을 받는 순간 원장의 그 사람 상태

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        row = app.state.user_store.get("user@corp.com")
        self.status_at_call.append((row or {}).get("status", ""))
        how = self.broken.get(request.url.host)
        if how == "refuse":
            raise httpx.ConnectError("refused", request=request)
        if how == "boom":
            raise RuntimeError("대역이 던진 예기치 않은 오류")
        return httpx.Response(int(how) if how else 200, json={"ok": True})

    def to(self, host: str) -> list[httpx.Request]:
        return [r for r in self.calls if r.url.host == host]


@pytest.fixture()
def box(tmp_path, monkeypatch):
    made: dict = {}

    def _make(**over):
        s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                     token_store_path=str(tmp_path / "tokens.sqlite"), local_bootstrap_admins="boss@corp.com",
                     **{"ste_sso_secret": STE_SECRET, "ste_base_url": "http://ste.test/ste",
                        "gateway_shared_token": GW_SECRET, "mcp_gateway_url": "http://gw.test:9110", **over})
        app.dependency_overrides[get_settings] = lambda: s
        from app.auth.routes.local import _rl
        _rl.clear()
        c = TestClient(app)
        c.__enter__()
        made["c"], made["keep"] = c, (app.state.user_store, app.state.token_store)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)   # 기동 뒤 교체 — 실 저장소를 안 쓴다
        net = _Net()
        real = httpx.AsyncClient

        def _client(*a, **kw):                     # 진입 뒤에 바꾼다 — 앱이 기동 때 만든 클라이언트는 그대로 둔다
            kw["transport"] = httpx.MockTransport(net.handler)
            return real(*a, **kw)

        monkeypatch.setattr(httpx, "AsyncClient", _client)
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": PW})
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        app.state.token_store.record_pat(jti="user-pat", sub="user@corp.com", email="user@corp.com", name="t",
                                         aud=["mcp-gateway"], scopes=["read"], created=1, exp=4102444800)
        # 포털이 메모리에 든 RA 위임 토큰 — 정지될 사람 것과, 건드리면 안 되는 남의 것
        ra_sso._CACHE.clear()
        ra_sso._CACHE["user@corp.com"] = ("ra-tok-user", time.monotonic() + 3600)
        ra_sso._CACHE["other@corp.com"] = ("ra-tok-other", time.monotonic() + 3600)
        assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": PW}).status_code == 200
        return c, net, {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}

    yield _make
    ra_sso._CACHE.clear()
    if made:
        app.state.user_store, app.state.token_store = made["keep"]
        made["c"].__exit__(None, None, None)
    app.dependency_overrides.pop(get_settings, None)


def _suspend(c, h, email="user@corp.com", status="disabled"):
    return c.post(f"/auth/local/users/{email}/status", json={"status": status}, headers=h)


def _is_suspended() -> bool:
    return (app.state.user_store.get("user@corp.com")["status"] == "disabled"
            and "user-pat" in app.state.token_store.revoked_jtis())


# ── 셋 모두 ──────────────────────────────────────────────────────────────────
def test_정지하면_ste_RA_게이트웨이_셋을_모두_회수한다(box):
    c, net, h = box()
    r = _suspend(c, h, "User@Corp.com")
    assert r.status_code == 200 and r.json()["pats_revoked"] == 1, r.text
    assert _is_suspended()

    assert len(net.to("ste.test")) == 1, "ste 에 회수를 부르지 않았다 — 그 사람의 ste 토큰이 만료(12시간)까지 산다"
    (ste,) = net.to("ste.test")
    assert ste.method == "POST" and ste.url.path == "/ste/api/auth/sso/revoke"
    assert ste.headers["x-heax-gateway-secret"] == STE_SECRET
    assert ste.headers["x-heax-user-email"] == "user@corp.com", "정지된 사람의 토큰이다 — 누른 관리자의 것이 아니다"
    assert ste.headers["x-heax-client"] == "hwax-portal", "게이트웨이(gateway)가 받은 토큰과 서로 회수하지 않는다"
    assert "x-heax-user-name" not in ste.headers, "회수는 이메일만 싣는다"

    (gw,) = net.to("gw.test")
    assert gw.method == "POST" and gw.url.path == "/conn-invalidate"
    assert dict(gw.url.params) == {"email": "user@corp.com"}, "그 사람 것만 비운다"
    assert gw.headers["authorization"] == f"Bearer {GW_SECRET}"

    assert "user@corp.com" not in ra_sso._CACHE and "other@corp.com" in ra_sso._CACHE
    assert set(net.status_at_call) == {"disabled"}, "정지를 먼저 적는다 — 앱 호출이 늦거나 매달려도 정지는 이미 걸려 있다"
    assert r.json()["app_revocations"] == {"ste": "ok", "reportarchive": "ok", "gateway": "ok"}


# ── 하나가 실패해도 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("broken", ["ste:refuse", "ste:500", "ste:boom", "gateway:refuse", "gateway:401",
                                    "gateway:boom", "reportarchive:boom"])
def test_하나가_실패해도_나머지와_정지는_그대로_간다(box, broken, monkeypatch, caplog):
    c, net, h = box()
    app_name, how = broken.split(":")
    if app_name == "reportarchive":
        def boom(_email):
            raise RuntimeError("캐시가 던진 예기치 않은 오류")
        monkeypatch.setattr(ra_sso, "forget", boom)
    else:
        net.broken[{"ste": "ste.test", "gateway": "gw.test"}[app_name]] = how
    with caplog.at_level(logging.WARNING):
        r = _suspend(c, h)
    assert r.status_code == 200, f"앱 쪽 실패가 정지를 막았다: {r.status_code} {r.text}"
    assert _is_suspended()
    # 셋 다 시도됐다 — 고장 난 쪽도 불리긴 했고, 나머지 둘은 그 실패와 무관하게 갔다
    assert len(net.to("ste.test")) == 1 and len(net.to("gw.test")) == 1
    if app_name != "reportarchive":
        assert "user@corp.com" not in ra_sso._CACHE
    got = r.json()["app_revocations"]
    assert got == {name: ("failed" if name == app_name else "ok") for name in ("ste", "reportarchive", "gateway")}, got
    # 실패는 남는 수준(WARNING)으로, 누구의 어느 앱인지 적는다. 비밀은 싣지 않는다.
    said = [rec.getMessage() for rec in caplog.records if rec.levelno >= logging.WARNING and "user@corp.com" in rec.getMessage()]
    assert any(app_name in m for m in said), f"실패가 로그에 없다: {[rec.getMessage() for rec in caplog.records]}"
    assert not any(STE_SECRET in rec.getMessage() or GW_SECRET in rec.getMessage() for rec in caplog.records)


# ── 부르지 않는 경우 ─────────────────────────────────────────────────────────
def test_다시_활성화할_때는_아무것도_회수하지_않는다(box):
    c, net, h = box()
    app.state.user_store.set_status("user@corp.com", "disabled")
    r = _suspend(c, h, status="active")
    assert r.status_code == 200
    assert net.calls == [] and "user@corp.com" in ra_sso._CACHE
    assert "user-pat" not in app.state.token_store.revoked_jtis()
    assert r.json()["app_revocations"] == {}


def test_꺼진_연동은_부르지_않고_실패로도_적지_않는다(box, caplog):
    c, net, h = box(ste_sso_secret="", gateway_shared_token="")
    with caplog.at_level(logging.WARNING):
        r = _suspend(c, h)
    assert r.status_code == 200 and _is_suspended()
    assert net.calls == [], "비밀이 없는 연동을 불렀다"
    assert "user@corp.com" not in ra_sso._CACHE, "RA 캐시는 설정과 무관하게 포털 안에서 비운다"
    assert r.json()["app_revocations"] == {"ste": "off", "reportarchive": "ok", "gateway": "off"}
    assert not [rec for rec in caplog.records if "회수" in rec.getMessage()], "꺼진 것을 실패로 적으면 늘 울리는 경보가 된다"


def test_없는_사용자는_404_이고_아무것도_부르지_않는다(box):
    c, net, h = box()
    assert _suspend(c, h, "nobody@corp.com").status_code == 404
    assert net.calls == [] and "user@corp.com" in ra_sso._CACHE


# ── 로그아웃 훅은 그대로 ─────────────────────────────────────────────────────
def test_로그아웃_때의_ste_회수는_종전대로_본인_것만_한다(box):
    """정지와 로그아웃이 같은 호출을 쓴다 — 한쪽을 고치다 다른 쪽이 갈리지 않게 같은 자리에서 본다."""
    c, net, h = box()
    r = c.post("/systems/ste/credential/revoke", headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True, "revoked": True}
    (ste,) = net.to("ste.test")
    assert ste.headers["x-heax-user-email"] == "boss@corp.com" and ste.headers["x-heax-client"] == "hwax-portal"
    net.broken["ste.test"] = "refuse"
    assert c.post("/systems/ste/credential/revoke", headers=h).json() == {"ok": True, "revoked": False}


# ── 권한을 거둘 때도 — 관리자 해제·소속·개별 허가 ─────────────────────────────────────────────────
# 게이트웨이는 그 사람의 권한(keys·is_admin)을 60초 캐시한다(GATEWAY_ACCESS_ENT_TTL). 정지는 그 캐시를 깨는데 관리자 해제와
# 소속·허가 변경은 깨지 않았다 — 포털 화면에서는 바로 거둬졌는데 개인 Claude(PAT) 길로는 한동안 옛 권한으로 도구가 불린다.
def _patch(c, h, email="user@corp.com", **body):
    return c.patch(f"/auth/access/users/{email}", json=body, headers=h)


def test_관리자를_해제하면_게이트웨이의_그_사람_캐시를_깬다(box):
    c, net, h = box()
    app.state.user_store.set_groups("user@corp.com", ["portal-admin"])
    assert _patch(c, h, admin=False).status_code == 200
    (req,) = net.to("gw.test")
    assert (req.method, req.url.path, req.url.params["email"]) == ("POST", "/conn-invalidate", "user@corp.com")
    assert req.headers["authorization"] == f"Bearer {GW_SECRET}"
    assert net.to("ste.test") == [], "ste 원장의 토큰은 건드리지 않는다 — 계정은 살아 있다(정지와 다르다)"
    assert "user-pat" in app.state.token_store.revoked_jtis(), "해제는 종전대로 PAT 도 죽인다"


def test_소속과_허가를_바꿔도_게이트웨이의_그_사람_캐시를_깬다(box):
    c, net, h = box()
    assert _patch(c, h, email="USER@corp.com", grants=[]).status_code == 200
    assert [r.url.params["email"] for r in net.to("gw.test")] == ["user@corp.com"], "원장의 주소(소문자)로 부른다"
    assert _patch(c, h, affiliation="").status_code == 200
    assert len(net.to("gw.test")) == 2


@pytest.mark.parametrize("how", ["refuse", "boom", "500"])
def test_게이트웨이가_고장_나도_권한_변경은_적용된다(box, how):
    """best-effort 다 — 못 깨면 최대 60초 늦게 반영될 뿐이다. 그 때문에 관리자의 저장이 실패하면 안 된다."""
    c, net, h = box()
    net.broken["gw.test"] = how
    app.state.user_store.set_groups("user@corp.com", ["portal-admin"])
    r = _patch(c, h, admin=False, grants=[])
    assert r.status_code == 200 and r.json()["admin"] is False, r.text
    assert app.state.user_store.get("user@corp.com")["groups"] == []


def test_거절된_권한_변경은_게이트웨이를_부르지_않는다(box):
    c, net, h = box()
    assert _patch(c, h, email="boss@corp.com", admin=False).status_code == 409, "자기 자신 해제"
    assert _patch(c, h, email="nobody@corp.com", grants=[]).status_code == 404
    assert _patch(c, h, grants=["plat:no-such"]).status_code == 422
    assert net.to("gw.test") == []


def test_게이트웨이를_안_쓰는_박스에서는_부르지_않는다(box):
    c, net, h = box(gateway_shared_token="")
    assert _patch(c, h, grants=[]).status_code == 200
    assert net.calls == []

