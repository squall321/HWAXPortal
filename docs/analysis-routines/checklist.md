# 분석 루틴 — 체크리스트

계획 `PLAN.md` · 판단과 까닭 `context-notes.md`. 단계마다 시험을 먼저 쓰고, 다른 리포를 건드리는 계약은 양쪽 시험이 다 돈 뒤에 커밋한다.

## R0 결정 · 계약

- [x] 조사 넷 — 절차 기능 · 챗 루틴 모드 · MCP 길 · 예시 연쇄의 플랫폼 지도(10-29, 읽기만)
- [x] 계획 `PLAN.md` · 이 체크리스트 · `context-notes.md`(10-29)
- [x] 사용자 결정 — Q1 저절로 · Q2/Q4 건너뛰고 끝까지 · Q7 둘 다(10-30, C-7) · 나머지는 권고 기본값
- [x] `contracts.md` — 스펙 · 상태 · 단계 봉투 · /routines-api · MCP 도구 · SSE · 보고서 렌더(10-30) — 스펙의 정본은 `app/procedures/routines.py`
- [x] 계약 시험 — 공유 JSON 대신 실물 맞대기로 했다(R2): 포털 RA 나눔 ↔ 엔진 `_ra_split` 원문 · 게이트웨이 시험의 계획 꼴 = 포털 run_view 꼴 · 에이전트 거부 목록

## R1 포털 — 짜고 저장하기

- [x] 저장 — `routines` · `routine_versions`(불변, 같은 `procedures.sqlite`) — 실행 · 단계 표는 R2
- [x] 검증 — 스펙 꼴 · 참조(`{{var}}` · `{{steps.<id>.<key>}}` · `{{run.started}}`) · 앞 단계만 · 단계 안 쓰기 금지 · 비밀처럼 생긴 글 · YAML 1.1 함정(C-8)
- [x] 준비도 — 단계마다 allowed · denied · not_connected · unavailable · 없는 도구
- [x] `/routines-api` — health · platforms · 목록 · 읽기 · 판 더하기(주인만) · 보관 · 준비도 · 검증 · YAML 내보내기/가져오기, 쓰기는 세션 + CSRF · 읽기는 PAT 도
- [x] 권한 키(Q5) — `access.yaml` 기능 `routines` · 라우트 전수 403 시험
- [x] 절차 탭 '루틴' — 목록 · 보기(판 · 준비도 표지) · 편집기(내 권한의 플랫폼 · 도구 고르기 · 위로 · 아래로 · 할 일 · 앞 단계 · 넘길 키 · 예산 · 막히면 · 보고서 · 공개) · YAML 가져오기, 임시 포털 캡처
- [x] 예시 루틴 둘 — `examples/market-defect.yaml`(cae00, Q7 둘 다) · `examples/dev-demo.yaml` — 시험이 저장 검증을 돌린다

## R2 게이트웨이 · Claude 길

- [x] `routine_list` · `routine_get` · `routine_run_start` · `routine_call` · `routine_step_done` · `routine_report_submit`(호출자 PAT 를 포털로 — 게이트웨이 공유 비밀은 거절)
- [x] `routine_call` — 단계 울타리 `{백엔드: [원래 이름]}` · 정상 호출 길 그대로(절차 면제 없음) · 원장 기록 · corr `routine:<실행>:<단계>` · 큰 결과는 쪽 · 같은 이름은 `백엔드:이름` · 심의 근거 채움
- [x] `/tools-map`(`_gateway` 수) · 영역표(앱 단위 system) · 읽기 전용 PAT 규칙 · 일반 챗 거부(에이전트 `_ROUTINE_TOOLS`)
- [ ] prompts `routine-<slug>` · `_INSTRUCTIONS` 한 항목 — R3 뒤(도구 설명이 순서를 이미 말한다)
- [x] 포털 실행 원장(실행 · 단계 · 호출 표) · 단계 닫기(원장과 맞대기) · 고르기 · 근거 · 보고서 렌더 · RA 초안(게이트웨이가 호출자 이름으로 — 토큰 없으면 건너뛰고 까닭을 원장에)
- [x] 시험 — 게이트웨이(가짜 포털로 울타리 · 원장 · 쪽 · 심의 근거 · RA 셋 · 낡은 포털 · 읽기 전용) · 포털(실행 원장 전부 · RA 나눔 계약)
- [ ] 각본 MCP 클라이언트로 포털 + 게이트웨이를 끝까지 한 번(실물 — R3 과 함께)

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
