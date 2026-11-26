// 심의 보고서를 Report Archive 시스템 공간에 올리기 — 이 박스의 게시판 · 게시 미리보기 · 게시를 포털에 묻는다(docs/ra-delib-standard RS-3)
import { apiFetch, errorDetail } from './client';

export interface PostTarget {
  slug: string;
  name: string;
  audience: number | null;
  already_mounted: boolean;
  blocked: string | null;
}

export interface PostPreview {
  board: string;
  targets: PostTarget[];
  ok: boolean;
}

export interface PostResult {
  board: string;
  name: string;
  mounted: boolean;
  already: boolean;
}

let boardOnce: Promise<string | null> | null = null;
const waiting: ((p: Promise<string | null>) => void)[] = [];

/** 앱 머리(AppHeader)가 RA 권한이 있는 사람에게 한 탭에 한 번 미리 묻는다 — 결과 카드는 그리면서 포털에 묻지 않는다(docs/wda-deck WD-D78). */
export function prefetchPostBoard(): void {
  if (!boardOnce) {
    const p = apiFetch('/agent/ra/post-target')
      .then((r) => (r.ok ? (r.json() as Promise<{ board?: unknown }>) : null))
      .then((j) => (j && typeof j.board === 'string' && j.board ? j.board : null))
      .catch(() => null);
    boardOnce = p;
    waiting.splice(0).forEach((f) => f(p));
  }
}

/** 이 박스의 심의 게시판 — 미리 물은 답을 기다린다. 아직 묻기 전이면(첫 화면에서 카드가 앱 머리보다 먼저 그려질 때) 묻기가 시작될 때까지
 *  기다린다 — 스스로 묻지는 않는다. RA 권한이 없거나 정하지 않은 박스는 null(단추를 그리지 않는다). */
export function knownPostBoard(): Promise<string | null> {
  if (boardOnce) return boardOnce;
  return new Promise((resolve) => {
    waiting.push((p) => void p.then(resolve));
  });
}

async function readJson<T>(res: Response, fallback: string): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(errorDetail((err as { detail?: unknown }).detail, `${fallback} (${res.status})`));
  }
  return (await res.json()) as T;
}

/** 올리면 어디에 몇 명에게 보이는지 — 실제로 게시하지 않는다. */
export async function previewPost(reportId: number): Promise<PostPreview> {
  return readJson(await apiFetch(`/agent/ra/reports/${reportId}/post-preview`), '게시 미리보기를 받지 못했습니다');
}

/** 사람이 미리보기를 보고 확인한 뒤 — 이 박스의 시스템 공간에 게시한다. */
export async function postReport(reportId: number): Promise<PostResult> {
  return readJson(await apiFetch(`/agent/ra/reports/${reportId}/post`, { method: 'POST' }), '게시하지 못했습니다');
}
