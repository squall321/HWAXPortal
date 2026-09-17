"""Liveness / readiness probes."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request) -> dict[str, object]:
    # Ready = startup wired the core singletons (auth provider, catalog, keystore).
    state = request.app.state
    catalog_count = len(state.catalog.all()) if getattr(state, "catalog", None) else 0
    return {
        "status": "ready",
        "auth_provider": getattr(state.auth_provider, "name", "unknown"),
        "systems": catalog_count,
        "mail_backend": getattr(state.mail_backend, "name", "unknown"),
        # 임시로 허용한 구성(예: prod_mock) — 기능 점검 때 한눈에 보이게. 문장이 아니라 코드만 싣는다(무인증 경로).
        "temporary": list(getattr(state, "startup_warnings", []) or []),
    }
