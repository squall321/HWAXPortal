# 챗 화면의 분석 루틴 상태를 node 로 돌려 본다 — SSE routine 프레임 합치기 · 실행 보기 바꾸기 · 다시 읽기 간격 · 보내는 꼴 · 저장 · 되살리기 · 받는 중의 단추 · 보고서 보기 · RA 초안 올리기 · 화면에 보일 때만 읽기 · 누른 뒤 포커스와 낭독기 알림(헤드리스 브라우저)(docs/analysis-routines R3)
"""R3-design §6 — 화면의 루틴은 세 자리에서 말없이 사라질 수 있다.

  · 파서(chat.api.ts dispatch) — switch 에 자리가 없는 이벤트는 버린다. `routine` 에 자리가 있어야 onRoutine 에 닿는다.
  · 보내는 꼴 — 포털 RoutineReq 는 모르는 칸을 422 로 거절하고(extra=forbid), delib_opts 에 넣으면 심의 손잡이 길로 새어 버려진다.
    본문 맨 위 칸 `routine` 이다. 새 실행은 id · version · inputs, 이어서는 run_id 하나.
  · 저장 — 브라우저 사본은 글이 빈 어시스턴트 메시지를 버리고, 서버 사본에서 되살리는 쪽은 meta 의 모르는 칸을 버린다. 루틴 턴은
    보고서(token) 전까지 글이 비고 실행은 서버에서 계속 돈다 — 실행 id 를 잃으면 '이어서' · 보고서 읽기가 닿을 곳이 없다.

합치기(mergeRoutine)는 다시 붙기가 지금까지의 프레임을 다시 보내도 결과가 같아야 하고, 칸이 빠진 프레임에서 던지지 않아야 한다.
실행 보기(routineFromRunView)는 포털의 실제 run_view 가 만든 꼴로 본다 — 손으로 적은 꼴은 양쪽이 같이 틀리면 통과한다.

프론트에는 단위 시험 러너가 없다 — TS 파일을 옮겨 적어(transpile) node 로 부른다(test_front_window_payload 의 _node,
test_stream_liveness_units 의 SSE 본문 대역과 같은 길). React 조각(ChatContext.tsx)은 소스에서 그 자리만 읽는다.
"""
import html
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
from tests.test_front_window_payload import _FE, _SRC, _msg, _node

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

RUN = "8f3c2a9e0d1b4c5aa6e7f8091a2b3c4d"
_ROUTINE_TS = ["components/chat/routine.ts"]
_REQ = "const R = require('./components/chat/routine.js');"

# 에이전트 서버 실행기가 내는 꼴(R3-design §3.2) — 루틴은 contracts.md §1 의 예시(기준 키 → 시장불량 이력 → PLM → 메커니즘)
PLAN = {"kind": "plan", "run_id": RUN, "routine_id": "rt-swelling", "version_no": 3, "title": "시장불량 원인 분석",
        "purpose": "S26 의 스웰링 시장불량 — 원인 · 시험 · 대책", "state": "running", "resumed": False,
        "steps": [{"id": "anchor", "title": "기준 키", "kind": "platform", "state": "pending",
                   "backends": ["rootdesigndatahub"], "label": "코어 허브"},
                  {"id": "ft", "title": "시장불량 이력", "kind": "platform", "state": "pending",
                   "backends": ["failuretrace"], "label": "FailureTrace"},
                  {"id": "plm", "title": "PLM 문제점", "kind": "platform", "state": "not_connected",
                   "backends": ["plm"], "label": "PLM"},
                  {"id": "delib", "title": "메커니즘", "kind": "deliberation", "state": "pending",
                   "backends": ["hwax-deliberation"], "label": "전문가 심의"}],
        "report": {"title": "S26 스웰링 분석", "sections": ["anchor", "ft", "plm", "delib", "insight"], "upload": "auto"}}


def _step(step: str, title: str, **kw) -> dict:
    return {"kind": "step", "run_id": RUN, "step": step, "title": title, "state": "running", **kw}


def _done(step: str, state: str, summary: str, calls: int, reason: str = "", flags=()) -> dict:
    return {"kind": "step_done", "run_id": RUN, "step": step, "state": state, "reason": reason, "summary": summary,
            "flags": list(flags), "calls": calls}


ANCHOR_OK = _done("anchor", "ok", "S26 은 코어 허브의 plm_model SM-S938 이다 [anchor.c1]", 1)
CANDS = [{"label": "SM-S938(국내)", "key": "SM-S938"}, {"label": "SM-S938N(북미)", "key": "SM-S938N"}]
GATE_PATH = [
    PLAN,
    _step("anchor", "기준 키"),
    ANCHOR_OK,
    _step("ft", "시장불량 이력"),
    _done("ft", "ambiguous", "SM-S938 · SM-S938N 두 계열에 기록이 있다 [ft.c2]", 3, reason="모델 후보가 둘이다",
          flags=["키 값이 결과에 없어 뺐다 — model_key"]),
    {"kind": "gate", "run_id": RUN, "step": "ft", "candidates": CANDS, "message": "어느 모델로 이어 갈지 고른다"},
    {"kind": "done", "run_id": RUN, "state": "waiting"},
]
DELIB_PROGRESS = _step("delib", "메커니즘", detail="라운드 2/3 · 좌석 발언")
DONE_PATH = [
    PLAN,
    _step("anchor", "기준 키"),
    ANCHOR_OK,
    _step("ft", "시장불량 이력"),
    _done("ft", "ok", "스웰링 기록 41건 — 3분기에 몰린다 [ft.c1] [ft.c2]", 2),
    _step("delib", "메커니즘"),
    DELIB_PROGRESS,
    _done("delib", "ok", "결정문 — 전해액 분해 가스가 원인이다 [delib.c3]", 3),
    {"kind": "report", "run_id": RUN, "ra_upload": "auto", "ra_report_id": "RA-2026-1029", "ra_error": None, "ra_next": None,
     "coverage": {"counts": {"ok": 3, "not_connected": 1}, "not_ok": [{"step": "plm", "state": "not_connected"}]},
     "warnings": ["출처 없는 수치 문단 1"]},
    {"kind": "done", "run_id": RUN, "state": "done"},
]


def _merge(events: list, prev: dict | None = None) -> dict:
    return _node(_ROUTINE_TS, _REQ + " let s = input.prev || undefined; for (const e of input.events) s = R.mergeRoutine(s, e); out(s);",
                 {"events": events, "prev": prev})


def _plan_step(sid: str, **over) -> dict:
    s = next(x for x in PLAN["steps"] if x["id"] == sid)
    return {k: s[k] for k in ("id", "title", "kind", "backends", "label")} | over


# ── 합치기(mergeRoutine) ─────────────────────────────────────────────────────────────────────────────
def test_계획에서_고를_것까지_프레임을_합친다():
    got = _merge(GATE_PATH)
    assert got == {
        "run_id": RUN, "routine_id": "rt-swelling", "title": "시장불량 원인 분석", "state": "waiting", "resumed": False,
        "steps": [
            _plan_step("anchor", state="ok", summary=ANCHOR_OK["summary"], reason="", flags=[], calls=1),
            _plan_step("ft", state="ambiguous", summary="SM-S938 · SM-S938N 두 계열에 기록이 있다 [ft.c2]",
                       reason="모델 후보가 둘이다", flags=["키 값이 결과에 없어 뺐다 — model_key"], calls=3),
            _plan_step("plm", state="not_connected"),
            _plan_step("delib", state="pending"),
        ],
        "gate": {"step": "ft", "candidates": [{"key": c["key"], "label": c["label"]} for c in CANDS],
                 "message": "어느 모델로 이어 갈지 고른다"},
    }


def test_보고서까지_간_실행은_끝남이고_진행_한_줄은_단계가_닫히면_지운다():
    mid = _merge(DONE_PATH[: DONE_PATH.index(DELIB_PROGRESS) + 1])
    assert mid["state"] == "running" and mid["steps"][3]["state"] == "running"
    assert mid["steps"][3]["detail"] == "라운드 2/3 · 좌석 발언", "심의 진행 한 줄이 단계에 실린다"
    got = _merge(DONE_PATH)
    assert got["state"] == "done" and "gate" not in got
    assert [(s["id"], s["state"], s.get("calls")) for s in got["steps"]] == [
        ("anchor", "ok", 1), ("ft", "ok", 2), ("plm", "not_connected", None), ("delib", "ok", 3)]
    assert "detail" not in got["steps"][3], "닫힌 단계에 '라운드 2/3' 이 남는다"
    assert got["report"] == {"ra_upload": "auto", "ra_report_id": "RA-2026-1029", "ra_error": None, "ra_next": None,
                             "warnings": ["출처 없는 수치 문단 1"]}


def test_다시_붙기가_같은_프레임을_다시_보내도_결과가_같다():
    """D8 — 같은 프로세스에 살아 있는 실행에 다시 붙으면 지금까지 낸 프레임을 다시 보낸다(두 번째 구독)."""
    assert _merge(DONE_PATH + DONE_PATH) == _merge(DONE_PATH)
    assert _merge(GATE_PATH, prev=_merge(GATE_PATH)) == _merge(GATE_PATH)


def test_이어서의_계획은_원장의_상태를_따르되_받은_요약을_남긴다():
    before = _merge(GATE_PATH[:3])                     # 기준 키까지 끝난 뒤 끊겼다
    resumed = {**PLAN, "resumed": True, "steps": [_plan_step("anchor", state="ok"), _plan_step("ft", state="pending"),
                                                  _plan_step("plm", state="not_connected"), _plan_step("delib", state="pending")]}
    got = _merge([resumed], prev=before)
    assert got["resumed"] is True and got["state"] == "running"
    assert got["steps"][0]["summary"] == ANCHOR_OK["summary"] and got["steps"][0]["calls"] == 1, "계획을 다시 세우며 받은 요약을 지웠다"
    # 고를 것이 남은 메시지에 running 계획이 오면(고른 뒤 이어서) 고를 것을 지운다
    picked = _merge([resumed], prev=_merge(GATE_PATH))
    assert picked["state"] == "running" and "gate" not in picked


def test_이어_돌림은_실행이_이어_돈_계획에만_단다():
    """실행기는 run_id 요청이면 늘 plan 에 resumed 를 단다 — RA 초안 올리기 · '이미 끝났다' · 고를 것에서 선 실행의 다시 보냄도. 그 계획은
    끝났거나 선 실행이라 건너뛰고 이어 돈 것이 없는데 '이어 돌림(끝난 단계는 건너뛰고 이어서 돌았습니다)' 표지가 끝남 곁에 남았다(2차 #16).
    다시 붙기 · 원장에서 잇기(도는 계획)만 단다. resumed 가 거짓인 계획은 종전대로 거짓이다."""
    states = ["running", "queued", "done", "failed", "cancelled", "waiting", "interrupted"]
    got = _node(_ROUTINE_TS, _REQ + " out(input.map((p) => R.mergeRoutine(undefined, p).resumed));",
                [{**PLAN, "state": st, "resumed": True} for st in states] + [{**PLAN, "state": "done", "resumed": False}])
    assert dict(zip(states, got[:-1], strict=True)) == {
        "running": True, "queued": True, "done": False, "failed": False, "cancelled": False, "waiting": False,
        "interrupted": False}, "끝났거나 선 실행의 계획에 '이어 돌림' 을 달았다"
    assert got[-1] is False


def test_모르는_kind_는_그대로_두고_처음이면_빈_실행을_만든다():
    got = _node(_ROUTINE_TS, _REQ + " const prev = R.mergeRoutine(undefined, input);"
                " const same = R.mergeRoutine(prev, { kind: 'heartbeat', run_id: 'x' }) === prev;"
                " out({ same, fresh: R.mergeRoutine(undefined, { kind: 'zzz', run_id: 'r9' }) });", PLAN)
    assert got["same"] is True, "모르는 프레임이 실행 상태를 바꿨다"
    assert got["fresh"] == {"run_id": "r9", "title": "", "state": "running", "steps": []}


def test_칸이_빠지거나_꼴이_다른_프레임에서_던지지_않는다():
    evs = [None, {}, {"kind": "plan"}, {"kind": "plan", "steps": [None, 3, "x", {"title": "id 없음"}, {"id": "a"}]},
           {"kind": "step"}, {"kind": "step", "step": "b"}, {"kind": "step_done", "step": "c"},
           {"kind": "step_done", "step": "a", "calls": "3", "flags": "x", "summary": 5},
           {"kind": "gate"}, {"kind": "gate", "candidates": [None, {"label": "라벨만"}, {"key": "k1"}, {"key": 7, "label": "칠"}]},
           {"kind": "report"}, {"kind": "report", "ra_report_id": 12, "warnings": ["w", 3]},
           {"kind": "done"}, {"kind": "done", "state": "failed", "reason": "실행기 오류"}]
    trail = _node(_ROUTINE_TS, _REQ + " let s; const t = []; for (const e of input) { s = R.mergeRoutine(s, e); t.push(s); } out(t);", evs)
    assert trail[0] == {"run_id": "", "title": "", "state": "running", "steps": []}
    gated = trail[9]
    assert gated["state"] == "waiting" and gated["gate"] == {"step": "", "candidates": [{"key": "k1", "label": "k1"},
                                                                                       {"key": "7", "label": "칠"}]}
    assert trail[12]["gate"] == gated["gate"], "끝 프레임에 상태가 없으면 고를 것을 지우지 않는다"
    assert trail[-1] == {
        "run_id": "", "title": "", "state": "failed", "reason": "실행기 오류",
        "steps": [{"id": "a", "title": "a", "kind": "", "state": "pending"},
                  {"id": "b", "title": "b", "kind": "", "state": "running"},
                  {"id": "c", "title": "c", "kind": "", "state": "pending"}],
        "report": {"ra_report_id": 12, "warnings": ["w"]},
    }, "꼴이 다른 칸(호출 수 '3' · 표지 'x' · 요약 5)은 받지 않고, 끝난 실행에서는 고를 것을 지운다"


def test_실행_상태_판정():
    states = ["queued", "running", "waiting", "done", "failed", "cancelled", "interrupted", ""]
    got = _node(_ROUTINE_TS, _REQ + " out(input.map((s) => [R.isRoutineLive(s), R.isRoutineTerminal(s)]));", states)
    assert dict(zip(states, map(tuple, got), strict=True)) == {
        "queued": (True, False), "running": (True, False), "waiting": (False, False), "done": (False, True),
        "failed": (False, True), "cancelled": (False, True), "interrupted": (False, False), "": (False, False)}


def test_라벨은_포털_원장의_상태와_같은_글이다():
    from app.procedures.routines import RUN_STATES, STAGE_STATES, STATE_LABEL

    got = _node(_ROUTINE_TS, _REQ + " out({ step: R.ROUTINE_STEP_LABEL, run: R.ROUTINE_RUN_LABEL, ready: R.READY_LABEL,"
                " chain: R.chain(input) });", [{"title": "기준 키"}, {"title": "시장불량 이력"}, {"title": "메커니즘"}])
    assert got["step"] == STATE_LABEL and set(got["step"]) == set(STAGE_STATES)
    assert set(got["run"]) == set(RUN_STATES)
    assert set(got["ready"]) == {"allowed", "denied", "not_connected", "unavailable"}
    assert got["chain"] == "기준 키 → 시장불량 이력 → 메커니즘"
    view = (_SRC / "pages/procedures/RoutinesView.tsx").read_text(encoding="utf-8")
    assert "from '../../components/chat/routine'" in view
    assert "const READY_LABEL" not in view and "function chain(" not in view, "절차 화면이 라벨 · 사슬 글을 따로 쥔다(두 벌)"


# ── 실행 보기(routineFromRunView) — 포털의 실제 run_view 가 만든 꼴 ─────────────────────────────────────────
_BLOCKED = {"empty": "continue", "denied": "skip", "unavailable": "skip"}


def _plan() -> dict:
    def ps(sid, title, kind, backends, allowed, goal, label=None, **kw):
        return {"id": sid, "title": title, "kind": kind, "backends": backends, "allowed": allowed, "goal": goal,
                "uses": kw.get("uses", []), "expect": {"keys": kw.get("keys", [])}, "budget": {"calls": 8, "seconds": 300},
                "blocked": kw.get("blocked", _BLOCKED), "deliberation": kw.get("deliberation"),
                "readiness": kw.get("readiness", {"state": "allowed", "reason": ""}), **({"label": label} if label else {})}
    return {
        "steps": [
            ps("anchor", "기준 키", "platform", ["rootdesigndatahub"], {"rootdesigndatahub": ["object_resolve"]},
               "{{model}} 을 코어 허브의 plm_model 로 푼다", label="코어 허브", keys=["model_key"],
               blocked={"empty": "stop", "denied": "stop", "unavailable": "stop"}),
            ps("ft", "시장불량 이력", "platform", ["failuretrace"], {"failuretrace": ["pd_defect"]},
               "{{steps.anchor.model_key}} 의 {{symptom}} 불량 기록", uses=["anchor"], keys=["model_key"]),
            ps("plm", "PLM 문제점", "platform", ["plm"], {"plm": []}, "PLM 문제점(enrich=0)",
               readiness={"state": "not_connected", "reason": "PLM 토큰이 없다"}),
            ps("delib", "메커니즘", "deliberation", ["hwax-deliberation"],
               {"hwax-deliberation": ["deliberate_start", "deliberate_status", "deliberate_result"]}, "불량의 메커니즘을 밝힌다",
               uses=["ft"], deliberation={"job": "mechanism", "chair_template": None}),
        ],
        "report": {"title": "{{model}} {{symptom}} 분석", "sections": ["anchor", "ft", "plm", "delib", "insight"],
                   "ra": {"upload": "auto"}},
        "limits": {"minutes": 60, "calls": 60}, "purpose": "{{model}} 의 {{symptom}} 시장불량 — 원인 · 시험 · 대책",
        "routine_title": "시장불량 원인 분석",
    }


def _stage(sid: str, state: str, calls: int = 0, reason: str | None = None, envelope: dict | None = None, flags=None) -> dict:
    return {"run_id": "r1", "step_id": sid, "ix": 0, "state": state, "calls": calls, "reason": reason, "envelope": envelope,
            "flags": flags or [], "started_at": None, "ended_at": None}


def _run_view(state: str, stages: list[dict], report_md: str | None = None, ra_report_id: str | None = None) -> dict:
    from app.procedures.routine_routes import run_view

    now = int(time.time())
    run = {"id": "r1", "owner_sub": "koo.park@example.com", "routine_id": "rt-swelling", "version_id": "v3", "version_no": 3,
           "title": "시장불량 원인 분석", "inputs": {"model": "S26", "symptom": "스웰링"}, "plan": _plan(), "executor": "chat",
           "conversation_id": "conv-1", "state": state, "reason": None, "calls": 4, "started_at": now - 120,
           "deadline": now + 3000, "ended_at": None, "report_md": report_md, "ra_report_id": ra_report_id, "ra_error": None,
           "report": None}
    return json.loads(json.dumps(run_view(run, stages), ensure_ascii=False))


def _from_view(view: dict) -> dict:
    return _node(_ROUTINE_TS, _REQ + " out(R.routineFromRunView(input));", view)


def test_고를_것을_기다리는_실행_보기를_메시지_꼴로_바꾼다():
    ft_env = {"status": "ambiguous", "summary": "두 계열에 기록이 있다 [ft.c2]", "keys": {},
              "findings": [{"text": "3분기에 몰린다", "refs": ["ft.c2"]}], "candidates": CANDS}
    view = _run_view("waiting", [
        _stage("anchor", "ok", 1, envelope={"summary": "SM-S938 이다 [anchor.c1]", "keys": {"model_key": "SM-S938"}}),
        _stage("ft", "ambiguous", 3, reason="모델 후보가 둘이다", envelope=ft_env, flags=["키 값이 결과에 없어 뺐다 — model_key"]),
        _stage("plm", "not_connected", reason="PLM 토큰이 없다"),
        # delib 은 원장에 행이 없다(서버가 상태를 null 로 준다)
    ])
    assert view["steps"][3]["state"] is None, "시험의 전제 — 행이 없는 단계는 null 이다"
    got = _from_view(view)
    assert got == {
        "run_id": "r1", "routine_id": "rt-swelling", "title": "시장불량 원인 분석", "state": "waiting",
        "steps": [
            {"id": "anchor", "title": "기준 키", "kind": "platform", "state": "ok", "calls": 1, "summary": "SM-S938 이다 [anchor.c1]",
             "backends": ["rootdesigndatahub"], "label": "코어 허브"},
            {"id": "ft", "title": "시장불량 이력", "kind": "platform", "state": "ambiguous", "calls": 3,
             "summary": "두 계열에 기록이 있다 [ft.c2]", "reason": "모델 후보가 둘이다",
             "flags": ["키 값이 결과에 없어 뺐다 — model_key"], "backends": ["failuretrace"]},
            {"id": "plm", "title": "PLM 문제점", "kind": "platform", "state": "not_connected", "calls": 0,
             "reason": "PLM 토큰이 없다", "backends": ["plm"]},
            {"id": "delib", "title": "메커니즘", "kind": "deliberation", "state": "pending", "calls": 0,
             "backends": ["hwax-deliberation"]},
        ],
        "gate": {"step": "ft", "candidates": [{"key": c["key"], "label": c["label"]} for c in CANDS]},
    }


def test_보고서를_낸_실행_보기는_RA_결과를_싣는다():
    closed = [_stage(s, st, n, envelope={"summary": f"{s} 요약"}) for s, st, n in
              (("anchor", "ok", 1), ("ft", "ok", 2), ("plm", "not_connected", 0), ("delib", "ok", 3))]
    got = _from_view(_run_view("done", closed, report_md="# 시장불량 원인 분석\n…", ra_report_id="RA-2026-1029"))
    assert got["state"] == "done" and "gate" not in got and "reason" not in got
    assert got["report"] == {"ra_upload": "auto", "ra_report_id": "RA-2026-1029", "ra_error": None}
    assert [s["state"] for s in got["steps"]] == ["ok", "ok", "not_connected", "ok"]
    running = _from_view(_run_view("running", closed[:1]))
    assert "report" not in running, "보고서가 없는 실행에 RA 칸을 만들지 않는다"


# ── 다시 읽기 간격(routineFingerprint · nextRoutinePoll) — 흐르지 않는 메시지가 도는 실행을 읽는 셈 ─────────────────────
def _ft_view(calls: int, state: str = "running", run_state: str = "running") -> dict:
    """기준 키는 닫혔고 시장불량 이력이 도는 실행 — 포털의 실제 run_view 꼴."""
    anchor = _stage("anchor", "ok", 1, envelope={"summary": "SM-S938 이다 [anchor.c1]"})
    return _run_view(run_state, [anchor, _stage("ft", state, calls)])


def test_다시_읽기_지문은_실행_상태와_단계의_상태_호출_수만_본다():
    """흐르지 않는 메시지가 도는 실행을 다시 읽을 때 '바뀌었나' 를 가르는 지문이다 — 단계 칩이 그리는 것(실행 상태 · 단계 상태 · 호출 수)만
    본다. 마감 · 시작 시각 · 요약처럼 칩에 안 보이는 칸이 바뀐 것은 그대로로 센다 — 그래야 긴 심의 단계 동안 늦출 수 있다."""
    base = _ft_view(1)
    moved = json.loads(json.dumps(base))
    moved["run"]["deadline"] += 3600                   # 이어서가 마감을 옮겼다(R3 §3.5-1)
    moved["run"]["started_at"] -= 7
    moved["steps"][0]["summary"] = "요약 글만 다르다"
    views = [base, moved, _ft_view(2), _ft_view(2, state="ok"), _ft_view(1, run_state="waiting")]
    fp = _node(_ROUTINE_TS, _REQ + " out(input.map((v) => R.routineFingerprint(R.routineFromRunView(v))));", views)
    assert fp[0] == fp[1], "칩에 안 보이는 칸(마감 · 시작 시각 · 요약)이 바뀐 것을 바뀜으로 셌다 — 긴 단계 동안 늦추지 못한다"
    assert len({fp[0], *fp[2:]}) == 4, "호출 수 · 단계 상태 · 실행 상태가 바뀐 것을 놓쳤다"


def test_다시_읽기는_그대로가_12번_잇달면_30초로_늦추고_바뀌면_5초로_돌아온다():
    """R3 §6 — 실행이 도는 동안 5초마다 읽되 심의 단계는 분 ~ 시간을 돈다. 실행 · 단계가 12번 잇달아(약 1분) 그대로면 30초로 늦추고,
    무엇이 바뀌면 5초로 돌아와 다시 센다. 사람이 이어서 · 고르기 · 멈춤을 누르면 화면이 셈을 처음(null)부터 다시 세운다 — 그 첫 읽기도 5초다."""
    a, b, c = _ft_view(1), _ft_view(2), _ft_view(2, state="ok")
    got = _node(_ROUTINE_TS, _REQ + " let p = null; const t = [];"
                " for (const v of input) { p = R.nextRoutinePoll(p, R.routineFromRunView(v)); t.push([p.same, p.delay]); }"
                " out({ t, slow: p, reset: R.nextRoutinePoll(null, R.routineFromRunView(input[0])), fast: R.ROUTINE_POLL_MS });",
                [a] * 14 + [b] * 13 + [c] * 13)
    t = got["t"]
    assert [d for _, d in t[:12]] == [5000] * 12, "처음 1분은 5초마다 읽는다"
    assert t[12:14] == [[12, 30000], [13, 30000]], "12번 잇달아 그대로면(약 1분) 30초로 늦춘다"
    assert t[14] == [0, 5000], "호출 수가 늘었는데 늦춘 채로 둔다"
    assert [d for _, d in t[15:26]] == [5000] * 11 and t[26] == [12, 30000], "바뀐 뒤에는 처음부터 다시 12번을 센다"
    assert t[27] == [0, 5000], "단계가 닫혔는데 늦춘 채로 둔다"
    assert got["slow"]["delay"] == 30000, "시험의 전제 — 마지막 셈은 늦춘 간격이다"
    assert (got["reset"]["same"], got["reset"]["delay"]) == (0, 5000), "사람이 누른 뒤(셈을 null 부터)의 첫 읽기는 5초다"
    assert got["fast"] == 5000, "숨은 탭 · 읽기 실패 뒤 다시 보기 간격이 처음 간격과 다르다"


# ── 파서 · 보내는 꼴(chat.api.ts) — 청크를 흘리는 본문 대역(test_stream_liveness_units 와 같은 길) ─────────────
_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
// chat.api.ts 가 값으로 끌어오는 파일까지(lib/chatErrors → state/chatStore) + 합치기 조각
for (const rel of ['api/chat.api.ts', 'lib/chatErrors.ts', 'state/chatStore.ts', 'components/chat/routine.ts']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });
  const dst = path.join(__dirname, rel.replace(/\.ts$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
// 네트워크 층만 대역 — 보낸 본문을 적어 두고, 청크 목록을 그대로 흘리는 본문을 돌려준다.
fs.writeFileSync(path.join(__dirname, 'api/client.js'),
  "exports.apiFetch = async (p, init) => { global.__sent.push({ path: p, body: JSON.parse(init.body) });" +
  " return new Response(new ReadableStream({ start(c) {" +
  " for (const x of global.__chunks) c.enqueue(new TextEncoder().encode(x)); c.close(); } })); };\n");
global.document = { cookie: '' };
const { streamChat } = require('./api/chat.api.js');
const R = require('./components/chat/routine.js');
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
(async () => {
  const out = [];
  for (const c of req.cases) {
    global.__chunks = c.chunks; global.__sent = [];
    const calls = []; let state;
    const log = (name) => (e) => calls.push(e === undefined ? [name] : [name, e]);
    await streamChat(c.message, { ...c.opts, onStatus: log('status'), onToken: log('token'), onResult: log('result'),
      onDelib: log('delib'), onError: log('error'), onDone: log('done'),
      onRoutine: (e) => { calls.push(['routine', e]); state = R.mergeRoutine(state, e); } });
    out.push({ calls, sent: global.__sent, state: state === undefined ? null : state });
  }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream(cases: list[dict]) -> list[dict]:
    work = Path(tempfile.mkdtemp(prefix="fe-routine-"))
    try:
        (work / "drive.cjs").write_text(_DRIVER, encoding="utf-8")
        r = subprocess.run(["node", "drive.cjs", str(_SRC)], cwd=str(work), capture_output=True, text=True, timeout=120,
                           input=json.dumps({"cases": cases}, ensure_ascii=False),
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(_FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(work, ignore_errors=True)


_STATUS_START = {"step": "도구 호출: object_resolve", "tool": "object_resolve", "via": "rootdesigndatahub", "call": "k1",
                 "routine_step": "anchor"}
_STATUS_END = {**_STATUS_START, "step": "도구 완료: object_resolve", "ok": True, "routine_call": "anchor.c1"}
_REPORT_MD = "# S26 스웰링 분석\n\n## 기준 키\nSM-S938 [anchor.c1]"


def test_파서가_routine_프레임을_onRoutine_으로_보내고_나머지는_그대로다():
    frames = [_sse("routine", PLAN), _sse("routine", _step("anchor", "기준 키")), _sse("status", _STATUS_START),
              _sse("status", _STATUS_END), _sse("routine", ANCHOR_OK), _sse("token", {"delta": _REPORT_MD}),
              _sse("result", {"type": "text", "content": _REPORT_MD}), _sse("routine", DONE_PATH[-2]),
              _sse("routine", {"kind": "done", "run_id": RUN, "state": "done"}), _sse("done", {})]
    # 청크 경계가 프레임 경계와 안 맞아도 같다 — 한 프레임이 두 청크에 걸친다
    blob = "".join(frames)
    torn = [blob[:37], blob[37:500], blob[500:]]
    whole, split = _stream([{"message": "루틴: 시장불량 원인 분석", "opts": {}, "chunks": frames},
                            {"message": "루틴: 시장불량 원인 분석", "opts": {}, "chunks": torn}])
    assert [c[0] for c in whole["calls"]] == ["routine", "routine", "status", "status", "routine", "token", "result",
                                              "routine", "routine", "done"]
    assert whole["calls"][0][1] == PLAN and whole["calls"][4][1] == ANCHOR_OK, "프레임이 그대로 닿아야 한다"
    assert split["calls"] == whole["calls"]
    assert whole["state"]["state"] == "done" and whole["state"]["steps"][0]["state"] == "ok"
    assert whole["state"]["report"]["ra_report_id"] == "RA-2026-1029"


def test_보내는_꼴은_본문_맨_위_routine_이고_아는_칸만_싣는다():
    done = [_sse("done", {})]
    new_run, resume, plain = _stream([
        # title 은 보이기용(켜 둔 루틴의 칸) — 실리면 포털 RoutineReq(extra=forbid)가 422 로 턴을 통째로 거절한다
        {"message": "루틴: 시장불량 원인 분석", "chunks": done,
         "opts": {"routine": {"id": "rt-swelling", "version": 3, "inputs": {"model": "S26", "symptom": "스웰링"},
                              "title": "시장불량 원인 분석"}, "delibOpts": {"rounds": 4}}},
        {"message": "루틴 이어서: 시장불량 원인 분석", "chunks": done, "opts": {"routine": {"run_id": RUN, "id": "rt-swelling"}}},
        {"message": "그냥 질문", "chunks": done, "opts": {"delibOpts": {"rounds": 4}}},
    ])
    body = new_run["sent"][0]["body"]
    assert new_run["sent"][0]["path"] == "/agent/chat"
    assert body["routine"] == {"id": "rt-swelling", "version": 3, "inputs": {"model": "S26", "symptom": "스웰링"}}
    assert body["delib_opts"] == {"rounds": 4} and "routine" not in body["delib_opts"], "루틴이 심의 손잡이 길로 샌다"
    assert resume["sent"][0]["body"]["routine"] == {"run_id": RUN}, "이어서는 run_id 하나다(서버는 나머지를 안 본다)"
    assert "routine" not in plain["sent"][0]["body"]


# ── 챗 상태(ChatContext.tsx) — React 조각이라 소스에서 그 자리만 읽는다 ────────────────────────────────────────
def _ctx() -> str:
    return (_SRC / "state/ChatContext.tsx").read_text(encoding="utf-8")


def test_챗_상태는_켜_둔_루틴을_본문_맨_위로_한_번만_싣는다():
    src = _ctx()
    send = src[src.index("const sendMessage = useCallback("):src.index("// 이어하기(사람 개입 스티어링)")]
    assert "...(routineReq ? { routine: routineReq } : {})," in send, "streamChat 에 루틴을 안 싣는다"
    wire = send[send.index("...(() => {"):send.index("onStatus:")]
    assert "routine" not in wire, "루틴을 delib_opts 로 싣는다 — 포털 DelibOpts 가 모르는 칸이라 버려진다"
    assert "if (armed) setArmedRoutine(null);" in send, "켜 둔 루틴이 한 번 쓰고 꺼지지 않는다"
    assert "!can('feat:routines')" in send, "권한 없는 사람의 발화에 루틴을 싣는다(포털이 403)"
    assert "routineOpt === undefined && !extraDelibOpts" in send, "심의 넘기기 · 이어하기가 켜 둔 루틴을 가져간다"
    on_routine = send[send.index("onRoutine: (e) => {"):send.index("onTools:")]
    assert "patch(cid, botId, (m) => ({ ...m, routine: mergeRoutine(m.routine, e) }));" in on_routine


def test_다시_시도는_루틴_턴을_일반_챗으로_보내지_않는다():
    src = _ctx()
    resume = src[src.index("const resumeRoutine = useCallback("):src.index("const retryLast = useCallback(")]
    assert "sendMessage(`루틴 이어서: ${title?.trim() || id}`, undefined, { run_id: id });" in resume
    retry = src[src.index("const retryLast = useCallback("):]
    retry = retry[:retry.index("\n  }, [")]
    assert "reply?.routine?.run_id" in retry and "resumeRoutine(reply.routine.run_id, reply.routine.title)" in retry, \
        "실행 id 를 받은 루틴 턴을 다시 보내면 새 실행이 또 생긴다 — 이어서로 간다"
    assert "routineSentRef.current.get(lastUser.id)" in retry, "실행 id 전에 실패한 루틴 턴(동시 상한)이 '루틴: 제목' 질문으로 간다"
    assert "sendMessage(text, undefined, null);" in retry, "그새 켜 둔 루틴이 다시 보내는 발화에 실린다"


# ── 저장 · 되살리기 ────────────────────────────────────────────────────────────────────────────────
_ROUTINE = {"run_id": RUN, "routine_id": "rt-swelling", "title": "시장불량 원인 분석", "state": "running",
            "steps": [{"id": "anchor", "title": "기준 키", "kind": "platform", "state": "ok", "summary": "SM-S938", "calls": 1}]}


def test_브라우저_사본은_글이_빈_루틴_답도_남기고_되읽는다():
    conv = {"id": "c1", "title": "t", "createdAt": 1, "updatedAt": 2,
            "messages": [_msg("user", "루틴: 시장불량 원인 분석"), _msg("assistant", "", routine=_ROUTINE, n=1),
                         _msg("assistant", "", n=2)]}
    got = _node(["state/chatStore.ts"],
                "const S = require('./state/chatStore.js'); S.saveConversations([input]);"
                " const raw = JSON.parse(localStorage.getItem('hwax.chat.conversations'));"
                " out({ stored: raw[0].messages, loaded: S.loadConversations()[0].messages });", conv)
    assert [m["role"] for m in got["stored"]] == ["user", "assistant"], "보고서 전의 루틴 답이 버려졌거나 빈 자리가 남았다"
    assert got["stored"][1]["routine"] == _ROUTINE
    assert got["loaded"][1]["routine"] == _ROUTINE and got["loaded"][1]["text"] == ""


def test_브라우저_사본의_깨진_루틴은_되살리지_않는다():
    stored = [{"id": "c1", "title": "t", "createdAt": 1, "updatedAt": 2, "messages": [
        {"role": "assistant", "content": "a", "ts": 1, "routine": {"title": "실행 id 없음", "state": "running", "steps": []}},
        {"role": "assistant", "content": "b", "ts": 2, "routine": {"run_id": RUN, "title": "t", "state": "done", "steps": "x"}},
        {"role": "assistant", "content": "c", "ts": 3, "routine": "x"}]}]
    got = _node(["state/chatStore.ts"],
                "localStorage.setItem('hwax.chat.conversations', JSON.stringify(input));"
                " const S = require('./state/chatStore.js'); out(S.loadConversations()[0].messages.map((m) => m.routine || null));",
                stored)
    assert got == [None, {"run_id": RUN, "title": "t", "state": "done", "steps": []}, None], \
        "실행 id 없는 루틴은 버리고(화면이 빈 id 로 포털을 부른다) 단계가 목록이 아니면 빈 목록으로"


def test_서버_사본의_답_meta_에서_루틴_포인터를_되살린다():
    server = [{"role": "user", "content": "루틴: 시장불량 원인 분석", "ts": 1, "meta": {"routine": {"run_id": "user-side"}}},
              {"role": "assistant", "content": _REPORT_MD, "ts": 2,
               "meta": {"activity": [{"ts": 1, "step": "도구 완료: object_resolve", "tool": "object_resolve"}],
                        "routine": {"run_id": RUN, "routine_id": "rt-swelling", "title": "시장불량 원인 분석", "state": "done"}}},
              {"role": "assistant", "content": "a", "ts": 3, "meta": {"routine": {"title": "실행 id 없음"}}},
              {"role": "assistant", "content": "b", "ts": 4, "meta": {"routine": {"run_id": "r2"}}},
              {"role": "assistant", "content": "c", "ts": 5, "meta": None},
              # 중계(app/agent/routes.py 의 _am["routine"])가 남기는 실제 꼴 — 네 칸을 늘 싣고 모르는 값은 null 이다
              {"role": "assistant", "content": "d", "ts": 6,
               "meta": {"routine": {"run_id": "r3", "routine_id": None, "title": None, "state": None}}}]
    got = _node(["api/conversations.api.ts", "state/chatStore.ts"],
                "const { serverMessagesToLocal } = require('./api/conversations.api.js');"
                " out(serverMessagesToLocal(input).map((m) => ({ role: m.role, routine: m.routine || null,"
                " acts: (m.activity || []).length })));", server)
    assert got == [
        {"role": "user", "routine": None, "acts": 0},
        {"role": "assistant", "routine": {"run_id": RUN, "routine_id": "rt-swelling", "title": "시장불량 원인 분석",
                                          "state": "done", "steps": []}, "acts": 1},
        {"role": "assistant", "routine": None, "acts": 0},
        {"role": "assistant", "routine": {"run_id": "r2", "title": "", "state": "", "steps": []}, "acts": 0},
        {"role": "assistant", "routine": None, "acts": 0},
        {"role": "assistant", "routine": {"run_id": "r3", "title": "", "state": "", "steps": []}, "acts": 0},
    ], "단계는 비워 두고(화면이 run_id 로 포털에서 읽는다) 상태를 모르면 '' 다 — 사람 발화의 meta 는 보지 않는다"


# ── 받는 중의 단추(RoutineView) — 조각을 서버 렌더(renderToStaticMarkup)로 한 번 그린다 ─────────────────────────────
# 효과 · 네트워크는 돌지 않는다 — 메시지와 챗 상태(받는 중인가)만으로 정해지는 꼴을 본다. 조각 밖 이음매는 대역이다(루틴 권한은 있다).
# 원장을 읽어야 정해지는 꼴(자리 글의 보고서 보기 · 화면 밖에서 읽지 않기)은 아래 브라우저 시험이 본다.
_VIEW_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
// RoutineView 가 값으로 끌어오는 파일까지(lib/chatErrors → state/chatStore)
for (const rel of ['components/chat/RoutineView.tsx', 'components/chat/routine.ts', 'lib/chatErrors.ts', 'state/chatStore.ts']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX } });
  const dst = path.join(__dirname, rel.replace(/\.tsx?$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
const stub = (rel, body) => {
  const p = path.join(__dirname, rel); fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, body); };
stub('api/routines.api.js', "for (const k of ['getRun', 'getRunReport', 'pickCandidate', 'cancelRun'])" +
  " exports[k] = async () => { throw new Error('시험에서 부르지 않는다'); };\n");
stub('auth/useCan.js', "exports.useCan = () => () => true;\n");
stub('state/ChatContext.js', "exports.useChat = () => ({ streaming: global.__streaming, resumeRoutine: async () => {} });\n");
stub('components/chat/renderers/TextBlock.js', "exports.TextBlock = (p) => p.text;\n");
const React = require('react'); const { renderToStaticMarkup } = require('react-dom/server');
const { RoutineView } = require('./components/chat/RoutineView.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(cases.map((c) => {
  global.__streaming = c.streaming;
  return renderToStaticMarkup(React.createElement(RoutineView, { msg: c.msg }));
})));
"""


def _render(cases: list[dict]) -> list[str]:
    work = Path(tempfile.mkdtemp(prefix="fe-routine-view-"))
    try:
        (work / "render.cjs").write_text(_VIEW_DRIVER, encoding="utf-8")
        r = subprocess.run(["node", "render.cjs", str(_SRC)], cwd=str(work), capture_output=True, text=True, timeout=120,
                           input=json.dumps(cases, ensure_ascii=False),
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(_FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _plain(markup: str) -> str:
    """그린 글을 읽는 글로 — 이웃한 글 조각 사이의 `<!-- -->`(서버 렌더의 경계 표지)를 걷고 엔티티를 푼다."""
    return html.unescape(markup.replace("<!-- -->", ""))


def _actions(markup: str) -> dict[str, tuple[bool, str]]:
    """그린 글의 루틴 단추(이어서 · 멈춤 · 후보 — 단계 칩은 뺀다) → {단추 글: (꺼짐, title)}."""
    got = {}
    for attrs, text in re.findall(r"<button([^>]*)>(.*?)</button>", markup):
        if re.search(r'class="(rv-btn|rv-cand)[ "]', attrs):
            title = re.search(r'title="([^"]*)"', attrs)
            got[html.unescape(text)] = ('disabled=""' in attrs, html.unescape(title.group(1)) if title else "")
    return got


_STEPS_RUN = [{"id": "anchor", "title": "기준 키", "kind": "platform", "state": "ok", "calls": 1},
              {"id": "ft", "title": "시장불량 이력", "kind": "platform", "state": "running", "calls": 2}]
_RT_RUNNING = {"run_id": RUN, "title": "시장불량 원인 분석", "state": "running", "steps": _STEPS_RUN}
_RT_WAITING = {**_RT_RUNNING, "state": "waiting", "steps": [_STEPS_RUN[0], {**_STEPS_RUN[1], "state": "ambiguous"}],
               "gate": {"step": "ft", "candidates": CANDS}}
_STEPS_DONE = [{"id": "anchor", "title": "기준 키", "kind": "platform", "state": "ok", "calls": 1},
               {"id": "ft", "title": "시장불량 이력", "kind": "platform", "state": "ok", "calls": 2}]
_RT_DONE = {"run_id": RUN, "title": "시장불량 원인 분석", "state": "done", "steps": _STEPS_DONE}
# 게이트웨이가 ask 루틴의 보고서에 다는 글(HWAXMcpGateway _routine_report) — MCP 클라이언트(Claude)에게 하는 지시다
_RA_NEXT = "사람에게 Report Archive 초안으로 올릴지 묻고, 올리기로 하면 같은 run_id 로 upload=true 를 붙여 다시 낸다"


def _vmsg(routine: dict, live: bool = False, text: str = "", **kw) -> dict:
    return {"id": "a1", "role": "assistant", "text": text, "routine": routine, **({"streaming": True} if live else {}), **kw}


def test_다른_답을_받는_중에는_이어서_멈춤_후보를_꺼_두고_title_로_까닭을_보인다():
    """챗은 한 번에 한 스트림이다 — 받는 중에 보낸 잇기는 조용히 버려지고(ChatContext sendMessage), 고르기는 원장에서 고른 뒤 잇지 못해
    실행을 아무도 돌리지 않는 채 남긴다. 다른 답을 받는 중에는 멈춤도 꺼 둔다. 꺼진 단추는 눌러도 아무 일이 없으니 title 로 까닭과 할 일을
    말한다(ChatActionBar 와 같은 길). 받는 중이 아니면 켜져 있고 title 은 하는 일을 말한다. 이 실행을 받는 메시지의 멈춤은 아래 시험이 본다."""
    idle, busy, pick_idle, pick_busy = (_actions(m) for m in _render([
        {"streaming": False, "msg": _vmsg(_RT_RUNNING)}, {"streaming": True, "msg": _vmsg(_RT_RUNNING)},
        {"streaming": False, "msg": _vmsg(_RT_WAITING)}, {"streaming": True, "msg": _vmsg(_RT_WAITING)}]))
    labels = {c["label"] for c in CANDS}
    assert set(idle) == set(busy) == {"이어서", "멈춤"} and set(pick_idle) == set(pick_busy) == labels | {"멈춤"}
    for view in (idle, pick_idle):
        for text, (off, title) in view.items():
            assert not off and "받는 중" not in title, f"받는 중이 아닌데 '{text}' 단추가 꺼졌거나 까닭이 붙었다 — {title!r}"
    assert [pick_idle[c["label"]][1] for c in CANDS] == [c["key"] for c in CANDS], "후보 title 은 그 키다"
    for view in (busy, pick_busy):
        for text, (off, title) in view.items():
            assert off, f"다른 답을 받는 중인데 '{text}' 단추가 켜져 있다"
            assert "받는 중" in title and "■" in title, f"꺼진 '{text}' 단추가 까닭(받는 중)과 할 일(■ 로 끊기)을 말하지 않는다 — {title!r}"
    assert all(pick_busy[c["label"]][1].endswith(c["key"]) for c in CANDS), "받는 중의 후보 title 이 키를 잃었다"


def test_이_실행을_받는_중인_메시지의_멈춤은_켜_두어_한_번에_그친다():
    """■ 는 받기만 끊고 실행은 서버에서 계속 돈다(중계가 끝까지 읽고 에이전트 실행은 따로 돈다, R3 D7 · D9). 흐르는 루틴을 그치는 길은
    멈춤(cancelRun — 포털로 바로 가는 부름, 실행기가 다음 검사에서 done(cancelled) 로 스트림을 닫는다)뿐이라, 이 실행을 받고 있는
    메시지에서 켜 둬야 한 번에 그친다(■ → 멈춤 → 확인의 세 걸음이 아니다). title 은 ■ 와 이 단추가 어떻게 다른지 말한다. 흐르는
    메시지에는 이어서가 없고(이미 받는 중이다), 후보는 받는 중이라 꺼 둔다(고른 뒤 이을 챗 턴이 버려진다)."""
    run_live, wait_live = (_actions(m) for m in _render([
        {"streaming": True, "msg": _vmsg(_RT_RUNNING, live=True)},
        {"streaming": True, "msg": _vmsg(_RT_WAITING, live=True)}]))
    assert set(run_live) == {"멈춤"}, f"흐르는 메시지의 단추가 멈춤 하나가 아니다 — {sorted(run_live)}"
    for view in (run_live, wait_live):
        off, title = view["멈춤"]
        assert not off, "이 실행을 받는 중인 메시지의 멈춤이 꺼져 있다 — ■ 로 끊은 뒤에야 멈출 수 있다"
        assert "■" in title and "받기만" in title and "받는 중" not in title, f"멈춤 title 이 ■ 와 다른 점을 말하지 않는다 — {title!r}"
    for c in CANDS:
        off, title = wait_live[c["label"]]
        assert off and "받는 중" in title, f"받는 중인데 후보 '{c['label']}' 가 켜져 있다"


def test_받기를_끊은_루틴_턴은_실행이_서버에서_계속_돈다고_말하고_멈춤을_가리킨다():
    """■ 뒤 오류 상자는 다른 턴과 같은 '중단되었습니다' 다(ChatContext 의 '취소됨' → lib/chatErrors). 루틴 실행은 서버에서 계속 도니
    루틴 칸이 그 뜻(받기만 끊었다 · 그치려면 멈춤)을 말하고 멈춤을 켜 둔다. 실행이 이미 끝났거나 고를 것에서 섰으면 말하지 않고,
    ■ 가 아닌 오류(스트림 절단)에도 말하지 않는다."""
    note = "받기만 끊었습니다 — 실행은 서버에서 계속 돕니다. 그치려면 '멈춤' 을 누릅니다."
    cut, done_cut, wait_cut, broke, plain = _render([
        {"streaming": False, "msg": _vmsg(_RT_RUNNING, error="취소됨")},
        {"streaming": False, "msg": _vmsg(_RT_DONE, error="취소됨")},
        {"streaming": False, "msg": _vmsg(_RT_WAITING, error="취소됨")},
        {"streaming": False, "msg": _vmsg(_RT_RUNNING, error="스트림이 끊겼습니다 — 프록시의 침묵 한도 (network error)")},
        {"streaming": False, "msg": _vmsg(_RT_RUNNING)}])
    assert note in _plain(cut), "■ 로 끊은 루틴 턴이 실행이 서버에서 계속 돈다고 말하지 않는다"
    assert _actions(cut)["멈춤"][0] is False, "■ 뒤 멈춤이 꺼져 있다"
    for name, markup in (("끝난 실행", done_cut), ("고를 것", wait_cut), ("스트림 절단", broke), ("오류 없음", plain)):
        assert "받기만 끊었습니다" not in _plain(markup), f"{name} 에 ■ 안내가 붙었다"
    got = _node(["lib/chatErrors.ts", "state/chatStore.ts"],
                "const E = require('./lib/chatErrors.js');"
                " out({ note: E.routineStopNote('취소됨'), none: [E.routineStopNote(''), E.routineStopNote(undefined),"
                " E.routineStopNote('스트림이 끊겼습니다 — x')], title: E.friendlyError('취소됨').title });", None)
    assert got == {"note": note, "none": [None, None, None], "title": "중단되었습니다"}, "■ 의 글자 판정이 오류 상자와 갈렸다"


def test_실행_id_전에_멈춘_루틴_턴의_오류_상자는_실행이_서버에서_돌_수_있다고_말한다():
    """실행 id 를 받기 전에 ■ 로 끊은 새 루틴 턴에는 루틴 칸이 없다 — '중단되었습니다' 만 보여 실행이 멈춘 것으로 읽혔는데 실행은 서버에서
    돌고 있다(2차 #16). 그 턴의 글(ROUTINE_STOPPED_BEFORE_RUN)은 실행이 돌 수 있고 다시 시도가 그것을 찾는다고 말한다. '취소' 를 담아 ■ 판정과
    다시 시도가 그대로 돈다. 다른 턴의 ■ 는 종전 그대로다."""
    got = _node(["lib/chatErrors.ts", "state/chatStore.ts"],
                "const E = require('./lib/chatErrors.js');"
                " out({ text: E.ROUTINE_STOPPED_BEFORE_RUN || null, f: E.friendlyError(E.ROUTINE_STOPPED_BEFORE_RUN || ''),"
                " plain: E.friendlyError('취소됨'), note: E.routineStopNote(E.ROUTINE_STOPPED_BEFORE_RUN) });", None)
    assert got["text"] and "취소" in got["text"], f"실행 id 전에 멈춘 루틴 턴의 글이 없거나 ■ 판정에 걸리지 않는다 — {got['text']!r}"
    f = got["f"]
    assert f["title"] == "중단되었습니다" and f["retry"] is True
    hint = f.get("hint") or ""
    assert "서버에서 돌고 있을 수 있습니다" in hint and "다시 시도" in hint and "멈춤" in hint, f"오류 상자가 루틴의 뜻을 말하지 않는다 — {hint!r}"
    assert got["plain"] == {"title": "중단되었습니다", "retry": True}, "다른 턴의 ■ 오류 상자가 바뀌었다"
    assert got["note"], "■ 판정(routineStopNote)이 이 글을 ■ 로 읽지 않는다"
    src = _ctx()
    assert "lost ? ROUTINE_STOPPED_BEFORE_RUN : '취소됨'" in src, "챗 상태가 실행 id 전에 멈춘 루틴 턴에 그 글을 적지 않는다"


def test_보고서_보기는_끝난_실행이면_메시지_글과_상관없이_낸다():
    """보고서 프레임(routine{report})을 받은 끝난 실행은 원장에 보고서가 저장된 뒤다. 메시지 글이 보고서든 '이미 끝났다' 안내 · RA 올리기
    결과 같은 짧은 글이든 '보고서 보기' 를 낸다 — 글이 있으면 숨기던 종전 판정은 자리 글 · 안내 글 아래에서 보고서에 닿을 길을 없앴다.
    보고서는 이 칸 안에 펼친다(메시지 글을 바꾸지 않는다). 받는 중에는 내지 않고, 끝나지 않은 실행에도 내지 않는다."""
    rep = {"ra_upload": "auto", "ra_report_id": "RA-2026-1029"}
    full, notice, live, running = _render([
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": rep}, text=_REPORT_MD)},
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": rep}, text="이 실행은 이미 끝났다 — 화면에서 보고서를 연다.")},
        {"streaming": True, "msg": _vmsg({**_RT_DONE, "report": rep}, live=True, text=_REPORT_MD)},
        {"streaming": False, "msg": _vmsg({**_RT_RUNNING, "report": rep}, text="(루틴 실행 — 단계와 보고서는 위 실행 보기에서 이어서 본다)")}])
    for name, markup in (("보고서 글", full), ("안내 글", notice)):
        assert _actions(markup).get("보고서 보기") == (False, ""), f"{name} 메시지에 켜진 '보고서 보기' 가 없다 — {_actions(markup)}"
        btn = re.search(r"<button([^>]*)>보고서 보기</button>", markup)
        assert btn and 'aria-expanded="false"' in btn.group(1), "보고서 보기가 펼침 단추(aria-expanded)가 아니다"
    for name, markup in (("받는 중", live), ("도는 실행", running)):
        assert "보고서 보기" not in markup, f"{name} 메시지에 '보고서 보기' 를 냈다"


def test_끝에_묻는_루틴은_MCP_용_지시문_대신_RA_초안_올리기_단추를_낸다():
    """게이트웨이는 ask 루틴의 보고서에 ra_next(MCP 클라이언트에게 'upload=true 로 다시 내라' 는 지시)를 단다. 사람에게 그 글을 보이면
    할 일이 없다 — 화면은 그 글을 내지 않고 사람 말과 'RA 초안 올리기' 를 낸다(누르면 resumeRoutine(run_id, 제목, {uploadRa: true}) →
    에이전트가 routine_report_submit(upload=true), C4). 초안이 이미 있으면 번호만, 올리기가 실패했으면 오류와 함께 다시 올릴 단추를 낸다.
    끝나지 않은 실행 · 실패하지 않은 저절로(auto) 올리기에는 내지 않고(실패한 auto 는 아래 시험), 다른 답을 받는 중에는 꺼 둔다(챗 턴으로 간다)."""
    ask = {"ra_upload": "ask", "ra_next": _RA_NEXT}
    idle, busy, has_id, failed, auto, running = _render([
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": ask}, text=_REPORT_MD)},
        {"streaming": True, "msg": _vmsg({**_RT_DONE, "report": ask}, text=_REPORT_MD)},
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": {"ra_upload": "ask", "ra_report_id": "RA-77"}})},
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": {**ask, "ra_error": "Report Archive 토큰이 없다"}})},
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": {"ra_upload": "auto", "ra_report_id": None}})},
        {"streaming": False, "msg": _vmsg({**_RT_RUNNING, "report": ask})}])
    for name, markup in (("끝남", idle), ("받는 중", busy), ("실패", failed), ("도는 중", running)):
        assert "upload=true" not in markup and _RA_NEXT not in _plain(markup), f"{name} — MCP 용 지시문을 사람에게 보였다"
    off, title = _actions(idle)["RA 초안 올리기"]
    assert not off and "Report Archive" in title, f"끝에 묻는 루틴의 끝난 실행에 켜진 'RA 초안 올리기' 가 없다 — {title!r}"
    assert "끝에 묻습니다" in _plain(idle), "올리기 단추 곁에 사람에게 하는 말이 없다"
    off, title = _actions(busy)["RA 초안 올리기"]
    assert off and "받는 중" in title and "■" in title, f"다른 답을 받는 중인데 올리기가 켜져 있거나 까닭이 없다 — {title!r}"
    assert "RA 초안 올리기" not in _actions(has_id) and "Report Archive 초안 #RA-77" in _plain(has_id), "초안이 이미 있는데 또 올리라고 한다"
    assert _actions(failed).get("RA 초안 올리기", (True,))[0] is False and "토큰이 없다" in failed, "실패한 올리기를 다시 올릴 길이 없다"
    for name, markup in (("저절로", auto), ("도는 중", running)):
        assert "RA 초안 올리기" not in markup, f"{name} 실행에 올리기 단추를 냈다"


def test_저절로_올리기가_실패한_루틴은_RA_초안_올리기_단추를_다시_낸다():
    """저절로(auto) 올리는 루틴의 초안이 실패하면(토큰 없음 등) 화면은 '다시 시도하세요' 라 하면서 누를 단추가 없었다 — 루틴 전체를 다시 돌리는
    길뿐이었다(2차 #15). 실행기 · 게이트웨이는 같은 길(upload_ra)로 auto 도 다시 올린다. 오류가 있을 때만 낸다 — 오류가 없는 auto 는 올리는
    중이거나 올렸고, 초안이 이미 있으면 번호만이다."""
    failed, plain_auto, has_id, busy = _render([
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": {"ra_upload": "auto", "ra_report_id": None,
                                                                   "ra_error": "Report Archive 토큰이 없다"}})},
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": {"ra_upload": "auto", "ra_report_id": None}})},
        {"streaming": False, "msg": _vmsg({**_RT_DONE, "report": {"ra_upload": "auto", "ra_report_id": "RA-9", "ra_error": None}})},
        {"streaming": True, "msg": _vmsg({**_RT_DONE, "report": {"ra_upload": "auto", "ra_error": "Report Archive 토큰이 없다"}})}])
    got = _actions(failed).get("RA 초안 올리기")
    assert got is not None and got[0] is False and "Report Archive" in got[1], f"실패한 저절로 올리기를 다시 올릴 단추가 없다 — {_actions(failed)}"
    text = _plain(failed)
    assert "토큰이 없다" in text and "저절로 올리기가 실패했습니다" in text and "끝에 묻습니다" not in text, "단추 곁의 말이 auto 의 뜻이 아니다"
    assert "RA 초안 올리기" not in _actions(plain_auto), "오류가 없는 저절로 올리기(올리는 중 · 올림)에 단추를 냈다"
    assert "RA 초안 올리기" not in _actions(has_id) and "Report Archive 초안 #RA-9" in _plain(has_id)
    off, title = _actions(busy)["RA 초안 올리기"]
    assert off and "받는 중" in title, "다른 답을 받는 중인데 올리기가 켜져 있다"


# ── 원장을 읽어야 정해지는 꼴(RoutineView) — 실제 조각을 헤드리스 브라우저에 올린다(test_delib_stream_in_browser 와 같은 길) ─────────
# RoutineView · routine.ts · chatErrors · chatStore 는 실물을 옮겨 두고, 챗 상태 · 권한 · 원장 API · 글 칸은 같은 자리의 대역이다(원장 API 는
# window.__views · __reports 에서 답하고 부른 것을 window.__calls 에 적는다). 시계는 가짜(5초 · 30초 다시 읽기를 빨리 돌린다).
_BR_REAL = ["components/chat/RoutineView.tsx", "components/chat/routine.ts", "lib/chatErrors.ts", "state/chatStore.ts"]
_BR_STUBS = {
    # streamLive — window.__live 면 다른 답이 흐르는 중이다. gen — 그 함수를 준 그리기의 차례(window.__gen)라, 누른 때의 함수로 불렀는지 가린다.
    "state/ChatContext.ts": (
        "const w = window as any;\n"
        "export function useChat() {\n"
        "  const gen = w.__gen ?? 1;\n"
        "  return { streaming: w.__streaming === true, streamLive: () => (w.__live ? { startedAt: 1 } : null),\n"
        "    resumeRoutine: (...args: unknown[]) => { w.__calls.push({ fn: 'resumeRoutine', args, gen }); return Promise.resolve(); } };\n"
        "}\n"),
    "auth/useCan.ts": "export const useCan = () => (_key: string) => true;\n",
    "api/routines.api.ts": (
        "const w = window as any;\n"
        "const rec = (fn: string, args: unknown[]) => { w.__calls.push({ fn, args }); };\n"
        "export async function getRun(runId: string) { rec('getRun', [runId]); const v = w.__views[runId];\n"
        "  if (!v) throw new Error('없는 실행 ' + runId); return JSON.parse(JSON.stringify(v)); }\n"
        "export async function getRunReport(runId: string) { rec('getRunReport', [runId]); return w.__reports[runId]; }\n"
        "export async function pickCandidate(...args: unknown[]) { rec('pickCandidate', args);\n"
        "  if (w.__pickHold) await new Promise((res) => { w.__pickRelease = res; }); return {}; }\n"
        "export async function cancelRun(runId: string) { rec('cancelRun', [runId]); return {}; }\n"),
    "components/chat/renderers/TextBlock.tsx": "export function TextBlock({ text }: { text: string }) { return <div className=\"tb\">{text}</div>; }\n",
}
# 메시지 하나마다 RoutineView 와 그 글(MessageList 처럼 칸 아래)을 그린다. dock — 닫힌 ChatDock 의 꼴(chat.css .chatdock: 오른쪽 끝에 붙어
# 제 폭만큼 화면 밖으로 밀려 있다). scroll — 긴 대화에서 화면 아래로 벗어난 메시지.
_BR_HARNESS = r"""
import { createRoot } from 'react-dom/client';
import { RoutineView } from './src/components/chat/RoutineView';

const w = window as any;
w.__mount = (cfg: any) => {
  w.__streaming = Boolean(cfg.streaming);
  const list = cfg.msgs.map((m: any) => (
    <div key={m.id} data-id={m.id} style={{ padding: 8 }}>
      <RoutineView msg={m} />
      <p className="msg-text">{m.text}</p>
    </div>
  ));
  const body =
    cfg.layout === 'dock' ? (
      <aside id="dock" style={{ position: 'fixed', top: 0, right: 0, width: 420, height: '100vh', overflow: 'auto',
                                transform: 'translateX(100%)' }}>
        <div style={{ padding: 16 }}>{list}</div>
      </aside>
    ) : cfg.layout === 'scroll' ? (
      <><div id="spacer" style={{ height: 3000 }} />{list}</>
    ) : (
      <>{list}</>
    );
  w.__cfg = cfg;
  w.__root = w.__root || createRoot(document.getElementById('root')!);
  w.__root.render(body);
};
// 같은 메시지로 다시 그린다 — 칸이 새 useChat 값(window.__gen)을 받는다
w.__rerender = () => w.__mount(w.__cfg);
"""
_BR_STUB_JS = r"""
window.__calls = []; window.__views = {}; window.__reports = {}; window.__vis = 'visible';
// 숨은 탭 — 브라우저가 스스로 바꾸지 않으니 값과 알림을 시험이 준다
Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => window.__vis });
window.__setVis = (v) => { window.__vis = v; document.dispatchEvent(new Event('visibilitychange')); };
"""
_BR_DRIVE = r"""
const { createRequire } = require('module');
const path = require('path'); const fs = require('fs');
const [FE, OUT] = process.argv.slice(2);
const { chromium } = createRequire(path.join(FE, 'package.json'))('@playwright/test');
const DATA = JSON.parse(fs.readFileSync(path.join(OUT, 'data.json'), 'utf8'));

async function open(browser, cfg) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(10000);
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e)));
  page.on('dialog', (d) => d.accept());                 // 멈춤의 확인 창
  await page.route('http://harness.invalid/**', (r) =>
    r.fulfill({ contentType: 'text/html', body: '<!doctype html><html><body style="margin:0"><div id="root"></div></body></html>' }));
  await page.clock.install({ time: new Date('2026-10-30T00:00:00Z') });
  await page.goto('http://harness.invalid/');
  await page.addScriptTag({ path: path.join(OUT, 'stub.js') });
  await page.evaluate((d) => { window.__views = d.views; window.__reports = d.reports; }, DATA);
  await page.addScriptTag({ path: path.join(OUT, 'bundle.js') });
  await page.evaluate((c) => window.__mount(c), cfg);
  return page;
}
const reads = (page, id) => page.evaluate((i) => window.__calls.filter((c) => c.fn === 'getRun' && c.args[0] === i).length, id);
const callsOf = (page, fn) => page.evaluate((f) => window.__calls.filter((c) => c.fn === f).map((c) => c.args), fn);
// 그 실행의 읽기가 n 번을 넘을 때까지 잠깐 기다린다 — 넘지 않아도 던지지 않고 센 값을 돌려준다(판정은 시험이 한다)
async function readsAfter(page, id, n = 0) {
  for (let i = 0; i < 40; i++) { const k = await reads(page, id); if (k > n) return k; await page.waitForTimeout(50); }
  return reads(page, id);
}
// 가짜 시계를 5초씩 돌리며 화면이 따라올 틈을 준다
async function forward(page, ms) { for (let t = 0; t < ms; t += 5000) { await page.clock.fastForward(5000); await page.waitForTimeout(25); } }
// IntersectionObserver 의 알림 · React 의 다시 그리기는 실제 시간으로 온다 — 잠깐 기다린다
const frames = (page) => page.waitForTimeout(400);
const btn = (page, id, text) => page.locator(`[data-id="${id}"] button`, { hasText: text });
const rvText = (page, id) => page.locator(`[data-id="${id}"] .rv`).innerText();

const SCENARIOS = {
  // 닫힌 독 — 읽지 않는다. 열면 곧 읽고 5초마다, 숨은 탭에서는 그치고 돌아오면 곧 읽는다. 다시 닫으면 그친다.
  async offscreen(browser) {
    const page = await open(browser, { layout: 'dock', msgs: DATA.msgs.offscreen });
    await frames(page);
    await forward(page, 60000);
    const closed = await reads(page, 'R-run');
    await page.evaluate(() => { document.getElementById('dock').style.transform = 'none'; });
    const opened = await readsAfter(page, 'R-run', closed);
    await forward(page, 10000);
    const polled = await reads(page, 'R-run');
    await page.evaluate(() => window.__setVis('hidden'));
    await frames(page);
    const hid = await reads(page, 'R-run');
    await forward(page, 60000);
    const hidden = await reads(page, 'R-run');
    await page.evaluate(() => window.__setVis('visible'));
    const back = await readsAfter(page, 'R-run', hidden);
    await page.evaluate(() => { document.getElementById('dock').style.transform = 'translateX(100%)'; });
    await frames(page);
    const shut = await reads(page, 'R-run');
    await forward(page, 60000);
    return { closed, opened, polled, hid, hidden, back, shut, reclosed: await reads(page, 'R-run'), errors: page.__errors };
  },
  // 긴 대화에서 화면 아래로 벗어난 메시지 — 보일 때까지 읽지 않는다
  async scrolled(browser) {
    const page = await open(browser, { layout: 'scroll', msgs: DATA.msgs.scrolled });
    await frames(page);
    await forward(page, 30000);
    const below = await reads(page, 'R-run2');
    await page.evaluate(() => document.querySelector('[data-id="m-scr"]').scrollIntoView());
    return { below, seen: await readsAfter(page, 'R-run2', below), errors: page.__errors };
  },
  // 중계의 자리 글(서버 사본 — 포인터만) · 실행기의 '이미 끝났다' 안내(끝난 단계 · 보고서 프레임 없음) — 둘 다 원장의 보고서를 펼쳐 본다
  async report(browser) {
    const page = await open(browser, { layout: 'plain', msgs: DATA.msgs.report });
    await readsAfter(page, 'R-ph');
    await frames(page);
    const ph = btn(page, 'ph', '보고서');
    const panel = page.locator('[data-id="ph"] .rv-report');
    const out = { ph_button: await ph.count(), note_button: await btn(page, 'note', '보고서 보기').count() };
    if (out.ph_button) {
      await ph.click();
      await panel.waitFor({ timeout: 5000 });
      out.opened = { panel: await panel.innerText(), label: await ph.innerText(), expanded: await ph.getAttribute('aria-expanded'),
                     text: await page.locator('[data-id="ph"] .msg-text').innerText() };
      await ph.click();
      await frames(page);
      out.folded = { panels: await panel.count(), label: await ph.innerText(), expanded: await ph.getAttribute('aria-expanded') };
      await ph.click();
      await panel.waitFor({ timeout: 5000 });
      out.reopened = await panel.count();
    }
    out.report_reads = (await callsOf(page, 'getRunReport')).length;
    await forward(page, 60000);
    out.ph_reads = await reads(page, 'R-ph');
    out.note_reads = await reads(page, 'R-note');
    out.errors = page.__errors;
    return out;
  },
  // 끝에 묻는 루틴 — 지시문 대신 올리기 단추. 원장에 초안이 생겼으면 단추를 거둔다. 누르면 upload_ra 로 잇는다(C4).
  async ra(browser) {
    const page = await open(browser, { layout: 'plain', msgs: DATA.msgs.ra });
    await readsAfter(page, 'R-srv');
    await frames(page);
    const out = {
      text: { ask: await rvText(page, 'ask'), later: await rvText(page, 'later'), server: await rvText(page, 'server') },
      buttons: { ask: await btn(page, 'ask', 'RA 초안 올리기').count(), later: await btn(page, 'later', 'RA 초안 올리기').count(),
                 server: await btn(page, 'server', 'RA 초안 올리기').count() },
      reads: { ask: await reads(page, 'R-ask'), later: await reads(page, 'R-later') },
    };
    if (out.buttons.ask) {
      await btn(page, 'ask', 'RA 초안 올리기').click();
      await frames(page);
      out.resumed = await callsOf(page, 'resumeRoutine');
      out.after = { text: await rvText(page, 'ask'), buttons: await btn(page, 'ask', 'RA 초안 올리기').count() };
    }
    out.errors = page.__errors;
    return out;
  },
  // 이 실행을 받는 중인 메시지 — 멈춤 한 번(확인)으로 실행을 멈춘다. 받는 동안은 원장을 읽지 않는다(스트림이 정본).
  async stop(browser) {
    const page = await open(browser, { layout: 'plain', streaming: true, msgs: DATA.msgs.stop });
    await frames(page);
    const stop = btn(page, 'live', '멈춤');
    const out = { disabled: await stop.isDisabled() };
    if (!out.disabled) {
      await stop.click();
      await page.waitForFunction(() => window.__calls.some((c) => c.fn === 'cancelRun'), null, { timeout: 5000 });
      await frames(page);
      out.cancelled = await callsOf(page, 'cancelRun');
      out.badge = await page.locator('[data-id="live"] .rv-badge').innerText();
      out.stop_left = await stop.count();
    }
    out.reads = (await callsOf(page, 'getRun')).length;
    out.errors = page.__errors;
    return out;
  },
  // 저절로 올리기(auto)가 실패한 실행 — 원장을 한 번 읽고 'RA 초안 올리기' 로 다시 올린다. 원장에 그 뒤 초안이 생겼으면 번호를 보이고 단추를 거둔다
  async ra_auto(browser) {
    const page = await open(browser, { layout: 'plain', msgs: DATA.msgs.ra_auto });
    await readsAfter(page, 'R-autofail');
    await readsAfter(page, 'R-autolater');
    await frames(page);
    const out = {
      text: { fail: await rvText(page, 'autofail'), later: await rvText(page, 'autolater') },
      buttons: { fail: await btn(page, 'autofail', 'RA 초안 올리기').count(), later: await btn(page, 'autolater', 'RA 초안 올리기').count() },
      reads: { fail: await reads(page, 'R-autofail'), later: await reads(page, 'R-autolater') },
    };
    if (out.buttons.fail) {
      await btn(page, 'autofail', 'RA 초안 올리기').click();
      await frames(page);
      out.resumed = await callsOf(page, 'resumeRoutine');
    }
    out.errors = page.__errors;
    return out;
  },
  // 키보드로 멈춤 · RA 초안 올리기 · 후보 고르기 — 누른 단추가 사라지거나 꺼져도 포커스는 그 루틴 칸에 남고, 결과가 낭독기 줄로 들린다
  async a11y(browser) {
    const page = await open(browser, { layout: 'plain', msgs: DATA.msgs.a11y });
    for (const id of ['R-a-run', 'R-a-ask', 'R-a-gate']) await readsAfter(page, id);
    await frames(page);
    const where = () => page.evaluate(() => {
      const a = document.activeElement;
      const host = a && a.closest('[data-id]');
      return { tag: a ? a.tagName : '', cls: (a && a.className) || '', id: host ? host.dataset.id : '' };
    });
    const heard = (id) => page.evaluate((i) => Array.from(document.querySelectorAll(`[data-id="${i}"] .rv p[role="status"]`))
      .map((e) => e.textContent).join(' | '), id);
    const out = {};
    for (const [id, text, fn] of [['a-run', '멈춤', 'cancelRun'], ['a-ask', 'RA 초안 올리기', 'resumeRoutine'],
                                  ['a-gate', 'SM-S938(국내)', 'pickCandidate']]) {
      const b = btn(page, id, text);
      if (!(await b.count())) { out[id] = { missing: true }; continue; }
      await b.first().focus();
      await page.keyboard.press('Enter');
      await page.waitForFunction((f) => window.__calls.some((c) => c.fn === f), fn, { timeout: 5000 });
      await frames(page);
      out[id] = { focus: await where(), heard: await heard(id) };
    }
    out.errors = page.__errors;
    return out;
  },
  // 고르기를 기다리는 사이 — 다시 그린 칸은 지금 함수로 잇는다. 그 사이 다른 답이 흐르기 시작했으면 잇지 않고 '이어서' 를 누르라고 말한다
  async pick(browser) {
    const page = await open(browser, { layout: 'plain', msgs: DATA.msgs.pick });
    await readsAfter(page, 'R-pick');
    await frames(page);
    const cand = btn(page, 'pk', 'SM-S938(국내)');
    const release = () => page.evaluate(() => { const r = window.__pickRelease; window.__pickRelease = undefined; r(); });
    await page.evaluate(() => { window.__pickHold = true; window.__gen = 1; });
    await cand.click();
    await page.waitForFunction(() => typeof window.__pickRelease === 'function');
    await page.evaluate(() => { window.__gen = 2; window.__rerender(); });
    await frames(page);
    await release();
    await frames(page);
    const first = await page.evaluate(() => window.__calls.filter((c) => c.fn === 'resumeRoutine').map((c) => ({ args: c.args, gen: c.gen })));
    await cand.click();
    await page.waitForFunction(() => typeof window.__pickRelease === 'function');
    await page.evaluate(() => { window.__live = true; });
    await release();
    await frames(page);
    const second = {
      picks: (await callsOf(page, 'pickCandidate')).length,
      resumes: (await callsOf(page, 'resumeRoutine')).length,
      note: await page.locator('[data-id="pk"] .rv-reason').allInnerTexts(),
      heard: await page.evaluate(() => Array.from(document.querySelectorAll('[data-id="pk"] .rv p[role="status"]'))
        .map((e) => e.textContent).join(' | ')),
    };
    return { first, second, errors: page.__errors };
  },
};

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { process.stdout.write(JSON.stringify({ skip: String(e).slice(0, 300) })); return; }
  const out = {};
  try {
    for (const [name, run] of Object.entries(SCENARIOS)) {
      try { out[name] = await run(browser); } catch (e) { out[name] = { failed: String((e && e.stack) || e).slice(0, 1500) }; }
    }
  } finally { await browser.close(); }
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""
_PLACEHOLDER = "(루틴 실행 — 단계와 보고서는 위 실행 보기에서 이어서 본다)"


def _view_as(run_id: str, state: str, *, upload: str = "auto", ra_report_id: str | None = None) -> dict:
    """포털의 실제 run_view 가 만든 실행 보기 — 끝난 실행은 보고서가 있다(report_ready)."""
    closed = [_stage(s, st, n, envelope={"summary": f"{s} 요약"}) for s, st, n in
              (("anchor", "ok", 1), ("ft", "ok", 2), ("plm", "not_connected", 0), ("delib", "ok", 3))]
    done = state == "done"
    v = _run_view(state, closed if done else closed[:1], report_md="# 시장불량 원인 분석\n원장의 보고서 본문" if done else None,
                  ra_report_id=ra_report_id)
    v["run"]["id"] = run_id
    v["report"]["upload"] = upload
    return v


def _view_wait(run_id: str) -> dict:
    """고를 것에서 선 실행의 보기(포털의 실제 run_view) — 시장불량 이력 단계가 후보 둘로 갈렸다."""
    ft_env = {"status": "ambiguous", "summary": "두 계열에 기록이 있다 [ft.c2]", "keys": {}, "candidates": CANDS}
    v = _run_view("waiting", [_stage("anchor", "ok", 1, envelope={"summary": "SM-S938 이다 [anchor.c1]"}),
                              _stage("ft", "ambiguous", 3, reason="모델 후보가 둘이다", envelope=ft_env)])
    v["run"]["id"] = run_id
    return v


def _br_data() -> dict:
    def ptr(rid: str, state: str) -> dict:          # 서버 사본이 되살린 꼴 — 단계는 비었다
        return {"run_id": rid, "routine_id": "rt-swelling", "title": "시장불량 원인 분석", "state": state, "steps": []}

    def am(mid: str, routine: dict, text: str = "", **kw) -> dict:
        return {"id": mid, "role": "assistant", "text": text, "routine": routine, **kw}

    ask = {"ra_upload": "ask", "ra_next": _RA_NEXT}
    auto_failed = {"ra_upload": "auto", "ra_report_id": None, "ra_error": "Report Archive 토큰이 없다"}
    views = {"R-run": _view_as("R-run", "running"), "R-run2": _view_as("R-run2", "running"),
             "R-ph": _view_as("R-ph", "done"), "R-note": _view_as("R-note", "done"),
             "R-ask": _view_as("R-ask", "done", upload="ask"), "R-later": _view_as("R-later", "done", upload="ask", ra_report_id="RA-77"),
             "R-srv": _view_as("R-srv", "done", upload="ask"), "R-live": _view_as("R-live", "running"),
             # 저절로 올리기가 실패해 원장에 오류만 있다 · 그 뒤 초안이 생겼다
             "R-autofail": _view_as("R-autofail", "done"), "R-autolater": _view_as("R-autolater", "done", ra_report_id="RA-88"),
             "R-a-run": _view_as("R-a-run", "running"), "R-a-ask": _view_as("R-a-ask", "done", upload="ask"),
             "R-a-gate": _view_wait("R-a-gate"), "R-pick": _view_wait("R-pick")}
    views["R-autofail"]["run"]["ra_error"] = auto_failed["ra_error"]
    return {
        "views": views,
        "reports": {"R-ph": {"run_id": "R-ph", "state": "done", "report_ready": True,
                             "report_md": "# 시장불량 원인 분석\n원장의 보고서 본문", "ra_upload": "auto"}},
        "msgs": {
            "offscreen": [am("m-off", ptr("R-run", "running"))],
            "scrolled": [am("m-scr", ptr("R-run2", "running"))],
            "report": [am("ph", ptr("R-ph", "running"), _PLACEHOLDER),
                       am("note", {**_RT_DONE, "run_id": "R-note"}, "이 실행은 이미 끝났다 — 화면에서 보고서를 연다.")],
            "ra": [am("ask", {**_RT_DONE, "run_id": "R-ask", "report": ask}, _REPORT_MD),
                   am("later", {**_RT_DONE, "run_id": "R-later", "report": ask}, _REPORT_MD),
                   am("server", ptr("R-srv", "done"), _REPORT_MD)],
            "stop": [am("live", {**_RT_RUNNING, "run_id": "R-live"}, streaming=True)],
            "ra_auto": [am("autofail", {**_RT_DONE, "run_id": "R-autofail", "report": auto_failed}, _REPORT_MD),
                        am("autolater", {**_RT_DONE, "run_id": "R-autolater", "report": auto_failed}, _REPORT_MD)],
            "a11y": [am("a-run", {**_RT_RUNNING, "run_id": "R-a-run"}),
                     am("a-ask", {**_RT_DONE, "run_id": "R-a-ask", "report": ask}, _REPORT_MD),
                     am("a-gate", {**_RT_WAITING, "run_id": "R-a-gate"})],
            "pick": [am("pk", {**_RT_WAITING, "run_id": "R-pick"})],
        },
    }


def _browser_run() -> dict:
    """화면을 묶어(esbuild — vite 의 의존성) 헤드리스 브라우저에서 시나리오를 돌린다. 도구가 없으면 건너뛴다(운영 박스)."""
    from tests.test_delib_stream_in_browser import _BUILD

    if not (_FE / "node_modules/@playwright/test").exists() or not (_FE / "node_modules/vite").exists():
        pytest.skip("frontend node_modules(@playwright/test · vite) 가 없다 — 화면을 올려 볼 수 없다")
    work = Path(tempfile.mkdtemp(prefix="fe-routine-browser-"))
    try:
        for rel in _BR_REAL:
            (work / "src" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_SRC / rel, work / "src" / rel)
        for rel, body in _BR_STUBS.items():
            (work / "src" / rel).parent.mkdir(parents=True, exist_ok=True)
            (work / "src" / rel).write_text(body, encoding="utf-8")
        for name, text in (("harness.tsx", _BR_HARNESS), ("build.cjs", _BUILD), ("stub.js", _BR_STUB_JS), ("drive.cjs", _BR_DRIVE),
                           ("data.json", json.dumps(_br_data(), ensure_ascii=False))):
            (work / name).write_text(text, encoding="utf-8")
        r = subprocess.run(["node", "build.cjs", str(_FE), str(work)], cwd=str(work), capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, "화면을 묶지 못했다:\n" + r.stdout + r.stderr
        r = subprocess.run(["node", "drive.cjs", str(_FE), str(work)], cwd=str(work), capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        got = json.loads(r.stdout)
        if "skip" in got:
            pytest.skip("헤드리스 브라우저를 띄우지 못했다(playwright 브라우저 미설치) — " + got["skip"])
        return got
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _br_scenarios(got: dict):
    def scenario(name: str) -> dict:
        assert "failed" not in got[name], f"시나리오 {name} 이 끝까지 돌지 못했다:\n{got[name].get('failed')}"
        assert not got[name].get("errors"), f"화면이 예외를 던졌다: {got[name]['errors']}"
        return got[name]
    return scenario


@pytest.fixture(scope="module")
def rv_browser():
    return _br_scenarios(_browser_run())


def test_화면_밖의_루틴_칸은_원장을_읽지_않고_보이면_곧_읽는다(rv_browser):
    """R3 §6 — 도는 실행은 '화면에 보일 때만' 다시 읽는다. 닫힌 ChatDock 은 챗이 아닌 모든 페이지에 붙어 화면 밖으로 밀려 있을 뿐이라,
    탭이 보이는지만 보면 그 안의 루틴 칸이 5초 · 30초마다 원장을 끝없이 읽는다(재기동 뒤 running 으로 남은 실행은 끝나지 않는다).
    IntersectionObserver 로 화면에 있는지 보고, 숨은 탭에서도 그친다. 다시 보이면 곧 읽고 다시 읽기를 잇는다."""
    s = rv_browser("offscreen")
    assert s["closed"] == 0, f"닫힌 독 안의 루틴 칸이 원장을 {s['closed']}번 읽었다"
    assert s["opened"] >= 1 and s["polled"] > s["opened"], f"독을 연 뒤 곧 읽고 5초마다 다시 읽어야 한다 — {s}"
    assert s["hidden"] == s["hid"], f"숨은 탭에서 원장을 읽었다 — {s['hidden'] - s['hid']}번"
    assert s["back"] > s["hidden"], "탭이 다시 보였는데 읽지 않는다"
    assert s["reclosed"] == s["shut"], f"독을 다시 닫았는데 읽기를 잇는다 — {s['reclosed'] - s['shut']}번"
    s = rv_browser("scrolled")
    assert s["below"] == 0 and s["seen"] >= 1, f"화면 아래로 벗어난 메시지는 보일 때까지 읽지 않는다 — {s}"


def test_자리_글_메시지도_끝난_실행의_보고서를_펼쳐_본다(rv_browser):
    """중계가 보고서 글 없이 끝난 루틴 턴에 남기는 자리 글('단계와 보고서는 위 실행 보기에서 이어서 본다')은 서버 사본에서 글이 있는
    메시지다. 실행이 끝까지 돌아 보고서가 원장에 있으면 그 메시지에서 '보고서 보기' 로 닿아야 한다(종전엔 글이 있으면 숨겼다). 펼친
    보고서는 이 칸 안에 보이고 메시지 글은 그대로다. 다시 누르면 접고, 또 펼쳐도 다시 읽지 않는다. 끝난 실행은 다시 읽지 않는다."""
    s = rv_browser("report")
    assert s["ph_button"] == 1, "자리 글 메시지에 '보고서 보기' 가 없다 — 보고서에 닿을 길이 없다"
    assert "원장의 보고서 본문" in s["opened"]["panel"], f"펼친 칸에 원장의 보고서가 없다 — {s['opened']}"
    assert (s["opened"]["label"], s["opened"]["expanded"]) == ("보고서 접기", "true"), f"펼친 뒤 접는 단추가 아니다 — {s['opened']}"
    assert s["opened"]["text"] == _PLACEHOLDER, "보고서를 펼치며 메시지 글을 바꿨다"
    assert s["folded"] == {"panels": 0, "label": "보고서 보기", "expanded": "false"}, f"다시 눌러도 접히지 않는다 — {s['folded']}"
    assert s["reopened"] == 1 and s["report_reads"] == 1, f"다시 펼칠 때 보고서를 또 읽었다 — {s['report_reads']}번"
    assert s["ph_reads"] == 1, f"끝난 실행을 다시 읽는다 — {s['ph_reads']}번"


def test_이미_끝났다_안내_메시지는_원장을_한_번_읽어_보고서_보기를_낸다(rv_browser):
    """끝난 실행을 이으면(■ 뒤 다시 시도 · 늦은 이어서) 실행기는 끝난 단계의 계획과 '이 실행은 이미 끝났다 — 화면에서 보고서를 연다.' 만
    낸다. 단계가 다 있고 실행이 끝났다고 원장을 읽지 않으면 보고서가 있는지 몰라 그 말이 가리키는 단추를 낼 수 없다 — 보고서 프레임이
    없는 끝난 실행은 한 번 읽는다(다시 읽지는 않는다)."""
    s = rv_browser("report")
    assert s["note_button"] == 1, "'이미 끝났다' 안내 메시지에 '보고서 보기' 가 없다"
    assert s["note_reads"] == 1, f"보고서 프레임이 없는 끝난 실행은 원장을 한 번만 읽는다 — {s['note_reads']}번"


def test_RA_초안_올리기는_upload_ra_로_이어서를_보내고_원장에_초안이_생기면_거둔다(rv_browser):
    """끝에 묻는 루틴(ask)의 끝난 실행 — 화면은 게이트웨이의 MCP 용 지시문(ra_next) 대신 'RA 초안 올리기' 를 내고, 누르면
    resumeRoutine(run_id, 제목, {uploadRa: true}) 로 잇는다(C4 — 에이전트가 routine_report_submit(upload=true)). 결과는 새 답에 오므로 이
    메시지는 보냈다고만 말하고 단추를 거둔다. 스트림의 보고서 칸은 초안이 없다고 말해도 원장에 이미 있으면(뒤에 올렸다) 번호를 보이고
    단추를 내지 않는다 — 끝에 묻는 끝난 실행은 그래서 원장을 한 번 읽는다. 서버 사본(포인터만)도 원장의 꼴로 같은 단추를 낸다."""
    s = rv_browser("ra")
    for name, text in s["text"].items():
        assert "upload=true" not in text and "사람에게 Report Archive" not in text, f"{name} — MCP 용 지시문을 사람에게 보였다"
    assert s["buttons"] == {"ask": 1, "later": 0, "server": 1}, f"올리기 단추가 틀린 자리에 있다 — {s['buttons']}"
    assert "Report Archive 초안 #RA-77" in s["text"]["later"], "원장에 생긴 RA 초안 번호를 보이지 않는다"
    assert s["reads"] == {"ask": 1, "later": 1}, f"끝에 묻는 끝난 실행은 원장을 한 번 읽는다 — {s['reads']}"
    assert s["resumed"] == [["R-ask", "시장불량 원인 분석", {"uploadRa": True}]], f"올리기가 upload_ra 로 잇지 않는다 — {s['resumed']}"
    assert s["after"]["buttons"] == 0 and "올리기를 보냈습니다" in s["after"]["text"], f"누른 뒤에도 단추가 남았다 — {s['after']}"


def test_받는_중인_루틴의_멈춤은_한_번에_실행을_멈춘다(rv_browser):
    """이 실행을 받고 있는 메시지에서 멈춤을 누르면(확인 한 번) 포털에 멈춤을 바로 보내고 칸이 곧 '멈춤' 으로 바뀐다 — ■ 로 받기를
    끊은 뒤에야 멈출 수 있던 세 걸음이 아니다. 받는 동안은 스트림이 정본이라 원장을 읽지 않는다."""
    s = rv_browser("stop")
    assert s["disabled"] is False, "이 실행을 받는 중인 메시지의 멈춤이 꺼져 있다"
    assert s["cancelled"] == [["R-live"]] and s["badge"] == "멈춤" and s["stop_left"] == 0, f"멈춤이 실행을 멈추지 않았다 — {s}"
    assert s["reads"] == 0, f"받는 중인 메시지가 원장을 읽었다 — {s['reads']}번"


def test_저절로_올리기가_실패한_메시지는_원장을_한_번_읽고_RA_초안_올리기로_다시_올린다(rv_browser):
    """되살린 메시지 · 끝난 스트림의 auto 실패 — 원장을 한 번 읽어 그 뒤 생긴 초안이 있으면 번호를 보이고 단추를 거둔다. 없으면 단추를 누르면
    resumeRoutine(run_id, 제목, {uploadRa: true}) 로 다시 올린다(2차 #15 — ask 와 같은 길)."""
    s = rv_browser("ra_auto")
    assert s["reads"] == {"fail": 1, "later": 1}, f"실패한 저절로 올리기의 끝난 실행은 원장을 한 번 읽는다 — {s['reads']}"
    assert s["buttons"] == {"fail": 1, "later": 0}, f"올리기 단추가 틀린 자리에 있다 — {s['buttons']}"
    assert "토큰이 없다" in s["text"]["fail"] and "저절로 올리기가 실패했습니다" in s["text"]["fail"]
    assert "Report Archive 초안 #RA-88" in s["text"]["later"], "원장에 그 뒤 생긴 초안 번호를 보이지 않는다"
    assert s.get("resumed") == [["R-autofail", "시장불량 원인 분석", {"uploadRa": True}]], f"다시 올리기가 upload_ra 로 잇지 않는다 — {s.get('resumed')}"


def test_키보드로_멈춤_RA_초안_올리기_후보를_누르면_포커스가_칸에_남고_결과가_들린다(rv_browser):
    """누른 단추가 사라지거나(멈춤 · RA 초안 올리기) 꺼지면(고르는 동안) 포커스가 문서(body)로 떨어지고 아무것도 들리지 않았다(2차 #17). 그 루틴
    칸이 포커스를 받고(tabIndex -1), 결과는 늘 그려 둔 낭독기 줄(role=status)로 들린다."""
    s = rv_browser("a11y")
    for mid, said in (("a-run", "실행을 멈췄습니다"), ("a-ask", "올리기를 보냈습니다"), ("a-gate", "골랐습니다")):
        got = s[mid]
        assert not got.get("missing"), f"{mid} — 시험의 전제(누를 단추)가 없다"
        assert got["focus"]["tag"] != "BODY" and got["focus"]["id"] == mid, f"{mid} — 포커스가 칸 밖으로 떨어졌다 — {got['focus']}"
        assert said in got["heard"], f"{mid} — 결과가 낭독기 줄로 들리지 않는다 — {got['heard']!r}"
    for mid in ("a-run", "a-ask"):
        f = s[mid]["focus"]
        assert f["tag"] == "SECTION" and "rv" in f["cls"].split(), f"{mid} — 사라진 단추 대신 루틴 칸이 포커스를 받아야 한다 — {f}"


def test_고르기를_기다린_뒤에는_지금_함수로_잇고_그새_다른_답이_흐르면_잇지_않는다(rv_browser):
    """고르기는 원장에 고른 뒤 잇는다 — 누른 때의 함수로 이으면 그새 시작한 다른 답을 몰라 둘째 스트림을 열었다(2차 #12). 지금 함수로 잇고, 다른
    답이 흐르는 중이면 잇지 않고 받기가 끝난 뒤 '이어서' 를 누르라고 말한다(다시 읽기가 지우지 않는 따로 쥔 말 · 낭독기 줄)."""
    s = rv_browser("pick")
    assert s["first"] == [{"args": ["R-pick", "시장불량 원인 분석"], "gen": 2}], \
        f"고른 뒤 누른 때의 함수(gen 1)로 이었거나 잇지 않았다 — {s['first']}"
    second = s["second"]
    assert second["picks"] == 2, f"시험의 전제 — 두 번 골랐다 — {second}"
    assert second["resumes"] == 1, f"다른 답이 흐르는 중인데 이었다 — 둘째 스트림이 열린다 — {second}"
    assert any("바로 잇지 못했습니다" in n and "이어서" in n for n in second["note"]), f"잇지 못한 까닭을 보이지 않는다 — {second['note']}"
    assert "바로 잇지 못했습니다" in second["heard"], "잇지 못한 까닭이 낭독기 줄로 들리지 않는다"
