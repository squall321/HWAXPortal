// 절차 셸 — 탭 셋(만들기·절차·실행 이력)과 자식 라우트
//
// 루트는 `.container` 다 — AppShell 의 ChatDock 이 열릴 때 자리를 비켜 주는 클래스다.
// 우하단은 비워 둔다(닫힌 독의 💬 FAB 가 거기 고정이라 겹친다).
import { NavLink, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/common/Spinner';
import { useProcedures } from '../../state/ProceduresContext';
import {
  cancelRun,
  getProcedure,
  listProcedures,
  listRuns,
  replayProcedure,
  resumeRun,
  type ProcedureRow,
  type ProcedureVersion,
  type RunSummary,
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

  useEffect(() => {
    listProcedures()
      .then((r) => setRows(r.procedures))
      .catch((e: Error) => setErr(e.message));
  }, []);

  if (err) return <ErrorBanner message={err} />;
  if (!rows) return <Spinner label="절차를 불러오는 중…" />;
  if (!rows.length)
    return (
      <p style={{ color: 'var(--muted)' }}>
        아직 절차가 없습니다. <b>만들기</b> 탭에서 도구를 한 단계씩 돌린 뒤 "절차로 저장" 을
        누르면 여기 쌓입니다.
      </p>
    );

  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.5rem' }}>
      {rows.map((r) => (
        <li key={r.id} style={rowCard}>
          <NavLink to={`/procedures/saved/${r.id}`} style={{ color: 'var(--fg)', fontWeight: 600, textDecoration: 'none' }}>
            {r.title}
          </NavLink>
          <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
            판본 {r.latest_version} · {r.visibility === 'all' ? '공유' : '개인'}
          </span>
        </li>
      ))}
    </ul>
  );
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
          <h3 style={{ color: 'var(--fg)', margin: '0 0 0.6rem', fontSize: '0.95rem' }}>이번에 채울 값</h3>
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
                ) : (
                  <input style={inp} value={vals[d.key] ?? ''} onChange={(e) => setVals({ ...vals, [d.key]: e.target.value })} />
                )}
                {d.why && <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>{d.why}</span>}
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
    </div>
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
          </span>
        </li>
      ))}
    </ul>
  );
}

function RunDetailView() {
  const { id = '' } = useParams();
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
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
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
