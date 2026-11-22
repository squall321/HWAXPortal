// 전문가 팀 API — 목록 · 만들기 · 고치기(판 번호) · 지우기 · 공식 표지 · 그 사람의 시야로 푼 사본(포털 /agent/teams, docs/expert-teams)
import { apiFetch, errorDetail } from './client';

export interface TeamMember {
  key: string;
  name?: string;
}

export type TeamScope = 'private' | 'org';

/** 원장의 팀 하나 — PLAN 1절 칸 + 내 것인가 · 고칠 수 있나 · 지울 수 있나(공식 팀은 관리자만 지운다). */
export interface Team {
  id: string;
  name: string;
  description: string;
  lead: TeamMember;
  helpers: TeamMember[];
  apps: string[];
  tools: string[];
  scope: TeamScope;
  official: boolean;
  owner_email: string;
  owner_aff: string;
  version: number;
  created_at: number;
  updated_at: number;
  mine: boolean;
  editable: boolean;
  deletable: boolean;
}

/** 그 사람의 시야로 푼 사본(PLAN 3-2) — 고르는 순간 이것을 대화 지정값으로 복사한다(나중에 팀을 고쳐도 연 대화는 그대로). */
export interface TeamSnapshot {
  id: string;
  name: string;
  version: number;
  lead: TeamMember;
  helpers: TeamMember[];
  apps: string[];
  tools: string[];
  resolved_at: number;
}

export interface TeamBody {
  name: string;
  description?: string;
  lead: TeamMember;
  helpers: TeamMember[];
  apps: string[];
  tools: string[];
  scope: TeamScope;
}

export const TEAM_LIMITS = { name: 60, description: 300, helpers: 4, apps: 3, tools: 12 } as const;

async function call<T>(path: string, what: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(`/agent/teams${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail((body as { detail?: unknown }).detail, `${what} 실패 (${res.status})`));
  }
  return (await res.json()) as T;
}

function send<T>(method: string, path: string, what: string, body: unknown): Promise<T> {
  return call<T>(path, what, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

export function listTeams(): Promise<{ teams: Team[]; note: string }> {
  return call('', '팀 목록 불러오기');
}

export function createTeam(body: TeamBody): Promise<Team> {
  return send('POST', '', '팀 저장', body);
}

/** 고치기 — 받아 둔 판(expected_version)이 지금 판과 다르면 409(그새 다른 곳에서 고쳤다). */
export function updateTeam(id: string, expectedVersion: number, patch: Partial<TeamBody>): Promise<Team> {
  return send('PATCH', `/${encodeURIComponent(id)}`, '팀 고치기', { ...patch, expected_version: expectedVersion });
}

export function deleteTeam(id: string): Promise<{ ok: boolean }> {
  return call(`/${encodeURIComponent(id)}`, '팀 지우기', { method: 'DELETE' });
}

export function setTeamOfficial(id: string, on: boolean): Promise<Team> {
  return send('POST', `/${encodeURIComponent(id)}/official`, '공식 표지', { on });
}

/** 못 풀면 team 이 null 이고 까닭이 온다. hidden — 이 사람이 쓸 수 없어 빠진 전문가(앱 권한이 없는 HE팀 운영자). */
export function resolveTeam(id: string): Promise<{ team: TeamSnapshot | null; why: string; hidden: TeamMember[] }> {
  return call(`/${encodeURIComponent(id)}/resolve`, '팀 풀기');
}
