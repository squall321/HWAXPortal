# 레디쉬 · 결로 연계 — 포털 · 게이트웨이 몫 할 일

> 계획은 `PLAN.md`, 결정은 `context-notes.md`.

## 전달 (11-18)

- [x] 원문 둘을 StepForge · ste · 브리지 세션에 나눠 보냄
- [x] ste 06 답 — 몫 다시 가름 · 토큰 보류 · 스테이징 창구 확인
- [x] 브리지 답 — 몫 받음 · BR-R1 정정(`STEPFORGE_BASE` 는 이미 읽는다, 폴백 `localhost:9520` 이 문제) · BR-R3 합성 재현은 통과
- [x] ste 1e53260 묶음 풀기 — 사용자 확인을 06 에 전함
- [x] StepForge 답 받기 — D-707(전부 · 두 번에 착지, SS-7)
- [x] BR-R3 입력 STEP(잡 3fa9415132b7) · B-2 공동 STEP 표본 — 사용자 결정 11-18: dev 로 꺼내지 않고 cae00 에서 시험한다
- [ ] 브리지 세션의 cae00 진단 절차(숫자만 내는) 받으면 받은 편지함에 덧붙이기

## 전달 (11-22) — 11-21 재시험 뒤 남은 것(`retest-1121-request.md`)

- [x] 원문을 리포에 정본으로(`retest-1121-request.md`) · 받을 곳 표(PLAN 「11-21 재시험」)
- [x] StepForge(`stepforge-d4`)에 SF-1 ~ SF-12 보냄 — 받음 · D-708 로 갈래에서 짓는 중(1차 SF-1 · 2 · 3 · 8 · 9 · 11 · 12), 착지 판 · 날짜는 그쪽 사용자 확인 뒤. 짚은 것 — SF-12 의 `source` · `to_ste_upload` 는 11-18 결정으로 없다(옮기기는 게이트웨이 한 길) · SF-8 원인(산출물 열쇠 글롭) · SF-2 의 접촉 넓이 0 은 참값으로 보임(`contact_zero_why`)
- [x] ste(`smarttwinexplorer-06`)에 ST-1 ~ ST-17 보냄 — ste 코어 몫 ST-4 · ST-5(틀) · ST-12 · ST-14 · ST-16 은 지어 로컬 main 에 있음(origin 보다 22커밋 앞 · Drive 는 1e53260 그대로 — 그쪽 사용자 확인 뒤 나간다). ST-5 는 `report_url` 대신 경로 · 크기 · `job_url`(저장형 XSS). ST-3 은 그쪽 사용자에게 묻는다(11-18 ST-R1 결정을 다시 여는 일). 나머지는 브리지 몫
- [x] 브리지(`koosolvercontainer-da`)에 BG-1 · BG-2 · BG-6 과 앱 래퍼 몫 보냄 — 받음 · 11-17 의 19 항목과 겹쳐 Phase 7 차례(ST-2 · ST-1 · BG-1 · BG-2 먼저), 반영은 Drive 동결 해제와 그쪽 사용자 확인 뒤. BG-2 를 합성 판으로 재현해 고침(KooSolverContainer `0296fab` · `41c2cc9`, 미배포 — 운영 진단기 숫자로 원인 확정). 새로 찾은 결함 — part-study 레디쉬 길이 mm 좌표를 m 로 읽어 1000배 판을 풀었다(단독 reddish 잡은 영향 없음)
- [x] SF-5 ↔ ST-7 어느 쪽이 규약 변환을 맡는지 — StepForge 가 geometry 절 변환(축 · 원점 · 변 4묶음 · UV 창), ST-7 은 그 절을 손대지 않고 싣고 검사 · 메시 크기 · placeholders 만(두 세션 합의 11-22)
- [x] 브리지 P0 셋을 dev 에 넣음(11-22, 미배포 — 반입은 Drive 동결 해제 · 그쪽 사용자 확인 뒤): ST-2 사유 opening_unmatched · no_outlet · no_inlet · flux_imbalance(기본 50 %) → 결로 단계 fail · 잡 FAILED(KooSolverContainer `85256df`) · ST-1 개구부를 원 안의 면만 패치로(합성 상자 반경 4 mm → 50.24 mm², `6b54715` · `843e22d` — 옛 꼴은 `"patch": "face"`) · BG-1 (가)(다) 주소를 짐작하지 않고 실패를 갈라 fetch.json 에(`2b1946f`, 주소 · 토큰 전달은 ST-3 결정 뒤). 운영의 1ddbdd7cd769 와 같은 입력의 재확인은 반입 뒤 운영 박스에서
- [x] 브리지가 ST-11 · ST-6 을 dev 에 넣음(11-22, 미배포 — 반입은 Drive 동결 해제 · 그쪽 사용자 확인 뒤): ST-11 part-study `stages`(outline · stl · reddish · condensation — 고른 단계가 쓰는 앞 단계는 함께 돈다 · 고르지 않은 단계는 skip · not_requested · 비우면 종전대로, 제출 파라미터 선언은 ste 가 지음 — part-study · part-study-registry 의 params `stages`(str · 기본 빈 글자, ste `ce3c864` · 로컬 — 푸시 · Drive · 운영 전). ⚠ 제출 파라미터는 **글자 하나**로 준다 — `"stages": "stl,condensation"`. 요청서(retest-1121)의 배열 꼴 `["stl","condensation"]` 은 제출 때 400(잡 안 생김, ste `783e7e7`) — 배열은 part-study-registry 요청서 `request.json` 안에서만. 모르는 낱말 · cond=1 인데 condensation 빠짐은 해석 전 FAILED · precheck · bad_input. part-study 의 get_app_schema 에는 params 설명 칸이 없어 낱말이 안 보인다(레지스트리 요청서 fields.stages 에는 있다) — 재시험은 글자 꼴로) · ST-6 `criteria: [{metric, limit, patch?}]`(상한 — 값 ≤ limit 이면 합격) → `ste_job_summary` 의 verdict {pass, metric, patch?, value, limit, reason_code(over_limit · metric_unavailable), checks}, 기준이 없으면 null · 틀린 기준은 해석 전에 그 단계 fail · bad_input. 결로 지표 넷(condensed_mg · rate_mg_s · risk_cells · patch_area_pct), 레디쉬는 지금 penetration_final_mm 하나
- [ ] ST-6 레디쉬 지표 더하기(붉어짐 면적비 · 조사 창 안 P 평균) — 사용자 결정(브리지 세션 11-22): 붉어짐 = 열화 분율 P/(P+P_ox) · ST-15 는 습도에 따른 산소분압 + 층별 온도 의존(활성화 에너지는 입력) · 새 해석 스크립트와 브리지 SIF 는 스테이징 먼저(Drive · 운영은 그대로). 짓기는 브리지 몫
- [ ] SF-11 운영 박스에서 맨 이름 `leak_report` 의 서명에 `parts` 가 왜 안 보였나(받은 편지함 2026-11-22 Q8) — 게이트웨이는 스키마 변화를 지문으로 알아채 다시 모은다(소스 확인) — 11-23 답: 지금 인자 목록에 `parts` 있음(array 또는 null) · StepForge 줄 1. 재시험 때 안 보인 까닭은 못 가림(SS-11)
- [ ] StepForge 2차 물음 — SF-10 테이프 이름 꼴 · SF-6 인쇄 도면 그림(받은 편지함 Q9 · Q10), SF-4 material_id 는 MaterialTwin 재료 id 라고 답함, SF-2 의 ST-8 쪽 물음은 브리지에 전함 — Q9 · Q10 은 11-23 운영 박스에서 볼 수 없어 과제 자료를 아는 사람에게 넘김(사용자 경유, SS-11)
- [x] ST-3 — ste 세션에서 사용자 결정(11-22 밤, ste-06 전언): 주소만 먼저(`STEPFORGE_BASE`) · 잡 한정 토큰은 발급처가 생긴 뒤 · 다 지으면 푸시 · Drive. 브리지 BG-1 의 주소 전달이 이것을 기다렸다
- [ ] ST-3 주소 넣기 — ste 헤드 `.env` 의 `STE_STEPFORGE_BASE`(사람 — 받은 편지함 Q15, 11-23 아직 · SS-11)
- [ ] BG-3 큰 파일(100 MB 급) · cavity_step 을 dev 에서 한 번 옮겨 보기
- [x] BG-3 · ST-10 업로드에 scenario.json 더하기 — ste 가 받는다(`submit_job` 이 files 와 upload_id 를 함께 · 같은 이름은 400). 게이트웨이에 새 도구 없음 — ste 가 지음(`47ed289` · `23f3245`, 로컬 main · 스테이징에서 part-study cond 1 을 STEP 업로드 + scenario.json files 로 REST · MCP 한 잡씩 — 결로 단계 ok). 운영은 그쪽 사용자 확인 뒤 다음 ste 묶음
- [ ] BG-4 `gas_transport_lookup` — S = P/D 추정(`derived`) 지음 · 올림(게이트웨이 `b571f36` — 같은 시료 · 온도 1 K 안 · O2 일 때만, dev 게이트웨이 반영 11-22) · 온도 차 칸은 이미 있다(`delta_K`) · 층별 조회는 SF-4 의 material_id 뒤
- [ ] BG-5 · PT-1 토큰이 없을 때의 답(등록 방법) 확인(받은 편지함 2026-11-22 Q7 — 답 받기) · 공용 프리셋은 만들지 않는다(사용자 결정 11-22 — SS-6 그대로) — 11-23 못 봄(토큰을 등록하지 않은 계정이 있어야 한다 — 사람 몫, SS-11)
- [x] PT-2 운영 박스에서 StepForge 줄의 build 가 비는 까닭 — 받은 편지함으로 묻기(`../cae00-inbox/2026-11-22.md` Q6) — 답 받기 — 11-23 답: build 없음 · 허브 서버 목록은 못 봄(401) · 그 박스엔 StepForge 인스턴스가 없다(운영 노드에서 돈다 — dev 와 다른 까닭일 가능성, SS-11)
- [ ] PT-2 까닭 가리기 — 허브 서버 목록(인증 창구)의 StepForge 항목에 build 가 있는지(11-23 못 봄 — 401, SS-11)

## P-1 `artifact_to_ste_upload` (P0)

- [x] 게이트웨이 로컬 도구 — StepForge 조각 받기(그 사람 명의, full=true) → ste 업로드 열기 · PUT(같은 위임 PAT, 티켓 안 씀) — 게이트웨이 `ec91b62`
- [x] sha256 맞대기 — 다르면 PUT 을 끊는다(ste 가 `.part` 를 지우게 — ste 결함 06 에 알림)
- [x] 시험 — 가짜 StepForge(접기까지 진짜 꼴) · 가짜 ste 로 조각 셋 · sha 어긋남 · 권한 · 신원 · 413/409/404 · 401 다시 받기
- [x] 게이트웨이 전체 회귀(1,100 통과 — PT-R1 · PT-R2 포함)
- [x] 올림 — 게이트웨이 master(`ec91b62` · `6dcef62` · `dd304eb`) · 포털 main · 받은 편지함 11-18 · 업데이트 이력(11-18)
- [x] dev 게이트웨이 재기동(11-18 04:34 — 새 도구 셋이 `/tools-map` 에 뜸)
- [x] dev 실호출(11-18, 사람 PAT) — STEP 34,347 B(조각 하나)로 새 업로드, 같은 업로드에 glb 2,034,988 B(조각 셋) 더함 · sha256 이 StepForge 디스크 원본과 같음 · ste 파일 목록 둘

## PT-R1 `material_gas_transport` (P1)

- [x] MaterialTwin 물성 키 · 응답 꼴 조사(실 DB 읽기 전용으로 꼴 확인)
- [x] 도구 `gas_transport_lookup` · 시험 — 게이트웨이 `6dcef62`(이름은 SS-5)
- [x] dev 실호출(11-18) — D · S · P 셋이 다 있는 재료 둘: 293 K 뿐인 재료는 303.15 K 요청에 그 값과 delta_K 10.15(외삽 안 함), 다른 재료는 같은 온도 값과 시료 경고 · 후보

## PT-R2 · P-2 시험 조건 → 환경 값 (P1)

- [x] 신뢰성 시험 앱 · 응답 칸 조사(TestScope 소스)
- [x] 도구 `reliability_test_conditions` · 시험 — 게이트웨이 `dd304eb`(공용 조건표는 SS-6)
- [x] dev 실호출 — TestScope 가 없어 '붙어 있지 않다' 로 답함(예상대로)
- [ ] cae00 실호출(받은 편지함 11-18 2번)

## PT-R3 · P-3 운영본 표시 (P2)

- [x] GW-05 로 env · canonical · aliases 가 이미 있음을 확인
- [x] HEAXHub 에 서버 목록 `build`(앱 커밋) 칸 청하기(heaxhub-4b, 11-18)
- [x] HEAXHub 답 — `build: {commit, started_at}`, 모르면 칸째 없음(SS-7)
- [x] 게이트웨이 받는 쪽 — `629f32c`(올림)
- [x] HEAXHub `ec240e1` 올림(사용자 결정 11-18 — 11-12 main 보류를 풀고 `118059b` 와 함께) · dev 허브 백엔드 재기동
- [x] dev 실제 목록(11-18) — 허브 앱 8개에 build(commit · started_at)가 실린다. step_forge 는 떠 있는 인스턴스보다 디스크 SIF 가 새로워 '모름'으로 비고(의도), kooremapper_mcp 는 프록시라 없다. 허브 밖 백엔드는 출처가 없어 없다

## PT-R4 ste 잡 목록 '내 잡' (P2)

- [ ] ste ST-R9 판이 나오면 게이트웨이를 거친 답에 `mine` 이 오는지 확인
