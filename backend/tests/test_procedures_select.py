# 룰로 대상을 고른다 — 0/1/N (PLAN §10-1)
#
# R1 은 `part: "UBEND_1"` 로 이름을 박아 뒀다. 그 절차는 **그 부품에만** 쓴다.
# 다른 과제에 재생하려면 대상을 고르는 규칙이 변수여야 한다.
#
# 이 파일이 거는 것은 **0/1/N 정책**이다. 특히 N —
# 여럿에서 첫 번째를 조용히 집으면 엉뚱한 대상으로 절차 전체가 돌고 **결과는 정상으로
# 나온다**. StepForge 가 이미 그 자세다: "이름이 겹치면 후보를 돌려주고 고르지 않는다"(D-170).
import pytest

from app.procedures.judge import Verdict
from app.procedures.models import ProcedureSpec, Step, validate_spec


def _spec(sel: dict, **extra) -> ProcedureSpec:
    return ProcedureSpec.model_validate({
        "title": "룰로 고르기",
        "vars": [{"key": "project_id", "label": "과제"},
                 {"key": "rule", "label": "대상 룰", "why": "이름을 박지 않는다"}],
        "steps": [
            {"backend": "heax-step_forge", "tool": "find_parts",
             "args": {"project_id": "{{project_id}}", "name": "{{rule}}"},
             "select": sel, **extra},
            {"backend": "heax-step_forge", "tool": "part_info",
             "args": {"project_id": "{{project_id}}", "part": "{{part}}"}},
        ],
    })


# ── 저장 시점 ────────────────────────────────────────────────────────────
def test_고른_것을_뒤_단계가_쓸_수_있다():
    spec = _spec({"from": "parts", "save": "name", "as": "part"})
    assert [e for e in validate_spec(spec) if not e.startswith("warn:")] == []


def test_조용히_첫_번째를_집는_설정은_경고한다():
    """**가장 위험한 설정이다.** 엉뚱한 대상으로 돌고 결과는 정상으로 나온다."""
    spec = _spec({"from": "parts", "save": "name", "as": "part", "on_many": "first"})
    warns = [e for e in validate_spec(spec) if e.startswith("warn:")]
    assert any("조용히 집는다" in w for w in warns), warns


def test_아무것도_못_골라도_넘어가는_설정도_경고한다():
    spec = _spec({"from": "parts", "save": "name", "as": "part", "on_none": "skip"})
    assert any("못 골라도" in e for e in validate_spec(spec) if e.startswith("warn:"))


def test_담을_이름이_변수와_겹치면_거절한다():
    spec = _spec({"from": "parts", "save": "name", "as": "rule"})
    assert any("변수와 겹친다" in e for e in validate_spec(spec))


def test_raw_단계는_고를_수_없다():
    spec = _spec({"from": "parts", "save": "name", "as": "part"}, raw=True)
    assert any("raw" in e and "select" in e for e in validate_spec(spec))


def test_from_과_save_는_비울_수_없다():
    with pytest.raises(Exception):
        Step.model_validate({"backend": "b", "tool": "t",
                             "select": {"from": "", "save": "name"}})


# ── 실행 시점 — 0/1/N ────────────────────────────────────────────────────
class _Store:
    """실행기가 부르는 것만 흉내 낸다."""

    def __init__(self):
        self.finished, self.state, self.inputs = [], None, {}

    def finish_step(self, run_id, ix, **kw): self.finished.append(kw)
    def set_run_state(self, run_id, state, **kw): self.state = state
    def merge_inputs(self, run_id, extra): self.inputs.update(extra)


def _pick(rows, **sel):
    from app.procedures.runner import ProceduresRunner

    st = Step.model_validate({"backend": "b", "tool": "find_parts",
                              "select": {"from": "parts", "save": "name", "as": "part", **sel}})
    r = ProceduresRunner.__new__(ProceduresRunner)
    r.store = _Store()
    scope = {}
    out = r._pick("run", 0, st, Verdict(True, "json", "ok", parsed={"parts": rows}), scope)
    return out, scope, r.store


def test_하나면_그것을_쓴다():
    out, scope, store = _pick([{"name": "PANEL_1"}])
    assert out is None and scope["part"] == "PANEL_1"
    assert store.inputs == {"part": "PANEL_1"}, "다시 돌릴 때 쓰도록 기록에 안 남겼다"


def test_아무것도_못_고르면_실패한다():
    """조용히 건너뛰면 **뒤 단계가 전부 헛돈다** — 그런데 화면은 정상으로 보인다."""
    out, scope, store = _pick([])
    assert out["state"] == "failed" and out["kind"] == "select_none"
    assert "못 골랐다" in out["error"] and "part" not in scope


def test_여럿이면_사람에게_묻는다():
    """**요점.** 첫 번째를 조용히 집지 않는다(D-170)."""
    out, scope, store = _pick([{"name": "PANEL_1"}, {"name": "PANEL_2"}])
    assert out["state"] == "gated" and out["kind"] == "select_ask"
    assert [c["value"] for c in out["candidates"]] == ["PANEL_1", "PANEL_2"]
    assert "part" not in scope, "묻기도 전에 골랐다"
    assert store.finished[-1]["notes"]["pick_into"] == "part"


def test_first_는_명시했을_때만_집는다():
    out, scope, _ = _pick([{"name": "A"}, {"name": "B"}], on_many="first")
    assert out is None and scope["part"] == "A"


def test_fail_은_후보를_보여_주고_실패한다():
    """왜 실패했는지 모르면 룰을 어떻게 좁힐지 알 수 없다."""
    out, scope, store = _pick([{"name": "A"}, {"name": "B"}], on_many="fail")
    assert out["state"] == "failed" and out["kind"] == "select_many"
    assert store.finished[-1]["notes"]["candidates"][0]["value"] == "A"


def test_skip_은_넘어가되_기록에_남긴다():
    out, scope, store = _pick([], on_none="skip")
    assert out is None and "part" not in scope
    assert store.finished[-1]["state"] == "skipped"
    assert "못 골랐다" in store.finished[-1]["notes"]["select"]


def test_경로가_안_풀리면_후보_없음과_같다():
    """`from` 이 틀렸는데 조용히 통과하면 그게 가장 나쁘다."""
    from app.procedures.runner import ProceduresRunner

    st = Step.model_validate({"backend": "b", "tool": "t",
                              "select": {"from": "없는경로", "save": "name", "as": "part"}})
    r = ProceduresRunner.__new__(ProceduresRunner)
    r.store = _Store()
    out = r._pick("run", 0, st, Verdict(True, "json", "ok", parsed={"parts": [{"name": "A"}]}), {})
    assert out["kind"] == "select_none"


# ── "못 골랐다" 와 구분해야 하는 것들(2026-09-15 감사) ──────────────────────
# 셋 다 예전엔 하나로 뭉뚱그려졌거나 아예 성공으로 흘렀다. 진단이 틀리면 사람이
# 엉뚱한 데를 고치러 간다 — `select` 를 봐야 할 때 질의를 고치러 가는 식이다.
def test_이름_목록으로_오면_비었다고_하지_않는다():
    """`parts: ["A","B"]` — 객체가 아니라 전부 걸러진다. 3개가 왔는데 '비었다' 는 거짓이다."""
    out, scope, store = _pick(["BRKT_1", "BRKT_2", "BRKT_3"])
    assert out["kind"] == "select_shape", out
    assert "3개" in store.finished[-1]["error"] and "str" in store.finished[-1]["error"]
    assert "part" not in scope


def test_칸_이름이_틀리면_그렇게_말한다():
    """`save: name` 인데 행에 `name` 이 없다. 예전엔 후보가 전부 `value: null` 로 떴고,
    사람이 그중 하나를 고르면 None 이 다음 단계로 갔다."""
    out, scope, store = _pick([{"pid": 1, "label": "A"}, {"pid": 2, "label": "B"}])
    assert out["kind"] == "select_no_field", out
    assert "pid" in store.finished[-1]["error"] and "label" in store.finished[-1]["error"]


def test_고른_것의_값이_비면_다음_단계로_안_넘긴다():
    """`save` 경로는 이미 이러고 있다(PLAN §5-6). 여기만 안 보고 있었다 —
    `find_parts(name=null)` 은 대개 '필터 없음' 으로 읽혀 **전부**가 돌아온다."""
    out, scope, store = _pick([{"name": ""}])
    assert out["kind"] == "select_empty", out
    assert "part" not in scope and store.inputs == {}
    assert store.state == "failed"
