# 확인 카드(10-30 HA-29) · 짚기만 한 자기검증(HA-27)이 웹 챗에 그려지는지 — SSE confirm 받기 · 단추 · 영속 · flagged (프론트 소스 대조)
"""에이전트서버가 사람이 시키지 않은 잡 · 쓰기를 보내지 않고 확인 카드로 멈춘다(HA-29). 본문 끝의 카드 글(서버 사본 · 다른 기기)과 함께
SSE `confirm` 을 내고, 화면은 그 카드에 '실행' · '취소' 단추를 단다 — 단추는 서버가 준 승인 · 거절 글을 다음 말로 보낸다. 자기검증은
검토자의 고침이 원문과 어긋나면 넣지 않고 짚기만 한다(HA-27 `flagged`). 프론트 전용이라 소스 지점을 본다.
"""
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _read(rel: str) -> str:
    return (_SRC / rel).read_text("utf-8")


def test_SSE_confirm_을_받아_메시지에_카드를_단다():
    api = _read("api/chat.api.ts")
    assert "onConfirm?: (e: ConfirmCard) => void;" in api
    assert "    case 'confirm':\n      h.onConfirm?.(payload as ConfirmCard);\n      break;" in api, "모르는 이벤트는 조용히 버려진다 — 자리가 있어야 한다"
    ctx = _read("state/ChatContext.tsx")
    blk = ctx[ctx.index("onConfirm: (e) =>"):]
    blk = blk[:blk.index("},") + 2]
    assert "patch(cid, botId, (m) => ({ ...m, confirm: e }))" in blk and "Array.isArray(e.calls)" in blk


def test_카드_단추는_서버가_준_글을_보내고_답했거나_지나면_잠긴다():
    src = _read("components/chat/ConfirmCard.tsx")
    assert "onClick={() => sendMessage(card.approve_text)}" in src and "onClick={() => sendMessage(card.decline_text)}" in src, \
        "단추 글을 화면이 지어내면 서버의 답 판정(_confirm_reply)과 어긋난다"
    assert "const off = answered || expired || streaming;" in src
    assert src.count("disabled={off}") == 2
    assert "Date.now() > card.expires_at" in src
    lst = _read("components/chat/MessageList.tsx")
    assert "{!msg.streaming && msg.confirm && <ConfirmCard card={msg.confirm} answered={answered} />}" in lst
    assert "const lastUser = messages.map((m) => m.role).lastIndexOf('user');" in lst
    assert "<Row key={m.id} msg={m} answered={i < lastUser} />" in lst, "카드 뒤에 사람 말이 있으면 답한 카드다(서버도 그 말로 카드를 닫는다)"


def test_카드는_브라우저_사본에_남고_되살아난다():
    store = _read("state/chatStore.ts")
    assert "...(m.confirm ? { confirm: m.confirm } : {})," in store, "저장할 때 빠지면 새로고침 뒤 단추가 사라진다"
    assert "...(m.confirm && typeof m.confirm.id === 'string' && Array.isArray(m.confirm.calls) ? { confirm: m.confirm } : {})," in store


def test_자기검증의_버린_고침과_관문_수는_사본에_남기지_않는다():
    store = _read("state/chatStore.ts")
    fn = store[store.index("function storedMeta(meta: TurnMeta): TurnMeta {"):]
    fn = fn[:fn.index("\n}\n") + 3]
    assert "delete keep.dropped;" in fn and "delete keep.gate;" in fn
    assert "...(m.meta ? { meta: storedMeta(m.meta) } : {})," in store


def test_짚기만_한_답은_고친_답과_다르게_보인다():
    types = _read("types/chat.ts")
    assert "status: 'ok' | 'fixed' | 'flagged' | 'skipped' | 'suspect' | 'failed' | 'unreadable';" in types
    assert "  flags?: string[];" in types and "  dropped?: string[];" in types
    lst = _read("components/chat/MessageList.tsx")
    note = lst[lst.index("function CheckNote({ check }: { check: SelfCheck }) {"):]
    note = note[:note.index("\nfunction ", 10)]
    assert "if (check.status === 'flagged') {" in note
    assert "짚었습니다 — 답은 고치지 않았습니다" in note, "짚기만 한 답을 '고쳤습니다' 로 보이면 사람이 고친 답으로 읽는다"
    assert "dropped" not in note, "버린 고침은 QA 용 — 화면에 보이지 않는다"
