"""Agent chat endpoints — thin proxy + auth gate + SSE relay.

The portal does NOT run the LLM / LangGraph / MCP fan-out. It:
  1. authenticates the session (get_current_principal) + CSRF,
  2. caps concurrency (a SSE connection holds a worker → Semaphore, 429 over the cap),
  3. audits the call,
  4. relays the remote Agent Server's SSE stream to the browser.

  POST /agent/chat?mode=echo  — dev: no remote needed; emits the §5 SSE contract locally.
  POST /agent/chat            — relay the remote Agent Server stream (Phase 3 wiring).

mode=echo is the single mock boundary: it proves the SSE path end-to-end (FastAPI →
StreamingResponse → nginx buffering-off → fetch+ReadableStream) with no Agent Server.
"""

import asyncio
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.audit import AuditLog
from app.agent.sse import sse_event
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal, require_csrf

router = APIRouter(prefix="/agent", tags=["agent"])

# text/event-stream + the headers nginx needs to NOT buffer the stream. proxy_buffering off
# is set in the nginx location too; X-Accel-Buffering is the per-response belt-and-suspenders.
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    message: str
    system_id: str | None = None  # current portal sub-page → per-page tool scope (Phase 2)


def _audit(request: Request) -> AuditLog:
    return request.app.state.agent_audit


def _sem(request: Request) -> asyncio.Semaphore:
    return request.app.state.agent_semaphore


async def _echo_stream(message: str, principal: Principal, audit: AuditLog) -> AsyncIterator[bytes]:
    """Local echo: emits the §5 SSE contract (status → token×N → result → done)."""
    chat_id = "echo"
    audit.record(principal=principal.subject, event="chat_start", chat_id=chat_id,
                 meta={"mode": "echo"})
    yield sse_event("status", {"step": "요청 수신", "tool": None})
    await asyncio.sleep(0.2)
    reply = f"echo: {message}"
    for ch in reply:
        yield sse_event("token", {"delta": ch})
        await asyncio.sleep(0.02)
    yield sse_event("result", {"type": "text", "content": reply})
    audit.record(principal=principal.subject, event="chat_done", chat_id=chat_id, status="ok")
    yield sse_event("done", {})


async def _relay_stream(
    body: "ChatRequest", principal: Principal, audit: AuditLog, settings: Settings
) -> AsyncIterator[bytes]:
    """Relay the remote Agent Server's SSE stream byte-for-byte to the browser.

    The portal stays a thin proxy: it forwards the message + the caller's groups (for
    allowed_groups filtering downstream) and pipes back whatever the Agent Server emits,
    which already speaks the §5 contract. Auth/CSRF were enforced before we got here.
    """
    chat_id = "relay"
    audit.record(principal=principal.subject, event="chat_start", chat_id=chat_id,
                 meta={"agent": settings.agent_server_url, "system_id": body.system_id})
    payload = {"message": body.message, "system_id": body.system_id, "groups": principal.groups}
    try:
        async with (
            httpx.AsyncClient(timeout=settings.agent_request_timeout) as client,
            client.stream("POST", f"{settings.agent_server_url}/chat", json=payload) as r,
        ):
            if r.status_code != 200:
                detail = (await r.aread()).decode(errors="replace")[:200]
                audit.record(principal=principal.subject, event="chat_error",
                             chat_id=chat_id, status="error",
                             meta={"upstream": r.status_code})
                yield sse_event("error", {"code": f"agent_{r.status_code}", "message": detail})
                yield sse_event("done", {})
                return
            async for chunk in r.aiter_raw():
                if chunk:
                    yield chunk
    except httpx.HTTPError as exc:
        audit.record(principal=principal.subject, event="chat_error", chat_id=chat_id,
                     status="error", meta={"reason": "agent_unreachable"})
        yield sse_event("error", {"code": "agent_unreachable", "message": str(exc)})
        yield sse_event("done", {})
        return
    audit.record(principal=principal.subject, event="chat_done", chat_id=chat_id, status="ok")


@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    mode: str | None = None,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    sem = _sem(request)
    audit = _audit(request)
    # SSE holds a worker for the stream's lifetime → cap, and reject (not queue) over the cap.
    # Acquire BEFORE returning the response so an over-cap request 429s instead of opening a
    # stream we can't serve. acquire() is non-blocking only when a slot is free here.
    if sem.locked():
        audit.record(principal=principal.subject, event="chat_error", status="rejected",
                     meta={"reason": "max_concurrent_chats"})
        raise AuthError("too many concurrent chats; retry shortly", status_code=429)

    if mode == "echo":
        await sem.acquire()

        async def gen() -> AsyncIterator[bytes]:
            try:
                async for frame in _echo_stream(body.message, principal, audit):
                    yield frame
            finally:
                sem.release()

        return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)

    # Non-echo: relay the remote Agent Server stream (the real LLM call lives there).
    await sem.acquire()

    async def relay() -> AsyncIterator[bytes]:
        try:
            async for frame in _relay_stream(body, principal, audit, settings):
                yield frame
        finally:
            sem.release()

    return StreamingResponse(relay(), media_type="text/event-stream", headers=SSE_HEADERS)
