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
//   - buildPlan       : true 면 2단 뒤에 3단 '구축 계획서'(특화 파라메트릭 시뮬 모듈 개발)를 이어 만든다.
//                       기본 false(2단까지). 좌석은 기존 실전문가 재사용(mcad-geometry·lsdyna·system-architecture·
//                       virtual-doe·version-provenance + cae-modeling·rigor-review + 2단 솔버·물리 유임).
//   - buildRounds     : 3단 라운드 수(기본 3). buildPlan:true 일 때만 유효.
//   - carryOver       : 2단에 남길 물리 유임 좌석 수(기본 2, 0~4)
//   - simPersonas     : [{key, role}] 2단 CAE 좌석을 호출자가 직접 지정(선택). 주면 내부 발굴을 건너뛴다.
//                       세션에 게이트웨이 MCP 가 연결되지 않아 좌석 발굴 에이전트가 recommend_agents 에
//                       닿지 못하는 환경을 위한 우회로다. 고정 CAE 좌석과 물리 유임은 그대로 붙는다.
//   - spine           : 2단에 수치 스파인 고정 착석(기본 true). false 면 종전대로 modeling·post 만.
//                       코어 4층 = 정식화·이산화·솔버·검증(솔버는 2026-09-01 추가 — 아래 SPINE_CORE 주석).
//   - spineReview     : 스파인 리뷰어 2석(rigor-review·theory-grounding) 착석(기본 true, spine=true 일 때).
//   - spineValidation : 검증·UQ 2석(model-validity·uncertainty) 착석(기본 true, spine=true 일 때) —
//                       Verification 만이 아니라 Validation(현실 대조)·불확실성 구간을 강제한다.
//                       false 면 핵심 4석(formulation·discretization·solver·verification)만 고정한다.
//   - humanNote       : 1단에 주입할 사람 의견
//   - groundCards     : 좌석이 발언 전 자기 지식카드를 조회·인용(기본 true). false 로 끈다(RAG 색인 옛것/비용).
//   - saveReport      : RA 보고서 저장(**기본 꺼짐**). true 를 줄 때만 저장한다 — 실측(2026-09-02)
//                       심의 본체 3시간에 RA 저장이 1시간 반이었다(페이지마다 에이전트 1개).
//                       끄더라도 결과는 포털 대화 저장소와 반환값에 전문으로 남는다.
//   - appendToReportId: 지정 시 최종 결과(3단, buildPlan:false 면 2단)를 그 RA report_id 에 이어붙인다.
//   - deliberateScript: 자식으로 부를 심의 워크플로 경로(기본 'infra/pipeline/hwax-deliberate.js').
//                       스크립트 안의 workflow() 는 이름으로 .claude/workflows/ 를 찾지 못한다 —
//                       내장 워크플로(deep-research·code-review)만 이름으로 해석된다(실측 2026-08-07).
//                       그래서 경로로 부른다. 정본을 직접 가리키므로 레지스트리 사본 동기화에도 무관하다.
// 출력: { question, mechanism:{decision,rounds,roundLabels}, seats, simPlan:{decision,rounds,roundLabels},
//        buildPlan:{decision,rounds,roundLabels}|null(buildPlan:true 일 때만 채워짐), report, conversation }
//
// 좌석 설계가 이 워크플로의 핵심이다. CAE 전문가만 모으면 틀린 물리를 아름답게 계산한다.
// 그래서 2단 좌석을 넷으로 나눈다 — 고정 방법론 2석(modeling·post) + 수치 스파인 6석
// (formulation·discretization·solver·verification 이 방법을 세우고 rigor-review·theory-grounding 이
// 가로질러 반증·근거요구, 현상과 무관하게 필요), 발굴 CAE 2~3석(1단 결론의 물리 축으로),
// 물리 유임 1~2석(해석이 물리에서 떠나는 것을 막는 감시자).
export const meta = {
  name: 'hwax-sim-deliberate',
  description: '메커니즘 심의 → CAE 해석 설계 심의 2단으로 해석 계획서까지 만든다',
  whenToUse: '현상의 원인을 좁힌 뒤 "그걸 어떤 시뮬레이션으로, 무슨 도구로 확인할 것인가"까지 결정해야 할 때. args.modifiers[] 로 얹을 층(voi·premortem·toulmin·eliminative·anon1r)을 2단 전체에 적용. buildPlan:true 면 구축 계획서(3단)까지. 단발 심의·다른 유형은 hwax-deliberate.',
  phases: [
    { title: '메커니즘', detail: '현상 도메인 전문가가 지배 물리를 좁힌다' },
    { title: '좌석전환', detail: 'CAE 좌석 발굴 + 물리 유임자 선별' },
    { title: '해석설계', detail: 'CAE 전문가가 해석 계획서를 만든다' },
    { title: '구축설계', detail: '(opt-in) 해석 계획을 특화 파라메트릭 모듈 구축 계획서로' },
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
// ?? 는 Number 인자 안에서 — Number(undefined)=NaN 은 nullish 가 아니라 `?? 2` 가 안 먹어 CARRY=NaN
// 이 되고(기본 경로) slice(0,NaN)=[] 로 물리 유임 좌석이 통째로 사라진다. 명시적 0 은 0 으로 보존.
// `|| 0` 은 비수치 문자열(Number('x')=NaN)까지 흡수 — NaN→0→안전망이 유임 1석을 강제한다(R1~R3 와 대칭).
const CARRY = Math.min(4, Math.max(0, Math.round(Number(A.carryOver ?? 2)) || 0))
// 카드 그라운딩 — sim 심의는 기본 켠다(좌석이 발언 전 자기 지식카드를 조회해 인용). 자식
// hwax-deliberate 에 groundCards 로 전달. groundCards:false 로 끌 수 있다(RAG 색인이 옛것이거나 비용 절감).
const GROUND = A.groundCards !== false

// 3단 — 구축 계획서(opt-in). buildPlan:true 면 2단 해석 계획 뒤에 "그 문제에 특화된 반복 파라메트릭
// 시뮬 모듈을 구축하는 계획"(chairTemplate build-plan)을 이어 만든다. 기본 꺼짐 — 기존 2단 무변경.
// 좌석은 이미 저작·AIDataHub 색인된 실전문가를 재사용한다(신규 저작 0).
const DO_BUILD = A.buildPlan === true
const R3 = Math.min(8, Math.max(2, Math.round(Number(A.buildRounds) || 3)))
// 3단 고정 좌석 — 모델링 자동화·구축의 실전문가. cae-modeling·rigor-review 는 별도로 이어 앉힌다.
const BUILD_ROLES = {
  'xd-mcad-geometry': 'STEP/CAD 지오메트리 — 어셈블리 하이라키·대상 파트 추출·인터페이스 검출·2D 단면 슬라이스',
  'xd-lsdyna': 'LS-DYNA 덱·카드 — 파트명(Group\\Name)·MAT·CONTACT·BOUNDARY/INITIAL 승계·재생성 규칙',
  'xd-system-architecture': '파라메트릭 툴 구조·모델 IR 계약·자산 재사용 경계·어댑터·오케스트레이션',
  'xd-virtual-doe': '스윕 설계·DOE(요인·수준·응답·설계행렬·해상도)·응답면·감도',
  'xd-version-provenance': '승계 원장·입력 해시·툴 버전 고정·dry_run 매핑오류 게이트·재현성',
}

// 고정 좌석 — 현상과 무관하게 구축형 해석 설계에 항상 필요한 방법론 축. 발굴에 맡기면 현상
// 어휘에 끌려 이 좌석들이 빠진다. 방법론 2석(modeling·post)에 더해 수치 스파인을 고정한다 —
// 정식화→이산화→솔버→검증이 방법을 세우고, 리뷰어 2석이 가로질러 반증·근거요구한다
// (roster-gap-numerical-spine.md §3). 스파인은 recommend_agents 발굴로는 축당 1명·최대 3석이라
// 세트로 착석할 수 없으므로 고정 티어에 넣는다. 역할 텍스트가 각 좌석의 렌즈를 발언 턴에 전한다.
// spine:false → 스파인 전체 제외(종전 modeling·post 만), spineReview:false → 리뷰어 2석만 제외.
const FIXED_ROLES = {
  'xd-cae-modeling': 'CAE 전처리·모델 구성(메시·경계·하중) 방법론',
  'xd-cae-post': 'CAE 후처리·결과 검증·지표 추출 방법론',
  'xd-cae-formulation': '정식화·약형·well-posedness — 지배방정식을 정당한 약형으로 세운다',
  'xd-cae-discretization': '이산화 이론 — 요소·스킴·수렴차수·안정성',
  'xd-cae-solver': '솔버 실행 방법론 — 접촉 알고리즘·임계시간증분·질량스케일링·에너지균형·실행 모드·자원 명세',
  'xd-cae-verification': '코드검증·수렴차수(MMS·GCI) — 방정식을 올바로 푸는지의 정식 검증',
  'xd-cae-rigor-review': '수치 엄밀성 적대 리뷰어(레드팀) — 정식화·이산화·솔버·검증 네 층을 반증만, 구축은 안 한다',
  'xd-cae-theory-grounding': '이론·문헌 grounding 챌린저 — 방법 주장에 출처·인용을 요구한다',
  'xd-model-validity': '검증(Validation) — 모델이 현실을 예측하는가, 유효 범위와 외삽 위험을 판정한다',
  'xd-uncertainty': '불확실성 정량화(UQ) — 파라미터 불확실을 전파해 출력을 점값이 아닌 구간으로 만든다',
}
// 네 층이다 — 정식화·이산화·솔버·검증. 솔버 층은 2026-09-01 에 추가했다. 그 전까지 셋뿐이었는데,
// 정작 이 스파인의 레드팀(rigor-review)이 매번 "방법 명세는 정식화·이산화·솔버·검증 네 층을 모두
// 갖춰야 한다"(G1)를 양보 불가 조항으로 걸었다. 자기가 요구한 층을 채울 좌석이 자리에 없었던 것이다.
// 실측 결과 — 염수 부식-낙하 심의 2단에서 접촉 알고리즘·임계시간증분·접촉 강성·실행 모드·실행 자원
// 명세 5건이 "주인 없이 계획서에 들어갔다"고 의장이 자백했고, 그것이 그 심의 최대 결손으로 기록됐다.
const SPINE_CORE = ['xd-cae-formulation', 'xd-cae-discretization', 'xd-cae-solver', 'xd-cae-verification']
const SPINE_REVIEW = ['xd-cae-rigor-review', 'xd-cae-theory-grounding']
// 검증(V&V 의 Validation)·불확실성 다이어드 — Verification(방정식을 올바로 푸나)만으로는
// '올바른 방정식인가(현실 대조)'와 '불확실→출력 구간'이 비어 계획이 그럴듯하게만 나온다.
const SPINE_VALIDATION = ['xd-model-validity', 'xd-uncertainty']
const useSpine = A.spine !== false
const useReview = useSpine && A.spineReview !== false
const useValidation = useSpine && A.spineValidation !== false  // 기본 ON — 현실 대조·UQ 좌석
// 발굴 제외·중복 제거·자동 착석에 쓰는 고정 좌석 전체 목록
const FIXED_CAE = ['xd-cae-modeling', 'xd-cae-post',
  ...(useSpine ? SPINE_CORE : []), ...(useReview ? SPINE_REVIEW : []),
  ...(useValidation ? SPINE_VALIDATION : [])]

const dom = k => (String(k).includes('-') ? String(k).split('-')[0] : String(k))
// sim-plan 결정문에서 기계판독 규격(sim_spec) 추출 — ```json 펜스 우선, 없으면 마지막 중괄호 블록.
// 다음 단계(구축)가 산문 재파싱 대신 이 구조를 승계한다. 파싱 실패는 null(비치명적).
const parseSimSpec = text => {
  const s = String(text || '')
  const m = s.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/)
  if (m) { try { return JSON.parse(m[1]) } catch { /* 펜스 파싱 실패 → 아래 균형스캔 폴백 */ } }
  // 펜스 없거나 실패 시 — 마지막 } 에서 중괄호를 세어 짝 { 를 찾는다(중첩 JSON 방어).
  const end = s.lastIndexOf('}')
  if (end === -1) return null
  let depth = 0
  for (let i = end; i >= 0; i--) {
    if (s[i] === '}') depth++
    else if (s[i] === '{' && --depth === 0) {
      try { return JSON.parse(s.slice(i, end + 1)) } catch { return null }
    }
  }
  return null
}
// ⚠ 이 상대경로는 **정본(infra/pipeline/)에서 부를 때만** 맞는다. 사본
//   (.claude/workflows/)에서 부르면 `.claude/workflows/infra/pipeline/…` 을 찾아 없다 —
//   실측 2026-09-02: 즉시 "script file not found" 로 죽었고, 원인이 안 보여 한참 헤맸다.
//   암묵 규약을 명시적 안내로 바꾼다. 사본에서 부를 일이 있으면 deliberateScript 에
//   절대경로를 주면 된다(그 인자가 이 용도로 있다).
const DELIB = { scriptPath: A.deliberateScript || 'infra/pipeline/hwax-deliberate.js' }
if (!A.deliberateScript) {
  log('자식 심의는 상대경로로 부른다 — 이 워크플로는 **정본**(infra/pipeline/hwax-sim-deliberate.js)' +
      '으로 실행해야 한다. 사본(.claude/workflows/)에서 부르면 자식을 못 찾는다. ' +
      '사본에서 부르려면 args.deliberateScript 에 자식 절대경로를 주라.')
}
// 얹을 층(2층 Modifier) — 서브 심의(hwax-deliberate)로 전달해 sim 2단 전체에 적용(하위가 화이트리스트 재검증).
const MODS = Array.isArray(A.modifiers) ? A.modifiers : []

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
  modifiers: MODS,
  groundCards: GROUND,
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
  `이때 축 하나는 반드시 **실행 도구축**으로 잡아라 — 이 해석을 실제로 어떤 솔버로 올리는가다. ` +
  `그 축으로 검색하면 사내 솔버 전문가(xd-lsdyna 등)와 오픈소스 솔버 좌석(oss-* 계열: ` +
  `OpenRadioss·CalculiX·Code_Aster·OpenFOAM)이 나온다. 오픈소스 좌석이 발굴되면 ` +
  `**반대 관점으로 한 자리를 주는 것을 우선 고려하라** — 라이선스 없이 검증·회귀 배치를 돌릴 수 ` +
  `있는지가 반복 실행 비용을 가르고, 결론이 '이관 불가'여도 그 근거가 계획서에 남아야 한다. ` +
  `(실측 근거 — 이 축을 명시하지 않았더니 발굴이 현상 물리 좌석만 뽑았고, 그 심의의 계획서가 ` +
  `접촉 알고리즘·시간증분 등 5건을 '주인 없이 들어갔다'고 자백했다. 2026-09-01) ` +
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
log(`2단 좌석 ${simSeats.length}인 (고정 ${fixedN}${useSpine ? ` [수치 스파인 ${useReview ? SPINE_CORE.length + SPINE_REVIEW.length : SPINE_CORE.length}석${useValidation ? ` + 검증·UQ ${SPINE_VALIDATION.length}석` : ''} 포함]` : ''} · ` +
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
  modifiers: MODS,
  groundCards: GROUND,
  continueFrom: { summary: String(mech.decision).slice(0, 12000), roundsSoFar: R1, nonNegotiables: NN },
  humanNote: '사내 보유 도구를 우선 검토하라. 파라미터 식별성 판정과 이 해석이 답할 수 없는 것을 비워두지 마라.',
  // 3단이 켜지면 최종 저장(RA 보고서·대화)은 3단이 한 번만 — 2단은 중간 산출물로 남기지 않는다.
  saveReport: DO_BUILD ? false : (A.saveReport === true),
  saveConversation: DO_BUILD ? false : (A.saveConversation !== false),
  appendToReportId: DO_BUILD ? undefined : A.appendToReportId,
})

// 2단 규격 — 변수·산출·모델·자원의 기계판독 sim_spec. 구축 단계가 산문 재파싱 대신 이걸 승계한다.
const simSpec = parseSimSpec(sim && sim.decision)
if (simSpec) log(`2단 규격 추출 — 변수 ${(simSpec.parameters || []).length}·산출 ${(simSpec.outputs || []).length}`)

// ── 3단 — 구축 설계 심의 (opt-in) ─────────────────────────────────────────────
let build = null
if (DO_BUILD) {
  phase('구축설계')
  const simFinal = (sim.rounds && sim.rounds[sim.rounds.length - 1]) || []
  const buildNN = simFinal.filter(Boolean).map(o => o.non_negotiable).filter(Boolean).slice(0, 12)
  // 3단 좌석 — 구축 실전문가 고정 + 2단에서 선택된 솔버(oss-*)·물리 유임을 carry 로 이어받는다.
  const bSeen = new Set(); const buildSeats = []
  const bpush = (k, origin, role) => { if (!k || bSeen.has(k)) return; bSeen.add(k); buildSeats.push({ key: k, role: role || '', origin }) }
  Object.keys(BUILD_ROLES).forEach(k => bpush(k, 'new', BUILD_ROLES[k]))
  bpush('xd-cae-modeling', 'new', FIXED_ROLES['xd-cae-modeling'])          // 전처리·메시 방법론
  bpush('xd-cae-rigor-review', 'new', FIXED_ROLES['xd-cae-rigor-review'])  // 엄밀성·완전성 게이트
  simSeats.forEach(s => { if (/^oss-/.test(s.key) || s.origin === 'carry') bpush(s.key, 'carry', s.role) })
  log(`3단 구축설계 좌석 ${buildSeats.length}인 (구축 실전문가 ${Object.keys(BUILD_ROLES).length + 2} + 2단 솔버·물리 유임)`)
  const buildQ = `위 해석 계획을 그 문제에 특화된 반복 실행형 파라메트릭 시뮬 모듈로 구축하는 계획 — 무엇을 어떤 사내 자산으로 자동 모델링하고 어떤 변수로 스윕할 것인가. 원 현상: ${Q}`
  build = await workflow(DELIB, {
    question: buildQ,
    context: `[원 현상의 정량 근거]\n${CTX}` +
      (simSpec ? `\n\n[2단 sim_spec — 재파싱 없이 승계할 기계판독 규격(변수·산출·모델·자원)]\n${JSON.stringify(simSpec)}` : ''),
    personas: buildSeats,
    rounds: R3,
    chairTemplate: 'build-plan',
    modifiers: MODS,
    groundCards: GROUND,
    // 3단 (2)는 2단 계획서 10항목 전부를 승계·분류하므로 요약 상한을 2단(12000)보다 올린다 —
    // 상세 해석 계획서가 길어 후미 항목((8)검증·(9)규모·(10)한계)이 잘리는 것을 완화. 조항은 buildNN 별도 승계.
    continueFrom: { summary: String(sim.decision).slice(0, 20000), roundsSoFar: R1 + R2, nonNegotiables: buildNN },
    humanNote: '사내 자산(KooD3plotReader·StepForge·gmsh·oss-*·export_dyna_cards)을 우선 재사용하라. 최소입력 계약과 모델 IR 수렴·dry_run 매핑오류 게이트·페이즈별 수치 게이트를 비워두지 마라.',
    saveReport: A.saveReport === true,
    saveConversation: A.saveConversation !== false,
    appendToReportId: A.appendToReportId,
  })
}

phase('종합')
log(`완료 — 메커니즘 ${R1}라운드 + 해석 설계 ${R2}라운드${DO_BUILD ? ` + 구축 설계 ${R3}라운드` : ''}`)
// buildPlan 을 끄고 돌리면 산출이 "무엇을 계산할지"에서 멈춘다 — "어떻게 반복 자동화할지"가 없다.
// 기본값이 false 라 호출자가 의식하지 못한 채 지나가기 쉬우므로(실측 2026-09-01: 염수 부식-낙하
// 심의가 그렇게 3단을 통째로 빠뜨렸다) 조용히 끝내지 않고 명시한다. 기본값 자체는 바꾸지 않는다 —
// 3단은 좌석이 배로 늘어 비용이 크고, 계획 단계에서 2단까지만 필요한 호출이 실제로 있다.
if (!DO_BUILD) {
  log('⚠ 3단 구축 계획 생략됨(buildPlan:false) — 자동화 계획(모델 IR·최소입력 계약·dry_run 게이트)은 ' +
      '이 산출에 없다. 필요하면 buildPlan:true 로 다시 돌리거나, 2단 결정문을 continueFrom 으로 ' +
      '승계해 chairTemplate:build-plan 으로 이어 돌릴 수 있다(양보 불가 조항은 nonNegotiables 로 따로 넘길 것).')
}
return {
  question: Q,
  mechanism: { decision: mech.decision, rounds: mech.rounds, roundLabels: mech.roundLabels },
  seats: { axes: (seatPick && seatPick.axes) || [], reason: (seatPick && seatPick.reason) || '',
           sim: simSeats, carriedNonNegotiables: NN },
  simPlan: { decision: sim && sim.decision, rounds: sim && sim.rounds, roundLabels: sim && sim.roundLabels, spec: simSpec },
  buildPlan: build ? { decision: build.decision, rounds: build.rounds, roundLabels: build.roundLabels } : null,
  report: (build && build.report) || (sim && sim.report),
  conversation: (build && build.conversation) || (sim && sim.conversation),
}
