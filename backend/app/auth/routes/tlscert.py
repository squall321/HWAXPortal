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
자체서명 리프는 스스로가 CA 라 그대로 내려 준다. ⚠ 사내 CA 가 발급한 **리프는 CA 를 대신하지
못한다** — 신뢰 목록에 넣어도 Node 는 발급자를 요구해 그대로 죽는다(실측). 그래서 내릴 체인이
리프를 실제로 검증하는지 확인한 것만 ca_available 로 낸다.

경로 계약 — TLS_CERT_PATH·TLS_CA_PATH 의 상대값은 **리포 루트 기준**이다(nginx 의 gen-nginx-conf.sh·
gen-tls-cert.sh 와 같다). 컨테이너 백엔드의 CWD 는 /workspace/backend 라 앵커 없이 쓰면 같은 값을
nginx 는 찾고 백엔드는 못 찾는다(적대 검토 2026-09-25 실측).

⚠ 배포하는 것은 **인증서(.crt)뿐이다.** 개인키(.key)는 어떤 경로로도 노출하지 않는다.
인증서는 TLS 핸드셰이크에서 이미 누구에게나 평문으로 전달되는 공개 정보다.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

router = APIRouter(tags=["tls"])

# 백엔드는 레포 루트에서 실행되지 않을 수 있어 이 파일 위치를 기준으로 거슬러 올라간다.
_REPO_ROOT = Path(__file__).resolve().parents[4]


def _anchor(value: str) -> Path:
    """env 의 경로값 — 절대경로는 그대로, 상대경로는 리포 루트 기준(nginx 쪽 계약과 같다)."""
    p = Path(value)
    return p if p.is_absolute() else _REPO_ROOT / p


# nginx 가 읽는 것과 같은 기본 경로(gen-nginx-conf.sh 의 TLS_CERT_PATH 기본값).
_CERT_PATH = _anchor(os.environ.get("TLS_CERT_PATH") or "infra/tls/hwax.crt")
# 선택 — 리프 파일에 체인이 안 붙어 있을 때(리프만 있는 사내 CA 발급) 발급 CA 체인을 따로 준다.
_CA_PATH = _anchor(os.environ["TLS_CA_PATH"]) if os.environ.get("TLS_CA_PATH") else None
# 선택 — "공개 루트" 로 삼을 번들. 기본은 certifi(Mozilla 번들 = Node 가 쓰는 것과 같은 계열).
# 박스의 /etc/ssl/certs 로 물러나지 않는다 — 거기 심어 둔 사설 CA 가 "공개" 로 읽히면 사용자 PC 의
# Node 는 못 믿는 인증서를 여기서는 된다고 말한다.
_TRUST_BUNDLE = str(_anchor(os.environ["TLS_TRUST_BUNDLE"])) if os.environ.get("TLS_TRUST_BUNDLE") else None

_PEM_RE = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)


def _read_pem(path: Path | None) -> str | None:
    """PEM 인증서 텍스트. 없거나·못 읽거나·바이너리(DER/PKCS#12)·개인키 동봉이면 None."""
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    # 개인키가 같은 파일에 붙어 있는 구성(fullchain+key)이면 배포하지 않는다 — 사고 방지.
    if "PRIVATE KEY" in text:
        return None
    return text if "BEGIN CERTIFICATE" in text else None


def _read_cert() -> str | None:
    return _read_pem(_CERT_PATH)


def _certs(pem: str) -> list[str]:
    return _PEM_RE.findall(pem)


def _leaf(pem: str):
    """cryptography 객체 — 파싱 실패는 None(자체서명·만료 판정을 '모름' 쪽으로 보낸다)."""
    try:
        from cryptography import x509  # noqa: PLC0415 — 선택 의존성 취급

        return x509.load_pem_x509_certificate(_certs(pem)[0].encode())
    except Exception:  # noqa: BLE001
        return None


def _is_self_signed(pem: str) -> bool:
    """issuer == subject 면 자체서명. 파싱 실패는 '모름'이 아니라 False(안내를 띄우지 않음)로
    본다 — 사내 CA 인증서에 불필요한 경고를 붙이는 쪽이 더 나쁘다."""
    c = _leaf(pem)
    return bool(c) and c.issuer == c.subject


def _is_expired(pem: str) -> bool:
    c = _leaf(pem)
    try:
        return bool(c) and c.not_valid_after_utc < dt.datetime.now(dt.timezone.utc)
    except AttributeError:  # cryptography < 42
        return bool(c) and c.not_valid_after < dt.datetime.utcnow()


def _trust_bundle() -> str | None:
    if _TRUST_BUNDLE:
        return _TRUST_BUNDLE
    try:
        import certifi  # noqa: PLC0415

        return certifi.where()
    except ImportError:
        return None


def _verify(pem: str, bundle: str) -> tuple[bool | None, str]:
    """리프가 이 번들에 닿는가. (판정, 오류 한 줄). 판정 None = 판정 수단이 없다.

    openssl verify 를 쓴다 — 기본 CApath/CAfile 을 **끄고** 준 번들만 본다(위 _TRUST_BUNDLE 주석).
    오류 문장에서 임시 경로는 지운다 — /tls/info 는 무인증이라 서버 경로를 내보내지 않는다."""
    openssl = shutil.which("openssl")
    if not openssl:
        return None, "판정 수단 없음(openssl)"
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
            return None, f"openssl 실행 실패: {type(exc).__name__}"
        out = (r.stderr + "\n" + r.stdout).replace(d, "<tmp>").replace(bundle, "<bundle>")
    if r.returncode == 0:
        return True, ""
    low = out.lower()
    if "error loading file" in low or "unable to load certificate" in low:
        return None, "판정 수단 없음(번들·인증서 파일을 읽지 못했다)"
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    err = next((ln for ln in lines if ln.lower().startswith("error ") and "depth" in ln),
               next((ln for ln in lines if "error" in ln.lower()), lines[-1] if lines else "verify failed"))
    return False, err


def _reaches_public_root(pem: str) -> tuple[bool | None, str]:
    bundle = _trust_bundle()
    if not bundle:
        return None, "판정 수단 없음(신뢰 번들)"
    return _verify(pem, bundle)


def _ca_bundle(pem: str) -> tuple[str | None, str, bool]:
    """개인 Claude 에 심을 발급 CA 체인, 없을 때의 이유(경로 없이), **판정을 실제로 했는가**(decided).

    후보 순서: TLS_CA_PATH > 리프 파일의 체인부 > 자체서명 리프 자신. 후보가 리프를 실제로 검증할 때만
    준다 — 엉뚱한 CA 를 "준비됨" 으로 내면 사용자는 심고도 같은 오류를 만난다. 검증에는 리프 파일의
    체인부(서버가 핸드셰이크로 보내는 중간 CA)를 -untrusted 로 같이 준다 — Node 도 그렇게 검증하므로
    루트만 심으면 되는 표준 구성(leaf+int 서빙, TLS_CA_PATH=루트)이 통해야 한다(2라운드 검토 회귀).
    판정 수단이 없으면(openssl 실패) **주지 않는다** — 검증 안 된 후보를 "준비됨" 으로 낸 3라운드 회귀.
    decided=False 는 호출자가 캐시하지 않고 화면이 "모름" 으로 내는 신호다."""
    certs = _certs(pem)
    if not certs:
        return None, "포털 인증서 파일에 인증서가 없다", True
    leaf_only = len(certs) == 1
    cands: list[tuple[str, str]] = []
    if _CA_PATH is not None:
        explicit = _read_pem(_CA_PATH)
        if explicit and _certs(explicit):
            cands.append(("TLS_CA_PATH", "\n".join(_certs(explicit)) + "\n"))
        else:
            return None, "TLS_CA_PATH 를 읽지 못했다(파일 없음·PEM 아님·개인키 동봉)", True
    if not leaf_only:
        cands.append(("리프 파일의 체인부", "\n".join(certs[1:]) + "\n"))
    if _is_self_signed(pem):
        cands.append(("자체서명 리프", certs[0] + "\n"))
    if not cands:
        # 리프만 서빙하면 중간 CA 가 핸드셰이크에도 없다 — 루트만으로는 Node 도 검증하지 못한다(3라운드 실측).
        return None, ("리프만 있고 발급 CA 체인이 없다 — TLS_CERT_PATH 를 루트까지 포함한 fullchain 으로 두거나 "
                      "TLS_CA_PATH 로 발급 체인(중간 CA + 루트)을 준다. 루트만으로는 안 된다(서버가 중간 CA 를 보내지 않는다)"), True
    reasons = []
    for name, bundle in cands:
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
            f.write(bundle)
        try:
            ok, err = _verify(pem, f.name)
        finally:
            os.unlink(f.name)
        if ok:
            return bundle, "", True
        if ok is None:
            return None, f"판정 수단 없음 — {err}", False
        reasons.append(f"{name}: 리프를 검증하지 못한다 — {err}")
    msg = "; ".join(reasons)
    if "issuer" in msg:                      # 발급자 결손일 때만, 서빙 모양에 맞는 처방을 붙인다(만료 등에는 안 붙인다)
        msg += (" (리프만 서빙하므로 TLS_CA_PATH 에 발급 체인 — 중간 CA 와 루트 — 가 모두 있어야 한다)" if leaf_only
                else " (체인이 루트 CA 까지 닿아야 한다 — 중간 CA 만으로는 Node 도 검증하지 못한다)")
    return None, msg, True


def _cert_response(pem: str, filename: str, max_age: int = 300) -> Response:
    return Response(
        content=pem,
        media_type="application/x-x509-ca-cert",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": f"public, max-age={max_age}",
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
    """개인 Claude(NODE_EXTRA_CA_CERTS)에 심을 **발급 CA 체인**. 없으면 404 와 이유(/tls/info 의 ca_error 와 같다)."""
    st = _state()
    if st["ca"] is None:
        return Response(status_code=404, content=f"발급 CA 체인이 없습니다 — {st['info']['ca_error']}",
                        media_type="text/plain; charset=utf-8")
    return _cert_response(st["ca"], "hwax-portal-ca.crt", max_age=60)   # /tls/info 와 같은 창


# openssl 서브프로세스는 요청마다 돌리지 않는다 — 무인증 엔드포인트라 증폭 표적이 된다.
# 두 엔드포인트가 **같은 상태**를 본다(따로 계산하면 만료·일시 실패 때 서로 어긋난다 — 2라운드 검토).
# 키는 인증서·CA 파일의 mtime 과 시간(TTL) — 파일이 안 바뀌어도 시간이 가면 만료가 보여야 한다.
# 판정을 못 한 순간(openssl 일시 실패 포함 — 공개루트 판정이든 CA 후보 검증이든)은 짧게만 둔다 —
# 곧 다시 판정하되, 실패가 이어지는 동안 요청마다 서브프로세스를 되살리지는 않는다(3라운드).
_TTL_S = int(os.environ.get("TLS_INFO_TTL", "60"))
_FAIL_TTL_S = 5
_CACHE: dict = {"key": None, "at": 0.0, "value": None}


def _stat_key() -> tuple:
    def st(p: Path | None):
        try:
            return (str(p), p.stat().st_mtime_ns, p.stat().st_size) if p else None
        except OSError:
            return (str(p), None, None)
    return (st(_CERT_PATH), st(_CA_PATH), _TRUST_BUNDLE)


def _compute() -> dict:
    pem = _read_cert()
    self_signed = bool(pem) and _is_self_signed(pem)
    expired = bool(pem) and _is_expired(pem)
    if pem:
        ok, err = _reaches_public_root(pem)
        # 판정 수단이 없으면 옛 기준(자체서명)으로 — 사내 CA 를 못 잡지만 없는 것보다 낫다. verified 가 그 사실을 낸다.
        needs_ca = (not ok) if ok is not None else self_signed
        ca, ca_err, ca_decided = _ca_bundle(pem)
        # verified = 두 판정(공개루트·CA 후보)을 **모두** 실제로 했다. 하나라도 못 했으면 화면은 "모름" 이다.
        verified = (ok is not None) and ca_decided
        # 만료는 리프의 날짜만이 아니라 openssl 이 본 체인 전체(중간 CA 만료·아직 유효하지 않음)도 센다.
        expired = expired or any(k in x for x in (err, ca_err) for k in ("expired", "not yet valid"))
    else:
        needs_ca, err, verified = False, "", False
        ca, ca_err = None, "포털 인증서 파일이 없다"
    info = {
        "available": pem is not None, "self_signed": self_signed,
        "needs_ca": needs_ca, "verified": verified, "verify_error": err,
        "expired": expired,
        "ca_available": ca is not None, "ca_error": ca_err,
    }
    return {"info": info, "ca": ca}


def _state() -> dict:
    key, now = _stat_key(), time.monotonic()
    c = _CACHE
    if c["value"] is not None and c["key"] == key:
        ttl = _TTL_S if c["value"]["info"]["verified"] else _FAIL_TTL_S   # 읽는 시점에 정한다(판정 못 한 값은 짧게)
        if now - c["at"] < ttl:
            return c["value"]
    value = _compute()
    _CACHE.update(key=key, at=now, value=value)
    return value


@router.get("/tls/info")
def portal_cert_info() -> JSONResponse:
    """프론트·doctor 가 안내를 띄울지 결정하는 데 쓴다.

    needs_ca     — 체인이 공개 루트에 안 닿는다(자체서명 또는 사내 CA) → 개인 Claude 에 CA 를 심어야 한다.
    verified     — 두 판정(공개루트·CA 후보)을 실제로 했다(false 면 화면은 '판정 못함' 으로 내고 등록을 미룬다).
    verify_error — needs_ca 의 근거 한 줄. expired — 리프 또는 체인이 만료·미유효(CA 를 심어도 안 된다, 운영자 몫).
    ca_available — /tls/ca.crt 가 내려 줄 체인이 있고 그 체인이 리프를 검증했다. ca_error — 없을 때의 이유."""
    return JSONResponse(_state()["info"], headers={"Cache-Control": "public, max-age=60"})
