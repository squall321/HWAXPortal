# 도구 그림 한 장을 그 사람 명의로 Report Archive 에 넣는 창구 — 게이트웨이(개인 Claude)는 보고서 쪽 끝에 그림 칸까지, 에이전트 서버(/보고서 · 심의 보고서)는 올리기만(docs/report-figures)
"""사용자 신고(2026-11-02) — StepForge · DynaForge 도구가 낸 그림이 인사이트에서 쓴 보고서에 한 장도 들어가지 않는다.

창구 둘(둘 다 multipart — `meta` JSON 칸 하나 + `file` 칸 하나, docs/report-figures RF-1)
  · POST /agent/figures/to-report — 게이트웨이 계약. meta = {report_id, caption, page?, tool, mime, sha256, filename, ref}. 그 사람 명의로 RA
    `POST /api/files` 에 올리고 그 보고서의 page 쪽(없으면 마지막 쪽) 끝에 그림 칸 하나를 붙인다(`PATCH /api/reports/{id}/ai-draft` 의 extra_blocks).
    답 {ok, report_id, file_id, page, block_index, url, block_id, replaced} · 실패 {ok:false, error, detail} 와 맞는 HTTP 상태(RF-8 표).
  · POST /agent/figures/upload — 같은 검사 · 같은 올리기, 보고서는 건드리지 않는다. 에이전트 서버가 /보고서 · 심의 보고서를 만들기 **전에** 그림을
    올려 file_id 를 받고, 보고서를 만드는 한 번의 호출에 그림 칸을 싣는다 — 그래야 못 올린 그림의 까닭을 본문 그 자리에 쓸 수 있다.
자격 — 게이트웨이가 포털로 넘기는 다른 창구(대화 저장 /agent/conversations)와 같은 principal_pat_or_session(사람 PAT 또는 세션 + CSRF). 쓰기라
읽기 전용 PAT 는 403, plat:reportarchive 가 없으면 403. RA 토큰은 그 사람의 것(routes._ra_user_token)이고 서비스 계정으로 내려가는 길은 없다.
RA 에 올리는 길은 DocForge 배달과 같은 RaSession 하나다(RF-3). 기록 · 로그에는 그림 바이트 · 캡션 글을 남기지 않는다(번호 · 크기 · 꼴만).
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import re

import httpx
import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agent import docforge_delivery as _dfd
from app.auth import ra_sso
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, principal_pat_or_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/figures", tags=["agent-figures"])

# 받는 그림 꼴 → RA 에 올릴 확장자. SVG 는 받지 않는다 — 스크립트를 품을 수 있고 RA 가 자기 주소에서 그대로 낸다(RF-4).
_MIME_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}
_MIME_ALIAS = {"image/jpg": "image/jpeg"}
_META_MAX = 16 * 1024                  # meta JSON 칸 상한
_BODY_SLACK = 64 * 1024                # multipart 머리 · 경계 · meta 몫 — Content-Length 는 그림 상한 + 이만큼까지
_CAPTION_MAX = 500                     # RA image 위젯 files[].caption 상한(ReportArchive widgets/registry.py _image_content)
_ALT_MAX = 200                         # files[].alt 상한
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_RA_TIMEOUT = httpx.Timeout(300.0, connect=10.0)     # DocForge 배달과 같은 값 — 에이전트 서버는 이보다 길게 기다린다(RF-12)
_LOCKS: dict[int, asyncio.Lock] = {}   # 보고서마다 하나 — RA 의 ai-draft PATCH 는 읽고 · 합치고 · 쓴다(병렬 호출이 칸을 덮지 않게, RF-6)
_TRANSPORT: httpx.AsyncBaseTransport | None = None   # 시험 이음매 — None 이 아니면 RA 로 가는 요청이 전부 이 전송을 탄다


class FigureError(Exception):
    def __init__(self, status: int, error: str, detail: str):
        super().__init__(detail)
        self.status, self.error, self.detail = status, error, detail


def _sniff(raw: bytes) -> str | None:
    """바이트의 머리로 그림 꼴 — 이름 · 선언이 아니라 내용으로 본다(에이전트 서버 vision.sniff 와 같은 넷)."""
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return None


def _read_only_pat(request: Request) -> bool:
    """읽기 전용 PAT 인가 — 게이트웨이 rest_proxy.is_read_only · 루틴 창구 routine_routes._read_only_pat 와 같은 판정(scopes 에 read 가 있고
    write 가 없을 때만). 칸이 없는 옛 PAT 와 챗 PAT(['chat'] — 웹 챗 /보고서 의 에이전트 서버가 그 토큰으로 부른다)는 아니다. 서명 · 청중 · 만료 ·
    폐기는 principal_pat_or_session 이 같은 머리로 이미 봤다 — 여기서는 scopes 칸만 읽는다. 루틴의 함수를 import 하지 않는 것은 절차 라우터
    등록이 실패해도 포털이 뜨게 둔 자리(main.py)라서다 — 같은 판정인지는 시험이 표로 견준다(RF-2)."""
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() != "bearer ":
        return False
    raw = jwt.decode(auth[7:].strip(), options={"verify_signature": False}).get("scopes")
    if not isinstance(raw, list):
        return False
    s = {str(x).strip().lower() for x in raw}
    return "read" in s and "write" not in s


def _limit(settings: Settings) -> int:
    """RA `/api/files` 상한 — DocForge 배달과 같은 손잡이(같은 RA 의 같은 상한이다, RF-4)."""
    return int(settings.docforge_ra_file_max_mb) * 1024 * 1024


async def _accept(request: Request, principal: Principal, settings: Settings) -> tuple[dict, bytes]:
    """쓰기 자격 → 본문 길이 → multipart 읽기. 자격을 본문보다 먼저 본다(남이 큰 본문을 보내 디스크를 채우지 못하게)."""
    if _read_only_pat(request):
        raise FigureError(403, "read_only_token", "읽기 전용 토큰으로는 Report Archive 에 그림을 넣지 못합니다 — 쓰기 범위(write)가 있는 토큰을 쓰세요.")
    try:
        ensure(principal, "plat:reportarchive")
    except AuthError as exc:
        raise FigureError(403, "forbidden", exc.message) from None
    limit = _limit(settings)
    cl = request.headers.get("content-length", "")
    if not cl.isdigit():
        raise FigureError(411, "length_required", "길이(Content-Length)가 없는 본문은 받지 않습니다.")
    if int(cl) > limit + _BODY_SLACK:
        raise FigureError(413, "too_large", f"그림이 Report Archive 상한({settings.docforge_ra_file_max_mb}MB)을 넘습니다.")
    try:
        async with request.form(max_files=2, max_fields=2, max_part_size=_META_MAX) as form:
            meta_part, file_part = form.get("meta"), form.get("file")
            if meta_part is None or file_part is None or isinstance(file_part, str):
                raise FigureError(400, "bad_request", "multipart 에 meta(JSON) 칸과 file 칸이 둘 다 있어야 합니다.")
            if not isinstance(meta_part, str):            # meta 를 파일 칸으로 보냈다
                meta_part = (await meta_part.read(_META_MAX + 1)).decode("utf-8", "replace")
            raw = await file_part.read(limit + 1)
    except StarletteHTTPException as exc:                 # 칸 수 · meta 크기 상한을 넘은 multipart
        raise FigureError(400, "bad_request", f"multipart 를 읽지 못했습니다({exc.detail}).") from None
    if len(meta_part) > _META_MAX:
        raise FigureError(400, "bad_meta", f"meta 가 {_META_MAX // 1024}KB 를 넘습니다.")
    try:
        meta = json.loads(meta_part)
    except ValueError:
        meta = None
    if not isinstance(meta, dict):
        raise FigureError(400, "bad_meta", "meta 가 JSON 객체가 아닙니다.")
    return meta, raw


def _text(meta: dict, key: str) -> str:
    v = meta.get(key)
    if v is None:
        return ""
    if not isinstance(v, str):
        raise FigureError(400, "bad_meta", f"meta.{key} 는 글이어야 합니다.")
    return v.strip()


def _int(meta: dict, key: str) -> int | None:
    v = meta.get(key)
    if v is None:
        return None
    if isinstance(v, str) and v.strip().isdigit():
        v = int(v.strip())
    if not isinstance(v, int) or isinstance(v, bool) or v < 1:
        raise FigureError(400, "bad_meta", f"meta.{key} 는 1 이상의 정수여야 합니다.")
    return v


def _filename(given: str, sha: str, ext: str) -> str:
    """RA 에 남길 파일 이름 — 준 이름의 줄기(경로 · 확장자 뗌, 글자 · 숫자 · _ . - 만)에 내용의 확장자. 비면 figure-<sha 앞 12자>."""
    stem = re.split(r"[\\/]", given)[-1]
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", stem)
    stem = re.sub(r"[^\w.-]+", "_", stem).strip("._")[:60]
    return f"{stem or 'figure-' + sha[:12]}.{ext}"


def _check(meta: dict, raw: bytes, settings: Settings, *, need_report: bool) -> dict:
    """그림 검사 — 꼴(선언 · 내용) · 크기 · sha256 · meta 칸. 통과하면 올릴 값을 돌려준다(RF-4)."""
    if len(raw) > _limit(settings):
        raise FigureError(413, "too_large", f"그림이 Report Archive 상한({settings.docforge_ra_file_max_mb}MB)을 넘습니다.")
    if not raw:
        raise FigureError(400, "empty_file", "그림 파일이 비었습니다.")
    declared = _text(meta, "mime").lower()
    declared = _MIME_ALIAS.get(declared, declared)
    if "svg" in declared:
        raise FigureError(415, "unsupported_media_type",
                          "SVG 는 Report Archive 그림으로 넣지 않습니다 — 스크립트를 품을 수 있는 꼴이라 PNG · JPEG · GIF · WebP 만 받습니다"
                          "(도구가 PNG 로 내게 하세요).")
    if declared not in _MIME_EXT:
        raise FigureError(415, "unsupported_media_type",
                          f"그림 꼴({declared or '없음'})을 받지 않습니다 — PNG · JPEG · GIF · WebP 만 받습니다.")
    real = _sniff(raw)
    if real is None:
        raise FigureError(415, "unsupported_media_type", f"내용이 PNG · JPEG · GIF · WebP 그림이 아닙니다(선언 {declared}).")
    sha = _text(meta, "sha256").lower()
    if not _SHA_RE.fullmatch(sha):
        raise FigureError(400, "bad_meta", "meta.sha256(64자리 16진)이 없습니다.")
    if hashlib.sha256(raw).hexdigest() != sha:
        raise FigureError(400, "sha256_mismatch", "받은 바이트의 sha256 이 meta.sha256 과 다릅니다 — 보내는 도중 바뀌었거나 다른 파일입니다.")
    caption = _text(meta, "caption")
    if len(caption) > _CAPTION_MAX:
        caption = caption[:_CAPTION_MAX - 1] + "…"
    tool = _text(meta, "tool")[:200]
    out = {"sha256": sha, "mime": real, "caption": caption, "tool": tool,
           "alt": (caption or (f"{tool} 그림" if tool else "도구 그림"))[:_ALT_MAX],
           "filename": _filename(_text(meta, "filename"), sha, _MIME_EXT[real]), "ref": _text(meta, "ref")[:200]}
    if need_report:
        rid = _int(meta, "report_id")
        if rid is None:
            raise FigureError(400, "bad_meta", "meta.report_id 가 없습니다.")
        out["report_id"], out["page"] = rid, _int(meta, "page")
    return out


def block(file_id: str, sha256: str, caption: str, alt: str) -> dict:
    """그림 칸 하나 — RA image 위젯(RF-5). id 는 RA 블록 id 규칙(^[a-z][a-z0-9_]{0,63}$)에 맞고, 같은 그림이면 같은 id 라 다시 넣어도 칸이 늘지
    않는다. content 는 additionalProperties:false 라 file_id · caption · alt 밖의 칸을 넣지 않는다."""
    f: dict = {"file_id": file_id}
    if caption:
        f["caption"] = caption
    if alt:
        f["alt"] = alt
    return {"id": f"fig_{sha256[:16]}", "type": "image", "props": {"max_count": 1}, "content": {"files": [f]}}


async def _ra(request: Request, settings: Settings, principal: Principal) -> _dfd.RaSession:
    """그 사람 명의 RA 세션 — 토큰은 챗 업로드 · 정밀 변환 · 발표자료와 같은 함수 하나로(위임 먼저 · 등록 토큰 다음, 서비스 계정 없음)."""
    from app.agent.routes import _ra_user_token     # 지연 import — routes 는 이 모듈을 부르지 않는다

    try:
        token, via_sso, conn = await _ra_user_token(request, settings, principal)
    except AuthError as exc:
        raise FigureError(exc.status_code, "no_ra_connection", exc.message) from None
    remint = None
    if via_sso:
        email = principal.email or principal.subject

        async def remint() -> str | None:
            ra_sso.forget(email)
            return await ra_sso.ra_user_token(settings, email=email, name=principal.display_name or "")
    return _dfd.RaSession(settings.ra_base_url, token, conn.get("workspace") or "", remint)


def _ra_fail(r: httpx.Response, step: str, *, left: str = "") -> FigureError:
    """RA 의 거절 → 포털 답(RF-8). step — outline(보고서 보기) · upload(파일 올리기) · patch(그림 칸 붙이기). left 는 이미 RA 에 남은 것."""
    st, why = r.status_code, _dfd._ra_error(r)
    tail = f" {left}" if left else ""
    if st == 401:
        return FigureError(502, "ra_token_rejected", "Report Archive 가 이 사람의 RA 토큰을 받지 않았습니다(HTTP 401) — 포털 '외부 연결' 의 "
                                                     f"RA 토큰 · 위임 상태를 확인하세요.{tail}")
    if st == 403:
        if step == "upload":
            return FigureError(403, "forbidden_by_ra", f"Report Archive 가 그림 파일을 받지 않았습니다(HTTP 403 {why}).{tail}")
        return FigureError(403, "not_editable", f"Report Archive 가 이 보고서에 그림을 넣지 못하게 했습니다(HTTP 403 {why}) — "
                                                f"편집 권한이 없거나 발행된 보고서입니다.{tail}")
    if st == 404:
        return FigureError(404, "report_not_found", f"그 보고서가 Report Archive 에 없습니다(HTTP 404 {why}).{tail}")
    if st == 409:
        return FigureError(409, "report_locked", f"누가 그 보고서의 편집 화면을 열어 두어 그림을 넣지 못했습니다(HTTP 409 {why}) — 편집 화면을 "
                                                 f"닫은 뒤 다시 보내세요.{tail}")
    if st == 413:
        return FigureError(413, "too_large", f"Report Archive 가 크기 상한으로 받지 않았습니다(HTTP 413 {why}).{tail}")
    if st == 415:
        return FigureError(415, "unsupported_media_type", f"Report Archive 가 그림 꼴을 받지 않았습니다(HTTP 415 {why}).{tail}")
    if 400 <= st < 500:
        return FigureError(422, "ra_rejected", f"Report Archive 가 받지 않았습니다(HTTP {st} {why}).{tail}")
    return FigureError(502, "ra_error", f"Report Archive 오류(HTTP {st} {why}) — 잠시 뒤 다시 보내세요.{tail}")


def _data(r: httpx.Response, what: str) -> dict:
    try:
        d = r.json().get("data")
    except (ValueError, AttributeError):
        d = None
    if not isinstance(d, dict):
        raise FigureError(502, "ra_error", f"Report Archive 의 {what} 답을 읽지 못했습니다(HTTP {r.status_code}).")
    return d


async def _upload(ra: _dfd.RaSession, cli: httpx.AsyncClient, fig: dict, raw: bytes) -> str:
    r = await ra.upload(cli, fig["filename"], io.BytesIO(raw), fig["mime"])
    if r.status_code >= 400:
        raise _ra_fail(r, "upload")
    fid = (_data(r, "파일 올리기").get("id"))
    if not fid:
        raise FigureError(502, "ra_error", "Report Archive 가 올린 그림의 번호(file_id)를 돌려주지 않았습니다.")
    return str(fid)


async def _to_report(ra: _dfd.RaSession, fig: dict, raw: bytes) -> dict:
    rid = fig["report_id"]
    async with _LOCKS.setdefault(rid, asyncio.Lock()), httpx.AsyncClient(timeout=_RA_TIMEOUT, transport=_TRANSPORT) as cli:
        r = await ra.call(cli, "GET", f"/api/reports/{rid}/outline")
        if r.status_code >= 400:
            raise _ra_fail(r, "outline")
        outline = _data(r, "보고서 구조")
        pages = outline.get("pages") if isinstance(outline.get("pages"), list) else []
        n = outline.get("page_count") if isinstance(outline.get("page_count"), int) else len(pages)
        if n < 1:
            raise FigureError(502, "ra_error", "Report Archive 가 그 보고서의 쪽 수를 주지 않았습니다.")
        page = fig["page"] or n
        if page > n:
            raise FigureError(400, "bad_page", f"그 보고서에는 {n}쪽까지 있습니다(page={page}). 없으면 마지막 쪽에 넣습니다.")
        cur = pages[page - 1] if len(pages) >= page and isinstance(pages[page - 1], dict) else {}
        had = {b.get("block_id") for b in (cur.get("blocks") or []) if isinstance(b, dict)}
        fid = await _upload(ra, cli, fig, raw)
        left = f"올린 그림 파일({fid})은 Report Archive 에 남았습니다."
        blk = block(fid, fig["sha256"], fig["caption"], fig["alt"])
        r = await ra.call(cli, "PATCH", f"/api/reports/{rid}/ai-draft", json={"page": page, "extra_blocks": [blk]})
        if r.status_code >= 400:
            raise _ra_fail(r, "patch", left=left)
        data = _data(r, "그림 칸 붙이기")
    # RA 는 형식이 틀린 칸을 경고만 남기고 버린다 — 답의 그 쪽에 우리 칸이 있어야 넣은 것이다(RF-7)
    rp = (data.get("report") or {}).get("pages") if isinstance(data.get("report"), dict) else None
    order = rp[page - 1].get("blocks_order") if isinstance(rp, list) and len(rp) >= page and isinstance(rp[page - 1], dict) else None
    if not isinstance(order, list) or blk["id"] not in order:
        warns = [str(w)[:200] for w in (data.get("warnings") or [])][:5]
        raise FigureError(502, "ra_dropped_block", "Report Archive 가 그림 칸을 받지 않았습니다"
                                                   + (f"({' / '.join(warns)})" if warns else "") + f" — {left}")
    url = data.get("url") if isinstance(data.get("url"), str) else None
    return {"ok": True, "report_id": rid, "file_id": fid, "page": page, "block_index": order.index(blk["id"]),
            "url": url, "block_id": blk["id"], "replaced": blk["id"] in had}


def _audit(request: Request, principal: Principal, event: str, status: str, **meta) -> None:
    try:
        request.app.state.agent_audit.record(principal=principal.subject, event=event, status=status, meta=meta)
    except Exception:  # noqa: BLE001 — 감사 실패가 답을 바꾸지 않는다
        logger.warning("그림 넣기 감사 기록 실패(%s)", event, exc_info=True)


def _failed(request: Request, principal: Principal, event: str, exc: FigureError, ids: dict) -> JSONResponse:
    _audit(request, principal, event, "failed", error=exc.error, detail=exc.detail[:300], **ids)
    return JSONResponse({"ok": False, "error": exc.error, "detail": exc.detail}, status_code=exc.status)


def _ids(fig: dict | None, raw: bytes | None) -> dict:
    """감사에 남길 것 — 번호 · 크기 · 꼴 · 도구 이름만(바이트 · 캡션 글은 남기지 않는다)."""
    if not fig:
        return {}
    return {k: fig.get(k) for k in ("report_id", "page", "mime", "tool", "ref") if fig.get(k) is not None} | \
        ({"bytes": len(raw)} if raw is not None else {})


@router.post("/to-report")
async def figure_to_report(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """그림 한 장을 그 사람 명의로 RA 에 올리고 그 보고서의 page 쪽(없으면 마지막 쪽) 끝에 그림 칸 하나를 붙인다 — 게이트웨이 계약(RF-1).
    편집 권한은 RA 가 정한다(거절은 403). 같은 그림을 같은 쪽에 다시 넣으면 그 칸을 갈아 끼운다(replaced)."""
    fig = raw = None
    try:
        meta, raw = await _accept(request, principal, settings)
        fig = _check(meta, raw, settings, need_report=True)
        ra = await _ra(request, settings, principal)
        out = await _to_report(ra, fig, raw)
    except FigureError as exc:
        return _failed(request, principal, "figure_to_report", exc, _ids(fig, raw))
    except httpx.HTTPError as exc:
        return _failed(request, principal, "figure_to_report",
                       FigureError(502, "ra_unreachable", f"Report Archive 에 연결하지 못했습니다({exc.__class__.__name__})."), _ids(fig, raw))
    _audit(request, principal, "figure_to_report", "ok", file_id=out["file_id"], block_id=out["block_id"], replaced=out["replaced"],
           **_ids(fig, raw) | {"page": out["page"]})
    return out


@router.post("/upload")
async def figure_upload(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """그림 한 장을 그 사람 명의로 RA 에 올리기만 한다 — {ok, file_id}. 에이전트 서버가 /보고서 · 심의 보고서를 만들기 전에 부르고, 그림 칸은
    보고서를 만드는 호출에 직접 싣는다(RF-1 · RF-9). 검사 · 자격은 to-report 와 같다(보고서 칸만 없다)."""
    fig = raw = None
    try:
        meta, raw = await _accept(request, principal, settings)
        fig = _check(meta, raw, settings, need_report=False)
        ra = await _ra(request, settings, principal)
        async with httpx.AsyncClient(timeout=_RA_TIMEOUT, transport=_TRANSPORT) as cli:
            fid = await _upload(ra, cli, fig, raw)
    except FigureError as exc:
        return _failed(request, principal, "figure_upload", exc, _ids(fig, raw))
    except httpx.HTTPError as exc:
        return _failed(request, principal, "figure_upload",
                       FigureError(502, "ra_unreachable", f"Report Archive 에 연결하지 못했습니다({exc.__class__.__name__})."), _ids(fig, raw))
    _audit(request, principal, "figure_upload", "ok", file_id=fid, **_ids(fig, raw))
    return {"ok": True, "file_id": fid}
