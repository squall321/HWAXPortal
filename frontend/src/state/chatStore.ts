// 대화 이력 localStorage 영속 계층 — 저장 스키마(role/content/ts)와 런타임 Message를 상호 변환
import type { Conversation, Message, Role } from '../types/chat';

// prefix 로 이력 네임스페이스를 가른다 — 일반 챗 'hwax.chat', 심의 페이지 'hwax.delib'.
const DEFAULT_PREFIX = 'hwax.chat';
const SIDEBAR_KEY = 'hwax.chat.sidebar'; // 사이드바 접힘은 페이지 공통 UI 선호라 공유
const MAX_CONVERSATIONS = 100;

// Persisted shape (plan: {role, content, ts}). Transient fields (streaming/status)
// are intentionally dropped; `error` is kept so failed turns stay explainable.
interface StoredMessage {
  role: Role;
  content: string;
  ts: number;
  error?: string;
}
interface StoredConversation {
  id: string;
  title: string;
  messages: StoredMessage[];
  createdAt: number;
  updatedAt: number;
}

let seq = 0;
/** 충돌 확률이 무시 가능한 로컬 전용 id (crypto.randomUUID는 비보안 컨텍스트에서 없음). */
export function newId(): string {
  return `${Date.now().toString(36)}-${(++seq).toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function loadConversations(prefix: string = DEFAULT_PREFIX): Conversation[] {
  try {
    const raw = localStorage.getItem(`${prefix}.conversations`);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const convs: Conversation[] = [];
    for (const c of parsed as StoredConversation[]) {
      if (!c || typeof c.id !== 'string' || !Array.isArray(c.messages)) continue;
      const messages: Message[] = [];
      for (const m of c.messages) {
        if (!m || (m.role !== 'user' && m.role !== 'assistant')) continue;
        messages.push({
          id: newId(),
          role: m.role,
          text: typeof m.content === 'string' ? m.content : '',
          ts: typeof m.ts === 'number' ? m.ts : undefined,
          ...(m.error ? { error: m.error } : {}),
        });
      }
      convs.push({
        id: c.id,
        title: typeof c.title === 'string' && c.title ? c.title : '새 대화',
        messages,
        createdAt: typeof c.createdAt === 'number' ? c.createdAt : Date.now(),
        updatedAt: typeof c.updatedAt === 'number' ? c.updatedAt : Date.now(),
      });
    }
    return convs;
  } catch {
    return []; // 손상된 저장분은 조용히 버리고 빈 상태로 시작
  }
}

export function saveConversations(convs: Conversation[], prefix: string = DEFAULT_PREFIX): void {
  try {
    const stored: StoredConversation[] = convs.slice(0, MAX_CONVERSATIONS).map((c) => ({
      id: c.id,
      title: c.title,
      createdAt: c.createdAt,
      updatedAt: c.updatedAt,
      messages: c.messages
        // 스트리밍 도중 닫힌 빈 어시스턴트 placeholder는 저장하지 않는다.
        .filter((m) => m.text || m.error || m.role === 'user')
        .map((m) => ({
          role: m.role,
          content: m.text,
          ts: m.ts ?? c.updatedAt,
          ...(m.error ? { error: m.error } : {}),
        })),
    }));
    localStorage.setItem(`${prefix}.conversations`, JSON.stringify(stored));
  } catch {
    // 쿼터 초과 등 — 채팅 자체는 계속 동작해야 하므로 무시
  }
}

export function loadActiveId(prefix: string = DEFAULT_PREFIX): string | null {
  try {
    return localStorage.getItem(`${prefix}.activeId`);
  } catch {
    return null;
  }
}

export function saveActiveId(id: string | null, prefix: string = DEFAULT_PREFIX): void {
  try {
    if (id) localStorage.setItem(`${prefix}.activeId`, id);
    else localStorage.removeItem(`${prefix}.activeId`);
  } catch {
    /* noop */
  }
}

export function loadSidebarOpen(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_KEY) !== '0';
  } catch {
    return true;
  }
}

export function saveSidebarOpen(open: boolean): void {
  try {
    localStorage.setItem(SIDEBAR_KEY, open ? '1' : '0');
  } catch {
    /* noop */
  }
}
