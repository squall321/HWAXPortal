// 심의 주제(과제 · 차수 · 글 · 설계 자료) — 후보를 그 사람의 도구 결과에서만 뽑고 보낼 꼴을 짓는다(과제 인사이트 그래프 M1)
//
// docs/project-insight-graph PLAN §4.1 · §4.3 · §4.6. 포털은 과제 목록을 쥐지 않는다(A13) — 후보는 이 대화에서 그 사람이 부른 도구의 결과
// (StepForge find_plm_task · get_project_meta · list_projects, ODB 잡, DynaForge 리포트)와 고르기 화면의 허브 과제 찾기(그 사람의 PAT)에서만 온다.
// 모델의 글(답 · 결정문)은 보지 않는다. 브라우저가 보낸 주제는 근거가 아니다 — 에이전트 서버가 같은 풀이로 다시 확인한다(여기서는 꼴만 맞춘다).
import type { Conversation, DelibSubject } from '../../types/chat';

/** 차수 — 개발 단계 코드 열한 개(사용자 결정 11-02 PG-17). 에이전트 서버 delib_subject.STAGES 와 같아야 한다(tests/test_subject_front.py 가 견준다). */
export const STAGE_CODES = ['pre', 'dv1', 'dv2', 'dv3', 'dvr', 'pv1', 'pv2', 'pv3', 'pvr', 'pra', 'mp'] as const;
export type StageCode = (typeof STAGE_CODES)[number];

/** 보낼 수 있는 글 상한 — 포털 DelibSubject · 에이전트 서버 delib_subject 와 같은 수다(시험이 견준다). */
export const SUBJECT_TEXT_MAX = 500;
export const SUBJECT_ARTIFACTS_MAX = 8;

export type ArtifactKind = 'mcad' | 'ecad' | 'cae';

/** 허브 과제 후보 한 행 — key 는 결과 행의 key 칸 그대로다(과제코드 · 과제명으로 바꾸지 않는다). */
export interface SpCandidate {
  key: string;
  label?: string;
  taskCode?: string;
  project?: string;
  active: boolean;
  /** 어디서 왔나 — 화면이 출처로 보인다(이 대화의 어느 도구 · 허브 과제 찾기). */
  from: string;
}

export interface ArtifactCandidate {
  kind: ArtifactKind;
  id: string;
  rev?: string;
  label?: string;
  from: string;
}

export interface RoundCandidate {
  code: StageCode;
  from: string;
}

export interface SubjectCandidates {
  sp: SpCandidate[];
  artifacts: ArtifactCandidate[];
  rounds: RoundCandidate[];
}

/** 고르기 화면의 상태 — spTask 가 비면 과제 대상이 아니다(어느 과제에도 잇지 않는다). */
export interface SubjectDraft {
  spTask: string;
  round: StageCode | '';
  text: string;
  artifacts: ArtifactCandidate[];
}

export const EMPTY_SUBJECT: SubjectDraft = { spTask: '', round: '', text: '', artifacts: [] };

/** 서버와 같은 사소한 정규화(NFKC · 공백 빼기 · 소문자) 뒤 글자 그대로 — 아니면 null(차수 모름). '2차' · 'C2' · '양산' 은 차수가 아니다. */
export function normRound(v: unknown): StageCode | null {
  if (typeof v !== 'string') return null;
  const s = v.normalize('NFKC').replace(/\s+/gu, '').toLowerCase();
  return (STAGE_CODES as readonly string[]).includes(s) ? (s as StageCode) : null;
}

// StepForge 도구 — 맨 이름이거나 게이트웨이가 붙인 StepForge 접두(heaxstep_forge_ · stepforgeprod_ — 노출 이름은 박스마다 다르다).
const SF_TOOL = /^(?:[a-z0-9_]*step_?forge[a-z0-9_]*_)?(find_plm_task|get_project_meta|list_projects)$/;
const HEX23 = /^[0-9a-f]{23}$/;
const HEX16 = /^[0-9a-f]{16}$/;
const ULID = /^[0-9A-HJKMNP-TV-Z]{26}$/;
const WALK_MAX = 4000; // 결과 하나에서 볼 객체 수 상한 — 큰 결과가 화면을 멈추지 않게

function str(v: unknown, cap = 200): string | undefined {
  return typeof v === 'string' && v.trim() ? v.trim().slice(0, cap) : undefined;
}

function obj(v: unknown): Record<string, unknown> | null {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

function taskRow(t: Record<string, unknown>, from: string): SpCandidate | null {
  const key = typeof t.key === 'string' && t.key ? t.key : null;
  if (!key) return null;
  const props = obj(t.properties) ?? {};
  const proj = obj(t.project) ?? {};
  return {
    key,
    ...(str(t.label) ? { label: str(t.label) } : {}),
    ...(str(props.task_code, 80) ? { taskCode: str(props.task_code, 80) } : {}),
    ...(str(proj.label) ? { project: str(proj.label) } : {}),
    active: t.active !== false,
    from,
  };
}

/** 결과 안의 객체들을 넓이 우선으로 — 상한(WALK_MAX)까지만. */
function* walk(root: unknown): Generator<Record<string, unknown>> {
  const q: unknown[] = [root];
  let n = 0;
  while (q.length && n < WALK_MAX) {
    const v = q.shift();
    if (Array.isArray(v)) {
      q.push(...v);
      continue;
    }
    const o = obj(v);
    if (!o) continue;
    n += 1;
    yield o;
    for (const x of Object.values(o)) if (x && typeof x === 'object') q.push(x);
  }
}

/** 이 대화의 도구 결과에서 주제 후보를 뽑는다 — 결과를 JSON 으로 못 읽으면(잘린 결과 등) 그 호출은 건너뛴다(찾기로 고른다). */
export function candidatesFromConversation(conv: Conversation | null | undefined): SubjectCandidates {
  const sp = new Map<string, SpCandidate>();
  const arts = new Map<string, ArtifactCandidate>();
  const rounds = new Map<StageCode, RoundCandidate>();
  for (const m of conv?.messages ?? []) {
    for (const a of m.activity ?? []) {
      if (!a.tool || a.ok === false) continue;
      const raw = (a.result_full ?? a.result_preview ?? '').trim();
      if (!raw.startsWith('{') && !raw.startsWith('[')) continue;
      let body: unknown;
      try {
        body = JSON.parse(raw);
      } catch {
        continue;
      }
      const tool = String(a.tool);
      const sf = SF_TOOL.exec(tool)?.[1];
      const top = obj(body);
      if (sf === 'find_plm_task' && top && Array.isArray(top.tasks)) {
        for (const t of top.tasks) {
          const row = obj(t) && taskRow(t as Record<string, unknown>, `이 대화의 ${tool}`);
          if (row && !sp.has(row.key)) sp.set(row.key, row);
        }
      }
      if (sf === 'get_project_meta' && top) {
        const pt = obj(top.plm_task);
        const row = pt && taskRow(pt, `이 대화의 ${tool}(CAD 과제의 허브 과제)`);
        if (row && !sp.has(row.key)) sp.set(row.key, row);
        const id = typeof top.id === 'string' ? top.id.toLowerCase() : '';
        if (HEX23.test(id)) {
          const fp = str(obj(top.revision)?.content_fp, 120);
          arts.set(`mcad:${id}`, { kind: 'mcad', id, ...(fp ? { rev: fp } : {}), ...(str(top.name) ? { label: str(top.name) } : {}),
                                   from: `이 대화의 ${tool}` });
        }
      }
      if (sf === 'list_projects' && top && Array.isArray(top.projects)) {
        for (const p of top.projects) {
          const po = obj(p);
          const id = typeof po?.id === 'string' ? po.id.toLowerCase() : '';
          if (po && HEX23.test(id) && !arts.has(`mcad:${id}`)) {
            arts.set(`mcad:${id}`, { kind: 'mcad', id, ...(str(po.name) ? { label: str(po.name) } : {}), from: `이 대화의 ${tool}` });
          }
        }
      }
      for (const o of walk(body)) {
        // ODB 허브 잡 — 16진 16자 job_id 와 잡 메타 칸(docs/procedures/fixtures/odb-hub/reference.md 3절)
        const jid = typeof o.job_id === 'string' ? o.job_id.toLowerCase() : '';
        if (HEX16.test(jid) && ('board_type' in o || ('revision' in o && 'model' in o)) && !arts.has(`ecad:${jid}`)) {
          const label = [str(o.project, 80), str(o.model, 80)].filter(Boolean).join(' · ');
          arts.set(`ecad:${jid}`, { kind: 'ecad', id: jid, ...(str(o.revision, 120) ? { rev: str(o.revision, 120) } : {}),
                                    ...(label ? { label } : {}), from: `이 대화의 ${tool}` });
        }
        // DynaForge 리포트 — ULID id 와 eng_meta(개발 단계 dev_revision 이 그 안에 있다)
        const em = obj(o.eng_meta);
        const rid = typeof o.report_id === 'string' ? o.report_id : typeof o.id === 'string' ? o.id : '';
        const dev = obj(em?.dev_revision) ?? obj(o.dev_revision);
        const code = normRound(dev?.code);
        if (em && ULID.test(rid.toUpperCase()) && !arts.has(`cae:${rid.toUpperCase()}`)) {
          const id = rid.toUpperCase();
          arts.set(`cae:${id}`, { kind: 'cae', id, ...(code ? { rev: code } : {}),
                                  ...(str(o.title ?? o.name) ? { label: str(o.title ?? o.name) } : {}), from: `이 대화의 ${tool}` });
        }
        if (code && !rounds.has(code)) rounds.set(code, { code, from: `이 대화의 ${tool}(개발 단계 dev_revision)` });
        // 리스크 앱 과제의 stage — 꼴에 맞을 때만 차수 후보다(웹 폼이 받는 dv · pre1 은 차수가 아니다)
        if (/^risk_/.test(tool) && typeof o.stage === 'string') {
          const st = normRound(o.stage);
          if (st && !rounds.has(st)) rounds.set(st, { code: st, from: `이 대화의 ${tool}(리스크 과제 stage)` });
        }
      }
    }
  }
  return { sp: [...sp.values()], artifacts: [...arts.values()].slice(0, 40), rounds: [...rounds.values()] };
}

/** 허브 과제 찾기의 답(포털 POST /agent/deliberate/subject/search) → 후보 행. */
export function candidatesFromSearch(rows: { key: string; label?: string | null; task_code?: string | null; project?: string | null;
  active?: boolean }[], query: string): SpCandidate[] {
  const out: SpCandidate[] = [];
  for (const r of rows) {
    if (!r || typeof r.key !== 'string' || !r.key) continue;
    out.push({ key: r.key, ...(r.label ? { label: r.label } : {}), ...(r.task_code ? { taskCode: r.task_code } : {}),
               ...(r.project ? { project: r.project } : {}), active: r.active !== false, from: `허브 과제 찾기 「${query}」` });
  }
  return out;
}

/** 보낼 꼴(delib_opts.subject) — 빈 칸은 싣지 않는다. 모두 비면 null(주제 없음 — 어느 과제에도 잇지 않는다). */
export function subjectWire(d: SubjectDraft | null | undefined): Record<string, unknown> | null {
  if (!d) return null;
  const arts = d.artifacts.slice(0, SUBJECT_ARTIFACTS_MAX).map((a) => ({ kind: a.kind, id: a.id, ...(a.rev ? { rev: a.rev.slice(0, 120) } : {}) }));
  const sp = d.spTask.trim();
  const text = d.text.trim().slice(0, SUBJECT_TEXT_MAX);
  const w: Record<string, unknown> = {
    ...(sp ? { sp_task: sp } : {}),
    ...(d.round ? { round: d.round } : {}),
    ...(text ? { text } : {}),
    ...(arts.length ? { artifacts: arts } : {}),
  };
  return Object.keys(w).length ? w : null;
}

/** 이어하기가 앞 심의의 주제를 다시 싣는 꼴 — 서버가 확인한 주제(답 meta.subject · 사건)에서 받는 칸 넷만. 서버가 다시 확인한다. */
export function subjectFromPrior(s: DelibSubject | null | undefined): Record<string, unknown> | null {
  if (!s) return null;
  return subjectWire({
    spTask: s.sp_task ?? '',
    round: normRound(s.round) ?? '',
    text: s.text ?? '',
    artifacts: (s.artifacts ?? []).map((a) => ({ kind: a.kind, id: a.id, ...(a.rev ? { rev: a.rev } : {}), from: '앞 심의' })),
  });
}

/** 확인 상태 한 줄 — 심의 화면이 주제 줄에 보인다. */
export function subjectLine(s: DelibSubject): string {
  const rnd = s.round ? `차수 ${s.round}` : '차수 모름';
  if (s.sp_state === 'confirmed') return `과제 「${s.sp_task}」 · ${rnd} — 허브 거울 풀이로 확인했다`;
  if (s.sp_state === 'claimed') return `과제 「${s.sp_task}」 · ${rnd} — 확인하지 못해 어느 과제에도 잇지 않는다${s.sp_why ? `(${s.sp_why})` : ''}`;
  return `과제 없음 · ${rnd} — 어느 과제에도 잇지 않는다`;
}
