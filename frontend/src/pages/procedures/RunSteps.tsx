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
  pickCandidates,
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
  pending: 'var(--fg-muted)',
  running: 'var(--info)',
  done: 'var(--ok)',
  failed: 'var(--danger)',
  unknown: 'var(--warn)',
  skipped: 'var(--fg-muted)',
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
    <ol className="pr-list">
      {run.steps.map((s) => (
        <StepCard key={s.ix} run={run} step={s} onChanged={onChanged} />
      ))}
      {run.steps.length === 0 && (
        <li className="pr-muted">아직 돌린 단계가 없습니다.</li>
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
  // 여럿이 한 인자인 자리(태그 적용 등) — 고른 것을 **목록 하나**로 넘긴다. 펼치기(배치)와 다르다:
  // 펼치기는 실행 N 개를 만들고, 이쪽은 한 실행이 한 번 부른다.
  const askingMany =
    run.state === 'gated' && step.stage === 'select:ask_many' && !!cands?.length;
  const [chosen, setChosen] = useState<number[]>([]);
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
      className="pr-step"
      style={{ borderLeftColor: STATE_COLOR[step.state] ?? 'var(--border)' }}
    >
      <div className="pr-head">
        <span className="pr-meta">{step.ix + 1}</span>
        <code className="pr-fg pr-strong">{step.tool}</code>
        <span className="pr-note">{step.backend}</span>
        <span className="pr-fs-12" style={{ color: STATE_COLOR[step.state] }}>
          {STATE_LABEL[step.state] ?? step.state}
        </span>
        {step.duration_ms != null && (
          <span className="pr-note">
            {(step.duration_ms / 1000).toFixed(1)}초
          </span>
        )}
        {step.truncated === 1 && (
          <span className="pr-warn pr-fs-12">결과가 커서 프리뷰만 남음</span>
        )}
      </div>

      {asking && (
        <div className="pr-callout pr-mt-2">
          <strong className="pr-warn">룰이 {cands!.length}개를 골랐습니다</strong>
          <p className="pr-meta pr-m-0 pr-mt-1 pr-mb-2">
            하나를 고르면 <code>{into}</code> 에 담고 이어서 돕니다. 첫 번째를 자동으로 집지
            않습니다 — <b>엉뚱한 대상으로 돌아도 결과는 정상으로 나오기 때문입니다.</b>
          </p>
          <div className="pr-row">
            {/* "해당하는 것 전부" 가 답인 물음이 있다 — 하나만 고르면 나머지는 버려진다 */}
            <button
              type="button"
              disabled={busy}
              className="pr-warn-btn"
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
              {cands!.length}개 전부 돌리기 <span className="pr-dim">(계획)</span>
            </button>
            <span className="pr-note">또는 하나만 —</span>
            {cands!.map((c) => (
              <button
                key={c.i}
                type="button"
                disabled={busy}
                className="pr-cand-btn"
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

      {askingMany && (
        <div className="pr-callout pr-mt-2">
          <strong className="pr-warn">{cands!.length}개 중에서 고르세요</strong>
          <p className="pr-meta pr-m-0 pr-mt-1 pr-mb-2">
            고른 것을 <code>{into}</code> 에 <b>목록으로</b> 담아 다음 단계가 한 번에 부릅니다.
            고르지 않은 것은 적용되지 않습니다.
          </p>
          <div className="pr-cands">
            {cands!.map((c) => (
              <label key={c.i} className="pr-cand">
                <input
                  type="checkbox"
                  checked={chosen.includes(c.i)}
                  disabled={busy}
                  onChange={() =>
                    setChosen((prev) =>
                      prev.includes(c.i) ? prev.filter((i) => i !== c.i) : [...prev, c.i],
                    )
                  }
                />{' '}
                {c.label || String(c.value)}
              </label>
            ))}
          </div>
          <div className="pr-row pr-mt-2">
            <button
              type="button"
              disabled={busy || chosen.length === 0}
              className="pr-warn-btn"
              style={{
                background: chosen.length ? 'var(--warn-bg)' : 'var(--bg)',
                cursor: chosen.length ? 'pointer' : 'not-allowed',
                opacity: chosen.length ? 1 : 0.5,
              }}
              onClick={async () => {
                setBusy(true);
                setErr(null);
                try {
                  const picked = cands!.filter((c) => chosen.includes(c.i)).map((c) => c.value);
                  await pickCandidates(run.id, step.ix, picked);
                  onChanged();
                } catch (e) {
                  setErr((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              고른 {chosen.length}개로 계속
            </button>
            <span className="pr-note">
              다음 단계가 사람 확인을 받는 단계면 거기서 한 번 더 멈춥니다.
            </span>
          </div>
        </div>
      )}

      {gated && (
        <div className="pr-callout pr-mt-2">
          <strong className="pr-warn">사람 확인이 필요합니다</strong>
          <p className="pr-meta pr-m-0 pr-mt-1 pr-mb-1">
            되돌리기 어려운 단계입니다. 아래는 <b>치환이 끝난 실제 인자</b>입니다 — 확인 뒤 인자가
            바뀌면 이 확인은 무효가 됩니다.
          </p>
          <pre className="pr-pre pr-step-pre">{JSON.stringify(step.args, null, 2)}</pre>
          <button type="button" onClick={confirm} disabled={busy} className="btn-primary pr-btn">
            {busy ? '확인 중…' : '확인하고 계속'}
          </button>
        </div>
      )}

      {step.error && (
        <div className="pr-mt-2">
          <span className="pr-danger pr-fs-14">{step.error}</span>
          {step.stage && (
            <span className="pr-note"> ({step.stage})</span>
          )}
          {step.state === 'unknown' && WRITEY.test(step.tool) && (
            <p className="pr-warn pr-fs-13 pr-m-0 pr-mt-1">
              ⚠ 쓰기 단계입니다. 실제로 만들어졌을 수 있으니 <b>확인한 뒤에</b> 다시 실행하세요.
            </p>
          )}
        </div>
      )}

      {Array.isArray(warnings) && warnings.length > 0 && (
        <ul className="pr-bullets pr-mt-2 pr-warn pr-fs-13">
          {warnings.slice(0, 5).map((w, i) => (
            <li key={i}>{String(w)}</li>
          ))}
        </ul>
      )}

      <div className="pr-actions pr-mt-2">
        <button type="button" className="pr-link-btn pr-fs-12" onClick={() => setShowArgs((v) => !v)}>
          {showArgs ? '인자 접기' : '인자 보기'}
        </button>
        {step.result_bytes != null && (
          <button type="button" className="pr-link-btn pr-fs-12" onClick={body ? () => setBody(null) : loadBody}>
            {body ? '결과 접기' : `결과 보기 (${fmtBytes(step.result_bytes)})`}
          </button>
        )}
      </div>
      {showArgs && <pre className="pr-pre pr-step-pre">{JSON.stringify(step.args, null, 2)}</pre>}
      {body && <pre className="pr-pre pr-step-pre pr-pre-tall">{body}</pre>}
      {err && <p className="pr-danger pr-fs-13">{err}</p>}
    </li>
  );
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n}B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}KB`;
  return `${(n / 1024 / 1024).toFixed(1)}MB`;
}
