# 띵킹 모드 체크리스트

정본 계획은 [PLAN.md](PLAN.md), 판단 근거는 [context-notes.md](context-notes.md).

## P0 — 엔진

- [x] `HWAXAgentServer/thinking.py` 신규 — 소집·예심·본심·위임·종합 5단
- [x] 후보 소집 `_summon` — `recommend_agents` 를 `CATALOG_RESULT_MAX` 로 부른다(절단 금지)
- [x] 예심 `_screen` — `agent_search(mode="semantic")` 병렬, 탈락은 AND 조건
- [x] 본심 `_judge_one` — 좌석 1콜, `{verdict, scope, answer, basis, refer}` 파싱
- [x] 위임 `_handoff` — `refer` 명사구로 재소집, 기존 키·도메인 제외
- [x] 종합 `_summary_text` — 코드가 조립, LLM 미경유
- [x] 동시성 세마포어 `THINK_CONCURRENCY`
- [x] 좌석 1콜 `asyncio.wait_for` 상한
- [x] 모든 종료 경로가 `result` → `done` 으로 닫힌다
- [x] 게이트웨이 불통 시 `error` 아닌 안내 텍스트 + `done`(`run_agent_search` 관례)

## P0 — 배선

- [x] `app.py` `ChatRequest.thinking: bool = False`
- [x] `app.py` `is_thinking` / `strip_thinking_trigger`
- [x] `app.py` `/chat` 디스패처 분기 — 명시 슬래시 트리거보다 **뒤**, 일반 챗보다 앞
- [x] 포털 `backend/app/agent/routes.py` `ChatRequest.thinking` 선언 + 포워딩
- [x] 프론트 `types/chat.ts` — `ThinkEvent` 타입, `Message.think`
- [x] 프론트 `api/chat.api.ts` — `StreamHandlers.onThink`, `dispatch` case, 요청 바디
- [x] 프론트 `state/ChatContext.tsx` — 상태·ref·setter·provider·`sendMessage`·`mergeThink`
- [x] 프론트 `components/chat/ThinkPanel.tsx` 신규 + `Composer.tsx` 배치(두 페이지 공용)
- [x] 프론트 `components/chat/ThinkView.tsx` 신규 — 좌석별 답변·기권 렌더
- [x] 프론트 `components/chat/MessageList.tsx` — `ThinkView` 끼우기 + `emptyDone` 조건
- [x] 프론트 `state/chatStore.ts` — 영속(직렬화·복원·`filter` 조건)
- [x] 프론트 `styles/chat.css` — `.tv-*` 스타일

## P1 — 검증

- [x] `HWAXAgentServer/test_app.py` 또는 신규 테스트 — 트리거 판정·파싱·예심 규칙
- [x] 실주행 1: 풀에 전문성이 **있는** 질의 → 답변 ≥1, 기권 사유 표시
- [x] 실주행 2: 풀에 전문성이 **없는** 질의(OCA 산소 확산) → 전원 기권 + 그 사실 표기
- [x] 실주행 3: 위임이 실제로 새 좌석을 데려오는 질의
- [x] 프론트 빌드 `cd frontend && pnpm build`
- [x] agent-server 재기동 후 SSE 프레임 실측(`event:`/`data:` 형식·저장 스니퍼 통과)

## P2 — 문서·마무리

- [x] `docs/thinking-mode/context-notes.md` 계속 append
- [x] `CLAUDE.md` 문서 색인에 모드 추가
- [ ] 커밋 분할 — 엔진 / 배선 / 프론트 / 문서

## 별건 — 사용자 지시로 이어서 처리 (2026-09-09 완료)

- [x] `_capture`/`_capture_b` 의 `startswith(b"data:")` 가 항상 거짓 — `/시뮬심의` 웹
      경로가 1단에서 죽던 것. SSE 문자열 파싱을 걷어내고 코어가 `out: dict` 를 직접
      채우게 했다(`a984d2b`). 실주행 확인 — 1단 결정문 2,253자 → 2단 좌석 11인 진입
- [x] `agent_search` 지연 — 원인이 둘이었다. ⓐ `hybrid_search` 가 범위를 SQL 이 아니라
      파이썬으로 걸어 코퍼스 전체를 훑고 상위 N 이 범위 밖에서 정해졌다(정확성 문제이기도
      했다 — FTS 절반이 0건 기여). ⓑ `to_tsvector` 식에 GIN 인덱스 부재.
      AIDataHub `bf57f06`(범위 SQL 화) + `15612b2`(0031 GIN 인덱스).
      실측 fts 221.4초 0건 → 0.3초 6건, hybrid 102.5초 3건 → 0.5초 6건
- [x] 호출부가 느린 검색을 상정하게 — `_agent_search_hits` 공용 헬퍼(타임아웃·semantic
      폴백·삼켜진 오류 판별·강등 가시화)로 심의·챗·띵킹 세 곳을 통일(`132c956`)
- [ ] `app.py:2624` `recd` 스코프 — `expert_tools` 가 조용히 빈다(아직 미확인·미수정)


## 남은 것

- [ ] 브라우저 렌더 실측 — 로그인 자격이 없어 못 했다(D6). 데이터 경로는 전부 확인됨.
- [ ] `test_app.py::test_agent_for_caches_by_group_set` 사전 실패 — 가짜 `app.state` 에
      `tool_snapshot` 이 없다. 내 변경과 무관하고(변경 전에도 실패) 고치지 않았다.
