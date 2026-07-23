// 대화 이력 localStorage 영속 계층 — 저장 스키마(role/content/ts)와 런타임 Message를 상호 변환
import type { ActivityItem, Conversation, DelibData, DelibOpts, Message, Role } from '../types/chat';

// prefix 로 이력 네임스페이스를 가른다 — 일반 챗 'hwax.chat', 심의 페이지 'hwax.delib'.
const DEFAULT_PREFIX = 'hwax.chat';
const SIDEBAR_KEY = 'hwax.chat.sidebar'; // 사이드바 접힘은 페이지 공통 UI 선호라 공유
const MAX_CONVERSATIONS = 100;

// Persisted shape (plan: {role, content, ts}). Transient fields (streaming/status)
// are intentionally dropped; `error` is kept so failed turns stay explainable.
// `activity`(도구·전문가 활동 로그)는 활동 패널이 과거 대화에서도 보이도록 영속한다.
interface StoredMessage {
  role: Role;
  content: string;
  ts: number;
  error?: string;
  activity?: ActivityItem[];
  delib?: DelibData;
}
interface StoredConversation {
  id: string;
  title: string;
  messages: StoredMessage[];
  createdAt: number;
  updatedAt: number;
  serverId?: string; // 서버 정본 id — 캐시 재로드 후에도 서버 병합·이어쓰기가 이어지게 영속
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
          ...(Array.isArray(m.activity) ? { activity: m.activity } : {}),
          ...(m.delib && typeof m.delib === 'object' ? { delib: m.delib } : {}),
        });
      }
      convs.push({
        id: c.id,
        title: typeof c.title === 'string' && c.title ? c.title : '새 대화',
        messages,
        createdAt: typeof c.createdAt === 'number' ? c.createdAt : Date.now(),
        updatedAt: typeof c.updatedAt === 'number' ? c.updatedAt : Date.now(),
        ...(typeof c.serverId === 'string' ? { serverId: c.serverId } : {}),
      });
    }
    return convs;
  } catch {
    return []; // 손상된 저장분은 조용히 버리고 빈 상태로 시작
  }
}

/** 심의 데이터 저장 트림 — turns/evidence 캡으로 localStorage 누적 증가를 통제한다. */
function trimDelib(d: DelibData): DelibData {
  // evidence 는 배열(과거 저장분은 단일 객체) — 최근 4개, 항목당 2000자 캡.
  const evList = Array.isArray(d.evidence) ? d.evidence : d.evidence ? [d.evidence] : [];
  return {
    ...d,
    ...(d.turns ? { turns: d.turns.slice(-45) } : {}),
    ...(evList.length
      ? { evidence: evList.slice(-4).map((e) => ({ ...e, text: e.text.slice(0, 2000) })) }
      : {}),
  };
}

export function saveConversations(convs: Conversation[], prefix: string = DEFAULT_PREFIX): void {
  try {
    const stored: StoredConversation[] = convs.slice(0, MAX_CONVERSATIONS).map((c) => ({
      id: c.id,
      title: c.title,
      createdAt: c.createdAt,
      updatedAt: c.updatedAt,
      ...(c.serverId ? { serverId: c.serverId } : {}),
      messages: c.messages
        // 스트리밍 도중 닫힌 빈 어시스턴트 placeholder는 저장하지 않는다.
        // 심의 메시지는 decision 도착 전까지 text가 비므로 delib 존재로도 보존한다(F5 소실 방지).
        .filter((m) => m.text || m.error || m.delib || m.role === 'user')
        .map((m) => ({
          role: m.role,
          content: m.text,
          ts: m.ts ?? c.updatedAt,
          ...(m.error ? { error: m.error } : {}),
          ...(m.activity && m.activity.length > 0 ? { activity: m.activity.slice(-60) } : {}),
          ...(m.delib ? { delib: trimDelib(m.delib) } : {}),
        })),
    }));
    try {
      localStorage.setItem(`${prefix}.conversations`, JSON.stringify(stored));
    } catch {
      // 쿼터 초과 — 오래된 대화 절반을 버리고 1회 재시도(무음 전면 저장 중단 방지)
      localStorage.setItem(
        `${prefix}.conversations`,
        JSON.stringify(stored.slice(0, Math.max(1, Math.floor(stored.length / 2)))),
      );
    }
  } catch {
    // 재시도까지 실패 — 채팅 자체는 계속 동작해야 하므로 무시
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

// 심의 손잡이(웹 토글) 영속 — prefix 네임스페이스로 심의 페이지 전용.
export function loadDelibOpts(prefix: string = DEFAULT_PREFIX): DelibOpts {
  try {
    const raw = localStorage.getItem(`${prefix}.delibOpts`);
    const o = raw ? JSON.parse(raw) : {};
    return o && typeof o === 'object' ? (o as DelibOpts) : {};
  } catch {
    return {};
  }
}

export function saveDelibOpts(opts: DelibOpts, prefix: string = DEFAULT_PREFIX): void {
  try {
    localStorage.setItem(`${prefix}.delibOpts`, JSON.stringify(opts));
  } catch {
    /* noop */
  }
}

// 손잡이 상태 → 서버 전송용(켠 것만). 나머지는 agent-server env 기본값 유지.
export function delibOptsToWire(o: DelibOpts): Record<string, number> {
  const w: Record<string, number> = {};
  for (const k of ['evidence_prepass', 'rebut_quote', 'prose_first', 'cross_exam', 'anchor', 'chair_cite'] as const) {
    if (o[k]) w[k] = 1;
  }
  if (o.chair_bestof && o.chair_bestof > 1) w.chair_bestof = Math.min(5, Math.max(1, o.chair_bestof));
  // 라운드 수 — 기본 3과 다를 때만 전송(같으면 서버 기본값). [2,8] 클램프(포털 DelibOpts 거부 방지).
  if (o.rounds != null && o.rounds !== 3) w.rounds = Math.min(8, Math.max(2, o.rounds));
  // 타임아웃은 여기서 [10,1800] 클램프 — 포털 DelibOpts 는 범위를 '거부'(422)하므로(agent-server 는
  // 클램프) HTML min/max 를 우회한 키보드 입력(5·5000 등)이 심의 전체를 422 로 죽이는 것 방지.
  if (o.timeout_s != null && o.timeout_s > 0) w.timeout_s = Math.min(1800, Math.max(10, o.timeout_s));
  return w;
}
