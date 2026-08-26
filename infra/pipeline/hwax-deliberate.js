// HWAX 심의 파이프라인 — 재사용 다중 라운드 전문가 심의 워크플로
// 입력(args): { question, context, options, personas:[{key,role}], rounds, saveReport, saveConversation,
//               continueFrom:{summary, roundsSoFar}, humanNote, appendToReportId }
//   - question        : 심의 주제(문자열)
//   - context         : 정량 근거/분석 결과(도구로 산출한 데이터의 텍스트 요약)
//   - options         : 후보/선택지 목록(JSON 문자열 또는 배열)
//   - personas        : [{key, role, origin?}] 참여 전문 페르소나(호출자가 recommend_agents로 발굴해 전달).
//                       origin — 'primary'(주 도메인, 기본) | 'counter'(반대 도메인) | 'carry'(이어하기 유임) |
//                       'new'(이어하기 신규). 결정문이 커버리지를 기록하고, origin:'new' 좌석은 1라운드에서
//                       이전 요약을 받지 않는다(앵커링 차단).
//     [좌석 계약 — 지키지 않으면 결정문에 커버리지 한계로 기록된다]
//       · 신규 심의: 질문으로 뽑은 주 도메인에 더해, 그 좌석들이 못 보는 원인 축을 명명하고 그 축으로 발굴한
//         반대 도메인 좌석 1~2를 반드시 포함할 것. 원 질문에 "이 분야 밖"을 덧붙이는 역질의는 작동하지 않는다 —
//         질의 대부분이 원 질문이라 임베딩 이웃이 그대로 돌아온다(실측: 도메인 확장 0). 짧은 축 질의를 쓸 것.
//       · 이어하기: 이전 좌석 전원 재사용 금지. '원 질문 + 이전 결론 + 사람 의견'이라는 실효 질문으로 재심사해
//         유임(전원) + 신규(다른 도메인 1~2)로 구성할 것. 좌석을 빼지는 말 것 — 그 도메인의 이전 발언에 대한
//         책임 주체가 사라진다.
//   - rounds          : 이번 호출에서 진행할 라운드 수(기본 3 = 초기+심화1+수렴). 최소 2, 최대 8로 클램프.
//   - continueFrom    : 이전 심의를 이어갈 때만 지정. { summary: 이전 심의 요약(결정문+라운드 하이라이트, 호출자가
//                       구성해 전달), roundsSoFar: 이전까지 이미 진행된 라운드 수(라운드 번호 이어붙이기용),
//                       nonNegotiables: [이전 심의의 양보 불가 조항] }.
//                       nonNegotiables 는 요약에 섞지 말고 따로 넘길 것 — 요약 문자열에만 의존하면 조항이
//                       조용히 소실되고 결정이 되돌아간다. 넘기면 매 라운드 구속 조항으로 주입되고, 뒤집으려면
//                       새 근거를 명시하도록 강제된다.
//                       지정 시 1라운드 프롬프트가 "이어하기"로 바뀌고, 라운드 번호가 roundsSoFar+1 부터 시작한다.
//   - humanNote       : 이번 라운드에서 패널이 반드시 정면으로 다뤄야 할 사람(검토자)의 코멘트/질문. 매 라운드
//                       프롬프트에 [인간 검토자 의견]으로 주입되어 무시할 수 없게 만든다.
//   - chairTemplate   : 의장 산출 항목 템플릿. 'default'(기본, 종전과 동일) | 'mechanism'(메커니즘 결론 —
//                       상태변수·지배방정식 후보·미지 파라미터·반증 관측을 뽑아 해석 설계로 넘긴다) |
//                       'sim-plan'(해석 계획서 10항목 — 식별성 판정과 한계를 강제) |
//                       'test-plan'(시험 계획서 9항목 — (3) '하나만 먼저 한다면' 과 (9) 미확보 항목을
//                       비워둘 수 없게 강제. 챗의 /시험계획 과 같은 계약). 시뮬레이션 심의
//                       (hwax-sim-deliberate.js)가 1단/2단에서 각각 지정하고, 시험 계획은
//                       hwax-test-plan.js 가 지정한다.
//   - stopAfterRound  : 1 이면 초기 라운드만 돌고 멈춘다(인간 체크포인트). 결정문·보고서 없이 checkpoint
//                       페이로드를 반환하므로, 사람이 빠진 관점을 보태 continueFrom+humanNote 로 이어하기를
//                       호출하면 그 지점부터 이어진다. 좌석 재심사가 사람이 준 방향에 맞는 도메인을 불러온다.
//   - appendToReportId: 지정 시 새 RA 보고서를 만들지 않고 이 report_id 에 새 페이지로 결과를 이어붙인다.
// 출력: { question, rounds:[페르소나별 라운드결과 배열...], roundLabels, decision, report, conversation, nextRoundOffset }
//   — stopAfterRound:1 이면 decision/report/conversation 이 null 이고 checkpoint{stage,seats,positions,ask} 가 붙는다.
//   — 호출자가 viz_module + Report Archive로 보고서화. nextRoundOffset 은 다음 이어하기 호출의
//   continueFrom.roundsSoFar 로 그대로 넘기면 라운드 번호가 끊기지 않는다.
//
// 설계: 게이트웨이 MCP가 도구(계산·에이전트·RA)를 제공하고, 이 워크플로는 그 위의 "심의 수렴"
//       오케스트레이션을 캡슐화한다. 도메인 도구 실행/페르소나 발굴/시각화는 호출자 몫(도메인별이라).
export const meta = {
  name: 'hwax-deliberate',
  description: '질문+정량근거를 다중 라운드 전문가 심의로 수렴시켜 의사결정문 생성',
  whenToUse: '여러 도메인 전문가의 의견이 갈리는 설계/분석 결정을, 도구 근거 위에서 라운드로 수렴시키고 싶을 때',
  phases: [
    { title: '초기입장', detail: '페르소나별 초기 의견(또는 이어하기 개시) — 병렬' },
    { title: '심화라운드', detail: '상호 반박·수치 심화 (가변 회차, 병렬)' },
    { title: '수렴', detail: '최종 입장·투표 (병렬)' },
    { title: 'Decision', detail: '의사결정문 합성' },
    { title: 'Explain', detail: '비전문가용 쉬운 설명 — 정식 절차' },
  ],
}

// args 는 객체 또는 JSON 문자열로 올 수 있다(런타임 차이 방어).
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const Q = A.question || '(질문 미지정)'
const CTX = A.context || ''
const OPTS = typeof A.options === 'string' ? A.options : JSON.stringify(A.options || [])
// 선택지 개수 — 상호 배타 후보가 2개 미만이면 표결이 성립하지 않는다. 그런데도 vote 를 강제하면
// 자기들이 공동 작성한 실행안을 승인하는 형태가 되어 정보량이 0 이 된다(실측: S26U 경시성
// 이어하기의 vote 6건이 전부 '패키지 채택 찬성'). 그 경우 표결 대신 스탠스를 받는다.
const OPT_LIST = (() => {
  if (Array.isArray(A.options)) return A.options.filter(Boolean)
  try { const x = JSON.parse(A.options || '[]'); return Array.isArray(x) ? x.filter(Boolean) : [] } catch { return [] }
})()
const HAS_CHOICES = OPT_LIST.length >= 2
const PERS = A.personas || []
const pk = PERS.map(p => p.key)
if (!pk.length) throw new Error('personas 가 비어 있음 — 호출자가 recommend_agents 로 발굴해 전달해야 함')

const CONT = A.continueFrom || null           // { summary, roundsSoFar } — 이어하기 모드
const HUMAN_NOTE = A.humanNote || ''          // 인간 검토자 의견(있으면 매 라운드 프롬프트에 강제 주입)
const APPEND_TO = A.appendToReportId ? Number(A.appendToReportId) : null
// 인간 체크포인트 — 1이면 초기 라운드만 돌고 반환한다. 사람이 빠진 관점·추가 관측을 보태
// continueFrom + humanNote 로 이어하기를 부르면 그 지점부터 이어진다. 이번 세션 실측에서
// 가장 큰 품질 개선이 사람의 중간 개입에서 나왔고(관측 3건 추가가 라운드 추가보다 결론을 크게
// 바꿨다), 비용은 거의 0 이다.
const STOP_AFTER = Number(A.stopAfterRound) === 1 ? 1 : 0
// 의장 산출 템플릿 — 시뮬레이션 심의처럼 결정문의 성격이 다른 경우에만 지정한다.
// 미지정이면 종전 항목((1)~(5))이 그대로 나가므로 기존 호출은 영향 없다.
const CHAIR_TEMPLATE = String(A.chairTemplate || 'default')

// 참여 인원수는 personas 배열 길이가 그대로 결정(상한 없음).
// 라운드 수는 이번 호출분만 — 기본 3(초기+심화1+수렴), 2~8 사이로 클램프(런어웨이 비용 방지).
const ROUNDS = Math.min(8, Math.max(2, Math.round(Number(A.rounds) || 3)))
const MID_ROUNDS = ROUNDS - 2   // 초기(1)·수렴(1)을 뺀 중간 심화 라운드 수(0이면 심화 생략, 초기→바로 수렴)
const ROUND_OFFSET = CONT ? Math.max(0, Math.round(Number(CONT.roundsSoFar) || 0)) : 0
const rn = localNo => ROUND_OFFSET + localNo   // 라운드 번호를 이전 회차 이후로 이어붙임

const CONT_BLOCK = CONT ? `[이전 심의 요약 — 지금까지 ${ROUND_OFFSET}라운드 진행됨]\n${CONT.summary}\n\n` : ''
// 양보 불가 조항 승계 — 요약 문자열에만 의존하면 조항이 소실되고 결정이 소리 없이 되돌아간다.
const NN = (CONT && Array.isArray(CONT.nonNegotiables) ? CONT.nonNegotiables : []).filter(Boolean).slice(0, 12)
const NN_BLOCK = NN.length
  ? `[이전 심의의 양보 불가 조항 — 이번 라운드에서도 구속력을 가진다]\n${NN.map(x => `- ${x}`).join('\n')}\n` +
    `이 조항을 뒤집으려면 어떤 새 근거 때문인지 반드시 명시하라. 근거 없는 폐기는 불인정.\n\n`
  : ''
const HUMAN_BLOCK = HUMAN_NOTE ? `[인간 검토자 의견 — 이번 라운드에서 반드시 정면으로 다룰 것]\n${HUMAN_NOTE}\n\n` : ''
const TAIL = `[심의 주제]\n${Q}\n\n[정량 근거·분석 결과]\n${CTX}\n\n[후보/선택지]\n${OPTS}\n`
const BASE = `${CONT_BLOCK}${NN_BLOCK}${HUMAN_BLOCK}${TAIL}`
// 신규 좌석 앵커링 차단 — 이어하기에 새로 합류한 좌석(origin:'new')은 1라운드에서 이전 결론을
// 받지 않는다. 새 관점을 얻으려고 부른 사람이 기존 결론을 먼저 읽으면 동조 압력을 받는다.
const BASE_BLIND = `${NN_BLOCK}${HUMAN_BLOCK}${TAIL}\n[안내] 당신은 이번 회차에 새로 합류했다. ` +
  `이전 논의 결과는 의도적으로 제공하지 않는다 — 먼저 당신 도메인의 독립적 판단을 내라. 다음 라운드에서 이전 결론을 받는다.\n`
const originOf = k => (PERS.find(p => p.key === k) || {}).origin || 'primary'
const baseFor = k => (CONT && originOf(k) === 'new' ? BASE_BLIND : BASE)
// 좌석 구성 — 결정문이 커버리지를 스스로 밝히게 한다.
const SEAT_NOTE = (() => {
  const label = { primary: '주 도메인', counter: '반대 도메인', carry: '유임', new: '이어하기 신규' }
  const by = {}
  pk.forEach(k => { (by[originOf(k)] = by[originOf(k)] || []).push(k) })
  const doms = [...new Set(pk.map(k => (k.includes('-') ? k.split('-')[0] : k)))].sort()
  return `참여 좌석 — ${Object.entries(by).map(([o, ks]) => `${label[o] || o} ${ks.length}명(${ks.join(', ')})`).join(' / ')}. ` +
         `착석 도메인 ${doms.length}종: ${doms.join(', ')}.`
})()
const role = k => (PERS.find(p => p.key === k) || {}).role || k

const OP_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    persona: { type: 'string' },
    lens: { type: 'string', description: '이 주제를 보는 당신의 한 줄 관점' },
    reads: { type: 'array', items: { type: 'string' }, description: '근거 데이터에 대한 도메인 해석(구체 인용)' },
    recommendation: { type: 'string', description: '당신 관점 권장안' },
    concerns: { type: 'array', items: { type: 'string' }, description: '이 근거가 당신 도메인에서 놓치는 것/리스크' },
  },
  required: ['persona', 'lens', 'recommendation', 'concerns'],
}
const R2_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    persona: { type: 'string' },
    concede: { type: 'array', items: { type: 'string' }, description: '타 전문가 지적 중 수용' },
    rebut: { type: 'array', items: { type: 'string' }, description: '반박 + 근거(수치·표준·실패모드)' },
    deepen: { type: 'string', description: '핵심 주장을 한 단계 더 깊게(구체적으로)' },
  },
  required: ['persona', 'concede', 'rebut', 'deepen'],
}
const R3_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    persona: { type: 'string' },
    final_position: { type: 'string' },
    non_negotiable: { type: 'string', description: '절대 양보 못 하는 제약' },
    vote: { type: 'string', description: '최종 권장 선택지 + 이유' },
  },
  required: ['persona', 'final_position', 'vote'],
}

// 라운드별 요약 — idx=0 초기, idx=마지막 수렴, 그 사이는 전부 심화.
// 프롬프트 컨텍스트용(compact — 한 줄 대괄호)과 기록용(readable — 문단 개행)을 구분한다:
// 웹 대화·RA 회의록에서 발언이 개행 없이 한 덩어리로 보이던 문제의 기록측 수정.
const summarize = (isFirst, isLast, o) => {
  if (isFirst) return `관점[${o.lens}] 권장[${o.recommendation}] 우려[${(o.concerns || []).join('; ')}]`
  if (isLast) return `${o.final_position || ''} — 최종권장: ${o.vote || ''}`
  return `수용[${(o.concede || []).join('; ')}] 반박[${(o.rebut || []).join('; ')}] 심화:${o.deepen}`
}
const readable = (isFirst, isLast, o) => {
  const join = v => (Array.isArray(v) ? v.filter(Boolean).join('\n- ') : String(v || ''))
  if (isFirst) {
    const parts = [o.lens, o.recommendation ? `저는 이렇게 봅니다 — ${o.recommendation}` : '',
                   (o.concerns || []).length ? `우려:\n- ${join(o.concerns)}` : '']
    return parts.filter(Boolean).join('\n\n')
  }
  if (isLast) {
    return [o.final_position, o.non_negotiable ? `양보 불가 — ${o.non_negotiable}` : '',
            o.vote ? `최종 권장 — ${o.vote}` : ''].filter(Boolean).join('\n\n')
  }
  const parts = []
  if ((o.concede || []).length) parts.push(`그 지적은 받아들입니다.\n- ${join(o.concede)}`)
  if ((o.rebut || []).length) parts.push(`다만 반박하자면,\n- ${join(o.rebut)}`)
  if (o.deepen) parts.push(`제 핵심은 이겁니다. ${o.deepen}`)
  return parts.join('\n\n')
}

const roundsData = []   // [ [페르소나별 결과...], ... ] — 길이 = ROUNDS
const roundLabels = []  // 회의록용 라운드 제목

phase('초기입장')
const R1_INSTRUCTION = CONT
  ? `이 논의는 이어하기 라운드다. 위 [이전 심의 요약]을 읽어라(당신이 이전에 참여했다면 거기 당신의 이전 입장도 있을 것이다). [인간 검토자 의견]이 있다면 반드시 정면으로 다뤄라. 당신의 도메인 관점에서: (1) 이전 논의·인간 의견에 대한 구체적 반응(동의/반박/보완, 구체 인용), (2) 갱신되었거나 새로 형성한 권장안, (3) 이 시점에 당신 도메인이 놓치고 있는 것/리스크. 수치엔 (도구)/(경험칙) 표기. 영역 밖은 아는 척 금지.`
  : `당신의 도메인 관점에서만: (1) 이 근거가 당신 관심사에 무엇을 의미하는지 구체 인용해 해석, (2) 권장안, (3) 이 분석이 당신 도메인에서 놓치는 것/리스크. 수치엔 (도구)/(경험칙) 표기. 영역 밖은 아는 척 금지.`
// 카드 그라운딩 — 켜지면 각 좌석이 발언 전 자기 지식카드를 조회해 수치·근거의 출처로 삼는다.
// 기본 꺼짐(일반 심의·챗 무변경). sim 심의가 켠다. get_context_bundle/semantic_search 는 RAG
// 색인을 읽으므로 새 카드가 잡히려면 색인이 최신이어야 한다(재색인 절차). 미사용·도구실패 시엔
// 종전과 동일하게 페르소나 지식으로 발언한다 — 가법적이라 회귀 위험이 없다.
const GROUND = A.groundCards === true
const groundBlock = k => GROUND
  ? `[근거 그라운딩 — 발언 전 실행] 먼저 get_context_bundle(agent_type: "${k}") 로 네 지식카드를 ` +
    `불러오고, 필요하면 semantic_search(q: 쟁점, agent_type: "${k}") 로 쟁점 관련 근거를 찾아라. ` +
    `수치·임계·정리를 인용할 땐 카드/섹션 출처를 붙이고, 카드에 없어 일반지식으로 답하면 ` +
    `(경험칙)/(expert-judgement)로 표기하라. 도구가 실패하면 그 사실을 한 줄로 남기고 페르소나 ` +
    `지식으로 답하되 과단정하지 마라.\n\n`
  : ''
// 페르소나 정규화 — LLM이 persona 필드에 긴 역할 설명을 붙여 반환하면 포털 저장(persona ≤120자
// 검증)이 배치째 422로 거부된다(전기박리 심의 대화 유실 사고의 원인). 정본 키로 강제한다.
const withKey = (k) => (o) => (o ? { ...o, persona: k } : o)
const r1 = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${baseFor(k)}\n\n${groundBlock(k)}${R1_INSTRUCTION}`,
  { label: `r${rn(1)}:${k}`, phase: '초기입장', schema: OP_SCHEMA }).then(withKey(k))))
roundsData.push(r1)
roundLabels.push(`${rn(1)}라운드 — ${CONT ? '이어하기·초기입장' : '초기입장'}`)

let priorText = r1.filter(Boolean).map(o => `• ${o.persona}: ${summarize(true, false, o)}`).join('\n')
let priorLabel = `${rn(1)}라운드(초기입장) 전원 입장`
if (STOP_AFTER === 1) {
  log(`체크포인트 — ${rn(1)}라운드까지 진행하고 멈춘다. 사람 검토 후 continueFrom(roundsSoFar=${rn(1)}) + humanNote 로 이어하기를 호출할 것.`)
  return {
    question: Q, rounds: roundsData, roundLabels, decision: null, explain: null,
    report: null, conversation: null, nextRoundOffset: rn(1),
    checkpoint: {
      stage: 'after-initial',
      seats: SEAT_NOTE,
      positions: r1.filter(Boolean).map(o => ({ persona: o.persona, position: o.position_short || o.lens, recommendation: o.recommendation })),
      ask: '빠진 관점이나 추가 관측이 있는가. 있으면 humanNote 로 넣어 이어하기를 호출하라 — 좌석 재심사가 그에 맞는 도메인을 불러온다.',
    },
  }
}
let preFinalText = priorText   // 마지막 심화(또는 심화 없으면 초기) 시점 스냅샷 — RA 'results' 블록용

for (let i = 0; i < MID_ROUNDS; i++) {
  const roundNo = rn(i + 2)
  phase('심화라운드')
  const rN = await parallel(pk.map(k => () => agent(
    `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n[${priorLabel}]\n${priorText}\n\n${groundBlock(k)}` +
    `${roundNo}라운드(심화 ${i + 1}/${MID_ROUNDS}): 다른 전문가 입장을 읽고 (1) 수용할 지적, (2) 반박(근거: 수치·표준·실패모드), (3) 당신 핵심 주장을 한 단계 더 깊게. 두루뭉술 금지, 당신 전문성으로.`,
    { label: `r${roundNo}:${k}`, phase: '심화라운드', schema: R2_SCHEMA }).then(withKey(k))))
  roundsData.push(rN)
  roundLabels.push(`${roundNo}라운드 — 상호 반박·심화`)
  priorText = rN.filter(Boolean).map(o => `• ${o.persona}: ${summarize(false, false, o)}`).join('\n')
  priorLabel = `${roundNo}라운드(심화) 전원 입장`
  preFinalText = priorText
}

phase('수렴')
const finalRoundNo = rn(ROUNDS)
const rFinal = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n[${priorLabel}]\n${priorText}\n\n${groundBlock(k)}` +
  `${finalRoundNo}라운드(최종수렴): 지금까지 논의를 반영해 최종 입장으로 수렴하라. (1) 최종 입장, (2) 절대 양보 못 하는 제약, ` +
  (HAS_CHOICES
    ? `(3) 위 [후보/선택지] 중 최종 권장 하나와 이유. 근거가 부족해 고를 수 없으면 "판정 불가 — 다음에 측정할 것"과 그 측정 항목을 쓰라.`
    : `(3) 형성된 다수 의견에 대한 당신의 스탠스(동의/조건부 동의/반대)와 이유. 상호 배타적 선택지가 제시되지 않았으므로 표결이 아니라 입장 표명이다 — 선택지를 지어내 투표하지 마라.`) +
  ` 결정 가능하도록 구체적으로.`,
  { label: `r${finalRoundNo}:${k}`, phase: '수렴', schema: R3_SCHEMA }).then(withKey(k))))
roundsData.push(rFinal)
roundLabels.push(`${finalRoundNo}라운드 — 수렴·최종 입장`)

phase('Decision')
const allRoundsText = roundsData.map((rd, idx) => {
  const isFirst = idx === 0
  const isLast = idx === roundsData.length - 1
  return `[${roundLabels[idx]}]\n` + rd.filter(Boolean).map(o => `• ${o.persona}: ${summarize(isFirst, isLast, o)}`).join('\n')
}).join('\n\n')

// 산출 항목 — 템플릿별로 다르다. mechanism 은 2단(해석 설계)으로 넘길 것을 뽑고,
// sim-plan 은 해석 계획서를 낸다. 계획서에서 (7) 식별성과 (10) 한계를 강제하는 이유는,
// 이 둘이 '그럴듯한 계획서'와 '실제로 돌릴 수 있는 계획'을 가르기 때문이다 — 파라미터가
// 곱으로 붙어 분리되지 않으면(퇴화) 모델을 세워도 피팅이 닫히지 않는다.
const CHAIR_ITEMS = {
  default:
    `(1) 결정사항(번호매김, 명확·실행가능하게), (2) 합의 근거(라운드를 거치며 어떻게 수렴했는지), (3) 반대/소수의견과 처리, (4) 미해결 쟁점 + 담당·다음 액션, (5) 결정 신뢰도·전제.`,
  mechanism:
    `(1) 메커니즘 결론 — 무엇이 무엇을 어떤 경로로 바꾸는가를 인과 사슬로, (2) 상태변수와 공간·시간 스케일 — 무엇을 추적해야 현상이 기술되는가, (3) 지배방정식 후보 — 형태 수준으로(확산·반응·이동·구조·열 등 어느 계열인지와 결합 관계), (4) 미지 파라미터 목록 — 값을 모르는 물리량과 그 단위·예상 범위, (5) 반증 관측 — 이 메커니즘이 틀렸다면 무엇이 관측되는가, (6) 합의 근거와 반대/소수의견 처리, (7) 신뢰도·전제. 이 결정문은 후속 해석 설계 심의의 입력이 되므로 (2)(3)(4)를 특히 구체적으로 쓰라.`,
  'sim-plan':
    `해석 계획서 10개 항목 — (1) 해석 목적: 이 계산이 답할 질문 하나를 문장으로, (2) 지배방정식과 물리 모델: 위 메커니즘 결론에서 승계해 수식 수준으로 확정, (3) 해석 종류·차원·기하 축약: 3D full / 2D 평면·축대칭 / 1D 중 무엇이며 그 축약이 정당한 이유, (4) 솔버·도구 선택과 근거: 사내 보유 도구를 우선 검토하고 없을 때만 외부 도구, (5) 이산화: 메시 전략·시간 적분·수치 기법과 안정성 조건, (6) 경계·초기조건, (7) 물성·파라미터 확보 경로와 식별성 판정 — 각 파라미터를 문헌/독립 측정/피팅으로 분류하고, 피팅 대상이 둘 이상이면 서로 곱으로 붙어 분리되지 않는지(퇴화) 판정하라. 퇴화가 있으면 그것을 푸는 독립 관측을 지정하라, (8) 검증 계획: 해석해·벤치마크·시험 대조, (9) 계산 규모와 일정, (10) 이 해석이 답할 수 없는 것. (7)과 (10)은 비워두지 마라 — 비면 계획서가 아니다.`,
  'test-plan':
    "시험 계획서 9개 항목 — " +
    "(1) 시험 목적: 이 시험이 풀어야 할 해석·판단을 한 문장으로. 어떤 결정을 막고 있는지 명시, " +
    "(2) 대상 물성과 현재 근거: 필요한 물성을 나열하고 [물성 근거 현황] 과 대조해 각각을 " +
    "실측 보유 / 카탈로그·계열값 / 가정 / 미보유 로 판정하라. 이미 실측이 있는 항목은 " +
    "다시 측정하지 마라 — 중복 측정은 자원 낭비이고 계획서의 신뢰를 깎는다, " +
    "(3) 우선순위와 근거: 해석 결과에 대한 민감도 × 근거 공백 × 확보 난이도로 서열화하라. " +
    "'다 필요하다' 는 답이 아니다. 하나만 먼저 한다면 무엇인지 답하고 그 이유를 쓰라, " +
    "(4) 시험 항목별 방법·장비·규격: 사내 보유 장비를 우선 검토하고, 없으면 외주·신규 도입으로 " +
    "구분하라. 규격이 있으면 규격 번호를 쓰라, " +
    "(5) 조건축 설계: 온도·습도·속도·하중 등 어떤 축을 어느 수준으로 몇 점 잡을지. " +
    "수준 수와 표본 수를 곱해 총 시험 횟수를 명시하라. 전수 조합이 불가하면 어떤 설계로 줄일지, " +
    "(6) 시편과 수량: 형상·전처리·반복 수. 파괴시험이면 소모량까지, " +
    "(7) 일정과 착수 순서: 경시·수명 항목은 결과가 나오는 데 수개월이 걸리므로 먼저 착수하고 " +
    "단기 항목을 병행하라. 무엇이 임계경로인지 명시하라, " +
    "(8) 판정 기준: 어떤 값이 나오면 확보로 보고 어떤 경우 재시험인가. 산포가 크면 어떻게 다룰지, " +
    "(9) 이 시험으로도 확보되지 않는 것: 남는 가정과 그 영향. " +
    "(3)과 (9)는 비워두지 마라 — 비면 우선순위 없는 희망 목록일 뿐이다.",
}

const DECISION_CONT_NOTE = CONT
  ? `\n\n이는 이전 심의(위 [이전 심의 요약] 참조)의 후속 라운드다. 산출 항목에 (6) 이전 결정문과의 관계(보완/수정/신규 쟁점 해소 중 무엇인지 명시)를 반드시 추가하라.`
  : ''
const decision = await agent(
  `당신은 심의체 의장. 이번 호출분 ${ROUNDS}라운드 토론(${rn(1)}~${finalRoundNo}라운드, 초기 1${MID_ROUNDS > 0 ? ` + 심화 ${MID_ROUNDS}` : ''} + 수렴 1)을 종합해 의사결정문을 한국어 엔지니어링 톤으로 작성하라.\n\n${BASE}\n\n` +
  `[전체 라운드 요약]\n${allRoundsText}\n\n[최종 라운드 상세]\n${JSON.stringify(rFinal.filter(Boolean), null, 1)}\n\n` +
  `[${SEAT_NOTE}]\n\n` +
  `산출: ## ${CHAIR_TEMPLATE === 'sim-plan' ? '해석 계획서' : CHAIR_TEMPLATE === 'test-plan' ? '시험 계획서' : '의사결정문'} — (0) 참여 도메인과 커버리지 한계 — 위 좌석 구성을 한 문단으로 기록하고, 이 문제에 관련되나 착석하지 않은 인접 도메인이 있으면 명시하라(없으면 없다고 쓰라), ` +
  `${CHAIR_ITEMS[CHAIR_TEMPLATE] || CHAIR_ITEMS.default} 라운드별 입장 심화·수렴 과정을 반드시 드러내라.${DECISION_CONT_NOTE}`,
  { label: 'decision', phase: 'Decision' })

// 쉬운 설명 — 챗 파이프라인(deliberation.py)과 동일한 정식 심의 절차. 의결 뒤에 붙는다.
// 여기 없으면 MCP 경로 결정문만 비전문가용 정리가 빠져 두 경로가 어긋난다.
phase('Explain')
const plain = await agent(
  `당신은 어려운 기술 결정을 비전문가에게 설명하는 사람이다. 쉬운 말로, 과장 없이.\n\n` +
  `다음 의사결정문을 처음 보는 사람도 이해하게 정리하라. 형식:\n` +
  `### 한마디로\n(무엇을 하라는 것인지 한 문장)\n` +
  `### 왜 그런가\n(핵심 근거 2~3개 — 수치가 있으면 쉬운 말로 풀어서)\n` +
  `### 당장 할 일 / 다음에 할 일 / 하지 말 것\n(각 2~4개 불릿, 전문용어는 괄호로 풀어쓰기)\n` +
  `새로운 내용을 지어내지 말고 원문에 있는 것만 쉽게 바꿔라.\n\n${decision.slice(0, 12000)}`,
  { label: 'explain', phase: 'Explain' })
const decisionFull = plain ? `${decision}\n\n---\n\n■ 쉬운 설명\n${plain}` : decision

// Report Archive 저장 — MCP 경로도 포털 챗과 동일하게 웹(RA)에 보고서를 남긴다.
// (챗 deliberation.py 와 같은 template_id/blocks + 대화체 회의록). saveReport:false 로 끄면
// 반환만 하고 저장 안 함(호출자가 직접 보고서화하고 싶을 때). appendToReportId 가 있으면 새 보고서
// 대신 그 report_id 에 새 페이지로 이어붙인다(get_report 로 현재 페이지 수 확인 → page=마지막+1).
let report = null
if (A.saveReport !== false) {
  phase('Report')
  const minutes = []
  roundsData.forEach((rd, idx) => {
    const isFirst = idx === 0
    const isLast = idx === roundsData.length - 1
    minutes.push(roundLabels[idx])
    rd.filter(Boolean).forEach(o => minutes.push(`[${o.persona}] ${readable(isFirst, isLast, o)}`))
  })
  // 기록 층위 — RA 는 심의의 정본 기록이라 발언·결정문을 문장 중간에서 자르지 않는다.
  // ⚠ RA rich_text 는 **항목당 2000자**가 서버 스키마 상한이다 — 하나라도 넘으면 보고서 전체가
  //   "Content invalid" 로 거절된다. 예전 slice(0, 4000) 은 그 자리에서 저장을 못 하게 만들었다.
  //   그래서 절단이 아니라 **분할**로 푼다(내용을 안 버린다). 결정문 40문단 컷도 없앤다 —
  //   #14/#16 이 컷 때문에 잘려 수동 재작성했던 것과 같은 손실이라서.
  const RA_MAX = 1900
  const raSplit = (s) => {
    s = String(s || '')
    if (s.length <= RA_MAX) return s ? [s] : []
    const out = []
    let buf = ''
    for (let part of s.split(/(?<=[.!?。])\s+|\n/)) {
      if (!part) continue
      if (buf.length + part.length + 1 > RA_MAX) {
        if (buf) { out.push(buf.trim()); buf = '' }
        while (part.length > RA_MAX) { out.push(part.slice(0, RA_MAX)); part = part.slice(RA_MAX) }
      }
      buf = buf ? `${buf}\n${part}` : part
    }
    if (buf.trim()) out.push(buf.trim())
    return out
  }
  const raBlocks = (b) => Object.fromEntries(
    Object.entries(b).map(([k, v]) => [k, v.flatMap(raSplit)]))

  const backgroundBlock = APPEND_TO
    ? [`이어하기 라운드(${rn(1)}~${finalRoundNo}라운드) 주제: ${Q}`, ...(HUMAN_NOTE ? [`인간 검토자 의견:\n${HUMAN_NOTE}`] : [])]
    : [`심의 주제: ${Q}`, ...(CTX ? [`정량 근거·분석:\n${CTX}`] : [])]
  const blocks = raBlocks({
    background: backgroundBlock,
    results: [preFinalText],
    recommendation: String(decisionFull).split('\n\n').map(s => s.trim()).filter(Boolean),
    minutes: [`참여: ${pk.join(', ')}`, `${ROUNDS}라운드 심의(${rn(1)}라운드→${MID_ROUNDS > 0 ? `심화 ${MID_ROUNDS}회→` : ''}${finalRoundNo}라운드 수렴).`, ...minutes],
  })
  // RA 부재/실패는 비치명적 — cae00 는 RA 가 안 떠 있을 수 있다(hands-off). 저장 실패해도
  // 심의 결과(decision·라운드)는 이미 아래 return 에 있으므로 절대 잃지 않는다.
  try {
    const raInstruction = APPEND_TO
      ? `기존 Report Archive 보고서에 이번 심의 결과를 새 페이지로 이어붙여라.\n` +
        `순서: (1) get_report(report_id=${APPEND_TO}) 로 현재 pages 배열 길이를 확인, (2) update_report_draft(report_id=${APPEND_TO}, page=<pages 길이+1>, blocks=${JSON.stringify(blocks)}) 호출.\n` +
        `- report_id 가 없거나(Report Archive 미가용) 실패하면 절대 재시도하지 말고 "RA_UNAVAILABLE" 한 줄만 반환.\n` +
        `- 성공하면 "${APPEND_TO}" 한 줄만 반환(붙인 보고서 번호).`
      : `create_report_draft 도구가 사용 가능하면 호출해 아래 심의 결과를 Report Archive 에 저장하라.\n` +
        `인자: template_id="deliberation", template_version=1, title="심의 — ${Q.slice(0, 50)}",\n` +
        `tags=["심의","mcp-deliberation"], blocks=${JSON.stringify(blocks)}\n` +
        `- 도구가 없거나(Report Archive 미가용) 저장이 실패하면 절대 재시도하지 말고 "RA_UNAVAILABLE" 한 줄만 반환.\n` +
        `- 성공하면 반환된 report.id(보고서 번호)만 한 줄로.`
    report = await agent(raInstruction, { label: 'ra-save', phase: 'Report' })
    if (typeof report === 'string' && /RA_UNAVAILABLE|FAILED|not available|unavailable/i.test(report)) {
      log('Report Archive 미가용 — 저장 건너뜀(심의 결과는 반환됨)')
      report = null
    }
  } catch (e) {
    log(`Report Archive 저장 실패(비치명적): ${String(e).slice(0, 120)}`)
    report = null
  }
}

// 서버 대화 저장 — 심의의 "대화 전개"를 포털 웹 챗에도 남긴다(GLM 이어가기·직접 결론용).
// 게이트웨이 save_conversation 도구가 호출자 PAT 를 포털에 포워딩해 owner 귀속.
// RA 와 동일한 폴백 계약: 미가용이면 건너뛸 뿐, 심의 결과(return)는 절대 잃지 않는다.
let conversation = null
if (A.saveConversation !== false) {
  phase('Report')
  const msgs = [
    { role: 'user', content: `${CONT ? '(이어하기) ' : ''}${Q}${HUMAN_NOTE ? `\n\n[인간 검토자 의견]\n${HUMAN_NOTE}` : ''}${CTX ? `\n\n[정량 근거·분석]\n${CTX.slice(0, 1500)}` : ''}` },
  ]
  roundsData.forEach((rd, idx) => {
    const isFirst = idx === 0
    const isLast = idx === roundsData.length - 1
    rd.filter(Boolean).forEach(o => msgs.push({ role: 'persona', persona: o.persona, round: rn(idx + 1), content: readable(isFirst, isLast, o).slice(0, 2000) }))
  })
  msgs.push({ role: 'assistant', content: String(decisionFull).slice(0, 24000) })
  try {
    conversation = await agent(
      `save_conversation 도구가 사용 가능하면 호출해 아래 심의 대화 로그를 포털 대화 저장소에 저장하라.\n` +
      `인자: title="${CONT ? '심의(이어하기) — ' : '심의 — '}${Q.slice(0, 50)}", kind="deliberation", source="mcp",\n` +
      `messages=${JSON.stringify(msgs)}\n` +
      `- 도구가 없거나 결과가 CONV_UNAVAILABLE 이면 절대 재시도하지 말고 "CONV_UNAVAILABLE" 한 줄만 반환.\n` +
      `- 성공하면 반환된 conversation_id 만 한 줄로.`,
      { label: 'conv-save', phase: 'Report' })
    if (typeof conversation === 'string' && /CONV_UNAVAILABLE|FAILED|not available|unavailable/i.test(conversation)) {
      log('포털 대화 저장소 미가용 — 저장 건너뜀(심의 결과는 반환됨)')
      conversation = null
    }
  } catch (e) {
    log(`대화 저장 실패(비치명적): ${String(e).slice(0, 120)}`)
    conversation = null
  }
}

return {
  question: Q,
  rounds: roundsData.map(rd => rd.filter(Boolean)),
  roundLabels,
  decision: decisionFull,
  plain,
  report,
  conversation,
  nextRoundOffset: finalRoundNo,   // 다음 이어하기 호출의 continueFrom.roundsSoFar 로 그대로 전달
}
