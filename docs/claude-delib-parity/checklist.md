# Claude 길 심의 기능 맞추기 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

## P1 좌석 자유 조회 — 글 왕복 ReAct (엔진)
- [x] `_TextReactAgent` — create_react_agent 와 같은 astream 꼴(도구 호출 AIMessage · ToolMessage), CALL 줄 읽기 · 예산 · 모르는 도구 · 깨진 줄 · 백틱 줄(CP-D6)
- [x] 외부 길의 free_tools 강제 해제 · 자유 조회 준비 · 좌석 에이전트를 글 왕복으로(external_closed · external_forced 걷음)
- [x] 표지 — 외부 실행 카드 · 결과 프레임 · 잡 기록 tool_mode(tools / evidence_only — CP-D4)
- [x] 시험 — 가짜 일꾼이 CALL 줄로 답해 엔진이 도구를 실행하고 근거 · 공용 풀 · 발언 턴에 든다, 예산 · 깨진 줄 · 끄기(free_tools=0) · 도구 없음 · 계약 예제 seat_lookup
- [x] 변이 27 · 엔진 전체 시험 2,481 + 루트 83

## P2 일반 심의를 워크플로가 맡는다 (엔진 · 포털)
- [x] 심의 잡 id 를 외부 과제 머리에(job_id — MCP 잡만)
- [x] 워크플로 `jobId(s)` — 맡은 잡의 과제만 · 답 지시에 CALL 줄 꼴 · 시험 37

## P3 그림 (엔진)
- [x] 외부 길 상태 줄 — 그림은 판독문으로 간다고 · 시험

## P4 리스크 앱 패널 잡을 Claude 로 (리스크 앱)
- [x] 패널 잡 llm=claude(동의 · 그 사람 PAT · external_llm 확인 · external_worker 보류 · 감사 · 살아 있는 잡 differs — CP-D7)
- [x] 엔진 tool_mode 를 받아 적기(보고서 판단 LLM 줄 · 통합 보고서 llm=external) · 시험 · 변이 14

## P5 문서
- [x] MCP 안내(엔진 · 리스크 앱) · 심의 메뉴 limits_external(C5 — CP-D9) · README 외부 응답자 절 · risk-claude-engine PLAN 5절 · 업데이트 이력 · CLAUDE.md
- [ ] 프론트 요청 — 리스크 앱 웹 패널 잡 만들기에 Claude 선택(다른 세션 몫, [frontend-request.md](frontend-request.md))
- [ ] 사람 몫 — dev 에이전트 서버 재기동(확인 뒤) · cae00 update-all
