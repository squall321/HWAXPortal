// 만들기 — **진입점**. 저장된 절차가 없어도 도구를 한 단계씩 돌리고, 끝나면 절차로 굳힌다.
//
// 절차 목록이 아니라 여기가 시작이다(PLAN §1) — 저장된 절차가 하나도 없어도 시작할 수 있어야
// 하고, 그 기록이 곧 절차라 해석이 필요 없다.
import { useEffect, useMemo, useState } from 'react';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { useProcedures } from '../../state/ProceduresContext';
import {
  runStep,
  saveAsProcedure,
  startEmptyRun,
  type StepDef,
  type Dispatcher,
  dispatcherItems,
  listDispatchers,
  type ToolInfo,
} from '../../api/procedures.api';
import { ArgsForm, buildArgs, emptyArgs, type ArgsState } from './ArgsForm';
import { RunSteps } from './RunSteps';

export default function BuildView() {
  const { tools, toolsError, toolsLoading, reloadTools, watch, watched, refreshWatched } = useProcedures();
  const [runId, setRunId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [picked, setPicked] = useState<string>('');
  const [args, setArgs] = useState<ArgsState>(emptyArgs());
  const [saveMap, setSaveMap] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => reloadTools(), [reloadTools]);

  const tool: ToolInfo | null = useMemo(
    () => tools.find((t) => t.name === picked) ?? null,
    [tools, picked],
  );

  const hits = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = q
      ? tools.filter((t) => t.name.includes(q) || (t.backend ?? '').includes(q))
      : tools;
    return base.slice(0, 60);
  }, [tools, query]);

  const begin = async () => {
    setErr(null);
    try {
      const r = await startEmptyRun('절차');
      setRunId(r.run_id);
      watch(r.run_id);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  const execute = async () => {
    if (!runId || !tool) return;
    setBusy(true);
    setErr(null);
    try {
      const save = parseSave(saveMap);
      await runStep(runId, {
        backend: tool.backend ?? '',
        tool: tool.name.replace(new RegExp(`^${(tool.backend ?? '').replace(/-/g, '')}_`), ''),
        args: buildArgs(tool, args),
        save,
        schema_fp: tool.schema_fp,
      });
      await refreshWatched();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const done = watched?.steps.filter((s) => s.state === 'done') ?? [];

  return (
    <div style={{ display: 'grid', gap: '1.2rem' }}>
      {err && <ErrorBanner message={err} />}
      {toolsError && <ErrorBanner message={toolsError} />}

      {!runId ? (
        <section style={card}>
          <h2 style={h2}>도구를 한 단계씩 돌립니다</h2>
          <p style={{ color: 'var(--muted)', marginTop: 0 }}>
            절차가 없어도 시작할 수 있습니다. 절차 기능이 <b>과정을 전부 기록</b>하고, 끝나면
            그대로 절차로 굳혀 다음 과제에서 값만 바꿔 재생합니다.
          </p>
          <button type="button" onClick={begin} style={primary}>
            시작하기
          </button>
        </section>
      ) : (
        <>
          <section style={card}>
            <h2 style={h2}>단계 추가</h2>
            <div style={{ display: 'grid', gap: '0.7rem' }}>
              <label style={{ display: 'grid', gap: '0.25rem' }}>
                <span style={lbl}>
                  도구 {toolsLoading && <span style={{ color: 'var(--muted)' }}>불러오는 중…</span>}
                  <span style={{ color: 'var(--muted)' }}> · 내가 부를 수 있는 것만 보입니다</span>
                </span>
                <input
                  style={input}
                  placeholder="이름·앱으로 검색"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <select style={input} value={picked} onChange={(e) => { setPicked(e.target.value); setArgs(emptyArgs()); }}>
                  <option value="">({tools.length}종 중에서 고르세요)</option>
                  {hits.map((t) => (
                    <option key={t.name} value={t.name}>
                      {t.name} {t.backend ? `— ${t.backend}` : ''}
                    </option>
                  ))}
                </select>
              </label>

              {tool && <TwoStage tool={tool} />}

              <ArgsForm tool={tool} state={args} onChange={setArgs} />

              <label style={{ display: 'grid', gap: '0.25rem' }}>
                <span style={lbl}>
                  결과에서 뽑기 <span style={{ color: 'var(--muted)' }}>선택 · 한 줄에 <code>이름 = 경로</code></span>
                </span>
                <textarea
                  rows={2}
                  style={{ ...input, fontFamily: 'var(--cx-mono, monospace)' }}
                  placeholder={'loads = equivalent_loads\nparts = parts[0].name'}
                  value={saveMap}
                  onChange={(e) => setSaveMap(e.target.value)}
                />
                <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>
                  뽑은 값은 다음 단계에서 <code>{'{{이름}}'}</code> 으로 씁니다.
                </span>
              </label>

              <button type="button" onClick={execute} disabled={busy || !tool} style={primary}>
                {busy ? '실행 중…' : '이 단계 실행'}
              </button>
            </div>
          </section>

          <section style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <h2 style={h2}>기록</h2>
              <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
                {watched?.state ?? '…'} · 단계 {watched?.steps.length ?? 0}
              </span>
            </div>
            {watched && <RunSteps run={watched} onChanged={refreshWatched} />}
            {Object.keys(watched?.inputs ?? {}).length > 0 && (
              <details style={{ marginTop: '0.7rem' }}>
                <summary style={{ color: 'var(--muted)', fontSize: '0.8rem', cursor: 'pointer' }}>
                  뽑아 둔 값
                </summary>
                <pre style={pre}>{JSON.stringify(watched?.inputs, null, 2)}</pre>
              </details>
            )}
          </section>

          {done.length > 0 && <SaveAsProcedure runId={runId} steps={done} />}
        </>
      )}
    </div>
  );
}

function SaveAsProcedure({
  runId,
  steps,
}: {
  runId: string;
  steps: { backend: string; tool: string; args: Record<string, unknown> }[];
}) {
  const [title, setTitle] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // 어느 인자가 변수인지 사람이 표시한다 — 자동으로 정하지 않는다.
  const leaves = useMemo(() => collectLeaves(steps), [steps]);
  const [vars, setVars] = useState<Record<string, string>>({});

  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      const defs = Object.entries(vars)
        .filter(([, name]) => name.trim())
        .map(([, name]) => ({ key: name.trim(), label: name.trim(), type: 'string' as const, required: true }));
      const patched: StepDef[] = steps.map((s, i) => ({
        backend: s.backend,
        tool: s.tool,
        args: substituteLeaves(s.args, i, vars),
      }));
      const r = await saveAsProcedure(runId, title || '이름 없는 절차', defs, patched);
      setMsg(`저장했습니다 — 판본 ${r.version_no}${r.warnings.length ? ` · 경고 ${r.warnings.length}건` : ''}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section style={card}>
      <h2 style={h2}>절차로 저장</h2>
      <p style={{ color: 'var(--muted)', marginTop: 0, fontSize: '0.85rem' }}>
        성공한 단계 {steps.length}개를 절차로 굳힙니다. <b>과제마다 바뀌는 값에 이름을 붙이면</b>{' '}
        다음에는 그 값만 채워 한 번에 재생합니다. 이름을 안 붙인 인자는 <b>상수로 박힙니다</b> —
        과제 ID·보고서 본문이 그대로 공유됩니다.
      </p>
      {err && <ErrorBanner message={err} />}
      {msg && <p style={{ color: '#4caf7d', fontSize: '0.85rem' }}>{msg}</p>}

      <label style={{ display: 'grid', gap: '0.25rem', marginBottom: '0.7rem' }}>
        <span style={lbl}>절차 이름</span>
        <input style={input} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 적층 굴곡 수명" />
      </label>

      <table style={{ width: '100%', fontSize: '0.82rem', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: 'var(--muted)', textAlign: 'left' }}>
            <th style={th}>단계</th>
            <th style={th}>인자</th>
            <th style={th}>값</th>
            <th style={th}>변수 이름(비우면 상수)</th>
          </tr>
        </thead>
        <tbody>
          {leaves.map((l) => (
            <tr key={l.id}>
              <td style={td}>{l.stepIx + 1}</td>
              <td style={td}>
                <code>{l.path}</code>
              </td>
              <td style={{ ...td, color: 'var(--muted)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {String(l.value).slice(0, 60)}
              </td>
              <td style={td}>
                <input
                  style={{ ...input, padding: '0.25rem 0.4rem' }}
                  value={vars[l.id] ?? ''}
                  placeholder="예: project_id"
                  onChange={(e) => setVars({ ...vars, [l.id]: e.target.value })}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button type="button" onClick={save} disabled={busy} style={{ ...primary, marginTop: '0.8rem' }}>
        {busy ? '저장 중…' : '절차로 저장'}
      </button>
    </section>
  );
}

type Leaf = { id: string; stepIx: number; path: string; value: unknown };

/** 인자 트리의 **문자열·수치 잎**만 변수 후보로 낸다. 치환도 잎 단위다(PLAN §2). */
function collectLeaves(steps: { args: Record<string, unknown> }[]): Leaf[] {
  const out: Leaf[] = [];
  steps.forEach((s, ix) => {
    walk(s.args, '', (path, value) => out.push({ id: `${ix}|${path}`, stepIx: ix, path, value }));
  });
  return out;
}

function walk(node: unknown, trail: string, hit: (path: string, v: unknown) => void) {
  if (node === null || node === undefined) return;
  if (typeof node === 'object') {
    if (Array.isArray(node)) node.forEach((v, i) => walk(v, `${trail}[${i}]`, hit));
    else
      Object.entries(node as Record<string, unknown>).forEach(([k, v]) =>
        walk(v, trail ? `${trail}.${k}` : k, hit),
      );
    return;
  }
  if (typeof node === 'string' || typeof node === 'number') hit(trail, node);
}

function substituteLeaves(args: Record<string, unknown>, stepIx: number, vars: Record<string, string>) {
  const clone: unknown = JSON.parse(JSON.stringify(args));
  const apply = (node: unknown, trail: string): unknown => {
    if (node === null || node === undefined) return node;
    if (Array.isArray(node)) return node.map((v, i) => apply(v, `${trail}[${i}]`));
    if (typeof node === 'object') {
      const o: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
        o[k] = apply(v, trail ? `${trail}.${k}` : k);
      }
      return o;
    }
    const name = vars[`${stepIx}|${trail}`]?.trim();
    return name ? `{{${name}}}` : node;
  };
  return apply(clone, '') as Record<string, unknown>;
}

function parseSave(text: string): Record<string, string> | null {
  const out: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    const [k, ...rest] = t.split('=');
    const path = rest.join('=').trim();
    if (k.trim() && path) out[k.trim()] = path;
  }
  return Object.keys(out).length ? out : null;
}

const card: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 6,
  background: 'var(--card)',
  padding: '1rem 1.1rem',
};
const h2: React.CSSProperties = { color: 'var(--fg)', fontSize: '1.02rem', margin: '0 0 0.5rem' };
const lbl: React.CSSProperties = { fontSize: '0.8rem', color: 'var(--fg)' };
const input: React.CSSProperties = {
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
  justifySelf: 'start',
};
const pre: React.CSSProperties = {
  background: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  padding: '0.5rem',
  fontSize: '0.78rem',
  overflowX: 'auto',
  color: 'var(--fg)',
};
const th: React.CSSProperties = { padding: '0.3rem 0.4rem', borderBottom: '1px solid var(--border)' };
const td: React.CSSProperties = { padding: '0.3rem 0.4rem', borderBottom: '1px solid var(--border)', color: 'var(--fg)' };

/** 이 도구가 **2단**이면 뒤에 무엇이 있는지 보여 준다(PLAN §9-4).
 *
 * `run_operation` 하나 뒤에 연산 47개가 있는데 화면에는 도구 하나로만 보인다. 그러면
 * `operation` 에 무엇을 적을지 알 방법이 없다 — 그게 이 칸이 있는 이유다.
 */
function TwoStage({ tool }: { tool: ToolInfo }) {
  const [reg, setReg] = useState<Dispatcher[] | null>(null);
  const [items, setItems] = useState<{ name: string; summary: string; category?: string }[] | null>(null);
  const [pickedItem, setPickedItem] = useState('');
  const [schema, setSchema] = useState<Record<string, unknown> | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    listDispatchers().then((r) => setReg(r.dispatchers)).catch(() => setReg([]));
  }, []);

  // 노출 이름은 앱이 겹치면 접두어가 붙는다 — 등록부의 tool 로 끝나는지로 본다
  const d = (reg ?? []).find(
    (x) => tool.name === x.tool || tool.name.endsWith(`_${x.tool}`),
  );

  useEffect(() => {
    setItems(null);
    setPickedItem('');
    setSchema(null);
    setNote(null);
    if (!d) return;
    dispatcherItems(d.backend, d.tool)
      .then((r) => { setItems(r.items ?? []); setNote(r.note ?? null); })
      .catch(() => setItems([]));
  }, [d]);

  if (!d) return null;

  return (
    <section style={{ border: '1px solid #d9a441', borderRadius: 6, padding: '0.6rem',
                      background: 'rgba(217,164,65,0.07)', display: 'grid', gap: '0.4rem' }}>
      <strong style={{ color: '#d9a441', fontSize: '0.86rem' }}>
        이 도구는 뒤에 여럿이 있습니다{items ? ` — ${items.length}개` : ''}
      </strong>
      <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>
        <code>{d.selector}</code> 로 고르고 <code>{d.payload}</code> 에 그 인자를 넣습니다.
        고르면 <b>그 계약</b>을 보여 주고, 저장할 때 <b>속 인자까지 검증</b>합니다.
      </span>
      {note && <span style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>{note}</span>}
      {!items && <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>불러오는 중…</span>}
      {!!items?.length && (
        <select
          style={input}
          value={pickedItem}
          onChange={(e) => {
            const n = e.target.value;
            setPickedItem(n);
            setSchema(null);
            if (!n) return;
            dispatcherItems(d.backend, d.tool, n)
              .then((r) => setSchema((r.schema as Record<string, unknown>) ?? null))
              .catch(() => setSchema(null));
          }}
        >
          <option value="">({items.length}개 중에서 — {d.selector})</option>
          {items.map((it) => (
            <option key={it.name} value={it.name}>
              {it.name}{it.category ? ` [${it.category}]` : ''} — {it.summary.slice(0, 60)}
            </option>
          ))}
        </select>
      )}
      {pickedItem && (
        <div style={{ fontSize: '0.76rem', color: 'var(--muted)' }}>
          {schema ? (
            <>
              <b style={{ color: 'var(--fg)' }}>{pickedItem} 의 인자</b> —{' '}
              {Object.keys((schema.properties as Record<string, unknown>) ?? {}).map((k) => (
                <code key={k} style={{ marginRight: '0.3rem' }}>
                  {k}{((schema.required as string[]) ?? []).includes(k) ? '*' : ''}
                </code>
              ))}
              <div style={{ marginTop: '0.2rem' }}>
                <code>{d.payload}</code> 칸에 이 키들로 JSON 을 넣으세요.
              </div>
            </>
          ) : (
            <span>계약을 못 받았습니다 — 이름이 틀렸거나 그 앱이 지금 안 붙어 있습니다.</span>
          )}
        </div>
      )}
    </section>
  );
}
