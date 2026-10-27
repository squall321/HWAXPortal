# DocForge 정밀 변환의 포털 몫 — 잡 기록(누가 맡겼나) · 패키지 읽기(데이터 루트 밑만) · RA 에 사용자 명의로 엄격 생성(docs/doc-to-ra DF-D17)
"""DocForge 는 RA 에 넣지 않는다(DF-D2) — 패키지(report.json + resources/ + conversion.json)만 만든다. 넣는 것은 여기다.

흐름(docs/doc-to-ra/cae00-handoff.md §4)
1. 맡기기 — 라우트가 스테이징의 호스트 경로를 사용자 PAT 로 게이트웨이 MCP `docforge_convert` 에 넘기고 job_id 를 받는다 → 잡 기록(맡긴 사람).
2. 진행 — 화면이 1.5초마다 포털 라우트를 거쳐 `docforge_status` 를 본다. 기록의 주인이 아니면 '없다' 로 답한다(있는지도 알리지 않는다).
3. 받기 — `docforge_package` 의 package_rel 을 DocForge 데이터 루트(설정 docforge_package_root — 비면 형제 리포
   ../HEAXHub/var/app_data/doc_forge) 밑에서 읽는다. realpath 가 루트 밖이면 거절한다.
4. 넣기 — RA 가지와 같은 사용자 명의 토큰으로 report.json 이 가리키는 resources/ 를 하나씩 `POST /api/files` → 'res://<이름>' 을 받은 id 로 →
   template_id · template_version 을 pages[0] 에서 위로 올려 `POST /api/reports`(엄격 생성 — 배치를 지키는 유일한 길, DF-D3).
   RA 상한(설정 docforge_ra_file_max_mb, RA 기본 25MB)을 넘는 리소스는 올리지 않고 그 파일 칸을 빼고 경고로 알린다.
5. 한 잡은 한 번만 넣는다 — 기록에 report_id 가 있으면 그것을 돌려준다(두 번 눌러도 보고서가 둘이 되지 않게 · 잡마다 잠금).
6. '이 대화에서 분석'(DF-D19) — 같은 잡 길로 맡기고(purpose chat), 끝나면 패키지의 document.md(챗에서 읽는 글 — DocForge R-D40)를 문서 칩으로.
   대화용 잡은 RA 에 넣지 않는다.
기록 · 로그에는 문서 글을 남기지 않는다(이름 · 수 · 번호만).
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from app.config import Settings

# 스테이징 루트 아래 — 사용자 폴더 이름(영숫자 · -_@.)과 겹치지 않는다. 스테이징 청소(6시간)에서 빠지고 docforge_job_days(7일) 뒤 지운다(E15)
JOBS_DIR = "#docforge-jobs"
_JOB_RE = re.compile(r"^[A-Za-z0-9_-]{6,80}$")
_RES = "res://"
_LOCKS: dict[str, asyncio.Lock] = {}


class DeliveryError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


# ── 잡 기록 ──────────────────────────────────────────────────────────────────────────────────
def _file(settings: Settings, job_id: str) -> Path:
    if not isinstance(job_id, str) or not _JOB_RE.fullmatch(job_id):
        raise DeliveryError("그 변환 잡이 없습니다.", 404)
    d = Path(settings.upload_staging_dir) / JOBS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{job_id}.json"


def _write(p: Path, rec: dict) -> None:
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def save_job(settings: Settings, job_id: str, *, owner_sub: str, owner_email: str, filename: str, purpose: str = "ra") -> dict:
    """purpose — ra(정밀 변환 → RA 엄격 생성) · chat(이 대화에서 분석 → 문서 칩)."""
    rec = {"job_id": job_id, "owner_sub": owner_sub, "owner_email": owner_email, "filename": filename, "purpose": purpose,
           "created_at": time.time(), "delivered": None}
    _write(_file(settings, job_id), rec)
    return rec


def load_job(settings: Settings, job_id: str, owner_sub: str) -> dict:
    """맡긴 사람의 기록만 — 남의 것 · 없는 것은 똑같이 404(있는지도 알리지 않는다)."""
    p = _file(settings, job_id)
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rec = None
    if not isinstance(rec, dict) or rec.get("owner_sub") != owner_sub:
        raise DeliveryError("그 변환 잡이 없습니다.", 404)
    return rec


def mark_delivered(settings: Settings, job_id: str, rec: dict, result: dict) -> None:
    _write(_file(settings, job_id), {**rec, "delivered": result})


def list_jobs(settings: Settings, owner_sub: str, *, purpose: str = "ra", limit: int = 20) -> list[dict]:
    """맡긴 사람의 잡 기록 — 새것부터 limit 개(숨긴 것 · 다른 목적은 뺀다). 깨진 기록은 건너뛴다. 창을 닫아 넣지 못한 잡을 다시 열 때 쓴다(E15)."""
    d = Path(settings.upload_staging_dir) / JOBS_DIR
    if not d.is_dir():
        return []
    out = []
    for p in d.glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (isinstance(rec, dict) and rec.get("owner_sub") == owner_sub and rec.get("purpose", "ra") == purpose
                and not rec.get("dismissed") and _JOB_RE.fullmatch(str(rec.get("job_id") or ""))):
            out.append(rec)
    out.sort(key=lambda r: r.get("created_at") or 0, reverse=True)
    return out[:limit]


def dismiss(settings: Settings, job_id: str, rec: dict) -> None:
    """목록에서 숨긴다 — 기록은 남는다(진행 · 배달은 그대로 된다)."""
    _write(_file(settings, job_id), {**rec, "dismissed": time.time()})


def lock(job_id: str) -> asyncio.Lock:
    return _LOCKS.setdefault(job_id, asyncio.Lock())


# ── 패키지 ───────────────────────────────────────────────────────────────────────────────────
def package_root(settings: Settings) -> Path:
    if settings.docforge_package_root:
        return Path(settings.docforge_package_root)
    return Path(__file__).resolve().parents[3].parent / "HEAXHub" / "var" / "app_data" / "doc_forge"


def package_dir(settings: Settings, package_rel: str) -> Path:
    """package_rel(DocForge 데이터 루트 기준) → 실제 폴더. 루트 밖(.. · 링크)이거나 report.json 이 없으면 거절."""
    root = package_root(settings).resolve()
    if not isinstance(package_rel, str) or not package_rel or package_rel.startswith("/"):
        raise DeliveryError("DocForge 가 패키지 위치를 주지 않았습니다.", 502)
    p = (root / package_rel).resolve()
    if not p.is_relative_to(root):
        raise DeliveryError("패키지 위치가 DocForge 데이터 루트 밖입니다 — 받지 않았습니다.", 502)
    if not (p / "report.json").is_file() or not (p / "conversion.json").is_file():
        raise DeliveryError("패키지를 찾지 못했습니다 — 포털이 DocForge 데이터 루트를 보는지(docforge_package_root) 확인하세요.", 502)
    return p


def document_text(settings: Settings, pkg: dict) -> str:
    """패키지의 document.md(DocForge 0.3 부터 — document_rel). 패키지 폴더 밑만 읽는다(package_dir 와 같은 검사)."""
    pdir = package_dir(settings, pkg.get("package_rel"))
    f = (pdir / "document.md").resolve()
    if not f.is_relative_to(pdir) or not f.is_file():
        raise DeliveryError("DocForge 가 읽을 글(document.md)을 만들지 않았습니다 — DocForge 판이 낡았을 수 있습니다.", 502)
    return f.read_text(encoding="utf-8")


def _refs(value) -> set[str]:
    if isinstance(value, str):
        return {value[len(_RES):]} if value.startswith(_RES) else set()
    if isinstance(value, dict):
        return set().union(*(_refs(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_refs(v) for v in value)) if value else set()
    return set()


def _swap(value, ids: dict[str, str | None]):
    """'res://<이름>' → RA file id. 올리지 못한 리소스(None)를 가리키는 파일 칸({file_id: …})은 목록에서 뺀다."""
    if isinstance(value, str):
        return ids.get(value[len(_RES):], value) if value.startswith(_RES) else value
    if isinstance(value, list):
        out = []
        for v in value:
            fid = v.get("file_id") if isinstance(v, dict) else None
            if isinstance(fid, str) and fid.startswith(_RES) and ids.get(fid[len(_RES):]) is None:
                continue
            out.append(_swap(v, ids))
        return out
    if isinstance(value, dict):
        return {k: _swap(v, ids) for k, v in value.items()}
    return value


def summary(conv: dict) -> dict:
    """변환 보고서 요약 — 대화 알림 · 화면 패널에 싣는다(수만, 문서 글 없음)."""
    counts = conv.get("counts") or {}
    acc = conv.get("accounting") or {}
    return {"pages": counts.get("units"), "blocks": counts.get("blocks"), "dropped": len(conv.get("dropped") or []),
            "model_written": len(conv.get("model_written") or []), "unaccounted": len(acc.get("unaccounted") or []),
            "fidelity": conv.get("fidelity"), "parser": conv.get("parser")}


# ── RA 에 넣기 ───────────────────────────────────────────────────────────────────────────────
Remint = Callable[[], Awaitable[str | None]]


def _ra_error(r: httpx.Response) -> str:
    try:
        j = r.json()
        msg = j.get("message") or j.get("detail") or j.get("error") or ""
    except ValueError:
        msg = r.text
    return str(msg)[:300]


async def deliver(settings: Settings, pkg: Path, *, token: str, workspace: str = "", remint: Remint | None = None) -> dict:
    """패키지 → RA 보고서(엄격 생성). 돌려주는 것 — report_id · url · title · 올린 리소스 수 · warnings. RA 거절은 DeliveryError."""
    report = json.loads((pkg / "report.json").read_text(encoding="utf-8"))
    conv = json.loads((pkg / "conversion.json").read_text(encoding="utf-8"))
    pages = report.get("pages") or []
    if not pages:
        raise DeliveryError("패키지에 쪽이 없습니다 — 보고서를 만들지 않았습니다.", 502)
    res_dir = (pkg / "resources").resolve()
    limit = int(settings.docforge_ra_file_max_mb) * 1024 * 1024
    base = settings.ra_base_url.rstrip("/")
    warnings: list[str] = []
    state = {"token": token, "reminted": False}

    async def post(cli: httpx.AsyncClient, path: str, **kw) -> httpx.Response:
        def hdrs() -> dict:
            h = {"Authorization": f"Bearer {state['token']}"}
            if workspace:
                h["X-Workspace-Slug"] = workspace
            return h
        r = await cli.post(base + path, headers=hdrs(), **kw)
        if r.status_code == 401 and remint is not None and not state["reminted"]:
            # 캐시해 둔 위임 토큰을 RA 가 거절했다(회수 · 비밀 교체) — 한 번만 새로 받아 다시(RA 가지와 같은 규칙)
            state["reminted"] = True
            fresh = await remint()
            if fresh:
                state["token"] = fresh
                if "files" in kw:                       # 올린 스트림은 다시 읽어야 한다
                    name, fh, mime = kw["files"]["file"]
                    fh.seek(0)
                r = await cli.post(base + path, headers=hdrs(), **kw)
        return r

    ids: dict[str, str | None] = {}
    async with httpx.AsyncClient(timeout=300) as cli:
        for name in sorted(_refs(pages)):
            f = (res_dir / name).resolve()
            if "/" in name or not f.is_relative_to(res_dir) or not f.is_file():
                raise DeliveryError(f"패키지가 가리키는 리소스가 없습니다({name}).", 502)
            size = f.stat().st_size
            if size > limit:
                ids[name] = None
                warnings.append(f"리소스 {name}({size / 1048576:.1f}MB)는 RA 상한({settings.docforge_ra_file_max_mb}MB)을 넘어 "
                                "올리지 않았습니다 — 그 그림 · 첨부 칸은 비었습니다(원본에서 직접 붙이세요).")
                continue
            mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            with f.open("rb") as fh:
                r = await post(cli, "/api/files", files={"file": (name, fh, mime)})
            if r.status_code >= 400:
                raise DeliveryError(f"RA 가 리소스 {name} 를 받지 않았습니다(HTTP {r.status_code} {_ra_error(r)})"
                                    + (f" — 앞서 올린 리소스 {sum(1 for v in ids.values() if v)}개는 RA 에 남았습니다" if ids else ""), 502)
            fid = ((r.json().get("data") or {}).get("id"))
            if not fid:
                raise DeliveryError(f"RA 가 리소스 {name} 의 번호를 돌려주지 않았습니다.", 502)
            ids[name] = str(fid)
        pages = _swap(pages, ids)
        body = {"template_id": pages[0]["template_id"], "template_version": pages[0]["template_version"],
                "title": (report.get("title") or "DocForge 변환")[:255], "tags": report.get("tags") or [], "pages": pages}
        if report.get("report_date"):
            body["report_date"] = report["report_date"]
        r = await post(cli, "/api/reports", json=body)
    if r.status_code >= 400:
        hint = " — RA 에 문서 가져오기 템플릿(__import_blank__)이 없으면 RA 웹 '가져오기' 를 한 번 쓰면 생깁니다" \
            if "template" in _ra_error(r).lower() else ""
        raise DeliveryError(f"RA 가 보고서를 만들지 않았습니다(HTTP {r.status_code} {_ra_error(r)}){hint}.", 502)
    data = r.json().get("data") or {}
    rid, slug = data.get("id"), data.get("workspace_slug")
    if rid is None:
        raise DeliveryError("RA 가 보고서 번호를 돌려주지 않았습니다 — 만들어졌는지 RA 에서 확인하세요.", 502)
    return {"report_id": rid, "title": data.get("title") or body["title"], "url": f"/w/{slug}/reports/{rid}" if slug else None,
            "resources": sum(1 for v in ids.values() if v), "warnings": warnings, **summary(conv),
            "conversion_warnings": (conv.get("warnings") or [])[:20]}
