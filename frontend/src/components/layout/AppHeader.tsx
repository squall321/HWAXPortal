import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { listSystems, type SystemTile } from '../../api/systems.api';
import { useAuth } from '../../auth/useAuth';

// 화면 전환마다 AppShell 이 재마운트돼 카탈로그를 다시 받지 않게 모듈 수준에서 한 번만 받는다.
let catalogOnce: Promise<SystemTile[]> | null = null;
function loadCatalogOnce(): Promise<SystemTile[]> {
  if (!catalogOnce) {
    catalogOnce = listSystems().catch((err) => {
      catalogOnce = null; // 실패는 캐시하지 않는다.
      throw err;
    });
  }
  return catalogOnce;
}

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
  // '리스크 심사' 는 카탈로그에 hwax-risk 타일이 보이는 사용자에게만 뜬다(env 플래그 없음).
  const [hasRiskTile, setHasRiskTile] = useState(false);
  useEffect(() => {
    if (!user) return;
    loadCatalogOnce()
      .then((systems) => setHasRiskTile(systems.some((s) => s.id === 'hwax-risk')))
      .catch(() => setHasRiskTile(false));
  }, [user]);
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        // 전체화면 챗('/')이 calc(100dvh - var(--hdr-h))로 정확히 채우도록 높이를 토큰에 고정.
        height: 'var(--hdr-h)',
        padding: '0 1.5rem',
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
            <NavLink to="/deliberate" style={navLinkStyle}>
              심의
            </NavLink>
            <NavLink to="/apps" style={navLinkStyle}>
              앱
            </NavLink>
            <NavLink to="/tokens" style={navLinkStyle}>
              API 토큰
            </NavLink>
            {hasRiskTile && (
              <NavLink to="/risk" style={navLinkStyle}>
                리스크 심사
              </NavLink>
            )}
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
