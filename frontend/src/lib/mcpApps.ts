// MCP Apps 패널 호스트의 순수 규칙 — CSP · 문서 짓기 · 브리지 메시지 판정 · 높이 죔 · open-link 허용 · 탭의 열린 패널 자리(docs/request-1027 HP-42)
//
// 설계 docs/request-1027/design-ha09-ha20.md B5.5 · 사용자 결정 10-31(B-3 (가) srcdoc · 같은 출처 없음 · CSP 메타, B-4 (가) 그 탭에서만,
// B-5 (가) 모델 맥락은 1단계에서 받지 않는다). 화면 부품(McpAppPanel)은 이 파일의 규칙만 쓴다 — 보안 판정이 한곳에 있게.

/** SimFlow 가정(Q-S1 의 답 전) — 패널이 ui/initialize 에 싣는 판과 호스트가 답하는 판. 답이 오면 이 줄만 고친다. */
export const ASSUME_PROTOCOL_VERSIONS = ['2026-01-26'];
export const HOST_PROTOCOL_VERSION = ASSUME_PROTOCOL_VERSIONS[0];

export const UI_HOST_TOKEN = 'mcp-apps/1'; // 챗 요청의 표지 — 포털 · 에이전트 서버와 같은 글자
export const SANDBOX = 'allow-scripts'; // ⚠ 이 하나뿐이다 — same-origin · forms · popups · top-navigation 을 더하면 격리가 깨진다
export const HEIGHT_MIN = 120;
export const HEIGHT_MAX = 1200;
export const HEIGHT_DEFAULT = 360;
export const MAX_OPEN = 2; // 탭에 열어 두는 패널 수 — 셋째를 열면 가장 오래된 것을 접는다
export const RATE_PER_SEC = 50; // 패널 하나가 1초에 보낼 수 있는 메시지 — 넘으면 답하지 않고 버린다(끝없는 루프 패널)
export const MSG_MAX_CHARS = 5 * 1024 * 1024; // 메시지 하나의 JSON 길이 위쪽(포털 호출 상한 4 MiB + 여유)

// 1단계에서 받지 않는 패널 메서드(B-5 (가)) — '지원 안 함' 오류로 답한다(조용히 삼키지 않는다)
export const UNSUPPORTED = new Set(['ui/update-model-context', 'ui/message', 'ui/request-display-mode']);

const DOMAIN_RE = /^https?:\/\/(\*\.)?[a-z0-9-]+(\.[a-z0-9-]+)*(:\d{1,5})?$/;

export interface PanelCsp {
  connectDomains?: string[];
  resourceDomains?: string[];
}

function clean(list: string[] | undefined): string[] {
  return (list ?? []).map((d) => String(d).trim().toLowerCase()).filter((d) => DOMAIN_RE.test(d));
}

/** 패널 CSP — 기본은 바깥에 닿지 못한다(connect · frame · form · base 모두 'none'). 도메인은 포털이 준 교집합만, 꼴이 틀린 것은 다시 버린다. */
export function buildCsp(csp: PanelCsp | undefined): string {
  const res = clean(csp?.resourceDomains).join(' ');
  const con = clean(csp?.connectDomains).join(' ');
  const r = res ? ` ${res}` : '';
  return [
    "default-src 'none'",
    `script-src 'unsafe-inline'${r}`,
    `style-src 'unsafe-inline'${r}`,
    `img-src data: blob:${r}`,
    `font-src data:${r}`,
    'media-src data: blob:',
    `connect-src ${con || "'none'"}`,
    "frame-src 'none'",
    "form-action 'none'",
    "base-uri 'none'",
  ].join('; ');
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

/** srcdoc 문서 — CSP 메타가 문서 맨 앞(head 의 첫 자식)이다. 앱 문서를 그 뒤에 그대로 잇는다(두 번째 doctype · html · head 는 파서가 버리고
 *  앱의 head 내용이 우리 head 에 이어진다). 앱이 제 CSP 를 더 넣어도 둘 다 걸려 더 좁아질 뿐이다. */
export function buildPanelDoc(html: string, csp: PanelCsp | undefined): string {
  return (
    '<!doctype html><html><head>' +
    `<meta http-equiv="Content-Security-Policy" content="${escapeAttr(buildCsp(csp))}">` +
    '<meta name="referrer" content="no-referrer">' +
    html
  );
}

export function clampHeight(h: unknown): number {
  const n = typeof h === 'number' && Number.isFinite(h) ? h : HEIGHT_DEFAULT;
  return Math.max(HEIGHT_MIN, Math.min(HEIGHT_MAX, Math.round(n)));
}

/** ui/open-link — http(s) 이고 출처가 허용 목록에 있을 때만(포털이 그 앱 타일 주소 · 박스 허용으로 준 것). */
export function linkAllowed(url: unknown, origins: string[]): boolean {
  if (typeof url !== 'string' || url.length > 4096) return false;
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return false;
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
  return origins.map((o) => o.toLowerCase().replace(/\/$/, '')).includes(u.origin.toLowerCase());
}

export interface RpcMsg {
  jsonrpc: '2.0';
  id?: string | number;
  method?: string;
  params?: Record<string, unknown>;
  result?: unknown;
  error?: { code: number; message: string };
}

/** 브리지가 받는 메시지인가 — JSON-RPC 2.0 꼴 · 크기 상한. 보낸 창(event.source)은 부르는 쪽이 먼저 본다(같은 출처가 없어 origin 은 'null' 이라
 *  origin 으로는 가를 수 없다). */
export function rpcOf(data: unknown): RpcMsg | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const m = data as Record<string, unknown>;
  if (m.jsonrpc !== '2.0') return null;
  if (m.method !== undefined && (typeof m.method !== 'string' || m.method.length > 200)) return null;
  if (m.id !== undefined && typeof m.id !== 'string' && typeof m.id !== 'number') return null;
  if (m.params !== undefined && (typeof m.params !== 'object' || m.params === null || Array.isArray(m.params))) return null;
  try {
    if (JSON.stringify(m).length > MSG_MAX_CHARS) return null;
  } catch {
    return null;
  }
  return m as unknown as RpcMsg;
}

/** 초당 상한 — 패널마다 하나. 1초 창에 RATE_PER_SEC 를 넘으면 거짓. */
export function rateGate(max = RATE_PER_SEC): () => boolean {
  let at = 0;
  let n = 0;
  return () => {
    const now = Date.now();
    if (now - at >= 1000) {
      at = now;
      n = 0;
    }
    n += 1;
    return n <= max;
  };
}

// ── 탭의 열린 패널 자리 — 둘까지. 셋째가 열리면 가장 오래된 것을 접는다(B5.5) ─────────────────────────────────────────────
const open: { key: string; fold: () => void }[] = [];

export function claimSlot(key: string, fold: () => void): void {
  releaseSlot(key);
  open.push({ key, fold });
  while (open.length > MAX_OPEN) {
    const old = open.shift();
    old?.fold();
  }
}

export function releaseSlot(key: string): void {
  const i = open.findIndex((o) => o.key === key);
  if (i >= 0) open.splice(i, 1);
}

// ── 그 탭이 받은 결과 — 영속하지 않는다(B-4 · B-6 (가)). 새로고침 · 다른 기기에서는 비어 '다시 열기' 가 입력만 보낸다 ───────────────
export interface PanelResult {
  content?: unknown[];
  structuredContent?: unknown;
  _meta?: unknown;
}
const live = new Map<string, PanelResult | null>();

export function panelKey(p: { call?: string; uri: string; tool: string }): string {
  return `${p.call || ''}|${p.tool}|${p.uri}`;
}

export function rememberLive(key: string, result: PanelResult | null): void {
  live.set(key, result);
  while (live.size > 64) {
    const first = live.keys().next().value;
    if (first === undefined) break;
    live.delete(first);
  }
}

/** 이 탭이 그 사건을 받았나 — 받았으면 결과(잘렸으면 null), 아니면 undefined. */
export function liveResult(key: string): PanelResult | null | undefined {
  return live.has(key) ? (live.get(key) ?? null) : undefined;
}
