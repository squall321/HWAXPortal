// 챗 파일 업로드 API — 수신·목적지 선택·분석(dry_run 미리보기)·확정.
// 목적지는 서버가 준 destinations 에서 사용자가 고른다(확장자 자동 라우팅 안 함).
import { apiFetch, errorDetail } from './client';

export interface UploadDestination {
  id: string;      // 'material' | 'stepforge' | …
  label: string;
}

export interface StagedFile {
  staging_id: string;
  filename: string;
  size: number;
  ext: string;
  content_type: string;
  /** 이 사용자·이 확장자로 고를 수 있는 목적지. 빈 배열이면 보낼 곳이 없다. */
  destinations?: UploadDestination[];
}

export interface StepProject {
  id: string;
  name: string;
}

/** 보내기 응답 — 서버(routes._dispatch_inner)와 같은 모양. 문서 둘(RA · AIDH)과 DynaForge 는 그 자리에서 끝나 `done`, StepForge 는 잡을
 *  세워 `dispatched`, 실패는 `failed`(오류는 error · detail). 종전 타입은 `done` 과 문서 갈래 칸이 없어 화면이 결과를 못 읽었다(docs/chat-ppt A1). */
export interface DispatchResult {
  stage: 'done' | 'dispatched' | 'failed';
  destination?: string;
  error?: string;
  detail?: unknown;
  /** 그 서비스 도구가 돌려준 것 그대로. */
  result?: Record<string, unknown> | null;
  // Report Archive — 만든 보고서 초안
  report_id?: number | string;
  title?: string | null;
  url?: string | null;
  pages?: number;
  blocks?: number;
  warnings?: string[];
  // AI 데이터 허브 — 변환한 inbox 파일 이름
  inbox_name?: string;
  // 이 대화에서 분석 — 저장하지 않고 읽어 온 글(.hwax.md). 화면이 문서 칩으로 붙인다(docs/chat-ppt PP-D17)
  doc?: { name: string; text: string; chars: number };
  // Report Archive 정밀 변환(DocForge, docs/doc-to-ra DF-D17) — 맡기면 dispatched(job_id), 배달하면 done(보고서 + 변환 보고서 요약)
  dropped?: number;
  model_written?: number;
  unaccounted?: number;
  fidelity?: string | null;
  resources?: number;
  conversion_warnings?: string[];
  // StepForge · DynaForge
  project_id?: string;
  created_project?: boolean;
  job_id?: string | null;
  kind?: string | null;
  next?: string;
  session_id?: string;
}

export interface UploadMeta {
  staging_id: string;
  filename: string;
  material_name?: string;
  category?: string;
  material_id?: number | null;
  gauge_length_mm?: number;
  width_mm?: number;
  thickness_mm?: number;
}

export interface TensileProps {
  E_GPa: number | null;
  yield_MPa: number | null;
  UTS_MPa: number | null;
  elong_pct: number | null;
}

export interface UploadResult {
  stage: 'parse' | 'preview' | 'material' | 'committed';
  material_id?: number | null;
  test_id?: number;
  properties?: TensileProps;
  fits?: { model: string; r2: number | null }[];
  warnings?: string[];
  needs_manual_mapping?: boolean;
  reason?: string;
  header?: string[];
  note?: string;
  error?: string;
  curve?: { n_points: number; strain_col: string; stress_col: string };
  material_preview?: unknown;
}

async function jpost(path: string, body: unknown): Promise<UploadResult> {
  const r = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `요청 실패 (HTTP ${r.status}).`));
  return j as UploadResult;
}

export async function uploadFile(file: File): Promise<StagedFile> {
  const fd = new FormData();
  fd.append('file', file);
  const r = await apiFetch('/agent/upload', { method: 'POST', body: fd });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `업로드 실패 (HTTP ${r.status}).`));
  return j as StagedFile;
}

export const analyzeUpload = (m: UploadMeta) => jpost('/agent/upload/analyze', m);
export const commitUpload = (m: UploadMeta) => jpost('/agent/upload/commit', m);

/** StepForge 기존 과제 목록 — 되묻기에서 '새 과제 / 기존 과제에 추가'를 고르게 한다. */
export async function stepProjects(): Promise<StepProject[]> {
  const r = await apiFetch('/agent/upload/destinations/stepforge/projects');
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `과제 목록을 못 읽었습니다 (HTTP ${r.status}).`));
  const rows = (j?.projects ?? j?.result ?? j) as unknown;
  return Array.isArray(rows) ? (rows as StepProject[]) : [];
}

/** 고른 목적지로 스테이징 파일을 보낸다. 서버가 목적지 권한을 다시 판정한다. */
/** 개발단계 — 백엔드 `_STEP_STAGES` 와 같은 목록이어야 한다(어긋나면 조용히 버려진다). */
export const STEP_STAGES = ['선행', 'DV', 'PV', '양산'] as const;

/** DocForge 잡 진행 — 맡긴 사람만(남의 잡은 404). 배달했으면 delivered 에 그 결과. */
export interface DocforgeStatus {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled' | string;
  stage?: string | null;
  progress?: number | null;
  error?: string | null;
  delivered?: DispatchResult;
}

export async function docforgeStatus(jobId: string): Promise<DocforgeStatus> {
  const r = await apiFetch(`/agent/upload/destinations/docforge/jobs/${encodeURIComponent(jobId)}`);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `변환 진행을 못 읽었습니다 (HTTP ${r.status}).`));
  return j as DocforgeStatus;
}

/** 끝난 잡을 그 사람 명의로 RA 에 엄격 생성 — 한 잡은 한 번만(다시 부르면 같은 보고서). */
export async function docforgeDeliver(jobId: string): Promise<DispatchResult> {
  const r = await apiFetch(`/agent/upload/destinations/docforge/jobs/${encodeURIComponent(jobId)}/deliver`, { method: 'POST' });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `Report Archive 에 넣지 못했습니다 (HTTP ${r.status}).`));
  return j as DispatchResult;
}

export async function docforgeCancel(jobId: string): Promise<void> {
  await apiFetch(`/agent/upload/destinations/docforge/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' }).catch(() => undefined);
}

export async function dispatchUpload(body: {
  staging_id: string; filename: string; destination: string; vlm?: boolean;
  project_id?: string; project_name?: string; run?: string;
  // 과제 메타 — 새 과제일 때만 보낸다. 기존 과제 메타는 덮지 않는다.
  code?: string; department?: string; purpose?: string; note?: string; stage?: string;
}): Promise<DispatchResult> {
  const r = await apiFetch('/agent/upload/dispatch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `보내기 실패 (HTTP ${r.status}).`));
  return j as DispatchResult;
}

// ── PC 도우미 — DRM 문서를 PC 의 Office 로 풀어 올린다(docs/chat-ppt B · PP-D8) ─────────────────────────────
// 표는 세션 + CSRF 로만 받는다. 도우미(추출기 -Url 모드)가 그 표로 로그인 없이 한 번 올리고, 화면은 상태를 보다가 받은 글을 문서 칩으로 붙인다.

export interface PcTicket {
  ticket: string;
  expires_in_s: number;
  /** hwax-doc://extract?t=…&name=…&slides=… — 설치 배치가 HKCU 에 이은 PC 도우미를 깨운다. */
  helper_url: string;
  protocol: number;
}

export type PcTicketStateName = 'waiting' | 'opened' | 'receiving' | 'received' | 'failed' | 'cancelled' | 'expired' | 'closed';

export interface PcTicketState {
  state: PcTicketStateName;
  filename: string;
  expires_in_s: number;
  error?: string;
  received?: { doc_name: string; chars: number; bytes: number; slides: number; doc_staging_id: string };
  /** 받은 글이 든 스테이징 상자 — '어디로 보낼까요' 를 이 상자로 연다(다음 단계 — AI 데이터 허브만, PP-D11). */
  staged?: StagedFile;
}

export async function createPcTicket(body: { filename: string; conversation_id?: string; slides?: boolean }): Promise<PcTicket> {
  const r = await apiFetch('/agent/upload/pc-ticket', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `PC 도우미 표를 받지 못했습니다 (HTTP ${r.status}).`));
  return j as PcTicket;
}

export async function getPcTicket(ticket: string): Promise<PcTicketState> {
  const r = await apiFetch(`/agent/upload/pc-ticket/${encodeURIComponent(ticket)}`);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorDetail(j?.detail, `상태를 못 읽었습니다 (HTTP ${r.status}).`));
  return j as PcTicketState;
}

async function pcFile(path: string, name: string, type: string): Promise<File> {
  const r = await apiFetch(path);
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    throw new Error(errorDetail(j?.detail, `받은 파일을 못 읽었습니다 (HTTP ${r.status}).`));
  }
  return new File([await r.blob()], name, { type });
}

/** 받은 글(.hwax.md) — 손으로 붙이던 파일과 같은 File 로 돌려준다(readDoc 이 그대로 읽는다). */
export const fetchPcDoc = (ticket: string, name: string) =>
  pcFile(`/agent/upload/pc-ticket/${encodeURIComponent(ticket)}/doc`, name, 'text/markdown');
/** 받은 슬라이드 그림(n 은 1부터) — readImage 가 그대로 줄인다. */
export const fetchPcSlide = (ticket: string, n: number) =>
  pcFile(`/agent/upload/pc-ticket/${encodeURIComponent(ticket)}/slides/${n}`, `slide-${String(n).padStart(2, '0')}.png`, 'image/png');

// 업로드 권한 그룹 — 백엔드 설정과 맞춘다. 프론트 숨김은 편의고 진짜 방어는 백엔드
// 재검증이다(두 층). ⚠ 목적지별 그룹(upload_allowed_groups·upload_groups_step)을 나눈 뒤로
// 이 목록은 '어느 목적지든 쓸 수 있는 그룹의 합집합' 이어야 한다. 사내 그룹명을 .env 로
// 바꾸면 여기도 함께 고쳐야 한다 — 안 고치면 권한 있는 사용자에게 버튼이 안 보인다.
const UPLOAD_GROUPS = ['portal-admin'];
export function canUpload(groups: string[] | undefined): boolean {
  return !!groups && groups.some((g) => UPLOAD_GROUPS.includes(g));
}
