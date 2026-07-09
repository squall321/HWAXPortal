"""Catalog endpoints.

  GET  /systems            — tiles the current user may see (filtered by required_role).
  GET  /systems/{id}       — one tile (404 if hidden/absent).
  POST /systems/reload     — re-read systems.yaml without restart (admin only, CSRF-guarded).
"""

from fastapi import APIRouter, Depends, Request

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.catalog.registry import CatalogRegistry
from app.deps import get_catalog, get_current_principal, require_csrf, require_role
from app.schemas.system import LinkedSystem, SystemRead

router = APIRouter(prefix="/systems", tags=["catalog"])


def _fill_host(url: str | None, request: Request) -> str | None:
    """external-url 의 {host} 를 요청 Host(브라우저가 보는 호스트)로 치환 — 박스별 하드코딩 없이
    다른 포트의 서비스(예: report-archive :3000)를 직결 링크로 열 수 있게 한다."""
    if not url or "{host}" not in url:
        return url
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "")
    host = host.split(",")[0].strip().split(":")[0]  # 첫 항목, 포트 제거
    return url.replace("{host}", host) if host else url


def _to_read(s: LinkedSystem, request: Request) -> SystemRead:
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
        # external-url → expose the URL (tile opens it directly). proxy → hide it (the SPA opens
        # the same-origin /<id>/ path; nginx proxies internally). handoffs → /systems/{id}/launch.
        url=_fill_host(s.url, request) if s.integration_type == "external-url" else None,
    )


@router.get("", response_model=list[SystemRead])
def list_systems(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
) -> list[SystemRead]:
    return [_to_read(s, request) for s in catalog.visible_for(principal.groups)]


@router.get("/{system_id}", response_model=SystemRead)
def get_system(
    system_id: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    catalog: CatalogRegistry = Depends(get_catalog),
) -> SystemRead:
    visible = {s.id for s in catalog.visible_for(principal.groups)}
    system = catalog.get(system_id)
    if not system or system_id not in visible:
        raise AuthError("system not found", status_code=404)
    return _to_read(system, request)


@router.post("/reload")
def reload_catalog(
    catalog: CatalogRegistry = Depends(get_catalog),
    _admin: Principal = Depends(require_role("portal-admin")),
    _csrf: None = Depends(require_csrf),
) -> dict[str, int | str]:
    count = catalog.reload()
    return {"status": "reloaded", "count": count}
