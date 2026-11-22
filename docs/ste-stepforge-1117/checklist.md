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
- [ ] StepForge(`stepforge-d4`)에 SF-1 ~ SF-12 보냄(11-22 08:40 KST 전달됨) — 답 받기
- [ ] ste(`smarttwinexplorer-06`)에 ST-1 ~ ST-17 보냄(11-22 08:40 KST 전달됨) — 몫 가름 · 답 받기
- [ ] 브리지(`koosolvercontainer-da`)에 BG-1 · BG-2 · BG-6 과 앱 래퍼 몫 보냄(11-22 08:40 KST 전달됨) — 답 받기
- [ ] SF-5 ↔ ST-7 어느 쪽이 규약 변환을 맡는지(StepForge · 브리지가 정함)
- [ ] BG-3 큰 파일(100 MB 급) · cavity_step 을 dev 에서 한 번 옮겨 보기
- [ ] BG-3 · ST-10 업로드에 scenario.json 더하기 — ste 답 뒤 어느 쪽이 짓는지 정함
- [ ] BG-4 `gas_transport_lookup` — S = P/D 추정(`derived`) 지음(게이트웨이 통합 가지 — 같은 시료 · 온도 1 K 안 · O2 일 때만, 올림은 통합 가지와 함께) · 온도 차 칸은 이미 있다(`delta_K`) · 층별 조회는 SF-4 의 material_id 뒤
- [ ] BG-5 · PT-1 토큰이 없을 때의 답(등록 방법) 확인(받은 편지함 2026-11-22 Q7 — 답 받기) · 공용 프리셋은 사용자에게 다시 묻기(SS-6)
- [x] PT-2 운영 박스에서 StepForge 줄의 build 가 비는 까닭 — 받은 편지함으로 묻기(`../cae00-inbox/2026-11-22.md` Q6) — 답 받기

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
