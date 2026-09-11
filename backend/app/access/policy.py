# 소속·허가 정책(access.yaml) 로더와 유효 권한 계산 — 요청마다 원장 행으로 다시 계산한다
"""Access policy: features (feat:*) and platforms (plat:*), affiliation defaults, and the
per-request entitlement computation.

권한은 JWT·PAT 에 박힌 groups 를 믿지 않고 요청마다 원장(users.affiliation·grants)과 이 정책으로
다시 계산한다 — 거둔 권한이 세션 8시간·PAT 수명 동안 남지 않게(docs/access-control D-2).
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.config import Settings

logger = logging.getLogger(__name__)

ADMIN_GROUP = "portal-admin"
FEAT, PLAT = "feat:", "plat:"
WILDCARD = "*"


def is_synthetic(group: str) -> bool:
    """포털이 계산해 얹는 합성 그룹인가 — 들어온 값(JWT·PAT·헤더)에 섞여 있으면 버리고
    다시 계산한다."""
    return group.startswith(FEAT) or group.startswith(PLAT)


@dataclass(frozen=True)
class Item:
    key: str                     # feat:deliberation · plat:stepforge
    id: str
    kind: str                    # feature | platform
    label: str
    desc: str = ""
    implies: tuple[str, ...] = ()
    systems: tuple[str, ...] = ()   # 포털 타일 id
    gateway: tuple[str, ...] = ()   # 게이트웨이 백엔드 키


@dataclass
class Policy:
    items: list[Item]
    affiliations: dict[str, dict]        # id → {label, grants}
    default_grants: list[str]
    _by_key: dict[str, Item] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_key = {i.key: i for i in self.items}

    @property
    def keys(self) -> list[str]:
        return [i.key for i in self.items]

    def item(self, key: str) -> Item | None:
        return self._by_key.get(key)

    def direct(self, grants: list[str]) -> set[str]:
        """허가 목록 → 키 집합('*' 는 전부). 표에 없는 키는 버린다(오타가 권한이 되지 않게)."""
        out: set[str] = set()
        for g in grants or []:
            if g == WILDCARD:
                out |= set(self.keys)
            elif g in self._by_key:
                out.add(g)
        return out

    def implied_by(self, key: str) -> list[str]:
        item = self._by_key.get(key)
        return [k for k in (item.implies if item else ()) if k in self._by_key]

    def system_key(self, system_id: str) -> str | None:
        """포털 타일 → 그 타일을 여는 플랫폼 키."""
        return next((i.key for i in self.items if system_id in i.systems), None)

    def gateway_policy(self) -> dict[str, list[str]]:
        """게이트웨이 백엔드 → 그 백엔드 도구에 필요한 권한(하나라도 있으면 통과)."""
        out: dict[str, set[str]] = {}
        for i in self.items:
            for b in i.gateway:
                out.setdefault(b, set()).add(i.key)
        return {b: sorted(v) for b, v in sorted(out.items())}

    def keys_for_gateway(self, backends: list[str]) -> list[str]:
        """이 게이트웨이 백엔드들을 쓰려면 필요한 키들(HE팀 페르소나의 앱 → 플랫폼)."""
        return sorted({i.key for i in self.items for b in backends if b in i.gateway})


def parse_policy(raw: dict) -> Policy:
    items: list[Item] = []
    for kind, prefix, section in (("feature", FEAT, "features"), ("platform", PLAT, "platforms")):
        for d in raw.get(section) or []:
            items.append(Item(
                key=f"{prefix}{d['id']}", id=str(d["id"]), kind=kind,
                label=str(d.get("label") or d["id"]),
                desc=str(d.get("desc") or ""), implies=tuple(d.get("implies") or ()),
                systems=tuple(d.get("systems") or ()), gateway=tuple(d.get("gateway") or ())))
    keys = [i.key for i in items]
    if len(keys) != len(set(keys)):
        raise ValueError("access.yaml: 같은 id 가 두 번 있다")
    known = set(keys)
    for i in items:
        bad = [k for k in i.implies if k not in known]
        if bad:
            raise ValueError(f"access.yaml: {i.key} implies 에 없는 키 {bad}")
    affs: dict[str, dict] = {}
    for a in raw.get("affiliations") or []:
        grants = list(a.get("grants") or [])
        bad = [g for g in grants if g != WILDCARD and g not in known]
        if bad:
            raise ValueError(f"access.yaml: 소속 {a['id']} grants 에 없는 키 {bad}")
        affs[str(a["id"])] = {"label": str(a.get("label") or a["id"]), "grants": grants}
    default = list(raw.get("default_grants") or [])
    bad = [g for g in default if g != WILDCARD and g not in known]
    if bad:
        raise ValueError(f"access.yaml: default_grants 에 없는 키 {bad}")
    return Policy(items=items, affiliations=affs, default_grants=default)


class AccessPolicy:
    """access.yaml 을 mtime 으로 캐시한다 — 고치면 다음 요청부터 새 정책(재기동 불필요).
    고친 파일이 깨졌으면 직전 정책을 계속 쓰고 로그에 남긴다(권한이 통째로 사라지지 않게)."""

    def __init__(self, settings: Settings) -> None:
        self._path = Path(settings.resolve(settings.access_path))
        self._lock = threading.Lock()
        self._mtime: float | None = None
        self._policy: Policy | None = None

    def get(self) -> Policy:
        mtime = self._path.stat().st_mtime
        with self._lock:
            if self._policy is None or mtime != self._mtime:
                try:
                    raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
                    self._policy = parse_policy(raw)
                    self._mtime = mtime
                except Exception:
                    if self._policy is None:
                        raise
                    logger.exception("access.yaml 을 읽지 못해 직전 정책을 계속 쓴다")
                    self._mtime = mtime
            return self._policy


# ── 유효 권한 ────────────────────────────────────────────────────────────────
# 같은 키가 여러 이유로 허가되면 사람에게 가장 구체적인 이유를 보인다.
_REASON_RANK = {"default": 0, "affiliation": 1, "grant": 2, "admin": 3}


@dataclass
class Entitlements:
    keys: set[str]
    reasons: dict[str, str]          # key → admin | grant | affiliation | default | implied:<키>
    affiliation: str
    is_admin: bool


def compute(policy: Policy, *, groups: list[str], row: dict | None) -> Entitlements:
    """유효 권한 = 기본 ∪ 소속 ∪ 개별 허가 (+ 함의). portal-admin 은 전부.

    groups 는 로그인 때 받은 값(IdP·로컬)이고, 합성 그룹은 여기서 버린다 — PAT·JWT 에 박힌 옛
    권한이 다시 들어오지 않게. 관리자 여부는 로그인 값이나 원장 값 어느 쪽이든 인정한다."""
    base = [g for g in (groups or []) if not is_synthetic(g)]
    stored = list((row or {}).get("groups") or [])
    is_admin = ADMIN_GROUP in base or ADMIN_GROUP in stored
    aff = str((row or {}).get("affiliation") or "")
    reasons: dict[str, str] = {}

    def put(keys: set[str], why: str) -> None:
        for k in keys:
            if k not in reasons or _REASON_RANK[why] > _REASON_RANK.get(reasons[k], -1):
                reasons[k] = why

    if is_admin:
        put(set(policy.keys), "admin")
    else:
        put(policy.direct(policy.default_grants), "default")
        if aff in policy.affiliations:
            put(policy.direct(policy.affiliations[aff]["grants"]), "affiliation")
        put(policy.direct(list((row or {}).get("grants") or [])), "grant")
        for k in list(reasons):
            for imp in policy.implied_by(k):
                reasons.setdefault(imp, f"implied:{k}")
    return Entitlements(keys=set(reasons), reasons=reasons, affiliation=aff, is_admin=is_admin)


def with_entitlements(groups: list[str], ents: Entitlements) -> list[str]:
    """principal.groups 에 얹을 값 — 들어온 합성 그룹은 버리고 계산값으로 바꾼다."""
    return [g for g in (groups or []) if not is_synthetic(g)] + sorted(ents.keys)


def filter_tiles(policy: Policy, systems: list, groups: list[str]) -> list:
    """포털 타일 — 그 타일을 여는 플랫폼 허가가 있어야 보인다. 표에 없는 타일은 막지 않는다
    (test_access_policy 가 모든 타일이 표에 있는지 대조한다)."""
    have = set(groups or [])
    out = []
    for s in systems:
        key = policy.system_key(s.id)
        if key is None or key in have:
            out.append(s)
    return out
