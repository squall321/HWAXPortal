"""Shared FastAPI dependencies: provider/service access, current user, CSRF guard."""

import secrets

import jwt
from fastapi import Depends, Request

from app.auth.cookies import CSRF_COOKIE, SESSION_COOKIE
from app.auth.errors import AuthError
from app.auth.factory import build_auth_provider
from app.auth.jwt_service import JWTService
from app.auth.provider import AuthProvider, Principal
from app.config import Settings, get_settings


def get_auth_provider(request: Request) -> AuthProvider:
    return request.app.state.auth_provider


def get_jwt_service(request: Request) -> JWTService:
    return request.app.state.jwt_service


def get_catalog(request: Request):
    return request.app.state.catalog


def build_services(settings: Settings) -> tuple[AuthProvider, JWTService]:
    """Constructed once at startup and stashed on app.state."""
    return build_auth_provider(settings), JWTService(settings)


def get_current_principal(
    request: Request,
    jwt_service: JWTService = Depends(get_jwt_service),
) -> Principal:
    """Resolve the logged-in user from the httpOnly session cookie. 401 if absent/invalid."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AuthError("not authenticated", status_code=401)
    try:
        claims = jwt_service.verify_session(token)
    except jwt.PyJWTError as exc:
        raise AuthError("invalid or expired session", status_code=401) from exc
    return jwt_service.principal_from_claims(claims)


def require_role(role: str):
    """Dependency factory: 403 unless the current user has `role` among their groups."""

    def _check(principal: Principal = Depends(get_current_principal)) -> Principal:
        if role not in principal.groups:
            raise AuthError(f"requires role: {role}", status_code=403)
        return principal

    return _check


def require_csrf(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Double-submit CSRF check for state-changing (POST) routes.

    The SPA reads the non-httpOnly hwax_csrf cookie and echoes it in X-CSRF-Token.
    An attacker's cross-site POST can send the cookie but cannot read it to set the header.
    """
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("X-CSRF-Token")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise AuthError("CSRF token missing or mismatched", status_code=403)


def principal_pat_or_session(
    request: Request,
    settings: Settings = Depends(get_settings),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> Principal:
    """Chat/MCP auth: accept a Bearer PAT (aud=pat_chat_audience) OR the browser session cookie.

    A PAT lets scripts / a personal Claude drive the LLM+tools with one long-lived token; it is
    verified locally against the keystore (scope=api, aud, unexpired, not revoked) and does NOT
    need CSRF (it rides the Authorization header, not a cookie). The cookie path keeps CSRF.
    """
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() == "bearer ":
        from app.auth.pat_verify import verify_pat
        try:
            return verify_pat(
                auth[7:].strip(),
                keystore=request.app.state.keystore,
                revoked_jtis=request.app.state.token_store.revoked_jtis(),
                audience=settings.pat_chat_audience,
            )
        except Exception as exc:  # noqa: BLE001 — any verify failure is a 401
            raise AuthError("invalid or expired PAT", status_code=401) from exc
    principal = get_current_principal(request, jwt_service)
    require_csrf(request, settings)
    return principal
