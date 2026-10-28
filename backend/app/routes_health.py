"""Liveness / readiness probes."""

import contextlib

from fastapi import APIRouter, Depends, Request

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
    return {
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
