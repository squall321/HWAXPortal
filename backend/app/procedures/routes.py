"""절차 API — prefix `/procedures-api`.

접두사가 SPA 경로 `/procedures/*` 와 다른 이유 — 같으면 새로고침이 JSON 을 받는다.
`App.tsx` 가 `/changelog`(API)와 `/updates`(SPA)를 가른 것과 같은 사고를 피한다.

**모든 라우트가 `ensure(principal, "feat:procedures")` 를 부른다.** `access.yaml` 의
`features:` 선언만으로는 아무 라우트도 안 막힌다 — 기능 키는 타일·게이트웨이 백엔드에만
자동으로 묶인다. 실행 계열은 거기에 더해 실행 소유자까지 본다.

실행은 **요청 밖에서** 돈다(202 + 폴링). 절차 경로는 nginx catch-all 이라 기본
`proxy_read_timeout` 이 60초인데, 동기로 두면 nginx 는 504 를 주고 uvicorn 은 핸들러를
끝까지 돌려 **화면은 실패·서버는 성공**이 된다. 그 상태에서 사람이 다시 누르면 비멱등
쓰기가 두 번 나간다. 이 고장은 dev vite 프록시에선 재현되지 않는다.
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.access.policy import ADMIN_GROUP
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import BACKEND_DIR, get_settings
from app.deps import ensure, get_current_principal, require_csrf
from app.procedures.models import (
    ProcedureSpec,
    SpecError,
    Step,
    check_against_schemas,
    coerce_inputs,
    schema_fingerprint,
    validate_spec,
)
from app.procedures.runner import RunnerError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/procedures-api", tags=["procedures"])

FEAT = "feat:procedures"
# create_task 의 결과를 붙잡아 둔다 — 안 잡으면 GC 가 실행 중인 실행을 거둬 간다.
_TASKS: set[asyncio.Task] = set()


def _store(request: Request):
    st = getattr(request.app.state, "procedures_store", None)
    if st is None:
        raise AuthError("절차 저장소가 열리지 않았습니다", status_code=503)
    return st


def _runner(request: Request):
    r = getattr(request.app.state, "procedures_runner", None)
    if r is None:
        raise AuthError("절차 실행기가 서지 않았습니다", status_code=503)
    return r


def _me(principal: Principal = Depends(get_current_principal)) -> Principal:
    ensure(principal, FEAT)
    return principal


def _owned(request: Request, principal: Principal, run_id: str) -> dict:
    """실행은 공유하지 않는다 — 결과에 그 사람 시야의 데이터가 담긴다."""
    run = _store(request).get_run(run_id, owner_sub=principal.subject)
    if run is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    return run


def _spawn(coro, what: str) -> None:
    t = asyncio.create_task(coro)
    _TASKS.add(t)

    def _done(task: asyncio.Task) -> None:
        _TASKS.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("절차 %s 실패", what, exc_info=task.exception())

    t.add_done_callback(_done)


# ── 무인증 ───────────────────────────────────────────────────────────────
@router.get("/health")
def health(request: Request, response: Response) -> dict:
    """모듈만 따로 본다 — 포털 `/health` 는 상수라 저장소가 안 열려도 200 이다."""
    st = getattr(request.app.state, "procedures_store", None)
    if st is None:
        response.status_code = 503
        return {"ok": False,
                "error": getattr(request.app.state, "procedures_error", "not initialised")}
    try:
        return {"ok": True, **st.health()}
    except Exception as exc:  # noqa: BLE001
        response.status_code = 503
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


# ── 도구 ─────────────────────────────────────────────────────────────────
@router.get("/tools")
async def tools(request: Request, principal: Principal = Depends(_me)) -> dict:
    """사용자 PAT `tools/list` + 무인증 `/tools-map` 라벨.

    `/tools-map` 만 쓰면 이 사람이 **못 부르는 도구까지** 보여 골라서 실행하면 403 이고,
    스키마도 없다. 권한 필터의 정본은 `tools/list` 쪽이다.
    """
    cat = await _runner(request).catalog(principal)
    labels = await _tools_map(request)
    out = []
    for name, meta in sorted(cat.items()):
        app = labels.get("map", {}).get(name)
        out.append({
            "name": name, "backend": app,
            "area": (labels.get("areas") or {}).get(name),
            "description": (meta.get("description") or "").strip().split("\n")[0][:200],
            "inputSchema": meta.get("inputSchema") or {},
            "schema_fp": schema_fingerprint(meta.get("description") or "",
                                            meta.get("inputSchema") or {}),
        })
    return {"count": len(out), "tools": out}


async def _tools_map(request: Request) -> dict:
    url = (getattr(request.app.state, "procedures_runner").gateway_url or "").rstrip("/")
    try:
        c = _runner(request)._client
        r = await c.get(f"{url}/tools-map", timeout=20.0)
        return r.json() if r.status_code == 200 else {}
    except Exception:  # noqa: BLE001 — 라벨이 없어도 도구 목록은 쓸 수 있다
        logger.info("tools-map 조회 실패 — 라벨 없이 낸다", exc_info=True)
        return {}


# ── 2단 도구 — 역량이 도구 하나 뒤에 숨은 자리(PLAN §9-4) ────────────────
@router.get("/dispatchers")
def dispatchers(principal: Principal = Depends(_me)) -> dict:
    """등록부에 확정된 2단 도구들. 화면이 "이 도구는 뒤에 여럿이 있다" 를 알게 한다."""
    from app.procedures import dispatch as _dsp

    out = []
    for d in _dsp.load().values():
        out.append({"backend": d.backend, "tool": d.tool, "selector": d.selector,
                    "payload": d.payload, "list": d.list_tool, "describe": d.describe,
                    "note": d.note})
    return {"dispatchers": out}


@router.get("/dispatchers/{backend}/{tool}/items")
async def dispatcher_items(request: Request, backend: str, tool: str,
                           name: str | None = None,
                           principal: Principal = Depends(_me)) -> dict:
    """그 도구 뒤에 **무엇이 있나**, 그리고 하나를 고르면 **그 계약**.

    `name` 없이 부르면 목록, 주면 그 항목의 JSON Schema 다. 이게 없으면 사람이
    `run_operation(operation=…)` 의 `operation` 에 무엇을 적을지 알 방법이 없다 —
    47개가 도구 하나로 보이기 때문이다(§9-4).
    """
    from app.procedures import dispatch as _dsp

    d = _dsp.load().get((backend, tool))
    if d is None:
        raise AuthError("등록부에 없는 2단 도구입니다", status_code=404)
    runner = _runner(request)
    if name:
        sch = (await runner.second_stage_one(principal, d, name))
        if sch is None:
            # ⚠ 계약을 못 받은 것과 그 항목이 없는 것은 다르다 — 못 받았다고 말한다.
            return {"name": name, "schema": None,
                    "note": "그 항목의 계약을 못 받았습니다 — 이름이 틀렸거나 앱이 안 붙어 있습니다"}
        return {"name": name, "schema": sch}
    items = await runner.dispatcher_items(principal, d)
    return {"backend": backend, "tool": tool, "selector": d.selector,
            "payload": d.payload, "items": items, "note": d.note}


# ── 절차 ───────────────────────────────────────────────────────────────
class ProcedureIn(BaseModel):
    title: str
    spec: dict
    visibility: str = Field(default="all", pattern="^(all|private)$")
    derived_from_run: str | None = None


async def _validated(request: Request, raw: dict,
                     principal: Principal | None = None) -> tuple[ProcedureSpec, list[str]]:
    """저장 시점 검증. `principal` 을 주면 **게이트웨이 스키마 대조까지** 한다.

    ⚠ 스키마 대조가 `/validate` 에만 있으면 그건 **권고**지 검증이 아니다. API 를 직접
    부르면 그대로 통과한다. 그래서 저장에서도 같은 검사를 한다.

    ⚠ 다만 **못 물어봤을 때와 틀렸을 때를 섞지 않는다.** 게이트웨이가 불통이면 대조를
    건너뛰고 그 사실을 경고로 남긴다 — 못 물어본 것을 통과로도, 실패로도 치지 않는다.
    """
    spec = ProcedureSpec.model_validate(raw)
    errs = validate_spec(
        spec, max_steps=int(getattr(get_settings(), "procedures_max_steps", 30)))
    if principal is not None:
        cat: dict = {}
        try:
            runner = _runner(request)
            cat = await runner.catalog(principal)
        except Exception:  # noqa: BLE001 — 불통이 저장을 막지 않는다. 다만 말한다.
            logger.info("저장 — 도구 카탈로그 조회 실패(대조 건너뜀)", exc_info=True)
        # ⚠ **빈 카탈로그를 "그 도구가 없다" 로 읽으면 안 된다.** 게이트웨이는 465종을
        # 들고 있으므로 0건은 "못 물어봤다" 는 뜻이다. 그걸 실패로 치면 게이트웨이가
        # 잠깐 흔들릴 때 멀쩡한 절차가 저장 거절된다 — 모른다와 틀렸다를 섞는 것이다.
        if cat:
            try:
                second = await runner.second_stage(principal, spec)
            except Exception:  # noqa: BLE001
                second = {}
            # 저장에서는 **안 보이는 도구**를 막지 않는다(권한·일시 불통과 구분 불가).
            # 인자 오타처럼 **보이는 도구에서 확실한 것**만 거절한다.
            errs += check_against_schemas(spec, cat, second, missing_is_error=False)
        else:
            errs.append("warn:게이트웨이에 못 물어봐 **도구 스키마 대조를 건너뛰었다** — "
                        "인자 오타가 실행 시점에야 드러날 수 있다")
    hard = [e for e in errs if not e.startswith("warn:")]
    if hard:
        raise AuthError("절차를 저장할 수 없습니다:\n- " + "\n- ".join(hard), status_code=422)
    return spec, [e[5:] for e in errs if e.startswith("warn:")]


# ── 씨앗 절차 ────────────────────────────────────────────────────────────
# 리포에 함께 오는 정본 예제다(docs/procedures/fixtures/*.yaml). 첫날 화면이 비어 있으면
# 사람은 무엇을 만들 수 있는지 모른다 — 씨앗은 "이렇게 생긴 것" 을 보여 주는 자리다.
# 가져오기는 **같은 저장 시점 검증**을 그대로 탄다(우회로가 아니다).
SEED_DIR = Path(BACKEND_DIR).parent / "docs" / "procedures" / "fixtures"
_SEED_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")


def _seed_path(name: str) -> Path:
    """이름으로만 고른다 — 경로를 받지 않는다(디렉터리 탈출 차단)."""
    if not _SEED_NAME.match(name):
        raise AuthError("씨앗 이름이 아닙니다", status_code=400)
    p = SEED_DIR / f"{name}.yaml"
    if not p.is_file():
        raise AuthError("그런 씨앗이 없습니다", status_code=404)
    return p


@router.get("/seeds")
def list_seeds(principal: Principal = Depends(_me)) -> dict:
    out = []
    for f in sorted(SEED_DIR.glob("*.yaml")) if SEED_DIR.is_dir() else []:
        try:
            raw = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            spec = ProcedureSpec.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — 깨진 씨앗이 목록을 통째로 죽이지 않게
            out.append({"name": f.stem, "title": f.stem, "broken": f"{type(exc).__name__}"})
            continue
        out.append({
            "name": f.stem, "title": spec.title, "steps": len(spec.steps),
            "vars": [{"key": v.key, "label": v.label, "why": v.why} for v in spec.vars],
            "gates": [st.tool for st in spec.steps if st.gate == "human"],
            "backends": sorted({st.backend for st in spec.steps}),
        })
    return {"seeds": out}


@router.post("/seeds/{name}/import", status_code=201,
             dependencies=[Depends(require_csrf)])
async def import_seed(request: Request, name: str,
                principal: Principal = Depends(_me)) -> dict:
    """씨앗을 내 절차로 들인다. 들어온 뒤에는 보통 절차와 똑같다(고치면 새 판본)."""
    raw = yaml.safe_load(_seed_path(name).read_text(encoding="utf-8")) or {}
    spec, warns = await _validated(request, raw, principal)
    store = _store(request)
    # 씨앗은 리포와 함께 **자란다**(예시가 늘고 경고가 붙는다). 다시 가져올 때마다 사본이
    # 생기면 목록이 같은 이름으로 채워지고, 어느 것이 최신인지 사람이 알 수 없다.
    # 이미 들여놓은 것이 있으면 **판본을 올린다** — 옛 판본과 그 이력은 그대로 남는다.
    existing = store.find_by_seed(owner_sub=principal.subject, seed=name)
    if existing:
        got = store.add_version(procedure_id=existing, author_sub=principal.subject, spec=raw)
        return {**got, "id": existing, "warnings": warns, "from_seed": name, "updated": True}
    got = store.create_procedure(
        owner_sub=principal.subject, spec=raw, title=spec.title, visibility="all",
        from_seed=name)
    return {**got, "warnings": warns, "from_seed": name, "updated": False}


@router.get("/procedures")
def list_procedures(request: Request, principal: Principal = Depends(_me)) -> dict:
    return {"procedures": _store(request).list_procedures(owner_sub=principal.subject)}


@router.post("/procedures", status_code=201, dependencies=[Depends(require_csrf)])
async def create_procedure(request: Request, body: ProcedureIn,
                  principal: Principal = Depends(_me)) -> dict:
    _, warns = await _validated(request, body.spec, principal)
    got = _store(request).create_procedure(
        owner_sub=principal.subject, spec=body.spec, title=body.title,
        visibility=body.visibility, derived_from_run=body.derived_from_run)
    return {**got, "warnings": warns}


@router.get("/procedures/{procedure_id}")
def get_procedure(request: Request, procedure_id: str,
               principal: Principal = Depends(_me)) -> dict:
    v = _store(request).latest_version_of(procedure_id)
    if v is None:
        raise AuthError("절차를 찾을 수 없습니다", status_code=404)
    return v


@router.post("/procedures/{procedure_id}/versions", status_code=201,
             dependencies=[Depends(require_csrf)])
async def add_version(request: Request, procedure_id: str, body: ProcedureIn,
                principal: Principal = Depends(_me)) -> dict:
    _, warns = await _validated(request, body.spec, principal)
    try:
        got = _store(request).add_version(
            procedure_id=procedure_id, author_sub=principal.subject, spec=body.spec,
            derived_from_run=body.derived_from_run)
    except KeyError:
        raise AuthError("절차를 찾을 수 없습니다", status_code=404) from None
    return {**got, "warnings": warns}


# ── 실행 ───────────────────────────────────────────────────────────────────
class RunIn(BaseModel):
    procedure_id: str | None = None
    version_id: str | None = None
    vars: dict = Field(default_factory=dict)
    mode: str = Field(default="plan", pattern="^(plan|live)$")
    title: str | None = None


# ReportArchive 는 **사용자별 연결 토큰**으로 돈다(포털 토큰 페이지에서 등록). 등록이
# 없으면 게이트웨이가 서비스 계정으로 내려앉아 **남의 함에 쓰거나 401 이 난다** — 어느
# 쪽이든 그 단계에 가서야 안다. 시작 전에 본다.
RA_BACKEND = "reportarchive"


def _ra_precheck(request: Request, spec: ProcedureSpec, principal: Principal) -> list[str]:
    """RA 단계가 있는데 연결이 없으면 **시작 전에** 말한다(PLAN S1).

    ⚠ 막지는 않는다. 계획 모드로 무엇을 부를지만 보려는 경우가 있고, 관리자가 남의
    절차를 검토할 수도 있다. **모르는 것과 틀린 것을 안 섞는 것**과 같은 자세다.
    """
    tools = [st.tool for st in spec.steps if st.backend == RA_BACKEND]
    if not tools:
        return []
    store = getattr(request.app.state, "user_store", None)
    if store is None:
        return []
    try:
        conn = store.get_connection(email=principal.email, service=RA_BACKEND)
    except Exception:  # noqa: BLE001 — 사전검사 실패가 실행을 막지 않는다
        logger.info("RA 사전검사 실패(건너뜀)", exc_info=True)
        return []
    if conn and conn.get("token"):
        if not conn.get("workspace"):
            return [f"Report Archive 연결은 있는데 **워크스페이스를 안 골랐습니다** — "
                    f"보고서가 개인함에 쌓입니다(단계: {', '.join(tools[:3])})"]
        return []
    return [f"Report Archive 연결이 없습니다 — 포털 **토큰 페이지**에서 등록하세요. "
            f"없으면 서비스 계정으로 내려앉아 **남의 함에 쓰거나 401** 이 납니다"
            f"(단계: {', '.join(tools[:3])})"]


@router.post("/runs", status_code=202, dependencies=[Depends(require_csrf)])
async def start_run(request: Request, body: RunIn,
                    principal: Principal = Depends(_me)) -> dict:
    """`procedure_id` 가 없으면 **빈 실행** — 도구를 한 단계씩 돌리는 절차다."""
    store, runner = _store(request), _runner(request)
    version = None
    if body.version_id or body.procedure_id:
        version = (store.get_version(body.version_id) if body.version_id
                   else store.latest_version_of(body.procedure_id))
        if version is None:
            raise AuthError("절차 판본을 찾을 수 없습니다", status_code=404)

    # ⚠ **실행을 만들기 전에** 형을 맞추고 빠진 값을 잡는다. 화면은 문자열밖에 못 보내므로
    # 여기서 안 풀면 적층 정의가 문자열인 채 도구로 가고, 필수 변수가 비면 그 변수를 쓰는
    # 단계에 가서야 터진다 — 그때는 앞 단계가 이미 게이트웨이를 부르고 난 뒤다.
    spec = ProcedureSpec.model_validate(version["spec"]) if version else None
    inputs = dict(body.vars)
    if spec is not None:
        try:
            inputs = coerce_inputs(spec, body.vars)
        except SpecError as exc:
            raise AuthError(str(exc), status_code=422) from None

    notes = _ra_precheck(request, spec, principal) if spec is not None else []

    run_id = store.create_run(
        owner_sub=principal.subject, run_by=principal.subject,
        procedure_version_id=(version or {}).get("version_id"), inputs=inputs,
        origin="replay" if version else "manual", mode=body.mode, title=body.title)

    if spec is None:
        return {"run_id": run_id, "state": "queued", "empty": True}

    _spawn(runner.run(run_id=run_id, spec=spec, principal=principal), f"run {run_id}")
    return {"run_id": run_id, "state": "queued", "poll": f"/procedures-api/runs/{run_id}",
            **({"warnings": notes} if notes else {})}


class StepIn(BaseModel):
    backend: str
    tool: str
    args: dict = Field(default_factory=dict)
    save: dict[str, str] | None = None
    raw: bool = False
    unwrap: str | None = None
    expect: str = Field(default="fast", pattern="^(fast|slow|job)$")
    schema_fp: str | None = None


@router.post("/runs/{run_id}/steps", status_code=202,
             dependencies=[Depends(require_csrf)])
async def add_step(request: Request, run_id: str, body: StepIn,
                   principal: Principal = Depends(_me)) -> dict:
    """빈 실행에 단계 하나. 이미 도는 단계가 있으면 **409** — 같은 단계 재실행 방지다."""
    run = _owned(request, principal, run_id)
    if any(s["state"] == "running" for s in run["steps"]):
        raise AuthError("이미 도는 단계가 있습니다", status_code=409)
    if run["state"] in ("cancelled", "gated"):
        raise AuthError(f"이 실행은 {run['state']} 상태입니다", status_code=409)

    step = Step(**body.model_dump())
    one = ProcedureSpec(title="ad-hoc", steps=[step])
    hard = [e for e in validate_spec(one) if not e.startswith("warn:")]
    # 미지 변수는 빈 실행에서 정상이다(앞 단계가 실행 입력에 값을 합쳐 둔다)
    hard = [e for e in hard if "어디서도 안 만든다" not in e]
    if hard:
        raise AuthError("이 단계는 실행할 수 없습니다:\n- " + "\n- ".join(hard), status_code=422)

    _spawn(_step_and_log(request, run_id, step, principal), f"step {run_id}")
    return {"run_id": run_id, "state": "queued", "poll": f"/procedures-api/runs/{run_id}"}


async def _step_and_log(request: Request, run_id: str, step: Step, principal) -> None:
    try:
        await _runner(request).step_once(run_id=run_id, step=step, principal=principal)
    except RunnerError as exc:
        _store(request).set_run_state(run_id, "failed", stage="runner", ended=True)
        logger.warning("절차 단계 시작 실패 run=%s: %s", run_id, exc)


@router.get("/runs")
def list_runs(request: Request, procedure_id: str | None = None,
              principal: Principal = Depends(_me)) -> dict:
    """확인 대기가 맨 위에 온다 — 게이트에서 멈춘 실행의 표면이 이 목록이다.

    `procedure_id` 를 주면 **그 절차의 이력만** 낸다. 절차를 한 번 만들면 그것으로 돌린
    실행이 쌓이는데, 종전에는 전체 목록에 섞여 어느 절차의 것인지 볼 수가 없었다.
    """
    return {"runs": _store(request).list_runs(
        owner_sub=principal.subject, procedure_id=procedure_id)}


class ReplayIn(BaseModel):
    mode: str = Field(default="live", pattern="^(plan|live)$")
    vars: dict | None = None   # 주면 그 값만 덮어쓴다(나머지는 지난 실행 그대로)


@router.post("/runs/{run_id}/replay", status_code=202,
             dependencies=[Depends(require_csrf)])
async def replay_run(request: Request, run_id: str, body: ReplayIn,
                     principal: Principal = Depends(_me)) -> dict:
    """**지난 실행을 그 값 그대로 다시 돌린다.**

    이력이 값을 들고 있는데 다시 돌릴 길이 없으면, 사람이 화면을 보며 여섯 칸을 손으로
    옮겨 적어야 한다 — 옮겨 적는 순간 "같은 입력" 이라는 보장이 사라진다.

    예제 실행(`origin='sample'`)도 여기서 돌린다. 기록된 결과를 **재생하는 것이 아니라**
    그 입력으로 도구를 실제로 다시 부른다 — 그래서 지금 데이터로 계산된 값이 나온다.
    """
    store, runner = _store(request), _runner(request)
    src = _owned(request, principal, run_id)
    if not src.get("procedure_version_id"):
        raise AuthError("빈 실행은 다시 돌릴 절차가 없습니다", status_code=422)
    version = store.get_version(src["procedure_version_id"])
    if version is None:
        raise AuthError("그 판본이 더 이상 없습니다", status_code=404)

    spec = ProcedureSpec.model_validate(version["spec"])
    # 지난 실행의 inputs 에는 **앞 단계가 뽑은 save 값도 섞여 있다**(merge_inputs).
    # 그대로 넘기면 이번 실행이 옛 중간값을 쥔 채 시작한다 — 선언된 변수만 걸러 낸다.
    declared = {v.key for v in spec.vars}
    seed_vars = {k: v for k, v in (src.get("inputs") or {}).items() if k in declared}
    seed_vars.update(body.vars or {})
    try:
        inputs = coerce_inputs(spec, seed_vars)
    except SpecError as exc:
        raise AuthError(str(exc), status_code=422) from None

    new_id = store.create_run(
        owner_sub=principal.subject, run_by=principal.subject,
        procedure_version_id=src["procedure_version_id"], inputs=inputs,
        origin="replay", mode=body.mode,
        title=src.get("title") or (version.get("spec") or {}).get("title"))
    _spawn(runner.run(run_id=new_id, spec=spec, principal=principal), f"run {new_id}")
    return {"run_id": new_id, "state": "queued", "from_run": run_id,
            "poll": f"/procedures-api/runs/{new_id}"}


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str, principal: Principal = Depends(_me)) -> dict:
    run = _owned(request, principal, run_id)
    for s in run["steps"]:
        s.pop("result_sha256", None)  # 화면은 본문을 따로 받는다
    return run


@router.get("/runs/{run_id}/steps/{ix}/result")
def step_result(request: Request, run_id: str, ix: int,
                principal: Principal = Depends(_me)) -> dict:
    _owned(request, principal, run_id)
    body = _store(request).step_result(run_id, ix)
    if body is None:
        raise AuthError("결과가 없습니다", status_code=404)
    return {"run_id": run_id, "ix": ix, "text": body}


class AckIn(BaseModel):
    args_sha256: str


class PickIn(BaseModel):
    value: Any   # 사람이 고른 후보의 값(목록의 `value`)


@router.post("/runs/{run_id}/steps/{ix}/pick", dependencies=[Depends(require_csrf)])
async def pick(request: Request, run_id: str, ix: int, body: PickIn,
               principal: Principal = Depends(_me)) -> dict:
    """룰이 여럿을 골랐을 때 **사람이 하나를 고른다**(PLAN §10-1).

    확인(ack)과 다르다. 확인은 "이대로 해라" 이고, 이쪽은 **"이것으로 해라"** 다.
    조용히 첫 번째를 집지 않으려면 이 자리가 있어야 한다.

    ⚠ **보여 준 후보 중에서만** 고를 수 있다. 아무 값이나 받으면 룰을 우회해 엉뚱한
    대상으로 절차가 돈다 — 그건 고르는 것이 아니라 박는 것이다.
    """
    store = _store(request)
    run = _owned(request, principal, run_id)
    steps = {s["ix"]: s for s in run["steps"]}
    if ix not in steps:
        raise AuthError("그 단계가 없습니다", status_code=404)
    notes = steps[ix].get("notes") or {}
    cands = notes.get("candidates")
    into = notes.get("pick_into")
    if not cands or not into:
        raise AuthError("이 단계는 고를 것이 없습니다", status_code=409)
    if not any(c.get("value") == body.value for c in cands):
        raise AuthError("보여 준 후보 중에서 골라 주세요", status_code=422)

    store.merge_inputs(run_id, {into: body.value})
    store.finish_step(run_id, ix, ok=True, state="done", stage="select:picked",
                      notes={**notes, "picked": body.value})
    version = store.get_version(run["procedure_version_id"] or "")
    if version is None:
        return {"picked": body.value, "resumed": False}
    spec = ProcedureSpec.model_validate(version["spec"])
    _spawn(_runner(request).run(run_id=run_id, spec=spec, principal=principal, start_at=ix + 1),
           f"resume {run_id}")
    return {"picked": body.value, "resumed": True}


# 배치 상한 — 사람이 표로 볼 수 있는 크기까지만. 넘으면 룰을 좁히라고 말한다.
BATCH_MAX = int(os.environ.get("PROCEDURES_BATCH_MAX", "50"))


class FanOutIn(BaseModel):
    values: list | None = None   # 안 주면 그 단계가 고른 후보 전부
    mode: str = Field(default="plan", pattern="^(plan|live)$")


@router.post("/runs/{run_id}/steps/{ix}/fan-out", status_code=202,
             dependencies=[Depends(require_csrf)])
async def fan_out(request: Request, run_id: str, ix: int, body: FanOutIn,
                  principal: Principal = Depends(_me)) -> dict:
    """룰이 고른 **전부**를 돌린다 — 하나를 고르는 대신(PLAN §10-1 · S5).

    "디스플레이 패널에 해당하는 것" 처럼 **여럿이 답인** 물음이 있다. 하나만 고르면
    나머지는 버려진다. 여기서는 후보마다 **실행을 하나씩** 만든다.

    배치는 **새 실행 N개**다 — 기존 기계가 그대로 돈다(게이트·재개·다시 돌리기·도출).
    그래서 사람 확인이 걸린 단계에서 **각자 알아서 멈춘다**. 초안 N개가 한꺼번에
    만들어지는 일이 없다(PLAN S5 "배치는 첫 gate 직전까지").

    ⚠ 기본이 **계획 모드**다. N개를 live 로 던지는 것은 사람이 골라야 한다.
    """
    store, runner = _store(request), _runner(request)
    run = _owned(request, principal, run_id)
    steps = {s["ix"]: s for s in run["steps"]}
    if ix not in steps:
        raise AuthError("그 단계가 없습니다", status_code=404)
    notes = steps[ix].get("notes") or {}
    cands, into = notes.get("candidates"), notes.get("pick_into")
    if not cands or not into:
        raise AuthError("이 단계는 고른 후보가 없습니다", status_code=409)
    if not run.get("procedure_version_id"):
        raise AuthError("빈 실행은 펼칠 절차가 없습니다", status_code=422)

    allowed = [c.get("value") for c in cands]
    want = body.values if body.values is not None else allowed
    # ⚠ **보여 준 후보 안에서만** 펼친다 — 아무 값이나 받으면 룰을 우회한다(pick 과 같은 규율).
    bad = [v for v in want if v not in allowed]
    if bad:
        raise AuthError(f"보여 준 후보 밖입니다: {bad[:3]}", status_code=422)
    if not want:
        raise AuthError("펼칠 대상이 없습니다", status_code=422)
    if len(want) > BATCH_MAX:
        raise AuthError(f"한 번에 {BATCH_MAX}개까지입니다 — 룰을 좁혀 주세요"
                        f"(지금 {len(want)}개)", status_code=422)

    version = store.get_version(run["procedure_version_id"])
    if version is None:
        raise AuthError("그 판본이 더 이상 없습니다", status_code=404)
    spec = ProcedureSpec.model_validate(version["spec"])
    declared = {v.key for v in spec.vars}
    base = {k: v for k, v in (run.get("inputs") or {}).items() if k in declared}

    batch_id = f"b-{run_id}-{ix}"
    made = []
    for val in want:
        new_id = store.create_run(
            owner_sub=principal.subject, run_by=principal.subject,
            procedure_version_id=run["procedure_version_id"],
            inputs={**base, into: val}, origin="batch", mode=body.mode,
            title=f"{run.get('title') or spec.title} — {val}", batch_id=batch_id)
        # 고른 값이 이미 범위에 있으니 **그 선택 단계 다음부터** 돈다.
        _spawn(runner.run(run_id=new_id, spec=spec, principal=principal, start_at=ix + 1),
               f"batch {new_id}")
        made.append({"run_id": new_id, "value": val})
    return {"batch_id": batch_id, "mode": body.mode, "count": len(made), "runs": made,
            "poll": f"/procedures-api/batches/{batch_id}"}


@router.get("/batches/{batch_id}")
def batch(request: Request, batch_id: str, principal: Principal = Depends(_me)) -> dict:
    """비교표 — 한 배치의 실행들을 나란히 본다(PLAN S5).

    ⚠ `inputs` 를 **그대로 열로 편다.** 단계 인자를 역파싱하면 치환된 뒤 값이라
    무엇이 달랐는지가 흐려진다.
    """
    store = _store(request)
    rows = store.list_runs(owner_sub=principal.subject, batch_id=batch_id, limit=BATCH_MAX)
    cols: list[str] = []
    for r in rows:
        for k in r.get("inputs") or {}:
            if k not in cols:
                cols.append(k)
        # ⚠ **실패한 것을 건너뛰고 계속하되, 무엇이 왜 실패했는지 표에 싣는다**(PLAN S5).
        # 상태만 보이면 "5건 중 2건 실패" 로 끝나고 사람이 실행을 하나씩 열어야 한다 —
        # 표의 값어치가 거기서 사라진다. 경고도 같이 싣는다(W120 처럼 결과는 정상인데
        # 경고만이 유일한 신호인 자리가 있다).
        full = store.get_run(r["id"], owner_sub=principal.subject) or {}
        bad = [s for s in (full.get("steps") or []) if s.get("ok") == 0 and s.get("error")]
        r["failed_at"] = ({"ix": bad[0]["ix"], "tool": bad[0]["tool"],
                           "error": str(bad[0]["error"])[:200]} if bad else None)
        codes: list[str] = []
        for st in full.get("steps") or []:
            for w in ((st.get("notes") or {}).get("warnings") or []):
                c = w.get("code") if isinstance(w, dict) else None
                if c and c not in codes:
                    codes.append(str(c))
        r["warnings"] = codes
    return {"batch_id": batch_id, "count": len(rows), "columns": cols, "runs": rows}


@router.post("/runs/{run_id}/steps/{ix}/ack", dependencies=[Depends(require_csrf)])
async def ack(request: Request, run_id: str, ix: int, body: AckIn,
              principal: Principal = Depends(_me)) -> dict:
    """게이트 확인 — 실행 소유자만, 그리고 **그 인자에 묶인다.**

    확인 뒤 인자가 바뀌면 무효다. 그래서 사람이 본 것과 실제로 나가는 것이 같다.
    """
    run = _owned(request, principal, run_id)
    steps = {s["ix"]: s for s in run["steps"]}
    if ix not in steps:
        raise AuthError("그 단계가 없습니다", status_code=404)
    if steps[ix]["args_sha256"] != body.args_sha256:
        raise AuthError("인자가 바뀌었습니다 — 다시 확인해 주세요", status_code=409)

    _store(request).ack_gate(run_id, ix, by=principal.subject,
                             args_sha256=body.args_sha256)
    version = _store(request).get_version(run["procedure_version_id"] or "")
    if version is None:
        return {"acked": True, "resumed": False}
    spec = ProcedureSpec.model_validate(version["spec"])
    _spawn(_runner(request).run(run_id=run_id, spec=spec, principal=principal, start_at=ix),
           f"resume {run_id}")
    return {"acked": True, "resumed": True}


@router.post("/runs/{run_id}/resume", dependencies=[Depends(require_csrf)])
async def resume(request: Request, run_id: str,
                 principal: Principal = Depends(_me)) -> dict:
    """실패·unknown 단계부터. **`done` 은 절대 재실행하지 않는다.**

    `unknown` 인 쓰기 단계는 사람이 확인한 뒤에만 돈다 — 실행 여부를 모르기 때문이다.
    """
    run = _owned(request, principal, run_id)
    version = _store(request).get_version(run["procedure_version_id"] or "")
    if version is None:
        raise AuthError("빈 실행은 재개하지 않습니다 — 단계를 다시 실행하세요", status_code=409)
    at = next((s["ix"] for s in run["steps"]
               if s["state"] in ("failed", "unknown", "pending")), len(run["steps"]))
    if at >= len(ProcedureSpec.model_validate(version["spec"]).steps):
        raise AuthError("재개할 단계가 없습니다", status_code=409)
    spec = ProcedureSpec.model_validate(version["spec"])
    _spawn(_runner(request).run(run_id=run_id, spec=spec, principal=principal, start_at=at),
           f"resume {run_id}")
    return {"resumed_at": at}


@router.post("/runs/{run_id}/cancel", dependencies=[Depends(require_csrf)])
def cancel(request: Request, run_id: str, principal: Principal = Depends(_me)) -> dict:
    """다음 단계 경계에서 반영된다. 진행 중 호출은 끝까지 간다.

    취소가 없으면 폭주하는 실행을 세우는 길이 포털 재기동뿐이고, 그 순간 챗 SSE 가 전부
    끊긴다 — "챗에 지장 없음" 이 실패 경로에서 깨진다.
    """
    store = _store(request)
    run = store.get_run(run_id)
    if run is None:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    if run["owner_sub"] != principal.subject and ADMIN_GROUP not in principal.groups:
        raise AuthError("실행을 찾을 수 없습니다", status_code=404)
    store.cancel_run(run_id, principal.subject)
    return {"cancelled": True}


class SaveAsIn(BaseModel):
    title: str
    vars: list[dict] = Field(default_factory=list)
    steps: list[dict] | None = None
    visibility: str = Field(default="all", pattern="^(all|private)$")


@router.get("/runs/{run_id}/draft")
async def run_draft(request: Request, run_id: str,
                    principal: Principal = Depends(_me)) -> dict:
    """이 실행을 **절차 초안**으로 펴 본다 — 그리고 안 펴지는 칸을 함께 낸다(PLAN §9-2).

    결손 찾기와 절차 도출은 두 일이 아니라 하나다. 펴 보면 안 펴지는 칸이 나오고 그게
    결손이다. 그래서 응답에 `spec` 과 `gaps` 가 같이 온다.

    ⚠ **저장하지 않는다.** 어느 인자가 변수이고 어느 것이 상수인지는 사람이 확정한다
    (PLAN §7 "자동 저장 금지"). `needs_human` 이 물어볼 자리다.
    """
    got, _, _ = await _draft_of(request, principal, run_id)
    return {"run_id": run_id, **got}


async def _draft_of(request: Request, principal: Principal,
                    run_id: str) -> tuple[dict, dict, dict]:
    """실행 → 초안 + 그때 쓴 도구 스키마·산문. `/draft` 와 `/draft/save` 가 **같은 것**을 쓴다."""
    from app.procedures import derive as _d

    store = _store(request)
    run = _owned(request, principal, run_id)
    steps = []
    for st in run["steps"]:
        steps.append({"tool": st["tool"],
                      "args": (st.get("args") or {}).get("_text") or st.get("args") or {},
                      "result": store.step_result(run_id, st["ix"])})
    # 챗 기록에는 **어느 앱인지 없다**(PLAN §9-8). 도구 지도로 채운다 — 못 채우면 결손이다.
    tmap, tschemas, tdesc = {}, {}, {}
    try:
        tmap = (await _tools_map(request)).get("map") or {}
    except Exception:  # noqa: BLE001 — 지도가 없어도 초안은 낸다(그 단계가 결손으로 잡힌다)
        logger.info("초안 — 도구 지도 조회 실패", exc_info=True)
    try:
        # 변수의 뜻은 **도구 스키마에서 온다** — 지어내지 않는다. 설명이 없는 인자는
        # 그 앱의 문서 결손으로 올라간다(PLAN §9-3 ①).
        cat = await _runner(request).catalog(principal)
        tschemas = {n: (m.get("inputSchema") or {}) for n, m in cat.items()}
        # 인자 설명이 거의 없어(1,348개 중 15개) 도구 **산문**에서 인용해야 한다
        tdesc = {n: str(m.get("description") or "") for n, m in cat.items()}
    except Exception:  # noqa: BLE001
        logger.info("초안 — 도구 스키마 조회 실패", exc_info=True)
    got = _d.draft(steps, tool_backend=tmap, asked=(run.get("title") or ""),
                   tool_schemas=tschemas, tool_desc=tdesc)
    got["input_schema"] = _d.to_input_schema(got["spec"])
    return got, tschemas, tdesc


@router.get("/procedures/{procedure_id}/tool")
def procedure_as_tool(request: Request, procedure_id: str,
                      principal: Principal = Depends(_me)) -> dict:
    """이 절차를 **도구 계약**으로 낸다 — 이름·설명·입력 스키마(PLAN §9).

    절차는 사실상 도구다. 계약을 도구와 같은 모양으로 내면 챗·심의가 절차를 부르는 것과
    도구를 부르는 것이 같아진다. 그 다리를 여기서 놓는다(등록은 아직 사람 손이다).
    """
    from app.procedures import derive as _d

    v = _store(request).latest_version_of(procedure_id)
    if v is None:
        raise AuthError("절차를 찾을 수 없습니다", status_code=404)
    spec = v["spec"]
    gates = [st.get("tool") for st in (spec.get("steps") or []) if st.get("gate") == "human"]
    return {
        "name": f"procedure_{procedure_id}",
        "title": spec.get("title") or "",
        "description": _tool_desc(spec, gates),
        "inputSchema": _d.to_input_schema(spec),
        "version_no": v.get("version_no"),
        # ⚠ 사람 확인이 걸린 단계는 **계약에 적는다.** 도구처럼 부르는 쪽이 이것을 모르면
        # "왜 안 끝나지" 가 된다 — 멈추는 것이 정상이라는 사실이 계약의 일부다.
        "human_gates": gates,
    }


def _tool_desc(spec: dict, gates: list) -> str:
    steps = spec.get("steps") or []
    lines = [spec.get("title") or "절차",
             f"단계 {len(steps)}개: " + " → ".join(str(st.get("tool")) for st in steps[:8])]
    if len(steps) > 8:
        lines[-1] += f" … 외 {len(steps) - 8}"
    if gates:
        lines.append(f"⚠ 사람 확인에서 멈춘다: {', '.join(map(str, gates))}")
    return "\n".join(lines)


@router.post("/runs/{run_id}/save-as-procedure", status_code=201,
             dependencies=[Depends(require_csrf)])
async def save_as_procedure(request: Request, run_id: str, body: SaveAsIn,
                   principal: Principal = Depends(_me)) -> dict:
    """실행에서 절차를 뽑는다 — **"하고 나서 저장" 이 성립하는 자리**다.

    어느 인자가 변수인지는 화면에서 사람이 표시하고, 여기는 그 결과를 받는다.
    """
    run = _owned(request, principal, run_id)
    steps = body.steps
    if steps is None:  # 표시 없이 저장하면 실행의 단계를 그대로 굳힌다
        steps = [{"backend": s["backend"], "tool": s["tool"], "args": s["args"],
                  "schema_fp": s["schema_fp"], "expect": s["expect"] or "fast"}
                 for s in run["steps"] if s["state"] == "done"]
    if not steps:
        raise AuthError("저장할 단계가 없습니다 — 성공한 단계가 하나도 없습니다",
                        status_code=422)
    spec = {"title": body.title, "vars": body.vars, "steps": steps}
    _, warns = await _validated(request, spec, principal)
    got = _store(request).create_procedure(
        owner_sub=principal.subject, spec=spec, title=body.title,
        visibility=body.visibility, derived_from_run=run_id)
    return {**got, "warnings": warns}


class DraftSaveIn(BaseModel):
    title: str
    # 어느 상수를 변수로 올릴지 — **사람이 고른 것만** 온다. [{step, arg, key?, label?, why?}]
    promote: list[dict] = Field(default_factory=list)
    visibility: str = Field(default="all", pattern="^(all|private)$")


@router.post("/runs/{run_id}/draft/save", status_code=201,
             dependencies=[Depends(require_csrf)])
async def save_draft(request: Request, run_id: str, body: DraftSaveIn,
                     principal: Principal = Depends(_me)) -> dict:
    """초안을 **사람이 확정해** 절차로 굳힌다(PLAN §9-2 고리의 마지막 칸).

    화면은 **결정만** 보낸다 — 어느 상수를 변수로 올릴지. 초안 자체는 여기서 다시 뽑는다.
    화면이 만든 spec 을 그대로 받으면 도출기가 낸 것과 다른 것이 저장될 수 있다.

    저장 검증은 **사람이 만든 절차와 똑같이** 탄다(`_validated`) — 도출이라고 우회하지 않는다.
    """
    from app.procedures import derive as _d

    spec_draft, tschemas, tdesc = await _draft_of(request, principal, run_id)
    spec, warns = _d.promote(spec_draft["spec"], body.promote, tool_schemas=tschemas,
                             tool_desc=tdesc)
    spec["title"] = body.title
    _, save_warns = await _validated(request, spec, principal)
    got = _store(request).create_procedure(
        owner_sub=principal.subject, spec=spec, title=body.title,
        visibility=body.visibility, derived_from_run=run_id)
    return {**got, "warnings": warns + save_warns}


@router.get("/procedures/{procedure_id}/export")
def export_procedure(request: Request, procedure_id: str, response: Response,
                     principal: Principal = Depends(_me)) -> Response:
    """절차를 **YAML 한 장**으로 뽑는다 — dev 에서 만들고 cae00 에서 쓰는 길(PLAN S1).

    두 박스는 망이 갈려 있어 DB 를 못 옮긴다. 옮기는 것은 **판본의 본문**뿐이고,
    실행 기록·소유자·id 는 안 옮긴다(그 사람 시야의 데이터이고 박스마다 다르다).

    받는 쪽은 `POST /procedures/import` 가 **사람이 만든 것과 똑같이** 검증한다 —
    내보낸 것이라고 통과시키지 않는다.
    """
    v = _store(request).latest_version_of(procedure_id)
    if v is None:
        raise AuthError("절차를 찾을 수 없습니다", status_code=404)
    spec = dict(v["spec"])
    head = (f"# 절차 내보내기 — {spec.get('title') or procedure_id}\n"
            f"# 판본 {v.get('version_no')} · {datetime.now(timezone.utc).date().isoformat()}\n"
            "#\n"
            "# 받는 쪽에서 `POST /procedures-api/procedures/import` 로 들인다.\n"
            "# ⚠ 실행 기록·소유자·id 는 **안 담겼다** — 본문만 옮긴다.\n"
            "# ⚠ 도구가 그 박스에 있는지는 들일 때 대조한다(없으면 경고로 말한다).\n")
    body = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, width=100)
    return Response(content=head + body, media_type="application/x-yaml",
                    headers={"Content-Disposition":
                             f'attachment; filename="procedure-{procedure_id}.yaml"'})


class ImportIn(BaseModel):
    yaml_text: str
    title: str | None = None
    visibility: str = Field(default="all", pattern="^(all|private)$")


@router.post("/procedures/import", status_code=201,
             dependencies=[Depends(require_csrf)])
async def import_procedure(request: Request, body: ImportIn,
                           principal: Principal = Depends(_me)) -> dict:
    """내보낸 YAML 을 들인다 — **사람이 만든 것과 똑같이** 검증한다."""
    try:
        raw = yaml.safe_load(body.yaml_text) or {}
    except yaml.YAMLError as exc:
        raise AuthError(f"YAML 이 아닙니다 — {str(exc)[:200]}", status_code=422) from None
    if not isinstance(raw, dict):
        raise AuthError("절차 본문이 아닙니다(맵이어야 합니다)", status_code=422)
    if body.title:
        raw["title"] = body.title
    spec, warns = await _validated(request, raw, principal)
    got = _store(request).create_procedure(
        owner_sub=principal.subject, spec=raw, title=spec.title,
        visibility=body.visibility)
    return {**got, "warnings": warns}


class GapDraftIn(BaseModel):
    run_id: str
    gap: dict                       # 초안이 낸 gaps[] 의 한 항목
    title: str | None = None
    owner_candidate: str | None = None


@router.post("/gaps/draft", dependencies=[Depends(require_csrf)])
def gap_draft(request: Request, body: GapDraftIn,
              principal: Principal = Depends(_me)) -> dict:
    """결손 하나를 **장부 파일 초안**으로 만든다(PLAN §9-6).

    ⚠ **파일을 쓰지 않는다.** YAML 텍스트를 돌려줄 뿐이고, 사람이 읽고 리포에 커밋한다.
    포털이 리포에 직접 쓰면 ① 검토 없이 결손이 늘고 ② 컨테이너가 리포를 쓰게 되며
    ③ 누가 등재했는지가 git 이 아니라 웹 세션에 남는다. 셋 다 싫다.

    §9-6 의 규율 그대로 — **근거 없는 등재 금지 · 자동 등재 금지 · 후보 소유자는 후보**.
    """
    _owned(request, principal, body.run_id)   # 남의 실행으로 결손을 만들 수 없다
    g = body.gap if isinstance(body.gap, dict) else {}
    kind = str(g.get("kind") or "unknown")
    slug = re.sub(r"[^a-z0-9]+", "-",
                  f"{g.get('tool') or kind}-{kind}".lower()).strip("-")[:60] or "gap"
    doc = {
        "id": slug,
        "title": body.title or str(g.get("why") or kind)[:120],
        "flow": "(어느 흐름에서 나왔는지 사람이 적는다)",
        "step": (f"{g.get('step')}단계 {g.get('tool') or ''}".strip()
                 if g.get("step") else "(어느 자리인지 사람이 적는다)"),
        "kind": _GAP_KIND.get(kind, 1),
        "owner_candidate": body.owner_candidate or "(사람이 확인한다)",
        "detected": {"by": "derive.draft", "kind": kind,
                     "why": str(g.get("why") or "")[:400],
                     **({"count": g["count"]} if isinstance(g.get("count"), int) else {}),
                     **({"where": g["where"][:12]} if isinstance(g.get("where"), list) else {})},
        "evidence": [f"실행 {body.run_id} 을 절차로 펴는 중에 드러났다"],
        "checked": ["⚠ 등재 전에 §9-3 순서를 밟을 것 — ② 숨어 있나(2단 도구) → "
                    "③ 안 이어지나 → ① 도구 없나 → ④ 재현 불가인가"],
        "status": "open",
        "confirmed_by": None,
    }
    head = ("# 결손 하나 = 파일 하나 (PLAN §9-6)\n"
            "# ⚠ 이것은 **초안**이다. 사람이 읽고 확인한 뒤 리포에 커밋한다.\n"
            f"#    두는 곳: docs/procedures/gaps/{slug}.yaml\n")
    return {"filename": f"{slug}.yaml",
            "yaml_text": head + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False,
                                               width=100)}


# 검출 종류 → §9-3 의 결손 종류. 모르는 것은 ①로 두고 사람이 고친다.
_GAP_KIND = {"backend_unknown": 1, "args_not_structured": 3, "args_undocumented": 1}


# ── 쓸모 판정(§6-1) ──────────────────────────────────────────────────────
@router.get("/stats")
def stats(request: Request, principal: Principal = Depends(_me)) -> dict:
    """§3 의 "쓸모가 증명되면 떼어낸다" 를 판정하는 네 수."""
    ensure(principal, ADMIN_GROUP)
    return _store(request).stats()


# ── 저장 전 검증만 (화면이 미리 부른다) ─────────────────────────────────
@router.post("/validate", dependencies=[Depends(require_csrf)])
async def validate(request: Request, body: ProcedureIn,
                   principal: Principal = Depends(_me)) -> dict:
    """거절 사유와 경고를 저장 **전에** 보여 준다. 스키마 대조는 게이트웨이가 붙었을 때만."""
    spec = ProcedureSpec.model_validate(body.spec)
    errs = validate_spec(
        spec, max_steps=int(getattr(get_settings(), "procedures_max_steps", 30)))
    schema_errs: list[str] = []
    try:
        runner = _runner(request)
        cat = await runner.catalog(principal)
        # 2단 도구는 **속 인자**까지 본다 — `run_operation(args=…)` 는 1단 스키마상 자유
        # object 라 오타가 그냥 통과한다(PLAN §9-4). 못 받아 오면 그 항목만 안 본다.
        second = await runner.second_stage(principal, spec)
        schema_errs = check_against_schemas(spec, cat, second)
    except Exception:  # noqa: BLE001 — 게이트웨이가 없어도 나머지 검증은 낸다
        logger.info("검증 중 도구 카탈로그 조회 실패", exc_info=True)
    return {
        "errors": [e for e in errs if not e.startswith("warn:")] + schema_errs,
        "warnings": [e[5:] for e in errs if e.startswith("warn:")],
    }
