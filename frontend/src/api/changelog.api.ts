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
   *  limit 에 걸려 잘렸을 때도 다음에 같은 것이 또 뜨지 않게). */
  latest: string;
  /** 서버 기준 오늘. 사용자 시계가 틀려도 "오늘의 업데이트" 판정이 흔들리지 않는다. */
  today: string;
  entries: ChangelogEntry[];
}

const EMPTY: ChangelogResponse = { latest: '', today: '', entries: [] };

/** 이력을 받아온다. 실패는 빈 결과 — 업데이트 안내가 못 뜨는 것이 화면을 막을 이유는 없다. */
export async function fetchChangelog(since?: string): Promise<ChangelogResponse> {
  try {
    const qs = since ? `?since=${encodeURIComponent(since)}` : '';
    const res = await apiFetch(`/changelog${qs}`);
    if (!res.ok) return EMPTY;
    return (await res.json()) as ChangelogResponse;
  } catch {
    return EMPTY;
  }
}
