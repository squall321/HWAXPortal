// 고른 VOC → 심의 원천 근거(delib_opts.evidence)·보강 문장(human_note) 변환 — 두 입구가 같이 쓴다
import type { VocItem } from '../../api/chat.api';
import { EVID_ITEMS } from './handoff';

/** VOC 는 사람이 고른 **원천**이다 — 요약·해석하지 않고 출처와 원문을 그대로 싣는다
 *  (핸드오프 헌법 P1: 브리프에 결론 금지). 길이는 여기서 자르지 않는다 — 엔진이 예산에 맞춰 줄이고 줄였다고 알린다. */
export function vocEvidence(picked: VocItem[]) {
  return picked.map((v) => ({
    source: 'SignalForge VOC',
    tool: 'search_voc',
    args: `keyword=${v.keyword}`,
    result:
      `[${[v.product, v.platform, v.country, v.date].filter(Boolean).join(' · ')}] ${v.text}` +
      (v.url ? ` (원문: ${v.url})` : ''),
  }));
}

/** '고른 VOC 로 화두 보강' 초안 — 사람이 고칠 출발점일 뿐이다. human_note 상한(2,000자) 안쪽. */
export function vocNoteDraft(picked: VocItem[]): string {
  if (!picked.length) return '';
  const lines = picked.map((v) => `- ${v.product || '제품 미상'}: ${v.text.replace(/\s+/g, ' ').slice(0, 140)}`);
  return `현장 고객 불만(VOC) ${picked.length}건을 근거로 함께 본다 — 이 증상들이 화두의 메커니즘과 같은 원인인지부터 따져라.\n${lines.join('\n')}`.slice(0, 1800);
}

/** 대화 근거와 VOC 를 합친다 — **VOC 가 앞**(사람이 직접 고른 것), 합쳐서 포털 상한(EVID_ITEMS)까지. 포털
 *  DelibOpts.evidence 의 max_length 를 넘기면 422 로 심의가 시작조차 안 된다. 잘린 대화 근거 수를 돌려준다.
 *  ⚠ 상한을 여기 숫자로 다시 적지 않는다. 종전 기본값 12 는 포털 상한이 12 이던 때의 값이었고, 상한이 40 · 120 으로
 *  오르는 동안 이 자리만 남아 웹 핸드오프가 12건에서 잘렸다(이어하기 길은 이미 EVID_ITEMS 를 쓴다). */
export function mergeEvidence<T>(voc: T[], conv: T[], cap = EVID_ITEMS): { merged: T[]; droppedConv: number } {
  const merged = [...voc, ...conv].slice(0, cap);
  return { merged, droppedConv: Math.max(0, voc.length + conv.length - cap) };
}
