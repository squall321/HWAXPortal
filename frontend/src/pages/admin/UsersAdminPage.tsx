// 사용자 관리(관리자 전용) — 가입 승인·비활성·비밀번호 재설정. SSO 지연 브리지의 운영 화면.
import { useCallback, useEffect, useState } from 'react';
import {
  approveLocalUser,
  listLocalUsers,
  resetLocalUserPassword,
  setLocalUserStatus,
  type LocalUserRow,
} from '../../api/auth.api';
import { useAuth } from '../../auth/useAuth';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';

const cell: React.CSSProperties = { padding: '0.5rem 0.7rem', borderBottom: '1px solid var(--border)' };

function when(ts: number | null): string {
  return ts ? new Date(ts * 1000).toLocaleString() : '—';
}

const STATUS_LABEL: Record<LocalUserRow['status'], string> = {
  pending: '승인 대기',
  active: '활성',
  disabled: '비활성',
};

export default function UsersAdminPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<LocalUserRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null); // 작업 중인 이메일

  const reload = useCallback(() => {
    listLocalUsers()
      .then(setRows)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'));
  }, []);
  useEffect(() => reload(), [reload]);

  const run = async (email: string, fn: () => Promise<void>) => {
    setBusy(email);
    setError(null);
    try {
      await fn();
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : '요청 실패');
    } finally {
      setBusy(null);
    }
  };

  const isAdmin = user?.groups.includes('portal-admin');
  if (!isAdmin) return <ErrorBanner message="관리자(portal-admin)만 볼 수 있는 페이지입니다." />;
  if (error && !rows) return <ErrorBanner message={error} />;
  if (!rows) return <Spinner label="사용자 목록 불러오는 중…" />;

  const pending = rows.filter((r) => r.status === 'pending');

  return (
    <section style={{ maxWidth: '60rem', margin: '0 auto', padding: '1.5rem' }}>
      <h2>사용자 관리</h2>
      <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
        가입은 승인제입니다. 승인·역할 변경은 해당 사용자의 다음 로그인부터 반영됩니다.
        {pending.length > 0 && <strong> 승인 대기 {pending.length}건.</strong>}
      </p>
      {error && <ErrorBanner message={error} />}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ color: 'var(--muted)', textAlign: 'left' }}>
              <th style={cell}>이메일</th>
              <th style={cell}>이름</th>
              <th style={cell}>상태</th>
              <th style={cell}>역할</th>
              <th style={cell}>로그인 수단</th>
              <th style={cell}>마지막 로그인</th>
              <th style={cell}>작업</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.email}>
                <td style={cell}>{r.email}</td>
                <td style={cell}>{r.name}</td>
                <td style={cell}>
                  {STATUS_LABEL[r.status]}
                  {r.locked_until * 1000 > Date.now() && ' · 잠금'}
                </td>
                <td style={cell}>{r.groups.join(', ') || '—'}</td>
                <td style={cell}>{r.auth_source === 'sso' ? 'SSO' : '이메일'}</td>
                <td style={cell}>{when(r.last_login_at)}</td>
                <td style={{ ...cell, whiteSpace: 'nowrap' }}>
                  {r.status === 'pending' && (
                    <>
                      <button
                        className="btn-primary"
                        disabled={busy === r.email}
                        onClick={() => void run(r.email, () => approveLocalUser(r.email, []))}
                      >
                        승인
                      </button>{' '}
                      <button
                        className="btn-secondary"
                        disabled={busy === r.email}
                        onClick={() =>
                          void run(r.email, () => approveLocalUser(r.email, ['portal-admin']))
                        }
                      >
                        관리자로 승인
                      </button>
                    </>
                  )}
                  {r.status === 'active' && r.email !== user?.email && (
                    <button
                      className="btn-secondary"
                      disabled={busy === r.email}
                      onClick={() => void run(r.email, () => setLocalUserStatus(r.email, 'disabled'))}
                    >
                      비활성화
                    </button>
                  )}
                  {r.status === 'disabled' && (
                    <button
                      className="btn-secondary"
                      disabled={busy === r.email}
                      onClick={() => void run(r.email, () => setLocalUserStatus(r.email, 'active'))}
                    >
                      다시 활성화
                    </button>
                  )}{' '}
                  {r.status !== 'pending' && (
                    <button
                      className="btn-secondary"
                      disabled={busy === r.email}
                      onClick={() => {
                        const pw = window.prompt(`${r.email} 의 새 비밀번호(8자 이상):`);
                        if (pw && pw.length >= 8) {
                          void run(r.email, () => resetLocalUserPassword(r.email, pw));
                        } else if (pw !== null) {
                          setError('비밀번호는 8자 이상이어야 합니다.');
                        }
                      }}
                    >
                      비번 재설정
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
