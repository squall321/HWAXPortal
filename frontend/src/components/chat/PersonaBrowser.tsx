// 전문가 조직도 — 전창으로 전체 분류(분야→그룹→사람)를 펼쳐 보고, 누르면 설명이 뜨고 거기서 고른다
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchAgentDetail, fetchDeliberateExperts, type AgentDetail, type PoolExpert } from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import { colorOf, initialOf, shortName } from './personaColor';
import { OperatorApps, RecordsHeading } from './AgentFacts';
import { AgentDeepView } from './AgentDeepView';
import { OrgCrumb, OrgOverview, OrgTreeNav } from './OrgTree';
import { agentPath, useOrgNav } from './orgNav';
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

/** `onPick` 이 오면 **고르기만 하고 돌려준다** — 챗 시작 화면처럼 도구·앱과 함께 나중에 한 번에
 *  확정하는 자리를 위해서다(그 자리에서 대화가 시작되면 안 된다). 없으면 곧장 지정하고 닫는다.
 *  `picked` 는 그 모드에서 '이미 고른 사람'(지정된 전문가가 아니라). */
export function PersonaBrowser({
  onClose,
  onBack,
  onPick,
  picked,
  onAddHelper,
  mode,
}: {
  onClose: () => void;
  onBack?: () => void;
  onPick?: (agent: PoolExpert, sample?: string) => void;
  picked?: string | null;
  /** 보조 전문가로 더하기 — 주 전문가가 이미 있는 자리에서만 준다. */
  onAddHelper?: (agent: PoolExpert) => void;
  /** 'helper' 면 고르기 버튼 문구가 '보조로 추가'가 된다(조직도를 보조 고르러 연 경우). */
  mode?: 'lead' | 'helper';
}) {
  const { pinnedAgent, setPinnedAgent, setInput } = useChat();
  const current = onPick ? (picked ?? null) : pinnedAgent;
  const { pool, loading, failed } = usePersonaPool();
  // 탐색(루트→분류→도메인→그룹·검색)은 심의 좌석 조직도와 같은 규칙이라 공용 훅을 쓴다.
  const nav = useOrgNav(pool);
  const { q, setQ, shown } = nav;
  const [sel, setSel] = useState<PoolExpert | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  // 한 명을 전체 화면으로 — 상세칸은 요약이고, 설명 전문·지식카드 전체·카드 본문은 여기서 본다.
  const [deep, setDeep] = useState(false);
  // 의미 검색 — 글자가 안 맞아도 주제가 맞는 사람을 찾는다(임베딩). 문자열 일치는 즉시 나오고
  // 이건 서버 왕복이라, **누를 때만** 돈다(입력마다 던지면 796명 풀에 질의가 쏟아진다).
  const [sem, setSem] = useState<{
    q: string; rows: PoolExpert[]; loading: boolean; axes: string[]; weak: boolean;
  } | null>(null);
  const runSemantic = useCallback(async (query: string) => {
    const t = query.trim();
    if (t.length < 2) return;
    setSem({ q: t, rows: [], loading: true, axes: [], weak: false });
    const r = await fetchDeliberateExperts(t);
    const rows = (r.candidates ?? r.recommended ?? []).map((e) => ({
      key: e.key, name: e.name, tags: e.tags ?? [],
    }));
    // 축 = 서버가 질문을 쪼갠 도메인. 축이 없으면 **질문 그대로** 임베딩 검색만 한 것이라
    // 구어("떨어뜨렸을 때 깨진다")가 전문 용어(낙하·커버글라스)에 못 닿는다 — 그걸 화면이 말한다.
    setSem({ q: t, rows, loading: false,
             axes: (r.axes ?? []).map((a) => `${a.domain} · ${a.phrase}`),
             weak: Boolean(r.low_confidence) });
  }, []);

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
    if (onPick) onPick(a);
    else setPinnedAgent(a.key, a.name);
    onClose();
  };

  // 샘플 질의는 "이 사람한테 뭘 물어야 하나" 가 막히는 자리의 답이다 — 읽고 옮겨 적게 하지 말고
  // 눌러서 그 전문가를 지정하고 입력창까지 채운다.
  const askSample = (a: PoolExpert, q: string) => {
    if (onPick) {
      onPick(a, q);
    } else {
      setPinnedAgent(a.key, a.name);
      setInput(q);
    }
    onClose();
  };

  const pickBtn = (a: PoolExpert) => (
    <>
      <button type="button" className="pv-apply" onClick={() => pick(a)} disabled={current === a.key}>
        {current === a.key
          ? onPick ? '이미 고른 전문가' : '이미 이 전문가와 대화 중'
          : onPick ? (mode === 'helper' ? '보조로 추가하기' : '이 전문가로 고르기') : '이 전문가로 대화하기'}
      </button>
      {/* 보조로 더하기 — 주 전문가가 이미 있을 때만. 목소리는 주 전문가 하나이고 보조는
          판단 기준과 도구만 빌려준다(각자 답하는 Thinking 과 다르다). */}
      {onAddHelper && current && current !== a.key && (
        <button type="button" className="pv-deep" onClick={() => { onAddHelper(a); onClose(); }}>
          ＋ 보조 전문가로 더하기 — 도구·판단 기준만 빌린다
        </button>
      )}
    </>
  );

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
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
                e.preventDefault();
                void runSemantic(q);
              }
            }}
            placeholder="이름·키·태그로 찾기 · Enter = 의미로 찾기"
            aria-label="전문가 검색"
          />
          <button type="button" className="pv-icon pv-sem" onClick={() => void runSemantic(q)}
                  disabled={q.trim().length < 2} title="주제·의미로 찾기(글자가 달라도 찾는다)">
            의미 검색
          </button>
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

            {/* 의미 검색 결과 — 문자열 일치와 **따로** 보여 준다. 임베딩(e5)은 무관한 문장끼리도
                코사인 0.87~0.90 이라 점수를 섞어 한 줄로 세우면 난수를 순위로 읽게 된다. */}
            {sem && (
              <section className="pv-sem-box">
                <div className="pv-crumb">
                  🧭 ‘{sem.q}’ 의미 검색 —{' '}
                  {sem.loading ? '찾는 중…' : `${sem.rows.length}명 (주제 관련도순)`}
                  <button type="button" className="pv-crumb-btn" onClick={() => setSem(null)}>닫기</button>
                </div>
                {!sem.loading && (
                  <p className="pv-dim pv-sem-note">
                    {sem.axes.length > 0
                      ? `질문을 이렇게 쪼개 찾았습니다 — ${sem.axes.join(' / ')}`
                      : '질문 그대로 찾았습니다(도메인 분해 없음) — 일상어보다 전문 용어로 물으면 잘 찾습니다.'}
                    {sem.weak && ' ⚠ 이 주제를 맡을 전문가가 풀에 없을 수 있습니다.'}
                  </p>
                )}
                {!sem.loading && sem.rows.length === 0 && (
                  <p className="pv-empty">주제로도 찾지 못했습니다 — 다른 말로 물어보세요.</p>
                )}
                {sem.rows.length > 0 && (
                  <ul className="pv-cards">
                    {sem.rows.slice(0, 24).map((a) => (
                      <AgentCard key={a.key} agent={a} active={sel?.key === a.key} onOpen={() => openAgent(a)} />
                    ))}
                  </ul>
                )}
              </section>
            )}

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
                {pickBtn(sel)}
                <button type="button" className="pv-deep" onClick={() => setDeep(true)}>
                  ⤢ 전체 화면으로 보기 — 설명 전문·지식카드 전체
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
                        <RecordsHeading detail={detail} onMore={() => setDeep(true)} />
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
      {deep && sel && (
        <AgentDeepView
          agent={sel}
          path={agentPath(nav.tree, sel.key)}
          initialDetail={detail}
          actions={pickBtn(sel)}
          onAsk={(s) => askSample(sel, s)}
          onClose={() => setDeep(false)}
        />
      )}
    </div>,
    document.body,
  );
}
