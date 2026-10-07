# 이메일 로컬 계정 라우트 — 가입(승인제)·로그인·비번 변경·관리자 승인. SSO 지연 브리지.
"""Local email-account routes.

로그인 성공 시 세션 발급은 SSO 콜백과 완전히 같은 기계(issue_session/refresh + 쿠키)를
탄다 — subject=이메일이라 대화·PAT·감사 소유권이 SSO 전환 후에도 그대로 이어진다.
로그인·가입은 CSRF 면제(로그인 전엔 CSRF 쿠키가 없다 — 자격증명 자체가 증명),
대신 IP rate-limit 과 계정 잠금(user_store)이 막는다. 정문이 인터넷 노출이라 필수다.
"""
import asyncio
import logging
import secrets
import threading
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.auth import access_log, cookies, ra_sso
from app.auth.errors import AuthError
from app.auth.jwt_service import JWTService
from app.auth.provider import Principal
from app.auth.routes import ste_credential
from app.auth.routes.connections import _invalidate_gateway_cache
from app.auth.user_store import UserStore, norm_email
from app.config import Settings, get_settings
from app.deps import get_current_principal, get_jwt_service, require_csrf, require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/local", tags=["local-auth"])

# ── IP rate-limit — 단일 인스턴스 전제(파일럿), 프로세스 메모리로 충분 ──────────
_rl_lock = threading.Lock()
_rl: dict[str, list[float]] = {}


def _rate_ok(key: str, limit: int, window_s: int) -> bool:
    now = time.monotonic()
    with _rl_lock:
        hist = [t for t in _rl.get(key, []) if now - t < window_s]
        if len(hist) >= limit:
            _rl[key] = hist
            return False
        hist.append(now)
        _rl[key] = hist
        return True


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def _user_store(request: Request) -> UserStore:
    return request.app.state.user_store


class SignupIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    department: str = Field(default="", max_length=80)  # 선택 — RA 연결 시 자동 채움도 됨


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/signup")
def signup(
    body: SignupIn,
    request: Request,
    settings: Settings = Depends(get_settings),
    store: UserStore = Depends(_user_store),
) -> JSONResponse:
    if not settings.local_auth_enabled:
        raise AuthError("local auth disabled", status_code=404)
    if not _rate_ok(f"su:{_client_ip(request)}", limit=5, window_s=3600):
        raise AuthError("too many signup attempts", status_code=429)
    try:
        res = store.signup(email=body.email, name=body.name, password=body.password,
                           bootstrap_admins=settings.local_bootstrap_admin_list,
                           department=body.department)
    except ValueError:
        # 이미 있는 이메일 — 존재 여부를 노출하지 않고 같은 응답을 준다.
        logger.info("local signup duplicate: %s", body.email)
        return JSONResponse({"status": "pending"})
    logger.info("local signup: %s status=%s ip=%s", res["email"], res["status"],
                _client_ip(request))
    return JSONResponse({"status": res["status"]})


@router.post("/login")
def login(
    body: LoginIn,
    request: Request,
    settings: Settings = Depends(get_settings),
    store: UserStore = Depends(_user_store),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> JSONResponse:
    if not settings.local_auth_enabled:
        raise AuthError("local auth disabled", status_code=404)
    if not _rate_ok(f"li:{_client_ip(request)}", limit=10, window_s=60):
        raise AuthError("too many login attempts", status_code=429)
    try:
        u = store.verify_login(email=body.email, password=body.password)
    except ValueError as exc:
        logger.info("local login fail: %s (%s) ip=%s", body.email, exc, _client_ip(request))
        # 실패도 원장에 — 누가 어디서 두드렸나. 이메일은 **시도한** 값이다(주장일 뿐, docs/access-history).
        access_log.note(request, email=str(body.email), event="login_fail", service="portal",
                        detail=f"local:{exc}")
        msg = ("account locked, retry later" if str(exc) == "locked"
               else "pending approval" if str(exc) == "not active"
               else "invalid email or password")
        raise AuthError(msg, status_code=401) from exc
    principal = Principal(
        subject=u["email"], email=u["email"], display_name=u["name"],
        groups=u["groups"], attributes={"provider": ["local"]})
    response = JSONResponse({"ok": True})
    cookies.set_session_cookies(
        response, settings,
        session=jwt_service.issue_session(principal),
        refresh=jwt_service.issue_refresh(principal))
    cookies.set_csrf_cookie(response, settings, token=secrets.token_urlsafe(24))
    # 로그인 연결 ID — nginx 가 정문 요청마다 적어 계정과 잇는다(docs/access-history D-5).
    uid = access_log.new_uid()
    cookies.set_uid_cookie(response, settings, uid=uid)
    access_log.note(request, email=u["email"], event="login", service="portal", detail="local", uid=uid)
    logger.info("local login ok: %s ip=%s", u["email"], _client_ip(request))
    return response


@router.post("/change-password")
def change_password(
    body: PasswordChangeIn,
    store: UserStore = Depends(_user_store),
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    try:
        store.verify_login(email=principal.email, password=body.current_password)
    except ValueError as exc:
        raise AuthError("current password incorrect", status_code=403) from exc
    store.set_password(principal.email, body.new_password)
    return JSONResponse({"ok": True})


# ── 관리자 ──────────────────────────────────────────────────────────────────
class ApproveIn(BaseModel):
    groups: list[str] | None = None  # 승인과 동시에 역할 지정(생략하면 무역할)


class ResetIn(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


@router.get("/users")
def list_users(
    store: UserStore = Depends(_user_store),
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role("portal-admin")),
) -> list[dict]:
    # 고정 관리자(PORTAL_ADMIN_EMAILS)는 원장 groups 에 안 보인다 — 따로 알려 주지 않으면 화면이 그 사람을 일반 사용자로 그리고,
    # 눌러도 해제되지 않는 스위치를 내놓는다. 원장 행의 이메일과 글자 그대로 견준다(권한 계산과 같은 규칙).
    pinned = settings.portal_admin_email_set
    return [{**u, "admin_pinned": u["email"] in pinned} for u in store.list_users()]


@router.post("/users/{email}/approve")
def approve_user(
    email: str,
    body: ApproveIn,
    store: UserStore = Depends(_user_store),
    admin: Principal = Depends(require_role("portal-admin")),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    if not store.approve(email, by=admin.email, groups=body.groups):
        raise AuthError("not found or not pending", status_code=404)
    logger.info("local approve: %s by %s", email, admin.email)
    return JSONResponse({"ok": True})


async def _revoke_app_credentials(settings: Settings, email: str) -> dict[str, str]:
    """정지된 사람의 **앱 쪽 자격**을 회수한다(8차 요청 §7). 정지가 포털 PAT 만 폐기하던 때는 이 셋이 만료까지 남았다.
      · ste — 그 사람이 포털을 거쳐 받은 ste 토큰(12시간). ste 원장에서 죽인다.
      · reportarchive — 포털이 메모리에 든 그 사람의 RA 위임 토큰(최대 11시간). RA 가 회수 엔드포인트를 내주면 여기에 더한다.
      · gateway — 게이트웨이가 든 그 사람 명의 토큰과 연결·응답·권한 캐시.

    **best-effort 다.** 셋을 따로 시도하고 하나가 실패해도(던져도) 나머지는 간다. 부르는 쪽은 정지를 원장에 적은 **뒤에** 이것을
    부른다 — 여기서 무엇이 실패하든 매달리든 정지는 이미 걸려 있고, 포털·게이트웨이의 새 호출은 권한 0 으로 막힌다. 회수는
    그 위에 남은 토큰의 수명을 줄이는 일이다.
    돌려주는 것: 앱 → "ok" | "failed" | "off"(그 연동이 이 박스에 꺼져 있어 부르지 않았다). 실패는 WARNING 으로 남긴다 —
    포털은 INFO 를 버리고, 회수 실패가 흔적 없이 지나가면 '정지했으니 끊겼다' 고 믿게 된다. 꺼진 것은 실패로 적지 않는다.
    """
    async def ste() -> bool | None:
        return await ste_credential.revoke_for(settings, email)

    async def reportarchive() -> bool | None:
        ra_sso.forget(email)
        return True

    async def gateway() -> bool | None:
        return await _invalidate_gateway_cache(settings, email)

    steps = (ste, reportarchive, gateway)
    # 동시에 — ste 는 SSH 터널 뒤라 응답이 늦을 수 있다(TIMEOUT_S). 차례로 부르면 그만큼 관리자의 화면이 매달린다.
    results = await asyncio.gather(*(step() for step in steps), return_exceptions=True)
    out: dict[str, str] = {}
    for step, got in zip(steps, results, strict=True):
        name = step.__name__
        if got is None:
            out[name] = "off"
        elif got is True:
            out[name] = "ok"
        else:
            out[name] = "failed"
            why = type(got).__name__ if isinstance(got, BaseException) else "닿지 못했거나 거절됐다"
            logger.warning("정지 %s — %s 쪽 자격 회수 실패(%s). 정지는 적용됐다 — 그 앱이 이미 내준 토큰은 만료까지 남을 수 있다",
                           email, name, why)
    return out


@router.post("/users/{email}/status")
async def set_user_status(
    request: Request,
    email: str,
    body: StatusIn,
    store: UserStore = Depends(_user_store),
    settings: Settings = Depends(get_settings),
    admin: Principal = Depends(require_role("portal-admin")),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    if body.status == "disabled":
        # 본인과 마지막 관리자의 정지는 거절한다 — 관리자 해제(access/routes._set_admin)가 막는 것과 같은 구멍의 다른 문이다.
        # 정지된 관리자는 권한이 0 이라, 실수 한 번으로 관리자 화면을 열 사람이 없어지면 되돌리는 길이 박스의 셸뿐이다.
        # 종전엔 화면이 본인 줄의 버튼을 숨길 뿐 이 라우트는 그대로 받았다.
        if norm_email(email) == norm_email(admin.email or ""):
            raise AuthError("자기 자신은 정지할 수 없습니다 — 다른 관리자에게 요청하세요", status_code=409)
        got = store.suspend(email, pinned=settings.portal_admin_email_set)
        if got == "missing":
            raise AuthError("not found", status_code=404)
        if got == "last":
            raise AuthError("마지막 관리자는 정지할 수 없습니다 — 먼저 다른 활성 사용자를 관리자로 지정하세요", status_code=409)
    elif not store.set_status(email, body.status):
        raise AuthError("not found", status_code=404)
    # ⚠ **정지는 토큰까지 죽인다.** 권한 계산만 막으면(`compute` 가 0개) 서명 자체는
    # 여전히 유효해서, 자격을 안 보는 경로가 생기는 순간 다시 뚫린다. 무기한 PAT 은
    # 만료로 안 죽고 폐기로만 죽는다 — 정지가 절반만 듣던 자리다(7차 감사).
    revoked = 0
    apps: dict[str, str] = {}
    if body.status == "disabled":
        ts = getattr(request.app.state, "token_store", None)
        if ts is not None:
            revoked = ts.revoke_all_for(email)
        # 포털 밖에 나가 있는 자격도 거둔다 — 원장의 정지와 PAT 폐기가 **끝난 뒤**다(순서가 뒤집히면 앱 호출이 매달린 동안
        # 그 사람이 정지되지 않은 채 남는다).
        apps = await _revoke_app_credentials(settings, norm_email(email))
    logger.info("local status: %s -> %s by %s (PAT %d개 폐기)",
                email, body.status, admin.email, revoked)
    return JSONResponse({"ok": True, "pats_revoked": revoked, "app_revocations": apps})


@router.post("/users/{email}/reset-password")
def reset_password(
    email: str,
    body: ResetIn,
    store: UserStore = Depends(_user_store),
    admin: Principal = Depends(require_role("portal-admin")),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    if not store.set_password(email, body.new_password):
        raise AuthError("not found", status_code=404)
    logger.info("local pw reset: %s by %s", email, admin.email)
    return JSONResponse({"ok": True})
