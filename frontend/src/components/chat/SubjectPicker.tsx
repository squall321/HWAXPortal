// 심의 주제 고르기 — 과제(SP 허브 과제 key) · 차수 · 글 · 설계 자료를 그 사람의 도구 결과 후보에서 고른다(과제 인사이트 그래프 M1)
//
// docs/project-insight-graph PLAN §4.1. 후보는 이 대화의 도구 결과(candidates)와 허브 과제 찾기(그 사람의 PAT — 포털이 StepForge find_plm_task 를
// 부른다)에서만 온다. 과제 key 를 손으로 적는 칸은 없다 — 결과 행의 key 칸만 고른다. 고른 주제는 심의 시작 때 에이전트 서버가 같은 풀이로 다시
// 확인한다(확인되지 않으면 어느 과제에도 잇지 않는다). 과제를 고르지 않으면 주제 없이 돈다(과제 대상이 아닌 질문 — 잇지 않는다).
// 이 대화의 결과에서 온 key 는 고를 때 허브 찾기로 글자 그대로 있는지 한 번 더 본다 — 도구 결과의 미리보기는 겹친 공백을 하나로 줄여 적어(에이전트
// 서버 _tool_preview) 그 key 가 허브의 key 와 다를 수 있다(반대 검토 11-02). 허브에서 비활성인 과제는 고를 수 없다(서버가 확인하지 않는다).
import { useId, useMemo, useRef, useState } from 'react';
import { searchSubjectTasks } from '../../api/chat.api';
import {
  candidatesFromSearch,
  sourceRounds,
  STAGE_CODES,
  SUBJECT_ARTIFACTS_MAX,
  SUBJECT_TEXT_MAX,
  type ArtifactCandidate,
  type SpCandidate,
  type StageCode,
  type SubjectCandidates,
  type SubjectDraft,
} from './subject';

const KIND_LABEL: Record<ArtifactCandidate['kind'], string> = { mcad: '기구 CAD', ecad: '회로 보드', cae: '해석 리포트' };

interface SubjectPickerProps {
  candidates: SubjectCandidates;
  value: SubjectDraft;
  onChange: (next: SubjectDraft) => void;
}

export function SubjectPicker({ candidates, value, onChange }: SubjectPickerProps) {
  const [query, setQuery] = useState('');
  const [found, setFound] = useState<SpCandidate[]>([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [check, setCheck] = useState(''); // 이 대화의 결과에서 온 key 를 허브 찾기로 다시 본 결과(문제가 없으면 빈 글)
  const ctrl = useRef<AbortController | null>(null);
  const checkCtrl = useRef<AbortController | null>(null);
  const latest = useRef(value); // 다시 보기의 답이 올 때 지금 고른 것 — 그사이 다른 것을 골랐으면 답을 버린다
  latest.current = value;
  const group = useId(); // 라디오 묶음 이름 — 한 화면에 고르기가 둘이어도(심의 시작 · 브리프) 섞이지 않게

  // 이 대화의 후보 뒤에 찾은 행 — 같은 key 는 하나다(먼저 본 출처를 둔다).
  const rows = useMemo(() => {
    const seen = new Set<string>();
    const out: SpCandidate[] = [];
    for (const r of [...candidates.sp, ...found]) {
      if (seen.has(r.key)) continue;
      seen.add(r.key);
      out.push(r);
    }
    return out;
  }, [candidates.sp, found]);
  const rounds = useMemo(() => sourceRounds(value.artifacts), [value.artifacts]);
  const picked = value.spTask !== '';
  const artsFull = value.artifacts.length >= SUBJECT_ARTIFACTS_MAX;

  const search = async () => {
    const q = query.trim();
    if (!q || busy) return;
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setBusy(true);
    setNote('');
    const r = await searchSubjectTasks(q, c.signal);
    if (ctrl.current !== c) return;
    setBusy(false);
    if (r.error) {
      setNote(`허브 과제를 찾지 못했다 — ${r.error}`);
      return;
    }
    setFound(candidatesFromSearch(r.rows, q));
    if (!r.rows.length) setNote(r.why?.message ? `맞는 과제가 없다 — ${r.why.message}` : '맞는 과제가 없다');
  };

  const recheck = async (key: string) => {
    const c = new AbortController();
    checkCtrl.current = c;
    setCheck(`허브에서 「${key}」 를 글자 그대로 찾는 중…`);
    const r = await searchSubjectTasks(key, c.signal);
    if (checkCtrl.current !== c || latest.current.spTask !== key) return;
    checkCtrl.current = null;
    const hit = r.rows.find((x) => x.key === key);
    if (r.error) setCheck(`고른 과제를 허브에서 다시 보지 못했다 — ${r.error}(시작하면 서버가 다시 확인한다)`);
    else if (!hit)
      setCheck(
        '이 대화의 결과에서 온 key 가 허브에 글자 그대로 없다(도구 결과는 겹친 공백을 하나로 줄여 적는다) — 이름 일부로 찾아 다시 고르세요. 이대로 시작하면 확인되지 않아 어느 과제에도 잇지 않습니다',
      );
    else if (hit.active === false) setCheck('허브에서 비활성인 과제다 — 이대로 시작하면 확인되지 않아 어느 과제에도 잇지 않습니다');
    else setCheck('');
  };
  const pick = (key: string) => {
    checkCtrl.current?.abort();
    checkCtrl.current = null;
    setCheck('');
    onChange(key ? { ...value, spTask: key } : { spTask: '', round: '', text: '', artifacts: [] });
    // 찾기에서 온 행은 서버가 받은 key 그대로라 다시 보지 않는다
    if (key && !found.some((x) => x.key === key)) void recheck(key);
  };
  const toggleArt = (a: ArtifactCandidate) => {
    const on = value.artifacts.some((x) => x.kind === a.kind && x.id === a.id);
    onChange({ ...value, artifacts: on ? value.artifacts.filter((x) => !(x.kind === a.kind && x.id === a.id)) : [...value.artifacts, a] });
  };

  return (
    <div className="cx-subj">
      <span className="cx-subj-label">
        과제 주제 — 과제를 대상으로 한 심의면 고르세요(과제 대상이 아닌 질문이면 그대로 둡니다)
      </span>
      <div className="cx-brief-seats cx-subj-rows" role="radiogroup" aria-label="과제 주제">
        <label className="cx-brief-seat">
          <input type="radio" name={group} checked={!picked} onChange={() => pick('')} />
          <span className="cx-brief-seat-name">과제 대상이 아님</span>
          <span className="cx-brief-seat-why">어느 과제에도 잇지 않는다</span>
        </label>
        {rows.map((r) => (
          <label key={r.key} className="cx-brief-seat">
            <input type="radio" name={group} checked={value.spTask === r.key} disabled={!r.active} onChange={() => pick(r.key)} />
            <span className="cx-brief-seat-name">{r.key}</span>
            {r.taskCode && <span className="cx-brief-seat-axis">{r.taskCode}</span>}
            {!r.active && <span className="cx-brief-seat-axis">허브에서 비활성 — 고를 수 없다</span>}
            <span className="cx-brief-seat-why">{[r.project, r.label !== r.key ? r.label : undefined, r.from].filter(Boolean).join(' · ')}</span>
          </label>
        ))}
      </div>
      <div className="cx-subj-search">
        <input
          className="cx-brief-seatsearch"
          value={query}
          maxLength={200}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void search();
            }
          }}
          placeholder="허브 과제 찾기 — 과제명 · 과제코드 · 모델명 · 프로젝트 이름"
        />
        <button type="button" className="cx-subj-go" onClick={() => void search()} disabled={busy || !query.trim()}>
          {busy ? '찾는 중…' : '찾기'}
        </button>
      </div>
      {note && <p className="cx-brief-empty">{note}</p>}
      {check && <p className="cx-brief-empty cx-subj-check">{check}</p>}

      {picked && (
        <div className="cx-subj-more">
          <label className="cx-subj-field">
            <span>차수</span>
            <select value={value.round} onChange={(e) => onChange({ ...value, round: e.target.value as StageCode | '' })}>
              <option value="">차수 모름 — 어느 차수에도 섞지 않는다</option>
              {rounds.length > 0 && (
                <optgroup label="고른 해석 리포트의 원천 값">
                  {rounds.map((r) => (
                    <option key={`src-${r.code}`} value={r.code}>
                      {r.code} — {r.from}
                    </option>
                  ))}
                </optgroup>
              )}
              <optgroup label="개발 단계 코드">
                {STAGE_CODES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </optgroup>
            </select>
          </label>
          <label className="cx-subj-field">
            <span>글(선택) — 과제 이름 · 코드 · 차수 메모</span>
            <input
              className="cx-brief-seatsearch"
              value={value.text}
              maxLength={SUBJECT_TEXT_MAX}
              onChange={(e) => onChange({ ...value, text: e.target.value })}
            />
          </label>
          {candidates.artifacts.length > 0 && (
            <div className="cx-subj-field">
              <span>
                설계 자료(선택 · {value.artifacts.length}/{SUBJECT_ARTIFACTS_MAX}) — 이 대화의 도구 결과
                {artsFull ? ` · ${SUBJECT_ARTIFACTS_MAX}건까지 싣는다` : ''}
              </span>
              <div className="cx-brief-seats">
                {candidates.artifacts.map((a) => {
                  const on = value.artifacts.some((x) => x.kind === a.kind && x.id === a.id);
                  return (
                    <label key={`${a.kind}:${a.id}`} className="cx-brief-seat">
                      <input type="checkbox" checked={on} disabled={artsFull && !on} onChange={() => toggleArt(a)} />
                      <span className="cx-brief-seat-axis">{KIND_LABEL[a.kind]}</span>
                      <span className="cx-brief-seat-name">{a.label ?? a.id}</span>
                      <span className="cx-brief-seat-why">
                        {[a.rev ? `판 ${a.rev}` : undefined, a.id, a.from].filter(Boolean).join(' · ')}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
          <p className="cx-subj-note">
            심의를 시작하면 서버가 허브 거울 풀이로 과제 key 를 다시 확인합니다 — 확인되지 않으면 어느 과제에도 잇지 않습니다. 주제는 Report
            Archive 보고서에 적지 않습니다.
          </p>
        </div>
      )}
    </div>
  );
}
