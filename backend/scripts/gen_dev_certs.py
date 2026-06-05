"""Generate dev SAML keypairs + the mock-IdP metadata.

Creates two self-signed RSA keypairs:
  - SP:      secrets/saml/sp.key   + config/saml/sp.crt          (portal's SP signing/cert)
  - mock IdP: secrets/saml/idp.key + config/saml/dev/idp.crt     (dev IdP signing)
and writes config/saml/dev/mock_idp_metadata.xml so the SP trusts the mock IdP.

These are DEV fixtures only (gitignored private keys). At go-live the SP keypair is
reissued for prod and the mock IdP metadata is replaced by the real Samsung AD metadata.

Run:  backend/.venv/bin/python backend/scripts/gen_dev_certs.py [--force]
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

BACKEND = Path(__file__).resolve().parent.parent
FORCE = "--force" in sys.argv


def _keypair(common_name: str) -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    # Fixed validity window (no Date.now dependency for reproducibility across runs is N/A here).
    not_before = datetime(2024, 1, 1, tzinfo=timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_before + timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return key_pem, cert_pem


def _write(rel: str, data: bytes) -> None:
    path = BACKEND / rel
    if path.exists() and not FORCE:
        print(f"  skip (exists): {rel}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"  wrote: {rel}")


def _cert_body(cert_pem: bytes) -> str:
    """Base64 cert body (no PEM header/footer) for embedding in SAML metadata."""
    lines = cert_pem.decode().strip().splitlines()
    return "".join(line for line in lines if "CERTIFICATE" not in line)


def main() -> None:
    print("Generating dev SAML keypairs…")
    sp_key, sp_crt = _keypair("hwax-portal-sp")
    idp_key, idp_crt = _keypair("hwax-mock-idp")

    _write("secrets/saml/sp.key", sp_key)
    _write("config/saml/sp.crt", sp_crt)
    _write("secrets/saml/idp.key", idp_key)
    _write("config/saml/dev/idp.crt", idp_crt)

    # Dev public origin = the Vite proxy (5283), where the browser reaches the portal.
    idp_entity = "http://localhost:5283/auth/mock-idp"
    sso_url = "http://localhost:5283/auth/mock-idp/sso"
    metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{idp_entity}">
  <IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <KeyDescriptor use="signing">
      <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
        <X509Data>
          <X509Certificate>{_cert_body(idp_crt)}</X509Certificate>
        </X509Data>
      </KeyInfo>
    </KeyDescriptor>
    <NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</NameIDFormat>
    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="{sso_url}"/>
    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{sso_url}"/>
  </IDPSSODescriptor>
</EntityDescriptor>
"""
    _write("config/saml/dev/mock_idp_metadata.xml", metadata.encode())
    print("Done.")


if __name__ == "__main__":
    main()
