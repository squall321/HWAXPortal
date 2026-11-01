// 관리자 'LLM · GPU 현황' API — 포털이 호스트 수집기(/snapshot · /series)를 대신 묻는다(docs/ops-dashboard PLAN §3.2)
import { apiFetch, errorDetail } from './client';

/** 값 하나 — 마지막으로 제대로 읽은 값(at)과, 마지막 시도가 실패했거나 값이 없는 까닭(error). 주기 셋을 놓치면 stale. */
export interface Cell<T = unknown> {
  value: T | null;
  at: number | null;
  source: string;
  error: string | null;
  stale: boolean;
  age_s: number | null;
  /** 히스토그램 칸으로 어림한 분위수 — 화면이 ≈ 를 붙인다 */
  approx?: boolean;
}

export interface ModelRow {
  id: string;
  max_model_len: number | null;
}

export interface SourceAge {
  at: number | null;
  tried: number | null;
  error: string | null;
  age_s: number | null;
  stale: boolean;
}

export interface LlmTarget {
  id: string;
  label: string;
  /** 호스트:포트만 — 주소 원문(스킴 · 계정 · 경로)은 싣지 않는다 */
  addr: string | null;
  origin: 'targets' | 'upstreams' | 'base' | 'chat' | 'replica';
  group: string | null;
  node: string | null;
  key: 'llm' | 'chat' | null;
  problem: string | null;
  busy: boolean;
  busy_s: number | null;
  polls: number;
  skipped: number;
  sources: Record<string, SourceAge>;
  values: Record<string, Cell>;
}

export interface SideView {
  id: string;
  label: string;
  addr: string | null;
  problem: string | null;
  busy: boolean;
  polls: number;
  skipped: number;
  sources: Record<string, SourceAge>;
  values: Record<string, Cell>;
  caption?: string;
}

export interface StubSection extends Cell<null> {
  rows: unknown[];
  milestone: string;
}

export interface ContextDiff {
  model: string;
  windows: Record<string, number>;
}

export interface LlmSnapshot {
  collector: {
    version: number;
    state: 'ok' | 'stalled';
    now: number;
    started_at: number;
    last_tick_at: number | null;
    tick_age_s: number | null;
    interval_s: number;
    models_every_s: number;
    stale_after_s: number;
    enabled: boolean;
    port: number | null;
    problems: string[];
    db: { bytes: number; series: number; error: string | null };
    keys: Record<string, boolean>;
  };
  targets: LlmTarget[];
  context: Cell<ContextDiff[]>;
  agent: SideView;
  router: SideView | null;
  slurm: StubSection;
  gpu: StubSection;
}

export type SeriesRange = '1h' | '24h' | '7d' | '35d';

export interface LlmSeries {
  target: string;
  metric: string;
  range: SeriesRange;
  step_s: number;
  source: string;
  /** 표본은 [시각, 값], 5분 칸은 [시각, 평균, 최대] */
  points: (number | null)[][];
  at: number | null;
  error: string | null;
  approx: boolean;
}

/** 포털 창구의 실패 — 503 은 수집기가 꺼져 있다, 502 는 수집기가 답하지 않는다 */
export class CollectorError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new CollectorError(errorDetail(body.detail, `${what} 실패 (${res.status})`), res.status);
  }
  return (await res.json()) as T;
}

export async function fetchLlmStatus(): Promise<LlmSnapshot> {
  return json(await apiFetch('/auth/admin/llm-status'), 'LLM · GPU 현황 불러오기');
}

export async function fetchLlmSeries(target: string, metric: string, range: SeriesRange): Promise<LlmSeries> {
  const p = new URLSearchParams({ target, metric, range });
  return json(await apiFetch(`/auth/admin/llm-status/series?${p}`), '그래프 불러오기');
}
