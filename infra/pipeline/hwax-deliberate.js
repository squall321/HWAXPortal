// HWAX 심의 파이프라인 — 재사용 다중 라운드 전문가 심의 워크플로
// 입력(args): { question, context, options, personas:[{key,role}], rounds, saveReport, saveConversation,
//               continueFrom:{summary, roundsSoFar}, humanNote, appendToReportId }
//   - question        : 심의 주제(문자열)
//   - context         : 정량 근거/분석 결과(도구로 산출한 데이터의 텍스트 요약)
//   - options         : 후보/선택지 목록(JSON 문자열 또는 배열)
//   - personas        : [{key, role}] 참여 전문 페르소나(호출자가 recommend_agents로 발굴해 전달, 인원수 자유).
//                       이어하기 라운드에서는 이전 패널 그대로/일부만/신규 전문가 추가 등 자유 구성 — 새로 합류한
//                       페르소나도 continueFrom.summary 를 읽고 자연스럽게 합류하도록 프롬프트가 처리한다.
//   - rounds          : 이번 호출에서 진행할 라운드 수(기본 3 = 초기+심화1+수렴). 최소 2, 최대 8로 클램프.
//   - continueFrom    : 이전 심의를 이어갈 때만 지정. { summary: 이전 심의 요약(결정문+라운드 하이라이트, 호출자가
//                       구성해 전달), roundsSoFar: 이전까지 이미 진행된 라운드 수(라운드 번호 이어붙이기용) }.
//                       지정 시 1라운드 프롬프트가 "이어하기"로 바뀌고, 라운드 번호가 roundsSoFar+1 부터 시작한다.
//   - humanNote       : 이번 라운드에서 패널이 반드시 정면으로 다뤄야 할 사람(검토자)의 코멘트/질문. 매 라운드
//                       프롬프트에 [인간 검토자 의견]으로 주입되어 무시할 수 없게 만든다.
//   - appendToReportId: 지정 시 새 RA 보고서를 만들지 않고 이 report_id 에 새 페이지로 결과를 이어붙인다.
// 출력: { question, rounds:[페르소나별 라운드결과 배열...], roundLabels, decision, report, conversation, nextRoundOffset }
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
  ],
}

// args 는 객체 또는 JSON 문자열로 올 수 있다(런타임 차이 방어).
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const Q = A.question || '(질문 미지정)'
const CTX = A.context || ''
const OPTS = typeof A.options === 'string' ? A.options : JSON.stringify(A.options || [])
const PERS = A.personas || []
const pk = PERS.map(p => p.key)
if (!pk.length) throw new Error('personas 가 비어 있음 — 호출자가 recommend_agents 로 발굴해 전달해야 함')

const CONT = A.continueFrom || null           // { summary, roundsSoFar } — 이어하기 모드
const HUMAN_NOTE = A.humanNote || ''          // 인간 검토자 의견(있으면 매 라운드 프롬프트에 강제 주입)
const APPEND_TO = A.appendToReportId ? Number(A.appendToReportId) : null

// 참여 인원수는 personas 배열 길이가 그대로 결정(상한 없음).
// 라운드 수는 이번 호출분만 — 기본 3(초기+심화1+수렴), 2~8 사이로 클램프(런어웨이 비용 방지).
const ROUNDS = Math.min(8, Math.max(2, Math.round(Number(A.rounds) || 3)))
const MID_ROUNDS = ROUNDS - 2   // 초기(1)·수렴(1)을 뺀 중간 심화 라운드 수(0이면 심화 생략, 초기→바로 수렴)
const ROUND_OFFSET = CONT ? Math.max(0, Math.round(Number(CONT.roundsSoFar) || 0)) : 0
const rn = localNo => ROUND_OFFSET + localNo   // 라운드 번호를 이전 회차 이후로 이어붙임

const CONT_BLOCK = CONT ? `[이전 심의 요약 — 지금까지 ${ROUND_OFFSET}라운드 진행됨]\n${CONT.summary}\n\n` : ''
const HUMAN_BLOCK = HUMAN_NOTE ? `[인간 검토자 의견 — 이번 라운드에서 반드시 정면으로 다룰 것]\n${HUMAN_NOTE}\n\n` : ''
const BASE = `${CONT_BLOCK}${HUMAN_BLOCK}[심의 주제]\n${Q}\n\n[정량 근거·분석 결과]\n${CTX}\n\n[후보/선택지]\n${OPTS}\n`
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
const r1 = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n${R1_INSTRUCTION}`,
  { label: `r${rn(1)}:${k}`, phase: '초기입장', schema: OP_SCHEMA })))
roundsData.push(r1)
roundLabels.push(`${rn(1)}라운드 — ${CONT ? '이어하기·초기입장' : '초기입장'}`)

let priorText = r1.filter(Boolean).map(o => `• ${o.persona}: ${summarize(true, false, o)}`).join('\n')
let priorLabel = `${rn(1)}라운드(초기입장) 전원 입장`
let preFinalText = priorText   // 마지막 심화(또는 심화 없으면 초기) 시점 스냅샷 — RA 'results' 블록용

for (let i = 0; i < MID_ROUNDS; i++) {
  const roundNo = rn(i + 2)
  phase('심화라운드')
  const rN = await parallel(pk.map(k => () => agent(
    `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n[${priorLabel}]\n${priorText}\n\n` +
    `${roundNo}라운드(심화 ${i + 1}/${MID_ROUNDS}): 다른 전문가 입장을 읽고 (1) 수용할 지적, (2) 반박(근거: 수치·표준·실패모드), (3) 당신 핵심 주장을 한 단계 더 깊게. 두루뭉술 금지, 당신 전문성으로.`,
    { label: `r${roundNo}:${k}`, phase: '심화라운드', schema: R2_SCHEMA })))
  roundsData.push(rN)
  roundLabels.push(`${roundNo}라운드 — 상호 반박·심화`)
  priorText = rN.filter(Boolean).map(o => `• ${o.persona}: ${summarize(false, false, o)}`).join('\n')
  priorLabel = `${roundNo}라운드(심화) 전원 입장`
  preFinalText = priorText
}

phase('수렴')
const finalRoundNo = rn(ROUNDS)
const rFinal = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n[${priorLabel}]\n${priorText}\n\n` +
  `${finalRoundNo}라운드(최종수렴): 지금까지 논의를 반영해 최종 입장으로 수렴하라. (1) 최종 입장, (2) 절대 양보 못 하는 제약, (3) 최종 권장 선택지+이유. 결정 가능하도록 구체적으로.`,
  { label: `r${finalRoundNo}:${k}`, phase: '수렴', schema: R3_SCHEMA })))
roundsData.push(rFinal)
roundLabels.push(`${finalRoundNo}라운드 — 수렴·최종 입장`)

phase('Decision')
const allRoundsText = roundsData.map((rd, idx) => {
  const isFirst = idx === 0
  const isLast = idx === roundsData.length - 1
  return `[${roundLabels[idx]}]\n` + rd.filter(Boolean).map(o => `• ${o.persona}: ${summarize(isFirst, isLast, o)}`).join('\n')
}).join('\n\n')

const DECISION_CONT_NOTE = CONT
  ? `\n\n이는 이전 심의(위 [이전 심의 요약] 참조)의 후속 라운드다. 산출 항목에 (6) 이전 결정문과의 관계(보완/수정/신규 쟁점 해소 중 무엇인지 명시)를 반드시 추가하라.`
  : ''
const decision = await agent(
  `당신은 심의체 의장. 이번 호출분 ${ROUNDS}라운드 토론(${rn(1)}~${finalRoundNo}라운드, 초기 1${MID_ROUNDS > 0 ? ` + 심화 ${MID_ROUNDS}` : ''} + 수렴 1)을 종합해 의사결정문을 한국어 엔지니어링 톤으로 작성하라.\n\n${BASE}\n\n` +
  `[전체 라운드 요약]\n${allRoundsText}\n\n[최종 라운드 상세]\n${JSON.stringify(rFinal.filter(Boolean), null, 1)}\n\n` +
  `산출: ## 의사결정문 — (1) 결정사항(번호매김, 명확·실행가능하게), (2) 합의 근거(라운드를 거치며 어떻게 수렴했는지), (3) 반대/소수의견과 처리, (4) 미해결 쟁점 + 담당·다음 액션, (5) 결정 신뢰도·전제. 라운드별 입장 심화·수렴 과정을 반드시 드러내라.${DECISION_CONT_NOTE}`,
  { label: 'decision', phase: 'Decision' })

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
  // 상한은 저장 API 보호용 여유값(발언당 2000자, 결정문 40문단). #14/#16 이 400자/12문단
  // 컷으로 잘려 수동 재작성했던 재발 방지.
  const trimmedMinutes = minutes.map(s => String(s).slice(0, 2000))
  const backgroundBlock = APPEND_TO
    ? [`이어하기 라운드(${rn(1)}~${finalRoundNo}라운드) 주제: ${Q}`, ...(HUMAN_NOTE ? [`인간 검토자 의견:\n${HUMAN_NOTE.slice(0, 2000)}`] : [])]
    : [`심의 주제: ${Q}`, ...(CTX ? [`정량 근거·분석:\n${CTX.slice(0, 4000)}`] : [])]
  const blocks = {
    background: backgroundBlock,
    results: [preFinalText.slice(0, 4000)],
    recommendation: String(decision).split('\n\n').map(s => s.trim()).filter(Boolean).slice(0, 40),
    minutes: [`참여: ${pk.join(', ')}`, `${ROUNDS}라운드 심의(${rn(1)}라운드→${MID_ROUNDS > 0 ? `심화 ${MID_ROUNDS}회→` : ''}${finalRoundNo}라운드 수렴).`, ...trimmedMinutes.slice(0, 60)],
  }
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
  msgs.push({ role: 'assistant', content: String(decision).slice(0, 8000) })
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
  decision,
  report,
  conversation,
  nextRoundOffset: finalRoundNo,   // 다음 이어하기 호출의 continueFrom.roundsSoFar 로 그대로 전달
}
