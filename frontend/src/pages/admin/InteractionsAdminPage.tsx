// 관리 › 상호작용 기록(분석가만) — 남의 기록을 찾고 원문을 연다. 검색 · 열기마다 감사 기록이 남는다(docs/interaction-data contract §6)
import { useEffect, useState } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { RecordDetail, RecordTable } from '../../components/records/RecordView';
import {
  SURFACE_LABEL,
  adminGet,
  adminSearch,
  fetchInteractionDetail,
  type InteractionFull,
  type InteractionPage,
  type InteractionStatus,
} from '../../api/interactions.api';
import '../../styles/admin.css';
import '../../styles/records.css';

const when = (ts: number) => new Date(ts * 1000).toLocaleString();

type Query = { q: string; actor: string; surface: string; app: string; days: number; before?: string };

export default function InteractionsAdminPage() {
  const [st, setSt] = useState<InteractionStatus | null | undefined>(undefined);
  const [f, setF] = useState<Query>({ q: '', actor: '', surface: '', app: '', days: 7 });
  const [page, setPage] = useState<InteractionPage | null>(null);
  const [open, setOpen] = useState<InteractionFull | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchInteractionDetail().then(setSt);
  }, []);

  if (st === undefined) return <Spinner label="불러오는 중…" />;
  if (!st || !st.analyst)
    return (
      <Page width="wide">
        <PageHeader title="상호작용 기록" />
        <ErrorBanner
          message={
            !st
              ? '이 포털 박스는 상호작용 기록을 켜지 않았습니다.'
              : '지정 분석가(feat:interaction-analyst — 운영자가 사람마다 준다)만 볼 수 있는 페이지입니다.'
          }
        />
      </Page>
    );

  const search = (q: Query) => {
    setError(null);
    adminSearch({ ...q, days: q.days || undefined })
      .then((got) => setPage((prev) => (q.before && prev ? { ...got, items: [...prev.items, ...got.items] } : got)))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '검색 실패'));
  };
  const openRow = (id: string) => {
    setError(null);
    adminGet(id)
      .then(setOpen)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '열지 못했습니다'));
  };
  const h = st.health;

  return (
    <Page width="wide">
      <PageHeader
        title="상호작용 기록"
        desc={
          <>
            모든 사람의 웹 챗 · 심의 · 개인 Claude 도구 호출 · 공유한 Claude 대화 원문입니다. <b>검색과 원문 열기마다 감사 기록이 남습니다.</b>{' '}
            비밀(토큰 · 키)은 넣을 때 가려져 있습니다.
          </>
        }
      />
      {error && <ErrorBanner message={error} />}
      {h && (
        <p className={h.ok ? 'adm-hint' : 'adm-err'}>
          수집 —{' '}
          {Object.entries(h.sources)
            .map(([k, v]) => `${k} ${v.state}${v.last_ok ? `(${when(v.last_ok)})` : ''}`)
            .join(' · ')}
          {!h.ok && ` · 문제: ${h.problems.join(', ')}`}
          {st.counts && ` · 사건 ${st.counts.events.toLocaleString()} · 공유 대화 ${st.counts.shared.toLocaleString()}`}
        </p>
      )}
      <form
        className="adm-filter"
        onSubmit={(e) => {
          e.preventDefault();
          search(f);
        }}
      >
        <input id="ix-q" placeholder="찾을 말" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        <input id="ix-actor" placeholder="사람(이메일)" value={f.actor} onChange={(e) => setF({ ...f, actor: e.target.value })} />
        <select id="ix-surface" value={f.surface} onChange={(e) => setF({ ...f, surface: e.target.value })}>
          <option value="">전부</option>
          {Object.entries(SURFACE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <input id="ix-app" placeholder="앱(백엔드 키)" value={f.app} onChange={(e) => setF({ ...f, app: e.target.value })} />
        <select id="ix-days" value={f.days} onChange={(e) => setF({ ...f, days: Number(e.target.value) })}>
          {[1, 7, 30, 90, 365, 0].map((d) => (
            <option key={d} value={d}>
              {d ? `최근 ${d}일` : '전체 기간'}
            </option>
          ))}
        </select>
        <button type="submit" className="btn-secondary">
          검색
        </button>
      </form>
      {open && <RecordDetail rec={open} onClose={() => setOpen(null)} />}
      {page && (
        <>
          <RecordTable rows={page.items} showActor onOpen={openRow} openId={open?.id ?? null} />
          {page.items.length === 0 && <p className="adm-hint">이 조건의 기록이 없습니다.</p>}
          {page.more && page.next_before && (
            <button type="button" className="btn-secondary" onClick={() => search({ ...f, before: page.next_before ?? undefined })}>
              더 보기
            </button>
          )}
        </>
      )}
      {!page && <p className="adm-hint">조건을 고르고 검색합니다 — 검색도 감사 기록에 남습니다.</p>}
    </Page>
  );
}
