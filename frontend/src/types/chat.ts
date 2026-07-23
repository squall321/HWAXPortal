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
  personas?: { key: string; role?: string }[];
  // 근거 카드 — 한 심의에 복수 출처가 올 수 있어 배열(SignalForge 환기 + 정량 근거 선주입).
  // 과거 저장분은 단일 객체일 수 있어 소비처는 배열/객체 양쪽을 허용한다.
  evidence?: { source: string; text: string; included: boolean }[];
  turns?: DelibTurn[];
  decision?: string;
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
}

// SSE `delib` 이벤트 payload — kind 별로 위 필드의 부분집합이 실려온다.
export interface DelibEvent {
  kind: 'stage' | 'evidence' | 'personas' | 'turn' | 'decision' | 'outcome';
  [k: string]: unknown;
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
