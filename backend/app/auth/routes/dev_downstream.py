"""Dev-only fake downstream system — proves the launch handoff end to end.

Simulates what a real linked system does on receipt of a launch token: verify the RS256
signature with the portal's published public key (kid → JWKS), check iss/exp/scope, and
enforce single-use via the jti replay store. Mounted only in dev; never in prod.
"""

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/echo-downstream")
async def echo_downstream(
    request: Request, settings: Settings = Depends(get_settings)
) -> JSONResponse:
    form = await request.form()
    token = form.get("token")
    if not token:
        return JSONResponse({"verified": False, "error": "no token"}, status_code=400)

    keystore = request.app.state.keystore
    token_store = request.app.state.token_store

    try:
        kid = jwt.get_unverified_header(token).get("kid")
        public_pem = keystore.public_pem(kid)
        claims = jwt.decode(
            token,
            public_pem,
            algorithms=["RS256"],  # pin
            issuer=settings.jwt_issuer,
            options={"verify_aud": False, "require": ["exp", "iss", "sub", "jti"]},
        )
    except Exception as exc:  # noqa: BLE001 — surface any verification failure to the caller
        return JSONResponse({"verified": False, "error": str(exc)}, status_code=401)

    if claims.get("scope") != "launch":
        return JSONResponse({"verified": False, "error": "wrong scope"}, status_code=401)
    if not token_store.mark_jti_once(claims["jti"], int(claims["exp"])):
        return JSONResponse({"verified": False, "error": "replay detected"}, status_code=401)

    return JSONResponse(
        {
            "verified": True,
            "sub": claims["sub"],
            "email": claims.get("email"),
            "aud": claims.get("aud"),
            "groups": claims.get("groups", []),
        }
    )
