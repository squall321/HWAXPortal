// 챗 대화에서 심의로 넘길 원천 근거(도구결과)를 추출한다 — 요약·결론이 아니라 도구가 낸 날것(핸드오프 P1)
import type { Conversation } from '../../types/chat';

// 사전 근거 상한 — 포털 DelibOpts.evidence(max_length)·엔진 _EVID_ITEMS/_EVID_ITEM_MAX 와 **같은 값**
// 이어야 한다. 세 계층 중 하나만 작으면 거기서 잘리고, 잘린 사실은 아무 데도 안 남는다.
export const EVID_ITEMS = 40;
export const EVID_ITEM_MAX = 150000;

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
        source: (a.step || a.tool).slice(0, 200),
        tool: a.tool.slice(0, 80),
        args: (a.detail ?? '').trim().slice(0, 1200) || undefined,
        result: result.slice(0, EVID_ITEM_MAX),
      });
      if (out.length >= EVID_ITEMS) return out; // 백엔드 상한과 동일 — 앞쪽(먼저 호출한 것)을 남긴다
    }
  }
  return out;
}

// 이어하기 — **이전 회차 좌석들이 도구로 조회한 결과**를 원천 근거로 승계한다.
//
// 종전에는 요약·양보 불가 조항·사람 의견만 넘어갔다. 조항을 요약에서 분리한 이유가
// "요약은 자유 텍스트라 빠져도 아무도 모른다" 인데, **수치도 똑같다** — 이전 회차에 DB 로
// 뽑은 값이 결정문 문장에 살아남은 것만 넘어가고 나머지는 사라졌다. 그러면 다음 회차 좌석이
// 같은 것을 다시 조회하거나, 못 하면 기억으로 말한다.
//
// 새 채널을 파지 않는다 — delib_opts.evidence 가 이미 "검증 대상이지 결론이 아닌 원천 데이터"
// 통로이고 엔진이 [e:N] 인용 표지까지 붙여 준다. 출처에 '이전 회차' 를 적어 지위를 밝힌다.
export function priorGatheredEvidence(
  evidence: { source: string; text: string; included: boolean }[] | undefined,
): HandoffEvidence[] {
  const out: HandoffEvidence[] = [];
  const seen = new Set<string>();
  for (const e of evidence ?? []) {
    if (!e?.included) continue;
    const i = (e.source ?? '').indexOf(' · ');
    if (i < 0) continue;
    const seat = e.source.slice(0, i).trim();
    const tool = e.source.slice(i + 3).trim();
    // 도구 이름만 받는다 — '지식카드'·'자유 조회 실패' 같은 한글 라벨은 도구가 아니다.
    if (!/^[a-z][a-z0-9_]{2,79}$/.test(tool)) continue;
    const result = (e.text ?? '').trim();
    if (!result) continue;
    const key = `${tool}|${result.slice(0, 80)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      source: `이전 회차 · ${seat}`.slice(0, 200),
      tool: tool.slice(0, 80),
      result: result.slice(0, EVID_ITEM_MAX),
    });
    if (out.length >= EVID_ITEMS) break;
  }
  return out;
}
