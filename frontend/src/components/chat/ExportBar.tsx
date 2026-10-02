// 활성 대화 내보내기 툴바 — HTML / JSON / Word(전문·정리본) 다운로드(ChatPage·DeliberatePage 공용)
import { useCallback, useMemo, useState, type RefObject } from 'react';
import { apiFetch, errorDetail } from '../../api/client';
import { useChat } from '../../state/ChatContext';
import { useCan } from '../../auth/useCan';
import { Menu, MenuSep } from '../ui/Menu';
import { ChatActionBar } from './ChatActionBar';
import { conversationEvidence } from './handoff';
import { HandoffBrief } from './HandoffBrief';
import { downloadBlob, exportHtml, exportJson } from './exportChat';
import { IconDownload, IconSliders } from './icons';

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
  const { conversations, activeId, streaming } = useChat();
  const can = useCan();
  const conv = conversations.find((c) => c.id === activeId);
  const [busy, setBusy] = useState<'' | 'transcript' | 'report'>('');
  const [err, setErr] = useState('');
  const [briefOpen, setBriefOpen] = useState(false); // 심의 브리프 모달(핸드오프 P3)
  // 심의로 넘길 원천 근거(도구결과) 수 — 있을 때만 핸드오프 버튼을 보인다(빈 버튼 방지).
  const evidenceCount = useMemo(() => (conv ? conversationEvidence(conv).length : 0), [conv]);

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
  // 스레드 머리 줄 — 종전엔 버튼 넷이 절대배치로 첫 질문 말풍선을 덮었다(1440·768·390 모두). 흐름 안의 한 줄로 두고,
  // 내보내기는 메뉴 하나로 접는다. 만드는 중이면 메뉴 버튼 이름이 그 상태를 말한다(메뉴는 닫혀도 보이게).
  return (
    <div className="cx-threadbar" role="toolbar" aria-label="대화 도구">
      <span className="cx-threadbar-title" title={conv.title}>
        {conv.title || '새 대화'}
      </span>
      <ChatActionBar />
      {evidenceCount > 0 && can('feat:deliberation') && (
        <button
          type="button"
          className="cx-threadbar-btn"
          onClick={() => setBriefOpen(true)}
          disabled={busy !== '' || streaming}
          title={`이 대화에서 정리한 실데이터 ${evidenceCount}건으로 심의 브리프를 엽니다`}
        >
          <IconSliders width={14} height={14} />
          심의로 넘기기
        </button>
      )}
      <Menu
        className="cx-export-menu"
        label={
          <>
            <IconDownload width={14} height={14} />
            {busy === 'transcript' ? 'Word 만드는 중…' : busy === 'report' ? '정리본 만드는 중…' : '내보내기'}
          </>
        }
      >
        <button type="button" role="menuitem" tabIndex={-1} onClick={onHtml} title="보이는 그대로 HTML 파일로 저장">
          HTML — 보이는 그대로
        </button>
        <button type="button" role="menuitem" tabIndex={-1} onClick={onJson} title="구조화된 JSON 파일로 저장">
          JSON — 구조화 데이터
        </button>
        <MenuSep />
        <button type="button" role="menuitem" tabIndex={-1} disabled={busy !== ''} onClick={() => void onDocx('transcript')}>
          Word — 대화 그대로
        </button>
        <button
          type="button"
          role="menuitem"
          tabIndex={-1}
          disabled={busy !== ''}
          onClick={() => void onDocx('report')}
          title="대화를 읽고 결론·근거·미결로 정리한 Word 보고서 (수십 초 걸립니다)"
        >
          Word 정리본 — 결론·근거·미결
        </button>
      </Menu>
      {briefOpen && conv && <HandoffBrief conv={conv} onClose={() => setBriefOpen(false)} />}
      {err && (
        <span className="cx-export-err" role="alert">
          {err}
        </span>
      )}
    </div>
  );
}
