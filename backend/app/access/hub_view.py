# 개인 Claude 보기(전체 · 묶음 · 가벼운)의 저장 꼴 — 포털 사람 설정과 게이트웨이 연결 머리 X-HWAX-View 가 같은 글을 쓴다(docs/request-1029 E-4)
"""보기 글의 꼴은 하나다 — `full` · `light` · `bundle:<영역>,<영역>…`(영역은 게이트웨이 tool_areas.json 의 키).

포털은 이 글을 `users.hub_view` 에 두고 `/internal/access/entitlements` 의 `view` 로 내린다. 게이트웨이는 같은 글을 PAT 분기에서 읽어
tools/list 에만 얹는다(HWAXMcpGateway `_parse_view` — 그쪽 시험이 이 파일을 읽어 맞댄다). 그래서 이 파일은 표준 라이브러리만 쓴다.
"""
from __future__ import annotations

import re

MODES = ("full", "bundle", "light")
AREA_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
AREAS_MAX = 32
# 연결 머리 — 값이 보기 글이면 그 연결의 보기다. 값 `portal` 은 보기 글이 아니라 '포털에서 고른 보기를 따른다' 는 표지다(저장하지 않는다). 게이트웨이는
# 이 표지로 청한 연결에만 포털 보기를 얹는다 — 포털 등록 배치 · 명령(frontend/src/lib/setupBat.ts)이 Claude Code · Desktop 에 단다. 머리가 없는 연결
# (내 토큰으로 서버에서 도는 앱 · 스크립트 · 그 밖의 클라이언트)은 늘 전체다(docs/request-1029 context-notes C-41).
HEADER_NAME = "X-HWAX-View"
HEADER_PORTAL = "portal"


def parse_view(raw) -> tuple[str, list[str]] | None:
    """보기 글 → (보기, 영역들). 틀린 꼴이면 None — 게이트웨이와 같은 규칙이다(대소문자 · 앞뒤 공백 무시, 영역은 겹치면 하나로)."""
    s = str(raw or "").strip().lower()
    if s in ("full", "light"):
        return s, []
    if s.startswith("bundle:"):
        areas = list(dict.fromkeys(a.strip() for a in s[len("bundle:"):].split(",") if a.strip()))
        if areas and len(areas) <= AREAS_MAX and all(AREA_RE.fullmatch(a) for a in areas):
            return "bundle", areas
    return None


def format_view(mode: str, areas: list[str] | tuple[str, ...] = ()) -> str:
    """(보기, 영역들) → 보기 글. 묶음이 아니면 영역은 버린다."""
    return "bundle:" + ",".join(dict.fromkeys(areas)) if mode == "bundle" else mode
