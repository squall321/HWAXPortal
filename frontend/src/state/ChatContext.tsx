import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { streamChat } from '../api/chat.api';
import type { Message } from '../types/chat';

interface ChatContextValue {
  open: boolean;
  messages: Message[];
  input: string;
  streaming: boolean;
  setInput: (v: string) => void;
  openDock: () => void;
  closeDock: () => void;
  toggleDock: () => void;
  send: (message: string) => void;
  cancel: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
const ChatContext = createContext<ChatContextValue | undefined>(undefined);

let seq = 0;
const nextId = () => `m${++seq}`;

export function ChatProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const patch = useCallback((id: string, fn: (m: Message) => Message) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
  }, []);

  const send = useCallback(
    (message: string) => {
      const text = message.trim();
      if (!text || streaming) return;

      const userMsg: Message = { id: nextId(), role: 'user', text };
      const botId = nextId();
      const botMsg: Message = { id: botId, role: 'assistant', text: '', streaming: true };
      setMessages((prev) => [...prev, userMsg, botMsg]);
      setInput('');
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      void streamChat(text, {
        signal: controller.signal,
        onStatus: (e) => patch(botId, (m) => ({ ...m, status: e.step })),
        onToken: (e) => patch(botId, (m) => ({ ...m, text: m.text + e.delta, status: undefined })),
        onResult: (block) =>
          patch(botId, (m) => ({
            ...m,
            result: block,
            text: block.type === 'text' ? block.content : m.text,
            status: undefined,
          })),
        onError: (e) => patch(botId, (m) => ({ ...m, error: e.message, status: undefined })),
        onDone: () => {
          patch(botId, (m) => ({ ...m, streaming: false, status: undefined }));
          setStreaming(false);
          abortRef.current = null;
        },
      }).catch((err) => {
        // AbortError is expected on cancel; surface anything else.
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          patch(botId, (m) => ({ ...m, error: String(err), streaming: false, status: undefined }));
        } else {
          patch(botId, (m) => ({ ...m, streaming: false, status: undefined, error: m.error ?? '취소됨' }));
        }
        setStreaming(false);
        abortRef.current = null;
      });
    },
    [streaming, patch],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const openDock = useCallback(() => setOpen(true), []);
  const closeDock = useCallback(() => setOpen(false), []);
  const toggleDock = useCallback(() => setOpen((v) => !v), []);

  return (
    <ChatContext.Provider
      value={{ open, messages, input, streaming, setInput, openDock, closeDock, toggleDock, send, cancel }}
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
