// 분석 루틴 — 목록 · 보기(준비도) · 편집기. 내 권한의 플랫폼을 순서대로 놓고 단계마다 할 일을 적는다(docs/analysis-routines, R1)
import { useCallback, useEffect, useMemo, useState } from 'react';
import { NavLink, useNavigate, useParams } from 'react-router-dom';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import {
  addRoutineVersion,
  archiveRoutine,
  createRoutine,
  exportRoutineUrl,
  getRoutine,
  importRoutineYaml,
  listRoutines,
  routinePlatforms,
  routineReadiness,
  type Platforms,
  type RoutineDetail,
  type RoutineRow,
  type RoutineSpec,
  type RoutineStep,
  type StepKind,
  type StepReadiness,
} from '../../api/routines.api';
// 준비도 라벨 · 사슬 글은 챗의 루틴 고르기와 함께 쓴다(R3) — 화면 조각 밖(.ts)에 둔다
import { READY_LABEL, chain } from '../../components/chat/routine';

const KIND_LABEL: Record<StepKind, string> = { platform: '플랫폼', cite: '기존 보고서 인용', deliberation: '전문가 심의' };
const UPLOAD_LABEL = { auto: '저절로 초안을 만든다', ask: '끝에 묻는다', off: '올리지 않는다' } as const;

function blankStep(n: number): RoutineStep {
  return {
    id: `s${n}`,
    title: '',
    kind: 'platform',
    backends: [],
    goal: '',
    tools: [],
    uses: [],
    expect: { keys: [] },
    budget: { calls: 8, seconds: 300 },
    blocked: { empty: 'continue', denied: 'skip', unavailable: 'skip' },
  };
}

function blankSpec(): RoutineSpec {
  return {
    title: '',
    purpose: '',
    vars: [],
    steps: [blankStep(1)],
    report: { title: '', sections: [], ra: { upload: 'auto' } },
    limits: { minutes: 60, calls: 60 },
    visibility: 'private',
  };
}

// ── 목록 ───────────────────────────────────────────────────────────────
export function RoutineList() {
  const [rows, setRows] = useState<RoutineRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const reload = useCallback(() => {
    listRoutines()
      .then((r) => setRows(r.routines))
      .catch((e: Error) => setErr(e.message));
  }, []);
  useEffect(() => reload(), [reload]);

  if (err) return <ErrorBanner message={err} />;
  if (!rows) return <Spinner label="루틴을 불러오는 중…" />;
  return (
    <div className="pr-stack">
      <div className="pr-row">
        <span className="pr-note pr-grow">
          내 권한의 플랫폼을 순서대로 엮어 둡니다. 챗에서 골라 켜거나 개인 Claude 가 MCP 로 부르면 그 연쇄로 분석해 보고서를 씁니다.
        </span>
        <NavLink to="/procedures/routines/new" className="btn-primary pr-btn-sm">
          새 루틴
        </NavLink>
      </div>
      {rows.length === 0 && <p className="pr-note">아직 루틴이 없습니다.</p>}
      <ul className="pr-list">
        {rows.map((r) => (
          <li key={r.id} className="pr-card">
            <div className="pr-col">
              <NavLink to={`/procedures/routines/${r.id}`} className="pr-link pr-strong">
                {r.title}
              </NavLink>
              <span className="pr-meta rt-chain">{chain(r.steps)}</span>
            </div>
            <span className="pr-meta">
              판 {r.latest_version} · {r.visibility === 'all' ? '모두에게 공개' : '나만'}
              {!r.mine && ' · 공유받음'}
            </span>
          </li>
        ))}
      </ul>
      <RoutineYamlImport onImported={reload} />
    </div>
  );
}

function RoutineYamlImport({ onImported }: { onImported: () => void }) {
  const [text, setText] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <section className="pr-card pr-card-stack">
      <strong className="pr-subhead">YAML 가져오기</strong>
      <span className="pr-note">
        내보낸 루틴 YAML 을 붙여 넣으면 <b>내 새 루틴</b>이 됩니다. 남의 루틴을 고치는 길이 이것입니다(판은 주인만 더합니다).
      </span>
      <textarea
        id="rt-import"
        className="pr-input pr-mono-sm pr-minh-5"
        spellCheck={false}
        placeholder="title: …"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="pr-row">
        <button
          type="button"
          className="btn-secondary pr-btn-sm"
          disabled={busy || !text.trim()}
          onClick={async () => {
            setBusy(true);
            setMsg(null);
            try {
              await importRoutineYaml(text.trim());
              setText('');
              setMsg('가져왔습니다.');
              onImported();
            } catch (e) {
              setMsg((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? '가져오는 중…' : '가져오기'}
        </button>
        {msg && <span className="pr-note">{msg}</span>}
      </div>
    </section>
  );
}

// ── 보기 ───────────────────────────────────────────────────────────────
export function RoutineDetailView() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [d, setD] = useState<RoutineDetail | null>(null);
  const [ready, setReady] = useState<StepReadiness[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [version, setVersion] = useState<number | undefined>(undefined);

  const load = useCallback(() => {
    setErr(null);
    getRoutine(id, version)
      .then((r) => {
        setD(r);
        return routineReadiness(id, r.version.version_no);
      })
      .then((r) => setReady(r.steps))
      .catch((e: Error) => setErr(e.message));
  }, [id, version]);
  useEffect(() => load(), [load]);

  if (err && !d) return <ErrorBanner message={err} />;
  if (!d) return <Spinner label="루틴을 불러오는 중…" />;
  const spec = d.version.spec;
  if (editing)
    return (
      <RoutineEditor
        initial={spec}
        onSaved={() => {
          setEditing(false);
          setVersion(undefined);
          load();
        }}
        onCancel={() => setEditing(false)}
        save={(s) => addRoutineVersion(id, s)}
      />
    );
  const byStep = new Map((ready ?? []).map((r) => [r.step, r]));
  return (
    <div className="pr-stack">
      {err && <ErrorBanner message={err} />}
      <div className="pr-head">
        <strong className="pr-subhead pr-grow">{spec.title}</strong>
        <select
          id="rt-version"
          value={d.version.version_no}
          onChange={(e) => setVersion(Number(e.target.value))}
          aria-label="판"
        >
          {d.versions.map((v) => (
            <option key={v.version_no} value={v.version_no}>
              판 {v.version_no}
            </option>
          ))}
        </select>
        {d.mine && (
          <button type="button" className="btn-primary pr-btn-sm" onClick={() => setEditing(true)}>
            고치기(새 판)
          </button>
        )}
        <a href={exportRoutineUrl(id, d.version.version_no)} className="btn-secondary pr-btn-sm">
          YAML 내보내기
        </a>
        {d.mine && (
          <button
            type="button"
            className="btn-secondary pr-btn-sm"
            onClick={async () => {
              if (!window.confirm('이 루틴을 보관할까요? 목록에서 빠지고 실행 기록은 남습니다.')) return;
              try {
                await archiveRoutine(id);
                navigate('/procedures/routines');
              } catch (e) {
                setErr((e as Error).message);
              }
            }}
          >
            보관
          </button>
        )}
      </div>
      {spec.purpose && <p className="pr-note">{spec.purpose}</p>}
      {spec.vars.length > 0 && (
        <p className="pr-meta">입력 — {spec.vars.map((v) => `${v.label}(${v.key})`).join(' · ')}</p>
      )}
      <ol className="pr-list">
        {spec.steps.map((s, i) => {
          const r = byStep.get(s.id);
          return (
            <li key={s.id} className="pr-step rt-step-view">
              <div className="pr-head">
                <strong>
                  {i + 1}. {s.title}
                </strong>
                <span className="pr-meta">
                  {KIND_LABEL[s.kind]}
                  {s.backends.length > 0 && ` · ${s.backends.join(', ')}`} · id {s.id}
                </span>
                {r && <span className={`rt-ready is-${r.state}`}>{READY_LABEL[r.state]}</span>}
              </div>
              <p className="pr-note rt-goal">{s.goal}</p>
              {r && r.reason && <p className="pr-meta">{r.reason}</p>}
              {r && r.missing_tools.length > 0 && (
                <p className="pr-meta">이 박스 목록에 없는 도구 — {r.missing_tools.join(', ')}</p>
              )}
            </li>
          );
        })}
      </ol>
      <p className="pr-meta">
        보고서 — 「{spec.report.title || spec.title}」 · 절 {spec.report.sections.join(' → ')} · Report Archive{' '}
        {UPLOAD_LABEL[spec.report.ra.upload]} · {spec.visibility === 'all' ? '모두에게 공개' : '나만'} · 상한{' '}
        {spec.limits.minutes}분 · 호출 {spec.limits.calls}번
      </p>
      <p className="pr-note">
        막힌 단계(권한 없음 · 토큰 없음 · 이 박스에 없음 · 결과 없음)는 건너뛰고 보고서에 사유를 적습니다. 실행은 챗 · 개인 Claude
        에서 합니다.
      </p>
    </div>
  );
}

export function RoutineNew() {
  const navigate = useNavigate();
  return (
    <RoutineEditor
      initial={blankSpec()}
      save={createRoutine}
      onSaved={(id) => navigate(`/procedures/routines/${id}`)}
      onCancel={() => navigate('/procedures/routines')}
    />
  );
}

// ── 편집기 ─────────────────────────────────────────────────────────────
function RoutineEditor({
  initial,
  save,
  onSaved,
  onCancel,
}: {
  initial: RoutineSpec;
  save: (s: RoutineSpec) => Promise<{ id: string }>;
  onSaved: (id: string) => void;
  onCancel: () => void;
}) {
  const [spec, setSpec] = useState<RoutineSpec>(initial);
  const [plats, setPlats] = useState<Platforms | null>(null);
  const [platErr, setPlatErr] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    routinePlatforms()
      .then(setPlats)
      .catch((e: Error) => setPlatErr(e.message));
  }, []);
  const labelOf = useMemo(
    () => new Map((plats?.platforms ?? []).map((p) => [p.backend, p.label])),
    [plats],
  );

  const patch = (p: Partial<RoutineSpec>) => setSpec((s) => ({ ...s, ...p }));
  const setStep = (i: number, p: Partial<RoutineStep>) =>
    setSpec((s) => ({ ...s, steps: s.steps.map((x, j) => (j === i ? { ...x, ...p } : x)) }));
  const moveStep = (i: number, d: -1 | 1) =>
    setSpec((s) => {
      const steps = [...s.steps];
      const j = i + d;
      if (j < 0 || j >= steps.length) return s;
      [steps[i], steps[j]] = [steps[j], steps[i]];
      // 앞 단계만 가리킬 수 있다 — 자리를 바꾸면 뒤로 간 단계를 가리키던 uses 를 뗀다
      const ids = steps.map((x) => x.id);
      return { ...s, steps: steps.map((x, k) => ({ ...x, uses: x.uses.filter((u) => ids.indexOf(u) < k) })) };
    });
  const removeStep = (i: number) =>
    setSpec((s) => {
      const gone = s.steps[i].id;
      return { ...s, steps: s.steps.filter((_, j) => j !== i).map((x) => ({ ...x, uses: x.uses.filter((u) => u !== gone) })) };
    });
  const addStep = () =>
    setSpec((s) => {
      const used = new Set(s.steps.map((x) => x.id));
      let n = s.steps.length + 1;
      while (used.has(`s${n}`)) n += 1;
      return { ...s, steps: [...s.steps, blankStep(n)] };
    });

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      // 절은 비워 보내면 서버가 '단계 차례 + 인사이트' 로 채운다 — 단계를 지우거나 바꾼 뒤의 옛 절 목록이 남지 않게 늘 다시 맞춘다
      const ids = new Set(spec.steps.map((s) => s.id));
      const sections = spec.report.sections.filter((x) => ids.has(x) || x === 'insight' || x === 'cite');
      const steps = spec.steps.map((s) => ({ ...s, label: s.backends.map((b) => labelOf.get(b) ?? b).join(' · ') }));
      const got = await save({ ...spec, steps, report: { ...spec.report, sections } });
      onSaved(got.id);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="pr-stack">
      {err && <ErrorBanner message={err} />}
      <section className="pr-panel pr-form">
        <div className="pr-field">
          <label htmlFor="rt-title" className="pr-label">
            루틴 이름
          </label>
          <input
            id="rt-title"
            className="pr-input"
            value={spec.title}
            maxLength={120}
            onChange={(e) => patch({ title: e.target.value })}
          />
        </div>
        <div className="pr-field">
          <label htmlFor="rt-purpose" className="pr-label">
            목적(질문의 틀 — {'{{변수}}'} 를 쓸 수 있습니다)
          </label>
          <textarea
            id="rt-purpose"
            className="pr-input"
            rows={2}
            value={spec.purpose}
            maxLength={2000}
            onChange={(e) => patch({ purpose: e.target.value })}
          />
        </div>
        <VarsEditor vars={spec.vars} onChange={(vars) => patch({ vars })} />
      </section>

      {platErr && <ErrorBanner message={`고를 수 있는 플랫폼을 못 받았습니다 — ${platErr}`} />}
      {!plats && !platErr && <Spinner label="내 권한의 플랫폼을 불러오는 중…" />}
      <ol className="pr-list">
        {spec.steps.map((s, i) => (
          <li key={i} className="pr-panel rt-step-edit">
            <StepEditor
              step={s}
              index={i}
              earlier={spec.steps.slice(0, i)}
              plats={plats}
              onChange={(p) => setStep(i, p)}
              onMove={(d) => moveStep(i, d)}
              onRemove={spec.steps.length > 1 ? () => removeStep(i) : undefined}
            />
          </li>
        ))}
      </ol>
      <div className="pr-row">
        <button type="button" className="btn-secondary pr-btn-sm" onClick={addStep} disabled={spec.steps.length >= 12}>
          단계 더하기
        </button>
        <span className="pr-meta">단계는 12개까지입니다.</span>
      </div>

      <section className="pr-panel pr-form">
        <strong className="pr-subhead">보고서</strong>
        <div className="pr-field">
          <label htmlFor="rt-report-title" className="pr-label">
            보고서 제목(비우면 루틴 이름)
          </label>
          <input
            id="rt-report-title"
            className="pr-input"
            value={spec.report.title}
            maxLength={200}
            onChange={(e) => patch({ report: { ...spec.report, title: e.target.value } })}
          />
        </div>
        <div className="pr-row">
          <label htmlFor="rt-upload" className="pr-label">
            Report Archive
          </label>
          <select
            id="rt-upload"
            value={spec.report.ra.upload}
            onChange={(e) =>
              patch({ report: { ...spec.report, ra: { upload: e.target.value as RoutineSpec['report']['ra']['upload'] } } })
            }
          >
            {(Object.keys(UPLOAD_LABEL) as (keyof typeof UPLOAD_LABEL)[]).map((k) => (
              <option key={k} value={k}>
                {UPLOAD_LABEL[k]}
              </option>
            ))}
          </select>
          <label htmlFor="rt-visibility" className="pr-label">
            공개
          </label>
          <select
            id="rt-visibility"
            value={spec.visibility}
            onChange={(e) => patch({ visibility: e.target.value as RoutineSpec['visibility'] })}
          >
            <option value="private">나만</option>
            <option value="all">모두(실행은 각자 권한으로)</option>
          </select>
          <label htmlFor="rt-minutes" className="pr-label">
            상한(분)
          </label>
          <input
            id="rt-minutes"
            type="number"
            className="pr-input pr-input-sm"
            min={5}
            max={240}
            value={spec.limits.minutes}
            onChange={(e) => patch({ limits: { ...spec.limits, minutes: Number(e.target.value) } })}
          />
          <label htmlFor="rt-calls" className="pr-label">
            호출 상한
          </label>
          <input
            id="rt-calls"
            type="number"
            className="pr-input pr-input-sm"
            min={1}
            max={200}
            value={spec.limits.calls}
            onChange={(e) => patch({ limits: { ...spec.limits, calls: Number(e.target.value) } })}
          />
        </div>
        <span className="pr-note">
          절은 단계 차례에 인사이트를 더한 것입니다. 게시는 늘 사람이 Report Archive 에서 합니다.
        </span>
      </section>

      <div className="pr-row">
        <button
          type="button"
          className="btn-primary"
          disabled={busy || !spec.title.trim() || spec.steps.some((s) => !s.title.trim() || !s.goal.trim())}
          onClick={submit}
        >
          {busy ? '저장 중…' : '저장'}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          취소
        </button>
      </div>
    </div>
  );
}

function VarsEditor({ vars, onChange }: { vars: RoutineSpec['vars']; onChange: (v: RoutineSpec['vars']) => void }) {
  return (
    <div className="pr-field">
      <span className="pr-label">입력(실행할 때 묻는 값 — 할 일에서 {'{{키}}'} 로 씁니다)</span>
      {vars.map((v, i) => (
        <div key={i} className="pr-row">
          <input
            id={`rt-var-key-${i}`}
            className="pr-input pr-input-sm pr-mono"
            placeholder="키(소문자 · 밑줄)"
            value={v.key}
            onChange={(e) => onChange(vars.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))}
          />
          <input
            id={`rt-var-label-${i}`}
            className="pr-input pr-input-sm"
            placeholder="이름(예: 모델)"
            value={v.label}
            onChange={(e) => onChange(vars.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))}
          />
          <button type="button" className="btn-secondary pr-btn-xs" onClick={() => onChange(vars.filter((_, j) => j !== i))}>
            빼기
          </button>
        </div>
      ))}
      <div>
        <button
          type="button"
          className="btn-secondary pr-btn-sm"
          disabled={vars.length >= 12}
          onClick={() => onChange([...vars, { key: '', label: '' }])}
        >
          입력 더하기
        </button>
      </div>
    </div>
  );
}

function StepEditor({
  step,
  index,
  earlier,
  plats,
  onChange,
  onMove,
  onRemove,
}: {
  step: RoutineStep;
  index: number;
  earlier: RoutineStep[];
  plats: Platforms | null;
  onChange: (p: Partial<RoutineStep>) => void;
  onMove: (d: -1 | 1) => void;
  onRemove?: () => void;
}) {
  const fid = `rt-s${index}`;
  const chosen = new Set(step.backends);
  const tools = (plats?.platforms ?? []).filter((p) => chosen.has(p.backend)).flatMap((p) => p.tools.filter((t) => !t.write));
  const known = new Set((plats?.platforms ?? []).map((p) => p.backend));
  const setKind = (kind: StepKind) =>
    onChange(kind === 'deliberation' ? { kind, backends: [], tools: [], deliberation: { job: 'mechanism' } } : { kind, deliberation: null });
  return (
    <div className="pr-form">
      <div className="pr-head">
        <strong className="pr-grow">단계 {index + 1}</strong>
        <button type="button" className="btn-secondary pr-btn-xs" onClick={() => onMove(-1)} disabled={index === 0}>
          위로
        </button>
        <button type="button" className="btn-secondary pr-btn-xs" onClick={() => onMove(1)}>
          아래로
        </button>
        {onRemove && (
          <button type="button" className="btn-secondary pr-btn-xs" onClick={onRemove}>
            빼기
          </button>
        )}
      </div>
      <div className="pr-row">
        <label htmlFor={`${fid}-title`} className="pr-label">
          제목(보고서의 절 이름)
        </label>
        <input
          id={`${fid}-title`}
          className="pr-input pr-grow"
          value={step.title}
          maxLength={80}
          onChange={(e) => onChange({ title: e.target.value })}
        />
        <label htmlFor={`${fid}-id`} className="pr-label">
          id
        </label>
        <input
          id={`${fid}-id`}
          className="pr-input pr-input-sm pr-mono"
          value={step.id}
          maxLength={24}
          onChange={(e) => onChange({ id: e.target.value })}
        />
        <label htmlFor={`${fid}-kind`} className="pr-label">
          종류
        </label>
        <select id={`${fid}-kind`} value={step.kind} onChange={(e) => setKind(e.target.value as StepKind)}>
          {(Object.keys(KIND_LABEL) as StepKind[]).map((k) => (
            <option key={k} value={k} disabled={k === 'deliberation' && plats !== null && !plats.deliberation}>
              {KIND_LABEL[k]}
            </option>
          ))}
        </select>
      </div>
      {step.kind !== 'deliberation' && (
        <div className="pr-field">
          <span className="pr-label">플랫폼(이 단계의 울타리 — 3개까지, 내 권한 안의 것만 보입니다)</span>
          <div className="pr-wrap">
            {step.backends.map((b) => (
              <span key={b} className="rt-chip">
                {plats?.platforms.find((p) => p.backend === b)?.label ?? b}
                {!known.has(b) && plats && ' (이 박스 목록에 없음)'}
                <button
                  type="button"
                  className="pr-link-btn"
                  aria-label={`${b} 빼기`}
                  onClick={() => onChange({ backends: step.backends.filter((x) => x !== b), tools: [] })}
                >
                  ×
                </button>
              </span>
            ))}
            {step.backends.length < 3 && (
              <select
                id={`${fid}-add`}
                value=""
                aria-label="플랫폼 더하기"
                onChange={(e) => e.target.value && onChange({ backends: [...step.backends, e.target.value] })}
              >
                <option value="">플랫폼 고르기…</option>
                {(plats?.platforms ?? [])
                  .filter((p) => !chosen.has(p.backend))
                  .map((p) => (
                    <option key={p.backend} value={p.backend}>
                      {p.label} ({p.tools.filter((t) => !t.write).length})
                    </option>
                  ))}
              </select>
            )}
          </div>
          {tools.length > 0 && (
            <details>
              <summary className="pr-meta">
                도구 고르기(선택 — 안 고르면 그 플랫폼의 읽기 도구 전부, 고른 것 {step.tools.length}개)
              </summary>
              <div className="pr-wrap rt-tools">
                {tools.map((t) => (
                  <label key={t.name} className="pr-check" title={t.description}>
                    <input
                      type="checkbox"
                      checked={step.tools.includes(t.name)}
                      disabled={!step.tools.includes(t.name) && step.tools.length >= 12}
                      onChange={(e) =>
                        onChange({
                          tools: e.target.checked ? [...step.tools, t.name] : step.tools.filter((x) => x !== t.name),
                        })
                      }
                    />{' '}
                    <code>{t.name}</code>
                  </label>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
      <div className="pr-field">
        <label htmlFor={`${fid}-goal`} className="pr-label">
          할 일 — {'{{키}}'} · {'{{steps.<id>.<키>}}'} 를 쓸 수 있습니다
        </label>
        <textarea
          id={`${fid}-goal`}
          className="pr-input"
          rows={3}
          maxLength={2000}
          value={step.goal}
          onChange={(e) => onChange({ goal: e.target.value })}
        />
      </div>
      {earlier.length > 0 && (
        <div className="pr-row">
          <span className="pr-label">앞 단계 결과 쓰기</span>
          {earlier.map((p) => (
            <label key={p.id} className="pr-check">
              <input
                type="checkbox"
                checked={step.uses.includes(p.id)}
                onChange={(e) =>
                  onChange({ uses: e.target.checked ? [...step.uses, p.id] : step.uses.filter((u) => u !== p.id) })
                }
              />{' '}
              {p.title || p.id}
            </label>
          ))}
        </div>
      )}
      <div className="pr-row">
        <label htmlFor={`${fid}-keys`} className="pr-label">
          다음 단계에 넘길 키
        </label>
        <input
          id={`${fid}-keys`}
          className="pr-input pr-input-sm pr-mono"
          placeholder="예: model_key, task_code"
          value={step.expect.keys.join(', ')}
          onChange={(e) =>
            onChange({ expect: { ...step.expect, keys: e.target.value.split(/[\s,]+/).filter(Boolean) } })
          }
        />
        <label htmlFor={`${fid}-calls`} className="pr-label">
          호출
        </label>
        <input
          id={`${fid}-calls`}
          type="number"
          className="pr-input pr-input-sm"
          min={1}
          max={30}
          value={step.budget.calls}
          onChange={(e) => onChange({ budget: { ...step.budget, calls: Number(e.target.value) } })}
        />
        <label htmlFor={`${fid}-secs`} className="pr-label">
          초
        </label>
        <input
          id={`${fid}-secs`}
          type="number"
          className="pr-input pr-input-sm"
          min={30}
          max={1800}
          value={step.budget.seconds}
          onChange={(e) => onChange({ budget: { ...step.budget, seconds: Number(e.target.value) } })}
        />
      </div>
      <div className="pr-row">
        <span className="pr-label">막히면</span>
        <label htmlFor={`${fid}-empty`} className="pr-meta">
          결과 없음
        </label>
        <select
          id={`${fid}-empty`}
          value={step.blocked.empty}
          onChange={(e) => onChange({ blocked: { ...step.blocked, empty: e.target.value as RoutineStep['blocked']['empty'] } })}
        >
          <option value="continue">계속</option>
          <option value="stop">멈춤</option>
        </select>
        <label htmlFor={`${fid}-denied`} className="pr-meta">
          권한 · 토큰 없음
        </label>
        <select
          id={`${fid}-denied`}
          value={step.blocked.denied}
          onChange={(e) => onChange({ blocked: { ...step.blocked, denied: e.target.value as RoutineStep['blocked']['denied'] } })}
        >
          <option value="skip">건너뜀</option>
          <option value="stop">멈춤</option>
        </select>
        <label htmlFor={`${fid}-unavail`} className="pr-meta">
          이 박스에 없음
        </label>
        <select
          id={`${fid}-unavail`}
          value={step.blocked.unavailable}
          onChange={(e) =>
            onChange({ blocked: { ...step.blocked, unavailable: e.target.value as RoutineStep['blocked']['unavailable'] } })
          }
        >
          <option value="skip">건너뜀</option>
          <option value="stop">멈춤</option>
        </select>
      </div>
    </div>
  );
}
