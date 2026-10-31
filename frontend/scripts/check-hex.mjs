// tokens.css 밖의 고유 hex 색 수를 세어 기준 파일(hex-baseline.json)보다 늘면 빌드를 막는 래칫 — 줄면 기준을 낮추라고 알린다
// 사용: node scripts/check-hex.mjs           (종료코드 1 = 기준보다 늘었다)
//       node scripts/check-hex.mjs --update  (줄었을 때 기준을 지금 값으로 낮춘다 — 올리지는 않는다)
// docs/ui-refresh 단계 3 · D-25. 색은 tokens.css 의 토큰으로 쓴다 — 화면마다 고유 hex 를 박으면 테마 하나를 고칠 때 모든 파일을 뒤진다.
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

// fileURLToPath — URL.pathname 은 한글 등 비ASCII 경로를 퍼센트 인코딩한 채 돌려줘 readdir 이 실패한다(check-css-vars 와 같다)
const SRC = fileURLToPath(new URL('../src/', import.meta.url));
const BASELINE = fileURLToPath(new URL('./hex-baseline.json', import.meta.url));
const TOKENS = join('styles', 'tokens.css');
// #rgb · #rgba · #rrggbb · #rrggbbaa. 대소문자는 같은 색으로 센다.
const HEX = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b/g;
// 같은 색은 한 값으로 센다 — 소문자로 바꾸고 짧은 꼴(#rgb · #rgba)은 긴 꼴(#rrggbb · #rrggbbaa)로 편다. 종전엔 기준에 #fff 가 있어도
// #ffffff 를 새 색으로 세어, 같은 흰색을 긴 꼴로 쓴 가지(HA-20 패널의 chat.css)를 합치면 빌드가 90 → 91 로 멈췄다. 기준 파일의 값도 편다.
const norm = (v) => {
  const h = v.slice(1).toLowerCase();
  return `#${h.length <= 4 ? [...h].map((c) => c + c).join('') : h}`;
};

function walk(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : /\.(css|[cm]?[jt]sx?)$/.test(n) ? [p] : [];
  });
}

const seen = new Map(); // 값 -> [file:line]
let places = 0;
for (const file of walk(SRC)) {
  const rel = relative(SRC, file);
  if (rel === TOKENS) continue;
  readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
    for (const m of line.matchAll(HEX)) {
      const v = norm(m[0]);
      seen.set(v, [...(seen.get(v) ?? []), `${rel}:${i + 1}`]);
      places += 1;
    }
  });
}

const values = [...seen.keys()].sort();
const base = JSON.parse(readFileSync(BASELINE, 'utf8'));
const allowed = new Set((base.values ?? []).map(norm));
const save = (note) =>
  writeFileSync(BASELINE, JSON.stringify({ note, unique: values.length, places, values }, null, 2) + '\n');

if (values.length > base.unique) {
  const added = values.filter((v) => !allowed.has(v));
  console.error(`✗ tokens.css 밖의 고유 hex 가 ${base.unique} → ${values.length}개로 늘었다 — 색은 styles/tokens.css 의 토큰(var(--…))으로 쓴다. 기준에 없는 값은 아래와 같다.`);
  for (const v of added) console.error(`  ${v}  ← ${seen.get(v).slice(0, 3).join(', ')}${seen.get(v).length > 3 ? ' …' : ''}`);
  console.error('  정말 새 색이 필요하면 tokens.css 에 토큰으로 더하거나, 까닭을 커밋에 적고 scripts/hex-baseline.json 을 손으로 고친다.');
  process.exit(1);
}
if (process.argv.includes('--update')) {
  save(base.note); // 늘었으면 위에서 이미 끝났다 — 여기 오면 같거나 줄었다(값 목록도 지금 것으로)
  console.log(`✓ 기준 ${base.unique} → ${values.length}개(${places}곳)`);
} else if (values.length < base.unique) {
  console.log(`✓ tokens.css 밖의 고유 hex ${values.length}개(${places}곳) — 기준 ${base.unique}개보다 줄었다. 래칫을 내린다: node scripts/check-hex.mjs --update`);
} else {
  console.log(`✓ tokens.css 밖의 고유 hex ${values.length}개(${places}곳) — 기준 ${base.unique}개 이내`);
}
