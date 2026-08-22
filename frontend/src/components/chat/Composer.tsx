// 메시지 컴포저 — 자동 높이 textarea, Enter 전송/Shift+Enter 줄바꿈(IME 안전), 스트리밍 중지 버튼
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react';
import { useChat } from '../../state/ChatContext';
import { SourcePanel } from './SourcePanel';
import { IconSend, IconStop } from './icons';
import { useAuth } from '../../auth/useAuth';
import { canUpload, uploadFile, type StagedFile } from '../../api/upload.api';
import { UploadPanel } from './UploadPanel';

export interface ComposerHandle {
  focus: () => void;
}

interface ComposerProps {
  autoFocus?: boolean;
  placeholder?: string;
  /** 힌트 라인(Enter 전송 · Shift+Enter 줄바꿈) 표시 여부 — 독에서는 생략. */
  showHint?: boolean;
  /** 전송 가로채기 — 주어지면 sendMessage 대신 이 콜백을 호출(심의 전 전문가 선정 단계 진입). */
  onSubmitText?: (text: string) => void;
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { autoFocus = false, placeholder = '무엇이든 물어보세요…', showHint = false, onSubmitText },
  ref,
) {
  const { input, setInput, sendMessage, stop, streaming, pinnedTools, setPinnedTools, pinnedApps, setPinnedApps, pinnedAgent, setPinnedAgent } =
    useChat();
  const taRef = useRef<HTMLTextAreaElement>(null);
  const { user } = useAuth();
  const canUp = canUpload(user?.groups);
  const fileRef = useRef<HTMLInputElement>(null);
  const [staged, setStaged] = useState<StagedFile | null>(null);
  const [upErr, setUpErr] = useState('');
  const onPick = useCallback(async (f: File | undefined) => {
    if (!f) return;
    setUpErr('');
    try { setStaged(await uploadFile(f)); }
    catch (e) { setUpErr(e instanceof Error ? e.message : '업로드 실패'); }
  }, []);

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
    const text = input.trim();
    if (!text) return;
    if (onSubmitText) onSubmitText(text);
    else sendMessage(input);
  }, [streaming, sendMessage, input, onSubmitText]);

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
      <SourcePanel />
      {/* 지정 전문가·도구 칩 — 이 대화에 적용될 선택을 항상 보이게(× 로 즉시 해제). */}
      {(pinnedTools.length > 0 || pinnedApps.length > 0 || pinnedAgent) && (
        <div className="composer-pins" aria-label="지정 전문가·앱·도구">
          {pinnedAgent && (
            <span className="composer-pin composer-pin-agent" title="지정 전문가 페르소나">
              👤 {pinnedAgent}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedAgent(null)}
                aria-label={`전문가 ${pinnedAgent} 해제`}
                title="전문가 해제"
              >
                ×
              </button>
            </span>
          )}
          {pinnedApps.length > 0 && <span className="composer-pins-label">지정 앱</span>}
          {pinnedApps.map((k) => (
            <span key={k} className="composer-pin composer-pin-app" title="이 앱의 기능 전체를 우선 사용">
              {k}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedApps(pinnedApps.filter((x) => x !== k))}
                aria-label={`앱 ${k} 지정 해제`}
                title="지정 해제"
              >
                ×
              </button>
            </span>
          ))}
          {pinnedTools.length > 0 && <span className="composer-pins-label">지정 도구</span>}
          {pinnedTools.map((n) => (
            <span key={n} className="composer-pin">
              {n}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedTools(pinnedTools.filter((x) => x !== n))}
                aria-label={`${n} 지정 해제`}
                title="지정 해제"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      {staged && <UploadPanel staged={staged} onClose={() => setStaged(null)} />}
      {upErr && <div className="upl-err" role="alert">⚠ {upErr}</div>}
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
        {canUp && !streaming && (
          <>
            <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }}
              onChange={(e) => void onPick(e.target.files?.[0] ?? undefined)} />
            <button type="button" className="composer-btn composer-attach"
              onClick={() => fileRef.current?.click()}
              aria-label="물성 파일 업로드" title="물성 파일 업로드 (CSV)">+</button>
          </>
        )}
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
