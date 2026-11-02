// '온톨로지 먼저 보기' 에서 사람이 고른 행 → 심의 원천 근거(delib_opts.evidence) — 호출 하나에 근거 한 항목(docs/ontology-first M4)
import type { OntoCall, OntoPreview } from '../../api/chat.api';
import type { HandoffEvidence } from './handoff';

/** 근거 글 머리 — 근거는 포털이 줄인 행이다(도구 원문이 아니다). 근거 표지의 지문도 이 글의 것이다. */
export const ONTO_REDUCED = '[포털이 줄인 행 — 도구 원문이 아니다]';

/** 패널이 부모에게 알리는 것 — 근거 항목(호출 하나에 한 항목)과 고른 수. */
export interface OntoChoice {
  evidence: HandoffEvidence[];
  rows: number;
  anchor: boolean;
}
export const EMPTY_ONTO: OntoChoice = { evidence: [], rows: 0, anchor: false };

function argsText(c: OntoCall): string {
  return Object.entries(c.args)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join(',') : String(v)}`)
    .join(' · ');
}

/** 고른 것 → 근거 항목. 닻(주제 과제 자신)을 골랐으면 풀이 호출의 항목 하나, 이웃 행을 하나라도 골랐으면 이웃 호출의 항목 하나 — 행마다 항목을
 *  만들지 않는다(근거 상한 120 · 과제 인사이트 근거 표지 60 을 먹어 지정 도구 표지를 밀어낸다). 행은 화면에 보인 차례대로 싣는다.
 *  이웃 항목은 주제 과제를 고른 때만 싣는다 — 그 인자(object_id — 허브 id) · 머리(「key」) · 행의 관계 글('이 과제')이 주제 과제를 가리킨다. 고르지
 *  않은 주제 과제의 key · 허브 id 가 말없이 나가지 않게(반대 검토 11-02 — docs/ontology-first OF-29). 화면은 이웃 행을 고르면 주제 과제 칸을 보이게
 *  함께 고르고, 주제 과제를 빼면 이웃 행도 뺀다(OntoFirstPanel). */
export function ontoEvidence(p: OntoPreview | null, pickAnchor: boolean, pickedIds: readonly string[]): HandoffEvidence[] {
  if (!p || p.state !== 'ok' || !p.anchor || !p.calls?.resolve) return [];
  const source = `온톨로지 먼저 · ${p.canonical?.label ?? '정본 허브'}`;
  const out: HandoffEvidence[] = [];
  if (pickAnchor) {
    out.push({
      source,
      tool: p.calls.resolve.tool,
      args: argsText(p.calls.resolve),
      result: `${ONTO_REDUCED} 심의 주제 과제 — 정본 허브에서 하나로 풀렸다\n${p.anchor.line}`,
    });
  }
  const want = new Set(pickedIds);
  const rows = (p.rows ?? []).filter((r) => want.has(r.id));
  if (pickAnchor && rows.length && p.calls.neighbors) {
    out.push({
      source,
      tool: p.calls.neighbors.tool,
      args: argsText(p.calls.neighbors),
      result:
        `${ONTO_REDUCED} 주제 과제 「${p.anchor.key}」의 한 걸음 이웃 가운데 사람이 고른 ${rows.length}행` +
        `(보인 ${p.shown ?? rows.length} · 전체 ${p.total ?? rows.length}${p.hub_truncated ? ' · 허브가 자른 답' : ''})\n` +
        rows.map((r) => r.line).join('\n'),
    });
  }
  return out;
}
