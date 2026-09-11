// 되묻기 답을 화두에 붙이는 규칙 — '[보강 정보]' 블록 하나로 모으고, 같은 칸을 다시 답하면 덮어쓴다
export const CLARIFY_MARK = '[보강 정보 — 질문자가 답함]';

/** 화두 = 원래 질문 + 보강 블록. 같은 칸을 두 번 답하면 줄이 쌓이지 않고 바뀐다.
 *  화두에 붙이는 이유 — 좌석 추천(recommend_agents)이 그 정보를 보고 다시 뽑고, 매 라운드
 *  프롬프트의 질문에 실리며, 회의록·보고서에도 질문과 함께 남는다. */
export function augmentTopic(topic: string, answers: { label: string; value: string }[]): string {
  const [head, block = ''] = splitTopic(topic);
  const lines = new Map<string, string>();
  for (const l of block.split('\n')) {
    const m = l.match(/^- ([^:]+): (.+)$/);
    if (m) lines.set(m[1].trim(), m[2].trim());
  }
  for (const a of answers) if (a.value.trim()) lines.set(a.label, a.value.trim().replace(/\s+/g, ' '));
  if (!lines.size) return head;
  return `${head}\n\n${CLARIFY_MARK}\n${[...lines].map(([k, v]) => `- ${k}: ${v}`).join('\n')}`;
}

/** [원래 질문, 보강 블록 본문] — 화면이 둘을 따로 보여 준다. */
export function splitTopic(topic: string): [string, string?] {
  const i = topic.indexOf(CLARIFY_MARK);
  if (i < 0) return [topic.trim()];
  return [topic.slice(0, i).trim(), topic.slice(i + CLARIFY_MARK.length).trim()];
}
