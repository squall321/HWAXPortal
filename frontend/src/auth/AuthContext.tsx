import { createContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { getMe, postLogout } from '../api/auth.api';
import { SESSION_EXPIRED_EVENT } from '../api/client';
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

  // 갱신까지 실패하면 세션은 끝났다 — 화면마다 http_401 을 띄우지 말고 로그인으로 보낸다(ProtectedRoute 가 /login 으로).
  // logout() 의 clearSteCredential·끝 두 줄과 같다.
  useEffect(() => {
    const onExpired = () => {
      // ste 사본을 안 지우면 이 탭에서 다음에 로그인한 사람이 앞 사람의 ste 토큰을 그대로 쓴다
      // (StePrimer 가 사본이 있으면 다시 받지 않는다. 토큰에 만료가 없다).
      // 서버 회수(revokeSteCredential)는 부르지 않는다 — 세션이 없어 401 이다(10-14 실측).
      clearSteCredential();
      setUser(null);
      setStatus('unauthenticated');
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
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
