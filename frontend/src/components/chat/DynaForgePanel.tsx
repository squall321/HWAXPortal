// K파일을 DynaForge 세션으로 보내는 패널 — 세션 이름만 받고 나머지는 서버가 한다
import { useState } from 'react';
import { dispatchUpload, type StagedFile } from '../../api/upload.api';

/** 파일 본문을 챗으로 나르지 않는다. LS-DYNA 덱은 수십 MB 가 흔해 프롬프트에 못 싣는다 —
 *  서버가 스테이징한 **호스트 경로**를 넘기고 DynaForge 가 직접 읽는다(StepForge 와 같은 방식). */
export function DynaForgePanel({ staged, onClose }: { staged: StagedFile; onClose: () => void }) {
  const [name, setName] = useState(staged.filename.replace(/\.[^.]+$/, ''));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<{ session_id: string } | null>(null);

  const go = async () => {
    setBusy(true); setErr('');
    try {
      const res = await dispatchUpload({
        staging_id: staged.staging_id, filename: staged.filename,
        destination: 'dynaforge', project_name: name.trim(),
      });
      const sid = (res as unknown as { session_id?: string }).session_id;
      if (!sid) throw new Error('세션 id 가 오지 않았습니다.');
      setDone({ session_id: sid });
    } catch (e) {
      setErr(e instanceof Error ? e.message : '보내기 실패');
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>DynaForge 세션에 넣었습니다</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <p className="upl-note">
          세션 <code>{done.session_id}</code> 입니다. 이어서 챗에 이렇게 물어보세요 —
          <b> “세션 {done.session_id} 에 뭐가 들어 있어?”</b> (list_session_files·inspect_file 이 답합니다)
        </p>
      </div>
    );
  }

  return (
    <div className="upl-panel">
      <div className="upl-head">
        <b>DynaForge 세션으로</b>
        <span className="upl-file">{staged.filename}</span>
        <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
      </div>
      <p className="upl-note">
        세션은 K파일·오퍼레이션의 작업 공간입니다. 나중에 이 이름으로 찾게 되니 알아볼 수 있게 지으세요.
      </p>
      <label className="upl-field">
        <span>세션 이름</span>
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
      </label>
      {err && <div className="upl-err" role="alert">⚠ {err}</div>}
      <div className="upl-actions">
        <button type="button" className="upl-go" disabled={busy || !name.trim()} onClick={() => void go()}>
          {busy ? '보내는 중…' : '세션 만들고 보내기'}
        </button>
        <button type="button" onClick={onClose}>취소</button>
      </div>
    </div>
  );
}
