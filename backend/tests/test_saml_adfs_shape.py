# 운영 ADFS 모양의 Assertion(NameID 없음·URI Claim 다섯 개)으로 끝까지 로그인한다(6차 요청 §2)
"""운영 ADFS(sts.secsso.net)는 NameID 를 보내지 않고 Claim 은 LoginId·CompId·DeptId·Sabun·Mail 다섯 개뿐이다(2026-10-01
SSO 운영팀 실측). python3-saml 은 wantNameId 가 참이면 NameID 부재를 검증 실패로 쳐서, 서명·시간·Audience 를 다 통과한 Assertion 이
400 이었다. dev mock IdP 가 실제로 서명한 Assertion 에서 NameID 를 빼고 Claim 을 운영 모양으로 바꿔(서명 **전에**) 실제 SP 검증 경로로 돌린다.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
CLAIM = "http://schemas.sec.com/2018/05/identity/claims/"

_E2E = r'''
import json, re, sys
from urllib.parse import urlsplit
from fastapi.testclient import TestClient
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import app.auth.routes.mock_idp as mock_idp
from app.main import app

CLAIM = "http://schemas.sec.com/2018/05/identity/claims/"
MAIL = sys.argv[1]
_real_sign = OneLogin_Saml2_Utils.add_sign

def _attr(name, value):
    return (f'<saml:Attribute Name="{CLAIM}{name}"><saml:AttributeValue xsi:type="xs:string">{value}'
            '</saml:AttributeValue></saml:Attribute>')

class _AdfsShape(OneLogin_Saml2_Utils):
    """서명 직전의 Assertion 을 운영 모양으로 — NameID 를 빼고 Claim 을 다섯 개로(이름·그룹 Claim 없음)."""
    @staticmethod
    def add_sign(xml, *a, **kw):
        xml = re.sub(r"<saml:NameID[^>]*>[^<]*</saml:NameID>", "", xml)
        attrs = "".join(_attr(n, v) for n, v in (("LoginId", "kpark01"), ("CompId", "C100"), ("DeptId", "D2001"),
                                                 ("Sabun", "1234567"), ("Mail", MAIL)))
        xml = re.sub(r"<saml:AttributeStatement>.*</saml:AttributeStatement>",
                     f"<saml:AttributeStatement>{attrs}</saml:AttributeStatement>", xml, flags=re.S)
        assert "NameID" not in xml
        return _real_sign(xml, *a, **kw)

mock_idp.OneLogin_Saml2_Utils = _AdfsShape

def path(u):
    p = urlsplit(u); return p.path + ("?" + p.query if p.query else "")

out = {}
with TestClient(app, base_url="http://localhost:5283") as c:
    # 로컬 계정 시절의 대화 — subject 는 정규화된 이메일이다(local.py: subject=u["email"])
    app.state.conv_store.create(owner_sub="koo.park@example.com", title="로컬 계정 시절 대화")
    r = c.get("/auth/login", follow_redirects=False)
    r2 = c.get(path(r.headers["location"]), follow_redirects=False)
    html = r2.text.replace("&amp;", "&")
    action = re.search(r'action="([^"]+)"', html).group(1)
    data = {"SAMLResponse": re.search(r'name="SAMLResponse" value="([^"]+)"', html).group(1)}
    m = re.search(r'name="RelayState" value="([^"]+)"', html)
    if m:
        data["RelayState"] = m.group(1)
    r3 = c.post(path(action), data=data, follow_redirects=False)
    out["status"] = r3.status_code
    out["body"] = r3.text[:400]
    if r3.status_code in (302, 303):
        me = c.get("/auth/me")
        out["me_status"] = me.status_code
        out["me"] = me.json() if me.status_code == 200 else me.text[:300]
        out["convs"] = [x["title"] for x in c.get("/agent/conversations").json().get("conversations", [])]
print(json.dumps(out, ensure_ascii=False))
'''


def _run(tmp_path, *, want_nameid: str | None, mail: str = "koo.park@example.com") -> dict:
    env = {**os.environ,
           "AUTH_PROVIDER": "saml", "APP_ENV": "dev", "SAML_MOCK_IDP_ENABLED": "true",
           "PUBLIC_BASE_URL": "http://localhost:5283", "FRONTEND_URL": "http://localhost:5283",
           "SAML_ACS_PATH": "/auth/callback", "SAML_ATTR_EMAIL": CLAIM + "Mail",
           "SESSION_SECRET": "t" * 48, "COOKIE_SECURE": "false",
           # 기동이 실 저장소를 건드리지 않게 전부 임시로(test_saml_acs_path 와 같은 묶음)
           "USER_STORE_PATH": str(tmp_path / "users.sqlite"), "TOKEN_STORE_PATH": str(tmp_path / "tok.sqlite"),
           "CONV_STORE_PATH": str(tmp_path / "conv.sqlite"), "PROCEDURES_STORE_PATH": str(tmp_path / "proc.sqlite"),
           "AGENT_AUDIT_LOG_PATH": str(tmp_path / "audit.sqlite"), "JWT_KEYS_DIR": str(tmp_path / "jwt"),
           "JWT_AUTOGEN_KEYS": "true", "PROCEDURES_ARTIFACT_ROOT": str(tmp_path / "art"),
           "DELIB_ARCHIVE_ROOT": str(tmp_path / "delib"), "UPLOAD_STAGING_DIR": str(tmp_path / "stage")}
    env.pop("SAML_WANT_NAMEID", None)
    if want_nameid is not None:
        env["SAML_WANT_NAMEID"] = want_nameid
    r = subprocess.run([sys.executable, "-c", _E2E, mail], cwd=BACKEND, env=env, capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


needs_keys = pytest.mark.skipif(
    not ((BACKEND / "secrets/saml/sp.key").exists() and (BACKEND / "secrets/saml/idp.key").exists()),
    reason="개발용 SAML 키(backend/secrets/saml/*.key)가 없다 — 추적 파일이 아니다(scripts/gen_dev_certs.py)")


@needs_keys
def test_기본값_그대로면_NameID_없는_Assertion_은_400_이다(tmp_path):
    """**운영에서 막던 그 줄의 재현** — 기본값을 바꾸지 않았다는 것도 같이 고정한다."""
    out = _run(tmp_path, want_nameid=None)
    assert out["status"] == 400 and "NameID" in out["body"], out


@needs_keys
def test_NameID_를_요구하지_않으면_Mail_Claim_으로_로그인된다(tmp_path):
    out = _run(tmp_path, want_nameid="false")
    assert out["status"] in (302, 303), out
    me = out["me"]
    assert out["me_status"] == 200, out
    assert me["email"] == "koo.park@example.com" and me["subject"] == "koo.park@example.com", me
    # 이름·그룹 Claim 이 없다 — 그래도 로그인은 되고, 기본 권한(일반 챗)은 원장에서 나온다
    assert me["groups"] == [] and "feat:chat" in me["entitlements"], me


@needs_keys
def test_Mail_Claim_의_대소문자가_달라도_로컬_계정_시절_소유가_이어진다(tmp_path):
    """AD 의 mail 값은 'Koo.Park@…' 처럼 대문자가 섞인다. 로컬 계정은 소문자로 저장되고 subject 가 곧 그 이메일이라, 정규화하지 않으면
    SAML 로 넘어온 같은 사람이 **다른 subject** 가 되어 대화·PAT·절차가 통째로 안 보인다(로컬 계정 브리지의 승계 약속이 깨진다)."""
    out = _run(tmp_path, want_nameid="false", mail="Koo.Park@Example.COM ")
    assert out["status"] in (302, 303), out
    assert out["me"]["email"] == "koo.park@example.com" and out["me"]["subject"] == "koo.park@example.com", out["me"]
    assert out["convs"] == ["로컬 계정 시절 대화"], out
