# 포털 업데이트 이력 — config/changelog.yaml 을 읽어 '아직 안 본 것'만 돌려준다(로그인 팝업용)
"""GET /changelog — 사용자가 아직 못 본 업데이트 항목.

파일은 **요청마다 mtime 을 확인해** 바뀌었을 때만 다시 읽는다. 항목을 적고 재기동을
기다릴 이유가 없고(운영자가 고치는 순간 반영), 매번 파싱하지도 않는다.

손상된 YAML 이나 이상한 항목은 **조용히 건너뛴다.** 업데이트 안내가 못 뜨는 것보다
포털이 500 을 내는 게 훨씬 나쁘다.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query

from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import get_current_principal

router = APIRouter(prefix="/changelog", tags=["changelog"])

# 한 번에 돌려줄 항목 수 상한 — 처음 로그인한 사람에게 이력 전체를 쏟지 않는다.
DEFAULT_LIMIT = 5
MAX_LIMIT = 20

_cache: dict[str, Any] = {"mtime": None, "entries": []}


def _norm_date(v: Any) -> str:
    """YAML 의 date 는 datetime.date 로 파싱된다 — 화면·비교 모두 ISO 문자열로 통일한다."""
    if isinstance(v, _dt.datetime):
        return v.date().isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    return str(v or "").strip()


def parse_entries(raw: Any) -> list[dict]:
    """YAML 본문 → 정규화된 항목 목록(최신 순). date 와 title 이 없는 항목은 버린다."""
    rows = (raw or {}).get("entries") if isinstance(raw, dict) else None
    out: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        date = _norm_date(row.get("date"))
        title = str(row.get("title") or "").strip()
        if not date or not title:
            continue
        items = [str(x).strip() for x in (row.get("items") or []) if str(x).strip()]
        out.append({
            "date": date,
            "title": title,
            "tag": str(row.get("tag") or "").strip(),
            "items": items,
        })
    # 파일이 최신 순으로 적혀 있더라도 정렬로 보장한다. 같은 날짜는 적힌 순서를 지킨다.
    return sorted(out, key=lambda e: e["date"], reverse=True)


def load_entries(path: Path) -> list[dict]:
    """파일을 읽어 항목을 돌려준다. mtime 이 그대로면 캐시를 쓴다."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return []  # 파일이 없으면 이력이 없는 것 — 팝업이 안 뜰 뿐이다
    if _cache["mtime"] != mtime:
        try:
            _cache["entries"] = parse_entries(yaml.safe_load(path.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001 — 손상된 YAML 로 포털을 세우지 않는다
            print(f"[changelog] parse failed: {exc!r}")
            _cache["entries"] = []
        _cache["mtime"] = mtime
    return _cache["entries"]


def select(entries: list[dict], since: str | None, limit: int) -> list[dict]:
    """`since` **이후**(배타적) 항목만, 최신부터 limit 개.

    since 가 없으면(처음 로그인) 전체에서 최신 limit 개다 — 이력을 통째로 쏟지 않는다.
    """
    picked = [e for e in entries if not since or e["date"] > since]
    return picked[:limit]


@router.get("")
def get_changelog(
    since: str = Query("", description="이 날짜(ISO) 이후 항목만. 사용자가 마지막으로 본 날짜."),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    settings: Settings = Depends(get_settings),
    _principal: Principal = Depends(get_current_principal),
) -> dict:
    entries = load_entries(Path(settings.resolve(settings.changelog_path)))
    picked = select(entries, since.strip() or None, limit)
    return {
        # latest 는 **전체의** 최신 날짜다 — 화면이 이걸 '봤다'고 저장한다.
        "latest": entries[0]["date"] if entries else "",
        "today": _dt.date.today().isoformat(),
        "entries": picked,
    }
