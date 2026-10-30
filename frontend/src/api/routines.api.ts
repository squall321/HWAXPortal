// 분석 루틴 API — 정의 · 판 · 보관 · 준비도 · 고를 수 있는 플랫폼 · YAML(docs/analysis-routines, R1)
import { config } from '../config';
import type { RoutineCandidate } from '../types/chat';
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

// ── 실행(R3) — 챗 화면이 실행 id 로 진행 · 보고서를 읽고, 고를 것을 고르고, 멈춘다. 실행은 주인만 본다(남의 것은 404) ─────
// 실행을 만드는 것은 에이전트 서버(게이트웨이 routine_run_start)다 — 화면은 POST /runs 를 부르지 않는다(R3-design D1).

/** 실행 보기의 단계 — 계획(울타리 · 허용 도구)에 원장의 상태 · 호출 수 · 넘긴 키 · 요약 · 표지를 얹은 것. */
export interface RunStep {
  id: string;
  title: string;
  kind: string;
  /** 원장에 행이 없으면 서버가 null 을 준다 — 읽는 쪽이 'pending' 으로 본다. */
  state: string;
  calls: number;
  reason: string;
  summary: string;
  keys: Record<string, string>;
  findings?: { text: string; refs: string[] }[];
  flags: string[];
  /** 고를 것이 있는 단계(ambiguous)에만. */
  candidates?: RoutineCandidate[];
  goal?: string;
  backends?: string[];
  label?: string;
}

/** GET /routines-api/runs/{id} — 포털 run_view 의 꼴. */
export interface RunView {
  contract: number;
  run: {
    id: string;
    routine_id: string;
    version_no: number;
    title: string;
    executor: string;
    state: string;
    reason: string | null;
    calls: number;
    limits: { minutes: number; calls: number };
    limit_reached: string | null;
    limit_kind?: string | null;
    report_ready: boolean;
    ra_report_id?: string | number | null;
    ra_error?: string | null;
  };
  inputs: Record<string, unknown>;
  purpose: string;
  steps: RunStep[];
  next_step: string | null;
  report: { title: string; sections: string[]; upload: string };
}

/** GET /routines-api/runs/{id}/report — 보고서가 없으면 report_ready=false · report_md ''. */
export interface RunReport {
  run_id: string;
  state: string;
  report_ready: boolean;
  report_md: string;
  ra_upload?: string;
  ra_report_id?: string | number | null;
  ra_error?: string | null;
}

/** GET /routines-api/runs 의 한 줄 — 내 실행(최근 시작부터 50건). started_at 은 서버 시계의 epoch 초다. */
export interface RunRow {
  id: string;
  routine_id: string;
  version_no: number;
  title: string;
  executor: string;
  state: string;
  reason: string | null;
  calls: number;
  started_at: number;
  ended_at: number | null;
  ra_report_id?: string | number | null;
  /** 실행을 연 대화(챗 실행) — 목록이 이 칸을 싣지 않는 포털에서는 없다. */
  conversation_id?: string | null;
}

export async function listRuns(routineId: string): Promise<{ count: number; runs: RunRow[] }> {
  return json(await apiFetch(`${BASE}/runs?${new URLSearchParams({ routine_id: routineId })}`), '루틴 실행 목록');
}

const runPath = (runId: string) => `${BASE}/runs/${encodeURIComponent(runId)}`;

export async function getRun(runId: string): Promise<RunView> {
  return json(await apiFetch(runPath(runId)), '루틴 실행');
}

export async function getRunReport(runId: string): Promise<RunReport> {
  return json(await apiFetch(`${runPath(runId)}/report`), '루틴 보고서');
}

/** 고를 것이 있는 단계에서 후보 하나를 고른다 — 실행이 running 으로 돌아간다. 잇는 것은 부른 쪽이 따로 한다(ChatContext.resumeRoutine). */
export async function pickCandidate(runId: string, step: string, key: string): Promise<unknown> {
  return json(
    await apiFetch(`${runPath(runId)}/steps/${encodeURIComponent(step)}/pick`,
      { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ key }) }),
    '후보 고르기');
}

/** 실행을 멈춘다 — 스트림을 끊는 것(중지)으로는 서버의 실행이 멈추지 않는다(브라우저가 떠나도 돈다, R3-design D7). */
export async function cancelRun(runId: string): Promise<unknown> {
  return json(await apiFetch(`${runPath(runId)}/cancel`, { method: 'POST' }), '루틴 멈춤');
}
