// 챗 답 끝의 근거 블록(에이전트 서버가 실행 기록으로 붙인다)을 본문과 갈라 접은 칸으로 그리기 위한 도우미

// 에이전트 서버 app.py 의 _EVIDENCE_MARK 와 같은 글이어야 한다 — 포털 시험(test_chat_evidence_fold)이 두 리포를 맞대 본다.
export const EVIDENCE_MARK = '**근거** — 이번 답변이 실제로 조회한 것';

// 블록은 "\n\n---\n" + 표지로 시작해 답의 맨 끝에 붙는다(app.py _evidence_block — 두 길 모두 text += _ev).
const SPLIT = `\n---\n${EVIDENCE_MARK}`;

export interface SplitEvidence {
  body: string;
  evidence: string;
  calls: number;
  unsourced: number;
}

/** 답 → 본문 · 근거 블록. 블록이 없으면 본문 그대로다. 저장 · 복사 · 다음 턴 출처 판정은 나누지 않은 원문을 쓴다 — 여기는 그리기만 한다. */
export function splitEvidence(text: string): SplitEvidence {
  const i = text.lastIndexOf(SPLIT);
  if (i < 0) return { body: text, evidence: '', calls: 0, unsourced: 0 };
  const body = text.slice(0, i).replace(/\s+$/, '');
  const evidence = text.slice(i + SPLIT.length).replace(/^\n+/, '');
  let calls = 0;
  let unsourced = 0;
  for (const line of evidence.split('\n')) {
    const more = /^- … 외 (\d+)건/.exec(line);
    if (more) calls += Number(more[1]);
    else if (line.startsWith('- `')) calls += 1;
    if (line.startsWith('> ⚠')) {
      // 블록은 6건까지 보이고 넘으면 '총 N건' 을 적는다 — 그 수가 있으면 그것을, 없으면 보인 값의 수를 센다.
      const total = /총 (\d+)건/.exec(line);
      unsourced = total ? Number(total[1]) : (line.match(/`[^`]+`/g) ?? []).length;
    }
  }
  return { body, evidence, calls, unsourced };
}
