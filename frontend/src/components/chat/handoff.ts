// 챗 대화에서 심의로 넘길 원천 근거(도구결과)를 추출한다 — 요약·결론이 아니라 도구가 낸 날것(핸드오프 P1)
import type { Conversation } from '../../types/chat';

// 심의로 넘기는 원천 근거 한 항목 — 백엔드 delib_opts.evidence 스키마와 맞춘다(agent-server 가 재클램프).
export interface HandoffEvidence {
  source: string;
  tool?: string;
  args?: string;
  result: string;
}

// 대화의 도구 호출 활동(activity[])에서 결과 미리보기를 뽑아 근거 항목으로 만든다.
// 어시스턴트의 '종합 답변'(result 텍스트)은 결론에 가까워 넣지 않는다 — P1(원천 데이터만, 결론 금지).
// 심의는 이 날것을 '검증 대상'으로 받아 재검토한다. 중복(같은 도구·같은 결과 앞머리)은 하나만.
export function conversationEvidence(conv: Conversation): HandoffEvidence[] {
  const out: HandoffEvidence[] = [];
  const seen = new Set<string>();
  for (const m of conv.messages) {
    for (const a of m.activity ?? []) {
      if (!a.tool) continue;
      // 날것(result_full)이 있으면 그것을 쓴다 — result_preview 는 활동 패널용 220자라
      // 심의에 넘기면 표의 첫 줄만 간다. 서버가 핸드오프용으로 따로 실어 보낸다.
      const result = (a.result_full ?? a.result_preview ?? '').trim();
      if (!result) continue; // 결과 없는 호출은 근거가 아니다
      const key = `${a.tool}|${result.slice(0, 80)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        source: (a.step || a.tool).slice(0, 120),
        tool: a.tool.slice(0, 80),
        args: (a.detail ?? '').trim().slice(0, 400) || undefined,
        result: result.slice(0, 2000),
      });
      if (out.length >= 12) return out; // 백엔드 상한과 동일 — 앞쪽(먼저 호출한 것)을 남긴다
    }
  }
  return out;
}
