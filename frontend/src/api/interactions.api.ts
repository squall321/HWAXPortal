// 상호작용 기록 API — 박스 상태(켜졌나 · 알림 문구) · 내 기록 · 지우기 청구 · 분석가 검색 · 원문 열기(docs/interaction-data contract §6)
import { apiFetch, errorDetail } from './client';

/** 켜진 박스에서만 온다 — 꺼진 박스는 404 라 null 이다(메뉴 · 알림을 그리지 않는다). */
export interface InteractionStatus {
  enabled: true;
  notice: string;
  analyst: boolean;
  share_max_mb: number;
  health?: { ok: boolean; problems: string[]; sources: Record<string, { state: string; last_ok: number | null }> };
  counts?: { events: number; shared: number };
}

export interface InteractionRow {
  id: string;
  ts: number;
  surface: string;
  actor: string | null;
  affiliation: string | null;
  client: string | null;
  conv_id: string | null;
  app: string | null;
  tool: string | null;
  model: string | null;
  status: string | null;
  ms: number | null;
  via: string | null;
  input_preview: string | null;
  output_preview: string | null;
  output_chars: number | null;
}

export interface InteractionPage {
  items: InteractionRow[];
  more: boolean;
  next_before: string | null;
}

export interface SharedSession {
  id: string;
  session_id: string;
  title: string | null;
  client: string | null;
  kind: 'tool' | 'transcript';
  messages: { role: string; content: string; tools?: string[] }[];
  chars: number;
  raw_available: boolean;
}

export interface InteractionFull extends Omit<InteractionRow, 'input_preview' | 'output_preview'> {
  input: string | null;
  output: string | null;
  output_sha256: string | null;
  corr: string | null;
  rid: string | null;
  meta: Record<string, unknown> | null;
  shared?: SharedSession | null;
}

/** 겉면 이름표 — 원장의 surface 낱말(contract §2)을 사람 말로 */
export const SURFACE_LABEL: Record<string, string> = {
  web_chat: '웹 챗',
  web_delib: '웹 심의',
  think: '띵킹',
  routine: '분석 루틴',
  procedure: '절차',
  mcp_call: 'MCP 도구 호출',
  tool_search: '도구 검색',
  shared_claude: '공유한 Claude 대화',
};

let statusOnce: Promise<InteractionStatus | null> | null = null;

/** 박스 상태 — 한 탭에 한 번만 묻는다(헤더 · 챗 첫 화면 · 토큰 화면이 같이 쓴다). 못 받으면 null(꺼진 것으로 그린다). */
export function fetchInteractionStatus(): Promise<InteractionStatus | null> {
  if (!statusOnce) {
    statusOnce = apiFetch('/interactions/status')
      .then((r) => (r.ok ? (r.json() as Promise<InteractionStatus>) : null))
      .catch(() => null);
  }
  return statusOnce;
}

/** 분석가 화면 머리 — 수집 상태(코드) · 원장의 수까지(detail=1). 탭 사이에 나눠 쓰지 않는다. */
export function fetchInteractionDetail(): Promise<InteractionStatus | null> {
  return apiFetch('/interactions/status?detail=1')
    .then((r) => (r.ok ? (r.json() as Promise<InteractionStatus>) : null))
    .catch(() => null);
}

async function readJson<T>(res: Response, fallback: string): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(errorDetail((err as { detail?: unknown }).detail, `${fallback} (${res.status})`));
  }
  return (await res.json()) as T;
}

function qs(p: Record<string, string | number | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== '') u.set(k, String(v));
  const s = u.toString();
  return s ? `?${s}` : '';
}

export async function listMine(p: { q?: string; surface?: string; before?: string }): Promise<InteractionPage> {
  return readJson(await apiFetch(`/interactions/me${qs(p)}`), '내 기록을 불러오지 못했습니다');
}

export async function getMine(id: string): Promise<InteractionFull> {
  return readJson(await apiFetch(`/interactions/me/${encodeURIComponent(id)}`), '기록을 열지 못했습니다');
}

export const ERASE_CONFIRM = '전부 지웁니다';

export async function eraseMine(): Promise<{ events: number; shared: number }> {
  return readJson(
    await apiFetch('/interactions/me', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: ERASE_CONFIRM }),
    }),
    '지우지 못했습니다',
  );
}

export async function adminSearch(p: {
  q?: string;
  actor?: string;
  surface?: string;
  app?: string;
  days?: number;
  before?: string;
}): Promise<InteractionPage> {
  return readJson(await apiFetch(`/interactions/admin/search${qs(p)}`), '검색하지 못했습니다');
}

export async function adminGet(id: string): Promise<InteractionFull> {
  return readJson(await apiFetch(`/interactions/admin/${encodeURIComponent(id)}`), '원문을 열지 못했습니다');
}

/** 설정 배치의 공유 칸 옆 한 줄 — portal: 이 박스가 상호작용 기록을 켰나, capture: 게이트웨이 원문 수집(모르면 null) */
export interface ShareBox {
  portal: boolean;
  capture: boolean | null;
}

export async function fetchShareBox(): Promise<ShareBox> {
  return readJson(await apiFetch('/auth/pat/share'), '박스 스위치를 읽지 못했습니다');
}
