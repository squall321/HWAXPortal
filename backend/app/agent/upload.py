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
