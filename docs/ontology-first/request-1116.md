# 11-16 MCP 온톨로지 먼저 — 게이트웨이 '온톨로지 조회' 도구 OL-1 ~ OL-5

> 운영 박스(cae00) 세션이 쓴 요청서다(작성 2026-11-16, 사용자가 11-17 dev 세션에 붙여 넣음). 답과 한 일은 [PLAN.md](PLAN.md) §12 · [context-notes.md](context-notes.md) OF-32 ~.
> 주소와 실제 이름은 보낸 쪽이 뺐다. 줄 번호는 11-16 운영 박스 판(게이트웨이 `58e392a` · 포털 `feaa4076`)이다.

개인 Claude(MCP)로 HWAX 를 쓸 때 온톨로지를 먼저 쓰게 하려는 요청이다. 지금은 검색 순위 손잡이뿐이라, 질의에 '온톨로지' 라는 말이 들어가면 정본 허브가
20위 밖으로 밀린다. 그래서 게이트웨이에 직접 온톨로지 조회 도구를 하나 두려고 한다. 이 도구가 정본에서 개체를 먼저 풀고, 그 키로 각 앱에서 부를
도구와 인자를 알려 주게 한다.

방향은 `PLAN.md` §1 의 (가) — 코어 타입은 정본 `object_resolve` 가 먼저 · 후보가 여럿이면 고르지 않는다 · 비코어 앱으로 질문을 보내지 않는다.
웹 챗은 바꾸지 않는다(OF-14 ④).

## 한눈에 보기

| 번호 | 어디 | 지금 | 바라는 것 | 급함 |
|---|---|---|---|---|
| OL-1 | 게이트웨이 로컬 도구 | 온톨로지 도구가 앱마다 따로 열 개 남짓이고 키 꼴이 다 다르다. 모델이 이름만 보고 아무거나 고른다 | 로컬 도구 `ontology_lookup` — 정본에서 풀고, 앱별 다음 호출(키를 채운 인자)을 준다 | 높음 |
| OL-2 | `search_tools` | '온톨로지 조회 · 검색' 에서 정본이 20위 밖이다. 낱말 순위라 손잡이로는 못 고친다 | 온톨로지 · 코어 질의에 OL-1 을 첫 줄로. 선택 인자 `object` 로 그 개체를 받는 앱의 도구를 올린다 | 높음 |
| OL-3 | 포털 `core_vocab.json` 의 `ontology` | 앱마다 무슨 키로 찾는지 적힌 곳이 없다 | `ontology.apps.<앱>.lookup` 칸 — 받는 타입 · 도구 · 인자 틀 | 중간 |
| OL-4 | `tool_search_eval/` | 온톨로지 질의 정답쌍이 없다 | 부록 A 의 36쌍을 평가셋에 | 낮음 |
| OL-5 | `search_tuning.json` | 운영 박스가 덧씌우기로 돌린다(3절) | 동의어 둘을 기본값으로 옮길지 정한다 | 질문 |

## 1. 왜 — 11-16 운영 박스에서 잰 것

`tool_search_eval/run.py` 의 `_import_gateway` · `_install` 로 카탈로그 스냅샷(백엔드 도구 1,590 · 로컬 23)을 앉히고 `_search_tools(limit 20)` 를 불렀다.

| 판 | 추적 142 | 코어 30 — 1위 · 5위 안 · MRR | 앱 이름 6 — 1위 · MRR |
|---|---|---|---|
| 기본값(덧씌우기 없음) | 기준 | 0.63 · 0.77 · 0.70 | 0.33 · 0.46 |
| 운영 박스 덧씌우기(3절) | 나빠진 쌍 0 · 좋아진 쌍 2 | 0.63 · 0.83 · 0.72 | 0.83 · 0.84 |

- 코어 낱말 질의는 이미 잘 된다(30 중 19 가 정본 1위 — 어휘표 `search` 넓히기).
- '온톨로지' 라는 말 자체가 약하다 — '온톨로지 조회' 는 기본값 20위 밖(1위 AIDataHub `agent_search`) · '온톨로지 검색' 20위 밖(Report Archive
  `list_saved_searches`) · 'ontology lookup' 8위 · '코어 온톨로지' 10위. '조회' · '검색' 은 도구 수백 개에 들어 낱말 순위로는 정본을 1위로 못 올린다.
- 앱 이름을 불러도 잘 안 맞았다 — 한국어 '온톨로지' 가 영어 도구 이름(`ontology_*` · `onto_*`)에 맞지 않는다. 덧씌우기로 고쳐졌다(6 중 5 가 1위).
- 구조 쪽 원인 — 온톨로지 도구가 앱마다 키 꼴이 다르다(정본 · 형제 허브 `type_slug` + UUID(허브마다 다르고 key 만 같다) · DynaForge `ontology_object`
  `type_slug` + 허브 key · StepForge `onto_*` `"<type>:<key>"` · Report Archive 정수 id · 그 밖 SignalForge · MatNexus `get_ontology` · ARP
  `ontology_status` · ComponentCore `ontology_guide`). 서버 지침은 약 2,031자로 시험 한도 2,048자에 닿아 '온톨로지 먼저' 를 지침으로 가르칠 수 없다.

## 2. 제안 — 게이트웨이가 먼저 풀고, 그 키로 앱 도구를 찾는다

### OL-1 로컬 도구 `ontology_lookup`
- 인자 — `query`(필수) · `type`(선택 — 코어 slug 또는 어휘표 `types` 의 한국어 이름) · `apps`(선택 — `next` 를 좁힌다) · `neighbors`(기본 false) · `limit`(기본 5).
- 차례 — ① 타입 고르기(`type` 이 없으면 어휘표 `types` 이름 · `search` 낱말로 셋까지, LLM 없음 — 없으면 정본 `search(query)`) ② 정본
  `object_resolve(type_slug, name)` — name 은 질의에서 타입 낱말을 뺀 것, exact · candidates · none 을 그대로 ③ exact 면 `{type_slug, key, name, object_id}`
  ④ `next` — OL-3 칸이 있는 앱 가운데 호출자에게 보이고 꺼 두지 않은 것만, 정본 → 형제 → 플랫폼, 비코어는 `role: noncore`, 줄은 `{tool, args, role}`
  ⑤ `neighbors=true` 면 `graph_neighbors(object_id, depth 1)` 를 `ontology.facts` 안으로 접어 ⑥ candidates 면 후보와 `ask_user: true` ⑦ none 이면 시도한 타입.
- 호출 길은 `invoke_tool` 과 같은 길(`_call_tool` → `_call_with_identity`) — 신원 · 그룹 · denied · muted · 감사 · 가림이 그대로. 새 신원 경로 · 토큰 없음.
- 정본이 닿지 않거나 권한이 없으면 `refused` 와 까닭(none 을 내면 '자료가 없다' 로 읽힌다).
- 읽기 전용(`readOnlyHint`) · 루틴 읽기 · 리스크 심사 좌석 목록에는 넣지 않는다(D-18).
- 시험 — tools/list · 세 판정 그대로 · 권한 없으면 refused · 보이지 않는 앱 · 꺼 둔 앱이 next 에서 빠짐 · 서버 지침 길이 시험 그대로.

### OL-2 `search_tools` 와 잇기
- (a) 질의에 '온톨로지' · 'ontology' 가 있거나 어휘표 `search` 낱말이 들면 `ontology_lookup` 을 1위 — 새 스위치(예 `onto_lookup_first`) 기본 끔, 끄면 순위 바이트 동일(E-7).
- (b) 선택 인자 `object`(`"type_slug:key"`) — 그 타입을 받는 앱(OL-3 `lookup.types`)의 도구에 가중치.
- (c) 코어 · 온톨로지 질의 결과에 `hint: "먼저 ontology_lookup 으로 key 를 얻고 next 를 따른다"`.

### OL-3 어휘표 `ontology.apps.<앱>.lookup`
- 꼴 `{"types": [...], "tool": "<원래 이름>", "args": {"type_slug": "{type_slug}", "key": "{key}"}}` — 게이트웨이만 읽고 에이전트 서버는 무시(시험으로 묶는다).
  `entry` 와 따로 두는 까닭 — `entry` 를 채우면 웹 챗 규칙 ⑧ 이 켜진다(OF-14 ④).
- 추적 기본값(확인된 것만) — `failuretrace` · `caegroupdatahub` `object_resolve(type_slug, key)` · DynaForge `ontology_object(type_slug, key)`(11-16 노출 스키마
  `required: [type_slug, key]` · 코어 35 타입 동기) · StepForge `onto_search(q="<type>:<key>", resolve=true)` 또는 `find_plm_task`(질문 1). ARP · MatNexus ·
  Report Archive 는 키 꼴 확인 뒤 박스 덧씌우기로.

### OL-4 평가셋
- 부록 A 36쌍을 `pairs.jsonl` 에 `source: "doc"` 으로. 받아들이는 기준 — '온톨로지' 네 질의(o01 · o02 · o04 · o05)는 `ontology_lookup` 1위 · 코어 30 은 1위
  비율이 0.63 보다 높다(`ontology_lookup` 또는 정본 읽기 도구가 1위면 맞다) · 앱 이름 6 은 1위가 5/6 보다 줄지 않는다 · 추적 142 는 나빠진 쌍 0.

### OL-5 질문 — 동의어 둘을 기본값으로
운영 박스 덧씌우기 동의어(3절)는 추적 142 에서 나빠진 쌍이 없고 앱 이름 질의를 0.33 → 0.83 으로 올렸다. 기본값으로 옮길지 — 권장은 옮긴다.
`noncore_demote` 는 결정 Q-1 대로 박스 몫.

## 3. 운영 박스에서 이미 한 것

11-16 18:4x 에 `search_tuning.local.json` 을 새로 두었다(그전엔 없음). `/health` `search_tuning` — 지문 `1fda07215734`(기본 `ba5d93cc1a9c`) · 덧씌우기
`dad5f432f1a1` · 바뀐 칸 `switches.noncore_demote` · `synonyms.온톨로지` · `synonyms.ontology` · 동의어 81 → 83.

```json
{"switches": {"noncore_demote": true},
 "synonyms": {"온톨로지": {"to": ["ontology", "onto_", "object_resolve", "graph_neighbors", "objects_summary", "코어 정본"]},
              "ontology": {"to": ["object_resolve", "graph_neighbors", "objects_summary", "코어 정본"]}}}
```

'코어 정본' 은 정본 허브 도구 설명 앞 소개 줄이다(정본 도구 115개만 가진다). 되돌리려면 파일을 지운다(재기동 없음). 실제 MCP 확인 — '코어 온톨로지'
정본 `graph_neighbors` · `object_resolve` · `objects_summary` 3 ~ 5위 · 'DynaForge 온톨로지 객체' `ontology_find` 1위 · 'MatNexus 온톨로지' `get_ontology` 1위.

## 4. 질문
1. StepForge 에서 코어 개체를 찾는 키 꼴이 `"<type>:<key>"` 가 맞나 — `onto_search(resolve=true)` 와 `find_plm_task` 가운데 어느 것을 `lookup` 으로 둘까.
2. OL-1 의 타입 고르기를 게이트웨이 코드(어휘표 낱말)로 할지, 허브 `objects_resolve_many` 로 여러 타입을 한 번에 풀지 — 후자가 한 번에 끝나면 그쪽을 권한다.

## 5. 뺀 것
웹 챗(OF-14 ④ — 고정 몫 16개를 `ontology_lookup` 하나로 줄이는 안은 M2 측정 뒤) · 심의 '온톨로지 먼저 보기'(PLAN §5.2) · 서버 지침 늘리기(2,048자 한도).

## 부록 A. 정답쌍 36

`o01` ~ `o30` 의 정답은 정본 `rootdesigndatahub` 의 `object_resolve` · `objects_resolve_many` · `objects_list` · `objects_summary` · `object_get` · `object_fields` ·
`graph_neighbors` · `graph_path` · `search` 다. `o01` · `o02` · `o04` · `o05` 는 `ontology_schema` · `graph_overview` · `core_status` 도 정답. OL-1 이 들어오면
`_gateway:ontology_lookup` 을 모두에 더한다. 순위는 기본값 → 덧씌우기('-' 는 20위 밖).

| id | 질의 | 순위 | id | 질의 | 순위 |
|---|---|---|---|---|---|
| o01 | 온톨로지 조회 | - → 11 | o16 | 시험이 잡는 고장 | 11 → 11 |
| o02 | 온톨로지 검색 | - → - | o17 | 해석이 예측하는 고장 | - → - |
| o03 | 온톨로지에서 과제 찾기 | 1 → 1 | o18 | 프로젝트 과제 목록 | 1 → 1 |
| o04 | ontology lookup | 8 → 6 | o19 | PLM 과제 찾기 | 2 → 2 |
| o05 | 코어 온톨로지 | 10 → 3 | o20 | 개발모델 코드로 과제 조회 | 1 → 1 |
| o06 | 과제 코드로 개발모델 찾기 | 1 → 1 | o21 | 고장모드 검색 | 1 → 1 |
| o07 | 이 과제의 고장모드 목록 | 1 → 1 | o22 | failure mode lookup | 1 → 1 |
| o08 | 고장모드와 연결된 시험항목 | 1 → 1 | o23 | test item for failure mode | 1 → 1 |
| o09 | 시험항목 관리 기준 | 1 → 1 | o24 | 과제 관계 그래프 | 1 → 1 |
| o10 | 가상검증 항목 찾기 | 1 → 1 | o25 | 시험군별 시험항목 | 6 → 3 |
| o11 | 관리기준 조회 | 1 → 1 | o26 | 모델코드 조회 | 1 → 1 |
| o12 | 물성 영률 값 | 1 → 1 | o27 | 고장모드별 대책 | 1 → 1 |
| o13 | 전작 모델 찾기 | 3 → 2 | o28 | 부품 고장 원인 메커니즘 | 5 → 5 |
| o14 | 후속 모델 과제 | 1 → 1 | o29 | 부하 조건 관리 기준 | 1 → 1 |
| o15 | 부품에서 나는 고장모드 | 1 → 1 | o30 | 개념 관계 이웃 조회 | 2 → 2 |

| id | 질의 | 순위 | 정답 |
|---|---|---|---|
| c01 | StepForge 온톨로지 검색 | 1 → 1 | `heax-step_forge:onto_search` · `onto_neighbors` · `ontology_model` · `onto_overview` · `onto_object` |
| c02 | DynaForge 온톨로지 객체 | 4 → 1 | `heax-kooremapper_mcp:ontology_find` · `ontology_object` · `ontology_types` |
| c03 | SignalForge 온톨로지 | 2 → 1 | `signalforge:get_ontology` · `get_kg_relations` |
| c04 | MatNexus 온톨로지 | - → 1 | `matnexus:get_ontology` |
| c05 | Report Archive 온톨로지 질문 | - → 16 | `reportarchive:ask_ontology` · `search_objects` |
| c06 | ComponentCore 온톨로지 가이드 | 1 → 1 | `componentcore:ontology_guide` · `object_resolve` |

`o16` · `o17` 은 관계 낱말이 어휘표 `relations` 에는 있지만 `search` 낱말에는 없어 낮다.

## 부록 B. 다시 재는 방법

운영 박스에 평가 파일을 남겼다(`~/portal-backups/onto-search-eval-20261116/` — `ev.py` · `ev3.py` · `onto_pairs.jsonl` · 카탈로그 스냅샷).

```bash
PY=../HWAXAgentServer/.venv/bin/python
$PY tool_search_eval/run.py snapshot --gateway http://127.0.0.1:9110 --config gateway_config.json --out /tmp/tse/catalog.json
$PY /tmp/tse/ev3.py
```
