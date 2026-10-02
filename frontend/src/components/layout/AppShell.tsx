import { useEffect, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { AppHeader } from './AppHeader';
import { ChangelogPopup } from './ChangelogPopup';
import { ChatDock } from '../chat/ChatDock';
import { SsoPrimer } from './SsoPrimer';
import { StePrimer } from './StePrimer';

// 탭 제목 — 모든 화면이 'HWAX Portal' 하나라 탭 여러 개를 구분할 수 없었다(docs/ui-refresh 단계 1).
const TITLES: [string, string][] = [
  ['/deliberate', '심의'], ['/procedures', '절차'], ['/apps', '앱'], ['/tokens', '개인 토큰'], ['/updates', '업데이트 이력'],
  ['/access', '내 권한'], ['/admin/users', '사용자 관리'], ['/admin/access', '접속 이력'], ['/risk', '리스크 심사'],
  ['/launch', '앱 여는 중'],
];

export function AppShell({ children }: { children: ReactNode }) {
  // '/'(챗)과 '/deliberate'(심의)는 전체화면 챗형 UI라 플로팅 독이 중복 — 그 외 페이지에서만 보조로 띄운다.
  const { pathname } = useLocation();
  useEffect(() => {
    const hit = pathname === '/' ? '챗' : TITLES.find(([p]) => pathname.startsWith(p))?.[1];
    document.title = hit ? `${hit} · HWAX` : 'HWAX Portal';
  }, [pathname]);
  const isChatMain = pathname === '/' || pathname === '/deliberate';
  return (
    <>
      {/* AppShell 은 ProtectedRoute 안에서만 그려진다 — 여기 닿았다는 것이 곧 포털 로그인 완료다. */}
      <SsoPrimer enabled />
      {/* ste 는 자체 Bearer 로 인증한다(SSO 리다이렉트를 안 쓴다) — 자격을 받아 놓아 둔다. */}
      <StePrimer enabled />
      {/* 아직 안 본 업데이트가 있으면 한 번 띄운다(없으면 아무것도 안 그린다). */}
      <ChangelogPopup />
      <AppHeader />
      {/* Full-bleed: pages manage their own width (the home hero spans the viewport). */}
      <main className="page">{children}</main>
      {!isChatMain && <ChatDock />}
    </>
  );
}
