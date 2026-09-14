// 절차 셸 — 탭 셋(만들기·절차·실행 이력)과 자식 라우트
//
// 루트는 `.container` 다 — AppShell 의 ChatDock 이 열릴 때 자리를 비켜 주는 클래스다.
// 우하단은 비워 둔다(닫힌 독의 💬 FAB 가 거기 고정이라 겹친다).
import { NavLink, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { useProcedures } from '../../state/ProceduresContext';
import {
  cancelRun,
  getProcedure,
  getRunDraft,
  importSeed,
  listSeeds,
  replayRun,
  listProcedures,
  listRuns,
  replayProcedure,
  resumeRun,
  type ProcedureRow,
  type ProcedureVersion,
  type RunDraft,
  type RunSummary,
  type SeedRow,
} from '../../api/procedures.api';
import BuildView from './BuildView';
import { RunSteps } from './RunSteps';

export default function ProceduresPage() {
  return (
    <div className="container" style={{ maxWidth: 1080, margin: '0 auto', padding: '1.6rem 1.5rem 4rem' }}>
      <header style={{ marginBottom: '1.1rem' }}>
        <h1 style={{ color: 'var(--fg)', margin: '0 0 0.2rem', fontSize: '1.5rem' }}>절차</h1>
        <p style={{ color: 'var(--muted)', margin: 0, fontSize: '0.9rem' }}>
          한 번 해낸 일을 절차로 굳혀 두었다가, 대상만 바꿔 다시 돌립니다.
        </p>
      </header>

      <nav style={{ display: 'flex', gap: '0.4rem', marginBottom: '1.1rem', flexWrap: 'wrap' }}>
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
      </Routes>
    </div>
  );
}

function Tab({ to, end, children }: { to: string; end?: boolean; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end={end}
      style={({ isActive }) => ({
        padding: '0.35rem 0.8rem',
        borderRadius: 4,
        border: '1px solid var(--border)',
        textDecoration: 'none',
        fontSize: '0.86rem',
        color: isActive ? '#fff' : 'var(--muted)',
        background: isActive ? 'var(--accent)' : 'transparent',
      })}
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
    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.5rem' }}>
      {rows.map((r) => (
        <li key={r.id} style={rowCard}>
          <NavLink to={`/procedures/saved/${r.id}`} style={{ color: 'var(--fg)', fontWeight: 600, textDecoration: 'none' }}>
            {r.title}
          </NavLink>
          <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
            판본 {r.latest_version} · {r.visibility === 'all' ? '공유' : '개인'}
            {r.from_seed && ' · 정본 예제'}
          </span>
        </li>
      ))}
    </ul>
      <SeedRefresh onImported={reload} />
    </>
  );
}

/** 씨앗은 리포와 함께 자란다 — 목록이 차 있어도 최신판을 받을 길이 있어야 한다. */
function SeedRefresh({ onImported }: { onImported: () => void }) {
  const [seeds, setSeeds] = useState<SeedRow[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    listSeeds().then((r) => setSeeds(r.seeds.filter((x) => !x.broken))).catch(() => setSeeds([]));
  }, []);
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
    <section style={{ ...rowCard, marginTop: '0.8rem', alignItems: 'flex-start',
                      flexWrap: 'wrap', gap: '0.5rem' }}>
      <div style={{ display: 'grid', gap: '0.2rem', flex: '1 1 300px', minWidth: 0 }}>
        <strong style={{ color: 'var(--fg)', fontSize: '0.88rem' }}>함께 오는 정본 예제</strong>
        <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>
          예제는 리포와 함께 자랍니다. 다시 받으면 <b>사본이 아니라 판본</b>이 올라가고,
          옛 판본과 그 이력은 그대로 남습니다.
        </span>
        {msg && <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>{msg}</span>}
      </div>
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
        {seeds.map((s) => (
          <button key={s.name} type="button" style={tiny} disabled={busy === s.name}
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
    <div style={{ display: 'grid', gap: '1rem' }}>
      <p style={{ color: 'var(--muted)', margin: 0 }}>
        아직 저장된 절차가 없습니다. <b>만들기</b> 탭에서 도구를 한 단계씩 돌린 뒤 "절차로
        저장" 을 누르면 여기 쌓입니다. 아래는 함께 오는 <b>정본 예제</b>입니다 — 가져와서
        값만 채워 돌려 볼 수 있습니다.
      </p>
      {err && <ErrorBanner message={err} />}
      {!seeds && <Spinner label="예제를 불러오는 중…" />}
      {seeds?.map((s) => (
        <section key={s.name} style={{ ...rowCard, alignItems: 'flex-start' }}>
          <div style={{ display: 'grid', gap: '0.3rem', flex: '1 1 320px', minWidth: 0 }}>
            <strong style={{ color: 'var(--fg)' }}>{s.title}</strong>
            {s.broken ? (
              <span style={{ color: '#e5534b', fontSize: '0.82rem' }}>
                이 예제가 깨져 있습니다({s.broken}) — 가져올 수 없습니다.
              </span>
            ) : (
              <>
                <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
                  단계 {s.steps} · {s.backends?.join(' · ')}
                  {s.gates?.length ? ` · 사람 확인 ${s.gates.length}곳` : ''}
                </span>
                {!!s.vars?.length && (
                  <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.1rem',
                               color: 'var(--muted)', fontSize: '0.78rem' }}>
                    {s.vars.filter((v) => v.why).slice(0, 3).map((v) => (
                      <li key={v.key}>
                        <b style={{ color: 'var(--fg)' }}>{v.label}</b> — {v.why}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
          {!s.broken && (
            <button type="button" style={primary} disabled={busy === s.name}
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

  useEffect(() => {
    getProcedure(id)
      .then(setV)
      .catch((e: Error) => setErr(e.message));
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
    <div style={{ display: 'grid', gap: '1rem' }}>
      <section style={rowCard}>
        <h2 style={{ color: 'var(--fg)', margin: 0, fontSize: '1.05rem' }}>{v.spec.title}</h2>
        <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
          판본 {v.version_no}
          {v.derived_from_run && ' · 실행에서 뽑음'}
        </span>
      </section>

      {gates.length > 0 && (
        <section style={{ ...rowCard, borderColor: '#d9a441' }}>
          <strong style={{ color: '#d9a441' }}>되돌리기 어려운 단계 {gates.length}개</strong>
          <p style={{ color: 'var(--muted)', fontSize: '0.84rem', margin: '0.3rem 0 0' }}>
            각 단계에서 멈추고 확인을 받습니다 — {gates.map((g) => g.tool).join(', ')}
          </p>
        </section>
      )}

      {v.spec.vars.length > 0 && (
        <section style={rowCard}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.6rem', flexWrap: 'wrap',
                        margin: '0 0 0.6rem' }}>
            <h3 style={{ color: 'var(--fg)', margin: 0, fontSize: '0.95rem' }}>이번에 채울 값</h3>
            {v.spec.vars.some((d) => d.example !== undefined && d.example !== null) && (
              <>
                <button type="button" style={tiny}
                        onClick={() => setVals({
                          ...vals,
                          ...Object.fromEntries(v.spec.vars
                            .filter((d) => d.example !== undefined && d.example !== null)
                            .map((d) => [d.key, exampleText(d.example)])),
                        })}>
                  예제 값 모두 넣기
                </button>
                <span style={{ color: 'var(--muted)', fontSize: '0.74rem' }}>
                  함께 오는 예제로 한 번 돌려 보는 용도입니다. <b>내 부품의 값이 아닙니다.</b>
                </span>
              </>
            )}
          </div>
          <div style={{ display: 'grid', gap: '0.6rem' }}>
            {v.spec.vars.map((d) => (
              <label key={d.key} style={{ display: 'grid', gap: '0.2rem' }}>
                <span style={{ fontSize: '0.82rem', color: 'var(--fg)' }}>
                  {d.label} <code style={{ color: 'var(--muted)' }}>{d.key}</code>
                </span>
                {d.type === 'enum' ? (
                  <select style={inp} value={vals[d.key] ?? ''} onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })}>
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
                    style={{ ...inp, minHeight: '9rem', fontFamily: 'ui-monospace, monospace', fontSize: '0.78rem' }}
                    spellCheck={false}
                    placeholder='{"unit_system": "SI_mm", "laminae": [...]}'
                    value={vals[d.key] ?? ''}
                    onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })}
                  />
                ) : (
                  <input style={inp} value={vals[d.key] ?? ''} onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })} />
                )}
                {d.why && <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>{d.why}</span>}
                {d.example !== undefined && d.example !== null && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <button type="button" style={tiny}
                            onClick={() => setVals({ ...vals, [d.key]: exampleText(d.example) })}>
                      예시 넣기
                    </button>
                    <span style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>
                      내 값이 아니다 — 넣고 <b>고쳐서</b> 쓴다.
                    </span>
                  </span>
                )}
              </label>
            ))}
          </div>
        </section>
      )}

      <section style={rowCard}>
        <h3 style={{ color: 'var(--fg)', margin: '0 0 0.5rem', fontSize: '0.95rem' }}>단계 {v.spec.steps.length}개</h3>
        <ol style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
          {v.spec.steps.map((s, i) => (
            <li key={i}>
              <code style={{ color: 'var(--fg)' }}>{s.tool}</code> <span>{s.backend}</span>
              {s.gate === 'human' && <span style={{ color: '#d9a441' }}> · 사람 확인</span>}
            </li>
          ))}
        </ol>
      </section>

      {err && <ErrorBanner message={err} />}
      <div style={{ display: 'flex', gap: '0.6rem' }}>
        <button type="button" onClick={() => go('plan')} disabled={busy} style={ghost}>
          계획만 보기
        </button>
        <button type="button" onClick={() => go('live')} disabled={busy} style={primary}>
          {busy ? '시작 중…' : '재생'}
        </button>
      </div>
      <p style={{ color: 'var(--muted)', fontSize: '0.78rem', margin: 0 }}>
        계획 모드는 게이트웨이를 부르지 않고 <b>무엇을 어떤 인자로 부를지</b>만 보여 줍니다.
      </p>

      <ProcedureRuns procedureId={id} />
    </div>
  );
}

/** 이 실행을 절차로 펴 본다 — **안 펴지는 칸이 곧 결손이다**(PLAN §9-2).
 *
 * ⚠ 저장하지 않는다. 어느 인자가 변수이고 어느 것이 상수인지는 사람이 확정한다.
 */
function DraftView({ runId }: { runId: string }) {
  const [d, setD] = useState<RunDraft | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const look = async () => {
    setBusy(true);
    setErr(null);
    try {
      setD(await getRunDraft(runId));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section style={rowCard}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.6rem', flexWrap: 'wrap' }}>
        <h3 style={{ color: 'var(--fg)', margin: 0, fontSize: '0.95rem' }}>절차로 펴 보기</h3>
        <button type="button" style={tiny} disabled={busy} onClick={look}>
          {busy ? '펴는 중…' : d ? '다시 펴 보기' : '펴 보기'}
        </button>
        <span style={{ color: 'var(--muted)', fontSize: '0.74rem' }}>
          저장하지 않습니다. 무엇이 변수인지는 <b>사람이 정합니다.</b>
        </span>
      </div>
      {err && <ErrorBanner message={err} />}
      {d && (
        <div style={{ display: 'grid', gap: '0.7rem', marginTop: '0.6rem' }}>
          <div>
            <b style={{ color: 'var(--fg)', fontSize: '0.86rem' }}>
              단계 {d.spec.steps.length} · 변수 {d.spec.vars.length}
            </b>
            <ol style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem',
                         color: 'var(--muted)', fontSize: '0.82rem' }}>
              {d.spec.steps.map((st, i) => (
                <li key={i}>
                  <code style={{ color: 'var(--fg)' }}>{st.tool}</code>{' '}
                  {st.backend || <span style={{ color: '#e5534b' }}>앱을 모름</span>}
                  {st.save && (
                    <span> · 넘김 {Object.entries(st.save).map(([k, v]) => `${k}←${v}`).join(', ')}</span>
                  )}
                </li>
              ))}
            </ol>
          </div>

          {d.needs_human.length > 0 && (
            <div>
              <b style={{ color: '#d9a441', fontSize: '0.86rem' }}>
                사람이 정할 자리 {d.needs_human.length}곳
              </b>
              <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.1rem',
                           color: 'var(--muted)', fontSize: '0.8rem' }}>
                {d.needs_human.map((r, i) => (
                  <li key={i}>
                    {r.step}단계 <code style={{ color: 'var(--fg)' }}>{r.arg}</code> — {r.why}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {d.gaps.length > 0 && (
            <div>
              <b style={{ color: '#e5534b', fontSize: '0.86rem' }}>안 펴지는 칸 {d.gaps.length}곳</b>
              <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.1rem',
                           color: 'var(--muted)', fontSize: '0.8rem' }}>
                {d.gaps.map((g, i) => (
                  <li key={i}>{g.step}단계 <code>{g.tool}</code> — {g.why}</li>
                ))}
              </ul>
              <p style={{ color: 'var(--muted)', fontSize: '0.76rem', margin: '0.3rem 0 0' }}>
                이 칸들이 <b>결손</b>입니다. 그 값이 어느 시스템엔가 이미 있다면 그 앱에 도구를
                만들 자리이고, 없다면 절차의 변수로 남습니다.
              </p>
            </div>
          )}
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
    <section style={rowCard}>
      <h3 style={{ color: 'var(--fg)', margin: '0 0 0.5rem', fontSize: '0.95rem' }}>
        이 절차로 돌린 이력 {rows ? `${rows.length}건` : ''}
      </h3>
      {err && <ErrorBanner message={err} />}
      {!rows && <Spinner label="이력을 불러오는 중…" />}
      {rows?.length === 0 && (
        <p style={{ color: 'var(--muted)', fontSize: '0.84rem', margin: 0 }}>
          아직 없습니다. 위에서 값을 채우고 <b>재생</b> 을 누르면 여기 쌓이고, 쌓인 실행은
          그 값 그대로 다시 돌릴 수 있습니다.
        </p>
      )}
      {!!rows?.length && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.4rem' }}>
          {rows.map((r) => (
            <li key={r.id} style={{ display: 'flex', gap: '0.6rem', alignItems: 'baseline',
                                    justifyContent: 'space-between', flexWrap: 'wrap' }}>
              <NavLink to={`/procedures/runs/${r.id}`}
                       style={{ color: 'var(--fg)', textDecoration: 'none', fontSize: '0.86rem' }}>
                {new Date(r.started_at * 1000).toLocaleString('ko-KR')}
                {r.version_no ? ` · 판본 ${r.version_no}` : ''}
              </NavLink>
              <span style={{ color: r.state === 'gated' ? '#d9a441' : 'var(--muted)',
                             fontSize: '0.78rem' }}>
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
  if (!rows.length) return <p style={{ color: 'var(--muted)' }}>아직 실행이 없습니다.</p>;

  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.5rem' }}>
      {rows.map((r) => (
        <li key={r.id} style={{ ...rowCard, borderColor: r.state === 'gated' ? '#d9a441' : 'var(--border)' }}>
          <NavLink to={`/procedures/runs/${r.id}`} style={{ color: 'var(--fg)', textDecoration: 'none' }}>
            {r.title ?? r.id.slice(0, 8)}
          </NavLink>
          <span style={{ color: r.state === 'gated' ? '#d9a441' : 'var(--muted)', fontSize: '0.8rem' }}>
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
    <div style={{ display: 'grid', gap: '1rem' }}>
      <section style={{ ...rowCard, borderColor: watched.state === 'gated' ? '#d9a441' : 'var(--border)' }}>
        <div>
          <strong style={{ color: 'var(--fg)' }}>{watched.title ?? watched.id.slice(0, 8)}</strong>
          <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
            {' '}
            · {watched.state}
            {watched.stage ? ` (${watched.stage})` : ''} · {watched.mode === 'plan' ? '계획' : '실행'}
          </span>
          {watched.procedure_id && (
            <div style={{ marginTop: '0.25rem' }}>
              <NavLink to={`/procedures/saved/${watched.procedure_id}`}
                       style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>
                ← 이 절차 판본 {watched.version_no} 에서 나왔습니다
              </NavLink>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {!running && watched.procedure_version_id && (
            // 이력이 값을 들고 있는데 다시 돌릴 길이 없으면 사람이 칸을 손으로 옮겨 적는다.
            // 옮겨 적는 순간 "같은 입력" 이라는 보장이 사라진다.
            <button type="button" style={primary}
                    onClick={() => act(async () => {
                      const r = await replayRun(watched.id, 'live');
                      watch(r.run_id);
                      nav(`/procedures/runs/${r.run_id}`);
                    })}>
              이 값으로 다시 돌리기
            </button>
          )}
          {(watched.state === 'failed' || watched.state === 'unknown') && (
            <button type="button" style={ghost} onClick={() => act(() => resumeRun(watched.id))}>
              재개
            </button>
          )}
          {running && (
            <button type="button" style={ghost} onClick={() => act(() => cancelRun(watched.id))}>
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

const rowCard: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 6,
  background: 'var(--card)',
  padding: '0.75rem 0.95rem',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: '0.8rem',
  flexWrap: 'wrap',
};
const inp: React.CSSProperties = {
  width: '100%',
  background: 'var(--bg)',
  color: 'var(--fg)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  padding: '0.4rem 0.55rem',
  fontSize: '0.85rem',
};
const primary: React.CSSProperties = {
  background: 'var(--accent)',
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  padding: '0.45rem 1rem',
  cursor: 'pointer',
  fontSize: '0.88rem',
};
const ghost: React.CSSProperties = {
  background: 'transparent',
  color: 'var(--fg)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  padding: '0.45rem 1rem',
  cursor: 'pointer',
  fontSize: '0.88rem',
};

const tiny: React.CSSProperties = {
  ...ghost,
  padding: '0.2rem 0.55rem',
  fontSize: '0.74rem',
  alignSelf: 'flex-start',
};
