# 고른 전문가가 서버 대화에 남아 다른 기기에서도 되살아나는지 — 안 그러면 조용히 풀린다
"""다른 기기에서 대화를 열면 전문가가 사라지던 자리(docs/persona-chat during-F4).

로컬 저장소에는 pinnedAgent 가 있었지만 **서버에는 없었다.** 화면엔 그 전문가의 지난
답이 그대로 남아 있어서, 사용자는 여전히 지정된 줄 알고 다음 질문을 던진다 — 그리고
일반 어시스턴트가 답한다. 실패가 성공과 똑같이 생긴 모양이다.

meta 는 자유 JSON 칸이라 스키마·API 계약은 안 바뀐다. 이 테스트는 **세 지점**이 서로
어긋나지 않는지 본다 — 요청 모델 · 저장 · 프론트 복원.
"""
import re
from pathlib import Path

import httpx
import pytest

from app.agent.routes import ChatRequest

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_요청_모델이_표시용_이름을_받는다():
    assert "pinned_agent_name" in ChatRequest.model_fields


def test_표시용_이름은_agent_server_로_넘기지_않는다():
    """이름은 포털 안에서만 쓴다 — 중계 페이로드에 끼면 계약이 한 줄 넓어진다."""
    src = (Path(__file__).resolve().parents[1] / "app" / "agent" / "routes.py").read_text("utf-8")
    relay = src[src.index('payload["pinned_agent"]'):]
    relay = relay[:relay.index("\n\n")]
    assert "pinned_agent_name" not in relay


def test_사용자_발화에_고른_전문가를_적어_둔다():
    src = (Path(__file__).resolve().parents[1] / "app" / "agent" / "routes.py").read_text("utf-8")
    blk = src[src.index('role="user", content=body.message'):]
    assert "meta=" in blk[:200], "발화를 저장하면서 전문가를 안 적으면 서버엔 남지 않는다"
    head = src[:src.index('role="user", content=body.message')]
    assert '"pinned_agent", body.pinned_agent' in head[-900:]


def test_프론트가_그_meta_로_복원한다():
    src = (_FRONT / "api" / "conversations.api.ts").read_text("utf-8")
    body = src[src.index("export function serverConvToLocal"):]
    for key in ("pinned_agent", "pinnedAgent", "pinned_agent_name", "pinnedAgentName"):
        assert key in body, f"복원부에 {key} 가 없다 — 저장만 하고 안 읽으면 아무 일도 안 일어난다"


def test_프론트가_이름을_보낸다():
    src = (_FRONT / "api" / "chat.api.ts").read_text("utf-8")
    assert re.search(r"pinned_agent_name:\s*pinnedAgentName", src), \
        "이름을 안 보내면 다른 기기에서 키로만 뜬다"
    ctx = (_FRONT / "state" / "ChatContext.tsx").read_text("utf-8")
    assert "pinnedAgentName: effPinnedAgentName" in ctx, "호출부가 안 실어 보내면 위 줄은 죽은 코드다"


class _Body(httpx.AsyncByteStream):
    """에이전트 서버의 SSE 본문 — 중계는 응답을 스트림으로 읽는다(content= 로 주면 이미 읽힌 응답이라 StreamConsumed)."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    async def __aiter__(self):
        yield self.raw


@pytest.fixture()
def relay():
    """챗 한 턴을 가짜 에이전트 서버로 흘리고 서버 대화에 남은 메시지를 돌려준다(test_conv_save_full 과 같은 길)."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat", "feat:thinking", "feat:expert-chat"])
    raw = b'event: result\ndata: {"type": "text", "content": "\xeb\x8b\xb5"}\n\nevent: done\ndata: {}\n\n'

    def go(**body) -> list[dict]:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})))
            try:
                cid = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
                r = c.post("/agent/chat", json={"message": "힌지 강도 봐 줘", "conversation_id": cid, **body})
                assert r.status_code == 200, r.text
                return c.get(f"/agent/conversations/{cid}").json()["messages"]
            finally:
                app.state.agent_client = real

    try:
        yield go
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def test_띵킹으로_보낸_지정_발화에는_thinking_을_같이_적는다(relay):
    """띵킹이 지정 전문가보다 먼저 갈리므로 그 답은 고른 전문가의 것이 아니다. 화면이 서버 사본에서 말풍선을 되살릴 때(serverMessagesToLocal)
    이 표지로 거른다 — 없으면 여러 전문가의 답이 고른 한 사람의 말풍선으로 되살아난다(docs/leftovers-1017 B11)."""
    msgs = relay(pinned_agent="mech-a", pinned_agent_name="기구 강도 전문가", thinking=True)
    assert msgs[0]["role"] == "user" and msgs[0]["meta"] == {
        "pinned_agent": "mech-a", "pinned_agent_name": "기구 강도 전문가", "thinking": True}, msgs[0]
    assert msgs[1]["role"] == "assistant" and msgs[1]["content"] == "답"


def test_지정만_했으면_thinking_을_적지_않고_띵킹만이면_meta_가_없다(relay):
    assert relay(pinned_agent="mech-a", pinned_agent_name="기구 강도 전문가")[0]["meta"] == {
        "pinned_agent": "mech-a", "pinned_agent_name": "기구 강도 전문가"}
    assert relay(thinking=True)[0]["meta"] is None, "고른 전문가가 없으면 적을 까닭이 없다 — 종전 그대로"


@pytest.mark.skipif(not (_FRONT.parent / "node_modules" / "typescript").exists(), reason="frontend node_modules(typescript) 가 없다")
def test_서버_사본의_답에_보낼_때와_같은_규칙으로_고른_전문가를_되살린다():
    """화면은 보낼 때 답에 persona 를 찍는다(D-3) — 루틴 턴만 빼고. 서버 사본에서 되살릴 때도 같은 규칙이어야 같은 답이 같은 말풍선이다.
    띵킹(여러 전문가) · 심의(좌석마다 자기 버블) · 루틴의 답 · 보내기 알림에는 붙이지 않고, 한 발화의 첫 답에만 붙인다."""
    from tests.test_front_window_payload import _node

    pin = {"pinned_agent": "mech-a", "pinned_agent_name": "기구 강도 전문가"}
    rid = "8f3c2a9e0d1b4c5aa6e7f8091a2b3c4d"
    server = [
        {"role": "user", "content": "지정", "ts": 1, "meta": pin},
        {"role": "assistant", "content": "답1", "ts": 2},
        {"role": "assistant", "content": "알림", "ts": 3, "meta": {"upload": True}},
        {"role": "user", "content": "띵킹", "ts": 4, "meta": {**pin, "thinking": True}},
        {"role": "assistant", "content": "답2", "ts": 5},
        {"role": "user", "content": "루틴", "ts": 6, "meta": pin},
        {"role": "assistant", "content": "답3", "ts": 7, "meta": {"routine": {"run_id": rid, "title": "r", "state": "done"}}},
        {"role": "user", "content": "/심의 x", "ts": 8, "meta": pin},
        {"role": "persona", "persona": "cae-b", "round": 1, "content": "입장", "ts": 9},
        {"role": "assistant", "content": "결정문", "ts": 10},
        {"role": "user", "content": "이름 없이", "ts": 11, "meta": {"pinned_agent": "cae-b"}},
        {"role": "assistant", "content": "답4", "ts": 12},
        {"role": "assistant", "content": "답5", "ts": 13},
        {"role": "user", "content": "지정 없음", "ts": 14},
        {"role": "assistant", "content": "답6", "ts": 15},
    ]
    got = _node(["api/conversations.api.ts", "state/chatStore.ts"],
                "const { serverMessagesToLocal } = require('./api/conversations.api.js');"
                " out(serverMessagesToLocal(input).filter(m => m.role === 'assistant')"
                ".map(m => [m.text, m.persona || null, Boolean(m.delib)]));", server)
    assert got == [
        ["답1", {"key": "mech-a", "name": "기구 강도 전문가"}, False],
        ["알림", None, False],
        ["답2", None, False],
        ["답3", None, False],
        ["결정문", None, True],
        ["답4", {"key": "cae-b"}, False],
        ["답5", None, False],
        ["답6", None, False],
    ], got
