"""Linked-systems registry: loads + validates config/systems.yaml, serves lookups.

The YAML is the source of truth for metadata (name/logo/description). The *destination*
(which localhost port / URL each tile routes to) comes from a simple `routes.env` file
(`system-id=URL` per line) or a `SYS_<ID>_URL` environment variable — so wiring a system
up is "set one line, done": that tile flips to clickable and opens its URL. Validated on
load (fail fast); `reload()` re-reads both files without a restart.
"""

import os
from pathlib import Path

import yaml

from app.config import Settings
from app.schemas.system import CatalogFile, LinkedSystem


def _env_key(system_id: str) -> str:
    return "SYS_" + system_id.upper().replace("-", "_") + "_URL"


class CatalogRegistry:
    def __init__(self, settings: Settings) -> None:
        self._catalog_path = Path(settings.resolve(settings.catalog_path))
        self._routes_path = Path(settings.resolve(settings.routes_path))
        self._systems: list[LinkedSystem] = []
        self.reload()

    def _load_routes(self) -> dict[str, str]:
        """Parse the simple `system-id=URL` routes file (if present)."""
        routes: dict[str, str] = {}
        if self._routes_path.exists():
            for raw in self._routes_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip()
                if value:
                    routes[key.strip()] = value
        return routes

    def _apply_route(self, s: LinkedSystem, routes: dict[str, str]) -> None:
        """Resolve a destination URL (env var > routes file > yaml) and flip the tile live.

        The mode is whatever systems.yaml declares (proxy / external-url / handoff) — we only
        fill in the destination + availability. A routes.env entry is a nginx proxy target by
        convention, so if the yaml left it at the bare default, treat it as `proxy`.
        """
        from_route = os.environ.get(_env_key(s.id)) or routes.get(s.id)
        url = from_route or s.url
        if url:
            s.url = url
            s.status = "available"  # a destination exists → tile is clickable
            # If the destination came from routes.env and yaml didn't pick a non-default mode,
            # it's a path-proxy target (the new-tab-to-localhost trap is why we don't default to
            # external-url here).
            if from_route and s.integration_type == "external-url":
                s.integration_type = "proxy"

    def reload(self) -> int:
        raw = yaml.safe_load(self._catalog_path.read_text(encoding="utf-8")) or {}
        catalog = CatalogFile.model_validate(raw)  # raises on malformed entries
        routes = self._load_routes()

        seen: set[str] = set()
        for s in catalog.systems:
            if s.id in seen:
                raise ValueError(f"duplicate system id in catalog: {s.id}")
            seen.add(s.id)
            self._apply_route(s, routes)

        self._systems = sorted(catalog.systems, key=lambda s: (s.sort_order, s.name))
        return len(self._systems)

    def all(self) -> list[LinkedSystem]:
        return list(self._systems)

    def visible_for(self, groups: list[str]) -> list[LinkedSystem]:
        """Enabled systems the user may see (required_role gate against their groups)."""
        gset = set(groups)
        return [
            s
            for s in self._systems
            if s.enabled and (s.required_role is None or s.required_role in gset)
        ]

    def get(self, system_id: str) -> LinkedSystem | None:
        return next((s for s in self._systems if s.id == system_id), None)
