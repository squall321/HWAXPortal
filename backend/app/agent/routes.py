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
from fastapi import APIRouter, Depends, Request, Response
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
    content: str = Field(max_length=24000)  # per-item cap — no unbounded input (DoS)


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
    rounds: int | None = Field(default=None, ge=2, le=8)
    timeout_s: float | None = Field(default=None, ge=10, le=1800)
    # 이어하기(사람 개입 스티어링) — 사람 의견 + 이전 심의 요약 + 전문가 재사용(발굴 생략)
    human_note: str | None = Field(default=None, max_length=2000)
    continue_summary: str | None = Field(default=None, max_length=8000)
    personas: list[dict] | None = Field(default=None, max_length=12)
    # 사용자 지정 도구 — 심의에서 실제 호출돼 정량 근거로 주입(선정 패널에서 선택).
    tools: list[str] | None = Field(default=None, max_length=6)
    # 사용자 지정 앱 — 전문가 자유 조회 범위를 이 앱들로 좁힌다. 도구와 달리 전량 호출이 아니다
    # (도구 하나당 LLM 인자 구성이 붙어, 앱을 20~30개로 펼쳐 호출하면 예산이 터진다).
    apps: list[str] | None = Field(default=None, max_length=3)
    # 웹 리서치 소스 토글(심의) — 켜지 않은 소스는 자유 조회에 바인딩되지 않는다.
    search_sources: list[str] | None = Field(default=None, max_length=4)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=65536)  # cap payload — no unbounded input (DoS)
    system_id: str | None = Field(default=None, max_length=128)  # sub-page → tool scope (Phase 2)
    # 멀티턴 컨텍스트: 오래된 것→최신 순, 이번 message는 포함하지 않는다(agent-server 계약).
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=80)
    # 있으면 이 대화(서버 정본)에 user+assistant 를 저장한다. 없으면 저장 안 함(하위호환).
    conversation_id: str | None = Field(default=None, max_length=64)
    # 심의 손잡이 오버라이드 — 심의(/심의) 요청에서만 의미. agent-server 로 그대로 포워딩.
    delib_opts: DelibOpts | None = None
    # 사용자 지정 우선 도구(챗) — 도구 카탈로그에서 직접 선택한 도구를 우선 사용하게 강제.
    pinned_tools: list[str] | None = Field(default=None, max_length=12)
    # 사용자 지정 우선 앱(챗) — 앱 하나가 도구 20~30개라 12개 캡을 씌우면 조용히 잘린다.
    # 캡은 앱 수(3개)로 걸고, 도구 펼침은 agent-server 가 한다.
    pinned_apps: list[str] | None = Field(default=None, max_length=3)
    # 사용자 지정 전문가(챗) — 이 전문가 페르소나로 대화('전문가와 대화' 모드).
    pinned_agent: str | None = Field(default=None, max_length=120)
    # 웹 리서치 소스 토글(챗) — None 이면 종전 동작, 리스트면 그 소스만 바인딩한다.
    # 빈 리스트는 '전부 끔'이다. 전역 SEARCH_MODE 가 끄면 이 값과 무관하게 나가지 않는다.
    search_sources: list[str] | None = Field(default=None, max_length=4)


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


@router.get("/search-capability")
async def search_capability(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    """웹 리서치 소스 가용성 — 프론트가 토글을 정직하게 그리기 위한 값.

    전역이 꺼져 있는데 UI 에서 켤 수 있으면 사용자는 켰다고 믿고 기다린다. 아무것도
    나가지 않는데 '검색이 잘 안 되는 도구'로만 보이는 것이 이 기능의 현실적 실패 모드다."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(f"{settings.agent_server_url}/search-capability")
            r.raise_for_status()
            return r.json()
    except Exception:  # noqa: BLE001 — agent-server 불통은 '알 수 없음'이지 '가능'이 아니다
        return {"sources": {}, "note": "agent-server 에 연결하지 못해 가용성을 확인할 수 없습니다."}


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
    if body.pinned_tools:  # 사용자 지정 우선 도구 — 켠 것만 전달
        payload["pinned_tools"] = body.pinned_tools
    if body.pinned_apps:  # 사용자 지정 우선 앱 — agent-server 가 도구로 펼친다
        payload["pinned_apps"] = body.pinned_apps
    if body.pinned_agent:  # 사용자 지정 전문가 페르소나
        payload["pinned_agent"] = body.pinned_agent
    if body.search_sources is not None:  # 빈 리스트도 의미가 있다(전부 끔) — None 과 구분
        payload["search_sources"] = body.search_sources
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


@router.get("/artifacts/{name}")
async def get_artifact(
    name: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """도구 산출 이미지 프록시 — 챗 마크다운 ![](/agent/artifacts/…) 이 로드한다.
    GET+세션쿠키(CSRF 불요), 파일명은 agent-server 가 재검증."""
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name):
        return Response(status_code=404)
    client = _agent_client(request)
    try:
        r = await client.get(f"{settings.agent_server_url}/artifacts/{name}")
        if r.status_code != 200:
            return Response(status_code=404)
        return Response(content=r.content,
                        media_type=r.headers.get("content-type", "application/octet-stream"),
                        headers={"Cache-Control": "private, max-age=86400"})
    except httpx.HTTPError:
        return Response(status_code=502)


class CatalogAgentRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)


@router.post("/catalog/agent")
async def catalog_agent(
    request: Request,
    body: CatalogAgentRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """전문가 상세+보유 지식 — 브라우즈 UI 용 프록시(비스트리밍 JSON)."""
    client = _agent_client(request)
    try:
        r = await client.post(f"{settings.agent_server_url}/catalog/agent",
                              json={"key": body.key, "groups": principal.groups})
        return r.json() if r.status_code == 200 else {"error": f"agent_{r.status_code}"}
    except httpx.HTTPError:
        return {"error": "agent_unreachable"}


class ExpertsRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8192)


@router.post("/deliberate/experts")
async def deliberate_experts(
    request: Request,
    body: ExpertsRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """심의 전 전문가 선정 미리보기 — agent-server 로 포워딩(caller groups 주입). 비스트리밍 JSON."""
    client = _agent_client(request)
    payload = {"message": body.message, "groups": principal.groups}
    try:
        r = await client.post(f"{settings.agent_server_url}/deliberate/experts", json=payload)
        if r.status_code != 200:
            return {"recommended": [], "pool": [], "error": f"agent_{r.status_code}"}
        return r.json()
    except httpx.HTTPError:
        return {"recommended": [], "pool": [], "error": "agent_unreachable"}


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
