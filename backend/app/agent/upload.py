# 챗 파일 업로드 — 수신·그룹게이트·스테이징(포탈 엣지). 파싱·등록은 materialtwin 에 위임한다.
from __future__ import annotations

import logging
import re
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
        "platform": "plat:materialtwin",
    },
    "stepforge": {
        "label": "StepForge — 어셈블리 파트 추출·메시·K파일",
        "exts": {"step", "stp", "msh", "zip"},
        "groups_attr": "upload_group_step_list",
        "platform": "plat:stepforge",
    },
    # K파일은 여기다. 챗 프롬프트로 나르지 않는 이유는 크기다 — LS-DYNA 덱은 수십 MB 가 흔해
    # upload_kfile(content=문자열) 로는 못 싣는다. 스테이징한 **호스트 경로**를 넘겨
    # upload_local_path 가 읽게 한다(StepForge 와 같은 방식 — apptainer 가 $HOME 을 공유한다).
    # 문서는 **각 서비스가 자기 취입기를 갖고 있다** — 포털은 배달만 한다(파서를 새로 안 만든다).
    # DRM 은 대개 브라우저 읽기에 투명해서 여기 도착한 바이트가 이미 평문이다(사용자 실측).
    # 막히는 정책이면 그때 COM 추출기로 간다(docs/doc-deliberate).
    # 이 챗에서 읽고 묻기 — 어디에도 저장하지 않는다. AI 데이터 허브의 변환기를 빌려(그 사람 명의라 허브를 쓸 수 있는 사람만) 글 · 표 ·
    # 차트 데이터 · 발표자 노트를 .hwax.md 로 옮겨 화면이 문서 칩으로 붙인다(docs/chat-ppt PP-D17). 문서 목적지 중 맨 앞이다 — 올린 문서를
    # 그 자리에서 묻는 일이 가장 잦다.
    "chat": {
        "label": "이 대화에서 분석 — 글·표·차트·노트를 읽어 입력창에(저장하지 않음)",
        "exts": {"pptx", "docx", "pdf", "xlsx"},
        "groups_attr": "upload_allowed_group_list",
        "platform": "plat:aidatahub",
    },
    "reportarchive": {
        "label": "Report Archive — 슬라이드를 보고서 페이지로(그림·표 포함)",
        "exts": {"pptx"},                      # RA /imports/pptx 가 받는 것이 이것뿐이다
        "groups_attr": "upload_allowed_group_list",
        "platform": "plat:reportarchive",
        "max_mb_attr": "ra_import_max_mb",     # 크기 한도 — 목적지 목록에 실어 화면이 미리 막고, 보내기가 다시 본다(HP-02)
    },
    # 정밀 변환 — DocForge 가 패키지를 만들고(배치 · 표 · 차트 값 · 그림 판독) 포털이 그 사람 명의로 RA 에 **엄격 생성**한다(docs/doc-to-ra
    # DF-D2 · DF-D3 · DF-D17). 위 'Report Archive 로 보내기' 는 비교 기준선이라 남긴다. 권한은 RA 와 DocForge 둘 다(also).
    # md 는 PC 도우미 추출본(DRM 문서 — DF-D18)이다. 화면은 .md 를 브라우저에서 읽으므로 스테이징의 .md 는 도우미가 올린 것이고, 그래도 dispatch 가
    # 추출기 머리말을 다시 본다.
    "reportarchive_precise": {
        "label": "Report Archive — 정밀 변환(배치 유지 · 그림 판독)",
        "exts": {"pptx", "docx", "xlsx", "pdf", "md"},
        "groups_attr": "upload_allowed_group_list",
        "platform": "plat:reportarchive",
        "also": ("plat:docforge",),
        # 게이트웨이에 이 도구가 있어야 고를 수 있다 — DocForge 가 초안(draft)이면 게이트웨이에 안 떠서, 보이기는 하는데 고를 때마다
        # docforge_convert 에서 실패했다(10-25 cae00 업데이트 점검 — dev 도 같았다). allowed_destinations 의 tools 참고.
        "needs_tool": "docforge_convert",
    },
    "aidatahub": {
        "label": "AI 데이터 허브 — 지식카드로 변환(검토 후 저장)",
        "exts": {"pptx", "docx", "pdf", "xlsx", "md"},
        "groups_attr": "upload_allowed_group_list",
        "platform": "plat:aidatahub",
    },
    "dynaforge": {
        "label": "DynaForge — LS-DYNA 덱 전처리(재료·메시·초기응력·해석 세팅)",
        "exts": {"k", "key", "dyn", "inc"},
        "groups_attr": "upload_group_step_list",
        "platform": "plat:dynaforge",
    },
    # SimFlow 워크플로우 입력(docs/request-1027 HP-15) — 게이트웨이 REST 다리(/api/simflow/api/v1/mcp-uploads)로 그 사람 명의로 넣고, 받은 id 를
    # run_workflow 에 쓴다. 확장자 · 한도는 박스 설정이다(SimFlow 쪽 확인 전 — config 주석). SimFlow 도구가 게이트웨이에 없으면(dev) 고를 수 없다.
    "simflow": {
        "label": "SimFlow — 워크플로우 입력 파일",
        "exts": set(),
        "exts_attr": "simflow_upload_ext_set",
        "groups_attr": "upload_allowed_group_list",
        "platform": "plat:simflow",
        "max_mb_attr": "simflow_upload_max_mb",
        "needs_tool": "run_workflow",
        "needs_tool_app": "simflow",            # 다른 앱과 이름이 겹치면 게이트웨이가 simflow_run_workflow 로 낸다
    },
}


def dest_exts(settings: Settings, dest_id: str) -> set[str]:
    """목적지가 받는 확장자 — 설정으로 정하는 목적지(exts_attr)는 그 값."""
    spec = DESTINATIONS.get(dest_id) or {}
    attr = spec.get("exts_attr")
    return set(getattr(settings, attr, None) or ()) if attr else set(spec.get("exts") or ())


def _has_tool(spec: dict, tools: frozenset[str]) -> bool:
    need = spec["needs_tool"]
    app = spec.get("needs_tool_app")
    return need in tools or bool(app and f"{app.replace('-', '')}_{need}" in tools)


def _dest_groups(settings: Settings, dest_id: str) -> list[str]:
    spec = DESTINATIONS.get(dest_id)
    if not spec:
        return []
    return list(getattr(settings, spec["groups_attr"], []) or [])


def _dest_ok(settings: Settings, groups: list[str], dest_id: str) -> bool:
    """이 목적지로 보낼 수 있나 — 목적지 그룹(종전 설정) 이거나, 파일 올리기 권한 + 그 목적지
    플랫폼 허가(docs/access-control). 둘 다 없으면 못 보낸다(안전 기본)."""
    have = set(groups or [])
    if set(_dest_groups(settings, dest_id)) & have:
        return True
    spec = DESTINATIONS.get(dest_id) or {}
    plats = [spec.get("platform"), *spec.get("also", ())]    # also — 함께 있어야 하는 플랫폼(정밀 변환 = RA + DocForge)
    return bool(plats[0]) and "feat:upload" in have and all(p in have for p in plats)


# 게이트웨이가 지금 내놓는 도구 이름(인증 없는 /tools-map) — 목적지 가운데 그 도구가 있어야 도는 것(needs_tool)을 고를 때 본다. 60초 붙잡는다.
_GW_TOOLS: dict = {"at": float("-inf"), "names": None}
GW_TOOLS_TTL_S = 60.0


async def gateway_tool_names(settings: Settings) -> frozenset[str] | None:
    """게이트웨이 도구 지도의 이름들. 못 읽으면 None(모른다) — 그때는 목적지를 숨기지 않는다(게이트웨이가 잠깐 안 닿는다고 지우지 않는다)."""
    now = time.monotonic()
    if now - _GW_TOOLS["at"] < GW_TOOLS_TTL_S:
        return _GW_TOOLS["names"]
    names = None
    base = (settings.mcp_gateway_url or "").rstrip("/")
    if base:
        try:
            async with _httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(base + "/tools-map")
            m = r.json().get("map") if r.status_code < 400 else None
            names = frozenset(m) if isinstance(m, dict) else None
        except (_httpx.HTTPError, ValueError, AttributeError):
            names = None
    # 못 읽었으면 **마지막으로 읽은 지도**를 쓴다 — 게이트웨이 재기동 중 60초 창에 None(모름 = 숨기지 않음)이 되면 지금 없는 '정밀 변환' 이
    # 다시 보였다(docs/request-1027 HP-32). 한 번도 못 읽었으면 종전대로 None 이다.
    if names is not None:
        _GW_TOOLS["last"] = names
    else:
        names = _GW_TOOLS.get("last")
    _GW_TOOLS.update(at=now, names=names)
    return names


def allowed_destinations(settings: Settings, groups: list[str], ext: str, tools: frozenset[str] | None = None) -> list[dict]:
    """이 사용자·이 확장자로 고를 수 있는 목적지. 되묻기(B) 화면의 입력이다.

    빈 배열이면 프론트가 "보낼 곳이 없다" 를 띄운다 — 조용히 아무 데나 보내지 않는다.
    tools — 게이트웨이 도구 이름(gateway_tool_names). 주면 needs_tool 이 없는 목적지를 뺀다, None(모름)이면 종전대로 둔다.
    """
    out: list[dict] = []
    for did, spec in DESTINATIONS.items():
        if ext and ext not in dest_exts(settings, did):
            continue
        if spec.get("needs_tool") and tools is not None and not _has_tool(spec, tools):
            continue
        if _dest_ok(settings, groups, did):
            item = {"id": did, "label": spec["label"]}
            mx = dest_max_bytes(settings, did)
            if mx:
                item["max_bytes"] = mx
            out.append(item)
    return out


def upload_exts(settings: Settings, groups: list[str], tools: frozenset[str] | None = None) -> list[str]:
    """이 사람이 어딘가로 보낼 수 있는 확장자 전부 — 화면의 파일 고르기 · 끌어 놓기 목록에 더한다. 화면 목록은 빌드 때 정해져 설정으로
    정하는 확장자(SimFlow)를 몰랐다 — 목록 밖 파일은 끌어 놓아도 '붙이지 않는 형식' 이었다(docs/request-1027 HP-15)."""
    return sorted({e for d in allowed_destinations(settings, groups, "", tools) for e in dest_exts(settings, d["id"])})


def dest_max_bytes(settings: Settings, dest_id: str) -> int | None:
    """목적지의 크기 한도(바이트) — 없거나 0 이면 None(한도 없음)."""
    attr = (DESTINATIONS.get(dest_id) or {}).get("max_mb_attr")
    mb = int(getattr(settings, attr, 0) or 0) if attr else 0
    return mb * 1024 * 1024 if mb > 0 else None


def require_any_upload_group(settings: Settings, groups: list[str]) -> None:
    """수신(스테이징) 게이트 — 목적지 **하나라도** 쓸 수 있으면 통과.

    목적지별 판정은 dispatch 가 다시 한다. 여기서 특정 목적지 그룹을 요구하면
    CAD 담당자가 STEP 을 올리지도 못한다(목적지를 나누기 전 동작이 그랬다).
    어디에도 속하지 않으면 파일을 받지 않는다 — 쓰지도 못할 파일을 디스크에 쌓지 않는다.
    """
    for did in DESTINATIONS:
        if _dest_ok(settings, groups, did):
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
    if not _dest_ok(settings, groups, dest_id):
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
    if not _dest_ok(settings, groups, "material"):
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
    """TTL 지난 스테이징을 지운다. 지운 개수 반환. 실패는 무시(청소가 업로드를 막지 않게)."""
    root = Path(settings.upload_staging_dir)
    if not root.exists():
        return 0
    from app.agent.docforge_delivery import JOBS_DIR
    cutoff = time.time() - settings.upload_staging_ttl_hours * 3600
    # 정밀 변환 잡 기록은 DocForge 보존 기한만큼 둔다 — 창을 닫아 넣지 못한 잡을 다시 열어 넣는다(DocForge E15)
    jobs_cutoff = time.time() - settings.docforge_job_days * 86400
    n = 0
    # <사용자>/<staging_id 상자>. 파일이 곧바로 오면 폴더로 바꾸기 전에 남은 것이라 같이 지운다.
    for entry in root.glob("*/*"):
        try:
            # 상자 자체의 mtime 으로 판정한다 — 쓰는 중인 상자는 mtime 이 새것이라
            # 청소가 진행 중인 업로드를 지우지 않는다.
            if entry.stat().st_mtime >= (jobs_cutoff if entry.parent.name == JOBS_DIR else cutoff):
                continue
            if entry.is_file():
                entry.unlink()
                n += 1
            elif entry.is_dir():
                for f in entry.iterdir():
                    f.unlink()
                    n += 1
                entry.rmdir()
        except OSError:
            continue
    return n


def aidh_inbox_dir() -> Path:
    """AI 데이터 허브 변환기가 읽는 inbox — 변환기는 이 아래의 이름만 받는다."""
    import os
    return Path(os.environ.get("AIDH_CONVERT_INBOX") or (Path.home() / "aidh-inbox"))


def _aidh_ledger(settings: Settings) -> Path:
    return Path(settings.upload_staging_dir) / ".aidh-inbox-ledger.json"


def aidh_inbox_note(settings: Settings, name: str) -> None:
    """포털이 inbox 에 둔 사본 하나를 장부에 적는다 — 청소가 **포털이 넣은 것만** 지우게(남이 둔 파일은 건드리지 않는다, HP-29)."""
    import json
    led = _aidh_ledger(settings)
    try:
        cur = json.loads(led.read_text(encoding="utf-8")) if led.exists() else {}
    except (OSError, ValueError):
        cur = {}
    cur[name] = time.time()
    try:
        led.parent.mkdir(parents=True, exist_ok=True)
        tmp = led.with_suffix(".tmp")
        tmp.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")
        tmp.replace(led)
    except OSError:
        logger.warning("AIDH inbox 장부를 쓰지 못했다 — 이 사본(%s)은 청소되지 않는다", name)


def sweep_aidh_inbox(settings: Settings) -> int:
    """장부에서 aidh_inbox_ttl_hours 가 지난 사본을 inbox 에서 지운다 → 지운 개수. 실패는 무시(청소가 업로드를 막지 않게)."""
    import json
    led = _aidh_ledger(settings)
    if not led.exists():
        return 0
    try:
        cur = json.loads(led.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    cutoff = time.time() - settings.aidh_inbox_ttl_hours * 3600
    inbox = aidh_inbox_dir()
    gone = [n for n, t in cur.items() if isinstance(t, (int, float)) and t < cutoff]
    n = 0
    for name in gone:
        if "/" in name or name.startswith("."):
            cur.pop(name, None)                  # 장부가 이상하면 지우지 않고 뺀다
            continue
        try:
            (inbox / name).unlink(missing_ok=True)
            n += 1
        except OSError:
            continue
        cur.pop(name, None)
    if gone:
        try:
            tmp = led.with_suffix(".tmp")
            tmp.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")
            tmp.replace(led)
        except OSError:
            pass
    return n


async def stage_upload(settings: Settings, sub: str, file: UploadFile) -> dict:
    """업로드 파일을 디스크로 스트리밍 저장(메모리 안전)하고 staging 메타를 반환한다.

    앱 하드 크기 상한은 두지 않는다 — nginx 2GB 가 바깥 경계고, 진짜 위험은 메모리라
    디스크 스트리밍으로 막는다. (docs/upload/PLAN.md 결정 참조.)
    """
    sweep_expired(settings)
    sweep_aidh_inbox(settings)
    d = _user_dir(settings, sub)
    staging_id = uuid.uuid4().hex
    orig = (file.filename or "upload").replace("/", "_").replace("\\", "_")
    # staging_id 를 **파일명 접두가 아니라 폴더**로 쓴다. 접두를 쓰면 그 32자가 파일명의
    # 일부가 되어 StepForge 의 영구 파트 경로에까지 박힌다 — 그 경로가 곧 run_job 의
    # 범위 지정(match_path) 대상이라 남의 시스템 식별자를 오염시킨다(2026-09-01 e2e 확인).
    box = d / staging_id
    box.mkdir(parents=True, exist_ok=True)
    dest = box / orig
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


def ra_import_pages_to_ai(pages: list) -> tuple[list[dict], int]:
    """RA 가져오기 초안의 쪽 → `create_report_draft` 의 쪽 입력. (쪽들, 블록 수)를 돌려준다.

    RA `/api/imports/pptx` 의 쪽은 저장 꼴(`ReportPage`)이라 위젯 정의 `extra_blocks: [{id, type, props}]` 와 내용
    `content: {id: 내용}` 이 따로 있다. `create_report_draft`(→ RA `/api/reports/ai-draft`)는 정의 항목 **안의** content 를
    읽는다 — 저장 꼴을 그대로 넘겨 블록마다 '내용 없음' 으로 버려졌고, 쪽만 있고 블록 0 인 보고서가 됐다(10-22 cae00 — 29쪽 ·
    블록 0, docs/chat-ppt PP-D2). 정의에 내용을 넣으면 RA 정규화를 한 번 더 거쳐도 가져오기와 같다(RA 코드로 확인 — 제목 ·
    글 · 표 · 그림). 배치(layout_overrides)는 넘기지 않는다 — AI 초안 API 는 자동 배치를 다시 한다. 빈 쪽도 남긴다(슬라이드
    한 장이 보고서 한 쪽이다)."""
    out: list[dict] = []
    n = 0
    for p in pages or []:
        if not isinstance(p, dict):
            continue
        content = p.get("content") if isinstance(p.get("content"), dict) else {}
        blocks = []
        for d in p.get("extra_blocks") or []:
            if not isinstance(d, dict) or not d.get("id") or not d.get("type") or d["id"] not in content:
                continue
            blocks.append({"id": d["id"], "type": d["type"], "props": d.get("props") or {}, "content": content[d["id"]]})
        page: dict = {"extra_blocks": blocks}
        if p.get("name"):
            page["name"] = p["name"]
        out.append(page)
        n += len(blocks)
    return out, n


_KIND = {"pptx": "ppt", "ppt": "ppt", "docx": "word", "doc": "word", "pdf": "pdf", "xlsx": "excel"}


_CAPTION_HEAD = re.compile(r"^(?:Table|Figure)\s+\d+\s*:\s*")


def _caption(v) -> str:
    """변환기가 붙인 'Table 1: ' · 'Figure 2: ' 머리를 뗀다 — 문서에는 [표 N] · [그림 N] 이 이미 붙는다."""
    return _CAPTION_HEAD.sub("", " ".join(str(v or "").split()))


def _md_cell(v) -> str:
    return " ".join(str("" if v is None else v).split()).replace("|", "\\|")


def record_markdown(record: dict, filename: str) -> str:
    """AI 데이터 허브 변환 결과(record — 절 · 블록 · 표 · 그림) → `.hwax.md`(PC 추출기와 같은 꼴: 머리말 schema hwax-doc/1, 슬라이드는
    `## [s.N]`). 이 챗에서 읽고 묻는 데 쓴다(docs/chat-ppt PP-D17). 발표자 노트는 '> 발표자 노트:' 로, 표는 마크다운 표로, 그림은 자리와
    설명만 남긴다 — 그림 내용은 글로 옮기지 않았다고 적는다(그림 판독은 다음 단계). 모양이 틀린 칸은 건너뛴다."""
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    fmt = str(meta.get("source_format") or Path(filename).suffix.lstrip(".")).lower()
    slides = fmt in ("pptx", "ppt") or meta.get("doc_type") == "slide"
    tables = {t.get("id"): t for t in (record.get("tables") or []) if isinstance(t, dict)}
    figures = {f.get("id"): f for f in (record.get("figures") or []) if isinstance(f, dict)}
    body: list[str] = []
    n_top = 0

    def table_md(t: dict) -> list[str]:
        heads = [_md_cell(h) for h in (t.get("headers") or [])]
        rows = [r for r in (t.get("rows") or []) if isinstance(r, list)]
        width = max([len(heads), *(len(r) for r in rows)] or [0])
        if not width:
            return []
        heads = heads + [""] * (width - len(heads))
        out = [f"| {' | '.join(heads)} |", f"|{' --- |' * width}"]
        for r in rows:
            cells = [_md_cell(c) for c in r] + [""] * (width - len(r))
            out.append(f"| {' | '.join(cells)} |")
        return out

    def section(sec: dict, depth: int, top_no: int | None) -> None:
        title = " ".join(str(sec.get("title") or "").split())
        tag = f"[s.{top_no}] " if slides and top_no is not None else ""
        body.append(f"{'#' * min(6, depth + 1)} {tag}{title}".rstrip())
        body.append("")
        notes = False
        for b in sec.get("blocks") or []:
            if not isinstance(b, dict):
                continue
            kind, text = b.get("type"), str(b.get("text") or "").strip()
            if kind == "paragraph" and text == "[Speaker Notes]":
                notes = True
                continue
            if kind != "list_item" and body and body[-1] != "":
                body.append("")             # 목록 뒤 — 다음 단락 · 노트 · 표가 목록에 엉겨 붙지 않게
            if kind in ("paragraph", "code") and text:
                body.append(("> 발표자 노트: " + text.replace("\n", "\n> ")) if notes else text)
                body.append("")
            elif kind == "list_item" and text:
                marker = str(b.get("marker") or "•")
                body.append(f"{marker} {text}")
            elif kind == "table" and b.get("ref") in tables:
                t = tables[b["ref"]]
                body.append(f"[표 {t.get('number')}] {_caption(t.get('caption'))}".rstrip())
                body.extend(table_md(t))
                body.append("")
            elif kind == "figure" and b.get("ref") in figures:
                f = figures[b["ref"]]
                body.append(f"[그림 {f.get('number')}] {_caption(f.get('caption'))} — 그림 내용은 글로 옮기지 않았다")
                body.append("")
        if body and body[-1] != "":
            body.append("")
        for c in sec.get("children") or []:
            if isinstance(c, dict):
                section(c, depth + 1, None)

    for sec in record.get("sections") or []:
        if isinstance(sec, dict):
            n_top += 1
            section(sec, 1, n_top)
    text = "\n".join(body).strip() + "\n"
    title = " ".join(str(meta.get("title") or Path(filename).stem).split())
    head = ["---", "schema: hwax-doc/1", f"source: {Path(filename).name}", f"kind: {_KIND.get(fmt, 'word')}"]
    if slides:
        head.append(f"units: {n_top}")
    head += [f"chars: {len(text)}", "extracted_by: AI 데이터 허브 변환기(서버 — 저장하지 않음)", "---", "", f"# {title}", "", ""]
    return "\n".join(head) + text


def staged_path(settings: Settings, sub: str, staging_id: str, filename: str) -> Path:
    """확정·삭제용 경로 복원. staging_id 가 폴더라 그 안의 파일 하나를 집는다."""
    # staging_id 는 이제 **경로 한 조각**이라 값 자체를 막아야 한다(전에는 glob 패턴의
    # 접두라 그럴 필요가 없었다). uuid4().hex 만 통과시키면 '..' 도 '/' 도 못 들어온다.
    if not staging_id.isalnum():
        raise AuthError("staging_id 형식이 아닙니다.", status_code=400)
    box = _user_dir(settings, sub) / staging_id
    for f in sorted(box.glob("*")):
        if f.is_file():
            return f
    raise AuthError("staging 파일을 찾을 수 없습니다(만료됐거나 이미 처리됨).", status_code=404)


# ── 파싱 + MCP 도구 호출 (분석·확정 단계) ────────────────────────────────────
import csv as _csv
import json as _json

import httpx as _httpx

logger = logging.getLogger(__name__)

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
        try:
            res = await c.post(url, headers=sh, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool, "arguments": args}})
        finally:
            # ⚠ **세션을 닫는다.** 게이트웨이 SDK 는 세션 유휴 만료가 없어서, 안 닫으면
            # 챗과 공유하는 게이트웨이에 세션이 쌓인다 — `procedures/runner.py` 가 같은
            # 이유로 `finally` 에서 닫는다고 적어 뒀는데 이 경로만 안 닫고 있었다.
            if sid:
                try:
                    await c.request("DELETE", url, headers=sh)
                except Exception:  # noqa: BLE001 — 닫기 실패가 호출을 실패시키지 않는다
                    logger.info("업로드 MCP 세션 닫기 실패 sid=%s", sid, exc_info=True)
        env = _last_data(res.text)
        if env.get("error"):
            raise AuthError(f"도구 오류: {env['error'].get('message', env['error'])}", status_code=502)
        # ⚠ **여기가 `judge.py` 가 "베끼면 안 되는 예" 로 이름을 적어 둔 자리다**(모듈 머리말).
        # 셋이 전부 실패를 성공으로 만들고 있었다 —
        #   ① `result.isError` 를 안 읽었다. 게이트웨이 거절(`unknown tool:`·`forbidden:`·
        #      파괴 도구 관문)이 그대로 돌아와 라우트가 **`created: true`** 를 냈다.
        #   ② `content[0]` 만 봤다. 항목마다 블록으로 오는 도구는 23개 중 1개만 남았다.
        #   ③ 파싱 실패를 `{"raw": …}` 로 **정상 반환**했다 — 거절 문구가 결과인 척했다.
        # 다섯 번의 감사가 그 문장을 읽고도 함수는 안 고쳤다(6차에 실호출로 확인).
        # 같은 리포에 판정기가 있으니 그것을 쓴다.
        from app.procedures import judge as _J
        res_obj = env.get("result") or {}
        text, _other = _J.join_content(res_obj.get("content") or [])
        v = _J.judge(is_error=bool(res_obj.get("isError")), text=text)
        if not v.ok:
            raise AuthError(f"{tool}: {_J.short_error(v)}", status_code=502)
        return v.parsed if isinstance(v.parsed, dict) else {"result": v.parsed}
