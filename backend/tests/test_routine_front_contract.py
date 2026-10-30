# 챗 분석 루틴(R3)의 화면 순수 함수를 설계서만 보고 node 로 돌려 본다 — SSE 프레임 접기 · 실행 보기 되살리기 · 상태 판정 · 라벨
"""docs/analysis-routines/R3-design.md §3.2(SSE `routine` 이벤트) · §6(화면)이 정한 components/chat/routine.ts 의 계약을 본다.

검은 상자로 썼다. routine.ts 를 읽지 않고 설계서와 두 화면 에이전트가 함께 쓰는 인터페이스(형 · 함수 이름)만 보고 짰다 — 짓는
쪽의 글을 보고 시험을 쓰면 둘이 같은 오해를 나눠 갖는다.

  · mergeRoutine(prev, e) — plan 은 단계를 세우되 알던 요약은 남기고, step 은 그 단계를 '도는 중' 과 진행 한 줄(detail)로, step_done 은
    포털이 고친 상태 · 요약 · 까닭 · 표지 · 호출 수로, gate 는 실행을 '고를 것'(waiting)과 후보로, report 는 보고서 칸으로, done 은 실행
    상태(와 까닭)로 접는다. 모르는 종류는 앞선 상태 그대로이고, 칸이 빠진 프레임에도 터지지 않는다.
  · routineFromRunView(view) — 흐르지 않는 메시지(복원 · 다시 열기)는 GET /routines-api/runs/{id} 의 실행 보기로 채운다. 고를 것이
    남은 실행은 그 단계의 후보로 gate 를 다시 세워야 후보 단추가 돌아온다.
  · isRoutineLive(queued · running) · isRoutineTerminal(done · failed · cancelled). waiting(고르기) · interrupted(이어서)는 어느 쪽도 아니다.
  · 단계 상태 라벨은 포털 STATE_LABEL 과 같은 글이고, 준비도 라벨 · 사슬 글은 R1 RoutinesView 에서 옮겨 와 함께 쓴다.

프론트에는 단위 시험 러너가 없다. test_front_window_payload 와 같은 길로 TS 를 CommonJS 로 옮겨 적어 node 로 부른다(.ts 만, JSX 없음).
"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.procedures.routines import RUN_STATES, STAGE_STATES, STATE_LABEL

_FE = Path(__file__).resolve().parents[2] / "frontend"
_SRC = _FE / "src"
# routine.ts 와 그 형이 사는 두 파일. 형만 가져오면 옮겨 적을 때 import 가 지워지지만, 값을 가져와도 돌게 함께 옮겨 둔다.
_FILES = ["components/chat/routine.ts", "types/chat.ts", "api/routines.api.ts"]

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 함수를 돌려 볼 수 없다",
)


def _node(script: str, data) -> object:
    """_FILES 를 CommonJS 로 옮겨 적고 script 를 돌린다. script 는 `R`(routine 모듈) · `input` 을 읽고 `out(값)` 으로 돌려준다.
    `plain(v)` 는 그 순간의 값을 JSON 으로 떠 두고(undefined 칸은 빠진다), `fold(frames, init?)` 는 프레임을 차례로 접는다."""
    out_dir = Path(tempfile.mkdtemp(prefix="fe-routine-"))
    try:
        (out_dir / "api").mkdir()
        # 네트워크 층과 빌드 때 env 는 대역이다. config.ts 의 import.meta 는 CommonJS 로 옮겨 적히지 않는다.
        (out_dir / "api" / "client.js").write_text(
            "exports.apiFetch = async () => { throw new Error('시험에서 부르지 않는다'); };\n"
            "exports.errorDetail = (detail, fallback) => fallback;\n", encoding="utf-8")
        (out_dir / "config.js").write_text("exports.config = { apiBase: '' };\n", encoding="utf-8")
        (out_dir / "in.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        (out_dir / "run.cjs").write_text(
            "const ts = require('typescript'); const fs = require('fs'); const path = require('path');\n"
            f"const src = {json.dumps(str(_SRC))};\n"
            f"for (const rel of {json.dumps(_FILES)}) {{\n"
            "  const js = ts.transpileModule(fs.readFileSync(src + '/' + rel, 'utf8'),\n"
            "    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });\n"
            "  const to = path.join(__dirname, rel.replace(/\\.tsx?$/, '.js'));\n"
            "  fs.mkdirSync(path.dirname(to), { recursive: true }); fs.writeFileSync(to, js.outputText);\n"
            "}\n"
            "const R = require('./components/chat/routine.js');\n"
            "const input = JSON.parse(fs.readFileSync(path.join(__dirname, 'in.json'), 'utf8'));\n"
            "const plain = v => (v === undefined ? null : JSON.parse(JSON.stringify(v)));\n"
            "const out = v => process.stdout.write(JSON.stringify(plain(v)));\n"
            "const fold = (frames, init) => frames.reduce((s, e) => R.mergeRoutine(s, e), init);\n"
            "const fail = err => String((err && err.stack) || err);\n"
            + script, encoding="utf-8")
        r = subprocess.run(["node", "run.cjs"], cwd=str(out_dir), capture_output=True, text=True, timeout=120,
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(_FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def _shape_errors(s, *, strict: bool = True) -> list[str]:
    """공유 인터페이스 RoutineState 의 꼴을 어긴 곳. strict 는 선언한 형 전부를 보고, 아니면 화면이 .map 으로 도는 칸(steps · 단계 id ·
    gate.candidates · flags)과 실행 id 만 본다 — 칸이 빠진 프레임 뒤 그 밖의 칸은 설계가 정하지 않았다."""
    if not isinstance(s, dict):
        return [f"상태가 객체가 아니다 — {s!r}"]
    errs = [f"{k} 가 글이 아니다 — {s.get(k)!r}" for k in (("run_id", "title", "state") if strict else ("run_id",))
            if not isinstance(s.get(k), str)]
    if strict:
        errs += [f"{k} 의 형이 틀렸다 — {s[k]!r}" for k, t in (("routine_id", str), ("reason", str), ("resumed", bool))
                 if s.get(k) is not None and not isinstance(s[k], t)]
    steps = s.get("steps")
    if not isinstance(steps, list):
        return [*errs, f"steps 가 배열이 아니다 — {steps!r}"]
    for st in steps:
        if not isinstance(st, dict) or not isinstance(st.get("id"), str):
            errs.append(f"단계가 객체가 아니거나 id 가 글이 아니다 — {st!r}")
            continue
        for k in ("flags", "backends"):
            v = st.get(k)
            if v is not None and not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                errs.append(f"단계 {st['id']} 의 {k} 가 글 배열이 아니다 — {v!r}")
        if not strict:
            continue
        errs += [f"단계 {st['id']} 의 {k} 가 글이 아니다 — {st.get(k)!r}" for k in ("title", "kind", "state")
                 if not isinstance(st.get(k), str)]
        errs += [f"단계 {st['id']} 의 {k} 형이 틀렸다 — {st[k]!r}" for k in ("summary", "reason", "detail", "label")
                 if st.get(k) is not None and not isinstance(st[k], str)]
        if st.get("calls") is not None and (isinstance(st["calls"], bool) or not isinstance(st["calls"], (int, float))):
            errs.append(f"단계 {st['id']} 의 calls 가 수가 아니다 — {st['calls']!r}")
    g = s.get("gate")
    if g is not None:
        if not isinstance(g, dict) or not isinstance(g.get("candidates"), list):
            errs.append(f"gate.candidates 가 배열이 아니다 — {g!r}")
        elif strict:
            if not isinstance(g.get("step"), str):
                errs.append(f"gate.step 이 글이 아니다 — {g!r}")
            if not all(isinstance(c, dict) and isinstance(c.get("label"), str) and isinstance(c.get("key"), str)
                       for c in g["candidates"]):
                errs.append(f"gate.candidates 가 {{label, key}} 꼴이 아니다 — {g['candidates']!r}")
            if g.get("message") is not None and not isinstance(g["message"], str):
                errs.append(f"gate.message 가 글이 아니다 — {g['message']!r}")
    r = s.get("report")
    if r is not None and not (isinstance(r, dict) and (r.get("warnings") is None or isinstance(r["warnings"], list))):
        errs.append(f"report 의 꼴이 틀렸다 — {r!r}")
    return errs


def _st(state: dict, step: str) -> dict:
    hit = [x for x in state["steps"] if x.get("id") == step]
    assert len(hit) == 1, f"단계 {step} 가 한 번 있어야 한다 — {[x.get('id') for x in state['steps']]}"
    return hit[0]


# ── SSE 프레임(설계 §3.2) ──────────────────────────────────────────────────────────────────────
_RUN = "run-7f3a"
_TITLE = "시장불량 원인 분석"
_TITLES = {"anchor": "기준 키", "ft": "시장불량 이력", "delib": "메커니즘"}
_SUM = {"anchor": "S26 은 plm_model SM-S938 로 풀린다 [anchor.c1]",
        "ft": "깜빡임 기록 42건 — 고장 모드 둘로 갈린다 [ft.c1] [ft.c2]",
        "delib": "구동 IC 의 저온 래치업이 가장 그럴듯하다 — 반증 좌석은 FPCB 접촉을 남겼다 [delib.c2]"}
_CANDS = [{"label": "패널 구동 IC 불량", "key": "FM-0112"}, {"label": "FPCB 커넥터 접촉", "key": "FM-0187"}]
_GATE_MSG = "고장 모드 후보가 둘이다 — 하나를 고른 뒤 이어서"
_FLAG_FT = "결과에 글자 그대로 없는 키는 넘기지 않는다: mode_key"     # 포털 step_done 이 다는 표지의 꼴 그대로


def _plan(states=("pending", "pending", "pending"), *, resumed: bool = False, state: str = "running") -> dict:
    """plan — 실행을 만들었거나 이었거나 다시 붙었을 때. 단계 셋(기준 키 · 시장불량 이력 · 메커니즘 심의)."""
    rows = (("anchor", "platform", ["rootdesigndatahub"], "코어 허브"), ("ft", "platform", ["failuretrace"], "FailureTrace"),
            ("delib", "deliberation", ["hwax-deliberation"], "전문가 심의"))
    return {"kind": "plan", "run_id": _RUN, "routine_id": "rt-12ab", "version_no": 3, "title": _TITLE,
            "purpose": "S26 의 화면 깜빡임 시장불량 — 원인 · 시험 · 대책", "state": state, "resumed": resumed,
            "steps": [{"id": i, "title": _TITLES[i], "kind": k, "state": st, "backends": b, "label": lb}
                      for (i, k, b, lb), st in zip(rows, states, strict=True)],
            "report": {"title": "S26 화면 깜빡임 분석", "sections": ["anchor", "ft", "delib", "insight"], "upload": "auto"}}


def _step(step: str, detail: str | None = None) -> dict:
    """step — 단계 시작 · 심의 진행(detail 은 한 줄)."""
    e = {"kind": "step", "run_id": _RUN, "step": step, "title": _TITLES[step], "state": "running"}
    return e if detail is None else {**e, "detail": detail}


def _closed(step: str, state: str, *, calls: int, reason: str = "", flags=(), summary: str | None = None) -> dict:
    """step_done — state 는 포털이 고친 값, summary 는 600자까지."""
    return {"kind": "step_done", "run_id": _RUN, "step": step, "state": state, "reason": reason,
            "summary": _SUM[step] if summary is None else summary, "flags": list(flags), "calls": calls}


_GATE = {"kind": "gate", "run_id": _RUN, "step": "ft", "candidates": _CANDS, "message": _GATE_MSG}
_REPORT = {"kind": "report", "run_id": _RUN, "ra_upload": "auto", "ra_report_id": 42,
           "coverage": {"counts": {"ok": 3}, "not_ok": []}, "warnings": ["인사이트 2문단에 근거 없는 수치가 있다"]}

# 한 판 — 기준 키는 풀리고 시장불량 이력이 후보 둘로 갈려 '고를 것' 에서 스트림이 끝난다.
_TO_GATE = [_plan(), _step("anchor"), _closed("anchor", "ok", calls=1), _step("ft", "pd_defect 조회 2/6"),
            _closed("ft", "ambiguous", calls=2, reason="고장 모드 후보가 둘이다", flags=[_FLAG_FT]), _GATE,
            {"kind": "done", "run_id": _RUN, "state": "waiting"}]

# 끝까지 간 판 — 심의 단계는 진행 한 줄을 두 번 고쳐 쓰고, 보고서를 낸 뒤 done 으로 닫는다.
_TO_DONE = [_plan(), _step("anchor"), _closed("anchor", "ok", calls=1), _step("ft"), _closed("ft", "ok", calls=3),
            _step("delib", "라운드 1/3 · 좌석 발언"), _step("delib", "라운드 2/3 · 교차 심문"), _closed("delib", "ok", calls=2),
            _REPORT, {"kind": "done", "run_id": _RUN, "state": "done"}]

_SNAPS = "let s; const snaps = []; for (const e of input) { s = R.mergeRoutine(s, e); snaps.push(plain(s)); } out(snaps);"


# ── mergeRoutine ────────────────────────────────────────────────────────────────────────────
def test_SSE_한_판을_접으면_고를_것에서_멈춘_상태가_된다():
    """§3.2 순서 그대로 — plan(단계 셋) → step anchor → step_done anchor ok → step ft → step_done ft ambiguous → gate(후보 둘) →
    done(waiting). 프레임마다 접은 상태를 떠서 중간도 본다. 단계 프레임의 state · title 은 단계의 것이라 실행에 번지면 안 된다."""
    snaps = _node(_SNAPS, _TO_GATE)
    assert len(snaps) == len(_TO_GATE)
    for e, s in zip(_TO_GATE, snaps, strict=True):
        assert not _shape_errors(s), (e["kind"], _shape_errors(s))
        assert (s["run_id"], s["title"]) == (_RUN, _TITLE), f"{e['kind']} 프레임 뒤 실행 id · 제목이 바뀌었다"
    planned, run_a, done_a, run_b, done_b, gated, end = snaps
    assert [s["state"] for s in snaps] == ["running"] * 5 + ["waiting"] * 2, "단계 프레임의 state 가 실행 상태로 번졌다"

    assert planned.get("routine_id") == "rt-12ab"
    assert [(x["id"], x["title"], x["kind"], x["state"]) for x in planned["steps"]] == [
        ("anchor", "기준 키", "platform", "pending"), ("ft", "시장불량 이력", "platform", "pending"),
        ("delib", "메커니즘", "deliberation", "pending")]
    assert not planned.get("gate") and not planned.get("resumed")

    assert _st(run_a, "anchor")["state"] == "running"
    a = _st(done_a, "anchor")
    assert (a["state"], a.get("summary"), a.get("calls")) == ("ok", _SUM["anchor"], 1)
    assert not a.get("reason") and not a.get("flags")

    b = _st(run_b, "ft")
    assert (b["state"], b.get("detail")) == ("running", "pd_defect 조회 2/6")
    assert _st(run_b, "anchor").get("summary") == _SUM["anchor"], "다음 단계 프레임이 앞 단계 요약을 지웠다"

    b = _st(done_b, "ft")
    assert (b["state"], b.get("summary"), b.get("reason"), b.get("flags"), b.get("calls")) == (
        "ambiguous", _SUM["ft"], "고장 모드 후보가 둘이다", [_FLAG_FT], 2)

    for s in (gated, end):
        g = s.get("gate") or {}
        assert (g.get("step"), g.get("candidates"), g.get("message")) == ("ft", _CANDS, _GATE_MSG), "후보 단추가 설 gate 가 없다"
    assert [(x["id"], x["state"], x.get("summary") or "") for x in end["steps"]] == [
        ("anchor", "ok", _SUM["anchor"]), ("ft", "ambiguous", _SUM["ft"]), ("delib", "pending", "")]


def test_보고서까지_간_판은_done_과_보고서_칸으로_끝난다():
    """심의 단계의 step 은 진행 한 줄(detail)을 고쳐 쓰고, report 프레임(ra_report_id)이 보고서 칸을 채운 뒤 done 이 실행 상태를 닫는다."""
    snaps = _node(_SNAPS, _TO_DONE)
    for e, s in zip(_TO_DONE, snaps, strict=True):
        assert not _shape_errors(s), (e["kind"], _shape_errors(s))
    assert [s["state"] for s in snaps] == ["running"] * 9 + ["done"], "실행 상태를 바꾸는 것은 plan · gate · done 뿐이다"
    d1, d2, closed = (_st(snaps[i], "delib") for i in (5, 6, 7))
    assert (d1["state"], d1.get("detail")) == ("running", "라운드 1/3 · 좌석 발언")
    assert (d2["state"], d2.get("detail")) == ("running", "라운드 2/3 · 교차 심문"), "진행 한 줄은 마지막 것이다"
    assert (closed["state"], closed.get("summary"), closed.get("calls")) == ("ok", _SUM["delib"], 2)
    end = snaps[-1]
    assert not end.get("gate")
    assert [x["state"] for x in end["steps"]] == ["ok", "ok", "ok"]
    rep = end.get("report") or {}
    assert (rep.get("ra_upload"), rep.get("ra_report_id"), rep.get("warnings")) == ("auto", 42, _REPORT["warnings"])
    assert not rep.get("ra_error") and not rep.get("ra_next")


def test_report_프레임은_RA_오류와_다음_할_일도_싣는다():
    """RA 토큰이 없으면 ra_error(서비스 계정으로 떨어지지 않는다 — Q1), upload=ask 면 ra_next. 화면은 둘 다 보고서 곁에 적는다."""
    no_token = {**_REPORT, "ra_report_id": None, "ra_error": "Report Archive 토큰이 없다 — 토큰을 등록하면 올라간다",
                "warnings": []}
    ask = {"kind": "report", "run_id": _RUN, "ra_upload": "ask", "ra_next": "routine_report_submit(run_id, upload=true) 로 올린다",
           "coverage": {"counts": {"ok": 3}, "not_ok": []}, "warnings": []}
    got = _node("out(input.reports.map((r) => fold([r, input.done], fold(input.head))));",
                {"head": _TO_DONE[:8], "reports": [no_token, ask], "done": {"kind": "done", "run_id": _RUN, "state": "done"}})
    for s in got:
        assert not _shape_errors(s), _shape_errors(s)
        assert s["state"] == "done"
    r0, r1 = (s.get("report") or {} for s in got)
    assert r0.get("ra_error") == no_token["ra_error"] and not r0.get("ra_report_id")
    assert (r1.get("ra_upload"), r1.get("ra_next")) == ("ask", ask["ra_next"]) and not r1.get("ra_report_id")


def test_done_프레임은_실행_상태와_까닭을_싣는다():
    """§3.2 done 의 state 는 done · waiting · failed · cancelled · running(실행기 오류로 멈춤 — 이어서 가능)이다. 화면은 이 값으로
    '이어서' · '멈춤' 을 낸다."""
    ends = [{"kind": "done", "run_id": _RUN, "state": "running",
             "reason": "실행기 오류 — '이어서' 를 누르면 끝난 단계를 건너뛰고 잇는다"},
            {"kind": "done", "run_id": _RUN, "state": "failed",
             "reason": "단계 anchor(기준 키) 결과 없음 — '멈춤' 으로 짠 단계라 실행을 멈췄다"},
            {"kind": "done", "run_id": _RUN, "state": "cancelled"}]
    got = _node("out(input.ends.map((e) => R.mergeRoutine(fold(input.head), e)));",
                {"head": _TO_GATE[:2], "ends": ends})
    for s in got:
        assert not _shape_errors(s), _shape_errors(s)
    assert [(s["state"], s.get("reason") or "") for s in got] == [
        ("running", ends[0]["reason"]), ("failed", ends[1]["reason"]), ("cancelled", "")]


def test_이어서_온_plan_은_알던_요약을_남긴다():
    """plan 은 이었거나 다시 붙었을 때도 온다(resumed — 지금 원장의 모양). plan 의 단계에는 요약이 없으니, 앞서 받은 요약(같은
    스트림에서 접은 것이든 실행 보기로 되살린 것이든)을 지우면 끝난 단계가 빈 칸으로 보인다."""
    resumed = _plan(("ok", "ok", "pending"), resumed=True)
    got = _node("out([fold([...input.frames, input.plan]), R.mergeRoutine(R.routineFromRunView(input.view), input.plan)]);",
                {"frames": _TO_GATE, "plan": resumed, "view": _run_view()})
    for s in got:
        assert not _shape_errors(s), _shape_errors(s)
        assert s.get("resumed") is True and s["state"] == "running"
        assert [(x["id"], x["state"]) for x in s["steps"]] == [("anchor", "ok"), ("ft", "ok"), ("delib", "pending")]
        assert (_st(s, "anchor").get("summary"), _st(s, "ft").get("summary")) == (_SUM["anchor"], _SUM["ft"]), \
            "이어서 온 plan 이 알던 요약을 지웠다"


_ODD = [
    {"kind": "routine_future", "run_id": _RUN, "x": 1},                        # 모르는 종류
    {"run_id": _RUN, "step": "ft"},                                           # kind 가 없다.
    {"kind": "step", "run_id": _RUN},                                         # 단계 id 가 없다.
    {"kind": "step", "run_id": _RUN, "step": "nope"},                         # 계획에 없는 단계
    {"kind": "step_done", "run_id": _RUN, "step": "ft"},                      # 상태 · 요약 · 표지 · 호출 수가 없다.
    {"kind": "step_done", "run_id": _RUN, "step": "ft", "state": "ok", "summary": None, "flags": None, "calls": None},
    {"kind": "step_done", "step": "ft", "state": "ok"},                       # run_id 가 없다.
    {"kind": "gate", "run_id": _RUN},                                         # 단계 · 후보가 없다.
    {"kind": "gate", "run_id": _RUN, "step": "ft", "candidates": None},
    {"kind": "report", "run_id": _RUN},
    {"kind": "done", "run_id": _RUN},                                         # state 가 없다.
    {"kind": "plan", "run_id": _RUN},                                         # 단계가 없다.
    {"kind": "plan", "run_id": _RUN, "steps": [{"id": "anchor"}]},            # 칸이 빈 단계
]


def test_모르는_종류나_칸이_빠진_프레임에도_터지지_않고_상태가_쓸만하다():
    """중계 · 에이전트 서버의 판이 어긋나도 화면이 죽으면 안 된다. 모르는 종류는 앞선 상태 그대로다. 칸이 빠진 프레임 뒤에도
    실행 id 와 알던 단계가 남고, 화면이 .map 으로 도는 칸(steps · gate.candidates · flags)이 배열이며, 다음 정상 프레임이 그대로
    접힌다. 앞선 상태가 없을 때(plan 전에 온 프레임)도 터지지 않는다."""
    good = _closed("delib", "skipped", calls=0, reason="실행 상한 — 시간 60분", summary="")
    # 프레임마다 앞선 상태를 새로 접는다 — 앞선 값을 고치는 결함은 아래 따로 본다(여기서 섞이면 탓이 엉뚱한 프레임에 간다).
    got = _node(
        "const mk = () => fold(input.base); const base0 = plain(mk());"
        " const res = input.odd.map((e) => { let s; try { s = R.mergeRoutine(mk(), e); } catch (err) { return { err: fail(err) }; }"
        "   try { return { s: plain(s), next: plain(R.mergeRoutine(s, input.good)) }; }"
        "   catch (err) { return { s: plain(s), nextErr: fail(err) }; } });"
        " const fresh = input.odd.map((e) => { try { return { s: plain(R.mergeRoutine(undefined, e)) }; }"
        "   catch (err) { return { err: fail(err) }; } });"
        " out({ base: base0, res, fresh });",
        {"base": _TO_GATE[:3], "odd": _ODD, "good": good})
    for e, r in zip(_ODD, got["res"], strict=True):
        assert "err" not in r, f"{e} 에서 터졌다 — {r.get('err')}"
        assert "nextErr" not in r, f"{e} 뒤 정상 프레임에서 터졌다 — {r.get('nextErr')}"
        s = r["s"]
        assert not _shape_errors(s, strict=False), (e, _shape_errors(s, strict=False))
        assert s["run_id"] == _RUN, f"{e} 뒤에 실행 id 를 잃었다 — 화면이 실행 보기 · 멈춤 · 고르기를 못 부른다"
        if e.get("kind") == "plan":
            continue                                  # plan 은 단계를 다시 세운다 — 빈 plan 뒤의 단계 수는 정하지 않았다.
        assert {"anchor", "ft", "delib"} <= {x["id"] for x in s["steps"]}, f"{e} 가 알던 단계를 지웠다"
        assert _st(r["next"], "delib")["state"] == "skipped", f"{e} 뒤에 정상 프레임이 접히지 않는다"
    for e, r in zip(_ODD[:2], got["res"][:2], strict=True):
        assert r["s"] == got["base"], f"모르는 종류 {e} 가 상태를 바꿨다"
    for e, r in zip(_ODD, got["fresh"], strict=True):
        assert "err" not in r, f"앞선 상태 없이 {e} 에서 터졌다 — {r.get('err')}"
        assert r["s"] is None or (isinstance(r["s"], dict) and isinstance(r["s"].get("steps"), list)), \
            f"앞선 상태 없이 {e} 를 접은 꼴이 틀렸다 — {r['s']}"


def test_mergeRoutine_은_앞선_상태를_고치지_않는다():
    """React 상태다. 접기는 새 값을 돌려주고 앞선 값(이미 그린 메시지)을 고치지 않는다 — 고치면 참조가 같아 memo 한 화면이
    다시 그리지 않고, 같은 앞선 값에서 두 번 접으면(재시도) 앞 결과가 섞인다."""
    frames = [*_TO_GATE, _plan(("ok", "ok", "pending"), resumed=True), *_TO_DONE[5:]]
    got = _node("let s; const refs = [], texts = [];"
                " for (const e of input) { s = R.mergeRoutine(s, e); refs.push(s); texts.push(JSON.stringify(s)); }"
                " out(refs.map((r, i) => JSON.stringify(r) === texts[i]));", frames)
    assert got == [True] * len(frames), [f"{i}:{frames[i]['kind']}" for i, ok in enumerate(got) if not ok]


# ── routineFromRunView ──────────────────────────────────────────────────────────────────────
def _run_view(*, ft: str = "ambiguous", delib: str = "pending", **run) -> dict:
    """GET /routines-api/runs/{id} — R2 실물(run_view)의 칸 그대로에 R3 의 단계 findings · 실행 limit_kind 를 더했다. 기본은 고를 것이
    남은 실행(waiting)이다. run 의 칸은 키워드로 덮는다."""
    common = {"budget": {"calls": 8, "seconds": 300}, "readiness": {"state": "allowed", "reason": ""}}
    lenient = {"empty": "continue", "denied": "skip", "unavailable": "skip"}
    steps = [
        {"id": "anchor", "title": "기준 키", "kind": "platform", "backends": ["rootdesigndatahub"],
         "allowed": {"rootdesigndatahub": ["object_resolve"]}, "goal": "S26 을 코어 허브의 plm_model 로 푼다", "uses": [],
         "expect": {"keys": ["model_key"], "fields": {}}, "blocked": {"empty": "stop", "denied": "stop", "unavailable": "stop"},
         "deliberation": None, **common,
         "state": "ok", "calls": 2, "reason": "", "summary": _SUM["anchor"], "keys": {"model_key": "SM-S938"},
         "findings": [{"text": "S26 의 plm_model 은 SM-S938 이다", "refs": ["anchor.c1"]}], "flags": []},
        {"id": "ft", "title": "시장불량 이력", "kind": "platform", "backends": ["failuretrace"],
         "allowed": {"failuretrace": ["pd_defect_search", "pd_defect_get"]},
         "goal": "SM-S938 의 화면 깜빡임 불량 기록을 유형 · 시기별로", "uses": ["anchor"],
         "expect": {"keys": ["mode_key"], "fields": {}}, "blocked": lenient, "deliberation": None, **common,
         "state": ft, "calls": 3, "reason": "고장 모드 후보가 둘이다" if ft == "ambiguous" else "",
         "summary": _SUM["ft"] if ft != "running" else "", "keys": {"mode_key": "FM-0112"} if ft == "ok" else {},
         "findings": [{"text": "깜빡임 42건 가운데 31건이 저온 출하분이다", "refs": ["ft.c1", "ft.c2"]}], "flags": [_FLAG_FT]},
        {"id": "delib", "title": "메커니즘", "kind": "deliberation", "backends": ["hwax-deliberation"],
         "allowed": {"hwax-deliberation": ["deliberate_start", "deliberate_status", "deliberate_result"]},
         "goal": "불량의 메커니즘을 밝힌다", "uses": ["ft"], "expect": {"keys": [], "fields": {}}, "blocked": lenient,
         "deliberation": {"job": "mechanism", "chair_template": None}, **common,
         "state": delib, "calls": 2 if delib == "ok" else 0, "reason": "", "summary": _SUM["delib"] if delib == "ok" else "",
         "keys": {}, "findings": [{"text": "구동 IC 저온 래치업", "refs": ["delib.c2"]}] if delib == "ok" else [], "flags": []},
    ]
    if ft == "ambiguous":
        steps[1]["candidates"] = _CANDS
    head = {"id": _RUN, "routine_id": "rt-12ab", "version_no": 3, "title": _TITLE, "executor": "chat", "state": "waiting",
            "reason": None, "calls": 5, "started_at": 1793318400, "deadline": 1793322000, "ended_at": None,
            "ra_report_id": None, "ra_error": None, "limits": {"minutes": 60, "calls": 60}, "limit_reached": None,
            "limit_kind": None, "report_ready": False}
    return {"contract": 1, "run": {**head, **run}, "inputs": {"model": "S26", "symptom": "화면 깜빡임"},
            "purpose": "S26 의 화면 깜빡임 시장불량 — 원인 · 시험 · 대책", "steps": steps,
            "next_step": next((x["id"] for x in steps if x["state"] in ("pending", "running", "ambiguous")), None),
            "report": {"title": "S26 화면 깜빡임 분석", "sections": ["anchor", "ft", "delib", "insight"], "upload": "auto"}}


def test_실행_보기에서_되살린_상태는_단계와_고를_것을_잇는다():
    """흐르지 않는 메시지는 getRun 으로 채운다. 단계 칩(상태 · 호출 수) · 요약 · 까닭 · 표지가 실행 보기와 같고, 고를 것이 남은
    실행(waiting)은 ambiguous 단계의 후보로 gate 를 다시 세운다 — 새로고침한 뒤에도 후보 단추가 돌아와야 고를 수 있다.
    R2 포털(findings · limit_kind 없음)의 보기도 읽는다."""
    waiting = _run_view()
    done = _run_view(ft="ok", delib="ok", state="done", calls=7, ended_at=1793320500, ra_report_id=77, report_ready=True)
    failed = _run_view(ft="failed", state="failed", ended_at=1793319000,
                       reason="단계 ft(시장불량 이력) 실패 — '멈춤' 으로 짠 단계라 실행을 멈췄다")
    limited = _run_view(ft="running", state="running", limit_reached="시간 60분", limit_kind="time")
    old = _run_view()
    old["run"].pop("limit_kind")
    for x in old["steps"]:
        x.pop("findings")
    views = [waiting, done, failed, limited, old]
    got = _node("out(input.map((v) => R.routineFromRunView(v)));", views)
    for v, s in zip(views, got, strict=True):
        assert not _shape_errors(s), (v["run"]["state"], _shape_errors(s))
        assert (s["run_id"], s.get("routine_id"), s["title"], s["state"]) == (_RUN, "rt-12ab", _TITLE, v["run"]["state"])
        assert [(x["id"], x["title"], x["kind"], x["state"], x.get("summary") or "", x.get("reason") or "", x.get("flags") or [],
                 x.get("calls") or 0) for x in s["steps"]] == [
            (x["id"], x["title"], x["kind"], x["state"], x["summary"], x["reason"], x["flags"], x["calls"]) for x in v["steps"]]
    w, d, f, lim, o = got
    for s in (w, o):
        g = s.get("gate") or {}
        assert (g.get("step"), g.get("candidates")) == ("ft", _CANDS), "고를 것이 남은 실행인데 후보로 gate 를 세우지 않았다"
    assert not d.get("gate") and not f.get("gate") and not lim.get("gate")
    assert (d.get("report") or {}).get("ra_report_id") == 77, "끝난 실행의 RA 초안 번호가 빠졌다"
    assert f.get("reason") == failed["run"]["reason"], "실패한 실행의 까닭이 빠졌다"


# ── 상태 판정 · 라벨 ────────────────────────────────────────────────────────────────────────
_LIVE = {"queued": True, "running": True, "waiting": False, "done": False, "failed": False, "cancelled": False,
         "interrupted": False}
_TERMINAL = {"queued": False, "running": False, "waiting": False, "done": True, "failed": True, "cancelled": True,
             "interrupted": False}


def test_도는_중과_끝남의_판정표():
    """isRoutineLive 는 queued · running, isRoutineTerminal 은 done · failed · cancelled 다. waiting(고를 것) · interrupted(이어서)는
    어느 쪽도 아니어서 화면이 고르기 · 이어서 단추를 낸다. 모르는 상태는 둘 다 거짓이다."""
    assert set(_LIVE) == set(_TERMINAL) == set(RUN_STATES), "판정표가 포털 실행 상태 일곱을 다 덮지 않는다"
    states = [*RUN_STATES, "", "paused"]
    got = _node("out(input.map((s) => [R.isRoutineLive(s), R.isRoutineTerminal(s)]));", states)
    assert dict(zip(states, map(tuple, got), strict=True)) == {
        **{s: (_LIVE[s], _TERMINAL[s]) for s in RUN_STATES}, "": (False, False), "paused": (False, False)}


def test_단계_상태_라벨은_포털_STATE_LABEL_과_같은_글이다():
    """보고서(포털 렌더)와 챗 화면이 같은 단계를 같은 말로 부른다 — 열 상태를 다 덮는다. 실행 상태 라벨은 일곱 상태를 다 덮는다."""
    assert len(STAGE_STATES) == 10 and set(STATE_LABEL) == set(STAGE_STATES)
    got = _node("out({ step: R.ROUTINE_STEP_LABEL, run: R.ROUTINE_RUN_LABEL });", None)
    assert got["step"] == STATE_LABEL
    assert got["run"] == {"queued": "줄", "running": "도는 중", "waiting": "고를 것", "done": "끝남", "failed": "실패",
                          "cancelled": "멈춤", "interrupted": "끊김"}
    assert set(got["run"]) == set(RUN_STATES)


def _union(rel: str, name: str) -> list[str]:
    src = (_SRC / rel).read_text(encoding="utf-8")
    m = re.search(rf"export type {name}\s*=\s*([^;]+);", src)
    assert m, f"{rel} 에 {name} 형이 없다"
    return re.findall(r"'([a-z_]+)'", m.group(1))


def test_화면_형의_상태_목록은_포털과_같다():
    """types/chat.ts 의 RoutineStepState · RoutineRunState 가 포털 STAGE_STATES · RUN_STATES 와 어긋나면 새 상태가 라벨 없이 그려진다."""
    assert sorted(_union("types/chat.ts", "RoutineStepState")) == sorted(STAGE_STATES)
    assert sorted(_union("types/chat.ts", "RoutineRunState")) == sorted(RUN_STATES)


def test_준비도_라벨과_사슬_글은_routine_ts_로_옮겨_함께_쓴다():
    """§6 — R1 RoutinesView 의 READY_LABEL · chain() 을 routine.ts 로 옮겨 루틴 고르기(챗)와 루틴 화면이 함께 쓴다. 사본이 남으면
    두 화면의 말이 갈린다."""
    titles = [{"title": "기준 키"}, {"title": "시장불량 이력"}, {"title": "메커니즘"}]
    got = _node("out({ ready: R.READY_LABEL, chain: [R.chain(input), R.chain(input.slice(0, 1)), R.chain([])] });", titles)
    assert got["ready"] == {"allowed": "부를 수 있음", "not_connected": "토큰 등록 필요", "denied": "권한 없음",
                            "unavailable": "이 박스에 없음"}
    assert set(got["ready"]) == set(_union("api/routines.api.ts", "Readiness")), "준비도 라벨이 Readiness 형과 어긋난다"
    assert got["chain"] == ["기준 키 → 시장불량 이력 → 메커니즘", "기준 키", ""]
    view = (_SRC / "pages/procedures/RoutinesView.tsx").read_text(encoding="utf-8")
    assert "const READY_LABEL" not in view and "function chain(" not in view, "RoutinesView 에 옮기기 전 사본이 남았다"
    for name in ("READY_LABEL", "chain"):
        assert re.search(rf"import\s*\{{[^}}]*\b{name}\b[^}}]*\}}\s*from\s*['\"]\.\./\.\./components/chat/routine['\"]", view), \
            f"RoutinesView 가 {name} 을 routine.ts 에서 가져오지 않는다"
