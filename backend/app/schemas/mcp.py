"""MCP server registry models.

An McpServer describes one independently-operated MCP server (one per portal sub-page,
by convention). The gateway exposes the union of their tools to the agent; the portal's
registry here is metadata + group-visibility only (the gateway does the actual fan-out).

Governance: config/mcp_servers.yaml is PR-managed (git diff = audit) and reloaded by an
admin via POST /mcp/reload — same convention as systems.yaml.
"""

from pydantic import BaseModel, Field


class McpServer(BaseModel):
    name: str  # e.g. "mcp_stress_analysis"
    url: str  # the MCP server's address (reachable by the gateway)
    description: str | None = None
    tools_prefix: str  # namespace to avoid tool collisions (stress.get_data vs thermal.get_data)
    auth: str = "jwt"  # how the gateway authenticates to this server
    # allowed_groups (plural) — a tool is visible if the user's groups intersect this set.
    # Distinct from the catalog's required_role (single value); empty = visible to all.
    allowed_groups: list[str] = Field(default_factory=list)
    enabled: bool = True


class McpServersFile(BaseModel):
    """Top-level shape of config/mcp_servers.yaml — validated on load (fail fast on typos)."""

    servers: list[McpServer] = Field(default_factory=list)


class McpServerRead(BaseModel):
    """An MCP server as the SPA / agent sees it (no internal auth detail)."""

    name: str
    description: str | None = None
    tools_prefix: str
