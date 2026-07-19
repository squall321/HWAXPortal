// HWAX 심의 파이프라인 — 재사용 다중 라운드 전문가 심의 워크플로
// 입력(args): { question, context, options, personas:[{key,role}], rounds }
//   - question : 심의 주제(문자열)
//   - context  : 정량 근거/분석 결과(도구로 산출한 데이터의 텍스트 요약)
//   - options  : 후보/선택지 목록(JSON 문자열 또는 배열)
//   - personas : [{key, role}] 참여 전문 페르소나(호출자가 recommend_agents로 발굴해 전달)
//   - rounds   : 심화 라운드 수(기본 2 → 초기 + 심화 + 수렴)
// 출력: { round1, round2, round3, decision } — 호출자가 viz_module + Report Archive로 보고서화.
//
// 설계: 게이트웨이 MCP가 도구(계산·에이전트·RA)를 제공하고, 이 워크플로는 그 위의 "심의 수렴"
//       오케스트레이션을 캡슐화한다. 도메인 도구 실행/페르소나 발굴/시각화는 호출자 몫(도메인별이라).
export const meta = {
  name: 'hwax-deliberate',
  description: '질문+정량근거를 다중 라운드 전문가 심의로 수렴시켜 의사결정문 생성',
  whenToUse: '여러 도메인 전문가의 의견이 갈리는 설계/분석 결정을, 도구 근거 위에서 라운드로 수렴시키고 싶을 때',
  phases: [
    { title: 'R1-초기입장', detail: '페르소나별 초기 의견 (병렬)' },
    { title: 'R2-심화반박', detail: '상호 반박·수치 심화 (병렬)' },
    { title: 'R3-수렴', detail: '최종 입장·투표 (병렬)' },
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

const BASE = `[심의 주제]\n${Q}\n\n[정량 근거·분석 결과]\n${CTX}\n\n[후보/선택지]\n${OPTS}\n`
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

phase('R1-초기입장')
const r1 = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n` +
  `당신의 도메인 관점에서만: (1) 이 근거가 당신 관심사에 무엇을 의미하는지 구체 인용해 해석, (2) 권장안, (3) 이 분석이 당신 도메인에서 놓치는 것/리스크. 수치엔 (도구)/(경험칙) 표기. 영역 밖은 아는 척 금지.`,
  { label: `r1:${k}`, phase: 'R1-초기입장', schema: OP_SCHEMA })))
const R1T = r1.filter(Boolean).map(o => `• ${o.persona}: 관점[${o.lens}] 권장[${o.recommendation}] 우려[${(o.concerns || []).join('; ')}]`).join('\n')

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

phase('R2-심화반박')
const r2 = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n[1라운드 전원 입장]\n${R1T}\n\n` +
  `2라운드: 다른 전문가 입장을 읽고 (1) 수용할 지적, (2) 반박(근거: 수치·표준·실패모드), (3) 당신 핵심 주장을 한 단계 더 깊게. 두루뭉술 금지, 당신 전문성으로.`,
  { label: `r2:${k}`, phase: 'R2-심화반박', schema: R2_SCHEMA })))
const R2T = r2.filter(Boolean).map(o => `• ${o.persona}: 수용[${(o.concede || []).join('; ')}] 반박[${(o.rebut || []).join('; ')}] 심화:${o.deepen}`).join('\n')

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

phase('R3-수렴')
const r3 = await parallel(pk.map(k => () => agent(
  `당신은 "${k}" 전문가. 영역: ${role(k)}\n\n${BASE}\n\n[2라운드 반박·심화 전원]\n${R2T}\n\n` +
  `3라운드: 2R 논의를 반영해 최종 입장으로 수렴하라. (1) 최종 입장, (2) 절대 양보 못 하는 제약, (3) 최종 권장 선택지+이유. 결정 가능하도록 구체적으로.`,
  { label: `r3:${k}`, phase: 'R3-수렴', schema: R3_SCHEMA })))

phase('Decision')
const decision = await agent(
  `당신은 심의체 의장. 3라운드를 종합해 의사결정문을 한국어 엔지니어링 톤으로 작성하라.\n\n${BASE}\n\n` +
  `[2R 심화]\n${R2T}\n\n[3R 최종입장]\n${JSON.stringify(r3.filter(Boolean), null, 1)}\n\n` +
  `산출: ## 의사결정문 — (1) 결정사항(번호매김, 명확·실행가능하게), (2) 합의 근거(라운드를 거치며 어떻게 수렴했는지), (3) 반대/소수의견과 처리, (4) 미해결 쟁점 + 담당·다음 액션, (5) 결정 신뢰도·전제. 라운드별 입장 심화·수렴 과정을 반드시 드러내라.`,
  { label: 'decision', phase: 'Decision' })

// Report Archive 저장 — MCP 경로도 포털 챗과 동일하게 웹(RA)에 보고서를 남긴다.
// (챗 deliberation.py 와 같은 template_id/blocks + 대화체 회의록). saveReport:false 로 끄면
// 반환만 하고 저장 안 함(호출자가 직접 보고서화하고 싶을 때).
let report = null
if (A.saveReport !== false) {
  phase('Report')
  const say = (rnd, o) => {
    if (rnd === 1) return `[${o.persona}] ${o.lens || ''} — 권장: ${o.recommendation || ''}`
    if (rnd === 2) return `[${o.persona}] 수용: ${(o.concede||[]).join('; ')} / 반박: ${(o.rebut||[]).join('; ')} / 핵심: ${o.deepen || ''}`
    return `[${o.persona}] ${o.final_position || ''} — 최종권장: ${o.vote || ''}`
  }
  const minutes = ['1라운드 — 도메인별 초기 입장', ...r1.filter(Boolean).map(o => say(1,o)),
                   '2라운드 — 상호 반박·심화', ...r2.filter(Boolean).map(o => say(2,o)),
                   '3라운드 — 수렴·최종 입장', ...r3.filter(Boolean).map(o => say(3,o))].map(s => String(s).slice(0,400))
  const blocks = {
    background: [`심의 주제: ${Q}`, ...(CTX ? [`정량 근거·분석:\n${CTX.slice(0,1500)}`] : [])],
    results: [R2T.slice(0,1500)],
    recommendation: String(decision).split('\n\n').map(s=>s.trim()).filter(Boolean).slice(0,12),
    minutes: [`참여: ${pk.join(', ')}`, '3라운드 심의(R1 초기→R2 심화→R3 수렴).', ...minutes.slice(0,40)],
  }
  // RA 부재/실패는 비치명적 — cae00 는 RA 가 안 떠 있을 수 있다(hands-off). 저장 실패해도
  // 심의 결과(decision·라운드)는 이미 아래 return 에 있으므로 절대 잃지 않는다.
  try {
    report = await agent(
      `create_report_draft 도구가 사용 가능하면 호출해 아래 심의 결과를 Report Archive 에 저장하라.\n` +
      `인자: template_id="deliberation", template_version=1, title="심의 — ${Q.slice(0,50)}",\n` +
      `tags=["심의","mcp-deliberation"], blocks=${JSON.stringify(blocks)}\n` +
      `- 도구가 없거나(Report Archive 미가용) 저장이 실패하면 절대 재시도하지 말고 "RA_UNAVAILABLE" 한 줄만 반환.\n` +
      `- 성공하면 반환된 report.id(보고서 번호)만 한 줄로.`,
      { label: 'ra-save', phase: 'Report' })
    if (typeof report === 'string' && /RA_UNAVAILABLE|FAILED|not available|unavailable/i.test(report)) {
      log('Report Archive 미가용 — 저장 건너뜀(심의 결과는 반환됨)')
      report = null
    }
  } catch (e) {
    log(`Report Archive 저장 실패(비치명적): ${String(e).slice(0,120)}`)
    report = null
  }
}

return { question: Q, round1: r1.filter(Boolean), round2: r2.filter(Boolean), round3: r3.filter(Boolean), decision, report }
