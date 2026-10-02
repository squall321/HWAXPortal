// 챗 메인 페이지 — 헤더 아래 전체화면 2단 레이아웃(이력 사이드바 + 활성 대화), 빈 상태는 클로드식 랜딩
import { useCallback, useRef, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import { useCan } from '../auth/useCan';
import { useChat } from '../state/ChatContext';
import { ActivityPanel } from '../components/chat/ActivityPanel';
import { ChatSidebar } from '../components/chat/ChatSidebar';
import { Composer, type ComposerHandle } from '../components/chat/Composer';
import { StartPicker } from '../components/chat/StartPicker';
import { ExportBar } from '../components/chat/ExportBar';
import { MessageList } from '../components/chat/MessageList';
import {
  IconBook,
  IconCalc,
  IconGrid,
  IconLink,
  IconPanel,
  IconPlus,
  IconSliders,
  IconSpark,
  IconUsers,
} from '../components/chat/icons';
import { loadSidebarOpen, saveSidebarOpen } from '../state/chatStore';
import '../styles/chat.css';
import '../styles/chatpage.css';

// 시작 카드 — 문장 길이 칩 6개가 들쭉날쭉 쌓이던 것을 짧은 제목·한 줄 설명의 카드 넷으로(docs/ui-refresh 단계 4).
// need 가 있는 카드는 그 권한이 있을 때만 보인다 — 눌러도 막히는 것을 권하지 않는다. 앞에서부터 넷을 쓴다.
const STARTS: {
  icon: (p: { width: number; height: number }) => JSX.Element;
  title: string;
  sub: string;
  prompt: string;
  need?: string;
}[] = [
  {
    icon: IconGrid,
    title: '도구 둘러보기',
    sub: '이 포털에서 할 수 있는 일과 쓸 수 있는 도구',
    prompt: '이 포털에서 무엇을 할 수 있는지, 어떤 도구가 있는지 알려줘',
  },
  {
    icon: IconLink,
    title: '내 Claude 에 연결',
    sub: 'Claude Code·Desktop 을 HWAX 에 붙이는 방법',
    prompt: '이 포털 사용법을 알려줘 — 내 Claude에 연결하려면?',
  },
  {
    icon: IconUsers,
    title: '전문가 심의',
    sub: 'FPCB 동박 두께 — 여러 라운드로 토의해 결정',
    prompt: '/심의 FPCB 적층 동박을 두껍게 vs 얇게 — 전문가 다중 라운드 심의',
    need: 'feat:deliberation',
  },
  {
    icon: IconCalc,
    title: '공학 계산',
    sub: '복합재 적층의 ABD 행렬·중립축',
    prompt: '복합재 적층 구성의 ABD 행렬·중립축을 계산해줘 (공학해석 도구)',
  },
  {
    icon: IconBook,
    title: '문헌 정리',
    sub: '배터리 스웰링 관련 백서 요약',
    prompt: '배터리 스웰링 관련 백서 내용을 정리해줘',
  },
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
  const can = useCan();
  const { messages, activeId, setInput, newConversation } = useChat();
  const composerRef = useRef<ComposerHandle>(null);
  const threadRef = useRef<HTMLDivElement>(null); // 내보내기(HTML)가 캡처할 렌더 루트
  // 데스크톱은 저장된 선호를 따르고, 좁은 화면은 오버레이라 기본 닫힘.
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow() && loadSidebarOpen());
  // 시작 전 전문가·도구 선택 패널(랜딩) — 열면 예시 칩 자리에 선택 카드가 뜬다.
  const [picker, setPicker] = useState(false);

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
              <Composer
                ref={composerRef}
                autoFocus
                showHint
                showExpert
                placeholder={
                  can('feat:deliberation')
                    ? '무엇이든 물어보세요 — /심의 로 시작하면 전문가 심의'
                    : undefined
                }
              />
              {/* 시작 전 구성 — 전문가(페르소나)·도구를 직접 고르고 대화 시작(심의 선정과 같은 구조). */}
              {picker ? (
                <StartPicker onClose={() => setPicker(false)} />
              ) : (
                <>
                  <div className="cx-starts">
                    {STARTS.filter((c) => !c.need || can(c.need))
                      .slice(0, 4)
                      .map((c) => (
                        <button
                          type="button"
                          key={c.title}
                          className="cx-start"
                          onClick={() => fillPrompt(c.prompt)}
                        >
                          <span className="cx-start-ic" aria-hidden="true">
                            <c.icon width={17} height={17} />
                          </span>
                          <span className="cx-start-text">
                            <b>{c.title}</b>
                            <span>{c.sub}</span>
                          </span>
                        </button>
                      ))}
                  </div>
                  <button type="button" className="cx-pick" onClick={() => setPicker(true)}>
                    <IconSliders width={15} height={15} />
                    {can('feat:expert-chat')
                      ? '전문가·도구를 직접 고르고 시작'
                      : '도구를 직접 고르고 시작'}
                  </button>
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="cx-thread" key={activeId ?? 'thread'}>
            <ExportBar threadRef={threadRef} />
            <div ref={threadRef} className="cx-thread-body">
              <MessageList messages={messages} />
            </div>
            <div className="cx-composer-dock">
              <Composer
                ref={composerRef}
                autoFocus
                showHint
                showExpert
                placeholder="답장을 입력하세요…"
              />
            </div>
          </div>
        )}
      </section>
      {!empty && <ActivityPanel messages={messages} />}
    </div>
  );
}
