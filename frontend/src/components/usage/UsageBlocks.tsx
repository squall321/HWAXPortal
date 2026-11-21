// 이용 통계 화면의 틀 — 칸(Block) · 카드(Card) · 표(Table). 화면(UsageStatsPage)과 접어 둔 표의 카드(UsageFoldCards)가 함께 쓴다
import type { ReactNode } from 'react';
import type { Section } from '../../api/usage.api';

/** 칸 하나 — 못 읽었으면 그 까닭, 접어 둔 표가 아직 없으면(pending) 그렇다는 말, 아니면 내용과 읽는 법(note) */
export function Block({
  sec,
  title,
  children,
}: {
  sec?: Section<unknown>;
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="uc-block">
      {title && <h3>{title}</h3>}
      {!sec ? (
        <p className="adm-hint">서버가 이 칸을 내지 않았다 — 포털이 이 화면보다 옛 판이다.</p>
      ) : sec.error ? (
        <p className="adm-err">{sec.note}</p>
      ) : sec.pending ? (
        <p className="adm-hint">{sec.note}</p>
      ) : (
        <>
          {children}
          <p className="uc-note">{sec.note}</p>
        </>
      )}
    </div>
  );
}

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="uc-card" aria-label={title}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function Table({
  head,
  rows,
  empty = '이 기간에는 없다.',
}: {
  head: string[];
  rows: ReactNode[][];
  empty?: string;
}) {
  if (!rows.length) return <p className="uc-empty">{empty}</p>;
  return (
    <div className="adm-table-wrap">
      <table className="adm-table">
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={h} className={i ? 'adm-num' : undefined}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((cell, j) => (
                <td key={j} className={j ? 'adm-num' : undefined}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
