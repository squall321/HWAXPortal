import { apiFetch } from './client';

export interface HandoffPayload {
  mode: 'redirect' | 'auto_post';
  action: string;
  fields: Record<string, string>;
  url: string | null;
}

// via=primer — 화면이 저절로 부르는 SSO 미리 로그인. 접속 원장이 사람이 누른 진입과 가른다(docs/access-history).
export async function launchSystem(systemId: string, opts: { via?: 'primer' } = {}): Promise<HandoffPayload> {
  const q = opts.via ? `?via=${opts.via}` : '';
  const res = await apiFetch(`/systems/${systemId}/launch${q}`, { method: 'POST' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Launch failed (${res.status})`);
  }
  return (await res.json()) as HandoffPayload;
}

/** 프록시·외부 타일을 눌렀다는 기록(docs/access-history). 새 창 열기를 막지 않게 기다리지 않는다 — 기록이 실패해도
 *  사용자가 할 일은 없으므로 화면에 알리지 않는다(서버 쪽 쓰기 실패는 포털 로그 WARNING 으로 남는다). */
export function noteTileOpen(systemId: string): void {
  void apiFetch(`/systems/${encodeURIComponent(systemId)}/open`, { method: 'POST', keepalive: true }).catch(() => {});
}
