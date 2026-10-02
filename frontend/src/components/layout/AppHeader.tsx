// 앱 헤더 — [브랜드] 주 메뉴(챗·심의·앱·절차) …… [관리 ▾](관리자) [계정 ▾]. 좁으면 주 메뉴를 시트로 접는다(docs/ui-refresh 단계 2)
import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { listSetupRequests, SETUP_CHANGED } from '../../api/setup.api';
import { useAuth } from '../../auth/useAuth';
import { useCan } from '../../auth/useCan';
import { BrandMark } from '../ui/BrandMark';
import { Menu, MenuSep } from '../ui/Menu';
import '../../styles/header.css';

type Item = { to: string; label: string; end?: boolean; badge?: number };


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
  const burger = useRef<HTMLButtonElement>(null);
  const sheetRef = useRef<HTMLElement>(null);
  useEffect(() => setSheet(false), [pathname]);
  const isAdmin = Boolean(user?.groups.includes('portal-admin'));
  // 안 된 배선 건수 — 상자는 사용자 관리 맨 위에 있고, 여기 '관리' 옆 숫자가 그 상자로 부른다(안 본 곳에 둔 할 일은 없는 셈이다).
  // 세션에 한 번 + 상자에서 '확인함' 을 누를 때(SETUP_CHANGED). 확인이 2초 걸릴 수 있어 화면 이동마다 다시 묻지 않는다.
  const [setupN, setSetupN] = useState(0);
  useEffect(() => {
    if (!isAdmin) return;
    const load = () => void listSetupRequests().then((r) => setSetupN(r.items.length));
    load();
    window.addEventListener(SETUP_CHANGED, load);
    return () => window.removeEventListener(SETUP_CHANGED, load);
  }, [isAdmin]);
  // 시트 — Esc(버거로 포커스 복귀)·바깥 탭이면 닫고, 창을 넓혀 시트가 필요 없어지면(900px 이상) 닫는다
  useEffect(() => {
    if (!sheet) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSheet(false);
        burger.current?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!sheetRef.current?.contains(t) && !burger.current?.contains(t)) setSheet(false);
    };
    const wide = window.matchMedia('(min-width: 900px)');
    const onWide = () => wide.matches && setSheet(false);
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown);
    wide.addEventListener('change', onWide);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
      wide.removeEventListener('change', onWide);
    };
  }, [sheet]);

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
        { to: '/admin/users', label: '사용자 관리', badge: setupN },
        { to: '/admin/access', label: '접속 이력' },
      ]
    : [];
  const account: Item[] = [
    { to: '/access', label: '내 권한' },
    ...(canTokens ? [{ to: '/tokens', label: can('feat:api-token') ? '개인 토큰' : '연결 설정' }] : []),
    { to: '/updates', label: '업데이트 이력' },
  ];
  const name = (user.display_name || '').trim() || user.email.split('@')[0];
  // 메뉴 안으로 옮긴 화면에 있을 때 그 메뉴 버튼에 '현재 위치' 를 표시한다(주 메뉴 링크의 active 와 같은 모양)
  const inside = (items: Item[]) => items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`));

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
          <Menu
            className="hdr-admin"
            active={inside(admin)}
            ariaLabel={setupN > 0 ? `관리 — 배선 설정 ${setupN}건 남음` : undefined}
            label={
              <>
                관리
                {setupN > 0 && <span className="hdr-badge" aria-hidden="true">{setupN}</span>}
                <Chevron />
              </>
            }
          >
            {admin.map((i) => (
              <NavLink key={i.to} to={i.to} role="menuitem" tabIndex={-1}>
                {i.label}
                {!!i.badge && <span className="hdr-badge" title={`배선 설정 ${i.badge}건`}>배선 {i.badge}</span>}
              </NavLink>
            ))}
          </Menu>
        )}
        <Menu
          className="hdr-account"
          active={inside(account)}
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
            <NavLink key={i.to} to={i.to} role="menuitem" tabIndex={-1}>
              {i.label}
            </NavLink>
          ))}
          <MenuSep />
          <button type="button" role="menuitem" tabIndex={-1} onClick={() => void logout()}>
            로그아웃
          </button>
        </Menu>
        <button
          ref={burger}
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
        <nav className="hdr-sheet" id="hdr-sheet" aria-label="전체 메뉴" ref={sheetRef}>
          {[...primary, ...admin].map((i) => (
            // 지금 화면의 링크를 눌러도(경로가 안 바뀌어도) 닫힌다
            <NavLink key={i.to} to={i.to} end={i.end} onClick={() => setSheet(false)}>
              {i.label}
              {!!i.badge && <span className="hdr-badge">배선 {i.badge}</span>}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}
