# 절차 실행의 단계 기록을 심의 근거 · 챗 대화로 옮기는 다리(app/procedures/handoff.py)의 시험 — 상한 · 가림 유지 · 실패와 모름 표지
import json

import pytest

from app.config import Settings
from app.procedures import handoff as H
from app.procedures.store import ProceduresStore


@pytest.fixture()
def st(tmp_path):
    return ProceduresStore(Settings(procedures_store_path=str(tmp_path / "wb.sqlite")))


def _run(st, *, mode="live", title="열충격 SED 판정"):
    return st.create_run(owner_sub="u1", run_by="u1", inputs={"odb_job": "J1"}, origin="replay", mode=mode, title=title)


def _step(st, rid, ix, tool, *, args=None, result=None, ok=True, state=None, stage=None, error=None, notes=None, backend="ra"):
    st.begin_step(rid, ix, backend=backend, tool=tool, args=args or {}, mode="live")
    st.finish_step(rid, ix, ok=ok, result_text=result, state=state, stage=stage, error=error, notes=notes)


def test_단계_기록이_근거_네_칸으로_바뀐다(st):
    rid = _run(st)
    _step(st, rid, 0, "odb_list_components", args={"job_id": "J1"}, result='{"ap": {"x": 50.1}}')
    _step(st, rid, 1, "predict_sed", args={"sample": {"ap_cx": 50.1}}, result='{"sed": 0.42}')
    got = H.run_evidence(st, st.get_run(rid))
    ev = got["evidence"]
    assert [set(e) for e in ev] == [{"source", "tool", "args", "result"}] * 2
    assert ev[0]["tool"] == "odb_list_components" and json.loads(ev[0]["args"]) == {"job_id": "J1"}
    assert ev[0]["result"] == '{"ap": {"x": 50.1}}', "성공한 단계의 결과는 한 글자도 바꾸지 않는다"
    assert ev[0]["source"] == "절차 실행 열충격 SED 판정#1" and ev[1]["source"].endswith("#2")
    assert got["called"] == 2 and got["dropped"] == 0 and got["not_called"] == []


def test_실패한_단계와_실행_여부를_모르는_단계는_그_사실이_근거에_드러난다(st):
    rid = _run(st)
    _step(st, rid, 0, "find_reports", result='{"items": []}')
    _step(st, rid, 1, "analyze_laminate", ok=False, result='{"ok": false, "errors": ["E100"]}', stage="envelope",
          error="E100 입력 스키마가 유효하지 않습니다")
    _step(st, rid, 2, "submit_job", ok=False, state="unknown", stage="timeout", error="30초 안에 응답이 없다 — 실행 여부를 모른다")
    ev = H.run_evidence(st, st.get_run(rid))["evidence"]
    assert len(ev) == 3, "실패 · 모름 단계를 근거에서 빼면 그 절차가 통째로 된 것처럼 읽힌다"
    assert not ev[0]["result"].startswith("["), ev[0]["result"][:40]
    assert ev[1]["result"].startswith("[실패한 단계 — E100 입력 스키마가 유효하지 않습니다]") and '"errors": ["E100"]' in ev[1]["result"]
    assert "(실패)" in ev[1]["source"]
    assert ev[2]["result"].startswith("[실행 여부를 모르는 단계 — 30초 안에 응답이 없다") and "(실행 여부 모름)" in ev[2]["source"]


def test_원장에_가려진_확인_토큰은_가려진_채로_넘어간다(st):
    """실행기 · 챗 기록은 원장에 넣기 전에 확인 토큰을 가린다(runner `_mask_publish_token`). 다리는 원장의 글을 읽을 뿐이라 가림이 풀리지 않는다."""
    from app.procedures.runner import _mask_publish_token

    tok = "1790000000." + "s" * 43
    rid = _run(st)
    _step(st, rid, 0, "preview_publish", args={"report_id": 7},
          result=_mask_publish_token(json.dumps({"targets": [{"slug": "b1"}], "confirm_token": tok})))
    got = H.run_evidence(st, st.get_run(rid))
    blob = json.dumps(got, ensure_ascii=False)
    assert tok not in blob and "[가림:confirm_token]" in blob
    _title, msgs = H.chat_messages(st, st.get_run(rid))
    blob = json.dumps(msgs, ensure_ascii=False)
    assert tok not in blob and "[가림:confirm_token]" in blob


def test_부르지_않은_단계는_근거가_아니고_따로_센다(st):
    rid = _run(st)
    _step(st, rid, 0, "find_reports", result='{"items": [1]}')
    _step(st, rid, 1, "add_report_tags", ok=False, state="pending", stage="gate")      # 확인 카드 — 아직 안 나갔다
    got = H.run_evidence(st, st.get_run(rid))
    assert [e["tool"] for e in got["evidence"]] == ["find_reports"]
    assert got["not_called"] == [{"ix": 1, "tool": "add_report_tags", "state": "pending", "stage": "gate"}]


def test_계획_모드_실행은_넘길_근거가_없다(st):
    rid = _run(st, mode="plan")
    _step(st, rid, 0, "find_reports", state="skipped", stage="plan")
    got = H.run_evidence(st, st.get_run(rid))
    assert got["evidence"] == [] and got["called"] == 0 and len(got["not_called"]) == 1


def test_고르기를_기다리는_단계는_결과가_있어_근거가_되고_그렇게_표시한다(st):
    rid = _run(st)
    _step(st, rid, 0, "find_parts", result='{"parts": [{"name": "A"}, {"name": "B"}]}')
    st.finish_step(rid, 0, ok=False, state="pending", stage="select:ask", error=None, notes={"pick_into": "part"})
    ev = H.run_evidence(st, st.get_run(rid))["evidence"]
    assert len(ev) == 1 and ev[0]["result"].startswith("[사람의 고르기 · 확인을 기다리는 단계]") and '"name": "A"' in ev[0]["result"]


def test_상한_넷__건수_40__결과_150000자__인자_1200자__넘친_것은_말한다(st):
    assert (H.EVID_ITEMS, H.EVID_RESULT_MAX, H.EVID_ARGS_MAX) == (40, 150_000, 1_200)
    rid = _run(st)
    for i in range(45):
        _step(st, rid, i, f"tool_{i}", args={"blob": "가" * 3000} if i == 0 else {"i": i},
              result=("나" * 200_000) if i == 1 else f'{{"i": {i}}}')
    got = H.run_evidence(st, st.get_run(rid))
    ev = got["evidence"]
    assert len(ev) == 40 and got["called"] == 45 and got["dropped"] == 6
    assert ev[-1]["source"] == "절차 실행 근거 건수 초과" and "45건" in ev[-1]["result"] and "39건" in ev[-1]["result"]
    assert [e["tool"] for e in ev[:39]] == [f"tool_{i}" for i in range(39)], "앞 단계부터 싣는다"
    assert len(ev[0]["args"]) <= 1_200 and "원문" in ev[0]["args"], ev[0]["args"][-80:]
    assert len(ev[1]["result"]) <= 150_000 and "200,000자" in ev[1]["result"][-200:], ev[1]["result"][-200:]
    assert all(len(e["args"]) <= 1_200 and len(e["result"]) <= 150_000 for e in ev)


def test_원장이_앞머리만_쥔_큰_결과는_그렇다고_말한다(st):
    from app.procedures import store as S

    rid = _run(st)
    _step(st, rid, 0, "list_agents", result="x" * (S.RESULT_MAX + 10))
    ev = H.run_evidence(st, st.get_run(rid))["evidence"]
    assert ev[0]["result"].startswith("[원장에 앞 4,096자만 남은 결과"), ev[0]["result"][:80]


def test_경고는_근거에_같이_간다(st):
    """결과는 정상인데 경고만이 유일한 신호인 자리(W120)와 설명에만 있는 경고(합성 데이터 모델)는 단계 노트에 있다 — 빠지면 좌석이 모른다."""
    rid = _run(st)
    _step(st, rid, 0, "pcb_warpage_surrogate", result='{"warpage": 1.2}', notes={"warnings": ["합성 데이터로 학습한 데모"]})
    ev = H.run_evidence(st, st.get_run(rid))["evidence"]
    assert ev[0]["result"].startswith("[경고 — 합성 데이터로 학습한 데모]\n") and ev[0]["result"].endswith('{"warpage": 1.2}')


def test_챗_기록에서_온_실행은_인자_글을_그대로_쓴다(st):
    rid = _run(st)
    _step(st, rid, 0, "predict_sed", args={"_text": "sample={'ap_cx': 50.1}"}, result="0.42", backend="")
    ev = H.run_evidence(st, st.get_run(rid))["evidence"]
    assert ev[0]["args"] == "sample={'ap_cx': 50.1}"


def test_챗으로_가져가는_대화는_사람_한_줄과_단계_요약_그리고_다음_턴의_근거가_될_활동이다(st):
    rid = _run(st)
    _step(st, rid, 0, "find_reports", args={"q": "x"}, result='{"items": [1, 2]}')
    _step(st, rid, 1, "analyze_laminate", ok=False, result='{"ok": false}', stage="envelope", error="E100")
    _step(st, rid, 2, "add_report_tags", ok=False, state="pending", stage="gate")
    st.set_run_state(rid, "gated", stage="step:2")
    title, msgs = H.chat_messages(st, st.get_run(rid))
    assert title == "절차 실행 — 열충격 SED 판정"
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    body = msgs[1]["content"]
    assert "find_reports" in body and "analyze_laminate" in body and "실패" in body and "E100" in body
    assert "add_report_tags" in body and "부르지 않" in body, "부르지 않은 단계도 요약에는 보인다"
    meta = msgs[1]["meta"]
    assert meta["procedure_run"] == {"run_id": rid, "state": "gated", "mode": "live"}
    act = meta["activity"]
    assert [a["tool"] for a in act] == ["find_reports", "analyze_laminate"], "부르지 않은 단계는 조회 근거가 아니다"
    # 짧은 결과는 미리보기가 곧 전문이다 — result_full 은 미리보기보다 길 때만 싣는다(화면은 result_full ?? result_preview 로 읽는다)
    assert act[0]["ok"] is True and act[0]["result_preview"] == '{"items": [1, 2]}' and "result_full" not in act[0]
    assert json.loads(act[0]["detail"]) == {"q": "x"}
    assert act[1]["ok"] is False and act[1]["result_preview"].startswith("[실패한 단계 — E100]")
    assert all(a["call"] and a["step"] and isinstance(a["ts"], int) for a in act)


def test_챗으로_가져가는_결과는_줄인_판이고_줄였다고_말한다(st):
    rid = _run(st)
    _step(st, rid, 0, "list_agents", result="가" * 60_000)
    _t, msgs = H.chat_messages(st, st.get_run(rid))
    full = msgs[1]["meta"]["activity"][0]["result_full"]
    assert len(full) <= H.CHAT_RESULT_MAX and "60,000자" in full[-200:], full[-200:]
