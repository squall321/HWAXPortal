// 경량 구문 강조 토크나이저(순수 함수, 의존성 없음) — 코드 문자열을 토큰 배열로만 변환하고
// 렌더는 TextBlock 이 React 노드로 한다(HTML 미주입). 정밀한 문법이 아니라 "키워드·문자열·
// 주석·숫자 4색"의 근사 강조가 목표 — 스트리밍 중 미완성 코드에도 안전(그냥 다시 토크나이즈).

export type CodeTok = { t: 'kw' | 'str' | 'com' | 'num' | 'key' | 'var' | 'txt'; s: string };

interface Rule {
  re: RegExp; // sticky(y) 필수
  t: CodeTok['t'];
}

const KW = {
  python: new Set(
    'def class return if elif else for while in not and or is None True False import from as with try except finally raise lambda yield pass break continue global nonlocal assert async await del match case'.split(
      ' ',
    ),
  ),
  js: new Set(
    'const let var function return if else for while do switch case break continue new class extends import from export default try catch finally throw async await yield typeof instanceof in of null undefined true false this super interface type enum implements readonly public private protected static void delete keyof as satisfies'.split(
      ' ',
    ),
  ),
  sql: new Set(
    'select from where insert into values update set delete join left right inner outer full on group by order limit offset having as and or not null create table alter drop index primary key foreign references distinct union all exists in like between case when then else end with returning conflict do nothing'.split(
      ' ',
    ),
  ),
  bash: new Set(
    'if then else elif fi for while until do done case esac function in echo export local return exit set unset source cd true false read shift trap'.split(
      ' ',
    ),
  ),
  yaml: new Set('true false null yes no on off'.split(' ')),
} as const;

// 공통 규칙 조각
const R_NUM: Rule = { re: /\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?/y, t: 'num' };
const R_DQ: Rule = { re: /"(?:\\.|[^"\\\n])*"?/y, t: 'str' };
const R_SQ: Rule = { re: /'(?:\\.|[^'\\\n])*'?/y, t: 'str' };

const LANG_RULES: Record<string, { rules: Rule[]; kw?: Set<string>; ci?: boolean }> = {
  python: {
    rules: [
      { re: /#[^\n]*/y, t: 'com' },
      { re: /(?:"""[\s\S]*?"""|'''[\s\S]*?''')/y, t: 'str' },
      R_DQ,
      R_SQ,
      { re: /@\w+/y, t: 'kw' },
      R_NUM,
    ],
    kw: KW.python,
  },
  js: {
    rules: [
      { re: /\/\/[^\n]*/y, t: 'com' },
      { re: /\/\*[\s\S]*?\*\//y, t: 'com' },
      { re: /`(?:\\.|[^`\\])*`?/y, t: 'str' },
      R_DQ,
      R_SQ,
      { re: /0[xX][\da-fA-F]+/y, t: 'num' },
      R_NUM,
    ],
    kw: KW.js,
  },
  json: {
    rules: [{ re: /"(?:\\.|[^"\\\n])*"(?=\s*:)/y, t: 'key' }, R_DQ, R_NUM],
    kw: new Set(['true', 'false', 'null']),
  },
  sql: {
    rules: [{ re: /--[^\n]*/y, t: 'com' }, { re: /\/\*[\s\S]*?\*\//y, t: 'com' }, R_SQ, R_DQ, R_NUM],
    kw: KW.sql,
    ci: true,
  },
  bash: {
    rules: [
      { re: /#[^\n]*/y, t: 'com' },
      R_DQ,
      R_SQ,
      { re: /\$\{[^}\n]*\}|\$\w+/y, t: 'var' },
      R_NUM,
    ],
    kw: KW.bash,
  },
  yaml: {
    rules: [
      { re: /#[^\n]*/y, t: 'com' },
      { re: /[A-Za-z_][\w./-]*(?=\s*:)/y, t: 'key' },
      R_DQ,
      R_SQ,
      R_NUM,
    ],
    kw: KW.yaml,
  },
  generic: {
    rules: [{ re: /#[^\n]*/y, t: 'com' }, { re: /\/\/[^\n]*/y, t: 'com' }, R_DQ, R_SQ, R_NUM],
  },
};

const ALIAS: Record<string, string> = {
  py: 'python',
  python: 'python',
  python3: 'python',
  js: 'js',
  jsx: 'js',
  ts: 'js',
  tsx: 'js',
  javascript: 'js',
  typescript: 'js',
  json: 'json',
  jsonc: 'json',
  sql: 'sql',
  psql: 'sql',
  bash: 'bash',
  sh: 'bash',
  shell: 'bash',
  zsh: 'bash',
  console: 'bash',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'yaml',
  ini: 'yaml',
};

const RE_WORD = /[A-Za-z_$][\w$]*/y;

/** 코드 → 토큰 배열. 알 수 없는 언어는 generic(문자열·주석·숫자만) 근사. */
export function tokenize(lang: string, code: string): CodeTok[] {
  const spec = LANG_RULES[ALIAS[lang.toLowerCase()] ?? ''] ?? LANG_RULES.generic;
  const out: CodeTok[] = [];
  const push = (t: CodeTok['t'], s: string) => {
    const last = out[out.length - 1];
    if (last && last.t === t) last.s += s; // 인접 동일 타입 병합(노드 수 절감)
    else out.push({ t, s });
  };
  let i = 0;
  outer: while (i < code.length) {
    for (const r of spec.rules) {
      r.re.lastIndex = i;
      const m = r.re.exec(code);
      if (m && m.index === i && m[0].length > 0) {
        push(r.t, m[0]);
        i += m[0].length;
        continue outer;
      }
    }
    RE_WORD.lastIndex = i;
    const w = RE_WORD.exec(code);
    if (w && w.index === i) {
      const word = w[0];
      const hit = spec.kw?.has(spec.ci ? word.toLowerCase() : word);
      push(hit ? 'kw' : 'txt', word);
      i += word.length;
      continue;
    }
    push('txt', code[i]);
    i += 1;
  }
  return out;
}

/** 토큰 스트림을 줄 단위로 분해(줄번호 렌더용) — '\n' 은 줄 경계로만 쓰이고 토큰에서 제거. */
export function tokenizeLines(lang: string, code: string): CodeTok[][] {
  const lines: CodeTok[][] = [[]];
  for (const tok of tokenize(lang, code)) {
    const parts = tok.s.split('\n');
    for (let p = 0; p < parts.length; p++) {
      if (p > 0) lines.push([]);
      if (parts[p]) lines[lines.length - 1].push({ t: tok.t, s: parts[p] });
    }
  }
  return lines;
}
