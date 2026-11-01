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
                                 {"id": "²", "title": "t"}, {"id": "٣", "title": "t"}, {"id": "５８", "title": "t"},
                                 {"id": "9" * 5000, "title": "t"}, {"id": "1" * 19, "title": "t"}])
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


# ── 도는 챗 턴 — 발표자료 알림을 질문과 답 사이에 끼우지 않으려고 중계가 센다(docs/wda-deck WD-D66) ───────────────────────────
@pytest.mark.parametrize("upstream", ["ok", "down"])
def test_챗_턴이_도는_동안만_그_대화는_도는_턴이다(upstream):
    from fastapi.testclient import TestClient

    from app.agent import routes as R
    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat"])
    seen: dict = {}
    raw = _sse([("result", {"type": "text", "content": "답"}), ("done", {})])

    def agent(req):
        seen["during"] = R.turn_active(seen["cid"])
        if upstream == "down":
            raise httpx.ConnectError("에이전트 서버가 없다", request=req)
        return httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})

    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(agent))
            try:
                seen["cid"] = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
                assert R.turn_active(seen["cid"]) is False
                c.post("/agent/chat", json={"message": "질문", "conversation_id": seen["cid"]})
            finally:
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert seen["during"] is True, "사용자 발화를 남긴 뒤 상류를 부르는 동안 그 대화는 도는 턴이다"
    assert R.turn_active(seen["cid"]) is False and seen["cid"] not in R._ACTIVE_TURNS, "답을 남기면(상류가 없어도) 뺀다"


def test_끝_정리가_새어도_오래된_턴은_세지_않는다(monkeypatch):
    from app.agent import routes as R
    end = R._turn_begin("c-stale")
    assert R.turn_active("c-stale") is True
    real = R.time.monotonic
    monkeypatch.setattr(R.time, "monotonic", lambda: real() + R._TURN_STALE_S + 1)
    assert R.turn_active("c-stale") is False, "새어 남은 턴이 알림을 영영 막지 않는다"
    monkeypatch.undo()
    end()
    end()
    assert "c-stale" not in R._ACTIVE_TURNS


def test_응답을_보내기_전에_끊겨도_턴을_뺀다():
    """머리를 보내다 끊기면(ASGI 2.4) 생성기가 한 번도 돌지 않는다 — 퍼밋처럼 턴도 응답의 on_close 가 뺀다(WD-D66)."""
    from fastapi.testclient import TestClient

    from app.agent import routes as R
    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat"])
    try:
        with TestClient(app) as c:
            cid = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
            body = json.dumps({"message": "질문", "conversation_id": cid}).encode()
            msgs = [{"type": "http.request", "body": body, "more_body": False}]

            async def receive():
                return msgs.pop(0) if msgs else {"type": "http.disconnect"}

            async def send(m):
                if m["type"] == "http.response.start":
                    raise OSError("브라우저가 떠났다")

            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
                     "path": "/agent/chat", "raw_path": b"/agent/chat", "query_string": b"", "root_path": "",
                     "headers": [(b"content-type", b"application/json"), (b"host", b"testserver")],
                     "client": ("127.0.0.1", 1), "server": ("testserver", 80), "app": app}

            async def call():
                try:
                    await app(scope, receive, send)
                except OSError:
                    pass

            c.portal.call(call)
            assert R.turn_active(cid) is False and cid not in R._ACTIVE_TURNS
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def _chat_spying_append(spy, *, owner_other: bool = False) -> dict:
    """사용자 발화를 남기는 store.append 를 spy(kw, orig) 로 감싸 한 턴을 돌린다 — 상류는 답 하나. 상류를 부르는 동안의 turn_active 도 적는다."""
    from fastapi.testclient import TestClient

    from app.agent import routes as R
    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    who = {"p": Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat"])}
    app.dependency_overrides[principal_pat_or_session] = lambda: who["p"]
    seen: dict = {}
    raw = _sse([("result", {"type": "text", "content": "답"}), ("done", {})])

    def agent(req):
        seen["during"] = R.turn_active(seen["cid"])
        return httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})

    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(agent))
            store = app.state.conv_store
            orig = store.append
            store.append = lambda **kw: spy(kw, orig)
            try:
                if owner_other:
                    who["p"] = Principal(subject="u2", email="u2@hwax.local", display_name="V", groups=["feat:chat"])
                seen["cid"] = c.post("/agent/conversations", json={"title": "t", "kind": "chat"}).json()["id"]
                who["p"] = Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:chat"])
                seen["status"] = c.post("/agent/chat", json={"message": "질문", "conversation_id": seen["cid"]}).status_code
            finally:
                store.append = orig
                app.state.agent_client = real
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    seen["after"] = R.turn_active(seen["cid"]) or seen["cid"] in R._ACTIVE_TURNS
    return seen


def test_사용자_발화를_남기기_전에_도는_턴을_센다():
    """2차 적대 검토 — 발화를 남긴 뒤에 세면 그 사이(저장 스레드)에 advance 가 알림을 질문 뒤 · 답 앞에 끼울 수 있었다(WD-D76)."""
    from app.agent import routes as R

    def spy(kw, orig):
        if kw.get("role") == "user":
            spy.at = R.turn_active(kw["conversation_id"])
        return orig(**kw)

    seen = _chat_spying_append(spy)
    assert spy.at is True, "발화를 남기는 순간에 이미 도는 턴이다"
    assert seen["during"] is True and seen["after"] is False


def test_발화를_남기다_터지면_도는_턴을_뺀다():
    """생성기를 만들기 전의 예외 갈래(except) — 턴을 먼저 세므로 이 갈래의 정리가 실제로 일한다(WD-D76 — WD-D66 이 남긴 틈)."""
    import sqlite3

    def spy(kw, orig):
        if kw.get("role") == "user":
            raise sqlite3.OperationalError("database is locked")
        return orig(**kw)

    seen = _chat_spying_append(spy)
    assert seen["status"] == 500 and seen["after"] is False, "터진 요청이 그 대화를 도는 턴으로 남기지 않는다"


def test_남의_대화로_보낸_챗은_그_대화를_도는_턴으로_세지_않는다():
    """발화를 남기지 못하면(없거나 남의 대화) 곧바로 뺀다 — 세 둔 채면 그 주인의 발표자료 알림이 이 스트림 동안 밀린다(WD-D76)."""
    seen = _chat_spying_append(lambda kw, orig: orig(**kw), owner_other=True)
    assert seen["status"] == 200 and seen["during"] is False and seen["after"] is False


def test_새_턴을_셀_때_낡은_턴을_걷어_낸다():
    """끝 정리가 샌 턴은 세지 않을 뿐 남아 있었다 — 새 턴을 셀 때 6시간이 지난 것을 걷는다(WD-D76)."""
    import time

    from app.agent import routes as R
    old = time.monotonic() - R._TURN_STALE_S - 1
    R._ACTIVE_TURNS["c-gone"] = [old]
    R._ACTIVE_TURNS["c-mixed"] = [old, time.monotonic()]
    end = R._turn_begin("c-new")
    try:
        assert "c-gone" not in R._ACTIVE_TURNS and len(R._ACTIVE_TURNS["c-mixed"]) == 1
        assert R.turn_active("c-mixed") is True and R.turn_active("c-new") is True
    finally:
        end()
        R._ACTIVE_TURNS.pop("c-mixed", None)
        R._ACTIVE_TURNS.pop("c-gone", None)
    assert "c-new" not in R._ACTIVE_TURNS
