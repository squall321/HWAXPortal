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
SEEDS = ROOT / "docs" / "procedures" / "fixtures"
# 씨앗 → (sim_type, 카탈로그 고정물, 미리보기 고정물)
SUBMIT = {
    "partial-impact-submit": ("partial_impact", "catalog_impact", "dry_run_impact"),
    "fullangle-drop-submit": ("fullangle_drop", "catalog_drop", "dry_run_fullangle"),
}


def _load(name: str) -> ProcedureSpec:
    return ProcedureSpec.model_validate(yaml.safe_load((SEEDS / f"{name}.yaml").read_text(encoding="utf-8")))


@pytest.fixture(scope="module", params=sorted(SUBMIT))
def seed(request) -> tuple[str, ProcedureSpec]:
    return request.param, _load(request.param)


@pytest.fixture(scope="module")
def text() -> dict:
    return json.loads((FIX / "smarttwin_text_responses.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schemas() -> dict:
    return json.loads((FIX / "smarttwin_schemas.json").read_text(encoding="utf-8"))


def _examples(spec: ProcedureSpec) -> dict:
    return {v.key: (v.example if v.example is not None else "/data/templates/MinimumModel.k") for v in spec.vars}


def _params(spec: ProcedureSpec) -> dict:
    return spec.steps[1].args["scenario_overrides"]["simulation_params"]


# ── 저장될 수 있나 ───────────────────────────────────────────────────────────────────────
def test_씨앗이_경고_없이_저장된다(seed):
    """미리보기 단계(리터럴 dry_run: true)는 잡을 안 만들므로 '게이트를 권한다' 경고도 없어야 한다."""
    name, spec = seed
    assert validate_spec(spec) == []
    assert [(s.tool, s.gate) for s in spec.steps] == [
        ("smarttwin_scenario_options", None), ("smarttwin_submit", None), ("smarttwin_submit", "human")]
    assert {s.args["sim_type"] for s in spec.steps} == {SUBMIT[name][0]}


def test_템플릿_dry_run_은_여전히_게이트를_권한다():
    """실행 때 무엇이 올지 모르는 `{{dry_run}}` 까지 면제하면 게이트 없는 실제 제출이 조용히 저장된다."""
    s = ProcedureSpec.model_validate({"title": "t", "vars": [{"key": "dr", "label": "d", "type": "boolean"}], "steps": [
        {"backend": "smart-twin-cluster", "tool": "smarttwin_submit", "args": {"dry_run": "{{dr}}"}}]})
    assert any("게이트를 권한다" in e for e in validate_spec(s))
    s2 = ProcedureSpec.model_validate({"title": "t", "steps": [
        {"backend": "smart-twin-cluster", "tool": "smarttwin_submit", "args": {"dry_run": False}}]})
    assert any("게이트를 권한다" in e for e in validate_spec(s2))


def test_인자가_실제_도구_스키마와_맞는다(seed, schemas):
    _, spec = seed
    table = {st.alias: schemas[st.tool] for st in spec.steps}
    assert check_against_schemas(spec, table, missing_is_error=True) == []


def test_미리보기와_제출은_dry_run_만_다르다(seed):
    """앵커로 묶었다 — 사람이 게이트에서 대조한 scenario 와 실제로 나가는 scenario 가 달라지면 확인이 거짓이 된다."""
    _, spec = seed
    preview, submit = spec.steps[1].args, spec.steps[2].args
    assert preview["dry_run"] is True and submit["dry_run"] is False
    assert {k: v for k, v in preview.items() if k != "dry_run"} == {k: v for k, v in submit.items() if k != "dry_run"}


def test_디스패치_키가_없고_잡_ID_는_제출_단계만_평문에서_뽑는다(seed, text):
    """mode·model_file·environment 는 서버가 고정한다(넣으면 버려진다). 반환이 평문이라 JSON 경로가 아니라
    `re:` 정규식으로 뽑는다(W-90) — 미리보기에서 뽑으면 없는 잡 ID 를 찾다 멈춘다."""
    _, spec = seed
    ov = spec.steps[1].args["scenario_overrides"]
    assert not ({"mode", "model_file", "output_dir", "project_name", "environment"} & set(ov))
    assert [st.save for st in spec.steps] == [None, None, {"slurm_job_id": "re:job_id=(\\d+)"}]
    got = template.extract(text["submit_ok"], spec.steps[2].save["slurm_job_id"])
    assert got == "12345"
    with pytest.raises(template.TemplateError):
        template.extract(text["dry_run_impact"], spec.steps[2].save["slurm_job_id"])


# ── 단위(W-91) ───────────────────────────────────────────────────────────────────────────
def test_단위계_선택_변수는_없다(seed):
    """단위계 키가 KMM 에 없으니 고르는 변수는 가짜 스위치다."""
    _, spec = seed
    assert not any("unit" in v.key or "단위계" in v.label for v in spec.vars)


def test_물성_예시는_tonne_mm_값이고_label_에_단위가_있다(seed):
    """SI 예시(7850·2e11)는 무변환 기입된다. 물성 변수마다 예시가 tonne-mm 범위이고 label 이 단위를 말한다."""
    _, spec = seed
    dens = [v for v in spec.vars if v.key.endswith("_density")]
    mods = [v for v in spec.vars if v.key.endswith("_youngs_modulus")]
    assert dens and mods
    for v in dens:
        assert isinstance(v.example, float) and v.example < 1e-6 and "tonne/mm³" in v.label, v.key
    for v in mods:
        assert isinstance(v.example, float) and 1e4 < v.example < 1e7 and "MPa" in v.label, v.key


def test_부분충격은_임팩터_물성을_늘_명시한다():
    imp = _params(_load("partial-impact-submit"))["impactor"]
    assert {"density", "youngs_modulus", "poisson_ratio", "height", "radius"} <= set(imp)
    why = next(v.why for v in _load("partial-impact-submit").vars if v.key == "impact_height_mm")
    assert "100" in why and "2배" in why          # 초속 이중 합산


def test_전각도는_프리셋의_SI_바닥_물성을_덮는다():
    """프리셋 5종의 바닥 7850/2e11 은 기본 단위계에서 틀린 값이다 — 덮지 않으면 그 값으로 돈다."""
    spec = _load("fullangle-drop-submit")
    p = _params(spec)
    assert {"density", "youngs_modulus", "poisson_ratio", "height"} <= set(p)
    why = next(v.why for v in spec.vars if v.key == "drop_height_mm")
    assert "100" in why and "9.81" in why         # 100 이하면 m 로 읽힌다


# ── 도는 모양인가 ─────────────────────────────────────────────────────────────────────────
def test_예시로_채우면_인자가_선언한_형으로_간다(seed):
    """통째 치환이 수치·객체를 문자열로 만들면 서버가 조용히 다른 해석을 돌린다."""
    name, spec = seed
    args = template.substitute(spec.steps[2].args, coerce_inputs(spec, _examples(spec)))
    sp = args["scenario_overrides"]["simulation_params"]
    assert args["dry_run"] is False and args["job_name"].isascii()
    if name == "partial-impact-submit":
        assert isinstance(sp["locations"], dict) and sp["locations"]["mode"] == "grid"
        assert isinstance(sp["impactor"]["density"], float) and isinstance(sp["impactor"]["height"], int)
    else:
        assert isinstance(sp["density"], float) and isinstance(sp["height"], int)
        assert sp["drop_surface"] == {"type": "Plane"} and args["angle_preset"] == "26direction"


def test_단계별_판정이_실물_평문에서_맞다(seed, text):
    name, spec = seed
    _, cat_key, dry_key = SUBMIT[name]
    cat, preview, submit = spec.steps

    def ok(st, body):
        return judge(is_error=False, text=body, raw=st.raw, unwrap=st.unwrap, ok_text=st.ok_text)

    assert ok(cat, text[cat_key]).ok
    assert ok(preview, text[dry_key]).ok
    assert ok(submit, text["submit_ok"]).ok
    # 실패는 실패로
    assert ok(submit, text["submit_http_fail"]).kind == "text_error"
    assert ok(submit, text["submit_parse_fail"]).kind == "text_unexpected"
    assert ok(cat, text["error_real"]).ok is False
    # 다른 sim_type 의 카탈로그를 받으면 실패 — 인자가 엇갈렸다는 뜻이다
    other = "catalog_drop" if cat_key == "catalog_impact" else "catalog_impact"
    assert not ok(cat, text[other]).ok


def test_단계가_엇갈린_응답을_성공으로_보지_않는다(seed, text):
    """제출 단계가 미리보기 응답을 받았다 = 아무것도 안 나갔다. 미리보기 단계가 제출 완료를 받았다 = dry_run 이 깨졌다."""
    name, spec = seed
    _, preview, submit = spec.steps
    assert not judge(is_error=False, text=text[SUBMIT[name][2]], raw=True, ok_text=submit.ok_text).ok
    assert not judge(is_error=False, text=text["submit_ok"], raw=True, ok_text=preview.ok_text).ok


# ── 평문 추출(re:) — 제출 씨앗이 잡 ID 를 넘기는 길 ─────────────────────────────────────────
def _raw_spec(save: dict, raw: bool = True) -> ProcedureSpec:
    return ProcedureSpec.model_validate({"title": "t", "steps": [
        {"backend": "smart-twin-cluster", "tool": "smarttwin_scenario_options", "raw": raw, "save": save}]})


def test_평문_추출_경로의_저장_검증():
    assert validate_spec(_raw_spec({"job": "re:job_id=(\\d+)"})) == []
    assert any("re:" in e for e in validate_spec(_raw_spec({"job": "a.b"})))            # raw 인데 JSON 경로
    assert any("raw 단계에만" in e for e in validate_spec(_raw_spec({"job": "re:(x)"}, raw=False)))
    assert any("정확히 하나" in e for e in validate_spec(_raw_spec({"job": "re:job_id=\\d+"})))
    assert any("정확히 하나" in e for e in validate_spec(_raw_spec({"job": "re:(a)(b)"})))
    assert any("깨졌다" in e for e in validate_spec(_raw_spec({"job": "re:(unclosed"})))


def test_평문_추출은_평문에서만_찾고_못_찾으면_멈춘다():
    assert template.extract("✅ 제출 완료 — job_id=77\n…", "re:job_id=(\\d+)") == "77"
    with pytest.raises(template.TemplateError, match="못 찾았다"):
        template.extract("[DRY-RUN] 제출 계획", "re:job_id=(\\d+)")
    with pytest.raises(template.TemplateError, match="평문"):
        template.extract({"job_id": 1}, "re:job_id=(\\d+)")
