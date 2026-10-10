# 내 지난 대화를 의미로 검색한다 — AIDataHub 임베더(768차원)를 그대로 빌려 쓴다.
"""왜 의미검색인가.

키워드는 "그때 배터리 스웰링 얘기하다 나온 그 판단"을 못 찾는다. 사용자가 기억하는 것은
표현이 아니라 내용이고, 지난 대화를 다시 꺼내는 목적 자체가 "무슨 얘기였는지"이기 때문이다.

왜 브루트포스인가. 지금 규모가 290 메시지다. 실측으로 10k 청크에서 2.6ms, 100k 에서 3.9ms,
1M 에서 37ms — 인덱스 구조를 얹을 이유가 아직 없다. 필요해지면 이 파일 안에서 바꾼다.

왜 임베더를 새로 안 만드는가. AIDataHub 가 이미 /api/embed 로 같은 모델을 서비스하고 있고,
검색 품질은 "같은 공간에 있느냐"가 좌우한다. 두 벌을 두면 반드시 어긋난다.
"""
from __future__ import annotations

import asyncio
import re
import struct
import time

import httpx

# 임베딩 공간의 이름. 모델이 바뀌면 이 값을 바꿔야 하고, 그러면 옛 벡터는 자동으로 무시된다
# (vectors_for 가 model 로 거른다). 섞인 채로 코사인을 재는 것이 가장 나쁜 실패다.
MODEL = "aidh-768"
DIM = 768

_CHUNK = 900        # 문자. 한 메시지가 길면 주제가 여러 개다 — 통째로 임베딩하면 다 뭉갠다.
_OVERLAP = 150      # 경계에 걸친 문장이 어느 쪽에서도 안 잡히는 것을 막는다.
_MIN = 40           # 이보다 짧은 조각은 "네", "확인했습니다" 같은 것이라 검색 가치가 없다.
# 이보다 낮으면 "관련 없음" 으로 본다. 감이 아니라 이 코퍼스에서 잰 값이다(2026-08-19,
# 1096청크): 정답 청크 점수 최소 0.882, 무관 질의 1위 최대 0.822 — 두 분포 사이가 비어
# 있고 0.84 가 그 한가운데다. 실측으로 정답 손실 0/23, 무관 통과 0/6.
# 코퍼스가 크게 바뀌면 다시 재야 한다(같은 방식으로 두 분포를 찍어 보면 된다).
_MIN_SCORE = 0.84
# 짧은 질의는 이 하한을 못 쓴다. e5 는 짧은 문장을 긴 본문과 견줄 때 점수를 낮게 주는데,
# 위 0.84 는 긴 질의(180자 발췌)로만 잰 값이라 '흡습재' 같은 정당한 질의가 통째로 걸렸다.
# 짧은 질의로 다시 재 보니 온토픽 0.767~0.859, 오프토픽 최대 0.803 으로 **분포가 겹친다** —
# 어떤 임계값도 깨끗이 가르지 못한다(0.78: 오탐 2/6, 0.82: 정답 3/6 손실).
# 그래서 거르지 말고 알린다. 못 가르는 것을 가르는 척하면 둘 중 하나는 반드시 거짓이 된다.
_SHORT_Q = 12          # 이보다 짧은 질의는 점수로 관련성을 판정하지 않는다
_SHORT_FLOOR = 0.75    # 명백한 무관만 쳐내는 느슨한 바닥

# 검색 한 번이 색인에 쓰는 시간. 게이트웨이 search_conversations 는 포털을 120초 기다린다(HWAXMcpGateway gateway.py) — 그보다 길면
# 게이트웨이가 먼저 포기하는데 핸들러는 계속 돌고, 벡터를 쓰기 전에 다음 검색이 같은 미색인분을 다시 보낸다. 웹 심의의 서버 사본이
# 좌석 발언을 줄이지 않은 글로 건수 상한 없이 남기면서(수천 자 × 좌석 × 라운드) 큰 심의 뒤 첫 검색이 이 한도에 닿는다. 예산에서
# 멈추고 남은 수는 응답의 index.not_indexed_yet·partial 이 말한다 — 다음 검색이 잇는다.
REINDEX_BUDGET_S = 60.0
_EMBED_BATCH = 64
_clock = time.monotonic   # 시험이 시계를 바꿔 끼운다


def chunks(text: str) -> list[str]:
    t = re.sub(r"\s+", " ", text or "").strip()
    if len(t) <= _CHUNK:
        return [t] if len(t) >= _MIN else []
    out, i = [], 0
    while i < len(t):
        out.append(t[i:i + _CHUNK])
        i += _CHUNK - _OVERLAP
    return [c for c in out if len(c) >= _MIN]


def pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _norm(v: list[float]) -> list[float]:
    s = sum(x * x for x in v) ** 0.5
    return [x / s for x in v] if s else v


async def embed(texts: list[str], base_url: str, kind: str = "passage",
                timeout: float = 60.0) -> list[list[float]]:
    """AIDataHub 임베더 호출. 실패를 삼키지 않는다 — 빈 결과로 떨어지면 '검색해봤는데 없다'가
    되어 사용자가 없는 사실을 믿는다."""
    if not texts:
        return []
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.post(f"{base_url.rstrip('/')}/api/embed",
                           json={"texts": texts, "kind": kind})
        r.raise_for_status()
        data = r.json()
    vecs = data.get("vectors") or []
    if len(vecs) != len(texts):
        raise ValueError(f"임베더가 {len(texts)}개를 받아 {len(vecs)}개를 돌려줬습니다.")
    return vecs


async def reindex(store, owner_sub: str, base_url: str, limit: int = 2000,
                  budget_s: float = REINDEX_BUDGET_S) -> dict:
    """아직 벡터가 없는 내 메시지를 색인한다. 증분이며, 여러 번 불러도 안전하다.

    budget_s 를 넘기면 새 메시지를 더 꺼내지 않고 멈춘다(budget_hit) — 남은 것은 다음 검색이 잇는다. 벡터는 임베딩 한 묶음
    (조각 64개 남짓)을 끝낼 때마다 쓴다. 메시지 하나의 조각은 한 묶음에 다 들어가므로, 쓰인 메시지는 조각을 전부 가진다(반쪽만
    쓰면 '색인됨' 으로 분류돼 뒤쪽 조각을 영영 못 찾는다). 임베더가 중간에 실패해도 앞서 끝낸 묶음은 남는다."""
    t0 = _clock()
    # 동기 sqlite 전량 조회다. 색인 대상이 수천 건이면 그 시간만큼 이벤트 루프가 멈춘다 —
    # _rank 만 빼고 여기를 남긴 것은 조사가 '아는 이름' 만 찾았기 때문이다(실측 지적).
    pending = await asyncio.to_thread(store.unindexed, owner_sub, MODEL, limit)
    marks, todo, short = [], [], 0
    for m in pending:
        cs = chunks(m["content"])
        if not cs:
            # "네", "확인했습니다" 류. 색인 대상이 아니지 밀린 일이 아니다.
            # ⚠ 표식을 남긴다(chunk_ix=-1). 안 남기면 매 검색마다 다시 뽑혀 나와 LIMIT 창을
            # 차지하고, 짧은 메시지가 창 크기를 넘으면 그보다 오래된 진짜 미색인 메시지가
            # 영영 색인되지 않는다. 이 표식은 vectors_for 가 chunk_ix >= 0 으로 걸러 낸다.
            short += 1
            marks.append({"message_id": m["message_id"], "chunk_ix": -1,
                          "conversation_id": m["conversation_id"], "owner_sub": owner_sub,
                          "text": "", "model": MODEL, "dim": 0, "vec": b""})
            continue
        todo.append((m, cs))
    if marks:
        await asyncio.to_thread(store.put_vectors, marks)   # 표식은 임베딩 없이 바로 남긴다
    written, done, budget_hit = len(marks), 0, False
    group: list[dict] = []
    texts: list[str] = []

    async def flush() -> None:
        nonlocal written
        # 한 번에 다 보내면 큰 대화에서 타임아웃이 난다. 나눠 보내되 실패는 그대로 올린다.
        vecs: list[list[float]] = []
        for i in range(0, len(texts), _EMBED_BATCH):
            vecs.extend(await embed(texts[i:i + _EMBED_BATCH], base_url, "passage"))
        for r, v in zip(group, vecs, strict=True):
            r["vec"] = pack(_norm(v))
        # 수천 행 일괄 INSERT — 같은 이유로 스레드에서.
        await asyncio.to_thread(store.put_vectors, group)
        written += len(group)
        group.clear()
        texts.clear()

    for m, cs in todo:
        if _clock() - t0 >= budget_s:
            budget_hit = True
            break
        for ix, c in enumerate(cs):
            group.append({"message_id": m["message_id"], "chunk_ix": ix,
                          "conversation_id": m["conversation_id"], "owner_sub": owner_sub,
                          "text": c, "model": MODEL, "dim": DIM})
            texts.append(c)
        done += 1
        if len(texts) >= _EMBED_BATCH:
            await flush()
    if texts:
        await flush()
    return {"indexed": written, "messages": len(pending), "too_short": short,
            "budget_hit": budget_hit, "deferred": len(todo) - done}


def short_query(query: str) -> bool:
    """질의가 짧아 점수로 관련성을 판정할 수 없는가. 호출부가 그 사실을 사용자에게 알린다."""
    return len((query or "").strip()) < _SHORT_Q


async def search(store, owner_sub: str, query: str, base_url: str,
                 limit: int = 8) -> list[dict]:
    """내 대화 안에서만 찾는다. 소유자 필터는 store 가 강제한다."""
    qv = _norm((await embed([query], base_url, "query"))[0])
    # SQLite 전량 조회와 순수 파이썬 코사인은 동기다 — async 엔드포인트에서 그대로 돌리면
    # 색인이 커질수록 포털 이벤트 루프 전체가 그 시간만큼 멈춘다(다른 사용자의 요청까지).
    # 스레드로 뺀다. sqlite3 연결은 check_same_thread=False 로 열려 있어 안전하다.
    return await asyncio.to_thread(_rank, store, owner_sub, qv, limit,
                                   _SHORT_FLOOR if short_query(query) else _MIN_SCORE)


def _rank(store, owner_sub: str, qv: list[float], limit: int, floor: float) -> list[dict]:
    hits = []
    for mid, cix, cid, text, blob, title, role, persona, ts in store.vectors_for(owner_sub, MODEL):
        v = unpack(blob)
        if len(v) != len(qv):
            continue          # 차원이 다르면 옛 모델의 잔재다. 조용히 건너뛴다.
        hits.append({
            "score": sum(a * b for a, b in zip(qv, v, strict=True)),
            "conversation_id": cid, "title": title, "role": role,
            "persona": persona, "ts": ts, "text": text,
            "message_id": mid, "chunk_ix": cix,
        })
    hits.sort(key=lambda h: h["score"], reverse=True)
    # 하한을 둔다. e5 는 무관한 문장끼리도 0.75~0.85 가 나오므로, 하한이 없으면 한 번도
    # 나온 적 없는 주제에도 늘 limit 건을 그럴듯한 점수와 함께 돌려준다 — "찾았다" 와
    # "없다" 가 구분되지 않는 검색은 없는 사실을 지어내는 것과 같다.
    # 값은 실측 기준이다: 같은 코퍼스에서 무관 질의 상위가 0.79~0.82, 적중은 0.86 이상.
    # 상대폭('1위 대비 얼마 이내')도 함께 걸어 봤으나 이 코퍼스에서는 절대 하한과 결과가
    # 완전히 같았고(재현율 23/25·오탐 0/6 동일), 1위가 유난히 높을 때 멀쩡한 2·3위를
    # 버리는 실패 모드만 늘었다. 하는 일이 없으면 없는 편이 낫다.
    hits = [h for h in hits if h["score"] >= floor]
    # 같은 대화가 상위를 독식하면 "어느 대화였는지"를 못 고른다 — 대화당 2조각까지만 올린다.
    seen: dict[str, int] = {}
    out = []
    for h in hits:
        n = seen.get(h["conversation_id"], 0)
        if n >= 2:
            continue
        seen[h["conversation_id"]] = n + 1
        out.append(h)
        if len(out) >= limit:
            break
    return out
