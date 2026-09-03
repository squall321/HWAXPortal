import type { User } from '../auth/types';
import { apiFetch } from './client';

export async function getMe(): Promise<User | null> {
  const res = await apiFetch('/auth/me');
  if (res.ok) return (await res.json()) as User;
  return null;
}

// ── 로컬 이메일 계정(SSO 지연 브리지) ─────────────────────────────────────────
export interface LocalUserRow {
  email: string;
  name: string;
  groups: string[];
  status: 'pending' | 'active' | 'disabled';
  auth_source: 'local' | 'sso';
  created_at: number;
  approved_at: number | null;
  last_login_at: number | null;
  locked_until: number;
}

export async function localLogin(email: string, password: string): Promise<void> {
  const res = await apiFetch('/auth/local/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
    throw new Error(typeof body.detail === 'string' ? body.detail : '로그인에 실패했습니다.');
  }
}

export async function localSignup(email: string, name: string, password: string): Promise<string> {
  const res = await apiFetch('/auth/local/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, name, password }),
  });
  const body = (await res.json().catch(() => ({}))) as { status?: string; detail?: unknown };
  if (!res.ok) {
    throw new Error(typeof body.detail === 'string' ? body.detail : '가입 신청에 실패했습니다.');
  }
  return body.status ?? 'pending';
}

export async function listLocalUsers(): Promise<LocalUserRow[]> {
  const res = await apiFetch('/auth/local/users');
  if (!res.ok) throw new Error('사용자 목록을 불러오지 못했습니다.');
  return (await res.json()) as LocalUserRow[];
}

async function postAdmin(path: string, body?: object): Promise<void> {
  const res = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    const b = (await res.json().catch(() => ({}))) as { detail?: unknown };
    throw new Error(typeof b.detail === 'string' ? b.detail : '요청이 실패했습니다.');
  }
}

export const approveLocalUser = (email: string, groups: string[]) =>
  postAdmin(`/auth/local/users/${encodeURIComponent(email)}/approve`, { groups });
export const setLocalUserStatus = (email: string, status: 'active' | 'disabled') =>
  postAdmin(`/auth/local/users/${encodeURIComponent(email)}/status`, { status });
export const resetLocalUserPassword = (email: string, newPassword: string) =>
  postAdmin(`/auth/local/users/${encodeURIComponent(email)}/reset-password`, {
    new_password: newPassword,
  });

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

  // 서버 쿠키만으로 안 끊기는 것들. 두 서비스 모두 자격증명을 localStorage 에 둔다 —
  // AIDataHub 는 SSO 쿠키를 읽어 거기로 옮기고, HEAXHub 는 쿠키를 지워도 주 자격증명이
  // heaxhub.auth 에 남는다. 같은 오리진이라 여기서 지울 수 있다.
  //
  // ⚠ 브라우저에서 지우는 것만으로는 권한이 회수되지 않는다. AIDataHub 의 정본은 서버의
  // ApiKey 행(name="sso:<email>", 기본 30일)이고, localStorage 에 있는 건 그 사본일 뿐이다.
  // 지우기 전에 그 키로 self-revoke 를 불러 서버 행부터 폐기한다 — 실패해도 로그아웃은
  // 계속한다(막히면 안 된다). 키가 바뀌면 이 목록도 같이 바꿔야 한다
  // (AIDataHub dashboard.js 의 API_KEY_STORAGE, HEAXHub store.ts 의 persist name).
  try {
    const aidh = localStorage.getItem('aidh.api_key');
    if (aidh) {
      await fetch('/ai-data-hub/api/auth/keys/self-revoke', {
        method: 'POST',
        headers: { 'X-API-Key': aidh },
      }).catch(() => undefined);
    }
  } catch {
    /* 저장소나 네트워크가 막혀도 아래 정리와 포털 로그아웃은 그대로 진행한다 */
  }
  try {
    for (const k of ['aidh.api_key', 'heaxhub.auth']) localStorage.removeItem(k);
  } catch {
    /* 저장소 접근이 막혀 있어도 포털 로그아웃 자체는 이미 끝났다 */
  }
}
