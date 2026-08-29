// 심의 방법 택소노미 — Jobs(1층)·Modifiers(2층) 단일 정본. docs/deliberation-quality/method-menu/decision-table.md 와 정합.
// 방법론은 엔진으로 숨기고 사람은 상황으로 고른다. 산출은 언제나 결정 문서(계획·판정·규명), 실행이 아니다.

export type JobId =
  | 'diagnosis'
  | 'option-select'
  | 'credibility'
  | 'sim-plan'
  | 'test-plan'
  | 'build-plan'
  | 'default';

export interface Job {
  id: JobId; // chair_template 키
  name: string; // 상황 헤드라인(크게)
  engine: string; // 방법론 서브텍스트(작게)
  when: string; // 언제 — 사용자 상황
  out: string; // 산출 — 결과 문서
}

// 순서 = 메뉴 노출 순서. diagnosis→option-select→credibility(신규 3) → sim/test/build(기존) → default.
export const JOBS: Job[] = [
  { id: 'diagnosis', name: '원인 규명', engine: 'FTA↔FMEA', when: '원인 불명 · 특정 로트/조건만 · HW+SW+공정 얽힘', out: '지배원인 후보 · cut set · 미지영역' },
  { id: 'option-select', name: '안 선택', engine: 'Pugh · Flip', when: '안이 2개+ · 트레이드오프로 못 정할 때', out: '선택안 · 하이브리드안 · 뒤집힘 임계' },
  { id: 'credibility', name: '신뢰 판정', engine: 'NASA-7009 · red-team', when: '이 해석/결정 믿어도 되나 · go/no-go', out: '신뢰도 채점 · 생존/기각' },
  { id: 'sim-plan', name: '해석 설계', engine: 'sim-plan', when: '이 물리를 무엇으로 어떻게 계산할지', out: '해석 계획서 · sim_spec' },
  { id: 'test-plan', name: '시험 설계', engine: 'test-plan', when: '무엇을 어떤 시험으로 언제 확보할지', out: '시험 계획서 · 상관 계약' },
  { id: 'build-plan', name: '구축 계획', engine: 'build-plan', when: '같은 해석을 형상·조건 바꿔 여러 번 돌릴 때', out: '구축 계획서 · P1~P4 게이트' },
  { id: 'default', name: '자유 심의', engine: '적대 패널', when: '위에 안 맞음 · 보고서 통째로 심의', out: '의사결정문' },
];

export const JOB_BY_ID: Record<JobId, Job> = JOBS.reduce(
  (m, j) => ((m[j.id] = j), m),
  {} as Record<JobId, Job>,
);

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
