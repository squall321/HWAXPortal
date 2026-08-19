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
  // ⚠ allSettled 로 전부 삼키면 안 된다 — 실측으로 유도한 경로의 상당수가 404/401 이었는데도
  // 화면은 '로그아웃됨' 으로 끝났다. 끊지 못한 서비스는 사용자가 알아야 직접 조치할 수 있다.
  const results = await Promise.allSettled(
    outs.map(async (u) => {
      const r = await fetch(u, { method: 'POST', credentials: 'include' });
      if (!r.ok) throw new Error(`${u} → ${r.status}`);
      return u;
    }),
  );
  const failed = results.flatMap((r) => (r.status === 'rejected' ? [String(r.reason)] : []));
  if (failed.length) {
    // 로그아웃 자체는 이미 끝났으므로 막지 않는다. 다만 조용히 넘기지도 않는다.
    console.warn('[logout] 하위 서비스 세션을 끊지 못했다:', failed);
  }

  // 서버 로그아웃으로 안 지워지는 것도 있다. AIDataHub 는 자격증명을 쿠키가 아니라
  // localStorage 에 두고(대시보드가 SSO 쿠키를 읽어 옮긴 뒤 즉시 만료시킨다), 로그아웃
  // 엔드포인트 자체가 없다 — 그대로 두면 포털에서 로그아웃해도 그 대시보드는 계속 열린다.
  // 같은 오리진이라 여기서 지울 수 있다. 키가 바뀌면 이 줄도 같이 바꿔야 한다
  // (AIDataHub dashboard.js 의 API_KEY_STORAGE).
  try {
    localStorage.removeItem('aidh.api_key');
  } catch {
    /* 저장소 접근이 막혀 있어도 포털 로그아웃 자체는 이미 끝났다 */
  }
}
