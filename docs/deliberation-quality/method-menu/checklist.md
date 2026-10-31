<!-- 심의 방법 메뉴(Jobs 2층 + Modifiers) 구현 체크리스트 -->
# 심의 방법 메뉴 — 구현 체크리스트

목표. 심의를 **목적(Job) 1층 + 얹을 층(Modifier) 2층**으로 고르게 하고, 두 진입 맥락
(A 챗 핸드오프=추천 우선 · B 새 심의=상황 카드)에서 같은 택소노미를 쓰게 한다.
방법론은 엔진(chairTemplate)으로 숨기고 사람은 자기 상황으로 고른다.

성공 기준. `node --check`(2 JS)·`py_compile`·프론트 빌드 통과 + 새 엔진 3종이
두 엔진(MCP JS·웹 PY)에서 동일 키·동일 산출 규격 + chair_template 웹 경로 유실 수정.

## 상태 (2026-08-29) — A·B·C 완료, D 문서·커밋 진행
- **A 계약** ✅ routes.py DelibOpts(chair_template·modifiers) · deliberation.py _resolve_opts. py_compile OK.
- **B 엔진** ✅ JS·PY 각 8 chair(신규 3 + build-plan PY 미러) + 5 modifier. 파리티 바이트 일치, node --check·AST OK.
- **C 프론트** ✅ delibTaxonomy.ts · HandoffBrief 2층 · DeliberatePage 7-Job · ChatContext modifiers. tsc·vite build OK.
- **D 문서·반영** 진행 — 커밋: RA 1f032e0(문서) · HWAXAgentServer c510300 · HWAXPortal daf3628(엔진)·9e9cf60(프론트).
  남음: 반영(agent-server 재기동·워크플로 sync·erag 재색인 — 운영은 사용자), 라이브 시각 QA(vLLM 복구 후 e2e).

---

## A. 계약(contract) 정합 — 유실 버그 수정 + modifiers 신설
- [x] `backend/app/agent/routes.py` DelibOpts: `chair_template: str|None` 필드 추가 → 검증: 웹 경로에서 model_dump 에 실려 나감 (현재 미선언이라 조용히 버려짐) — 풀림 backend/app/agent/routes.py:207 chair_template(`daf3628`) · 계약 시험 backend/tests/test_delib_opts_contract.py (10-31 정리)
- [x] routes.py DelibOpts: `modifiers: list[str]|None` (max_length=5) 추가 → 검증: 화이트리스트 밖 값은 agent-server 가 재클램프 — 풀림 routes.py:209 modifiers(max_length 5, `daf3628`) · 엔진 재클램프 HWAXAgentServer deliberation.py:1578-1586 (10-31 정리)
- [x] `HWAXAgentServer/deliberation.py` `_resolve_opts`: `modifiers` 파싱(화이트리스트 재클램프, 알 수 없는 키 드롭) → 검증: py_compile — 풀림 HWAXAgentServer deliberation.py:1578-1586 `_resolve_opts`(`c510300` — 화이트리스트 · 중복 제거 · 5 상한) · tests/test_delib_seats.py 의 얹을 층 시험 (10-31 정리)
- [x] 검증: `python -m py_compile deliberation.py` — 풀림 08-29 py_compile OK · 10-31 구문 확인(ast.parse) 통과, dev 엔진이 그 파일로 떠 있다 (10-31 정리)

## B. 엔진(③) — 두 엔진 정합 (JS = MCP, PY = 웹)
- [x] `infra/pipeline/hwax-deliberate.js` CHAIR_ITEMS: `diagnosis`(원인 규명 — FTA↔FMEA/is·is-not/ACH/cut set) — 풀림 infra/pipeline/hwax-deliberate.js:807 diagnosis(`daf3628`) · 지정 반증석 :163 (10-31 정리)
- [x] hwax-deliberate.js CHAIR_ITEMS: `option-select`(안 선택 — Pugh 2R/Flip 민감도) — 풀림 hwax-deliberate.js:809-810 option-select · 지정 반대석 :165 (10-31 정리)
- [x] hwax-deliberate.js CHAIR_ITEMS: `credibility`(신뢰 판정 — NASA-STD-7009/red-team/severe test) — 풀림 hwax-deliberate.js:817-818 credibility · 지정 red-team 석 :162 (10-31 정리)
- [x] hwax-deliberate.js: 산출 heading 맵에 3종 반영(진단 결정문/선택 결정문/신뢰 판정문) — 풀림 hwax-deliberate.js:839 산출 머리 셋(원인 규명 결정문 · 안 선택 결정문 · 신뢰 판정문) (10-31 정리)
- [x] hwax-deliberate.js: `MODIFIERS` 블록 정의 + BASE(또는 좌석 프롬프트)에 주입 — chairTemplate 무관하게 합성 — 풀림 hwax-deliberate.js:346 MODIFIERS · :361 MODIF_BLOCK 이 :365 BASE · :368 BASE_BLIND 에 chairTemplate 과 상관없이 실린다 (10-31 정리)
- [x] deliberation.py `_CHAIR_ITEMS`: 위 3종 미러(같은 키·같은 항목) — 풀림 HWAXAgentServer deliberation.py:547 · :562 · :577(`c510300`) — 두 엔진 정규화 뒤 바이트 일치(context-notes 08-29 파리티 검증) (10-31 정리)
- [x] deliberation.py: heading 맵 + MODIFIERS 주입 미러 — 풀림 deliberation.py:6275-6276 산출 머리 · :713 _MODIFIER_BLOCKS · :5735 mod_inject (10-31 정리)
- [x] 검증: `node --check hwax-deliberate.js` · `node --check hwax-sim-deliberate.js` · py_compile — 풀림 10-31 node --check hwax-deliberate.js · hwax-sim-deliberate.js 통과 · 엔진 구문 확인 통과 (10-31 정리)

## C. 프론트(②)
- [x] `frontend/src/components/chat/delibTaxonomy.ts` (신규) — Jobs 7 + Modifiers 5 단일 정본(3줄 가이드·engine·좌석 힌트·아이콘). HandoffBrief·DeliberatePage 공용 — 풀림 frontend/src/components/chat/delibTaxonomy.ts:29 JOBS · :50 JOB_GROUPS · :66 JOB_ROUTING · :84 MODIFIERS(`9e9cf60`) (10-31 정리)
- [x] `HandoffBrief.tsx`: 평면 `<select>` → 2층 메뉴(Job + Modifier 토글) + AI 추천 배너(추천 Job + 왜 + 1클릭) — 풀림 HandoffBrief.tsx:18 · :208(`9e9cf60` · `a68a2c2`) (10-31 정리)
- [x] `pages/DeliberatePage.tsx`: 상황 카드 메뉴(Screen B) 선행 → 고르면 질문·좌석 단계로 — 풀림 pages/DeliberatePage.tsx:13 · :109(`9e9cf60`) (10-31 정리)
- [x] `state/ChatContext.tsx`: `modifiers` 스레딩(startHandoff/continueDeliberation → delib_opts.modifiers) — 풀림 state/ChatContext.tsx:126 · :1115 · :1138 — extra.modifiers 를 delib_opts 로(`9e9cf60`) (10-31 정리)
- [x] 검증: 프론트 타입체크/빌드 — 풀림 08-29 tsc · vite build OK · 10-30 dist 번들에 택소노미가 들었다 (10-31 정리)

## D. 문서·반영
- [x] `decision-table.md` — 결정표(상황→Job) + 각 Job/Modifier 3줄 + 카피 규칙 + 계약 — 풀림 decision-table.md(`1f032e0`) (10-31 정리)
- [x] `context-notes.md` — 결정과 근거 기록(계속 갱신) — 풀림 context-notes.md(`1f032e0` 뒤 `6e16d16` · `20770e0` · `fe5c74d` · `ba2544f` · `3ce4f12`) (10-31 정리)
- [x] 커밋(시맨틱 단위: 계약 / 엔진 / 프론트 / 문서 분리) — 풀림 계약 + MCP 엔진 `daf3628` · 웹 엔진 `c510300` · 프론트 `9e9cf60` · 문서 `1f032e0` (10-31 정리)
- [x] 반영 주의(운영은 사용자 몫): agent-server 재기동 · 워크플로 sync · erag 재색인 — 풀림 dev 에이전트 서버 리스너 10-31 01:06 UTC ⊇ `c510300` · `5386f2d` · sync-workflows.sh --check rc 0 · cae00 기준 판 `969e723` ⊇ `c510300` — 지정 좌석은 합성 키라 색인할 카드가 없다 (10-31 정리)

---

## 카피 규칙 (혼동 최소화 — 사용자 지적)
1. 카드 헤드라인·"언제"는 **사용자 상황**(행동·목표 아님). "산출"은 항상 **결과 문서**(계획서/판정/규명).
2. 애매한 동사("구축한다·자동화한다")는 산출물 오해를 부른다 — 대상이 *계획*인지 *실행*인지 반드시 명시.
3. 방법론명(FTA↔FMEA·VoI…)은 서브텍스트. 사람은 이름 몰라도 상황으로 고른다.
