# 배선 요청·설정 — config/setup_requests.yaml 을 읽고, 포털이 스스로 확인할 수 있는 것은 확인한다
"""GET /setup/requests — 아직 안 된 설정과 사람이 해야 하는 요청.

**왜 화면에 두나.** 이 스택에서 반복된 실패 모양이 "설정 한 줄이 빠졌는데 아무 데도 안
보인다" 였다. 배포는 성공하고 화면도 멀쩡한데 그 기능만 조용히 안 되는 식이다. 그래서
포털이 스스로 확인할 수 있는 것은 확인해 **안 된 것만** 띄우고, 확인할 수 없는 것(다른
박스의 파일·사람이 해야 하는 요청)은 목록으로 남긴다.

**확인은 전부 저렴하고 실패에 관대하다.** 이 화면이 느려지거나 500 을 내면 본래 목적인
"눈에 띄기" 가 도리어 방해가 된다. 확인이 안 되면 그 항목은 `unknown` 으로 남기지
`ok` 로 접지 않는다 — 모르는 것을 됐다고 말하는 것이 가장 나쁘다.

비밀은 **값이 아니라 있고 없음만** 본다. 응답에 시크릿·내부 주소를 싣지 않는다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import APIRouter, Depends, Request

from app.access.policy import ADMIN_GROUP, sso_default_problems
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal, require_csrf, require_role

router = APIRouter(prefix="/setup", tags=["setup"])

# 확인 하나가 오래 걸리면 홈 화면이 그만큼 늦는다. 짧게 끊고 모르면 모른다고 한다.
PROBE_TIMEOUT_S = 2.0

_cache: dict[str, Any] = {"mtime": None, "rows": []}


def _path(settings: Settings) -> Path:
    return Path(settings.resolve(settings.setup_requests_path))


def parse_requests(raw: Any) -> list[dict]:
    """YAML 본문 → 정규화된 항목. id·title 이 없으면 버린다(조용히 건너뛴다)."""
    rows = (raw or {}).get("requests") if isinstance(raw, dict) else None
    out: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not rid or not title:
            continue
        out.append({
            "id": rid,
            "title": title,
            "tag": str(row.get("tag") or "").strip(),
            "severity": str(row.get("severity") or "important").strip(),
            "check": str(row.get("check") or "").strip() or None,
            "manual": bool(row.get("manual")),
            # "셋업이 안 됐을 때 기본값이 들어가나" 에 대한 답. auto|generate|none.
            # 모르는 값은 none 으로 본다 — **기본값이 있다고 잘못 말하는 쪽이 더 나쁘다.**
            "default": (str(row.get("default") or "none").strip()
                        if str(row.get("default") or "none").strip() in ("auto", "generate", "none")
                        else "none"),
            "body": str(row.get("body") or "").strip(),
        })
    return out


def _load(settings: Settings) -> list[dict]:
    p = _path(settings)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return []
    if _cache["mtime"] != mtime:
        try:
            _cache["rows"] = parse_requests(yaml.safe_load(p.read_text("utf-8")))
        except Exception:          # 깨진 YAML 이 포털을 500 으로 만들지 않는다
            _cache["rows"] = []
        _cache["mtime"] = mtime
    return _cache["rows"]


async def _probe(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as c:
            r = await c.get(url)
        return r.status_code < 500
    except httpx.HTTPError:
        return False


def _tiles_outside_table(access: Any, catalog: Any) -> list[str]:
    """권한 표의 어느 플랫폼에도 없는 포털 타일 id. 그런 타일은 권한과 무관하게 모두에게 보인다(policy.filter_tiles 는 표에 없는
    타일을 막지 않는다). 떠 있는 카탈로그와 떠 있는 권한 표를 대조한다 — 박스 파일(systems.local.yaml)로 붙인 타일까지."""
    policy = access.get()
    return sorted(s.id for s in catalog.all() if policy.system_key(s.id) is None)


async def run_check(name: str, settings: Settings, access: Any, catalog: Any = None) -> str:
    """`ok` | `todo` | `unknown`. **모르면 모른다고 한다** — ok 로 접지 않는다."""
    if name == "ste_sso_secret":
        # 값은 보지 않는다. 있고 없음만.
        return "ok" if (settings.ste_sso_secret or "").strip() else "todo"

    if name == "ra_sso":
        # RA 사람별 위임 — 포털이 아는 것은 비밀의 있고 없음뿐이다(RA 쪽이 켜졌는지는 RA 담당 몫, docs/sso-delegation).
        return "ok" if (settings.ra_sso_secret or "").strip() else "todo"

    if name == "access_ste":
        # 정책 원장에 직접 묻는다 — 파일을 다시 파싱하면 두 곳이 어긋날 수 있다.
        # access 는 표를 캐시하는 로더(AccessPolicy)다 — 표는 get() 으로 꺼낸다. 로더에서 곧바로 `.items` 를 읽던 때는 예외가 삼켜져
        # 떠 있는 포털에서 늘 unknown 이었다(표에 ste 가 있어도 이 항목이 사라지지 않았다).
        try:
            backends = {b for item in access.get().items for b in (item.gateway or ())}
        except Exception:
            return "unknown"
        return "ok" if "ste" in backends else "todo"

    if name == "access_overlay":
        # 권한 표의 박스 오버레이(access.local.yaml) — 깨져서 직전 정책을 쓰는 중이거나 읽다가 버린 행이 있으면 안 된 것이다.
        # 파일이 없는 박스는 ok 다(오버레이는 선택이다). 무엇이 문제인지는 check_notes 가 싣는다.
        try:
            return "todo" if access.problems() else "ok"
        except Exception:
            return "unknown"

    if name == "tiles_in_access_table":
        # 박스 파일로 타일만 붙이고 플랫폼을 안 붙이면 그 타일은 모두에게 보인다 — 실행 중에 이것을 알리는 자리가 없었다
        # (추적 파일끼리는 시험이 대조하지만 운영 박스는 시험을 돌리지 않는다). 무엇이 빠졌는지는 check_notes 가 싣는다.
        try:
            return "todo" if _tiles_outside_table(access, catalog) else "ok"
        except Exception:
            return "unknown"

    if name == "sso_default_affiliation":
        # SSO 기본 소속 — 표에 없는 값(적용 안 됨)이거나 전권 소속(누구나 전권)이면 안 된 것이다. 꺼져 있으면 ok.
        try:
            return "todo" if sso_default_problems(access.get(), settings.sso_default_affiliation) else "ok"
        except Exception:
            return "unknown"

    if name == "ste_backend":
        base = (settings.ste_base_url or "").rstrip("/")
        return "ok" if base and await _probe(base + "/api/health") else "todo"

    if name in ("gateway", "gateway_ste"):
        base = (settings.mcp_gateway_url or "").rstrip("/")
        if not base:
            return "unknown"
        try:
            async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as c:
                r = await c.get(base + "/tools-map")
        except httpx.HTTPError:
            return "todo" if name == "gateway" else "unknown"
        if r.status_code >= 400:
            return "todo" if name == "gateway" else "unknown"
        if name == "gateway":
            return "ok"
        try:
            body = r.json()
        except ValueError:
            return "unknown"
        return "ok" if "ste" in str(body) else "todo"

    return "unknown"


def check_notes(name: str, settings: Settings, access: Any, catalog: Any = None) -> list[str]:
    """`todo` 인 확인이 **무엇 때문인지** — 고정 안내(body) 위에 그대로 뜬다. 박스마다 사유가 달라 YAML 에 적어 둘 수 없는 것만.

    여기 싣는 문장도 응답으로 나간다 — 비밀·내부 주소·사내 코드를 넣지 않는다(정책 로더가 값 대신 행 번호를 적는다)."""
    if name == "access_overlay":
        try:
            return list(access.problems())
        except Exception:
            return []
    if name == "tiles_in_access_table":
        try:
            ids = _tiles_outside_table(access, catalog)      # 타일 id 만 — 주소는 싣지 않는다
        except Exception:
            return []
        return [f"어느 플랫폼에도 없는 타일: {', '.join(ids)}"] if ids else []
    if name == "sso_default_affiliation":
        try:
            return [text for _code, text in sso_default_problems(access.get(), settings.sso_default_affiliation)]
        except Exception:
            return []
    return []


@router.get("/requests")
async def list_requests(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> dict:
    # 운영자 할 일이다 — 일반 사용자에게는 앱 목록보다 먼저 '필수 3' 노란 상자가 보였다(docs/ui-refresh 단계 1).
    # 403 이 아니라 빈 목록: 화면은 '다 됐으면 아무것도 안 그린다' 로 이미 그 경우를 안다.
    if ADMIN_GROUP not in (principal.groups or []):
        return {"items": [], "pending": 0}
    rows = _load(settings)
    access = getattr(request.app.state, "access", None)
    catalog = getattr(request.app.state, "catalog", None)
    store = getattr(request.app.state, "user_store", None)
    acks = store.setup_acks() if store is not None else {}

    out, acked = [], []
    for row in rows:
        manual = row["manual"] or not row["check"]
        # 사람이 '확인함' 한 manual 항목은 상자에서 빠지고 접힌 목록으로 간다 — 되돌릴 수 있게.
        # 포털이 확인하는 항목(check)은 확인함이 없다 — 고쳐지면 저절로 사라진다.
        if manual and row["id"] in acks:
            acked.append({"id": row["id"], "title": row["title"], **acks[row["id"]]})
            continue
        state = "manual" if manual else await run_check(row["check"], settings, access, catalog)
        if state == "ok":
            continue                      # 된 것은 화면에서 사라진다
        out.append({**row, "state": state,
                    "notes": [] if manual else check_notes(row["check"], settings, access, catalog)})
    return {"items": out, "pending": len(out), "acked": acked}


def _manual_row(settings: Settings, rid: str) -> dict:
    row = next((r for r in _load(settings) if r["id"] == rid), None)
    if row is None or not (row["manual"] or not row["check"]):
        raise AuthError("확인함은 포털이 스스로 확인할 수 없는(manual) 항목에만 씁니다", status_code=404)
    return row


@router.post("/requests/{rid}/ack", dependencies=[Depends(require_csrf)])
def ack_request(
    rid: str,
    request: Request,
    principal: Principal = Depends(require_role(ADMIN_GROUP)),
    settings: Settings = Depends(get_settings),
) -> dict:
    _manual_row(settings, rid)
    request.app.state.user_store.ack_setup(rid, by=principal.email or principal.subject)
    return {"ok": True}


@router.delete("/requests/{rid}/ack", dependencies=[Depends(require_csrf)])
def unack_request(
    rid: str,
    request: Request,
    principal: Principal = Depends(require_role(ADMIN_GROUP)),
    settings: Settings = Depends(get_settings),
) -> dict:
    _manual_row(settings, rid)
    return {"ok": request.app.state.user_store.unack_setup(rid)}
