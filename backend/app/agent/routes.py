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
import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote

import httpx
import jwt
from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.agent import conv_search
from app.agent.audit import AuditLog
from app.agent.sse import sse_event
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.agent import upload as _upload
from app.deps import principal_pat_or_session

logger = logging.getLogger(__name__)

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
    # 챗 워크스페이스가 정리해 넘긴 원천 근거(도구결과+출처). 심의는 '검증 대상·결론 아님'으로
    # 좌석에 주입한다(요약 아닌 날것) — 핸드오프 P1. agent-server 가 항목 필드를 재클램프한다.
    evidence: list[dict] | None = Field(default=None, max_length=12)
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


def _chat_user_pat(keystore, settings: Settings, principal: Principal) -> str | None:
    """이 챗 한 번을 위한 단명 PAT. agent-server 가 이걸로 게이트웨이에 붙는다.

    왜 필요한가 — agent-server 는 지금까지 서비스 계정(GW_TOKEN)으로 게이트웨이에 붙고
    사용자는 X-HWAX-User 헤더로만 알렸다. 그러면 게이트웨이가 "호출자 신원"을 요구하는
    도구(대화 검색·저장처럼 포털에 되물어야 하는 것들)에서 포털이 401 을 준다. 실측으로
    search_conversations 가 웹 챗에서만 CONV_UNAVAILABLE 이었다.

    새 공유비밀을 만들지 않고 이미 있는 PAT 체계를 쓴다. 게이트웨이는 이 토큰을 포털
    JWKS 로 검증하므로 위조가 불가능하고, 도구 인가도 서비스 계정이 아니라 이 사람의
    groups 로 이뤄진다 — 감사 기록도 사람 단위로 남는다.

    ⚠ 30분 창(window)에 맞춰 결정적으로 발급한다 — 같은 사용자·같은 창이면 토큰이 완전히
    같다. 매번 새로 찍으면 agent-server 의 에이전트 캐시가 첫 요청의 토큰을 물고 계속
    재사용해서, 이후에 보낸 새 토큰은 무시되고 60분 뒤 그 하나가 만료되며 도구가 조용히
    죽는다. 창을 맞춰 두면 캐시는 그대로 맞고 자격증명은 30분마다 갱신된다(남은 유효기간
    항상 30분 이상).
    """
    try:
        now = datetime.now(tz=UTC)
        win = int(now.timestamp()) // 1800 * 1800     # 30분 창의 시작
        issued = datetime.fromtimestamp(win, tz=UTC)
        claims = {
            "iss": settings.jwt_issuer,
            "sub": principal.subject,
            "email": principal.email,
            "name": principal.display_name,
            "groups": principal.groups,
            "aud": [settings.pat_chat_audience],
            "scope": "api",
            "scopes": ["chat"],
            "pat_name": "chat-session",
            "iat": issued, "nbf": issued, "exp": issued + timedelta(minutes=60),
            # jti 도 결정적이어야 토큰이 바이트 단위로 같아진다. 서명된 토큰이라 예측
            # 가능성 자체는 위험이 아니고, 폐기 목록에 이 값을 넣으면 그 창이 막힌다.
            "jti": f"chat-{principal.subject}-{win}",
        }
        return jwt.encode(claims, keystore.private_pem, algorithm="RS256",
                          headers={"kid": keystore.active_kid})
    except Exception:  # noqa: BLE001 — 발급 실패로 챗 자체를 막지 않는다
        logger.warning("챗용 사용자 PAT 발급 실패 — agent-server 가 GW_TOKEN 으로 돈다",
                       exc_info=True)
        return None


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


class ConvSearch(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=8, ge=1, le=30)


@router.post("/conversations/search")
async def search_conversations(
    request: Request,
    body: ConvSearch,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    """내 지난 대화를 의미로 찾는다. 남의 대화는 store 가 owner_sub 로 막는다.

    색인은 검색할 때 게으르게 채운다. 별도 워커를 두면 "언제 반영되는지"가 불투명해지고,
    방금 한 대화를 못 찾는 이유를 사용자가 알 방법이 없다. 지금 규모(수백 메시지)에서
    증분 색인은 한 번뿐이고, 그 다음부터는 새 메시지 몇 개만 채운다.
    """
    settings = get_settings()
    store = _conv(request)
    try:
        idx = await conv_search.reindex(store, principal.subject, settings.embed_base_url)
        hits = await conv_search.search(store, principal.subject, body.query,
                                        settings.embed_base_url, body.limit)
    except (httpx.HTTPError, ValueError) as e:
        # 임베더 불통을 빈 결과로 바꾸지 않는다 — "찾아봤는데 없다"로 읽히면 없는 사실을 믿는다.
        raise AuthError(f"의미검색을 할 수 없습니다(임베더 응답 실패): {e}", status_code=503) from e
    # 아직 남은 색인 분량을 반드시 실어 보낸다 — 게으른 색인은 한 번에 상한까지만 처리하므로,
    # 큰 대화 이력에서는 첫 검색이 '부분 색인 위의 결과' 다. 그 사실을 숨기면 못 찾은 것이
    # 없는 것으로 읽힌다.
    left = store.remaining(principal.subject, conv_search.MODEL)
    # 짧은 질의는 점수로 관련성을 가릴 수 없다(온토픽·오프토픽 분포가 겹친다). 결과를
    # 주되 그 사실을 함께 낸다 — 못 가르는 것을 가른 척하면 사용자가 무관한 결과를
    # 관련 있는 것으로 읽는다.
    warn = ("질의가 짧아 관련성 판정이 약합니다 — 무관한 결과가 섞일 수 있습니다. "
            "문장으로 풀어 쓰면 정확해집니다.") if conv_search.short_query(body.query) else ""
    return {"query": body.query, "results": hits,
            "low_confidence": bool(warn), "note": warn,
            "index": {**store.index_stats(principal.subject, conv_search.MODEL),
                      "just_indexed": idx["indexed"], "too_short": idx["too_short"],
                      "not_indexed_yet": left,
                      "partial": bool(left)}}


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
    settings: Settings, client: httpx.AsyncClient, user_pat: str | None = None
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
        # 호출자 신원 — 게이트웨이가 사용자별 데이터를 쓰는 백엔드(DynaForge 등)를 이 사람의
        # 자격증명으로 부른다. 브라우저가 보낸 값이 아니라 검증된 세션/PAT 주체에서 채운다.
        "user_email": principal.email,
        # agent-server 가 게이트웨이에 '이 사람으로' 붙기 위한 단명 자격증명.
        # ⚠ None 을 그대로 보내면 안 된다. agent-server 의 ChatRequest.user_pat 은 str 이라
        # pydantic 이 null 을 422 로 거절하고, 그러면 '발급 실패해도 챗은 계속' 이라는 이쪽
        # 폴백이 정반대로 챗 전체를 죽인다(실측: null→422, ""→200). 빈 문자열이 '없음' 이다.
        "user_pat": user_pat or "",
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


class DocxTurn(BaseModel):
    """심의 좌석 발언 한 건. delib.turns 가 렌더 대상이 된 이상 여기에도 캡이 필요하다 —
    extra=allow 로 열어 두면 캡을 건 text 옆에서 delib 이 무제한으로 들어온다."""
    model_config = {"extra": "ignore"}
    round: int | None = None
    persona: str = Field(default="", max_length=120)
    say: str = Field(default="", max_length=100_000)
    position: str = Field(default="", max_length=2_000)
    stance: str = Field(default="", max_length=120)
    nonNegotiable: str = Field(default="", max_length=2_000)  # noqa: N815 — 프론트 필드명


class DocxDelib(BaseModel):
    model_config = {"extra": "ignore"}
    turns: list[DocxTurn] = Field(default_factory=list, max_length=400)


class DocxMessage(BaseModel):
    """내보내기 입력의 메시지 한 건.

    ⚠ extra 를 닫는다. allow 로 두면 캡을 건 필드 옆으로 임의 크기 JSON 이 무제한 통과해
    캡이 메모리 상한 구실을 못 한다. docx_export 가 실제로 읽는 필드를 전수 확인했고
    (delib·role·text·ts, turn 은 round/persona/say/position/stance/nonNegotiable),
    전부 여기 선언돼 있으므로 닫아도 잃는 것이 없다.
    """
    model_config = {"extra": "ignore"}
    role: str = Field(default="assistant", max_length=40)
    text: str = Field(default="", max_length=200_000)
    # 표시용 시각. int/float/str/None 만 받는다 — Any 로 열어 두면 extra 를 닫은 의미가
    # 없다(임의 크기 dict·list 가 그대로 들어온다). 값의 타당성은 _ts 가 다시 본다.
    ts: int | float | str | None = None
    delib: DocxDelib | None = None


class ConvPayload(BaseModel):
    model_config = {"extra": "ignore"}
    title: str = Field(default="", max_length=300)
    messages: list[DocxMessage] = Field(default_factory=list, max_length=2000)

    @field_validator("messages")
    @classmethod
    def _total_budget(cls, v: list[DocxMessage]) -> list[DocxMessage]:
        """총량 상한. 항목별 캡만 있으면 2000개 × 20만자 = 4억자가 통과한다 —
        통째로 메모리에 올려 렌더하므로 그것 자체가 부하다."""
        # ⚠ 렌더되는 문자열 필드를 **전부** 센다. 앞선 커밋은 같은 자리에서 text 와 say 만
        # 세어, position·nonNegotiable·persona·stance 로 채운 페이로드가 '0자' 로 통과했다 —
        # 그 커밋이 바로 위 docstring 에 그 필드 목록을 적어 놓고도 합산식에 안 쓴 것이다.
        # 필드를 늘리면 여기도 같이 늘려야 한다. 그래서 목록을 한 곳에 둔다.
        def _turn_chars(t: "DocxTurn") -> int:
            return sum(len(getattr(t, f) or "")
                       for f in ("say", "position", "stance", "persona", "nonNegotiable"))

        total = sum(len(m.text) + sum(_turn_chars(t) for t in (m.delib.turns if m.delib else []))
                    for m in v)
        if total > 4_000_000:
            # 거부 메시지에 입력을 되싣지 않는다 — pydantic 이 detail.input 으로 페이로드
            # 전체를 되돌려주면 거부가 렌더보다 비싸진다. 숫자만 말한다.
            raise ValueError(f"본문 총량이 상한(400만자)을 넘는다: {total}자")
        return v


class DocxRequest(BaseModel):
    """대화 이력 → Word. mode='transcript' 는 있는 그대로, 'report' 는 LLM 이 정리한다."""
    # 상한을 건다. 같은 파일의 다른 모델은 전부 캡이 있는데 여기만 맨 dict 였다 —
    # 통째로 메모리에 올린 뒤 python-docx 로 렌더하므로 큰 입력이 그대로 부하가 된다.
    conversation: ConvPayload = Field(default_factory=lambda: ConvPayload())
    mode: Literal["transcript", "report"] = "transcript"


# 정리본 지시 — 대화를 요약하는 게 아니라 **문서로 재구성**하라는 것이 요점이다.
# 요약만 시키면 "이런 얘기를 했다" 가 나오고, 그건 읽는 사람이 판단에 쓸 수 없다.
_REPORT_PROMPT = """다음은 엔지니어링 포털에서 오간 대화 이력이다. 이것을 그대로 요약하지 말고,
읽는 사람이 판단에 쓸 수 있는 **보고서**로 재구성하라.

규칙:
- 결론을 먼저 쓴다. 무엇을 하기로 했는지/무엇이 밝혀졌는지가 첫 절이다.
- 근거는 대화에 실제로 나온 것만 쓴다. 수치는 원문 그대로 옮기고, 없는 값을 지어내지 않는다.
- 대화에서 결론이 나지 않은 것은 '미결'로 따로 모은다. 억지로 결론을 만들지 않는다.
- 누가 말했는지는 옮기지 않는다. 문서는 대화록이 아니다.
- 한국어. 문장은 마침표로 끝낸다.

형식(마크다운):
# <문서 제목 — 내용을 담은 짧은 제목>
## 요약
## 결론과 근거
## 미결·확인 필요
## 상세

대화 이력:
"""


@router.post("/export/docx")
async def export_docx(
    request: Request,
    body: DocxRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """대화 이력을 Word(.docx) 로 내려준다 — 브라우저가 그대로 저장한다.

    report 모드는 LLM 왕복이 있다. 실패하면 transcript 로 조용히 대체하지 않는다 —
    정리본을 기대한 사람에게 원문을 주면 '정리가 안 됐다'로 보이지 '실패했다'로 보이지 않는다.
    """
    # 모델 → dict. docx_export 는 dict 로 다루므로 여기서 한 번만 변환한다.
    audit = _audit(request)
    conv = body.conversation.model_dump()
    title = (conv.get("title") or "대화").strip()[:60]
    n_msg = len([m for m in (conv.get("messages") or []) if (m.get("text") or "").strip()])
    if not n_msg:
        return Response(content='{"error":"empty_conversation"}', status_code=400,
                        media_type="application/json")

    # ⚠ 게이트는 두 분기 모두에 건다. report 에만 걸어 두면 기본값인 transcript 가 무방비다 —
    # 총량 상한이 있어도 400만자 렌더는 수 초~수십 초 CPU 다. 같은 세마포어를 쓴다.
    sem = _sem(request)
    if sem.locked():
        audit.record(principal=principal.subject, event="docx", status="rejected",
                     meta={"reason": "max_concurrent_chats", "mode": body.mode})
        raise AuthError("too many concurrent exports; retry shortly", status_code=429)
    await sem.acquire()
    try:
        return await _export_docx_inner(request, body, principal, settings, audit, conv,
                                        title, n_msg)
    finally:
        sem.release()


async def _export_docx_inner(request, body, principal, settings, audit, conv, title, n_msg):
    # python-docx 는 여기서만 쓴다 — 임포트를 바깥에 두면 이 함수 스코프에 없어 NameError 다
    # (실측: 세마포어를 바깥으로 뺄 때 임포트를 같이 옮기지 않아 전문 내보내기가 500 이었다).
    from app.agent import docx_export as dx

    if body.mode == "transcript":
        # python-docx 렌더는 동기 CPU 작업이다. async 안에서 그대로 돌리면 그 시간만큼
        # 이벤트 루프가 멈춰 다른 사용자의 요청까지 함께 선다(대화검색 랭킹을 to_thread 로
        # 뺀 것과 같은 이유). 총량 상한이 있어도 400만자는 짧지 않다.
        data = await asyncio.to_thread(dx.build_transcript, conv)
        name = f"{title}-전문"
        audit.record(principal=principal.subject, event="docx_transcript",
                     status="ok", meta={"messages": n_msg})
    else:
        # ⚠ 이 경로는 /chat 과 똑같은 부하를 건다(에이전트 + LLM 왕복 수십 초). 그런데
        # 동시성 상한과 감사 기록을 둘 다 우회하고 있었다 — /chat 이 그 둘을 두는 이유가
        # 그대로 적용되는데도. 같은 게이트를 통과시킨다.
        # 세마포어는 바깥(export_docx)에서 이미 잡았다 — 이중 획득 금지.
        # ⚠ acquire 와 try 사이에 아무것도 두지 않는다. 그 틈에서 예외가 나면
        # 퍼밋이 영구히 새고, 상한만큼 쌓이면 챗 전체가 429 로 고정된다(실측 재현).
        # 대화 전체(총량 상한 400만자)를 문자열로 조립하는 동기 작업이다.
        _tx = await asyncio.to_thread(dx.transcript_text, conv)
        md = ""
        try:
            # 에이전트는 SSE 만 낸다(비스트리밍 엔드포인트가 없다). 여기서 스트림을 받아
            # 최종 result 만 모은다 — 에이전트에 엔드포인트를 새로 파는 것보다 접점이 적다.
            client = _agent_client(request)
            payload = {"message": _REPORT_PROMPT + _tx,
                       "groups": principal.groups, "user_email": principal.email,
                       "user_pat": _chat_user_pat(request.app.state.keystore,
                                                  get_settings(), principal) or ""}
            async with client.stream("POST", f"{settings.agent_server_url}/chat",
                                     json=payload) as resp:
                if resp.status_code == 200:
                    ev = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("event: "):
                            ev = line[7:].strip()
                        elif line.startswith("data: ") and ev == "result":
                            try:
                                md = json.loads(line[6:]).get("content", "") or md
                            except ValueError:
                                pass
        except httpx.HTTPError:
            md = ""
        audit.record(principal=principal.subject, event="docx_report",
                     status="ok" if md.strip() else "error",
                     meta={"messages": n_msg})
        if not md.strip():
            return Response(
                content='{"error":"report_failed","detail":"정리본 생성에 실패했습니다 — '
                        'LLM 응답이 없습니다. 전문(transcript) 내보내기는 그대로 동작합니다."}',
                status_code=503, media_type="application/json")
        first = next((ln.lstrip("# ").strip() for ln in md.splitlines()
                      if ln.startswith("#")), title)
        data = await asyncio.to_thread(dx.build_report, first, md,
                                       f"원본 대화 '{title}' · 발화 {n_msg}개")
        name = f"{first[:50]}-정리본"

    safe = re.sub(r'[\\/:*?"<>|]+', " ", name).strip() or "대화"
    quoted = quote(f"{safe}.docx")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


class UploadAnalyzeReq(BaseModel):
    model_config = {"extra": "ignore"}
    staging_id: str
    filename: str
    # 재료 메타 — AI 가 채우거나 사용자가 입력. dry_run 미리보기에 필요.
    material_name: str = ""
    category: str = "metal"           # metal/polymer/rubber/composite/ceramic/foam
    material_id: int | None = None    # 기존 재료에 붙일 때
    gauge_length_mm: float = 25.0
    width_mm: float = 5.0
    thickness_mm: float = 1.0


class UploadCommitReq(UploadAnalyzeReq):
    pass


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """챗 파일 업로드 — 수신·스테이징만 한다(파싱·등록은 이후 단계에서 materialtwin 에 위임).

    두 층 게이트의 백엔드 층 — 프론트가 버튼을 숨겨도 이 검사가 API 직접 호출을 막는다.
    업로드는 쓰기라 사용자 자격증명이 반드시 있어야 하고, 강등되면 안 된다(무음 강등 금지).
    """
    _upload.require_upload_group(settings, principal.groups)
    audit = _audit(request)
    meta = await _upload.stage_upload(settings, principal.subject, file)
    audit.record(principal=principal.subject, event="upload_stage", status="ok",
                 meta={"filename": meta["filename"], "size": meta["size"], "ext": meta["ext"]})
    # path 는 내부용 — 응답에 내보내지 않는다.
    return {k: v for k, v in meta.items() if k != "path"}


async def _upload_register(request, principal, settings, body, dry_run: bool):
    """스테이징 CSV 를 파싱해 물성 등록(dry_run 또는 확정)을 사용자 PAT 로 호출한다."""
    _upload.require_upload_group(settings, principal.groups)
    path = _upload.staged_path(settings, principal.subject, body.staging_id, body.filename)
    parsed = _upload.parse_tensile_csv(path)
    if not parsed.get("parsed"):
        return {"stage": "parse", **parsed}   # 열 매핑 실패 — 프론트가 사용자에게 매핑을 묻는다
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("업로드용 자격증명을 발급하지 못했습니다.", status_code=403)

    # 재료가 없으면 먼저 등록(확정 때만). dry_run 미리보기는 기존 material_id 없이도 곡선만 계산.
    mid = body.material_id
    if not dry_run and mid is None:
        if not body.material_name.strip():
            raise AuthError("material_name 이 필요합니다(새 재료).", status_code=422)
        matr = await _upload.mcp_call(settings.mcp_gateway_url, pat, "register_material",
                                      {"name": body.material_name, "category": body.category})
        mid = matr.get("material_id")
        if mid is None:
            return {"stage": "material", "error": matr.get("error") or matr.get("message"), "detail": matr}
    # dry_run 은 material_id 가 있어야 곡선 계산이 된다 — 없으면 임시로 등록 안 하고
    # material_id=0 을 못 쓰므로, 기존 재료 지정이 없으면 미리보기용으로 register_material dry_run 만.
    if dry_run and mid is None:
        # 재료 미리보기(저장 안 함) + 곡선은 material_id 필요 → 곡선 계산은 확정 시로 안내.
        matr = await _upload.mcp_call(settings.mcp_gateway_url, pat, "register_material",
                                      {"name": body.material_name or "(미정)", "category": body.category,
                                       "dry_run": True})
        return {"stage": "preview", "material_preview": matr, "curve": {"n_points": parsed["n_points"],
                "strain_col": parsed["strain_col"], "stress_col": parsed["stress_col"]},
                "note": "기존 재료를 지정하면 곡선 물성(E·항복·UTS) 미리보기가 나옵니다. "
                        "새 재료면 확정 시 재료 등록 후 곡선이 계산됩니다."}

    tool_args = {"material_id": mid, "strain": parsed["strain"], "stress_mpa": parsed["stress_mpa"],
                 "gauge_length_mm": body.gauge_length_mm, "width_mm": body.width_mm,
                 "thickness_mm": body.thickness_mm, "dry_run": dry_run}
    out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "register_tensile_test", tool_args)
    return {"stage": "preview" if dry_run else "committed", "material_id": mid, **out}


@router.post("/upload/analyze")
async def upload_analyze(
    request: Request,
    body: UploadAnalyzeReq,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """스테이징 파일을 파싱해 dry_run 미리보기(물성 계산, 저장 안 함)를 반환한다."""
    return await _upload_register(request, principal, settings, body, dry_run=True)


@router.post("/upload/commit")
async def upload_commit(
    request: Request,
    body: UploadCommitReq,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """사용자 확인 후 실제 등록(dry_run=False). 성공하면 스테이징 파일을 삭제한다."""
    audit = _audit(request)
    out = await _upload_register(request, principal, settings, body, dry_run=False)
    if out.get("stage") == "committed":
        try:
            _upload.staged_path(settings, principal.subject, body.staging_id, body.filename).unlink()
        except Exception:  # noqa: BLE001 — 삭제 실패가 등록 성공을 뒤집지 않게
            pass
        audit.record(principal=principal.subject, event="upload_commit", status="ok",
                     meta={"material_id": out.get("material_id"), "test_id": out.get("test_id")})
    return out


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

    # ⚠ acquire 와 gen() 사이는 반드시 보호한다. 여기서 예외가 나면 gen() 이 아예
    # 만들어지지 않으므로 그 안의 finally(sem.release) 가 영원히 실행되지 않는다 —
    # 퍼밋이 영구히 새고 상한(64)만큼 쌓이면 챗·docx 가 전부 429 로 고정된다.
    # 실제 방아쇠가 있다: store.append 는 sqlite3 를 예외 처리 없이 부른다
    # (database is locked / disk I/O error 등).
    try:

        # Pick the stream source. echo = local mock (no remote); else relay the Agent Server.
        if mode == "echo":
            source = _echo_stream(body.message, principal, audit)
        else:
            source = _relay_stream(body, principal, audit, settings, _agent_client(request),
                                   _chat_user_pat(request.app.state.keystore, settings, principal))

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

    except BaseException:
        sem.release()
        raise

    async def gen() -> AsyncIterator[bytes]:
        acc: list[str] = []          # token delta 누적(폴백)
        final: str | None = None     # result 프레임의 전체 텍스트(우선)
        decision: str | None = None  # 심의 결정문(result 없을 때 폴백)
        turns: list[dict] = []       # 심의 persona 발언 — MCP 경로와 대칭으로 서버에 남긴다
        activity: list[dict] = []    # status 이벤트(도구 호출·결과) 누적 — 심의 핸드오프 스냅샷 서버 영속
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
                        elif evt == "status" and data.get("tool"):
                            # 도구가 붙은 status 만 근거로 남긴다(진행 텍스트만 있는 건 스냅샷 대상 아님).
                            activity.append({
                                "step": str(data.get("step") or "")[:200],
                                "tool": str(data.get("tool"))[:80],
                                "detail": (str(data.get("detail"))[:400] if data.get("detail") else None),
                                "result_preview": (str(data.get("result_preview"))[:2000]
                                                   if data.get("result_preview") else None),
                            })
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
                    store.append(conversation_id=cid, owner_sub=owner, role="assistant", content=reply,
                                 meta=({"activity": activity[:60]} if activity else None))

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
