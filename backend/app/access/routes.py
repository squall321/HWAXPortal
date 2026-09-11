# 소속·허가 API — 내 권한·허가 요청(사용자), 소속·허가 편집·요청 결정(관리자), 게이트웨이 조회
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.access.policy import ADMIN_GROUP, compute
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal, require_csrf, require_role

router = APIRouter(tags=["access"])


def _store(request: Request):
    return request.app.state.user_store


def _policy(request: Request):
    return request.app.state.access.get()


def _reason_text(reason: str, policy, affiliation: str) -> str:
    """사람에게 보일 허가 이유."""
    if reason == "admin":
        return "관리자"
    if reason == "grant":
        return "개별 허가"
    if reason == "affiliation":
        label = (policy.affiliations.get(affiliation) or {}).get("label") or affiliation
        return f"소속 기본({label})"
    if reason == "default":
        return "모든 사용자 기본"
    if reason.startswith("implied:"):
        src = policy.item(reason.split(":", 1)[1])
        return f"{src.label if src else reason}에 포함"
    return reason


def _table(policy, ents, pending: dict[str, dict]) -> dict:
    def row(i):
        allowed = i.key in ents.keys
        return {"key": i.key, "id": i.id, "label": i.label, "desc": i.desc, "allowed": allowed,
                "reason": (_reason_text(ents.reasons[i.key], policy, ents.affiliation)
                           if allowed else ""),
                "request": pending.get(i.key)}
    return {"features": [row(i) for i in policy.items if i.kind == "feature"],
            "platforms": [row(i) for i in policy.items if i.kind == "platform"]}


@router.get("/auth/access")
def my_access(request: Request, principal: Principal = Depends(get_current_principal)) -> dict:
    """내 권한 — 모든 기능·플랫폼에 대해 쓸 수 있나, 왜, 요청했으면 그 상태."""
    policy = _policy(request)
    ents = getattr(request.state, "entitlements", None) or compute(
        policy, groups=principal.groups, row=_store(request).get(principal.email))
    pending = {}
    for r in _store(request).list_requests(email=principal.email, limit=500):
        if r["key"] not in pending:           # 최신순 — 키마다 가장 최근 요청만
            pending[r["key"]] = {"id": r["id"], "status": r["status"],
                                 "created_at": r["created_at"]}
    aff = policy.affiliations.get(ents.affiliation)
    return {"affiliation": ents.affiliation, "affiliation_label": (aff or {}).get("label") or "",
            "is_admin": ents.is_admin, **_table(policy, ents, pending)}


class AccessRequestIn(BaseModel):
    key: str = Field(min_length=6, max_length=80)
    note: str = Field(default="", max_length=500)


@router.post("/auth/access/requests")
def request_access(body: AccessRequestIn, request: Request,
                   principal: Principal = Depends(get_current_principal),
                   _csrf: None = Depends(require_csrf)) -> dict:
    policy = _policy(request)
    if policy.item(body.key) is None:
        raise AuthError("모르는 권한입니다", status_code=404)
    if body.key in principal.groups:
        raise AuthError("이미 쓸 수 있는 권한입니다", status_code=409)
    return _store(request).create_request(email=principal.email, key=body.key, note=body.note)


# ── 관리자 ──────────────────────────────────────────────────────────────────
@router.get("/auth/access/policy")
def access_policy(request: Request, _p: Principal = Depends(get_current_principal)) -> dict:
    """정책 표(기능·플랫폼·소속) — 관리자 화면의 체크 목록과 내 권한 페이지의 머리말."""
    policy = _policy(request)
    return {"features": [{"key": i.key, "label": i.label, "desc": i.desc,
                          "implies": list(i.implies)} for i in policy.items if i.kind == "feature"],
            "platforms": [{"key": i.key, "label": i.label, "desc": i.desc} for i in policy.items
                          if i.kind == "platform"],
            "affiliations": [{"id": k, "label": v["label"], "grants": v["grants"]}
                             for k, v in policy.affiliations.items()],
            "default_grants": policy.default_grants}


@router.get("/auth/access/requests")
def list_access_requests(request: Request, status: str = Query(default="pending", max_length=20),
                         _admin: Principal = Depends(require_role(ADMIN_GROUP))) -> list[dict]:
    return _store(request).list_requests(status=status or None)


class DecideIn(BaseModel):
    approve: bool


@router.post("/auth/access/requests/{req_id}/decide")
def decide_access_request(req_id: int, body: DecideIn, request: Request,
                          admin: Principal = Depends(require_role(ADMIN_GROUP)),
                          _csrf: None = Depends(require_csrf)) -> dict:
    out = _store(request).decide_request(req_id, approve=body.approve, by=admin.email)
    if out is None:
        raise AuthError("대기 중인 요청이 아닙니다", status_code=404)
    return out


class UserAccessIn(BaseModel):
    affiliation: str | None = Field(default=None, max_length=40)
    grants: list[str] | None = Field(default=None, max_length=100)


@router.patch("/auth/access/users/{email}")
def set_user_access(email: str, body: UserAccessIn, request: Request,
                    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
                    _csrf: None = Depends(require_csrf)) -> dict:
    """소속·개별 허가 편집. 표에 없는 키·소속은 거절한다 — 오타가 권한이 되지 않게."""
    policy = _policy(request)
    if body.affiliation and body.affiliation not in policy.affiliations:
        raise AuthError(f"모르는 소속입니다: {body.affiliation}", status_code=422)
    if body.grants is not None:
        bad = [g for g in body.grants if policy.item(g) is None]
        if bad:
            raise AuthError(f"모르는 권한입니다: {', '.join(bad)}", status_code=422)
    store = _store(request)
    if store.get(email) is None:
        raise AuthError("사용자가 없습니다", status_code=404)
    store.set_access(email, affiliation=body.affiliation, grants=body.grants)
    u = store.get(email) or {}
    return {"email": u.get("email"), "affiliation": u.get("affiliation") or "",
            "grants": u.get("grants") or []}


# ── 게이트웨이 내부 조회 — 공유 시크릿으로만 연다(connections 와 같은 문) ─────────────
def _internal(request: Request, settings: Settings) -> None:
    expected = settings.gateway_shared_token
    if not expected:
        raise AuthError("internal access disabled (GATEWAY_SHARED_TOKEN unset)", status_code=503)
    if request.headers.get("authorization", "") != f"Bearer {expected}":
        raise AuthError("forbidden", status_code=403)


@router.get("/internal/access/policy")
def internal_policy(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """게이트웨이 백엔드별 필요 권한 — 게이트웨이가 allowed_groups 로 쓴다(access-control D-4)."""
    _internal(request, settings)
    return {"backends": _policy(request).gateway_policy()}


@router.get("/internal/access/entitlements")
def internal_entitlements(request: Request, email: str = Query(min_length=3, max_length=200),
                          groups: str = Query(default="", max_length=2000),
                          settings: Settings = Depends(get_settings)) -> dict:
    """이 사람의 **지금** 권한 — 게이트웨이가 PAT 에 박힌 옛 그룹 대신 쓴다(D-2).
    groups 는 토큰이 가진 로그인 그룹(관리자 여부 판정용)이고 합성 그룹은 여기서 버린다."""
    _internal(request, settings)
    base = [g for g in groups.split(",") if g]
    ents = compute(_policy(request), groups=base, row=_store(request).get(email))
    return {"email": email, "keys": sorted(ents.keys)}
