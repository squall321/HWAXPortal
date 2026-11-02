# 운영 현황 — 체크리스트

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## M0. 계획 · 물음(dev — 11-02)
- [x] 조사(읽기만) — 이용 통계 원천 · LLM/GPU 원천 · 셋 다 근거 줄(OD-1 · OD-2)
- [x] 계획서 · 받은 편지함 물음(`../cae00-inbox/2026-11-02.md`)
- [x] 사용자 결정 — 합계도 관리자만 · 호스트 수집기(OD-4, 11-02) — 나머지는 권장 기본값
- [ ] cae00 답(받은 편지함 Q1 ~ Q12) — 사용자를 거쳐

## 이용 통계
- [ ] M1 — 포털 안 원장으로 S 지표 · 관리자 API · `/admin/usage` 화면 · `agent_audit` ts 색인 · 예열 줄 · 시험 계정 빼기 · 시험 격리 · 이력
- [ ] M2 — `usage_daily` · `usage_actor_daily`(agent_audit.sqlite 안) · lifespan 접기 · 되채우기 · 게이트웨이 `/usage-rollup` · 에이전트 서버 창구 · nginx 날마다 접기 · MCP · 심의 · RA 칸 · DAU/WAU/MAU
- [ ] M3 — 2단계 (가) 턴 종류 · 모델 (나) 날마다 PAT · 연결 수 (다) 에이전트 토큰(결정 뒤) (라) 게이트웨이 PAT 종류 · 엔진 호출 주인 · 리스크 토큰 · (정하면) 합계 공개 · 내 이용
- [ ] cae00 절차서 · 반대 검토

## LLM/GPU 현황
- [x] M1 — 수집기(HTTP · 해석기 · sqlite · 가짜 vLLM 시험 · 라우터 해석기와 같은 결과) — dev 11-02, 가지 `wt1102/llm-status`(OD-13 ~ OD-22 · OD-24)
  - [x] `infra/llm-status/`(collector · promtext · samplestore) · `infra/scripts/llm-status.sh`(run · start · stop) · 포트 8760(PORT-MAP · OD-14)
  - [x] 시험 — 해석기 · 라우터와 같은 셈 · 분위수 · 리셋 빈칸 · 히스토그램 창 · 401 · 걸린 서버 · 연결 거부/시간 초과 · 틀린 지표 · 값 꼴 · 낡음 · 숨기지 않음 ·
        키 가리기 · 기본 대상 · 짝 파일 · 에이전트 · 라우터 · 시계열 · 지우기 · 띄우는 스크립트 · 격리, 한 줄 변이 25개가 모두 잡힌다(스크래치 사본)
- [ ] M2 — 포털 API · `/admin/llm-status` · update-all 배선(끄면 '꺼짐' 한 줄) · 이력 · 문서
  - [x] 매니페스트 `if_env: LLM_STATUS`(기본 꺼짐 · 제 파일만의 지문) · update-all 5d(켜면 update-sites · 끄면 ○ 와 떠 있으면 내림) · 예시 설정 · env-sync 는 선택으로
  - [x] 포털 `GET /auth/admin/llm-status` · `/series`(관리자만 — CAEG 도 403 · 꺼짐 503 · 안 닿음 502) · start.sh 가 `LLM_STATUS_URL` 을 넘긴다(OD-15)
  - [x] 화면 `/admin/llm-status`(관리 메뉴) — 머리 · 서버 카드 · 복제본 표 · 라우터 · 지금 쓰는 일 · Slurm/GPU 모름 줄, 브라우저 시험(실제 수집기 답)
  - [x] cae00 절차서 [server-setup.md](server-setup.md)
  - [ ] 이력(backend/config/changelog.yaml) — 이 가지에서는 쓰지 않았다(올리는 세션이 함께 적는다)
- [ ] cae00 에서 켜고 확인 — 사람(server-setup.md 2 ~ 5절) · 받은 편지함 Q4 · Q5(서버별 주소) · Q7(짝 파일) · Q12 1번(긁는 주기)
- [ ] M3 — Slurm 잡 표 · 남은 때(답 뒤 · cae00 에서만 확인)
- [ ] M4 — GPU 하드웨어(dev nvidia-smi · stcx 표본은 사람이 sbatch 에 넣은 뒤 · GLM 은 그 팀이 줄 때)
- [ ] M5(선택) — 에이전트 서버 안 서버별 지연 · 오류 고리
- [x] 반대 검토(M1 · M2, 11-02) — MEDIUM 둘 · LOW 열 · INFO 둘. cae00 절차서는 M2 에서 썼다(server-setup.md). 고침은 아래(OD-26 ~)
  - [x] 결정 번호 — 이 가지의 OD-5 ~ OD-17 을 OD-13 ~ OD-25 로(이용 통계가 main 에서 OD-5 ~ OD-12 를 먼저 썼다)
  - [x] 묶음 주소의 속도 · 분위수 — 같은 서버 프로세스(process_start_time_seconds)의 표본끼리만 · 표지가 없으면 줄면 그 창을 비운다(OD-26)
  - [x] 되돌린 쓰기의 계열 번호 — 캐시는 COMMIT 된 줄만(OD-27)
  - [x] 꺼진 5d — /health 의 service 표지로 수집기를 알아보고 남의 앱이면 ○ 한 줄만(llm-status.sh probe · OD-28) · cae00 8760 확인은 사람(server-setup.md 2절)
  - [x] 재기동 생략 · start 의 '이미 떠 있다' — stop 과 같은 명령줄 판정(llm-status.sh check · update-sites 는 llm-status 만, OD-29)
  - [x] 오류 — HTTP 5xx 답 · 오류로 끝난 요청을 따로(더하면 한 요청을 두 번 센다 · 카드 · 저장 · 가짜 · 화면 시험, OD-30)
