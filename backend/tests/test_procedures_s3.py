# S3 낙하·충격 — 제출 씨앗이 **저장되고, 도는 모양이고, 단위·미리보기 규칙을 지키는가**
#
# R3 와 같은 자세다(test_procedures_r3.py). 제출은 부르지 않았다 — 평문 응답은 KooSlurm 소스·게이트웨이 dry_run
# 실호출 고정물(tests/fixtures/procedures/smarttwin_text_responses.json), 스키마는 게이트웨이 tools/list 에서 옮긴
# 것(smarttwin_schemas.json)으로 본다. 단위 규칙은 docs/procedures/context-notes.md W-91, 평문은 W-90.
import json
from pathlib import Path

import pytest
import yaml

from app.procedures import template
from app.procedures.judge import judge
from app.procedures.models import ProcedureSpec, check_against_schemas, coerce_inputs, validate_spec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).parent / "fixtures" / "procedures"
IMPACT = ROOT / "docs" / "procedures" / "fixtures" / "partial-impact-submit.yaml"


@pytest.fixture(scope="module")
def spec() -> ProcedureSpec:
    return ProcedureSpec.model_validate(yaml.safe_load(IMPACT.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def text() -> dict:
    return json.loads((FIX / "smarttwin_text_responses.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schemas() -> dict:
    return json.loads((FIX / "smarttwin_schemas.json").read_text(encoding="utf-8"))


def _examples(spec: ProcedureSpec) -> dict:
    return {v.key: (v.example if v.example is not None else "/data/templates/MinimumModel.k") for v in spec.vars}


# ── 저장될 수 있나 ───────────────────────────────────────────────────────────────────────
def test_부분충격_씨앗이_경고_없이_저장된다(spec):
    """미리보기 단계(리터럴 dry_run: true)는 잡을 안 만들므로 '게이트를 권한다' 경고도 없어야 한다."""
    assert validate_spec(spec) == []
    assert [(s.tool, s.gate) for s in spec.steps] == [
        ("smarttwin_scenario_options", None), ("smarttwin_submit", None), ("smarttwin_submit", "human")]


def test_템플릿_dry_run_은_여전히_게이트를_권한다():
    """실행 때 무엇이 올지 모르는 `{{dry_run}}` 까지 면제하면 게이트 없는 실제 제출이 조용히 저장된다."""
    s = ProcedureSpec.model_validate({"title": "t", "vars": [{"key": "dr", "label": "d", "type": "boolean"}], "steps": [
        {"backend": "smart-twin-cluster", "tool": "smarttwin_submit", "args": {"dry_run": "{{dr}}"}}]})
    assert any("게이트를 권한다" in e for e in validate_spec(s))
    s2 = ProcedureSpec.model_validate({"title": "t", "steps": [
        {"backend": "smart-twin-cluster", "tool": "smarttwin_submit", "args": {"dry_run": False}}]})
    assert any("게이트를 권한다" in e for e in validate_spec(s2))


def test_인자가_실제_도구_스키마와_맞는다(spec, schemas):
    table = {st.alias: schemas[st.tool] for st in spec.steps}
    assert check_against_schemas(spec, table, missing_is_error=True) == []


def test_미리보기와_제출은_dry_run_만_다르다(spec):
    """앵커로 묶었다 — 사람이 게이트에서 대조한 scenario 와 실제로 나가는 scenario 가 달라지면 확인이 거짓이 된다."""
    preview, submit = spec.steps[1].args, spec.steps[2].args
    assert preview["dry_run"] is True and submit["dry_run"] is False
    assert {k: v for k, v in preview.items() if k != "dry_run"} == {k: v for k, v in submit.items() if k != "dry_run"}


def test_디스패치_키와_잡_ID_save_가_없다(spec):
    """mode·model_file·environment 는 서버가 고정한다(넣으면 버려진다). 반환이 평문이라 save 로 job_id 를 못 뽑는다(W-90)."""
    ov = spec.steps[1].args["scenario_overrides"]
    assert not ({"mode", "model_file", "output_dir", "project_name", "environment"} & set(ov))
    assert all(st.save is None for st in spec.steps)


# ── 단위(W-91) ───────────────────────────────────────────────────────────────────────────
def test_임팩터_물성은_늘_명시하고_label_에_단위가_있다(spec):
    imp = spec.steps[1].args["scenario_overrides"]["simulation_params"]["impactor"]
    assert {"density", "youngs_modulus", "poisson_ratio", "height", "radius"} <= set(imp)
    labels = {v.key: v.label for v in spec.vars}
    assert "tonne/mm³" in labels["impactor_density"] and "MPa" in labels["impactor_youngs_modulus"]
    assert "(mm)" in labels["impact_height_mm"]


def test_예시는_tonne_mm_값이고_단위계_선택_변수는_없다(spec):
    """SI 예시(7850·2e11)는 무변환 기입돼 질량 10¹²배가 된다. 단위계 키가 KMM 에 없으니 고르는 변수는 가짜 스위치다."""
    ex = {v.key: v.example for v in spec.vars}
    assert isinstance(ex["impactor_density"], float) and ex["impactor_density"] < 1e-6
    assert isinstance(ex["impactor_youngs_modulus"], float) and 1e4 < ex["impactor_youngs_modulus"] < 1e7
    assert not any("unit" in v.key or "단위계" in v.label for v in spec.vars)


def test_100mm_초과_초속_이중_합산을_경고한다(spec):
    why = next(v.why for v in spec.vars if v.key == "impact_height_mm")
    assert "100" in why and "2배" in why


# ── 도는 모양인가 ─────────────────────────────────────────────────────────────────────────
def test_예시로_채우면_인자가_선언한_형으로_간다(spec):
    """통째 치환이 수치·객체를 문자열로 만들면 서버가 조용히 다른 해석을 돌린다(W-85 류)."""
    args = template.substitute(spec.steps[2].args, coerce_inputs(spec, _examples(spec)))
    sp = args["scenario_overrides"]["simulation_params"]
    assert isinstance(sp["locations"], dict) and sp["locations"]["mode"] == "grid"
    assert isinstance(sp["impactor"]["density"], float) and isinstance(sp["impactor"]["height"], int)
    assert sp["generation_mode"] == "DampingSpring" and args["dry_run"] is False


def test_단계별_판정이_실물_평문에서_맞다(spec, text):
    cat, preview, submit = spec.steps

    def ok(st, body):
        return judge(is_error=False, text=body, raw=st.raw, unwrap=st.unwrap, ok_text=st.ok_text)

    assert ok(cat, text["catalog_impact"]).ok
    assert ok(preview, text["dry_run_impact"]).ok
    assert ok(submit, text["submit_ok"]).ok
    # 실패는 실패로
    assert ok(submit, text["submit_http_fail"]).kind == "text_error"
    assert ok(submit, text["submit_parse_fail"]).kind == "text_unexpected"
    assert ok(cat, text["error_real"]).ok is False


def test_단계가_엇갈린_응답을_성공으로_보지_않는다(spec, text):
    """제출 단계가 미리보기 응답을 받았다 = 아무것도 안 나갔다. 미리보기 단계가 제출 완료를 받았다 = dry_run 이 깨졌다."""
    _, preview, submit = spec.steps
    assert not judge(is_error=False, text=text["dry_run_impact"], raw=True, ok_text=submit.ok_text).ok
    assert not judge(is_error=False, text=text["submit_ok"], raw=True, ok_text=preview.ok_text).ok
