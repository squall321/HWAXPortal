// 대화에 남은 발표자료 알림 아래의 도구 줄 — 누를 때 잡을 읽어 PDF 미리보기 · 다시 시도 · 사본 지우기를 낸다(docs/wda-deck M2)
import { useState } from 'react';
import { DeckHttpError, deckJob, type DeckJob } from '../../api/deck.api';
import { useCan } from '../../auth/useCan';
import { DeckTools } from './DeckTools';
import { useDeckStatus } from './useDeckStatus';

/** 알림은 새로고침 뒤에도 남는다(메시지의 deckJob) — 단추 칸(DeckSpot)은 맡긴 그 화면에서만 산다. 잡은 누를 때만 읽는다(알림마다 묻지 않는다). */
export function DeckNoticeTools({ jobId }: { jobId: string }) {
  const can = useCan();
  const allowed = can('plat:webdesign') && can('plat:reportarchive');
  const status = useDeckStatus(allowed);
  const [job, setJob] = useState<DeckJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');

  if (!allowed || !status?.enabled) return null;

  const open = async () => {
    setBusy(true);
    setNote('');
    try {
      setJob(await deckJob(jobId));
    } catch (e) {
      // 404 — 잡 기록이 보존 기한(7일) 뒤 지워졌다. 이 줄은 그 알림 하나의 일이다(창구가 꺼졌는지는 여기서 가리지 않는다)
      setNote(e instanceof DeckHttpError && e.status === 404
        ? '이 발표자료의 기록이 지워졌습니다 — 그 보고서의 \'발표자료로\' 에서 다시 만드세요.'
        : e instanceof Error ? e.message : '읽지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  if (!job) {
    return (
      <div className="deck-spot deck-notice-tools">
        <button type="button" className="msg-copy" disabled={busy} onClick={() => void open()}
          title="이 발표자료의 PDF 미리보기 · 다시 시도 · WebDesignAgents 사본 지우기">
          <span>{busy ? '읽는 중…' : '발표자료 관리'}</span>
        </button>
        {note && <span className="msg-wiki-note is-err" role="status">{note}</span>}
      </div>
    );
  }
  return (
    <div className="upl-panel deck-panel deck-notice-tools" role="group" aria-label="발표자료 관리">
      <div className="upl-head">
        <b>발표자료 관리</b>
        <span className="upl-file">{job.report.title || `보고서 ${job.report.id}`}</span>
        <button type="button" className="upl-x" onClick={() => setJob(null)} aria-label="닫기">✕</button>
      </div>
      {note && <p className="upl-note" role="status">{note}</p>}
      <DeckTools
        job={job}
        allowed={allowed}
        onJob={(j, how) => {
          if (how === 'retry') {
            // 다시 시도는 새 잡이다 — 진행은 입력창 위 '만들고 있는 발표자료' 줄이 잇고, 끝나면 맡긴 대화에 새 알림이 남는다
            setNote('다시 시도를 맡겼습니다 — 진행은 입력창 위 \'만들고 있는 발표자료\' 에 보이고, 끝나면 맡긴 대화에 새 알림을 남깁니다.');
            setJob({ ...job, can_retry: false });
          } else {
            setJob(j);
          }
        }}
      />
      {!job.deleted && job.state === 'failed' && !job.can_retry && !note && (
        <p className="upl-note">다시 시도할 수 없는 잡입니다 — 그 보고서의 '발표자료로' 에서 다시 만드세요.</p>
      )}
    </div>
  );
}
