# 챗 중계의 분석 루틴 턴 — 요청 칸 · 권한 · 사람 PAT · 긴 침묵 한도 · 브라우저가 떠나도 끝까지 읽기 · meta.routine · 절차 원장 건너뜀 · 빈 답 자리 글 · 끝난 같은 답 하나 · 떼어 낸 중계 상한(docs/analysis-routines R3-design 5)
"""루틴 턴은 에이전트 서버의 실행기가 단계를 코드로 돈다(R3 D1). 중계가 할 일은 열이다.
  · 칸 `routine` 을 채운 것만 싣는다(덧붙인 말 note · 끝난 실행의 RA 초안 올리기 upload_ra 도 — upload_ra 는 run_id 와 함께만) — 에이전트 서버
    ChatRequest 에도 그 칸이 있어야 한다(없으면 조용히 버려져 '루틴: <제목>' 이 일반 챗으로 돈다).
  · feat:routines 가 없으면 403 — 세마포어보다 먼저, 에이전트 서버를 부르기 전에.
  · 싣는 토큰은 그 사람의 챗 PAT(_chat_user_pat)다 — 절차 PAT(purpose=procedure · 15분)가 아니다. 발급이 실패하면 에이전트 서버를 부르지 않고
    routine_no_pat — 일반 챗처럼 서비스 계정으로 떨어지지 않는다(AR-D4).
  · 침묵 한도는 심의 쪽(긴 값)이고 끊을 때 '서버에서 계속 돌 수 있다' 고 말한다.
  · 브라우저가 떠나도 상류를 끝까지 읽어 대화에 남긴다(루틴 턴만 — 일반 턴은 종전처럼 끊으면 상류도 끊는다).
  · 답 meta 에 포인터 routine = {run_id, routine_id, title, state} 만 — 실행 상태는 plan · done 프레임에서만 읽는다.
  · 절차 원장(from_chat.record)에는 넣지 않는다 — 루틴 원장(routine_calls)에 이미 있다(R3 D9).
  · 글 없이 끊긴 루틴 턴(침묵 한도 · 에이전트 서버가 죽음 · 상류 오류)도 자리 글로 답을 남긴다 — 버리면 대화에서 run_id 가 사라진다.
  · 끝난 실행(done · failed · cancelled)의 같은 글 답은 (대화, 실행)마다 하나 — 두 탭이 같은 실행을 끝까지 읽어도 보고서가 두 번 남지 않는다.
    글이 다른 답(끝난 실행의 RA 초안 올리기 안내)은 같은 실행 · 같은 끝이라도 남긴다.
  · 떼어 낸 중계는 상한(_DETACHED_RELAYS_MAX)까지 — 넘으면 그 턴은 일반 턴처럼 떠날 때 상류를 끊고 로그 한 줄을 남긴다.
"""
import ast
import asyncio
import contextlib
import json
import logging
import time
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.agent import routes as relay
from app.agent.routes import ChatRequest, RoutineReq, _relay_stream
from app.auth.pat_verify import verify_pat_claims
from app.auth.provider import Principal
from app.config import Settings, chat_pat_ttl_s, get_settings
from app.deps import principal_pat_or_session
from app.procedures import pat as procedure_pat
from tests.test_agent_stream_idle import _HEAD, _Audit, _frames
from tests.test_chat_relay_decouple import _Turn, _scope, _until
from tests.test_conv_store_busy_timeout import _agent, portal  # noqa: F401 — 같은 포털 · 가짜 에이전트 서버를 쓴다

_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:routines"])
_AGENT_APP = Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "app.py"
_TITLE = "시장불량 원인 분석"
_REPORT = "## S26 분석\n\n솔더 크랙이 3분기에 몰린다 [ft.c1]"
_PLAN = {"kind": "plan", "run_id": "run-1", "routine_id": "rt-1", "version_no": 2, "title": _TITLE, "purpose": "S26 시장불량",
         "state": "running", "resumed": False,
         "steps": [{"id": "ft", "title": "불량 이력", "kind": "platform", "state": "pending", "backends": ["failuretrace"],
                    "label": "FailureTrace"}],
         "report": {"title": "S26 분석", "sections": ["ft", "insight"], "upload": "auto"}}


def _sse(evt: str, data: dict) -> bytes:
    return f"event: {evt}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


class _RoutineTurn(httpx.AsyncByteStream):
    """루틴 한 턴 — plan · 도구 호출 시작 뒤 hang 초 조용하다가(그 사이 브라우저가 떠난다) 호출 끝 · 단계 닫힘 · (pad 바이트짜리 단계 글
    조각 n 개) · 보고서 · done 으로 끝난다. 몇 프레임을 내줬는지(pulled) · 끝까지 읽혔는지(finished) · 닫혔는지(closed)를 남긴다."""

    def __init__(self, hang: float = 0.0, *, n: int = 0, pad: int = 0) -> None:
        self.hang, self.n, self.pad = hang, n, pad
        self.pulled, self.finished, self.closed = 0, False, False

    def _frames(self) -> list[bytes]:
        return [
            _sse("routine", _PLAN),
            _sse("status", {"step": "도구 호출: ft_search", "tool": "ft_search", "call": "k1", "detail": "{}", "routine_step": "ft"}),
            _sse("status", {"step": "도구 완료: ft_search", "tool": "ft_search", "call": "k1", "ok": True,
                            "result_preview": "[12건]", "routine_step": "ft", "routine_call": "ft.c1"}),
            _sse("routine", {"kind": "step_done", "run_id": "run-1", "step": "ft", "state": "ok", "reason": "",
                             "summary": "12건", "flags": [], "calls": 1}),
            *[_sse("reasoning", {"delta": f"조각{i} " + "x" * self.pad}) for i in range(self.n)],
            _sse("token", {"delta": _REPORT}),
            _sse("routine", {"kind": "report", "run_id": "run-1", "ra_upload": "auto",
                             "coverage": {"counts": {"ok": 1}, "not_ok": []}, "warnings": []}),
            _sse("result", {"type": "text", "content": _REPORT}),
            _sse("routine", {"kind": "done", "run_id": "run-1", "state": "done"}),
            _sse("done", {}),
        ]

    async def __aiter__(self):
        try:
            for i, frame in enumerate(self._frames()):
                if i == 2 and self.hang:
                    await asyncio.sleep(self.hang)
                self.pulled += 1
                yield frame
            self.finished = True
        finally:
            self.closed = True


def _as_routine_user(app) -> None:
    """portal 픽스처의 u1 은 feat:deliberation 만 있다 — 루틴 권한이 있는 u1 으로 바꾼다(픽스처가 끝에 되돌린다)."""
    app.dependency_overrides[principal_pat_or_session] = lambda: _WHO


def _saved(app, cid: str) -> list[dict]:
    return app.state.conv_store.get(cid, "u1")["messages"]


def _routine_body(cid: str | None = None, **routine) -> dict:
    body = {"message": f"루틴: {_TITLE}", "routine": routine or {"id": "rt-1", "inputs": {"model": "S26"}}}
    if cid:
        body["conversation_id"] = cid
    return body


# ── 요청 칸 ─────────────────────────────────────────────────────────────────────────────────────────────
def _sent(body: ChatRequest, user_pat: str = "pat-x") -> dict:
    seen: dict = {}

    def upstream(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.read()))
        return httpx.Response(200, stream=httpx.ByteStream(b'event: done\ndata: {}\n\n'), headers={"content-type": "text/event-stream"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            return [c async for c in _relay_stream(body, _WHO, _Audit(), Settings(_env_file=None), client, user_pat)]
    asyncio.run(go())
    return seen


def test_루틴_칸은_채운_것만_에이전트_서버로_싣는다():
    new = _sent(ChatRequest(message="루틴: 분석", routine={"id": "rt-1", "version": 3, "inputs": {"model": "S26"}}))
    assert new["routine"] == {"id": "rt-1", "version": 3, "inputs": {"model": "S26"}}, "빈 run_id 를 싣지 않는다"
    assert new["user_pat"] == "pat-x"
    assert _sent(ChatRequest(message="루틴: 분석", routine={"id": "rt-1"}))["routine"] == {"id": "rt-1"}, \
        "빈 inputs · 없는 version 은 싣지 않는다"
    assert _sent(ChatRequest(message="루틴: 분석", routine={"run_id": "run-1"}))["routine"] == {"run_id": "run-1"}, "이어서는 run_id 하나"
    assert "routine" not in _sent(ChatRequest(message="안녕")), "루틴이 아닌 턴은 칸이 없다"


def test_덧붙인_말과_RA_초안_올리기도_채운_것만_에이전트_서버로_싣는다():
    """note 는 실행기가 새 실행의 routine_run_start(note=…)로 원장에 남기고 이어서 · 다시 붙기의 프롬프트도 그 값을 쓴다. upload_ra 는 끝난 실행의
    저장 보고서를 RA 초안으로 올린다(R3-design 8). 빈 note · 거짓 upload_ra 는 싣지 않는다 — 칸이 없으면 실행기는 종전 그대로다."""
    new = _sent(ChatRequest(message="3분기만 본다", routine={"id": "rt-1", "inputs": {"model": "S26"}, "note": "3분기만 본다"}))
    assert new["routine"] == {"id": "rt-1", "inputs": {"model": "S26"}, "note": "3분기만 본다"}
    assert _sent(ChatRequest(message=f"루틴: {_TITLE}", routine={"id": "rt-1", "note": ""}))["routine"] == {"id": "rt-1"}, \
        "빈 note 는 싣지 않는다 — 화면 글 '루틴: <제목>' 은 덧붙인 말이 아니다"
    assert _sent(ChatRequest(message="RA 초안 올리기", routine={"run_id": "run-1", "upload_ra": True}))["routine"] == \
        {"run_id": "run-1", "upload_ra": True}
    assert _sent(ChatRequest(message=f"루틴 이어서: {_TITLE}", routine={"run_id": "run-1", "upload_ra": False}))["routine"] == \
        {"run_id": "run-1"}, "거짓 upload_ra 는 싣지 않는다"


def test_에이전트_서버의_요청_꼴에_routine_칸이_있다():
    """싣는 칸은 에이전트 서버 ChatRequest 가 받는 칸이어야 한다 — 없는 칸은 조용히 버려진다(pydantic 기본 extra=ignore)."""
    if not _AGENT_APP.exists():
        pytest.skip(f"형제 리포 없음: {_AGENT_APP}")
    tree = ast.parse(_AGENT_APP.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatRequest")
    fields = {s.target.id for s in cls.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)}
    assert "routine" in fields, "에이전트 서버 ChatRequest 에 routine 이 없다 — '루틴: <제목>' 이 일반 챗으로 돈다"


def test_입력_상한은_키_24개_JSON_20000자다():
    assert RoutineReq(id="rt-1", inputs={f"k{i}": "v" for i in range(24)})
    edge = {"k": "가" * 19_991}                     # {"k": "…"} — 머리 · 꼬리 9자. 한글도 한 자로 센다(\uXXXX 여섯 자가 아니다)
    assert len(json.dumps(edge, ensure_ascii=False)) == 20_000
    assert RoutineReq(id="rt-1", inputs=edge)
    for bad in ({"k": "가" * 19_992}, {f"k{i}": "v" for i in range(25)}):
        with pytest.raises(ValidationError):
            RoutineReq(id="rt-1", inputs=bad)
    assert RoutineReq(run_id="run-1").id == "", "이어서는 run_id 하나로 된다"
    assert RoutineReq(id="rt-1", inputs={"a": "S26", "b": 3, "c": 1.5, "d": True, "e": {"x": 1}, "f": [1]}).inputs["d"] is True


def test_덧붙인_말은_2000자까지이고_RA_초안_올리기는_run_id_와_참거짓으로만_받는다():
    plain = RoutineReq(id="rt-1")
    assert plain.note == "" and plain.upload_ra is False, "기본은 덧붙인 말 없음 · 올리지 않음"
    assert RoutineReq(id="rt-1", note="가" * 2000).note == "가" * 2000, "한글도 한 자로 센다 — 포털 RunIn · 게이트웨이와 같은 2,000자"
    assert RoutineReq(run_id="run-1", upload_ra=True).upload_ra is True
    # 새 실행에는 올릴 보고서가 없다. "true" · 1 을 true 로 바꾸면 바깥(RA)에 글을 만드는 동작을 사람이 고르지 않은 값으로 연다.
    for bad in ({"id": "rt-1", "note": "가" * 2001}, {"id": "rt-1", "upload_ra": True},
                {"run_id": "run-1", "upload_ra": "true"}, {"run_id": "run-1", "upload_ra": 1}):
        with pytest.raises(ValidationError):
            RoutineReq(**bad)


@pytest.mark.parametrize("routine", [
    {},
    {"id": "", "run_id": ""},
    {"id": "rt-1", "inputs": {}, "executor": "web"},
    {"id": "rt-1", "inputs": {f"k{i}": "v" for i in range(25)}},
    {"id": "rt-1", "inputs": {"k": "x" * 20_000}},
    {"id": "rt-1", "inputs": {"k": None}},
    {"id": "r" * 65},
    {"run_id": "r" * 65},
    {"id": "rt-1", "version": 0},
    {"id": "rt-1", "note": "가" * 2001},
    {"id": "rt-1", "upload_ra": True},
    {"run_id": "run-1", "upload_ra": "yes"},
], ids=["빈 꼴", "id · run_id 둘 다 빔", "모르는 칸", "키 25개", "입력 20,000자 넘음", "값이 null", "id 65자", "run_id 65자", "version 0",
        "덧붙인 말 2,001자", "RA 초안 올리기에 run_id 없음", "upload_ra 가 참거짓이 아님"])
def test_루틴_요청_꼴이_틀리면_422_이고_에이전트_서버를_부르지_않는다(portal, routine):
    c, app, _path = portal
    _as_routine_user(app)
    calls: list = []
    _agent(app, _RoutineTurn(), on_call=lambda: calls.append(1))
    r = c.post("/agent/chat", json={"message": "루틴: x", "routine": routine})
    assert r.status_code == 422, r.text
    assert calls == []


# ── 권한 · 사람 PAT ──────────────────────────────────────────────────────────────────────────────────────
def test_feat_routines_가_없으면_403_이고_에이전트_서버를_부르지_않는다(portal):
    c, app, _path = portal                          # u1 — feat:deliberation 만 있다
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    calls: list = []
    _agent(app, _RoutineTurn(), on_call=lambda: calls.append(1))
    r = c.post("/agent/chat", json=_routine_body(cid))
    assert r.status_code == 403 and "feat:routines" in r.json()["detail"], r.text
    assert calls == [] and _saved(app, cid) == [], "거절한 턴은 사용자 발화도 남기지 않는다"
    # 세마포어보다 먼저 본다 — 상한이 찼어도 권한 없는 요청은 429 가 아니라 403 이다. 권한이 있으면 그다음이 상한이다.
    saved_sem = app.state.agent_semaphore
    app.state.agent_semaphore = asyncio.Semaphore(0)
    try:
        assert c.post("/agent/chat", json=_routine_body()).status_code == 403
        _as_routine_user(app)
        assert c.post("/agent/chat", json=_routine_body()).status_code == 429
    finally:
        app.state.agent_semaphore = saved_sem
    assert calls == []


@pytest.mark.parametrize("minted", [None, ""], ids=["발급 실패", "빈 토큰"])
def test_사람_PAT_가_없으면_에이전트_서버를_부르지_않고_routine_no_pat_을_낸다(portal, monkeypatch, minted):
    c, app, _path = portal
    _as_routine_user(app)
    monkeypatch.setattr(relay, "_chat_user_pat", lambda *_a, **_k: minted)
    calls: list = []
    _agent(app, _RoutineTurn(), on_call=lambda: calls.append(1))
    r = c.post("/agent/chat", json=_routine_body())
    assert r.status_code == 200
    assert _frames(r.content) == [("error", {"code": "routine_no_pat", "message": "루틴은 사람 토큰으로만 돈다 — 다시 로그인한 뒤 보낸다"}),
                                  ("done", {})]
    assert calls == [], "서비스 계정(GW_TOKEN)으로 떨어지지 않는다 — 에이전트 서버를 부르지 않는다"
    # 일반 챗은 종전대로 — 발급이 실패해도 서비스 계정으로 돈다
    _agent(app, httpx.ByteStream(b'event: done\ndata: {}\n\n'), on_call=lambda: calls.append(1))
    assert c.post("/agent/chat", json={"message": "안녕"}).status_code == 200 and calls == [1]


def test_루틴_턴은_절차_PAT_가_아니라_그_사람의_챗_PAT_를_싣는다(portal, monkeypatch):
    """루틴 턴이 에이전트 서버에 싣는 user_pat 은 _chat_user_pat 이 찍은 챗 PAT 다(PLAN 6 · 9 · context-notes C-4 — '시험으로 잠근다').
    절차 PAT(app.procedures.pat.mint — purpose=procedure · pat_name procedures · 15분)를 실으면 게이트웨이가 via=procedure 로 읽어 실행자가 mcp 로
    남고, 15분 넘게 도는 실행은 도중에 401 로 선다. 발급을 대역으로 바꾸지 않고 진짜 /agent/chat 으로 보내, 에이전트 서버가 받은 토큰을
    포털 키로 검증해 클레임을 읽는다."""
    c, app, _path = portal
    _as_routine_user(app)
    minted: list = []
    real_mint = procedure_pat.mint
    monkeypatch.setattr(procedure_pat, "mint", lambda *a, **k: minted.append(a) or real_mint(*a, **k))
    seen: dict = {}

    def upstream(req: httpx.Request) -> httpx.Response:
        seen.update(json.loads(req.read()))
        return httpx.Response(200, stream=httpx.ByteStream(b'event: done\ndata: {}\n\n'), headers={"content-type": "text/event-stream"})

    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    assert c.post("/agent/chat", json=_routine_body()).status_code == 200
    assert seen.get("routine") == {"id": "rt-1", "inputs": {"model": "S26"}}, f"시험 전제 — 루틴 턴이 에이전트 서버에 닿았다 {seen}"
    settings = get_settings()
    claims = verify_pat_claims(seen["user_pat"], keystore=app.state.keystore, revoked_jtis=[], audience=settings.pat_chat_audience)
    assert "purpose" not in claims, f"절차 PAT 를 실었다 — 게이트웨이가 via=procedure 로 읽어 실행자가 mcp 로 남는다 {claims}"
    # 게이트웨이의 챗 판별(_is_chat)이 이 둘이다 — 둘 다 맞아야 via=chat 이고 실행자가 chat 으로 남는다
    assert claims["pat_name"] == "chat-session" and str(claims["jti"]).startswith("chat-"), claims
    assert (claims["sub"], claims["email"]) == ("u1", "u1@hwax.local"), "그 사람 명의다"
    assert claims["exp"] - claims["iat"] == chat_pat_ttl_s(settings), \
        f"수명이 챗 PAT 의 것이 아니다({claims['exp'] - claims['iat']}초) — 짧으면 긴 실행이 도중에 401 로 선다"
    assert minted == [], "루틴 턴에 절차 PAT(app.procedures.pat.mint)를 찍었다"


# ── 침묵 한도 ────────────────────────────────────────────────────────────────────────────────────────────
async def _relay_routine(handler, *, idle: float, chat_idle: float) -> tuple[bytes, _Audit, float]:
    """handler(reader, writer) 로 답하는 진짜 TCP 서버에 루틴 턴을 중계한다 — 심의 한도는 공유 클라이언트의 read(idle), 챗 한도는 chat_idle."""
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    audit = _Audit()
    settings = Settings(_env_file=None, agent_server_url=f"http://127.0.0.1:{port}", agent_chat_idle_timeout_s=chat_idle)
    body = ChatRequest(message=f"루틴: {_TITLE}", routine={"id": "rt-1"})
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=idle), trust_env=False) as client:
        got = b"".join([c async for c in _relay_stream(body, _WHO, audit, settings, client, "pat-x")])
    took = time.monotonic() - t0
    server.close()
    return got, audit, took


def test_루틴_턴은_챗_침묵_한도에_걸리지_않는다():
    """심의 단계 · 작은 ReAct 하나가 챗 한도보다 오래 조용할 수 있다 — 루틴 턴은 심의 쪽 한도를 쓴다."""
    async def slow(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(_HEAD)
        await writer.drain()
        await asyncio.sleep(0.8)                       # 챗 한도(0.3초)보다 길고 심의 한도(5초)보다 짧은 침묵
        writer.write(_sse("result", {"type": "text", "content": _REPORT}) + _sse("done", {}))
        await writer.drain()
        writer.close()

    got, _audit, _took = asyncio.run(_relay_routine(slow, idle=5.0, chat_idle=0.3))
    assert [e for e, _ in _frames(got)] == ["result", "done"], "루틴 턴이 챗 침묵 한도에 끊겼다"


def test_조용해진_루틴_턴은_심의_한도에_끊기고_서버에서_계속_돌_수_있다고_말한다():
    async def stalled(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(_HEAD + _sse("routine", _PLAN))
        await writer.drain()
        await asyncio.sleep(30)

    got, audit, took = asyncio.run(_relay_routine(stalled, idle=0.4, chat_idle=10.0))
    assert took < 5, f"심의 한도 0.4초인데 {took:.1f}초를 기다렸다 — 챗 한도(10초)를 썼다"
    frames = _frames(got)
    assert frames[0] == ("routine", _PLAN) and [e for e, _ in frames[1:]] == ["error", "done"]
    err = frames[1][1]
    assert err["code"] == "agent_stream_idle"
    assert "AGENT_STREAM_IDLE_TIMEOUT_S" in err["message"] and "AGENT_CHAT_IDLE_TIMEOUT_S" not in err["message"], err
    assert "루틴은 서버에서 계속 돌 수 있다" in err["message"], "떼어 낸 실행이다 — 새로 시작하면 두 번째 실행이 나란히 돈다"
    assert [r for r in audit.rows if r.get("status") == "error"][0]["meta"] == {"reason": "agent_stream_idle", "idle_s": 0.4}


# ── 브라우저가 떠날 때 ───────────────────────────────────────────────────────────────────────────────────
def _leave_after_first_frame(app, body: bytes, spec: str):
    """첫 프레임을 받자마자 브라우저가 떠나는 ASGI 호출 — 2.3 은 http.disconnect 를 받고, 2.4 는 send 가 OSError 다(uvicorn 의 두 갈래)."""
    given, gone = [False], asyncio.Event()

    async def receive():
        if not given[0]:
            given[0] = True
            return {"type": "http.request", "body": body, "more_body": False}
        await gone.wait()
        return {"type": "http.disconnect"}

    async def send(msg):
        if msg["type"] == "http.response.body" and msg.get("body"):
            if spec == "2.4":
                raise OSError("client gone")
            gone.set()

    async def call() -> float:
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        with contextlib.suppress(Exception):   # 끊긴 연결의 ASGI 호출은 예외(ClientDisconnect)로 끝날 수 있다
            await asyncio.wait_for(app(_scope(body, spec, app), receive, send), 10)
        return loop.time() - t0

    return call


@pytest.mark.parametrize("spec", ["2.3", "2.4"])
def test_브라우저가_떠나도_루틴_턴은_상류를_끝까지_읽어_답과_meta_routine_을_남긴다(portal, spec):
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    turn = _RoutineTurn(hang=3.0)
    _agent(app, turn)
    seen: dict = {}

    async def run():
        saved_sem = app.state.agent_semaphore
        app.state.agent_semaphore = asyncio.Semaphore(1)
        try:
            seen["took"] = await _leave_after_first_frame(app, json.dumps(_routine_body(cid)).encode(), spec)()
            # 응답은 끝났는데 상류는 아직 돈다 — 퍼밋은 pump 가 끝날 때까지 쥐고, 작업은 모듈 집합이 쥔다
            seen["held"] = app.state.agent_semaphore.locked()
            seen["kept"] = len(relay._DETACHED_RELAYS)
            seen["closed_early"] = turn.closed
            seen["finished"] = await _until(lambda: turn.finished, 10.0)
            seen["saved"] = await _until(lambda: any(m["role"] == "assistant" for m in _saved(app, cid)), 10.0)
            seen["permit_back"] = await _until(lambda: not app.state.agent_semaphore.locked(), 5.0)
            seen["released_task"] = await _until(lambda: not relay._DETACHED_RELAYS, 5.0)
        finally:
            app.state.agent_semaphore = saved_sem

    c.portal.call(run)
    assert seen["took"] < 2.5, f"브라우저가 떠났는데 응답이 {seen['took']:.1f}초 동안 끝나지 않았다"
    assert not seen["closed_early"], "브라우저가 떠나자 상류를 끊었다 — 루틴 턴은 끝까지 읽는다"
    assert seen["held"] and seen["kept"] == 1, seen
    assert seen["finished"], "브라우저가 떠난 뒤 상류(에이전트 서버) 스트림을 끝까지 읽지 않았다"
    assert seen["saved"] and seen["permit_back"] and seen["released_task"], seen
    msgs = _saved(app, cid)
    assert [(m["role"], m["content"]) for m in msgs] == [("user", f"루틴: {_TITLE}"), ("assistant", _REPORT)]
    meta = msgs[1]["meta"]
    assert meta["routine"] == {"run_id": "run-1", "routine_id": "rt-1", "title": _TITLE, "state": "done"}
    assert [a.get("ok") for a in meta["activity"]] == [None, True], "단계 안 도구 호출은 활동으로 그대로 남는다"


def test_떠난_뒤의_프레임은_큐에_쌓지_않아_상한에_걸려_멈추지_않는다(portal, monkeypatch):
    """아무도 안 읽는 큐에 쌓으면 상한(_RELAY_BUFFER_BYTES)에서 상류 읽기를 멈추고 영영 깨지 않는다 — 루틴은 그대로 '도는 중' 으로 남는다."""
    c, app, _path = portal
    _as_routine_user(app)
    monkeypatch.setattr(relay, "_RELAY_BUFFER_BYTES", 400)          # 한 조각 약 150바이트 — 두세 조각이면 찬다
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    turn = _RoutineTurn(hang=0.5, n=10, pad=100)
    _agent(app, turn)
    seen: dict = {}

    async def run():
        await _leave_after_first_frame(app, json.dumps(_routine_body(cid)).encode(), "2.3")()
        seen["finished"] = await _until(lambda: turn.finished, 10.0)
        seen["saved"] = await _until(lambda: any(m["role"] == "assistant" for m in _saved(app, cid)), 10.0)

    c.portal.call(run)
    assert seen["finished"], f"브라우저가 떠난 뒤 상한(400바이트)에 걸려 상류 읽기가 멈췄다 — {turn.pulled}프레임"
    assert seen["saved"]


def test_상한에_걸려_멈춘_pump_도_브라우저가_떠나면_다시_읽는다(portal, monkeypatch):
    """숨은 탭이 읽지 않아 상한에 걸려 멈춘 뒤 탭을 닫았다 — 루틴 턴은 그 자리에서 깨어 끝까지 읽는다."""
    c, app, _path = portal
    _as_routine_user(app)
    monkeypatch.setattr(relay, "_RELAY_BUFFER_BYTES", 400)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    turn = _RoutineTurn(n=10, pad=100)
    _agent(app, turn)
    seen: dict = {}

    async def run():
        body = json.dumps(_routine_body(cid)).encode()
        given, leave = [False], asyncio.Event()

        async def receive():
            if not given[0]:
                given[0] = True
                return {"type": "http.request", "body": body, "more_body": False}
            await leave.wait()
            return {"type": "http.disconnect"}

        async def send(msg):
            if msg["type"] == "http.response.body" and msg.get("body"):
                await asyncio.Event().wait()            # 숨은 탭 — 첫 조각부터 읽지 않는다

        call = asyncio.create_task(app(_scope(body, "2.3", app), receive, send))
        await _until(lambda: turn.pulled >= 3, 2.0)
        await asyncio.sleep(0.3)                        # 상한이 없다면 이 사이에 다 읽는다
        seen["held"] = turn.pulled
        leave.set()                                     # 탭을 닫는다
        await asyncio.wait_for(call, 10)
        seen["finished"] = await _until(lambda: turn.finished, 10.0)
        seen["saved"] = await _until(lambda: any(m["role"] == "assistant" for m in _saved(app, cid)), 10.0)

    c.portal.call(run)
    assert seen["held"] <= 5, f"시험 전제 — 상한에 걸려 멈춰 있었다({seen['held']}프레임)"
    assert seen["finished"], "브라우저가 떠났는데 상한 대기(room.wait)에 선 pump 가 깨지 않았다"
    assert seen["saved"]


class _SlowClose(httpx.AsyncByteStream):
    """plan 과 'boom' 단계 프레임을 내고 조용하다. 닫는 데 0.5초가 걸린다 — pump 가 상류를 닫는 await 에 서 있게."""

    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self):
        yield _sse("routine", _PLAN)
        yield _sse("routine", {"kind": "step", "run_id": "run-1", "step": "boom", "title": "x", "state": "running"})
        await asyncio.sleep(30)

    async def aclose(self) -> None:
        await asyncio.sleep(0.5)
        self.closed = True


def test_pump_의_끝을_기다리는_사이_떠나도_퍼밋은_pump_가_돌려주고_실패는_로그로_남긴다(portal, monkeypatch, caplog):
    """pump 가 터져 상류를 닫는 사이(await) 브라우저가 떠났다 — 그 취소가 기다리던 pump 로 번지면(finally 의 anyio shield 는 asyncio 취소를
    못 막는다) 퍼밋 반납 앞에서 끊긴다. 루틴 턴은 퍼밋을 pump 만 돌려주므로 영영 새고, 상한(64)만큼 쌓이면 챗이 전부 429 다."""
    c, app, _path = portal
    _as_routine_user(app)
    real = relay._parse_sse_frame

    def parse(frame: str):
        if '"step": "boom"' in frame:
            raise RuntimeError("파싱 고장")
        return real(frame)

    monkeypatch.setattr(relay, "_parse_sse_frame", parse)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    up = _SlowClose()
    _agent(app, up)
    seen: dict = {}

    async def run():
        saved_sem = app.state.agent_semaphore
        app.state.agent_semaphore = asyncio.Semaphore(1)
        try:
            await _leave_after_first_frame(app, json.dumps(_routine_body(cid)).encode(), "2.3")()
            seen["permit_back"] = await _until(lambda: not app.state.agent_semaphore.locked(), 5.0)
            seen["released_task"] = await _until(lambda: not relay._DETACHED_RELAYS, 5.0)
            seen["closed"] = up.closed
        finally:
            app.state.agent_semaphore = saved_sem

    with caplog.at_level(logging.WARNING, logger=relay.logger.name):
        c.portal.call(run)
    assert seen["permit_back"], "pump 의 끝을 기다리던 취소가 pump 로 번져 퍼밋을 돌려주지 못했다"
    assert seen["released_task"] and seen["closed"], seen
    assert any("브라우저가 떠난 뒤 상류를 읽다 실패했다" in r.getMessage() for r in caplog.records), "받아 줄 쪽이 없는 실패는 로그로 남긴다"


@pytest.mark.parametrize("spec", ["2.3", "2.4"])
def test_루틴이_아닌_턴은_브라우저가_떠나면_종전처럼_상류도_끊는다(portal, spec):
    c, app, _path = portal
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    turn = _Turn(hang=30)
    _agent(app, turn)
    seen: dict = {}

    async def run():
        saved_sem = app.state.agent_semaphore
        app.state.agent_semaphore = asyncio.Semaphore(1)
        try:
            seen["took"] = await _leave_after_first_frame(app, json.dumps({"message": "질문", "conversation_id": cid}).encode(),
                                                          spec)()
            seen["closed"] = await _until(lambda: turn.closed, 5.0)
            seen["finished"] = turn.finished
            seen["permit_back"] = not app.state.agent_semaphore.locked()
            seen["kept"] = len(relay._DETACHED_RELAYS)
        finally:
            app.state.agent_semaphore = saved_sem

    c.portal.call(run)
    assert seen["took"] < 5 and seen["closed"] and not seen["finished"], seen
    assert seen["permit_back"] and seen["kept"] == 0, seen
    assert [(m["role"], m["content"]) for m in _saved(app, cid)] == [("user", "질문"), ("assistant", "조각0 ")]


def test_떼어_낸_중계가_상한이면_다음_루틴_턴은_일반_턴처럼_상류를_끊고_로그를_남긴다(portal, monkeypatch, caplog):
    """떼어 낸 pump 하나가 챗 퍼밋 하나 · 에이전트 서버 연결 하나를 실행 끝까지 쥔다 — 끝없이 떼면 퍼밋 상한(64)이 루틴으로 찬다.
    상한을 넘은 턴은 상류를 끊는다(실행은 에이전트 서버에서 따로 돈다). 받은 데까지와 실행 포인터는 남아 '이어서' 로 다시 붙는다."""
    c, app, _path = portal
    _as_routine_user(app)
    monkeypatch.setattr(relay, "_DETACHED_RELAYS_MAX", 1)
    cid_a = c.post("/agent/conversations", json={"title": "a"}).json()["id"]
    cid_b = c.post("/agent/conversations", json={"title": "b"}).json()["id"]
    turn_a, turn_b = _RoutineTurn(hang=2.0), _RoutineTurn(hang=30.0)
    seen: dict = {}

    async def run():
        saved_sem = app.state.agent_semaphore
        app.state.agent_semaphore = asyncio.Semaphore(2)
        try:
            _agent(app, turn_a)
            await _leave_after_first_frame(app, json.dumps(_routine_body(cid_a)).encode(), "2.3")()
            seen["kept_a"] = len(relay._DETACHED_RELAYS)
            _agent(app, turn_b)
            seen["took_b"] = await _leave_after_first_frame(app, json.dumps(_routine_body(cid_b)).encode(), "2.3")()
            seen["a_alive"] = not turn_a.finished                             # 시험 전제 — b 가 떠날 때 a 는 떼어 낸 채 돌았다
            seen["kept"] = len(relay._DETACHED_RELAYS)
            seen["permit_b_back"] = not app.state.agent_semaphore.locked()   # 둘 중 하나는 아직 a 의 pump 가 쥔다
            seen["closed_b"] = await _until(lambda: turn_b.closed, 5.0)
            seen["finished_b"] = turn_b.finished
            seen["finished_a"] = await _until(lambda: turn_a.finished, 10.0)
            seen["saved_a"] = await _until(lambda: any(m["role"] == "assistant" for m in _saved(app, cid_a)), 10.0)
            seen["released"] = await _until(lambda: not relay._DETACHED_RELAYS, 5.0)
        finally:
            app.state.agent_semaphore = saved_sem

    with caplog.at_level(logging.WARNING, logger=relay.logger.name):
        c.portal.call(run)
    assert seen["kept_a"] == 1 and seen["a_alive"], f"시험 전제 — {seen}"
    assert seen["closed_b"] and not seen["finished_b"] and seen["kept"] == 1, \
        f"상한을 넘은 루틴 턴이 떼어져 상류를 끝까지 읽으려 했다 — {seen}"
    assert seen["took_b"] < 2.5 and seen["permit_b_back"], seen
    assert seen["finished_a"] and seen["saved_a"] and seen["released"], seen
    capped = [r.getMessage() for r in caplog.records if "상한" in r.getMessage() and "상류를 끊는다" in r.getMessage()]
    assert len(capped) == 1 and "run-1" in capped[0], capped
    msgs_b = _saved(app, cid_b)
    assert [(m["role"], m["content"]) for m in msgs_b] == [("user", f"루틴: {_TITLE}"), ("assistant", relay._ROUTINE_EMPTY_REPLY)]
    assert msgs_b[1]["meta"]["routine"]["run_id"] == "run-1", "끊긴 턴도 실행 포인터를 남긴다 — '이어서' 로 다시 붙는다"


# ── 저장 ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_meta_routine_은_실행_상태만_읽고_네_칸을_늘_싣는다(portal):
    """step · step_done 의 state 는 단계 상태다 — 실행기가 도중에 멈춰 done 이 없으면 plan 의 상태(running — 이어서 가능)가 남아야 한다."""
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    note = "실행기가 멈췄다 — 이어서 할 수 있다"
    _agent(app, httpx.ByteStream(
        _sse("routine", _PLAN)
        + _sse("routine", {"kind": "step", "run_id": "run-1", "step": "ft", "title": "불량 이력", "state": "running"})
        + _sse("routine", {"kind": "step_done", "run_id": "run-1", "step": "ft", "state": "ok", "reason": "", "summary": "",
                           "flags": [], "calls": 1})
        + _sse("error", {"code": "routine_internal", "message": "x"})
        + _sse("result", {"type": "text", "content": note}) + _sse("done", {})))
    assert c.post("/agent/chat", json=_routine_body(cid)).status_code == 200
    # 다시 붙었는데 이미 끝난 실행 — plan 없이 done 만 온다. 모르는 칸은 null 로 싣는다.
    _agent(app, httpx.ByteStream(_sse("routine", {"kind": "done", "run_id": "run-1", "state": "done"})
                                 + _sse("result", {"type": "text", "content": "이미 끝났다"}) + _sse("done", {})))
    assert c.post("/agent/chat", json=_routine_body(cid, run_id="run-1")).status_code == 200
    answers = [m for m in _saved(app, cid) if m["role"] == "assistant"]
    assert [a["content"] for a in answers] == [note, "이미 끝났다"]
    assert answers[0]["meta"]["routine"] == {"run_id": "run-1", "routine_id": "rt-1", "title": _TITLE, "state": "running"}
    assert answers[1]["meta"]["routine"] == {"run_id": "run-1", "routine_id": None, "title": None, "state": "done"}


def test_루틴_턴은_절차_원장에_남기지_않는다(portal, monkeypatch):
    from app.procedures import from_chat

    c, app, _path = portal
    _as_routine_user(app)
    monkeypatch.setattr(app.state, "procedures_store", object())     # 원장 자리 — record 는 아래 대역이 받는다
    recorded: list = []
    monkeypatch.setattr(from_chat, "record", lambda *_a, **kw: recorded.append(kw) or "run-x")
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _RoutineTurn())
    r = c.post("/agent/chat", json=_routine_body(cid))
    assert r.status_code == 200 and ("result", {"type": "text", "content": _REPORT}) in _frames(r.content)
    assert _saved(app, cid)[-1]["meta"]["activity"], "시험 전제 — 루틴 턴에도 도구 활동이 있었다"
    assert recorded == [], "루틴 호출은 루틴 원장(routine_calls)에 이미 있다 — 절차 원장에 또 넣으면 두 벌이다"
    # 대조 — 같은 도구 호출이 일반 턴이면 절차 원장에 남는다(시험이 그 길을 실제로 탄다)
    _agent(app, httpx.ByteStream(
        _sse("status", {"step": "도구 호출: ft_search", "tool": "ft_search", "call": "k1", "detail": "{}"})
        + _sse("status", {"step": "도구 완료: ft_search", "tool": "ft_search", "call": "k1", "ok": True, "result_preview": "[12건]"})
        + _sse("result", {"type": "text", "content": "12건이다"}) + _sse("done", {})))
    assert c.post("/agent/chat", json={"message": "발열 문의", "conversation_id": cid}).status_code == 200
    assert [kw["conversation_id"] for kw in recorded] == [cid]


class _Cut(httpx.AsyncByteStream):
    """plan · 도구 호출 시작을 내고 글 없이 끝나는 루틴 턴 — exc 가 있으면 그 예외로(중계의 침묵 한도 · 에이전트 서버가 죽음), 없으면 오류
    프레임으로(루틴 프레임 뒤 상류 오류) 끝난다. hang 이 있으면 끝나기 전에 그만큼 조용하다(그 사이 브라우저가 떠난다)."""

    def __init__(self, exc: Exception | None = None, *, hang: float = 0.0) -> None:
        self.exc, self.hang = exc, hang
        self.finished = False

    async def __aiter__(self):
        yield _sse("routine", _PLAN)
        yield _sse("status", {"step": "도구 호출: ft_search", "tool": "ft_search", "call": "k1", "detail": "{}", "routine_step": "ft"})
        if self.hang:
            await asyncio.sleep(self.hang)
        self.finished = True
        if self.exc is not None:
            raise self.exc
        yield _sse("error", {"code": "routine_internal", "message": "실행기 오류"}) + _sse("done", {})


@pytest.mark.parametrize("exc", [httpx.ReadTimeout("idle"), httpx.RemoteProtocolError("peer closed connection"), None],
                         ids=["중계 침묵 한도", "에이전트 서버가 죽음", "루틴 프레임 뒤 상류 오류"])
def test_글_없이_끊긴_루틴_턴도_자리_글로_답을_남겨_run_id_를_잃지_않는다(portal, exc):
    """답 글이 비면 남기지 않는 것이 챗 규칙이다 — 루틴 턴에 그대로 쓰면 대화에서 run_id 가 사라져 그 실행으로 돌아갈 길이 없다."""
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _Cut(exc))
    r = c.post("/agent/chat", json=_routine_body(cid))
    assert r.status_code == 200
    assert [e for e, _ in _frames(r.content)][-2:] == ["error", "done"], "시험 전제 — 글 없이 오류로 끝났다"
    msgs = _saved(app, cid)
    assert [(m["role"], m["content"]) for m in msgs] == [("user", f"루틴: {_TITLE}"), ("assistant", relay._ROUTINE_EMPTY_REPLY)]
    assert msgs[1]["meta"]["routine"] == {"run_id": "run-1", "routine_id": "rt-1", "title": _TITLE, "state": "running"}
    # 루틴이 아닌 턴은 종전대로 — 같은 스트림이라도 빈 답은 남기지 않는다
    _agent(app, _Cut(exc))
    assert c.post("/agent/chat", json={"message": "안녕", "conversation_id": cid}).status_code == 200
    assert [m["role"] for m in _saved(app, cid)] == ["user", "assistant", "user"]


def test_브라우저가_떠난_뒤_상류가_끊겨도_떼어_낸_중계가_자리_글로_run_id_를_남긴다(portal):
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    up = _Cut(httpx.ReadTimeout("idle"), hang=0.5)
    _agent(app, up)
    seen: dict = {}

    async def run():
        await _leave_after_first_frame(app, json.dumps(_routine_body(cid)).encode(), "2.3")()
        seen["kept"] = len(relay._DETACHED_RELAYS)
        seen["saved"] = await _until(lambda: any(m["role"] == "assistant" for m in _saved(app, cid)), 5.0)
        seen["released"] = await _until(lambda: not relay._DETACHED_RELAYS, 5.0)

    c.portal.call(run)
    assert seen["kept"] == 1 and up.finished, seen
    assert seen["saved"] and seen["released"], f"떠난 뒤 끊긴 루틴 턴의 답이 없다 — 대화에서 run_id 가 사라졌다 {seen}"
    msgs = _saved(app, cid)
    assert msgs[-1]["content"] == relay._ROUTINE_EMPTY_REPLY
    assert msgs[-1]["meta"]["routine"] == {"run_id": "run-1", "routine_id": "rt-1", "title": _TITLE, "state": "running"}


def _ending(state: str, text: str, run_id: str = "run-1") -> httpx.ByteStream:
    return httpx.ByteStream(_sse("routine", {"kind": "done", "run_id": run_id, "state": state})
                            + _sse("result", {"type": "text", "content": text}) + _sse("done", {}))


def test_다시_붙은_턴이_같은_실행을_끝까지_읽어도_끝난_답은_대화에_한_번만_남는다(portal):
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _RoutineTurn())
    assert c.post("/agent/chat", json=_routine_body(cid)).status_code == 200
    # 다른 탭에서 '이어서' — 에이전트 서버가 기록 프레임을 다시 보내고 같은 끝(done)까지 간다. 화면에는 그대로 흐른다.
    _agent(app, _RoutineTurn())
    r = c.post("/agent/chat", json=_routine_body(cid, run_id="run-1"))
    assert r.status_code == 200 and ("result", {"type": "text", "content": _REPORT}) in _frames(r.content)
    user = ("user", f"루틴: {_TITLE}")
    assert [(m["role"], m["content"]) for m in _saved(app, cid)] == [user, ("assistant", _REPORT), user], \
        "같은 실행의 같은 끝은 한 번만 — 다시 붙은 턴은 사용자 발화만 남긴다"
    assert relay._ROUTINE_SAVE_LOCKS == {}, "잠금 자리는 다 쓰면 지운다 — 실행마다 쌓이지 않는다"
    # 다른 실행은 남긴다. 끝이 아닌 상태(running — 이어서 할 수 있다)는 같은 실행이라도 겹쳐 남긴다.
    for stream in (_ending("done", "다른 실행", run_id="run-2"), _ending("running", "멈췄다", run_id="run-3"),
                   _ending("running", "또 멈췄다", run_id="run-3")):
        _agent(app, stream)
        assert c.post("/agent/chat", json=_routine_body(cid)).status_code == 200
    answers = [m for m in _saved(app, cid) if m["role"] == "assistant"]
    assert [(a["content"], a["meta"]["routine"]["state"]) for a in answers] == [
        (_REPORT, "done"), ("다른 실행", "done"), ("멈췄다", "running"), ("또 멈췄다", "running")]


def _uploaded(text: str) -> httpx.ByteStream:
    """끝난 실행의 RA 초안 올리기(routine {run_id, upload_ra}) — 에이전트 서버 _upload_ra 의 꼴: 지금 원장의 plan(done) · 진행 한 줄 · report ·
    짧은 안내 글 · done(done). 보고서 글은 다시 흘리지 않는다."""
    return httpx.ByteStream(
        _sse("routine", {**_PLAN, "state": "done", "resumed": True})
        + _sse("status", {"step": "Report Archive 초안을 올리는 중 — 저장한 보고서로"})
        + _sse("routine", {"kind": "report", "run_id": "run-1", "ra_upload": "ask", "ra_report_id": "ra-7",
                           "coverage": {"counts": {"ok": 1}, "not_ok": []}, "warnings": []})
        + _sse("token", {"delta": text}) + _sse("result", {"type": "text", "content": text})
        + _sse("routine", {"kind": "done", "run_id": "run-1", "state": "done"}) + _sse("done", {}))


def test_끝난_실행의_RA_초안_올리기_안내는_보고서가_있어도_대화에_남는다(portal):
    """같은 실행 · 같은 끝(done)이라도 글이 다르면 다른 턴의 답이다 — 끝난 실행에 'RA 초안 올리기' 를 보내면(R3-design 8) 보고서 뒤에 짧은
    안내가 온다. (대화, 실행)마다 끝난 답 하나로 거르면 그 안내가 버려져 다른 기기 · 새로고침 뒤에는 올린 초안 id 도, 그 턴의 답도 대화에 없다."""
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _RoutineTurn())
    assert c.post("/agent/chat", json=_routine_body(cid)).status_code == 200
    up = f"RA 초안 올리기: {_TITLE}"
    ok = "Report Archive 초안을 올렸다 — ra-7. 게시는 RA 에서 한다."
    again = "이 실행의 Report Archive 초안은 이미 있다 — ra-7. 게시는 RA 에서 한다."
    for text in (ok, again):                 # 두 번 눌렀다 — 두 번째는 게이트웨이가 다시 만들지 않고 그렇게 말한다(글이 다르다)
        _agent(app, _uploaded(text))
        r = c.post("/agent/chat", json={**_routine_body(cid, run_id="run-1", upload_ra=True), "message": up})
        assert r.status_code == 200 and ("result", {"type": "text", "content": text}) in _frames(r.content), "시험 전제 — 안내가 흘렀다"
    msgs = _saved(app, cid)
    assert [(m["role"], m["content"]) for m in msgs] == [
        ("user", f"루틴: {_TITLE}"), ("assistant", _REPORT), ("user", up), ("assistant", ok), ("user", up), ("assistant", again)], \
        "RA 초안 올리기 안내가 같은 실행의 끝난 보고서에 가려 버려졌다"
    assert [m["meta"]["routine"] for m in msgs if m["role"] == "assistant"] == \
        [{"run_id": "run-1", "routine_id": "rt-1", "title": _TITLE, "state": "done"}] * 3
    # 같은 글은 그대로 한 번이다 — 공백만 다른 보고서를 다시 읽어도(다시 붙기) 새 답이 아니다
    _agent(app, _ending("done", "\n" + _REPORT.replace("\n\n", " \n\n") + "  \n"))
    assert c.post("/agent/chat", json=_routine_body(cid, run_id="run-1")).status_code == 200
    assert [m["content"] for m in _saved(app, cid) if m["role"] == "assistant"] == [_REPORT, ok, again], \
        "공백만 다른 같은 보고서를 새 답으로 또 남겼다"
    assert relay._ROUTINE_SAVE_LOCKS == {}


class _BothTabs(httpx.AsyncByteStream):
    """같은 실행을 읽는 두 탭의 상류 — 둘 다 plan 을 받은 뒤에야 보고서 · done 을 함께 낸다(두 중계의 끝 저장이 겹치게)."""

    def __init__(self) -> None:
        self.arrived = 0

    async def __aiter__(self):
        yield _sse("routine", _PLAN)
        self.arrived += 1
        while self.arrived < 2:
            await asyncio.sleep(0.01)
        yield (_sse("token", {"delta": _REPORT}) + _sse("result", {"type": "text", "content": _REPORT})
               + _sse("routine", {"kind": "done", "run_id": "run-1", "state": "done"}) + _sse("done", {}))


async def _stay(app, body: dict) -> bytes:
    """끝까지 붙어 있는 브라우저의 ASGI 호출 — 받은 본문을 돌려준다."""
    raw = json.dumps(body).encode()
    given, ended, got = [False], asyncio.Event(), []

    async def receive():
        if not given[0]:
            given[0] = True
            return {"type": "http.request", "body": raw, "more_body": False}
        await ended.wait()
        return {"type": "http.disconnect"}

    async def send(msg):
        if msg["type"] == "http.response.body":
            got.append(msg.get("body", b""))
            if not msg.get("more_body", False):
                ended.set()

    await asyncio.wait_for(app(_scope(raw, "2.3", app), receive, send), 10)
    return b"".join(got)


def test_두_탭의_중계가_같은_실행의_끝을_함께_저장해도_답은_하나다(portal, monkeypatch):
    """확인('아직 없다')과 넣기 사이에 다른 탭의 저장이 끼면 둘 다 넣는다 — (대화, 실행) 잠금이 둘을 한 줄로 세운다."""
    c, app, _path = portal
    _as_routine_user(app)
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    store = app.state.conv_store
    real_append = store.append

    def slow_append(**kw):
        if kw.get("role") == "assistant":
            time.sleep(0.3)          # 스레드에서 — 확인과 넣기 사이를 벌린다
        return real_append(**kw)

    monkeypatch.setattr(store, "append", slow_append)
    _agent(app, _BothTabs())
    got: list = []

    async def run():
        got.extend(await asyncio.gather(_stay(app, _routine_body(cid)), _stay(app, _routine_body(cid, run_id="run-1"))))

    c.portal.call(run)
    assert all(("result", {"type": "text", "content": _REPORT}) in _frames(b) for b in got), "시험 전제 — 두 탭 모두 끝까지 받았다"
    msgs = _saved(app, cid)
    assert [(m["role"], m["content"]) for m in msgs] == [("user", f"루틴: {_TITLE}")] * 2 + [("assistant", _REPORT)], \
        [(m["role"], m["content"]) for m in msgs]
    assert msgs[-1]["meta"]["routine"]["state"] == "done"
    assert relay._ROUTINE_SAVE_LOCKS == {}
