// 다중 대화 + localStorage 영속을 관리하는 챗 전역 상태 — SSE 스트리밍은 chat.api 그대로 재사용
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { streamChat, type HistoryMessage } from '../api/chat.api';
import {
  createServerConversation,
  deleteServerConversation,
  getServerConversation,
  listServerConversations,
  renameServerConversation,
  serverConvToLocal,
  type ConvKind,
} from '../api/conversations.api';
import { useAuth } from '../auth/useAuth';
import type { Conversation, DelibData, DelibEvent, DelibOpts, DelibTally, DelibTurn, Message } from '../types/chat';
import {
  delibOptsToWire,
  loadActiveId,
  loadConversations,
  loadDelibOpts,
  newId,
  saveActiveId,
  saveConversations,
  saveDelibOpts,
} from './chatStore';

interface ChatContextValue {
  // 다중 대화
  conversations: Conversation[];
  activeId: string | null;
  activeConversation: Conversation | null;
  /** 활성 대화의 메시지(없으면 빈 배열) — ChatDock/MessageList 공용. */
  messages: Message[];
  input: string;
  streaming: boolean;
  setInput: (v: string) => void;
  sendMessage: (text: string, extraDelibOpts?: Record<string, unknown>) => void;
  /** 이어하기 — 끝난 심의(prior)에 사람 의견을 넣어 같은 전문가로 후속 심의를 스티어링. */
  continueDeliberation: (prior: DelibData, opinion: string) => void;
  /** 심의 손잡이(웹 토글) — 심의 페이지 패널이 읽고 쓴다. 전송 시 켠 것만 서버로 실린다. */
  delibOpts: DelibOpts;
  setDelibOpts: (o: DelibOpts) => void;
  stop: () => void;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  // 보조 페이지(/apps, /launch)의 플로팅 독 상태
  open: boolean;
  openDock: () => void;
  closeDock: () => void;
  toggleDock: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
const ChatContext = createContext<ChatContextValue | undefined>(undefined);

// 서버 캡(40항목/4000자)에 걸려 422가 나지 않도록 프론트에서도 자른다.
const HISTORY_MAX_ITEMS = 20;
const HISTORY_MAX_ITEM_CHARS = 4000;
const HISTORY_MAX_TOTAL_CHARS = 16000;

/** 멀티턴 history: 활성 대화의 기존 메시지 → 계약 형식(오래된 것→최신 순, 이번 발화 제외). */
function buildHistory(messages: Message[]): HistoryMessage[] {
  const items = messages
    .filter((m) => !m.error && m.text.trim() !== '')
    .map((m) => ({ role: m.role, content: m.text.slice(0, HISTORY_MAX_ITEM_CHARS) }));
  // 최근 것 우선 — 뒤에서부터 개수/총량 예산만큼 담고, 다시 시간순으로 뒤집는다.
  const out: HistoryMessage[] = [];
  let total = 0;
  for (let i = items.length - 1; i >= 0 && out.length < HISTORY_MAX_ITEMS; i--) {
    if (total + items[i].content.length > HISTORY_MAX_TOTAL_CHARS) break;
    total += items[i].content.length;
    out.push(items[i]);
  }
  return out.reverse();
}

/** 심의 delib 이벤트를 메시지의 DelibData 로 병합 — kind 별 리듀서. */
function mergeDelib(prev: DelibData | undefined, e: DelibEvent): DelibData {
  const d: DelibData = { ...(prev ?? {}) };
  switch (e.kind) {
    case 'stage': {
      const stage = String(e.stage ?? '');
      d.stage = stage;
      d.stages = [...(d.stages ?? []), stage];
      if (typeof e.n === 'number') d.roundN = e.n;
      break;
    }
    case 'personas':
      d.personas = (e.personas as DelibData['personas']) ?? [];
      if (typeof e.totalRounds === 'number') d.totalRounds = e.totalRounds;
      break;
    case 'evidence': {
      // 복수 출처(SignalForge 환기 + 정량 근거 선주입)가 서로 덮어쓰지 않게 append.
      const prevEv = Array.isArray(d.evidence) ? d.evidence : d.evidence ? [d.evidence] : [];
      d.evidence = [
        ...prevEv,
        {
          source: String(e.source ?? ''),
          text: String(e.text ?? ''),
          included: Boolean(e.included),
        },
      ];
      break;
    }
    case 'turn': {
      const turn: DelibTurn = {
        round: Number(e.round ?? 0),
        persona: String(e.persona ?? ''),
        say: String(e.say ?? ''),
        ...(e.position ? { position: String(e.position) } : {}),
        ...(e.stance ? { stance: String(e.stance) } : {}),
        ts: Date.now(),
      };
      d.turns = [...(d.turns ?? []), turn];
      break;
    }
    case 'decision':
      d.decision = String(e.text ?? '');
      break;
    case 'outcome':
      d.outcome = {
        report_id: (e.report_id as number | null) ?? null,
        title: String(e.title ?? ''),
        tally: e.tally as DelibTally | undefined,
        unanimous: Boolean(e.unanimous),
      };
      break;
  }
  return d;
}

/** 첫 사용자 메시지 → 대화 제목(≈40자). */
function makeTitle(text: string): string {
  const t = text.replace(/\s+/g, ' ').trim();
  if (!t) return '새 대화';
  return t.length > 40 ? `${t.slice(0, 40).trimEnd()}…` : t;
}

interface ChatProviderProps {
  children: ReactNode;
  /** 이력 localStorage 네임스페이스 — 심의 페이지는 'hwax.delib' 로 분리(기본 일반 챗). */
  storagePrefix?: string;
  /** 전송 시 서버로만 붙는 프리픽스(화면 표시는 원문) — 심의 페이지가 '/심의 ' 자동 부착에 사용.
   *  대화의 "첫 발화"에만 붙는다 — 이후 발화는 일반 챗(GLM 이어가기)으로 흐른다. */
  sendPrefix?: string;
  /** 서버 대화 저장소 동기화 — 설정 시 이 kind 의 서버 대화(MCP 심의 포함)를 목록에 병합하고,
   *  전송을 서버 대화에 저장한다(정본=서버, localStorage=캐시). 미설정이면 종전 로컬 전용. */
  serverKind?: ConvKind;
}

export function ChatProvider({
  children,
  storagePrefix = 'hwax.chat',
  sendPrefix = '',
  serverKind,
}: ChatProviderProps) {
  // localStorage는 동기라 초기 렌더에서 바로 복원 — 새로고침 시 플래시 없음.
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations(storagePrefix));
  const [activeId, setActiveId] = useState<string | null>(() => {
    const saved = loadActiveId(storagePrefix);
    return saved && loadConversations(storagePrefix).some((c) => c.id === saved) ? saved : null;
  });
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  // 심의 손잡이(웹 토글) — 상태는 UI 바인딩용, ref 는 전송 시점 읽기용(sendMessage 재생성·스테일 방지).
  const [delibOpts, setDelibOptsState] = useState<DelibOpts>(() => loadDelibOpts(storagePrefix));
  const delibOptsRef = useRef<DelibOpts>(delibOpts);
  const setDelibOpts = useCallback(
    (o: DelibOpts) => {
      delibOptsRef.current = o;
      setDelibOptsState(o);
      saveDelibOpts(o, storagePrefix);
    },
    [storagePrefix],
  );
  const abortRef = useRef<AbortController | null>(null);
  // 스트리밍 중인 대화 id — 그 대화가 삭제되면 스트림도 중단하기 위해 추적.
  const streamConvRef = useRef<string | null>(null);

  // 변경 시 저장(토큰 단위 갱신이 잦으므로 250ms 디바운스).
  useEffect(() => {
    const t = window.setTimeout(() => saveConversations(conversations, storagePrefix), 250);
    return () => window.clearTimeout(t);
  }, [conversations, storagePrefix]);
  useEffect(() => {
    saveActiveId(activeId, storagePrefix);
  }, [activeId, storagePrefix]);

  // ── 서버 대화 저장소 동기화(정본=서버, localStorage=캐시) ──────────────────
  const { user } = useAuth();
  // 서버 목록의 updated_at(ms) — "열 때 최신 로드" 판정용(서버가 더 새로우면 상세 재로드).
  const serverMetaRef = useRef<Map<string, number>>(new Map());
  // 상세 로드 중복 방지.
  const detailLoadingRef = useRef<Set<string>>(new Set());

  /** 서버 상세를 가져와 해당 대화의 메시지를 교체(스트리밍 중엔 건드리지 않음). */
  const refreshFromServer = useCallback((serverId: string) => {
    if (detailLoadingRef.current.has(serverId)) return;
    detailLoadingRef.current.add(serverId);
    void getServerConversation(serverId)
      .then((detail) => {
        if (!detail) return;
        const fresh = serverConvToLocal(detail);
        setConversations((prev) =>
          prev.map((c) =>
            (c.serverId ?? c.id) !== serverId || streamConvRef.current === c.id
              ? c
              : { ...c, title: fresh.title, messages: fresh.messages, updatedAt: fresh.updatedAt },
          ),
        );
      })
      .catch(() => {
        /* 서버 미가용 — 캐시로 계속(비치명적) */
      })
      .finally(() => {
        detailLoadingRef.current.delete(serverId);
      });
  }, []);

  // 로그인 후 1회(+사용자 변경 시): 서버 목록을 로컬 목록에 병합. 메시지는 열 때 로드.
  useEffect(() => {
    if (!serverKind || !user) return;
    let cancelled = false;
    void listServerConversations()
      .then((list) => {
        if (cancelled) return;
        const metas = list.filter((m) => m.kind === serverKind);
        for (const m of metas) serverMetaRef.current.set(m.id, m.updated_at * 1000);
        setConversations((prev) => {
          const bySrv = new Map(prev.map((c) => [c.serverId ?? c.id, c] as const));
          const merged = [...prev];
          for (const m of metas) {
            if (bySrv.has(m.id)) continue; // 이미 로컬 캐시에 있음 — 상세는 열 때 판정
            merged.push({
              id: m.id,
              serverId: m.id,
              title: m.title || '새 대화',
              messages: [], // 자리표시자 — 선택 시 상세 로드
              createdAt: m.created_at * 1000,
              updatedAt: m.updated_at * 1000,
            });
          }
          return merged.sort((a, b) => b.updatedAt - a.updatedAt);
        });
      })
      .catch(() => {
        /* 서버 미가용 — 로컬 캐시만으로 동작 */
      });
    return () => {
      cancelled = true;
    };
  }, [serverKind, user]);

  // "열 때 최신 로드": 활성 대화가 서버 대화인데 비었거나 서버가 더 새로우면 상세 재로드.
  useEffect(() => {
    if (!serverKind || !activeId) return;
    const conv = conversations.find((c) => c.id === activeId);
    const sid = conv?.serverId;
    if (!conv || !sid) return;
    const serverTs = serverMetaRef.current.get(sid) ?? 0;
    const stale = conv.messages.length === 0 || serverTs > conv.updatedAt + 2000;
    if (stale && streamConvRef.current !== conv.id) refreshFromServer(sid);
    // conversations 를 deps 에 넣으면 교체 직후 재실행되지만 stale 판정이 false 라 루프 없음.
  }, [serverKind, activeId, conversations, refreshFromServer]);

  const patch = useCallback((convId: string, msgId: string, fn: (m: Message) => Message) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id !== convId
          ? c
          : {
              ...c,
              updatedAt: Date.now(),
              messages: c.messages.map((m) => (m.id === msgId ? fn(m) : m)),
            },
      ),
    );
  }, []);

  const sendMessage = useCallback(
    (message: string, extraDelibOpts?: Record<string, unknown>) => {
      const text = message.trim();
      if (!text || streaming) return;

      const now = Date.now();
      const userMsg: Message = { id: newId(), role: 'user', text, ts: now };
      const botId = newId();
      const botMsg: Message = { id: botId, role: 'assistant', text: '', ts: now, streaming: true };

      // 멀티턴: 이번 user 메시지를 붙이기 전의 활성 대화 메시지가 history가 된다(중복 금지).
      const existing = conversations.find((c) => c.id === activeId);
      const history = buildHistory(existing?.messages ?? []);
      // 첫 발화 여부 — sendPrefix(심의 트리거)는 첫 발화에만 붙는다(이후는 GLM 이어가기).
      const isFirstTurn = !existing || existing.messages.length === 0;

      // 활성 대화가 없으면(랜딩/새 대화) 첫 전송 시점에 대화를 생성한다.
      let convId = activeId && conversations.some((c) => c.id === activeId) ? activeId : null;
      if (!convId) {
        convId = newId();
        const conv: Conversation = {
          id: convId,
          title: makeTitle(text),
          messages: [userMsg, botMsg],
          createdAt: now,
          updatedAt: now,
        };
        setConversations((prev) => [conv, ...prev]);
        setActiveId(convId);
      } else {
        setConversations((prev) =>
          prev.map((c) =>
            c.id !== convId
              ? c
              : { ...c, updatedAt: now, messages: [...c.messages, userMsg, botMsg] },
          ),
        );
      }

      setInput('');
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;
      streamConvRef.current = convId;
      const cid = convId;

      // 심의 페이지 등에서 서버 트리거 프리픽스를 자동 부착 — "첫 발화"에만(이후 발화는
      // 일반 챗으로 흘려 심의 로그 위에서 GLM 이어가기가 되게 한다). 직접 입력했으면 존중.
      const applyPrefix = sendPrefix && (isFirstTurn || text.startsWith(sendPrefix.trim()));
      const outbound = applyPrefix && !text.startsWith(sendPrefix.trim()) ? sendPrefix + text : text;

      void (async () => {
        // 서버 정본 확보 — serverKind 설정 시 이 대화의 서버 id 를 보장(없으면 생성).
        // 실패해도 채팅은 계속(로컬 캐시 전용) — cae00 등 서버 저장 미가용 폴백.
        let serverId = existing?.serverId;
        if (serverKind && !serverId) {
          try {
            serverId = await createServerConversation(makeTitle(text), serverKind);
            const sid = serverId;
            serverMetaRef.current.set(sid, now);
            setConversations((prev) => prev.map((c) => (c.id === cid ? { ...c, serverId: sid } : c)));
          } catch {
            serverId = undefined;
          }
        }
        await streamChat(outbound, {
        signal: controller.signal,
        history,
        ...(serverId ? { conversationId: serverId } : {}),
        // 심의 손잡이(웹 토글) — 켠 것만. 서버 트리거 프리픽스가 붙는 심의 첫 발화에만 의미가 있지만,
        // 이어가기(일반 챗)로 흘러도 agent-server 챗 경로가 무시하므로 항상 실어도 무해하다.
        ...(() => {
          // 패널 손잡이(켠 것만) + 일회성 extra(이어하기 human_note·요약·personas)를 병합
          const w = { ...delibOptsToWire(delibOptsRef.current), ...(extraDelibOpts ?? {}) };
          return Object.keys(w).length > 0 ? { delibOpts: w } : {};
        })(),
        onStatus: (e) =>
          patch(cid, botId, (m) => {
            // 활동 패널용 누적 — 같은 step 연속 중복은 스킵, 60건 캡(영속 크기 통제).
            const prev = m.activity ?? [];
            const last = prev[prev.length - 1];
            const activity =
              last && last.step === e.step
                ? prev
                : [
                    ...prev.slice(-59),
                    {
                      ts: Date.now(),
                      step: e.step,
                      tool: e.tool ?? null,
                      ...(e.personas ? { personas: e.personas } : {}),
                      ...(e.tools_used ? { tools_used: e.tools_used } : {}),
                      ...(e.detail ? { detail: e.detail } : {}),
                      ...(e.result_preview ? { result_preview: e.result_preview } : {}),
                    },
                  ];
            return { ...m, status: e.step, activity };
          }),
        onToken: (e) =>
          patch(cid, botId, (m) => ({ ...m, text: m.text + e.delta, status: undefined })),
        onDelib: (e) => patch(cid, botId, (m) => ({ ...m, delib: mergeDelib(m.delib, e) })),
        onResult: (block) =>
          patch(cid, botId, (m) => ({
            ...m,
            result: block,
            text: block.type === 'text' ? block.content : m.text,
            status: undefined,
          })),
        onError: (e) => patch(cid, botId, (m) => ({ ...m, error: e.message, status: undefined })),
        onDone: () => {
          patch(cid, botId, (m) => ({ ...m, streaming: false, status: undefined }));
          setStreaming(false);
          abortRef.current = null;
          streamConvRef.current = null;
        },
        });
      })().catch((err) => {
        // AbortError is expected on stop(); surface anything else.
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          patch(cid, botId, (m) => ({
            ...m,
            error: String(err),
            streaming: false,
            status: undefined,
          }));
        } else {
          patch(cid, botId, (m) => ({
            ...m,
            streaming: false,
            status: undefined,
            // 토큰이 이미 조금 왔으면 부분 응답을 그대로 두고, 아니면 취소를 표기.
            error: m.error ?? (m.text ? undefined : '취소됨'),
          }));
        }
        setStreaming(false);
        abortRef.current = null;
        streamConvRef.current = null;
      });
    },
    [streaming, activeId, conversations, patch, sendPrefix, serverKind],
  );

  // 이어하기(사람 개입 스티어링) — 끝난 심의에 사람 의견을 넣어, 같은 전문가가 이전 결정을
  // 이어받아 그 의견 방향으로 다시 토론하게 한다. 원 화두는 활성 대화의 첫 사용자 발화에서 취한다.
  const continueDeliberation = useCallback(
    (prior: DelibData, opinion: string) => {
      const note = opinion.trim();
      if (!note || streaming) return;
      const conv = conversations.find((c) => c.id === activeId);
      const firstUser = conv?.messages.find((m) => m.role === 'user');
      const topic = (firstUser?.text ?? '').replace(/^\/(심의|deliberate|토의)\s*/, '').trim();
      if (!topic) return;
      sendMessage('/심의 ' + topic, {
        human_note: note,
        continue_summary: (prior.decision ?? '').slice(0, 8000),
        personas: (prior.personas ?? []).map((p) => ({ key: p.key, role: p.role ?? '' })),
      });
    },
    [conversations, activeId, streaming, sendMessage],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const newConversation = useCallback(() => {
    // 빈 대화를 목록에 만들지 않는다 — activeId=null이 '새 대화(랜딩)' 상태.
    setActiveId(null);
    setInput('');
  }, []);

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const deleteConversation = useCallback(
    (id: string) => {
      if (streamConvRef.current === id) abortRef.current?.abort();
      const sid = conversations.find((c) => c.id === id)?.serverId;
      if (sid) {
        serverMetaRef.current.delete(sid);
        void deleteServerConversation(sid).catch(() => {});
      }
      setConversations((prev) => prev.filter((c) => c.id !== id));
      setActiveId((prev) => (prev === id ? null : prev));
    },
    [conversations],
  );

  const renameConversation = useCallback(
    (id: string, title: string) => {
      const t = title.trim();
      if (!t) return;
      const sid = conversations.find((c) => c.id === id)?.serverId;
      if (sid) void renameServerConversation(sid, t).catch(() => {});
      // 이름 변경은 updatedAt을 건드리지 않는다(사이드바 순서 유지).
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: t } : c)));
    },
    [conversations],
  );

  const openDock = useCallback(() => setOpen(true), []);
  const closeDock = useCallback(() => setOpen(false), []);
  const toggleDock = useCallback(() => setOpen((v) => !v), []);

  const activeConversation = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? null,
    [conversations, activeId],
  );
  const messages = activeConversation?.messages ?? [];

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeId,
        activeConversation,
        messages,
        input,
        streaming,
        setInput,
        sendMessage,
        continueDeliberation,
        delibOpts,
        setDelibOpts,
        stop,
        newConversation,
        selectConversation,
        deleteConversation,
        renameConversation,
        open,
        openDock,
        closeDock,
        toggleDock,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within <ChatProvider>');
  return ctx;
}
