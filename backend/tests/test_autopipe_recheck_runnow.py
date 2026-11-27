# 자동 파이프라인 사람의 손 둘(막힌 단계 다시 확인 · 지금 돌리기)과 update-all 의 박자 멈춤 — 엔진 단위(docs/auto-pipeline AP-24 ~ AP-26)
"""게이트웨이 · 앱은 계약 꼴 가짜(tests/autopipe_fakes.py), 시계는 시험이 쥔다. 고정하는 것.

  · 다시 확인은 막힌 단계와 그것을 기다린 뒤 단계만 대기로 되돌리고 같은 실행을 다시 연다 — 새 실행을 만들지 않는다. 그것 없이 쓴 보고서는 다시
    쓰고 옛 보고서는 사건에 남는다. 대체 · 취소된 실행, 뒤 실행이 있는 옛 실행, 입력이 바뀐 실행은 거절한다. 단계(stage)는 그대로 — 그림자는
    다시 그림자, 승인 전이면 다시 승인을 기다린다.
  · 지금 돌리기는 켠 시각 · 조용함을 넘지만 제외 목록 · ready_when · 같은 판 같은 입력 한 번 · 도는 실행 대체 금지는 그대로다.
  · 멈춤은 새 박자를 건너뛰고, 도는 박자는 실행 하나를 끝낸 자리에서 접고, quiesce 는 그것을 기다린다(못 기다리면 idle=false).
"""
from __future__ import annotations

import asyncio

import pytest
from autopipe_fakes import DROP, SPEC, T0, THERMAL, FakeAnalysis, Harness
from autopipe_fakes import ready_run as _ready_run

from app.agent import ra_post as _ra_post

BLOCK = {"ready": False, "missing": [{"kind": "infra", "why": "공유 볼륨 없음"}], "inputs": []}
TWO = {**SPEC, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                         {"id": "drop", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"},
                         {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal", "drop"]}]}


@pytest.fixture(autouse=True)
def _no_box_ra(tmp_path, monkeypatch):
    monkeypatch.setattr(_ra_post, "PATH", tmp_path / "없는-ra-formats.json")


@pytest.fixture()
def mk(tmp_path):
    made = []

    def make(*apps, **kw):
        d = tmp_path / f"h{len(made)}"
        d.mkdir()
        h = Harness(d, *apps, **kw)
        made.append(h)
        return h
    yield make
    for h in made:
        h.close()


def _until(h, run_id, *, ticks=(1, 120, 120, 120, 120)):
    for dt in ticks:
        h.tick(dt)
    return h.store.get_run(run_id)


def _run_now(h, rule_id, project="TASK-A", revision="dv1", by="op@example.com"):
    return h.loop.run_until_complete(h.engine.run_now(rule_id, project, revision, by))


# ── 다시 확인 ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_막힌_단계를_다시_확인하면_같은_실행이_확인부터_다시_해서_끝까지_간다(mk):
    app = FakeAnalysis(THERMAL)
    app.check_answer = BLOCK
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    assert h.store.get_run(run["id"])["state"] == "failed"
    for _ in range(3):
        h.tick(300)
    assert h.gw.count("auto_check") == 1, "막힘은 그 실행의 끝 — 사람이 누르기 전에는 박자가 다시 묻지 않는다"

    app.check_answer = None                               # 박스 문제가 풀렸다
    got, why = h.engine.recheck(run["id"], "op@example.com")
    assert why is None and got["rechecked"] == ["thermal"] and got["reset"] == ["thermal", "summary"]
    r = h.store.get_run(run["id"])
    assert r["state"] == "running" and r["ended_at"] is None and "다시 확인" in r["reason"]
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "pending" and st["check"] is None and st["error"] is None and st["ended_at"] is None and st["attempts"] == 0

    assert _until(h, run["id"])["state"] == "done"
    assert h.gw.count("auto_check") == 2 and h.gw.count("auto_submit") == 1
    assert len(h.runs()) == 1, "새 실행을 만들지 않는다 — 같은 입력의 같은 실행이다"
    ev = next(e["detail"] for e in h.store.events(run["id"]) if e["kind"] == "recheck")
    assert ev["by"] == "op@example.com" and ev["from_state"] == "failed" and ev["steps"] == ["thermal"]


def test_그것_없이_쓴_보고서는_다시_쓰고_옛_보고서는_사건에_남는다(mk):
    drop = FakeAnalysis(DROP)
    drop.check_answer = BLOCK
    h = mk(FakeAnalysis(THERMAL), drop)
    h.rule(TWO)
    run = _ready_run(h)
    run = _until(h, run["id"])
    st = h.steps(run["id"])
    assert run["state"] == "partial" and st["drop"]["state"] == "blocked" and st["summary"]["state"] == "done"
    old_md = st["summary"]["report_md"]

    drop.check_answer = None
    got, why = h.engine.recheck(run["id"], "op@example.com")
    assert why is None and got["reset"] == ["drop", "summary"], "끝난 해석(thermal)은 그대로 둔다"
    st = h.steps(run["id"])
    assert st["thermal"]["state"] == "done" and st["summary"]["state"] == "pending" and st["summary"]["report_md"] is None
    ev = next(e["detail"] for e in h.store.events(run["id"]) if e["kind"] == "recheck")
    assert ev["replaced_reports"][0]["step"] == "summary" and ev["replaced_reports"][0]["report_md"] == old_md

    run = _until(h, run["id"])
    st = h.steps(run["id"])
    assert run["state"] == "done" and st["drop"]["state"] == "done" and st["summary"]["state"] == "done"
    assert st["summary"]["report_md"] and st["summary"]["report_md"] != old_md
    assert sum(1 for t, _ in h.apps[THERMAL].calls if t == "auto_submit") == 1, "끝난 해석은 다시 내지 않는다"


def test_승인_전_실행은_다시_확인해도_다시_승인을_기다린다(mk):
    drop = FakeAnalysis(DROP)
    drop.check_answer = BLOCK
    h = mk(FakeAnalysis(THERMAL), drop)
    h.rule({**TWO, "stage": "approve"})
    run = _ready_run(h)
    assert h.store.get_run(run["id"])["state"] == "awaiting_approval"
    drop.check_answer = None
    _, why = h.engine.recheck(run["id"], "op@example.com")
    assert why is None
    h.tick(1)
    assert h.store.get_run(run["id"])["state"] == "awaiting_approval"
    assert {k: v["state"] for k, v in h.steps(run["id"]).items() if k != "summary"} == {"thermal": "ready", "drop": "ready"}
    assert h.gw.count("auto_submit") == 0, "다시 확인은 승인이 아니다"
    h.engine.approve(run["id"], "boss@example.com")
    h.tick(1)
    assert h.gw.count("auto_submit") == 2


def test_그림자_실행은_다시_확인해도_다시_그림자다(mk):
    app = FakeAnalysis(THERMAL)
    app.check_answer = BLOCK
    h = mk(app)
    h.rule({**SPEC, "stage": "shadow"})
    run = _ready_run(h)
    assert h.store.get_run(run["id"])["state"] == "planned"
    app.check_answer = None
    _, why = h.engine.recheck(run["id"], "op@example.com")
    assert why is None
    h.tick(1)
    assert h.store.get_run(run["id"])["state"] == "planned" and h.gw.count("auto_submit") == 0
    assert [e["kind"] for e in h.store.events(run["id"])].count("planned") == 2


def test_다시_확인을_거절하는_자리(mk):
    app = FakeAnalysis(THERMAL)
    app.check_answer = BLOCK
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    assert h.engine.recheck("없음", "op@example.com") == (None, "not_found")
    _, why = h.engine.recheck(run["id"], "op@example.com", "summary")
    assert "막힘이 아닙니다" in why
    # 입력이 바뀌었다 — 새 입력의 실행이 따로 선다(조용함을 기다리는 동안에도 옛 입력으로 되살리지 않는다)
    h.src.add("TASK-A", "dv1", sha="b" * 64, at=h.t + 10)
    h.tick(20)
    _, why = h.engine.recheck(run["id"], "op@example.com")
    assert "입력이 바뀌었습니다" in why
    # 뒤 실행이 섰다 — 옛 실행은 되살리지 않는다
    h.tick(700)
    assert len(h.runs()) == 2
    _, why = h.engine.recheck(run["id"], "op@example.com")
    assert "뒤 실행" in why
    assert h.store.get_run(run["id"])["state"] == "failed", "거절은 아무것도 바꾸지 않는다"


def test_막힘_없이_끝났거나_취소된_실행은_다시_확인하지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    run = _ready_run(h)
    assert _until(h, run["id"])["state"] == "done"
    _, why = h.engine.recheck(run["id"], "op@example.com")
    assert "이 실행은 done" in why
    h2 = mk(FakeAnalysis(THERMAL))
    h2.rule({**SPEC, "stage": "approve"})
    run2 = _ready_run(h2)
    h2.loop.run_until_complete(h2.engine.cancel(run2["id"], "op@example.com"))
    _, why = h2.engine.recheck(run2["id"], "op@example.com")
    assert "이 실행은 cancelled" in why


# ── 지금 돌리기 ────────────────────────────────────────────────────────────────────────────────────────────────────
def test_지금_돌리기는_켜기_전에_본_과제에도_돌고_같은_판_같은_입력은_한_번이다(mk):
    h = mk(FakeAnalysis(THERMAL), settings_over={"auto_pipeline_sources": "step_forge"})
    h.src.add("TASK-A", "dv1", at=h.t + 10)
    h.tick(20)
    h.tick(700)
    rid = h.rule()                                        # 켠 시각이 주제의 변화보다 뒤 — 저절로는 돌지 않는다(AP-12)
    h.tick(700)
    assert h.runs() == []
    got, why = _run_now(h, rid)
    assert why is None and got["run"]["stage"] == "auto" and got["run"]["reason"].startswith("사람이 지금 돌렸다(op@example.com)")
    run_id = got["run"]["id"]
    assert next(e["detail"] for e in h.store.events(run_id) if e["kind"] == "run_now") == {"by": "op@example.com", "rule_enabled": True}
    assert _until(h, run_id)["state"] == "done" and h.gw.count("auto_submit") == 1
    _, why = _run_now(h, rid)
    assert "이미 돌았습니다" in why and len(h.runs()) == 1


def test_지금_돌리기를_거절하는_자리(mk):
    h = mk(FakeAnalysis(THERMAL), settings_over={"auto_pipeline_sources": "step_forge"})
    h.src.add("TASK-A", "dv1", at=h.t + 10)
    h.src.add("TASK-B", "dv1", ref="p-2", at=h.t + 10, parsed=False)
    h.tick(20)
    rid = h.rule({**SPEC, "stage": "approve", "scope": {"all_projects": True, "exclude": ["TASK-X"]}})
    assert _run_now(h, "없음") == (None, "not_found")
    assert "감지한 적 없는" in _run_now(h, rid, "TASK-Z")[1]
    assert "ready_when" in _run_now(h, rid, "TASK-B")[1] and "step_forge.parsed" in _run_now(h, rid, "TASK-B")[1]
    rid_x = h.rule({**SPEC, "scope": {"all_projects": True, "exclude": ["TASK-A"]}})
    assert "제외 목록" in _run_now(h, rid_x)[1]
    got, why = _run_now(h, rid)
    assert why is None
    h.tick(1)
    assert h.store.get_run(got["run"]["id"])["state"] == "awaiting_approval"
    _, why = _run_now(h, rid)
    assert "도는 실행" in why, "앞 실행을 대체하지 않는다 — 끝나거나 취소한 뒤에"
    assert len(h.runs()) == 1


def test_꺼진_규칙도_지금_돌릴_수_있고_단계는_규칙_그대로다(mk):
    h = mk(FakeAnalysis(THERMAL), settings_over={"auto_pipeline_sources": "step_forge"})
    h.src.add("TASK-A", "dv1", at=h.t + 10)
    h.tick(20)
    rid = h.rule({**SPEC, "stage": "shadow"}, enable=False)
    got, why = _run_now(h, rid)
    assert why is None and got["run"]["stage"] == "shadow"
    h.tick(1)
    assert h.store.get_run(got["run"]["id"])["state"] == "planned" and h.gw.count("auto_submit") == 0
    assert next(e["detail"] for e in h.store.events(got["run"]["id"]) if e["kind"] == "run_now")["rule_enabled"] is False


# ── update-all 의 박자 멈춤 ────────────────────────────────────────────────────────────────────────────────────────
def test_멈춤은_새_박자를_건너뛰고_quiesce_는_도는_박자가_접히기를_기다린다(mk):
    h = mk(FakeAnalysis(THERMAL))
    eng = h.engine

    async def held(wait):
        await eng._lock.acquire()                         # 도는 박자 — 잠시 뒤 끝난다

        async def later():
            await asyncio.sleep(0.05)
            eng._lock.release()
        t = asyncio.create_task(later())
        r = await eng.quiesce(ttl_s=600, wait_s=wait, by="update-all")
        await t
        return r
    r = h.loop.run_until_complete(held(5))
    assert r["enabled"] is True and r["was_busy"] is True and r["idle"] is True and r["paused_until"] == T0 + 600
    assert h.tick(1) == {"skipped": "paused", "until": T0 + 600, "by": "update-all"}
    assert eng.health()["paused_until"] == T0 + 600 and eng.health()["paused_by"] == "update-all"
    out = h.tick(600)
    assert "skipped" not in out and eng.health()["paused_until"] is None, "멈춤은 ttl 뒤에 풀린다(포털이 못 다시 떠도)"

    async def stuck():
        await eng._lock.acquire()
        try:
            return await eng.quiesce(ttl_s=5, wait_s=0.05, by="update-all")
        finally:
            eng._lock.release()
    r = h.loop.run_until_complete(stuck())
    assert r["was_busy"] is True and r["idle"] is False
    r = h.loop.run_until_complete(eng.quiesce(ttl_s=5, wait_s=0, by="update-all"))
    assert r["was_busy"] is False and r["idle"] is True


def test_박자_도중에_멈추면_실행_하나를_끝낸_자리에서_접는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.src.add("TASK-A", "dv1", at=h.t + 10)
    h.src.add("TASK-B", "dv1", ref="p-2", at=h.t + 10)
    h.tick(20)
    h.tick(700)
    assert len(h.store.open_runs()) == 2
    seen = []
    orig = h.engine._advance_run

    async def advance(run_id, now, profiles):
        seen.append(run_id)
        await orig(run_id, now, profiles)
        h.engine.paused_until = h.t + 100                 # update-all 이 이 실행을 도는 동안 멈춤을 세웠다
    h.engine._advance_run = advance
    out = h.tick(120)
    assert out.get("paused") is True and len(seen) == 1, "남은 실행은 다음 박자에"
