# 리스크 심사 종합 보고서 판을 그 사람 명의로 Report Archive 초안으로 — 재료는 리스크 앱이 내주고(게이트웨이 위임) 포털이 RA 에 쓰고 결과를 리스크 앱 원장에 적는다
"""사용자 결정 2026-11-22(docs/leftovers-1121 L21-17 ④) — 리스크 심사 앱은 RA 에 쓰지 않는다(앱에 쓰기 자격을 두지 않는다). 쓰는 것은 포털이다.

창구 하나 — POST /agent/risk-report/ra-draft {target_key, version?}. 사람이 화면에서 누른 호출만 받는다(세션 + CSRF — PAT 로는 못 부른다).
차례.
  ① 그 사람의 RA 연결을 먼저 본다(routes._ra_user_token — 챗 '/보고서' · 그림 넣기 · 발표자료와 같은 함수 하나). 없으면 까닭을 주고 끝이다 —
     리스크 앱을 부르지 않는다(「보내는 중」 을 잡지 않는다). 다른 자격으로 내려가는 길은 없다(2026-09-29 사고의 교훈).
  ② 리스크 앱에서 재료를 받는다 — 게이트웨이 MCP `risk_report_ra_material`, 그 사람의 PAT 로(게이트웨이의 사람별 위임이 그 앱에 그 사람
     신원을 싣는다 — 과제 인사이트가 리스크 앱을 읽는 길과 같다). 편집자 판정 · 박스 스위치 · 한 판에 초안 하나는 리스크 앱이 정한다.
  ③ RA 에 쓴다 — 1쪽을 dry_run 으로 물어 경고가 있으면 만들지 않는다(RA 는 형식이 틀린 블록을 경고만 내고 버린다) → 만든다 → 번호를 먼저
     리스크 앱 원장에 적는다 → 2쪽부터 차례로 붙인다(쪽마다 진행을 적는다) → 다 실렸다고 적는다. 이미 초안이 선 판은 원장의 다음 쪽부터 잇는다.
  ④ 멈추면 리스크 앱 원장에 사실을 적는다 — 확실한 거절은 풀리고, 만드는 호출의 결과를 모르면 「보내는 중」 으로 남고(곧바로 다시 만들면
     초안이 둘이 된다), 붙이다 멈추면 실린 데까지 적힌다.
RA 에 싣는 것은 재료가 준 제목 · 태그 · 템플릿 · 쪽뿐이다 — 템플릿 id · 판은 리스크 앱의 박스 설정 한 곳이 정본이고 포털은 그대로 쓴다. 게시 ·
게시판 · 객체 태그는 부르지도 싣지도 않는다. 포털에 따로 스위치가 없다 — 리스크 앱의 문이 꺼져 있으면 그 앱(또는 도구를 모르는 게이트웨이)의
거절을 정해진 글로 옮긴다. 리스크 앱 · 게이트웨이의 글은 그대로 내지 않는다(REFUSALS 의 글만). 요청이 끊겨도 도는 보내기는 끝까지 간다.
감사에는 번호 · 쪽 수 · 오류 낱말만 남긴다(보고서 글은 남기지 않는다).
"""
from __future__ import annotations

import asyncio
import logging
import re

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent import docforge_delivery as _dfd
from app.agent import report_figures as _figs
from app.agent import upload as _upload
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, get_current_principal, require_csrf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/risk-report", tags=["agent-risk-report"])

NEEDS = ("plat:risk", "plat:reportarchive")
# 게이트웨이가 리스크 앱(heax-hwax_risk) 도구에 붙이는 이름 — 과제 인사이트의 RISK_TOOL 과 같은 접두다.
TOOL_MATERIAL = "heaxhwax_risk_risk_report_ra_material"
TOOL_RECORD = "heaxhwax_risk_risk_report_ra_record"
MATERIAL_TIMEOUT_S = 120.0             # 재료는 보고서 전체 쪽이다
RECORD_TIMEOUT_S = 30.0
_RA_TIMEOUT = httpx.Timeout(300.0, connect=10.0)     # 그림 넣기 · DocForge 배달과 같은 값 — 리스크 앱의 낡음 기한(CLAIM_STALE_S)보다 짧다
_TRANSPORT: httpx.AsyncBaseTransport | None = None   # 시험 이음매 — None 이 아니면 RA 로 가는 요청이 전부 이 전송을 탄다
_TASKS: set[asyncio.Task] = set()      # 도는 보내기 — 요청이 끊겨도 끝까지 가게 붙들어 둔다
TITLE_MAX = 255                        # RA AiDraftCreate.title 상한
_URL_RE = re.compile(r"/w/[^/\s]+/reports/(\d+)")
_CODE_RE = re.compile(r"[A-Za-z0-9_]{1,40}")
_WARN_MAX, _WARN_CHARS, _NOTE_CHARS = 5, 200, 280

# 답의 오류 낱말 → (HTTP 상태, 정해진 글). 리스크 앱 · 게이트웨이 · RA 의 글은 여기 글로 옮긴다.
REFUSALS: dict[str, tuple[int, str]] = {
    "no_person_token": (502, "게이트웨이에 낼 사람 토큰을 만들지 못했습니다 — 다시 로그인한 뒤 시도하세요."),
    "gateway_unreachable": (502, "게이트웨이를 거쳐 리스크 심사 앱을 부르지 못했습니다 — 잠시 뒤 다시 시도하세요."),
    "risk_ra_draft_off": (409, "리스크 심사 앱의 'RA 초안으로 보내기' 가 이 박스에서 꺼져 있습니다(기본값) — 켜는 것은 운영자 몫입니다"
                               "(리스크 앱 knobs.env 의 HWAXRISK_RA_REPORT_DRAFT)."),
    "risk_forbidden": (403, "리스크 심사 앱을 쓸 권한이 없습니다."),
    "risk_not_delegated": (502, "게이트웨이가 리스크 심사 앱에 사람별 위임으로 붙어 있지 않아 누구의 요청인지 확인하지 못했습니다 — 운영자에게 "
                                "알려 주세요."),
    "not_editor": (403, "이 심사 대상의 편집자 이상만 RA 초안으로 보낼 수 있습니다."),
    "target_not_found": (404, "그 심사 대상이 없거나 볼 수 없습니다."),
    "report_absent": (404, "이 대상에는 종합 보고서 판이 아직 없습니다 — 리스크 심사 앱에서 먼저 만드세요."),
    "report_version_moved": (409, "그사이 새 판이 섰습니다 — 화면을 새로 고친 뒤 다시 보내세요."),
    "project_purged": (409, "폐기된 과제의 보고서는 보내지 않습니다."),
    "ra_report_withheld": (409, "비공개 과제의 보고서는 Report Archive 에 올리지 않습니다 — 과제를 조직 공개로 바꾼 뒤 다시 보내세요."),
    "ra_report_empty": (409, "이 판에는 보낼 쪽이 없습니다."),
    "ra_report_in_progress": (409, "이 판은 지금 보내는 중입니다 — 끝난 뒤 다시 확인하세요. 앞 시도가 멈췄으면 15분쯤 뒤에 다시 보낼 수 있습니다."),
    "ra_report_other_author": (409, "이 판의 RA 초안은 다른 사람이 만들다 멈췄습니다 — 초안이 그 사람의 RA 개인 공간에 있어 그 사람만 이어 보낼 수 "
                                    "있습니다."),
    "risk_refused": (502, "리스크 심사 앱이 요청을 받지 않았습니다({code})."),
    "risk_bad_material": (502, "리스크 심사 앱이 준 재료를 읽지 못했습니다 — 포털과 리스크 앱의 판이 맞는지 운영자가 확인해야 합니다."),
    "ledger_unrecorded": (502, "Report Archive 초안(#{report_id})은 만들었는데 리스크 심사 앱에 적지 못했습니다 — 초안은 RA 의 내 공간에 있습니다. "
                               "15분쯤 뒤에 다시 누르면 이어서 맞춥니다."),
    "ra_template_mismatch": (409, "Report Archive 템플릿({template})이 이 보고서의 블록을 받지 않아 만들지 않았습니다 — 리스크 앱의 템플릿 설정"
                                  "(HWAXRISK_RA_REPORT_TEMPLATE · _VERSION)을 운영자가 확인해야 합니다."),
    "ra_template_not_found": (409, "Report Archive 에 템플릿({template})이 없거나 이 계정에 보이지 않아 만들지 않았습니다 — 리스크 앱의 템플릿 "
                                   "설정(HWAXRISK_RA_REPORT_TEMPLATE · _VERSION)을 운영자가 확인해야 합니다."),
    "ra_token_rejected": (502, "Report Archive 가 이 사람의 RA 토큰을 받지 않았습니다(HTTP 401) — 포털 '외부 연결' 의 RA 토큰 · 위임 상태를 "
                               "확인하세요."),
    "ra_forbidden": (403, "Report Archive 가 이 계정의 초안 쓰기를 받지 않았습니다(HTTP 403)."),
    "ra_rejected": (422, "Report Archive 가 받지 않았습니다 — 다시 눌러도 같으면 운영자에게 알려 주세요."),
    "ra_error": (502, "Report Archive 오류로 멈췄습니다 — 잠시 뒤 다시 누르면 실린 다음 쪽부터 이어 보냅니다."),
    "ra_unreachable": (502, "Report Archive 에 연결하지 못했습니다 — 잠시 뒤 다시 누르면 실린 다음 쪽부터 이어 보냅니다."),
    "report_locked": (409, "누가 그 초안의 편집 화면을 열어 두어 쪽을 붙이지 못했습니다 — 편집 화면을 닫은 뒤 다시 보내세요."),
    "ra_draft_gone": (409, "Report Archive 에서 그 초안(#{report_id})을 찾지 못했습니다 — 지워졌다면 이 판은 이어 보낼 수 없습니다(새 판을 만들면 "
                           "새 초안으로 보냅니다)."),
    "ra_outcome_unknown": (502, "Report Archive 가 답하지 않아 초안이 만들어졌는지 알 수 없습니다 — RA 의 내 공간을 확인하세요. 15분쯤 뒤에 다시 "
                                "보낼 수 있습니다(그때 같은 제목의 초안이 둘이면 하나를 지우세요)."),
}
# 리스크 앱이 눕혀 주는 오류 낱말(HWAXRisk routes · report_ra · entry) → 답의 오류 낱말. 여기 없는 낱말은 risk_refused 다.
RISK_CODES: dict[str, str] = {
    "ra_report_off": "risk_ra_draft_off", "role_insufficient": "not_editor", "E404": "target_not_found",
    "delegation_required": "risk_not_delegated", "report_absent": "report_absent", "report_version_moved": "report_version_moved",
    "project_purged": "project_purged", "ra_report_withheld": "ra_report_withheld", "ra_report_empty": "ra_report_empty",
    "ra_report_in_progress": "ra_report_in_progress", "ra_report_other_author": "ra_report_other_author",
}


class DraftError(Exception):
    """정해진 오류 하나 — error 는 REFUSALS 의 낱말. reason · note 는 리스크 앱 원장에 적을 까닭(낱말 · 짧은 글), extra 는 답에 함께 실을 칸."""

    def __init__(self, error: str, *, reason: str = "failed", note: str = "", **extra):
        status, text = REFUSALS[error]
        self.error, self.status, self.reason, self.note, self.extra = error, status, reason, note[:_NOTE_CHARS], extra
        self.template = text
        super().__init__(error)

    @property
    def detail(self) -> str:
        return self.template.format_map({"code": "", "report_id": "?", "template": "?"} | self.extra)


class RaDraftIn(BaseModel):
    target_key: str = Field(min_length=1, max_length=200)     # 리스크 앱 심사 대상 열쇠('snap:…' · 'diff:…')
    version: int | None = Field(default=None, ge=1)           # 보고 있는 판 — 주면 그 판일 때만 보낸다


# ── 리스크 앱(게이트웨이 MCP · 그 사람의 PAT) ────────────────────────────────────────────────────────────────────
async def _risk(settings: Settings, pat: str, tool: str, args: dict, timeout: float) -> dict:
    """리스크 앱의 창구 하나를 그 사람의 PAT 로 부른다 — 답(dict)이거나 DraftError. 앱이 눕힌 오류 봉투의 낱말 · 게이트웨이 거절의 갈래만
    읽고 글은 버린다."""
    try:
        v = await _upload.mcp_verdict(settings.mcp_gateway_url, pat, tool, args, timeout=timeout)
    except (AuthError, httpx.HTTPError, ValueError) as exc:        # 게이트웨이 초기화 실패 · 불통 · 기한 · 읽지 못한 답
        logger.warning("리스크 보고서 RA 초안 — 게이트웨이 호출 실패(%s · %s)", tool, type(exc).__name__)
        raise DraftError("gateway_unreachable") from None
    if v.ok:
        if isinstance(v.parsed, dict):
            return v.parsed
        raise DraftError("risk_bad_material")
    if v.kind == "unknown_tool":
        raise DraftError("risk_ra_draft_off")
    if v.kind in ("forbidden", "denied"):
        raise DraftError("risk_forbidden")
    if v.kind == "unavailable":
        raise DraftError("gateway_unreachable")
    code = v.parsed.get("error") if isinstance(v.parsed, dict) else None
    code = code if isinstance(code, str) and _CODE_RE.fullmatch(code) else ""
    if code in RISK_CODES:
        raise DraftError(RISK_CODES[code])
    raise DraftError("risk_refused", code=code or "unknown")


async def _record(settings: Settings, pat: str, ids: dict, **facts) -> dict:
    return await _risk(settings, pat, TOOL_RECORD, {"target_key": ids["target_key"], "report_uid": ids["report_uid"], **facts},
                       RECORD_TIMEOUT_S)


async def _record_quiet(settings: Settings, pat: str, ids: dict, **facts) -> None:
    """적기를 해 보되 못 적어도 넘어간다 — 멈춘 까닭을 적을 때와 쪽마다 진행을 적을 때(답은 이미 정해졌거나 끝에 다시 적는다)."""
    try:
        await _record(settings, pat, ids, **facts)
    except DraftError as exc:
        logger.warning("리스크 보고서 RA 초안 — 원장 적기 실패(%s · %s)", exc.error, sorted(facts))


def _state(answer: dict) -> str | None:
    """적기의 답에서 원장의 상태."""
    ra = answer.get("ra")
    return ra.get("state") if isinstance(ra, dict) else None


def _url(value, report_id) -> str | None:
    """RA 가 준 주소 — 꼴(/w/<공간>/reports/<번호>)이 맞고 그 번호일 때만 돌려준다(다른 글을 링크로 내지 않는다)."""
    hit = _URL_RE.fullmatch(value) if isinstance(value, str) else None
    return value if hit is not None and isinstance(report_id, int) and int(hit.group(1)) == report_id else None


def _count(value, low: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def _material(mat: dict) -> dict | None:
    """재료의 꼴 — 맞으면 쓸 값만 추린 것, 틀리면 None. RA 에 그대로 실릴 것이라 꼴을 여기서 본다."""
    tpl, ledger, pages = mat.get("template"), mat.get("ra"), mat.get("pages")
    title, tags = mat.get("title"), mat.get("tags")
    if not (isinstance(tpl, dict) and isinstance(tpl.get("id"), str) and tpl["id"] and _count(tpl.get("version"), 1)):
        return None
    if not (isinstance(title, str) and 0 < len(title) <= TITLE_MAX and isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        return None
    if not (isinstance(pages, list) and pages and mat.get("pages_total") == len(pages) and all(
            isinstance(p, dict) and p and all(isinstance(b, str) and isinstance(v, list) and all(isinstance(i, str) for i in v)
                                              for b, v in p.items()) for p in pages)):
        return None
    ledger = ledger if isinstance(ledger, dict) else {}
    rid, sent = ledger.get("report_id"), ledger.get("pages_sent") or 0
    if not ((rid is None or _count(rid, 1)) and _count(sent, 0) and sent <= len(pages) and (rid is not None or sent == 0)):
        return None
    return {"template_id": tpl["id"], "template_version": tpl["version"], "title": title, "tags": tags, "pages": pages,
            "report_id": rid, "sent": sent, "url": _url(ledger.get("url"), rid)}


# ── RA(그 사람의 RA 토큰) ───────────────────────────────────────────────────────────────────────────────────────
def _ra_fail(r: httpx.Response, step: str, **extra) -> DraftError:
    """RA 의 거절 → 정해진 오류. step — preview(1쪽 미리보기) · create(만들기) · append(쪽 붙이기). RA 의 글은 원장의 까닭 칸에만 간다."""
    st = r.status_code
    note = f"HTTP {st} {_dfd._ra_error(r)}"
    if st == 401:
        return DraftError("ra_token_rejected", reason="unauthorized", note=note, **extra)
    if st == 403:
        return DraftError("ra_forbidden", reason="forbidden", note=note, **extra)
    if st == 404:
        return DraftError("ra_draft_gone" if step == "append" else "ra_template_not_found", reason="rejected", note=note, **extra)
    if st == 409 and step == "append":
        return DraftError("report_locked", reason="locked", note=note, **extra)
    if 400 <= st < 500:
        return DraftError("ra_rejected", reason="rejected", note=note, **extra)
    return DraftError("ra_error", reason="transient", note=note, **extra)


def _data(r: httpx.Response) -> dict:
    try:
        d = r.json().get("data")
    except (ValueError, AttributeError):
        d = None
    return d if isinstance(d, dict) else {}


def _warnings(data: dict, page: int | None = None) -> list[str]:
    head = f"{page}쪽: " if page else ""
    return [head + str(w)[:_WARN_CHARS] for w in (data.get("warnings") or [])]


async def _send(settings: Settings, pat: str, ra: _dfd.RaSession, target_key: str, version: int | None, ids: dict) -> dict:
    """재료 → RA 초안 → 원장. ids 는 감사 · 실패 답에 실을 번호들(도는 동안 채운다)."""
    mat = await _risk(settings, pat, TOOL_MATERIAL, {"target_key": target_key} | ({"version": version} if version is not None else {}),
                      MATERIAL_TIMEOUT_S)
    if isinstance(mat.get("report_uid"), str):
        ids.update(report_uid=mat["report_uid"], version=mat.get("version"))
    base = {"ok": True, "target_key": target_key, "report_uid": mat.get("report_uid"), "version": mat.get("version")}
    if mat.get("already") is True:                  # 한 판에 초안 하나 — 이미 다 실렸다. 아무것도 쓰지 않는다
        led = mat.get("ra") if isinstance(mat.get("ra"), dict) else {}
        rid = led.get("report_id")
        ids.update(report_id=rid, pages_sent=led.get("pages_sent"), pages_total=led.get("pages_total"), created=False)
        return {**base, "state": "sent", "already": True, "created": False, "report_id": rid, "url": _url(led.get("url"), rid),
                "pages_sent": led.get("pages_sent"), "pages_total": led.get("pages_total"), "warnings": [], "orphan_possible": False}
    m = _material(mat) if "report_uid" in ids else None
    if m is None:
        if "report_uid" in ids:                     # 잡아 둔 「보내는 중」 을 푼다
            await _record_quiet(settings, pat, ids, error_reason="bad_material", error_text="포털이 재료의 꼴을 읽지 못했다")
        raise DraftError("risk_bad_material")
    pages, total = m["pages"], len(m["pages"])
    rid, sent, url, created, warnings, state = m["report_id"], m["sent"], m["url"], False, [], None
    template = f"{m['template_id']}@{m['template_version']}"
    ids.update(report_id=rid, pages_sent=sent, pages_total=total, created=False)

    async def stop(fail: DraftError, **facts) -> DraftError:
        """멈춘 까닭을 원장에 적고(못 적어도 넘어간다) 그 오류를 돌려준다."""
        await _record_quiet(settings, pat, ids, error_reason=fail.reason, error_text=fail.note, **facts)
        return fail

    async with httpx.AsyncClient(timeout=_RA_TIMEOUT, transport=_TRANSPORT) as cli:
        if rid is None:
            draft = {"template_id": m["template_id"], "template_version": m["template_version"], "title": m["title"],
                     "blocks": pages[0], "tags": m["tags"]}
            # 미리보기 — 만들지 않는다. 여기서 멈추면 어떤 까닭이든 RA 에 생긴 것이 없다(보낸 적 없는 상태로 돌린다).
            try:
                r = await ra.call(cli, "POST", "/api/reports/ai-draft", json={**draft, "dry_run": True})
            except httpx.HTTPError as exc:
                raise await stop(DraftError("ra_unreachable", reason="transient", note=type(exc).__name__)) from None
            if r.status_code >= 400:
                raise await stop(_ra_fail(r, "preview", template=template))
            dropped = _warnings(_data(r))
            if dropped:
                raise await stop(DraftError("ra_template_mismatch", reason="template_mismatch", note=dropped[0], template=template,
                                            warnings=dropped[:_WARN_MAX]))
            # 만들기 — 답을 받지 못하면 초안이 생겼는지 모른다(곧바로 다시 만들면 둘이 된다 — 「보내는 중」 으로 남긴다).
            try:
                r = await ra.call(cli, "POST", "/api/reports/ai-draft", json=draft)
            except httpx.HTTPError as exc:
                raise await stop(DraftError("ra_outcome_unknown", reason="transient", note=type(exc).__name__),
                                 outcome_unknown=True) from None
            if 400 <= r.status_code < 500:              # 확실한 거절 — 만들어지지 않았다
                raise await stop(_ra_fail(r, "create", template=template))
            data = _data(r)
            if r.status_code >= 500 or not _count(data.get("report_id"), 1):
                raise await stop(DraftError("ra_outcome_unknown", reason="transient", note=f"HTTP {r.status_code} {_dfd._ra_error(r)}"),
                                 outcome_unknown=True)
            rid, sent, created = data["report_id"], 1, True
            url = _url(data.get("url"), rid)
            warnings += _warnings(data, 1)
            ids.update(report_id=rid, pages_sent=1, created=True)
            # 번호를 먼저 적는다 — 그 뒤에 끊겨도 초안을 잃지 않는다. 못 적었으면 더 붙이지 않고 번호를 돌려준다.
            try:
                state = _state(await _record(settings, pat, ids, report_id=rid, pages_sent=1, **({"url": url} if url else {})))
            except DraftError:
                raise DraftError("ledger_unrecorded", report_id=rid, url=url, pages_sent=1, pages_total=total, created=True) from None
        where = {"report_id": rid, "url": url, "pages_total": total}
        for n in range(sent + 1, total + 1):
            try:
                r = await ra.call(cli, "PATCH", f"/api/reports/{rid}/ai-draft", json={"page": n, "blocks": pages[n - 1]})
                fail = _ra_fail(r, "append", pages_sent=sent, created=created, **where) if r.status_code >= 400 else None
            except httpx.HTTPError as exc:
                fail = DraftError("ra_unreachable", reason="transient", note=type(exc).__name__, pages_sent=sent, created=created, **where)
            if fail is not None:
                raise await stop(fail, pages_sent=sent)
            sent = n
            warnings += _warnings(_data(r), n)
            ids.update(pages_sent=sent)
            if n < total:                               # 진행 — 못 적어도 보내기는 잇는다(끝에 다시 적는다)
                await _record_quiet(settings, pat, ids, pages_sent=sent)
    if state != "sent":                                 # 한 쪽짜리 판은 번호를 적을 때 이미 닫혔다
        try:
            state = _state(await _record(settings, pat, ids, pages_sent=total))
        except DraftError:
            state = None
    if state != "sent":
        raise DraftError("ledger_unrecorded", pages_sent=total, created=created, **where)
    return {**base, "state": "sent", "already": False, "created": created, "report_id": rid, "url": url, "pages_sent": total,
            "pages_total": total, "warnings": warnings[:_WARN_MAX * 4], "orphan_possible": mat.get("orphan_possible") is True}


# ── 창구 ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _note(audit, principal: Principal, status: str, meta: dict) -> None:
    try:
        audit.record(principal=principal.subject, event="risk_report_ra_draft", status=status, meta=meta)
    except Exception:  # noqa: BLE001 — 감사 실패가 답을 바꾸지 않는다
        logger.warning("리스크 보고서 RA 초안 감사 기록 실패", exc_info=True)


def _refusal(exc: DraftError) -> tuple[int, dict]:
    return exc.status, {"ok": False, "error": exc.error, "detail": exc.detail, **{k: v for k, v in exc.extra.items() if k != "code"}}


async def _job(audit, settings: Settings, principal: Principal, pat: str, ra: _dfd.RaSession, target_key: str,
               version: int | None) -> tuple[int, dict]:
    """보내기 한 번 — (HTTP 상태, 답). 감사를 여기서 적는다(요청이 끊긴 뒤에 끝나도 남게)."""
    ids: dict = {"target_key": target_key}
    try:
        out = await _send(settings, pat, ra, target_key, version, ids)
    except DraftError as exc:
        _note(audit, principal, "failed", ids | {"error": exc.error})
        return _refusal(exc)
    _note(audit, principal, "ok", ids)
    return 200, out


async def _detached(job) -> tuple[int, dict]:
    """요청과 떼어 돌린다 — 브라우저가 떠나 요청이 취소돼도 보내기와 원장 적기는 끝난다(안 그러면 그 판이 리스크 앱에 「보내는 중」 으로
    잡힌 채 낡기를 기다린다)."""
    task = asyncio.ensure_future(job)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return await asyncio.shield(task)


@router.post("/ra-draft")
async def ra_draft(
    request: Request,
    body: RaDraftIn,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
):
    """리스크 심사 종합 보고서의 지금 판을 그 사람의 RA 개인 공간에 초안으로 — 사람이 화면에서 누른 호출만(세션 + CSRF). 답 {ok, state,
    already, created, report_id, url, pages_sent, pages_total, warnings, orphan_possible} · 실패 {ok:false, error, detail, …} 와 맞는 HTTP 상태."""
    ensure(principal, *NEEDS)
    audit = request.app.state.agent_audit
    try:
        try:
            ra = await _figs._ra(request, settings, principal)      # 그 사람의 RA 토큰 — 없으면 여기서 끝(리스크 앱을 부르지 않는다)
        except _figs.FigureError as exc:
            _note(audit, principal, "failed", {"target_key": body.target_key, "error": exc.error})
            return JSONResponse({"ok": False, "error": exc.error, "detail": exc.detail}, status_code=exc.status)
        from app.agent.routes import _chat_user_pat                 # 지연 import — routes 는 이 모듈을 부르지 않는다

        pat = _chat_user_pat(request.app.state.keystore, settings, principal)
        if not pat:
            raise DraftError("no_person_token")
    except DraftError as exc:
        _note(audit, principal, "failed", {"target_key": body.target_key, "error": exc.error})
        status, out = _refusal(exc)
        return JSONResponse(out, status_code=status)
    status, out = await _detached(_job(audit, settings, principal, pat, ra, body.target_key, body.version))
    return out if status == 200 else JSONResponse(out, status_code=status)
