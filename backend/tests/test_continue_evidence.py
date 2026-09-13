# 이어하기가 이전 회차의 도구 조회 결과를 승계하는지 — 안 하면 수치가 조용히 사라진다
"""이전 회차 좌석들이 DB 로 뽑은 값이 결정문 문장에 살아남은 것만 넘어가던 자리.

양보 불가 조항을 요약에서 분리한 이유가 "요약은 자유 텍스트라 빠져도 아무도 모른다" 인데
**수치도 똑같다.** 다음 회차는 같은 것을 다시 조회하거나, 못 하면 기억으로 말한다.

새 채널을 파지 않았다 — delib_opts.evidence 가 이미 "검증 대상이지 결론이 아닌 원천 데이터"
통로다. 그래서 이 테스트는 계약이 아니라 **세 지점의 연결**을 본다.
"""
import re
from pathlib import Path

from app.agent.routes import DelibOpts

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_evidence_채널이_계약에_있다():
    assert "evidence" in DelibOpts.model_fields


def test_이어하기가_이전_조회를_실어_보낸다():
    src = (_FRONT / "state" / "ChatContext.tsx").read_text("utf-8")
    blk = src[src.index("continueDeliberation"):]
    blk = blk[:blk.index("sendMessage('/심의 ") + 2000]
    assert "priorGatheredEvidence(prior.evidence)" in blk, "이전 회차 조회를 안 뽑는다"
    assert "evidence: gathered" in blk, "뽑아 놓고 안 실어 보내면 아무 일도 안 일어난다"


def test_도구_결과만_추린다():
    """'지식카드'·'자유 조회 실패'·'인간 검토자 의견' 은 도구 결과가 아니다."""
    src = (_FRONT / "components" / "chat" / "handoff.ts").read_text("utf-8")
    fn = src[src.index("export function priorGatheredEvidence"):]
    assert "e?.included" in fn, "좌석에 안 들어간 근거를 승계하면 없던 사실이 생긴다"
    assert re.search(r"a-z0-9_", fn), "도구 이름 형태로 거르지 않으면 한글 라벨이 섞인다"
    assert "이전 회차" in fn, "출처에 지위를 안 적으면 이번 회차 조회와 구별이 안 된다"


def test_상한이_세_계층에서_같다():
    """세 계층 중 하나만 작으면 거기서 잘리고, 잘린 사실은 아무 데도 안 남는다."""
    src = (_FRONT / "components" / "chat" / "handoff.ts").read_text("utf-8")
    n = int(re.search(r"export const EVID_ITEMS = (\d+)", src).group(1))
    assert n == DelibOpts.model_fields["evidence"].metadata[0].max_length
