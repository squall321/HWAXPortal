# IdP 메타데이터 URL 은 TLS 를 검증해 받는다 — 끄는 손잡이는 설정으로만(5차 요청 §4)
"""메타데이터에는 IdP 서명 인증서가 들어 있다. 검증 없이 받으면 중간자가 그것을 갈아끼워 위조 Assertion 을 통과시킨다.
예전엔 `validate_cert=False` 가 박혀 있었다. 실제 네트워크는 안 쓴다 — parse_remote 를 대역으로 바꿔 받은 인자를 본다."""
import pytest

from app.auth import saml_sp
from app.config import Settings


class _Stop(Exception):
    pass


def _validate_cert_passed(monkeypatch, **kw) -> bool:
    seen: dict = {}

    def fake(url, **kwargs):
        seen.update(kwargs, url=url)
        raise _Stop          # 뒤의 SP 인증서 읽기까지 가지 않는다

    monkeypatch.setattr(saml_sp.OneLogin_Saml2_IdPMetadataParser, "parse_remote", staticmethod(fake))
    with pytest.raises(_Stop):
        saml_sp.build_saml_settings(Settings(saml_idp_metadata_url="https://idp.test/md.xml", **kw))
    assert seen["url"] == "https://idp.test/md.xml"
    return seen["validate_cert"]


def test_기본은_TLS_를_검증한다(monkeypatch):
    assert _validate_cert_passed(monkeypatch) is True


def test_끄는_것은_설정으로만(monkeypatch):
    assert _validate_cert_passed(monkeypatch, saml_idp_metadata_validate_cert=False) is False


def test_환경변수로도_끈다(monkeypatch):
    monkeypatch.setenv("SAML_IDP_METADATA_VALIDATE_CERT", "false")
    assert Settings().saml_idp_metadata_validate_cert is False
