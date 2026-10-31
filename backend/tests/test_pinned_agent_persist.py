# 고른 전문가가 서버 대화에 남아 다른 기기에서도 되살아나는지 — 안 그러면 조용히 풀린다
"""다른 기기에서 대화를 열면 전문가가 사라지던 자리(docs/persona-chat during-F4).

로컬 저장소에는 pinnedAgent 가 있었지만 **서버에는 없었다.** 화면엔 그 전문가의 지난
답이 그대로 남아 있어서, 사용자는 여전히 지정된 줄 알고 다음 질문을 던진다 — 그리고
일반 어시스턴트가 답한다. 실패가 성공과 똑같이 생긴 모양이다.

meta 는 자유 JSON 칸이라 스키마·API 계약은 안 바뀐다. 이 테스트는 **세 지점**이 서로
어긋나지 않는지 본다 — 요청 모델 · 저장 · 프론트 복원.
"""
import json
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


def sse(event: str, data: dict) -> str:
    """SSE 프레임 하나 — 에이전트 서버 _sse 와 같은 꼴."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# 고른 전문가가 답한 턴 — 일반 챗의 끝 꼴(result 뒤 done)
ANSWER_TURN = sse("result", {"type": "text", "content": "답"}) + sse("done", {})
# Thinking 이 답한 턴 — 좌석 둘을 불러 하나는 답하고 하나는 기권한 뒤 요약 글(에이전트 서버 thinking._run_thinking 의 꼴)
THINK_SUMMARY = "Thinking 요약 — 1명 답변 · 1명 기권"
THINK_TURN = "".join((
    sse("think", {"kind": "roster", "hop": 0, "seats": [{"key": "cae-b", "name": "구조 해석 전문가", "domain": "cae"},
                                                        {"key": "rel-c", "name": "신뢰성 전문가", "domain": "rel"}]}),
    sse("think", {"kind": "screen", "key": "cae-b", "passed": True, "hits": 3, "reason": ""}),
    sse("think", {"kind": "screen", "key": "rel-c", "passed": True, "hits": 2, "reason": ""}),
    sse("think", {"kind": "verdict", "key": "cae-b", "verdict": "answer", "scope": "구조"}),
    sse("think", {"kind": "answer", "key": "cae-b", "name": "구조 해석 전문가", "domain": "cae", "text": "응력 집중입니다",
                  "basis": []}),
    sse("think", {"kind": "verdict", "key": "rel-c", "verdict": "pass", "scope": "소관 밖", "refer": []}),
    sse("think", {"kind": "summary", "answered": 1, "passed": 1, "screened_out": 0, "errored": 0, "capped": 0, "hops": 0,
                  "no_answer": False}),
    sse("token", {"delta": THINK_SUMMARY}), sse("result", {"type": "text", "content": THINK_SUMMARY}), sse("done", {}),
))
# 심의가 발언 없이 끝난 턴 — 불량 환기(VOC)의 앞글만 흐르고 첫 발언 전에 끊겼다(에이전트 서버 deliberation 의 stage recall ·
# stream_head 뒤 _detach_stream 의 오류). 포털은 받은 글(앞글)을 답으로 남긴다.
DELIB_HEAD = "최근 불량 이슈 — 힌지 파손 3건"
DELIB_NO_TURNS = "".join((
    sse("delib", {"kind": "stage", "stage": "recall"}),
    sse("delib", {"kind": "evidence", "source": "SignalForge VOC", "text": DELIB_HEAD, "included": True}),
    sse("token", {"delta": DELIB_HEAD}),
    sse("error", {"message": "심의 오류: RuntimeError('좌석 소집 실패')"}),
    sse("done", {}),
))


def relay_turn(raw: str = ANSWER_TURN, *, message: str = "힌지 강도 봐 줘", **body) -> list[dict]:
    """챗 한 턴을 가짜 에이전트 서버(raw SSE)로 흘리고 서버 대화에 남은 메시지를 돌려준다(test_conv_save_full 과 같은 길).
    화면 시험(test_persona_chat_in_browser)도 이것으로 서버 사본을 만든다 — 포털이 적는 꼴을 손으로 옮겨 적으면 둘이 어긋나도 모른다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat", "feat:thinking", "feat:expert-chat"])
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, stream=_Body(raw.encode()), headers={"content-type": "text/event-stream"})))
            try:
                cid = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
                r = c.post("/agent/chat", json={"message": message, "conversation_id": cid, **body})
                assert r.status_code == 200, r.text
                return c.get(f"/agent/conversations/{cid}").json()["messages"]
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


_PIN = {"pinned_agent": "mech-a", "pinned_agent_name": "기구 강도 전문가"}


def test_띵킹이_답한_턴은_답_meta_에_answered_by_think_를_적는다():
    """고른 전문가가 답했는지는 보낸 요청이 아니라 그 턴에 흐른 프레임으로 가린다 — 에이전트 서버는 '/띵킹' 같은 슬래시 트리거로도
    띵킹을 먼저 연다(app.py chat 의 is_thinking(req.message) or req.thinking). 요청의 thinking 은 거짓이어도 답은 여러 전문가의 것이다.
    표지가 없으면 화면이 서버 사본에서 그 요약을 고른 전문가의 말풍선으로 되살렸다(docs/leftovers-1017 B11 반대 검토)."""
    msgs = relay_turn(THINK_TURN, message="/띵킹 힌지 강도 봐 줘", **_PIN)
    assert msgs[0]["role"] == "user" and msgs[0]["meta"] == _PIN, msgs[0]
    assert msgs[1]["role"] == "assistant" and msgs[1]["content"] == THINK_SUMMARY
    assert msgs[1]["meta"] == {"answered_by": "think"}, msgs[1]


def test_심의가_발언_없이_끝난_턴도_answered_by_delib_를_적는다():
    """발언이 하나라도 남으면 화면은 결정문으로 가른다 — 첫 발언 전에 끝난 심의(멈춤 · 끊김)는 발언이 없어 일반 답처럼 보였다."""
    msgs = relay_turn(DELIB_NO_TURNS, message="/심의 힌지 파손 원인", **_PIN)
    assert [m["role"] for m in msgs] == ["user", "assistant"], msgs
    assert msgs[1]["content"] == DELIB_HEAD and msgs[1]["meta"]["answered_by"] == "delib", msgs[1]


def test_띵킹을_켜고_보내도_일반_챗이_답했으면_표지가_없다():
    """확인 카드의 답(단추 · '실행')은 Thinking 을 켜 두어도 일반 챗이 고른 전문가로 답한다(에이전트 서버 _confirm_reply — HA-29).
    요청의 thinking 을 사람 발화에 적어 거르면 그 답의 말풍선이 서버 사본에서 사라졌다 — 사람 발화에는 고른 전문가만 적는다."""
    msgs = relay_turn(**_PIN, thinking=True)
    assert msgs[0]["meta"] == _PIN, msgs[0]
    assert msgs[1]["content"] == "답" and msgs[1]["meta"] is None, msgs[1]


def test_지정만_했으면_고른_전문가만_적고_띵킹만이면_meta_가_없다():
    assert relay_turn(**_PIN)[0]["meta"] == _PIN
    assert relay_turn(thinking=True)[0]["meta"] is None, "고른 전문가가 없으면 적을 까닭이 없다 — 종전 그대로"


@pytest.mark.skipif(not (_FRONT.parent / "node_modules" / "typescript").exists(), reason="frontend node_modules(typescript) 가 없다")
def test_서버_사본의_답에_보낼_때와_같은_규칙으로_고른_전문가를_되살린다():
    """화면은 보낼 때 답에 persona 를 찍고(D-3) 띵킹 · 심의가 답하면 그리지 않는다(MessageList — 좌석마다 자기 버블). 서버 사본에서 되살릴
    때도 같은 답이 같은 말풍선이어야 한다. 무엇이 답했는지로 가른다 — 띵킹 · 심의(포털 중계가 적은 answered_by — '/띵킹' 슬래시 · 발언
    없이 끝난 심의도) · 발언이 앞선 결정문 · 루틴의 답 · 보내기 알림에는 붙이지 않고, 한 발화의 첫 답에만 붙인다. 보낸 요청의 Thinking
    켜짐은 보지 않는다 — 확인 카드의 답은 Thinking 을 켜 두어도 고른 전문가가 답한다."""
    from tests.test_front_window_payload import _node

    pin = {"pinned_agent": "mech-a", "pinned_agent_name": "기구 강도 전문가"}
    rid = "8f3c2a9e0d1b4c5aa6e7f8091a2b3c4d"
    server = [
        {"role": "user", "content": "지정", "ts": 1, "meta": pin},
        {"role": "assistant", "content": "답1", "ts": 2},
        {"role": "assistant", "content": "알림", "ts": 3, "meta": {"upload": True}},
        {"role": "user", "content": "/띵킹 힌지 강도 봐 줘", "ts": 4, "meta": pin},
        {"role": "assistant", "content": "답2", "ts": 5, "meta": {"answered_by": "think"}},
        {"role": "user", "content": "루틴", "ts": 6, "meta": pin},
        {"role": "assistant", "content": "답3", "ts": 7, "meta": {"routine": {"run_id": rid, "title": "r", "state": "done"}}},
        {"role": "user", "content": "/심의 x", "ts": 8, "meta": pin},
        {"role": "persona", "persona": "cae-b", "round": 1, "content": "입장", "ts": 9},
        {"role": "assistant", "content": "결정문", "ts": 10, "meta": {"answered_by": "delib"}},
        {"role": "user", "content": "이름 없이", "ts": 11, "meta": {"pinned_agent": "cae-b"}},
        {"role": "assistant", "content": "답4", "ts": 12},
        {"role": "assistant", "content": "답5", "ts": 13},
        {"role": "user", "content": "지정 없음", "ts": 14},
        {"role": "assistant", "content": "답6", "ts": 15},
        {"role": "user", "content": "/심의 힌지 파손 원인", "ts": 16, "meta": pin},
        {"role": "assistant", "content": "앞글", "ts": 17, "meta": {"delib_evidence": [{"source": "VOC"}], "answered_by": "delib"}},
        {"role": "user", "content": "실행 — 확인 번호 cf-1", "ts": 18, "meta": pin},
        {"role": "assistant", "content": "답7", "ts": 19},
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
        ["앞글", None, False],
        ["답7", {"key": "mech-a", "name": "기구 강도 전문가"}, False],
    ], got
