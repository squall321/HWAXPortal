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
import re
from pathlib import Path

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


# ── 절차 ───────────────────────────────────────────────────────────────
class ProcedureIn(BaseModel):
    title: str
    spec: dict
    visibility: str = Field(default="all", pattern="^(all|private)$")
    derived_from_run: str | None = None


def _validated(request: Request, raw: dict) -> tuple[ProcedureSpec, list[str]]:
    spec = ProcedureSpec.model_validate(raw)
    errs = validate_spec(
        spec, max_steps=int(getattr(get_settings(), "procedures_max_steps", 30)))
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
def import_seed(request: Request, name: str,
                principal: Principal = Depends(_me)) -> dict:
    """씨앗을 내 절차로 들인다. 들어온 뒤에는 보통 절차와 똑같다(고치면 새 판본)."""
    raw = yaml.safe_load(_seed_path(name).read_text(encoding="utf-8")) or {}
    spec, warns = _validated(request, raw)
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
def create_procedure(request: Request, body: ProcedureIn,
                  principal: Principal = Depends(_me)) -> dict:
    _, warns = _validated(request, body.spec)
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
def add_version(request: Request, procedure_id: str, body: ProcedureIn,
                principal: Principal = Depends(_me)) -> dict:
    _, warns = _validated(request, body.spec)
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

    run_id = store.create_run(
        owner_sub=principal.subject, run_by=principal.subject,
        procedure_version_id=(version or {}).get("version_id"), inputs=inputs,
        origin="replay" if version else "manual", mode=body.mode, title=body.title)

    if spec is None:
        return {"run_id": run_id, "state": "queued", "empty": True}

    _spawn(runner.run(run_id=run_id, spec=spec, principal=principal), f"run {run_id}")
    return {"run_id": run_id, "state": "queued", "poll": f"/procedures-api/runs/{run_id}"}


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
    got, _ = await _draft_of(request, principal, run_id)
    return {"run_id": run_id, **got}


async def _draft_of(request: Request, principal: Principal, run_id: str) -> tuple[dict, dict]:
    """실행 → 초안 + 그때 쓴 도구 스키마. `/draft` 와 `/draft/save` 가 **같은 것**을 쓴다."""
    from app.procedures import derive as _d

    store = _store(request)
    run = _owned(request, principal, run_id)
    steps = []
    for st in run["steps"]:
        steps.append({"tool": st["tool"],
                      "args": (st.get("args") or {}).get("_text") or st.get("args") or {},
                      "result": store.step_result(run_id, st["ix"])})
    # 챗 기록에는 **어느 앱인지 없다**(PLAN §9-8). 도구 지도로 채운다 — 못 채우면 결손이다.
    tmap, tschemas = {}, {}
    try:
        tmap = (await _tools_map(request)).get("map") or {}
    except Exception:  # noqa: BLE001 — 지도가 없어도 초안은 낸다(그 단계가 결손으로 잡힌다)
        logger.info("초안 — 도구 지도 조회 실패", exc_info=True)
    try:
        # 변수의 뜻은 **도구 스키마에서 온다** — 지어내지 않는다. 설명이 없는 인자는
        # 그 앱의 문서 결손으로 올라간다(PLAN §9-3 ①).
        cat = await _runner(request).catalog(principal)
        tschemas = {n: (m.get("inputSchema") or {}) for n, m in cat.items()}
    except Exception:  # noqa: BLE001
        logger.info("초안 — 도구 스키마 조회 실패", exc_info=True)
    got = _d.draft(steps, tool_backend=tmap, asked=(run.get("title") or ""),
                   tool_schemas=tschemas)
    got["input_schema"] = _d.to_input_schema(got["spec"])
    return got, tschemas


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
def save_as_procedure(request: Request, run_id: str, body: SaveAsIn,
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
    _, warns = _validated(request, spec)
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

    spec_draft, tschemas = await _draft_of(request, principal, run_id)
    spec, warns = _d.promote(spec_draft["spec"], body.promote, tool_schemas=tschemas)
    spec["title"] = body.title
    _, save_warns = _validated(request, spec)
    got = _store(request).create_procedure(
        owner_sub=principal.subject, spec=spec, title=body.title,
        visibility=body.visibility, derived_from_run=run_id)
    return {**got, "warnings": warns + save_warns}


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
