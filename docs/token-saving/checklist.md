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

## 2판 — 서버 Qwen · GLM 에 일 맡기기(TS-6 · [offload-v2.md](offload-v2.md))
- [x] 계약 문서(A ~ E · 스위치 · 리포 사이 창구)
- [x] 에이전트 서버 — A 위임 잡(`DELEGATE_ENABLED`) · C `draft_section`(`DRAFT_ENABLED`) · D `llm_transform`(`TRANSFORM_ENABLED`) · 묻기 창구 `/llm/ask_over_text`
- [x] 게이트웨이 — B 결과 손잡이(`GATEWAY_RESULT_REFS` + `X-HWAX-Result: ref`) · `result_get` · `result_ask` · 내부 ref 창구 · `/health` 표지
- [x] 포털 — E 설정 배치 선택 칸 · Claude Code 명령 둘 · CLAUDE.md 규칙 묶음 · 박스 꺼짐 표시 · update-all ○ 줄 넷 · env 킷 · 이력 — 가지 `wt1124/offload-v2`(합치기 전, TS-10 ~ TS-13)
- [ ] 포털 — Windows PC 에서 배치 실제 한 번(켬 → 다시 켬 → 끔 — 명령 둘 · CLAUDE.md 표지 사이 · 머리 · 걷은 뒤 바이트 대조, BOM · LF 파일 · 사람 파일 같은 이름)
- [ ] 합치기 · 리포마다 전체 회귀 · dev 에서 켜고 실제 한 번씩 · 끄면 바이트 같음 확인
- [x] cae00 받은 편지함 — 켜는 법(켤지는 사람) — 5차 글(11-24) · 에이전트 서버 `b0fd922` · 게이트웨이 `c43382b`

### 2판 비교 테스트셋(TS-14 · [eval-plan.md](eval-plan.md) · `infra/offload-eval/`)
- [x] 과제 16(R · M · W · T 넷씩 — 읽기만 · 공개 리포라 스스로 찾게) · 기대 꼴 검사
- [x] 실행기 `run-eval.mjs` — check · run(섞인 차례 · 이어 하기 · 울타리 대조) · judge(눈가림 · 한 번 다시) · human(4쌍) · report(합계 · 중앙값 · 개선율 · 숫자 대조 · 서버 LLM 따로)
- [x] 시험 `backend/tests/test_offload_eval.py` — 가짜 claude · 가짜 게이트웨이, 변이 열셋 모두 붉음 — 가지 `wt1124/offload-eval`
- [x] 사용자 확인 — 결과 파일 Read 허용(README 4-3) · 판정 기준 제안(패배율 ≤ 10% · 어긋남 늘지 않음) — 권장안(TS-15)
- [x] cae00(사람) — 스위치 켜기 · check · 연기 시험 · 본 실행 64 · 판정 32 · 보고서 돌려받기 — 패배율 25% 로 기준 미달 · 다시 끔(TS-16)
- [ ] 사람 4쌍과 판정의 일치(사용자 검토)
- [ ] OF-1 ~ OF-5 고침(운영 요청서 — 첨부 읽기 · 위임 깊이 · 숫자 대조 단위 · 초안 권고 · 기다리기) → 같은 과제로 다시 재기
