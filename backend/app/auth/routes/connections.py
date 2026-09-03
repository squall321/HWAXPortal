# 외부 서비스 연결 토큰 — 사용자가 RA 등에서 발급받은 PAT 를 등록하면 게이트웨이가
# 그 사람 자격증명으로 해당 서비스를 부른다(SSO 전 브리지, 사용자 발안 2026-09-03).
"""Service connection tokens.

흐름: 사용자가 Report Archive 에서 PAT(rat_…)를 발급 → 포털 API 토큰 페이지에 붙여넣기 →
포털이 RA /api/users/me 로 검증(이메일 일치 강제)하고 부서(home_workspace_slug)까지 얻어
저장 → 게이트웨이가 RA 호출 시 /internal/connections 로 조회해 그 토큰+부서 헤더로 호출.
SSO 가 연동되면 RA 쪽 자동 계정 등록으로 대체될 브리지다 — 그날 이 등록부는 자연 소멸.
"""
import logging

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.deps import principal_pat_or_session, require_csrf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["connections"])

SERVICES = ("reportarchive",)


def _store(request: Request) -> UserStore:
    return request.app.state.user_store


class ConnectionIn(BaseModel):
    token: str = Field(min_length=8, max_length=512)


async def _ra_profile(settings: Settings, token: str) -> dict:
    """RA 토큰 검증 + 프로필 — 실패는 AuthError(사용자에게 보여줄 문구)로 승격."""
    url = settings.ra_base_url.rstrip("/") + "/api/me"  # openapi 실측 — /api/users/me 아님
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            resp = await cli.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        raise AuthError(f"Report Archive 에 연결하지 못했습니다({exc.__class__.__name__}). "
                        "서비스가 떠 있는지 확인하세요.", status_code=502) from exc
    if resp.status_code == 401:
        raise AuthError("Report Archive 가 이 토큰을 거부했습니다 — 만료됐거나 잘못 복사됐습니다.",
                        status_code=400)
    if resp.status_code != 200:
        raise AuthError(f"Report Archive 검증 실패(HTTP {resp.status_code}).", status_code=400)
    me = resp.json()
    # RA 는 {success, data:{…}} 봉투로 감싼다(실측) — data 를 벗겨 반환.
    return me["data"] if isinstance(me, dict) and isinstance(me.get("data"), dict) else me


@router.put("/auth/connections/reportarchive")
async def set_ra_connection(
    body: ConnectionIn,
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
) -> JSONResponse:
    token = body.token.strip()
    me = await _ra_profile(settings, token)
    ra_user = me.get("user") or {}
    ra_email = str(ra_user.get("email") or "").strip().lower()
    # 이메일 일치 강제 — 남의 토큰을 등록하면 그 사람 명의로 보고서가 쌓인다(오귀속).
    if ra_email and ra_email != principal.email.lower():
        raise AuthError(
            f"RA 계정 이메일({ra_email})이 포털 계정({principal.email})과 다릅니다. "
            "같은 이메일의 RA 계정에서 발급한 토큰을 등록하세요.", status_code=400)
    ws_slug = str(me.get("home_workspace_slug") or "")
    mems = me.get("memberships") or []
    # home 미지정 계정(RA 구계정 등) 폴백 — 개인(personal-*) 아닌 첫 부서 멤버십.
    if not ws_slug:
        ws_slug = next((str(m.get("workspace_slug") or "") for m in mems
                        if m.get("workspace_kind") != "personal"
                        and not str(m.get("workspace_slug") or "").startswith("personal-")), "")
    ws_name = next((str(m.get("workspace_name") or "") for m in mems
                    if m.get("workspace_slug") == ws_slug), "")
    store = _store(request)
    store.set_connection(email=principal.email, service="reportarchive",
                         token=token, workspace=ws_slug)
    # 부서 자동 채움 — 포털 계정에 부서가 비어 있으면 RA 의 소속 부서로.
    u = store.get(principal.email)
    dept_filled = ""
    if u is not None and not (u.get("department") or "").strip() and (ws_name or ws_slug):
        store.set_department(principal.email, ws_name or ws_slug)
        dept_filled = ws_name or ws_slug
    logger.info("connection set: reportarchive for %s (ws=%s)", principal.email, ws_slug)
    return JSONResponse({"ok": True, "workspace": ws_slug, "workspace_name": ws_name,
                         "department_filled": dept_filled})


@router.get("/auth/connections")
def list_connections(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    store = _store(request)
    return {s: store.connection_meta(email=principal.email, service=s) for s in SERVICES}


@router.delete("/auth/connections/reportarchive")
def delete_ra_connection(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    _store(request).delete_connection(email=principal.email, service="reportarchive")
    return JSONResponse({"ok": True})


# ── 게이트웨이 전용 내부 조회 — 공유 시크릿(GW_TOKEN)으로만 연다 ─────────────────
@router.get("/internal/connections/{service}")
def internal_connection(
    service: str,
    request: Request,
    email: str = Query(min_length=3, max_length=200),
    settings: Settings = Depends(get_settings),
) -> dict:
    expected = settings.gateway_shared_token
    if not expected:
        raise AuthError("internal connections disabled (GATEWAY_SHARED_TOKEN unset)",
                        status_code=503)
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {expected}":
        raise AuthError("forbidden", status_code=403)
    if service not in SERVICES:
        raise AuthError("unknown service", status_code=404)
    conn = _store(request).get_connection(email=email, service=service)
    if not conn:
        raise AuthError("no connection", status_code=404)
    return conn
