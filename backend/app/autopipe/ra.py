# 자동 파이프라인 보고서의 RA 게시 — 박스 파일 auto_pipeline 줄이 있을 때만, 시스템 계정 토큰(0600 파일)으로 초안 → 게시판 연결(AP-D3 · AP-10)
"""박스 파일은 심의 형식과 같은 `infra/ra-formats.local.json`(gitignore — 경로는 app/agent/ra_post.PATH, RA_FORMATS_PATH 로 바꾼다)이다.

    {"auto_pipeline": {"board": "sys-<시스템>", "token_file": "infra/secrets/ra-auto-pipeline.token",
                       "formats": {"summary": {"template_id": "…", "template_version": 1}, "per_analysis": {…}, "revdiff": {…}}}}

- 줄이 없으면 게시하지 않는다 — 보고서는 포털 원장에만 있고 /health 가 「RA 미설정」을 말한다.
- 토큰 파일은 리포 루트 기준 상대 경로(박스마다 리포 경로가 다르다)이고 0600 이어야 한다(그룹 · 남이 읽을 수 있으면 쓰지 않는다). 값은 로그 ·
  응답 · 원장에 싣지 않는다 — 읽어서 RA 요청 머리에만 쓴다.
- 길 — RA `POST /api/reports/ai-draft` 를 dry_run 으로 먼저 물어 경고(형식이 블록을 받지 않음)가 있으면 만들지 않는다 → 만든다 → `POST /api/mounts`
  (게시판 = board). 게이트웨이를 거치지 않는다(사람 · Claude 길의 create_report_from_format 막기와 무관 — AP-3). X-Client: mcp 를 싣지 않으니 RA 의
  확인 토큰 단계가 없고, 시스템 계정은 관리자가 게시판을 미리 연결한 것이 사전 승인이다(RA 문서 §6.4). 게시는 게시판마다 한 번이라 다시 해도 겹치지 않는다.
- 만들기의 답을 잃으면 초안이 생겼는지 모른다 — 다시 만들지 않는다(같은 보고서가 둘이 된다). 원장에 ra_outcome_unknown 으로 남긴다.
- 에이전트 서버 · 게이트웨이의 박스 파일 리더는 이 줄을 「모르는 종류」로 경고하고 그 줄만 버린다(심의 형식 줄은 그대로) — 그쪽 리더가 이 키를
  건너뛰게 하는 것은 그 리포 몫이다(context-notes AP-18).
"""
from __future__ import annotations

import json
import logging
import re
import stat
from pathlib import Path

import httpx

from app.agent import docforge_delivery as _dfd
from app.agent import ra_post as _ra_post
from app.agent import risk_report as _risk_report

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]          # HWAXPortal — 토큰 파일 경로의 앵커
KINDS = ("per_analysis", "summary", "revdiff")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")            # ra_post 와 같은 형식 id 꼴
_BOARD_RE = re.compile(r"(?!\.{1,2}$)[A-Za-z0-9._-]{1,64}")           # ra_post 와 같은 공간 slug 꼴
TOKEN_MAX = 4096
TIMEOUT = httpx.Timeout(120.0, connect=10.0)
ATTEMPTS_MAX = 3                                     # 확실히 실패하지 않은 게시는 박자마다 이만큼까지 다시
_TRANSPORT: httpx.AsyncBaseTransport | None = None   # 시험 이음매 — None 이 아니면 RA 요청이 이 전송을 탄다


def _path() -> Path:
    return _ra_post.PATH            # 매번 읽는다 — 시험이 ra_post.PATH 를 바꿔 끼운다


def config() -> dict:
    """{configured, board, formats{kind: (id, 판)}, token_file(Path|None), error}. 토큰 값은 읽지 않는다(있는지 · 권한만)."""
    out: dict = {"configured": False, "board": None, "formats": {}, "token_file": None, "error": None}
    p = _path()
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return out
    except (OSError, ValueError) as exc:
        out["error"] = f"박스 파일을 못 읽음({type(exc).__name__})"
        return out
    row = doc.get("auto_pipeline") if isinstance(doc, dict) else None
    if row is None:
        return out
    if not isinstance(row, dict):
        out["error"] = "auto_pipeline 줄이 객체가 아니다"
        return out
    board, tf, fmts = row.get("board"), row.get("token_file"), row.get("formats")
    if not isinstance(board, str) or not _BOARD_RE.fullmatch(board):
        out["error"] = "auto_pipeline.board 꼴이 틀렸다(RA 시스템 공간 slug)"
        return out
    out["board"] = board
    if not isinstance(fmts, dict):
        out["error"] = "auto_pipeline.formats 가 객체가 아니다"
        return out
    for kind, f in fmts.items():
        tid = f.get("template_id") if isinstance(f, dict) else None
        ver = f.get("template_version") if isinstance(f, dict) else None
        if kind in KINDS and isinstance(tid, str) and _ID_RE.fullmatch(tid) and isinstance(ver, int) and not isinstance(ver, bool) and ver >= 1:
            out["formats"][kind] = (tid, ver)
    if not out["formats"]:
        out["error"] = f"auto_pipeline.formats 에 쓸 수 있는 형식이 없다({' · '.join(KINDS)})"
        return out
    if not isinstance(tf, str) or not tf.strip() or Path(tf).is_absolute():
        out["error"] = "auto_pipeline.token_file 은 리포 루트 기준 상대 경로다"
        return out
    path = ROOT / tf
    try:
        st = path.stat()
    except OSError:
        out["error"] = "시스템 계정 토큰 파일이 없다"
        return out
    if not stat.S_ISREG(st.st_mode):
        out["error"] = "시스템 계정 토큰 파일이 보통 파일이 아니다"
        return out
    if st.st_mode & 0o077:
        out["error"] = "시스템 계정 토큰 파일이 0600 이 아니다 — 그룹 · 남이 읽을 수 있어 쓰지 않는다(chmod 600)"
        return out
    out.update(configured=True, token_file=path)
    return out


def health() -> dict:
    c = config()
    return {"configured": c["configured"], "board": c["board"], "formats": sorted(c["formats"]), "error": c["error"]}


def _token(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    # 요청 머리에 실을 수 있는 글자만(ASCII · 보이는 글자 · 빈칸 없음) — 아니면 머리를 짓다가 박자째 터진다
    return raw if raw and len(raw) <= TOKEN_MAX and raw.isascii() and raw.isprintable() and " " not in raw else None


def _fail(r: httpx.Response, step: str) -> str:
    """RA 거절 → 원장에 적을 짧은 낱말 + 까닭(RA 의 글 — 토큰을 싣지 않는다)."""
    return f"{step}:HTTP {r.status_code} {_dfd._ra_error(r)}"[:400]


async def post(settings, cfg: dict, kind: str, rendered: dict, *, report_id: str | None = None) -> dict:
    """{ra_state, ra_report_id, ra_error}. ra_state — posted(게시됨) · drafted(초안만 — 게시를 다시) · pending(다시) · failed(그만) · none(이 종류의
    형식이 없다). report_id 를 주면 만들기를 건너뛰고 게시만 다시 한다."""
    fmt = cfg["formats"].get(kind)
    if fmt is None:
        return {"ra_state": "none", "ra_report_id": None, "ra_error": f"format_missing:{kind}"}
    token = _token(cfg["token_file"])
    if not token:
        return {"ra_state": "failed", "ra_report_id": report_id, "ra_error": "token_unreadable"}
    ra = _dfd.RaSession(settings.ra_base_url, token)
    async with httpx.AsyncClient(timeout=TIMEOUT, transport=_TRANSPORT) as cli:
        if report_id is None:
            draft = {"template_id": fmt[0], "template_version": fmt[1], "title": rendered["title"], "blocks": rendered["blocks"],
                     "tags": rendered["tags"]}
            try:
                r = await ra.call(cli, "POST", "/api/reports/ai-draft", json={**draft, "dry_run": True})
            except httpx.HTTPError as exc:
                return {"ra_state": "pending", "ra_report_id": None, "ra_error": f"ra_unreachable:{type(exc).__name__}"}
            if r.status_code >= 500:
                return {"ra_state": "pending", "ra_report_id": None, "ra_error": _fail(r, "preview")}
            if r.status_code >= 300:
                return {"ra_state": "failed", "ra_report_id": None, "ra_error": _fail(r, "preview")}
            data = _risk_report._data(r)
            if data.get("dry_run") is not True:
                return {"ra_state": "pending", "ra_report_id": None, "ra_error": "preview:미리보기 답을 읽지 못했다"}
            dropped = _risk_report._warnings(data)
            if dropped:
                return {"ra_state": "failed", "ra_report_id": None,
                        "ra_error": f"ra_template_mismatch:{fmt[0]}@{fmt[1]} — {dropped[0]}"[:400]}
            try:
                r = await ra.call(cli, "POST", "/api/reports/ai-draft", json=draft)
            except httpx.HTTPError as exc:
                return {"ra_state": "failed", "ra_report_id": None,
                        "ra_error": f"ra_outcome_unknown:{type(exc).__name__} — 초안이 생겼는지 모른다. 시스템 계정의 RA 개인 공간을 확인한다"}
            if 400 <= r.status_code < 500:
                return {"ra_state": "failed", "ra_report_id": None, "ra_error": _fail(r, "create")}
            rid = _risk_report._data(r).get("report_id")
            if r.status_code >= 300 or not isinstance(rid, int) or isinstance(rid, bool) or rid < 1:
                return {"ra_state": "failed", "ra_report_id": None,
                        "ra_error": f"ra_outcome_unknown:HTTP {r.status_code} — 초안이 생겼는지 모른다"}
            report_id = str(rid)
        try:
            r = await ra.call(cli, "POST", "/api/mounts", json={"report_id": int(report_id), "workspace_slugs": [cfg["board"]],
                                                                "note": "HWAX 자동 파이프라인"})
        except httpx.HTTPError as exc:
            return {"ra_state": "drafted", "ra_report_id": report_id, "ra_error": f"mount:ra_unreachable:{type(exc).__name__}"}
        if r.status_code != 200:
            state = "failed" if r.status_code in (400, 404, 422) else "drafted"
            return {"ra_state": state, "ra_report_id": report_id, "ra_error": _fail(r, "mount")}
    return {"ra_state": "posted", "ra_report_id": report_id, "ra_error": None}
