# 챗 파일 업로드 — 수신·그룹게이트·스테이징(포탈 엣지). 파싱·등록은 materialtwin 에 위임한다.
from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.auth.errors import AuthError
from app.config import Settings

# 스트리밍 청크 — 파일을 메모리에 통째로 올리지 않는다(앱 하드 상한 대신 이 방식이 진짜 방어).
_CHUNK = 1 << 20  # 1MiB


def require_upload_group(settings: Settings, groups: list[str]) -> None:
    """업로드 권한 그룹 게이트(백엔드 층). 프론트가 버튼을 숨겨도 API 직접 호출을 막는다.

    허용 그룹이 비어 있으면 아무도 못 한다 — 안전 기본. 물성 DB 는 정본이라 오염 파급이 크다.
    """
    allowed = set(settings.upload_allowed_group_list)
    if not allowed or not (allowed & set(groups or [])):
        raise AuthError(
            "파일 업로드 권한이 없습니다 — 물성 담당 그룹만 사용할 수 있습니다.",
            status_code=403,
        )


def _user_dir(settings: Settings, sub: str) -> Path:
    # sub 를 파일시스템에 안전한 형태로 — 경로 조작 방지(‘/’·‘..’ 제거).
    safe = "".join(c if c.isalnum() or c in "-_@." else "_" for c in (sub or "anon"))[:80]
    d = Path(settings.upload_staging_dir) / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def sweep_expired(settings: Settings) -> int:
    """TTL 지난 스테이징 파일을 지운다. 지운 개수 반환. 실패는 무시(청소가 업로드를 막지 않게)."""
    root = Path(settings.upload_staging_dir)
    if not root.exists():
        return 0
    cutoff = time.time() - settings.upload_staging_ttl_hours * 3600
    n = 0
    for f in root.glob("*/*"):
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                n += 1
        except OSError:
            continue
    return n


async def stage_upload(settings: Settings, sub: str, file: UploadFile) -> dict:
    """업로드 파일을 디스크로 스트리밍 저장(메모리 안전)하고 staging 메타를 반환한다.

    앱 하드 크기 상한은 두지 않는다 — nginx 2GB 가 바깥 경계고, 진짜 위험은 메모리라
    디스크 스트리밍으로 막는다. (docs/upload/PLAN.md 결정 참조.)
    """
    sweep_expired(settings)
    d = _user_dir(settings, sub)
    staging_id = uuid.uuid4().hex
    orig = (file.filename or "upload").replace("/", "_").replace("\\", "_")
    dest = d / f"{staging_id}__{orig}"
    size = 0
    with dest.open("wb") as out:
        while True:
            chunk = await file.read(_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            out.write(chunk)
    ext = Path(orig).suffix.lower().lstrip(".")
    return {
        "staging_id": staging_id,
        "filename": orig,
        "size": size,
        "ext": ext,
        "content_type": file.content_type or "",
        "path": str(dest),
    }


def staged_path(settings: Settings, sub: str, staging_id: str, filename: str) -> Path:
    """확정·삭제용 경로 복원. staging_id 가 파일명 접두라 사용자 폴더 안에서만 찾는다."""
    d = _user_dir(settings, sub)
    # staging_id 로 시작하는 파일 하나. 경로 조작은 _user_dir 의 sub 정규화로 이미 막힌다.
    for f in d.glob(f"{staging_id}__*"):
        return f
    raise AuthError("staging 파일을 찾을 수 없습니다(만료됐거나 이미 처리됨).", status_code=404)


# ── 파싱 + MCP 도구 호출 (분석·확정 단계) ────────────────────────────────────
import csv as _csv
import json as _json

import httpx as _httpx

# CSV 헤더에서 변형률·응력 열을 찾는다. 열 이름이 조금씩 달라도 잡히게 후보를 넓게 둔다.
_STRAIN_KEYS = ("strain", "변형률", "eng_strain", "true_strain", "e")
_STRESS_KEYS = ("stress_mpa", "stress", "응력", "eng_stress", "sigma", "s")


def parse_tensile_csv(path: Path) -> dict:
    """인장 CSV → strain·stress_mpa 배열 + 감지 요약. stdlib 만 쓴다(포탈에 pandas 없음).

    xlsx 등 다른 형식은 이 경로가 아니라 materialtwin sniff 로 위임한다(미구현: fast-follow).
    """
    rows = list(_csv.reader(path.open(newline="", encoding="utf-8-sig")))
    if not rows:
        raise AuthError("빈 파일입니다.", status_code=422)
    header = [h.strip().lower() for h in rows[0]]

    def _find(keys):
        for i, h in enumerate(header):
            if h in keys:
                return i
        return None

    si = _find(_STRAIN_KEYS)
    ti = _find(_STRESS_KEYS)
    if si is None or ti is None:
        return {"parsed": False, "header": rows[0],
                "reason": "변형률/응력 열을 찾지 못했습니다 — 헤더에 strain, stress_mpa 가 있어야 합니다.",
                "needs_manual_mapping": True}
    strain, stress = [], []
    for r in rows[1:]:
        if len(r) <= max(si, ti):
            continue
        try:
            strain.append(float(r[si])); stress.append(float(r[ti]))
        except ValueError:
            continue
    if len(strain) < 5:
        raise AuthError(f"유효 데이터 점이 {len(strain)}개뿐입니다 — 최소 5개 필요.", status_code=422)
    return {"parsed": True, "n_points": len(strain), "strain": strain, "stress_mpa": stress,
            "strain_col": rows[0][si], "stress_col": rows[0][ti], "needs_manual_mapping": False}


async def mcp_call(gateway_url: str, pat: str, tool: str, args: dict, timeout: float = 90.0) -> dict:
    """게이트웨이 MCP 도구를 사용자 PAT 로 한 번 호출한다(streamable-http: init→call).

    포탈은 원래 MCP 를 직접 안 부르지만, 업로드의 register(dry_run/확정)는 사용자 신원으로
    나가야 하고 감사도 사람 단위로 남아야 하므로 여기서 최소 클라이언트로 부른다.
    """
    url = gateway_url.rstrip("/") + "/mcp"
    hdr = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json",
           "Accept": "application/json, text/event-stream"}

    def _last_data(text: str) -> dict:
        # SSE 응답에서 마지막 data: 줄의 JSON.
        lines = [ln[6:] for ln in text.splitlines() if ln.startswith("data: ")]
        return _json.loads(lines[-1]) if lines else _json.loads(text)

    async with _httpx.AsyncClient(timeout=timeout) as c:
        init = await c.post(url, headers=hdr, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "portal-upload", "version": "1"}}})
        if init.status_code != 200:
            raise AuthError(f"게이트웨이 초기화 실패 ({init.status_code}).", status_code=502)
        sid = init.headers.get("mcp-session-id", "")
        sh = {**hdr, "mcp-session-id": sid}
        await c.post(url, headers=sh, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        res = await c.post(url, headers=sh, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool, "arguments": args}})
        env = _last_data(res.text)
        if env.get("error"):
            raise AuthError(f"도구 오류: {env['error'].get('message', env['error'])}", status_code=502)
        content = (env.get("result") or {}).get("content") or []
        text = content[0].get("text", "{}") if content else "{}"
        try:
            return _json.loads(text)
        except ValueError:
            return {"raw": text}
