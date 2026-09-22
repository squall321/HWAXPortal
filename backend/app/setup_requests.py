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

from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal

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


async def run_check(name: str, settings: Settings, access: Any) -> str:
    """`ok` | `todo` | `unknown`. **모르면 모른다고 한다** — ok 로 접지 않는다."""
    if name == "ste_sso_secret":
        # 값은 보지 않는다. 있고 없음만.
        return "ok" if (settings.ste_sso_secret or "").strip() else "todo"

    if name == "access_ste":
        # 정책 원장에 직접 묻는다 — 파일을 다시 파싱하면 두 곳이 어긋날 수 있다.
        try:
            backends = {b for item in access.items for b in (item.gateway or ())}
        except Exception:
            return "unknown"
        return "ok" if "ste" in backends else "todo"

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


@router.get("/requests")
async def list_requests(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> dict:
    rows = _load(settings)
    access = getattr(request.app.state, "access", None)

    out = []
    for row in rows:
        state = "manual" if row["manual"] or not row["check"] else \
            await run_check(row["check"], settings, access)
        if state == "ok":
            continue                      # 된 것은 화면에서 사라진다
        out.append({**row, "state": state})
    return {"items": out, "pending": len(out)}
