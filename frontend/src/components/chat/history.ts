// 챗 대화를 에이전트 서버 이력(history) 계약으로 옮긴다 — 줄이는 일은 창을 아는 서버가 한다
import type { HistoryMessage } from '../../api/chat.api';
import type { Message } from '../../types/chat';

// 포털 ChatRequest.history 의 항목 수 상한과 같은 수다(에이전트 서버 HIST_MAX_ITEMS 와도 같다). 넘으면 포털이 422 다.
export const HISTORY_MAX_ITEMS = 160;
// 이력 합계 상한 — 포털 _WINDOW_CHARS(1M 토큰 창 하나 = 1,048,576 × 4자)와 같은 값이다(backend tests/test_front_window_payload.py).
// 종전엔 항목마다 머리 24,000자 · 합계 600,000자에서 잘랐다. 결정문 하나가 13,000~75,000자라 결정문이 든 대화를 이어가면
// (5)뒤집힘 조건·(7)신뢰도·risk_spec 이 이력에서 조용히 빠졌고, 1M 창의 에이전트 서버 이력 예산(약 85만 자)보다 먼저 묶였다.
// 에이전트 서버는 예산을 넘는 오래된 턴을 버리지 않고 발췌 압축본으로 남긴다(app._compact_turns) — 여기서 먼저 버리면
// 그 턴은 존재 자체가 사라진다. 그래서 창 하나까지 다 보낸다. 항목 하나를 줄이는 것도 서버 몫이다(에이전트 서버 HIST_ITEM_MAX).
export const HISTORY_MAX_TOTAL_CHARS = 4_194_304;

/** 멀티턴 history: 대화의 기존 메시지 → 계약 형식(오래된 것→최신 순, 이번 발화 제외). 항목은 자르지 않는다. */
export function buildHistory(messages: Message[]): HistoryMessage[] {
  const items = messages
    .filter((m) => !m.error && m.text.trim() !== '')
    .map((m) => ({ role: m.role, content: m.text }));
  // 최근 것 우선 — 뒤에서부터 개수/총량 예산만큼 담고, 다시 시간순으로 뒤집는다.
  const out: HistoryMessage[] = [];
  let total = 0;
  for (let i = items.length - 1; i >= 0 && out.length < HISTORY_MAX_ITEMS; i--) {
    if (total + items[i].content.length > HISTORY_MAX_TOTAL_CHARS) break;
    total += items[i].content.length;
    out.push(items[i]);
  }
  return out.reverse();
}
