# R1 적층 굴곡 수명 — 씨앗 절차가 **실물 응답에서 실제로 풀리는가**
#
# 절차가 "저장된다" 와 "돈다" 는 다른 문제다. 여기서 닫는 것은 뒤쪽이다 —
# `save` 경로 하나가 틀리면 실행 시점에야 알게 되고, 그때는 이미 앞 단계가 돌아 있다.
#
# 고정물은 **실물**이다(tests/fixtures/procedures/laminate_responses.json). 2026-09-14
# dev 게이트웨이를 실제로 불러 받은 응답이고, **8개 넘는 배열만** 앞 2개로 줄였다 —
# 짧은 배열은 모양이 곧 뜻이라(N·M 은 숫자 3개다) 자르면 고정물이 거짓이 된다.
# 실제로 이 테스트를 쓰는 중에 문서의 `save` 경로가 전부 틀렸다는 것이 드러났다 —
# 적층 해석기 응답은 `{status, data, errors, warnings}` 봉투라 값이 `data.` 아래에 있다.
import json
from pathlib import Path

import pytest
import yaml

from app.procedures import template
from app.procedures.judge import collect_notes, judge
from app.procedures.models import ProcedureSpec, validate_spec

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "docs" / "procedures" / "fixtures" / "laminate-bend-life.yaml"
REAL = Path(__file__).parent / "fixtures" / "procedures" / "laminate_responses.json"

# 단계 순서 ↔ 어느 실물 응답으로 시험하나
STEP_RESPONSE = {0: "bend", 2: "bent", 3: "flat", 4: "plies", 5: "life"}


@pytest.fixture(scope="module")
def spec() -> ProcedureSpec:
    return ProcedureSpec.model_validate(yaml.safe_load(SEED.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def real() -> dict:
    return json.loads(REAL.read_text(encoding="utf-8"))


# ── 저장될 수 있나 ───────────────────────────────────────────────────────
def test_seed_parses_and_passes_save_time_validation(spec):
    hard = [e for e in validate_spec(spec) if not e.startswith("warn:")]
    assert hard == [], f"씨앗 절차가 저장 시점 검증에 걸린다: {hard}"


def test_report_step_is_gated(spec):
    """되돌리기 어려운 단계는 작성자가 게이트를 끌 수 없다."""
    last = spec.steps[-1]
    assert last.tool == "create_report_draft" and last.gate == "human"


def test_every_variable_is_used_and_every_save_is_consumed(spec):
    """쓰이지 않는 변수·아무도 안 받는 save 는 절차가 덜 여문 자리다."""
    refs: set[str] = set()
    for st in spec.steps:
        refs |= {r.split(".")[0] for r in template.refs(st.args)}
    declared = {v.key for v in spec.vars}
    assert declared <= refs, f"안 쓰는 변수: {sorted(declared - refs)}"

    saved = {k for st in spec.steps for k in (st.save or {})}
    # bend_basis·t_part·w_part 는 보고서 근거로 남기는 값이라 인자로는 안 쓴다
    unconsumed = saved - refs - {"bend_basis", "t_part", "w_part", "tsai_wu_r",
                                 "failure_mode", "life_cycles"}
    assert not unconsumed, f"아무도 안 받는 save: {sorted(unconsumed)}"


def test_variables_left_to_humans_all_say_why(spec):
    """형상에 없는 값만 사람이 채운다 — 왜 물어보는지가 없으면 그 자체가 결손이다."""
    for v in spec.vars:
        if v.key in ("project_id",):
            continue
        assert v.why, f"{v.key}: why 가 없다"


# ── 실물에서 풀리나 ──────────────────────────────────────────────────────
@pytest.mark.parametrize("ix,key", sorted(STEP_RESPONSE.items()))
def test_save_paths_resolve_against_real_responses(spec, real, ix, key):
    """**이 테스트가 문서의 틀린 경로를 잡았다.** 봉투 때문에 값이 `data.` 아래 있다."""
    step = spec.steps[ix]
    body = real[key]["body"]
    v = judge(is_error=real[key]["is_error"], text=json.dumps(body, ensure_ascii=False),
              raw=step.raw, unwrap=step.unwrap)
    assert v.ok, f"{step.tool}: 실물 응답이 실패로 판정됐다 — {v.error}"
    for name, path in (step.save or {}).items():
        got = template.extract(v.parsed, path)
        assert not template.is_empty(got), f"{step.tool}: save {name} ← {path} 가 비었다"


def test_bend_profile_gives_the_three_values_that_used_to_be_human(spec, real):
    """굽힘반경·두께·폭이 형상에서 나온다 — 계획은 이 셋을 '사람이 채우는 칸' 으로 뒀었다."""
    body = real["bend"]["body"]
    got = {k: template.extract(body, p) for k, p in (spec.steps[0].save or {}).items()}
    assert got["r_designed"] == pytest.approx(6.0, abs=1e-6)
    assert got["t_part"] == pytest.approx(1.2, abs=1e-6)
    assert got["w_part"] == pytest.approx(40.0, abs=1e-6)
    assert got["bend_basis"] in ("analytic_cylinder_pair", "sampled_curvature_pair")


def test_equivalent_loads_flow_into_the_next_two_steps(spec, real):
    """체인의 핵심 — ③의 등가하중이 ⑤·⑥에 **형 그대로** 들어간다."""
    loads = template.extract(real["bent"]["body"], "data.equivalent_loads")
    assert isinstance(loads, dict) and set(loads) >= {"N", "M"}
    scope = {"laminate": {}, "loads_bent": loads, "loads_flat": loads}
    for ix in (4, 5):
        args = template.substitute(spec.steps[ix].args, {**_stub(spec, ix), **scope})
        passed = args.get("loads") or args.get("loads_max")
        assert passed == loads, f"{spec.steps[ix].tool}: 하중이 형 그대로 안 들어갔다"


def _stub(spec: ProcedureSpec, ix: int) -> dict:
    """이 단계가 참조하는 나머지 변수의 빈 자리 — 진짜 값을 덮어쓰면 안 된다."""
    return {r.split(".")[0]: {} for r in template.refs(spec.steps[ix].args)}


# ── 실패·경고가 제대로 보이나 ────────────────────────────────────────────
@pytest.mark.parametrize("key", ["bad", "bad2"])
def test_error_envelope_is_a_failure_even_though_is_error_is_false(real, key):
    """`{status:"error", data:null, errors:[…]}` 가 isError=false 로 온다 — 실측."""
    body = real[key]["body"]
    assert body["status"] == "error" and body["data"] is None
    v = judge(is_error=False, text=json.dumps(body, ensure_ascii=False))
    assert v.ok is False and v.kind == "app_envelope"
    assert any(c in v.error for c in ("E100", "E102"))


def test_warning_status_is_not_a_failure_but_reaches_notes(real):
    """`status:"warning"` 은 실패가 아니다. 다만 경고가 사라지면 안 된다."""
    body = real["bent"]["body"]
    assert body["status"] == "warning"
    v = judge(is_error=False, text=json.dumps(body, ensure_ascii=False))
    assert v.ok is True
    codes = [w.get("code") for w in v.notes.get("warnings", []) if isinstance(w, dict)]
    assert "W130" in codes, "폭 구속 경고(9.6% 차이)가 notes 로 안 올라왔다"


def test_w120_silent_ply_exclusion_reaches_notes(real):
    """물성 없는 ply 를 조용히 제외하고 결과는 정상으로 온다 — 경고만이 유일한 신호다."""
    body = real["life_w120"]["body"]
    v = judge(is_error=False, text=json.dumps(body, ensure_ascii=False))
    assert v.ok is True, "이 응답은 성공으로 와야 한다(그게 함정이다)"
    blob = json.dumps(collect_notes(v.parsed), ensure_ascii=False)
    assert "W120" in blob and "제외" in blob


def test_clean_run_has_no_warnings_to_lift(real):
    """경고가 없을 때 빈 칸을 만들지 않는다 — 있으면 사람이 무시하게 된다."""
    v = judge(is_error=False, text=json.dumps(real["life"]["body"], ensure_ascii=False))
    assert v.ok is True and "warnings" not in v.notes


# ── 붙여 넣을 예시 — 씨앗이 들고 있어야 한다 ─────────────────────────────────
def test_laminate_example_is_a_real_payload_the_tool_accepts(spec):
    """사람이 손으로 쓰면 **두 번 걸린다**(실호출 2026-09-14) — `material.type` 누락은
    E202, `fatigue.k > 1` 은 E100 이다. 예시는 그 둘을 피한 판이어야 한다.
    """
    v = next(x for x in spec.vars if x.key == "laminate")
    assert v.example, "붙여 넣을 예시가 없으면 사람이 4겹을 손으로 쓴다"
    plies = v.example["laminae"]
    assert len(plies) == 4 and v.example["unit_system"] == "SI_mm"
    for i, p in enumerate(plies):
        m = p["material"]
        assert m.get("type") == "orthotropic_2d", f"ply {i}: type 이 없으면 E202 다"
        assert m["fatigue"]["k"] <= 1, f"ply {i}: k 는 기울기라 1 이하다(아니면 E100)"
        assert set(m["strength"]) >= {"Xt", "Xc", "Yt", "Yc", "S"}, f"ply {i}: 강도가 모자라다"


def test_example_total_thickness_matches_the_part_the_geometry_step_reads(spec, real):
    """총두께가 ①이 준 두께와 다르면 **다른 부품을 해석하는 것이다.**"""
    v = next(x for x in spec.vars if x.key == "laminate")
    total = sum(p["thickness"] for p in v.example["laminae"])
    from_geometry = template.extract(real["bend"]["body"],
                                     "parts[0].for_bending_analysis.thickness_mm")
    assert total == pytest.approx(from_geometry, abs=1e-9), (
        f"예시 총두께 {total}mm 인데 형상은 {from_geometry}mm 다")


def test_example_does_not_quietly_become_the_answer(spec):
    """**예시는 기본값이 아니다.** 비워 두면 시작에서 걸려야 한다 — 남의 값으로 돌면 안 된다."""
    from app.procedures.models import SpecError, coerce_inputs

    assert next(x for x in spec.vars if x.key == "laminate").required is True
    with pytest.raises(SpecError):
        coerce_inputs(spec, {"project_id": "p", "part": "UBEND_1", "r_unfold": 1000,
                             "bend_axis": "x", "width_mode": "free"})   # laminate 없음
