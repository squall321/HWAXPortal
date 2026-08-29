// HWAX 심의 파이프라인 — 재사용 다중 라운드 전문가 심의 워크플로
// 입력(args): { question, context, evidence:[{source,tool,args,result}], options, personas:[{key,role}], rounds, saveReport, saveConversation,
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
//                       비워둘 수 없게 강제. 챗의 /시험계획 과 같은 계약) |
//                       'build-plan'(구축 계획서 12항목 — 2단 해석 계획을 그 문제 특화 반복 파라메트릭
//                       시뮬 모듈 구축 계획으로. 모델링 자동화 3경로→단일 모델 IR·dry_run 게이트를 강제).
//                       시뮬레이션 심의(hwax-sim-deliberate.js)가 1단/2단/3단에서 각각 mechanism·sim-plan·
//                       build-plan 을 지정하고, 시험 계획은 hwax-test-plan.js 가 지정한다.
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

// 신규 Job 전용 지정 좌석 — 방법론의 반대/반증 역할을 좌석 구조로 보장(발굴이 반대석을 안 뽑을 수 있어
// 프롬프트 지시만으론 아무도 안 맡는다). deliberation.py _CHAIR_ADVERSARY 와 키·역할 정합. 합성 좌석 push.
const CHAIR_ADVERSARY = {
  credibility: { key: 'delib-redteam', role: `이 심의의 red-team(반대 지정석). 결론을 지지하지 말고 깨는 것이 임무 — 가장 약한 가정·가장 위태로운 외삽·미검증 Validation 공백·간과된 물리를 집요하게 파고들어 '이 결과를 믿으면 안 되는 이유'를 대라. 근거 없는 go 를 쉽게 내주지 말고, 정말 살아남는 예측만 인정하라.` },
  diagnosis: { key: 'delib-disconfirm', role: `이 진단의 반증 지정석. 지배원인 후보를 적극적으로 반증하라 — is/is-not 경계에서 그 원인이면 설명 안 되는 관측·아직 배제 안 된 대안 원인·증거의 과대해석을 지적하고, 팀이 '가장 그럴듯한 하나'로 성급히 수렴하는 것을 막아 미지영역을 드러내라.` },
  'option-select': { key: 'delib-contrarian', role: `이 선택의 반대 지정석. 유력안을 의심하라 — 숨은 비용·실패모드·양산 리스크를 파고들고, 기준·가중이 특정 안에 유리하게 짜였는지·뒤집힘 임계가 얼마나 아슬아슬한지 지적하라. 만장일치를 경계하고 열등해 보이는 안의 강점을 대변하라.` },
}
{
  const adv = CHAIR_ADVERSARY[CHAIR_TEMPLATE]
  if (adv && !pk.includes(adv.key)) { PERS.push({ key: adv.key, role: adv.role, origin: 'counter' }); pk.push(adv.key) }
}

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
// 챗 워크스페이스 핸드오프 원천 근거(deliberation.py 와 정합) — 요약이 아니라 날것 도구결과+출처를
// 좌석에 준다. '검증 대상, 결론 아님'으로 프레이밍해 좌석이 재검토하게 한다(브리프 결론이 심의를
// 오염 못 하게). 예산 ≈11KB 초과분은 중간절단 없이 항목 통째 드롭.
const EV = (Array.isArray(A.evidence) ? A.evidence : [])
  .filter(e => e && e.result != null && String(e.result).trim())
  .slice(0, 12)
let EV_BLOCK = ''
if (EV.length) {
  const evItems = []
  let evBudget = 0
  for (const e of EV) {
    const src = String(e.source || '챗').slice(0, 120)
    const meta = (e.tool ? ` · ${String(e.tool).slice(0, 80)}` : '') + (e.args ? `(${String(e.args).slice(0, 400)})` : '')
    const line = `· [${src}${meta}] ${String(e.result).slice(0, 2000)}`
    if (evBudget + line.length > 11000 && evItems.length) break
    evItems.push(line)
    evBudget += line.length
  }
  EV_BLOCK = `[챗 워크스페이스가 정리한 원천 데이터 — 검증 대상이지 결론이 아니다. 각 수치·주장을 ` +
    `당신 도메인으로 재검토하고, 부족하면 도구로 더 확인하라]\n${evItems.join('\n')}\n\n`
}
// 얹을 층(2층 Modifier) — chairTemplate(무엇을 산출)과 직교하는 "어떻게 굴리나" 오버레이.
// deliberation.py _MODIFIER_BLOCKS 와 키·취지 정합. BASE/BASE_BLIND 에 실어 좌석·의장 전체에 적용.
const MODIFIERS = {
  voi: `[얹을 층 · 교착 정산(VoI)] 패널이 값으로 결론을 못 가르고 막히면, '누가 더 그럴듯한가'를 더 논쟁하지 말고 **무엇을 측정·계산하면 결론이 갈리는가**로 전환하라. 경합하는 결론마다 그것을 뒤집을 관측량을 지목하고, 그 관측의 (a) 결정 전환 가능성 (b) 확보 비용·시간 (c) 순이득(정보가치)을 견줘 **다음에 잴 것 하나**를 정하라. 이건 해석·시험 계획으로 넘어가는 다리다.`,
  premortem: `[얹을 층 · 사전부검] 결론을 굳히기 전에, '이 결정을 그대로 실행했더니 뒤에 크게 실패했다'고 가정하고 **실패 경로부터** 3~5개 열거하라(성공 이유가 아니라). 각 실패 경로에 조기경보 신호와 선제 방어책을 붙이고, 결론을 바꿔야 할 만큼 치명적인 것이 있으면 결정에 반영하라.`,
  toulmin: `[얹을 층 · 논증 엄밀(Toulmin)] 각 핵심 주장은 **주장(claim) → 근거(data) → 왜 그 근거가 그 주장을 지지하는가(warrant)**를 명시하라. warrant 가 비면 그 주장은 근거 없는 단정이다. 가능하면 반증조건(rebuttal)과 확신도(qualifier)를 덧붙여, 세 보이지만 밑이 빈 주장을 걸러내라.`,
  eliminative: `[얹을 층 · 완결 기준] '언제 이 심의가 끝인가'를 처음에 정하라. 결론을 무너뜨릴 수 있는 반증요인(defeater)의 **유형**을 열거하고(빠진 도메인·미검증 가정·미확보 데이터·대안 가설), 각 유형이 처리됐는지 점검하라. 남은 defeater 가 있으면 결론은 '조건부'이고, 무엇이 처리되면 종료인지 밝혀라.`,
  anon1r: `[얹을 층 · 익명 1R] 1라운드는 좌석들이 서로의 발언을 보기 전에 **독립적으로** 초기 입장·핵심 추정치를 낸다(초반 쏠림·거수기 방지). 2라운드부터 공개해 반박·수렴한다. 1라운드에서 추정이 크게 갈린 지점을 이후 라운드의 우선 쟁점으로 삼아라.`,
}
const _seenMod = new Set()
const MOD_LIST = (Array.isArray(A.modifiers) ? A.modifiers : [])
  .map(m => String(m).trim())
  .filter(m => MODIFIERS[m] && !_seenMod.has(m) && _seenMod.add(m))
  .slice(0, 5)
const MODIF_BLOCK = MOD_LIST.length
  ? `[얹을 층 — 아래 방식을 심의 전체에 적용하라]\n${MOD_LIST.map(m => MODIFIERS[m]).join('\n')}\n\n`
  : ''
const TAIL = `[심의 주제]\n${Q}\n\n[정량 근거·분석 결과]\n${CTX}\n\n[후보/선택지]\n${OPTS}\n`
const BASE = `${CONT_BLOCK}${NN_BLOCK}${HUMAN_BLOCK}${EV_BLOCK}${MODIF_BLOCK}${TAIL}`
// 신규 좌석 앵커링 차단 — 이어하기에 새로 합류한 좌석(origin:'new')은 1라운드에서 이전 결론을
// 받지 않는다. 새 관점을 얻으려고 부른 사람이 기존 결론을 먼저 읽으면 동조 압력을 받는다.
const BASE_BLIND = `${NN_BLOCK}${HUMAN_BLOCK}${EV_BLOCK}${MODIF_BLOCK}${TAIL}\n[안내] 당신은 이번 회차에 새로 합류했다. ` +
  `이전 논의 결과는 의도적으로 제공하지 않는다 — 먼저 당신 도메인의 독립적 판단을 내라. 다음 라운드에서 이전 결론을 받는다.\n`
const originOf = k => (PERS.find(p => p.key === k) || {}).origin || 'primary'
// 익명 1R(anon1r) — 이어하기에서 기존 좌석도 1R 엔 이전 결론을 가려 독립 재추정을 강제(1R 은 좌석 간
// 이미 병렬 독립이라 남은 레버는 '이전 결론 은닉'). MOD_LIST 는 위에서 계산됨.
const ANON1R = MOD_LIST.includes('anon1r')
const baseFor = k => (CONT && (ANON1R || originOf(k) === 'new') ? BASE_BLIND : BASE)
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
    `해석 계획서 10개 항목 — (1) 해석 목적: 이 계산이 답할 질문 하나를 문장으로, (2) 지배방정식과 물리 모델: 위 메커니즘 결론에서 승계해 수식 수준으로 확정, (3) 해석 종류·차원·기하 축약: 3D full / 2D 평면·축대칭 / 1D 중 무엇이며 그 축약이 정당한 이유, (4) 솔버·도구 선택과 근거: 사내 보유 도구를 우선 검토하고 없을 때만 외부 도구, (5) 이산화: 메시 전략·시간 적분·수치 기법과 안정성 조건, (6) 경계·초기조건, (7) 물성·파라미터 확보 경로와 식별성 판정 — 각 파라미터를 문헌/독립 측정/피팅으로 분류하고, 피팅 대상이 둘 이상이면 서로 곱으로 붙어 분리되지 않는지(퇴화) 판정하라. 퇴화가 있으면 그것을 푸는 독립 관측을 지정하라, (8) 검증(Validation)·유효범위·불확실성: 해석해·벤치마크·시험 대조에 더해 — 이 모델이 유효한 조건 범위(외삽 위험)와 정량 수용임계(무엇이 나오면 검증 통과인가)를 **결과를 보기 전에** 선언하라. Validation(올바른 방정식·모델인가를 현실 대조로 판정)은 코드검증(방정식을 올바로 푸는가, (5))과 다르다. 핵심 예측은 파라미터 불확실을 전파해 **점값이 아니라 구간**으로 낸다, (9) 계산 규모·자원: 메시·시간스텝·케이스 수에서 실제 자원 수치를 낸다 — 클러스터(예: stc)·코어시간·벽시계·라이선스 좌석·저장용량·임계경로. '크다/작다'가 아니라 숫자여야 한다, (10) 이 해석이 답할 수 없는 것. (7)(8)(9)(10)은 비워두지 마라 — 비면 '그럴듯하지만 돌릴 수도 믿을 수도 없는' 계획서다. 끝으로 결정문 산문 뒤에 위 변수·산출·모델·자원을 기계판독 규격 sim_spec 으로 \`\`\`json 펜스 블록에 함께 내라 — {"parameters":[{"name":"","symbol":"","unit":"","role":"state|material|BC|geometry","source":"문헌|측정|피팅","value_or_range":"","identifiability":"식별가능|퇴화","degeneracy_note":"","resolving_obs":""}],"outputs":[{"quantity":"","symbol":"","unit":"","uncertainty_band":"","acceptance_criterion":"","validity_range":""}],"model":{"eq_family":"","dim":"","reduction":"","solver":"","discretization":""},"compute":{"cluster":"","cores":"","wallclock":"","license":""}}. 값은 산문 (7)(8)(9)와 일치해야 하고, 지어낸 항목은 넣지 마라(모르면 필드를 빈 문자열로). 이 규격을 다음 단계(구축 계획·비교)가 재파싱 없이 승계한다.`,
  'test-plan':
    "시험 계획서 10개 항목 — " +
    "(1) 시험 목적: 이 시험이 풀어야 할 해석·판단을 한 문장으로. 어떤 결정을 막고 있는지 명시, " +
    "(2) 대상 물성과 현재 근거: 필요한 물성을 나열하고 [물성 근거 현황] 과 대조해 각각을 " +
    "실측 보유 / 카탈로그·계열값 / 가정 / 미보유 로 판정하라. 이미 실측이 있는 항목은 " +
    "다시 측정하지 마라 — 중복 측정은 자원 낭비이고 계획서의 신뢰를 깎는다, " +
    "(3) 우선순위와 근거: 해석 결과에 대한 민감도 × 근거 공백 × 확보 난이도로 서열화하라. " +
    "'다 필요하다' 는 답이 아니다. 하나만 먼저 한다면 무엇인지 답하고 그 이유를 쓰라, " +
    "(4) 시험 항목별 방법·장비·규격·계측 불확실: 사내 보유 장비를 우선 검토하고, 없으면 외주·신규 도입으로 " +
    "구분하라. 규격이 있으면 규격 번호를 쓰고, 장비가 그 물리량의 요구 분해능·불확실을 내는지(계측 불확실 예산) 판정하라, " +
    "(5) 조건축·통계 설계: 온도·습도·속도·하중 등 어떤 축을 어느 수준으로 몇 점 잡을지. " +
    "수준 수와 표본 수를 곱해 총 시험 횟수를 명시하라. 표본 수는 산포·요구 검정력에서 근거를 대고, " +
    "전수 조합이 불가하면 어떤 DOE(부분요인·LHS)로 줄일지, " +
    "(6) 시편과 수량: 형상·전처리·반복 수. 파괴시험이면 소모량까지, " +
    "(7) 일정과 착수 순서: 경시·수명 항목은 결과가 나오는 데 수개월이 걸리므로 먼저 착수하고 " +
    "단기 항목을 병행하라. 무엇이 임계경로인지 명시하라, " +
    "(8) 판정 기준: 어떤 값이 나오면 확보로 보고 어떤 경우 재시험인가. 산포가 크면 어떻게 다룰지, " +
    "(9) 이 시험으로도 확보되지 않는 것: 남는 가정과 그 영향, " +
    "(10) sim 상관 계약: 각 시험이 검증할 해석(sim-plan)의 물리량·조건·수용임계를 명시하라 — " +
    "무엇을 어떤 값 이내로 대조하면 '해석이 시험과 맞다'고 할 것인가. 대조 대상이 없는 시험은 계획서가 아니다. " +
    "(3)(9)(10)은 비워두지 마라 — 비면 우선순위도 검증 대상도 없는 희망 목록일 뿐이다.",
  'build-plan':
    `구축 계획서 12개 항목 — 2단 해석 계획(sim-plan)을 고정 핵심으로 승계해, 한 번 돌리는 해석을 그 문제에 특화된 반복 실행형 파라메트릭 시뮬 툴로 "구축"하는 계획이다. 본체는 모델링 자동화 — 자산 3경로(a Dyna 낙하세트 승계 / b 제품 STEP 파트추출·메시 / c 2D 최소입력 슬라이스)가 하나의 정본 모델 IR 로 수렴하는 것이다. 각 항목의 구체성은 숫자·자산 경로·계약 필드로 채워라 — 비면 그 절은 계획서가 아니라 소망서다. 단위계는 export_dyna_cards 기본 ton_mm_s 로 통일한다. ` +
    `(1) 모듈 목표·비목표 [필수]: 이 툴이 반복적으로 답할 물리 질문 한 문장 + 대상 제품·파트 계열을 실명으로 + 최종 툴의 입력 스키마(파트명·디멘전·방향·재료세트·낙하고/속도·자세)와 출력 스키마(케이스별 max응력·에너지·파손플래그·스윕 결과표/응답면)를 필드 단위로 + 명시적 비목표(솔버를 LLM 으로 만들지 않는다·OSS 셋업 자동화가 아니다·이 물리 계열 밖은 안 한다). '낙하 해석 툴'로 끝나면 실패다. ` +
    `(2) 2단 sim-plan 10항목 승계·분류: context 에 [2단 sim_spec] 기계판독 규격이 있으면 그 parameters·outputs·model·compute 를 재파싱 없이 정본으로 승계하라(산문과 값이 어긋나면 규격을 우선하되 불일치를 (12)에 적는다). 2단 결정문 10항목과 양보 불가 조항을 표로 '고정 핵심 / 파라미터화(스윕 변수) / 재검토'로 분류하라. 무엇이 얼어붙고(예: 솔버=oss-openradioss, 차원축약=plane strain/axisym) 무엇이 변수인지 조용히 유실되지 않게. (2)의 지배방정식·차원축약은 (6)의 축약 가정과 물리적으로 일관해야 한다. ` +
    `(3) 파라미터 스윕·DOE [필수]: 스윕 변수 각각의 물리 의미·범위·수준 수(재료세트·기하 디멘전·낙하고/속도 v=√(2gh)·자세/방향·마찰)와 DOE 전략(전요인/부분요인/LHS), 총 케이스 수 N=수준의 곱(숫자), 반응 지표. '여러 변수'는 실패, N 이 숫자로 나와야 한다. ` +
    `(4) 모델링 자동화 A — Dyna 낙하세트 승계 [필수·use-or-justify]: KooD3plotReader·export_dyna_cards(units=ton_mm_s)·upload_kfile 로 기준 덱을 읽어 PID→(SECID·MID·파트명·지오메트리) 승계 원장 매핑표를 값으로 확정. 파트 'Group\\Name'(예: Front\\Metal·PCB\\PCB·PKG\\PKG N·Bond\\Bond)을 정규식/사전으로 역할(하우징·기판·패키지·강체벽)에 매핑하고 스윕 대상 대 고정을 규칙표로 가른다(중복·익명 이름 방어). MAT_*_TITLE 을 물성 DB 에서 재발급해 원본값(RO·E·PR)과 자릿수까지 대조하고 유사매칭 오인을 사람이 승인해야 통과하는 게이트. CONTACT_TIED·BOUNDARY_SPC·INITIAL_VELOCITY 를 SET 단위로 승계하되 치수 스윕으로 파트가 바뀌면 무엇을 재생성/보존하는지 카드 단위로. 안 쓰면 왜 안 쓰는지 적어라. ` +
    `(5) 모델링 자동화 B — 제품 STEP 파트추출·메시 [필수·use-or-justify]: StepForge 로 어셈블리 하이라키 확정 후 대상 파트 추출, Dyna 파트명↔STEP 파트명 대조표(불일치 시 자동 진행 중단), 인터페이스(tied/touching/clearance/침투) 검출을 Dyna CONTACT 와 교차검증(오분류는 사람 확정 게이트). 메시는 BREP 경로로 파트별 크기·품질지표(minSICN)·요소형식을 선택 솔버와 정합, 치수 스윕 시 재메시 트리거 규정. 안 쓰면 이유. ` +
    `(6) 모델링 자동화 C — 2D 단면 최소입력 [필수·use-or-justify]: 정확히 3필드(part_name·dimension·direction)의 스키마·단위·좌표계(전역/파트로컬)를 못박아라. 방향→평면 normal 매핑, dimension 이 슬라이스 위치인지 두께인지, 원점 규칙. 자를 소스가 STEP(평면교차)인지 d3plot 지오메트리인지 정하고, 2D 프로파일→쿼드 우선 메시→셸 요소로 잇고, plane strain/stress/axisym 축약을 (2)와 정합, 두께방향 물성·적층 투영과 단면 검증 절차. 구체 케이스(예: PKG\\PKG N 을 Z중앙 XY평면 절단)를 적어라. 안 쓰면 이유. ` +
    `(7) 최소입력 계약·모델 IR 수렴·dry_run 게이트 [필수·크럭스]: 자산 3경로(a/b/c)가 수렴하는 단일 정본 모델 IR(파트·재료·연결·BC·메시)을 필드 단위로 정의하고 솔버 드라이버가 이 IR 만 소비함을 못박아라. 3경로가 서로 다른 산출을 내면 실패다. 각 경로의 최소입력이 자동 추론으로 '닫히는 조건' 대 '사람 게이트로 넘어가는 조건'을 경계선으로(sim-plan (7) 식별성의 구축판), 스윕 진입 전 비가역 dry_run 게이트 4종(중복/익명 이름 수, 재료 유사매칭 오인, 접촉 침투가 tied 로 새는지, 단위·밀도 자릿수 불일치)마다 검출 신호·임계값을 붙여 사람 승인 없이 스윕 진입 금지. 여기가 '모델링 자동화 최대 난제'를 실제로 닫는 자리다. ` +
    `(8) SW 아키텍처·자산 재사용·프로비넌스: 파이프라인(입력 어댑터 3경로→IR 빌더→형상·메시 코어→솔버 어댑터→후처리·지표 추출→스윕 오케스트레이터)을 이름 있는 컴포넌트로, 각 컴포넌트를 재사용(KooD3plotReader·StepForge·gmsh·oss-* 컨테이너·export_dyna_cards/upload_kfile/convert_file)/신규 로 표시, 인터페이스(포맷·좌표계·단위)를 명시. 승계 결정·물성 값의 출처와 입력 자산 해시·툴 버전을 고정. 재현 불가면 실패다. ` +
    `(9) 검증·회귀 3단 게이트 [필수]: g1 자동화 충실도(자동 생성 모델이 P1 골든을 허용오차 내 재현 — 총질량·파트별 질량·무게중심·bbox·요소 수·접촉쌍 수를 원본 덱 1회 solve 의 d3plot 을 KooD3plotReader 로 읽은 baseline 과 수치 대조), g2 물리 수렴(에너지 밸런스·아워글래스·메시 독립성), g3 스윕 정합(단조성/추세·서러게이트 오차). 각 게이트에 지표·임계값을 숫자로(예: 골든 대비 max응력 오차 ≤5%). '동작하면'은 실패다. ` +
    `(10) 계산 규모·솔버 실행·오케스트레이션: 물리별 좌석 배정(명시적 낙하·충격→oss-openradioss, 정적/암시→oss-calculix/oss-code-aster, 열→oss-elmer)과 실행 계약(convert_file·ntasks·라이선스·/data), 케이스당 코어시간×N=자원 예산, 제출 경로(slurm/STC), 벽시계·저장용량·일정·임계경로를 숫자로. ` +
    `(11) 페이즈 로드맵 P1→P4 + 게이트 [필수]: P1 단일 수동 골든(기준 덱 1건을 파트·재료·BC·oss 좌석 손수 지정·실행, d3plot+정량 기준셋), P2 모델링 자동화(자산 a/b/c→IR 로 신규 형상 1건을 최소입력만으로 자동 모델링해 P1 골든 재현), P3 파라메트릭 드라이버(스윕 N+응답면), P4 툴화(입출력 계약 동결·재현성 고정). 각 페이즈에 이름 있는 산출 아티팩트·진입 전제·다음 페이즈를 막는 수치 통과/실패 게이트를 배정하라. 게이트가 '동작하면'이면 실패, 수치여야 한다. ` +
    `(12) 자동화 한계 [필수]: 파트명 승계가 실패하는 형상·재료·연결(익명 MAT·이름 충돌·미등록), 얼린 솔버가 못 잡는 물리(MAT 에 없는 파손모드), 추출기가 못 다루는 기하(얇은 피처·단순화 소실 필렛), 최소입력만으로 결정 불가한 단면(방향 모호)과 사람이 계속 손으로 할 잔여 작업을 열거하라. (1)(3)(4)(5)(6)(7)(9)(11)(12)는 비워둘 수 없다 — 비면 '돌릴 수 없는데 그럴듯한' 계획서다.`,
  diagnosis:
    `원인 규명 결정문 8개 항목 — 불량/이상의 지배원인을 증거 위에서 좁힌다. 조치(고치기)는 이 심의의 산출이 아니다 — 원인과 미지영역까지가 산출이다. (1) 현상 정의: 무엇이·어디서·언제부터·얼마나(불량률·분포) 나는가를 관측값으로. 추정 섞지 마라, (2) is / is-not 경계(KT): 이 현상이 나는 조건과 바로 옆인데 안 나는 조건을 대비하라(로트·라인·온도·시점·자재). 경계가 원인 후보를 가장 많이 잘라낸다, (3) 결함 사슬(FTA): 최상위 사상에서 아래로 AND/OR 게이트로 원인 후보를 전개하라. 관측·물리로 배제 가능한 가지는 배제하고 근거를 남겨라, (4) 고장 양식(FMEA) 교차: 각 후보를 양식·영향·검출성으로 훑어 (3)에서 빠진 경로를 보완하라, (5) 가설 경합 표(ACH): 살아남은 원인 후보 × 증거의 부합/불일치 표를 만들어, 증거로 가장 덜 반박되는 후보를 지배원인으로. '가장 그럴듯한 하나'가 아니라 '가장 덜 반증된 것'이다, (6) cut set·기여도: 지배원인(단독/조합)과 상대 기여를 명시하라. 조합이면 어떤 인자들의 곱인지, (7) 반증 관측·미지영역: 이 결론이 틀렸다면 무엇이 관측되는가 + 아직 증거가 없어 못 가르는 영역을 명시하라. 여기가 다음 시험/해석의 입력이다, (8) 합의 근거·소수의견·신뢰도. (2)(5)(7)은 비워두지 마라 — 비면 근거 없이 원인을 단정한 것이다.`,
  'option-select':
    `안 선택 결정문 8개 항목 — 경합하는 안 중에서 근거 위에서 고른다(못 고르면 무엇이 부족한지). (1) 결정 문제와 후보안: 무엇을 정하는가 + 후보안을 2개 이상 실명으로. 기준선(현행/기본안)을 반드시 하나 포함하라, (2) 평가 기준과 가중: 성능·원가·신뢰성·양산성·일정 등 기준을 정하고 가중을 합의하라. 가중 근거를 대라 — 임의 가중은 결론을 조작한다, (3) Pugh 1라운드: 기준선 대비 각 안을 기준별 +/0/− 로 채점하고 가중합을 내라. 점수의 근거(수치·시험·해석)를 각 칸에 붙여라, (4) 하이브리드안 생성: 상위안의 강점과 하위안의 강점을 결합한 새 안을 만들 수 있는가. 만들었으면 (5)에 넣어라, (5) Pugh 2라운드: 하이브리드 포함해 재채점. 라운드 간 순위가 바뀌었으면 왜인지 밝혀라, (6) Flip(민감도·뒤집힘 임계): 어떤 기준의 가중이나 어떤 입력이 얼마 바뀌면 1위가 뒤집히는가. 결론이 아슬아슬하면 그 인자를 먼저 확보하라, (7) 선택안과 조건: 고른 안 + 그것이 유효한 전제. 못 고르겠으면 무엇을 확보해야 갈리는지(→ 시험/해석), (8) 합의 근거·소수의견·신뢰도. (2)(3)(6)은 비워두지 마라 — 가중·채점·민감도가 없으면 취향일 뿐이다.`,
  credibility:
    `신뢰 판정문 8개 항목 — 이 해석/결정을 믿고 가도 되는지(go/no-go)를 채점한다. NASA-STD-7009 의 신뢰도 축을 쓴다. (1) 판정 대상과 결정: 무엇의 신뢰를 판정하며, 이 판정이 어떤 go/no-go 를 막고 있는가, (2) 신뢰도 축별 채점: 입력 데이터 품질·검증(Verification)·확인(Validation)·불확실성 정량화·모델 성숙도·인력/프로세스 — 각 축을 상/중/하로 채점하고 근거를 대라. 가장 낮은 축이 전체 신뢰의 상한이다, (3) 검증 증거: 이 결과가 해석해·벤치마크·시험과 대조된 적 있는가. 대조 없으면 '미검증'으로 명시하라(둘러대지 마라), (4) 불확실성·유효범위: 핵심 예측이 점값인가 구간인가. 이 결과가 유효한 조건 범위와 외삽 위험, (5) red-team 반박: 반대 지정석이 이 결론을 적극적으로 깨보라 — 가장 약한 가정·가장 위태로운 외삽·간과된 물리. 살아남았는가, (6) severe test: 이 모델이 틀렸다면 가장 먼저 깨질 예측은 무엇이고, 그 예측이 실제로 엄격한 시험을 통과했는가, (7) 판정: 생존(go) / 기각(no-go) / 조건부(무엇을 확보하면 go). 조건부면 조건을 수치로, (8) 합의 근거·소수의견·잔여 위험. (2)(5)(6)(7)은 비워두지 마라 — 채점·반박·시험 없는 '믿어도 된다'는 거수기다.`,
}

const DECISION_CONT_NOTE = CONT
  ? `\n\n이는 이전 심의(위 [이전 심의 요약] 참조)의 후속 라운드다. 위 산출 항목에 더해, 이전 결정문과의 관계(보완/수정/신규 쟁점 해소 중 무엇인지)를 별도 항목으로 반드시 명시하라.`
  : ''
const decision = await agent(
  `당신은 심의체 의장. 이번 호출분 ${ROUNDS}라운드 토론(${rn(1)}~${finalRoundNo}라운드, 초기 1${MID_ROUNDS > 0 ? ` + 심화 ${MID_ROUNDS}` : ''} + 수렴 1)을 종합해 의사결정문을 한국어 엔지니어링 톤으로 작성하라.\n\n${BASE}\n\n` +
  `[전체 라운드 요약]\n${allRoundsText}\n\n[최종 라운드 상세]\n${JSON.stringify(rFinal.filter(Boolean), null, 1)}\n\n` +
  `[${SEAT_NOTE}]\n\n` +
  `산출: ## ${CHAIR_TEMPLATE === 'sim-plan' ? '해석 계획서' : CHAIR_TEMPLATE === 'test-plan' ? '시험 계획서' : CHAIR_TEMPLATE === 'build-plan' ? '구축 계획서' : CHAIR_TEMPLATE === 'diagnosis' ? '원인 규명 결정문' : CHAIR_TEMPLATE === 'option-select' ? '안 선택 결정문' : CHAIR_TEMPLATE === 'credibility' ? '신뢰 판정문' : '의사결정문'} — (0) 참여 도메인과 커버리지 한계 — 위 좌석 구성을 한 문단으로 기록하고, 이 문제에 관련되나 착석하지 않은 인접 도메인이 있으면 명시하라(없으면 없다고 쓰라), ` +
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
