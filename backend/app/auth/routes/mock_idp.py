"""Dev-only mock SAML IdP — a REAL signing IdP fixture.

Mounted only when APP_ENV=dev and SAML_MOCK_IDP_ENABLED. It receives the SP's AuthnRequest,
builds a SAML Response containing a signed Assertion (signed with python3-saml's vetted
`add_sign` — NOT hand-rolled crypto), and auto-POSTs it to the SP ACS. This exercises the
REAL SP validation path end-to-end, which is what proves go-live against Samsung AD is
config-only. At go-live this whole module is simply not mounted (prod).
"""

import html
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from lxml import etree
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from app.config import Settings, get_settings

router = APIRouter(prefix="/auth/mock-idp", tags=["mock-idp"])


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _decode_authn_request(saml_request: str | None) -> tuple[str | None, str | None]:
    """Return (request_id, acs_url) from the SP AuthnRequest, if present."""
    if not saml_request:
        return None, None
    try:
        xml = OneLogin_Saml2_Utils.decode_base64_and_inflate(saml_request)
        root = etree.fromstring(xml)
        return root.get("ID"), root.get("AssertionConsumerServiceURL")
    except Exception:
        return None, None


def _build_signed_response(settings: Settings, *, in_response_to: str | None, acs_url: str) -> str:
    now = datetime.now(tz=UTC)
    not_before = now - timedelta(minutes=2)
    not_after = now + timedelta(minutes=5)
    idp_entity = settings.saml_mock_idp_entity_id
    sp_entity = settings.saml_sp_entity_id
    email = settings.mock_user_email
    name = settings.mock_user_name
    groups = settings.mock_user_group_list

    assertion_id = OneLogin_Saml2_Utils.generate_unique_id()
    response_id = OneLogin_Saml2_Utils.generate_unique_id()
    session_index = OneLogin_Saml2_Utils.generate_unique_id()
    irt = f' InResponseTo="{in_response_to}"' if in_response_to else ""

    group_values = "".join(
        f'<saml:AttributeValue xsi:type="xs:string">{html.escape(g)}</saml:AttributeValue>'
        for g in groups
    )

    # Self-contained namespaces so the assertion stays valid once embedded in the Response.
    assertion = f"""<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" \
xmlns:xs="http://www.w3.org/2001/XMLSchema" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
ID="{assertion_id}" Version="2.0" IssueInstant="{_ts(now)}">\
<saml:Issuer>{html.escape(idp_entity)}</saml:Issuer>\
<saml:Subject>\
<saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{html.escape(email)}</saml:NameID>\
<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">\
<saml:SubjectConfirmationData NotOnOrAfter="{_ts(not_after)}" Recipient="{html.escape(acs_url)}"{irt}/>\
</saml:SubjectConfirmation>\
</saml:Subject>\
<saml:Conditions NotBefore="{_ts(not_before)}" NotOnOrAfter="{_ts(not_after)}">\
<saml:AudienceRestriction><saml:Audience>{html.escape(sp_entity)}</saml:Audience></saml:AudienceRestriction>\
</saml:Conditions>\
<saml:AuthnStatement AuthnInstant="{_ts(now)}" SessionIndex="{session_index}">\
<saml:AuthnContext>\
<saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>\
</saml:AuthnContext>\
</saml:AuthnStatement>\
<saml:AttributeStatement>\
<saml:Attribute Name="{settings.saml_attr_email}" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">\
<saml:AttributeValue xsi:type="xs:string">{html.escape(email)}</saml:AttributeValue></saml:Attribute>\
<saml:Attribute Name="{settings.saml_attr_name}" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">\
<saml:AttributeValue xsi:type="xs:string">{html.escape(name)}</saml:AttributeValue></saml:Attribute>\
<saml:Attribute Name="{settings.saml_attr_groups}" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">\
{group_values}</saml:Attribute>\
</saml:AttributeStatement>\
</saml:Assertion>"""

    idp_key = Path(settings.resolve(settings.saml_idp_key_path)).read_text(encoding="utf-8")
    idp_cert = Path(settings.resolve(settings.saml_idp_cert_path)).read_text(encoding="utf-8")
    signed_assertion = OneLogin_Saml2_Utils.add_sign(
        assertion,
        idp_key,
        idp_cert,
        sign_algorithm=OneLogin_Saml2_Constants.RSA_SHA256,
        digest_algorithm=OneLogin_Saml2_Constants.SHA256,
    )
    if isinstance(signed_assertion, bytes):
        signed_assertion = signed_assertion.decode("utf-8")

    response = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" \
xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" \
ID="{response_id}" Version="2.0" IssueInstant="{_ts(now)}" Destination="{html.escape(acs_url)}"{irt}>\
<saml:Issuer>{html.escape(idp_entity)}</saml:Issuer>\
<samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>\
{signed_assertion}\
</samlp:Response>"""
    return response


def _auto_post_form(acs_url: str, saml_response_b64: str, relay_state: str | None) -> str:
    relay_field = (
        f'<input type="hidden" name="RelayState" value="{html.escape(relay_state)}"/>'
        if relay_state
        else ""
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Mock IdP</title></head>
<body onload="document.forms[0].submit()">
<p>Mock IdP — signing in… (dev only)</p>
<form method="POST" action="{html.escape(acs_url)}">
<input type="hidden" name="SAMLResponse" value="{html.escape(saml_response_b64)}"/>
{relay_field}
<noscript><button type="submit">Continue</button></noscript>
</form></body></html>"""


async def _handle(request: Request, settings: Settings) -> HTMLResponse:
    params = dict(request.query_params)
    if request.method == "POST":
        form = await request.form()
        params = {**params, **{k: str(v) for k, v in form.items()}}

    request_id, acs_from_req = _decode_authn_request(params.get("SAMLRequest"))
    acs_url = acs_from_req or settings.saml_acs_url
    relay_state = params.get("RelayState")

    response_xml = _build_signed_response(settings, in_response_to=request_id, acs_url=acs_url)
    response_b64 = OneLogin_Saml2_Utils.b64encode(response_xml)
    return HTMLResponse(_auto_post_form(acs_url, response_b64, relay_state))


@router.get("/sso")
async def sso_get(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return await _handle(request, settings)


@router.post("/sso")
async def sso_post(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return await _handle(request, settings)
