# 도는 웹 심의 멈춤(POST /agent/deliberate/cancel) — 세션 + CSRF · 대화 주인만 · 실행 id 로 그 심의 하나만 · 에이전트 서버의 답을 넘기고, 멈춘 사실을 중계나 창구가 대화에 한 번 남긴다
"""docs/leftovers-1017 triage A24 (나) — 사용자 결정 10-31.

웹 심의는 에이전트 서버의 분리 태스크라 화면이 떠나도 서버에서 끝까지 돌았고 멈출 길이 없었다(docs/change-request-8-10/server-setup §6).
포털 창구가 대화 주인을 확인하고 에이전트 서버 POST /deliberate/cancel 을 부른다. 고정하는 것.
  · 주인은 멈춘다 — 에이전트에 대화 id · 실행 id(run_id — 화면의 심의 칸이 쥔다) · 누가(by) · 그 사람(user_email)을 싣는다(에이전트는 그
    사람의 그 심의 하나만 접는다 — 낡은 화면이 같은 대화의 새 심의를 접지 않게, A24 검토). 실행 id 가 없으면 422 이고 에이전트를 부르지 않는다.
  · 남의 대화는 403 not_owner — 관리자도 같다(MCP deliberate_cancel 의 규칙). 없는 대화는 404 conversation_not_found. 둘 다 에이전트를 부르지 않는다.
  · CSRF 가 없거나 어긋나면 403, 세션이 없으면 401(PAT 는 받지 않는다).
  · 에이전트의 답(200 · 404 delib_not_found · 409 already_finished)은 상태 · 본문 그대로. code 없는 404 는 agent_outdated, 닿지 못하면 502,
    늦으면 504, code 없는 5xx 는 502 agent_5xx.
  · 중계가 멈춤 사건(delib kind=cancelled)을 받으면 받은 발언과 멈춤을 서버 대화에 남긴다(결정문으로 남기지 않는다). 발언 · 답에는 실행 id 를
    meta.delib_run 으로 남긴다(새로고침 · 다른 기기의 화면이 그 심의를 짚는다).
  · 받는 중계가 없으면(받기가 끊긴 화면 · 다른 기기) 창구가 멈춘 사실을 끊긴 판 글로 대화에 남기고 stop_note 로 돌려준다 — 남기지 않으면 새로고침
    뒤 같은 심의가 다시 '아직 돌 수 있다' 와 '멈춤' 으로 보였다(A24 검토). 받는 중계가 있으면 중계가 남긴다(사건 전에 끊기면 끊긴 판 글로). 같은
    실행의 멈춤은 한 번만 남긴다.
에이전트 서버는 httpx.MockTransport 로 흉내 낸다. 에이전트 쪽 실제 프로세스 시험은 HWAXAgentServer tests/test_web_delib_cancel_e2e.py 다.
"""
import asyncio
import json
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy
from app.agent import routes as relay
from app.agent.conv_store import ConversationStore
from app.auth.user_store import UserStore
from app.catalog.registry import CatalogRegistry
from app.config import Settings, get_settings
from app.main import app

_CONFIG = Path(__file__).resolve().parents[1] / "config"
OWNER, OTHER, ADMIN = "user@corp.com", "other@corp.com", "boss@corp.com"
_OK = {"conversation_id": "", "status": "cancelling", "runs": 1, "message": "멈춤을 요청했다"}
RID = "0a1b2c3d4e5f6a7b"


class _Agent:
    """에이전트 서버 대역 — 받은 요청을 적고, answer(req) 로 답한다(기본은 200 cancelling)."""

    def __init__(self) -> None:
        self.seen: list[httpx.Request] = []
        self.answer = lambda req: httpx.Response(200, json={**_OK, "conversation_id": json.loads(req.content)["conversation_id"]})

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.seen.append(req)
        return self.answer(req)


@pytest.fixture()
def portal(tmp_path):
    for name in ("systems.yaml", "access.yaml"):
        shutil.copy(_CONFIG / name, tmp_path / name)
    (tmp_path / "routes.env").write_text("\n")
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), local_bootstrap_admins=ADMIN,
                 catalog_path=str(tmp_path / "systems.yaml"), routes_path=str(tmp_path / "routes.env"),
                 access_path=str(tmp_path / "access.yaml"), conv_store_path=str(tmp_path / "conv.db"),
                 agent_server_url="http://agent.invalid")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        # 기동 뒤 바꿔 끼운다 — 실 계정 원장 · 대화 저장소 · 에이전트 서버를 건드리지 않는다
        keep = (app.state.user_store, app.state.access, app.state.catalog, app.state.conv_store, app.state.agent_client)
        app.state.user_store, app.state.access, app.state.catalog = UserStore(s), AccessPolicy(s), CatalogRegistry(s)
        app.state.conv_store = ConversationStore(s)
        agent = _Agent()
        app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(agent))
        for email in (ADMIN, OWNER, OTHER):
            c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": "pw123456"})
        h = _login(c, ADMIN)
        for email in (OWNER, OTHER):
            assert c.post(f"/auth/local/users/{email}/approve", json={"groups": []}, headers=h).status_code == 200
        try:
            yield c, agent
        finally:
            app.state.user_store, app.state.access, app.state.catalog, app.state.conv_store, app.state.agent_client = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c: TestClient, email: str) -> dict:
    r = c.post("/auth/local/login", json={"email": email, "password": "pw123456"})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("hwax_csrf")}


def _conv(c: TestClient, h: dict) -> str:
    r = c.post("/agent/conversations", json={"title": "심의", "kind": "deliberation"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _cancel(c: TestClient, cid: str, h: dict | None, rid: str = RID):
    return c.post("/agent/deliberate/cancel", json={"conversation_id": cid, "run_id": rid}, headers=h or {})


def _stored(c: TestClient, cid: str, h: dict) -> list[dict]:
    return c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]


def _audit_rows() -> list[dict]:
    rows = app.state.agent_audit._conn.execute(
        "SELECT event, status, meta FROM agent_audit WHERE event = 'delib_cancel' ORDER BY id").fetchall()
    return [{"event": e, "status": st, "meta": json.loads(m) if m else None} for e, st, m in rows]


# ── 주인 ─────────────────────────────────────────────────────────────────────────────────────────
def test_주인은_멈추고_에이전트에_대화_id_와_실행_id_와_그_사람을_싣는다(portal):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    n = len(_audit_rows())
    r = _cancel(c, cid, h)
    assert r.status_code == 200, r.text
    assert r.json() == {**_OK, "conversation_id": cid, "stop_note": relay._DELIB_CUT_STOP_NOTE}, "에이전트의 답에 남긴 멈춤 글이 붙어 온다"
    (req,) = agent.seen
    assert (req.method, req.url.path) == ("POST", "/deliberate/cancel")
    assert json.loads(req.content) == {"conversation_id": cid, "run_id": RID, "by": OWNER, "user_email": OWNER}
    row = _audit_rows()[n:]
    assert row == [{"event": "delib_cancel", "status": "ok", "meta": {"conversation": cid, "run": RID, "upstream": 200}}], row


@pytest.mark.parametrize("body", [{}, {"run_id": ""}, {"run_id": "r" * 65}], ids=["없음", "빈", "긺"])
def test_실행_id_가_없거나_어긋나면_422_이고_에이전트를_부르지_않는다(portal, body):
    """대화 id 만으로 멈추면 낡은 화면의 '멈춤' 이 같은 대화에서 다른 기기가 띄운 새 심의를 접는다(A24 검토) — 화면은 그 칸의 실행 id 를 싣는다."""
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    r = c.post("/agent/deliberate/cancel", json={"conversation_id": cid, **body}, headers=h)
    assert r.status_code == 422, r.text
    assert agent.seen == []


# ── 남 · 없는 대화 · 관리자 ──────────────────────────────────────────────────────────────────────────
def test_남의_대화는_403_not_owner_이고_에이전트를_부르지_않는다(portal):
    c, agent = portal
    cid = _conv(c, _login(c, OWNER))
    r = _cancel(c, cid, _login(c, OTHER))
    assert r.status_code == 403 and r.json()["code"] == "not_owner", r.text
    assert agent.seen == []
    assert _audit_rows()[-1] == {"event": "delib_cancel", "status": "rejected",
                                 "meta": {"conversation": cid, "run": RID, "code": "not_owner"}}


def test_관리자도_남의_심의는_멈추지_못한다(portal):
    """MCP deliberate_cancel(에이전트 delib_jobs.cancel 의 _foreign)과 같은 규칙 — 관리자는 볼 수 있어도 접지는 못한다."""
    c, agent = portal
    cid = _conv(c, _login(c, OWNER))
    r = _cancel(c, cid, _login(c, ADMIN))
    assert r.status_code == 403 and r.json()["code"] == "not_owner", r.text
    assert agent.seen == []


def test_없는_대화는_404_conversation_not_found_이고_에이전트를_부르지_않는다(portal):
    c, agent = portal
    r = _cancel(c, "0" * 32, _login(c, OWNER))
    assert r.status_code == 404 and r.json()["code"] == "conversation_not_found", r.text
    assert agent.seen == []


# ── 인증 · CSRF · 본문 ───────────────────────────────────────────────────────────────────────────────
def test_CSRF_가_없거나_어긋나면_403_이고_에이전트를_부르지_않는다(portal):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    for bad in (None, {"X-CSRF-Token": "forged"}):
        r = _cancel(c, cid, bad)
        assert r.status_code == 403 and "CSRF" in r.json()["detail"], r.text
    assert agent.seen == []


def test_세션이_없으면_401_이고_PAT_는_받지_않는다(portal):
    c, agent = portal
    cid = _conv(c, _login(c, OWNER))
    c.cookies.clear()
    assert _cancel(c, cid, None).status_code == 401
    assert _cancel(c, cid, {"Authorization": "Bearer anything"}).status_code == 401
    assert agent.seen == []


def test_본문의_모르는_칸은_422_다(portal):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    r = c.post("/agent/deliberate/cancel", json={"conversation_id": cid, "run_id": RID, "user_email": ADMIN}, headers=h)
    assert r.status_code == 422, "호출자가 실은 신원 칸은 받지 않는다 — 에이전트에 가는 신원은 세션의 것뿐이다"
    assert agent.seen == []


# ── 에이전트의 답 ─────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("status, body", [
    (404, {"code": "delib_not_found", "conversation_id": "X", "run_id": RID, "message": "이 대화에서 도는 그 웹 심의가 없다"}),
    (409, {"code": "already_finished", "conversation_id": "X", "run_id": RID, "status": "done", "message": "이미 끝난 심의다"}),
    (409, {"code": "finishing", "conversation_id": "X", "run_id": RID, "status": "running", "message": "의장이 결정문을 이미 냈다"}),
], ids=["404", "409", "finishing"])
def test_에이전트의_거절은_상태와_본문_그대로_오고_대화에_아무것도_남기지_않는다(portal, status, body):
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    agent.answer = lambda req: httpx.Response(status, json=body)
    r = _cancel(c, cid, h)
    assert (r.status_code, r.json()) == (status, body)
    assert _audit_rows()[-1]["meta"] == {"conversation": cid, "run": RID, "upstream": status, "code": body["code"]}
    assert _stored(c, cid, h) == [], "멈추지 않았는데 대화에 멈춤을 남겼다"


@pytest.mark.parametrize("answer, status, code", [
    (lambda req: httpx.Response(404, json={"detail": "Not Found"}), 404, "agent_outdated"),
    (lambda req: httpx.Response(500, text="boom"), 502, "agent_5xx"),
], ids=["옛-에이전트", "5xx"])
def test_code_없는_404_는_옛_에이전트_code_없는_5xx_는_502(portal, answer, status, code):
    c, agent = portal
    h = _login(c, OWNER)
    agent.answer = answer
    r = _cancel(c, _conv(c, h), h)
    assert (r.status_code, r.json()["code"]) == (status, code), r.text


@pytest.mark.parametrize("exc, status, code", [
    (httpx.ConnectError("refused"), 502, "agent_unreachable"),
    (httpx.ReadTimeout("slow"), 504, "agent_timeout"),
], ids=["닿지-못함", "늦음"])
def test_에이전트에_닿지_못하거나_늦으면_502_504(portal, exc, status, code):
    c, agent = portal
    h = _login(c, OWNER)

    def boom(req):
        raise exc

    agent.answer = boom
    r = _cancel(c, _conv(c, h), h)
    assert (r.status_code, r.json()["code"]) == (status, code), r.text
    assert _audit_rows()[-1]["status"] == "error"


# ── 받는 중계가 없으면 창구가 멈춘 사실을 대화에 남긴다(받기가 끊긴 화면 · 다른 기기 — A24 검토) ───────────────────────────────
def _cut_run(c: TestClient, cid: str) -> None:
    """받기가 끊긴 웹 심의 — 중계는 끊기며 받은 발언까지 남겼고(답 없음) 실행 id 를 발언에 남겼다. 그 뒤로 이 대화를 받는 중계는 없다."""
    store = app.state.conv_store
    store.append(conversation_id=cid, owner_sub=OWNER, role="user", content="/심의 힌지")
    store.append(conversation_id=cid, owner_sub=OWNER, role="persona", content="초기 입장", persona="mech-a", round=1,
                 meta={"delib_run": RID})


def test_받는_중계가_없으면_창구가_끊긴_판_글로_대화에_남기고_같은_실행은_한_번만_남긴다(portal):
    """끊긴 화면의 '멈춤' 이 200 을 받아도 대화에는 아무것도 남지 않아, 새로고침 · 다른 기기에서 같은 심의가 다시 '아직 돌 수 있다' 와 '멈춤'
    으로 보였다. 끊긴 뒤 서버에서 나온 발언은 남지 않았으므로 '지금까지의 발언은 남는다' 가 아닌 글로 남긴다."""
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    _cut_run(c, cid)
    first = _cancel(c, cid, h)
    agent.answer = lambda req: httpx.Response(200, json={"conversation_id": cid, "run_id": RID, "status": "cancelled", "runs": 0,
                                                          "already": True, "message": "이미 멈춘 심의다"})
    again = _cancel(c, cid, h)
    assert first.status_code == 200 and first.json()["stop_note"] == relay._DELIB_CUT_STOP_NOTE, first.text
    assert again.status_code == 200 and again.json()["already"] is True and again.json()["stop_note"] == relay._DELIB_CUT_STOP_NOTE
    msgs = _stored(c, cid, h)
    assert [m["role"] for m in msgs] == ["user", "persona", "assistant"], "같은 실행의 멈춤을 두 번 남겼거나 남기지 않았다"
    note = msgs[2]
    assert note["content"] == relay._DELIB_CUT_STOP_NOTE and "끊긴 뒤 서버에서 나온 발언은 남지 않았" in note["content"]
    assert "지금까지의 발언은 남" not in note["content"]
    assert note["meta"] == {"delib_cancelled": {"message": relay._DELIB_CUT_STOP_NOTE, "by": OWNER, "run_id": RID, "cut": True},
                            "delib_run": RID}
    # 새로고침 · 다른 기기 — 멈춘 심의로 되살아난다('아직 돌 수 있다' 와 '멈춤' 이 아니다)
    local = _restore(msgs)
    assert local[-1]["delib"]["cancelled"] == {"message": relay._DELIB_CUT_STOP_NOTE} and "decision" not in local[-1]["delib"]
    assert local[-1]["delib"]["runId"] == RID


def test_답_없이_끊긴_심의를_되살리면_발언에_남은_실행_id_를_쥔다():
    """새로고침 · 다른 기기에서 연 끊긴 심의 — '멈춤' 이 그 심의를 짚을 열쇠가 발언의 meta.delib_run 에 있다(없으면 단추가 없다)."""
    local = _restore([{"role": "user", "persona": None, "round": None, "content": "/심의 힌지", "meta": None, "ts": 1},
                      {"role": "persona", "persona": "mech-a", "round": 1, "content": "발언", "meta": {"delib_run": RID}, "ts": 2}])
    assert local[-1]["delib"]["runId"] == RID and "cancelled" not in local[-1]["delib"]
    bare = _restore([{"role": "persona", "persona": "mech-a", "round": 1, "content": "발언", "meta": None, "ts": 2}])
    assert "runId" not in bare[-1]["delib"], "MCP 심의 · 옛 저장분은 실행 id 가 없다 — 멈출 열쇠가 없다"


# ── 받는 중계가 있으면 중계가 남긴다 — 화면이 받는 중인 심의를 멈춘다(실제 /agent/chat 중계를 ASGI 로 돌린다) ───────────────────────────
class _Upstream:
    """에이전트 서버 대역 — /chat 은 시험이 밀어 넣는 SSE 를 흘리고(push · end), /deliberate/cancel 은 200 cancelling 으로 답한다(받은 본문을 적는다)."""

    def __init__(self) -> None:
        self.q: asyncio.Queue = asyncio.Queue()
        self.cancels: list[dict] = []

    def push(self, *frames: tuple[str, dict]) -> None:
        for ev, d in frames:
            self.q.put_nowait(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n".encode())

    def end(self) -> None:
        self.q.put_nowait(None)

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if req.url.path == "/deliberate/cancel":
            body = json.loads(req.content)
            self.cancels.append(body)
            return httpx.Response(200, json={"conversation_id": body["conversation_id"], "run_id": body["run_id"],
                                             "status": "cancelling", "runs": 1, "message": "멈춤을 요청했다"})
        q = self.q

        class _Live(httpx.AsyncByteStream):
            async def __aiter__(self):
                while (chunk := await q.get()) is not None:
                    yield chunk

        return httpx.Response(200, stream=_Live(), headers={"content-type": "text/event-stream"})


def _session(c: TestClient) -> dict:
    return {"cookie": "; ".join(f"{k}={v}" for k, v in c.cookies.items()), "x-csrf-token": c.cookies.get("hwax_csrf")}


async def _chat(c: TestClient, cid: str, gone: asyncio.Event) -> None:
    """브라우저 하나가 /agent/chat 으로 웹 심의를 받는다 — gone 이 서면 떠난다(■ · 탭 닫기). 받은 바이트는 버린다."""
    body = json.dumps({"message": "/심의 힌지", "conversation_id": cid}).encode()
    head = [(b"host", b"testserver"), (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    head += [(k.encode(), v.encode()) for k, v in _session(c).items()]
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1", "method": "POST",
             "scheme": "http", "path": "/agent/chat", "raw_path": b"/agent/chat", "query_string": b"", "root_path": "",
             "client": ("127.0.0.1", 1), "server": ("testserver", 80), "app": app, "state": {}, "headers": head}
    first = [True]

    async def receive():
        if first[0]:
            first[0] = False
            return {"type": "http.request", "body": body, "more_body": False}
        await gone.wait()
        return {"type": "http.disconnect"}

    async def send(_msg):
        return None

    await app(scope, receive, send)


async def _acancel(c: TestClient, cid: str) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
        return await ac.post("/agent/deliberate/cancel", json={"conversation_id": cid, "run_id": RID}, headers=_session(c))


async def _until(pred, timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.02)):
        if pred():
            return
        await asyncio.sleep(0.02)
    assert pred(), "기다린 일이 일어나지 않았다"


@pytest.mark.parametrize("ends", ["사건", "끊김"])
def test_받는_중계가_있으면_창구는_남기지_않고_중계가_한_번_남긴다(portal, ends):
    """받는 중인 심의를 멈추면 창구는 대화에 남기지 않는다 — 그 심의를 받는 중계가 멈춤 사건의 글로 남긴다(창구가 먼저 남기면 답이 받은
    발언보다 앞에 선다). 멈춤을 청한 뒤 사건이 오기 전에 받기가 끊기면(■ · 탭 닫기) 중계가 끊긴 판 글로 남긴다."""
    c, _agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    seen: dict = {}

    async def run():
        up, gone = _Upstream(), asyncio.Event()
        app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(up))
        chat = asyncio.create_task(_chat(c, cid, gone))
        up.push(("delib", {"kind": "stage", "stage": "r1", "run_id": RID}),
                ("delib", {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}))
        await _until(lambda: (cid, RID) in relay._DELIB_RELAYS)
        r = await _acancel(c, cid)
        seen["cancel"], seen["sent"] = (r.status_code, r.json()), list(up.cancels)
        seen["mid"] = [m["role"] for m in app.state.conv_store.get(cid, OWNER)["messages"]]
        if ends == "사건":
            up.push(("delib", {"kind": "cancelled", "by": OWNER, "message": _STOP, "run_id": RID}), ("done", {}))
            up.end()
        else:
            gone.set()
        await asyncio.wait_for(chat, 10)

    c.portal.call(run)
    status, body = seen["cancel"]
    assert status == 200 and body["status"] == "cancelling" and "stop_note" not in body, body
    assert seen["sent"] == [{"conversation_id": cid, "run_id": RID, "by": OWNER, "user_email": OWNER}]
    assert seen["mid"] == ["user"], "받는 중계가 있는데 창구가 대화에 남겼다"
    msgs = _stored(c, cid, h)
    assert [m["role"] for m in msgs] == ["user", "persona", "assistant"], msgs
    note = msgs[2]
    if ends == "사건":
        assert note["content"] == _STOP and note["meta"]["delib_cancelled"] == {"message": _STOP, "by": OWNER, "run_id": RID}
    else:
        assert note["content"] == relay._DELIB_CUT_STOP_NOTE
        assert note["meta"]["delib_cancelled"] == {"message": relay._DELIB_CUT_STOP_NOTE, "by": OWNER, "run_id": RID, "cut": True}
    assert (cid, RID) not in relay._DELIB_RELAYS


# ── 중계가 멈춤 사건을 대화에 남긴다 ─────────────────────────────────────────────────────────────────────
_STOP = "사람이 멈췄다 — 의장이 결정문을 내기 전에 멈춰 이 단의 결정문 · 보고서는 없다"


class _Body(httpx.AsyncByteStream):
    """상류 SSE 본문 — 청크를 프레임 경계와 어긋나게 쪼갠다(중계는 완결 프레임만 읽는다)."""

    def __init__(self, raw: bytes, step: int = 37) -> None:
        self.raw, self.step = raw, step

    async def __aiter__(self):
        for i in range(0, len(self.raw), self.step):
            yield self.raw[i:i + self.step]


def test_중계가_멈춤_사건을_받으면_발언과_멈춤을_대화에_남기고_결정문으로_남기지_않는다(portal):
    c, _agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    frames = [("delib", {"kind": "stage", "stage": "r1", "run_id": RID}),
              ("delib", {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}),
              ("delib", {"kind": "cancelled", "by": OWNER, "message": _STOP, "run_id": RID}), ("done", {})]
    raw = "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})))
    r = c.post("/agent/chat", json={"message": "/심의 힌지", "conversation_id": cid}, headers=h)
    assert r.status_code == 200 and '"cancelled"' in r.text
    msgs = c.get(f"/agent/conversations/{cid}", headers=h).json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "persona", "assistant"], msgs
    assert msgs[1]["content"] == "초기 입장" and msgs[1]["meta"] == {"delib_run": RID}
    assert msgs[2]["content"] == _STOP
    # 심의 프레임을 받은 턴의 답에는 중계가 answered_by='delib' 도 적는다(백로그 B11 — 다시 열 때 전문가 말풍선을 붙이지 않는다)
    assert msgs[2]["meta"] == {"delib_cancelled": {"message": _STOP, "by": OWNER, "run_id": RID}, "delib_run": RID,
                               "answered_by": "delib"}
    assert (cid, RID) not in relay._DELIB_RELAYS, "끝난 중계의 기록이 표에 남았다"
    # 다른 기기 · 새로고침이 되살린 심의 — 멈춤은 멈춤으로, 결정문으로 그리지 않는다(conversations.api.ts serverMessagesToLocal)
    local = _restore(msgs)
    assert local[-1]["delib"].get("cancelled") == {"message": _STOP} and "decision" not in local[-1]["delib"], local[-1]
    assert [t["say"] for t in local[-1]["delib"]["turns"]] == ["초기 입장"] and local[-1]["delib"]["runId"] == RID


def test_결정문_뒤에_멈춘_심의는_결정문과_멈춤을_함께_되살린다():
    """다단 심의(/시뮬심의)는 1단 결정문을 낸 뒤 2단에서 멈출 수 있다 — 답의 글은 1단 결정문이고 meta 가 멈춤을 말한다."""
    local = _restore([{"role": "persona", "persona": "mech-a", "round": 1, "content": "발언", "meta": None, "ts": 1},
                      {"role": "assistant", "persona": None, "round": None, "content": "1단 결정문",
                       "meta": {"delib_cancelled": {"message": _STOP, "by": OWNER}}, "ts": 2}])
    assert local[-1]["delib"]["decision"] == "1단 결정문" and local[-1]["delib"]["cancelled"] == {"message": _STOP}


def _relay(c: TestClient, h: dict, cid: str, frames: list, message: str) -> list[dict]:
    """에이전트 서버가 frames 를 흘리고 상류가 닫히는 /agent/chat 한 턴을 중계에 돌리고, 서버 대화에 남은 메시지를 돌려준다."""
    raw = "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, stream=_Body(raw), headers={"content-type": "text/event-stream"})))
    r = c.post("/agent/chat", json={"message": message, "conversation_id": cid}, headers=h)
    assert r.status_code == 200, r.text
    return _stored(c, cid, h)


# /시뮬심의 의 1단 끝 — 엔진이 실제로 내는 차례다(의결 뒤 마무리 표지 → 결정문 · 결과 → 1단의 done — 시뮬 래퍼가 단마다의 done 을 그대로 흘린다)
_SIM_STAGE1 = [("delib", {"kind": "stage", "stage": "r1", "run_id": RID}),
               ("delib", {"kind": "turn", "round": 1, "persona": "mech-a", "say": "1단 입장"}),
               ("delib", {"kind": "finishing"}),
               ("delib", {"kind": "decision", "text": "1단 결정문"}),
               ("delib", {"kind": "outcome", "report_id": 41, "title": "t"}),
               ("result", {"type": "text", "content": "1단 결정문"}),
               ("done", {})]
# 2단의 처음 — 단 경계 표지(checkpoint) 뒤 2단 라운드
_SIM_STAGE2 = [("delib", {"kind": "checkpoint", "stage": "sim-1", "decision_a": "1단 결정문"}),
               ("delib", {"kind": "stage", "stage": "r1", "n": 1}),
               ("delib", {"kind": "turn", "round": 1, "persona": "cae-b", "say": "2단 입장"})]
# 다단 심의의 두 꼴 — 오늘의 에이전트는 단마다 done 을 낸다(위 _SIM_STAGE1 의 끝). 단 사이 done 을 걷은 에이전트는 마지막 단의 done 하나만 낸다.
# 중계의 판정은 그 차이와 무관해야 한다
_SHAPES = pytest.mark.parametrize("stage1", [_SIM_STAGE1, _SIM_STAGE1[:-1]], ids=["단마다_done", "끝에만_done"])


@_SHAPES
def test_다단_심의가_다음_단을_도는_중에_끊기면_답에_남기고_다른_기기도_끝나지_않은_심의로_되살린다(portal, stage1):
    """/시뮬심의 는 1단 결정문 뒤 2단을 돈다. 2단 도중에 받기가 끊기면 서버 사본의 답은 1단 결정문이다 — 다음 단이 열렸다는 표지
    (meta.delib_next_stage)가 없으면 다른 기기 · 새로고침의 화면이 끝난 심의로 읽어, 서버에서 아직 도는 2단에 '멈춤' 을 내지 않는다."""
    c, _agent = portal
    h = _login(c, OWNER)
    # 상류가 닫힌(끊긴) 자리 둘 — 단 경계 표지 뒤 좌석 전환 중(2단의 심의 사건이 아직 없다) · 2단 라운드 중
    for tail, personas in ((_SIM_STAGE2[:1], 1), (_SIM_STAGE2, 2)):
        cid = _conv(c, h)
        msgs = _relay(c, h, cid, stage1 + tail, "/시뮬심의 힌지")
        assert [m["role"] for m in msgs] == ["user"] + ["persona"] * personas + ["assistant"], msgs
        ans = msgs[-1]
        assert ans["content"] == "1단 결정문" and ans["meta"]["delib_next_stage"] is True and ans["meta"]["delib_run"] == RID, ans
        d = _restore(msgs)[-1]["delib"]
        assert d["decision"] == "1단 결정문" and d.get("nextStage") is True and d["runId"] == RID, d


@_SHAPES
def test_끊긴_다단_심의를_받지_않는_화면에서_멈추면_되살릴_때_그_심의_칸에_멈춤으로_붙는다(portal, stage1):
    """2단 도중에 받기가 끊기면 중계는 1단 결정문을 답으로 남긴다. 그 뒤 받지 않는 화면(끊긴 화면 · 다른 기기)에서 멈추면 창구가 멈춤 답을 따로
    남긴다 — 되살릴 때 그 답이 일반 답 말풍선으로 따로 그려지고 1단 결정문은 끝난 심의처럼 보였다. 같은 실행의 앞 심의 칸에 멈춤으로 붙는다."""
    c, agent = portal
    h = _login(c, OWNER)
    cid = _conv(c, h)
    _relay(c, h, cid, stage1 + _SIM_STAGE2, "/시뮬심의 힌지")                # 2단 도중에 끊겼다
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(agent))   # 멈춤 창구가 부를 에이전트 대역(200 cancelling)
    r = _cancel(c, cid, h)
    assert r.status_code == 200 and r.json()["stop_note"] == relay._DELIB_CUT_STOP_NOTE, r.text
    msgs = _stored(c, cid, h)
    assert [m["role"] for m in msgs] == ["user", "persona", "persona", "assistant", "assistant"], msgs
    local = _restore(msgs)
    assert [m["role"] for m in local] == ["user", "assistant"], local
    d = local[-1]["delib"]
    assert d["decision"] == "1단 결정문" and d["cancelled"] == {"message": relay._DELIB_CUT_STOP_NOTE} and d["runId"] == RID, d
    # 다른 실행의 멈춤 답은 붙이지 않는다 — 그 심의의 멈춤이 아니다
    stray = {**msgs[-1], "meta": {**msgs[-1]["meta"], "delib_run": "f" * 16,
                                  "delib_cancelled": {**msgs[-1]["meta"]["delib_cancelled"], "run_id": "f" * 16}}}
    apart = _restore(msgs[:-1] + [stray])
    assert [m["role"] for m in apart] == ["user", "assistant", "assistant"] and "cancelled" not in apart[1]["delib"], apart


# 불량 환기(SignalForge VOC)가 있는 한 단 심의의 앞머리 — 엔진은 근거 카드와 함께 그 글을 token 으로 먼저 흘린다(결정문보다 한참 앞이다)
_VOC = "■ 최근 불량 이슈(SignalForge) — 힌지 크랙 3건"
_VOC_HEAD = [("delib", {"kind": "stage", "stage": "discover", "run_id": RID}),
             ("delib", {"kind": "evidence", "source": "SignalForge VOC", "text": _VOC, "included": True}),
             ("token", {"delta": _VOC + "\n\n"}),
             ("delib", {"kind": "stage", "stage": "r1", "n": 1}),
             ("delib", {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"})]


def test_불량_환기_앞머리만_받고_끊긴_한_단_심의는_결정문으로_남기지도_되살리지도_않는다(portal):
    """결정문 전에 받기가 끊기면 중계는 받은 앞머리(token)를 답의 글로 남긴다 — 종전엔 되살릴 때 그 글을 결정문으로 읽어 다른 기기 · 새로고침의
    화면이 끝난 심의로 보고, 서버에서 아직 도는 심의에 멈춤을 내지 않았다. 사람이 멈춘 심의(멈춤 사건)도 그 글을 결정문으로 읽었다."""
    c, _agent = portal
    h = _login(c, OWNER)
    for tail in ([], [("delib", {"kind": "cancelled", "by": OWNER, "message": _STOP, "run_id": RID}), ("done", {})]):
        cid = _conv(c, h)
        msgs = _relay(c, h, cid, _VOC_HEAD + tail, "/심의 힌지")
        assert [m["role"] for m in msgs] == ["user", "persona", "assistant"], msgs
        ans = msgs[-1]
        assert ans["content"] == _VOC + "\n\n" and ans["meta"]["delib_undecided"] is True and ans["meta"]["delib_run"] == RID, ans
        d = _restore(msgs)[-1]["delib"]
        assert "decision" not in d and d["runId"] == RID and d["evidence"][0]["source"] == "SignalForge VOC", d
        if tail:
            assert d["cancelled"] == {"message": _STOP}, d
    # 끝까지 받은 심의는 결정문이다 — 표지가 없다
    cid = _conv(c, h)
    done = _VOC_HEAD + [("delib", {"kind": "finishing"}), ("delib", {"kind": "decision", "text": "결정문"}),
                        ("delib", {"kind": "outcome", "report_id": 43, "title": "t"}), ("token", {"delta": "결정문"}),
                        ("result", {"type": "text", "content": _VOC + "\n\n결정문"}), ("done", {})]
    ans = _relay(c, h, cid, done, "/심의 힌지")[-1]
    assert "delib_undecided" not in ans["meta"] and ans["content"] == _VOC + "\n\n결정문", ans
    assert _restore(_stored(c, cid, h))[-1]["delib"]["decision"] == _VOC + "\n\n결정문"
    # 심의가 아닌 챗 답이 글 도중에 끊긴 것은 심의 표지를 달지 않는다
    cid = _conv(c, h)
    ans = _relay(c, h, cid, [("token", {"delta": "힌지 브래킷"})], "힌지 파손 원인")[-1]
    assert ans["content"] == "힌지 브래킷" and "delib_undecided" not in (ans["meta"] or {}), ans


@_SHAPES
def test_다단_심의를_끝까지_받았거나_한_단_심의면_다음_단_표지를_남기지_않는다(portal, stage1):
    c, _agent = portal
    h = _login(c, OWNER)
    stage2_end = [("delib", {"kind": "finishing"}), ("delib", {"kind": "decision", "text": "2단 결정문"}),
                  ("delib", {"kind": "outcome", "report_id": 42, "title": "t"}),
                  ("result", {"type": "text", "content": "2단 결정문"}), ("done", {})]
    for frames, message in ((stage1 + _SIM_STAGE2 + stage2_end, "/시뮬심의 힌지"), (_SIM_STAGE1, "/심의 힌지")):
        cid = _conv(c, h)
        ans = _relay(c, h, cid, frames, message)[-1]
        assert ans["role"] == "assistant" and "delib_next_stage" not in ans["meta"], ans
        assert "nextStage" not in _restore(_stored(c, cid, h))[-1]["delib"]


# 프론트에는 단위 시험 러너가 없어 그 파일을 typescript 로 옮겨 적어 node 로 부른다(test_conv_save_full 과 같은 길).
_FE = Path(__file__).resolve().parents[2] / "frontend"


def _restore(server_messages: list[dict]) -> list[dict]:
    import subprocess
    import tempfile

    if not (_FE / "node_modules/typescript").exists() or not shutil.which("node"):
        pytest.skip("frontend node_modules(typescript) 또는 node 가 없다")
    out = Path(tempfile.mkdtemp(prefix="delib-cancel-restore-"))
    try:
        (out / "api").mkdir()
        (out / "state").mkdir()
        (out / "api" / "client.js").write_text("exports.apiFetch = async () => { throw new Error('시험에서 부르지 않는다'); };\n")
        (out / "in.json").write_text(json.dumps(server_messages, ensure_ascii=False), encoding="utf-8")
        (out / "build.cjs").write_text(
            "const ts = require('typescript'); const fs = require('fs');\n"
            f"const src = {json.dumps(str(_FE / 'src'))};\n"
            "for (const [from, to] of [['api/conversations.api.ts', 'api/conversations.api.js'], ['state/chatStore.ts', 'state/chatStore.js']]) {\n"
            "  const js = ts.transpileModule(fs.readFileSync(src + '/' + from, 'utf8'),\n"
            "    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });\n"
            "  fs.writeFileSync(__dirname + '/' + to, js.outputText);\n"
            "}\n"
            "const { serverMessagesToLocal } = require('./api/conversations.api.js');\n"
            "const msgs = JSON.parse(fs.readFileSync(__dirname + '/in.json', 'utf8'));\n"
            "process.stdout.write(JSON.stringify(serverMessagesToLocal(msgs)));\n", encoding="utf-8")
        r = subprocess.run(["node", "build.cjs"], cwd=str(out), capture_output=True, text=True, timeout=120,
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(_FE / "node_modules")})
    finally:
        shutil.rmtree(out, ignore_errors=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)
