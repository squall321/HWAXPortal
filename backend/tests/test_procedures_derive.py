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
