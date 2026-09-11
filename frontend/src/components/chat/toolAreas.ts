// 도구 영역 목록 유도 — 서버 areas 우선, 구 서버면 도구의 area 칸으로 재구성(분류를 지어내지 않는다)
import type { ToolArea } from '../../types/chat';

type WithArea = { area?: string; area_label?: string };

/** 서버가 areas 를 주면 그대로 쓴다(순서·설명이 붙어 온다). 없으면 도구들의 area 로 세되,
 *  **영역이 붙은 도구가 하나도 없으면 [] 이다** — 그때 칩을 그리면 '미분류 462' 한 칸뿐인
 *  쓸모없는 줄이 생긴다. 구 게이트웨이와 붙어 있다는 뜻이라 종전 앱 필터만 쓴다. */
export function toolAreasOf(all: WithArea[], given?: ToolArea[]): ToolArea[] {
  if (given?.length) return given;
  if (!all.some((t) => t.area)) return [];
  const m = new Map<string, ToolArea>();
  for (const t of all) {
    const k = t.area || '';
    const cur = m.get(k);
    if (cur) cur.tool_count += 1;
    else m.set(k, { area: k, label: k ? t.area_label || k : '미분류', tool_count: 1 });
  }
  const out = [...m.values()].filter((a) => a.area);
  const none = m.get('');
  return none ? [...out, none] : out;
}

/** 영역 필터 — null 이면 통과, '' 이면 미분류만. */
export const inArea = (t: WithArea, area: string | null) => area === null || (t.area || '') === area;

export const toolAreaHint = (area: string) =>
  area ? '' : '영역 분류표(게이트웨이 tool_areas.json)에 아직 없는 도구';
