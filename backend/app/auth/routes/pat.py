# 포털 PAT(장기 scope=api RS256 JWT) 발급·목록·폐기 + 게이트웨이용 공개 폐기목록 라우터
"""Portal PAT (Personal Access Token) endpoints.

A PAT shares the launch-token trust root (portal keystore → JWKS) but is longer-lived,
multi-audience, and `scope="api"`. The HWAX REST API gateway verifies it via
`/.well-known/jwks.json` and forwards to sub-site REST APIs with each site's own service
token — the sub-sites are never changed. Revocation = the token_store jti denylist,
published (non-expired revoked jtis) at `/auth/pat/revoked.json` for the gateway to poll.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal, require_csrf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/pat", tags=["pat"])


class PatCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    audiences: list[str] = Field(default_factory=list)  # sites this PAT may reach; empty → config default
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    # 0 = 무기한(만료로는 안 죽고 폐기로만 죽는다). None 이면 서버 기본값.
    ttl_days: int | None = Field(default=None, ge=0, le=36500)


class PatMeta(BaseModel):
    jti: str
    name: str
    audiences: list[str]
    scopes: list[str]
    created: int
    exp: int
    revoked: bool


class PatCreated(PatMeta):
    token: str  # the JWT — shown ONCE, never stored server-side


def _mint_pat(request: Request, settings: Settings, principal: Principal, *,
              name: str, audiences: list[str], scopes: list[str], ttl_days: int):
    keystore = request.app.state.keystore
    now = datetime.now(tz=UTC)
    exp = now + timedelta(days=ttl_days)
    jti = secrets.token_urlsafe(24)
    claims = {
        "iss": settings.jwt_issuer,
        "sub": principal.subject,
        "email": principal.email,
        "name": principal.display_name,
        "groups": principal.groups,
        "aud": audiences,        # array — the gateway checks the target site is a member
        "scope": "api",          # distinguishes a PAT from a 90s "launch" token
        "scopes": scopes,
        "pat_name": name,
        "iat": now, "nbf": now, "exp": exp,
        "jti": jti,
    }
    token = jwt.encode(claims, keystore.private_pem, algorithm="RS256",
                       headers={"kid": keystore.active_kid})
    return token, jti, int(now.timestamp()), int(exp.timestamp())


@router.post("", response_model=PatCreated)
def create_pat(
    body: PatCreate,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> PatCreated:
    # ttl_days=0 은 '무기한' 이다. `or` 로 기본값을 채우면 0 이 falsy 라 90일로 둔갑하므로
    # None 과 0 을 반드시 구분한다.
    never = body.ttl_days == 0
    ttl = settings.pat_never_ttl_days if never else (body.ttl_days or settings.pat_ttl_days)
    if not never and (ttl < 1 or ttl > settings.pat_max_ttl_days):
        raise AuthError(f"ttl_days must be 0(무기한) or 1..{settings.pat_max_ttl_days}",
                        status_code=400)
    auds = body.audiences or settings.pat_default_audience_list
    allowed = set(settings.pat_default_audience_list)  # least privilege: only known sites
    bad = [a for a in auds if a not in allowed]
    if bad:
        raise AuthError(f"unknown audience(s): {', '.join(bad)}", status_code=400)
    token, jti, created, exp = _mint_pat(
        request, settings, principal,
        name=body.name, audiences=auds, scopes=body.scopes, ttl_days=ttl,
    )
    request.app.state.token_store.record_pat(
        jti=jti, sub=principal.subject, email=principal.email, name=body.name,
        aud=auds, scopes=body.scopes, created=created, exp=exp,
    )
    # 발급을 남긴다 — 특히 무기한은 만료로 안 죽으므로 "누가 언제 냈나" 가 사후 유일한
    # 단서다. token_store 행 하나만으로는 조회 경로가 관리자 목록뿐이라 부족하다.
    logger.warning("PAT issued: sub=%s name=%s aud=%s ttl=%s%s",
                   principal.subject, body.name, auds,
                   "무기한" if never else f"{ttl}d",
                   " ⚠NEVER-EXPIRES" if never else "")
    return PatCreated(jti=jti, name=body.name, audiences=auds, scopes=body.scopes,
                      created=created, exp=exp, revoked=False, token=token)


@router.get("", response_model=list[PatMeta])
def list_pat(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> list[PatMeta]:
    return [PatMeta(**r) for r in request.app.state.token_store.list_pats(principal.subject)]


@router.get("/all")
def list_all_pats(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> list[dict]:
    """전체 PAT 메타 — 관리자 전용. 토큰 자체는 어디에도 실리지 않는다.

    무기한 토큰은 폐기가 유일한 통제인데, 남의 토큰을 찾을 방법이 없으면 그 폐기를
    실행할 수 없다. 목록 없이 '폐기하면 된다' 고만 적어 두는 것은 통제가 아니다.
    """
    if "portal-admin" not in principal.groups:
        raise AuthError("admin only", status_code=403)
    return request.app.state.token_store.all_pats()


@router.delete("/{jti}")
def revoke_pat(
    jti: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
) -> dict:
    is_admin = "portal-admin" in principal.groups
    ok = request.app.state.token_store.revoke_pat(jti, None if is_admin else principal.subject)
    if not ok:
        raise AuthError("token not found", status_code=404)
    return {"revoked": jti}


@router.get("/revoked.json")
def revoked_list(request: Request) -> JSONResponse:
    """PUBLIC denylist (opaque jtis) the REST gateway polls to enforce pre-expiry revocation."""
    return JSONResponse(
        {"revoked": request.app.state.token_store.revoked_jtis()},
        headers={"Cache-Control": "public, max-age=60"},
    )
