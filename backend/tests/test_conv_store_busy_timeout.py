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
