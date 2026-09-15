# 2단 도구 — 역량이 도구 하나 뒤에 숨어 있는 자리를 절차가 단계로 쓰게 한다(PLAN §9-4·§9-5)
#
# 문제. DynaForge 는 연산 47개를 들고 있는데 게이트웨이에는 `run_operation` 하나로 보인다.
# 절차는 도구 단위라 `matdb`(물성 교체)를 단계로 적을 수가 없고, 적더라도 `args` 가 자유
# JSON 이라 **오타가 실행 시점에야 터진다** — 이 리포가 반복해서 만나는 모양이다.
#
# 그런데 계약은 있다. `describe_operation("matdb")` 가 JSON Schema 를 준다. 이 모듈은
# 그 두 번째 단을 어디서 받아 오는지를 **등록부(데이터)** 에서 읽고, 형식 차이를 어댑터로
# 흡수해 절차의 저장 시점 검증에 넘긴다.
#
# ⚠ 등록부는 사람이 확정한 것만 담는다. 검출기는 후보를 밀 뿐 등재하지 않는다.
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.config import BACKEND_DIR

REGISTRY_PATH = Path(BACKEND_DIR).parent / "docs" / "procedures" / "dispatchers.yaml"


class Dispatcher:
    """도구 하나 뒤에 여러 역량이 있는 자리."""

    __slots__ = ("backend", "tool", "selector", "payload", "list_tool",
                 "describe", "describe_arg", "schema_kind", "schema_at", "note",
                 "detector_finds")

    def __init__(self, raw: dict):
        self.backend: str = raw["backend"]
        self.tool: str = raw["tool"]
        self.selector: str = raw["selector"]
        self.payload: str = raw["payload"]
        self.list_tool: str | None = raw.get("list")
        self.describe: str = raw["describe"]
        self.describe_arg: str = raw.get("describe_arg") or raw["selector"]
        self.schema_kind: str = raw.get("schema_kind") or "json_schema"
        self.schema_at: str = raw.get("schema_at") or ""
        self.note: str = raw.get("note") or ""
        # 검출기가 이 항목을 후보로 밀 수 있나. 못 미는 것은 **데이터로 적는다** —
        # 이름 규칙을 늘려 맞추면 그게 이 프로젝트가 피하려는 하드코딩이다.
        self.detector_finds: bool = raw.get("detector_finds", True)

    @property
    def key(self) -> tuple[str, str]:
        return (self.backend, self.tool)

    def __repr__(self) -> str:  # 진단용
        return f"<Dispatcher {self.backend}/{self.tool} by {self.selector}>"


def load(path: Path | None = None) -> dict[tuple[str, str], Dispatcher]:
    """등록부를 읽는다. 없으면 빈 것 — 2단 지원이 없을 뿐 절차는 그대로 돈다."""
    p = path or REGISTRY_PATH
    if not p.is_file():
        return {}
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: dict[tuple[str, str], Dispatcher] = {}
    for item in raw.get("dispatchers") or []:
        d = Dispatcher(item)
        if d.key in out:
            raise ValueError(f"등록부에 같은 도구가 두 번 있다: {d.key}")
        out[d.key] = d
    return out


def selected(step_args: dict, d: Dispatcher) -> str | None:
    """이 단계가 그 도구 뒤의 **무엇을** 부르는가. 변수면 None(저장 시점엔 모른다)."""
    v = step_args.get(d.selector)
    return v if isinstance(v, str) and "{{" not in v else None


# ── 두 번째 단의 형식 흡수 ────────────────────────────────────────────────
def to_json_schema(body: Any, d: Dispatcher, *, item: str) -> dict | None:
    """describe 응답 → JSON Schema. 못 옮기면 None(모른다고 말한다, 지어내지 않는다)."""
    if not isinstance(body, dict):
        return None
    if d.schema_kind == "json_schema":
        got = _dig(body, d.schema_at)
        return got if isinstance(got, dict) and got.get("properties") is not None else None
    if d.schema_kind == "params_ko":
        return _params_ko(body, d, item)
    return None


def _dig(body: dict, path: str) -> Any:
    cur: Any = body
    for part in (path or "").split("."):
        if not part:
            continue
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


# StepForge `job_params_guide` 모양 — {jobs: {kind: {name: {type, default, 설명}}}}
_KO_TYPES = {"str": "string", "int": "integer", "float": "number",
             "bool": "boolean", "list": "array", "dict": "object"}


def _params_ko(body: dict, d: Dispatcher, item: str) -> dict | None:
    jobs = _dig(body, d.schema_at)
    if not isinstance(jobs, dict):
        return None
    spec = jobs.get(item)
    if not isinstance(spec, dict):
        return None
    props: dict[str, dict] = {}
    for name, meta in spec.items():
        if not isinstance(meta, dict):
            continue
        p: dict[str, Any] = {"type": _KO_TYPES.get(str(meta.get("type") or ""), "string")}
        if meta.get("설명"):
            p["description"] = str(meta["설명"])
        if meta.get("default") is not None:
            p["default"] = meta["default"]
        props[name] = p
    if not props:
        return None
    # ⚠ **닫지 않는다.** 이 앱이 모르는 키를 거절하는 것은 맞지만, 앱이 받는 키는
    # 이 표보다 **넓다** — 공차 키는 `jobs` 밖의 딴 칸에 있고 특정 종류만 받으며,
    # `pipeline` 은 중첩 블록도 받는다. 실측(2026-09-15): `mesh` + `clearance_gap` 은
    # StepForge 가 통과시키는데 우리가 닫아 두면 **저장 시점에 거절한다** — 모르는 것을
    # 틀렸다고 말하는 꼴이고, 이 리포가 반복해서 고쳐 온 바로 그 오류다.
    # 아는 키의 형은 여전히 본다. 모르는 키는 앱이 거절하며 쓸 수 있는 목록까지 알려 준다.
    return {"type": "object", "properties": props}


# ── 검출 — 후보를 밀 뿐 등재하지 않는다 ──────────────────────────────────
def detect_candidates(catalog: dict[str, dict]) -> list[dict]:
    """카탈로그에서 2단으로 보이는 도구를 민다.

    신호는 **이름이 아니라 스키마 모양**이다(§9-7 — 이름 분류는 466개 중 113개를 못 갈랐다).
      · 인자가 적고
      · 그중 하나가 무엇을 고르는 문자열이고
      · 다른 하나가 **속성 없는 object**(자유 페이로드)다
    그리고 같은 카탈로그에 `describe`·`list` 로 보이는 짝이 있다.

    ⚠ 이것은 **후보**다. 등재는 사람이 한다 — 잘못 등재하면 엉뚱한 인자를 검증한다.
    """
    names = set(catalog)
    out: list[dict] = []
    for name, meta in catalog.items():
        schema = (meta or {}).get("inputSchema") or {}
        props = schema.get("properties") or {}
        if not 1 < len(props) <= 4:
            continue
        free = [k for k, v in props.items() if _is_free_object(v)]
        picks = [k for k, v in props.items() if _is_plain_string(v)]
        if not free or not picks:
            continue
        mate = _mate(name, names)
        if not mate:
            continue
        out.append({"tool": name, "selector": picks[0], "payload": free[0], **mate})
    return sorted(out, key=lambda x: x["tool"])


def _is_free_object(v: Any) -> bool:
    return (isinstance(v, dict) and v.get("type") == "object"
            and not (v.get("properties") or {}))


def _is_plain_string(v: Any) -> bool:
    return isinstance(v, dict) and v.get("type") == "string" and not v.get("enum")


# 부르는 동사·설명하는 동사·목록 동사. **접두와 접미 둘 다** 본다 —
# `run_operation`/`describe_operation` 도 있고 `catalog_run`/`catalog_describe` 도 있다.
# ⚠ 처음엔 접두만 봐서 **확정 등재된 `catalog_run` 을 못 찾았다**(2026-09-15 점검에서 잡힘).
_RUN_V = ("run", "submit", "execute")
_DESC_V = ("describe", "spec", "schema", "params")
_LIST_V = ("list", "search", "catalog", "index")


def _mate(name: str, names: set[str]) -> dict | None:
    """그 도구의 짝(설명·목록)을 찾는다. 없으면 후보가 아니다.

    ⚠ **이름 규칙이라 놓치는 게 있다.** 여기서 못 찾는다고 2단이 아닌 게 아니다 —
    검출기는 **후보를 미는 것**이고, 등재는 사람이 한다(§9-5). 실제로 이 함수는
    `slurm_submit_job`/`slurm_list_templates` 처럼 어간이 다른 짝은 못 잡는다.
    """
    for stem, verb in _stems(name, _RUN_V):
        for d in _cands(stem, _DESC_V):
            if d in names and d != name:
                out = {"describe": d}
                for lst in _cands(stem, _LIST_V):
                    if lst in names and lst != name:
                        out["list"] = lst
                        break
                return out
    return None


def _stems(name: str, verbs: tuple) -> list[tuple[str, str]]:
    """`run_operation` → ("operation", 접두) · `catalog_run` → ("catalog", 접미)."""
    out = []
    for v in verbs:
        if name.startswith(v + "_"):
            out.append((name[len(v) + 1:], "prefix"))
        if name.endswith("_" + v):
            out.append((name[: -(len(v) + 1)], "suffix"))
    return out


def _cands(stem: str, verbs: tuple) -> list[str]:
    """어간 하나에서 나올 수 있는 짝 이름들(단수·복수 · 접두·접미)."""
    bases = {stem, stem.rstrip("s"), stem + "s"}
    return [f"{v}_{b}" for b in bases for v in verbs] + \
           [f"{b}_{v}" for b in bases for v in verbs]
