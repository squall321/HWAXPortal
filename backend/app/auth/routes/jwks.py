"""JWKS endpoint — downstream systems fetch this to verify launch tokens (RS256 public keys)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json")
def jwks(request: Request) -> JSONResponse:
    return JSONResponse(
        request.app.state.keystore.jwks(),
        headers={"Cache-Control": "public, max-age=300"},
    )
