# 챗 중계가 끝난 턴의 종류(챗 · 띵킹 · 심의 · 루틴)와 답한 모델을 chat_done 감사 줄에 싣는지 — 이용 통계가 턴을 가른다(docs/ops-dashboard M3 가)
"""M1 의 챗 턴 수는 챗 · 심의 · 띵킹 · 루틴을 가르지 못했다(턴 종류를 어디에도 적지 않았다). 중계가 넘기는 바이트에서 사건 이름(think · delib)과 끝의
meta 프레임(models)만 읽어 감사 줄에 싣는다 — 본문은 건드리지 않고(바이트 그대로 넘긴다), 읽다 실패해도 답은 그대로 흐른다. 글 · 질의는 싣지 않는다."""
import asyncio
import json

import httpx
import pytest
from tests.test_usage_stats import NOW, Box

from app.agent import routes
from app.agent.routes import ChatRequest, _relay_stream
from app.auth.provider import Principal
from app.config import Settings

_WHO = Principal(subject="u1@example.com", email="u1@example.com", display_name="U", groups=[])


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


def _relay(frames: list[bytes], body: ChatRequest | None = None, chunk: int | None = None, user_pat: str | None = None):
    """가짜 에이전트 서버의 스트림을 중계해 (넘긴 바이트, 감사 줄들)을 낸다. chunk 를 주면 그 크기로 잘라 흘린다(프레임 경계와 어긋나게)."""
    raw = b"".join(frames)
    parts = [raw] if not chunk else [raw[i:i + chunk] for i in range(0, len(raw), chunk)]
    recs: list[dict] = []

    class _Audit:
        def record(self, **kw):
            recs.append(kw)

    def upstream(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=httpx.ByteStream(b"") if not parts else _Parts(parts), headers={"content-type": "text/event-stream"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            return b"".join([c async for c in _relay_stream(body or ChatRequest(message="안녕"), _WHO, _Audit(), Settings(_env_file=None),
                                                           client, user_pat)])
    return asyncio.run(go()), recs


class _Parts(httpx.AsyncByteStream):
    def __init__(self, parts):
        self.parts = parts

    async def __aiter__(self):
        for p in self.parts:
            yield p


def _done(recs: list[dict]) -> dict:
    [rec] = [r for r in recs if r["event"] == "chat_done"]
    return rec


CHAT = [_sse("status", {"step": "도구"}), _sse("token", {"delta": "답"}), _sse("result", {"type": "text", "content": "답"}),
        _sse("meta", {"models": {"qwen-chat": 3, "glm-5": 1}, "chat_model": "qwen-chat", "thinking": True}), _sse("done", {})]


def test_일반_챗_턴은_chat_이고_답한_모델을_싣는다():
    out, recs = _relay(CHAT)
    assert out == b"".join(CHAT), "넘기는 바이트는 그대로다"
    assert _done(recs)["meta"] == {"kind": "chat", "models": ["glm-5", "qwen-chat"]} and _done(recs)["status"] == "ok"


@pytest.mark.parametrize(("frames", "kind"), [
    ([_sse("think", {"kind": "plan"}), _sse("result", {"type": "text", "content": "x"}), _sse("done", {})], "think"),
    ([_sse("think", {"kind": "plan"}), _sse("delib", {"kind": "stage"}), _sse("done", {})], "delib"),
    ([_sse("delib", {"kind": "personas", "say": "긴 발언 " * 4000}), _sse("meta", {"models": {"glm-5": 40}}), _sse("done", {})], "delib"),
])
def test_띵킹_심의_프레임이_흐른_턴은_그_종류로_적는다(frames, kind):
    for chunk in (None, 7, 4096):
        out, recs = _relay(frames, chunk=chunk)
        assert out == b"".join(frames) and _done(recs)["meta"]["kind"] == kind, chunk


def test_루틴_턴은_routine_이다():
    body = ChatRequest(message="루틴", routine={"id": "r1", "version": 1})
    _out, recs = _relay([_sse("routine", {"kind": "plan"}), _sse("done", {})], body, user_pat="pat")
    assert _done(recs)["meta"]["kind"] == "routine"


def test_모델_표지가_없으면_종류만_적고_이상한_이름은_싣지_않는다():
    _out, recs = _relay([_sse("token", {"delta": "x"}), _sse("done", {})])
    assert _done(recs)["meta"] == {"kind": "chat"}
    _out, recs = _relay([_sse("meta", {"models": {"<script>": 1, "ok-model.v2": 1, "x" * 200: 1, "비밀 질문?": 2}}), _sse("done", {})])
    assert _done(recs)["meta"] == {"kind": "chat", "models": ["ok-model.v2"]}
    _out, recs = _relay([_sse("meta", {"models": {f"m{i:02d}": 1 for i in range(30)}}), _sse("done", {})])
    assert len(_done(recs)["meta"]["models"]) == routes._TURN_MODELS_MAX


def test_읽다_실패해도_답은_그대로_흐르고_끝남은_적힌다(monkeypatch):
    def boom(self, frame):
        raise RuntimeError("통계 칸을 읽다 터졌다")
    monkeypatch.setattr(routes._TurnProbe, "_frame", boom)
    out, recs = _relay(CHAT, chunk=11)
    assert out == b"".join(CHAT) and _done(recs)["meta"] == {"kind": "chat"}


def test_깨진_프레임과_끝없는_한_줄도_답을_막지_않는다(monkeypatch):
    monkeypatch.setattr(routes._TurnProbe, "MAX_BUF", 64)
    frames = [b"event: meta\ndata: {not json\n\n", b"data: " + b"x" * 500 + b"\n\n", _sse("delib", {"kind": "stage"}),
              _sse("meta", {"models": {"glm-5": 1}}), b"event: done\ndata: {}"]          # 마지막 프레임은 끝 표지 없이 끊겼다
    out, recs = _relay(frames, chunk=13)
    assert out == b"".join(frames) and _done(recs)["meta"] == {"kind": "delib", "models": ["glm-5"]}


# ── 이용 통계 ──────────────────────────────────────────────────────────────────────────────────────────────
def test_이용_통계는_턴_종류와_모델을_세고_적기_전의_턴은_따로_말한다(tmp_path):
    box = Box(tmp_path)
    t = int(NOW) - 3600
    box.audit((t, "a@example.com", "chat_done", "ok"),                                           # 적기 전 판의 줄
              (t + 1, "a@example.com", "chat_done", "ok", {"kind": "chat", "models": ["qwen-chat"]}),
              (t + 2, "a@example.com", "chat_done", "ok", {"kind": "chat", "models": ["qwen-chat", "glm-5"]}),
              (t + 3, "b@example.com", "chat_done", "ok", {"kind": "delib", "models": ["glm-5"]}),
              (t + 4, "b@example.com", "chat_done", "ok", {"kind": "think"}),
              (t + 5, "b@example.com", "chat_done", "ok", {"kind": "이상한 값", "models": "문자열"}),
              (t + 6, "b@example.com", "chat_error", "error", {"kind": "chat"}))
    sec = box.build()["sections"]["chat_kinds"]
    assert sec["rows"] == [{"kind": "chat", "turns": 2}, {"kind": "delib", "turns": 1}, {"kind": "think", "turns": 1}]
    assert sec["models"] == [{"model": "glm-5", "turns": 2}, {"model": "qwen-chat", "turns": 2}]
    assert sec["unknown"] == 2 and sec["since"] == "2026-11-02" and "끝까지 간 턴" in sec["note"]


def test_뺄_계정의_턴은_종류_셈에서도_빠진다(tmp_path):
    box = Box(tmp_path, usage_exclude_accounts="tester@example.com")
    t = int(NOW) - 3600
    box.audit((t, "tester@example.com", "chat_done", "ok", {"kind": "chat"}), (t, "a@example.com", "chat_done", "ok", {"kind": "delib"}))
    assert box.build()["sections"]["chat_kinds"]["rows"] == [{"kind": "delib", "turns": 1}]
