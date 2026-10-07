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


def login_groups(groups: list[str] | None) -> list[str]:
    """로그인 때 받은 그룹(IdP·로컬)만 — 관리자 표지와 합성 그룹을 뺀 나머지. 토큰에 박는 것도, 토큰에서 믿는 것도 이것뿐이다.

    뺀 둘은 요청마다 원장으로 다시 정한다(`compute`). 박아 두면 그 값이 토큰 수명만큼 산다 — 관리자이던 때 받은 PAT(최대
    36,500일)의 `portal-admin` 이 해제 뒤에도 관리자로 통했고, 게이트웨이를 거쳐 하위 백엔드까지 내려갔다(10차 요청 §4)."""
    return [g for g in (groups or []) if g != ADMIN_GROUP and not is_synthetic(g)]


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
    # 그 타일이 이 박스에서 하나도 안 열리면 권한 표·요청에서 숨긴다(표시만 — 권한 계산·게이트웨이 정책은 그대로).
    hide_unless_routed: bool = False


@dataclass(frozen=True)
class SsoAffiliationRule:
    """SSO 로 **처음** 생기는 사람의 소속을 Claim 으로 정하는 한 줄 — 이 Claim 이 이 값이면 이 소속."""
    claim: str
    value: str
    affiliation: str


@dataclass
class Policy:
    items: list[Item]
    affiliations: dict[str, dict]        # id → {label, grants}
    default_grants: list[str]
    # 박스 파일(access.local.yaml)에서만 온다 — Claim 값이 사내 식별자라 추적 파일에 적지 않는다. 파일에 적힌 순서 그대로다.
    sso_affiliation_map: tuple[SsoAffiliationRule, ...] = ()
    # 읽다가 버린 것(틀린 행·읽지 않는 절) — 관리자의 배선 설정에 뜬다(AccessPolicy.problems).
    warnings: tuple[str, ...] = ()
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

    def hidden_keys(self, live_systems: set[str]) -> set[str]:
        """이 박스에서 숨길 플랫폼 키 — `hide_unless_routed` 인데 그 타일이 하나도 안 열린다."""
        return {i.key for i in self.items
                if i.hide_unless_routed and not (set(i.systems) & live_systems)}

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


# 박스 파일에서 읽는 절은 이 둘뿐이다. 소속·기본 허가·기능까지 받으면 추적되지 않는 파일 한 줄이 전원의 권한을 바꾼다.
LOCAL_SECTIONS = ("platforms", "sso_affiliation_map")
_NOTES = "_load_notes"      # load_raw → parse_policy 로 넘기는 '읽지 않은 것' 메모


def local_path(path: Path) -> Path:
    """access.yaml → 옆의 access.local.yaml(gitignore, 박스별)."""
    return path.with_name(path.stem + ".local" + path.suffix)


def _read_yaml(path: Path):
    # 문자열이 아니라 파일로 넘긴다 — 문법 오류의 위치 표시에 파일 이름이 실려 어느 파일이 깨졌는지 말할 수 있다(_brief).
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_raw(path: Path) -> dict:
    """access.yaml + 옆의 access.local.yaml(gitignore). platforms 는 id 기준 추가·치환, 나머지 절은 본 파일 그대로.

    systems.local.yaml·routes.local.env 는 오버레이가 있는데 권한 표에만 없어서, 박스에만 있는 앱을 붙일 때마다 추적 파일을
    고쳐야 했다(8차 요청 §4-(1)). 정책을 읽는 곳은 **전부 이 함수를 지난다** — 시험이 추적 파일만 읽으면 오버레이로 붙인
    백엔드를 '표에 없다' 고 보고 조용히 갈라진다.
    `sso_affiliation_map` 은 반대로 **박스 파일에서만** 받는다 — 매핑 키(회사·부서 코드)가 사내 식별자다.
    읽지 않은 것은 조용히 넘기지 않고 메모로 넘긴다(parse_policy 가 warnings 에 싣는다)."""
    raw = _read_yaml(path) or {}
    local = local_path(path)
    notes: list[str] = []
    if raw.pop("sso_affiliation_map", None) is not None:
        notes.append(f"{path.name} 의 sso_affiliation_map 은 읽지 않는다 — Claim 값은 사내 식별자라 {local.name} 에만 적는다")
    if local.exists():
        ov = _read_yaml(local) or {}
        if not isinstance(ov, dict):
            raise ValueError(f"{local.name}: 'platforms:' · 'sso_affiliation_map:' 절을 가진 매핑이어야 한다")
        by_id = {str(d["id"]): d for d in raw.get("platforms") or []}
        for d in ov.get("platforms") or []:
            by_id[str(d["id"])] = d
        raw["platforms"] = list(by_id.values())
        if "sso_affiliation_map" in ov:
            raw["sso_affiliation_map"] = ov["sso_affiliation_map"]
        ignored = sorted(str(k) for k in set(ov) - set(LOCAL_SECTIONS))
        if ignored:
            notes.append(f"{local.name} 의 {', '.join(ignored)} 절은 읽지 않는다 — 박스 파일은 "
                         f"{' · '.join(LOCAL_SECTIONS)} 만 받는다(나머지는 {path.name})")
    if notes:
        raw[_NOTES] = notes
    return raw


def _bad_sso_row(row: object, affiliations: dict[str, dict]) -> str | None:
    """sso_affiliation_map 한 행이 못 쓸 행이면 그 이유. ⚠ Claim **값**은 이유에 싣지 않는다 — 관리자 화면·로그로 나간다."""
    if not isinstance(row, dict):
        return "'{claim, value, affiliation}' 모양이 아니다"
    for k in ("claim", "value", "affiliation"):
        v = row.get(k)
        # 따옴표 없는 코드는 YAML 이 숫자로 읽는다(0123 → 83) — 문자열로 바꿔 받으면 영영 안 맞는 행이 조용히 남는다.
        if not isinstance(v, str) or not v.strip():
            return f"{k} 가 비었거나 문자열이 아니다(코드는 따옴표로 감싼다 — 숫자로 읽히면 앞자리 0 이 사라진다)"
    aff = row["affiliation"].strip()
    if aff not in affiliations:
        return f"모르는 소속 {aff!r}(affiliations 에 없다)"
    return None


def parse_policy(raw: dict) -> Policy:
    items: list[Item] = []
    for kind, prefix, section in (("feature", FEAT, "features"), ("platform", PLAT, "platforms")):
        for d in raw.get(section) or []:
            items.append(Item(
                key=f"{prefix}{d['id']}", id=str(d["id"]), kind=kind,
                label=str(d.get("label") or d["id"]),
                desc=str(d.get("desc") or ""), implies=tuple(d.get("implies") or ()),
                systems=tuple(d.get("systems") or ()), gateway=tuple(d.get("gateway") or ()),
                hide_unless_routed=bool(d.get("hide_unless_routed", False))))
    keys = [i.key for i in items]
    if len(keys) != len(set(keys)):
        raise ValueError("access.yaml: 같은 id 가 두 번 있다")
    known = set(keys)
    for i in items:
        if i.hide_unless_routed and not i.systems:
            raise ValueError(f"access.yaml: {i.key} hide_unless_routed 는 systems 가 있는 플랫폼에만 쓴다")
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
    # SSO Claim → 소속 표. 위의 절들과 달리 틀린 행은 **던지지 않고 버린다** — 박스 파일의 오타 한 줄이 권한 표 전체를 멈추면
    # 안 된다. 대신 조용히 버리지 않는다: 모르는 소속으로 가는 행이 남으면 그 사람은 소속 없이(기본 권한) 생기고 아무도 모른다.
    notes = [str(n) for n in raw.get(_NOTES) or []]
    rows = raw.get("sso_affiliation_map") or []
    if not isinstance(rows, list):
        notes.append("sso_affiliation_map 이 목록이 아니다 — 통째로 버렸다('- {claim: …, value: …, affiliation: …}' 를 줄마다)")
        rows = []
    rules: list[SsoAffiliationRule] = []
    for n, row in enumerate(rows, 1):
        why = _bad_sso_row(row, affs)
        if why:
            notes.append(f"sso_affiliation_map {n}번째 행을 버렸다 — {why}")
            continue
        rules.append(SsoAffiliationRule(claim=row["claim"].strip(), value=row["value"].strip(),
                                        affiliation=row["affiliation"].strip()))
    for note in notes:
        logger.warning("권한 표: %s", note)
    return Policy(items=items, affiliations=affs, default_grants=default,
                  sso_affiliation_map=tuple(rules), warnings=tuple(notes))


# ── SSO 로 처음 생기는 사람의 소속 ────────────────────────────────────────────
# SSO 신규 가입자는 소속 없이 생겨 기본 권한(일반 챗)만 받았고, 관리자가 찾아 지정할 때까지 막혀 있었다(10차 요청 §2 —
# 2026-10-07 실측 16명). 처음 생길 때 Claim 으로 소속을 정한다. ⚠ 여기서 정하는 것은 **넣을 값**뿐이다 — 넣는 자리는
# 원장의 최초 INSERT 하나다(user_store.note_sso_login). 이미 있는 행에 다시 계산해 넣으면 관리자가 거둔 소속이 되살아난다.
def claim_values(attrs: dict, claim: str) -> list[str]:
    """Assertion 속성(이름 → 값 목록)에서 이 Claim 의 값들. 없으면 [].

    이름은 **정확한 키**가 먼저다 — SAML_ATTR_* 설정과 같은 규칙이고 모호할 수가 없다(운영 ADFS 는 전체 URI 를 준다).
    '/' 도 ':' 도 없는 짧은 이름(CompId)은 마지막 경로 조각이 통째로 같은 속성이 그 Assertion 에 **하나뿐일 때만** 잇는다.
    둘 이상이면 고르지 않는다 — 다른 네임스페이스의 같은 이름이 소속을 정하면 안 된다. 그때는 전체 이름으로 적는다."""
    if claim in attrs:
        return [str(v) for v in attrs[claim] or []]
    if "/" in claim or ":" in claim:
        return []
    hits = sorted(k for k in attrs if "/" in str(k) and str(k).rsplit("/", 1)[-1] == claim)
    if len(hits) > 1:
        # Claim **이름**만 적는다 — 값은 사내 코드·개인정보다.
        logger.warning("SSO 소속 매핑: 짧은 Claim 이름 %r 에 맞는 속성이 둘 이상이라 고르지 않는다 — "
                       "access.local.yaml 에 전체 이름으로 적을 것: %s", claim, hits)
        return []
    return [str(v) for v in attrs[hits[0]] or []] if hits else []


def first_sso_affiliation(policy: Policy, attrs: dict, default: str = "") -> tuple[str, str, str]:
    """SSO 로 **처음** 생기는 사람에게 넣을 (소속 id, 출처, 사람용 근거). 출처는 'map' | 'default' | ''(안 넣는다).

    표(sso_affiliation_map)를 파일 순서대로 보아 처음 맞는 행이 이긴다. 값은 앞뒤 공백만 떼고 글자 그대로 견준다.
    맞는 행이 없을 때만 기본 소속(SSO_DEFAULT_AFFILIATION)이다. 어느 쪽이든 **표에 있는 소속만** 돌려준다 — 표의 행은 읽을 때
    걸렀고(parse_policy), 기본 소속은 여기서 본다. 모르는 값이 원장에 들어가면 권한 계산이 조용히 버려 다시 '막힌 사람' 이 된다."""
    for n, rule in enumerate(policy.sso_affiliation_map, 1):
        if any(v.strip() == rule.value for v in claim_values(attrs, rule.claim)):
            return rule.affiliation, "map", f"sso_affiliation_map {n}번째 행 · Claim {rule.claim}"
    default = (default or "").strip()
    if not default:
        return "", "", ""
    if default not in policy.affiliations:
        logger.warning("SSO_DEFAULT_AFFILIATION=%r 는 권한 표의 affiliations 에 없다 — 적용하지 않았다(소속 없이 생긴다)", default)
        return "", "", ""
    return default, "default", "SSO_DEFAULT_AFFILIATION"


def sso_default_problems(policy: Policy, default: str) -> list[tuple[str, str]]:
    """기본 소속 설정의 문제 — (코드, 사람용 문장). 기동 로그와 관리자의 배선 설정이 같은 문장을 쓴다.

    `unknown` 은 오타다(적용되지 않는다). `wildcard` 는 **막지 않는다** — 운영자의 결정일 수 있다. 다만 grants 가 '*' 인 소속을
    기본으로 주면 IdP 를 통과한 누구나 처음 로그인하는 순간 전권이라, 조용히 두지 않는다."""
    default = (default or "").strip()
    if not default:
        return []
    aff = policy.affiliations.get(default)
    if aff is None:
        return [("unknown", f"SSO_DEFAULT_AFFILIATION={default!r} 는 권한 표의 affiliations 에 없다 — 적용되지 않는다"
                            f"(SSO 로 처음 들어온 사람은 소속 없이 생긴다). 쓸 수 있는 값: {', '.join(sorted(policy.affiliations))}")]
    if WILDCARD in aff["grants"]:
        return [("wildcard", f"SSO_DEFAULT_AFFILIATION={default!r} 는 전권 소속이다(grants 에 '*') — IdP 를 통과한 사람은 "
                             "누구나 처음 로그인하는 순간 모든 기능·플랫폼을 받는다. 일부에게만 줄 것이면 값을 비우고 "
                             "access.local.yaml 의 sso_affiliation_map(Claim → 소속)을 쓴다")]
    return []


def _brief(exc: Exception) -> str:
    """읽기 실패를 관리자 화면에 실을 한 줄로. YAML 오류 원문은 그 줄의 **내용**을 인용한다 — 박스 파일에는 사내 코드가
    있어 어느 파일 몇 행인지만 말한다."""
    mark = getattr(exc, "problem_mark", None)
    if isinstance(exc, yaml.YAMLError) and mark is not None:
        return f"YAML 문법 오류({Path(str(mark.name)).name} {mark.line + 1}행)"
    if isinstance(exc, yaml.YAMLError):
        return "YAML 문법 오류"
    return f"{type(exc).__name__}: {exc}"[:200]


class AccessPolicy:
    """access.yaml(+ access.local.yaml)을 mtime 으로 캐시한다 — 고치면 다음 요청부터 새 정책(재기동 불필요).
    고친 파일이 깨졌으면 직전 정책을 계속 쓰고 로그에 남긴다(권한이 통째로 사라지지 않게). 그 상태는 `problems()` 로
    관리자 화면에도 뜬다 — 깨진 박스 파일이 '오버레이가 없는 것' 과 똑같이 보이면 그 박스의 백엔드가 표에서 빠진 줄 아무도 모른다.
    ⚠ 직전 정책이 **없을 때**(기동 뒤 첫 읽기) 깨져 있으면 던진다. 추적 파일만으로 넘어가지 않는다 — 박스 전용 백엔드가
    표에서 빠지고, 게이트웨이는 표에 없는 백엔드를 전체 공개로 본다."""

    def __init__(self, settings: Settings) -> None:
        self._path = Path(settings.resolve(settings.access_path))
        self._lock = threading.Lock()
        self._mtime: tuple[float, float | None] | None = None   # (본 파일, 박스 파일 — 없으면 None)
        self._policy: Policy | None = None
        self._stale: str | None = None      # 직전 정책을 쓰는 중이면 그 사유

    def _mtimes(self) -> tuple[float, float | None]:
        try:
            local = local_path(self._path).stat().st_mtime
        except OSError:
            local = None
        return (self._path.stat().st_mtime, local)

    def get(self) -> Policy:
        mtime = self._mtimes()
        with self._lock:
            if self._policy is None or mtime != self._mtime:
                try:
                    self._policy = parse_policy(load_raw(self._path))
                    self._mtime = mtime
                    self._stale = None
                except Exception as exc:
                    if self._policy is None:
                        raise
                    logger.exception("%s(또는 %s)을 읽지 못해 직전 정책을 계속 쓴다",
                                     self._path.name, local_path(self._path).name)
                    self._mtime = mtime
                    self._stale = (f"{self._path.name}(또는 {local_path(self._path).name})을 읽지 못해 "
                                   f"직전 정책을 계속 쓴다 — {_brief(exc)}")
            return self._policy

    def problems(self) -> list[str]:
        """관리자에게 보일 정책 읽기 문제 — 깨진 파일 때문에 직전 정책을 쓰는 중인가, 읽다가 버린 것이 있나.
        배선 설정(setup_requests 의 access_overlay)이 띄운다. 비어 있으면 문제없다."""
        policy = self.get()
        return ([self._stale] if self._stale else []) + list(policy.warnings)


# ── 유효 권한 ────────────────────────────────────────────────────────────────
# 같은 키가 여러 이유로 허가되면 사람에게 가장 구체적인 이유를 보인다.
_REASON_RANK = {"default": 0, "affiliation": 1, "grant": 2, "admin": 3}


@dataclass
class Entitlements:
    keys: set[str]
    reasons: dict[str, str]          # key → admin | grant | affiliation | default | implied:<키>
    affiliation: str
    is_admin: bool


def compute(policy: Policy, *, groups: list[str], row: dict | None,
            admin_emails: frozenset[str] = frozenset()) -> Entitlements:
    """유효 권한 = 기본 ∪ 소속 ∪ 개별 허가 (+ 함의). portal-admin 은 전부.

    **입력은 원장 행(row)과 박스 설정(admin_emails)뿐이다.** groups(세션·PAT 이 들고 온 값)는 권한에도 관리자 판정에도 쓰지
    않는다 — 호출부 서명을 지키려 받기만 한다. 예전엔 "로그인 값이나 원장 값 어느 쪽이든" 관리자로 인정해서, 원장에서 관리자를
    해제해도 그 사람이 들고 있던 세션(8시간)·PAT(최대 36,500일)이 계속 관리자였다(10차 요청 §4). IdP 그룹으로 관리자를 받던
    박스(mock·oidc-mock)는 원장이나 고정 목록에 적어야 한다(docs/change-request-8-10 D-3).

    admin_emails 는 언제나 관리자인 주소다(PORTAL_ADMIN_EMAILS — 소문자, 호출부가 settings.portal_admin_email_set 을 넘긴다).
    **원장 행의 이메일**과 글자 그대로 견준다. 행이 없는 신원은 목록에 있어도 관리자가 아니다 — 요청이 들고 온 이메일로 견주면
    원장에 없는 신원이 관리자가 되는 길이 생긴다. 안 넘긴 호출부는 고정 관리자를 일반 사용자로 본다(잊으면 닫히는 쪽)."""
    # ⚠ **정지된 계정은 권한이 0이다.** 여기가 원장 행을 권한으로 바꾸는 **유일한** 자리다 —
    # 포털 요청(`deps.entitled`)도, 게이트웨이가 읽는 `/internal/access/entitlements` 도
    # 이 함수를 지난다. 정지 검사를 포털 쪽에만 두면 **게이트웨이로는 그대로 통과한다**
    # (실측 2026-09-15: 정지 계정 PAT 로 MCP·REST 둘 다 200). 관리자 여부도 같이 내린다 —
    # `set_status` 는 `groups` 를 안 건드려서 정지된 관리자가 `portal-admin` 을 유지했다.
    if str((row or {}).get("status") or "") == "disabled":
        return Entitlements(keys=set(), reasons={}, affiliation="", is_admin=False)
    stored = list((row or {}).get("groups") or [])
    # 관리자는 원장의 표지, 또는 원장 행의 이메일이 고정 목록에 있을 때 — 세션·PAT 에 박힌 값은 믿지 않는다.
    # 정지는 위에서 이미 걸렀다(정지된 고정 관리자는 권한이 0이다).
    email = str((row or {}).get("email") or "").strip().lower()
    is_admin = ADMIN_GROUP in stored or bool(email and email in admin_emails)
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
    """principal.groups 에 얹을 값 — 들어온 합성 그룹과 관리자 표지는 버리고 계산값으로 바꾼다.

    ⚠ **관리자 표지는 들어온 값을 살리지 않고 `is_admin` 으로만 붙인다.** `require_role`·`ensure(principal, ADMIN_GROUP)` 는
    이 목록을 본다 — `compute` 만 고치고 여기서 토큰의 `portal-admin` 을 그대로 두면 판정은 '아니다' 인데 문은 열린다
    (10차 요청 §4). 반대쪽도 여기서 맞춘다: 토큰에 표지가 없는 **원장 관리자**에게 붙여 주지 않으면 기능 키는 전부 받으면서
    관리자 검사는 못 통과한다 — 막히는 쪽이라 조용하다(아무도 신고하지 않는다).
    """
    out = login_groups(groups) + sorted(ents.keys)
    if ents.is_admin:
        out.append(ADMIN_GROUP)
    return out


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
