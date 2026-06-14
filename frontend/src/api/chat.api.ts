import { config } from '../config';
import type { ErrorEvent, ResultBlock, StatusEvent, TokenEvent } from '../types/chat';

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
    case 'error':
      h.onError?.(payload as ErrorEvent);
      break;
    case 'done':
      h.onDone?.();
      break;
  }
}

export async function streamChat(
  message: string,
  opts: { systemId?: string; mode?: string } & StreamHandlers = {},
): Promise<void> {
  const { systemId, mode = 'echo', signal, ...handlers } = opts;
  const csrf = getCookie('hwax_csrf');

  const res = await fetch(`${config.apiBase}/agent/chat?mode=${encodeURIComponent(mode)}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    },
    body: JSON.stringify({ message, ...(systemId ? { system_id: systemId } : {}) }),
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
        if (frame) dispatch(frame, handlers);
      }
    }
    // Flush any trailing frame without a closing blank line.
    const frame = parseFrame(buffer);
    if (frame) dispatch(frame, handlers);
  } finally {
    reader.releaseLock();
  }
}
