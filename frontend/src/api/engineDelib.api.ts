// MCP 로 연 심의(엔진 잡)를 포털 화면에서 — 진행 카드의 다시 묻기(docs/request-1125 WD-13)
import { apiFetch, errorDetail } from './client';

/** 포털 GET /agent/engine-delib/status/{job_id} 의 답 — 그 사람의 PAT 로 deliberate_status(brief) 를 부른 것. 끝났으면(phase end) 그 사람의
 *  대화에 들었는지(conversation_id — 아직이면 null)도 온다. */
export interface EngineJobStatus {
  job_id: string;
  status: string;
  phase: 'run' | 'end';
  stage?: string | null;
  step?: string;
  round?: number | null;
  total_rounds?: number | null;
  report_id?: number | null;
  error?: string | null;
  finishing?: boolean;
  queue?: { position?: number; ahead?: number; length?: number };
  conversation_id?: string | null;
}

/** 포털이 돌려준 거절 글(AuthError 의 detail · 엔진 거절의 message). */
export async function failText(r: Response, fallback: string): Promise<string> {
  const j = (await r.json().catch(() => null)) as { detail?: unknown; message?: unknown } | null;
  if (j && typeof j.message === 'string' && j.message) return j.message;
  return errorDetail(j?.detail, fallback);
}

export async function fetchEngineJobStatus(jobId: string): Promise<EngineJobStatus> {
  const r = await apiFetch(`/agent/engine-delib/status/${encodeURIComponent(jobId)}`);
  if (!r.ok) throw new Error(await failText(r, `진행을 묻지 못했습니다(HTTP ${r.status})`));
  return (await r.json()) as EngineJobStatus;
}

/** 포털 POST /agent/engine-delib/continue 의 답(docs/request-1125 WD-05) — 엔진이 세운 다음 잡과 대화에 남긴 진행 카드 한 줄. */
export interface EngineContinueResult {
  job_id: string;
  status: string;
  card: unknown;
  text: string;
  saved: boolean;
}

/** MCP 심의 대화의 '이어가기' — 새 웹 심의를 열지 않고 엔진이 같은 잡 계보로 잇는다. 세션 + CSRF(apiFetch 가 싣는다). 거절은 던진다(글). */
export async function continueEngineJob(body: {
  conversation_id: string;
  previous_job_id: string;
  human_note: string;
  rounds?: number;
  keep_seats?: boolean;
}): Promise<EngineContinueResult> {
  const r = await apiFetch('/agent/engine-delib/continue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await failText(r, `엔진에 이어하기를 맡기지 못했습니다(HTTP ${r.status})`));
  return (await r.json()) as EngineContinueResult;
}

/** 내 엔진 잡 목록의 한 행(포털 GET /agent/engine-delib/jobs — 엔진 deliberate_list 를 그 사람의 PAT 로, docs/request-1125 WD-08). */
export interface EngineJobRow {
  job_id: string;
  job?: string | null;
  label?: string | null;
  status?: string | null;
  question: string;
  question_chars: number;
  chair_template?: string | null;
  round?: number | null;
  total_rounds?: number | null;
  report_id?: number | null;
  mine: boolean;
  owner: string;
  /** 잡 id 의 시각(엔진 박스 현지 — 'YYYY-MM-DDTHH:MM:SS') */
  created?: string | null;
  error?: string | null;
  /** 포털이 그 사람의 대화로 들인 잡이면 그 대화(WD-03) */
  conversation_id?: string | null;
}

export interface EngineJobList {
  jobs: EngineJobRow[];
  more: boolean;
  /** 더 보기 — 이 시각을 until 로 다시 묻는다 */
  next_until: string | null;
  window?: { complete: boolean };
}

export async function listEngineJobs(q: {
  since?: string; until?: string; query?: string; job?: string; scope?: 'mine' | 'all'; limit?: number;
}): Promise<EngineJobList> {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) if (v !== undefined && v !== '') p.set(k, String(v));
  const r = await apiFetch(`/agent/engine-delib/jobs?${p.toString()}`);
  if (!r.ok) throw new Error(await failText(r, `엔진 잡 목록을 읽지 못했습니다(HTTP ${r.status})`));
  return (await r.json()) as EngineJobList;
}

/** 결정문 전문(GET /agent/engine-delib/jobs/{job_id}/decision) — 포털이 쪽을 이어 원문 그대로 준다. */
export interface EngineDecision {
  job_id: string;
  status?: string | null;
  job?: string | null;
  label?: string | null;
  question: string;
  decision: string;
  plain?: string | null;
  report_id?: number | null;
  error?: string | null;
  note?: string | null;
  conversation_id?: string | null;
}

export async function fetchEngineDecision(jobId: string): Promise<EngineDecision> {
  const r = await apiFetch(`/agent/engine-delib/jobs/${encodeURIComponent(jobId)}/decision`);
  if (!r.ok) throw new Error(await failText(r, `결정문을 읽지 못했습니다(HTTP ${r.status})`));
  return (await r.json()) as EngineDecision;
}
