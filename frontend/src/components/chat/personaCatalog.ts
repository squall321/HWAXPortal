// 전문가 풀을 도메인 → 그룹 → 사람으로 접는 분류기 — 조직도 뷰와 빠른 선택기가 함께 쓴다
import type { PoolExpert } from '../../api/chat.api';

/** 도메인 코드 → 사람이 읽는 이름.
 *
 *  ⚠ AIDataHub `list_agent_domains` 는 **코드와 인원만** 준다(라벨 정본이 없다). 그래서
 *  여기서 붙인다. 모르는 코드는 코드 그대로 보여 준다 — 새 도메인이 생겨도 화면은 안 깨지고
 *  이름만 코드로 나온다. 코드는 키의 첫 세그먼트다(`sh-imu` → `sh`). */
const DOMAIN_LABEL: Record<string, string> = {
  sw: '소프트웨어·플랫폼',
  xd: '업무·프로세스(교차 도메인)',
  sim: '시뮬레이션·해석',
  cam: '카메라',
  rel: '신뢰성',
  soc: 'AP·SoC·패키지',
  disp: '디스플레이',
  mech: '기구·구조',
  pcb: '기판(PCB)',
  rf: '무선(RF)',
  passive: '수동부품',
  pwr: '전원·배터리',
  sh: '센서·음향',
  mem: '메모리·스토리지',
  std: '표준·규격',
  oss: '오픈소스',
  misc: '규제·안전',
  material: '소재',
  market: '시장',
  mx: 'MX 백서',
  kooremapper: 'KooRemapper',
  dynaforge: 'DynaForge',
};

export const domainLabel = (code: string) => DOMAIN_LABEL[code] ?? code;

/** 키의 첫 세그먼트 = 도메인. 세그먼트가 없으면 '기타'로 모은다. */
export const domainOf = (key: string) => key.split('-')[0] || '기타';

export interface GroupNode {
  /** 키의 둘째 세그먼트. 묶이지 않은 사람들은 '' (개별)로 모인다. */
  code: string;
  agents: PoolExpert[];
}
export interface DomainNode {
  code: string;
  label: string;
  agents: PoolExpert[];
  groups: GroupNode[];
}

/** 둘째 세그먼트로 묶되 **2명 이상일 때만** 그룹으로 세운다.
 *  1명짜리 그룹을 다 세우면 sw(408명)에서 그룹이 150개가 되어 조직도가 아니라 목록이 된다. */
export function groupsOf(agents: PoolExpert[]): GroupNode[] {
  const by = new Map<string, PoolExpert[]>();
  for (const a of agents) {
    const seg = a.key.split('-')[1] ?? '';
    const list = by.get(seg);
    if (list) list.push(a);
    else by.set(seg, [a]);
  }
  const groups: GroupNode[] = [];
  const loose: PoolExpert[] = [];
  for (const [code, list] of by) {
    if (code && list.length >= 2) groups.push({ code, agents: list });
    else loose.push(...list);
  }
  groups.sort((a, b) => b.agents.length - a.agents.length || a.code.localeCompare(b.code));
  if (loose.length) {
    loose.sort((a, b) => a.key.localeCompare(b.key));
    groups.push({ code: '', agents: loose });
  }
  return groups;
}

/** 전체 풀 → 도메인 트리(인원 많은 순). */
export function buildTree(pool: PoolExpert[]): DomainNode[] {
  const by = new Map<string, PoolExpert[]>();
  for (const a of pool) {
    const d = domainOf(a.key);
    const list = by.get(d);
    if (list) list.push(a);
    else by.set(d, [a]);
  }
  return [...by.entries()]
    .map(([code, agents]) => ({
      code,
      label: domainLabel(code),
      agents: agents.sort((a, b) => a.key.localeCompare(b.key)),
      groups: groupsOf(agents),
    }))
    .sort((a, b) => b.agents.length - a.agents.length || a.code.localeCompare(b.code));
}

/** 검색 — 이름·키·태그를 모두 본다. 사람 이름이 한글이라 키만 보면 거의 안 걸린다. */
export function matches(a: PoolExpert, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return false;
  if (a.name.toLowerCase().includes(needle)) return true;
  if (a.key.toLowerCase().includes(needle)) return true;
  return (a.tags ?? []).some((t) => t.toLowerCase().includes(needle));
}
