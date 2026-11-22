# 운영 현황 — 체크리스트

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## M0. 계획 · 물음(dev — 11-02)
- [x] 조사(읽기만) — 이용 통계 원천 · LLM/GPU 원천 · 셋 다 근거 줄(OD-1 · OD-2)
- [x] 계획서 · 받은 편지함 물음(`../cae00-inbox/2026-11-02.md`)
- [x] 사용자 결정 — 합계도 관리자만 · 호스트 수집기(OD-4, 11-02) — 나머지는 권장 기본값
- [ ] cae00 답(받은 편지함 Q1 ~ Q12) — 사용자를 거쳐

## 이용 통계
- [x] M1 — 포털 안 원장으로 S 지표 · 관리자 API `GET /auth/admin/usage` · `/admin/usage` 화면 · `agent_audit` ts 색인 · 예열 줄 · 시험 · 서비스 계정 빼기(`USAGE_EXCLUDE_ACCOUNTS`) · 시험(격리 — 새 저장소 · 경로 없음, 한 줄 변이) — 가지 `wt1102/usage-stats`(11-02, OD-5 ~ OD-11)
- [ ] M1 이력(`backend/config/changelog.yaml`) — 병합 때 사용자 세션이 쓴다
- [ ] M1 cae00 확인 — 반영 뒤 관리자 화면의 숫자를 받은 편지함 Q1(원장마다 행 수 · 기간 · 사람 수)과 맞대고, 시험 · 서비스 계정이 있으면 `backend/.env` 의 `USAGE_EXCLUDE_ACCOUNTS` 에 적는다(dev 숫자는 cae00 숫자가 아니다)
- [x] M2 — 날마다 접는 표와 접기 · 창구 둘 · 접어 둔 표에서 읽는 칸 · 화면 — dev 11-21, 가지 `wt1121/usage`(세 리포 · OD-41 ~ OD-48)
  - [x] 표 — `usage_daily` · `usage_actor_daily`(400일) · 접은 기록 `usage_fold`(agent_audit.sqlite 안 — 새 경로 설정 없음, OD-41)
  - [x] 접기 `backend/app/usage_fold.py` — 기동 30초 뒤 · `USAGE_FOLD_S`(기본 3600 · 0 끔)마다 · 오늘은 돌 때마다 · 끝난 날은 사흘 뒤 닫음 · 400일 되채우기 · 멱등(OD-42)
  - [x] 원천 다섯 — portal(사람 줄 · 새 대화 · 낸 PAT) · snapshot(오늘의 PAT · 연결 · 계정 · 허가) · nginx · gateway · agent(OD-43 · OD-47)
  - [x] 게이트웨이 `/usage-rollup`(HWAXMcpGateway `f0090dd` · `9dc69f2` — 읽은 자리 뒤만 접는 `usage-rollup.sqlite` · 20초 기한 · complete 인 답만, OD-45)
  - [x] 에이전트 서버 `/usage-rollup`(HWAXAgentServer `63c0c95` — MCP 심의 잡 · 목록 색인으로만, OD-46)
  - [x] 읽는 칸 — 접기 상태 · 쓴 사람(DAU · WAU · MAU) · MCP(날마다 · 자격 · 앱 · 도구 · 인증 실패 · 개인 Claude 주마다) · MCP 심의 · RA 초안 · 정문 요청 · 날마다 찍은 수 · 접어 둔 새 대화
  - [x] 화면 `/admin/usage` — 카드 여섯 + PAT · 대화 · 권한 카드의 접어 둔 수(OD-48 — 사람의 이메일은 내지 않는다)
  - [x] 뺄 계정 — 사람 줄은 읽을 때 · 합계는 접을 때 · 게이트웨이 · 에이전트는 목록이 바뀌면 다시 접음(OD-44)
  - [x] 시험 — 게이트웨이 25 · 에이전트 서버 12 · 포털 62(접기 29 · 읽는 칸 13 · 화면 카드 4 · 화면 브라우저 4 · 턴 종류 11 · 격리 1), 한 줄 변이 40개가 붉다(하나는 처음에 초록이어서 시험을 더했다 — 탐침의 프레임 상한), dev 원장 사본 · 실제 감사 원장(읽기만)으로 연기 시험
- [ ] M2 이력(`backend/config/changelog.yaml`) — 병합 때 사용자 세션이 쓴다
- [ ] M2 cae00 확인 — 사람([server-setup.md](server-setup.md) 10절): 세 서비스가 새 판으로 뜬 뒤 '접기 상태' 카드에 실패 까닭이 없는지 · 게이트웨이 첫 접기에 걸린 때 · 숫자를 받은 편지함 2026-11-02 Q1 · Q2 와 맞대기 · 시험 · 서비스 계정을 `USAGE_EXCLUDE_ACCOUNTS` 에
- [ ] M3 — 2단계
  - [x] (가) 턴 종류 · 답한 모델 — 중계가 `chat_done` 에 `{kind, models}` · 통계 칸 `chat_kinds`(OD-49 — 포털이 다시 뜬 뒤 끝난 턴부터)
  - [x] (나) 날마다 PAT · 외부 연결 · 계정 · 개별 허가 수 — M2 의 snapshot 원천(OD-50)
  - [x] (다) 에이전트 서버의 사람별 LLM 토큰 — 사용자 결정 2026-11-22(관리자만 · 400일) · `usage_tokens.py` · 창구 `llm` · 포털 `usage_llm_daily` · 카드(OD-53)
  - [x] 엔진 호출의 주인 — 사용자 결정 2026-11-22: 감사 전용 머리 `x-hwax-audit-for`(게이트웨이 감사 줄의 `audit_for` 칸에만 · 동작 불변 시험) · 포털 중계 일곱이 주체의 이메일을 실음 · 갈래 `engine`(OD-52)
  - [x] 사람별 표 — 사용자 결정 2026-11-22: 관리자 화면 '사람별 이용'(이메일이 나오는 유일한 칸 · 400일, OD-55)
  - [ ] 흘려 받는 호출의 사용량(`LLM_STREAM_USAGE`) — cae00 에서 확인 뒤 켠다(사람 · server-setup.md 11절, OD-54)
  - [x] (라) 게이트웨이 PAT 종류 · 합계 공개 · 내 이용 — 짓지 않는다(닫힌 기본값 — 사용자 결정 2026-11-22)
  - [ ] 리스크 토큰 · 리스크 앱의 누구의 일 머리 — 그 리포 세션(OD-56)
- [ ] 반대 검토(M2 · M3 가 나 · 11-22 결정분)
- [ ] 11-22 결정분 cae00 확인 — 사람([server-setup.md](server-setup.md) 11절): 게이트웨이 감사 줄의 `audit_for` · 에이전트 `/health.usage_tokens` · 화면의 LLM 토큰 · 사람별 이용

## LLM/GPU 현황
- [x] M1 — 수집기(HTTP · 해석기 · sqlite · 가짜 vLLM 시험 · 라우터 해석기와 같은 결과) — dev 11-02, 가지 `wt1102/llm-status`(OD-13 ~ OD-22 · OD-24)
  - [x] `infra/llm-status/`(collector · promtext · samplestore) · `infra/scripts/llm-status.sh`(run · start · stop) · 포트 8760(PORT-MAP · OD-14)
  - [x] 시험 — 해석기 · 라우터와 같은 셈 · 분위수 · 리셋 빈칸 · 히스토그램 창 · 401 · 걸린 서버 · 연결 거부/시간 초과 · 틀린 지표 · 값 꼴 · 낡음 · 숨기지 않음 ·
        키 가리기 · 기본 대상 · 짝 파일 · 에이전트 · 라우터 · 시계열 · 지우기 · 띄우는 스크립트 · 격리, 한 줄 변이 25개가 모두 잡힌다(스크래치 사본)
- [x] M2 — 포털 API · `/admin/llm-status` · update-all 배선(끄면 '꺼짐' 한 줄) · 이력 · 문서 — main 병합 11-02
  - [x] 매니페스트 `if_env: LLM_STATUS`(기본 꺼짐 · 제 파일만의 지문) · update-all 5d(켜면 update-sites · 끄면 ○ 와 떠 있으면 내림) · 예시 설정 · env-sync 는 선택으로
  - [x] 포털 `GET /auth/admin/llm-status` · `/series`(관리자만 — CAEG 도 403 · 꺼짐 503 · 안 닿음 502) · start.sh 가 `LLM_STATUS_URL` 을 넘긴다(OD-15)
  - [x] 화면 `/admin/llm-status`(관리 메뉴) — 머리 · 서버 카드 · 복제본 표 · 라우터 · 지금 쓰는 일 · Slurm/GPU 모름 줄, 브라우저 시험(실제 수집기 답)
  - [x] cae00 절차서 [server-setup.md](server-setup.md)
  - [x] 이력(backend/config/changelog.yaml) — 합칠 때 2026-11-02 두 항목(수정 · 기술)
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
  - [x] 읽기 기한 — 머리부터 몸까지 하나 · 지나면 타이머가 소켓을 닫는다(조금씩 흘리는 서버, OD-31)
  - [x] 읽기 스레드를 못 띄우면 — 바쁨을 풀고 그 대상의 까닭으로 · 주기의 나머지 · 정리는 그대로(OD-32)
  - [x] 키 — 그 키의 주소에만(LLM_BASE_URL · LLM_UPSTREAMS / CHAT_LLM_BASE_URL · 복제본) · 루프백 별칭은 같은 주소 · 그 밖에는 싣지 않는다(OD-33)
  - [x] 벽시계가 뛰면 — 앞날의 접은 끝 표지를 당긴다 · 거꾸로 가면 정리가 곧바로 · 모델 목록 주기는 monotonic(OD-34)
  - [x] 에이전트 서버 — 제 기한 12초 · 늦으면 '모름 — 늦음' · 내려감은 연결 거부 · 오류 상태일 때만(OD-36)
  - [x] 대상 이름 agent · router — 받지 않고 까닭과 함께 남긴다(OD-37)
  - [x] 감시 — watch: true(heal 이 if_env 를 따른다 — 끈 박스는 그대로, OD-38)
  - [x] 짝 파일 자리 — 리포 밖이나 infra/.state/ 아래(update-all §1 의 stash -u, 문서만 · OD-39)
  - [x] 서버별 주소의 키 표지 `#glm` · `#chat` — OD-33 뒤로 서버별 GLM 대상이 창을 잃던 것(OD-40)
