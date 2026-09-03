# 이메일 로컬 계정 라우트 — 가입(승인제)·로그인·비번 변경·관리자 승인. SSO 지연 브리지.
"""Local email-account routes.

로그인 성공 시 세션 발급은 SSO 콜백과 완전히 같은 기계(issue_session/refresh + 쿠키)를
탄다 — subject=이메일이라 대화·PAT·감사 소유권이 SSO 전환 후에도 그대로 이어진다.
로그인·가입은 CSRF 면제(로그인 전엔 CSRF 쿠키가 없다 — 자격증명 자체가 증명),
대신 IP rate-limit 과 계정 잠금(user_store)이 막는다. 정문이 인터넷 노출이라 필수다.
"""
import logging
import secrets
import threading
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.auth import cookies
from app.auth.errors import AuthError
from app.auth.jwt_service import JWTService
from app.auth.provider import Principal
from app.auth.user_store import UserStore
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
                           bootstrap_admins=settings.local_bootstrap_admin_list)
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
    _admin: Principal = Depends(require_role("portal-admin")),
) -> list[dict]:
    return store.list_users()


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


@router.post("/users/{email}/status")
def set_user_status(
    email: str,
    body: StatusIn,
    store: UserStore = Depends(_user_store),
    admin: Principal = Depends(require_role("portal-admin")),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    if not store.set_status(email, body.status):
        raise AuthError("not found", status_code=404)
    logger.info("local status: %s -> %s by %s", email, body.status, admin.email)
    return JSONResponse({"ok": True})


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
