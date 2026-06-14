import { useEffect, useRef } from 'react';
import type { Message } from '../../types/chat';
import { TextBlock } from './renderers/TextBlock';

function Bubble({ msg }: { msg: Message }) {
  const cls = msg.role === 'user' ? 'chat-msg me' : 'chat-msg bot';
  return (
    <div className={cls}>
      {msg.text && <TextBlock text={msg.text} />}
      {msg.status && <div className="chat-status">{msg.status}</div>}
      {msg.streaming && !msg.text && !msg.status && <div className="chat-status">…</div>}
      {msg.error && <div className="chat-error">⚠ {msg.error}</div>}
    </div>
  );
}

export function MessageList({ messages }: { messages: Message[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  return (
    <div className="chat-body">
      {messages.length === 0 && (
        <div className="chat-msg bot">
          <TextBlock text="무엇을 도와드릴까요?" />
        </div>
      )}
      {messages.map((m) => (
        <Bubble key={m.id} msg={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
