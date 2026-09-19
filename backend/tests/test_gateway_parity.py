# 두 리포가 **같은 목록**을 들고 있는지 — 한쪽만 늘리면 양쪽 초록인 채 느슨해진다
#
# 게이트웨이 `_INVOKE_DENY_EXACT` 는 "포털이 이미 확정한 MUST_GATE 를 그대로 쓴다" 고 주석이 말한다
# (HWAXMcpGateway/gateway.py:1317-1320). 그 '그대로' 를 사람 눈으로만 지키면 어긋난다 — 어긋난 쪽은
# 늘 느슨한 쪽이고, 느슨해진 자리는 **사람 승인이 필요한 도구가 별칭으로 통과하는 구멍**이다.
# 포털의 `GW_DENY_PREFIX`·`GW_DENY_SUFFIX` 는 반대 방향 거울이다 — 실행기 검증이 "이 이름은 애초에
# 못 부른다" 고 미리 말해 주는 근거라, 게이트웨이가 바뀌면 포털의 예측이 조용히 틀린다.
#
# 게이트웨이를 **import 하지 않는다**(설정 파일·토큰이 있어야 뜬다) — 소스를 AST 로 읽는다.
import ast
from pathlib import Path

import pytest

from app.procedures.models import GW_DENY_PREFIX, GW_DENY_SUFFIX, MUST_GATE

GW = Path(__file__).resolve().parents[2].parent / "HWAXMcpGateway" / "gateway.py"


def _literals(path: Path, names: set[str]) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict = {}
    for node in tree.body:                      # 모듈 수준만 — 함수 안의 동명 지역변수에 속지 않는다
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id in names:
                v = node.value
                if isinstance(v, ast.Call) and getattr(v.func, "id", "") == "frozenset":
                    out[t.id] = frozenset(ast.literal_eval(v.args[0]))
                else:
                    out[t.id] = ast.literal_eval(v)
    return out


@pytest.fixture(scope="module")
def gw() -> dict:
    if not GW.exists():
        pytest.skip("형제 리포 HWAXMcpGateway 가 이 박스에 없다")
    got = _literals(GW, {"_INVOKE_DENY_EXACT", "_INVOKE_DENY_PREFIX", "_INVOKE_DENY_SUFFIX"})
    missing = {"_INVOKE_DENY_EXACT", "_INVOKE_DENY_PREFIX", "_INVOKE_DENY_SUFFIX"} - set(got)
    assert not missing, f"게이트웨이에서 목록을 못 찾았다(이름이 바뀌었나): {sorted(missing)}"
    return got


def test_되돌리기_어려운_도구_목록이_두_리포에서_같다(gw):
    """한쪽에만 추가하면 — 포털은 사람 승인을 요구하는데 게이트웨이는 별칭으로 통과시킨다(또는 반대로
    승인받은 절차 단계가 승인 뒤에 죽는다)."""
    only_portal = sorted(MUST_GATE - gw["_INVOKE_DENY_EXACT"])
    only_gw = sorted(gw["_INVOKE_DENY_EXACT"] - MUST_GATE)
    assert not only_portal, (
        f"포털 MUST_GATE 에만 있다 {only_portal} — 게이트웨이 `_INVOKE_DENY_EXACT` 에 넣어야 "
        f"별칭 우회가 막힌다(gateway.py:_INVOKE_DENY_EXACT)")
    assert not only_gw, (
        f"게이트웨이에만 있다 {only_gw} — 포털 `MUST_GATE` 에 넣어야 절차가 승인을 먼저 받는다"
        f"(app/procedures/models.py:MUST_GATE). 승인 없이 실행하려다 게이트웨이에서 죽는다")


def test_이름_패턴_거울이_같다(gw):
    """포털은 이 패턴으로 '애초에 못 부른다' 고 **미리** 말한다 — 게이트웨이와 갈리면 그 예측이 거짓이다."""
    assert tuple(GW_DENY_PREFIX) == tuple(gw["_INVOKE_DENY_PREFIX"]), (
        "접두 목록이 갈렸다 — models.py:GW_DENY_PREFIX 와 gateway.py:_INVOKE_DENY_PREFIX")
    assert tuple(GW_DENY_SUFFIX) == tuple(gw["_INVOKE_DENY_SUFFIX"]), (
        "접미 목록이 갈렸다 — models.py:GW_DENY_SUFFIX 와 gateway.py:_INVOKE_DENY_SUFFIX")
