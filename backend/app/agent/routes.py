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
from pydantic import BaseModel, Field

from app.agent.audit import AuditLog
from app.agent.sse import sse_event
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session

router = APIRouter(prefix="/agent", tags=["agent"])

# text/event-stream + the headers nginx needs to NOT buffer the stream. proxy_buffering off
# is set in the nginx location too; X-Accel-Buffering is the per-response belt-and-suspenders.
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8192)  # cap payload — no unbounded input (DoS)
    system_id: str | None = Field(default=None, max_length=128)  # sub-page → tool scope (Phase 2)


def _audit(request: Request) -> AuditLog:
    return request.app.state.agent_audit


def _sem(request: Request) -> asyncio.Semaphore:
    return request.app.state.agent_semaphore


def _agent_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.agent_client


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
    body: "ChatRequest", principal: Principal, audit: AuditLog,
    settings: Settings, client: httpx.AsyncClient
) -> AsyncIterator[bytes]:
    """Relay the remote Agent Server's SSE stream byte-for-byte to the browser.

    The portal stays a thin proxy: it forwards the message + the caller's groups (for
    allowed_groups filtering downstream) and pipes back whatever the Agent Server emits,
    which already speaks the §5 contract. Auth/CSRF were enforced before we got here.
    Upstream error detail is logged server-side (audit), NOT reflected to the browser.
    """
    chat_id = "relay"
    audit.record(principal=principal.subject, event="chat_start", chat_id=chat_id,
                 meta={"agent": settings.agent_server_url, "system_id": body.system_id})
    payload = {"message": body.message, "system_id": body.system_id, "groups": principal.groups}
    try:
        async with client.stream(
            "POST", f"{settings.agent_server_url}/chat", json=payload
        ) as r:
            if r.status_code != 200:
                detail = (await r.aread()).decode(errors="replace")[:200]  # server-side only
                audit.record(principal=principal.subject, event="chat_error",
                             chat_id=chat_id, status="error",
                             meta={"upstream": r.status_code, "detail": detail})
                yield sse_event("error", {"code": f"agent_{r.status_code}",
                                          "message": "agent server error"})
                yield sse_event("done", {})
                return
            async for chunk in r.aiter_raw():
                if chunk:
                    yield chunk
    except httpx.HTTPError as exc:
        audit.record(principal=principal.subject, event="chat_error", chat_id=chat_id,
                     status="error", meta={"reason": "agent_unreachable", "exc": str(exc)})
        yield sse_event("error", {"code": "agent_unreachable",
                                  "message": "agent server unreachable"})
        yield sse_event("done", {})
        return
    audit.record(principal=principal.subject, event="chat_done", chat_id=chat_id, status="ok")


@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    mode: str | None = None,
    principal: Principal = Depends(principal_pat_or_session),  # Bearer PAT 또는 세션 쿠키(+CSRF)
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    sem = _sem(request)
    audit = _audit(request)
    # SSE holds a worker for the stream's lifetime → cap, and reject (not queue) over the cap.
    # This IS atomic despite looking like check-then-act: asyncio is single-threaded and there
    # is NO await between sem.locked() and sem.acquire() (acquire returns synchronously when a
    # slot is free), so no other task can steal the slot in between. Acquire BEFORE returning
    # so an over-cap request 429s up front instead of opening a stream we can't serve.
    if sem.locked():
        audit.record(principal=principal.subject, event="chat_error", status="rejected",
                     meta={"reason": "max_concurrent_chats"})
        raise AuthError("too many concurrent chats; retry shortly", status_code=429)
    await sem.acquire()

    # Pick the stream source. echo = local mock (no remote); else relay the Agent Server.
    if mode == "echo":
        source = _echo_stream(body.message, principal, audit)
    else:
        source = _relay_stream(body, principal, audit, settings, _agent_client(request))

    async def gen() -> AsyncIterator[bytes]:
        try:
            async for frame in source:
                yield frame
        finally:
            sem.release()  # released even on client disconnect (Starlette aclose()s the gen)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
