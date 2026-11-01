// 관리자 이용 통계 API — 포털 안 원장을 읽을 때 센 한 판(GET /auth/admin/usage, docs/ops-dashboard M1)
import { apiFetch, errorDetail } from './client';

/** 원장의 첫 줄보다 앞선 날 · 주 · 달은 null 이다(기록 전 — 0 이 아니다) */
export type Num = number | null;

export interface UsageRange {
  days: number;
  requested_days: number;
  clamped: boolean;
  max_days: number;
  default_days: number;
  first_day: string;
  last_day: string;
  since: number;
  until: number;
  tz: string;
  /** 기간의 날(KST, YYYY-MM-DD) — 날마다 칸이 이 차례다 */
  axis: string[];
}

/** 칸 하나 — 모든 칸이 rows · note 를 갖고, 원장을 못 읽었으면 error */
export interface Section<R> {
  rows: R[];
  note: string;
  error?: boolean;
}

export interface LoginDay {
  day: string;
  logins: Num;
  failures: Num;
  accounts: Num;
  sso: Num;
  local: Num;
}

export interface Totals {
  [k: string]: number;
}

export interface UsageSections {
  logins_daily: Section<LoginDay> & { first_day?: string | null; totals?: Totals };
  logins_weekly: Section<{ week: string; accounts: Num; partial: boolean }>;
  logins_monthly: Section<{ month: string; accounts: Num; partial: boolean }>;
  logins_method: Section<{ method: string; logins: number; failures: number; accounts: number }>;
  accounts_status: Section<{ status: string; n: number }>;
  accounts_affiliation: Section<{
    affiliation: string | null;
    label: string;
    n: number;
    active: number;
    folded?: number;
  }> & {
    k?: number;
  };
  accounts_new: Section<{ week: string; n: Num; partial: boolean }>;
  tiles: Section<{
    service: string;
    label: string;
    entries: number;
    accounts: number;
    launch: number;
    open: number;
    daily: Num[];
    daily_accounts: Num[];
  }> & { totals?: Totals };
  chat_daily: Section<{ day: string; turns: Num; done: Num; errors: Num; chatters: Num }> & {
    first_day?: string | null;
    totals?: Totals;
  };
  chat_errors: Section<{ reason: string; n: number }>;
  events: Section<{ family: string; event: string; status: string; n: number }>;
  conversations: Section<{ day: string; kind: string; source: string; n: number }> & {
    totals?: { kind: string; source: string; n: number; owners: number }[];
    oldest_day?: string | null;
  };
  procedure_runs: Section<RunGroup & { origin: string }> & { completion?: Completion };
  routine_runs: Section<RunGroup & { executor: string }> & { completion?: Completion };
  pats_live: Section<{ kind: string; n: number; owners: number }>;
  pats_weekly: Section<{ week: string; n: Num; personal: number; partial: boolean }>;
  access_requests: Section<{
    key: string;
    label: string;
    n: number;
    pending: number;
    approved: number;
    rejected: number;
    median_hours: number | null;
  }>;
  connections: Section<{ service: string; n: number; new: number }>;
}

export interface Completion {
  n: number;
  done: number;
  ended: number;
  completion: number | null;
}

export interface RunGroup extends Completion {
  states: Record<string, number>;
}

export interface UsageReport {
  generated_at: number;
  range: UsageRange;
  excluded: { accounts: string[]; setting: string; primer: boolean; note: string };
  sections: Partial<UsageSections>;
}

export async function fetchUsage(days: number): Promise<UsageReport> {
  const res = await apiFetch(`/auth/admin/usage?${new URLSearchParams({ days: String(days) })}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body.detail, `이용 통계 조회 실패 (${res.status})`));
  }
  return (await res.json()) as UsageReport;
}
