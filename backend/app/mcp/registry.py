"""MCP server registry: loads + validates config/mcp_servers.yaml, serves lookups.

Mirrors CatalogRegistry (same load/validate/reload shape). The YAML is the source of
truth; `reload()` re-reads it without a restart. Group visibility uses allowed_groups
(plural intersection) — a tool/server is visible if the user's groups intersect it, or
allowed_groups is empty (visible to all). This differs from the catalog's required_role
(a single value), so it is NOT a straight copy of visible_for.
"""

import threading
from pathlib import Path

import yaml

from app.config import Settings
from app.schemas.mcp import McpServer, McpServersFile


class McpRegistry:
    def __init__(self, settings: Settings) -> None:
        self._path = Path(settings.resolve(settings.mcp_servers_path))
        self._servers: list[McpServer] = []
        self._lock = threading.RLock()  # reload (admin) vs reads can interleave across threads
        self.reload()

    def reload(self) -> int:
        # Parse fully BEFORE taking the lock / swapping, so a bad file never leaves a torn state.
        # Absent file is fine in early phases (no MCP servers wired yet) → empty registry.
        if not self._path.exists():
            with self._lock:
                self._servers = []
            return 0
        raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        parsed = McpServersFile.model_validate(raw)  # raises on malformed entries

        seen: set[str] = set()
        for s in parsed.servers:
            if s.name in seen:
                raise ValueError(f"duplicate mcp server name: {s.name}")
            seen.add(s.name)

        new_servers = sorted(parsed.servers, key=lambda s: s.name)
        with self._lock:
            self._servers = new_servers  # atomic swap of a fully-built list
            return len(self._servers)

    def all(self) -> list[McpServer]:
        with self._lock:
            return list(self._servers)

    def visible_for(self, groups: list[str]) -> list[McpServer]:
        """Enabled servers the user may use (allowed_groups intersection; empty = all)."""
        gset = set(groups)
        with self._lock:
            return [
                s
                for s in self._servers
                if s.enabled and (not s.allowed_groups or gset & set(s.allowed_groups))
            ]

    def get(self, name: str) -> McpServer | None:
        with self._lock:
            return next((s for s in self._servers if s.name == name), None)
