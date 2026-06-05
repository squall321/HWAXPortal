import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { Spinner } from '../components/common/Spinner';

export default function LoginPage() {
  const { status, login } = useAuth();
  const loc = useLocation() as { state?: { from?: string } };
  const returnTo = loc.state?.from ?? '/';

  if (status === 'loading') return <Spinner label="Checking sign-in…" />;
  if (status === 'authenticated') return <Navigate to="/" replace />;

  return (
    <main className="app-shell" style={{ textAlign: 'center', paddingTop: '6rem' }}>
      <h1>HWAX Portal</h1>
      <p style={{ color: 'var(--muted)' }}>Sign in with your Samsung AD account to continue.</p>
      <button className="btn-primary" style={{ marginTop: '1.5rem' }} onClick={() => login(returnTo)}>
        Sign in with Samsung AD
      </button>
    </main>
  );
}
