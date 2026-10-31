# 심의 엔진 운영 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 요청서 [request.md](request.md) · 결정 [context-notes.md](context-notes.md).

## 엔진(HWAXAgentServer)
- [x] R4 한도 셋을 판정 때마다(박스 파일 > env) · `GET · POST /limits` · 올리면 줄 띄우기 · `/health` 의 `limits` — 엔진 `2e5dad6`(DO-D3)
- [x] R4' 좌석 합 상한 `max_seats_running`(기본 꺼짐) · 앉기 전 어림 · 앉으면 다시 보기 · 혼자 예외 · 차례 지키기 — 엔진 `43234c6`(DO-D16)
- [x] R3 보강 — 이어하기 요약을 좌석 몫으로(엔진 `8c37ba2`, DO-D15)
- [x] R5 `LLM_CONTEXT_TOKENS` 상한 · 주기 재조회(뒤에서) · 여러 번 물어 작은 값 · `/health` 출처 — 줄일 때만 받는다, 엔진 `41a3996`(DO-D4)
- [x] R1 비우기 클래스에 범위 매개변수 · 심의 멈춤 파일(`scope: delib`) · MCP 두 도구 거절 · 웹 세 트리거 거절(앱 패널 빼고) · 줄 붙잡기 · 주기 펌프 · `/drain` · `/health` — 엔진 `e7df642`(DO-D5)
- [x] R2 시작 인자 파일(0600, 토큰 없음) · 끝나면 지우기 · 재기동 뒤 줄 다시 세우기(순서) · `/health` 의 `delib_queue_durable` · `delib_requeued` · 정상 종료는 interrupted — `e7df642`(DO-D6 · DO-D7)
- [x] R3 끊긴 잡에 끝난 라운드 수 · `deliberate_continue` 가 끊긴 잡을 받는다(의견 없이) · 남은 라운드만 · 시작 인자 재사용 — `e7df642`(DO-D8~D10)
- [x] R2' 에이전트 `start.sh` 재기동 판정 — 줄을 넘기는 판이면 줄 선 수를 빼고 센다 — `1567dba`(DO-D11)
- [x] 시험 · 변이 · 엔진 전체 시험(2,554) · 포털 계약 시험(엔진을 읽는 1,031 — 실패 둘은 기존 환경 탓 EC-D6) · 엔진 올림(10-22)

## 운영 스크립트(HWAXPortal)
- [x] R2' `lib/delib-busy.sh` — 같은 규칙(DO-D11) · 계약 시험 ⊆(DO-D14)
- [x] O1 재기동할 일이 있고 심의가 돌면 멈춤 세우기 · `HWAX_DELIB_WAIT_S` 기다리기 · 끝에서 내리기 — update-sites 에이전트 갈래 + update-all 끝맺음(표지 파일, DO-D12)
- [x] O2 재기동 뒤 다시 선 줄 수 — 이번에 다시 떴을 때만(DO-D13)
- [x] 셸 시험 — `test_delib_pause_ops` 35 · 셸 묶음 392 · 포털 전체 3,239 · 변이 17

## 문서 · 올리기
- [x] README(엔진) · 운영 절차(사람이 멈춤 · 한도를 쓰는 법 — [server-setup.md](server-setup.md)) · risk-200k 절차서 4절의 엔진 판 조건
- [x] 업데이트 이력 · CLAUDE.md 행 · 기억 — 풀림 `07a75b3`(CLAUDE.md 행 · 업데이트 이력 10-22 셋) · `284e604`(좌석 합 상한 항목) · 기억 hwax-delib-ops (10-31 정리)
- [x] push(엔진 · 포털) — 풀림 엔진 `e7df642` · `43234c6` · `41a3996` · `2e5dad6` · `8c37ba2` · `1567dba` · `bb307c6` 와 포털 `5ea295d` · `07a75b3` · `284e604` 가 origin 에 있다 · cae00 기준 판 `969e723` · `aec8e29` 도 품는다 (10-31 정리)
