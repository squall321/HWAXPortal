// 분석 루틴 고르기 — 내 루틴 목록 → 하나를 고르면 단계 준비도와 입력 칸 → '켜기'. 켜 둔 루틴은 다음 발화에 실린다(docs/analysis-routines R3 §6)
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getRoutine,
  listRoutines,
  routineReadiness,
  type RoutineDetail,
  type RoutineRow,
  type RoutineVar,
  type StepReadiness,
} from '../../api/routines.api';
import { useChat, type ArmedRoutine } from '../../state/ChatContext';
import { Modal } from '../ui/Modal';
import { InlineMd } from './renderers/TextBlock';
import { READY_LABEL, SR_ONLY, chain } from './routine';

// 루틴 보기(getRoutine)는 절차의 Var 를 그대로 싣는다 — 목록 형(RoutineVar)에 없는 선택지 · 예시도 온다(models.py Var)
type VarDef = RoutineVar & { values?: string[] | null; example?: unknown };

/** 예시를 칸에 넣을 문자열로 — 객체 · 목록은 고칠 수 있게 들여쓴 JSON 이다(절차 화면과 같다). */
function exampleText(v: unknown): string {
  return typeof v === 'string' ? v : JSON.stringify(v, null, 2);
}

/** 켜 둔 입력을 칸 값으로 되돌린다 — 다시 열어 고칠 때. */
function asField(v: unknown): string {
  return v === null || v === undefined ? '' : typeof v === 'string' ? v : JSON.stringify(v);
}

export function RoutinePicker({ onClose }: { onClose: () => void }) {
  const { armedRoutine, setArmedRoutine } = useChat();
  const [rows, setRows] = useState<RoutineRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // 고른 루틴 — 켜 둔 것이 있으면 그 입력 칸부터 연다(고쳐서 다시 켠다)
  const [pick, setPick] = useState<string | null>(armedRoutine?.id ?? null);
  // 고른 줄은 목록과 함께 사라져 포커스가 문서로 떨어지고 아무것도 들리지 않았다(R3 반대 검토 2차 #17) — 무엇을 열었는지 낭독기 줄(SR_ONLY)로
  // 말하고, 칸은 다 불러온 뒤 '← 목록' 이 포커스를 받는다(RoutineForm). 목록으로 돌아오면 방금 본 루틴의 줄이 포커스를 받는다(backTo — 그 줄이 그려질 때).
  const [said, setSaid] = useState('');
  const [backTo, setBackTo] = useState<string | null>(null);
  const focusRow = useCallback((el: HTMLButtonElement | null) => el?.focus(), []);
  // 배경을 눌러 닫기는 누름과 뗌이 둘 다 배경에서일 때만이다 — 칸 안에서 끌어 글을 고르다 카드 밖에서 떼면 브라우저가 click 을 둘의 공통
  // 조상(배경)에 보내 창이 닫히고 적던 값이 다 사라졌다(R3 반대 검토 #33). × · 끄기 · Esc 는 그대로 닫는다.
  const press = useRef({ down: false, up: false });

  useEffect(() => {
    let alive = true;
    listRoutines()
      .then((r) => alive && setRows(r.routines))
      .catch((e: Error) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <Modal onClose={onClose} label="분석 루틴 고르기">
      <div
        className="rp-backdrop"
        onMouseDown={(e) => {
          press.current = { down: e.target === e.currentTarget, up: false };
        }}
        onMouseUp={(e) => {
          press.current.up = e.target === e.currentTarget;
        }}
        onClick={() => {
          const { down, up } = press.current;
          press.current = { down: false, up: false };
          if (down && up) onClose();
        }}
      >
        <div className="rp-card" onClick={(e) => e.stopPropagation()}>
          <div className="rp-head">
            <span className="rp-title">분석 루틴</span>
            <button type="button" className="rp-x" onClick={onClose} aria-label="닫기">
              ×
            </button>
          </div>
          {armedRoutine && (
            <div className="rp-current">
              <span className="rp-current-k">지금 켜 둔 루틴</span>
              <b title={armedRoutine.title}>{armedRoutine.title}</b>
              <button
                type="button"
                className="rp-clear"
                onClick={() => {
                  setArmedRoutine(null);
                  onClose();
                }}
              >
                끄기
              </button>
            </div>
          )}
          {pick ? (
            <RoutineForm
              key={pick}
              id={pick}
              initial={armedRoutine?.id === pick ? armedRoutine.inputs : undefined}
              rejected={armedRoutine?.id === pick ? armedRoutine.reason : undefined}
              onBack={() => {
                setBackTo(pick);
                setSaid('');
                setPick(null);
              }}
              onArm={(r) => {
                setArmedRoutine(r);
                onClose();
              }}
            />
          ) : (
            <div className="rp-body">
              {!rows && !err && <p className="rp-empty">루틴 목록을 불러오는 중…</p>}
              {err && <p className="rp-err" role="alert">목록을 불러오지 못했습니다 — {err}</p>}
              {rows && rows.length === 0 && (
                <p className="rp-empty">
                  아직 루틴이 없습니다. <Link to="/procedures/routines/new">절차 › 루틴</Link> 에서 내 권한의 플랫폼을 순서대로 엮어
                  만듭니다.
                </p>
              )}
              {rows && rows.length > 0 && (
                <ul className="rp-list">
                  {rows.map((r) => (
                    <li key={r.id}>
                      <button
                        type="button"
                        ref={r.id === backTo ? focusRow : undefined}
                        className={`rp-row${armedRoutine?.id === r.id ? ' is-on' : ''}`}
                        onClick={() => {
                          setPick(r.id);
                          setSaid(`「${r.title}」 을(를) 열었습니다 — 단계와 이번에 채울 값을 불러옵니다.`);
                        }}
                      >
                        <span className="rp-row-title">{r.title}</span>
                        <span className="rp-row-chain">{chain(r.steps)}</span>
                        <span className="rp-row-meta">
                          판 {r.latest_version}
                          {!r.mine && ' · 공유받음'}
                          {armedRoutine?.id === r.id && ' · 켜 둠'}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <p role="status" style={SR_ONLY}>
            {said}
          </p>
        </div>
      </div>
    </Modal>
  );
}

/** 고른 루틴 하나 — 단계마다 내 준비도와 이번에 채울 값. 준비도는 게이트웨이에 묻는다(없으면 '모름' — 켜기를 막지 않는다).
 *  rejected — 이 값으로 보낸 시작이 실행을 만들지 못한 까닭(실패한 턴이 값을 되살려 켜 둔 것, ChatContext rearm). */
function RoutineForm({
  id,
  initial,
  rejected,
  onBack,
  onArm,
}: {
  id: string;
  initial?: Record<string, unknown>;
  rejected?: string;
  onBack: () => void;
  onArm: (r: ArmedRoutine) => void;
}) {
  const [d, setD] = useState<RoutineDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ready, setReady] = useState<StepReadiness[] | null>(null);
  const [readyErr, setReadyErr] = useState(false);
  // 값은 문자열 그대로 보낸다 — 형은 포털이 실행을 만들 때 맞춘다(_coerce). 예시는 '예시 넣기' 를 눌렀을 때만 들어간다.
  const [vals, setVals] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(initial ?? {}).map(([k, v]) => [k, asField(v)])),
  );

  useEffect(() => {
    let alive = true;
    getRoutine(id)
      .then((got) => {
        if (!alive) return;
        setD(got);
        routineReadiness(id, got.version.version_no)
          .then((r) => alive && setReady(r.steps))
          .catch(() => alive && setReadyErr(true));
      })
      .catch((e: Error) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [id]);

  // 목록에서 고른 줄이 사라져 포커스가 문서(또는 창 틀)로 떨어졌다 — 다 불러오면(못 불러와도) '← 목록' 으로 옮긴다. 창을 막 열어 닫기(×)에 있거나
  // 사람이 그새 창 안의 다른 곳으로 옮겼으면 그대로 둔다.
  const backRef = useRef<HTMLButtonElement>(null);
  const settled = Boolean(d || err);
  useEffect(() => {
    if (!settled) return;
    const a = document.activeElement;
    if (!a || a === document.body || a.tagName === 'DIALOG') backRef.current?.focus();
  }, [settled]);

  if (err)
    return (
      <div className="rp-body">
        <button type="button" className="rp-back" ref={backRef} onClick={onBack}>
          ← 목록
        </button>
        <p className="rp-err" role="alert">루틴을 불러오지 못했습니다 — {err}</p>
      </div>
    );
  if (!d)
    return (
      <div className="rp-body">
        <p className="rp-empty">루틴을 불러오는 중…</p>
      </div>
    );

  const spec = d.version.spec;
  const vars = (spec.vars ?? []) as VarDef[];
  const title = spec.title || d.routine.title;
  const byStep = new Map((ready ?? []).map((r) => [r.step, r]));
  // 필수(기본 필수)인데 비어 있는 칸 — 포털이 422 로 막는 것을 켜기 전에 말한다
  const missing = vars.filter((v) => v.required !== false && !(vals[v.key] ?? '').trim());
  // 지난 시작이 실행을 만들지 못한 까닭 — 글이 이름을 댄 칸(포털 _coerce 의 '입력 <이름>(<키>) …') 아래에, 없으면 단계 위에 보인다. 값은 보낸
  // 그대로 칸에 있다.
  const badKey = rejected ? vars.find((v) => rejected.includes(`(${v.key})`))?.key : undefined;
  const rejectNote = rejected ? (
    <p className="rp-err" role="alert">
      지난번 보낸 값으로 시작하지 못했습니다 — {rejected}
    </p>
  ) : null;
  const set = (k: string, v: string) => setVals((s) => ({ ...s, [k]: v }));
  const arm = () => {
    const inputs = Object.fromEntries(
      vars.filter((v) => (vals[v.key] ?? '').trim() !== '').map((v) => [v.key, vals[v.key]]),
    );
    onArm({ id, version: d.version.version_no, title, inputs });
  };

  return (
    <>
      <div className="rp-body">
        <div className="rp-sub">
          <button type="button" className="rp-back" ref={backRef} onClick={onBack}>
            ← 목록
          </button>
          <b className="rp-name" title={title}>
            {title}
          </b>
          <span className="rp-meta">판 {d.version.version_no}</span>
        </div>
        {spec.purpose && <p className="rp-purpose">{spec.purpose}</p>}
        {!badKey && rejectNote}

        <div className="rp-sec">단계 {spec.steps.length}개</div>
        {readyErr && <p className="rp-note">준비도를 모른다 — 게이트웨이에 묻지 못했습니다. 켤 수는 있고, 막힌 단계는 실행 때 단계 상태로 보입니다.</p>}
        <ol className="rp-steps">
          {spec.steps.map((s, i) => {
            const r = byStep.get(s.id);
            return (
              <li key={s.id} className="rp-step">
                <span className="rp-step-title">
                  {i + 1}. {s.title}
                </span>
                {r && <span className={`rp-ready is-${r.state}`}>{READY_LABEL[r.state] ?? r.state}</span>}
                {r?.reason && <span className="rp-step-why">{r.reason}</span>}
                {r && r.missing_tools.length > 0 && (
                  <span className="rp-step-why">이 박스 목록에 없는 도구 — {r.missing_tools.join(', ')}</span>
                )}
              </li>
            );
          })}
        </ol>

        {vars.length > 0 && (
          <>
            <div className="rp-sec">이번에 채울 값</div>
            <div className="rp-fields">
              {vars.map((v) => (
                <label key={v.key} className="rp-field">
                  <span className="rp-label">
                    {v.label} <code>{v.key}</code>
                    {v.required !== false && (
                      <em className="rp-req" title="필수">
                        필수
                      </em>
                    )}
                  </span>
                  {v.type === 'enum' ? (
                    <select
                      className="rp-input"
                      value={vals[v.key] ?? ''}
                      onChange={(e) => set(v.key, e.target.value)}
                      aria-invalid={v.key === badKey || undefined}
                    >
                      <option value="">(고르세요)</option>
                      {(v.values ?? []).map((x) => (
                        <option key={x} value={x}>
                          {x}
                        </option>
                      ))}
                    </select>
                  ) : v.type === 'boolean' ? (
                    // 참거짓은 고른다 — 포털은 true · false 만 받는다(글로 적은 '예' · '참' 은 실행을 만들기 전에 거절된다)
                    <select
                      className="rp-input"
                      value={vals[v.key] ?? ''}
                      onChange={(e) => set(v.key, e.target.value)}
                      aria-invalid={v.key === badKey || undefined}
                    >
                      <option value="">(고르세요)</option>
                      <option value="true">참(true)</option>
                      <option value="false">거짓(false)</option>
                    </select>
                  ) : v.type === 'json' ? (
                    <textarea
                      className="rp-input rp-mono"
                      spellCheck={false}
                      rows={4}
                      value={vals[v.key] ?? ''}
                      onChange={(e) => set(v.key, e.target.value)}
                      aria-invalid={v.key === badKey || undefined}
                    />
                  ) : (
                    // 수치는 수 칸이다 — 값은 적은 글 그대로 가고(큰 정수 id 가 바뀌지 않게) 형은 포털이 맞춘다(_coerce)
                    <input
                      className="rp-input"
                      {...(v.type === 'number' ? { type: 'number', step: 'any' } : {})}
                      value={vals[v.key] ?? ''}
                      onChange={(e) => set(v.key, e.target.value)}
                      aria-invalid={v.key === badKey || undefined}
                    />
                  )}
                  {v.key === badKey && rejectNote}
                  {v.why && (
                    <span className="rp-note">
                      <InlineMd text={v.why} />
                    </span>
                  )}
                  {v.example !== undefined && v.example !== null && (
                    <span className="rp-ex">
                      <button type="button" className="rp-ex-btn" onClick={() => set(v.key, exampleText(v.example))}>
                        예시 넣기
                      </button>
                      <span className="rp-note">내 값이 아니다 — 넣고 고쳐서 쓴다.</span>
                    </span>
                  )}
                </label>
              ))}
            </div>
          </>
        )}
      </div>
      <div className="rp-foot">
        <span className="rp-note">
          {missing.length
            ? `채울 칸 — ${missing.map((v) => v.label).join(' · ')}`
            : '켜 두면 다음에 보내는 발화가 이 루틴을 돌립니다(글을 비워 보내도 됩니다).'}
        </span>
        <button type="button" className="rp-on" disabled={missing.length > 0} onClick={arm}>
          켜기
        </button>
      </div>
    </>
  );
}
