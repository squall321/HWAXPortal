# 토큰 화면의 '서버 LLM 에 일 맡기기' 칸 옆에 보이는 이 박스의 스위치 — GET /auth/pat/offload(docs/token-saving/offload-v2.md 3-4)
#
# 포털이 에이전트 서버 /health 의 offload{delegate, draft, transform, result_ask} 와 게이트웨이 /health 의 result_refs.enabled 를 읽어
# 칸마다 참 · 거짓 · null(모름)로 준다. 칸이 없거나 못 닿으면 모름이다 — 꺼짐으로 단정하지 않는다(그쪽 새 판이 아직 안 들어온 박스).
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.routes import pat
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

AGENT, GW = "http://agent.test:9009", "http://gw.test:9110"


@pytest.fixture
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"), jwt_keys_dir=str(tmp_path / "keys"),
                 local_bootstrap_admins="a@corp.com", agent_server_url=AGENT, mcp_gateway_url=GW)
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        yield c
    app.dependency_overrides.pop(get_settings, None)


def _login(client) -> None:
    client.post("/auth/local/signup", json={"email": "a@corp.com", "name": "A", "password": "pw123456"})
    client.post("/auth/local/login", json={"email": "a@corp.com", "password": "pw123456"})


def _serve(monkeypatch, agent: dict, gw: dict) -> list[str]:
    seen: list[str] = []

    async def fake(cli, base):
        seen.append(base)
        return {AGENT: agent, GW: gw}[base]
    monkeypatch.setattr(pat, "_box_health", fake)
    return seen


@pytest.mark.parametrize("agent, gw, want", [
    # 새 판 · 모두 꺼짐 — 화면이 '켜도 도구가 없다' 를 말한다
    ({"offload": {"delegate": False, "draft": False, "transform": False, "result_ask": False}}, {"result_refs": {"enabled": False}},
     {"delegate": False, "draft": False, "transform": False, "result_ask": False, "result_refs": False}),
    # 일부 켬 — 표지는 참 · 거짓이거나 {enabled} 꼴
    ({"offload": {"delegate": True, "draft": {"enabled": True}, "transform": False, "result_ask": True}},
     {"result_refs": {"enabled": True, "min_chars": 20000, "head_chars": 4000, "ttl_days": 7, "stored": 3}},   # 게이트웨이가 확정한 꼴
     {"delegate": True, "draft": True, "transform": False, "result_ask": True, "result_refs": True}),
    # 옛 판 — 칸이 없다 · 못 닿았다(빈 사전) · 꼴이 틀리다 → 모름
    ({"status": "ok"}, {}, {"delegate": None, "draft": None, "transform": None, "result_ask": None, "result_refs": None}),
    ({"offload": ["delegate"]}, {"result_refs": True}, {"delegate": None, "draft": None, "transform": None, "result_ask": None, "result_refs": True}),
    ({"offload": {"delegate": "1", "draft": 1}}, {"result_refs": {"enabled": "yes"}},
     {"delegate": None, "draft": None, "transform": None, "result_ask": None, "result_refs": None}),
])
def test_박스_스위치를_칸마다_참_거짓_모름으로_준다(client, monkeypatch, agent, gw, want):
    seen = _serve(monkeypatch, agent, gw)
    _login(client)
    r = client.get("/auth/pat/offload")
    assert r.status_code == 200, r.text
    assert r.json() == want
    assert sorted(seen) == sorted([AGENT, GW]), "에이전트 서버와 게이트웨이를 하나씩 읽는다"


def test_로그인하지_않으면_주지_않는다(client, monkeypatch):
    seen = _serve(monkeypatch, {}, {})
    r = client.get("/auth/pat/offload")
    assert r.status_code in (401, 403) and seen == []


def _health(handler) -> dict:
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cli:
            return await pat._box_health(cli, "http://x.test:1/")
    return asyncio.run(go())


def test_health_읽기는_200_의_JSON_사전만_받고_나머지는_빈_사전이다():
    assert _health(lambda req: httpx.Response(200, json={"offload": {}})) == {"offload": {}}
    for bad in (lambda req: httpx.Response(503, json={"offload": {}}),        # 내려가는 중
                lambda req: httpx.Response(200, text="<html>"),               # JSON 이 아니다
                lambda req: httpx.Response(200, json=["offload"])):           # 사전이 아니다
        assert _health(bad) == {}

    def refuse(req):
        raise httpx.ConnectError("refused", request=req)
    assert _health(refuse) == {}, "못 닿으면 모름 — 예외를 내지 않는다"


def test_health_주소는_끝_빗금을_떼고_붙인다():
    got = []
    _health(lambda req: got.append(str(req.url)) or httpx.Response(200, json={}))
    assert got == ["http://x.test:1/health"]
