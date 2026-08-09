// Chat data contract — mirrors the backend SSE / agent-response contract (plan §5).

export type Role = 'user' | 'assistant';

// Agent result object — the only payload the renderers parse (plan §5).
// graph/cad are Phase 4; Phase 2 only renders text.
export type ResultBlock =
  | { type: 'text'; content: string }
  | { type: 'graph'; content: string; metadata?: { title?: string; source?: string } }
  | { type: 'cad'; content: string; metadata?: { part_id?: string; format?: string } };

// 활동 패널 항목 — status 이벤트 누적분(어떤 도구·전문가가 쓰였는지). 대화 옆 정보 표시용.
export interface ActivityItem {
  ts: number;
  step: string;
  tool?: string | null;
  personas?: string[];
  tools_used?: string[];
  // 드릴다운 — 도구 호출 입력/결과 요약(서버에서 절단되어 옴).
  detail?: string;
  result_preview?: string;
}

// ── 심의(deliberation) 구조화 스트림 — 라이브 회의·스테퍼·수렴 UI(DelibView)의 데이터 ──
export interface DelibTurn {
  round: number;
  persona: string;
  say: string;
  position?: string; // 입장 한 줄 요약(R1/R3)
  stance?: string; // R3: 동의|조건부 동의|반대
  /** R3 양보 불가 제약 원문 — 이어하기에서 승계해 이전 결정이 되돌아가지 않게 한다(표시용 say 와 별개). */
  nonNegotiable?: string;
  ts: number;
}
export interface DelibTally {
  agree: number;
  conditional: number;
  oppose: number;
  total: number;
}
export interface DelibData {
  stage?: string; // recall|discover|r1..rN|decide|report
  stages?: string[]; // 지나온 단계(순서)
  roundN?: number; // 라운드당 패널 수(진행률 분모)
  totalRounds?: number; // 총 라운드 수(가변, 기본 3) — 스테퍼/회의록 동적 렌더용
  /** origin — 좌석 성격. primary(주 도메인) · counter(반대 도메인, 커버리지 게이트가 앉힌 좌석)
   *  · carry(이어하기 유임) · new(이어하기 재심사로 합류). 없으면 primary 로 본다. */
  personas?: { key: string; role?: string; origin?: 'primary' | 'counter' | 'carry' | 'new' }[];
  // 근거 카드 — 한 심의에 복수 출처가 올 수 있어 배열(SignalForge 환기 + 정량 근거 선주입).
  // 과거 저장분은 단일 객체일 수 있어 소비처는 배열/객체 양쪽을 허용한다.
  evidence?: { source: string; text: string; included: boolean }[];
  turns?: DelibTurn[];
  decision?: string;
  /** 쉬운 설명 — 비전문가용 정리(정식 심의 단계 'explain' 산출물). */
  plain?: string;
  outcome?: {
    report_id?: number | null;
    title?: string;
    tally?: DelibTally;
    unanimous?: boolean;
  };
}
// 심의 손잡이(웹 토글) — 켠 것만 서버로 전송, 나머지는 agent-server env 기본값. GLM 리뷰 §5.
// 불리언=0/1 플래그, chair_bestof=의장 후보 수(1=끔), timeout_s=호출당 타임아웃(초·미지정=기본).
export interface DelibOpts {
  evidence_prepass?: boolean;
  rebut_quote?: boolean;
  prose_first?: boolean;
  cross_exam?: boolean;
  anchor?: boolean;
  chair_cite?: boolean;
  chair_bestof?: number;
  rounds?: number;
  timeout_s?: number;
  /** 1이면 초기 라운드까지만 돌고 멈춘다(인간 체크포인트). 결정문 대신 전원 초기 입장이
   *  내려오고, 이어하기 폼으로 의견을 보태면 좌석 재심사가 그 방향의 도메인을 불러온다. */
  stop_after_round?: number;
  // ── 이어하기(사람 개입 스티어링) 필드 — 손잡이가 아니라 승계 데이터다 ──
  /** 이번 회차에서 패널이 반드시 정면으로 다뤄야 할 사람의 의견. 매 라운드 프롬프트에 주입된다. */
  human_note?: string;
  /** 이전 심의 요약(보통 직전 결정문). 이어하기 1라운드의 출발점. */
  continue_summary?: string;
  /** 이전 좌석. 서버가 유임으로 잡고, 실효 질문으로 재심사해 신규 좌석을 더한다. */
  personas?: { key: string; role?: string }[];
  /** 이전 심의의 양보 불가 조항. 요약에 섞지 않고 따로 넘겨야 승계가 보장된다 —
   *  빠지면 이전 결정이 조용히 되돌아간다. */
  non_negotiables?: string[];
  /** 이번 발화에서 우선 사용할 도구 이름. 심의가 실제로 호출해 정량 근거로 주입한다. */
  tools?: string[];
  /** 라운드 중 전문가 자유 조회를 이 앱들로 좁힌다. tools 와 달리 전량 호출하지 않는다. */
  apps?: string[];
  /** 인터넷 소스 토글. 켠 소스의 도구만 바인딩된다 — 끄면 모델의 도구 목록에 아예 없다. */
  search_sources?: SearchSource[];
}

/** 인터넷 소스. 사내 자산은 나가지 않으므로 토글 대상이 아니다. */
export type SearchSource = 'scholar' | 'web';

// SSE `delib` 이벤트 payload — kind 별로 위 필드의 부분집합이 실려온다.
export interface DelibEvent {
  kind: 'stage' | 'evidence' | 'personas' | 'turn' | 'decision' | 'plain' | 'outcome';
  [k: string]: unknown;
}

// 도구 카탈로그(SSE `tools` 이벤트) — '/도구' 검색 시 서버가 추천+전체 목록을 내려준다.
// 사용자가 직접 선택한 도구는 대화의 pinnedTools 가 되어 이후 발화에서 우선 사용된다.
export interface ToolInfo {
  name: string;
  desc: string;
  score?: number;
  /** 소유 MCP 앱 키·이름 — 앱별 계층 선택용(게이트웨이 /tools-map 유래). */
  group?: string;
  group_label?: string;
}
/** MCP 앱 한 건 — 앱 단위 선택(pinnedApps)의 단위. tool_count 는 이 사용자에게 보이는 수. */
export interface ToolApp {
  app: string;
  label: string;
  desc?: string;
  tool_count: number;
}
export interface ToolCatalog {
  query?: string;
  recommended: ToolInfo[];
  all: ToolInfo[];
  /** 앱 목록 — 없으면(구 서버) all[].group 으로 프론트가 재구성한다. */
  apps?: ToolApp[];
}

export interface Message {
  id: string;
  role: Role;
  // For assistant messages this fills incrementally from `token` deltas, then
  // settles to the final `result` block. User messages are plain text.
  text: string;
  // Unix ms — set when the message is created; survives persistence round-trips.
  ts?: number;
  result?: ResultBlock;
  // Transient status line shown while the agent works (from `status` events).
  status?: string;
  // status 이벤트 누적 — 활동 패널(도구·전문가·진행)용. 영속됨.
  activity?: ActivityItem[];
  // 심의 구조화 데이터 — 라이브 회의/스테퍼/수렴 렌더(DelibView)용. 영속됨.
  delib?: DelibData;
  // 도구 카탈로그(SSE tools 이벤트) — 도구 선택 카드(ToolCatalogBlock) 렌더용. 영속됨.
  toolCatalog?: ToolCatalog;
  error?: string;
  streaming?: boolean;
}

// 대화 한 건 — localStorage('hwax.chat.*') 영속 단위 (chatStore.ts가 직렬화 담당).
export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  // 서버 대화 저장소 정본 id — 있으면 /agent/chat 이 이 대화에 user+assistant 를 서버 저장.
  // 서버에서 로드된 대화(MCP 심의 포함)는 id === serverId. 웹 생성분은 전송 시 발급받아 채움.
  serverId?: string;
  // 사용자 지정 우선 도구 — 도구 카탈로그에서 선택. 이 대화의 이후 발화에 pinned_tools 로 실린다.
  pinnedTools?: string[];
  // 사용자 지정 우선 앱 — 앱을 고르면 그 앱의 도구 전체가 우선 사용된다(서버가 펼침).
  pinnedApps?: string[];
  // 인터넷 소스 토글 — undefined 면 종전 동작, 배열이면 그 소스만 바인딩된다(빈 배열=전부 끔).
  searchSources?: SearchSource[];
  // 사용자 지정 전문가(agent_type) — '전문가와 대화' 모드. 이후 발화에 pinned_agent 로 실린다.
  pinnedAgent?: string;
}

// SSE event payloads (plan §5).
export interface StatusEvent {
  step: string;
  tool: string | null;
  // 심의 경로가 얹는 구조화 정보 — 활동 패널용(없으면 무시).
  personas?: string[];
  tools_used?: string[];
  detail?: string;
  result_preview?: string;
}
export interface TokenEvent {
  delta: string;
}
export interface ErrorEvent {
  code: string;
  message: string;
}

export interface ChatState {
  open: boolean;
  messages: Message[];
  input: string;
  streaming: boolean;
}
