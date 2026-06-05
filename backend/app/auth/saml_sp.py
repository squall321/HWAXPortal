"""python3-saml (OneLogin) glue for the SP role.

Builds the python3-saml settings dict from app config + on-disk cert/key, parsing the IdP
half straight from metadata (file in dev, URL in prod). This is the entire mock↔real-AD
delta: the same SP code, a different `idp` block. `prepare_request` pins the request's
host/port to public_base_url so SAML Destination validation works behind the Vite proxy
(and behind any reverse proxy in prod).
"""

from pathlib import Path
from urllib.parse import urlparse

from fastapi import Request
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

from app.config import Settings


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _pem_body(pem: str) -> str:
    """Strip PEM header/footer + newlines — python3-saml wants the bare base64 body."""
    return "".join(
        line for line in pem.strip().splitlines() if "-----" not in line
    )


def build_saml_settings(settings: Settings) -> dict:
    if settings.saml_idp_metadata_url:
        idp_data = OneLogin_Saml2_IdPMetadataParser.parse_remote(
            settings.saml_idp_metadata_url, validate_cert=False
        )
    else:
        idp_data = OneLogin_Saml2_IdPMetadataParser.parse(
            _read(settings.resolve(settings.saml_idp_metadata_path))
        )

    sp_cert = _read(settings.resolve(settings.saml_sp_cert_path))
    sp_key = _read(settings.resolve(settings.saml_sp_key_path))

    saml_settings: dict = {
        "strict": True,
        "debug": settings.app_env == "dev",
        "sp": {
            "entityId": settings.saml_sp_entity_id,
            "assertionConsumerService": {
                "url": settings.saml_acs_url,
                "binding": OneLogin_Saml2_Constants.BINDING_HTTP_POST,
            },
            "singleLogoutService": {
                "url": settings.saml_sls_url,
                "binding": OneLogin_Saml2_Constants.BINDING_HTTP_REDIRECT,
            },
            "NameIDFormat": OneLogin_Saml2_Constants.NAMEID_EMAIL_ADDRESS,
            "x509cert": _pem_body(sp_cert),
            "privateKey": _pem_body(sp_key),
        },
        "security": {
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "wantNameId": True,
            "requestedAuthnContext": False,
            "signatureAlgorithm": OneLogin_Saml2_Constants.RSA_SHA256,
            "digestAlgorithm": OneLogin_Saml2_Constants.SHA256,
        },
    }
    # Take only the parsed "idp" block. (The metadata parser also returns an "sp" block
    # carrying the IdP's advertised NameIDFormat — a blind .update() would clobber our SP config.)
    saml_settings["idp"] = idp_data["idp"]
    return saml_settings


def _host_fields(settings: Settings) -> dict:
    parsed = urlparse(settings.public_base_url)
    https = parsed.scheme == "https"
    return {
        "https": "on" if https else "off",
        "http_host": parsed.hostname,
        "server_port": str(parsed.port or (443 if https else 80)),
    }


def prepare_request(request: Request, post_data: dict, settings: Settings) -> dict:
    """Build the request dict python3-saml expects, with host pinned to public_base_url."""
    return {
        **_host_fields(settings),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": post_data,
    }


def prepare_static_request(settings: Settings, *, path: str) -> dict:
    """Request dict for contexts without a FastAPI Request (e.g. building a login redirect)."""
    return {
        **_host_fields(settings),
        "script_name": path,
        "get_data": {},
        "post_data": {},
    }
