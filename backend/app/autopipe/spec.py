# 자동 파이프라인 규칙 스펙 검증 — 범위 · 트리거 · 단계 연결도(순환 · 참조) · 한도 · stage 를 저장 전에 본다(portal-api §2)
"""규칙 스펙은 JSON 이다. 저장 · 새 판 · `/validate` 가 모두 `validate` 하나를 지난다.

- 모르는 칸은 오류다 — 오타(`neds`)가 조용히 빈 의존이 되지 않게.
- `kind: deliberation` 은 M5 다 — v1 은 「아직 없음」으로 거절한다.
- analysis 가 analysis 를 `needs` 로 가리킬 수 있다(계약 v1.1 upstream — 예 ODB 추출 → 열충격). report 는 analysis 만 가리킨다. 순환은 막는다.
- 범위는 「모든 과제 + 제외 목록」 하나다(AP-D4) — `all_projects` 는 참이어야 한다.
"""
from __future__ import annotations

import copy
import re

STAGES = ("shadow", "approve", "auto")
REPORTS = ("per_analysis", "summary", "revdiff")
STEP_MAX = 12
QUIET_MIN, QUIET_MAX = 60, 86400
EXCLUDE_MAX = 1000
READY_MAX = 10

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
# 게이트웨이 백엔드 키(앱 id) — heax-step_forge · signalforge · heax-thermal_shock_mcp 같은 꼴
APP_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
# ready_when — "<앱 id>.<키>"(계약 v1.1 §1 — 예 step_forge.parsed). 앱 id 에 점이 없으니 마지막 점에서 가른다
READY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}\.[a-z0-9_]{1,40}$")

_TOP = {"title", "stage", "scope", "trigger", "steps", "limits"}
_SCOPE = {"all_projects", "exclude"}
_TRIGGER = {"ready_when", "quiet_s"}
_LIMITS = {"max_concurrent", "per_project_per_day", "night_only"}
_STEP = {"analysis": {"id", "kind", "app", "profile", "needs"},
         "report": {"id", "kind", "report", "needs"}}


class SpecError(ValueError):
    """저장할 수 없는 스펙 — errors 는 사람이 읽을 까닭들."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _unknown(where: str, got: dict, allowed: set, errors: list[str]) -> None:
    extra = sorted(str(k) for k in got if k not in allowed)
    if extra:
        errors.append(f"{where}: 모르는 칸 {', '.join(extra)}")


def ready_split(entry: str) -> tuple[str, str]:
    """ready_when 한 줄 → (앱 id, 키)."""
    app, _, key = entry.rpartition(".")
    return app, key


def _cycle(edges: dict[str, list[str]]) -> list[str] | None:
    """순환이 있으면 그 고리(단계 id 차례), 없으면 None."""
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(n: str) -> list[str] | None:
        state[n] = 1
        path.append(n)
        for m in edges.get(n, []):
            if state.get(m) == 1:
                return path[path.index(m):] + [m]
            if state.get(m) is None:
                got = visit(m)
                if got:
                    return got
        state[n] = 2
        path.pop()
        return None

    for n in edges:
        if state.get(n) is None:
            got = visit(n)
            if got:
                return got
    return None


def order(steps: list[dict]) -> list[str]:
    """단계 id 를 의존 차례로(needs 가 먼저) — 같은 깊이는 스펙 차례. 검증을 지난 스펙에만 쓴다."""
    done: list[str] = []
    left = [s["id"] for s in steps]
    needs = {s["id"]: list(s.get("needs") or []) for s in steps}
    while left:
        for sid in left:
            if all(n in done for n in needs[sid]):
                done.append(sid)
                left.remove(sid)
                break
        else:                       # 순환 — 검증이 막으니 오지 않는다. 남은 것은 스펙 차례로
            done += left
            break
    return done


def validate(raw) -> tuple[list[str], list[str], dict | None]:
    """(errors, warnings, 정규화한 스펙). 오류가 있으면 스펙은 None 이다."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(raw, dict):
        return ["스펙은 JSON 객체여야 한다"], [], None
    spec = copy.deepcopy(raw)
    _unknown("스펙", spec, _TOP, errors)

    title = spec.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        errors.append("title 은 1 ~ 200자 글이어야 한다")
    else:
        spec["title"] = title.strip()
    if spec.get("stage") not in STAGES:
        errors.append(f"stage 는 {' · '.join(STAGES)} 가운데 하나다(AP-D2)")

    scope = spec.get("scope", {"all_projects": True})
    if not isinstance(scope, dict):
        errors.append("scope 는 객체다")
        scope = {}
    _unknown("scope", scope, _SCOPE, errors)
    if scope.get("all_projects", True) is not True:
        errors.append("scope.all_projects 는 참이어야 한다 — v1 의 범위는 「모든 과제 + 제외 목록」 하나다(AP-D4)")
    exclude = scope.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(x, str) and 0 < len(x) <= 200 for x in exclude) \
            or len(exclude) > EXCLUDE_MAX:
        errors.append(f"scope.exclude 는 과제 key 글(1 ~ 200자)의 목록이다(최대 {EXCLUDE_MAX})")
        exclude = []
    spec["scope"] = {"all_projects": True, "exclude": sorted(set(exclude))}

    trig = spec.get("trigger", {})
    if not isinstance(trig, dict):
        errors.append("trigger 는 객체다")
        trig = {}
    _unknown("trigger", trig, _TRIGGER, errors)
    ready = trig.get("ready_when", [])
    if not isinstance(ready, list) or len(ready) > READY_MAX or not all(isinstance(r, str) and READY_RE.fullmatch(r) for r in ready):
        errors.append(f"trigger.ready_when 은 '<앱 id>.<키>' 글의 목록이다(최대 {READY_MAX} — 예 step_forge.parsed)")
        ready = []
    quiet = trig.get("quiet_s", 1800)
    if not _int(quiet) or not QUIET_MIN <= quiet <= QUIET_MAX:
        errors.append(f"trigger.quiet_s 는 {QUIET_MIN} ~ {QUIET_MAX} 의 정수(초)다")
    spec["trigger"] = {"ready_when": list(ready), "quiet_s": quiet}

    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps 는 한 개 이상의 목록이다")
        steps = []
    if len(steps) > STEP_MAX:
        errors.append(f"단계는 {STEP_MAX}개까지다")
    seen: dict[str, str] = {}
    norm: list[dict] = []
    for i, s in enumerate(steps):
        where = f"steps[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{where}: 객체여야 한다")
            continue
        sid, kind = s.get("id"), s.get("kind")
        if not isinstance(sid, str) or not ID_RE.fullmatch(sid):
            errors.append(f"{where}: id 는 {ID_RE.pattern} 꼴이다")
            continue
        where = f"단계 {sid}"
        if sid in seen:
            errors.append(f"{where}: id 가 겹친다")
            continue
        if kind == "deliberation":
            errors.append(f"{where}: 심의 단계(deliberation)는 아직 없다 — M5 에 더한다")
            continue
        if kind not in _STEP:
            errors.append(f"{where}: kind 는 analysis · report 가운데 하나다")
            continue
        seen[sid] = kind
        _unknown(where, s, _STEP[kind], errors)
        needs = s.get("needs", [])
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs) or len(set(needs)) != len(needs):
            errors.append(f"{where}: needs 는 겹치지 않는 단계 id 목록이다")
            needs = []
        row = {"id": sid, "kind": kind, "needs": list(needs)}
        if kind == "analysis":
            app, prof = s.get("app"), s.get("profile")
            if not isinstance(app, str) or not APP_RE.fullmatch(app):
                errors.append(f"{where}: app 은 게이트웨이 백엔드 키(앱 id)다 — {APP_RE.pattern}")
            if not isinstance(prof, str) or not PROFILE_RE.fullmatch(prof):
                errors.append(f"{where}: profile 은 앱이 auto_profiles 로 내보인 id 다 — {PROFILE_RE.pattern}")
            row.update(app=app, profile=prof)
        else:
            rep = s.get("report")
            if rep not in REPORTS:
                errors.append(f"{where}: report 는 {' · '.join(REPORTS)} 가운데 하나다")
            if not needs:
                errors.append(f"{where}: 보고서 단계는 needs 에 해석 단계를 하나 이상 적는다")
            row["report"] = rep
        norm.append(row)

    for row in norm:
        for n in row["needs"]:
            if n == row["id"]:
                errors.append(f"단계 {row['id']}: 자기 자신을 needs 로 가리킨다")
            elif n not in seen:
                errors.append(f"단계 {row['id']}: needs 의 {n} 이 없는 단계다")
            elif seen[n] != "analysis":
                errors.append(f"단계 {row['id']}: needs 는 해석(analysis) 단계만 가리킨다 — {n} 은 {seen[n]}")
    loop = _cycle({r["id"]: [n for n in r["needs"] if seen.get(n) == "analysis"] for r in norm})
    if loop:
        errors.append(f"단계 연결에 순환이 있다 — {' → '.join(loop)}")
    if norm and not any(r["kind"] == "analysis" for r in norm):
        errors.append("해석(analysis) 단계가 하나도 없다")
    spec["steps"] = norm

    lim = spec.get("limits", {})
    if not isinstance(lim, dict):
        errors.append("limits 는 객체다")
        lim = {}
    _unknown("limits", lim, _LIMITS, errors)
    out_lim: dict = {}
    for k, hi in (("max_concurrent", 50), ("per_project_per_day", 100)):
        if k in lim:
            if not _int(lim[k]) or not 1 <= lim[k] <= hi:
                errors.append(f"limits.{k} 는 1 ~ {hi} 의 정수다")
            else:
                out_lim[k] = lim[k]
    night = lim.get("night_only", [])
    if not isinstance(night, list) or not all(isinstance(n, str) for n in night):
        errors.append("limits.night_only 는 해석 단계 id 목록이다")
        night = []
    for n in night:
        if seen.get(n) != "analysis":
            errors.append(f"limits.night_only 의 {n} 은 해석 단계가 아니다")
    out_lim["night_only"] = sorted(set(night))
    spec["limits"] = out_lim

    if not errors:
        if not any(r["kind"] == "report" for r in norm):
            warnings.append("보고서 단계가 없다 — 결과는 현황판에서만 보인다")
        if spec["stage"] == "auto" and "max_concurrent" not in out_lim and "per_project_per_day" not in out_lim:
            warnings.append("auto 인데 규칙 한도(max_concurrent · per_project_per_day)가 없다 — 박스 전체 상한만 걸린다")
        if not ready:
            warnings.append("trigger.ready_when 이 비었다 — 입력이 바뀌고 조용해지면 곧바로 돈다")
    return errors, warnings, (spec if not errors else None)


def parse(raw) -> dict:
    """저장용 — 오류면 SpecError."""
    errors, _w, spec = validate(raw)
    if errors:
        raise SpecError(errors)
    return spec
