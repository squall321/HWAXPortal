"""RSA keystore for downstream launch tokens (RS256) + the JWKS published to verifiers.

Downstream systems verify launch tokens with the PUBLIC key fetched from
/.well-known/jwks.json — never a shared secret. Keys live in `jwt_keys_dir` as
<kid>.key (private PEM) + <kid>.pub (public PEM). In dev the active key auto-generates
if missing; in prod the keys are provisioned as secrets. Rotation = drop in a new <kid>
pair, point jwt_active_kid at it, and keep the old public key in the dir so its JWKS entry
stays available until old tokens expire.
"""

import json
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
        return self._dir / f"{kid}.key"

    def _pub_path(self, kid: str) -> Path:
        return self._dir / f"{kid}.pub"

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
