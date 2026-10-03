# TestScope 토큰 등록 — 다른 조직 포털의 개인 토큰을 /api/auth/me 로 주인 확인(이메일 일치·fail-closed)해 저장하는지
"""docs/sso-delegation. RA 와 같은 '토큰 등록' 이다(TestScope 코드는 고치지 않는다).

  · 주인 확인 — 맨 모델 `{id, email, …}` 의 email 이 포털 계정과 같을 때만 저장한다. 이메일이 없으면(모르겠다) 저장하지 않는다.
  · 거부 사유를 사람 말로 — 401 은 만료·폐기·잘못 복사, 403 은 'read' 범위 없음.
  · 주소(TESTSCOPE_BASE_URL)가 없는 박스는 연결을 내지 않는다 — 화면은 testscope_enabled 로 카드를 가린다.
  · 게이트웨이는 /internal/connections/testscope 로 그 토큰을 읽는다.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings, get_settings

BASE = "http://ts.test:8020"
TOKEN = "tsc_pat_0123456789abcdef"
GW = "gw-test-secret"
_REAL_CLIENT = httpx.AsyncClient


def _me(email="boss@corp.com"):
    return lambda req: httpx.Response(200, json={"id": 7, "email": email, "display_name": "B", "status": "active"})


def _mock_ts(monkeypatch, handler):
    """포털 코드가 만드는 AsyncClient 를 MockTransport 로 바꾼다 — 시험이 진짜 TestScope·게이트웨이를 치면 안 된다."""
    seen: list[httpx.Request] = []

    def _h(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path == "/conn-invalidate":
            return httpx.Response(200, json={"ok": True})
        return handler(req)

    monkeypatch.setattr(httpx, "AsyncClient",
                        lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(_h), **kw))
    return seen


@pytest.fixture
def portal(tmp_path):
    from app.main import app

    made = []

    def make(**over):
        over.setdefault("testscope_base_url", BASE + "/")
        s = Settings(_env_file=None, user_store_path=str(tmp_path / "u.sqlite"),
                     local_bootstrap_admins="boss@corp.com", gateway_shared_token=GW,
                     mcp_gateway_url="http://gw.test:9110", **over)
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


def _stored(c):
    return c.app.state.user_store.get_connection(email="boss@corp.com", service="testscope")


def _put(c, token=TOKEN):
    return c.put("/auth/connections/testscope", json={"token": token},
                 headers={"X-CSRF-Token": c.cookies.get("hwax_csrf")})


# ── 등록 ─────────────────────────────────────────────────────────────────────
def test_a_matching_token_is_stored_and_the_gateway_cache_is_dropped(portal, monkeypatch):
    seen = _mock_ts(monkeypatch, _me("Boss@Corp.com"))
    c = portal()
    r = _put(c, "  " + TOKEN + "  ")
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    assert _stored(c) == {"token": TOKEN, "workspace": ""}, "조직 개념이 없다 — 빈 값"
    me = [q for q in seen if q.url.path == "/api/auth/me"]
    assert len(me) == 1 and str(me[0].url) == BASE + "/api/auth/me", "주소 끝의 / 는 한 번만"
    assert me[0].headers["Authorization"] == f"Bearer {TOKEN}"
    assert any(q.url.path == "/conn-invalidate" for q in seen), "안 깨면 최대 TTL 동안 옛 토큰으로 부른다"


def test_someone_elses_token_is_refused(portal, monkeypatch):
    _mock_ts(monkeypatch, _me("other@corp.com"))
    c = portal()
    r = _put(c)
    assert r.status_code == 400
    assert "other@corp.com" in r.json()["detail"] and "boss@corp.com" in r.json()["detail"]
    assert _stored(c) is None


@pytest.mark.parametrize("resp", [
    httpx.Response(200, json={"id": 7, "display_name": "B"}),
    httpx.Response(200, json={"id": 7, "email": "  "}),
    httpx.Response(200, json=[{"email": "boss@corp.com"}]),
    httpx.Response(200, text="<!doctype html><title>SPA</title>"),
], ids=["no-email", "blank-email", "not-a-dict", "html"])
def test_an_unknown_owner_is_not_stored_fail_closed(portal, monkeypatch, resp):
    """'모르겠다' 는 '맞다' 가 아니다 — 주소가 엉뚱한 SPA 를 가리켜 200 HTML 이 와도 닫는다."""
    _mock_ts(monkeypatch, lambda req: resp)
    c = portal()
    r = _put(c)
    assert r.status_code == 502, r.text
    assert "확인할 수 없습니다" in r.json()["detail"]
    assert _stored(c) is None


@pytest.mark.parametrize("code,needle", [(401, "만료·폐기"), (403, "'read'"), (500, "HTTP 500"), (404, "HTTP 404")])
def test_refusals_are_explained(portal, monkeypatch, code, needle):
    _mock_ts(monkeypatch, lambda req: httpx.Response(code, json={"error": {"code": "x", "message": "m"}}))
    c = portal()
    r = _put(c)
    assert r.status_code == 400 and needle in r.json()["detail"], r.text
    assert _stored(c) is None


def test_an_unreachable_testscope_is_502(portal, monkeypatch):
    def boom(req):
        raise httpx.ConnectError("refused", request=req)
    _mock_ts(monkeypatch, boom)
    c = portal()
    r = _put(c)
    assert r.status_code == 502 and "연결하지 못했습니다" in r.json()["detail"]
    assert _stored(c) is None


def test_a_box_without_testscope_offers_no_connection(portal, monkeypatch):
    seen = _mock_ts(monkeypatch, _me())
    c = portal(testscope_base_url="  ")
    r = _put(c)
    assert r.status_code == 404 and "설정돼 있지 않습니다" in r.json()["detail"]
    assert seen == [] and _stored(c) is None


# ── 해제 ─────────────────────────────────────────────────────────────────────
def test_delete_needs_csrf_and_removes_the_token(portal, monkeypatch):
    seen = _mock_ts(monkeypatch, _me())
    c = portal()
    assert _put(c).status_code == 200
    assert c.delete("/auth/connections/testscope").status_code == 403, "쿠키 세션의 해제는 CSRF 를 본다"
    assert _stored(c) is not None
    seen.clear()
    r = c.delete("/auth/connections/testscope", headers={"X-CSRF-Token": c.cookies.get("hwax_csrf")})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert _stored(c) is None
    assert any(q.url.path == "/conn-invalidate" for q in seen), "해제도 즉시 반영"


# ── 목록 · 게이트웨이 조회 ──────────────────────────────────────────────────────
def test_list_carries_testscope_and_whether_it_is_offered(portal, monkeypatch):
    _mock_ts(monkeypatch, _me())
    c = portal()
    body = c.get("/auth/connections").json()
    assert set(body) == {"reportarchive", "testscope", "reportarchive_mode", "testscope_enabled"}
    assert body["testscope"] is None and body["testscope_enabled"] is True
    assert _put(c).status_code == 200
    got = c.get("/auth/connections")
    meta = got.json()["testscope"]
    assert meta["tail"] == TOKEN[-4:] and meta["workspace"] == ""
    assert TOKEN not in got.text, "토큰 원문은 화면에 안 간다"
    assert portal(testscope_base_url="").get("/auth/connections").json()["testscope_enabled"] is False


def test_the_gateway_reads_the_testscope_token(portal, monkeypatch):
    _mock_ts(monkeypatch, _me())
    c = portal()
    assert _put(c).status_code == 200
    url = "/internal/connections/testscope?email=boss@corp.com"
    r = c.get(url, headers={"Authorization": f"Bearer {GW}"})
    assert r.status_code == 200 and r.json() == {"token": TOKEN, "workspace": ""}
    assert c.get(url, headers={"Authorization": "Bearer nope"}).status_code == 403
    assert c.get("/internal/connections/nope?email=boss@corp.com",
                 headers={"Authorization": f"Bearer {GW}"}).status_code == 404
