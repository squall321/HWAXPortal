# 챗 중계의 퍼밋이 헤더를 보내다 끊겨도 돌아오는지 본다 — 생성기가 한 번도 돌지 않는 끊김(ASGI spec 2.4)
"""`/agent/chat` 은 스트림 전에 `agent_semaphore` 퍼밋을 잡고 생성기의 finally 에서 돌려준다. 헤더를 보내다 앱 쪽이 끊기면
(spec 2.4 — send 가 OSError) 생성기는 한 번도 돌지 않아 그 finally 도 돌지 않는다 — 퍼밋이 영구히 새고 상한(64)만큼 쌓이면
챗·docx 가 전부 429 로 굳는다. 카드 대조 중계(`_CrStream`)가 같은 길을 막은 것을 챗에도 둔다. TestClient 는 응답을 끝까지 모은
뒤 돌려주므로 이 끊김을 만들지 못해 ASGI 를 직접 부른다.
"""
import asyncio
import contextlib
import json

from fastapi.testclient import TestClient

from app.auth.provider import Principal
from app.deps import principal_pat_or_session
from app.main import app

_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U",
                 groups=["eng-team", "feat:deliberation", "plat:aidatahub"])


def _scope(body: bytes, spec: str) -> dict:
    return {"type": "http", "asgi": {"version": "3.0", "spec_version": spec}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/agent/chat", "raw_path": b"/agent/chat",
            "root_path": "", "query_string": b"mode=echo", "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())]}


def _drive(body: bytes, spec: str, *, fail_send: bool) -> bool:
    """ASGI 한 번 — fail_send 면 첫 send(헤더)부터 OSError 다. 끝난 뒤 퍼밋이 잠겨 있는지 돌려준다."""
    async def go() -> bool:
        app.state.agent_semaphore = asyncio.Semaphore(1)
        given = False

        async def receive() -> dict:
            nonlocal given
            if not given:
                given = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.sleep(3600)

        async def send(msg: dict) -> None:
            if fail_send:
                raise OSError("client gone")

        with contextlib.suppress(Exception):   # 끊긴 연결의 ASGI 호출은 예외로 끝난다(ClientDisconnect 등)
            await asyncio.wait_for(app(_scope(body, spec), receive, send), timeout=10)
        return app.state.agent_semaphore.locked()

    return asyncio.run(go())


def test_헤더를_보내다_끊겨도_챗_퍼밋이_돌아온다():
    app.dependency_overrides[principal_pat_or_session] = lambda: _WHO
    try:
        with TestClient(app):
            saved = app.state.agent_semaphore
            try:
                body = json.dumps({"message": "안녕"}).encode()
                assert not _drive(body, "2.4", fail_send=True), "헤더를 보내다 끊긴 챗의 퍼밋이 돌아오지 않았다"
                assert not _drive(body, "2.4", fail_send=False), "끝까지 흐른 챗의 퍼밋도 돌아와야 한다"
            finally:
                app.state.agent_semaphore = saved
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
