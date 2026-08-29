<!-- 심의 방법 결정표 — Jobs(1층)·Modifiers(2층) 단일 정본 레퍼런스 -->
# 심의 방법 결정표 — Jobs · Modifiers 가이드

심의를 시작할 때 **무엇을 하는 심의인지(Job)**를 하나 고르고, 필요하면 **얹을 층(Modifier)**을
켠다. 방법론(FTA↔FMEA·Pugh·NASA-7009·VoI…)은 엔진으로 숨기고, 사람은 자기 상황으로 고른다.

- **1층 Job** — 목적. 하나만 고른다. `chair_template` 하나로 매핑.
- **2층 Modifier** — 굴리는 방식. 여럿 켤 수 있다. `modifiers[]` 로 합성.
- **산출은 언제나 결정 문서** — 계획서·판정·규명 결과. 실행(코드 빌드·시험 수행)이 아니다.

---

## 1층 — Jobs (목적, 택1)

| Job | 언제 | 언제 아님 | 산출 | 엔진(chair_template) | 방법론 |
|---|---|---|---|---|---|
| **원인 규명** | 원인 불명 · 특정 로트/조건만 · HW+SW+공정 얽힘 | 원인이 뻔함 · 안을 고르는 문제 | 지배원인 후보 · cut set · 미지영역 | `diagnosis` | FTA↔FMEA · KT is/is-not · ACH |
| **안 선택** | 안이 2개+ · 트레이드오프로 못 정할 때 | 안이 하나뿐 · 원인 규명이 먼저 | 선택안 · 하이브리드안 · 뒤집힘 임계 | `option-select` | Pugh 2R · Flip |
| **신뢰 판정** | 이 해석/결정 믿어도 되나 · go/no-go | 아직 안 만듦 · 탐색 단계 | 신뢰도 채점 · 생존/기각 · 조건부 승인 | `credibility` | NASA-STD-7009 · red-team · severe test |
| **해석 설계** | 이 물리를 무엇으로 어떻게 계산할지 | 계산이 필요 없는 문제 | 해석 계획서 · sim_spec | `sim-plan` (전반부 `mechanism`) | 식별성 · V&V · UQ |
| **시험 설계** | 무엇을 어떤 시험으로 언제 확보할지 | 시험이 필요 없음 | 시험 계획서 · 상관 계약 | `test-plan` | 우선순위 · DOE · sim 상관 |
| **구축 계획** | 같은 해석을 형상·조건 바꿔 여러 번 돌릴 때 | 1회성 해석 | 구축 계획서 · P1~P4 게이트 | `build-plan` | 모델링 자동화 · 모델 IR · 스윕 |
| **자유 심의** | 위에 안 맞음 · 보고서 통째 복붙 심의 | — | 의사결정문 | `default` | 변증법적 적대 패널 |

> `mechanism`(해석 전 인과사슬 확정)은 top-level Job 이 아니라 **해석 설계의 전반부**다.
> sim-deliberate 가 mechanism→sim-plan 으로 연쇄한다.

### 원인 규명 — `diagnosis`
- **상황.** 필드/라인에서 불량이 나는데 원인이 여러 도메인에 얽혀 있고, 특정 로트·조건에서만 난다.
- **엔진이 강제하는 것.** 결함 사슬(FTA)과 양식(FMEA)을 양방향으로, KT is/is-not 로 경계를 좁히고,
  경합 가설을 증거로 가중(ACH)해 **지배원인 후보와 cut set, 아직 모르는 영역**을 낸다. 조치는 다음 일.
- **대표 좌석(초안).** 신뢰성·불량분석(rel-fa) · 품질/공정 · 해당 물리 도메인 · (SW 관여 시)SW.

### 안 선택 — `option-select`
- **상황.** 설계안이 둘 이상이고 트레이드오프(성능↔원가↔신뢰성)로 못 정한다.
- **엔진이 강제하는 것.** Pugh 2라운드 — 기준·가중을 먼저 합의하고 채점한 뒤, 하위안의 장점을 흡수한
  **하이브리드안**을 만들어 재채점한다. Flip — **무엇이 얼마 바뀌면 순위가 뒤집히나**(민감 임계)를 낸다.
- **대표 좌석(초안).** 설계 · 원가 · 신뢰성 · 제조/양산성 · 해당 도메인.

### 신뢰 판정 — `credibility`
- **상황.** 해석 결과나 결정을 실제로 믿고 가도 되는지(go/no-go)를 판정해야 한다.
- **엔진이 강제하는 것.** NASA-STD-7009 신뢰도 축(입력 데이터·검증·불확실성·모델 성숙도·인력)을 축별로
  **채점**하고, red-team 이 결론을 **적극적으로 깨보며**, severe test(가장 깨지기 쉬운 예측이 살아남았나)로
  **생존/기각/조건부 승인**을 낸다. 점수의 근거를 반드시 붙인다.
- **대표 좌석(초안).** V&V · UQ · 해당 물리 도메인 · red-team(반대 지정석).

### 해석 설계 / 시험 설계 / 구축 계획 / 자유 심의
- 기존 엔진 그대로. 상세는 각 엔진 정의(hwax-deliberate.js CHAIR_ITEMS)와
  `../sim-spec-standardization.md`(sim_spec)·`../sim-test-reinforcement.md` 참조.

---

## 2층 — Modifiers (얹을 층, 다중)

| Modifier | 언제 | 산출 효과 | 방법론 |
|---|---|---|---|
| **교착 정산** `voi` | 패널이 값으로 못 가르고 막힘 · sim/계측 데이터 있음 | "무엇을 재면 결론이 갈리나"를 계산으로 전환 → 측정 우선순위 | Value of Information |
| **사전부검** `premortem` | 결정이 굳기 전 실패를 미리 막고 싶을 때 | 5분간 "이미 실패했다" 가정하고 실패 경로 먼저 열거 → 방어책 | Pre-mortem (Klein) |
| **논증 엄밀** `toulmin` | 주장이 근거 없이 세질 때 | 주장→근거→**warrant(왜 근거가 주장을 지지하나)**를 명시 강제 | Toulmin |
| **완결 기준** `eliminative` | "언제 끝인지" 모호할 때 | defeater(반증 요인) 유형을 열거하고, 다 처리되면 종료 선언 | Eliminative induction / GSN |
| **익명 1R** `anon1r` | 초반 쏠림·거수기 우려 | 1라운드는 서로 안 보고 독립 추정부터 → 이후 공개 심화 | IDEA / Delphi 유용부분 |

- Job 이 "무엇을 산출하나"라면 Modifier 는 "어떻게 더 엄밀하게/안전하게 굴리나". 직교하므로 아무 Job 에나 얹는다.
- 주입 방식. 각 Modifier 는 정의된 지시 블록을 심의 BASE 에 덧붙인다(evidence 주입과 같은 오버레이).
- 남용 금지. 다 켜면 프롬프트가 비대해진다. 상황에 맞는 1~2개를 권장(추천 로직이 선제안).

---

## 결정표 (증상 → Job)

| 이런 말이 나오면 | Job |
|---|---|
| "왜 이렇게 됐는지 모르겠다 / 특정 로트만 / 재현이 애매" | 원인 규명 |
| "A안이냐 B안이냐 / 뭘 골라야 할지" | 안 선택 |
| "이 결과 믿어도 되나 / 양산 가도 되나" | 신뢰 판정 |
| "이걸 어떻게 계산하지 / 무슨 솔버로" | 해석 설계 |
| "뭘 시험해야 하지 / 무슨 데이터를 확보" | 시험 설계 |
| "이 해석을 형상만 바꿔 계속 돌리고 싶다" | 구축 계획 |
| 위에 안 맞거나 남의 보고서로 심의 | 자유 심의 |

---

## 카피 규칙 (혼동 최소화)

불분명한 산출물 메시지가 가장 큰 사용 혼동을 부른다. 메뉴/카드 문구는 다음을 지킨다.

1. **상황이 헤드라인, 방법론은 서브.** "왜 이렇게 됐나"를 크게, `FTA↔FMEA`는 작게. 이름 몰라도 고른다.
2. **"언제"는 사용자 상황**(행동·목표 아님), **"산출"은 결과 문서**(계획서/판정/규명)로 명명한다.
3. **애매한 동사 금지.** "구축한다·자동화한다"는 *툴을 짜는 것*으로 오해된다 — 대상이 *계획*인지
   *실행*인지 반드시 붙인다(예: "반복 파라메트릭 툴로 구축" → "같은 해석을 반복해 돌릴 때 · 산출=구축 계획서").
4. 메뉴 상단에 한 줄. "무엇을 고르든 산출은 근거가 붙은 결정 문서 — 프로그램을 짜는 게 아니라 판단이 나온다."

---

## 계약 (delib_opts)

```
delib_opts.chair_template : 'default'|'mechanism'|'sim-plan'|'test-plan'|'build-plan'
                            |'diagnosis'|'option-select'|'credibility'   (하나)
delib_opts.modifiers[]     : 'voi'|'premortem'|'toulmin'|'eliminative'|'anon1r'  (0~5)
```

- 두 엔진이 같은 키를 쓴다. 알 수 없는 값은 agent-server(`_resolve_opts`)가 드롭·재클램프.
- **주의(수정 완료).** 종전 `routes.py` DelibOpts 에 `chair_template` 미선언 → 웹 경로에서 유실됐다.
  본 작업에서 `chair_template`·`modifiers` 를 DelibOpts 에 선언해 model_dump 에 실리게 한다.

---

## 세 진입 맥락 (UX)

- **A. 챗에서 이어가기 — 추천 우선.** AI 가 대화를 읽고 Job 하나를 "왜"와 함께 추천, 1클릭 시작.
  관련 Modifier 는 선제안(예: sim 데이터 있으면 교착 정산). `HandoffBrief.tsx`.
- **B. 새 심의 시작 — 상황 카드.** 맥락이 없으니 상황 카드 그리드(판단/계획/자유 그룹)로 고르게 한다.
  `pages/DeliberatePage.tsx`. "모르겠음 → 질문부터"는 A 의 추천 흐름으로 넘긴다.
- **C. MCP / Claude Code — 스킬 인자.** 포털 UI 가 없으므로 Claude 가 사용자 의도를 읽어 유형을 고른다.
  진입 표면은 워크플로 `meta.whenToUse`(hwax-deliberate·-sim-deliberate·-test-plan)에 유형·얹을 층을
  카탈로그로 실어 Claude 가 인지·선택하게 한다 — `Workflow({name:'hwax-deliberate', args:{question,
  chairTemplate, modifiers}})`. 유형 선택=chairTemplate, 얹을 층=modifiers[]. 지정 반대석은 엔진이 자동 착석.
- 목업. `scratchpad/delib-method-mockup.html`(Artifact) — A·B 두 화면 나란히.

---

## 두 엔진 정합 (반영)

- MCP JS `infra/pipeline/hwax-deliberate.js` CHAIR_ITEMS ↔ 웹 PY `HWAXAgentServer/deliberation.py`
  `_CHAIR_ITEMS` — 같은 키·같은 항목·같은 heading 맵.
- 반영. agent-server 재기동 · 워크플로 sync · erag 재색인(운영은 사용자 몫).
