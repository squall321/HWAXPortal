// 포털 PAT(AI 토큰) 발급·목록·폐기를 감싸는 얇은 API 래퍼 (세션 쿠키 + CSRF는 apiFetch가 처리)
import { apiFetch } from './client';

export interface PatMeta {
  jti: string;
  name: string;
  audiences: string[];
  scopes: string[];
  created: number; // unix seconds
  exp: number; // unix seconds
  revoked: boolean;
}

export interface PatCreated extends PatMeta {
  token: string; // 평문 JWT — 발급 응답에서 한 번만 노출, 서버·로컬 어디에도 저장하지 않음
}

export interface PatCreateBody {
  name: string;
  audiences: string[];
  scopes: string[];
  ttl_days?: number;
}

function detailMessage(detail: unknown, fallback: string): string {
  return typeof detail === 'string' ? detail : fallback;
}

export async function createPat(body: PatCreateBody): Promise<PatCreated> {
  const res = await apiFetch('/auth/pat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(detailMessage(err.detail, `토큰 발급 실패 (${res.status})`));
  }
  return (await res.json()) as PatCreated;
}

export async function listPats(): Promise<PatMeta[]> {
  const res = await apiFetch('/auth/pat');
  if (!res.ok) throw new Error(`토큰 목록을 불러오지 못했습니다 (${res.status})`);
  return (await res.json()) as PatMeta[];
}

export async function revokePat(jti: string): Promise<void> {
  const res = await apiFetch(`/auth/pat/${encodeURIComponent(jti)}`, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(detailMessage(err.detail, `토큰 폐기 실패 (${res.status})`));
  }
}
