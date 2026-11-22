# Claude 워크플로의 심의 주제 — 대화 저장(save_conversation · save-delib-conversation.py)에만 실리고 좌석 · 의장 · RA 에는 안 가는지(과제 인사이트 M2)
"""docs/project-insight-graph contracts §5 · PLAN §4.7 (b).
  · hwax-deliberate.js 는 subject(받는 칸 넷)를 대화 저장 지시에만 싣고 결과에 subject · chairTemplate 을 낸다. 리스크 심사면 싣지 않는다.
  · 다단 워크플로(hwax-sim-deliberate.js · hwax-test-plan.js)는 자식에 그대로 넘긴다 — 대화를 남기는 단만 카드가 된다.
  · infra/scripts/save-delib-conversation.py 는 결과의 subject · chairTemplate 을 ConvCreate 에 싣는다(리스크 심사면 싣지 않는다).
스크립트를 스텁 런타임에서 실제로 돌린다(tests/test_infra_pipeline_notices 의 구동기).
"""
import importlib.util
import json
from pathlib import Path

import pytest

from tests.test_delib_pipeline_js import _run as _run_with_children
from tests.test_infra_pipeline_notices import _DELIB, _SEATS, _run

_SIM = "infra/pipeline/hwax-sim-deliberate.js"
_TEST = "infra/pipeline/hwax-test-plan.js"
KEY = "알파 개발_C2"
SUBJECT = {"sp_task": KEY, "round": "dv1", "text": "알파 1차", "artifacts": [{"kind": "ecad", "id": "abcdef0123456789"}]}


def _full(**kw) -> dict:
    args = {"question": "힌지 리브를 보강할 것인가", "personas": _SEATS, "rounds": 2, "saveConversation": True, "saveReport": True, **kw}
    return _run(_DELIB, args)


def _call(out: dict, label: str) -> str:
    return next(c["prompt"] for c in out["calls"] if c["label"] == label)


def test_주제는_대화_저장에만_실리고_좌석_의장_RA_에는_가지_않는다():
    out = _full(subject={**SUBJECT, "sp_state": "confirmed", "junk": 1, "text": ""})
    save = _call(out, "conv-save")
    want = {k: v for k, v in SUBJECT.items() if k != "text"}
    assert f"subject={json.dumps(want, ensure_ascii=False, separators=(',', ':'))}" in save and 'chair_template="default"' in save
    assert "sp_state" not in save and "junk" not in save, "받는 칸 넷만 · 빈 값은 뺀다(확인 상태는 서버가 적는다)"
    others = [c for c in out["calls"] if c["label"] != "conv-save"]
    assert others and not [c["label"] for c in others if KEY in c["prompt"]], "좌석 · 의장 · RA 저장에는 주제가 없다"
    res = out["result"]
    assert res["subject"] == want and res["chairTemplate"] == "default"


def test_리스크_심사와_주제_없는_심의는_대화_저장이_종전_그대로다():
    for kw in ({"chairTemplate": "risk-review", "subject": SUBJECT}, {}, {"subject": "문자열"}, {"subject": {"junk": 1}}):
        out = _full(**kw)
        save = _call(out, "conv-save")
        assert "subject=" not in save and "chair_template=" not in save, kw
        assert out["result"]["subject"] is None


def test_다단_워크플로는_자식에_주제를_넘기고_단마다_주제와_틀을_낸다():
    out = _run_with_children(_SIM, {"question": "화두", "personas": _SEATS, "rounds": 2, "simRounds": 2, "saveConversation": True,
                      "simPersonas": [{"key": "cae-a", "role": "해석"}], "subject": SUBJECT})
    assert [a.get("subject") for a in out["childArgs"]] == [SUBJECT, SUBJECT]
    res = out["result"]
    assert res["mechanism"]["subject"] == SUBJECT and res["mechanism"]["chairTemplate"] == "mechanism"
    assert res["simPlan"]["subject"] == SUBJECT and res["simPlan"]["chairTemplate"] == "sim-plan"
    saves = [c["prompt"] for c in out["calls"] if c["label"] == "conv-save"]
    assert len(saves) == 1 and 'chair_template="sim-plan"' in saves[0], "대화를 남기는 단(2단)만 카드가 된다"
    tp = _run_with_children(_TEST, {"question": "물성 확보", "personas": _SEATS, "rounds": 2, "saveConversation": False, "subject": SUBJECT})
    assert tp["childArgs"][0]["subject"] == SUBJECT and tp["result"]["chairTemplate"] == "test-plan"


def _script():
    path = Path(__file__).resolve().parents[2] / "infra" / "scripts" / "save-delib-conversation.py"
    spec = importlib.util.spec_from_file_location("save_delib_conversation_insight", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_결정적_저장_스크립트는_결과의_주제와_틀을_함께_싣는다(monkeypatch, tmp_path):
    mod = _script()
    assert mod._insight({"subject": SUBJECT, "chairTemplate": "sim-plan"}) == {"subject": SUBJECT, "chair_template": "sim-plan"}
    assert mod._insight({"subject": SUBJECT, "chairTemplate": "risk-review"}) == {}
    assert mod._insight({"subject": None, "chairTemplate": "default"}) == {} and mod._insight({}) == {}
    sent = []

    def fake_req(base, pat, path, payload):
        sent.append((path, payload))
        return {"id": "c-1", "insight": {"id": "ins:wf:c-1", "status": "draft"}} if path == "/agent/conversations" else {"ok": True}
    monkeypatch.setattr(mod, "_req", fake_req)
    rounds = [[{"persona": "mech-a", "final_position": "최종"}]]
    res = {"question": "화두", "mechanism": {"rounds": rounds, "decision": "1단", "subject": SUBJECT, "chairTemplate": "mechanism"},
           "simPlan": {"rounds": rounds, "decision": "2단", "subject": SUBJECT, "chairTemplate": "sim-plan"}}
    f = tmp_path / "res.json"
    f.write_text(json.dumps({"result": res}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("HWAX_PAT", "pat-EXAMPLE")
    monkeypatch.setattr("sys.argv", ["x", str(f)])
    assert mod.main() == 0
    creates = [p for path, p in sent if path == "/agent/conversations"]
    assert [(c["subject"], c["chair_template"]) for c in creates] == [(SUBJECT, "mechanism"), (SUBJECT, "sim-plan")]


_ROUNDS = [[{"persona": "mech-a", "final_position": "최종"}]]


@pytest.mark.parametrize("res", [{"question": "q", "rounds": _ROUNDS, "decision": "d"},
                                 {"question": "q", "rounds": _ROUNDS, "decision": "d", "subject": SUBJECT, "chairTemplate": "risk-review"}])
def test_결정적_저장_스크립트는_주제가_없거나_리스크_심사면_종전_본문이다(monkeypatch, tmp_path, res):
    mod = _script()
    sent = []
    monkeypatch.setattr(mod, "_req", lambda base, pat, path, payload: sent.append(payload) or {"id": "c-1"})
    f = tmp_path / "res.json"
    f.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("HWAX_PAT", "pat-EXAMPLE")
    monkeypatch.setattr("sys.argv", ["x", str(f)])
    assert mod.main() == 0
    assert set(sent[0]) == {"title", "kind", "source", "messages"}


def test_리스크_심사_좌석의_D18_줄은_과제_인사이트_도구와_주제_찾기를_막는다():
    """Claude 워크플로의 리스크 심사 좌석은 그 사람 PAT 의 게이트웨이 도구를 다 쓰고 지키는 것은 D-18 한 줄뿐이다 — M2 의 새 도구(insight_find ·
    insight_get · risk_find_projects_by_subject)도 그 줄이 이름으로 막는다(반대 검토 11-02 의 5). 리스크 심사가 아니면 줄이 없다."""
    out = _run(_DELIB, {"question": "[리스크심사 P1 T-1] 판정하라", "personas": _SEATS, "rounds": 2, "chairTemplate": "risk-review",
                        "saveConversation": False, "saveReport": False})
    seats = [c["prompt"] for c in out["calls"] if "[D-18]" in c["prompt"]]
    assert seats, "리스크 심사 좌석에 D-18 줄이 있다"
    for name in ("insight_find", "insight_get", "risk_find_projects_by_subject"):
        assert all(name in p for p in seats), name
    plain = _full()
    assert not [c for c in plain["calls"] if "[D-18]" in c["prompt"]]



# ── M3 — 앞선 과제 인사이트를 근거로(PLAN §7.1) ──────────────────────────────────────────────────────────────────
_INS_EV = [{"source": "앞선 인사이트 — 검증 대상, 독립 근거 아님", "tool": "insight_get", "args": '{"id": "ins:web:c:r:default"}',
            "result": "앞선 결론 — 리브를 보강한다"},
           {"source": "개인 Claude", "tool": "mcp__hwax__insight_find", "result": "찾기 묶음 — 앞선 결론 둘"},
           {"source": "StepForge", "tool": "find_part", "result": "힌지 2종"}]


def test_리스크_심사_워크플로는_과제_인사이트_근거를_좌석에_주지_않고_뺐다고_남긴다():
    """엔진의 받침(HWAXAgentServer deliberation._resolve_opts)과 같은 거름이다 — 의장이 리스크 심사면 도구 칸이 과제 인사이트인 근거 항목을 뺀다
    (D-18). 워크플로의 근거 블록은 코드가 짓는다 — 좌석 도구와 달리 지시가 아니라 강제다. 다른 의장은 그대로 싣는다."""
    out = _full(chairTemplate="risk-review", evidence=_INS_EV, saveConversation=False, saveReport=False)
    prompts = "\n".join(c["prompt"] for c in out["calls"])
    assert "앞선 결론" not in prompts and "힌지 2종" in prompts
    om = [x for x in out["result"]["evidenceOmitted"] if x["source"] == "과제 인사이트 근거 거름"]
    assert len(om) == 1 and om[0]["count"] == 2 and "D-18" in om[0]["text"] and "앞선 결론" not in om[0]["text"]
    plain = _full(evidence=_INS_EV, saveConversation=False, saveReport=False)
    assert "앞선 결론 — 리브를 보강한다" in "\n".join(c["prompt"] for c in plain["calls"])
    assert not [x for x in plain["result"]["evidenceOmitted"] if x["source"] == "과제 인사이트 근거 거름"]


# 과제 인사이트 근거인지 가리는 규칙은 세 곳에 있다 — 엔진(HWAXAgentServer deliberation._insight_evidence_tool) · 포털(app.insights.cards.insight_tool) ·
# 워크플로(hwax-deliberate.js isInsightEvidence). 갈리면 한쪽 길로 샌다(반대 검토 11-22 M3 — 범용 실행기 invoke_tool · 접두가 붙은 이름 · 머리의
# BOM 과 정보 분리 문자에서 갈렸다). 같은 입력을 셋에 넣어 같은 답인지 본다. (도구 칸, 인자, 과제 인사이트인가)
INSIGHT_RULE_TABLE = [
    ("insight_get", '{"id": "ins:web:c:r:default"}', True), ("insight_find", {"sp_task": "알파"}, True), (" Insight_Get ", None, True),
    ("mcp__hwax__insight_find", None, True), ("gateway.insight_get", None, True), ("hwax:insight_find", None, True),
    ("hwax-insight_get", None, True), ("hwax insight_get", None, True), ("hwax_insight_get", None, True), ("(insight_get)", None, True),
    ("\ufeffinsight_get", None, True), ("\x1cinsight_get", None, True), ("INSIGHT_FIND", None, True), ("insight_future_tool", None, True),
    ("get_insight_summary", None, True), ("my_insight_tool", None, True),
    ("find_part", {"q": "힌지"}, False), ("myinsight_get", None, False), ("insights_get", None, False), ("in\u017fight_get", None, False),
    ("\u0131nsight_get", None, False), ("x", None, False),
    ("mcp__hwax__invoke_tool", {"name": "insight_get", "arguments": {"id": "ins:web:c:r:default"}}, True),
    ("invoke_tool", '{"name": "insight_find", "arguments": {"sp_task": "알파"}}', True),
    ("hwax.invoke_tool", "{'name': 'insight_get', 'arguments': {'id': 'ins:wf:z'}}", True),
    ("INVOKE_TOOL", {"name": "Insight_Get"}, True), ("invoke_tool", {"arguments": {"name": "insight_x"}}, True),
    ("invoke_tool", {"name": "find_part", "arguments": {"q": "insight_get"}}, False), ("invoke_tool", None, False), ("invoke_tool", "", False),
    ("invoke_tools", {"name": "insight_get"}, False), ("find_part", {"name": "insight_get"}, False),
]


def _engine_insight_rule():
    """엔진의 판정 함수와 그 상수만 AST 로 떼어 실행한다(엔진 모듈 전체를 읽지 않는다)."""
    import ast
    import re
    eng = Path(__file__).resolve().parents[3] / "HWAXAgentServer" / "deliberation.py"
    if not eng.exists():
        pytest.skip(f"형제 리포 없음: {eng}")
    tree = ast.parse(eng.read_text(encoding="utf-8"))
    want_var = {"_INSIGHT_TOOL_HEAD", "_INSIGHT_EV_TOOL_RE", "_INVOKE_TOOL_RE", "_INVOKE_NAME_RE"}
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "_insight_evidence_tool")
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in want_var for t in n.targets))]
    assert len(body) == len(want_var) + 1, "엔진의 과제 인사이트 판정 모양이 바뀌었다 — 이 시험도 고쳐라"
    ns: dict = {"re": re, "json": json}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(eng), "exec"), ns)  # noqa: S102 — 형제 리포의 우리 코드다
    return ns["_insight_evidence_tool"]


def test_과제_인사이트_근거_판정은_엔진_포털_워크플로가_같은_답을_낸다():
    from app.insights import cards as C
    engine = _engine_insight_rule()
    # 워크플로 — 리스크 심사로 한 번 돌려 어느 항목이 좌석에 가지 않았는지로 판정을 읽는다(근거 블록은 코드가 짓는다)
    ev = [{"source": f"S{i}", "tool": tool, **({"args": args} if args is not None else {}), "result": f"MARK-{i:02d}-END"}
          for i, (tool, args, _want) in enumerate(INSIGHT_RULE_TABLE)]
    out = _full(chairTemplate="risk-review", evidence=ev, saveConversation=False, saveReport=False)
    prompts = "\n".join(c["prompt"] for c in out["calls"])
    for i, (tool, args, want) in enumerate(INSIGHT_RULE_TABLE):
        got = {"엔진": engine(tool, args), "포털": C.insight_tool(tool, args), "워크플로": f"MARK-{i:02d}-END" not in prompts}
        assert got == dict.fromkeys(got, want), (tool, args, got)
    dropped = [x for x in out["result"]["evidenceOmitted"] if x["source"] == "과제 인사이트 근거 거름"]
    assert dropped[0]["count"] == sum(1 for _t, _a, w in INSIGHT_RULE_TABLE if w)
    # 도구 칸이 글이 아니면 과제 인사이트가 아니다(엔진 · 포털 — 워크플로도 그 항목을 좌석에 싣는다)
    for tool in (None, 7, ["insight_get"]):
        assert engine(tool, None) is False and C.insight_tool(tool) is False


@pytest.mark.parametrize("evidence, want", [
    ([{"tool": "insight_get", "args": '{"id": "ins:web:c1:r1:default"}', "result": "가"},
      {"tool": "mcp__hwax__insight_get", "args": {"id": "ins:delib:job-1:sim-plan"}, "result": "나"},
      {"tool": "mcp__hwax__invoke_tool", "args": {"name": "insight_get", "arguments": {"id": "ins:wf:c9"}}, "result": "다"},
      {"tool": "insight_get", "args": '{"id": "ins:web:c1:r1:default"}', "result": "가 — 같은 카드"},
      {"tool": "find_part", "args": "{}", "result": "힌지"}], ["ins:web:c1:r1:default", "ins:delib:job-1:sim-plan", "ins:wf:c9"]),
    ([{"tool": "insight_get", "args": '{"id": "ins:wf:c9"}', "result": "가"}, {"tool": "insight_find", "args": {"sp_task": "알파"}, "result": "묶음"}],
     "unknown"),
    ([{"tool": "insight_get", "args": '{"id": "남의 글"}', "result": "가"}], "unknown"),
    ([{"tool": "insight_get", "result": "인자 없이"}], "unknown"),
    ([{"tool": "invoke_tool", "args": "{'name': 'insight_get', 'arguments': {'id': 'ins:wf:c9'}}", "result": "글로 옮긴 사전은 풀지 않는다"}], "unknown"),
    ([{"tool": "insight_get", "args": json.dumps({"id": f"ins:wf:c{i}"}), "result": "가"} for i in range(61)], "unknown"),
    ([{"tool": "find_part", "args": "{}", "result": "힌지"}], None),
    ([], None),
])
def test_워크플로는_읽은_과제_인사이트를_주제_안에_실어_대화_저장에_넘긴다(evidence, want):
    """워크플로 카드는 근거 표지가 없다 — 앞선 인사이트를 근거로 썼으면 읽은 카드 id(다 알 수 없으면 unknown)를 주제 안의 insights 로 실어야 포털이 그
    카드들의 범위를 이어받는다(contracts §10.3 · 반대 검토 11-22 M5). 주제와 한 덩이다 — 그 칸만 빠지는 일이 없다. 근거로 쓰지 않았으면 칸이 없다."""
    out = _full(subject=SUBJECT, evidence=evidence)
    save = _call(out, "conv-save")
    subj = out["result"]["subject"]
    if want is None:
        assert "insights" not in subj and '"insights"' not in save
    else:
        assert subj["insights"] == want and f'"insights":{json.dumps(want, ensure_ascii=False, separators=(",", ":"))}' in save
    assert {k: v for k, v in subj.items() if k != "insights"} == SUBJECT


def test_워크플로_머리의_evidence_안내가_앞선_인사이트를_넘기는_법을_말한다():
    head = (Path(__file__).resolve().parents[2] / _DELIB).read_text(encoding="utf-8").split("export const meta", 1)[0]
    for want in ("insight_find", "insight_get", "검증 대상, 독립 근거 아님", "plat:", "같은 (과제, 차수)", "리스크 심사"):
        assert want in head, want


def test_읽은_인사이트_칸의_이름_상한_id_꼴이_워크플로_게이트웨이_포털에서_같다():
    """subject.insights 는 세 곳이 같은 꼴로 읽는다 — 워크플로(싣는다) · 게이트웨이(save_conversation 이 거른다) · 포털(표지로 적는다). 하나만
    달라지면 그 칸이 든 주제가 통째로 버려지거나(카드 없음) 읽은 카드를 모르는 것으로 떨어진다."""
    import re

    from app.insights import cards as C
    from app.insights import intake as I
    root = Path(__file__).resolve().parents[2]
    gw = root.parent / "HWAXMcpGateway" / "gateway.py"
    if not gw.exists():
        pytest.skip(f"형제 리포 없음: {gw}")
    g = gw.read_text(encoding="utf-8")
    js = (root / _DELIB).read_text(encoding="utf-8")
    assert f'CONV_INSIGHTS_FIELD = "{I.INSIGHTS_KEY}"' in g and f'CONV_INSIGHTS_UNKNOWN = "{I.INSIGHTS_UNKNOWN}"' in g
    assert f"CONV_INSIGHTS_MAX = {I.WORKFLOW_INSIGHTS_MAX}\n" in g and f"const INSIGHTS_MAX = {I.WORKFLOW_INSIGHTS_MAX}\n" in js
    assert "insights: INSIGHT_REFS" in js and f"'{I.INSIGHTS_UNKNOWN}'" in js
    m = re.search(r'^_CONV_INSIGHT_ID_RE = re\.compile\(r"(.+)"\)$', g, re.M)
    assert m and m.group(1) == C.INSIGHT_ID_RE.pattern, "카드 id 의 꼴"
    m = re.search(r"^const INSIGHT_ID_RE = /\^(.+)\$/$", js, re.M)
    assert m and m.group(1) == C.INSIGHT_ID_RE.pattern.replace('\\"', '"'), "카드 id 의 꼴(워크플로 — 파이썬 글의 따옴표 이스케이프만 다르다)"
