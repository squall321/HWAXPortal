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
        """Parse the simple `system-id=URL` routes file (if present).

        routes.local.env(gitignore, 박스별 오버레이)가 옆에 있으면 같은 키를 덮어쓴다 —
        gen-nginx-conf.sh 와 동일 규칙. 이걸 안 읽으면 오버레이로 nginx 라우트만 생기고
        타일은 coming_soon 으로 남는다(실사고 2026-09-03: cae00 STE — update-all 의 conf
        재생성이 base 의 주석 처리된 ste 를 반영하며 웹 접속이 끊겼다).
        """
        routes: dict[str, str] = {}
        overlay = self._routes_path.parent / "routes.local.env"
        for path in (self._routes_path, overlay):
            if not path.exists():
                continue
            for raw in path.read_text(encoding="utf-8").splitlines():
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
        # Handoff tiles: systems.yaml `url` is the launch CALLBACK target (where the portal
        # auto-POSTs the launch token), which is NOT the nginx proxy target in routes.env. A
        # routes.env entry for these only wires reverse-proxy reachability, so it must never
        # overwrite the callback url. Flip the tile live when it's routed (proxied) or already
        # carries a callback url.
        if s.integration_type in ("jwt-handoff", "saml-handoff"):
            if from_route or s.url:
                s.status = "available"
            return
        # external-url 타일도 routes 파일에 항목이 있으면 proxy 로 승격한다 — 라우트 파일이
        # 박스별 진실이다(2026-09-03, report-archive 실사고: dev 는 RA 가 127.0.0.1 바인드라
        # 직결 링크가 원격에서 연결 거부 → dev routes.env 의 항목이 프록시로 살리고, cae00 은
        # routes.prod.env 에 항목이 없어 yaml 의 :3000 직결이 그대로 산다). 항목 없이 yaml 이
        # url 을 줬으면 그 직결 의도를 존중한다.
        if s.integration_type == "external-url" and s.url:
            if from_route:
                s.integration_type = "proxy"
            s.status = "available"
            return
        url = from_route or s.url
        if url:
            s.url = url
            s.status = "available"  # a destination exists → tile is clickable
            # If the destination came from routes.env and yaml didn't pick a non-default mode,
            # it's a path-proxy target (the new-tab-to-localhost trap is why we don't default to
            # external-url here).
            if from_route and s.integration_type == "external-url":
                s.integration_type = "proxy"
        elif s.integration_type == "proxy":
            # 목적지 없는 proxy 타일은 정직하게 끈다. yaml/스키마 기본값이 available 이라
            # 여기서 강등하지 않으면 라우트 없는 타일이 클릭 가능하게 뜨고, /<id>/ 는
            # nginx catch-all 이 SPA index.html 을 200 으로 돌려줘 조용히 깨진다
            # (실사고 2026-09-03: ste — routes.local.env 없는 박스에서 available 로 노출).
            s.status = "coming_soon"

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
