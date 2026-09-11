// 심의 좌석 조직도 — 분야→그룹→사람으로 훑으며 **여러 명**을 고른다(챗 조직도의 다중선택판)
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchAgentDetail, type AgentDetail, type PoolExpert, type RecommendedExpert } from '../../api/chat.api';
import { colorOf, initialOf, shortName } from './personaColor';
import { OperatorApps } from './AgentFacts';
import { findDomain } from './personaCatalog';
import { OrgCrumb, OrgOverview, OrgTreeNav } from './OrgTree';
import { useOrgNav } from './orgNav';

export interface SeatBrowserProps {
  pool: PoolExpert[];
  /** 질문 관련도순 후보(≈40). **분류만 하고 이걸 안 얹으면** 사용자가 가진 유일한 판단
   *  근거(관련도)가 사라져 "분류는 됐는데 누굴 골라야 할지 더 모르겠다" 가 된다. */
  candidates: RecommendedExpert[];
  selected: Record<string, { key: string; name: string; role: string }>;
  onToggle: (row: { key: string; name: string; role: string }) => void;
  min: number;
  max: number;
  onClose: () => void;
}

export function SeatBrowser({ pool, candidates, selected, onToggle, min, max, onClose }: SeatBrowserProps) {
  // 탐색은 챗 조직도와 같은 공용 훅(루트→분류→도메인→그룹·검색).
  const nav = useOrgNav(pool);
  const { q, setQ, shown } = nav;
  const [sel, setSel] = useState<PoolExpert | null>(null);
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 관련도·역할을 key 로 얹는다 — 조직도 카드가 판단 근거를 잃지 않게.
  const relBy = useMemo(() => {
    const top = candidates[0]?.score ?? null;
    const m = new Map<string, { pct: number | null; role: string }>();
    for (const c of candidates) {
      const pct =
        typeof c.score === 'number' && typeof top === 'number' && top > 0
          ? Math.round((c.score / top) * 100)
          : null;
      m.set(c.key, { pct, role: c.role || '' });
    }
    return m;
  }, [candidates]);

  // 분야마다 이미 앉힌 좌석 수 — 분야로 접으면 한쪽에 쏠린 걸 못 본다.
  const pickedBadge = (code: string) => {
    const d = findDomain(nav.tree, code);
    const n = d ? d.agents.filter((a) => selected[a.key]).length : 0;
    return n > 0 ? <span className="sb-tree-pick">{n}석</span> : null;
  };

  // 늦게 온 상세가 지금 선택을 덮지 않게 — /catalog/agent 는 콜드 6~11초다.
  const selKeyRef = useRef<string | null>(null);
  const openAgent = useCallback((a: PoolExpert) => {
    selKeyRef.current = a.key;
    setSel(a);
    setDetail(null);
    setDetailLoading(true);
    void fetchAgentDetail(a.key).then((d) => {
      if (selKeyRef.current !== d.key) return;
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

  const count = Object.keys(selected).length;
  const full = count >= max;

  const toggle = (a: PoolExpert) => {
    const on = Boolean(selected[a.key]);
    // 상한에서 **조용히 무시하지 않는다** — 눌렀는데 아무 일도 안 일어나면 고장으로 읽힌다.
    if (!on && full) return;
    onToggle({ key: a.key, name: a.name, role: relBy.get(a.key)?.role || '' });
  };

  const card = (a: PoolExpert) => {
    const on = Boolean(selected[a.key]);
    const rel = relBy.get(a.key);
    const blocked = !on && full;
    return (
      <li key={a.key}>
        <div className={`sb-card${on ? ' is-on' : ''}${blocked ? ' is-blocked' : ''}`}>
          <button
            type="button"
            className="sb-card-main"
            onClick={() => openAgent(a)}
            aria-label={`${a.name} 상세 보기`}
          >
            <span className="pv-card-av" style={{ background: colorOf(a.name) }}>
              {initialOf(a.name)}
            </span>
            <span className="pv-card-body">
              <span className="pv-card-name" title={a.name}>
                {shortName(a.name)}
              </span>
              <span className="pv-card-key">{a.key}</span>
            </span>
            {rel?.pct != null && <span className="sb-rel">관련도 {rel.pct}%</span>}
          </button>
          <button
            type="button"
            className="sb-pick"
            onClick={() => toggle(a)}
            disabled={blocked}
            title={blocked ? `${max}석이 찼습니다 — 먼저 제외하세요` : undefined}
          >
            {on ? '제외' : blocked ? '가득' : '＋ 좌석'}
          </button>
        </div>
      </li>
    );
  };

  return createPortal(
    <div className="pv-overlay" role="dialog" aria-modal="true" aria-label="심의 좌석 조직도">
      <div className="pv-win">
        <header className="pv-head">
          <h2 className="pv-title">좌석 조직도</h2>
          <span className="pv-count">
            {pool.length}명 · {nav.domainCount}개 분야
          </span>
          <span className={`sb-chosen${full ? ' is-full' : ''}`}>
            선정 {count}/{max}
            {full && ' — 가득'}
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
          <OrgTreeNav nav={nav} total={pool.length} badge={pickedBadge} />

          <main className="pv-main">
            {!q.trim() && !nav.node && <OrgOverview nav={nav} total={pool.length} badge={pickedBadge} />}

            {(q.trim() || nav.node) && (
              <>
                <OrgCrumb nav={nav} />
                {shown.length === 0 ? (
                  <p className="pv-empty">일치하는 전문가가 없습니다.</p>
                ) : (
                  <ul className="pv-cards sb-cards">{shown.map(card)}</ul>
                )}
              </>
            )}
          </main>

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
                    <div className="pv-detail-name" title={sel.name}>
                      {shortName(sel.name)}
                    </div>
                    <div className="pv-card-key">{sel.key}</div>
                  </div>
                </div>
                <button
                  type="button"
                  className="pv-apply"
                  onClick={() => toggle(sel)}
                  disabled={!selected[sel.key] && full}
                >
                  {selected[sel.key]
                    ? '좌석에서 제외'
                    : full
                      ? `${max}석이 찼습니다`
                      : '이 전문가를 좌석에'}
                </button>
                {detailLoading && <p className="pv-empty">상세 불러오는 중…</p>}
                {detail && (
                  <>
                    {detail.role && <p className="pv-detail-role">{detail.role}</p>}
                    {detail.tags.length > 0 && (
                      <p className="pv-dim pv-detail-tags">{detail.tags.slice(0, 14).join(' · ')}</p>
                    )}
                    <OperatorApps detail={detail} />
                    {detail.records.length > 0 && (
                      <>
                        <h4 className="pv-detail-h">보유 지식 {detail.records.length}건</h4>
                        <ul className="pv-detail-list pv-detail-scroll">
                          {detail.records.map((r) => (
                            <li key={r.id || r.title}>{r.title}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </>
                )}
              </>
            )}
          </aside>
        </div>

        <footer className="sb-foot">
          <span className="sb-foot-list">
            {count === 0
              ? '아직 고른 좌석이 없습니다.'
              : Object.values(selected)
                  .map((p) => shortName(p.name))
                  .join(' · ')}
          </span>
          {/* 0석은 '서버가 알아서 발굴' 이라 정상이다. 1석만 남기는 것이 사고다 —
              엔진이 2석 미만이면 no_personas 로 죽는다(deliberation.py). */}
          {count > 0 && count < min && (
            <span className="sb-warn">{min}석 미만은 심의가 시작되지 않습니다.</span>
          )}
          <button type="button" className="sb-done" onClick={onClose}>
            선택 완료
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
