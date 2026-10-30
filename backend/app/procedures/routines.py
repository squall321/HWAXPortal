# 분석 루틴 스펙(RoutineSpec v1) — 단계마다 게이트웨이 백엔드(울타리) + 할 일, 저장 때 검증과 참조 치환(docs/analysis-routines/contracts.md §1)
"""루틴은 절차와 다른 종류다(AR-D1). 절차의 보증은 '저장 때 고정된 인자' 위에 서 있고, 루틴은 실행 때 LLM 이 단계의 울타리(백엔드) 안에서
도구와 인자를 고른다. 그래서 같은 저장소의 다른 표 · 다른 스펙이다. 변수(Var)와 쓰기 도구 분류(MUST_GATE · WARN · 게이트웨이 차단 접두)는
절차의 정본을 그대로 쓴다 — 두 곳에 목록을 두면 어긋난다.

저장 때 막는 것 — 꼴 · 길이 · 단계 id 고유 · `uses` 는 앞 단계만 · 참조가 풀린다 · 쓰기 도구 없음(v1, AR-D5) · 비밀 같은 글.
막지 않는 것 — 백엔드가 이 박스에 있나 · 이 사람이 부를 수 있나(실행 때 준비도가 단계 상태로 말한다 — cae00 에서 짠 루틴을 dev 로 가져올 수 있다).
"""
import json
import re
from datetime import datetime, timedelta, timezone
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


KST = timezone(timedelta(hours=9), "KST")      # 한국은 일광 절약 시간이 없다 — 고정 오프셋이면 tzdata 없이도 같다


def started_kst(ts: int | None) -> str:
    """`{{run.started}}` 의 값 — 실행 시작 시각(KST 'YYYY-MM-DD HH:MM'). 시각이 없으면 빈 글이다(render 가 자리를 그대로 둔다)."""
    return datetime.fromtimestamp(int(ts), tz=KST).strftime("%Y-%m-%d %H:%M") if ts else ""


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


# ── 실행(R2) — 단계 봉투 · 계획 · 보고서 ─────────────────────────────────────────────────────────────────────────────
DELIB_BACKEND = "hwax-deliberation"
DELIB_TOOLS = ("deliberate_start", "deliberate_status", "deliberate_result")
EXECUTORS = ("mcp", "chat", "web")
CLOSED = ("ok", "empty", "denied", "not_connected", "unavailable", "failed", "skipped")
STATE_LABEL = {"pending": "아직", "running": "도는 중", "ok": "끝남", "empty": "결과 없음", "ambiguous": "고를 것 있음",
               "denied": "권한 없음", "not_connected": "토큰 없음", "unavailable": "이 박스에 없음", "failed": "실패",
               "skipped": "건너뜀"}
RA_ITEM_MAX = 1900                     # 에이전트 서버 _RA_ITEM_MAX 와 같다(서버 상한 2,000 에 여유) — 계약 시험이 맞댄다
_RA_SPLIT_RE = re.compile(r"(?<=[.!?。])\s+|\n")
_CALL_REF = re.compile(r"\[([a-z][a-z0-9_]{0,23}\.c\d+)\]")


class Finding(BaseModel):
    model_config = {"extra": "forbid"}
    text: str = Field(min_length=1, max_length=500)
    refs: list[str] = Field(default_factory=list, max_length=10)


class Candidate(BaseModel):
    model_config = {"extra": "forbid"}
    label: str = Field(min_length=1, max_length=200)
    key: str = Field(min_length=1, max_length=200)


class Envelope(BaseModel):
    """실행자가 단계를 닫으며 보내는 것(contracts.md §2). 상태는 포털이 원장과 맞대 고친다."""
    model_config = {"extra": "forbid"}
    status: Literal["ok", "empty", "ambiguous", "denied", "not_connected", "unavailable", "failed", "skipped"]
    reason: str = Field("", max_length=500)
    summary: str = Field("", max_length=6000)
    keys: dict[str, str] = Field(default_factory=dict, max_length=16)
    findings: list[Finding] = Field(default_factory=list, max_length=20)
    candidates: list[Candidate] = Field(default_factory=list, max_length=20)

    @field_validator("keys", mode="before")
    @classmethod
    def _keys(cls, v):
        if not isinstance(v, dict):
            return v
        return {str(k)[:32]: (v2 if isinstance(v2, str) else str(v2))[:200] for k, v2 in v.items() if v2 is not None}


def _gw_write(meta) -> bool:
    """게이트웨이가 쓰기로 분류한 도구인가(_catalog 가 /tools-map 의 write 로 단 표지). 표지가 None(옛 게이트웨이 — 모름)이면 아니다."""
    return isinstance(meta, dict) and meta.get("write") is True


def _gw_read(meta) -> bool:
    """게이트웨이가 읽기로 확인한 도구인가(_catalog 가 /tools-map 의 routine_read 로 단 표지 read). 모르면 아니다(C-12)."""
    return isinstance(meta, dict) and meta.get("read") is True


def _read_mode(s: Step, mine: dict[str, dict]) -> bool:
    """이 단계 백엔드의 내 도구에 읽기 표지(read)가 달렸나 — 게이트웨이가 routine_read 를 주면 _catalog 가 모든 도구에 참 · 거짓을 단다.
    달렸으면 '읽기로 확인된 것만' 판정이고, 없으면(routine_read 를 안 주는 옛 게이트웨이) 종전 판정(write · 이름 꼴)이다."""
    return any(isinstance(m, dict) and m.get("read") is not None for b in s.backends for m in (mine.get(b) or {}).values())


def allowed_tools(s: Step, mine: dict[str, dict]) -> tuple[dict[str, list[str]], list[str]]:
    """플랫폼 · 인용 단계의 허용 도구 {백엔드: [원래 이름]}와 뺀 적은 도구('백엔드:이름') — 계획(plan_steps)과 준비도(readiness_of)가 같은
    판정을 쓴다. 게이트웨이가 읽기 목록(/tools-map 의 routine_read)을 주면 **읽기로 확인된 것만** 묶는다(R3 반대 검토 C-12 — 이름 동사 규칙은
    risk_job_action · single_drop_simulation 같은 쓰기를 '쓰기 아님' 으로 통과시켰다): (적은 도구, 안 적었으면 내 도구 전부) ∩ 내 목록 ∩ 읽기 목록
    − 이름 꼴(is_write_tool), 적은 도구 가운데 이 판정으로 빠진 것은 뺀 목록에. 읽기 목록이 없으면(옛 게이트웨이) 종전대로(R3-D6) — 도구를 적었으면
    그 가운데 내 목록에 있고 게이트웨이 쓰기가 아닌 것, 안 적었으면 그 백엔드의 도구에서 이름 꼴(is_write_tool)과 게이트웨이 쓰기를 뺀 것."""
    allowed: dict[str, list[str]] = {}
    dropped: list[str] = []
    read = _read_mode(s, mine)
    for b in s.backends:
        have = mine.get(b) or {}
        if read:
            picked = [t for t in s.tools if t in have] if s.tools else sorted(have)
            allowed[b] = [t for t in picked if _gw_read(have[t]) and not is_write_tool(t)]
            if s.tools:
                dropped += [f"{b}:{t}" for t in picked if t not in allowed[b]]
        elif s.tools:
            picked = [t for t in s.tools if t in have]
            dropped += [f"{b}:{t}" for t in picked if _gw_write(have[t])]
            allowed[b] = [t for t in picked if not _gw_write(have[t])]
        else:
            allowed[b] = sorted(t for t in have if not is_write_tool(t) and not _gw_write(have[t]))
    return allowed, dropped


_READ_HINT = "단계 안에서는 읽기로 확인된 도구만 v1 · 읽기 도구라면 앱이 readOnlyHint 를 달거나 박스의 read_tools.local.json 에 더한다"


def write_reason(s: Step, allowed: dict[str, list[str]], dropped: list[str], mine: dict[str, dict] | None = None) -> str:
    """뺀 것의 준비도 까닭 — 뺀 것이 없으면 빈 글. 빼서 단계가 비었으면 그 단계는 이 까닭으로 '이 박스에 없음' 이다('목록에 없다' 가
    아니다 — first_states · readiness_of). 부르는 쪽은 준비도가 allowed 일 때만 쓴다(그 백엔드가 내 목록에 있어야 '모두 쓰기' 가 참이다).
    `mine` 이 읽기 표지를 달았으면(읽기 목록 판정) '읽기로 확인되지 않았다' 로 말한다 — 모르는 도구도 빠지므로 '쓰기로 분류' 는 틀린 말이다."""
    if mine is not None and _read_mode(s, mine):
        if dropped and any(allowed.values()):
            return f"고른 도구 가운데 {', '.join(dropped)} 는 읽기로 확인되지 않았다 — 빼고 남은 도구로 돈다({_READ_HINT})"
        if dropped:
            return f"고른 도구가 읽기로 확인되지 않았다 — {', '.join(dropped)} 를 뺐다({_READ_HINT})"
        if not s.tools and not any(allowed.values()):
            return f"이 플랫폼에서 부를 수 있는 도구가 하나도 읽기로 확인되지 않았다({_READ_HINT})"
        return ""
    if dropped and any(allowed.values()):
        return f"고른 도구 가운데 쓰기로 분류된 것은 뺐다(단계 안 쓰기 금지 v1) — {', '.join(dropped)} · 남은 도구로 돈다"
    if dropped:
        return f"고른 도구가 쓰기로 분류돼 뺐다(단계 안 쓰기 금지 v1) — {', '.join(dropped)}"
    if not s.tools and not any(allowed.values()):
        return "이 플랫폼에서 부를 수 있는 도구가 모두 쓰기로 분류된다 — 단계에는 읽기 도구만 묶는다(단계 안 쓰기 금지 v1)"
    return ""


def plan_steps(spec: RoutineSpec, mine: dict[str, dict], readiness: list[dict]) -> list[dict]:
    """실행 계획의 단계 — 울타리(backends)와 허용 도구 {백엔드: [원래 이름]}. 허용 도구는 이 사람의 도구 목록에서 고른다 — 단계가 도구를 적었으면
    그 가운데 내 목록에 있고 쓰기가 아닌 것, 안 적었으면 그 백엔드의 읽기 도구 전부(단계 안 쓰기 금지 v1). 심의 단계는 심의 도구 셋.
    판정의 정본은 게이트웨이다 — 읽기 목록(`mine` 의 read, /tools-map 의 routine_read)을 주면 읽기로 확인된 것만(allowed_tools), 안 주는 옛 판이면
    종전대로 쓰기 분류(R3-D6 — `mine` 의 write)와 이름 꼴(is_write_tool, 도구를 비운 단계). 적은 도구를 뺐으면 dropped_write('백엔드:이름')와
    준비도 까닭에 남긴다(단계가 비면 그 까닭으로 닫힌다).
    행마다 스펙의 앱 라벨(label, 안 적었으면 빈 글)을 싣는다 — 챗의 plan 프레임 · 화면이 단계마다 보인다(R3-design 3.2)."""
    rd = {r["step"]: r for r in readiness}
    out = []
    for s in spec.steps:
        r = rd.get(s.id) or {}
        ready = {"state": r.get("state") or "unavailable", "reason": r.get("reason") or ""}
        dropped: list[str] = []
        if s.kind == "deliberation":
            backends = [DELIB_BACKEND]
            allowed = {DELIB_BACKEND: [t for t in DELIB_TOOLS if t in (mine.get(DELIB_BACKEND) or {})]}
        else:
            backends = list(s.backends)
            allowed, dropped = allowed_tools(s, mine)
            # 뺀 도구(쓰기 · 읽기로 확인되지 않은 것)는 단계가 남아도 준비도 까닭에 적는다(R3-design 3.5 ⑦ — 계획을 읽는 실행자 · 사람이 그 도구가 왜 없는지 안다).
            # 쓰기를 빼서 단계가 비었으면 first_states 가 이 단계를 '이 박스에 없음' 으로 닫을 때 까닭이 이것이어야 한다('목록에 없다' 가 아니다).
            # readiness_of 도 같은 판정으로 적어 온다(그 단계는 이미 unavailable) — 여기서 다시 보는 것은 준비도를 따로 받은 호출도 같게
            if ready["state"] == "allowed":
                ready["reason"] = write_reason(s, allowed, dropped, mine) or ready["reason"]
        out.append({"id": s.id, "title": s.title, "kind": s.kind, "backends": backends, "label": s.label, "allowed": allowed,
                    "dropped_write": dropped,
                    "goal": s.goal, "uses": list(s.uses), "expect": s.expect.model_dump(), "budget": s.budget.model_dump(),
                    "blocked": s.blocked.model_dump(),
                    # 심의 단계의 일(job) · 의장 틀 — 실행자(챗 · Claude)가 deliberate_start 에 넘긴다. 다른 단계는 None
                    "deliberation": s.deliberation.model_dump() if s.deliberation else None,
                    "readiness": ready})
    return out


def first_states(steps: list[dict]) -> tuple[list[tuple[str, str, str | None]], str | None]:
    """단계의 첫 상태와(막힌 단계는 그 상태로 닫는다) '멈춤' 으로 짠 단계가 막혔을 때의 실행 멈춤 까닭."""
    out, stop = [], None
    for ps in steps:
        rs, why = ps["readiness"]["state"], ps["readiness"]["reason"]
        if rs == "allowed" and not any(ps["allowed"].values()):
            rs, why = "unavailable", why or "고른 도구가 이 박스 · 내 도구 목록에 없다"      # 계획이 적은 까닭(쓰기로 뺐다)이 먼저다
        if rs == "allowed":
            out.append((ps["id"], "pending", None))
            continue
        out.append((ps["id"], rs, why))
        policy = ps["blocked"]["unavailable" if rs == "unavailable" else "denied"]
        if policy == "stop" and stop is None:
            stop = f"단계 {ps['id']}({ps['title']}) — {STATE_LABEL.get(rs, rs)}: {why} · '멈춤' 으로 짠 단계라 실행을 멈췄다"
    return out, stop


def ra_split(s: str) -> list[str]:
    """긴 글을 RA_ITEM_MAX 이하 조각으로 — 버리지 않는다(에이전트 서버 deliberation._ra_split 과 같은 결과, 계약 시험)."""
    s = str(s or "")
    if len(s) <= RA_ITEM_MAX:
        return [s] if s else []
    out: list[str] = []
    buf = ""
    for part in _RA_SPLIT_RE.split(s):
        if not part:
            continue
        if len(buf) + len(part) + 1 > RA_ITEM_MAX:
            if buf:
                out.append(buf.strip())
                buf = ""
            while len(part) > RA_ITEM_MAX:
                out.append(part[:RA_ITEM_MAX])
                part = part[RA_ITEM_MAX:]
        buf = f"{buf}\n{part}" if buf else part
    if buf.strip():
        out.append(buf.strip())
    return out


def ra_blocks(blocks: dict) -> dict:
    return {k: [c for item in v for c in ra_split(item)] for k, v in blocks.items()}


def _squash(s: str) -> str:
    """공백을 하나로 — 글이 같은지 맞댈 때 줄바꿈 · 겹친 띄어쓰기를 다르게 치지 않는다."""
    return " ".join(str(s or "").split())


def coverage_of(steps: list[dict], stages: list[dict]) -> dict:
    by = {st["step_id"]: st for st in stages}
    counts: dict[str, int] = {}
    blocked = []
    for ps in steps:
        st = by.get(ps["id"]) or {}
        state = st.get("state") or "pending"
        counts[state] = counts.get(state, 0) + 1
        if state != "ok":
            blocked.append({"step": ps["id"], "title": ps["title"], "state": state, "reason": st.get("reason") or ""})
    return {"counts": counts, "not_ok": blocked}


def render_report(*, spec: RoutineSpec, run: dict, steps: list[dict], stages: list[dict], calls: list[dict],
                  sections: dict, title: str | None) -> dict:
    """보고서 — 절은 루틴의 report.sections 차례. 실행자가 쓴 절을 쓰고, 안 쓴 단계 절은 단계 요약으로 채운다. 포털이 덧붙이는 것 —
    입력 · 커버리지(건너뛴 단계와 까닭, 숨기지 않는다) · 근거 부록(원장) · 경고(모르는 인용 · 근거 없는 수치 문단)."""
    inputs = run.get("inputs") or {}
    by = {st["step_id"]: st for st in stages}
    known = {c["call_id"] for c in calls}
    keys = {sid: ((st.get("envelope") or {}).get("keys") or {}) for sid, st in by.items()}
    started = started_kst(run.get("started_at"))
    head = render(title or spec.report.title or spec.title, inputs, keys, started)
    purpose = render(spec.purpose, inputs, keys, started)
    cov = coverage_of(steps, stages)
    cov_line = " · ".join(f"{STATE_LABEL.get(k, k)} {v}" for k, v in cov["counts"].items())
    skipped = [f"{b['title']}({b['step']}) — {STATE_LABEL.get(b['state'], b['state'])}" + (f": {b['reason']}" if b["reason"] else "")
               for b in cov["not_ok"]]
    titles = {ps["id"]: ps["title"] for ps in steps}
    warnings: list[str] = []
    unknown_sections = sorted(k for k in sections if k not in spec.report.sections)
    if unknown_sections:
        warnings.append(f"루틴에 없는 절은 뺐다: {', '.join(unknown_sections)}")
    md = [f"# {head}", "",
          f"> 루틴 「{spec.title}」 판 {run.get('version_no')} · 실행 {str(run.get('id'))[:8]} · {run.get('executor')}", ""]
    if purpose:
        md += [purpose, ""]
    if inputs:
        md += ["**입력** — " + " · ".join(f"{k}={v}" for k, v in inputs.items()), ""]
    md += [f"**커버리지** — {cov_line}"] + [f"- {x}" for x in skipped] + [""]
    results, insight = [], ""
    for sec in spec.report.sections:
        text = str(sections.get(sec) or "").strip()[:20000]
        if sec == "insight":
            insight = text
            md += ["## 인사이트", "", text or "_(쓰지 않았다)_", ""]
            if not text:
                warnings.append("인사이트 절을 쓰지 않았다")
            continue
        if sec == "cite":
            cites = [f"- {f['text']} " + " ".join(f"[{r}]" for r in f.get("refs") or [])
                     for ps in steps if ps["kind"] == "cite"
                     for f in ((by.get(ps["id"]) or {}).get("envelope") or {}).get("findings") or []]
            text = text or "\n".join(cites)
            md += ["## 인용", "", text or "_(인용할 보고서를 찾지 못했다)_", ""]
            results.append(f"인용\n{text}" if text else "")
            continue
        st = by.get(sec) or {}
        env = st.get("envelope") or {}
        body = text or (env.get("summary") or "").strip() or \
            f"_(이 단계는 {STATE_LABEL.get(st.get('state'), st.get('state'))}" + (f" — {st.get('reason')}" if st.get("reason") else "") + ")_"
        extra = []
        if env.get("keys"):
            extra.append("넘긴 키 — " + " · ".join(f"{k}={v}" for k, v in env["keys"].items()))
        # 실행자가 쓴 절에 이미 있는 발견은 다시 붙이지 않는다 — 에이전트 실행기의 단계 절이 요약 + '- 발견 [ref]' 줄이라 그대로 붙이면
        # report_md 와 RA results 에 발견이 두 번 실렸다. 공백을 줄여 맞댄다. 절이 없으면 지금처럼 요약 · 키 · 발견 전부
        said = _squash(text)
        for f in env.get("findings") or []:
            if text and _squash(f["text"]) in said:
                continue
            extra.append(f"- {f['text']} " + " ".join(f"[{r}]" for r in f.get("refs") or []))
        md += [f"## {titles.get(sec, sec)}", "", body] + ([""] + extra if extra else []) + [""]
        results.append(f"{titles.get(sec, sec)}\n{body}" + ("\n" + "\n".join(extra) if extra else ""))
    cited = set(_CALL_REF.findall("\n".join(md)))
    bad = sorted(cited - known)
    if bad:
        warnings.append(f"원장에 없는 인용: {', '.join(bad[:10])}")
    bare = [p for p in re.split(r"\n\s*\n", insight) if re.search(r"\d", p) and not _CALL_REF.search(p)]
    if bare:
        warnings.append(f"인사이트에 근거 없는 수치 문단 {len(bare)}개 — [call_id] 로 인용하라")
    appendix = [f"- [{c['call_id']}] {c['backend']}:{c['tool']} {json.dumps(c['args'], ensure_ascii=False)[:160]}"
                f" — {'성공' if c['ok'] else '실패'}" + (f" · {c['ms']}ms" if c.get("ms") is not None else "")
                + (" · 결과 일부만 원장에" if c.get("truncated") else "") for c in calls]
    md += ["## 근거 부록", ""] + (appendix or ["_(호출 없음)_"])
    blocks = {"background": [x for x in (f"루틴 「{spec.title}」 판 {run.get('version_no')} — {purpose}" if purpose else
                                           f"루틴 「{spec.title}」 판 {run.get('version_no')}",
                                           "입력 — " + " · ".join(f"{k}={v}" for k, v in inputs.items()) if inputs else "",
                                           "커버리지 — " + cov_line + ("\n" + "\n".join(skipped) if skipped else "")) if x],
              "results": [x for x in results if x],
              "recommendation": [insight] if insight else [],
              "minutes": ["\n".join(appendix)] if appendix else []}
    return {"title": head, "report_md": "\n".join(md), "coverage": cov, "warnings": warnings,
            "blocks": ra_blocks(blocks), "tags": ["분석 루틴", spec.title[:40]]}
