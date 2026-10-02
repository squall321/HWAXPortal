import { useEffect } from 'react';
import { useChat } from '../../state/ChatContext';
import { MessageList } from './MessageList';
import { Composer } from './Composer';
import '../../styles/chat.css';

export function ChatDock() {
  const { open, messages, openDock, closeDock } = useChat();

  // Toggle a body class so the main content (.home-wrap / .hero-inner) can reserve
  // space for the fixed dock — the .pgrid auto-fill grid doesn't know about it.
  useEffect(() => {
    document.body.classList.toggle('dock-open', open);
    return () => document.body.classList.remove('dock-open');
  }, [open]);

  return (
    <>
      {!open && (
        <button className="chat-fab" onClick={openDock} aria-label="채팅 열기">
          💬
        </button>
      )}
      {/* 닫힌 독은 화면에 없지만 Tab 순서에는 남아 보이지 않는 정지점 5개가 됐다 — inert 로 통째로 뺀다(React 18 은 문자열 속성). */}
      <aside className="chatdock" aria-hidden={!open} {...(!open ? { inert: '' } : {})}>
        <div className="chat-hd">
          <b>HWAX Assistant</b>
          <button className="chat-x" onClick={closeDock} aria-label="채팅 닫기">
            ×
          </button>
        </div>
        <MessageList messages={messages} />
        <Composer />
      </aside>
    </>
  );
}
