"""Liveness / readiness probes."""

import contextlib

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    # Ready = startup wired the core singletons (auth provider, catalog, keystore).
    state = request.app.state
    systems = state.catalog.all() if getattr(state, "catalog", None) else []
    catalog_count = len(systems)
    temporary = list(getattr(state, "startup_warnings", []) or [])
    # 활성 관리자 0명(main.lifespan 의 같은 판정) — 기동 때 값이 아니라 **지금** 센다. 고정 목록의 사람이 처음 로그인하거나 원장에
    # 관리자가 생기면 재기동 없이 풀리는 상태라, 기동 때 한 번 센 값을 실으면 고친 뒤에도 다음 재기동까지 남는다.
    # 못 세면 싣지 않는다 — 모름을 0명으로 읽지 않는다. update-all §6 이 이 코드를 읽어 배포 로그에 올린다.
    store = getattr(state, "user_store", None)
    with contextlib.suppress(Exception):
        if store is not None and store.no_active_admin(settings.portal_admin_email_set):
            temporary.append("no_active_admin")
    out: dict[str, object] = {
        "status": "ready",
        "auth_provider": getattr(state.auth_provider, "name", "unknown"),
        "systems": catalog_count,
        "mail_backend": getattr(state.mail_backend, "name", "unknown"),
        # 임시로 허용한 구성(예: prod_mock) — 기능 점검 때 한눈에 보이게. 문장이 아니라 코드만 싣는다(무인증 경로).
        "temporary": temporary,
        # 진입 토큰에 소속을 싣는 시스템 — 떠 있는 카탈로그의 값이다(파일이 아니라). 박스 파일(systems.<박스>.yaml)이 덮었는지
        # 점검이 볼 길이 없었다(docs/request-1027 HP-40). id 만 싣는다.
        "claims_affiliation": sorted(s.id for s in systems if getattr(s, "claims_affiliation", False)),
    }
    # 상호작용 수집(docs/interaction-data) — 켠 박스에서만 싣는다(꺼진 박스의 답은 바이트까지 종전 그대로). 코드만 — 까닭 글은 로그 · 분석가 화면.
    if settings.interactions_enabled:
        from app.interactions import collector
        ok, body = collector.health(request.app, settings)
        out["interactions"] = {"ok": ok, "problems": body["problems"]}
    return out


@router.get("/health/interactions")
def interactions_health(request: Request, settings: Settings = Depends(get_settings)) -> JSONResponse:
    """상태판 줄(infra/scripts/gen-status-config.py) — 켠 박스에서만 있다(꺼지면 404). 수집이 멈췄거나 · 원천이 잇달아 실패하거나 · 게이트웨이 창고가
    넘치면 503(IX-9 — 실패가 정상처럼 보이지 않게). 무인증이라 상태 낱말 · 시각 · 코드만 싣는다."""
    if not settings.interactions_enabled:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    from app.interactions import collector
    ok, body = collector.health(request.app, settings)
    return JSONResponse(body, status_code=200 if ok else 503)
