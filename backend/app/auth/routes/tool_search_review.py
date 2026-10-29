# 관리자 '도구 검색 검토' — 게이트웨이 검색 고리 창구(/search-log · /search-review · /search-eval)를 공유 비밀로 부른다(docs/request-1029 E-9 ②)
"""cae00 에서 검색 고리를 닫는 사람 쪽 입구다(request-1029 C-31 — dev 의 QA 는 기준이 아니다).

질의 원문을 내므로 관리자만 보고, 표시 · 평가는 CSRF 를 요구한다. 포털은 아무것도 저장하지 않는다 — 표시는 게이트웨이의 박스 정답쌍
(`HWAXMcpGateway/tool_search_eval/pairs.local.jsonl`)에 남고, 평가는 떠 있는 게이트웨이가 그 박스의 카탈로그로 잰다.

게이트웨이 답을 포털 답으로 옮기는 법.
  · 공유 비밀 · 주소가 없다 → 503(무엇을 채울지 말한다).
  · 401 → 502 '공유 비밀이 다르다' · 404 · 405 → 502 '게이트웨이가 낡았다(창구 없음)'.
  · 400 · 409 는 게이트웨이의 사유 그대로(입력이 틀렸다 · 평가가 이미 돈다).
  · 닿지 못함 · 그 밖 → 502.
"""
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.access.policy import ADMIN_GROUP
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import require_csrf, require_role

router = APIRouter(prefix="/auth/admin/tool-search", tags=["tool-search-review"])

# 평가는 정답쌍 수 × 판 아홉만큼 돈다 — 게이트웨이 호출 한도(600초)와 같게 둔다
EVAL_TIMEOUT_S = 600.0


class ReviewIn(BaseModel):
    q: str = Field(min_length=1, max_length=500)
    verdict: Literal["ok", "gold", "remove"]
    gold: list[str] = Field(default_factory=list, max_length=10)     # '앱키:원래 이름' — 꼴은 게이트웨이가 본다
    memo: str = Field(default="", max_length=300)
    qid: str | None = Field(default=None, max_length=24)


async def _gateway(settings: Settings, method: str, path: str, *, params: dict | None = None, body: dict | None = None,
                   timeout: float = 30.0) -> dict:
    tok = settings.gateway_shared_token
    base = (getattr(settings, "mcp_gateway_url", "") or "").rstrip("/")
    if not (tok and base):
        raise AuthError("게이트웨이 공유 비밀(backend/.env GATEWAY_SHARED_TOKEN)이나 주소(MCP_GATEWAY_URL)가 없다", status_code=503)
    try:
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.request(method, f"{base}{path}", params=params, json=body,
                                  headers={"Authorization": f"Bearer {tok}"})
    except httpx.HTTPError as exc:
        raise AuthError(f"게이트웨이에 닿지 못했다({type(exc).__name__})", status_code=502) from exc
    if r.status_code == 200:
        return r.json()
    try:
        why = str((r.json() or {}).get("error") or "")
    except (ValueError, AttributeError):
        why = ""
    if r.status_code == 401:
        raise AuthError("게이트웨이가 공유 비밀을 거절했다 — 포털 GATEWAY_SHARED_TOKEN 과 게이트웨이 _gateway.token 이 다르다",
                        status_code=502)
    if r.status_code in (404, 405):
        raise AuthError("게이트웨이에 검색 고리 창구가 없다 — 게이트웨이가 이 판보다 낡았다(업데이트 · 재기동 뒤 다시)", status_code=502)
    if r.status_code in (400, 409):
        raise AuthError(why or f"게이트웨이 {r.status_code}", status_code=r.status_code)
    raise AuthError(f"게이트웨이 {r.status_code}" + (f" — {why[:200]}" if why else ""), status_code=502)


@router.get("/log")
async def search_log(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(200, ge=1, le=1000),
    q: str = Query("", max_length=200),
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """최근 질의(새것 먼저)마다 상위 다섯 · 보정 표지 · 뒤이은 호출 · 박스 표시."""
    return await _gateway(settings, "GET", "/search-log", params={"days": days, "limit": limit, "q": q})


@router.post("/review", dependencies=[Depends(require_csrf)])
async def search_review(
    body: ReviewIn,
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """사람 표시 → 박스 정답쌍. 같은 질의는 바꿔 쓰고 remove 는 지운다."""
    return await _gateway(settings, "POST", "/search-review", body=body.model_dump())


@router.post("/eval", dependencies=[Depends(require_csrf)])
async def search_eval(
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """떠 있는 카탈로그로 정답쌍(추적 + 박스)을 판마다 잰다 — 한 번에 하나."""
    return await _gateway(settings, "POST", "/search-eval", body={}, timeout=EVAL_TIMEOUT_S)
