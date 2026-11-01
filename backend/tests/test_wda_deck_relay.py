# 중계가 RA 보고서 번호를 서버 사본에 남기는지 — 심의 결과(outcome) · '/보고서' 저장 답(ra_report). '발표자료로' 단추가 새로고침 뒤에도 서게(docs/wda-deck WD-D12)
"""왜 — 단추는 그 메시지의 RA 보고서 번호로 선다. 종전 중계는 심의 사건 가운데 turn · decision · cancelled · evidence 만 서버 사본에 남기고
outcome 을 버렸다 — 새로고침 · 다른 기기에서 연 심의는 보고서 카드도 '보고' 단계도 사라졌다(frontend DelibView 의 '되살린 심의는 stage · outcome 이
없다'). '/보고서' 는 에이전트 서버가 글로만 알렸다 — 이제 result 사건에 ra_report {id, title} 를 싣는다(HWAXAgentServer 짝 커밋).
고정하는 것 — outcome 은 답 meta.delib_outcome 으로(번호 · 제목 · 집계 · 만장일치, 번호가 없어도 집계는 남긴다), ra_report 는 답 meta.ra_report 로.
꼴이 틀린 값(번호가 숫자가 아님 · 0 이하 · 참거짓)은 남기지 않는다 — 없는 보고서로 단추가 서면 안 된다.
"""
import json

import httpx
import pytest


def _sse(frames: list[tuple[str, dict]]) -> bytes:
    return "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()


class _Body(httpx.AsyncByteStream):
    def __init__(self, raw: bytes, step: int = 37) -> None:
        self.raw, self.step = raw, step

    async def __aiter__(self):
        # 청크를 프레임 경계와 어긋나게 쪼갠다 — 중계는 완결 프레임만 읽는다
        for i in range(0, len(self.raw), self.step):
            yield self.raw[i:i + self.step]


@pytest.fixture()
def run():
    """프레임 목록을 에이전트 서버 자리에서 흘리고, 저장된 서버 대화의 메시지를 돌려준다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat", "feat:deliberation"])

    def go(message: str, frames: list[tuple[str, dict]]) -> list[dict]:
        with TestClient(app) as c:
            real = app.state.agent_client
            raw = _sse(frames)
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})))
            try:
                cid = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
                r = c.post("/agent/chat", json={"message": message, "conversation_id": cid})
                assert r.status_code == 200
                return c.get(f"/agent/conversations/{cid}").json()["messages"]
            finally:
                app.state.agent_client = real

    try:
        yield go
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def _answer(msgs: list[dict]) -> dict:
    got = [m for m in msgs if m["role"] == "assistant"]
    assert len(got) == 1, [m["role"] for m in msgs]
    return got[0]


TALLY = {"agree": 2, "conditional": 1, "oppose": 0, "abstain": 0, "total": 3, "responded": 3}


def test_심의_결과의_보고서_번호를_답_meta_로_남긴다(run):
    msgs = run("/심의 x", [
        ("delib", {"kind": "decision", "text": "결정문"}),
        ("delib", {"kind": "outcome", "report_id": 58, "title": "심의 — x", "tally": TALLY, "unanimous": False}),
        ("done", {}),
    ])
    a = _answer(msgs)
    assert a["content"] == "결정문"
    assert (a["meta"] or {}).get("delib_outcome") == {"report_id": 58, "title": "심의 — x", "tally": TALLY, "unanimous": False}


def test_보고서_없이_끝난_심의도_집계는_남기고_번호는_비운다(run):
    msgs = run("/심의 x", [
        ("delib", {"kind": "decision", "text": "결정문"}),
        ("delib", {"kind": "outcome", "report_id": None, "title": "심의 — x", "tally": TALLY, "unanimous": True}),
        ("done", {}),
    ])
    out = _answer(msgs)["meta"]["delib_outcome"]
    assert out["report_id"] is None and out["unanimous"] is True and out["tally"] == TALLY


def test_보고서_저장_답의_ra_report_를_답_meta_로_남긴다(run):
    text = "📄 Report Archive 보고서 #58 로 저장했습니다 — 「심의 — x」"
    msgs = run("/보고서", [
        ("token", {"delta": text}),
        ("result", {"type": "text", "content": text, "ra_report": {"id": 58, "title": "심의 — x"}}),
        ("done", {}),
    ])
    a = _answer(msgs)
    assert a["content"] == text and a["meta"]["ra_report"] == {"id": 58, "title": "심의 — x"}


@pytest.mark.parametrize("bad", [{"id": "abc", "title": "t"}, {"id": 0, "title": "t"}, {"id": -3, "title": "t"},
                                 {"id": True, "title": "t"}, {"title": "t"}, "58", None,
                                 {"id": "²", "title": "t"}, {"id": "٣", "title": "t"}, {"id": "５８", "title": "t"}])
def test_꼴이_틀린_ra_report_는_남기지_않는다(run, bad):
    msgs = run("/보고서", [("result", {"type": "text", "content": "저장", "ra_report": bad}), ("done", {})])
    assert "ra_report" not in (_answer(msgs)["meta"] or {})


def test_꼴이_틀린_outcome_번호는_비운다(run):
    msgs = run("/심의 x", [
        ("delib", {"kind": "decision", "text": "결정문"}),
        ("delib", {"kind": "outcome", "report_id": "58; drop", "title": 7, "tally": {"agree": "x", "total": 2}, "unanimous": "yes"}),
        ("done", {}),
    ])
    out = _answer(msgs)["meta"]["delib_outcome"]
    assert out == {"report_id": None, "title": "", "tally": {"total": 2}, "unanimous": False}


def test_보고서도_심의도_아닌_답에는_칸이_없다(run):
    msgs = run("안녕", [("result", {"type": "text", "content": "안녕하세요"}), ("done", {})])
    meta = _answer(msgs)["meta"] or {}
    assert "ra_report" not in meta and "delib_outcome" not in meta
