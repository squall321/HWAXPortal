# 관리자 '도구 검색 검토' — 게이트웨이 검색 고리 창구를 공유 비밀로 부르고 관리자 · CSRF 를 요구하는지(docs/request-1029 E-9 ②)
"""포털은 저장하지 않고 게이트웨이 창구(/search-log · /search-review · /search-eval)를 공유 비밀로 부른다. 원장 · 토큰 저장소는 임시 폴더에,
게이트웨이는 MockTransport 다. 응답 꼴은 게이트웨이 `_search_log_view` 가 내는 그대로다(HWAXMcpGateway test_gateway.py 의 E-9 시험이 그 꼴을 잠근다).
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.cookies import CSRF_COOKIE
from app.auth.routes import tool_search_review as tsr
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PW = "pw123456"
BASE = "/auth/admin/tool-search"
LOG = {"days": 7, "count": 1, "fingerprint": "6c8512116255", "searches": [
    {"id": "3f9a1c0b7d2e", "d": "2026-10-29", "ts": 1793260800, "q": "보고서 요약해줘", "mode": "substring", "fp": "6c8512116255",
     "top": ["signalforge:digest", "signalforge:list"], "via": {"signalforge:digest": ["syn:요약"]},
     "boost_only": ["signalforge:digest"], "outcomes": [{"t": "signalforge:digest", "r": 1, "ok": True}]}]}


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """boss = 원장 관리자 · user = 활성 일반 사용자. 게이트웨이는 reply 로 답한다."""
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), upload_staging_dir=str(tmp_path / "staging"),
                 local_bootstrap_admins="boss@corp.com", gateway_shared_token="gw-test-secret",
                 mcp_gateway_url="http://gw.test/")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    seen: list[httpx.Request] = []
    gw = {"reply": lambda req: httpx.Response(200, json=LOG)}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return gw["reply"](req)
    real = httpx.AsyncClient
    monkeypatch.setattr(tsr.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.token_store)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)
        for email in ("boss@corp.com", "user@corp.com"):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        yield c, s, gw, seen
        app.state.user_store, app.state.token_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


def test_관리자만_보고_게이트웨이에_공유_비밀과_조건을_넘긴다(box):
    c, _s, _gw, seen = box
    h = _login(c, "user@corp.com")
    assert c.get(f"{BASE}/log").status_code == 403
    assert c.post(f"{BASE}/review", json={"q": "x", "verdict": "ok", "gold": ["a:b"]}, headers=h).status_code == 403
    assert c.post(f"{BASE}/eval", headers=h).status_code == 403
    assert not seen, "일반 사용자의 요청은 게이트웨이에 닿지 않는다"
    _login(c, "boss@corp.com")
    r = c.get(f"{BASE}/log", params={"days": 3, "limit": 50, "q": "요약"})
    assert r.status_code == 200 and r.json() == LOG
    [req] = seen
    assert req.method == "GET" and req.url.path == "/search-log" and req.url.host == "gw.test"
    assert dict(req.url.params) == {"days": "3", "limit": "50", "q": "요약"}
    assert req.headers["authorization"] == "Bearer gw-test-secret"


def test_표시와_평가는_CSRF_를_요구하고_본문을_그대로_넘긴다(box):
    c, _s, gw, seen = box
    h = _login(c, "boss@corp.com")
    body = {"q": "보고서 요약해줘", "verdict": "gold", "gold": ["signalforge:digest"], "memo": "1위가 맞다", "qid": "3f9a1c0b7d2e"}
    assert c.post(f"{BASE}/review", json=body).status_code == 403, "CSRF 머리가 없다"
    assert not seen
    gw["reply"] = lambda req: httpx.Response(200, json={"ok": True, "id": "box-0123456789", "removed": False, "pairs": 1})
    r = c.post(f"{BASE}/review", json=body, headers=h)
    assert r.status_code == 200 and r.json()["pairs"] == 1
    assert seen[-1].url.path == "/search-review" and json.loads(seen[-1].content) == body
    gw["reply"] = lambda req: httpx.Response(200, json={"fingerprint": "6c8512116255", "base": "6c8512116255", "pairs": {},
                                                        "variants": {}, "changed": [], "changed_count": 0, "seconds": 1.2})
    assert c.post(f"{BASE}/eval").status_code == 403
    r = c.post(f"{BASE}/eval", headers=h)
    assert r.status_code == 200 and r.json()["seconds"] == 1.2 and seen[-1].url.path == "/search-eval"
    assert c.post(f"{BASE}/review", json={**body, "verdict": "maybe"}, headers=h).status_code == 422


@pytest.mark.parametrize("status, payload, want, text", [
    (401, {"error": "unauthorized"}, 502, "공유 비밀"),
    (404, None, 502, "낡았다"),
    (409, {"error": "평가가 이미 돌고 있다 — 끝난 뒤 다시"}, 409, "평가가 이미 돌고 있다"),
    (400, {"error": "gold 는 '앱키:원래 이름' 1 ~ 10개"}, 400, "앱키:원래 이름"),
    (500, {"error": "boom"}, 502, "게이트웨이 500 — boom"),
])
def test_게이트웨이_답을_포털_답으로_옮긴다(box, status, payload, want, text):
    c, _s, gw, _seen = box
    _login(c, "boss@corp.com")
    gw["reply"] = lambda req: httpx.Response(status, json=payload) if payload is not None else httpx.Response(status, text="Not Found")
    r = c.get(f"{BASE}/log")
    assert r.status_code == want and text in r.json()["detail"], r.json()


def test_닿지_못하거나_공유_비밀이_없으면_까닭을_말한다(box):
    c, s, gw, seen = box
    _login(c, "boss@corp.com")

    def down(req):
        raise httpx.ConnectError("refused", request=req)
    gw["reply"] = down
    r = c.get(f"{BASE}/log")
    assert r.status_code == 502 and "닿지 못했다" in r.json()["detail"]
    s.gateway_shared_token = ""
    n = len(seen)
    r = c.get(f"{BASE}/log")
    assert r.status_code == 503 and "GATEWAY_SHARED_TOKEN" in r.json()["detail"] and len(seen) == n, "비밀이 없으면 부르지 않는다"
