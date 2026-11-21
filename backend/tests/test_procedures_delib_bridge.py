# 절차 실행 → 심의 다리(챗 중계의 delib_opts.procedure_run) — 서버가 근거를 싣고, 리스크 심사 · 남의 실행 · 도는 실행은 서버가 거절한다
"""실행 상세의 '심의로 넘기기' 는 실행 id 만 보낸다(docs/procedures W-114). 근거는 포털이 그 사람의 실행 원장에서 지어 싣는다 — 브라우저를
거치지 않으므로 가려진 값이 풀리거나 근거가 바뀔 틈이 없고, 리스크 심사로 보내는 길은 화면이 아니라 여기서 막힌다(사용자 결정 11-22 —
리스크 심사의 입구는 리스크 앱 하나다, D-18 · 10-31 A17).
"""
import json

import httpx
import pytest

from app.auth.provider import Principal
from app.deps import principal_pat_or_session

_GROUPS = ["feat:deliberation", "feat:procedures"]


@pytest.fixture()
def portal():
    """u1 로 들어온 포털 → (TestClient, app, 에이전트 서버가 받은 요청 몸들). 가짜 에이전트 서버는 받은 것을 적고 곧바로 끝낸다."""
    from fastapi.testclient import TestClient

    from app.main import app

    who = {"p": Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=list(_GROUPS))}
    app.dependency_overrides[principal_pat_or_session] = lambda: who["p"]
    seen: list[dict] = []

    def upstream(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/chat"):
            seen.append(json.loads(req.read()))
        return httpx.Response(200, stream=httpx.ByteStream(b"event: done\ndata: {}\n\n"),
                              headers={"content-type": "text/event-stream"})
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
            try:
                yield c, app, seen, who
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def _run(app, *, owner="u1", state="done", mode="live"):
    st = app.state.procedures_store
    rid = st.create_run(owner_sub=owner, run_by=owner, inputs={}, origin="replay", mode=mode, title="열충격 SED 판정")
    st.begin_step(rid, 0, backend="odb-hub", tool="odb_list_components", args={"job_id": "J1"}, mode="live")
    st.finish_step(rid, 0, ok=True, result_text='{"ap": {"x": 50.1}}')
    st.begin_step(rid, 1, backend="heax-thermal_shock_mcp", tool="predict_sed", args={"sample": {"ap_cx": 50.1}}, mode="live")
    st.finish_step(rid, 1, ok=False, state="unknown", stage="timeout", error="30초 안에 응답이 없다")
    st.set_run_state(rid, state, ended=state in ("done", "failed"))
    return rid


def _chat(c, rid, *, message="/심의 SED 가 기준을 넘는 까닭", **opts):
    return c.post("/agent/chat", json={"message": message, "delib_opts": {"procedure_run": rid, **opts}})


def test_실행_id_만_보내면_서버가_단계_기록을_근거로_싣는다(portal):
    c, app, seen, _ = portal
    rid = _run(app)
    r = _chat(c, rid, chair_template="diagnosis")
    assert r.status_code == 200, r.text
    assert len(seen) == 1
    do = seen[0]["delib_opts"]
    assert "procedure_run" not in do, "엔진이 모르는 칸을 넘기지 않는다"
    assert do["chair_template"] == "diagnosis", "유형은 사람이 고른 그대로다"
    ev = do["evidence"]
    assert [e["tool"] for e in ev] == ["odb_list_components", "predict_sed"]
    assert ev[0]["result"] == '{"ap": {"x": 50.1}}' and ev[0]["source"] == "절차 실행 열충격 SED 판정#1"
    assert ev[1]["result"].startswith("[실행 여부를 모르는 단계 — 30초 안에 응답이 없다]")


def test_사람이_함께_실은_근거는_뒤에_남는다(portal):
    c, app, seen, _ = portal
    rid = _run(app)
    r = _chat(c, rid, evidence=[{"source": "붙인 문서", "result": "본문"}])
    assert r.status_code == 200, r.text
    assert [e["source"] for e in seen[0]["delib_opts"]["evidence"]][-1] == "붙인 문서" and len(seen[0]["delib_opts"]["evidence"]) == 3


@pytest.mark.parametrize("chair", ["risk-review", "risk-review-sealed", " Risk-Review "])
def test_리스크_심사로는_서버가_넘기지_않는다(portal, chair):
    """화면이 그 유형을 안 보여도 요청은 직접 보낼 수 있다 — 에이전트 서버를 부르기 전에 422 다."""
    c, app, seen, _ = portal
    r = _chat(c, _run(app), chair_template=chair)
    assert r.status_code == 422 and "리스크 심사" in r.json()["detail"], (r.status_code, r.text[:300])
    assert seen == [], "거절한 요청이 에이전트 서버까지 갔다"


def test_남의_실행은_없는_것과_같다(portal):
    c, app, seen, _ = portal
    r = _chat(c, _run(app, owner="someone-else"))
    assert r.status_code == 404 and seen == [], (r.status_code, r.text[:200])
    assert _chat(c, "0" * 32).status_code == 404


def test_절차_권한이_없으면_403(portal):
    c, app, seen, who = portal
    rid = _run(app)
    who["p"] = Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:deliberation"])
    r = _chat(c, rid)
    assert r.status_code == 403 and seen == [], (r.status_code, r.text[:200])


def test_심의를_여는_발화가_아니면_싣지_않고_거절한다(portal):
    """일반 챗 턴은 delib_opts 를 읽지 않는다 — 그대로 보내면 근거 없이 일반 답이 오고 사람은 실린 줄 안다."""
    c, app, seen, _ = portal
    r = _chat(c, _run(app), message="SED 가 왜 높지")
    assert r.status_code == 422 and "심의" in r.json()["detail"] and seen == [], (r.status_code, r.text[:200])


def test_도는_실행과_부른_단계가_없는_실행은_넘기지_않는다(portal):
    c, app, seen, _ = portal
    r = _chat(c, _run(app, state="running"))
    assert r.status_code == 409 and "도는" in r.json()["detail"], (r.status_code, r.text[:200])
    st = app.state.procedures_store
    plan = st.create_run(owner_sub="u1", run_by="u1", inputs={}, origin="replay", mode="plan", title="t")
    st.begin_step(plan, 0, backend="b", tool="find_reports", args={}, mode="plan")
    st.finish_step(plan, 0, ok=True, state="skipped", stage="plan")
    st.set_run_state(plan, "done", stage="plan", ended=True)
    r = _chat(c, plan)
    assert r.status_code == 422 and "근거" in r.json()["detail"] and seen == [], (r.status_code, r.text[:200])


def test_실행_id_꼴이_아니면_422(portal):
    c, app, seen, _ = portal
    assert _chat(c, "../../etc").status_code == 422 and seen == []


def test_칸을_안_실은_심의는_종전_그대로다(portal):
    c, app, seen, _ = portal
    r = c.post("/agent/chat", json={"message": "/심의 x", "delib_opts": {"chair_template": "risk-review",
                                                                        "evidence": [{"source": "s", "result": "r"}]}})
    assert r.status_code == 200, r.text
    assert seen[0]["delib_opts"] == {"chair_template": "risk-review", "evidence": [{"source": "s", "result": "r"}]}


def test_합친_근거가_상한을_넘으면_잘라_보내지_않고_거절한다(portal):
    c, app, seen, _ = portal
    r = _chat(c, _run(app), evidence=[{"source": f"s{i}", "result": "r"} for i in range(119)])   # 119 + 단계 기록 2 = 121 > 120
    assert r.status_code == 422 and "상한" in r.json()["detail"] and seen == [], (r.status_code, r.text[:200])
