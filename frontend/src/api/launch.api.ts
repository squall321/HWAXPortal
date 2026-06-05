import { apiFetch } from './client';

export interface HandoffPayload {
  mode: 'redirect' | 'auto_post';
  action: string;
  fields: Record<string, string>;
  url: string | null;
}

export async function launchSystem(systemId: string): Promise<HandoffPayload> {
  const res = await apiFetch(`/systems/${systemId}/launch`, { method: 'POST' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Launch failed (${res.status})`);
  }
  return (await res.json()) as HandoffPayload;
}
