# 손으로 적은 목록이 **카탈로그와 어긋나지 않는지** (PLAN §5-4)
#
# `models.py` 의 MUST_GATE·DRY_RUN_TOOLS·WARN_EXACT 는 465종 전수에서 뽑은 것이고
# 주석이 "손으로 고치지 마라. 게이트웨이가 바뀌면 다시 뽑는다" 라고만 적어 뒀다 —
# **확인하는 코드가 없었다.** 그러면 —
#   · 새 파괴 도구가 게이트 없이 저장되고
#   · dry_run 을 안 받는 도구에 dry_run 을 적어도 백엔드가 조용히 버리고 **실제로 실행된다**
#
# 이 파일이 그 목록을 **기록된 인구조사**(catalog-census.json)에 대조한다. 살아 있는
# 게이트웨이는 안 친다 — 테스트가 공유 서비스를 치면 안 된다(W-54).
# 인구조사 갱신은 사람이 한다: `python3 backend/scripts/refresh-census.py`
import json
from pathlib import Path

import pytest

from app.procedures.models import (
    CACHE_PREFIX,
    DRY_RUN_TOOLS,
    GW_DENY_PREFIX,
    GW_DENY_SUFFIX,
    MUST_GATE,
    WARN_EXACT,
)

ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / "docs" / "procedures" / "fixtures" / "catalog-census.json"


@pytest.fixture(scope="module")
def census() -> dict:
    assert CENSUS.is_file(), "인구조사 고정물이 없다 — refresh-census.py 를 돌려라"
    return json.loads(CENSUS.read_text(encoding="utf-8"))


def test_인구조사가_실물_규모다(census):
    """빈 파일을 훑고 통과하는 사고를 막는다."""
    assert census["gateway_tools"] > 400, census["gateway_tools"]
    assert len(census["tools"]) == census["gateway_tools"]


# ── dry_run — 여기 없는 도구에 적으면 **조용히 버려지고 실제로 실행된다** ──
def test_DRY_RUN_TOOLS_가_카탈로그와_정확히_같다(census):
    real = {t["name"] for t in census["tools"] if t["dry_run"]}
    assert DRY_RUN_TOOLS == real, (
        f"어긋났다 — 목록에만 있는 것: {sorted(DRY_RUN_TOOLS - real)} · "
        f"카탈로그에만 있는 것: {sorted(real - DRY_RUN_TOOLS)}. "
        "refresh-census.py 를 돌리고 models.py 를 사람이 다시 본다")


# ── 그 도구가 아직 있나 ──────────────────────────────────────────────────
def test_게이트_필수_도구가_아직_카탈로그에_있다(census):
    """사라진 도구가 목록에 남아 있으면 그 줄은 **아무 일도 안 한다** — 지키는 척만 한다."""
    have = {t["name"] for t in census["tools"]}
    assert MUST_GATE <= have, f"사라진 것: {sorted(MUST_GATE - have)}"
    assert WARN_EXACT <= have, f"사라진 것: {sorted(WARN_EXACT - have)}"


def test_되돌리기_어려운_도구가_새로_생기지_않았나(census):
    """⚠ 이 테스트는 **사람을 부른다.** 게이트웨이 거절 접두사에 걸리는 도구는 백스톱이
    막지만, `trash_report`·`job_stop` 처럼 거기 안 걸리는 파괴 도구는 MUST_GATE 가
    유일한 방어다. 새 이름이 보이면 사람이 판단해 목록에 넣는다."""
    have = {t["name"] for t in census["tools"]}
    backstopped = {n for n in have
                   if n.startswith(GW_DENY_PREFIX) or n.endswith(GW_DENY_SUFFIX)}
    # 이름만으로 "되돌리기 어렵다" 를 판정할 수 없다(§9-7) — 그래서 **알려진 것만** 센다.
    known = MUST_GATE | WARN_EXACT | backstopped
    suspicious = {n for n in have - known
                  if any(n.startswith(p) for p in ("publish_", "trash_", "restore_", "unpublish_"))}
    assert not suspicious, (
        f"되돌리기 어려워 보이는 새 도구: {sorted(suspicious)} — "
        "사람이 보고 MUST_GATE 에 넣을지 정한다")


# ── 다른 리포에서 베낀 상수 — 그쪽이 바뀌면 어긋난다 ─────────────────────
def _gateway_source() -> str | None:
    for c in (ROOT.parent / "HWAXMcpGateway", Path.home() / "Projects" / "HWAXMcpGateway",
              Path.home() / "claude" / "HWAXMcpGateway"):
        p = c / "gateway.py"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None


def test_게이트웨이에서_베낀_상수가_아직_같다():
    """`CACHE_PREFIX`·`GW_DENY_*` 는 게이트웨이 소스의 **사본**이다. 그쪽이 바뀌면
    우리 판정이 조용히 틀린다 — 캐시 접두사가 늘면 상태 조회 단계가 낡은 값을 받는다."""
    src = _gateway_source()
    if src is None:
        pytest.skip("HWAXMcpGateway 리포가 이 박스에 없다")
    for name, ours in (("_CACHEABLE", CACHE_PREFIX),
                       ("_INVOKE_DENY_PREFIX", GW_DENY_PREFIX),
                       ("_INVOKE_DENY_SUFFIX", GW_DENY_SUFFIX)):
        i = src.find(f"{name} = ")
        if i < 0:
            pytest.skip(f"게이트웨이에 {name} 이 없다 — 이름이 바뀌었나")
        blob = src[i:i + 900]
        missing = [x for x in ours if f'"{x}"' not in blob]
        assert not missing, (
            f"{name} 에서 사라졌다: {missing} — 게이트웨이가 바뀌었다. "
            "models.py 의 사본을 맞춰라")


def test_게이트웨이_호출_상한과의_관계가_아직_성립한다():
    """우리 단계 상한은 게이트웨이 상한(`CALL_TIMEOUT_S`)과 **관계로** 정해져 있다 —
    그보다 짧게 둬야 우리가 먼저 끊고 기록을 남긴다. 그쪽이 바뀌면 그 관계가 조용히
    뒤집혀, 게이트웨이가 먼저 끊고 우리에겐 `unknown` 만 남는다."""
    from app.procedures.runner import EXPECT_TIMEOUT, WARMUP_TIMEOUT

    src = _gateway_source()
    if src is None:
        pytest.skip("HWAXMcpGateway 리포가 이 박스에 없다")
    import re as _re

    m = _re.search(r"CALL_TIMEOUT_S\s*=\s*(?:float\()?[^\n]*?(\d+)", src)
    assert m, "게이트웨이에서 CALL_TIMEOUT_S 를 못 읽었다 — 이름이 바뀌었나"
    gw = float(m.group(1))
    assert max(EXPECT_TIMEOUT.values()) < gw, (
        f"단계 상한 {max(EXPECT_TIMEOUT.values())} 이 게이트웨이 {gw} 보다 짧지 않다")
    assert WARMUP_TIMEOUT > gw, (
        f"워밍업 {WARMUP_TIMEOUT} 이 게이트웨이 {gw} 를 안 넘는다 — 콜드스타트를 못 흡수한다")
