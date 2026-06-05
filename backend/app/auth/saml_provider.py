"""SAML SP provider — the real upstream auth, behind the same AuthProvider seam as mock.

Uses python3-saml to build the AuthnRequest (login) and to validate the IdP's signed
SAMLResponse at the ACS (callback). Maps the assertion attributes to a Principal via the
configurable attribute names. Selected by AUTH_PROVIDER=saml.
"""

from fastapi import Request
from fastapi.responses import RedirectResponse
from onelogin.saml2.auth import OneLogin_Saml2_Auth

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.auth.saml_sp import build_saml_settings, prepare_request, prepare_static_request
from app.config import Settings


def _first(values: list[str] | None) -> str | None:
    return values[0] if values else None


class SamlProvider:
    name = "saml"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Built once; raises at startup if metadata/certs are missing/invalid (fail fast).
        self._saml_settings = build_saml_settings(settings)

    def _auth(self, request: Request, post_data: dict | None = None) -> OneLogin_Saml2_Auth:
        req = prepare_request(request, post_data or {}, self._settings)
        return OneLogin_Saml2_Auth(req, old_settings=self._saml_settings)

    def login_redirect(self, *, state: str) -> RedirectResponse:
        req = prepare_static_request(self._settings, path="/auth/login")
        auth = OneLogin_Saml2_Auth(req, old_settings=self._saml_settings)
        # return_to becomes RelayState — round-trips our signed login state to the ACS.
        url = auth.login(return_to=state)
        return RedirectResponse(url, status_code=302)

    async def handle_callback(self, request: Request, *, expected_state: str | None) -> Principal:
        form = await request.form()
        post_data = {k: str(v) for k, v in form.items()}
        auth = self._auth(request, post_data)
        auth.process_response()

        errors = auth.get_errors()
        if errors:
            raise AuthError(
                f"SAML response invalid: {', '.join(errors)} ({auth.get_last_error_reason()})",
                status_code=400,
            )
        if not auth.is_authenticated():
            raise AuthError("SAML authentication failed", status_code=401)

        # RelayState binds the response to our login attempt (defense against replay/CSRF).
        relay = post_data.get("RelayState")
        if expected_state and relay and relay != expected_state:
            raise AuthError("SAML RelayState mismatch", status_code=400)

        attrs = auth.get_attributes()
        s = self._settings
        nameid = auth.get_nameid()
        email = _first(attrs.get(s.saml_attr_email)) or nameid
        if not email:
            raise AuthError("SAML assertion missing email/NameID", status_code=400)
        return Principal(
            subject=nameid or email,
            email=email,
            display_name=_first(attrs.get(s.saml_attr_name)),
            groups=attrs.get(s.saml_attr_groups, []),
            attributes=attrs,
        )
