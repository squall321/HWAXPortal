# 서버 대화 저장소의 잠금 대기(CONV_STORE_BUSY_TIMEOUT_S)와, 끝난 심의의 저장이 실패했을 때 그 사실이 로그에 남는지
"""웹 심의는 스트림이 끝난 뒤(finally) 발언 최대 199건과 결정문을 서버 대화 저장소에 쓴다 — 다른 기기에서 열거나
서버 사본에서 이어갈 때 쓰는 유일한 서버 사본이다. 잠금 대기가 sqlite3 기본 5초였고, 저장이 실패해도 스트림이 이미
닫힌 뒤라 화면에도 로그에도 아무것도 안 남았다(백업 backup-local.sh 가 이 DB 를 연다).

잠금은 다른 연결이 실제로 쥔다 — PRAGMA 값만 읽으면 '설정은 됐는데 안 걸리는' 경우를 못 본다.
"""
import logging
import sqlite3
import threading
import time

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
