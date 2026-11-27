# 자동 파이프라인 엔진 한 박자 — 감지 · 판정 · shadow/approve/auto · 응답 잃은 뒤 같은 idem_key · 폴링 간격 · 봉투 불량 · 막힘 · 한도 · 야간 · AP-D5 · upstream
"""게이트웨이 · 앱은 계약 v1.1 꼴 그대로의 가짜다(tests/autopipe_fakes.py — MockTransport). 시계는 시험이 쥔다. 원장은 임시 절차 저장소다.
RA 박스 파일은 없는 자리로 돌려 이 박스의 infra/ra-formats.local.json 을 읽지 않는다."""
from __future__ import annotations

import pytest
from autopipe_fakes import DROP, SPEC, SRC, T0, THERMAL, FakeAnalysis, Harness
from autopipe_fakes import ready_run as _ready_run

from app.agent import ra_post as _ra_post
from app.autopipe import spec as S
from app.autopipe.engine import in_night, night_window


@pytest.fixture(autouse=True)
def _no_box_ra(tmp_path, monkeypatch):
    monkeypatch.setattr(_ra_post, "PATH", tmp_path / "없는-ra-formats.json")


@pytest.fixture()
def mk(tmp_path):
    made = []

    def make(*apps, **kw):
        d = tmp_path / f"h{len(made)}"            # 한 시험의 둘째 하네스가 첫째의 원장을 보지 않게
        d.mkdir()
        h = Harness(d, *apps, **kw)
        made.append(h)
        return h
    yield make
    for h in made:
        h.close()


# ── 흐름 셋 — shadow · approve · auto ──────────────────────────────────────────────────────────────────────────────
def test_shadow_는_확인까지만_하고_제출하지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule({**SPEC, "stage": "shadow"})
    run = _ready_run(h)
    run = h.store.get_run(run["id"])
    assert run["state"] == "planned" and h.gw.count("auto_submit") == 0
    st = h.steps(run["id"])
    assert st["thermal"]["state"] == "ready" and st["summary"]["state"] == "skipped"
    ev = [e for e in h.store.events(run["id"]) if e["kind"] == "planned"][0]["detail"]
    assert ev["would_submit"][0]["step"] == "thermal" and ev["would_submit"][0]["cost"]["cores"] == 64
    for _ in range(5):
        h.tick(300)
    assert h.gw.count("auto_submit") == 0, "그림자 실행은 뒤 박자에도 내지 않는다"


def test_approve_는_승인_전_제출_0_승인하면_낸다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule({**SPEC, "stage": "approve"})
    run = _ready_run(h)
    assert h.store.get_run(run["id"])["state"] == "awaiting_approval"
    for _ in range(3):
        h.tick(300)
    assert h.gw.count("auto_submit") == 0
    assert h.engine.approve(run["id"], "boss@example.com")["approved_by"] == "boss@example.com"
    assert h.engine.approve(run["id"], "boss@example.com") is None, "두 번 승인하지 않는다"
    h.tick(1)
    assert h.gw.count("auto_submit") == 1
    assert h.steps(run["id"])["thermal"]["state"] == "queued"
    kinds = [e["kind"] for e in h.store.events(run["id"])]
    assert "approved" in kinds and kinds.index("approved") < kinds.index("submit")


def test_auto_는_내고_폴링해서_결과_봉투를_받고_보고서를_쓴다(mk):
    app = FakeAnalysis(THERMAL)
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "queued" and len(st["idem_key"]) == 64 and st["run_ref"]
    h.tick(120)
    assert h.steps(run["id"])["thermal"]["state"] == "running"
    h.tick(120)
    st = h.steps(run["id"])
    assert st["thermal"]["state"] == "done" and st["thermal"]["verdict"] == "pass"
    assert st["thermal"]["result"]["metrics"][0]["value"] == 0.82
    assert st["summary"]["state"] == "done" and "솔더 SED 최대" in st["summary"]["report_md"]
    run = h.store.get_run(run["id"])
    assert run["state"] == "done" and run["ended_at"]
    # 제출 인자는 계약 꼴 그대로 — subject{project, revision, refs} · profile · idem_key
    sub = [a for bk, o, a in h.gw.calls if o == "auto_submit"][0]
    assert sub["subject"] == {"project": "TASK-A", "revision": "dv1", "refs": {"step_forge": "p-1"}}
    assert sub["profile"] == "default" and sub["idem_key"] == st["thermal"]["idem_key"]


@pytest.mark.parametrize("stage", ["shadow", "approve"])
def test_다른_해석의_확인이_밀려_실행이_running_에_머물러도_shadow_approve_는_내지_않는다(mk, stage):
    """해석 둘 중 하나의 확인이 결과 모름으로 밀리면 실행은 planned · awaiting_approval 로 서지 못하고 running 에 머문다 — 그 동안에도 준비된
    다른 해석을 내지 않는다(실행 상태가 아니라 stage 가 막는다)."""
    h = mk(FakeAnalysis(THERMAL), FakeAnalysis(DROP))
    h.rule({**SPEC, "stage": stage, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                                              {"id": "drop", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"}]})
    h.gw.unreachable.add(DROP)
    run = _ready_run(h)
    for _ in range(3):
        h.tick(60)
    st = h.steps(run["id"])
    assert h.store.get_run(run["id"])["state"] == "running" and st["thermal"]["state"] == "ready" and st["drop"]["state"] == "pending"
    assert h.gw.count("auto_submit") == 0


def test_같은_박자를_여러_번_돌려도_실행은_하나다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    _ready_run(h)
    for _ in range(4):
        h.tick(1)
    assert len(h.runs()) == 1


# ── 제출 · 상태 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_제출_답을_잃으면_다음_박자에_같은_idem_key_로_다시_부르고_실행은_하나다(mk):
    app = FakeAnalysis(THERMAL)
    app.lose_submit = 1
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "ready" and st["idem_key"] and st["run_ref"] is None and "다시 시도" in st["error"]
    key = st["idem_key"]
    h.tick(60)
    subs = [a["idem_key"] for bk, o, a in h.gw.calls if o == "auto_submit"]
    assert subs == [key, key], "같은 idem_key 로 다시 불렀다"
    assert len(app.runs) == 1, "앱에 실행은 하나다"
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "queued" and st["run_ref"] == next(iter(app.runs))


def test_제출_재시도는_한도를_다시_보지_않는다(mk):
    """답을 잃은 제출은 이미 낸 것을 확인하는 호출이다 — 박스 상한이 1 이고 그 자리를 자기가 쥐고 있어도 다시 부른다."""
    app = FakeAnalysis(THERMAL)
    app.lose_submit = 1
    h = mk(app, settings_over={"auto_pipeline_max_concurrent": 1})
    h.rule()
    run = _ready_run(h)
    assert h.store.active_steps() == 1, "결과 모르는 제출도 자리를 쥔다"
    h.tick(60)
    assert h.steps(run["id"])["thermal"]["state"] == "queued"


def test_상태는_폴링_간격마다만_묻는다(mk):
    app = FakeAnalysis(THERMAL)
    app.status_seq = ["running", "running", "done"]
    h = mk(app, settings_over={"auto_pipeline_poll_s": 120})
    h.rule()
    run = _ready_run(h)
    for dt in (30, 30, 30):
        h.tick(dt)
    assert h.gw.count("auto_status") == 0, "120초가 안 지나면 묻지 않는다"
    h.tick(30)
    assert h.gw.count("auto_status") == 1
    h.tick(60)
    assert h.gw.count("auto_status") == 1
    h.tick(60)
    assert h.gw.count("auto_status") == 2
    h.tick(120)
    assert h.steps(run["id"])["thermal"]["state"] == "done"


def test_동기_앱은_제출이_곧_done_이면_상태를_묻지_않고_결과로_간다(mk):
    app = FakeAnalysis(THERMAL, sync=True)
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])
    assert st["thermal"]["state"] == "done" and st["summary"]["state"] == "done"
    assert h.gw.count("auto_status") == 0 and h.gw.count("auto_result") == 1
    assert h.store.get_run(run["id"])["state"] == "done"


@pytest.mark.parametrize("raw,why", [
    ({"verdict": "ok"}, "verdict"),
    ({"metrics": [{"name": "x", "unit": "", "value": 1}]}, "metrics"),
    ({"metrics": [{"name": "x", "unit": "mm", "value": "1"}]}, "metrics"),
    ({"run_ref": "남의-실행"}, "run_ref"),
    ({"subject": {"project": "TASK-Z", "revision": "dv1", "refs": {}}}, "subject"),
    ({"metrics": [], "notes": []}, "notes"),
])
def test_봉투가_꼴에_안_맞으면_failed_envelope_invalid(mk, raw, why):
    app = FakeAnalysis(THERMAL, sync=True)
    app.result_over = raw
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])
    assert st["thermal"]["state"] == "failed" and st["thermal"]["error"].startswith("envelope_invalid") and why in st["thermal"]["error"]
    assert st["summary"]["state"] == "skipped", "끝난 해석이 없으면 보고서는 건너뛴다"
    assert h.store.get_run(run["id"])["state"] == "failed"


def test_isError_false_에_error_칸이_실리면_실패다(mk):
    app = FakeAnalysis(THERMAL, sync=True)
    app.result_raw = {"error": "boom", "detail": "실패를 성공처럼"}
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "failed" and "envelope_invalid" in st["error"] and "error 칸" in st["error"]


# ── 막힘 ────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("field,reason", [("project", "project_key"), ("revision", "revision")])
def test_과제_key_나_개발_단계가_null_이면_막힘이고_실행이_없다(mk, field, reason):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.src.add(None if field == "project" else "TASK-A", None if field == "revision" else "dv1", at=h.t + 10)
    h.tick(20)
    h.tick(5000)
    assert h.runs() == []
    sub = h.store.subjects()
    assert len(sub) == 1 and sub[0]["state"] == "blocked" and sub[0]["block_reason"] == reason


@pytest.mark.parametrize("missing", [[{"kind": "infra", "why": "공유 볼륨 없음"}],
                                     [{"kind": "human_input", "name": "pkg_type", "why": "사람 값"}],
                                     [{"kind": "앱이_새로_만든_낱말"}]])
def test_auto_check_가_빠진_입력을_말하면_막힘이고_제출하지_않는다(mk, missing):
    app = FakeAnalysis(THERMAL)
    app.check_answer = {"ready": False, "missing": missing, "inputs": []}
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "blocked" and st["error"].startswith("missing:" + missing[0]["kind"])
    assert st["check"]["missing"][0]["kind"] == missing[0]["kind"], "모르는 낱말도 그대로 둔다"
    assert h.gw.count("auto_submit") == 0
    assert h.store.get_run(run["id"])["state"] == "failed"


def test_서비스_신원을_못_받는_앱_과_없는_profile_은_막힘(mk):
    h = mk(FakeAnalysis(THERMAL, service_identity=False))
    h.rule()
    run = _ready_run(h)
    assert h.steps(run["id"])["thermal"]["error"].startswith("service_identity")
    h2 = mk(FakeAnalysis(THERMAL, profile="다른-것"))
    h2.rule()
    run = _ready_run(h2)
    assert h2.steps(run["id"])["thermal"]["error"].startswith("profile_unknown")


def test_허용_목록_밖이면_막힘(mk):
    app = FakeAnalysis(THERMAL)
    h = mk(app, allowed={f"{SRC}:auto_changes", f"{THERMAL}:auto_profiles", f"{THERMAL}:auto_check"})
    h.rule()
    run = _ready_run(h)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "blocked" and "permission" in st["error"] and "service-denied" in st["error"]


def test_계약_도구가_없는_앱은_막힘이고_불통인_앱은_기다린다(mk):
    app = FakeAnalysis(THERMAL)
    app.tools = ["auto_profiles"]                     # 계약을 덜 갖춤
    h = mk(app)
    h.rule()
    run = _ready_run(h)
    assert h.steps(run["id"])["thermal"]["error"].startswith("auto_check tool_missing")
    app2 = FakeAnalysis(THERMAL)
    h2 = mk(app2)
    h2.rule()
    h2.gw.unreachable.add(THERMAL)
    run = _ready_run(h2)
    st = h2.steps(run["id"])["thermal"]
    assert st["state"] == "pending" and "다시 시도" in (st["error"] or "")
    h2.gw.unreachable.clear()
    h2.tick(60)
    assert h2.steps(run["id"])["thermal"]["state"] == "queued"


def test_결과_모르는_실패가_상한을_넘으면_확인은_막힘_제출은_실패(mk, monkeypatch):
    from app.autopipe import engine as E
    monkeypatch.setattr(E, "CHECK_RETRY_MAX", 2)
    monkeypatch.setattr(E, "SUBMIT_RETRY_MAX", 2)
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.gw.unreachable.add(THERMAL)
    run = _ready_run(h)
    h.tick(60)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "blocked" and st["error"].startswith("auto_profiles: unreachable")
    app = FakeAnalysis(THERMAL)
    app.lose_submit = 5
    h2 = mk(app)
    h2.rule()
    run = _ready_run(h2)
    h2.tick(60)
    st = h2.steps(run["id"])["thermal"]
    assert st["state"] == "failed" and "결과 모름" in st["error"] and "idem_key" in st["error"]


# ── 판정(감지 · 조용함 · 준비 신호 · 범위) ─────────────────────────────────────────────────────────────────────────
def test_조용해지기_전에_새_입력이_오면_조용함을_다시_잰다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.src.add("TASK-A", "dv1", at=h.t + 10)
    h.tick(20)
    h.tick(500)                                       # 아직 600초 전
    h.src.add("TASK-A", "dv1", ref="p-2", sha="b" * 64, at=h.t)   # 같은 단계의 새 CAD 개정
    h.tick(10)
    h.tick(400)
    assert h.runs() == [], "마지막 변화부터 600초가 안 지났다"
    h.tick(300)
    runs = h.runs()
    assert len(runs) == 1 and runs[0]["refs"]["step_forge"] == "p-2"


def test_ready_when_이_안_서면_실행하지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.src.add("TASK-A", "dv1", at=h.t + 10, parsed=False)
    h.tick(20)
    h.tick(5000)
    assert h.runs() == []
    h.src.add("TASK-A", "dv1", at=h.t, parsed=True)  # 같은 입력 · 준비 신호만 섬(지문 같음 — 조용함은 그대로)
    h.tick(1)
    assert len(h.runs()) == 1


def test_범위_제외_과제는_돌지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule({**SPEC, "scope": {"all_projects": True, "exclude": ["TASK-X"]}})
    h.src.add("TASK-X", "dv1", at=h.t + 10)
    h.src.add("TASK-A", "dv1", ref="p-9", at=h.t + 10)
    h.tick(20)
    h.tick(700)
    assert [r["project"] for r in h.runs()] == ["TASK-A"]


def test_규칙은_켠_뒤에_바뀐_과제에만_돈다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.src.add("TASK-A", "dv1", at=h.t - 5000)        # 켜기 전에 바뀐 것
    rid = h.rule(enable=False)
    h.tick(10)
    h.store.set_enabled(rule_id=rid, enabled=True, by="maker@example.com", now=h.t)
    h.tick(5000)
    assert h.runs() == [], "켜기 전 변화로 한꺼번에 해석을 내지 않는다"
    h.src.add("TASK-A", "dv1", sha="c" * 64, at=h.t + 1)
    h.tick(10)
    h.tick(700)
    assert len(h.runs()) == 1


def test_판을_고쳐도_같은_지문은_다시_돌지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    rid = h.rule()
    _ready_run(h)
    h.store.add_version(rule_id=rid, spec=S.parse({**SPEC, "title": "고친 판"}), by="maker@example.com", now=h.t)
    h.tick(700)
    assert len(h.runs()) == 1


def test_원천_답이_꼴에_안_맞으면_커서를_나아가지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.src.raw = {"items": [{"subject": {"project": 3}}], "complete": True}
    h.tick(1)
    cur = {c["source"]: c for c in h.store.cursors()}[SRC]
    assert cur["cursor"] is None and "꼴이 틀렸다" in cur["last_error"]


def test_원천은_쪽을_끝까지_넘긴_뒤에만_커서를_나아간다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.src.page = 2
    h.rule()
    for i in range(5):
        h.src.add(f"TASK-{i}", "dv1", ref=f"p-{i}", at=h.t + 1)
    h.tick(10)
    assert len(h.store.subjects()) == 5
    assert {c["source"]: c for c in h.store.cursors()}[SRC]["cursor"] == "5"
    assert [a["since"] for _, a in h.src.calls] == [None, "2", "4"]


# ── 한도 · 야간 창 ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_박스_전체_동시_상한(mk):
    h = mk(FakeAnalysis(THERMAL), settings_over={"auto_pipeline_max_concurrent": 1})
    h.rule()
    h.src.add("TASK-A", "dv1", ref="p-1", at=h.t + 10)
    h.src.add("TASK-B", "dv1", ref="p-2", at=h.t + 10)
    h.tick(20)
    h.tick(700)
    states = sorted(h.steps(r["id"])["thermal"]["state"] for r in h.runs())
    assert states == ["queued", "ready"]
    waiting = [h.steps(r["id"])["thermal"] for r in h.runs() if h.steps(r["id"])["thermal"]["state"] == "ready"][0]
    assert "박스 전체 동시 제출 상한 1" in waiting["error"]
    h.tick(120)
    h.tick(120)                                       # 앞 것이 끝나 자리가 난다
    h.tick(1)
    assert sorted(h.steps(r["id"])["thermal"]["state"] for r in h.runs()) in (["done", "queued"], ["done", "running"])


def test_규칙_동시_상한과_과제당_하루_상한(mk):
    h = mk(FakeAnalysis(THERMAL), settings_over={"auto_pipeline_max_concurrent": 10})
    h.rule({**SPEC, "limits": {"max_concurrent": 1}})
    h.src.add("TASK-A", "dv1", ref="p-1", at=h.t + 10)
    h.src.add("TASK-B", "dv1", ref="p-2", at=h.t + 10)
    h.tick(20)
    h.tick(700)
    assert h.gw.count("auto_submit") == 1
    h2 = mk(FakeAnalysis(THERMAL, sync=True), settings_over={"auto_pipeline_max_concurrent": 10})
    h2.rule({**SPEC, "limits": {"per_project_per_day": 1}})
    _ready_run(h2, "TASK-A", "dv1")
    assert h2.gw.count("auto_submit") == 1
    h2.src.add("TASK-A", "dv2", ref="p-3", at=h2.t + 1)
    h2.tick(10)
    h2.tick(700)
    dv2 = [r for r in h2.runs() if r["revision"] == "dv2"][0]
    st = h2.steps(dv2["id"])["thermal"]
    assert st["state"] == "ready" and "과제당 하루 상한" in st["error"]
    h2.tick(86400)
    assert h2.steps(dv2["id"])["thermal"]["state"] == "done", "24시간이 지나면 낸다"


def test_야간_전용_단계는_창_밖에서_기다린다(mk):
    assert night_window("20-07") == (20, 7) and night_window("x") is None and night_window("7-7") is None
    assert not in_night(T0, (20, 7)) and in_night(T0 + 3 * 3600, (20, 7)), "T0 는 17시 KST, +3시간은 20시"
    h = mk(FakeAnalysis(THERMAL))
    h.rule({**SPEC, "limits": {"night_only": ["thermal"]}})
    run = _ready_run(h)
    st = h.steps(run["id"])["thermal"]
    assert st["state"] == "ready" and "야간 전용" in st["error"]
    h.tick(3 * 3600)
    assert h.steps(run["id"])["thermal"]["state"] == "queued"


# ── AP-D5 대체 ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_새_차수가_오면_도는_해석은_끝까지_안_낸_해석은_취소_보고서는_대체됨_표지(mk):
    thermal, drop = FakeAnalysis(THERMAL), FakeAnalysis(DROP)
    thermal.status_seq = ["running", "running", "running", "done"]
    h = mk(thermal, drop, settings_over={"auto_pipeline_max_concurrent": 1})
    spec = {**SPEC, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                              {"id": "drop", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"},
                              {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal", "drop"]}]}
    h.rule(spec)
    old = _ready_run(h, "TASK-A", "dv1")
    st = h.steps(old["id"])
    assert st["thermal"]["state"] == "queued" and st["drop"]["state"] == "ready", "상한 1 — drop 은 아직 안 냈다"
    h.src.add("TASK-A", "dv2", ref="p-2", sha="d" * 64, at=h.t + 1)
    h.tick(10)
    h.tick(700)
    old_run = h.store.get_run(old["id"])
    new = [r for r in h.runs() if r["revision"] == "dv2"][0]
    assert old_run["state"] == "superseded" and old_run["superseded_by"] == new["id"]
    st = h.steps(old["id"])
    assert st["drop"]["state"] == "cancelled" and st["drop"]["error"] == "superseded"
    assert st["thermal"]["state"] in ("queued", "running"), "도는 해석은 끝까지 둔다"
    for _ in range(6):
        h.tick(120)
    st = h.steps(old["id"])
    assert st["thermal"]["state"] == "done"
    assert st["summary"]["state"] == "done" and "대체됨 — 차수 dv2" in st["summary"]["report_md"]
    assert h.store.get_run(old["id"])["ended_at"], "대체된 실행도 단계가 다 끝나면 닫힌다"


# ── upstream(계약 v1.1 — analysis → analysis) ───────────────────────────────────────────────────────────────────────
UP_SPEC = {**SPEC, "steps": [{"id": "odb", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"},
                             {"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default", "needs": ["odb"]},
                             {"id": "summary", "kind": "report", "report": "summary", "needs": ["odb", "thermal"]}]}


def test_앞_해석이_끝나면_그_봉투를_upstream_으로_넘기고_지문에_넣는다(mk):
    odb, thermal = FakeAnalysis(DROP, sync=True), FakeAnalysis(THERMAL, sync=True)
    h = mk(odb, thermal)
    h.rule(UP_SPEC)
    run = _ready_run(h)
    st = h.steps(run["id"])
    assert st["odb"]["state"] == "done" and st["thermal"]["state"] == "done"
    chk = [a for bk, o, a in h.gw.calls if o == "auto_check" and bk == THERMAL][0]
    sub = [a for bk, o, a in h.gw.calls if o == "auto_submit" and bk == THERMAL][0]
    assert chk["upstream"]["odb"]["artifacts"] == [{"kind": "d3plot", "location": "/cluster/run/1"}]
    assert sub["upstream"]["odb"]["run_ref"] == st["odb"]["run_ref"]
    assert [a for bk, o, a in h.gw.calls if o == "auto_check" and bk == DROP][0].get("upstream") is None
    assert st["thermal"]["idem_key"] != st["odb"]["idem_key"]


def test_앞_해석이_실패하면_뒤_해석은_upstream_failed_로_건너뛴다(mk):
    odb, thermal = FakeAnalysis(DROP, sync=True), FakeAnalysis(THERMAL, sync=True)
    odb.result_over = {"verdict": "엉터리"}
    h = mk(odb, thermal)
    h.rule(UP_SPEC)
    run = _ready_run(h)
    st = h.steps(run["id"])
    assert st["odb"]["state"] == "failed" and st["thermal"]["state"] == "skipped" and st["thermal"]["error"] == "upstream_failed:odb"
    assert h.gw.count("auto_check", THERMAL) == 0


def test_그림자에서_뒤_해석은_앞_결과를_기다린다고_적는다(mk):
    h = mk(FakeAnalysis(DROP), FakeAnalysis(THERMAL))
    h.rule({**UP_SPEC, "stage": "shadow"})
    run = _ready_run(h)
    assert h.store.get_run(run["id"])["state"] == "planned"
    st = h.steps(run["id"])
    assert st["odb"]["state"] == "ready" and st["thermal"]["state"] == "pending" and "앞 해석(odb)" in st["thermal"]["error"]


# ── 재기동 · 잠금 · 취소 ────────────────────────────────────────────────────────────────────────────────────────────
def test_포털이_다시_떠도_도는_단계를_이어_묻는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    run = _ready_run(h)
    h.engine = h.new_engine()                         # 새 프로세스 — 상태는 원장에만
    h.tick(120)
    h.tick(120)
    assert h.steps(run["id"])["thermal"]["state"] == "done"


def test_박자는_한_번에_하나만(mk):
    h = mk(FakeAnalysis(THERMAL))
    other = h.new_engine()
    assert h.store.lock(other.holder, h.t)
    assert h.tick(0) == {"skipped": "locked"}, "다른 프로세스가 원장 잠금을 쥐면 건너뛴다"
    h.store.unlock(other.holder)
    assert "skipped" not in h.tick(0)


def test_사람의_취소는_안_낸_단계를_끝내고_도는_단계는_auto_cancel_이_있으면_부른다(mk):
    thermal, drop = FakeAnalysis(THERMAL, with_cancel=True), FakeAnalysis(DROP)
    h = mk(thermal, drop, settings_over={"auto_pipeline_max_concurrent": 1})
    spec = {**SPEC, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                              {"id": "drop", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"},
                              {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal", "drop"]}]}
    h.rule(spec)
    run = _ready_run(h)
    got = h.loop.run_until_complete(h.engine.cancel(run["id"], "boss@example.com"))
    assert got["cancelled"] == ["drop", "summary"] and got["left_running"] == ["thermal"] and got["auto_cancel"]["thermal"] == "ok"
    assert h.store.get_run(run["id"])["state"] == "cancelled"
    h.tick(120)
    assert h.steps(run["id"])["thermal"]["state"] == "cancelled"
    assert h.store.get_run(run["id"])["ended_at"]


def test_게이트웨이가_내려가도_박자는_죽지_않는다(mk):
    h = mk(FakeAnalysis(THERMAL))
    h.rule()
    h.gw.down = True
    out = h.tick(1)
    assert "error" in out and h.engine.last_error
    h.gw.down = False
    assert not h.tick(1).get("error")


def test_결과_모름_횟수는_박자마다_하나씩만_오른다(mk):
    """한 박자 안에서 단계를 여러 번 훑어도(다른 단계가 나아가면 다시 훑는다) 밀린 확인은 그 박자에 한 번만 센다 — 상한이 박자 수로 읽힌다."""
    h = mk(FakeAnalysis(THERMAL), FakeAnalysis(DROP))
    h.rule({**SPEC, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                              {"id": "drop", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"}]})
    h.gw.unreachable.add(DROP)
    run = _ready_run(h)
    assert h.steps(run["id"])["drop"]["attempts"] == 1
    h.tick(60)
    assert h.steps(run["id"])["drop"]["attempts"] == 2
