// 심의 방법 택소노미 — Jobs(1층)·Modifiers(2층)·그룹·라우팅 단일 정본.
// docs/deliberation-quality/method-menu/decision-table.md 와 정합. 방법론은 엔진으로 숨기고 사람은 상황으로 고른다.
// 산출은 언제나 결정 문서(계획·판정·규명), 실행이 아니다. 두 화면(브리프·심의 랜딩)이 이 파일만 소비한다.

export type JobId =
  | 'diagnosis'
  | 'option-select'
  | 'credibility'
  | 'sim-plan'
  | 'test-plan'
  | 'build-plan'
  | 'default';

// 산출물 성격으로 묶는다 — judge(이미 있는 것에 대한 결론) / plan(앞으로 할 일의 계획서) / free(catch-all).
export type JobGroupId = 'judge' | 'plan' | 'free';

export interface Job {
  id: JobId; // chair_template 키
  group: JobGroupId;
  name: string; // 상황 헤드라인(크게)
  engine: string; // 방법론 서브텍스트(작게)
  when: string; // 언제 — 사용자 상황
  out: string; // 산출 — 결과 문서
  note: string; // 이 심의가 무엇을 하는지 한 줄(선택 시 힌트로 노출)
  placeholder: string; // 입력창 플레이스홀더
}

// 순서 = 메뉴 노출 순서(그룹 내). judge 3 → plan 3 → free 1.
export const JOBS: Job[] = [
  { id: 'diagnosis', group: 'judge', name: '원인 규명', engine: 'FTA↔FMEA', when: '원인 불명 · 특정 로트/조건만 · HW+SW+공정 얽힘', out: '지배원인 후보 · cut set · 미지영역', note: '증거 위에서 지배원인을 좁힙니다 — 조치가 아니라 원인·미지영역까지가 산출입니다.', placeholder: '불량 현상을 입력하세요…' },
  { id: 'option-select', group: 'judge', name: '안 선택', engine: 'Pugh · Flip', when: '안이 2개+ · 트레이드오프로 못 정할 때', out: '선택안 · 하이브리드안 · 뒤집힘 임계', note: '기준·가중을 먼저 합의하고 Pugh 2라운드로 고릅니다 — 뒤집힘 임계까지.', placeholder: '비교할 안들과 결정 문제를 입력하세요…' },
  { id: 'credibility', group: 'judge', name: '신뢰 판정', engine: 'NASA-7009 · red-team', when: '이 해석/결정 믿어도 되나 · go/no-go', out: '신뢰도 채점 · 생존/기각', note: 'NASA-7009 축별로 신뢰도를 채점하고 red-team 지정석이 결론을 깨봅니다.', placeholder: '판정할 해석·결정을 입력하세요…' },
  { id: 'sim-plan', group: 'plan', name: '해석 설계', engine: 'sim-plan', when: '이 물리를 무엇으로 어떻게 계산할지', out: '해석 계획서 · sim_spec', note: '메커니즘을 먼저 좁히고 그 위에서 CAE 가 해석을 설계하는 2단 심의입니다.', placeholder: '계산으로 풀 현상을 입력하세요…' },
  { id: 'test-plan', group: 'plan', name: '시험 설계', engine: 'test-plan', when: '무엇을 어떤 시험으로 언제 확보할지', out: '시험 계획서 · 상관 계약', note: '계측·CAE·프로그램 전문가가 고정 착석해 무엇을 먼저 측정할지 계획합니다.', placeholder: '확보하려는 물성·성능을 입력하세요…' },
  { id: 'build-plan', group: 'plan', name: '구축 계획', engine: 'build-plan', when: '같은 해석을 형상·조건 바꿔 여러 번 돌릴 때', out: '구축 계획서 · P1~P4 게이트', note: '메커니즘→해석 계획을 거쳐 반복 파라메트릭 모듈 구축 계획서까지 3단으로 냅니다(P1~P4).', placeholder: '반복해서 돌릴 해석을 입력하세요…' },
  { id: 'default', group: 'free', name: '자유 심의', engine: '적대 패널', when: '위에 안 맞음 · 보고서 통째로 심의', out: '의사결정문', note: '관련 전문가들이 여러 라운드로 자유롭게 심의합니다.', placeholder: '화두를 입력하세요…' },
];

export const JOB_BY_ID: Record<JobId, Job> = JOBS.reduce(
  (m, j) => ((m[j.id] = j), m),
  {} as Record<JobId, Job>,
);

export interface JobGroup {
  id: JobGroupId;
  label: string;
  hint: string;
}

export const JOB_GROUPS: JobGroup[] = [
  { id: 'judge', label: '판단', hint: '무엇이 맞나 · 이미 있는 것에 대한 결론' },
  { id: 'plan', label: '계획', hint: '무엇을 할까 · 앞으로 할 일의 계획서' },
  { id: 'free', label: '자유', hint: '위 틀에 안 맞을 때' },
];

export const jobsByGroup = (g: JobGroupId): Job[] => JOBS.filter((j) => j.group === g);

// 라우팅 — 해석/시험 설계는 기존 다단 트리거(서버가 chair 지정 + 고정 좌석), 나머지는 /심의 + chair_template.
// 다단 경로도 _deliberation_stream 을 타 evidence·modifiers 를 승계하므로, 두 화면이 이 표를 그대로 공유한다.
export interface JobRouting {
  trigger: string;
  chair?: JobId; // 다단 트리거는 서버가 chair 를 세우므로 비운다.
  opts?: Record<string, unknown>; // 추가 delib_opts(예: build_plan). sendMessage 2번째 인자로 병합.
}

export const JOB_ROUTING: Record<JobId, JobRouting> = {
  diagnosis: { trigger: '/심의 ', chair: 'diagnosis' },
  'option-select': { trigger: '/심의 ', chair: 'option-select' },
  credibility: { trigger: '/심의 ', chair: 'credibility' },
  'sim-plan': { trigger: '/시뮬심의 ' },
  'test-plan': { trigger: '/시험계획 ' },
  // 구축 계획은 sim_spec 을 승계해야 하므로 단발이 아니라 시뮬 심의 3단 체인(메커니즘→해석→구축)으로 간다.
  'build-plan': { trigger: '/시뮬심의 ', opts: { build_plan: 1 } },
  default: { trigger: '/심의 ' },
};

export interface Modifier {
  id: string;
  name: string;
  when: string;
}

// 얹을 층 — chairTemplate(무엇을 산출)과 직교하는 "어떻게 굴리나". 여럿 켤 수 있다. 백엔드 화이트리스트와 정합.
export const MODIFIERS: Modifier[] = [
  { id: 'voi', name: '교착 정산 (VoI)', when: '패널이 값으로 못 가르고 막힐 때' },
  { id: 'premortem', name: '사전부검', when: '결정 굳기 전 실패를 미리 막고 싶을 때' },
  { id: 'toulmin', name: '논증 엄밀', when: '주장이 근거 없이 세질 때' },
  { id: 'eliminative', name: '완결 기준', when: '언제 끝인지 모호할 때' },
  { id: 'anon1r', name: '익명 1R', when: '초반 쏠림·거수기 우려' },
];

// 이 대화에서 감지된 신호로 Job 을 제안한다(LLM 아님 — 도구 시그널 휴리스틱). vLLM 복구 후 LLM 추론으로 승격 가능.
// 반환 null 이면 확신 부족 — 메뉴에서 직접 고르게 한다(억지 추천 금지).
export function suggestJob(usedTools: string[]): { id: JobId; why: string } | null {
  const t = usedTools.map((x) => x.toLowerCase());
  const has = (...names: string[]) => t.some((x) => names.some((n) => x.includes(n)));
  if (has('voc', 'top_issues', 'sentiment', 'crisis', 'issue'))
    return { id: 'diagnosis', why: '대화에 불량·VOC 신호가 있어 원인 규명을 제안합니다' };
  if (has('coverage_gap', 'measurement_gap', 'test_plan', 'how_to_measure'))
    return { id: 'test-plan', why: '물성 공백·측정 신호가 있어 시험 설계를 제안합니다' };
  if (has('laminate', 'abd', 'buckling', 'thermal', 'frequenc', 'stress', 'sed', 'warpage', 'material'))
    return { id: 'sim-plan', why: '해석·물성 신호가 있어 해석 설계를 제안합니다' };
  return null;
}
