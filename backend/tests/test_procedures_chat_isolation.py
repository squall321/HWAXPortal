# 절차 실행기가 자리를 다 쓰고 게이트웨이에 붙잡혀 있어도 챗 한 턴은 429 없이 곧바로 끝난다 — 절차의 격리(PLAN §3, checklist S1 검증 · W-120)
"""checklist S1 '검증' 의 '챗 동시 실행에서 429 · 지연 없음' 을 LLM 없이 되는 데까지 닫는다.

격리의 실질은 셋이다 — 절차는 챗의 퍼밋(`agent_semaphore` — 넘치면 큐 없이 429)을 쓰지 않고 자기 세마포어(`procedures_concurrency`)에 줄을
서며, 자기 httpx 클라이언트로 게이트웨이를 부르고, 기다리는 동안 이벤트 루프를 놓는다. 여기서는 그 셋이 한꺼번에 깨지면 드러나는 꼴로 잰다 —
챗 퍼밋을 절차 자리 수와 같게(2) 줄여 두고 절차 실행 셋(자리 둘 + 줄 하나)을 게이트웨이 initialize 에 붙잡은 채 챗 한 턴을 보낸다.

못 재는 것 — 진짜 LLM 이 답하는 동안의 지연. 에이전트 서버는 대역이다(dev 에 GLM · Qwen 이 없고 웹 챗 Claude 는 부르지 않는다). 챗 턴 자체의
LLM 지연은 절차와 무관한 자리라 cae00 실사용에서 본다.
"""
import asyncio
import json
import time

import httpx

from tests.test_procedures_routes import PREFIX, _HeldGateway, _until, client, user  # noqa: F401  (client · user 는 픽스처)


def _chat_upstream(req: httpx.Request) -> httpx.Response:
    frames = [f"event: {e}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n".encode() for e, d in (
        ("token", {"delta": "답"}), ("result", {"type": "text", "content": "답"}), ("done", {}))]
    return httpx.Response(200, stream=httpx.ByteStream(b"".join(frames)), headers={"content-type": "text/event-stream"})


def test_절차가_자리를_다_쓰고_붙잡혀_있어도_챗은_429_없이_곧바로_끝난다(user):
    c, h = user
    st = c.app.state.procedures_store
    me = c.get("/auth/me", headers=h).json()["subject"]
    gw = _HeldGateway(["ra_find_reports"])          # initialize 를 붙잡는다 — 풀어 주기 전까지 실행은 게이트웨이 앞에 선다(상한 5초)
    started, finished = gw.install(c)
    runner = c.app.state.procedures_runner
    slots = runner.sem._value
    assert slots == 2, "절차 자리 기본값(procedures_concurrency) — 바뀌면 아래 '자리 + 1' 을 다시 본다"
    c.app.state.agent_semaphore = asyncio.Semaphore(slots)   # 챗 퍼밋을 절차 자리 수로 — 같은 세마포어를 쓰면 여기서 429 가 난다

    vid = st.create_procedure(owner_sub=me, title="t", spec={"title": "t", "vars": [], "steps": [
        {"backend": "ra", "tool": "find_reports", "args": {"q": "x"}}]})["version_id"]
    pid = st.get_version(vid)["procedure_id"]
    runs = []
    for _ in range(slots + 1):
        r = c.post(f"{PREFIX}/runs", json={"procedure_id": pid, "mode": "live"}, headers=h)
        assert r.status_code == 202, (r.status_code, r.text[:200])   # 넘쳐도 429 가 아니라 줄이다
        runs.append(r.json()["run_id"])
    _until(lambda: len(started) == slots + 1 and runner.sem.locked(), "절차 자리가 다 차기")
    assert not finished and gw.calls == [], "붙잡힌 실행이 게이트웨이를 지났다"

    real = c.app.state.agent_client
    c.app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(_chat_upstream))
    try:
        assert not c.app.state.agent_semaphore.locked(), "절차가 챗 퍼밋을 쥐고 있다"
        t0 = time.monotonic()
        with c.stream("POST", "/agent/chat", json={"message": "안녕"}, headers=h) as r:
            status, text = r.status_code, "".join(r.iter_text())
        took = time.monotonic() - t0
    finally:
        c.app.state.agent_client = real
    assert status == 200 and "event: result" in text, (status, text[:300])
    assert took < 2.0, f"챗 한 턴이 {took:.2f}초 — 붙잡힌 절차 실행 뒤에 줄을 섰다"
    assert not finished and runner.sem.locked(), "챗이 끝날 때까지 절차는 여전히 붙잡혀 있어야 이 잼이 뜻이 있다"

    gw.release.set()
    _until(lambda: len(finished) == slots + 1, "풀어 준 뒤 절차 실행이 모두 끝나기")
    assert [st.get_run(r)["state"] for r in runs] == ["done"] * (slots + 1)
    assert [n for n, _ in gw.calls] == ["ra_find_reports"] * (slots + 1)
