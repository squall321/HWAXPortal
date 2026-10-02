// 내 권한 — 모든 기능·플랫폼에 대해 쓸 수 있나·왜·요청(없는 것은 여기서 청하고 관리자가 승인한다)
import { useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../components/ui/Page';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchMyAccess, requestAccess, type AccessRow, type MyAccess } from '../api/access.api';
import { useAuth } from '../auth/useAuth';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { Spinner } from '../components/common/Spinner';
import { IconCheck } from '../components/chat/icons';
import '../styles/access.css';

function Row({
  row,
  focus,
  onRequested,
}: {
  row: AccessRow;
  focus: boolean;
  onRequested: () => void;
}) {
  const [open, setOpen] = useState(focus);
  const [note, setNote] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const req = row.request;
  const send = async () => {
    setBusy(true);
    setErr('');
    try {
      await requestAccess(row.key, note);
      setOpen(false);
      onRequested();
    } catch (e) {
      setErr(e instanceof Error ? e.message : '요청 실패');
    } finally {
      setBusy(false);
    }
  };
  return (
    <li id={row.key} className={`acc-row${focus ? ' is-focus' : ''}`}>
      <div className="acc-row-main">
        <div className="acc-row-text">
          <strong>{row.label}</strong>
          {row.desc && <span className="acc-row-desc">{row.desc}</span>}
        </div>
        {req?.status === 'pending' ? (
          <span className="acc-st acc-st-pending">
            요청 대기 중 · {new Date(req.created_at * 1000).toLocaleDateString()}
          </span>
        ) : (
          req?.status === 'rejected' && (
            <span className="acc-st acc-st-rejected">지난 요청 거절됨</span>
          )
        )}
        {req?.status !== 'pending' && !open && (
          <button className="btn-secondary acc-req" onClick={() => setOpen(true)}>
            {req?.status === 'rejected' ? '다시 요청' : '요청'}
          </button>
        )}
      </div>
      {open && req?.status !== 'pending' && (
        <div className="acc-req-form">
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="어디에 쓰는지 한 줄(선택) — 관리자가 승인할 때 봅니다"
            aria-label={`${row.label} 요청 사유`}
            maxLength={500}
            style={{ flex: '1 1 18rem', minWidth: 0 }}
          />
          <button className="btn-primary" disabled={busy} onClick={() => void send()}>
            요청 보내기
          </button>
          <button className="btn-secondary" onClick={() => setOpen(false)}>
            취소
          </button>
          {err && (
            <span className="acc-err" role="alert">
              {err}
            </span>
          )}
        </div>
      )}
    </li>
  );
}

export default function AccessPage() {
  const { refresh } = useAuth();
  const [params] = useSearchParams();
  const need = params.get('need') ?? '';
  const [data, setData] = useState<MyAccess | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    fetchMyAccess()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'));
  }, []);
  useEffect(() => {
    load();
    void refresh(); // 방금 승인됐을 수 있다 — 메뉴도 같이 따라가게
  }, [load, refresh]);

  if (error && !data)
    return (
      <Page>
        <PageHeader title="내 권한" />
        <ErrorBanner message={error} />
      </Page>
    );
  if (!data) return <Spinner label="권한 불러오는 중…" />;

  const needRow = [...data.features, ...data.platforms].find((r) => r.key === need);
  // 쓸 수 있는 것은 칩 한 줄로(이유는 툴팁) — 종전엔 '✓ 쓸 수 있음 · 관리자' 카드가 27개 반복됐다. 요청할 것만 줄로 남긴다.
  const section = (title: string, hint: string, rows: AccessRow[]) => {
    const ok = rows.filter((r) => r.allowed);
    const rest = rows.filter((r) => !r.allowed);
    return (
      <section className="acc-sec">
        <header className="acc-sec-head">
          <h2>{title}</h2>
          <span className="acc-count">
            {ok.length}/{rows.length} 사용 가능
          </span>
        </header>
        <p className="acc-hint">{hint}</p>
        {ok.length > 0 && (
          <ul className="acc-chips" aria-label={`${title} — 쓸 수 있음`}>
            {ok.map((r) => (
              <li
                key={r.key}
                id={r.key}
                className="acc-chip"
                title={[r.desc, `허가: ${r.reason}`].filter(Boolean).join(' — ')}
              >
                <IconCheck width={13} height={13} />
                {r.label}
              </li>
            ))}
          </ul>
        )}
        {rest.length > 0 && (
          <ul className="acc-list" aria-label={`${title} — 요청할 수 있음`}>
            {rest.map((r) => (
              <Row key={r.key} row={r} focus={r.key === need} onRequested={load} />
            ))}
          </ul>
        )}
      </section>
    );
  };
  const all = [...data.features, ...data.platforms];
  const pending = all.filter((r) => !r.allowed && r.request?.status === 'pending').length;

  return (
    <Page>
      <PageHeader
        title="내 권한"
        desc={
          data.is_admin
            ? '관리자 — 모든 기능과 플랫폼을 씁니다.'
            : data.affiliation
              ? `소속 ${data.affiliation_label || data.affiliation} — 소속 기본 권한에 개별 허가가 더해집니다.`
              : '소속이 지정되지 않았습니다 — 기본 권한(일반 챗)만 씁니다. 필요한 것을 아래에서 요청하세요.'
        }
        actions={
          data.is_admin ? <Link to="/admin/users">사용자 관리에서 요청 승인 →</Link> : undefined
        }
      />
      <p className="acc-summary">
        <span>
          쓸 수 있음 <b>{all.filter((r) => r.allowed).length}</b>
        </span>
        {pending > 0 && (
          <span>
            요청 대기 <b>{pending}</b>
          </span>
        )}
        <span>
          요청 가능 <b>{all.filter((r) => !r.allowed && r.request?.status !== 'pending').length}</b>
        </span>
      </p>
      {needRow && !needRow.allowed && (
        <div role="status" className="acc-need">
          <b>{needRow.label}</b> 권한이 없어 이 화면으로 왔습니다. 아래에서 요청하면 관리자가
          승인합니다.
        </div>
      )}
      {section('기능', '에이전트 기능 — 심의·Thinking·전문가와 대화 등.', data.features)}
      {section(
        '플랫폼',
        '앱 타일과 챗 도구 — 허가된 플랫폼의 도구만 챗에 붙습니다.',
        data.platforms,
      )}
    </Page>
  );
}
