# /tls/info 의 needs_ca 판정과 /tls/ca.crt 가 리프가 아니라 발급 CA 체인을 내리는지
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.routes import tlscert


def _openssl(*args, cwd):
    subprocess.run(["openssl", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture(scope="module")
def certs(tmp_path_factory):
    """자체서명 리프 하나, 사설 루트 CA 가 발급한 리프 하나(+fullchain)."""
    d = tmp_path_factory.mktemp("tls")
    _openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "self.key", "-out", "self.crt",
             "-days", "2", "-subj", "/CN=self.example.test", cwd=d)
    _openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.crt",
             "-days", "2", "-subj", "/CN=Private Test CA", cwd=d)
    _openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "leaf.key", "-out", "leaf.csr",
             "-subj", "/CN=leaf.example.test", cwd=d)
    _openssl("x509", "-req", "-in", "leaf.csr", "-CA", "ca.crt", "-CAkey", "ca.key", "-CAcreateserial",
             "-out", "leaf.crt", "-days", "1", cwd=d)
    (d / "fullchain.crt").write_text((d / "leaf.crt").read_text() + (d / "ca.crt").read_text())
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


def test_self_signed_needs_ca_and_serves_itself_as_ca(client, certs, monkeypatch):
    _use(monkeypatch, certs / "self.crt")
    info = client.get("/tls/info").json()
    assert info["available"] and info["self_signed"] and info["needs_ca"] and info["ca_available"]
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
    assert info["needs_ca"] is False and info["verify_error"] == ""


def test_leaf_only_private_ca_has_no_chain_until_tls_ca_path(client, certs, monkeypatch):
    _use(monkeypatch, certs / "leaf.crt")
    info = client.get("/tls/info").json()
    assert info["needs_ca"] and info["ca_available"] is False, "리프만 있으면 체인을 지어내지 않는다"
    assert client.get("/tls/ca.crt").status_code == 404
    _use(monkeypatch, certs / "leaf.crt", ca=certs / "ca.crt")
    assert client.get("/tls/info").json()["ca_available"] is True
    assert client.get("/tls/ca.crt").text.strip() == (certs / "ca.crt").read_text().strip()


def test_private_key_in_the_file_is_never_served(client, certs, tmp_path, monkeypatch):
    bad = tmp_path / "bundle.pem"
    bad.write_text((certs / "self.crt").read_text() + (certs / "self.key").read_text())
    _use(monkeypatch, bad, ca=bad)
    assert client.get("/tls/portal.crt").status_code == 404
    assert client.get("/tls/ca.crt").status_code == 404
    assert client.get("/tls/info").json()["available"] is False


def test_no_verifier_falls_back_to_self_signed_rule(client, certs, monkeypatch):
    _use(monkeypatch, certs / "fullchain.crt")
    monkeypatch.setattr(tlscert.shutil, "which", lambda _n: None)
    info = client.get("/tls/info").json()
    assert info["needs_ca"] is False and "판정 수단" in info["verify_error"]
