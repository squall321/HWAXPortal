// 이용 통계 화면의 셈 조각 — 막대 자리 · 깨끗한 눈금 · 짧은 수 · 기록 전 구간(컴포넌트 파일과 떼어 node 로 돌려 본다)
import type { Num } from '../api/usage.api';

/** 막대 한 칸 — v 가 null 이면 그리지 않는다(기록 전) */
export interface Col {
  i: number;
  x: number;
  w: number;
  h: number;
  v: Num;
}

/** 1 · 2 · 5 × 10^k 가운데 max 이상인 가장 작은 값 — 눈금 꼭대기(0 이면 1) */
export function niceMax(max: number): number {
  if (!(max > 0)) return 1;
  const p = 10 ** Math.floor(Math.log10(max));
  for (const m of [1, 2, 5, 10]) if (m * p >= max) return m * p;
  return 10 * p;
}

/** 1,284 · 12.9K · 3.4M — 큰 수만 줄인다(눈금 · 타일 값) */
export function compact(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e6) return `${(n / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, '')}M`;
  if (a >= 1e4) return `${(n / 1e3).toFixed(a >= 1e5 ? 0 : 1).replace(/\.0$/, '')}K`;
  return n.toLocaleString('en-US');
}

/**
 * 막대 자리. 칸 폭 = 그림 폭 / 칸 수, 막대는 칸에서 틈을 뺀 폭(최대 24px — 칸을 다 채우지 않는다).
 * 틈은 칸이 넉넉하면 2px, 촘촘하면(400일) 칸의 1/4 — 이웃 막대가 붙어 한 덩이로 보이지 않게.
 */
export function columns(
  values: Num[],
  width: number,
  height: number,
  top: number,
  maxBar = 24,
): { cols: Col[]; slot: number } {
  const n = Math.max(1, values.length);
  const slot = width / n;
  const gap = slot >= 8 ? 2 : slot / 4;
  const w = Math.max(0.5, Math.min(maxBar, slot - gap));
  const cols = values.map((v, i) => ({
    i,
    x: i * slot + (slot - w) / 2,
    w,
    h: v == null || top <= 0 ? 0 : Math.max(v > 0 ? 1 : 0, (Math.min(v, top) / top) * height),
    v,
  }));
  return { cols, slot };
}

/** 위 모서리만 둥근 막대(밑은 기준선에 각지게) — r 은 4px 를 넘지 않고 막대 폭 · 높이의 절반을 넘지 않는다 */
export function roundedTop(x: number, base: number, w: number, h: number): string {
  if (h <= 0) return '';
  const r = Math.max(0, Math.min(4, w / 2, h));
  const y = base - h;
  return (
    `M${x},${base}V${y + r}` +
    (r ? `Q${x},${y} ${x + r},${y}` : '') +
    `H${x + w - r}` +
    (r ? `Q${x + w},${y} ${x + w},${y + r}` : '') +
    `V${base}Z`
  );
}

/** 이어진 null 구간(처음 · 끝 칸 번호) — 그림에 '기록 전' 띠로 보인다 */
export function nullRuns(values: Num[]): { start: number; end: number }[] {
  const out: { start: number; end: number }[] = [];
  values.forEach((v, i) => {
    if (v != null) return;
    const last = out[out.length - 1];
    if (last && last.end === i - 1) last.end = i;
    else out.push({ start: i, end: i });
  });
  return out;
}

/** 값이 있는 칸의 최댓값(없으면 0) */
export function maxOf(values: Num[]): number {
  return values.reduce<number>((m, v) => (v != null && v > m ? v : m), 0);
}

/** 2026-11-02 → 11-02 */
export function shortDay(iso: string): string {
  return iso.length >= 10 ? iso.slice(5, 10) : iso;
}

/** 그림 양 끝의 날 — 해가 같으면 월-일, 기간이 해를 넘으면 해까지(400일이면 09-29 가 어느 해인지 모른다) */
export function edgeLabels(labels: string[]): [string, string] {
  const first = labels[0] ?? '';
  const last = labels[labels.length - 1] ?? '';
  return first.slice(0, 4) === last.slice(0, 4) ? [shortDay(first), shortDay(last)] : [first, last];
}

/** 앞쪽에 이어진 기록 전 줄을 한 줄로 접는다 — 남은 줄과 접힌 줄의 처음 · 끝 키(없으면 null) */
export function foldLeading<T>(
  rows: T[],
  isNull: (r: T) => boolean,
  key: (r: T) => string,
): { span: [string, string] | null; rest: T[] } {
  let k = 0;
  while (k < rows.length && isNull(rows[k])) k += 1;
  return { span: k ? [key(rows[0]), key(rows[k - 1])] : null, rest: rows.slice(k) };
}

/** 0.667 → 67% · null → — */
export function pct(r: number | null | undefined): string {
  return r == null ? '—' : `${Math.round(r * 100)}%`;
}

/** 대화 칸(날 × 종류 × 출처)을 기간의 날마다 합친 수 — 빠진 날은 0 */
export function perDay(rows: { day: string; n: number }[], axis: string[]): number[] {
  const by = new Map<string, number>();
  for (const r of rows) by.set(r.day, (by.get(r.day) ?? 0) + r.n);
  return axis.map((d) => by.get(d) ?? 0);
}
