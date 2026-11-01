# 관리자 '이용 통계' — 포털 안 원장을 읽을 때 세어 낸다(docs/ops-dashboard M1 · 사용자 결정 OD-4 — 사람별 줄도 합계도 관리자만)
"""문은 관리자 그룹 하나다(`require_role(ADMIN_GROUP)` — 접속 이력 · 전체 PAT 와 같은 문). `feat:` 키로 막지 않는다 — CAEG 가 `"*"` 를 쥐어
모든 키가 열린다(PLAN §2.3). 셈은 app/usage_stats.py 가 원장마다 읽기 전용 연결로 하고, 여기서는 이벤트 루프 밖(스레드)으로 넘긴다.

기간은 `days`(기본 30 · 1 ~ 400) 하나다 — 범위 밖 값은 거절하지 않고 붙잡아 맞춘 뒤 응답의 range 에 그대로 적는다(clamped).
"""
import asyncio
import logging

from fastapi import APIRouter, Depends, Query, Request

from app import usage_stats
from app.access.policy import ADMIN_GROUP
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import require_role

router = APIRouter(prefix="/auth/admin/usage", tags=["usage-stats"])
log = logging.getLogger(__name__)


def _labels(request: Request) -> dict:
    """화면에 이름으로 보일 것들 — 타일 이름 · 소속 라벨 · 권한 키 라벨. 못 읽으면 id 그대로 보인다(통계는 낸다)."""
    out: dict[str, dict[str, str]] = {"service": {}, "affiliation": {}, "key": {}}
    try:
        out["service"] = {s.id: s.name for s in request.app.state.catalog.all()}
    except Exception:  # noqa: BLE001 — 이름이 없어도 수는 낸다
        log.warning("이용 통계 — 타일 이름을 읽지 못해 id 로 보인다", exc_info=True)
    try:
        pol = request.app.state.access.get()
        out["affiliation"] = {k: str((v or {}).get("label") or k) for k, v in pol.affiliations.items()}
        out["key"] = {i.key: i.label for i in pol.items}
    except Exception:  # noqa: BLE001
        log.warning("이용 통계 — 권한 표를 읽지 못해 소속 · 권한 키를 id 로 보인다", exc_info=True)
    return out


@router.get("")
async def usage(
    request: Request,
    days: int = Query(usage_stats.DEFAULT_DAYS),
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """{generated_at, range, excluded, sections: {이름: {rows, note, …}}} — 칸의 차례 · 뜻은 usage_stats._SECTIONS 와 각 note."""
    labels = _labels(request)
    return await asyncio.to_thread(usage_stats.build, settings, days=days, labels=labels)
