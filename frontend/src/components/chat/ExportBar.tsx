// 활성 대화 내보내기 툴바 — 보이는 그대로 HTML / 구조화 JSON 다운로드(ChatPage·DeliberatePage 공용)
import { useCallback, type RefObject } from 'react';
import { useChat } from '../../state/ChatContext';
import { exportHtml, exportJson } from './exportChat';
import { IconDownload } from './icons';

export function ExportBar({ threadRef }: { threadRef: RefObject<HTMLDivElement | null> }) {
  const { conversations, activeId } = useChat();
  const conv = conversations.find((c) => c.id === activeId);

  const onHtml = useCallback(() => {
    if (conv && threadRef.current) exportHtml(threadRef.current, conv);
  }, [conv, threadRef]);

  const onJson = useCallback(() => {
    if (conv) exportJson(conv);
  }, [conv]);

  if (!conv || conv.messages.length === 0) return null;
  return (
    <div className="cx-export" role="toolbar" aria-label="대화 내보내기">
      <button type="button" className="cx-export-btn" onClick={onHtml} title="보이는 그대로 HTML 파일로 저장">
        <IconDownload width={13} height={13} />
        HTML
      </button>
      <button type="button" className="cx-export-btn" onClick={onJson} title="구조화된 JSON 파일로 저장">
        <IconDownload width={13} height={13} />
        JSON
      </button>
    </div>
  );
}
