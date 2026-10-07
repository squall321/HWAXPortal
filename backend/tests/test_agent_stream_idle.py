# 에이전트 서버 스트림의 침묵 한도(AGENT_STREAM_IDLE_TIMEOUT_S) — 멈춘 서버를 영영 기다리지 않고, 끊을 때 사유와 손잡이를 말하는지
"""포털 릴레이는 에이전트 서버의 SSE 를 `read=None`(무제한)으로 읽었다. 에이전트 서버가 연결을 쥔 채 멈추면 로그 한 줄
없이 영영 기다렸고, 그 요청은 동시 실행 퍼밋(64개) 중 하나를 쥔 채였다. 이 경로에서 진짜로 끝이 없던 유일한 대기다.

침묵 한도는 **바이트 사이 간격**이다 — 엔진이 15초마다 ping 을 내므로 살아 있는 심의는 몇 시간을 돌아도 걸리지 않는다.
그래서 여기서 보는 것은 셋이다.
  · 조용해진 스트림은 그 시간 뒤에 끊기고, '연결 못 함' 과 다른 코드·문구로 나간다(사람이 할 일이 다르다).
  · ping 이 섞인 스트림은 그대로 흘러가고 서버 대화에 남는 내용이 같다(릴레이는 heartbeat 를 만들지도 삼키지도 않는다).
  · 기본값이 침묵 한도 사슬의 맨 안쪽 값이다(포털 46800 < nginx 50400 < 리스크 앱 54000 — 나머지 둘은 다른 파일·리포다).

멈춘 서버는 대역이 아니라 실제 소켓으로 만든다 — httpx 의 read 타임아웃이 스트림 본문에서 실제로 걸리는지가 이 시험의 요점이다.
"""
import asyncio
import json
import time

import httpx

from app.agent.routes import ChatRequest, _relay_stream
from app.auth.provider import Principal
from app.config import Settings

_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:deliberation"])
_HEAD = (b"HTTP/1.1 200 OK\r\ncontent-type: text/event-stream\r\ncache-control: no-cache\r\n"
         b"connection: close\r\n\r\n")


class _Audit:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def record(self, **kw) -> None:
        self.rows.append(kw)


def _frames(raw: bytes) -> list[tuple[str, dict]]:
    out = []
    for blk in raw.decode().split("\n\n"):
        ev = [ln[6:].strip() for ln in blk.split("\n") if ln.startswith("event:")]
        data = [ln[5:].strip() for ln in blk.split("\n") if ln.startswith("data:")]
        if ev and data:
            out.append((ev[0], json.loads(data[0])))
    return out


async def _relay_against(handler, *, idle: float) -> tuple[bytes, _Audit, float]:
    """handler(reader, writer) 로 답하는 진짜 TCP 서버를 띄우고 릴레이를 끝까지 돌린다."""
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    audit = _Audit()
    settings = Settings(_env_file=None, agent_server_url=f"http://127.0.0.1:{port}")
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=idle), trust_env=False) as client:
        got = b"".join([c async for c in _relay_stream(ChatRequest(message="x"), _WHO, audit, settings, client)])
    took = time.monotonic() - t0
    server.close()
    return got, audit, took


def test_조용해진_스트림은_침묵_한도_뒤에_끊기고_사유와_손잡이를_말한다():
    async def stalled(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(_HEAD + 'event: status\ndata: {"step": "1라운드", "tool": null}\n\n'.encode())
        await writer.drain()
        await asyncio.sleep(30)          # 연결은 쥔 채 아무것도 안 보낸다 — 멈춘 에이전트 서버

    got, audit, took = asyncio.run(_relay_against(stalled, idle=0.4))
    assert took < 10, f"침묵 한도 0.4초인데 {took:.1f}초를 기다렸다 — 한도가 걸리지 않는다"
    frames = _frames(got)
    assert frames[0] == ("status", {"step": "1라운드", "tool": None}), "끊기 전에 받은 것은 그대로 넘어간다"
    assert [e for e, _ in frames[1:]] == ["error", "done"], "끊을 때 error 와 done 을 낸다 — done 이 없으면 화면이 잠긴 채 남는다"
    err = frames[1][1]
    assert err["code"] == "agent_stream_idle", "'연결 못 함'(agent_unreachable)과 갈라야 한다 — 이쪽은 심의가 서버에서 아직 돌 수 있다"
    assert "AGENT_STREAM_IDLE_TIMEOUT_S" in err["message"] and "0초" in err["message"], "얼마 동안 조용했는지와 손잡이 이름을 말한다"
    assert "계속 돌 수 있다" in err["message"], "곧바로 다시 시작하면 두 번째 심의가 나란히 돈다 — 그 전에 확인할 곳을 말한다"
    (row,) = [r for r in audit.rows if r.get("status") == "error"]
    assert row["meta"] == {"reason": "agent_stream_idle", "idle_s": 0.4}, "감사에 사유가 남아야 멈춘 서버를 뒤에서 찾는다"
    assert not [r for r in audit.rows if r["event"] == "chat_done"], "끊긴 실행을 정상 종료로 적지 않는다"


def test_신호를_내는_스트림은_한도보다_오래_걸려도_끊기지_않는다():
    """원칙 — 진행 중인 실행을 자르지 않는다. 한도 0.4초, 전체 1.5초, 0.15초마다 ping."""
    async def alive(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(_HEAD)
        for i in range(10):
            writer.write(f'event: ping\ndata: {{"idle_s": {i * 15}, "ts": {i}}}\n\n'.encode())
            await writer.drain()
            await asyncio.sleep(0.15)
        writer.write('event: result\ndata: {"type": "text", "content": "끝"}\n\nevent: done\ndata: {}\n\n'.encode())
        await writer.drain()
        writer.close()

    got, audit, took = asyncio.run(_relay_against(alive, idle=0.4))
    frames = _frames(got)
    assert took > 1.0 and [e for e, _ in frames].count("ping") == 10, "ping 은 삼키지 않고 그대로 넘긴다(바깥 층의 침묵 한도도 이것으로 산다)"
    assert [e for e, _ in frames[-2:]] == ["result", "done"] and "error" not in [e for e, _ in frames]
    assert audit.rows[-1]["event"] == "chat_done"


def test_연결_못_함은_종전_코드_그대로다():
    async def run():
        audit = _Audit()
        settings = Settings(_env_file=None, agent_server_url="http://127.0.0.1:9")   # 닫힌 포트
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, read=0.4), trust_env=False) as client:
            return b"".join([c async for c in _relay_stream(ChatRequest(message="x"), _WHO, audit, settings, client)]), audit

    got, audit = asyncio.run(run())
    frames = _frames(got)
    assert [e for e, _ in frames] == ["error", "done"] and frames[0][1]["code"] == "agent_unreachable"
    assert audit.rows[-1]["meta"]["reason"] == "agent_unreachable"


def test_공유_클라이언트의_read_가_침묵_한도이고_나머지는_짧다():
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import _agent_timeout, app

    t = _agent_timeout(Settings(_env_file=None))
    assert t.read == 46800.0, "기본 13시간 — nginx /agent/(50400)·리스크 앱(54000)보다 작아야 이 층의 문구가 먼저 나간다"
    assert (t.connect, t.write, t.pool) == (30.0, 30.0, 30.0), "죽은 상대 감지는 짧게 둔다"
    assert t.read > 2 * 14400 + 8, "heartbeat 없는 옛 엔진에서도 요청 상한 호출 1회(재시도 포함)를 자르지 않는다"
    assert _agent_timeout(Settings(_env_file=None, agent_stream_idle_timeout_s=0)).read is None, "0 은 끔(무제한)이다"
    assert _agent_timeout(Settings(_env_file=None, agent_stream_idle_timeout_s=600)).read == 600.0
    with TestClient(app):
        assert app.state.agent_client.timeout == _agent_timeout(get_settings()), "기동이 그 한도로 클라이언트를 만든다"


def test_ping_이_섞인_스트림도_서버_대화에_같은_내용을_남긴다():
    """엔진 heartbeat 이벤트 이름은 ping 이다. 포털은 스트림을 훑어 발언·결정문을 서버 대화에 저장하는데, 모르는 이벤트가
    섞여도 저장되는 내용이 달라지면 안 된다(리스크 앱·프론트에도 같은 시험이 하나씩 있다)."""
    from fastapi.testclient import TestClient

    from app.deps import principal_pat_or_session
    from app.main import app

    body = [
        'event: delib\ndata: {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}\n\n',
        'event: status\ndata: {"step": "조회", "tool": "list_materials", "ok": true}\n\n',
        'event: delib\ndata: {"kind": "decision", "text": "결정문"}\n\n',
        'event: done\ndata: {}\n\n',
    ]
    ping = 'event: ping\ndata: {"idle_s": 15, "ts": 1}\n\n'

    class _Body(httpx.AsyncByteStream):
        def __init__(self, text: str) -> None:
            self._raw = text.encode()

        async def __aiter__(self):
            yield self._raw[:37]         # 프레임 경계와 안 맞는 청크 — 릴레이가 실제로 받는 모양
            yield self._raw[37:]

    def serve(text: str):
        return httpx.AsyncClient(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, stream=_Body(text), headers={"content-type": "text/event-stream"})))

    app.dependency_overrides[principal_pat_or_session] = lambda: _WHO
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            saved, relayed = [], []
            try:
                for text in ("".join(body), ping + ping.join(body) + ping):
                    cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]
                    app.state.agent_client = serve(text)
                    r = c.post("/agent/chat", json={"message": "/심의 x", "conversation_id": cid})
                    assert r.status_code == 200
                    relayed.append(r.text)
                    msgs = c.get(f"/agent/conversations/{cid}").json()["messages"]
                    saved.append([(m["role"], m.get("persona"), m.get("round"), m["content"], m.get("meta")) for m in msgs])
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert relayed[1].count("event: ping") == len(body) + 1, "ping 은 브라우저까지 그대로 간다"
    assert [row[0] for row in saved[0]] == ["user", "persona", "assistant"] and saved[0][2][3] == "결정문"
    assert saved[1] == saved[0], "ping 이 섞였다고 저장되는 발언·결정문·활동이 달라졌다"
