# 심의 메뉴 — 컨텍스트 노트(결정과 이유)

작업 중 내린 결정을 시간순으로 기록한다. 다음 세션이 재도출 없이 이어받기 위한 문서.

## 2026-07-17 설계 결정

**D1. 심의 기록은 챗 이력과 분리(사용자 확정).**
localStorage 키를 `hwax.delib.*`로 분리. 구현은 새 스토어를 만들지 않고 기존
`chatStore.ts`/`ChatContext.tsx`를 prefix 파라미터화해 재사용 — Composer/MessageList/
ChatSidebar가 가장 가까운 Provider를 읽는 React Context 특성 덕에, `/deliberate` 라우트를
중첩 `<ChatProvider storagePrefix="hwax.delib" sendPrefix="/심의 ">`로 감싸면 복제 코드 0으로
심의 전용 이력이 된다. AppShell의 플로팅 ChatDock은 바깥(일반 챗) Provider를 보므로 간섭 없음.

**D2. Claude MCP 진입은 기존 워크플로 정본 유지(사용자 확정).**
`hwax-deliberate.js`가 이미 `context` 인자를 받으므로, Claude 경로의 불량 환기는 호출자가
SF 도구(alert_check/get_top_issues/query_voc)를 먼저 부르고 요약을 `args.context`로 넘기면
코드 수정 0. 'deliberate' MCP 도구 신설(agent-server FastMCP 서브서버 + submit/poll 잡 패턴)은
범위 밖으로 보류 — 게이트웨이는 pure pass-through(자체 도구 0)이고 동기 호출은
CALL_TIMEOUT_S=120에 걸린다(심의 실측 수 분).

**D3. 불량 환기는 agent-server(deliberation.py)의 전단계로 구현.**
위치: tools 로드 직후 ~ recommend_agents 사이. SF 3-콜 시퀀스(매핑 워크플로 권고안).
1) `alert_check` {} — 무인자 경보(부정비율/부정급증). MIN_VOLUME=30 노이즈 컷이라 빈 배열이 정상.
2) 경보 제품 있으면 `get_top_issues`{product_code,period_days:7,top_n:5}, 없으면 `daily_briefing` 폴백.
3) `query_voc`{sentiment:'negative',limit:5} 원문 증거(content_translated 200자 컷).
연관성 판정은 LLM 1콜(JSON {relevant,reason}) — 사용자 요구가 "연관된 문제가 있으면 포함,
없으면 그냥 질문 기반"이므로 항상 포함이 아니라 판정 후 주입. 전 과정 best-effort(도구 실패가
심의를 죽이지 않음, 기존 `_call` 패턴).

**D4. 심의 SSE 계약을 일반 경로와 정합(버그 수정 겸).**
프론트 `chat.api.ts`는 `status/token/result/error/done`만 dispatch하고 `token`은 `delta` 필드를
읽는다. 기존 심의 경로는 `token{content}`+`text{content}`를 방출 → 포털 챗에서 "undefined"
연결 또는 미표시. 수정: 환기 요약·의사결정문을 `token{delta}`로 흘리고 마지막에
`result{type:'text',content:전문}`으로 확정.

**D5. SF '불량'의 도메인 주의.**
SignalForge 데이터는 제조라인 결함이 아니라 소비자 VOC 부정 감성이다. 주입 블록 라벨을
"최근 고객 불만 신호 (SignalForge VOC)"로 명시해 심의 페르소나가 오해하지 않게 한다.

**D6. 게이트웨이 도구명은 flat.**
게이트웨이는 이름 충돌 시에만 `{backend}_` prefix를 붙인다. SF 도구는 `alert_check`,
`query_voc`, `get_top_issues`, `daily_briefing` 그대로 보인다(라이브 148 tools에서 확인).

## 참고(매핑에서 발견된 기존 버그·리스크, 이번 범위 밖)

- `hwax-deliberate.js`의 `rounds` 인자는 문서화만 되고 코드는 3라운드 고정(무시됨).
- `create_report_draft` 실패가 bare except로 무음 — 보고서 누락을 알 수 없음(이번에 로그 한 줄 추가 고려).
- dev vLLM 7B는 완주하나 느리고 품질 약함 — 실용 품질은 상암 GLM 전제.
- README 도구 수(46)는 낡음 — 라이브 148 tools/7 backends.
