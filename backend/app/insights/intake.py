# 과제 인사이트 들이기 셋 — 웹 중계 · MCP 잡 당기기 · Claude 워크플로 대화 저장(docs/project-insight-graph contracts §5)
"""카드는 확인된 주제만(draft), 주장으로 남은 주제는 주인의 기다림 줄(waiting), 주제가 없거나 none 이면 들이지 않는다(PLAN §3.4). 리스크 심사가
낳은 심의(의장 risk-review* · started_by=app · 대화 kind risk-review)는 어느 길로도 들이지 않는다(PLAN §3.1 — 리스크 판정은 리스크 앱 한 곳에만).
범위는 들일 때 늘 [user:<주인>] 이다 — 넓히기는 주인이 포털에서 확인할 때만이다(사용자 결정 11-02 · PLAN §6.3). MCP 잡의 주인 · 소속은 그때
게이트웨이가 실은 값(자칭)이라 소속은 넓힐 때 쓰지 않는다."""
from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import unquote

import httpx

from app.agent.subject import subject_of
from app.insights import cards as C

logger = logging.getLogger(__name__)

AGENT_CONTRACT = "insight-cards/1"       # 에이전트 서버 delib_jobs.INSIGHT_CONTRACT 와 같아야 한다(시험이 견준다)
SYNC_OVERLAP_S = 600                     # 커서보다 이만큼 앞부터 다시 읽는다 — 늦게 쓰인 원장을 놓치지 않게(같은 id 는 하나다)
SYNC_LIMIT = 200
SYNC_PAGES_MAX = 5
SYNC_TIMEOUT_S = 15.0
CONFIRM_TIMEOUT_S = 40.0                 # 에이전트의 풀이 기한(RESOLVE_TIMEOUT_S 20초) 바깥
_CALLS_MAX, _ARGS_MAX, _NAMES_MAX = 60, 1200, 200


def _s(v, cap: int) -> str:
    return v[:cap] if isinstance(v, str) else ""


def _card_fields(raw: dict, *, extra_refs: tuple = ()) -> dict:
    """엔진의 카드 거리 → 원장의 card 칸(아는 칸만 · 길이 상한 안). 주장은 따로 둔다."""
    t = raw.get("tally") if isinstance(raw.get("tally"), dict) else {}
    calls = []
    for c in (raw.get("calls") or [])[:_CALLS_MAX]:
        if isinstance(c, dict) and isinstance(c.get("tool"), str):
            calls.append({"ref": _s(c.get("ref"), 40), "tool": _s(c.get("tool"), _NAMES_MAX), "app": _s(c.get("app"), 80) or None,
                          "args": _s(c.get("args"), _ARGS_MAX), "sha256": _s(c.get("sha256"), 64), "ok": bool(c.get("ok"))})
    names = lambda k: [_s(x, _NAMES_MAX) for x in (raw.get(k) or [])[:_NAMES_MAX] if isinstance(x, str) and x]  # noqa: E731
    rid = raw.get("report_id")
    return {"tally": {k: int(t.get(k) or 0) for k in ("agree", "conditional", "oppose", "abstain")},
            "report_id": rid if isinstance(rid, (int, str)) and not isinstance(rid, bool) else None,
            "report_url": _s(raw.get("report_url"), 500) or None, "model": _s(raw.get("model"), 120),
            "calls": calls, "tools": names("tools"), "apps": names("apps"), "apps_unknown": names("apps_unknown"),
            "refs": [*extra_refs, *names("refs")]}


def _row(*, cid: str, path: str, source_id: str, stage: str, owner_email: str, owner_sub: str | None, subject: dict,
         claim: str, claim_from: str, card: dict, continues: str | None = None) -> dict:
    confirmed = subject.get("sp_state") == "confirmed"
    rnd = C.norm_round(subject.get("round") or "")
    return {"id": cid, "path": path, "source_id": source_id, "stage": stage or "default", "owner_email": owner_email.lower(),
            "owner_sub": owner_sub, "status": "draft" if confirmed else "waiting",
            "sp_task": subject.get("sp_task") if confirmed else None, "round": rnd, "round_by": subject.get("round_by") if rnd else None,
            "subject": subject, "claim": C._clip(claim), "claim_from": claim_from if claim else "", "card": card,
            "scope": [f"user:{owner_email.lower()}"], "continues": continues}


# ── 웹 — /agent/chat 중계가 답을 남길 때 ─────────────────────────────────────────────────────────────────────────────
def from_relay(store, *, owner_email: str, owner_sub: str, cid: str, run_key: str, subject: dict | None, cards: list,
               chair_template: str | None, started_by: str | None) -> list[str]:
    """웹 심의의 카드 거리 → 원장(들인 id). 주제는 중계가 받은 에이전트 사건(delib kind=subject)뿐이다 — 브라우저가 보낸 값이 아니다."""
    if store is None or not (cid and run_key and owner_email) or not isinstance(subject, dict):
        return []
    if subject.get("sp_state") not in C.SP_STATES_CARD or C.risk_family(chair_template, started_by):
        return []
    by_stage: dict = {}
    for c in cards or []:
        if isinstance(c, dict):
            by_stage[str(c.get("stage") or "default")[:40]] = c       # 같은 단을 다시 냈으면 뒤엣것
    out = []
    for stage, c in by_stage.items():
        if C.risk_family(stage):
            continue
        row = _row(cid=C.web_id(cid, run_key, stage), path="web", source_id=cid, stage=stage, owner_email=owner_email,
                   owner_sub=owner_sub or None, subject=subject, claim=_s(c.get("claim"), 4000), claim_from=_s(c.get("claim_from"), 20),
                   card=_card_fields(c))
        if store.ingest(row):
            out.append(row["id"])
    return out


# ── MCP 잡 — 에이전트 서버의 공유 비밀 창구를 읽을 때 당긴다(PG-9) ──────────────────────────────────────────────────────────
_SYNC = {"at": 0.0, "lock": None, "loop": None, "last": None}


def _lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    if _SYNC["loop"] is not loop:
        _SYNC["loop"], _SYNC["lock"] = loop, asyncio.Lock()
    return _SYNC["lock"]


def ingest_jobs(store, items: list) -> int:
    """창구의 항목들 → 원장(들인 카드 수). 주인은 잡 원장의 user(퍼센트 인코딩을 푼 소문자 — 자칭), 주제는 잡 원장의 것."""
    n = 0
    for it in items or []:
        if not isinstance(it, dict) or not isinstance(it.get("job_id"), str):
            continue
        owner = unquote(str(it.get("user") or "")).strip().lower()
        subj = subject_of(it.get("subject"))
        if "@" not in owner or subj is None or subj["sp_state"] not in C.SP_STATES_CARD:
            continue
        if C.risk_family(it.get("chair_template"), it.get("started_by")):
            continue
        jid, prev = it["job_id"][:120], str(it.get("continues") or "")[:120]
        for c in it.get("cards") or []:
            if not isinstance(c, dict):
                continue
            stage = str(c.get("stage") or "default")[:40]
            if C.risk_family(stage):
                continue
            cont = None
            if prev:
                pid = C.job_card_id(prev, stage)
                cont = pid if store.get(pid) is not None else f"delib:{prev}"
            row = _row(cid=C.job_card_id(jid, stage), path="mcp-job", source_id=jid, stage=stage, owner_email=owner, owner_sub=None,
                       subject=subj, claim=_s(c.get("claim"), 4000), claim_from=_s(c.get("claim_from"), 20),
                       card=_card_fields(c, extra_refs=(f"delib:{jid}",)), continues=cont)
            if store.ingest(row):
                n += 1
    return n


async def sync_jobs(app, settings, *, force: bool = False) -> dict:
    """끝난 MCP 잡의 카드를 당겨 들인다 — INSIGHT_SYNC_S 초에 한 번(0 이면 끔, force 는 무시). 커서(jobs_since)보다 SYNC_OVERLAP_S 앞부터
    읽고 쪽을 넘기며 끝까지(SYNC_PAGES_MAX 쪽). 못 닿으면 까닭을 돌려주고 다음 읽기에 따라잡는다 — 읽기를 막지 않는다."""
    every = int(getattr(settings, "insight_sync_s", 0) or 0)
    if every <= 0 and not force:
        return {"skipped": "off"}
    if not force and time.monotonic() - _SYNC["at"] < every:
        return {"skipped": "recent"}
    lock = _lock()
    if lock.locked():
        return {"skipped": "busy"}
    async with lock:
        _SYNC["at"] = time.monotonic()
        store = getattr(app.state, "insight_store", None)
        tok, base = settings.gateway_shared_token, (settings.agent_server_url or "").rstrip("/")
        if store is None or not (tok and base):
            out = {"error": "인사이트 원장 · 공유 비밀(GATEWAY_SHARED_TOKEN) · 에이전트 서버 주소 가운데 없는 것이 있다"}
            _SYNC["last"] = out
            return out
        cursor = float(await asyncio.to_thread(store.meta_get, "jobs_since") or 0)
        # 앞 당기기가 쪽 상한에서 멈췄으면(jobs_partial) 겹침 없이 커서부터 잇는다 — 겹침 창 안에 쪽 상한보다 많은 항목이 있으면 매번 같은 앞쪽만
        # 다시 읽어 커서가 영영 못 넘어갔다(반대 검토 11-02 의 7). 다 따라잡으면 다음은 다시 겹쳐 읽는다(늦게 쓰인 원장을 놓치지 않게).
        partial = (await asyncio.to_thread(store.meta_get, "jobs_partial")) == "1"
        start, got = (cursor if partial else max(0.0, cursor - SYNC_OVERLAP_S)), 0
        out: dict = {}
        done = False
        for _ in range(SYNC_PAGES_MAX):
            try:
                async with httpx.AsyncClient(timeout=SYNC_TIMEOUT_S) as cli:
                    r = await cli.get(f"{base}/insights/cards", params={"since": start, "limit": SYNC_LIMIT},
                                      headers={"Authorization": f"Bearer {tok}"})
                data = r.json() if r.status_code == 200 else None
            except (httpx.HTTPError, ValueError) as exc:
                out = {"error": f"에이전트 서버에 닿지 못했다({type(exc).__name__})"}
                break
            if not isinstance(data, dict) or data.get("contract") != AGENT_CONTRACT:
                out = {"error": f"에이전트 서버 답이 다르다(HTTP {r.status_code}) — 낡았거나 공유 비밀이 다르다"}
                break
            got += await asyncio.to_thread(ingest_jobs, store, data.get("items") or [])
            nxt = float(data.get("next_since") or start)
            cursor = max(cursor, nxt)
            await asyncio.to_thread(store.meta_set, "jobs_since", repr(cursor))
            if data.get("complete") or nxt <= start:
                done = True
                break
            start = nxt
        if not out.get("error"):
            await asyncio.to_thread(store.meta_set, "jobs_partial", "0" if done else "1")
        out = {**out, "ingested": got, "since": cursor}
        if out.get("error"):
            logger.warning("과제 인사이트 — MCP 잡 카드를 당기지 못했다: %s", out["error"])
        _SYNC["last"] = out
        return out


# ── Claude 워크플로 — 포털 대화 저장(ConvCreate) 뒤 ───────────────────────────────────────────────────────────────────
def confirm_payload(*, subject: dict, principal, pat: str, chair_template: str | None) -> dict:
    """에이전트 POST /deliberate/subject/confirm 의 본문(contracts §3.2) — 그 사람의 PAT · 그룹 · 메일(웹 중계와 같은 칸)."""
    return {"subject": subject, "groups": list(principal.groups), "user_email": principal.email, "user_pat": pat,
            "chair_template": chair_template}


def confirm_reply(status: int, data) -> tuple[dict | None, str]:
    """에이전트의 답 → (주제 기록, 까닭)."""
    if status == 200 and isinstance(data, dict) and "subject" in data:
        rec = subject_of(data.get("subject"))
        return (rec, "") if rec is not None else (None, "과제가 없는 주제다 — 잇지 않는다")
    why = data.get("message") if isinstance(data, dict) else None
    return None, f"주제를 다시 풀지 못했다(에이전트 서버 HTTP {status}" + (f" — {str(why)[:200]}" if why else "") + ")"


def confirm_sync(settings, *, subject: dict, principal, pat: str, chair_template: str | None) -> tuple[dict | None, str]:
    """대화 REST(def — 스레드)에서 부른다. 못 닿으면 (None, 까닭)."""
    try:
        with httpx.Client(timeout=CONFIRM_TIMEOUT_S) as cli:
            r = cli.post(f"{settings.agent_server_url.rstrip('/')}/deliberate/subject/confirm",
                         json=confirm_payload(subject=subject, principal=principal, pat=pat, chair_template=chair_template))
        return confirm_reply(r.status_code, r.json() if "json" in r.headers.get("content-type", "") else None)
    except (httpx.HTTPError, ValueError) as exc:
        return None, f"에이전트 서버에 닿지 못했다({type(exc).__name__})"


async def confirm_async(settings, *, subject: dict, principal, pat: str, chair_template: str | None) -> tuple[dict | None, str]:
    try:
        async with httpx.AsyncClient(timeout=CONFIRM_TIMEOUT_S) as cli:
            r = await cli.post(f"{settings.agent_server_url.rstrip('/')}/deliberate/subject/confirm",
                               json=confirm_payload(subject=subject, principal=principal, pat=pat, chair_template=chair_template))
        return confirm_reply(r.status_code, r.json() if "json" in r.headers.get("content-type", "") else None)
    except (httpx.HTTPError, ValueError) as exc:
        return None, f"에이전트 서버에 닿지 못했다({type(exc).__name__})"


def from_workflow(store, settings, *, principal, pat: str | None, cid: str, kind: str, source: str, subject_raw: dict,
                  chair_template: str | None, messages: list) -> dict:
    """워크플로 대화 → 원장(ins:wf:<cid>). 답의 insight 칸 — {id, status} 또는 {skipped: 까닭}. 저장을 막지 않는다(부르는 쪽이 예외를 삼킨다)."""
    if store is None:
        return {"skipped": "인사이트 원장이 열리지 않았다"}
    if source != "mcp":
        return {"skipped": "Claude 워크플로(source=mcp)의 대화만 인사이트로 들인다"}
    if kind == "risk-review" or C.risk_family(chair_template):
        return {"skipped": "리스크 심사는 인사이트로 들이지 않는다 — 리스크 판정은 리스크 앱에 있다"}
    if not pat:
        return {"skipped": "사람 자격(PAT)을 만들지 못해 주제를 다시 풀지 못했다"}
    rec, why = confirm_sync(settings, subject=subject_raw, principal=principal, pat=pat, chair_template=chair_template)
    if rec is None:
        return {"skipped": why}
    if rec["sp_state"] not in C.SP_STATES_CARD:
        return {"skipped": "과제가 없는 주제다(과제 대상이 아닌 질문) — 잇지 않는다"}
    claim, src = C.claim_of(C.workflow_decision(messages))
    row = _row(cid=C.wf_id(cid), path="mcp-workflow", source_id=cid, stage=(chair_template or "default"), owner_email=principal.email,
               owner_sub=principal.subject, subject=rec, claim=claim, claim_from=src,
               card={**_card_fields({}), "apps_unknown": ["(workflow)"]})
    store.ingest(row)
    return {"id": row["id"], "status": row["status"]}


def refresh_workflow_claim(store, *, cid: str, owner_email: str, messages: list) -> bool:
    """워크플로 대화에 결정문 조각이 덧붙었으면(큰 심의 — 200건을 넘는 몫은 덧붙이기로 온다) 주장을 다시 뽑는다. 사람이 고친 주장은 건드리지 않는다."""
    row = store.get(C.wf_id(cid)) if store is not None else None
    if row is None or row["status"] == "withdrawn" or row.get("claim_edited_by") or row["owner_email"] != owner_email.lower():
        return False
    claim, src = C.claim_of(C.workflow_decision(messages))
    if (claim, src) == (row["claim"], row["claim_from"]):
        return False
    return store.update(row["id"], claim=claim, claim_from=src)
