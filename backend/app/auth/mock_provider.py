"""In-process mock IdP — dev only.

Simulates an instant SSO: `login_redirect` bounces the browser straight back to the
portal callback (staying on the same proxied origin so cookies flow in dev), and
`handle_callback` returns the configured fake AD user. This exercises the real
login/callback/session machinery without any external IdP. The SAML provider (Phase 2)
replaces it behind the same `AuthProvider` interface — no downstream code changes.
"""

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings


class MockProvider:
    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def login_redirect(self, *, state: str) -> RedirectResponse:
        # Relative URL keeps the browser on the current (proxied, same-origin) host in dev,
        # so the state cookie set at /auth/login is sent back to /auth/callback.
        return RedirectResponse(f"/auth/callback?state={quote(state)}", status_code=302)

    async def handle_callback(self, request: Request, *, expected_state: str | None) -> Principal:
        returned_state = request.query_params.get("state")
        if not expected_state or returned_state != expected_state:
            raise AuthError("login state mismatch", status_code=400)
        s = self._settings
        return Principal(
            subject=s.mock_user_email,
            email=s.mock_user_email,
            display_name=s.mock_user_name,
            groups=s.mock_user_group_list,
            attributes={"provider": ["mock"]},
        )
