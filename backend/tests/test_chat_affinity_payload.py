# 챗 중계가 서버 대화 id 를 에이전트 서버에 싣는지 — 에이전트가 챗 LLM 호출의 대화 머리(X-Session-Affinity)로 쓴다(docs/request-1029 W-1)
"""10-29 — 한 질문의 LLM 호출 3 ~ 16회가 매번 다른 GPU 복제본으로 가서 접두 캐시를 못 썼다(117쌍 중 1쌍만 같은 복제본). 에이전트 서버는 대화 id 가
있으면 그 해시를, 없으면 '사람 + 턴의 시작' 의 해시를 머리에 싣는다(HWAXAgentServer a478519). 대화 id 는 포털만 안다."""
import ast
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.agent.routes import ChatRequest, _relay_stream
from app.auth.provider import Principal
from app.config import Settings

_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=[])
_AGENT_APP = Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "app.py"


def _sent(body: ChatRequest) -> dict:
    seen: dict = {}

    def upstream(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.read()))
        return httpx.Response(200, stream=httpx.ByteStream(b'event: done\ndata: {}\n\n'), headers={"content-type": "text/event-stream"})

    class _Audit:
        def record(self, **_kw):
            pass

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            return [c async for c in _relay_stream(body, _WHO, _Audit(), Settings(_env_file=None), client)]
    asyncio.run(go())
    return seen


def test_대화_id_가_있으면_싣고_없으면_칸이_없다():
    assert _sent(ChatRequest(message="안녕", conversation_id="conv-1"))["conversation_id"] == "conv-1"
    assert "conversation_id" not in _sent(ChatRequest(message="안녕"))


def test_에이전트_서버의_요청_꼴에_그_칸이_있다():
    """싣는 칸은 에이전트 서버 ChatRequest 가 받는 칸이어야 한다 — 없는 칸은 조용히 버려진다(pydantic 기본 extra=ignore)."""
    if not _AGENT_APP.exists():
        pytest.skip(f"형제 리포 없음: {_AGENT_APP}")
    tree = ast.parse(_AGENT_APP.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatRequest")
    fields = {s.target.id for s in cls.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)}
    assert "conversation_id" in fields
