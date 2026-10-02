// 쓰는 CSS 변수(var(--x))가 어딘가에 정의돼 있는지 본다 — 없으면 폴백(대개 라이트 테마 값)으로 조용히 떨어져 흰 패널이 생긴다
// 사용: node scripts/check-css-vars.mjs  (종료코드 1 = 정의 안 된 변수 있음). docs/ui-refresh 단계 0 · D-6.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

// fileURLToPath — URL.pathname 은 한글 등 비ASCII 경로를 퍼센트 인코딩한 채 돌려줘 readdir 이 실패한다
const SRC = fileURLToPath(new URL('../src/', import.meta.url));

function walk(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : /\.(css|tsx?|jsx?)$/.test(n) ? [p] : [];
  });
}

const defined = new Set();
const used = new Map(); // name -> [file:line]
for (const file of walk(SRC)) {
  const lines = readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, i) => {
    // 정의 — CSS `--x:` 와 인라인 스타일 객체 `'--x':` 둘 다
    for (const m of line.matchAll(/(?:^|[\s{;'"(])(--[a-zA-Z0-9-]+)\s*['"]?\s*:/g)) defined.add(m[1]);
    for (const m of line.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)/g)) {
      const at = `${relative(SRC, file)}:${i + 1}`;
      used.set(m[1], [...(used.get(m[1]) ?? []), at]);
    }
  });
}

const missing = [...used.keys()].filter((n) => !defined.has(n)).sort();
if (missing.length) {
  console.error(`✗ 정의 안 된 CSS 변수 ${missing.length}개 — 폴백으로 떨어진다:`);
  for (const n of missing) console.error(`  ${n}  ← ${used.get(n).slice(0, 3).join(', ')}${used.get(n).length > 3 ? ' …' : ''}`);
  process.exit(1);
}
console.log(`✓ CSS 변수 ${used.size}개 모두 정의됨`);
