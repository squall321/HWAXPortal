import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { ChatProvider } from './state/ChatContext';
import { AppShell } from './components/layout/AppShell';
import ChatPage from './pages/ChatPage';
import DeliberatePage from './pages/DeliberatePage';
import LaunchPage from './pages/LaunchPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import PortalHomePage from './pages/PortalHomePage';
import TokenPage from './pages/TokenPage';

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell>
          <ChatPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/deliberate',
    element: (
      <ProtectedRoute>
        <AppShell>
          {/* 심의 전용 이력(hwax.delib.*) + '/심의 ' 자동 트리거 — 중첩 Provider 라 일반 챗과 분리 */}
          <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 ">
            <DeliberatePage />
          </ChatProvider>
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/apps',
    element: (
      <ProtectedRoute>
        <AppShell>
          <PortalHomePage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/tokens',
    element: (
      <ProtectedRoute>
        <AppShell>
          <TokenPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/launch/:systemId',
    element: (
      <ProtectedRoute>
        <AppShell>
          <LaunchPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  { path: '*', element: <NotFoundPage /> },
]);

export default function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <RouterProvider router={router} />
      </ChatProvider>
    </AuthProvider>
  );
}
