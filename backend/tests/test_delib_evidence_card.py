# 심의 화면의 근거 카드가 좌석에 주지 않은 카드를 '직접 연관 없음' 으로 잘못 부르지 않는지 — 버린 것을 알리는 카드가 '무관한 자료' 로 읽힌다
"""엔진은 좌석에 주지 않은 것을 `included=false` 근거 카드로 화면에 남긴다. 처음엔 그런 카드가 '조회는 했는데
화두와 무관해 싣지 않은 VOC·검색 결과' 하나뿐이라 딱지가 '직접 연관 없음' 이었다.

지금은 같은 깃발로 **버린 것을 알리는 카드**가 온다 — '사전 근거 본문 없음'·'사전 근거 건수 초과'·'사전 근거
예산 초과'·'사람 의견 상한 초과'·'의장 전사 상한 초과'·'지식카드 조회 강등'·'… 자유 조회 실패'
(2026-10-07 S26U 피드백, docs/delib-engine-feedback). 거기에 '직접 연관 없음' 이 붙으면 '예산을 넘겨 못 실었다'
가 '무관해서 뺐다' 로 읽힌다 — 알리려고 만든 카드가 거꾸로 말한다. 딱지는 사유를 말하지 않는다(사유는 카드
제목과 본문에 있다). 깃발이 뜻하는 것만 말한다 — 좌석에 주지 않았다.

그 뒤 엔진이 그 가운데 **알림**을 따로 가른다(`notice=true`) — '의장 전사 상한 초과'(줄인 것은 의장의 입력이고 좌석은
전부 받았다) · '좌석 유실' · '지정 앱 범위 제한 불가'. 이 카드들은 좌석에 안 준 근거가 아니라서 '좌석에 주지 않음' 도
거꾸로 말한다. 깃발은 세 곳을 지나야 화면에 닿는다 — 타입(types/chat.ts) · 이벤트 병합(ChatContext mergeDelib) ·
카드(DelibView). 한 곳이라도 빠지면 에러 없이 종전 딱지로 남는다.

프론트에는 단위 시험 러너가 없어 소스에서 그 자리만 읽는다(test_continue_evidence 와 같은 방식). 딱지가 화면에 실제로
그렇게 뜨는지는 test_delib_stream_in_browser 가 이벤트를 흘려 본다.
"""
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
_VIEW = _SRC / "components" / "chat" / "DelibView.tsx"


def _evidence_card() -> str:
    src = _VIEW.read_text(encoding="utf-8")
    blk = src[src.index("function EvidenceCard("):]
    return blk[:blk.index("\nfunction ")]


def test_좌석에_주지_않은_카드를_무관하다고_부르지_않는다():
    blk = _evidence_card()
    assert "ev.included ?" in blk, "근거 카드가 included 깃발을 안 읽는다 — 이 시험이 보는 자리가 사라졌다"
    assert "연관 없음" not in blk, "버린 것을 알리는 카드까지 '무관한 자료' 로 읽힌다"
    assert "좌석에 주지 않음" in blk


def test_알림_카드는_좌석에_주지_않음이_아니라_알림이라고_부른다():
    blk = _evidence_card()
    assert "ev.included ? '심의에 포함' : ev.notice ? '알림' : '좌석에 주지 않음'" in blk, (
        "포함된 근거가 먼저다 — notice 를 먼저 보면 포함된 카드가 알림으로 뜬다")


def test_알림_깃발이_이벤트에서_카드까지_이어진다():
    """엔진 → SSE delib(evidence) → mergeDelib → DelibData.evidence[] → 카드. 가운데서 빠지면 조용히 종전 딱지다."""
    types = (_SRC / "types" / "chat.ts").read_text(encoding="utf-8")
    assert "included: boolean; notice?: boolean }[]" in types, "근거 항목 타입에 notice 가 없다"
    ctx = (_SRC / "state" / "ChatContext.tsx").read_text(encoding="utf-8")
    case = ctx[ctx.index("case 'evidence': {"):]
    case = case[:case.index("break;")]
    assert "e.notice" in case, "mergeDelib 가 notice 를 안 옮긴다 — 화면까지 가지 못한다"
