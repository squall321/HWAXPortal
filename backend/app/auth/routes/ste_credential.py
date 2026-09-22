"""ste 자격 중계 — 포털에 로그인한 사람에게 ste PAT 를 건네준다.

  POST /systems/ste/credential  — (세션 + CSRF) → { token, expires_in }

**왜 중계인가.** ste 는 자체 계정·PAT 로 인증한다(그 결정은 ste 계획서에 근거와 함께
기록돼 있다 — 앞단에 SSO 게이트를 두지 않고 백엔드가 401 로 막는다). 그래서 포털이
할 일은 ste 의 인증을 바꾸는 것이 아니라, **사용자가 손으로 하던 단계를 대신하는 것**이다.

**왜 JWT 핸드오프가 아닌가.** ste 헤드노드는 인터넷이 전무해서 포털 JWKS 를 받아올
방향이 없고(검증된 방향은 포털 → ste 뿐이다), RS256 검증에 쓸 wheel 도 그 배포에 없다.
그래서 신원은 서버 간 공유 시크릿으로 건넨다. 브라우저 리다이렉트가 없으므로 ste 의
"SSO 리다이렉트 금지" 요구와도 부딪히지 않는다.

**인가는 여기서 한다.** ste 타일이 그 사람에게 보이는지(`visible_systems`)를 보고, 안
보이면 404 다. 이 한 줄이 ste 의 관리자 승인제를 대신한다 — 빠지면 포털에 로그인한
모든 사람이 ste 계정을 얻는다.

**토큰은 저장하지 않는다.** 받은 값을 응답 본문으로 넘기고 끝이다. 포털 DB 에 쌓으면
전 사용자의 다운스트림 자격을 떠안게 되고, 회수 책임까지 따라온다.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.catalog.registry import CatalogRegistry
from app.catalog.routes import visible_systems
from app.config import Settings, get_settings
from app.deps import get_catalog, get_current_principal, require_csrf

log = logging.getLogger("hwax.ste")
router = APIRouter(prefix="/systems", tags=["launch"])

SYSTEM_ID = "ste"
# ste 쪽 시한(15초)은 넉넉하다 — 계정 생성 + PAT 발급뿐이라 원래 수십 ms 다. 길게 잡는
# 이유는 SSH 터널 경유일 때의 첫 연결 지연이고, 그래도 브라우저를 매달아 둘 수는 없다.
TIMEOUT_S = 15.0


class SteCredential(BaseModel):
    token: str
    expires_in: int


@router.post("/ste/credential", response_model=SteCredential)
async def ste_credential(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> SteCredential:
    if not settings.ste_sso_secret:
        # 꺼져 있는 것과 권한이 없는 것을 같은 모양으로 낸다 — 어느 쪽이든 브라우저가
        # 할 일은 "그냥 조용히 넘어간다" 로 같다.
        raise AuthError("ste credential relay is not configured", status_code=404)

    visible = {s.id for s in visible_systems(request, catalog, principal)}
    if SYSTEM_ID not in visible:
        raise AuthError("system not found", status_code=404)
    if not principal.email:
        raise AuthError("no email on principal", status_code=403)

    url = settings.ste_base_url.rstrip("/") + "/api/auth/sso"
    headers = {
        "X-Heax-Gateway-Secret": settings.ste_sso_secret,
        "X-Heax-User-Email": principal.email,
        "X-Heax-User-Name": principal.display_name or "",
        "X-Heax-Client": "hwax-portal",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            r = await client.post(url, headers=headers)
    except httpx.HTTPError as exc:
        # **조용히 빈 토큰을 돌려주지 않는다.** 그러면 브라우저는 자격을 받은 줄 알고
        # ste 로 갔다가 로그인 화면을 보고, 원인은 아무 데도 안 남는다.
        log.warning("ste sso call failed: %s", type(exc).__name__)
        raise AuthError("ste is unreachable", status_code=502) from exc

    if r.status_code == 403:
        # ste 가 그 계정을 정지시켜 뒀다 — 포털 권한과 어긋난 상태다. 그대로 전한다.
        raise AuthError("ste account is disabled", status_code=403)
    if r.status_code != 200:
        log.warning("ste sso rejected: HTTP %s", r.status_code)
        raise AuthError("ste refused the delegation", status_code=502)

    body = r.json()
    token = (body.get("access_token") or "").strip()
    if not token:
        raise AuthError("ste returned no token", status_code=502)
    log.info("ste credential relayed for %s", principal.email)
    return SteCredential(token=token, expires_in=int(body.get("expires_in") or 43200))


@router.post("/ste/credential/revoke")
async def ste_credential_revoke(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> dict:
    """로그아웃 훅. 브라우저 사본을 지우는 것만으로는 회수가 아니다 — 원장에서 죽여야 한다.

    실패는 **비치명**이다. 회수가 안 됐다고 로그아웃을 막으면 사용자가 나갈 수 없다.
    """
    if not settings.ste_sso_secret or not principal.email:
        return {"ok": True, "revoked": False}
    url = settings.ste_base_url.rstrip("/") + "/api/auth/sso/revoke"
    headers = {
        "X-Heax-Gateway-Secret": settings.ste_sso_secret,
        "X-Heax-User-Email": principal.email,
        "X-Heax-Client": "hwax-portal",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            r = await client.post(url, headers=headers)
        return {"ok": True, "revoked": r.status_code == 200}
    except httpx.HTTPError as exc:
        log.warning("ste sso revoke failed: %s", type(exc).__name__)
        return {"ok": True, "revoked": False}
