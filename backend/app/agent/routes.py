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
from typing import Literal

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


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)  # per-item cap — no unbounded input (DoS)


class DelibOpts(BaseModel):
    """심의 손잡이 요청 오버라이드(웹 토글) — 각 필드 None=agent-server env 기본값 유지.
    범위를 여기서 강제(agent-server 도 재클램프)해 신뢰 안 되는 값 유입을 막는다. GLM 리뷰 §5."""
    evidence_prepass: int | None = Field(default=None, ge=0, le=1)
    rebut_quote: int | None = Field(default=None, ge=0, le=1)
    prose_first: int | None = Field(default=None, ge=0, le=1)
    cross_exam: int | None = Field(default=None, ge=0, le=1)
    anchor: int | None = Field(default=None, ge=0, le=1)
    chair_bestof: int | None = Field(default=None, ge=1, le=5)
    chair_cite: int | None = Field(default=None, ge=0, le=1)
    timeout_s: float | None = Field(default=None, ge=10, le=1800)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8192)  # cap payload — no unbounded input (DoS)
    system_id: str | None = Field(default=None, max_length=128)  # sub-page → tool scope (Phase 2)
    # 멀티턴 컨텍스트: 오래된 것→최신 순, 이번 message는 포함하지 않는다(agent-server 계약).
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=40)
    # 있으면 이 대화(서버 정본)에 user+assistant 를 저장한다. 없으면 저장 안 함(하위호환).
    conversation_id: str | None = Field(default=None, max_length=64)
    # 심의 손잡이 오버라이드 — 심의(/심의) 요청에서만 의미. agent-server 로 그대로 포워딩.
    delib_opts: DelibOpts | None = None


# ── 서버 대화 저장소 REST ─────────────────────────────────────────────────────
# 웹 챗·Claude(MCP) 심의·GLM 이어가기가 공유하는 정본. 인증은 /chat 과 동일하게
# PAT(Bearer) 또는 세션 쿠키(+CSRF). owner_sub 로 소유권 강제(타인 대화 접근 차단).


class ConvMessageIn(BaseModel):
    role: Literal["user", "assistant", "system", "persona"] = "assistant"
    content: str = Field(max_length=20000)
    persona: str | None = Field(default=None, max_length=120)
    round: int | None = None
    meta: dict | None = None


class ConvCreate(BaseModel):
    title: str = Field(default="새 대화", max_length=200)
    kind: Literal["chat", "deliberation"] = "chat"
    source: Literal["web", "mcp"] = "web"
    # MCP 심의 등 일괄 생성 — 라운드 발언 전체를 한 번에(왕복 최소화). 비면 빈 대화 생성.
    messages: list[ConvMessageIn] = Field(default_factory=list, max_length=200)


def _conv(request: Request):
    return request.app.state.conv_store


@router.get("/conversations")
async def list_conversations(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    return {"conversations": _conv(request).list_for_owner(principal.subject)}


@router.post("/conversations")
async def create_conversation(
    request: Request,
    body: ConvCreate,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    if body.messages:
        cid = _conv(request).create_with_messages(
            owner_sub=principal.subject, title=body.title, kind=body.kind,
            source=body.source,
            messages=[m.model_dump() for m in body.messages],
        )
    else:
        cid = _conv(request).create(
            owner_sub=principal.subject, title=body.title, kind=body.kind, source=body.source
        )
    return {"id": cid}


@router.get("/conversations/{cid}")
async def get_conversation(
    cid: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    conv = _conv(request).get(cid, principal.subject)
    if conv is None:
        raise AuthError("conversation not found", status_code=404)
    return conv


@router.post("/conversations/{cid}/messages")
async def append_conversation_message(
    cid: str,
    request: Request,
    body: ConvMessageIn,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    ok = _conv(request).append(
        conversation_id=cid, owner_sub=principal.subject, role=body.role,
        content=body.content, persona=body.persona, round=body.round, meta=body.meta,
    )
    if not ok:
        raise AuthError("conversation not found", status_code=404)
    return {"ok": True}


@router.delete("/conversations/{cid}")
async def delete_conversation(
    cid: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    if not _conv(request).delete(cid, principal.subject):
        raise AuthError("conversation not found", status_code=404)
    return {"ok": True}


class ConvRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.patch("/conversations/{cid}")
async def rename_conversation(
    cid: str,
    request: Request,
    body: ConvRename,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    if not _conv(request).rename(cid, principal.subject, body.title):
        raise AuthError("conversation not found", status_code=404)
    return {"ok": True}


def _parse_sse_frame(frame: str) -> tuple[str, dict] | None:
    """완결된 SSE 프레임 1개('event: x\\ndata: {...}') → (event, data). 파싱 불가면 None."""
    evt = None
    data_lines: list[str] = []
    for line in frame.split("\n"):
        if line.startswith("event:"):
            evt = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if evt is None or not data_lines:
        return None
    import json
    try:
        return evt, json.loads("\n".join(data_lines))
    except (ValueError, TypeError):
        return None


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
    payload = {
        "message": body.message,
        "system_id": body.system_id,
        "groups": principal.groups,
        "history": [{"role": m.role, "content": m.content} for m in body.history],
    }
    if body.delib_opts is not None:  # 지정된 손잡이만 전달(None 필드는 제외 → env 기본값 유지)
        payload["delib_opts"] = body.delib_opts.model_dump(exclude_none=True)
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

    # conversation_id 가 있으면 이 대화(서버 정본)에 user 를 먼저 저장하고, 스트림을 훑어
    # assistant 최종 텍스트를 모아 종료 시 저장한다(웹에서 GLM 이어가기가 서버에 남게).
    store = _conv(request) if body.conversation_id else None
    owner = principal.subject
    cid = body.conversation_id
    if store is not None and cid:
        # 소유자 대화가 아니면 조용히 저장 스킵(스트림은 정상 — 채팅 자체는 막지 않음).
        if store.append(conversation_id=cid, owner_sub=owner, role="user", content=body.message):
            pass
        else:
            store = None  # 없거나 타인 소유 → 이 요청은 저장 안 함

    async def gen() -> AsyncIterator[bytes]:
        acc: list[str] = []          # token delta 누적(폴백)
        final: str | None = None     # result 프레임의 전체 텍스트(우선)
        decision: str | None = None  # 심의 결정문(result 없을 때 폴백)
        turns: list[dict] = []       # 심의 persona 발언 — MCP 경로와 대칭으로 서버에 남긴다
        buf = ""                     # relay 는 청크가 프레임 경계와 안 맞음 → 완결 프레임만 파싱
        try:
            async for frame in source:
                if store is not None:
                    buf += frame.decode(errors="replace") if isinstance(frame, bytes) else str(frame)
                    while "\n\n" in buf:
                        one, buf = buf.split("\n\n", 1)
                        parsed = _parse_sse_frame(one)
                        if parsed is None:
                            continue
                        evt, data = parsed
                        if evt == "result" and isinstance(data.get("content"), str):
                            final = data["content"]
                        elif evt == "token" and isinstance(data.get("delta"), str):
                            acc.append(data["delta"])
                        elif evt == "delib":
                            k = data.get("kind")
                            if k == "turn" and isinstance(data.get("say"), str):
                                turns.append({"persona": data.get("persona"),
                                              "round": data.get("round"),
                                              "content": data["say"]})
                            elif k == "decision" and isinstance(data.get("text"), str):
                                decision = data["text"]
                yield frame
        finally:
            sem.release()  # released even on client disconnect (Starlette aclose()s the gen)
            if store is not None and cid:
                for t in turns[:60]:  # 심의 발언 수 캡(폭주 방어)
                    store.append(conversation_id=cid, owner_sub=owner, role="persona",
                                 content=str(t["content"])[:20000],
                                 persona=(str(t["persona"])[:120] if t.get("persona") else None),
                                 round=(int(t["round"]) if isinstance(t.get("round"), int) else None))
                reply = final if final is not None else (decision or "".join(acc))
                if reply:
                    store.append(conversation_id=cid, owner_sub=owner, role="assistant", content=reply)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
