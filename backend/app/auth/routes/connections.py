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
    # 저장할 워크스페이스 슬러그. 생략하면 서버가 조직 우선으로 고른다.
    # 빈 문자열("")은 '지정 안 함' 이고, 그러면 게이트웨이가 헤더를 지워 RA 가 토큰의
    # 기본 워크스페이스로 보낸다 — None(미지정)과 뜻이 다르므로 구분해서 받는다.
    workspace: str | None = Field(default=None, max_length=120)


class WorkspaceIn(BaseModel):
    """토큰은 그대로 두고 조직만 바꾼다."""

    workspace: str = Field(max_length=120)


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


async def _invalidate_gateway_cache(settings: Settings, email: str) -> None:
    """게이트웨이의 연결 캐시를 깬다 — 안 부르면 바뀐 값이 최대 5분(PORTAL_CONN_TTL_S) 안 먹는다.

    방금 조직을 바꾼 사용자의 보고서가 옛 워크스페이스로 조용히 가는 것을 막는다. 실패는
    비치명이다 — TTL 이 지나면 어차피 반영되므로, 여기서 예외를 올려 설정 변경 자체를
    실패시키지는 않는다. 대신 로그로 남겨 '왜 늦게 반영됐나' 를 나중에 추적할 수 있게 한다.
    """
    tok = settings.gateway_shared_token
    base = (getattr(settings, "mcp_gateway_url", "") or "").rstrip("/")
    if not (tok and base):
        return
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.post(f"{base}/conn-invalidate", params={"email": email},
                               headers={"Authorization": f"Bearer {tok}"})
        if r.status_code != 200:
            logger.warning("gateway conn-invalidate → HTTP %s (반영이 최대 TTL 만큼 늦어진다)",
                           r.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("gateway conn-invalidate 실패(%r) — 반영이 최대 TTL 만큼 늦어진다", exc)


def _workspace_options(me: dict) -> list[dict]:
    """고를 수 있는 워크스페이스 — 조직을 앞에, 개인을 뒤에. 화면이 그대로 그린다."""
    out: list[dict] = []
    for m in (me.get("memberships") or []):
        slug = str(m.get("workspace_slug") or "").strip()
        if not slug:
            continue
        personal = (m.get("workspace_kind") == "personal") or slug.startswith("personal-")
        out.append({"slug": slug, "name": str(m.get("workspace_name") or slug),
                    "personal": personal, "role": str(m.get("role") or "")})
    out.sort(key=lambda w: (w["personal"], w["slug"]))
    return out


def _pick_default_workspace(me: dict, options: list[dict]) -> str:
    """기본값 — **조직을 먼저** 고른다.

    예전엔 home_workspace_slug 를 그대로 썼다. 그런데 RA 계정의 home 이 personal-N 이면
    개인 워크스페이스가 박히고, 화면에 바꿀 방법이 없어 보고서가 계속 개인함에 쌓인다.
    home 이 조직이면 그것을 존중하고, 아니면 첫 조직 멤버십으로 간다.
    """
    home = str(me.get("home_workspace_slug") or "").strip()
    orgs = [w["slug"] for w in options if not w["personal"]]
    if home and home in orgs:
        return home
    if orgs:
        return orgs[0]
    return home or ""


def _validate_workspace(slug: str, options: list[dict]) -> str:
    """멤버십에 있는 슬러그만 통과. 빈 문자열은 '지정 안 함' 으로 허용한다.

    오타를 그대로 저장하면 보고서가 어디에도 안 보이는데 등록은 성공한 것처럼 끝난다 —
    실패가 성공과 똑같이 생기는 그 부류다. 여기서 막는다.
    """
    slug = (slug or "").strip()
    if not slug:
        return ""
    if slug not in {w["slug"] for w in options}:
        raise AuthError(
            f"'{slug}' 는 이 RA 계정이 속한 워크스페이스가 아닙니다. "
            + ("고를 수 있는 것: " + ", ".join(w["slug"] for w in options) if options
               else "이 계정에는 멤버십이 없습니다."),
            status_code=400)
    return slug


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
    options = _workspace_options(me)
    # 사용자가 고른 것이 있으면 그것을(검증 후), 없으면 조직 우선 기본값을.
    ws_slug = (_validate_workspace(body.workspace, options) if body.workspace is not None
               else _pick_default_workspace(me, options))
    ws_name = next((w["name"] for w in options if w["slug"] == ws_slug), "")
    store = _store(request)
    store.set_connection(email=principal.email, service="reportarchive",
                         token=token, workspace=ws_slug)
    # 부서 자동 채움 — 포털 계정에 부서가 비어 있으면 RA 의 소속 부서로.
    u = store.get(principal.email)
    dept_filled = ""
    if u is not None and not (u.get("department") or "").strip() and (ws_name or ws_slug):
        store.set_department(principal.email, ws_name or ws_slug)
        dept_filled = ws_name or ws_slug
    await _invalidate_gateway_cache(settings, principal.email)
    logger.info("connection set: reportarchive for %s (ws=%s)", principal.email, ws_slug)
    # 후보를 함께 준다 — 화면이 토큰을 다시 받지 않고 바로 조직 선택을 그릴 수 있다.
    return JSONResponse({"ok": True, "workspace": ws_slug, "workspace_name": ws_name,
                         "department_filled": dept_filled, "workspaces": options})


@router.get("/auth/connections/reportarchive/workspaces")
async def list_ra_workspaces(
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    """저장된 토큰으로 RA 에 물어 고를 수 있는 워크스페이스를 준다(토큰 재입력 없이)."""
    conn = _store(request).get_connection(email=principal.email, service="reportarchive")
    if not conn:
        raise AuthError("Report Archive 연결이 없습니다. 토큰을 먼저 등록하세요.", status_code=404)
    me = await _ra_profile(settings, conn["token"])
    return {"current": conn.get("workspace") or "", "workspaces": _workspace_options(me)}


@router.put("/auth/connections/reportarchive/workspace")
async def set_ra_workspace(
    body: WorkspaceIn,
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
) -> JSONResponse:
    """조직만 바꾼다 — 부서를 옮겼다고 PAT 를 다시 발급받게 하지 않는다."""
    store = _store(request)
    conn = store.get_connection(email=principal.email, service="reportarchive")
    if not conn:
        raise AuthError("Report Archive 연결이 없습니다. 토큰을 먼저 등록하세요.", status_code=404)
    # 멤버십은 저장된 토큰으로 **매번 다시 확인한다** — RA 쪽에서 부서가 바뀌었을 수 있고,
    # 등록 시점 목록을 믿으면 이미 나간 조직에 계속 쌓게 된다.
    options = _workspace_options(await _ra_profile(settings, conn["token"]))
    ws_slug = _validate_workspace(body.workspace, options)
    store.set_connection_workspace(email=principal.email, service="reportarchive",
                                   workspace=ws_slug)
    ws_name = next((w["name"] for w in options if w["slug"] == ws_slug), "")
    await _invalidate_gateway_cache(settings, principal.email)
    logger.info("connection workspace set: reportarchive for %s (ws=%s)",
                principal.email, ws_slug or "(지정 안 함)")
    return JSONResponse({"ok": True, "workspace": ws_slug, "workspace_name": ws_name,
                         "workspaces": options})


@router.get("/auth/connections")
def list_connections(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    store = _store(request)
    return {s: store.connection_meta(email=principal.email, service=s) for s in SERVICES}


@router.delete("/auth/connections/reportarchive")
async def delete_ra_connection(
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    _store(request).delete_connection(email=principal.email, service="reportarchive")
    # 해제도 즉시 반영해야 한다 — 안 그러면 해제한 토큰으로 최대 TTL 동안 계속 부른다.
    await _invalidate_gateway_cache(settings, principal.email)
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
