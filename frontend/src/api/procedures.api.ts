// 절차 API 클라이언트 — 절차·실행·단계·도구 카탈로그
//
// ⚠ 접두사는 '/procedures-api' 다. SPA 경로는 '/procedures/*' — 같게 두면 브라우저
//    새로고침이 SPA 가 아니라 JSON 을 받는다('/changelog' 와 '/updates' 를 가른 것과 같다).
import { apiFetch, errorDetail } from './client';
import { config } from '../config';

const P = '/procedures-api';

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
  procedure_version_id: string | null;
  procedure_id?: string | null;
  version_no?: number | null;
  inputs: Record<string, unknown>;
  steps: StepRow[];
  started_at: number;
  ended_at: number | null;
};

export type RunSummary = Omit<RunDetail, 'steps' | 'inputs'> & {
  /** 어느 절차의 몇 판본에서 나왔나 — 빈 실행이면 null 이다. */
  procedure_id?: string | null;
  version_no?: number | null;
};

export type ProcedureRow = {
  id: string;
  title: string;
  owner_sub: string;
  created_by: string;
  visibility: string;
  latest_version: number;
  updated_at: number;
  /** 함께 오는 정본 예제에서 들여온 것 — 다시 가져오면 판본이 올라간다. */
  from_seed?: string | null;
};

export type ProcedureVersion = {
  version_id: string;
  procedure_id: string;
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
  /** 기본값이 아니다 — 사람이 "예시 넣기" 를 눌러야 칸에 들어간다. */
  example?: unknown;
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

export type SeedRow = {
  name: string;
  title: string;
  steps?: number;
  vars?: { key: string; label: string; why?: string | null }[];
  gates?: string[];
  backends?: string[];
  broken?: string;
};

/** 리포에 함께 오는 정본 예제 — 첫 화면이 비어 있지 않게 하는 자리. */
export function listSeeds() {
  return get<{ seeds: SeedRow[] }>('/seeds', '씨앗 절차를 불러오지 못했습니다.');
}

export function importSeed(name: string) {
  return post<{ id: string; version_no: number; from_seed: string; warnings: string[];
                updated: boolean }>(
    `/seeds/${encodeURIComponent(name)}/import`,
    {},
    '씨앗을 가져오지 못했습니다.',
  );
}

export function listProcedures() {
  return get<{ procedures: ProcedureRow[] }>('/procedures', '절차를 불러오지 못했습니다.');
}

export function getProcedure(id: string) {
  return get<ProcedureVersion>(`/procedures/${id}`, '절차를 불러오지 못했습니다.');
}

export function listRuns(procedureId?: string) {
  return get<{ runs: RunSummary[] }>(procedureId ? `/runs?procedure_id=${encodeURIComponent(procedureId)}` : '/runs', '실행 이력을 불러오지 못했습니다.');
}

export function getRun(id: string) {
  return get<RunDetail>(`/runs/${id}`, '실행을 불러오지 못했습니다.');
}

export function stepResult(runId: string, ix: number) {
  return get<{ text: string }>(`/runs/${runId}/steps/${ix}/result`, '결과를 불러오지 못했습니다.');
}

/** 절차 없이 시작하는 **빈 실행** — 절차 기능의 진입점이다(절차 목록이 아니다). */
export function startEmptyRun(title?: string) {
  return post<{ run_id: string; empty?: boolean }>(
    '/runs',
    { mode: 'live', title },
    '실행을 시작하지 못했습니다.',
  );
}

export type DraftReason = {
  step: number; tool: string; arg: string;
  kind: 'chain' | 'asked' | 'constant';
  why: string; path?: string; from_step?: number;
};

export type RunDraft = {
  run_id: string;
  spec: { title: string; vars: VarDef[]; steps: StepDef[] };
  reasons: DraftReason[];
  gaps: { step: number; tool: string; kind: string; why: string }[];
  /** 사람이 확정해야 하는 자리 — 변수인지 상수인지 코드가 모른다. */
  needs_human: DraftReason[];
};

export type ProcedureTool = {
  name: string; title: string; description: string;
  inputSchema: { properties?: Record<string, unknown>; required?: string[] };
  version_no: number; human_gates: string[];
};

/** 룰이 여럿을 고르면 **사람이 하나를 고른다.** 확인(ack)과 다른 자리다. */
export function pickCandidate(runId: string, ix: number, value: unknown) {
  return post<{ picked: unknown; resumed: boolean }>(
    `/runs/${runId}/steps/${ix}/pick`,
    { value },
    '후보를 고르지 못했습니다.',
  );
}

export type BatchTable = {
  batch_id: string;
  count: number;
  columns: string[];
  runs: (RunSummary & {
    inputs: Record<string, unknown>;
    /** 어디서 왜 멈췄나 — 상태만으로는 표를 못 읽는다. */
    failed_at: { ix: number; tool: string; error: string } | null;
    /** 결과는 정상인데 경고만이 유일한 신호인 자리가 있다(W120 류). */
    warnings: string[];
  })[];
};

/** 룰이 고른 **전부**를 돌린다 — 하나를 고르는 대신. 기본은 계획 모드다. */
export function fanOut(runId: string, ix: number, mode: 'plan' | 'live' = 'plan',
                       values?: unknown[]) {
  return post<{ batch_id: string; count: number; mode: string;
                runs: { run_id: string; value: unknown }[] }>(
    `/runs/${runId}/steps/${ix}/fan-out`,
    values ? { mode, values } : { mode },
    '전부 돌리지 못했습니다.',
  );
}

/** 비교표 — 한 배치의 실행들을 나란히. `inputs` 를 그대로 열로 편다. */
export function getBatch(batchId: string) {
  return get<BatchTable>(`/batches/${encodeURIComponent(batchId)}`, '비교표를 불러오지 못했습니다.');
}

export type Dispatcher = {
  backend: string; tool: string; selector: string; payload: string;
  list: string | null; describe: string; note: string;
};

/** 등록부에 확정된 2단 도구 — 이 도구는 **뒤에 여럿이 있다**. */
export function listDispatchers() {
  return get<{ dispatchers: Dispatcher[] }>('/dispatchers', '2단 도구 목록을 불러오지 못했습니다.');
}

/** 그 도구 뒤에 무엇이 있나(name 없이) · 하나의 계약(name 주면). */
export function dispatcherItems(backend: string, tool: string, name?: string) {
  const q = name ? `?name=${encodeURIComponent(name)}` : '';
  return get<{
    items?: { name: string; summary: string; category?: string }[];
    selector?: string; payload?: string; note?: string;
    schema?: { properties?: Record<string, unknown>; required?: string[] } | null;
  }>(`/dispatchers/${encodeURIComponent(backend)}/${encodeURIComponent(tool)}/items${q}`,
     '뒤에 무엇이 있는지 알아내지 못했습니다.');
}

/** 결손 하나를 **장부 파일 초안**으로. ⚠ 파일을 쓰지 않는다 — 사람이 읽고 커밋한다. */
export function draftGap(runId: string, gap: Record<string, unknown>, ownerCandidate?: string) {
  return post<{ filename: string; yaml_text: string }>(
    '/gaps/draft',
    { run_id: runId, gap, owner_candidate: ownerCandidate },
    '장부 초안을 만들지 못했습니다.',
  );
}

/** 절차를 YAML 한 장으로. dev 에서 만들고 cae00 에서 쓰는 길이다. */
export function exportProcedureUrl(id: string): string {
  return `${config.apiBase}/procedures-api/procedures/${id}/export`;
}

/** 내보낸 YAML 을 들인다 — **사람이 만든 것과 똑같이** 검증한다. */
export function importProcedureYaml(yamlText: string, title?: string) {
  return post<{ id: string; version_no: number; warnings: string[] }>(
    '/procedures/import',
    title ? { yaml_text: yamlText, title } : { yaml_text: yamlText },
    '가져오지 못했습니다.',
  );
}

/** 이 절차의 **도구 계약** — 이름·설명·입력 스키마. 절차를 도구로 등록하는 다리다. */
export function getProcedureTool(id: string) {
  return get<ProcedureTool>(`/procedures/${id}/tool`, '도구 계약을 불러오지 못했습니다.');
}

/** 이 실행을 절차 **초안**으로 펴 본다. 저장하지 않는다 — 확정은 사람이 한다. */
export function getRunDraft(runId: string) {
  return get<RunDraft>(`/runs/${runId}/draft`, '초안을 만들지 못했습니다.');
}

/** 초안을 **사람이 확정해** 절차로 굳힌다. 결정(어느 상수를 변수로)만 보낸다 —
 *  초안 자체는 서버가 다시 뽑는다(화면이 만든 spec 을 그대로 받지 않는다). */
export function saveDraft(
  runId: string,
  title: string,
  promote: { step: number; arg: string; key?: string; label?: string; why?: string }[],
) {
  return post<{ id: string; version_no: number; warnings: string[] }>(
    `/runs/${runId}/draft/save`,
    { title, promote },
    '절차로 굳히지 못했습니다.',
  );
}

/** 지난 실행을 **그 값 그대로** 다시 돌린다. 기록 재생이 아니라 실제 재계산이다. */
export function replayRun(runId: string, mode: 'plan' | 'live' = 'live') {
  return post<{ run_id: string; state: string; from_run: string }>(
    `/runs/${runId}/replay`,
    { mode },
    '이 실행을 다시 돌리지 못했습니다.',
  );
}

export function replayProcedure(procedureId: string, vars: Record<string, unknown>, mode: 'plan' | 'live') {
  return post<{ run_id: string }>(
    '/runs',
    { procedure_id: procedureId, vars, mode },
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

export function saveAsProcedure(runId: string, title: string, vars: VarDef[], steps: StepDef[]) {
  return post<{ id: string; version_no: number; warnings: string[] }>(
    `/runs/${runId}/save-as-procedure`,
    { title, vars, steps },
    '절차로 저장하지 못했습니다.',
  );
}

export function validateSpec(spec: unknown) {
  return post<{ errors: string[]; warnings: string[] }>(
    '/validate',
    { title: 'check', spec },
    '검증하지 못했습니다.',
  );
}
