// 로그인 페이지 — 이메일 로컬 계정(가입 신청 포함) + SSO 버튼. SSO 지연 브리지.
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { localLogin, localSignup } from '../api/auth.api';
import { useAuth } from '../auth/useAuth';
import { Spinner } from '../components/common/Spinner';

const linkBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  padding: 0,
  color: 'var(--accent, #2563eb)',
  cursor: 'pointer',
  fontSize: 'inherit',
  textDecoration: 'underline',
};

const field: React.CSSProperties = {
  display: 'block',
  width: '100%',
  padding: '0.55rem 0.7rem',
  marginTop: '0.6rem',
  border: '1px solid var(--border)',
  borderRadius: '6px',
  background: 'var(--bg)',
  color: 'var(--fg)',
  fontSize: '0.95rem',
};

export default function LoginPage() {
  const { status, login, refresh } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const returnTo = loc.state?.from ?? '/';

  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (status === 'loading') return <Spinner label="Checking sign-in…" />;
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
        const st = await localSignup(email, name, password);
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
    <main className="app-shell" style={{ textAlign: 'center', paddingTop: '5rem' }}>
      <h1>HWAX Portal</h1>
      <p style={{ color: 'var(--muted)' }}>
        {mode === 'login'
          ? '이메일 계정으로 로그인하세요. 회사 이메일 그대로 쓰면 SSO 전환 후에도 계정이 이어집니다.'
          : '회사 이메일로 가입을 신청하세요. 관리자 승인 후 사용할 수 있습니다.'}
      </p>

      <form onSubmit={submit} style={{ maxWidth: '20rem', margin: '1.5rem auto 0', textAlign: 'left' }}>
        <input
          style={field}
          type="email"
          placeholder="이메일 (회사 계정)"
          value={email}
          autoComplete="username"
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        {mode === 'signup' && (
          <input
            style={field}
            type="text"
            placeholder="이름"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        )}
        <input
          style={field}
          type="password"
          placeholder={mode === 'signup' ? '비밀번호 (8자 이상)' : '비밀번호'}
          value={password}
          autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
          minLength={mode === 'signup' ? 8 : undefined}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && (
          <p style={{ color: 'var(--danger-fg, #b91c1c)', fontSize: '0.85rem', marginTop: '0.6rem' }}>{error}</p>
        )}
        {notice && (
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginTop: '0.6rem' }}>{notice}</p>
        )}
        <button className="btn-primary" style={{ width: '100%', marginTop: '0.9rem' }} disabled={busy}>
          {busy ? '처리 중…' : mode === 'login' ? '로그인' : '가입 신청'}
        </button>
      </form>

      <p style={{ marginTop: '0.9rem', fontSize: '0.9rem' }}>
        {mode === 'login' ? (
          <>
            계정이 없나요?{' '}
            <button style={linkBtn} type="button" onClick={() => { setMode('signup'); setError(null); }}>
              가입 신청
            </button>
          </>
        ) : (
          <>
            이미 계정이 있나요?{' '}
            <button style={linkBtn} type="button" onClick={() => { setMode('login'); setError(null); }}>
              로그인
            </button>
          </>
        )}
      </p>

      <div style={{ margin: '1.6rem auto 0', maxWidth: '20rem', borderTop: '1px solid var(--border)', paddingTop: '1.1rem' }}>
        <button className="btn-secondary" style={{ width: '100%' }} onClick={() => login(returnTo)}>
          Sign in with Samsung AD (SSO)
        </button>
      </div>
    </main>
  );
}
