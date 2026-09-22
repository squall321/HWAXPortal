import { createContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { getMe, postLogout } from '../api/auth.api';
import type { AuthStatus, User } from './types';
import { revokeSteCredential } from '../api/ste.api';
import { clearSteCredential } from '../components/layout/StePrimer';

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

  // 권한은 관리자가 바꾸면 서버에서 곧바로 바뀐다(요청마다 계산) — 창으로 돌아올 때 /auth/me 를 다시
  // 받아 메뉴가 따라가게 한다. 30초에 한 번까지만. 실패(null)는 무시한다 — 순간 끊김으로 로그아웃
  // 화면이 되면 안 되고, 진짜 만료는 다음 API 호출의 401 이 알린다.
  const lastFocus = useRef(0);
  useEffect(() => {
    const onFocus = () => {
      if (Date.now() - lastFocus.current < 30_000) return;
      lastFocus.current = Date.now();
      void getMe().then((u) => {
        if (u) setUser(u);
      });
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, []);

  // Full-page navigation to the backend, which redirects to the IdP (mock or real AD).
  const login = useCallback((returnTo = '/') => {
    window.location.assign(`/auth/login?return_to=${encodeURIComponent(returnTo)}`);
  }, []);

  const logout = useCallback(async () => {
    // ste 자격 회수 — **서버 원장과 브라우저 사본을 둘 다** 끊어야 회수다.
    // 브라우저만 지우면 토큰은 살아 있고(만료가 없다), 서버만 끊으면 다음 탭이 죽은
    // 토큰으로 401 을 맞는다. 실패는 비치명이다 — 로그아웃을 막으면 사용자가 못 나간다.
    await revokeSteCredential();
    clearSteCredential();
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
