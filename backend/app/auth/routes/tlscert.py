"""포털 TLS 인증서(공개키) 배포 — 자체서명일 때 개인 Claude 가 이 포털을 신뢰하게 만드는 용도.

사내 CA 인증서가 들어오기 전까지 포털은 자체서명 인증서로 뜬다. 브라우저는 경고를 누르면
통과하지만 Node(mcp-remote·claude mcp add --transport http)는 눌러 줄 사람이 없어
SELF_SIGNED_CERT_IN_CHAIN 으로 죽는다 — "웹은 되는데 MCP 만 안 되는" 증상의 원인이다.
해결은 NODE_EXTRA_CA_CERTS 로 이 인증서를 가리키는 것이라, 받을 곳이 필요하다.

⚠ 배포하는 것은 **인증서(.crt)뿐이다.** 개인키(.key)는 어떤 경로로도 노출하지 않는다.
인증서는 TLS 핸드셰이크에서 이미 누구에게나 평문으로 전달되는 공개 정보다.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

router = APIRouter(tags=["tls"])

# nginx 가 읽는 것과 같은 기본 경로(gen-nginx-conf.sh 의 TLS_CERT_PATH 기본값).
# 백엔드는 레포 루트에서 실행되지 않을 수 있어 이 파일 위치를 기준으로 거슬러 올라간다.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_CERT_PATH = Path(os.environ.get("TLS_CERT_PATH") or (_REPO_ROOT / "infra" / "tls" / "hwax.crt"))


def _read_cert() -> str | None:
    try:
        text = _CERT_PATH.read_text(encoding="utf-8")
    except OSError:
        return None
    # 개인키가 같은 파일에 붙어 있는 구성(fullchain+key)이면 배포하지 않는다 — 사고 방지.
    if "PRIVATE KEY" in text:
        return None
    return text if "BEGIN CERTIFICATE" in text else None


def _is_self_signed(pem: str) -> bool:
    """issuer == subject 면 자체서명. 파싱 실패는 '모름'이 아니라 False(안내를 띄우지 않음)로
    본다 — 사내 CA 인증서에 불필요한 경고를 붙이는 쪽이 더 나쁘다."""
    try:
        from cryptography import x509  # noqa: PLC0415 — 선택 의존성 취급

        cert = x509.load_pem_x509_certificate(pem.encode())
        return cert.issuer == cert.subject
    except Exception:  # noqa: BLE001
        return False


@router.get("/tls/portal.crt")
def portal_cert() -> Response:
    """포털 TLS 인증서(PEM). 무인증 — 공개키이고, 신뢰 설정은 로그인 전에도 필요하다."""
    pem = _read_cert()
    if pem is None:
        return Response(status_code=404, content="인증서 파일이 없습니다.", media_type="text/plain; charset=utf-8")
    return Response(
        content=pem,
        media_type="application/x-x509-ca-cert",
        headers={
            "Content-Disposition": 'attachment; filename="hwax-portal.crt"',
            "Cache-Control": "public, max-age=300",
        },
    )


@router.get("/tls/info")
def portal_cert_info() -> JSONResponse:
    """프론트가 안내 블록을 띄울지 결정하는 데 쓴다. self_signed 가 false 면 안내 불필요."""
    pem = _read_cert()
    return JSONResponse(
        {"available": pem is not None, "self_signed": bool(pem) and _is_self_signed(pem)},
        headers={"Cache-Control": "public, max-age=300"},
    )
