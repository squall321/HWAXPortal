// 과제 인사이트 API — 과제 목록 · 과제 보기 · 내 카드 · 카드 하나 · 주인의 확인과 쓰기(포털 /insights-api, docs/project-insight-graph M2)
import { apiFetch, errorDetail } from './client';

export type InsightStatus = 'waiting' | 'draft' | 'confirmed' | 'disputed';
export type InsightPath = 'web' | 'mcp-job' | 'mcp-workflow';

export interface InsightArtifact {
  kind: string;
  id: string;
  app?: string;
  rev?: string;
}

export interface InsightSubject {
  sp_task: string | null;
  sp_state: 'confirmed' | 'claimed' | 'none' | null;
  sp_why?: string | null;
  round: string | null;
  round_by: string | null;
  text: string;
  artifacts: InsightArtifact[];
}

export interface InsightCall {
  ref: string;
  tool: string;
  app: string | null;
  args: string;
  sha256: string;
  ok: boolean;
}

/** 카드 한 장 — 서버가 읽는 사람 기준으로 거른 뒤의 꼴이다(보이지 않는 카드는 오지 않는다). */
export interface InsightCard {
  id: string;
  path: InsightPath;
  source_id: string;
  stage: string;
  owner: string;
  mine: boolean;
  status: InsightStatus;
  subject: InsightSubject;
  claim: string;
  claim_from: string;
  claim_edited_by?: string | null;
  claim_edited_at?: number | null;
  tally?: { agree: number; conditional: number; oppose: number; abstain: number };
  report_id?: number | string | null;
  report_url?: string | null;
  model?: string;
  tools?: string[];
  apps?: string[];
  apps_unknown?: string[];
  refs?: string[];
  calls_n: number;
  calls?: InsightCall[];
  scope: string[];
  scope_note?: string | null;
  evidence_known: boolean;
  created_at: number;
  updated_at: number;
  confirmed_at?: number | null;
  continues?: string | null;
  disputed_by?: { by: string | null; note: string; at: number }[];
  disputes?: string[];
}

/** 리스크 앱 등록부의 앞 행 — 그 사람이 risk_get_registry 로 받는 행과 같은 문을 지났다(칸 값 · 상태 낱말 그대로). */
export interface RiskRegistryRow {
  target_key: string;
  cluster_key?: string;
  status?: string | null;
  severity?: string | null;
  attention?: string | null;
  claim?: string | null;
}

/** 리스크 앱의 과제 — 리스크 앱이 그 사람 시야로 낸 것을 그대로 싣는다(상태 낱말을 번역하지 않는다). */
export interface RiskProject {
  project_id: string;
  code?: string;
  name?: string;
  stage?: string | null;
  round?: string | null;
  sp_task?: string | null;
  my_role?: string | null;
  targets?: { target_key: string; kind?: string; level?: string | null; verdict_candidate?: string | null; verdict_final?: string | null }[];
  registry_top?: RiskRegistryRow[];
  registry_total?: number;
}

export interface ProjectCell {
  round: string | null;
  cards: InsightCard[];
  risk: RiskProject[];
}

export interface ProjectView {
  sp_task: string;
  rounds: ProjectCell[];
  risk_error?: string;
  note: string;
}

export interface ProjectRow {
  sp_task: string;
  rounds: Record<string, number>;
  total: number;
  latest_at: number;
  risk: number;
}

export interface MineView {
  waiting: InsightCard[];
  draft: InsightCard[];
  shared: InsightCard[];
  note: string;
}

async function call<T>(path: string, what: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(`/insights-api${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail((body as { detail?: unknown }).detail, `${what} 실패 (${res.status})`));
  }
  return (await res.json()) as T;
}

function post<T>(path: string, what: string, body: unknown = {}): Promise<T> {
  return call<T>(path, what, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

const card = (id: string) => `/cards/${encodeURIComponent(id)}`;

export const fetchProjects = (q = '') =>
  call<{ projects: ProjectRow[]; risk_error?: string; note: string }>(`/projects?${new URLSearchParams({ q })}`, '과제 목록');
export const fetchProject = (spTask: string) =>
  call<ProjectView>(`/project?${new URLSearchParams({ sp_task: spTask })}`, '과제 보기');
export const fetchMine = () => call<MineView>('/mine', '내 카드');
export const fetchCard = (id: string) => call<InsightCard & { note: string }>(card(id), '카드');

export const confirmCard = (id: string) => post<InsightCard>(`${card(id)}/confirm`, '확인');
export const setCardSubject = (id: string, spTask: string, round?: string) =>
  post<InsightCard & { confirmed: boolean }>(`${card(id)}/subject`, '주제 확인', { sp_task: spTask, ...(round ? { round } : {}) });
export const setCardRound = (id: string, round: string) => post<InsightCard>(`${card(id)}/round`, '차수 달기', { round });
export const setCardClaim = (id: string, claim: string) => post<InsightCard>(`${card(id)}/claim`, '주장 고치기', { claim });
export const widenCard = (id: string) => post<InsightCard>(`${card(id)}/widen`, '조직에 열기', { to: 'org' });
export const disputeCard = (id: string, byCard: string, note: string) =>
  post<InsightCard>(`${card(id)}/dispute`, '반박 표시', { ...(byCard ? { by_card: byCard } : {}), note });
export const withdrawCard = (id: string) => post<{ id: string; status: string }>(`${card(id)}/withdraw`, '거두기');
