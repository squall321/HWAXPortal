# 심의 확인 카드의 고치기(WD-06) — 승인 말의 confirm_edit 를 꼴만 보고 바꾼 칸만 에이전트 서버로 옮긴다 · 화면의 종류 목록 · 고칠 칸이 엔진과 같다
"""docs/request-1125 WD-06 의 포털 몫. 에이전트 서버(eb3dd1d)는 확인 카드 사건의 calls[].summary 에 종류 · 라운드 · 좌석 · RA 저장 · 근거 · 앱을 싣고,
승인 말과 함께 온 ChatRequest.confirm_edit {id: 카드 번호, set: {save_report · job · rounds}} 를 그 카드의 심의 호출에만 얹는다. 고정하는 것.
  · 포털 ChatRequest.confirm_edit — 받는 칸은 엔진 _CONFIRM_EDIT_KEYS 셋, 모르는 칸 · 틀린 꼴은 422(바꾼 줄 알았던 칸이 조용히 버려지지 않게) · 바꾼 칸만
    옮기고 아무것도 안 바꿨으면 싣지 않는다 · 에이전트 서버 ChatRequest 에도 같은 칸이 있다.
  · 화면 — 종류 고르기 목록(confirm.ts ENGINE_JOBS)이 엔진 delib_jobs.JOBS 의 키와 같다 · 라운드는 0 · 2~8.
"""
import ast
import asyncio
import json
import re
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.agent.routes import ChatRequest, ConfirmEditSet, _relay_stream
from app.config import Settings
from tests.test_chat_routine_relay import _WHO, _Audit

ROOT = Path(__file__).resolve().parents[2]
_AGENT = ROOT.parent / "HWAXAgentServer"
CONFIRM_TS = ROOT / "frontend/src/components/chat/confirm.ts"


def _agent(name: str) -> str:
    p = _AGENT / name
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    return p.read_text(encoding="utf-8")


def _sent(body: ChatRequest) -> dict:
    seen: dict = {}

    def upstream(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.read()))
        return httpx.Response(200, stream=httpx.ByteStream(b'event: done\ndata: {}\n\n'), headers={"content-type": "text/event-stream"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            return [c async for c in _relay_stream(body, _WHO, _Audit(), Settings(_env_file=None), client, "pat-x")]
    asyncio.run(go())
    return seen


def test_받는_칸은_엔진의_고칠_칸이다():
    tree = ast.parse(_agent("app.py"))
    keys = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(getattr(t, "id", "") == "_CONFIRM_EDIT_KEYS" for t in n.targets))
    assert set(ConfirmEditSet.model_fields) == set(keys)
    chat = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatRequest")
    assert "confirm_edit" in {s.target.id for s in chat.body if isinstance(s, ast.AnnAssign)}, "에이전트 서버 ChatRequest 에도 같은 칸"


def test_바꾼_칸만_옮기고_안_바꿨으면_싣지_않는다():
    got = _sent(ChatRequest(message="실행 — 확인 번호 cf-7f3a9c2e41d0",
                            confirm_edit={"id": "cf-7f3a9c2e41d0", "set": {"job": "option-select", "save_report": False}}))
    assert got["confirm_edit"] == {"id": "cf-7f3a9c2e41d0", "set": {"job": "option-select", "save_report": False}}
    assert _sent(ChatRequest(message="실행", confirm_edit={"id": "cf-1", "set": {}})).get("confirm_edit") is None
    assert "confirm_edit" not in _sent(ChatRequest(message="실행")), "종전 요청 그대로"
    assert _sent(ChatRequest(message="실행", confirm_edit={"id": "cf-1", "set": {"rounds": 0}}))["confirm_edit"]["set"] == {"rounds": 0}, \
        "0 은 '기본으로' 라는 바꿈이다(None 과 다르다)"


@pytest.mark.parametrize("bad", [
    {"id": "cf-1", "set": {"question": "다른 화두"}}, {"id": "cf-1", "set": {"rounds": 9}}, {"id": "cf-1", "set": {"save_report": "true"}},
    {"id": "cf-1", "set": {"job": "Option Select"}}, {"id": "../x", "set": {"rounds": 3}}, {"id": "cf-1", "set": {"rounds": 3}, "extra": 1},
])
def test_모르는_칸과_틀린_꼴은_거절한다(bad):
    with pytest.raises(ValidationError):
        ChatRequest(message="실행", confirm_edit=bad)


def test_화면의_종류_목록은_엔진과_같다():
    tree = ast.parse(_agent("delib_jobs.py"))
    node = next(n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                and getattr(n.target if isinstance(n, ast.AnnAssign) else n.targets[0], "id", "") == "JOBS")
    engine = {k.value: next(v.value for kk, v in zip(d.keys, d.values, strict=True) if getattr(kk, "value", "") == "label")
              for k, d in zip(node.value.keys, node.value.values, strict=True)}
    src = CONFIRM_TS.read_text(encoding="utf-8")
    block = src[src.index("export const ENGINE_JOBS"):src.index("];", src.index("export const ENGINE_JOBS"))]
    screen = dict(re.findall(r"\['([a-z-]+)', '([^']+)'\]", block))
    assert screen == engine
    rounds = re.search(r"export const EDIT_ROUNDS: readonly number\[\] = \[([0-9, ]+)\]", src)
    assert rounds and [int(x) for x in rounds.group(1).split(",")] == [0, *range(2, 9)]
