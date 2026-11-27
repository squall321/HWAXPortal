# 자동 파이프라인 서비스 토큰 — core-link 서비스 PAT 꼴(service_claims) · 15분 · jti svc-ap-<실행>-<단계>, 게이트웨이 _service_scope 가 실제로 받는 꼴인지
"""게이트웨이(HWAXMcpGateway/gateway.py)의 `_service_scope` 와 그 상수를 형제 리포 원문에서 떼어 와 이 토큰의 클레임을 넣어 본다(게이트웨이 의존을
포털 venv 에 들이지 않는다 — test_core_vocab 과 같은 방식). 형제 리포가 없으면 그 시험만 건너뛴다."""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import jwt
import pytest
from autopipe_fakes import SPEC, THERMAL, FakeAnalysis, Harness, ready_run
from cryptography.hazmat.primitives import serialization

from app.agent import ra_post as _ra_post
from app.auth.keystore import KeyStore
from app.auth.service_pat import SERVICE_AUDIENCE
from app.autopipe import token as T
from app.config import Settings

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT.parent / "HWAXMcpGateway" / "gateway.py"
NOW = 1_800_000_000
_CONSTS = ("SERVICE_AUDIENCE", "SERVICE_PURPOSE", "SERVICE_JTI_PREFIX", "SERVICE_SCOPES", "SERVICE_MAX_TTL_S", "_SERVICE_SUB_RE")


def _gateway_service_scope():
    """gateway._service_scope 와 그 상수들(형제 리포 원문)."""
    if not GW.exists():
        pytest.skip(f"형제 리포 HWAXMcpGateway 가 없다: {GW}")
    src = GW.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns: dict = {"re": re}
    got = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in _CONSTS:
            exec(compile(ast.Module(body=[node], type_ignores=[]), "gateway:const", "exec"), ns)  # noqa: S102 — 형제 리포의 우리 코드다
            got.add(node.targets[0].id)
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_service_scope"), None)
    assert fn is not None and got == set(_CONSTS), f"게이트웨이 서비스 판별이 바뀌었다 — 빠진 것 {sorted(set(_CONSTS) - got)}"
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "gateway:_service_scope", "exec"), ns)  # noqa: S102
    return ns["_service_scope"], ns


def test_클레임은_서비스_PAT_꼴이고_수명은_15분이다():
    c = T.claims("https://portal.example", "0123456789abcdef0123", "thermal", now=NOW)
    assert c["aud"] == [SERVICE_AUDIENCE] == ["mcp-gateway-service"]
    assert c["sub"] == "system:auto-pipeline" and c["pat_name"] == "service:auto-pipeline"
    assert c["scope"] == "api" and c["scopes"] == ["service"] and c["purpose"] == "service"
    assert c["jti"] == "svc-ap-0123456789ab-thermal"
    assert c["exp"] - c["iat"] == 900 and c["nbf"] == NOW - 60
    assert not {"email", "name", "groups"} & set(c), "사람 신원 칸이 없다"


def test_게이트웨이가_실제로_받는_꼴이다():
    scope, ns = _gateway_service_scope()
    c = T.claims("https://portal.example", "run1", "thermal", now=NOW)
    is_svc, got = scope(c)
    assert is_svc and got == {"job": "auto-pipeline", "jti": c["jti"]}
    assert c["jti"].startswith(ns["SERVICE_JTI_PREFIX"])
    # 처음 설계(AP-8)의 jti 'ap-…' 는 게이트웨이가 꼴 어긋남으로 401 이다 — 그래서 svc-ap-… 로 고쳤다
    is_svc, got = scope({**c, "jti": "ap-run1-thermal"})
    assert is_svc and got is None
    for k, v in (("aud", ["mcp-gateway-service", "mcp-gateway"]), ("scopes", ["service", "read"]), ("sub", "system:Auto Pipeline")):
        assert scope({**c, k: v})[1] is None, f"{k} 가 어긋나면 받지 않는다"


def test_jti_는_실행_단계에_묶이고_꼴을_벗어난_글자는_뺀다():
    assert T.jti_for("src", "heax-step_forge") == "svc-ap-src-heax-step_forge"
    assert T.jti_for("ABCDEF0123456789", "Th Ermal!") == "svc-ap-abcdef012345-thermal"


def test_발급은_포털_키로_서명하고_원장에_적지_않는다(tmp_path):
    s = Settings(_env_file=None, jwt_keys_dir=str(tmp_path / "keys"), jwt_autogen_keys=True, jwt_issuer="https://portal.example")
    ks = KeyStore(s)
    tok = T.mint(ks, s, "run1", "thermal")
    pub = serialization.load_pem_public_key(ks.public_pem(ks.active_kid).encode())
    c = jwt.decode(tok, pub, algorithms=["RS256"], audience=SERVICE_AUDIENCE, issuer="https://portal.example")
    assert c["sub"] == "system:auto-pipeline" and jwt.get_unverified_header(tok)["kid"] == ks.active_kid
    assert "record_pat(" not in inspect.getsource(T), "호출마다 찍는 토큰을 원장에 적으면 원장이 끝없이 자란다(context-notes AP-13)"


def test_발급에_실패하면_그_호출을_하지_않는다():
    class Broken:
        private_pem = "키 아님"
        active_kid = "x"
    assert T.mint(Broken(), Settings(_env_file=None), "run1", "thermal") is None


def test_엔진은_호출마다_그_단계의_토큰을_싣는다(tmp_path, monkeypatch):
    monkeypatch.setattr(_ra_post, "PATH", tmp_path / "없음.json")
    s = Settings(_env_file=None, jwt_keys_dir=str(tmp_path / "keys"), jwt_autogen_keys=True, jwt_issuer="https://portal.example")
    ks = KeyStore(s)
    h = Harness(tmp_path, FakeAnalysis(THERMAL, sync=True))
    try:
        h.engine._mint = lambda run, step: T.mint(ks, s, run, step)
        h.rule(SPEC)
        run = ready_run(h)
        jtis = [jwt.decode(t, options={"verify_signature": False})["jti"] for t in h.gw.tokens]
        assert jtis[0] == "svc-ap-src-heax-step_forge", "원천 감지"
        assert f"svc-ap-{run['id'][:12]}-thermal" in jtis, "해석 단계 — 실행 · 단계에 묶인다"
        assert all(j.startswith("svc-") for j in jtis)
    finally:
        h.close()
