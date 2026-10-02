// 접속 이력(관리자 전용) — 누가(이메일) 어디서(IP) 언제 어느 서비스에 들어갔나(docs/access-history)
import { useCallback, useEffect, useState } from 'react';
import { Page, PageHeader } from '../../components/ui/Page';
import {
  fetchAccessLedger,
  fetchAccountRequests,
  type AccessLedger,
  type AccountRequests,
} from '../../api/accessHistory.api';
import { useAuth } from '../../auth/useAuth';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import '../../styles/admin.css';

function when(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

const EVENT_LABEL: Record<string, string> = {
  login: '로그인',
  login_fail: '로그인 실패',
  launch: '서비스 진입',
  open: '타일 열기',
};

const DETAIL_LABEL: Record<string, string> = {
  local: '이메일 로그인',
  sso: 'SSO',
  primer: '자동 갱신',
  credential: '자격 중계',
};

function detailText(d: string | null): string {
  if (!d) return '';
  if (d.startsWith('local:')) return `이메일 로그인 — ${d.slice(6)}`;
  return DETAIL_LABEL[d] ?? d;
}

export default function AccessHistoryPage() {
  const { user } = useAuth();
  const [email, setEmail] = useState('');
  const [service, setService] = useState('');
  const [days, setDays] = useState(7);
  const [includeAuto, setIncludeAuto] = useState(false);
  const [ledger, setLedger] = useState<AccessLedger | null>(null);
  const [reqs, setReqs] = useState<AccountRequests | null>(null);
  const [loadingReqs, setLoadingReqs] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (q: { email: string; service: string; days: number; includeAuto: boolean }) => {
      setError(null);
      setReqs(null);
      fetchAccessLedger({ email: q.email.trim(), service: q.service.trim(), days: q.days, includeAuto: q.includeAuto })
        .then(setLedger)
        .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'));
    },
    [],
  );
  useEffect(() => load({ email: '', service: '', days: 7, includeAuto: false }), [load]);

  const isAdmin = user?.groups.includes('portal-admin');
  // 페이지 틀 안에서 — 화면 끝까지 붙은 오류 띠만 덩그러니 보였다
  if (!isAdmin)
    return (
      <Page width="wide">
        <PageHeader title="접속 이력" />
        <ErrorBanner message="관리자(portal-admin)만 볼 수 있는 페이지입니다." />
      </Page>
    );

  const search = () => load({ email, service, days, includeAuto });
  const pick = (e: string) => {
    setEmail(e);
    load({ email: e, service, days, includeAuto });
  };
  const loadRequests = () => {
    setLoadingReqs(true);
    setError(null);
    fetchAccountRequests(email.trim(), Math.min(days, 14))
      .then(setReqs)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '불러오기 실패'))
      .finally(() => setLoadingReqs(false));
  };

  return (
    <Page width="wide">
      <PageHeader
        title="접속 이력"
        desc={
          <>
            포털 로그인과 타일로 서비스에 들어간 기록입니다. IP 는 포털이 본 주소이고 사람과 1:1 이 아닙니다(사내 NAT).
            각 서비스 안에서 다시 들어온 것은 여기 없고, 계정을 고르면 <b>정문 요청(최근 14일)</b>으로 봅니다.
          </>
        }
      />
      {error && <ErrorBanner message={error} />}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
        className="adm-filter"
      >
        <input
          id="access-email"
          placeholder="계정(이메일)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          id="access-service"
          placeholder="서비스 id (예: heax-hub)"
          value={service}
          onChange={(e) => setService(e.target.value)}
        />
        <select id="access-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[1, 7, 14, 30, 90, 365].map((d) => (
            <option key={d} value={d}>
              최근 {d}일
            </option>
          ))}
        </select>
        <label>
          <input
            id="access-auto"
            type="checkbox"
            checked={includeAuto}
            onChange={(e) => setIncludeAuto(e.target.checked)}
          />{' '}
          자동 갱신 포함
        </label>
        <button type="submit" className="btn-secondary">
          조회
        </button>
        {email.trim() && (
          <button type="button" className="btn-secondary" onClick={loadRequests} disabled={loadingReqs}>
            {loadingReqs ? '정문 요청 읽는 중…' : '이 계정의 정문 요청'}
          </button>
        )}
      </form>

      {reqs && (
        <div className="adm-sec">
          <h3>
            {reqs.email} — 정문 요청 최근 {reqs.days}일 (로그인 {reqs.logins}회)
          </h3>
          {reqs.note && <p className="adm-hint">{reqs.note}</p>}
          {reqs.services.length > 0 && (
            <div className="adm-table-wrap">
              <table className="adm-table">
                <thead>
                  <tr>
                    <th>서비스</th>
                    <th className="adm-num">요청</th>
                    <th>처음</th>
                    <th>마지막</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {reqs.services.map((s) => (
                    <tr key={s.service}>
                      <td>{s.service}</td>
                      <td className="adm-num">{s.requests.toLocaleString()}</td>
                      <td>{when(s.first)}</td>
                      <td>{when(s.last)}</td>
                      <td>{s.ips.join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {reqs.services.length === 0 && !reqs.note && (
            <p className="adm-hint">이 기간에 정문을 지난 요청이 없습니다.</p>
          )}
        </div>
      )}

      {!ledger && !error && <Spinner label="접속 이력 불러오는 중…" />}
      {ledger && (
        <div className="adm-table-wrap">
          <table className="adm-table">
            <thead>
              <tr>
                <th>시각</th>
                <th>계정</th>
                <th>무엇</th>
                <th>서비스</th>
                <th>IP</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              {ledger.rows.map((r, i) => (
                <tr key={`${r.ts}-${i}`}>
                  <td className="adm-nowrap">{when(r.ts)}</td>
                  <td>
                    <button
                      type="button"
                      className="adm-linkbtn"
                      onClick={() => pick(r.email)}
                      aria-label={`${r.email} 만 보기`}
                    >
                      {r.email}
                    </button>
                  </td>
                  <td>{EVENT_LABEL[r.event] ?? r.event}</td>
                  <td>{r.service ?? '—'}</td>
                  <td>{r.ip ?? '—'}</td>
                  <td className="adm-muted-cell">{detailText(r.detail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {ledger.rows.length === 0 && (
            <p className="adm-hint">이 조건의 기록이 없습니다.</p>
          )}
          {ledger.truncated && (
            <p className="adm-hint">
              최근 {ledger.rows.length}건까지만 보입니다 — 계정이나 서비스로 좁혀 보세요.
            </p>
          )}
        </div>
      )}
    </Page>
  );
}
