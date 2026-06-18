"""MCP registry endpoints.

  GET  /mcp/servers   — MCP servers the current user may use (allowed_groups filtered).
  POST /mcp/reload    — re-read mcp_servers.yaml without restart (admin only, CSRF-guarded).
  GET  /mcp/health    — registry liveness (count). Gateway/server health is the gateway's job.

The catalog of *tools* (tools/list) is the gateway's responsibility (remote fan-out); this
router only owns the PR-managed server registry + group visibility.
"""

from fastapi import APIRouter, Depends, Request

from app.auth.provider import Principal
from app.deps import get_current_principal, require_csrf, require_role
from app.schemas.mcp import McpServer, McpServerRead

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _registry(request: Request):
    return request.app.state.mcp_registry


def _to_read(s: McpServer) -> McpServerRead:
    return McpServerRead(name=s.name, description=s.description, tools_prefix=s.tools_prefix)


@router.get("/servers", response_model=list[McpServerRead])
def list_servers(
    request: Request,
    principal: Principal = Depends(get_current_principal),
) -> list[McpServerRead]:
    return [_to_read(s) for s in _registry(request).visible_for(principal.groups)]


@router.get("/health")
def mcp_health(request: Request) -> dict[str, int | str]:
    return {"status": "ok", "servers": len(_registry(request).all())}


@router.post("/reload")
def reload_registry(
    request: Request,
    admin: Principal = Depends(require_role("portal-admin")),
    _csrf: None = Depends(require_csrf),
) -> dict[str, int | str]:
    count = _registry(request).reload()
    # Sensitive admin action → audit it (who reloaded the MCP registry, to what size).
    request.app.state.agent_audit.record(
        principal=admin.subject, event="mcp_reload", status="ok", meta={"count": count}
    )
    return {"status": "reloaded", "count": count}
