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

/** 칸 하나 — 모든 칸이 rows · note 를 갖고, 원장을 못 읽었으면 error, 날마다 접어 둔 표가 아직 없으면 pending(M2) */
export interface Section<R> {
  rows: R[];
  note: string;
  error?: boolean;
  pending?: boolean;
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
  /** 끝까지 간 턴의 종류(chat · think · delib · routine)와 답한 모델 — 종류를 적기 전의 턴은 unknown(M3 가) */
  chat_kinds: Section<{ kind: string; turns: number }> & {
    models?: { model: string; turns: number }[];
    unknown?: number;
    since?: string | null;
  };
  chat_errors: Section<{ reason: string; n: number }>;
  events: Section<{ family: string; event: string; status: string; n: number }>;
  conversations: Section<{ day: string; kind: string; source: string; n: number }> & {
    totals?: { kind: string; source: string; n: number; owners: number }[];
    oldest_day?: string | null;
  };
  procedure_runs: Section<RunGroup & { origin: string }> & { completion?: Completion };
  routine_runs: Section<RunGroup & { executor: string }> & {
    completion?: Completion;
    /** 그 가운데 Report Archive 초안까지 간 실행(M2) */
    ra_drafts?: number;
  };
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
  // ── 날마다 접어 둔 표에서 읽는 칸(M2 — docs/ops-dashboard). 원천의 첫 날 전은 null, 접은 적이 없으면 pending ──
  fold_status: Section<FoldSource>;
  active_daily: Section<ActiveDay> & { first_day?: string | null; totals?: Totals };
  active_weekly: Section<{ week: string; people: Num; partial: boolean }>;
  active_monthly: Section<{ month: string; people: Num; partial: boolean }>;
  mcp_daily: Section<{ day: string; calls: Num; status_calls: Num; errors: Num; people: Num }> & {
    first_day?: string | null;
    totals?: Totals;
  };
  mcp_via: Section<
    McpCount & {
      via: string;
      people: number;
      anon_calls: number;
      for_calls: number;
      people_for: number;
    }
  > & {
    via_since?: string | null;
  };
  mcp_apps: Section<
    McpCount & McpLatency & { app: string; cache: number; big: number; tools: number }
  >;
  mcp_tools: Section<
    McpLatency & {
      app: string;
      tool: string;
      status: boolean;
      calls: number;
      errors_app: number;
      errors_gate: number;
      error_rate: number | null;
      cache: number;
      big: number;
    }
  > & { total_tools?: number };
  mcp_auth: Section<{ reason: string; n: number }>;
  mcp_personal_weekly: Section<{ week: string; people: Num; partial: boolean }>;
  delib_jobs: Section<{
    kind: string;
    n: number;
    done: number;
    states: Record<string, number>;
    external: number;
    with_report: number;
    seats_avg: number | null;
    rounds_avg: number | null;
    minutes_avg: number | null;
  }> & { daily?: Num[]; first_day?: string | null; totals?: Totals };
  ra_drafts: Section<{ day: string; n: Num }> & {
    by_via?: { via: string; n: number }[];
    totals?: Totals;
  };
  front_door: Section<{
    service: string;
    label: string;
    requests: number;
    days: number;
    people_max: number;
    daily: Num[];
  }> & { first_day?: string | null; totals?: Totals };
  snapshots: Section<{
    day: string;
    pats_live: Num;
    pats_personal: Num;
    pats_exchanged: Num;
    connections: Num;
    accounts_active: Num;
    grants: Num;
    pats_issued: Num;
  }> & { days?: number };
  conversations_kept: Section<{ kind: string; source: string; n: number }>;
  /** 에이전트 서버의 LLM 토큰 — 종류 × 모델(사람을 뺀 합). daily 는 날마다 입력 + 출력(적기 시작한 날 전은 null) — OD-53 */
  llm_tokens: Section<LlmTokens & { kind: string; model: string }> & {
    daily?: Num[];
    since?: string | null;
    totals?: LlmTokens & { people: number };
  };
  /** 사람별 이용 — 관리자 화면에서 이메일이 나오는 유일한 칸(사용자 결정 2026-11-22 · OD-55) */
  people: Section<PersonRow> & { total?: number; truncated?: boolean };
}

export interface LlmTokens {
  calls: number;
  /** 사용량이 오지 않은 호출(흘려 받는 호출 · 외부 응답자) — 토큰을 모른다 */
  unknown: number;
  tokens_in: number;
  tokens_out: number;
  cache_read: number;
}

export interface PersonRow {
  email: string;
  affiliation: string;
  affiliation_label: string;
  login: number;
  chat: number;
  tile: number;
  mcp: number;
  engine: number;
  ra: number;
  delib: number;
  nginx: number;
  active_days: number;
  first_day: string | null;
  last_day: string | null;
  llm_calls: number;
  llm_unknown: number;
  llm_tokens_in: number;
  llm_tokens_out: number;
  llm_cache_read: number;
}

/** 접기 상태 — 원천(포털 원장 · 지금 상태 · 정문 로그 · 게이트웨이 · 에이전트 서버)마다 접은 범위와 마지막 접기의 실패 까닭 */
export interface FoldSource {
  source: string;
  label: string;
  first_day: string | null;
  last_day: string | null;
  closed_through: string | null;
  days: number;
  other_list_days: number;
  attempt_at: number | null;
  error: string | null;
}

/** 원천을 가로지른 쓴 사람 — people 은 그날의 서로 다른 계정, 나머지는 갈래마다(한 사람이 여러 갈래에 든다) */
export interface ActiveDay {
  day: string;
  people: Num;
  login: Num;
  chat: Num;
  tile: Num;
  mcp: Num;
  /** 호출자가 빈 엔진 호출을 '누구의 일' 감사 머리로 이은 사람(검증하지 않은 주장 — OD-52) */
  engine: Num;
  delib: Num;
  nginx: Num;
}

export interface McpCount {
  calls: number;
  status_calls: number;
  errors_app: number;
  errors_gate: number;
  error_rate: number | null;
}

/** 걸린 시간(ms)의 분위수 — 칸 안 보간 어림이라 화면이 ≈ 를 붙인다. 표본이 없으면 null */
export interface McpLatency {
  ms_p50: number | null;
  ms_p95: number | null;
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
