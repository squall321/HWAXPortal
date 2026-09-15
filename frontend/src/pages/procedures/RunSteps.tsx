// 실행의 단계 목록 — 게이트 카드·실패 카드·결과 펼치기
//
// 실패 카드는 포털 관례(client.ts errorDetail)를 따른다 — 한 줄로 추리고 원문은 접어 둔다.
// pydantic 덤프를 그대로 띄우지 않고, 사용자가 넣은 값(input_value)은 화면에 안 쓴다.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ackGate,
  fanOut,
  pickCandidate,
  stepResult,
  type RunDetail,
  type StepRow,
} from '../../api/procedures.api';

const STATE_LABEL: Record<string, string> = {
  pending: '대기',
  running: '도는 중',
  done: '완료',
  failed: '실패',
  unknown: '알 수 없음',
  skipped: '건너뜀',
};

const STATE_COLOR: Record<string, string> = {
  pending: 'var(--muted)',
  running: '#7aa2ff',
  done: '#4caf7d',
  failed: '#e5534b',
  unknown: '#d9a441',
  skipped: 'var(--muted)',
};

/** unknown 은 실패가 아니다 — **실행 여부를 모른다**. 쓰기 단계면 사람이 확인해야 한다. */
const WRITEY = /^(create_|submit_|publish_|ingest_|register_|upload_|add_|run_)/;

export function RunSteps({
  run,
  onChanged,
}: {
  run: RunDetail;
  onChanged: () => void;
}) {
  return (
    <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '0.6rem' }}>
      {run.steps.map((s) => (
        <StepCard key={s.ix} run={run} step={s} onChanged={onChanged} />
      ))}
      {run.steps.length === 0 && (
        <li style={{ color: 'var(--muted)' }}>아직 돌린 단계가 없습니다.</li>
      )}
    </ol>
  );
}

function StepCard({
  run,
  step,
  onChanged,
}: {
  run: RunDetail;
  step: StepRow;
  onChanged: () => void;
}) {
  const [body, setBody] = useState<string | null>(null);
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showArgs, setShowArgs] = useState(false);

  const gated = run.state === 'gated' && step.stage === 'gate' && step.state === 'pending';
  // 룰이 여럿을 골라 멈춘 자리 — **고르기는 확인과 다르다.** 확인은 "이대로 해라",
  // 이쪽은 "이것으로 해라". 첫 번째를 조용히 집지 않으려면 이 화면이 있어야 한다.
  const cands = (step.notes?.candidates ?? null) as
    | { i: number; label: string; value: unknown }[]
    | null;
  const asking = run.state === 'gated' && step.stage === 'select:ask' && !!cands?.length;
  const into = (step.notes?.pick_into ?? '') as string;
  const notes = step.notes ?? {};
  const warnings = (notes.warnings ?? notes.warning) as unknown;

  const confirm = async () => {
    setBusy(true);
    setErr(null);
    try {
      await ackGate(run.id, step.ix, step.args_sha256);
      onChanged();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loadBody = async () => {
    try {
      setBody((await stepResult(run.id, step.ix)).text);
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <li
      style={{
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${STATE_COLOR[step.state] ?? 'var(--border)'}`,
        borderRadius: 4,
        background: 'var(--card)',
        padding: '0.7rem 0.85rem',
      }}
    >
      <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{step.ix + 1}</span>
        <code style={{ color: 'var(--fg)', fontWeight: 600 }}>{step.tool}</code>
        <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{step.backend}</span>
        <span style={{ color: STATE_COLOR[step.state], fontSize: '0.78rem' }}>
          {STATE_LABEL[step.state] ?? step.state}
        </span>
        {step.duration_ms != null && (
          <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>
            {(step.duration_ms / 1000).toFixed(1)}초
          </span>
        )}
        {step.truncated === 1 && (
          <span style={{ color: '#d9a441', fontSize: '0.75rem' }}>결과가 커서 프리뷰만 남음</span>
        )}
      </div>

      {asking && (
        <div
          style={{
            marginTop: '0.6rem',
            padding: '0.7rem',
            borderRadius: 6,
            border: '1px solid #d9a441',
            background: 'rgba(217,164,65,0.08)',
          }}
        >
          <strong style={{ color: '#d9a441' }}>룰이 {cands!.length}개를 골랐습니다</strong>
          <p style={{ color: 'var(--muted)', fontSize: '0.82rem', margin: '0.3rem 0 0.5rem' }}>
            하나를 고르면 <code>{into}</code> 에 담고 이어서 돕니다. 첫 번째를 자동으로 집지
            않습니다 — <b>엉뚱한 대상으로 돌아도 결과는 정상으로 나오기 때문입니다.</b>
          </p>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
            {/* "해당하는 것 전부" 가 답인 물음이 있다 — 하나만 고르면 나머지는 버려진다 */}
            <button
              type="button"
              disabled={busy}
              style={{
                background: 'rgba(217,164,65,0.18)', color: 'var(--fg)',
                border: '1px solid #d9a441', borderRadius: 4,
                padding: '0.3rem 0.7rem', cursor: 'pointer', fontSize: '0.82rem',
              }}
              onClick={async () => {
                setBusy(true);
                setErr(null);
                try {
                  const b = await fanOut(run.id, step.ix, 'plan');
                  nav(`/procedures/batches/${encodeURIComponent(b.batch_id)}`);
                } catch (e) {
                  setErr((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {cands!.length}개 전부 돌리기 <span style={{ opacity: 0.7 }}>(계획)</span>
            </button>
            <span style={{ color: 'var(--muted)', fontSize: '0.74rem' }}>또는 하나만 —</span>
            {cands!.map((c) => (
              <button
                key={c.i}
                type="button"
                disabled={busy}
                style={{
                  background: 'var(--bg)',
                  color: 'var(--fg)',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  padding: '0.3rem 0.7rem',
                  cursor: 'pointer',
                  fontSize: '0.82rem',
                }}
                onClick={async () => {
                  setBusy(true);
                  setErr(null);
                  try {
                    await pickCandidate(run.id, step.ix, c.value);
                    onChanged();
                  } catch (e) {
                    setErr((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {c.label || String(c.value)}
              </button>
            ))}
          </div>
        </div>
      )}

      {gated && (
        <div
          style={{
            marginTop: '0.6rem',
            border: '1px solid #d9a441',
            borderRadius: 4,
            padding: '0.6rem 0.7rem',
            background: 'rgba(217,164,65,0.08)',
          }}
        >
          <strong style={{ color: '#d9a441' }}>사람 확인이 필요합니다</strong>
          <p style={{ color: 'var(--muted)', fontSize: '0.82rem', margin: '0.35rem 0' }}>
            되돌리기 어려운 단계입니다. 아래는 <b>치환이 끝난 실제 인자</b>입니다 — 확인 뒤 인자가
            바뀌면 이 확인은 무효가 됩니다.
          </p>
          <pre style={preStyle}>{JSON.stringify(step.args, null, 2)}</pre>
          <button type="button" onClick={confirm} disabled={busy} style={primaryBtn}>
            {busy ? '확인 중…' : '확인하고 계속'}
          </button>
        </div>
      )}

      {step.error && (
        <div style={{ marginTop: '0.5rem' }}>
          <span style={{ color: '#e5534b', fontSize: '0.85rem' }}>{step.error}</span>
          {step.stage && (
            <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}> ({step.stage})</span>
          )}
          {step.state === 'unknown' && WRITEY.test(step.tool) && (
            <p style={{ color: '#d9a441', fontSize: '0.8rem', margin: '0.3rem 0 0' }}>
              ⚠ 쓰기 단계입니다. 실제로 만들어졌을 수 있으니 <b>확인한 뒤에</b> 다시 실행하세요.
            </p>
          )}
        </div>
      )}

      {Array.isArray(warnings) && warnings.length > 0 && (
        <ul style={{ margin: '0.45rem 0 0', paddingLeft: '1.1rem', color: '#d9a441', fontSize: '0.8rem' }}>
          {warnings.slice(0, 5).map((w, i) => (
            <li key={i}>{String(w)}</li>
          ))}
        </ul>
      )}

      <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.5rem' }}>
        <button type="button" style={linkBtn} onClick={() => setShowArgs((v) => !v)}>
          {showArgs ? '인자 접기' : '인자 보기'}
        </button>
        {step.result_bytes != null && (
          <button type="button" style={linkBtn} onClick={body ? () => setBody(null) : loadBody}>
            {body ? '결과 접기' : `결과 보기 (${fmtBytes(step.result_bytes)})`}
          </button>
        )}
      </div>
      {showArgs && <pre style={preStyle}>{JSON.stringify(step.args, null, 2)}</pre>}
      {body && <pre style={{ ...preStyle, maxHeight: 360 }}>{body}</pre>}
      {err && <p style={{ color: '#e5534b', fontSize: '0.8rem' }}>{err}</p>}
    </li>
  );
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n}B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}KB`;
  return `${(n / 1024 / 1024).toFixed(1)}MB`;
}

const preStyle: React.CSSProperties = {
  background: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  padding: '0.5rem',
  fontSize: '0.78rem',
  overflowX: 'auto',
  maxHeight: 220,
  margin: '0.45rem 0 0',
  color: 'var(--fg)',
};

const primaryBtn: React.CSSProperties = {
  background: 'var(--accent)',
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  padding: '0.4rem 0.9rem',
  cursor: 'pointer',
  fontSize: '0.85rem',
};

const linkBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'var(--muted)',
  cursor: 'pointer',
  padding: 0,
  fontSize: '0.78rem',
  textDecoration: 'underline',
};
