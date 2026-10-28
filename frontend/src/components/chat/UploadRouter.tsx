// 업로드 목적지 되묻기 — 파일을 받은 뒤 "어디로 보낼까요" 를 사람에게 묻는다.
// 확장자로 자동 라우팅하지 않는 이유는 PLAN-destinations.md 참조 — 같은 확장자를 다른 곳에
// 넣고 싶은 경우가 있고, 파급이 큰 곳일수록 사람이 확인해야 한다.
import { useState } from 'react';
import type { StagedFile } from '../../api/upload.api';
import { useChat } from '../../state/ChatContext';
import { DEST_APPS } from './destApps';
import { DocDispatchPanel } from './DocDispatchPanel';
import { DynaForgePanel } from './DynaForgePanel';
import { StepForgePanel } from './StepForgePanel';
import { UploadPanel } from './UploadPanel';
import type { UploadNotice } from './uploadNotice';

/** 바이트 → MB(소수 한 자리). */
const mb = (n: number) => (n / (1024 * 1024)).toFixed(1).replace(/\.0$/, '');

export function UploadRouter({ staged, onClose, onFill, onDispatched, onAttachDoc }: {
  staged: StagedFile;
  onClose: () => void;
  /** 문서 갈래(RA · AIDH) 성공 뒤 — 지시문을 입력창에(auto 면 비어 있을 때만) · 대화에 알림(docs/chat-ppt A1 · A2). */
  onFill?: (text: string, auto?: boolean) => void;
  onDispatched?: (n: UploadNotice) => void;
  /** 이 대화에서 분석 — 읽어 온 글을 문서 칩으로(docs/chat-ppt PP-D17). */
  onAttachDoc?: (doc: File) => Promise<string | void>;
}) {
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
          {[...dests].sort((a, b) => (a.id === rec ? -1 : b.id === rec ? 1 : 0)).map((d) => {
            // 크기 한도를 넘는 목적지는 고르기 전에 막는다 — 업로드를 다 한 뒤에야 '파일이 너무 큽니다.' 를 보던 길이다(HP-02).
            const over = !!d.max_bytes && staged.size > d.max_bytes;
            return (
              <button key={d.id} type="button" disabled={over}
                className={d.id === rec ? 'upl-go upl-rec' : 'upl-go'}
                title={over ? `한도 ${mb(d.max_bytes!)} MB 를 넘습니다(${mb(staged.size)} MB)` : undefined}
                onClick={() => setPicked(d.id)}>
                {d.label}{d.id === rec && <em> · 지금 전문가</em>}
                {over && <em> · 한도 {mb(d.max_bytes!)} MB 넘음</em>}
              </button>
            );
          })}
        </div>
        {dests.some((d) => d.max_bytes && staged.size > d.max_bytes) && (
          <p className="upl-note">
            {mb(staged.size)} MB 라 한도가 있는 곳으로는 보낼 수 없습니다 — 사진을 압축하거나 나눠 보내거나, 한도가 없는 곳(AI 데이터 허브 등)으로 보내세요.
          </p>
        )}
      </div>
    );
  }

  if (picked === 'stepforge') return <StepForgePanel staged={staged} onClose={onClose} />;
  if (picked === 'dynaforge') return <DynaForgePanel staged={staged} onClose={onClose} />;
  if (picked === 'reportarchive' || picked === 'reportarchive_precise' || picked === 'aidatahub' || picked === 'chat')
    return (
      <DocDispatchPanel staged={staged} destination={picked} onClose={onClose} onFill={onFill}
        onDispatched={onDispatched} onAttachDoc={onAttachDoc} />
    );
  return <UploadPanel staged={staged} onClose={onClose} />;
}
