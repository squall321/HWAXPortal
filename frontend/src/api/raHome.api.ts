// 챗 첫 화면의 '내 부서' — 그 사람의 Report Archive 홈 부서와 그 위 사슬(그룹 › 파트)을 포털에 묻는다(docs/ra-chat RC-2 ~ RC-6)
import { apiFetch } from './client';

export interface RaNode {
  slug: string;
  name: string;
  kind: string;
}

/** 홈 부서와 위 사슬 — chain 은 위에서 아래로, 끝이 홈. 못 받으면(연결 없음 · 홈 없음 · RA 실패) home 이 null 이다. */
export interface RaHome {
  home: RaNode | null;
  chain?: RaNode[];
  reason?: string;
}

let once: Promise<RaHome | null> | null = null;

/** 한 탭에 한 번만 묻는다 — 첫 화면은 / 로 올 때마다 다시 그려지므로 그때마다 RA 를 두 번 부르지 않는다(RC-6). 못 받으면 null. */
export function fetchRaHome(): Promise<RaHome | null> {
  if (!once) {
    once = apiFetch('/agent/ra/home')
      .then((r) => (r.ok ? (r.json() as Promise<RaHome>) : null))
      .catch(() => null);
  }
  return once;
}
