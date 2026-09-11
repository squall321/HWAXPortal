// 전문가 조직도 — 전창으로 전체 분류(분야→그룹→사람)를 펼쳐 보고, 누르면 설명이 뜨고 거기서 고른다
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchAgentDetail, type AgentDetail, type PoolExpert } from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import { colorOf, initialOf, shortName } from './personaColor';
import { OperatorApps } from './AgentFacts';
import { OrgCrumb, OrgOverview, OrgTreeNav } from './OrgTree';
import { useOrgNav } from './orgNav';
import { usePersonaPool } from './usePersonaPool';

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
  // 탐색(루트→분류→도메인→그룹·검색)은 심의 좌석 조직도와 같은 규칙이라 공용 훅을 쓴다.
  const nav = useOrgNav(pool);
  const { q, setQ, shown } = nav;
  const [sel, setSel] = useState<PoolExpert | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

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
            {loading ? '불러오는 중…' : `${pool.length}명 · ${nav.domainCount}개 분야`}
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
          {/* ── 왼쪽: 조직도 트리(루트→분류→도메인→그룹). 접혀 있어도 인원이 다 보인다 ── */}
          <OrgTreeNav nav={nav} total={pool.length} />

          {/* ── 가운데: 조직도 개요 또는 선택한 갈래의 사람들 ── */}
          <main className="pv-main">
            {failed && <p className="pv-empty">전문가 목록을 불러오지 못했습니다 — 잠시 후 다시 열어 보세요.</p>}
            {loading && <p className="pv-empty">조직도를 불러오는 중…</p>}

            {!loading && !q.trim() && !nav.node && <OrgOverview nav={nav} total={pool.length} />}

            {!loading && (q.trim() || nav.node) && (
              <>
                <OrgCrumb nav={nav} />
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
                    <OperatorApps detail={detail} />
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
