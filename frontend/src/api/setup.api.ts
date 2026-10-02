// 배선 요청·설정 — 아직 안 된 것만 돌아온다(다 되면 빈 목록)
import { apiFetch } from './client';

export type SetupState = 'todo' | 'manual' | 'unknown';

export interface SetupRequest {
  id: string;
  title: string;
  tag: string;
  severity: string;
  /** 셋업이 안 됐을 때 기본값이 들어가나 — auto(알아서 채움) | generate(없으면 만듦) | none(사람이 정해야 함) */
  default: 'auto' | 'generate' | 'none';
  body: string;
  state: SetupState;
}

/** 사람이 '확인함' 한 manual 항목 — 상자에서 빠지고 접힌 목록에 남는다(되돌릴 수 있게) */
export interface SetupAck {
  id: string;
  title: string;
  by: string;
  at: number;
}

export async function listSetupRequests(): Promise<{ items: SetupRequest[]; acked: SetupAck[] }> {
  const res = await apiFetch('/setup/requests');
  if (!res.ok) return { items: [], acked: [] }; // 이 상자가 화면을 막으면 안 된다
  const body = (await res.json()) as { items?: SetupRequest[]; acked?: SetupAck[] };
  return { items: body.items ?? [], acked: body.acked ?? [] };
}

/** manual 항목 '확인함' / 되돌리기. 바뀌면 헤더의 '관리' 건수도 다시 센다(SETUP_CHANGED). */
export const SETUP_CHANGED = 'hwax:setup-changed';
export async function setSetupAck(id: string, on: boolean): Promise<void> {
  const res = await apiFetch(`/setup/requests/${encodeURIComponent(id)}/ack`, { method: on ? 'POST' : 'DELETE' });
  if (!res.ok) throw new Error(`저장하지 못했습니다 (HTTP ${res.status})`);
  window.dispatchEvent(new Event(SETUP_CHANGED));
}
