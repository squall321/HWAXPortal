import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spinner } from '../components/common/Spinner';
import { useAuth } from './useAuth';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const loc = useLocation();

  if (status === 'loading') return <Spinner label="로그인 확인 중…" />;
  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />;
  }
  return <>{children}</>;
}
