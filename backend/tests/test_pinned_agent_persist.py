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
