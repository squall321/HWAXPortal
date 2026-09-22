// ste(SmartTwinExplorer) 자격 중계 — 포털 로그인으로 ste 까지 열리게 한다
import { apiFetch } from './client';

export interface SteCredential {
  token: string;
  expires_in: number;
}

/** 내 ste PAT 를 받아 온다. 권한이 없거나 기능이 꺼져 있으면 null(조용히 넘어간다). */
export async function fetchSteCredential(): Promise<SteCredential | null> {
  const res = await apiFetch('/systems/ste/credential', { method: 'POST' });
  if (res.status === 404) return null;            // 타일이 없거나 중계가 꺼져 있다
  if (!res.ok) throw new Error(`ste credential failed (${res.status})`);
  return (await res.json()) as SteCredential;
}

/** 로그아웃·정지 때 서버 원장에서 끊는다. 실패해도 로그아웃을 막지 않는다. */
export async function revokeSteCredential(): Promise<void> {
  try {
    await apiFetch('/systems/ste/credential/revoke', { method: 'POST' });
  } catch {
    /* 비치명 — 브라우저 사본은 어차피 지운다 */
  }
}
