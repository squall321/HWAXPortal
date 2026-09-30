# 서비스 접속 원장에 한 줄 남기는 도우미 — 로그인·타일 진입을 이메일·실제 IP·시각·서비스로(docs/access-history)
"""라우트에서 부르는 한 곳. 원장 쓰기가 실패해도 로그인·진입은 막지 않는다 — 대신 WARNING 으로 드러낸다(D-4).

IP 는 `request.client.host` 다. nginx 뒤의 uvicorn 이 X-Forwarded-For 로 이미 실제 주소로 바꿔 두었다(127.0.0.1 만 믿는
기본값). 주소 형식일 때만 적는다 — 박스 안 프로세스는 XFF 로 아무 글자나 넣을 수 있다(게이트웨이 감사와 같은 규칙).
"""

import ipaddress
import logging
import re
import secrets

from fastapi import Request

from app.auth import cookies

log = logging.getLogger(__name__)


def clean_ip(host) -> str:
    """주소 형식이면 정규화한 문자열, 아니면 ''. IPv6 영역 표기(`fe80::1%…`)는 `%` 뒤를 아무 글자나 받으므로 버리고,
    `::ffff:a.b.c.d` 는 IPv4 로 풀어 적는다(HWAXMcpGateway `_clean_ip` 와 같은 규칙)."""
    try:
        a = ipaddress.ip_address(str(host).strip()) if host else None
    except ValueError:
        return ""
    if a is None or getattr(a, "scope_id", None):
        return ""
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return str(a)


_UID = re.compile(r"[A-Za-z0-9_-]{16}")


def new_uid() -> str:
    return secrets.token_urlsafe(12)          # 16자 — _UID 와 짝이다


def _cookie_uid(request: Request) -> str | None:
    """요청의 연결 ID — 우리가 준 모양(16자)일 때만. 쿠키는 클라이언트 값이라 로그인 없이도 수 KB 를 실어
    무기한 원장에 쌓을 수 있었다(검토 1차, docs/access-history D-9)."""
    v = request.cookies.get(cookies.UID_COOKIE) or ""
    return v if _UID.fullmatch(v) else None


def note(request: Request, *, email: str, event: str, service: str | None = None,
         detail: str | None = None, uid: str | None = None) -> None:
    """원장에 한 줄. `uid` 를 안 주면 요청의 연결 ID 쿠키를 쓴다(로그인 뒤의 진입)."""
    try:
        store = request.app.state.agent_audit
        store.record_access(
            email=email, event=event, service=service,
            ip=clean_ip(getattr(request.client, "host", None)),
            ua=request.headers.get("user-agent"),
            uid=uid or _cookie_uid(request),
            detail=detail)
    except Exception as exc:  # noqa: BLE001 — 부기록이다. 다만 조용히 삼키지 않는다(INFO 는 버려진다, WARNING 은 남는다)
        log.warning("access log write failed (%s %s %s): %r", event, service, email, exc)
