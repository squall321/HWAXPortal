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

import httpx

# 임베딩 공간의 이름. 모델이 바뀌면 이 값을 바꿔야 하고, 그러면 옛 벡터는 자동으로 무시된다
# (vectors_for 가 model 로 거른다). 섞인 채로 코사인을 재는 것이 가장 나쁜 실패다.
MODEL = "aidh-768"
DIM = 768

_CHUNK = 900        # 문자. 한 메시지가 길면 주제가 여러 개다 — 통째로 임베딩하면 다 뭉갠다.
_OVERLAP = 150      # 경계에 걸친 문장이 어느 쪽에서도 안 잡히는 것을 막는다.
_MIN = 40           # 이보다 짧은 조각은 "네", "확인했습니다" 같은 것이라 검색 가치가 없다.


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


async def reindex(store, owner_sub: str, base_url: str, limit: int = 2000) -> dict:
    """아직 벡터가 없는 내 메시지를 색인한다. 증분이며, 여러 번 불러도 안전하다."""
    pending = store.unindexed(owner_sub, MODEL, limit)
    rows, texts, short = [], [], 0
    for m in pending:
        cs = chunks(m["content"])
        if not cs:
            # "네", "확인했습니다" 류. 색인 대상이 아니지 밀린 일이 아니다.
            # ⚠ 표식을 남긴다(chunk_ix=-1). 안 남기면 매 검색마다 다시 뽑혀 나와 LIMIT 창을
            # 차지하고, 짧은 메시지가 창 크기를 넘으면 그보다 오래된 진짜 미색인 메시지가
            # 영영 색인되지 않는다. 이 표식은 vectors_for 가 chunk_ix >= 0 으로 걸러 낸다.
            short += 1
            rows.append({"message_id": m["message_id"], "chunk_ix": -1,
                         "conversation_id": m["conversation_id"], "owner_sub": owner_sub,
                         "text": "", "model": MODEL, "dim": 0, "vec": b""})
            continue
        for ix, c in enumerate(cs):
            rows.append({"message_id": m["message_id"], "chunk_ix": ix,
                         "conversation_id": m["conversation_id"], "owner_sub": owner_sub,
                         "text": c, "model": MODEL, "dim": DIM})
            texts.append(c)
    if not texts:
        store.put_vectors(rows)          # 표식만이라도 남긴다
        return {"indexed": 0, "messages": len(pending), "too_short": short}
    # 한 번에 다 보내면 큰 대화에서 타임아웃이 난다. 나눠 보내되 실패는 그대로 올린다.
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 64):
        vecs.extend(await embed(texts[i:i + 64], base_url, "passage"))
    # 표식 행(dim=0)은 임베딩 대상이 아니었으므로 벡터를 받을 행만 짝짓는다.
    embedded = [r for r in rows if r["dim"]]
    for r, v in zip(embedded, vecs, strict=True):
        r["vec"] = pack(_norm(v))
    store.put_vectors(rows)
    return {"indexed": len(rows), "messages": len(pending), "too_short": short}


async def search(store, owner_sub: str, query: str, base_url: str,
                 limit: int = 8) -> list[dict]:
    """내 대화 안에서만 찾는다. 소유자 필터는 store 가 강제한다."""
    qv = _norm((await embed([query], base_url, "query"))[0])
    # SQLite 전량 조회와 순수 파이썬 코사인은 동기다 — async 엔드포인트에서 그대로 돌리면
    # 색인이 커질수록 포털 이벤트 루프 전체가 그 시간만큼 멈춘다(다른 사용자의 요청까지).
    # 스레드로 뺀다. sqlite3 연결은 check_same_thread=False 로 열려 있어 안전하다.
    return await asyncio.to_thread(_rank, store, owner_sub, qv, limit)


def _rank(store, owner_sub: str, qv: list[float], limit: int) -> list[dict]:
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
