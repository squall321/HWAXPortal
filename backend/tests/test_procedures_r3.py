# R3 열충격 SED — 씨앗 절차가 **실물 응답에서 실제로 풀리는가**
#
# R1 과 같은 자세다(test_procedures_r1.py). "저장된다" 와 "돈다" 는 다른 문제라, save 경로 하나가
# 틀리면 실행 시점에야 알게 된다 — 그때는 이미 odb-hub 를 세 번 부른 뒤다.
#
# 고정물(tests/fixtures/procedures/thermal_shock_responses.json):
#   - odb_* : odb-hub 실측 표본(fixtures/odb-hub/reference.md §4.6·§4.12). **ap_part 만 합성**이다 —
#             실측 AP 표본이 없다. 표시(_synthetic)가 붙어 있다.
#   - reduce·predict : ThermalShockMCP 코드를 **실제로 실행한 출력**(predict 모델은 실데이터 294건 학습).
#   - schemas : ThermalShockMCP 도구의 실제 inputSchema.
# odb-hub 스키마는 dev 게이트웨이에 없다 — 아래 검사는 그 두 단계를 "안 보인다(warn)" 로만 다룬다.
import json
from pathlib import Path

import pytest
import yaml

from app.procedures import template
from app.procedures.judge import collect_notes, judge
from app.procedures.models import ProcedureSpec, check_against_schemas, validate_spec

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "docs" / "procedures" / "fixtures" / "thermal-shock-sed.yaml"
REAL = Path(__file__).parent / "fixtures" / "procedures" / "thermal_shock_responses.json"

# 단계 순서 ↔ 실물 응답
STEP_RESPONSE = {0: "odb_ap_part", 1: "odb_pkg_part", 2: "odb_interposer", 3: "reduce", 4: "predict",
                 5: "ra_create", 6: "ra_suggest"}


@pytest.fixture(scope="module")
def spec() -> ProcedureSpec:
    return ProcedureSpec.model_validate(yaml.safe_load(SEED.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def real() -> dict:
    return json.loads(REAL.read_text(encoding="utf-8"))


def _text(obj) -> str:
    # 게이트웨이가 넘기는 모양 그대로(들여쓰기 JSON) — 판정기는 이 문자열을 받는다
    return json.dumps(obj, ensure_ascii=False, indent=2)


# ── 저장될 수 있나 ───────────────────────────────────────────────────────────────────────
def test_씨앗이_저장_시점_검증을_통과한다(spec):
    hard = [e for e in validate_spec(spec) if not e.startswith("warn:")]
    assert hard == [], f"씨앗 절차가 저장 시점 검증에 걸린다: {hard}"
    assert [s.tool for s in spec.steps] == [
        "get_part_detail", "get_part_detail", "get_interposer_result", "sed_sample_from_odb", "predict_sed",
        "create_report_draft", "suggest_report_tags"]


def test_열충격_단계의_인자가_실제_도구_스키마와_맞는다(spec, real):
    schemas = {st.alias: real["schemas"][st.tool] for st in spec.steps if st.tool in real["schemas"]}
    assert len(schemas) == 4, sorted(schemas)   # 열충격 둘 + RA 둘 — 실제 스키마로 대조한다
    errs = check_against_schemas(spec, schemas, missing_is_error=False)
    hard = [e for e in errs if not e.startswith("warn:")]
    assert hard == [], hard
    # odb-hub 두 도구는 dev 에 없다 — **안 보인다고 말하는지**(조용히 통과가 아니다)
    assert sum("get_part_detail" in e or "get_interposer_result" in e for e in errs) == 3, errs


# ── 도는가 — 실물 응답에서 판정·save 가 풀린다 ────────────────────────────────────────────────
def test_모든_단계의_save_경로가_실물_응답에서_풀린다(spec, real):
    scope: dict = {}
    for i, st in enumerate(spec.steps):
        body = real[STEP_RESPONSE[i]]
        v = judge(is_error=False, text=_text(body), raw=st.raw, unwrap=st.unwrap)
        assert v.ok, f"{i + 1}단계 {st.tool} 가 실패로 판정됐다: {v.kind} {v.error}"
        for key, path in (st.save or {}).items():
            scope[key] = template.extract(v.parsed, path)
    assert scope["sample"]["pad_size"] == 190.0          # U1005 의 r190
    assert scope["needs_human"] == {}
    assert scope["judgement"] in {"OK", "WARNING", "FAIL"} and scope["sed"] > 0
    assert isinstance(scope["report_id"], int) and scope["report_url"].startswith("/w/")
    assert isinstance(scope["tag_candidates"], list)


def test_환원_단계의_인자가_앞_단계_저장값으로_채워진다(spec, real):
    """통째 치환(`"{{ap_part}}"`)이 객체를 **문자열로 만들지 않는지** — 만들면 환원 도구가 E100 으로 멈춘다."""
    scope = {"ap_part": real["odb_ap_part"], "pkg_part": real["odb_pkg_part"],
             "interposer": real["odb_interposer"], "pkg_type": "WLP", "ball_size": "147/250",
             "board_type": "INT"}
    args = template.substitute(spec.steps[3].args, scope)
    assert isinstance(args["ap_part"], dict) and isinstance(args["interposer"], dict)
    assert args["human"] == {"pkg_type": "WLP", "ball_size": "147/250", "board_type": "INT"}


def test_사람_칸은_모두_변수로_선언돼_있다(spec):
    declared = {v.key for v in spec.vars}
    human = spec.steps[3].args["human"]
    refs = {v.strip("{} ") for v in human.values()}
    assert refs <= declared and set(human) == {"pkg_type", "ball_size", "board_type"}


def test_환원의_notes_가_실행_기록으로_올라온다(real):
    """AP·PKG 같은 잡 조건·INT 규칙 미검증 같은 경고가 **사라지지 않는지**(PLAN §10-5)."""
    v = judge(is_error=False, text=_text(real["reduce"]))
    notes = collect_notes(v.parsed)
    assert notes.get("warnings"), f"환원 도구의 warnings 가 실행 기록으로 안 올라온다: {sorted(notes)}"
    assert any("같은 잡" in n for n in notes["warnings"])


def test_실측이_아닌_고정물은_표시돼_있다(real):
    assert real["odb_ap_part"].get("_synthetic") is True
    assert "_synthetic" not in real["odb_pkg_part"]


# ── 보고서 ──────────────────────────────────────────────────────────────────────────────
def test_보고서_초안은_사람이_확인하고_태그_적용은_절차에_없다(spec):
    """태그 적용(add_report_tags)은 must-gate 인데, 게이트는 인자 지문에 묶인 승인/거절뿐이고 select 는 하나만
    고른다 — 사람이 후보 **여럿**을 골라 넘기는 길이 없다. 그래서 RA 화면에서 고른다(씨앗 머리 주석)."""
    create = next(st for st in spec.steps if st.tool == "create_report_draft")
    assert create.gate == "human"
    assert "add_report_tags" not in [st.tool for st in spec.steps]
    suggest = next(st for st in spec.steps if st.tool == "suggest_report_tags")
    assert suggest.gate is None   # 후보만 — 저장하지 않는다


def test_본문_위젯이_dry_run_으로_확인한_그_모양이다(spec, real):
    """위젯 형식이 틀리면 RA 는 블록을 **조용히 버린다**(경고만 오고 초안은 만들어진다). 씨앗의 위젯을
    바꾸면 dry_run 을 다시 돌려 고정물을 갱신하라 — 안 그러면 이 검사가 멈춘다."""
    dry = real["ra_create_dry_run"]
    assert dry["dry_run"] is True and dry["warnings"] == []
    create = next(st for st in spec.steps if st.tool == "create_report_draft")
    assert {b["id"] for b in create.args["extra_blocks"]} == set(dry["pages"][0]["blocks"])
    assert [b["type"] for b in create.args["extra_blocks"]] == ["key_value", "rich_text"]


def test_버려진_위젯_경고가_실행_기록으로_올라온다(real):
    body = {**real["ra_create"], "warnings": ["블록 result: 형식을 맞추지 못해 비웠다"]}
    v = judge(is_error=False, text=_text(body))
    assert v.ok
    assert collect_notes(v.parsed).get("warnings"), "버려진 위젯이 조용히 사라진다"


def test_RA_응답은_봉투를_벗긴_모양이라_save_경로에_data_가_없다(spec):
    """RA MCP 는 API 봉투(success·data)를 벗긴다(mcp_server `_unwrap`) — R1 의 반대 방향 함정."""
    for st in spec.steps:
        if st.backend == "reportarchive":
            assert not any(p.startswith("data.") for p in (st.save or {}).values()), st.tool
