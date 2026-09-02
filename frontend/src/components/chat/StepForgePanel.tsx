// StepForge 반입 패널 — 새 과제로 만들거나 기존 과제에 붙이고, 파싱을 잡으로 건다.
import { useEffect, useState } from 'react';
import {
  dispatchUpload,
  stepProjects,
  STEP_STAGES,
  type DispatchResult,
  type StagedFile,
  type StepProject,
} from '../../api/upload.api';
import { useAuth } from '../../auth/useAuth';

// StepForge 가 받는 잡 종류. pipeline 은 K파일까지 한 번에 가지만 그만큼 오래 걸린다.
const RUNS: { id: string; label: string }[] = [
  { id: 'parse', label: '파싱 — 어셈블리 트리·파트 추출' },
  { id: 'detect', label: '검출 — 파트 간 관계(tied·닿음·간극·침투)' },
  { id: 'mesh', label: '메시' },
  { id: 'pipeline', label: '전체 — 파싱·검출·메시·K파일' },
  { id: 'none', label: '등록만 (잡 걸지 않음)' },
];

export function StepForgePanel({ staged, onClose }: { staged: StagedFile; onClose: () => void }) {
  const { user } = useAuth();
  const [mode, setMode] = useState<'new' | 'existing'>('new');
  const [name, setName] = useState(staged.filename.replace(/\.[^.]+$/, ''));
  const [projects, setProjects] = useState<StepProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [run, setRun] = useState('parse');
  // 과제 메타 — 새 과제일 때만 쓴다. 담당자는 묻지 않는다(로그인한 사람이 담당자다).
  const [stage, setStage] = useState('');
  const [note, setNote] = useState('');
  const [code, setCode] = useState('');
  const [dept, setDept] = useState('');
  const [purpose, setPurpose] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<DispatchResult | null>(null);

  // 기존 과제 목록은 '기존에 추가' 를 고를 때만 부른다 — 안 쓸 조회를 매번 하지 않는다.
  useEffect(() => {
    if (mode !== 'existing' || projects.length) return;
    let alive = true;
    void (async () => {
      try {
        const rows = await stepProjects();
        if (!alive) return;
        setProjects(rows);
        if (rows.length && !projectId) setProjectId(rows[0].id);
      } catch (e) {
        if (alive) setErr(e instanceof Error ? e.message : '과제 목록을 못 읽었습니다.');
      }
    })();
    return () => { alive = false; };
  }, [mode, projects.length, projectId]);

  async function send() {
    setBusy(true);
    setErr('');
    try {
      const res = await dispatchUpload({
        staging_id: staged.staging_id,
        filename: staged.filename,
        destination: 'stepforge',
        run,
        ...(mode === 'existing'
          ? { project_id: projectId }
          : { project_name: name, stage, note, code, department: dept, purpose }),
      });
      if (res.stage === 'failed') setErr(res.error ?? '보내지 못했습니다.');
      else setDone(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '실패했습니다.');
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="upl-panel upl-done" role="status">
        <b>✓ StepForge 반입</b> — 과제 {done.project_id}
        {done.created_project ? ' (새로 만듦)' : ' (기존에 추가)'}
        {done.job_id ? (
          <span className="upl-props">
            잡 {done.job_id} · {done.kind} 진행 중 — 끝나면 파트 트리와 계면 목록을 볼 수 있습니다
          </span>
        ) : (
          <span className="upl-props">등록만 했습니다(잡 없음)</span>
        )}
        <button type="button" className="upl-x" onClick={onClose}>닫기</button>
      </div>
    );
  }

  const canSend = !busy && (mode === 'new' ? name.trim().length > 0 : !!projectId);
  return (
    <div className="upl-panel">
      <div className="upl-head">
        <b>StepForge 반입</b>
        <span className="upl-file">{staged.filename}</span>
        <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
      </div>

      <div className="upl-grid">
        <label>
          과제
          <select value={mode} onChange={(e) => setMode(e.target.value as 'new' | 'existing')}>
            <option value="new">새 과제로 만들기</option>
            <option value="existing">기존 과제에 추가</option>
          </select>
        </label>

        {mode === 'new' ? (
          <>
            <label>
              과제명
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="예: GS26U 미드프레임" />
            </label>
            <label>
              단계
              <select value={stage} onChange={(e) => setStage(e.target.value)}>
                <option value="">(미지정)</option>
                {STEP_STAGES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <label className="upl-wide">
              특이사항
              <input value={note} onChange={(e) => setNote(e.target.value)}
                     placeholder="예: 미드프레임만, 배터리 제외" />
            </label>
          </>
        ) : (
          <label>
            기존 과제
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.length === 0 && <option value="">(과제 없음)</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>
        )}

        <label>
          반입 후 작업
          <select value={run} onChange={(e) => setRun(e.target.value)}>
            {RUNS.map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </label>
      </div>

      {/* 나머지 메타는 접어 둔다 — 챗 흐름에서 칸이 많으면 올리기가 성가시다.
          안 적어도 반입은 되고, StepForge 앱에서 나중에 채울 수 있다. */}
      {mode === 'new' && (
        <details className="upl-more">
          <summary>자세히 — 과제번호 · 부서 · 해석목적</summary>
          <div className="upl-grid">
            <label>
              과제번호
              <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="예: GS26U-DROP-001" />
            </label>
            <label>
              부서
              <input value={dept} onChange={(e) => setDept(e.target.value)} placeholder="예: MX 구조해석" />
            </label>
            <label className="upl-wide">
              해석목적
              <input value={purpose} onChange={(e) => setPurpose(e.target.value)}
                     placeholder="예: 염수부식 후 낙하 크랙 평가" />
            </label>
          </div>
        </details>
      )}

      {/* 같은 이름 재등록은 StepForge 가 갱신으로 처리하고, 잡이 도는 중 교체는 거부한다.
          사용자가 그 거부를 만나기 전에 미리 알려 둔다. */}
      {mode === 'existing' && (
        <p className="upl-note">
          같은 이름의 파일을 다시 올리면 갱신됩니다. 그 과제에 잡이 도는 중이면 거부됩니다 —
          먼저 끝내거나 취소하세요.
        </p>
      )}
      <p className="upl-note">
        파싱은 무거워 <b>잡으로 걸고 바로 돌아옵니다.</b> 진행은 잡 번호로 확인합니다.
        {mode === 'new' && user && <> 담당자는 <b>{user.email}</b> 로 자동 기입됩니다.</>}
      </p>

      {err && <p className="upl-err" role="alert">{err}</p>}

      <div className="upl-actions">
        <button type="button" className="upl-go" disabled={!canSend} onClick={() => void send()}>
          {busy ? '보내는 중…' : 'StepForge 로 보내기'}
        </button>
      </div>
    </div>
  );
}
