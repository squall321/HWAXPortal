// 챗 메인 페이지 — 헤더 아래 전체화면 2단 레이아웃(이력 사이드바 + 활성 대화), 빈 상태는 클로드식 랜딩
import { useCallback, useRef, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import { useChat } from '../state/ChatContext';
import { ChatSidebar } from '../components/chat/ChatSidebar';
import { Composer, type ComposerHandle } from '../components/chat/Composer';
import { MessageList } from '../components/chat/MessageList';
import { IconPanel, IconPlus, IconSpark } from '../components/chat/icons';
import { loadSidebarOpen, saveSidebarOpen } from '../state/chatStore';
import '../styles/chat.css';
import '../styles/chatpage.css';

const EXAMPLE_PROMPTS = [
  '이 포털 사용법을 알려줘 — 내 Claude에 연결하려면?',
  '이 포털에서 무엇을 할 수 있는지 알려줘',
  '배터리 스웰링 관련 백서 내용을 정리해줘',
  '시험 신호 데이터의 전처리 방법을 추천해줘',
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 6) return '늦은 밤까지 수고가 많으세요';
  if (h < 12) return '좋은 아침이에요';
  if (h < 18) return '안녕하세요';
  return '좋은 저녁이에요';
}

const isNarrow = () => window.matchMedia('(max-width: 900px)').matches;

export default function ChatPage() {
  const { user } = useAuth();
  const { messages, activeId, setInput, newConversation } = useChat();
  const composerRef = useRef<ComposerHandle>(null);
  // 데스크톱은 저장된 선호를 따르고, 좁은 화면은 오버레이라 기본 닫힘.
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow() && loadSidebarOpen());

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((v) => {
      const next = !v;
      if (!isNarrow()) saveSidebarOpen(next);
      return next;
    });
  }, []);

  // 모바일 오버레이에서 대화 선택/새 대화 시 사이드바를 닫아 대화로 복귀.
  const onSidebarNavigate = useCallback(() => {
    if (isNarrow()) setSidebarOpen(false);
  }, []);

  const fillPrompt = (text: string) => {
    setInput(text);
    composerRef.current?.focus();
  };

  const empty = messages.length === 0;

  return (
    <div className="cx-root">
      <ChatSidebar open={sidebarOpen} onToggle={toggleSidebar} onNavigate={onSidebarNavigate} />
      <div
        className={`cx-backdrop${sidebarOpen ? ' show' : ''}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <section className="cx-main" aria-label="대화">
        {!sidebarOpen && (
          <div className="cx-mainbar">
            <button
              type="button"
              className="cx-fab"
              onClick={toggleSidebar}
              aria-label="사이드바 열기"
              title="사이드바 열기"
            >
              <IconPanel width={16} height={16} />
            </button>
            <button
              type="button"
              className="cx-fab"
              onClick={newConversation}
              aria-label="새 대화"
              title="새 대화"
            >
              <IconPlus width={16} height={16} />
            </button>
          </div>
        )}

        {empty ? (
          <div className="cx-hero" key={activeId ?? 'new'}>
            <div className="cx-hero-inner">
              <div className="cx-hero-mark" aria-hidden="true">
                <IconSpark width={30} height={30} />
              </div>
              <p className="cx-hero-kicker">
                {greeting()}
                {user?.display_name ? `, ${user.display_name}님` : ''}
              </p>
              <h1 className="cx-hero-title">무엇을 도와드릴까요?</h1>
              <Composer ref={composerRef} autoFocus showHint />
              <div className="cx-chips">
                {EXAMPLE_PROMPTS.map((p) => (
                  <button type="button" key={p} className="cx-chip" onClick={() => fillPrompt(p)}>
                    {p}
                  </button>
                ))}
              </div>
              <p className="cx-hero-sub">
                요청을 이해해 알맞은 플랫폼으로 연결하고 결과를 대화로 돌려드립니다.
              </p>
            </div>
          </div>
        ) : (
          <div className="cx-thread" key={activeId ?? 'thread'}>
            <MessageList messages={messages} />
            <div className="cx-composer-dock">
              <Composer ref={composerRef} autoFocus showHint placeholder="답장을 입력하세요…" />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
