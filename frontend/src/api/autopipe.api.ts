// 자동 파이프라인 창구(/autopipe-api) — 상태 · 규칙 · 검증 · 감지 목록 · 현황판 · 실행(docs/auto-pipeline/portal-api.md §6)
//
// 창구 문서는 칸 이름은 정하지만 목록의 봉투(배열인가 {rules: [...]} 인가)와 상세의 묶음은 정하지 않았다. 백엔드와 화면을 동시에
// 지었으므로 여기서 두 꼴을 다 받아 화면 쪽 꼴 하나로 편다(아래 norm* — 화면은 이 꼴만 본다). 저장 칸(check_json · result_json)이
// 글로 와도 편다.
import { apiFetch, errorDetail } from './client';

const BASE = '/autopipe-api';
const JSON_HEAD = { 'Content-Type': 'application/json' };

/** 서버 시각 — epoch 초(포털 원장) 또는 ISO 8601(앱 계약) 둘 다 온다. */
export type Time = number | string;

export type Stage = 'shadow' | 'approve' | 'auto';
export type Verdict = 'pass' | 'fail' | 'marginal' | 'unknown';

export interface Health {
  enabled: boolean;
  how_to_enable?: string | null;
  engine?: { running?: boolean; last_tick?: Time | null; last_error?: string | null } | null;
  sources?: { app: string; cursor_at?: Time | null; last_error?: string | null }[];
  ra?: { configured?: boolean; board?: string | null } | null;
  counts?: Record<string, unknown> | null;
}

export interface RuleStep {
  id: string;
  kind: string;
  app?: string;
  profile?: string;
  report?: string;
  needs?: string[];
}

/** 규칙 스펙(portal-api §2) — 화면은 JSON 글상자로 고치므로 칸을 다 알 필요는 없다. 읽는 칸만 적는다. */
export interface RuleSpec {
  title?: string;
  stage?: Stage | string;
  steps?: RuleStep[];
  [k: string]: unknown;
}

export interface RuleRow {
  id: string;
  title: string;
  enabled: boolean;
  latest_version: number;
  stage?: string | null;
  updated_at?: Time | null;
  created_by?: string | null;
}

export interface RuleVersion {
  version_no: number;
  spec: RuleSpec | null;
  author?: string | null;
  created_at?: Time | null;
}

export interface RuleDetail {
  rule: RuleRow;
  version: RuleVersion | null;
  versions: RuleVersion[];
}

/** 검증 결과의 한 줄 — 글이거나 {path, msg} 꼴 객체다. 화면은 issueText 로 읽는다. */
export type Issue = string | { path?: unknown; loc?: unknown; field?: unknown; msg?: unknown; message?: unknown; detail?: unknown };

export interface ValidateResult {
  ok: boolean;
  errors: Issue[];
  warnings: Issue[];
}

export interface Subject {
  project: string | null;
  revision: string | null;
  state: string;
  block_reason?: string | null;
  last_change?: Time | null;
  first_seen?: Time | null;
}

export interface BoardRow {
  project: string | null;
  revision: string | null;
  run_id: string | null;
  run_state: string;
  superseded_by?: string | null;
  steps: Record<string, { state: string; verdict?: string | null }>;
}

export interface Board {
  /** 열 = 규칙 단계 — 서버가 열을 주지 않으면 화면이 규칙 스펙에서 짓는다. */
  columns: string[];
  rows: BoardRow[];
}

export interface Missing {
  kind: string;
  why?: string;
}

export interface CheckResult {
  ready?: boolean;
  missing?: Missing[];
  inputs?: { kind?: string; ref?: string; sha256?: string }[];
  [k: string]: unknown;
}

export interface Metric {
  name: string;
  label?: string;
  unit?: string;
  value?: number | null;
  limit?: number | null;
  limit_source?: string;
  verdict?: string;
}

/** 결과 봉투(contract.md §2 auto_result) */
export interface Envelope {
  verdict?: string;
  profile?: string;
  app_version?: string;
  metrics?: Metric[];
  figures?: { ref?: string; caption?: string }[];
  artifacts?: { kind?: string; location?: string }[];
  notes?: string[];
  finished_at?: Time;
  [k: string]: unknown;
}

export interface RunStep {
  step_id: string;
  kind: string;
  state: string;
  app?: string | null;
  profile?: string | null;
  report?: string | null;
  run_ref?: string | null;
  check: CheckResult | null;
  result: Envelope | null;
  verdict?: string | null;
  ra_report_id?: string | number | null;
  error?: string | null;
  started_at?: Time | null;
  ended_at?: Time | null;
}

export interface RunEvent {
  id?: string | number;
  at?: Time | null;
  kind: string;
  detail?: unknown;
}

export interface Run {
  id: string;
  rule_id: string;
  rule_title?: string | null;
  version_no?: number | null;
  project: string | null;
  revision: string | null;
  fingerprint?: string | null;
  stage?: string | null;
  state: string;
  superseded_by?: string | null;
  reason?: string | null;
  created_at?: Time | null;
  updated_at?: Time | null;
  ended_at?: Time | null;
}

export interface RunDetail {
  run: Run;
  steps: RunStep[];
  events: RunEvent[];
}

/** 창구 거절 — 검증 오류 목록이 실려 오면 errors 에 둔다(저장 때 검증, portal-api §2). */
export class AutopipeError extends Error {
  status: number;
  errors: Issue[];
  constructor(message: string, status: number, errors: Issue[] = []) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => !!v && typeof v === 'object' && !Array.isArray(v);

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as Obj;
    const d = body.detail;
    // {detail: {errors: [...]}} 또는 {errors: [...]} — 검증 오류 목록을 같이 넘긴다
    const errs = (isObj(d) && Array.isArray(d.errors) ? d.errors : Array.isArray(body.errors) ? body.errors : []) as Issue[];
    const msg = isObj(d) && typeof d.message === 'string' ? d.message : errorDetail(d, `${what} 실패 (${res.status})`);
    throw new AutopipeError(msg, res.status, errs);
  }
  return (await res.json()) as T;
}

/** 배열이거나 {key: [...]} 꼴 — 어느 쪽이든 배열로. */
function listOf<T>(body: unknown, key: string): T[] {
  if (Array.isArray(body)) return body as T[];
  if (isObj(body) && Array.isArray(body[key])) return body[key] as T[];
  if (isObj(body) && Array.isArray(body.items)) return body.items as T[];
  return [];
}

/** 원장 칸이 JSON 글로 오면 편다(check_json · result_json · spec_json). 못 펴면 null. */
function parsed<T>(v: unknown): T | null {
  if (v == null) return null;
  if (typeof v === 'string') {
    try {
      const x = JSON.parse(v);
      return isObj(x) ? (x as T) : null;
    } catch {
      return null;
    }
  }
  return isObj(v) ? (v as T) : null;
}

function normRule(r: Obj): RuleRow {
  return {
    ...(r as unknown as RuleRow),
    id: String(r.id ?? ''),
    title: String(r.title ?? ''),
    enabled: Boolean(r.enabled),
    latest_version: Number(r.latest_version ?? r.version_no ?? 0),
  };
}

function normVersion(v: Obj): RuleVersion {
  return {
    version_no: Number(v.version_no ?? 0),
    spec: parsed<RuleSpec>(v.spec ?? v.spec_json),
    author: (v.author ?? v.author_sub ?? null) as string | null,
    created_at: (v.created_at ?? null) as Time | null,
  };
}

// ── 상태 ─────────────────────────────────────────────────────────────────
export async function getHealth(): Promise<Health> {
  return json(await apiFetch(`${BASE}/health`), '자동 파이프라인 상태');
}

// ── 규칙 ─────────────────────────────────────────────────────────────────
export async function listRules(): Promise<RuleRow[]> {
  const body = await json<unknown>(await apiFetch(`${BASE}/rules`), '규칙 목록');
  return listOf<Obj>(body, 'rules').map(normRule);
}

export async function getRule(id: string): Promise<RuleDetail> {
  const b = await json<Obj>(await apiFetch(`${BASE}/rules/${encodeURIComponent(id)}`), '규칙');
  // {rule, version, versions} 또는 규칙 행에 spec 이 바로 붙은 꼴
  const rule = normRule(isObj(b.rule) ? b.rule : b);
  const vRaw = isObj(b.version) ? b.version : (b.spec ?? b.spec_json) ? { ...b, version_no: rule.latest_version } : null;
  const version = vRaw ? normVersion(vRaw) : null;
  const versions = listOf<Obj>(b.versions ?? [], 'versions').map(normVersion);
  return { rule: { ...rule, stage: rule.stage ?? (version?.spec?.stage as string | undefined) ?? null }, version, versions };
}

export async function createRule(spec: unknown): Promise<{ id: string; version_no: number }> {
  return json(await apiFetch(`${BASE}/rules`, { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ spec }) }), '규칙 저장');
}

export async function addRuleVersion(id: string, spec: unknown): Promise<{ id?: string; version_no: number }> {
  return json(
    await apiFetch(`${BASE}/rules/${encodeURIComponent(id)}/versions`, { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ spec }) }),
    '새 판 저장',
  );
}

export async function setRuleEnabled(id: string, enabled: boolean): Promise<unknown> {
  return json(
    await apiFetch(`${BASE}/rules/${encodeURIComponent(id)}/enabled`, { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ enabled }) }),
    enabled ? '켜기' : '끄기',
  );
}

export async function validateSpec(spec: unknown): Promise<ValidateResult> {
  const b = await json<Obj>(await apiFetch(`${BASE}/validate`, { method: 'POST', headers: JSON_HEAD, body: JSON.stringify({ spec }) }), '검증');
  return { ok: Boolean(b.ok), errors: (b.errors ?? []) as Issue[], warnings: (b.warnings ?? []) as Issue[] };
}

// ── 감지 목록 · 현황판 ─────────────────────────────────────────────────────
export async function listSubjects(q: { project?: string; state?: string; limit?: number } = {}): Promise<Subject[]> {
  const qs = new URLSearchParams();
  if (q.project) qs.set('project', q.project);
  if (q.state) qs.set('state', q.state);
  qs.set('limit', String(q.limit ?? 200));
  return listOf<Subject>(await json<unknown>(await apiFetch(`${BASE}/subjects?${qs}`), '감지 목록'), 'subjects');
}

export async function getBoard(rule: string, limit = 200): Promise<Board> {
  const b = await json<unknown>(await apiFetch(`${BASE}/board?${new URLSearchParams({ rule, limit: String(limit) })}`), '현황판');
  const rows = listOf<BoardRow>(b, 'rows').map((r) => ({ ...r, steps: isObj(r.steps) ? r.steps : {} }));
  // 열 — columns(글 또는 {id}) · steps(단계 정의) 가운데 서버가 준 것. 없으면 빈 목록(화면이 스펙에서 짓는다)
  const rawCols = isObj(b) ? (Array.isArray(b.columns) ? b.columns : Array.isArray(b.steps) ? b.steps : []) : [];
  const columns = rawCols.map((c) => (isObj(c) ? String(c.id ?? c.step_id ?? '') : String(c))).filter(Boolean);
  return { columns, rows };
}

// ── 실행 ─────────────────────────────────────────────────────────────────
const runPath = (id: string) => `${BASE}/runs/${encodeURIComponent(id)}`;

export async function getRun(id: string): Promise<RunDetail> {
  const b = await json<Obj>(await apiFetch(runPath(id)), '실행');
  const runObj = isObj(b.run) ? b.run : b;
  // 단계 행에 앱 · 프로파일이 없으면 실행이 실어 온 규칙 판 스펙에서 채운다(승인 확인 글이 무엇을 내는지 말하게)
  const spec = parsed<RuleSpec>(b.spec ?? runObj.spec ?? runObj.spec_json);
  const steps = listOf<Obj>(b.steps ?? runObj.steps ?? [], 'steps').map((s): RunStep => {
    const step_id = String(s.step_id ?? s.id ?? '');
    const def = spec?.steps?.find((x) => x.id === step_id);
    const str = (v: unknown) => (typeof v === 'string' && v ? v : null);
    return {
      ...(s as unknown as RunStep),
      step_id,
      kind: String(s.kind ?? def?.kind ?? ''),
      state: String(s.state ?? 'pending'),
      app: str(s.app) ?? def?.app ?? null,
      profile: str(s.profile) ?? def?.profile ?? null,
      report: str(s.report) ?? def?.report ?? null,
      check: parsed<CheckResult>(s.check ?? s.check_json),
      result: parsed<Envelope>(s.result ?? s.envelope ?? s.result_json),
    };
  });
  const events = listOf<RunEvent>(b.events ?? runObj.events ?? [], 'events').map((e) => ({
    ...e,
    detail: (e as unknown as Obj).detail ?? parsed((e as unknown as Obj).detail_json),
  }));
  return { run: { ...(runObj as unknown as Run), id: String(runObj.id ?? id), state: String(runObj.state ?? '') }, steps, events };
}

export async function approveRun(id: string): Promise<Obj> {
  return json(await apiFetch(`${runPath(id)}/approve`, { method: 'POST' }), '제출 승인');
}

export async function cancelRun(id: string): Promise<Obj> {
  return json(await apiFetch(`${runPath(id)}/cancel`, { method: 'POST' }), '취소');
}

/** report 단계의 마크다운 — JSON({markdown}) 이든 글(text/markdown)이든 받는다. */
export async function getRunReport(id: string, step: string): Promise<string> {
  const res = await apiFetch(`${runPath(id)}/report?${new URLSearchParams({ step })}`);
  if (!res.ok || !(res.headers.get('Content-Type') ?? '').includes('json')) {
    if (!res.ok) await json(res, '보고서');
    return res.text();
  }
  const b = (await res.json()) as Obj;
  const md = b.markdown ?? b.report_md ?? b.md ?? b.text;
  return typeof md === 'string' ? md : '';
}
