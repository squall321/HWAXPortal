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

// ── 심의 확인 카드의 고치기(docs/request-1125 WD-06) ─────────────────────────────────────────────────────────────
/** 엔진의 심의 종류(HWAXAgentServer delib_jobs.JOBS 의 키 · label) — 카드의 '종류' 고르기. 엔진이 받지 않는 값은 에이전트 서버가 버린다(시험이 견준다). */
export const ENGINE_JOBS: readonly (readonly [string, string])[] = [
  ['default', '자유 심의'], ['diagnosis', '원인 규명'], ['option-select', '안 선택'], ['credibility', '신뢰 판정'],
  ['mechanism', '메커니즘 규명'], ['sim-plan', '해석 설계'], ['test-plan', '시험 설계'], ['build-plan', '구축 계획'],
  ['risk-review', '리스크 심사'], ['risk-review-sealed', '리스크 심사(봉인)'],
];
/** 카드에서 고를 수 있는 라운드 — 0 은 엔진 기본(3). 에이전트 서버 _confirm_apply_edit 와 같은 범위(0 · 2~8). */
export const EDIT_ROUNDS: readonly number[] = [0, 2, 3, 4, 5, 6, 7, 8];

export interface DelibEdit {
  save_report: boolean;
  job: string;
  rounds: number;
}

/** 카드가 보인 값(summary) 대비 바꾼 칸만 — 승인 말의 confirm_edit.set. 이어하기는 종류를 앞 잡에서 잇는다(엔진이 job 을 버린다 — 싣지 않는다). */
export function editDiff(sm: { call: string; job: string; rounds: number; save_report: boolean; editable: string[] }, ed: DelibEdit):
  { save_report?: boolean; job?: string; rounds?: number } {
  const out: { save_report?: boolean; job?: string; rounds?: number } = {};
  if (sm.editable.includes('save_report') && ed.save_report !== sm.save_report) out.save_report = ed.save_report;
  if (sm.editable.includes('job') && sm.call === 'deliberate_start' && ed.job && ed.job !== sm.job) out.job = ed.job;
  if (sm.editable.includes('rounds') && ed.rounds !== sm.rounds && (ed.rounds === 0 || (ed.rounds >= 2 && ed.rounds <= 8))) out.rounds = ed.rounds;
  return out;
}
