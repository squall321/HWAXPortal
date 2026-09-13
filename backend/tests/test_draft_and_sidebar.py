# 랜딩 draft 영속 + 사이드바 전문가 표시 — 둘 다 '골라 뒀는데 안 보이는' 결함이었다
"""entry-F7 / during-F7 (docs/persona-chat 의 '안 한 것').

draft 는 새로고침에 날아갔다. 사용자는 **여전히 골라 둔 줄** 알고 첫 발화를 던지고,
아무것도 적용되지 않은 답을 받는다 — 화면에 아무 표시가 없어 알 방법이 없다.
사이드바는 어느 전문가와 나눈 대화인지 열어 봐야만 알 수 있었다.

프론트 전용이라 소스 지점을 본다. 세 지점(초기 로드·저장·소비 후 비움) 중 하나만 빠져도
기능이 조용히 반쪽이 된다.
"""
from pathlib import Path

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_draft_를_켤_때_읽는다():
    src = (_FRONT / "state" / "ChatContext.tsx").read_text("utf-8")
    assert "useState<DraftPins>(() => loadDraftPins())" in src


def test_draft_를_바꿀_때_저장한다():
    src = (_FRONT / "state" / "ChatContext.tsx").read_text("utf-8")
    blk = src[src.index("const setDraftPins = useCallback"):]
    assert "saveDraftPins(v)" in blk[:400], "저장 안 하면 읽을 게 없다"


def test_대화로_옮긴_뒤_비운_것도_저장된다():
    """비움이 저장 안 되면 새로고침에 draft 가 되살아나 다음 새 대화에도 계속 붙는다."""
    src = (_FRONT / "state" / "ChatContext.tsx").read_text("utf-8")
    assert "setDraftPins({ tools: [], apps: [] })" in src


def test_저장소_헬퍼가_잘못된_값을_방어한다():
    src = (_FRONT / "state" / "chatStore.ts").read_text("utf-8")
    fn = src[src.index("export function loadDraftPins"):]
    fn = fn[:fn.index("export function saveDraftPins")]
    assert "catch" in fn, "깨진 localStorage 한 줄이 챗 전체를 못 열게 하면 안 된다"
    assert "Array.isArray" in fn


def test_사이드바가_전문가를_보여_준다():
    src = (_FRONT / "components" / "chat" / "ChatSidebar.tsx").read_text("utf-8")
    assert "conv.pinnedAgentName || conv.pinnedAgent" in src
    assert "sb-item-agent" in src
    css = (_FRONT / "styles" / "chatpage.css").read_text("utf-8")
    assert ".sb-item-agent" in css, "클래스만 붙이고 스타일이 없으면 줄바꿈 없이 붙어 나온다"
