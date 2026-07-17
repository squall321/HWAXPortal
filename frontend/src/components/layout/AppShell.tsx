import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { AppHeader } from './AppHeader';
import { ChatDock } from '../chat/ChatDock';

export function AppShell({ children }: { children: ReactNode }) {
  // '/'(챗)과 '/deliberate'(심의)는 전체화면 챗형 UI라 플로팅 독이 중복 — 그 외 페이지에서만 보조로 띄운다.
  const { pathname } = useLocation();
  const isChatMain = pathname === '/' || pathname === '/deliberate';
  return (
    <>
      <AppHeader />
      {/* Full-bleed: pages manage their own width (the home hero spans the viewport). */}
      <main className="page">{children}</main>
      {!isChatMain && <ChatDock />}
    </>
  );
}
