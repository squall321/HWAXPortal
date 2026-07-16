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
import { streamChat } from '../api/chat.api';
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

/** 첫 사용자 메시지 → 대화 제목(≈40자). */
function makeTitle(text: string): string {
  const t = text.replace(/\s+/g, ' ').trim();
  if (!t) return '새 대화';
  return t.length > 40 ? `${t.slice(0, 40).trimEnd()}…` : t;
}

export function ChatProvider({ children }: { children: ReactNode }) {
  // localStorage는 동기라 초기 렌더에서 바로 복원 — 새로고침 시 플래시 없음.
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations());
  const [activeId, setActiveId] = useState<string | null>(() => {
    const saved = loadActiveId();
    return saved && loadConversations().some((c) => c.id === saved) ? saved : null;
  });
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // 스트리밍 중인 대화 id — 그 대화가 삭제되면 스트림도 중단하기 위해 추적.
  const streamConvRef = useRef<string | null>(null);

  // 변경 시 저장(토큰 단위 갱신이 잦으므로 250ms 디바운스).
  useEffect(() => {
    const t = window.setTimeout(() => saveConversations(conversations), 250);
    return () => window.clearTimeout(t);
  }, [conversations]);
  useEffect(() => {
    saveActiveId(activeId);
  }, [activeId]);

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

      void streamChat(text, {
        signal: controller.signal,
        onStatus: (e) => patch(cid, botId, (m) => ({ ...m, status: e.step })),
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
    [streaming, activeId, conversations, patch],
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
