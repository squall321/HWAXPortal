// 이용 통계의 작은 그림 — 한 계열 막대(마우스 · 화살표 키로 값 보기 + 표로 보기) · 줄 안 막대 띠 · 수 타일. 인라인 SVG 에 CSS 토큰만 쓴다
import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
} from 'react';
import type { Num } from '../../api/usage.api';
import {
  columns,
  compact,
  maxOf,
  niceMax,
  nullRuns,
  roundedTop,
  edgeLabels,
} from '../../lib/usageChart';

const LEFT = 40; // y 눈금 자리
const RIGHT = 6;
const TOP = 8;
const BOTTOM = 20; // x 눈금 자리 — 그림 높이에 넣는다(카드 안에 작은 세로 스크롤이 생기지 않게)

/** 그 상자의 폭(px) — 처음(그리고 서버에서 그릴 때)은 fallback 이다 */
function useWidth(ref: RefObject<HTMLElement>, fallback: number): number {
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(120, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

function valueText(v: Num, unit: string): string {
  return v == null ? '기록 전' : `${v.toLocaleString('en-US')}${unit}`;
}

/**
 * 날 · 주마다 한 계열 막대. 한 계열이라 범례는 없고 제목이 무엇인지 말한다. null 칸은 그리지 않고 '기록 전' 띠로 둔다(0 이 아니다).
 * partial 칸(기간에 걸치거나 아직 끝나지 않은 주)은 흐리게. 값은 마우스 · 화살표 키의 말풍선과 '표로 보기' 에 늘 있다.
 */
export function ColumnChart({
  title,
  values,
  labels,
  unit = '',
  partial,
  height = 110,
}: {
  title: string;
  values: Num[];
  labels: string[];
  unit?: string;
  partial?: boolean[];
  height?: number;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const width = useWidth(wrap, 640);
  const [hi, setHi] = useState<number | null>(null);
  const plotW = Math.max(40, width - LEFT - RIGHT);
  const max = maxOf(values);
  const top = niceMax(max);
  const { cols, slot } = columns(values, plotW, height, top);
  const base = TOP + height;
  const n = values.length;
  const shown = values.filter((v) => v != null).length;
  const [firstLabel, lastLabel] = edgeLabels(labels);
  const pick = (e: PointerEvent<SVGSVGElement>) => {
    const i = Math.floor((e.clientX - e.currentTarget.getBoundingClientRect().left - LEFT) / slot);
    setHi(i >= 0 && i < n ? i : null);
  };
  const key = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const d = e.key === 'ArrowRight' ? 1 : -1;
      setHi((h) => Math.min(n - 1, Math.max(0, h == null ? (d > 0 ? 0 : n - 1) : h + d)));
    } else if (e.key === 'Escape') setHi(null);
  };
  const tipX =
    hi == null ? 0 : Math.min(width - 60, Math.max(60, LEFT + cols[hi].x + cols[hi].w / 2));
  return (
    <figure className="uc">
      <figcaption>{title}</figcaption>
      <div
        ref={wrap}
        className="uc-plot"
        tabIndex={0}
        role="img"
        aria-label={`${title} — ${labels[0] ?? ''} ~ ${labels[n - 1] ?? ''}, 가장 큰 값 ${max.toLocaleString('en-US')}${unit}`}
        onKeyDown={key}
        onBlur={() => setHi(null)}
      >
        <svg
          width={width}
          height={TOP + height + BOTTOM}
          onPointerMove={pick}
          onPointerLeave={() => setHi(null)}
          aria-hidden="true"
        >
          <line className="uc-grid" x1={LEFT} x2={LEFT + plotW} y1={TOP} y2={TOP} />
          <line className="uc-base" x1={LEFT} x2={LEFT + plotW} y1={base} y2={base} />
          <text className="uc-axis" x={LEFT - 6} y={TOP + 4} textAnchor="end">
            {compact(top)}
          </text>
          <text className="uc-axis" x={LEFT - 6} y={base} textAnchor="end">
            0
          </text>
          {nullRuns(values).map((r) => {
            const w = (r.end - r.start + 1) * slot;
            return (
              <g key={`gap-${r.start}`}>
                <rect
                  className="uc-gap"
                  x={LEFT + r.start * slot}
                  y={TOP}
                  width={w}
                  height={height}
                />
                {w >= 44 && (
                  <text
                    className="uc-gap-label"
                    x={LEFT + r.start * slot + w / 2}
                    y={TOP + height / 2 + 4}
                    textAnchor="middle"
                  >
                    기록 전
                  </text>
                )}
              </g>
            );
          })}
          <g transform={`translate(${LEFT},0)`}>
            {cols.map((c) =>
              c.h > 0 ? (
                <path
                  key={c.i}
                  className={`uc-bar${c.i === hi ? ' is-hi' : ''}${partial?.[c.i] ? ' is-partial' : ''}`}
                  d={roundedTop(c.x, base, c.w, c.h)}
                />
              ) : null,
            )}
          </g>
          {n > 0 && (
            <>
              <text className="uc-axis" x={LEFT} y={base + 15} textAnchor="start">
                {firstLabel}
              </text>
              {n > 1 && (
                <text className="uc-axis" x={LEFT + plotW} y={base + 15} textAnchor="end">
                  {lastLabel}
                </text>
              )}
            </>
          )}
        </svg>
        {hi != null && (
          <div className="uc-tip" style={{ left: tipX }}>
            <b>{valueText(values[hi], unit)}</b>
            <span>
              {labels[hi]}
              {partial?.[hi] ? ' · 일부만' : ''}
            </span>
          </div>
        )}
      </div>
      {shown === 0 && <p className="uc-empty">이 기간에는 기록이 없다.</p>}
      <details className="uc-table">
        <summary>표로 보기</summary>
        <div className="adm-table-wrap">
          <table className="adm-table">
            <tbody>
              {labels.map((l, i) => (
                <tr key={l}>
                  <td className="adm-nowrap">
                    {l}
                    {partial?.[i] ? ' (일부만)' : ''}
                  </td>
                  <td className="adm-num">{valueText(values[i], unit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** 표의 한 줄 안에 들어가는 날마다 막대 띠(눈금 없음) — 수는 그 줄의 칸이 말한다 */
export function Spark({ values, label }: { values: Num[]; label: string }) {
  const W = 120;
  const H = 22;
  const { cols } = columns(values, W, H, niceMax(maxOf(values)), 6);
  return (
    <svg className="uc-spark" width={W} height={H} role="img" aria-label={label}>
      <title>{label}</title>
      {cols.map((c) =>
        c.h > 0 ? <rect key={c.i} x={c.x} y={H - c.h} width={c.w} height={c.h} /> : null,
      )}
    </svg>
  );
}

/** 수 타일 — 이름 · 값(큰 수는 줄여 쓴다) · 덧붙임 */
export function StatTile({
  label,
  value,
  sub,
}: {
  label: string;
  value: number | null | undefined;
  sub?: string;
}) {
  return (
    <div className="uc-tile">
      <div className="uc-tile-label">{label}</div>
      <div className="uc-tile-value">{value == null ? '—' : compact(value)}</div>
      {sub && <div className="uc-tile-sub">{sub}</div>}
    </div>
  );
}
