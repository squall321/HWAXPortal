// 관리자 '도구 검색 검토' API — 게이트웨이 검색 고리 창구를 포털이 공유 비밀로 대신 부른다(docs/request-1029 E-9)
import { apiFetch, errorDetail } from './client';

/** 찾은 뒤 600초 안에 같은 호출자가 부른 백엔드 도구 — r 은 그 찾기의 순위(결과에 없었으면 null) */
export interface SearchOutcome {
  t: string;
  r: number | null;
  ok: boolean;
}

export interface SearchMark {
  gold: string[];
  verdict: 'ok' | 'gold';
  at: string;
}

/** 질의 한 줄 — 이름은 정답 꼴 '앱키:원래 이름'. 10-29 전 옛 줄은 id · 보정 표지가 없다 */
export interface SearchRow {
  id?: string;
  d: string;
  ts?: number;
  q: string;
  mode: string;
  fp?: string;
  top: string[];
  via?: Record<string, string[]>;
  boost_only?: string[];
  outcomes: SearchOutcome[];
  mark?: SearchMark;
}

export interface SearchLog {
  days: number;
  count: number;
  searches: SearchRow[];
  fingerprint: string;
}

export interface EvalSummary {
  n: number;
  'hit@1'?: number;
  'hit@5'?: number;
  'mrr@20'?: number;
}

export interface SearchEval {
  fingerprint: string;
  base: string;
  pairs: { total: number; measured: number; missing_gold: number; doc?: number; auto?: number; box?: number };
  /** 판(effective · base · off · -묶음) → 출처(전체 · doc · auto · box) → 지표 */
  variants: Record<string, Record<string, EvalSummary>>;
  changed: {
    id: string;
    query: string;
    source: string | null;
    effective: number | null;
    base: number | null;
    off: number | null;
  }[];
  changed_count: number;
  seconds: number;
}

export type Verdict = 'ok' | 'gold' | 'remove';

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body.detail, `${what} 실패 (${res.status})`));
  }
  return (await res.json()) as T;
}

export async function fetchSearchLog(q: { days: number; limit: number; q: string }): Promise<SearchLog> {
  const p = new URLSearchParams({ days: String(q.days), limit: String(q.limit), q: q.q });
  return json(await apiFetch(`/auth/admin/tool-search/log?${p}`), '검색 기록 불러오기');
}

export async function postSearchReview(body: {
  q: string;
  verdict: Verdict;
  gold: string[];
  memo?: string;
  qid?: string | null;
}): Promise<{ ok: boolean; id: string; removed: boolean; pairs: number }> {
  return json(
    await apiFetch('/auth/admin/tool-search/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
    '표시 저장',
  );
}

export async function runSearchEval(): Promise<SearchEval> {
  return json(await apiFetch('/auth/admin/tool-search/eval', { method: 'POST' }), '평가');
}
