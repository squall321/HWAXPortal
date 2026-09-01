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


# ── 목적지 레지스트리 ────────────────────────────────────────────
# 업로드가 materialtwin 물성 하나로 고정돼 있던 것을 목적지 선택형으로 연다.
# 확장자로 **자동 라우팅하지 않는다** — 목적지는 사람이 고른다(PLAN-destinations.md).
# 같은 확장자를 다른 곳에 넣고 싶은 경우가 있고, 자동 분기는 이 기능의 2층 권한 게이트
# 설계(오염 파급이 큰 곳일수록 사람이 확인)와 어긋난다.
#
# groups_attr 는 Settings 의 그룹 리스트 property 이름이다. 목적지마다 파급이 달라
# 그룹을 따로 둔다 — 물성 DB 오염과 CAD 과제 생성은 위험 등급이 같지 않다.
DESTINATIONS: dict[str, dict] = {
    "material": {
        "label": "물성 DB — 인장·완화 시험 등록",
        "exts": {"csv", "xlsx"},
        "groups_attr": "upload_allowed_group_list",
    },
    "stepforge": {
        "label": "StepForge — 어셈블리 파트 추출·메시·K파일",
        "exts": {"step", "stp", "msh", "zip"},
        "groups_attr": "upload_group_step_list",
    },
}


def _dest_groups(settings: Settings, dest_id: str) -> list[str]:
    spec = DESTINATIONS.get(dest_id)
    if not spec:
        return []
    return list(getattr(settings, spec["groups_attr"], []) or [])


def allowed_destinations(settings: Settings, groups: list[str], ext: str) -> list[dict]:
    """이 사용자·이 확장자로 고를 수 있는 목적지. 되묻기(B) 화면의 입력이다.

    빈 배열이면 프론트가 "보낼 곳이 없다" 를 띄운다 — 조용히 아무 데나 보내지 않는다.
    """
    have = set(groups or [])
    out: list[dict] = []
    for did, spec in DESTINATIONS.items():
        if ext and ext not in spec["exts"]:
            continue
        allowed = set(_dest_groups(settings, did))
        if allowed and (allowed & have):
            out.append({"id": did, "label": spec["label"]})
    return out


def require_any_upload_group(settings: Settings, groups: list[str]) -> None:
    """수신(스테이징) 게이트 — 목적지 **하나라도** 쓸 수 있으면 통과.

    목적지별 판정은 dispatch 가 다시 한다. 여기서 특정 목적지 그룹을 요구하면
    CAD 담당자가 STEP 을 올리지도 못한다(목적지를 나누기 전 동작이 그랬다).
    어디에도 속하지 않으면 파일을 받지 않는다 — 쓰지도 못할 파일을 디스크에 쌓지 않는다.
    """
    have = set(groups or [])
    for did in DESTINATIONS:
        allowed = set(_dest_groups(settings, did))
        if allowed and (allowed & have):
            return
    raise AuthError(
        "파일 업로드 권한이 없습니다 — 업로드 대상 그룹에 속해 있어야 합니다.",
        status_code=403,
    )


def require_destination_group(settings: Settings, groups: list[str], dest_id: str) -> None:
    """dispatch 층의 재검사. /upload 응답의 destinations 를 믿지 않는다 — 클라이언트가
    목적지 문자열을 바꿔 보낼 수 있으므로 실제 실행 직전에 다시 판정한다."""
    if dest_id not in DESTINATIONS:
        raise AuthError(f"알 수 없는 목적지입니다: {dest_id}", status_code=400)
    allowed = set(_dest_groups(settings, dest_id))
    if not allowed or not (allowed & set(groups or [])):
        raise AuthError(
            f"'{DESTINATIONS[dest_id]['label']}' 으로 보낼 권한이 없습니다.",
            status_code=403,
        )


def host_path(settings: Settings, container_path: str | Path) -> str:
    """컨테이너 경로 → 호스트 절대경로. 다른 컨테이너(StepForge)에 파일을 넘길 때 쓴다.

    MCP upload_step 은 "서버가 읽을 수 있는 절대경로" 를 받는데, 포탈이 보는
    /var/upload-staging 은 포탈 컨테이너 안에서만 유효하다. apptainer 가 $HOME 을
    자동 마운트하므로 호스트 경로는 양쪽에서 같게 보인다(실측 확인).
    upload_staging_host_dir 이 비면 변환하지 않는다(로컬·비컨테이너 실행).
    """
    p = str(container_path)
    hostdir = (settings.upload_staging_host_dir or "").rstrip("/")
    base = str(settings.upload_staging_dir).rstrip("/")
    if hostdir and p.startswith(base + "/"):
        return hostdir + p[len(base):]
    return p


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
