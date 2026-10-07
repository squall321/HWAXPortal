# 심의 전 도우미·전문가 카탈로그 프록시의 응답 한도(AGENT_UNARY_TIMEOUT_S) — 느린 에이전트 서버가 브리프를 붙들지 않고, 만료가 폴백과 사유로 나가는지
"""포털의 비스트리밍 프록시 여덟(좌석 발굴·화두 제안·되묻기·VOC 미리보기 · 전문가 상세·지식카드 목록·카드 한 장 · 그림)은
SSE 릴레이와 같은 클라이언트를 써서 read 가 무제한이었다. 도는 22석 패널 뒤에 도우미가 줄을 서면 브리프의 스피너가
nginx 절단(1시간)까지 돌았고, 그 뒤에야 '실패는 폴백' 계약이 적용됐다 — 왜 그런지는 아무도 말해 주지 않았다.

이제 요청마다 read 600초(AGENT_UNARY_TIMEOUT_S)다. 만료는 실패가 아니라 **기본값으로 진행**이다 — 폴백은 그대로이고
error 가 agent_timeout, message 가 초와 손잡이 이름을 말한다. 연결·쓰기·풀 30초(죽은 상대 감지)는 그대로다.
"""
import socket
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session
from app.main import app

_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U",
                 groups=["feat:deliberation", "feat:expert-chat"])

# (포털 경로, 본문, 만료 때도 그대로 나가야 하는 폴백 칸)
_PROXIES = [
    ("/agent/deliberate/experts", {"message": "힌지 파손"}, {"recommended": [], "pool": []}),
    ("/agent/deliberate/clarify", {"message": "힌지 파손"}, {"applicable": False, "slots": [], "ask": []}),
    ("/agent/deliberate/topic", {"history": [], "fallback": "첫 발화"}, {"topic": "첫 발화", "why": "", "options": []}),
    ("/agent/deliberate/voc", {"message": "힌지 파손"}, {"items": [], "keywords": []}),
    ("/agent/catalog/agent", {"key": "mech-a"}, {}),
    ("/agent/catalog/agent/records", {"key": "mech-a"}, {"total": 0, "items": []}),
    ("/agent/catalog/record", {"id": "r1"}, {"id": "r1"}),
]


@pytest.fixture
def portal():
    app.dependency_overrides[principal_pat_or_session] = lambda: _WHO
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            try:
                yield c
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
        app.dependency_overrides.pop(get_settings, None)


def test_프록시마다_요청별_read_한도를_준다(portal):
    """공유 클라이언트의 read 는 SSE 침묵 한도(13시간)다 — 요청마다 따로 주지 않으면 도우미 하나가 그만큼 매달린다."""
    seen: dict[str, dict] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen[req.url.path] = req.extensions["timeout"]
        return httpx.Response(200, json={}) if req.method == "POST" else httpx.Response(200, content=b"png")

    # 실제 기동과 같은 한도로 만든 클라이언트 — 요청별 값이 없으면 여기 read(46800)가 그대로 걸린다.
    portal.app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler),
                                                      timeout=httpx.Timeout(30.0, read=46800.0))
    for path, body, _fallback in _PROXIES:
        assert portal.post(path, json=body).status_code == 200
    assert portal.get("/agent/artifacts/a.png").status_code == 200
    assert len(seen) == len(_PROXIES) + 1, f"프록시 여덟 중 일부가 에이전트 서버를 안 불렀다: {sorted(seen)}"
    for path, t in seen.items():
        assert t["read"] == 600.0, f"{path}: read 한도가 {t['read']} — AGENT_UNARY_TIMEOUT_S(600)가 아니다"
        assert (t["connect"], t["write"], t["pool"]) == (30.0, 30.0, 30.0), f"{path}: 죽은 상대 감지는 짧게 둔다"


def test_만료는_폴백에_사유와_손잡이를_싣는다(portal):
    def slow(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=req)

    portal.app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(slow))
    for path, body, fallback in _PROXIES:
        got = portal.post(path, json=body).json()
        assert got.pop("error") == "agent_timeout", f"{path}: '연결 못 함' 과 갈라야 한다 — 서버는 살아 있고 느린 것이다"
        msg = got.pop("message")
        assert "600초" in msg and "AGENT_UNARY_TIMEOUT_S" in msg and "기본값으로 진행" in msg, path
        assert got == fallback, f"{path}: 만료 때의 폴백이 종전 '연결 못 함' 폴백과 다르다"
    assert portal.get("/agent/artifacts/a.png").status_code == 502


def test_연결_못_함은_종전_그대로다(portal):
    def down(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=req)

    portal.app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(down))
    for path, body, fallback in _PROXIES:
        assert portal.post(path, json=body).json() == {**fallback, "error": "agent_unreachable"}, path


def test_답하지_않는_서버를_한도만큼만_기다린다(portal):
    """대역이 아니라 실제 소켓 — 연결은 받고 답은 안 하는 서버. 공유 클라이언트의 read(13시간)가 아니라 요청별 한도가 걸린다."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)                       # accept 하지 않는다 — 커널이 연결만 받아 두고 응답은 영영 없다
    try:
        s = Settings(_env_file=None, agent_server_url=f"http://127.0.0.1:{srv.getsockname()[1]}", agent_unary_timeout_s=0.4)
        app.dependency_overrides[get_settings] = lambda: s
        assert portal.app.state.agent_client.timeout.read == 46800.0
        t0 = time.monotonic()
        got = portal.post("/agent/deliberate/topic", json={"history": [], "fallback": "첫 발화"}).json()
        took = time.monotonic() - t0
    finally:
        srv.close()
    assert took < 10, f"한도 0.4초인데 {took:.1f}초를 기다렸다"
    assert got["topic"] == "첫 발화" and got["error"] == "agent_timeout", "만료는 첫 발화로 여는 폴백이다 — 브리프가 안 열리면 안 된다"


def test_0_은_끔이다():
    from app.agent.routes import _unary_timeout

    assert _unary_timeout(Settings(_env_file=None)).read == 600.0
    assert _unary_timeout(Settings(_env_file=None, agent_unary_timeout_s=0)).read is None
    assert Settings(_env_file=None).agent_unary_timeout_s < Settings(_env_file=None).agent_stream_idle_timeout_s, \
        "도우미 한도는 스트림 침묵 한도보다 작다 — 화면 대기가 심의 스트림보다 오래 매달릴 이유가 없다"
