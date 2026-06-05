import type { ReactNode } from 'react';
import { AppHeader } from './AppHeader';

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <AppHeader />
      {/* Full-bleed: pages manage their own width (the home hero spans the viewport). */}
      <main className="page">{children}</main>
    </>
  );
}
