// 발표자료로 창구(/agent/deck) — 상태 · 만들기 · 진행 · 한 걸음(렌더 맡기기 · 끝 알림) · 내 목록 · 숨기기(docs/wda-deck)
import type { ActivityItem } from '../types/chat';
import { apiFetch, errorDetail } from './client';

export type DeckTarget = 'pptx' | 'pdf' | 'docx' | 'html' | 'video';
export type DeckDocStyle = 'report' | 'brief' | 'memo';
/** 화면의 낱말 하나 — 포털이 WDA 의 파이프라인 · 렌더 낱말을 접어 준다(PLAN §7.2). */
export type DeckState = 'queued' | 'preparing' | 'rendering' | 'done' | 'failed';

/** 단추를 보일지 — 스위치 · 권한 둘 · WDA 능력(owner). formats.deliberation 이 거짓이면 심의 보고서의 단추는 숨긴다(사용자 결정 U-6). */
export interface DeckStatus {
  enabled: boolean;
  reason: string | null;
  formats: { deliberation: boolean };
  targets: DeckTarget[];
  doc_styles: DeckDocStyle[];
  defaults: { targets: DeckTarget[]; doc_style: DeckDocStyle };
  keep_days: number;
}

export interface DeckFile {
  kind: DeckTarget;
  bytes: number | null;
  label: string;
  /** 포털 경로(/agent/deck/jobs/<잡>/files/<kind>) — WDA 주소가 아니다. */
  url: string;
}

/** 끝난 잡의 대화 알림 — 서버가 그 대화의 서버 사본에 이미 남겼다. 화면은 화면 사본에만 붙인다. */
export interface DeckNotice {
  text: string;
  activity: ActivityItem[];
  deck: { job_id: string; state: string; report_id: number; files: string[] };
}

export interface DeckJob {
  job_id: string;
  report: { id: number; title: string };
  options: { targets: DeckTarget[]; doc_style: DeckDocStyle; pptx_mode: string };
  conversation_id: string;
  created_at: number;
  elapsed_s: number;
  /** 입력창 위 줄에서 숨겼다 — 끝나지 않았으면 목록에 실리고 줄이 계속 한 걸음씩 간다(화면에는 보이지 않는다, WD-D59). */
  dismissed?: boolean;
  state: DeckState;
  step: string;
  progress: number | null;
  error: string | null;
  late: boolean;
  /** render — 렌더를 맡겨야 한다 · finish — 끝을 적고 알림을 남겨야 한다(둘 다 advance 가 한다). */
  next: 'render' | 'finish' | null;
  skipped: { target: string; reason: string }[];
  files: DeckFile[];
  /** 끝난 잡의 파일이 WDA 에서 지워졌다(받기가 404 · 410) — 링크 대신 '다시 만들기'(WD-D62). */
  expired?: boolean;
  created?: boolean;
  notice?: DeckNotice | null;
  noticed?: boolean;
  /** 끝(파일 · 링크)은 적었고 대화 알림만 미뤄 두었다 — 그 대화에 질문이 돌고 있었다. next 는 finish 로 남아 다음 걸음이 알림을 남긴다(WD-D75). */
  notice_pending?: boolean;
  deferred?: boolean;
}

/** 발표자료 창구의 거절 — 화면이 상태로 가른다(404 = 박스 스위치가 꺼졌거나 그 잡이 없다 — 묻기를 멈춘다, WD-D65). */
export class DeckHttpError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function json<T>(r: Response, fallback: string): Promise<T> {
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new DeckHttpError(errorDetail(j?.detail, `${fallback} (HTTP ${r.status}).`), r.status);
  return j as T;
}

export async function deckStatus(): Promise<DeckStatus> {
  return json<DeckStatus>(await apiFetch('/agent/deck/status'), '발표자료 상태를 못 읽었습니다');
}

/** 잡을 맡겼다는 신호 — 입력창 위 '만들고 있는 발표자료' 줄이 목록을 다시 읽는다(단추 칸이 다른 대화로 옮겨 가 사라져도 그 줄이 잇는다). */
export const DECK_CHANGED = 'hwax:deck-changed';

export async function createDeck(body: {
  report_id: number; conversation_id: string; targets: DeckTarget[]; doc_style: DeckDocStyle; again?: boolean;
}): Promise<DeckJob> {
  const j = await json<DeckJob>(await apiFetch('/agent/deck/jobs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }), '발표자료를 맡기지 못했습니다');
  window.dispatchEvent(new Event(DECK_CHANGED));
  return j;
}

export async function deckJob(jobId: string): Promise<DeckJob> {
  return json<DeckJob>(await apiFetch(`/agent/deck/jobs/${encodeURIComponent(jobId)}`), '진행을 못 읽었습니다');
}

export async function advanceDeck(jobId: string): Promise<DeckJob> {
  return json<DeckJob>(await apiFetch(`/agent/deck/jobs/${encodeURIComponent(jobId)}/advance`, { method: 'POST' }),
    '발표자료를 마무리하지 못했습니다');
}

export async function deckJobs(): Promise<{ jobs: DeckJob[]; keep_days?: number }> {
  const j = await json<{ jobs?: DeckJob[]; keep_days?: number }>(await apiFetch('/agent/deck/jobs'), '발표자료 목록을 못 읽었습니다');
  return { jobs: Array.isArray(j.jobs) ? j.jobs : [], keep_days: j.keep_days };
}

export async function dismissDeck(jobId: string): Promise<void> {
  await apiFetch(`/agent/deck/jobs/${encodeURIComponent(jobId)}/dismiss`, { method: 'POST' }).catch(() => undefined);
}
