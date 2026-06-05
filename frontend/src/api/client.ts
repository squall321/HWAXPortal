import { config } from '../config';

// httpOnly session cookie rides automatically with credentials:'include'.
// For state-changing requests we attach the double-submit CSRF token, read from the
// non-httpOnly hwax_csrf cookie. On 401 we transparently try one /auth/refresh and retry.

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)'));
  return m ? decodeURIComponent(m[2]) : null;
}

let refreshInFlight: Promise<boolean> | null = null;

function doRefresh(): Promise<boolean> {
  if (!refreshInFlight) {
    const csrf = getCookie('hwax_csrf');
    refreshInFlight = fetch(`${config.apiBase}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: csrf ? { 'X-CSRF-Token': csrf } : {},
    })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

export async function apiFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = getCookie('hwax_csrf');
    if (csrf) headers.set('X-CSRF-Token', csrf);
  }

  const res = await fetch(`${config.apiBase}${path}`, { ...init, credentials: 'include', headers });

  if (res.status === 401 && retry && path !== '/auth/refresh') {
    const refreshed = await doRefresh();
    if (refreshed) return apiFetch(path, init, false);
  }
  return res;
}
