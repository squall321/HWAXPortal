// 앱 헤더 — [브랜드] 주 메뉴(챗·심의·앱·절차) …… [관리 ▾](관리자) [계정 ▾]. 좁으면 주 메뉴를 시트로 접는다(docs/ui-refresh 단계 2)
import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';
import { useCan } from '../../auth/useCan';
import { Menu, MenuSep } from '../ui/Menu';
import '../../styles/header.css';

type Item = { to: string; label: string; end?: boolean };

function BrandMark() {
  return (
    <svg className="app-brand-mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--primary)" />
      <path d="M10 9v14M22 9v14M10 16h12" stroke="#fff" strokeWidth="3" strokeLinecap="round" fill="none" />
    </svg>
  );
}

function Chevron() {
  return (
    <svg className="menu-chev" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AppHeader() {
  const { user, logout } = useAuth();
  // 권한이 없는 메뉴는 비활성으로 두지 않고 아예 숨긴다(사용자 요구 — docs/access-control).
  const can = useCan();
  const [sheet, setSheet] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setSheet(false), [pathname]);

  if (!user) {
    return (
      <header className="app-header">
        <span className="app-brand">
          <BrandMark />
          HWAX <span className="app-brand-sub">Portal</span>
        </span>
      </header>
    );
  }

  const isAdmin = user.groups.includes('portal-admin');
  // 같은 페이지가 PAT 발급과 Report Archive 연결(내 조직 선택)을 담는다 — 토큰 권한이 없어도 RA 를 쓰는 사람은 들어가야 한다.
  const canTokens = can('feat:api-token') || can('plat:reportarchive');
  const primary: Item[] = [
    { to: '/', label: '챗', end: true },
    ...(can('feat:deliberation') ? [{ to: '/deliberate', label: '심의' }] : []),
    { to: '/apps', label: '앱' },
    ...(can('feat:procedures') ? [{ to: '/procedures', label: '절차' }] : []),
  ];
  const admin: Item[] = isAdmin
    ? [
        { to: '/admin/users', label: '사용자 관리' },
        { to: '/admin/access', label: '접속 이력' },
      ]
    : [];
  const account: Item[] = [
    { to: '/access', label: '내 권한' },
    ...(canTokens ? [{ to: '/tokens', label: can('feat:api-token') ? '개인 토큰' : '연결 설정' }] : []),
    { to: '/updates', label: '업데이트 이력' },
  ];
  const name = (user.display_name || '').trim() || user.email.split('@')[0];

  return (
    <header className="app-header">
      <NavLink to="/" end className="app-brand" aria-label="HWAX Portal — 챗으로">
        <BrandMark />
        HWAX <span className="app-brand-sub">Portal</span>
      </NavLink>

      <nav className="app-nav" aria-label="주 메뉴">
        {primary.map((i) => (
          <NavLink key={i.to} to={i.to} end={i.end}>
            {i.label}
          </NavLink>
        ))}
      </nav>

      <div className="app-right">
        {admin.length > 0 && (
          <Menu className="hdr-admin" label={<>관리<Chevron /></>}>
            {admin.map((i) => (
              <NavLink key={i.to} to={i.to} role="menuitem">
                {i.label}
              </NavLink>
            ))}
          </Menu>
        )}
        <Menu
          className="hdr-account"
          ariaLabel={`계정 메뉴 — ${user.email}`}
          label={
            <>
              <span className="hdr-avatar" aria-hidden="true">{name.slice(0, 1)}</span>
              <span className="hdr-name">{name}</span>
              <Chevron />
            </>
          }
        >
          <div className="menu-head">
            <strong>{name}</strong>
            <span>{user.email}</span>
          </div>
          <MenuSep />
          {account.map((i) => (
            <NavLink key={i.to} to={i.to} role="menuitem">
              {i.label}
            </NavLink>
          ))}
          <MenuSep />
          <button type="button" role="menuitem" onClick={() => void logout()}>
            로그아웃
          </button>
        </Menu>
        <button
          type="button"
          className="hdr-burger"
          aria-label="메뉴"
          aria-expanded={sheet}
          aria-controls="hdr-sheet"
          onClick={() => setSheet((s) => !s)}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M3 6h14M3 10h14M3 14h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {sheet && (
        <nav className="hdr-sheet" id="hdr-sheet" aria-label="전체 메뉴">
          {[...primary, ...admin].map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end}>
              {i.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}
