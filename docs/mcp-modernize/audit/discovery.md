# HWAX MCP 게이트웨이 — 찾기 · 묶음 · 길 안내 조사(2026-11-27)

읽기만 한 조사다. 리포를 고치지 않았고 서비스를 재기동하지 않았으며 쓰기 도구를 부르지 않았다. 순위 흉내는 게이트웨이 코드를 그대로 import 해
스크래치패드의 카탈로그(dev 게이트웨이 tools/list 797개 · /tools-map)를 앉혀 돌렸다(`tool_search_eval/run.py` 의 `_import_gateway` · `_install` — 질의 기록 끔 ·
감사는 임시 폴더 · pyc 안 씀). 인증이 필요한 `/search-eval` · `/search-log` 는 부르지 않았다.

- 표기 — **[확인]** 은 코드 · 파일 · 실행으로 본 것, **[짐작]** 은 근거에서 미룬 것이다.
- 규모 — 운영(cae00) 게이트웨이는 백엔드 35 · 도구 1,984 다(`HWAXPortal/docs/request-1125/context-notes.md:374`, 11-25) [확인 — 문서]. dev 는 백엔드 18 ·
  도구 797(서비스 시야)이다. 아래 dev 숫자는 dev 것이고, 판단은 2,000개 규모를 기준으로 한다(사용자 덧붙임).
- 산출물 — 이 폴더의 `catalog-1127.json`(평가용 카탈로그) · `eval-1127.txt` · `eval-variants.json`(평가 판별 순위) · `purpose-walk.txt` · `overlap-walk.txt` ·
  `scripts/drive.py`(흉내 스크립트).

---

## 1. 지금 있는 길의 지도

### 1.1 입구 한눈에

| 입구 | 무엇을 내나 | 누가 쓰나 | 근거 |
|---|---|---|---|
| `tools/list` | 권한 안의 도구 전부(보기 `full`) — 보기 머리에 따라 줄인다 | 모든 MCP 클라이언트 | `gateway.py:11856` `_list_tools` [확인] |
| `search_tools(query, limit≤20, detail, object)` | 부분문자열 점수 순위 · 한 줄 요약 · 필수 인자 스키마 | 개인 Claude · 웹 챗 안내대 | `gateway.py:3560` 정의 · `:4121` 순위 [확인] |
| `invoke_tool(name, arguments)` | 목록에 없어도 이름으로 호출(파괴 이름 · `MUST_GATE` 는 막음) | 같음 | `gateway.py:3052` · 막음 `:3080-3110` [확인] |
| `list_tool_apps(app?, by='area'?, area?, include_tools?)` | 앱별(또는 영역별) 도구 이름 · 권한 없음 · 끈 앱 · 보기 정보 | 같음 | `gateway.py:4706` · `:4851` [확인] |
| 보기 `X-HWAX-View` | `full` · `bundle:<영역>,…` · `light`(search_tools · invoke_tool 둘) — **tools/list 에만** | 개인 PAT(머리 `portal` 이면 포털 설정) | `gateway.py:322-371` · `:10127` · `:10158` [확인] |
| 영역 `tool_areas.json` | 도구 → 영역 키 하나(도구 지정 > 이름 패턴 > 앱 기본값) · 14개 영역 | 보기 묶음 · `by='area'` · 포털 화면 | `gateway.py:2944-2979` [확인] |
| 코어 어휘표 `core_vocab.json` | 코어 낱말 → 정본 허브 읽기 도구, 앱 역할(가족 · 비코어 · 시험), 온톨로지 입구 | search_tools · 웹 챗 | 포털 `backend/config/core_vocab.json` · `gateway.py:3871` [확인] |
| `ontology_lookup` | 정본 `object_resolve` 판정 + 앱마다 key 를 채운 `next` | 개인 Claude(웹 챗은 묶지 않음 OF-41) | `gateway.py:6411` [확인] |
| `browse_experts` · `use_experts` | 조직도 → 고른 전문가의 역할 · 운영 앱 · 입구 도구 | 개인 Claude | `gateway.py` 전문가 절 [확인] |
| `routine_*` · `procedure_*` | 사람이 짠 다단계 사슬(포털 원장) | 개인 Claude · 챗 실행기 | `gateway.py:9983-10100` [확인] |
| MCP prompts | **분석 루틴 하나에 `routine-<id>` 하나뿐** — 서비스 · 패널 · GW_TOKEN 은 늘 빈 목록 | 개인 Claude(슬래시 명령) | `gateway.py:9995` [확인] |
| MCP resources | 패널 도구의 `ui://` 리소스뿐 | MCP Apps 패널 | `gateway.py:11756` [확인] |
| `rest_catalog` · `rest_call` | 하위 사이트 REST(전용 도구가 없을 때의 우회로) | 같음 | `gateway.py:3016` · `:3036` [확인] |
| 서버 지침(initialize) | 14개 규칙 — 2,048자 상한에 2,031자까지 찼다 | Claude Code · Desktop | `gateway.py:2004` · `:2053` [확인], 길이는 `docs/ontology-first/request-1116.md` §1 [확인 — 문서] |
| 앱별 엔드포인트 `/mcp/<앱>` | **없다** — 경로는 `/mcp` 하나 | — | `gateway.py:12872` [확인] |

스크래치패드 `prompts-list.json` 이 0개인 것은 그 목록을 서비스 토큰으로 받았기 때문이다 — 그 분기는 설계상 늘 빈 목록이다(`gateway.py:9999`) [확인].
개인 PAT 로 받아도 dev 는 0개다 — 포털 원장 `procedures.sqlite` 의 `routines` 표가 0행이다(절차 2건) [확인 — 읽기 전용 조회].

### 1.2 `search_tools` 순위 함수(`gateway.py:4121-4340`)

- 질의를 빈칸 · 구두점에서 갈라 2자 이상 낱말만 쓴다. 낱말마다 손 동의어(`search_tuning.json` 83줄 — 주인 없음 42 · 심의 17 · DynaForge 14 · 정본 허브 10)와
  코어 어휘표 낱말 → 허브 읽기 도구 이름으로 넓힌다 [확인].
- 줄 점수 = 이름 적중 × 4 + 설명 빈도(낱말당 상한 3) + 앱 라벨 · 설명 적중 × 1, 그리고 커버리지 승수 `× (1 + 맞힌 낱말 비율)`. 질의가 앱 이름을 부르면 이름 적중과 같다 [확인].
- 보정 — 품질 낱말(불량 · 시장 · 원인 · 대책 · 사례)이면 품질 · VOC 영역 +2/낱말, 쓰기 의도 낱말이 없으면 쓰기 도구 × 0.5, 같은 도구 사본은 정본 한 줄로 접기 [확인].
- 기본 끔 손잡이 셋 — `noncore_demote`(코어 질문의 비코어 앱 × 0.5) · `onto_first`(부른 앱의 온톨로지 입구 +4) · `onto_lookup_first`(온톨로지 · 코어 질의에
  `ontology_lookup` 1위)(`gateway.py:3625`) [확인].
- 의미 순위(RRF, AIDataHub 임베더)는 `GATEWAY_TOOL_SEARCH_EMBED_URL` 이 비면 꺼짐이다(`gateway.py:3125`, k=60 `:3133`) [확인].
- 결과는 `ranked`(이름 순위)를 앞에, 설명 · 스키마를 뒤에 싣는다. `detail=true` 는 25,000자 상한(`:3558`) [확인].
- 시야는 `_visible_tools` — 권한 · 끈 앱 · 시험 앱을 뺀다. **보기는 검색에 걸리지 않는다** — light 에서도 검색은 전부를 찾는다(`gateway.py:10110` · C-38) [확인].

### 1.3 보기 셋 — 무엇을 내나

| 보기 | tools/list | 비고 |
|---|---|---|
| `full`(기본) | 권한 안 백엔드 도구 − 끈 앱 − 시험 앱 + 로컬 도구(형제 사본 포함) | 머리가 없으면 늘 이것 |
| `bundle:<영역>,…` | 고른 영역의 백엔드 도구 + 정본 읽기 도구 + 로컬 도구 전부, 형제 사본 · 미분류 제외 | 영역은 `tool_areas.json` 키 |
| `light` | `search_tools` · `invoke_tool` 둘 | 앱 목록 · 패널 도구는 invoke_tool 로 |

정하는 차례는 연결 머리(보기 글) > 머리 `portal` 이면 포털 사람 설정 > 전체다. 웹 챗 · 절차 PAT 는 늘 전체, GW_TOKEN 은 머리를 버린다(`gateway.py:322-334`) [확인].

**채택 0 — dev `/health` 의 `tools_list_by_view` 가 full 5 · bundle 0 · light 0** [확인 — health.json]. 까닭 짐작(앞 셋은 확인된 사실에서 미룬 것).

1. **기본이 전체이고, 바꾸려면 두 단계다** — 포털 '허브에 보일 앱' 에서 고르고, **새 등록 배치**를 받아 연결에 `X-HWAX-View: portal` 을 달아야 한다. 그 전에 등록한
   Claude 는 머리가 없어 늘 전체다(C-41 — `docs/request-1029/context-notes.md:321-334`) [확인 — 문서].
2. **리포 `.mcp.json` 은 `full` 고정**(`HWAXPortal/.mcp.json` — `${HWAX_GATEWAY_VIEW:-full}`) [확인]. 리포에서 도는 Claude Code 는 보기를 쓰지 않는다.
3. **light 의 값이 크다** — 권한 규칙 하나가 모든 호출을 덮고(`invoke_tool` 을 늘 허용하면 쓰기도 저절로), 지우기 · 멈추기 · 게시는 invoke_tool 로 닿지 않으며(`:3080-3110`),
   패널이 안 그려진다(`docs/token-saving/PLAN.md:91-96`) [확인 — 문서].
4. **bundle 의 단위가 '목적' 이 아니다** — 영역이 사실상 앱과 1:1 이라(아래 1.5) 영역을 고르는 것은 앱을 고르는 것이고, 실제 업무는 영역 너덧을 가로지른다 [짐작 — 1.5 · 2.2 의 데이터에서].
5. **효과가 보이지 않는다** — 셈은 프로세스 메모리(`gateway.py:11852`)라 재기동마다 0 이고, 운영 측정(받은 편지함 2026-11-02 Q13 — 보기별 연결)은 답이 없다
   (`docs/token-saving/checklist.md:8` 미완) [확인]. 열린 세션은 재연결해야 목록이 바뀐다(listChanged 없음) [확인].
6. **Claude Code 는 큰 목록을 스스로 견딘다** — 이 조사 세션의 Claude Code 도 MCP 도구를 지연 목록으로 받고 ToolSearch 로 불러온다 [확인 — 이 세션의 동작].
   개인 Claude Code 도 전체 목록을 지연으로 받으면 사용자가 목록 크기를 체감하지 못한다 [짐작 — 판 · 설정에 따른다].

### 1.4 앱별 엔드포인트 — 없다, 그리고 왜

- 9-29 결정(D-1) — 앱별 서버는 도구 이름을 `mcp__hwax-<앱>__X` 로 바꿔 허용 규칙을 깨고, 서버 항목 · PAT 평문 사본 · mcp-remote 프로세스가 앱 수만큼 늘며,
  등록 시점에 고정돼 새 앱이 안 보인다. 그래서 포털 스위치(끄기)를 먼저 했다(`docs/mcp-app-toggle/context-notes.md` D-1) [확인 — 문서].
- 10-31 — 2단계(`/mcp/<app>`) 대신 보기 셋(E-4)으로 갈음했다(`docs/mcp-app-toggle/PLAN.md:34-37`) [확인 — 문서].
- **가능은 하다** — D-1 탐침이 같은 FastMCP 세션 매니저에 Route 를 더해 앱 범위를 요청 경로에서 매번 셈할 수 있음을 봤다 [확인 — 문서]. 게이트웨이에는 이미
  **요청마다 범위를 셈하는 길이 둘** 있다 — 패널 PAT(그 앱 도구만 — `gateway.py:11865`)와 서비스 PAT(작업 허용 목록 — `:11862`) [확인].

### 1.5 영역(`tool_areas.json`) — 목적 묶음 노릇을 하나

- 영역 14개(cad · mesh · sim · calc · result · material · voc · knowledge · research · report · expert · data · system · quality), 도구 하나에 **영역 하나** [확인].
- 판정은 도구 지정 142개 > 이름 패턴 7개 > 앱 기본값 36개다 [확인]. 대부분이 앱 기본값이라 영역 ≈ 앱이다. dev 의 영역 × 앱(도구 수) [확인 — tools-map]

| 영역 | 수 | 앱 구성 |
|---|---|---|
| cad | 176 | StepForge 176 |
| report | 107 | RA 67 · WDA 24 · MXWP 10 · DocForge 6 |
| mesh | 102 | DynaForge 81 · StepForge 21 |
| expert | 74 | 리스크 52 · 심의 13 · AIDataHub 9 |
| knowledge | 56 | MXWP 27 · RA 16 · AIDataHub 12 · 게이트웨이 1 |
| calc | 52 | 적층 39 · 열충격 12 · AIDataHub 1 |
| material | 45 | MaterialTwin 34 · StepForge 7 · 적층 3 · AIDataHub 1 |
| result | 44 | DynaForge 36 · RA 7 · SmartTwin 1 |
| voc | 37 | SignalForge 37 |
| sim | 34 | SmartTwin 21 · ste 13 |
| system | 39 | 게이트웨이 29 · 그 밖 10 |
| data | 17 | AIDataHub 7 · RA 6 · MXWP 4 |
| research | 12 | 웹 조사 8 · 논문 4 |
| quality | 0 | dev 에 없음(cae00 의 PLM · FMEA · SIREN) |

- 결론 — 영역은 '무슨 종류의 일' 이고 '어떤 업무를 끝내는 길' 이 아니다. 한 도구가 두 목적에 들 수 없고, 단계 차례 · 입구 · 확인 관문이 없다 [확인].
- cae00 에서는 cad 에 ComponentCore · ODB 허브 · DevLab 체크리스트가 더해진다(`tool_areas.json` apps) [확인]. 그래서 `bundle:cad` 하나가 수백 개일 수 있다 [짐작 — cae00 도구 수 미확인].

### 1.6 다른 곳에 흩어진 '묶음'

| 무엇 | 단위 | 노출 | 근거 |
|---|---|---|---|
| HE팀 운영자 19명 | **앱 하나** — `key_tools`(4~10) · `workflow`(3~6) · `samples`(2~4) · `writes` · `confirm` | `browse_experts` · `use_experts` · 웹 챗 핀 | `HWAXPortal/infra/personas/he-team.json` [확인] |
| 분석 루틴 | 사람이 짠 다앱 사슬 | `routine-<id>` prompt · `routine_*` | dev 0건 [확인] |
| 절차 | 사람이 굳힌 사슬 | `procedure_*` | dev 2건 [확인] |
| 어휘표 `personas.domains` | 도메인 → 코어 타입 · 영역 · 앱 | 심의 좌석(E-5) | `core_vocab.json` [확인] |
| 어휘표 `ontology.apps.<앱>.entry` | 앱의 온톨로지 입구 | onto_first(기본 끔) | `core_vocab.json` [확인] |
| 웹 챗 `_select_tools` | 질의 관련도(임베딩) · 핀 · 전문가 분야 · 고정 몫 | 웹 챗 바인딩 | `HWAXAgentServer/app.py:3390` [확인] |

- 웹 챗은 게이트웨이 `search_tools` 와 **다른 순위기**로 바인딩을 고른다 — 두 순위가 갈린다 [확인].
- 앱 스스로 둔 입구 도구가 있다 — RA `get_guide` · StepForge `measurement_guide` · `job_params_guide` · 리스크 `risk_next_step` · SmartTwin `recipe_list` · DynaForge
  `recipe_search` 등. 그러나 꼴 · 이름 · 유무가 앱마다 다르고, 게이트웨이가 아는 칸이 없다 [확인 — 도구 설명 훑기].

---

## 2. 「목적별 도구모음」 은 어디에 정의돼 있나

### 2.1 답

- **정의된 곳이 없다.** 가장 가까운 것은 HE 운영자의 workflow(앱 하나 안의 차례)와 루틴 · 절차(사람이 짠 사슬, dev 0 · 2건)다 [확인].
- **사람이 고를 수 있는 단위로 노출되는 것** — 보기 `bundle:<영역>`(영역 = 종류), `use_experts`(앱 하나의 운영자), `routine-<id>` prompt(루틴이 있을 때만) [확인].
  목적(낙하 해석 준비 · 보고서 쓰기 · 물성 찾기 · VOC 분석 · 설계 리스크)을 단위로 고르는 엔드포인트 · 보기 · prompt 는 없다 [확인].
- 서버 지침에는 자리가 없다 — 2,048자 상한에 2,031자가 찼다 [확인 — 문서].

### 2.2 목적 다섯을 따라가 보기(오프라인 흉내, dev 카탈로그 796 · 기본 손잡이 · 서비스 시야)

개인 Claude 의 걸음은 지침 1번대로 `search_tools("하려는 일")` → 상위 8 중 고르기 → (모자라면) `list_tool_apps(app=…)` → `invoke_tool` 이다 [확인 — 지침].
순위는 `purpose-walk.txt` · `overlap-walk.txt` 에 있다 [확인 — 실행].

| 목적 · 질의 | 맞은 줄(전체 796 중) | 상위에 선 것 | 놓친 것(순위) |
|---|---|---|---|
| 낙하 해석 준비 | 229 | StepForge `drop_check` · SmartTwin `fullangle_drop_simulation` · `single_drop_simulation` · DynaForge 리포트 도구 넷 · RA `list_analysis_runs` | StepForge 준비 사슬(intake → 점검 → `mesh_size_advice` · `run_job` → `check_deck`) · MaterialTwin `export_dyna_cards` 가 상위 10 밖 |
| STEP 파일로 낙하 해석 돌리기 | 459 | 같은 무리 + `heaxstep_forge_whoami`(8위 — 접두 `heaxstep_` 가 'step' 에 맞음) | 같음 |
| 재료 물성 찾기 | 245 | MaterialTwin 8 · StepForge 2 — 좋다 | — |
| 알루미늄 영률 | 3 | `ashby_data` · 쓰기 둘(`register_relaxation_test` · `recompute_properties`) | `get_material_properties` 20위 밖 |
| 보고서 쓰기 | 332 | 리스크 `risk_export_report_bundle` · `risk_get_report` · RA 조회 도구 | `create_report_draft` · RA 입구 `get_guide` 20위 밖 |
| 보고서 작성 | — | RA 조회 도구 | `create_report_draft` 15위 |
| 새 보고서 초안 만들기 | — | `create_report_draft` 1위 | — |
| VOC 분석 | 71 | SignalForge 10/10 — 좋다 | — |
| 갤럭시 배터리 불만 | 46 | `search_voc` 1위, StepForge `compare_stackup` 2위 · `compare_part_shape` 5위 | — |
| 설계 리스크 심사 | 111 | `deliberate_start` · `deliberate_continue` · `deliberate_status` | 지침 11번의 입구 `risk_next_step` 20위 밖 · `risk_start_job` 6위 |

읽기 [확인 — 실행 결과에서].

- **목적의 첫 걸음이 순위에 없다** — 낙하 준비 · 보고서 쓰기 · 리스크 심사 셋 다 그 일을 시작하는 도구(입구 · 준비 사슬)가 아니라 끝난 일을 읽는 도구가 앞선다.
- **지침과 순위가 어긋난다** — 지침 11번은 '설계 리스크 심사는 `risk_next_step` 부터' 인데 같은 낱말의 검색은 심의 가족을 올린다.
- **쓰기 의도 낱말에 '작성' · '쓰기' 가 없다**(`search_tuning.json` `write_intent`) — 그래서 '보고서 쓰기 · 작성' 에서 `create_report_draft` 가 × 0.5 감점을 받는다.
- 결국 낙하 준비 같은 다앱 목적은 search_tools 한 번으로 길이 안 보이고, `list_tool_apps(app='heax-step_forge')`(207개 설명 전문)나 `use_experts` 로 넘어가야 한다 [짐작 — 걸음 수].

---

## 3. 검색 품질의 최근 측정치

### 3.1 평가셋 [확인 — `tool_search_eval/pairs.jsonl`]

- 186쌍 — doc 42(문서 · 실사고) · onto 36(10-17 운영 요청 OL-4 — 코어 30 · 앱 이름 6) · auto 108(도구 설명에서 별도 에이전트가 쓴 문장).
- **사람이 본 쌍 0**(`reviewed: false` 전부). 박스 정답쌍 `pairs.local.jsonl` 은 dev 에 없다. 카탈로그 스냅샷 `catalog.local.json` 은 10-16 판이다.
- 지표 — hit@1 · hit@5 · MRR@20. 목적 단위(앱을 맞혔나 · 단계를 덮었나) 지표는 없다.

### 3.2 리포에 남은 숫자 [확인 — `tool_search_eval/README.md` · 포털 문서]

| 날 · 곳 | 카탈로그 | 판 | doc hit@5 · MRR | auto hit@5 · MRR |
|---|---|---|---|---|
| 10-16 dev | 440 | 부분문자열 | 0.882 · 0.651(34쌍) | 0.389 · 0.298 |
| 10-18 dev | 440 | RRF(BGE-M3) | 0.765 · 0.621 | 0.769 · 0.572 |
| 10-28 dev | 557 | 부분문자열(HG-01 고침 뒤) | 0.875 · 0.679(40쌍) | 0.393 · 0.295 |
| 11-16 cae00 | 1,590 + 23 | 기본 | 코어 30 — hit@1 0.63 · hit@5 0.77 | 앱 이름 6 — hit@1 0.33 |
| 11-16 cae00 | 같음 | 박스 덧씌우기 | 코어 30 — 0.63 · 0.83 | 앱 이름 6 — 0.83 |

- 10-18 판정 — 손댄 심의 낱말은 부분문자열이 이기고, 손대지 않은 질의는 RRF 가 이긴다 → 그대로 끔(README 'BGE-M3 로 다시 잼').
- 11-16 cae00 — '온톨로지 조회' 는 20위 밖(1위 AIDataHub `agent_search`) · '온톨로지 검색' 20위 밖. **'조회' · '검색' 은 도구 수백 개에 들어 낱말 순위로는 정본을 1위로
  못 올린다**(`docs/ontology-first/request-1116.md` §1). 이것이 2,000개 규모에서 낱말 순위의 한계다.

### 3.3 오늘 다시 잼 — dev 카탈로그(백엔드 765 + 로컬 31), 183쌍(정답 도구가 없는 3쌍 뺌) [확인 — `eval-1127.txt` · `eval-variants.json`]

| 판 | doc 42 | onto-o 코어 30 | onto-c 앱 이름 4 | auto 107 | 전체 183 |
|---|---|---|---|---|---|
| 기본 | 0.500 · **0.857** · 0.643 | 0 · 0 · 0 | 0.75 · 0.75 · 0.77 | 0.196 · **0.383** · 0.284 | 0.246 · 0.437 · 0.331 |
| +onto_lookup_first | 0.476 · 0.833 · 0.628 | 0.867 · 0.867 · 0.867 | 0.75 · 0.75 · 0.77 | 0.168 · 0.383 · 0.270 | 0.366 · 0.574 · 0.461 |
| −synonyms | 0.381 · 0.690 · 0.498 | 0 · 0 · 0 | 0.25 · 0.75 · 0.44 | 0.196 · 0.355 · 0.271 | 0.208 · 0.383 · 0.282 |

(칸은 hit@1 · hit@5 · MRR@20.)

- 코어 30 이 0 인 것은 dev 에 정본 허브가 없고 `ontology_lookup` 은 손잡이를 켜야 순위에 들기 때문이다 — dev 숫자로 코어 질의를 판정하지 않는다.
- **+onto_lookup_first 가 문 쌍** — doc-25 'SUS304 물성 표' 1 → 2 · doc-26 'SCM440 물성' 3 → 4 · doc-39 '물성' 5 → 6 · auto 셋. '물성' · '모델' · '기준' 은 코어 낱말이면서
  MaterialTwin · 적층 · 열충격의 일이다 — 코어와 앱이 같은 낱말을 다툰다.
- 손 동의어는 36쌍을 돕고 18쌍을 해친다(−synonyms 대비).
- auto 의 hit@5 0.383 — 설명을 바꿔 말한 실사용형 문장의 6할이 상위 5 밖이다.

### 3.4 질의 기록 [확인 — `tool_search_eval/queries-2026-11-22.local.jsonl` · `queries.local.jsonl`]

- dev 는 30일 창에 11-22 하루 4건뿐이다(옛 파일 1건). 운영 질의는 cae00 에 있다(여기서 못 읽음).
- 유형 — ① **도구 이름을 그대로 넣는 찾기**(4건 중 2건 — 이름 조회로 search_tools 를 쓴다) ② 한국어 · 영어 섞인 앱 이름 + 재료 낱말 ③ 여러 일을 한 문장에 묶은 질의(옛 1건 —
  품질 분석 · 과제 연결 · 발표자료).
- 결과 줄 14건 중 9건이 순위 `null` — 찾은 뒤 부른 도구가 상위 다섯에 없었다(목록 · 다른 길로 고른 것).

### 3.5 이번 흉내에서 본 실패 꼴 [확인 — 실행]

| 꼴 | 예 |
|---|---|
| 띄어쓰기 | '지식카드 찾기' → 1위 `deliberate_start` · 2위 StepForge `corner_proximity`, AIDataHub 지식카드 도구 20위 밖('지식 카드 검색' 은 11 · 13위) |
| 쓰기 의도 낱말 빠짐 | '보고서 쓰기' — `create_report_draft` 20위 밖 |
| 지침 ↔ 순위 어긋남 | '설계 리스크 심사' — `risk_next_step` 20위 밖 |
| 읽기 질의에 쓰기 도구 1위 | '온톨로지 객체 찾기' — StepForge `onto_put`(쓰기 표지) 1위 · 감점 × 0.5 로 모자람 |
| 접두 잡음 | 'STEP 파일로 낙하 해석' — `heaxstep_forge_whoami` 8위 |
| 영어 설명 | AIDataHub `hybrid_search` · `semantic_search` 설명이 영어라 한국어 질의에 약하다 |
| 일반 낱말 범람 | 맞은 줄이 카탈로그의 29 ~ 58%(낙하 준비 229 · STEP 낙하 459 · 잡 상태 261 / 796) |

---

## 4. 겹침 · 혼동

### 4.1 같은 원래 이름이 여러 앱에(dev 12개) [확인 — tools-map `orig`]

`cancel_job`(DynaForge · StepForge · ste) · `list_jobs`(StepForge · ste) · `job_status`(StepForge · SmartTwin) · `submit_job`(SmartTwin · ste) · `recipe_run`(DynaForge · SmartTwin) ·
`list_reports`(DynaForge · RA) · `prepare_upload`(RA · ste) · `semantic_search`(AIDataHub · SignalForge) · `register_material`(MaterialTwin · StepForge) · `whoami` ·
`system_status` · `system_capabilities`(DynaForge · StepForge). 이름이 겹치면 접두가 붙고(`heaxstep_forge_…`) 그 접두가 다시 부분문자열 잡음이 된다.
cae00 은 허브 가족이 늘 접두이고 시험 사본(`*-prod`)이 있어 겹침이 더 많다 [짐작].

### 4.2 같은 목적에 경쟁하는 앱 [확인 — `overlap-walk.txt`]

| 목적 | 경쟁하는 앱 · 도구 | 지금 순위가 고르는 것 |
|---|---|---|
| 문서 · 지식 검색 | MXWP(`wiki_search` · `search_documents` · `search_knowledge`) · RA(`search_reports`) · AIDataHub(`agent_search` · `hybrid_search`) · 웹 조사(`search_internal`) | MXWP 가 위. MXWP `search_knowledge` 는 '플랫폼 설계 지식' 인데 '지식 카드 검색' 1위 |
| 잡 상태 | SmartTwin · StepForge · DynaForge · 심의 · 논문 반입 · 절차 | 다섯 앱이 한 목록에 섞인다 |
| 레시피 | StepForge(`list_recipes` · `run_recipe`) · DynaForge(`recipe_search` · `recipe_run`) · SmartTwin(`recipe_list` · `recipe_run`) | 세 체계가 따로 |
| 물성 | MaterialTwin · StepForge `material_lookup` · 적층 라이브러리 · DynaForge `material_usage` · cae00 정본 허브 `material_property` · MatNexus | 앱은 MaterialTwin 이 위, 코어 낱말 '물성' 은 정본 쪽으로 |
| 온톨로지 | StepForge `onto_*` · RA `ask_ontology` · AIDataHub · DynaForge `ontology_object` · cae00 정본 · 형제 허브 · SignalForge · MatNexus · ARP · ComponentCore | 앱마다 키 꼴이 다르다(request-1116 §1) |
| 보고서 만들기 | RA(`create_report_draft` · `create_report_from_format`) · MXWP(`export_document`) · WDA(PPT) · DocForge · 리스크(`risk_export_report_bundle`) | '보고서 쓰기' 에서 리스크 묶음이 1위 |

### 4.3 코어 질문이 다른 앱으로 새기(10-29 운영 QA) [확인 — `HWAXPortal/docs/request_261029.md:19` · `:55-63` · `:179-185`]

- 고장모드 · 시험항목 · 가상검증 · 관리 기준 · 물성 질문(OT-06 ~ 10)이 코어를 건너뛰고 FMEA 규격 · ARP 실측 · MatNexus · RA 로 갔다. OT-10 은 코어에 있는 기준을
  '정의돼 있지 않다' 고 답했다. 까닭 — 비코어 앱 도구 설명이 '규격 · 시험 · 고장모드' 를 싣고 허브 도구 설명은 일반문이었다(R-3).
- 그 뒤 지은 것 — 정본 소개 줄(R-3) · 어휘표 낱말 → 허브 도구(R-4) · 코어 질문의 심의 가중 끔(R-5) · 사본 접기 · `noncore_demote`(기본 끔) · `ontology_lookup` 과
  `onto_lookup_first`(기본 끔).
- 남은 것 — 낮추기 · 조회 먼저 둘 다 **기본 끔이고 켜는 것은 cae00 측정 뒤** 다. 위 3.3 처럼 '물성' 같은 낱말은 코어와 앱 둘 다의 일이라, 앱 단위 낮추기로는
  가를 수 없고 **목적**(정본 키를 묻나 · 재료 값을 묻나)으로 갈라야 한다 [짐작].

---

## 5. 2,000개 규모에서 무엇이 달라지나

| 자리 | dev 797 | cae00 ~2,000 | 판단 |
|---|---|---|---|
| tools/list 이름만 | 15,484자 [확인] | 약 39,000자 [짐작 — 비례] · token-saving 은 '요청마다 약 20k' 로 적음 [확인 — 문서] | 전체 목록을 늘 싣는 클라이언트(지연이 없는 쪽)에 무겁다 |
| tools/list 전문(설명 · 스키마) | 992,776자 [확인] | 약 250만 자 [짐작 — 비례] | Claude Code 는 지연으로 견디되, 그때 찾기는 **클라이언트의 검색**이 한다 — 손 동의어 · 어휘표 · 쓰기 감점을 모른다 [짐작] |
| search_tools 맞은 줄 | 29 ~ 58% | 같은 비율이면 600 ~ 1,100줄 [짐작] | 상위 20 안의 자리싸움이 설명 빈도 · 접두 잡음으로 갈린다 — 11-16 cae00 이 이미 '조회 · 검색으로는 정본을 못 올린다' 를 봤다 |
| `bundle:<영역>` | cad 176 · report 107 · mesh 102 | cad 에 ComponentCore · ODB · DevLab 이 더해진다 [확인 — 앱 기본값], 수는 미확인 | 영역 셋을 고르면 수백 개 — 줄여 주는 힘이 약하다 [짐작] |
| `list_tool_apps` 기본 | 이름 전부 싣기(`include_tools` 기본 참) [확인] | 2,000 이름 | 요약에는 이름을 빼는 편이 맞다 |
| 사본 · 겹침 | 원래 이름 겹침 12 | 허브 가족 늘 접두 · 시험 사본 | 접두 잡음이 는다 |

결론 — 2,000개에서는 '전부를 보이고 낱말로 찾는' 길만으로는 첫 걸음을 못 맞힌다. **목적으로 먼저 좁히고(작은 정본 표), 그 안에서 앱 입구 → 도구로 내려가는**
두 층이 필요하다. 앱별 · 목적별 엔드포인트(또는 보기)는 지연이 없는 클라이언트와 '몇 앱만 쓰는 사람' 에게 실익이 생긴다 — D-1 의 비용(이름 · PAT 사본 · 프로세스)과
다시 견줄 때다 [짐작].

---

## 6. 가장 큰 틈 다섯

1. **목적 단위가 없다.** 영역은 도구 하나에 하나뿐인 '종류' 칸이고 사실상 앱과 1:1 이다(cad = StepForge 176/176). 다앱 목적(낙하 해석 준비)의 차례 · 입구 · 확인 관문은
   HE 운영자(앱 하나씩) · 루틴(dev 0) · 절차(dev 2)에 흩어져 있고 게이트웨이 찾기에 이어지지 않는다.
2. **사람이 고를 수 있는 노출 단위가 비어 있다.** 보기 셋은 채택 0(dev full 5/5), 앱별 엔드포인트는 없고, prompts 는 루틴뿐(dev 0)이며, 서버 지침은 2,031/2,048자라 길 안내를 실을 자리가 없다.
3. **순위가 첫 걸음을 못 맞힌다.** auto hit@5 0.383. '보고서 쓰기' · '설계 리스크 심사' · '낙하 해석 준비' 에서 그 일을 시작하는 도구가 20위 밖이고, 띄어쓰기(지식카드) ·
   쓰기 의도 낱말(작성 · 쓰기) · 접두 잡음 · 읽기 질의의 쓰기 도구 1위 같은 작은 결함이 겹친다. 2,000개에서 더 나빠진다.
4. **같은 목적에 앱이 경쟁하고 코어가 샌다.** 문서 · 지식 검색 4앱, 잡 상태 5앱, 레시피 3체계, 온톨로지 5+앱, 원래 이름 겹침 12. 코어 새기 막이(`noncore_demote` ·
   `onto_lookup_first`)는 기본 끔이고, '물성' 처럼 코어와 앱이 함께 쓰는 낱말은 앱 단위 손잡이로는 못 가른다.
5. **측정 고리가 dev 에 갇혀 있다.** 평가셋 186쌍은 사람이 본 쌍 0, 스냅샷은 10-16, dev 질의는 4건, 박스 정답쌍 없음, 보기 채택 셈은 재기동마다 0, 운영 물음 Q13 미답.
   목적 단위 지표(앱을 맞혔나 · 단계를 덮었나)가 없다.

---

## 7. 고도화 안

차례 권장 — 안 6(측정 바닥) · 안 1(정본 표) → 안 3 의 작은 고침 → 안 5 → 안 2 → 안 4. 모든 안은 **끄면 지금과 바이트까지 같게**(E-7 규칙) 짓는다.

### 안 1. 목적 묶음 정본 표 하나 — `tool_purposes.json`(+ 박스 덧씌우기)

- **무엇** — 목적 30개 안팎을 한 표에 둔다. 칸 — `key` · `label` · `description` · `triggers`(낱말) · `steps[]`(`id` · `title` · `tools`: `[백엔드 키, 원래 이름]` 목록 ·
  `write` · `confirm`) · `areas` · `experts`(HE 운영자 키) · `samples`(질의 예). 별도 칸 `apps.<키>.entry`(안 5). 도구는 노출 이름이 아니라 (백엔드, 원래 이름)으로 적는다 —
  접두가 박스마다 달라서다(평가셋 정답과 같은 규칙). 도구 하나가 여러 목적에 든다(영역과 다르다).
- **읽는 곳(같은 표 하나)** — `search_tools`(안 3) · `list_tool_apps(by='purpose')`(안 2) · 보기 `purpose:<key>`(안 4) · prompts(안 2) · 포털 '허브에 보일 앱' 화면 ·
  웹 챗 `_select_tools` 의 `prefer`(전문가 분야 도구 자리) · `/tools-map` 의 `purposes`.
- **씨앗** — HE 운영자 19명의 `workflow` · `key_tools` · `samples`(앱 하나 안의 차례), 절차 예제 · 루틴, `docs/` 의 사고 기록. 다앱 목적(낙하 준비 · 보고서 · 리스크 심사 ·
  물성 찾기 · VOC → 보고서)부터 다섯.
- **손댈 곳** — 게이트웨이 리포에 `tool_purposes.json` · `tool_purposes.local.json`(gitignore). 읽기는 `_tuning()`(`gateway.py:3688`)과 같은 꼴 — mtime 재읽기 ·
  `_merge_patch` · `_json_fp` 지문 · 깨지면 기본값. `/health` 에 `purposes{fingerprint, overlay, missing}` — 표가 가리키는데 카탈로그에 없는 도구(cae00 전용 앱은 그 박스에서만
  세는 HE 운영자 `optional` 규칙).
- **자리 선택지** — (가) 게이트웨이 리포(`tool_areas.json` 곁 — 읽는 곳 대부분이 게이트웨이, 포털은 `/tools-map` 으로 받는다) · (나) 포털 `core_vocab.json` 곁(C-2 —
  라벨 정본이 포털에 모여 있다, 에이전트 서버도 이미 읽는다). (가)를 권하되 사람이 고른다.
- **위험** — 손으로 쓴 표의 낡음(절차서 낡음이 코드 낡음보다 위험하다는 기록과 같은 꼴). 막이 — `missing` 셈 · 시험(표의 도구가 시험 카탈로그에 있는가) · update-all §7 지문.
- **기본값에서 바뀌는 것** — 없다(읽는 곳이 모두 손잡이 뒤에 선다). `/tools-map` · `/health` 에 칸이 는다.
- **재는 법** — 안 6 의 목적 쌍(purpose@1 · 단계 덮기).

### 안 2. 목적 길 안내 — prompts `purpose-<key>` + `list_tool_apps(by='purpose')`

- **무엇** — 사람은 prompt 로(Claude Code 의 슬래시 명령), 모델은 도구로 같은 표를 읽는다. prompt 본문은 단계 · 단계마다 노출 이름 · 입구 도구 · 확인 관문(쓰기는 사람에게
  먼저) · '모르면 search_tools' 를 싣는다. 루틴 prompt(`_rt_prompt_text`)와 같은 꼴이다.
- **왜 prompt 인가** — prompt 는 부를 때까지 문맥을 먹지 않는다. 서버 지침(2,048자)에 못 싣는 길 안내를 실을 유일한 MCP 표면이다. 2,000개에서도 크기가 목적 수에만 따른다.
- **손댈 곳** — `_list_prompts`(`gateway.py:9995`)에 목적 줄을 더한다(호출자에게 보이는 앱만 — `_visible_tools` · 끈 앱, 서비스 · 패널 · GW_TOKEN 은 지금처럼 빈 목록).
  `_get_prompt`(`:10066`)에 `purpose-` 머리. `_list_tool_apps`(`:4706`)에 `by='purpose'` 갈래(`_list_by_area` `:4851` 와 같은 꼴, 요약은 이름 없이).
- **위험** — prompts/list 는 연결할 때 불리므로 여기서 터지면 연결이 오류로 보인다(지금 규칙 그대로 실패하면 빈 목록). 남이 쓴 글이 아니라 표의 글이라 루틴의 «…» 막이는 덜 든다.
- **기본값에서 바뀌는 것** — prompts 목록에 줄이 는다 → 손잡이(env `GATEWAY_PURPOSE_PROMPTS`, 기본 끔)로 둔다. `by='purpose'` 는 새 인자라 기존 호출은 그대로다.
- **재는 법** — 감사에 `prompts/get purpose-<key>` 줄을 남기고(지금 prompts 는 감사 밖인지 확인 필요), 뒤이은 호출이 그 목적의 단계 도구인지 질의 기록의 결과 줄과 같은 꼴로 센다.

### 안 3. `search_tools` 목적 층 + 작은 순위 고침

- **3-a 목적 층** — 질의가 목적의 `triggers` 에 맞으면(목적 30개라 낱말 · 임베딩 어느 쪽도 싸고 안정하다) 답 앞쪽에 `purpose{key, label, steps[{title, tools}], prompt}` 를 싣는다
  (손잡이 `purpose_hint`). 그 목적 단계의 도구에 가중(`weights.purpose`, 손잡이 `purpose_boost`). 도구 이름 질의(`detail` 이름 그대로)는 건드리지 않는다.
- **3-b 작은 고침(각각 측정 뒤)**
  - `write_intent` 에 '작성' · '쓰기' · '써' 를 더한다(`search_tuning.json` — 코드 아님). '보고서 쓰기' 의 `create_report_draft` 20위 밖을 겨눈다.
  - 띄어쓰기 접기 — 빈칸 없는 낱말(지식카드)을 빈칸을 뺀 설명에서도 센다(`gateway.py:4237` `desc.count`). 손 동의어 `표 칸` 의 빈칸 접기(RF-23)와 같은 결의 일반화.
  - 쓰기 표지(annotations `readOnlyHint:false`) 도구의 감점을 박스 덧씌우기로 0.3 쯤에서 잰다(`onto_put` 1위).
  - 접두 잡음 — 이름 적중을 원래 이름 + 앱 라벨로 보는 안은 10-29 에 '시장 불량' 순위 때문에 걷었다(README 10-29 절). 목적 층이 생긴 뒤 다시 잰다.
  - RRF 다시 잼 — 10-18 판정은 440개 카탈로그였다. cae00 1,984 스냅샷에서 k=10 판을 잰다(README 진단 표 — k=10 이 심의 낱말 회귀를 없앴다).
- **손댈 곳** — `_search_tools`(`gateway.py:4121`), `_TUNING_SWITCHES` · `_TUNING_OPT_IN` · `_TUNING_WEIGHTS`(`:3617-3627`), `search_tuning.json`, `/search-eval` 의 판 목록(켬 · 끔 판에 `+purpose_hint`).
- **위험** — 목적 층이 잘못 맞으면 엉뚱한 단계를 앞세운다 → `purpose` 칸은 순위 밖 안내로만 먼저 내고, 가중은 따로 켠다. 낱말 고침은 평가셋에 맞춘 값이 될 수 있다 → 박스 쌍으로 다시 잰다.
- **기본값에서 바뀌는 것** — 손잡이는 모두 끔. `write_intent` 낱말은 기본값 파일의 변경이라 순위가 바뀐다 — 그것만은 측정 뒤 사람 결정(OF-42 처럼).
- **재는 법** — `run.py eval --catalog`(오늘 쓴 길 — 스냅샷만 있으면 백엔드 없이 돈다) · cae00 `/search-eval` 판 비교 · 나빠진 쌍 0 을 받아들이는 기준으로.

### 안 4. 보기에 `purpose:<key>` + (선택) 경로 별칭 `/mcp/p/<key>` · `/mcp/app/<key>`

- **무엇** — 보기 글에 `purpose:<key>,…` 를 더한다 — 그 목적들의 단계 도구 + 앱 입구 + 로컬 도구. 보기와 같은 길이라 '목록만 줄이고 검색 · 호출 · 권한은 그대로' 다.
  더 나아가 경로 별칭을 두면 등록 한 줄로 고른다 — 미들웨어가 `/mcp/p/<key>` 를 `/mcp` + 보기 머리로, `/mcp/app/<key>` 를 `/mcp` + 앱 범위로 바꾼다(패널 PAT 의 앱 범위 ·
  `gateway.py:11865` 와 같은 꼴, 세션은 지금처럼 `mcp-session-id`).
- **왜 지금 다시 보나** — D-1(9-29)은 도구가 수백 개일 때의 판단이었다. 2,000개에서는 지연이 없는 클라이언트 · '두세 앱만 쓰는 사람' 에게 목록 크기가 실제 문제다.
  앱 엔드포인트 안에서는 같은 앱끼리라 접두가 필요 없다는 장점도 있다 [짐작].
- **손댈 곳** — `_parse_view`(`gateway.py:357`) · 포털 `backend/app/access/hub_view.py`(두 시험이 맞댄다) · `_listed_tools`(`:10127`) · `_VIEW_LISTS`(`:11852`) · `/tools-map` `views`.
  경로 별칭은 ASGI 미들웨어(`:12394` · `:12872` 부근).
- **위험** — D-1 그대로 남는다 — 서버 이름이 바뀌면 `mcp__<서버>__<도구>` 이름과 허용 규칙이 바뀐다, PAT 사본과 mcp-remote 프로세스가 등록 수만큼 는다, 다앱 목적은 결국 허브가 필요하다.
  그래서 **보기 모드 먼저(새 경로 없음), 경로 별칭은 사람 결정 뒤** 를 권한다.
- **기본값에서 바뀌는 것** — 없다(머리 · 경로를 쓰는 연결만).
- **재는 법** — `_VIEW_LISTS` 에 `purpose` 칸, 안 6 의 채택 셈을 `/usage-rollup` 으로 날마다 남기기, `list_tool_apps.view.listed` 크기.

### 안 5. 앱 입구 계약 — `apps.<키>.entry`

- **무엇** — 앱마다 '처음 부를 도구' 하나를 표에 적는다(RA `get_guide` · 리스크 `risk_next_step` · StepForge `measurement_guide` · DynaForge `recipe_search` 등 — 씨앗은 HE 운영자
  `key_tools` 첫 줄과 '먼저 부른다' 설명). `list_tool_apps` 앱 줄에 `entry` 를 싣고, 질의가 앱 이름을 부르면(`named_apps`) 그 앱의 입구를 첫 줄로(손잡이 `app_entry_first` —
  `onto_first` 의 일반화). 입구가 없는 앱은 앱 주인에게 요청서로 청한다.
- **효과** — 2,000개에서 '앱 이름 + 일' 질의가 앱 도구 20개 무작위 대신 길잡이 하나를 받는다. 지침 11번(리스크)처럼 지침에 한 줄씩 넣던 일을 표가 대신한다 — 지침 자리가 빈다.
- **손댈 곳** — 안 1 표의 `apps` 칸, `_list_tool_apps`(`:4706`) 앱 줄, `_search_tools` 의 `named_apps` 뒤(`:4344` `lookup_first` 와 같은 자리).
- **위험** — 입구 도구가 쓰기면 안 된다(표 시험으로 읽기 표지 확인). 앱 판이 바뀌어 이름이 사라지면 `missing`.
- **기본값에서 바뀌는 것** — `list_tool_apps` 에 칸 하나가 는다. 순위는 손잡이 뒤.
- **재는 법** — 앱 이름 쌍(onto-c 꼴)을 앱마다 둘씩 더해 entry@1.

### 안 6. 평가셋 확장과 박스 측정 고리

- **쌍 넓히기**
  - HE 운영자 `samples`(19명 × 2~4 ≈ 70) → 정답 = 그 운영자의 `key_tools`, 지표 **app@1**(첫 줄이 맞는 앱인가).
  - 목적 쌍(목적마다 질의 다섯 · 정답 = 단계 도구) → **purpose@1**(목적 층이 맞혔나) · **단계 덮기**(상위 10 이 단계를 몇 개 덮나).
  - 186쌍 사람 검토(지금 0) — 운영 '도구 검색 검토' 화면(`/search-review`)으로.
- **재는 곳** — dev 숫자는 운영을 말하지 못한다(C-31). cae00 에서 `run.py snapshot` → `eval --catalog`(백엔드 없이 도는 길 — 오늘 확인) · `/search-eval` 판 비교.
- **채택 셈** — `_VIEW_LISTS` 는 메모리라 재기동마다 0 이다 → `/usage-rollup`(이미 있는 창구)에 보기별 tools/list · prompts/get · `by=` 갈래 · search → invoke 성공 사슬을 날마다 접는다.
  운영 물음 Q13(보기별 연결)을 다시 싣는다.
- **첫 걸음 지표** — 질의 기록 결과 줄(찾기 → 600초 안 부르기 → 성공)을 `platform_feedback_report.py` 가 이미 읽는다. '첫 성공 호출까지 걸음 수' 를 더한다.
- **손댈 곳** — `tool_search_eval/pairs.jsonl`(+ `source: he` · `purpose`), `run.py` 의 `_summary`(app@1 · purpose@1), `/search-eval` 처리기, `usage_rollup.py`.
- **위험** — 같은 쌍으로 손잡이를 고르면 그 쌍에 맞춘 값이 된다 → 손잡이를 고른 쌍과 받아들이는 쌍을 나눈다(README '진단' 의 경고 그대로).
- **기본값에서 바뀌는 것** — 없다(측정만).

---

## 8. 확인하지 못한 것

- cae00 의 백엔드별 도구 수 · 영역별 수 · 보기 채택 · 질의 기록 · 박스 정답쌍(이 박스에서 못 읽는다).
- Claude Desktop 이 MCP 도구를 지연하는지(Claude Code 는 이 세션에서 지연을 봤다).
- prompts/get 이 감사에 남는지(코드를 끝까지 따라가지 않았다).
- 운영 박스의 `search_tuning.local.json` · `core_vocab.local.json` 내용(11-16 덧씌우기 이후 무엇이 켜졌는지).
