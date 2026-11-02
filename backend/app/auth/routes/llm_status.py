# 관리자 'LLM · GPU 현황' — 호스트 수집기(infra/llm-status/collector.py)의 /snapshot · /series 를 대신 묻는다(docs/ops-dashboard PLAN §3.2)
"""수집기는 루프백에만 듣고 인증이 없다 — 사람은 이 창구로만 본다(관리자만, 사용자 결정 OD-4). 포털은 아무것도 저장하지 않는다.

수집기 답을 포털 답으로 옮기는 법(도구 검색 검토 `tool_search_review.py` 와 같은 꼴).
  · 주소가 없다(LLM_STATUS 를 켜지 않은 박스) → 503 '수집기가 꺼져 있다'(무엇을 켜면 되는지 말한다).
  · 닿지 못함 · 시간 초과 · 주소가 틀림 · 그 포트의 답이 수집기 꼴이 아님 · 그 밖의 상태 → 502 '수집기가 답하지 않는다'.
  · 400 · 404(그래프 조건이 틀렸다 · 모르는 대상)는 수집기의 사유 그대로.
프록시를 타지 않는다(trust_env=False — 루프백이다).
"""
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, Query

from app.access.policy import ADMIN_GROUP
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import require_role

router = APIRouter(prefix="/auth/admin/llm-status", tags=["llm-status"])

TIMEOUT_S = 10.0       # 수집기는 메모리에서 답한다 — 이보다 오래 걸리면 매달린 것이다
OFF = ("LLM/GPU 현황 수집기가 꺼져 있다 — infra/.env 에 LLM_STATUS=1 을 적고 update-all 을 돌린다"
       "(포털도 다시 떠야 화면이 수집기 주소를 받는다 — docs/ops-dashboard/server-setup.md)")
DOWN = "수집기가 답하지 않는다"
HINT = "./infra/scripts/services.sh status llm-status · 로그 /tmp/hwax-services/llm-status.log"


async def _collector(settings: Settings, path: str, *, params: dict | None = None, shape: str) -> dict:
    base = (settings.llm_status_url or "").strip().rstrip("/")
    if not base:
        raise AuthError(OFF, status_code=503)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S, trust_env=False) as cli:
            r = await cli.get(f"{base}{path}", params=params)
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
        raise AuthError(f"{DOWN}({type(exc).__name__}) — 수집기가 떠 있는지 본다({HINT})", status_code=502) from exc
    try:
        body = r.json()
    except ValueError:
        body = None
    if r.status_code == 200:
        if not isinstance(body, dict) or shape not in body:
            raise AuthError(f"{DOWN} — 그 포트의 답이 수집기 꼴이 아니다(LLM_STATUS_PORT 에 다른 것이 떠 있다 — docs/PORT-MAP.md)",
                            status_code=502)
        return body
    why = str(body.get("error") or "") if isinstance(body, dict) else ""
    if r.status_code in (400, 404) and why:
        raise AuthError(why[:300], status_code=r.status_code)
    raise AuthError(f"{DOWN}(HTTP {r.status_code})" + (f" — {why[:200]}" if why else f" — {HINT}"), status_code=502)


@router.get("")
async def llm_status(
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """서버마다 살아 있음 · 판 · 창 · 부하 · 속도 · 지연(≈) · 오류, '지금 쓰는 일'(HWAX 몫), Slurm · GPU 자리. 값은 모두 {value, at, source, error}."""
    return await _collector(settings, "/snapshot", shape="collector")


@router.get("/series")
async def llm_status_series(
    target: str = Query(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$"),
    metric: str = Query(..., min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$"),
    range_: Literal["1h", "24h", "7d", "35d"] = Query("1h", alias="range"),
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """한 대상 · 한 지표의 시계열 — 1h 는 15초 표본, 그보다 길면 5분 칸(평균 · 최대)."""
    return await _collector(settings, "/series", params={"target": target, "metric": metric, "range": range_}, shape="points")
