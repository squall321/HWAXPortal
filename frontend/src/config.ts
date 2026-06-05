// Typed access to build-time env. In dev the API is same-origin via the Vite proxy,
// so the base path is empty (requests like /auth/me hit the proxy).
export const config = {
  apiBase: import.meta.env.VITE_API_BASE ?? '',
} as const;
