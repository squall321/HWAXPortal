// 포털 업데이트 이력 조회 — 로그인 팝업이 '아직 안 본 것'만 받아온다
import { apiFetch } from './client';

export interface ChangelogEntry {
  /** ISO 날짜(YYYY-MM-DD). */
  date: string;
  title: string;
  /** 배지 문구(챗·심의·연결·배포·수정 등). 비어 있을 수 있다. */
  tag: string;
  items: string[];
}

export interface ChangelogResponse {
  /** **전체**의 최신 날짜. 화면은 이걸 '봤다'고 저장한다(받아온 항목의 최신이 아니다 —
   *  limit 이나 분류에 걸려 잘렸을 때도 다음에 같은 것이 또 뜨지 않게). */
  latest: string;
  /** 서버 기준 오늘. 사용자 시계가 틀려도 "오늘의 업데이트" 판정이 흔들리지 않는다. */
  today: string;
  /** 실제로 쓰인 분류만. 화면의 필터 칩을 이걸로 만든다(안 쓰는 칩을 내밀지 않는다). */
  tags?: string[];
  /** 거른 기준의 총수. `entries.length` 가 아니라 이것으로 '더 보기'를 판정한다. */
  total?: number;
  has_more?: boolean;
  entries: ChangelogEntry[];
}

export interface ChangelogQuery {
  /** 이 날짜 이후만(팝업 전용). 이력 페이지는 쓰지 않는다. */
  since?: string;
  tag?: string;
  offset?: number;
  limit?: number;
}

const EMPTY: ChangelogResponse = { latest: '', today: '', tags: [], total: 0, has_more: false, entries: [] };

/** 이력을 받아온다. 실패는 빈 결과 — 안내가 못 뜨는 것이 화면을 막을 이유는 없다.
 *  ⚠ 실패와 '새 것이 없음'이 같은 모양이다. 이력 페이지는 그 둘을 구분해야 하므로
 *  `ok` 를 함께 준다 — 팝업은 어느 쪽이든 안 뜨면 되므로 무시한다. */
export async function fetchChangelog(q: ChangelogQuery = {}): Promise<ChangelogResponse & { ok: boolean }> {
  try {
    const p = new URLSearchParams();
    if (q.since) p.set('since', q.since);
    if (q.tag) p.set('tag', q.tag);
    if (q.offset) p.set('offset', String(q.offset));
    if (q.limit) p.set('limit', String(q.limit));
    const qs = p.toString();
    const res = await apiFetch(`/changelog${qs ? `?${qs}` : ''}`);
    if (!res.ok) return { ...EMPTY, ok: false };
    return { ...EMPTY, ...((await res.json()) as ChangelogResponse), ok: true };
  } catch {
    return { ...EMPTY, ok: false };
  }
}
