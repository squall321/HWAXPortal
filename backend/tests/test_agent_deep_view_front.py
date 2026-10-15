# 심층 보기의 지식카드 칸 — 빈 카드 안내·긴 카드 이어 읽기·검색칸 문구가 에이전트서버 응답과 맞는지(프론트 소스 대조)
"""읽기 칸은 에이전트서버 /catalog/record 응답을 그린다(docs/request_1015.md K1·K3·K5).

  sections·table·truncated        종전부터
  total_sections·total_chars      카드 전체(블록을 푼 절 기준 · RAG 절로 채웠으면 그 절 기준) 총량 — 없으면 구 서버
  next {section, char} | null     이어 읽을 위치. char > 0 이면 다음 쪽 첫 절은 앞 쪽 마지막 절의 뒷부분이다

프런트 전용이라 소스 지점을 본다. 이어 붙이는 동작 자체는 임시 진입점으로 화면에서 확인했다(이 시험의 몫이 아니다).
"""
from pathlib import Path

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _view() -> str:
    return (_FRONT / "components" / "chat" / "AgentDeepView.tsx").read_text("utf-8")


# ── K1-3 빈 카드 ──────────────────────────────────────────────────────────────────────────────
def test_글이_하나도_없는_카드는_비어_있다고_말한다():
    """절이 0개일 때만 안내가 떠서, 제목만 늘어선 카드(MX 백서 427장)가 다 불러온 카드처럼 보였다. [].every 는 true 라
    에이전트서버가 빈 카드를 절 0개로 주는 지금 경우도 그대로 덮는다."""
    src = _view()
    assert ('{rec.sections.every((s) => !s.text) && !rec.table && '
            '<p className="pv-empty">본문이 비어 있는 카드입니다.</p>}') in src
    assert "rec.sections.length === 0 && !rec.table" not in src
