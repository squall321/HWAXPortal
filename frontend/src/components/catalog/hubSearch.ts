// 앱 검색에 HEAX 허브 앱을 함께 — 게이트웨이 앱 목록(/auth/access/apps)에서 허브 앱만 골라 검색어로 거른다(수정 제안서 F4)
import type { HubApp } from '../../api/access.api';

export interface HubHit extends HubApp {
  /** 허브 앱 id(매니페스트 id) — 허브 화면 /heax-hub/apps/<id> 로 연다. */
  slug: string;
}

/** 허브 앱 — 게이트웨이 키 heax-<허브 앱 id>. 쓸 수 있는 것만(allowed), 지금 게이트웨이에 있는 것만(absent 아님),
 *  이미 포털 타일로 있는 앱(hwax-risk 처럼 id 의 _ 를 - 로 바꾼 것이 타일 id)은 타일 쪽에 맡긴다. 검색어는 이름 · 설명 · id 에서 찾는다. */
export function hubMatches(apps: HubApp[], tileIds: Set<string>, q: string): HubHit[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return [];
  return apps
    .filter((a) => a.app.startsWith('heax-') && a.allowed && !a.absent)
    .map((a) => ({ ...a, slug: a.app.slice('heax-'.length) }))
    .filter((a) => !tileIds.has(a.slug.replace(/_/g, '-')))
    .filter((a) => [a.label, a.description, a.slug].some((t) => (t ?? '').toLowerCase().includes(needle)));
}
