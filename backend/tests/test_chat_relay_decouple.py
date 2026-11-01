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


@pytest.mark.parametrize("save_delay", [0.0, 0.3])
@pytest.mark.parametrize("spec", ["2.3", "2.4"])
def test_상류가_끝난_직후_브라우저가_떠나도_답을_남긴다(portal, spec, save_delay):
    """2차 적대 검토(있던 결함 — 사용자 결정 11-01로 고친다, docs/wda-deck WD-D79) — 상류가 끝나 pump 가 finally 에서 상류를 닫고 저장하는 사이에
    브라우저가 떠나면(done 프레임을 받은 직후), 생성기 쪽 취소가 pump 로 번져 저장 스레드 앞(anyio.to_thread.run_sync)에 떨어졌다 — 서버
    사본에 사용자 발화만 남았다. 2.3 은 끊김을 receive 로(http.disconnect), 2.4 는 send 의 실패로 안다."""
    import time as _time

    c, app, _path = portal
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _Turn(n=3))
    store = app.state.conv_store
    orig = store.append

    def slow(**kw):
        if kw.get("role") == "assistant" and save_delay:
            _time.sleep(save_delay)                 # 저장이 잠금을 기다리는 꼴
        return orig(**kw)

    async def run():
        body = json.dumps({"message": "질문", "conversation_id": cid}).encode()
        given, done_sent = [False], asyncio.Event()

        async def receive():
            if not given[0]:
                given[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            await (done_sent.wait() if spec == "2.3" else asyncio.Event().wait())
            return {"type": "http.disconnect"}

        async def send(msg):
            if msg["type"] == "http.response.body" and b"event: done" in (msg.get("body") or b""):
                if spec == "2.4":
                    raise OSError("client gone")    # 2.4 — 마지막 프레임을 보내다 끊김을 안다
                done_sent.set()

        try:
            await asyncio.wait_for(app(_scope(body, spec, app), receive, send), 10)
        except Exception:  # noqa: BLE001 — 끊긴 연결의 ASGI 호출은 예외로 끝날 수 있다
            pass
        await asyncio.sleep(save_delay + 0.5)       # 저장 스레드가 끝날 틈

    store.append = slow
    try:
        c.portal.call(run)
    finally:
        store.append = orig
    assert _messages(app, cid) == [("user", "질문"), ("assistant", _RESULT)], "다 받은 답을 서버 사본에 남긴다"
    assert not relay.turn_active(cid)


@pytest.mark.parametrize("leave", [True, False])
def test_저장이_막혀도_응답은_상한_안에_닫히고_저장은_뒤에서_끝난다(portal, monkeypatch, caplog, leave):
    """3차 적대 검토(docs/wda-deck WD-D81) — WD-D79 뒤로 생성기는 끝맺는 pump(상류 닫기 · 저장)를 끊지 않고 기다린다. 저장이 막히면(잠금을 놓지
    않는 쓰기) 그 기다림에 끝이 없어 ASGI 호출이 저장이 풀릴 때까지 붙잡혔다. 기다림은 상한까지만 — 넘기면 크게 남기고 응답을 닫되, 저장은 끊지
    않고 뒤에서 끝까지 둔다(끝나면 그것도 남긴다). leave — 브라우저가 done 뒤에 떠났다(아니면 연결을 둔 채 끝을 기다린다)."""
    import threading
    import time as _time

    c, app, _path = portal
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _Turn(n=2))
    monkeypatch.setattr(relay, "_RELAY_FINISH_WAIT_S", 0.3, raising=False)
    store = app.state.conv_store
    orig = store.append
    release = threading.Event()

    def stuck(**kw):
        if kw.get("role") == "assistant":
            release.wait(5)                         # 잠금을 놓지 않는 쓰기 뒤에 선 저장
        return orig(**kw)

    seen: dict = {}

    async def run():
        body = json.dumps({"message": "질문", "conversation_id": cid}).encode()
        given, done_sent = [False], asyncio.Event()

        async def receive():
            if not given[0]:
                given[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            await (done_sent.wait() if leave else asyncio.Event().wait())
            return {"type": "http.disconnect"}

        async def send(msg):
            if msg["type"] == "http.response.body" and b"event: done" in (msg.get("body") or b""):
                done_sent.set()

        t0 = _time.monotonic()
        try:
            await asyncio.wait_for(app(_scope(body, "2.3", app), receive, send), 10)
        except Exception as exc:  # noqa: BLE001
            seen["exc"] = repr(exc)
        seen["call_s"] = _time.monotonic() - t0
        seen["saved_early"] = ("assistant", _RESULT) in _messages(app, cid)
        release.set()                               # 쓰기가 풀린다 — 뒤에 둔 저장이 끝난다
        seen["saved_late"] = await _until(lambda: ("assistant", _RESULT) in _messages(app, cid))
        seen["turn_after"] = await _until(lambda: not relay.turn_active(cid))
        seen["late_logged"] = await _until(lambda: any("늦게 끝났다" in r.getMessage() for r in caplog.records))

    store.append = stuck
    try:
        with caplog.at_level(logging.WARNING, logger=relay.logger.name):
            c.portal.call(run)
    finally:
        release.set()
        store.append = orig
    assert seen["call_s"] < 2.0, f"막힌 저장이 응답을 붙잡았다({seen['call_s']:.1f}초) — {seen}"
    assert not seen["saved_early"], "시험 전제 — 저장이 막혀 있었다"
    assert seen["saved_late"] and seen["turn_after"], "저장은 끊지 않고 뒤에서 끝낸다"
    assert sum("상한" in r.getMessage() and "끝맺는" in r.getMessage() for r in caplog.records) == 1, "넘긴 사실을 한 번 크게 남긴다"
    assert seen["late_logged"], "뒤에서 끝난 것도 남긴다"
