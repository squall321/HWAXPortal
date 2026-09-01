// 업로드 목적지 되묻기 — 파일을 받은 뒤 "어디로 보낼까요" 를 사람에게 묻는다.
// 확장자로 자동 라우팅하지 않는 이유는 PLAN-destinations.md 참조 — 같은 확장자를 다른 곳에
// 넣고 싶은 경우가 있고, 파급이 큰 곳일수록 사람이 확인해야 한다.
import { useState } from 'react';
import type { StagedFile } from '../../api/upload.api';
import { StepForgePanel } from './StepForgePanel';
import { UploadPanel } from './UploadPanel';

export function UploadRouter({ staged, onClose }: { staged: StagedFile; onClose: () => void }) {
  const dests = staged.destinations ?? [];
  // 고를 게 하나뿐이면 묻지 않는다 — 버튼 하나짜리 질문은 방해일 뿐이다.
  const [picked, setPicked] = useState<string>(dests.length === 1 ? dests[0].id : '');

  if (dests.length === 0) {
    return (
      <div className="upl-panel" role="alert">
        <div className="upl-head">
          <b>보낼 곳이 없습니다</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <p className="upl-note">
          <b>.{staged.ext}</b> 를 받을 수 있는 목적지 중 권한이 있는 곳이 없습니다.
          담당 그룹에 속해 있는지 확인해 주세요.
        </p>
      </div>
    );
  }

  if (!picked) {
    return (
      <div className="upl-panel">
        <div className="upl-head">
          <b>어디로 보낼까요</b>
          <span className="upl-file">{staged.filename}</span>
          <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">✕</button>
        </div>
        <div className="upl-actions upl-dests">
          {dests.map((d) => (
            <button key={d.id} type="button" className="upl-go" onClick={() => setPicked(d.id)}>
              {d.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (picked === 'stepforge') return <StepForgePanel staged={staged} onClose={onClose} />;
  return <UploadPanel staged={staged} onClose={onClose} />;
}
