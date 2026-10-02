// 로그인 페이지 — 이메일 로컬 계정(가입 신청 포함) + SSO 버튼. SSO 지연 브리지.
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { localLogin, localSignup } from '../api/auth.api';
import { useAuth } from '../auth/useAuth';
import { Spinner } from '../components/common/Spinner';
import { BrandMark } from '../components/ui/BrandMark';
import '../styles/login.css';

export default function LoginPage() {
  const { status, login, refresh } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const returnTo = loc.state?.from ?? '/';

  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [department, setDepartment] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // 이메일 로그인은 접어 둔다 — 운영 SSO 가 열려 주 경로가 SSO 다(2026-10-02). 가입·오류·안내가 있으면 펼친 채로.
  const [localOpen, setLocalOpen] = useState(false);
  // SSO 콜백 실패 — 서버가 흰 JSON 화면 대신 이리 돌려보낸다(/login?error=sso&detail=원인). 원인은 접어 둔 '자세히' 에.
  const [params] = useSearchParams();
  const ssoError = params.get('error') === 'sso';
  const ssoDetail = params.get('detail') ?? '';

  if (status === 'loading') return <Spinner label="로그인 확인 중…" />;
  if (status === 'authenticated') return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      if (mode === 'login') {
        await localLogin(email, password);
        await refresh();
        navigate(returnTo, { replace: true });
      } else {
        const st = await localSignup(email, name, password, department);
        if (st === 'active') {
          setNotice('가입이 완료됐습니다. 바로 로그인하세요.');
        } else {
          setNotice('가입 신청이 접수됐습니다. 관리자 승인 후 로그인할 수 있습니다.');
        }
        setMode('login');
        setPassword('');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '요청이 실패했습니다.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <div className="login-card">
        <div className="login-brand">
          <BrandMark size={36} />
          <span>
            HWAX <span className="login-brand-sub">Portal</span>
          </span>
        </div>
        <p className="login-sub">사내 AI·해석 플랫폼을 한 곳에서 — 회사 계정으로 들어갑니다.</p>

        {ssoError && (
          <div className="login-fail" role="alert">
            <b>SSO 로그인을 마치지 못했습니다.</b> 잠시 뒤 다시 시도하세요. 계속되면 아래 내용을
            포털 관리자에게 알려 주세요.
            {ssoDetail && (
              <details>
                <summary>자세히</summary>
                <code>{ssoDetail}</code>
              </details>
            )}
          </div>
        )}
        <button type="button" className="btn-primary login-sso" onClick={() => login(returnTo)}>
          {ssoError ? '삼성 AD 계정으로 다시 로그인' : '삼성 AD 계정으로 로그인'}
        </button>

        <details
          className="login-local"
          open={localOpen || mode === 'signup' || Boolean(error) || Boolean(notice)}
          onToggle={(e) => setLocalOpen((e.target as HTMLDetailsElement).open)}
        >
          <summary>SSO 를 쓸 수 없나요? 이메일 계정으로 로그인</summary>
          <p className="login-local-note">
            {mode === 'login'
              ? '회사 이메일 그대로 만든 계정이면 SSO 로 들어와도 같은 계정입니다.'
              : '회사 이메일로 가입을 신청하세요. 관리자 승인 후 사용할 수 있습니다.'}
          </p>
          <form onSubmit={submit} className="login-form">
            <label className="login-field">
              <span>이메일</span>
              <input
                type="email"
                placeholder="회사 계정"
                value={email}
                autoComplete="username"
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            {mode === 'signup' && (
              <>
                <label className="login-field">
                  <span>이름</span>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </label>
                <label className="login-field">
                  <span>부서 (선택)</span>
                  <input
                    type="text"
                    placeholder="Report Archive 연결 시 자동 채움"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                  />
                </label>
              </>
            )}
            <label className="login-field">
              <span>비밀번호</span>
              <input
                type="password"
                placeholder={mode === 'signup' ? '8자 이상' : undefined}
                value={password}
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                minLength={mode === 'signup' ? 8 : undefined}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && (
              <p className="login-msg login-msg-err" role="alert">
                {error}
              </p>
            )}
            {notice && <p className="login-msg">{notice}</p>}
            <button className="btn-secondary login-submit" disabled={busy}>
              {busy ? '처리 중…' : mode === 'login' ? '이메일로 로그인' : '가입 신청'}
            </button>
          </form>
          <p className="login-switch">
            {mode === 'login' ? (
              <>
                계정이 없나요?{' '}
                <button
                  type="button"
                  className="login-link"
                  onClick={() => {
                    setMode('signup');
                    setError(null);
                  }}
                >
                  가입 신청
                </button>
              </>
            ) : (
              <>
                이미 계정이 있나요?{' '}
                <button
                  type="button"
                  className="login-link"
                  onClick={() => {
                    setMode('login');
                    setError(null);
                  }}
                >
                  로그인
                </button>
              </>
            )}
          </p>
        </details>
      </div>
    </main>
  );
}
