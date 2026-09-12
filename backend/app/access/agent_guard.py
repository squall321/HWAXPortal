# 챗·심의 요청의 권한 검사 — 챗 필드별 기능 권한, HE팀 운영자의 플랫폼 권한, 전문가 목록 거르기
"""Agent-route guards (docs/access-control).

메뉴를 숨겨도 요청은 직접 보낼 수 있다 — 포털이 챗의 명시 모드(thinking·pinned_agent)를 권한과
대조한다. 심의 트리거(/심의 등)는 에이전트서버가 쥐고 있어 entitlements 를 넘겨 그쪽이 막고,
도구는 게이트웨이가 거른다(같은 판정을 두 곳에 두지 않는다).
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


def check_chat(policy: Policy, principal: Principal, *, thinking: bool,
               pinned_agent: str | None, pinned_agents: list[str] | None = None) -> None:
    """챗의 명시 모드(Thinking·전문가 지정)만 본다. 없으면 403.

    나머지는 여기서 보지 않는다 — 프론트는 delib_opts 를 **늘** 싣고(search_sources 를 담아서) 일반
    챗에서도 보낸다. 그걸 심의 권한으로 막으면 모든 챗이 403 이 된다. 심의 트리거는 에이전트서버가,
    도구(웹 검색·지정 앱)는 게이트웨이가 권한으로 거른다 — 같은 판정을 세 곳에 두지 않는다."""
    if thinking:
        ensure(principal, "feat:thinking")
    # 여러 명을 세우면 **각자** 검사한다 — 한 명만 봐도 되는 것처럼 두면 못 쓰는 운영자를
    # 두 번째 자리에 끼워 그 앱 도구를 얻을 수 있다(권한 우회).
    keys = [k for k in (list(pinned_agents or []) or ([pinned_agent] if pinned_agent else []))
            if isinstance(k, str) and k.strip()]
    if keys:
        ensure(principal, "feat:expert-chat")
        for key in keys:
            need = policy.keys_for_gateway(he_apps(key))
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
