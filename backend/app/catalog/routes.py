"""Catalog endpoints.

  GET  /systems            — tiles the current user may see (filtered by required_role).
  GET  /systems/{id}       — one tile (404 if hidden/absent).
  POST /systems/reload     — re-read systems.yaml without restart (admin only, CSRF-guarded).
"""

from fastapi import APIRouter, Depends

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.catalog.registry import CatalogRegistry
from app.deps import get_catalog, get_current_principal, require_csrf, require_role
from app.schemas.system import LinkedSystem, SystemRead

router = APIRouter(prefix="/systems", tags=["catalog"])


def _to_read(s: LinkedSystem) -> SystemRead:
    return SystemRead(
        id=s.id,
        name=s.name,
        description=s.description,
        tagline=s.tagline,
        icon=s.icon,
        accent=s.accent,
        category=s.category,
        status=s.status,
        integration_type=s.integration_type,
        # Only external-url tiles expose a direct URL; handoffs go via /systems/{id}/launch.
        url=s.url if s.integration_type == "external-url" else None,
    )


@router.get("", response_model=list[SystemRead])
def list_systems(
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
) -> list[SystemRead]:
    return [_to_read(s) for s in catalog.visible_for(principal.groups)]


@router.get("/{system_id}", response_model=SystemRead)
def get_system(
    system_id: str,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
) -> SystemRead:
    visible = {s.id for s in catalog.visible_for(principal.groups)}
    system = catalog.get(system_id)
    if not system or system_id not in visible:
        raise AuthError("system not found", status_code=404)
    return _to_read(system)


@router.post("/reload")
def reload_catalog(
    catalog: CatalogRegistry = Depends(get_catalog),
    _admin: Principal = Depends(require_role("portal-admin")),
    _csrf: None = Depends(require_csrf),
) -> dict[str, int | str]:
    count = catalog.reload()
    return {"status": "reloaded", "count": count}
