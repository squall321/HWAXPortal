# 대화 검색이 AIDataHub 의 임베딩 모델을 따라가는가 — 표지 · 다시 색인 · 모델별 하한(포털 docs/embedder-bge-m3)
"""왜 — 대화 검색은 AIDataHub /api/embed 를 빌려 쓴다. 표지를 상수(aidh-768)로 박아 두면 AIDataHub 가 BGE-M3(1024)로 바뀐 날 새 벡터를
옛 표지로 저장하거나 옛 벡터와 견준다. 하한(0.84 · 0.75)도 e5 의 코사인 분포로 잰 값이라 다른 모델에 그대로 걸면 맞는 것까지 버린다.

  · 응답에 model 이 없거나 e5-base(768)면 옛 표지 — 같은 공간을 다시 색인하지 않는다.
  · 다른 모델이면 새 표지 — 그 공간의 벡터와만 견주고, 없으면 새로 색인한다.
  · 재지 않은 모델은 점수로 거르지 않고 응답이 알린다.
"""
import asyncio

import httpx
import pytest

from app.agent import conv_search as cs
from app.agent.conv_store import ConversationStore
from app.config import Settings


@pytest.fixture(autouse=True)
def _reset_tag(monkeypatch):
    monkeypatch.setitem(cs._LAST, "tag", cs.MODEL)


def _store(tmp_path) -> ConversationStore:
    return ConversationStore(Settings(_env_file=None, conv_store_path=str(tmp_path / "conv.sqlite")))


def test_표지는_모델이_없거나_e5_base_면_옛_것이다():
    v768, v1024 = [[0.1] * 768], [[0.1] * 1024]
    assert cs.tag_of({}, v768) == cs.MODEL
    assert cs.tag_of({"model": "sentence-transformers-e5-base-d768", "dim": 768}, v768) == cs.MODEL
    assert cs.tag_of({"model": "BAAI/bge-m3", "dim": 1024}, v1024) == "aidh-BAAI_bge-m3-1024"
    assert cs.tag_of({"model": "x y/../z", "dim": "1024"}, v1024) == "aidh-x_y_.._z-1024", "표지 글자는 안전한 것만"
    assert cs.floors_for(cs.MODEL) == (cs._MIN_SCORE, cs._SHORT_FLOOR)
    assert cs.floors_for("aidh-BAAI_bge-m3-1024") is None


def test_embed_는_응답의_모델로_표지를_바꾼다(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"vectors": [[0.5] * 1024], "model": "BAAI/bge-m3", "dim": 1024})
    real = httpx.AsyncClient
    monkeypatch.setattr(cs.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    vecs = asyncio.run(cs.embed(["질의"], "http://aidh.invalid", "query"))
    assert len(vecs[0]) == 1024 and cs.current_tag() == "aidh-BAAI_bge-m3-1024"


def _fake_embed(monkeypatch, tag: str, dim: int, value: float = 1.0):
    async def fake(texts, base_url, kind="passage", timeout=60.0):
        cs._LAST["tag"] = tag                  # 실제 embed 처럼 응답이 정한 공간을 남긴다
        return [[value] + [0.0] * (dim - 1) for _ in texts]
    monkeypatch.setattr(cs, "embed", fake)


def test_모델이_바뀌면_새_표지로_다시_색인하고_그_공간과만_견준다(tmp_path, monkeypatch):
    store = _store(tmp_path)
    cid = store.create(owner_sub="u1", title="배터리", kind="chat")
    store.append(conversation_id=cid, owner_sub="u1", role="user", content="배터리 스웰링 원인을 셀 적층 압력과 함께 살펴본 대화 " * 3)
    _fake_embed(monkeypatch, cs.MODEL, 768)
    asyncio.run(cs.reindex(store, "u1", "http://aidh.invalid"))
    assert store.remaining("u1", cs.MODEL) == 0
    new = "aidh-BAAI_bge-m3-1024"
    _fake_embed(monkeypatch, new, 1024)
    hits = asyncio.run(cs.search(store, "u1", "배터리 스웰링 원인을 찾던 대화", "http://aidh.invalid"))
    assert hits == [], "새 공간에는 아직 벡터가 없다 — 옛 768 벡터와 견주지 않는다"
    assert store.remaining("u1", new) > 0, "새 공간으로는 색인이 남아 있다"
    out = asyncio.run(cs.reindex(store, "u1", "http://aidh.invalid"))
    assert out["indexed"] > 0 and store.remaining("u1", new) == 0
    rows = list(store.vectors_for("u1", new))      # (message_id, chunk_ix, conversation_id, text, blob, …)
    assert rows and all(len(cs.unpack(r[4])) == 1024 for r in rows), "새 공간의 벡터로 저장했다"
    hits = asyncio.run(cs.search(store, "u1", "배터리 스웰링 원인을 찾던 대화", "http://aidh.invalid"))
    assert hits and hits[0]["conversation_id"] == cid


def test_재지_않은_모델은_점수로_거르지_않는다(tmp_path, monkeypatch):
    store = _store(tmp_path)
    cid = store.create(owner_sub="u1", title="t", kind="chat")
    store.append(conversation_id=cid, owner_sub="u1", role="user", content="낙하 해석의 코너 응력 이야기 " * 4)
    new = "aidh-BAAI_bge-m3-1024"
    _fake_embed(monkeypatch, new, 1024, value=1.0)
    asyncio.run(cs.reindex(store, "u1", "http://aidh.invalid"))

    async def low(texts, base_url, kind="passage", timeout=60.0):      # 질의 벡터가 저장 벡터와 0.3 만 닮았다
        cs._LAST["tag"] = new
        return [[0.3, (1 - 0.09) ** 0.5] + [0.0] * 1022 for _ in texts]
    monkeypatch.setattr(cs, "embed", low)
    hits = asyncio.run(cs.search(store, "u1", "낙하 해석의 코너 응력을 다룬 대화를 찾는다", "http://aidh.invalid"))
    assert hits and 0.29 < hits[0]["score"] < 0.31, "e5 하한(0.84)으로 거르지 않는다"
    # 옛 공간(e5)은 그대로 걸러진다
    monkeypatch.setitem(cs._FLOORS, new, (0.5, 0.4))
    hits = asyncio.run(cs.search(store, "u1", "낙하 해석의 코너 응력을 다룬 대화를 찾는다", "http://aidh.invalid"))
    assert hits == [], "잰 하한이 생기면 그것으로 거른다"
