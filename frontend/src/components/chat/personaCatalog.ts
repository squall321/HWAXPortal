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
  he: 'HE팀',
};

export const domainLabel = (code: string) => DOMAIN_LABEL[code] ?? code;

/** HE팀 묶음(키 둘째 세그먼트, he-<묶음>-<앱>) 라벨. 정본은 infra/personas/he-team.json 의 groups 이고
 *  backend/tests/test_he_personas.py 가 두 곳을 대조한다 — 한쪽만 고치면 조직도에 코드가 그대로 뜬다. */
export const HE_GROUP_LABEL: Record<string, string> = {
  cad: '설계 데이터(CAD·ECAD)',
  sim: '시뮬레이션·해석 결과',
  calc: '해석 계산·물성',
  data: '데이터 허브·VOC',
  doc: '보고서·문서·발표',
  research: '웹·논문 조사',
  expert: '심의·리스크',
};

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

/** 검색 — 이름·키·태그를 모두 본다. 사람 이름이 한글이라 키만 보면 거의 안 걸린다. */
export function matches(a: PoolExpert, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return false;
  if (a.name.toLowerCase().includes(needle)) return true;
  if (a.key.toLowerCase().includes(needle)) return true;
  return (a.tags ?? []).some((t) => t.toLowerCase().includes(needle));
}

// ── 조직도 계층 — 루트 → 분류 → 도메인 → 그룹 → 사람 ─────────────────────────────
// 사용자 요청(2026-09-11): '전문 지식 에이전트' 아래 스마트폰 HW·SW 지식, 별도 '플랫폼 에이전트'(그 안에
// HE팀). 도메인 코드는 키 첫 세그먼트 그대로이고, 여기서는 그걸 어느 분류에 둘지만 정한다.
// ⚠ 표에 없는 도메인은 **미분류**로 보인다 — 한 줄이 빠졌다고 사람이 조직도에서 사라지면 안 된다.
export interface CategoryNode {
  id: string;
  label: string;
  domains: DomainNode[];
  count: number;
}
export interface RootNode {
  id: string;
  label: string;
  categories: CategoryNode[];
  count: number;
}

const ROOTS: { id: string; label: string }[] = [
  { id: 'knowledge', label: '전문 지식 에이전트' },
  { id: 'platform', label: '플랫폼 에이전트' },
  { id: 'other', label: '미분류' },
];

// 분류 순서·도메인 순서가 곧 화면 순서다(인원순으로 섞지 않는다 — 조직도는 설계된 계보다).
const CATEGORIES: { id: string; root: string; label: string; domains: string[] }[] = [
  { id: 'hw', root: 'knowledge', label: '스마트폰 HW 지식',
    domains: ['rel', 'disp', 'mech', 'cam', 'soc', 'pcb', 'rf', 'passive', 'pwr', 'sh', 'mem', 'sim'] },
  { id: 'sw', root: 'knowledge', label: '스마트폰 SW 지식', domains: [] },   // SW 는 아래 규칙으로 하위 영역을 만든다
  { id: 'common', root: 'knowledge', label: '공통·업무 지식', domains: ['xd', 'std', 'misc', 'oss'] },
  { id: 'he', root: 'platform', label: 'HE팀 — MCP 도구 전문가', domains: ['he'] },
  { id: 'apps', root: 'platform', label: '앱 지식 분석가', domains: ['apps'] },
];

// 앱 지식 분석가 — 앱마다 1~2명이라 도메인 5개로 쪼개면 조직도가 부스러기가 된다. 한 도메인으로
// 모으고 앱 이름을 그룹으로 쓴다(material-twin-analyst 등, 지식카드로 답하는 분석가들).
const APP_ANALYST_DOMAINS = new Set(['material', 'mx', 'market', 'kooremapper', 'dynaforge']);

// ── 스마트폰 SW 하위 영역 — sw 408명은 둘째 세그먼트가 분류가 아니다(57개 소그룹 + 1명짜리 205명).
// 키의 토큰을 앞에서부터 보고 처음 걸리는 영역에 둔다. 모호한 키만 전체 키로 덮어쓴다.
const SW_AREAS: { code: string; label: string; tokens: string[] }[] = [
  { code: 'app', label: '앱·UX', tokens: ['app', 'widget', 'launcher', 'systemui', 'quick', 'lockscreen',
    'notification', 'theme', 'aod', 'ime', 'browser', 'webview', 'wallet', 'payment', 'health', 'smartthings',
    'home', 'matter', 'game', 'dex', 'pc', 'buds', 'wearable', 'automotive', 'tablet', 'crossdevice',
    'multidevice', 'nearby', 'clipboard', 'accessibility', 'screenreader', 'gesture', 'account', 'multiuser',
    'work', 'parental', 'emergency', 'find', 'context', 'night', 'animation', 'backup'] },
  { code: 'camera', label: '카메라·이미징', tokens: ['camera', 'computational', 'portrait', 'image', 'super',
    'led'] },
  { code: 'media', label: '미디어·그래픽·디스플레이', tokens: ['video', 'media', 'streaming', 'cast', 'drm',
    'av', 'screen', 'hwc', 'hwui', 'skia', 'opengl', 'vulkan', 'gpu', 'graphics', 'rendering', 'surfaceflinger',
    'frame', 'jank', 'color', 'display', 'brightness', 'multidisplay', 'refresh', 'gallery'] },
  { code: 'audio', label: '오디오·음성·햅틱', tokens: ['audio', 'anc', 'beamforming', 'echo', 'noise', 'spatial',
    'speaker', 'voice', 'wakeword', 'speech', 'haptic'] },
  { code: 'conn', label: '연결성·통신', tokens: ['bt', 'wifi', 'nfc', 'uwb', 'gnss', 'location', 'geofencing',
    'network', 'dns', 'vpn', 'tethering', 'cellular', 'dualsim', 'esim', 'sim', 'carrier', 'ims', 'volte', 'vowifi',
    'rcs', 'sms', 'cell', 'roaming', 'ril', 'modem', 'ntn', 'radio', 'coexistence', 'telephony', 'call',
    'connectivity', 'push'] },
  { code: 'sys', label: '시스템·커널·BSP', tokens: ['linux', 'kernel', 'binder', 'process', 'virtual', 'memory',
    'block', 'file', 'ufs', 'storage', 'init', 'boot', 'bsp', 'sensor', 'sensorhub', 'input', 'touch', 'usb',
    'art', 'native', 'npu', 'system', 'package', 'mainline', 'job', 'timekeeping', 'watchdog', 'recovery',
    'virtualization', 'container', 'window', 'resource', 'firmware', 'interrupt'] },
  { code: 'power', label: '전력·열·성능', tokens: ['power', 'background', 'battery', 'dvfs', 'thermal',
    'sustained', 'performance', 'anr', 'profiler', 'charging', 'pmic', 'fuelgauge'] },
  { code: 'sec', label: '보안·프라이버시', tokens: ['security', 'secure', 'selinux', 'tee', 'keystore', 'verified',
    'antirollback', 'code', 'mobile', 'biometric', 'face', 'fingerprint', 'identity', 'authorization',
    'credential', 'permission', 'privacy', 'fuzzing'] },
  { code: 'ai', label: 'AI·데이터', tokens: ['ai', 'llm', 'ondevice', 'multimodal', 'vision', 'translation',
    'personalization', 'recommendation', 'ranking', 'rag', 'federated', 'private', 'model', 'nlp', 'data',
    'causal', 'product', 'funnel', 'retention', 'experiment', 'insight', 'kpi', 'telemetry', 'voc', 'event',
    'observability', 'log', 'generative'] },
  { code: 'dev', label: '개발·빌드·품질', tokens: ['build', 'ci', 'release', 'branch', 'source', 'dependency',
    'reproducible', 'variant', 'config', 'remote', 'regression', 'compatibility', 'integration', 'unit', 'test',
    'api', 'developer', 'sample', 'public', 'debug', 'lowlevel', 'static', 'crash', 'defect', 'emulator',
    'quality', 'field', 'longterm', 'service', 'backend', 'search', 'cloud', 'platform', 'ota', 'rollback'] },
  { code: 'reg', label: '지역화·규제', tokens: ['localization', 'internationalization', 'language', 'locale',
    'region', 'regional', 'legal', 'export', 'content', 'open', 'sustainability'] },
];
// 첫 토큰이 두 영역에 걸치는 키 — 전체 키로 정한다.
const SW_OVERRIDE: Record<string, string> = {
  'hdr-imaging': 'camera', 'hdr-display': 'media', 'data-call': 'conn', 'enterprise-network': 'conn',
  'enterprise-mdm': 'sec', 'device-integrity': 'sec', 'device-tree': 'sys', 'device-control': 'app',
  'device-discovery': 'conn', 'device-farm': 'dev', 'device-registration': 'sys', 'kernel-security': 'sec',
  'kernel-locking': 'sys', 'network-security': 'sec', 'cloud-security': 'sec', 'data-encryption': 'sec',
  'data-minimization': 'sec', 'ui-responsiveness': 'power', 'ui-automation': 'dev', 'feature-store': 'ai',
  'feature-flag': 'dev', 'feature-adoption': 'ai', 'user-segmentation': 'ai', 'user-profile': 'app',
  'ab-testing': 'ai', 'ab-update': 'dev', 'foldable-ux': 'app', 'foldable-display': 'media',
  'digital-key': 'app', 'digital-market-compliance': 'reg', 'privacy-regulation': 'reg',
  'carrier-regulation': 'reg', 'call-message-continuity': 'app', 'secure-display': 'sec',
  'radio-power': 'power', 'privacy-analytics': 'ai', 'open-source-compliance': 'reg',
  'memory-training-fw': 'sys', 'charging-fw': 'power', 'usb-pd-fw': 'power', 'search-backend': 'dev',
  'app-performance': 'power', 'app-security': 'sec', 'app-camera': 'camera', 'app-gallery': 'media',
  'camera-app-integration': 'camera', 'bt-audio': 'conn', 'sensor-hal': 'sys',
};
const SW_LABEL = Object.fromEntries(SW_AREAS.map((a) => [a.code, a.label]));
const SW_TOKEN = new Map<string, string>();
for (const a of SW_AREAS) for (const t of a.tokens) if (!SW_TOKEN.has(t)) SW_TOKEN.set(t, a.code);

/** sw 키의 하위 영역 코드. 규칙에 안 걸리면 'etc'(기타 SW) — 숨기지 않는다. */
export function swAreaOf(key: string): string {
  const rest = key.startsWith('sw-') ? key.slice(3) : key;
  if (SW_OVERRIDE[rest]) return SW_OVERRIDE[rest];
  for (const t of rest.split('-')) {
    const a = SW_TOKEN.get(t);
    if (a) return a;
  }
  return 'etc';
}

/** 사람 한 명의 자리 — 조직도 도메인 코드·라벨과 그룹 코드. */
function placeOf(key: string): { dom: string; label: string; group: string } {
  const segs = key.split('-');
  const first = segs[0] || '기타';
  if (first === 'sw') {
    const area = swAreaOf(key);
    return { dom: `sw.${area}`, label: SW_LABEL[area] ?? '기타 SW', group: segs[1] ?? '' };
  }
  if (APP_ANALYST_DOMAINS.has(first)) return { dom: 'apps', label: '앱 지식 분석가', group: first };
  return { dom: first, label: domainLabel(first), group: segs[1] ?? '' };
}

/** 도메인 노드(그룹 포함) — placeOf 로 자리를 정한 뒤 묶는다. 그룹은 **2명 이상일 때만** 세운다 —
 *  1명짜리 그룹을 다 세우면 큰 도메인에서 그룹이 150개가 되어 조직도가 아니라 목록이 된다. */
function domainNodes(pool: PoolExpert[]): DomainNode[] {
  const by = new Map<string, { label: string; agents: PoolExpert[]; groupOf: Map<string, string> }>();
  for (const a of pool) {
    const p = placeOf(a.key);
    let n = by.get(p.dom);
    if (!n) by.set(p.dom, (n = { label: p.label, agents: [], groupOf: new Map() }));
    n.agents.push(a);
    n.groupOf.set(a.key, p.group);
  }
  const out: DomainNode[] = [];
  for (const [code, n] of by) {
    const g = new Map<string, PoolExpert[]>();
    for (const a of n.agents) {
      const k = n.groupOf.get(a.key) ?? '';
      const list = g.get(k);
      if (list) list.push(a);
      else g.set(k, [a]);
    }
    const groups: GroupNode[] = [];
    const loose: PoolExpert[] = [];
    for (const [gc, list] of g) {
      if (gc && list.length >= 2) groups.push({ code: gc, agents: list.sort((x, y) => x.key.localeCompare(y.key)) });
      else loose.push(...list);
    }
    groups.sort((x, y) => y.agents.length - x.agents.length || x.code.localeCompare(y.code));
    if (loose.length) groups.push({ code: '', agents: loose.sort((x, y) => x.key.localeCompare(y.key)) });
    out.push({ code, label: n.label, agents: n.agents.sort((x, y) => x.key.localeCompare(y.key)), groups });
  }
  return out;
}

/** 전체 풀 → 루트/분류/도메인 트리. 빈 분류·빈 루트는 싣지 않는다. */
export function buildOrgTree(pool: PoolExpert[]): RootNode[] {
  const doms = domainNodes(pool);
  const byCode = new Map(doms.map((d) => [d.code, d]));
  const used = new Set<string>();
  const cats: (CategoryNode & { root: string })[] = [];
  for (const c of CATEGORIES) {
    let list: DomainNode[];
    if (c.id === 'sw') {
      // SW 하위 영역은 SW_AREAS 순서 + 기타 SW 를 끝에.
      list = [...SW_AREAS.map((a) => `sw.${a.code}`), 'sw.etc'].map((k) => byCode.get(k)).filter(Boolean) as DomainNode[];
    } else {
      list = c.domains.map((k) => byCode.get(k)).filter(Boolean) as DomainNode[];
    }
    list.forEach((d) => used.add(d.code));
    if (list.length) cats.push({ id: c.id, root: c.root, label: c.label, domains: list, count: list.reduce((s, d) => s + d.agents.length, 0) });
  }
  const rest = doms.filter((d) => !used.has(d.code)).sort((a, b) => b.agents.length - a.agents.length);
  if (rest.length) {
    cats.push({ id: 'unmapped', root: 'other', label: '분류표에 없는 분야', domains: rest,
      count: rest.reduce((s, d) => s + d.agents.length, 0) });
  }
  return ROOTS.map((r) => {
    const categories: CategoryNode[] = cats
      .filter((c) => c.root === r.id)
      .map((c) => ({ id: c.id, label: c.label, domains: c.domains, count: c.count }));
    return { id: r.id, label: r.label, categories, count: categories.reduce((s, c) => s + c.count, 0) };
  }).filter((r) => r.categories.length);
}

/** 조직도 트리에서 도메인 하나 찾기(코드로). */
export function findDomain(tree: RootNode[], code: string | null): DomainNode | undefined {
  if (!code) return undefined;
  for (const r of tree) for (const c of r.categories) for (const d of c.domains) if (d.code === code) return d;
  return undefined;
}

/** 도메인이 속한 [루트, 분류] — 빵부스러기용. */
export function pathOf(tree: RootNode[], code: string | null): { root?: RootNode; cat?: CategoryNode } {
  if (!code) return {};
  for (const r of tree) for (const c of r.categories) if (c.domains.some((d) => d.code === code)) return { root: r, cat: c };
  return {};
}
