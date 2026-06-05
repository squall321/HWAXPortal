import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import { getMe, postLogout } from '../api/auth.api';
import type { AuthStatus, User } from './types';

interface AuthState {
  user: User | null;
  status: AuthStatus;
  login: (returnTo?: string) => void;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  const refresh = useCallback(async () => {
    const u = await getMe();
    setUser(u);
    setStatus(u ? 'authenticated' : 'unauthenticated');
  }, []);

  // Bootstrap: ask the backend who we are (cookie-based). No token ever touches JS.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Full-page navigation to the backend, which redirects to the IdP (mock or real AD).
  const login = useCallback((returnTo = '/') => {
    window.location.assign(`/auth/login?return_to=${encodeURIComponent(returnTo)}`);
  }, []);

  const logout = useCallback(async () => {
    await postLogout();
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
