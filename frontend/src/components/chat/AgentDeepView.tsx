// 전문가 심층 보기 — 한 명을 전체 화면으로: 설명·역할 문서 전문·예시·운영 앱, 지식카드 전체(검색·쪽), 카드 본문
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import {
  fetchAgentDetail,
  fetchAgentRecords,
  fetchRecord,
  type AgentDetail,
  type AgentRecordsPage,
  type PoolExpert,
  type RecordView,
} from '../../api/chat.api';
import { OperatorApps } from './AgentFacts';
import { colorOf, initialOf } from './personaColor';
import { TextBlock } from './renderers/TextBlock';

const PAGE = 50;

export interface AgentDeepViewProps {
  agent: PoolExpert;
  /** 조직도 경로(루트·분류·분야·그룹) — 이 사람이 어디 소속인지. */
  path?: string[];
  /** 상세칸이 이미 받아 둔 요약. 있으면 다시 부르지 않는다(/catalog/agent 는 콜드 6~11초). */
  initialDetail?: AgentDetail | null;
  /** 머리줄 오른쪽 행동(이 전문가로 대화 / 좌석에 넣기) — 부르는 쪽이 정한다. */
  actions?: ReactNode;
  /** 예시 질문을 누르면 — 없으면 예시는 읽기만 한다. */
  onAsk?: (q: string) => void;
  onClose: () => void;
}

const nf = new Intl.NumberFormat('ko-KR');

function doiHref(doi: string): string {
  return /^https?:\/\//i.test(doi) ? doi : `https://doi.org/${doi}`;
}

/** 카드 한 장 — 문서(섹션)·표·그 밖(JSON 원문) 셋을 모두 보인다. 잘렸으면 잘렸다고 말한다. */
function RecordReader({ rec }: { rec: RecordView }) {
  return (
    <div className="dv-rec">
      <h3 className="dv-rec-title">{rec.title || rec.id}</h3>
      <div className="dv-rec-meta">
        <span className="pv-card-key">{rec.id}</span>
        {[rec.doc_type, rec.data_type, rec.year].filter(Boolean).map((m) => (
          <span key={String(m)} className="pv-chip">{m}</span>
        ))}
      </div>
      {rec.tags.length > 0 && <p className="pv-dim dv-rec-tags">{rec.tags.join(' · ')}</p>}
      {rec.summary && <p className="dv-rec-summary">{rec.summary}</p>}
      {rec.truncated && (
        <p className="dv-note">본문이 길어 앞부분만 싣습니다 — 표는 앞 {nf.format(rec.table?.rows.length ?? 0)}행입니다.</p>
      )}
      {rec.sections.map((s, i) => (
        <section key={s.id || i} className="dv-rec-sec">
          {s.title && <h4 className="dv-rec-h">{s.title}</h4>}
          <TextBlock text={s.text} />
        </section>
      ))}
      {rec.table && (
        <section className="dv-rec-sec">
          <h4 className="dv-rec-h">
            {rec.table.caption || '표'} <span className="pv-dim">{nf.format(rec.table.total_rows)}행</span>
          </h4>
          <div className="dv-table-wrap">
            <table className="dv-table">
              <thead>
                <tr>{rec.table.headers.map((h, i) => <th key={i}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {rec.table.rows.map((row, ri) => (
                  <tr key={ri}>{row.map((c, ci) => <td key={ci}>{c === null ? '' : String(c)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
          {rec.table.notes && <p className="pv-dim dv-rec-tags">{rec.table.notes}</p>}
        </section>
      )}
      {rec.sources.length > 0 && (
        <section className="dv-rec-sec">
          <h4 className="dv-rec-h">출처 {rec.sources.length}건</h4>
          <ul className="dv-sources">
            {rec.sources.map((s, i) => (
              <li key={i}>
                {s.title || s.url || s.doi}
                {s.doi && (
                  <>
                    {' '}
                    <a href={doiHref(s.doi)} target="_blank" rel="noreferrer noopener" className="dv-link">DOI</a>
                  </>
                )}
                {!s.doi && s.url && (
                  <>
                    {' '}
                    <a href={s.url} target="_blank" rel="noreferrer noopener" className="dv-link">링크</a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
      {rec.sections.length === 0 && !rec.table && <p className="pv-empty">본문이 비어 있는 카드입니다.</p>}
    </div>
  );
}

export function AgentDeepView({ agent, path, initialDetail, actions, onAsk, onClose }: AgentDeepViewProps) {
  const [detail, setDetail] = useState<AgentDetail | null>(initialDetail ?? null);
  useEffect(() => {
    // 상세칸 요약이 늦게 도착하면 그걸 쓴다 — 여기서 따로 부른 것과 같은 응답이다.
    if (initialDetail) {
      setDetail(initialDetail);
      return;
    }
    let live = true;
    void fetchAgentDetail(agent.key).then((d) => {
      if (live) setDetail(d);
    });
    return () => {
      live = false;
    };
  }, [agent.key, initialDetail]);

  // 지식카드 목록 — 검색어는 잠깐 멈췄을 때 보낸다(글자마다 게이트웨이를 두드리지 않게).
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<AgentRecordsPage | null>(null);
  const [listLoading, setListLoading] = useState(true);
  useEffect(() => {
    const t = window.setTimeout(() => {
      setQuery(q.trim());
      setOffset(0);
    }, 300);
    return () => window.clearTimeout(t);
  }, [q]);
  useEffect(() => {
    let live = true;
    setListLoading(true);
    void fetchAgentRecords(agent.key, { q: query, offset, limit: PAGE }).then((p) => {
      if (!live) return;
      setPage(p);
      setListLoading(false);
    });
    return () => {
      live = false;
    };
  }, [agent.key, query, offset]);

  // 읽기 칸 — 늦게 온 본문이 지금 고른 카드를 덮지 않게 ref 로 대조한다.
  const [selId, setSelId] = useState<string | null>(null);
  const [rec, setRec] = useState<RecordView | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const selRef = useRef<string | null>(null);
  const openRecord = useCallback((id: string) => {
    selRef.current = id;
    setSelId(id);
    setRec(null);
    setRecLoading(true);
    void fetchRecord(id).then((r) => {
      if (selRef.current !== id) return;
      setRec(r);
      setRecLoading(false);
    });
  }, []);
  // 첫 쪽이 오면 첫 카드를 펼쳐 둔다 — 빈 읽기 칸으로 시작하면 무엇을 보는 화면인지 한 번 더 눌러야 안다.
  useEffect(() => {
    if (selRef.current === null && page && page.items.length > 0) openRecord(page.items[0].id);
  }, [page, openRecord]);

  // Esc 는 이 화면만 닫는다. 뒤에 깔린 조직도도 window keydown 으로 닫히므로, 캡처 단계에서 먼저
  // 받아 전파를 끊는다(같은 window 의 버블 리스너까지 멈춘다).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      e.stopPropagation();
      onClose();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [onClose]);

  const total = page && !page.error ? page.total : (detail?.records_total ?? null);
  const items = page?.items ?? [];
  // 카드가 아예 없는 사람(HE팀 운영자 등) — 읽기 칸을 접고 프로필을 넓힌다.
  const noCards = !listLoading && !query && !!page && !page.error && page.total === 0;
  const name = detail?.name || agent.name;

  return createPortal(
    <div className="dv-overlay" role="dialog" aria-modal="true" aria-label={`${name} 심층 보기`}>
      <div className="dv-win">
        <header className="dv-head">
          <button type="button" className="pv-icon" onClick={onClose} aria-label="조직도로 돌아가기">
            ←
          </button>
          <span className="pv-card-av dv-av" style={{ background: colorOf(agent.name) }}>
            {initialOf(agent.name)}
          </span>
          <div className="dv-id">
            <h2 className="dv-name" title={name}>{name}</h2>
            <div className="dv-sub">
              <span className="pv-card-key">{agent.key}</span>
              {path && path.length > 0 && <span className="pv-dim"> · {path.join(' / ')}</span>}
            </div>
          </div>
          {actions && <div className="dv-actions">{actions}</div>}
          <button type="button" className="pv-icon pv-close" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </header>

        <div className={`dv-body${noCards ? ' is-nocards' : ''}`}>
          {/* ── 프로필: 무엇을 하는 사람인가 ── */}
          <aside className="dv-col dv-profile" aria-label="전문가 설명">
            {!detail && <p className="pv-empty">설명 불러오는 중…</p>}
            {detail?.error && <p className="pv-empty">설명을 불러오지 못했습니다({detail.error}).</p>}
            {detail && (
              <>
                {detail.role && <p className="dv-desc">{detail.role}</p>}
                {detail.tags.length > 0 && (
                  <div className="dv-tags">
                    {detail.tags.map((t) => (
                      <span key={t} className="pv-chip">{t}</span>
                    ))}
                  </div>
                )}
                <OperatorApps detail={detail} />
                {detail.samples.length > 0 && (
                  <>
                    <h4 className="pv-detail-h">
                      이런 걸 물을 수 있어요{onAsk ? ' — 누르면 이 전문가와 대화를 시작합니다' : ''}
                    </h4>
                    <ul className="pv-detail-list pv-samples">
                      {detail.samples.map((s, i) => (
                        <li key={i}>
                          {onAsk ? (
                            <button type="button" className="pv-sample" onClick={() => onAsk(s)}>{s}</button>
                          ) : (
                            <span className="pv-sample is-static">{s}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                <h4 className="pv-detail-h">역할 문서 — 이 전문가가 받는 지시 전문</h4>
                {detail.prompt ? (
                  <div className="dv-doc">
                    <TextBlock text={detail.prompt} />
                  </div>
                ) : (
                  <p className="pv-empty">따로 쓴 역할 문서가 없습니다 — 위 설명이 전부입니다.</p>
                )}
              </>
            )}
          </aside>

          {/* ── 지식카드 전체: 검색·쪽 ── */}
          <section className="dv-col dv-list" aria-label="지식카드 목록">
            <div className="dv-list-head">
              <h3 className="dv-list-title">
                지식카드 {total !== null ? <b>{nf.format(total)}건</b> : ''}
                {query && page && !page.error && <span className="pv-dim"> · ‘{query}’ 검색</span>}
              </h3>
              {!noCards && (
                <input
                  className="pv-search dv-search"
                  type="text"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="카드 제목·요약으로 찾기"
                  aria-label="지식카드 검색"
                  autoFocus
                />
              )}
            </div>
            {page && !page.error && page.total > 0 && (
              <div className="dv-pager">
                <span className="pv-dim">
                  {nf.format(offset + 1)}–{nf.format(offset + items.length)} / {nf.format(page.total)}
                </span>
                <button type="button" className="pv-chip pv-chip-btn" disabled={offset === 0 || listLoading}
                  onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                  ◀ 이전
                </button>
                <button type="button" className="pv-chip pv-chip-btn"
                  disabled={offset + items.length >= page.total || listLoading}
                  onClick={() => setOffset(offset + PAGE)}>
                  다음 ▶
                </button>
              </div>
            )}
            {listLoading && <p className="pv-empty">지식카드 불러오는 중…</p>}
            {!listLoading && page?.error && (
              <p className="pv-empty">
                지식카드를 불러오지 못했습니다({page.error}) — 보유 지식이 없다는 뜻이 아닙니다.
              </p>
            )}
            {!listLoading && page && !page.error && page.total === 0 && (
              <p className="pv-empty">
                {query
                  ? `‘${query}’ 에 맞는 카드가 없습니다.`
                  : detail?.operator
                    ? '지식카드가 없습니다 — 이 전문가는 지식카드가 아니라 앱 도구를 직접 호출해 답합니다.'
                    : '연결된 지식카드가 없습니다.'}
              </p>
            )}
            {!listLoading && items.length > 0 && (
              <ul className="dv-items">
                {items.map((r) => (
                  <li key={r.id}>
                    <button type="button" className={`dv-item${selId === r.id ? ' is-on' : ''}`}
                      onClick={() => openRecord(r.id)}>
                      <span className="dv-item-title">{r.title || r.id}</span>
                      <span className="dv-item-meta">
                        {[r.doc_type, r.data_type, r.year].filter(Boolean).join(' · ')}
                      </span>
                      {r.summary && r.summary !== r.title && <span className="dv-item-sum">{r.summary}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* ── 읽기: 고른 카드의 본문 ── */}
          {!noCards && (
            <article className="dv-col dv-reader" aria-label="지식카드 본문">
              {!selId && !listLoading && <p className="pv-empty">가운데에서 카드를 고르면 본문이 여기 보입니다.</p>}
              {recLoading && <p className="pv-empty">카드 불러오는 중…</p>}
              {rec?.error && <p className="pv-empty">카드를 불러오지 못했습니다({rec.error}).</p>}
              {rec && !rec.error && <RecordReader rec={rec} />}
            </article>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
