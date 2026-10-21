# 외부 서비스 연결 토큰 — 사용자가 RA 등에서 발급받은 PAT 를 등록하면 게이트웨이가
# 그 사람 자격증명으로 해당 서비스를 부른다(SSO 전 브리지, 사용자 발안 2026-09-03).
"""Service connection tokens.

흐름: 사용자가 Report Archive 에서 PAT(rat_…)를 발급 → 포털 API 토큰 페이지에 붙여넣기 →
포털이 RA /api/users/me 로 검증(이메일 일치 강제)하고 부서(home_workspace_slug)까지 얻어
저장 → 게이트웨이가 RA 호출 시 /internal/connections 로 조회해 그 토큰+부서 헤더로 호출.
SSO 가 연동되면 RA 쪽 자동 계정 등록으로 대체될 브리지다 — 그날 이 등록부는 자연 소멸.

TestScope(다른 조직 포털)도 같은 등록부를 쓴다 — 그쪽 개인 토큰(tsc_pat_…)을 TestScope /api/auth/me 로
확인(이메일 일치 강제)해 저장한다. 조직(워크스페이스) 개념은 없다(docs/sso-delegation).
"""
import hmac
import logging
import re

import httpx
import jwt
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.access.policy import BUILTIN_TOKEN_PREFIXES, ConnectSpec
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["connections"])

SERVICES = ("reportarchive", "testscope")
# 내장 연결 — 주인 확인 · 부서가 있는 RA · TestScope. 아래 외부 연결(ext) 길은 이 둘을 받지 않는다(설정으로 확인 없는 길로 옮기지 못하게).
BUILTIN = frozenset(SERVICES)


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


async def _invalidate_gateway_cache(settings: Settings, email: str) -> bool | None:
    """게이트웨이의 연결 캐시를 깬다 — 안 부르면 바뀐 값이 최대 5분(PORTAL_CONN_TTL_S) 안 먹는다.

    방금 조직을 바꾼 사용자의 보고서가 옛 워크스페이스로 조용히 가는 것을 막는다. 실패는
    비치명이다 — TTL 이 지나면 어차피 반영되므로, 여기서 예외를 올려 설정 변경 자체를
    실패시키지는 않는다. 대신 로그로 남겨 '왜 늦게 반영됐나' 를 나중에 추적할 수 있게 한다.

    게이트웨이는 이 호출에서 그 사람의 연결·응답·권한 캐시와 **그 사람 명의로 받아 둔 토큰**(ste·RA 등)을 함께 비운다 —
    계정 정지가 이것을 부르는 이유다(auth/routes/local.py). 돌려주는 것: True(비웠다) · False(닿지 못했거나 거절) ·
    None(공유 시크릿·주소가 없어 부르지 않았다). 종전 호출부는 값을 보지 않는다.
    """
    tok = settings.gateway_shared_token
    base = (getattr(settings, "mcp_gateway_url", "") or "").rstrip("/")
    if not (tok and base):
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.post(f"{base}/conn-invalidate", params={"email": email},
                               headers={"Authorization": f"Bearer {tok}"})
        if r.status_code != 200:
            logger.warning("gateway conn-invalidate → HTTP %s (반영이 최대 TTL 만큼 늦어진다)",
                           r.status_code)
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("gateway conn-invalidate 실패(%r) — 반영이 최대 TTL 만큼 늦어진다", exc)
        return False


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
    # ⚠ **확인 못 한 것을 확인한 것으로 치지 않는다.** 예전엔 `if ra_email and …` 라서
    # RA 가 이메일을 안 주면 검사가 **통째로 사라졌다**(fail-open). 신원 결속에서
    # "모르겠다" 는 "맞다" 가 아니다. RA 스키마상 `email` 은 필수라 닫아도 안 깨진다
    # (`UserRead.email: str` — 2026-09-15 확인).
    if not ra_email:
        raise AuthError(
            "RA 가 계정 이메일을 주지 않아 이 토큰이 누구 것인지 확인할 수 없습니다 — "
            "등록하지 않습니다. RA 쪽 응답 모양이 바뀌었을 수 있습니다.", status_code=502)
    if ra_email != principal.email.lower():
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
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    store = _store(request)
    out: dict = {s: store.connection_meta(email=principal.email, service=s) for s in SERVICES}
    # 화면이 RA 카드를 가른다 — "sso" 면 포털 로그인으로 본인 명의(등록할 것 없음), "token" 이면 종전 토큰 등록
    # (docs/sso-delegation). 값은 비밀의 있고 없음뿐이다.
    out["reportarchive_mode"] = "sso" if settings.ra_sso_secret else "token"
    # TestScope 가 없는 박스에서는 화면이 카드를 안 그린다 — 주소의 있고 없음만 준다.
    out["testscope_enabled"] = bool((settings.testscope_base_url or "").strip())
    # TestScope 도 RA 와 같은 두 갈래다 — "sso" 면 게이트웨이가 그 사람 토큰을 받는다(등록할 것 없음), "token" 이면 토큰 등록.
    # 등록·해제(PUT/DELETE)는 어느 갈래든 열어 둔다 — 위임으로 넘어간 뒤에도 옛 토큰을 지울 수 있어야 한다.
    out["testscope_mode"] = "sso" if settings.testscope_sso_secret else "token"
    return out


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


# ── TestScope — 다른 조직 포털, RA 와 같은 '토큰 등록' ──────────────────────────
async def _testscope_owner(settings: Settings, token: str) -> str:
    """TestScope 토큰의 주인 이메일(소문자) — 실패는 AuthError(사용자에게 보여줄 문구)로 승격."""
    base = (settings.testscope_base_url or "").strip().rstrip("/")
    if not base:
        raise AuthError("TestScope 연결이 이 박스에 설정돼 있지 않습니다.", status_code=404)
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            resp = await cli.get(base + "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        raise AuthError(f"TestScope 에 연결하지 못했습니다({exc.__class__.__name__}). "
                        "서비스가 떠 있는지 확인하세요.", status_code=502) from exc
    if resp.status_code == 401:
        raise AuthError("TestScope 가 이 토큰을 거부했습니다 — 만료·폐기됐거나 잘못 복사된 토큰입니다.",
                        status_code=400)
    if resp.status_code == 403:
        # 본인 확인(/api/auth/me)에 'read' 범위가 필요하다 — 쓰기 범위만 준 토큰이 여기서 걸린다.
        raise AuthError("TestScope 가 이 토큰으로 본인 확인을 거부했습니다 — 토큰에 'read' 범위가 있어야 합니다. "
                        "TestScope 에서 'read' 를 포함해 다시 발급하세요.", status_code=400)
    if resp.status_code != 200:
        raise AuthError(f"TestScope 검증 실패(HTTP {resp.status_code}).", status_code=400)
    # 봉투 없는 맨 모델 {id, email, …}. 200 인데 JSON 이 아니면(주소가 엉뚱한 SPA 등) 이메일 없음과 같게 닫는다.
    try:
        me = resp.json()
    except ValueError:
        me = None
    return str((me if isinstance(me, dict) else {}).get("email") or "").strip().lower()


@router.put("/auth/connections/testscope")
async def set_testscope_connection(
    body: ConnectionIn,
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
) -> JSONResponse:
    token = body.token.strip()
    ts_email = await _testscope_owner(settings, token)
    # 확인 못 한 것을 확인한 것으로 치지 않는다(RA 와 같은 fail-closed) — 남의 토큰이면 그 사람 명의로 쓰인다.
    if not ts_email:
        raise AuthError(
            "TestScope 가 계정 이메일을 주지 않아 이 토큰이 누구 것인지 확인할 수 없습니다 — "
            "등록하지 않습니다. TestScope 쪽 응답 모양이 바뀌었거나 주소가 틀렸을 수 있습니다.", status_code=502)
    if ts_email != principal.email.lower():
        raise AuthError(
            f"TestScope 계정 이메일({ts_email})이 포털 계정({principal.email})과 다릅니다. "
            "같은 이메일의 TestScope 계정에서 발급한 토큰을 등록하세요.", status_code=400)
    _store(request).set_connection(email=principal.email, service="testscope", token=token, workspace="")
    await _invalidate_gateway_cache(settings, principal.email)
    logger.info("connection set: testscope for %s", principal.email)
    return JSONResponse({"ok": True})


@router.delete("/auth/connections/testscope")
async def delete_testscope_connection(
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(principal_pat_or_session),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    _store(request).delete_connection(email=principal.email, service="testscope")
    await _invalidate_gateway_cache(settings, principal.email)
    return JSONResponse({"ok": True})


# ── 외부 연결 — 박스 권한표의 connect: 선언으로 붙는 플랫폼(docs/ext-connect) ─────────────────────
# 위 RA · TestScope 는 그대로다. 아래는 플랫폼 이름을 모르는 일반 길이다 — 선언이 카드 문구 · 토큰 접두 · 확인 방법을 정하고, 새 플랫폼은
# 박스 파일 한 곳으로 붙는다(빌드 · 코드 · 재기동 없음). 새 플랫폼은 토큰 주인을 확인하지 않는다(사용자 결정 10-21) — 대신 등록은 브라우저
# 세션 + CSRF 만 받고(PAT 를 훔친 사람이 남의 행에 제 토큰을 넣지 못하게), 포털 JWT · 다른 서비스 접두를 네트워크를 쓰기 전에 거른다.
_SERVICE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
_TOKEN = re.compile(r"^[\x21-\x7e]{8,512}$")
_WORKSPACE = re.compile(r"^[A-Za-z0-9._:-]{0,120}$")
_BEARER = re.compile(r"^bearer\s+", re.I)
_MCP_INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "hwax-portal-verify", "version": "1"}}}


def _registry(request: Request) -> dict[str, ConnectSpec]:
    """지금 정책의 외부 연결 선언 — 백엔드 키(= service) → 선언. 정책 객체는 요청마다 mtime 을 본다(재기동 없이 반영)."""
    access = getattr(request.app.state, "access", None)
    return access.get().connections() if access is not None else {}


def _hidden_keys(request: Request) -> set[str]:
    """이 박스에서 권한 요청을 받지 않는 플랫폼 키 — 권한 화면과 같은 셈(access/routes._hidden)."""
    access = getattr(request.app.state, "access", None)
    catalog = getattr(request.app.state, "catalog", None)
    if access is None or catalog is None:
        return set()
    return access.get().hidden_keys(catalog.live_ids())


@router.get("/auth/connections/ext")
def list_ext_connections(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    """외부 연결 카드 — 선언마다 문구 · 내 권한 · 등록 상태, 그리고 더는 선언이 없는 내 토큰(고아). 주소 · 확인 주소 · 목록 자격은 내지 않는다."""
    store = _store(request)
    reg = _registry(request)
    hidden = _hidden_keys(request)
    have = set(principal.groups)
    platforms = [{"service": k, "label": c.label, "token_hint": c.token_hint, "issue": c.issue, "issue_url": c.issue_url,
                  "note": c.note, "verify": c.verify, "workspace_label": c.workspace_label,
                  "entitled": c.need in have, "need": c.need, "requestable": c.need not in hidden,
                  "connected": store.connection_meta(email=principal.email, service=k)}
                 for k, c in sorted(reg.items(), key=lambda kv: (kv[1].label, kv[0]))]
    orphans = []
    for svc in store.connection_services(principal.email):
        if svc in BUILTIN or svc in reg:
            continue
        meta = store.connection_meta(email=principal.email, service=svc) or {}
        orphans.append({"service": svc, "tail": meta.get("tail") or "", "created_at": meta.get("created_at")})
    return {"platforms": platforms, "orphans": orphans}


class ExtConnectionIn(BaseModel):
    # 'Bearer ' 를 붙여 넣어도 받는다 — 꼴은 그것을 뗀 뒤에 본다(FMEA 화면이 'Bearer fmea_…' 로 보여 준다).
    token: str = Field(min_length=1, max_length=600)
    workspace: str | None = Field(default=None, max_length=120)


def _portal_jwt(token: str, issuer: str) -> bool:
    """HWAX 포털이 낸 JWT(PAT · 세션)인가 — 서명은 보지 않고 iss 만 본다. 포털 PAT 는 접두가 없어 접두 검사로는 못 거른다."""
    if token.count(".") != 2:
        return False
    try:
        claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": False, "verify_aud": False})
    except jwt.PyJWTError:
        return False
    return isinstance(claims, dict) and claims.get("iss") == issuer


def _foreign_prefix(spec: ConnectSpec, token: str, reg: dict[str, ConnectSpec]) -> str:
    """토큰이 다른 서비스의 접두로 시작하면 그 접두. 자기 접두의 앞부분인 접두는 보지 않는다(mnx_pat_ 플랫폼에 mnx_ 플랫폼이 있어도)."""
    others = {c.token_prefix for k, c in reg.items() if k != spec.backend and c.token_prefix} | set(BUILTIN_TOKEN_PREFIXES)
    if spec.token_prefix:
        others = {p for p in others if not spec.token_prefix.startswith(p)}
    return next((p for p in sorted(others, key=len, reverse=True) if token.startswith(p)), "")


async def _verify_ext(spec: ConnectSpec, token: str, email: str) -> None:
    """선언의 verify 대로 토큰의 **유효성**만 본다(none · mcp · url). owner_field 가 있으면 주인도 본다(fail-closed — TestScope 와 같다).
    사람 토큰이 사내 프록시를 지나지 않게 env 프록시를 따르지 않는다(trust_env=False). 응답 본문은 돌려주지 않는다."""
    if spec.verify == "none":
        return
    auth = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=8, trust_env=False) as cli:
            if spec.verify == "mcp":
                resp = await cli.post(spec.mcp_url, json=_MCP_INIT,
                                      headers={**auth, "Accept": "application/json, text/event-stream"})
                sid = resp.headers.get("mcp-session-id")
                if resp.status_code == 200 and sid:
                    try:   # 확인용 세션을 닫는다 — 실패해도 확인 결과는 그대로다
                        await cli.delete(spec.mcp_url, headers={**auth, "Mcp-Session-Id": sid})
                    except httpx.HTTPError:
                        pass
            else:
                resp = await cli.get(spec.verify_url, headers=auth)
    except httpx.HTTPError as exc:
        raise AuthError(f"{spec.label} 에 연결하지 못했습니다({exc.__class__.__name__}). 서비스가 떠 있는지 확인하세요.",
                        status_code=502) from exc
    if resp.status_code in (401, 403):
        raise AuthError(f"{spec.label} 가 이 토큰을 거부했습니다 — 만료 · 폐기됐거나 잘못 복사된 토큰입니다.", status_code=400)
    if resp.status_code != 200:
        raise AuthError(f"{spec.label} 확인 실패(HTTP {resp.status_code}).", status_code=400)
    if not spec.owner_field:
        return
    # 맨 모델이든 {data: …} 봉투든 그 칸의 이메일 — '모르겠다' 는 '맞다' 가 아니다(RA · TestScope 와 같은 fail-closed).
    try:
        me = resp.json()
    except ValueError:
        me = None
    me = me if isinstance(me, dict) else {}
    data = me.get("data") if isinstance(me.get("data"), dict) else {}
    owner = str(me.get(spec.owner_field) or data.get(spec.owner_field) or "").strip().lower()
    if not owner:
        raise AuthError(f"{spec.label} 가 계정 이메일({spec.owner_field})을 주지 않아 이 토큰이 누구 것인지 확인할 수 없습니다 — "
                        "등록하지 않습니다.", status_code=502)
    if owner != email.strip().lower():
        raise AuthError(f"{spec.label} 계정 이메일({owner})이 포털 계정({email})과 다릅니다. 같은 이메일의 {spec.label} 계정에서 "
                        "발급한 토큰을 등록하세요.", status_code=400)


@router.put("/auth/connections/ext/{service}")
async def set_ext_connection(
    service: str,
    body: ExtConnectionIn,
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    """외부 연결 토큰 등록 — 브라우저 세션 + CSRF 만(PAT 거절). ⓪~⑥ 은 네트워크를 쓰지 않는다(docs/ext-connect PB8)."""
    token = _BEARER.sub("", body.token.strip(), count=1)                             # ⓪
    reg = _registry(request)
    spec = None if (service in BUILTIN or not _SERVICE.fullmatch(service)) else reg.get(service)
    if spec is None:                                                                # ①
        raise AuthError("모르는 외부 연결입니다.", status_code=404)
    ensure(principal, spec.need)                                                    # ②
    if not _TOKEN.fullmatch(token):                                                 # ③
        raise AuthError("토큰 꼴이 아닙니다 — 공백 · 줄바꿈 없이 8~512자를 그대로 붙여 넣으세요.", status_code=400)
    if _portal_jwt(token, settings.jwt_issuer):                                     # ④
        raise AuthError(f"HWAX 포털 토큰입니다 — {spec.label} 에서 발급한 토큰을 붙여 넣으세요(포털 토큰은 다른 서버로 보내지 않습니다).",
                        status_code=400)
    if spec.token_prefix and not token.startswith(spec.token_prefix):               # ⑤
        raise AuthError(f"{spec.label} 토큰은 {spec.token_prefix} 로 시작합니다 — 다른 서비스의 토큰이 아닌지 확인하세요.",
                        status_code=400)
    other = _foreign_prefix(spec, token, reg)
    if other:
        raise AuthError(f"{other} 로 시작하는 토큰은 다른 서비스의 것입니다 — {spec.label} 에서 발급한 토큰을 붙여 넣으세요.",
                        status_code=400)
    workspace = (body.workspace or "").strip()                                      # ⑥
    if workspace and not spec.workspace_header:
        raise AuthError(f"{spec.label} 연결은 워크스페이스 칸을 받지 않습니다.", status_code=400)
    if not _WORKSPACE.fullmatch(workspace):
        raise AuthError("워크스페이스 값은 영문 · 숫자 · . _ : - 로 120자 이하입니다.", status_code=400)
    await _verify_ext(spec, token, principal.email)                                 # ⑦
    _store(request).set_connection(email=principal.email, service=service, token=token, workspace=workspace)   # ⑧
    await _invalidate_gateway_cache(settings, principal.email)                      # ⑨
    logger.info("connection set: %s for %s (verify=%s, owner %s)", service, principal.email, spec.verify,  # ⑩ 토큰은 남기지 않는다
                "verified" if spec.owner_field else "not verified")
    return JSONResponse({"ok": True, "verify": spec.verify})


@router.delete("/auth/connections/ext/{service}")
async def delete_ext_connection(
    service: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    """외부 연결 토큰 해제 — 권한을 잃었거나 선언이 사라진(고아) 행도 지운다. 내장 RA · TestScope 는 제 주소로만 지운다."""
    if service in BUILTIN or not _SERVICE.fullmatch(service):
        raise AuthError("모르는 외부 연결입니다.", status_code=404)
    if not _store(request).delete_connection(email=principal.email, service=service):
        raise AuthError("등록된 토큰이 없습니다.", status_code=404)
    await _invalidate_gateway_cache(settings, principal.email)
    logger.info("connection deleted: %s for %s", service, principal.email)
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
    # 공유 시크릿은 **상수 시간**으로 본다(access/routes.py 와 같은 이유).
    if not hmac.compare_digest(auth, f"Bearer {expected}"):
        raise AuthError("forbidden", status_code=403)
    # 외부 연결 선언 키도 받는다(docs/ext-connect PB10) — 선언이 사라지면 404 라 게이트웨이가 호출을 거절한다.
    if service not in SERVICES and service not in _registry(request):
        raise AuthError("unknown service", status_code=404)
    conn = _store(request).get_connection(email=email, service=service)
    if not conn:
        raise AuthError("no connection", status_code=404)
    return conn
