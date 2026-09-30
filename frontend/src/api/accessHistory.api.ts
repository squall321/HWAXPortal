// 관리자용 서비스 접속 이력 API — 포털 원장(로그인·진입)과 계정별 정문 요청 요약(docs/access-history)
import { apiFetch, errorDetail } from './client';

export interface AccessRow {
  ts: number;
  email: string;
  event: 'login' | 'login_fail' | 'launch' | 'open' | string;
  service: string | null;
  ip: string | null;
  ua: string | null;
  uid: string | null;
  detail: string | null;
}

export interface AccessLedger {
  rows: AccessRow[];
  truncated: boolean;
  days: number;
}

export interface ServiceRequests {
  service: string;
  requests: number;
  first: number;
  last: number;
  ips: string[];
}

export interface RecentRequest {
  ts: number;
  ip: string;
  method: string;
  path: string;
  status: number;
  service: string;
}

export interface AccountRequests {
  email: string;
  days: number;
  services: ServiceRequests[];
  recent: RecentRequest[];
  logins: number;
  files: number;
  uid_column: boolean;
  note: string;
}

async function getJson<T>(path: string, what: string): Promise<T> {
  const res = await apiFetch(path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body.detail, `${what} 실패 (${res.status})`));
  }
  return (await res.json()) as T;
}

export function fetchAccessLedger(q: {
  email?: string;
  service?: string;
  event?: string;
  days: number;
  includeAuto: boolean;
}): Promise<AccessLedger> {
  const p = new URLSearchParams({ days: String(q.days), include_auto: String(q.includeAuto) });
  if (q.email) p.set('email', q.email);
  if (q.service) p.set('service', q.service);
  if (q.event) p.set('event', q.event);
  return getJson<AccessLedger>(`/auth/admin/access?${p}`, '접속 원장 조회');
}

export function fetchAccountRequests(email: string, days: number): Promise<AccountRequests> {
  const p = new URLSearchParams({ email, days: String(days) });
  return getJson<AccountRequests>(`/auth/admin/access/requests?${p}`, '정문 요청 조회');
}
