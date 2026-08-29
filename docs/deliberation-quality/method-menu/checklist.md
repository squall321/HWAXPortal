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
- [ ] `backend/app/agent/routes.py` DelibOpts: `chair_template: str|None` 필드 추가 → 검증: 웹 경로에서 model_dump 에 실려 나감 (현재 미선언이라 조용히 버려짐)
- [ ] routes.py DelibOpts: `modifiers: list[str]|None` (max_length=5) 추가 → 검증: 화이트리스트 밖 값은 agent-server 가 재클램프
- [ ] `HWAXAgentServer/deliberation.py` `_resolve_opts`: `modifiers` 파싱(화이트리스트 재클램프, 알 수 없는 키 드롭) → 검증: py_compile
- [ ] 검증: `python -m py_compile deliberation.py`

## B. 엔진(③) — 두 엔진 정합 (JS = MCP, PY = 웹)
- [ ] `infra/pipeline/hwax-deliberate.js` CHAIR_ITEMS: `diagnosis`(원인 규명 — FTA↔FMEA/is·is-not/ACH/cut set)
- [ ] hwax-deliberate.js CHAIR_ITEMS: `option-select`(안 선택 — Pugh 2R/Flip 민감도)
- [ ] hwax-deliberate.js CHAIR_ITEMS: `credibility`(신뢰 판정 — NASA-STD-7009/red-team/severe test)
- [ ] hwax-deliberate.js: 산출 heading 맵에 3종 반영(진단 결정문/선택 결정문/신뢰 판정문)
- [ ] hwax-deliberate.js: `MODIFIERS` 블록 정의 + BASE(또는 좌석 프롬프트)에 주입 — chairTemplate 무관하게 합성
- [ ] deliberation.py `_CHAIR_ITEMS`: 위 3종 미러(같은 키·같은 항목)
- [ ] deliberation.py: heading 맵 + MODIFIERS 주입 미러
- [ ] 검증: `node --check hwax-deliberate.js` · `node --check hwax-sim-deliberate.js` · py_compile

## C. 프론트(②)
- [ ] `frontend/src/components/chat/delibTaxonomy.ts` (신규) — Jobs 7 + Modifiers 5 단일 정본(3줄 가이드·engine·좌석 힌트·아이콘). HandoffBrief·DeliberatePage 공용
- [ ] `HandoffBrief.tsx`: 평면 `<select>` → 2층 메뉴(Job + Modifier 토글) + AI 추천 배너(추천 Job + 왜 + 1클릭)
- [ ] `pages/DeliberatePage.tsx`: 상황 카드 메뉴(Screen B) 선행 → 고르면 질문·좌석 단계로
- [ ] `state/ChatContext.tsx`: `modifiers` 스레딩(startHandoff/continueDeliberation → delib_opts.modifiers)
- [ ] 검증: 프론트 타입체크/빌드

## D. 문서·반영
- [ ] `decision-table.md` — 결정표(상황→Job) + 각 Job/Modifier 3줄 + 카피 규칙 + 계약
- [ ] `context-notes.md` — 결정과 근거 기록(계속 갱신)
- [ ] 커밋(시맨틱 단위: 계약 / 엔진 / 프론트 / 문서 분리)
- [ ] 반영 주의(운영은 사용자 몫): agent-server 재기동 · 워크플로 sync · erag 재색인

---

## 카피 규칙 (혼동 최소화 — 사용자 지적)
1. 카드 헤드라인·"언제"는 **사용자 상황**(행동·목표 아님). "산출"은 항상 **결과 문서**(계획서/판정/규명).
2. 애매한 동사("구축한다·자동화한다")는 산출물 오해를 부른다 — 대상이 *계획*인지 *실행*인지 반드시 명시.
3. 방법론명(FTA↔FMEA·VoI…)은 서브텍스트. 사람은 이름 몰라도 상황으로 고른다.
