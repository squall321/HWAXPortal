// 조직도 탐색 상태 훅 — 루트→분류→도메인→그룹·검색(챗 조직도·심의 좌석 조직도 공용)
import { useMemo, useState } from 'react';
import type { PoolExpert } from '../../api/chat.api';
import { buildOrgTree, findDomain, matches, pathOf, type CategoryNode } from './personaCatalog';

/** 그룹 코드 '' 는 '묶이지 않은 사람들' 이다(2명 미만이라 그룹을 안 세운 것). */
export const groupLabel = (code: string) => (code ? code : '개별');

/** 조직도 탐색 상태 — 두 브라우저가 같은 규칙으로 움직이게 한곳에 둔다.
 *  선택 경로는 분류(cat) → 도메인(dom) → 그룹(grp). 검색어가 있으면 경로보다 검색이 이긴다. */
export function useOrgNav(pool: PoolExpert[]) {
  const [q, setQ] = useState('');
  const [cat, setCat] = useState<string | null>(null);
  const [dom, setDom] = useState<string | null>(null);
  const [grp, setGrp] = useState<string | null>(null);
  const [openDoms, setOpenDoms] = useState<string[]>([]);
  const [closedCats, setClosedCats] = useState<string[]>([]);

  const tree = useMemo(() => buildOrgTree(pool), [pool]);
  const hits = useMemo(() => (q.trim() ? pool.filter((a) => matches(a, q)).slice(0, 120) : []), [pool, q]);
  const node = useMemo(() => findDomain(tree, dom), [tree, dom]);
  const catNode: CategoryNode | undefined = useMemo(() => {
    for (const r of tree) for (const c of r.categories) if (c.id === cat) return c;
    return undefined;
  }, [tree, cat]);
  const shown = useMemo(() => {
    if (q.trim()) return hits;
    if (!node) return [];
    if (grp === null) return node.agents;
    return node.groups.find((g) => g.code === grp)?.agents ?? [];
  }, [q, hits, node, grp]);
  const domainCount = useMemo(() => tree.reduce((s, r) => s + r.categories.reduce((t, c) => t + c.domains.length, 0), 0), [tree]);

  const reset = () => {
    setQ('');
    setCat(null);
    setDom(null);
    setGrp(null);
  };
  const gotoCategory = (c: CategoryNode) => {
    setQ('');
    // 도메인이 하나뿐인 분류(HE팀·앱 지식 분석가)는 한 단계 건너 곧장 사람들로 — 빈 층을 누르게 하지 않는다.
    if (c.domains.length === 1) {
      gotoDomain(c.domains[0].code);
      return;
    }
    setCat(c.id);
    setDom(null);
    setGrp(null);
  };
  const gotoDomain = (code: string) => {
    setQ('');
    setDom(code);
    setGrp(null);
    const p = pathOf(tree, code);
    setCat(p.cat?.id ?? null);
    setOpenDoms((prev) => (prev.includes(code) ? prev : [...prev, code]));
  };
  const toggleDom = (code: string) =>
    setOpenDoms((prev) => (prev.includes(code) ? prev.filter((x) => x !== code) : [...prev, code]));
  const toggleCat = (id: string) =>
    setClosedCats((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  return {
    q, setQ, cat, dom, grp, setGrp, tree, hits, node, catNode, shown, domainCount,
    openDoms, closedCats, reset, gotoCategory, gotoDomain, toggleDom, toggleCat, setCat, setDom,
  };
}
export type OrgNav = ReturnType<typeof useOrgNav>;

