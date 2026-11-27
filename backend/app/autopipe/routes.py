# 자동 파이프라인 창구 /autopipe-api — 규칙 · 감지 주제 · 현황판 · 실행 · 승인 · 취소 · 보고서 · 한 박자(모두 feat:auto-pipeline, portal-api §6)
"""모든 창구는 세션 + 권한 feat:auto-pipeline(grant_only — 「전부」 · 관리자 전권에 딸려 오지 않는다, AP-9)이다. 쓰기(POST)는 CSRF 를 본다(검증은
저장하지 않아 빼다 — 문서 그대로).

스위치 AUTO_PIPELINE_ENABLED 가 꺼져 있으면 엔진이 돌지 않고 창구는 읽기 · 규칙 편집 · 검증만 된다 — 승인 · 취소 · 다시 확인 · 지금 돌리기 ·
한 박자는 409 다. update-all 이 포털을 내리기 전에 부르는 /internal/autopipe/quiesce 는 사람 창구가 아니라 공유 시크릿 문이다(AP-26).
창구 꼴은 portal-api.md §6 이 정본이다(화면이 같은 문서로 짓는다 — 꼴을 바꾸면 문서와 화면을 같이).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.access.routes import _internal

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.autopipe import FEAT
from app.autopipe import ra as RA
from app.autopipe import spec as S
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, require_csrf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autopipe-api", tags=["auto-pipeline"])
internal_router = APIRouter(tags=["auto-pipeline"])

HOW_TO_ENABLE = ("포털 infra/.env 에 AUTO_PIPELINE_ENABLED=1 을 적고 포털을 다시 띄운다(start.sh 가 넘긴다). 그 전에 게이트웨이 박스 파일 "
                 "service_tools.local.json 의 jobs.auto-pipeline.tools 에 계약 도구('<백엔드 키>:auto_check' 등)를 적는다(docs/auto-pipeline).")


def _me(principal: Principal = Depends(get_current_principal)) -> Principal:
    ensure(principal, FEAT)
    return principal


def _who(p: Principal) -> str:
    return p.email or p.subject


def _store(request: Request):
    st = getattr(request.app.state, "autopipe_store", None)
    if st is None:
        raise AuthError("자동 파이프라인 원장이 열리지 않았습니다(절차 저장소 기동 실패)", status_code=503)
    return st


def _engine(request: Request):
    eng = getattr(request.app.state, "autopipe_engine", None)
    if eng is None:
        raise AuthError("자동 파이프라인 엔진이 없습니다(절차 저장소 기동 실패)", status_code=503)
    return eng


def _on(request: Request, settings: Settings) -> None:
    if not settings.auto_pipeline_enabled:
        raise AuthError("자동 파이프라인이 이 박스에서 꺼져 있습니다(AUTO_PIPELINE_ENABLED) — 읽기 · 규칙 편집 · 검증만 됩니다", status_code=409)


class SpecIn(BaseModel):
    spec: dict


class EnabledIn(BaseModel):
    enabled: bool


class RecheckIn(BaseModel):
    step: str | None = Field(default=None, max_length=40)


class RunNowIn(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    revision: str = Field(min_length=1, max_length=40)


class QuiesceIn(BaseModel):
    ttl_s: int = Field(default=900, ge=1, le=3600)
    wait_s: float = Field(default=300, ge=0, le=1800)
    by: str = Field(default="update-all", max_length=80)


def _bad_spec(errors: list[str]) -> JSONResponse:
    return JSONResponse({"ok": False, "errors": errors}, status_code=422)


# ── 상태 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
@router.get("/health")
def health(request: Request, principal: Principal = Depends(_me), settings: Settings = Depends(get_settings)) -> dict:
    st = _store(request)
    eng = getattr(request.app.state, "autopipe_engine", None)
    e = eng.health() if eng is not None else {"running": False, "last_tick": None, "last_error": None}
    ra = RA.health()
    return {"enabled": bool(settings.auto_pipeline_enabled), "how_to_enable": None if settings.auto_pipeline_enabled else HOW_TO_ENABLE,
            "engine": {"running": e["running"], "last_tick": e["last_tick"], "last_error": e["last_error"],
                       "paused_until": e.get("paused_until"), "paused_by": e.get("paused_by")},
            "sources": [{"app": c["source"], "cursor_at": c["last_ok_at"], "last_error": c["last_error"]} for c in st.cursors()],
            "ra": {"configured": ra["configured"], "board": ra["board"], "formats": ra["formats"], "error": ra["error"]},
            "counts": st.counts()}


# ── 규칙 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
@router.post("/validate")
def validate(body: SpecIn, principal: Principal = Depends(_me)) -> dict:
    errors, warnings, _ = S.validate(body.spec)
    return {"ok": not errors, "errors": errors, "warnings": warnings}


@router.get("/rules")
def rules(request: Request, principal: Principal = Depends(_me)) -> dict:
    return {"rules": _store(request).list_rules()}


@router.post("/rules")
def create_rule(request: Request, body: SpecIn, principal: Principal = Depends(_me), _csrf: None = Depends(require_csrf)):
    errors, warnings, spec = S.validate(body.spec)
    if errors:
        return _bad_spec(errors)
    eng = _engine(request)
    got = _store(request).create_rule(spec=spec, by=_who(principal), now=eng.now())
    return {**got, "warnings": warnings}


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str, request: Request, principal: Principal = Depends(_me)) -> dict:
    got = _store(request).get_rule(rule_id)
    if got is None:
        raise AuthError("규칙을 찾을 수 없습니다", status_code=404)
    return got


@router.post("/rules/{rule_id}/versions")
def add_version(rule_id: str, request: Request, body: SpecIn, principal: Principal = Depends(_me), _csrf: None = Depends(require_csrf)):
    errors, warnings, spec = S.validate(body.spec)
    if errors:
        return _bad_spec(errors)
    got = _store(request).add_version(rule_id=rule_id, spec=spec, by=_who(principal), now=_engine(request).now())
    if got is None:
        raise AuthError("규칙을 찾을 수 없습니다", status_code=404)
    return {**got, "warnings": warnings}


@router.post("/rules/{rule_id}/enabled")
def set_enabled(rule_id: str, request: Request, body: EnabledIn, principal: Principal = Depends(_me),
                _csrf: None = Depends(require_csrf)) -> dict:
    got = _store(request).set_enabled(rule_id=rule_id, enabled=body.enabled, by=_who(principal), now=_engine(request).now())
    if got is None:
        raise AuthError("규칙을 찾을 수 없습니다", status_code=404)
    return got


# ── 감지 · 현황판 · 실행 ─────────────────────────────────────────────────────────────────────────────────────────────
@router.get("/subjects")
def subjects(request: Request, project: str = Query("", max_length=200), state: str = Query("", max_length=20),
             limit: int = Query(200, ge=1, le=2000), principal: Principal = Depends(_me)) -> dict:
    rows = _store(request).subjects(project=project or None, state=state or None, limit=limit)
    for r in rows:
        r.pop("skey", None)
    return {"subjects": rows}


def _step_cell(s: dict) -> dict:
    return {"state": s["state"], "verdict": s.get("verdict")}


@router.get("/board")
def board(request: Request, rule: str = Query("", max_length=64), limit: int = Query(200, ge=1, le=2000),
          principal: Principal = Depends(_me)) -> dict:
    """행은 (과제, 차수)마다 가장 최근 실행 하나, 열은 규칙 단계(규칙을 주면 그 최신 판의 단계 차례)."""
    st = _store(request)
    columns: list[str] = []
    if rule:
        r = st.get_rule(rule)
        if r is None:
            raise AuthError("규칙을 찾을 수 없습니다", status_code=404)
        columns = [s["id"] for s in (r.get("spec") or {}).get("steps") or []]
    seen: set = set()
    rows = []
    for run in st.runs(rule_id=rule or None, limit=limit * 4):
        key = (run["rule_id"], run["project"], run["revision"])
        if key in seen:
            continue
        seen.add(key)
        steps = st.steps(run["id"])
        for s in steps:
            if s["step_id"] not in columns:
                columns.append(s["step_id"])
        rows.append({"project": run["project"], "revision": run["revision"], "rule_id": run["rule_id"], "run_id": run["id"],
                     "run_state": run["state"], "stage": run["stage"], "superseded_by": run.get("superseded_by"),
                     "steps": {s["step_id"]: _step_cell(s) for s in steps}})
        if len(rows) >= limit:
            break
    return {"rule": rule or None, "columns": columns, "rows": rows}


def _public_step(s: dict) -> dict:
    out = {k: v for k, v in s.items() if k != "report_md"}
    out["has_report"] = bool(s.get("report_md"))
    return out


@router.get("/runs")
def runs(request: Request, rule: str = Query("", max_length=64), project: str = Query("", max_length=200),
         state: str = Query("", max_length=30), limit: int = Query(100, ge=1, le=1000), principal: Principal = Depends(_me)) -> dict:
    return {"runs": _store(request).runs(rule_id=rule or None, project=project or None, state=state or None, limit=limit)}


@router.get("/runs/{run_id}")
def run_detail(run_id: str, request: Request, principal: Principal = Depends(_me)) -> dict:
    st = _store(request)
    run = st.get_run(run_id)
    if run is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    # 그 실행이 돈 규칙 판의 스펙 — 화면의 승인 확인이 「어느 앱의 어느 해석을 내는지」 말하게(단계 행에는 앱 · 프로파일이 없다)
    return {"run": run, "spec": st.version_spec(run["rule_id"], run["version_no"]),
            "steps": [_public_step(s) for s in st.steps(run_id)], "events": st.events(run_id)}


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
def run_report(run_id: str, request: Request, step: str = Query(..., max_length=40), principal: Principal = Depends(_me)):
    st = _store(request)
    if st.get_run(run_id) is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    hit = next((s for s in st.steps(run_id) if s["step_id"] == step and s["kind"] == "report"), None)
    if hit is None or not hit.get("report_md"):
        raise AuthError("그 보고서 단계가 없거나 아직 쓰지 않았습니다", status_code=404)
    return PlainTextResponse(hit["report_md"], media_type="text/markdown; charset=utf-8")


@router.post("/runs/{run_id}/approve")
def approve(run_id: str, request: Request, principal: Principal = Depends(_me), _csrf: None = Depends(require_csrf),
            settings: Settings = Depends(get_settings)) -> dict:
    _on(request, settings)
    eng = _engine(request)
    if eng.store.get_run(run_id) is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    got = eng.approve(run_id, _who(principal))
    if got is None:
        raise AuthError("승인을 기다리는 실행이 아닙니다", status_code=409)
    return {"run": got}


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str, request: Request, principal: Principal = Depends(_me), _csrf: None = Depends(require_csrf),
                 settings: Settings = Depends(get_settings)) -> dict:
    _on(request, settings)
    eng = _engine(request)
    if eng.store.get_run(run_id) is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    got = await eng.cancel(run_id, _who(principal))
    if got is None:
        raise AuthError("도는 중이거나 승인을 기다리는 실행만 취소합니다", status_code=409)
    return got


@router.post("/runs/{run_id}/recheck")
def recheck(run_id: str, request: Request, body: RecheckIn | None = None, principal: Principal = Depends(_me),
            _csrf: None = Depends(require_csrf), settings: Settings = Depends(get_settings)) -> dict:
    """막힌 해석 단계를 같은 입력으로 다시 확인한다(AP-24) — step 을 주면 그 단계만, 비우면 막힌 단계 전부."""
    _on(request, settings)
    got, why = _engine(request).recheck(run_id, _who(principal), (body.step if body else None) or None)
    if why == "not_found":
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    if got is None:
        raise AuthError(why or "다시 확인할 수 없습니다", status_code=409)
    return got


@router.post("/rules/{rule_id}/run")
async def run_now(rule_id: str, request: Request, body: RunNowIn, principal: Principal = Depends(_me),
                  _csrf: None = Depends(require_csrf), settings: Settings = Depends(get_settings)) -> dict:
    """감지한 과제 · 차수 하나에 이 규칙을 지금 돌린다(AP-25) — 단계(stage)는 규칙 최신 판 그대로다."""
    _on(request, settings)
    got, why = await _engine(request).run_now(rule_id, body.project, body.revision, _who(principal))
    if why == "not_found":
        raise AuthError("규칙을 찾을 수 없습니다", status_code=404)
    if got is None:
        raise AuthError(why or "돌릴 수 없습니다", status_code=409)
    return got


@router.post("/tick")
async def tick(request: Request, principal: Principal = Depends(_me), _csrf: None = Depends(require_csrf),
               settings: Settings = Depends(get_settings)) -> dict:
    _on(request, settings)
    return await _engine(request).tick()


# ── update-all 의 기다림(공유 시크릿 문 — 게이트웨이 내부 조회와 같은 GATEWAY_SHARED_TOKEN) ──────────────────────────────
@internal_router.post("/internal/autopipe/quiesce")
async def quiesce(request: Request, body: QuiesceIn | None = None, settings: Settings = Depends(get_settings)) -> dict:
    """새 박자를 ttl_s 동안 멈추고 도는 박자가 접히기를 wait_s 까지 기다린다(AP-26). 멈춤은 메모리라 포털이 다시 뜨면 풀린다 — 내린 뒤
    띄우지 못해도 ttl_s 뒤에 풀린다. 꺼진 박스도 같은 꼴로 답한다(enabled=false · idle=true)."""
    _internal(request, settings)
    b = body or QuiesceIn()
    return await _engine(request).quiesce(ttl_s=b.ttl_s, wait_s=b.wait_s, by=b.by)
