import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { RequireEntitlement } from './auth/RequireEntitlement';
import { ChatProvider } from './state/ChatContext';
import { AppShell } from './components/layout/AppShell';
import AccessPage from './pages/AccessPage';
import ChangelogPage from './pages/ChangelogPage';
import ChatPage from './pages/ChatPage';
import DeliberatePage from './pages/DeliberatePage';
import LaunchPage from './pages/LaunchPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import PortalHomePage from './pages/PortalHomePage';
import TokenPage from './pages/TokenPage';
import RiskLaunchPage from './pages/risk/RiskLaunchPage';
import UsersAdminPage from './pages/admin/UsersAdminPage';

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
          <RequireEntitlement need="feat:deliberation">
            {/* 심의 전용 이력(hwax.delib.*) + 첫 발화 '/심의 ' 트리거 + 서버 심의 대화(MCP 포함) 병합 */}
            <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 " serverKind="deliberation">
              <DeliberatePage />
            </ChatProvider>
          </RequireEntitlement>
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
    // ⚠ SPA 경로는 '/updates' 다. '/changelog' 는 **API** 가 쓰고 있어서, 같은 경로로
    //    만들면 브라우저 새로고침이 SPA 가 아니라 JSON 을 받는다.
    path: '/updates',
    element: (
      <ProtectedRoute>
        <AppShell>
          <ChangelogPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/tokens',
    element: (
      <ProtectedRoute>
        <AppShell>
          <RequireEntitlement need="feat:api-token">
            <TokenPage />
          </RequireEntitlement>
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
  {
    path: '/admin/users',
    element: (
      <ProtectedRoute>
        <AppShell>
          <UsersAdminPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/risk',
    element: (
      <ProtectedRoute>
        <AppShell>
          <RequireEntitlement need="plat:risk">
            <RiskLaunchPage />
          </RequireEntitlement>
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    // 내 권한 — 모든 기능·플랫폼의 사용 가능 여부와 요청(docs/access-control). 누구나 연다.
    path: '/access',
    element: (
      <ProtectedRoute>
        <AppShell>
          <AccessPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  { path: '*', element: <NotFoundPage /> },
]);

export default function App() {
  return (
    <AuthProvider>
      {/* 일반 챗도 서버 대화 저장소와 동기화(kind='chat') — 기기 간 이력 공유. */}
      <ChatProvider serverKind="chat">
        <RouterProvider router={router} />
      </ChatProvider>
    </AuthProvider>
  );
}
