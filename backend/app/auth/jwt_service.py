"""Portal session tokens (HS256, portal-internal verification).

These are the PORTAL's own session credentials — only the portal verifies them, so a
symmetric key (SESSION_SECRET) is correct and keeps Phase 1 free of key management.
Downstream launch tokens (Phase 4) are a SEPARATE mechanism: RS256, verified by external
systems via JWKS. Do not conflate the two.

Token kinds (the `typ` claim):
  - "session": short-lived access token (cookie: hwax_session)
  - "refresh": longer-lived, mints new access tokens (cookie: hwax_refresh)
  - "state":   binds a login attempt across the IdP round-trip (cookie: hwax_authstate)
"""

import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.auth.provider import Principal
from app.config import Settings

ALGO = "HS256"
SESSION_AUDIENCE = "hwax-portal"


def _now() -> datetime:
    return datetime.now(tz=UTC)


class JWTService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.session_secret
        self._issuer = settings.jwt_issuer
        self._session_ttl = settings.jwt_session_ttl
        self._refresh_ttl = settings.jwt_refresh_ttl
        self._state_ttl = settings.jwt_state_ttl

    # ── encode/decode core ──────────────────────────────────────────────────
    def _encode(self, claims: dict, *, ttl: int, typ: str) -> str:
        now = _now()
        payload = {
            **claims,
            "iss": self._issuer,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=ttl),
            "typ": typ,
            "jti": secrets.token_urlsafe(12),
        }
        return jwt.encode(payload, self._secret, algorithm=ALGO)

    def _decode(self, token: str, *, typ: str, audience: str | None = None) -> dict:
        claims = jwt.decode(
            token,
            self._secret,
            algorithms=[ALGO],  # pin: never trust the token header's alg
            audience=audience,
            issuer=self._issuer,
            options={"require": ["exp", "iat", "iss", "typ"]},
        )
        if claims.get("typ") != typ:
            raise jwt.InvalidTokenError(f"expected typ={typ}, got {claims.get('typ')}")
        return claims

    # ── session (access) ────────────────────────────────────────────────────
    def issue_session(self, principal: Principal) -> str:
        return self._encode(
            {
                "sub": principal.subject,
                "aud": SESSION_AUDIENCE,
                "email": principal.email,
                "name": principal.display_name,
                "groups": principal.groups,
            },
            ttl=self._session_ttl,
            typ="session",
        )

    def verify_session(self, token: str) -> dict:
        return self._decode(token, typ="session", audience=SESSION_AUDIENCE)

    # ── refresh ───────────────────────────────────────────────────────────────
    def issue_refresh(self, principal: Principal) -> str:
        # Carries enough identity to re-mint a session without another IdP round-trip.
        return self._encode(
            {
                "sub": principal.subject,
                "aud": SESSION_AUDIENCE,
                "email": principal.email,
                "name": principal.display_name,
                "groups": principal.groups,
            },
            ttl=self._refresh_ttl,
            typ="refresh",
        )

    def verify_refresh(self, token: str) -> dict:
        return self._decode(token, typ="refresh", audience=SESSION_AUDIENCE)

    def principal_from_claims(self, claims: dict) -> Principal:
        return Principal(
            subject=claims["sub"],
            email=claims.get("email", ""),
            display_name=claims.get("name"),
            groups=claims.get("groups", []),
        )

    # ── login-flow state (CSRF/replay binding across the IdP round-trip) ──────
    def issue_state(self, *, return_to: str) -> str:
        return self._encode({"return_to": return_to}, ttl=self._state_ttl, typ="state")

    def verify_state(self, token: str) -> dict:
        return self._decode(token, typ="state")
