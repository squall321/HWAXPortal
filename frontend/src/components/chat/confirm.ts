// 확인 카드(10-30 HA-29)를 지금 답할 수 있는지 — 에이전트 서버의 답 판정(_confirm_reply)과 같은 조건을 화면이 먼저 본다
import type { Message } from '../../types/chat';

/** open — 누를 수 있다 · answered — 뒤에 사람 말이 있다 · closed — 뒤에 다른 글(보내기 알림 등)이 붙었거나 이력에 그 카드 번호가 실리지 않는다 ·
 *  expired — 30분이 지났다. */
export type ConfirmState = 'open' | 'answered' | 'closed' | 'expired';

/** messages[i] 의 카드 상태. 서버는 이력의 **마지막 항목**이 그 카드 번호를 실은 어시스턴트 글일 때만 다음 말을 카드의 답으로 받는다 — 카드 뒤에 사람
 *  말 없이 보내기 알림이 붙어도 그 카드는 답할 수 없다(누르면 서버가 그 카드를 지우고 단추 글을 보통 말로 읽는다). 오류가 난 답 · 빈 답은 이력에
 *  실리지 않는다(history.buildHistory). */
export function confirmState(messages: Message[], i: number, now: number): ConfirmState {
  const m = messages[i];
  const card = m?.confirm;
  if (!card) return 'closed';
  const after = messages.slice(i + 1);
  if (after.some((x) => x.role === 'user')) return 'answered';
  if (after.length > 0 || m.error || !m.text.includes(card.id)) return 'closed';
  return typeof card.expires_at === 'number' && now > card.expires_at ? 'expired' : 'open';
}
