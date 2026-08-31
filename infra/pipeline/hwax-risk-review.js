// 리스크 심사 L2 오케스트레이터 — 앱에서 패널 브리프를 받아 패널마다 심의를 돌리고 결과를 원장에 되돌린다.
//
// 이 워크플로가 하는 일은 셋뿐이다 — 브리프 받기 · 패널마다 hwax-deliberate 자식 호출 · 결과 제출.
// 파싱·병합·원장·보고서 반영은 전부 앱(hwax_risk) 한 곳에서 한다. 여기서 risk_spec 을 파싱하지 않는다.
//
// 앱과의 접점은 게이트웨이 MCP 도구 둘뿐이다(백엔드 heax-hwax_risk).
//   risk_get_brief(target_key, tier)          → 패널 목록·delib_opts 초안·근거 E0~E9
//   risk_submit_panel_result(panel_id, ...)   → 결정문·라운드 수·보고서 번호 회수
// 포털 REST 를 직접 부르지 않는다(fetch 없음) — PAT 인자도 없고 신원은 게이트웨이가 정한다.
//
// 이 경로의 등급은 evidence_only 다. hwax-deliberate.js 에는 좌석 도구 호출 경로(free_tools·tools·
// apps)가 없으므로 좌석은 브리프의 [근거]만으로 판정하고, 앱은 engine='mcp' · tool_mode='evidence_only'
// 로 기록한다(웹 러너의 C2 strong 비율 분모에서 빠진다). Tier A 대표 패널과 무인 배치는 웹 러너
// 전용이라 tier:'A' 를 요청하면 앱이 {error:'tier_a_web_only'} 를 돌려주고 여기서 멈춘다.
//
// 입력(args): { targetKey, tier, panels?, actor?, model?, deliberateScript? }
//   - targetKey : 심사 대상 과제 키(앱 원장의 target_key)
//   - tier      : 'B' | 'C'. 'A' 는 웹 전용이라 앱이 거절한다
//   - panels    : 이번 실행에서 돌릴 패널 수(기본 1, 1~4). 브리프가 더 줘도 앞에서부터 이만큼만
//   - actor     : 결과 제출자 이메일(앱은 actor_verified:false 로 표기 — 검증 신원이 아니다)
//   - model     : 이 워크플로를 돌리는 LLM 모델명 신고값(없으면 'unknown', caller_reported 등급)
//   - deliberateScript : 자식 심의 워크플로 경로(기본 'infra/pipeline/hwax-deliberate.js').
//                        workflow() 는 이름으로 .claude/workflows/ 를 못 찾으므로 경로로 부른다.
// 출력: { targetKey, tier, submitted:[{panel_id, report_id, turns, decisionChars}],
//         failed:[{panel_id, error}], error? }
//   - submitted[].turns 는 원장에 넘긴 발언 레코드 수다(라운드 수가 아니다).
//   - submitted[].report_id 는 정수 또는 null 이다(rr_panels.report_id 가 INTEGER).
export const meta = {
  name: 'hwax-risk-review',
  description: '리스크 심사 패널을 앱 원장에서 받아 심의로 돌리고 결과를 되돌린다 — L2 오케스트레이터',
  whenToUse: '설계 리스크 심사(risk-review)의 편성된 패널을 Claude Code 에서 보충 회차로 돌릴 때. args 는 객체 {targetKey, tier, panels?, actor?, model?}. tier 는 B 또는 C 이며 A(대표 패널)와 무인 배치는 웹 러너 전용이다. 이 경로는 좌석 도구 호출이 없는 evidence_only 등급으로 원장에 들어간다. 단발 심사(원장 미연동)는 hwax-deliberate 에 chairTemplate:risk-review 만 주면 된다.',
  phases: [
    { title: '브리프', detail: '앱 원장에서 패널 목록·delib_opts·근거를 받는다' },
    { title: '심의', detail: '패널마다 hwax-deliberate 를 자식으로 호출' },
    { title: '회수', detail: '결정문·라운드·보고서 번호를 원장에 제출' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const TARGET = String(A.targetKey || '').trim()
if (!TARGET) throw new Error('targetKey 가 비어 있음 — 심사 대상 과제 키가 필요하다')
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
const joinList = v => (Array.isArray(v) ? v.filter(Boolean).map(String) : [])
function toTurns(roundsData) {
  if (!Array.isArray(roundsData)) return []
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
      const t = { round: i + 1, persona: String(o.persona), say: say.slice(0, SAY_CAP) }
      if (position) t.position = position.slice(0, SAY_CAP)
      if (isLast && o.non_negotiable) t.non_negotiable = String(o.non_negotiable).slice(0, SAY_CAP)
      out.push(t)
      if (out.length >= TURN_CAP) return
    }
  })
  return out.slice(0, TURN_CAP)
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
  // 인자는 둘뿐이다 — 도구는 actor 를 받지 않는다(게이트웨이가 최종 사용자를 싣지 않아
  // 앱이 응답에 reason='caller_unresolved' 를 남긴다, §6.11).
  `인자: target_key="${TARGET}", tier="${TIER}"\n` +
  `- 결과를 요약·가공하지 말고 스키마 필드에 그대로 옮겨라. 근거(evidence)의 result 문자열은 원문 그대로다.\n` +
  `- 응답에 error 가 있으면 error 에 그 코드를 넣고 panels 는 빈 배열로 둬라.\n` +
  `- 도구가 없거나 호출이 실패하면 error="brief_unavailable" 로 두고 panels 는 빈 배열로 둬라. 재시도하지 마라.`,
  { label: 'brief', phase: '브리프', schema: BRIEF_SCHEMA })

const briefError = (brief && String(brief.error || '')).trim()
if (briefError) {
  // tier_a_web_only 는 정상 응답이다 — 대표 패널은 웹 러너만 돌린다. 그대로 보고하고 멈춘다.
  log(`브리프 중단 — ${briefError}${brief.reason ? ` (${brief.reason})` : ''}`)
  return { targetKey: TARGET, tier: TIER, submitted: [], failed: [], error: briefError,
           reason: String((brief && brief.reason) || '') }
}

const panels = ((brief && brief.panels) || []).filter(p => p && p.panel_id && (p.seats || []).length)
  .slice(0, MAX_PANELS)
if (!panels.length) {
  log('편성된 패널이 없다 — 앱에서 먼저 패널을 편성해야 한다')
  return { targetKey: TARGET, tier: TIER, submitted: [], failed: [], error: 'no_planned_panel',
           reason: String((brief && brief.reason) || '') }
}
log(`패널 ${panels.length}건 — target=${TARGET} tier=${TIER} actor=${ACTOR || '(미지정)'} model=${MODEL}`)

// ── 패널마다 심의 → 회수 ─────────────────────────────────────────────────────
const submitted = []
const failed = []
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
    log(`패널 ${p.panel_id} 결정문 없음 — 제출하지 않는다`)
    continue
  }

  // 회수 — 결정문 원문을 그대로 앱에 넘긴다. 파싱·병합은 앱 한 곳에서 한다.
  phase('회수')
  const turns = toTurns(result.rounds)
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
    submitted.push({ panel_id: p.panel_id, report_id: reportNo, turns: turns.length,
                     decisionChars: String(result.decision).length })
    log(`패널 ${p.panel_id} 제출 완료 — 발언 ${turns.length}건, 보고서 ${reportNo ?? '미저장'}`)
  } else {
    failed.push({ panel_id: p.panel_id, error: `submit_failed: ${(ack && ack.detail) || 'unknown'}` })
    log(`패널 ${p.panel_id} 제출 실패 — 심의 결과는 아래 반환에 남는다`)
  }
}

log(`완료 — 제출 ${submitted.length}건 / 실패 ${failed.length}건`)
return { targetKey: TARGET, tier: TIER, submitted, failed }
