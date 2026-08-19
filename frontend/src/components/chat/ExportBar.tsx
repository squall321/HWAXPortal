// 활성 대화 내보내기 툴바 — HTML / JSON / Word(전문·정리본) 다운로드(ChatPage·DeliberatePage 공용)
import { useCallback, useState, type RefObject } from 'react';
import { apiFetch, errorDetail } from '../../api/client';
import { useChat } from '../../state/ChatContext';
import { downloadBlob, exportHtml, exportJson } from './exportChat';
import { IconDownload } from './icons';

// Word 는 서버가 만든다(python-docx). 브라우저에서 만들려면 프론트에 새 의존성이 붙고,
// 서식 규칙이 두 곳으로 갈린다.
//   전문   — 있는 그대로. 즉시 나온다.
//   정리본 — LLM 이 읽고 보고서로 재구성. 왕복이 있어 수십 초 걸린다.
async function exportDocx(conv: unknown, mode: 'transcript' | 'report'): Promise<string | null> {
  // 챗과 같은 이유로 apiFetch 를 쓴다 — access token 이 900초라 화면을 오래 띄워 두면
  // raw fetch 는 401 로 조용히 실패하고, 사용자에겐 "가끔 안 되는 버튼"으로 보인다.
  const res = await apiFetch('/agent/export/docx', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation: conv, mode }),
  });
  if (!res.ok) {
    // 실패를 조용히 넘기지 않는다 — 눌렀는데 아무 일도 안 일어나면 사용자는 다시 누른다.
    // detail 은 문자열일 수도 배열일 수도 있다(pydantic 검증 오류). 문자열로 가정하고
    // 그대로 렌더하면 화면에 "[object Object]" 가 뜬다 — 공용 정규화를 쓴다.
    const fallback = `내보내기에 실패했습니다 (HTTP ${res.status}).`;
    try {
      const j = await res.json();
      return errorDetail(j?.detail, fallback);
    } catch {
      return fallback;   /* 본문이 JSON 이 아니면 기본 문구 */
    }
  }
  const cd = res.headers.get('Content-Disposition') || '';
  const m = /filename\*=UTF-8''([^;]+)/.exec(cd);
  const name = m ? decodeURIComponent(m[1]) : '대화.docx';
  downloadBlob(name, await res.blob());
  return null;
}

export function ExportBar({ threadRef }: { threadRef: RefObject<HTMLDivElement | null> }) {
  const { conversations, activeId } = useChat();
  const conv = conversations.find((c) => c.id === activeId);
  const [busy, setBusy] = useState<'' | 'transcript' | 'report'>('');
  const [err, setErr] = useState('');

  const onHtml = useCallback(() => {
    if (conv && threadRef.current) exportHtml(threadRef.current, conv);
  }, [conv, threadRef]);

  const onJson = useCallback(() => {
    if (conv) exportJson(conv);
  }, [conv]);

  const onDocx = useCallback(
    async (mode: 'transcript' | 'report') => {
      if (!conv || busy) return;
      setBusy(mode);
      setErr('');
      setErr((await exportDocx(conv, mode)) ?? '');
      setBusy('');
    },
    [conv, busy],
  );

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
      <button
        type="button"
        className="cx-export-btn"
        onClick={() => void onDocx('transcript')}
        disabled={busy !== ''}
        title="대화를 있는 그대로 Word 문서로 저장"
      >
        <IconDownload width={13} height={13} />
        {busy === 'transcript' ? '만드는 중…' : 'Word'}
      </button>
      <button
        type="button"
        className="cx-export-btn"
        onClick={() => void onDocx('report')}
        disabled={busy !== ''}
        title="대화를 읽고 결론·근거·미결로 정리한 Word 보고서 (수십 초 걸립니다)"
      >
        <IconDownload width={13} height={13} />
        {busy === 'report' ? '정리 중…' : 'Word 정리본'}
      </button>
      {err && (
        <span className="cx-export-err" role="alert">
          {err}
        </span>
      )}
    </div>
  );
}
