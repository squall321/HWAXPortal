# 챗 중계의 침묵 한도를 심의와 뗀다 — 챗은 AGENT_CHAT_IDLE_TIMEOUT_S(900초), 심의는 AGENT_STREAM_IDLE_TIMEOUT_S(docs/request-1029 P-1 ④ · 결정 D-5)
"""10-29 cae00 QA — 화면이 25분 멈췄는데 포털 중계의 침묵 한도는 46,800초(13시간)였다. 그 값은 heartbeat 없는 옛 심의 엔진과 리스크 패널
벽시계 때문에 컸다. 챗은 에이전트 서버가 15초마다 ping 을 내므로(HWAXAgentServer 670778f) 짧게 둔다. 심의 판정은 에이전트 서버의 트리거와 같아야
한다 — 어긋나면 심의가 900초에 끊기거나 챗이 13시간을 기다린다. 형제 리포의 실제 값과 대조한다."""
import ast
import asyncio
from pathlib import Path

import pytest

from app.agent.routes import _DELIB_TRIGGERS, _is_delib_message
from app.config import Settings
from tests.test_agent_stream_idle import _HEAD, _frames, _relay_against

_ENGINE = Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "deliberation.py"


def test_심의_트리거는_에이전트_서버와_같다():
    if not _ENGINE.exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE}")
    tree = ast.parse(_ENGINE.read_text(encoding="utf-8"))
    names = {"DELIBERATE_TRIGGERS", "SIM_DELIBERATE_TRIGGERS", "TEST_PLAN_TRIGGERS"}
    found = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
             if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) in names}
    assert set(found) == names, found
    assert set(_DELIB_TRIGGERS) == {t for v in found.values() for t in v}


@pytest.mark.parametrize("msg, delib", [("/심의 낙하", True), ("  /시뮬심의 x", True), ("/시험계획 물성", True), ("/DOE a", True),
                                        ("심의 해줘", False), ("/보고서", False), ("/띵킹 x", False), ("", False), (None, False)])
def test_심의_판정(msg, delib):
    assert _is_delib_message(msg) is delib


def test_기본값은_챗이_심의보다_짧고_심의_값은_그대로다():
    s = Settings(_env_file=None)
    assert s.agent_chat_idle_timeout_s == 900.0 and s.agent_stream_idle_timeout_s == 46800.0


def test_조용해진_챗은_챗_한도에_끊기고_챗_손잡이를_말한다():
    async def stalled(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(_HEAD + 'event: status\ndata: {"step": "조회", "tool": null}\n\n'.encode())
        await writer.drain()
        await asyncio.sleep(30)

    got, audit, took = asyncio.run(_relay_against(stalled, idle=30.0, message="안녕", chat_idle=0.4))
    assert took < 10, f"챗 한도 0.4초인데 {took:.1f}초를 기다렸다 — 공유 클라이언트의 심의 한도(30초)를 썼다"
    err = [d for e, d in _frames(got) if e == "error"][0]
    assert err["code"] == "agent_stream_idle" and "AGENT_CHAT_IDLE_TIMEOUT_S" in err["message"], err
    assert "계속 돌 수 있다" not in err["message"], "챗은 끊으면 서버에서도 멈춘다 — 심의 안내를 하지 않는다"
    assert [r for r in audit.rows if r.get("status") == "error"][0]["meta"] == {"reason": "agent_stream_idle", "idle_s": 0.4}


def test_심의는_챗_한도에_걸리지_않는다():
    async def slow(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(_HEAD)
        await writer.drain()
        await asyncio.sleep(0.8)                       # 챗 한도(0.3초)보다 길고 심의 한도(5초)보다 짧은 침묵
        writer.write('event: result\ndata: {"type": "text", "content": "결정문"}\n\nevent: done\ndata: {}\n\n'.encode())
        await writer.drain()
        writer.close()

    got, _audit, _took = asyncio.run(_relay_against(slow, idle=5.0, message="/심의 낙하", chat_idle=0.3))
    assert [e for e, _ in _frames(got)] == ["result", "done"]
