# 체크리스트 — 자동 파이프라인

> 계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 파악 · 결정

- [x] 개념 제안(11-26) — 감지 · 규칙 · 해석 앱 계약 · 원장 · 보고서 다섯 층
- [x] 사용자 결정 다섯(11-27 — AP-D1 ~ AP-D5, 모두 권장안)
- [x] RA 시스템 연계 3종 원문 대조(RA `04a147e` 문서 §6 — 양식 · 계정 · 공간 · 게시판 지정 게시)
- [x] 계획 · 체크리스트 · 결정 기록

## M0 계약 굳히기

- [x] `contract.md` — 원천 `auto_changes` + 해석 다섯 · subject · 결과 봉투 · 상태 낱말 · idem_key 규칙(v1, 11-27)
- [x] `portal-api.md` — 포털 표 · 엔진 박자 · 창구 · 신원(11-27)
- [x] 계약 도구 이름이 심의 좌석 자유 조회 접두(`_FREE_ALLOW`)와 안 겹치는지 확인(D-18 — `auto_` 없음, 11-27)
- [x] 앱 코드 조사 → 계약 v1.1(AP-11)
- [x] 앱 요청서 `requests/` — StepForge · DynaForge · ThermalShock · KooSlurm · ODB 허브(11-27)
- [x] 보냄(11-27) — StepForge(stepforge-d4) · DynaForge(kooremapper-4a) · KooSlurm(smarttwinmcp-c8)
- [x] 받음(11-27, AP-28) — StepForge(사람이 정하는 개발 단계 칸 `set_revision(dev_rev)`) · DynaForge(세션에 과제 · 개발 단계 칸 · 기준 없이 수치만 ·
  auto_* 만 모두 읽기) — 둘 다 가지에서 짓고 main · Drive 는 87 의 다음 운영 회차에. KooSlurm(c8)은 앞 질문에 막혀 아직 못 읽음
- [x] 개발 단계를 나중에 넣어 풀린 항목의 막힘 줄을 걷는다(11-27, AP-28)
- [ ] ThermalShock — 열린 세션 없음(사용자가 세션을 열면 넘긴다) · ODB 허브 — cae00 사람(AQ-8)
- [x] cae00 물음 `cae00-questions.md` AQ-1 ~ AQ-9(11-27)
- [x] 87 에 넘김(11-27) → [ ] 받은 편지함에 실림

## M1 포털 뼈대(dev)

- [x] 표 — `auto_rules` · `auto_rule_versions` · `auto_cursors` · `auto_subjects` · `auto_runs` · `auto_run_steps` + `auto_events` · `auto_lock`(절차 저장소, `backend/app/autopipe/store.py` — 11-27 가지 `wt1127/autopipe-core`)
- [x] 규칙 스펙 검증(범위 · 트리거 · 단계 연결도 순환 · 참조 · 한도 · stage, analysis → analysis 허용 — `autopipe/spec.py`)
- [x] 감지기(묻기 · 커서는 끝까지 받았을 때만 · quiet_s · 입력 지문 · project/revision null → 막힘 — `autopipe/engine.py`)
- [x] 그림자 실행 — 판정 · auto_check 까지, 제출 없음 · 「냈을 것」 사건(cost · sync)
- [x] 끄기 스위치 `AUTO_PIPELINE_ENABLED`(기본 꺼짐 — start.sh 가 값이 있을 때만 넘김) · 권한 `feat:auto-pipeline`(grant_only) · 창구 `/autopipe-api`
- [x] 현황판 · 규칙 화면(11-27, 가지 `wt1127/autopipe-ui`) — 절차 › 「자동」 탭 `/procedures/auto`: 상태 머리 · 규칙 목록 · 편집(JSON · 검증 · 새 판) · 켜기(자동 제출은 확인) ·
  현황판 · 실행 상세(결과 봉투 · 입력 확인 · 보고서 · 승인 · 취소) · 감지 목록, 시험 `backend/tests/test_autopipe_page_in_browser.py`(가짜 창구 — 실제 창구로 보기는 백엔드 뒤)
- [x] 계약 꼴 가짜 앱(진짜 꼴 그대로 — `tests/autopipe_fakes.py`) · 시험 113(엔진 · 스펙 · 보고서 · RA · 토큰 · 창구 · 격리)
- [x] update-all 기다림(11-27, AP-26) — deploy-all 포털 `_stop` 이 내리기 직전에 `/internal/autopipe/quiesce`(공유 시크릿) — 새 박자 멈춤 + 도는 박자가 접히기를
  `HWAX_AUTOPIPE_WAIT_S`(300) 기다림. 해석 잡은 기다리지 않는다(앱 쪽에서 돌고 다시 뜬 포털이 이어 묻는다). 꺼진 박스 · 옛 포털 ○, 못 기다림 ⚠

## M2 첫 해석 끝까지(cae00)

- [x] approve 단계 — 사람 한 번 누름(`POST /autopipe-api/runs/{id}/approve`) → `auto_submit`(코드 · 가짜 시험)
- [x] `auto_status` 재기동 넘기 · 결과 봉투 판정(꼴 틀림 → failed envelope_invalid · isError=false 의 error 칸도 실패) · sync 앱은 제출 답 done → 곧바로 결과
- [x] 해석별 보고서 렌더 · 시스템 계정 게시 코드(박스 파일 `auto_pipeline` 줄 · 0600 토큰 파일 · dry_run → ai-draft → mounts) · 형식 정의 `infra/ra/formats/auto-pipeline.json`
- [ ] RA 시스템 양식 등록 · 시스템 계정 · 시스템 공간(운영 — AQ 물음)
- [x] ~~서비스 PAT 만료 표시~~ — 필요 없어짐(AP-8 · AP-13 — 호출마다 15분 토큰)
- [ ] cae00 실주행 — 계약을 먼저 갖춘 앱 하나로 그림자 → approve → 결과 봉투 → 보고서 → RA 시스템 공간

## M3 ~ M5

- [x] 두 번째 해석 · DAG(upstream 넘기기 · 앞 단계 실패면 upstream_failed) · 종합 · 이전 차수 대비(코드 · 가짜 시험)
- [x] AP-D5 대체 사슬(도는 것 끝까지 · 안 낸 해석 취소 · 보고서는 「대체됨」 표지로 남김 — AP-14)
- [x] auto 단계 · 한도(박스 · 규칙 동시 · 과제당 24시간) · 야간 창
- [ ] 알림 감지(StepForge 웹훅 또는 SP 변경 목록)
- [x] 막힌 단계 다시 확인(11-27, AP-24) — `POST /runs/{id}/recheck` · 실행 상세 「막힌 단계 다시 확인」(확인 뒤) — 같은 실행을 다시 연다
- [x] 지금 돌리기(11-27, AP-25) — `POST /rules/{id}/run` · 감지 목록에서 규칙을 고르고 줄마다 「지금 돌리기」(확인 뒤) — 켜기 전에 본 과제 · 차수에도
- [x] `ra-register-format.py --auto-pipeline`(11-27, AP-27) — 형식 등록과 박스 파일 `auto_pipeline` 줄(formats 셋 · board · token_file)을 한 번에
- [ ] 심의 · 리스크 심사 단계 · 과제 인사이트 보기
