# 분석 루틴 스펙 — 저장 때 막는 것(꼴 · 참조 · 앞 단계 · 쓰기 도구 · 비밀)과 막지 않는 것(백엔드가 이 박스에 있나), 참조 치환(docs/analysis-routines/contracts.md §1)
import copy

import pytest

from app.procedures.models import SpecError
from app.procedures.routines import RoutineSpec, is_write_tool, parse_spec, refs_of, render

SPEC = {
    "title": "시장불량 원인 분석",
    "purpose": "{{model}} 의 {{symptom}} 시장불량 — 원인 · 시험 · 대책",
    "vars": [{"key": "model", "label": "모델"}, {"key": "symptom", "label": "증상"}],
    "steps": [
        {"id": "anchor", "title": "기준 키", "backends": ["rootdesigndatahub"], "goal": "{{model}} 을 plm_model 로 푼다",
         "tools": ["object_resolve"], "expect": {"keys": ["model_key"]},
         "blocked": {"empty": "stop", "denied": "stop", "unavailable": "stop"}},
        {"id": "ft", "title": "시장불량 이력", "backends": ["failuretrace"], "uses": ["anchor"],
         "goal": "{{steps.anchor.model_key}} 의 {{symptom}} 불량 기록을 유형 · 시기별로", "budget": {"calls": 6}},
        {"id": "delib", "title": "메커니즘", "kind": "deliberation", "goal": "메커니즘을 밝힌다", "uses": ["ft"]},
    ],
    "report": {"title": "{{model}} {{symptom}} 분석 — {{steps.anchor.model_key}}"},
}


def _spec(**patch):
    d = copy.deepcopy(SPEC)
    d.update(patch)
    return d


def _bad(raw, needle):
    with pytest.raises(SpecError) as exc:
        parse_spec(raw)
    assert needle in str(exc.value), str(exc.value)
    return str(exc.value)


def test_예시_스펙은_기본값을_채워_통과한다():
    s = parse_spec(_spec())
    assert isinstance(s, RoutineSpec) and s.version == 1 and s.visibility == "private"
    assert s.report.ra.upload == "auto", "사용자 결정 Q1 — RA 초안은 저절로"
    assert s.report.sections == ["anchor", "ft", "delib", "insight"], "절을 안 적으면 단계 차례 + 인사이트"
    ft = s.steps[1]
    assert (ft.blocked.empty, ft.blocked.denied, ft.blocked.unavailable) == ("continue", "skip", "skip"), "막힌 단계는 건너뛴다(Q2 · Q4)"
    assert (ft.budget.calls, ft.budget.seconds) == (6, 300) and s.limits.minutes == 60
    assert s.steps[2].deliberation is not None and s.steps[2].deliberation.job == "mechanism"


def test_단계_id_와_백엔드와_종류를_본다():
    _bad(_spec(steps=[{**SPEC["steps"][0], "id": "Anchor"}]), "단계 id")
    _bad(_spec(steps=[{**SPEC["steps"][0], "id": "insight"}]), "예약")
    steps = copy.deepcopy(SPEC["steps"])
    steps[1]["id"] = "anchor"
    _bad(_spec(steps=steps), "단계 id 가 겹친다")
    _bad(_spec(steps=[{**SPEC["steps"][0], "backends": []}]), "백엔드(울타리)가 하나 이상")
    _bad(_spec(steps=[{**SPEC["steps"][0], "backends": ["bad key!"]}]), "백엔드 키 꼴")
    _bad(_spec(steps=[{"id": "d", "title": "심의", "kind": "deliberation", "goal": "g", "backends": ["x"]}]), "심의 단계는 백엔드")
    _bad(_spec(steps=[{**SPEC["steps"][0], "deliberation": {"job": "mechanism"}}]), "심의 단계에만")
    _bad(_spec(steps=[{**SPEC["steps"][0], "surprise": 1}]), "Extra inputs")


def test_uses_와_참조는_앞_단계만_가리킨다():
    steps = copy.deepcopy(SPEC["steps"])
    steps[0]["uses"] = ["ft"]
    _bad(_spec(steps=steps), "앞 단계만")
    steps = copy.deepcopy(SPEC["steps"])
    steps[0]["goal"] = "{{steps.ft.x}}"
    _bad(_spec(steps=steps), "앞 단계가 아니다")
    steps = copy.deepcopy(SPEC["steps"])
    steps[1]["goal"] = "{{steps.anchor.nope}}"
    _bad(_spec(steps=steps), "expect.keys 에 'nope' 가 없다")
    _bad(_spec(purpose="{{nobody}}"), "풀 수 없다")
    assert parse_spec(_spec(purpose="{{run.started}} 기준 {{ model }}")).purpose


def test_단계_안에서_쓰지_않는다_v1():
    for tool in ("publish_report", "submit_job", "delete_project", "slurm_job_control", "run_job"):
        assert is_write_tool(tool), tool
        _bad(_spec(steps=[{**SPEC["steps"][0], "tools": [tool]}]), "쓰기 도구")
    assert not is_write_tool("search_reports") and not is_write_tool("object_resolve")


def test_비밀처럼_생긴_글은_저장하지_않는다():
    for text in ("Bearer abcdefghijklmnopqrstuvwxyz012345", "https://user:pw@host/x",
                 "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4eXoifQ.sig"):
        _bad(_spec(steps=[{**SPEC["steps"][0], "goal": f"{{{{model}}}} {text}"}]), "비밀처럼 생긴 글")


def test_보고서_절은_단계_id_와_insight_cite_만():
    _bad(_spec(report={"sections": ["anchor", "nowhere"]}), "없는 절")
    _bad(_spec(report={"sections": ["anchor", "anchor"]}), "겹친다")
    assert parse_spec(_spec(report={"sections": ["ft", "cite", "insight"], "ra": {"upload": "off"}})).report.ra.upload == "off"


def test_까닭은_읽을_수_있고_입력을_되싣지_않는다():
    msg = _bad({"title": "", "steps": []}, "title")
    assert "input" not in msg and len(msg) < 600
    with pytest.raises(SpecError):
        parse_spec(["not", "a", "dict"])


def test_참조_치환은_모르는_것을_지우지_않는다():
    assert refs_of("{{a}} {{ steps.x.k }} {{run.started}}") == ["a", "steps.x.k", "run.started"]
    out = render("{{model}} · {{steps.anchor.model_key}} · {{steps.ft.k}} · {{run.started}} · {{gone}}",
                 {"model": "S26"}, {"anchor": {"model_key": "SM-S938"}}, started="2026-10-30")
    assert out == "S26 · SM-S938 · {{steps.ft.k}} · 2026-10-30 · {{gone}}"


def test_문서의_예시_루틴_둘은_저장_검증을_통과한다():
    """docs/analysis-routines/examples — cae00 시장불량 연쇄(결정 Q7 둘 다) · dev 시연 연쇄. 낡으면 여기서 깨진다."""
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[2] / "docs" / "analysis-routines" / "examples"
    got = {p.name: parse_spec(yaml.safe_load(p.read_text(encoding="utf-8"))) for p in sorted(root.glob("*.yaml"))}
    assert set(got) == {"dev-demo.yaml", "market-defect.yaml"}
    md = got["market-defect.yaml"]
    assert [s.id for s in md.steps] == ["anchor", "ft", "plm", "voc", "delib", "fmea", "ecad", "sim", "refs"]
    assert md.steps[0].blocked.unavailable == "stop" and md.steps[1].blocked.unavailable == "skip", "기준 키만 멈춘다(Q4)"
    assert {"failuretrace", "plm-defect"} <= {b for s in md.steps for b in s.backends}, "시장불량은 둘 다(Q7)"
    assert md.report.ra.upload == "auto" and got["dev-demo.yaml"].report.sections[-1] == "insight"


def test_YAML_1_1_의_참거짓_낱말에_걸리지_않는다():
    """PyYAML 은 on · off 를 참 · 거짓으로 읽는다 — 정책 칸은 blocked, `upload: off` 는 'off' 로 받고, 옛 `on:` 은 고칠 것을 말한다."""
    import yaml
    text = """
title: t
steps:
  - id: a
    title: A
    backends: [signalforge]
    goal: g
    blocked: {empty: stop}
report: {ra: {upload: off}}
"""
    s = parse_spec(yaml.safe_load(text))
    assert s.steps[0].blocked.empty == "stop" and s.report.ra.upload == "off"
    bad = yaml.safe_load(text.replace("blocked:", "on:"))
    assert True in bad["steps"][0], "이 시험의 전제 — PyYAML 이 on 을 True 로 읽는다"
    _bad(bad, "blocked:")
    dumped = yaml.safe_dump(s.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
    assert parse_spec(yaml.safe_load(dumped)).report.ra.upload == "off", "내보내기 → 가져오기가 제자리로 돈다"
