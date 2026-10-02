import { createBrowserRouter, Outlet, RouterProvider } from 'react-router-dom';
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
import AccessHistoryPage from './pages/admin/AccessHistoryPage';
import UsersAdminPage from './pages/admin/UsersAdminPage';
import ProceduresPage from './pages/procedures/ProceduresPage';
import { ProceduresProvider } from './state/ProceduresContext';

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    // 셸은 한 번만 마운트한다 — 화면을 옮길 때마다 헤더·업데이트 팝업·프라이머가 다시 붙고 카탈로그를 다시 받던 것을 없앤다.
    // 404 도 셸 안에서 그린다(헤더가 남아 다음 행동이 보인다). docs/ui-refresh 단계 2.
    element: (
      <ProtectedRoute>
        <AppShell>
          <Outlet />
        </AppShell>
      </ProtectedRoute>
    ),
    children: [
      {
        path: '/',
        element: <ChatPage />,
      },
      {
        path: '/deliberate',
        element: (
          <RequireEntitlement need="feat:deliberation">
            {/* 심의 전용 이력(hwax.delib.*) + 첫 발화 '/심의 ' 트리거 + 서버 심의 대화(MCP 포함) 병합 */}
            <ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 " serverKind="deliberation">
              <DeliberatePage />
            </ChatProvider>
          </RequireEntitlement>
        ),
      },
      {
        // 자식 라우트는 ProceduresPage 안에 둔다 — 절차·실행에 링크할 URL 이 있어야
        // '남과 공유된다' 가 성립하고, 게이트에 멈춘 실행으로 돌아오는 길도 URL 이다.
        // ⚠ API 접두사는 '/procedures-api' 다(겹치면 새로고침이 JSON 을 받는다).
        path: '/procedures/*',
        element: (
          <RequireEntitlement need="feat:procedures">
            {/* 페이지 스코프 Provider — App() 루트에 두지 않고 useChat 도 쓰지 않는다. */}
            <ProceduresProvider>
              <ProceduresPage />
            </ProceduresProvider>
          </RequireEntitlement>
        ),
      },
      {
        path: '/apps',
        element: <PortalHomePage />,
      },
      {
        // ⚠ SPA 경로는 '/updates' 다. '/changelog' 는 **API** 가 쓰고 있어서, 같은 경로로
        //    만들면 브라우저 새로고침이 SPA 가 아니라 JSON 을 받는다.
        path: '/updates',
        element: <ChangelogPage />,
      },
      {
        // Report Archive 연결(토큰·내 조직 선택)이 이 페이지에 함께 산다 — API 토큰 권한이
        // 없어도 RA 를 쓰는 사람은 조직을 골라야 보고서가 제 자리에 쌓인다.
        path: '/tokens',
        element: (
          <RequireEntitlement need={['feat:api-token', 'plat:reportarchive']}>
            <TokenPage />
          </RequireEntitlement>
        ),
      },
      {
        path: '/launch/:systemId',
        element: <LaunchPage />,
      },
      {
        path: '/admin/users',
        element: <UsersAdminPage />,
      },
      {
        path: '/admin/access',
        element: <AccessHistoryPage />,
      },
      {
        path: '/risk',
        element: (
          <RequireEntitlement need="plat:risk">
            <RiskLaunchPage />
          </RequireEntitlement>
        ),
      },
      {
        // 내 권한 — 모든 기능·플랫폼의 사용 가능 여부와 요청(docs/access-control). 누구나 연다.
        path: '/access',
        element: <AccessPage />,
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
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
