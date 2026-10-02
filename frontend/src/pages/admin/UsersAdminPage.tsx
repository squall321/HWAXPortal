// 사용자 관리(관리자 전용) — 가입 승인·비활성·비밀번호 재설정·소속과 권한. SSO 지연 브리지의 운영 화면.
import { Fragment, useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import { fetchAccessPolicy, type AccessPolicy } from '../../api/access.api';
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
import { AccessRequestsPanel, AffiliationSelect, BulkAffiliation, GrantEditor } from './AccessAdmin';
import { SetupRequests } from '../../components/admin/SetupRequests';
import '../../styles/admin.css';

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
  const [policy, setPolicy] = useState<AccessPolicy | null>(null);
  const [editing, setEditing] = useState<string | null>(null); // 개별 허가를 펼친 이메일
  useEffect(() => {
    fetchAccessPolicy().then(setPolicy).catch(() => setPolicy(null));
  }, []);

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
  // 페이지 틀 안에서 — 화면 끝까지 붙은 오류 띠만 덩그러니 보였다
  if (!isAdmin || (error && !rows))
    return (
      <Page width="wide">
        <PageHeader title="사용자 관리" />
        <ErrorBanner message={!isAdmin ? '관리자(portal-admin)만 볼 수 있는 페이지입니다.' : (error as string)} />
      </Page>
    );
  if (!rows) return <Spinner label="사용자 목록 불러오는 중…" />;

  const pending = rows.filter((r) => r.status === 'pending');

  return (
    <Page width="wide">
      <PageHeader
        title="사용자 관리"
        desc={
          <>
            가입은 승인제입니다. 관리자 역할은 다음 로그인부터, <b>소속·권한은 곧바로</b> 반영됩니다.
            {pending.length > 0 && <strong> 승인 대기 {pending.length}건.</strong>}
          </>
        }
      />
      {error && <ErrorBanner message={error} />}
      <SetupRequests />
      <AccessRequestsPanel policy={policy} onChanged={reload} />
      <BulkAffiliation policy={policy} rows={rows} onChanged={reload} /> 
      <div className="adm-table-wrap">
        <table className="adm-table">
          <thead>
            <tr>
              <th>이메일</th>
              <th>이름</th>
              <th>부서</th>
              <th>소속</th>
              <th>개별 허가</th>
              <th>상태</th>
              <th>역할</th>
              <th>로그인 수단</th>
              <th>마지막 로그인</th>
              <th>작업</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.email}>
              <tr>
                <td>{r.email}</td>
                <td>{r.name || '—'}</td>
                <td>{r.department || '—'}</td>
                <td>
                  <AffiliationSelect policy={policy} row={r} onSaved={reload} onError={setError} />
                </td>
                <td>
                  {(r.grants ?? []).length}건{' '}
                  {policy && (
                    <button className="btn-secondary" onClick={() => setEditing(editing === r.email ? null : r.email)}>
                      {editing === r.email ? '접기' : '편집'}
                    </button>
                  )}
                </td>
                <td>
                  {STATUS_LABEL[r.status]}
                  {r.locked_until * 1000 > Date.now() && ' · 잠금'}
                </td>
                <td>{r.groups.join(', ') || '—'}</td>
                <td>{r.auth_source === 'sso' ? 'SSO' : '이메일'}</td>
                <td>{when(r.last_login_at)}</td>
                <td>
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
              {editing === r.email && policy && (
                <tr>
                  <td colSpan={10}>
                    <GrantEditor policy={policy} row={r} onSaved={reload} onClose={() => setEditing(null)} />
                  </td>
                </tr>
              )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
