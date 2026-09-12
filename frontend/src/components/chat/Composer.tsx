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
import { shortName } from './personaColor';
import { SourcePanel } from './SourcePanel';
import { ThinkPanel } from './ThinkPanel';
import { IconSend, IconStop } from './icons';
import { useAuth } from '../../auth/useAuth';
import { useCan } from '../../auth/useCan';
import { canUpload, uploadFile, type StagedFile } from '../../api/upload.api';
import { classify, readDoc, kindLabel, unitsLabel, isEncryptedOffice, DOC_MAX } from './docAttach';
import { DocExtractHint } from './DocExtractHint';
import { DocActions } from './DocActions';
import { UploadRouter } from './UploadRouter';

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
  const { input, setInput, sendMessage, stop, streaming, pinnedTools, setPinnedTools, pinnedApps, setPinnedApps, pinnedAgent, pinnedAgentName, setPinnedAgent, pinnedHelpers, setPinnedHelpers, attachedDocs, setAttachedDocs } =
    useChat();
  const taRef = useRef<HTMLTextAreaElement>(null);
  const { user } = useAuth();
  // 권한이 없으면 입구를 아예 숨긴다(docs/access-control). 업로드는 종전 그룹 설정도 인정한다.
  const can = useCan();
  const canUp = can('feat:upload') || canUpload(user?.groups);
  const fileRef = useRef<HTMLInputElement>(null);
  const [staged, setStaged] = useState<StagedFile | null>(null);
  const [upErr, setUpErr] = useState('');
  // Office 원본을 붙였을 때 띄우는 안내 — DRM 때문에 추출은 이 PC 에서 해야 한다.
  // 이름만이 아니라 **바이트**로 갈린다 — DRM 이 브라우저에도 투명하면 평문이 읽히고,
  // 그러면 COM 추출이 필요 없다(서버가 그대로 파싱한다). 짐작하지 않고 본다.
  const [comFile, setComFile] = useState<{ name: string; encrypted: boolean | null } | null>(null);
  // 붙인 파일이 갈 곳은 셋이고 **내용을 읽기 전에** 갈린다(확장자로만 판정).
  //   text      추출문·평문 → 브라우저에서 그대로 읽어 챗·심의 근거로. 서버에 안 올린다.
  //   needs-com PPT·Word·PDF 원본 → 서버가 파싱하면 DRM 에 막힌다. PC 추출 안내를 띄운다.
  //   upload    물성 CSV·STEP 등 → 종전 목적지 선택 경로 그대로.
  const onPick = useCallback(async (f: File | undefined) => {
    if (!f) return;
    setUpErr(''); setComFile(null);
    const verdict = classify(f.name);
    if (verdict === 'needs-com') {
      setComFile({ name: f.name, encrypted: await isEncryptedOffice(f) });
      return;
    }
    if (verdict === 'text') {
      if (attachedDocs.length >= DOC_MAX) { setUpErr(`문서는 한 번에 ${DOC_MAX}건까지 붙일 수 있습니다.`); return; }
      try { setAttachedDocs([...attachedDocs, await readDoc(f)]); }
      catch (e) { setUpErr(e instanceof Error ? e.message : '문서를 읽지 못했습니다.'); }
      return;
    }
    try { setStaged(await uploadFile(f)); }
    catch (e) { setUpErr(e instanceof Error ? e.message : '업로드 실패'); }
  }, [attachedDocs, setAttachedDocs]);

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
      {can('plat:webresearch') && <SourcePanel />}
      {can('feat:thinking') && <ThinkPanel />}
      {/* 지정 전문가·도구 칩 — 이 대화에 적용될 선택을 항상 보이게(× 로 즉시 해제). */}
      {(pinnedTools.length > 0 || pinnedApps.length > 0 || pinnedAgent || pinnedHelpers.length > 0) && (
        <div className="composer-pins" aria-label="지정 전문가·앱·도구">
          {pinnedAgent && (
            // 기계 키가 아니라 사람 이름을 보여 준다 — 키는 툴팁으로 남긴다(구 저장분은 이름이 없어
            // 키가 그대로 보인다).
            <span className="composer-pin composer-pin-agent" title={`지정 전문가 페르소나 — ${pinnedAgent}`}>
              👤 {shortName(pinnedAgentName || pinnedAgent)}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedAgent(null)}
                aria-label={`전문가 ${pinnedAgentName || pinnedAgent} 해제`}
                title="전문가 해제"
              >
                ×
              </button>
            </span>
          )}
          {/* 보조 전문가 — 답은 주 전문가 한 목소리이고 이들은 판단 기준·도구만 빌려준다.
              누가 서 있는지 안 보이면 왜 그 도구를 쓰는지 알 수 없다. */}
          {pinnedHelpers.map((h) => (
            <span key={h.key} className="composer-pin" title={`보조 전문가 — ${h.key}`}>
              ＋{shortName(h.name || h.key)}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedHelpers(pinnedHelpers.filter((x) => x.key !== h.key))}
                aria-label={`보조 전문가 ${h.name || h.key} 빼기`}
                title="보조 빼기"
              >
                ×
              </button>
            </span>
          ))}
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
      {staged && <UploadRouter staged={staged} onClose={() => setStaged(null)} />}
      {comFile && <DocExtractHint filename={comFile.name} encrypted={comFile.encrypted}
        onClose={() => setComFile(null)} />}
      {attachedDocs.length > 0 && (
        <div className="doc-chips">
          {attachedDocs.map((d, i) => (
            <span key={`${d.name}-${i}`} className="doc-chip" title={`${d.chars.toLocaleString()}자`}>
              📄 {d.name}
              <em>{[kindLabel(d.meta), unitsLabel(d.meta), `${d.chars.toLocaleString()}자`].filter(Boolean).join(' · ')}</em>
              {d.truncated && <b className="doc-chip-cut">잘림</b>}
              <button type="button" onClick={() => setAttachedDocs(attachedDocs.filter((_, j) => j !== i))}
                aria-label={`${d.name} 떼기`}>×</button>
            </span>
          ))}
        </div>
      )}
      {attachedDocs.length > 0 && (
        <DocActions docs={attachedDocs} onFill={(t) => { setInput(t); taRef.current?.focus(); }} />
      )}
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
            <input ref={fileRef} type="file"
              accept=".md,.txt,.pptx,.ppt,.docx,.doc,.pdf,.htm,.html,.csv,.xlsx,.step,.stp,.msh,.zip,.k,.key,.dyn,.inc"
              style={{ display: 'none' }}
              onChange={(e) => void onPick(e.target.files?.[0] ?? undefined)} />
            <button type="button" className="composer-btn composer-attach"
              onClick={() => fileRef.current?.click()}
              aria-label="파일 붙이기" title="파일 붙이기 — 문서(PPT·Word·PDF) · 물성 CSV · STEP·MSH·ZIP · K파일">+</button>
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
