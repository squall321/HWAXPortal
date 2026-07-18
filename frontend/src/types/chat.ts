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
