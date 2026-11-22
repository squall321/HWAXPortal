# 과제 인사이트의 Report Archive 투영 — 조직에 연 확인 카드의 RA 보고서에 SP 과제 객체를 id 로 단다(그 사람의 RA 연결로 · 박스 스위치 기본 꺼짐)
"""docs/project-insight-graph M5 · 사용자 결정 2026-11-21(docs/leftovers-1121 L21-6 ③) — RA 최신판 기준(객체를 id 로 다는 길 — SP 에서 받은
객체는 code = SP 키)으로 짓고 박스 스위치(INSIGHT_RA_PROJECT) 뒤에 둔다. 관리자 토큰 · 서비스 자격은 쓰지 않는다(그 사용은 승인되지 않았다).

카드 하나 → 그 카드의 RA 보고서 하나에 과제 객체 태그 하나. 사람이 화면에서 누른 호출만 받는다(세션 + CSRF · 카드 주인 · plat:reportarchive).
  ① 대상 — 확인한(confirmed) 카드이고 범위가 조직뿐(["org"] — plat: 이 붙은 카드는 RA 독자가 그 권한으로 걸러지지 않아 달지 않는다)이며, 확인된
     과제 key 와 RA 보고서 번호가 있을 때(why_not).
  ② 과제 객체 — RA `POST /api/entities/search {q: key}` 의 결과에서 code 가 key 와 글자 그대로 같은 살아 있는 객체가 하나일 때만. RA 의 SP 받기가
     code = SP 키로 싣는다(RA connectors/sp_pull.py — 64자를 넘는 key 는 code 로 실리지 않는다). 없거나 · 여럿이거나 · 결과를 다 보지 못하면 달지
     않는다(틀릴 거면 닫힌 쪽).
  ③ 달기 — RA `POST /api/reports/{id}/entities/add {entity_ids: [객체 id]}`(더하기만 · 편집 잠금 없음 · 보고서 주인 · 편집자만). 객체를 만들거나
     고치거나 잇는 일(create_object · update_object · link_objects · 축 · 관계 정의)은 RA 시스템 관리자 전용이라 하지 않는다.
  ④ 원장 — insight_meta 의 'ra:<카드 id>' 한 줄. 한 카드는 한 번만 단다 — 줄이 있으면 RA 를 부르지 않고 그 줄을 돌려준다.
거두면 — RA 에는 사람 권한으로 태그 하나만 떼는 길이 없다(보고서 PATCH 의 entity_ids 는 통째 교체라 그사이 남이 단 태그를 지울 수 있다). RA 는
건드리지 않고 원장 줄의 표지만 'withdrawn' 으로 바꾼다 — 태그는 '이 보고서가 그 과제의 것이다' 라는 사실이라 거둔 뒤에도 참이다. 사람은 RA 의
보고서 편집 화면에서 손으로 뗄 수 있다.
"""
from __future__ import annotations

import json
import time

import httpx

KEY_PREFIX = "ra:"
CODE_MAX = 64                  # RA Entity.code 칸 길이 — 넘는 SP 키는 RA 가 code 로 싣지 않는다(sp_pull: code=key if len(key) <= 64)
SEARCH_LIMIT = 200             # RA EntitySearchRequest.limit 상한
_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
_TRANSPORT: httpx.AsyncBaseTransport | None = None   # 시험 이음매 — None 이 아니면 RA 로 가는 요청이 전부 이 전송을 탄다
PROJECTED, WITHDRAWN = "projected", "withdrawn"
_PUBLIC = ("state", "report_id", "entity_id", "type_slug", "value", "added", "at", "by")
NOTE = ("RA 보고서에 과제 객체 태그를 달았다 — 그 보고서를 볼 수 있는 사람의 RA 검색 · 과제 객체 화면에 선다. 보고서의 공개 범위는 바뀌지 않는다. "
        "카드를 거두어도 RA 의 태그는 떼지 않는다(사람 권한으로 하나만 떼는 길이 없다 — 보고서 편집 화면에서 손으로 뗀다).")
WITHDRAWN_NOTE = "이 카드의 RA 보고서에 단 과제 객체 태그는 RA 에 남는다 — 떼려면 RA 의 보고서 편집 화면에서 손으로 뗀다."


class ProjectError(Exception):
    def __init__(self, status: int, error: str, detail: str):
        super().__init__(detail)
        self.status, self.error, self.detail = status, error, detail


# ── 원장 ─────────────────────────────────────────────────────────────────────────────────────────
def record(store, cid: str) -> dict | None:
    raw = store.meta_get(KEY_PREFIX + cid)
    try:
        got = json.loads(raw) if raw else None
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


def records(store, cids: list[str]) -> dict[str, dict]:
    return {c: r for c in dict.fromkeys(cids) if (r := record(store, c)) is not None}


def public(rec: dict | None) -> dict | None:
    """화면에 내는 칸 — 투영한 줄만(거둔 카드는 어차피 아무에게도 안 보인다)."""
    if not rec or rec.get("state") != PROJECTED:
        return None
    return {k: rec.get(k) for k in _PUBLIC}


def mark_withdrawn(store, cid: str, by: str) -> dict | None:
    """카드를 거둘 때 — 투영한 줄이 있으면 표지만 바꾼다(RA 는 부르지 않는다). 바꾼 줄 또는 None."""
    rec = record(store, cid)
    if not rec or rec.get("state") != PROJECTED:
        return None
    rec = {**rec, "state": WITHDRAWN, "withdrawn_at": int(time.time()), "withdrawn_by": by.lower()}
    store.meta_set(KEY_PREFIX + cid, json.dumps(rec, ensure_ascii=False))
    return rec


# ── 대상 ─────────────────────────────────────────────────────────────────────────────────────────
def report_id_of(row: dict) -> int | None:
    rid = (row.get("card") or {}).get("report_id")
    if isinstance(rid, bool):
        return None
    if isinstance(rid, int):
        return rid if rid > 0 else None
    if isinstance(rid, str) and rid.isascii() and rid.isdigit() and int(rid) > 0:
        return int(rid)
    return None


def why_not(row: dict) -> str | None:
    """이 카드를 RA 에 달지 않는 까닭 — 달 수 있으면 None."""
    if row.get("status") != "confirmed":
        return "확인한 카드만 RA 에 단다(초안 · 반박이 달린 카드는 아니다)"
    scope = [str(t) for t in row.get("scope") or ()]
    if "org" not in scope:
        return "조직에 연 카드만 RA 에 단다 — RA 보고서의 독자는 포털 소속으로 걸러지지 않는다"
    if set(scope) != {"org"}:
        return "플랫폼 권한(plat:)이 붙은 카드는 RA 에 달지 않는다 — RA 의 독자는 그 권한으로 걸러지지 않는다"
    subj = row.get("subject") or {}
    key = str(row.get("sp_task") or "")
    if not key or subj.get("sp_state") != "confirmed" or subj.get("sp_task") != key:
        return "확인된 과제 key 가 없다"
    if len(key) > CODE_MAX:
        return f"과제 key 가 {CODE_MAX}자를 넘어 RA 의 SP 받기가 객체의 code 로 싣지 않는다 — 달 객체를 key 로 찾을 수 없다"
    if report_id_of(row) is None:
        return "RA 보고서 번호가 없다 — 보고서를 저장하지 않은 심의다"
    return None


# ── RA ───────────────────────────────────────────────────────────────────────────────────────────
def _data(r: httpx.Response) -> dict:
    try:
        j = r.json()
    except ValueError:
        return {}
    d = j.get("data") if isinstance(j, dict) else None
    return d if isinstance(d, dict) else {}


def _fail(r: httpx.Response, step: str) -> ProjectError:
    """RA 의 거절 → 포털 답. step — search(과제 객체 찾기) · add(보고서에 달기)."""
    from app.agent import docforge_delivery as _dfd     # 지연 import — 가벼운 읽기 창구가 이 모듈을 부를 때 무거운 것을 끌지 않게
    st, why = r.status_code, _dfd._ra_error(r)
    if st == 401:
        return ProjectError(502, "ra_token_rejected", "Report Archive 가 이 사람의 RA 토큰을 받지 않았습니다(HTTP 401) — 포털 '외부 연결' 의 "
                                                      "RA 토큰 · 위임 상태를 확인하세요.")
    if step == "add" and st == 403:
        return ProjectError(403, "not_editable", f"Report Archive 가 이 보고서에 태그를 달지 못하게 했습니다(HTTP 403 {why}) — RA 에서 그 보고서의 "
                                                 "주인 · 편집자만 태그를 답니다.")
    if step == "add" and st == 404:
        return ProjectError(404, "report_not_found", f"그 보고서가 Report Archive 에 없습니다(HTTP 404 {why}).")
    if 400 <= st < 500:
        return ProjectError(422, "ra_rejected", f"Report Archive 가 받지 않았습니다(HTTP {st} {why}).")
    return ProjectError(502, "ra_error", f"Report Archive 가 답하지 못했습니다(HTTP {st} {why}).")


async def find_task_object(ra, cli: httpx.AsyncClient, key: str) -> dict:
    """SP 과제 key → RA 과제 객체(EntityRead). code 가 key 와 글자 그대로 같은 살아 있는 객체가 하나일 때만이다 — 아니면 ProjectError."""
    r = await ra.call(cli, "POST", "/api/entities/search", json={"q": key, "limit": SEARCH_LIMIT})
    if r.status_code != 200:
        raise _fail(r, "search")
    data = _data(r)
    items = [x for x in data.get("items") or () if isinstance(x, dict)]
    exact = [x for x in items if x.get("code") == key and x.get("status", "active") == "active" and isinstance(x.get("id"), int)
             and not isinstance(x.get("id"), bool)]
    total = data.get("total")
    if not isinstance(total, int) or isinstance(total, bool) or total > len(items):
        raise ProjectError(409, "ra_search_truncated", f"Report Archive 에서 과제 「{key}」 를 담은 객체가 많아(전체 {total}) 다 보지 못했다 — "
                                                       "code 가 같은 객체가 하나뿐인지 알 수 없어 달지 않았다.")
    if not exact:
        raise ProjectError(409, "ra_no_task_object", f"Report Archive 에 code 가 「{key}」 인 과제 객체가 없다 — RA 의 SP 받기가 아직 이 과제를 "
                                                     "싣지 않았거나(받기 꺼짐 · 다음 받기 전) 과제가 SP 에서 지워졌다. 객체를 만드는 일은 RA 관리자 "
                                                     "몫이라 포털은 하지 않는다.")
    if len(exact) > 1:
        raise ProjectError(409, "ra_task_object_ambiguous", f"Report Archive 에 code 가 「{key}」 인 객체가 {len(exact)}개다 — 어느 것인지 "
                                                            "고르지 않고 달지 않았다(RA 관리자가 합치거나 code 를 고친다).")
    return exact[0]


async def project(*, ra, store, row: dict, by: str) -> dict:
    """카드 하나를 RA 에 단다 — 새로 단 원장 줄을 돌려준다. ra 는 그 사람 명의 RA 세션(report_figures._ra). 대상 검사는 부른 쪽이 why_not 으로."""
    key, rid = str(row["sp_task"]), report_id_of(row)
    async with httpx.AsyncClient(timeout=_TIMEOUT, transport=_TRANSPORT) as cli:
        try:
            obj = await find_task_object(ra, cli, key)
            r = await ra.call(cli, "POST", f"/api/reports/{rid}/entities/add", json={"entity_ids": [obj["id"]]})
        except httpx.HTTPError as exc:
            raise ProjectError(502, "ra_unreachable", f"Report Archive 에 닿지 못했습니다({type(exc).__name__}).") from None
    if r.status_code != 200:
        raise _fail(r, "add")
    after = _data(r).get("entity_ids")
    if not isinstance(after, list) or obj["id"] not in after:
        raise ProjectError(502, "ra_outcome_unknown", "Report Archive 의 답에 단 태그가 보이지 않습니다 — 달렸는지 모릅니다(다시 눌러도 겹치지 "
                                                      "않습니다).")
    added = _data(r).get("added")
    rec = {"state": PROJECTED, "report_id": rid, "entity_id": obj["id"], "type_slug": str(obj.get("type_slug") or ""),
           "value": str(obj.get("value") or "")[:255], "added": bool(added) if isinstance(added, int) else None, "at": int(time.time()),
           "by": by.lower()}
    store.meta_set(KEY_PREFIX + row["id"], json.dumps(rec, ensure_ascii=False))
    return rec

