// 업로드 목적지 되묻기 — 파일을 받은 뒤 "어디로 보낼까요" 를 사람에게 묻는다.
// 확장자로 자동 라우팅하지 않는 이유는 PLAN-destinations.md 참조 — 같은 확장자를 다른 곳에
// 넣고 싶은 경우가 있고, 파급이 큰 곳일수록 사람이 확인해야 한다.
import { useState } from 'react';
import type { StagedFile } from '../../api/upload.api';
import { useChat } from '../../state/ChatContext';
import { DEST_APPS } from './destApps';
import { DynaForgePanel } from './DynaForgePanel';
import { StepForgePanel } from './StepForgePanel';
import { UploadPanel } from './UploadPanel';

export function UploadRouter({ staged, onClose }: { staged: StagedFile; onClose: () => void }) {
  const dests = staged.destinations ?? [];
  const { pinnedApps } = useChat();
  // ⚠ 종전에는 목적지가 하나면 묻지 않고 바로 들어갔다. 목적지는 계속 는다 — 하나일 때
  // 자동으로 가면, 둘이 되는 순간 사람은 이미 "올리면 알아서 간다" 로 학습돼 있다.
  // 되돌리기 어려운 일에서 그 어긋남은 위험하다. 그래서 하나여도 고르게 한다.
  const [picked, setPicked] = useState<string>('');
  // 지금 고른 전문가가 그 앱의 운영자면 그쪽을 추천으로 앞세운다(고르는 건 여전히 사람).
  const rec = dests.find((d) => (DEST_APPS[d.id] ?? []).some((a) => pinnedApps.includes(a)))?.id;

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
          {[...dests].sort((a, b) => (a.id === rec ? -1 : b.id === rec ? 1 : 0)).map((d) => (
            <button key={d.id} type="button"
              className={d.id === rec ? 'upl-go upl-rec' : 'upl-go'}
              onClick={() => setPicked(d.id)}>
              {d.label}{d.id === rec && <em> · 지금 전문가</em>}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (picked === 'stepforge') return <StepForgePanel staged={staged} onClose={onClose} />;
  if (picked === 'dynaforge') return <DynaForgePanel staged={staged} onClose={onClose} />;
  return <UploadPanel staged={staged} onClose={onClose} />;
}
