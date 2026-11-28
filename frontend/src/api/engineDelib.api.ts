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
