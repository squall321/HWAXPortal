// 챗 대화를 에이전트 서버 이력(history) 계약으로 옮긴다 — 줄이는 일은 창을 아는 서버가 한다
import type { HistoryEvidence, HistoryMessage } from '../../api/chat.api';
import type { Message } from '../../types/chat';

// 포털 ChatRequest.history 의 항목 수 상한과 같은 수다(에이전트 서버 HIST_MAX_ITEMS 와도 같다). 넘으면 포털이 422 다.
export const HISTORY_MAX_ITEMS = 160;
// 이력 합계 상한 — 포털 _WINDOW_CHARS(1M 토큰 창 하나 = 1,048,576 × 4자)와 같은 값이다(backend tests/test_front_window_payload.py).
// 종전엔 항목마다 머리 24,000자 · 합계 600,000자에서 잘랐다. 결정문 하나가 13,000~75,000자라 결정문이 든 대화를 이어가면
// (5)뒤집힘 조건·(7)신뢰도·risk_spec 이 이력에서 조용히 빠졌고, 1M 창의 에이전트 서버 이력 예산(약 85만 자)보다 먼저 묶였다.
// 에이전트 서버는 예산을 넘는 오래된 턴을 버리지 않고 발췌 압축본으로 남긴다(app._compact_turns) — 여기서 먼저 버리면
// 그 턴은 존재 자체가 사라진다. 그래서 창 하나까지 다 보낸다. 항목 하나를 줄이는 것도 서버 몫이다(에이전트 서버 HIST_ITEM_MAX).
export const HISTORY_MAX_TOTAL_CHARS = 4_194_304;

// 포털이 근거 항목 하나에서 받는 인자 길이(ChatHistoryEvidence.args) — 넘기면 422 라 여기서 그 길이로 줄인다(원문은 활동 기록에 남는다).
const EVIDENCE_ARGS_MAX = 8000;

/** 어시스턴트 메시지가 그 턴에 도구로 조회한 결과 — 활동 기록(activity)에서 모은다(docs/chat-depth-context CD-D5).
 *  호출(인자)과 완료(결과)는 따로 온다 — 짝 키(call)로 잇고, 짝 키가 없는 낡은 기록은 같은 도구의 직전 인자로 잇는다.
 *  같은 도구 · 같은 결과 머리는 하나만. 날것(result_full)이 있으면 그것, 없으면 미리보기. 실패한 호출은 표지를 단다. */
export function turnEvidence(m: Message): HistoryEvidence[] {
  const out: HistoryEvidence[] = [];
  const seen = new Set<string>();
  const argsByCall = new Map<string, string>();
  const lastArgs = new Map<string, string>();
  for (const a of m.activity ?? []) {
    if (!a.tool) continue;
    const detail = (a.detail ?? '').trim();
    const result = (a.result_full ?? a.result_preview ?? '').trim();
    if (!result) {
      if (detail) {
        if (a.call) argsByCall.set(a.call, detail);
        lastArgs.set(a.tool, detail);
      }
      continue;
    }
    const key = `${a.tool}|${result.slice(0, 80)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const args = detail || (a.call ? argsByCall.get(a.call) : undefined) || lastArgs.get(a.tool) || '';
    lastArgs.delete(a.tool);
    const res = a.ok === false ? `[호출 실패] ${result}` : result;
    out.push(args ? { tool: a.tool.slice(0, 200), args: args.slice(0, EVIDENCE_ARGS_MAX), result: res }
                  : { tool: a.tool.slice(0, 200), result: res });
  }
  return out;
}

function sizeOf(h: HistoryMessage): number {
  // 포털 _history_total 과 같은 셈 — 글 + 근거(도구 · 인자 · 결과).
  return h.content.length + (h.evidence ?? []).reduce((n, e) => n + e.tool.length + (e.args?.length ?? 0) + e.result.length, 0);
}

/** 멀티턴 history: 대화의 기존 메시지 → 계약 형식(오래된 것→최신 순, 이번 발화 제외). 항목은 자르지 않는다.
 *  evidence 를 켜면 어시스턴트 항목에 그 턴의 조회 근거를 싣는다(챗 보내기) — 심의 전 도우미(브리프)는 글만 본다.
 *  images 를 켜면 사람 항목에 그 발화에 올린 그림의 서버 주소를 싣는다(주소뿐이라 합계 상한에 세지 않는다 — 포털도 안 센다).
 *  글이 근거에 밀리지 않게 두 번 담는다 — 1차로 글만 종전처럼 최신부터 합계 상한까지, 2차로 남는 몫에 최근 턴의 근거부터. */
export function buildHistory(messages: Message[], opts: { evidence?: boolean; images?: boolean } = {}): HistoryMessage[] {
  const items = messages
    .filter((m) => !m.error && m.text.trim() !== '')
    .map((m) => ({ role: m.role, content: m.text,
                   evidence: opts.evidence && m.role === 'assistant' ? turnEvidence(m) : [],
                   images: opts.images && m.role === 'user' ? (m.images ?? []) : [] }));
  // 1차 — 최근 것 우선, 뒤에서부터 개수/총량 예산만큼 글을 담는다(종전과 같다).
  const out: HistoryMessage[] = [];
  const evs: HistoryEvidence[][] = [];
  let total = 0;
  for (let i = items.length - 1; i >= 0 && out.length < HISTORY_MAX_ITEMS; i--) {
    if (total + items[i].content.length > HISTORY_MAX_TOTAL_CHARS) break;
    total += items[i].content.length;
    out.push({ role: items[i].role, content: items[i].content,
               ...(items[i].images.length ? { images: items[i].images } : {}) });
    evs.push(items[i].evidence);
  }
  // 2차 — 남는 몫에 최근 턴의 근거부터. 못 드는 턴은 건너뛴다(더 오래된 턴의 작은 근거는 들 수 있다).
  for (let k = 0; k < out.length; k++) {
    if (!evs[k].length) continue;
    const n = sizeOf({ role: 'assistant', content: '', evidence: evs[k] });
    if (total + n > HISTORY_MAX_TOTAL_CHARS) continue;
    total += n;
    out[k].evidence = evs[k];
  }
  return out.reverse();
}
