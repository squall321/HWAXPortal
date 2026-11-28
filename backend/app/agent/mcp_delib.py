# MCP 로 연 심의(엔진 잡)를 포털로 — 끝난 잡을 주인의 대화로 당기기(WD-03) · 진행 카드 상태(WD-13)
"""docs/request-1125 WD-03 · WD-13 의 포털 몫. 엔진 쪽은 HWAXAgentServer(c27c13e · 3c6a54d)다.

- **당기기(WD-03)** — 엔진이 밀지 않고 포털이 읽는다(과제 인사이트 PG-9 · 심의 묶음 알림과 같은 까닭 — 어느 쪽이 내려가 있어도 다음 읽기에 따라잡는다).
  `GET /delib/conversations?since&limit` 를 공유 비밀(GATEWAY_SHARED_TOKEN)만 실어 부른다(사람 신원 머리를 실으면 엔진이 403). 커서는 대화 저장소 안의
  표(conv_cursors)에 남고 앞으로만 간다. 엔진은 경계의 잡을 다음 부름에 다시 내므로 잡 id 로 한 번만 쓴다(conv_store.ingest_mcp_delib — 같은 판은
  already, 제자리 이어하기로 더 늦게 끝난 판은 그 잡의 줄만 바꾼다). 같은 주인의 같은 뿌리 잡(이어하기 사슬의 맨 앞)은 한 대화에 붙는다.
  주인은 포털 계정(users 원장의 이메일)일 때만 쓴다(심의 묶음 알림과 같다). 대화 주인 키(sub)는 그 이메일로 낸 사람 PAT 의 sub(MCP 잡은 그 PAT 로
  열렸다), 없으면 이메일이다(SAML · 로컬 · mock 박스는 sub 가 이메일이다). 첫 당기기는 커서 0 이라 지난 MCP 심의도 다 들어온다 — 보름 전 심의를
  대화 목록 · 대화 검색에서 찾게(WD-08 의 '확인'). 대화 시각은 잡이 끝난 때다(오늘로 몰리지 않는다).
- **진행 카드(WD-13)** — 엔진에 HTTP 창구가 없는 읽기라 그 사람의 챗 PAT 로 게이트웨이 도구를 부른다(deliberate_status — 엔진이 그 사람 기준으로
  볼 수 있는 잡만 준다). 챗 중계는 SSE job_card 를 card_pointer 로 걸러 답 meta.job_cards 로 남긴다. MCP 쪽 나누기(mcp_pages.paged)로 나뉜 답은 join_pages 로 이어 원래 응답으로 만든다.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, Depends, Request

from app.agent import upload as _upload
from app.agent.subject import subject_of
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, principal_pat_or_session

logger = logging.getLogger(__name__)

CONTRACT = "delib-conversations/1"      # 에이전트 서버 delib_jobs.CONV_CONTRACT 와 같아야 한다(시험이 견준다)
PATH = "/delib/conversations"
CURSOR = "mcp_delib_conversations"
PAGE_LIMIT = 20                         # 엔진 CONV_LIMIT_MAX(50) 안 — 항목마다 발언 전문이 실린다
PAGES_MAX = 5                           # 한 틱에 넘기는 쪽 — 남으면 다음 틱이 커서부터 잇는다
TIMEOUT_S = 30.0
REPEAT_EVERY = 60
KICK_MIN_S = 5.0                        # 진행 조회가 끝난 잡을 보고 당기기를 앞당길 때의 최소 간격
TITLE_MAX = 80
EVIDENCE_MAX = 100
READ_TIMEOUT_S = 60.0
PARTS_MAX = 40                          # 쪽으로 나뉜 답을 받을 때의 상한(쪽 25,000자 — 백만 자)
JOB_ID_RE = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_JOB_ID = re.compile(JOB_ID_RE)
_END = ("done", "error", "cancelled", "interrupted", "failed")
_HTTP_WHY = {
    401: "공유 비밀(GATEWAY_SHARED_TOKEN)이 에이전트 서버의 것과 다르다(HTTP 401)",
    403: "에이전트 서버가 서비스 호출로 받지 않았다(HTTP 403)",
    404: "에이전트 서버가 대화 거리 창구를 모른다(HTTP 404) — WD-03(c27c13e) 전의 판이다",
    405: "에이전트 서버가 대화 거리 창구를 모른다(HTTP 405) — WD-03(c27c13e) 전의 판이다",
    422: "에이전트 서버가 물음의 꼴을 거절했다(HTTP 422)",
    503: "에이전트 서버에 공유 비밀이 없다(HTTP 503)",
}


# ── 쪽 잇기 — mcp_pages.paged 의 쪽들 → 원래 응답 ─────────────────────────────────────────────────────────────────
class PageJoinError(ValueError):
    pass


def _merge(a, b, path: str, pieces: dict):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            p = f"{path}.{k}" if path else str(k)
            out[k] = _merge(out[k], v, p, pieces) if k in out else v
        return out
    if isinstance(a, list) and isinstance(b, list):
        pc = pieces.get(path)
        if pc is None:
            return b                            # 쪽마다 되풀이하는 칸(나뉜 목록은 두 쪽 모두 pieces 에 있다)
        start = int(pc["from"])
        if start == len(a):
            return a + b
        if start == len(a) - 1 and b:          # 앞 쪽의 끝 항목을 이 쪽이 이어 싣는다 — 한 항목이다
            return a[:-1] + [_merge(a[-1], b[0], f"{path}[{start}]", pieces)] + b[1:]
        raise PageJoinError(f"{path} 목록이 이어지지 않는다(받은 {len(a)}개 · 이 쪽 시작 {start})")
    if isinstance(a, str) and isinstance(b, str):
        pc = pieces.get(path)
        if pc is None:
            return b                            # 쪽마다 되풀이하는 칸
        if int(pc["from"]) == len(a):
            return a + b
        raise PageJoinError(f"{path} 글이 이어지지 않는다(받은 {len(a)}자 · 이 쪽 시작 {pc['from']}) — 쪽을 받는 사이에 바뀌었다")
    return b


def join_pages(pages: list[dict]) -> dict:
    """쪽들(1쪽부터 차례대로) → 원래 응답. 쪽 안내(page)는 뗀다. 한 쪽이면 그대로."""
    acc: dict = {}
    for pg in pages:
        meta = pg.get("page") if isinstance(pg.get("page"), dict) else {}
        pieces = {str(p.get("path")): p for p in (meta.get("pieces") or []) if isinstance(p, dict)}
        acc = _merge(acc, {k: v for k, v in pg.items() if k != "page"}, "", pieces)
    return acc


async def gateway_read(settings: Settings, pat: str, tool: str, args: dict) -> dict:
    """그 사람의 PAT 로 게이트웨이 도구를 부르고, 쪽으로 나뉘었으면 끝 쪽까지 받아 잇는다. 실패는 AuthError(502)."""
    pages: list[dict] = []
    part = 1
    while True:
        got = await _upload.mcp_call(settings.mcp_gateway_url, pat, tool, {**args, **({"part": part} if part > 1 else {})},
                                     timeout=READ_TIMEOUT_S)
        pages.append(got)
        nxt = (got.get("page") or {}).get("next") if isinstance(got.get("page"), dict) else None
        if not isinstance(nxt, dict):
            break
        part += 1
        if part > PARTS_MAX:
            raise AuthError(f"{tool}: 답이 {PARTS_MAX}쪽을 넘는다 — 받지 않았다", status_code=502)
    try:
        return join_pages(pages)
    except PageJoinError as exc:
        raise AuthError(f"{tool}: 쪽을 잇지 못했다 — {exc}", status_code=502) from exc


# ── 당기기(WD-03) ────────────────────────────────────────────────────────────────────────────────────────────
def owner_of(raw) -> str:
    """엔진의 user → 포털 원장의 이메일 꼴(퍼센트 인코딩을 풀고 소문자 — 엔진 delib_jobs._norm 과 같다)."""
    return unquote(str(raw or "")).strip().lower()


def owner_sub_for(app, email: str) -> str | None:
    """포털 계정이면 그 사람의 대화 주인 키 — 그 이메일로 낸 사람 PAT 의 sub, 없으면 이메일(SAML · 로컬 · mock 은 sub 가 이메일). 계정이 아니면 None."""
    users = getattr(app.state, "user_store", None)
    if "@" not in email or users is None or users.get(email) is None:
        return None
    tokens = getattr(app.state, "token_store", None)
    return (tokens.sub_for_email(email) if tokens is not None else None) or email


def _title(question: str) -> str:
    first = next((ln.strip() for ln in str(question or "").splitlines() if ln.strip()), "")
    return (first[:TITLE_MAX] + ("…" if len(first) > TITLE_MAX else "")) or "MCP 심의"


def _rid(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else None


def decision_meta(meta: dict) -> dict:
    """엔진 항목의 meta → 결정문(assistant) 줄의 meta — 화면이 아는 칸으로(conversations.api.ts serverMessagesToLocal).
    mcp_delib 은 이어하기 · 진행 조회의 열쇠, delib_outcome 은 결과 카드, subject 는 확인된 주제, delib_evidence 는 근거 표지(본문 없이 — 이어하기는
    엔진이 참조를 다시 푼다)."""
    keep = ("job_id", "root_job_id", "job", "chair_template", "status", "continues", "report_id", "report_url")
    mcp = {k: meta[k] for k in keep if meta.get(k) not in (None, "")}
    out: dict = {"mcp_delib": mcp}
    rid = _rid(meta.get("report_id"))
    if rid:
        url = meta.get("report_url") if isinstance(meta.get("report_url"), str) else ""
        out["delib_outcome"] = {"report_id": rid, **({"url": url[:500]} if url else {}), "title": ""}
    subj = subject_of(meta.get("subject"))
    if subj is not None:
        out["subject"] = subj
    ev = []
    for e in (meta.get("evidence") or [])[:EVIDENCE_MAX]:
        if not isinstance(e, dict):
            continue
        name = str(e.get("tool") or e.get("source") or "근거")[:200]
        key = f" · {str(e['key'])[:120]}" if e.get("key") else ""
        chars = int(e.get("chars") or 0) if isinstance(e.get("chars"), int) else 0
        ev.append({"source": str(e.get("source") or name)[:200], "text": f"{name}{key} — {chars:,}자(본문은 엔진 원장에 — 이어하기가 참조를 다시 푼다)",
                   "included": True})
    if ev:
        out["delib_evidence"] = ev
    return out


def messages_of(item: dict) -> list[dict] | None:
    """엔진의 대화 거리 하나 → 대화 메시지(화두 user → 좌석 persona → 결정문 assistant). 꼴이 다르면 None.
    결정문이 없는 잡(오류 · 접힘 · 끊김)은 끝 줄에 상태를 적고 delib_undecided 로 단다 — 화면이 그 글을 결정문으로 읽지 않는다."""
    jid, rows = item.get("job_id"), item.get("rows")
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    if not isinstance(jid, str) or not _JOB_ID.match(jid) or not isinstance(rows, list):
        return None
    dmeta = decision_meta({**meta, "job_id": jid})
    out: list[dict] = []
    decided = False
    for r in rows:
        if not isinstance(r, dict):
            continue
        kind, content = r.get("kind"), str(r.get("content") or "")
        if kind == "question":
            out.append({"role": "user", "content": content or str(item.get("question") or ""), "meta": {"mcp_job": jid}})
        elif kind == "seat" and content:
            rnd = r.get("round")
            out.append({"role": "persona", "persona": (str(r.get("persona") or "") or "?")[:120],
                        "round": rnd if isinstance(rnd, int) and not isinstance(rnd, bool) else None, "content": content})
        elif kind == "decision" and content:
            decided = True
            out.append({"role": "assistant", "content": content, "meta": dmeta})
    if not out:
        return None
    if not decided:
        st = str(meta.get("status") or "?")
        out.append({"role": "assistant", "content": f"엔진 잡 {jid} 이 결정문 없이 끝났습니다(상태 {st}).",
                    "meta": {**dmeta, "delib_undecided": True}})
    return out


def _write_page(app, items: list) -> dict:
    """한 쪽의 항목 → 대화(스레드에서 부른다). 셈 {new, appended, replaced, already, deleted, no_account, bad}."""
    store = app.state.conv_store
    n = dict.fromkeys(("new", "appended", "replaced", "already", "deleted", "no_account", "bad"), 0)
    for it in items:
        msgs = messages_of(it) if isinstance(it, dict) else None
        if msgs is None:
            n["bad"] += 1
            continue
        sub = owner_sub_for(app, owner_of(it.get("user")))
        if sub is None:
            n["no_account"] += 1
            continue
        root = str(it.get("root_job_id") or it["job_id"])[:128]
        fin = it.get("finished_at")
        how = store.ingest_mcp_delib(owner_sub=sub, job_id=it["job_id"], root_job_id=root, title=_title(it.get("question")),
                                     messages=msgs, finished_at=float(fin) if isinstance(fin, (int, float)) and not isinstance(fin, bool) else 0.0)
        n[how] += 1
    return n


_SYNC: dict = {"loop": None, "lock": None, "at": 0.0}


def _lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    if _SYNC["loop"] is not loop:
        _SYNC["loop"], _SYNC["lock"] = loop, asyncio.Lock()
    return _SYNC["lock"]


async def tick(app, settings, *, client: httpx.AsyncClient | None = None) -> dict:
    """한 번 당긴다 → 셈 + {pages, since} 또는 {error, …}. 다른 틱이 도는 중이면 {skipped: busy}. 원장 쓰기의 예외만 위로 간다."""
    lock = _lock()
    if lock.locked():
        return {"skipped": "busy"}
    async with lock:
        _SYNC["at"] = time.monotonic()
        return await _tick(app, settings, client)


async def _tick(app, settings, client) -> dict:
    store = getattr(app.state, "conv_store", None)
    tok, base = settings.gateway_shared_token, (settings.agent_server_url or "").rstrip("/")
    if store is None:
        return {"error": "대화 저장소가 열리지 않았다"}
    if not tok:
        return {"error": "공유 비밀(GATEWAY_SHARED_TOKEN)이 없어 에이전트 서버의 대화 거리 창구를 부르지 않는다"}
    if not base:
        return {"error": "에이전트 서버 주소(AGENT_SERVER_URL)가 없다"}
    since = await asyncio.to_thread(store.cursor, CURSOR)
    total = dict.fromkeys(("new", "appended", "replaced", "already", "deleted", "no_account", "bad"), 0)
    out: dict = {}
    own = client is None
    cli = client or httpx.AsyncClient(timeout=TIMEOUT_S)
    pages = 0
    try:
        for _ in range(PAGES_MAX):
            sent = since
            try:
                r = await cli.get(f"{base}{PATH}", params={"since": sent, "limit": PAGE_LIMIT}, headers={"Authorization": f"Bearer {tok}"})
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
            items = data.get("items") if isinstance(data, dict) else None
            nxt = data.get("next_since") if isinstance(data, dict) else None
            if not isinstance(data, dict) or data.get("contract") != CONTRACT:
                out = {"error": f"에이전트 서버 답의 계약이 다르다({str((data or {}).get('contract') if isinstance(data, dict) else None)[:40]}) "
                                f"— {CONTRACT} 를 기다린다"}
                break
            if not isinstance(items, list) or isinstance(nxt, bool) or not isinstance(nxt, (int, float)):
                out = {"error": "에이전트 서버 답의 꼴이 다르다(items · next_since 가 없다)"}
                break
            pages += 1
            got = await asyncio.to_thread(_write_page, app, items)
            for k, v in got.items():
                total[k] += v
            since = await asyncio.to_thread(store.advance, CURSOR, float(nxt))   # 대화를 쓴 뒤에 — 앞으로만 간다
            if data.get("complete") or len(items) < PAGE_LIMIT:
                break
            if float(nxt) <= sent:
                out = {"error": f"꽉 찬 한 쪽({PAGE_LIMIT}개)이 모두 같은 끝난 시각이라 커서가 넘어가지 못한다 — PAGE_LIMIT 을 늘려야 한다"}
                break
    finally:
        if own:
            await cli.aclose()
    return {**out, **total, "pages": pages, "since": since}


async def kick(app, settings) -> None:
    """진행 조회가 끝난 잡을 보았을 때 — 당기기를 앞당긴다(KICK_MIN_S 안에 돈 틱이 있거나 도는 중이면 하지 않는다). 손잡이가 0 이면 하지 않는다."""
    if int(getattr(settings, "delib_conv_sync_s", 0) or 0) <= 0:
        return
    if time.monotonic() - float(_SYNC["at"] or 0) < KICK_MIN_S:
        return
    try:
        out = await tick(app, settings)
    except Exception:  # noqa: BLE001 — 조회를 막지 않는다
        logger.warning("MCP 심의 대화 — 앞당긴 당기기가 실패했다", exc_info=True)
        return
    app.state.delib_conv_last = {**out, "at": time.time()}


async def run(app, settings, every: float) -> None:
    last_err, fails = None, 0
    while True:
        await asyncio.sleep(every)
        try:
            out = await tick(app, settings)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — 한 틱의 실패가 작업을 죽이지 않는다
            out = {"error": f"대화 저장소에 쓰지 못했다({type(exc).__name__}: {exc})"}
        if out.get("skipped"):
            continue
        err = out.get("error")
        if err:
            fails += 1
            if err != last_err or fails % REPEAT_EVERY == 0:
                logger.warning("MCP 심의 대화 — 끝난 엔진 잡을 당기지 못했다(%d번째 · 다음 틱에 다시 묻는다): %s", fails, err)
        else:
            if last_err:
                logger.warning("MCP 심의 대화 — 에이전트 서버에 다시 닿았다(%d번 실패 뒤)", fails)
            fails = 0
            if any(out.get(k) for k in ("new", "appended", "replaced", "no_account", "bad")):
                logger.info("MCP 심의 대화 — 새 대화 %d · 붙임 %d · 바꿈 %d · 이미 %d · 지운 대화 %d · 포털 계정 아님 %d · 꼴이 다름 %d",
                            *(out.get(k, 0) for k in ("new", "appended", "replaced", "already", "deleted", "no_account", "bad")))
        last_err = err
        app.state.delib_conv_last = {**out, "at": time.time()}


def start(app, settings) -> asyncio.Task | None:
    every = int(getattr(settings, "delib_conv_sync_s", 0) or 0)
    if every <= 0:
        logger.info("MCP 심의 대화 — DELIB_CONV_SYNC_S=0 이라 끝난 엔진 잡을 당기지 않는다")
        return None
    if getattr(app.state, "conv_store", None) is None:
        logger.warning("MCP 심의 대화 — 대화 저장소가 열리지 않아 당기기를 띄우지 않는다")
        return None
    return asyncio.get_running_loop().create_task(run(app, settings, float(every)), name="mcp-delib-conversations")


async def stop(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


# ── 창구 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/agent/engine-delib", tags=["agent"])


def _pat(request: Request, settings: Settings, principal: Principal) -> str:
    from app.agent.routes import _chat_user_pat  # 늦게 — routes 가 크다(순환 아님)
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다 — 다시 로그인한 뒤 시도하세요", status_code=401)
    return pat


def _job_id(v: str) -> str:
    s = (v or "").strip()
    if not _JOB_ID.match(s):
        raise AuthError("잡 id 의 꼴이 아닙니다", status_code=422)
    return s


_LINK = re.compile(r"(?:https?://[^\s\"'<>\\]{1,490}|/(?!/)[^\s\"'<>\\]{0,498})")


def card_pointer(data) -> dict | None:
    """SSE job_card(에이전트 서버 _confirm_job_card — WD-13)의 한 사건 → 서버 사본(답 meta.job_cards)에 남길 꼴. 아는 칸만 · 길이 상한 안. 다시 묻기는
    심의 잡의 deliberate_status 만 남긴다(다른 도구를 화면이 부르게 하지 않는다). 링크는 http(s) · 포털 안 경로만. 잡 id 가 없으면 None."""
    if not isinstance(data, dict):
        return None
    ids = [str(x)[:128] for x in (data.get("job_ids") or []) if isinstance(x, (str, int)) and not isinstance(x, bool) and _JOB_ID.match(str(x))][:5]
    if not ids:
        return None
    kind = "deliberation" if data.get("kind") == "deliberation" else "job"
    prog = data.get("progress")
    out = {"kind": kind, "job_ids": ids, "tool": str(data.get("tool") or "")[:120], "phase": "end" if data.get("phase") == "end" else "run",
           "state": str(data.get("state") or "")[:40], "progress": prog if isinstance(prog, int) and not isinstance(prog, bool) and 0 <= prog <= 100 else None,
           "detail": str(data.get("detail") or "")[:200]}
    for k, cap in (("call", 80), ("app", 80), ("continued_from", 128)):
        if isinstance(data.get(k), str) and data[k]:
            out[k] = data[k][:cap]
    link = data.get("link")
    if isinstance(link, str) and _LINK.fullmatch(link.strip()):
        out["link"] = link.strip()
    sc = data.get("status_call")
    if kind == "deliberation" and isinstance(sc, dict) and sc.get("tool") == "deliberate_status":
        jid = (sc.get("args") or {}).get("job_id") if isinstance(sc.get("args"), dict) else None
        if isinstance(jid, str) and jid in ids:
            out["status_call"] = {"tool": "deliberate_status", "args": {"job_id": jid}}
    return out


def _status_view(d: dict) -> dict:
    st = str(d.get("status") or "")
    q = d.get("queue") if isinstance(d.get("queue"), dict) else None
    return {"job_id": d.get("job_id"), "status": st, "phase": "end" if st in _END else "run",
            "stage": d.get("stage"), "step": str(d.get("step") or d.get("last_step") or "")[:200],
            "round": d.get("round"), "total_rounds": d.get("total_rounds"), "report_id": _rid(d.get("report_id")),
            "error": str(d.get("error") or "")[:400] or None, "finishing": bool(d.get("finishing")),
            **({"queue": {k: q.get(k) for k in ("position", "ahead", "length") if k in q}} if q else {})}


@router.get("/status/{job_id}")
async def job_status(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """진행 카드(WD-13)의 다시 묻기 — 그 사람의 PAT 로 deliberate_status(brief). 끝났으면 당기기를 앞당겨 그 사람의 대화에 들었는지(conversation_id)도 준다."""
    ensure(principal, "feat:deliberation")
    jid = _job_id(job_id)
    d = await gateway_read(settings, _pat(request, settings, principal), "deliberate_status", {"job_id": jid, "brief": True})
    out = _status_view({**d, "job_id": d.get("job_id") or jid})
    if out["phase"] == "end":
        store = request.app.state.conv_store
        cid = await asyncio.to_thread(store.mcp_delib_conversation, principal.subject, jid)
        if cid is None:
            await kick(request.app, settings)
            cid = await asyncio.to_thread(store.mcp_delib_conversation, principal.subject, jid)
        out["conversation_id"] = cid
    return out
