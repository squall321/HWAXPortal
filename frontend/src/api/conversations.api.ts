// 서버 대화 저장소 REST 클라이언트 — Claude(MCP) 심의·웹 챗·GLM 이어가기가 공유하는 정본
import { apiFetch } from './client';
import type { Conversation, DelibTurn, Message } from '../types/chat';
import { newId } from '../state/chatStore';

export type ConvKind = 'chat' | 'deliberation';

export interface ServerConvMeta {
  id: string;
  title: string;
  kind: ConvKind;
  source: 'web' | 'mcp';
  created_at: number; // epoch 초(서버) — 로컬 ms 와 구분 주의
  updated_at: number;
}

interface ServerMessage {
  role: 'user' | 'assistant' | 'system' | 'persona';
  persona: string | null;
  round: number | null;
  content: string;
  meta: Record<string, unknown> | null;
  ts: number; // epoch 초
}

export async function listServerConversations(): Promise<ServerConvMeta[]> {
  const r = await apiFetch('/agent/conversations');
  if (!r.ok) throw new Error(`list failed (${r.status})`);
  const body = (await r.json()) as { conversations?: ServerConvMeta[] };
  return body.conversations ?? [];
}

export async function getServerConversation(
  id: string,
): Promise<(ServerConvMeta & { messages: ServerMessage[] }) | null> {
  const r = await apiFetch(`/agent/conversations/${encodeURIComponent(id)}`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`get failed (${r.status})`);
  return (await r.json()) as ServerConvMeta & { messages: ServerMessage[] };
}

/** 빈 서버 대화 생성 — 이후 /agent/chat 의 conversation_id 저장이 이 대화에 append 된다. */
export async function createServerConversation(title: string, kind: ConvKind): Promise<string> {
  const r = await apiFetch('/agent/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, kind, source: 'web' }),
  });
  if (!r.ok) throw new Error(`create failed (${r.status})`);
  return ((await r.json()) as { id: string }).id;
}

export async function deleteServerConversation(id: string): Promise<void> {
  await apiFetch(`/agent/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export async function renameServerConversation(id: string, title: string): Promise<void> {
  await apiFetch(`/agent/conversations/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
}

/** 서버 메시지 → 런타임 Message[]. persona 발언 묶음은 다음 assistant 에 delib(turns/decision)로
 *  붙여 기존 DelibView 렌더를 그대로 재사용한다(MCP 심의가 웹 심의처럼 보이게). */
export function serverMessagesToLocal(server: ServerMessage[]): Message[] {
  const out: Message[] = [];
  let turns: DelibTurn[] = [];
  for (const m of server) {
    const ts = (m.ts ?? 0) * 1000;
    if (m.role === 'persona') {
      turns.push({
        round: m.round ?? 0,
        persona: m.persona ?? '',
        say: m.content,
        ts,
      });
      continue;
    }
    if (m.role === 'system') continue; // 화면 비표시(향후 필요 시 확장)
    if (m.role === 'assistant' && turns.length > 0) {
      out.push({
        id: newId(),
        role: 'assistant',
        text: m.content,
        ts,
        delib: { turns, decision: m.content },
      });
      turns = [];
    } else {
      out.push({ id: newId(), role: m.role, text: m.content, ts });
    }
  }
  if (turns.length > 0) {
    // 결정문 없이 끝난 심의(비정상 종료) — 발언만이라도 보이게 남긴다.
    out.push({ id: newId(), role: 'assistant', text: '', ts: Date.now(), delib: { turns } });
  }
  return out;
}

/** 서버 대화(메시지 포함) → 로컬 Conversation. id 는 서버 id 그대로(재로드 시 중복 병합 안정). */
export function serverConvToLocal(
  conv: ServerConvMeta & { messages: ServerMessage[] },
): Conversation {
  return {
    id: conv.id,
    serverId: conv.id,
    title: conv.title || '새 대화',
    messages: serverMessagesToLocal(conv.messages),
    createdAt: conv.created_at * 1000,
    updatedAt: conv.updated_at * 1000,
  };
}
