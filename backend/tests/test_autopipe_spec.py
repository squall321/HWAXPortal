# 자동 파이프라인 규칙 스펙 검증(순환 · 참조 · 꼴 · 한도) · 원장 멱등(같은 열쇠 = 한 실행) · 계약 꼴 검사 · 입력 지문 · idem_key
"""docs/auto-pipeline portal-api §2 · §3, contract.md v1.1."""
from __future__ import annotations

import copy

import pytest

from app.autopipe import contract as C
from app.autopipe import spec as S
from app.autopipe.store import AutoStore
from app.config import Settings
from app.procedures.store import ProceduresStore

BASE = {"title": "낙하 · 열충격 기본", "stage": "shadow",
        "scope": {"all_projects": True, "exclude": ["TASK-X"]},
        "trigger": {"ready_when": ["step_forge.parsed"], "quiet_s": 1800},
        "steps": [{"id": "thermal", "kind": "analysis", "app": "heax-thermal_shock_mcp", "profile": "default"},
                  {"id": "drop", "kind": "analysis", "app": "heax-kooremapper_mcp", "profile": "fullangle-26", "needs": []},
                  {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal", "drop"]},
                  {"id": "revdiff", "kind": "report", "report": "revdiff", "needs": ["thermal", "drop"]}],
        "limits": {"max_concurrent": 2, "per_project_per_day": 1, "night_only": ["drop"]}}


def _spec(**over) -> dict:
    s = copy.deepcopy(BASE)
    s.update(over)
    return s


def _errs(spec) -> list[str]:
    return S.validate(spec)[0]


def test_문서의_예가_지나고_정규화된다():
    errors, warnings, spec = S.validate(BASE)
    assert errors == [] and spec["scope"] == {"all_projects": True, "exclude": ["TASK-X"]}
    assert spec["steps"][0]["needs"] == [] and spec["limits"]["night_only"] == ["drop"]
    assert S.parse(BASE) == spec


@pytest.mark.parametrize("steps,needle", [
    ([{"id": "a", "kind": "analysis", "app": "x", "profile": "p", "needs": ["b"]},
      {"id": "b", "kind": "analysis", "app": "x", "profile": "p", "needs": ["a"]}], "순환"),
    ([{"id": "a", "kind": "analysis", "app": "x", "profile": "p", "needs": ["a"]}], "자기 자신"),
    ([{"id": "a", "kind": "analysis", "app": "x", "profile": "p", "needs": ["없는것"]}], "없는 단계"),
    ([{"id": "a", "kind": "analysis", "app": "x", "profile": "p"},
      {"id": "r", "kind": "report", "report": "summary", "needs": ["a"]},
      {"id": "r2", "kind": "report", "report": "summary", "needs": ["r"]}], "해석(analysis) 단계만"),
    ([{"id": "a", "kind": "analysis", "app": "x", "profile": "p"}, {"id": "a", "kind": "analysis", "app": "x", "profile": "p"}], "겹친다"),
    ([{"id": "A!", "kind": "analysis", "app": "x", "profile": "p"}], "id 는"),
    ([{"id": "d", "kind": "deliberation"}], "M5"),
    ([{"id": "r", "kind": "report", "report": "summary", "needs": []}], "needs"),
    ([{"id": "r", "kind": "report", "report": "보고서", "needs": []}], "report 는"),
    ([{"id": "a", "kind": "analysis", "app": "X Y", "profile": "p"}], "app 은"),
    ([{"id": "a", "kind": "analysis", "app": "x", "profile": "p", "neds": []}], "모르는 칸"),
    ([], "steps"),
])
def test_단계_연결도_오류(steps, needle):
    errs = _errs(_spec(steps=steps, limits={}))
    assert any(needle in e for e in errs), errs


def test_analysis_가_analysis_를_가리키는_것은_되고_의존_차례로_세운다():
    steps = [{"id": "thermal", "kind": "analysis", "app": "x", "profile": "p", "needs": ["odb"]},
             {"id": "odb", "kind": "analysis", "app": "y", "profile": "p"},
             {"id": "summary", "kind": "report", "report": "summary", "needs": ["odb", "thermal"]}]
    errors, _w, spec = S.validate(_spec(steps=steps, limits={}))
    assert errors == []
    assert S.order(spec["steps"]) == ["odb", "thermal", "summary"]


@pytest.mark.parametrize("over,needle", [
    ({"stage": "live"}, "stage"),
    ({"title": ""}, "title"),
    ({"scope": {"all_projects": False}}, "AP-D4"),
    ({"scope": {"exclude": "TASK-X"}}, "exclude"),
    ({"trigger": {"quiet_s": 59}}, "quiet_s"),
    ({"trigger": {"quiet_s": 86401}}, "quiet_s"),
    ({"trigger": {"quiet_s": True}}, "quiet_s"),
    ({"trigger": {"ready_when": ["parsed"]}}, "ready_when"),
    ({"limits": {"max_concurrent": 0}}, "max_concurrent"),
    ({"limits": {"per_project_per_day": -1}}, "per_project_per_day"),
    ({"limits": {"night_only": ["summary"]}}, "night_only"),
    ({"limits": {"night_only": ["없음"]}}, "night_only"),
    ({"extra": 1}, "모르는 칸"),
])
def test_범위_트리거_한도_꼴(over, needle):
    errs = _errs(_spec(**over))
    assert any(needle in e for e in errs), errs


def test_단계는_열둘까지():
    steps = [{"id": f"a{i}", "kind": "analysis", "app": "x", "profile": "p"} for i in range(13)]
    assert any("12개" in e for e in _errs(_spec(steps=steps, limits={})))


def test_경고는_저장을_막지_않는다():
    errors, warnings, spec = S.validate(_spec(stage="auto", limits={}, steps=BASE["steps"][:2], trigger={"quiet_s": 600}))
    assert errors == [] and spec is not None
    assert any("보고서 단계가 없다" in w for w in warnings) and any("규칙 한도" in w for w in warnings)
    assert any("ready_when" in w for w in warnings)


# ── 원장 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def store(tmp_path):
    base = ProceduresStore(Settings(_env_file=None, procedures_store_path=str(tmp_path / "wb.sqlite")))
    yield AutoStore(base)
    base.close()


def test_같은_열쇠면_실행은_하나다(store):
    rid = store.create_rule(spec=S.parse(BASE), by="m@example.com", now=10)["id"]
    subj = {"project": "TASK-A", "revision": "dv1", "fingerprint": "f" * 64, "refs": {"step_forge": "p-1"}}
    steps = [("thermal", "analysis"), ("summary", "report")]
    a = store.create_run(rule_id=rid, version_no=1, subject=subj, stage="shadow", steps=steps, now=11)
    b = store.create_run(rule_id=rid, version_no=1, subject=subj, stage="shadow", steps=steps, now=12)
    assert a and b is None and len(store.runs()) == 1
    assert store.has_run(rule_id=rid, project="TASK-A", revision="dv1", fingerprint="f" * 64)
    c = store.create_run(rule_id=rid, version_no=2, subject=subj, stage="shadow", steps=steps, now=13)
    assert c, "판이 다르면 열쇠가 다르다(엔진이 has_run 으로 막는다)"
    assert [s["step_id"] for s in store.steps(a)] == ["thermal", "summary"]


def test_판은_불변이고_켜기는_판과_따로다(store):
    rid = store.create_rule(spec=S.parse(BASE), by="m@example.com", now=10)["id"]
    assert store.get_rule(rid)["enabled"] is False and store.get_rule(rid)["enabled_at"] is None
    store.add_version(rule_id=rid, spec=S.parse(_spec(title="둘째 판")), by="m@example.com", now=20)
    r = store.get_rule(rid)
    assert r["latest_version"] == 2 and r["title"] == "둘째 판" and store.version_spec(rid, 1)["title"] == BASE["title"]
    assert store.set_enabled(rule_id=rid, enabled=True, by="b@example.com", now=30)["enabled_at"] == 30
    assert store.set_enabled(rule_id=rid, enabled=True, by="b@example.com", now=40)["enabled_at"] == 30, "이미 켜져 있으면 그대로"
    assert store.add_version(rule_id="없음", spec=S.parse(BASE), by="x", now=1) is None


# ── 계약 꼴 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_입력_지문은_시각을_넣지_않고_차례에_무관하다():
    a = C.fingerprint({"s": [{"kind": "cad", "ref": "1", "sha256": "x"}, {"kind": "ecad", "ref": "2", "sha256": "y"}]})
    b = C.fingerprint({"s": [{"kind": "ecad", "ref": "2", "sha256": "y", "at": "2027"}, {"kind": "cad", "ref": "1", "sha256": "x"}]})
    assert a == b and a != C.fingerprint({"s": [{"kind": "cad", "ref": "1", "sha256": "z"}]})


def test_idem_key_는_64자_소문자_16진수이고_다섯이_다_들어간다():
    k = C.idem_key("TASK-A", "dv1", "r1", 1, "f" * 64, "thermal")
    assert len(k) == 64 and k == k.lower() and all(ch in "0123456789abcdef" for ch in k)
    for other in (("TASK-B", "dv1", "r1", 1, "f" * 64, "thermal"), ("TASK-A", "dv2", "r1", 1, "f" * 64, "thermal"),
                  ("TASK-A", "dv1", "r1", 2, "f" * 64, "thermal"), ("TASK-A", "dv1", "r1", 1, "e" * 64, "thermal"),
                  ("TASK-A", "dv1", "r1", 1, "f" * 64, "drop")):
        assert C.idem_key(*other) != k


def test_단계_지문에_앞_단계_결과의_inputs_artifacts_가_들어간다():
    up = {"odb": {"inputs": [{"kind": "odb", "ref": "o1", "sha256": "1"}], "artifacts": [{"kind": "tgz", "location": "/a"}]}}
    base = C.step_fingerprint("f", [], {})
    assert C.step_fingerprint("f", [], up) != base
    up2 = {"odb": {**up["odb"], "artifacts": [{"kind": "tgz", "location": "/b"}]}}
    assert C.step_fingerprint("f", [], up2) != C.step_fingerprint("f", [], up)


@pytest.mark.parametrize("v,ok", [
    ({"ready": True, "missing": [], "inputs": []}, True),
    ({"ready": False, "missing": [{"kind": "앱_낱말"}], "inputs": []}, True),
    ({"ready": "yes"}, False),
    ({"ready": True, "inputs": [{"kind": "cad"}]}, False),
    ({"ready": False, "missing": [{"why": "kind 없음"}]}, False),
])
def test_check_꼴(v, ok):
    assert (C.check_ok(v) is not None) is ok


def test_상태_제출_꼴():
    assert C.status_ok({"state": "running", "progress": 0.4}) == {"state": "running", "progress": 0.4}
    assert C.status_ok({"state": "succeeded"}) is None, "앱이 낱말을 바꿔 싣는다(§0.3)"
    assert C.status_ok({"state": "running", "progress": 1.5}) is None
    assert C.submit_ok({"run_ref": "r", "state": "done", "created": False})["state"] == "done"
    assert C.submit_ok({"run_ref": "", "state": "queued"}) is None
    assert C.submit_ok({"run_ref": "r", "state": "COMPLETED"}) is None


def test_원천_항목의_null_과제는_그대로_싣는다():
    got = C.changes_ok({"items": [{"subject": {"project": None, "revision": None, "refs": {"step_forge": 12}}, "inputs": [],
                                   "ready": {"parsed": 1}, "updated_at": None}], "next_since": None, "complete": True})
    assert got["items"][0]["subject"] == {"project": None, "revision": None, "refs": {"step_forge": "12"}}
    assert got["items"][0]["ready"] == {"parsed": True}
    assert C.changes_ok({"items": [], "complete": "yes"}) is None
