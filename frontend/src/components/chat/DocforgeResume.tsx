// 창을 닫아 Report Archive 에 넣지 못한 정밀 변환 잡을 다시 여는 줄 — 입력창 위 '끝나지 않은 정밀 변환 N건'(DocForge E15)
import { useEffect, useState } from 'react';
import { docforgeDismiss, docforgeJobs, type DocforgeJob } from '../../api/upload.api';

const LIVE = ['queued', 'running', 'done'];

/** 아직 넣지 않았고 DocForge 가 살아 있다고 답한 잡만 — 실패 · 취소 · 보존 기한이 지나 못 물은 잡은 보이지 않는다. */
function pending(jobs: DocforgeJob[]): DocforgeJob[] {
  return jobs.filter((j) => !j.delivered && j.st && LIVE.includes(String(j.st.status)));
}

function stateText(j: DocforgeJob): string {
  const st = j.st;
  if (!st) return '';
  if (st.status === 'done') return '변환 끝 — 넣기를 기다림';
  if (st.status === 'queued') return '줄 서는 중';
  return `${st.stage || '변환 중'} · ${Math.round(st.progress ?? 0)}%`;
}

function when(t?: number | null): string {
  return t ? new Date(t * 1000).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
}

export function DocforgeResume({ refresh, onResume }: {
  /** 바뀌면 목록을 다시 읽는다(이어 본 패널을 닫은 뒤). */
  refresh: number;
  onResume: (j: DocforgeJob) => void;
}) {
  const [jobs, setJobs] = useState<DocforgeJob[]>([]);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let stop = false;
    docforgeJobs().then((r) => { if (!stop) setJobs(pending(r.jobs)); }).catch(() => undefined);   // 못 읽으면 줄을 띄우지 않는다
    return () => { stop = true; };
  }, [refresh]);
  if (!jobs.length) return null;
  return (
    <div className="upl-panel df-resume">
      <div className="upl-head">
        <b>끝나지 않은 정밀 변환 {jobs.length}건</b>
        <span className="upl-file">창을 닫아 Report Archive 에 아직 넣지 않았습니다</span>
        <button type="button" className="upl-x" onClick={() => setOpen((o) => !o)} aria-expanded={open}
          aria-label={open ? '접기' : '펼치기'}>{open ? '▴' : '▾'}</button>
      </div>
      {open && (
        <ul className="df-resume-list">
          {jobs.map((j) => (
            <li key={j.job_id}>
              <span className="upl-file">{j.filename || j.job_id}</span>
              <span className="upl-note"> {when(j.created_at)} · {stateText(j)} </span>
              <span className="upl-actions">
                <button type="button" className="upl-go" onClick={() => onResume(j)}>이어 보기</button>
                <button type="button" onClick={() => {
                  void docforgeDismiss(j.job_id);
                  setJobs((xs) => xs.filter((x) => x.job_id !== j.job_id));
                }}>숨기기</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
