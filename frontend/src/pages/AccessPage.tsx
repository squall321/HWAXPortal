// 내 권한 — 모든 기능·플랫폼에 대해 쓸 수 있나·왜·요청(없는 것은 여기서 청하고 관리자가 승인한다)
import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchMyAccess, requestAccess, type AccessRow, type MyAccess } from '../api/access.api';
import { useAuth } from '../auth/useAuth';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { Spinner } from '../components/common/Spinner';

const chip = (bg: string, fg: string): React.CSSProperties => ({
  fontSize: '0.75rem',
  padding: '0.1rem 0.5rem',
  borderRadius: 999,
  background: bg,
  color: fg,
  whiteSpace: 'nowrap',
});

function Row({ row, focus, onRequested }: { row: AccessRow; focus: boolean; onRequested: () => void }) {
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
    <li
      id={row.key}
      style={{
        display: 'grid',
        gap: '0.25rem',
        padding: '0.7rem 0.9rem',
        border: `1px solid ${focus ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 10,
        background: 'var(--card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        <strong style={{ color: 'var(--fg)' }}>{row.label}</strong>
        {row.allowed ? (
          <span style={chip('rgba(76, 175, 80, 0.16)', '#8fd694')}>✓ 쓸 수 있음 · {row.reason}</span>
        ) : req?.status === 'pending' ? (
          <span style={chip('rgba(255, 193, 7, 0.16)', '#ffd666')}>
            요청 대기 중 · {new Date(req.created_at * 1000).toLocaleDateString()}
          </span>
        ) : (
          <span style={chip('rgba(255, 255, 255, 0.06)', 'var(--muted)')}>
            권한 없음{req?.status === 'rejected' ? ' · 지난 요청 거절됨' : ''}
          </span>
        )}
        {!row.allowed && req?.status !== 'pending' && !open && (
          <button className="btn-secondary" style={{ marginLeft: 'auto' }} onClick={() => setOpen(true)}>
            {req?.status === 'rejected' ? '다시 요청' : '요청'}
          </button>
        )}
      </div>
      {row.desc && <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{row.desc}</span>}
      {open && !row.allowed && req?.status !== 'pending' && (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.3rem' }}>
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
          {err && <span style={{ color: 'var(--danger-fg, #f28b82)' }}>⚠ {err}</span>}
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

  if (error && !data) return <ErrorBanner message={error} />;
  if (!data) return <Spinner label="권한 불러오는 중…" />;

  const needRow = [...data.features, ...data.platforms].find((r) => r.key === need);
  const section = (title: string, hint: string, rows: AccessRow[]) => (
    <section style={{ marginTop: '1.4rem' }}>
      <h3 style={{ margin: '0 0 0.2rem' }}>
        {title} <span style={{ color: 'var(--muted)', fontSize: '0.85rem', fontWeight: 400 }}>
          {rows.filter((r) => r.allowed).length}/{rows.length}
        </span>
      </h3>
      <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0 0 0.6rem' }}>{hint}</p>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.5rem' }}>
        {rows.map((r) => (
          <Row key={r.key} row={r} focus={r.key === need} onRequested={load} />
        ))}
      </ul>
    </section>
  );

  return (
    <section style={{ maxWidth: '52rem', margin: '0 auto', padding: '1.5rem' }}>
      <h2 style={{ marginBottom: '0.3rem' }}>내 권한</h2>
      <p style={{ color: 'var(--muted)', margin: 0 }}>
        {data.is_admin
          ? '관리자 — 모든 기능과 플랫폼을 씁니다.'
          : data.affiliation
            ? `소속 ${data.affiliation_label || data.affiliation} — 소속 기본 권한에 개별 허가가 더해집니다.`
            : '소속이 지정되지 않았습니다 — 기본 권한(일반 챗)만 씁니다. 필요한 것을 아래에서 요청하세요.'}
        {data.is_admin && (
          <>
            {' '}
            <Link to="/admin/users">사용자 관리에서 요청 승인 →</Link>
          </>
        )}
      </p>
      {needRow && !needRow.allowed && (
        <div
          role="status"
          style={{
            marginTop: '0.9rem',
            padding: '0.6rem 0.9rem',
            borderRadius: 10,
            border: '1px solid var(--accent)',
            color: 'var(--fg)',
          }}
        >
          <b>{needRow.label}</b> 권한이 없어 이 화면으로 왔습니다. 아래에서 요청하면 관리자가 승인합니다.
        </div>
      )}
      {section('기능', '에이전트 기능 — 심의·Thinking·전문가와 대화 등.', data.features)}
      {section('플랫폼', '앱 타일과 챗 도구 — 허가된 플랫폼의 도구만 챗에 붙습니다.', data.platforms)}
    </section>
  );
}
