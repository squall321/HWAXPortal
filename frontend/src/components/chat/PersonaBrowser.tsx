// 전문가 조직도 — 전창으로 전체 분류(분야→그룹→사람)를 펼쳐 보고, 누르면 설명이 뜨고 거기서 고른다
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchAgentDetail, type AgentDetail, type PoolExpert } from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import { colorOf, initialOf, shortName } from './personaColor';
import { buildTree, domainLabel, matches, type DomainNode } from './personaCatalog';
import { usePersonaPool } from './usePersonaPool';

/** 그룹 코드 '' 는 '묶이지 않은 사람들' 이다(2명 미만이라 그룹을 안 세운 것). */
const groupLabel = (code: string) => (code ? code : '개별');

function AgentCard({
  agent,
  active,
  onOpen,
}: {
  agent: PoolExpert;
  active: boolean;
  onOpen: () => void;
}) {
  return (
    <li>
      <button type="button" className={`pv-card${active ? ' is-on' : ''}`} onClick={onOpen}>
        <span className="pv-card-av" style={{ background: colorOf(agent.name) }}>
          {initialOf(agent.name)}
        </span>
        <span className="pv-card-body">
          <span className="pv-card-name" title={agent.name}>{shortName(agent.name)}</span>
          <span className="pv-card-key">{agent.key}</span>
        </span>
      </button>
    </li>
  );
}

export function PersonaBrowser({ onClose, onBack }: { onClose: () => void; onBack?: () => void }) {
  const { pinnedAgent, setPinnedAgent, setInput } = useChat();
  const { pool, loading, failed } = usePersonaPool();
  const [q, setQ] = useState('');
  // 선택 경로 — 분야(없으면 전체 조직도), 그 안의 그룹.
  const [dom, setDom] = useState<string | null>(null);
  const [grp, setGrp] = useState<string | null>(null);
  const [open, setOpen] = useState<string[]>([]); // 트리에서 펼친 분야
  const [sel, setSel] = useState<PoolExpert | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const tree = useMemo(() => buildTree(pool), [pool]);
  const hits = useMemo(
    () => (q.trim() ? pool.filter((a) => matches(a, q)).slice(0, 120) : []),
    [pool, q],
  );
  const node: DomainNode | undefined = useMemo(
    () => tree.find((d) => d.code === dom),
    [tree, dom],
  );
  const shown = useMemo(() => {
    if (q.trim()) return hits;
    if (!node) return [];
    if (grp === null) return node.agents;
    return node.groups.find((g) => g.code === grp)?.agents ?? [];
  }, [q, hits, node, grp]);

  // 지금 열어 둔 사람 — 상태 갱신 함수 안에서 부수효과를 내지 않으려고 ref 로 따로 둔다.
  const selKeyRef = useRef<string | null>(null);
  const openAgent = useCallback((a: PoolExpert) => {
    selKeyRef.current = a.key;
    setSel(a);
    setDetail(null);
    setDetailLoading(true);
    void fetchAgentDetail(a.key).then((d) => {
      if (selKeyRef.current !== d.key) return; // 연달아 누르면 늦게 온 응답이 화면을 덮는다
      setDetail(d);
      setDetailLoading(false);
    });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const pick = (a: PoolExpert) => {
    setPinnedAgent(a.key, a.name);
    onClose();
  };

  // 샘플 질의는 "이 사람한테 뭘 물어야 하나" 가 막히는 자리의 답이다 — 읽고 옮겨 적게 하지 말고
  // 눌러서 그 전문가를 지정하고 입력창까지 채운다.
  const askSample = (a: PoolExpert, q: string) => {
    setPinnedAgent(a.key, a.name);
    setInput(q);
    onClose();
  };

  const gotoDomain = (code: string) => {
    setQ('');
    setDom(code);
    setGrp(null);
    setOpen((prev) => (prev.includes(code) ? prev : [...prev, code]));
  };

  return createPortal(
    <div className="pv-overlay" role="dialog" aria-modal="true" aria-label="전문가 조직도">
      <div className="pv-win">
        <header className="pv-head">
          {onBack && (
            <button type="button" className="pv-icon" onClick={onBack} aria-label="간단 선택으로">
              ←
            </button>
          )}
          <h2 className="pv-title">전문가 조직도</h2>
          <span className="pv-count">
            {loading ? '불러오는 중…' : `${pool.length}명 · ${tree.length}개 분야`}
          </span>
          <input
            className="pv-search"
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="이름·키·태그로 찾기"
            aria-label="전문가 검색"
          />
          <button type="button" className="pv-icon pv-close" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </header>

        <div className="pv-body">
          {/* ── 왼쪽: 전체 분류 트리(조직도의 계보). 접혀 있어도 인원이 다 보인다 ── */}
          <nav className="pv-tree" aria-label="분야 분류">
            <button
              type="button"
              className={`pv-tree-root${dom === null && !q.trim() ? ' is-on' : ''}`}
              onClick={() => {
                setQ('');
                setDom(null);
                setGrp(null);
              }}
            >
              전체 <span className="pv-n">{pool.length}</span>
            </button>
            <ul className="pv-tree-list">
              {tree.map((d) => {
                const expanded = open.includes(d.code);
                return (
                  <li key={d.code} className="pv-tree-item">
                    <div className={`pv-tree-row${dom === d.code ? ' is-on' : ''}`}>
                      <button
                        type="button"
                        className="pv-twist"
                        onClick={() =>
                          setOpen((prev) =>
                            prev.includes(d.code)
                              ? prev.filter((x) => x !== d.code)
                              : [...prev, d.code],
                          )
                        }
                        aria-label={`${d.label} ${expanded ? '접기' : '펼치기'}`}
                        aria-expanded={expanded}
                      >
                        {expanded ? '▾' : '▸'}
                      </button>
                      <button type="button" className="pv-tree-name" onClick={() => gotoDomain(d.code)}>
                        {d.label}
                        <span className="pv-n">{d.agents.length}</span>
                      </button>
                    </div>
                    {expanded && (
                      <ul className="pv-tree-sub">
                        {d.groups.map((g) => (
                          <li key={g.code || '_loose'}>
                            <button
                              type="button"
                              className={`pv-tree-sub-btn${dom === d.code && grp === g.code ? ' is-on' : ''}`}
                              onClick={() => {
                                setQ('');
                                setDom(d.code);
                                setGrp(g.code);
                              }}
                            >
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
          </nav>

          {/* ── 가운데: 조직도 개요 또는 선택한 갈래의 사람들 ── */}
          <main className="pv-main">
            {failed && <p className="pv-empty">전문가 목록을 불러오지 못했습니다 — 잠시 후 다시 열어 보세요.</p>}
            {loading && <p className="pv-empty">조직도를 불러오는 중…</p>}

            {!loading && !q.trim() && !node && (
              <div className="pv-chart">
                <div className="pv-chart-root">
                  전문가 풀 <b>{pool.length}명</b>
                </div>
                <ul className="pv-chart-kids">
                  {tree.map((d) => (
                    <li key={d.code}>
                      <button type="button" className="pv-dom" onClick={() => gotoDomain(d.code)}>
                        <span className="pv-dom-head">
                          <span className="pv-dom-name">{d.label}</span>
                          <span className="pv-dom-n">{d.agents.length}</span>
                        </span>
                        <span className="pv-dom-code">{d.code}</span>
                        <span className="pv-dom-groups">
                          {d.groups
                            .filter((g) => g.code)
                            .slice(0, 5)
                            .map((g) => (
                              <span key={g.code} className="pv-chip">
                                {g.code} {g.agents.length}
                              </span>
                            ))}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!loading && (q.trim() || node) && (
              <>
                <div className="pv-crumb">
                  {q.trim() ? (
                    <span>
                      ‘{q.trim()}’ 검색 — {hits.length}명
                      {hits.length >= 120 && <span className="pv-dim"> (상위 120명만)</span>}
                    </span>
                  ) : (
                    <>
                      <button type="button" className="pv-crumb-btn" onClick={() => setDom(null)}>
                        전체
                      </button>
                      <span className="pv-dim"> / </span>
                      <button type="button" className="pv-crumb-btn" onClick={() => setGrp(null)}>
                        {domainLabel(dom ?? '')}
                      </button>
                      {grp !== null && (
                        <>
                          <span className="pv-dim"> / </span>
                          <span>{groupLabel(grp)}</span>
                        </>
                      )}
                      <span className="pv-dim"> — {shown.length}명</span>
                    </>
                  )}
                </div>
                {!q.trim() && node && grp === null && node.groups.length > 1 && (
                  <div className="pv-grouprow">
                    {node.groups.map((g) => (
                      <button
                        key={g.code || '_loose'}
                        type="button"
                        className="pv-chip pv-chip-btn"
                        onClick={() => setGrp(g.code)}
                      >
                        {groupLabel(g.code)} {g.agents.length}
                      </button>
                    ))}
                  </div>
                )}
                {shown.length === 0 ? (
                  <p className="pv-empty">일치하는 전문가가 없습니다.</p>
                ) : (
                  <ul className="pv-cards">
                    {shown.map((a) => (
                      <AgentCard
                        key={a.key}
                        agent={a}
                        active={sel?.key === a.key}
                        onOpen={() => openAgent(a)}
                      />
                    ))}
                  </ul>
                )}
              </>
            )}
          </main>

          {/* ── 오른쪽: 누른 사람의 설명. 여기서 바로 고른다 ── */}
          <aside className={`pv-detail${sel ? ' is-open' : ''}`} aria-label="전문가 상세">
            {!sel ? (
              <p className="pv-empty pv-detail-hint">전문가를 누르면 역할·보유 지식이 여기 보입니다.</p>
            ) : (
              <>
                <div className="pv-detail-head">
                  <span className="pv-card-av" style={{ background: colorOf(sel.name) }}>
                    {initialOf(sel.name)}
                  </span>
                  <div>
                    <div className="pv-detail-name" title={sel.name}>{shortName(sel.name)}</div>
                    <div className="pv-card-key">{sel.key}</div>
                  </div>
                </div>
                <button
                  type="button"
                  className="pv-apply"
                  onClick={() => pick(sel)}
                  disabled={pinnedAgent === sel.key}
                >
                  {pinnedAgent === sel.key ? '이미 이 전문가와 대화 중' : '이 전문가로 대화하기'}
                </button>
                {detailLoading && <p className="pv-empty">상세 불러오는 중…</p>}
                {detail && (
                  <>
                    {detail.role && <p className="pv-detail-role">{detail.role}</p>}
                    {detail.tags.length > 0 && (
                      <p className="pv-dim pv-detail-tags">{detail.tags.slice(0, 14).join(' · ')}</p>
                    )}
                    {detail.samples.length > 0 && (
                      <>
                        <h4 className="pv-detail-h">이런 걸 물을 수 있어요 — 누르면 입력창에 들어갑니다</h4>
                        <ul className="pv-detail-list pv-samples">
                          {detail.samples.slice(0, 4).map((s, i) => (
                            <li key={i}>
                              <button type="button" className="pv-sample" onClick={() => askSample(sel, s)}>
                                {s}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                    {detail.records.length > 0 && (
                      <>
                        <h4 className="pv-detail-h">보유 지식 {detail.records.length}건</h4>
                        <ul className="pv-detail-list pv-detail-scroll">
                          {detail.records.map((r) => (
                            <li key={r.id || r.title}>
                              {r.title}
                              {r.data_type && <span className="pv-dim"> [{r.data_type}]</span>}
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                    {detail.error && <p className="pv-empty">상세를 불러오지 못했습니다({detail.error}).</p>}
                  </>
                )}
              </>
            )}
          </aside>
        </div>
      </div>
    </div>,
    document.body,
  );
}
