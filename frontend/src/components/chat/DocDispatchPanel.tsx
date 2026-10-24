// 문서(PPT·Word·PDF)를 각 서비스의 **자기 취입기**로 보내는 패널 — 포털은 배달만 한다
import { useEffect, useRef, useState } from 'react';
import {
  dispatchUpload, docforgeCancel, docforgeDeliver, docforgeStatus, type DispatchResult, type DocforgeStatus, type StagedFile,
} from '../../api/upload.api';
import { dispatchInstruction, dispatchNotice, reportLink, type UploadNotice } from './uploadNotice';

const SPEC: Record<string, { title: string; note: string; go: string }> = {
  chat: {
    title: '이 대화에서 분석',
    // 저장하지 않는다 — AI 데이터 허브 변환기로 읽어 온 글을 입력창의 문서 칩으로 붙인다(docs/chat-ppt PP-D17).
    note: '글 · 표 · 차트 데이터 · 발표자 노트를 읽어 입력창에 문서로 붙입니다. 어디에도 저장하지 않습니다. '
      + '그림 내용은 아직 글로 옮기지 않습니다(그림이 있던 자리만 표시).',
    go: '읽어서 붙이기',
  },
  reportarchive: {
    title: 'Report Archive 로 보내기',
    // RA 의 /imports/pptx 를 그대로 쓴다 — 포털에 파서를 새로 만들지 않는다.
    note: '슬라이드 한 장이 보고서 페이지 한 장이 됩니다. 제목·본문·표·그림이 위젯으로 들어갑니다. '
      + '초안으로 만들어지니 확인하고 저장·게시하세요.',
    go: '보고서 초안 만들기',
  },
  reportarchive_precise: {
    title: 'Report Archive — 정밀 변환',
    // DocForge 가 패키지를 만들고 포털이 본인 명의로 엄격 생성한다(docs/doc-to-ra DF-D17). 변환은 잡이라 진행을 보다가 끝나면 넣는다.
    note: '배치 · 표 · 차트 값 · 발표자 노트를 원본 그대로 옮기고, 그림은 모델이 읽어 \'모델 판독\' 으로 따로 답니다. '
      + '담지 못한 것은 버린 까닭과 함께 알립니다. 본인 명의로 내 공간에 보고서가 만들어집니다.',
    go: '정밀 변환 맡기기',
  },
  aidatahub: {
    title: 'AI 데이터 허브로 보내기',
    note: '서버가 정밀 변환해 지식카드 **초안**을 만듭니다. 바로 저장하지 않습니다 — '
      + '모자란 항목(팀·그룹 등)은 챗에서 확인한 뒤 저장합니다.',
    go: '변환하기',
  },
};

const POLL_MS = 1500;
const POLL_ERR_MAX = 3;

export function DocDispatchPanel({
  staged, destination, onClose, onFill, onDispatched, onAttachDoc,
}: {
  staged: StagedFile;
  destination: string;
  onClose: () => void;
  /** 지시문을 입력창에 — auto 면 입력창이 비어 있을 때만 넣는다(사람이 쓰던 글을 지우지 않는다, docs/chat-ppt PP-D4). */
  onFill?: (text: string, auto?: boolean) => void;
  /** 보내기 성공을 대화에 남긴다(알림 한 건 + 업로드 근거, PP-D3). 종전엔 결과가 이 패널 안에서만 끝났다. */
  onDispatched?: (n: UploadNotice) => void;
  /** 이 대화에서 분석 — 읽어 온 글을 문서 칩으로 붙인다(PP-D17). 못 붙이면 까닭을 돌려준다. */
  onAttachDoc?: (doc: File) => Promise<string | void>;
}) {
  const spec = SPEC[destination];
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<DispatchResult | null>(null);
  // 정밀 변환 — 맡긴 잡을 1.5초마다 본다(PC 도우미와 같은 박자). 끝나면 배달(RA 엄격 생성)까지 하고 멈춘다.
  const [job, setJob] = useState<{ id: string; st?: DocforgeStatus; errs: number } | null>(null);
  const cb = useRef({ onDispatched, onFill });
  cb.current = { onDispatched, onFill };

  const finish = (r: DispatchResult) => {
    setDone(r);
    const n = dispatchNotice(staged.filename, r);
    if (n) cb.current.onDispatched?.(n);
    const t = dispatchInstruction(r);
    if (t) cb.current.onFill?.(t, true);
  };

  useEffect(() => {
    if (!job || done || (job.st && ['failed', 'cancelled'].includes(job.st.status))) return;
    let stop = false;
    const timer = window.setTimeout(async () => {
      try {
        const st = await docforgeStatus(job.id);
        if (stop) return;
        if (st.status === 'done') {
          const r = st.delivered ?? await docforgeDeliver(job.id);
          if (stop) return;
          if (r.stage === 'failed') {
            setErr(String(r.error || 'Report Archive 에 넣지 못했습니다.'));
            setJob((j) => (j && j.id === job.id ? { ...j, st: { ...st, status: 'failed' } } : j));
            return;
          }
          finish({ ...r, destination: 'reportarchive_precise' });
          return;
        }
        if (st.status === 'failed' || st.status === 'cancelled') {
          setErr(st.status === 'cancelled' ? '변환을 취소했습니다.' : `변환 실패 — ${st.error || '까닭을 받지 못했습니다'}`);
        }
        setJob((j) => (j && j.id === job.id ? { ...j, st, errs: 0 } : j));
      } catch (e) {
        if (stop) return;
        if (job.errs + 1 < POLL_ERR_MAX) {
          setJob((j) => (j && j.id === job.id ? { ...j, errs: j.errs + 1 } : j));   // 다시 묻는다
          return;
        }
        setErr(e instanceof Error ? e.message : '변환 진행을 못 읽었습니다.');
        setJob((j) => (j && j.id === job.id ? { ...j, st: { job_id: job.id, status: 'failed' } } : j));
      }
    }, POLL_MS);
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
    // finish 는 렌더마다 새로 만들어지지만 cb 로 최신 콜백을 부른다 — 의존성은 잡 상태뿐
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job, done]);

  const go = async () => {
    setBusy(true); setErr('');
    try {
      const r = await dispatchUpload({
        staging_id: staged.staging_id, filename: staged.filename, destination,
      });
      if (r.stage === 'failed') {
        // 0블록처럼 서버가 만들지 않고 돌려준 경우 — 왜 비었는지(가져오기 경고)를 함께 보인다(docs/chat-ppt A4).
        const w = (r.detail as { warnings?: unknown } | undefined)?.warnings;
        const ws = Array.isArray(w) ? w.filter((x): x is string => typeof x === 'string') : [];
        throw new Error(String(r.error || '보내기 실패') + (ws.length ? ` (경고: ${ws.slice(0, 3).join(' · ')}${ws.length > 3 ? ` 외 ${ws.length - 3}건` : ''})` : ''));
      }
      if (destination === 'reportarchive_precise') {
        if (r.stage !== 'dispatched' || !r.job_id) throw new Error('DocForge 가 잡 번호를 주지 않았습니다.');
        setJob({ id: r.job_id, errs: 0 });
        return;
      }
      if (destination === 'chat') {
        // 보낸 것이 아니라 읽어 온 것 — 대화에 '보냈다' 알림을 남기지 않고 입력창에 문서로 붙인다
        if (!r.doc?.text) throw new Error('읽어 온 글이 없습니다.');
        const why = await onAttachDoc?.(new File([r.doc.text], r.doc.name, { type: 'text/markdown' }));
        if (why) throw new Error(why);
        setDone(r);
        return;
      }
      setDone(r);
      const n = dispatchNotice(staged.filename, r);
      if (n) onDispatched?.(n);
      const t = dispatchInstruction(r);
      if (t) onFill?.(t, true);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '보내기 실패');
    } finally {
      setBusy(false);
    }
  };

  if (done && destination === 'chat') {
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>입력창에 붙였습니다</b>
          <span className="upl-file">{done.doc?.name ?? staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <p className="upl-note">
          글 <b>{(done.doc?.chars ?? 0).toLocaleString()}</b>자를 문서로 붙였습니다 — 이제 물어보세요. 어디에도 저장하지 않았습니다.
        </p>
      </div>
    );
  }

  if (job && !done) {
    const st = job.st;
    const running = !st || !['failed', 'cancelled'].includes(st.status);
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>{running ? '정밀 변환 중' : '정밀 변환을 끝내지 못했습니다'}</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        {running && (
          <p className="upl-note" role="status">
            {st?.status === 'done' ? 'Report Archive 에 넣는 중…'
              : `${st?.stage || '줄 서는 중'} · ${Math.round(st?.progress ?? 0)}%`} — 그림 판독이 있으면 몇 분 걸립니다. 이 창을 닫아도 변환은 계속됩니다.
          </p>
        )}
        {err && <div className="upl-err" role="alert">⚠ {err}</div>}
        <div className="upl-actions">
          {running && st?.status !== 'done' && (
            <button type="button" onClick={() => { void docforgeCancel(job.id); }}>변환 취소</button>
          )}
          {!running && <button type="button" onClick={onClose}>닫기</button>}
        </div>
      </div>
    );
  }

  if (done && destination === 'reportarchive_precise') {
    const warns = [...(done.warnings ?? []), ...(done.conversion_warnings ?? [])];
    const link = reportLink(done);
    const ask = dispatchInstruction(done);
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>정밀 변환 보고서를 만들었습니다</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <p className="upl-note">
          보고서 <b>{String(done.report_id ?? '?')}</b>{done.title ? <>「{done.title}」</> : null} —
          {' '}<b>{String(done.pages ?? '?')}</b>쪽 · 블록 <b>{String(done.blocks ?? '?')}</b>개 · 버린 요소 {done.dropped ?? 0}건 ·
          모델 판독 {done.model_written ?? 0}건 · 무음 누락 {done.unaccounted ?? 0}.
          {link
            ? <> <a href={link} target="_blank" rel="noreferrer">Report Archive 에서 열기</a></>
            : <> Report Archive 의 “내가 쓴 보고서” 에서 확인하세요.</>}
        </p>
        {(done.model_written ?? 0) > 0 && (
          <p className="upl-note">‘모델 판독’ 블록은 모델이 그림을 읽은 것입니다 — 원본과 맞는지 확인하세요.</p>
        )}
        <p className="upl-note">대화에 이 결과를 남겼습니다 — 다음 질문에서 근거로 함께 갑니다.</p>
        {ask && (
          <div className="upl-actions">
            <button type="button" className="upl-go" onClick={() => onFill?.(ask)}>검토 지시문을 입력창에 넣기</button>
          </div>
        )}
        {warns.length > 0 && (
          <details className="upl-note">
            <summary>경고 {warns.length}건</summary>
            <ul>{warns.slice(0, 20).map((w) => <li key={w}>{w}</li>)}</ul>
          </details>
        )}
      </div>
    );
  }

  if (done) {
    const warns = done.warnings ?? [];
    const ask = dispatchInstruction(done);
    const link = reportLink(done);
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>{destination === 'reportarchive' ? '보고서 초안을 만들었습니다' : '변환했습니다'}</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <p className="upl-note">
          {destination === 'reportarchive'
            ? <>보고서 <b>{String(done.report_id ?? '?')}</b>{done.title ? <>「{done.title}」</> : null} —
              {' '}<b>{String(done.pages ?? '?')}</b>쪽 · 블록 <b>{String(done.blocks ?? '?')}</b>개가 들어갔습니다.
              {link
                ? <> <a href={link} target="_blank" rel="noreferrer">Report Archive 에서 열기</a> — 확인하고 저장·게시하세요.</>
                : <> Report Archive 의 “내가 쓴 보고서” 에서 확인하고 저장·게시하세요.</>}</>
            : <>지식카드 초안이 나왔습니다(inbox 파일명 <code>{String(done.inbox_name ?? '')}</code>, 아직 저장하지 않았습니다).</>}
        </p>
        <p className="upl-note">
          대화에 이 결과를 남겼습니다 — 다음 질문에서 근거로 함께 갑니다.
          {ask && <> 검토하려면 아래 단추로 지시문을 입력창에 넣고 보내세요.</>}
        </p>
        {ask && (
          <div className="upl-actions">
            <button type="button" className="upl-go" onClick={() => onFill?.(ask)}>검토 지시문을 입력창에 넣기</button>
          </div>
        )}
        {warns.length > 0 && (
          // 변환 못 한 요소를 조용히 넘기면 사용자는 원본에 있던 것이 사라진 줄 모른다.
          <details className="upl-note">
            <summary>변환하지 못한 요소 {warns.length}건</summary>
            <ul>{warns.slice(0, 12).map((w) => <li key={w}>{w}</li>)}</ul>
          </details>
        )}
      </div>
    );
  }

  return (
    <div className="upl-panel">
      <div className="upl-head">
        <b>{spec?.title ?? '보내기'}</b>
        <span className="upl-file">{staged.filename}</span>
        <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
      </div>
      <p className="upl-note">
        {destination === 'reportarchive_precise' && staged.ext === 'md'
          // PC 도우미 추출본(DRM 문서) — 위치 · 차트 값 · 박힌 그림이 없다(DocForge R-D35 · DF-D18). 원본 그대로라고 말하지 않는다.
          ? 'PC 도우미로 가져온 추출본이라 위치 · 차트 값 · 박힌 그림은 없습니다. 슬라이드마다 글 · 표 · 발표자 노트를 옮기고, '
            + '함께 가져온 슬라이드 그림을 그대로 싣고 모델이 읽어 \'모델 판독\' 으로 답니다. 본인 명의로 내 공간에 보고서가 만들어집니다.'
          : spec?.note}
      </p>
      {err && <div className="upl-err" role="alert">⚠ {err}</div>}
      <div className="upl-actions">
        <button type="button" className="upl-go" disabled={busy} onClick={() => void go()}>
          {busy ? '보내는 중… (큰 자료는 몇 분)' : (spec?.go ?? '보내기')}
        </button>
        <button type="button" onClick={onClose}>취소</button>
      </div>
    </div>
  );
}
