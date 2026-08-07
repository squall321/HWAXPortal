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
//   - humanNote       : 1단에 주입할 사람 의견
// 출력: { question, mechanism:{decision, rounds}, seats, simPlan:{decision, rounds}, report, conversation }
//
// 좌석 설계가 이 워크플로의 핵심이다. CAE 전문가만 모으면 틀린 물리를 아름답게 계산한다.
// 그래서 2단 좌석을 셋으로 나눈다 — 고정 CAE 2석(방법론·검증은 현상과 무관하게 필요),
// 발굴 CAE 2~3석(1단 결론의 물리 축으로), 물리 유임 1~2석(해석이 물리에서 떠나는 것을 막는 감시자).
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

// 고정 CAE 좌석 — 해석 방법론과 후처리·검증은 어떤 현상이든 필요하다. 발굴에 맡기면
// 현상 어휘에 끌려가 방법론 좌석이 빠지는 일이 생긴다.
const FIXED_CAE = ['xd-cae-modeling', 'xd-cae-post']

const dom = k => (String(k).includes('-') ? String(k).split('-')[0] : String(k))

// ── 1단 — 메커니즘 심의 ──────────────────────────────────────────────────────
phase('메커니즘')
log(`1단 메커니즘 심의 — 좌석 ${PERS.length}인, ${R1}라운드`)
const mech = await workflow('hwax-deliberate', {
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
const seatPick = await agent(
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

const roleOf = k => (PERS.find(p => p.key === k) || {}).role || ''
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
log(`2단 좌석 ${simSeats.length}인 (CAE ${simSeats.length - carryN} · 물리 유임 ${carryN}) · ` +
    `도메인 ${[...new Set(simSeats.map(s => dom(s.key)))].length}종 · 축: ${((seatPick && seatPick.axes) || []).join(' / ')}`)

// ── 2단 — 해석 설계 심의 ─────────────────────────────────────────────────────
phase('해석설계')
const simQ = `위 메커니즘을 계산으로 확인하고 설계 인자로 돌리기 위한 해석 설계 — 무엇을 어떤 도구로 계산할 것인가. 원 현상: ${Q}`
const sim = await workflow('hwax-deliberate', {
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
