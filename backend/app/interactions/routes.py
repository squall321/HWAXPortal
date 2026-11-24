# 상호작용 기록 창구 — 공유(POST /interactions/share) · 내 기록 · 지우기 · 분석가 검색 · 원문 열기(contract §5 · §6)
"""박스 스위치 INTERACTIONS_ENABLED 가 꺼지면 모든 창구가 404 다(없는 것과 같다 — contract §1).

  · 공유 · 내 기록 · 지우기 — PAT(aud mcp-gateway) 또는 세션 + CSRF(principal_pat_or_session). 주인은 PAT sub · 세션 sub 의 이메일이다.
  · 분석가 — 세션만 · 권한 feat:interaction-analyst(grant_only — 관리자 전권에 딸려 오지 않는다). 검색 · 원문 열기마다 view_audit 한 줄.
저장소는 동기 sqlite 라 이벤트 루프 밖에서만 부른다(def 라우트 또는 to_thread — app/agent/routes.py 의 같은 경고)."""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, principal_pat_or_session
from app.interactions import ANALYST, NOTICE
from app.interactions import collector
from app.interactions.redact import redact, redact_text
from app.interactions.store import SURFACES, InteractionStore
from app.interactions import transcript as tx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interactions", tags=["interactions"])

ERASE_CONFIRM = "전부 지웁니다"
_MSG_MAX = 20000           # 도구로 받는 메시지 수 상한
_open_lock = threading.Lock()


def enabled(settings: Settings = Depends(get_settings)) -> Settings:
    """꺼진 박스에서는 없는 창구다 — 404(contract §1)."""
    if not settings.interactions_enabled:
        raise AuthError("Not Found", status_code=404)
    return settings


def store_of(app, settings: Settings) -> InteractionStore:
    """기동이 연 원장 — 없으면(시험 · 기동 뒤 켠 설정) 여기서 열고 둔다."""
    st = getattr(app.state, "interaction_store", None)
    if st is None:
        with _open_lock:
            st = getattr(app.state, "interaction_store", None)
            if st is None:
                st = InteractionStore(settings)
                app.state.interaction_store = st
    return st


def _who(p: Principal) -> str:
    return (p.email or p.subject or "").strip().lower()


def _surface(v: str) -> str:
    if v and v not in SURFACES:
        raise AuthError(f"surface 는 {' · '.join(SURFACES)} 중 하나", status_code=422)
    return v


# ── 상태(화면이 메뉴 · 알림을 그릴지) ─────────────────────────────────────────────
@router.get("/status")
def status(request: Request, detail: bool = False, principal: Principal = Depends(principal_pat_or_session),
           settings: Settings = Depends(enabled)) -> dict:
    """켜졌을 때만 200 — 화면은 이 답이 있을 때만 '내 기록' 메뉴와 알림 문구를 그린다. detail=1 이면 분석가 · 관리자에게 수집 상태(코드)와 원장의 수를
    함께 준다(분석가 화면 머리 — 헤더가 화면마다 묻는 답에는 싣지 않는다. 수 세기는 표 전체를 훑는다)."""
    analyst = ANALYST in principal.groups
    out: dict = {"enabled": True, "notice": NOTICE, "analyst": analyst, "share_max_mb": settings.interactions_share_max_mb}
    if detail and (analyst or "portal-admin" in principal.groups):
        ok, body = collector.health(request.app, settings)
        out["health"] = body
        out["counts"] = store_of(request.app, settings).counts()
    return out


# ── 공유(M2) ───────────────────────────────────────────────────────────────────
async def _read_capped(request: Request, cap: int) -> bytes:
    """본문을 상한까지만 읽는다 — Content-Length 가 넘으면 읽기 전에, 청크로 오면 넘는 순간 413."""
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > cap:
        raise AuthError(f"본문이 상한({cap // (1024 * 1024)} MB)을 넘는다", status_code=413)
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > cap:
            raise AuthError(f"본문이 상한({cap // (1024 * 1024)} MB)을 넘는다", status_code=413)
    return bytes(buf)


def _str(v, n: int, what: str) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        raise AuthError(f"{what} 는 글이어야 한다", status_code=422)
    return v.strip()[:n]


def share_work(store: InteractionStore, owner: str, data: dict) -> dict:
    """공유 본문 하나를 풀어 넣는다 → 답. 무거운 일(기록 파일 풀이 · 가림 · 압축)이라 스레드에서 돈다."""
    sid = _str(data.get("session_id"), 200, "session_id")
    title = _str(data.get("title"), 200, "title")
    client = _str(data.get("client"), 200, "client")
    msgs_in, text = data.get("messages"), data.get("transcript")
    if bool(msgs_in) == bool(text):
        raise AuthError("messages 또는 transcript 둘 중 하나만 싣는다", status_code=422)
    meta: dict = {}
    if text:
        if not isinstance(text, str):
            raise AuthError("transcript 는 Claude Code 기록 파일(JSONL) 글이어야 한다", status_code=422)
        p = tx.parse(text)
        msgs, raw, kind = p["messages"], p["raw"], "transcript"
        sid, title, client = sid or p["session_id"] or uuid.uuid4().hex, title or p["title"], client or p["client"]
        meta = {"lines": p["lines"], "skipped": p["skipped"]}
    else:
        if not isinstance(msgs_in, list) or len(msgs_in) > _MSG_MAX:
            raise AuthError(f"messages 는 {_MSG_MAX}개 이하의 목록이어야 한다", status_code=422)
        msgs = []
        for m in msgs_in:
            if not isinstance(m, dict) or m.get("role") not in ("user", "assistant") or not isinstance(m.get("content"), str):
                raise AuthError("messages 의 줄은 {role: user|assistant, content: 글} 이어야 한다", status_code=422)
            msgs.append({"role": m["role"], "content": redact_text(m["content"])})
        raw, kind = None, "tool"
        sid = sid or uuid.uuid4().hex
        title = title or next((m["content"].strip().splitlines()[0][:80] for m in msgs if m["role"] == "user" and m["content"].strip()), "")
        client = client or "share_conversation"
    msgs = redact(msgs)
    res = store.put_shared(owner=owner, session_id=sid, title=redact_text(title), client=client, messages=msgs, kind=kind, raw=raw,
                           event={"input": title, "output": tx.render(msgs), "meta": meta})
    return {"id": res["id"], "session_id": sid, "kind": kind, "messages": len(msgs), "chars": res["chars"],
            "created": res["created"], **meta}


@router.post("/share")
async def share(request: Request, principal: Principal = Depends(principal_pat_or_session),
                settings: Settings = Depends(enabled)) -> dict:
    """공유한 Claude 대화(contract §5) — 본문 {session_id?, title?, client?, messages? | transcript?}(둘 중 하나 · 50 MB). 같은 session_id 는
    덮어쓴다(주인마다). 서버도 가림을 한 번 더 건다. 기록 파일(transcript)은 사람 · 어시스턴트 글과 도구 호출을 꺼내고 원문도 가린 채 압축해 둔다."""
    owner = _who(principal)
    if not owner:
        raise AuthError("주인을 알 수 없는 자격이다(이메일 · subject 없음)", status_code=403)
    raw = await _read_capped(request, max(1, settings.interactions_share_max_mb) * 1024 * 1024)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AuthError("본문이 UTF-8 JSON 이 아니다", status_code=422) from exc
    if not isinstance(data, dict):
        raise AuthError("본문은 JSON 객체여야 한다", status_code=422)
    st = store_of(request.app, settings)
    out = await asyncio.to_thread(share_work, st, owner, data)
    logger.info("상호작용 — 공유 대화 %s: %s · %s · 메시지 %d", "새로" if out["created"] else "덮어씀", owner, out["kind"], out["messages"])
    return out


# ── 내 기록 · 지우기(M3 — 본인만) ─────────────────────────────────────────────────
def _with_shared(st: InteractionStore, ev: dict, owner: str | None, *, raw: bool = False) -> dict:
    sid = (ev.get("meta") or {}).get("shared_id") if ev.get("surface") == "shared_claude" else None
    if sid:
        ev["shared"] = st.shared(sid, owner, with_raw=raw)
    return ev


@router.get("/me")
def my_list(request: Request, q: str = Query("", max_length=200), surface: str = Query("", max_length=40),
            before: str = Query("", max_length=40), limit: int = Query(50, ge=1, le=200),
            principal: Principal = Depends(principal_pat_or_session), settings: Settings = Depends(enabled)) -> dict:
    out = store_of(request.app, settings).search(actor=_who(principal), q=q, surface=_surface(surface), before=before, limit=limit)
    return {**out, "notice": NOTICE}


@router.delete("/me")
async def my_erase(request: Request, principal: Principal = Depends(principal_pat_or_session),
                   settings: Settings = Depends(enabled)) -> dict:
    """내 기록 전부 지우기 청구 — 본문 {confirm: "전부 지웁니다"}. 사건 · 공유 대화를 지우고 지우기 표지를 남긴다(그 시각 전 줄은 다시 들어오지 않는다)."""
    try:
        body = json.loads((await request.body()).decode("utf-8") or "{}")
    except (UnicodeDecodeError, ValueError):
        body = {}
    if not isinstance(body, dict) or body.get("confirm") != ERASE_CONFIRM:
        raise AuthError(f"지우려면 본문에 confirm: '{ERASE_CONFIRM}' 을 싣는다", status_code=422)
    who = _who(principal)
    got = await asyncio.to_thread(store_of(request.app, settings).erase, who)
    logger.warning("상호작용 — 본인 지우기 청구: %s · 사건 %d · 공유 대화 %d", who, got["events"], got["shared"])
    return got


@router.get("/me/{eid}", response_model=None)
def my_get(eid: str, request: Request, raw: bool = False, principal: Principal = Depends(principal_pat_or_session),
           settings: Settings = Depends(enabled)) -> dict | PlainTextResponse:
    st = store_of(request.app, settings)
    who = _who(principal)
    ev = st.get(eid, who)
    if ev is None:
        raise AuthError("없는 기록이다", status_code=404)
    ev = _with_shared(st, ev, who, raw=raw)
    if raw:
        body = (ev.get("shared") or {}).get("raw")
        if body is None:
            raise AuthError("원문 파일이 없는 기록이다", status_code=404)
        return PlainTextResponse(body, media_type="application/x-ndjson; charset=utf-8")
    return ev


# ── 분석가(M3 — feat:interaction-analyst · 열람 감사) ─────────────────────────────
@router.get("/admin/search")
def admin_search(request: Request, q: str = Query("", max_length=200), actor: str = Query("", max_length=200),
                 surface: str = Query("", max_length=40), app: str = Query("", max_length=80), status: str = Query("", max_length=10),
                 days: int = Query(0, ge=0, le=3650), before: str = Query("", max_length=40), limit: int = Query(50, ge=1, le=200),
                 principal: Principal = Depends(get_current_principal), settings: Settings = Depends(enabled)) -> dict:
    """남의 기록 검색 — 결과의 미리보기도 원문 조각이라 검색마다 감사 한 줄(action search · owner 는 거른 사람)."""
    ensure(principal, ANALYST)
    st = store_of(request.app, settings)
    out = st.search(actor=actor or None, q=q, surface=_surface(surface), app=app, status=status,
                    since=int(time.time()) - days * 86400 if days else None, before=before, limit=limit)
    st.audit(viewer=_who(principal), owner=actor or None, action="search")
    return out


@router.get("/admin/{eid}", response_model=None)
def admin_get(eid: str, request: Request, raw: bool = False, principal: Principal = Depends(get_current_principal),
              settings: Settings = Depends(enabled)) -> dict | PlainTextResponse:
    """남의 원문 열기 — 열 때마다 view_audit 한 줄(contract §6). raw=1 은 공유 대화의 기록 파일 원문(가린 것)."""
    ensure(principal, ANALYST)
    st = store_of(request.app, settings)
    ev = st.get(eid)
    if ev is None:
        raise AuthError("없는 기록이다", status_code=404)
    ev = _with_shared(st, ev, None, raw=raw)
    viewer = _who(principal)
    st.audit(viewer=viewer, owner=ev.get("actor"), action="open_raw" if raw else "open", event_id=eid,
             shared_id=(ev.get("shared") or {}).get("id"))
    logger.info("상호작용 — 분석가 원문 열기: %s → %s(%s)%s", viewer, eid, ev.get("actor"), " 원문 파일" if raw else "")
    if raw:
        body = (ev.get("shared") or {}).get("raw")
        if body is None:
            raise AuthError("원문 파일이 없는 기록이다", status_code=404)
        return PlainTextResponse(body, media_type="application/x-ndjson; charset=utf-8")
    return ev
