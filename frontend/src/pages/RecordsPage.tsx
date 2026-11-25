// 내 기록 — 내 웹 챗 · 심의 · 개인 Claude 도구 호출 · 공유한 Claude 대화를 한 줄로 보고 찾고, 전부 지우기를 청한다(docs/interaction-data contract §6)
import { useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../components/ui/Page';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { Spinner } from '../components/common/Spinner';
import { RecordDetail, RecordTable } from '../components/records/RecordView';
import {
  ERASE_CONFIRM,
  SURFACE_LABEL,
  eraseMine,
  fetchInteractionStatus,
  getMine,
  listMine,
  type InteractionFull,
  type InteractionPage,
} from '../api/interactions.api';
import '../styles/admin.css';
import '../styles/records.css';

export default function RecordsPage() {
  const [on, setOn] = useState<boolean | null>(null);
  const [notice, setNotice] = useState('');
  const [q, setQ] = useState('');
  const [surface, setSurface] = useState('');
  const [page, setPage] = useState<InteractionPage | null>(null);
  const [open, setOpen] = useState<InteractionFull | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState('');
  const [erased, setErased] = useState<string | null>(null);

  useEffect(() => {
    void fetchInteractionStatus().then((s) => {
      setOn(!!s);
      setNotice(s?.notice ?? '');
    });
  }, []);

  const load = useCallback((p: { q: string; surface: string; before?: string }) => {
    setError(null);
    listMine(p)
      .then((got) => setPage((prev) => (p.before && prev ? { ...got, items: [...prev.items, ...got.items] } : got)))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'));
  }, []);
  useEffect(() => {
    if (on) load({ q: '', surface: '' });
  }, [on, load]);

  if (on === null) return <Spinner label="불러오는 중…" />;
  if (!on)
    return (
      <Page>
        <PageHeader title="내 기록" />
        <ErrorBanner message="이 포털 박스는 상호작용 기록을 켜지 않았습니다." />
      </Page>
    );

  const openRow = (id: string) => {
    setError(null);
    getMine(id)
      .then(setOpen)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '열지 못했습니다'));
  };
  const erase = () => {
    setError(null);
    eraseMine()
      .then((r) => {
        setErased(`사건 ${r.events.toLocaleString()}건 · 공유 대화 ${r.shared.toLocaleString()}건을 지웠습니다.`);
        setConfirm('');
        setOpen(null);
        load({ q, surface });
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '지우지 못했습니다'));
  };

  return (
    <Page width="wide">
      <PageHeader title="내 기록" desc={notice} />
      {error && <ErrorBanner message={error} />}
      <form
        className="adm-filter"
        onSubmit={(e) => {
          e.preventDefault();
          load({ q, surface });
        }}
      >
        <input id="rec-q" placeholder="찾을 말" value={q} onChange={(e) => setQ(e.target.value)} />
        <select id="rec-surface" value={surface} onChange={(e) => setSurface(e.target.value)}>
          <option value="">전부</option>
          {Object.entries(SURFACE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <button type="submit" className="btn-secondary">
          찾기
        </button>
      </form>
      {open && <RecordDetail rec={open} onClose={() => setOpen(null)} />}
      {!page && !error && <Spinner label="내 기록 불러오는 중…" />}
      {page && (
        <>
          <RecordTable rows={page.items} showActor={false} onOpen={openRow} openId={open?.id ?? null} />
          {page.items.length === 0 && <p className="adm-hint">이 조건의 기록이 없습니다.</p>}
          {page.more && page.next_before && (
            <button
              type="button"
              className="btn-secondary"
              onClick={() => load({ q, surface, before: page.next_before ?? undefined })}
            >
              더 보기
            </button>
          )}
        </>
      )}
      <div className="adm-sec rec-erase">
        <h3>전부 지우기 청구</h3>
        <p className="adm-hint">
          내 기록(웹 챗 · 심의 · 도구 호출 · 공유한 대화)을 이 원장에서 모두 지웁니다. 지운 시각 전의 일은 다시 들어오지 않고, 그 뒤의 일은 다시
          기록됩니다. 대화 화면의 대화 자체는 그대로입니다. 계속하려면 아래에 「{ERASE_CONFIRM}」 을 적습니다.
        </p>
        <div className="adm-filter">
          <input id="rec-erase" placeholder={ERASE_CONFIRM} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <button type="button" className="btn-secondary" disabled={confirm !== ERASE_CONFIRM} onClick={erase}>
            전부 지우기
          </button>
        </div>
        {erased && <p className="adm-hint">{erased}</p>}
      </div>
    </Page>
  );
}
