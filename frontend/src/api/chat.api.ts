import { apiFetch } from './client';
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
  /** 치명적이지 않은 경고(SSE warning) — 자격증명 강등 등. 응답은 계속된다. */
  onWarning?: (e: { code?: string; message: string }) => void;
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
    case 'warning':
      h.onWarning?.(payload as { code?: string; message: string });
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
  /** 이 좌석을 찾아낸 축들("도메인 · 구절"). 없으면 화두 질의로 나온 좌석이다. */
  axes?: string[];
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
  /** 앱 목록 — 앱 단위 선택(pinned_apps)용. 구 서버 응답에는 없다. */
  apps?: { app: string; label: string; desc?: string; tool_count: number }[];
}

/** 웹 리서치 소스 가용성 — 전역이 꺼져 있으면 토글을 비활성으로 그린다. */
export interface SearchCapability {
  sources: Record<string, { available: boolean }>;
  note?: string;
}

export async function fetchSearchCapability(signal?: AbortSignal): Promise<SearchCapability> {
  const r = await apiFetch('/agent/search-capability', { signal });
  if (!r.ok) throw new Error(`search-capability ${r.status}`);
  return (await r.json()) as SearchCapability;
}

/** 좌석 검색 축 — 풀의 도메인 분류에서 고른 것(자유 생성이 아니다). */
export interface SeatAxis {
  domain: string;
  phrase: string;
  seats?: string[];
}

export interface ExpertsResponse {
  recommended: RecommendedExpert[];
  /** 풀에 이 주제를 맡을 전문가가 없을 가능성이 높다는 신호.
   *  AIDataHub 가 역할/설명 어휘 일치로 판정한다 — 점수로는 못 한다(e5 코사인은
   *  무관한 문장끼리도 0.87~0.90 이라 어떤 질의든 그럴듯한 값이 나온다).
   *  실제 사고: "OCA 의 산소 확산 계수" 질의에 백플레인 TFT·안테나 OTA 가 추천됐고,
   *  랭킹 버그가 아니라 762명 풀에 그 전문성이 아예 없었다. */
  low_confidence?: boolean;
  /** 질문 연관도순 후보(상위 ~40) — 수동 추가 기본 노출·검색 우선순위에 사용. */
  candidates?: RecommendedExpert[];
  pool: PoolExpert[];
  /** 도구 정보 — 자동 파이프라인 + 주제 추천 + 전체 카탈로그. */
  tools?: ExpertsTools;
  /** 대화에서 고른 도메인 축. 빈 배열이면 화두 한 줄로만 추천했다는 뜻이다. */
  axes?: SeatAxis[];
  error?: string;
}

/** 화두로 추천 전문가 + 전체 풀을 받아온다(비스트리밍). 수동 선정 패널이 사용. */
export async function fetchDeliberateExperts(
  message: string,
  signal?: AbortSignal,
  // 대화 전체 — 축 분해에만 쓴다. 서버가 통째로 임베딩 질의에 넣지 않는다(그러면 추천이 나빠진다).
  history?: HistoryMessage[],
): Promise<ExpertsResponse> {
  const csrf = getCookie('hwax_csrf');
  try {
    const res = await apiFetch('/agent/deliberate/experts', {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      },
      body: JSON.stringify({ message, ...(history?.length ? { history } : {}) }),
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
    const res = await apiFetch('/agent/catalog/agent', {
      method: 'POST',

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
    pinnedApps?: string[];
    searchSources?: string[];
    /** 사용자 지정 전문가(agent_type) — 이 전문가 페르소나로 대화. */
    pinnedAgent?: string;
  } & StreamHandlers = {},
): Promise<void> {
  // Default = real relay (Agent Server → vLLM). Pass mode:'echo' only for local UI debugging
  // when the chat stack isn't up.
  const { systemId, mode, history, conversationId, delibOpts, pinnedTools, pinnedApps, pinnedAgent, searchSources, signal, ...handlers } = opts;
  const csrf = getCookie('hwax_csrf');
  const qs = mode ? `?mode=${encodeURIComponent(mode)}` : '';

  // ⚠ raw fetch 를 쓰면 안 된다. access token 수명이 900초라 화면을 15분만 띄워 둬도
  // 다음 전송이 401 이 되는데, raw fetch 에는 갱신도 재시도도 없어 그대로 실패한다.
  // 다른 화면은 apiFetch 를 타서 멀쩡하고 챗만 안 되는, "가끔 되고 오래 두면 안 되는"
  // 증상이 이것이었다. apiFetch 는 401 이면 /auth/refresh 한 번 후 재시도하고 Response 를
  // 그대로 돌려주므로 스트리밍에도 그대로 쓸 수 있다.
  const res = await apiFetch(`/agent/chat${qs}`, {
    method: 'POST',
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
      // 앱은 서버가 도구로 펼치므로 12개 캡이 아니라 앱 수 캡(3)을 쓴다.
      ...(pinnedApps && pinnedApps.length > 0 ? { pinned_apps: pinnedApps.slice(0, 3) } : {}),
      ...(pinnedAgent ? { pinned_agent: pinnedAgent } : {}),
      // 빈 배열도 의미가 있다(전부 끔) — undefined 와 반드시 구분해서 보낸다.
      ...(searchSources !== undefined ? { search_sources: searchSources } : {}),
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
