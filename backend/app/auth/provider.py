"""The auth seam.

`AuthProvider` is the ONLY IdP-dependent surface in the system. Two implementations
satisfy it — `mock` (dev) and `saml` (real Samsung AD, Phase 2) — selected by config.
Everything downstream of `handle_callback() -> Principal` (session issuance, current-user
resolution, RBAC, catalog, launch, the entire frontend) is IdP-independent and written
once. Going live = flip AUTH_PROVIDER and swap IdP metadata/cert/attribute-map (config only).
"""

from typing import Protocol, runtime_checkable

from fastapi import Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field


class Principal(BaseModel):
    """Normalized identity returned by every provider. The cross-system contract."""

    subject: str  # stable unique id (AD objectGUID in prod; email in mock)
    email: str
    display_name: str | None = None
    groups: list[str] = Field(default_factory=list)  # AD groups (memberOf)
    attributes: dict[str, list[str]] = Field(default_factory=dict)  # raw, for debugging/mapping


@runtime_checkable
class AuthProvider(Protocol):
    """Upstream identity provider. `mock` and `saml` both implement this."""

    name: str

    def login_redirect(self, *, state: str) -> RedirectResponse:
        """Send the browser to the IdP to authenticate.

        `state` is an opaque, signed token the provider must round-trip back
        (mock: as a query param; SAML: as RelayState) so the callback can bind
        the response to this login attempt.
        """
        ...

    async def handle_callback(self, request: Request, *, expected_state: str | None) -> Principal:
        """Process the IdP's return (mock callback / SAML ACS POST) into a Principal.

        Must validate the response (signature/conditions for SAML; state match for mock)
        and raise `AuthError` on any failure. `expected_state` is the state value the
        portal stored at login time.
        """
        ...
