// 메시지 컴포저 — 자동 높이 textarea, Enter 전송/Shift+Enter 줄바꿈(IME 안전), 스트리밍 중지 버튼
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  type FormEvent,
  type KeyboardEvent,
} from 'react';
import { useChat } from '../../state/ChatContext';
import { IconSend, IconStop } from './icons';

export interface ComposerHandle {
  focus: () => void;
}

interface ComposerProps {
  autoFocus?: boolean;
  placeholder?: string;
  /** 힌트 라인(Enter 전송 · Shift+Enter 줄바꿈) 표시 여부 — 독에서는 생략. */
  showHint?: boolean;
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { autoFocus = false, placeholder = '무엇이든 물어보세요…', showHint = false },
  ref,
) {
  const { input, setInput, sendMessage, stop, streaming } = useChat();
  const taRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({ focus: () => taRef.current?.focus() }), []);

  // textarea 자동 높이 — 값이 바뀔 때마다 scrollHeight에 맞춰 늘리고 max는 CSS가 자른다.
  useLayoutEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${ta.scrollHeight}px`;
  }, [input]);

  useEffect(() => {
    if (autoFocus) taRef.current?.focus();
  }, [autoFocus]);

  const submit = useCallback(() => {
    if (streaming) return;
    sendMessage(input);
  }, [streaming, sendMessage, input]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 한글 조합 중 Enter(isComposing)는 전송이 아니라 조합 확정 — 반드시 무시한다.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = input.trim().length > 0 && !streaming;

  return (
    <form className="composer" onSubmit={onSubmit}>
      <div className="composer-box">
        <textarea
          ref={taRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          aria-label="메시지 입력"
        />
        {streaming ? (
          <button
            type="button"
            className="composer-btn composer-stop"
            onClick={stop}
            aria-label="응답 중지"
            title="응답 중지"
          >
            <IconStop width={17} height={17} />
          </button>
        ) : (
          <button
            type="submit"
            className="composer-btn composer-send"
            disabled={!canSend}
            aria-label="전송"
            title="전송 (Enter)"
          >
            <IconSend width={17} height={17} />
          </button>
        )}
      </div>
      {showHint && (
        <div className="composer-hint" aria-hidden="true">
          {streaming ? '응답 생성 중… 중지하려면 ■ 버튼' : 'Enter 전송 · Shift+Enter 줄바꿈'}
        </div>
      )}
    </form>
  );
});
