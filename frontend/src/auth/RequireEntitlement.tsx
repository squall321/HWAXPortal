// 권한 라우트 가드 — 권한이 없으면 페이지 대신 '내 권한'으로 보낸다(무엇이 없는지 표시)
import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useCan } from './useCan';

export function RequireEntitlement({ need, children }: { need: string; children: ReactNode }) {
  const can = useCan();
  if (!can(need)) return <Navigate to={`/access?need=${encodeURIComponent(need)}`} replace />;
  return <>{children}</>;
}
