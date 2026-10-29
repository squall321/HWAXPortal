# 분석 루틴 API(/routines-api) — 정의(짜기 · 판 · 보관 · 준비도 · 검증 · YAML)와 고를 수 있는 플랫폼(docs/analysis-routines/contracts.md §3, R1)
"""권한은 `feat:routines`. 짜기 · 판 더하기 · 보관 · 가져오기는 브라우저 세션 + CSRF 만 받는다(루틴은 사람이 화면에서 짠다). 읽기 · 준비도 · 검증은
세션 또는 PAT 를 받는다 — 게이트웨이의 `routine_list` · `routine_get` 이 호출자 PAT 를 그대로 넘긴다(대화 저장과 같은 길).

준비도는 막지 않는다 — 이 사람의 도구 목록(사람 PAT 의 tools/list, 권한 필터의 정본)과 이 박스의 /tools-map 으로 단계마다
allowed · denied(권한 없음) · not_connected(RA · 외부 연결 토큰 미등록) · unavailable(이 박스 게이트웨이에 없음)을 말한다.
"""
import logging
import time

import yaml
from typing import Literal

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from pydantic import BaseModel, Field, ValidationError

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf
from app.procedures.models import SpecError
from app.procedures.routes import RA_BACKEND, _gw, _runner, _tools_map
from app.procedures.routine_store import RESULT_MAX
from app.procedures.routines import (CLOSED, CONTRACT, Envelope, RoutineSpec, first_states, is_write_tool, parse_spec,
                                     plan_steps, render, render_report)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/routines-api", tags=["routines"])
FEAT = "feat:routines"
DELIB_BACKEND = "hwax-deliberation"
IMPORT_MAX = 64 * 1024


def _store(request: Request):
    st = getattr(request.app.state, "routine_store", None)
    if st is None:
        raise AuthError("루틴 저장소가 열리지 않았습니다", status_code=503)
    return st


def _me(principal: Principal = Depends(get_current_principal)) -> Principal:
    """화면 전용(세션) — 쓰기 라우트는 여기에 require_csrf 를 더한다."""
    ensure(principal, FEAT)
    return principal


def _me_any(principal: Principal = Depends(principal_pat_or_session)) -> Principal:
    """세션 또는 PAT(게이트웨이가 넘긴 호출자 PAT) — 세션의 POST 는 principal_pat_or_session 이 CSRF 를 본다."""
    ensure(principal, FEAT)
    return principal


def _parse(raw) -> dict:
    try:
        return parse_spec(raw).model_dump(mode="json")
    except SpecError as exc:
        raise AuthError(f"루틴 스펙이 틀렸습니다 — {exc}"[:600], status_code=422) from None


class SpecIn(BaseModel):
    spec: dict


class ImportIn(BaseModel):
    yaml: str = Field(min_length=1, max_length=IMPORT_MAX)


@router.get("/health")
def health(request: Request, response: Response) -> dict:
    """무인증 — 게이트웨이가 '포털이 이 판보다 낡았다' 를 가르는 데 쓴다. 저장소가 안 열렸으면 503."""
    if getattr(request.app.state, "routine_store", None) is None:
        response.status_code = 503
        return {"ok": False, "contract": CONTRACT, "error": "루틴 저장소가 열리지 않았습니다"}
    return {"ok": True, "contract": CONTRACT}


async def _catalog(request: Request, principal: Principal) -> tuple[dict, dict]:
    """(이 사람이 부를 수 있는 도구 {백엔드: {원래 이름: 노출 이름 · 설명}}, 이 박스의 /tools-map)."""
    cat = await _gw(_runner(request).catalog(principal, run_id="routines"), "도구 목록")
    tmap = await _tools_map(request)
    owner = tmap.get("map") or {}
    mine: dict[str, dict] = {}
    for name, meta in cat.items():
        bk = owner.get(name)
        if not bk or bk == "_gateway":
            continue
        p = bk.replace("-", "") + "_"
        orig = name[len(p):] if name.startswith(p) else name     # 게이트웨이 별칭 규칙 — <백엔드에서 하이픈 뺀 것>_<원래 이름>
        mine.setdefault(bk, {})[orig] = {"exposed": name,
                                         "description": (meta.get("description") or "").strip().split("\n")[0][:200]}
    return mine, tmap


def _labels(tmap: dict) -> dict:
    return {a.get("app"): a.get("label") or a.get("app") for a in tmap.get("apps") or []}


@router.get("/platforms")
async def platforms(request: Request, principal: Principal = Depends(_me_any)) -> dict:
    """루틴 단계에 고를 수 있는 플랫폼 — 내 도구 목록을 백엔드로 묶는다. 이 박스에 있지만 내 권한 밖인 것은 따로 이름만."""
    mine, tmap = await _catalog(request, principal)
    labels = _labels(tmap)
    rows = [{"backend": bk, "label": labels.get(bk, bk),
             "tools": [{"name": n, "exposed": t["exposed"], "write": is_write_tool(n), "description": t["description"]}
                       for n, t in sorted(tools.items())]}
            for bk, tools in mine.items() if bk != DELIB_BACKEND]
    on_box = [a.get("app") for a in tmap.get("apps") or [] if a.get("app") not in (None, "_gateway")]
    return {"platforms": sorted(rows, key=lambda r: (r["label"].lower(), r["backend"])),
            "deliberation": "deliberate_start" in (mine.get(DELIB_BACKEND) or {}),
            "not_permitted": [{"backend": b, "label": labels.get(b, b)} for b in sorted(on_box) if b not in mine]}


def _connections_missing(request: Request, principal: Principal, settings: Settings, backends: set[str]) -> dict[str, str]:
    """토큰 등록이 필요한 백엔드(RA · 박스 권한표의 외부 연결) 가운데 이 사람이 등록하지 않은 것 → 까닭. 사전검사는 막지 않는다."""
    users = getattr(request.app.state, "user_store", None)
    if users is None:
        return {}
    need: dict[str, str] = {}
    if RA_BACKEND in backends and not settings.ra_sso_secret:
        need[RA_BACKEND] = "Report Archive"
    access = getattr(request.app.state, "access", None)
    if access is not None:
        try:
            for key, c in access.get().connections().items():
                if key in backends:
                    need[key] = c.label or key
        except Exception:  # noqa: BLE001 — 선언을 못 읽으면 모르는 것으로 둔다
            logger.info("루틴 준비도 — 외부 연결 선언을 읽지 못했다", exc_info=True)
    out = {}
    for key, label in need.items():
        try:
            conn = users.get_connection(email=principal.email, service=key)
        except Exception:  # noqa: BLE001
            continue
        if not (conn and conn.get("token")):
            out[key] = f"{label} 토큰이 등록되어 있지 않습니다 — 개인 토큰 › 외부 연결(/tokens?tab=connect)에서 등록하면 이 단계가 돈다"
    return out


async def readiness_of(request: Request, principal: Principal, settings: Settings, spec: RoutineSpec,
                       catalog: tuple[dict, dict] | None = None) -> list[dict]:
    mine, tmap = catalog or await _catalog(request, principal)
    labels = _labels(tmap)
    on_box = {a.get("app") for a in tmap.get("apps") or []}
    missing_conn = _connections_missing(request, principal, settings,
                                        {b for s in spec.steps for b in s.backends})
    out = []
    for s in spec.steps:
        if s.kind == "deliberation":
            ok = "deliberate_start" in (mine.get(DELIB_BACKEND) or {})
            state = "allowed" if ok else ("denied" if DELIB_BACKEND in on_box else "unavailable")
            out.append({"step": s.id, "state": state, "backends": [], "missing_tools": [],
                        "reason": "" if ok else "심의(전문가 심의 권한)를 부를 수 없다" if state == "denied" else "이 박스에 심의 엔진이 없다"})
            continue
        per = []
        for b in s.backends:
            st = ("not_connected" if b in missing_conn else "allowed") if b in mine else ("denied" if b in on_box else "unavailable")
            per.append({"backend": b, "label": labels.get(b, s.label or b), "state": st, "reason": missing_conn.get(b, "")})
        have = {t for b in s.backends for t in (mine.get(b) or {})}
        states = {p["state"] for p in per}
        state = "allowed" if "allowed" in states else next(
            (x for x in ("not_connected", "denied", "unavailable") if x in states), "unavailable")
        reasons = {"denied": "이 플랫폼 권한이 없다", "unavailable": "이 박스 게이트웨이에 없다",
                   "not_connected": next((p["reason"] for p in per if p["reason"]), "")}
        out.append({"step": s.id, "state": state, "backends": per,
                    "missing_tools": [t for t in s.tools if t not in have] if state == "allowed" else [],
                    "reason": "" if state == "allowed" else reasons[state]})
    return out


@router.get("/routines")
def list_routines(request: Request, q: str = Query("", max_length=200),
                  principal: Principal = Depends(_me_any)) -> dict:
    rows = _store(request).list_routines(sub=principal.subject, q=q)
    return {"count": len(rows), "routines": rows}


@router.post("/routines", status_code=201, dependencies=[Depends(require_csrf)])
def create_routine(request: Request, body: SpecIn, principal: Principal = Depends(_me)) -> dict:
    return _store(request).create(owner_sub=principal.subject, spec=_parse(body.spec))


def _readable(request: Request, principal: Principal, routine_id: str, version: int | None) -> dict:
    got = _store(request).readable(sub=principal.subject, routine_id=routine_id, version_no=version)
    if got is None:
        raise AuthError("루틴을 찾을 수 없습니다", status_code=404)
    return got


@router.get("/routines/{routine_id}")
def get_routine(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                principal: Principal = Depends(_me_any)) -> dict:
    got = _readable(request, principal, routine_id, version)
    return {**got, "mine": got["routine"]["owner_sub"] == principal.subject,
            "versions": _store(request).versions(sub=principal.subject, routine_id=routine_id) or []}


@router.post("/routines/{routine_id}/versions", status_code=201, dependencies=[Depends(require_csrf)])
def add_version(request: Request, routine_id: str, body: SpecIn, principal: Principal = Depends(_me)) -> dict:
    try:
        return _store(request).add_version(routine_id=routine_id, author_sub=principal.subject, spec=_parse(body.spec))
    except KeyError:
        raise AuthError("루틴을 찾을 수 없습니다 — 판은 주인만 더한다(남의 루틴은 내보내기 · 가져오기로 내 것을 만든다)",
                        status_code=404) from None


@router.delete("/routines/{routine_id}", dependencies=[Depends(require_csrf)])
def archive_routine(request: Request, routine_id: str, principal: Principal = Depends(_me)) -> dict:
    if not _store(request).archive(routine_id=routine_id, owner_sub=principal.subject):
        raise AuthError("루틴을 찾을 수 없습니다 — 보관은 주인만 한다", status_code=404)
    return {"ok": True, "archived": True}


@router.get("/routines/{routine_id}/readiness")
async def readiness(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                    settings: Settings = Depends(get_settings), principal: Principal = Depends(_me_any)) -> dict:
    got = _readable(request, principal, routine_id, version)
    spec = RoutineSpec.model_validate(got["version"]["spec"])
    return {"routine_id": routine_id, "version_no": got["version"]["version_no"],
            "steps": await readiness_of(request, principal, settings, spec)}


@router.post("/validate")
def validate(body: SpecIn, principal: Principal = Depends(_me_any)) -> dict:
    """검증만 — 저장하지 않는다. 틀리면 422 와 까닭, 맞으면 기본값을 채운 스펙."""
    return {"ok": True, "spec": _parse(body.spec)}


@router.get("/routines/{routine_id}/export")
def export_routine(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                   principal: Principal = Depends(_me_any)) -> Response:
    got = _readable(request, principal, routine_id, version)
    text = yaml.safe_dump(got["version"]["spec"], allow_unicode=True, sort_keys=False)
    return Response(content=text, media_type="application/x-yaml; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="routine-{routine_id[:8]}.yaml"'})


@router.post("/import", status_code=201, dependencies=[Depends(require_csrf)])
def import_routine(request: Request, body: ImportIn = Body(...), principal: Principal = Depends(_me)) -> dict:
    """YAML 을 내 새 루틴으로 — 남의 루틴을 고치는 길이다(판은 주인만 더한다)."""
    try:
        raw = yaml.safe_load(body.yaml)
    except yaml.YAMLError as exc:
        raise AuthError(f"YAML 을 읽지 못했습니다 — {str(exc)[:200]}", status_code=422) from None
    return _store(request).create(owner_sub=principal.subject, spec=_parse(raw))


# ── 실행(R2) — 원장 · 단계 · 보고서(docs/analysis-routines/contracts.md §2 · §3) ─────────────────────────────────────────
# 읽기 · 쓰기 모두 세션 또는 PAT(게이트웨이 routine_* 가 호출자 PAT 를 넘긴다). 실행은 주인만 — 없는 것과 남의 것은 같은 404 다.
PAGE_CHARS = 60_000           # 큰 결과 한 쪽(게이트웨이 ROUTINE_PAGE_CHARS 와 같다)
EVID_CHARS = 15_000           # 심의 근거 한 건의 결과 글자(엔진이 창에 맞게 더 줄인다)
EVID_MAX = 120                # 심의 근거 건수 상한(엔진의 근거 칸 상한과 같다)


class RunIn(BaseModel):
    routine_id: str = Field(min_length=1, max_length=64)
    version: int | None = Field(None, ge=1)
    inputs: dict = Field(default_factory=dict)
    executor: Literal["mcp", "chat", "web"] = "mcp"
    conversation_id: str | None = Field(None, max_length=64)


class CallIn(BaseModel):
    step: str = Field(min_length=1, max_length=24)
    backend: str = Field(min_length=1, max_length=64)
    tool: str = Field(min_length=1, max_length=80)
    args: dict = Field(default_factory=dict)
    ok: bool
    ms: int | None = Field(None, ge=0)
    result: str = Field("", max_length=RESULT_MAX + 1)
    truncated: bool = False


class ReportIn(BaseModel):
    title: str | None = Field(None, max_length=200)
    sections: dict[str, str] = Field(default_factory=dict, max_length=24)


class RaIn(BaseModel):
    report_id: str | None = Field(None, max_length=64)
    error: str | None = Field(None, max_length=600)


class PickIn(BaseModel):
    key: str = Field(min_length=1, max_length=200)


def _coerce(spec: RoutineSpec, raw: dict) -> dict:
    """루틴 입력 — 선언한 형으로 맞춘다. 모르는 키 · 빠진 필수는 422(오타가 다른 루틴처럼 조용히 도는 것을 막는다)."""
    known = {v.key for v in spec.vars}
    extra = sorted(set(raw) - known)
    if extra:
        raise AuthError(f"이 루틴에 없는 입력: {', '.join(extra)}(있는 것: {', '.join(sorted(known)) or '없음'})", status_code=422)
    out = {}
    for v in spec.vars:
        val = raw.get(v.key)
        if val is None or val == "":
            if v.required:
                raise AuthError(f"입력 {v.label}({v.key}) 이 없다", status_code=422)
            continue
        try:
            out[v.key] = v.coerce(val)
        except SpecError as exc:
            raise AuthError(f"입력 {v.label}({v.key}) — {exc}", status_code=422) from None
    return out


def _run(request: Request, principal: Principal, run_id: str) -> dict:
    run = _store(request).get_run(run_id=run_id, owner_sub=principal.subject)
    if run is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    return run


def _keys(stages: list[dict]) -> dict:
    return {st["step_id"]: ((st.get("envelope") or {}).get("keys") or {}) for st in stages}


def run_view(run: dict, stages: list[dict]) -> dict:
    """실행 하나의 보기 — 계획(울타리 · 허용 도구)에 단계 상태 · 넘긴 키 · 요약을 얹고, 할 일의 참조를 지금까지 넘긴 키로 푼다."""
    plan, inputs, keys = run["plan"], run["inputs"], _keys(stages)
    by = {st["step_id"]: st for st in stages}
    limits = plan["limits"]
    limit = None
    if run["state"] == "running":
        if time.time() > run["deadline"]:
            limit = f"시간 {limits['minutes']}분"
        elif run["calls"] >= limits["calls"]:
            limit = f"호출 {limits['calls']}번"
    steps = []
    for ps in plan["steps"]:
        st = by.get(ps["id"]) or {}
        env = st.get("envelope") or {}
        row = {**ps, "goal": render(ps["goal"], inputs, keys), "state": st.get("state"), "calls": st.get("calls", 0),
               "reason": st.get("reason") or "", "summary": env.get("summary") or "", "keys": env.get("keys") or {},
               "flags": st.get("flags") or []}
        if st.get("state") == "ambiguous":
            row["candidates"] = env.get("candidates") or []
        steps.append(row)
    rep = plan["report"]
    return {"contract": CONTRACT,
            "run": {k: run.get(k) for k in ("id", "routine_id", "version_no", "title", "executor", "state", "reason", "calls",
                                           "started_at", "deadline", "ended_at", "ra_report_id", "ra_error")}
                   | {"limits": limits, "limit_reached": limit, "report_ready": bool(run.get("report_md"))},
            "inputs": inputs, "purpose": render(plan.get("purpose") or "", inputs, keys), "steps": steps,
            "next_step": next((s["id"] for s in steps if s["state"] in ("pending", "running", "ambiguous")), None),
            "report": {"title": render(rep.get("title") or plan.get("routine_title") or "", inputs, keys),
                       "sections": rep.get("sections") or [], "upload": (rep.get("ra") or {}).get("upload") or "off"}}


@router.get("/routines/{routine_id}/plan")
async def plan_preview(request: Request, routine_id: str, version: int | None = Query(None, ge=1),
                       settings: Settings = Depends(get_settings), principal: Principal = Depends(_me_any)) -> dict:
    """실행 없이 계획만 — 단계마다 울타리 · 허용 도구 · 내 준비도(routine_get). 할 일의 참조는 풀지 않는다(입력 전이다)."""
    got = _readable(request, principal, routine_id, version)
    spec = RoutineSpec.model_validate(got["version"]["spec"])
    cat = await _catalog(request, principal)
    steps = plan_steps(spec, cat[0], await readiness_of(request, principal, settings, spec, catalog=cat))
    return {"contract": CONTRACT, "routine_id": routine_id, "version_no": got["version"]["version_no"], "title": spec.title,
            "purpose": spec.purpose, "vars": [v.model_dump(exclude_none=True) for v in spec.vars], "steps": steps,
            "report": spec.report.model_dump(), "limits": spec.limits.model_dump()}


@router.post("/runs", status_code=201)
async def start_run(request: Request, body: RunIn, settings: Settings = Depends(get_settings),
                    principal: Principal = Depends(_me_any)) -> dict:
    """판 · 입력을 박고 계획을 찍는다(이 사람의 도구 목록 · 준비도로). 막힌 단계는 그 상태로 닫혀 시작하고, '멈춤' 으로 짠 단계가 막혔으면
    실행이 failed 로 시작한다(까닭과 함께 — 사용자 결정 Q4 · 기준 키)."""
    got = _readable(request, principal, body.routine_id, body.version)
    spec = RoutineSpec.model_validate(got["version"]["spec"])
    inputs = _coerce(spec, body.inputs)
    cat = await _catalog(request, principal)
    steps = plan_steps(spec, cat[0], await readiness_of(request, principal, settings, spec, catalog=cat))
    stages, stop = first_states(steps)
    store = _store(request)
    plan = {"steps": steps, "report": spec.report.model_dump(), "limits": spec.limits.model_dump(),
            "purpose": spec.purpose, "routine_title": spec.title}
    run_id = store.create_run(owner_sub=principal.subject, routine=got["routine"], version=got["version"], inputs=inputs,
                              plan=plan, executor=body.executor, conversation_id=body.conversation_id,
                              deadline=int(time.time()) + spec.limits.minutes * 60,
                              state="failed" if stop else "running", reason=stop, stages=stages)
    return run_view(store.get_run(run_id=run_id, owner_sub=principal.subject), store.stages(run_id))


@router.get("/runs")
def list_runs(request: Request, routine_id: str | None = Query(None, max_length=64),
              principal: Principal = Depends(_me_any)) -> dict:
    rows = _store(request).list_runs(owner_sub=principal.subject, routine_id=routine_id)
    return {"count": len(rows), "runs": rows}


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str, principal: Principal = Depends(_me_any)) -> dict:
    run = _run(request, principal, run_id)
    return run_view(run, _store(request).stages(run_id))


def _stage(stages: list[dict], step: str) -> dict:
    st = next((s for s in stages if s["step_id"] == step), None)
    if st is None:
        raise AuthError(f"이 실행에 단계 {step!r} 가 없다", status_code=404)
    return st


@router.post("/runs/{run_id}/calls", status_code=201)
def add_call(request: Request, run_id: str, body: CallIn, principal: Principal = Depends(_me_any)) -> dict:
    """호출 한 줄 — 게이트웨이 routine_call 이 부른 뒤 남긴다. 울타리 · 예산 · 상한을 여기서도 본다(게이트웨이를 거치지 않은 쓰기도 막는다)."""
    store = _store(request)
    run = _run(request, principal, run_id)
    stages = store.stages(run_id)
    st = _stage(stages, body.step)
    ps = next(p for p in run["plan"]["steps"] if p["id"] == body.step)
    view = run_view(run, stages)["run"]
    if run["state"] != "running":
        raise AuthError(f"실행이 {run['state']} 상태다", status_code=409)
    if st["state"] not in ("pending", "running"):
        raise AuthError(f"단계 {body.step} 는 이미 닫혔다({st['state']})", status_code=409)
    if body.backend not in ps["backends"] or body.tool not in (ps["allowed"].get(body.backend) or []):
        raise AuthError(f"울타리 밖 — 단계 {body.step} 는 {', '.join(ps['backends'])} 의 허용 도구만 부른다", status_code=409)
    if st["calls"] >= ps["budget"]["calls"]:
        raise AuthError(f"단계 {body.step} 의 호출 예산({ps['budget']['calls']}번)을 다 썼다", status_code=409)
    if view["limit_reached"]:
        raise AuthError(f"실행 상한에 닿았다({view['limit_reached']})", status_code=409)
    call_id = store.add_call(run_id=run_id, step_id=body.step, backend=body.backend, tool=body.tool, args=body.args,
                             ok=body.ok, ms=body.ms, result=body.result, truncated=body.truncated)
    return {"call_id": call_id}


@router.get("/runs/{run_id}/calls/{call_id}")
def get_call(request: Request, run_id: str, call_id: str, page: int = Query(1, ge=1),
             principal: Principal = Depends(_me_any)) -> dict:
    _run(request, principal, run_id)
    c = _store(request).get_call(run_id, call_id)
    if c is None:
        raise AuthError(f"원장에 호출 {call_id!r} 가 없다", status_code=404)
    text = c["result"]
    pages = max(1, -(-len(text) // PAGE_CHARS))
    if page > pages:
        raise AuthError(f"쪽은 {pages}쪽까지다", status_code=404)
    return {"call_id": call_id, "step": c["step_id"], "tool": f"{c['backend']}:{c['tool']}", "ok": c["ok"],
            "chars": len(text), "truncated": c["truncated"], "page": page, "pages": pages,
            "text": text[(page - 1) * PAGE_CHARS: page * PAGE_CHARS]}


@router.get("/runs/{run_id}/evidence")
def evidence(request: Request, run_id: str, step: str = Query(..., max_length=24),
             principal: Principal = Depends(_me_any)) -> dict:
    """심의 단계의 근거 — 그 단계가 쓰는(uses) 앞 단계들의 성공한 호출 원문(도구 · 인자 · 결과). 정리한 결론은 넘기지 않는다(심의 헌법 P1)."""
    run = _run(request, principal, run_id)
    ps = next((p for p in run["plan"]["steps"] if p["id"] == step), None)
    if ps is None:
        raise AuthError(f"이 실행에 단계 {step!r} 가 없다", status_code=404)
    calls = [c for c in _store(request).calls(run_id, list(ps["uses"]), with_result=True) if c["ok"]]
    items = [{"source": f"{c['backend']}:{c['tool']}", "tool": c["tool"], "args": c["args"],
              "result": c["result"][:EVID_CHARS], "key": c["call_id"]} for c in calls[:EVID_MAX]]
    return {"step": step, "evidence": items, "omitted": max(0, len(calls) - EVID_MAX)}


def _next_or_report(view: dict) -> dict:
    nxt = next((s for s in view["steps"] if s["state"] in ("pending", "running", "ambiguous")), None)
    return {"next_step": nxt} if nxt else {"next_step": None, "report": view["report"]}


@router.post("/runs/{run_id}/steps/{step}/done")
def step_done(request: Request, run_id: str, step: str, body: dict = Body(...),
              principal: Principal = Depends(_me_any)) -> dict:
    """단계를 닫는다 — 실행자가 본 것을 원장과 맞대 고친다. 호출 없이 ok · empty 면 skipped, 결과가 다 오류면 failed, keys 의 값은 그 단계 결과에
    글자 그대로 있어야 다음 단계로 넘어간다(지어낸 키 · 잘못 이은 제품을 막는다, AR-D2), 원장에 없는 인용은 뗀다. ambiguous 는 후보와 함께 실행을
    waiting 으로 — 사람이 고르면(같은 단계를 ok + 고른 키로 다시 닫거나 /pick) 이어진다."""
    try:
        env = Envelope.model_validate(body)
    except ValidationError as exc:
        msgs = [f"{'.'.join(str(x) for x in e.get('loc') or ())}: {e.get('msg')}" for e in exc.errors()[:6]]
        raise AuthError("단계 봉투가 틀렸다 — " + " / ".join(msgs), status_code=422) from None
    store = _store(request)
    run = _run(request, principal, run_id)
    stages = store.stages(run_id)
    st = _stage(stages, step)
    ps = next(p for p in run["plan"]["steps"] if p["id"] == step)
    if run["state"] not in ("running", "waiting"):
        raise AuthError(f"실행이 {run['state']} 상태다", status_code=409)
    if st["state"] not in ("pending", "running", "ambiguous"):
        raise AuthError(f"단계 {step} 는 이미 닫혔다({st['state']})", status_code=409)
    calls = store.calls(run_id, [step], with_result=True)
    texts = [c["result"] for c in calls]
    flags: list[str] = []
    status = env.status
    if status in ("ok", "empty") and not calls:
        status = "skipped"
        flags.append("호출 없이 닫으려 했다 — 건너뜀으로 고쳤다")
    if status == "ok" and calls and not any(c["ok"] for c in calls):
        status = "failed"
        flags.append("결과가 다 오류다 — 실패로 고쳤다")
    want = set(ps["expect"]["keys"])
    picked = st["state"] == "ambiguous" and {c["key"] for c in ((st.get("envelope") or {}).get("candidates") or [])}
    keys, unsourced, unexpected = {}, [], []
    for k, v in env.keys.items():
        if want and k not in want:
            unexpected.append(k)
        elif any(v in t for t in texts) or (picked and v in picked):
            keys[k] = v
        else:
            unsourced.append(k)
    if unexpected:
        flags.append(f"계획에 없는 키는 뺐다: {', '.join(unexpected)}")
    if unsourced:
        flags.append(f"결과에 글자 그대로 없는 키는 넘기지 않는다: {', '.join(unsourced)}")
    known = {c["call_id"] for c in store.calls(run_id)}
    findings, bad = [], []
    for f in env.findings:
        bad += [r for r in f.refs if r not in known]
        findings.append({"text": f.text, "refs": [r for r in f.refs if r in known]})
    if bad:
        flags.append(f"원장에 없는 인용은 뗐다: {', '.join(sorted(set(bad))[:10])}")
    if status == "ambiguous" and not env.candidates:
        status = "failed"
        flags.append("후보 없이 '여럿' 이라 했다 — 실패로 고쳤다")
    envelope = {"status": env.status, "summary": env.summary, "keys": keys, "findings": findings,
                "candidates": [c.model_dump() for c in env.candidates]}
    store.set_stage(run_id, step, state=status, reason=env.reason or None, envelope=envelope, flags=flags)
    blocked = ps["blocked"]
    stop = None
    if status == "empty" and blocked["empty"] == "stop":
        stop = f"단계 {step}({ps['title']}) 결과 없음 — '멈춤' 으로 짠 단계라 실행을 멈췄다"
    elif status in ("denied", "not_connected") and blocked["denied"] == "stop":
        stop = f"단계 {step}({ps['title']}) {status} — '멈춤' 으로 짠 단계라 실행을 멈췄다"
    elif status == "unavailable" and blocked["unavailable"] == "stop":
        stop = f"단계 {step}({ps['title']}) 이 박스에 없음 — '멈춤' 으로 짠 단계라 실행을 멈췄다"
    if stop:
        store.set_run(run_id, state="failed", reason=stop)
    elif status == "ambiguous":
        store.set_run(run_id, state="waiting", reason=f"단계 {step} — 사람이 후보를 고른다")
    elif run["state"] == "waiting":
        store.set_run(run_id, state="running", reason=None)
    view = run_view(store.get_run(run_id=run_id, owner_sub=principal.subject), store.stages(run_id))
    return {"step": step, "state": status, "flags": flags, "run_state": view["run"]["state"], **_next_or_report(view)}


@router.post("/runs/{run_id}/steps/{step}/pick")
def pick(request: Request, run_id: str, step: str, body: PickIn, principal: Principal = Depends(_me_any)) -> dict:
    """고를 것이 있는 단계에서 사람이 후보 하나를 고른다 — 그 키를 단계의 첫 기대 키로 넘기고 단계를 ok 로 닫는다."""
    store = _store(request)
    run = _run(request, principal, run_id)
    st = _stage(store.stages(run_id), step)
    if st["state"] != "ambiguous":
        raise AuthError(f"단계 {step} 는 고를 것이 없다({st['state']})", status_code=409)
    env = st.get("envelope") or {}
    if body.key not in {c["key"] for c in env.get("candidates") or []}:
        raise AuthError("후보에 없는 키다", status_code=422)
    ps = next(p for p in run["plan"]["steps"] if p["id"] == step)
    name = (ps["expect"]["keys"] or ["key"])[0]
    store.set_stage(run_id, step, state="ok", reason=None, envelope={**env, "keys": {**(env.get("keys") or {}), name: body.key}},
                    flags=(st.get("flags") or []) + [f"사람이 고른 후보 — {name}={body.key}"])
    store.set_run(run_id, state="running", reason=None)
    view = run_view(store.get_run(run_id=run_id, owner_sub=principal.subject), store.stages(run_id))
    return {"step": step, "state": "ok", **_next_or_report(view)}


@router.post("/runs/{run_id}/report")
def report(request: Request, run_id: str, body: ReportIn, principal: Principal = Depends(_me_any)) -> dict:
    """모든 단계가 닫힌 뒤 — 보고서를 렌더해 원장에 두고 실행을 끝낸다. RA 블록(deliberation v1)과 올리기 방식을 돌려준다 — 올리는 것은
    게이트웨이가 호출자 이름으로 한다(서비스 계정 없음)."""
    store = _store(request)
    run = _run(request, principal, run_id)
    if run["state"] != "running":
        raise AuthError(f"실행이 {run['state']} 상태다 — 보고서는 도는 실행에서만 낸다", status_code=409)
    stages = store.stages(run_id)
    open_ = [s["step_id"] for s in stages if s["state"] not in CLOSED]
    if open_:
        raise AuthError(f"아직 닫히지 않은 단계: {', '.join(open_)} — routine_step_done 으로 닫는다", status_code=409)
    got = _readable(request, principal, run["routine_id"], run["version_no"])
    spec = RoutineSpec.model_validate(got["version"]["spec"])
    out = render_report(spec=spec, run=run, steps=run["plan"]["steps"], stages=stages, calls=store.calls(run_id),
                        sections=body.sections, title=body.title)
    store.set_run(run_id, state="done", report_md=out["report_md"])
    return {"report_md": out["report_md"], "coverage": out["coverage"], "warnings": out["warnings"],
            "ra": {"upload": spec.report.ra.upload, "title": out["title"], "blocks": out["blocks"], "tags": out["tags"]}}


@router.post("/runs/{run_id}/ra")
def ra_result(request: Request, run_id: str, body: RaIn, principal: Principal = Depends(_me_any)) -> dict:
    run = _run(request, principal, run_id)
    if run["state"] != "done":
        raise AuthError("보고서를 낸 뒤에만 RA 결과를 적는다", status_code=409)
    _store(request).set_run(run_id, ra_report_id=body.report_id, ra_error=None if body.report_id else (body.error or "까닭 없음"))
    return {"ok": True}


@router.post("/runs/{run_id}/cancel")
def cancel(request: Request, run_id: str, principal: Principal = Depends(_me_any)) -> dict:
    run = _run(request, principal, run_id)
    if run["state"] not in ("queued", "running", "waiting"):
        raise AuthError(f"실행이 이미 {run['state']} 상태다", status_code=409)
    _store(request).set_run(run_id, state="cancelled", reason="사람이 멈췄다")
    return {"ok": True, "state": "cancelled"}
