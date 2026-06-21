"""Dev-only mock OIDC OP — a REAL RS256-signing OpenID Provider fixture.

Mounted only when APP_ENV=dev and OIDC_MOCK_IDP_ENABLED. Exposes the standard OIDC endpoints
(discovery / jwks / authorize / token / userinfo) and, like the mock SAML IdP, auto-issues the
configured mock user with NO login form. It signs id_tokens with the portal RS256 keystore, so the
RP's full validation path (discovery → authorize → code exchange → id_token RS256 verify via JWKS →
nonce + PKCE) is exercised end-to-end. At go-live this module is simply not mounted (prod points the
RP at the real corp IdP). Single-process, in-process code/token stores — dev only.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import Settings, get_settings

router = APIRouter(prefix="/auth/oidc-mock", tags=["oidc-mock"])

# code -> {nonce, challenge, exp} ;  access_token -> exp   (in-process; single uvicorn; dev only)
_codes: dict[str, dict[str, Any]] = {}
_tokens: dict[str, float] = {}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _gc(now: float) -> None:
    for k in [k for k, v in _codes.items() if v["exp"] < now]:
        _codes.pop(k, None)
    for k in [k for k, v in _tokens.items() if v < now]:
        _tokens.pop(k, None)


@router.get("/.well-known/openid-configuration")
def discovery(settings: Settings = Depends(get_settings)) -> JSONResponse:
    base = settings.oidc_mock_issuer
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/authorize",
            "token_endpoint": f"{base}/token",
            "jwks_uri": f"{base}/jwks",
            "userinfo_endpoint": f"{base}/userinfo",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "scopes_supported": ["openid", "email", "profile", "groups"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
        }
    )


@router.get("/jwks")
def jwks(request: Request) -> JSONResponse:
    # Same RS256 keystore the portal publishes for downstream launch tokens — fine for a dev OP.
    return JSONResponse(request.app.state.keystore.jwks())


@router.get("/authorize")
def authorize(request: Request, settings: Settings = Depends(get_settings)) -> RedirectResponse:
    q = request.query_params
    redirect_uri = q.get("redirect_uri") or settings.oidc_redirect_uri
    state = q.get("state") or ""
    now = time.time()
    _gc(now)
    code = secrets.token_urlsafe(24)
    _codes[code] = {"nonce": q.get("nonce") or "", "challenge": q.get("code_challenge") or "", "exp": now + 120}
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{sep}code={code}&state={state}", status_code=302)


@router.post("/token")
async def token(request: Request, settings: Settings = Depends(get_settings)) -> JSONResponse:
    form = await request.form()
    code = form.get("code")
    now = time.time()
    _gc(now)
    entry = _codes.pop(code, None) if code else None
    if entry is None:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)
    # PKCE (S256) verification when the client used a challenge.
    if entry.get("challenge"):
        calc = _b64url(hashlib.sha256(str(form.get("code_verifier") or "").encode()).digest())
        if calc != entry["challenge"]:
            return JSONResponse({"error": "invalid_grant", "error_description": "pkce"}, status_code=400)

    ks = request.app.state.keystore
    claims = {
        "iss": settings.oidc_mock_issuer,
        "sub": settings.mock_user_email,
        "aud": settings.oidc_client_id,
        "email": settings.mock_user_email,
        "name": settings.mock_user_name,
        "groups": settings.mock_user_group_list,
        "nonce": entry["nonce"],
        "iat": int(now),
        "exp": int(now) + 300,
    }
    id_token = jwt.encode(claims, ks.private_pem, algorithm="RS256", headers={"kid": ks.active_kid})
    access = secrets.token_urlsafe(24)
    _tokens[access] = now + 300
    return JSONResponse(
        {"access_token": access, "token_type": "Bearer", "expires_in": 300, "id_token": id_token}
    )


@router.get("/userinfo")
def userinfo(request: Request, settings: Settings = Depends(get_settings)) -> JSONResponse:
    auth = request.headers.get("Authorization", "")
    tok = auth[7:] if auth.lower().startswith("bearer ") else ""
    _gc(time.time())
    if tok not in _tokens:
        return JSONResponse({"error": "invalid_token"}, status_code=401)
    return JSONResponse(
        {
            "sub": settings.mock_user_email,
            "email": settings.mock_user_email,
            "name": settings.mock_user_name,
            "groups": settings.mock_user_group_list,
        }
    )
