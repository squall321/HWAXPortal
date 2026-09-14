"""절차·실행 모델의 **정본**. 저장 시점 검증이 전부 여기 있다(PLAN §2-1).

pydantic v2 — 포털 관례다(`jsonschema` 의존성이 리포에 없고, 새 pip 의존성 0 이 원칙이다).
docs/procedures/PLAN.md 의 YAML 은 예시이고 이 파일이 정본이다.

검증이 여기 있는 이유 — 이 스택의 반복 사고가 "실패가 정상 응답과 똑같이 생겼다" 이고,
그중 셋(enum 오타·단위·미지 인자)은 **저장 시점에만** 잡을 수 있다. 실행 시점에는 이미
다른 해석이 정상으로 돌고 난 뒤다.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.procedures import template

# ── 2026-09-14 게이트웨이 465종 전수에서 뽑은 목록 ────────────────────────
# ⚠ 손으로 고치지 마라. 게이트웨이가 바뀌면 다시 뽑는다(docs/procedures/PLAN.md §5-4).

# 되돌리려면 타인 승인이 필요한 바깥 방향 행위 — gate: human 이 없으면 저장 거절.
MUST_GATE = frozenset({
    "publish_report", "request_unpublish", "trash_report", "restore_version",
    "job_stop", "risk_add_finding", "add_report_tags",
})

# 자원을 쓰거나 잡을 만든다 — 거절이 아니라 경고. must-gate 로 하면 S5 일괄 재생이 죽는다.
WARN_PREFIX = ("submit_", "register_", "upload_", "ingest_")
WARN_EXACT = frozenset({"run_job", "train_model", "smarttwin_submit", "slurm_submit_job"})

# 게이트웨이 invoke_tool 이 막는 것(gateway.py:1100-1101). **백스톱일 뿐** 안전 목록이 아니다 —
# trash_report·job_stop 은 이 목록을 통과하고 앱 접두 이름(odb_delete_job)은 하나도 안 걸린다.
GW_DENY_PREFIX = ("delete_", "remove_", "cancel_", "purge_", "destroy_")
GW_DENY_SUFFIX = ("_control", "_set_state")

# 인자에 상수로 박히면 공유 절차가 곧 유출이다. 변수·앞 단계 save 만 허용한다.
SECRET_KEY = re.compile(r"token|secret|password|authorization|api_key|cookie", re.I)
USERINFO_URL = re.compile(r"://[^/\s:@]+:[^/\s@]+@")

# 이 키의 값은 기본을 변수로 올린다(상수로 두려면 사람이 확인).
PATHY_KEY = frozenset({"path", "local_path", "file_path", "url", "dest_path", "model_path"})

# 게이트웨이가 결과를 300초 캐시하는 접두사(gateway.py:144). 상태 조회 단계로 쓰면
# 낡은 '진행 중' 이 정상 응답처럼 온다.
CACHE_PREFIX = ("list_", "get_", "search_", "find_", "query_", "describe_", "hybrid_")

# 자기 dry_run 인자를 가진 도구(465종 중 16). 그 밖의 도구 args 에 dry_run 이 적혀 있으면
# 백엔드가 조용히 버리고 **실제로 실행된다**.
DRY_RUN_TOOLS = frozenset({
    "create_report_draft", "update_report_draft", "append_rows", "patch_cells", "remove_rows",
    "restore_version", "import_record", "slurm_node_set_state", "slurm_job_control",
    "smarttwin_submit", "slurm_submit_job", "heaxmaterialtwin_web_register_material",
    "register_tensile_test", "register_relaxation_test", "apply_naming_rules",
    "register_materials_csv",
})

_KEY = re.compile(r"^[a-z_][a-z0-9_]*$")
_TOOL = re.compile(r"^[a-z][a-z0-9_]*$")
_BACKEND = re.compile(r"^[a-z][a-z0-9_-]*$")


class SpecError(ValueError):
    """절차가 저장 시점 검증에 걸렸다."""


class Var(BaseModel):
    """과제마다 바뀌는 값. `why` 는 **왜 물어보는지** — 유도 불가한 값에 필수다."""
    model_config = {"extra": "forbid"}

    key: str
    label: str
    type: Literal["string", "enum", "number", "boolean", "json"] = "string"
    values: list[str] | None = None
    required: bool = True
    why: str | None = None

    @field_validator("key")
    @classmethod
    def _key(cls, v: str) -> str:
        if not _KEY.match(v):
            raise ValueError(f"변수 이름은 소문자·숫자·밑줄이다: {v!r}")
        if v.startswith("me.") or v in {"run_id", "me"}:
            raise ValueError(f"예약 변수와 겹친다: {v!r}")
        return v

    @model_validator(mode="after")
    def _enum(self):
        if self.type == "enum" and not self.values:
            raise ValueError(f"enum 변수 {self.key} 에 values 가 없다")
        if self.type != "enum" and self.values:
            raise ValueError(f"{self.key}: values 는 enum 에만 쓴다")
        return self

    def coerce(self, raw: Any) -> Any:
        """사람이 넣은 값을 선언한 형으로 맞춘다. 못 맞추면 SpecError."""
        if self.type == "enum":
            if raw not in (self.values or []):
                raise SpecError(f"{self.key}: {raw!r} 은 허용값이 아니다 {self.values}")
            return raw
        if self.type == "number":
            try:
                return float(raw) if not isinstance(raw, bool) else _bad(self.key, raw)
            except (TypeError, ValueError):
                raise SpecError(f"{self.key}: 수치가 아니다 — {raw!r}") from None
        if self.type == "boolean":
            if isinstance(raw, bool):
                return raw
            raise SpecError(f"{self.key}: 참·거짓이 아니다 — {raw!r}")
        if self.type == "string":
            if isinstance(raw, str):
                return raw
            raise SpecError(f"{self.key}: 문자열이 아니다 — {type(raw).__name__}")
        return raw  # json — 무엇이든


def _bad(key, raw):
    raise SpecError(f"{key}: 수치가 아니다 — {raw!r}")


class Step(BaseModel):
    """한 단계. 노출 이름이 아니라 `backend` + 원본 `tool` 로 저장한다(PLAN §5-8).

    `expect` 는 예상 소요다 — `job`(120초를 넘길 수 있다)은 저장 거절이고 제출·회수 두
    절차로 갈라야 한다(PLAN §5-10).
    """
    model_config = {"extra": "forbid"}

    backend: str
    tool: str
    schema_fp: str | None = None
    expect: Literal["fast", "slow", "job"] = "fast"
    args: dict[str, Any] = Field(default_factory=dict)
    save: dict[str, str] | None = None
    gate: Literal["human"] | None = None
    raw: bool = False          # 결과가 JSON 이 아니다(텍스트 카탈로그 등)
    unwrap: str | None = None  # SmartTwin 류 이중 포장 — 그 필드를 한 번 더 파싱
    warmup: bool = False       # 한 번 먼저 부르고 버린다. 타임아웃이 나도 실패로 안 친다
    note: str | None = None

    @field_validator("backend")
    @classmethod
    def _be(cls, v: str) -> str:
        if not _BACKEND.match(v):
            raise ValueError(f"백엔드 키 모양이 아니다: {v!r}")
        return v

    @field_validator("tool")
    @classmethod
    def _tool(cls, v: str) -> str:
        if not _TOOL.match(v):
            raise ValueError(f"도구 이름 모양이 아니다: {v!r}")
        return v

    @property
    def alias(self) -> str:
        """게이트웨이에서 **항상** 호출되는 별칭. 노출 이름은 다른 앱 때문에 뒤집힌다."""
        return f"{self.backend.replace('-', '')}_{self.tool}"

    @property
    def cacheable(self) -> bool:
        return self.tool.startswith(CACHE_PREFIX)


class ProcedureSpec(BaseModel):
    """절차 판본의 불변 본문. 이것이 바뀔 때만 새 판본이 생긴다."""
    model_config = {"extra": "forbid"}

    title: str
    vars: list[Var] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_vars(self):
        seen = set()
        for v in self.vars:
            if v.key in seen:
                raise ValueError(f"변수 이름이 겹친다: {v.key}")
            seen.add(v.key)
        return self


# ── 저장 시점 검증 ────────────────────────────────────────────────────────

RESERVED = frozenset({"run_id"})  # me.email·me.sub 은 접두로 따로 본다


def validate_spec(spec: ProcedureSpec, *, max_steps: int = 30) -> list[str]:
    """절차를 저장해도 되는지 본다. 문제를 **전부** 모아 돌려준다(첫 건에서 멈추지 않는다).

    빈 리스트면 통과. 경고는 `warn:` 접두로 온다 — 거절이 아니라 화면에 띄울 것.
    """
    errs: list[str] = []
    if not spec.steps:
        errs.append("단계가 하나도 없다")
    if len(spec.steps) > max_steps:
        errs.append(f"단계가 {len(spec.steps)}개다 — 상한 {max_steps}")

    declared = {v.key for v in spec.vars}
    produced: set[str] = set()

    for i, st in enumerate(spec.steps, 1):
        at = f"{i}단계 {st.tool}"

        # ① 사람 자리 — 작성자가 끌 수 없다
        if st.tool in MUST_GATE and st.gate != "human":
            errs.append(f"{at}: 되돌리기 어려운 도구라 gate: human 이 필수다")
        if st.tool in WARN_EXACT or st.tool.startswith(WARN_PREFIX):
            if st.gate != "human":
                errs.append(f"warn:{at}: 자원을 쓰거나 잡을 만든다 — 게이트를 권한다")

        # ② 게이트웨이 백스톱에 걸리는 이름은 애초에 못 부른다
        if st.tool.startswith(GW_DENY_PREFIX) or st.tool.endswith(GW_DENY_SUFFIX):
            errs.append(f"{at}: invoke_tool 이 막는 이름이라 실행되지 않는다")

        # ③ 시간 — job 은 제출·회수로 갈라야 한다
        if st.expect == "job":
            errs.append(f"{at}: expect=job — 120초를 넘길 수 있다. 제출·회수 두 절차로 가른다")
        if st.expect == "slow" and st.cacheable:
            errs.append(f"warn:{at}: 느린 읽기 도구다 — 재실행은 300초 캐시가 받는다")

        # ④ dry_run — 스키마에 없는 도구에 얹으면 조용히 진짜 실행된다
        if "dry_run" in st.args and st.tool not in DRY_RUN_TOOLS:
            errs.append(f"{at}: 이 도구에는 dry_run 인자가 없다 — 백엔드가 버리고 실제로 실행한다")

        # ⑤ 비밀·경로가 상수로 박히면 공유 절차가 곧 유출이다
        errs += _scan_args(st.args, at)

        # ⑥ 치환 — 참조하는 변수가 앞에서 나왔나
        for name in template.refs(st.args):
            root = name.split(".")[0]
            if root == "me" or name in RESERVED:
                continue
            if name not in declared and name not in produced:
                errs.append(f"{at}: {{{{{name}}}}} 을 어디서도 안 만든다")

        # ⑦ 추출 — 토큰을 save 로 넘겨 2단 확인을 우회하지 않는다
        for key, path in (st.save or {}).items():
            if not _KEY.match(key):
                errs.append(f"{at}: save 이름이 소문자·숫자·밑줄이 아니다 — {key!r}")
            if SECRET_KEY.search(key) or SECRET_KEY.search(path):
                errs.append(f"{at}: save 로 토큰을 넘길 수 없다 — {key} (2단 확인 우회)")
            if key in declared:
                errs.append(f"{at}: save 이름이 변수와 겹친다 — {key}")
            produced.add(key)
        if st.save and st.raw:
            errs.append(f"{at}: raw 단계는 JSON 이 아니라 save 로 못 뽑는다")

    unused = declared - _all_refs(spec)
    for k in sorted(unused):
        errs.append(f"warn:변수 {k} 를 아무 단계도 안 쓴다")
    return errs


def _all_refs(spec: ProcedureSpec) -> set[str]:
    out: set[str] = set()
    for st in spec.steps:
        out |= {r.split(".")[0] for r in template.refs(st.args)}
    return out


def _scan_args(args: Any, at: str, trail: str = "") -> list[str]:
    errs: list[str] = []
    if isinstance(args, dict):
        for k, v in args.items():
            here = f"{trail}.{k}" if trail else k
            literal = isinstance(v, str) and "{{" not in v
            if SECRET_KEY.search(k) and literal and v:
                errs.append(f"{at}: 비밀로 보이는 인자를 상수로 저장할 수 없다 — {here}")
            elif k in PATHY_KEY and literal and v:
                errs.append(f"warn:{at}: 경로·URL 이 상수로 박힌다 — {here}")
            if literal and USERINFO_URL.search(v):
                errs.append(f"{at}: URL 에 계정·비밀번호가 들어 있다 — {here}")
            errs += _scan_args(v, at, here)
    elif isinstance(args, list):
        for i, v in enumerate(args):
            errs += _scan_args(v, at, f"{trail}[{i}]")
    return errs


def check_against_schemas(spec: ProcedureSpec, schemas: dict[str, dict]) -> list[str]:
    """게이트웨이 `tools/list` 스키마와 대조한다 — 호출 시점에 받아 따로 돈다.

    게이트웨이는 `validate_input=False`(gateway.py:1766) 라 인자를 검증하지 않고, 백엔드는
    모르는 최상위 키를 조용히 버린다. 오타 인자가 정상 응답으로 돌아오는 자리다.
    """
    errs: list[str] = []
    for i, st in enumerate(spec.steps, 1):
        at = f"{i}단계 {st.tool}"
        sch = schemas.get(st.alias) or schemas.get(st.tool)
        if sch is None:
            errs.append(f"{at}: 게이트웨이에 이 도구가 없다 ({st.alias})")
            continue
        props = (sch.get("properties") or {}).keys()
        req = sch.get("required") or []
        if props:
            for k in st.args:
                if k not in props:
                    errs.append(f"{at}: 스키마에 없는 인자 — {k} (백엔드가 조용히 버린다)")
        for k in req:
            if k not in st.args:
                errs.append(f"{at}: 필수 인자가 빠졌다 — {k}")
    return errs


def schema_fingerprint(description: str, input_schema: dict) -> str:
    """도구 판본이 없으니 **변화를 잡아 멈추는 것까지** 한다(PLAN §5-8).

    게이트웨이 내부 `_tools_fp`(gateway.py:162-172)와 같은 식이라, 나중에 게이트웨이가
    지문을 노출하면 그대로 대조된다.
    """
    import hashlib
    import json

    blob = (description or "") + "\x00" + json.dumps(input_schema or {}, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]
