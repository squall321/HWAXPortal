# 분석 루틴 — 체크리스트

계획 `PLAN.md` · 판단과 까닭 `context-notes.md`. 단계마다 시험을 먼저 쓰고, 다른 리포를 건드리는 계약은 양쪽 시험이 다 돈 뒤에 커밋한다.

## R0 결정 · 계약

- [x] 조사 넷 — 절차 기능 · 챗 루틴 모드 · MCP 길 · 예시 연쇄의 플랫폼 지도(10-29, 읽기만)
- [x] 계획 `PLAN.md` · 이 체크리스트 · `context-notes.md`(10-29)
- [ ] 사용자 결정 Q1 ~ Q10(PLAN 8절) — 받은 답을 context-notes 에 적는다
- [ ] `contracts.md` — RoutineSpec JSON Schema · 단계 봉투 · SSE `routine` 이벤트 · MCP 도구 입출력
- [ ] 계약 시험 뼈대(포털 · 게이트웨이 · 에이전트가 같은 스키마 파일을 읽는다)

## R1 포털 — 짜고 저장하기

- [ ] 저장 — `routines` · `routine_versions`(불변) · `routine_runs` · `routine_stages`(같은 `procedures.sqlite`, 새 표)
- [ ] 검증 — 스펙 꼴 · 참조(`{{var}}` · `{{steps.<id>.<key>}}`) · 플랫폼 id 가 권한표에 있나 · 단계 안 쓰기 금지 · 비밀 상수
- [ ] 준비도 — 단계마다 이 사람이 부를 수 있나(권한 · 연결 토큰 · 이 박스 게이트웨이에 있나)
- [ ] `/routines-api` — 목록 · 읽기 · 판 더하기(주인만) · 공개 범위 · YAML 내보내기/가져오기 · 세션과 PAT 둘 다
- [ ] 권한 키(Q5) — `access.yaml` 기능 줄 · 시험
- [ ] 절차 탭 '루틴' 편집기 — 내 권한 · 이 박스의 플랫폼만 고르기 · 순서 끌기 · 할 일 · 기대 출력 · 정책 · 보고서 절 · 판 · 준비도 미리 보기
- [ ] 예시 루틴 둘 — cae00 시장불량 연쇄 · dev 시연 연쇄(SignalForge → 심의 → DynaForge → 보고서)

## R2 게이트웨이 · Claude 길

- [ ] `routine_list` · `routine_get` · `routine_run_start` · `routine_call` · `routine_step_done` · `routine_report_submit`(호출자 PAT 를 포털로)
- [ ] `routine_call` — 단계 울타리 · `invoke_tool` 검사 그대로(절차 면제 없음) · 원장 기록 · `corr=run_id` · 큰 결과는 쪽
- [ ] prompts `routine-<slug>` · `_INSTRUCTIONS` 한 항목(포털이 답할 때만) · `/tools-map` · 영역표 · 읽기 전용 PAT 규칙
- [ ] 포털 실행 원장 · 보고서 렌더 · RA 초안(게이트웨이가 호출자 이름으로 — 토큰 없으면 거부)
- [ ] 시험 — 각본 MCP 클라이언트로 끝까지 · 울타리 밖 도구 거부 · 판 엇갈림('포털이 낡았다')

## R3 Qwen 길

- [ ] 에이전트 서버 `routine.py` — 단계 하위 실행 · 허용 목록 묶음(캐시 키에도) · 확정 종결 · 새어 나온 호출도 허용 목록 안 · 단계 상태는 코드가
- [ ] 떼어 낸 작업 · 단계마다 원장 · 이어서(새 PAT) · interrupted · 동시 상한 · `/health` routine_active · update-all 기다림
- [ ] 포털 중계 — `ChatRequest.routine` 두 곳 선언 · 긴 idle · 브라우저가 떠나도 끊지 않음 · meta 저장 · 원장(trigger_kind=routine)
- [ ] 화면 — RoutinePicker(입력창) · RoutineView(단계 칩 · 단계별 호출 · 문 · 이어서)
- [ ] 시험 — 가짜 LLM 이 호출 없이 '했다' → skipped · 도구 ⊆ 허용 · SSE 계약(에이전트 ↔ 포털 ↔ TS)

## R4 보고서

- [ ] 절 쓰기 · 인사이트 인용 · 자기검증 한 번 · 근거 부록 · 커버리지 · 출처 없는 수치 표지
- [ ] RA 초안(`deliberation` v1 블록 · `_ra_blocks` 계약 시험) · 대화 `kind=routine`
- [ ] 이력(changelog) · CLAUDE.md 문서 표 · cae00 안내(`server-setup.md`) · 화면 Drive

## R5 cae00 받아들이기(사람)

- [ ] 예시 연쇄 한 번 — 단계별 토큰 · 시간 · 캐시 적중 · 커버리지를 10-29 기준선과 견준다
