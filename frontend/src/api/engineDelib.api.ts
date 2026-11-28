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
