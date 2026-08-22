// 챗 파일 업로드 API — 수신·분석(dry_run 미리보기)·확정. 물성 CSV 왕복.
import { apiFetch, errorDetail } from './client';

export interface StagedFile {
  staging_id: string;
  filename: string;
  size: number;
  ext: string;
  content_type: string;
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

// 업로드 권한 그룹 — 백엔드 config.upload_allowed_groups 와 맞춘다. 프론트 숨김은 편의고
// 진짜 방어는 백엔드 재검증이다(두 층). 기본 portal-admin.
const UPLOAD_GROUPS = ['portal-admin'];
export function canUpload(groups: string[] | undefined): boolean {
  return !!groups && groups.some((g) => UPLOAD_GROUPS.includes(g));
}
