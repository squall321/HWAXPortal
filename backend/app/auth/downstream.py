"""Downstream identity propagation.

`DownstreamTokenIssuer` is the seam for how identity reaches a linked system. The JWT
implementation (now) mints a short-lived, audience-scoped RS256 token the downstream
verifies via JWKS. A SAML implementation (issuing assertions) can be added behind the same
interface later without touching the launch route — that's why saml-handoff currently
raises "not implemented" rather than being wired into the JWT path.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

import jwt
from pydantic import BaseModel

from app.auth.errors import AuthError
from app.auth.keystore import KeyStore
from app.auth.provider import Principal
from app.config import Settings
from app.schemas.system import LinkedSystem


class HandoffPayload(BaseModel):
    """How the browser should arrive at the downstream system."""

    mode: Literal["redirect", "auto_post"]
    action: str  # downstream URL
    fields: dict[str, str] = {}  # hidden form fields (auto_post)
    url: str | None = None  # full URL incl. token (redirect)


class DownstreamTokenIssuer(Protocol):
    def issue(self, principal: Principal, system: LinkedSystem) -> HandoffPayload: ...


class JwtDownstreamIssuer:
    """Mints an RS256, audience-scoped, 90s launch token and frames the handoff."""

    def __init__(self, settings: Settings, keystore: KeyStore) -> None:
        self._settings = settings
        self._keystore = keystore

    def mint(self, principal: Principal, *, audience: str) -> str:
        now = datetime.now(tz=UTC)
        claims = {
            "iss": self._settings.jwt_issuer,
            "sub": principal.subject,
            "aud": audience,  # ONE downstream system — replay at another system fails aud check
            "email": principal.email,
            "name": principal.display_name,
            "groups": principal.groups,
            "scope": "launch",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=self._settings.jwt_launch_ttl),
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(
            claims,
            self._keystore.private_pem,
            algorithm="RS256",
            headers={"kid": self._keystore.active_kid},
        )

    def issue(self, principal: Principal, system: LinkedSystem) -> HandoffPayload:
        if system.integration_type == "saml-handoff":
            # Deferred: downstream SAML-IdP (assertion issuance) lands behind this same seam.
            raise AuthError("SAML handoff not implemented yet", status_code=501)
        if system.integration_type != "jwt-handoff" or not system.audience:
            raise AuthError("system is not configured for token handoff", status_code=400)

        token = self.mint(principal, audience=system.audience)
        if system.handoff_mode == "auto_post":
            return HandoffPayload(
                mode="auto_post", action=system.url, fields={system.handoff_param: token}
            )
        sep = "&" if "?" in system.url else "?"
        url = f"{system.url}{sep}{system.handoff_param}={token}"
        return HandoffPayload(mode="redirect", action=system.url, url=url)
