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
    prefixes = ("publish_", "trash_", "restore_", "unpublish_")
    prefixed = {n for n in have if any(n.startswith(p) for p in prefixes)}
    # ⚠ **먼저 접두사가 살아 있는지 본다.** 오타 하나로 `prefixed` 가 0건이 되면
    # `suspicious` 도 0건이 되어 **조용히 통과**한다 — 카나리가 죽은 줄 아무도 모른다.
    assert prefixed, f"접두사 {prefixes} 에 걸리는 도구가 하나도 없다 — 목록이 죽었다"
    suspicious = prefixed - known
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
    # ⚠ **이름이 사라진 것도 어긋남이다.** 예전엔 여기서 `pytest.skip` 을 했는데,
    # 그건 이 검사가 쫓는 바로 그 사건이 났을 때 **조용히 통과**한다는 뜻이다. 게다가
    # skip 이 반복문 첫 바퀴에서 터지면 나머지 둘은 아예 안 본다. 모아서 끝에 따진다.
    renamed, missing_all = [], []
    for name, ours in (("_CACHEABLE", CACHE_PREFIX),
                       ("_INVOKE_DENY_PREFIX", GW_DENY_PREFIX),
                       ("_INVOKE_DENY_SUFFIX", GW_DENY_SUFFIX)):
        i = src.find(f"{name} = ")
        if i < 0:
            renamed.append(name)
            continue
        blob = src[i:i + 900]
        gone = [x for x in ours if f'"{x}"' not in blob]
        if gone:
            missing_all.append(f"{name}: {gone}")
    assert not renamed, (f"게이트웨이에서 이름이 사라졌다: {renamed} — 바뀐 이름을 찾아 "
                         "이 검사와 models.py 의 사본을 맞춰라")
    assert not missing_all, (f"사본이 어긋났다 — {' · '.join(missing_all)}. "
                             "게이트웨이가 바뀌었다")


def test_게이트웨이_호출_상한과의_관계가_아직_성립한다():
    """우리 단계 상한은 게이트웨이 상한(`CALL_TIMEOUT_S`)과 **관계로** 정해져 있다 —
    그보다 짧게 둬야 우리가 먼저 끊고 기록을 남긴다. 그쪽이 바뀌면 그 관계가 조용히
    뒤집혀, 게이트웨이가 먼저 끊고 우리에겐 `unknown` 만 남는다."""
    from app.procedures.runner import EXPECT_TIMEOUT, WARMUP_TIMEOUT

    src = _gateway_source()
    if src is None:
        pytest.skip("HWAXMcpGateway 리포가 이 박스에 없다")
    import re as _re

    # ⚠ 앞에서부터 처음 나오는 숫자를 집으면 안 된다. 실물은
    # `CALL_TIMEOUT_S = int(os.environ.get("GATEWAY_CALL_TIMEOUT", "120"))` 이라
    # 환경변수 **이름 안의 숫자**나 `60 * 2` 의 `60` 을 집을 수 있다 — 지금 120 이
    # 나오는 것은 운이다. 그 줄의 **마지막** 숫자(기본값 리터럴)를 본다.
    line = _re.search(r"^CALL_TIMEOUT_S\s*=.*$", src, _re.M)
    assert line, "게이트웨이에서 CALL_TIMEOUT_S 를 못 읽었다 — 이름이 바뀌었나"
    nums = _re.findall(r"\d+(?:\.\d+)?", line.group(0))
    assert nums, f"CALL_TIMEOUT_S 줄에 숫자가 없다: {line.group(0)}"
    gw = float(nums[-1])
    # ⚠ 이 값은 **배포된 게이트웨이의 값이 아니다** — GATEWAY_CALL_TIMEOUT 로 덮인다.
    # 소스의 기본값끼리 비교하는 검사이고, 운영값이 다르면 이 관계는 보장되지 않는다.
    assert 30 <= gw <= 600, f"읽은 값이 상한 같지 않다: {gw} ({line.group(0)})"
    assert max(EXPECT_TIMEOUT.values()) < gw, (
        f"단계 상한 {max(EXPECT_TIMEOUT.values())} 이 게이트웨이 {gw} 보다 짧지 않다")
    assert WARMUP_TIMEOUT > gw, (
        f"워밍업 {WARMUP_TIMEOUT} 이 게이트웨이 {gw} 를 안 넘는다 — 콜드스타트를 못 흡수한다")


def test_게이트웨이가_실제로_보내는_문구를_본다():
    """⚠ 판정기가 찾는 문자열은 **호출자가 받는 본문**에 있어야 한다.

    `invoke-denied` 는 게이트웨이 **감사 로그**에만 쓰이고 응답 본문에는 없다. 그것만
    보던 동안 파괴 도구 관문 갈래는 프로덕션에서 죽어 있었고, 관문에 막힌 호출이
    `tool_error`(그냥 에러)로 기록됐다. 테스트는 손으로 지어낸 문자열을 단언해 초록이었다.
    """
    from app.procedures.judge import (GW_DENIED, GW_FORBIDDEN, GW_UNAVAILABLE,
                                      GW_UNKNOWN)

    src = _gateway_source()
    if src is None:
        pytest.skip("HWAXMcpGateway 리포가 이 박스에 없다")
    # `TextContent(... text=...)` 로 나가는 문구에 있어야 한다 — 감사 줄이 아니라
    for name, needle in (("GW_DENIED", GW_DENIED), ("GW_UNKNOWN", GW_UNKNOWN),
                         ("GW_FORBIDDEN", GW_FORBIDDEN),
                         ("GW_UNAVAILABLE", GW_UNAVAILABLE)):
        assert needle in src, f"{name}({needle!r}) 가 게이트웨이 소스에 없다"
        i = src.find(needle)
        around = src[max(0, i - 400):i + 200]
        assert "TextContent" in around or "isError" in around, (
            f"{name} 은 응답 본문이 아니라 로그·주석 자리에만 있다 — "
            f"호출자는 그 문자열을 절대 못 받는다")
