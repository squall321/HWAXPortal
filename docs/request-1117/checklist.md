# 11-17 요청 — 체크리스트

## 계획
- [x] 요청서 둘 요약(과제 이름 뺌) · 사용자 결정 셋 · 꼴(contracts) · 결정 R-1 ~ R-4

## 리스크 앱(HWAXRisk — 가지 wt1117/rk)
- [x] v8 표 · RK-01 판정표 칸 정의 · 판 · 층 · 비교 · 내보내기 — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] RK-02 근거 묶음(색인 맨 앞 · 칸별 상한 · 가림 · 엔진 상한 거절 · 지문) — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] RK-06 provenance(아는 것만 · 모름 · 판 · 개수 불일치 경고) — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] RK-03 결정 반영 층(결정 JSON · 결정문 글 · 칸 매핑 · 충돌 · 합의/표결 불일치) — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] RK-04 숫자 원장 · 금지값 점검 — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] RK-07 표기 규칙(labels) · 묶음 · 보고 묶음에 적용 — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] RK-05 보고 묶음(facts 틀 등록 · null 과 까닭) — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [x] MCP 도구 · REST · 도구 설명 · 시험 · 전체 회귀 · 반대 검토 — main 에 있다(HWAXRisk 병합 `91abdb6` · RK-06 `5d0c4e2`, 11-21 커밋 대조 — `docs/leftovers-1121` L21-2)
- [ ] 병합 · 올림 · SIF(허브) · 화면 요청서(화면 세션 몫)

## 포털 — 심의 엔진(HWAXAgentServer — 가지 wt1117/dl)
- [x] DL-03 구조화 결정 · 합의/표결 대조 — main 에 있다(에이전트 서버 병합 `7da623d`, 11-21 커밋 대조)
- [x] DL-01 참조 근거(risk_bundle 먼저 · 확인된 kind 만) · 미리 보기 · 이어하기 재실음 — main 에 있다(에이전트 서버 병합 `7da623d`, 11-21 커밋 대조)
- [x] DL-02 묶음 실행(중복 0 · 끝난 것 안 함 · 멈춤 · 재시작 · 좌석 유실 표지 · 끝남 알림) — main 에 있다(에이전트 서버 병합 `7da623d`, 11-21 커밋 대조)
- [x] DL-04 원천 대조(num · id · part · net · 쪽 이음) — main 에 있다(에이전트 서버 병합 `7da623d`, 11-21 커밋 대조)
- [x] DL-05 preset — main 에 있다(에이전트 서버 병합 `7da623d`, 11-21 커밋 대조)

## 포털 — 게이트웨이(HWAXMcpGateway — 가지 wt1117/gw)
- [x] GW-05 앱 env · 정본 · 옛 키 안내(가지 `fd1f52d` · `ac49fae` · `4aba6cb` — 적지 않은 박스는 unknown, R-10)
- [x] GW-02 읽기 목록 재기동 없이 · 덧씌우기 · 관리자 보기 · PATCH(`86cef7f`)
- [x] GW-01 적재 경로 카탈로그 — 게시만(결정 문서 C3 · R-8, 중계 없음 — `d84c700`) · DynaForge 선언은 그쪽 공식 답(D4) 뒤
- [x] 게이트웨이 가지 반대 검토(M1 · L1 ~ L9 고침 — `ff54acb` · `7e63cfa` · `7d4d8ed`) · 병합 `4c85945`(합친 판 1,082 통과) · 올림 · dev 재기동(dev 박스 `app_keys.local.json` default_env dev) · cae00 할 일 받은 편지함 11-17
- [x] GW-04 점검표 문서 · 훑기 보고(`431b2d1`) · D1 항목
- [ ] GW-03 — DynaForge 캠페인 적재 상태(DF-01)를 읽는다(C4) · DF-01 뒤

## 다른 세션에 보낸 것(11-17 결정 문서)
- [x] DynaForge(kooremapper-4a) · KooChainRun · stcx(KooSlurm -35 · -de 를 거쳐 pyKooCAE -88 · -53 이 받음 — KC-01 매니페스트는 pyKooCAE `Runner/RunProvenance.py` 몫, KooSlurm 대시보드의 return_manifest 는 다른 파일) · ReportArchive(-f6 · -e2) · WebDesignAgents(-7e · -88) — 그쪽 몫만
- [ ] 이 박스에 세션이 없는 곳(MatNexus · SIREN · PLM/failuretrace · SP 사전 주인 · 자주검증 Datahub) — 사용자 몫

## StepForge 착지 뒤(갈래 feat-receiver-v1 `3eeea280` · D-706)
- [x] 게이트웨이 쓰기 동사 subscribe · recheck(`85fcd24` — job_subscribe · interference_recheck 가 표지 없이 와도 루틴 읽기로 안 열림)
- [ ] HE팀 운영자 `he-cad-stepforge` — writes 에 interference_recheck · save_role_pairs, confirm 에 job_subscribe(착지 뒤 — 없는 이름은 동기화가 멈춘다)
- [ ] 리스크 앱 RK-06 이 StepForge `stage_code` · `revision` · `copy_stage` · `system_status.env` 를 읽게
- [ ] cae00 받은 편지함 — `APPTAINERENV_STEPFORGE_ENV=prod`(그 전엔 env null)

## 마무리
- [ ] 세 가지 검토(반대 검토) · 전체 회귀 · 병합(--no-ff) · 올림 · dev 재기동 · 허브 SIF(리스크 앱) · 업데이트 이력 · 받은 편지함 · PC 수용 절차(acceptance-pc.md)

## 포털 — 묶음 끝남 알림(가지 wt1117/notice — contracts §7 · R-12 ② · 결정 R-13)
- [x] 알림 원장 — 대화 저장소 파일 안의 표 둘(notices · notice_cursors) · (kind, source_id) 유일 · 포털 안 링크만 · 시험 격리 확인
- [x] API `/notices-api` — 목록(최신 것부터 · 안 읽은 수) · `/{id}/read` · `/read-all`(세션, 쓰기는 CSRF, 제 알림만)
- [x] 당기기 — `DELIB_BATCH_NOTICE_S`(기본 60 · 0 끔) · 공유 비밀만 · 주인이 포털 계정일 때만 · 경계 반복 · 재기동 · 두 일꾼에 한 번 · 실패 까닭 경고
- [x] 화면 — 머리줄 종(안 읽은 수) · 목록(제목 · 한 줄 · 시각 · 묶음 id · 열기 · 읽음 · 모두 읽음) · 1280 · 390 화면 확인
- [x] 업데이트 이력(11-17 심의 · 기술)
- [ ] 엔진 가지(wt1117/dl)와 함께 병합 · 올림 — 엔진이 먼저 나가지 않으면 당기기가 'HTTP 404 — DL-02 전의 판' 경고를 한 번 남기고 기다린다
- [ ] dev 실주행 — 묶음 하나를 끝내 알림이 한 번 뜨는지(포털 재기동 뒤)
