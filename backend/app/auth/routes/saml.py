"""SAML SP endpoints (active when AUTH_PROVIDER=saml).

  POST /auth/saml/acs       — Assertion Consumer Service: the IdP posts the signed response here.
  GET  /auth/saml/metadata  — SP metadata XML (give this to the Samsung AD admins to register us).
  GET  /auth/saml/sls       — Single Logout (stub; full SLO is a later phase).
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.auth import cookies
from app.auth.jwt_service import JWTService
from app.auth.provider import AuthProvider
from app.auth.routes.session import complete_login
from app.auth.saml_sp import build_saml_settings
from app.config import Settings, get_settings
from app.deps import get_auth_provider, get_jwt_service

router = APIRouter(prefix="/auth/saml", tags=["saml"])


@router.post("/acs")
async def acs(
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: AuthProvider = Depends(get_auth_provider),
    jwt_service: JWTService = Depends(get_jwt_service),
):
    expected_state = request.cookies.get(cookies.STATE_COOKIE)
    principal = await provider.handle_callback(request, expected_state=expected_state)
    return complete_login(
        principal=principal,
        expected_state=expected_state,
        settings=settings,
        jwt_service=jwt_service,
    )


@router.get("/metadata")
def metadata(settings: Settings = Depends(get_settings)) -> Response:
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    saml_settings = OneLogin_Saml2_Settings(build_saml_settings(settings), sp_validation_only=True)
    xml = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(xml)
    if errors:
        return Response(content=f"invalid metadata: {errors}", status_code=500)
    return Response(content=xml, media_type="application/xml")


@router.get("/sls")
def sls() -> Response:
    # Full Single Logout is deferred; portal logout (clearing cookies) is handled at /auth/logout.
    return Response(content="SLO not implemented", status_code=501)
