"""RSA keystore for downstream launch tokens (RS256) + the JWKS published to verifiers.

Downstream systems verify launch tokens with the PUBLIC key fetched from
/.well-known/jwks.json — never a shared secret. Keys live in `jwt_keys_dir` as
<kid>.key (private PEM) + <kid>.pub (public PEM). In dev the active key auto-generates
if missing; in prod the keys are provisioned as secrets. Rotation = drop in a new <kid>
pair, point jwt_active_kid at it, and keep the old public key in the dir so its JWKS entry
stays available until old tokens expire.
"""

import json
import re
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import Settings


class KeyStore:
    def __init__(self, settings: Settings) -> None:
        self._dir = Path(settings.resolve(settings.jwt_keys_dir))
        self._active_kid = settings.jwt_active_kid
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ensure_active_key(settings)
        self._private_pem = self._priv_path(self._active_kid).read_text()

    def _priv_path(self, kid: str) -> Path:
        # 공개키 쪽과 같은 잣대 — 여기는 우리가 만든 kid 만 들어오지만, 두 곳이 다르면
        # 다음 사람이 "여긴 검사 안 하네" 로 읽는다.
        return self._dir / f"{self._check_kid(kid)}.key"

    # 키 id 는 **식별자**다 — 경로가 아니다. 소문자·숫자·`.`·`_`·`-` 만.
    _KID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

    @classmethod
    def _check_kid(cls, kid: str) -> str:
        """⚠ **토큰이 준 `kid` 를 그대로 경로에 넣으면 안 된다.**

        `kid` 는 검증 **전의** 헤더에서 온다 — 즉 공격자가 정하는 값이다. 그대로
        `self._dir / f"{kid}.pub"` 에 넣으면 `../` 로 keystore 밖의 아무 `.pub` 를
        검증키로 쓸 수 있다. 공격자가 자기 공개키를 아무 데나 심고(업로드 스테이징 등)
        그 경로를 `kid` 로 가리키면, **자기 개인키로 서명한 위조 PAT 가 통과한다** —
        `sub`·`email`·`groups` 를 마음대로 적을 수 있으므로 곧 임의 신원·권한 탈취다.
        실측(2026-09-15 7차 감사): 계정도 없는 신원이 `portal-admin` 으로 수락됐다.
        게이트웨이는 JWKS(발행 키목록 대조)라 안 뚫렸고 **포털의 로컬 검증만** 뚫렸다.
        """
        if not kid or not cls._KID.match(kid):
            raise ValueError(f"키 id 가 식별자 모양이 아니다: {kid!r}")
        return kid

    def _pub_path(self, kid: str) -> Path:
        return self._dir / f"{self._check_kid(kid)}.pub"

    def _ensure_active_key(self, settings: Settings) -> None:
        if self._priv_path(self._active_kid).exists():
            return
        if settings.app_env != "dev" and not settings.jwt_autogen_keys:
            raise RuntimeError(
                f"JWT key '{self._active_kid}' missing in {self._dir} "
                "(provision keys, or set JWT_AUTOGEN_KEYS=true for a single-instance deploy)"
            )
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._priv_path(self._active_kid).write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        self._pub_path(self._active_kid).write_bytes(
            key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    @property
    def active_kid(self) -> str:
        return self._active_kid

    @property
    def private_pem(self) -> str:
        return self._private_pem

    def public_pem(self, kid: str) -> str:
        return self._pub_path(kid).read_text()

    def jwks(self) -> dict:
        """All currently-published public keys as a JWK set (current + any retained old kids)."""
        keys = []
        for pub in sorted(self._dir.glob("*.pub")):
            kid = pub.stem
            public_key = serialization.load_pem_public_key(pub.read_bytes())
            jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
            jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
            keys.append(jwk)
        return {"keys": keys}
