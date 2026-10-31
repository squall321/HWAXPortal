# 환원 도구 공통 계약(절차 PLAN §10-7 규약) — 씨앗이 해석에 통째로 넘기는 환원 값이 `for_<해석>_analysis` 에서 오는가
#
# 환원 도구(형상 · 보드 응답 → 해석 입력의 요약)는 해석이 그대로 먹는 값을 `for_<해석>_analysis` 아래에 모은다 — StepForge
# `bend_profile` · `stackup_profile`, ThermalShockMCP `sed_sample_from_odb`(대조표 docs/procedures/reduction-contract.md · W-103).
# 같은 응답의 `primary` · `basis` 도 숫자나 객체라, 씨앗이 그 칸을 해석에 넘기면 실행은 오류 없이 **다른 답**을 낸다.
# 그래서 정적으로 본다. 보고서 근거로만 남기는 save(`bend_basis` · `needs_human`)와 글 안에 섞인 자리(보고서 제목)는 묻지 않는다.
import re
from pathlib import Path

import yaml

from app.procedures import template

ROOT = Path(__file__).resolve().parents[2]
SEEDS = sorted((ROOT / "docs" / "procedures" / "fixtures").glob("*.yaml"))
# §10-7 규약을 지키는 환원 도구 — 새로 생기면 여기와 대조표에 더한다
REDUCERS = {"bend_profile", "stackup_profile", "sed_sample_from_odb"}
_FOR = re.compile(r"(?:^|\.)for_[a-z0-9_]+_analysis(?:$|[.\[])")


def _whole_refs(value) -> list[str]:
    """인자 트리에서 값 전체가 `"{{var}}"` 인 자리의 변수 — 형 그대로 넘는 값이다(template.substitute)."""
    out: list[str] = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        else:
            name = template.whole_ref(v)
            if name:
                out.append(name.split(".")[0])

    walk(value)
    return out


def contract_problems(spec: dict) -> list[str]:
    """씨앗 하나(파싱한 YAML)의 위반 — 빈 목록이면 통과."""
    bad: list[str] = []
    origin: dict[str, tuple[int, str, str]] = {}      # 환원 단계가 저장한 변수 → (단계, 도구, 경로)
    for ix, st in enumerate(spec.get("steps") or []):
        for name in _whole_refs(st.get("args") or {}):
            if name in origin and not _FOR.search(origin[name][2]):
                at, tool, path = origin[name]
                bad.append(f"단계 {ix}({st.get('tool')})가 {name} 을 통째로 받는데 그 값은 단계 {at}({tool})의 "
                           f"{path!r} 다 — for_*_analysis 밖")
        save = st.get("save") or {}
        if st.get("tool") in REDUCERS:
            if not any(_FOR.search(str(p)) for p in save.values()):
                bad.append(f"단계 {ix}({st['tool']})의 save 가 for_*_analysis 를 하나도 지나지 않는다: {save}")
            for k, p in save.items():
                origin[k] = (ix, st["tool"], str(p))
        else:
            for k in save:
                origin.pop(k, None)                     # 뒤 단계가 같은 이름으로 다시 저장하면 그 값이다
    return bad


def test_씨앗이_해석에_넘기는_환원_값은_for_analysis_에서_온다():
    seen, bad = [], []
    for f in SEEDS:
        spec = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        seen += [f"{f.stem}:{st.get('tool')}" for st in spec.get("steps") or [] if st.get("tool") in REDUCERS]
        bad += [f"{f.name}: {p}" for p in contract_problems(spec)]
    # 헛돌지 않게 — 지금은 R1(bend_profile)과 R3(sed_sample_from_odb) 둘이 걸린다
    assert len(seen) >= 2, f"환원 도구를 부르는 씨앗이 {seen} 뿐이다 — 이 시험이 볼 것이 없다"
    assert not bad, "환원 도구의 해석 칸 밖에서 값을 꺼내 해석에 넘긴다:\n" + "\n".join(bad)


def test_판정기는_대표값을_해석에_넘기는_씨앗을_잡는다():
    """판정기 자신 — 대표값(`primary`)을 통째로 넘기거나 환원 단계가 해석 칸을 하나도 안 거치면 잡고, 글 안의 자리는 묻지 않는다."""
    wrong = {"steps": [
        {"tool": "bend_profile", "save": {"r": "parts[0].primary.radius_mid"}},
        {"tool": "solve_prescribed_curvature", "args": {"bend_radius": "{{r}}"}},
        {"tool": "create_report_draft", "args": {"title": "R {{r}}"}},
    ]}
    got = contract_problems(wrong)
    assert len(got) == 2, got
    assert "하나도 지나지 않는다" in got[0] and "for_*_analysis 밖" in got[1]

    right = {"steps": [
        {"tool": "sed_sample_from_odb", "save": {"sample": "data.for_sed_analysis", "needs_human": "data.needs_human"}},
        {"tool": "predict_sed", "args": {"sample": "{{sample}}"}},
    ]}
    assert contract_problems(right) == []
