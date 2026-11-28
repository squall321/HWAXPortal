// 내 엔진 심의 잡(docs/request-1125 WD-08) — 날짜 · 종류 · 글로 거르고 더 보기, 결정문 전문 보기, '이 대화에 싣기', 들인 대화 열기(거기서 이어가기)
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchEngineDecision, listEngineJobs, type EngineDecision, type EngineJobRow } from '../../api/engineDelib.api';
import { useChat } from '../../state/ChatContext';
import { Modal } from '../ui/Modal';
import { ENGINE_JOBS } from './confirm';
import { TextBlock } from './renderers/TextBlock';
import { decisionNotice } from './uploadNotice';

const STATUS: Record<string, string> = {
  queued: '줄 섬', running: '도는 중', done: '끝남', error: '오류', cancelled: '접힘', interrupted: '끊김',
};

/** 엔진 잡 목록 대화상자 — 사이드바의 단추가 연다. 결정문은 모델을 거치지 않고 포털이 엔진에서 원문 그대로 받는다. */
export function EngineJobsPanel({ onClose }: { onClose: () => void }) {
  const { addUploadNotice, activeConversation } = useChat();
  const navigate = useNavigate();
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const [query, setQuery] = useState('');
  const [job, setJob] = useState('');
  const [all, setAll] = useState(false);
  const [rows, setRows] = useState<EngineJobRow[] | null>(null);
  const [nextUntil, setNextUntil] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [open, setOpen] = useState<string | null>(null);
  const [dec, setDec] = useState<Record<string, EngineDecision | { error: string }>>({});
  const [put, setPut] = useState<Record<string, boolean>>({});

  const search = async (more = false) => {
    setBusy(true);
    setErr('');
    try {
      const got = await listEngineJobs({
        since, until: more && nextUntil ? nextUntil : until, query, job, scope: all ? 'all' : 'mine', limit: 50,
      });
      setRows((prev) => (more && prev ? [...prev, ...got.jobs.filter((r) => !prev.some((p) => p.job_id === r.job_id))] : got.jobs));
      setNextUntil(got.more ? got.next_until : null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const view = async (id: string) => {
    if (open === id) {
      setOpen(null);
      return;
    }
    setOpen(id);
    if (dec[id]) return;
    try {
      const d = await fetchEngineDecision(id);
      setDec((p) => ({ ...p, [id]: d }));
    } catch (e) {
      setDec((p) => ({ ...p, [id]: { error: e instanceof Error ? e.message : String(e) } }));
    }
  };
  const load = (d: EngineDecision) => {
    addUploadNotice(decisionNotice(d));
    setPut((p) => ({ ...p, [d.job_id]: true }));
  };
  const openConv = (r: EngineJobRow) => {
    if (!r.conversation_id) return;
    navigate('/deliberate', { state: { openConversation: { id: r.conversation_id, title: r.question.slice(0, 80) || r.job_id } } });
    onClose();
  };

  return (
    <Modal onClose={onClose} label="엔진 심의 잡">
      <div className="pp-backdrop" onClick={onClose}>
      <div className="pp-card ejp" onClick={(e) => e.stopPropagation()}>
        <div className="pp-head">
          <span className="pp-title">엔진 심의 잡</span>
          <button type="button" className="pp-x" onClick={onClose} aria-label="닫기">×</button>
        </div>
        <p className="ejp-note">
          개인 Claude(MCP) · 챗 확인 카드로 연 심의입니다. 끝난 잡은 포털이 심의 목록에 대화로 들입니다 — 열면 거기서 이어갑니다.
        </p>
        <form className="ejp-filter" onSubmit={(e) => { e.preventDefault(); void search(); }}>
          <label>부터 <input type="date" value={since} onChange={(e) => setSince(e.target.value)} aria-label="시작일" /></label>
          <label>까지 <input type="date" value={until} onChange={(e) => setUntil(e.target.value)} aria-label="끝일" /></label>
          <label>
            종류{' '}
            <select value={job} onChange={(e) => setJob(e.target.value)} aria-label="심의 종류">
              <option value="">전부</option>
              {ENGINE_JOBS.map(([k, label]) => (
                <option key={k} value={k}>{label}</option>
              ))}
            </select>
          </label>
          <input type="search" placeholder="화두 · 잡 id 에 든 글" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="글" />
          <label><input type="checkbox" checked={all} onChange={(e) => setAll(e.target.checked)} /> 같은 소속 잡도</label>
          <button type="submit" className="btn-primary" disabled={busy}>{busy ? '찾는 중…' : '찾기'}</button>
        </form>
        {err && <div className="ejp-err" role="alert">{err}</div>}
        {rows && rows.length === 0 && <div className="ejp-empty">맞는 잡이 없습니다</div>}
        {rows && rows.length > 0 && (
          <ul className="ejp-list">
            {rows.map((r) => {
              const d = dec[r.job_id];
              const ok = d && !('error' in d) ? d : null;
              return (
                <li key={r.job_id} className="ejp-row">
                  <div className="ejp-row-head">
                    <span className="ejp-when">{(r.created ?? '').replace('T', ' ').slice(0, 16)}</span>
                    <span className="ejp-kind">{r.label || r.job}</span>
                    <span className={`ejp-st st-${r.status ?? ''}`}>{STATUS[r.status ?? ''] ?? r.status}</span>
                    {!r.mine && <span className="ejp-owner">{r.owner}</span>}
                    {r.report_id ? <span className="ejp-owner">보고서 #{r.report_id}</span> : null}
                    <code className="ejp-id">{r.job_id}</code>
                  </div>
                  <div className="ejp-q">{r.question}{r.question_chars > r.question.length ? ' …' : ''}</div>
                  <div className="ejp-actions">
                    <button type="button" className="cx-chip" onClick={() => void view(r.job_id)} aria-expanded={open === r.job_id}>
                      {open === r.job_id ? '결정문 접기' : '결정문 보기'}
                    </button>
                    {ok && ok.decision && (
                      <button type="button" className="cx-chip" onClick={() => load(ok)} disabled={put[r.job_id]}
                        title={activeConversation ? '이 대화에 결정문을 근거로 싣습니다' : '새 대화를 만들어 결정문을 싣습니다'}>
                        {put[r.job_id] ? '실었습니다' : '이 대화에 싣기'}
                      </button>
                    )}
                    {r.conversation_id && (
                      <button type="button" className="cx-chip" onClick={() => openConv(r)}>대화 열기 · 이어가기</button>
                    )}
                  </div>
                  {open === r.job_id && (
                    <div className="ejp-decision">
                      {!d ? '결정문을 받는 중…' : 'error' in d ? `결정문을 읽지 못했습니다 — ${d.error}` : d.decision ? (
                        <TextBlock text={d.decision} />
                      ) : (
                        `결정문이 없습니다${d.error ? ` — ${d.error}` : d.note ? ` — ${d.note}` : ''}`
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {nextUntil && (
          <button type="button" className="btn-secondary ejp-more" onClick={() => void search(true)} disabled={busy}>
            더 보기({nextUntil.replace('T', ' ').slice(0, 16)} 전)
          </button>
        )}
      </div>
      </div>
    </Modal>
  );
}
