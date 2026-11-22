// 끝난 발표자료 잡의 도구 — PDF 미리보기(포털이 중계 · 응답 머리 CSP sandbox) · 다시 시도(WDA resume) · WebDesignAgents 사본 지우기(docs/wda-deck M2)
import { useState } from 'react';
import { DeckHttpError, deckJob, deleteDeck, retryDeck, type DeckJob } from '../../api/deck.api';
import { config } from '../../config';
import { useDeckStatus } from './useDeckStatus';

/** `onJob` — 잡이 바뀌었다(지웠다 · 다시 시도한 **새 잡**). 부른 쪽이 그 잡으로 갈아 끼운다. `allowed` — 권한 둘(부른 쪽이 이미 봤다). */
export function DeckTools({ job, onJob, allowed }: { job: DeckJob; onJob: (j: DeckJob, how: 'retry' | 'delete') => void; allowed: boolean }) {
  const status = useDeckStatus(allowed);
  const [busy, setBusy] = useState<'' | 'preview' | 'retry' | 'delete'>('');
  const [err, setErr] = useState('');
  // 미리보기 주소 — 누른 뒤 포털에 한 번 물어(apiFetch 가 지난 세션을 되살린다) 받은 것만 틀에 싣는다. 틀의 이동은 세션을 되살리지 못한다
  const [preview, setPreview] = useState<string | null>(null);

  const act = async (what: 'preview' | 'retry' | 'delete', run: () => Promise<void>) => {
    setBusy(what);
    setErr('');
    try {
      await run();
    } catch (e) {
      setErr(e instanceof DeckHttpError || e instanceof Error ? e.message : '하지 못했습니다.');
    } finally {
      setBusy('');
    }
  };
  const togglePreview = () => {
    if (preview) {
      setPreview(null);
      return;
    }
    void act('preview', async () => {
      const j = await deckJob(job.job_id);
      if (!j.preview) throw new Error('미리볼 PDF 가 없습니다(지워졌거나 만들지 않았습니다).');
      setPreview(j.preview);
    });
  };
  const retry = () => void act('retry', async () => onJob(await retryDeck(job.job_id), 'retry'));
  const remove = () => {
    if (!window.confirm('WebDesignAgents 에 남은 이 발표자료의 사본(보고서 본문 · 파일)을 지울까요? 되돌릴 수 없고, 받기 링크는 더 열리지 않습니다.')) return;
    void act('delete', async () => {
      setPreview(null);
      onJob(await deleteDeck(job.job_id), 'delete');
    });
  };

  const canPreview = job.state === 'done' && Boolean(job.preview) && !job.expired && !job.deleted;
  const canRetry = job.state === 'failed' && Boolean(job.can_retry);
  const canDelete = Boolean(status?.delete) && !job.deleted;
  if (!canPreview && !canRetry && !canDelete && !job.deleted && !err) return null;
  return (
    <>
      {job.deleted && <p className="upl-note" role="status">WebDesignAgents 의 사본을 지웠습니다.</p>}
      {(canPreview || canRetry || canDelete) && (
        <div className="upl-actions deck-tools">
          {canPreview && (
            <button type="button" disabled={busy !== ''} aria-expanded={Boolean(preview)} onClick={togglePreview}>
              {busy === 'preview' ? '여는 중…' : preview ? 'PDF 미리보기 닫기' : 'PDF 미리보기'}
            </button>
          )}
          {canRetry && (
            <button type="button" className="upl-go" disabled={busy !== ''} onClick={retry}
              title="같은 실행을 끊긴 단계부터 다시 돌립니다 — 보고서를 다시 읽거나 넘기지 않습니다">
              {busy === 'retry' ? '맡기는 중…' : '다시 시도'}
            </button>
          )}
          {canDelete && (
            <button type="button" disabled={busy !== ''} onClick={remove}
              title="WebDesignAgents 에 남은 보고서 본문 · 파일을 지웁니다(대화의 알림은 남습니다)">
              {busy === 'delete' ? '지우는 중…' : '사본 지우기'}
            </button>
          )}
        </div>
      )}
      {err && <div className="upl-err" role="alert">⚠ {err}</div>}
      {preview && canPreview && (
        <>
          {/* ⚠ sandbox **속성**을 달지 않는다 — 속성이 있으면 Chromium 의 내장 PDF 보기가 서지 않는다(빈 틀). 격리는 포털이 다는 응답 머리
              (Content-Security-Policy: sandbox · frame-ancestors 'self')가 한다. 주소는 포털 경로다 — WDA 주소가 아니다(WD-D91). */}
          <iframe className="deck-preview" src={`${config.apiBase}${preview}`} title="발표자료 PDF 미리보기" referrerPolicy="no-referrer" />
          <p className="upl-note">미리보기가 비어 보이면 위의 'PDF 받기' 로 내려받으세요.</p>
        </>
      )}
    </>
  );
}
