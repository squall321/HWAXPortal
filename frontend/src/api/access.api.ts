// 소속·허가 API 클라이언트 — 내 권한 표·허가 요청(사용자), 소속·개별 허가·요청 결정(관리자)
import { apiFetch } from './client';

export interface AccessRow {
  key: string; // feat:deliberation · plat:stepforge
  id: string;
  label: string;
  desc: string;
  allowed: boolean;
  /** 허가 이유(사람용) — 관리자·개별 허가·소속 기본(CAE그룹)·모든 사용자 기본·○○에 포함. */
  reason: string;
  /** 가장 최근 요청 — 없으면 null. */
  request: { id: number; status: 'pending' | 'approved' | 'rejected'; created_at: number } | null;
  /** 게이트웨이 백엔드가 딸린 항목 — PAT(개인 Claude)로 열리는 것이 이것들이다. */
  tools: boolean;
}

export interface MyAccess {
  affiliation: string;
  affiliation_label: string;
  is_admin: boolean;
  features: AccessRow[];
  platforms: AccessRow[];
}

export interface AccessPolicy {
  features: { key: string; label: string; desc: string; implies: string[] }[];
  platforms: { key: string; label: string; desc: string }[];
  affiliations: { id: string; label: string; grants: string[] }[];
  default_grants: string[];
}

export interface AccessRequest {
  id: number;
  email: string;
  key: string;
  note: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: number;
  decided_at: number | null;
  decided_by: string | null;
}

async function detail(res: Response, fallback: string): Promise<Error> {
  const b = (await res.json().catch(() => ({}))) as { detail?: unknown };
  return new Error(typeof b.detail === 'string' ? b.detail : fallback);
}

export async function fetchMyAccess(): Promise<MyAccess> {
  const res = await apiFetch('/auth/access');
  if (!res.ok) throw await detail(res, '권한 표를 불러오지 못했습니다.');
  return (await res.json()) as MyAccess;
}

export async function requestAccess(key: string, note: string): Promise<void> {
  const res = await apiFetch('/auth/access/requests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, note }),
  });
  if (!res.ok) throw await detail(res, '요청을 보내지 못했습니다.');
}

/** 허브에 보일 앱 — 게이트웨이 앱 하나. 끄면 개인 Claude 의 허브 도구 목록·검색에서 빠진다(docs/mcp-app-toggle). */
export interface HubApp {
  app: string;
  label: string;
  description: string;
  tool_count: number;
  reachable: boolean;
  /** 포털 권한 표 기준 — 권한이 없는 앱은 끄지 않아도 안 보인다. */
  allowed: boolean;
  muted: boolean;
  /** 꺼 둔 앱이 지금 게이트웨이에 없다(잠시 내려감 등). */
  absent?: boolean;
}

export interface HubApps {
  apps: HubApp[];
  muted: string[];
  note: string;
}

export async function fetchHubApps(): Promise<HubApps> {
  const res = await apiFetch('/auth/access/apps');
  if (!res.ok) throw await detail(res, '앱 목록을 불러오지 못했습니다.');
  return (await res.json()) as HubApps;
}

/** 끈 앱 목록을 통째로 저장한다 — 서버가 게이트웨이 캐시를 바로 깬다. */
export async function saveHubApps(muted: string[]): Promise<HubApps> {
  const res = await apiFetch('/auth/access/apps', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ muted }),
  });
  if (!res.ok) throw await detail(res, '저장하지 못했습니다.');
  return (await res.json()) as HubApps;
}

export async function fetchAccessPolicy(): Promise<AccessPolicy> {
  const res = await apiFetch('/auth/access/policy');
  if (!res.ok) throw await detail(res, '권한 정책을 불러오지 못했습니다.');
  return (await res.json()) as AccessPolicy;
}

export async function listAccessRequests(status = 'pending'): Promise<AccessRequest[]> {
  const res = await apiFetch(`/auth/access/requests?status=${encodeURIComponent(status)}`);
  if (!res.ok) throw await detail(res, '요청 목록을 불러오지 못했습니다.');
  return (await res.json()) as AccessRequest[];
}

export async function decideAccessRequest(id: number, approve: boolean): Promise<void> {
  const res = await apiFetch(`/auth/access/requests/${id}/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approve }),
  });
  if (!res.ok) throw await detail(res, '요청을 처리하지 못했습니다.');
}

export async function setUserAccess(
  email: string,
  patch: { affiliation?: string; grants?: string[] },
): Promise<{ email: string; affiliation: string; grants: string[] }> {
  const res = await apiFetch(`/auth/access/users/${encodeURIComponent(email)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw await detail(res, '권한을 저장하지 못했습니다.');
  return (await res.json()) as { email: string; affiliation: string; grants: string[] };
}
