// 사용자 관리(관리자 전용) — 가입 승인·비활성·비밀번호 재설정·소속과 권한. SSO 지연 브리지의 운영 화면.
import { Fragment, useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import { fetchAccessPolicy, type AccessPolicy } from '../../api/access.api';
import {
  approveLocalUser,
  isUnassigned,
  listLocalUsers,
  resetLocalUserPassword,
  setLocalUserStatus,
  type LocalUserRow,
} from '../../api/auth.api';
import { useAuth } from '../../auth/useAuth';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { AccessRequestsPanel, AdminToggle, AffiliationSelect, BulkAffiliation, GrantEditor } from './AccessAdmin';
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
  const [onlyUnassigned, setOnlyUnassigned] = useState(false); // 소속 미지정만 보기
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
  // 한 사람씩 소속을 정할 때 — 일괄 지정으로는 누가 그 소속 사람인지 가릴 수 없다. 마지막 한 명을 지정해 0명이 되면 전체로 돌아간다
  // (필터가 켜진 채 빈 표만 남지 않게).
  const unassigned = rows.filter(isUnassigned);
  const shown = onlyUnassigned && unassigned.length > 0 ? unassigned : rows;

  return (
    <Page width="wide">
      <PageHeader
        title="사용자 관리"
        desc={
          <>
            가입은 승인제입니다. <b>관리자 지정·해제와 소속·권한은 곧바로</b> 반영됩니다(다시 로그인할 필요가 없습니다).
            {pending.length > 0 && <strong> 승인 대기 {pending.length}건.</strong>}
          </>
        }
      />
      {error && <ErrorBanner message={error} />}
      <SetupRequests />
      <AccessRequestsPanel policy={policy} onChanged={reload} />
      <BulkAffiliation policy={policy} rows={rows} onChanged={reload} /> 
      <div className="adm-filter">
        <label>
          <input
            type="checkbox"
            checked={onlyUnassigned && unassigned.length > 0}
            disabled={unassigned.length === 0}
            onChange={(e) => setOnlyUnassigned(e.target.checked)}
          />{' '}
          소속 미지정만 보기({unassigned.length}명)
        </label>
      </div>
      <div className="adm-table-wrap">
        <table className="adm-table">
          <thead>
            <tr>
              <th>이메일</th>
              <th>이름</th>
              <th>부서 · 코드</th>
              <th>소속</th>
              <th>개별 허가</th>
              <th>상태</th>
              <th>역할</th>
              <th>로그인 수단</th>
              <th>생성</th>
              <th>마지막 로그인</th>
              <th>작업</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <Fragment key={r.email}>
              <tr>
                <td>{r.email}</td>
                <td>{r.name || '—'}</td>
                <td>
                  {r.department || (r.dept_id ? '' : '—')}
                  {r.dept_id && <span className="adm-meta"> {r.dept_id}</span>}
                </td>
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
                <td>
                  <AdminToggle row={r} self={r.email === user?.email} onSaved={reload} onError={setError} />
                  {r.groups.some((g) => g !== 'portal-admin') && (
                    <span className="adm-meta"> {r.groups.filter((g) => g !== 'portal-admin').join(', ')}</span>
                  )}
                </td>
                <td>{r.auth_source === 'sso' ? 'SSO' : '이메일'}</td>
                <td className="adm-nowrap">{when(r.created_at)}</td>
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
                  <td colSpan={11}>
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
