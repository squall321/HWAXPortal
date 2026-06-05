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
