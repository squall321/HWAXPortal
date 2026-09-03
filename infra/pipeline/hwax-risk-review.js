// 리스크 심사 L2 오케스트레이터 — 앱에서 패널 브리프를 받아 패널마다 심의를 돌리고 결과를 원장에 되돌린다.
//
// 이 워크플로가 하는 일은 셋뿐이다 — 브리프 받기 · 패널마다 hwax-deliberate 자식 호출 · 결과 제출.
// 파싱·병합·원장·보고서 반영은 전부 앱(hwax_risk) 한 곳에서 한다. 여기서 risk_spec 을 파싱하지 않는다.
//
// 앱과의 접점은 게이트웨이 MCP 도구 둘뿐이다(백엔드 heax-hwax_risk).
//   risk_get_brief(target_key, brief_token, tier) → 패널 목록·delib_opts 초안·근거 E0~E9
//   risk_submit_panel_result(panel_id, ...)   → 결정문·라운드 수·보고서 번호 회수
// 포털 REST 를 직접 부르지 않는다(fetch 없음) — PAT 인자도 없고 신원은 게이트웨이가 정한다.
//
// 이 경로의 등급은 evidence_only 다. hwax-deliberate.js 에는 좌석 도구 호출 경로(free_tools·tools·
// apps)가 없으므로 좌석은 브리프의 [근거]만으로 판정하고, 앱은 engine='mcp' · tool_mode='evidence_only'
// 로 기록한다(웹 러너의 C2 strong 비율 분모에서 빠진다). Tier A 대표 패널과 무인 배치는 웹 러너
// 전용이라 tier:'A' 를 요청하면 앱이 {error:'tier_a_web_only'} 를 돌려주고 여기서 멈춘다.
//
// 입력(args): { targetKey, briefToken, tier, panels?, actor?, model?, deliberateScript? }
//   - targetKey : 심사 대상 과제 키(앱 원장의 target_key)
//   - briefToken: 앱 화면(GET /targets/{key}/brief)이 발급한 1건짜리 브리프 토큰. 읽기 범위를 여는 유일한
//                 열쇠라 필수다 — 없으면 앱을 부르기 전에 멈춘다(계획 §8.2.5)
//   - tier      : 'B' | 'C'. 'A' 는 웹 전용이라 앱이 거절한다
//   - panels    : 이번 실행에서 돌릴 패널 수(기본 1, 1~4). 브리프가 더 줘도 앞에서부터 이만큼만
//   - actor     : 결과 제출자 이메일(앱은 actor_verified:false 로 표기 — 검증 신원이 아니다)
//   - model     : 이 워크플로를 돌리는 LLM 모델명 신고값(없으면 'unknown', caller_reported 등급)
//   - deliberateScript : 자식 심의 워크플로 경로(기본 'infra/pipeline/hwax-deliberate.js').
//                        workflow() 는 이름으로 .claude/workflows/ 를 못 찾으므로 경로로 부른다.
// 출력: { targetKey, tier, submitted:[{panel_id, report_id, turns, decisionChars, flags}],
//         failed:[{panel_id, error}], partials:[{panel_id, decision?, rounds, …}], error? }
//   - submitted[].turns 는 원장에 넘긴 발언 레코드 수다(라운드 수가 아니다).
//   - submitted[].report_id 는 정수 또는 null 이다(rr_panels.report_id 가 INTEGER).
//   - partials 는 제출되지 못한 패널의 심의 데이터 보존분이다(결정문 절단·페이로드 초과·
//     제출 실패·no_decision) — 자식의 부분 반환 원칙을 부모도 지킨다(감사 1-F). 여기 있는
//     데이터로 결정적 재제출·전사 복원·continueFrom 재의결이 가능하다.
export const meta = {
  name: 'hwax-risk-review',
  description: '리스크 심사 패널을 앱 원장에서 받아 심의로 돌리고 결과를 되돌린다 — L2 오케스트레이터',
  whenToUse: '설계 리스크 심사(risk-review)의 편성된 패널을 Claude Code 에서 보충 회차로 돌릴 때. args 는 객체 {targetKey, briefToken, tier, panels?, actor?, model?}. briefToken 은 앱 화면 GET /targets/{key}/brief 에서 복사해 오는 필수 인자다. tier 는 B 또는 C 이며 A(대표 패널)와 무인 배치는 웹 러너 전용이다. 이 경로는 좌석 도구 호출이 없는 evidence_only 등급으로 원장에 들어간다. 단발 심사(원장 미연동)는 hwax-deliberate 에 chairTemplate:risk-review 만 주면 된다. ⚠ 이름으로는 못 부른다(내장 워크플로만 이름 해석) — Workflow 의 scriptPath 에 정본 경로 <리포루트>/infra/pipeline/hwax-risk-review.js 를 준다. 사본(.claude/workflows/)에서 부르면 자식 워크플로를 못 찾는다.',
  phases: [
    { title: '브리프', detail: '앱 원장에서 패널 목록·delib_opts·근거를 받는다' },
    { title: '심의', detail: '패널마다 hwax-deliberate 를 자식으로 호출' },
    { title: '회수', detail: '결정문·라운드·보고서 번호를 원장에 제출' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const TARGET = String(A.targetKey || '').trim()
if (!TARGET) throw new Error('targetKey 가 비어 있음 — 심사 대상 과제 키가 필요하다')
// brief_token 은 읽기 범위를 여는 유일한 열쇠다(계획 §8.2.5) — 없이 부르면 앱이 brief_token_invalid 를
// 돌려주므로 앱을 부르기 전에 사람에게 되돌린다.
const BRIEF_TOKEN = String(A.briefToken || '').trim()
if (!BRIEF_TOKEN) throw new Error('briefToken 이 비어 있음 — 앱 화면에서 브리프 토큰을 받아 오세요')
const TIER = String(A.tier || 'C').trim().toUpperCase()
const MAX_PANELS = Math.min(4, Math.max(1, Math.round(Number(A.panels) || 1)))
const ACTOR = String(A.actor || '').trim()
// 모델 출처(D6) — MCP 경로에는 agent-server /health 스냅샷이 없어 호출자 신고값을 그대로 적는다.
const MODEL = String(A.model || '').trim() || 'unknown'
const DELIB = { scriptPath: A.deliberateScript || 'infra/pipeline/hwax-deliberate.js' }
// 좌석 프롬프트 추가 문장 — 이 경로엔 도구 호출 경로가 없다. 좌석 계약 상수의 마지막 문장
// (evidence_only 절)이 이를 받아 "[근거]의 수치를 같은 형식으로 인용하라" 로 잇는다.
const EVIDENCE_ONLY_NOTE = '이 실행에는 도구 호출 경로가 없다 — 도구를 호출하지 말고 [근거]만으로 판정하라.'

// 자식 심의의 rounds 를 앱이 받는 turn 레코드로 옮긴다 — 계획 §6.7 7단계의
// `turn{round, persona, say, position?, stance?, non_negotiable?}` 형식이고 앱은 이것을
// rr_seat_opinions.turns 로 저장한다. 여기서 요약·재작성을 하지 않는다(엔진이 낸 필드만 옮긴다).
// hwax-deliberate 의 라운드 스키마는 셋이다 — 1라운드 {lens, recommendation, concerns},
// 중간 {concede, rebut, deepen}, 마지막 {final_position, non_negotiable, vote}.
const TURN_CAP = 60          // 저장 상한(계획 §0.6 turns 60/대화)
const SAY_CAP = 2000         // seat_opinion.say_excerpt 상한
// 캡 절단에 표식을 남긴다(감사 1-F) — 무표식 절단은 좌석이 잘린 발언을 완결로 읽게 한다.
// 표식 포함 총길이가 캡을 넘지 않게 안쪽에서 자른다(원장 열 상한이 캡 기준일 수 있다).
const capMark = (s) => {
  const v = String(s)
  return v.length > SAY_CAP ? v.slice(0, SAY_CAP - 25) + ` …[총 ${v.length}자]` : v
}
const joinList = v => (Array.isArray(v) ? v.filter(Boolean).map(String) : [])
function toTurns(roundsData) {
  if (!Array.isArray(roundsData)) return { turns: [], dropped: 0 }
  const out = []
  const last = roundsData.length - 1
  roundsData.forEach((rd, i) => {
    const isFirst = i === 0
    const isLast = i === last && last > 0
    for (const o of (Array.isArray(rd) ? rd : [])) {
      if (!o || !o.persona) continue
      let say = ''
      let position = ''
      if (isFirst) {
        say = [o.lens, o.recommendation, ...joinList(o.concerns)].filter(Boolean).join('\n')
        position = String(o.recommendation || '')
      } else if (isLast) {
        say = [o.final_position, o.non_negotiable, o.vote].filter(Boolean).join('\n')
        position = String(o.final_position || '')
      } else {
        say = [...joinList(o.concede), ...joinList(o.rebut), o.deepen].filter(Boolean).join('\n')
        position = String(o.deepen || '')
      }
      const t = { round: i + 1, persona: String(o.persona), say: capMark(say) }
      if (position) t.position = capMark(position)
      if (isLast && o.non_negotiable) t.non_negotiable = capMark(o.non_negotiable)
      out.push(t)
    }
  })
  // 캡 초과분은 **앞(초기 라운드)** 을 버리고 꼬리를 지킨다(감사 1-F 실증) — 종전의 선두 우선
  // 채움은 21석×6R(126건)에서 최종 라운드의 final_position·vote 전원분을 무표시로 버렸다.
  // 원장의 최우선 가치는 최종 입장이다. 드롭은 반드시 로그한다.
  const dropped = Math.max(0, out.length - TURN_CAP)
  if (dropped) {
    log(`⚠ 발언 ${out.length}건 중 앞라운드 ${dropped}건 드롭(TURN_CAP ${TURN_CAP}) — ` +
        `최종 라운드를 보존했다. 전체 발언은 반환 partials/자식 결과에 있다.`)
  }
  return { turns: out.slice(-TURN_CAP), dropped }
}

// ── 브리프 ───────────────────────────────────────────────────────────────────
phase('브리프')
const BRIEF_SCHEMA = {
  type: 'object',
  properties: {
    error: { type: 'string', description: '앱이 오류를 돌려줬으면 그 코드(예 tier_a_web_only). 없으면 빈 문자열' },
    reason: { type: 'string', description: '앱이 reason 을 돌려줬으면 그 값(예 caller_unresolved). 없으면 빈 문자열' },
    panels: {
      type: 'array',
      description: '앱이 돌려준 패널 목록을 그대로. 값을 지어내지 말 것',
      items: {
        type: 'object',
        properties: {
          panel_id: { type: 'string' },
          question: { type: 'string', description: '패널 질문 문자열(브리프에 있으면 그대로)' },
          seats: {
            type: 'array',
            description: 'seats_json 의 좌석 목록',
            items: {
              type: 'object',
              properties: {
                key: { type: 'string' },
                role: { type: 'string' },
                origin: { type: 'string', description: 'primary | counter' },
              },
              required: ['key'],
            },
          },
          modifiers: { type: 'array', items: { type: 'string' }, description: 'delib_opts 초안의 modifiers' },
          rounds: { type: 'number', description: 'delib_opts 초안의 rounds(없으면 0)' },
          evidence: {
            type: 'array',
            description: '근거 항목 E0~E9 를 순서 그대로',
            items: {
              type: 'object',
              properties: {
                source: { type: 'string' },
                tool: { type: 'string' },
                args: { type: 'string' },
                result: { type: 'string' },
              },
              required: ['source', 'result'],
            },
          },
        },
        required: ['panel_id', 'seats'],
      },
    },
  },
  required: ['panels'],
}

const brief = await agent(
  `risk_get_brief 도구를 정확히 한 번 호출해 리스크 심사 패널 브리프를 받아라.\n` +
  // 인자는 셋뿐이다 — 도구는 actor 를 받지 않는다. 읽기 범위는 자칭 신원이 아니라 brief_token
  // 대조가 정하고, 토큰이 틀리거나 만료면 앱이 {error:'brief_token_invalid'} 를 돌려준다(§8.2.5).
  `인자: target_key="${TARGET}", brief_token="${BRIEF_TOKEN}", tier="${TIER}"\n` +
  `- 결과를 요약·가공하지 말고 스키마 필드에 그대로 옮겨라. 근거(evidence)의 result 문자열은 원문 그대로다.\n` +
  `- 응답에 error 가 있으면 error 에 그 코드를 넣고 panels 는 빈 배열로 둬라.\n` +
  `- 도구가 없거나 호출이 실패하면 error="brief_unavailable" 로 두고 panels 는 빈 배열로 둬라. 재시도하지 마라.`,
  { label: 'brief', phase: '브리프', schema: BRIEF_SCHEMA })

// agent() 는 API 오류·취소 시 null 이다(계약) — 가드 밖 .trim() 은 TypeError 즉사였다(감사 1-F).
const briefError = String((brief && brief.error) || '').trim()
if (briefError) {
  // tier_a_web_only 는 정상 응답이다 — 대표 패널은 웹 러너만 돌린다. 그대로 보고하고 멈춘다.
  // brief_token_invalid 는 토큰이 다르거나 만료(기본 900 s)라는 뜻이다 — 앱 화면에서 다시 받아야 한다.
  if (briefError === 'brief_token_invalid') log('브리프 토큰이 만료·불일치다 — 앱 화면에서 다시 받아 오세요')
  log(`브리프 중단 — ${briefError}${brief.reason ? ` (${brief.reason})` : ''}`)
  return { targetKey: TARGET, tier: TIER, submitted: [], failed: [], error: briefError,
           reason: String((brief && brief.reason) || '') }
}

const _rawPanels = (brief && brief.panels) || []
const _validPanels = _rawPanels.filter(p => p && p.panel_id && (p.seats || []).length)
if (_validPanels.length < _rawPanels.length) {
  log(`⚠ 브리프 패널 ${_rawPanels.length}건 중 ${_rawPanels.length - _validPanels.length}건 제외` +
      `(panel_id 또는 seats 누락) — 앱 브리프를 점검하라`)
}
if (_validPanels.length > MAX_PANELS) {
  log(`패널 ${_validPanels.length}건 중 앞 ${MAX_PANELS}건만 실행(panels 인자 상한) — ` +
      `나머지는 다음 실행에서`)
}
const panels = _validPanels.slice(0, MAX_PANELS)
if (!panels.length) {
  log('편성된 패널이 없다 — 앱에서 먼저 패널을 편성해야 한다')
  return { targetKey: TARGET, tier: TIER, submitted: [], failed: [], error: 'no_planned_panel',
           reason: String((brief && brief.reason) || '') }
}
log(`패널 ${panels.length}건 — target=${TARGET} tier=${TIER} actor=${ACTOR || '(미지정)'} model=${MODEL}`)

// ── 패널마다 심의 → 회수 ─────────────────────────────────────────────────────
const submitted = []
const failed = []
// 제출 못 한 패널의 심의 데이터 보존(감사 1-F) — 자식의 "의장이 죽어도 라운드는 돌려준다"
// 원칙을 부모도 지킨다. 수 시간 심의가 제출 한 홉의 실패로 증발하지 않게 한다.
const partials = []
const keepPartial = (p, result, why) => partials.push({
  panel_id: p.panel_id, why,
  decision: result && result.decision ? String(result.decision) : null,
  decisionTruncated: result ? result.decisionTruncated : undefined,
  rounds: (result && result.rounds) || [],
  seatLoss: (result && result.seatLoss) || [],
  citationAudit: result ? result.citationAudit : undefined,
  nextRoundOffset: result ? result.nextRoundOffset : undefined,
})
for (const p of panels) {
  const seats = (p.seats || []).filter(s => s && s.key).map(s => ({
    key: String(s.key),
    // 좌석 역할은 엔진이 좌석 계약을 접미로 붙인다(RISK_SEAT_CONTRACT). 여기서는 이 실행이
    // 도구 없는 경로임을 한 줄로 알린다 — 계약의 evidence_only 절이 이를 받는다.
    role: `${String(s.role || '')}\n${EVIDENCE_ONLY_NOTE}`.trim(),
    origin: (s.origin === 'counter' ? 'counter' : 'primary'),
  }))
  const mods = Array.isArray(p.modifiers) && p.modifiers.length ? p.modifiers : ['toulmin']
  const rounds = Math.min(8, Math.max(2, Math.round(Number(p.rounds) || 3)))
  const question = String(p.question || '').trim()
    || `[리스크심사 ${TARGET}] 각 도메인에서 어떤 리스크와 개선이 생기는가를 [근거]로 판정하라.`

  phase('심의')
  log(`패널 ${p.panel_id} — 좌석 ${seats.length}인, ${rounds}라운드, 근거 ${(p.evidence || []).length}항목`)
  let result = null
  try {
    result = await workflow(DELIB, {
      question,
      personas: seats,
      chairTemplate: 'risk-review',
      modifiers: mods,
      evidence: p.evidence || [],
      rounds,
      saveReport: true,
      saveConversation: false,
    })
  } catch (e) {
    failed.push({ panel_id: p.panel_id, error: String(e).slice(0, 300) })
    log(`패널 ${p.panel_id} 심의 실패 — 제출하지 않는다(앱 재시도 규칙이 처리)`)
    continue
  }
  if (!result || !result.decision) {
    failed.push({ panel_id: p.panel_id, error: 'no_decision' })
    keepPartial(p, result, 'no_decision')   // 자식의 부분 반환(라운드·seatLoss)을 폐기하지 않는다
    log(`패널 ${p.panel_id} 결정문 없음 — 제출하지 않는다(라운드 데이터는 반환 partials 에 보존)`)
    continue
  }
  // 절단본을 기계 병합(앱의 risk_spec 파싱)에 넘기면 원장이 반쪽 펜스로 오염된다(감사 1-F 치명).
  // 'marker-missing' 은 꼬리 완결 오탐 분류라 진행하되 제출 레코드 플래그로 남긴다.
  if (result.decisionTruncated === true) {
    failed.push({ panel_id: p.panel_id, error: 'decision_truncated' })
    keepPartial(p, result, 'decision_truncated')
    log(`패널 ${p.panel_id} 결정문 절단 — 원장 오염 방지 위해 제출하지 않는다. ` +
        `전문은 전사 agent-*.jsonl 에서 복원 후 결정적 재제출(반환 partials 참조)`)
    continue
  }
  if (result.seatLoss && result.seatLoss.length) {
    log(`⚠ 패널 ${p.panel_id} 좌석 유실 ${result.seatLoss.length}건 — ` +
        result.seatLoss.map(x => `${x.round}R:${(x.lost || []).join('/')}`).join(', ') +
        ` (결정문 (0)항에 반영됨, 제출 레코드 플래그로도 남긴다)`)
  }

  // 회수 — 결정문 원문을 그대로 앱에 넘긴다. 파싱·병합은 앱 한 곳에서 한다.
  phase('회수')
  const { turns, dropped: droppedTurns } = toTurns(result.rounds)
  // 보고서 번호는 원장 열이 INTEGER 다(rr_panels.report_id) — 에이전트가 한 줄로 돌려주는
  // 보고서 번호에서 숫자만 뽑고, 없으면 null 로 보내 열을 건드리지 않는다.
  const reportNo = (() => {
    const m = String(result.report || '').match(/\d+/)
    return m ? Number(m[0]) : null
  })()
  const SUBMIT_SCHEMA = {
    type: 'object',
    properties: {
      ok: { type: 'boolean', description: '도구가 성공했으면 true' },
      detail: { type: 'string', description: '실패했으면 오류 코드·메시지, 성공이면 빈 문자열' },
    },
    required: ['ok'],
  }
  // 에코 제출 크기 예산(감사 1-F 치명) — 자식 CONV_AGENT_BUDGET 와 같은 근거: 대형 페이로드를
  // LLM 이 도구 인자로 옮기면 조용히 요약·의역해 넣고 성공을 돌려준다(실측 C37/C50). 절단보다
  // 나쁜 무표시 변조라, 예산을 넘으면 에코 제출을 생략하고 데이터를 반환에 보존한다.
  const SUBMIT_BUDGET = 60000
  const payloadSize = JSON.stringify(turns).length + String(result.decision).length
  if (payloadSize > SUBMIT_BUDGET) {
    failed.push({ panel_id: p.panel_id,
                  error: `payload_too_large: ${payloadSize}자 > ${SUBMIT_BUDGET}` })
    keepPartial(p, result, 'payload_too_large')
    log(`패널 ${p.panel_id} 페이로드 ${payloadSize.toLocaleString()}자 — LLM 에코 제출은 이 크기에서 ` +
        `의역 변조된다(실측). 제출 생략, 반환 partials 의 원문으로 결정적 제출이 필요하다`)
    continue
  }
  let ack = null
  try {
    ack = await agent(
      `risk_submit_panel_result 도구를 정확히 한 번 호출해 아래 패널 결과를 리스크 심사 원장에 제출하라.\n` +
      `인자(전부 필수, 아래 값을 그대로 — 값을 지어내거나 형식을 바꾸지 마라):\n` +
      `  panel_id = "${p.panel_id}"\n` +
      `  engine = "mcp"\n` +
      `  actor = ${JSON.stringify(ACTOR)}\n` +
      `  model = "${MODEL}"\n` +
      `  report_id = ${reportNo === null ? 'null' : reportNo}\n` +
      `  turns = ${JSON.stringify(turns)}\n` +
      `  decision_text = ${JSON.stringify(String(result.decision))}\n` +
      `- turns 는 위 JSON 배열 그대로다(객체 목록이지 개수가 아니다). 항목을 줄이거나 요약하지 마라.\n` +
      `- decision_text 는 위 문자열 그대로다. 요약·재작성·펜스 제거를 하지 마라.\n` +
      `- 실패하면 재시도하지 말고 ok=false 와 detail 에 오류를 담아라.`,
      { label: `submit:${p.panel_id}`, phase: '회수', schema: SUBMIT_SCHEMA })
  } catch (e) {
    ack = { ok: false, detail: String(e).slice(0, 300) }
  }
  if (ack && ack.ok) {
    submitted.push({
      panel_id: p.panel_id, report_id: reportNo, turns: turns.length,
      decisionChars: String(result.decision).length,
      // 자식 품질 플래그 승계(감사 1-F) — 원장 감사 시 절단·유실·대조 상태를 여기서 본다.
      flags: {
        decisionTruncated: result.decisionTruncated || false,   // 'marker-missing' 이면 그 문자열
        seatLoss: (result.seatLoss || []).length,
        droppedTurns,
        citationUnmatched: (result.citationAudit && result.citationAudit.unmatched
                            ? result.citationAudit.unmatched.length : null),
      },
    })
    log(`패널 ${p.panel_id} 제출 완료 — 발언 ${turns.length}건${droppedTurns ? `(+드롭 ${droppedTurns})` : ''}, ` +
        `보고서 ${reportNo ?? '미저장'}`)
  } else {
    failed.push({ panel_id: p.panel_id, error: `submit_failed: ${(ack && ack.detail) || 'unknown'}` })
    keepPartial(p, result, 'submit_failed')
    log(`패널 ${p.panel_id} 제출 실패 — 결정문·라운드는 반환 partials 에 보존했다(결정적 재제출 재료)`)
  }
}

log(`완료 — 제출 ${submitted.length}건 / 실패 ${failed.length}건 / 보존 ${partials.length}건`)
return { targetKey: TARGET, tier: TIER, submitted, failed, partials }
