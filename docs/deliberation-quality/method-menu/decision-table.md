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
| **리스크 심사** | 설계가 바뀌었다(스냅샷·그래프 diff) · 이 변경이 무엇을 깨뜨리나 | 변경 대상이 없음 · 원인이 이미 난 불량(→ 원인 규명) | 리스크 심사 보고서 · `risk_spec` | `risk-review` | 등록부 선례 · 커버리지 회계 · 기준선 옹호 지정석 |

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

### 리스크 심사 — `risk-review`
- **상황.** 과제의 설계가 바뀌었고(이전 과제 대비 또는 한 과제 안의 개념설계 변동), 그 변경이 어느
  도메인에서 무엇을 깨뜨리는지를 HW/XD 크로스도메인으로 훑어야 한다.
- **엔진이 강제하는 것.** 좌석마다 **도메인별 좌석 계약**(`_RISK_SEAT_CONTRACT` 16키)이 붙어 1R 발언 전
  자기 도메인 도구를 1회 이상 실호출하고 결과 수치·id 를 인용하게 한다. 인용 없는 주장은 [경험칙]으로
  등급이 내려간다. **기준선 옹호 지정석**(`delib-baseline-defender`)이 자동 착석해 "변경 전이 더 낫다"를
  적극 변호하고, 결정문은 8항목 + `risk_spec` 펜스로 낸다.
- **대표 좌석(초안).** 변경이 닿는 도메인(mech·xd·sim·rel·pcb·disp…) + 기준선 옹호(지정 반대석).
- **주의.** 이 Job 은 앱 `hwax_risk` 의 원장·등록부와 함께 쓸 때 커버리지 회계가 돈다. 앱 없이
  `chairTemplate:'risk-review'` 만 주면 단발 심의(원장 미연동)다.

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
| "설계가 이렇게 바뀌었는데 뭐가 문제되나 / 이전 과제 대비 리스크" | 리스크 심사 |
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
                            |'diagnosis'|'option-select'|'credibility'|'risk-review'   (하나)
delib_opts.modifiers[]     : 'voi'|'premortem'|'toulmin'|'eliminative'|'anon1r'  (0~5)
delib_opts.personas[]      : {key, role, origin?}  origin ∈ 'primary'|'counter' (그 밖·미지정은 'carry')
```

- 두 엔진이 같은 키를 쓴다. 알 수 없는 값은 agent-server(`_resolve_opts`)가 드롭·재클램프.
- **주의(수정 완료).** 종전 `routes.py` DelibOpts 에 `chair_template` 미선언 → 웹 경로에서 유실됐다.
  본 작업에서 `chair_template`·`modifiers` 를 DelibOpts 에 선언해 model_dump 에 실리게 한다.
- **`personas[].origin` 통과(추가).** `_resolve_opts` 가 `origin` 을 화이트리스트(`primary`·`counter`)로
  승계한다. 호출자(리스크 심사 러너)가 로스터석·반대 도메인석을 구분해 보내면 SSE `personas` 이벤트와
  결정문 (0) 커버리지 문단이 그 값을 그린다. **`origin` 을 안 보내는 기존 호출자는 종전대로 전 좌석
  `carry`** 다 — 동작 변화 0. `human_note`·`continue_summary` 는 리스크 심사 러너가 쓰지 않는다.

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

## 리스크 심사가 기존 심의에 주는 영향

`risk-review` 추가는 전부 additive 지만, **자유조회 도구 목록에 한 곳만 chair 무관 확장**이 있다.
정본으로 여기에 남긴다(계획 §6.5.2 통과경로 표).

| 상수 | 조건 | 다른 심의 영향 |
|---|---|---|
| `_RISK_KEEP_TOOLS` | `chair_template == 'risk-review'` 일 때만 | **0** — 조건부라 다른 심의는 1바이트도 안 바뀐다 |
| `_RISK_SEAT_CONTRACT` 좌석 계약 접미 | 같은 chair 조건부 | **0** |
| `_RISK_READ_TOOLS` | **chair 무관 · 앱 조건부** — `delib_apps` 에 그 앱을 고르면 열린다 | **있음(읽기 전용 확장)** — 아래 |

- **무엇이 늘어나나.** `chair_template` 이 무엇이든(`default`·`diagnosis`·`sim-plan` …) `delib_apps` 에
  `heax-step_forge` 를 고르면 `project_tree` · `interface_graph` · `inspect_report` · `mass_estimate` ·
  `mesh_report` · `part_mesh_map` **6종**이, `heax-kooremapper_mcp` 를 고르면 `inspect_file` ·
  `report_summary` · `report_case` · `report_findings` · `report_part_risk` · `report_energy_flow` ·
  `report_directional` · `report_worst_cases` · `report_part_series` · `report_scatter` ·
  `report_corpus` · `section_contact_usage` · `operation_usage` · `corpus_summary` **14종**이 좌석
  자유조회 목록에 새로 들어온다(합 **20종**). 이 20종은 전부 접두사 규칙 `_FREE_ALLOW` 에 걸리지 않아
  종전에는 목록에 없었다.
- **왜 chair 조건부로 막지 않았나.** 이 20종은 그 앱을 고른 심의가 원래 보고 싶어 하는 읽기 도구다
  (`interface_graph` 없이 StepForge 앱만 고르면 계면을 못 본다). 또 P5 에서 `heax-hwax_risk` 항목의
  `risk_*` 4종이 같은 경로로 열려야 **다른 심의(예 `sim-plan`) 좌석이 리스크 등록부를 자유조회**할 수
  있다(계획 §6.11). chair 조건부로 좁히면 그 경로가 죽는다.
- **안전 한계.** 20종 + `risk_*` 는 전부 **읽기 전용**이다. 쓰기 도구(`run_job`·`run_operation`·
  `set_interface`·`confirm_interfaces`·`remesh_parts`·`upload_*`·`add_training_data`·`create_object`·
  `update_object`·`link_objects`·`import_record`·`bind_records_to_agent`·`patch_agent`)는 어느 경로에도
  없다. `_FREE_DENY`(`get_agent_session`)는 모든 경로보다 우선한다. 앱 지정도 `risk-review` 도 아니면
  도구-앱 매핑 조회 자체를 하지 않으므로 종전 심의의 호출 수도 그대로다.
- `_RISK_KEEP_TOOLS` 8종 중 실제로 새로 열리는 것은 `pcb_warpage_surrogate` 하나뿐이다 — 나머지
  7종(`search_objects`·`get_object`·`get_subgraph`·`search_reports`·`predict_sed`·`check_design_rules`·
  `get_reference_cases`)은 이미 `search_`·`get_`·`predict_`·`check_` 접두사로 통과한다. keep 의 역할은
  `_narrow`(앱 제한)에서 잘려 나가지 않게 남기는 것이다.

---

## 두 엔진 정합 (반영)

- MCP JS `infra/pipeline/hwax-deliberate.js` CHAIR_ITEMS ↔ 웹 PY `HWAXAgentServer/deliberation.py`
  `_CHAIR_ITEMS` — 같은 키·같은 항목·같은 heading 맵.
- 반영. agent-server 재기동 · 워크플로 sync · erag 재색인(운영은 사용자 몫).

### 리스크 심사 파리티 표 (계획 §8.3.6)

| 항목 | 웹(deliberation.py) | MCP(hwax-deliberate.js) |
|---|---|---|
| 결정문 8항목 + risk_spec 펜스 | `_CHAIR_ITEMS['risk-review']` | `CHAIR_ITEMS['risk-review']` (바이트 동일) |
| 기준선 옹호 지정석 | `_CHAIR_ADVERSARY['risk-review']` 합성 push | `CHAIR_ADVERSARY['risk-review']` 합성 push |
| 좌석 계약 | `_RISK_SEAT_CONTRACT`(chair 조건부) | `RISK_SEAT_CONTRACT`(chair 조건부) |
| 지정 도구 tools ≤6 | 실호출·tool_inject | N/A(evidence-only) |
| 자유조회 free_tools·apps | `_RISK_READ_TOOLS`·`_RISK_KEEP_TOOLS` | N/A(evidence-only) |
| evidence ≤12 | 동일 예산 | 동일 예산 |
| 호출자 | 앱 러너 → 포털 `/agent/chat`(포털 PAT) → agent-server | 사람 → Claude Code 워크플로 → 게이트웨이 도구 |
| 원장·등록부·성격 저장 | 앱 러너 → 앱 `narrative.py` | 앱 MCP `risk_submit_panel_result` → 같은 `narrative.py` |
| 신원 | 포털 PAT(검증) · `credential service\|owner` | `actor`(미검증, `actor_verified:false`) |
| tool_mode | `tools` | `evidence_only`(C2 strong 비율 제외) |
| 제목 | doc_title '리스크 심사 보고서' | 삼항 '리스크 심사 보고서' |

- 세 정본(PY 상수 · JS 상수 · 앱 자산 `HWAXRisk/backend/app/assets/seat-contract.v1.json`)의 바이트
  동일은 `scripts/check_chair_parity.py` 가 검사한다(**exit 0 이 통과 기준**).

### 호출 경로 (계획 §6.7.1)

- **정본(웹).** 앱 러너 → `POST {포털}/agent/chat`(`Authorization: Bearer <포털 PAT>`, SSE). 포털이 PAT 의
  sub·email·groups 를 신원으로 채우므로 좌석 도구 스코핑이 '앱 자칭 그룹' 이 아니라 '검증된 PAT 의
  groups' 로 강제된다. conv_store 저장·감사로그·세마포어가 함께 붙는다.
- **폴백.** `HWAXRISK_AGENT_URL` 이 설정된 박스에서 정본 경로가 연결 오류 3회 연속일 때만 agent-server
  직결. 401/403 은 자격 문제라 폴백하지 않는다.
- **MCP.** 사람 → Claude Code 워크플로. 단발 심사는 `hwax-deliberate`(`chairTemplate:'risk-review'`),
  편성된 패널의 보충 회차는 L2 오케스트레이터 `hwax-risk-review`
  (`{targetKey, tier, panels?, actor?, model?}`, `tier:'A'` 는 웹 러너 전용이라 그대로 멈춘다).
- **앱 MCP 직접 등록(선택).** `claude mcp add --transport http hwax-risk <포털베이스>/apps/hwax_risk/mcp`
  (헤더 `Authorization: Bearer heax_pat_…`). 게이트웨이가 `heax-hwax_risk` 로 이미 흡수하므로 필수는 아니다.

### 반영 절차 (계획 §8.4.4 1항 — 엔진 부분만)

1. agent-server 재기동(`deliberation.py` 상수·`_g` 조립 조건·`_narrow`·좌석 계약 접미).
2. `infra/scripts/sync-workflows.sh`(`hwax-deliberate.js`·`hwax-risk-review.js` → `.claude/workflows`).
3. erag 재색인(`meta.whenToUse` 변경분).
4. `python3 scripts/check_chair_parity.py` **exit 0** 확인.

포털 창(타일·라우트)·앱 등록·app-data·게이트웨이 흡수·cae00 이관은 계획 §8.4.4 2~6항이며 운영은
사용자 몫이다.
