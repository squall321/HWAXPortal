# 과제 인사이트 API(/insights-api) — 읽을 때 그 사람 기준으로 거르는 과제 보기 · 찾기 · 카드, 주인의 확인 · 고침 · 거둠(docs/project-insight-graph contracts §6)
"""권한은 `feat:insights`. 읽기는 세션 또는 사람 PAT(게이트웨이 insight_find · insight_get 이 호출자 PAT 를 그대로 넘긴다), 쓰기는 브라우저 세션 + CSRF
만 받는다 — 사람이 화면에서 확인한다(사용자 결정 11-02 '주인이 포털에서 확인하면 같은 소속').

- 시야는 원장을 쥔 여기서 읽을 때 거른다(cards.visible) — 목록을 다 내려보내고 화면이 거르지 않는다. 수 · 잇기도 거른 뒤에 센다.
- 관리자는 다 보되 범위 밖 읽기를 감사에 한 줄(insight_admin_read) 남긴다.
- 리스크 심사 행은 베끼지 않는다 — 과제 보기가 읽는 사람의 PAT 로 리스크 앱(risk_find_projects_by_subject)을 불러 같은 (과제, 차수) 칸에 싣는다.
- 읽기 창구는 MCP 잡 카드를 당겨 들인 뒤 읽는다(intake.sync_jobs — 박스 손잡이 INSIGHT_SYNC_S 초에 한 번).
- 읽을 때 셈(M4 — lineage) — 설계 판의 뒤 판 표지(stale) · 옛 key 로 남은 카드 모으기 · 같은 결론 묶기(same)는 읽는 사람의 PAT · 시야로 그때
  셈하고 저장하지 않는다. 검토 줄(/review)은 그 사람이 손댈 카드와 까닭이다.
"""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.access.policy import ADMIN_GROUP
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf
from app.insights import cards as C
from app.insights import intake, lineage
from app.insights import store as S

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights-api", tags=["insights"])
FEAT = "feat:insights"
CONTRACT = "insights/1"
NOTE = "앞선 인사이트 — 검증 대상이고 독립 근거가 아니다. 출처(누가 · 언제 · 어느 심의)와 상태를 보고 쓴다."
# 리스크 앱의 읽기 도구 — 게이트웨이의 호출 전용 별칭(<백엔드 키에서 - 를 뺀 것>_<원래 이름>, 겹침과 무관하게 늘 선다)
RISK_TOOL = "heaxhwax_risk_risk_find_projects_by_subject"
RISK_PLAT = "plat:risk"
RISK_TIMEOUT_S = 30.0
RISK_PAGES_MAX = 4  # 한 화면이 리스크 앱을 이어 부르는 쪽 수 상한(쪽마다 50 과제) — 넘으면 앞쪽만 실었다고 말한다
FIND_MAX, ADMIN_AUDIT_IDS = 50, 50


def _store(request: Request):
    st = getattr(request.app.state, "insight_store", None)
    if st is None:
        raise AuthError("인사이트 원장이 열리지 않았습니다", status_code=503)
    return st


def _viewer(request: Request, principal: Principal) -> C.Viewer:
    from app.agent.wiki_send import known_affiliation      # 요청마다 원장으로 센 소속(권한표에 없는 값은 빈 값)
    return C.Viewer(email=(principal.email or "").strip().lower(), sub=principal.subject, aff=known_affiliation(request),
                    groups=frozenset(principal.groups), admin=ADMIN_GROUP in principal.groups)


def _reader(principal: Principal = Depends(principal_pat_or_session)) -> Principal:
    ensure(principal, FEAT)
    return principal


def _writer(principal: Principal = Depends(get_current_principal), _csrf: None = Depends(require_csrf)) -> Principal:
    """쓰기는 브라우저 세션 + CSRF 만 — 사람이 화면에서 한다(PAT 로는 못 쓴다)."""
    ensure(principal, FEAT)
    return principal


def _audit_admin(request: Request, v: C.Viewer, ids: list[str], where: str) -> None:
    if ids:
        try:
            request.app.state.agent_audit.record(principal=v.sub or v.email, event="insight_admin_read", status="ok",
                                                 meta={"where": where, "ids": ids[:ADMIN_AUDIT_IDS], "n": len(ids)})
        except Exception:  # noqa: BLE001 — 감사가 못 남아도 읽기는 막지 않는다(로그로 남긴다)
            logger.warning("과제 인사이트 — 관리자 범위 밖 읽기를 감사에 남기지 못했다", exc_info=True)


def _filter(rows: list[dict], v: C.Viewer) -> tuple[list[dict], list[str]]:
    """(보이는 행, 관리자라서만 보인 id)."""
    out, admin_only = [], []
    for r in rows:
        ok, only = C.visible(r, v)
        if ok:
            out.append(r)
            if only:
                admin_only.append(r["id"])
    return out, admin_only


def _view(r: dict, v: C.Viewer, *, full: bool = False, links: list | None = None, seen: set | None = None) -> dict:
    """원장 행 → 응답 꼴. 근거 표지(calls)는 카드 하나를 볼 때만 싣는다. 잇기는 보이는 카드(seen)끼리만."""
    card = dict(r.get("card") or {})
    calls = card.pop("calls", [])
    out = {"id": r["id"], "path": r["path"], "source_id": r["source_id"], "stage": r["stage"], "owner": r["owner_email"],
           "mine": C.owner_of(r, v), "status": r["status"],
           "subject": {"sp_task": (r.get("subject") or {}).get("sp_task"), "sp_state": (r.get("subject") or {}).get("sp_state"),
                       "sp_why": (r.get("subject") or {}).get("sp_why"), "round": r.get("round"), "round_by": r.get("round_by"),
                       "text": (r.get("subject") or {}).get("text") or "", "artifacts": (r.get("subject") or {}).get("artifacts") or []},
           "claim": r["claim"], "claim_from": r["claim_from"], "claim_edited_by": r.get("claim_edited_by"),
           "claim_edited_at": r.get("claim_edited_at"), **card, "calls_n": len(calls), "scope": r.get("scope") or [],
           "scope_note": r.get("scope_note"), "evidence_known": C.evidence_known(r), "created_at": r["created_at"],
           "updated_at": r["updated_at"], "confirmed_at": r.get("confirmed_at")}
    cont = r.get("continues")
    # 앞 카드는 읽는 사람이 볼 수 있을 때만 말한다(보이지 않는 카드는 있다는 것도 말하지 않는다 — PLAN §6.3). delib:<잡> 은 잡 원장의 열람 규칙이다.
    out["continues"] = cont if (cont and (cont.startswith("delib:") or (seen is not None and cont in seen))) else None
    if full:
        out["calls"] = calls
        out["subject"]["sp_resolved_by"] = (r.get("subject") or {}).get("sp_resolved_by")
    if links is not None:
        vis = seen or set()
        # 반박 줄은 늘 싣고 반박한 카드가 보이지 않으면 누가인지만 가린다 — 카드 없이 단 반박과 같은 꼴이라 숨은 카드가 있다는 것이 드러나지
        # 않는다(반대 검토 11-02 의 9 — 줄을 빼면 상태만 '반박' 이고 줄이 비어 숨은 카드가 있다고 말하는 셈이었다).
        out["disputed_by"] = [{"by": lk["from_id"] if lk["from_id"] in vis else None, "note": lk.get("note") or "", "at": lk["at"]}
                              for lk in links if lk["to_id"] == r["id"] and lk["kind"] == "disputes"]
        out["disputes"] = [lk["to_id"] for lk in links if lk["from_id"] == r["id"] and lk["kind"] == "disputes" and lk["to_id"] in vis]
    return out


async def _sync(request: Request, settings: Settings) -> None:
    try:
        await intake.sync_jobs(request.app, settings)
    except Exception:  # noqa: BLE001 — 당기기는 읽기를 막지 않는다
        logger.warning("과제 인사이트 — MCP 잡 카드 당기기 실패", exc_info=True)


def _risk_pat(request: Request, settings: Settings, principal: Principal) -> str | None:
    from app.agent.routes import _chat_user_pat
    return _chat_user_pat(request.app.state.keystore, settings, principal)


async def _risk_rows(request: Request, settings: Settings, principal: Principal, args: dict) -> tuple[list[dict], str]:
    """리스크 앱의 과제 · 대상 · 등록부 상위 — 읽는 사람의 PAT 로(그 앱의 시야 규칙이 곧 우리 규칙이다, PLAN §5.2). (과제 목록, 까닭)."""
    if RISK_PLAT not in principal.groups:
        return [], "리스크 앱 권한(plat:risk)이 없어 리스크 심사는 싣지 않았다"
    pat = _risk_pat(request, settings, principal)
    if not pat:
        return [], "사람 자격(PAT)을 만들지 못해 리스크 앱을 읽지 못했다"
    from app.agent import upload as _upload
    projects: list[dict] = []
    notes: list[str] = []
    page = dict(args)
    for _ in range(RISK_PAGES_MAX):
        try:
            out = await _upload.mcp_call(settings.mcp_gateway_url, pat, RISK_TOOL, page, timeout=RISK_TIMEOUT_S)
        except AuthError as exc:
            return projects, " · ".join([*notes, f"리스크 앱을 읽지 못했다 — {str(exc.message)[:200]}"])
        except Exception as exc:  # noqa: BLE001 — 게이트웨이 불통 · 기한 — 일반 심의 카드는 그대로 보인다
            return projects, " · ".join([*notes, f"리스크 앱을 읽지 못했다({type(exc).__name__})"])
        projects += [p for p in (out.get("projects") or []) if isinstance(p, dict)]
        if out.get("caller") == "service" and not notes:
            notes.append("리스크 앱이 이 사람을 알아보지 못해(service) 조직 공개 과제만 보였다")
        if not out.get("truncated"):
            break
        nxt = out.get("next_offset")
        if isinstance(nxt, bool) or not isinstance(nxt, int) or nxt <= int(page.get("offset") or 0):
            notes.append(f"리스크 앱 답이 남았다는데 다음 쪽이 없어 앞 {len(projects)}개 과제만 실었다")
            break
        page = {**args, "offset": nxt}
    else:
        notes.append(f"리스크 앱 과제가 많아 앞 {len(projects)}개만 실었다")
    return projects, " · ".join(notes)


def _seen_with_continues(st, rows: list[dict], v: C.Viewer, extra=()) -> tuple[set, list]:
    """(목록 행들의 id 와, 그 행들이 잇는 앞 카드 · 반박 잇기의 다른 끝(extra) 가운데 읽는 사람이 볼 수 있는 것의 id, 그 가운데 관리자라서만 보인
    id) — 뒤엣것도 범위 밖 읽기라 감사에 남긴다(반대 검토 11-02 의 8 — 잇기로 남의 초안 id 를 보는 것이 감사 밖이었다)."""
    seen, admin_seen = {r["id"] for r in rows}, []
    for cid in ({r.get("continues") for r in rows} | set(extra)) - seen - {None}:
        if cid and not cid.startswith("delib:"):
            o = st.get(cid)
            ok, only = C.visible(o, v) if o is not None else (False, False)
            if ok:
                seen.add(cid)
                if only:
                    admin_seen.append(cid)
    return seen, admin_seen


def _rows_for(st, v: C.Viewer, **kw) -> tuple[list[dict], dict]:
    """읽는 사람의 창 — 관리자가 아니면 그 사람의 것과 공유 상태만 센다(store.rows viewer). 창이 차면 '최근 N장만' 이라고 말한다."""
    raw = st.rows(viewer=None if v.admin else v.email, **kw)
    more = {"truncated": True, "note_rows": f"카드가 많아 최근 {S.ROWS_MAX}장만 봤다 — 과제 · 차수로 좁혀 다시 본다"} if len(raw) >= S.ROWS_MAX else {}
    return raw, more


def _bucket(rnd) -> str:
    return rnd if rnd in C.STAGES else C.ROUND_UNKNOWN


# ── 읽을 때 셈(M4) — 읽는 사람의 PAT · 시야로 ────────────────────────────────────────────────────────────────────
_NO_PAT = "사람 자격(PAT)을 만들지 못해"


def _caller(request: Request, settings: Settings, principal: Principal):
    """읽는 사람의 PAT 로 게이트웨이를 부르는 함수 — 사람 자격을 못 만들면 None(서비스 자격으로 내려가지 않는다)."""
    pat = _risk_pat(request, settings, principal)
    return lineage.caller(settings, pat) if pat else None


async def _family(st, v: C.Viewer, call, key: str) -> tuple[list[str], str]:
    """(지금 과제 key 에 모을 옛 key 들, 까닭). 그 사람에게 다른 key 의 카드가 보일 때만 이력을 부른다 — 옛 key 가 있어도 그 key 의 카드가 그 사람에게
    없으면 모을 것이 없다."""
    have = C.visible_tasks(await asyncio.to_thread(st.task_scopes, viewer=v.email), v) - {key}
    if not have:
        return [], ""
    if call is None:
        return [], f"{_NO_PAT} 과제 key 의 이력을 읽지 못했다 — 옛 key 로 남은 카드가 있어도 여기 모으지 않았다"
    return await lineage.old_keys(call, key, have)


async def _stales(call, rows: list[dict]) -> dict:
    """{카드 id: 판 표지} — 설계 자료가 있는 카드만. 기구 CAD 가 있으면 StepForge 개정 줄을 과제마다 한 번 묻는다(저장하지 않는다)."""
    ids = lineage.mcad_ids(rows)
    if not ids:
        revs: dict = {}
    elif call is None:
        revs = {i: {"state": "unknown", "why": f"{_NO_PAT} 묻지 않았다"} for i in ids}
    else:
        revs = await lineage.mcad_revisions(call, ids)
    out = {}
    for r in rows:
        got = lineage.card_stale(r.get("subject") or {}, revs)
        if got is not None:
            out[r["id"]] = got
    return out


def _newest(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (-int(r.get("created_at") or 0), str(r.get("id"))))


def _same(view: dict, same: dict) -> dict:
    """같은 결론 표지 — 같은 칸에서 정규화한 주장 글이 같은 다른 카드(읽는 사람이 볼 수 있는 것만). 둘 이상일 때만 싣는다."""
    ids = same.get(view["id"])
    return {**view, "same": {"n": len(ids) + 1, "ids": ids}} if ids else view


def _risk_round(p: dict):
    return C.norm_round(p.get("round") or "") or C.norm_round(p.get("stage") or "")


@router.get("/health")
def health(request: Request) -> dict:
    """무인증 — 게이트웨이가 '포털이 낡았다' 를 가르는 데 쓴다."""
    return {"ok": getattr(request.app.state, "insight_store", None) is not None, "contract": CONTRACT}


@router.get("/projects")
async def projects(request: Request, q: str = Query("", max_length=200), principal: Principal = Depends(_reader),
                   settings: Settings = Depends(get_settings)) -> dict:
    """보이는 과제 목록 — 일반 심의 카드(보이는 것만 센다)와 리스크 앱 과제(그 사람 시야)를 SP key 로 모은다. 기다림 줄(waiting)은 과제가 아니다."""
    await _sync(request, settings)
    v = _viewer(request, principal)
    raw, more = await asyncio.to_thread(_rows_for, _store(request), v)
    rows, admin_only = _filter(raw, v)
    by: dict = {}
    for r in rows:
        if r["status"] == "waiting" or not r.get("sp_task"):
            continue
        p = by.setdefault(r["sp_task"], {"sp_task": r["sp_task"], "rounds": {}, "total": 0, "latest_at": 0, "risk": 0})
        b = _bucket(r.get("round"))
        p["rounds"][b] = p["rounds"].get(b, 0) + 1
        p["total"] += 1
        p["latest_at"] = max(p["latest_at"], r["created_at"])
    risk, risk_why = await _risk_rows(request, settings, principal, {"limit": 50})
    for rp in risk:
        key = rp.get("sp_task")
        if isinstance(key, str) and key:
            by.setdefault(key, {"sp_task": key, "rounds": {}, "total": 0, "latest_at": 0, "risk": 0})["risk"] += 1
    want = q.strip().lower()
    out = sorted((p for p in by.values() if not want or want in p["sp_task"].lower()),
                 key=lambda p: (-p["latest_at"], p["sp_task"]))
    _audit_admin(request, v, admin_only, "projects")
    return {"projects": out, **({"risk_error": risk_why} if risk_why else {}), **more, "note": NOTE}


@router.get("/project")
async def project(request: Request, sp_task: str = Query(..., min_length=1, max_length=200),
                  round: str = Query("", max_length=40), principal: Principal = Depends(_reader),  # noqa: A002 — API 칸 이름
                  settings: Settings = Depends(get_settings)) -> dict:
    """한 과제 — 차수 칸마다(열한 코드 차례, 끝에 차수 모름) 일반 심의 카드와 리스크 행. 차수가 다르면 다른 칸이고 차수 모름은 어느 차수에도 섞지
    않는다(사용자 결정 11-02 PG-17). round 를 주면 그 칸만(unknown 은 차수 모름 칸만)."""
    want = ""
    if round.strip():
        want = C.ROUND_UNKNOWN if round.strip().lower() in (C.ROUND_UNKNOWN, "모름") else (C.norm_round(round) or "")
        if not want:
            raise AuthError(f"차수 {round[:40]!r} 는 차수가 아니다 — {' · '.join(C.STAGES)} 가운데 하나 또는 unknown 이다", status_code=422)
    await _sync(request, settings)
    v = _viewer(request, principal)
    st = _store(request)
    call = _caller(request, settings, principal)
    # 옛 key(이름 바뀜 · 합쳐짐)로 남은 카드를 지금 과제에 모은다(PLAN §4.3) — 카드의 key 는 그때의 것을 그대로 보인다
    old, keys_note = await _family(st, v, call, sp_task)
    fam = [sp_task, *old]
    raw, more = [], {}
    for k in fam:
        got, m = await asyncio.to_thread(_rows_for, st, v, sp_task=k)
        raw += got
        more.update(m)
    rows, admin_only = _filter(_newest(raw), v)
    rows = [r for r in rows if r["status"] != "waiting"]
    links = await asyncio.to_thread(st.links, sorted({r["id"] for r in rows}))
    seen, admin_seen = await asyncio.to_thread(_seen_with_continues, st, rows, v,
                                               [x for lk in links for x in (lk["from_id"], lk["to_id"]) if x])
    risk, risk_whys = [], []
    for k in fam:
        got, why = await _risk_rows(request, settings, principal, {"sp_task": k, "limit": 50})
        risk += got
        if why and why not in risk_whys:
            risk_whys.append(why)
    risk_why = " · ".join(risk_whys)
    stales = await _stales(call, rows)
    cells: dict = {b: {"round": (None if b == C.ROUND_UNKNOWN else b), "cards": [], "risk": []} for b in (*C.STAGES, C.ROUND_UNKNOWN)}
    by_cell: dict = {}
    for r in rows:
        by_cell.setdefault(_bucket(r.get("round")), []).append(r)
    for b, cell_rows in by_cell.items():
        same = C.same_claims(cell_rows)       # 같은 결론 — 이 칸에서 읽는 사람이 볼 수 있는 카드끼리만(합치지 않는다)
        for r in cell_rows:
            view = _same(_view(r, v, links=links, seen=seen), same)
            cells[b]["cards"].append({**view, "stale": stales[r["id"]]} if r["id"] in stales else view)
    for rp in risk:
        if rp.get("sp_task") in fam:
            cells[_bucket(_risk_round(rp))]["risk"].append(rp)
    order = [b for b in (*C.STAGES, C.ROUND_UNKNOWN) if (not want or b == want) and (cells[b]["cards"] or cells[b]["risk"])]
    _audit_admin(request, v, admin_only + admin_seen, "project")
    return {"sp_task": sp_task, "rounds": [cells[b] for b in order], **({"risk_error": risk_why} if risk_why else {}), **more,
            **({"previous_keys": old} if old else {}), **({"keys_note": keys_note} if keys_note else {}), "note": NOTE}


@router.get("/mine")
async def mine(request: Request, principal: Principal = Depends(_reader), settings: Settings = Depends(get_settings)) -> dict:
    """내 카드 — 기다림 줄(주제를 확인하지 못했다) · 초안 · 그 밖(확인 · 반박)."""
    await _sync(request, settings)
    v = _viewer(request, principal)
    st = _store(request)
    rows = await asyncio.to_thread(st.rows, owner_email=v.email)
    seen, admin_seen = await asyncio.to_thread(_seen_with_continues, st, rows, v)
    groups: dict = {"waiting": [], "draft": [], "shared": []}
    for r in rows:
        groups["shared" if r["status"] in C.SHARED else r["status"]].append(_view(r, v, seen=seen))
    _audit_admin(request, v, admin_seen, "mine")
    return {**groups, **({"truncated": True} if len(rows) >= S.ROWS_MAX else {}), "note": NOTE}


# 검토 줄(PLAN §8 사람 검토) — 까닭의 차례가 줄의 차례다. 글은 화면과 같이 쓴다.
_REVIEW = {"waiting": "주제 확인을 기다린다 — 허브에서 찾은 과제 행을 고른다",
           "disputed": "반박이 달렸다 — 주장을 고치거나 거둔다(지우지 않고 둘 다 남는다)",
           "stale": "설계 판이 바뀌었다 — 결론이 지금 판에도 맞는지 본다",
           "draft": "초안이다 — 주제 · 차수 · 주장을 보고 확인한다(확인하면 같은 소속에 열린다)",
           "round_unknown": "차수를 모른다 — 차수를 단다(모르는 것이 맞으면 '모름' 을 고른다)",
           "admin_disputed": "반박이 달린 남의 카드다 — 관리자는 반박 표시 · 거두기를 할 수 있다"}


def _review_reasons(r: dict, stale: dict | None) -> list[str]:
    out = []
    if r["status"] == "waiting":
        out.append("waiting")
    if r["status"] == "disputed":
        out.append("disputed")
    if (stale or {}).get("state") == "stale":
        out.append("stale")
    if r["status"] == "draft":
        out.append("draft")
    if r["status"] in C.SHARED and r.get("round") not in C.STAGES and r.get("round_by") != "person":
        out.append("round_unknown")     # 사람이 고른 '차수 모름' 은 손댈 것이 아니다
    return out


@router.get("/review")
async def review(request: Request, principal: Principal = Depends(_reader), settings: Settings = Depends(get_settings)) -> dict:
    """검토 줄 — 내가 손댈 내 카드와 까닭(주제 확인 기다림 · 반박 · 설계 판이 바뀜 · 초안 · 차수 모름). 관리자에게는 반박이 달린 남의 카드도 선다
    (반박 · 거둠은 주인 · 관리자가 한다 — 범위 밖 읽기는 감사에 남는다). 판이 바뀌었는지는 읽을 때 셈한다."""
    await _sync(request, settings)
    v = _viewer(request, principal)
    st = _store(request)
    mine = await asyncio.to_thread(st.rows, owner_email=v.email)
    stales = await _stales(_caller(request, settings, principal), [r for r in mine if r["status"] != "waiting"])
    picked: list[tuple[list, dict]] = []
    for r in mine:
        reasons = _review_reasons(r, stales.get(r["id"]))
        if reasons:
            picked.append((reasons, r))
    admin_only: list[str] = []
    if v.admin:
        for r in await asyncio.to_thread(st.rows):
            ok, only = C.visible(r, v)
            if ok and r["status"] == "disputed" and not C.owner_of(r, v):
                picked.append((["admin_disputed"], r))
                if only:
                    admin_only.append(r["id"])
    order = list(_REVIEW)
    picked.sort(key=lambda x: (order.index(x[0][0]), -int(x[1].get("created_at") or 0), x[1]["id"]))
    seen, admin_seen = await asyncio.to_thread(_seen_with_continues, st, [r for _why, r in picked], v)
    items, counts = [], {}
    for reasons, r in picked:
        view = _view(r, v, seen=seen)
        if r["id"] in stales:
            view["stale"] = stales[r["id"]]
        items.append({"reasons": reasons, "say": " · ".join(_REVIEW[x] for x in reasons), "card": view})
        for x in reasons:
            counts[x] = counts.get(x, 0) + 1
    _audit_admin(request, v, admin_only + admin_seen, "review")
    return {"items": items, "counts": counts, **({"truncated": True} if len(mine) >= S.ROWS_MAX else {}), "note": NOTE}


@router.get("/find")
async def find(request: Request, sp_task: str = Query("", max_length=200), round: str = Query("", max_length=40),  # noqa: A002
               q: str = Query("", max_length=200), artifact_kind: str = Query("", max_length=8),
               artifact_id: str = Query("", max_length=64), limit: int = Query(20, ge=1, le=FIND_MAX),
               principal: Principal = Depends(_reader), settings: Settings = Depends(get_settings)) -> dict:
    """게이트웨이 insight_find 의 몸 — 보이는 카드의 짧은 행(기다림 줄은 빼고). 과제 key 는 글자 그대로(그 과제의 옛 key 로 남은 카드도 모은다 —
    previous_keys), 차수는 정확히(unknown 은 차수 모름만), q 는 주장 · 과제 글에 든 말(대소문자 없이), 설계 자료는 (종류, 열쇠)."""
    rnd = ""
    if round.strip():
        rnd = C.ROUND_UNKNOWN if round.strip().lower() in (C.ROUND_UNKNOWN, "모름") else (C.norm_round(round) or "")
        if not rnd:
            raise AuthError(f"차수 {round[:40]!r} 는 차수가 아니다 — {' · '.join(C.STAGES)} 가운데 하나 또는 unknown 이다", status_code=422)
    if bool(artifact_kind) != bool(artifact_id):
        raise AuthError("artifact_kind 와 artifact_id 는 함께 준다", status_code=422)
    await _sync(request, settings)
    v = _viewer(request, principal)
    st = _store(request)
    key = sp_task.strip()
    old, keys_note = (await _family(st, v, _caller(request, settings, principal), key)) if key else ([], "")
    raw, more = [], {}
    for k in ([key, *old] if key else [None]):
        got, m = await asyncio.to_thread(_rows_for, st, v, sp_task=k)
        raw += got
        more.update(m)
    rows, admin_only = _filter(_newest(raw), v)
    want_q, aid = q.strip().lower(), artifact_id.strip().lower()
    picked: list[dict] = []
    for r in rows:
        if r["status"] == "waiting":
            continue
        if rnd and _bucket(r.get("round")) != rnd:
            continue
        subj = r.get("subject") or {}
        if want_q and want_q not in (r["claim"] + "\n" + str(subj.get("text") or "")).lower():
            continue
        if aid and not any(isinstance(a, dict) and a.get("kind") == artifact_kind and str(a.get("id") or "").lower() == aid
                           for a in subj.get("artifacts") or []):
            continue
        picked.append(r)
        if len(picked) >= limit:
            break
    seen, admin_seen = await asyncio.to_thread(_seen_with_continues, st, picked, v)
    out = [_view(r, v, seen=seen) for r in picked]
    _audit_admin(request, v, [i for i in admin_only if i in {o["id"] for o in out}] + admin_seen, "find")
    return {"items": out, "count": len(out), **more, **({"previous_keys": old} if old else {}),
            **({"keys_note": keys_note} if keys_note else {}), "note": NOTE}


@router.get("/cards/{cid}")
async def card(cid: str, request: Request, principal: Principal = Depends(_reader), settings: Settings = Depends(get_settings)) -> dict:
    """카드 하나의 전부 — 못 보면 없는 것과 같은 404 다(id 를 넣어 보는 것만으로 남의 카드가 있는지 알 수 없게). 판 표지(stale)와, 뒤 판이 있으면
    그 판의 리스크 변경 심사 줄(stale.risk_diffs)을 읽을 때 셈해 싣는다."""
    await _sync(request, settings)
    v = _viewer(request, principal)
    st = _store(request)
    r = await asyncio.to_thread(st.get, cid)
    ok, only = C.visible(r, v) if r is not None else (False, False)
    if not ok:
        raise AuthError("카드를 찾을 수 없습니다", status_code=404)
    links = await asyncio.to_thread(st.links, [cid])
    seen, admin_seen = await asyncio.to_thread(_seen_with_continues, st, [r], v,
                                               [x for lk in links for x in (lk["from_id"], lk["to_id"]) if x])
    _audit_admin(request, v, ([cid] if only else []) + admin_seen, "card")
    view = _view(r, v, full=True, links=links, seen=seen)
    if r["status"] != "waiting" and r.get("sp_task"):
        # 같은 결론 — 이 카드의 과제 key · 같은 차수 칸에서 볼 수 있는 카드끼리(과제 보기는 옛 key 의 카드까지 모아 센다)
        peers, _admin = _filter((await asyncio.to_thread(_rows_for, st, v, sp_task=r["sp_task"]))[0], v)
        view = _same(view, C.same_claims([x for x in peers if x["status"] != "waiting" and _bucket(x.get("round")) == _bucket(r.get("round"))]))
    call = _caller(request, settings, principal)
    stale = (await _stales(call, [r])).get(cid)
    if stale is not None:
        nxt = lineage.next_ids(stale)
        if nxt:
            # 뒤 판의 리스크 변경 심사(PLAN §8) — 읽는 사람의 리스크 앱 시야로. 그 비교의 앞 판이 이 카드의 판인지는 확인하지 않았다고 적는다
            if RISK_PLAT not in principal.groups:
                stale["risk_note"] = "리스크 앱 권한(plat:risk)이 없어 뒤 판의 리스크 변경 심사는 보지 않았다"
            elif call is None:
                stale["risk_note"] = f"{_NO_PAT} 뒤 판의 리스크 변경 심사는 보지 않았다"
            else:
                diffs, why = await lineage.risk_diffs(call, nxt)
                if diffs:
                    stale["risk_diffs"] = diffs
                stale["risk_note"] = lineage.RISK_DIFF_NOTE if diffs else (why or "뒤 판의 CAD 과제를 원천으로 쓰는 리스크 변경 심사가 내 시야에 없다")
        view["stale"] = stale
    return {**view, "note": NOTE}


# ── 쓰기 — 세션 + CSRF, 주인(일부는 관리자도) ──────────────────────────────────────────────────────────────────────────
async def _mine_or_404(request: Request, cid: str, principal: Principal, *, admin_ok: bool = False) -> tuple[dict, C.Viewer]:
    v = _viewer(request, principal)
    r = await asyncio.to_thread(_store(request).get, cid)
    if r is None or r["status"] == "withdrawn" or not (C.owner_of(r, v) or (admin_ok and v.admin)):
        if r is not None and r["status"] != "withdrawn" and C.visible(r, v)[0]:
            raise AuthError("이 카드의 주인만 할 수 있다", status_code=403)
        raise AuthError("카드를 찾을 수 없습니다", status_code=404)
    return r, v


async def _save(request: Request, cid: str, v: C.Viewer, r: dict, **fields) -> dict:
    st = _store(request)
    if C.owner_of(r, v) and not r.get("owner_sub"):
        fields["owner_sub"] = v.sub        # MCP 잡 카드는 주인이 처음 손댈 때 포털 subject 를 단다
    if fields and not await asyncio.to_thread(lambda: st.update(cid, **fields)):
        raise AuthError("카드를 찾을 수 없습니다", status_code=404)
    return {**_view(await asyncio.to_thread(st.get, cid), v), "note": NOTE}


async def _apps_now(settings: Settings, card: dict) -> tuple[list, list] | None:
    """(근거 앱, 여전히 앱을 모르는 도구) — 카드를 지은 때 앱을 몰랐던 도구는 지금 게이트웨이 도구 지도로 다시 푼다. 엔진이 지도를 못 받은 때 지은
    카드는 근거 도구가 다 '앱 모름' 이라 plat 토큰 없이 열렸다(반대 검토 11-02 의 4). 다시 풀 도구가 있는데 지도를 못 받으면 None(확인을 미룬다).
    워크플로 표지 같은 괄호 이름('(workflow)')은 도구가 아니라 그대로 둔다."""
    from app.access.routes import _gateway_tools_map
    apps = {str(a) for a in card.get("apps") or () if a}
    unknown = [str(x) for x in card.get("apps_unknown") or () if x]
    tools = [x for x in unknown if not x.startswith("(")]
    if not tools:
        return sorted(apps), unknown
    tm = await _gateway_tools_map(settings)
    amap = tm.get("map") if isinstance(tm, dict) else None
    if not isinstance(amap, dict):
        return None
    still = []
    for x in tools:
        if amap.get(x):
            apps.add(str(amap[x]))
        else:
            still.append(x)
    return sorted(apps), still + [x for x in unknown if x.startswith("(")]


_UNTRACKED_WORDS = {"evidence": "붙인 근거 글", "note": "사람 의견 · 보강 글", "summary": "앞 회차 요약", "images": "그림"}


@router.post("/cards/{cid}/confirm")
async def confirm(cid: str, request: Request, principal: Principal = Depends(_writer),
                  settings: Settings = Depends(get_settings)) -> dict:
    """주인의 확인 — 초안을 같은 소속에 연다. 범위는 [aff:<주인의 지금 포털 원장 소속>] + 근거 앱의 plat 토큰(포털 권한표로 푼다 — 앱을 몰랐던
    도구는 지금 게이트웨이 도구 지도로 다시 푼다). 주인에게 소속이 없으면 확인은 하되 주인만 보고 까닭을 단다(PLAN §6.2 — 더 좁게 막으면 그 선에서
    멈춘다). MCP 잡이 실은 소속(자칭)은 쓰지 않는다. 앞선 인사이트(insight_*)를 근거로 쓴 카드는 읽은 카드들의 범위를 다 담는다(M3 — 읽은 카드를
    모르거나 담을 수 없으면 주인만 본다)."""
    r, v = await _mine_or_404(request, cid, principal)
    if r["status"] != "draft":
        raise AuthError("확인할 수 있는 것은 초안이다" + (" — 주제를 먼저 확인한다(기다림 줄)" if r["status"] == "waiting" else ""),
                        status_code=409)
    card = dict(r.get("card") or {})
    now = int(time.time())
    got = await _apps_now(settings, card)
    if got is None:
        raise AuthError("근거 도구의 앱을 지금 알 수 없다(게이트웨이 도구 지도에 닿지 못했다) — 범위를 정하지 못해 확인을 미룬다. 잠시 뒤 다시 확인한다",
                        status_code=503)
    apps, unknown = got
    fields: dict = {}
    if apps != sorted(card.get("apps") or []) or unknown != list(card.get("apps_unknown") or []):
        card.update(apps=apps, apps_unknown=unknown)
        fields["card"] = card
    policy = getattr(request.app.state, "access", None)
    plats = C.plat_tokens(apps, policy.get() if policy is not None else None)
    notes = []
    if v.aff:
        scope = [f"aff:{v.aff}", *plats]
    else:
        scope = [f"user:{v.email}"]
        notes.append("소속이 없어 같은 소속에 열지 못했다 — 주인만 본다(관리자가 소속을 정하면 다시 확인한다)")
    if unknown:
        notes.append("근거 도구 일부의 앱을 몰라 그 플랫폼 권한은 범위에 넣지 못했다 — 조직 공개는 열리지 않는다")
    if card.get("untracked"):
        what = " · ".join(_UNTRACKED_WORDS.get(str(u), str(u)) for u in card["untracked"])
        notes.append(f"범위를 모르는 입력({what})이 있어 같은 소속까지다 — 조직 공개는 열리지 않는다")
    if C.insight_derived(r):
        # 앞선 인사이트를 근거로 쓴 카드 — 읽은 카드들의 범위를 다 담는다(PLAN §6.2 최소 범위 · M3). 어느 카드를 읽었는지 모르거나 담을 수 없으면
        # 주인만 본다(종전 — 반대 검토 11-02 의 3). 읽은 카드는 근거 표지의 insight_get 인자(카드 id)로 안다 — 포털이 깐 항목이 그 꼴이다(reuse).
        ids, why = C.insight_sources(r)
        if ids is not None:
            st = _store(request)
            scope, why = C.inherit_scope(scope, [await asyncio.to_thread(st.get, i) for i in ids], v.email)
        else:
            scope, why = [f"user:{v.email}"], f"{why} — 그 카드들의 범위를 이어받지 못해 주인만 본다"
        if why:
            notes.append(why)
    return await _save(request, cid, v, r, status="confirmed", scope=scope, scope_note=" · ".join(notes) or None, confirmed_at=now,
                       confirmed_by=v.email, **fields)


class SubjectIn(BaseModel):
    model_config = {"extra": "forbid"}
    sp_task: str = Field(min_length=1, max_length=200)
    round: str | None = Field(default=None, max_length=40)


@router.post("/cards/{cid}/subject")
async def set_subject(cid: str, body: SubjectIn, request: Request, principal: Principal = Depends(_writer),
                      settings: Settings = Depends(get_settings)) -> dict:
    """기다림 줄의 주제 확인 — 주인이 허브 찾기 결과 행의 key 를 고르면 에이전트 서버가 그 사람 PAT 로 같은 풀이로 다시 확인한다(브라우저가 보낸
    key 를 믿지 않는다 — PG-19). 확인되면 초안이 선다. 글 · 설계 자료는 처음 주제의 것을 그대로 쓴다."""
    r, v = await _mine_or_404(request, cid, principal)
    if r["status"] != "waiting":
        raise AuthError("주제를 고칠 수 있는 것은 기다림 줄의 카드다", status_code=409)
    old = r.get("subject") or {}
    # 사람이 단 차수(모름 포함 — round_by person)는 지킨다. 종전엔 처음 주제의 차수로 되돌렸다(반대 검토 11-02 의 10).
    keep = not body.round and r.get("round_by") == "person"
    rnd = body.round or (r.get("round") if keep else old.get("round")) or None
    want = {"sp_task": body.sp_task.strip(), "round": rnd, "text": old.get("text") or None,
            "artifacts": [{k: a[k] for k in ("kind", "app", "id", "rev") if a.get(k)} for a in old.get("artifacts") or []
                          if isinstance(a, dict)] or None}
    pat = _risk_pat(request, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    rec, why = await intake.confirm_async(settings, subject={k: v2 for k, v2 in want.items() if v2}, principal=principal, pat=pat,
                                          chair_template=r["stage"])
    if rec is None:
        raise AuthError(why, status_code=502 if "닿지" in why or "HTTP 5" in why else 422)
    fields: dict = {"subject": rec, "round": C.norm_round(rec.get("round") or ""), "round_by": rec.get("round_by")}
    if keep:
        fields.update(round=r.get("round"), round_by="person")
    if rec["sp_state"] == "confirmed":
        fields.update(status="draft", sp_task=rec["sp_task"])
    out = await _save(request, cid, v, r, **fields)
    return {**out, "confirmed": rec["sp_state"] == "confirmed"}


class RoundIn(BaseModel):
    model_config = {"extra": "forbid"}
    round: str = Field(min_length=1, max_length=40)


@router.post("/cards/{cid}/round")
async def set_round(cid: str, body: RoundIn, request: Request, principal: Principal = Depends(_writer)) -> dict:
    """차수 달기 — 열한 코드 가운데 하나, 차수 모름은 unknown. 사람이 단 차수다(round_by=person — 고른 '모름' 도 사람의 것이라 주제 확인이 되돌리지
    않는다)."""
    r, v = await _mine_or_404(request, cid, principal)
    raw = body.round.strip()
    if raw.lower() in (C.ROUND_UNKNOWN, "모름"):
        return await _save(request, cid, v, r, round=None, round_by="person")
    code = C.norm_round(raw)
    if code is None:
        raise AuthError(f"차수 {raw[:40]!r} 는 차수가 아니다 — {' · '.join(C.STAGES)} 가운데 하나 또는 unknown 이다", status_code=422)
    return await _save(request, cid, v, r, round=code, round_by="person")


class ClaimIn(BaseModel):
    model_config = {"extra": "forbid"}
    claim: str = Field(max_length=C.CLAIM_MAX)


@router.post("/cards/{cid}/claim")
async def set_claim(cid: str, body: ClaimIn, request: Request, principal: Principal = Depends(_writer)) -> dict:
    """주장 고치기 — 500자까지, 고친 사람 · 때를 남긴다."""
    r, v = await _mine_or_404(request, cid, principal)
    return await _save(request, cid, v, r, claim=body.claim.strip(), claim_from="person", claim_edited_by=v.email,
                       claim_edited_at=int(time.time()))


class WidenIn(BaseModel):
    model_config = {"extra": "forbid"}
    to: str = Field(pattern="^org$")


@router.post("/cards/{cid}/widen")
async def widen(cid: str, body: WidenIn, request: Request, principal: Principal = Depends(_writer)) -> dict:
    """조직 공개 — 근거 범위를 다 알 때만(PLAN §6.2 '한 칸 다른 자리'). 아니면 409 와 까닭. plat 토큰은 그대로 남는다(빼기는 관리자 몫 — 짓지 않았다)."""
    r, v = await _mine_or_404(request, cid, principal)
    if r["status"] not in C.SHARED:
        raise AuthError("조직에 열 수 있는 것은 확인한 카드다", status_code=409)
    if not C.evidence_known(r):
        raise AuthError("근거 범위를 다 알지 못해 조직에 열지 않는다 — 같은 소속까지다(도구 근거 · 워크플로 카드는 남의 보고서 · 리포트가 섞였을 수 있다)",
                        status_code=409)
    scope = ["org", *[t for t in r.get("scope") or [] if str(t).startswith("plat:")]]
    return await _save(request, cid, v, r, scope=scope, scope_note=None)


class DisputeIn(BaseModel):
    model_config = {"extra": "forbid"}
    by_card: str | None = Field(default=None, max_length=300)
    note: str = Field(default="", max_length=500)


@router.post("/cards/{cid}/dispute")
async def dispute(cid: str, body: DisputeIn, request: Request, principal: Principal = Depends(_writer)) -> dict:
    """반박 표시 — 주인 · 관리자. 지우지 않고 둘 다 근거째 남긴다(PLAN §8). 반박한 카드(by_card)는 그 사람이 볼 수 있어야 한다."""
    r, v = await _mine_or_404(request, cid, principal, admin_ok=True)
    if r["status"] not in C.SHARED:
        raise AuthError("반박을 달 수 있는 것은 확인한 카드다", status_code=409)
    st = _store(request)
    by = (body.by_card or "").strip()
    if by:
        other = await asyncio.to_thread(st.get, by)
        if other is None or by == cid or not C.visible(other, v)[0]:
            raise AuthError("반박한 카드를 찾을 수 없습니다", status_code=404)
    await asyncio.to_thread(lambda: st.link(by, cid, kind="disputes", by=v.email, note=body.note.strip()))
    return await _save(request, cid, v, r, status="disputed")


@router.post("/cards/{cid}/withdraw")
async def withdraw(cid: str, request: Request, principal: Principal = Depends(_writer)) -> dict:
    """거두기 — 주인 · 관리자. 내용을 지우고 묘비(id · 거둔 사람 · 때)만 남긴다. 아무에게도 안 보인다(PLAN §6.5)."""
    r, v = await _mine_or_404(request, cid, principal, admin_ok=True)
    st = _store(request)
    await asyncio.to_thread(lambda: st.withdraw(cid, by=v.email))
    return {"id": cid, "status": "withdrawn"}
