// 문서(PPT·Word·PDF)를 각 서비스의 **자기 취입기**로 보내는 패널 — 포털은 배달만 한다
import { useState } from 'react';
import { dispatchUpload, type DispatchResult, type StagedFile } from '../../api/upload.api';
import { dispatchInstruction, dispatchNotice, reportLink, type UploadNotice } from './uploadNotice';

const SPEC: Record<string, { title: string; note: string; go: string }> = {
  reportarchive: {
    title: 'Report Archive 로 보내기',
    // RA 의 /imports/pptx 를 그대로 쓴다 — 포털에 파서를 새로 만들지 않는다.
    note: '슬라이드 한 장이 보고서 페이지 한 장이 됩니다. 제목·본문·표·그림이 위젯으로 들어갑니다. '
      + '초안으로 만들어지니 확인하고 저장·게시하세요.',
    go: '보고서 초안 만들기',
  },
  aidatahub: {
    title: 'AI 데이터 허브로 보내기',
    note: '서버가 정밀 변환해 지식카드 **초안**을 만듭니다. 바로 저장하지 않습니다 — '
      + '모자란 항목(팀·그룹 등)은 챗에서 확인한 뒤 저장합니다.',
    go: '변환하기',
  },
};

export function DocDispatchPanel({
  staged, destination, onClose, onFill, onDispatched,
}: {
  staged: StagedFile;
  destination: string;
  onClose: () => void;
  /** 지시문을 입력창에 — auto 면 입력창이 비어 있을 때만 넣는다(사람이 쓰던 글을 지우지 않는다, docs/chat-ppt PP-D4). */
  onFill?: (text: string, auto?: boolean) => void;
  /** 보내기 성공을 대화에 남긴다(알림 한 건 + 업로드 근거, PP-D3). 종전엔 결과가 이 패널 안에서만 끝났다. */
  onDispatched?: (n: UploadNotice) => void;
}) {
  const spec = SPEC[destination];
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<DispatchResult | null>(null);

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
      <p className="upl-note">{spec?.note}</p>
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
