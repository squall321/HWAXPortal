# 포털이 발급한 PAT(RS256, scope=api)를 로컬 keystore 공개키로 검증해 Principal 을 돌려주는 헬퍼
"""Verify a portal-issued PAT locally (the portal is the issuer, so no JWKS round-trip).

Signature is checked with the public key for the token's `kid` from the keystore; the token
must carry `aud` containing the required audience, `scope == "api"`, be unexpired, and its
`jti` must not be in the token_store revocation denylist. Returns a Principal on success.
"""

import jwt

from app.auth.provider import Principal


def verify_pat(token: str, *, keystore, revoked_jtis, audience: str) -> Principal:
    kid = jwt.get_unverified_header(token).get("kid")
    if not kid:
        raise ValueError("PAT has no kid")
    public_pem = keystore.public_pem(kid)  # unknown kid → FileNotFoundError (treated as invalid)
    claims = jwt.decode(
        token, public_pem, algorithms=["RS256"], audience=audience,
        options={"require": ["exp", "aud", "sub", "jti"]}, leeway=30,
    )
    if claims.get("scope") != "api":
        raise ValueError("PAT is not scope=api")
    if claims["jti"] in set(revoked_jtis):
        raise ValueError("PAT revoked")
    return Principal(
        subject=claims["sub"],
        email=claims.get("email", ""),
        display_name=claims.get("name") or claims.get("email") or claims["sub"],
        groups=list(claims.get("groups") or []),
    )
