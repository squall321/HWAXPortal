// 마크다운 경량 파서(순수 함수, React 무의존) — LLM 출력의 제목/구분선/표/목록/인용/인라인 서식을
// 블록 AST 로 변환한다. HTML 문자열을 만들지 않으므로(렌더는 TextBlock 이 React 노드로) XSS 표면이 없다.
// 스트리밍 중 재파싱을 전제로 한 관대한 문법 — 미완성 구문은 일반 문단으로 남는다.

export type Inline =
  | { t: 'text'; s: string }
  | { t: 'code'; s: string }
  | { t: 'bold'; s: string }
  | { t: 'em'; s: string }
  | { t: 'strike'; s: string }
  | { t: 'link'; s: string; href: string };

export type ListItem = { depth: number; text: string };

export type Block =
  | { t: 'p'; text: string }
  | { t: 'h'; level: number; text: string }
  | { t: 'hr' }
  | { t: 'quote'; text: string }
  | { t: 'list'; ordered: boolean; start: number; items: ListItem[] }
  | { t: 'table'; head: string[]; align: ('l' | 'c' | 'r')[]; rows: string[][] };

const RE_HEADING = /^(#{1,6})\s+(.*)$/;
const RE_HR = /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/;
const RE_LIST = /^(\s*)(?:([-*+])|(\d{1,3})[.)])\s+(.*)$/;
const RE_QUOTE = /^\s*>\s?(.*)$/;
// 표 구분행: |---|:--:|--- 류 — 셀마다 최소 하이픈 1개(콜론 정렬 허용)
const RE_TABLE_SEP = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

function splitCells(line: string): string[] {
  let s = line.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|')) s = s.slice(0, -1);
  // 인라인 코드 안의 | 는 셀 구분자가 아니다 — 백틱 짝 안쪽을 잠시 치환 후 복원.
  // 센티널은 유니코드 사설영역 문자 — LLM 일반 출력에 등장하지 않고 제어문자 lint 도 회피.
  const guards: string[] = [];
  s = s.replace(/`[^`\n]*`/g, (m) => {
    guards.push(m);
    return `\uE000${guards.length - 1}\uE000`;
  });
  return s.split('|').map((c) => {
    const restored = c.replace(/\uE000(\d+)\uE000/g, (_, i) => guards[Number(i)] ?? '');
    return restored.trim();
  });
}

function sepAligns(line: string): ('l' | 'c' | 'r')[] {
  return splitCells(line).map((c) => {
    const left = c.startsWith(':');
    const right = c.endsWith(':');
    if (left && right) return 'c';
    if (right) return 'r';
    return 'l';
  });
}

/** 텍스트(코드펜스 제거 후)를 블록 목록으로 파싱. */
export function parseBlocks(text: string): Block[] {
  const lines = text.split('\n');
  const blocks: Block[] = [];
  let para: string[] = [];

  const flushPara = () => {
    // 앞뒤 빈 줄만 제거 — 문단 내부 줄바꿈은 보존(pre-wrap 렌더)
    while (para.length && para[0].trim() === '') para.shift();
    while (para.length && para[para.length - 1].trim() === '') para.pop();
    if (para.length) blocks.push({ t: 'p', text: para.join('\n') });
    para = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    const h = line.match(RE_HEADING);
    if (h) {
      flushPara();
      blocks.push({ t: 'h', level: h[1].length, text: h[2].trim() });
      continue;
    }

    if (RE_HR.test(line)) {
      // "- 항목" 목록과 구분: hr 은 기호만으로 이뤄진 줄(RE_HR 이 이미 보장)
      flushPara();
      blocks.push({ t: 'hr' });
      continue;
    }

    // 표: 이 줄에 | 가 있고 다음 줄이 구분행이면 표 시작
    if (line.includes('|') && i + 1 < lines.length && RE_TABLE_SEP.test(lines[i + 1]) && lines[i + 1].includes('-')) {
      flushPara();
      const head = splitCells(line);
      const align = sepAligns(lines[i + 1]);
      const rows: string[][] = [];
      let j = i + 2;
      for (; j < lines.length; j++) {
        if (!lines[j].includes('|') || !lines[j].trim()) break;
        rows.push(splitCells(lines[j]));
      }
      blocks.push({ t: 'table', head, align, rows });
      i = j - 1;
      continue;
    }

    const li = line.match(RE_LIST);
    if (li) {
      flushPara();
      const ordered = li[3] !== undefined;
      const start = ordered ? Number(li[3]) : 1;
      const items: ListItem[] = [];
      let j = i;
      for (; j < lines.length; j++) {
        const m = lines[j].match(RE_LIST);
        if (m && (m[3] !== undefined) === ordered) {
          items.push({ depth: Math.min(2, Math.floor((m[1] ?? '').length / 2)), text: m[4] });
        } else if (lines[j].match(/^\s{2,}\S/) && items.length) {
          // 들여쓴 연속행은 직전 항목에 붙인다
          items[items.length - 1].text += '\n' + lines[j].trim();
        } else {
          break;
        }
      }
      blocks.push({ t: 'list', ordered, start, items });
      i = j - 1;
      continue;
    }

    const q = line.match(RE_QUOTE);
    if (q) {
      flushPara();
      const qlines: string[] = [q[1]];
      let j = i + 1;
      for (; j < lines.length; j++) {
        const m = lines[j].match(RE_QUOTE);
        if (!m) break;
        qlines.push(m[1]);
      }
      blocks.push({ t: 'quote', text: qlines.join('\n') });
      i = j - 1;
      continue;
    }

    if (line.trim() === '') {
      flushPara();
      continue;
    }
    para.push(line);
  }
  flushPara();
  return blocks;
}

// 인라인: 코드 > 볼드 > 이탤릭 > 취소선 > 링크(http/https 만) — 알터네이션 순서가 우선순위.
// 이탤릭은 여는 * 뒤 비공백 요구(곱셈 기호 오탐 방지). 미완성 구문은 일반 텍스트로 남는다.
const RE_INLINE =
  /(`[^`\n]+`)|(\*\*[^*\n]+?\*\*)|(\*(?=\S)[^*\n]+?\*)|(~~[^~\n]+?~~)|(\[[^\]\n]+\]\(https?:\/\/[^\s)]+\))/g;

export function parseInline(s: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  RE_INLINE.lastIndex = 0;
  for (let m = RE_INLINE.exec(s); m; m = RE_INLINE.exec(s)) {
    if (m.index > last) out.push({ t: 'text', s: s.slice(last, m.index) });
    const tok = m[0];
    if (m[1]) out.push({ t: 'code', s: tok.slice(1, -1) });
    else if (m[2]) out.push({ t: 'bold', s: tok.slice(2, -2) });
    else if (m[3]) out.push({ t: 'em', s: tok.slice(1, -1) });
    else if (m[4]) out.push({ t: 'strike', s: tok.slice(2, -2) });
    else {
      const lm = tok.match(/^\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)$/);
      if (lm) out.push({ t: 'link', s: lm[1], href: lm[2] });
      else out.push({ t: 'text', s: tok });
    }
    last = m.index + tok.length;
  }
  if (last < s.length) out.push({ t: 'text', s: s.slice(last) });
  return out;
}
