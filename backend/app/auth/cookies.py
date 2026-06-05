"""Centralized cookie names + flags. One place so security flags can't drift.

Cookies are host-only (no Domain attribute) so they work through the Vite dev proxy
(localhost:5283) AND on the real domain in prod without change.
"""

from fastapi import Response

from app.config import Settings

SESSION_COOKIE = "hwax_session"  # httpOnly access token
REFRESH_COOKIE = "hwax_refresh"  # httpOnly refresh token (scoped to /auth)
CSRF_COOKIE = "hwax_csrf"        # readable by JS for double-submit CSRF
STATE_COOKIE = "hwax_authstate"  # httpOnly login-flow binding (scoped to /auth)

_REFRESH_PATH = "/auth"
_STATE_PATH = "/auth"


def _base(settings: Settings) -> dict:
    return {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }


def set_session_cookies(
    response: Response, settings: Settings, *, session: str, refresh: str
) -> None:
    response.set_cookie(
        SESSION_COOKIE, session, httponly=True, path="/",
        max_age=settings.jwt_session_ttl, **_base(settings),
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh, httponly=True, path=_REFRESH_PATH,
        max_age=settings.jwt_refresh_ttl, **_base(settings),
    )


def set_session_cookie(response: Response, settings: Settings, *, session: str) -> None:
    """Refresh path: replace only the access token."""
    response.set_cookie(
        SESSION_COOKIE, session, httponly=True, path="/",
        max_age=settings.jwt_session_ttl, **_base(settings),
    )


def set_csrf_cookie(response: Response, settings: Settings, *, token: str) -> None:
    # NOT httpOnly: the SPA reads it and echoes it in the X-CSRF-Token header (double-submit).
    # Lives as long as the refresh window so /auth/refresh still passes CSRF after the
    # access token expires.
    response.set_cookie(
        CSRF_COOKIE, token, httponly=False, path="/",
        max_age=settings.jwt_refresh_ttl, **_base(settings),
    )


def set_state_cookie(response: Response, settings: Settings, *, token: str) -> None:
    # The state cookie must survive the IdP's cross-site POST back to the ACS. With a real
    # external IdP (prod, https) that requires SameSite=None + Secure. In dev the mock IdP
    # is same-origin, so the normal (lax) policy is fine — and None without Secure (http)
    # would be rejected by browsers anyway.
    samesite = "none" if settings.cookie_secure else settings.cookie_samesite
    response.set_cookie(
        STATE_COOKIE, token, httponly=True, path=_STATE_PATH,
        max_age=settings.jwt_state_ttl, secure=settings.cookie_secure, samesite=samesite,
    )


def clear_state_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(STATE_COOKIE, path=_STATE_PATH, **_base(settings))


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", **_base(settings))
    response.delete_cookie(REFRESH_COOKIE, path=_REFRESH_PATH, **_base(settings))
    response.delete_cookie(CSRF_COOKIE, path="/", **_base(settings))
