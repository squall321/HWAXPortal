// 전문가 조직도 공용 조각 — 루트→분류→도메인→그룹 탐색 상태, 왼쪽 트리, 가운데 개요, 빵부스러기(챗·심의 공용)
import { type ReactNode } from 'react';
import { groupLabel, type OrgNav } from './orgNav';
import { pathOf, type CategoryNode, type RootNode } from './personaCatalog';

/** 도메인 옆에 붙일 작은 배지(예: 심의 좌석 조직도의 'N석'). */
type Badge = (domainCode: string) => ReactNode;

/** 왼쪽 트리 — 루트는 머리글, 분류는 접힘, 도메인은 누르면 사람들·펼치면 그룹. */
export function OrgTreeNav({ nav, total, badge }: { nav: OrgNav; total: number; badge?: Badge }) {
  const { tree, q, dom, grp, cat } = nav;
  return (
    <nav className="pv-tree" aria-label="조직도">
      <button type="button" className={`pv-tree-root${dom === null && cat === null && !q.trim() ? ' is-on' : ''}`} onClick={nav.reset}>
        전체 <span className="pv-n">{total}</span>
      </button>
      {tree.map((r: RootNode) => (
        <div key={r.id} className="ot-root">
          <div className="ot-root-head">
            {r.label} <span className="pv-n">{r.count}</span>
          </div>
          <ul className="pv-tree-list">
            {r.categories.map((c) => {
              const closed = nav.closedCats.includes(c.id);
              const single = c.domains.length === 1;
              return (
                <li key={c.id} className="pv-tree-item">
                  <div className={`pv-tree-row ot-cat${cat === c.id && !dom ? ' is-on' : ''}`}>
                    {!single ? (
                      <button type="button" className="pv-twist" onClick={() => nav.toggleCat(c.id)}
                        aria-expanded={!closed} aria-label={`${c.label} ${closed ? '펼치기' : '접기'}`}>
                        {closed ? '▸' : '▾'}
                      </button>
                    ) : (
                      <span className="pv-twist" aria-hidden="true">·</span>
                    )}
                    <button type="button" className="pv-tree-name ot-cat-name" onClick={() => nav.gotoCategory(c)}>
                      {c.label}
                      {single && badge?.(c.domains[0].code)}
                      <span className="pv-n">{c.count}</span>
                    </button>
                  </div>
                  {!closed && !single && (
                    <ul className="pv-tree-sub ot-doms">
                      {c.domains.map((d) => {
                        const expanded = nav.openDoms.includes(d.code);
                        return (
                          <li key={d.code}>
                            <div className={`pv-tree-row${dom === d.code ? ' is-on' : ''}`}>
                              <button type="button" className="pv-twist" onClick={() => nav.toggleDom(d.code)}
                                aria-expanded={expanded} aria-label={`${d.label} ${expanded ? '접기' : '펼치기'}`}>
                                {expanded ? '▾' : '▸'}
                              </button>
                              <button type="button" className="pv-tree-name" onClick={() => nav.gotoDomain(d.code)}>
                                {d.label}
                                {badge?.(d.code)}
                                <span className="pv-n">{d.agents.length}</span>
                              </button>
                            </div>
                            {expanded && (
                              <ul className="pv-tree-sub">
                                {d.groups.map((g) => (
                                  <li key={g.code || '_loose'}>
                                    <button type="button"
                                      className={`pv-tree-sub-btn${dom === d.code && grp === g.code ? ' is-on' : ''}`}
                                      onClick={() => { nav.gotoDomain(d.code); nav.setGrp(g.code); }}>
                                      {groupLabel(g.code)}
                                      <span className="pv-n">{g.agents.length}</span>
                                    </button>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function DomainCard({ d, onOpen, badge }: { d: CategoryNode['domains'][number]; onOpen: () => void; badge?: ReactNode }) {
  return (
    <li>
      <button type="button" className="pv-dom" onClick={onOpen}>
        <span className="pv-dom-head">
          <span className="pv-dom-name">{d.label}</span>
          <span className="pv-dom-n">{d.agents.length}</span>
        </span>
        <span className="pv-dom-groups">
          {badge}
          {d.groups.filter((g) => g.code).slice(0, 5).map((g) => (
            <span key={g.code} className="pv-chip">{g.code} {g.agents.length}</span>
          ))}
        </span>
      </button>
    </li>
  );
}

/** 가운데 개요 — 아무것도 안 골랐으면 전체 조직도(루트→분류→도메인 카드), 분류를 골랐으면 그 분류만. */
export function OrgOverview({ nav, total, badge }: { nav: OrgNav; total: number; badge?: Badge }) {
  const roots = nav.catNode
    ? nav.tree.map((r) => ({ ...r, categories: r.categories.filter((c) => c.id === nav.cat) })).filter((r) => r.categories.length)
    : nav.tree;
  return (
    <div className="pv-chart">
      <div className="pv-chart-root">
        전문가 풀 <b>{total}명</b>
      </div>
      {roots.map((r) => (
        <section key={r.id} className="ot-sec">
          <h3 className="ot-sec-h">{r.label} <span className="pv-dim">{r.count}명</span></h3>
          {r.categories.map((c) => (
            <div key={c.id} className="ot-cat-block">
              <button type="button" className="ot-cat-h" onClick={() => nav.gotoCategory(c)}>
                {c.label}{' '}
                <span className="pv-dim">
                  {c.count}명{c.domains.length > 1 ? ` · ${c.domains.length}개 분야` : ''}
                </span>
              </button>
              <ul className="pv-chart-kids ot-kids">
                {c.domains.map((d) => (
                  <DomainCard key={d.code} d={d} onOpen={() => nav.gotoDomain(d.code)} badge={badge?.(d.code)} />
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

/** 빵부스러기 + 그룹 칩. 검색 중이면 검색 결과 줄. */
export function OrgCrumb({ nav }: { nav: OrgNav }) {
  const { q, hits, node, grp, dom } = nav;
  const { root, cat } = pathOf(nav.tree, dom);
  return (
    <>
      <div className="pv-crumb">
        {q.trim() ? (
          <span>
            ‘{q.trim()}’ 검색 — {hits.length}명
            {hits.length >= 120 && <span className="pv-dim"> (상위 120명만)</span>}
          </span>
        ) : (
          <>
            <button type="button" className="pv-crumb-btn" onClick={nav.reset}>전체</button>
            {root && <span className="pv-dim"> / {root.label}</span>}
            {cat && cat.domains.length > 1 && (
              <>
                <span className="pv-dim"> / </span>
                <button type="button" className="pv-crumb-btn" onClick={() => nav.gotoCategory(cat)}>{cat.label}</button>
              </>
            )}
            {node && (
              <>
                <span className="pv-dim"> / </span>
                <button type="button" className="pv-crumb-btn" onClick={() => nav.setGrp(null)}>{node.label}</button>
              </>
            )}
            {grp !== null && (
              <>
                <span className="pv-dim"> / </span>
                <span>{groupLabel(grp)}</span>
              </>
            )}
            <span className="pv-dim"> — {nav.shown.length}명</span>
          </>
        )}
      </div>
      {!q.trim() && node && grp === null && node.groups.length > 1 && (
        <div className="pv-grouprow">
          {node.groups.map((g) => (
            <button key={g.code || '_loose'} type="button" className="pv-chip pv-chip-btn" onClick={() => nav.setGrp(g.code)}>
              {groupLabel(g.code)} {g.agents.length}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
