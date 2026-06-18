import { useEffect, useRef } from 'react';
import type { Message } from '../../types/chat';
import { TextBlock } from './renderers/TextBlock';

function Bubble({ msg }: { msg: Message }) {
  const cls = msg.role === 'user' ? 'chat-msg me' : 'chat-msg bot';
  // A finished assistant turn with no text/error/status (e.g. the model only called a tool
  // and produced no closing text) would otherwise render an empty bubble — show a fallback.
  const emptyDone =
    msg.role !== 'user' && !msg.streaming && !msg.text && !msg.error && !msg.status;
  return (
    <div className={cls}>
      {msg.text && <TextBlock text={msg.text} />}
      {msg.status && <div className="chat-status">{msg.status}</div>}
      {msg.streaming && !msg.text && !msg.status && <div className="chat-status">…</div>}
      {emptyDone && <div className="chat-status">(응답이 없습니다)</div>}
      {msg.error && <div className="chat-error">⚠ {msg.error}</div>}
    </div>
  );
}

export function MessageList({ messages }: { messages: Message[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  // Auto-scroll only when the user is already near the bottom, so streaming tokens don't
  // yank the view down while they're scrolled up reading earlier messages.
  const stickRef = useRef(true);

  const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  useEffect(() => {
    if (stickRef.current) endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  return (
    <div className="chat-body" onScroll={onScroll}>
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
