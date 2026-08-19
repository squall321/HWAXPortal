import type { User } from '../auth/types';
import { apiFetch } from './client';

export async function getMe(): Promise<User | null> {
  const res = await apiFetch('/auth/me');
  if (res.ok) return (await res.json()) as User;
  return null;
}

export async function postLogout(): Promise<void> {
  const res = await apiFetch('/auth/logout', { method: 'POST' });
  // 하위 서비스 세션도 끊는다. 그 쿠키들은 같은 호스트의 '경로 스코프' 라 포털 서버가
  // 대신 지울 수 없다 — 브라우저가 각 서비스의 로그아웃을 쳐야 한다. 안 그러면 포털에서
  // 로그아웃해도 /apps/<slug>/ 가 그 서비스의 토큰 수명(최대 1시간) 동안 직전 사용자
  // 신원으로 열려 있다. 하나가 실패해도 나머지는 계속 시도한다(로그아웃은 막히면 안 된다).
  let outs: string[] = [];
  try {
    outs = ((await res.json()) as { downstream_logout?: string[] }).downstream_logout ?? [];
  } catch {
    /* 본문이 없거나 형식이 달라도 포털 로그아웃 자체는 이미 끝났다 */
  }
  await Promise.allSettled(
    outs.map((u) => fetch(u, { method: 'POST', credentials: 'include' })),
  );
}
