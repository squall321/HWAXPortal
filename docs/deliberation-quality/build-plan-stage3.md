# 3단 — 특화 파라메트릭 시뮬 모듈 구축 계획서 (`build-plan` chairTemplate)

설계 2026-08-27 · 대상 `infra/pipeline/hwax-deliberate.js`(새 chairTemplate) + `hwax-sim-deliberate.js`(3단) + 웹.
다각 설계(모델링자동화·페이즈로드맵·심의계약)→합성→요구대조 워크플로 산출.

> **구현 완료 (2026-08-27)** — `build-plan` chairTemplate + `hwax-sim-deliberate.js` 3단(opt-in `buildPlan:true`).
> 좌석은 **기존 실전문가 재사용**(신규 저작 0). MCP 경로만(웹 후속). 결정: c2(3단 phase)·기존좌석·MCP·opt-in.

## 0. 목표 재정의 (사용자 확정)

- ❌ OSS 셋업 자동화(허황) → ✅ **기존 OSS 솔버 위에 그 문제 특화 파라메트릭 시뮬 모듈을 개발하는 구체적 계획서**.
- 3단은 2단 `sim-plan`(해석 계획서)을 **고정 핵심으로 승계**해, 한 번 돌리는 해석을 **반복 실행형 파라메트릭 툴로 "구축"**하는 계획을 쓴다.
- 계획서의 본체 = **모델링 자동화** — 자산 3경로가 하나의 **정본 모델 IR** 로 수렴하는 것.

## 1. 산출 — 구축 계획서 12항목 (필수 8)

| # | 항목 | 필수 | 강제 구체성 |
|---|---|:--:|---|
| 1 | 모듈 목표·비목표 | ● | 반복 질문 1문장 + **입출력 스키마 필드** + 비목표(솔버 LLM 제작 아님·OSS셋업 아님) |
| 2 | 2단 sim-plan 10항목 승계 | | **고정 / 스윕 / 재검토** 분류표(양보불가 조항 포함) |
| 3 | 파라미터 스윕·DOE | ● | 변수·범위·수준·**총 케이스 N(숫자)**·반응 지표 |
| 4 | 모델링 자동화 A — Dyna 승계 | ●* | PID→SECID/MID 원장·`Group\Name` 규칙표·25 CONTACT_TIED 승계·MAT 재발급 대조 게이트 |
| 5 | 모델링 자동화 B — STEP 추출·메시 | ●* | 파트명 대조표(불일치 중단)·interfaces 교차검증·BREP→gmsh minSICN |
| 6 | 모델링 자동화 C — 2D 최소입력 | ●* | **3필드(part_name·dimension·direction)** 스키마·방향→normal·split_by_planes→ELEMENT_SHELL |
| **7** | **최소입력 계약·모델 IR 수렴·dry_run 게이트** | **● 크럭스** | 3경로 → **단일 정본 IR** + 자동추론 '닫힘' vs '사람 게이트' 경계 + **4종 매핑오류 비가역 게이트** |
| 8 | SW 아키텍처·자산 재사용·프로비넌스 | | 파이프라인 컴포넌트(재사용/신규)·입력 해시·툴 버전 고정 |
| 9 | 검증·회귀 3단 게이트 | ● | g1 골든 재현(**d3plot oracle**)·g2 물리 수렴·g3 스윕 정합, **임계값 숫자(예 ≤5%)** |
| 10 | 계산 규모·솔버 실행·오케스트레이션 | | 물리별 oss 좌석·코어시간×N·제출경로(slurm/STC) |
| 11 | 페이즈 로드맵 P1→P4 + 게이트 | ● | P1 수동골든→P2 자동화→P3 파라메트릭→P4 툴화, 각 **수치 통과/실패 게이트** |
| 12 | 자동화 한계 | ● | 승계 실패 범주·얼린 솔버 물리·추출 불가 기하·잔여 수작업 |

\* use-or-justify: 그 경로를 안 쓰면 **왜 안 쓰는지** 적어야 통과.

**크럭스 (7)**: "최소입력만으로 모델링 자동화"라는 역학 시뮬 최대 난제를 실제로 닫는 자리. 3경로(Dyna/STEP/2D)가 **하나의 정본 모델 IR** 로 수렴하지 않으면 자동화가 3개의 별개 스크립트로 흩어져 무의미. 스윕 진입 전 **dry_run 매핑오류 게이트 4종**(중복/junk 이름·재료 유사매칭 오인·접촉 penetration 이 tied 로 샘·단위/밀도 자릿수)을 사람 승인 없이 못 넘게.

## 2. 3단 좌석 — 기존 실전문가 재사용 (신규 저작 0)

설계 초안이 지어낸 이름(xd-cad-geometry 등)은 없지만, 그 도메인의 **실전문가가 이미 저작·AIDataHub 색인**돼 있어 그대로 재사용한다(구현됨). cae-modeling·rigor-review 는 2단 스파인이라 3단에도 이어 앉히고, 2단에서 선택된 oss 솔버·물리 유임은 carry.

| 실 좌석 | records | 역할 | 책임 항목 |
|---|---|---|---|
| `xd-mcad-geometry` | 85 | STEP 하이라키·파트 추출·인터페이스·2D 슬라이스 | (5)(6) |
| `xd-lsdyna` | 34 | `Group\Name`·MAT·CONTACT·BOUNDARY/INITIAL 승계 규칙 | (4) |
| `xd-system-architecture` | 55 | 파라메트릭 툴 구조·**모델 IR 계약**·재사용 경계 | (8)(7) IR |
| `xd-virtual-doe` | 52 | 스윕·DOE(요인/수준/응답·설계행렬)·응답면·감도 | (3)(9 g3) |
| `xd-version-provenance` | 45 | 승계 원장·해시·dry_run 게이트·재현성 | (7)(8)(9) |
| `xd-cae-modeling` | 128 | 전처리·메시 자동화(2단 스파인 재사용) | (7) 메시 |
| `xd-cae-rigor-review` | 12 | 엄밀성·완전성 게이트(2단 스파인 재사용) | 게이트 |
| (carry) oss 솔버 · 물리 유임 | — | 어느 솔버 위에 얹나 + 물리 왜곡 감시 | 전반 |

**모두 저작된 실전문가라 그라운딩이 자동으로 붙는다** — 신규 저작 불요. 남은 한계: 기존 카드는 일반 도메인 지식이지 StepForge·KooD3plotReader 사내 도구 API 특정은 아니다(humanNote 로 도구 우선 재사용 주입). 도구-특정 카드 보강은 후속(사내 도구가 보편화되면).

## 3. 배선 (구현됨)

- (A) `hwax-deliberate.js` `CHAIR_ITEMS['build-plan']` — 12항목 문자열(백슬래시 `\\` 이스케이프, 렌더 검증됨). (B) 산출 제목 삼항에 `build-plan → '구축 계획서'` 분기.
- (C) **c2 채택** — `hwax-sim-deliberate.js` 에 3번째 phase '구축설계'. **opt-in `buildPlan:true`**(기본 false, 기존 2단 무변경). `buildRounds`(기본 3).
- (D) 승계: `continueFrom:{ summary: sim.decision, roundsSoFar: R1+R2, nonNegotiables: 2단 최종 non_negotiable }`.
- (E) 좌석: 위 표(§2). (F) `groundCards:true` + humanNote(사내 자산 우선·최소입력·모델 IR 수렴·dry_run·페이즈 게이트 비우지 마).
- (G) 3단 켜지면 최종 RA 보고서·대화는 3단이 한 번만(2단은 중간 산출로 저장 안 함).

## 4. 실행

```
Workflow({ name: 'hwax-sim-deliberate', args: JSON.stringify({
  question, context, personas: [1단 좌석], buildPlan: true   // ← 3단 켜기
}) })
```
→ 메커니즘 → 해석 계획서 → **구축 계획서** 순으로 흐른다.

검증: 문법(async 래핑)·build-plan 템플릿·백슬래시 렌더·3단 좌석(9인 dedup·재사용)·워크플로 sync 통과. **실 심의 E2E 는 게이트웨이 MCP + GLM 필요 = cae00 몫**(재기동 후 buildPlan:true 로 1건).

**후속(미착수)**: 웹 경로(deliberation.py) 3단, StepForge·KooD3plotReader 도구-특정 카드 보강.
