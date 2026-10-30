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
- [x] prompts `routine-<루틴 id>`(남이 쓴 제목은 «…» 데이터로) · `_INSTRUCTIONS` 12번(10-30, R3 와 함께)
- [x] 포털 실행 원장(실행 · 단계 · 호출 표) · 단계 닫기(원장과 맞대기) · 고르기 · 근거 · 보고서 렌더 · RA 초안(게이트웨이가 호출자 이름으로 — 토큰 없으면 건너뛰고 까닭을 원장에)
- [x] 시험 — 게이트웨이(가짜 포털로 울타리 · 원장 · 쪽 · 심의 근거 · RA 셋 · 낡은 포털 · 읽기 전용) · 포털(실행 원장 전부 · RA 나눔 계약)
- [ ] 각본 MCP 클라이언트로 포털 + 게이트웨이를 끝까지 한 번(실물) — dev 재기동(사용자 확인) 뒤 또는 cae00 R5 에서. 계약은 가짜 · 블랙박스 시험이 본다

## R3 Qwen 길

- [x] 에이전트 서버 `routine.py` — 단계 하위 실행(허용 목록만 묶은 작은 ReAct — 캐시 없는 단계마다 새 묶음) · 봉투는 도구 없는 따로 턴 · 단계 상태는 코드가 → 포털이 원장과 맞대
  고침 · 확정 종결 · 새어 나온 호출 직접 실행은 루틴에 없다(울타리 밖 길이라 쓰지 않는다 — R3-D3)
- [x] 떼어 낸 작업 · 다시 붙기(같은 사람만) · 단계마다 원장 · 이어서(새 PAT · 앞 프로세스의 심의 잡 다시 쓰기) · 동시 상한 · `/health` routine_active · routine_parked ·
  update-all 기다림(쉬는 루틴은 안 센다) — interrupted 자동 표시는 안 한다(R3-D8)
- [x] 포털 중계 — `ChatRequest.routine` 두 곳 선언(AST 시험) · 긴 idle · 브라우저가 떠나도 끝까지(동시 8) · meta.routine 포인터 · 빈 답에도 포인터 · 같은 답 한 번 ·
  `from_chat.record` 건너뜀(루틴 호출 원장이 따로 — trigger_kind=routine 항목은 R2 의 원장 분리로 바뀌었다)
- [x] 화면 — RoutinePicker(입력창 · 변수 형 · 거절해도 값이 남는다) · RoutineView(단계 칩 · 요약 · 고르기 · 이어서 · 한 번에 멈춤 · RA 초안 올리기 · 보고서 보기 · 화면 밖은 안 읽는다)
- [x] 시험 — 구현자 시험 + 설계서만 읽고 쓴 블랙박스(에이전트 · 화면 순수 함수) + 머리 없는 브라우저(실제 ChatProvider) · 고침마다 변이 시험 · 반대 검토 두 라운드
  (10-30 — 포털 3,726 · 에이전트 2,802 + 83 · 게이트웨이 712 통과)

## R4 보고서

- [x] 절 쓰기(단계 절은 포털이 봉투로 — 준 글에 있는 발견은 다시 안 붙인다) · 인사이트 인용 · 출처 없는 수치면 한 번 고쳐 쓰기 · 근거 부록 · 커버리지 · 출처 없는 수치 표지
- [x] RA 초안(`deliberation` v1 블록 · `_ra_blocks` 계약 시험 · ask 는 챗의 'RA 초안 올리기' · 이미 올렸으면 다시 안 만든다) — 대화 `kind=routine` 은 만들지 않는다(R3-D10)
- [ ] 이력(changelog) · CLAUDE.md 문서 표 · cae00 안내(`server-setup.md`) · 화면 Drive

## R5 cae00 받아들이기(사람)

- [ ] 예시 연쇄 한 번 — 단계별 토큰 · 시간 · 캐시 적중 · 커버리지를 10-29 기준선과 견준다
