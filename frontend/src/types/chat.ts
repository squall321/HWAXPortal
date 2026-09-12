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
  /** 심의 핸드오프용 날것(≈1200자) — 화면에는 안 쓴다. 표시용(220자)보다 길 때만 온다. */
  result_full?: string;
}

// ── 심의(deliberation) 구조화 스트림 — 라이브 회의·스테퍼·수렴 UI(DelibView)의 데이터 ──
export interface DelibTurn {
  /** 이번 회차 안의 라운드(1..N) — 진행률·라운드 묶음·수렴 판정은 이것으로 한다. */
  round: number;
  /** 이어하기 회차를 이어 센 번호(엔진 display_round). 라벨·다음 이어하기의 rounds_so_far 는 이것. */
  displayRound?: number;
  persona: string;
  say: string;
  position?: string; // 입장 한 줄 요약(R1/R3)
  stance?: string; // R3: 동의|조건부 동의|반대
  /** R3 양보 불가 제약 원문 — 이어하기에서 승계해 이전 결정이 되돌아가지 않게 한다(표시용 say 와 별개). */
  nonNegotiable?: string;
  /** 이 발언이 **누구의 어떤 말을** 반박했는지. 산문(say)에도 녹아 있지만, 그것만으로는
   *  관계를 그릴 수 없다 — 지식 그래프와 이어하기 승계가 쓰는 구조 부본이다. */
  rebut?: { target: string; quote: string; counter: string; basis: string }[];
  ts: number;
}
export interface DelibTally {
  agree: number;
  conditional: number;
  oppose: number;
  /** 스탠스를 표명하지 않았거나 아예 응답하지 못한 좌석. 침묵을 동의로 세지 않기 위한 칸이다.
   *  과거 저장분에는 없으므로 optional. */
  abstain?: number;
  /** 마지막 라운드에 실제로 응답한 좌석 수. total 은 **착석 수**라 둘이 다를 수 있다. */
  responded?: number;
  /** 착석 좌석 수(응답자 수가 아니다) — 예전엔 응답자 수였고 그래서 좌석이 유실되면
   *  '만장일치 3/3' 같은 거짓 표시가 나갔다. */
  total: number;
}
export interface DelibData {
  stage?: string; // recall|discover|r1..rN|decide|report
  stages?: string[]; // 지나온 단계(순서)
  roundN?: number; // 라운드당 패널 수(진행률 분모)
  totalRounds?: number; // 총 라운드 수(가변, 기본 3) — 스테퍼/회의록 동적 렌더용
  /** origin — 좌석 성격. primary(주 도메인) · counter(반대 도메인, 커버리지 게이트가 앉힌 좌석)
   *  · adversary(신규 Job 지정 반대석 — red-team/반증/반대) · carry(이어하기 유임)
   *  · new(이어하기 재심사로 합류). 없으면 primary 로 본다. */
  personas?: { key: string; role?: string; origin?: 'primary' | 'counter' | 'adversary' | 'carry' | 'new' }[];
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

// ── 띵킹 모드 — 답할 수 있는 전문가만 각자 답한다(회의 아님) ──────────────────
// 심의(DelibData)와 형제이지만 구조가 다르다. 라운드도 표결도 결정문도 없고, 좌석마다
// '답했나 기권했나' 와 '기권했으면 어디로 넘겼나' 가 단위다.
export interface ThinkSeat {
  key: string;
  name?: string;
  domain?: string;
  /** recommend_agents 의 합성 점수. 코사인이 아니라 순위용이다(절대값 비교 금물). */
  score?: number;
  /** 질의 토큰이 좌석 프로필에 포함된 어휘 비율(0~1). 벡터와 독립인 신호다. */
  desc_match?: number;
  sections?: number;
  records?: number;
  /** 예심 — 그 좌석의 실제 바인딩 문서에서 나온 근거 수. */
  hits?: number;
  screened?: boolean;
  screenReason?: string;
  /** 본심 — answer(답함) · pass(기권) · error(응답 실패, 기권 아님). */
  verdict?: 'answer' | 'pass' | 'error';
  /** verdict='error' 의 사유(타임초과 · 형식 실패 · 예외 원문). 다음 행동이 갈린다 —
   *  타임초과는 재시도, 형식 실패는 질문을 바꾸는 쪽이다. 없으면 서버가 안 보낸 것(구 버전). */
  error?: string;
  scope?: string;
  answer?: string;
  basis?: string[];
  /** 기권 좌석이 지목한 분야(위임 사슬의 입력). */
  refer?: string[];
  /** 소집된 홉. 0=최초 소집, 1 이상=위임으로 합류. */
  hop?: number;
}
export interface ThinkData {
  seats?: ThinkSeat[];
  handoffs?: { phrases: string[]; seats: string[] }[];
  summary?: {
    answered: number;
    passed: number;
    screened_out: number;
    errored: number;
    /** 답변 상한에 걸려 **묻지 않은** 좌석 수. 0이 아니면 화면이 그렇게 말해야 한다. */
    capped?: number;
    hops: number;
    no_answer: boolean;
  };
}
// SSE `think` 이벤트 payload — kind 별로 위 필드의 부분집합이 실려온다.
export interface ThinkEvent {
  kind: 'roster' | 'screen' | 'verdict' | 'answer' | 'handoff' | 'summary';
  [k: string]: unknown;
}

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
  /** 영역(하는 일) 키·이름 — 게이트웨이 tool_areas.json 판정. ''/없음 = 미분류. */
  area?: string;
  area_label?: string;
}
/** MCP 앱 한 건 — 앱 단위 선택(pinnedApps)의 단위. tool_count 는 이 사용자에게 보이는 수. */
export interface ToolApp {
  app: string;
  label: string;
  desc?: string;
  tool_count: number;
}
/** 도구 영역 한 건 — 앱이 아니라 '하는 일'로 묶은 1단 필터. area='' 는 미분류. */
export interface ToolArea {
  area: string;
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
  /** 영역 목록 — 없으면(구 서버) all[].area 로 재구성, 그마저 없으면 영역 칩을 안 그린다. */
  areas?: ToolArea[];
}

// 전문가 카탈로그(SSE `agents` 이벤트) — '/전문가' 검색 시 서버가 추천+전체 풀을 내려준다.
// 도구(ToolCatalog)와 대칭인 채널인데 오래 소비처가 없어 조용히 버려지고 있었다.
export interface AgentCatalog {
  query?: string;
  recommended: { key: string; name: string; desc?: string }[];
  pool: { key: string; name: string }[];
  /** [도메인 코드, 인원] — 서버가 인원 많은 순으로 정렬해 준다. */
  domains?: [string, number][];
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
  // 전문가 카탈로그(SSE agents 이벤트) — 전문가 선택 카드용. toolCatalog 와 같이 영속하지
  // 않는다(풀이 700명 넘어 대화마다 쌓으면 localStorage 쿼터를 먹는다).
  agentCatalog?: AgentCatalog;
  /** 이 답이 **누구의 것**인지 — 지정 전문가(페르소나)로 보낸 발화의 답에 전송 시점에 찍는다.
   *  대화 상태(pinnedAgent)만 보면 나중에 전문가를 바꿨을 때 과거 답까지 그 사람 것으로
   *  보이고, 새로고침하면 아예 사라진다. name 은 표시용(서버 계약은 여전히 key=agent_type). */
  persona?: { key: string; name?: string };
  // 띵킹 구조화 데이터 — 좌석별 답변·기권 렌더(ThinkView)용. 영속됨.
  think?: ThinkData;
  error?: string;
  // 자격증명 강등 등 치명적이지 않은 경고 — 심의가 서비스 계정으로 근거를 모은 경우.
  // error 와 달리 응답을 막지 않고 옆에 지속 표시한다(무음 강등 가시화).
  warn?: string;
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
  // 그 전문가의 사람 이름 — 화면 표시용이다. 없으면 키를 그대로 보여 준다(구 저장분).
  pinnedAgentName?: string;
  /** 보조 전문가 — 주 전문가 뒤에 서서 판단 기준·도구만 빌려준다(답은 한 목소리다). */
  pinnedHelpers?: { key: string; name?: string }[];
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
  result_full?: string;
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
