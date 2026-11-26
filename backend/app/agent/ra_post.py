# 심의 보고서 RA 제출 표준 — 박스 파일의 심의 형식 · 시스템 공간 게시판을 읽고, 그 사람 명의로 게시 미리보기 · 게시를 한다(docs/ra-delib-standard)
"""박스 파일 `infra/ra-formats.local.json`(gitignore, `infra/scripts/ra-register-format.py --use` 가 쓴다)의 `deliberation` 줄.

    {"deliberation": {"template_id": "sys.hwax.deliberation", "template_version": 1, "board": "sys-hwax"}}

- 형식 두 칸은 에이전트 서버 `ra_formats.py` · 게이트웨이 `_ra_formats_load` 와 **같은 규칙**으로 읽는다(시험이 세 쪽을 맞댄다). 꼴이 틀리면 기본
  `deliberation` v1 이고 까닭을 남긴다.
- `board` 는 이 박스의 심의 보고서가 올라갈 RA 시스템 공간이다(RS-3). 없거나 꼴이 틀리면 게시하지 않는다 — 초안까지만(지금과 같다). 두 리더는
  이 칸을 무시하므로 칸을 더해도 그쪽 동작이 같다(RS-4).
- 바뀐 시각 · 크기가 다르면 다시 읽는다(재기동 없이).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DEFAULT = ("deliberation", 1)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")          # 에이전트 서버 · 게이트웨이와 같은 id 꼴(RA TemplateCreate)
_BOARD_RE = re.compile(r"(?!\.{1,2}$)[A-Za-z0-9._-]{1,64}")         # RA 공간 slug(String(64)) — 경로를 바꿀 꼴은 받지 않는다

_ROOT = Path(__file__).resolve().parents[3]                          # HWAXPortal — 박스 파일은 이 리포의 infra/ 아래
_ENV = os.environ.get("RA_FORMATS_PATH", "").strip()
PATH = (_ROOT / Path(_ENV).expanduser()) if _ENV else (_ROOT / "infra" / "ra-formats.local.json")

_STATE: dict = {"key": "아직 읽지 않음", "row": None, "board": None, "error": None}


def _load() -> dict:
    try:
        st = PATH.stat()
        key = (str(PATH), st.st_mtime_ns, st.st_size)
    except OSError:
        key = (str(PATH), None, None)
    if key == _STATE["key"]:
        return _STATE
    row, board, error = None, None, None
    if key[1] is not None:
        try:
            doc = json.loads(PATH.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("객체가 아니다")
        except (OSError, ValueError) as exc:
            error, doc = f"못 읽음({type(exc).__name__})", {}
        got = doc.get("deliberation")
        if got is not None:
            tid = got.get("template_id") if isinstance(got, dict) else None
            ver = got.get("template_version") if isinstance(got, dict) else None
            if isinstance(tid, str) and _ID_RE.fullmatch(tid) and isinstance(ver, int) and not isinstance(ver, bool) and ver >= 1:
                row = (tid, ver)
                b = got.get("board")
                if isinstance(b, str) and _BOARD_RE.fullmatch(b):
                    board = b
                elif b is not None:
                    error = "deliberation 줄의 board 꼴이 틀렸다 — 게시하지 않는다"
            else:
                error = "deliberation 줄의 꼴이 틀렸다 — 기본값으로 돌고 게시하지 않는다"
        if error:
            logger.warning("ra-formats: %s — %s", PATH.name, error)
    _STATE.update(key=key, row=row, board=board, error=error)
    return _STATE


def deliberation_template() -> tuple[str, int]:
    """심의 보고서의 (template_id, template_version) — 박스 파일의 줄이 맞으면 그것, 아니면 기본 deliberation v1."""
    return _load()["row"] or DEFAULT


def box_template() -> tuple[str, int] | None:
    """박스 파일이 정한 심의 형식 — 줄이 없거나 꼴이 틀리면 None(부르는 쪽이 자기 값을 그대로 쓴다)."""
    return _load()["row"]


def deliberation_board() -> str | None:
    """이 박스의 심의 보고서가 올라갈 RA 시스템 공간 slug — 형식 줄이 맞고 board 가 있을 때만(아니면 None — 게시하지 않는다)."""
    st = _load()
    return st["board"] if st["row"] else None


def status() -> dict:
    """/agent/ra/post-target 의 몸 — 화면이 단추를 그릴지 정한다."""
    st = _load()
    tid, ver = deliberation_template()
    return {"board": deliberation_board(), "template_id": tid, "template_version": ver,
            "source": "box" if st["row"] else "default", "error": st["error"]}


class PostError(Exception):
    """게시 길의 정해진 실패 — status(포털 답의 HTTP) · code(화면이 고르는 낱말) · message(사람에게)."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _targets(r: httpx.Response) -> tuple[list[dict], str | None]:
    """RA `/api/mounts/preview` 답 → (대상 줄들, 확인 토큰). 대상 줄은 화면에 낼 칸만 추린다."""
    try:
        data = (r.json() or {}).get("data") or {}
    except (ValueError, AttributeError):
        data = {}
    rows = data.get("targets") if isinstance(data, dict) else None
    out = []
    for t in rows if isinstance(rows, list) else []:
        if not isinstance(t, dict) or not isinstance(t.get("slug"), str):
            continue
        out.append({"slug": t["slug"], "name": str(t.get("name") or t["slug"])[:128],
                    "audience": t["audience"] if isinstance(t.get("audience"), int) and not isinstance(t.get("audience"), bool) else None,
                    "already_mounted": t.get("already_mounted") is True,
                    "blocked": str(t.get("blocked") or t.get("error") or "")[:300] or None})
    token = data.get("confirm_token") if isinstance(data, dict) else None
    return out, token if isinstance(token, str) and token else None


def _fail(r: httpx.Response, step: str) -> PostError:
    from app.agent import docforge_delivery as _dfd     # RA 거절 글 읽기는 한 곳(_ra_error)
    st, why = r.status_code, _dfd._ra_error(r)
    if st == 401:
        return PostError(502, "ra_token_rejected", "Report Archive 가 이 사람의 RA 토큰을 받지 않았습니다(HTTP 401) — 포털 '외부 연결' 의 RA 토큰 · "
                                                    "위임 상태를 확인하세요.")
    if st == 403:
        return PostError(403, "forbidden_by_ra", f"Report Archive 가 게시를 허락하지 않았습니다(HTTP 403 {why}) — 보고서 작성자이고 그 게시판에 "
                                                 "올릴 수 있는 부서여야 합니다.")
    if st == 404:
        return PostError(404, "not_found", f"Report Archive 에 그 보고서나 게시판이 없습니다(HTTP 404 {why}).")
    if 400 <= st < 500:
        return PostError(422, "ra_rejected", f"Report Archive 가 받지 않았습니다(HTTP {st} {why}).")
    return PostError(502, "ra_error", f"Report Archive 오류({step} — HTTP {st} {why}) — 잠시 뒤 다시 하세요.")


async def preview(ra, cli: httpx.AsyncClient, report_id: int, board: str) -> tuple[list[dict], str | None]:
    """그 사람 명의로 RA 게시 미리보기 — 실제로 게시하지 않는다. (대상 줄들, 확인 토큰). 못 올릴 곳이면 토큰이 None 이다."""
    try:
        r = await ra.call(cli, "POST", "/api/mounts/preview", json={"report_id": report_id, "workspace_slugs": [board]})
    except httpx.HTTPError as exc:
        raise PostError(502, "ra_unreachable", f"Report Archive 에 닿지 못했습니다({type(exc).__name__}).") from None
    if r.status_code != 200:
        raise _fail(r, "미리보기")
    return _targets(r)


async def post(ra, cli: httpx.AsyncClient, report_id: int, board: str) -> dict:
    """사람이 미리보기를 보고 확인한 뒤 — 미리보기를 다시 받아(게시판 구성 · 권한이 바뀌었을 수 있다) 그 확인 토큰과 함께 게시한다(RS-3)."""
    targets, token = await preview(ra, cli, report_id, board)
    hit = next((t for t in targets if t["slug"] == board), None)
    if hit is None or hit["blocked"] or not token:
        why = (hit or {}).get("blocked") or "게시판을 찾지 못했습니다"
        raise PostError(409, "blocked", f"이 게시판에는 올릴 수 없습니다 — {why}")
    if hit["already_mounted"]:
        return {"board": board, "name": hit["name"], "mounted": False, "already": True}
    try:
        r = await ra.call(cli, "POST", "/api/mounts", json={"report_id": report_id, "workspace_slugs": [board],
                                                            "confirm_token": token, "note": "HWAX 심의 보고서"})
    except httpx.HTTPError as exc:
        # 답을 못 받았다 — 게시됐는지 모른다. 다시 누르면 미리보기가 already_mounted 로 알려 준다(게시는 게시판마다 한 번만)
        raise PostError(502, "ra_outcome_unknown", f"Report Archive 의 답을 받지 못했습니다({type(exc).__name__}) — 게시됐는지 모릅니다. "
                                                   "잠시 뒤 다시 누르면 이미 게시됐는지 알려 줍니다.") from None
    if r.status_code != 200:
        raise _fail(r, "게시")
    return {"board": board, "name": hit["name"], "mounted": True, "already": False}
