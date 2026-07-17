// 심의 전용 페이지 — 화두를 던지면 전문가 다중 라운드 심의(불량 화두면 SignalForge 환기 선행), 이력은 챗과 분리
import { useCallback, useRef, useState } from 'react';
import { useChat } from '../state/ChatContext';
import { ChatSidebar } from '../components/chat/ChatSidebar';
import { Composer, type ComposerHandle } from '../components/chat/Composer';
import { MessageList } from '../components/chat/MessageList';
import { IconPanel, IconPlus, IconSpark } from '../components/chat/icons';
import { loadSidebarOpen, saveSidebarOpen } from '../state/chatStore';
import '../styles/chat.css';
import '../styles/chatpage.css';

// 화두 예시 — 불량 계열(SignalForge 환기 경로)과 일반 설계 화두를 섞어 노출.
const EXAMPLE_TOPICS = [
  '배터리 스웰링 불량이 보고되고 있어 — 셀 적층 설계에서 어떤 대응이 우선인가',
  'FPCB 적층 동박을 두껍게 vs 얇게 — 강성·폴딩·낙하 관점 종합',
  '폴더블 힌지 구간 크랙 불량 — 재료 교체 vs 구조 보강 어느 쪽이 맞나',
  '리플로우 warpage 산포를 줄이려면 대칭 적층과 동박 밸런스 중 무엇이 먼저인가',
];

const FLOW_HINT =
  '화두에 불량·품질 얘기가 있으면 SignalForge 최근 이슈를 먼저 환기하고, 관련 전문가들이 여러 라운드로 심의해 Report Archive 보고서까지 남깁니다';

const isNarrow = () => window.matchMedia('(max-width: 900px)').matches;

export default function DeliberatePage() {
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

      <section className="cx-main" aria-label="심의">
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
              aria-label="새 심의"
              title="새 심의"
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
              <p className="cx-hero-kicker">다중 전문가 심의</p>
              <h1 className="cx-hero-title">어떤 화두를 심의할까요?</h1>
              <Composer ref={composerRef} autoFocus placeholder="화두를 입력하세요…" />
              <div className="cx-chips">
                {EXAMPLE_TOPICS.map((p) => (
                  <button type="button" key={p} className="cx-chip" onClick={() => fillPrompt(p)}>
                    {p}
                  </button>
                ))}
              </div>
              <p className="cx-hero-hint">{FLOW_HINT}</p>
              <p className="cx-hero-sub">
                의견을 하나 던지면 전문가 에이전트들이 토의로 답합니다. 기록은 이 페이지에만 남습니다.
              </p>
            </div>
          </div>
        ) : (
          <div className="cx-thread" key={activeId ?? 'thread'}>
            <MessageList messages={messages} />
            <div className="cx-composer-dock">
              <Composer ref={composerRef} autoFocus placeholder="추가 화두를 입력하세요…" />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
