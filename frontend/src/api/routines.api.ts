// 분석 루틴 API — 정의 · 판 · 보관 · 준비도 · 고를 수 있는 플랫폼 · YAML(docs/analysis-routines, R1)
import { config } from '../config';
import { apiFetch, errorDetail } from './client';

export type StepKind = 'platform' | 'deliberation' | 'cite';

export interface RoutineVar {
  key: string;
  label: string;
  type?: string;
  required?: boolean;
  why?: string | null;
}

export interface RoutineStep {
  id: string;
  title: string;
  kind: StepKind;
  backends: string[];
  label?: string;
  goal: string;
  tools: string[];
  uses: string[];
  expect: { keys: string[]; fields?: Record<string, string> };
  budget: { calls: number; seconds: number };
  blocked: { empty: 'continue' | 'stop'; denied: 'skip' | 'stop'; unavailable: 'skip' | 'stop' };
  deliberation?: { job: string; chair_template?: string | null } | null;
}

export interface RoutineSpec {
  version?: 1;
  title: string;
  purpose: string;
  vars: RoutineVar[];
  steps: RoutineStep[];
  report: { title: string; sections: string[]; ra: { upload: 'auto' | 'ask' | 'off' } };
  limits: { minutes: number; calls: number };
  visibility: 'private' | 'all';
}

export interface RoutineRow {
  id: string;
  owner_sub: string;
  title: string;
  visibility: 'private' | 'all';
  latest_version: number;
  updated_at: number;
  mine: boolean;
  steps: { id: string; title: string; kind: StepKind; backends: string[] }[];
  vars: { key: string; label: string }[];
}

export interface RoutineDetail {
  routine: { id: string; owner_sub: string; title: string; visibility: string; latest_version: number; archived: number };
  version: { version_id: string; version_no: number; spec: RoutineSpec; author_sub: string; created_at: number };
  versions: { version_id: string; version_no: number; author_sub: string; created_at: number }[];
  mine: boolean;
}

export interface PlatformTool {
  name: string;
  exposed: string;
  write: boolean;
  description: string;
}

export interface Platform {
  backend: string;
  label: string;
  tools: PlatformTool[];
}

export interface Platforms {
  platforms: Platform[];
  deliberation: boolean;
  not_permitted: { backend: string; label: string }[];
}

export type Readiness = 'allowed' | 'denied' | 'not_connected' | 'unavailable';

export interface StepReadiness {
  step: string;
  state: Readiness;
  backends: { backend: string; label: string; state: Readiness; reason: string }[];
  missing_tools: string[];
  reason: string;
}

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body.detail, `${what} 실패 (${res.status})`));
  }
  return (await res.json()) as T;
}

const BASE = '/routines-api';
const JSON_HEAD = { 'Content-Type': 'application/json' };

export async function listRoutines(q = ''): Promise<{ count: number; routines: RoutineRow[] }> {
  return json(await apiFetch(`${BASE}/routines?${new URLSearchParams({ q })}`), '루틴 목록');
}

export async function getRoutine(id: string, version?: number): Promise<RoutineDetail> {
  const qs = version ? `?version=${version}` : '';
  return json(await apiFetch(`${BASE}/routines/${encodeURIComponent(id)}${qs}`), '루틴');
}

export async function createRoutine(spec: RoutineSpec): Promise<{ id: string; version_no: number }> {
  return json(await apiFetch(`${BASE}/routines`, { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ spec }) }),
    '루틴 저장');
}

export async function addRoutineVersion(id: string, spec: RoutineSpec): Promise<{ id: string; version_no: number }> {
  return json(
    await apiFetch(`${BASE}/routines/${encodeURIComponent(id)}/versions`,
      { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ spec }) }),
    '새 판 저장');
}

export async function archiveRoutine(id: string): Promise<{ ok: boolean }> {
  return json(await apiFetch(`${BASE}/routines/${encodeURIComponent(id)}`, { method: 'DELETE' }), '보관');
}

export async function routineReadiness(id: string, version?: number): Promise<{ version_no: number; steps: StepReadiness[] }> {
  const qs = version ? `?version=${version}` : '';
  return json(await apiFetch(`${BASE}/routines/${encodeURIComponent(id)}/readiness${qs}`), '준비도');
}

export async function routinePlatforms(): Promise<Platforms> {
  return json(await apiFetch(`${BASE}/platforms`), '플랫폼 목록');
}

export function exportRoutineUrl(id: string, version?: number): string {
  return `${config.apiBase}${BASE}/routines/${encodeURIComponent(id)}/export${version ? `?version=${version}` : ''}`;
}

export async function importRoutineYaml(yaml: string): Promise<{ id: string; version_no: number }> {
  return json(await apiFetch(`${BASE}/import`, { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ yaml }) }),
    'YAML 가져오기');
}
