// 진행 카드(docs/request-1125 WD-13) — 확인 뒤 건 잡 · 엔진 이어하기의 상태 · 단계 · 링크. 심의 잡은 진행을 다시 물어 끝나면 결과로 바꾼다
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { fetchEngineJobStatus, type EngineJobStatus } from '../../api/engineDelib.api';
import { useChat } from '../../state/ChatContext';
import { isJobLink } from '../../state/chatStore';
import type { JobCard as Card } from '../../types/chat';
import { RA_HOME, openRaReport } from './raLink';

// 잡 상태 낱말(에이전트 서버 status_wait 가 읽는 낱말 · 엔진 delib_jobs 의 상태) → 화면 낱말. 모르는 낱말은 그대로 보인다.
const WORD: Record<string, string> = {
  queued: '줄 서는 중', pending: '기다리는 중', waiting: '기다리는 중', running: '도는 중', started: '도는 중', in_progress: '도는 중',
  processing: '도는 중', done: '끝남', completed: '끝남', succeeded: '끝남', success: '끝남', finished: '끝남', error: '오류',
  failed: '실패', cancelled: '접힘', canceled: '접힘', interrupted: '끊김 — 이어가면 남은 라운드만 돈다',
};
// 다시 묻는 간격 — 처음은 잦게, 오래 도는 심의는 1분마다(한 번 묻는 데 게이트웨이 왕복이 셋이다)
const POLL_MS = [10_000, 20_000, 30_000, 60_000];

/** 이 답의 진행 카드들. */
export function JobCards({ cards }: { cards: Card[] }) {
  return (
    <div className="job-cards">
      {cards.map((c) => (
        <JobCardView key={c.job_ids[0]} card={c} />
      ))}
    </div>
  );
}

function JobCardView({ card }: { card: Card }) {
  const jobId = card.job_ids[0];
  // 다시 묻는 것은 심의 잡의 deliberate_status 하나뿐이다(포털 · 화면이 같은 규칙으로 거른다) — 다른 잡은 받은 상태 · 링크만 보인다
  const pollId = card.kind === 'deliberation' && card.status_call?.args.job_id === jobId ? jobId : null;
  const [st, setSt] = useState<EngineJobStatus | null>(null);
  const [err, setErr] = useState('');
  const { refreshServerList, activeConversation } = useChat();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    if (!pollId) return;
    let stop = false;
    let n = 0;
    let t: number | undefined;
    const run = async () => {
      try {
        const s = await fetchEngineJobStatus(pollId);
        if (stop) return;
        setSt(s);
        setErr('');
        if (s.phase === 'end') {
          void refreshServerList(); // 들인 대화가 사이드바에 서고, 열린 대화면 결과가 붙는다
          return;
        }
      } catch (e) {
        if (stop) return;
        setErr(e instanceof Error ? e.message : String(e));
      }
      t = window.setTimeout(() => void run(), POLL_MS[Math.min(n++, POLL_MS.length - 1)]);
    };
    void run();
    return () => {
      stop = true;
      window.clearTimeout(t);
    };
  }, [pollId, refreshServerList]);

  const state = st?.status ?? card.state;
  const ended = (st?.phase ?? card.phase) === 'end';
  const round = st?.round && st?.total_rounds ? ` · 라운드 ${st.round}/${st.total_rounds}` : '';
  const queue = st?.queue?.position ? ` · 줄 ${st.queue.position}번째` : '';
  const step = st?.step || card.detail || '';
  const prog = st ? '' : typeof card.progress === 'number' ? ` · ${card.progress}%` : '';
  const rid = st?.report_id ?? null;
  const cid = st?.conversation_id ?? null;
  const here = Boolean(cid && activeConversation?.serverId === cid);
  const openConv = () => {
    if (!cid) return;
    navigate('/deliberate', { state: { openConversation: { id: cid, title: `심의 ${jobId}` } } });
  };
  return (
    <div className={`job-card${ended ? ' is-end' : ''}`} role="status" aria-label="잡 진행">
      <div className="job-card-head">
        <span className="job-card-k">{card.kind === 'deliberation' ? '심의 잡' : '잡'}</span>
        <code>{jobId}</code>
        {card.app ? <span className="job-card-app">{card.app}</span> : null}
        {card.continued_from ? <span className="job-card-app">앞 잡 {card.continued_from}</span> : null}
      </div>
      <div className="job-card-state">
        {WORD[state] ?? (state || '상태 모름')}
        {prog}
        {round}
        {queue}
        {step && !ended ? ` — ${step}` : ''}
        {st?.error ? ` — ${st.error}` : ''}
      </div>
      {err && <div className="job-card-err">진행을 다시 묻지 못했습니다 — {err}</div>}
      <div className="job-card-links">
        {isJobLink(card.link) && (
          <a href={card.link} target="_blank" rel="noreferrer">
            결과 · 잡 화면 열기 ↗
          </a>
        )}
        {ended && rid != null && (
          <a href={RA_HOME} target="_blank" rel="noopener" onClick={(e) => {
            if (openRaReport(rid)) e.preventDefault();
          }}>
            Report Archive 보고서 #{rid} ↗
          </a>
        )}
        {ended && pollId && (here ? (
          <span>이 대화에 좌석 발언과 결정문이 붙었습니다</span>
        ) : cid ? (
          pathname.startsWith('/deliberate') && activeConversation?.serverId !== cid ? (
            <button type="button" className="job-card-btn" onClick={openConv}>심의 대화 열기</button>
          ) : (
            <button type="button" className="job-card-btn" onClick={openConv}>심의 페이지에서 결정문 보기</button>
          )
        ) : (
          <span>결정문은 잠시 뒤 심의 목록에 대화로 섭니다</span>
        ))}
      </div>
    </div>
  );
}
