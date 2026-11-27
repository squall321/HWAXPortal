// 자동 파이프라인 탭 — 상태 머리 · 규칙(목록 · 편집 · 검증 · 켜기) · 과제 · 차수 현황판 · 실행 상세 · 감지 목록(docs/auto-pipeline portal-api §6)
//
// 화면은 원장을 읽고 사람이 할 셋(규칙 저장 · 켜기 · 제출 승인 · 취소)만 보낸다. 해석 조건은 앱의 프로파일이 정하고, 규칙은 어느 앱의 어느
// 프로파일을 어떤 순서로 부를지만 적는다(AP-1). 상태 낱말은 사람 말로 바꿔 보이고, 모르는 낱말은 그대로 보인다.
// 단계 상태의 순서(대기 → 제출됨 → 도는 중 → 끝)를 가정하지 않는다 — 동기 앱은 제출 응답에서 곧바로 끝난다.
import { useCallback, useEffect, useState } from 'react';
import { NavLink, Route, Routes, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { TextBlock } from '../../components/chat/renderers/TextBlock';
import {
  addRuleVersion,
  approveRun,
  cancelRun,
  createRule,
  getBoard,
  getHealth,
  getRule,
  getRun,
  getRunReport,
  listRules,
  listSubjects,
  setRuleEnabled,
  validateSpec,
  type AutopipeError,
  type Board,
  type CheckResult,
  type Envelope,
  type Health,
  type Issue,
  type RuleDetail,
  type RuleRow,
  type RuleSpec,
  type RuleStep,
  type RunDetail,
  type RunStep,
  type Subject,
  type Time,
} from '../../api/autopipe.api';

// ── 낱말 → 사람 말 ─────────────────────────────────────────────────────────
type Tone = 'ok' | 'warn' | 'danger' | 'info' | 'muted';

const RUN_STATE: Record<string, [string, Tone]> = {
  planned: ['계획만(그림자)', 'muted'],
  awaiting_approval: ['승인 기다림', 'warn'],
  running: ['도는 중', 'info'],
  done: ['끝', 'ok'],
  partial: ['일부 끝', 'warn'],
  failed: ['실패', 'danger'],
  superseded: ['대체됨', 'muted'],
  cancelled: ['취소됨', 'muted'],
};
const STEP_STATE: Record<string, [string, Tone]> = {
  pending: ['대기', 'muted'],
  ready: ['입력 갖춤', 'info'],
  blocked: ['막힘', 'warn'],
  queued: ['제출됨', 'info'],
  running: ['도는 중', 'info'],
  done: ['끝', 'ok'],
  failed: ['실패', 'danger'],
  cancelled: ['취소됨', 'muted'],
  skipped: ['건너뜀', 'muted'],
};
const SUBJECT_STATE: Record<string, [string, Tone]> = {
  waiting_quiet: ['조용해지기를 기다림', 'muted'],
  ready: ['준비됨', 'ok'],
  blocked: ['막힘', 'warn'],
};
/** 판정 — 색만으로 가르지 않는다(기호 + 글자). */
const VERDICT: Record<string, [string, string]> = {
  pass: ['✓', '합'],
  fail: ['✗', '부'],
  marginal: ['△', '경계'],
  unknown: ['?', '모름'],
};
const STAGE: Record<string, string> = { shadow: '그림자(계획만)', approve: '승인 뒤 제출', auto: '자동 제출' };
const KIND: Record<string, string> = { analysis: '해석', report: '보고서', deliberation: '심의' };
const REPORT_KIND: Record<string, string> = { per_analysis: '해석별', summary: '종합', revdiff: '이전 차수 대비' };
/** 막힌 까닭 · 빠진 것(block_reason · check 의 missing[].kind) */
const REASON: Record<string, string> = {
  project_key: '과제 key 를 못 풂',
  revision: '개발 단계(차수)를 모름',
  input: '입력 없음',
  infra: '박스 문제(클러스터 · 저장소 등)',
  permission: '권한 없음',
  human_input: '사람이 줄 값이 필요함',
};
const COUNT: Record<string, string> = {
  rules: '규칙',
  enabled_rules: '켜진 규칙',
  rules_enabled: '켜진 규칙',
  subjects: '감지한 과제 · 차수',
  runs: '실행',
};
/** 끝난 실행 — 취소할 것이 없다. 그림자 실행은 계획(planned)에서 멈추고 제출하지 않는다. */
const RUN_ENDED = new Set(['done', 'partial', 'failed', 'superseded', 'cancelled', 'planned']);
const STEP_ENDED = new Set(['done', 'failed', 'cancelled', 'skipped']);

const AUTO_ENABLE_CONFIRM =
  '이 규칙의 단계는 「자동 제출」입니다.\n켜면 입력이 갖춰진 과제 · 차수마다(제외 목록 빼고 모든 과제) 사람 확인 없이 클러스터 해석 제출이 저절로 시작됩니다.\n켤까요?';
const AUTO_SAVE_CONFIRM =
  '이 규칙은 켜져 있습니다.\n단계를 「자동 제출」로 저장하면 이 판부터 입력이 갖춰진 과제 · 차수마다 사람 확인 없이 클러스터 해석 제출이 저절로 시작됩니다.\n저장할까요?';

const RULE_TEMPLATE = JSON.stringify(
  {
    title: '낙하 · 열충격 기본',
    stage: 'shadow',
    scope: { all_projects: true, exclude: [] },
    trigger: { ready_when: ['step_forge.parsed'], quiet_s: 1800 },
    steps: [
      { id: 'thermal', kind: 'analysis', app: 'thermal_shock', profile: 'default' },
      { id: 'summary', kind: 'report', report: 'summary', needs: ['thermal'] },
    ],
    limits: { max_concurrent: 2, per_project_per_day: 1, night_only: [] },
  },
  null,
  2,
);

function when(v?: Time | null): string {
  if (v == null || v === '') return '—';
  const d = typeof v === 'number' ? new Date(v > 1e12 ? v : v * 1000) : new Date(v);
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString('ko-KR', { hour12: false });
}

/** 'infra' · 'infra: 공유 볼륨 없음' 꼴 — 머리 낱말만 사람 말로 바꾸고 뒤는 그대로 붙인다. */
function reasonText(r?: string | null): string {
  if (!r) return '—';
  const m = /^([a-z_]+)\s*(?:[:—]\s*([\s\S]*))?$/.exec(r.trim());
  if (!m || !REASON[m[1]]) return r;
  return m[2] ? `${REASON[m[1]]} — ${m[2]}` : REASON[m[1]];
}

function issueText(i: Issue): string {
  if (typeof i === 'string') return i;
  const where = i.path ?? i.loc ?? i.field;
  const what = i.msg ?? i.message ?? i.detail;
  const at = Array.isArray(where) ? where.join('.') : where != null ? String(where) : '';
  return `${at ? `${at} — ` : ''}${what != null ? String(what) : JSON.stringify(i)}`;
}

function Chip({ map, state }: { map: Record<string, [string, Tone]>; state: string }) {
  const [label, tone] = map[state] ?? [state || '—', 'muted' as Tone];
  return <span className={`ap-chip is-${tone}`}>{label}</span>;
}

function VerdictTag({ v }: { v?: string | null }) {
  if (!v) return null;
  const [mark, word] = VERDICT[v] ?? ['', v];
  return (
    <span className={`ap-verdict is-${v}`} title={`판정 ${word}`}>
      {mark} {word}
    </span>
  );
}

function stepWhat(s: { kind: string; app?: string | null; profile?: string | null; report?: string | null }): string {
  const k = KIND[s.kind] ?? s.kind;
  if (s.kind === 'report') return `${k}${s.report ? ` · ${REPORT_KIND[s.report] ?? s.report}` : ''}`;
  return `${k}${s.app ? ` · ${s.app}` : ''}${s.profile ? ` · ${s.profile}` : ''}`;
}

// ── 셸 ────────────────────────────────────────────────────────────────────
export default function AutoPipelineView() {
  return (
    <div className="pr-stack">
      <HealthHeader />
      <Routes>
        <Route index element={<AutoHome />} />
        <Route path="rules/new" element={<RuleEditor />} />
        <Route path="rules/:id" element={<RuleEditor />} />
        <Route path="runs/:id" element={<RunView />} />
      </Routes>
    </div>
  );
}

// ── 1. 머리 — 켜짐 · 엔진 · 원천 커서 · RA ──────────────────────────────────
function HealthHeader() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    setErr(null);
    getHealth().then(setH, (e: Error) => setErr(e.message));
  }, []);
  useEffect(load, [load]);

  if (err) return <ErrorBanner message={`자동 파이프라인 상태를 받지 못했습니다 — ${err}`} />;
  if (!h) return <Spinner label="자동 파이프라인 상태를 불러오는 중…" />;
  const eng = h.engine ?? {};
  const counts = Object.entries(h.counts ?? {}).flatMap(([k, v]) =>
    typeof v === 'number' ? [`${COUNT[k] ?? RUN_STATE[k]?.[0] ?? k} ${v}`] : [],
  );
  return (
    <section className={`pr-card pr-card-stack${h.enabled ? '' : ' pr-card-warn'}`} aria-label="자동 파이프라인 상태">
      <div className="pr-row">
        <span className={`ap-chip is-${h.enabled ? 'ok' : 'warn'}`}>{h.enabled ? '켜짐' : '꺼짐'}</span>
        <strong className="pr-subhead pr-grow">자동 파이프라인</strong>
        <button type="button" className="btn-secondary pr-btn-sm" onClick={load}>
          새로 고침
        </button>
      </div>
      {!h.enabled && (
        <div className="pr-callout">
          <p className="pr-m-0 pr-fs-13 pr-fg">
            꺼져 있습니다. 엔진이 돌지 않아 새 차수를 감지하지 않고 해석도 내지 않습니다. 규칙 보기 · 편집 · 검증은 됩니다.
          </p>
          {h.how_to_enable && <p className="pr-note pr-mt-1 pr-m-0 pr-prewrap">켜는 법 — {h.how_to_enable}</p>}
        </div>
      )}
      <span className="pr-meta">
        엔진 {eng.running ? '도는 중' : '멈춤'} · 마지막 박자 {when(eng.last_tick)}
        {eng.last_error && <span className="pr-danger"> · 마지막 오류 — {eng.last_error}</span>}
      </span>
      <span className="pr-meta">
        RA 게시 —{' '}
        {h.ra?.configured
          ? `설정됨${h.ra.board ? `(게시판 ${h.ra.board})` : ''}`
          : '미설정. 보고서는 포털 원장에만 남고 실행 상세에서 읽습니다.'}
      </span>
      {(h.sources ?? []).length > 0 && (
        <ul className="pr-list pr-list-tight" aria-label="원천 앱">
          {(h.sources ?? []).map((s) => (
            <li key={s.app} className="pr-fs-13">
              <span className="pr-fg">{s.app}</span>
              <span className="pr-meta"> · 마지막으로 받은 때 {when(s.cursor_at)}</span>
              {s.last_error && <span className="pr-danger"> · 오류 — {s.last_error}</span>}
            </li>
          ))}
        </ul>
      )}
      {counts.length > 0 && <span className="pr-note">{counts.join(' · ')}</span>}
    </section>
  );
}

// ── 첫 화면 — 규칙 목록 · 현황판 · 감지 목록 ─────────────────────────────────
function AutoHome() {
  const [rules, setRules] = useState<RuleRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    listRules().then(setRules, (e: Error) => setErr(e.message));
  }, []);
  return (
    <>
      <RulesSection rules={rules} err={err} />
      <BoardSection rules={rules ?? []} />
      <SubjectsSection />
    </>
  );
}

// ── 2. 규칙 목록 ───────────────────────────────────────────────────────────
function RulesSection({ rules, err }: { rules: RuleRow[] | null; err: string | null }) {
  return (
    <section className="pr-card-stack" aria-label="규칙">
      <div className="pr-row">
        <h2 className="pr-h2 pr-m-0 pr-grow">규칙</h2>
        <NavLink to="/procedures/auto/rules/new" className="btn-primary pr-btn-sm">
          새 규칙
        </NavLink>
      </div>
      <span className="pr-note">
        한 번 정해 두면 제외 목록을 뺀 모든 과제에 적용됩니다. 어떤 해석을 어떻게 할지는 각 앱의 프로파일이 정하고, 규칙은 어느 앱의 어느
        프로파일을 어떤 순서로 부를지만 적습니다.
      </span>
      {err && <ErrorBanner message={err} />}
      {!err && !rules && <Spinner label="규칙을 불러오는 중…" />}
      {rules && rules.length === 0 && <p className="pr-note">아직 규칙이 없습니다.</p>}
      {rules && rules.length > 0 && (
        <ul className="pr-list">
          {rules.map((r) => (
            <li key={r.id} className="pr-card ap-rule">
              <NavLink to={`/procedures/auto/rules/${encodeURIComponent(r.id)}`} className="pr-link pr-strong">
                {r.title || r.id}
              </NavLink>
              <span className="pr-row">
                <span className={`ap-chip is-${r.enabled ? 'ok' : 'muted'}`}>{r.enabled ? '켜짐' : '꺼짐'}</span>
                <span className="pr-meta">
                  판 {r.latest_version}
                  {r.stage ? ` · ${STAGE[r.stage] ?? r.stage}` : ''}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ── 3. 현황판 — 행 = 과제 · 차수, 열 = 규칙 단계 ─────────────────────────────
function BoardSection({ rules }: { rules: RuleRow[] }) {
  const [sp, setSp] = useSearchParams();
  const ruleId = sp.get('rule') ?? '';
  const nav = useNavigate();
  const [board, setBoard] = useState<Board | null>(null);
  const [steps, setSteps] = useState<RuleStep[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setBoard(null);
    setErr(null);
    if (!ruleId) return;
    let live = true;
    // 열 이름 · 단계 설명은 규칙의 최신 판에서 — 현황판이 열을 주지 않아도 단계 순서대로 선다
    Promise.all([getBoard(ruleId), getRule(ruleId).catch(() => null)])
      .then(([b, d]) => {
        if (!live) return;
        setBoard(b);
        setSteps(d?.version?.spec?.steps ?? []);
      })
      .catch((e: Error) => live && setErr(e.message));
    return () => {
      live = false;
    };
  }, [ruleId]);

  const cols = board
    ? board.columns.length
      ? board.columns
      : steps.length
        ? steps.map((s) => s.id)
        : [...new Set(board.rows.flatMap((r) => Object.keys(r.steps)))]
    : [];
  const def = (c: string) => steps.find((s) => s.id === c);
  const openRun = (id: string | null) => id && nav(`/procedures/auto/runs/${encodeURIComponent(id)}`);

  return (
    <section className="pr-card-stack" aria-label="현황판">
      <div className="pr-row">
        <h2 className="pr-h2 pr-m-0 pr-grow">과제 · 차수 현황판</h2>
        <select
          className="pr-input pr-input-tight ap-rule-pick"
          aria-label="현황판 규칙"
          value={ruleId}
          onChange={(e) => {
            const n = new URLSearchParams(sp);
            if (e.target.value) n.set('rule', e.target.value);
            else n.delete('rule');
            setSp(n, { replace: true });
          }}
        >
          <option value="">규칙을 고르세요</option>
          {rules.map((r) => (
            <option key={r.id} value={r.id}>
              {r.title || r.id}
            </option>
          ))}
        </select>
      </div>
      {!ruleId && <span className="pr-note">규칙을 고르면 그 규칙이 돈 과제 · 차수가 줄마다, 단계가 칸마다 보입니다.</span>}
      {err && <ErrorBanner message={err} />}
      {ruleId && !err && !board && <Spinner label="현황판을 불러오는 중…" />}
      {board && board.rows.length === 0 && <p className="pr-note">이 규칙으로 만든 실행이 아직 없습니다.</p>}
      {board && board.rows.length > 0 && (
        <div className="pr-card-scroll">
          <table className="pr-table ap-table ap-board">
            <thead>
              <tr>
                <th>과제 · 차수</th>
                <th>실행</th>
                {cols.map((c) => {
                  const s = def(c);
                  return (
                    <th key={c}>
                      {c}
                      {s && <span className="pr-note ap-col-sub">{stepWhat(s)}</span>}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {board.rows.map((r, i) => {
                const sup = r.run_state === 'superseded' || !!r.superseded_by;
                return (
                  <tr
                    key={r.run_id ?? `${r.project}-${r.revision}-${i}`}
                    className={`ap-row${sup ? ' ap-superseded' : ''}${r.run_id ? ' ap-click' : ''}`}
                    onClick={() => openRun(r.run_id)}
                  >
                    <td>
                      {r.run_id ? (
                        <NavLink
                          to={`/procedures/auto/runs/${encodeURIComponent(r.run_id)}`}
                          className="pr-link pr-strong"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {r.project ?? '과제 key 없음'}
                        </NavLink>
                      ) : (
                        <span className="pr-strong">{r.project ?? '과제 key 없음'}</span>
                      )}
                      <span className="pr-meta"> · {r.revision ?? '차수 모름'}</span>
                      {sup && r.run_state !== 'superseded' && <span className="ap-chip is-muted ap-ml">대체됨</span>}
                    </td>
                    <td>
                      <Chip map={RUN_STATE} state={r.run_state} />
                    </td>
                    {cols.map((c) => {
                      const cell = r.steps[c];
                      return (
                        <td key={c} className="ap-cell">
                          {cell ? (
                            <>
                              <Chip map={STEP_STATE} state={cell.state} /> <VerdictTag v={cell.verdict} />
                            </>
                          ) : (
                            <span className="pr-note">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ── 5. 감지 목록 ───────────────────────────────────────────────────────────
function SubjectsSection() {
  const [state, setState] = useState('');
  const [rows, setRows] = useState<Subject[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setRows(null);
    setErr(null);
    listSubjects({ state: state || undefined }).then(setRows, (e: Error) => setErr(e.message));
  }, [state]);

  return (
    <section className="pr-card-stack" aria-label="감지 목록">
      <div className="pr-row">
        <h2 className="pr-h2 pr-m-0 pr-grow">감지한 과제 · 차수</h2>
        <select className="pr-input pr-input-tight ap-rule-pick" aria-label="감지 상태" value={state} onChange={(e) => setState(e.target.value)}>
          <option value="">전체</option>
          {Object.entries(SUBJECT_STATE).map(([k, [label]]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <span className="pr-note">
        원천 앱(CAD · 해석 모델)에서 새 입력이 온 과제 · 차수입니다. 입력이 일정 시간 조용해진 뒤에 준비를 판정합니다.
      </span>
      {err && <ErrorBanner message={err} />}
      {!err && !rows && <Spinner label="감지 목록을 불러오는 중…" />}
      {rows && rows.length === 0 && <p className="pr-note">감지한 과제 · 차수가 없습니다.</p>}
      {rows && rows.length > 0 && (
        <div className="pr-card-scroll">
          <table className="pr-table ap-table ap-subjects">
            <thead>
              <tr>
                <th>과제</th>
                <th>차수</th>
                <th>상태</th>
                <th>막힌 까닭</th>
                <th>마지막 변화</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s, i) => (
                <tr key={`${s.project}-${s.revision}-${i}`}>
                  <td>{s.project ?? '과제 key 없음'}</td>
                  <td>{s.revision ?? '차수 모름'}</td>
                  <td>
                    <Chip map={SUBJECT_STATE} state={s.state} />
                  </td>
                  <td className="ap-wrap">{s.block_reason ? reasonText(s.block_reason) : '—'}</td>
                  <td>{when(s.last_change)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ── 2'. 규칙 편집 — JSON 글상자 · 검증 · 저장(새 규칙 · 새 판) · 켜기/끄기 ──────────
type Issues = { ok?: boolean; errors: Issue[]; warnings: Issue[]; parse?: string };

function RuleEditor() {
  const { id } = useParams();
  const nav = useNavigate();
  const [detail, setDetail] = useState<RuleDetail | null>(null);
  const [text, setText] = useState(id ? '' : RULE_TEMPLATE);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [issues, setIssues] = useState<Issues | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    const d = await getRule(id);
    setDetail(d);
    setText(JSON.stringify(d.version?.spec ?? {}, null, 2));
  }, [id]);
  useEffect(() => {
    setDetail(null);
    setLoadErr(null);
    setIssues(null);
    setMsg(null);
    setText(id ? '' : RULE_TEMPLATE);
    load().catch((e: Error) => setLoadErr(e.message));
  }, [id, load]);

  if (loadErr) return <ErrorBanner message={loadErr} />;
  if (id && !detail) return <Spinner label="규칙을 불러오는 중…" />;

  const parse = (): RuleSpec | undefined => {
    try {
      return JSON.parse(text) as RuleSpec;
    } catch (e) {
      setIssues({ errors: [], warnings: [], parse: (e as Error).message });
      return undefined;
    }
  };

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
    } catch (e) {
      const err = e as AutopipeError;
      setMsg(err.message);
      if (err.errors?.length) setIssues({ ok: false, errors: err.errors, warnings: [] });
    } finally {
      setBusy(false);
    }
  };

  const validate = () => {
    const spec = parse();
    if (spec === undefined) return;
    setIssues(null);
    void run(async () => setIssues(await validateSpec(spec)));
  };

  const save = () => {
    const spec = parse();
    if (spec === undefined) return;
    // 켜진 규칙을 「자동 제출」로 올리는 저장은 켜기와 같은 일이다 — 같은 확인을 거친다
    const toAuto = !!detail?.rule.enabled && spec?.stage === 'auto' && detail.version?.spec?.stage !== 'auto';
    if (toAuto && !window.confirm(AUTO_SAVE_CONFIRM)) return;
    setIssues(null);
    void run(async () => {
      if (!id) {
        const r = await createRule(spec);
        nav(`/procedures/auto/rules/${encodeURIComponent(r.id)}`, { replace: true });
        return;
      }
      const r = await addRuleVersion(id, spec);
      await load();
      setMsg(`판 ${r.version_no} 으로 저장했습니다.`);
    });
  };

  const toggle = () => {
    if (!id || !detail) return;
    const on = !detail.rule.enabled;
    // 확인은 저장된 최신 판의 단계로 판정한다 — 엔진이 도는 것은 글상자가 아니라 그 판이다
    if (on && detail.version?.spec?.stage === 'auto' && !window.confirm(AUTO_ENABLE_CONFIRM)) return;
    void run(async () => {
      await setRuleEnabled(id, on);
      setDetail({ ...detail, rule: { ...detail.rule, enabled: on } });
      setMsg(on ? '켰습니다.' : '껐습니다.');
    });
  };

  const bad = !!issues && (!!issues.parse || issues.errors.length > 0);
  const savedStage = detail?.version?.spec?.stage;

  return (
    <div className="pr-stack">
      <NavLink to="/procedures/auto" className="pr-note">
        ← 자동 파이프라인
      </NavLink>
      {detail && (
        <section className="pr-card pr-card-stack" aria-label="규칙 정보">
          <div className="pr-row">
            <strong className="pr-fg pr-grow">{detail.rule.title || detail.rule.id}</strong>
            <span className={`ap-chip is-${detail.rule.enabled ? 'ok' : 'muted'}`}>{detail.rule.enabled ? '켜짐' : '꺼짐'}</span>
            <button type="button" className={`${detail.rule.enabled ? 'btn-secondary' : 'btn-primary'} pr-btn-sm`} disabled={busy} onClick={toggle}>
              {detail.rule.enabled ? '끄기' : '켜기'}
            </button>
          </div>
          <span className="pr-meta">
            판 {detail.rule.latest_version}
            {savedStage ? ` · ${STAGE[savedStage] ?? savedStage}` : ''}
          </span>
          {detail.versions.length > 0 && (
            <details>
              <summary className="pr-summary pr-note">판 이력 {detail.versions.length}개</summary>
              <ul className="pr-list pr-list-tight pr-mt-1">
                {detail.versions.map((v) => (
                  <li key={v.version_no} className="pr-note">
                    판 {v.version_no}
                    {v.spec?.stage ? ` · ${STAGE[String(v.spec.stage)] ?? v.spec.stage}` : ''} · {v.author ?? '—'} · {when(v.created_at)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
      <section className="pr-card pr-card-stack" aria-label="규칙 편집">
        <strong className="pr-subhead">{id ? '새 판 만들기' : '새 규칙'}</strong>
        <span className="pr-note">
          단계(stage)는 shadow(그림자 — 제출 없이 냈을 것만 기록) · approve(사람이 한 번 승인하면 제출) · auto(자동 제출) 가운데 하나입니다. 단계 목록의
          analysis 는 앱의 프로파일로 해석을 내고, report 는 결과로 보고서(per_analysis · summary · revdiff)를 씁니다. 판은 고치지 않고 저장할 때마다 새
          판이 생깁니다.
        </span>
        <textarea
          className="pr-input pr-mono-sm pr-minh-11 ap-spec"
          aria-label="규칙 스펙 JSON"
          spellCheck={false}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="pr-row">
          <button type="button" className="btn-secondary pr-btn-sm" disabled={busy || !text.trim()} onClick={validate}>
            검증
          </button>
          <button type="button" className="btn-primary pr-btn-sm" disabled={busy || !text.trim()} onClick={save}>
            {id ? '새 판으로 저장' : '저장'}
          </button>
          {msg && (
            <span className="pr-note" role="status">
              {msg}
            </span>
          )}
        </div>
        {issues && (
          <div className={bad ? 'pr-callout ap-issues-bad' : 'pr-callout'} role={bad ? 'alert' : 'status'} aria-label="검증 결과">
            {issues.parse ? (
              <p className="pr-m-0 pr-fs-13 pr-fg">JSON 꼴이 아닙니다 — {issues.parse}</p>
            ) : issues.errors.length > 0 ? (
              <>
                <strong className="pr-fs-13 pr-danger">오류 {issues.errors.length}건 — 이대로는 저장되지 않습니다.</strong>
                <ul className="pr-bullets pr-fs-13 ap-errors">
                  {issues.errors.map((e, i) => (
                    <li key={i}>{issueText(e)}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="pr-m-0 pr-fs-13 pr-ok">검증을 지났습니다.</p>
            )}
            {issues.warnings.length > 0 && (
              <>
                <strong className="pr-fs-13 pr-warn">경고 {issues.warnings.length}건</strong>
                <ul className="pr-bullets pr-fs-13 ap-warnings">
                  {issues.warnings.map((w, i) => (
                    <li key={i}>{issueText(w)}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

// ── 4. 실행 상세 ───────────────────────────────────────────────────────────
function RunView() {
  const { id = '' } = useParams();
  const [d, setD] = useState<RunDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => getRun(id).then(setD), [id]);
  useEffect(() => {
    setD(null);
    setErr(null);
    setMsg(null);
    load().catch((e: Error) => setErr(e.message));
  }, [load]);

  if (err && !d) return <ErrorBanner message={err} />;
  if (!d) return <Spinner label="실행을 불러오는 중…" />;
  const { run, steps, events } = d;

  const act = async (fn: () => Promise<Record<string, unknown>>, done: string) => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const r = await fn();
      // 취소는 도는 단계를 끝까지 둔다고 알릴 수 있다 — 창구가 준 말을 그대로 보인다
      const said = [r.message, r.notice, r.detail].find((x) => typeof x === 'string' && x.trim());
      setMsg((said as string | undefined) ?? done);
      await load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toSubmit = steps.filter((s) => s.kind === 'analysis' && !STEP_ENDED.has(s.state));
  const approve = () => {
    const list = toSubmit.map((s) => `· ${s.step_id}${s.app ? ` — ${s.app}${s.profile ? ` · ${s.profile}` : ''}` : ''}`).join('\n');
    const ok = window.confirm(
      `이 실행의 해석 ${toSubmit.length}개를 클러스터에 제출합니다.\n${list}\n\n과제 ${run.project ?? '—'} · 차수 ${run.revision ?? '—'}.\n승인할까요?`,
    );
    if (ok) void act(() => approveRun(run.id), '승인했습니다. 엔진의 다음 박자에 제출합니다.');
  };
  const cancel = () => {
    const ok = window.confirm(
      '이 실행을 취소합니다.\n아직 내지 않은 단계는 취소되고, 클러스터에서 이미 도는 해석은 앱이 취소를 받지 않으면 끝까지 돕니다.\n취소할까요?',
    );
    if (ok) void act(() => cancelRun(run.id), '취소했습니다.');
  };

  return (
    <div className="pr-stack">
      <NavLink to="/procedures/auto" className="pr-note">
        ← 자동 파이프라인
      </NavLink>
      <section className={`pr-card pr-card-stack${run.state === 'awaiting_approval' ? ' pr-card-warn' : ''}`} aria-label="실행">
        <div className="pr-row">
          <strong className="pr-fg pr-grow">
            {run.project ?? '과제 key 없음'} · {run.revision ?? '차수 모름'}
          </strong>
          <Chip map={RUN_STATE} state={run.state} />
        </div>
        <span className="pr-meta">
          규칙{' '}
          <NavLink to={`/procedures/auto/rules/${encodeURIComponent(run.rule_id)}`} className="pr-link">
            {run.rule_title || run.rule_id}
          </NavLink>
          {run.version_no != null ? ` 판 ${run.version_no}` : ''}
          {run.stage ? ` · ${STAGE[run.stage] ?? run.stage}` : ''} · 만든 때 {when(run.created_at)}
          {run.ended_at ? ` · 끝난 때 ${when(run.ended_at)}` : ''}
        </span>
        {run.fingerprint && (
          <span className="pr-note">
            입력 지문 <span className="pr-mono-sm">{run.fingerprint.slice(0, 16)}</span>
          </span>
        )}
        {run.reason && <span className="pr-note">까닭 — {run.reason}</span>}
        {(run.state === 'superseded' || run.superseded_by) && (
          <p className="pr-callout pr-m-0 pr-fs-13 ap-superseded-note">
            대체됨 — 같은 과제의 뒤 차수가 와서 이 실행을 대신합니다. 클러스터에서 돌던 해석은 끝까지 두고, 아직 내지 않은 단계는 취소했습니다.
            {run.superseded_by && (
              <>
                {' '}
                <NavLink to={`/procedures/auto/runs/${encodeURIComponent(run.superseded_by)}`} className="pr-link">
                  뒤 실행 보기
                </NavLink>
              </>
            )}
          </p>
        )}
        {run.state === 'awaiting_approval' && (
          <p className="pr-callout pr-m-0 pr-fs-13">
            승인을 기다립니다. 해석마다 입력 확인을 지났습니다. 「제출 승인」을 누르면 해석을 클러스터에 냅니다.
          </p>
        )}
        {run.state === 'planned' && <span className="pr-note">그림자 실행입니다. 제출하지 않고 냈을 것만 기록했습니다.</span>}
        <div className="pr-row">
          {run.state === 'awaiting_approval' && (
            <button type="button" className="btn-primary pr-btn-sm" disabled={busy} onClick={approve}>
              제출 승인
            </button>
          )}
          {!RUN_ENDED.has(run.state) && (
            <button type="button" className="btn-secondary pr-btn-sm" disabled={busy} onClick={cancel}>
              취소
            </button>
          )}
          <button type="button" className="btn-secondary pr-btn-sm" disabled={busy} onClick={() => void load().catch((e: Error) => setErr(e.message))}>
            새로 고침
          </button>
          {msg && (
            <span className="pr-note" role="status">
              {msg}
            </span>
          )}
        </div>
        {err && <ErrorBanner message={err} />}
      </section>

      <section className="pr-card-stack" aria-label="단계">
        <h3 className="pr-h3">단계</h3>
        <ol className="pr-list">
          {steps.map((s) => (
            <StepCard key={s.step_id} runId={run.id} step={s} />
          ))}
          {steps.length === 0 && <li className="pr-note">아직 단계가 없습니다.</li>}
        </ol>
      </section>

      <section className="pr-card-stack" aria-label="이벤트">
        <h3 className="pr-h3">이벤트</h3>
        {events.length === 0 && <p className="pr-note">이벤트가 없습니다.</p>}
        <ol className="pr-list pr-list-tight ap-events">
          {events.map((e, i) => (
            <li key={e.id ?? i} className="pr-fs-13">
              <span className="pr-meta">{when(e.at)}</span> <span className="pr-mono-sm pr-fg">{e.kind}</span>
              {e.detail != null && <span className="pr-meta"> {typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail).slice(0, 300)}</span>}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function StepCard({ runId, step }: { runId: string; step: RunStep }) {
  const tone: Tone = STEP_STATE[step.state]?.[1] ?? 'muted';
  const [md, setMd] = useState<string | null>(null);
  const [mdErr, setMdErr] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const verdict = step.verdict ?? step.result?.verdict;

  const showReport = () => {
    if (open) return setOpen(false);
    setOpen(true);
    if (md !== null) return;
    setMdErr(null);
    getRunReport(runId, step.step_id).then(setMd, (e: Error) => setMdErr(e.message));
  };

  return (
    <li className={`pr-step ap-step is-${tone}`} data-step={step.step_id}>
      <div className="pr-head">
        <strong className="pr-fg">{step.step_id}</strong>
        <span className="pr-meta">{stepWhat(step)}</span>
        <Chip map={STEP_STATE} state={step.state} />
        <VerdictTag v={verdict} />
      </div>
      {(step.started_at || step.ended_at || step.run_ref) && (
        <span className="pr-note">
          {step.started_at ? `시작 ${when(step.started_at)}` : ''}
          {step.ended_at ? `${step.started_at ? ' · ' : ''}끝 ${when(step.ended_at)}` : ''}
          {step.run_ref ? `${step.started_at || step.ended_at ? ' · ' : ''}앱 쪽 실행 ${step.run_ref}` : ''}
        </span>
      )}
      {step.error && <p className="pr-m-0 pr-mt-1 pr-fs-13 pr-danger">{step.error}</p>}
      {step.check && <CheckView check={step.check} />}
      {step.result && <EnvelopeView env={step.result} />}
      {step.kind === 'report' && step.state === 'done' && (
        <div className="pr-mt-2">
          <button type="button" className="btn-secondary pr-btn-sm" onClick={showReport}>
            {open ? '보고서 접기' : '보고서 보기'}
          </button>
          {open && (
            <div className="ap-report pr-mt-2">
              {mdErr ? (
                <ErrorBanner message={mdErr} />
              ) : md === null ? (
                <Spinner label="보고서를 불러오는 중…" />
              ) : md.trim() ? (
                <TextBlock text={md} />
              ) : (
                <p className="pr-note pr-m-0">보고서가 비어 있습니다.</p>
              )}
            </div>
          )}
        </div>
      )}
      {step.ra_report_id != null && step.ra_report_id !== '' && (
        <span className="pr-note">RA 에 게시했습니다(보고서 {String(step.ra_report_id)}).</span>
      )}
    </li>
  );
}

/** 입력 확인(auto_check) — 갖췄는지 · 빠진 것(종류 · 까닭) · 이번 입력 */
function CheckView({ check }: { check: CheckResult }) {
  const missing = check.missing ?? [];
  const inputs = check.inputs ?? [];
  return (
    <div className="pr-mt-2 ap-check">
      <span className="pr-label">입력 확인 — {check.ready ? '갖춤' : '안 갖춤'}</span>
      {missing.length > 0 && (
        <ul className="pr-bullets pr-fs-13 ap-missing">
          {missing.map((m, i) => (
            <li key={i}>
              {reasonText(m.kind)}
              {m.why ? ` — ${m.why}` : ''}
            </li>
          ))}
        </ul>
      )}
      {inputs.length > 0 && (
        <details>
          <summary className="pr-summary pr-note">입력 {inputs.length}개</summary>
          <ul className="pr-list pr-list-tight pr-mt-1">
            {inputs.map((x, i) => (
              <li key={i} className="pr-note">
                {x.kind ?? '—'} · {x.ref ?? '—'}
                {x.sha256 && <span className="pr-mono-sm"> · {x.sha256.slice(0, 12)}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

/** 결과 봉투(contract §2 auto_result) — 판정 · 수치 표 · 그림 캡션 · 원자료 · notes */
function EnvelopeView({ env }: { env: Envelope }) {
  const metrics = env.metrics ?? [];
  const figures = env.figures ?? [];
  const artifacts = env.artifacts ?? [];
  const notes = env.notes ?? [];
  return (
    <div className="pr-mt-2 pr-card-stack ap-env">
      <div className="pr-row">
        <span className="pr-label">결과</span>
        <VerdictTag v={env.verdict} />
        <span className="pr-note">
          {env.profile ? `프로파일 ${env.profile}` : ''}
          {env.app_version ? ` · 앱 판 ${env.app_version}` : ''}
          {env.finished_at ? ` · 끝난 때 ${when(env.finished_at)}` : ''}
        </span>
      </div>
      {metrics.length > 0 && (
        <div className="pr-card-scroll">
          <table className="pr-table ap-table ap-metrics">
            <thead>
              <tr>
                <th>항목</th>
                <th>값</th>
                <th>단위</th>
                <th>기준</th>
                <th>판정</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m, i) => (
                <tr key={`${m.name}-${i}`}>
                  <td title={m.name}>{m.label || m.name}</td>
                  <td>{m.value ?? '—'}</td>
                  <td>{m.unit || '—'}</td>
                  <td className="ap-wrap">
                    {m.limit ?? '—'}
                    {m.limit_source && <span className="pr-note"> ({m.limit_source})</span>}
                  </td>
                  <td>
                    <VerdictTag v={m.verdict} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {figures.length > 0 && (
        <ul className="pr-list pr-list-tight" aria-label="그림">
          {figures.map((f, i) => (
            <li key={i} className="pr-fs-13">
              그림 — {f.caption || '(설명 없음)'}
              {f.ref && <span className="pr-note pr-mono-sm"> {f.ref}</span>}
            </li>
          ))}
        </ul>
      )}
      {artifacts.length > 0 && (
        <ul className="pr-list pr-list-tight" aria-label="원자료">
          {artifacts.map((a, i) => (
            <li key={i} className="pr-note">
              원자료 {a.kind ?? '—'} · {a.location ?? '—'}
            </li>
          ))}
        </ul>
      )}
      {notes.length > 0 && (
        <ul className="pr-bullets pr-fs-13" aria-label="메모">
          {notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
