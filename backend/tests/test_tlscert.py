# /tls/info 의 needs_ca 판정과 /tls/ca.crt 가 리프가 아니라 발급 CA 체인을 내리는지
import datetime as dt
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.routes import tlscert


def _openssl(*args, cwd):
    subprocess.run(["openssl", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture(scope="module")
def certs(tmp_path_factory):
    """자체서명 리프 하나, 사설 루트 CA 가 발급한 리프 하나(+fullchain), 같은 CA 의 만료 리프, 남의 CA."""
    d = tmp_path_factory.mktemp("tls")
    _openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "self.key", "-out", "self.crt",
             "-days", "2", "-subj", "/CN=self.example.test", cwd=d)
    _openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.crt",
             "-days", "2", "-subj", "/CN=Private Test CA", cwd=d)
    _openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "other.key", "-out", "other.crt",
             "-days", "2", "-subj", "/CN=Other CA", cwd=d)
    _openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "leaf.key", "-out", "leaf.csr",
             "-subj", "/CN=leaf.example.test", cwd=d)
    _openssl("x509", "-req", "-in", "leaf.csr", "-CA", "ca.crt", "-CAkey", "ca.key", "-CAcreateserial",
             "-out", "leaf.crt", "-days", "1", cwd=d)
    (d / "fullchain.crt").write_text((d / "leaf.crt").read_text() + (d / "ca.crt").read_text())
    # 만료 리프 — openssl 3.0 은 과거 유효기간을 못 주므로 cryptography 로 같은 CA 키로 서명한다.
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.x509.oid import NameOID
    ca_key = serialization.load_pem_private_key((d / "ca.key").read_bytes(), None)
    ca_cert = x509.load_pem_x509_certificate((d / "ca.crt").read_bytes())
    leaf_key = serialization.load_pem_private_key((d / "leaf.key").read_bytes(), None)
    now = dt.datetime.now(dt.timezone.utc)
    exp = (x509.CertificateBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "expired.example.test")]))
           .issuer_name(ca_cert.subject).public_key(leaf_key.public_key())
           .serial_number(x509.random_serial_number())
           .not_valid_before(now - dt.timedelta(days=10)).not_valid_after(now - dt.timedelta(days=1))
           .sign(ca_key, hashes.SHA256()))
    (d / "expired-fullchain.crt").write_bytes(exp.public_bytes(serialization.Encoding.PEM) + (d / "ca.crt").read_bytes())
    (d / "ca.der").write_bytes(ca_cert.public_bytes(serialization.Encoding.DER))
    return d


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(tlscert.router)
    return TestClient(app)


def _use(monkeypatch, cert, ca=None, bundle=None):
    monkeypatch.setattr(tlscert, "_CERT_PATH", cert)
    monkeypatch.setattr(tlscert, "_CA_PATH", ca)
    monkeypatch.setattr(tlscert, "_TRUST_BUNDLE", str(bundle) if bundle else None)
    monkeypatch.setattr(tlscert, "_INFO_CACHE", {"key": None, "value": None})


def test_self_signed_needs_ca_and_serves_itself_as_ca(client, certs, monkeypatch):
    _use(monkeypatch, certs / "self.crt")
    info = client.get("/tls/info").json()
    assert info["available"] and info["self_signed"] and info["needs_ca"] and info["ca_available"]
    assert info["verified"] and not info["expired"]
    assert client.get("/tls/ca.crt").text == (certs / "self.crt").read_text()


def test_private_ca_fullchain_needs_ca_and_serves_the_ca_not_the_leaf(client, certs, monkeypatch):
    # 종전 판정(self_signed)은 여기서 False 라 안내가 안 떴다 — Node 는 그래도 죽는다.
    _use(monkeypatch, certs / "fullchain.crt")
    info = client.get("/tls/info").json()
    assert not info["self_signed"] and info["needs_ca"] and info["ca_available"]
    ca = client.get("/tls/ca.crt").text
    assert ca.strip() == (certs / "ca.crt").read_text().strip()
    assert "leaf" not in ca and client.get("/tls/portal.crt").text == (certs / "fullchain.crt").read_text()


def test_chain_that_reaches_the_trust_bundle_does_not_need_ca(client, certs, monkeypatch):
    _use(monkeypatch, certs / "fullchain.crt", bundle=certs / "ca.crt")
    info = client.get("/tls/info").json()
    assert info["needs_ca"] is False and info["verify_error"] == "" and info["verified"]


def test_leaf_only_private_ca_has_no_chain_until_tls_ca_path(client, certs, monkeypatch):
    _use(monkeypatch, certs / "leaf.crt")
    info = client.get("/tls/info").json()
    assert info["needs_ca"] and info["ca_available"] is False, "리프만 있으면 체인을 지어내지 않는다"
    assert "리프만" in info["ca_error"]
    assert client.get("/tls/ca.crt").status_code == 404
    _use(monkeypatch, certs / "leaf.crt", ca=certs / "ca.crt")
    assert client.get("/tls/info").json()["ca_available"] is True
    assert client.get("/tls/ca.crt").text.strip() == (certs / "ca.crt").read_text().strip()


def test_wrong_tls_ca_path_is_not_reported_ready(client, certs, monkeypatch):
    """엉뚱한 CA(리프를 검증 못 함)를 '준비됨' 으로 내면 사용자는 심고도 같은 오류를 만난다."""
    _use(monkeypatch, certs / "leaf.crt", ca=certs / "other.crt")
    info = client.get("/tls/info").json()
    assert info["ca_available"] is False and "TLS_CA_PATH" in info["ca_error"] and "검증하지 못한다" in info["ca_error"]
    assert client.get("/tls/ca.crt").status_code == 404


def test_unreadable_or_binary_tls_ca_path_is_named_not_silently_ignored(client, certs, monkeypatch):
    _use(monkeypatch, certs / "fullchain.crt", ca=certs / "nope.crt")
    info = client.get("/tls/info").json()
    assert info["ca_available"] is False and "TLS_CA_PATH 를 읽지 못했다" in info["ca_error"]
    _use(monkeypatch, certs / "fullchain.crt", ca=certs / "ca.der")           # DER — 종전엔 500 이었다
    r = client.get("/tls/ca.crt")
    assert r.status_code == 404 and client.get("/tls/info").status_code == 200


def test_expired_leaf_is_flagged_not_prescribed_a_ca(client, certs, monkeypatch):
    _use(monkeypatch, certs / "expired-fullchain.crt", bundle=certs / "ca.crt")
    info = client.get("/tls/info").json()
    assert info["expired"] is True and "expired" in info["verify_error"]


def test_verify_error_never_carries_server_paths(client, certs, monkeypatch):
    _use(monkeypatch, certs / "self.crt")
    info = client.get("/tls/info").json()
    assert "/tmp" not in info["verify_error"] and str(certs) not in info["verify_error"]


def test_private_key_in_the_file_is_never_served(client, certs, tmp_path, monkeypatch):
    bad = tmp_path / "bundle.pem"
    bad.write_text((certs / "self.crt").read_text() + (certs / "self.key").read_text())
    _use(monkeypatch, bad, ca=bad)
    assert client.get("/tls/portal.crt").status_code == 404
    assert client.get("/tls/ca.crt").status_code == 404
    assert client.get("/tls/info").json()["available"] is False


def test_no_verifier_falls_back_to_self_signed_rule_and_says_so(client, certs, monkeypatch):
    _use(monkeypatch, certs / "fullchain.crt")
    monkeypatch.setattr(tlscert.shutil, "which", lambda _n: None)
    info = client.get("/tls/info").json()
    assert info["needs_ca"] is False and info["verified"] is False and "판정 수단" in info["verify_error"]


def test_relative_env_paths_anchor_at_repo_root_like_nginx_does(monkeypatch):
    """컨테이너 백엔드의 CWD 는 /workspace/backend — 앵커 없이 쓰면 nginx 는 찾는 파일을 백엔드만 못 찾는다."""
    assert tlscert._anchor("infra/tls/hwax.crt") == tlscert._REPO_ROOT / "infra/tls/hwax.crt"
    assert tlscert._anchor("/etc/ssl/x.crt").as_posix() == "/etc/ssl/x.crt"
    assert tlscert._REPO_ROOT.joinpath("infra", "tls").is_dir()


def test_info_is_cached_by_file_mtime(client, certs, monkeypatch):
    _use(monkeypatch, certs / "self.crt")
    calls = []
    real = tlscert._verify
    monkeypatch.setattr(tlscert, "_verify", lambda pem, b: (calls.append(1), real(pem, b))[1])
    client.get("/tls/info"); client.get("/tls/info")
    assert len(calls) == 2, "첫 요청의 공개루트 판정 + CA 후보 검증 뒤로는 서브프로세스가 없다"
