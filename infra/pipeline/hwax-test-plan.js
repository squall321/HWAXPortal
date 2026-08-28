// HWAX 시험 계획 심의 — "무엇을 먼저 측정할 것인가" 를 정해 시험 계획서를 낸다.
//
// 입력(args): { question, context, personas, rounds, saveReport, saveConversation, humanNote }
//   - question   : 확보하려는 물성·성능(예: "낙하·충격 해석용 물성 확보")
//   - context    : (선택) 물성 근거 현황. 안 주면 이 워크플로가 MaterialTwin 도구로 직접 조회한다.
//   - personas   : (선택) 추가 좌석. 고정 3석 뒤에 붙는다. 안 주면 고정 3석 + 자동 발굴.
//   - deliberateScript: 자식으로 부를 심의 워크플로 경로(기본 'infra/pipeline/hwax-deliberate.js').
//                  ⚠ 스크립트 안의 workflow() 는 이름으로 .claude/workflows/ 를 못 찾는다 —
//                  내장 워크플로만 이름 해석된다(실측). 그래서 경로로 부른다.
//   - 나머지는 hwax-deliberate 와 동일(rounds 기본 3, saveReport 기본 true).
//
// 왜 별도 워크플로인가 — 챗의 /시험계획 과 **같은 계약**을 MCP 쪽에도 두기 위해서다.
// 예전에는 hwax-deliberate 의 question 에 9항목 계약을 손으로 밀어 넣어 우회했는데,
// 그러면 계약이 호출자마다 달라지고 (3)·(9) 강제가 조용히 빠진다. 계약은 한 곳에 둔다.
//
// 좌석을 고정하는 이유 — 하나씩 빠질 때 나오는 실패가 분명하다.
//   계측이 빠지면 → 측정할 수 없는 것을 계획에 넣는다
//   해석이 빠지면 → 결과에 영향 없는 물성을 최우선으로 올린다
//   일정이 빠지면 → 전부 1순위인 목록이 나온다
export const meta = {
  name: 'hwax-test-plan',
  description: '물성·성능을 어떤 시험으로 언제 확보할지 — 근거 현황 조회 후 다중 라운드 심의로 시험 계획서 9항목 생성',
  whenToUse: '해석에 필요한 물성이 없거나 근거가 약해 "무엇을 먼저 측정할지" 를 정해야 할 때',
  phases: [
    { title: '근거조회', detail: '물성 DB 보유·공백·출처 등급 실조회' },
    { title: '심의', detail: 'hwax-deliberate 를 test-plan 계약으로 실행' },
  ],
}

const A = args || {}
const QUESTION = String(A.question || '').trim()
if (!QUESTION) throw new Error('args.question 이 필요하다 — 확보하려는 물성·성능을 적을 것')

// 챗(deliberation.py _TEST_FIXED)과 같은 고정 좌석. 순서까지 맞춘다.
const FIXED_SEATS = [
  { key: 'rel-test-measurement', role: '계측·시험 — 측정 가능성, 장비·규격, 시편 준비, 산포와 반복성', origin: 'primary' },
  { key: 'xd-cae-modeling', role: 'CAE 모델링 — 해석 결과가 어떤 물성에 민감한가, 어떤 정밀도가 필요한가', origin: 'primary' },
  { key: 'xd-program', role: '프로그램·일정·자원 — 시험 자원 배정, 임계경로, 개발 일정과의 정합', origin: 'primary' },
  { key: 'xd-model-correlation', role: 'sim↔test 상관 — 이 시험이 어떤 해석을 무슨 물리량·조건·수용임계로 검증하는지 계약한다', origin: 'primary' },
  { key: 'rel-reliability-stats', role: '통계·신뢰성 — 표본 수·검정력·산포, 측정 불확실 예산으로 시험을 설계된 실험으로 만든다', origin: 'primary' },
]

// 챗과 동일한 구속 조항. 매 라운드 [인간 검토자 의견]으로 주입돼 무시할 수 없다.
const BASE_NOTE =
  '이미 실측이 있는 항목을 다시 측정 대상으로 올리지 마라. ' +
  "우선순위는 '민감도 × 근거 공백 × 확보 난이도' 로 서열화하고, " +
  '하나만 먼저 한다면 무엇인지 반드시 답하라. ' +
  '경시·수명 항목은 결과까지 수개월이 걸리므로 착수 순서에서 앞에 두라. ' +
  '각 시험은 어떤 해석(sim)을 무슨 물리량·조건·수용임계로 검증하는지 상관 계약을 밝혀라 — ' +
  '대조 대상이 없는 시험은 무엇을 확인하는지 불명이다. ' +
  '표본 수는 산포·요구 검정력에서 근거를 대라 — 장비가 그 물리량의 요구 분해능·불확실을 내는지도 함께 판정하라.'

// ── 1) 물성 근거 현황 ────────────────────────────────────────────────────────
// 계획서의 값어치는 '이미 있는 것을 다시 재지 않는 것' 과 '없는 것을 놓치지 않는 것'
// 양쪽에서 나온다. 둘 다 보유 현황을 봐야 판단되므로 코드가 먼저 깐다.
// context 를 호출자가 주면 그걸 쓰고(중복 조회 회피), 없으면 여기서 조회한다.
let evidence = String(A.context || '').trim()
if (!evidence) {
  phase('근거조회')
  evidence = await agent(
    `MaterialTwin 도구로 아래 목적에 걸리는 물성 근거 현황을 조회해 요약하라. 목적: ${QUESTION}\n\n` +
    `호출할 것(있는 것만, 실패는 건너뛴다):\n` +
    `- database_summary — 물성 DB 전체 현황\n` +
    `- coverage_gaps — 요구 대비 공백(미보유·근거 부족). 시험 후보 목록의 1차 입력이다\n` +
    `- property_distribution — 출처 등급 분포. '채움률은 높은데 실측이 낮은' 상태를 드러낸다\n` +
    `- list_materials(query=목적 키워드, limit=5) — 질문에 걸리는 재료의 보유 물성(중복 측정 방지 근거)\n` +
    `- list_property_definitions — 물성 항목 정의(있으면)\n\n` +
    `출력은 '[물성 근거 현황]' 으로 시작하는 텍스트 요약. 숫자는 조회값을 그대로 쓰고 추정하지 마라.\n` +
    `도구가 하나도 없으면 "물성 근거 현황: 조회 불가(MaterialTwin 도구 없음)" 한 줄만 반환하라.`,
    { label: 'evidence:물성근거', phase: '근거조회' })
}

// ── 2) 심의 ─────────────────────────────────────────────────────────────────
phase('심의')
const personas = [...FIXED_SEATS, ...(Array.isArray(A.personas) ? A.personas : [])]

const DELIB = { scriptPath: A.deliberateScript || 'infra/pipeline/hwax-deliberate.js' }
const result = await workflow(DELIB, {
  question: `아래 목적을 위한 시험 계획 — 어떤 물성을 어떤 시험으로 언제 확보할 것인가. 목적: ${QUESTION}`,
  context: evidence,
  personas,
  rounds: A.rounds ?? 3,
  chairTemplate: 'test-plan',
  humanNote: [BASE_NOTE, String(A.humanNote || '').trim()].filter(Boolean).join('\n\n'),
  saveReport: A.saveReport,
  saveConversation: A.saveConversation,
})

return { ...result, mode: 'test-plan', evidence }
