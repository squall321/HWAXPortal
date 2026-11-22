# 전문가 팀 API(/agent/teams) — 목록 · 만들기 · 고치기(판 번호) · 지우기 · 공식 표지(관리자) · 그 사람의 시야로 푼 사본(docs/expert-teams PLAN 3-1)
"""권한은 `feat:expert-chat`(전문가와 대화). 읽기(목록 · 사본)는 세션 또는 사람 PAT, 쓰기는 브라우저 세션 + CSRF 만 받는다 — 팀은 사람이 화면에서
짠다. 없는 팀과 못 보는 팀은 같은 404 다(id 를 넣어 보는 것만으로 남의 팀이 있는지 알 수 없게). 사본(resolve)은 못 풀어도 200 에 null + 까닭이다 —
루틴 실행 원장 · 절차 넘기기가 같은 판정(resolve_for)을 쓴다."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ValidationError

from app.access.agent_guard import persona_allowed
from app.access.policy import ADMIN_GROUP
from app.agent import teams as T
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf
from app.insights.cards import Viewer

router = APIRouter(prefix="/agent/teams", tags=["teams"])
NOTE = ("팀은 사람만 묶는다 — 고르면 그 순간 대화의 지정값으로 복사되고, 그 사람이 쓸 수 없는 전문가(앱 권한이 없는 HE팀 운영자)는 쓰는 순간 빠진다. "
        "공식 표지는 관리자가 단다.")


def _store(request: Request) -> T.TeamStore:
    st = getattr(request.app.state, "team_store", None)
    if st is None:
        raise AuthError("팀 저장소가 열리지 않았습니다", status_code=503)
    return st


def viewer_of(request: Request, principal: Principal) -> Viewer:
    # 요청마다 원장으로 센 소속(권한표에 없는 값은 빈 값)
    from app.agent.wiki_send import known_affiliation
    return Viewer(email=(principal.email or "").strip().lower(), sub=principal.subject, aff=known_affiliation(request),
                  groups=frozenset(principal.groups), admin=ADMIN_GROUP in principal.groups)


def resolve_for(request: Request, principal: Principal, team_id: str) -> T.Resolved:
    """팀 id → 그 사람의 사본(없거나 못 보면 None + 까닭). 저장소가 안 열렸으면 그 까닭으로 None — 루틴 · 절차는 팀 없이 돈다."""
    st = getattr(request.app.state, "team_store", None)
    if st is None:
        return T.Resolved(None, "팀 저장소가 열리지 않아 팀을 쓰지 않는다")
    v = viewer_of(request, principal)
    policy = request.app.state.access.get()
    groups = list(principal.groups)
    return T.resolve(st.get(team_id), v, lambda key: persona_allowed(policy, key, groups), team_id=team_id)


def _reader(principal: Principal = Depends(principal_pat_or_session)) -> Principal:
    ensure(principal, T.FEAT)
    return principal


def _writer(principal: Principal = Depends(get_current_principal), _csrf: None = Depends(require_csrf)) -> Principal:
    """쓰기는 브라우저 세션 + CSRF 만 — 사람이 화면에서 한다(PAT 로는 못 쓴다)."""
    ensure(principal, T.FEAT)
    return principal


def _seen(request: Request, v: Viewer, tid: str) -> dict:
    row = _store(request).get(tid) if T.TEAM_ID_RE.match(tid) else None
    if row is None or not T.visible(row, v):
        raise AuthError("팀을 찾을 수 없습니다", status_code=404)
    return row


def _org_ok(body_scope: str | None, aff: str) -> None:
    if body_scope == "org" and not aff:
        raise AuthError("소속이 없어 같은 소속에 공유할 수 없습니다 — 나만(private)으로 두거나 관리자에게 소속을 받으세요", status_code=422)


@router.get("")
def list_teams(request: Request, principal: Principal = Depends(_reader)) -> dict:
    v = viewer_of(request, principal)
    return {"teams": [T.view(r, v) for r in _store(request).rows(v)], "note": NOTE}


@router.post("", status_code=201)
def create_team(request: Request, body: T.TeamBody, principal: Principal = Depends(_writer)) -> dict:
    v = viewer_of(request, principal)
    _org_ok(body.scope, v.aff)
    row = _store(request).create(body, owner_email=v.email, owner_sub=principal.subject, owner_aff=v.aff)
    return T.view(row, v)


@router.patch("/{tid}")
def update_team(request: Request, tid: str, body: T.TeamPatch, principal: Principal = Depends(_writer)) -> dict:
    v = viewer_of(request, principal)
    row = _seen(request, v, tid)
    if not T.editable(row, v):
        raise AuthError("팀은 주인과 관리자만 고칩니다", status_code=403)
    try:
        merged = body.merged(row)
    except ValidationError as exc:
        msgs = [str(e.get("msg") or "").removeprefix("Value error, ") for e in exc.errors()[:4]]
        raise AuthError(f"팀 칸이 맞지 않습니다 — {' / '.join(msgs)}"[:400], status_code=422) from None
    mine = T.owner_of(row, v)
    # 주인이 고치면 공유 범위의 소속을 지금 소속으로 새긴다(ET-6) — 관리자가 고칠 때는 주인의 소속을 그대로 둔다
    _org_ok(merged.scope, v.aff if mine else str(row.get("owner_aff") or ""))
    got = _store(request).update(tid, merged, expected_version=body.expected_version, by=v.email,
                                 owner_aff=v.aff if mine else None)
    if got == "missing":
        raise AuthError("팀을 찾을 수 없습니다", status_code=404)
    if got == "conflict":
        cur = _store(request).get(tid) or {}
        raise AuthError(f"그새 다른 곳에서 고쳤습니다(지금 판 {cur.get('version')}, 보낸 판 {body.expected_version}) — 다시 불러와 고치세요",
                        status_code=409)
    return T.view(_store(request).get(tid), v)


@router.delete("/{tid}")
def delete_team(request: Request, tid: str, principal: Principal = Depends(_writer)) -> dict:
    v = viewer_of(request, principal)
    row = _seen(request, v, tid)
    if not T.deletable(row, v):
        raise AuthError("공식 팀은 관리자만 지웁니다" if row.get("official") and T.owner_of(row, v) else "팀은 주인과 관리자만 지웁니다",
                        status_code=403)
    _store(request).delete(tid)
    return {"ok": True, "deleted": tid}


class OfficialIn(BaseModel):
    model_config = {"extra": "forbid"}
    on: bool


@router.post("/{tid}/official")
def set_official(request: Request, tid: str, body: OfficialIn, principal: Principal = Depends(_writer)) -> dict:
    v = viewer_of(request, principal)
    if not v.admin:
        raise AuthError("공식 표지는 관리자만 답니다", status_code=403)
    _seen(request, v, tid)
    _store(request).set_official(tid, body.on, by=v.email)
    return T.view(_store(request).get(tid), v)


@router.get("/{tid}/resolve")
def resolve_team(request: Request, tid: str, principal: Principal = Depends(_reader)) -> dict:
    """그 사람의 시야로 푼 사본(PLAN 3-2) — 못 풀면 team 이 null 이고 까닭이 있다. 빠진 보조는 hidden 에."""
    _store(request)
    got = resolve_for(request, principal, tid) if T.TEAM_ID_RE.match(tid) else T.Resolved(None, f"팀 {tid[:40]} 를 찾을 수 없다")
    return {"team": got.team, "why": got.why, "hidden": got.hidden}
