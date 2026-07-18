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
import type { Conversation, Message } from '../types/chat';
import {
  loadActiveId,
  loadConversations,
  newId,
  saveActiveId,
  saveConversations,
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
  sendMessage: (text: string) => void;
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
  /** 전송 시 서버로만 붙는 프리픽스(화면 표시는 원문) — 심의 페이지가 '/심의 ' 자동 부착에 사용. */
  sendPrefix?: string;
}

export function ChatProvider({ children, storagePrefix = 'hwax.chat', sendPrefix = '' }: ChatProviderProps) {
  // localStorage는 동기라 초기 렌더에서 바로 복원 — 새로고침 시 플래시 없음.
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations(storagePrefix));
  const [activeId, setActiveId] = useState<string | null>(() => {
    const saved = loadActiveId(storagePrefix);
    return saved && loadConversations(storagePrefix).some((c) => c.id === saved) ? saved : null;
  });
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
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
    (message: string) => {
      const text = message.trim();
      if (!text || streaming) return;

      const now = Date.now();
      const userMsg: Message = { id: newId(), role: 'user', text, ts: now };
      const botId = newId();
      const botMsg: Message = { id: botId, role: 'assistant', text: '', ts: now, streaming: true };

      // 멀티턴: 이번 user 메시지를 붙이기 전의 활성 대화 메시지가 history가 된다(중복 금지).
      const history = buildHistory(conversations.find((c) => c.id === activeId)?.messages ?? []);

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

      // 심의 페이지 등에서 서버 트리거 프리픽스를 자동 부착(이미 입력했으면 중복 금지).
      const outbound = sendPrefix && !text.startsWith(sendPrefix.trim()) ? sendPrefix + text : text;

      void streamChat(outbound, {
        signal: controller.signal,
        history,
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
                    },
                  ];
            return { ...m, status: e.step, activity };
          }),
        onToken: (e) =>
          patch(cid, botId, (m) => ({ ...m, text: m.text + e.delta, status: undefined })),
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
      }).catch((err) => {
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
    [streaming, activeId, conversations, patch, sendPrefix],
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

  const deleteConversation = useCallback((id: string) => {
    if (streamConvRef.current === id) abortRef.current?.abort();
    setConversations((prev) => prev.filter((c) => c.id !== id));
    setActiveId((prev) => (prev === id ? null : prev));
  }, []);

  const renameConversation = useCallback((id: string, title: string) => {
    const t = title.trim();
    if (!t) return;
    // 이름 변경은 updatedAt을 건드리지 않는다(사이드바 순서 유지).
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: t } : c)));
  }, []);

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
