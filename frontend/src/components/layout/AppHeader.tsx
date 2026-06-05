import { useAuth } from '../../auth/useAuth';

export function AppHeader() {
  const { user, logout } = useAuth();
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.75rem 1.5rem',
        borderBottom: '1px solid var(--border)',
        background: 'var(--card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <strong style={{ color: 'var(--fg)' }}>HWAX Portal</strong>
        <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>hwax.sec.samsung.net</span>
      </div>
      {user && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>{user.email}</span>
          <button onClick={() => void logout()} className="btn-secondary">
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
