"""Downstream launch: mint an audience-scoped token and tell the SPA how to hand it off.

  POST /systems/{id}/launch  — (auth + CSRF) returns a HandoffPayload:
      { mode: "auto_post", action, fields }   → SPA auto-submits a hidden POST form
      { mode: "redirect",  action, url }       → SPA navigates to url (token in query)

external-url tiles never hit this (the SPA opens them directly).
"""

from fastapi import APIRouter, Depends, Request

from app.auth import access_log
from app.auth.downstream import HandoffPayload
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.catalog.registry import CatalogRegistry
from app.catalog.routes import visible_systems
from app.deps import get_catalog, get_current_principal, require_csrf

router = APIRouter(prefix="/systems", tags=["launch"])


@router.post("/{system_id}/launch", response_model=HandoffPayload)
def launch(
    system_id: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
    _csrf: None = Depends(require_csrf),
    via: str | None = None,
) -> HandoffPayload:
    visible = {s.id for s in visible_systems(request, catalog, principal)}
    system = catalog.get(system_id)
    if not system or system_id not in visible:
        raise AuthError("system not found", status_code=404)
    if system.integration_type == "external-url":
        raise AuthError("external systems are opened directly, not launched", status_code=400)

    issuer = request.app.state.downstream_issuer
    payload = issuer.issue(principal, system)
    # 접속 원장(docs/access-history). 화면의 SSO 미리 로그인(SsoPrimer)은 45분마다 저절로 부르므로 표시해 둔다 —
    # 관리자 화면은 기본으로 그 줄을 숨긴다. 발급이지 하위 서비스의 수락은 아니다.
    access_log.note(request, email=principal.email or principal.subject, event="launch", service=system_id,
                    detail="primer" if via == "primer" else None)
    return payload


@router.post("/{system_id}/open")
def open_tile(
    system_id: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
    _csrf: None = Depends(require_csrf),
) -> dict:
    """프록시·외부 타일을 눌렀다는 기록 — 이 타일들은 토큰 발급 없이 화면이 곧장 연다(docs/access-history).
    외부 타일은 허브를 지나지 않으므로 허브가 아는 것은 이 클릭까지다."""
    visible = {s.id for s in visible_systems(request, catalog, principal)}
    if system_id not in visible:
        raise AuthError("system not found", status_code=404)
    access_log.note(request, email=principal.email or principal.subject, event="open", service=system_id)
    return {"ok": True}
