# 심의 묶음 끝남 알림 당기기 — 에이전트 서버의 끝난 묶음 창구를 주기로 물어 묶음마다 주인에게 포털 알림 한 줄을 남긴다(docs/request-1117 contracts §7)
"""엔진 창구 `POST /deliberate/batch/finished {since, limit}` → `{batches: [{batch_id, owner, name, status, finished_at, counts, notice}], next_since}`.

- **공유 비밀만 싣는다**(GATEWAY_SHARED_TOKEN — 포털이 에이전트 서버의 다른 서비스 창구에 쓰는 그 값). 사람 신원 머리(x-hwax-user)를 실으면 엔진이 403
  으로 거절한다 — 싣지 않는다. 비밀은 로그 · 답 어디에도 적지 않는다.
- **같은 묶음은 한 번만** — 엔진은 next_since 를 마지막 묶음의 finished_at 으로 주므로 경계의 묶음이 다음 부름에 다시 나온다. 알림 원장의 (kind, batch_id)
  유일 색인이 걸러 낸다. 재기동 · 여러 일꾼이 같은 쪽을 다시 읽어도 같다(INSERT OR IGNORE). 커서는 원장에 남고 앞으로만 간다(재기동에도 이어 읽는다).
  알림을 쓴 **뒤에** 커서를 옮긴다 — 그 사이에 죽으면 같은 쪽을 다시 읽을 뿐이다.
- 주인이 포털 계정(users 원장의 이메일)이 아니면 남기지 않는다(셈만 한다).
- 실패는 까닭과 함께 경고 로그로 남기고 다음 틱에 다시 묻는다 — 같은 까닭이 이어지면 처음 한 번과 REPEAT_EVERY 번마다만 적는다. 요청 처리와 떨어진
  백그라운드 작업이고, 원장 쓰기는 스레드에서 한다(이벤트 루프를 막지 않는다).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)

KIND = "delib_batch"
CURSOR = "delib_batch_finished"
PATH = "/deliberate/batch/finished"
PAGE_LIMIT = 100          # 엔진 FINISHED_LIMIT_DEFAULT(상한 500). 2 이상이어야 한다 — 꽉 찬 쪽마다 경계의 묶음 하나가 다음 쪽 첫 줄로 되돌아온다
PAGES_MAX = 5             # 한 틱에 넘기는 쪽 수 — 남으면 다음 틱이 커서부터 잇는다
TIMEOUT_S = 15.0
REPEAT_EVERY = 60         # 같은 실패가 이어질 때 다시 적는 간격(틱 수 — 기본 60초면 한 시간에 한 번)
FINISHED = ("done", "stopped", "failed")
_TITLE = {"done": "심의 묶음 끝남", "stopped": "심의 묶음 멈춤", "failed": "심의 묶음 실패"}
_HTTP_WHY = {
    401: "공유 비밀(GATEWAY_SHARED_TOKEN)이 에이전트 서버의 것과 다르다(HTTP 401)",
    403: "에이전트 서버가 서비스 호출로 받지 않았다(HTTP 403)",
    404: "에이전트 서버가 끝난 묶음 창구를 모른다(HTTP 404) — 심의 묶음(DL-02) 전의 판이다",
    405: "에이전트 서버가 끝난 묶음 창구를 모른다(HTTP 405) — 심의 묶음(DL-02) 전의 판이다",
    422: "에이전트 서버가 물음의 꼴을 거절했다(HTTP 422)",
    503: "에이전트 서버에 공유 비밀이 없다(HTTP 503)",
}


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def owner_of(raw) -> str:
    """엔진의 owner → 포털 원장의 이메일 꼴(퍼센트 인코딩을 풀고 소문자 — 엔진 delib_jobs._norm 과 같다)."""
    return unquote(str(raw or "")).strip().lower()


def notice_of(b) -> dict | None:
    """끝난 묶음 한 줄 → 알림 칸(user_email · title · line · source_id · created_at). 꼴이 다르면 None."""
    if not isinstance(b, dict):
        return None
    bid, status = b.get("batch_id"), b.get("status")
    if not isinstance(bid, str) or not bid.strip() or status not in FINISHED:
        return None
    name = str(b.get("name") or "").strip() or bid
    line = str(b.get("notice") or "").strip()
    if not line:
        c = b.get("counts") if isinstance(b.get("counts"), dict) else {}
        line = (f"끝남 {_int(c.get('done'))} · 건너뜀 {_int(c.get('skipped'))} · 실패 {_int(c.get('failed'))} · "
                f"멈춤 {_int(c.get('stopped'))}.")
    fin, now = b.get("finished_at"), time.time()
    at = int(min(float(fin), now)) if isinstance(fin, (int, float)) and not isinstance(fin, bool) and fin > 0 else int(now)
    return {"user_email": owner_of(b.get("owner")), "title": f"{_TITLE[status]} — {name}", "line": line, "source_id": bid.strip(),
            "created_at": at}


def _write_page(store, users, batches: list) -> dict:
    """한 쪽의 묶음 → 알림(스레드에서 부른다). 셈 {written, already, no_account, bad}."""
    n = {"written": 0, "already": 0, "no_account": 0, "bad": 0}
    for b in batches:
        f = notice_of(b)
        if f is None:
            n["bad"] += 1
            continue
        if "@" not in f["user_email"] or users is None or users.get(f["user_email"]) is None:
            n["no_account"] += 1
            continue
        try:
            added = store.add(kind=KIND, **f)
        except ValueError:      # 다듬고 나니 빈 원천 id 따위 — 한 줄의 꼴 때문에 쪽 전체가 멈춰 커서가 영영 못 넘어가지 않게 그 줄만 센다
            n["bad"] += 1
            continue
        n["written" if added else "already"] += 1
    return n


async def tick(app, settings, *, client: httpx.AsyncClient | None = None) -> dict:
    """한 번 당긴다 → {written, already, no_account, bad, pages, since} 또는 {error: 까닭, …}. 예외를 내지 않는다(원장 쓰기의 예외만 위로 간다)."""
    store, users = getattr(app.state, "notice_store", None), getattr(app.state, "user_store", None)
    tok, base = settings.gateway_shared_token, (settings.agent_server_url or "").rstrip("/")
    if store is None:
        return {"error": "알림 원장이 열리지 않았다"}
    if not tok:
        return {"error": "공유 비밀(GATEWAY_SHARED_TOKEN)이 없어 에이전트 서버의 끝난 묶음 창구를 부르지 않는다"}
    if not base:
        return {"error": "에이전트 서버 주소(AGENT_SERVER_URL)가 없다"}
    since = await asyncio.to_thread(store.cursor, CURSOR)
    total = {"written": 0, "already": 0, "no_account": 0, "bad": 0}
    out: dict = {}
    own = client is None
    cli = client or httpx.AsyncClient(timeout=TIMEOUT_S)
    pages = 0
    try:
        for _ in range(PAGES_MAX):
            sent = since
            try:
                r = await cli.post(f"{base}{PATH}", json={"since": sent, "limit": PAGE_LIMIT},
                                   headers={"Authorization": f"Bearer {tok}"})
            except httpx.HTTPError as exc:
                out = {"error": f"에이전트 서버에 닿지 못했다({type(exc).__name__})"}
                break
            if r.status_code != 200:
                out = {"error": _HTTP_WHY.get(r.status_code, f"에이전트 서버 답이 HTTP {r.status_code} 이다")}
                break
            try:
                data = r.json()
            except ValueError:
                data = None
            batches = data.get("batches") if isinstance(data, dict) else None
            nxt = data.get("next_since") if isinstance(data, dict) else None
            if not isinstance(batches, list) or isinstance(nxt, bool) or not isinstance(nxt, (int, float)):
                out = {"error": "에이전트 서버 답의 꼴이 다르다(batches · next_since 가 없다)"}
                break
            pages += 1
            got = await asyncio.to_thread(_write_page, store, users, batches)
            for k, v in got.items():
                total[k] += v
            since = await asyncio.to_thread(store.advance, CURSOR, float(nxt))     # 알림을 쓴 뒤에 — 앞으로만 간다
            if len(batches) < PAGE_LIMIT:
                break                                       # 다 읽었다(경계의 묶음 하나는 다음 틱에 다시 나온다 — 이미 있다)
            if float(nxt) <= sent:
                # 꽉 찬 쪽이 모두 since 와 같은 끝난 시각 — 같은 since 로는 같은 쪽만 온다. 조용히 돌지 않고 까닭을 남긴다.
                out = {"error": f"꽉 찬 한 쪽({PAGE_LIMIT}개)이 모두 같은 끝난 시각이라 커서가 넘어가지 못한다 — PAGE_LIMIT 을 늘려야 한다"}
                break
    finally:
        if own:
            await cli.aclose()
    return {**out, **total, "pages": pages, "since": since}


async def run(app, settings, every: float) -> None:
    """every 초마다 tick — 끌 때(cancel)까지. 실패는 까닭이 바뀔 때와 REPEAT_EVERY 번마다 경고로 적는다."""
    last_err, fails = None, 0
    while True:
        await asyncio.sleep(every)
        try:
            out = await tick(app, settings)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — 한 틱의 실패가 작업을 죽이지 않는다(다음 틱에 다시 한다)
            out = {"error": f"알림 원장에 쓰지 못했다({type(exc).__name__}: {exc})"}
        err = out.get("error")
        if err:
            fails += 1
            if err != last_err or fails % REPEAT_EVERY == 0:
                logger.warning("심의 묶음 알림 — 끝난 묶음을 당기지 못했다(%d번째 · 다음 틱에 다시 묻는다): %s", fails, err)
        else:
            if last_err:
                logger.warning("심의 묶음 알림 — 에이전트 서버에 다시 닿았다(%d번 실패 뒤)", fails)
            fails = 0
            if out.get("written") or out.get("no_account") or out.get("bad"):
                logger.info("심의 묶음 알림 — 남김 %d · 이미 있음 %d · 포털 계정 아님 %d · 꼴이 다름 %d", out.get("written", 0),
                            out.get("already", 0), out.get("no_account", 0), out.get("bad", 0))
        last_err = err
        app.state.notice_poll_last = {**out, "at": time.time()}


def start(app, settings) -> asyncio.Task | None:
    """기동 때 — 손잡이(DELIB_BATCH_NOTICE_S)가 0 이하거나 원장이 없으면 띄우지 않는다(None)."""
    every = int(getattr(settings, "delib_batch_notice_s", 0) or 0)
    if every <= 0:
        logger.info("심의 묶음 알림 — DELIB_BATCH_NOTICE_S=0 이라 끝난 묶음을 당기지 않는다")
        return None
    if getattr(app.state, "notice_store", None) is None:
        logger.warning("심의 묶음 알림 — 알림 원장이 열리지 않아 당기기를 띄우지 않는다")
        return None
    return asyncio.get_running_loop().create_task(run(app, settings, float(every)), name="delib-batch-notice")


async def stop(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
