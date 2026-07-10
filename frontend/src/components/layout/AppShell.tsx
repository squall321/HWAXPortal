import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { AppHeader } from './AppHeader';
import { ChatDock } from '../chat/ChatDock';

export function AppShell({ children }: { children: ReactNode }) {
  // '/' is the full-screen ChatPage, so the floating dock would duplicate it there.
  // Keep the dock as a secondary helper on the other pages (/apps, /launch).
  const isChatMain = useLocation().pathname === '/';
  return (
    <>
      <AppHeader />
      {/* Full-bleed: pages manage their own width (the home hero spans the viewport). */}
      <main className="page">{children}</main>
      {!isChatMain && <ChatDock />}
    </>
  );
}
