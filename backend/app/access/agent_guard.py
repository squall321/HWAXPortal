# 챗·심의 요청의 권한 검사 — 챗 필드별 기능 권한, HE팀 운영자의 플랫폼 권한, 전문가 목록 거르기
"""Agent-route guards (docs/access-control).

메뉴를 숨겨도 요청은 직접 보낼 수 있다 — 포털이 챗 요청의 필드(thinking·pinned_agent·delib_opts·
search_sources·pinned_apps)를 권한과 대조한다. 심의 트리거(/심의 등)는 에이전트서버가 쥐고 있어
entitlements 를 넘겨 그쪽이 한 번 더 막는다(트리거 목록을 두 곳에 두지 않는다).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from app.access.policy import Policy
from app.auth.provider import Principal
from app.deps import ensure

# HE팀 정본 — 페르소나 키 → 모는 게이트웨이 앱. 파일 위치는 리포 루트 기준(박스마다 경로가 다르다).
_HE_SPEC = Path(__file__).resolve().parents[3] / "infra" / "personas" / "he-team.json"
_he_lock = threading.Lock()
_he_cache: dict = {"mtime": None, "apps": {}}


def he_apps(key: str) -> list[str]:
    """HE팀 페르소나가 모는 게이트웨이 앱. 정본에 없는 키는 빈 목록(일반 전문가)."""
    if not key.startswith("he-"):
        return []
    try:
        mtime = _HE_SPEC.stat().st_mtime
    except OSError:
        return []
    with _he_lock:
        if _he_cache["mtime"] != mtime:
            spec = json.loads(_HE_SPEC.read_text(encoding="utf-8"))
            _he_cache["apps"] = {p["key"]: list(p.get("apps") or [])
                                 for p in spec.get("personas") or []}
            _he_cache["mtime"] = mtime
        return list(_he_cache["apps"].get(key, []))


def persona_allowed(policy: Policy, key: str, groups: list[str]) -> bool:
    """이 전문가를 쓸 수 있나 — HE팀 운영자는 자기 앱의 플랫폼 허가가 있어야 한다."""
    need = policy.keys_for_gateway(he_apps(key))
    return not need or any(k in groups for k in need)


def check_chat(policy: Policy, principal: Principal, *, thinking: bool, pinned_agent: str | None,
               delib_opts: object | None, search_sources: list[str] | None,
               pinned_apps: list[str] | None) -> None:
    """챗 요청 필드별 권한. 없으면 403 — 조용히 떼고 진행하면 사용자는 기능이 고장 난 줄 안다."""
    if thinking:
        ensure(principal, "feat:thinking")
    if delib_opts is not None:
        ensure(principal, "feat:deliberation")
    if pinned_agent:
        ensure(principal, "feat:expert-chat")
        need = policy.keys_for_gateway(he_apps(pinned_agent))
        if need:
            ensure(principal, *need, any_of=True)
    if search_sources:                     # 빈 리스트는 '전부 끔'이라 권한이 필요 없다
        need = policy.keys_for_gateway(["heax-web_research_mcp"])
        if need:
            ensure(principal, *need, any_of=True)
    for app in pinned_apps or []:
        need = policy.keys_for_gateway([app])
        if need:
            ensure(principal, *need, any_of=True)


def filter_experts(resp: dict, policy: Policy, groups: list[str]) -> dict:
    """전문가 목록(추천·후보·풀)에서 이 사람이 못 쓰는 HE팀 운영자를 뺀다 — 골라도 403 인 사람을
    조직도에 보이면 고장으로 읽힌다."""
    out = dict(resp)
    for field in ("recommended", "candidates", "pool"):
        rows = resp.get(field)
        if isinstance(rows, list):
            out[field] = [r for r in rows if not isinstance(r, dict)
                          or persona_allowed(policy, str(r.get("key") or ""), groups)]
    return out
