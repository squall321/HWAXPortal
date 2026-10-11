# 대화 검색의 게으른 색인이 시간 예산 안에서 멈추고, 끝낸 메시지의 벡터를 묶음마다 남기며, 남은 분량을 알리는지
"""웹 심의의 서버 사본은 좌석 발언을 버블(수백 자) 대신 줄이지 않은 글(say_full, 수천 자)로, 건수 상한 없이 남긴다(ae47e82).
search_conversations 는 검색할 때 미색인 메시지를 최대 2,000건까지 900자 조각으로 나눠 AIDataHub 임베더에 64개씩 보낸다.
종전 색인에는 시간 예산이 없었고 벡터는 끝에 한 번에 썼다. 게이트웨이는 120초를 기다린다 — 큰 심의 뒤 첫 검색이 그보다 길면
CONV_UNAVAILABLE 이 되고, 핸들러는 계속 도는데 벡터를 쓰기 전에 다음 검색이 같은 미색인분을 다시 보낸다(검토 P-8).

입력은 저장소의 실제 함수(ConversationStore.append)로 만든다. 임베더는 부른 횟수만큼 시계를 앞으로 미는 대역이다 — 실 임베더는
부르지 않는다.
"""
import asyncio

import pytest

from app.agent import conv_search as cs
from app.agent.conv_store import ConversationStore
from app.config import Settings


def _store(tmp_path) -> ConversationStore:
    return ConversationStore(Settings(_env_file=None, conv_store_path=str(tmp_path / "conv.sqlite")))


def _big_deliberation(store: ConversationStore, seats: int = 20, rounds: int = 8, chars: int = 4_000) -> str:
    """20석 × 8라운드 심의 한 번 — 좌석 발언은 줄이지 않은 글(say_full)이라 한 건이 수천 자다."""
    cid = store.create(owner_sub="u1", title="큰 심의", kind="deliberation")
    for r in range(1, rounds + 1):
        for s in range(seats):
            body = f"[seat-{s} R{r}] " + ("힌지 브래킷 두께 0.6 mm 에서 낙하 응력이 항복을 넘는다는 해석 근거. " * 200)[:chars]
            store.append(conversation_id=cid, owner_sub="u1", role="persona", content=body, persona=f"seat-{s}", round=r)
    store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="결정문 " * 50)
    return cid


@pytest.fixture()
def slow_embedder(monkeypatch):
    """한 번 부를 때마다 시계를 per_call 초 민다. fail_at 번째 호출에서 임베더가 실패한다."""
    state = {"now": 0.0, "calls": 0, "per_call": 10.0, "fail_at": None}

    async def fake_embed(texts, base_url, kind="passage", timeout=60.0):
        state["calls"] += 1
        if state["fail_at"] is not None and state["calls"] >= state["fail_at"]:
            raise ValueError("임베더가 응답하지 않았다")
        state["now"] += state["per_call"]
        return [[1.0] + [0.0] * (cs.DIM - 1) for _ in texts]

    monkeypatch.setattr(cs, "embed", fake_embed)
    monkeypatch.setattr(cs, "_clock", lambda: state["now"])
    return state


def test_큰_심의_뒤_첫_색인은_시간_예산_안에서_멈추고_남은_수를_알린다(tmp_path, slow_embedder):
    """**이 파일의 이유다** — 160건 × 4,000자는 조각 800여 개, 64개씩 13번 이상 부른다. 한 번에 10초면 130초로 게이트웨이 120초를
    넘는다. 예산(게이트웨이 한도의 절반)에서 멈추고, 끝낸 메시지는 남기고, 나머지는 다음 검색이 잇는다."""
    store = _store(tmp_path)
    _big_deliberation(store)
    total = store.remaining("u1", cs.MODEL)
    out = asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))
    elapsed = slow_embedder["now"]
    assert out["budget_hit"] is True
    assert elapsed <= cs.REINDEX_BUDGET_S + 2 * slow_embedder["per_call"], f"{elapsed}초 — 예산을 넘어 계속 불렀다"
    assert cs.REINDEX_BUDGET_S < 120, "게이트웨이(120초)보다 짧아야 핸들러가 끝난 뒤에 게이트웨이가 포기하지 않는다"
    left = store.remaining("u1", cs.MODEL)
    assert 0 < left < total, (left, total)
    # 다음 검색이 잇는다 — 이미 쓴 메시지를 다시 보내지 않는다.
    slow_embedder["now"] = 0.0
    calls_before = slow_embedder["calls"]
    asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))
    assert store.remaining("u1", cs.MODEL) < left
    assert slow_embedder["calls"] > calls_before


def test_색인한_메시지는_조각을_전부_가진다(tmp_path, slow_embedder):
    """예산에서 멈춰도 메시지 하나의 조각은 다 쓰거나 하나도 쓰지 않는다 — 반쪽만 쓰면 '색인됨' 으로 분류돼 뒤쪽 조각을 영영 못 찾는다."""
    store = _store(tmp_path)
    _big_deliberation(store)
    asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))
    by_msg: dict[str, set[int]] = {}
    for mid, cix, *_ in store.vectors_for("u1", cs.MODEL):
        by_msg.setdefault(mid, set()).add(cix)
    contents = dict(store._conn.execute("SELECT id, content FROM messages").fetchall())
    assert by_msg, "아무것도 색인하지 않았다"
    for mid, ixs in by_msg.items():
        assert ixs == set(range(len(cs.chunks(contents[mid])))), f"{mid} 의 조각이 빠졌다"


def test_임베더가_중간에_실패해도_앞서_끝낸_묶음은_남는다(tmp_path, slow_embedder):
    """종전엔 벡터를 끝에 한 번에 써서, 실패하면 그때까지 부른 임베딩이 전부 버려지고 다음 검색이 처음부터 다시 보냈다."""
    store = _store(tmp_path)
    _big_deliberation(store)
    total = store.remaining("u1", cs.MODEL)
    slow_embedder["fail_at"] = 4
    with pytest.raises(ValueError):
        asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))
    assert store.remaining("u1", cs.MODEL) < total, "앞서 끝낸 묶음의 벡터가 남지 않았다"


def test_작은_색인은_종전대로_한_번에_끝난다(tmp_path, slow_embedder):
    store = _store(tmp_path)
    cid = store.create(owner_sub="u1", title="t", kind="chat")
    store.append(conversation_id=cid, owner_sub="u1", role="user", content="배터리 스웰링 원인을 가스 발생 쪽에서 다시 보자. " * 3)
    store.append(conversation_id=cid, owner_sub="u1", role="assistant", content="네")
    out = asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))
    assert out["budget_hit"] is False and out["too_short"] == 1
    assert store.remaining("u1", cs.MODEL) == 0


def test_검색_응답이_예산에서_멈춘_색인을_알린다(slow_embedder):
    """멈춘 사실과 남은 수가 응답에 있어야 '못 찾은 것' 이 '없는 것' 으로 읽히지 않는다(not_indexed_yet·partial 은 종전부터 싣는다)."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u-reindex", email="u@hwax.local", display_name="U", groups=["feat:deliberation"])
    try:
        with TestClient(app) as c:
            store = app.state.conv_store
            cid = store.create(owner_sub="u-reindex", title="큰 심의", kind="deliberation")
            for s in range(160):
                store.append(conversation_id=cid, owner_sub="u-reindex", role="persona", persona=f"seat-{s % 20}",
                             round=1 + s // 20, content=("해석 근거 문장. " * 600)[:4_000])
            r = c.post("/agent/conversations/search", json={"query": "힌지 브래킷 낙하 응력 판단"})
        assert r.status_code == 200, r.text
        idx = r.json()["index"]
        assert idx["budget_hit"] is True and idx["partial"] is True and idx["not_indexed_yet"] > 0, idx
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


# ── RR2-PF-2 — 큰 메시지 하나 ────────────────────────────────────────────────────────────────
def _paste(store: ConversationStore) -> dict:
    """1M 창에서 문서를 통째로 붙여 넣은 챗 — 포털이 받는 메시지 한 칸의 상한(_WINDOW_CHARS) 하나와 짧은 메시지 하나."""
    from app.agent.routes import _WINDOW_CHARS

    cid = store.create(owner_sub="u1", title="문서 붙여넣기", kind="chat")
    store.append(conversation_id=cid, owner_sub="u1", role="user", content=("배터리 스웰링 가스 발생 판단 근거. " * 40)[:800])
    store.append(conversation_id=cid, owner_sub="u1", role="user",
                 content=("힌지 브래킷 낙하 해석 사양서 본문 문장. " * 200_000)[:_WINDOW_CHARS])
    return next(m for m in store.unindexed("u1", cs.MODEL) if len(m["content"]) == _WINDOW_CHARS)


def test_큰_메시지_하나도_예산을_넘겨_임베딩하지_않고_반쪽을_쓰지_않는다(tmp_path, slow_embedder):
    """**RR2-PF-2 의 이유다** — 예산을 메시지 사이에서만 보면, 예산 안에 집은 메시지 하나의 조각은 예산과 무관하게 다 임베딩한다.
    4,194,304자 메시지 하나는 5,592조각 · 임베딩 88번이다(한 번에 10초면 880초 — 게이트웨이 120초를 한참 넘기고, 핸들러가 끝에서야
    쓰는 사이 다음 검색이 같은 메시지를 처음부터 다시 보낸다 — P-8 의 이중 색인). 묶음마다 시계를 보고, 넘으면 쓰지 않은 묶음을 버린다."""
    store = _store(tmp_path)
    big = _paste(store)
    assert len(cs.chunks(big["content"])) > 5_000
    out = asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))
    per = slow_embedder["per_call"]
    assert slow_embedder["now"] <= cs.REINDEX_BUDGET_S + per, f"{slow_embedder['now']}초 — 예산을 넘어 계속 불렀다"
    assert slow_embedder["calls"] <= cs.REINDEX_BUDGET_S / per + 1, f"임베딩 {slow_embedder['calls']}번"
    assert out["budget_hit"] is True and out["deferred"] == 2, out
    assert big["message_id"] not in {mid for mid, *_ in store.vectors_for("u1", cs.MODEL)}, "반쪽을 썼다"
    assert store.remaining("u1", cs.MODEL) == 2


def test_예산_안에_끝낼_수_없는_메시지는_요청_밖에서_끝까지_색인하고_그동안_다시_보내지_않는다(tmp_path, slow_embedder):
    """묶음마다 멈추기만 하면 그 메시지는 영영 못 끝나고, 검색마다 앞 조각을 임베더에 다시 보낸다. 이번 요청이 예산 안에 임베딩한 조각
    수보다 조각이 많은 메시지는 요청 밖에서 끝까지 색인한다 — 도는 동안 다음 검색은 그 메시지를 건너뛰고 그 수를 알린다."""
    store = _store(tmp_path)
    big = _paste(store)
    jobs = []
    out = asyncio.run(cs.reindex(store, "u1", "http://embed.invalid", spawn=lambda fn, *a: jobs.append((fn, a))))
    assert out["budget_hit"] is True and out["background"] == 1 and out["deferred"] == 1, out
    assert len(jobs) == 1
    slow_embedder["now"] = 0.0
    before = slow_embedder["calls"]
    again = asyncio.run(cs.reindex(store, "u1", "http://embed.invalid", spawn=lambda fn, *a: jobs.append((fn, a))))
    assert again["background"] == 1 and again["deferred"] == 0 and len(jobs) == 1, again
    assert slow_embedder["calls"] - before == 1, "요청 밖에서 도는 메시지를 다음 검색이 다시 보냈다"
    assert store.remaining("u1", cs.MODEL) == 1
    fn, a = jobs[0]
    asyncio.run(fn(*a))
    ixs = {cix for mid, cix, *_ in store.vectors_for("u1", cs.MODEL) if mid == big["message_id"]}
    assert ixs == set(range(len(cs.chunks(big["content"])))), "요청 밖 색인이 조각을 다 쓰지 않았다"
    assert store.remaining("u1", cs.MODEL) == 0
    assert asyncio.run(cs.reindex(store, "u1", "http://embed.invalid"))["background"] == 0, "끝난 뒤에도 도는 중으로 센다"


def test_요청_밖_색인이_실패해도_다음_검색이_다시_넘긴다(tmp_path, slow_embedder):
    store = _store(tmp_path)
    big = _paste(store)
    jobs = []
    asyncio.run(cs.reindex(store, "u1", "http://embed.invalid", spawn=lambda fn, *a: jobs.append((fn, a))))
    slow_embedder["fail_at"] = slow_embedder["calls"] + 3
    fn, a = jobs[0]
    asyncio.run(fn(*a))   # 요청 밖이라 올릴 곳이 없다 — 로그에 남기고 표식을 푼다
    slow_embedder["fail_at"], slow_embedder["now"] = None, 0.0
    out = asyncio.run(cs.reindex(store, "u1", "http://embed.invalid", spawn=lambda fn, *a: jobs.append((fn, a))))
    assert out["background"] == 1 and len(jobs) == 2, out
    fn, a = jobs[1]
    asyncio.run(fn(*a))   # 다시 넘긴 것은 끝까지 쓴다(그리고 이 시험이 표식을 남기지 않는다)
    ixs = {cix for mid, cix, *_ in store.vectors_for("u1", cs.MODEL) if mid == big["message_id"]}
    assert ixs == set(range(len(cs.chunks(big["content"])))) and not cs._OUTSIDE


def test_검색_응답이_요청_밖에서_색인하는_큰_메시지를_알린다(slow_embedder):
    """남은 수(not_indexed_yet)와 함께, 그중 몇 건이 요청 밖에서 색인 중인지와 그 뜻을 싣는다 — 다음 검색에서 찾힌다."""
    import time as _time

    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u-bg", email="u@hwax.local", display_name="U", groups=["feat:deliberation"])
    try:
        with TestClient(app) as c:
            store = app.state.conv_store
            cid = store.create(owner_sub="u-bg", title="문서 붙여넣기", kind="chat")
            store.append(conversation_id=cid, owner_sub="u-bg", role="user",
                         content=("힌지 브래킷 낙하 해석 사양서 본문 문장. " * 20_000)[:400_000])
            r = c.post("/agent/conversations/search", json={"query": "힌지 브래킷 낙하 응력 판단"})
            assert r.status_code == 200, r.text
            idx = r.json()["index"]
            # not_indexed_yet 은 여기서 단언하지 않는다 — 대역 임베더는 기다리지 않아, 요청 밖 색인이 응답을 만드는 사이에 끝나기도 한다.
            assert idx["in_background"] == 1 and idx["budget_hit"] is True, idx
            assert "요청 밖" in idx["background_note"] and "다음 검색" in idx["background_note"], idx
            end = _time.monotonic() + 30
            while store.remaining("u-bg", cs.MODEL) and _time.monotonic() < end:
                _time.sleep(0.05)
            assert store.remaining("u-bg", cs.MODEL) == 0, "요청 밖 색인이 끝나지 않았다"
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
