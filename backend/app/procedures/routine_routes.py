# 분석 루틴 API(/routines-api) — 정의(짜기 · 판 · 보관 · 준비도 · 검증 · YAML)와 고를 수 있는 플랫폼(docs/analysis-routines/contracts.md §3, R1)
"""권한은 `feat:routines`. 짜기 · 판 더하기 · 보관 · 가져오기는 브라우저 세션 + CSRF 만 받는다(루틴은 사람이 화면에서 짠다). 읽기 · 준비도 · 검증은
세션 또는 PAT 를 받는다 — 게이트웨이의 `routine_list` · `routine_get` 이 호출자 PAT 를 그대로 넘긴다(대화 저장과 같은 길).

준비도는 막지 않는다 — 이 사람의 도구 목록(사람 PAT 의 tools/list, 권한 필터의 정본)과 이 박스의 /tools-map 으로 단계마다
allowed · denied(권한 없음) · not_connected(RA · 외부 연결 토큰 미등록) · unavailable(이 박스 게이트웨이에 없음)을 말한다.
"""
import asyncio
import json
import logging
import time

import jwt
import yaml
from typing import Literal

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from pydantic import BaseModel, Field, ValidationError

from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf
from app.procedures import judge as J
from app.procedures.models import SpecError
from app.procedures.routes import RA_BACKEND, _gw, _runner, _tools_map
from app.procedures.routine_store import RESULT_MAX, CallRefused
from app.procedures.routines import (CLOSED, CONTRACT, Envelope, RoutineSpec, allowed_tools, first_states, is_write_tool,
                                     parse_spec, plan_steps, render, render_report, started_kst, write_reason)
from app.procedures.runner import GatewaySession

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


def _read_only_pat(token: str) -> bool:
    """읽기 전용 PAT 인가 — 게이트웨이 rest_proxy.is_read_only 와 같은 판정(scopes 에 read 가 있고 write 가 없을 때만). 칸이 없는 옛 PAT 와
    챗 · 절차 PAT 의 ["chat"] 은 아니다. 서명 · aud · 만료 · 폐기는 앞 의존성(principal_pat_or_session)이 같은 요청의 같은 헤더로 이미 봤다 —
    여기서는 scopes 칸만 읽는다."""
    raw = jwt.decode(token, options={"verify_signature": False}).get("scopes")
    if not isinstance(raw, list):
        return False
    s = {str(x).strip().lower() for x in raw}
    return "read" in s and "write" not in s


def _me_write(request: Request, principal: Principal = Depends(_me_any)) -> Principal:
    """실행 쓰기(원장 · 상태) — _me_any 에 더해 읽기 전용 PAT 는 403. 게이트웨이도 막지만(_readonly_denial) 포털로 바로 오는 길이 있다(R3 3.5 ⑧)."""
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() == "bearer " and _read_only_pat(auth[7:].strip()):
        raise AuthError("읽기 전용 토큰은 원장에 쓰지 못한다", status_code=403)
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


def _write_class(tmap: dict) -> str:
    """단계 도구 판정을 무엇으로 했나 — 'gateway_read'(/tools-map 의 routine_read — 읽기로 확인된 것만, 모르면 읽기가 아니다 · C-12),
    'gateway'(write 목록만 주는 판 — 정본 _tool_is_write, R3-D6) 또는 'name'(둘 다 없는 옛 게이트웨이 — is_write_tool 만)."""
    if isinstance(tmap.get("routine_read"), list):
        return "gateway_read"
    return "gateway" if isinstance(tmap.get("write"), list) else "name"


async def _catalog(request: Request, principal: Principal) -> tuple[dict, dict]:
    """(이 사람이 부를 수 있는 도구 {백엔드: {원래 이름: 노출 이름 · 설명 · 쓰기 · 읽기}}, 이 박스의 /tools-map). 쓰기는 게이트웨이가 준 write(노출
    이름 목록)에 있으면 참 · 없으면 거짓, 읽기는 routine_read(노출 이름 목록 — 단계에 묶어도 되는 읽기로 확인된 것)에 있으면 참 · 없으면 거짓이고,
    게이트웨이가 그 칸을 안 주면(옛 판) None(모름)이다."""
    cat = await _gw(_runner(request).catalog(principal, run_id="routines"), "도구 목록")
    tmap = await _tools_map(request)
    owner = tmap.get("map") or {}
    writes = set(tmap["write"]) if isinstance(tmap.get("write"), list) else None
    reads = set(tmap["routine_read"]) if _write_class(tmap) == "gateway_read" else None
    mine: dict[str, dict] = {}
    for name, meta in cat.items():
        bk = owner.get(name)
        if not bk or bk == "_gateway":
            continue
        p = bk.replace("-", "") + "_"
        orig = name[len(p):] if name.startswith(p) else name     # 게이트웨이 별칭 규칙 — <백엔드에서 하이픈 뺀 것>_<원래 이름>
        mine.setdefault(bk, {})[orig] = {"exposed": name,
                                         "description": (meta.get("description") or "").strip().split("\n")[0][:200],
                                         "write": None if writes is None else name in writes,
                                         "read": None if reads is None else name in reads}
    return mine, tmap


def _labels(tmap: dict) -> dict:
    return {a.get("app"): a.get("label") or a.get("app") for a in tmap.get("apps") or []}


@router.get("/platforms")
async def platforms(request: Request, principal: Principal = Depends(_me_any)) -> dict:
    """루틴 단계에 고를 수 있는 플랫폼 — 내 도구 목록을 백엔드로 묶는다. 이 박스에 있지만 내 권한 밖인 것은 따로 이름만.
    쓰기 표지(단계에 못 묶는다)는 계획과 같은 판정이다 — 게이트웨이가 읽기 목록(routine_read)을 주면 이름 꼴(is_write_tool)이거나 읽기로
    확인되지 않은 것, 안 주는 옛 판이면 이름 꼴 또는 게이트웨이 분류(/tools-map 의 write, 그것도 없으면 이름 꼴만)."""
    mine, tmap = await _catalog(request, principal)
    labels = _labels(tmap)
    rows = [{"backend": bk, "label": labels.get(bk, bk),
             "tools": [{"name": n, "exposed": t["exposed"],
                        "write": is_write_tool(n) or (t["read"] is not True if t["read"] is not None else t["write"] is True),
                        "description": t["description"]}
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
        missing = [t for t in s.tools if t not in have] if state == "allowed" else []
        reason = "" if state == "allowed" else reasons[state]
        if state == "allowed":
            # 단계 도구 판정(읽기 목록 · 쓰기 분류) — 계획(plan_steps)과 같은 판정 · 같은 까닭. 빼서 단계가 비면 '이 박스에 없음'(실행을 만들면
            # first_states 가 같은 까닭으로 닫는다 — 고르는 화면이 '돈다' 고 보이면 안 된다), 일부만 뺐으면 그대로 돌고 뺀 것을 까닭에 적는다
            allowed, dropped = allowed_tools(s, mine)
            reason = write_reason(s, allowed, dropped, mine)
            if reason and not any(allowed.values()):
                state = "unavailable"
        out.append({"step": s.id, "state": state, "backends": per, "missing_tools": missing, "reason": reason})
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
# 쓰기(_me_write)는 읽기 전용 PAT 를 받지 않는다(R3).
PAGE_CHARS = 60_000           # 큰 결과 한 쪽(게이트웨이 ROUTINE_PAGE_CHARS 와 같다)
EVID_CHARS = 15_000           # 심의 근거 한 건의 결과 글자(엔진이 창에 맞게 더 줄인다)
EVID_MAX = 120                # 심의 근거 건수 상한(엔진의 근거 칸 상한과 같다)


class RunIn(BaseModel):
    routine_id: str = Field(min_length=1, max_length=64)
    version: int | None = Field(None, ge=1)
    inputs: dict = Field(default_factory=dict)
    executor: Literal["mcp", "chat", "web"] = "mcp"
    conversation_id: str | None = Field(None, max_length=64)
    # 사용자가 덧붙인 말 — 실행에 남겨 이어서 · 다시 붙기 · 고른 뒤 잇기에도 같은 말을 싣는다(C-12 — 화면의 '루틴 이어서: <제목>' 이 그 말을 덮었다)
    note: str = Field("", max_length=2000)


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


def _limit(run: dict) -> tuple[str | None, str | None]:
    """도는 실행이 닿은 상한 — (종류 'calls' · 'time', 까닭 글), 안 닿았거나 도는 실행이 아니면 (None, None). 호출 상한을 먼저 본다 — 둘 다
    닿았는데 'time' 이라 하면 시간 상한 예외(심의 결과 읽기, R3-D5)가 호출 상한까지 넘긴다(게이트웨이는 limit_kind 만 본다)."""
    if run["state"] != "running":
        return None, None
    limits = run["plan"]["limits"]
    if run["calls"] >= limits["calls"]:
        return "calls", f"호출 {limits['calls']}번"
    if time.time() > run["deadline"]:
        return "time", f"시간 {limits['minutes']}분"
    return None, None


def run_view(run: dict, stages: list[dict]) -> dict:
    """실행 하나의 보기 — 계획(울타리 · 허용 도구)에 단계 상태 · 넘긴 키 · 요약 · 발견을 얹고, 할 일의 참조를 지금까지 넘긴 키와 실행 시작
    시각(`{{run.started}}`, KST)으로 푼다."""
    plan, inputs, keys = run["plan"], run["inputs"], _keys(stages)
    by = {st["step_id"]: st for st in stages}
    limits = plan["limits"]
    kind, limit = _limit(run)
    started = started_kst(run.get("started_at"))
    steps = []
    for ps in plan["steps"]:
        st = by.get(ps["id"]) or {}
        env = st.get("envelope") or {}
        row = {**ps, "goal": render(ps["goal"], inputs, keys, started), "state": st.get("state"), "calls": st.get("calls", 0),
               "reason": st.get("reason") or "", "summary": env.get("summary") or "", "keys": env.get("keys") or {},
               "findings": env.get("findings") or [], "flags": st.get("flags") or []}
        if st.get("state") == "ambiguous":
            row["candidates"] = env.get("candidates") or []
        steps.append(row)
    rep = plan["report"]
    return {"contract": CONTRACT,
            "run": {k: run.get(k) for k in ("id", "routine_id", "version_no", "title", "executor", "state", "reason", "calls",
                                           "started_at", "deadline", "ended_at", "ra_report_id", "ra_error")}
                   | {"limits": limits, "limit_reached": limit, "limit_kind": kind, "report_ready": bool(run.get("report_md"))},
            # 사용자가 덧붙인 말(시작 때 한 번) — 실행기는 이어서도 이것을 싣는다. 칸이 생기기 전 실행은 빈 글
            "note": run.get("note") or "",
            "inputs": inputs, "purpose": render(plan.get("purpose") or "", inputs, keys, started), "steps": steps,
            "next_step": next((s["id"] for s in steps if s["state"] in ("pending", "running", "ambiguous")), None),
            # 쓰기 분류를 무엇으로 했나(R3-D6) — R3 전에 찍은 계획은 None
            "write_class": plan.get("write_class"),
            "report": {"title": render(rep.get("title") or plan.get("routine_title") or "", inputs, keys, started),
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
            "report": spec.report.model_dump(), "limits": spec.limits.model_dump(), "write_class": _write_class(cat[1])}


@router.post("/runs", status_code=201)
async def start_run(request: Request, body: RunIn, settings: Settings = Depends(get_settings),
                    principal: Principal = Depends(_me_write)) -> dict:
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
            "purpose": spec.purpose, "routine_title": spec.title, "write_class": _write_class(cat[1])}
    run_id = store.create_run(owner_sub=principal.subject, routine=got["routine"], version=got["version"], inputs=inputs,
                              plan=plan, executor=body.executor, conversation_id=body.conversation_id,
                              deadline=int(time.time()) + spec.limits.minutes * 60,
                              state="failed" if stop else "running", reason=stop, stages=stages, note=body.note)
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


@router.post("/runs/{run_id}/resume")
def resume(request: Request, run_id: str, principal: Principal = Depends(_me_write)) -> dict:
    """이어서(R3-D8) — 실행자가 사라진 실행을 다시 잡는다. running · interrupted → running 이고, 시간 상한에 닿았으면 마감을 '지금 + 상한 분' 으로
    다시 잡는다. 고를 것이 남은(waiting) 실행은 고른 뒤에 잇고, 끝난 실행은 잇지 않는다. 닫힌 단계는 실행자가 건너뛴다(이 길은 상태만 고친다)."""
    store = _store(request)
    run = _run(request, principal, run_id)
    if run["state"] == "waiting":
        raise AuthError("고를 것이 있다 — 고른 뒤 이어서", status_code=409)
    if run["state"] not in ("running", "interrupted"):
        raise AuthError(f"실행이 {run['state']} 다", status_code=409)
    fields: dict = {}
    if run["state"] == "interrupted":
        fields.update(state="running", reason=None, ended_at=None)
    now = int(time.time())
    if now > run["deadline"]:
        fields["deadline"] = now + int(run["plan"]["limits"]["minutes"]) * 60
    store.set_run(run_id, **fields)
    return run_view(store.get_run(run_id=run_id, owner_sub=principal.subject), store.stages(run_id))


def _stage(stages: list[dict], step: str) -> dict:
    st = next((s for s in stages if s["step_id"] == step), None)
    if st is None:
        raise AuthError(f"이 실행에 단계 {step!r} 가 없다", status_code=404)
    return st


@router.post("/runs/{run_id}/calls", status_code=201)
def add_call(request: Request, run_id: str, body: CallIn, principal: Principal = Depends(_me_write)) -> dict:
    """호출 한 줄 — 게이트웨이 routine_call 이 부른 뒤 남긴다. 울타리 · 예산 · 상한을 여기서도 본다(게이트웨이를 거치지 않은 쓰기도 막는다).
    시간 상한에 닿아도 이미 세운 심의의 결과 읽기(hwax-deliberation:deliberate_result)는 받는다 — 게이트웨이 routine_call 과 같은 규칙(R3-D5),
    호출 상한은 그대로다. 심의 단계의 결과 읽기는 단계 호출 예산도 보지 않는다(C-12 — 예산을 시작에 다 쓰면 결정문을 못 읽고, save_report 를
    false 로 넣어 RA 에도 없다). 아래 검사는 빠른 거절이고, 상태 · 예산 · 호출 상한은 원장 쓰기 트랜잭션 안에서 다시 본다(동시 호출)."""
    store = _store(request)
    run = _run(request, principal, run_id)
    stages = store.stages(run_id)
    st = _stage(stages, body.step)
    ps = next(p for p in run["plan"]["steps"] if p["id"] == body.step)
    result_read = (body.backend, body.tool) == (DELIB_BACKEND, "deliberate_result")
    budget_free = result_read and ps.get("kind") == "deliberation"
    if run["state"] != "running":
        raise AuthError(f"실행이 {run['state']} 상태다", status_code=409)
    if st["state"] not in ("pending", "running"):
        raise AuthError(f"단계 {body.step} 는 이미 닫혔다({st['state']})", status_code=409)
    if body.backend not in ps["backends"] or body.tool not in (ps["allowed"].get(body.backend) or []):
        raise AuthError(f"울타리 밖 — 단계 {body.step} 는 {', '.join(ps['backends'])} 의 허용 도구만 부른다", status_code=409)
    if not budget_free and st["calls"] >= ps["budget"]["calls"]:
        raise AuthError(f"단계 {body.step} 의 호출 예산({ps['budget']['calls']}번)을 다 썼다", status_code=409)
    kind, limit = _limit(run)
    if limit and not (kind == "time" and result_read):
        raise AuthError(f"실행 상한에 닿았다({limit})", status_code=409)
    try:
        call_id = store.add_call(run_id=run_id, step_id=body.step, backend=body.backend, tool=body.tool, args=body.args,
                                 ok=body.ok, ms=body.ms, result=body.result, truncated=body.truncated,
                                 step_budget=None if budget_free else ps["budget"]["calls"],
                                 run_budget=run["plan"]["limits"]["calls"])
    except CallRefused as exc:
        raise AuthError(str(exc), status_code=409) from None
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
              principal: Principal = Depends(_me_write)) -> dict:
    """단계를 닫는다 — 실행자가 본 것을 원장과 맞대 고친다. 호출 없이 ok · empty 면 skipped, 결과가 다 오류면 failed, keys 의 값은 그 단계의
    성공한 호출 결과에 글자 그대로 있고 그 호출의 인자(JSON)에는 없어야 다음 단계로 넘어간다(지어낸 키 · 잘못 이은 제품을 막는다, AR-D2 — 실패한
    호출의 글 · 받은 인자를 되돌려 준 값은 근거가 아니다, C-12), 원장에 없는 인용은 뗀다. ambiguous 는 후보와 함께 실행을
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
    # 키의 근거 — 성공한 호출의 (결과, 인자 JSON). 실패한 호출의 오류 글과, 모델이 넣은 인자를 도구가 되돌려 준 값(「'SM-S999' 를 찾을 수
    # 없다」 · {"query": "SM-S999", "items": []})은 근거가 아니다. 에이전트 실행기의 봉투 검사도 같은 규칙이다(C5)
    sources = [(c["result"], json.dumps(c["args"], ensure_ascii=False)) for c in calls if c["ok"]]
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
    keys, unsourced, echoed, unexpected = {}, [], [], []
    for k, v in env.keys.items():
        if want and k not in want:
            unexpected.append(k)
        elif (v and any(v in res and v not in args for res, args in sources)) or (picked and v in picked):
            keys[k] = v
        elif v and any(v in c["result"] for c in calls):
            echoed.append(k)
        else:
            unsourced.append(k)
    if unexpected:
        flags.append(f"계획에 없는 키는 뺐다: {', '.join(unexpected)}")
    if unsourced:
        flags.append(f"결과에 글자 그대로 없는 키는 넘기지 않는다: {', '.join(unsourced)}")
    if echoed:
        flags.append(f"받은 인자를 되돌려 준 값 · 실패한 호출에만 있는 키는 넘기지 않는다: {', '.join(echoed)}")
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
def pick(request: Request, run_id: str, step: str, body: PickIn, principal: Principal = Depends(_me_write)) -> dict:
    """고를 것이 있는 단계에서 사람이 후보 하나를 고른다 — 그 키를 단계의 첫 기대 키로 넘기고 단계를 ok 로 닫는다. 기다리는(waiting) 실행에서만
    고른다 — 멈춘 실행의 고르기 단추가 다른 탭 · 앞 메시지에 남아 있어도 그 실행을 running 으로 되살리지 않는다(C-12)."""
    store = _store(request)
    run = _run(request, principal, run_id)
    if run["state"] != "waiting":
        raise AuthError(f"실행이 {run['state']} 다 — 고를 수 없다", status_code=409)
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


def _ra_state(run: dict) -> dict:
    """RA 올리기 방식과 지금까지의 올리기 결과 — 실행 행의 지금 값이다(렌더 저장본에 넣지 않는다 — /ra 가 뒤에 고친다). GET · POST /report 가
    같은 칸으로 낸다."""
    return {"ra_upload": ((run["plan"].get("report") or {}).get("ra") or {}).get("upload") or "off",
            "ra_report_id": run.get("ra_report_id"), "ra_error": run.get("ra_error")}


@router.get("/runs/{run_id}/report")
def get_report(request: Request, run_id: str, principal: Principal = Depends(_me_any)) -> dict:
    """낸 보고서 읽기(주인) — 화면이 대화의 루틴 턴을 다시 열 때(R3 3.3). 아직 안 냈으면 report_ready 거짓 · 빈 글. ra_upload 는 올리기 방식이다."""
    run = _run(request, principal, run_id)
    return {"run_id": run["id"], "state": run["state"], "report_ready": bool(run.get("report_md")),
            "report_md": run.get("report_md") or "", **_ra_state(run)}


@router.post("/runs/{run_id}/report")
def report(request: Request, run_id: str, body: ReportIn, principal: Principal = Depends(_me_write)) -> dict:
    """모든 단계가 닫힌 뒤 — 보고서를 렌더해 원장에 두고 실행을 끝낸다. RA 블록(deliberation v1)과 올리기 방식을 돌려준다 — 올리는 것은
    게이트웨이가 호출자 이름으로 한다(서비스 계정 없음). 스펙은 실행이 묶인 판(version_id)의 것이다 — 공개 범위 · 보관을 다시 보지 않는다(주인이
    도중에 보관 · 비공개로 바꿔도 이 실행의 보고서는 난다). 렌더한 RA 블록 · 커버리지 · 경고는 실행 행에 두고, 끝난 실행에 다시 내면 다시 렌더하지
    않고 그 저장본을 돌려준다(새 절은 보지 않는다 — RA 'ask' 의 upload=true 다시 내기, R3-D12). 저장본이 없는 끝난 실행(R3 전)은 그대로 409.
    두 길 모두 실행 행의 지금 RA 결과(ra_report_id · ra_error)와 올리기 방식(ra_upload)을 함께 싣는다 — 저장본을 다시 받은 게이트웨이가 이미
    올렸는지 알고 RA 초안을 두 번 만들지 않게."""
    store = _store(request)
    run = _run(request, principal, run_id)
    if run["state"] == "done" and run.get("report"):
        return {"report_md": run.get("report_md") or "", **run["report"], **_ra_state(run)}
    if run["state"] != "running":
        raise AuthError(f"실행이 {run['state']} 상태다 — 보고서는 도는 실행에서만 낸다", status_code=409)
    stages = store.stages(run_id)
    open_ = [s["step_id"] for s in stages if s["state"] not in CLOSED]
    if open_:
        raise AuthError(f"아직 닫히지 않은 단계: {', '.join(open_)} — routine_step_done 으로 닫는다", status_code=409)
    raw = store.version_spec(run["version_id"])
    if raw is None:
        raise AuthError("이 실행의 루틴 판을 찾을 수 없습니다", status_code=404)
    spec = RoutineSpec.model_validate(raw)
    out = render_report(spec=spec, run=run, steps=run["plan"]["steps"], stages=stages, calls=store.calls(run_id),
                        sections=body.sections, title=body.title)
    saved = {"coverage": out["coverage"], "warnings": out["warnings"],
             "ra": {"upload": spec.report.ra.upload, "title": out["title"], "blocks": out["blocks"], "tags": out["tags"]}}
    store.set_run(run_id, state="done", report_md=out["report_md"], report_json=json.dumps(saved, ensure_ascii=False))
    return {"report_md": out["report_md"], **saved, **_ra_state(run)}


@router.post("/runs/{run_id}/ra")
def ra_result(request: Request, run_id: str, body: RaIn, principal: Principal = Depends(_me_write)) -> dict:
    run = _run(request, principal, run_id)
    if run["state"] != "done":
        raise AuthError("보고서를 낸 뒤에만 RA 결과를 적는다", status_code=409)
    _store(request).set_run(run_id, ra_report_id=body.report_id, ra_error=None if body.report_id else (body.error or "까닭 없음"))
    return {"ok": True}


# 멈춤이 이 실행이 세운 심의를 접는 데 쓰는 시간 전부(도구 지도 · 세션 열기 · 접기) — 게이트웨이가 늦거나 죽어도 멈춤 답을 붙잡지 않는다
# (멈춤은 그 전에 원장에 선다). 세션 닫기는 따로 5초까지다
DELIB_FOLD_S = 15.0


def _started_jobs(calls: list[dict]) -> list[str]:
    """원장 호출 가운데 성공한 심의 시작(hwax-deliberation:deliberate_start)의 job_id — 답(엔진 요약 JSON)의 최상위 칸이다(게이트웨이
    _rt_job_id · 에이전트 서버 _prior_job 이 읽는 칸). 원장 차례대로, 겹침 없이. 거절된 시작에는 잡이 없다."""
    out: list[str] = []
    for c in calls:
        if not c["ok"] or (c["backend"], c["tool"]) != (DELIB_BACKEND, "deliberate_start"):
            continue
        try:
            body = json.loads(c.get("result") or "null")
        except ValueError:
            continue
        jid = str(body.get("job_id") or "").strip() if isinstance(body, dict) else ""
        if jid and jid not in out:
            out.append(jid)
    return out


def _exposed(tmap: dict, backend: str, original: str) -> str:
    """(백엔드, 원래 이름) → 이 박스 게이트웨이의 노출 이름 — /tools-map 에서 _catalog 와 같은 별칭 규칙으로 찾고, 못 찾으면 원래 이름이다
    (에이전트 서버 routine 의 exposed 와 같다)."""
    p = backend.replace("-", "") + "_"
    for name, bk in (tmap.get("map") or {}).items():
        if bk == backend and (name[len(p):] if name.startswith(p) else name) == original:
            return name
    return original


async def _fold_delibs(request: Request, settings: Settings, principal: Principal, run_id: str,
                       jobs: list[str]) -> tuple[list[str], list[dict]]:
    """멈춘 실행이 세운 심의를 접는다(deliberate_cancel, best-effort) — (접은 job_id, [{job_id, error}]).

    그 사람 명의의 **챗 PAT** 로 부른다 — 엔진은 시작한 사람의 심의만 접게 하고(_foreign), 실행기(Qwen · Claude 길)가 심의를 세운 신원도 그
    사람이다. 절차 PAT 는 쓰지 않는다 — purpose=procedure 는 게이트웨이 정확이름 차단의 면제 표지라 이 길에 실을 까닭이 없다(docs/analysis-routines
    — 루틴은 절차 PAT 를 쓰지 않는다). 세션은 절차 실행기의 GatewaySession(같은 클라이언트, 감사 corr 는 routine:<실행>:cancel)이고, 시간 전부를
    DELIB_FOLD_S 로 묶는다. 접지 못한 것(게이트웨이 오류 · 연결 실패 · 시간 초과 · 엔진의 거절)은 까닭과 함께 돌려준다 — 예외로 올리지 않는다."""
    # 챗 PAT 발급의 정본(30분 창 · 결정적 jti) — 무거운 챗 모듈이라 쓸 때 읽는다
    from app.agent.routes import _chat_user_pat

    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:                                       # 다른 토큰(절차 · 서비스 계정)으로 대신 접지 않는다
        return [], [{"job_id": j, "error": "그 사람 명의의 챗 PAT 를 찍지 못했다"} for j in jobs]
    done: list[str] = []
    errors: list[dict] = []
    sess = None
    try:
        async with asyncio.timeout(DELIB_FOLD_S):
            runner = _runner(request)
            name = _exposed(await _tools_map(request), DELIB_BACKEND, "deliberate_cancel")
            sess = GatewaySession(runner.gateway_url, runner._client, corr=f"routine:{run_id}:cancel")
            await sess.open(pat)
            for jid in jobs:
                is_err, content = await sess.call(name, {"job_id": jid}, pat, DELIB_FOLD_S)
                if is_err:
                    errors.append({"job_id": jid, "error": (J.join_content(content)[0].strip() or "오류로 답했다")[:300]})
                else:
                    done.append(jid)
    except Exception as exc:  # noqa: BLE001 — 접기 실패로 멈춤을 되돌리지 않는다(멈춤은 이미 원장에 섰다)
        why = (f"{DELIB_FOLD_S:g}초 안에 끝나지 않았다" if isinstance(exc, TimeoutError)
               else (f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__)[:300])
        tried = set(done) | {e["job_id"] for e in errors}
        errors += [{"job_id": j, "error": why} for j in jobs if j not in tried]
    finally:
        if sess is not None:
            try:
                async with asyncio.timeout(5):
                    await sess.close(pat)
            except Exception:  # noqa: BLE001 — 닫기 실패는 접은 결과를 바꾸지 않는다
                logger.info("루틴 %s 멈춤 — 심의 접기 세션을 닫지 못했다", run_id, exc_info=True)
    if errors:
        logger.warning("루틴 %s 멈춤 — 심의 %s 를 접지 못했다", run_id, ", ".join(e["job_id"] for e in errors))
    return done, errors


@router.post("/runs/{run_id}/cancel")
async def cancel(request: Request, run_id: str, settings: Settings = Depends(get_settings),
                 principal: Principal = Depends(_me_write)) -> dict:
    """사람의 멈춤 — 실행을 cancelled 로 세우고 이 실행이 세운 심의를 접는다(R3-design §8 '실행을 멈추면 시작한 심의도 접는다'). 접을 것은
    닫히지 않은 심의 단계의 원장에 있는 성공한 deliberate_start 의 job_id 다 — 닫힌 단계(결정문을 읽었다 · 실패로 닫았다)와 플랫폼 단계는 보지
    않는다. 실행기가 살아 있으면 그쪽도 접는다(_delib_fold — 두 번 접어도 엔진은 '이미 끝난 잡이다' 로 답한다). 실행기가 없으면(재기동 · 실행기
    오류로 멈춤 · Claude 길) 접는 곳이 여기뿐이다 — 재기동 뒤 다시 줄 선 심의가 멈춤이 풀리면 몇 시간씩 돌며 GLM 자리와 그 사람의 자리를
    쥐었다(R2 반대 검토 #2). 멈춤을 접기보다 먼저 원장에 세운다 — 그 뒤에 닿는 심의 시작은 원장 쓰기가 거절되고 게이트웨이가 접으며
    (_rt_fold_orphan), 그 앞에 닿은 것은 원장에 있다. 접기는 멈춤을 막지 않는다 — 결과는 delib_cancelled · delib_cancel_errors 와 실행의 까닭에 남는다."""
    store = _store(request)
    run = _run(request, principal, run_id)
    if run["state"] not in ("queued", "running", "waiting"):
        raise AuthError(f"실행이 이미 {run['state']} 상태다", status_code=409)
    store.set_run(run_id, state="cancelled", reason="사람이 멈췄다")
    open_ = {st["step_id"] for st in store.stages(run_id) if st["state"] not in CLOSED}
    steps = [p["id"] for p in run["plan"]["steps"] if p.get("kind") == "deliberation" and p["id"] in open_]
    jobs = _started_jobs(store.calls(run_id, steps, with_result=True))
    if not jobs:
        return {"ok": True, "state": "cancelled", "delib_cancelled": [], "delib_cancel_errors": []}
    done, errors = await _fold_delibs(request, settings, principal, run_id, jobs)
    reason = "사람이 멈췄다"
    if done:
        reason += f" — 이 실행이 세운 심의 {' · '.join(done)} 를 접었다"
    if errors:
        reason += (" — " + " · ".join(f"심의 {e['job_id']} 는 접지 못했다({e['error'][:160]})" for e in errors)
                   + ". 서버에서 계속 돌 수 있다 — deliberate_cancel 로 접는다")
    store.set_run(run_id, reason=reason)
    return {"ok": True, "state": "cancelled", "delib_cancelled": done, "delib_cancel_errors": errors}
