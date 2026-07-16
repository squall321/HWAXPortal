import { NavLink } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  color: isActive ? 'var(--fg)' : 'var(--muted)',
  textDecoration: 'none',
  fontSize: '0.9rem',
  fontWeight: isActive ? 700 : 500,
  padding: '0.32rem 0.72rem',
  borderRadius: '8px',
  background: isActive ? 'rgba(255, 255, 255, 0.06)' : 'transparent',
});

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
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem' }}>
        <strong style={{ color: 'var(--fg)' }}>HWAX Portal</strong>
        <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>hwax.sec.samsung.net</span>
        {user && (
          <nav style={{ display: 'flex', gap: '0.25rem' }}>
            {/* 챗이 메인('/'), 앱 카탈로그가 보조('/apps'). */}
            <NavLink to="/" style={navLinkStyle} end>
              챗
            </NavLink>
            <NavLink to="/apps" style={navLinkStyle}>
              앱
            </NavLink>
            <NavLink to="/tokens" style={navLinkStyle}>
              API 토큰
            </NavLink>
          </nav>
        )}
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
