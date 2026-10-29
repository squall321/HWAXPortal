# 분석 루틴 — 내 권한의 플랫폼을 순서대로 엮어 표준 보고서까지(계획, 10-29)

절차 탭에서 **플랫폼 연쇄**(단계마다 플랫폼 + 그 단계에서 할 일)를 짜 둔다. 챗(Qwen)에서 그 루틴을 골라 켜거나 개인 Claude 가 MCP 로 부르면,
같은 연쇄 · 같은 기록 · 같은 보고서 꼴로 분석해 Report Archive 초안까지 간다.

- 상태 — **계획**(10-29). 조사 넷(절차 기능 · 챗 루틴 모드 · MCP 길 · 예시 연쇄의 플랫폼 지도)을 합쳤다. 사용자 결정(8절)을 받은 뒤 R0 계약부터 짓는다.
- 체크리스트 `checklist.md` · 판단과 까닭 `context-notes.md`.

## 1. 요청(사용자 10-29)

- 지금 챗은 질문마다 의미 검색으로 플랫폼을 고른다. 나만의 분석 루틴을 커스터마이징하고 싶다.
- 절차 탭에서 **지금 내게 권한이 있는 플랫폼** 몇 개를 **특정 순서**로 엮는다.
- 챗에서는 그 조합을 고를 수 있고, 켜져 있으면 지정한 플랫폼 연쇄로 보고서를 쓰는 루틴이 된다. 챗은 지금처럼 Qwen 이다.
- MCP 로도 등록해 웹에서 설정한 루틴대로 Claude 가 분석할 수 있게 한다.
- 예시 연쇄 — FailureTrace 시장불량 → SignalForge VOC → PLM 문제점 → 심의로 메커니즘 → FMEA 로 시험 → ECAD 불량 net → 시뮬레이션 플랫폼 →
  인사이트 → 기존 사람 보고서 인용 → Report Archive 업로드.

## 2. 지금 있는 것 — 조사 근거(10-29 코드 기준, 줄 번호 대신 이름)

### 2.1 절차(procedures) — 결정적 재생 엔진

- 기록이 곧 절차다. 장치는 `{{var}}` 치환 · `save` 추출 · `select` · `assert` 뿐이고 분기 · 반복 · LLM 이 없다(`docs/procedures/PLAN.md` §4).
- 보증은 **저장 때 고정된 인자** 위에 선다 — `schema_fp` · 모르는 인자 거부 · `MUST_GATE` · 비밀 상수 검사 · 참조 풀이(`procedures/models.py` `validate_spec`).
- 저장소 `procedures.sqlite`(설정 · services.yaml · 백업 · main 네 곳에 이미 등록), 원장 `runs` · `run_steps`(덧붙이기만, 인자 sha256 · 결과 gzip),
  판은 불변, 공개 범위 all | private. 챗 턴의 도구 호출도 같은 원장에 남는다(`from_chat.record`, origin chat).
- 신원 — 호출마다 사람 PAT 를 15분짜리로 찍는다(`procedures/pat.py`, `purpose=procedure`). 게이트웨이는 이 PAT 에만 `invoke_tool` 의 정확이름 파괴 차단을
  면제한다('사람이 이 인자를 승인했다' 는 전제).
- 문(gate) — 대입된 인자의 sha256 에 묶인 사람 확인. 권한은 `feat:procedures`. 화면은 탭 셋(만들기 · 절차 · 실행 이력).
- MCP 표면은 없다(S7 미구현). 브라우저 세션으로만 부른다.

### 2.2 챗(에이전트 서버)

- 한 턴은 ReAct 하나다 — `AGENT_RECURSION_LIMIT` 80(연속 왕복 약 39), 챗 idle 900초. 10-29 QA 의 여러 허브 질문 EX-03 은 호출 25 · 541초였다.
- 핀은 울타리가 아니다 — `pinned_apps` 는 셋까지 우선순위이고 프롬프트도 '다른 도구 사용 금지는 아니다' 라 말한다. `_GUIDE_TOOLS`(search_tools · invoke_tool ·
  list_tool_apps · recommend_agents)는 늘 묶여 `invoke_tool` 로 아무 도구나 부를 수 있다. 10-29 QA 에서 코어 질문이 FMEA · ARP · MatNexus 로 샌 길이다.
- cae00 은 창의 45%(88,473 토큰)까지 도구 설명을 싣는다. 10-29 QA 의 질문당 평균 프롬프트 108,275 토큰 가운데 약 80% 가 도구 설명이다.
- 이어 쓸 것 — 심의 넘김(`/심의` + `delib_opts.evidence` [{source, tool, args, result}] 120건까지), `/보고서`(`run_report_save` → `create_report_draft`
  template `deliberation` v1 · `_ra_blocks` 2,000자 나눔 · 사람 PAT), 띵킹(코드가 짠 여러 LLM 호출의 선례), `_detach_stream`, 자기검증.
- 포털 중계는 허용 목록의 칸만 넘긴다 — 새 칸은 포털 `ChatRequest` 와 에이전트 `ChatRequest` 두 곳에 선언하지 않으면 조용히 버려진다.

### 2.3 게이트웨이

- 로컬 도구가 호출자 PAT 를 포털로 넘기는 선례가 있다(`save_conversation` · `search_conversations` — 포털이 PAT 주인을 소유자로 쓴다).
- 권한 — `_visible_tools`(거부 · 숨김 · 시험 사본 빼기) · 호출마다 `_backend_allowed` · `_needs_connect`(RA · TestScope 토큰 미등록) · 읽기 전용 PAT · 감사 `corr`.
- MCP prompts 는 없다(FastMCP 기본 `[]`) — 도구 · 리소스처럼 덮어 달 수 있다.

### 2.4 예시 연쇄의 플랫폼 지도

| # | 단계 | 백엔드(있는 박스) | 대표 도구(읽기) | 신원 | 빈 곳 |
|---|---|---|---|---|---|
| 0 | 기준 키 | `rootdesigndatahub` 코어 허브(cae00) | `object_resolve` · `search` · `object_get` · `graph_neighbors` | 서비스(확인 필요) | 응답 95k ~ 217k자 · `candidates` 는 사람이 고른다 · 마케팅 이름 별칭 빔 |
| 1 | 시장불량 | `failuretrace`(cae00) | `failuretrace_search` · `_objects_summary` · `_graph_neighbors` | 서비스 | `pd_defect` 가 시장불량인지 생산 불량인지 불분명 · 솔더 묶음 오탐 · 이름 가림 없음 |
| 2 | VOC | `signalforge`(dev · cae00) | `resolve_product_keyword` → `search_voc` · `defect_profile` · `defect_evidence` | 서비스 | P8 · PH8 가 한 제품 코드(EX-03 잘못된 제품) · 코어 고장 모드 ↔ 증상 대응 없음 |
| 3 | PLM 문제점 | `plm-defect`(cae00) | `plm_defect_search`(enrich=0) · `plm_case_detail` · `plm_similar_cases` | 서비스 | PLM 작업 보류(사용자 결정) · 쿼터를 수집기 · 웹과 나눈다 |
| 4 | 메커니즘 | `hwax-deliberation`(dev · cae00) | `deliberate_start`(job mechanism · diagnosis, evidence) → `_status` · `_result` | 사람 | 근거 예산 약 120건 · 50,400자(20만 창) · 분 ~ 시간 · RA 초안을 스스로 남긴다 |
| 5 | 시험(FMEA) | `fmea` 외부 연결(cae00) + 코어 `graph_neighbors(detects …)` | `gather_evidence_tool` · `list_candidate_specs` · `get_spec_details` | 사람 토큰 | readOnlyHint 없음 · 개인 PC 서버 · 코어 키를 안 쓴다 |
| 6 | ECAD 불량 net | `odb-hub`(cae00) | `find_job` → `list_parts` · `get_part_detail`(핀별 net) | 서비스 | net 목록 · net → 핀 조회 없음 — 의심 refdes 가 있어야 net 이 나온다 |
| 7 | 시뮬레이션 | DynaForge · RA analysis · ARP · SmartTwin · ste | `task_revisions` · `find_reports` · `report_*` · `get_analysis_summary` | 플랫폼마다 | 대개 비거나 '이 키로 못 찾음' — 그것도 결과로 적는다 |
| 8 | 기존 보고서 | `reportarchive` · `mx-white-paper` · `ai-data-hub` | `search_reports` · `get_report` · `search_documents` · `hybrid_search` | RA 는 사람 토큰 | RA 코어 소스 오등록(O-7) — 코어 키로 못 거른다 |
| 9 | 인사이트 · 올리기 | gateway · `reportarchive` | `verify_answer` → `create_report_draft` → (사람) `preview_publish` · `publish_report` | 사람 토큰 | `publish_report` 는 MUST_GATE · dev 는 RA 가 내려가 있다 |

dev 에는 0 · 1 · 3 · 5 · 6 이 없고 RA 가 내려가 있다. **예시 연쇄의 실주행은 cae00 몫이다**(9절).

## 3. 설계 — 권고(AR-D1 ~ AR-D10)

- **AR-D1 루틴은 절차와 다른 종류다.** 같은 저장소(`procedures.sqlite`)에 다른 표 · 다른 스펙(`RoutineSpec`)을 둔다. 절차의 보증은 고정 인자 위에 서 있어 LLM 이
  실행 때 도구와 인자를 고르는 단계에 맞지 않는다 — `ProcedureSpec` 에 LLM 단계를 넣지 않는다. Var · 불변 판 · 공개 범위 · YAML 내보내기 · 원장
  (`runs` · `run_steps`, `trigger_kind=routine`)은 그대로 쓴다. 단계 하나가 절차를 품을 수 있다(`kind: procedure` — 결정적 하위 단계, 그 문 · 판정 그대로).
- **AR-D2 단계는 코드가 돈다.** 한 턴 ReAct 에 단계를 적어 주는 길은 하지 않는다 — 왕복 상한 · 한 맥락에 쌓이는 결과 · 울타리 없는 핀. 단계마다
  - 그 플랫폼 도구만 묶는다 — `search_tools` · `invoke_tool` 은 단계에 없다. '확정 종결' · 새어 나온 `<tool_call>` 직접 실행도 단계 허용 목록 안에서만.
  - 예산(호출 수 · 초)을 둔다. 단계마다 도구 설명이 그 앱 몫만 실려 고정비가 80 ~ 95% 준다(SignalForge 약 8.9k 토큰 · StepForge 151개는 부분집합).
  - 상태는 **코드가 정한다** — ok · empty · ambiguous · denied · not_connected · unavailable · failed · skipped. 빈 결과는 그 플랫폼의 사유(diagnosis ·
    reason · notes)를 싣고, '이 박스에 없음' 을 '없다' 로 적지 않는다.
  - 작업 기억(키 · 근거 id · 요약)은 코드가 쥔다. 키는 **그 단계 도구 결과에 그 값이 나왔을 때만** 기억에 든다 — 지어낸 키와 잘못 이은 제품을 막는다.
- **AR-D3 하나의 계약, 두 실행자.** 정의 · 실행 상태 · 원장 · 보고서 렌더는 포털(`/routines-api`)이 쥐고, 단계 울타리와 기록은 게이트웨이 `routine_call` 한 곳이
  맡는다. Qwen(에이전트 서버 `routine.py`)과 Claude(MCP)가 같은 도구를 같은 계약으로 부른다 — 다른 것은 순서를 쥔 쪽(코드 대 Claude)과 생각하는 LLM 뿐이다.
- **AR-D4 신원은 실행하는 사람이다(작성자 아님).** LLM 이 고른 호출은 절차 PAT(`purpose=procedure`)로 **절대** 나가지 않는다 — 챗 PAT 또는 개인 PAT 로
  나가 정확이름 차단을 그대로 받는다. RA · FMEA · TestScope 토큰은 시작 전 점검하고, 없으면 그 단계는 not_connected 다(서비스 계정으로 떨어지지 않는다).
- **AR-D5 단계 안에서 쓰지 않는다(v1).** 이미 있는 결과만 읽는다 — 작업 제출 · 덮어쓰기 · FMEA 오버레이는 막는다('심의는 작업을 제출하지 않는다' 와 같은 규칙).
  예외는 둘 — 심의 단계의 `deliberate_start`(루틴의 단계 종류로) · 끝의 RA 초안. MUST_GATE(`publish_report` 등)는 루틴이 부르지 않는다.
- **AR-D6 기준 키가 먼저다.** 연쇄의 첫 단계는 기준 키 풀기(코어 허브 `object_resolve` · `core_vocab.json` 정본)다. 후보가 여럿이면 사람에게 묻고 멈춘다.
  단계마다 실제로 쓴 키를 기록하고 보고서에 낸다(EX-03 처럼 VOC 가 다른 제품을 말하는 것을 보이게).
- **AR-D7 보고서는 단계에서 나온다.** 단계 제목이 절 제목이고, 절은 그 단계의 검증된 출력(요약 · 수치 · 근거 id)으로 쓴다. 인사이트 절은 근거 id 를 인용해야
  한다. 코드가 덧붙이는 것 — 근거 부록(원장의 호출 · 결과 id) · 커버리지(한 단계 · 건너뜀 · 권한 없음 · 이 박스에 없음, 숨기지 않는다) · 출처 없는 수치 표지.
  RA 는 기존 `deliberation` v1 블록 꼴로 올린다(`_ra_blocks` 나눔과 같은 계약 시험). 루틴 전용 RA 템플릿은 RA 팀 몫이다(리포 hands-off).
- **AR-D8 오래 돈다.** 떼어 낸 작업으로 돈다(탭을 닫아도 계속). 단계가 끝날 때마다 원장에 남긴다. 에이전트 서버가 재기동되면 interrupted 이고 저절로 다시
  돌지 않는다(사람 PAT 를 잃는다). '이어서' 는 새 PAT 로 끝난 단계를 건너뛴다. 동시 실행 상한(기본 2 — stcx Qwen 은 챗과 나눠 쓴다) · update-all 은 도는
  루틴이 있으면 심의처럼 기다린다.
- **AR-D9 심의 단계는 원자료를 넘긴다.** 앞 단계의 원 근거(도구 · 인자 · 결과)를 `evidence` 로 넘긴다 — 정리한 결론을 넘기지 않는다(심의 헌법 P1).
  엔진은 두 길 모두 서버 심의 엔진이다.
- **AR-D10 dev 는 꼴, cae00 은 실주행.** dev 시험의 가짜는 cae00 `tools/list` 스냅샷 · 기록한 실패 응답(isError false 오류 봉투 · not_configured ·
  토큰 미등록 거부) 꼴 그대로 만든다. dev 에 있는 플랫폼(SignalForge · 심의 · DynaForge · StepForge · MaterialTwin)으로 짧은 연쇄를 실주행한다.
  예시 연쇄의 받아들이기는 cae00 에서 사람이 한다(request-1029 C-31).

## 4. 계약 초안 — R0 에서 굳힌다

### 4.1 RoutineSpec

```yaml
title: 시장불량 원인 분석
purpose: "{{model}} 의 {{symptom}} 시장불량 — 원인 · 시험 · 대책"
vars:
  - {name: model, label: 모델, type: string, required: true}
  - {name: symptom, label: 증상, type: string, required: true}
anchor: {var: model, type: plm_model}            # 코어 허브 object_resolve — 후보가 여럿이면 묻는다
steps:
  - id: ft
    title: 시장불량 이력
    kind: platform                               # platform | procedure | deliberation | cite
    platform: failuretrace                       # 권한표(access.yaml + 박스 표)의 플랫폼 id → 게이트웨이 백엔드
    goal: "{{anchor.key}} 의 {{symptom}} 불량 기록을 유형 · 시기별로"
    tools: []                                    # 선택 — 비면 그 플랫폼 도구 전부(울타리는 플랫폼)
    uses: []                                     # 앞 단계 출력(요약 · 키 · 근거 id)
    expect: {keys: [failure_mode], fields: {period: string}}
    budget: {calls: 6, seconds: 300}
    on: {empty: continue, denied: skip, unavailable: skip}
  - id: delib
    title: 메커니즘
    kind: deliberation
    uses: [ft, voc, plm]
    deliberation: {job: mechanism}
report:
  title: "{{model}} {{symptom}} 분석"
  sections: [ft, voc, plm, delib, fmea, ecad, sim, cite, insight]
  ra: {template: deliberation, upload: ask}      # ask | auto | off — 8절 Q1
limits: {minutes: 60, calls: 60}
visibility: private                              # private | all — 8절 Q6
```

### 4.2 단계 봉투 — 두 실행자가 같은 꼴로 원장에 남긴다

`{status, reason, keys_out, summary_md, findings[{text, refs}], evidence[{id, source, tool, args, result_ref, key}],
provenance{backend, tool(원래 이름), args_sha, ts, as: user | service}, truncated{total, returned}}`

### 4.3 MCP 도구(게이트웨이 로컬 — 호출자 PAT 를 포털로 넘긴다)

| 도구 | 하는 일 |
|---|---|
| `routine_list` | 내가 볼 수 있는 루틴과 단계마다 지금 부를 수 있나(권한 · 토큰 · 이 박스에 있나) |
| `routine_get` | 판 하나의 계획(단계 · 허용 도구 · 할 일 · 기대 출력 · 예산 · 보고서 절). `run_id` 를 주면 진행과 다음 단계 — 이어하기 |
| `routine_run_start` | 판 · 입력을 박고 실행 id 를 낸다 |
| `routine_call` | 단계 울타리 안의 도구 호출 — `invoke_tool` 의 검사를 다 받고(절차 면제 없음) 원장에 인자 · 결과를 남긴다(`corr=run_id`). 큰 결과는 원장에 다 두고 응답은 쪽으로 |
| `routine_step_done` | 단계 상태 · 요약 → 다음 단계 또는 보고서 틀 |
| `routine_report_submit` | 절 · 인용 → 포털이 렌더하고 게이트웨이가 호출자 이름으로 `create_report_draft`(RA 토큰 없으면 거부 — 서비스 계정 없음) |
| prompts `routine-<slug>` | 루틴 하나에 하나 — Claude Code `/mcp__hwax__routine-<slug>` · Desktop 메뉴에서 한 번에 시작 |

### 4.4 챗

- `ChatRequest.routine = {id, version, inputs, run_id?, resume?}` — 포털 · 에이전트 두 곳에 선언한다. 브라우저는 id · 판 · 입력만 보내고 포털이 스펙을 푼다.
- SSE `routine{kind: plan | step | step_done | gate | report | done}` 하나를 더한다(`think` · `delib` 선례). `token` 은 최종 보고서만, 단계 글은 '생각' 칸.

## 5. 단계(마일스톤)

| 단계 | 내용 | 끝의 모습 |
|---|---|---|
| R0 | 사용자 결정(8절) · `contracts.md`(스펙 JSON Schema · 봉투 · 이벤트 · 도구 스키마) | 계약 시험 뼈대 |
| R1 | 포털 저장(routines · routine_versions · routine_runs · routine_stages) · 검증 · 준비도(단계마다 이 사람이 부를 수 있나) · `/routines-api`(세션 · PAT) · 절차 탭 '루틴' 편집기(내 권한 · 이 박스에 있는 플랫폼만 고르기, 순서 끌기, 할 일 · 기대 출력, 보고서 절) · YAML · 예시 루틴 둘(cae00 시장불량 연쇄 · dev 시연 연쇄) | 루틴을 짜고 저장 · 공유 · 내보내기 |
| R2 | 게이트웨이 `routine_*` · prompts · `_INSTRUCTIONS` 한 항목(포털이 답할 때만) · tools-map · 영역표 · 읽기 전용 PAT 규칙 · 포털 원장 · 렌더 · RA 초안 | Claude 길 끝까지(각본 MCP 클라이언트로 시험 — 진짜 Claude 시험은 안 한다, 10-15 결정) |
| R3 | 에이전트 서버 `routine.py`(단계 하위 실행 · 허용 목록 묶음과 캐시 키 · 떼어 낸 작업 · 이어서 · 동시 상한 · `/health` routine_active · update-all 기다림) · 포털 중계(긴 idle · 브라우저가 떠나도 끊지 않음) · 화면 RoutinePicker · RoutineView | Qwen 길 끝까지(dev 시연 연쇄) |
| R4 | 보고서 — 절 쓰기 · 인사이트 인용 · 자기검증 한 번 · 근거 부록 · 커버리지 · RA 초안 · 대화 `kind=routine` · 이력 · 문서 · Drive | 표준 보고서 |
| R5 | cae00 받아들이기(사람) — 예시 연쇄를 돌려 단계별 토큰 · 시간 · 캐시 적중을 10-29 기준선(질문당 108,275 토큰 · 50 ~ 105초)과 견준다 | 숫자 |

## 6. 위험

- **남의 루틴을 내 자격으로 돌린다** — 단계 글은 작성자의 데이터로 표시하고(«…» · 작성자 · 판), 호출은 실행하는 사람의 권한 · 단계 울타리 · 차단 목록을 다 받는다.
- **면제의 덫** — 절차 PAT 로 LLM 호출이 나가면 파괴 차단이 풀린다. 루틴은 그 PAT 를 쓰지 않는다(시험으로 잠근다).
- **키 넘기기** — 플랫폼마다 키가 다르다(FailureTrace 객체 · SignalForge 제품 코드 · PLM 과제 · ODB job · StepForge project · DynaForge ULID · RA 프로젝트).
  잇는 표가 없는 곳(코어 부품 ↔ ECAD refdes ↔ StepForge 부품)은 사람이 주거나 루틴이 확신도를 적는다.
- **크기 · 시간** — 코어 허브 응답이 217k자까지 간다. 단계 요약이 원 결과 대신 근거 id 를 인용해야 한다. 심의 · 시뮬레이션은 분 ~ 시간이다.
- **같은 루틴 · 같은 입력이 다른 호출을 낸다**(LLM) — 비교는 원장과 커버리지로 하고, 좋았던 실행은 절차로 굳힐 수 있게 한다(`derive.draft`).
- **두 길의 창이 다르다** — Claude Code 는 결과 약 25k 토큰에서 자르고 Qwen 은 1M 이다. 큰 결과는 쪽으로 주고 잘림을 적는다.
- **cae00 판 엇갈림** — 게이트웨이가 새것이고 포털이 낡으면 도구가 '포털이 낡았다' 고 말해야 한다('루틴 없음' 이 아니라).

## 7. 하지 않는 것

- `ProcedureSpec` 에 LLM 단계를 넣지 않는다(AR-D1). 절차의 두 장치는 공유 자산이라 얼린다.
- 단계 안 쓰기 · 작업 제출 · publish 를 루틴이 하지 않는다(v1, AR-D5).
- ReportArchive 리포에 템플릿을 커밋하지 않는다 — 필요하면 RA 팀에 요청서.
- 진짜 Claude 로 시험하지 않는다(10-15 결정) — Claude 길은 각본 MCP 클라이언트로 계약을 본다.
- dev 에서 예시 연쇄의 결과를 판정하지 않는다 — 꼴만 본다(AR-D10).

## 8. 사용자 결정 대기 — 권고 기본값

| # | 묻는 것 | 권고 |
|---|---|---|
| Q1 | 끝의 RA 초안 — 저절로 · 끝에 묻기 · 안 올림 | **끝에 묻는다**. 올리기(publish)는 늘 사람이 RA 에서 |
| Q2 | 단계마다 멈춰 검토할까 | **끝까지 돈다** — 기준 키 후보가 여럿일 때 · 쓰기 직전만 멈춘다 |
| Q3 | 단계의 울타리 — 플랫폼까지 · 도구까지 | **플랫폼이 울타리**, 도구는 고르면 그 부분집합(12개까지) |
| Q4 | 실행 때 권한 · 토큰 · 박스에 없는 단계 | **건너뛰고 보고서에 적는다**. 기준 키 단계가 안 되면 멈춘다 |
| Q5 | 권한 키 — 새 `feat:routines` · `feat:procedures` 재사용 | **새 키**(챗 경로 · 비용이 다르다). CAEG 는 전부라 그대로 |
| Q6 | 공유 기본값 — 나만 · 모두 | **나만**, 모두 공개는 고를 수 있게(실행은 늘 실행하는 사람 권한) |
| Q7 | 시장불량의 원천 — FailureTrace `pd_defect` · PLM 문제점 · 둘 다 | 사용자 판단(도메인) — 둘 다면 잇는 키 |
| Q8 | PLM 보류 중에도 루틴이 PLM 을 불러도 되나 | 사용자 판단 — `enrich=0` 만 |
| Q9 | 시뮬레이션 단계 — 있는 결과만 읽기 · 작업 제출 | **있는 결과만**(v1) |
| Q10 | Claude 길의 자료 반출 — 개인 MCP 와 같게 · 플랫폼별 내부 LLM 전용 표시 | **개인 MCP 와 같게**(지금 개인 Claude 가 그 플랫폼을 이미 부른다) |

## 9. 시험 · 받아들이기

- 가짜는 진짜 꼴로 — cae00 `tools/list` 스냅샷 · 기록한 실패 응답 · ChatOpenAI 1.x 프레임(tool_calls · reasoning_content · `finish_reason=length` ·
  `max_completion_tokens` · 새어 나온 `<tool_call>` 글).
- 잠글 것 — 단계 요청의 도구 ⊆ 허용 목록 · 절차 PAT 를 안 쓴다 · 호출 없이 '했다' 는 단계는 skipped · 키는 결과에 나온 값만 · 토큰 미등록은
  서비스 계정으로 안 떨어진다 · 같은 사람 두 앱에서 캐시가 도구를 섞지 않는다 · 에이전트 SSE ↔ 포털 `_parse_sse_frame` ↔ TS 형 계약.
- dev 실주행 — SignalForge VOC → 심의 → DynaForge 보고서 → 보고서(RA 는 내려가 있어 unavailable 로 적힌다).
- cae00 받아들이기(R5) — 예시 연쇄 한 번, 단계별 토큰 · 시간 · 캐시 적중 · 커버리지.
