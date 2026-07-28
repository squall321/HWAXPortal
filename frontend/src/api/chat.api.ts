import { config } from '../config';
import type { DelibEvent, ErrorEvent, ResultBlock, StatusEvent, TokenEvent, ToolCatalog } from '../types/chat';

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
  /** 도구 카탈로그(SSE tools) — '/도구' 검색 응답. 선택 카드 렌더용. */
  onTools?: (e: ToolCatalog) => void;
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
    case 'tools':
      h.onTools?.(payload as ToolCatalog);
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

// ── 심의 전 전문가 선정 미리보기 ────────────────────────────────────────────
export interface RecommendedExpert {
  key: string;
  name: string;
  role: string;
  score?: number | null;
  why?: string;
  tags?: string[];
}
export interface PoolExpert {
  key: string;
  name: string;
  tags: string[];
}
export interface ToolEntry {
  name: string;
  desc: string;
  score?: number;
  /** 소유 MCP 앱 키(게이트웨이 백엔드) — 계층 선택용. */
  group?: string;
  /** 사람이 읽는 앱 이름(예: 열충격 해석). */
  group_label?: string;
}

export interface ExpertsTools {
  /** 주제 관련도순 추천 도구 — 선택하면 심의에서 실제 호출돼 정량 근거로 주입. */
  recommended: ToolEntry[];
  /** 심의 파이프라인이 자동 사용하는 도구(정보 표시 — 항상 돌아감). */
  pipeline: string[];
  /** 전문가가 쓰는 도구 — AIDH 가 관리하는 도구↔에이전트 연결(compatible_agents). */
  expert_tools?: (ToolEntry & { agents?: string[] })[];
  /** 전체 도구 카탈로그 — 검색 추가용. */
  all: ToolEntry[];
}

export interface ExpertsResponse {
  recommended: RecommendedExpert[];
  /** 질문 연관도순 후보(상위 ~40) — 수동 추가 기본 노출·검색 우선순위에 사용. */
  candidates?: RecommendedExpert[];
  pool: PoolExpert[];
  /** 도구 정보 — 자동 파이프라인 + 주제 추천 + 전체 카탈로그. */
  tools?: ExpertsTools;
  error?: string;
}

/** 화두로 추천 전문가 + 전체 풀을 받아온다(비스트리밍). 수동 선정 패널이 사용. */
export async function fetchDeliberateExperts(
  message: string,
  signal?: AbortSignal,
): Promise<ExpertsResponse> {
  const csrf = getCookie('hwax_csrf');
  try {
    const res = await fetch(`${config.apiBase}/agent/deliberate/experts`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      },
      body: JSON.stringify({ message }),
      signal,
    });
    if (!res.ok) return { recommended: [], pool: [], error: `http_${res.status}` };
    return (await res.json()) as ExpertsResponse;
  } catch {
    return { recommended: [], pool: [], error: 'network' };
  }
}

// ── 전문가 상세 + 보유 지식(카탈로그 브라우즈) ─────────────────────────────
export interface AgentDetail {
  key: string;
  name: string;
  role: string;
  tags: string[];
  samples: string[];
  records: { id: string; title: string; data_type: string }[];
  error?: string;
}

export async function fetchAgentDetail(key: string): Promise<AgentDetail> {
  const csrf = getCookie('hwax_csrf');
  const empty: AgentDetail = { key, name: key, role: '', tags: [], samples: [], records: [] };
  try {
    const res = await fetch(`${config.apiBase}/agent/catalog/agent`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
      body: JSON.stringify({ key }),
    });
    if (!res.ok) return { ...empty, error: `http_${res.status}` };
    return { ...empty, ...(await res.json()) };
  } catch {
    return { ...empty, error: 'network' };
  }
}

export async function streamChat(
  message: string,
  opts: {
    systemId?: string;
    mode?: string;
    history?: HistoryMessage[];
    /** 서버 대화 저장소 정본 id — 있으면 백엔드가 이 대화에 user+assistant 를 서버 저장. */
    conversationId?: string;
    /** 심의 손잡이 오버라이드(웹 토글) — 켠 것만. 심의(/심의) 요청에서만 의미.
     *  스칼라 손잡이 외에 이어하기 필드(human_note·continue_summary·personas·tools)도 실린다. */
    delibOpts?: Record<string, unknown>;
    /** 사용자 지정 우선 도구(챗) — 도구 카탈로그에서 선택. 서버가 우선 사용을 강제. */
    pinnedTools?: string[];
    /** 사용자 지정 전문가(agent_type) — 이 전문가 페르소나로 대화. */
    pinnedAgent?: string;
  } & StreamHandlers = {},
): Promise<void> {
  // Default = real relay (Agent Server → vLLM). Pass mode:'echo' only for local UI debugging
  // when the chat stack isn't up.
  const { systemId, mode, history, conversationId, delibOpts, pinnedTools, pinnedAgent, signal, ...handlers } = opts;
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
      ...(conversationId ? { conversation_id: conversationId } : {}),
      ...(delibOpts && Object.keys(delibOpts).length > 0 ? { delib_opts: delibOpts } : {}),
      ...(pinnedTools && pinnedTools.length > 0 ? { pinned_tools: pinnedTools.slice(0, 12) } : {}),
      ...(pinnedAgent ? { pinned_agent: pinnedAgent } : {}),
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
