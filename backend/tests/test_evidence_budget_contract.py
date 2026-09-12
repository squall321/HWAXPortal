# 심의 사전 근거 상한이 프론트·포털·엔진 세 곳에서 같은 값인지 — 어긋나면 조용히 잘린다
"""사전 근거(delib_opts.evidence)는 세 계층을 지난다.

  프론트 frontend/src/components/chat/handoff.ts  EVID_ITEMS / EVID_ITEM_MAX
  포털   backend/app/agent/routes.py              DelibOpts.evidence(max_length)  → 넘으면 422
  엔진   HWAXAgentServer/deliberation.py          _EVID_ITEMS / _EVID_ITEM_MAX    → 넘으면 잘라 버린다

좌석 상한(test_seat_cap_contract)과 달리 이쪽은 **어긋나도 아무 신호가 없다.** 프론트가
항목을 12건만 만들면 포털이 40 을 받아도 12건만 오고, 엔진이 2,000자에서 자르면 발표자료
한 장 분량만 좌석에 간다 — 심의는 정상적으로 돌고 결론도 나온다. 틀린 줄 모른 채로.

실제로 그랬다. 종전 값(12항목 · 항목당 2,000자 · 합계 11,000자)은 챗 도구결과 몇 건을
나르려고 잡은 것이라, 추출하면 30,000~80,000자인 발표자료·보고서를 넣으면 첫 항목에서
잘렸다. 그래서 여기 숫자를 박아 둔다.
"""
import re
from pathlib import Path

from app.agent.routes import DelibOpts

_ROOT = Path(__file__).resolve().parents[2]
_ENGINE = _ROOT.parent / "HWAXAgentServer" / "deliberation.py"
_HANDOFF = _ROOT / "frontend" / "src" / "components" / "chat" / "handoff.ts"


def _portal_items() -> int:
    f = DelibOpts.model_fields["evidence"]
    caps = [m.max_length for m in f.metadata if getattr(m, "max_length", None) is not None]
    assert caps, "DelibOpts.evidence 에 max_length 가 없다 — 상한이 없으면 폭주 방지선도 없다"
    return caps[0]


def _front(const: str) -> int:
    src = _HANDOFF.read_text(encoding="utf-8")
    m = re.search(rf"^export const {const}\s*=\s*(\d+)", src, re.M)
    assert m, f"handoff.ts 에서 {const} 를 못 찾았다 — 이름이 바뀌었으면 이 테스트도 고쳐라"
    return int(m.group(1))


def _engine(const: str) -> int:
    src = _ENGINE.read_text(encoding="utf-8")
    m = re.search(rf'^{const}\s*=\s*_env_int\("[A-Z_]+",\s*(\d+)\)', src, re.M)
    assert m, f"deliberation.py 에서 {const} 기본값을 못 찾았다 — 이름이 바뀌었으면 이 테스트도 고쳐라"
    return int(m.group(1))


def test_근거_항목수_상한이_세_곳에서_같다():
    front, portal, engine = _front("EVID_ITEMS"), _portal_items(), _engine("_EVID_ITEMS")
    assert front == portal == engine, (
        f"항목수 상한 불일치 — 프론트 {front} · 포털 {portal} · 엔진 {engine}. "
        "작은 쪽에서 잘리고 잘린 사실은 아무 데도 안 남는다."
    )


def test_항목당_글자_상한이_프론트와_엔진에서_같다():
    front, engine = _front("EVID_ITEM_MAX"), _engine("_EVID_ITEM_MAX")
    assert front == engine, (
        f"항목당 상한 불일치 — 프론트 {front} · 엔진 {engine}. 프론트가 더 작으면 엔진 상한을 "
        "올려도 소용없고, 더 크면 엔진이 말없이 자른다."
    )


def test_합계_예산은_항목당_상한보다_크다():
    """예산이 항목 하나보다 작으면 문서 한 건도 못 들어간다 — 종전이 정확히 그 상태였다."""
    budget, item = _engine("_EVID_BUDGET"), _engine("_EVID_ITEM_MAX")
    assert budget >= item * 2, (
        f"합계 예산 {budget:,}자가 항목당 상한 {item:,}자의 2배 미만이다 — 문서 한 건에 "
        "근거 한 줄도 못 붙인다."
    )


def test_문서_한_건_분량이_들어간다():
    """발표자료·보고서를 추출하면 보통 30,000자를 넘는다. 이 기능의 최소 요구다."""
    assert _engine("_EVID_ITEM_MAX") >= 12000, "항목당 상한이 발표자료 한 건을 못 담는다"
    assert _engine("_EVID_BUDGET") >= 40000, "합계 예산이 문서 한 건 + 챗 근거를 못 담는다"
