# 토큰 절감 — 체크리스트

계획 · 검토는 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## T0. 검토(dev — 11-02)
- [x] 설계안 v1.0 의 코드 주장 확인 · 항목별 판정 · 셈(TS-1 · TS-2)
- [x] 사용자 결정 — 작은 코드 셋 지금 · 서버 엔진을 기본 길로 · P4b · P2 는 측정 뒤(TS-5, 11-02)
- [ ] cae00 측정(받은 편지함 Q13) — via=pat 도구별 호출 · chars · 상태 묻기 비율 · 보기별 연결

## T1. 오늘 — PC 설정(사용자)
- [ ] P1 `X-HWAX-View` 머리(권장 시작 `bundle:expert,report,knowledge` 또는 `portal`) · `list_tool_apps` 로 확인
- [ ] PC CLAUDE.md 습관(상태 고리 금지 · search_tools detail 없이 · list_agents compact · risk_next_step 부터)

## T2. 작은 코드(S)
- [x] 에이전트 서버 — `deliberate_status(wait_s, brief)` — `aadd591`(11-02, dev 반영)
- [x] 에이전트 서버 — `deliberate_result(view="summary")` 골라 쓰기(기본 full) — `aadd591` · 루틴 쪽 view 버림은 게이트웨이 `95fdbe9`
- [x] 게이트웨이 — `search_tools` 촘촘한 JSON(소비처가 모두 JSON 으로 읽어 기본으로) · `detail=true` 상한 25,000자 — `6dc4abc`(11-02, dev 반영)
- [x] 안내 글 — 게이트웨이 서버 지침 13번(`6dc4abc`) · 워크플로 다섯의 설명(`6327d0fb`). 등록 배치는 안내 글을 깔지 않아 손대지 않음

## T3. 중간(M) — 측정 뒤
- [ ] P2 `{tool, args}` 근거 — 확인된 읽기 울타리 · 사람 없으면 막기 · 봉인 · 기준일 · 출처 표지
- [ ] P4b 머리로 고르는 결과 줄이기 + `result_get` — 따로 쓰는 저장소 · 사람에 묶은 손잡이 · content + structuredContent · 검증 근거엔 전체

## T4. 나중
- [ ] P8 · P6 · P7(WDA 마크다운 입구) · 리스크 심사 루틴 · R1 ~ R4 + GLM 우선순위 관문 · §4.5 따로 시험
