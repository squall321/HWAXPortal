// 관리자 '전문가 고르기 검토' API — 에이전트 서버 박스 파일(실사용 질문 · 사람 표시)을 포털이 공유 비밀로 대신 부른다(docs/request-1029 E-5 · E5-2)
import { apiFetch, errorDetail } from './client';

/** 출처 — 지목 전문가 챗의 첫 발화 · 띵킹 질문 · 사람이 좌석을 고른 심의의 화두 · '/전문가' 질의(design-e5 2.2 H) */
export type SeatSource = 'persona' | 'thinking' | 'delib' | 'expert_cmd';
export const SEAT_SOURCES: SeatSource[] = ['persona', 'thinking', 'delib', 'expert_cmd'];
export const SOURCE_LABEL: Record<SeatSource, string> = {
  persona: '지목 전문가 챗',
  thinking: '띵킹',
  delib: '심의 화두',
  expert_cmd: "'/전문가'",
};

export type NoneKind = 'core_data' | 'out_of_pool';
export type Via = 'tree' | 'search';

/** 내 표시 — 주 전문가 1 ~ 3 · 같이 0 ~ 5, 또는 없음(둘 중 하나), 또는 모르겠음 */
export interface SeatMark {
  primary: string[];
  also: string[];
  none: NoneKind | null;
  unsure: boolean;
  via: Record<string, Via>;
  memo: string;
  t: number | null;
}

/** 질문 한 줄 — 순위 · 점수 · 지금 좌석은 오지 않는다(누설 규칙 L6). others 는 다른 사람이 단 표시의 **수**다 */
export interface SeatItem {
  qid: string;
  d: string | null;
  src: SeatSource;
  text: string;
  mine: SeatMark | null;
  others: number;
}

export interface SeatView {
  contract: string;
  total: number;
  counts: Partial<Record<SeatSource, number>>;
  /** 에이전트 서버가 뺀 수 — 8자 아래 · 홀로 서지 않는 발화 · 3글자 조각 자카드 0.8 이상의 겹침 */
  filtered: Record<string, number>;
  labeled: { mine: number | null; any: number };
  collect: { on: boolean; days: number | null };
  labelers_set: boolean;
  me: { by: string | null; can_label: boolean };
  items: SeatItem[];
}

export interface SeatExpert {
  key: string;
  name: string;
}

export interface SeatCard {
  key: string;
  name: string;
  desc: string;
  error: string | null;
}

export interface SeatLabelBody {
  qid: string;
  primary?: string[];
  also?: string[];
  none?: NoneKind | null;
  unsure?: boolean;
  via?: Record<string, Via>;
  memo?: string;
  remove?: boolean;
}

export interface CollectResult {
  harvest: {
    days: number;
    seen: Record<string, number>;
    sent: number;
    skipped: Record<string, number>;
    scrubbed: number;
  };
  agent: { added: number; dup: number; old: number; short: number };
}

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorDetail(body.detail, `${what} 실패 (${res.status})`));
  }
  return (await res.json()) as T;
}

export async function fetchSeatItems(q: {
  src: SeatSource | '';
  offset: number;
  limit: number;
}): Promise<SeatView> {
  const p = new URLSearchParams({ src: q.src, offset: String(q.offset), limit: String(q.limit) });
  return json(await apiFetch(`/auth/admin/seat-review/items?${p}`), '질문 불러오기');
}

export async function fetchSeatCatalog(): Promise<SeatExpert[]> {
  const r = await json<{ experts: SeatExpert[] }>(
    await apiFetch('/auth/admin/seat-review/catalog'),
    '전문가 명부',
  );
  return r.experts;
}

export async function fetchSeatCard(key: string): Promise<SeatCard> {
  return json(
    await apiFetch(`/auth/admin/seat-review/expert?${new URLSearchParams({ key })}`),
    '전문가 카드',
  );
}

export async function postSeatLabel(
  body: SeatLabelBody,
): Promise<{ ok: boolean; qid: string; removed: boolean }> {
  return json(
    await apiFetch('/auth/admin/seat-review/label', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
    '표시 저장',
  );
}

export async function runSeatCollect(): Promise<CollectResult> {
  return json(
    await apiFetch('/auth/admin/seat-review/collect', { method: 'POST' }),
    '지난 날 모으기',
  );
}
