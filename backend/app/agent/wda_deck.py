# 발표자료로 — 포털이 만든 RA 보고서를 그 사람 명의로 읽어 WebDesignAgents 에 넘기고 진행 · 알림 · 내려받기를 중계한다(docs/wda-deck)
"""흐름(docs/wda-deck/PLAN.md §3 — 사용자 결정 11-01 '포털이 맡고 알린다')

1. 만들기 — RA 를 그 사람 토큰으로 읽는다(`routes._ra_user_token` — 위임 먼저 · 등록 토큰 다음, 서비스 계정 없음). 허브 Caddy 를 거쳐 WDA
   `POST /api/runs` 를 그 사람 이름의 짧은 포털 PAT(청중 heax-hub)로 부른다. 허브 게이트가 PAT 를 검증하고 Caddy 가 `X-Heax-User-Email` 을 그 사람으로
   싣는다 — WDA 는 그 값을 run 의 주인으로 쓴다(요청 W-1). 포털은 그 머리를 싣지 않는다(Caddy 가 지우고 다시 싣는 머리다).
2. 진행 — 화면이 묻는다. WDA 의 낱말 둘(파이프라인 · 렌더)을 하나로 접는다(`fold`, PLAN §7.2). 부작용이 없다.
3. advance(POST · CSRF) — 잡 잠금 안에서 렌더 맡기기(WDA 가 이어서 렌더하지 않는 판) · 끝나면 알림 한 건(단추를 누른 그 대화의 서버 사본, 한 번만).
4. 받기 — 기록의 주인만. **요청한 사람의** 이름으로 WDA 에서 받아 흘린다(WDA 가 주인을 다시 본다 — 두 겹).

브라우저는 WDA 의 run_id · 주소 · 서버 경로를 보지 않는다(WD-D7). 기록 · 로그 · 감사에는 보고서 본문을 남기지 않는다(번호 · 제목 · 수만).
켜기 — 박스 스위치 wda_deck_enabled(기본 꺼짐) 와 WDA /api/health 의 features 에 owner(WD-D23 · D24). 심의(deliberation 템플릿) 보고서는
WDA 의 심의 꼴 delib-16x9 가 준비됐을 때만(format_ready — features 의 format:delib-16x9 와 그 꼴의 상태) 그 꼴을 실어 넘긴다(WD-D29 · D39 — 기본
꼴로 넣으면 결정문 · 액션아이템이 빠진 발표자료가 나간다).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import sqlite3
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, NamedTuple
from urllib.parse import quote

import anyio
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StrictBool, StrictInt

from app.access.policy import login_groups
from app.auth import ra_sso
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import ensure, principal_pat_or_session

logger = logging.getLogger("hwax.wda_deck")

# 스테이징 루트 아래 — 사용자 폴더 이름(영숫자 · -_@.)과 겹치지 않는다. 스테이징 청소(6시간)에서 빠지고 wda_deck_job_days 뒤 지운다(upload.sweep_expired)
JOBS_DIR = "#deck-jobs"
_JOB_RE = re.compile(r"^[a-f0-9]{32}$")
_RUN_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
NEEDS = ("plat:webdesign", "plat:reportarchive")
TARGETS = ("pptx", "pdf", "docx", "html", "video")
DEFAULT_TARGETS = ("pptx", "pdf")              # 사용자 결정 11-01 — PPT + PDF(hybrid)
DOC_STYLES = ("report", "brief", "memo")       # 사용자 결정 11-01 U-4 — 기본 report(정식 보고서 문서)
DOC_TARGETS = ("pdf", "docx", "html")
PPTX_MODE = "hybrid"
TERMINAL = ("done", "failed")
# 화면의 출력 이름 → WDA 내려받기 kind(웹 경로는 영상을 mp4 로 부른다 — WDA app.py _DOWNLOAD_META)
WDA_KIND = {"pptx": "pptx", "pdf": "pdf", "docx": "docx", "html": "html", "video": "mp4"}
_FILE = {"pptx": (".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
         "pdf": (".pdf", "application/pdf"),
         "docx": (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
         "html": (".html", "text/html; charset=utf-8"),
         "video": (".mp4", "video/mp4")}
LABEL = {"pptx": "PPT", "pdf": "PDF", "docx": "Word", "html": "HTML", "video": "영상"}
DOC_LABEL = {"report": "정식 보고서 문서", "brief": "요약 문서(2~3쪽)", "memo": "1쪽 메모"}
# RA 템플릿 → WDA 꼴 id(요청 W-21). 이 템플릿의 보고서는 그 꼴이 준비됐을 때만(format_ready) 그 꼴을 실어 넘긴다 — 심의 보고서를 기본 꼴(wide-16x9)로
# 넣으면 결정문 · 액션아이템이 사라진다(WDA 11-01 답). 그 밖의 템플릿은 format 칸을 싣지 않는다(WDA 기본 wide-16x9).
TEMPLATE_FORMAT = {"deliberation": "delib-16x9"}
STEPS = {"ingest": "보고서 읽기", "fragmentize": "조각 나누기", "scenario": "장면 구성", "build": "화면 굽기"}
_PROGRESS = {"ingest": 10, "fragmentize": 25, "scenario": 40, "build": 55}
CAPS_TTL_S = 60.0

_LOCKS: dict[str, asyncio.Lock] = {}
_CAPS: dict[str, Any] = {"at": 0.0, "features": None, "formats": {}, "version": None}

router = APIRouter(prefix="/agent/deck", tags=["agent-deck"])


def lock(key: str) -> asyncio.Lock:
    return _LOCKS.setdefault(key, asyncio.Lock())


def _knob(settings: Settings = Depends(get_settings)) -> None:
    """박스 스위치가 꺼져 있으면 없는 창구와 같은 404 다(패널 손잡이와 같은 자세). status 는 이 문 밖이다 — 화면이 숨길 까닭을 알아야 한다."""
    if not settings.wda_deck_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


class DeckError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message, self.status = message, status


def _http_error(exc: DeckError) -> AuthError:
    return AuthError(exc.message, status_code=exc.status)


# ── 잡 기록 ──────────────────────────────────────────────────────────────────────────────────────────────
def _dir(settings: Settings) -> Path:
    d = Path(settings.upload_staging_dir) / JOBS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(settings: Settings, job_id: str) -> Path:
    if not isinstance(job_id, str) or not _JOB_RE.fullmatch(job_id):
        raise DeckError("그 발표자료 잡이 없습니다.", 404)
    return _dir(settings) / f"{job_id}.json"


def save(settings: Settings, rec: dict) -> None:
    rec["updated_at"] = time.time()
    p = _path(settings, rec["job_id"])
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def load(settings: Settings, job_id: str, owner_sub: str) -> dict:
    """맡긴 사람의 기록만 — 남의 것 · 없는 것은 똑같이 404(있는지도 알리지 않는다)."""
    p = _path(settings, job_id)
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rec = None
    if not isinstance(rec, dict) or rec.get("owner_sub") != owner_sub:
        raise DeckError("그 발표자료 잡이 없습니다.", 404)
    return rec


def records(settings: Settings) -> list[dict]:
    """모든 잡 기록(박스 상한 셈 · 내 목록). 깨진 기록은 건너뛴다."""
    out = []
    for p in _dir(settings).glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and _JOB_RE.fullmatch(str(rec.get("job_id") or "")):
            out.append(rec)
    out.sort(key=lambda r: r.get("created_at") or 0, reverse=True)
    return out


def inflight(rec: dict, settings: Settings, now: float) -> bool:
    """아직 도는 잡인가 — 끝을 적지 않았고 give_up 을 넘기지 않은 것(끊긴 채 남은 옛 기록이 상한을 영영 먹지 않게)."""
    return not rec.get("finished") and now - float(rec.get("created_at") or 0) < settings.wda_deck_give_up_s


# ── 자격 · 주소 ─────────────────────────────────────────────────────────────────────────────────────────
def hub_pat(keystore, settings: Settings, principal: Principal) -> str:
    """허브 게이트(HEAXHub authz — 포털 PAT 를 그 이메일의 허브 사용자로 잇는다)를 지나는 그 사람 이름의 짧은 PAT. 청중은 허브 하나 · 저장하지 않는다.
    로그인 그룹만 싣는다(권한 키 · 관리자 표지는 허브가 보지 않는다 — 허브 앱의 사람별 권한은 can_view_app, followups-1017 결정 ⑦)."""
    now = datetime.now(tz=UTC)
    claims = {"iss": settings.jwt_issuer, "sub": principal.subject, "email": principal.email, "name": principal.display_name,
              "groups": login_groups(principal.groups), "aud": [settings.wda_hub_audience], "scope": "api", "scopes": ["deck"],
              "pat_name": "deck-wda", "iat": now, "nbf": now, "exp": now + timedelta(seconds=settings.wda_hub_pat_ttl_s),
              "jti": f"deck-{uuid.uuid4().hex}"}
    return jwt.encode(claims, keystore.private_pem, algorithm="RS256", headers={"kid": keystore.active_kid})


def wda_base(settings: Settings, catalog) -> str:
    """WDA 의 허브 Caddy 경로 — 설정이 이기고, 없으면 routes.env 의 apps(허브 Caddy 의 /apps/) + web_design_agents."""
    if settings.wda_base_url.strip():
        return settings.wda_base_url.strip().rstrip("/")
    apps = catalog.route("apps") if catalog is not None else None
    return f"{apps.rstrip('/')}/web_design_agents" if apps else ""


def _http(timeout: float | httpx.Timeout) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout)


def _json(r: httpx.Response) -> dict:
    try:
        j = r.json()
    except ValueError:
        return {}
    return j if isinstance(j, dict) else {}


def _why(r: httpx.Response) -> str:
    """상대가 밝힌 까닭 — WDA 봉투의 message, 허브 게이트의 detail, 아니면 본문 앞. **서버 로그에만** 쓴다(WD-D49)."""
    j = _json(r)
    msg = j.get("message") or j.get("detail") or (r.text or "")
    return (msg if isinstance(msg, str) else json.dumps(msg, ensure_ascii=False))[:300]


# 마크다운이 되는 글자 → 같은 모양의 전각 글자. 포털 챗 글(md.ts)에는 역슬래시 이스케이프가 없고 `\(..\)` 는 수식이라 \ 를 붙이면 오히려
# 수식 · 글자 그대로의 \ 가 된다 — 바꿔 끼운다(WD-D49). 줄바꿈 · 제어 · 방향 바꾸기 글자는 빈칸으로(제목 · 인용 · 표 · 코드 울타리가 서지 않게).
_MD_PLAIN = str.maketrans({"[": "［", "]": "］", "(": "（", ")": "）", "!": "！", "*": "＊", "_": "＿", "\\": "＼", "`": "｀",
                           "#": "＃", ">": "＞", "|": "｜", "$": "＄", "~": "～", "<": "＜"})
_UNSEEN = re.compile(r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")


def md_plain(v: Any, limit: int = 300) -> str:
    """사람 · WDA 가 쓴 글을 알림(마크다운) · LLM 근거에 넣기 전에 — 링크 · 그림 · 제목 · 콜아웃 · 코드가 되지 않는 한 줄로."""
    s = re.sub(r"\s+", " ", _UNSEEN.sub(" ", str(v or ""))).strip()
    return s.translate(_MD_PLAIN)[:limit]


def _wda_error(r: httpx.Response, what: str) -> DeckError:
    """허브 · WDA 의 거절 → 사람에게 보일 정해진 글(코드 · 상태로 고른다). 상대의 글(WDA 예외 글 — 경로 · run_id 가 실린다)은 서버 로그에만(WD-D49)."""
    j = _json(r)
    code = j.get("code") if isinstance(j.get("code"), str) else ""
    st = r.status_code
    logger.warning("발표자료 — %s 요청이 거절됐다 HTTP %s code=%s 까닭=%r", what, st, code or "-", _why(r))
    if st == 401 and not code:
        return DeckError("허브가 포털 토큰을 받지 않았습니다 — 다시 로그인한 뒤 누르세요.", 403)
    if st == 403 and not code:
        return DeckError("허브가 막았습니다 — 허브 계정이 없거나(포털에서 HEAX Hub 타일을 한 번 눌러 허브에 로그인한 뒤 다시) 이 앱을 볼 권한이 "
                         "없습니다.", 403)
    if st == 413 or code == "TOO_LARGE":
        return DeckError("보고서가 커서 WDA 가 받지 않았습니다.", 413)
    if st in (404, 410) or code == "NOT_FOUND":
        return DeckError("WDA 가 그 실행을 모릅니다(지웠거나 다른 박스).", 404)
    if st == 409 or code in ("BUSY", "NOT_BUILT"):
        return DeckError("WDA 가 지금 그 요청을 받을 수 없습니다(이미 하는 중이거나 아직 준비 전) — 잠시 뒤 다시.", 409)
    if st == 422 or (code == "INVALID" and st != 400):
        return DeckError("WDA 가 이 보고서를 다루지 못했습니다 — 글이 있는 블록이 없거나 꼴이 맞지 않습니다.", 422)
    if st == 400 or code == "INVALID":
        return DeckError(f"WDA 가 {what} 요청의 꼴을 받지 않았습니다 — WDA 판이 바뀌었을 수 있습니다.", 502)
    if st == 429 or st >= 500 or code == "INTERNAL":
        return DeckError(f"허브 또는 WDA 가 지금 {what} 요청에 답하지 못합니다(HTTP {st}) — 잠시 뒤 다시 누르세요.", 503 if st != 429 else 429)
    return DeckError(f"WDA 가 {what} 요청을 받지 않았습니다(HTTP {st}).", 502)


class Caps(NamedTuple):
    """WDA /api/health — features(요청 W-6 · 꼴마다 format:<id>)와 꼴마다의 상태(formats — draft · active …, WDA 의 꼴 등록부에서 나온다).
    version 은 WDA 패키지 판(허브 매니페스트 판과 같다) — 잡 기록에 진단용으로만 남기고 막는 데 쓰지 않는다(WD-D43)."""
    features: frozenset[str]
    formats: dict[str, str]
    version: str | None = None


def format_ready(caps: Caps, fmt: str) -> bool:
    """그 꼴로 넘겨도 되는가 — 정책은 이 함수 하나다(status 의 formats 와 만들기의 문이 함께 쓴다). WDA 가 `format:<id>` 를 알리고 그 꼴의 상태가
    active 여야 한다 — draft · 없음은 숨긴다. 사용자 결정(11-01, WD-D42) — active 일 때만 열고 draft 를 여는 손잡이는 두지 않는다."""
    return f"format:{fmt}" in caps.features and caps.formats.get(fmt) == "active"


async def capabilities(base: str, token: str) -> Caps | None:
    """WDA /api/health 의 features · formats(요청 W-6 · W-21). 못 읽으면 None(모른다 — 화면은 숨긴다). 읽은 값만 60초 붙잡는다 — 한 사람의
    실패(허브 계정 없음)가 모두의 단추를 숨기지 않게."""
    now = time.monotonic()
    if _CAPS["features"] is not None and now - _CAPS["at"] < CAPS_TTL_S:
        return Caps(_CAPS["features"], _CAPS["formats"], _CAPS["version"])
    try:
        async with _http(10.0) as cli:
            r = await cli.get(f"{base}/api/health", headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    j = _json(r)
    feats, fmts, ver = j.get("features"), j.get("formats"), j.get("version")
    got = Caps(frozenset(str(f) for f in feats if isinstance(f, str)) if isinstance(feats, list) else frozenset(),
               {k: v for k, v in fmts.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(fmts, dict) else {},
               ver[:40] if isinstance(ver, str) and ver else None)
    _CAPS.update(at=now, features=got.features, formats=got.formats, version=got.version)
    return got


# ── RA 읽기 ───────────────────────────────────────────────────────────────────────────────────────────
def templates_of(data: dict) -> set[str]:
    """RA ReportRead 의 템플릿 — 최상위(첫 쪽)와 쪽마다."""
    out = {str(data.get("template_id"))} if data.get("template_id") else set()
    for p in data.get("pages") or []:
        if isinstance(p, dict) and p.get("template_id"):
            out.add(str(p["template_id"]))
    return out


def file_refs(v: Any) -> set[str]:
    """보고서 안 그림 · 첨부의 file_id — M1 은 넘기지 않으므로 알림에 그 수를 말한다(WD-D15)."""
    if isinstance(v, dict):
        own = {str(v["file_id"])} if isinstance(v.get("file_id"), (str, int)) and not isinstance(v.get("file_id"), bool) else set()
        return own.union(*(file_refs(x) for x in v.values())) if v else own
    if isinstance(v, list):
        return set().union(*(file_refs(x) for x in v)) if v else set()
    return set()


async def read_report(request: Request, settings: Settings, principal: Principal, report_id: int) -> tuple[dict, int]:
    """그 사람 명의로 RA `GET /api/reports/{id}` → (ReportRead, 바이트 수). 서비스 계정으로 내려가는 길은 없다(2026-09-29 사고의 교훈)."""
    # 지연 import — RA 자격은 챗 업로드 · 정밀 변환과 같은 함수 하나로 받는다(위임 먼저 · 등록 토큰 다음 · 둘 다 없으면 고칠 곳을 말한다)
    from app.agent.routes import _ra_user_token

    token, via_sso, conn = await _ra_user_token(request, settings, principal)
    email = principal.email or principal.subject
    url = f"{settings.ra_base_url.rstrip('/')}/api/reports/{report_id}"

    def hdrs(tok: str) -> dict:
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
        if conn.get("workspace"):
            h["X-Workspace-Slug"] = conn["workspace"]
        return h

    try:
        async with _http(httpx.Timeout(60.0, connect=10.0)) as cli:
            r = await cli.get(url, headers=hdrs(token))
            if r.status_code == 401 and via_sso:
                # 캐시해 둔 위임 토큰을 RA 가 거절했다(회수 · 비밀 교체) — 한 번만 새로 받는다(RA 가지와 같은 규칙)
                ra_sso.forget(email)
                fresh = await ra_sso.ra_user_token(settings, email=email, name=principal.display_name or "")
                if fresh:
                    r = await cli.get(url, headers=hdrs(fresh))
    except httpx.HTTPError as exc:
        raise DeckError(f"Report Archive 에 연결하지 못했습니다({exc.__class__.__name__}).", 502) from exc
    if r.status_code in (401, 403):
        raise DeckError(f"이 보고서를 읽을 수 없습니다(HTTP {r.status_code}) — RA 권한과 '외부 연결'(RA 토큰)을 확인하세요.", 403)
    if r.status_code == 404:
        raise DeckError("그 보고서가 Report Archive 에 없습니다.", 404)
    if r.status_code >= 400:
        logger.warning("발표자료 — RA 가 보고서 %s 를 주지 않았다 HTTP %s 까닭=%r", report_id, r.status_code, _why(r))
        raise DeckError(f"Report Archive 가 보고서를 주지 않았습니다(HTTP {r.status_code}) — 잠시 뒤 다시 누르세요.", 502)
    size = len(r.content)
    if size > settings.wda_deck_report_max_mb * 1024 * 1024:
        raise DeckError(f"보고서가 커서({size / 1048576:.1f} MB) 발표자료로 만들 수 없습니다 — 상한 {settings.wda_deck_report_max_mb} MB.", 413)
    data = _json(r).get("data")
    if not isinstance(data, dict):
        raise DeckError("Report Archive 응답에 보고서가 없습니다.", 502)
    return data, size


# ── WDA 부르기 ────────────────────────────────────────────────────────────────────────────────────────
def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def wda_create(base: str, token: str, *, data: dict, report_id: int, targets: list[str], doc_style: str, job_id: str,
                     fmt: str | None) -> str:
    """WDA `POST /api/runs` — 본문은 RA ReportRead 를 **바꾸지 않고**(WD-D31). render 칸이 있으면 WDA 가 빌드 뒤 이어서 렌더한다(요청 W-8).
    `format` 은 꼴이 정해진 템플릿(심의 → delib-16x9)일 때만 싣는다 — 없으면 WDA 기본(wide-16x9). WDA 가 모르는 꼴이면 곧바로 400 이다(실행 없음)."""
    body = {"report_json": data, "slug": f"ra-{report_id}",
            "source": {"system": "report-archive", "report_id": report_id, "client": "hwax-portal"},
            "render": {"targets": list(targets), "doc_style": doc_style, "pptx_mode": PPTX_MODE, "narration": False}}
    if fmt:
        body["format"] = fmt
    try:
        async with _http(httpx.Timeout(60.0, connect=10.0)) as cli:
            r = await cli.post(f"{base}/api/runs", json=body, headers={**_auth(token), "Idempotency-Key": job_id})
    except httpx.HTTPError as exc:
        raise DeckError(f"WDA 에 연결하지 못했습니다({exc.__class__.__name__}).", 502) from exc
    if r.status_code >= 400:
        raise _wda_error(r, "만들기")
    rid = (_json(r).get("data") or {}).get("run_id") if isinstance(_json(r).get("data"), dict) else None
    if not isinstance(rid, str) or not _RUN_RE.fullmatch(rid):
        raise DeckError("WDA 가 실행 번호를 주지 않았습니다 — 만들어졌는지 알 수 없습니다.", 502)
    return rid


async def wda_run(base: str, token: str, run_id: str) -> dict | None:
    """WDA `GET /api/runs/{id}` — 404 · 410 은 None(모른다 — 지웠거나 다른 박스). 그 밖의 실패는 DeckError(화면이 다시 묻는다)."""
    try:
        async with _http(httpx.Timeout(15.0, connect=5.0)) as cli:
            r = await cli.get(f"{base}/api/runs/{quote(run_id, safe='')}", headers=_auth(token))
    except httpx.HTTPError as exc:
        raise DeckError(f"WDA 에 연결하지 못했습니다({exc.__class__.__name__}).", 502) from exc
    if r.status_code in (404, 410):
        return None
    if r.status_code >= 400:
        raise _wda_error(r, "진행 조회")
    run = _json(r).get("data")
    if not isinstance(run, dict):
        raise DeckError("WDA 가 진행을 알려 주지 않았습니다.", 502)
    return run


async def wda_render(base: str, token: str, run_id: str, rec: dict) -> None:
    """렌더 맡기기 — WDA 가 이어서 렌더하지 않는 판의 대체 길(요청 4.3). 409 BUSY 는 '이미 맡겼다' 로 읽는다."""
    opts = rec["options"]
    body = {"targets": list(opts["targets"]), "doc_style": opts["doc_style"], "pptx_mode": PPTX_MODE, "narration": False}
    try:
        async with _http(httpx.Timeout(30.0, connect=5.0)) as cli:
            r = await cli.post(f"{base}/api/runs/{quote(run_id, safe='')}/render", json=body, headers=_auth(token))
    except httpx.HTTPError as exc:
        raise DeckError(f"WDA 에 연결하지 못했습니다({exc.__class__.__name__}).", 502) from exc
    if r.status_code == 409:
        # 이미 렌더 중(BUSY) — 지금 WDA 는 code 를 싣지 않는다(W-10 전). NOT_BUILT 는 생기지 않는다(빌드가 끝난 실행에만 맡긴다)
        return
    if r.status_code >= 400:
        raise _wda_error(r, "렌더")


async def wda_artifacts(base: str, token: str, run_id: str) -> dict[str, int | None]:
    """WDA 산출물 크기 — {WDA kind: 바이트 | None(없음)}."""
    try:
        async with _http(httpx.Timeout(15.0, connect=5.0)) as cli:
            r = await cli.get(f"{base}/api/runs/{quote(run_id, safe='')}/artifacts", headers=_auth(token))
    except httpx.HTTPError as exc:
        raise DeckError(f"WDA 에 연결하지 못했습니다({exc.__class__.__name__}).", 502) from exc
    if r.status_code >= 400:
        raise _wda_error(r, "산출물 조회")
    arts = _json(r).get("data")
    out: dict[str, int | None] = {}
    for kind, v in (arts.items() if isinstance(arts, dict) else []):
        ok = isinstance(v, dict) and v.get("exists") is True
        size = v.get("size") if ok and isinstance(v.get("size"), int) and not isinstance(v.get("size"), bool) else None
        out[str(kind)] = size if ok else None
    return out


# ── 상태 접기(PLAN §7.2) ────────────────────────────────────────────────────────────────────────────
def fold(run: dict | None, *, rec: dict, now: float, settings: Settings) -> dict:
    """WDA 실행 원장(또는 None — WDA 가 모른다) → 화면 낱말 하나(queued · preparing · rendering · done · failed).
    돌려주는 것 — state · step · progress(단계 기준) · error · late · next(render | finish | None) · skipped. error 는 포털의 정해진 글이고 WDA 의
    예외 글(경로 · run_id 가 실린다)은 raw_error 로만 둔다 — 화면 · 알림에는 싣지 않고 끝을 적을 때 서버 로그에 남긴다(WD-D49)."""
    out: dict[str, Any] = {"state": "preparing", "step": "", "progress": 0, "error": None, "late": False, "next": None, "skipped": [],
                           "raw_error": None}
    if run is None:
        out.update(state="failed", step="WDA 가 이 실행을 모릅니다(지웠거나 다른 박스)", error="WDA 가 이 실행을 모릅니다(지웠거나 다른 박스).")
    else:
        st = run.get("status")
        stages = [s for s in (run.get("stages") or []) if isinstance(s, dict)]
        render = run.get("render") if isinstance(run.get("render"), dict) else None
        if st == "failed":
            bad = next((s for s in stages if s.get("status") == "failed"), {})
            name = STEPS.get(str(bad.get("stage")), "보고서 다루기")
            out.update(state="failed", step=f"{name} 에서 멈춤", error=f"WDA 가 '{name}' 단계에서 실패했습니다.",
                       raw_error=str(bad.get("error") or run.get("error") or "")[:500] or None)
        elif st == "queued":
            out.update(state="queued", step="줄 서는 중", progress=0)
        elif st == "running" or st not in ("done",):
            cur = next((s for s in stages if s.get("status") == "running"), None) or next((s for s in stages if s.get("status") == "pending"), {})
            key = str(cur.get("stage") or "")
            out.update(state="preparing", step=STEPS.get(key, "보고서 다루는 중"), progress=_PROGRESS.get(key, 5))
        elif render is None:
            if rec.get("render_submitted_at"):
                out.update(state="rendering", step="렌더 맡김", progress=62)
            else:
                out.update(state="preparing", step="렌더 맡기기", progress=60, next="render")
        else:
            rs = render.get("status")
            skipped = [{"target": md_plain(x.get("target"), 20), "reason": md_plain(x.get("reason"), 120)}
                       for x in (render.get("skipped") or []) if isinstance(x, dict) and x.get("target")]
            if rs == "done":
                out.update(state="done", step="끝", progress=100, skipped=skipped)
            elif rs == "failed":
                out.update(state="failed", step="파일 만들기에서 멈춤", error="WDA 가 파일을 만들다 실패했습니다.",
                           raw_error=str(render.get("error") or "")[:500] or None)
            elif rs == "queued":
                out.update(state="rendering", step="차례 기다림", progress=65)
            elif rs == "building":
                out.update(state="rendering", step="준비", progress=70)
            else:
                out.update(state="rendering", step="만드는 중", progress=80)
    elapsed = now - float(rec.get("created_at") or now)
    if out["state"] not in TERMINAL:
        if elapsed > settings.wda_deck_give_up_s:
            hours = settings.wda_deck_give_up_s / 3600
            out.update(state="failed", step="시간 초과", next=None,
                       error=f"{hours:g}시간이 지나도 끝나지 않았습니다 — WDA 가 재기동에 끊긴 실행일 수 있습니다.")
        else:
            video = "video" in rec["options"]["targets"]
            limit = (settings.wda_deck_late_prepare_s if out["state"] in ("queued", "preparing")
                     else settings.wda_deck_late_video_s if video else settings.wda_deck_late_render_s)
            out["late"] = elapsed > limit
    if out["state"] in TERMINAL and not rec.get("finished"):
        out["next"] = "finish"
    return out


def view(rec: dict, f: dict | None = None, now: float | None = None) -> dict:
    """화면에 주는 잡 — 포털 잡 id · 보고서 · 옵션 · 상태. WDA 의 run_id · 주소는 싣지 않는다."""
    now = time.time() if now is None else now
    base = {"job_id": rec["job_id"], "report": rec["report"], "options": rec["options"], "conversation_id": rec.get("conversation_id"),
            "created_at": rec.get("created_at"), "elapsed_s": round(now - float(rec.get("created_at") or now))}
    fin = rec.get("finished")
    if fin:
        return {**base, "state": fin["state"], "step": fin.get("step") or "", "progress": 100 if fin["state"] == "done" else None,
                "error": fin.get("error"), "late": False, "next": None, "skipped": fin.get("skipped") or [],
                "files": [{**x, "label": LABEL.get(x["kind"], x["kind"]), "url": file_url(rec["job_id"], x["kind"])}
                          for x in fin.get("files") or []]}
    f = f or {"state": rec.get("state") or "queued", "step": "", "progress": 0, "error": None, "late": False, "next": None, "skipped": []}
    return {**base, **{k: f[k] for k in ("state", "step", "progress", "error", "late", "next", "skipped")}, "files": []}


def file_url(job_id: str, kind: str) -> str:
    return f"/agent/deck/jobs/{job_id}/files/{kind}"


# ── 알림(PP-D3 꼴 — 어시스턴트 글 + 활동 하나 origin upload) ─────────────────────────────────────────────────
def notice(rec: dict, *, state: str, files: list[dict], skipped: list[dict], error: str | None, step: str,
           keep_days: int, now_ms: int | None = None) -> dict:
    """끝난 잡 → 대화 알림 한 건. 글에 포털 링크(받기)를 박고, 활동 근거에는 번호 · 제목 · 수만(본문 · WDA 번호 없음).
    사람(RA 제목) · WDA(뺀 출력의 까닭)가 쓴 글은 md_plain 으로 — 알림은 마크다운으로 그려지고 다음 턴의 LLM 근거가 된다(WD-D49). error · step 은
    포털의 정해진 글뿐이다(fold · advance)."""
    rep = rec["report"]
    opts = rec["options"]
    title = md_plain(rep.get("title"), 120)
    skipped = [{"target": md_plain(x.get("target"), 20), "reason": md_plain(x.get("reason"), 120)} for x in skipped]
    head = f"보고서 {rep['id']}" + (f"「{title}」" if title else "")
    if state == "done":
        names = []
        for x in files:
            k = x["kind"]
            names.append("PPT(글자를 고칠 수 있는 꼴)" if k == "pptx" else
                         f"{LABEL[k]}({DOC_LABEL[opts['doc_style']]})" if k in DOC_TARGETS else LABEL.get(k, k))
        links = " · ".join(f"[{LABEL.get(x['kind'], x['kind'])} 받기]({file_url(rec['job_id'], x['kind'])})" for x in files)
        text = (f"{head}로 발표자료를 만들었습니다 — {' · '.join(names)}. 받기 — {links}. "
                f"파일은 맡긴 사람만 받을 수 있고 {keep_days}일 뒤에는 받지 못할 수 있습니다.")
        if skipped:
            text += " 만들지 않은 것 — " + " · ".join(
                LABEL.get(s["target"], s["target"]) + (f"({s['reason']})" if s.get("reason") else "") for s in skipped) + "."
        if rec.get("images_not_sent"):
            text += f" 보고서의 그림 · 첨부 {rec['images_not_sent']}개는 이번에 싣지 않았습니다."
    else:
        text = (f"{head}로 발표자료를 만들지 못했습니다 — {step or '실패'}" + (f"({error})" if error else "")
                + ". 다시 만들려면 그 보고서의 '발표자료로' 를 다시 누르세요.")
    facts = {"report_id": rep["id"], "title": md_plain(rep.get("title"), 300) or None, "state": state, "targets": opts["targets"],
             "doc_style": opts["doc_style"], "files": [{"kind": x["kind"], "bytes": x.get("bytes")} for x in files],
             "skipped": skipped, "images_not_sent": rec.get("images_not_sent") or 0, "error": error}
    full = json.dumps(facts, ensure_ascii=False)
    act = {"ts": int(time.time() * 1000) if now_ms is None else now_ms, "step": "발표자료 만들기(사람이 맡김)", "tool": "web_design_agents",
           "detail": json.dumps({"report_id": rep["id"], "targets": opts["targets"], "doc_style": opts["doc_style"]}, ensure_ascii=False),
           "result_full": full, "result_preview": full[:220], "ok": state == "done", "origin": "upload"}
    return {"text": text, "activity": [act],
            "deck": {"job_id": rec["job_id"], "state": state, "report_id": rep["id"], "files": [x["kind"] for x in files]}}


# ── 감사 ─────────────────────────────────────────────────────────────────────────────────────────────
def _audit(request: Request, principal: Principal, event: str, status: str, **meta) -> None:
    try:
        request.app.state.agent_audit.record(principal=principal.subject, event=event, status=status, meta=meta)
    except Exception:  # noqa: BLE001 — 감사 실패가 잡을 막지 않는다
        logger.warning("발표자료 감사 기록 실패(%s)", event, exc_info=True)


# ── 라우트 ────────────────────────────────────────────────────────────────────────────────────────────
class DeckJobIn(BaseModel):
    model_config = {"extra": "forbid"}
    report_id: StrictInt = Field(gt=0)
    conversation_id: str = Field(min_length=1, max_length=200)     # 서버 대화 id — 끝나면 알림을 여기에 남긴다
    targets: list[Literal["pptx", "pdf", "docx", "html", "video"]] = Field(
        default_factory=lambda: list(DEFAULT_TARGETS), min_length=1, max_length=len(TARGETS))
    doc_style: Literal["report", "brief", "memo"] = "report"
    again: StrictBool = False                                     # 끝난 같은 잡이 있어도 새로 만든다


def _base_and_token(request: Request, settings: Settings, principal: Principal) -> tuple[str, str]:
    base = wda_base(settings, getattr(request.app.state, "catalog", None))
    if not base:
        raise AuthError("WDA 주소를 모릅니다 — 박스 설정 wda_base_url 또는 routes.env 의 apps 를 확인하세요.", status_code=409)
    return base, hub_pat(request.app.state.keystore, settings, principal)


@router.get("/status")
async def deck_status(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """화면이 단추를 보일지 — 스위치 · 권한 둘 · WDA 주소 · WDA 능력(owner). formats 는 템플릿 문 — RA 템플릿마다 그 꼴이 준비됐나(format_ready)."""
    out: dict[str, Any] = {"enabled": False, "reason": None, "formats": {t: False for t in TEMPLATE_FORMAT},
                           "targets": list(TARGETS), "doc_styles": list(DOC_STYLES),
                           "defaults": {"targets": list(DEFAULT_TARGETS), "doc_style": "report"}, "keep_days": settings.wda_deck_job_days}
    if not settings.wda_deck_enabled:
        out["reason"] = "off"
        return out
    if not all(k in (principal.groups or []) for k in NEEDS):
        out["reason"] = "permission"
        return out
    base = wda_base(settings, getattr(request.app.state, "catalog", None))
    if not base:
        out["reason"] = "no_base"
        return out
    caps = await capabilities(base, hub_pat(request.app.state.keystore, settings, principal))
    if caps is None:
        out["reason"] = "unknown"
    elif "owner" not in caps.features:
        out["reason"] = "no_owner"
    else:
        out.update(enabled=True, formats={t: format_ready(caps, f) for t, f in TEMPLATE_FORMAT.items()})
    return out


@router.post("/jobs", dependencies=[Depends(_knob)])
async def deck_create(
    request: Request,
    body: DeckJobIn,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """그 사람 명의로 RA 보고서를 읽어 WDA 에 맡긴다. 같은 보고서 · 같은 옵션의 잡이 돌면(또는 끝났고 again 이 아니면) 그 잡을 준다."""
    ensure(principal, *NEEDS)
    targets = [t for t in TARGETS if t in body.targets]
    owner = principal.subject
    store = request.app.state.conv_store
    try:
        whose = await asyncio.to_thread(store.owner_state, body.conversation_id, owner)
    except sqlite3.OperationalError as exc:
        raise AuthError("대화 저장소가 바쁩니다 — 잠시 뒤 다시 누르세요.", status_code=503) from exc
    if whose != "mine":
        raise AuthError("그 대화가 없습니다.", status_code=404)
    base, token = _base_and_token(request, settings, principal)
    caps = await capabilities(base, token)
    if caps is None:
        raise AuthError("WDA 상태를 읽지 못했습니다 — 잠시 뒤 다시 누르세요.", status_code=503)
    if "owner" not in caps.features:
        raise AuthError("WDA 에 아직 주인 기능이 없습니다 — 보고서를 넘기지 않습니다(사용자 결정 11-01).", status_code=409)
    async with lock("create"):
        now = time.time()
        recs = await asyncio.to_thread(records, settings)
        for r in recs:
            if (r.get("owner_sub") == owner and r["report"]["id"] == body.report_id
                    and r["options"]["targets"] == targets and r["options"]["doc_style"] == body.doc_style
                    and (inflight(r, settings, now) or (not body.again and (r.get("finished") or {}).get("state") == "done"))):
                return {**view(r, now=now), "created": False}
        live = [r for r in recs if inflight(r, settings, now)]
        if sum(1 for r in live if r.get("owner_sub") == owner) >= settings.wda_deck_inflight_max:
            raise AuthError(f"만드는 중인 발표자료가 {settings.wda_deck_inflight_max}건입니다 — 끝난 뒤에 다시 누르세요.", status_code=429)
        if len(live) >= settings.wda_deck_inflight_box_max:
            raise AuthError("지금 발표자료를 만드는 사람이 많습니다 — 잠시 뒤 다시 누르세요.", status_code=429)
        try:
            data, size = await read_report(request, settings, principal, body.report_id)
            fmts = sorted({TEMPLATE_FORMAT[t] for t in templates_of(data) if t in TEMPLATE_FORMAT})
            not_ready = [f for f in fmts if not format_ready(caps, f)]
            if not_ready:
                raise DeckError("WDA 의 심의 보고서 꼴(" + ", ".join(f"{f} — {caps.formats.get(f) or '없음'}" for f in not_ready)
                                + ")이 아직 준비되지 않았습니다 — 준비(active)되기 전에는 심의 보고서를 넘기지 않습니다(기본 꼴로는 결정문 · "
                                  "액션아이템이 빠진다, 사용자 결정 11-01 U-6).", 409)
            fmt = fmts[0] if fmts else None
            job_id = secrets.token_hex(16)
            run_id = await wda_create(base, token, data=data, report_id=body.report_id, targets=targets,
                                      doc_style=body.doc_style, job_id=job_id, fmt=fmt)
        except DeckError as exc:
            _audit(request, principal, "deck_create", "failed", report_id=body.report_id, error=exc.message[:300])
            raise _http_error(exc) from exc
        title = data.get("title") if isinstance(data.get("title"), str) else ""
        rec = {"job_id": job_id, "owner_sub": owner, "owner_email": principal.email or owner,
               "conversation_id": body.conversation_id, "report": {"id": body.report_id, "title": title[:300]},
               "options": {"targets": targets, "doc_style": body.doc_style, "pptx_mode": PPTX_MODE},
               "wda": {"run_id": run_id, "format": fmt, "version": caps.version}, "state": "queued", "created_at": now, "render_submitted_at": None,
               "images_not_sent": len(file_refs(data.get("pages"))), "finished": None, "dismissed": None}
        await asyncio.to_thread(save, settings, rec)
    _audit(request, principal, "deck_create", "ok", job_id=job_id, report_id=body.report_id, targets=targets,
           doc_style=body.doc_style, format=fmt, wda_version=caps.version, bytes=size, images=rec["images_not_sent"])
    return {**view(rec, now=now), "created": True}


@router.get("/jobs", dependencies=[Depends(_knob)])
async def deck_jobs(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """내 잡(새것부터 20 · 숨긴 것 빼고) — 창을 닫은 잡을 입력창 위 줄에서 다시 연다. 아직 끝을 적지 않은 잡만 WDA 에 지금 상태를 묻는다.
    못 물은 잡도 목록에 남긴다('묻지 못했다' — 다음 차례에 다시 묻는다). 빼면 줄이 그 잡을 잃고 다시 묻기를 멈춰 끝 알림이 남지 않는다."""
    now = time.time()
    mine = [r for r in await asyncio.to_thread(records, settings)
            if r.get("owner_sub") == principal.subject and not r.get("dismissed")][:20]
    open_ = [r for r in mine if not r.get("finished")]
    folded: dict[str, dict | None] = {}
    if open_:
        base, token = _base_and_token(request, settings, principal)

        async def one(r: dict) -> tuple[str, dict | None]:
            try:
                run = await wda_run(base, token, r["wda"]["run_id"])
            except DeckError:
                return r["job_id"], None
            return r["job_id"], fold(run, rec=r, now=now, settings=settings)

        folded = dict(await asyncio.gather(*(one(r) for r in open_)))
    unasked = {"state": "preparing", "step": "WDA 에 묻지 못했습니다 — 다시 묻습니다", "progress": None, "error": None, "late": False,
               "next": None, "skipped": []}
    jobs = [view(r, now=now) if r.get("finished") else view(r, folded.get(r["job_id"]) or unasked, now=now) for r in mine]
    return {"jobs": jobs, "keep_days": settings.wda_deck_job_days}


@router.get("/jobs/{job_id}", dependencies=[Depends(_knob)])
async def deck_job(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """화면이 몇 초마다 본다 — 부작용이 없다(렌더 맡기기 · 알림은 advance)."""
    try:
        rec = await asyncio.to_thread(load, settings, job_id, principal.subject)
    except DeckError as exc:
        raise _http_error(exc) from exc
    if rec.get("finished"):
        return view(rec)
    base, token = _base_and_token(request, settings, principal)
    try:
        run = await wda_run(base, token, rec["wda"]["run_id"])
    except DeckError as exc:
        raise _http_error(exc) from exc
    return view(rec, fold(run, rec=rec, now=time.time(), settings=settings))


@router.post("/jobs/{job_id}/advance", dependencies=[Depends(_knob)])
async def deck_advance(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """잡을 한 걸음 — 렌더 맡기기(WDA 가 이어서 하지 않는 판) 또는 끝(알림 한 건, 단추를 누른 그 대화에). 잡마다 잠금 · 두 번 불러도 알림은 하나."""
    try:
        await asyncio.to_thread(load, settings, job_id, principal.subject)
    except DeckError as exc:
        raise _http_error(exc) from exc
    async with lock(job_id):
        rec = await asyncio.to_thread(load, settings, job_id, principal.subject)
        fin = rec.get("finished")
        if fin:
            return {**view(rec), "notice": fin.get("notice"), "noticed": bool(fin.get("saved"))}
        base, token = _base_and_token(request, settings, principal)
        try:
            run = await wda_run(base, token, rec["wda"]["run_id"])
            now = time.time()
            f = fold(run, rec=rec, now=now, settings=settings)
            if f["next"] == "render":
                await wda_render(base, token, rec["wda"]["run_id"], rec)
                rec["render_submitted_at"] = now
                await asyncio.to_thread(save, settings, rec)
                _audit(request, principal, "deck_render", "ok", job_id=job_id)
                return view(rec, fold(run, rec=rec, now=now, settings=settings), now=now)
            if f["next"] != "finish":
                return view(rec, f, now=now)
            files: list[dict] = []
            skipped = list(f["skipped"])
            state, error, step = f["state"], f["error"], f["step"]
            if f.get("raw_error"):
                # WDA 의 예외 글은 사람에게 보이지 않는다 — 끝을 적을 때 한 번 서버 로그에(WD-D49)
                logger.warning("발표자료 잡 %s — WDA 실패 까닭=%r", job_id, f["raw_error"])
            if state == "done":
                arts = await wda_artifacts(base, token, rec["wda"]["run_id"])
                for t in rec["options"]["targets"]:
                    size = arts.get(WDA_KIND[t])
                    if size is not None:
                        files.append({"kind": t, "bytes": size})
                made = {x["kind"] for x in files}
                told = {s["target"] for s in skipped}
                skipped = [s for s in skipped if s["target"] not in made] + [
                    {"target": t, "reason": "WDA 가 만들지 않았습니다"} for t in rec["options"]["targets"] if t not in made and t not in told]
                if not files:
                    state, step, error = "failed", "파일 만들기에서 멈춤", "WDA 가 끝났다고 했지만 받을 파일이 하나도 없습니다."
        except DeckError as exc:
            raise _http_error(exc) from exc
        n = notice(rec, state=state, files=files, skipped=skipped, error=error, step=step, keep_days=settings.wda_deck_job_days)
        store = request.app.state.conv_store
        try:
            saved = await asyncio.to_thread(
                store.append, conversation_id=rec["conversation_id"], owner_sub=rec["owner_sub"], role="assistant",
                content=n["text"], meta={"activity": n["activity"], "upload": True, "deck": n["deck"]})
        except sqlite3.OperationalError as exc:
            # 끝을 적지 않는다 — 화면이 다시 부르면 그때 남긴다(알림 없이 끝난 잡이 되지 않게)
            raise AuthError("대화 저장소가 바쁩니다 — 잠시 뒤 다시 시도합니다.", status_code=503) from exc
        rec["finished"] = {"state": state, "step": step, "error": error, "files": files, "skipped": skipped,
                           "at": time.time(), "notice": n, "saved": bool(saved)}
        await asyncio.to_thread(save, settings, rec)
    _audit(request, principal, "deck_finish", "ok" if state == "done" else "failed", job_id=job_id, report_id=rec["report"]["id"],
           files=[x["kind"] for x in files], skipped=[s["target"] for s in skipped], noticed=bool(saved))
    return {**view(rec), "notice": n, "noticed": bool(saved)}


@router.post("/jobs/{job_id}/dismiss", dependencies=[Depends(_knob)])
async def deck_dismiss(
    job_id: str,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """입력창 위 '끝나지 않은 발표자료' 줄에서 숨긴다 — 기록 · WDA 실행은 그대로(WDA 에 취소가 없다)."""
    try:
        # 잠금보다 먼저 — 꼴이 틀리거나 없거나 남의 잡이면 잠금을 만들지 않는다(아무 id 로 부른 만큼 잠금이 쌓이지 않게 · advance 와 같다)
        await asyncio.to_thread(load, settings, job_id, principal.subject)
    except DeckError as exc:
        raise _http_error(exc) from exc
    async with lock(job_id):
        rec = await asyncio.to_thread(load, settings, job_id, principal.subject)
        rec["dismissed"] = time.time()
        await asyncio.to_thread(save, settings, rec)
    return {"job_id": job_id, "dismissed": True}


def _filename(title: str, kind: str) -> str:
    ext = _FILE[kind][0]
    base = re.sub(r"[\x00-\x1f\x7f/\\:*?\"<>|]+", " ", title or "").strip()[:80] or "발표자료"
    return base + ext


class _DeckFileStream(StreamingResponse):
    """WDA 에서 받아 흘리는 파일 — 끝나든 끊기든 상류 응답 · 클라이언트를 닫는다(생성기 finally 에만 맡기면 끊김에서 새어 나간다 — _CrStream 과 같은 까닭)."""

    def __init__(self, up: httpx.Response, cli: httpx.AsyncClient, content: AsyncIterator[bytes], **kw: Any) -> None:
        super().__init__(content, **kw)
        self._up, self._cli = up, cli

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                await self._up.aclose()
                await self._cli.aclose()


@router.get("/jobs/{job_id}/files/{kind}", dependencies=[Depends(_knob)])
async def deck_file(
    job_id: str,
    kind: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """맡긴 사람만 — 요청한 사람의 이름으로 WDA 에서 받아 그대로 흘린다(attachment · nosniff · no-store · HTML 은 CSP sandbox, WD-D14)."""
    try:
        rec = await asyncio.to_thread(load, settings, job_id, principal.subject)
    except DeckError as exc:
        raise _http_error(exc) from exc
    fin = rec.get("finished") or {}
    if kind not in _FILE or fin.get("state") != "done" or kind not in {x["kind"] for x in fin.get("files") or []}:
        raise AuthError("그 파일이 없습니다.", status_code=404)
    base, token = _base_and_token(request, settings, principal)
    cli = _http(httpx.Timeout(300.0, connect=10.0))
    try:
        up = await cli.send(cli.build_request(
            "GET", f"{base}/api/runs/{quote(rec['wda']['run_id'], safe='')}/download/{WDA_KIND[kind]}", headers=_auth(token)), stream=True)
    except httpx.HTTPError as exc:
        await cli.aclose()
        raise AuthError(f"WDA 에 연결하지 못했습니다({exc.__class__.__name__}).", status_code=502) from exc
    if up.status_code != 200:
        await up.aread()
        await up.aclose()
        await cli.aclose()
        if up.status_code in (404, 410):
            raise AuthError("파일이 지워졌습니다 — 그 보고서의 '발표자료로' 를 다시 누르세요.", status_code=404)
        err = _wda_error(up, "내려받기")
        raise AuthError(err.message, status_code=err.status)
    headers = {"Content-Disposition": f"attachment; filename=\"deck{_FILE[kind][0]}\"; filename*=UTF-8''{quote(_filename(rec['report'].get('title') or '', kind))}",
               "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"}
    if kind == "html":
        headers["Content-Security-Policy"] = "sandbox"
    if up.headers.get("content-length") and not up.headers.get("content-encoding"):
        headers["Content-Length"] = up.headers["content-length"]
    _audit(request, principal, "deck_download", "ok", job_id=job_id, kind=kind, bytes=up.headers.get("content-length"))

    async def body() -> AsyncIterator[bytes]:
        async for chunk in up.aiter_bytes():
            yield chunk

    return _DeckFileStream(up, cli, body(), media_type=_FILE[kind][1], headers=headers)
