# 심의 메뉴(화두→심의 분석) — 체크리스트

목표: 포털 메인에 심의 전용 메뉴/페이지를 추가한다. 화두에 불량 얘기가 있으면 SignalForge에서
최근 불량 이슈를 먼저 환기하고, 연관되면 심의 컨텍스트에 포함한다. 대화는 chat처럼 기록으로
남고, 최종 결과는 Report Archive 보고서로 출력된다. Claude MCP(정본 워크플로)와 포털 chat
양쪽에서 같은 심의가 가능해야 한다.

## Backend (HWAXAgentServer)

- [x] `deliberation.py` — 불량 키워드 감지(`_has_defect_topic`)
- [x] `deliberation.py` — SignalForge 환기(`_defect_briefing`): alert_check → get_top_issues/daily_briefing 폴백 → query_voc 증거, LLM 연관성 판정
- [x] `deliberation.py` — 연관 시 심의 base 프롬프트에 `[최근 고객 불만 신호 (SignalForge)]` 블록 주입, RA blocks.background에도 포함
- [x] `deliberation.py` — SSE 계약 정합: `token{delta}` + `result{type:'text',content}` (기존 `token{content}`+`text`는 프론트가 못 읽음)
- [x] 검증: 불량 화두 → SSE에 SF 환기 단계 등장 / 비불량 화두 → 환기 스킵 / 심의 완주 + RA 보고서 id

## Frontend (HWAXPortal/frontend)

- [x] `state/chatStore.ts` — 저장 키 prefix 파라미터화(기본 `hwax.chat`, 기존 호출자 무변경)
- [x] `state/ChatContext.tsx` — `storagePrefix`/`sendPrefix` props(기본값이 기존 동작)
- [x] `pages/DeliberatePage.tsx` — 심의 전용 페이지(ChatPage 패턴, 화두 예시 칩, 흐름 안내)
- [x] `App.tsx` — `/deliberate` 라우트(중첩 ChatProvider: prefix=`hwax.delib`, sendPrefix=`/심의 `)
- [x] `AppHeader.tsx` — 네비에 '심의' 메뉴
- [x] `AppShell.tsx` — `/deliberate`에서 플로팅 ChatDock 숨김
- [x] 검증: 빌드 통과, 메뉴/페이지 렌더, 심의 기록이 `hwax.delib.*`에만 저장(챗 이력과 분리), 스트림 표시

## Claude MCP 경로(코드 0 — 문서)

- [x] `docs/DELIBERATION-PIPELINE.md` — 불량 환기 절차(단계 2 앞단: SF 조회 → `args.context`로 전달) 명시

## 마무리

- [x] 레포별 시맨틱 커밋(HWAXAgentServer / HWAXPortal)
- [x] 메모리 갱신(hwax-deliberation-pipeline)
