# HE팀 운영자 정의를 읽는다 — git 기본 he-team.json + cae00 박스 덧씌우기 he-team.local.json(gitignore)을 합친다
"""HE팀 운영자 정의 — 기본 + 박스 덧씌우기(docs/he-team-overlay).

표준 라이브러리만 쓴다 — 동기화 스크립트(시스템 python3)와 포털 백엔드(접근 검사)가 같이 들인다. 에이전트 서버(확인 관문)는 같은 셈을
따로 갖고, 그쪽 시험이 이 모듈과 같은 합친 정의 · 지문이 나오는지 견준다(HO-4).

덧씌우기 꼴(PLAN 2절) —
    {"_doc": "...", "groups": {<merge patch>}, "personas": {"<운영자 키>": <merge patch> | null}}
있는 키는 그 운영자에 JSON merge patch(RFC 7386 — 목록은 통째로 바뀐다), 없는 키는 새 운영자, null 은 이 박스에서 뺀다. 꼴이 틀리면
덧씌우기를 통째로 버리고 기본 정의로 돈다(HO-3) — 까닭은 정보의 error 에 남는다.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

BASE_PATH = Path(__file__).resolve().with_name("he-team.json")
# 시험은 HE_TEAM_LOCAL_PATH 로 이 박스의 덧씌우기를 비켜 간다(backend/tests/conftest.py).
LOCAL_PATH = Path(os.environ.get("HE_TEAM_LOCAL_PATH") or BASE_PATH.with_name("he-team.local.json"))
_TOP = frozenset({"_doc", "groups", "personas"})


def merge_patch(target, patch):
    """JSON merge patch(RFC 7386) — 객체는 재귀로 합치고, 그 밖은 바꾸며, null 은 그 칸을 지운다(목록은 통째로 바뀐다)."""
    if not isinstance(patch, dict):
        return patch
    out = dict(target) if isinstance(target, dict) else {}
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = merge_patch(out.get(k), v)
    return out


def fingerprint(spec) -> str:
    """정의의 지문 — 키 차례 JSON 의 sha256 앞 12자(맨 위 `_doc` 은 뺀다). 에이전트 서버가 같은 셈을 낸다."""
    obj = {k: v for k, v in spec.items() if k != "_doc"} if isinstance(spec, dict) else spec
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]


def apply_overlay(spec: dict, overlay) -> tuple[dict, dict]:
    """기본 정의 + 덧씌우기 → (합친 정의, {changed, added, removed, missing}). 꼴이 틀리면 ValueError — 부르는 쪽이 통째로 버린다.

    missing 은 null 로 뺀다고 적었는데 기본에 없는 키다(오타일 수 있어 알린다). 합친 운영자 차례는 기본 차례 그대로이고 새 운영자는 덧씌우기 차례로 뒤에 붙는다."""
    if not isinstance(overlay, dict):
        raise ValueError(f"덧씌우기는 객체여야 한다({type(overlay).__name__})")
    extra = sorted(set(overlay) - _TOP)
    if extra:
        raise ValueError(f"모르는 칸 {', '.join(extra)} — groups · personas · _doc 만 받는다")
    groups = overlay.get("groups")
    if groups is not None and not isinstance(groups, dict):
        raise ValueError("groups 는 묶음 → 라벨의 객체여야 한다")
    pats = overlay.get("personas")
    if pats is None:
        pats = {}
    if not isinstance(pats, dict):
        raise ValueError("personas 는 운영자 키로 묶은 객체여야 한다(정본처럼 목록으로 적지 않는다)")
    for k, v in pats.items():
        if not k.strip():
            raise ValueError("운영자 키가 비었다")
        if v is not None and not isinstance(v, dict):
            raise ValueError(f"{k} — 운영자 덧씌우기는 객체이거나 null 이어야 한다({type(v).__name__})")
        if isinstance(v, dict) and v.get("key") not in (None, k):
            raise ValueError(f"{k} — 키는 바꾸지 않는다(바꾸려면 null 로 빼고 새 키로 더한다)")
    base = list(spec.get("personas") or [])
    have = {p.get("key") for p in base}
    merged, changed, removed = [], [], []
    for p in base:
        k = p.get("key")
        if k not in pats:
            merged.append(p)
        elif pats[k] is None:
            removed.append(k)
        else:
            merged.append({**merge_patch(p, pats[k]), "key": k})
            changed.append(k)
    added = [k for k, v in pats.items() if k not in have and v is not None]
    merged += [{**merge_patch({}, pats[k]), "key": k} for k in added]
    missing = [k for k, v in pats.items() if k not in have and v is None]
    out = {**spec, "personas": merged}
    if groups:
        out["groups"] = merge_patch(spec.get("groups") or {}, groups)
    return out, {"changed": changed, "added": added, "removed": removed, "missing": missing}


def load(base_path=None, local_path=None) -> tuple[dict, dict]:
    """→ (정의, 정보). 정보 — overlay(none · ok · error) · error · changed · added · removed · missing · fingerprint · path.
    기본 정의를 못 읽으면 예외를 그대로 낸다(부르는 쪽이 지금처럼 다룬다). 덧씌우기는 없으면 none, 못 읽거나 꼴이 틀리면 error 로 버린다."""
    base_path = Path(base_path or BASE_PATH)
    local_path = Path(local_path or LOCAL_PATH)
    spec = json.loads(base_path.read_text(encoding="utf-8"))
    info = {"overlay": "none", "error": None, "changed": [], "added": [], "removed": [], "missing": [], "path": str(local_path)}
    try:
        raw = local_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return spec, {**info, "fingerprint": fingerprint(spec)}
    except (OSError, UnicodeDecodeError) as exc:
        return spec, {**info, "overlay": "error", "error": f"못 읽었다({type(exc).__name__})", "fingerprint": fingerprint(spec)}
    try:
        merged, diff = apply_overlay(spec, json.loads(raw))
    except ValueError as exc:            # json.JSONDecodeError 도 ValueError 다
        return spec, {**info, "overlay": "error", "error": str(exc)[:300], "fingerprint": fingerprint(spec)}
    return merged, {**info, **diff, "overlay": "ok", "fingerprint": fingerprint(merged)}


def stamp(base_path=None, local_path=None) -> tuple:
    """다시 읽을 열쇠 — 두 파일의 (바뀐 시각 ns, 크기). 없는 파일은 None."""
    out = []
    for p in (Path(base_path or BASE_PATH), Path(local_path or LOCAL_PATH)):
        try:
            st = p.stat()
            out.append((st.st_mtime_ns, st.st_size))
        except OSError:
            out.append(None)
    return tuple(out)


def describe(info: dict) -> str:
    """미리보기 · update-all 에 찍는 한 줄 — '  · 덧씌우기 …' · '  ✗ 덧씌우기 …' 꼴(update-all §6 이 이 머리로 가른다)."""
    name = Path(info.get("path") or LOCAL_PATH).name
    if info.get("overlay") == "none":
        return f"  · 덧씌우기 없음 — 기본 정의(he-team.json)만 쓴다({name} 이 없다) · 지문 {info.get('fingerprint')}"
    if info.get("overlay") == "error":
        return f"  ✗ 덧씌우기 {name} 을 버렸다 — {info.get('error')} · 기본 정의로 돈다(확인 관문도 기본 목록만) · 지문 {info.get('fingerprint')}"
    parts = [f"{label} {len(info[k])}({', '.join(info[k][:8])}{' …' if len(info[k]) > 8 else ''})"
             for k, label in (("changed", "고침"), ("added", "더함"), ("removed", "뺌")) if info.get(k)]
    if info.get("missing"):
        parts.append(f"뺀다고 적었는데 기본에 없는 키 {', '.join(info['missing'][:8])}")
    return f"  · 덧씌우기 {name} — {' · '.join(parts) or '바뀐 운영자 없음'} · 지문 {info.get('fingerprint')}"
