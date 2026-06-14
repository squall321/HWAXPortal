import type { FormEvent } from 'react';
import { useChat } from '../../state/ChatContext';

export function Composer() {
  const { input, setInput, send, cancel, streaming } = useChat();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (streaming) {
      cancel();
      return;
    }
    send(input);
  };

  return (
    <form className="chat-in" onSubmit={onSubmit}>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="메시지 입력…"
        aria-label="메시지 입력"
      />
      <button type="submit" className="chat-send">
        {streaming ? '중지' : '전송'}
      </button>
    </form>
  );
}
