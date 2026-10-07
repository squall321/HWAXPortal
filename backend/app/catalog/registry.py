"""Linked-systems registry: loads + validates config/systems.yaml, serves lookups.

The YAML is the source of truth for metadata (name/logo/description). The *destination*
(which localhost port / URL each tile routes to) comes from a simple `routes.env` file
(`system-id=URL` per line) or a `SYS_<ID>_URL` environment variable — so wiring a system
up is "set one line, done": that tile flips to clickable and opens its URL. Validated on
load (fail fast); `reload()` re-reads both files without a restart.
"""

import logging
import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.config import Settings
from app.schemas.system import CatalogFile, LinkedSystem


log = logging.getLogger(__name__)

# 박스별 타일 덮어쓰기(gitignore) — 있는 타일은 `url` 한 칸만. 외부 타일의 직결 주소는 사내 IP 라 추적 파일(systems.yaml)에
# 적지 않는다(리포 규칙, docs/access-history). routes.local.env 에 적으면 프록시로 승격되므로 그 파일을 쓰지 않는다.
# 카탈로그에 없는 id 는 name 이 있으면 이 박스에만 있는 **새 외부 타일**이다(reload — 8차 요청 §4-(3)).
LOCAL_OVERLAY = "systems.local.yaml"
_OVERLAY_KEYS = {"url"}


def _env_key(system_id: str) -> str:
    return "SYS_" + system_id.upper().replace("-", "_") + "_URL"


class CatalogRegistry:
    def __init__(self, settings: Settings) -> None:
        self._catalog_path = Path(settings.resolve(settings.catalog_path))
        self._routes_path = Path(settings.resolve(settings.routes_path))
        self._systems: list[LinkedSystem] = []
        self._routed: set[str] = set()
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
            if s.hide_unless_routed and not from_route:
                # 콜백 url 은 추적 파일에 늘 있다 — url 만 보고 켜면 라우트가 없는 박스에서 타일이 열린 채 보이고, 누르면 로그인
                # 토큰이 든 POST 를 포털 자신이 받아 새 탭에 405 JSON 한 줄이 뜬다(nginx 에 그 location 이 없다 — aireadyportal,
                # 2026-10-07). 박스마다 있고 없는 타일이라 '곧 공개' 로도 보이지 않게 숨긴다(아래 external-url·proxy 와 같다).
                # 표식이 없는 핸드오프 타일은 종전 그대로다 — 그 타일들의 라우트는 추적 파일에 있다.
                s.status = "coming_soon"
                s.enabled = False
                log.info("핸드오프 타일 %s 는 라우트가 없어 숨긴다 — 쓰려면 backend/config/routes.local.env 에 '%s=<주소>'",
                         s.id, s.id)
                return
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
        if s.integration_type == "external-url" and not from_route:
            # 주소 없는 외부 타일은 정직하게 끈다 — 두면 화면이 `/<id>/` 로 열어 SPA 로 떨어지고 조용히 깨진다.
            # 사내 주소는 systems.local.yaml(gitignore)에 둔다 — 새 박스·새 클론에서 여기로 온다.
            s.status = "coming_soon"
            if s.hide_unless_routed:
                # 박스마다 있고 없는 남의 서비스(testscope) — 없는 박스가 정상이라 경고가 아니라 안내 한 줄로 숨긴다.
                s.enabled = False
                log.info("외부 타일 %s 는 주소가 없어 숨긴다 — 쓰려면 backend/config/%s 에 '%s: {url: ...}'",
                         s.id, LOCAL_OVERLAY, s.id)
                return
            log.warning("외부 타일 %s 에 주소가 없다 — backend/config/%s 에 '%s: {url: ...}' 를 적어라(곧 공개로 둔다)",
                        s.id, LOCAL_OVERLAY, s.id)
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
            if s.hide_unless_routed:
                s.enabled = False  # visible_for 가 거른다 — 사내 전용 연계는 '곧 공개' 로도 안 보인다

    def reload(self) -> int:
        raw = yaml.safe_load(self._catalog_path.read_text(encoding="utf-8")) or {}
        catalog = CatalogFile.model_validate(raw)  # raises on malformed entries
        routes = self._load_routes()
        # 이 박스의 nginx 에 location 이 생기는 경로 접두어 — 라우트 파일(routes.env + routes.local.env) 키의 첫 마디다
        # (`mx-white-paper/api` → mx-white-paper). SYS_<ID>_URL 은 타일은 켜도 location 은 만들지 않아 세지 않는다.
        self._routed = {k.split("/")[0] for k in routes}
        overlay = self._load_local_overlay()

        seen: set[str] = set()
        for s in catalog.systems:
            if s.id in seen:
                raise ValueError(f"duplicate system id in catalog: {s.id}")
            seen.add(s.id)
            ov = overlay.get(s.id) or {}
            if ov and s.integration_type != "external-url":
                # 핸드오프 타일의 url 은 **서명된 로그인 토큰을 보내는 곳**이다 — 추적되지 않는 파일로 바꾸게 두지 않는다
                # (routes 파일도 그 url 은 못 덮는다). 이 덮어쓰기는 외부 직결 주소 전용이다(검토 1차).
                log.warning("%s 의 '%s' 는 외부 타일이 아니라 무시한다(%s)", LOCAL_OVERLAY, s.id, s.integration_type)
                ov = {}
            for k, v in ov.items():
                if k in _OVERLAY_KEYS and v:
                    setattr(s, k, str(v))
            self._apply_route(s, routes)
        # 카탈로그에 없는 id 는 경고만 하고 버렸다 — 박스에만 있는 서비스의 바로가기 하나를 붙이려면 추적 파일을 고쳐야 했다
        # (8차 요청 §4-(3)). ⚠ 새 타일은 권한 표의 어느 플랫폼에도 없다. access.local.yaml 에 그 플랫폼(systems: [<id>])을
        # 같이 적지 않으면 권한과 무관하게 모두에게 보인다(filter_tiles 는 표에 없는 타일을 막지 않는다).
        for unknown in sorted(set(overlay) - seen):
            spec = {**overlay[unknown], "id": unknown}
            # url 한 칸만 있으면 오타일 가능성이 크다 — 지금처럼 경고만(name 이 있어야 새 타일로 본다)
            if "name" not in spec:
                log.warning("%s 의 '%s' 는 카탈로그에 없는 타일이다 — 오타인지 보라(새 타일이면 name 을 적는다)",
                            LOCAL_OVERLAY, unknown)
                continue
            # 핸드오프 타일은 서명된 로그인 토큰을 보내는 곳 — 추적되지 않는 파일로 새로 만들게 두지 않는다(위의 덮어쓰기 금지와 같은 이유)
            if spec.get("integration_type", "external-url") != "external-url":
                log.warning("%s 의 '%s' 는 external-url 만 새로 만들 수 있다 — 무시한다(%s)",
                            LOCAL_OVERLAY, unknown, spec.get("integration_type"))
                continue
            try:
                s = LinkedSystem.model_validate(spec)
            except ValidationError as exc:
                # 틀린 칸의 이름만 말한다 — pydantic 원문은 그 칸의 값을 인용하는데 박스 파일의 주소는 사내 주소다.
                bad = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
                log.warning("%s 의 '%s' 를 타일로 읽지 못했다 — 무시한다(틀린 칸: %s)", LOCAL_OVERLAY, unknown, ", ".join(bad))
                continue
            self._apply_route(s, routes)
            catalog.systems.append(s)

        self._systems = sorted(catalog.systems, key=lambda s: (s.sort_order, s.name))
        return len(self._systems)

    def _load_local_overlay(self) -> dict[str, dict]:
        p = self._catalog_path.with_name(LOCAL_OVERLAY)
        if not p.exists():
            return {}
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"{p}: '<타일 id>: {{url: ...}}' 모양이어야 한다")
        out: dict[str, dict] = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                out[str(k)] = v
                continue
            # `<id>: <주소>` 처럼 값에 바로 적은 항목 — 종전엔 경고 없이 사라져 '적었는데 왜 안 뜨나' 를 찾을 수 없었다.
            # 값은 싣지 않는다(박스 파일의 주소는 사내 주소다) — 어느 id 인지와 맞는 모양만 말한다.
            log.warning("%s 의 '%s' 는 읽지 않는다 — 값이 매핑이 아니다. 한 단 들여 `url: <주소>`(새 타일이면 name 도)로 적는다",
                        LOCAL_OVERLAY, k)
        return out

    def all(self) -> list[LinkedSystem]:
        return list(self._systems)

    def routed_prefixes(self) -> set[str]:
        """이 박스에 리버스 프록시 라우트가 있는 경로 접두어(/<접두어>/…) — 로그아웃이 하위 서비스 목록을 고를 때 쓴다."""
        return set(self._routed)

    def live_ids(self) -> set[str]:
        """이 박스에서 실제로 열리는 타일 — 켜져 있고 목적지가 있다(권한 표의 플랫폼 숨김이 쓴다)."""
        return {s.id for s in self._systems if s.enabled and s.status == "available"}

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
