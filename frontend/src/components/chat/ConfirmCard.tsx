// 확인 카드(10-30 HA-29) — 에이전트 서버가 보내지 않고 멈춘 잡 · 쓰기에 사람이 '실행' · '취소' 로 답하는 단추
import { useChat } from '../../state/ChatContext';
import type { ConfirmCard as Card } from '../../types/chat';
import type { ConfirmState } from './confirm';

const KIND: Record<string, string> = { job: '잡', write: '쓰기', confirm: '되돌리기 어려움' };

const CLOSED: Record<Exclude<ConfirmState, 'open'>, string> = {
  answered: '이 카드에는 이미 답했습니다',
  closed: '카드 바로 다음 말로만 답할 수 있어 이 카드는 닫혔습니다 — 다시 시키면 새 카드가 섭니다',
  expired: '30분이 지나 이 카드는 닫혔습니다 — 다시 시키면 새 카드가 섭니다',
};
const BUSY = "입력창에 쓰던 글 · 붙인 그림이 있어 단추를 잠갔습니다 — 비우면 누를 수 있습니다('실행' 이라고 답해도 됩니다)";

/** 호출의 무엇 · 인자 · 예상 작업량은 본문의 카드 글에 이미 있다(서버 사본 · 다른 기기도 같은 글을 본다). 여기는 단추와 상태만 더한다 —
 *  단추는 에이전트 서버가 준 승인 · 거절 글(approve_text · decline_text)을 다음 말로 보낸다. 답할 수 없는 카드는 단추를 잠근다(state — confirm.ts,
 *  서버도 바로 다음 말 하나 · 30분만 받는다 — 지난 카드에 답하면 '찾지 못했다' 로 처리하고 필요하면 새 카드가 선다). */
export function ConfirmCard({ card, state }: { card: Card; state: ConfirmState }) {
  const { sendMessage, streaming, input, attachedImages } = useChat();
  // 쓰던 글 · 붙인 그림이 있으면 누르지 않게 한다 — 보내기가 입력창을 비워 그 글이 사라지고 그림은 이 승인 말에 실린다(ChatActionBar 와 같은 까닭).
  // 붙인 문서는 보지 않는다 — 떼기 전까지 모든 말에 실려 다니는 칸이다(ChatContext attachedDocs).
  const busy = input.trim() !== '' || attachedImages.length > 0;
  const off = state !== 'open' || streaming || busy;
  const why = state === 'open' && busy ? BUSY : '';
  const kinds = [...new Set(card.calls.map((c) => KIND[c.kind] ?? c.kind))];
  // 셋째 인자 null — 켜 둔 분석 루틴을 싣지도 쓰지도 않는다. 실리면 에이전트 서버가 카드를 판정하기 전에 루틴 가지로 보내, '취소' 를 눌러도 루틴이
  // 새로 돈다(ChatContext sendMessage 의 약속 — ChatActionBar 의 한 번 누름 보내기와 같다).
  return (
    <div className="msg-confirm" role="group" aria-label="확인이 필요한 작업">
      <button type="button" className="btn-primary" disabled={off} title={why} onClick={() => sendMessage(card.approve_text, undefined, null)}>
        실행
      </button>
      <button type="button" className="btn-secondary" disabled={off} title={why} onClick={() => sendMessage(card.decline_text, undefined, null)}>
        취소
      </button>
      <span className="msg-confirm-note">
        {state !== 'open' ? CLOSED[state] : busy ? BUSY : `${card.calls.length}건 · ${kinds.join(' · ')} · 확인 번호 ${card.id} · 30분`}
      </span>
    </div>
  );
}
