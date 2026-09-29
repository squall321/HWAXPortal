# SAML ACS/SLS 경로를 설정으로 — AD-SSO 등록값(/auth/callback)과 맞춘다(4차 변경 요청, 2026-09-29)
#
# ADFS 는 ACS 를 인증 **전에** 검증하지 않는다 — 어긋나면 로그인 뒤 일반 오류 페이지로 끝나고 SP 에는 요청이 한 번도
# 오지 않는다. 그래서 ① 기본값은 종전 그대로 ② 경로를 바꾸면 메타데이터·AuthnRequest·검증이 전부 그 경로를 쓰고
# ③ /auth/callback 으로 온 SAML POST 가 실제로 로그인된다는 것을 mock IdP 로 끝까지 돌려 본다.
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import SAML_ACS_ROUTES, Settings, startup_warnings

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
START = (ROOT / "infra/scripts/start.sh").read_text(encoding="utf-8")


def _s(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_기본값은_종전_경로_그대로다():
    s = _s(public_base_url="https://hwax.example")
    assert s.saml_acs_url == "https://hwax.example/auth/saml/acs"
    assert s.saml_sls_url == "https://hwax.example/auth/saml/sls"


def test_경로를_설정으로_바꾼다():
    s = _s(public_base_url="https://hwax.example", saml_acs_path="/auth/callback", saml_sls_path="/auth/logout")
    assert s.saml_acs_url == "https://hwax.example/auth/callback" and s.saml_sls_url == "https://hwax.example/auth/logout"


@pytest.mark.parametrize("bad", ["auth/callback", "https://evil.example/auth/callback", "/auth/ callback", ""])
def test_경로가_아닌_값은_기동에서_막는다(bad):
    with pytest.raises(ValueError):
        _s(saml_acs_path=bad)


def test_받을_라우트가_없는_ACS_경로는_경고한다():
    codes = lambda **kw: [c for c, _ in startup_warnings(_s(**kw))]           # noqa: E731
    assert "saml_acs_route" in codes(auth_provider="saml", saml_acs_path="/auth/acs", session_secret="x" * 40)
    for ok in SAML_ACS_ROUTES:
        assert "saml_acs_route" not in codes(auth_provider="saml", saml_acs_path=ok, session_secret="x" * 40)
    assert "saml_acs_route" not in codes(auth_provider="oidc", saml_acs_path="/auth/acs")   # SAML 이 아니면 무관


def test_운영인데_FRONTEND_URL_이_localhost_면_경고한다():
    codes = lambda **kw: [c for c, _ in startup_warnings(_s(**kw))]           # noqa: E731
    assert "frontend_localhost" in codes(app_env="prod", frontend_url="http://localhost:5283")
    assert "frontend_localhost" in codes(app_env="prod", frontend_url="http://127.0.0.1:8088")
    assert "frontend_localhost" not in codes(app_env="prod", frontend_url="https://hwax.example")
    assert "frontend_localhost" not in codes(app_env="dev", frontend_url="http://localhost:5283")


# ── start.sh: SAML_* 를 명시해서 넘긴다(호스트 env 상속에만 기대지 않는다) ────────────────────────────
def _saml_envs_block() -> str:
    i = START.index("  SAML_ENVS=()")
    return START[i:START.index("  done\n", i) + len("  done\n")]


def test_start_sh_는_SAML_설정을_컨테이너에_명시해서_넘긴다():
    script = ("set -euo pipefail\n" + _saml_envs_block() + 'printf "%s\\n" ${SAML_ENVS[@]+"${SAML_ENVS[@]}"}\n')
    env = {"PATH": os.environ["PATH"], "SAML_ACS_PATH": "/auth/callback",
           "SAML_SP_ENTITY_ID": "https://hwax.example", "SAML_MOCK_IDP_ENABLED": "true"}
    out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    args = out.stdout.split("\n")
    assert "SAML_ACS_PATH=/auth/callback" in args and "SAML_SP_ENTITY_ID=https://hwax.example" in args
    assert not any(a.startswith("SAML_MOCK_IDP_ENABLED") for a in args), "mock IdP 는 아래에서 false 로 고정한다"
    empty = subprocess.run(["bash", "-c", script], env={"PATH": os.environ["PATH"]}, capture_output=True, text=True)
    assert empty.returncode == 0 and empty.stdout.strip() == "", "SAML_* 가 없는 박스에서 set -e 로 죽으면 안 된다"
    assert '${SAML_ENVS[@]+"${SAML_ENVS[@]}"}' in START[START.index('"$APPTAINER" instance start'):]


# ── 끝까지: mock IdP → /auth/callback 으로 SAML POST → 로그인 ─────────────────────────────────────────
_E2E = r'''
import json, re, sys
from urllib.parse import urlsplit
from fastapi.testclient import TestClient
from app.main import app

def path(u):
    p = urlsplit(u); return p.path + ("?" + p.query if p.query else "")

out = {}
with TestClient(app, base_url="http://localhost:5283") as c:
    md = c.get("/auth/saml/metadata")
    out["metadata_acs"] = re.search(r'AssertionConsumerService[^>]*Location="([^"]+)"', md.text).group(1)
    r = c.get("/auth/login", follow_redirects=False)
    r2 = c.get(path(r.headers["location"]), follow_redirects=False)
    html = r2.text.replace("&amp;", "&")
    action = re.search(r'action="([^"]+)"', html).group(1)
    data = {"SAMLResponse": re.search(r'name="SAMLResponse" value="([^"]+)"', html).group(1)}
    m = re.search(r'name="RelayState" value="([^"]+)"', html)
    if m:
        data["RelayState"] = m.group(1)
    out["posted_to"] = action
    r3 = c.post(path(action), data=data, follow_redirects=False)
    out["status"] = r3.status_code
    out["cookies"] = sorted(r3.cookies.keys())
    out["location"] = r3.headers.get("location", "")
    out["body"] = r3.text[:300]
print(json.dumps(out))
'''


@pytest.mark.skipif(not ((BACKEND / "secrets/saml/sp.key").exists() and (BACKEND / "secrets/saml/idp.key").exists()),
                    reason="개발용 SAML 키(backend/secrets/saml/*.key)가 없다 — 추적 파일이 아니다(scripts/gen_dev_certs.py)")
def test_mock_IdP_로_callback_경로에서_끝까지_로그인된다(tmp_path):
    env = {**os.environ,
           "AUTH_PROVIDER": "saml", "APP_ENV": "dev", "SAML_MOCK_IDP_ENABLED": "true",
           "PUBLIC_BASE_URL": "http://localhost:5283", "FRONTEND_URL": "http://localhost:5283",
           "SAML_ACS_PATH": "/auth/callback", "SESSION_SECRET": "t" * 48, "COOKIE_SECURE": "false",
           # 기동이 실 저장소를 건드리지 않게 전부 임시로
           "USER_STORE_PATH": str(tmp_path / "users.sqlite"), "TOKEN_STORE_PATH": str(tmp_path / "tok.sqlite"),
           "CONV_STORE_PATH": str(tmp_path / "conv.sqlite"), "PROCEDURES_STORE_PATH": str(tmp_path / "proc.sqlite"),
           "AGENT_AUDIT_LOG_PATH": str(tmp_path / "audit.sqlite"), "JWT_KEYS_DIR": str(tmp_path / "jwt"),
           "JWT_AUTOGEN_KEYS": "true", "PROCEDURES_ARTIFACT_ROOT": str(tmp_path / "art"),
           "DELIB_ARCHIVE_ROOT": str(tmp_path / "delib"), "UPLOAD_STAGING_DIR": str(tmp_path / "stage")}
    r = subprocess.run([sys.executable, "-c", _E2E], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["metadata_acs"] == "http://localhost:5283/auth/callback", "메타데이터가 등록값을 광고해야 한다"
    assert out["posted_to"] == "http://localhost:5283/auth/callback", "AuthnRequest 의 ACS 가 설정 경로여야 한다"
    assert out["status"] in (302, 303), out
    assert out["location"].startswith("http://localhost:5283"), out
    assert out["cookies"], f"세션 쿠키가 안 실렸다: {out}"
