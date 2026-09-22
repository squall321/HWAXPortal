// 배선 요청·설정 — 아직 안 된 것만 돌아온다(다 되면 빈 목록)
import { apiFetch } from './client';

export type SetupState = 'todo' | 'manual' | 'unknown';

export interface SetupRequest {
  id: string;
  title: string;
  tag: string;
  severity: string;
  body: string;
  state: SetupState;
}

export async function listSetupRequests(): Promise<SetupRequest[]> {
  const res = await apiFetch('/setup/requests');
  if (!res.ok) return [];          // 이 카드가 홈을 막으면 안 된다
  const body = (await res.json()) as { items?: SetupRequest[] };
  return body.items ?? [];
}
