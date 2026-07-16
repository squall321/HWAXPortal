// 대화 메시지 목록 — 클로드 스타일(어시스턴트 좌측 와이드/유저 버블), 스티키 자동 스크롤 + 하단 이동 버튼
import { useEffect, useRef, useState } from 'react';
import type { Message } from '../../types/chat';
import { copyText } from './clipboard';
import { IconArrowDown, IconCheck, IconCopy } from './icons';
import { TextBlock } from './renderers/TextBlock';

function CopyAction({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = () => {
    void copyText(text).then((ok) => {
      if (!ok) return;
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button type="button" className="msg-copy" onClick={onCopy} aria-label="응답 복사">
      {copied ? <IconCheck width={14} height={14} /> : <IconCopy width={14} height={14} />}
      <span>{copied ? '복사됨' : '복사'}</span>
    </button>
  );
}

function Row({ msg }: { msg: Message }) {
  if (msg.role === 'user') {
    return (
      <div className="msg user">
        <div className="msg-bubble">
          <TextBlock text={msg.text} />
        </div>
      </div>
    );
  }

  const thinking = Boolean(msg.streaming) && !msg.text;
  // A finished assistant turn with no text/error (e.g. the model only called a tool
  // and produced no closing text) would otherwise render empty — show a fallback.
  const emptyDone = !msg.streaming && !msg.text && !msg.error && !msg.status;

  return (
    <div className="msg assistant">
      <div className="msg-content">
        {msg.text && <TextBlock text={msg.text} cursor={Boolean(msg.streaming)} />}
        {/* 토큰이 흐른 뒤에도 도구 호출 등으로 status가 다시 올 수 있다 — 텍스트 아래에 표시. */}
        {msg.text && msg.status && <div className="msg-status-text">{msg.status}</div>}
        {thinking && (
          <div className="msg-thinking" aria-label="응답 생성 중">
            {msg.status ? (
              <span className="msg-status-text">{msg.status}</span>
            ) : (
              <span className="typing-dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
            )}
          </div>
        )}
        {emptyDone && <div className="msg-status-text">(응답이 없습니다)</div>}
        {msg.error && <div className="chat-error">⚠ {msg.error}</div>}
      </div>
      {!msg.streaming && msg.text && (
        <div className="msg-actions">
          <CopyAction text={msg.text} />
        </div>
      )}
    </div>
  );
}

export function MessageList({ messages }: { messages: Message[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  // Auto-scroll only when the user is already near the bottom, so streaming tokens don't
  // yank the view down while they're scrolled up reading earlier messages.
  const stickRef = useRef(true);
  const [stuck, setStuck] = useState(true);

  const onScroll = () => {
    const el = bodyRef.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    stickRef.current = near;
    setStuck(near);
  };

  useEffect(() => {
    if (stickRef.current) endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  const jumpToEnd = () => {
    stickRef.current = true;
    setStuck(true);
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
  };

  return (
    <div className="msg-wrap">
      <div className="chat-body" ref={bodyRef} onScroll={onScroll}>
        <div className="chat-col">
          {messages.length === 0 && (
            <div className="msg assistant">
              <div className="msg-content">
                <TextBlock text="무엇을 도와드릴까요?" />
              </div>
            </div>
          )}
          {messages.map((m) => (
            <Row key={m.id} msg={m} />
          ))}
          <div ref={endRef} />
        </div>
      </div>
      {!stuck && (
        <button type="button" className="msg-jump" onClick={jumpToEnd} aria-label="맨 아래로 이동">
          <IconArrowDown width={15} height={15} />
        </button>
      )}
    </div>
  );
}
