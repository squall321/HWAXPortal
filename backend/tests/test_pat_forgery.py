# PAT 위조 — **토큰이 준 `kid` 를 경로로 쓰면 임의 신원·권한이 된다**(2026-09-15 7차 감사)
#
# `kid` 는 **검증 전의** 헤더에서 온다. 즉 공격자가 정하는 값이다. 그대로
# `keystore/<kid>.pub` 에 넣으면 `../` 로 keystore 밖 아무 `.pub` 를 검증키로 쓸 수 있다.
# 공격자가 자기 공개키를 아무 데나 심고(업로드 스테이징 등) 그 경로를 가리키면,
# **자기 개인키로 서명한 PAT 가 통과한다** — `sub`·`email`·`groups` 를 마음대로 적는다.
#
# 게이트웨이는 JWKS(발행 키목록 대조)라 안 뚫렸다. **포털의 로컬 검증만** 뚫렸고,
# 그 경로를 `principal_pat_or_session` 을 쓰는 전부(챗·업로드·대화·심의·docx)가 지난다.
import datetime
import tempfile
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.keystore import KeyStore
from app.auth.pat_verify import verify_pat
from app.config import Settings


@pytest.fixture()
def ks(tmp_path):
    return KeyStore(Settings(jwt_keys_dir=str(tmp_path / "keys")))


def _attacker_key(where: Path):
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_bytes(k.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())


def _forge(priv, kid, **claims):
    now = datetime.datetime.now(datetime.UTC)
    body = {"sub": "intruder@evil.com", "email": "boss@corp.com",
            "groups": ["portal-admin"], "scope": "api", "aud": "hwax-chat",
            "jti": "forged", "exp": now + datetime.timedelta(days=1), **claims}
    return jwt.encode(body, priv, algorithm="RS256", headers={"kid": kid})


def test_kid_로_keystore_를_벗어날_수_없다(ks):
    """실측으로 계정도 없는 신원이 `portal-admin` 으로 수락됐다."""
    priv = _attacker_key(ks._dir.parent / "staging" / "evil.pub")
    tok = _forge(priv, "../staging/evil")
    with pytest.raises(Exception) as e:
        verify_pat(tok, keystore=ks, revoked_jtis=[], audience="hwax-chat")
    assert "식별자" in str(e.value) or isinstance(e.value, ValueError)


def test_경로_모양은_전부_거절한다(ks):
    priv = _attacker_key(Path(tempfile.mkdtemp()) / "x.pub")
    for kid in ("../../etc/passwd", "/tmp/evil", "a/b", "evil\x00x", "", "." * 200):
        with pytest.raises(Exception):
            verify_pat(_forge(priv, kid), keystore=ks, revoked_jtis=[], audience="hwax-chat")


def test_진짜_키로_발급한_PAT_은_그대로_돈다(ks):
    """가드가 너무 세면 정상 발급이 막힌다 — 그 짝을 함께 고정한다."""
    now = datetime.datetime.now(datetime.UTC)
    tok = jwt.encode({"sub": "u1", "email": "u1@corp.com", "groups": [],
                      "scope": "api", "aud": "hwax-chat", "jti": "ok",
                      "exp": now + datetime.timedelta(days=1)},
                     ks._private_pem, algorithm="RS256",
                     headers={"kid": ks._active_kid})
    p = verify_pat(tok, keystore=ks, revoked_jtis=[], audience="hwax-chat")
    assert p.subject == "u1" and p.email == "u1@corp.com"
