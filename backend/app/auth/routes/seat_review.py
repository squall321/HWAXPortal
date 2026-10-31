# 관리자 '전문가 고르기 검토' — 실사용 질문(H) 후보 · 정답 표시를 에이전트 서버 박스 파일과 공유 비밀로 주고받는다(docs/request-1029 E-5 · E5-2)
"""계약은 docs/request-1029/e5-seat-review-contract.md 다 — 화면 ⇄ 포털이 seat-review/1, 포털 ⇄ 에이전트 서버가 seat-questions/1.

포털은 아무것도 저장하지 않는다 — 후보와 표시는 에이전트 서버의 박스 파일(seat_questions — B0 러너가 읽는다)에 있고, 포털은 관리자 세션 + CSRF 로
받아 에이전트 서버 창구(/seat-questions · /seat-questions/label · /seat-questions/ingest — 공유 비밀)에 넘긴다(도구 검색 검토 E-9 와 같은 꼴).
더 하는 것 셋.
  · 누설 규칙 L6(design-e5 2.1) — 에이전트 서버가 무엇을 실어 보내든 허용 목록으로 다시 걸러, 순위 · 점수 · 지금 좌석(사람이 고른 전문가 · 답한
    좌석)이 화면에 닿지 않게 한다. 전문가 카드는 키 · 이름 · 설명만이다(표본 질문은 표본 신호가 새는 길 L1 이라 싣지 않는다).
  · 사람 이름 — 질문 글은 화면에 낼 때마다 포털 원장의 이름 · 메일 앞부분을 '[이름]' 으로 지운다(지난 날 모으기와 같은 규칙 — harvest.name_re).
    켠 뒤 에이전트 서버가 실시간으로 모은 글은 그 사람 메일의 이름 조각만 지워진 채 박스 파일에 있다(원장은 포털에만 있다). 원장에 없는 이름 ·
    별명은 남는다.
  · 켜기 전의 날들 — 이 박스 대화 저장소에서 출처 셋(지목 전문가 챗 · 띵킹 · '/전문가')을 떼어(이름 · 메일 · 대화 id 를 뗀다) ingest 로 민다.
    에이전트 서버 쪽 스위치(SEAT_QUESTIONS_COLLECT — 기본 꺼짐, D-E5-2)가 꺼져 있으면 저장소를 읽지도 않는다. 창(일)도 그쪽 값을 쓴다.
  · 다는 사람 — 표시자 이름(by)은 이 관리자의 메일(소문자)이다. 누가 다는지는 사람이 정해 에이전트 서버 SEAT_QUESTIONS_LABELERS 에 적는다.

에이전트 서버 답을 포털 답으로 옮기는 법.
  · 공유 비밀 · 주소가 없다 → 503. 401 → 502(공유 비밀이 다르다). 사유 없는 404 · 405 → 502(에이전트 서버가 낡았다 — 창구 없음).
  · 400 · 404(사유 있음) · 409 · 422 는 그쪽 사유 그대로. 닿지 못함 · 그 밖 → 502. 꼴이 다르거나 판(contract)이 다르면 → 502.
"""
import asyncio
import logging
import re

import httpx
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, model_validator

from app.access.policy import ADMIN_GROUP
from app.agent.seat_review_harvest import harvest, name_re, scrub
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import require_csrf, require_role

router = APIRouter(prefix="/auth/admin/seat-review", tags=["seat-review"])
log = logging.getLogger(__name__)

CONTRACT = "seat-review/1"            # 화면 ⇄ 포털
AGENT_CONTRACT = "seat-questions/1"   # 포털 ⇄ 에이전트 서버(그쪽 답에 contract 가 실리면 이 값이어야 한다 — 없으면 이 판의 꼴로 본다)
SOURCES = ("persona", "thinking", "delib", "expert_cmd")
NONE_KINDS = ("core_data", "out_of_pool")
INGEST_MAX = 1000                     # 에이전트 서버 ingest 한 번의 상한
_KEY_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,120}")             # 에이전트 서버 seat_questions._KEY_RE 와 같다
_BY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]{0,39}")        # 에이전트 서버 seat_questions._BY_RE 와 같다
_ID_RE = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_COLLECT_LOCK = asyncio.Lock()        # 모으기는 한 번에 하나 — 대화 저장소를 창만큼 훑는다


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def by_of(principal: Principal) -> str:
    """표시자 이름 — 메일(소문자). 에이전트 서버가 받는 꼴(영문 · 숫자 · '._@-' 40자)이 아니면 메일 앞부분, 그래도 아니면 빈 값(달 수 없다)."""
    e = (principal.email or "").strip().lower()
    for cand in (e, e.split("@", 1)[0][:40]):
        if _BY_RE.fullmatch(cand):
            return cand
    return ""


def _ints(d) -> dict[str, int]:
    """{낱말: 정수} 만 남긴다(셈 칸) — 다른 값 · 꼴이 틀린 키는 버린다."""
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str) and re.fullmatch(r"[a-z][a-z_]{0,31}", k) and _is_int(v)}


def _keys(v, cap: int) -> list[str]:
    return [k for k in (v if isinstance(v, list) else []) if isinstance(k, str) and _KEY_RE.fullmatch(k)][:cap]


def _mine_view(lb) -> dict | None:
    """내 표시 — 그쪽 _label_public 의 꼴만(primary · also · none · unsure · via · memo · t). 모르는 칸은 버린다."""
    if not isinstance(lb, dict):
        return None
    primary, also = _keys(lb.get("primary"), 3), _keys(lb.get("also"), 5)
    via = lb.get("via") if isinstance(lb.get("via"), dict) else {}
    return {"primary": primary, "also": also, "none": lb.get("none") if lb.get("none") in NONE_KINDS else None,
            "unsure": lb.get("unsure") is True, "via": {k: via[k] for k in primary + also if via.get(k) in ("tree", "search")},
            "memo": str(lb.get("memo") or "")[:300], "t": lb["t"] if _is_int(lb.get("t")) else None}


def items_view(d: dict, by: str, nre: re.Pattern | None = None) -> dict:
    """에이전트 서버 /seat-questions 답 → 화면 답(L6 허용 목록). 질문마다 qid · 날짜 · 출처 · 글 · 내 표시 · 남의 표시 수뿐이다 — 그 밖의 칸(순위 ·
    점수 · 좌석 · picked …)은 에이전트 서버가 실어 보내도 여기서 떨어진다. 글은 nre(원장 이름 · 메일 앞부분)와 메일을 지워 낸다. 차례는 그쪽
    그대로(출처를 번갈아 · 출처 안은 qid 의 해시 — 시스템 점수가 아니다)."""
    rows = []
    for it in d.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid, src, text = it.get("qid"), it.get("src"), it.get("text")
        if not (isinstance(qid, str) and _ID_RE.fullmatch(qid) and src in SOURCES and isinstance(text, str)):
            continue
        day = it.get("d")
        rows.append({"qid": qid, "d": day if isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) else None,
                     "src": src, "text": scrub(text, nre)[:2000], "mine": _mine_view(it.get("mine")),
                     "others": it["others"] if _is_int(it.get("others")) else 0})
    lab = d.get("labeled") if isinstance(d.get("labeled"), dict) else {}
    labelers = [x for x in (d.get("labelers") or []) if isinstance(x, str)]
    return {"contract": CONTRACT,
            "total": d["total"] if _is_int(d.get("total")) else len(rows),
            "counts": {k: v for k, v in _ints(d.get("counts")).items() if k in SOURCES},
            "filtered": _ints(d.get("filtered")),
            "labeled": {"mine": lab["mine"] if _is_int(lab.get("mine")) else None,
                        "any": lab["any"] if _is_int(lab.get("any")) else 0},
            "collect": {"on": d.get("collect") is True, "days": d["days"] if _is_int(d.get("days")) else None},
            "labelers_set": bool(labelers),
            # 그쪽 label 이 같은 규칙으로 거른다(SEAT_QUESTIONS_LABELERS 가 비면 누구나 — 글자 그대로 견준다)
            "me": {"by": by or None, "can_label": bool(by) and (not labelers or by in labelers)},
            "items": rows}


def catalog_view(d: dict) -> dict:
    """전문가 명부 — 키 · 이름만, 운영자를 빼고 키 순(조직도 라벨은 화면이 정본 orgTaxonomy.json 으로 붙인다). 태그는 버린다."""
    out: dict[str, dict] = {}
    for e in d.get("pool") or []:
        key = e.get("key") if isinstance(e, dict) else None
        if isinstance(key, str) and _KEY_RE.fullmatch(key) and not key.startswith("he-") and key not in out:
            out[key] = {"key": key, "name": str(e.get("name") or key)[:200]}
    return {"contract": CONTRACT, "experts": [out[k] for k in sorted(out)]}


class LabelIn(BaseModel):
    """그쪽 seat_questions.check_label 과 같은 규칙(by 는 포털이 붙인다) — 운영자를 고를 수 없는 것 하나를 더 본다(평가는 운영자를 뺀 순위다)."""
    qid: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    primary: list[str] = Field(default_factory=list, max_length=3)
    also: list[str] = Field(default_factory=list, max_length=5)
    none: str | None = None
    unsure: bool = False
    via: dict[str, str] = Field(default_factory=dict)
    memo: str = Field(default="", max_length=300)
    remove: bool = False

    @model_validator(mode="after")
    def _shape(self) -> "LabelIn":
        if self.remove:
            return self
        chosen = self.primary + self.also
        bad = [k for k in chosen if not _KEY_RE.fullmatch(k) or k.startswith("he-")]
        if bad:
            raise ValueError(f"전문가 키가 아니거나 운영자다 — {bad[:3]}")
        if len(set(chosen)) != len(chosen):
            raise ValueError("같은 전문가를 두 번(주 · 같이) 골랐다")
        if self.none is not None and self.none not in NONE_KINDS:
            raise ValueError(f"none 은 {list(NONE_KINDS)} 가운데 하나거나 비운다")
        if sum([bool(self.primary), self.none is not None, self.unsure]) != 1:
            raise ValueError("주 전문가(1 ~ 3) · 없음(core_data · out_of_pool) · 모르겠음 가운데 하나만 고른다")
        if self.also and not self.primary:
            raise ValueError("같이 맡을 전문가는 주 전문가가 있을 때만 단다")
        if any(k not in chosen or v not in ("tree", "search") for k, v in self.via.items()):
            raise ValueError("via 는 고른 키 → tree · search 다(나무에서 골랐나 · 찾아서 골랐나)")
        return self


async def _ledger(request: Request) -> tuple[list[str], list[str]]:
    """포털 원장의 사람 이름 · 메일 앞부분 — 질문 글에서 지울 것(이벤트 루프 밖에서 읽는다)."""
    users = await asyncio.to_thread(request.app.state.user_store.list_users)
    return [str(u.get("name") or "") for u in users], [str(u.get("email") or "").split("@", 1)[0] for u in users]


async def _agent(settings: Settings, method: str, path: str, *, params: dict | None = None, body: dict | None = None,
                 timeout: float = 30.0, need: str = "") -> dict:
    """에이전트 서버를 공유 비밀로 부른다. need 는 200 답에 있어야 하는 칸이다(없으면 꼴이 다른 판 — 502)."""
    tok = settings.gateway_shared_token
    base = (settings.agent_server_url or "").rstrip("/")
    if not (tok and base):
        raise AuthError("공유 비밀(backend/.env GATEWAY_SHARED_TOKEN)이나 에이전트 서버 주소(AGENT_SERVER_URL)가 없다", status_code=503)
    try:
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.request(method, f"{base}{path}", params=params, json=body,
                                  headers={"Authorization": f"Bearer {tok}", "X-Seat-Contract": AGENT_CONTRACT})
    except httpx.HTTPError as exc:
        raise AuthError(f"에이전트 서버에 닿지 못했다({type(exc).__name__})", status_code=502) from exc
    try:
        data = r.json()
    except ValueError:
        data = None
    if r.status_code == 200:
        got = data.get("contract", AGENT_CONTRACT) if isinstance(data, dict) else None
        if got != AGENT_CONTRACT or (need and need not in data):
            raise AuthError(f"에이전트 서버 답의 꼴 · 판이 다르다 — 포털은 {AGENT_CONTRACT}(두 리포를 같은 판으로 받는다)", status_code=502)
        return data
    why = str((data.get("error") or data.get("message") or data.get("code") or "") if isinstance(data, dict) else "")[:300]
    if r.status_code == 401:
        raise AuthError("에이전트 서버가 공유 비밀을 거절했다 — 포털 GATEWAY_SHARED_TOKEN 과 에이전트 서버 MCP_CONFIG 의 게이트웨이 토큰이 다르다",
                        status_code=502)
    if r.status_code in (404, 405) and not why:
        raise AuthError("에이전트 서버에 전문가 고르기 검토 창구가 없다 — 에이전트 서버가 이 판보다 낡았다(업데이트 · 재기동 뒤 다시)",
                        status_code=502)
    if r.status_code in (400, 404, 409, 422):
        raise AuthError(why or f"에이전트 서버 {r.status_code}", status_code=r.status_code)
    raise AuthError(f"에이전트 서버 {r.status_code}" + (f" — {why[:200]}" if why else ""), status_code=502)


@router.get("/items")
async def seat_review_items(
    request: Request,
    src: str = Query("", max_length=16),
    offset: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    settings: Settings = Depends(get_settings),
    admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """후보(출처를 번갈아)와 내 표시. 순위 · 점수 · 지금 좌석은 싣지 않는다(L6). 글은 원장 이름 · 메일 앞부분을 지워 낸다."""
    if src and src not in SOURCES:
        raise AuthError(f"src 는 {list(SOURCES)} 가운데 하나다", status_code=422)
    by = by_of(admin)
    d = await _agent(settings, "GET", "/seat-questions", need="items",
                     params={"src": src, "by": by, "limit": limit, "offset": offset})
    names, locals_ = await _ledger(request)
    return items_view(d, by, await asyncio.to_thread(name_re, names, locals_))


@router.get("/catalog")
async def seat_review_catalog(
    settings: Settings = Depends(get_settings),
    admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """전문가 명부(키 · 이름) — 에이전트 서버의 조직도 명부(심의 전 미리보기의 light — 추천을 돌리지 않는다) 그대로, 운영자를 뺀다."""
    d = await _agent(settings, "POST", "/deliberate/experts", need="pool",
                     body={"message": "전체 카탈로그 조회", "groups": admin.groups, "light": True}, timeout=60.0)
    return catalog_view(d)


@router.get("/expert")
async def seat_review_expert(
    key: str = Query(min_length=1, max_length=121),
    settings: Settings = Depends(get_settings),
    admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """전문가 카드 — 이름 · 설명만(표본 질문 · 태그 · 보유 지식 · 역할 문서는 버린다 — L1 · L6)."""
    if not _KEY_RE.fullmatch(key) or key.startswith("he-"):
        raise AuthError("전문가 키가 아니거나 운영자다", status_code=422)
    d = await _agent(settings, "POST", "/catalog/agent", body={"key": key, "groups": admin.groups}, timeout=60.0)
    return {"contract": CONTRACT, "key": key, "name": str(d.get("name") or key)[:200], "desc": str(d.get("role") or "")[:400],
            "error": "detail_failed" if d.get("error") else None}


@router.post("/label", dependencies=[Depends(require_csrf)])
async def seat_review_label(
    body: LabelIn,
    settings: Settings = Depends(get_settings),
    admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """내 정답 표시 → 에이전트 서버 박스 파일. 같은 사람 · 같은 질문은 바꿔 쓰고 remove 는 지운다."""
    by = by_of(admin)
    if not by:
        raise AuthError("이 계정의 메일로는 표시자 이름을 지을 수 없다 — 영문 · 숫자 · '._@-' 40자 이내여야 한다", status_code=409)
    payload = ({"qid": body.qid, "by": by, "remove": True} if body.remove else
               {"by": by, **body.model_dump(exclude={"remove"})})
    d = await _agent(settings, "POST", "/seat-questions/label", body=payload, need="ok")
    return {"contract": CONTRACT, "ok": d.get("ok") is True, "qid": body.qid, "removed": d.get("removed") is True}


@router.post("/collect", dependencies=[Depends(require_csrf)])
async def seat_review_collect(
    request: Request,
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    """켜기 전의 날들 — 이 박스 대화 저장소에서 에이전트 서버 창(SEAT_QUESTIONS_DAYS)만큼의 첫 발화를 떼어 ingest 로 민다. 그쪽 스위치가 꺼져
    있으면 저장소를 읽지 않는다. 같은 글은 그쪽이 qid 로 거른다(다시 눌러도 겹치지 않는다)."""
    if _COLLECT_LOCK.locked():
        raise AuthError("모으기가 이미 돌고 있다 — 끝난 뒤 다시", status_code=409)
    async with _COLLECT_LOCK:
        state = await _agent(settings, "GET", "/seat-questions", params={"limit": 1}, need="items")
        if state.get("collect") is not True:
            raise AuthError("모으기가 꺼져 있다 — 사용자 허락을 받은 박스에서만 에이전트 서버 env 에 SEAT_QUESTIONS_COLLECT=1 을 적고 다시 띄운다"
                            "(사용자 결정 D-E5-2 · docs/request-1029 server-setup 9절). 꺼져 있는 동안 포털은 대화 저장소를 읽지 않는다",
                            status_code=409)
        days = state["days"] if _is_int(state.get("days")) and state["days"] > 0 else 60
        names, locals_ = await _ledger(request)
        try:
            items, stats = await asyncio.to_thread(harvest, settings.resolve(settings.conv_store_path), days=days,
                                                   names=names, locals_=locals_)
        except Exception as exc:  # noqa: BLE001 — 저장소를 못 열면 무엇이 틀렸는지만 말한다(경로는 싣지 않는다)
            raise AuthError(f"대화 저장소를 읽지 못했다({type(exc).__name__})", status_code=503) from exc
        agent = {"added": 0, "dup": 0, "old": 0, "short": 0}
        for i in range(0, len(items), INGEST_MAX):
            d = await _agent(settings, "POST", "/seat-questions/ingest", body={"items": items[i:i + INGEST_MAX]},
                             timeout=120.0, need="added")
            for k in agent:
                agent[k] += d[k] if _is_int(d.get(k)) else 0
    log.info("전문가 고르기 검토 모으기 — 셈 %s · 에이전트 서버 %s", stats, agent)
    return {"contract": CONTRACT, "harvest": stats, "agent": agent}
