# 소속·허가 API — 내 권한·허가 요청(사용자), 소속·허가 편집·요청 결정(관리자), 게이트웨이 조회
from __future__ import annotations

import hmac
import json
import logging
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.access.policy import ADMIN_GROUP, compute
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.auth.routes.connections import _invalidate_gateway_cache
from app.auth.user_store import norm_email
from app.config import Settings, get_settings
from app.deps import get_current_principal, require_csrf, require_role

logger = logging.getLogger(__name__)
router = APIRouter(tags=["access"])


def _store(request: Request):
    return request.app.state.user_store


def _policy(request: Request):
    return request.app.state.access.get()


def _hidden(request: Request, policy) -> set[str]:
    """이 박스에서 안 열리는 사내 전용 플랫폼(예: Knox 연계) — 권한 표·요청에서 뺀다. 표시만 가린다."""
    catalog = getattr(request.app.state, "catalog", None)
    return policy.hidden_keys(catalog.live_ids()) if catalog is not None else set()


def _reason_text(reason: str, policy, affiliation: str) -> str:
    """사람에게 보일 허가 이유."""
    if reason == "admin":
        return "관리자"
    if reason == "grant":
        return "개별 허가"
    if reason == "affiliation":
        label = (policy.affiliations.get(affiliation) or {}).get("label") or affiliation
        return f"소속 기본({label})"
    if reason == "default":
        return "모든 사용자 기본"
    if reason.startswith("implied:"):
        src = policy.item(reason.split(":", 1)[1])
        return f"{src.label if src else reason}에 포함"
    return reason


def _taglines(request: Request) -> dict[str, str]:
    """앱 타일 id → 한 줄 소개(systems.yaml tagline). 권한 표의 플랫폼 줄에 설명이 없어 무엇을 요청하는지 알 수 없었다
    (docs/ui-refresh 단계 4) — access.yaml 에 desc 가 없으면 그 플랫폼 타일의 소개를 빌린다."""
    catalog = getattr(request.app.state, "catalog", None)
    if catalog is None:
        return {}
    return {s.id: s.tagline for s in catalog.all() if getattr(s, "tagline", None)}


def _table(policy, ents, pending: dict[str, dict], hidden: set[str], taglines: dict[str, str] | None = None) -> dict:
    def row(i):
        allowed = i.key in ents.keys
        desc = i.desc or next((taglines[s] for s in i.systems if s in (taglines or {})), "")
        return {"key": i.key, "id": i.id, "label": i.label, "desc": desc, "allowed": allowed,
                "reason": (_reason_text(ents.reasons[i.key], policy, ents.affiliation)
                           if allowed else ""),
                "request": pending.get(i.key),
                # 게이트웨이 백엔드가 딸린 항목 — PAT(개인 Claude) 로 열리는 것이 이것들이다(TokenPage).
                "tools": bool(i.gateway)}
    return {"features": [row(i) for i in policy.items if i.kind == "feature"],
            "platforms": [row(i) for i in policy.items if i.kind == "platform" and i.key not in hidden]}


@router.get("/auth/access")
def my_access(request: Request, principal: Principal = Depends(get_current_principal),
              settings: Settings = Depends(get_settings)) -> dict:
    """내 권한 — 모든 기능·플랫폼에 대해 쓸 수 있나, 왜, 요청했으면 그 상태."""
    policy = _policy(request)
    ents = getattr(request.state, "entitlements", None) or compute(
        policy, groups=principal.groups, row=_store(request).get(principal.email),
        admin_emails=settings.portal_admin_email_set)
    pending = {}
    for r in _store(request).list_requests(email=principal.email, limit=500):
        if r["key"] not in pending:           # 최신순 — 키마다 가장 최근 요청만
            pending[r["key"]] = {"id": r["id"], "status": r["status"],
                                 "created_at": r["created_at"]}
    aff = policy.affiliations.get(ents.affiliation)
    return {"affiliation": ents.affiliation, "affiliation_label": (aff or {}).get("label") or "",
            "is_admin": ents.is_admin, **_table(policy, ents, pending, _hidden(request, policy), _taglines(request))}


class AccessRequestIn(BaseModel):
    key: str = Field(min_length=6, max_length=80)
    note: str = Field(default="", max_length=500)


@router.post("/auth/access/requests")
def request_access(body: AccessRequestIn, request: Request,
                   principal: Principal = Depends(get_current_principal),
                   _csrf: None = Depends(require_csrf)) -> dict:
    policy = _policy(request)
    if policy.item(body.key) is None or body.key in _hidden(request, policy):
        raise AuthError("모르는 권한입니다", status_code=404)
    if body.key in principal.groups:
        raise AuthError("이미 쓸 수 있는 권한입니다", status_code=409)
    return _store(request).create_request(email=principal.email, key=body.key, note=body.note)


# ── 허브에 보일 앱(개인 MCP 시야에서 끄기 — docs/mcp-app-toggle) ─────────────────────
# 끄기는 권한이 아니라 선호다: 게이트웨이가 **개인 PAT** 의 tools/list·search_tools·list_tool_apps 에서만 숨기고,
# 이름을 주면 invoke_tool 로는 여전히 부른다(D-3). 웹 챗·웹 심의·절차는 영향 없다(D-2). Claude Code 에서 돌리는 심의
# 워크플로는 개인 PAT 라 적용된다 — 파이프라인이 필수 도구(보고서 저장·근거 조회)는 이름으로 부른다(D-7).
_APP_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
_HUB_NOTE = ("끈 앱은 개인 Claude(Code·Desktop 등)의 허브 도구 목록과 search_tools 에서 빠진다. search_tools 는 바로, "
             "열려 있는 Claude 세션의 도구 목록은 재연결해야 바뀐다(Claude Code: /mcp 에서 hwax 재연결 또는 재시작 · "
             "Desktop: 완전히 종료 후 다시 실행). 포털 웹 챗·웹 심의에는 영향이 없다.")


async def _gateway_apps(settings: Settings) -> list[dict] | None:
    """게이트웨이 `/tools-map` 의 apps[](라벨·도구 수·연결) — 브라우저는 못 닿는다(nginx 404).
    `_gateway`(허브 자체 도구)는 끌 수 없으므로 뺀다. 못 닿으면 None."""
    base = (settings.mcp_gateway_url or "").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.get(f"{base}/tools-map")
        if r.status_code != 200:
            return None
        apps = (r.json() or {}).get("apps") or []
    except Exception:  # noqa: BLE001 — 게이트웨이 불통은 '목록 없음'이 아니라 '모름'이다(502)
        return None
    return [a for a in apps if isinstance(a, dict) and a.get("app") and a.get("app") != "_gateway"]


def _hub_apps_view(policy, ents, apps: list[dict], muted: set[str]) -> dict:
    rows, known = [], set()
    for a in apps:
        key = str(a["app"])
        known.add(key)
        need = policy.keys_for_gateway([key])
        rows.append({"app": key, "label": str(a.get("label") or key),
                     "description": str(a.get("description") or "")[:300],
                     "tool_count": int(a.get("tool_count") or 0), "reachable": bool(a.get("reachable")),
                     # 포털 권한 표 기준(게이트웨이도 같은 표로 막는다). 권한 없는 앱은 끄지 않아도 안 보인다.
                     "allowed": (not need) or bool(set(need) & set(ents.keys)),
                     "muted": key in muted})
    # 지금 게이트웨이에 없는 앱을 끈 기록 — 조용히 사라지지 않게 보인다(내려간 앱이 돌아오면 그대로 꺼져 있다)
    for key in sorted(muted - known):
        rows.append({"app": key, "label": key, "description": "", "tool_count": 0, "reachable": False,
                     "allowed": True, "muted": True, "absent": True})
    return {"apps": rows, "muted": sorted(muted), "note": _HUB_NOTE}


@router.get("/auth/access/apps")
async def my_hub_apps(request: Request, principal: Principal = Depends(get_current_principal),
                      settings: Settings = Depends(get_settings)) -> dict:
    """허브에 보일 앱 — 앱마다 도구 수·연결·권한·끔 여부."""
    policy = _policy(request)
    row = _store(request).get(principal.email) or {}
    ents = getattr(request.state, "entitlements", None) or compute(
        policy, groups=principal.groups, row=row or None, admin_emails=settings.portal_admin_email_set)
    apps = await _gateway_apps(settings)
    if apps is None:
        raise AuthError("게이트웨이에 닿지 못해 앱 목록을 만들 수 없습니다 — 잠시 뒤 다시 여세요", status_code=502)
    return _hub_apps_view(policy, ents, apps, set(row.get("hub_muted_apps") or []))


class HubAppIn(BaseModel):
    muted: bool


@router.put("/auth/access/apps/{key}")
async def set_hub_app(key: str, body: HubAppIn, request: Request,
                      principal: Principal = Depends(get_current_principal),
                      settings: Settings = Depends(get_settings),
                      _csrf: None = Depends(require_csrf)) -> dict:
    """앱 **하나**를 끄거나 켠다(두 탭이 서로의 선택을 덮지 않게 — 저장소가 잠금 안에서 한 번에 고친다).
    끌 때는 지금 게이트웨이에 있는 앱만 받고, 켤 때는 언제든 받는다 — 게이트웨이에서 빠진 앱의 끈 기록도 지울 수 있게.
    바꾼 뒤 게이트웨이 캐시를 바로 깨서 search_tools 에 즉시 반영한다."""
    if key == "_gateway":
        raise AuthError("허브 자체 도구(_gateway)는 끌 수 없습니다", status_code=400)
    if not _APP_KEY.match(key):
        raise AuthError(f"모르는 앱입니다: {key[:80]}", status_code=400)
    apps = await _gateway_apps(settings)
    if apps is None:
        raise AuthError("게이트웨이에 닿지 못해 앱을 확인할 수 없습니다 — 잠시 뒤 다시 시도하세요", status_code=502)
    if body.muted and key not in {str(a["app"]) for a in apps}:
        raise AuthError(f"모르는 앱입니다: {key[:80]}", status_code=400)
    store = _store(request)
    new = store.set_hub_app_muted(principal.email, key, body.muted)
    if new is None:
        raise AuthError("계정 원장에 없는 사용자입니다 — 로그아웃 후 다시 로그인하세요", status_code=404)
    await _invalidate_gateway_cache(settings, principal.email)
    policy = _policy(request)
    ents = getattr(request.state, "entitlements", None) or compute(
        policy, groups=principal.groups, row=store.get(principal.email),
        admin_emails=settings.portal_admin_email_set)
    return _hub_apps_view(policy, ents, apps, set(new))


# ── 관리자 ──────────────────────────────────────────────────────────────────
@router.get("/auth/access/policy")
def access_policy(request: Request, _p: Principal = Depends(get_current_principal)) -> dict:
    """정책 표(기능·플랫폼·소속) — 관리자 화면의 체크 목록과 내 권한 페이지의 머리말."""
    policy = _policy(request)
    hidden = _hidden(request, policy)
    return {"features": [{"key": i.key, "label": i.label, "desc": i.desc,
                          "implies": list(i.implies)} for i in policy.items if i.kind == "feature"],
            "platforms": [{"key": i.key, "label": i.label, "desc": i.desc} for i in policy.items
                          if i.kind == "platform" and i.key not in hidden],
            "affiliations": [{"id": k, "label": v["label"], "grants": v["grants"]}
                             for k, v in policy.affiliations.items()],
            "default_grants": policy.default_grants}


@router.get("/auth/access/requests")
def list_access_requests(request: Request, status: str = Query(default="pending", max_length=20),
                         _admin: Principal = Depends(require_role(ADMIN_GROUP))) -> list[dict]:
    return _store(request).list_requests(status=status or None)


class DecideIn(BaseModel):
    approve: bool


@router.post("/auth/access/requests/{req_id}/decide")
def decide_access_request(req_id: int, body: DecideIn, request: Request,
                          admin: Principal = Depends(require_role(ADMIN_GROUP)),
                          _csrf: None = Depends(require_csrf)) -> dict:
    out = _store(request).decide_request(req_id, approve=body.approve, by=admin.email)
    if out is None:
        raise AuthError("대기 중인 요청이 아닙니다", status_code=404)
    return out


class UserAccessIn(BaseModel):
    affiliation: str | None = Field(default=None, max_length=40)
    grants: list[str] | None = Field(default=None, max_length=100)
    # 관리자 지정(true)·해제(false) — 안 주면 안 건드린다. 원장 groups 의 portal-admin 을 붙이거나 뗀다.
    admin: bool | None = None


def _set_admin(request: Request, settings: Settings, by: Principal, row: dict, on: bool) -> int:
    """관리자 지정·해제(10차 요청 §3) — 종전엔 활성 사용자의 관리자 여부를 바꾸는 라우트가 없었다. 폐기한 PAT 수를 돌려준다.

    거절하는 것 넷. 전부 **쓰기 전에** 본다(마지막 관리자만 저장소가 잠금 안에서 쓰기와 함께 본다).
      · 자기 자신 해제 — 실수 한 번으로 화면에서 스스로를 내보낸다.
      · 고정 관리자 해제 — PORTAL_ADMIN_EMAILS 는 박스 설정이라 원장을 고쳐도 그대로 관리자다. 됐다고 답하면 '해제했는데
        여전히 관리자' 가 된다 — 어디서 바꾸는지 말하고 거절한다.
      · 마지막 관리자 해제 — 아무도 이 화면을 못 열게 되면 되돌리는 길이 박스의 셸뿐이다.
      · 활성이 아닌 계정 지정 — 승인 대기는 '관리자로 승인' 으로, 정지는 다시 활성화한 뒤에.
    """
    target = row["email"]
    pinned = settings.portal_admin_email_set
    if on and row.get("status") != "active":
        raise AuthError("활성 계정만 관리자로 지정할 수 있습니다 — 승인 대기는 '관리자로 승인' 을 쓰고, "
                        "정지된 계정은 다시 활성화한 뒤에 지정하세요", status_code=409)
    if not on and target == norm_email(by.email or ""):
        raise AuthError("자기 자신의 관리자 권한은 해제할 수 없습니다 — 다른 관리자에게 요청하세요", status_code=409)
    if not on and target in pinned:
        raise AuthError("고정 관리자입니다 — 박스 설정 PORTAL_ADMIN_EMAILS 에 있는 주소라 화면에서 해제할 수 없습니다. "
                        "그 값에서 빼고 포털을 다시 띄워야 합니다", status_code=409)
    got = _store(request).set_admin(target, on, pinned=pinned)
    if got == "last":
        raise AuthError("마지막 관리자는 해제할 수 없습니다 — 먼저 다른 활성 사용자를 관리자로 지정하세요", status_code=409)
    if got != "set":
        return 0
    # ⚠ 해제는 그 사람의 PAT 까지 죽인다 — 정지 때와 같은 자리다(auth/routes/local.py). 관리자이던 때 받은 토큰에는 표지가
    # 박혀 있고(이 변경 전 발급분), 포털은 이제 그 표지를 안 믿지만 표지를 그대로 믿는 하위가 남아 있을 수 있다.
    revoked = 0
    if not on:
        ts = getattr(request.app.state, "token_store", None)
        revoked = ts.revoke_all_for(target) if ts is not None else 0
    # 누가 누구를 관리자로 만들거나 내렸는지는 남긴다 — WARNING 이어야 남는다(포털은 INFO 를 버린다).
    logger.warning("관리자 %s: %s by %s (PAT %d개 폐기)", "지정" if on else "해제", target, by.email, revoked)
    return revoked


@router.patch("/auth/access/users/{email}")
async def set_user_access(email: str, body: UserAccessIn, request: Request,
                          admin: Principal = Depends(require_role(ADMIN_GROUP)),
                          settings: Settings = Depends(get_settings),
                          _csrf: None = Depends(require_csrf)) -> dict:
    """소속·개별 허가·관리자 지정 편집. 표에 없는 키·소속은 거절한다 — 오타가 권한이 되지 않게.
    바꾼 뒤 게이트웨이의 그 사람 캐시를 깬다 — 게이트웨이는 권한(keys·is_admin)을 60초 들고 있어, 포털에서 거둔 권한이
    개인 Claude(PAT) 길로는 그동안 그대로 통했다(정지는 이미 깬다 — auth/routes/local.py). best-effort 다."""
    policy = _policy(request)
    if body.affiliation and body.affiliation not in policy.affiliations:
        raise AuthError(f"모르는 소속입니다: {body.affiliation}", status_code=422)
    if body.grants is not None:
        bad = [g for g in body.grants if policy.item(g) is None]
        if bad:
            raise AuthError(f"모르는 권한입니다: {', '.join(bad)}", status_code=422)
    store = _store(request)
    row = store.get(email)
    if row is None:
        raise AuthError("사용자가 없습니다", status_code=404)
    # 관리자 쪽을 먼저 한다 — 거절되면 소속·허가도 쓰지 않는다(반만 저장된 요청을 만들지 않는다).
    revoked = _set_admin(request, settings, admin, row, body.admin) if body.admin is not None else 0
    store.set_access(email, affiliation=body.affiliation, grants=body.grants)
    await _invalidate_gateway_cache(settings, row["email"])
    u = store.get(email) or {}
    return {"email": u.get("email"), "affiliation": u.get("affiliation") or "",
            "grants": u.get("grants") or [], "admin": ADMIN_GROUP in (u.get("groups") or []),
            "pats_revoked": revoked}


# ── 게이트웨이 내부 조회 — 공유 시크릿으로만 연다(connections 와 같은 문) ─────────────
def _internal(request: Request, settings: Settings) -> None:
    expected = settings.gateway_shared_token
    if not expected:
        raise AuthError("internal access disabled (GATEWAY_SHARED_TOKEN unset)", status_code=503)
    # 공유 시크릿은 **상수 시간**으로 본다 — `!=` 는 앞에서부터 갈려 길이·접두를 흘린다.
    # 같은 리포의 `require_csrf` 가 이미 `compare_digest` 를 쓴다(여기만 달랐다).
    if not hmac.compare_digest(request.headers.get("authorization", ""),
                               f"Bearer {expected}"):
        raise AuthError("forbidden", status_code=403)


@router.get("/internal/access/policy")
def internal_policy(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """게이트웨이 백엔드별 필요 권한 — 게이트웨이가 allowed_groups 로 쓴다(access-control D-4)."""
    _internal(request, settings)
    return {"backends": _policy(request).gateway_policy()}


@router.get("/internal/access/entitlements")
def internal_entitlements(request: Request, email: str = Query(min_length=3, max_length=200),
                          groups: str = Query(default="", max_length=2000),
                          settings: Settings = Depends(get_settings)) -> dict:
    """이 사람의 **지금** 권한 — 게이트웨이가 PAT 에 박힌 옛 그룹 대신 쓴다(D-2).
    groups 는 토큰이 가진 로그인 그룹인데 **판정에 쓰지 않는다** — 관리자 여부도 원장만 본다(10차 요청 §4). 게이트웨이가
    계속 보내므로 받기만 한다.

    `is_admin` 은 게이트웨이가 하위로 넘기는 그룹에 `portal-admin` 을 붙일지 정하는 값이다. 게이트웨이는 PAT 에 박힌 표지를
    떼고 이 칸이 **불리언 참**일 때만 다시 붙인다 — 칸 이름을 바꾸면 관리자 표지가 하위로 가지 않는다(같은 배포로 나간다).

    `affiliation` 도 함께 낸다 — 앱이 **소속 단위 읽기 공유**를 하려면 이 값이 필요하다
    (DynaForge 자동 반입 리포트, W-93). 소속은 원장 한 곳(`users.affiliation`)에서만 나오고
    정지된 계정은 `compute` 가 빈 값으로 내린다 — 권한과 같은 문을 지난다.
    `label` 은 사람에게 보일 이름일 뿐이다. **범위 판정은 id 로 한다**(라벨은 바뀔 수 있다)."""
    _internal(request, settings)
    policy = _policy(request)
    base = [g for g in groups.split(",") if g]
    row = _store(request).get(email)
    ents = compute(policy, groups=base, row=row, admin_emails=settings.portal_admin_email_set)
    # ⚠ **표에 없는 소속 id 는 빈 값으로 내린다.** 조직 개편으로 access.yaml 에서 소속을 지워도
    # 원장 `users.affiliation` 에는 옛 값이 남는다. 포털 권한은 그 순간 끊기는데(`compute` 의
    # `aff in policy.affiliations`), 이 응답만 옛 id 를 계속 내면 앱은 **없어진 소속으로** 예전
    # 구성원끼리 서로의 문서를 계속 읽는다 — 권한은 거둬졌는데 공유만 살아 있는 상태다.
    known = policy.affiliations.get(ents.affiliation) or {}
    aff = ents.affiliation if known else ""
    return {"email": email, "keys": sorted(ents.keys), "affiliation": aff,
            "affiliation_label": str(known.get("label") or ""),
            "is_admin": ents.is_admin,
            # 허브에서 끈 앱 — 게이트웨이가 개인 PAT 시야에서 숨긴다(docs/mcp-app-toggle). 권한과 무관한 선호다.
            "muted_apps": sorted((row or {}).get("hub_muted_apps") or [])}

@router.get("/internal/org-taxonomy")
def internal_org_taxonomy(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """전문가 조직도 라벨 정본 — 게이트웨이가 받아 MCP(클로드)에도 같은 계층을 보여 준다.

    ⚠ 정본은 `frontend/src/components/chat/orgTaxonomy.json` 파일 하나다. 프론트가 그 파일을
    import 하고 여기서는 같은 파일을 읽어 내보낸다 — 파이썬으로 옮겨 적으면 두 조직도가 갈린다
    (AIDataHub 는 도메인 **코드**만 주고 사람 이름표가 없어서 이 표가 필요하다)."""
    _internal(request, settings)
    path = Path(__file__).resolve().parents[3] / "frontend" / "src" / "components" / "chat" / "orgTaxonomy.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — 없으면 코드가 그대로 보이는 조직도가 된다(치명적이지 않다)
        raise AuthError(f"org taxonomy unavailable: {exc}", status_code=503) from exc
