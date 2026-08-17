// 심의 전용 페이지 — 화두를 던지면 전문가 다중 라운드 심의(불량 화두면 SignalForge 환기 선행), 이력은 챗과 분리
import { useCallback, useRef, useState } from 'react';
import { useChat } from '../state/ChatContext';
import { ActivityPanel } from '../components/chat/ActivityPanel';
import { ChatSidebar } from '../components/chat/ChatSidebar';
import { Composer, type ComposerHandle } from '../components/chat/Composer';
import { DelibOptsPanel } from '../components/chat/DelibOptsPanel';
import { ExpertPicker, type Persona } from '../components/chat/ExpertPicker';
import { ExportBar } from '../components/chat/ExportBar';
import { MessageList } from '../components/chat/MessageList';
import { IconPanel, IconPlus, IconSpark } from '../components/chat/icons';
import { fetchDeliberateExperts, type ExpertsResponse } from '../api/chat.api';
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

// 심의 모드 — 일반은 "원인이 무엇인가"에서 끝나고, 시뮬레이션 심의는 거기서 한 걸음 더 가
// "그걸 어떤 계산으로 확인할 것인가"까지 낸다. 트리거가 달라 서버가 2단 파이프라인으로 분기한다.
const MODES = [
  {
    id: 'delib' as const,
    trigger: '/심의 ',
    label: '전문가 심의',
    kicker: '다중 전문가 심의',
    title: '어떤 화두를 심의할까요?',
    hint: FLOW_HINT,
  },
  {
    id: 'sim' as const,
    trigger: '/시뮬심의 ',
    label: '시뮬레이션 심의',
    kicker: '메커니즘 → 해석 설계',
    title: '어떤 현상을 계산으로 풀어볼까요?',
    hint: '먼저 도메인 전문가가 지배 물리를 좁히고, 그 결론 위에서 CAE 전문가가 어떤 해석을 어떤 도구로 할지 계획서를 만듭니다. 물리를 아는 전문가 일부가 2단에 남아 해석이 물리에서 떠나지 않게 감시합니다',
  },
  {
    id: 'test' as const,
    trigger: '/시험계획 ',
    label: '시험 계획',
    kicker: '무엇을 먼저 측정할까',
    title: '어떤 물성·성능을 시험으로 확보할까요?',
    hint: '계측·CAE·프로그램 전문가가 고정 착석해, 보유 실측을 재측정하지 않으면서 무엇을 어떤 규격·조건으로 몇 회 시험할지 9항목 계획서를 만듭니다. "하나만 먼저 한다면"과 "이 시험으로도 확보되지 않는 것"은 비워둘 수 없습니다',
  },
];
type ModeId = (typeof MODES)[number]['id'];

const SIM_SUGGESTIONS = [
  '적색 발광이 외곽부터 액자 모양으로 죽어 들어가는데 UV 를 쬐면 회복되고 다시 재발한다',
  '리플로우 후 warpage 산포가 커지는 원인을 계산으로 좁히고 싶다',
  '낙하 시 특정 모서리에서만 크랙이 나는데 어떤 해석으로 재현할 수 있나',
];

// 시험계획 예시 — '무엇을 먼저 측정할 것인가' 형태로. 물성 확보·수명·공정 산포 세 갈래.
const TEST_SUGGESTIONS = [
  '낙하·충격 해석용 물성 확보 — 무엇을 먼저 측정할 것인가',
  '접착·테이프 계면의 신뢰성 판정을 위해 어떤 시험을 설계해야 하나',
  '리플로우 warpage 산포의 지배 인자를 가리는 DOE 를 짜고 싶다',
];

const SUGGESTIONS_BY_MODE = {
  delib: EXAMPLE_TOPICS,
  sim: SIM_SUGGESTIONS,
  test: TEST_SUGGESTIONS,
} as const;

const isNarrow = () => window.matchMedia('(max-width: 900px)').matches;

// RA 저장 — '/보고서' 트리거로 에이전트 서버가 대화 이력을 코드로 blocks 화해 결정적으로 저장
// (LLM 재량에 맡기면 도구 인자를 텍스트로 에코하는 불안정성이 있어 서버 핸들러로 처리).
const RA_SAVE_PROMPT = '/보고서';

export default function DeliberatePage() {
  const { messages, activeId, setInput, newConversation, sendMessage, streaming } = useChat();
  const composerRef = useRef<ComposerHandle>(null);
  const threadRef = useRef<HTMLDivElement>(null); // 내보내기(HTML)가 캡처할 렌더 루트
  // 데스크톱은 저장된 선호를 따르고, 좁은 화면은 오버레이라 기본 닫힘.
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow() && loadSidebarOpen());
  // 심의 전 전문가 선정 단계 — 화두 제출 시 추천/풀을 받아 확인 패널을 띄운다(기본 자동, 확인 후 시작).
  const [picking, setPicking] = useState<{ topic: string; experts: ExpertsResponse | null } | null>(null);
  const [mode, setMode] = useState<ModeId>('delib');
  const modeDef = MODES.find((m) => m.id === mode) ?? MODES[0];

  // 화두 제출 → 전문가 미리보기 로드 후 선정 패널 표시. 실패해도 패널은 열려(자동/수동 선택 가능).
  const startPicking = useCallback((topic: string) => {
    setPicking({ topic, experts: null });
    setInput('');
    void fetchDeliberateExperts(topic).then((experts) =>
      setPicking((cur) => (cur && cur.topic === topic ? { ...cur, experts } : cur)),
    );
  }, [setInput]);

  // 선정 확정 → 고른 전문가(+선택 도구·앱)로 심의 시작. personas 는 발굴 생략, tools 는 심의가
  // 실제 호출해 정량 근거로 주입한다(미선택이면 자동 파이프라인만 — 종전과 동일).
  // apps 는 호출 대상이 아니라 라운드 중 전문가 자유 조회의 범위 제한이다.
  const confirmExperts = useCallback((personas: Persona[], tools: string[], apps: string[]) => {
    const topic = picking?.topic;
    setPicking(null);
    if (!topic) return;
    sendMessage(modeDef.trigger + topic, {
      personas: personas.map((p) => ({ key: p.key, role: p.role })),
      ...(tools.length > 0 ? { tools } : {}),
      ...(apps.length > 0 ? { apps } : {}),
    });
  }, [picking, sendMessage, modeDef]);

  const cancelPicking = useCallback(() => {
    const topic = picking?.topic ?? '';
    setPicking(null);
    if (topic) {
      setInput(topic);
      composerRef.current?.focus();
    }
  }, [picking, setInput]);

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
          <div className={`cx-hero${picking ? ' cx-hero--picking' : ''}`} key={activeId ?? 'new'}>
            {picking ? (
              <div className="cx-hero-inner">
                <ExpertPicker
                  topic={picking.topic}
                  loading={picking.experts === null}
                  experts={picking.experts}
                  onConfirm={confirmExperts}
                  onCancel={cancelPicking}
                />
              </div>
            ) : (
              <div className="cx-hero-inner">
                <div className="cx-hero-mark" aria-hidden="true">
                  <IconSpark width={30} height={30} />
                </div>
                <p className="cx-hero-kicker">{modeDef.kicker}</p>
                <h1 className="cx-hero-title">{modeDef.title}</h1>
                <div className="cx-modes" role="tablist" aria-label="심의 모드">
                  {MODES.map((m) => (
                    <button
                      type="button"
                      key={m.id}
                      role="tab"
                      aria-selected={mode === m.id}
                      className={`cx-mode${mode === m.id ? ' is-on' : ''}`}
                      onClick={() => setMode(m.id)}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                <Composer
                  ref={composerRef}
                  autoFocus
                  placeholder={
                    mode === 'sim' ? '현상을 입력하세요…'
                    : mode === 'test' ? '확보하려는 물성·성능을 입력하세요…'
                    : '화두를 입력하세요…'
                  }
                  onSubmitText={startPicking}
                />
                <DelibOptsPanel />
                <div className="cx-chips">
                  {SUGGESTIONS_BY_MODE[mode].map((p) => (
                    <button type="button" key={p} className="cx-chip" onClick={() => fillPrompt(p)}>
                      {p}
                    </button>
                  ))}
                </div>
                <p className="cx-hero-hint">{modeDef.hint}</p>
                <p className="cx-hero-sub">
                  의견을 하나 던지면 전문가 에이전트들이 토의로 답합니다. 기록은 서버에 남아 Claude(MCP) 심의와 한곳에 모입니다.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="cx-thread" key={activeId ?? 'thread'}>
            <ExportBar threadRef={threadRef} />
            <div ref={threadRef} className="cx-thread-body">
              <MessageList messages={messages} />
            </div>
            <div className="cx-composer-dock">
              {!streaming && messages.some((m) => m.role === 'assistant' && (m.text || m.delib)) && (
                <div className="cx-delib-actions">
                  <button
                    type="button"
                    className="cx-chip"
                    onClick={() => sendMessage(RA_SAVE_PROMPT)}
                    title="이 대화의 심의 내용·결론을 Report Archive 보고서로 저장"
                  >
                    📄 RA 보고서로 저장
                  </button>
                </div>
              )}
              <DelibOptsPanel />
              <Composer
                ref={composerRef}
                autoFocus
                placeholder="이어서 질문하거나 의견을 보태세요… (GLM이 심의 로그를 이어받아 답합니다)"
              />
            </div>
          </div>
        )}
      </section>
      {!empty && <ActivityPanel messages={messages} />}
    </div>
  );
}
