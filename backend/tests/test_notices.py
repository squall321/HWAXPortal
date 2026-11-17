# 포털 알림 원장 · API — 같은 원천은 한 줄 · 제 알림만 · 링크는 포털 안 경로만 · 쓰기는 세션 + CSRF(docs/request-1117 contracts §7)
"""고정하는 것.
  · (kind, source_id) 가 같으면 한 줄이다 — 다시 넣어도 아무것도 바뀌지 않는다(읽음 표시도 그대로).
  · 한 줄 · 길이 상한 · 포털 안 링크만(바깥 주소 · '//' 는 버린다).
  · 커서는 앞으로만 간다 — 두 일꾼이 다른 값을 써도 뒤로 가지 않는다.
  · API — 로그인해야 읽고, 늘 제 알림만(최신 것부터 · 안 읽은 수), 남의 id 는 404, 쓰기는 CSRF 가 없으면 403.
계정은 example.com 시험 신원만 쓴다 — 이 리포는 GitHub 에 있다.
"""
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.agent.audit import AuditLog
from app.auth.cookies import CSRF_COOKIE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.notices import store as NS
from app.notices.store import NoticeStore

PW = "pw123456"


def _settings(tmp_path, **kw) -> Settings:
    return Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), agent_audit_log_path=str(tmp_path / "audit.sqlite"),
                    token_store_path=str(tmp_path / "tokens.sqlite"), conv_store_path=str(tmp_path / "conv.sqlite"),
                    procedures_store_path=str(tmp_path / "procedures.sqlite"), conn_key_path=str(tmp_path / "conn.key"),
                    insight_sync_s=0, **kw)


@pytest.fixture()
def store(tmp_path):
    st = NoticeStore(_settings(tmp_path))
    yield st
    st.close()


def _add(st, who="me@example.com", src="batch-1", **kw):
    return st.add(user_email=who, kind=kw.pop("kind", "delib_batch"), title=kw.pop("title", "심의 묶음 끝남 — 가"),
                  line=kw.pop("line", "끝남 3."), source_id=src, **kw)


# ── 원장 ─────────────────────────────────────────────────────────────────────────────────────────
def test_같은_원천은_한_줄이고_다시_넣어도_읽음이_그대로다(store):
    nid = _add(store, created_at=100)
    assert nid and store.mark_read("me@example.com", nid)
    assert _add(store, title="다른 제목", created_at=200) is None, "같은 (kind, source_id) 는 다시 넣지 않는다"
    rows = store.list_for("me@example.com")
    assert len(rows) == 1 and rows[0]["title"] == "심의 묶음 끝남 — 가" and rows[0]["read_at"] is not None
    assert _add(store, kind="wda_deck") is not None, "kind 가 다르면 다른 원천이다"


def test_유일_색인이_원장에_있다(store):
    with closing(sqlite3.connect(store.path)) as c:
        idx = {r[1]: r for r in c.execute("PRAGMA index_list(notices)").fetchall()}
        assert idx["ux_notice_source"][2] == 1
        assert [r[2] for r in c.execute("PRAGMA index_info(ux_notice_source)").fetchall()] == ["kind", "source_id"]


def test_한_줄_길이_상한_포털_안_링크만(store):
    _add(store, src="a", title="제목\n둘째 줄", line="첫째\r\n둘째 셋째" + "가" * 900, link="/deliberate?x=1")
    r = store.find("delib_batch", "a")
    assert r["title"] == "제목 둘째 줄" and r["line"].startswith("첫째 둘째 셋째") and len(r["line"]) == NS.LINE_MAX
    assert r["link"] == "/deliberate?x=1"
    for i, bad in enumerate(["https://evil.example/x", "//evil.example/x", "/\\evil", "javascript:alert(1)", "deliberate", "/a\nb", ""]):
        _add(store, src=f"b{i}", link=bad)
        assert store.find("delib_batch", f"b{i}")["link"] is None, bad


def test_주인_kind_원천이_없으면_넣지_않는다(store):
    for kw in ({"who": "", "src": "x"}, {"who": "이메일아님", "src": "x"}, {"src": ""}, {"src": "x", "kind": ""}):
        with pytest.raises(ValueError):
            _add(store, **kw)


def test_제_알림만_최신_것부터_안_읽은_수(store):
    _add(store, src="old", created_at=100)
    _add(store, src="new", created_at=300)
    _add(store, src="mid", created_at=200)
    _add(store, who="peer@example.com", src="peer", created_at=400)
    assert [r["source_id"] for r in store.list_for("ME@example.com")] == ["new", "mid", "old"]
    assert [r["source_id"] for r in store.list_for("me@example.com", limit=2)] == ["new", "mid"]
    assert store.unread("me@example.com") == 3 and store.unread("peer@example.com") == 1
    peer_id = store.list_for("peer@example.com")[0]["id"]
    assert not store.mark_read("me@example.com", peer_id), "남의 알림은 읽음으로 바꾸지 못한다"
    assert store.unread("peer@example.com") == 1
    assert store.mark_all_read("me@example.com") == 3 and store.unread("me@example.com") == 0
    assert store.mark_all_read("me@example.com") == 0 and store.unread("peer@example.com") == 1


def test_처음_읽은_시각은_다시_읽어도_그대로다(store, monkeypatch):
    nid = _add(store)
    monkeypatch.setattr(NS, "_now", lambda: 1000)
    assert store.mark_read("me@example.com", nid)
    monkeypatch.setattr(NS, "_now", lambda: 2000)
    assert store.mark_read("me@example.com", nid), "이미 읽은 제 알림도 참이다(멱등)"
    assert store.list_for("me@example.com")[0]["read_at"] == 1000


def test_커서는_앞으로만_가고_다시_열어도_남는다(tmp_path):
    s = _settings(tmp_path)
    a, b = NoticeStore(s), NoticeStore(s)          # 같은 파일을 여는 두 일꾼
    try:
        assert a.cursor("k") == 0.0
        assert a.advance("k", 50.5) == 50.5
        assert b.advance("k", 20.0) == 50.5, "뒤 값은 앞선 커서를 되돌리지 않는다"
        assert b.advance("k", 70.25) == 70.25 and a.cursor("k") == 70.25
    finally:
        a.close()
        b.close()
    again = NoticeStore(s)
    try:
        assert again.cursor("k") == 70.25
    finally:
        again.close()


def test_원장은_대화_저장소_파일_안의_표다(tmp_path):
    """새 파일을 레지스트리 · 백업 · 격리에 올리지 않으려고 대화 저장소 파일에 둔다(store.py 머리) — 경로가 갈라지면 그 등록이 모두 빠진다."""
    s = _settings(tmp_path)
    st = NoticeStore(s)
    try:
        assert st.path == tmp_path / "conv.sqlite"
    finally:
        st.close()


# ── API — 실제 로그인 두 사람 ───────────────────────────────────────────────────────────────────
def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = _settings(tmp_path, local_bootstrap_admins="boss@example.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.agent_audit, app.state.token_store, app.state.notice_store)
        app.state.user_store, app.state.agent_audit, app.state.token_store = UserStore(s), AuditLog(s), TokenStore(s)
        st = app.state.notice_store = NoticeStore(s)
        for email in ("me@example.com", "peer@example.com"):
            assert c.post("/auth/local/signup", json={"email": email, "name": email.split("@")[0], "password": PW}).status_code < 300
            assert app.state.user_store.approve(email, by="boss@example.com", groups=[])
        c.cookies.clear()
        yield c, st
        app.state.user_store, app.state.agent_audit, app.state.token_store, app.state.notice_store = keep
        st.close()
    app.dependency_overrides.pop(get_settings, None)


def test_API_는_로그인해야_읽고_제_알림만_최신_것부터(env):
    c, st = env
    assert c.get("/notices-api").status_code == 401
    _add(st, src="a", created_at=100, link="/deliberate")
    _add(st, src="b", created_at=200)
    _add(st, who="peer@example.com", src="p", created_at=300)
    _login(c, "me@example.com")
    r = c.get("/notices-api")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unread"] == 2 and [x["source_id"] for x in body["items"]] == ["b", "a"]
    assert set(body["items"][0]) == {"id", "kind", "title", "line", "link", "source_id", "created_at", "read_at"}
    assert body["items"][1]["link"] == "/deliberate"
    assert [x["source_id"] for x in c.get("/notices-api", params={"limit": 1}).json()["items"]] == ["b"]
    assert c.get("/notices-api", params={"limit": 0}).status_code == 422


def test_API_읽음은_CSRF_가_있어야_하고_남의_id_는_404(env):
    c, st = env
    mine = _add(st, src="a")
    _add(st, src="b")
    peer = _add(st, who="peer@example.com", src="p")
    h = _login(c, "me@example.com")
    assert c.post(f"/notices-api/{mine}/read").status_code == 403, "CSRF 머리가 없으면 거절"
    assert c.post("/notices-api/read-all").status_code == 403
    r = c.post(f"/notices-api/{mine}/read", headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True, "unread": 1}
    assert c.post(f"/notices-api/{peer}/read", headers=h).status_code == 404, "남의 알림은 없는 것과 같다"
    assert c.post("/notices-api/없는-id/read", headers=h).status_code == 404
    assert st.unread("peer@example.com") == 1
    r = c.post("/notices-api/read-all", headers=h)
    assert r.status_code == 200 and r.json() == {"marked": 1, "unread": 0}
    assert st.unread("peer@example.com") == 1, "모두 읽음도 제 알림만"


def test_API_원장이_없으면_503(env):
    c, st = env
    _login(c, "me@example.com")
    keep, app.state.notice_store = app.state.notice_store, None
    try:
        assert c.get("/notices-api").status_code == 503
    finally:
        app.state.notice_store = keep
