<!-- 시뮬·시험 심의 보강 — 설계·체크리스트(두 엔진 정합) -->
# 시뮬·시험 심의 보강 (2026-08-28)

기존 심의(sim-deliberate·test-plan)를 **좌석 추가 없이 되는 프로세스 보강**으로 강화한다. 인용 좌석은
모두 실재 전문가(카드 30~34장). 어설프지 않으려면 **두 엔진(MCP 워크플로 JS + deliberation.py 웹/챗)을
정합**시키고, 새 좌석을 **chairTemplate 이 실제로 소비**하게 한다(좌석만 앉히고 결정문이 안 쓰면 죽은 템플릿).

## 진단

- **sim 스파인**: V&V 중 **Verification**(방정식을 올바로 푸나 — formulation/discretization/verification)엔
  강하나 **Validation**(올바른 방정식인가=현실 대조)·**UQ**(불확실→출력 구간)가 없다.
- **test 좌석**: 측정가능성(rel-test-measurement)·민감도(xd-cae-modeling)·자원(xd-program)엔 좋으나
  **sim↔test 상관 계약**(이 시험이 무슨 sim 을 검증하나)과 **통계 설계**(표본수·검정력)가 없다.

## 설계 — SIM (soft-add, 기본 ON, 플래그로 끌 수 있음)

- **검증·UQ 다이어드 좌석 추가**: `xd-model-validity`(모델이 현실을 예측하나·유효 범위), `xd-uncertainty`
  (파라미터 불확실 전파·출력 구간). 스파인 리뷰어와 같은 급의 챌린저.
- **chairTemplate `sim-plan` 강화**(좌석을 실제로 소비):
  - (8) 검증 계획 → **검증 대상·수용임계·모델 유효 범위(외삽 위험)** 를 명시(validation 좌석 산출).
  - (9) 계산 규모 → **실제 자원 수치**(클러스터·코어·wallclock·라이선스·/data) 강제(HPC 현실성).
  - 출력 강제: 핵심 예측은 **점값이 아니라 불확실 구간**으로(UQ 좌석 산출).

## 설계 — TEST (좌석 2석 추가 + 계약 강화)

- **좌석 추가**: `xd-model-correlation`(sim↔test 다리 — 무엇을 어떤 임계로 대조), `rel-reliability-stats`
  (표본수·검정력·산포).
- **chairTemplate `test-plan` 강화**:
  - 신규 항목 **(10) sim 상관 계약**: 이 시험이 검증할 sim-plan 의 물리량·조건·수용임계를 명시(없으면
    시험이 무엇을 확인하는지 불명). 9항목 → 10항목.
  - (4)(8) 계측 불확실 예산(장비가 요구 분해능·불확실을 내나) 보강, (5) DOE·검정력(표본수 근거) 보강.
- **BASE_NOTE 강화**(test-plan.js): 상관 계약을 매 라운드 주입.

## 두 엔진 정합 (반드시 쌍으로)

| 변경 | MCP 워크플로(JS) | deliberation.py(웹/챗) |
|---|---|---|
| sim 검증·UQ 좌석 | `hwax-sim-deliberate.js` SPINE_VALIDATION + 플래그 | `_SIM_SPINE_VALIDATION` + env `DELIB_SIM_SPINE_VALIDATION` → `_SIM_FIXED_CAE` |
| sim-plan 강화 | `hwax-deliberate.js` CHAIR_ITEMS['sim-plan'] | `_CHAIR_ITEMS['sim-plan']` (동일 문구) |
| test 좌석 2석 | `hwax-test-plan.js` FIXED_SEATS | `_TEST_FIXED` |
| test-plan 강화 | `hwax-deliberate.js` CHAIR_ITEMS['test-plan'] | `_CHAIR_ITEMS['test-plan']` (동일 문구) |
| test BASE_NOTE | `hwax-test-plan.js` BASE_NOTE | (챗은 humanNote 로 주입 — 해당시) |

## 체크리스트 (완료 2026-08-28, 커밋 HWAXPortal 87a6cf2 · HWAXAgentServer 469ad5b)

- [x] SIM: JS SPINE_VALIDATION(+spineValidation 플래그) 배선, FIXED_CAE 합류(9석)
- [x] SIM: py `_SIM_SPINE_VALIDATION`(+env DELIB_SIM_SPINE_VALIDATION) 배선, `_SIM_FIXED_CAE` 합류
- [x] SIM: sim-plan CHAIR_ITEMS 강화 (JS·py — Validation·유효범위·불확실 구간·실제 자원 수치)
- [x] TEST: JS FIXED_SEATS +2석(model-correlation·reliability-stats), BASE_NOTE 강화
- [x] TEST: py `_TEST_FIXED` +2석
- [x] TEST: test-plan CHAIR_ITEMS 9→10항목 강화 (JS·py — 상관 계약·계측 불확실·통계·DOE)
- [x] 검증: node --check 3 JS ✓, py_compile ✓, 좌석수(SIM 9·TEST 5) ✓, 문구 정합 ✓, FIXED_ROLES·발굴제외 회귀 ✓
- [ ] **반영(사용자)**: deliberation.py 는 API 재기동, JS 는 `sync-workflows.sh` — 미실행

## 비목표

- 새 전문가 저작 안 함(좌석 실재). 카드 얇은 `rel-test-measurement` 심화는 별건(PaperAuthor).
- 좌석 과다 방지 — sim +2(검증·UQ), test +2(상관·통계)만. HPC 는 좌석 아닌 sim-plan (9) 강제항목으로.
