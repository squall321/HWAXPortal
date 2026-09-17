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


# ── 부품 보고서 씨앗 둘(회수·판독) ───────────────────────────────────────────────────────────
COLLECT = {"fullangle-drop-part-report": "sphere", "partial-impact-part-report": "impact"}
DF = json.loads((FIX / "dynaforge_report_responses.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=sorted(COLLECT))
def collect(request) -> tuple[str, ProcedureSpec]:
    return request.param, _load(request.param)


def _text(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def test_회수_씨앗이_경고_없이_저장된다(collect):
    name, spec = collect
    assert validate_spec(spec) == []
    assert [s.tool for s in spec.steps] == [
        "find_reports", "report_summary", "report_part_risk", "report_directional",
        "report_part_series", "report_findings", "create_report_draft", "suggest_report_tags"]
    assert [s.gate for s in spec.steps] == [None] * 6 + ["human", None], "게이트는 보고서 초안 하나뿐이다"
    assert spec.steps[0].args["kind"] == COLLECT[name]


def test_리포트를_report_id_가_아니라_잡_키로_찾는다(collect):
    """사람이 report_id 를 옮겨 적으면 오타 하나가 남의 잡을 가리킨다 — 제출이 남긴 잡 키로 찾는다(W-93)."""
    _, spec = collect
    declared = {v.key for v in spec.vars}
    assert declared == {"job_name", "slurm_job_id", "part_id"}, declared
    assert spec.steps[0].args["project"] == "{{job_name}}_{{slurm_job_id}}"
    sel = spec.steps[0].select
    assert (sel.from_, sel.save, sel.var) == ("$", "id", "report_id")
    assert (sel.on_many, sel.on_none) == ("ask", "fail"), "여럿이면 사람이 고르고 0건은 실패다"


def test_인자가_DynaForge_실제_스키마와_맞는다(collect):
    _, spec = collect
    table = {st.alias: DF["schemas"][st.tool] for st in spec.steps if st.tool in DF["schemas"]}
    # 스키마가 없는 단계는 **대조되지 않는다.** 개수를 박으면 단계를 늘렸을 때 조용히 빠지므로
    # 빠진 것을 이름으로 적는다. create_report_draft 는 블록이 자유 형식이라 여기서 안 본다.
    assert sorted({st.tool for st in spec.steps} - set(DF["schemas"])) == ["create_report_draft"]
    errs = check_against_schemas(spec, table, missing_is_error=False)
    hard = [e for e in errs if not e.startswith("warn:")]
    assert hard == [], hard


def test_save_경로가_응답_모양에서_풀린다(collect):
    """dev 에는 리포트가 0건이라 합성 고정물이다(소스에서 유도). cae00 실행 뒤 실측으로 간다."""
    _, spec = collect
    bodies = [DF["find_reports"], DF["report_summary"], DF["report_part_risk"], DF["report_directional"],
              DF["report_part_series"], DF["report_findings"], DF["ra_create"], DF["ra_suggest"]]
    scope: dict = {}
    for st, body in zip(spec.steps, bodies, strict=True):
        v = judge(is_error=False, text=_text(body), raw=st.raw, unwrap=st.unwrap)
        assert v.ok, (st.tool, v.kind, v.error)
        if st.select is not None:
            rows = template.extract(v.parsed, st.select.from_)
            assert isinstance(rows, list) and rows, st.tool
            scope[st.select.var] = rows[0][st.select.save]
        for key, path in (st.save or {}).items():
            scope[key] = template.extract(v.parsed, path)
            assert not template.is_empty(scope[key]), f"{st.tool} {key} 가 빈 값이다 — 실행이 선다"
    assert scope["report_id"].startswith("01JAX7")
    assert scope["part_name"] == "BRKT_MAIN" and scope["worst_case"] == "Run_014/corner_xyz"
    assert scope["ra_report_id"] == 4210 and scope["ra_report_url"].startswith("/w/")
    assert isinstance(scope["tag_candidates"], list)


def test_없을_수_있는_칸은_뽑지_않는다(collect):
    """최소 안전율·소견은 **정상적으로 빌 수 있다.** save 로 뽑으면 빈 값이 실행을 세운다(PLAN §5-6)."""
    _, spec = collect
    saved_paths = {p for st in spec.steps for p in (st.save or {}).values()}
    assert not any("safety" in p for p in saved_paths), saved_paths
    findings = next(st for st in spec.steps if st.tool == "report_findings")
    assert findings.save is None
    assert DF["report_part_risk"]["parts"][0]["min_safety_factor"] is None, "고정물이 그 경우를 담고 있어야 한다"


def test_시계열은_앞_단계가_고른_최악_케이스로_돈다(collect):
    _, spec = collect
    series = next(st for st in spec.steps if st.tool == "report_part_series")
    assert series.args == {"report_id": "{{report_id}}", "case_key": "{{worst_case}}",
                           "part_id": "{{part_id}}"}


def test_보고서_초안_저장_이름이_리포트_ID_와_안_겹친다(collect):
    """`report_id`(DynaForge 리포트)와 RA 보고서 번호가 같은 이름이면 뒤 단계가 엉뚱한 것을 가리킨다."""
    _, spec = collect
    draft = next(st for st in spec.steps if st.tool == "create_report_draft")
    assert set(draft.save) == {"ra_report_id", "ra_report_url"}
    tags = next(st for st in spec.steps if st.tool == "suggest_report_tags")
    assert tags.args == {"report_id": "{{ra_report_id}}"} and tags.gate is None


# ── 축 태그 붙이기 씨앗(여럿을 골라 한 번에) ────────────────────────────────────────────────
def test_태그_씨앗이_경고_없이_저장된다():
    spec = _load("report-add-tags")
    assert validate_spec(spec) == []
    assert [(s.tool, s.gate) for s in spec.steps] == [
        ("suggest_report_tags", None), ("add_report_tags", "human")]


def test_태그는_펼치지_않고_고른_것을_한_번에_넘긴다():
    """펼치면(fan-out) 태그 수만큼 실행이 생기고 **승인도 그만큼** 받는다. 태그는 한 번이 맞다."""
    spec = _load("report-add-tags")
    sel = spec.steps[0].select
    assert sel.multi is True and sel.on_many == "ask", "여럿은 사람이 고른다"
    assert (sel.from_, sel.save, sel.var, sel.label) == ("items", "id", "tag_ids", "value")
    assert sel.on_none == "fail", "후보 0건은 기준정보가 없다는 뜻이다 — 조용히 넘어가지 않는다"
    assert spec.steps[1].args["entity_ids"] == "{{tag_ids}}", "통째 치환이라 목록이 목록으로 간다"


def test_태그_씨앗의_인자가_RA_실제_스키마와_맞는다():
    spec = _load("report-add-tags")
    table = {st.alias: DF["schemas"][st.tool] for st in spec.steps}
    assert check_against_schemas(spec, table, missing_is_error=True) == []


def test_태그_씨앗이_응답_모양에서_풀린다():
    """후보의 `id` 를 고른다 — RA 가 주는 칸 이름이 그것이다(autotag.Suggestion)."""
    spec = _load("report-add-tags")
    v = judge(is_error=False, text=_text(DF["ra_suggest"]))
    rows = template.extract(v.parsed, spec.steps[0].select.from_)
    assert [r[spec.steps[0].select.save] for r in rows] == [812, 917, 933]
    assert [r[spec.steps[0].select.label] for r in rows][0] == "drop-demo-01"
    assert judge(is_error=False, text=_text(DF["ra_add"])).ok


def test_고른_태그가_정수_목록으로_치환된다():
    """`"{{tag_ids}}"` 는 **통째 치환**이라 형이 산다 — 문자열로 가면 RA 가 거절한다."""
    spec = _load("report-add-tags")
    args = template.substitute(spec.steps[1].args, {"report_id": 4210, "tag_ids": [812, 917]})
    assert args == {"report_id": 4210, "entity_ids": [812, 917]}


# ── 엉뚱한 해석의 리포트를 받으면 거기서 선다 ─────────────────────────────────────────────
def test_회수_씨앗이_리포트_종류를_단언한다(collect):
    """잡 키가 겹치면 다른 해석의 리포트가 온다. 판정기는 '도구가 실패했나' 만 보므로
    판독은 전부 성공하고 **보고서만 다른 해석 위에서** 나온다 — 그 자리를 선언으로 막는다."""
    name, spec = collect
    summary = next(st for st in spec.steps if st.tool == "report_summary")
    assert [(c.path, c.equals) for c in summary.asserts] == [("kind", COLLECT[name])]
    # 단언은 save 보다 먼저 본다 — 어긋난 응답에서 값을 뽑아 다음 단계로 넘기지 않는다.
    assert summary.save == {"kind": "kind"}


def test_단언이_실제_응답_모양에서_돈다(collect):
    name, spec = collect
    summary = next(st for st in spec.steps if st.tool == "report_summary")
    body = dict(DF["report_summary"], kind=COLLECT[name])
    v = judge(is_error=False, text=_text(body))
    for chk in summary.asserts:
        assert chk.check(template.extract(v.parsed, chk.path)) is None
    other = dict(body, kind="impact" if COLLECT[name] == "sphere" else "sphere")
    v2 = judge(is_error=False, text=_text(other))
    why = summary.asserts[0].check(template.extract(v2.parsed, "kind"))
    assert why and "기대했다" in why, why
