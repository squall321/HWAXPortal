# 웹 챗 Claude 의 모델 · 생각 깊이 고르기 — 포털이 고른 값을 옮기고, 고를 수 있는 사람에게만 목록을 준다(docs/chat-llm-claude CC-8)
"""사용자 요청 11-22 「클로드 버전을 선택할 수 있게 · effort 도」. 포털은 꼴만 보고 옮긴다 — 고를 수 있는 사람인지 · 박스 목록 안인지는 에이전트
서버가 다시 본다(밖이면 기본으로 돌고 답 아래에 알린다). 목록 창구는 Claude 대상(FOR=all 또는 개별 허가 feat:chat-claude)에게만 고를 값을 준다."""
import ast
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

import app.agent.routes as R
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


def test_고른_값만_옮기고_비면_칸이_없다():
    got = _sent(ChatRequest(message="안녕", claude_model="claude-haiku-5-5", claude_effort="low"))
    assert got["claude_model"] == "claude-haiku-5-5" and got["claude_effort"] == "low"
    got = _sent(ChatRequest(message="안녕"))
    assert "claude_model" not in got and "claude_effort" not in got, "고르지 않으면 종전 요청 그대로(박스 기본)"


@pytest.mark.parametrize("kw", [
    {"claude_model": "gpt-5"}, {"claude_model": "Claude-Opus-5-5"}, {"claude_model": "claude-opus 5"},
    {"claude_model": "claude-" + "a" * 60}, {"claude_effort": "ultra"}, {"claude_effort": "MEDIUM"},
])
def test_꼴이_틀린_값은_받지_않는다(kw):
    with pytest.raises(ValidationError):
        ChatRequest(message="안녕", **kw)


def test_에이전트_서버의_요청_꼴에_두_칸이_있다():
    """옮기는 칸은 에이전트 서버 ChatRequest 가 받는 칸이어야 한다 — 없는 칸은 조용히 버려진다(pydantic 기본 extra=ignore)."""
    if not _AGENT_APP.exists():
        pytest.skip(f"형제 리포 없음: {_AGENT_APP}")
    tree = ast.parse(_AGENT_APP.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatRequest")
    fields = {s.target.id for s in cls.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)}
    assert {"claude_model", "claude_effort"} <= fields


_ON = {"claude": {"enabled": True, "for": "feat:chat-claude",
                  "models": [{"id": "claude-opus-5-5", "label": "Claude Opus 5.5"}, {"id": "claude-haiku-5-5", "label": "Claude Haiku 5.5"}],
                  "efforts": ["low", "medium", "high", "xhigh", "max"], "default_model": "claude-opus-5-5", "default_effort": "medium"}}


_REAL_CLIENT = httpx.AsyncClient     # R.httpx 는 httpx 모듈 그 자체다 — 바꿔 끼운 뒤 다시 읽으면 앞 시험의 가짜를 잡는다


def _models(monkeypatch, upstream, groups) -> dict:
    def fake_client(*a, **kw):
        kw.pop("transport", None)
        return _REAL_CLIENT(*a, transport=httpx.MockTransport(upstream), **kw)
    monkeypatch.setattr(R.httpx, "AsyncClient", fake_client)
    who = Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=groups)
    return asyncio.run(R.chat_models(request=None, principal=who))


def test_개별_허가가_있는_사람에게만_목록을_준다(monkeypatch):
    seen = []

    def up(req):
        seen.append(req.url.path)
        return httpx.Response(200, json=_ON)
    got = _models(monkeypatch, up, ["feat:chat-claude", "feat:thinking"])
    assert seen == ["/claude-models"]
    assert got == {"claude": {"eligible": True, "models": _ON["claude"]["models"], "efforts": _ON["claude"]["efforts"],
                              "default_model": "claude-opus-5-5", "default_effort": "medium"}}
    assert _models(monkeypatch, up, ["feat:thinking"]) == {"claude": {"eligible": False}}, "허가 없는 사람은 칸이 없다"


def test_FOR_all_이면_모두에게_꺼졌거나_불통이면_아무에게도(monkeypatch):
    on_all = {"claude": {**_ON["claude"], "for": "all"}}
    assert _models(monkeypatch, lambda r: httpx.Response(200, json=on_all), [])["claude"]["eligible"] is True
    assert _models(monkeypatch, lambda r: httpx.Response(200, json={"claude": {"enabled": False}}), ["feat:chat-claude"]) == \
        {"claude": {"eligible": False}}
    assert _models(monkeypatch, lambda r: httpx.Response(404, json={"detail": "Not Found"}), ["feat:chat-claude"]) == \
        {"claude": {"eligible": False}}, "이 창구가 없는 옛 에이전트 서버면 칸을 그리지 않는다"
    odd = {"claude": {**_ON["claude"], "for": "everyone"}}
    assert _models(monkeypatch, lambda r: httpx.Response(200, json=odd), ["feat:chat-claude"])["claude"]["eligible"] is False, \
        "모르는 대상 값은 닫힌 쪽"
