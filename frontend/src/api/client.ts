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

/** FastAPI 의 error detail 을 사람이 읽을 한 줄로.
 *
 * detail 은 문자열일 수도 있고(우리가 raise 한 것), 검증 오류면 배열이다
 * (pydantic: [{loc, msg, type, input}]). 문자열로 가정하고 그대로 렌더하면 화면에
 * "[object Object]" 가 뜬다 — 사용자는 무엇이 잘못됐는지 알 수 없다.
 * input 필드는 요청 본문 전체를 되싣고 있을 수 있어 절대 쓰지 않는다(msg 만 쓴다).
 */
export function errorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : ''))
      .filter(Boolean);
    if (msgs.length) return msgs.slice(0, 3).join(' / ');
  }
  return fallback;
}
