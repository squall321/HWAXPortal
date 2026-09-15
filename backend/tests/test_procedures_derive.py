# 실행 기록 → 절차 초안 (PLAN §9-2·§9-9)
#
# 어려운 것은 "어느 인자가 변수인가" 다. 키워드 목록으로 정하면 그게 하드코딩이다.
# 대신 **값이 어디서 왔는지**를 찾는다 — 앞 결과에 있으면 체인, 사람 말에 있으면 변수,
# 둘 다 아니면 **모른다**(상수로 두고 사람에게 묻는다).
#
# 세 번째가 요점이다. 지어낸 변수는 절차를 조용히 망친다.
import pytest

from app.procedures import derive
from app.procedures.models import ProcedureSpec, validate_spec


# ── 값이 어디서 왔나 ─────────────────────────────────────────────────────
def test_경로를_역으로_찾는다():
    body = {"parts": [{"for_bending_analysis": {"bend_radius_mm": 6.0, "thickness_mm": 1.2}}]}
    p = derive.find_path(body, 6.0)
    assert p == "parts[0].for_bending_analysis.bend_radius_mm"


def test_찾은_경로는_실제로_풀린다():
    """짐작한 경로를 주면 못 도는 절차가 나온다 — 찾은 것은 대조해서 준다."""
    from app.procedures import template

    body = {"a": {"b": [{"c": "긴값입니다"}]}}
    p = derive.find_path(body, "긴값입니다")
    assert template.extract(body, p) == "긴값입니다"


def test_없으면_비슷한_경로를_주지_않는다():
    assert derive.find_path({"a": 1}, "없는값") is None


def test_짧은_값은_경로를_안_믿는다():
    """`1`·`ok` 같은 값은 아무 데나 있다 — 우연한 일치로 체인을 만들면 안 된다."""
    got = derive._where_from("ok", [{"tool": "t", "args": {}, "result": {"status": "ok"}}], "")
    assert got["kind"] == "constant" and "짧아" in got["why"]


def test_화면이_문자열로_보낸_숫자도_같게_본다():
    """`"6.0"` 과 `6.0` 은 같은 값이다 — 화면은 문자열밖에 못 보낸다."""
    assert derive.find_path({"r": 6.0}, "6.0") == "r"


# ── 초안 ─────────────────────────────────────────────────────────────────
TB = {"bend_profile": "heax-step_forge",
      "solve_prescribed_curvature": "heax-laminate_analyzer_mcp"}


def test_R1_모양을_넣으면_R1_체인이_나온다():
    """**이것이 도출의 요점이다.** ①이 읽은 굽힘반경이 ③의 인자로 쓰였다는 사실을
    사람이 적어 주지 않아도, 값이 거기 있다는 것으로 알아낸다."""
    steps = [
        {"tool": "bend_profile", "args": {"project_id": "R1-예제", "part": "UBEND_1"},
         "result": {"parts": [{"for_bending_analysis": {"bend_radius_mm": 6.0,
                                                        "thickness_mm": 1.2}}]}},
        {"tool": "solve_prescribed_curvature",
         "args": {"bend_radius": 6.0, "bend_axis": "x", "width": "free"},
         "result": {"status": "ok"}},
    ]
    got = derive.draft(steps, tool_backend=TB, asked="R1-예제 의 UBEND_1 굽힘 수명 봐줘")

    s1, s2 = got["spec"]["steps"]
    assert s1["backend"] == "heax-step_forge"
    # ① 이 굽힘반경을 save 하고 ③ 이 그걸 쓴다
    assert list(s1["save"].values()) == ["parts[0].for_bending_analysis.bend_radius_mm"]
    name = list(s1["save"])[0]
    assert s2["args"]["bend_radius"] == "{{%s}}" % name

    # 사람이 대화에서 준 값은 변수가 된다
    keys = {v["label"] for v in got["spec"]["vars"]}
    assert {"project_id", "part"} <= keys, got["spec"]["vars"]


def test_모르는_값은_상수로_두고_사람에게_묻는다():
    """`width="free"` 는 앞 결과에도 사람 말에도 없다. 변수로 지어내면 안 된다."""
    steps = [{"tool": "solve_prescribed_curvature",
              "args": {"width": "free", "bend_axis": "x"}, "result": {}}]
    got = derive.draft(steps, tool_backend=TB, asked="굽힘 좀 봐줘")
    assert got["spec"]["steps"][0]["args"]["width"] == "free"
    asked = {r["arg"] for r in got["needs_human"]}
    assert "width" in asked, "사람에게 물을 자리로 안 올렸다"


def test_어느_앱인지_모르면_결손으로_잡는다():
    """지어내지 않는다 — 챗 기록에는 앱이 없다(PLAN §9-8)."""
    got = derive.draft([{"tool": "모르는도구", "args": {}, "result": {}}], tool_backend={})
    assert got["spec"]["steps"][0]["backend"] == ""
    assert any(g["kind"] == "backend_unknown" for g in got["gaps"])


def test_인자가_글이면_결손으로_잡는다():
    """잘린 미리보기로 만든 절차는 인자가 손상돼 있다 — 조용히 넘기면 안 된다."""
    got = derive.draft([{"tool": "t", "args": "search_voc(발열) 를 불렀다", "result": {}}],
                       tool_backend={"t": "x"})
    assert any(g["kind"] == "args_not_structured" for g in got["gaps"])


def test_이름이_겹치면_갈라_준다():
    """변수와 save 가 같은 이름 공간을 쓴다 — 겹치면 뒤엣것이 앞엣것을 조용히 덮는다."""
    steps = [
        {"tool": "a", "args": {"part": "UBEND_1"}, "result": {"part": "다른부품이름"}},
        {"tool": "b", "args": {"part": "다른부품이름"}, "result": {}},
    ]
    got = derive.draft(steps, tool_backend={"a": "x", "b": "x"}, asked="UBEND_1 봐줘")
    used = [v["key"] for v in got["spec"]["vars"]] + list(got["spec"]["steps"][0].get("save", {}))
    assert len(used) == len(set(used)), f"이름이 겹쳤다: {used}"


def test_초안은_그대로_저장되지_않는다():
    """`backend` 가 빈 초안은 저장 검증에 걸려야 한다 — 자동 저장 금지의 실질이다."""
    got = derive.draft([{"tool": "t", "args": {}, "result": {}}], tool_backend={})
    with pytest.raises(Exception):
        ProcedureSpec.model_validate(got["spec"])


def test_제대로_갖춰진_초안은_저장_검증을_통과한다():
    got = derive.draft(
        [{"tool": "list_parts", "args": {"project_id": "과제이름"}, "result": {}}],
        tool_backend={"list_parts": "heax-step_forge"}, asked="과제이름 부품 보여줘")
    spec = ProcedureSpec.model_validate(got["spec"])
    hard = [e for e in validate_spec(spec) if not e.startswith("warn:")]
    assert hard == [], hard


def test_근거가_인자마다_달린다():
    """왜 변수로 봤는지가 없으면 사람이 확정할 수 없다."""
    got = derive.draft([{"tool": "t", "args": {"a": "긴값하나", "b": "다른긴값"}, "result": {}}],
                       tool_backend={"t": "x"}, asked="긴값하나 로 해줘")
    kinds = {r["arg"]: r["kind"] for r in got["reasons"]}
    assert kinds == {"a": "asked", "b": "constant"}
    assert all(r.get("why") for r in got["reasons"])


# ── 변수의 뜻은 도구 스키마에서 온다 (지어내지 않는다) ───────────────────
SCHEMAS = {
    "solve_prescribed_curvature": {"properties": {
        "bend_radius": {"type": "number",
                        "description": "굽힘반경, 길이 단위. unit_system 에 묶인다"},
        "width": {"type": "string", "enum": ["free", "constrained"],
                  "description": "폭 구속 — free(M_y=0) vs constrained(κ_y=0). 답이 9.6% 갈린다",
                  "default": "free"},
        "bend_axis": {"type": "string"},   # 설명이 없다 — 결손이어야 한다
    }},
}


def test_변수_설명이_도구_스키마에서_온다():
    """절차는 사실상 도구다 — 변수가 그 입력 스키마다. 설명을 지어낼 필요가 없다."""
    steps = [{"tool": "solve_prescribed_curvature",
              "args": {"bend_radius": 6.0}, "result": {}}]
    got = derive.draft(steps, tool_backend={"solve_prescribed_curvature": "x"},
                       asked="굽힘반경 6.0 으로 봐줘", tool_schemas=SCHEMAS)
    v = got["spec"]["vars"][0]
    assert "굽힘반경, 길이 단위" in v["why"], v
    assert "1단계" in v["why"] and "bend_radius" in v["why"], "어디에 쓰이는지가 없다"
    assert v["type"] == "number", "스키마의 형을 안 썼다"


def test_허용값이_있으면_고르는_칸이_된다():
    """`free|constrained` 는 답이 9.6% 갈리는 자리다 — 자유 입력으로 두면 오타가 조용히 산다."""
    steps = [{"tool": "solve_prescribed_curvature",
              "args": {"width": "constrained"}, "result": {}}]
    got = derive.draft(steps, tool_backend={"solve_prescribed_curvature": "x"},
                       asked="폭은 constrained 로", tool_schemas=SCHEMAS)
    v = got["spec"]["vars"][0]
    assert v["type"] == "enum" and v["values"] == ["free", "constrained"]
    assert "9.6%" in v["why"], "왜 중요한지가 안 실렸다"
    assert "기본값" in v["why"], "도구 기본값이 안 실렸다"


def test_설명_없는_인자는_결손으로_올린다():
    """⚠ 설명 없는 인자는 **그 앱의 문서 결손**이다. 사람도 LLM 도 그 칸의 뜻을 알 수 없다.
    다만 인자마다가 아니라 **한 줄로 모아** 올린다(1%만 설명이 있어서 그러지 않으면
    목록이 그것으로 덮인다)."""
    steps = [{"tool": "solve_prescribed_curvature",
              "args": {"bend_axis": "x축으로"}, "result": {}}]
    got = derive.draft(steps, tool_backend={"solve_prescribed_curvature": "x"},
                       asked="x축으로 굽혀", tool_schemas=SCHEMAS)
    agg = [g for g in got["gaps"] if g["kind"] == "args_undocumented"]
    assert agg and agg[0]["count"] == 1
    assert any("bend_axis" in w for w in agg[0]["where"])
    v = got["spec"]["vars"][0]
    assert "어디에도 없다" in v["why"], "모르면서 아는 척하면 안 된다"
    assert "_undocumented" not in v, "내부 표식이 밖으로 샜다"


def test_실제로_쓰인_값이_예시로_남는다():
    """기본값이 아니다 — 사람이 눌러야 들어간다(Var.example 규약)."""
    steps = [{"tool": "solve_prescribed_curvature", "args": {"bend_radius": 6.0}, "result": {}}]
    got = derive.draft(steps, tool_backend={"solve_prescribed_curvature": "x"},
                       asked="6.0 으로", tool_schemas=SCHEMAS)
    assert got["spec"]["vars"][0]["example"] == 6.0


def test_여러_단계에_쓰이면_그_자리를_전부_적는다():
    """한 칸이 세 단계를 움직이는데 한 단계만 적혀 있으면 영향 범위를 오해한다."""
    steps = [
        {"tool": "solve_prescribed_curvature", "args": {"width": "constrained"}, "result": {}},
        {"tool": "solve_prescribed_curvature", "args": {"width": "constrained"}, "result": {}},
    ]
    got = derive.draft(steps, tool_backend={"solve_prescribed_curvature": "x"},
                       asked="폭은 constrained", tool_schemas=SCHEMAS)
    why = got["spec"]["vars"][0]["why"]
    assert "1단계" in why and "2단계" in why, why


def test_살찐_변수가_저장_검증을_통과한다():
    """스키마에서 끌어온 값이 절차 규격에 안 맞으면 도출이 못 쓰는 초안을 낸다."""
    steps = [{"tool": "solve_prescribed_curvature",
              "args": {"width": "free", "bend_radius": 6.0}, "result": {}}]
    got = derive.draft(steps, tool_backend={"solve_prescribed_curvature": "heax-x"},
                       asked="free 로 6.0", tool_schemas=SCHEMAS)
    spec = ProcedureSpec.model_validate(got["spec"])
    assert [e for e in validate_spec(spec) if not e.startswith("warn:")] == []


# ── 절차 → 도구 계약 ─────────────────────────────────────────────────────
def test_절차_변수가_도구_입력_스키마가_된다():
    """절차는 사실상 도구다 — 계약을 같은 모양으로 내면 부르는 쪽이 같아진다."""
    spec = {"title": "t", "vars": [
        {"key": "project_id", "label": "과제", "type": "string", "why": "어느 과제인가"},
        {"key": "width_mode", "label": "폭", "type": "enum", "values": ["free", "constrained"],
         "why": "답이 9.6% 갈린다", "example": "free"},
        {"key": "memo", "label": "비고", "type": "string", "required": False},
    ], "steps": []}
    sc = derive.to_input_schema(spec)
    assert sc["type"] == "object" and sc["additionalProperties"] is False
    assert sc["required"] == ["project_id", "width_mode"], "선택 변수가 필수로 갔다"
    assert sc["properties"]["width_mode"]["enum"] == ["free", "constrained"]
    assert "9.6%" in sc["properties"]["width_mode"]["description"]
    assert sc["properties"]["width_mode"]["examples"] == ["free"]
    assert sc["properties"]["memo"]["type"] == "string"


def test_json_변수는_object_로_나간다():
    sc = derive.to_input_schema({"vars": [{"key": "laminate", "type": "json", "why": "적층"}]})
    assert sc["properties"]["laminate"]["type"] == "object"


# ── 사람이 확정한다 — 상수를 변수로 올린다 ───────────────────────────────
def _two_step_draft():
    steps = [
        {"tool": "solve_prescribed_curvature", "args": {"width": "constrained"}, "result": {}},
        {"tool": "solve_prescribed_curvature", "args": {"width": "constrained"}, "result": {}},
    ]
    return derive.draft(steps, tool_backend={"solve_prescribed_curvature": "heax-x"},
                        asked="", tool_schemas=SCHEMAS)


def test_고른_상수가_변수가_된다():
    d = _two_step_draft()
    assert d["spec"]["steps"][0]["args"]["width"] == "constrained"
    got, warns = derive.promote(d["spec"], [{"step": 1, "arg": "width", "key": "width_mode"}],
                                tool_schemas=SCHEMAS)
    assert got["steps"][0]["args"]["width"] == "{{width_mode}}"
    v = next(v for v in got["vars"] if v["key"] == "width_mode")
    assert v["type"] == "enum" and v["values"] == ["free", "constrained"]
    assert "9.6%" in v["why"], "스키마 설명이 안 실렸다"


def test_같은_인자_같은_값은_전부_함께_올린다():
    """**한 자리만 바꾸면 나머지는 옛 값으로 돈다.** 절차가 조용히 어긋나는 자리다."""
    d = _two_step_draft()
    got, warns = derive.promote(d["spec"], [{"step": 1, "arg": "width", "key": "w"}],
                                tool_schemas=SCHEMAS)
    assert [st["args"]["width"] for st in got["steps"]] == ["{{w}}", "{{w}}"]
    assert any("2곳" in w for w in warns), f"함께 바뀐다는 사실을 안 알렸다: {warns}"


def test_원본_초안을_안_건드린다():
    d = _two_step_draft()
    derive.promote(d["spec"], [{"step": 1, "arg": "width", "key": "w"}], tool_schemas=SCHEMAS)
    assert d["spec"]["steps"][0]["args"]["width"] == "constrained", "원본이 바뀌었다"


def test_못_올린_것은_조용히_건너뛰지_않는다():
    d = _two_step_draft()
    got, warns = derive.promote(d["spec"], [
        {"step": 9, "arg": "width"}, {"step": 1, "arg": "없는인자"}], tool_schemas=SCHEMAS)
    assert len(warns) == 2 and all("건너뛰었다" in w for w in warns)
    assert not got.get("vars"), "못 올렸는데 변수가 생겼다"


def test_이미_변수인_칸은_다시_안_올린다():
    d = _two_step_draft()
    once, _ = derive.promote(d["spec"], [{"step": 1, "arg": "width", "key": "w"}],
                             tool_schemas=SCHEMAS)
    twice, warns = derive.promote(once, [{"step": 1, "arg": "width", "key": "w2"}],
                                  tool_schemas=SCHEMAS)
    assert any("이미 변수다" in w for w in warns)
    assert [v["key"] for v in twice.get("vars", [])] == ["w"]


def test_사람이_준_이름과_설명이_이긴다():
    d = _two_step_draft()
    got, _ = derive.promote(d["spec"], [{"step": 1, "arg": "width", "key": "지그",
                                         "label": "지그 구속", "why": "우리 지그는 구속이다"}],
                            tool_schemas=SCHEMAS)
    v = got["vars"][0]
    assert v["label"] == "지그 구속"
    # 사람이 쓴 설명은 **살아남고**, 쓰이는 자리가 함께 적힌다(둘 다 필요하다)
    assert "우리 지그는 구속이다" in v["why"]
    assert "1단계" in v["why"] and "2단계" in v["why"], v["why"]


def test_못_쓰는_이름은_조용히_바꾸지_않고_말한다():
    """`지그` 는 규칙상 쓸 글자가 하나도 없어 종전엔 **조용히 `arg`** 가 됐다.
    조용히 다른 이름이 되는 것이 이 리포가 싫어하는 모양이다."""
    d = _two_step_draft()
    got, warns = derive.promote(d["spec"], [{"step": 1, "arg": "width", "key": "지그"}],
                                tool_schemas=SCHEMAS)
    assert got["vars"][0]["key"] == "width", "인자 이름으로 안 떨어졌다"
    assert any("못 쓴다" in w for w in warns), f"조용히 바꿨다: {warns}"


# ── 인자 설명이 없을 때 — 도구 산문에서 **인용**한다 ─────────────────────
PROSE = {"find_parts": "조건으로 파트 찾기 — 이름 글롭·재질·부피 범위·메시 유무.\n\n"
                       "    `name` 은 글롭이다(`bolt_*`). 규칙 파일과 같은 매칭을 쓴다."}


def test_스키마에_없으면_도구_산문에서_인용한다():
    """이 허브의 인자 설명은 1,348개 중 **15개(1%)** 뿐이다(실측). 대신 그 내용이 도구
    산문에 있다 — `name` 이 글롭이라는 사실은 그 문장에만 있다."""
    got = derive.draft([{"tool": "find_parts", "args": {"name": "*BRKT*"}, "result": {}}],
                       tool_backend={"find_parts": "heax-step_forge"},
                       asked="*BRKT* 로 찾아줘", tool_schemas={}, tool_desc=PROSE)
    why = got["spec"]["vars"][0]["why"]
    assert "글롭" in why, why
    assert "(도구 설명에서)" in why, "인용이라는 사실을 안 밝혔다"


def test_산문에도_없으면_없다고_한다():
    got = derive.draft([{"tool": "find_parts", "args": {"material": "CFRP소재"}, "result": {}}],
                       tool_backend={"find_parts": "x"}, asked="CFRP소재 로",
                       tool_schemas={}, tool_desc=PROSE)
    assert "어디에도 없다" in got["spec"]["vars"][0]["why"]


def test_인용은_그_인자를_말하는_문장만_가져온다():
    """⚠ 지어내지 않는다 — 인용이다. 아무 문장이나 붙이면 **틀린 설명**이 된다."""
    assert derive.from_prose(PROSE["find_parts"], "zzz") == ""
    assert "글롭" in derive.from_prose(PROSE["find_parts"], "name")


def test_설명_없는_인자는_한_줄로_모아_낸다():
    """⚠ **99%에서 울리는 검출기는 검출기가 아니다.** 인자마다 결손을 올리면 목록이
    그것으로 덮여 진짜 결손이 묻힌다."""
    steps = [{"tool": "t", "args": {"a": "긴값하나", "b": "다른긴값", "c": "또다른값"},
              "result": {}}]
    got = derive.draft(steps, tool_backend={"t": "x"},
                       asked="긴값하나 다른긴값 또다른값", tool_schemas={}, tool_desc={})
    agg = [g for g in got["gaps"] if g["kind"] == "args_undocumented"]
    assert len(agg) == 1, f"인자마다 올렸다: {got['gaps']}"
    assert agg[0]["count"] == 3 and len(agg[0]["where"]) == 3


# ── 우연한 일치를 값으로 착각하던 자리(2026-09-15 감사) ────────────────────
def test_앞의_0_이_있는_번호는_같은_수가_아니다():
    """`"0012"` 와 `12` — 로트·도면·파트 번호에서 앞의 0 은 뜻을 갖는다.

    느슨하게 보면 초안이 "앞 결과의 `count` 에 같은 값이 있다" 며 체인을 만들고,
    재생 때 정수 `12` 를 넣어 **다른 대상**을 부른다. 이유 문구는 같다고 단언한다.
    """
    got = derive.draft([
        {"tool": "list_lots", "args": {}, "result": {"count": 12}},
        {"tool": "get_lot", "args": {"lot": "0012"}, "result": {}},
    ], tool_backend={"list_lots": "a", "get_lot": "a"})
    assert "{{" not in str(got["spec"]["steps"][1]["args"]["lot"]), got["reasons"]
    assert not got["spec"]["steps"][0].get("save")


def test_같은_수를_같은_표기로_쓰면_이어진다():
    """짝 검사 — 너무 세게 조이면 진짜 체인을 놓친다."""
    got = derive.draft([
        {"tool": "list_lots", "args": {}, "result": {"lot_id": 4210}},
        {"tool": "get_lot", "args": {"lot": "4210"}, "result": {}},
    ], tool_backend={"list_lots": "a", "get_lot": "a"})
    assert got["spec"]["steps"][1]["args"]["lot"].startswith("{{")


def test_사람_말_안의_조각_일치는_인정하지_않는다():
    """`12.5` 가 `"2012.5월"` 안에서 잡혔다 — '사람이 쓴 말에 있다' 가 거짓이 된다."""
    r = derive._where_from(12.5, [], "2012.5월에 측정했다")
    assert r["kind"] == "constant", r
    assert derive._where_from(12.5, [], "두께 12.5 mm 로")["kind"] == "asked"


# ── 사람이 고른 이름이 말없이 바뀌던 자리 ─────────────────────────────────
def _one_const():
    return {"title": "t", "vars": [],
            "steps": [{"backend": "a", "tool": "t1", "args": {"lot": "A-1000"}},
                      {"backend": "a", "tool": "t2", "args": {"jig": "J-2000"}}]}


def test_이름이_요청과_달라지면_전부_말한다():
    spec, warns = derive.promote(_one_const(), [{"step": 2, "arg": "jig", "key": "지그2"}])
    keys = [v["key"] for v in spec["vars"]]
    assert warns, f"`지그2` 가 {keys} 로 바뀌었는데 아무 말이 없다"
    assert any("지그2" in w for w in warns)


def test_이미_있는_이름은_따로_만들되_말한다():
    spec = _one_const()
    spec["vars"] = [{"key": "lot", "label": "로트", "type": "string", "required": True}]
    spec["steps"][0]["args"]["lot"] = "{{lot}}"
    out, warns = derive.promote(spec, [{"step": 2, "arg": "jig", "key": "lot"}])
    assert any("이미 있는 변수" in w for w in warns), warns
    assert sorted(v["key"] for v in out["vars"]) == ["lot", "lot_2"]


def test_그대로_쓸_수_있는_이름은_조용하다():
    """짝 검사 — 아무 때나 경고하면 경고가 소음이 된다."""
    _spec, warns = derive.promote(_one_const(), [{"step": 1, "arg": "lot", "key": "lot_no"}])
    assert warns == [], warns
