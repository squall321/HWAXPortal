// 서버 대화 저장소 REST 클라이언트 — Claude(MCP) 심의·웹 챗·GLM 이어가기가 공유하는 정본
import { apiFetch } from './client';
import type { ActivityItem, Conversation, DelibTurn, Message, RoutineState } from '../types/chat';
import { newId, panelsFromMeta } from '../state/chatStore';

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

/** 서버 대화에 메시지 하나를 덧붙인다(주인만) — 챗 화면이 스스로 남기는 것(보내기 알림, docs/chat-ppt PP-D3)에 쓴다. 챗 턴은 포털이
 *  /agent/chat 에서 적는다. 실패하면 던진다(부른 쪽이 화면 사본만 남긴다). */
export async function appendServerMessage(
  id: string,
  m: { role: 'assistant' | 'user'; content: string; meta?: Record<string, unknown> },
): Promise<void> {
  const r = await apiFetch(`/agent/conversations/${encodeURIComponent(id)}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(m),
  });
  if (!r.ok) throw new Error(`append failed (${r.status})`);
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

/** 답의 meta.routine(분석 루틴 턴, R3-design §3.3) → 화면의 실행 상태. 서버 사본은 포인터 {run_id, routine_id, title, state} 만 쥔다 —
 *  단계 · 보고서의 정본은 포털 원장이라 단계는 비워 두고 화면이 run_id 로 다시 읽는다. 실행 id 가 없으면 되살리지 않는다. */
function routineFromMeta(meta: Record<string, unknown> | null): RoutineState | undefined {
  const r = meta?.routine as Record<string, unknown> | null | undefined;
  if (!r || typeof r !== 'object' || typeof r.run_id !== 'string' || !r.run_id) return undefined;
  return {
    run_id: r.run_id,
    ...(typeof r.routine_id === 'string' ? { routine_id: r.routine_id } : {}),
    title: typeof r.title === 'string' ? r.title : '',
    state: typeof r.state === 'string' ? r.state : '',
    steps: [],
  };
}

/** 서버 메시지 → 런타임 Message[]. persona 발언 묶음은 다음 assistant 에 delib(turns/decision)로
 *  붙여 기존 DelibView 렌더를 그대로 재사용한다(MCP 심의가 웹 심의처럼 보이게). */
export function serverMessagesToLocal(server: ServerMessage[]): Message[] {
  const out: Message[] = [];
  let turns: DelibTurn[] = [];
  // 지정 전문가의 답이었는지 — 화면은 보낼 때 답에 persona 를 찍는데(docs/persona-chat D-3) 서버 사본의 답에는 그 칸이 없고, 사람 발화의
  // meta 에 고른 전문가(pinned_agent · pinned_agent_name)가 남는다. 그 발화의 첫 답에 되살린다 — 없으면 서버 사본으로 화면을 바꾸는 길
  // (사본이 더 새로운 새로고침 · 다른 기기 · 숨은 탭에서 돌아옴)에서 말풍선이 사라져 그 답이 일반 어시스턴트의 것으로 읽혔다.
  // 무엇이 답했는지로 거른다 — 보낸 요청의 Thinking 켜짐이 아니다(확인 카드의 답은 켜 두어도 고른 전문가가 답하고, '/띵킹' 은 꺼 두어도
  // 띵킹이 답한다). 포털 중계가 그 턴의 프레임으로 적은 answered_by('think' 띵킹 · 'delib' 심의 — 발언 없이 끝난 심의도) · 발언이 앞선 심의
  // 결정문 · 분석 루틴의 답에는 붙이지 않는다(라이브도 띵킹 · 심의 화면에는 말풍선을 그리지 않는다 — MessageList). 보내기 알림은 건너뛴다
  // (사람 발화의 답이 아니다). answered_by 를 적기 전의 포털이 남긴 띵킹의 답은 가를 수 없어 고른 전문가가 있었으면 말풍선이 붙는다(드물다).
  let pinned: Message['persona'];
  // 웹 심의의 실행 id — 포털 중계가 발언 · 답의 meta.delib_run 에 남긴다(triage A24). 답 없이 끊긴 심의도 이것으로 '멈춤' 이 그 심의를 짚는다.
  let runId = '';
  for (const m of server) {
    const ts = (m.ts ?? 0) * 1000;
    if (m.role === 'persona') {
      // meta 에 영속된 관계·입장을 되살린다 — 없으면 다른 기기에서 연 심의는 관계도가 비고
      // 이어하기가 양보 불가 조항을 승계하지 못한다(구 저장분은 meta 가 없어 그대로 비어 온다).
      const meta = (m.meta ?? {}) as Record<string, unknown>;
      if (typeof meta.delib_run === 'string' && meta.delib_run) runId = meta.delib_run;
      turns.push({
        round: m.round ?? 0,
        persona: m.persona ?? '',
        // 웹 심의의 서버 사본은 줄이지 않은 발언을 본문에, 회의 버블을 meta.say 에 둔다 — 화면은 라이브와 같이 버블을 그린다.
        // MCP 가 저장한 발언은 버블이 따로 없다(본문 그대로).
        say: typeof meta.say === 'string' ? meta.say : m.content,
        ...(typeof meta.say === 'string' ? { sayFull: m.content } : {}),
        ...(typeof meta.stance === 'string' ? { stance: meta.stance } : {}),
        ...(typeof meta.non_negotiable === 'string' ? { nonNegotiable: meta.non_negotiable } : {}),
        ...(Array.isArray(meta.rebut) && meta.rebut.length
          ? { rebut: meta.rebut as DelibTurn['rebut'] }
          : {}),
        ts,
      });
      continue;
    }
    if (m.role === 'system') continue; // 화면 비표시(향후 필요 시 확장)
    if (m.role === 'assistant') {
      // 그 발화에 올린 그림의 서버 주소 — 포털이 답의 meta(user_images)에 남긴다(사람 발화는 스트림 전에 저장돼 주소를 모른다).
      // 바로 앞 사람 발화에 붙인다 — 다른 기기에서 연 대화도 다음 턴 이력에 그림이 실린다(T5).
      const ui = (m.meta as { user_images?: unknown } | null)?.user_images;
      if (Array.isArray(ui) && ui.length) {
        for (let k = out.length - 1; k >= 0; k -= 1) {
          if (out[k].role !== 'user') continue;
          out[k] = { ...out[k], images: ui.filter((u): u is string => typeof u === 'string') };
          break;
        }
      }
    }
    if (m.role === 'user') {
      const meta = (m.meta ?? {}) as Record<string, unknown>;
      pinned = typeof meta.pinned_agent === 'string' && meta.pinned_agent
        ? { key: meta.pinned_agent, ...(typeof meta.pinned_agent_name === 'string' ? { name: meta.pinned_agent_name } : {}) }
        : undefined;
    }
    // 받기가 끊긴 뒤 멈춤 창구가 남긴 멈춤 답 — 그 실행의 발언 · 앞 단 결정문이 이미 앞 답으로 남아(다단 심의) 발언 없이 따로 왔다. 같은 실행의 앞
    // 심의 칸에 멈춤으로 붙인다 — 따로 그리면 멈춤 글이 일반 답 말풍선이 되고 그 심의는 끝난 결정문처럼 보였다(멈춘 화면에서는 그 칸에 적힌다).
    const lone = m.role === 'assistant' && turns.length === 0
      ? (m.meta as { delib_cancelled?: { message?: unknown; run_id?: unknown }; delib_run?: unknown } | null)
      : null;
    const prev = out[out.length - 1];
    if (lone?.delib_cancelled && prev?.delib?.runId && prev.delib.runId === (lone.delib_run ?? lone.delib_cancelled.run_id)) {
      out[out.length - 1] = { ...prev, delib: { ...prev.delib, cancelled: { message: String(lone.delib_cancelled.message ?? '') } } };
      continue;
    }
    let persona: Message['persona'];
    const am = m.role === 'assistant' ? ((m.meta ?? {}) as Record<string, unknown>) : null;
    if (am && am.upload !== true) {
      if (!am.answered_by && turns.length === 0 && !routineFromMeta(m.meta)) persona = pinned;
      pinned = undefined; // 그 발화의 첫 답에만
    }
    if (m.role === 'assistant' && turns.length > 0) {
      // 저장된 round 는 이어하기를 이어 센 번호다(웹·MCP 공통). 한 회차의 라운드는 offset+1 부터
      // 연속이므로 최소값으로 회차 안 번호를 되살린다 — 라운드 묶음·수렴 판정이 그걸 쓴다.
      const off = Math.min(...turns.map((t) => t.round || 1)) - 1;
      const local = turns.map((t) => ({ ...t, displayRound: t.round, round: (t.round || 1) - off }));
      // 근거 카드 — 좌석이 조회한 것(이어하기가 승계한다)과 엔진의 '줄였다·뺐다' 알림. 서버 사본에 없으면 다른 기기에서는 사라진다.
      const ev = (m.meta as { delib_evidence?: { source?: unknown; text?: unknown; included?: unknown; notice?: unknown }[] } | null)
        ?.delib_evidence;
      // 사람이 멈춘 심의 — 포털 중계나 멈춤 창구가 멈춤을 답으로 남겼다(meta.delib_cancelled, triage A24). 그 글은 결정문이 아니다.
      const cx = (m.meta as { delib_cancelled?: { message?: unknown } } | null)?.delib_cancelled;
      const stopNote = cx ? String(cx.message ?? '') : '';
      const dr = (m.meta as { delib_run?: unknown } | null)?.delib_run;
      const rid = typeof dr === 'string' && dr ? dr : runId;
      // 다단 심의(/시뮬심의)가 다음 단을 도는 중에 받기가 끊겼다 — 포털 중계가 meta.delib_next_stage 로 남긴다. 답의 글은 앞 단의 결정문이고
      // 심의는 서버에서 아직 돌 수 있다(라이브의 nextStage 와 같은 뜻 — 끝난 심의로 읽으면 '멈춤' 이 사라진다).
      const nx = (m.meta as { delib_next_stage?: unknown } | null)?.delib_next_stage === true;
      // 결정문 없이 받기가 끝난 심의 — 답의 글은 엔진이 먼저 흘린 앞머리(불량 환기 VOC 등)뿐이다(meta.delib_undecided — 포털 중계). 결정문으로
      // 읽으면 끝난 심의가 되어 서버에서 아직 도는 심의에 '멈춤' 이 사라진다(라이브 칸에서도 그 글은 결정문이 아니다)
      const undecided = (m.meta as { delib_undecided?: unknown } | null)?.delib_undecided === true;
      out.push({
        id: newId(),
        role: 'assistant',
        text: m.content,
        ts,
        delib: {
          turns: local,
          ...((cx && m.content === stopNote) || undecided ? {} : { decision: m.content }),
          ...(cx ? { cancelled: { message: stopNote } } : {}),
          ...(rid ? { runId: rid } : {}),
          ...(nx ? { nextStage: true } : {}),
          totalRounds: Math.max(...local.map((t) => t.round)),
          ...(Array.isArray(ev) && ev.length
            ? {
                evidence: ev.map((e) => ({
                  source: String(e.source ?? ''),
                  text: String(e.text ?? ''),
                  included: Boolean(e.included),
                  ...(e.notice ? { notice: true } : {}),
                })),
              }
            : {}),
        },
      });
      turns = [];
      runId = '';
    } else {
      // 서버 meta 에 영속된 도구 활동(status) 복원 — 리로드·크로스디바이스에서도 심의 핸드오프
      // 근거 추출(conversationEvidence)이 동작하게 한다.
      const act = (m.meta as { activity?: ActivityItem[] } | null)?.activity;
      const routine = m.role === 'assistant' ? routineFromMeta(m.meta) : undefined;
      // 패널 포인터(HA-20) — 서버 사본은 포인터만 쥔다. 다른 기기 · 새로고침에서는 '다시 열기' 카드로 그린다(입력 · 결과 없이)
      const panels = m.role === 'assistant' ? panelsFromMeta((m.meta as { panels?: unknown } | null)?.panels) : undefined;
      out.push({
        id: newId(),
        role: m.role,
        text: m.content,
        ts,
        ...(persona ? { persona } : {}),
        ...(Array.isArray(act) ? { activity: act } : {}),
        ...(routine ? { routine } : {}),
        ...(panels ? { panels } : {}),
      });
    }
  }
  if (turns.length > 0) {
    // 결정문 없이 끝난 심의(비정상 종료) — 발언만이라도 보이게 남긴다. 실행 id 가 있으면 서버에서 아직 돌 수 있는 그 심의를 멈출 수 있다.
    out.push({ id: newId(), role: 'assistant', text: '', ts: Date.now(), delib: { turns, ...(runId ? { runId } : {}) } });
  }
  return out;
}

/** 브라우저 사본이 저장 한도로 줄인 칸(도구 활동·날것·심의 발언·근거)을 서버 정본으로 되채운다. 메시지 배열의 모양(개수·역할)이
 *  다르면 손대지 않는다(null) — 어긋난 자리에 다른 메시지의 기록을 붙이지 않게. 서버 사본에 없는 칸(보고서 번호·쉬운 설명·
 *  좌석 명단 등)은 브라우저 사본을 그대로 둔다. */
export function fillTrimmed(local: Message[], fresh: Message[]): Message[] | null {
  if (local.length !== fresh.length || local.some((m, i) => m.role !== fresh[i].role)) return null;
  return local.map((m, i) => {
    const f = fresh[i];
    const out: Message = { ...m };
    if (f.activity?.length && f.activity.length >= (m.activity?.length ?? 0)) out.activity = f.activity;
    if (m.delib && f.delib) {
      out.delib = {
        ...m.delib,
        ...(f.delib.turns?.length ? { turns: f.delib.turns } : {}),
        ...(f.delib.evidence?.length ? { evidence: f.delib.evidence } : {}),
      };
    }
    return out;
  });
}

/** 서버 대화(메시지 포함) → 로컬 Conversation. id 는 서버 id 그대로(재로드 시 중복 병합 안정). */
export function serverConvToLocal(
  conv: ServerConvMeta & { messages: ServerMessage[] },
): Conversation {
  // 마지막 사용자 발화의 meta 에서 고른 전문가를 되살린다. 없으면 안 건드린다 —
  // 다른 기기에서 열면 전문가가 조용히 풀리는데, 화면엔 그 전문가의 지난 답이 그대로
  // 있어서 사용자는 여전히 지정된 줄 안다(구 저장분은 meta 가 없어 그대로 비어 온다).
  let pin: Record<string, unknown> = {};
  for (let i = conv.messages.length - 1; i >= 0; i -= 1) {
    const m = conv.messages[i];
    if (m.role !== 'user') continue;
    const meta = (m.meta ?? {}) as Record<string, unknown>;
    if (typeof meta.pinned_agent === 'string') pin = meta;
    break;   // 가장 최근 발화의 상태가 현재 상태다 — 중간에 바꿨으면 그 뒤가 맞다
  }
  return {
    id: conv.id,
    serverId: conv.id,
    title: conv.title || '새 대화',
    messages: serverMessagesToLocal(conv.messages),
    createdAt: conv.created_at * 1000,
    updatedAt: conv.updated_at * 1000,
    ...(typeof pin.pinned_agent === 'string' ? { pinnedAgent: pin.pinned_agent } : {}),
    ...(typeof pin.pinned_agent_name === 'string'
      ? { pinnedAgentName: pin.pinned_agent_name } : {}),
    ...(Array.isArray(pin.pinned_agents) && pin.pinned_agents.length > 1
      ? { pinnedHelpers: (pin.pinned_agents as string[]).slice(1).map((k) => ({ key: k })) } : {}),
  };
}
