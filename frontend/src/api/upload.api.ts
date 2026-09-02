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

export interface DispatchResult {
  stage: 'dispatched' | 'failed';
  destination?: string;
  project_id?: string;
  created_project?: boolean;
  job_id?: string | null;
  kind?: string | null;
  next?: string;
  error?: string;
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

export async function dispatchUpload(body: {
  staging_id: string; filename: string; destination: string;
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

// 업로드 권한 그룹 — 백엔드 설정과 맞춘다. 프론트 숨김은 편의고 진짜 방어는 백엔드
// 재검증이다(두 층). ⚠ 목적지별 그룹(upload_allowed_groups·upload_groups_step)을 나눈 뒤로
// 이 목록은 '어느 목적지든 쓸 수 있는 그룹의 합집합' 이어야 한다. 사내 그룹명을 .env 로
// 바꾸면 여기도 함께 고쳐야 한다 — 안 고치면 권한 있는 사용자에게 버튼이 안 보인다.
const UPLOAD_GROUPS = ['portal-admin'];
export function canUpload(groups: string[] | undefined): boolean {
  return !!groups && groups.some((g) => UPLOAD_GROUPS.includes(g));
}
