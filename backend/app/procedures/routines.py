# 분석 루틴 스펙(RoutineSpec v1) — 단계마다 게이트웨이 백엔드(울타리) + 할 일, 저장 때 검증과 참조 치환(docs/analysis-routines/contracts.md §1)
"""루틴은 절차와 다른 종류다(AR-D1). 절차의 보증은 '저장 때 고정된 인자' 위에 서 있고, 루틴은 실행 때 LLM 이 단계의 울타리(백엔드) 안에서
도구와 인자를 고른다. 그래서 같은 저장소의 다른 표 · 다른 스펙이다. 변수(Var)와 쓰기 도구 분류(MUST_GATE · WARN · 게이트웨이 차단 접두)는
절차의 정본을 그대로 쓴다 — 두 곳에 목록을 두면 어긋난다.

저장 때 막는 것 — 꼴 · 길이 · 단계 id 고유 · `uses` 는 앞 단계만 · 참조가 풀린다 · 쓰기 도구 없음(v1, AR-D5) · 비밀 같은 글.
막지 않는 것 — 백엔드가 이 박스에 있나 · 이 사람이 부를 수 있나(실행 때 준비도가 단계 상태로 말한다 — cae00 에서 짠 루틴을 dev 로 가져올 수 있다).
"""
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.procedures.models import GW_DENY_PREFIX, GW_DENY_SUFFIX, MUST_GATE, WARN_EXACT, WARN_PREFIX, SpecError, Var, USERINFO_URL

CONTRACT = 1
RUN_STATES = ("queued", "running", "waiting", "done", "failed", "cancelled", "interrupted")
STAGE_STATES = ("pending", "running", "ok", "empty", "ambiguous", "denied", "not_connected", "unavailable", "failed",
                "skipped")
EXTRA_SECTIONS = ("insight", "cite")          # 단계 밖의 보고서 절 — 인사이트 · 인용

_STEP_ID = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
_BACKEND = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_TOOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
_KEY = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_REF = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")
# 비밀처럼 생긴 글 — 단계 할 일은 공유되는 자산이다(공개 범위 all). 토큰 · 비밀번호가 들면 그 글이 남의 화면 · LLM 에 실린다.
_SECRETISH = (USERINFO_URL, re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
              re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\."))


def is_write_tool(name: str) -> bool:
    """단계에 묶지 않는 도구 — 되돌리기 어렵거나 자원을 쓰는 것(절차 routes._writey 와 같은 분류 + 게이트웨이 차단 꼬리)."""
    return (name in MUST_GATE or name in WARN_EXACT or name.startswith(WARN_PREFIX)
            or name.startswith(GW_DENY_PREFIX) or name.endswith(GW_DENY_SUFFIX))


class Budget(BaseModel):
    model_config = {"extra": "forbid"}
    calls: int = Field(8, ge=1, le=30)
    seconds: int = Field(300, ge=30, le=1800)


class Blocked(BaseModel):
    """막힌 단계를 어떻게 하나 — 기본은 사유를 적고 건너뛴다(사용자 결정 Q2 · Q4). 기준 키 단계는 stop 으로 짠다.
    칸 이름이 `on` 이 아닌 까닭 — YAML 1.1(PyYAML)은 `on` 을 참으로 읽어, 손으로 쓴 YAML 의 `on:` 이 `True:` 가 된다."""
    model_config = {"extra": "forbid"}
    empty: Literal["continue", "stop"] = "continue"
    denied: Literal["skip", "stop"] = "skip"
    unavailable: Literal["skip", "stop"] = "skip"


class Expect(BaseModel):
    model_config = {"extra": "forbid"}
    keys: list[str] = Field(default_factory=list, max_length=8)
    fields: dict[str, Literal["string", "number", "list", "text"]] = Field(default_factory=dict, max_length=12)

    @field_validator("keys")
    @classmethod
    def _keys(cls, v: list[str]) -> list[str]:
        bad = [k for k in v if not _KEY.match(k)]
        if bad:
            raise ValueError(f"키 이름은 소문자 · 숫자 · 밑줄이다: {bad}")
        if len(set(v)) != len(v):
            raise ValueError("키 이름이 겹친다")
        return v


class DelibOpts(BaseModel):
    model_config = {"extra": "forbid"}
    job: str = Field("mechanism", pattern=r"^[a-z][a-z-]{0,31}$")
    chair_template: str | None = Field(None, max_length=64)


class Step(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    title: str = Field(min_length=1, max_length=80)
    kind: Literal["platform", "deliberation", "cite"] = "platform"
    backends: list[str] = Field(default_factory=list, max_length=3)
    label: str = Field("", max_length=80)            # 고를 때의 앱 라벨(보이기용 사본 — 울타리는 backends)
    goal: str = Field(min_length=1, max_length=2000)
    tools: list[str] = Field(default_factory=list, max_length=12)
    uses: list[str] = Field(default_factory=list, max_length=12)
    expect: Expect = Field(default_factory=Expect)
    budget: Budget = Field(default_factory=Budget)
    blocked: Blocked = Field(default_factory=Blocked)
    deliberation: DelibOpts | None = None

    @model_validator(mode="before")
    @classmethod
    def _yaml_on(cls, data):
        """손으로 쓴 YAML 의 `on:` 은 PyYAML 이 참(True) 키로 읽는다 — '키는 문자열이어야 한다' 대신 고칠 것을 말한다."""
        if isinstance(data, dict) and True in data:
            raise ValueError("`on:` 칸은 YAML 에서 참(True)으로 읽힌다 — 막혔을 때의 정책은 `blocked:` 에 적는다")
        return data

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not _STEP_ID.match(v) or v in EXTRA_SECTIONS:
            raise ValueError(f"단계 id 는 소문자로 시작하는 소문자 · 숫자 · 밑줄 24자까지다(insight · cite 는 예약): {v!r}")
        return v

    @model_validator(mode="after")
    def _kind(self):
        bad = [b for b in self.backends if not _BACKEND.match(b)]
        if bad:
            raise ValueError(f"{self.id}: 백엔드 키 꼴이 아니다 — {bad}")
        if self.kind in ("platform", "cite") and not self.backends:
            raise ValueError(f"{self.id}: 플랫폼 단계에는 백엔드(울타리)가 하나 이상 있어야 한다")
        if self.kind == "deliberation":
            if self.backends or self.tools:
                raise ValueError(f"{self.id}: 심의 단계는 백엔드 · 도구를 두지 않는다(심의 엔진을 부른다)")
            if self.deliberation is None:
                self.deliberation = DelibOpts()
        elif self.deliberation is not None:
            raise ValueError(f"{self.id}: deliberation 칸은 심의 단계에만 쓴다")
        bad = [t for t in self.tools if not _TOOL.match(t)]
        if bad:
            raise ValueError(f"{self.id}: 도구 이름 꼴이 아니다 — {bad}")
        writes = [t for t in self.tools if is_write_tool(t)]
        if writes:
            raise ValueError(f"{self.id}: 단계 안에서는 쓰지 않는다(v1) — 쓰기 도구 {writes} 를 빼라")
        if len(set(self.tools)) != len(self.tools) or len(set(self.backends)) != len(self.backends):
            raise ValueError(f"{self.id}: 도구 · 백엔드가 겹친다")
        return self


class RaOpts(BaseModel):
    model_config = {"extra": "forbid"}
    upload: Literal["auto", "ask", "off"] = "auto"      # 사용자 결정 Q1 — 저절로

    @field_validator("upload", mode="before")
    @classmethod
    def _yaml_off(cls, v):
        """YAML 1.1 은 `off` 를 거짓으로 읽는다 — 손으로 쓴 `upload: off` 를 그 뜻대로 받는다."""
        return "off" if v is False else v


class ReportSpec(BaseModel):
    model_config = {"extra": "forbid"}
    title: str = Field("", max_length=200)
    sections: list[str] = Field(default_factory=list, max_length=16)
    ra: RaOpts = Field(default_factory=RaOpts)


class Limits(BaseModel):
    model_config = {"extra": "forbid"}
    minutes: int = Field(60, ge=5, le=240)
    calls: int = Field(60, ge=1, le=200)


class RoutineSpec(BaseModel):
    model_config = {"extra": "forbid"}
    version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=120)
    purpose: str = Field("", max_length=2000)
    vars: list[Var] = Field(default_factory=list, max_length=12)
    steps: list[Step] = Field(min_length=1, max_length=12)
    report: ReportSpec = Field(default_factory=ReportSpec)
    limits: Limits = Field(default_factory=Limits)
    visibility: Literal["private", "all"] = "private"

    @model_validator(mode="after")
    def _whole(self):
        keys = [v.key for v in self.vars]
        if len(set(keys)) != len(keys):
            raise ValueError("변수 이름이 겹친다")
        ids = [s.id for s in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError(f"단계 id 가 겹친다: {sorted({i for i in ids if ids.count(i) > 1})}")
        expect = {s.id: set(s.expect.keys) for s in self.steps}
        for i, s in enumerate(self.steps):
            earlier = set(ids[:i])
            late = [u for u in s.uses if u not in earlier]
            if late:
                raise ValueError(f"{s.id}: uses 는 앞 단계만 가리킨다 — {late}")
            _check_refs(s.goal, f"{s.id}.goal", set(keys), {k: v for k, v in expect.items() if k in earlier})
        _check_refs(self.purpose, "purpose", set(keys), {})
        _check_refs(self.report.title, "report.title", set(keys), expect)
        allowed = set(ids) | set(EXTRA_SECTIONS)
        bad = [x for x in self.report.sections if x not in allowed]
        if bad:
            raise ValueError(f"report.sections 에 없는 절: {bad}(단계 id · insight · cite)")
        if len(set(self.report.sections)) != len(self.report.sections):
            raise ValueError("report.sections 가 겹친다")
        if not self.report.sections:
            self.report.sections = ids + ["insight"]
        for where, text in [("title", self.title), ("purpose", self.purpose), ("report.title", self.report.title)] + \
                [(f"{s.id}.goal", s.goal) for s in self.steps] + [(f"{s.id}.title", s.title) for s in self.steps]:
            if any(p.search(text or "") for p in _SECRETISH):
                raise ValueError(f"{where}: 비밀처럼 생긴 글이 있다(토큰 · 주소 안 비밀번호) — 루틴은 공유되는 자산이다")
        return self


def _check_refs(text: str, where: str, var_keys: set[str], step_keys: dict[str, set[str]]) -> None:
    for ref in refs_of(text):
        if ref in var_keys or ref == "run.started":
            continue
        parts = ref.split(".")
        if len(parts) == 3 and parts[0] == "steps":
            if parts[1] not in step_keys:
                raise ValueError(f"{where}: {{{{{ref}}}}} — 앞 단계가 아니다")
            if parts[2] not in step_keys[parts[1]]:
                raise ValueError(f"{where}: {{{{{ref}}}}} — 그 단계 expect.keys 에 {parts[2]!r} 가 없다")
            continue
        raise ValueError(f"{where}: {{{{{ref}}}}} 를 풀 수 없다(변수 · steps.<id>.<키> · run.started)")


def refs_of(text: str) -> list[str]:
    return [m.group(1) for m in _REF.finditer(text or "")]


def parse_spec(raw: dict) -> RoutineSpec:
    """저장 때 검증. 사람이 읽을 까닭 목록을 담은 SpecError 로 낸다(pydantic 의 loc · msg 만 — 입력 전문은 싣지 않는다)."""
    if not isinstance(raw, dict):
        raise SpecError("루틴 스펙은 객체여야 한다")
    try:
        return RoutineSpec.model_validate(raw)
    except ValidationError as exc:
        msgs = []
        for e in exc.errors()[:8]:
            loc = ".".join(str(x) for x in e.get("loc") or ())
            msg = str(e.get("msg") or "").removeprefix("Value error, ")
            msgs.append(f"{loc}: {msg}" if loc else msg)
        raise SpecError(" / ".join(msgs)) from None


def render(text: str, inputs: dict, keys: dict[str, dict[str, str]] | None = None, started: str = "") -> str:
    """참조를 값으로 — 변수 · 앞 단계 키 · 실행 시각. 값이 없으면 자리를 그대로 둔다(빈칸으로 지우면 할 일이 다른 뜻이 된다)."""
    keys = keys or {}

    def sub(m: re.Match) -> str:
        ref = m.group(1)
        if ref == "run.started":
            return started or m.group(0)
        parts = ref.split(".")
        if len(parts) == 3 and parts[0] == "steps":
            val = (keys.get(parts[1]) or {}).get(parts[2])
            return str(val) if val not in (None, "") else m.group(0)
        val = inputs.get(ref)
        return str(val) if val not in (None, "") else m.group(0)
    return _REF.sub(sub, text or "")
