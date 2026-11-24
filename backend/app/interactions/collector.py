# 상호작용 수집기 — 게이트웨이 수집 창고 · 대화 저장소 · 절차 원장 · 도구 검색 질의를 주기마다 원장으로 옮긴다(contract §2 · §3, 포털 백그라운드)
"""원천 넷(PLAN §3 의 S1 · S2 · S3 · S4 · S6).
  · gateway        — 게이트웨이 수집 창고(GET /internal/interactions → 넣기 → 자리 쓰기 → POST /internal/interactions/ack). 서비스 자격은
                     포털이 게이트웨이를 부르는 지금 설정(GATEWAY_SHARED_TOKEN = 게이트웨이 GW_TOKEN, MCP_GATEWAY_URL)이다.
  · conversations  — 대화 저장소(웹 챗 · 웹 심의 · 띵킹 · MCP 워크플로가 저장한 심의)의 메시지를 rowid 차례로. 처음은 전부(백필)이고 주기마다
                     CONV_MAX_PER_TICK 줄까지라 큰 저장소는 몇 주기에 걸쳐 채운다. 끝 줄이 지워진 뒤 rowid 가 다시 쓰이는 틈은 되돌아보기 창(CONV_LOOKBACK)이 덮는다.
  · procedures     — 절차 실행의 단계(run_steps)와 분석 루틴의 호출(routine_calls) · 실행 보고서 — 끝난 실행만(ended_at 차례).
  · tool_search    — 게이트웨이 /search-log(30일 굴림 · 공유 비밀). 처음은 30일, 그 뒤는 지난 자리부터의 날 수. 뒤이은 호출이 나중에 붙으므로 바꿔 쓴다.
읽기는 원천마다 제 연결(대화 · 절차 저장소는 읽기 전용 mode=ro — WAL 이라 쓰는 쪽을 막지 않는다)이고 이벤트 루프 밖(to_thread)에서 돈다.

실패가 정상처럼 보이지 않게(IX-9) — 원천마다 마지막 성공 · 까닭 · 잇단 실패를 들고, /health/interactions(상태판 줄) · /health/ready · 로그 경고로 낸다.
그쪽에 창구가 아직 없거나(404 · 405 — 캡처를 안 켰거나 옛 판) 게이트웨이가 내려가 있으면 실패로 세지 않고 다음 주기에 다시(이용 통계 접기의 FoldPending 꼴).
게이트웨이 /health 의 interactions.dropped(창고 상한을 넘어 버린 줄 수)가 0 이 아니면 넘침으로 낸다."""
from __future__ import annotations

import asyncio
import contextlib
import gzip
import hashlib
import json
import logging
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

import httpx

from app.config import Settings
from app.interactions.store import InteractionStore

logger = logging.getLogger(__name__)

SOURCES = ("gateway", "conversations", "procedures", "tool_search")
FIRST_DELAY_S = 20
GW_PAGE = 500
GW_PAGES_PER_TICK = 20
GW_TIMEOUT_S = 30
CONV_BATCH = 2000
CONV_MAX_PER_TICK = 20000
CONV_LOOKBACK = 500
PROC_BATCH = 500
PROC_LOOKBACK_S = 300
SEARCH_LIMIT = 1000           # 게이트웨이 /search-log 의 limit 상한 — 한 번에 이만큼 오면 앞선 줄을 놓쳤을 수 있다(note)
SEARCH_DAYS_MAX = 30
FAILING_AFTER = 3             # 잇단 실패가 이만큼이면 상태판 · /health 가 붉다
REPEAT_EVERY = 10             # 같은 까닭은 이만큼마다 다시 적는다
STALL_MIN_S = 600             # 마지막 성공이 이보다(또는 주기 × 10 보다) 오래면 멈춤
SPOOL_OLD_S = 3600            # 게이트웨이 창고의 가장 오래된 줄이 이보다 오래면 가져가기가 밀렸다
_WHY = {
    401: "공유 비밀(GATEWAY_SHARED_TOKEN)이 게이트웨이 GW_TOKEN 과 다르다(HTTP 401)",
    403: "게이트웨이가 서비스 호출로 받지 않았다(HTTP 403 — X-Forwarded-* 가 실렸거나 자격이 틀렸다)",
    503: "게이트웨이에 공유 비밀이 없다(HTTP 503)",
}


class Pending(Exception):
    """그쪽 창구가 아직 없다 · 그쪽이 내려가 있다 — 까닭은 남기되 실패로 세지 않고 다음 주기에 다시."""


class IngestError(Exception):
    """원천 하나를 옮기지 못한 까닭 — 사람이 읽는 글(비밀 · 주소는 싣지 않는다)."""


def _ts(v) -> int:
    """원천의 시각 → 초. 수(초 · 밀리초)와 ISO 글을 받는다 — 못 읽으면 지금."""
    if isinstance(v, bool):
        return int(time.time())
    if isinstance(v, (int, float)):
        return int(v / 1000) if v > 1e12 else int(v)
    if isinstance(v, str) and v.strip():
        with contextlib.suppress(ValueError):
            return int(datetime.fromisoformat(v.strip().replace("Z", "+00:00")).timestamp())
    return int(time.time())


def _client(v) -> str | None:
    if isinstance(v, dict):
        s = " ".join(str(v.get(k)) for k in ("name", "version") if v.get(k))
        return s[:120] or None
    return str(v)[:120] if v else None


def _aff_lookup(app):
    """이메일 → 지금 소속(원장 행). 그때의 소속은 원천이 주지 않아 옮기는 때의 값을 적는다. 주기 안에서만 기억한다."""
    cache: dict[str, str | None] = {}
    store = getattr(getattr(app, "state", None), "user_store", None)

    def aff(email) -> str | None:
        if not email or store is None:
            return None
        e = str(email).strip().lower()
        if e not in cache:
            try:
                cache[e] = ((store.get(e) or {}).get("affiliation") or None)
            except Exception:  # noqa: BLE001 — 소속을 못 읽어도 사건은 넣는다
                cache[e] = None
        return cache[e]
    return aff


def _auth(settings: Settings) -> dict:
    tok = settings.gateway_shared_token
    if not tok:
        raise IngestError("공유 비밀(GATEWAY_SHARED_TOKEN)이 없어 게이트웨이를 부르지 않는다")
    return {"Authorization": f"Bearer {tok}"}


async def _gw_get(cli: httpx.AsyncClient, settings: Settings, path: str, params: dict, what: str, *,
                  auth_pending: bool = False) -> dict:
    """auth_pending — 401 · 403 도 기다림으로 센다. 게이트웨이는 캡처 스위치가 꺼졌으면 내부 창구를 일반 인증으로 보내 401 로 답한다(게이트웨이
    작업자 확정 꼴) — 그때는 공유 비밀이 틀린 것과 구별이 안 된다. 그래서 게이트웨이 /health 가 interactions.enabled 를 참으로 말할 때만 실패로 센다."""
    try:
        r = await cli.get(f"{settings.mcp_gateway_url.rstrip('/')}{path}", params=params, headers=_auth(settings), timeout=GW_TIMEOUT_S)
    except httpx.ConnectError as exc:
        raise Pending(f"게이트웨이에 닿지 못했다 — 내려가 있다({type(exc).__name__} · 다음 주기에 다시)") from exc
    except httpx.HTTPError as exc:
        raise IngestError(f"게이트웨이 {what} 답을 받지 못했다({type(exc).__name__})") from exc
    if r.status_code in (404, 405):
        raise Pending(f"게이트웨이에 {what} 창구가 없다(HTTP {r.status_code} — 스위치를 안 켰거나 옛 판 · 다음 주기에 다시)")
    if auth_pending and r.status_code in (401, 403):
        raise Pending(f"게이트웨이 {what} 창구가 자격을 받지 않았다(HTTP {r.status_code}) — 게이트웨이 /health 가 캡처를 켰다고 말하지 않는다"
                      "(GATEWAY_INTERACTION_CAPTURE 꺼짐 · 옛 판 · 다음 주기에 다시)")
    if r.status_code != 200:
        raise IngestError(_WHY.get(r.status_code, f"게이트웨이 {what} 답이 HTTP {r.status_code} 이다"))
    try:
        data = r.json()
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise IngestError(f"게이트웨이 {what} 답의 꼴이 다르다(JSON 객체가 아니다)")
    return data


# ── gateway — 수집 창고 ──────────────────────────────────────────────────────
# 게이트웨이의 share_conversation 호출 줄 — 인자에 대화가 통째로 실린다. 같은 대화가 포털 공유 창구로 shared_sessions 에 들어가므로 건너뛴다(겹치지 않게).
SHARE_TOOL = "share_conversation"


def gateway_event(e: dict, aff) -> dict:
    """창고 한 줄(contract §3) → 사건. via 는 게이트웨이가 준 낱말 그대로(pat · chat · procedure · mcp-app · gw-token · service …) 칸에 둔다 —
    계약 §2 의 여섯과 낱말이 달라도 바꿔 적지 않는다(IX-15 · 계약 변경 제안). args 는 1 MB 를 넘으면 앞부분 글이고 args_chars 가 붙는다(meta 로).
    줄에 id 가 없으면 내용으로 열쇠를 짓는다."""
    via = str(e["via"])[:40] if e.get("via") else None
    known = {"ts", "corr", "rid", "actor", "via", "client", "tool", "backend", "orig", "args", "result", "result_chars",
             "result_sha256", "is_error", "ms", "id"}
    meta = {k: v for k, v in e.items() if k not in known}
    if e.get("orig"):
        meta["orig"] = e["orig"]
    ref = e.get("id")
    if not ref:
        key = [e.get(k) for k in ("ts", "corr", "rid", "actor", "tool", "backend", "result_sha256", "ms")]
        key.append(hashlib.sha256(json.dumps(e.get("args"), sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest())
        ref = hashlib.sha256(json.dumps(key, ensure_ascii=False, default=str).encode()).hexdigest()[:40]
    res = e.get("result")
    return {"ts": _ts(e.get("ts")), "surface": "mcp_call", "actor": e.get("actor"), "affiliation": aff(e.get("actor")),
            "client": _client(e.get("client")), "corr": e.get("corr"), "rid": e.get("rid"), "via": via,
            "app": e.get("backend"), "tool": e.get("tool"), "status": "error" if e.get("is_error") else "ok",
            "ms": int(e["ms"]) if isinstance(e.get("ms"), (int, float)) and not isinstance(e.get("ms"), bool) else None,
            "input": e.get("args"), "output": res if isinstance(res, str) or res is None else json.dumps(res, ensure_ascii=False, default=str),
            "output_chars": e.get("result_chars") if isinstance(e.get("result_chars"), int) else None,
            "output_sha256": e.get("result_sha256") if isinstance(e.get("result_sha256"), str) else None,
            "meta": meta, "source": "gateway", "source_ref": str(ref)[:80]}


class AckState:
    """마지막으로 게이트웨이가 받은 ack 자리 — 실패했으면 다음 주기에 같은 자리로 다시 보낸다(창고 조각이 안 지워진 채 남지 않게)."""

    def __init__(self) -> None:
        self.cursor: str | None = None


async def _ingest_gateway(settings: Settings, store: InteractionStore, cli: httpx.AsyncClient, aff, acked: AckState,
                          capture_on: bool = True) -> int:
    """capture_on — 게이트웨이 /health 가 interactions.enabled 를 참으로 말했나. 아니면 401 · 403 을 기다림으로 센다(_gw_get)."""
    n = 0
    base = settings.mcp_gateway_url.rstrip("/")
    for _ in range(GW_PAGES_PER_TICK):
        cur = await asyncio.to_thread(store.cursor, "gateway")
        params: dict = {"max": GW_PAGE}
        if cur:
            params["cursor"] = cur
        data = await _gw_get(cli, settings, "/internal/interactions", params, "수집 창고", auth_pending=not capture_on)
        evs = data.get("events")
        if not isinstance(evs, list):
            raise IngestError("게이트웨이 수집 창고 답에 events 목록이 없다")
        n += await asyncio.to_thread(store.put_events, [gateway_event(e, aff) for e in evs if isinstance(e, dict)
                                                        and SHARE_TOOL not in (e.get("tool"), e.get("orig"))])
        nxt = data.get("next_cursor")    # 불투명 글 — 읽지 않고 그대로 돌려준다(빈 글이면 창고가 비었다)
        if isinstance(nxt, str) and nxt and nxt != cur:
            await asyncio.to_thread(store.set_cursor, "gateway", nxt)     # 넣은 **뒤에** 자리를 쓴다 — 그 사이에 죽으면 다시 읽어 UNIQUE 가 거른다
            cur = nxt
        if cur and acked.cursor != cur:
            try:
                r = await cli.post(f"{base}/internal/interactions/ack", json={"cursor": cur}, headers=_auth(settings), timeout=GW_TIMEOUT_S)
                if r.status_code == 200:
                    acked.cursor = cur
                elif r.status_code == 400:
                    # 게이트웨이가 내준 적 없는 자리라 한다(아무것도 지우지 않았다 — 게이트웨이 재기동 등). 같은 자리를 되풀이해 보내지 않는다 —
                    # 다음 쪽의 자리로 보내는 ack 가 앞선 조각까지 지운다.
                    acked.cursor = cur
                    logger.warning("상호작용 수집 — 게이트웨이가 창고 ack 자리를 모른다고 했다(HTTP 400 · 그 자리는 다시 보내지 않는다)")
                else:
                    logger.warning("상호작용 수집 — 게이트웨이 창고 ack 가 HTTP %s 다(넣기는 끝났다 · 다음 주기에 같은 자리로 다시)", r.status_code)
            except httpx.HTTPError as exc:
                logger.warning("상호작용 수집 — 게이트웨이 창고 ack 를 보내지 못했다(%s · 다음 주기에 다시)", type(exc).__name__)
        if not data.get("more"):
            break
    return n


async def gateway_health(settings: Settings, cli: httpx.AsyncClient) -> dict | None:
    """게이트웨이 /health 의 interactions 칸(무인증) — 넘침(dropped) · 밀림(oldest_ts)을 본다. 못 읽으면 None(모름)."""
    try:
        r = await cli.get(f"{settings.mcp_gateway_url.rstrip('/')}/health", timeout=5)
        body = r.json() if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None
    ix = body.get("interactions") if isinstance(body, dict) else None
    return ix if isinstance(ix, dict) else None


# ── conversations — 대화 저장소 ───────────────────────────────────────────────
_CONV_SQL = ("SELECT m.rowid, m.id, m.conversation_id, m.seq, m.role, m.persona, m.round, m.content, m.meta, m.ts, "
             "c.owner_sub, c.title, c.kind, c.source FROM messages m JOIN conversations c ON c.id = m.conversation_id "
             "WHERE m.rowid > ? ORDER BY m.rowid LIMIT ?")


def conversation_event(r: tuple, aff) -> dict:
    """메시지 한 줄 → 사건. 사람 발화는 input, 답 · 좌석 발언은 output. 메시지 meta(쓴 도구 activity · 답한 모델 · 자기검증 · 확인 카드 — turn)는
    그대로 meta 에 싣는다 — 도구 호출 사건은 따로 만들지 않는다(그 호출은 게이트웨이 줄 하나로만 센다, IX-12)."""
    _rowid, mid, cid, seq, role, persona, rnd, content, meta_s, ts, owner, title, kind, src = r
    try:
        meta = json.loads(meta_s) if meta_s else {}
    except ValueError:
        meta = {"meta_unreadable": True}
    meta = meta if isinstance(meta, dict) else {"meta_raw": meta}
    answered = meta.get("answered_by")
    if kind in ("deliberation", "risk-review") or role == "persona" or answered == "delib":
        surface = "web_delib"
    elif answered == "think":
        surface = "think"
    else:
        surface = "web_chat"
    turn = meta.get("turn") if isinstance(meta.get("turn"), dict) else {}
    model = turn.get("chat_model") if isinstance(turn.get("chat_model"), str) else None
    if not model and isinstance(turn.get("models"), dict) and turn["models"]:
        model = sorted(turn["models"])[0]
    tools = [str(a.get("tool")) for a in meta.get("activity") or [] if isinstance(a, dict) and a.get("tool")]
    out = {**meta, "role": role, "seq": seq, "title": title, "conv_kind": kind, "conv_source": src}
    if persona:
        out["persona"] = persona
    if rnd is not None:
        out["round"] = rnd
    if tools:
        out["tools"] = tools
    user = role == "user"
    return {"ts": int(ts or time.time()), "surface": surface, "actor": owner, "affiliation": aff(owner),
            "client": "MCP 워크플로" if src == "mcp" else "브라우저", "conv_id": cid, "turn_id": str(seq), "model": model,
            "input": content if user else None, "output": None if user else content, "meta": out,
            "source": "conversations", "source_ref": mid}


def _ingest_conversations(settings: Settings, store: InteractionStore, aff) -> int:
    path = Path(settings.resolve(settings.conv_store_path))
    if not path.exists():
        return 0
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=settings.conv_store_busy_timeout_s)) as con:
        cur = int(store.cursor("conversations") or 0)
        top = con.execute("SELECT COALESCE(MAX(rowid), 0) FROM messages").fetchone()[0]
        cur = min(cur, top)                  # 끝 줄이 지워졌다 — 다음 rowid 가 다시 쓰인다
        pos, last, n, seen = max(0, cur - CONV_LOOKBACK), cur, 0, 0
        while seen < CONV_MAX_PER_TICK:
            rows = con.execute(_CONV_SQL, (pos, CONV_BATCH)).fetchall()
            if not rows:
                break
            n += store.put_events([conversation_event(r, aff) for r in rows])
            pos = rows[-1][0]
            last, seen = max(last, pos), seen + len(rows)
            if len(rows) < CONV_BATCH:
                break
    store.set_cursor("conversations", str(last))
    return n


# ── procedures — 절차 · 루틴 실행 원장 ───────────────────────────────────────
def _gunzip(b) -> str | None:
    if not b:
        return None
    try:
        return gzip.decompress(b).decode("utf-8", "replace")
    except (OSError, EOFError):
        return None


def _ingest_procedures(settings: Settings, store: InteractionStore, aff) -> int:
    path = Path(settings.resolve(settings.procedures_store_path))
    if not path.exists():
        return 0
    try:
        cur = json.loads(store.cursor("procedures") or "{}")
    except ValueError:
        cur = {}
    cur = cur if isinstance(cur, dict) else {}
    n = 0
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=settings.conv_store_busy_timeout_s)) as con:
        # 절차 실행 — 단계 하나 = 사건 하나(via procedure). 같은 호출의 게이트웨이 줄(via procedure)은 따로 남는다 — 이쪽은 실행 원장 사본이다.
        since = int(cur.get("runs", 0)) - PROC_LOOKBACK_S
        runs = con.execute("SELECT id, owner_sub, run_by, title, origin, mode, state, started_at, ended_at, procedure_version_id "
                           "FROM runs WHERE ended_at IS NOT NULL AND ended_at >= ? ORDER BY ended_at LIMIT ?",
                           (since, PROC_BATCH)).fetchall()
        for rid, owner, run_by, title, origin, mode, state, started, ended, ver in runs:
            actor = run_by or owner
            evs = []
            for (ix, backend, tool, args, gz, rbytes, sha, trunc, preview, st, ok, err, s_at, dur, s_mode) in con.execute(
                    "SELECT ix, backend, tool, args_json, result_gz, result_bytes, result_sha256, truncated, preview, state, ok, error, "
                    "started_at, duration_ms, mode FROM run_steps WHERE run_id = ? ORDER BY ix", (rid,)):
                text = _gunzip(gz) or preview
                evs.append({"ts": int(s_at or started or ended), "surface": "procedure", "actor": actor, "affiliation": aff(actor),
                            "client": "절차 실행기", "via": "procedure", "app": backend, "tool": tool,
                            "status": "ok" if ok else ("error" if ok == 0 else None), "ms": dur, "input": args, "output": text,
                            "output_chars": rbytes if trunc else None, "output_sha256": sha,
                            "meta": {"run_id": rid, "step": ix, "title": title, "run_state": state, "step_state": st, "error": err,
                                     "origin": origin, "mode": s_mode or mode, "procedure_version_id": ver, "truncated": bool(trunc)},
                            "source": "procedures", "source_ref": f"run:{rid}:{ix}"})
            n += store.put_events(evs)
            cur["runs"] = max(int(cur.get("runs", 0)), int(ended))
        # 분석 루틴 — 호출 하나 = 사건 하나(via routine) + 실행 하나의 보고서 = 사건 하나
        try:
            rruns = con.execute("SELECT id, owner_sub, routine_id, title, inputs_json, executor, conversation_id, state, reason, started_at, "
                                "ended_at, report_md FROM routine_runs WHERE ended_at IS NOT NULL AND ended_at >= ? ORDER BY ended_at LIMIT ?",
                                (int(cur.get("routines", 0)) - PROC_LOOKBACK_S, PROC_BATCH)).fetchall()
        except sqlite3.OperationalError:
            rruns = []                        # 루틴 표가 없는 옛 저장소
        for rid, owner, routine_id, title, inputs, executor, conv, state, reason, started, ended, report in rruns:
            evs = [{"ts": int(ended), "surface": "routine", "actor": owner, "affiliation": aff(owner), "client": f"루틴 실행기({executor})",
                    "conv_id": conv, "via": "routine", "status": "ok" if state == "done" else "error", "input": inputs, "output": report,
                    "meta": {"run_id": rid, "routine_id": routine_id, "title": title, "state": state, "reason": reason,
                             "started_at": started, "kind": "run"},
                    "source": "procedures", "source_ref": f"routine_run:{rid}"}]
            for (call_id, step_id, num, backend, tool, args, ok, ms, gz, chars, sha, trunc, created) in con.execute(
                    "SELECT call_id, step_id, n, backend, tool, args_json, ok, ms, result_gz, result_chars, result_sha256, truncated, "
                    "created_at FROM routine_calls WHERE run_id = ? ORDER BY n", (rid,)):
                evs.append({"ts": int(created), "surface": "routine", "actor": owner, "affiliation": aff(owner),
                            "client": f"루틴 실행기({executor})", "conv_id": conv, "via": "routine", "app": backend, "tool": tool,
                            "status": "ok" if ok else "error", "ms": ms, "input": args, "output": _gunzip(gz),
                            "output_chars": chars if trunc else None, "output_sha256": sha,
                            "meta": {"run_id": rid, "routine_id": routine_id, "title": title, "step_id": step_id, "n": num,
                                     "truncated": bool(trunc), "kind": "call"},
                            "source": "procedures", "source_ref": f"routine:{rid}:{call_id}"})
            n += store.put_events(evs)
            cur["routines"] = max(int(cur.get("routines", 0)), int(ended))
    store.set_cursor("procedures", json.dumps(cur, sort_keys=True))
    return n


# ── tool_search — 게이트웨이 도구 검색 질의(30일 굴림) ─────────────────────────
def search_event(r: dict) -> dict:
    meta = {k: r.get(k) for k in ("d", "mode", "fp", "top", "via", "boost_only", "outcomes", "mark") if r.get(k) is not None}
    top = r.get("top") if isinstance(r.get("top"), list) else []
    return {"ts": _ts(r.get("ts")), "surface": "tool_search", "client": "게이트웨이 search_tools", "tool": "search_tools",
            "input": str(r.get("q") or ""), "output": "\n".join(str(t) for t in top), "meta": meta,
            "source": "tool_search", "source_ref": str(r.get("id"))[:40]}


async def _ingest_tool_search(settings: Settings, store: InteractionStore, cli: httpx.AsyncClient, notes: dict) -> int:
    cur = await asyncio.to_thread(store.cursor, "tool_search")
    now = time.time()
    days = SEARCH_DAYS_MAX if not cur else max(2, min(SEARCH_DAYS_MAX, int((now - int(cur)) // 86400) + 2))
    data = await _gw_get(cli, settings, "/search-log", {"days": days, "limit": SEARCH_LIMIT}, "도구 검색 기록")
    rows = [r for r in data.get("searches") or [] if isinstance(r, dict) and r.get("id")]
    n = await asyncio.to_thread(store.put_events, [search_event(r) for r in rows], update=True)
    if rows:
        newest = max(_ts(r.get("ts")) for r in rows)
        await asyncio.to_thread(store.set_cursor, "tool_search", str(max(newest, int(cur or 0))))
    if len(rows) >= SEARCH_LIMIT:
        notes["tool_search"] = (f"한 번에 {SEARCH_LIMIT}줄이 와 그보다 앞선 질의를 놓쳤을 수 있다(게이트웨이 /search-log 에 자리 · 쪽이 없다 — "
                                "게이트웨이에 청할 것)")
    return n


# ── 한 주기 · 상태 ────────────────────────────────────────────────────────────
def _new_status() -> dict:
    return {s: {"last_ok": None, "last_try": None, "error": None, "pending": None, "fails": 0, "rows": 0, "note": None} for s in SOURCES}


async def run_once(app, settings: Settings, store: InteractionStore, *, client: httpx.AsyncClient | None = None) -> dict:
    """한 번 옮긴다 → {원천: 새로 넣은 줄 수 또는 {"error"|"pending": 까닭}}. 예외를 내지 않는다 — 원천 하나의 실패가 다른 원천을 막지 않는다.
    상태는 app.state.interactions_status 에 쌓는다(없으면 만든다)."""
    st = getattr(app.state, "interactions_status", None) or _new_status()
    app.state.interactions_status = st
    acked = getattr(app.state, "interactions_ack", None) or AckState()
    app.state.interactions_ack = acked
    aff = _aff_lookup(app)
    own = client is None
    cli = client or httpx.AsyncClient()
    notes: dict = {}
    out: dict = {}
    try:
        spool = await gateway_health(settings, cli)
        app.state.interactions_spool = spool
        capture_on = bool((spool or {}).get("enabled") is True)
        steps = (("gateway", lambda: _ingest_gateway(settings, store, cli, aff, acked, capture_on)),
                 ("conversations", lambda: asyncio.to_thread(_ingest_conversations, settings, store, aff)),
                 ("procedures", lambda: asyncio.to_thread(_ingest_procedures, settings, store, aff)),
                 ("tool_search", lambda: _ingest_tool_search(settings, store, cli, notes)))
        for source, step in steps:
            s = st[source]
            s["last_try"] = time.time()
            try:
                got = await step()
                out[source] = got
                s.update(last_ok=time.time(), error=None, pending=None, fails=0, rows=s["rows"] + got)
            except asyncio.CancelledError:
                raise
            except Pending as exc:
                out[source] = {"pending": str(exc)}
                s.update(pending=str(exc), error=None, fails=0)
            except Exception as exc:  # noqa: BLE001 — 까닭을 남기고 다음 원천으로
                why = str(exc) if isinstance(exc, IngestError) else f"{type(exc).__name__}: {str(exc)[:160]}"
                out[source] = {"error": why}
                s.update(error=why, pending=None, fails=s["fails"] + 1)
            s["note"] = notes.get(source)
    finally:
        if own:
            await cli.aclose()
    return out


def problems(app, settings: Settings, *, now: float | None = None) -> list[str]:
    """지금의 문제 코드 — 빈 목록이면 건강하다. 문장이 아니라 코드다(무인증 /health 에 싣는다 · 까닭 글은 로그와 분석가 화면에)."""
    now = time.time() if now is None else now
    out: list[str] = []
    every = int(settings.interactions_ingest_s or 0)
    task = getattr(app.state, "interactions_task", None)
    if every <= 0:
        return ["collector_off"]
    if task is None or task.done():
        out.append("collector_dead")
    st = getattr(app.state, "interactions_status", None)
    started = getattr(app.state, "interactions_started", now)
    stall = max(STALL_MIN_S, every * 10)
    for src in SOURCES:
        s = (st or {}).get(src) or {}
        if s.get("fails", 0) >= FAILING_AFTER:
            out.append(f"failing:{src}")
        elif not s.get("pending") and (s.get("last_ok") or started) < now - stall:
            out.append(f"stalled:{src}")
    spool = getattr(app.state, "interactions_spool", None) or {}
    if isinstance(spool.get("dropped"), int) and spool["dropped"] > 0:
        out.append("spool_dropped")
    if isinstance(spool.get("errors"), int) and spool["errors"] > 0:
        out.append("spool_errors")                # 게이트웨이가 창고에 덧붙이지 못한 줄(호출은 막지 않았다 — 그 줄은 잃었다)
    if isinstance(spool.get("oldest_ts"), (int, float)) and spool["oldest_ts"] and _ts(spool["oldest_ts"]) < now - SPOOL_OLD_S:
        out.append("spool_old")
    return out


def health(app, settings: Settings) -> tuple[bool, dict]:
    """(건강한가, 무인증 본문) — 원천마다 상태 낱말(ok · pending · error · waiting)과 마지막 성공 시각만. 비밀 · 주소 · 까닭 글은 싣지 않는다."""
    probs = problems(app, settings)
    st = getattr(app.state, "interactions_status", None) or {}
    srcs = {}
    for src in SOURCES:
        s = st.get(src) or {}
        state = "error" if s.get("error") else "pending" if s.get("pending") else "ok" if s.get("last_ok") else "waiting"
        srcs[src] = {"state": state, "last_ok": int(s["last_ok"]) if s.get("last_ok") else None}
    spool = getattr(app.state, "interactions_spool", None) or {}
    return not probs, {"ok": not probs, "problems": probs, "sources": srcs,
                       "spool": {k: spool.get(k) for k in ("enabled", "spool_bytes", "segments", "dropped", "errors", "oldest_ts")} if spool else None}


async def run(app, settings: Settings, store: InteractionStore, every: float) -> None:
    """기동 뒤 조금 있다가 한 번, 그 뒤 every 초마다 — 끌 때(cancel)까지. 까닭이 바뀔 때와 REPEAT_EVERY 번마다 경고로 적는다."""
    last: dict[str, str | None] = {}
    delay = min(every, FIRST_DELAY_S)
    dropped_seen = 0
    n = 0
    while True:
        await asyncio.sleep(delay)
        delay = every
        t0 = time.time()
        out = await run_once(app, settings, store)
        n += 1
        st = app.state.interactions_status
        for src, v in out.items():
            why = v.get("error") or v.get("pending") if isinstance(v, dict) else None
            kind = "error" if isinstance(v, dict) and v.get("error") else "pending" if isinstance(v, dict) else None
            if why and (why != last.get(src) or st[src]["fails"] % REPEAT_EVERY == 0 and st[src]["fails"]):
                (logger.warning if kind == "error" else logger.info)(
                    "상호작용 수집 — %s 를 %s(%s번째 · 다음 주기에 다시): %s", src,
                    "옮기지 못했다" if kind == "error" else "기다린다", st[src]["fails"] or "-", why)
            elif not why and last.get(src):
                logger.warning("상호작용 수집 — %s 를 다시 옮긴다(앞선 까닭: %s)", src, last[src])
            last[src] = why
        spool = getattr(app.state, "interactions_spool", None) or {}
        if isinstance(spool.get("dropped"), int) and spool["dropped"] > dropped_seen:
            logger.warning("상호작용 수집 — 게이트웨이 수집 창고가 넘쳐 %d줄을 버렸다(GATEWAY_INTERACTION_SPOOL_MAX_MB · 포털 가져가기가 멈췄는지 본다)",
                           spool["dropped"])
            dropped_seen = spool["dropped"]
        if n == 1:
            logger.warning("상호작용 수집 — 기동 뒤 첫 주기(%.1f초): %s", time.time() - t0,
                           " · ".join(f"{s} {v}줄" if isinstance(v, int) else f"{s} {'기다림' if 'pending' in v else '실패'}" for s, v in out.items()))


def start(app, settings: Settings, store: InteractionStore) -> asyncio.Task | None:
    """기동 때 — 손잡이(INTERACTIONS_INGEST_S)가 0 이하면 띄우지 않는다(None — /health/interactions 가 collector_off 로 붉다)."""
    every = int(settings.interactions_ingest_s or 0)
    app.state.interactions_started = time.time()
    if every <= 0:
        logger.warning("상호작용 수집 — INTERACTIONS_ENABLED 는 켜졌는데 INTERACTIONS_INGEST_S=0 이라 수집기를 띄우지 않는다(공유 창구 · 열람만 돈다)")
        return None
    return asyncio.get_running_loop().create_task(run(app, settings, store, float(every)), name="interactions-ingest")


async def stop(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
