import { config } from '../config';
import type { DelibEvent, ErrorEvent, ResultBlock, StatusEvent, TokenEvent } from '../types/chat';

// Streaming chat client. EventSource cannot be used here: POST /agent/chat needs the
// X-CSRF-Token header (double-submit) and EventSource only does GET with cookies.
// So we drive the stream by hand: fetch(POST) -> response.body.getReader() and parse
// the `event:`/`data:` SSE frames manually. CSRF/credentials match api/client.ts.

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)'));
  return m ? decodeURIComponent(m[2]) : null;
}

export interface StreamHandlers {
  onStatus?: (e: StatusEvent) => void;
  onToken?: (e: TokenEvent) => void;
  onResult?: (block: ResultBlock) => void;
  onDelib?: (e: DelibEvent) => void;
  onError?: (e: ErrorEvent) => void;
  onDone?: () => void;
  signal?: AbortSignal;
}

interface SseFrame {
  event: string;
  data: string;
}

// Parse one SSE block (frames separated by a blank line) into {event, data}.
function parseFrame(block: string): SseFrame | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join('\n') };
}

function dispatch(frame: SseFrame, h: StreamHandlers): void {
  let payload: unknown;
  try {
    payload = frame.data ? JSON.parse(frame.data) : {};
  } catch {
    return; // ignore malformed data lines
  }
  switch (frame.event) {
    case 'status':
      h.onStatus?.(payload as StatusEvent);
      break;
    case 'token':
      h.onToken?.(payload as TokenEvent);
      break;
    case 'result':
      h.onResult?.(payload as ResultBlock);
      break;
    case 'delib':
      h.onDelib?.(payload as DelibEvent);
      break;
    case 'error':
      h.onError?.(payload as ErrorEvent);
      break;
    case 'done':
      h.onDone?.();
      break;
  }
}

// 멀티턴 계약(agent-server): 오래된 것→최신 순, 이번 message는 history에 넣지 않는다.
export interface HistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function streamChat(
  message: string,
  opts: { systemId?: string; mode?: string; history?: HistoryMessage[] } & StreamHandlers = {},
): Promise<void> {
  // Default = real relay (Agent Server → vLLM). Pass mode:'echo' only for local UI debugging
  // when the chat stack isn't up.
  const { systemId, mode, history, signal, ...handlers } = opts;
  const csrf = getCookie('hwax_csrf');
  const qs = mode ? `?mode=${encodeURIComponent(mode)}` : '';

  const res = await fetch(`${config.apiBase}/agent/chat${qs}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    },
    body: JSON.stringify({
      message,
      ...(systemId ? { system_id: systemId } : {}),
      ...(history && history.length > 0 ? { history } : {}),
    }),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError?.({ code: `http_${res.status}`, message: `Request failed (${res.status})` });
    handlers.onDone?.();
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  // 서버가 done 이벤트 없이 스트림을 끊어도(제너레이터 사망 등) 호출측 잠금이 풀리도록,
  // 스트림 종료 시 onDone 을 반드시 1회 보장한다(중복 방지).
  let doneFired = false;
  const guarded: StreamHandlers = {
    ...handlers,
    onDone: () => {
      if (doneFired) return;
      doneFired = true;
      handlers.onDone?.();
    },
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line (\n\n). Process complete ones, keep the rest.
      let sep: number;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const frame = parseFrame(block);
        if (frame) dispatch(frame, guarded);
      }
    }
    // Flush any trailing frame without a closing blank line.
    const frame = parseFrame(buffer);
    if (frame) dispatch(frame, guarded);
  } finally {
    reader.releaseLock();
    guarded.onDone?.();
  }
}
