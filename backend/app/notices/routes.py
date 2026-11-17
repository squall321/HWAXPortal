# 포털 알림 API(/notices-api) — 내 알림 목록(최신 것부터 · 안 읽은 수) · 하나 읽음 · 모두 읽음(docs/request-1117 contracts §7)
"""브라우저 세션으로만 — 읽기는 세션, 쓰기(읽음 표시)는 세션 + CSRF(다른 화면 창구와 같은 꼴). 늘 그 사람(로그인 이메일)의 알림만 보고 바꾼다 —
남의 알림 id 는 없는 것과 같은 404 다(있다는 것도 흘리지 않는다). 권한 키는 따로 없다 — 제 알림은 누구나 본다."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.deps import get_current_principal, require_csrf
from app.notices.store import LIST_DEFAULT, LIST_MAX

router = APIRouter(prefix="/notices-api", tags=["notices"])


def _store(request: Request):
    st = getattr(request.app.state, "notice_store", None)
    if st is None:
        raise AuthError("알림 원장이 열리지 않았습니다", status_code=503)
    return st


def _me(principal: Principal) -> str:
    return (principal.email or "").strip().lower()


def _writer(principal: Principal = Depends(get_current_principal), _csrf: None = Depends(require_csrf)) -> Principal:
    return principal


@router.get("")
def mine(request: Request, limit: int = Query(LIST_DEFAULT, ge=1, le=LIST_MAX),
         principal: Principal = Depends(get_current_principal)) -> dict:
    st, me = _store(request), _me(principal)
    if not me:
        return {"items": [], "unread": 0}
    return {"items": st.list_for(me, limit=limit), "unread": st.unread(me)}


@router.post("/read-all")
def read_all(request: Request, principal: Principal = Depends(_writer)) -> dict:
    st, me = _store(request), _me(principal)
    n = st.mark_all_read(me) if me else 0
    return {"marked": n, "unread": st.unread(me) if me else 0}


@router.post("/{nid}/read")
def read_one(request: Request, nid: str = Path(..., min_length=1, max_length=64),
             principal: Principal = Depends(_writer)) -> dict:
    st, me = _store(request), _me(principal)
    if not me or not st.mark_read(me, nid):
        raise AuthError("알림을 찾지 못했습니다", status_code=404)
    return {"ok": True, "unread": st.unread(me)}
