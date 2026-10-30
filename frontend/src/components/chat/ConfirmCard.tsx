// 확인 카드(10-30 HA-29) — 에이전트 서버가 보내지 않고 멈춘 잡 · 쓰기에 사람이 '실행' · '취소' 로 답하는 단추
import { useChat } from '../../state/ChatContext';
import type { ConfirmCard as Card } from '../../types/chat';

const KIND: Record<string, string> = { job: '잡', write: '쓰기', confirm: '되돌리기 어려움' };

/** 호출의 무엇 · 인자 · 예상 작업량은 본문의 카드 글에 이미 있다(서버 사본 · 다른 기기도 같은 글을 본다). 여기는 단추와 상태만 더한다 —
 *  단추는 에이전트 서버가 준 승인 · 거절 글(approve_text · decline_text)을 다음 말로 보낸다. 답한 카드 · 30분이 지난 카드는 단추를 잠근다
 *  (서버도 한 번만 · 30분만 받는다 — 지난 카드에 답하면 '찾지 못했다' 로 처리하고 필요하면 새 카드가 선다). */
export function ConfirmCard({ card, answered }: { card: Card; answered: boolean }) {
  const { sendMessage, streaming } = useChat();
  const expired = typeof card.expires_at === 'number' && Date.now() > card.expires_at;
  const off = answered || expired || streaming;
  const kinds = [...new Set(card.calls.map((c) => KIND[c.kind] ?? c.kind))];
  return (
    <div className="msg-confirm" role="group" aria-label="확인이 필요한 작업">
      <button type="button" className="btn-primary" disabled={off} onClick={() => sendMessage(card.approve_text)}>
        실행
      </button>
      <button type="button" className="btn-secondary" disabled={off} onClick={() => sendMessage(card.decline_text)}>
        취소
      </button>
      <span className="msg-confirm-note">
        {expired
          ? '30분이 지나 이 카드는 닫혔습니다 — 다시 시키면 새 카드가 섭니다'
          : answered
            ? '이 카드에는 이미 답했습니다'
            : `${card.calls.length}건 · ${kinds.join(' · ')} · 확인 번호 ${card.id} · 30분`}
      </span>
    </div>
  );
}
