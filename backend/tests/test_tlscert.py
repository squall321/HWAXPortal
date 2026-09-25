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
    # root → intermediate → leaf2 (표준 사내 PKI 모양). nginx 는 leaf2+int 를 서빙하고 루트는 따로 있다.
    from cryptography.hazmat.primitives.asymmetric import rsa
    int_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    int_cert = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Private Intermediate CA")]))
                .issuer_name(ca_cert.subject).public_key(int_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=2))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .sign(ca_key, hashes.SHA256()))
    leaf2 = (x509.CertificateBuilder()
             .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "leaf2.example.test")]))
             .issuer_name(int_cert.subject).public_key(leaf_key.public_key())
             .serial_number(x509.random_serial_number())
             .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=1))
             .sign(int_key, hashes.SHA256()))
    pem = serialization.Encoding.PEM
    (d / "int.crt").write_bytes(int_cert.public_bytes(pem))
    (d / "leaf2-int.crt").write_bytes(leaf2.public_bytes(pem) + int_cert.public_bytes(pem))
    (d / "leaf2-int-root.crt").write_bytes(leaf2.public_bytes(pem) + int_cert.public_bytes(pem) + (d / "ca.crt").read_bytes())
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
    monkeypatch.setattr(tlscert, "_CACHE", {"key": None, "at": 0.0, "value": None})


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
    assert info["ca_available"] is False, "판정 못 한 후보를 '준비됨' 으로 내지 않는다(3라운드 회귀)"


def test_relative_env_paths_anchor_at_repo_root_like_nginx_does(monkeypatch):
    """컨테이너 백엔드의 CWD 는 /workspace/backend — 앵커 없이 쓰면 nginx 는 찾는 파일을 백엔드만 못 찾는다."""
    assert tlscert._anchor("infra/tls/hwax.crt") == tlscert._REPO_ROOT / "infra/tls/hwax.crt"
    assert tlscert._anchor("/etc/ssl/x.crt").as_posix() == "/etc/ssl/x.crt"
    assert tlscert._REPO_ROOT.joinpath("infra", "tls").is_dir()


def test_info_and_ca_share_one_cached_state(client, certs, monkeypatch):
    _use(monkeypatch, certs / "self.crt")
    calls = []
    real = tlscert._verify
    monkeypatch.setattr(tlscert, "_verify", lambda pem, b: (calls.append(1), real(pem, b))[1])
    client.get("/tls/info"); client.get("/tls/info"); client.get("/tls/ca.crt")
    assert len(calls) == 2, "첫 요청의 공개루트 판정 + CA 후보 검증 뒤로는 서브프로세스가 없다(/tls/ca.crt 도 같은 상태)"
    monkeypatch.setattr(tlscert, "_TTL_S", 0)                       # 시간이 가면 다시 판정한다(만료가 보이게)
    client.get("/tls/info")
    assert len(calls) == 4


def test_transient_openssl_failure_is_not_cached(client, certs, monkeypatch):
    """OOM·타임아웃으로 한 번 실패한 판정을 고정하면 사내 CA 포털이 '공개 CA 정상' 으로 굳는다(2라운드 검토)."""
    _use(monkeypatch, certs / "fullchain.crt")
    real = tlscert.subprocess.run
    state = {"fail": True}
    def flaky(*a, **k):
        if state["fail"]:
            state["fail"] = False
            raise OSError("fork failed")
        return real(*a, **k)
    monkeypatch.setattr(tlscert.subprocess, "run", flaky)
    first = client.get("/tls/info").json()
    assert first["verified"] is False and "실행 실패" in first["verify_error"]
    monkeypatch.setattr(tlscert, "_FAIL_TTL_S", 0)                 # 짧은 보류가 지난 뒤
    second = client.get("/tls/info").json()
    assert second["verified"] is True and second["needs_ca"] is True and second["ca_available"] is True


def test_server_sends_intermediate_and_root_is_in_tls_ca_path(client, certs, monkeypatch):
    """표준 사내 PKI: nginx 가 leaf+int 를 서빙, 루트만 TLS_CA_PATH — Node 는 루트만 심으면 된다(검토 실측).
    후보 검증이 서빙 체인을 -untrusted 로 안 주면 이 정상 구성을 '연결 불가' 로 판정한다(1라운드 수정의 회귀)."""
    _use(monkeypatch, certs / "leaf2-int.crt", ca=certs / "ca.crt")
    info = client.get("/tls/info").json()
    assert info["needs_ca"] and info["ca_available"] and info["verified"], info
    assert client.get("/tls/ca.crt").text.strip() == (certs / "ca.crt").read_text().strip()
    # 루트까지 붙은 fullchain 이면 TLS_CA_PATH 없이도 체인부(int+root)가 준비된다.
    _use(monkeypatch, certs / "leaf2-int-root.crt")
    info = client.get("/tls/info").json()
    assert info["ca_available"] and info["verified"]
    served = client.get("/tls/ca.crt").text
    assert served.strip() == ((certs / "int.crt").read_text() + (certs / "ca.crt").read_text()).strip(), "체인부 그대로(int+root)"
    # 중간 CA 까지만 있고 루트가 없으면 Node 도 못 믿는다 — 안내가 '루트' 를 말한다.
    _use(monkeypatch, certs / "leaf2-int.crt")
    info = client.get("/tls/info").json()
    assert info["ca_available"] is False and "루트" in info["ca_error"]
    assert client.get("/tls/ca.crt").status_code == 404


def test_expired_leaf_keeps_info_and_ca_endpoint_consistent(client, certs, monkeypatch):
    _use(monkeypatch, certs / "expired-fullchain.crt", bundle=certs / "ca.crt")
    info = client.get("/tls/info").json()
    assert info["expired"] and info["ca_available"] is False and "expired" in info["ca_error"]
    assert client.get("/tls/ca.crt").status_code == 404


def test_ca_candidate_check_failure_is_unknown_not_ready(client, certs, monkeypatch):
    """공개루트 판정은 됐는데 CA 후보 검증(둘째 openssl)만 실패한 순간 — 검증 안 된 TLS_CA_PATH 를
    '준비됨' 으로 60초 고정하던 3라운드 회귀. 이제 verified=false·ca_available=false 이고 곧 다시 판정한다."""
    # 자체서명이 아닌 리프(자체서명이면 자기 자신이 다음 후보로 통해 버린다) + 엉뚱한 TLS_CA_PATH.
    _use(monkeypatch, certs / "leaf.crt", ca=certs / "other.crt")
    real = tlscert.subprocess.run
    n = {"i": 0}
    def second_fails(*a, **k):
        n["i"] += 1
        if n["i"] == 2:
            raise tlscert.subprocess.TimeoutExpired(cmd="openssl", timeout=10)
        return real(*a, **k)
    monkeypatch.setattr(tlscert.subprocess, "run", second_fails)
    first = client.get("/tls/info").json()
    assert first["verified"] is False and first["ca_available"] is False and "판정 수단" in first["ca_error"]
    assert client.get("/tls/ca.crt").status_code == 404
    monkeypatch.setattr(tlscert, "_FAIL_TTL_S", 0)
    second = client.get("/tls/info").json()
    assert second["verified"] is True and second["ca_available"] is False, "엉뚱한 TLS_CA_PATH 는 판정 뒤에도 준비됨이 아니다"
    assert "TLS_CA_PATH" in second["ca_error"]


def test_persistent_failure_is_held_briefly_not_rerun_per_request(client, certs, monkeypatch):
    _use(monkeypatch, certs / "self.crt")
    calls = []
    def dead(*a, **k):
        calls.append(1); raise OSError("fork failed")
    monkeypatch.setattr(tlscert.subprocess, "run", dead)
    client.get("/tls/info"); client.get("/tls/info"); client.get("/tls/ca.crt")
    assert len(calls) == 2, "첫 요청의 두 판정(공개루트·CA 후보) 뒤로는 실패가 이어져도 요청마다 되살리지 않는다(짧은 TTL)"


def test_leaf_only_guidance_asks_for_the_issuing_chain_not_the_root_alone(client, certs, monkeypatch):
    """리프만 서빙 + TLS_CA_PATH=루트 는 Node 도 못 믿는다(중간 CA 가 어디에도 없다) — 안내가 '루트' 를 시키면 안 된다."""
    leaf2 = certs / "leaf2.crt"
    leaf2.write_text((certs / "leaf2-int.crt").read_text().split("-----END CERTIFICATE-----")[0] + "-----END CERTIFICATE-----\n")
    _use(monkeypatch, leaf2)
    info = client.get("/tls/info").json()
    assert info["ca_available"] is False and "중간 CA + 루트" in info["ca_error"] and "루트만으로는 안 된다" in info["ca_error"]
    _use(monkeypatch, leaf2, ca=certs / "ca.crt")
    info = client.get("/tls/info").json()
    assert info["ca_available"] is False and "중간 CA 와 루트" in info["ca_error"]
    int_root = certs / "int-root.crt"
    int_root.write_text((certs / "int.crt").read_text() + (certs / "ca.crt").read_text())
    _use(monkeypatch, leaf2, ca=int_root)
    assert client.get("/tls/info").json()["ca_available"] is True


def test_chain_expiry_counts_as_expired_and_gets_no_issuer_hint(client, certs, monkeypatch):
    _use(monkeypatch, certs / "expired-fullchain.crt", bundle=certs / "ca.crt")
    info = client.get("/tls/info").json()
    assert info["expired"] is True and "루트" not in info["ca_error"], "만료에 '루트까지' 처방을 붙이지 않는다"
