import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { ChatProvider } from './state/ChatContext';
import { AppShell } from './components/layout/AppShell';
import ChatPage from './pages/ChatPage';
import LaunchPage from './pages/LaunchPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import PortalHomePage from './pages/PortalHomePage';

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
