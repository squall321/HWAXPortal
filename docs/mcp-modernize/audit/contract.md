# MCP 게이트웨이 도구 계약 품질 전수 조사 (2026-11-27, dev)

읽기만 했다. 어떤 리포도 고치지 않았고, 서비스를 재기동하지 않았으며, 도구를 부르지 않았다.
자료는 이 폴더의 `tools-list.json`(dev 게이트웨이 서비스 시야 tools/list 797개) · `tools-map.json` · `health.json` 과
게이트웨이 소스(`/home/koopark/claude/HWAXMcpGateway/gateway.py` 13,056줄 · `read_tools.json` · `audit.jsonl`), 앱 소스다.
재현 스크립트는 같은 폴더의 `analyze.py`(앱별 점수) · `analyze2.py`(인자 세부)이고, 중간 결과는 `app-metrics.json` ·
`tool-metrics.json` · `args-detail.json` · `candidates.txt` · `samples.txt` 에 있다.

표기 — **[확인]** 은 자료 · 소스에서 직접 센 것이다. **[짐작]** 은 정황으로 미룬 것이고 확인 방법을 붙였다.

---

## 0. 한눈에

| 항목 | 수 | 근거 |
|---|---|---|
| 도구 | 797 = 백엔드 765 + 게이트웨이 자체 32 (백엔드 17개 + `_gateway`) | [확인] `health.json` tools 765, tools/list 797 |
| 설명 글자 합 | 514,648자 (tools/list JSON 994,370바이트) — StepForge 혼자 271,261자(52.7%) | [확인] |
| 설명 100자 미만 / 3,000자 이상 | 57 / 18 | [확인] |
| 웹 챗 상한(2,400자)을 넘는 설명 | 28 (StepForge 23) — 그 꼬리에만 뜻이 적힌 인자 24개가 웹 챗에서 사라진다 | [확인] `HWAXAgentServer/app.py:1759` · `:2958-2985` |
| 인자 | 2,998 · 설명 있음 1,136(0.379, 게이트웨이 자체를 빼면 0.358) | [확인] 점수판과 같은 셈 |
| 설명도 없고 도구 설명에 이름조차 안 나오는 인자 | 750 (25%) | [확인] `analyze2.py` |
| enum 이 달린 인자 | 13 (게이트웨이 10 · AIDataHub 2 · 심의 1). 앱 소스의 `Literal` 은 심의 서버 3개뿐 | [확인] |
| 값 나열이 글에 있는데 enum 이 없는 문자열 인자 | 142 이상(하한 — 줄머리 꼴만 셌다) · 이름이 정해진 낱말꼴인 것 235 더 | [확인]/[짐작] 경계 |
| 숫자 인자 709 가운데 스키마 경계(minimum · maximum)가 있는 것 | 11 | [확인] |
| 구조 없는 자유형 객체 인자(`type: object` 에 properties 없음) | 237 (Laminate 90 · StepForge 42 · SmartTwin 19) | [확인] |
| annotations 가 있는 도구 | 273/797 — StepForge 207 · Laminate 43 · 게이트웨이 10 · MXWP 9 · DocForge 4, 나머지 13개 앱은 0 | [확인] |
| outputSchema | 107/797 — **107개 전부** FastMCP 자동 껍데기(`{"result": …}` 또는 빈 객체)라 필드 정보 0 | [확인] |
| MCP prompts | 서비스 시야 0. 게이트웨이는 사람 PAT 의 루틴 프롬프트만 내고, 앱 프롬프트 5개(MaterialTwin 2 · AIDataHub 3)는 모으지 않는다 | [확인] `gateway.py:9994-10030` |
| 이름이 앱 사이에 겹쳐 접두가 붙은 도구 | 원래 이름 12개 → 노출 25개 | [확인] `tools-map.json` orig |
| dev 감사 원장 신호 | 최근 14일 421줄 중 315줄이 토큰 만료 거절, 도구 호출 106 · 실패 14. 60일 호출 1,830 · 실패 129 | [확인] — 운영 대표성 없음 |

---

## 1. 가장 큰 결함 다섯

1. **인자 계약이 스키마가 아니라 산문에 있다.** [확인] 인자 2,998개 중 스키마 설명은 1,136개이고, 750개는 도구 설명에 이름조차 없다.
   enum 은 13개, 숫자 경계는 11개, 자유형 객체가 237개다. 모델은 산문을 읽고 값을 짓는다. 에이전트 서버 주석에 그 결과가
   적혀 있다 — 설명이 잘려 `units` 선택지가 사라지자 계획자가 `units="MPa"` 를 지어냈다(`HWAXAgentServer/app.py:2972-2976`).
   SignalForge · RA · MaterialTwin · AIDataHub · MXWP · WDA · ste · ThermalShock · WebResearch · DocForge · PaperIngest 는 0% 다.
   앱 소스는 모두 공식 SDK `mcp.server.fastmcp` 인데 이 FastMCP 는 docstring 의 「Args:」 를 스키마로 옮기지 않는다 — 그래서
   SignalForge 처럼 Google 꼴 「Args:」 를 정성껏 써도 inputSchema 는 비어 있다.

2. **웹 챗은 긴 설명의 꼬리를 자르는데, 인자 뜻이 그 꼬리에 있다.** [확인] 챗 바인딩 상한 `TOOL_DESC_MAX` 기본 2,400자
   (`HWAXAgentServer/app.py:1759`, dev `.env` 는 120자 — `HWAXAgentServer/.env:1`), 심의 인자 계획 상한 `CATALOG_DESC_MAX` 4,000자
   (`app.py:1756`). 2,400자를 넘는 설명이 28개(StepForge 23 · RA 2 · SignalForge 1 · 심의 1 · SmartTwin 1)이고, 스키마 설명 없이
   2,400자 뒤에만 뜻이 적힌 인자가 24개다(예: StepForge `match_parts_across` 의 `limit` · `scan_budget` · `page` · `offset` 은 4,149~5,417자
   자리, RA `create_report_from_format` 의 `title` · `entity_ids` 는 3,791~4,355자 자리). 개인 Claude 는 전문을 받으므로 같은 도구가 길마다
   다른 계약으로 보인다.

3. **SmartTwin 은 계약을 다 써 놓고 숨긴다.** [확인] 직접 노출 도구 19개의 inputSchema 가 `args: object|null` 하나뿐이다. 그런데 운영 코드
   (`KooSlurmInstallAutomationRefactory/dashboard/smarttwin_mcp`)의 카탈로그 `tools/<이름>/<판>/args.schema.json` 에는 게이트웨이에 보이는
   도구 18개의 최신판 인자 103개가 **전부 설명이 있고 enum 7개**가 있다. `_register_direct`(같은 리포 `src/smarttwin_mcp/server.py:234-250`)가
   `def _direct(args: dict | None = None)` 로 등록해 그 스키마를 버린다. 고칠 자리가 한 함수다. 점수판은 이 앱을 「인자 25개 · 설명 0」 으로
   세는데 실제로는 103개 · 100% 다(측정 결함이기도 하다 — 7절).

4. **읽기 · 쓰기 표지가 13개 앱에 없어서 안전 판정이 이름 낱말에 기댄다.** [확인] annotations 0 인 앱이 13개다. 루틴 단계 · 읽기 전용 PAT 의
   읽기 판정에서 193개 도구가 **이름의 조회 낱말만으로** 열리고(`gateway.py:9733-9760` 의 마지막 갈래), 148개가 이름 낱말만으로 쓰기로
   분류된다. 이름 꼴 오판도 실제로 있다 — 확인된 읽기 도구 넷(AIDataHub `get_record` · `get_record_sections` · `describe_record_schema`,
   ste `get_sync_settings`)이 쓰기 낱말 `record` · `sync`(`gateway.py:3602-3605`)에 걸려 tools-map `write` 에 올라 있고, `search_tools` 가
   쓰기 의도 없는 질문에서 점수를 0.5배로 깎는다(`gateway.py:4271-4274`, `search_tuning.json` weights.write_penalty 0.5). `read_tools.json`
   의 tools 목록에 넷 다 있지만 `_tool_is_write`(`gateway.py:4080-4091`)는 override 만 보고 이 목록은 보지 않는다. `get_record` 는
   dev 60일 15회 · `get_record_sections` 27회 불린 축이다.

5. **설명이 계약 대신 이력을 싣고, 형식이 앱마다 제각각이다.** [확인] StepForge 207개 중 162개가 결정 번호(D-xxx) · 날짜를, 54개가 「실측」 일화를
   싣는다. SmartTwin 8개는 첫머리가 판 이력(`v1.1.2: …`)이다. DynaForge 46/120 은 한국어 뒤에 같은 뜻의 영어 문장이 붙는다. AIDataHub 는
   영어 15 · 한국어 15 로 반반이다. 반대로 PaperIngest 4개 · WDA 8개 · DynaForge 11개 · MXWP 11개는 100자도 안 돼 돌려주는 꼴 · 한도 ·
   오류 꼴이 없다. 페이지 계약도 약하다 — `limit` 꼴 인자가 있는 도구 186개 중 상한을 적은 것 69개, 잘림 신호(total · truncated · next)를
   말하는 것 79개다(StepForge 78개 중 23 · 39, RA 18개 중 2 · 3, AIDataHub 10개 중 0 · 4). MaterialTwin `list_materials` 는 설명이
   「총 건수 · 절단 여부를 알려주지 않는다」 고 결함을 스스로 적고 있다.

---

## 2. 앱별 점수표

열 뜻 — **desc** 설명 평균/가운데 글자 수 · **<100/≥3k/>2.4k** 짧은 · 아주 긴 · 웹 챗 상한을 넘는 설명 수 · **형제%** 같은 앱의 다른 도구 이름을
설명에 적은 비율 · **인자%** 스키마 설명 비율 · **뽑힘** 스키마 설명은 없지만 docstring 줄머리 `인자: 뜻` 꼴로 기계적으로 뽑히는 인자 수 ·
**무문서** 스키마 설명도 없고 도구 설명에 이름도 없는 인자 · **enum빠짐** 값 나열이 글에 있는데 enum 없음(하한) / 이름이 정해진 낱말꼴 ·
**자유객체** 구조 없는 객체 인자 · **ann%** annotations 비율 · **out%** outputSchema 비율(전부 껍데기) · **오류(60일)** dev 감사 원장의
호출/실패(토큰 만료 거절 제외). 언어는 한/영/섞임 설명 수.

| 앱 (백엔드 키) | 도구 | desc 평균/가운데 | <100/≥3k/>2.4k | 언어 한/영/섞임 | 형제% | 인자 | 인자% | 뽑힘 | 무문서 | enum빠짐 | 자유객체 | ann% | out% | 오류(60일) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| StepForge (heax-step_forge) | 207 | 1,310/956 | 2/15/23 | 207/0/0 | 85 | 1,056 | 36 | 87 | 198 | 36/107 | 42 | 100 | 0 | 468/32 (6.8%) |
| DynaForge MCP (heax-kooremapper_mcp) | 120 | 404/278 | 11/0/0 | 100/0/20 | 50 | 405 | 48 | 5 | 129 | 24/31 | 14 | 0 | 0 | 65/1 |
| ReportArchive (reportarchive) | 96 | 584/431 | 1/2/2 | 95/0/1 | 86 | 326 | 0 | 28 | 137 | 4/24 | 12 | 0 | 0 | 38/13 ※ |
| HWAX Risk (heax-hwax_risk) | 52 | 340/333 | 5/0/0 | 51/0/1 | 33 | 232 | 100 | – | 0 | 31/10 | 14 | 0 | 0 | 54/1 |
| Laminate Analyzer (heax-laminate_analyzer_mcp) | 43 | 488/486 | 1/0/0 | 40/0/3 | 51 | 173 | 100 | – | 0 | 19/1 | 90 | 100 | 0 | 20/0 |
| MX 백서 (mx-white-paper) | 41 | 167/155 | 11/0/0 | 27/1/13 | 39 | 97 | 0 | 0 | 49 | 0†/7 | 7 | 22 | 100 | 57/10 |
| SignalForge (signalforge) | 37 | 393/245 | 0/0/1 | 35/0/2 | 14 | 156 | 0 | 93 | 46 | 12/12 | 0 | 0 | 5 | 24/2 |
| MaterialTwin (heax-materialtwin_web) | 34 | 391/305 | 0/0/0 | 33/0/1 | 76 | 124 | 0 | 17 | 53 | 2/13 | 4 | 0 | 24 | 175/14 (8.0%) |
| AI 데이터 허브 (ai-data-hub) | 32 | 302/246 | 2/0/0 | 15/15/2 | 56 | 107 | 0 | 0 | 56 | 0/19 | 4 | 0 | 88 | 786/35 (4.5%) |
| 게이트웨이 자체 (_gateway) | 32 | 334/312 | 1/0/0 | 32/0/0 | 38 | 106 | 96 | – | 3 | 6/0 | 8 | 31 | 0 | 15/2 |
| WebDesignAgents (heax-web_design_agents) | 24 | 176/161 | 8/0/0 | 21/0/3 | 33 | 58 | 0 | 1 | 35 | 1/7 | 3 | 0 | 0 | 3/1 |
| SmartTwin (smart-twin-mcp) | 23 | 600/338 | 1/0/1 | 8/6/9 | 57 | 25 (숨은 103) | 0 (숨은 100) | 0 | 17 | 0/0 | 19 | 0 | 100 | 26/4 |
| ste (ste) | 13 | 324/305 | 1/0/0 | 13/0/0 | 85 | 22 | 0 | 4 | 12 | 0/1 | 2 | 0 | 8 | 18/6 |
| 전문가 심의 (hwax-deliberation) | 13 | 1,291/678 | 1/1/1 | 13/0/0 | 62 | 60 | 100 | – | 0 | 4/2 | 10 | 0 | 0 | 17/0 |
| ThermalShock (heax-thermal_shock_mcp) | 12 | 241/207 | 4/0/0 | 10/0/2 | 58 | 20 | 0 | 5 | 7 | 0/1 | 8 | 0 | 0 | 24/0 |
| 웹 리서치 (heax-web_research_mcp) | 8 | 189/169 | 1/0/0 | 8/0/0 | 38 | 15 | 0 | 15 | 0 | 1/0 | 0 | 0 | 0 | 16/0 |
| DocForge (heax-doc_forge) | 6 | 258/157 | 3/0/0 | 5/0/1 | 33 | 10 | 0 | 4 | 3 | 2/0 | 0 | 67 | 0 | 0/0 |
| PaperIngest (heax-paper_ingest) | 4 | 53/57 | 4/0/0 | 4/0/0 | 0 | 6 | 0 | 0 | 5 | 0/0 | 0 | 0 | 100 | 12/0 |

※ RA 의 실패 13 중 8은 `get_report` 의 `refused: no-connection` — 연결 등록 문제이지 계약 문제가 아니다.
† MXWP 는 값 나열을 문장 가운데(`format: docx | pptx | pdf | markdown`)에 써서 줄머리 셈에 안 잡혔다 — 실제로는 있다(예 `export_document` · `search_knowledge`).

### docstring 형식 판정(앱마다 표본 3개 — `samples.txt`)

게이트웨이가 docstring 에서 인자 설명을 대신 뽑을 수 있나를 보려고 앱마다 인자 있는 도구 3개를 골라 형식을 봤다.

| 앱 | 형식 | 판정 |
|---|---|---|
| SignalForge | Google 꼴 `Args:` 절(37개 중 30개) · 나머지는 산문 | **뽑힘** — 93/156 |
| 웹 리서치 | Google 꼴 `Args:` 절 | **뽑힘** — 15/15 |
| DocForge | 줄머리 `parser: …` · 한 줄에 두 인자(`vlm: … llm: …`)가 섞임 | 일부 — 4/10, 경계 오류 위험 |
| ThermalShock | 줄머리 `sample: SedInput dict — …` | 일부 — 5/20, 뽑아도 그 인자가 자유형 객체라 구조는 없다 |
| ste | 줄머리 정렬 `app:       …`(제출 도구) · 나머지 산문 | 일부 — 4/22 |
| MaterialTwin | 산문 + 일부 줄머리 `attributes: …` | 일부 — 17/124 |
| ReportArchive | 마크다운 산문 + 일부 줄머리 `` `workflow`: … `` | 일부 — 28/326 |
| StepForge | 굵은 글씨 산문 + 백틱 인자명이 문장 속 · 일부 Field 설명(36%) | 거의 안 뽑힘 — 87/680 |
| DynaForge | 한국어 산문 + 백틱 · 영어 요약 한 줄 · Field 설명 48% | 안 뽑힘 — 5/212 |
| MXWP | 한 줄 산문, 값 나열이 문장 속 | 안 뽑힘(줄머리 아님) |
| AIDataHub | 영어 · 한국어 산문 | 안 뽑힘 — 0 |
| WDA | 산문 | 안 뽑힘 — 1/58 |
| SmartTwin | 영어 산문 + 판 이력, 진짜 인자는 카탈로그 스키마 | 해당 없음 — 앱 한 자리 고침이 답 |
| PaperIngest | 한 줄 | 안 뽑힘 |
| Risk · Laminate · 심의 · 게이트웨이 자체 | `Annotated[…, Field(description=…)]` | 이미 채워짐 |

---

## 3. 앱별 고칠 것 상위 10

각 줄 — **도구** · 무엇 · 왜. 별표 없는 것은 [확인], (짐작)은 표시했다.

### StepForge (207)
1. **section_pair_view** · `axis` 설명이 「필수」 인데 스키마는 `default: ""` 이고 enum 없음 → required + enum `[x, y, z]`, `format` · `unit`(mm 만 받음) enum · 설명 5,282자를 앞 2,400자에 계약 요지로 · 왜: dev 60일 14번 중 7번 실패(오류 글은 원장에 없음 — 인자 누락 가능성은 짐작).
2. **section_view** · 5,683자 · `format` enum 없음 · 왜: 웹 챗에서 절반 넘게 잘린다.
3. **match_parts_across** · `limit` · `scan_budget` · `page` · `offset` 뜻이 4,149~5,417자 자리에만 있음 → Field 설명 · 왜: 웹 챗에서 인자 뜻이 통째로 사라진다. 대응을 남기는데 readOnlyHint=True(표지 재검토 — 짐작).
4. **record_dimension** · 3,032자 · `args` 자유형 객체(어떤 측정 도구의 인자인지 스키마 없음) · 왜: 기록 도구라 잘못된 인자가 남는다.
5. **align_image_to_geometry** · 인자 14 중 13 설명 없음 · `mode` · `region` enum 없음 · 2,349자 · 왜: 설명 상한 경계에 걸쳐 있다.
6. **set_revision** · 2,471자 · 인자 12 중 10 설명 없음 · `rev_label` · `task_code` · `status` 규칙이 산문뿐 · 왜: PLM 개정을 확정하는 쓰기다.
7. **intake · set_project_meta** · 인자 대부분 설명 없음(9/9 · 9/10) · `extras` · `tol_config` 자유형 · 왜: 반입 첫 관문이라 오해 비용이 크다.
8. **onto_* 16종 + ontology_model** · `onto_query` · `onto_search` · `onto_walk` · `onto_neighbors` · `onto_reach` · `onto_path` · `onto_lineage` · `onto_explode` 가 같은 그래프 질의의 변형 · `onto_walk` `mode` enum 없음 · 왜: 모델이 고를 근거가 각 설명 끝의 「몇 단계 안은 onto_neighbors…」 한 줄뿐이다. 입구 하나 + 표, 또는 묶음.
9. **interface_graph · list_interfaces** · `fmt`(mermaid|json|dot) · `kind` enum 없음 · 왜: dev 60일 실패 6/8 · 7/18(10-11 한 회차 — 원인 짐작 불가).
10. **설명 일반** · 162/207 에 D-번호 · 날짜, 54개에 「실측」 일화, 설명 합 271,261자 · `limit` 꼴 도구 78개 중 상한 적은 것 23 · 왜: 개인 Claude tools/list 무게의 절반이 이 앱이고, 이력은 계약이 아니다. 이력은 docs 로, 설명은 무엇 · 언제 · 꼴 · 한도 · 오류로.

### DynaForge MCP (120)
1. **전 도구 annotations 0** · 37개가 이름 꼴로만 쓰기, 26개가 이름 꼴로만 읽기 판정 · `read_tools.json` 에 15개를 손으로 올려 두었다 · 왜: 등록 자리에서 표지 한 줄이면 손 목록이 필요 없다.
2. **report_* 31종** · `report_query` · `report_summary` · `report_findings` · `report_case` · `report_facets` · `report_analytics` · `report_corpus` 가 겹친다 · 왜: 「무엇을 물을 때 어느 것」 표가 없다(list_operations 처럼 한 곳에).
3. **set_campaign_* 7종** · criteria · frame_offset · health_thresholds · pair_rule · part_groups · required_extractions · sites · 왜: 한 도구(필드 이름 enum)로 묶을 만하다.
4. **report_query** · `metric` 8 낱말인데 enum 없음 · 인자 13 모두 설명 없음.
5. **find_cae_parts · find_cae_load_paths** · `kind` · `min_severity` · `sort` 를 「중 하나」 라고 적고 enum 없음.
6. **create_campaign** · `dev_rev`(pre|dv1..dvr|…) enum 없음 · `impactor` · `health_thresholds` · `required_extractions[]` 자유형 · 문서는 required_extractions 필수, 스키마는 선택.
7. **mesh_surface_figure · mesh_section_figure · mesh_stack_diagram** · 인자 8~10개 전부 설명 없음(azimuth · elevation 단위 등).
8. **update_session 외 짧은 설명 11개** · 돌려주는 꼴 · 한도 없음.
9. **heaxkooremapper_mcp_recipe_run** · `params` 자유형 · SmartTwin `recipe_run` 과 겹쳐 접두.
10. **이름 겹침 7개**(cancel_job · list_reports · recipe_run · system_capabilities · system_status · whoami) · 노출 접두 `heaxkooremapper_mcp_` 가 제품명(DynaForge)과 달라 사람도 모델도 못 알아본다 · 46/120 설명에 같은 뜻 영어 문장.

### ReportArchive (96)
1. **인자 326개 설명 0** · 등록 길목이 `tool(group)` 한 자리(`ReportArchive/mcp_server/server.py:247-269`) · 왜: 그 자리에서 docstring → Field 와 그룹별 표지를 한 번에 넣을 수 있다(RA 리포 커밋은 이 포털 세션 몫이 아니다 — RA 세션 몫).
2. **reportarchive_list_reports** · 인자 21 · 설명 0 · 기간 인자(last_days · period · date_from · date_to) 관계가 산문 · DynaForge 와 이름 겹침.
3. **create_report_draft** · 인자 14 · 설명 0 · `blocks` · `block_sections` 자유형 · 왜: dev 5번 중 3번 실패.
4. **create_report_from_format** · 4,413자 · `data` 자유형(설명이 「RA 가 검증하지 않는다」) · `title` · `entity_ids` 설명이 2,400자 뒤.
5. **search_reports** · 인자 15 설명 0.
6. **update_report_draft · patch_cells · append_rows · remove_rows** · 쓰기인데 표지 없음 · `expected_revision` · `dry_run` 뜻이 산문.
7. **annotations 0 전반** · 47개가 이름의 조회 낱말로만 읽기, 34개가 이름으로만 쓰기.
8. **[시스템 관리자 전용] 21개** · SP 매핑 · 데이터 소스 · 경보 규칙 도구가 모두의 목록에 · 왜: 보기(light · bundle)나 역할로 빼면 목록이 22% 준다.
9. **list_analysis_runs · get_analysis_peaks · aggregate_reports** · `workflow` · `quantity` · `phase` · `lifecycle` enum 없음.
10. **페이지 계약** · `limit` 꼴 18개 중 상한 적은 것 2, 잘림 신호 3.

### HWAX Risk (52)
1. **annotations 0** · 설명 첫머리에 「쓰기:」 「읽기 전용」 을 적어 두었는데 기계 표지가 없다 · 그래서 읽기 판정이 이름 낱말에 기댄다(21개가 조회 낱말로만 열림).
2. **risk_add_finding** · `domain` · `mechanism` 이 통제 어휘(risk_taxonomy — 「추측해 넣으면 422」)인데 enum 없음.
3. **risk_job_action** · `action`(pause · resume · cancel · retry_failed · skip_failed) enum 없음 · `reason` 은 skip_failed 에 필수인데 스키마는 선택(조건부라 oneOf 또는 설명 맨 앞에).
4. **risk_start_job** · 1,449자 · `tier` 문서 필수/스키마 선택 · `scope` 자유형.
5. **risk_set_board_transform** · `board_body` · `force` · `reason` 문서 필수/스키마 선택(짐작 — 조건부일 수 있다).
6. **risk_submit_panel_result** · `turns[]` · `evidence_omitted[]` 자유형.
7. **risk_decide_sameas** · `decisions[]` 자유형(confirm|reject).
8. **risk_similar_projects · risk_get_precedents · risk_get_panel_transcript** · 50자 안팎 · 돌려주는 꼴 · 한도 없음.
9. **enum 빠짐 31** · severity · judgement · direction 등 통제 어휘 칸 전반 · risk_taxonomy 를 부르기 전엔 모른다.
10. **형제 안내 33%** · 「risk_next_step 부터」 안내가 일부 도구에만.

### Laminate Analyzer (43) — 기준 모델이지만
1. **laminate 자유형 객체** · 43개 도구 전부, 자유형 인자 90 · 꼴이 인자 설명 산문에만 · 왜: `$defs` 로 Laminate · Lamina · Material 스키마를 걸면 모든 도구가 한 번에 정확해진다.
2. **값 나열 19개** · `neutral_axis_mode` · `mode` · `include` · `language` · `detail` 이 `"a"|"b"` 로 적혀 있고 enum 없음 → `Literal`.
3. **필수 어긋남 4** · compute_thermal_response · recover_ply_stresses 의 `panel`(문서 필수/스키마 선택), derive_lamina_from_constituents 의 `fiber` · `matrix`(반대).
4. **outputSchema 0** · 결정론 계산 커널이라 출력 스키마를 붙이기 가장 쉬운 앱.
5. **설명의 결정 · 날짜 참조 15 · 「실측」 14**.

### MX 백서 (41)
1. **인자 97 설명 0** · 한 줄 산문, 13개 영/한 섞임.
2. **export_document** · `format: docx | pptx | pdf | markdown` 이 문장 속 · enum 없음.
3. **search_knowledge** · `kind: lat|guide|doc|archive` enum 없음.
4. **get_document_outline** · dev 9번 중 5번 실패(원인 글 없음).
5. **insert_block · update_block · validate_block** · `block` 자유형 — 설명이 「로컬 schema 검증」 이라고 하니 그 스키마를 inputSchema 로.
6. **wiki_propose · wiki_fileback** · `ops[]` · `citations[]` 자유형.
7. **delete_block · move_block · get_block · list_documents** · 80자 미만 · 쓰기 15개 표지 없음.
8. **outputSchema 41/41** · `{"result": …}` 껍데기 — 필드 정보 0.
9. **query_rules** · 영어 · `backend`(bm25 …) enum 없음.
10. 운영 MCP 서버 소스 위치가 리포 안에서 분명하지 않다(`dist/llm-docx-toolkit/mcp/server.py` 만 찾았다 — 확인 필요).

### SignalForge (37)
1. **인자 156 설명 0** · 그런데 30개 도구가 `Args:` 절을 가져 93개가 기계적으로 뽑힌다 · 등록 길목 `_MaskedFastMCP.tool`(`SignalForge/mcp-server/server.py:99`) 한 자리에서 옮길 수 있다.
2. **query_voc** · `category`(12 낱말) · `sentiment`(3) enum 없음.
3. **search_voc** · 2,919자 · `match`('auto'|'phrase'|'fts'|'substring') enum 없음 · `core_type` 뜻이 2,400자 뒤.
4. **defect_profile** · `component` · `severity` enum 없음.
5. **signalforge_semantic_search** · `order` enum 없음 · AIDataHub 와 이름 겹침으로 접두.
6. **defect_timeline · keyword_stats · defect_evidence · defect_cooccurrence · defect_onset** · 인자 6~10개, `Args:` 없는 산문 · `interval` enum 없음.
7. **voc_breakdown · defect_breakdown · period_compare** · `by` 축 이름 enum 없음.
8. **형제 안내 14%** · search_voc ↔ keyword_stats ↔ query_voc 의 「언제 무엇」 이 일부만.
9. **annotations 0** · 쓰기 낱말 도구가 없다 — 전부 readOnlyHint 한 줄로 끝난다.
10. **들여쓰기 낭비 12%** · docstring 앞 공백.

### MaterialTwin (34)
1. **compare_materials** · `materials` 가 `list[str]` 이라 「id 도 ["73","68"] 처럼 문자열로」 라고 설명이 결함을 적어 둠 · dev 4/4 실패 → `list[int | str]` 로 받기.
2. **search_catalog_property** · `property_key` 가 157개 닫힌 어휘인데 설명 · enum 없음(틀리면 `{"error": "알 수 없는 property_key …"}` — `MaterialTwinWeb/backend/mcp_server.py:826-842`) · dev 72번 중 6번 실패(키 오답인지는 짐작).
3. **get_material** · `material_id` 정수만 · 이름을 주면 실패(짐작) · dev 8번 중 4번 실패.
4. **list_materials** · 「총 건수 · 절단 여부를 알려주지 않는다」 → total · truncated 를 돌려주기.
5. **register_property** · 인자 18 설명 0 · `conditions` 자유형.
6. **register_tensile_test · register_relaxation_test** · 단위(mm · MPa · 무차원)가 산문에만, 인자 10.
7. **export_dyna_cards** · `units`(ton_mm_s · kg_m_s · g_mm_ms · kg_mm_ms) enum 없음 — 에이전트 서버 주석의 `units="MPa"` 날조 사례가 바로 이 칸이다.
8. **find_materials_by_metadata** · `limit` 상한 없음 · 총계 없이 잘림.
9. **annotations 0** · 쓰기 7개(register_* · update_material · set_instrument_ownership).
10. **register_material** · StepForge 와 겹쳐 `heaxmaterialtwin_web_register_material` 접두.

### AI 데이터 허브 (32)
1. **설명 영/한 반반 · 인자 107 설명 0 · docstring 에 Args 없음** · 게이트웨이 검색은 한국어 동의어 중심이라 영어 설명 도구가 한국어 질의에 덜 잡힐 수 있다(짐작 — `/search-eval` 로 확인).
2. **agent_search** · 가장 많이 불리는 축(60일 113회) · 실패 11(600초 시간 초과 2 포함) · `agent_type` 설명 없음.
3. **recommend_agents** · `onto`(off · shadow · rank) enum 없음.
4. **list_records** · 인자 10 · `limit` 상한 없음 · 133회 호출.
5. **get_record · get_record_sections · describe_record_schema** · 게이트웨이가 이름의 `record` 로 쓰기 분류 → 검색 점수 반감(게이트웨이 쪽 고침 — 6절).
6. **import_record · create_agent · patch_agent · create_doc_type** · 자유형 객체.
7. **get_context_bundle** · `format` enum 없음 · `max_records` 상한.
8. **echo_args · fetch_rerank_model** · 시험 · 운영 도구가 일반 목록에.
9. **outputSchema 28/32 껍데기**.
10. **hybrid_search · fts_search · aidatahub_semantic_search** · 세 검색의 「언제 무엇」 이 영어 산문에만 · semantic_search 는 겹쳐 접두.

### 게이트웨이 자체 (32)
1. **rest_catalog · rest_call** · tools/list 에는 있는데 `/tools-map` 의 map · areas 에 없다 — 점수판 · 영역 귀속에서 빠진다.
2. **annotations 31%** · 로컬 읽기 도구(search_tools · list_tool_apps 등)에 표지가 없다.
3. **procedure_run_start** · `inputs` 문서 필수/스키마 선택.
4. **invoke_tool · routine_call** · `arguments` 자유형(성격상 불가피 — 설명에 「대상 도구의 inputSchema 를 따른다」 한 줄).
5. **save_conversation** · `subject` 꼴이 설명 산문.

### WebDesignAgents (24)
1. **인자 58 설명 0 · 짧은 설명 8**.
2. **meeting_submit_turn** · 인자 8 · `citations[]` · `artifacts[]` 자유형.
3. **approval_record** · `point`(participants|scenario|shipping|action_items|golden) · `decision` enum 없음.
4. **meeting_start** · `type` enum 없음 · `participants` id 를 meeting_personas 로 본다는 안내가 meeting_personas 쪽에만.
5. **render_submit** · `fps` · `pptx_mode` enum · 범위 없음.
6. **report_ingest** · 78자 · `file` 이 어느 경로인지.
7. **annotations 0** · 쓰기 7.
8. **meeting_status · meeting_minutes · meeting_list · meeting_close** · 50자 미만.
9. **scenario_patch** · `ops[]` 자유형.
10. **qa_run** · `gates` enum.

### SmartTwin (23)
1. **직접 노출 19개가 `args: object` 하나** · 숨은 인자 103(설명 103 · enum 7) · 고칠 자리 `KooSlurmInstallAutomationRefactory/dashboard/smarttwin_mcp/src/smarttwin_mcp/server.py:241-242`.
2. **판 이력 첫머리 8개**(`v1.1.2: …`) · 계약 대신 변경 기록.
3. **영/한 섞임 9**.
4. **echo** · 시험 도구가 노출 · dev 9번 중 4번 실패.
5. **outputSchema 23/23 껍데기**.
6. **annotations 0** · job_stop · job_rerun · submit_* 가 이름 꼴로만 쓰기.
7. **submit_job · job_status · recipe_run** · 겹쳐 `smarttwinmcp_` 접두.
8. **catalog_versions** · 48자.
9. **fullangle_drop_simulation · single_drop_simulation** · 2,300~2,466자 대부분이 판 이력.

### ste (13)
1. **인자 22 설명 0** · ste_submit_job 만 줄머리 꼴이라 뽑힌다.
2. **ste_list_jobs** · `state`(PENDING|RUNNING|COMPLETED|FAILED|CANCELLED|active) enum 없음 · dev 7번 중 2번 실패.
3. **ste_submit_job** · `params` · `files[]` 자유형 — get_app_schema 의 스키마를 가리키기만.
4. **cluster_info** · 54자 · dev 실패 3/8 은 forbidden · no-identity(권한).
5. **get_sync_settings** · 게이트웨이가 `sync` 로 쓰기 분류 → 검색 감점.
6. **annotations 0**.
7. **get_job_file** · 64KB 상한이 설명엔 있고 스키마 경계는 없다.
8. **설명에 「(게이트웨이 이름: ste_submit_job)」** · 앱이 게이트웨이 접두 규칙을 박아 두었다 — 박스마다 겹침이 달라 틀릴 수 있다.

### 전문가 심의 (13)
1. **deliberate_start** · 7,757자 — 웹 챗 2,400 · 심의 계획 4,000 상한 모두 넘음 · status 진행 설명은 deliberate_status 로 옮기기.
2. **evidence[] · personas[] · advanced · subject** · 자유형 객체(꼴이 인자 설명 산문).
3. **job** · 10 종류가 설명에 나열 · enum 없음(modifiers 도 같다).
4. **annotations 0** · deliberate_status · result · list · transcript 읽기 표지.
5. **deliberate_status** · 2,307자.

### ThermalShock (12)
1. **predict_sed** · `sample` 자유형 · 필수 키와 값(board_type INT|HALF|FULL · pkg_type WLP|FX|DIG)이 산문 → SedInput 스키마.
2. **predict_sed_batch** · `samples[]` 같은 문제.
3. **sed_sample_from_odb** · 자유형 객체 4개.
4. **get_training_data** · `pkg_type` enum 없음.
5. **activate_model · train_model · add_training_data · remove_training_data** · 모델 활성 전환 · 데이터 삭제인데 표지 없음.
6. **list_models · get_dataset_summary · activate_model · get_model_info** · 60자 안팎.
7. **add_training_data** · `records[]` 자유형.

### 웹 리서치 (8)
1. **인자 15 설명 0** · Google `Args:` 100% 라 한 줄 헬퍼(또는 게이트웨이 채움)로 100% 가 된다.
2. **search_scholar** · `sources` enum 없음 · `limit`(1~20) 스키마 경계 없음.
3. **search_web · search_scholar** · 외부로 나가는데 openWorldHint 없음.
4. **annotations 0**.

### DocForge (6)
1. **docforge_convert** · `parser`(auto|skeleton|docling|native) · `snapshot_blocks`(selected|all|none) enum 없음 · 인자 7 설명 0.
2. **docforge_convert · docforge_cancel** · 쓰기 · 취소인데 표지 없음(읽기 넷은 readOnlyHint 있음).
3. **docforge_cancel** · 35자.

### PaperIngest (4)
1. **설명 전부 70자 미만 · 인자 6 설명 0**.
2. **submit_paper** · `content_md` 크기 상한 · `doi` 꼴 없음.
3. **ingest_now · gate_expert_now** · 쓰기 · GLM 비용이 드는데 표지 없음.
4. **outputSchema 4/4 껍데기**.

---

## 4. annotations ↔ read_tools.json 어긋남

- [확인] `read_tools.json` tools 47개 가운데 9개(StepForge interface_graph · job_status · list_interfaces · list_parts · part_mesh_map · project_tree · resolve_materials · system_status · upload_instructions)는 앱이 이미 readOnlyHint=True 를 달아 중복이다(해롭지 않음).
- [확인] 7개(odb-hub 6 · testscope:resolve)는 dev 에 그 백엔드가 없다 — cae00 전용이라 정상으로 보인다.
- [확인] 앱이 readOnlyHint=False 를 단 도구를 tools 목록이 읽기로 적은 「무력한 줄」 은 0이다. override 5개(StepForge 단면 · 적층 잡 도구)는 앱이 readOnlyHint=False 를 단 그대로이고 사용자 결정으로 읽기 취급이다.
- [확인] 앱 표지와 쓰기 이름이 엇갈리는 것 — Laminate `run_sensitivity_analysis` · `run_progressive_failure`(readOnlyHint=True, 순수 계산이라 맞다), StepForge `upload_instructions` · `assess_edit_impact`(맞다).
- [짐작] StepForge readOnlyHint=True 인데 무언가를 남기는 도구 — `match_parts_across`(끝까지 잰 대응을 남긴다) · `debug_bundle`(파일 하나를 만든다) · `part_index`(캐시). 캐시 성격이면 둬도 되지만 `debug_bundle` 은 표지를 다시 볼 만하다. 확인 — `StepForge/app/catalog.py:124` 의 분류와 각 함수 본문.
- [확인] **확인된 읽기인데 쓰기로 분류**되는 넷(`get_record` · `get_record_sections` · `describe_record_schema` · `get_sync_settings`)은 1절 4번과 같다. 루틴 · 읽기 PAT 판정은 읽기 목록을 보므로 열리지만, 검색 감점 · tools-map `write` · 운영자 알림은 이름 꼴을 따른다.

---

## 5. 이름 · 접두

- [확인] 게이트웨이는 지금 붙은 (선언 백엔드가 아닌) 백엔드끼리 원래 이름이 겹칠 때만 `<백엔드 키에서 하이픈 뺀 것>_<이름>` 을 붙인다(`gateway.py:1430-1485`). 별칭(같은 꼴)은 늘 부를 수 있지만 목록에는 없다(`gateway.py:1465`). 허브 가족은 늘 접두(dev 에는 없음).
- [확인] dev 에서 겹치는 원래 이름 12개 — cancel_job(DynaForge · StepForge · ste) · job_status(StepForge · SmartTwin) · list_jobs(StepForge · ste) · list_reports(DynaForge · RA) · prepare_upload(RA · ste) · recipe_run(DynaForge · SmartTwin) · register_material(MaterialTwin · StepForge) · semantic_search(AIDataHub · SignalForge) · submit_job(SmartTwin · ste) · system_capabilities · system_status · whoami(DynaForge · StepForge).
- [확인] 결과 — 한 앱 안에서 이름 꼴이 섞인다. StepForge 는 `heaxstep_forge_job_status` 와 맨 이름 `list_projects` 가 함께 있고, dev 감사에서 StepForge 최다 호출 이름이 `heaxstep_forge_job_status`(194회)다. 접두 `heaxkooremapper_mcp_` · `heaxmaterialtwin_web_` 는 제품명과 다르다.
- [짐작] cae00 에는 odb-hub(list_parts · find_job …) · MatNexus · FMEA 등이 더 붙어 겹침 집합이 다르다 — 같은 도구가 박스마다 다른 이름일 수 있다(예 StepForge `list_parts`). 확인 — cae00 `/tools-map` 의 orig 를 dev 와 대조.
- [확인] 앱이 스스로 접두를 다는 앱(risk_ · docforge_ · deliberate_ · wiki_ · meeting_)과 안 다는 앱(StepForge · DynaForge · RA · AIDataHub · MaterialTwin)이 섞여 있다. 맨 이름이 일반어인 도구 — RA `resolve` · `get_report` · `list_templates`, AIDataHub `discover` · `list_records` · `get_record`, SmartTwin `echo`, StepForge `intake` · `glossary` · `list_parts` · `list_artifacts`.

## 6. 크기 · 묶을 만한 무리

- **StepForge 207** — onto_* 16 + ontology_model(그래프 질의), section_* 9 + stackup_* 2(단면), compare_* 8(assemblies · dimension · part_shape · part_view · projects · revisions · snapshots · stackup), *_report 9(fastener · field_check · leak · mesh · naming · precheck · structure · thickness · inspect), register_material(s)(_csv) 3, explain_* 3, *_guide/advice 4, part_* 10. 관리 · 진단 도구(set_admin · delete_project · debug_bundle · tool_usage_report)도 같은 목록에 있다.
- **DynaForge 120** — report_* 31, campaign_* 12 + set_campaign_* 7, 세션 관리 9(create · delete · get · list · update · list_session_files · list_session_jobs · rename_session_part · session_includes), recipe_* 7, ontology_* 4, mesh_*_figure 3, attach_* 4.
- **RA 96** — list_* 23 · get_* 17, 만들기 길 6(create_report_draft · from_format · from_preset · from_run · create_html_report · create_embed_bundle), SP 매핑 관리 7, 분석 런 5, 객체 온톨로지 12. 관리자 전용 21.
- 묶는 길은 둘이다 — (가) 앱이 「입구 + mode enum」 으로 줄인다, (나) 앱은 두고 게이트웨이 보기(bundle · light)에서 무리의 대표만 보인다. (나)는 이미 있는 장치(E-4 보기)를 쓰므로 앱 고침이 없다.

## 7. 실제 쓰임 신호 (dev 감사 원장)

- [확인] dev 원장은 운영 신호가 아니다. 최근 14일 421줄 중 315줄이 `unauthorized: expired`, 도구 호출 106 · 실패 14. 60일은 호출 1,830 · 실패 129 · 그 가운데 사유 글이 빈 실패 97.
- [확인] 60일 최다 호출 — AIDataHub list_agents 205 · StepForge heaxstep_forge_job_status 194(한 폴링 고리로 보인다 — 짐작) · list_records 133 · recommend_agents 128 · agent_search 113 · get_agent_session 107 · MaterialTwin search_catalog_property 72 · StepForge glossary 42 · list_projects 40 · MaterialTwin list_materials 37.
- [확인] 실패율 상위(4회 이상) — RA get_report 8/8(refused: no-connection — 계약 아님) · StepForge section_pair_view 7/14 · interface_graph 6/8 · list_interfaces 7/18 · part_history 4/4 · MaterialTwin compare_materials 4/4 · get_material 4/8 · MXWP get_document_outline 5/9 · SmartTwin echo 4/9 · AIDataHub agent_search 11/113.
- [짐작] 계약 문제로 보이는 것 — compare_materials(설명이 「문자열 배열만」 이라는 함정을 적어 둠), search_catalog_property(닫힌 어휘 157개 · enum 없음), get_material(정수 id 만), section_pair_view(「필수」 인자가 스키마에서 선택). 실패 응답이 10ms 안팎 · 수백 자로 짧아 입력 검증이나 없는 키 오류 모양이지만, **원장에 실패 사유가 없어 확인할 수 없다**(8절 2번).

## 8. 측정 방법 자체의 결함

1. **점수판은 맨 위 인자만 센다** [확인] (`gateway.py:1259`, `:1299-1312`). 자유형 객체를 「설명 있음」 으로 세어 Laminate 100% 가 90개 자유형 인자의 구조 공백을 가린다. 반대로 SmartTwin 은 `args` 껍데기 하나만 세어 실제 인자 103개 · 설명 100% 를 못 본다.
2. **감사 원장이 앱 오류 사유를 남기지 않는다** [확인]. 백엔드가 `isError=True` 로 답하면 `ok=false` 에 `error=None` 이다(`gateway.py:12220`, `:12301`, `:12325-12329`; `_audit` 는 `ok` 인 결과에만 봉투 사유를 본다 — `gateway.py:1095`). 인자 오해와 데이터 없음과 권한을 가를 수 없다. 60일 실패 129 중 97이 사유 빈 칸이다.
3. **도구 수가 세 개다** [확인]. health 765(백엔드만) · tools-map map 796(rest_catalog · rest_call 빠짐, 관리자 전용 gateway_readonly_allowlist 포함) · tools/list 797. 점수판 total 0.379 에는 게이트웨이 자체 인자(96% 설명)가 섞여 앱 평균(0.358)보다 높게 나온다.
4. **단위 · 범위 셈의 낱말** [확인]. `기본값` · `default` 를 범위로 센다(`gateway.py:1278-1279`) — 그것만으로 센 인자는 338개 중 11개라 작다. 더 큰 문제는 enum · 숫자 경계가 있어도 설명이 없으면 세지 않는다는 것이다(설명이 전제) — 게이트웨이 save_conversation 의 `kind` 같은 칸이 빠진다.
5. **쓰기 분류가 확인된 읽기 목록을 안 본다** [확인]. 4절 · 1절 4번. tools-map `write` 198개 중 넷이 오판이다.
6. **prompts 0 은 반쯤 측정 탓이다** [확인]. 서비스 시야(GW_TOKEN)는 설계상 빈 목록이고(`gateway.py:9998-9999`), 앱 프롬프트는 게이트웨이가 아예 모으지 않는다.
7. **dev 원장은 운영 신호가 아니다** [확인]. 실패율은 cae00 원장으로 다시 재야 한다 — `tool_usage_report.py` 와 같은 길로 이름 · 수만 뽑으면 된다. 별칭 이름(heaxstep_forge_job_status)과 맨 이름을 합쳐 세야 한다(`tool_usage_report.py` `_names` 가 그 셈).
8. **이 조사 자신의 한계** — 값 나열 검출은 줄머리 꼴(`인자: …`)과 몇 가지 나열 꼴만 봐서 하한이다(MXWP · 심의 job 처럼 문장 속 나열은 빠진다). 형제 안내 비율은 「같은 앱의 다른 도구 이름이 설명에 나오나」 라 언제 쓰나의 질까지는 못 잰다. 돌려주는 꼴 · 오류 꼴은 낱말 셈이라 거칠다.

---

## 9. 게이트웨이 쪽 일괄 안 — 실현성과 위험

| 안 | 하는 것 | 효과(확인 수) | 위험 | 판단 |
|---|---|---|---|---|
| A. docstring → 인자 설명 채우기 | 줄머리 `인자: 뜻`(이어지는 들여쓴 줄 포함)을 노출 사본의 `properties[].description` 에 넣는다 | 뽑히는 인자 259개 → 전체 0.379 → 0.465. SignalForge 0 → 0.60, 웹 리서치 0 → 1.0, StepForge 0.36 → 0.44, RA 0 → 0.09 | ① 돌려주는 칸 이름이 인자와 같으면 엉뚱한 줄을 집는다(`status:` 등) ② 한 줄에 두 인자(DocForge `vlm: … llm: …`) ③ 웹 챗은 설명과 인자 설명을 둘 다 보내 같은 글이 두 번 실린다(토큰 증가) ④ 점수판이 앱의 실제 상태를 가린다 — `filled_by_gateway` 를 따로 세야 한다 ⑤ 검색 순위는 바이트까지 같아야 한다는 E-7 약속 — 검색은 도구 설명을 보므로 인자 칸만 바꾸면 안 바뀐다(짐작, 시험으로 확인) | **임시로는 됨.** 정답은 앱 쪽 — 길목 한 자리씩(RA `tool(group)` · SignalForge `_MaskedFastMCP.tool` · StepForge `catalog.register`)에 같은 헬퍼를 넣는 것. 게이트웨이 채움은 앱이 고칠 때까지만, 출처 표지와 함께 |
| B. 설명 들여쓰기 걷기(`inspect.cleandoc`) | docstring 앞 공백 제거 | 23,399자(4.5%) — StepForge 13,120 · RA 3,891 | 낱말은 그대로라 순위 영향 작음(짐작 — E-7 시험으로 확인) | **됨** — 가장 싸다 |
| C. enum 넣기 | 글의 값 나열을 enum 으로 | 142개 이상 | 나열이 예시인지 닫힌 집합인지 게이트웨이가 모른다. 엄격한 클라이언트가 enum 밖 값을 막아 지금 되는 호출이 깨진다 | **하지 않는다** — 앱이 `Literal` 로 |
| D. 쓰기 분류가 읽기 목록을 보게 | `_tool_is_write` 가 `READ_TOOLS`(확인된 읽기)를 이름 꼴보다 먼저 본다 | 오판 4개 해소, 검색 감점 제거 | 그 넷의 검색 순위가 바뀐다(의도한 변화). 기본값 순위 바이트 동일 약속의 예외로 적어야 | **됨** — 작은 고침 |
| E. 읽기 표지를 노출 사본에 | 읽기 목록의 도구에 readOnlyHint=True 를 붙여 내보낸다(선언 백엔드에는 이미 한다 — `gateway.py:1487-1489`) | 클라이언트(Claude Code 의 승인 판단 등)가 읽기를 안다 | `read_tools.json` _note 의 결정 「클라이언트가 보는 tools/list 표지는 앱이 적은 그대로다」 를 뒤집는다. 이름 꼴로 연 것은 절대 넣지 않는다 | 사용자 결정 필요 |
| F. 실패 사유를 원장에 | `isError` 결과의 첫 글 200자를 `error` 에(가림 · 자르기 거쳐) | 인자 오해 · 데이터 없음 · 권한을 가른다. 계약 품질의 실측 고리가 생긴다 | 오류 글에 사용자 입력이 섞일 수 있다 — 기존 `_pii_mask` · `_clip` 를 거친다 | **됨** — 이 조사가 가장 아쉬웠던 자리 |
| G. 앱 프롬프트 모으기 | 백엔드 prompts/list 를 모아 접두 붙여 낸다 | MaterialTwin 2 · AIDataHub 3 | 프롬프트 인자 · 권한 경계(앱 프롬프트가 쓰기 도구를 시킬 수 있다) | 필요하면 2단계 |
| H. 박스 사이 이름 고정 | 겹침과 무관하게 같은 이름(별칭 꼴)을 노출 | 박스마다 같은 이름 | 지금 이름을 외운 절차 · 허용 규칙 · 클라이언트가 깨진다(게이트웨이 주석의 경고 그대로) | 하지 않는다 — 대신 클라이언트 설정이 별칭을 쓰게 안내 |

정리 — 게이트웨이로 당장 되는 것은 B · D · F 이고 A 는 임시방편이다. 계약의 본체(인자 설명 · enum · 숫자 경계 · 객체 구조 · 표지)는 앱 길목에서
고치는 것이 맞다. 앱 길목이 하나인 곳이 많아 일이 작다 — RA · SignalForge · StepForge · SmartTwin 은 한 함수씩이다.

---

## 10. 근거 파일:행

- 점수판 셈 — `HWAXMcpGateway/gateway.py:1252-1349` (맨 위 인자만 `:1259`, 설명 판정 `:1305-1311`, 단위 · 범위 낱말 `:1272-1281`)
- 접두 · 별칭 — `gateway.py:1430-1485` (별칭 `:1465`, 선언 백엔드 읽기 표지 주입 `:1487-1489`)
- 쓰기 분류 — `gateway.py:3602-3606`(_WRITE_NAME), `:4080-4091`(_tool_is_write), 검색 감점 `:4271-4274`, tools-map write `:12506`
- 루틴 읽기 판정 — `gateway.py:9628-9640`(조회 낱말), `:9733-9760`(_routine_read)
- 감사 원장 — `gateway.py:1060-1100`(_audit, 봉투 사유는 ok 일 때만 `:1095`), isError 사유 없음 `:12220` · `:12301` · `:12325-12329`
- 프롬프트 — `gateway.py:9994-10030`(루틴만)
- 웹 챗 설명 상한 — `HWAXAgentServer/app.py:1756`(CATALOG_DESC_MAX 4,000) · `:1759`(TOOL_DESC_MAX 2,400) · `:2958-2985`(_cap_desc · _slim_tool — 인자 설명도 자른다), `HWAXAgentServer/.env:1`(dev 120)
- SmartTwin 숨은 스키마 — `KooSlurmInstallAutomationRefactory/dashboard/smarttwin_mcp/src/smarttwin_mcp/server.py:234-250`, 카탈로그 `…/smarttwin_mcp/tools/*/*/args.schema.json`(SmartTwinMCP 리포는 「도는 코드가 아니다」 — 커밋 97c0e0b)
- RA 등록 길목 — `ReportArchive/mcp_server/server.py:247-269`
- SignalForge 등록 길목 — `SignalForge/mcp-server/server.py:95-101`
- StepForge 등록 길목 — `StepForge/app/catalog.py:124`, section_pair_view `StepForge/app/mcp_server.py:12929`
- MaterialTwin — `MaterialTwinWeb/backend/mcp_server.py:162`(get_material 정수 id) · `:294`(compare_materials) · `:826-842`(search_catalog_property 오류 봉투)
- 읽기 목록 — `HWAXMcpGateway/read_tools.json`(tools 47 · deny 2 · override 5), 검색 가중치 `search_tuning.json`
