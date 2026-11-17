# 심의 묶음 끝남 알림 당기기 — 가짜 엔진(끝난 묶음 창구와 같은 꼴)으로 한 번만 · 계정 아닌 주인 건너뜀 · 재기동 · 두 일꾼 · 실패 까닭을 본다(contracts §7)
"""가짜 엔진은 HWAXAgentServer `POST /deliberate/batch/finished`(app.py · delib_batch.finished_since)를 그대로 흉내 낸다.
  · 공유 비밀만 — 없거나 다르면 401, 비밀 + x-hwax-user 머리면 403 service_only, 비밀이 없는 박스는 503.
  · 본문 {since ≥ 0, limit 1~500(기본 100)}, 모르는 칸 · 꼴이 틀린 값은 422.
  · finished_at ≥ since 를 (finished_at, batch_id) 차례로 limit 개 — next_since 는 마지막 묶음의 finished_at(없으면 since)이라 **경계의 묶음이 다음 부름에
    다시 나온다.** 도는 묶음은 나오지 않는다(가짜는 끝난 것만 쥔다).
고정하는 것 — 묶음마다 알림 하나(경계 반복 · 재기동 · 두 일꾼에도), 주인이 포털 계정이 아니면 안 남김, 커서는 원장에 남고 앞으로만, 실패는 까닭과 함께
돌려주고 커서를 옮기지 않음, 비밀은 머리에만 싣고 로그에 적지 않음, 손잡이 0 이면 띄우지 않음. 계정은 example.com 시험 신원만.
"""
import asyncio
import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.user_store import UserStore
from app.config import Settings
from app.main import app
from app.notices import poller as P
from app.notices.store import NoticeStore

SECRET = "gw-secret-for-tests-only"


class FakeEngine:
    """끝난 묶음 창구 — 엔진과 같은 인증 · 검증 · 차례 · 경계 규칙."""

    def __init__(self, batches=(), *, has_secret=True):
        self.batches, self.has_secret, self.calls = list(batches), has_secret, []

    def handler(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        if req.method != "POST" or req.url.path != P.PATH:
            return httpx.Response(404, json={"detail": "Not Found"})
        if not self.has_secret:
            return httpx.Response(503, json={"error": "공유 비밀이 없다"})
        if req.headers.get("authorization", "") != f"Bearer {SECRET}":
            return httpx.Response(401, json={"error": "unauthorized"})
        if req.headers.get("x-hwax-user", "").strip():
            return httpx.Response(403, json={"code": "service_only", "message": "끝난 묶음 창구는 포털 서비스만 부른다"})
        try:
            body = json.loads(req.content or b"{}")
        except ValueError:
            return httpx.Response(422, json={"code": "bad_request"})
        if not isinstance(body, dict) or set(body) - {"since", "limit"}:
            return httpx.Response(422, json={"code": "unknown_fields"})
        since, limit = body.get("since"), body.get("limit", 100)
        if isinstance(since, bool) or not isinstance(since, (int, float)) or not since >= 0:
            return httpx.Response(422, json={"code": "bad_request"})
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            return httpx.Response(422, json={"code": "bad_request"})
        rows = sorted((b for b in self.batches if b["finished_at"] >= since), key=lambda b: (b["finished_at"], b["batch_id"]))[:limit]
        return httpx.Response(200, json={"batches": rows, "next_since": rows[-1]["finished_at"] if rows else float(since)})

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=5)


def batch(n: int, at: float, owner="me@example.com", status="done", **kw) -> dict:
    return {"batch_id": f"batch-20261117-1200{n:02d}-{n:06x}", "owner": owner, "name": kw.pop("name", f"묶음 {n}"), "status": status,
            "finished_at": float(at), "counts": {"done": 2, "failed": 0, "stopped": 0, "skipped": 1, "not_trustworthy": 0},
            "notice": kw.pop("notice", f"묶음 「묶음 {n}」 이 끝났다(모두 끝남) — 끝남 2 · 건너뜀 1 · 실패 0 · 접힘 0 · 멈춤 0."), **kw}


@pytest.fixture()
def box(tmp_path):
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), conv_store_path=str(tmp_path / "conv.sqlite"),
                 conn_key_path=str(tmp_path / "conn.key"), gateway_shared_token=SECRET, agent_server_url="http://agent.test",
                 delib_batch_notice_s=60)
    users = UserStore(s)
    for email in ("me@example.com", "peer@example.com"):
        users.note_sso_login(email=email, name=email.split("@")[0])     # SSO 로 들어온 사람 — 원장에 행이 생긴다
    store = NoticeStore(s)
    yield SimpleNamespace(state=SimpleNamespace(notice_store=store, user_store=users)), s, store
    store.close()


def _tick(app_, s, eng, **kw):
    async def go():
        async with eng.client() as cli:
            return await P.tick(app_, s, client=cli, **kw)
    return asyncio.run(go())


def _counts(out: dict) -> tuple:
    return tuple(out[k] for k in ("written", "already", "no_account", "bad"))


# ── 정상 길 ──────────────────────────────────────────────────────────────────────────────────────
def test_묶음마다_주인에게_알림_하나_경계가_다시_나와도_한_번(box):
    app_, s, store = box
    eng = FakeEngine([batch(1, 100.5), batch(2, 200.25, owner="peer@example.com", status="stopped")])
    out = _tick(app_, s, eng)
    assert "error" not in out and _counts(out) == (2, 0, 0, 0) and out["since"] == 200.25
    req = eng.calls[0]
    assert json.loads(req.content) == {"since": 0.0, "limit": P.PAGE_LIMIT}
    assert req.headers["authorization"] == f"Bearer {SECRET}" and "x-hwax-user" not in req.headers, "신원 머리를 실으면 엔진이 403 이다"
    n1 = store.find(P.KIND, batch(1, 0)["batch_id"])
    assert (n1["user_email"], n1["title"], n1["link"], n1["created_at"], n1["read_at"]) == (
        "me@example.com", "심의 묶음 끝남 — 묶음 1", None, 100, None)
    assert n1["line"] == batch(1, 0)["notice"]
    assert store.find(P.KIND, batch(2, 0)["batch_id"])["title"] == "심의 묶음 멈춤 — 묶음 2"
    # 다음 틱 — 엔진은 since=200.25 에서 경계의 묶음 2 를 다시 낸다. 알림은 늘지 않는다.
    out = _tick(app_, s, eng)
    assert json.loads(eng.calls[-1].content)["since"] == 200.25
    assert _counts(out) == (0, 1, 0, 0) and store.unread("peer@example.com") == 1 and store.unread("me@example.com") == 1
    # 새로 끝난 묶음만 새 알림이다
    eng.batches.append(batch(3, 300.0, status="failed"))
    out = _tick(app_, s, eng)
    assert _counts(out) == (1, 1, 0, 0) and store.find(P.KIND, batch(3, 0)["batch_id"])["title"] == "심의 묶음 실패 — 묶음 3"


def test_주인이_포털_계정이_아니면_남기지_않고_대소문자_퍼센트는_푼다(box):
    app_, s, store = box
    eng = FakeEngine([batch(1, 10, owner="ghost@example.com"), batch(2, 20, owner="ME%40example.com"), batch(3, 30, owner=""),
                      {"batch_id": "", "owner": "me@example.com", "status": "done", "finished_at": 40.0},
                      {"batch_id": "batch-x", "owner": "me@example.com", "status": "running", "finished_at": 50.0}])
    out = _tick(app_, s, eng)
    assert _counts(out) == (1, 0, 2, 2)
    assert store.find(P.KIND, batch(1, 0)["batch_id"]) is None, "포털 계정이 아닌 주인에게는 남기지 않는다"
    assert store.find(P.KIND, batch(2, 0)["batch_id"])["user_email"] == "me@example.com"
    assert out["since"] == 50.0, "꼴이 다른 줄도 커서는 넘긴다(다시 읽어도 같은 줄이다)"


def test_알림_글이_비면_셈으로_한_줄을_짓는다():
    f = P.notice_of({**batch(1, 10), "notice": "", "name": ""})
    assert f["line"] == "끝남 2 · 건너뜀 1 · 실패 0 · 멈춤 0." and f["title"].endswith(batch(1, 0)["batch_id"])


def test_쪽을_넘기며_다_읽고_재기동해도_커서부터_잇는다(box, monkeypatch):
    app_, s, store = box
    monkeypatch.setattr(P, "PAGE_LIMIT", 3)
    eng = FakeEngine([batch(i, 10 * i) for i in range(1, 6)])
    out = _tick(app_, s, eng)
    assert _counts(out) == (5, 2, 0, 0) and out["pages"] == 3 and out["since"] == 50.0, "경계의 묶음(30 · 50)은 다시 와도 이미 있다"
    assert [json.loads(r.content)["since"] for r in eng.calls] == [0.0, 30.0, 50.0], "경계(30 · 50)부터 다음 쪽을 묻는다"
    store.close()
    again = NoticeStore(s)                                     # 재기동 — 같은 파일을 다시 연다
    app_.state.notice_store = again
    assert again.cursor(P.CURSOR) == 50.0
    out = _tick(app_, s, eng)
    assert json.loads(eng.calls[-1].content)["since"] == 50.0 and _counts(out) == (0, 1, 0, 0)
    assert again.unread("me@example.com") == 5


def test_한_틱의_쪽_수에는_상한이_있고_남은_것은_다음_틱이_잇는다(box, monkeypatch):
    app_, s, store = box
    monkeypatch.setattr(P, "PAGE_LIMIT", 2)
    monkeypatch.setattr(P, "PAGES_MAX", 2)
    eng = FakeEngine([batch(i, 10 * i) for i in range(1, 6)])
    out = _tick(app_, s, eng)                                # since 0 → 10 · 20, since 20 → 20(경계) · 30 — 쪽 상한
    assert "error" not in out and out["pages"] == 2 and out["since"] == 30.0 and _counts(out)[0] == 3
    out = _tick(app_, s, eng)                                # since 30 → 30 · 40, since 40 → 40 · 50
    assert out["since"] == 50.0 and store.unread("me@example.com") == 5
    out = _tick(app_, s, eng)                                # since 50 → 50(경계) 하나 — 덜 찬 쪽이라 끝
    assert out["pages"] == 1 and _counts(out) == (0, 1, 0, 0)


def test_두_일꾼이_같은_쪽을_함께_읽어도_묶음마다_하나(box):
    app_, s, store = box
    other = NoticeStore(s)                                     # 같은 파일을 여는 다른 일꾼
    app_b = SimpleNamespace(state=SimpleNamespace(notice_store=other, user_store=app_.state.user_store))
    eng = FakeEngine([batch(i, 10 * i) for i in range(1, 8)])

    async def both():
        async with eng.client() as a, eng.client() as b:
            return await asyncio.gather(P.tick(app_, s, client=a), P.tick(app_b, s, client=b))
    try:
        ra, rb = asyncio.run(both())
        assert ra["written"] + rb["written"] == 7 and ra["written"] + ra["already"] == 7
        assert store.unread("me@example.com") == 7 and len(store.list_for("me@example.com")) == 7
        assert other.cursor(P.CURSOR) == 70.0
    finally:
        other.close()


def test_꽉_찬_쪽이_모두_같은_시각이면_돌지_않고_까닭을_남긴다(box, monkeypatch):
    app_, s, store = box
    monkeypatch.setattr(P, "PAGE_LIMIT", 2)
    eng = FakeEngine([batch(1, 10), batch(2, 10), batch(3, 10)])
    out = _tick(app_, s, eng)
    assert "커서가 넘어가지 못한다" in out["error"] and len(eng.calls) == 2 and _counts(out)[0] == 2


# ── 실패 — 까닭을 돌려주고 커서를 옮기지 않는다 ──────────────────────────────────────────────────────
@pytest.mark.parametrize(("make", "tok", "why"), [
    (lambda: FakeEngine([batch(1, 10)]), "wrong-secret", "HTTP 401"),
    (lambda: FakeEngine([batch(1, 10)], has_secret=False), SECRET, "HTTP 503"),
])
def test_엔진이_거절하면_까닭만(box, make, tok, why):
    app_, s, store = box
    s = s.model_copy(update={"gateway_shared_token": tok})
    out = _tick(app_, s, make())
    assert why in out["error"] and out["since"] == 0.0 and store.cursor(P.CURSOR) == 0.0 and store.unread("me@example.com") == 0
    assert tok not in out["error"], "비밀을 까닭에 싣지 않는다"


def test_신원_머리를_실으면_엔진이_403_이고_까닭이_남는다(box):
    """포털은 신원 머리를 싣지 않는다(위 시험) — 실은 호출이 엔진에서 어떻게 막히는지를 가짜가 같게 흉내 내는지 본다."""
    eng = FakeEngine([batch(1, 10)])
    r = eng.handler(httpx.Request("POST", f"http://agent.test{P.PATH}", json={"since": 0},
                                  headers={"Authorization": f"Bearer {SECRET}", "x-hwax-user": "me@example.com"}))
    assert r.status_code == 403 and r.json()["code"] == "service_only"
    assert P._HTTP_WHY[403].startswith("에이전트 서버가 서비스 호출로 받지 않았다")


def test_낡은_엔진_불통_꼴이_다른_답(box):
    app_, s, store = box

    def old(req):
        return httpx.Response(404, json={"detail": "Not Found"})

    def down(req):
        raise httpx.ConnectError("refused", request=req)

    def odd(req):
        return httpx.Response(200, json={"items": []})

    for h, why in ((old, "HTTP 404"), (down, "닿지 못했다(ConnectError)"), (odd, "꼴이 다르다")):
        async def go(h=h):
            async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as cli:
                return await P.tick(app_, s, client=cli)
        out = asyncio.run(go())
        assert why in out["error"] and store.cursor(P.CURSOR) == 0.0, out


def test_비밀_원장_주소가_없으면_부르지_않는다(box):
    app_, s, store = box
    eng = FakeEngine([batch(1, 10)])
    assert "공유 비밀" in _tick(app_, s.model_copy(update={"gateway_shared_token": ""}), eng)["error"]
    assert "주소" in _tick(app_, s.model_copy(update={"agent_server_url": ""}), eng)["error"]
    assert "원장" in _tick(SimpleNamespace(state=SimpleNamespace(notice_store=None, user_store=None)), s, eng)["error"]
    assert eng.calls == []


# ── 백그라운드 작업 ──────────────────────────────────────────────────────────────────────────────
def test_작업은_실패를_한_번만_적고_다시_닿으면_알리며_비밀을_적지_않는다(box, monkeypatch, caplog):
    app_, s, store = box
    eng = FakeEngine([batch(1, 10)], has_secret=False)
    real = httpx.AsyncClient
    monkeypatch.setattr(P.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(eng.handler), **kw))

    async def go():
        task = asyncio.get_running_loop().create_task(P.run(app_, s, 0.005))
        while len(eng.calls) < 4:
            await asyncio.sleep(0.005)
        eng.has_secret = True                                  # 엔진에 비밀이 생겼다 — 다음 틱부터 닿는다
        while (getattr(app_.state, "notice_poll_last", None) or {}).get("written") != 1:   # 틱이 끝나 로그까지 적은 뒤
            await asyncio.sleep(0.005)
        await P.stop(task)
        return task
    with caplog.at_level(logging.INFO, logger=P.__name__):
        task = asyncio.run(go())
    assert task.cancelled()
    warns = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert sum("HTTP 503" in w for w in warns) == 1, warns
    assert any("다시 닿았다" in w for w in warns), warns
    assert all(SECRET not in r.getMessage() for r in caplog.records)
    assert store.unread("me@example.com") == 1


def test_손잡이가_0_이면_띄우지_않고_시험_포털도_띄우지_않는다(box):
    app_, s, store = box

    async def go(v):
        return P.start(app_, s.model_copy(update={"delib_batch_notice_s": v}))
    assert asyncio.run(go(0)) is None
    with TestClient(app):
        assert app.state.notice_poller is None, "conftest 가 DELIB_BATCH_NOTICE_S=0 — 시험이 떠 있는 에이전트 서버를 부르면 안 된다"


def test_기동이_띄운_작업은_내려갈_때_멈춘다(box):
    app_, s, store = box

    async def go():
        t = P.start(app_, s)
        assert t is not None and not t.done()
        await P.stop(t)
        return t
    assert asyncio.run(go()).cancelled()
