# 서버 대화 저장소의 잠금 대기(CONV_STORE_BUSY_TIMEOUT_S)와, 끝난 심의의 저장이 실패했을 때 그 사실이 로그에 남는지
"""웹 심의는 스트림이 끝난 뒤(finally) 발언 최대 199건과 결정문을 서버 대화 저장소에 쓴다 — 다른 기기에서 열거나
서버 사본에서 이어갈 때 쓰는 유일한 서버 사본이다. 잠금 대기가 sqlite3 기본 5초였고, 저장이 실패해도 스트림이 이미
닫힌 뒤라 화면에도 로그에도 아무것도 안 남았다(백업 backup-local.sh 가 이 DB 를 연다).

잠금은 다른 연결이 실제로 쥔다 — PRAGMA 값만 읽으면 '설정은 됐는데 안 걸리는' 경우를 못 본다.
"""
import asyncio
import json
import logging
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app.agent.conv_store import ConversationStore
from app.config import Settings


def _store(tmp_path, **over) -> tuple[ConversationStore, str]:
    path = str(tmp_path / "conv.sqlite")
    return ConversationStore(Settings(_env_file=None, conv_store_path=path, **over)), path


def _hold_write_lock(path: str, seconds: float) -> tuple[threading.Thread, threading.Event]:
    """다른 프로세스의 쓰기 잠금 대역 — 별도 연결이 BEGIN IMMEDIATE 로 쥐었다가 seconds 뒤(또는 release 가 서면) 놓는다."""
    held, release = threading.Event(), threading.Event()

    def run():
        c = sqlite3.connect(path, timeout=5)
        c.execute("BEGIN IMMEDIATE")
        held.set()
        release.wait(seconds)
        c.rollback()
        c.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    assert held.wait(5), "잠금을 못 쥐었다 — 시험 전제가 깨졌다"
    return t, release


def test_기본_잠금_대기는_30초다(tmp_path):
    store, _ = _store(tmp_path)
    assert store._conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000, "sqlite3 기본 5초로 남아 있다"
    assert Settings(_env_file=None).conv_store_busy_timeout_s == 30.0


def test_잠금이_한도_안에_풀리면_저장된다(tmp_path):
    store, path = _store(tmp_path, conv_store_busy_timeout_s=5)
    cid = store.create(owner_sub="u1", title="t", kind="deliberation")
    t, _release = _hold_write_lock(path, 0.6)
    t0 = time.monotonic()
    assert store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="결정문") is True
    assert time.monotonic() - t0 >= 0.4, "잠금이 풀릴 때까지 기다린 것이 아니다 — 잠금 대역이 안 걸렸다"
    t.join()
    assert [m["content"] for m in store.get(cid, "u1")["messages"]] == ["결정문"]


def test_잠금이_한도를_넘기면_그_시간_뒤에_실패한다(tmp_path):
    """손잡이가 실제 대기 시간이다 — 0.3초로 주면 0.3초쯤에 포기한다(종전이면 5초를 기다렸다)."""
    store, path = _store(tmp_path, conv_store_busy_timeout_s=0.3)
    cid = store.create(owner_sub="u1", title="t", kind="deliberation")
    t, release = _hold_write_lock(path, 30.0)      # 시험이 풀어 줄 때까지 쥔다 — 느린 박스에서도 잠금이 먼저 풀리지 않게
    t0 = time.monotonic()
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="결정문")
        took = time.monotonic() - t0
    finally:
        release.set()
        t.join()
    assert 0.2 <= took < 4.0, f"잠금 대기 0.3초인데 {took:.2f}초 뒤에 포기했다(종전이면 5초)"


def _hold_read_lock(path: str) -> sqlite3.Connection:
    """백업의 읽기 잠금 대역 — backup-local.sh 가 여는 그 모양(mode=ro)으로 읽기 트랜잭션을 쥔다. 놓으려면 close() 한다."""
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, isolation_level=None)
    c.execute("BEGIN")
    c.execute("SELECT count(*) FROM messages").fetchone()
    return c


def test_읽기_잠금은_저장을_막지_않는다(tmp_path):
    """백업은 DB 를 통째로 읽는 동안 읽기 잠금을 쥔다. 종전 저널(delete)에서는 그 동안 append 의 commit 이 잠금 대기만큼 멈췄다 —
    그 대기가 포털의 이벤트 루프 위라 로그인과 다른 사람의 릴레이가 같이 멈춘다. WAL 에서는 읽는 쪽이 쓰기를 막지 않는다."""
    store, path = _store(tmp_path, conv_store_busy_timeout_s=2)
    cid = store.create(owner_sub="u1", title="t", kind="deliberation")
    reader = _hold_read_lock(path)
    t0 = time.monotonic()
    try:
        assert store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="결정문") is True
        took = time.monotonic() - t0
    finally:
        reader.close()
    assert took < 1.0, f"읽는 쪽이 쥔 동안 저장이 {took:.2f}초 기다렸다"
    assert [m["content"] for m in store.get(cid, "u1")["messages"]] == ["결정문"]
    assert store._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_WAL_로_못_바꿔도_기동은_하고_로그로_말한다(tmp_path, caplog):
    """저널 모드를 바꾸는 순간 다른 연결이 DB 를 쥐고 있으면 sqlite 가 'database is locked' 를 던진다. 포털은 SSO 허브다 —
    대화 저장소 하나 때문에 기동을 못 하면 로그인이 같이 내려간다. 종전 모드로 돌고, 다음 기동이 다시 바꾼다."""
    before, path = _store(tmp_path)
    before._conn.execute("PRAGMA journal_mode=DELETE")      # 이 변경 전에 만들어진 DB 의 모양(저널 delete)으로 되돌려 둔다
    before._conn.close()
    reader = _hold_read_lock(path)
    try:
        with caplog.at_level(logging.WARNING, logger="app.agent.conv_store"):
            store = ConversationStore(Settings(_env_file=None, conv_store_path=path, conv_store_busy_timeout_s=0.3))
    finally:
        reader.close()
    assert store._conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "시험 전제 — 쥔 연결 때문에 못 바꿨다"
    (line,) = [rec.getMessage() for rec in caplog.records if "WAL" in rec.getMessage()]
    assert "database is locked" in line and "다음 기동" in line
    store._conn.close()
    again = ConversationStore(Settings(_env_file=None, conv_store_path=path))
    assert again._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal", "쥔 연결이 없으면 다음 기동이 바꾼다"


def test_잠금에_걸린_쓰기가_연결을_열린_트랜잭션에_남기지_않는다(tmp_path):
    """저장소는 연결 하나를 계속 쓴다. 잠금 대기가 다 찬 INSERT 는 파이썬이 먼저 연 BEGIN 을 남기는데, 되돌리지 않으면 그 연결의
    다음 읽기가 그 트랜잭션 안에서 스냅샷을 쥔다. WAL 에서는 그 뒤 다른 연결이 한 번이라도 커밋하면 스냅샷이 낡아, 이 연결의
    쓰기는 **기다리지도 않고** 'database is locked' 로 실패하고 읽기는 옛 내용만 본다 — 포털을 다시 띄울 때까지(사본 재현)."""
    store, path = _store(tmp_path, conv_store_busy_timeout_s=0.3)
    cid = store.create(owner_sub="u1", title="t", kind="deliberation")
    other = sqlite3.connect(path, isolation_level=None, timeout=5)      # 다른 프로세스의 쓰기 — 쥐고 있다가 커밋한다
    other.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="잠긴 동안")
        assert store._conn.in_transaction is False, "실패한 쓰기가 연 트랜잭션이 그대로 남았다"
        assert [c["id"] for c in store.list_for_owner("u1")] == [cid]    # 그 사이의 읽기 — 남은 트랜잭션이면 여기서 스냅샷이 박힌다
        other.execute("INSERT INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) "
                      "VALUES ('other', 'u1', '다른 연결', 'chat', 'web', 1, 1)")
        other.execute("COMMIT")
    finally:
        other.close()
    t0 = time.monotonic()
    assert store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="풀린 뒤") is True
    assert time.monotonic() - t0 < 2.0
    assert {c["id"] for c in store.list_for_owner("u1")} == {cid, "other"}, "읽기가 옛 스냅샷에 갇혔다"
    assert [m["content"] for m in store.get(cid, "u1")["messages"]] == ["풀린 뒤"], "실패한 쓰기는 뒤늦게 들어가지 않는다"


def test_끝난_심의의_저장이_실패하면_로그가_사유와_손잡이를_말한다(caplog):
    """스트림은 정상으로 끝나고(화면은 다 받았다) 서버 사본만 빠진다 — 그 사실이 로그 한 줄로 남아야 한다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    class _Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield ('event: delib\ndata: {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}\n\n'
                   'event: delib\ndata: {"kind": "decision", "text": "결정문"}\n\nevent: done\ndata: {}\n\n').encode()

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:deliberation"])
    try:
        with TestClient(app) as c:
            real_client, store = app.state.agent_client, app.state.conv_store
            real_append = store.append
            cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]

            def locked_at_the_end(**kw):
                if kw["role"] == "user":            # 시작할 때의 사용자 발화는 저장된다 — 잠기는 것은 끝이다
                    return real_append(**kw)
                raise sqlite3.OperationalError("database is locked")

            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, stream=_Body(), headers={"content-type": "text/event-stream"})))
            store.append = locked_at_the_end
            try:
                with caplog.at_level(logging.WARNING, logger="app.agent.routes"):
                    r = c.post("/agent/chat", json={"message": "/심의 x", "conversation_id": cid})
            finally:
                app.state.agent_client = real_client
                del store.append
            saved = c.get(f"/agent/conversations/{cid}").json()["messages"]
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert r.status_code == 200 and "결정문" in r.text, "화면으로 간 스트림은 저장 실패와 무관하게 온전하다"
    assert [m["role"] for m in saved] == ["user"], "시험 전제 — 끝의 저장이 실제로 실패했다"
    (line,) = [rec.getMessage() for rec in caplog.records if "대화 저장 실패" in rec.getMessage()]
    assert "database is locked" in line and "CONV_STORE_BUSY_TIMEOUT_S" in line and cid in line


# ── 저장은 이벤트 루프 밖에서 한다 — 포털은 uvicorn 프로세스 하나, 이벤트 루프 하나다 ─────────────────────────────
# 저장소는 동기 sqlite3 다. async 핸들러가 그대로 부르면 잠금을 기다리는 동안(최대 CONV_STORE_BUSY_TIMEOUT_S 30초) 루프가 통째로
# 멈춘다 — 로그인, 다른 사람의 릴레이와 그 ping, 게이트웨이·리스크 앱이 포털에 거는 3~8초짜리 조회까지. 잠금 대기를 5초에서
# 30초로 늘리면서 그 최악이 30초가 됐다. 아래는 저장소 자리를 대역으로 바꾸지 않고, 다른 연결이 실제로 쥔 잠금으로 본다.
class _Deliberation(httpx.AsyncByteStream):
    """발언 하나와 결정문으로 끝나는 심의 스트림. hang 이 있으면 발언을 낸 뒤 그만큼 조용하다(끝나지 않은 심의)."""

    def __init__(self, hang: float = 0.0) -> None:
        self.hang = hang

    async def __aiter__(self):
        yield 'event: delib\ndata: {"kind": "turn", "round": 1, "persona": "mech-a", "say": "초기 입장"}\n\n'.encode()
        if self.hang:
            await asyncio.sleep(self.hang)
        yield 'event: delib\ndata: {"kind": "decision", "text": "결정문"}\n\nevent: done\ndata: {}\n\n'.encode()


@pytest.fixture()
def portal():
    """u1 로 들어온 포털 → (TestClient, app, 대화 DB 경로). 에이전트 서버 자리(app.state.agent_client)는 시험이 바꿔 끼우고 여기서 되돌린다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.config import get_settings
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:deliberation"])
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            real_client = app.state.agent_client
            try:
                yield c, app, get_settings().resolve(get_settings().conv_store_path)
            finally:
                app.state.agent_client = real_client
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def _agent(app, stream, on_call=lambda: None) -> None:
    def upstream(req):
        on_call()
        return httpx.Response(200, stream=stream, headers={"content-type": "text/event-stream"})
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))


def _roles(c, cid: str) -> list[str]:
    return [m["role"] for m in c.get(f"/agent/conversations/{cid}").json()["messages"]]


def test_잠긴_저장소를_기다리는_동안_다른_요청은_답한다(portal):
    """**이 시험이 이 구획의 이유다.** 끝난 심의의 저장이 3초짜리 잠금을 기다리는 사이에 무관한 GET /health 가 곧바로 답한다.
    고치기 전에는 그 요청이 잠금이 풀릴 때까지(2.8초) 같이 멈췄다."""
    c, app, path = portal
    cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]
    locks: list = []
    # 에이전트 서버가 불리는 때는 사용자 발화가 저장된 뒤다 — 여기서 잠그면 걸리는 것은 끝의 저장이다
    _agent(app, _Deliberation(), on_call=lambda: locks.append(_hold_write_lock(path, 3.0)))
    with ThreadPoolExecutor(1) as pool:
        relay = pool.submit(c.post, "/agent/chat", json={"message": "/심의 x", "conversation_id": cid})
        for _ in range(500):
            if locks:
                break
            time.sleep(0.01)
        assert locks, "시험 전제 — 릴레이가 에이전트 서버를 부르지 않았다"
        time.sleep(0.3)                             # 릴레이가 스트림을 다 읽고 끝의 저장에서 잠금을 기다리는 중이다
        t0 = time.monotonic()
        health = c.get("/health").status_code
        took = time.monotonic() - t0
        r = relay.result(timeout=60)
    locks[0][0].join()
    assert health == 200 and took < 1.0, f"대화 저장소의 잠금 대기가 이벤트 루프를 멈췄다 — 무관한 GET /health 가 {took:.2f}초 걸렸다"
    assert r.status_code == 200 and "결정문" in r.text
    assert _roles(c, cid) == ["user", "persona", "assistant"], "잠금이 풀린 뒤 끝의 저장이 끝까지 됐다"


def _health_while(c, start) -> tuple[float, httpx.Response]:
    """start 를 다른 스레드에서 걸어 놓고 0.3초 뒤 무관한 GET /health 가 얼마 만에 답하는지 → (걸린 초, start 의 응답)."""
    with ThreadPoolExecutor(1) as pool:
        job = pool.submit(start)
        time.sleep(0.3)
        t0 = time.monotonic()
        assert c.get("/health").status_code == 200
        took = time.monotonic() - t0
        return took, job.result(timeout=60)


@pytest.mark.parametrize("what", ["대화 생성", "챗의 사용자 발화"])
def test_요청_길의_쓰기가_잠금을_기다려도_다른_요청은_답한다(portal, what):
    """끝의 저장만이 아니다 — 같은 잠금 대기가 요청 길에도 걸린다. 리스크 앱이 패널 전에 거는 대화 생성과, 챗을 시작할 때의
    사용자 발화 저장이다. 하나라도 루프에 남으면 그 요청 하나가 포털 전체를 세운다."""
    c, app, path = portal
    cid = c.post("/agent/conversations", json={"title": "t"}).json()["id"]
    _agent(app, _Deliberation())
    start = {"대화 생성": lambda: c.post("/agent/conversations", json={"title": "리스크 패널", "kind": "risk-review"}),
             "챗의 사용자 발화": lambda: c.post("/agent/chat", json={"message": "안녕", "conversation_id": cid})}[what]
    t, _release = _hold_write_lock(path, 2.0)
    took, r = _health_while(c, start)
    t.join()
    assert took < 1.0, f"{what} — 잠금을 기다리는 동안 이벤트 루프가 멈췄다. 무관한 GET /health 가 {took:.2f}초 걸렸다"
    assert r.status_code == 200, "잠금이 풀린 뒤 그 요청은 끝까지 됐다"


def test_검색의_색인_통계가_저장소의_Lock_을_기다려도_다른_요청은_답한다(portal, monkeypatch):
    """스레드가 sqlite 잠금을 기다리는 동안에는 저장소의 Lock 도 쥐고 있다 — 루프에서 부른 **읽기** 하나가 그 Lock 에서 같이
    멈춘다. 검색 응답에 싣는 색인 통계 둘이 루프에 남아 있던 자리다(색인·순위는 이미 스레드였다). 임베더는 대역이고,
    Lock 은 순위가 끝난 직후(통계를 읽기 직전)에 다른 스레드가 2초 쥔다."""
    from app.agent import conv_search

    c, app, _path = portal
    lock = app.state.conv_store._lock

    async def reindex(*_a, **_k):
        return {"indexed": 0, "messages": 0, "too_short": 0}

    async def search(*_a, **_k):
        lock.acquire()
        threading.Timer(2.0, lock.release).start()
        return []

    monkeypatch.setattr(conv_search, "reindex", reindex)
    monkeypatch.setattr(conv_search, "search", search)
    took, r = _health_while(c, lambda: c.post("/agent/conversations/search", json={"query": "배터리 스웰링 판단"}))
    assert took < 1.0, f"검색이 저장소의 Lock 을 기다리는 동안 이벤트 루프가 멈췄다 — 무관한 GET /health 가 {took:.2f}초 걸렸다"
    assert r.status_code == 200 and {"messages", "indexed", "not_indexed_yet"} <= set(r.json()["index"]), r.text


def test_브라우저가_도중에_끊겨도_받은_발언은_저장된다(portal):
    """끝의 저장을 스레드로 넘기면 await 가 생긴다. 브라우저가 스트림 도중에 떠나면 Starlette 가 그 태스크를 취소하는데(uvicorn 의
    ASGI spec 2.3 갈래), 취소된 채로 만난 await 는 곧바로 CancelledError 다 — 가리지(shield) 않으면 저장이 통째로 건너뛰어진다.
    긴 심의일수록 사람은 창을 닫고 떠난다. uvicorn 과 같은 scope 로 앱을 직접 불러 첫 프레임 뒤에 끊는다."""
    c, app, _path = portal
    cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]
    _agent(app, _Deliberation(hang=30))             # 발언 하나를 낸 뒤 계속 도는 심의 — 그 사이에 끊긴다

    async def run():
        gone, first = asyncio.Event(), [True]
        body = json.dumps({"message": "/심의 x", "conversation_id": cid}).encode()

        async def receive():
            if first[0]:
                first[0] = False
                return {"type": "http.request", "body": body, "more_body": False}
            await gone.wait()
            return {"type": "http.disconnect"}

        async def send(msg):
            if msg["type"] == "http.response.body" and msg.get("body"):
                gone.set()                          # 첫 프레임을 받은 직후 브라우저가 떠난다

        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1", "method": "POST",
                 "scheme": "http", "path": "/agent/chat", "raw_path": b"/agent/chat", "query_string": b"", "root_path": "",
                 "client": ("127.0.0.1", 1), "server": ("testserver", 80), "app": app, "state": {},
                 "headers": [(b"host", b"testserver"), (b"content-type", b"application/json"),
                             (b"content-length", str(len(body)).encode())]}
        await asyncio.wait_for(app(scope, receive, send), 20)

    c.portal.call(run)
    assert _roles(c, cid) == ["user", "persona"], "끊기기 전에 받은 발언이 서버 대화에 없다"


def test_잠금_대기가_다_찬_대화_쓰기는_503_으로_손잡이를_말한다(portal):
    """리스크 앱은 패널을 돌리기 전에 포털에 대화를 만든다(POST /agent/conversations). 잠금 대기가 다 차면 종전에는 사유 없는
    HTTP 500 이라 그쪽 로그에 '대화 생성 거부: HTTP 500' 만 남았다 — 무엇을 기다리다 포기했는지, 어느 손잡이인지 말한다."""
    from app.config import get_settings

    c, app, path = portal
    conn = app.state.conv_store._conn
    cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]
    conn.execute("PRAGMA busy_timeout=300")         # 떠 있는 저장소의 대기만 줄인다(기본 30초를 그대로 기다리지 않게)
    t, release = _hold_write_lock(path, 30.0)
    try:
        made = c.post("/agent/conversations", json={"title": "리스크 패널", "kind": "risk-review"})
        added = c.post(f"/agent/conversations/{cid}/messages", json={"role": "assistant", "content": "발언"})
    finally:
        release.set()
        t.join()
        conn.execute(f"PRAGMA busy_timeout={int(get_settings().conv_store_busy_timeout_s * 1000)}")
    for r in (made, added):
        assert r.status_code == 503, (r.status_code, r.text)
        assert "CONV_STORE_BUSY_TIMEOUT_S" in r.json()["detail"] and "database is locked" in r.json()["detail"]
    assert _roles(c, cid) == [], "실패한 쓰기는 뒤늦게 들어가지 않는다"
    assert c.post("/agent/conversations", json={"title": "풀린 뒤"}).status_code == 200
