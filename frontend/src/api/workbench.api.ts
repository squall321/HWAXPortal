// 워크벤치 API 클라이언트 — 레시피·런·단계·도구 카탈로그
//
// ⚠ 접두사는 '/workbench-api' 다. SPA 경로는 '/workbench/*' — 같게 두면 브라우저
//    새로고침이 SPA 가 아니라 JSON 을 받는다('/changelog' 와 '/updates' 를 가른 것과 같다).
import { apiFetch, errorDetail } from './client';

const P = '/workbench-api';

export type ToolInfo = {
  name: string;
  backend: string | null;
  area: string | null;
  description: string;
  inputSchema: { properties?: Record<string, JsonSchema>; required?: string[] };
  schema_fp: string;
};

export type JsonSchema = {
  type?: string | string[];
  title?: string;
  description?: string;
  enum?: unknown[];
  default?: unknown;
  anyOf?: JsonSchema[];
};

export type StepRow = {
  ix: number;
  backend: string;
  tool: string;
  expect: string | null;
  args: Record<string, unknown>;
  args_sha256: string;
  state: 'pending' | 'running' | 'done' | 'failed' | 'unknown' | 'skipped';
  ok: number | null;
  error: string | null;
  stage: string | null;
  duration_ms: number | null;
  result_bytes: number | null;
  truncated: number;
  notes: Record<string, unknown> | null;
};

export type RunDetail = {
  id: string;
  state: 'queued' | 'running' | 'gated' | 'done' | 'failed' | 'cancelled' | 'unknown';
  stage: string | null;
  mode: 'plan' | 'live';
  origin: string;
  title: string | null;
  recipe_version_id: string | null;
  inputs: Record<string, unknown>;
  steps: StepRow[];
  started_at: number;
  ended_at: number | null;
};

export type RunSummary = Omit<RunDetail, 'steps' | 'inputs'>;

export type RecipeRow = {
  id: string;
  title: string;
  owner_sub: string;
  created_by: string;
  visibility: string;
  latest_version: number;
  updated_at: number;
};

export type RecipeVersion = {
  version_id: string;
  recipe_id: string;
  version_no: number;
  author_sub: string;
  created_at: number;
  derived_from_run: string | null;
  spec: { title: string; vars: VarDef[]; steps: StepDef[] };
};

export type VarDef = {
  key: string;
  label: string;
  type: 'string' | 'enum' | 'number' | 'boolean' | 'json';
  values?: string[];
  required?: boolean;
  why?: string;
};

export type StepDef = {
  backend: string;
  tool: string;
  args: Record<string, unknown>;
  save?: Record<string, string> | null;
  gate?: 'human' | null;
  raw?: boolean;
  expect?: string;
  schema_fp?: string | null;
};

async function jsonOf<T>(res: Response, fallback: string): Promise<T> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errorDetail((body as { detail?: unknown }).detail, fallback));
  return body as T;
}

async function get<T>(path: string, fallback: string): Promise<T> {
  return jsonOf<T>(await apiFetch(`${P}${path}`), fallback);
}

async function post<T>(path: string, body: unknown, fallback: string): Promise<T> {
  const res = await apiFetch(`${P}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  return jsonOf<T>(res, fallback);
}

/** 도구 목록 — 사용자 PAT `tools/list` 라 **내가 부를 수 있는 것만** 온다. */
export function listTools() {
  return get<{ count: number; tools: ToolInfo[] }>('/tools', '도구 목록을 불러오지 못했습니다.');
}

export function listRecipes() {
  return get<{ recipes: RecipeRow[] }>('/recipes', '레시피를 불러오지 못했습니다.');
}

export function getRecipe(id: string) {
  return get<RecipeVersion>(`/recipes/${id}`, '레시피를 불러오지 못했습니다.');
}

export function listRuns() {
  return get<{ runs: RunSummary[] }>('/runs', '런 이력을 불러오지 못했습니다.');
}

export function getRun(id: string) {
  return get<RunDetail>(`/runs/${id}`, '런을 불러오지 못했습니다.');
}

export function stepResult(runId: string, ix: number) {
  return get<{ text: string }>(`/runs/${runId}/steps/${ix}/result`, '결과를 불러오지 못했습니다.');
}

/** 레시피 없이 시작하는 **빈 런** — 워크벤치의 진입점이다(레시피 목록이 아니다). */
export function startEmptyRun(title?: string) {
  return post<{ run_id: string; empty?: boolean }>(
    '/runs',
    { mode: 'live', title },
    '런을 시작하지 못했습니다.',
  );
}

export function replayRecipe(recipeId: string, vars: Record<string, unknown>, mode: 'plan' | 'live') {
  return post<{ run_id: string }>(
    '/runs',
    { recipe_id: recipeId, vars, mode },
    '재생을 시작하지 못했습니다.',
  );
}

export function runStep(runId: string, step: Omit<StepDef, 'gate'>) {
  return post<{ run_id: string }>(`/runs/${runId}/steps`, step, '단계를 실행하지 못했습니다.');
}

/** 게이트 확인 — 사람이 본 인자에 묶인다. 확인 뒤 인자가 바뀌면 409 다. */
export function ackGate(runId: string, ix: number, argsSha256: string) {
  return post<{ acked: boolean; resumed: boolean }>(
    `/runs/${runId}/steps/${ix}/ack`,
    { args_sha256: argsSha256 },
    '확인에 실패했습니다.',
  );
}

export function resumeRun(runId: string) {
  return post<{ resumed_at: number }>(`/runs/${runId}/resume`, {}, '재개하지 못했습니다.');
}

export function cancelRun(runId: string) {
  return post<{ cancelled: boolean }>(`/runs/${runId}/cancel`, {}, '중단하지 못했습니다.');
}

export function saveAsRecipe(runId: string, title: string, vars: VarDef[], steps: StepDef[]) {
  return post<{ id: string; version_no: number; warnings: string[] }>(
    `/runs/${runId}/save-as-recipe`,
    { title, vars, steps },
    '레시피로 저장하지 못했습니다.',
  );
}

export function validateSpec(spec: unknown) {
  return post<{ errors: string[]; warnings: string[] }>(
    '/validate',
    { title: 'check', spec },
    '검증하지 못했습니다.',
  );
}
