"""SAML SP provider — the real upstream auth, behind the same AuthProvider seam as mock.

Uses python3-saml to build the AuthnRequest (login) and to validate the IdP's signed
SAMLResponse at the ACS (callback). Maps the assertion attributes to a Principal via the
configurable attribute names. Selected by AUTH_PROVIDER=saml.
"""

import logging

from fastapi import Request
from fastapi.responses import RedirectResponse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.errors import OneLogin_Saml2_Error, OneLogin_Saml2_ValidationError

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.auth.saml_sp import build_saml_settings, prepare_request, prepare_static_request
from app.auth.user_store import norm_email
from app.config import Settings

log = logging.getLogger("hwax.saml")


def _first(values: list[str] | None) -> str | None:
    return values[0] if values else None


def _subject(source: str, *, email: str, nameid: str | None, attrs: dict) -> str:
    """식별자 — 기본은 이메일로 고정(config `saml_subject_source`). 다른 출처를 골랐는데 Assertion 에 없으면 **거절한다** —
    이메일로 몰래 떨어지면 로그인마다 키가 바뀌어 한 사람이 둘로 갈린다(종전 `nameid or email` 의 지뢰와 같은 모양)."""
    if source == "email":
        return email
    got = nameid if source == "nameid" else _first(attrs.get(source))
    if not (got or "").strip():
        raise AuthError(f"SAML assertion has no subject source {source!r} (SAML_SUBJECT_SOURCE) — "
                        "refusing to fall back to email", status_code=400)
    return got.strip()


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
        # python3-saml 은 검증 실패를 두 길로 낸다 — get_errors() 와 **예외**. is_valid() 를 통과한 뒤 store_valid_response() 가
        # NameID 를 꺼내다 던지는 것(wantNameId 참 + NameID 없음 — 운영 ADFS 모양)과 SAMLResponse 없는 POST 는 예외라, 잡지 않으면
        # 핸들링 없는 500 트레이스백이 됐다(6차 요청 §2 를 재현하다 발견 — 요청서는 400 으로 읽었다). 실패는 400 과 사유로 낸다.
        try:
            auth.process_response()
        except (OneLogin_Saml2_Error, OneLogin_Saml2_ValidationError) as exc:
            raise AuthError(f"SAML response invalid: {exc}", status_code=400) from exc

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
        # 원장·로컬 계정과 같은 정규화 — subject 가 곧 이메일인 사람(NameID 없는 운영 ADFS)이 'Koo.Park@…' 로 오면 로컬 계정 시절의
        # 소문자 subject 와 갈라져 대화·PAT·절차가 통째로 안 보인다(로컬 계정 브리지의 승계 약속, 6차 요청 검토).
        # 이메일은 **지정한 Claim(SAML_ATTR_EMAIL)에서만** 잡는다. 종전엔 없으면 NameID 로 떨어져, IdP 가 NameID(LoginId 등)를 켠 날
        # SAML_ATTR_EMAIL 이 어긋나 있으면 subject·원장 키가 말없이 'kpark01' 이 되어 빈 새 계정이 생겼다 — subject 를 못박은 것과 같은
        # 지뢰다(6차 검토 2차). 없으면 거절하고 받은 Claim **이름**을 알려 준다(값은 안 싣는다).
        email = norm_email(_first(attrs.get(s.saml_attr_email)) or "")
        if not email:
            raise AuthError(f"SAML assertion has no email claim {s.saml_attr_email!r} (SAML_ATTR_EMAIL) — "
                            f"received claims: {sorted(attrs)}", status_code=400)
        # 지정한 Claim 이 Assertion 에 없으면 한 줄 남긴다 — 이름 Claim 이 릴리즈됐는데 이름이 대소문자·형식(`displayName` 대
        # `…/DisplayName`)이 어긋나면 대체 사슬이 조용히 원장으로 떨어지고 아무도 모른다(6차 요청 §4-B-5). Claim **이름만** 적는다.
        for env_key, claim in (("SAML_ATTR_NAME", s.saml_attr_name), ("SAML_ATTR_DEPARTMENT", s.saml_attr_department)):
            if claim and claim not in attrs:
                log.warning("SAML: %s=%r 이 Assertion 에 없다 — 받은 Claim: %s", env_key, claim, sorted(attrs))
        return Principal(
            subject=_subject(s.saml_subject_source, email=email, nameid=nameid, attrs=attrs),
            email=email,
            display_name=_first(attrs.get(s.saml_attr_name)),
            groups=attrs.get(s.saml_attr_groups, []),
            attributes=attrs,
        )
