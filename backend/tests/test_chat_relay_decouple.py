# 챗 중계가 상류 읽기를 브라우저 쓰기와 떼는지 — 숨은 탭에도 상류를 끝까지 읽어 저장 · 퍼밋 반납, 끊기면 상류도 끊는다(docs/request-1029 P-1 ①)
"""10-29 cae00 QA — 조종하던 탭이 숨겨진 동안(visibilityState hidden) 화면이 '생각 중' 에서 25분 멈췄고(OT-07), 탭을 깨우자 답이 나왔다(OT-13).
숨은 탭은 연결을 끊은 것이 아니라 읽기를 멈춘 것이다 — 중계 생성기가 yield 에 서면 상류(에이전트 서버)도 읽히지 않아 에이전트 응답 ·
서버 사본 저장 · 퍼밋이 함께 묶였다. 브라우저의 읽기 멈춤은 ASGI send 가 돌아오지 않는 것으로 흉내 낸다(uvicorn 이 쓰기 버퍼가 차면
그렇게 기다린다). uvicorn 의 HTTP spec 은 2.3 이다 — 2.4 갈래도 같이 본다.
"""
import asyncio
import json
import logging

import httpx
import pytest

from app.agent import routes as relay
from tests.test_conv_store_busy_timeout import _agent, portal  # noqa: F401 — 같은 포털 · 가짜 에이전트 서버를 쓴다

_RESULT = "최종 답 — 끝까지 읽혔다"


def _sse(evt: str, data: dict) -> bytes:
    return f"event: {evt}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


class _Turn(httpx.AsyncByteStream):
    """조각 n 개와 결과로 끝나는 챗 한 턴. 몇 조각을 내줬는지(pulled) · 끝까지 읽혔는지(finished) · 닫혔는지(closed)를 남긴다.
    hang 이 있으면 첫 조각 뒤에 그만큼 조용하다(끝나지 않은 턴)."""

    def __init__(self, n: int = 5, *, hang: float = 0.0, pad: int = 0) -> None:
        self.n, self.hang, self.pad = n, hang, pad
        self.pulled, self.finished, self.closed = 0, False, False

    async def __aiter__(self):
        try:
            for i in range(self.n):
                self.pulled += 1
                yield _sse("token", {"delta": f"조각{i} " + "x" * self.pad})
                if self.hang and i == 0:
                    await asyncio.sleep(self.hang)
            self.pulled += 1
            yield _sse("result", {"type": "text", "content": _RESULT}) + _sse("done", {})
            self.finished = True
        finally:
            self.closed = True


def _scope(body: bytes, spec: str, app) -> dict:
    return {"type": "http", "asgi": {"version": "3.0", "spec_version": spec}, "http_version": "1.1", "method": "POST",
            "scheme": "http", "path": "/agent/chat", "raw_path": b"/agent/chat", "query_string": b"", "root_path": "",
            "client": ("127.0.0.1", 1), "server": ("testserver", 80), "app": app, "state": {},
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())]}


def _messages(app, cid: str) -> list[tuple[str, str]]:
    return [(m["role"], m["content"]) for m in app.state.conv_store.get(cid, "u1")["messages"]]


async def _until(cond, timeout: float = 5.0) -> bool:
    for _ in range(int(timeout / 0.02)):
        if cond():
            return True
        await asyncio.sleep(0.02)
    return cond()


@pytest.mark.parametrize("spec", ["2.3", "2.4"])
def test_숨은_탭이_읽지_않아도_상류를_끝까지_읽어_저장하고_퍼밋을_돌려준다(portal, spec):
    c, app, _path = portal
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    turn = _Turn()
    _agent(app, turn)
    seen: dict = {}

    async def run():
        saved_sem = app.state.agent_semaphore
        app.state.agent_semaphore = asyncio.Semaphore(1)
        wake, got = asyncio.Event(), []
        body = json.dumps({"message": "질문", "conversation_id": cid}).encode()
        given = [False]

        async def receive():
            if not given[0]:
                given[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()                # 끊지 않는다 — 탭은 열려 있다

        async def send(msg):
            if msg["type"] == "http.response.body" and msg.get("body"):
                got.append(msg["body"])
                if len(got) == 1:
                    await wake.wait()                   # 첫 조각 뒤로 브라우저가 읽지 않는다(숨은 탭)

        call = asyncio.create_task(app(_scope(body, spec, app), receive, send))
        try:
            seen["finished"] = await _until(lambda: turn.finished)
            seen["saved"] = await _until(lambda: ("assistant", _RESULT) in _messages(app, cid))
            seen["permit_back"] = not app.state.agent_semaphore.locked()
            seen["blocked"] = not call.done() and len(got) == 1
            wake.set()                                  # 탭을 깨운다
            await asyncio.wait_for(call, 10)
            seen["body"] = b"".join(got).decode()
        finally:
            app.state.agent_semaphore = saved_sem

    c.portal.call(run)
    assert seen["blocked"], "시험 전제 — 브라우저가 읽지 않는 동안이었다"
    assert seen["finished"], "브라우저가 읽지 않는 동안 상류(에이전트 서버) 스트림을 끝까지 읽지 않았다"
    assert seen["saved"], "브라우저가 읽지 않는 동안 서버 대화에 답이 저장되지 않았다"
    assert seen["permit_back"], "상류가 끝났는데 숨은 탭이 퍼밋을 쥐고 있다"
    assert all(f"조각{i}" in seen["body"] for i in range(5)) and _RESULT in seen["body"], "깨운 뒤 남은 프레임이 다 가지 않았다"
    assert _messages(app, cid) == [("user", "질문"), ("assistant", _RESULT)]


def test_브라우저가_떠나면_상류도_끊고_받은_것까지_저장한다(portal):
    """끊김은 읽기 멈춤과 다르다 — 사용자가 중지하거나 탭을 닫으면 종전처럼 상류도 끊는다(C-5). 끝까지 돌게 하면 '중지' 의 뜻이 바뀐다."""
    c, app, _path = portal
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    turn = _Turn(hang=30)
    _agent(app, turn)
    seen: dict = {}

    async def run():
        saved_sem = app.state.agent_semaphore
        app.state.agent_semaphore = asyncio.Semaphore(1)
        gone, first = asyncio.Event(), [True]
        body = json.dumps({"message": "질문", "conversation_id": cid}).encode()

        async def receive():
            if first[0]:
                first[0] = False
                return {"type": "http.request", "body": body, "more_body": False}
            await gone.wait()
            return {"type": "http.disconnect"}

        async def send(msg):
            if msg["type"] == "http.response.body" and msg.get("body"):
                gone.set()                              # 첫 조각을 받은 직후 떠난다(중지 · 탭 닫기)

        try:
            loop = asyncio.get_running_loop()
            t0 = loop.time()
            await asyncio.wait_for(app(_scope(body, "2.3", app), receive, send), 10)
            seen["took"] = loop.time() - t0
            seen["closed"], seen["finished"] = turn.closed, turn.finished
            seen["permit_back"] = not app.state.agent_semaphore.locked()
        finally:
            app.state.agent_semaphore = saved_sem

    c.portal.call(run)
    assert seen["took"] < 5 and seen["closed"] and not seen["finished"], seen
    assert seen["permit_back"]
    assert _messages(app, cid) == [("user", "질문"), ("assistant", "조각0 ")], "끊기기 전에 받은 것은 저장한다(종전과 같다)"


def test_읽지_않는_클라이언트가_상한을_넘기면_그때만_상류_읽기를_멈춘다(portal, monkeypatch, caplog):
    c, app, _path = portal
    turn = _Turn(n=10, pad=100)
    _agent(app, turn)
    monkeypatch.setattr(relay, "_RELAY_BUFFER_BYTES", 400)          # 한 조각 약 150바이트 — 두세 조각이면 찬다
    seen: dict = {}

    async def run():
        wake, got = asyncio.Event(), []
        body = json.dumps({"message": "질문"}).encode()
        given = [False]

        async def receive():
            if not given[0]:
                given[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()

        async def send(msg):
            if msg["type"] == "http.response.body" and msg.get("body"):
                got.append(msg["body"])
                if len(got) == 1:
                    await wake.wait()

        call = asyncio.create_task(app(_scope(body, "2.3", app), receive, send))
        await _until(lambda: turn.pulled >= 4, 2.0)
        await asyncio.sleep(0.3)                        # 상한이 없다면 이 사이에 열한 조각을 다 읽는다
        seen["held"] = turn.pulled
        wake.set()
        await asyncio.wait_for(call, 10)
        seen["body"] = b"".join(got).decode()
        seen["finished"] = turn.finished

    with caplog.at_level(logging.WARNING, logger=relay.logger.name):
        c.portal.call(run)
    assert seen["held"] <= 5, f"상한(400바이트)을 넘겨서도 상류를 계속 읽었다 — {seen['held']}조각"
    assert seen["finished"] and _RESULT in seen["body"] and all(f"조각{i}" in seen["body"] for i in range(10))
    assert sum("상한" in r.getMessage() and "챗 중계" in r.getMessage() for r in caplog.records) == 1, "닿은 사실을 한 번 남긴다"


def test_보내다_끊기면_생성기를_닫아_상류를_곧바로_끊는다(portal):
    """spec 2.4 — send 가 끊김으로 실패하면 Starlette 는 생성기를 yield 에 세워 둔 채 나간다. 예외의 traceback 이 생성기를 붙들고
    있는 동안은 GC 도 닫지 않는다 — 응답 쪽(_ReleasingStream)이 닫아야 상류가 곧바로 끊긴다."""
    c, app, _path = portal
    turn = _Turn(hang=30)
    _agent(app, turn)
    seen: dict = {}

    async def run():
        body = json.dumps({"message": "질문"}).encode()
        given, sent = [False], []

        async def receive():
            if not given[0]:
                given[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()

        async def send(msg):
            if msg["type"] == "http.response.body" and msg.get("body"):
                sent.append(msg["body"])
                raise OSError("client gone")

        kept = None
        try:
            await asyncio.wait_for(app(_scope(body, "2.4", app), receive, send), 10)
        except Exception as exc:  # noqa: BLE001 — 끊긴 연결의 ASGI 호출은 예외(ClientDisconnect)로 끝난다
            kept = exc                                  # traceback 을 쥔다 — 로그가 예외를 붙든 꼴
        seen["closed"], seen["kept"], seen["sent"] = turn.closed, kept is not None, len(sent)

    c.portal.call(run)
    assert seen["kept"] and seen["sent"] == 1, seen
    assert seen["closed"], "끊긴 응답의 생성기가 닫히지 않아 상류 연결이 남았다"
