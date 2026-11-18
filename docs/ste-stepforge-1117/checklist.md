# 레디쉬 · 결로 연계 — 포털 · 게이트웨이 몫 할 일

> 계획은 `PLAN.md`, 결정은 `context-notes.md`.

## 전달 (11-18)

- [x] 원문 둘을 StepForge · ste · 브리지 세션에 나눠 보냄
- [x] ste 06 답 — 몫 다시 가름 · 토큰 보류 · 스테이징 창구 확인
- [x] 브리지 답 — 몫 받음 · BR-R1 정정(`STEPFORGE_BASE` 는 이미 읽는다, 폴백 `localhost:9520` 이 문제) · BR-R3 합성 재현은 통과
- [x] ste 1e53260 묶음 풀기 — 사용자 확인을 06 에 전함
- [x] StepForge 답 받기 — D-707(전부 · 두 번에 착지, SS-7)
- [ ] BR-R3 입력 STEP(잡 3fa9415132b7) · B-2 공동 STEP 표본 — 운영 박스에 있어 사용자가 꺼내야 한다(토폴로지만 있으면 치수를 바꾼 사본도 된다)

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
- [ ] HEAXHub 판이 나오면 dev 실제 목록으로 확인

## PT-R4 ste 잡 목록 '내 잡' (P2)

- [ ] ste ST-R9 판이 나오면 게이트웨이를 거친 답에 `mine` 이 오는지 확인
