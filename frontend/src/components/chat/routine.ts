// 챗의 분석 루틴 상태 조각 — SSE routine 프레임을 메시지의 실행 상태로 합치고, 포털 실행 보기를 같은 꼴로 바꾸고, 상태 · 준비도 라벨과 다시 읽기 간격을 둔다(docs/analysis-routines R3)
import type { CSSProperties } from 'react';
import type { Readiness, RunView } from '../../api/routines.api';
import type {
  RoutineCandidate,
  RoutineEvent,
  RoutineRunState,
  RoutineState,
  RoutineStepState,
  RoutineStepView,
} from '../../types/chat';

// 노드 시험(backend/tests/test_routine_front_state.py)이 이 파일만 옮겨 적어 부른다 — 값으로 끌어오는 import 를 두지 않는다(타입만).
// 화면 조각(.tsx)에 두면 react-refresh 규칙에 걸리고 노드가 읽지 못한다(ChatContext 의 mergeDelib 가 그래서 시험 밖이다).

/** 낭독기에만 들리는 알림 줄의 꼴 — 루틴 칸 · 고르기 창이 늘 그려 두고 글만 바꾼다(글과 함께 끼운 칸은 낭독기가 놓친다). 화면에는 자리를
 *  차지하지 않는다(칸의 flex 틈도 늘리지 않는다). 보이는 글은 표지 · 단추 곁이 이미 말한다. */
export const SR_ONLY: CSSProperties = {
  position: 'absolute', width: 1, height: 1, margin: -1, padding: 0, border: 0,
  overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap',
};

/** 단계 상태 라벨 — 포털 STATE_LABEL(app/procedures/routines.py)과 같은 글이다(시험이 맞댄다). */
export const ROUTINE_STEP_LABEL: Record<string, string> = {
  pending: '아직',
  running: '도는 중',
  ok: '끝남',
  empty: '결과 없음',
  ambiguous: '고를 것 있음',
  denied: '권한 없음',
  not_connected: '토큰 없음',
  unavailable: '이 박스에 없음',
  failed: '실패',
  skipped: '건너뜀',
} satisfies Record<RoutineStepState, string>;

/** 실행 상태 라벨 — 포털 RUN_STATES 의 일곱이다. */
export const ROUTINE_RUN_LABEL: Record<string, string> = {
  queued: '줄',
  running: '도는 중',
  waiting: '고를 것',
  done: '끝남',
  failed: '실패',
  cancelled: '멈춤',
  interrupted: '끊김',
} satisfies Record<RoutineRunState, string>;

/** 단계 준비도 라벨 — 절차 화면의 루틴 보기(RoutinesView)와 챗의 루틴 고르기가 함께 쓴다. */
export const READY_LABEL: Record<string, string> = {
  allowed: '부를 수 있음',
  not_connected: '토큰 등록 필요',
  denied: '권한 없음',
  unavailable: '이 박스에 없음',
} satisfies Record<Readiness, string>;

/** 단계 제목을 사슬 글로 — '기준 키 → 시장불량 이력 → 메커니즘'. */
export function chain(steps: { title: string }[]): string {
  return steps.map((s) => s.title).join(' → ');
}

/** 실행이 아직 돈다(줄 · 도는 중). */
export function isRoutineLive(state: string): boolean {
  return state === 'queued' || state === 'running';
}

/** 실행이 끝났다(끝남 · 실패 · 멈춤) — 더 읽을 것이 없다. waiting · interrupted 는 사람이 이어 갈 수 있어 끝이 아니다. */
export function isRoutineTerminal(state: string): boolean {
  return state === 'done' || state === 'failed' || state === 'cancelled';
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => !!v && typeof v === 'object' && !Array.isArray(v);
// 프레임 칸은 꼴이 맞을 때만 받는다 — 없거나 다르면 undefined(던지지 않는다).
const str = (v: unknown): string | undefined => (typeof v === 'string' ? v : undefined);
const strs = (v: unknown): string[] | undefined =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : undefined;
const strOrNull = (v: unknown): string | null | undefined => (typeof v === 'string' || v === null ? v : undefined);

function toCandidates(v: unknown): RoutineCandidate[] {
  if (!Array.isArray(v)) return [];
  return v
    .filter(isObj)
    .map((c) => ({ key: String(c.key ?? ''), label: String(c.label ?? c.key ?? '') }))
    .filter((c) => c.key !== '');
}

// 단계 하나를 고친다 — 계획에 없던 단계면(plan 보다 먼저 온 프레임) 뒤에 붙인다.
function withStep(
  steps: RoutineStepView[],
  id: string,
  title: string | undefined,
  fn: (s: RoutineStepView) => RoutineStepView,
): RoutineStepView[] {
  const i = steps.findIndex((s) => s.id === id);
  if (i < 0) return [...steps, fn({ id, title: title || id, kind: '', state: 'pending' })];
  return steps.map((s, k) => (k === i ? fn(s) : s));
}

/** SSE routine 프레임 하나를 메시지의 실행 상태에 합친다(R3-design §3.2). 모르는 kind 는 그대로 돌려준다.
 *  다시 붙기는 지금까지의 프레임을 다시 보내므로 같은 프레임이 두 번 와도 결과가 같아야 한다 — plan 은 단계를 다시 세우되
 *  이미 받은 요약 · 까닭 · 표지 · 호출 수를 남긴다. 칸이 빠진 프레임에서 던지지 않는다. */
export function mergeRoutine(prev: RoutineState | undefined, e: RoutineEvent): RoutineState {
  const ev: Obj = isObj(e) ? e : {};
  const cur: RoutineState = prev ?? { run_id: str(ev.run_id) ?? '', title: str(ev.title) ?? '', state: 'running', steps: [] };
  const runId = str(ev.run_id) || cur.run_id;
  switch (ev.kind) {
    case 'plan': {
      const known = new Map(cur.steps.map((s) => [s.id, s] as const));
      const steps = Array.isArray(ev.steps)
        ? ev.steps.filter(isObj).flatMap((s): RoutineStepView[] => {
            const id = str(s.id);
            if (!id) return [];
            const old = known.get(id);
            const backends = strs(s.backends);
            const label = str(s.label);
            return [{
              ...old,
              id,
              title: str(s.title) || old?.title || id,
              kind: str(s.kind) ?? old?.kind ?? '',
              // 계획의 상태는 지금 원장의 것이다(포털이 고친 값) — 앞서 받은 것보다 낫다
              state: str(s.state) || old?.state || 'pending',
              ...(backends ? { backends } : {}),
              ...(label !== undefined ? { label } : {}),
            }];
          })
        : cur.steps;
      const state = str(ev.state) || cur.state;
      const routineId = str(ev.routine_id);
      const next: RoutineState = {
        ...cur,
        run_id: runId,
        title: str(ev.title) || cur.title,
        state,
        steps,
        ...(routineId ? { routine_id: routineId } : {}),
        // '이어 돌림' 은 실행이 실제로 이어 돈 때만 — 실행기는 run_id 요청이면 늘 resumed 를 단다(RA 초안 올리기 · '이미 끝났다' · 고를 것에서
        // 선 실행의 다시 보냄). 그 계획은 끝났거나 선 실행이라 건너뛰고 이어 돈 것이 없다. 다시 붙기 · 원장에서 잇기는 도는(running) 계획이다.
        ...(typeof ev.resumed === 'boolean' ? { resumed: ev.resumed && isRoutineLive(state) } : {}),
      };
      if (state !== 'waiting') delete next.gate;
      return next;
    }
    case 'step': {
      const id = str(ev.step);
      if (!id) return cur;
      const detail = str(ev.detail);
      const steps = withStep(cur.steps, id, str(ev.title), (s) => {
        const next: RoutineStepView = { ...s, state: str(ev.state) || 'running' };
        if (detail) next.detail = detail;
        else delete next.detail; // 단계 시작 — 앞선 진행 한 줄을 남기지 않는다
        return next;
      });
      return { ...cur, run_id: runId, steps };
    }
    case 'step_done': {
      const id = str(ev.step);
      if (!id) return cur;
      const summary = str(ev.summary);
      const reason = str(ev.reason);
      const flags = strs(ev.flags);
      const steps = withStep(cur.steps, id, str(ev.title), (s) => {
        // 상태는 포털이 원장과 맞대 고친 값이다(호출 없이 '했다' 면 skipped 등) — 실행기가 보낸 봉투의 상태가 아니다
        const next: RoutineStepView = { ...s, state: str(ev.state) || s.state };
        delete next.detail;
        if (summary !== undefined) next.summary = summary;
        if (reason !== undefined) next.reason = reason;
        if (flags) next.flags = flags;
        if (typeof ev.calls === 'number' && Number.isFinite(ev.calls)) next.calls = ev.calls;
        return next;
      });
      return { ...cur, run_id: runId, steps };
    }
    case 'gate': {
      const message = str(ev.message);
      return {
        ...cur,
        run_id: runId,
        state: 'waiting',
        gate: { step: str(ev.step) ?? '', candidates: toCandidates(ev.candidates), ...(message ? { message } : {}) },
      };
    }
    case 'report': {
      const report: NonNullable<RoutineState['report']> = {};
      const upload = str(ev.ra_upload);
      if (upload !== undefined) report.ra_upload = upload;
      const rid = ev.ra_report_id;
      if (typeof rid === 'number' || typeof rid === 'string' || rid === null) report.ra_report_id = rid;
      const raError = strOrNull(ev.ra_error);
      if (raError !== undefined) report.ra_error = raError;
      const raNext = strOrNull(ev.ra_next);
      if (raNext !== undefined) report.ra_next = raNext;
      const warnings = strs(ev.warnings);
      if (warnings) report.warnings = warnings;
      return { ...cur, run_id: runId, report };
    }
    case 'done': {
      // 스트림의 마지막 routine 프레임 — done · waiting · failed · cancelled, 또는 running(실행기 오류로 멈춤 — 이어서 갈 수 있다)
      const state = str(ev.state) || cur.state;
      const reason = str(ev.reason);
      const next: RoutineState = { ...cur, run_id: runId, state, ...(reason ? { reason } : {}) };
      if (isRoutineTerminal(state)) delete next.gate;
      return next;
    }
    default:
      return cur;
  }
}

/** 포털 실행 보기(GET /routines-api/runs/{id}) → 메시지의 실행 상태 꼴. 흐르지 않는 메시지(되살린 대화 · 다시 열기)를 채운다.
 *  원장에 행이 없는 단계는 서버가 상태를 null 로 준다 — 'pending' 으로 본다. 고를 것은 실행이 waiting 일 때 ambiguous 단계의 후보다. */
export function routineFromRunView(view: RunView): RoutineState {
  const run = view.run;
  const rows = Array.isArray(view.steps) ? view.steps : [];
  const steps = rows.map((s): RoutineStepView => ({
    id: s.id,
    title: s.title || s.id,
    kind: s.kind || '',
    state: s.state || 'pending',
    calls: typeof s.calls === 'number' ? s.calls : 0,
    ...(s.summary ? { summary: s.summary } : {}),
    ...(s.reason ? { reason: s.reason } : {}),
    ...(s.flags?.length ? { flags: s.flags } : {}),
    ...(s.backends?.length ? { backends: s.backends } : {}),
    ...(s.label ? { label: s.label } : {}),
  }));
  const gated = run.state === 'waiting' ? rows.find((s) => s.state === 'ambiguous') : undefined;
  return {
    run_id: run.id,
    routine_id: run.routine_id,
    title: run.title || view.report?.title || '',
    state: run.state,
    steps,
    ...(run.reason ? { reason: run.reason } : {}),
    ...(gated ? { gate: { step: gated.id, candidates: toCandidates(gated.candidates) } } : {}),
    ...(run.report_ready
      ? { report: { ra_upload: view.report?.upload, ra_report_id: run.ra_report_id ?? null, ra_error: run.ra_error ?? null } }
      : {}),
  };
}

/** 흐르지 않는 메시지가 도는 실행을 다시 읽는 간격(밀리초) — 처음은 5초다. 숨은 탭 · 읽기 실패 뒤 다시 보기도 이 간격이다. */
export const ROUTINE_POLL_MS = 5000;
// 실행 · 단계가 12번 잇달아(약 1분) 그대로면 30초로 늦춘다 — 심의 단계는 분 ~ 시간을 돌고(R3 D5) 그동안 5초마다 원장을 읽을 까닭이 없다.
const ROUTINE_POLL_SLOW_MS = 30000;
const ROUTINE_POLL_SLOW_AFTER = 12;

/** 다시 읽은 실행이 바뀌었는지 가르는 지문 — 실행 상태와 단계마다 id · 상태 · 호출 수(단계 칩이 그리는 것). 요약 · 마감 같은 다른 칸은 보지 않는다. */
export function routineFingerprint(state: RoutineState): string {
  return JSON.stringify([state.state, state.steps.map((s) => [s.id, s.state, s.calls ?? 0])]);
}

/** 다시 읽기 셈 — 앞서 읽은 지문 · 그대로 잇달은 수 · 다음 읽기까지(밀리초). */
export interface RoutinePoll {
  fp: string;
  same: number;
  delay: number;
}

/** 한 번 읽은 뒤의 셈 — 앞 지문과 같으면 '그대로' 를 하나 더 세고 바뀌었으면 0 부터 센다. 그대로가 12번 잇달면 다음 읽기는 30초 뒤, 아니면 5초 뒤다.
 *  prev 가 null 이면(처음 읽기 · 사람이 이어서 · 고르기 · 멈춤을 눌러 다시 읽기를 처음부터 세울 때) 바뀐 것으로 센다. */
export function nextRoutinePoll(prev: RoutinePoll | null, state: RoutineState): RoutinePoll {
  const fp = routineFingerprint(state);
  const same = prev !== null && prev.fp === fp ? prev.same + 1 : 0;
  return { fp, same, delay: same >= ROUTINE_POLL_SLOW_AFTER ? ROUTINE_POLL_SLOW_MS : ROUTINE_POLL_MS };
}
