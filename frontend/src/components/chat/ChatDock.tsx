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
      <aside className="chatdock" aria-hidden={!open}>
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
