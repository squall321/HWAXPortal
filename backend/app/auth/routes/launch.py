"""Downstream launch: mint an audience-scoped token and tell the SPA how to hand it off.

  POST /systems/{id}/launch  — (auth + CSRF) returns a HandoffPayload:
      { mode: "auto_post", action, fields }   → SPA auto-submits a hidden POST form
      { mode: "redirect",  action, url }       → SPA navigates to url (token in query)

external-url tiles never hit this (the SPA opens them directly).
"""

from fastapi import APIRouter, Depends, Request

from app.auth.downstream import HandoffPayload
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.catalog.registry import CatalogRegistry
from app.deps import get_catalog, get_current_principal, require_csrf

router = APIRouter(prefix="/systems", tags=["launch"])


@router.post("/{system_id}/launch", response_model=HandoffPayload)
def launch(
    system_id: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
    _csrf: None = Depends(require_csrf),
) -> HandoffPayload:
    visible = {s.id for s in catalog.visible_for(principal.groups)}
    system = catalog.get(system_id)
    if not system or system_id not in visible:
        raise AuthError("system not found", status_code=404)
    if system.integration_type == "external-url":
        raise AuthError("external systems are opened directly, not launched", status_code=400)

    issuer = request.app.state.downstream_issuer
    return issuer.issue(principal, system)
