// 문서(PPT·Word·PDF)를 각 서비스의 **자기 취입기**로 보내는 패널 — 포털은 배달만 한다
import { useState } from 'react';
import { dispatchUpload, type StagedFile } from '../../api/upload.api';

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
  staged, destination, onClose,
}: { staged: StagedFile; destination: string; onClose: () => void }) {
  const spec = SPEC[destination];
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<Record<string, unknown> | null>(null);

  const go = async () => {
    setBusy(true); setErr('');
    try {
      const res = await dispatchUpload({
        staging_id: staged.staging_id, filename: staged.filename, destination,
      });
      const r = res as unknown as Record<string, unknown>;
      if (r.stage === 'failed') throw new Error(String(r.error || '보내기 실패'));
      setDone(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '보내기 실패');
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    const warns = (done.warnings as string[]) ?? [];
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>{destination === 'reportarchive' ? '보고서 초안을 만들었습니다' : '변환했습니다'}</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <p className="upl-note">
          {destination === 'reportarchive'
            ? <>페이지 <b>{String(done.pages ?? '?')}</b>장이 들어갔습니다. Report Archive 의
              “내가 쓴 보고서” 에서 확인하고 저장·게시하세요.</>
            : <>지식카드 초안이 나왔습니다. 챗에서 <b>“방금 변환한 것 검토해 줘”</b> 라고 하면
              모자란 항목을 물어보고 저장까지 이어집니다
              (inbox 파일명 <code>{String(done.inbox_name ?? '')}</code>).</>}
        </p>
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
