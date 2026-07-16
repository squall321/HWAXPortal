// Chat data contract — mirrors the backend SSE / agent-response contract (plan §5).

export type Role = 'user' | 'assistant';

// Agent result object — the only payload the renderers parse (plan §5).
// graph/cad are Phase 4; Phase 2 only renders text.
export type ResultBlock =
  | { type: 'text'; content: string }
  | { type: 'graph'; content: string; metadata?: { title?: string; source?: string } }
  | { type: 'cad'; content: string; metadata?: { part_id?: string; format?: string } };

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
