// 포털 알림 조회 · 읽음 표시 — 머리줄의 알림 표지와 목록이 쓴다(docs/request-1117 contracts §7)
import { apiFetch, errorDetail } from './client';

export interface Notice {
  id: string;
  /** 알림 종류 — 지금은 delib_batch(심의 묶음 끝남) 하나. */
  kind: string;
  title: string;
  /** 한 줄 글. */
  line: string;
  /** 포털 안 경로(없을 수 있다). */
  link: string | null;
  /** 원천 id — 심의 묶음이면 batch_id(deliberate_batch_status 로 볼 수 있다). */
  source_id: string;
  /** 일이 일어난 시각(epoch 초) — 심의 묶음이면 끝난 시각. */
  created_at: number;
  read_at: number | null;
}

export interface NoticeList {
  items: Notice[];
  unread: number;
}

async function fail(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => null);
  throw new Error(errorDetail(body?.detail, fallback));
}

export async function fetchNotices(limit = 30): Promise<NoticeList> {
  const res = await apiFetch(`/notices-api?limit=${limit}`);
  if (!res.ok) return fail(res, `알림을 불러오지 못했습니다(HTTP ${res.status}).`);
  const data = (await res.json()) as NoticeList;
  return { items: Array.isArray(data.items) ? data.items : [], unread: Number(data.unread) || 0 };
}

/** 하나를 읽음으로 → 남은 안 읽은 수. */
export async function markNoticeRead(id: string): Promise<number> {
  const res = await apiFetch(`/notices-api/${encodeURIComponent(id)}/read`, { method: 'POST' });
  if (!res.ok) return fail(res, `읽음으로 표시하지 못했습니다(HTTP ${res.status}).`);
  return Number(((await res.json()) as { unread?: number }).unread) || 0;
}

/** 모두 읽음으로 → 남은 안 읽은 수(늘 0). */
export async function markAllNoticesRead(): Promise<number> {
  const res = await apiFetch('/notices-api/read-all', { method: 'POST' });
  if (!res.ok) return fail(res, `모두 읽음으로 표시하지 못했습니다(HTTP ${res.status}).`);
  return Number(((await res.json()) as { unread?: number }).unread) || 0;
}

/** 포털 안 경로만 링크로 — '/' 로 시작하고 '//' 가 아니며 역슬래시 · 제어 문자가 없다. 서버가 이미 거르지만 화면도 한 번 더 본다. */
export function safeNoticeLink(link: unknown): string | null {
  if (typeof link !== 'string') return null;
  const s = link.trim();
  if (!s.startsWith('/') || s.startsWith('//') || s.includes('\\')) return null;
  for (let i = 0; i < s.length; i += 1) {
    const c = s.charCodeAt(i);
    if (c < 0x20 || c === 0x7f) return null;
  }
  return s;
}

/** 머리줄 표지의 숫자 — 99 를 넘으면 '99+'. 0 이면 빈 글(표지를 그리지 않는다). */
export function unreadLabel(n: number): string {
  return n <= 0 ? '' : n > 99 ? '99+' : String(n);
}
