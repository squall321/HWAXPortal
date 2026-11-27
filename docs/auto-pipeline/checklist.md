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
- [ ] ThermalShock — 열린 세션 없음(사용자가 세션을 열면 넘긴다) · ODB 허브 — cae00 사람(AQ-8)
- [x] cae00 물음 `cae00-questions.md` AQ-1 ~ AQ-9(11-27)
- [x] 87 에 넘김(11-27) → [ ] 받은 편지함에 실림

## M1 포털 뼈대(dev)

- [ ] 표 여섯(`auto_rules` · `auto_rule_versions` · `auto_cursors` · `auto_subjects` · `auto_runs` · `auto_run_steps`) — 절차 저장소
- [ ] 규칙 스펙 검증(범위 · 트리거 · DAG 순환 · 한도 · stage)
- [ ] 감지기(묻기 · 커서 · quiet_s · 입력 지문)
- [ ] 그림자 실행 — 판정 · auto_check 까지, 제출 없음
- [ ] 현황판 · 규칙 화면 · 끄기 스위치 `AUTO_PIPELINE_ENABLED`(기본 꺼짐) · 권한 `feat:auto-pipeline`
- [ ] 계약 꼴 가짜 앱(진짜 꼴 그대로) · 시험
- [ ] update-all 기다림(도는 실행)

## M2 첫 해석 끝까지(cae00)

- [ ] approve 단계 — 사람 한 번 누름 → `auto_submit`
- [ ] `auto_status` 재기동 넘기 · 결과 봉투 판정
- [ ] 해석별 보고서 렌더 · RA 시스템 양식 등록 · 시스템 계정 게시(박스 비밀 파일)
- [ ] 서비스 PAT 만료 표시

## M3 ~ M5

- [ ] 두 번째 해석 · DAG · 종합 · 이전 차수 대비
- [ ] AP-D5 대체 사슬(도는 것 끝까지 · 안 낸 단계 취소 · 「대체됨」 표지)
- [ ] auto 단계 · 알림 감지(StepForge 웹훅 또는 SP 변경 목록)
- [ ] 심의 · 리스크 심사 단계 · 과제 인사이트 보기
