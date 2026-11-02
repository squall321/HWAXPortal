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

