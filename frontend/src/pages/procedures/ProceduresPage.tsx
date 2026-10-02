// 절차 셸 — 탭 셋(만들기·절차·실행 이력)과 자식 라우트
//
// 루트는 `.container` 다 — AppShell 의 ChatDock 이 열릴 때 자리를 비켜 주는 클래스다.
// 우하단은 비워 둔다(닫힌 독의 💬 FAB 가 거기 고정이라 겹친다).
import { NavLink, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { ChangelogBold as Bold } from '../../components/layout/ChangelogBold';
import { Page, PageHeader } from '../../components/ui/Page';
import { useCallback, useEffect, useState } from 'react';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { useProcedures } from '../../state/ProceduresContext';
import {
  cancelRun,
  getProcedure,
  draftGap,
  exportProcedureUrl,
  getBatch,
  getProcedureTool,
  getRunDraft,
  importProcedureYaml,
  importSeed,
  listSeeds,
  replayRun,
  saveDraft,
  listProcedures,
  listRuns,
  replayProcedure,
  resumeRun,
  type ProcedureRow,
  type BatchTable,
  type ProcedureTool,
  type ProcedureVersion,
  type RunDraft,
  type RunSummary,
  type SeedRow,
} from '../../api/procedures.api';
import BuildView from './BuildView';
import { RunSteps } from './RunSteps';
import '../../styles/procedures.css';

export default function ProceduresPage() {
  return (
    <Page width="wide">
      <PageHeader title="절차" desc="한 번 해낸 일을 절차로 굳혀 두었다가, 대상만 바꿔 다시 돌립니다." />

      <nav className="pr-tabs">
        <Tab to="/procedures" end>
          만들기
        </Tab>
        <Tab to="/procedures/saved">절차</Tab>
        <Tab to="/procedures/runs">실행 이력</Tab>
      </nav>

      <Routes>
        <Route index element={<BuildView />} />
        <Route path="saved" element={<ProcedureList />} />
        <Route path="saved/:id" element={<ProcedureDetail />} />
        <Route path="runs" element={<RunList />} />
        <Route path="runs/:id" element={<RunDetailView />} />
        <Route path="batches/:id" element={<BatchView />} />
      </Routes>
    </Page>
  );
}

function Tab({ to, end, children }: { to: string; end?: boolean; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={end}
      className="pr-tab"
    >
      {children}
    </NavLink>
  );
}

// ── 절차 ───────────────────────────────────────────────────────────────
function ProcedureList() {
  const [rows, setRows] = useState<ProcedureRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(() => {
    listProcedures()
      .then((r) => setRows(r.procedures))
      .catch((e: Error) => setErr(e.message));
  }, []);
  useEffect(() => reload(), [reload]);

  if (err) return <ErrorBanner message={err} />;
  if (!rows) return <Spinner label="절차를 불러오는 중…" />;
  if (!rows.length) return <EmptyWithSeeds onImported={reload} />;
  // 목록이 차 있어도 씨앗은 리포와 함께 자란다 — 다시 가져오면 판본이 올라간다(사본 아님).

  return (
    <>
    <ul className="pr-list">
      {rows.map((r) => (
        <li key={r.id} className="pr-card">
          <NavLink to={`/procedures/saved/${r.id}`} className="pr-link pr-strong">
            {r.title}
          </NavLink>
          <span className="pr-meta">
            판본 {r.latest_version} · {r.visibility === 'all' ? '공유' : '개인'}
            {r.from_seed && ' · 정본 예제'}
          </span>
        </li>
      ))}
    </ul>
      <SeedRefresh onImported={reload} />
      <YamlImport onImported={reload} />
    </>
  );
}

/** 다른 박스에서 내보낸 절차를 들인다(PLAN S1 — dev → cae00). */
function YamlImport({ onImported }: { onImported: () => void }) {
  const [text, setText] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <section className="pr-card pr-card-stack pr-mt-3">
      <strong className="pr-subhead">YAML 가져오기</strong>
      <span className="pr-note">
        다른 박스에서 내려받은 절차 YAML 을 붙여 넣습니다. <b>사람이 만든 것과 똑같이</b>
        검증하므로, 그 박스에 없는 도구가 있으면 경고로 알려 줍니다.
      </span>
      <textarea
        className="pr-input pr-mono-sm pr-minh-5"
        spellCheck={false}
        placeholder="# 절차 내보내기 — …"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="pr-row">
        <button type="button" className="btn-secondary pr-btn-sm" disabled={busy || !text.trim()}
                onClick={async () => {
                  setBusy(true);
                  setMsg(null);
                  try {
                    const got = await importProcedureYaml(text.trim());
                    setText('');
                    setMsg(got.warnings?.length ? got.warnings.join(' · ') : '들였습니다.');
                    onImported();
                  } catch (e) {
                    setMsg((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}>
          {busy ? '들이는 중…' : '들이기'}
        </button>
        {msg && <span className="pr-note">{msg}</span>}
      </div>
    </section>
  );
}

/** 씨앗은 리포와 함께 자란다 — 목록이 차 있어도 최신판을 받을 길이 있어야 한다. */
function SeedRefresh({ onImported }: { onImported: () => void }) {
  const [seeds, setSeeds] = useState<SeedRow[] | null>(null);
  const [seedErr, setSeedErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    // 못 받은 것은 **비어 있는 것과 다르다.** 조용히 []로 두면 정본 예제 칸이 통째로
    // 사라져, 게이트웨이가 죽은 것과 "예제가 없다" 가 같은 모양이 된다.
    listSeeds()
      .then((r) => setSeeds(r.seeds.filter((x) => !x.broken)))
      .catch((e: Error) => { setSeeds([]); setSeedErr(e.message); });
  }, []);
  if (seedErr) {
    return (
      <p className="pr-warn pr-fs-12">
        정본 예제 목록을 못 받았습니다 — {seedErr} (예제가 없다는 뜻이 아닙니다)
      </p>
    );
  }
  if (!seeds?.length) return null;

  const take = async (s: SeedRow) => {
    setBusy(s.name);
    setMsg(null);
    try {
      const r = await importSeed(s.name);
      setMsg(r.updated ? `${s.title} — 판본 ${r.version_no} 로 올렸습니다.`
                       : `${s.title} — 가져왔습니다.`);
      onImported();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="pr-card pr-card-top pr-card-tight pr-mt-3">
      <div className="pr-col">
        <strong className="pr-subhead">함께 오는 정본 예제</strong>
        <span className="pr-note">
          예제는 리포와 함께 자랍니다. 다시 받으면 <b>사본이 아니라 판본</b>이 올라가고,
          옛 판본과 그 이력은 그대로 남습니다.
        </span>
        {msg && <span className="pr-note">{msg}</span>}
      </div>
      <div className="pr-wrap">
        {seeds.map((s) => (
          <button key={s.name} type="button" className="btn-secondary pr-btn-sm" disabled={busy === s.name}
                  onClick={() => take(s)}>
            {busy === s.name ? '받는 중…' : `${s.title} 최신으로`}
          </button>
        ))}
      </div>
    </section>
  );
}

/** 절차가 하나도 없을 때 — 무엇을 만들 수 있는지 **실물로** 보여 준다. */
function EmptyWithSeeds({ onImported }: { onImported: () => void }) {
  const [seeds, setSeeds] = useState<SeedRow[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    listSeeds()
      .then((r) => setSeeds(r.seeds))
      .catch((e: Error) => setErr(e.message));
  }, []);

  const take = async (name: string) => {
    setBusy(name);
    setErr(null);
    try {
      await importSeed(name);
      onImported();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="pr-stack">
      <p className="pr-muted pr-m-0">
        아직 저장된 절차가 없습니다. <b>만들기</b> 탭에서 도구를 한 단계씩 돌린 뒤 "절차로
        저장" 을 누르면 여기 쌓입니다. 아래는 함께 오는 <b>정본 예제</b>입니다 — 가져와서
        값만 채워 돌려 볼 수 있습니다.
      </p>
      {err && <ErrorBanner message={err} />}
      {!seeds && <Spinner label="예제를 불러오는 중…" />}
      {seeds?.map((s) => (
        <section key={s.name} className="pr-card pr-card-top">
          <div className="pr-col pr-col-wide">
            <strong className="pr-fg">{s.title}</strong>
            {s.broken ? (
              <span className="pr-danger pr-fs-13">
                이 예제가 깨져 있습니다({s.broken}) — 가져올 수 없습니다.
              </span>
            ) : (
              <>
                <span className="pr-meta">
                  단계 {s.steps} · {s.backends?.join(' · ')}
                  {s.gates?.length ? ` · 사람 확인 ${s.gates.length}곳` : ''}
                </span>
                {!!s.vars?.length && (
                  <ul className="pr-bullets pr-mt-1 pr-fs-12">
                    {s.vars.filter((v) => v.why).slice(0, 3).map((v) => (
                      <li key={v.key}>
                        <b className="pr-fg">{v.label}</b> — <Bold text={v.why ?? ''} />
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
          {!s.broken && (
            <button type="button" className="btn-primary pr-btn" disabled={busy === s.name}
                    onClick={() => take(s.name)}>
              {busy === s.name ? '가져오는 중…' : '가져오기'}
            </button>
          )}
        </section>
      ))}
    </div>
  );
}

/** 예시를 칸에 넣을 문자열로. 객체·배열은 사람이 고칠 수 있게 들여쓴 JSON 이다. */
function exampleText(v: unknown): string {
  if (typeof v === 'string') return v;
  return JSON.stringify(v, null, 2);
}

function ProcedureDetail() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const { watch } = useProcedures();
  const [v, setV] = useState<ProcedureVersion | null>(null);
  const [vals, setVals] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // ⚠ 절차를 갈아탈 때 **비운다.** 안 비우면 앞 절차에 입력한 값(`vals`)이 그대로 남아
  // 새 절차 id 로 제출된다 — 같은 이름의 변수면 화면상 아무 표시도 없다. 늦게 온 응답이
  // 새 절차를 덮어쓰는 것도 막는다(`alive`).
  useEffect(() => {
    let alive = true;
    setV(null);
    setVals({});
    setErr(null);
    getProcedure(id)
      .then((got) => alive && setV(got))
      .catch((e: Error) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [id]);

  const go = async (mode: 'plan' | 'live') => {
    setBusy(true);
    setErr(null);
    try {
      const r = await replayProcedure(id, vals, mode);
      watch(r.run_id);
      nav(`/procedures/runs/${r.run_id}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (err) return <ErrorBanner message={err} />;
  if (!v) return <Spinner label="절차를 불러오는 중…" />;

  const gates = v.spec.steps.filter((s) => s.gate === 'human');

  return (
    <div className="pr-stack">
      <section className="pr-card">
        <h2 className="pr-h2 pr-m-0">{v.spec.title}</h2>
        <span className="pr-meta">
          판본 {v.version_no}
          {v.derived_from_run && ' · 실행에서 뽑음'}
        </span>
      </section>

      {gates.length > 0 && (
        <section className="pr-card pr-card-warn">
          <strong className="pr-warn">되돌리기 어려운 단계 {gates.length}개</strong>
          <p className="pr-meta pr-m-0 pr-mt-1">
            각 단계에서 멈추고 확인을 받습니다 — {gates.map((g) => g.tool).join(', ')}
          </p>
        </section>
      )}

      {(v.spec.vars?.length ?? 0) > 0 && (
        <section className="pr-card pr-card-block">
          <div className="pr-head pr-mb-2">
            <h3 className="pr-h3">이번에 채울 값</h3>
            {(v.spec.vars ?? []).some((d) => d.example !== undefined && d.example !== null) && (
              <>
                <button type="button" className="btn-secondary pr-btn-sm"
                        onClick={() => setVals({
                          ...vals,
                          ...Object.fromEntries((v.spec.vars ?? [])
                            .filter((d) => d.example !== undefined && d.example !== null)
                            .map((d) => [d.key, exampleText(d.example)])),
                        })}>
                  예제 값 모두 넣기
                </button>
                <span className="pr-note">
                  함께 오는 예제로 한 번 돌려 보는 용도입니다. <b>내 부품의 값이 아닙니다.</b>
                </span>
              </>
            )}
          </div>
          <div className="pr-fields">
            {(v.spec.vars ?? []).map((d) => (
              <label key={d.key} className="pr-field">
                <span className="pr-label">
                  {d.label} <code className="pr-muted">{d.key}</code>
                </span>
                {d.type === 'enum' ? (
                  <select className="pr-input" value={vals[d.key] ?? ''} onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })}>
                    <option value="">(고르세요)</option>
                    {(d.values ?? []).map((x) => (
                      <option key={x} value={x}>
                        {x}
                      </option>
                    ))}
                  </select>
                ) : d.type === 'json' ? (
                  // 적층 정의는 한 줄 칸에 못 넣는다 — 여러 줄로 받고 형은 서버가 푼다
                  <textarea
                    className="pr-input pr-mono-sm pr-minh-9"
                    spellCheck={false}
                    placeholder='{"unit_system": "SI_mm", "laminae": [...]}'
                    value={vals[d.key] ?? ''}
                    onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })}
                  />
                ) : (
                  <input className="pr-input" value={vals[d.key] ?? ''} onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })} />
                )}
                {d.why && <span className="pr-note"><Bold text={d.why} /></span>}
                {d.example !== undefined && d.example !== null && (
                  <span className="pr-row">
                    <button type="button" className="btn-secondary pr-btn-sm"
                            onClick={() => setVals({ ...vals, [d.key]: exampleText(d.example) })}>
                      예시 넣기
                    </button>
                    <span className="pr-note">
                      내 값이 아니다 — 넣고 <b>고쳐서</b> 쓴다.
                    </span>
                  </span>
                )}
              </label>
            ))}
          </div>
        </section>
      )}

      <section className="pr-card pr-card-block">
        <h3 className="pr-h3 pr-mb-2">단계 {v.spec.steps.length}개</h3>
        <ol className="pr-bullets pr-fs-14">
          {v.spec.steps.map((s, i) => (
            <li key={i}>
              <code className="pr-fg">{s.tool}</code> <span>{s.backend}</span>
              {s.gate === 'human' && <span className="pr-warn"> · 사람 확인</span>}
            </li>
          ))}
        </ol>
      </section>

      {err && <ErrorBanner message={err} />}
      <div className="pr-actions">
        <button type="button" onClick={() => go('plan')} disabled={busy} className="btn-secondary pr-btn">
          계획만 보기
        </button>
        <button type="button" onClick={() => go('live')} disabled={busy} className="btn-primary pr-btn">
          {busy ? '시작 중…' : '재생'}
        </button>
      </div>
      <p className="pr-note pr-m-0">
        계획 모드는 게이트웨이를 부르지 않고 <b>무엇을 어떤 인자로 부를지</b>만 보여 줍니다.
      </p>

      <section className="pr-card pr-card-baseline pr-card-tight">
        <h3 className="pr-h3">다른 박스로 옮기기</h3>
        <a href={exportProcedureUrl(id)} className="btn-secondary pr-btn-sm">
          YAML 로 내려받기
        </a>
        <span className="pr-note">
          본문만 옮깁니다 — <b>실행 기록·소유자는 안 담깁니다.</b> 받는 쪽에서 절차 목록의
          “YAML 가져오기” 로 들이면 사람이 만든 것과 똑같이 검증합니다.
        </span>
      </section>

      <ToolContract procedureId={id} />
      <ProcedureRuns procedureId={id} />
    </div>
  );
}

/** 비교표 — 한 배치의 실행들을 나란히 본다(PLAN S5).
 *
 * ⚠ `inputs` 를 **그대로 열로 편다.** 단계 인자를 역파싱하면 치환된 뒤 값이라 무엇이
 * 달랐는지가 흐려진다 — 비교표의 요점은 "무엇을 바꿨더니 무엇이 달라졌나" 다.
 */
function BatchView() {
  const { id = '' } = useParams();
  const [t, setT] = useState<BatchTable | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    getBatch(id).then(setT).catch((e: Error) => setErr(e.message));
  }, [id]);
  useEffect(() => load(), [load]);

  if (err) return <ErrorBanner message={err} />;
  if (!t) return <Spinner label="비교표를 불러오는 중…" />;

  const done = t.runs.filter((r) => r.state === 'done').length;
  const gated = t.runs.filter((r) => r.state === 'gated').length;
  const failed = t.runs.filter((r) => r.state === 'failed').length;

  return (
    <div className="pr-stack">
      <section className="pr-card">
        <div>
          <strong className="pr-fg">배치 {t.count}건</strong>
          <span className="pr-meta">
            {' '}· 끝남 {done} · 확인 대기 {gated} · 실패 {failed}
          </span>
        </div>
        <button type="button" className="btn-secondary pr-btn" onClick={load}>새로 고침</button>
      </section>

      {gated > 0 && (
        <p className="pr-warn pr-fs-13 pr-m-0">
          사람 확인이 걸린 단계에서 <b>각자 멈춰 있습니다.</b> 표에서 골라 하나씩 이어갑니다 —
          초안이 한꺼번에 {t.count}개 만들어지지 않습니다.
        </p>
      )}

      <section className="pr-card pr-card-block pr-card-scroll">
        <table className="pr-table pr-batch">
          <thead>
            <tr>
              <th>상태</th>
              {t.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
              <th>왜 / 경고</th>
            </tr>
          </thead>
          <tbody>
            {t.runs.map((r) => (
              <tr key={r.id}>
                <td className="pr-batch-state">
                  <NavLink to={`/procedures/runs/${r.id}`} className="pr-link"
                           style={{ color: r.state === 'gated' ? 'var(--warn)'
                                    : r.state === 'failed' ? 'var(--danger)' : 'var(--fg)' }}>
                    {r.state === 'gated' ? '확인 대기' : r.state}
                  </NavLink>
                </td>
                {t.columns.map((c) => (
                  <td key={c} className="pr-batch-val">
                    {fmt(r.inputs?.[c])}
                  </td>
                ))}
                <td className="pr-batch-why">
                  {r.failed_at && (
                    <span className="pr-danger">
                      {r.failed_at.ix + 1}단계 <code>{r.failed_at.tool}</code> — {r.failed_at.error}
                    </span>
                  )}
                  {!!r.warnings?.length && (
                    <span className="pr-warn" style={{ marginLeft: r.failed_at ? 'var(--sp-2)' : 0 }}>
                      {r.warnings.join(' ')}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function fmt(v: unknown): string {
  if (v === undefined || v === null) return '';
  return typeof v === 'object' ? JSON.stringify(v).slice(0, 120) : String(v);
}

/** 이 실행을 절차로 펴 본다 — **안 펴지는 칸이 곧 결손이다**(PLAN §9-2).
 *
 * ⚠ 저장하지 않는다. 어느 인자가 변수이고 어느 것이 상수인지는 사람이 확정한다.
 */
function DraftView({ runId }: { runId: string }) {
  const nav = useNavigate();
  const [d, setD] = useState<RunDraft | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // 어느 상수를 변수로 올릴지 — 키는 `단계|인자`, 값은 사람이 줄 변수 이름
  const [promote, setPromote] = useState<Record<string, string>>({});
  const [title, setTitle] = useState('');
  const [saved, setSaved] = useState<string[] | null>(null);
  const [gapDoc, setGapDoc] = useState<{ filename: string; yaml_text: string } | null>(null);

  const look = async () => {
    setBusy(true);
    setErr(null);
    try {
      const got = await getRunDraft(runId);
      setD(got);
      setTitle((t) => t || got.spec.title || '');
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="pr-card">
      <div className="pr-head">
        <h3 className="pr-h3">절차로 펴 보기</h3>
        <button type="button" className="btn-secondary pr-btn-sm" disabled={busy} onClick={look}>
          {busy ? '펴는 중…' : d ? '다시 펴 보기' : '펴 보기'}
        </button>
        <span className="pr-note">
          저장하지 않습니다. 무엇이 변수인지는 <b>사람이 정합니다.</b>
        </span>
      </div>
      {err && <ErrorBanner message={err} />}
      {d && (
        <div className="pr-form pr-mt-2">
          <div>
            <b className="pr-fg pr-fs-14">
              단계 {d.spec.steps?.length ?? 0} · 변수 {d.spec.vars?.length ?? 0}
            </b>
            <ol className="pr-bullets pr-mt-1 pr-fs-13">
              {d.spec.steps.map((st, i) => (
                <li key={i}>
                  <code className="pr-fg">{st.tool}</code>{' '}
                  {st.backend || <span className="pr-danger">앱을 모름</span>}
                  {st.save && (
                    <span> · 넘김 {Object.entries(st.save).map(([k, v]) => `${k}←${v}`).join(', ')}</span>
                  )}
                </li>
              ))}
            </ol>
          </div>

          {d.needs_human.length > 0 && (
            <div>
              <b className="pr-warn pr-fs-14">
                사람이 정할 자리 {d.needs_human.length}곳
              </b>
              <p className="pr-note pr-m-0 pr-mt-1 pr-mb-2">
                코드는 이 값들이 어디서 왔는지 <b>모릅니다.</b> 과제마다 바뀌는 값이면 변수로
                올리고, 이 절차의 성질이면 그대로 둡니다.
              </p>
              <ul className="pr-list pr-list-tight">
                {d.needs_human.map((r) => {
                  const k = `${r.step}|${r.arg}`;
                  return (
                    <li key={k} className="pr-pick">
                      <label className="pr-check">
                        <input
                          type="checkbox"
                          checked={!!promote[k]}
                          onChange={(e) =>
                            setPromote((p) => {
                              const n = { ...p };
                              if (e.target.checked) n[k] = r.arg;
                              else delete n[k];
                              return n;
                            })
                          }
                        />
                        <span className="pr-fg">변수로</span>
                      </label>
                      <span className="pr-muted">
                        {r.step}단계 <code className="pr-fg">{r.arg}</code> — {r.why}
                      </span>
                      {promote[k] !== undefined && (
                        <input
                          className="pr-input pr-input-tight pr-input-sm"
                          value={promote[k]}
                          placeholder="변수 이름"
                          onChange={(e) => setPromote((p) => ({ ...p, [k]: e.target.value }))}
                        />
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <div className="pr-row">
            <input
              className="pr-input pr-grow"
              value={title}
              placeholder="절차 이름"
              onChange={(e) => setTitle(e.target.value)}
            />
            <button
              type="button"
              className="btn-primary pr-btn"
              disabled={busy || !title.trim()}
              onClick={async () => {
                setBusy(true);
                setErr(null);
                try {
                  const picks = Object.entries(promote).map(([k, name]) => {
                    const [step, arg] = k.split('|');
                    return { step: Number(step), arg, key: name || arg };
                  });
                  const got = await saveDraft(runId, title.trim(), picks);
                  setSaved(got.warnings ?? []);
                  nav(`/procedures/saved/${got.id}`);
                } catch (e) {
                  setErr((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? '굳히는 중…' : '절차로 굳히기'}
            </button>
            {!!saved?.length && (
              <span className="pr-warn pr-fs-12">{saved.join(' · ')}</span>
            )}
          </div>

          {d.gaps.length > 0 && (
            <div>
              <b className="pr-danger pr-fs-14">안 펴지는 칸 {d.gaps.length}곳</b>
              <ul className="pr-bullets pr-mt-1 pr-fs-13">
                {d.gaps.map((g, i) => (
                  <li key={i} className="pr-mb-1">
                    {g.step ? `${g.step}단계 ` : ''}
                    {g.tool && <code>{g.tool}</code>} {g.why}{' '}
                    <button type="button" className="btn-secondary pr-btn-sm pr-btn-xs"
                            onClick={async () => {
                              try {
                                const got = await draftGap(runId, g as unknown as
                                  Record<string, unknown>);
                                setGapDoc(got);
                              } catch (e) {
                                setErr((e as Error).message);
                              }
                            }}>
                      장부 초안
                    </button>
                  </li>
                ))}
              </ul>
              <p className="pr-note pr-m-0 pr-mt-1">
                이 칸들이 <b>결손</b>입니다. 그 값이 어느 시스템엔가 이미 있다면 그 앱에 도구를
                만들 자리이고, 없다면 절차의 변수로 남습니다.
              </p>
              {gapDoc && (
                <div className="pr-mt-2">
                  <p className="pr-note pr-m-0 pr-mb-1">
                    ⚠ <b>초안입니다.</b> 확인한 뒤 리포의{' '}
                    <code>docs/procedures/gaps/{gapDoc.filename}</code> 로 커밋하세요 —
                    포털이 리포에 직접 쓰지 않습니다.
                  </p>
                  <textarea
                    readOnly
                    className="pr-input pr-mono-sm pr-minh-11"
                    value={gapDoc.yaml_text}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/** 이 절차를 **도구로 본다** — 변수가 곧 입력 스키마다.
 *
 * 절차는 사실상 도구다. 그 계약을 도구와 같은 모양으로 보여 주면, 이 절차를 남에게(또는
 * 챗·심의에) 넘길 때 무엇을 채워야 하는지가 한눈에 보인다.
 */
function ToolContract({ procedureId }: { procedureId: string }) {
  const [t, setT] = useState<ProcedureTool | null>(null);
  const [tErr, setTErr] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  // ⚠ 절차가 바뀌면 다시 받는다. `!t` 로 막아 두면 A 의 스키마가 B 의 제목 아래 남는다.
  useEffect(() => {
    setT(null);
    setTErr(null);
  }, [procedureId]);

  useEffect(() => {
    if (!open || t || tErr) return;
    let alive = true;
    getProcedureTool(procedureId)
      .then((got) => alive && setT(got))
      // ⚠ 조용히 null 로 두면 펴도 **아무것도 없는 칸**이 열린다 — 못 받은 것과
      // 계약이 없는 것이 같은 모양이 된다. 왜 못 받았는지 말한다.
      .catch((e: Error) => alive && setTErr(e.message));
    return () => {
      alive = false;
    };
  }, [open, t, tErr, procedureId]);

  const props = (t?.inputSchema.properties ?? {}) as Record<string, {
    type?: string; description?: string; enum?: string[]; examples?: unknown[];
  }>;
  const req = new Set(t?.inputSchema.required ?? []);

  return (
    <section className="pr-card">
      <div className="pr-head">
        <h3 className="pr-h3">도구로 보기</h3>
        <button type="button" className="btn-secondary pr-btn-sm" onClick={() => setOpen((v) => !v)}>
          {open ? '접기' : '펴기'}
        </button>
        <span className="pr-note">
          절차의 변수가 곧 <b>입력 스키마</b>입니다.
        </span>
      </div>
      {open && tErr && (
        <p className="pr-warn pr-fs-13 pr-m-0 pr-mt-2">
          도구 계약을 못 받았습니다 — {tErr}{' '}
          <button type="button" className="btn-secondary pr-btn-sm" onClick={() => setTErr(null)}>다시</button>
        </p>
      )}
      {open && t && (
        <div className="pr-fields pr-mt-2">
          {t.human_gates.length > 0 && (
            <p className="pr-warn pr-fs-13 pr-m-0">
              ⚠ <b>{t.human_gates.join(', ')}</b> 에서 멈추고 사람 확인을 받습니다 —
              부르는 쪽이 이걸 모르면 “왜 안 끝나지” 가 됩니다.
            </p>
          )}
          <table className="pr-table pr-contract">
            <tbody>
              {Object.entries(props).map(([k, p]) => (
                <tr key={k}>
                  <td className="pr-contract-key">
                    <code className="pr-fg">{k}</code>
                    {req.has(k) && <span className="pr-danger"> *</span>}
                    <div className="pr-note">
                      {p.enum ? p.enum.join(' | ') : p.type}
                    </div>
                  </td>
                  <td className="pr-contract-desc">
                    {p.description || <i>설명이 없습니다 — 도구 스키마에 근거가 없습니다.</i>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/** 이 절차로 돌린 것들 — 절차를 만든 뜻은 **다시 돌리는 것**이라 이력이 절차 옆에 있어야 한다. */
function ProcedureRuns({ procedureId }: { procedureId: string }) {
  const [rows, setRows] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    listRuns(procedureId)
      .then((r) => setRows(r.runs))
      .catch((e: Error) => setErr(e.message));
  }, [procedureId]);

  return (
    <section className="pr-card">
      <h3 className="pr-h3 pr-mb-2">
        이 절차로 돌린 이력 {rows ? `${rows.length}건` : ''}
      </h3>
      {err && <ErrorBanner message={err} />}
      {!rows && <Spinner label="이력을 불러오는 중…" />}
      {rows?.length === 0 && (
        <p className="pr-meta pr-m-0">
          아직 없습니다. 위에서 값을 채우고 <b>재생</b> 을 누르면 여기 쌓이고, 쌓인 실행은
          그 값 그대로 다시 돌릴 수 있습니다.
        </p>
      )}
      {!!rows?.length && (
        <ul className="pr-list">
          {rows.map((r) => (
            <li key={r.id} className="pr-run-row">
              <NavLink to={`/procedures/runs/${r.id}`}
                       className="pr-link pr-fs-14">
                {new Date(r.started_at * 1000).toLocaleString('ko-KR')}
                {r.version_no ? ` · 판본 ${r.version_no}` : ''}
              </NavLink>
              <span className="pr-fs-12"
                    style={{ color: r.state === 'gated' ? 'var(--warn)' : 'var(--fg-muted)' }}>
                {r.state === 'gated' ? '확인 대기' : r.state}
                {r.mode === 'plan' && ' · 계획'}
                {r.origin === 'replay' && ' · 다시 돌림'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ── 실행 ───────────────────────────────────────────────────────────────────
function RunList() {
  const [rows, setRows] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    listRuns()
      .then((r) => setRows(r.runs))
      .catch((e: Error) => setErr(e.message));
  }, []);

  if (err) return <ErrorBanner message={err} />;
  if (!rows) return <Spinner label="실행 이력을 불러오는 중…" />;
  if (!rows.length) return <p className="pr-muted">아직 실행이 없습니다.</p>;

  return (
    <ul className="pr-list">
      {rows.map((r) => (
        <li key={r.id} className="pr-card" style={{ borderColor: r.state === 'gated' ? 'var(--warn)' : 'var(--border)' }}>
          <NavLink to={`/procedures/runs/${r.id}`} className="pr-link">
            {r.title ?? r.id.slice(0, 8)}
          </NavLink>
          <span className="pr-fs-13" style={{ color: r.state === 'gated' ? 'var(--warn)' : 'var(--fg-muted)' }}>
            {r.state === 'gated' ? '확인 대기' : r.state}
            {r.mode === 'plan' && ' · 계획'}
            {r.origin === 'replay' && ' · 다시 돌림'}
            {r.version_no ? ` · 판본 ${r.version_no}` : ' · 절차 없음'}
          </span>
        </li>
      ))}
    </ul>
  );
}

function RunDetailView() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const { watch, watched, refreshWatched } = useProcedures();
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => watch(id), [id, watch]);

  if (err) return <ErrorBanner message={err} />;
  if (!watched) return <Spinner label="실행을 불러오는 중…" />;

  const act = async (fn: () => Promise<unknown>) => {
    setErr(null);
    try {
      await fn();
      await refreshWatched();
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const running = watched.state === 'running' || watched.state === 'queued';

  return (
    <div className="pr-stack">
      <section className="pr-card" style={{ borderColor: watched.state === 'gated' ? 'var(--warn)' : 'var(--border)' }}>
        <div>
          <strong className="pr-fg">{watched.title ?? watched.id.slice(0, 8)}</strong>
          <span className="pr-meta">
            {' '}
            · {watched.state}
            {watched.stage ? ` (${watched.stage})` : ''} · {watched.mode === 'plan' ? '계획' : '실행'}
          </span>
          {watched.procedure_id && (
            <div className="pr-mt-1">
              <NavLink to={`/procedures/saved/${watched.procedure_id}`}
                       className="pr-note">
                ← 이 절차 판본 {watched.version_no} 에서 나왔습니다
              </NavLink>
            </div>
          )}
        </div>
        <div className="pr-actions">
          {!running && watched.procedure_version_id && (
            // 이력이 값을 들고 있는데 다시 돌릴 길이 없으면 사람이 칸을 손으로 옮겨 적는다.
            // 옮겨 적는 순간 "같은 입력" 이라는 보장이 사라진다.
            <button type="button" className="btn-primary pr-btn"
                    onClick={() => act(async () => {
                      const r = await replayRun(watched.id, 'live');
                      watch(r.run_id);
                      nav(`/procedures/runs/${r.run_id}`);
                    })}>
              이 값으로 다시 돌리기
            </button>
          )}
          {(watched.state === 'failed' || watched.state === 'unknown') && (
            <button type="button" className="btn-secondary pr-btn" onClick={() => act(() => resumeRun(watched.id))}>
              재개
            </button>
          )}
          {running && (
            <button type="button" className="btn-secondary pr-btn" onClick={() => act(() => cancelRun(watched.id))}>
              중단
            </button>
          )}
        </div>
      </section>
      {err && <ErrorBanner message={err} />}
      <RunSteps run={watched} onChanged={refreshWatched} />
      <DraftView runId={watched.id} />
    </div>
  );
}
