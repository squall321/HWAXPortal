"""포털 TLS 인증서 배포 — 개인 Claude(Node)가 이 포털을 신뢰하게 만드는 용도.

브라우저는 경고를 누르면 통과하지만 Node(mcp-remote·claude mcp add --transport http)는 눌러 줄
사람이 없어 자체서명이면 SELF_SIGNED_CERT_IN_CHAIN, 사내 CA 면 UNABLE_TO_VERIFY_LEAF_SIGNATURE 로
죽는다 — "웹은 되는데 MCP 만 안 되는" 증상의 원인이다. 해결은 NODE_EXTRA_CA_CERTS 로 **발급 CA**
를 가리키는 것이라, 받을 곳이 필요하다.

판정은 "자체서명인가" 가 아니라 **"체인이 공개 루트에 닿는가"**(needs_ca) 다. 자체서명은 그 한
경우고, 사내 CA 로 발급된 인증서도 Node 의 번들에는 없어 똑같이 추가 CA 가 필요하다. 종전 필드
`self_signed` 는 옛 프론트를 위해 남긴다.

내려 주는 것도 리프가 아니라 **발급 CA 체인**이다(`/tls/ca.crt`). 리프를 신뢰 목록에 넣으면
갱신 때마다 사용자 PC 를 다시 만져야 하지만, CA 를 넣으면 그 CA 가 새로 발급한 리프도 통한다.
자체서명 리프는 스스로가 CA 라 그대로 내려 준다.

⚠ 배포하는 것은 **인증서(.crt)뿐이다.** 개인키(.key)는 어떤 경로로도 노출하지 않는다.
인증서는 TLS 핸드셰이크에서 이미 누구에게나 평문으로 전달되는 공개 정보다.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

router = APIRouter(tags=["tls"])

# nginx 가 읽는 것과 같은 기본 경로(gen-nginx-conf.sh 의 TLS_CERT_PATH 기본값).
# 백엔드는 레포 루트에서 실행되지 않을 수 있어 이 파일 위치를 기준으로 거슬러 올라간다.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_CERT_PATH = Path(os.environ.get("TLS_CERT_PATH") or (_REPO_ROOT / "infra" / "tls" / "hwax.crt"))
# 선택 — 리프 파일에 체인이 안 붙어 있을 때(리프만 있는 사내 CA 발급) 발급 CA 체인을 따로 준다.
_CA_PATH = Path(os.environ["TLS_CA_PATH"]) if os.environ.get("TLS_CA_PATH") else None
# 선택 — "공개 루트" 로 삼을 번들. 기본은 certifi(Mozilla 번들 = Node 가 쓰는 것과 같은 계열).
_TRUST_BUNDLE = os.environ.get("TLS_TRUST_BUNDLE") or None

_PEM_RE = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)


def _read_pem(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # 개인키가 같은 파일에 붙어 있는 구성(fullchain+key)이면 배포하지 않는다 — 사고 방지.
    if "PRIVATE KEY" in text:
        return None
    return text if "BEGIN CERTIFICATE" in text else None


def _read_cert() -> str | None:
    return _read_pem(_CERT_PATH)


def _certs(pem: str) -> list[str]:
    return _PEM_RE.findall(pem)


def _is_self_signed(pem: str) -> bool:
    """issuer == subject 면 자체서명. 파싱 실패는 '모름'이 아니라 False(안내를 띄우지 않음)로
    본다 — 사내 CA 인증서에 불필요한 경고를 붙이는 쪽이 더 나쁘다."""
    try:
        from cryptography import x509  # noqa: PLC0415 — 선택 의존성 취급

        cert = x509.load_pem_x509_certificate(_certs(pem)[0].encode())
        return cert.issuer == cert.subject
    except Exception:  # noqa: BLE001
        return False


def _trust_bundle() -> str | None:
    if _TRUST_BUNDLE:
        return _TRUST_BUNDLE
    try:
        import certifi  # noqa: PLC0415

        return certifi.where()
    except ImportError:
        pass
    for p in ("/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt"):
        if Path(p).is_file():
            return p
    return None


def _reaches_public_root(pem: str) -> tuple[bool | None, str]:
    """리프가 공개 루트 번들에 닿는가. (판정, 오류 한 줄). 판정 None = 판정 수단이 없다.

    openssl verify 를 쓴다 — 기본 CApath/CAfile 을 **끄고** 번들만 본다. 안 끄면 박스의
    /etc/ssl/certs 에 누가 심어 둔 사설 CA 가 "공개" 로 읽혀, 사용자 PC 의 Node 는 못 믿는
    인증서를 여기서는 된다고 말한다."""
    bundle, openssl = _trust_bundle(), shutil.which("openssl")
    if not bundle or not openssl:
        return None, "판정 수단 없음(openssl 또는 신뢰 번들)"
    certs = _certs(pem)
    if not certs:
        return None, "인증서 없음"
    with tempfile.TemporaryDirectory() as d:
        leaf = Path(d) / "leaf.pem"
        leaf.write_text(certs[0] + "\n", encoding="utf-8")
        cmd = [openssl, "verify", "-no-CApath", "-no-CAfile", "-CAfile", bundle]
        if len(certs) > 1:
            chain = Path(d) / "chain.pem"
            chain.write_text("\n".join(certs[1:]) + "\n", encoding="utf-8")
            cmd += ["-untrusted", str(chain)]
        try:
            r = subprocess.run(cmd + [str(leaf)], capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"openssl 실행 실패: {exc}"
    if r.returncode == 0:
        return True, ""
    lines = [ln.strip() for ln in (r.stderr + "\n" + r.stdout).splitlines() if ln.strip()]
    err = next((ln for ln in lines if "error" in ln.lower()), lines[-1] if lines else "verify failed")
    return False, err


def _ca_bundle() -> str | None:
    """개인 Claude 에 심을 발급 CA 체인. TLS_CA_PATH > 리프 파일의 체인부 > 자체서명 리프 자신."""
    explicit = _read_pem(_CA_PATH)
    if explicit:
        return "\n".join(_certs(explicit)) + "\n"
    pem = _read_cert()
    if not pem:
        return None
    certs = _certs(pem)
    if len(certs) > 1:
        return "\n".join(certs[1:]) + "\n"
    if certs and _is_self_signed(pem):
        return certs[0] + "\n"
    return None


def _cert_response(pem: str, filename: str) -> Response:
    return Response(
        content=pem,
        media_type="application/x-x509-ca-cert",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=300",
        },
    )


@router.get("/tls/portal.crt")
def portal_cert() -> Response:
    """포털 TLS 인증서(PEM, 리프). 무인증 — 공개키이고, 신뢰 설정은 로그인 전에도 필요하다."""
    pem = _read_cert()
    if pem is None:
        return Response(status_code=404, content="인증서 파일이 없습니다.", media_type="text/plain; charset=utf-8")
    return _cert_response(pem, "hwax-portal.crt")


@router.get("/tls/ca.crt")
def portal_ca() -> Response:
    """개인 Claude(NODE_EXTRA_CA_CERTS)에 심을 **발급 CA 체인**. 리프만 있고 사내 CA 발급이면 404 —
    그때는 리프 파일을 fullchain 으로 바꾸거나 TLS_CA_PATH 를 준다(/tls/info 의 ca_available)."""
    ca = _ca_bundle()
    if ca is None:
        return Response(status_code=404, content="발급 CA 체인이 없습니다 — TLS_CERT_PATH 를 fullchain 으로 두거나 TLS_CA_PATH 를 설정하세요.",
                        media_type="text/plain; charset=utf-8")
    return _cert_response(ca, "hwax-portal-ca.crt")


@router.get("/tls/info")
def portal_cert_info() -> JSONResponse:
    """프론트·doctor 가 안내를 띄울지 결정하는 데 쓴다.

    needs_ca     — 체인이 공개 루트에 안 닿는다(자체서명 또는 사내 CA) → 개인 Claude 에 CA 를 심어야 한다.
    ca_available — /tls/ca.crt 가 내려 줄 체인이 있다. needs_ca 인데 false 면 운영자가 채울 몫이다.
    self_signed  — 옛 필드(호환). verify_error — needs_ca 의 근거 한 줄(만료 등 다른 원인도 여기 보인다)."""
    pem = _read_cert()
    self_signed = bool(pem) and _is_self_signed(pem)
    if pem:
        ok, err = _reaches_public_root(pem)
        # 판정 수단이 없으면 옛 기준(자체서명)으로 — 사내 CA 를 못 잡지만 없는 것보다 낫다.
        needs_ca = (not ok) if ok is not None else self_signed
    else:
        needs_ca, err = False, ""
    return JSONResponse(
        {"available": pem is not None, "self_signed": self_signed, "needs_ca": needs_ca,
         "ca_available": _ca_bundle() is not None, "verify_error": err},
        headers={"Cache-Control": "public, max-age=300"},
    )
