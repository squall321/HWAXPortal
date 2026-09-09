# 전문가 페르소나 챗 — 체크리스트

PLAN.md 의 ①~④ 를 순서대로. 확인란은 **실제로 확인한 것**만 체크한다.

## 0. 준비

- [x] `colorOf`/`initialOf` 를 `components/chat/personaColor.ts` 로 분리 — 심의와 챗이 같은 함수를 쓴다
- [x] `DelibView.tsx` 가 그 모듈을 임포트하도록 교체(로컬 사본 제거)

## 1. 계약 — 사람 이름과 '누가 답했나'를 실어 나른다

- [x] `types/chat.ts` — `Message.persona?: {key, name?}`
- [x] `types/chat.ts` — `AgentCatalog`(SSE `agents` payload) + `Message.agentCatalog?`
- [x] `types/chat.ts` — `Conversation.pinnedAgentName?`(표시용 이름. 서버 계약은 여전히 key)
- [x] `chat.api.ts` — `onAgents` 핸들러 + `case 'agents'` (죽어 있던 채널 연결)
- [x] `chatStore.ts` — `persona`·`pinnedAgentName` 영속. `agentCatalog` 는 **저장하지 않는다**
      (풀 762명 × 메시지수 → 쿼터. `toolCatalog` 도 같은 이유로 저장 안 한다)
- [x] `ChatContext.tsx` — `pinnedAgentName`, `setPinnedAgent(key, name?)`, 전송 시 `persona` 스탬프

## 2. 오른쪽 레일 '현재 전문가' (사용자 제안 2)

- [x] `ActivityPanel` 이 활동이 없어도 살아 있게 — 조기 반환 조건 변경
- [x] `act-head` 바로 아래 `PersonaBar` — 아바타·사람 이름·키, `바꾸기`/`해제`
- [x] 미지정이면 "일반 어시스턴트" + `전문가 고르기`

## 3. 거기서 바로 고르기 (사용자 제안 2)

- [x] `PersonaPicker.tsx` — 포털 모달(라이트박스와 같은 이유: `transform` 조상 함정)
- [x] 이름·키 즉시 필터(로컬) + Enter 로 주제 추천(서버 `/deliberate/experts`)
- [x] 고르면 `setPinnedAgent(key, name)` — 다음 발화부터 적용

## 4. 페르소나 말풍선 (사용자 제안 3)

- [x] `MessageList` — `msg.persona` 가 있으면 아바타+이름+색 테두리로 그린다
- [x] 심의·띵킹 메시지에는 붙이지 않는다(그쪽은 자기 뷰가 있다)
- [x] 색은 `personaColor` — 심의 회의록과 같은 사람이면 같은 색

## 5. '/전문가' 검색 결과 선택 (④)

- [x] `AgentCatalogBlock.tsx` — 추천/분야별 목록에서 바로 지정
- [x] `MessageList` 에 연결

## 6. 곁가지

- [x] `Composer` 지정 칩이 키 대신 **사람 이름**을 보여준다
- [x] `StartPicker` 가 이름까지 넘긴다
- [x] `chat.css` — `.pb-*`, `.pp-*`, `.msg-persona*`, `.ac-*`

## 7. 검증

- [x] `pnpm build` 통과(타입·번들)
- [x] 임시 vite 진입점으로 실제 컴포넌트 렌더 — `validateDOMNesting` 경고 0
- [x] 실제 포털에서 전문가 지정 → 발화 → 말풍선 → 새로고침 후에도 유지
- [x] 심의 화면에서 같은 사람이 같은 색인지 대조
