"""OIDC Relying Party — the portal logs users in via an upstream OIDC IdP.

The third `AuthProvider` (mock / saml / oidc). `login_redirect` sends the browser to the IdP's
authorization endpoint (authorization-code + PKCE + nonce); `handle_callback` exchanges the code,
validates the id_token against the IdP JWKS, and maps the claims to a `Principal`. Everything
downstream of `Principal` is provider-independent — going live = set OIDC_ISSUER + client id/secret
(no code edits). The dev mock OP (auth/routes/oidc_mock_idp.py) exercises this EXACT path.

nonce and the PKCE verifier are DERIVED from the signed login-state token via HMAC(session_secret),
so they round-trip through the existing `hwax_authstate` cookie with no server-side store.

HTTP discipline: `login_redirect` runs in a SYNC FastAPI route (threadpool) so a blocking
`httpx.Client` is fine; `handle_callback` is ASYNC and talks to the SAME uvicorn process (the IdP
loops back through nginx in dev), so it MUST use `httpx.AsyncClient` — a sync call there would block
the event loop and self-deadlock.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class OidcProvider:
    """Authorization-code + PKCE + nonce RP. Validates the id_token via the IdP JWKS (RS256)."""

    name = "oidc"

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._discovery: dict[str, Any] | None = None

    # ── discovery (cached) ────────────────────────────────────────────────────
    def _disco_sync(self) -> dict[str, Any]:
        if self._discovery is None:
            with httpx.Client(timeout=5) as c:
                r = c.get(self._s.oidc_discovery)
                r.raise_for_status()
                self._discovery = r.json()
        return self._discovery

    async def _disco_async(self, client: httpx.AsyncClient) -> dict[str, Any]:
        if self._discovery is None:
            r = await client.get(self._s.oidc_discovery)
            r.raise_for_status()
            self._discovery = r.json()
        return self._discovery

    # ── nonce / PKCE verifier derived from the signed state (no server-side store) ──
    def _derive(self, state: str, label: str) -> str:
        mac = hmac.new(
            self._s.session_secret.encode(), f"{state}:{label}".encode(), hashlib.sha256
        ).digest()
        return _b64url(mac)

    # ── AuthProvider interface ─────────────────────────────────────────────────
    def login_redirect(self, *, state: str) -> RedirectResponse:
        nonce = self._derive(state, "nonce")
        verifier = self._derive(state, "pkce")
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        params = {
            "response_type": "code",
            "client_id": self._s.oidc_client_id,
            "redirect_uri": self._s.oidc_redirect_uri,
            "scope": self._s.oidc_scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = f"{self._disco_sync()['authorization_endpoint']}?{urlencode(params)}"
        return RedirectResponse(url, status_code=302)

    async def handle_callback(self, request: Request, *, expected_state: str | None) -> Principal:
        q = request.query_params
        if q.get("error"):
            raise AuthError(f"IdP returned error: {q.get('error')}", status_code=401)
        code = q.get("code")
        returned_state = q.get("state")
        if not code or not expected_state or returned_state != expected_state:
            raise AuthError("login state mismatch", status_code=400)

        verifier = self._derive(expected_state, "pkce")
        nonce = self._derive(expected_state, "nonce")

        # All IdP HTTP is async here — the dev mock OP loops back through THIS uvicorn process,
        # so a blocking client would deadlock the event loop.
        async with httpx.AsyncClient(timeout=8) as c:
            disco = await self._disco_async(c)
            tok = await c.post(
                disco["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._s.oidc_redirect_uri,
                    "client_id": self._s.oidc_client_id,
                    "client_secret": self._s.oidc_client_secret,
                    "code_verifier": verifier,
                },
            )
            if tok.status_code != 200:
                raise AuthError("token exchange failed", status_code=401)
            token_resp = tok.json()
            id_token = token_resp.get("id_token")
            if not id_token:
                raise AuthError("no id_token in token response", status_code=401)

            jwks_keys = (await c.get(disco["jwks_uri"])).json().get("keys", [])
            claims = self._verify_id_token(id_token, nonce, disco["issuer"], jwks_keys)

            # userinfo enrichment (email/groups sometimes only there); best-effort, never fatal.
            info: dict[str, Any] = {}
            access = token_resp.get("access_token")
            if access and disco.get("userinfo_endpoint"):
                try:
                    ui = await c.get(
                        disco["userinfo_endpoint"],
                        headers={"Authorization": f"Bearer {access}"},
                    )
                    if ui.status_code == 200:
                        info = ui.json()
                except Exception:  # noqa: BLE001
                    info = {}

        merged = {**claims, **info}
        s = self._s
        email = merged.get(s.oidc_claim_email)
        if not email:
            raise AuthError("id_token has no email claim", status_code=401)
        groups = merged.get(s.oidc_claim_groups) or []
        if isinstance(groups, str):
            groups = [g for g in groups.replace(",", " ").split() if g]
        return Principal(
            subject=str(merged.get(s.oidc_claim_subject) or email),
            email=email,
            display_name=merged.get(s.oidc_claim_name),
            groups=list(groups),
            attributes={"provider": ["oidc"]},
        )

    def _verify_id_token(
        self, id_token: str, nonce: str, issuer: str, jwks_keys: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError as e:
            raise AuthError("malformed id_token", status_code=401) from e
        kid = header.get("kid")
        jwk = next((k for k in jwks_keys if k.get("kid") == kid), None)
        if jwk is None:
            raise AuthError("no matching IdP key for id_token", status_code=401)
        try:
            claims = jwt.decode(
                id_token,
                jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk)),
                algorithms=["RS256"],
                audience=self._s.oidc_client_id,
                issuer=issuer,
                options={"require": ["exp", "aud", "iss", "sub"]},
                leeway=30,
            )
        except jwt.PyJWTError as e:
            raise AuthError("id_token rejected", status_code=401) from e
        if nonce and claims.get("nonce") != nonce:
            raise AuthError("id_token nonce mismatch", status_code=401)
        return claims
