// HWAX 시뮬레이션 심의 — 메커니즘을 먼저 좁히고, 그 위에서 CAE 가 해석을 설계하는 2단 심의
//
// 왜 2단인가: 기존 심의는 "원인이 무엇인가"에서 끝난다. 그런데 원인 가설이 서면 다음 질문은
// 항상 "그래서 그걸 어떻게 계산으로 확인하고 무엇을 설계 인자로 돌릴 것인가"이고, 지금은 그
// 전환을 사람이 매번 손으로 한다. 이 워크플로가 그 절반을 맡는다.
//
// 입력(args): { question, context, personas, rounds, simRounds, carryOver, saveReport, saveConversation, humanNote }
//   - question        : 현상·문제(1단 메커니즘 심의의 화두)
//   - context         : 정량 근거·관측(1단에 실린다. 2단은 1단 결론을 받는다)
//   - personas        : [{key, role, origin?}] 1단 좌석. 주 도메인 + 반대 도메인 1~2 를 포함할 것
//                       (좌석 계약은 hwax-deliberate.js 헤더 참조 — 지키지 않으면 결정문에 커버리지 한계로 남는다)
//   - rounds          : 1단 라운드 수(기본 3)
//   - simRounds       : 2단 라운드 수(기본 3)
//   - carryOver       : 2단에 남길 물리 유임 좌석 수(기본 2, 0~4)
//   - simPersonas     : [{key, role}] 2단 CAE 좌석을 호출자가 직접 지정(선택). 주면 내부 발굴을 건너뛴다.
//                       세션에 게이트웨이 MCP 가 연결되지 않아 좌석 발굴 에이전트가 recommend_agents 에
//                       닿지 못하는 환경을 위한 우회로다. 고정 CAE 좌석과 물리 유임은 그대로 붙는다.
//   - spine           : 2단에 수치 스파인 고정 착석(기본 true). false 면 종전대로 modeling·post 만.
//   - spineReview     : 스파인 리뷰어 2석(rigor-review·theory-grounding) 착석(기본 true, spine=true 일 때).
//                       false 면 핵심 3석(formulation·discretization·verification)만 고정한다.
//   - humanNote       : 1단에 주입할 사람 의견
//   - deliberateScript: 자식으로 부를 심의 워크플로 경로(기본 'infra/pipeline/hwax-deliberate.js').
//                       스크립트 안의 workflow() 는 이름으로 .claude/workflows/ 를 찾지 못한다 —
//                       내장 워크플로(deep-research·code-review)만 이름으로 해석된다(실측 2026-08-07).
//                       그래서 경로로 부른다. 정본을 직접 가리키므로 레지스트리 사본 동기화에도 무관하다.
// 출력: { question, mechanism:{decision, rounds}, seats, simPlan:{decision, rounds}, report, conversation }
//
// 좌석 설계가 이 워크플로의 핵심이다. CAE 전문가만 모으면 틀린 물리를 아름답게 계산한다.
// 그래서 2단 좌석을 넷으로 나눈다 — 고정 방법론 2석(modeling·post) + 수치 스파인 5석
// (formulation·discretization·verification 이 방법을 세우고 rigor-review·theory-grounding 이
// 가로질러 반증·근거요구, 현상과 무관하게 필요), 발굴 CAE 2~3석(1단 결론의 물리 축으로),
// 물리 유임 1~2석(해석이 물리에서 떠나는 것을 막는 감시자).
export const meta = {
  name: 'hwax-sim-deliberate',
  description: '메커니즘 심의 → CAE 해석 설계 심의 2단으로 해석 계획서까지 만든다',
  whenToUse: '현상의 원인을 좁힌 뒤 "그걸 어떤 시뮬레이션으로, 무슨 도구로 확인할 것인가"까지 결정해야 할 때',
  phases: [
    { title: '메커니즘', detail: '현상 도메인 전문가가 지배 물리를 좁힌다' },
    { title: '좌석전환', detail: 'CAE 좌석 발굴 + 물리 유임자 선별' },
    { title: '해석설계', detail: 'CAE 전문가가 해석 계획서를 만든다' },
    { title: '종합', detail: '메커니즘과 계획서를 하나로 잇는다' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const Q = A.question || '(질문 미지정)'
const CTX = A.context || ''
const PERS = A.personas || []
if (!PERS.length) throw new Error('personas 가 비어 있음 — 1단 좌석을 호출자가 발굴해 전달해야 함')
const R1 = Math.min(8, Math.max(2, Math.round(Number(A.rounds) || 3)))
const R2 = Math.min(8, Math.max(2, Math.round(Number(A.simRounds) || 3)))
const CARRY = Math.min(4, Math.max(0, Math.round(Number(A.carryOver) ?? 2)))

// 고정 좌석 — 현상과 무관하게 구축형 해석 설계에 항상 필요한 방법론 축. 발굴에 맡기면 현상
// 어휘에 끌려 이 좌석들이 빠진다. 방법론 2석(modeling·post)에 더해 수치 스파인을 고정한다 —
// 정식화→이산화→검증이 방법을 세우고, 리뷰어 2석이 가로질러 반증·근거요구한다
// (roster-gap-numerical-spine.md §3). 스파인은 recommend_agents 발굴로는 축당 1명·최대 3석이라
// 세트로 착석할 수 없으므로 고정 티어에 넣는다. 역할 텍스트가 각 좌석의 렌즈를 발언 턴에 전한다.
// spine:false → 스파인 전체 제외(종전 modeling·post 만), spineReview:false → 리뷰어 2석만 제외.
const FIXED_ROLES = {
  'xd-cae-modeling': 'CAE 전처리·모델 구성(메시·경계·하중) 방법론',
  'xd-cae-post': 'CAE 후처리·결과 검증·지표 추출 방법론',
  'xd-cae-formulation': '정식화·약형·well-posedness — 지배방정식을 정당한 약형으로 세운다',
  'xd-cae-discretization': '이산화 이론 — 요소·스킴·수렴차수·안정성',
  'xd-cae-verification': '코드검증·수렴차수(MMS·GCI) — 방정식을 올바로 푸는지의 정식 검증',
  'xd-cae-rigor-review': '수치 엄밀성 적대 리뷰어(레드팀) — 정식화·이산화·검증을 반증만, 구축은 안 한다',
  'xd-cae-theory-grounding': '이론·문헌 grounding 챌린저 — 방법 주장에 출처·인용을 요구한다',
}
const SPINE_CORE = ['xd-cae-formulation', 'xd-cae-discretization', 'xd-cae-verification']
const SPINE_REVIEW = ['xd-cae-rigor-review', 'xd-cae-theory-grounding']
const useSpine = A.spine !== false
const useReview = useSpine && A.spineReview !== false
// 발굴 제외·중복 제거·자동 착석에 쓰는 고정 좌석 전체 목록
const FIXED_CAE = ['xd-cae-modeling', 'xd-cae-post',
  ...(useSpine ? SPINE_CORE : []), ...(useReview ? SPINE_REVIEW : [])]

const dom = k => (String(k).includes('-') ? String(k).split('-')[0] : String(k))
const DELIB = { scriptPath: A.deliberateScript || 'infra/pipeline/hwax-deliberate.js' }

// ── 1단 — 메커니즘 심의 ──────────────────────────────────────────────────────
phase('메커니즘')
log(`1단 메커니즘 심의 — 좌석 ${PERS.length}인, ${R1}라운드`)
const mech = await workflow(DELIB, {
  question: Q,
  context: CTX,
  personas: PERS,
  rounds: R1,
  humanNote: A.humanNote || '',
  chairTemplate: 'mechanism',
  saveReport: false,       // 최종 저장은 2단 종료 후 한 번만 — 중간 산출물로 RA 를 어지럽히지 않는다
  saveConversation: false,
})
if (!mech || !mech.decision) throw new Error('1단 메커니즘 심의가 결정문을 내지 못했다 — 2단 입력이 없다')

// 1단의 양보 불가 조항 — 2단이 물리 제약을 조용히 버리지 못하게 승계한다.
const mechFinal = (mech.rounds && mech.rounds[mech.rounds.length - 1]) || []
const NN = mechFinal.filter(Boolean).map(o => o.non_negotiable).filter(Boolean).slice(0, 12)

// ── 좌석 전환 ────────────────────────────────────────────────────────────────
phase('좌석전환')
const SEAT_SCHEMA = {
  type: 'object',
  properties: {
    axes: { type: 'array', items: { type: 'string' }, description: '메커니즘에서 뽑은 해석 물리 축(짧은 명사구)' },
    cae_seats: { type: 'array', items: { type: 'string' }, description: '발굴한 CAE 전문가 키' },
    carry_seats: { type: 'array', items: { type: 'string' }, description: '2단에 남길 1단 참여자 키' },
    reason: { type: 'string', description: '이 구성을 고른 이유' },
  },
  required: ['axes', 'cae_seats', 'carry_seats', 'reason'],
}
// 호출자가 2단 CAE 좌석을 직접 주면 발굴을 건너뛴다 — hwax-deliberate 의 "좌석은 호출자가
// 발굴해 전달" 계약과 같은 취급이다. 안 주면 메커니즘 결론을 읽고 워크플로가 발굴한다.
const GIVEN = (A.simPersonas || []).filter(x => x && x.key)
const seatPick = GIVEN.length
  ? { axes: ['(호출자 지정)'], cae_seats: GIVEN.map(x => x.key), carry_seats: [],
      reason: '호출자가 2단 CAE 좌석을 직접 지정해 발굴을 건너뛰었다.' }
  : await agent(
  `아래 메커니즘 결론을 읽고, 이 물리를 계산으로 확인할 해석 설계 심의의 좌석을 구성하라.\n\n` +
  `[메커니즘 결론]\n${String(mech.decision).slice(0, 6000)}\n\n` +
  `[1단 참여 좌석]\n${PERS.map(p => p.key).join(', ')}\n\n` +
  `순서: (1) 결론에서 해석 물리 축을 2~3개 뽑아라 — '확산 반응 수치해석', '낙하 충격 구조해석' 처럼 ` +
  `전문가 검색에 쓸 짧은 명사구다. 현상 이름이 아니라 계산의 성격을 써라. ` +
  `(2) 각 축으로 recommend_agents 를 호출해 CAE 전문가를 발굴하라. 이미 1단에 앉은 키와 ` +
  `${JSON.stringify(FIXED_CAE)} 는 제외하고, 축당 1명씩 최대 3명을 cae_seats 로 낸다. ` +
  `(3) 1단 참여자 중 메커니즘을 가장 강하게 주장했거나 그 물리를 가장 잘 아는 ${CARRY}명을 ` +
  `carry_seats 로 골라라 — 해석이 물리에서 떠나는 것을 막는 역할이다.\n` +
  `도구를 못 쓰면 cae_seats 는 빈 배열로 두고 reason 에 사유를 적어라. 지어내지 마라.`,
  { label: 'seat-pick', phase: '좌석전환', schema: SEAT_SCHEMA })

const roleOf = k => (GIVEN.find(x => x.key === k) || PERS.find(p => p.key === k) || {}).role || FIXED_ROLES[k] || ''
const seen = new Set()
const simSeats = []
const push = (k, origin) => {
  if (!k || seen.has(k)) return
  seen.add(k)
  simSeats.push({ key: k, role: roleOf(k), origin })
}
FIXED_CAE.forEach(k => push(k, 'new'))
;((seatPick && seatPick.cae_seats) || []).slice(0, 3).forEach(k => push(k, 'new'))
;((seatPick && seatPick.carry_seats) || []).slice(0, CARRY).forEach(k => push(k, 'carry'))
// 유임이 하나도 안 잡히면 1단 좌석 앞에서 채운다 — 물리 감시자 없는 해석 설계를 막는다.
if (!simSeats.some(s => s.origin === 'carry')) {
  PERS.slice(0, Math.max(1, CARRY)).forEach(p => push(p.key, 'carry'))
}
const carryN = simSeats.filter(s => s.origin === 'carry').length
const fixedN = simSeats.filter(s => FIXED_CAE.includes(s.key)).length
log(`2단 좌석 ${simSeats.length}인 (고정 ${fixedN}${useSpine ? ` [수치 스파인 ${useReview ? SPINE_CORE.length + SPINE_REVIEW.length : SPINE_CORE.length}석 포함]` : ''} · ` +
    `발굴 ${simSeats.length - fixedN - carryN} · 물리 유임 ${carryN}) · ` +
    `도메인 ${[...new Set(simSeats.map(s => dom(s.key)))].length}종 · 축: ${((seatPick && seatPick.axes) || []).join(' / ')}`)

// ── 2단 — 해석 설계 심의 ─────────────────────────────────────────────────────
phase('해석설계')
const simQ = `위 메커니즘을 계산으로 확인하고 설계 인자로 돌리기 위한 해석 설계 — 무엇을 어떤 도구로 계산할 것인가. 원 현상: ${Q}`
const sim = await workflow(DELIB, {
  question: simQ,
  context: `[원 현상의 정량 근거]\n${CTX}`,
  personas: simSeats,
  rounds: R2,
  chairTemplate: 'sim-plan',
  continueFrom: { summary: String(mech.decision).slice(0, 12000), roundsSoFar: R1, nonNegotiables: NN },
  humanNote: '사내 보유 도구를 우선 검토하라. 파라미터 식별성 판정과 이 해석이 답할 수 없는 것을 비워두지 마라.',
  saveReport: A.saveReport !== false,
  saveConversation: A.saveConversation !== false,
  appendToReportId: A.appendToReportId,
})

phase('종합')
log(`완료 — 메커니즘 ${R1}라운드 + 해석 설계 ${R2}라운드`)
return {
  question: Q,
  mechanism: { decision: mech.decision, rounds: mech.rounds, roundLabels: mech.roundLabels },
  seats: { axes: (seatPick && seatPick.axes) || [], reason: (seatPick && seatPick.reason) || '',
           sim: simSeats, carriedNonNegotiables: NN },
  simPlan: { decision: sim && sim.decision, rounds: sim && sim.rounds, roundLabels: sim && sim.roundLabels },
  report: sim && sim.report,
  conversation: sim && sim.conversation,
}
