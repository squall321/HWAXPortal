"""Session routes: login init, IdP callback, current-user, refresh, logout.

These are IdP-independent: they delegate the only IdP-specific steps (redirect to IdP,
process the IdP response) to the active AuthProvider, then run the same session machinery
for mock and SAML alike.
"""

import secrets

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth import cookies
from app.auth.errors import AuthError
from app.auth.jwt_service import JWTService
from app.auth.provider import AuthProvider
from app.config import Settings, get_settings
from app.deps import (
    get_auth_provider,
    get_current_principal,
    get_jwt_service,
    require_csrf,
)
from app.schemas.auth import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


def _safe_return_to(raw: str | None) -> str:
    """Only allow same-site relative paths — blocks open-redirect via return_to."""
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return "/"
    return raw


def complete_login(
    *,
    principal,
    expected_state: str | None,
    settings: Settings,
    jwt_service: JWTService,
) -> RedirectResponse:
    """Issue the portal session and bounce the browser back to where it wanted to go.

    Shared by the mock callback and the SAML ACS — everything from a verified Principal
    onward is IdP-independent.
    """
    return_to = "/"
    if expected_state:
        try:
            return_to = _safe_return_to(jwt_service.verify_state(expected_state).get("return_to"))
        except jwt.PyJWTError:
            return_to = "/"

    response = RedirectResponse(f"{settings.frontend_url}{return_to}", status_code=302)
    cookies.set_session_cookies(
        response,
        settings,
        session=jwt_service.issue_session(principal),
        refresh=jwt_service.issue_refresh(principal),
    )
    cookies.set_csrf_cookie(response, settings, token=secrets.token_urlsafe(24))
    cookies.clear_state_cookie(response, settings)
    return response


@router.get("/login")
def login(
    request: Request,
    return_to: str = "/",
    settings: Settings = Depends(get_settings),
    provider: AuthProvider = Depends(get_auth_provider),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RedirectResponse:
    state = jwt_service.issue_state(return_to=_safe_return_to(return_to))
    response = provider.login_redirect(state=state)
    cookies.set_state_cookie(response, settings, token=state)
    return response


# GET(response_mode=query) + POST(response_mode=form_post) 둘 다 — 사내 IdP 는 대개 form_post
# 로 POST 콜백을 보내는데, GET 전용이면 여기서 405 Method Not Allowed 로 로그인이 깨진다.
@router.api_route("/callback", methods=["GET", "POST"])
async def callback(
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: AuthProvider = Depends(get_auth_provider),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RedirectResponse:
    expected_state = request.cookies.get(cookies.STATE_COOKIE)
    principal = await provider.handle_callback(request, expected_state=expected_state)
    return complete_login(
        principal=principal,
        expected_state=expected_state,
        settings=settings,
        jwt_service=jwt_service,
    )


@router.get("/me", response_model=UserProfile)
def me(principal=Depends(get_current_principal)) -> UserProfile:
    return UserProfile(
        subject=principal.subject,
        email=principal.email,
        display_name=principal.display_name,
        groups=principal.groups,
    )


@router.post("/refresh")
def refresh(
    request: Request,
    settings: Settings = Depends(get_settings),
    jwt_service: JWTService = Depends(get_jwt_service),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    token = request.cookies.get(cookies.REFRESH_COOKIE)
    if not token:
        raise AuthError("no refresh token", status_code=401)
    try:
        claims = jwt_service.verify_refresh(token)
    except jwt.PyJWTError as exc:
        raise AuthError("invalid or expired refresh token", status_code=401) from exc

    principal = jwt_service.principal_from_claims(claims)
    response = JSONResponse({"status": "refreshed"})
    cookies.set_session_cookie(response, settings, session=jwt_service.issue_session(principal))
    return response


@router.post("/logout")
def logout(
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_csrf),
) -> JSONResponse:
    response = JSONResponse({"status": "logged_out"})
    cookies.clear_session_cookies(response, settings)
    return response
