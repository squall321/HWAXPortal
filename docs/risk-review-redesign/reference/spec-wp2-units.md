# WP2 설계서 — 변경 묶음(검토 단위) + 전원 포함

작성 2026-10-09. 대조한 코드는 dev HEAD — HWAXRisk `7248651` · HWAXAgentServer `7683125` 이다(cae00 배포판과 같은지는 확인하지 못했다).
리포 경로는 전부 리포 루트 기준 상대경로로 적는다(예 `HWAXRisk/backend/app/diff.py`). 줄 번호는 위 HEAD 기준이다.

---

## 1. 목적과 범위

### 하는 것

1. **검토 단위 생성기.** 타깃 하나(diff 또는 snap)의 변경·현황 항목 전부를 빠짐없이 '검토 단위' 로 나눈다. 원천은 `rr_diff_events` 가 아니라 `rr_diffs.diff_json` 의 구조·파라메트릭·의미 세 층이다. 결정론(같은 입력이면 같은 단위 id)이고 불변식(미배정 0 · 소유 겹침 0)을 코드가 검사한다.
2. **전량 요약과 단위 시그니처.** 단위마다 잘라내지 않는 줄 단위 정규 표기(부품 실명·before/after·단위·부호)와, 변경 종류·부품 역할·재질·계면 종류를 담은 시그니처를 만든다.
3. **근거 꾸러미.** 단위마다 코드가 한 번 조립해 동결한다. 스냅샷 캡처가 이미 동결한 지정 도구 응답(IR)에서 그 단위 부품만 발췌하고, 캡처에 없던 도구(`compare_reports`·재질 조회)만 결정적 인자로 실호출한다.
4. **변경→영역 신호.** 결정적 신호 여럿을 계산해 (단위 × 전문가)마다 `hit | blind | miss` 를 낸다. 신호는 포함만 시키고 제외는 못 한다.
5. **전원 포함.** 새 흐름 타깃에서는 로스터 동결 때 `deferred` 를 만들지 않는다. 회로 6개 영역 104명과 Tier 밖 전문가가 전부 흐름에 들어온다. 입력 결손(ECAD 부재)은 좌석을 빼는 사유가 아니라 질문을 바꾸는 사유가 된다. Tier A/B/C 는 범위가 아니라 도는 순서다.
6. **패널 연결.** WP4 의 쟁점 패널이 단위별 질문·근거를 받도록 `runner.panel_question`·`build_delib_opts` 가 unit 을 받는 형태와 단위 발췌 함수를 정한다.
7. **새 표** `rr_unit_builds`·`rr_units` 의 DDL·인덱스·상한.

### 하지 않는 것

- 전문가 호출(전수 훑기·카드 대조)과 셀 원장 `rr_review_cells` 는 WP3 이다. 이 꾸러미는 셀이 읽을 것(단위·신호·꾸러미·입력 결손)과 호출 순서만 준다.
- 쟁점 선정·교차 셀·메커니즘 셀·완결 판정(`close_level`)·보고서는 WP4 다. 이 꾸러미는 재료(단위 사이 연결·시그니처·제외 회계)만 준다.
- 지금 브리프의 결함(E3·E4 경로, E2 부호 정렬, 질문 200자)은 WP1 이다. 이 꾸러미는 그 수리에 기대지 않는다(단위는 `diff_json` 을 직접 읽는다).
- diff 재계산·tol 해시 읽기·cid 공식 변경은 하지 않는다(발견한 결함은 9절과 반환값 dependencies 에 적었다).
- `frontend/` 는 건드리지 않는다. 백엔드 응답 필드까지만 정한다.
- 심의 엔진(HWAXAgentServer)·포털·게이트웨이·AIDataHub 코드는 이 꾸러미에서 고치지 않는다.

---

## 2. 지금 코드

직접 열어 확인한 것만 적는다. 입력 자료와 다르거나 입력 자료에 없던 것은 **[바로잡음]**·**[새로 확인]** 으로 표시했다.

### 2.1 변경 항목이 사는 곳과 새는 곳 — `HWAXRisk/backend/app/diff.py`

| 줄 | 지금 동작 | 이 설계에 주는 뜻 |
|---|---|---|
| 1743~1753 `_event_rows` | `rr_diff_events` 에는 `layer='semantic'` 행만 쓴다. 구조·파라메트릭 항목은 `rr_diffs.diff_json` 안에만 있다. | 단위의 원천은 `diff_json` 이다. |
| 996~1006 `_parametric` | 대응된 노드마다 속성 17종을 전부 항목으로 만든다(양쪽 다 None 인 것만 뺀다). 대부분 `flag='noise'` 다. | '변경 항목' 의 정의가 필요하다(3.4.1). |
| 1362~1378 | `part.thickness_changed` 는 `min_dim` 한 항목만 `derived_from` 으로 건다. `elif` 라서 같은 부품의 bbox·volume 변화는 이벤트가 없다. | **[새로 확인]** 픽스처 `pair_thick` 를 메모리에서 돌리면 변경 파라미터 5건(min_dim·bbox_dz·centroid_world_z·bbox_world_dz·volume) 중 이벤트로 이어진 것은 1건이다. 합성 640부품·변형 300건에서는 변경 파라미터 307건 중 159건이 어느 이벤트에도 걸리지 않았다(volume 78·bbox 78·centroid 3). 부피 −16.7% 같은 변화가 지금은 좌석 누구에게도 가지 않는다. |
| 1425~1428 `edge_codes` | 계면 파라미터 중 `min_gap`·`contact_area_est`·`penetration_depth`·`fs` 만 이벤트가 된다. | **[새로 확인]** `band_width`·`penetration_volume` 변화는 이벤트가 없다. |
| 1336~1339 | 한 노드의 속성 중 하나라도 `excluded_reason` 이 있으면 그 노드의 이벤트를 전부 건너뛴다. `_param_item`(425~426)은 한쪽이 None 이면 `excluded_reason='null_one_side'` 를 붙인다. | **[새로 확인]** 속성 하나가 한쪽에서만 미측정이면 그 부품의 두께·이동·재질 이벤트가 통째로 사라진다. 파라메트릭 항목은 `changed` 로 남는다. |
| 1241~1243, 534 | G2 실패(same-as `pending_n > 0` 포함)면 의미 이벤트 0건이다. | 구조·파라메트릭층은 온전하다. 단위는 그 두 층으로 선다. |
| 1536~1546 | `capture_parity` 가 깨지면 파라메트릭 전 항목과 `edge_changes` 에 `excluded_reason='capture_partial'` 을 붙이고 이벤트를 비운다. | 남는 활성 항목은 `node_changes` 뿐이다. |
| 1698~1703 | 같은 (base, target) 쌍이 있으면 저장된 diff 를 그대로 돌려준다. | **[새로 확인]** `rr_diffs` 를 UPDATE·DELETE 하는 SQL 은 앱 전체에 0건이다(grep). 사람이 same-as 를 확정해도 그 diff 는 다시 계산되지 않는다. G2 로 막힌 diff 는 영구히 이벤트 0건이다. |
| 1182~1211 `_rollup_delta` | 조립 접두마다(깊이 1..max) 행을 만든다. 변했는지 표시(flag)가 없다. | 변한 행은 before≠after 로 가려야 한다. 깊은 접두의 변화는 조상 접두 행에도 겹쳐 나온다. |
| 1118~1141 `_dims_delta` | 명명 치수 전부를 항목으로 만든다. 양쪽 다 None 이어도 `null_one_side` 다. | 양쪽 None 은 변경이 아니다. |
| 729~740 | `moved_in_tree` 는 같은 dict 를 `node_changes` 와 `hierarchy_moves` 에 둘 다 넣는다. | cid 가 두 버킷에 겹친다. 중복 제거가 필요하다. |
| 73~76 `cid_for`, 1001 | 노드 파라메트릭 cid = `sha1('parametric'|'node'|dn||attr)`. dn 은 대표 노드다. | **[새로 확인 · 결함]** dyna pid 가 mcad 부품과 같은 dn 으로 묶이면(브리지) 두 노드의 같은 이름 속성이 **같은 cid** 를 받는다. 픽스처의 dyna pid 1 을 PLATE_1 에 묶어 돌리니 `c:c51c68b0e737` 이 두 번 나왔다(dyna `3000→3000 noise`, mcad `3000→2500 changed`). 1333~1335 의 `by_dn[dn][attr] = item` 도 뒤 항목이 앞 항목을 덮는다. 지금은 브리지가 0행이라(cad-capabilities.md:50) 드러나지 않는다. |
| 31~34, 1534, 1540 | `EXCLUDED_REASONS` 는 10종인데 코드는 그 밖의 `source_drift`·`capture_partial` 도 붙인다. `unit_scale`·`suspect_coords`·`sameas_pending`·`bridge_stale` 을 붙이는 곳은 없다. | 사유 어휘를 닫힌 집합으로 믿으면 안 된다(모르는 사유는 '검토에 싣는다' 쪽으로 떨어뜨린다). |
| 472~484 `_neighborhood` | 1홉 이웃은 iface·contact 중 clearance 를 뺀 것이다. | 비접촉 근접(clearance)은 이웃이 아니다. 문맥에는 따로 싣는다. |
| 602~640 `changed_ckeys` | `excluded_reason` 항목과 `design_relevant=false` 를 뺀 ckey 집합. | 승계(carried) 판정의 입력이다. 이 설계는 건드리지 않는다. |

### 2.2 인용 검증 — `HWAXRisk/backend/app/narrative.py`

- 339~362 `SpecContext.diff_item` 은 세 층 어디에 있든 cid 로 항목을 찾는다. 단위 줄에 `[c:…]` 를 달면 지금 인용 검증을 그대로 탄다. **[새로 확인]** 다만 `structural` 아래에서 리스트인 버킷만 훑어서 `structural.dyna.scope_changed`(dict 안의 리스트) 항목은 찾지 못한다.
- 502~506 `[c:]` 의 정규 표기는 항목의 `text` 다. 719 `quote not in canonical` 은 정확 부분문자열 대조다. 계면 항목의 `text` 는 부품명이 아니라 `p:해시↔p:해시` 다(diff.py:875, 1071). 단위 줄에 실명을 쓰면 전문가가 그 줄에서 옮긴 인용문이 불일치로 떨어진다. 대조 후보에 단위 줄을 더해야 한다(3.6.4).
- 644~650 `card:` 인용은 `external_check` 가 없어 미검증 통과다(WP3 몫).

### 2.3 로스터·보류 — `planner.py`·`routes.py`·`registry.py`

- `planner.py:143~145` ECAD 의존 도메인이고 `ecad_absent` 이며 `rank != 1` 이면 처음부터 `deferred(reason='ecad_absent')` 다. `:56` `deferred` 의 허용 전이는 빈 집합이다. `tests/test_planner.py:522~524`·`:553` 이 이 두 사실을 못 박고 있다.
- `planner.py:168~213 refresh_roster` 는 새로 붙는 좌석을 ECAD 여부와 무관하게 `pending` 으로 넣는다(200행). 동결 때와 규칙이 다르다. **[새로 확인]**
- `routes.py:1883` `missing_json` 에 값이 없으면 `ecad_absent=True` 로 본다. `routes.py:2049` 가 그 값을 `freeze_roster` 에 넘긴다. `adapters/ecad_stub.py` 는 스텁이라 실제로 늘 True 다.
- `config.py:43` `_DEFAULT_MCAD_DOMAINS` 와 `Settings.risk_mcad_domains` 는 있으나 planner 에 소비처가 없다(grep). plan.md:3392 의 'MCAD 부재 deferred' 와 plan.md:3451 의 'material 좌석 deferred' 는 구현돼 있지 않다.
- `planner.py:230~238` Tier 는 `rank_in_domain` 상한이다(A=1, B=ceil(0.3·크기), C=전원). `:371~382 _queues` 가 그 상한 안의 pending 만 큐에 넣으므로 Tier 는 범위다.
- `registry.py:937~945` C1 은 deferred 를 종결로 세고 Tier A 패널 done 3건을 요구한다. `:954~957` C2 의 need 는 deferred 를 뺀 활성 좌석 기준이다(WP4 가 고친다).
- `roster.py:20~21, 151, 175` 관련도는 `summary_text` 앞 500자로 `recommend_agents(top_k=60)` 을 한 번 부른 `score` 이고 목록 밖은 0 이다. `desc_match`·`matched_sections` 는 응답에 오지만 읽지 않는다.

### 2.4 패널 페이로드 — `runner.py`·`brief.py`

- `runner.py:337~378 panel_question(store, target_key)` 는 타깃만 받는다. 요약은 `summary_text[:200]`(358행)이라 `[대상]` 머리줄뿐이다.
- `runner.py:398~460 build_delib_opts` 는 `narrative.prior_evidence`(E0~E9)를 받아 E0c 를 끼우고(427행) 12칸에 맞춘다(381~395). `apps` 는 어댑터 앱 둘뿐이다(302~310, `adapters/registry.py:26~30`).
- `brief.py:28~31 CAPS` 에서 변경 칸은 E1 1650·E2 1100·E3 700·E4 600 이다. `brief.py:498` E2 는 이벤트 글 전체를 `_q(text, 'note')` 로 «…» 에 넣는다(`render.SANITIZE_LIMITS['note']=300`).
- `render.py:53~73` 판단어 린터 17종. 브리프는 `strict_lint=True` 로 조립한다(`narrative.py:1434~1436`). 코드가 만드는 단위 줄도 이 린터를 통과해야 한다('위험'·'리스크'·'개선'·'문제'·'부족'·'실패'·'결함'·'판단'·'평가' 등을 쓰면 안 된다).

### 2.5 지정 도구와 캡처 — **[바로잡음]**

과제문은 '지정 도구(list_interfaces·interface_graph·report_part_risk·compare_reports 등)를 코드가 단위마다 한 번 돌려 동결' 이라고 적었다. 코드를 보면 그 도구들 대부분은 **스냅샷 캡처 때 이미 불려 응답이 동결돼 있다.**

- `adapters/mcad.py:479~501` 캡처는 REST `/interfaces`(limit 5000) 또는 MCP `list_interfaces`(kind 4종)와 `interface_graph` 를 부른다. 결과가 `rr_ir_edges`·`rr_ir_nodes`·`ir_json` 이고 원문은 `rr_snapshot_calls.response_gz` 다.
- `adapters/dyna.py:187~250` 캡처는 `report_summary`·`report_part_risk`·`report_findings`·`report_worst_cases`·`report_energy_flow` 를 부른다. 결과가 `ir_json.results` 다.
- 캡처에 없는 것은 `compare_reports` 와 재질 도구(`get_material`·`compare_materials`)다.
- 지금 패널에서는 엔진이 지정 도구의 인자를 LLM 에게 짜게 한다(`HWAXAgentServer/deliberation.py:3896~3917`). 그리고 그 호출은 소스의 **지금** 상태를 읽는다. 같은 과제의 리비전 비교에서는 base 상태가 소스에 더는 없다.
- 실제 도구 시그니처는 `list_interfaces(project_id, kind='', limit=100, part='')`(`StepForge/app/mcp_server.py:2180`, `part` 는 이름·경로 글롭), `interface_graph(project_id, fmt='mermaid', limit=120)`(같은 파일 16277), `report_part_risk(report_id, part_id=None)`·`compare_reports(report_ids, part_id=None)`(`KooRemapper/.../platform/mcp_server/server.py:517, 720` — 빌드 작업본에서 확인) 이다. 인자를 코드가 결정적으로 만들 수 있다.

그래서 꾸러미는 두 층으로 설계한다(3.8). 동결본 발췌가 기본이고 실호출은 캡처에 없던 도구로 한정한다.

### 2.6 snap 타깃의 재료 — `state.py`

- `state.py:53 _TOP_K = 10`. `top.interference`·`top.tight_clearance`·`top.thin_parts` 등은 상위 10건만 담는다(445~473). **[새로 확인]** signals 만으로 단위를 만들면 11번째 간섭부터 빠진다. 전수는 IR(`rr_ir_edges`·`rr_ir_nodes`)에서 다시 세어야 한다.
- `state.py:873~991 evaluate_rules` 의 `found.refs` 는 적중 전부다(자르지 않는다).

### 2.7 신호의 재료

- `ir_builder.py:64~77 SEED_SYNONYMS` 는 별칭 → 정규 머리 토큰(pcb·battery·display·housing·bracket·tape·screw·frame·shield_can·fpcb) 표다. `name_norm_canon`(165~205)이 이미 적용한다. `rr_ir_nodes` 에는 `name`·`name_norm`·`asm_key`·`material_norm` 열이 있다(`risk_store.py:127~132`). `name_norm_canon` 열은 없다.
- `assets/taxonomy.v1.json` 메커니즘 38종의 `default_tools` 와 `assets/seat-contract.v1.json` 의 `table`(도메인별 required·recommended 도구)을 잇는 코드는 없다.
- `AIDataHub/api_server/src/api/services/recommend_svc.py:277~290` `desc_match` 는 질의 토큰이 전문가 프로필(name·description·common_tags·data_types)에 부분일치하는 비율이다(임베딩이 아니다). `:338~347` 은 `score`(e5 코사인 항 포함)로는 판정할 수 없다고 스스로 적는다. `recommend_agents(q, top_k)` 는 `ranked[:top_k]` 로만 자른다(348행 — 코드상 상한 없음).
- `mcp_runtime.py:820~836 fts_search(q, top_k, agent_type)` 는 좌석 범위를 SQL 로 건다. `search_svc.py:171~175` 는 `websearch_to_tsquery('simple')` AND 매칭이 0건이면 토큰 OR 로 한 번 더 찾는다.
- `mcp_runtime.py:776 hybrid_search` 는 의미 검색을 섞으므로 좌석에 문서가 있으면 무엇을 물어도 top_k 가 돌아온다. 적중 건수는 포함 신호로 쓸 수 없다.

### 2.8 살림

- `risk_store.py:561~562` 마이그레이션은 버전 오름차순이고 허용 연산은 CREATE TABLE·ADD COLUMN·CREATE INDEX 다. `:627~629` 는 현재 버전보다 높은 버전만 적용한다. **이미 적용된 버전 블록에 문장을 덧붙이면 그 DB 에는 영영 적용되지 않는다.**
- 새 표는 `export.py:43~75 _SINCE_COLS`, `routes.py:762~779 TRANSFER_DERIVED`, `routes.py:962~978 PURGE_BLANK_SQL` 에 등록해야 하고 `tests/test_store.py:74, 91` 과 `tests/test_mcp_tools.py:14~29` 의 고정값을 같이 고쳐야 한다.
- 외부 도구 원문 원장은 `rr_brief_calls`(v2)와 `field_source.FieldSource`(같은 인자 24시간 재사용, 실패는 성공 행을 덮지 않는다)가 이미 있다.

---

## 3. 설계

### 3.1 낱말과 전체 흐름

| 낱말 | 뜻 |
|---|---|
| 항목(item) | `diff_json` 의 구조·파라메트릭·의미 층에 있는 cid 하나(중복 제거 뒤). snap 은 IR 의 부품·계면·규칙 적중·경고·명명 치수 하나. |
| 변경 줄 | 단위 요약에 실리는 항목 한 줄. 단위 크기의 단위다. |
| 원자(atom) | 쪼개지지 않는 묶음. 부품 원자(한 부품에만 걸린 항목 전부)와 쌍 원자(같은 두 부품에 걸린 항목 전부). |
| 검토 단위(unit) | 원자를 모은 것. kind ∈ `bundle`(묶음) · `boundary`(경계) · `global`(전역) · `excluded`(제외) · `snap_unit`(현황). |
| 소유 / 문맥 | 항목은 단위 하나만 **소유**한다. 다른 단위에는 **문맥** 줄로 다시 보일 수 있다(셈에 넣지 않는다). |
| 빌드 | 타깃 하나의 단위 생성 1회. `rr_unit_builds` 한 행. |

```
POST /targets ──▶ units.build_units ──▶ rr_unit_builds · rr_units      (순수 계산 + 한 트랜잭션, 네트워크 없음)
        │              └─ roster 질의문(units.roster_query) ─▶ freeze_roster(defer_absent=False)
        ▼
잡 시작(WP3 review_loop 또는 수동) ─▶ unit_evidence.ensure      (동결본 발췌 + 실호출, 러너 자격)
                                 ─▶ unit_signals.compute   (영역 신호 — 표·어휘는 코드, 어휘 일치는 게이트웨이)
        ▼
WP3: units.load_units / units.manifest_items / units.review_payload / unit_signals.for_cell / planner.review_order
WP4: units.panel_evidence / runner.panel_question(unit=…) / rr_units.context_json.links
```

### 3.2 스키마

새 표 둘과 기존 표의 열 하나다. `rr_units` 는 WP5a 의 v3 통합 초안에 있는 열 이름을 그대로 쓰고(`cids_json`·`unit_hash`·`summary_*`·`evidence_*`), 이 설계에 더 필요한 열에 `[wp2+]` 를 달았다. 어휘는 WP5a 방침대로 CHECK 로 묶지 않고 코드가 지킨다(값은 주석에 적었다).

```sql
-- [wp2+] 타깃별 검토 단위 빌드(머리 행). rev 는 1부터 오른다. 타깃당 활성 빌드는 1건이다.
CREATE TABLE IF NOT EXISTS rr_unit_builds (
  target_key TEXT NOT NULL, rev INTEGER NOT NULL, owner_sub TEXT NOT NULL,
  status TEXT NOT NULL,                         -- ok | empty | oversize | failed
  active INTEGER NOT NULL DEFAULT 1,
  builder_version TEXT NOT NULL,                -- 'units-1.0' — 묶는 알고리즘의 판
  input_hash TEXT NOT NULL,                     -- sha256(원천 해시|builder_version|상한)[:16]. 같으면 재빌드는 아무것도 하지 않는다
  source_hash TEXT NOT NULL,                    -- diff: rr_diffs.diff_hash · snap: ir_hash + rule_hits payload_hash 들의 해시
  mode TEXT NOT NULL,                           -- single | bundles | snap
  caps_json TEXT NOT NULL,                      -- 이 빌드에 쓴 상한과 그 출처 {target_lines, max_lines, max_chars, evidence_max_chars, units_max, small_lines, limits_rev}
  blocked_by TEXT,                              -- 의미층 차단 'G2' | 'capture_partial' | NULL
  stats_json TEXT NOT NULL,                     -- 회계(3.4.7)
  invariants_json TEXT NOT NULL,                -- {U1_unassigned, U2_double_owned, U3_oversize[], U4_lint, U5_clipped}
  error TEXT, built_by TEXT, built_at INTEGER NOT NULL,
  PRIMARY KEY(target_key, rev));
CREATE UNIQUE INDEX IF NOT EXISTS ux_rr_unit_builds_active ON rr_unit_builds(target_key) WHERE active = 1;

CREATE TABLE IF NOT EXISTS rr_units (                         -- 검토 단위. diff = 변경 묶음 · snap = (조립 단위 × 신호군)
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL,            -- unit_id 는 내용에서 유도한 결정적 값
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  rev_first INTEGER NOT NULL DEFAULT 1, rev_last INTEGER NOT NULL DEFAULT 1,   -- [wp2+] 살아 있던 빌드 구간. 활성 = rev_last 가 활성 빌드의 rev
  seq INTEGER NOT NULL, kind TEXT NOT NULL,                   -- bundle | boundary | global | excluded | snap_unit. seq 는 표시 순번(식별자가 아니다)
  reviewable INTEGER NOT NULL DEFAULT 1,                      -- [wp2+] 0 이면 셀을 만들지 않는다(제외 단위)
  scope_key TEXT, split_from TEXT, semantic_blocked TEXT,     -- [wp2+] 범위 키 · 쪼개 나온 원래 범위 · 'G2'|'capture_partial'|NULL
  title TEXT, digest TEXT,                                    -- [wp2+] digest = 단위 목록 항목의 글(전수 훑기용, ≤ manifest_item_max)
  signature_json TEXT, sig_hash TEXT,                         -- [wp2+] sig_hash — 시그니처의 sha256[:16]
  unit_hash TEXT NOT NULL,                                    -- sha256(시그니처·소유 참조·요약)[:16] — 값이 바뀌면 달라진다. 셀 재사용 키의 반쪽
  cids_json TEXT NOT NULL, n_changes INTEGER NOT NULL DEFAULT 0,   -- 소유 참조(정렬). diff 는 'c:…', snap 은 'e:…'·'p:…'·'rule:…'·'d:…'·'warn:…'·'req:…'. n_changes = 변경 줄 수
  n_parts INTEGER, context_json TEXT, flags_json TEXT,        -- [wp2+] 문맥(이웃·연결·다른 단위 소유 줄) · 표지
  lines_gz BLOB,                                              -- [wp2+] 줄 구조 전량 [{ref, text, …}](canonical_json gzip)
  summary_gz BLOB, summary_sha TEXT, summary_chars INTEGER,   -- 전량 요약(잘림 0)
  evidence_gz BLOB, evidence_sha TEXT, evidence_chars INTEGER,-- 근거 꾸러미
  evidence_status TEXT,                                       -- NULL(아직) | ok | partial | failed | none(제외 단위)
  evidence_gaps_json TEXT,                                    -- 못 돌린 도구와 사유 [{tool, code, note}]
  evidence_json TEXT, evidence_frozen_at INTEGER,             -- [wp2+] 머리(자격·호출 id·생략한 참조)와 동결 시각
  signals_json TEXT, signals_status TEXT,                     -- [wp2+] 영역 신호(3.9.4) · NULL(아직) | ok | partial
  builder_version TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id));
CREATE INDEX IF NOT EXISTS ix_rr_units_seq ON rr_units(target_key, seq);
CREATE INDEX IF NOT EXISTS ix_rr_units_hash ON rr_units(unit_hash);    -- [wp2+]
CREATE INDEX IF NOT EXISTS ix_rr_units_sig ON rr_units(sig_hash);      -- [wp2+]

ALTER TABLE rr_roster ADD COLUMN input_gaps_json TEXT;        -- [wp2+] 로스터 동결 때의 입력 결손 ['ecad_absent','mcad_absent'] — 없으면 NULL
-- rr_targets.flow 는 WP4 초안이 더한다(TEXT NOT NULL DEFAULT 'panels', 값 panels | cells). 그 열을 같이 쓴다 — 두 번 더하지 않는다.
```

- '근거 꾸러미' 의 열 이름은 `evidence_*` 다. `pack_*` 라고 부르지 않는다 — WP3b 가 `pack_hash` 를 전문가 **카드 묶음**(`rr_card_packs`)의 키로 쓰고 있어 섞인다.
- 역색인 표(항목 → 단위)는 두지 않는다. 단위 수가 수십이라 `cids_json` 을 읽어 메모리에서 만든다(`units.ref_index`). 불변식은 빌드 때 파이썬이 검사해 `invariants_json` 에 남긴다.
- 실호출 원문은 새 표를 만들지 않고 `rr_brief_calls` 를 쓴다(구조가 같다 — 타깃 단위·도구·인자 해시·원문 gzip).
- 마이그레이션 번호. WP5a 는 재설계 표 전부를 v3 한 블록으로 넣자고 한다. 그 블록이 나가기 전이면 위 열을 거기에 넣고, 이미 나갔으면 v4 로 더한다(`CREATE TABLE rr_unit_builds` + `ADD COLUMN`). 지킬 것은 하나다 — 이미 적용된 블록에 문장을 덧붙이지 않는다(2.8).
- 등록할 곳. `export._SINCE_COLS` 에 `rr_unit_builds: ('built_at',)`·`rr_units: ('updated_at','created_at')`. `routes.TRANSFER_DERIVED` 에 두 표(target_key 경유). `routes.PURGE_BLANK_SQL` 에 `rr_units` 의 원문 열(`summary_gz`·`lines_gz`·`evidence_gz`·`context_json` 은 NULL, `title`·`digest` 는 빈 문자열, `signature_json` 은 `'{}'`).

### 3.3 모듈과 함수

새 파일 셋(`units.py`·`unit_evidence.py`·`unit_signals.py`)과 자산 셋이다. 전부 `HWAXRisk/backend/app/`.

```python
# units.py — 타깃의 변경·현황 항목을 검토 단위로 나누고 전량 요약·시그니처를 만든다(결정론, LLM·네트워크 없음)
UNITS_VERSION = "units-1.0"

@dataclass(frozen=True)
class UnitCaps:
    target_lines: int = 20        # 형제 조립을 채워 넣는 목표 크기
    max_lines: int = 40           # 단위 하나의 변경 줄 상한
    max_chars: int = 7000         # 단위 요약 글자 상한(렌더 실측)
    evidence_max_chars: int = 4500   # 근거 꾸러미 글자 상한
    units_max: int = 60           # 검토 대상 단위 수의 경고선(넘으면 status='oversize')
    small_lines: int = 15         # 이 이하면 단위 하나로 낸다
    snap_max_lines: int = 70      # snap 단위의 줄 상한(표 행이라 줄이 짧다)
    snap_tight_gap_mm: float = 0.2
    digest_max: int = 780         # 단위 목록 항목 글 상한(WP3a manifest_item_max 800 − 여유)

def caps_from_settings(settings=None) -> UnitCaps: ...
def caps_for_limits(limits: Mapping, base: UnitCaps | None = None) -> UnitCaps: ...   # WP3a GET /card-review/limits 응답에서 유도(3.13)
def unit_size(unit: Mapping) -> int: ...                              # WP3a 의 단위 크기 식 그대로(lines + evidence + 머리)

# --- 순수 함수(시험이 DB 없이 부른다)
def collect_diff_items(diff_obj: Mapping) -> list[dict]: ...          # 3.4.1 — 세 층을 정규화 항목으로
def walk_cids(diff_obj: Mapping) -> dict[str, list[str]]: ...         # 독립 순회 — cid → [버킷 경로]. 불변식 U1 의 기준(수집 코드와 로직을 공유하지 않는다)
def partition(atoms, pairs, anchored, asm_of: Callable[[str], str], caps: UnitCaps, *, max_lines: int) -> list[dict]: ...   # 3.4.3 — diff·snap 공용
def build_diff_units(diff_obj, node_info: Mapping[str, Mapping], neighbors: Mapping[str, list], *,
                     caps: UnitCaps, roles: Mapping, routing: Mapping) -> dict: ...
def build_snap_units(ir: Mapping, state: Mapping, *, caps: UnitCaps, roles: Mapping) -> dict: ...
def render_unit(unit: Mapping, *, seq: int, total: int) -> str: ...   # 3.6 — 린터 통과가 보장되는 전량 요약(줄 구조의 렌더)
def digest_of(unit: Mapping, *, max_chars: int) -> str: ...            # 3.7.1 — 단위 목록 항목의 글
def signature_of(unit: Mapping) -> dict: ...                          # 3.7

# --- 저장·조회
def compute(store, kind: str, ref_id: str, *, owner_sub: str, settings=None) -> dict: ...   # diff·IR·상태를 읽어 빌드 결과를 만든다(쓰지 않는다 — 타깃 행이 생기기 전에도 부를 수 있다)
def persist(store, target_key: str, owner_sub: str, built: Mapping, *, built_by: str | None = None,
            force: bool = False, reason: str | None = None) -> dict: ...                  # 한 트랜잭션으로 rr_unit_builds·rr_units 에 쓴다
def build_units(store, target_key: str, *, force: bool = False, reason: str | None = None,
                built_by: str | None = None, settings=None) -> dict: ...                  # compute + persist(이미 있는 타깃용)
def manifest(store, target_key: str, *, owner_sub: str | None = None) -> dict: ...
def get_unit(store, target_key: str, unit_id: str, part: str = "summary", *, owner_sub: str | None = None) -> dict: ...   # part ∈ summary|lines|signature|signals|evidence|evidence_full
def ref_index(store, target_key: str) -> dict[str, str]: ...          # 참조 → 소유 unit_id(활성 빌드)
def line_index(store, target_key: str) -> dict[str, tuple[str, ...]]: ...   # 참조 → 단위 줄(인용 대조 후보, 3.6.4)
def load_units(store, target_key: str, *, kinds: Sequence[str] | None = None, reviewable_only: bool = True) -> list[dict]: ...   # WP3b·WP4 가 읽는 단위 목록(3.10.4 의 모양). list_units 는 같은 함수의 별칭
def manifest_items(store, target_key: str) -> list[dict]: ...       # WP3 전수 훑기용 [{unit_id, kind, title, text}] — text = digest
def part_roles(store, target_key: str, unit_id: str) -> dict[str, str | None]: ...   # 부품(대표 노드) → 역할
def unit_domains(store, target_key: str, unit_id: str) -> dict[str, list[str]]: ...   # 영역 → 그 영역을 부른 신호들(3.9)
def review_payload(store, target_key: str, unit_id: str, agent_key: str) -> dict: ...   # WP3 카드 대조용(3.10.4)
def panel_evidence(store, target_key: str, unit_id: str, *, refs: Sequence[str] | None = None,
                   budget_chars: int = 6000, item_max: int | None = None) -> dict: ...   # WP4 패널용(3.11)
def roster_query(store, target_key: str, *, max_phrases: int = 6) -> list[str]: ...   # 로스터 순위·신호 질의 구절
def check_invariants(store, target_key: str) -> list[str]: ...

# unit_evidence.py — 단위별 근거 꾸러미(동결본 발췌 + 결정적 실호출)를 조립해 동결한다
def plan_calls(store, target_key: str, unit: Mapping) -> list[dict]: ...          # [{tool, args, scope: 'target'|'unit'}]
def render_frozen(ir_base: Mapping | None, ir_target: Mapping, unit: Mapping, caps) -> tuple[str, dict]: ...
def ensure(store, settings, target_key: str, *, credential_sub: str | None = None,
           deadline_s: float | None = None, only: Sequence[str] | None = None) -> dict: ...

# unit_signals.py — 변경→영역 신호(포함만 시킨다). 절대 점수 임계를 쓰지 않는다
def domain_signals(unit: Mapping, *, roles, routing, taxonomy, seat_contract, priors) -> dict: ...
def compute(store, settings, target_key: str, *, credential_sub: str | None = None) -> dict: ...
def for_cell(store, target_key: str, unit_id: str, agent_key: str, *,
             card_vocab: Mapping | None = None, last_check: bool = False) -> dict: ...
```

고치는 기존 함수.

```python
# planner.py
def freeze_roster(store, target_key, owner_sub, agents, *, ecad_absent=False, mcad_absent=False,
                  defer_absent=True, settings=None) -> dict: ...      # defer_absent=False 면 deferred 를 만들지 않는다
def undefer(store, target_key: str, *, decided_by: str, reason: str) -> dict: ...   # 기존 타깃의 deferred → pending(사람 전이)
def review_order(store, target_key: str, *, settings=None) -> list[dict]: ...       # Tier 를 순서로(3.10.3)
def input_gaps(store, target_key: str, agent_key: str) -> list[str]: ...
ALLOWED_TRANSITIONS["deferred"] = frozenset({"pending"})

# runner.py
def panel_question(store, target_key, *, unit: Mapping | None = None, issue: Mapping | None = None) -> str: ...
def build_delib_opts(store, settings, panel, *, evidence=None, user_memo=None, narrative_mod=None, loss=None,
                     unit: Mapping | None = None, issue: Mapping | None = None) -> dict: ...

# narrative.py
SpecContext.unit_lines: Mapping[str, tuple[str, ...]]     # 새 필드(기본 빈 dict). 겹친 cid·snap 줄의 대조 후보(3.6.4)
SpecContext.diff_item(...)                                 # structural.dyna.scope_changed 도 훑는다

# render.py
SANITIZE_LIMITS["unit"] = 600                              # 단위 줄에 싣는 원천 문자열 한 칸. 넘으면 잘린 수를 센다(U5)
```

자산(`assets/*.v1.json`, `taxonomy.VOCAB_ASSETS` 에 등록).

| 파일 | 내용 |
|---|---|
| `part-roles.v1.json` | 부품 역할 어휘와 역할 → 영역. `{version, status:'seed', roles:{<role>:{label, tokens[], domains[]}}}` |
| `unit-routing.v1.json` | 변경 종류·이벤트 코드 → 영역 바닥 표, 늘 포함하는 영역, 제외 사유별 처리(`caveat`·`none`). |
| `input-gap.v1.json` | 입력 결손 질문 문안과 영역별 예시 경로(3.10.2). |

### 3.4 diff 타깃의 단위 생성 알고리즘

#### 3.4.1 항목 수집

세 층을 한 가지 모양으로 편다.

```json
{"ref": "c:35b9c6fd4309", "layer": "parametric", "bucket": "node_params", "code": "param.min_dim",
 "change_kind": "dimension", "klass": "active", "anchors": ["p:87ae2f56d589"], "asm": null,
 "attr": "min_dim", "before": 1.2, "after": 1.0, "delta": -0.2, "rel": -0.166667, "unit": "mm",
 "flag": "changed", "excluded_reason": null, "design_relevant": true, "confidence": null,
 "unconfirmed": false, "lower_bound": false, "caveat": null, "derived_from": [], "text": "PLATE_1 min_dim 1.200→1.000 mm (−16.7%) [c:35b9c6fd4309]"}
```

| 버킷 | 항목이 되는 조건 | anchors(대표 노드 dn) |
|---|---|---|
| `structural.node_changes` | 전부. `hierarchy_moves` 는 같은 cid 라 건너뛴다. | `[dn]` |
| `structural.edge_changes` | 전부. `op='status_changed'` 는 klass `non_design`. | `[dn_a, dn_b]` |
| `structural.dyna.scope_changed` | 전부. | 없음(전역) |
| `parametric.node_params`·`edge_params`·`result_delta` | `flag != 'noise'`. | `[dn]` 또는 `[dn_a, dn_b]` |
| `parametric.dims_delta` | `flag != 'noise'` 이고 (before, after) 가 둘 다 None 은 아닌 것. | 없음(전역). IR `dims_named[].ref` 가 부품이면 문맥 반복용으로만 적는다. |
| `parametric.materials` | 전부. | `[dn]` |
| `parametric.rollup_delta` | `n_leaf`·`edges_internal`·`edges_external`·`orphan_leaf` 중 before≠after 가 하나라도 있는 행. | 없음. `asm=<접두>` |
| `semantic.events` | 전부. | `subject.dns` 중 `p:` 로 시작하는 것. `asm:`·`dim:`·`contact#` 는 앵커가 아니다. |
| 그 밖의 리스트 버킷(앞으로 생기는 층) | `cid` 가 있는 dict 전부. `bucket_unknown=true`. | 없음(전역) |

이벤트가 없는 하위층 항목의 `change_kind` 는 속성에서 정한다 — `min_dim`·`bbox_*`·`volume`·`area`·계면 수치는 `dimension`, `centroid_world`·`bbox_world` 는 `placement`, `material.*` 는 `material`, `n_elems` 는 `discretization`, 결과 지표는 `result`, `fs` 는 `parameter`, 노드·계면의 추가·삭제·종류 변경은 의미층과 같은 값(`count`·`type`·`topology`)이다.

klass 는 넷이다.

| klass | 조건 | 가는 곳 |
|---|---|---|
| `active` | `excluded_reason` 없음 · `design_relevant` 가 False 아님 · `flag ∈ {changed, 없음}` | 묶음·경계·전역 단위 |
| `caveat` | `excluded_reason` 이 `unit-routing` 의 `caveat` 목록에 있거나 목록에 **없는 모르는 사유**, 또는 `flag='incomparable'` 이고 before≠after | 활성 항목과 같은 자리(앵커로 묶인다). 줄에 `단서=<사유>` 가 붙는다. |
| `excluded` | `excluded_reason` 이 `none` 목록에 있음, 또는 `flag='incomparable'` 이고 before=after, 또는 `null_one_side` 인데 양쪽 다 None | 제외 단위(검토 셀 없음) |
| `non_design` | `design_relevant=false`(`n_elems`·`mesh.density_changed`) 또는 `status_changed` | 제외 단위. 그 부품이 묶음에 있으면 문맥으로 반복한다. |

`unit-routing.v1.json` 의 제외 사유 기본값(8절 결정 2 의 권고값).

| 처리 | 사유 | 까닭 |
|---|---|---|
| `caveat` | `tol_unknown` · `tol_differs` · `null_one_side`(한쪽만) · `result_kind_differs` · `sim_params_differ` · 모르는 사유 | 비교 잣대가 불확실하다는 뜻이지 그 항목이 무관하다는 뜻이 아니다. 지금은 어댑터가 tol 해시를 읽지 않아(cad-capabilities.md:48) 계면 간극·띠·관통 수치 변화가 **전부** `tol_unknown` 이다. 제외 단위에만 두면 가장 중요한 변화가 아무에게도 가지 않는다. |
| `none` | `partial_scope` · `capture_partial` · `source_drift` · `not_design_relevant` · `incomparable_same` · `null_both` | 한쪽 스냅샷에 없거나 캡처가 깨져 생긴 겉보기 차이, 또는 설계 변경이 아닌 것이다. 제외 단위에 건수·사유와 함께 전부 남긴다. |

'타는' 규칙 하나. 활성 이벤트의 `derived_from` 에 있는 항목은 klass 가 무엇이든 그 이벤트와 같은 원자에 싣고 줄에 사유를 붙인다(`dim.named_unmeasured` 가 `null_one_side` 항목에서 나오는 경우).

같은 cid 가 두 번 나오면(2.1 의 브리지 충돌) 두 항목을 같은 원자에 싣고 `cids_json` 에는 한 번만 적는다. `flags.dup_cid_n` 에 센다.

#### 3.4.2 원자

- **부품 원자** `A(dn)` — 앵커가 그 dn 하나인 항목 전부.
- **쌍 원자** `A(dn_a|dn_b)` — 앵커가 그 두 dn 인 항목 전부(정렬).
- **조립 항목** — `asm` 이 있는 항목(롤업). 3.4.3 에서 범위가 한 단위 안이면 그 단위에, 아니면 전역에 간다.
- **전역 항목** — 앵커도 asm 도 없는 항목(명명 치수·scope 집합·모르는 버킷).

부품의 조립 키 `asm_of(dn)` 는 target 스냅샷 `rr_ir_nodes.asm_key`, 없으면 base 것, 그것도 없으면 `~<source_kind>`(dyna 단독 pid 는 `~dyna`)다. 표시 키는 `ckey or dn` 이다.

#### 3.4.3 묶기 — 조립 먼저, 연결 다음, 순서로 자르기 마지막

크기는 변경 줄 수와 글자 수 두 가지로 잰다. `fits(X)` = 줄 ≤ `max_lines` 이고 요약 글자 ≤ `max_chars` 다. 글자 수는 WP3a 의 단위 크기 식(3.13)으로 센다.

```
0. 활성·단서 항목의 줄 합이 small_lines 이하이고 fits 면 → 단위 하나(kind=bundle, scope='all', mode='single'). 끝.
1. 재귀 분할 split(접두, 부품들, 깊이).
     load = 그 부품들의 부품 원자 + 양 끝이 다 그 안에 있는 쌍 원자 + 접두가 그 범위 안인 조립 항목
     fits(load) 면 잎으로 낸다.
     아니면 asm_key 의 다음 조각으로 가른다(이 접두 직속 부품은 '<접두>/.' 로 모은다). 둘 이상으로 갈리면 각각 재귀.
     갈리지 않으면(평평한 모델) 쌍 원자와 '변경 부품끼리 잇는 변경 없는 1홉 계면' 을 간선으로 한 BFS 순서
       (시작·이웃 모두 표시 키 오름차순)로 늘어놓고 target_lines 를 넘기 직전마다 끊는다('<접두>#0', '#1', …).
   최상위는 asm_key 첫 조각으로 가른다.
2. 형제 채우기: 부모 접두가 같은 잎을 scope 오름차순으로 훑으며 target_lines 를 넘지 않는 동안 한 단위로 합친다(next-fit).
3. 쌍 원자 배정: 양 끝이 같은 단위면 그 단위가 소유. 다르면 두 단위 scope 의 가장 깊은 공통 접두를 키로 모아
     '경계 단위' 를 만든다(키 안에서 (단위 쌍, 표시 키) 순으로 target_lines 까지 채운다 — 'boundary:<공통 접두>#n').
     경계 항목은 양쪽 묶음에 문맥 줄로 반복한다.
4. 전역 단위: 전역 항목 + 한 단위에 들지 않는 조립 항목. 검토 대상 단위가 둘 이상이면 항목이 0건이어도 만든다
     (단위 목록·총량 줄을 싣는다 — 묶음 사이 조합을 보는 자리다).
5. 제외 단위: klass excluded·non_design 전부. 사유별 구획. max_lines 를 넘으면 사유 → 표시 키 순으로 자른다.
6. 재검사: 렌더해서 글자 수를 실측하고, 넘는 단위는 그 단위만 BFS 순서의 가운데에서 둘로 쪼개 다시 렌더한다(최대 6회).
7. 순번: (kind 순서 bundle→boundary→global→excluded, scope_key, unit_id) 로 정렬해 seq 를 매긴다.
```

묶는 열쇠 넷이 하는 일은 이렇다.

| 열쇠 | 쓰이는 곳 |
|---|---|
| `subject_key`·`ckeys`(대표 노드 dn) | 원자를 만든다 — 한 부품의 항목은 한 원자, 한 계면 쌍의 항목은 한 원자다. 원자는 쪼개지 않는다. |
| asm 롤업 키(`asm_key` 접두) | 1차 분할 축이다. 롤업 항목이 어느 단위에 붙는지도 이 키로 정한다. |
| 1홉 이웃(clearance 제외) | 조립 키로 더 못 가를 때 자르는 순서(BFS 간선), 문맥 줄('이웃'), 단위 사이 `links(via='neighbor')` 다. |
| clearance 근접 | 묶는 데는 쓰지 않는다. 문맥 줄('근접')과 `links(via='near')`, 시그니처 `near_roles` 로만 간다. |

합성 입력으로 이 절차의 초안을 메모리에서 돌려 본 값이다(파일을 만들지 않았다). 초안은 크기를 '이벤트 + 파생 항목' 묶음 수로 쟀고 목표 20·상한 40 이었다. 한 묶음이 평균 1.7줄이라(항목 2,102 / 묶음 1,263) 최종 설계의 줄 기준 20·40 에서는 단위 수가 이 표의 1.5~1.7배쯤 될 것으로 본다(추정 — 커밋 2 의 시험이 실제 값을 낸다).

| 합성 입력(부품·변형) | 항목 | 단위(묶음/경계/전역) | 단위당 크기 중앙·최대 | 미배정·이중 소유 | 순서 섞어 재실행 |
|---|---|---|---|---|---|
| 60 · 2 | 5 | 1 / 0 / 0 | 2 | 0 · 0 | 같은 id |
| 60 · 10 | 30 | 1 / 0 / 0 | 19 | 0 · 0 | 같은 id |
| 240 · 60 | 194 | 6 / 1 / 1 | 15 · 27 | 0 · 0 | 같은 id |
| 640 · 300 | 762 | 22 / 8 / 1 | 14 · 44 | 0 · 0 | 같은 id |
| 1200 · 900 | 2,102 | 36 / 21 / 1 | 20 · 40 | 0 · 0 | 같은 id |
| 640 평평 · 300 | 698 | 22 / 1 / 1 | 19 · 20 | 0 · 0 | 같은 id |
| 240 · 60, 의미층을 비움(G2 흉내) | 124 | 8개 | — | 0 · 0 | — |

640·300 행의 최대 44 는 초안이 롤업 항목을 분할 뒤에 붙여 상한(40)을 넘긴 것이다. 그래서 위 절차는 조립 항목을 1단계의 `load` 에 처음부터 넣고 6단계에서 다시 잰다. 묶는 계산 자체는 1,200부품·2,102항목에서 13ms 였고 9.2MB `diff_json` 의 파싱은 46ms 였다.

#### 3.4.4 결정론

- 단위 id = `'u:' + sha1(f"{builder 주판}|{kind}|" + "\n".join(정렬한 소유 참조))[:12]`. 소유 참조가 0건인 단위(전역 0건)는 `kind|scope_key|source_hash` 를 쓴다.
- 입력의 리스트 순서·DB 행 순서·dict 순서에 기대지 않는다. 모든 순회 앞에 정렬 키를 둔다(부품은 표시 키, 항목은 (층 순서 의미→구조→파라메트릭, 참조, text)).
- 시각·난수·uuid 를 해시 입력에 넣지 않는다. `built_at` 은 열에만 있다.
- `unit_hash` = `sha256(canonical_json([{ref, before, after, flag, excluded_reason, text}…정렬]))[:16]`. cid 는 값이 달라도 같으므로(cid 공식에 값이 없다) 값이 바뀐 것을 가리는 것은 이 해시다.
- `seq`·`title` 은 표시용이다. 다른 표가 단위를 가리킬 때는 `unit_id` 만 쓴다.

#### 3.4.5 불변식

| 이름 | 등식 | 어길 때 |
|---|---|---|
| U1 미배정 0 | `walk_cids(diff)` 의 cid 전부 ⊆ (단위 소유 참조 ∪ noise ∪ 변화 없는 롤업 ∪ 양쪽 None 치수). 기준은 수집 코드와 별개인 순회다. | 빌드 `failed`. 활성 빌드는 바뀌지 않는다. |
| U2 소유 하나 | 어떤 참조도 두 단위의 `cids_json` 에 동시에 없다. | 빌드 `failed`. |
| U3 상한 | bundle·boundary·global·snap 단위는 `fits` 다. 부품 원자 하나가 상한을 넘는 경우만 예외이고 `flags.split.rule='atom_oversize'` 로 적는다. | 예외가 아니면 `failed`. |
| U4 린터 | 모든 요약이 `render.assert_clean` 을 통과한다. | `failed`(코드 결함). |
| U5 절단 0 | 원천 문자열이 `SANITIZE_LIMITS['unit']` 에 잘린 칸 수 = 0. | 0 이 아니면 `invariants_json.U5_clipped` 에 수를 적고 단위 `flags` 에도 적는다(빌드는 `ok` — 숫자·참조는 온전하다). |
| U6 겹침 규칙 | 문맥 줄의 참조는 반드시 다른 단위가 소유한다. 부품 원자와 쌍 원자는 쪼개지지 않는다. | `failed`. |

겹침 규칙을 말로 적으면 이렇다. **소유는 하나, 문맥 반복은 허용.** 부품(P 줄)은 여러 단위에 나올 수 있다(이웃·경계의 끝점). 항목은 한 단위만 소유한다. 경계 항목·제외 항목·롤업·명명 치수는 관련 묶음에 '(문맥 · 소유 U07)' 로 다시 보일 수 있고 줄 수·노출 회계에서 소유와 따로 센다.

#### 3.4.6 경우별 동작

| 경우 | 동작 |
|---|---|
| 변경 1~2건 | 0단계로 단위 하나. 전역·경계 단위 없음. 제외 항목이 있으면 제외 단위 하나가 더 붙는다(셀 없음). |
| 변경 0건(self-diff) | 단위 0개. 빌드 `status='empty'`. 검토 잡은 이 상태에서 시작하지 않는다(WP3 에 계약). 종전 패널 흐름은 그대로 돌 수 있다. |
| 수백 건 | 위 표대로 수십 단위. 같은 변화가 여러 부품에 반복되면 동형 묶음 표기(3.6.3)로 줄 수가 준다. |
| 검토 대상 단위 > `units_max` | 단위를 버리지 않는다. 먼저 `target_lines` 를 `max_lines` 까지 올려 다시 묶고, 그래도 넘으면 그대로 저장하고 빌드 `status='oversize'`. 잡을 만들 때 셀 수(로스터 × 단위)를 보여 주고 명시 동의를 받는다. |
| G2 차단 | 구조·파라메트릭층으로 평소대로 묶는다. 빌드 `blocked_by='G2'`, 모든 단위 머리에 주의 줄이 붙는다(3.6.1). 추가·삭제로 보이는 부품이 이름만 바뀐 같은 부품일 수 있다는 것과 same-as 미확정 건수를 적는다. 이벤트를 코드가 지어내지 않는다. |
| capture_partial | 파라메트릭·계면 변경이 전부 `none` 이라 제외 단위로 간다. 활성은 `node_changes` 뿐이다. 빌드 `blocked_by='capture_partial'`, 전역 단위 머리에 '부분 캡처 — 제외 N건' 을 적는다. |
| asm_key 가 없거나 한 덩어리 | 1단계가 BFS 순서로 자른다(표의 '640 평평' 행). |
| 한 부품의 항목이 상한 초과 | 쪼개지 않고 그 부품만으로 단위 하나. `atom_oversize`. |
| 모르는 버킷 | 전역 단위가 소유하고 `bucket_unknown` 을 단위 머리에 적는다. U1 은 순회 기준이라 놓치지 않는다. |

#### 3.4.7 빌드 회계 `stats_json`

모양을 보이는 예다(숫자는 합성 640부품·변형 300건에서 딴 것에 제외 건수를 덧붙였다).

```json
{"items_total": 762, "by_layer": {"structural": 67, "parametric": 394, "semantic": 301},
 "by_klass": {"active": 715, "caveat": 31, "excluded": 4, "non_design": 12},
 "noise_n": 9841, "dup_cid_n": 0, "lower_only_n": 159,
 "excluded_by_reason": {"tol_unknown": 31, "not_design_relevant": 12, "incomparable_same": 4},
 "units": {"bundle": 22, "boundary": 8, "global": 1, "excluded": 1, "reviewable": 31},
 "lines_total": 746, "chars_total": 131200, "parts_changed": 268, "pending_sameas_n": 0}
```

`lower_only_n` 은 어느 이벤트의 `derived_from` 에도 없는 활성 항목 수다(지금 흐름에서 좌석에 가지 않던 변화의 크기다).

#### 3.4.8 재빌드와 단위의 수명

- `build_units` 는 `input_hash` 가 활성 빌드와 같으면 아무것도 쓰지 않고 활성 빌드를 돌려준다.
- 다르면 새 rev 를 만든다. 새 빌드에도 있는 `unit_id` 는 `rev_last` 만 올린다. 사라진 단위는 행을 지우지 않는다(`rev_last` 가 옛 rev 로 남는다). 새 단위는 새 행이다.
- 셀이 이미 있는 타깃(WP3 가 `rr_review_cells` 로 판정)에서 입력이 달라지는 재빌드는 `force=True` 와 `reason` 이 있어야 하고 `rr_audit(scope='target', action='units.rebuild')` 한 줄을 남긴다. 그때 셀을 어떻게 하는지는 WP3 다(WP3b 초안은 `reset_review` 로 그 타깃의 셀을 비운다). 이 꾸러미는 옛 단위 행을 남겨 `units.ref_index` 로 '그 전문가가 이미 본 참조 집합' 을 셀 수 있게 한다.
- 입력이 달라지는 원인은 넷뿐이다 — `builder_version`(배포), 상한(설정), 자산 판(역할 표는 시그니처에만 들어가고 묶기에는 안 들어간다 — `input_hash` 에서 묶기 입력과 시그니처 입력을 나누어 자산만 바뀌면 `sig_hash`·`signals` 만 다시 만든다), snap 의 상태 재계산(`rr_states`). diff 와 IR 은 불변이다.

### 3.5 snap 타깃의 단위 — (조립 단위 × 신호군)

원천은 `rr_states.state_json`(signals·rule_hits·gates·missing)과 `ir_json` 이다. signals 의 top 표가 10건에서 잘리므로(2.6) 항목은 IR 에서 같은 조건으로 **전부** 다시 뽑는다. signals 는 신호군의 정의와 인용 키(`sig:`)로 쓴다.

| 신호군 | 항목(IR 에서 전수) | 참조 | 앵커 |
|---|---|---|---|
| `interference` | kind=interference 계면 전부(관통 깊이·하한 표기·status) | `e:` · `sig:top.interference` | 두 부품 |
| `tight_gap` | kind=clearance 이고 `min_gap ≤ snap_tight_gap_mm` | `e:` · `sig:top.tight_clearance` | 두 부품 |
| `joint` | kind ∈ tied·touching·geometric·contact 계면(밴드 면적·간극·cross_file) | `e:` | 두 부품 |
| `thin` | 리프 부품 중 `min_dim < 0.3`(state.py `_THIN_MM`) | `p:` · `sig:ratios.thin_ratio` | 부품 |
| `material_null` | 재질 미기재 리프 | `p:` · `sig:counts.material_null` | 부품 |
| `orphan` | 닿는 계면이 없는 리프 | `p:` · `sig:counts.orphans` | 부품 |
| `rule` | `rule_hits` 의 적중 refs(적중 전부), `ir.warnings` | `rule:` · `warn:` + `e:`·`p:` | refs 의 부품 |
| `result` | `results.part_risk` 행(부품별 최악값) | `p:` · `sig:results.part_risk_top` | 부품 |
| 전역 | `dims_named`, `req.*`, 게이트 요약, `missing`, `counts.*`·`ratios.*`·`scale.*`·`hist.*`, `results.findings`, 평가 불가 규칙(`pass=null`), scope 하이퍼엣지 | `d:`·`req:`·`gate:`·`sig:`·`rule:` | 없음 |

- 묶기는 3.4.3 의 `partition` 을 그대로 쓴다. 부품 원자·쌍 원자가 위 항목이고 줄 상한만 `snap_max_lines` 다. 한 조립 범위의 신호군 합이 상한 안이면 신호군을 한 단위에 구획으로 싣고(`snap:<접두>:all`), 넘으면 신호군별 단위로 가른다(`snap:<접두>:joint` 등). 조립 범위를 가로지르는 계면은 경계 단위다.
- 신호에 걸리지 않은 부품·계면(예: 간극 0.2mm 초과 clearance)은 항목으로 싣지 않고 조립 범위마다 **집계 줄**로 싣는다('clearance 412건 중 37건을 실었다 — 나머지는 min_gap 분포 0.2~0.5mm 201 · 0.5mm 이상 174'). 고르는 기준(임계값)과 건수를 `flags.aggregated` 에 적는다. 조용히 빠지는 것이 없다.
- 전량 감사(전 부품·전 계면을 항목으로)는 설정 `HWAXRISK_SNAP_UNITS_FULL=1` 로 켠다(8절 결정 6).
- snap 단위의 신호는 전부 `forced hit` 이다(관련성으로 거르지 않는다 — 3.9.1).
- `rr_states` 가 없거나 `blocked` 면 빌드 `failed(error='state_absent' | 'gate_blocked')`.

### 3.6 전량 요약 — 잘라내지 않는 정규 표기

#### 3.6.1 구조

```
[검토 단위 3/31 · u:5d0c1e9a77b2 · bundle · 조립 «a_stack/stack_asm» · 변경 줄 9 · 부품 2 · 계면 1]
[요약] dimension 4 · topology 1 · material 1 · 이벤트 없는 원자료 3 | 감소 3 · 증가 1 | 역할 미상 2 | 재질 al6061→al7075
[주의] 의미층 차단 [gate:G2] — same-as 미확정 4건. 아래는 구조·파라메트릭층 원자료다. 추가·삭제로 적힌 부품이 이름만 바뀐 같은 부품일 수 있다.   ← 해당할 때만
[주의] 단서 변경 3줄 — 비교 잣대가 확인되지 않은 수치다(tol_unknown).                                                  ← 해당할 때만
[부품]
P1 [p:87ae2f56d589] «PLATE_1» 역할=미상 재질=«AL6061»→«AL7075» 조립=«a_stack/stack_asm» 소스=mcad 상태=유지
P2 [p:8051c8e0492d] «PLATE_2» 역할=미상 재질=«AL6061» 조립=«a_stack/stack_asm» 소스=mcad 상태=유지
[변경]
C01 [c:4423090197b5] part.thickness_changed P1 «PLATE_1 min_dim 1.200→1.000 mm (−16.7%) (min_dim 근사)» 감소 conf=high
  ↳ [c:35b9c6fd4309] 원자료 «PLATE_1 min_dim 1.200→1.000 mm (−16.7%)»
C02 [c:…] iface.rank_down P1↔P2 «PLATE_2↔PLATE_1 kind tied→touching (rank 2→1)» conf=high
  ↳ [c:185582dbf4c1] 원자료 «PLATE_2↔PLATE_1 iface kind_changed tied→touching (rank 2→1)»
C03 [c:8cee8c246679] part.material_changed P1 «PLATE_1 material.name AL6061→AL7075»
  ↳ [c:0b7b7235942e] 원자료 «PLATE_1 material.material_norm al6061→al7075»
C04 [c:c51c68b0e737] (이벤트 없음) P1 «PLATE_1 volume 3000→2500 mm3 (−16.7%)» 감소
C05 [c:893d8bcddc5a] (이벤트 없음) P1 «PLATE_1 bbox_dz 1.200→1.000 mm (−16.7%)» 감소
C06 [c:695d8f332da8] (이벤트 없음) P1↔P2 «PLATE_2↔PLATE_1 min_gap 0.000→0.018 mm» 증가 단서=tol_unknown
[문맥]
이웃 P2 — interference(status=auto) — «BRACKET_L» [p:d8f6805b7766] 변경 없음 · penetration_depth ≥0.050 mm(lower_bound) [e:c650f4ca3da5]
경계 [c:…] iface.removed «PLATE_2↔SHIM_1 iface.removed (tied)» (소유 U09)
참고 [c:…] mesh.density_changed «STACK\PLATE_1 n_elems 3200→4800 (+50.0%)» — 설계 변경 아님(소유 U31)
롤업 [c:…] asm.rollup_changed «asm:a_stack edges_internal 2→2 · external 0→0» (소유 U30)
```

#### 3.6.2 줄 규칙

- **줄의 몸통은 WP1 의 공용 표기 그대로다.** 항목의 `text` 에서 꼬리 참조를 떼고(`render.split_trailing_refs`) 대괄호 밖의 `p:해시` 를 부품 이름으로 바꾼 글(`render.humanize_refs(text, brief.name_index(…))`)이 몸통이다. 인용 대조(`canonical_text_for`)가 같은 함수로 같은 글을 만들므로 전문가가 단위 줄에서 옮긴 인용문이 그대로 맞는다. WP1 이 먼저 병합되지 않으면 이 꾸러미가 같은 시그니처로 그 함수들을 넣는다(먼저 들어가는 쪽이 넣는다).
- **줄 구조가 정본이고 요약은 그 렌더다.** 단위는 `lines_gz` 에 `[{ref, text, code, alias, layer, klass, direction, caveat, conf, derived_of}]` 를 둔다. `text` 는 몸통(«» 없음, 참조 꼬리 없음)이다 — WP3a 가 요구하는 `unit.lines[{ref, text}]` 가 이것이다(감싸기는 에이전트 서버가 한다). 요약(`summary_gz`)은 사람·패널·REST 가 읽는 렌더이고 거기서는 앱이 감싼다.
- **참조가 줄 머리에 한 번.** `[c:…]` 는 줄마다 한 번이다(지금 E2 는 두 번 찍는다 — brief.py:502).
- **부품 실명.** 이름은 `rr_ir_nodes.name`(스냅샷과 함께 동결된 값)이고 `rr_part_keys.display_name`(나중에 바뀔 수 있다)은 쓰지 않는다. P 번호는 그 단위의 `[부품]` 표를 가리키는 별칭이다.
- **before→after·단위·부호.** 몸통의 숫자는 diff 가 적은 그대로다(길이 3자리·면적 1자리·응력 정수, 음수는 U+2212). 방향은 `증가`·`감소` 낱말로 한 번 더 붙인다(부호를 놓치지 않게).
- **순서는 WP1 의 `brief.event_order` 를 원자 단위로 쓴다.** 원자마다 대표 줄(그 원자에서 `event_order` 가 가장 앞에 세우는 줄)을 뽑아 원자를 세우고, 원자 안은 이벤트 → 그 파생 줄 → 이벤트 없는 원자료(|rel| 큰 순 → 참조 순)다. 변경 종류가 돌아가며 앞에 서고 부호는 `abs` 로 지워지므로 감소가 뒤로 밀리지 않는다. 설계 변경이 아닌 줄(문맥 '참고')은 맨 뒤다.
- **표기.** `conf=`·`unconfirmed`·`lower_bound`·`caveat=parser_differs`·`단서=<사유>` 를 줄 끝에 붙인다.
- **원천 문자열은 «…» 안에.** 요약 렌더에서 몸통은 `render.sanitize_source_text(body, 'unit')` 를 거친다(E2 와 같은 모양). 인젝션 어휘에 걸려 자리표시자가 되면 그 줄만 필드에서 다시 조립한다 — 이름 칸만 `«[suspect_text …]»` 이고 속성·before→after·단위·참조는 코드가 쓴 글로 남는다(지금 E2 는 줄 전체가 자리표시자가 된다). `lines_gz` 의 `text` 에도 같은 치환을 한다.
- **코드가 쓰는 낱말은 린터 어휘 밖.** '증가'·'감소'·'단서'·'미상'·'차단'·'제외'·'원자료'·'문맥'·'참고' 만 쓴다. 게이트는 `[gate:G2]` 참조로 적는다('G2 실패' 라고 쓰면 L14 에 걸린다).
- **잘림 없음.** 요약은 `clip_lines` 를 타지 않는다. 길면 단위를 쪼갠다(3.4.3 6단계).

#### 3.6.3 동형 묶음 표기

한 단위 안에서 (code, attr, before, after, unit) 이 같은 항목이 4건 이상이면 한 줄로 묶는다. 참조와 이름은 하나도 빼지 않는다.

```
C07 part.moved centroid_world 이동 1.500 mm × 12건
  ↳ «SCREW_0_3»[c:14a92ff514d0] · «SCREW_0_7»[c:…] · «SCREW_0_11»[c:…] · … (한 줄에 8건씩, 12건 전부)
```

줄 수는 머리 1줄 + ceil(n/8) 줄로 센다.

#### 3.6.4 인용 대조와의 맞물림

- `c:`·`d:` 인용은 WP1 의 수리(정규 표기에 `humanize_refs` · 대조에 `norm_quote`)로 맞는다. 단위 줄의 몸통이 그 정규 표기와 같은 함수에서 나오기 때문이다(3.6.2).
- 이 꾸러미가 더하는 것은 둘이다. 첫째, `SpecContext.diff_item` 이 `structural.dyna.scope_changed` 도 훑게 한다(지금은 그 cid 가 dangling 이 된다 — 2.2). 둘째, 같은 cid 가 두 항목에 붙은 경우(2.1)에 `diff_item` 이 첫 항목만 돌려주는 것을 `SpecContext.unit_lines`(참조 → 그 참조의 단위 줄 몸통 전부, 값은 `units.line_index`)로 메운다 — 대조 후보가 여럿이면 어느 하나에 들어 있으면 일치다.
- `unit_lines` 가 비어 있으면(단위가 없는 종전 타깃) 지금과 한 글자도 다르지 않게 돈다.
- snap 단위의 `e:`·`p:` 줄은 지금 정규 표기가 없어(`canonical_text_for` 가 None) 인용문 대조를 건너뛴다. `unit_lines` 가 있으면 그 줄이 대조 기준이 된다.

### 3.7 단위 시그니처

모양을 보이는 예다(3.6.1 의 예와는 다른, 부품 6개짜리 단위다).

```json
{"change_kinds": {"dimension": 7, "topology": 3, "material": 2},
 "codes": {"part.thickness_changed": 2, "iface.rank_down": 1, "iface.gap_changed": 1, "part.material_changed": 1, "param.volume": 2, "param.bbox_def_dims": 3},
 "roles": ["bracket", "pcb"], "roles_unknown_n": 2,
 "role_pairs": ["bracket|pcb"],
 "materials": {"before": ["al6061"], "after": ["al7075"], "present": ["al6061", "sus304"]},
 "iface_kinds": {"tied": 2, "interference": 1}, "iface_transitions": ["tied→touching"],
 "attrs": {"min_dim": {"n": 2, "min_delta": -0.2, "max_delta": -0.1, "unit": "mm"},
           "min_gap": {"n": 1, "min_delta": 0.018, "max_delta": 0.018, "unit": "mm", "caveat": "tol_unknown"}},
 "directions": {"decrease": 6, "increase": 3, "none": 5},
 "asm_scope": ["main/asm2/sub0", "main/asm2/sub1"],
 "neighbor_roles": ["battery"], "near_roles": ["shield_can"],
 "n_parts": 6, "n_ifaces": 3, "n_lines": 14,
 "flags": {"semantic_blocked": null, "caveat_n": 3, "unconfirmed_n": 0, "lower_bound_n": 1, "low_conf_n": 0},
 "vocab": ["bracket", "브래킷", "pcb", "기판", "al6061", "al7075", "두께", "간극", "재질", "접합", "접촉"]}
```

- `roles` 는 변경 부품의 `name_norm_canon` 토큰을 `part-roles` 의 `tokens` 와 맞춘 것이다(머리 토큰부터, 첫 일치). 못 맞춘 부품 수가 `roles_unknown_n` 이다. `rr_ir_nodes` 에 `name_norm_canon` 열이 없으므로 `rr_part_keys.name_norm_canon`(ckey 로)을 읽고, 없으면 `ir_builder.name_norm_canon(name_norm)` 으로 계산한다.
- `neighbor_roles` 는 1홉 이웃(clearance 제외), `near_roles` 는 clearance 이웃이다. 비접촉 근접을 따로 둔다(02-coverage 의 지적).
- `vocab` 은 신호와 검색 질의에 쓰는 낱말이다 — 역할의 영문 토큰과 한글 label, 재질 정규명, 변경 종류의 한글 낱말(`unit-routing` 의 `terms`).
- `sig_hash` 는 `flags`·`n_*` 를 뺀 나머지의 해시다(WP3 의 카드 적용 시그니처 대조 키).

#### 3.7.1 단위 목록 항목(`digest`) — 전수 훑기가 보는 것

WP3a 의 전수 훑기는 단위 전문이 아니라 단위마다 800자 이하의 목록 항목 `{unit_id, kind, title, text}` 를 본다. 이 `text` 가 `rr_units.digest` 다. 관련성을 일으키는 세부를 버리지 않도록 코드가 다음 순서로 채운다(결정론).

```
1) 범위와 건수 — 조립 «a_stack/stack_asm» · 변경 9줄 · 부품 2 · 계면 1
2) 변경 종류별 건수와 방향 — dimension 4(감소 3 · 증가 1) · topology 1 · material 1
3) 역할과 재질 전부 — 역할 bracket·pcb·미상 2 | 재질 al6061→al7075
4) 수치 범위 — min_dim −0.200~−0.100 mm · min_gap +0.018 mm(단서 tol_unknown)
5) 계면 전이 — tied→touching 1
6) 부품 이름 — |rel| 큰 순으로 자리가 남는 만큼, 못 실은 수는 '외 n개' 로 적는다
7) 이웃·근접 역할 — 이웃 battery | 근접 shield_can
```

- 단위에서 유일하게 줄이는 글이다. 1~5 는 반드시 들어가고(넘치면 6·7 부터 줄인다) 못 실은 부품 수를 `flags.digest_omitted_n` 에 적는다.
- 전문가가 이 글만 보고 '무관' 이라 해도 그것만으로는 셀이 닫히지 않는다. 결정적 신호가 `miss` 일 때만 닫힌다(3.9.1).

### 3.8 근거 꾸러미

#### 3.8.1 두 층

| 층 | 무엇 | 원천 | 실패 |
|---|---|---|---|
| A 동결본 발췌 | 그 단위 부품의 명세(양쪽 스냅샷), 그 부품들이 끼인 계면 전부(변경 없는 것 포함, clearance 는 근접으로 따로), 1홉 인접 그래프, 해석 결과 행(`results.part_risk`), 규칙 적중 | `rr_ir_nodes`·`rr_ir_edges`·`ir_json.results`·`rr_states.rule_hits_json` — 캡처 때 `list_interfaces`·`interface_graph`·`report_part_risk` 가 준 것의 동결본이다(2.5) | 네트워크가 없으므로 IR 이 폐기된 경우(`ir_json=''`)에만 실패한다 → `evidence_status='failed'`, `error='ir_absent'` |
| B 실호출 | 캡처에 없던 지정 도구 | 게이트웨이 MCP | 그 줄만 `[조회 불가: <도구> — <사유>]`, `evidence_status='partial'` |

B 층의 호출 계획은 코드가 결정적으로 만든다(LLM 이 인자를 짜지 않는다).

| 도구 | 범위 | 조건 | 인자 |
|---|---|---|---|
| `compare_reports` | 타깃 1회 + 단위별 | diff 이고 `rr_targets.report_ids_json` 이 2건 이상 | `{report_ids: [앞 2건]}`. 단위별로는 그 단위에 `result_delta` 행이 있는 pid 마다 `part_id` 를 더한다(단위당 최대 4회). |
| `compare_materials` | 단위 | `part.material_changed` 가 있을 때 | `{names: [before, after]}`(재질명 쌍마다 1회, 타깃 안에서 같은 쌍은 재사용) |
| `get_material` | 단위 | 재질이 바뀌었는데 `compare_materials` 가 실패했을 때 | `{name: after}` |
| `list_interfaces` | 단위 | `HWAXRISK_EVIDENCE_LIVE_IFACE=1` 일 때만(기본 꺼짐) | `{project_id: <target 의 stepforge_project_id>, part: <부품명>, limit: 100}` — IR 이 담지 않는 필드(`sliver_verdict` 등)를 더 보려는 경우. '지금 상태' 표기가 붙는다. |

호출은 `field_source.FieldSource` 를 `reuse_s` 를 사실상 무한(10년)으로 주어 쓴다. 원문은 `rr_brief_calls` 에 남고(같은 인자는 타깃 안에서 한 번만 나간다) call_id 는 `b-…` 다. 도구 이름은 게이트웨이 실이름으로 풀어 부른다(`adapters.base.resolve_tool_name` — FieldSource 가 이미 한다).

#### 3.8.2 누가 어떤 자격으로 부르나

러너의 자격 순서를 그대로 따른다(`runner.resolve_credential_with_note` 와 같은 규칙, 짧은 호출의 여유 `runner.CREDENTIAL_MARGIN_S` 1800초).

1. 잡을 만든 사람(잡이 요청자 자격으로 집혔을 때)의 등록 PAT.
2. 타깃 owner 의 등록 PAT.
3. 서비스 계정 읽기 PAT(`HWAXRISK_PORTAL_PAT`).
4. 셋 다 없으면 B 층을 건너뛴다(`evidence_status='partial'`, `evidence_gaps_json` 에 `{tool:'*', code:'no_credential'}`, 본문에 `[실호출 없음 — 자격 없음]`).

- 쓰기 PAT(`HWAXRISK_PORTAL_PAT_RW`)는 쓰지 않는다(`tests/test_no_write_tools.py` 의 규율).
- 누구 자격으로 불렀는지를 `evidence_json.credential={kind, email}` 에 적는다.
- **서비스 계정 시야의 빈 응답을 사실로 굳히지 않는다.** 시야 밖 응답은 오류가 아니라 빈 배열로 온다(`field_source.for_target` 의 주석). 서비스 자격으로 받은 빈 결과는 `[조회 결과 0건 — 서비스 계정 시야]` 로 적고 `evidence_json.calls[].suspect_scope=true` 를 남긴다.
- MCP 경로(`actor` 미검증)는 꾸러미 조립을 일으킬 수 없다. REST `POST /targets/{key}/units/evidence` 는 editor 이상이고 호출자 → owner → 서비스 순이다.

#### 3.8.3 조립·동결·실패

```
unit_evidence.ensure(target) 의 절차.
  활성 단위 중 evidence_status 가 NULL 인 것마다(seq 순) 아래를 한다.
    A 층을 렌더한다(순수 계산).
    B 층 호출 계획을 만들고 호출마다 기한(HWAXRISK_EVIDENCE_CALL_DEADLINE_S 기본 300초)을 걸어 부른다.
      전체 예산(HWAXRISK_EVIDENCE_BUDGET_S 기본 3600초)을 넘기면 남은 호출은 '기한' 으로 적는다.
    본문을 evidence_max_chars 에 맞춘다(아래 우선순위). 생략한 줄의 참조를 evidence_json.omitted 에 적는다.
    한 트랜잭션으로 evidence_gz·evidence_sha·evidence_chars·evidence_gaps_json·evidence_json·evidence_status·evidence_frozen_at 을 쓴다.
```

- 꾸러미는 그 단위의 첫 셀·첫 패널이 돌기 **전에** 동결하고 그 뒤로는 고치지 않는다. 일부 실패(`partial`)여도 동결한다 — 전문가마다 다른 꾸러미를 보는 것보다 같은 결손을 다 같이 보는 편이 낫다. 다시 조립하려면 `only=[unit_id]` 와 `force` 가 필요하고, 그 단위에 이미 셀이 있으면 `evidence_json.history[]` 에 옛 해시를 남긴다(WP3 가 셀에 적은 `evidence_sha` 와 대조된다).
- 요약과 달리 꾸러미는 보조 근거라 줄일 수 있다. 우선순위는 변경 부품 명세 → 변경 계면 → 이웃 계면(간섭 → tied·touching → clearance, 그 안에서 `min_gap` 의 절댓값 오름차순) → 해석 결과 → 실호출 발췌 순이다. 끝에 `…(n줄 생략 — 전문은 GET /api/targets/{key}/units/{unit_id}?part=evidence_full)` 를 붙인다.
- 재기동이 조립 도중에 끊으면 `evidence_status` 가 NULL 인 단위가 남고 다음 `ensure` 가 이어서 한다. 이미 받은 원문은 `rr_brief_calls` 에 있어 다시 부르지 않는다.
- 꾸러미 줄의 참조는 지금 스킴으로 다 풀린다 — `[p:]`·`[e:]`·`[rule:]`·`[sig:]`, 캡처 호출은 `tool:<call_id>`. B 층의 `tool:b-…` 를 인용으로 인정하려면 셀·패널의 `SpecContext.call_ids` 에 `evidence_json.calls[].call_id` 를 더해야 한다(WP3·WP4 에 계약).
- 실호출 응답은 원문 JSON 을 그대로 붓지 않는다. 도구별 렌더러가 수치·id 필드만 뽑아 줄로 만들고 문자열 칸은 `sanitize_source_text(…, 'unit')` 를 거친다. 렌더러가 없는 도구는 줄마다 «…» 로 감싼다.

본문 모양.

```
[근거 꾸러미 — 검증 대상 · 결론 아님 · 단위 u:5d0c1e9a77b2 · 동결 2026-10-09 · 자격 owner]
[부품 명세 — 동결본(스냅샷 3f1c… → 9ab2…)]
P1 [p:87ae2f56d589] «PLATE_1» 크기 50.000×50.000×1.200→1.000 mm · 부피 3000→2500 mm3 · 재질 «AL6061»→«AL7075»
[계면 — list_interfaces 동결본]
[e:f1dabe4da27f] «PLATE_1»↔«PLATE_2» tied→touching · min_gap 0.000→0.018 mm · 밴드 면적 2500.0 mm2 · status=confirmed [tool:c3ff8323-004]
[e:c650f4ca3da5] «PLATE_2»↔«BRACKET_L» interference(status=auto) · penetration_depth ≥0.050 mm(lower_bound) · 변경 없음
[인접 — interface_graph 동결본, 1홉]
«PLATE_1» — tied→touching — «PLATE_2» — interference — «BRACKET_L»
[해석 결과 — report_part_risk 동결본]
«STACK\PLATE_1» pid 1 worst_stress 210→245 MPa (+16.7%) · worst_g … [c:…]
[실호출 — 지금 상태(스냅샷 뒤에 바뀌었을 수 있다)]
[tool:b-7c1e…] compare_materials(names=AL6061,AL7075) → E 69000→71700 MPa · sigy 276→503 MPa · rho …
[조회 불가: compare_reports — unknown tool]
```

### 3.9 변경→영역 신호

#### 3.9.1 규율

1. **신호는 포함만 시킨다.** 코드는 신호로 셀을 종결하지 않는다. 신호가 하는 일은 셋뿐이다 — `hit` 이면 그 셀은 반드시 깊이 검토로 간다(전문가의 '해당 없음' 이 지름길이 못 된다), `blind` 도 같다, `miss` 일 때만 전문가 자기판정이 '무관' 이면 '해당 없음' 이 **허용**된다(판정과 사유는 WP3 의 호출 출력이다).
2. **단조성.** 어떤 신호의 `miss` 도 다른 신호의 `hit` 을 뒤집지 못한다. 신호를 더하면 `hit` 은 늘기만 한다.
3. **모르면 `blind`.** 재료가 없어 계산하지 못한 신호는 `miss` 가 아니다.
4. **e5 절대 점수를 임계로 쓰지 않는다.** 이 코퍼스의 임베딩은 무관한 문장끼리도 코사인 0.87~0.90 이다. 신호가 읽는 값은 표 소속 여부, 어휘 겹침 건수(≥1), 키워드 검색 행 수(≥1), `desc_match > 0`(어휘 일치 비율 — 임베딩이 아니다) 뿐이다. `score` 는 읽지 않는다. `hybrid_search`·`semantic_search`·`agent_search(semantic)` 의 적중 건수도 쓰지 않는다(무엇을 물어도 top_k 가 온다). 의미 검색에서 온 `matched_sections > 0` 은 순위 기반이라 `hit` 으로만 쓰고 없다고 `miss` 로 세지 않는다.
5. **강제 포함.** 아래는 신호와 무관하게 `forced hit` 이다.

| 강제 포함 | 까닭 |
|---|---|
| Tier A(영역 1순위) 전문가의 전 단위 | 거르지 않은 기준 집합이다. WP3 가 자기판정과 대조해 놓침률을 잰다. |
| snap 타깃의 전 단위 | 현황 감사는 전 전문가 대상이다. |
| kind=global 단위 | 묶음 사이 조합(질량·공차 누적)은 전원이 본다. |
| 전문가가 2명 이하인 영역(material 1명) | 한 명이 걸러지면 영역이 빈다. |
| 지식카드 0장 전문가 | 어휘 신호를 계산할 재료가 없다(`blind` 로도 같은 결과지만 사유를 가른다). |
| 설정 `HWAXRISK_ROUTE_FILTER=off` | 필터를 끈 운영(8절 결정 3). |

#### 3.9.2 신호 목록

| 신호 | 단위 | 재료 | `hit` | `blind` | 방향 |
|---|---|---|---|---|---|
| S-role 부품 역할 | 단위→영역 | `signature.roles ∪ neighbor_roles ∪ near_roles` → `part-roles.roles[*].domains` | 역할의 영역 | 변경 부품 중 역할 미상이 하나라도 있으면 `hit` 아닌 영역 전부 | 양방향 |
| S-kind 변경 종류 바닥 | 단위→영역 | `signature.change_kinds`·`codes` → `unit-routing.floor`, `unit-routing.always` | 표의 영역 | 표에 없는 change_kind·code 가 있으면 전 영역 | 양방향 |
| S-mech 메커니즘 사슬 | 단위→영역 | `rr_delta_priors`(change_kind → mechanism, `n_raised>0`) → `taxonomy.mechanism.default_tools` → `seat-contract.table` 의 required·recommended 도구를 가진 영역 | 사슬 끝의 영역 | — | hit 전용(이력이 없으면 정보 없음) |
| S-card 카드 어휘 | 단위→전문가 | `signature.vocab` ∩ 그 전문가 카드 묶음의 제목·태그 어휘(WP3 `rr_card_packs`) | 겹침 ≥ 1 | 카드 묶음이 아직 없거나 0장 | 양방향 |
| S-desc 프로필 어휘 | 단위→전문가 | 게이트웨이 `recommend_agents(q=<구절>, top_k=<로스터 크기+50>)` 의 `desc_match` | `desc_match > 0` | 호출 실패·기한 | 양방향 |
| S-sect 섹션 순위 | 단위→전문가 | 같은 응답의 `matched_sections` | `> 0` | — | hit 전용 |
| S-fts 키워드 | 단위→전문가 | 게이트웨이 `fts_search(q=<vocab 낱말들>, top_k=1, agent_type=<키>)` | 행 ≥ 1 | 호출 실패·기한·그 전문가 문서 0건 | 양방향. **'해당 없음' 직전에만** 부른다(`for_cell(last_check=True)`) |
| S-adj 경계 승계 | 경계 단위→전문가 | 그 경계가 잇는 두 묶음의 `det` | 어느 한쪽이 `hit` | 어느 한쪽이 `blind` | 양방향 |

합치는 식.

```
det = 'hit'    — forced 이거나 어느 신호든 hit
    = 'blind'  — hit 이 없고 양방향 신호 중 하나라도 blind
    = 'miss'   — 양방향 신호가 전부 계산됐고 전부 miss
```

S-desc 의 질의 구절은 `units.roster_query` 가 만든다 — 단위마다 최대 4구절, 구절 하나는 낱말 2~4개(역할 label + 변경 낱말, 재질명 쌍, 계면 전이). 긴 질의는 임베딩이 뭉개지므로 짧은 구절로 나눠 부르라는 `recommend_agents` 설명(mcp_runtime.py:233~234)을 따른다. 호출 수는 단위 수 × 4 이하다.

#### 3.9.3 자산 초안

`unit-routing.v1.json`(값은 seed 다. 확정은 8절 결정 4).

```json
{"version": "unit-routing-1.0", "status": "seed",
 "floor": {"dimension": ["mech", "xd", "sim", "rel"], "placement": ["mech", "xd", "sim"],
           "topology": ["mech", "xd", "sim", "rel"], "material": ["material", "mech", "sim", "rel"],
           "type": ["mech", "xd", "rel"], "count": ["mech", "xd"], "result": ["sim", "rel", "mech"],
           "contact_type": ["sim"], "parameter": ["sim"], "consistency": ["sim", "mech"], "discretization": ["sim"]},
 "always": ["std"],
 "terms": {"dimension": ["치수", "두께"], "placement": ["위치", "이동"], "topology": ["계면", "접합", "접촉", "간섭", "간극"],
           "material": ["재질", "물성"], "count": ["부품 추가", "부품 삭제"], "result": ["응력", "가속도", "변위"]},
 "excluded_policy": {"caveat": ["tol_unknown", "tol_differs", "null_one_side", "result_kind_differs", "sim_params_differ"],
                     "none": ["partial_scope", "capture_partial", "source_drift", "not_design_relevant", "incomparable_same", "null_both"],
                     "unknown": "caveat"}}
```

`part-roles.v1.json` 의 첫 판은 `ir_builder.SEED_SYNONYMS` 의 정규명 10개(pcb·battery·display·housing·bracket·tape·screw·frame·shield_can·fpcb)와 택소노미 영역 label 에서 근거를 댈 수 있는 대응만 싣는다(pcb→pcb·passive·soc·mem, battery→pwr, display→disp, shield_can→rf·pcb, fpcb→pcb, housing·frame·bracket·screw→mech·xd, tape→mech·material). `sh` 영역은 자산에 label 이 'SH' 뿐이라 대응을 비워 둔다(9절). 표가 얇아도 규율 3 때문에 역할 미상 부품이 있는 단위는 `blind` 가 되어 누락 쪽으로 기울지 않는다.

#### 3.9.4 저장과 조회

`rr_units.signals_json`.

```json
{"asset_revs": {"part-roles": "part-roles-1.0", "unit-routing": "unit-routing-1.0", "seat-contract": "seat-contract-1.0"},
 "domains": {"mech": {"hit": ["S-role:bracket", "S-kind:dimension"]}, "material": {"hit": ["S-kind:material"]},
             "pcb": {"hit": ["S-role:pcb"]}, "std": {"hit": ["S-kind:always"]}},
 "domain_blind": ["S-role"], 
 "agents": {"mech-housing-structure": ["S-desc:0.5", "S-sect:3"], "pwr-swelling": ["S-desc:0.25"]},
 "agent_blind": {"S-desc": false},
 "phrases": ["브래킷 두께 변경", "AL6061 AL7075 재질", "tied touching 계면"],
 "computed_at": 1760000000}
```

`for_cell` 의 반환.

```json
{"det": "hit", "forced": null, "hits": ["S-role:pcb", "S-desc:0.25"], "blind": [], "miss": ["S-kind", "S-card"],
 "values": {"role": ["pcb"], "desc_match": 0.25, "card_overlap": 0, "fts_rows": null}, "input_gaps": ["ecad_absent"]}
```

WP3 는 셀을 만들 때 이 값을 셀 행에 그대로 얼린다(`na_irrelevant` 의 '신호값' 이 이것이다).

### 3.10 전원 포함

#### 3.10.1 로스터 동결

- `freeze_roster(..., defer_absent=False)` 면 전원이 `pending` 이다. `deferred` 를 만들지 않는다. 반환의 `deferred` 는 0 이고 `input_gap_n` 을 더한다.
- 입력 결손은 로스터 행에 얼린다 — `rr_roster.input_gaps_json`. ECAD 의존 도메인이고 `ecad_absent` 면 `'ecad_absent'`, `risk_mcad_domains` 에 들고 `mcad_absent` 면 `'mcad_absent'`.
- `routes.create_target` 은 타깃의 `flow` 가 `'cells'` 면 `defer_absent=False` 로 부른다. `flow` 는 본문 `flow` 또는 설정 `HWAXRISK_REVIEW_FLOW`(코드 기본값은 `panels` — WP3 가 붙을 때 WP5 가 `cells` 로 바꾼다)에서 온다. `refresh_roster` 도 같은 규칙으로 새 행의 `input_gaps_json` 을 채운다.
- 로스터 순위 질의문은 `units.roster_query` 의 구절을 쓴다(없으면 지금처럼 `summary_text` 앞 500자). 구절마다 `recommend_agents` 를 부르고 전문가별 `score` 최댓값을 relevance 로 삼는다(임계가 아니라 줄 세우는 값이다 — 3.9 의 신호는 이 값을 읽지 않는다). relevance 는 **영역 안 순서**에만 쓰이고(지금과 같다) 새 흐름에서는 범위를 정하지 않으므로 점수의 질이 누락으로 이어지지 않는다. `RECOMMEND_TOP_K` 는 60 에서 로스터 크기 + 50 으로 올린다(목록 밖 0점이 키 순서가 되는 것을 줄인다).

#### 3.10.2 `no_input` 과 두 질문

입력 결손이 있는 전문가의 셀은 질문이 둘이다. 호출의 정본은 WP3a 의 `noinput` 종류다(그쪽 3.5.4 — 출력 `q1{impact, l, k, cq, sev, why}`·`q2{item, needs, k, l, why}`). 이 꾸러미가 정하는 것은 **누가 그 길로 가는가**(`rr_roster.input_gaps_json`), **단위에 무엇이 빠졌다고 적는가**(`unit.missing[{kind, note}]`), **영역별 실마리**(`input-gap.v1.json`) 셋이다. 아래 문안은 질문의 뜻을 못 박으려는 초안이고 WP3a 의 문안과 다르면 그쪽을 따른다.

```
[입력 결손 — 이 타깃에는 ECAD(회로·배치·넷·스택업)가 없다]
아래 검토 단위에는 기구(MCAD)·해석 변경만 있다. 주어지지 않은 회로 데이터를 있는 것처럼 쓰지 마라.

질문 1 — 기구 변경이 당신 영역에 주는 영향.
  이 단위의 기구 변경이 {영역 label} 의 부품·기능에 주는 영향을 변경 줄마다 따져라.
  실마리({영역}): {input-gap 의 영역별 예시 경로}
  판정에는 변경 인용([c:…])과 카드 인용(card:…)이 둘 다 있어야 한다.
  기구 변경만으로는 말할 수 있는 것이 없으면 q1.status 를 "no_input" 으로 두고 까닭을 적어라.
  "해당 없음" 과 다르다 — 해당 없음은 ECAD 가 있어도 이 변경이 당신 영역과 무관하다는 뜻이다.

질문 2 — ECAD 가 오면 확인할 것.
  ECAD 가 제공되면 이 변경 때문에 당신이 확인할 항목을 적어라. 항목마다
  {what: 부품·넷·층·치수, because: [c:…], card: card:…, data_kind: 배치|넷|스택업|부품 사양|규칙 결과}.
  확인할 것이 없으면 빈 배열과 그 까닭을 적어라.
```

영역별 예시 경로의 첫 판은 `HWAXPortal/docs/design-risk-review/cad-capabilities.md:180~184` 에서 옮긴다 — passive '소자 위치의 변형률·지지 스팬', soc 'Z 간극·TIM 접촉', mem '언더필·스택업', pwr '팩 주변 간극과 허용치', rf '방사체·접지 금속과의 거리'. pcb 는 '보드 고정점·지지 스팬·보드 근접 계면' 이다(좌석 계약의 산출 문구).

`unit.missing` 의 예(`review_payload` 가 싣는다).

```json
"missing": [{"kind": "ecad", "note": "이 과제에는 회로(ECAD) 정보가 없다. 실마리(pwr) — 팩 주변 간극과 허용치"}]
```

| 질문 1 | 질문 2 | 셀 상태(제안) | 집계 |
|---|---|---|---|
| `impact=yes` 가 한 줄이라도 있음 | 무엇이든 | `reviewed`(입력 결손 표기) | 검토함. 정보 요청은 보고서의 '입력이 오면 확인할 것' 으로 모인다. |
| `yes` 없음(`no`·`unknown`) | 항목 ≥ 1 | `no_input` | 검토함에 세지 않는다. 타깃은 'C3(입력 결손 N셀)' 로 표기하고 사람 확인으로만 닫는다(WP4). |
| `yes` 없음 | 항목 0 + 까닭 | `no_input` | 같다. mem 의 일부 좌석처럼 ECAD 가 와도 풀리지 않는 자리가 여기 남는다. |
| (해당 없음) | — | `na_irrelevant` 는 `det='miss'` 일 때만 허용 | 3.9.1. 입력 결손 전문가도 같은 규율이다. 역할 미상 부품이 있으면 `blind` 라 허용되지 않는다. |

`rr_coverage.status` 는 CHECK 로 10종에 묶여 있어 `no_input` 을 넣을 수 없다. 전문가의 셀이 전부 `no_input` 이면 롤업은 `abstain` + `reason='no_input:ecad_absent'` 로 적고, 완결 판정은 그 reason 을 보고 '검토함' 에서 뺀다(WP4 에 계약). 입력 결손 전문가는 strong 비율의 분모에서도 뺀다(지금 MCP evidence_only 좌석을 빼는 것과 같은 처리 — registry.py:966~968).

#### 3.10.3 Tier 를 순서로

```python
planner.review_order(store, target_key) -> [
  {"order": 1, "agent_key": "cam-…", "domain": "cam", "rank_in_domain": 1, "tier": "A", "input_gaps": []},
  …]
```

- 정렬 키는 (tier 순서 A→B→C, `rank_in_domain`, domain, agent_key) 다. tier 는 지금 식 그대로(`tier_rank_cap`)에서 라벨만 뽑는다. 같은 원장이면 같은 순서다.
- 뜻이 바뀐다. A(영역 1순위 15명)는 '먼저 도는, 거르지 않는 기준 집합', B(누적 114명)는 '중간 점검 지점', C 는 나머지 전원이다. 중간에 멈춰도 어디까지 봤는지가 tier 로 나온다.
- 새 흐름 타깃의 기본 마감은 전원(C3)이다(8절 결정 1). `rr_targets.close_level` 은 타깃을 열 때 `HWAXRISK_UNITS_CLOSE_LEVEL`(기본 `C3`)로 적는다. 종전 흐름의 `risk_default_close_level`(C2)은 건드리지 않는다.
- 타깃 응답의 비용 추정에 `cells_estimate = roster_size × 검토 대상 단위 수` 와 tier 별 셀 수를 더한다(Tier C 동의 한 번으로 갈음할 숫자다 — 잡 API 는 WP3).

#### 3.10.4 `load_units`·`review_payload` — WP3 가 받는 것

단위의 모양은 WP3a 가 요구한 것(`{unit_id, kind, title, summary, lines, evidence, notes, missing}`)에 이 꾸러미의 열을 덧붙인 것이다.

```json
{"unit_id": "u:5d0c1e9a77b2", "kind": "bundle", "seq": 3, "total": 31, "reviewable": true,
 "title": "a_stack/stack_asm — 부품 2 · 계면 1", "summary": "dimension 4(감소 3 · 증가 1) · topology 1 · material 1 | 역할 미상 2 | 재질 al6061→al7075",
 "lines": [{"ref": "c:4423090197b5", "text": "PLATE_1 min_dim 1.200→1.000 mm (−16.7%) (min_dim 근사)", "code": "part.thickness_changed",
            "alias": "P1", "direction": "decrease", "klass": "active", "conf": "high", "caveat": null, "derived_of": null},
           {"ref": "c:695d8f332da8", "text": "PLATE_2↔PLATE_1 min_gap 0.000→0.018 mm", "code": "param.min_gap",
            "alias": "P1↔P2", "direction": "increase", "klass": "caveat", "conf": null, "caveat": "tol_unknown", "derived_of": null}],
 "evidence": [{"ref": "e:f1dabe4da27f", "text": "PLATE_1↔PLATE_2 tied→touching · min_gap 0.000→0.018 mm · 밴드 면적 2500.0 mm2 · status=confirmed"},
              {"ref": "tool:b-7c1e…", "text": "compare_materials(AL6061, AL7075) → E 69000→71700 MPa · sigy 276→503 MPa"}],
 "notes": "interference 의 auto 는 미확정 초안이다. penetration_depth 는 하한 추정치다. 단서=tol_unknown 줄은 비교 잣대가 확인되지 않은 수치다.",
 "missing": [{"kind": "ecad", "note": "이 과제에는 회로(ECAD) 정보가 없다. 실마리(pwr) — 팩 주변 간극과 허용치"}],
 "unit_hash": "…", "sig_hash": "…", "summary_sha": "…", "evidence_sha": "…", "evidence_status": "partial",
 "evidence_call_ids": ["b-7c1e…"], "size": 5912, "signature": {…}}
```

- `lines[].text`·`evidence[].text` 는 «» 없이, 참조 꼬리 없이 준다(WP3a 가 감싼다). 위생 처리(제어문자·인젝션 치환)는 앱이 이미 했다.
- `notes` 는 좌석 계약 `_common` 의 데이터 의미 문장(`seat-contract.v1.json`)에 그 단위의 표지(단서·차단·부분 캡처)를 더한 것이다.
- `missing` 은 타깃 수준 결측(ecad·mcad·dyna — 스냅샷 `missing_json`)과 단위 수준 표지(`semantic_blocked`)다. 전문가별 실마리는 `review_payload` 가 `rr_roster.input_gaps_json` 과 영역으로 덧붙인다.
- `review_payload(target_key, unit_id, agent_key)` 는 위에 `route`(3.9.4 의 `for_cell`)·`input_gaps`·`tier`·`order` 를 더해 돌려준다. `input_gaps` 가 비어 있지 않으면 WP3b 가 `noinput` 호출로 보낸다.

#### 3.10.5 기존 타깃·기존 원장과의 호환

- **아무것도 자동으로 바뀌지 않는다.** `flow='panels'`(기본값)인 타깃은 종전대로 돈다. `freeze_roster` 의 기본값 `defer_absent=True` 가 지금 동작이다. 종전 시험(`test_freeze_roster_defers_ecad_dependents_except_rank_one`·`test_tier_plan_with_ecad_absent`)은 그대로 통과한다.
- **단위 빌드는 종전 타깃에도 해가 없다.** `POST /targets/{key}/units` 는 표 두 개에 행을 더할 뿐이고 패널 흐름은 그 표를 읽지 않는다. 운영 타깃에서 먼저 돌려 실제 분포를 잴 수 있다(5.3).
- **보류를 푸는 길.** `planner.undefer(target_key, decided_by, reason)` 가 `deferred(reason='ecad_absent')` 를 `pending` 으로 돌리고 `input_gaps_json` 을 채우며 `status_source='human'`·`decided_by`·`decided_at` 과 `rr_audit(scope='coverage', action='coverage.undefer')` 를 남긴다. 그 타깃에 `queued|running|paused|cancelling` 잡이 있으면 409 다. `ALLOWED_TRANSITIONS['deferred']` 가 `{'pending'}` 이 되므로 `tests/test_planner.py:522~524`·`:553` 을 의도를 적어 고친다(종결 상태에서 나가는 길이 `carried`·`deferred` 둘이 된다). plan.md:3639 의 '사용자가 되돌릴 수도 없다' 도 같이 고친다.
- 보류를 푼 종전 타깃은 `close_level` 의 지금 식에서 ECAD 영역의 need 가 1 에서 max(3, ceil(0.3·크기)) 로 오른다. 의도한 결과다.

### 3.11 패널 연결(WP4 가 쓰는 것)

WP4 초안은 쟁점 패널의 질문과 브리프를 제 함수(`issues.issue_question`·`build_issue_brief`)로 만든다. 그 길로 가면 이 꾸러미가 주는 것은 단위 머리 문구와 `units.panel_evidence` 둘이고, 아래 `panel_question(unit=…)`·`build_delib_opts(unit=…)` 는 그것을 감싼 얇은 형태다. 둘을 따로 구현하지 않는다 — 통합할 때 한쪽으로 정한다(7.4).

- **질문.** `panel_question(store, target_key, unit=None, issue=None)`. `unit` 이 없으면 지금 문자열과 바이트가 같다. 있으면 다음 모양이다.

```
[리스크심사 {과제코드} {target_key} · 단위 {seq}/{total} {unit_id}] 기준 {base 코드} 대비 변경 가운데 {title} — {digest}.
쟁점: {issue.title}. 이 변경이 {issue.domains 또는 '각 도메인'} 에서 어떤 리스크와 개선을 낳는가를
근거 EU(변경 줄)·EP(근거 꾸러미)의 [c:]·[e:]·[p:] 를 인용해 판정하라. 낱말: {signature.vocab 앞 12개}.
```

  엔진은 이 질문으로 좌석 지식카드를 찾고(`deliberation.py:4095`) 좌석 도구 순서를 매기므로, 변경 어휘(역할·재질·변경 낱말)가 질문에 들어가는 것이 핵심이다. 질문은 사람에게 묻는 지시문이라 판단어 린터 대상이 아니다(지금 질문도 '리스크와 개선' 을 쓴다).

- **근거.** `units.panel_evidence(store, target_key, unit_id, refs=None, budget_chars=6000, item_max=None)`.

```json
{"evidence": [
   {"source": "rr_unit", "tool": "rr_units", "args": "u:5d0c1e9a77b2", "key": "EU", "result": "[검증 대상 — 결론 아님 · 원천: rr_unit · 생성: 2026-10-09]\n[검토 단위 3/31 …]\n…"},
   {"source": "rr_unit.evidence", "tool": "rr_units", "args": "u:5d0c1e9a77b2", "key": "EP", "result": "[근거 꾸러미 …]\n…"}],
 "omitted": {"lines": 0, "refs": []}, "chars": {"EU": 3890, "EP": 1980}, "call_ids": ["b-7c1e…"]}
```

  - `refs` 를 주면 그 참조의 줄(과 그 줄이 가리키는 P 줄)만 싣는다(쟁점이 단위의 일부일 때). 안 주면 단위 전체다.
  - 예산을 넘으면 줄 단위로 줄이되 빠진 참조를 `omitted.refs` 로 돌려준다. 호출자가 패널 `quality_json` 에 옮긴다(지금 `evidence_dropped` 를 적는 자리 — runner.py:1357 부근).
  - `item_max` 를 주면 EU 를 그 길이 이하의 여러 항목(EU1·EU2…)으로 나눈다. MCP L2 경로의 JS 파이프라인은 항목 2,000자·합 11,000자·12건에 묶여 있다(`HWAXPortal/infra/pipeline/hwax-deliberate.js:228~230`).
  - 예산 6,000자의 근거. 128K 창에서 엔진의 좌석 근거 합계는 약 17,967자다(02-fit 의 산식). 남기는 브리프 항목(E0·E0c·E1·E5~E9·M)의 라인 상한 합은 `brief.CAPS` 로 8,200자라 약 9,700자가 남고, EU·EP 6,000자는 그 안에 든다.

- **조립.** `build_delib_opts(..., unit=…, issue=…)` 가 `unit` 을 받으면 `prior_evidence(..., exclude=('E2','E3','E4'))` 로 타깃 전체 변경 칸을 빼고 그 자리에 EU·EP 를 넣는다(E1 요약은 타깃 문맥으로 남긴다). 칸 수는 11 로 12 이하다. `question` 은 위 함수로 만든다. 그 밖의 필드(`tools`·`apps`·`personas`·`voc`)는 건드리지 않는다. 포털 스키마에 새 필드를 더하지 않으므로 포털·엔진 변경이 없다.
- **연결 재료.** `rr_units.context_json.links` 는 `[{unit_id, via: 'boundary'|'neighbor'|'near', n}]` 이다 — 경계 단위가 잇는 묶음, 변경 없는 계면으로 이웃한 변경 부품 쌍, clearance 로 가까운 변경 부품 쌍. WP4 의 (단위 × 영역쌍) 교차 셀이 `signature.role_pairs` 와 함께 읽는다.

### 3.12 REST·MCP(추가만 한다)

| 경로 | 권한 | 응답 |
|---|---|---|
| `POST /api/targets` | 종전 | 종전 필드 + `flow`, `units: {rev, status, mode, n, reviewable_n, blocked_by, lines_total, excluded_by_reason}`, `input_gap_n`, `cells_estimate` |
| `POST /api/targets/{key}/units` | editor | `{rev, status, changed: bool, units: […매니페스트]}`. 본문 `{force?: bool, reason?: str}` |
| `GET /api/targets/{key}/units` | 멤버 | `{rev, status, mode, blocked_by, stats, invariants, units: [{unit_id, seq, kind, reviewable, scope_key, title, digest, n_changes, n_parts, summary_chars, unit_hash, sig_hash, evidence_status, signals_status, links}]}` |
| `GET /api/targets/{key}/units/{unit_id}?part=summary\|lines\|signature\|signals\|evidence\|evidence_full` | 멤버 | 그 부분 |
| `POST /api/targets/{key}/units/evidence` | editor | `{built, ok, partial, failed, gaps, credential}` |
| `POST /api/targets/{key}/undefer` | editor | `{undeferred}`. 본문 `{reason}` 필수 |
| `GET /api/targets/{key}/coverage` | 종전 | 종전 필드 + `units{rev,status,reviewable_n}`, `input_gap{agents_n, by_gap}` |
| MCP `risk_get_units(target_key, unit_id=None, part='manifest')` | 읽기(`_scoped('target', …)`) | 위 GET 과 같은 함수. `tests/test_mcp_tools.py` 의 도구 목록 15종으로 갱신 |

`create_target` 안의 순서. 검증 → `units.compute`(읽기와 계산뿐, DB 쓰기 없음) → 로스터 조회(구절 질의) → **한 트랜잭션**으로 타깃 행·`units.persist`·로스터 동결·승계. 단위 계산이 예외를 내면 타깃은 그대로 만들고 `rr_unit_builds(status='failed', error=…)` 한 행을 남긴다(단위 실패가 타깃 생성을 막지 않는다).

### 3.13 설정과 상한

전부 코드 기본값이 넉넉한 쪽이다. 바꾸려면 매니페스트 `launch.env` 에 적는다(SIF 가 cleanenv 라 셸 export 는 닿지 않는다 — `config.KNOB_HOME`).

| env | 기본 | 뜻 |
|---|---|---|
| `HWAXRISK_REVIEW_FLOW` | `panels` | 새 타깃의 흐름(`cells` 면 deferred 없음). 전환은 WP5. |
| `HWAXRISK_UNIT_TARGET_LINES` / `_MAX_LINES` / `_MAX_CHARS` | 20 / 40 / 7000 | 단위 크기(변경 줄·요약 글자) |
| `HWAXRISK_UNIT_EVIDENCE_MAX_CHARS` | 4500 | 꾸러미 크기 |
| `HWAXRISK_UNITS_MAX` / `HWAXRISK_UNITS_SMALL_LINES` | 60 / 15 | 단위 수 경고선 / 단위 하나로 내는 크기 |
| `HWAXRISK_SNAP_UNIT_MAX_LINES` / `HWAXRISK_SNAP_TIGHT_GAP_MM` / `HWAXRISK_SNAP_UNITS_FULL` | 70 / 0.2 / 0 | snap 단위 |
| `HWAXRISK_EVIDENCE_CALL_DEADLINE_S` / `HWAXRISK_EVIDENCE_BUDGET_S` / `HWAXRISK_EVIDENCE_LIVE_IFACE` | 300 / 3600 / 0 | 꾸러미 실호출 |
| `HWAXRISK_ROUTE_FILTER` | `on` | `off` 면 전 셀 `forced hit` |
| `HWAXRISK_UNITS_CLOSE_LEVEL` | `C3` | 새 흐름 타깃의 마감 수준 |

**상한은 전문가 호출이 받을 수 있는 크기에서 온다.** 단위 하나(요약 + 꾸러미 + 머리)는 WP3a 의 카드 대조 호출에 통째로 실린다. 그 자리의 크기는 에이전트 서버가 모델 창에서 유도해 `GET /card-review/limits` 의 `verdict.unit_body_max` 로 알려 준다(WP3a 초안 — 운영 128K 창에서 12,126자, dev 16K 창에서 3,008자). 그래서 다음처럼 한다.

- 코드 기본값(7,000 + 4,500 = 11,500자)은 운영 128K 창의 12,126자에 맞춘 값이다.
- 크기를 재는 식은 WP3a 의 것을 그대로 쓴다 — `unit_size = Σ(len(text) + len(ref) + 11) + len(title) + len(summary) + len(notes) + Σlen(missing.note) + 160`(줄과 근거 줄 전부에 대해). 불변식 U3 의 `fits` 가 이 식이다.
- `caps_for_limits(limits)` 가 박스의 실제 값으로 상한을 다시 만든다 — `max_chars = int((unit_body_max − 400) × 0.6)`, `evidence_max_chars = unit_body_max − 400 − max_chars`, `max_lines = max(8, max_chars // 175)`, `target_lines = max_lines // 2`, `digest_max = sweep.manifest_item_max − 20`.
- 타깃을 열 때는 설정값으로 빌드한다(네트워크 없음). 검토 잡이 격자를 만들기 **전에** WP3b 가 limits 를 읽고, 어느 단위든 `unit_size > unit_body_max` 이면 `build_units(force=True, reason='limits')` 를 `caps_for_limits` 로 다시 부른다. 셀이 아직 없을 때라 고아가 생기지 않는다. dev(16K 창)에서는 그래서 단위가 더 잘게 나온다(형식 시험용이다).
- 단위 목록 항목(`digest`)은 `sweep.manifest_item_max`(800자) 안이다(3.7.1).
- 타깃 전체의 요약 총량은 단위 수 × 7,000자가 천장이고 gzip 으로 타깃당 수백 KB 다(합성 1,800줄·105,760자가 32,562바이트였다).

### 3.14 상태기계

```
빌드(rr_unit_builds.status, rev 마다 한 번 정해지고 바뀌지 않는다)
  계산 성공 · 검토 대상 단위 ≥ 1 · 불변식 통과 ──▶ ok
  활성 항목 0                                 ──▶ empty
  검토 대상 단위 > units_max                   ──▶ oversize   (단위는 전부 저장. 잡에 명시 동의 필요)
  예외 · 불변식 U1·U2·U3·U4·U6 위반            ──▶ failed     (직전 활성 빌드가 그대로 활성)
  새 rev 가 ok|empty|oversize 로 서면 직전 rev 의 active 가 0 이 된다.

꾸러미(rr_units.evidence_status)
  NULL ──ensure──▶ ok        (계획한 실호출 전부 성공, 또는 실호출 계획 0건)
              ├──▶ partial   (실호출 일부 실패·기한, 또는 자격 없음 — 사유는 evidence_gaps_json)
              └──▶ failed    (A 층 불가 — IR 없음)
  제외 단위는 none(꾸러미를 만들지 않는다).
  ok|partial 은 evidence_frozen_at 이 찍히고 불변. 다시 하려면 force(이력 남김).

신호(rr_units.signals_status)
  NULL ──compute──▶ ok | partial(게이트웨이 호출 일부 실패 — 그 신호는 blind)

좌석(rr_coverage.status) — 바뀌는 전이 하나
  deferred ──undefer(사람)──▶ pending
```

---

## 4. 커밋 단위 작업 순서

리포는 따로 적지 않으면 HWAXRisk 다. 걸음마다 `cd backend && python -m pytest -q` 전체와 `ruff check app tests` 가 초록이어야 다음으로 간다. 리포 CLAUDE.md 규칙대로 새 소스 파일 첫 줄은 한글 한 줄 주석이다.

| # | 커밋 | 선행 | 바뀌는 파일 | 검증 |
|---|---|---|---|---|
| 0 | docs: 계획·체크리스트·결정 기록 | 없음 | `HWAXPortal/docs/design-risk-review/` 에 이 설계의 PLAN·checklist·context-notes 항목, `HWAXRisk/context-notes.md` | 문서만. `test_cluster_naming` 등 포털 문서 가드 통과 |
| 1 | test: 다건 diff 합성기 | 없음 | `tests/synth_ir.py`(부품 N·조립 M·변형 K·시드), `tests/test_synth_ir.py` | 합성 쌍이 `rr_ir.v1.json` 스키마를 통과하고 `compute_diff` 가 시드마다 같은 `diff_hash` 를 낸다. 변형 300건에서 이벤트 > 100 |
| 2 | feat(units): 순수 핵심 — 수집·묶기·렌더·시그니처 | 1. WP1 의 공용 표기 함수(없으면 이 커밋이 같은 시그니처로 넣는다) | `app/units.py`(순수 함수만), `app/assets/part-roles.v1.json`·`unit-routing.v1.json`, `app/assets/taxonomy.v1.json`(change_kind 축에 `contact_type`·`parameter` — WP1 R-32, 자산 minor 판), `app/taxonomy.py`(VOCAB_ASSETS), `app/render.py`(`SANITIZE_LIMITS['unit']`), `tests/test_units_diff.py` | 5.1 의 U1~U6·결정론·경우별 시험. 실제 줄 기준 단위 수 표를 context-notes 에 적는다 |
| 3 | feat(store): 단위 표 | WP5a 의 v3 블록과 순서를 맞춘다(그 블록이 나가기 전이면 거기에, 나간 뒤면 v4) | `app/risk_store.py`, `app/export.py`, `app/routes.py`(TRANSFER·PURGE), `tests/test_store.py`·`test_export_import.py` | 빈 DB·v2 DB 양쪽에서 migrate 멱등, pre-migrate 사본, 반출·들여오기 왕복에서 BLOB 보존, 폐기 뒤 원문 열이 빈다 |
| 4 | feat(units): 저장·조회·REST·MCP | 2·3 | `app/units.py`(compute·persist·build_units·manifest·load_units·manifest_items·get_unit·ref_index·line_index), `app/routes.py`(경로 셋 + create_target 훅), `app/mcp_server.py`, `tests/test_units_store.py`·`test_p6_routes.py`·`test_mcp_tools.py` | 같은 입력 재빌드가 no-op, 상한을 바꾸면 rev 가 오르고 겹치는 unit_id 는 유지, 단위 계산 예외에도 타깃은 생긴다, MCP 범위 밖은 not_visible |
| 5 | feat(units): snap 단위 | 4 | `app/units.py`(build_snap_units), `tests/test_units_snap.py` | 간섭 25건 합성 스냅샷에서 25건 전부 항목(signals top 은 10건), 집계 줄의 건수 합 = IR 건수 |
| 6 | fix(narrative): scope_changed 조회, 겹친 cid 의 대조 후보 | 4. WP1 의 인용 대조 수리 뒤 | `app/narrative.py`, `tests/test_persist_panel.py`·`test_atoms.py` | 단위가 없는 타깃의 기존 시험 전부 불변. `structural.dyna.scope_changed` cid 가 풀린다. cid 가 겹친 두 항목 어느 쪽 줄에서 옮긴 인용도 일치로 판정 |
| 7 | feat(evidence): 근거 꾸러미 | 4 | `app/unit_evidence.py`, `app/routes.py`(evidence 경로), `app/config.py`(손잡이), `tests/test_unit_evidence.py` | 5.1 의 꾸러미 시험. 네트워크는 `httpx.MockTransport` |
| 8 | feat(signals): 변경→영역 신호 | 4(S-card 는 WP3 의 카드 묶음이 생긴 뒤 켜진다) | `app/unit_signals.py`, `app/roster.py`(구절 질의·top_k·`desc_match` 파싱), `tests/test_unit_signals.py`·`test_roster.py` | 5.1 의 신호 시험(단조성·blind·강제 포함·점수 미사용) |
| 9 | feat(planner): 전원 포함 | 3 | `app/planner.py`(freeze_roster·undefer·review_order·input_gaps·전이표), `app/routes.py`(flow·undefer·coverage 필드), `app/assets/input-gap.v1.json`, `app/config.py`, `tests/test_planner.py`·`test_p6_routes.py` | 기본값에서 종전 시험 불변. `defer_absent=False` 면 deferred 0 이고 회로 6개 영역 110명에 입력 결손이 적힌다(종전에 보류되던 104명 + 대표 6명). review_order 가 15 / 114 / 359 경계를 낸다. undefer 감사 행 |
| 10 | feat(runner): 패널이 단위를 받는다(WP4 가 제 함수로 만들면 `units.panel_evidence`·`review_payload` 만 한다) | 4·7 | `app/runner.py`(panel_question·build_delib_opts), `app/units.py`(panel_evidence·review_payload), `tests/test_runner.py`·`test_brief.py` | `unit=None` 이면 delib_opts 가 바이트 동일(기존 스냅샷 시험). `unit` 을 주면 E2~E4 가 빠지고 EU·EP 가 들어가며 질문에 역할·재질 낱말이 든다. strict lint 통과 |
| 11 | feat(dev): 합성 쌍 주입 명령과 실주행 절차 | 4 | `app/cli.py`(`hwax-risk dev-seed-pair` — fixture 과제에만 쓴다), `HWAXRisk/docs/` 실주행 절차 | 5.3 |
| 12 | docs: 정본 문서 맞추기 | 9 | `HWAXPortal/docs/design-risk-review/plan.md`(§6.3 deferred·§6.4.1 Tier·§6.8.2 전이), `docs/changelog.yaml`, `HWAXRisk/README.md`·`.portal/manifest.yaml` 주석(손잡이) | 문서가 구현과 어긋난 채 남지 않게 한다 |

2·3 은 서로 독립이라 어느 쪽이 먼저여도 된다. 8 의 S-card 와 3.10 의 셀 상태는 WP3 가 붙어야 닫히지만 그 전에도 나머지는 혼자 돌고 시험된다.

---

## 5. 시험

### 5.1 단위 시험(네트워크 없음)

WP5b 초안이 단위 계약 시험(`tests/rr/test_units_contract.py`, U1~U9·S1)을 따로 잡고 있다. 아래 표는 이 꾸러미가 제 커밋에서 같이 내는 시험이고, 이름이 겹치는 것(U1·U2·결정론·크기·G2·빈 입력)은 한 벌로 합친다. 두 곳의 정의가 다른 것은 7.4 에 적었다(제외 사유의 처리, 순서 단언).

**단위 생성(`test_units_diff.py`).** 입력은 기존 픽스처 6쌍(`tests/fixtures/diff_pairs`)과 합성기다.

| 단언 | 방법 |
|---|---|
| U1 미배정 0 | `walk_cids` 와 단위 소유 참조의 차집합이 noise·무변화뿐이다. 픽스처 6쌍 + 합성(부품 60~1,200 × 변형 2~900 × 시드 5) |
| U2 소유 하나 | 참조별 소유 단위 수 = 1 |
| 결정론 | `diff_json` 의 모든 리스트를 섞고 노드 행 순서를 섞어 3회 — `unit_id` 목록·`summary_sha`·`sig_hash`·`unit_hash` 가 같다 |
| 상한 | 검토 대상 단위 전부 `fits`. 일부러 작은 상한(줄 5)으로 돌려 재귀·BFS·재검사 경로를 탄다 |
| 작은 diff | 변형 1·2건 → 단위 1개(`mode='single'`), 전역·경계 없음 |
| 빈 diff | self-diff → 단위 0, `status='empty'` |
| 큰 diff | 변형 900건 → 단위 수가 `units_max` 이하이거나 `oversize` 이고 어느 쪽이든 U1 성립 |
| 이벤트 없는 변화 | `pair_thick` 에서 volume·bbox_dz 줄이 요약에 있다(지금 흐름의 누락을 못 박는다) |
| 감소가 남는다 | 감소 변화 줄에 U+2212 와 '감소' 가 있고 증가 줄보다 뒤로 밀려 잘리지 않는다(요약에는 절단이 없다 — 전 참조가 요약 글에 나타나는지를 정규식으로 센다) |
| 줄 형식 | 수치 항목 줄마다 `before→after`, 단위, 참조가 있다. 계면 줄에 `p:` 해시가 아니라 «실명» 이 있다 |
| G2 차단 | `links` 에 pending 한 건을 넣어 `compute_diff` → 이벤트 0 이어도 단위가 서고 머리에 `[gate:G2]` 줄, 빌드 `blocked_by='G2'` |
| capture_partial | IR 에 `capture_partial=True` → 파라메트릭·계면이 제외 단위로, 전역 머리에 건수 |
| 제외 사유 처리 | tol 해시를 한쪽에서 지우면(`tol_unknown`) 간극 변화가 묶음 안에 `단서=tol_unknown` 줄로 실린다. `n_elems` 변화는 제외 단위가 소유하고 그 부품 묶음에 '참고' 문맥으로 보인다 |
| 모르는 사유·모르는 버킷 | `excluded_reason='새사유'` → caveat. `parametric['new_bucket']` 주입 → 전역 단위 소유, U1 성립 |
| 경계 | 조립을 가로지르는 계면 변경 → 경계 단위가 소유, 양쪽 묶음에 문맥 줄, `links` 에 서로 |
| cid 충돌 | dyna pid 를 mcad 부품의 dn 에 묶은 IR → 예외 없이 두 줄, `cids_json` 에 한 번, `dup_cid_n=1` |
| 린터·위생 | 모든 요약이 `render.assert_clean` 통과. 부품명에 `ignore previous` 를 넣으면 그 칸만 자리표시자이고 숫자·참조는 남는다. 600자 넘는 이름이면 `U5_clipped=1` |
| 해시의 뜻 | 값만 바꾸면 `unit_id` 는 같고 `unit_hash` 가 다르다. 항목이 하나 늘면 그 단위의 `unit_id` 만 바뀐다 |
| 동형 묶음 | 같은 이동 12건 → 한 묶음 줄에 참조 12개 전부 |

**저장(`test_units_store.py`).** no-op 재빌드, rev 증가와 `rev_last` 유지, `ux_rr_unit_builds_active` 가 활성 둘을 막는다, 실패 빌드가 활성을 바꾸지 않는다, `manifest_items` 가 검토 대상 단위를 전부 덮고 항목마다 `digest_max` 안이다, `line_index` 가 문맥 줄도 돌려준다.

**snap(`test_units_snap.py`).** 간섭 전수, 임계 초과 clearance 의 집계 건수, 규칙 적중 refs 전부, 상태 없음 → `failed`.

**꾸러미(`test_unit_evidence.py`).** A 층이 그 단위 부품의 계면을 전부(변경 없는 것 포함) 싣는다, 실호출 인자가 계획표와 같다(LLM 없음), 성공·`unknown tool`·기한 초과·자격 없음 각각의 `evidence_status` 와 `evidence_gaps_json`, 서비스 자격의 빈 응답에 `suspect_scope`, 자격 순서(요청자 → owner → 서비스 → 없음), 동결 뒤 `ensure` 재호출이 본문을 바꾸지 않는다, 재기동 흉내(절반만 쓰고 다시 호출)에서 이미 받은 호출을 다시 내보내지 않는다, 쓰기 PAT 를 읽지 않는다.

**신호(`test_unit_signals.py`).**

| 단언 | 방법 |
|---|---|
| 단조성 | 임의의 신호 결과 조합(전수 3^n)에서 어느 신호를 hit 로 바꿔도 det 가 miss 쪽으로 가지 않는다 |
| miss 의 조건 | det='miss' ⇔ 양방향 신호 전부 miss 이고 forced 가 없다 |
| blind | 역할 미상 부품, 카드 묶음 없음, 게이트웨이 실패가 각각 blind 를 낸다 |
| 강제 포함 | Tier A·snap·전역·1인 영역·필터 off |
| 점수 미사용 | `unit_signals` 소스의 AST 에서 'score' 키를 읽는 식이 없다. 응답의 `score` 를 0 과 0.99 로 바꿔도 결과가 같다 |
| 경계 승계 | 경계 단위의 det 가 양쪽 묶음의 합집합 |

**로스터·플래너(`test_planner.py`).** 기본값 불변, `defer_absent=False` 에서 deferred 0·`input_gaps_json`, `review_order` 가 `PLAN_SIZES`(plan §6.3 의 로스터 규모, 합 359명)에서 A 15·B 누적 114·전체 359 이고 두 번 불러 같다, `undefer` 전이·감사·도는 잡이 있으면 409.

**러너(`test_runner.py`).** `unit=None` 바이트 동일, `unit` 이 있으면 EU·EP·질문 낱말·12칸 이하, `omitted` 가 돌아온다.

### 5.2 통합 시험(임시 DB, 프로세스 안)

합성 쌍을 `ir_builder.freeze_snapshot` 으로 두 스냅샷에 얼리고 실제 `create_diff` → `POST /targets(flow='cells')` → 단위 저장 → 매니페스트 → `manifest_items` → 가짜 게이트웨이로 `unit_signals.compute` → `unit_evidence.ensure` → `review_payload` → `panel_evidence` 까지 한 줄로 잇는다(`tests/test_e2e_smoke.py` 의 방식). 단언은 타깃 응답의 `units`·`cells_estimate`, 로스터 deferred 0, 반출 → 빈 DB 들여오기 → 같은 매니페스트다.

### 5.3 실주행 — dev 에 실제 다건 diff 가 없다는 것을 넘는 법

dev 원장에는 자기 자신과 비교한 빈 diff 뿐이다. 세 갈래로 넘는다.

1. **dev · 실제 빈 diff.** 그 타깃에 `POST /targets/{key}/units` → `status='empty'`, 단위 0. 실 DB 에서 빈 입력 경로를 확인한다.
2. **dev · 합성 쌍을 실제 경로로.** `hwax-risk dev-seed-pair --parts 640 --mutations 300 --seed 7` 이 fixture 과제(`corpus_excluded=1`, `excluded_reason='fixture'` — rr_projects 에 이미 있는 열)에 합성 스냅샷 둘을 얼리고 실제 `create_diff`·`POST /targets` 를 탄다. 그 뒤는 실물과 같은 코드다 — 단위·꾸러미(A 층)·신호(실제 게이트웨이의 `recommend_agents`·`fts_search`)·WP3 의 Tier A 15명. 확인할 것은 U1·U2 = 0, 단위 수와 크기 분포, 빌드 시간, 꾸러미 글자 수, 신호의 hit·blind·miss 분포(특히 blind 비율)다. 합성 부품명은 역할 낱말을 섞어 짓는다. 이 명령은 fixture 과제 밖에는 쓰지 않고 코퍼스(선례·통계)에서 빠진다.
3. **cae00 · 실제 과제의 diff.** 운영에는 실사용 타깃이 있다. 기존 diff 타깃에 `POST /targets/{key}/units` 만 돌린다(LLM 호출 0, 패널 흐름에 영향 없음). 여기서 처음으로 실제 분포를 잰다 — 항목 수, `lower_only_n`(지금까지 좌석에 가지 않던 변화), `tol_unknown` 건수, 역할 미상 비율, 단위 수. 이 숫자로 상한과 자산 seed 를 조정한 뒤에 WP3 를 켠다.

실주행의 합격선. 불변식 위반 0, `U5_clipped` 0, 빌드 5초 안(1,500 리프 기준), 사람이 단위 요약 셋을 읽어 실명·수치·부호가 원본 diff 와 맞는지 대조한다(`GET /api/diffs/{id}` 와 나란히).

---

## 6. 위험과 완화

| # | 깨질 수 있는 경우 | 완화 |
|---|---|---|
| 1 | **경합** — 타깃 생성과 수동 재빌드가 동시에 돈다. | 계산은 트랜잭션 밖(순수), 저장은 `store.tx()`(BEGIN IMMEDIATE) 하나. 트랜잭션 안에서 활성 빌드의 `input_hash` 를 다시 읽어 같으면 쓰지 않는다. 부분 유니크 인덱스가 활성 둘을 막는다. |
| 2 | **재기동** — 빌드 도중·꾸러미 도중. | 빌드는 한 트랜잭션이라 반쪽이 없다. 꾸러미는 단위마다 한 트랜잭션이고 `evidence_status` 가 NULL 인 단위가 남으면 다음 `ensure` 가 잇는다. 받은 원문은 `rr_brief_calls` 에 있다. |
| 3 | **부분 실패** — 실호출 일부 실패, 게이트웨이 불통. | 꾸러미는 `partial` 로 동결하고 줄에 사유를 적는다. 신호는 그 신호만 `blind`(포함 쪽). 단위 생성은 네트워크를 쓰지 않는다. |
| 4 | **큰 입력** — 리프 1,500·계면 6,000, 변형 수천. | 합성 1,500부품의 `diff_json` 9.2MB 파싱이 46ms, 1,200부품·2,102항목의 묶기가 13ms 였다. 단위 수는 `oversize` 로 드러내고 버리지 않는다. 대량 추가·삭제는 대개 대응 실패(G2)의 신호라 머리 줄이 same-as 확정을 먼저 권한다. 동형 묶음 표기가 반복 변화를 접는다. |
| 5 | **빈 입력** — self-diff, 상태 없는 스냅샷. | `empty`·`failed(state_absent)` 로 구분해 적고 잡이 시작되지 않게 한다. 전역 단위를 억지로 만들어 359회를 쓰지 않는다. |
| 6 | **옛 데이터** — 옛 `diff_json` 에 버킷이 없거나 모르는 버킷이 있다. | 버킷은 전부 `.get(...) or []`. 모르는 버킷은 전역 단위가 소유한다. U1 의 기준이 독립 순회라 수집 코드가 모르는 층도 미배정으로 잡힌다. |
| 7 | **박스 차이** — cae00 은 리포 루트가 다르고 env 는 매니페스트로만 닿는다. dev LLM 은 16K 창이다. | 경로를 쓰지 않는다(자산은 패키지 안). 손잡이는 `launch.env`. 상한이 박스마다 다르면 단위 id 가 달라지지만 DB 가 박스마다 따로라 섞이지 않는다. 16K 창에서의 분할은 WP3 의 덱 분할 몫이다(단위 상한은 글자 수로만 건다). |
| 8 | **cid 충돌** — 브리지가 살아나면 같은 cid 가 두 항목에 붙는다(2.1). | 생성기는 두 항목을 같은 원자에 싣고 센다. 인용 대조는 그 cid 의 줄 전부를 후보로 본다. 근본 수리(cid 공식에 소스 종류를 넣기)는 `DIFF_VERSION` 이 바뀌는 일이라 WP1·WP5 에 넘긴다. |
| 9 | **G2 로 막힌 diff 가 영구히 막혀 있다** — diff 재계산 경로가 없다. | 단위는 아래 두 층으로 서고 주의 줄을 단다. same-as 확정 뒤 diff 를 다시 만드는 길은 이 꾸러미 밖이다(dependencies). |
| 10 | **신호가 틀려 누락** — 역할 표가 얇거나 틀리다. | 신호는 포함만 시킨다. 틀린 표는 hit 을 덜 만들 뿐이고, 역할 미상이면 blind 다. 제외는 전문가 자기판정과 AND 이고 Tier A 대조·표본 재검토(WP3)가 놓침률을 잰다. 첫 운영은 필터를 끄고 시작할 수 있다(결정 3). |
| 11 | **꾸러미의 실호출이 스냅샷과 다른 세대를 읽는다.** | 기본은 동결본이다. 실호출은 캡처에 없던 도구로 한정하고 구획 머리에 '지금 상태' 를 적는다. `list_interfaces` 실호출은 기본 꺼짐이다. |
| 12 | **서비스 계정 시야의 빈 응답이 '없음' 으로 굳는다.** | 자격을 꾸러미에 적고 서비스 자격의 빈 결과는 따로 표기한다(3.8.2). |
| 13 | **부품명 인젝션·린터.** | 원천 문자열은 칸마다 위생 처리·«…». 코드 낱말은 어휘 밖. 빌드가 `assert_clean` 을 강제한다(U4). |
| 14 | **빌더 판이 오르면 단위 id 가 바뀐다.** | id 는 소유 참조 집합의 해시라 묶음이 그대로면 유지된다. 바뀐 단위는 새 행이고 옛 행은 남는다. 셀이 있는 타깃의 재빌드는 `force`+감사다. 전문가가 이미 본 참조는 `ref_index` 로 셀 수 있다. |
| 15 | **단위가 인과 사슬을 가른다** — 원인과 결과가 다른 묶음에 있다. | 경계 단위, 양쪽 문맥 반복, `links`(이웃·근접), 전역 단위의 단위 목록 줄. 2홉 이상은 WP4 의 교차 셀 몫이다. |
| 16 | **보류를 풀면 종전 타깃의 완결 수준 계산이 달라진다.** | `undefer` 는 사람이 타깃마다 부르고 감사에 남는다. 도는 잡이 있으면 거절한다. 달라지는 식(ECAD 영역의 need)을 응답에 미리 보여 준다. |
| 17 | **MCP L2 경로의 JS 상한(항목 2,000자·12건)에 EU 가 잘린다.** | `panel_evidence(item_max=…)` 로 나눠 준다. 그래도 12건을 넘는 조합은 WP4·WP5 가 JS 정본을 같이 고쳐야 한다(dependencies). |
| 18 | **마이그레이션 번호 충돌** — 여러 꾸러미가 같은 버전 블록에 문장을 더한다. | 커밋마다 새 번호. 이미 나간 블록은 고치지 않는다(2.8). |
| 19 | **요약·꾸러미가 폐기·반출에서 빠지거나 남는다.** | 3.2 의 세 등록 지점과 시험(커밋 3). |
| 20 | **snap 의 임계값(0.2mm)이 고른 것 밖에 문제가 있다.** | 고르지 않은 것은 집계 줄로 건수·분포를 싣고 임계값을 단위에 적는다. 전량 모드 손잡이가 있다. |

---

## 7. 다른 꾸러미와의 계약

### 7.1 내가 받는 것

| 누구 | 무엇 | 없으면 |
|---|---|---|
| WP1 | 공용 표기 함수(`render.split_trailing_refs`·`humanize_refs`·`norm_quote`, `brief.name_index`·`event_order`)와 `canonical_text_for` 의 이름 치환. `roster.query_text` 는 WP1 이 먼저 고치고 이 꾸러미가 '단위 구절이 있으면 그것을 쓴다' 를 얹는다. | 같은 시그니처로 이 꾸러미가 넣는다(먼저 들어가는 쪽이 넣는다). |
| WP1 | (권고) 어댑터가 tol 해시를 읽게 하는 수리. | 계면 수치 변화가 전부 `단서=tol_unknown` 으로 실린다(빠지지는 않는다). |
| WP3 | `card_vocab(store, agent_key, pack_hash) -> {"tokens": set[str], "n_cards": int} \| None` — 동결한 카드 묶음(`rr_card_packs`)의 제목·태그 어휘. 그리고 `GET /card-review/limits`(WP3a). | S-card 가 blind 다. limits 가 없으면 설정값 상한으로 돈다. |
| WP3 | 셀 표가 `for_cell` 반환을 얼릴 열(WP3b 초안의 `route_det`·`na_basis_json`), `unit_hash`·`evidence_sha` 를 적을 열, 셀 상태 `no_input`. 재빌드 때 그 타깃의 셀을 비우는 `reset_review`. | — |
| WP3 | 검토 잡이 격자를 만들기 전에 limits 를 읽어 필요하면 단위를 다시 만들고(3.13), 첫 셀 전에 `unit_evidence.ensure`·`unit_signals.compute` 를 부른다. 빌드 `status ∈ {empty, failed}` 면 시작하지 않으며 `oversize` 면 동의를 받는다. | — |
| WP4 | `close_level` 이 `rr_coverage.reason LIKE 'no_input:%'` 를 '검토함' 에서 빼고 입력 결손 전문가를 strong 분모에서 뺀다. 제외 단위의 사유별 건수와 '입력이 오면 확인할 것' 을 보고서에 싣는다. | — |
| WP4 | 쟁점 패널이 `SpecContext.call_ids` 에 꾸러미의 `call_ids` 를, `unit_lines` 에 `units.line_index` 를 넣는다. | `tool:b-…` 인용이 dangling 이 된다. |
| WP5 | 마이그레이션 번호 배정, `HWAXRISK_REVIEW_FLOW` 전환 시점, 매니페스트 손잡이, 문서. | — |

### 7.2 내가 주는 것

| 받는 쪽 | 표·필드·함수 |
|---|---|
| WP3·WP4·WP5 | 표 `rr_unit_builds(target_key, rev, status, active, mode, blocked_by, stats_json, invariants_json, …)`, `rr_units(target_key, unit_id, kind, reviewable, seq, scope_key, split_from, semantic_blocked, title, digest, n_changes, cids_json, context_json, lines_gz, summary_gz, summary_sha, summary_chars, signature_json, sig_hash, unit_hash, flags_json, signals_json, evidence_*, …)` |
| WP3 | `units.load_units`(=`list_units`) · `units.manifest_items` · `units.part_roles` · `units.unit_domains` · `units.review_payload(target_key, unit_id, agent_key)` · `units.ref_index` · `units.line_index` |
| WP3 | `unit_signals.for_cell(target_key, unit_id, agent_key, card_vocab=…, last_check=…)` → `{det, forced, hits, blind, miss, values, input_gaps}` |
| WP3 | `planner.review_order(target_key)` → `[{order, agent_key, domain, rank_in_domain, tier, input_gaps}]` · `planner.input_gaps` · `rr_roster.input_gaps_json` |
| WP3 | `unit_evidence.ensure(store, settings, target_key, credential_sub=…)` · 입력 결손 두 질문(`review_payload.questions`)과 응답 계약(`input_gap{q1,q2}`) |
| WP4 | `units.panel_evidence(target_key, unit_id, refs=…, budget_chars=…, item_max=…)` · `runner.panel_question(…, unit=…, issue=…)` · `runner.build_delib_opts(…, unit=…, issue=…)` |
| WP4 | `rr_units.context_json.links[{unit_id, via, n}]` · `signature.role_pairs`·`neighbor_roles`·`near_roles` · 전역 단위(kind='global') · 제외 회계(`stats_json.excluded_by_reason`) |
| WP4 | `planner.undefer` · `rr_coverage.reason='no_input:<gap>'` 규약 |
| WP5 | 새 env 15개(3.13), 등록 지점 셋(반출·이양·폐기), MCP 도구 `risk_get_units`, v3 초안에 넣을 열(7.3 의 2) |
| 프론트(다른 세션) | `GET /api/targets/{key}/units` · `/units/{unit_id}?part=` · `POST /units` · `POST /units/evidence` · `POST /undefer` · coverage·targets 응답의 추가 필드 |

### 7.3 공통 계약 초안에서 바꾸자는 것

1. **표 추가 `rr_unit_builds`.** 초안에는 `rr_units` 뿐이다. 빌드 상태(empty·oversize·failed), 불변식 결과, 차단 사유, 쓴 상한, 재빌드 이력을 둘 머리 행이 필요하다.
2. **`rr_units` 에 열을 더한다.** WP5a 통합 초안의 열 이름은 그대로 쓰고 `[wp2+]` 열(3.2)을 더한다 — `rev_first`·`rev_last`·`reviewable`·`scope_key`·`split_from`·`semantic_blocked`·`digest`·`sig_hash`·`n_parts`·`context_json`·`flags_json`·`lines_gz`·`evidence_json`·`evidence_frozen_at`·`signals_json`·`signals_status`.
3. **열 추가 `rr_roster.input_gaps_json`.** `no_input` 이 될 수 있는 전문가를 로스터 동결 때 얼린다.
4. **'제외 단위' 의 뜻을 좁힌다.** 제외 단위는 검토하지 않는 것만 모은 곳이다(`reviewable=0`). 비교 잣대가 불확실해 diff 가 제외 사유를 붙인 항목(`tol_unknown` 등)은 제외 단위가 아니라 그 부품의 묶음에 단서 줄로 싣는다(3.4.1). 부품 키가 없어도 범위가 한 묶음 안인 롤업은 그 묶음이 소유한다.
5. **셀 상태 `na_irrelevant` 의 조건을 못 박는다.** `route.det == 'miss'` 일 때만 허용한다(`hit`·`blind`·forced 에서는 쓸 수 없다).
6. **`no_input` 의 정의.** 입력 결손 전문가가 `noinput` 호출의 질문 1 에 영향(`yes`)을 하나도 내지 못한 셀이다. 영향을 냈으면 검토한 것이고 입력 결손 표기만 남는다. `rr_coverage` 롤업은 `abstain` + `reason='no_input:<gap>'` 이다.
7. **인용 스킴을 늘리지 않는다.** 단위를 가리키는 새 참조 스킴(`u:`)은 만들지 않는다. 인용은 항목 참조(`c:`·`e:`·`p:`…)로만 하고 단위는 JSON 필드의 `unit_id` 로만 오간다(REF_SCHEMES·린터·정규식 넷을 고치지 않아도 된다).
8. **'근거 꾸러미' 는 `evidence_*`, 전문가 카드 묶음은 `pack_*`.** 두 말을 섞지 않는다.
9. **이미 적용된 마이그레이션 블록에 문장을 덧붙이지 않는다.** v3 한 블록(WP5a)이 나간 뒤에 생기는 열은 v4 다.

### 7.4 다른 설계서 초안과 맞춰 본 것

같은 폴더에 다른 꾸러미의 설계서 초안이 쓰이고 있어(작성 중인 것도 있다) 나를 가리키는 줄만 grep 으로 읽고 맞췄다. 남은 차이는 다음과 같다.

| 상대 | 그쪽 초안 | 이 설계 | 제안 |
|---|---|---|---|
| WP3a | 단위는 `{unit_id, kind, title, summary, lines[{ref, text}], evidence[{ref, text}], notes, missing}`, 크기 식과 `unit_body_max`, 목록 항목 800자 | 그 모양으로 맞췄다(3.10.4·3.13·3.7.1). 전문 패킷은 두지 않는다 | 맞음. 남는 물음 — 전수 훑기가 800자 요약만 보고 '무관' 을 정한다. 그래서 `det='miss'` 일 때만 닫히게 했다 |
| WP3a | `noinput` 호출이 두 질문의 정본 | 누가 그 길로 가는지와 `missing`·실마리만 준다(3.10.2) | 맞음 |
| WP3b | 단위는 `units.load_units`, 신호는 `relevance.signals()`. `no_input` 은 훑기 분류(`det='miss'` 이고 훑기가 '입력이 없다' 고 했고 그 입력이 실제로 없다)에서만 난다 | `load_units` 를 더했다. 신호 함수 이름은 `unit_signals.for_cell` 이다. `no_input` 은 `noinput` 호출의 결과로도 난다 | 함수 이름을 하나로(`unit_signals.for_cell`). `no_input` 으로 가는 문을 둘 다 두되 '입력이 실제로 없음' 의 코드 확인은 WP3b 규칙을 쓴다. `det` 이 `hit`·`blind` 인 입력 결손 전문가는 `noinput` 호출로 간다 |
| WP3b | 단위를 다시 만들면 `reset_review` 가 그 타깃의 셀·판정을 지운다 | 옛 단위 행을 남기고(`rev_last`) 재빌드에 `force`+감사를 건다 | 맞음. limits 때문에 다시 만드는 것은 격자 전이라 지울 것이 없다 |
| WP4 | `rr_targets.flow`(`panels`\|`cells`) 를 그쪽이 더한다. kind 는 `snap_unit`. `units.list_units`·`part_roles`·`unit_domains` 를 기대한다 | 그 이름·값으로 맞췄다 | 맞음. 열은 한 번만 더한다 |
| WP4 | 쟁점 패널의 질문·브리프는 `issues.issue_question`·`build_issue_brief` | `panel_question(unit=…)`·`build_delib_opts(unit=…)`·`units.panel_evidence` | 구현은 하나로 — `issue_question` 이 단위 머리 문구를, `build_issue_brief` 가 `units.panel_evidence` 를 쓴다. `panel_question(unit=…)` 은 만들지 않아도 된다 |
| WP5a | 재설계 표 전부를 v3 한 블록, 어휘는 CHECK 없이 | CHECK 를 뺐다. 열 이름을 맞췄다 | 내 열(7.3 의 2)을 v3 초안에 넣는다 |
| WP5b | 단위 계약 U1~U9·S1(`tests/rr/test_units_contract.py`). U3 = 제외 사유가 붙은 것은 전부 `excluded`, 부품 키 없는 것은 전부 `global`. U9 = 본문 첫 5줄 안에 절대 크기 1위의 감소 변화 | 제외 사유는 처리표에 따라 갈리고(단서 줄 / 제외 단위), 범위가 한 묶음 안인 롤업은 그 묶음이 소유한다. 순서는 원자 단위의 `event_order` 다 | U3 을 '처리표대로' 로, U9 를 '첫 5개 원자 안' 으로 고친다. 변경→영역 표의 키가 `change_kind` 14종이라는 것은 같다(`contact_type`·`parameter` 포함) |
| WP1 | `render.split_trailing_refs`·`humanize_refs`·`norm_quote`, `brief.name_index`·`event_order` 를 준다. R-32(택소노미에 `contact_type`·`parameter` 추가)·R-54·R-56 을 이 꾸러미로 넘겼다 | 줄 몸통·순서·인용 대조가 그 함수에 기댄다. R-54 는 3.10.1, R-56 은 3.9.2(S-mech)·3.10.1(`risk_mcad_domains`)에서 받았다. R-32 는 커밋 2 에 넣었다 | WP1 이 먼저 병합된다. 아니면 그 순수 함수 다섯을 이 꾸러미가 같은 시그니처로 넣는다 |

---

## 8. 사용자가 정해야 하는 것

| # | 정할 것 | 권고 기본값 | 까닭 |
|---|---|---|---|
| 1 | 새 흐름 타깃의 기본 마감을 전원(C3)으로 할지, 지금처럼 114명(C2)에서 닫을지. | 전원. A(15명)·B(114명)는 중간 점검 지점으로 남긴다. | '모든 전문가에게서 보고서' 가 목표다. 지금 C2 는 계획 문서도 '비용에 대한 타협' 이라고 적었다(plan.md:3656). 호출 수는 반박 검토에서 지금 범위 안으로 계산됐다. |
| 2 | 비교 잣대가 불확실해 제외된 수치 변화(`tol_unknown` 등)를 전문가에게 단서를 달아 보여 줄지. | 보여 준다(묶음 안에 `단서=` 줄). 캡처 실패·범위 밖·메시 밀도는 제외 단위에만 둔다. | 지금은 어댑터가 잣대 해시를 읽지 않아 간극·접착 띠·관통 변화가 전부 여기에 든다. 숨기면 가장 중요한 변화가 아무에게도 가지 않는다. 단서를 달면 잘못된 확신도 막는다. |
| 3 | 신호와 전문가 자기판정이 둘 다 '무관' 일 때 '해당 없음' 으로 건너뛰게 할지(첫 운영값). | 첫 실제 타깃 한두 건은 끈다(전 셀 깊이 검토). Tier A 대조로 놓침률을 잰 뒤 켠다. | 역할 표와 신호의 실제 성능을 아직 모른다. 반박 검토는 거르지 않아도 호출 수가 지금 범위 안이라고 계산했다. |
| 4 | 부품 역할→영역 표, 변경 종류→영역 바닥 표, 회로 영역별 실마리 문안을 누가 확정하나. `sh` 영역이 무엇인지도 여기서 정한다. | seed 로 시작하고, 첫 실주행에서 나온 '역할 미상 부품 목록' 을 보고 사용자(또는 지정한 담당)가 확정한다. | 영역 지식이 필요한 표다. 다만 신호가 포함만 시키므로 seed 가 틀려도 누락으로 이어지지 않는다 — 확정을 기다리느라 막을 필요가 없다. |
| 5 | 운영에 이미 열린 타깃의 보류 104명을 풀지. | 새 타깃부터 적용한다. 기존 타깃은 그대로 두고, 원하는 타깃만 사람이 `undefer` 한다. | 도는 중인 심사의 완결 수준 계산이 바뀐다. 자동으로 풀면 끝난 줄 알았던 타깃이 다시 열린다. |
| 6 | snap(현황) 타깃을 신호에 걸린 항목 중심으로 볼지, 전 부품·전 계면을 다 볼지. | 신호 항목 전수 + 나머지는 조립별 집계 줄. | 리프 1,500·계면 6,000 을 다 항목으로 실으면 단위가 수십 개 늘고 셀이 만 단위로 는다. 신호 항목은 상위 10건이 아니라 전부 싣는다. |
| 7 | 근거 꾸러미에서 '지금 상태' 를 읽는 실호출을 어디까지 허용할지. | 캡처에 없던 도구(`compare_reports`·재질 조회)만. 계면 실호출은 끈다. | 스냅샷과 다른 세대를 섞으면 전문가가 본 숫자의 출처가 흐려진다. 같은 과제의 리비전 비교에서는 base 상태가 소스에 없다. |

---

## 9. 확인하지 못한 것

- **실제 diff 의 분포.** 항목 수, 조립 깊이, 조립을 가로지르는 계면의 비율, 역할 미상 비율. 단위 수 표(3.4.3)는 합성 입력에서 잰 값이고 합성기는 조립 사이 계면을 일부러 많이 넣었다. 실제 값은 5.3 의 3번에서 처음 나온다.
- **cae00 배포판이 dev HEAD 와 같은지.** 줄 번호와 동작은 dev HEAD 기준이다.
- **브리지(dyna pid ↔ mcad 부품)가 살아난 실제 스냅샷에서 cid 충돌이 얼마나 나는지.** 충돌 자체는 픽스처의 dn 을 손으로 묶어 메모리에서 재현했다. 실제 브리지 스냅샷은 보지 못했다.
- **게이트웨이를 거친 `recommend_agents(top_k≈400)` 의 응답 크기와 지연, 게이트웨이의 응답 한도.** AIDataHub 코드에는 top_k 상한이 없다는 것만 확인했다(네트워크 호출을 하지 않았다).
- **`fts_search` 가 한국어 낱말에 얼마나 걸리는지.** `'simple'` 설정이라 형태소를 모른다는 것과 OR 재시도가 있다는 것만 코드로 확인했다. 재질 코드·영문 역할명에는 걸릴 것으로 보지만 추정이다.
- **`compare_reports`·`compare_materials`·`get_material` 의 응답 모양.** 시그니처는 확인했다(`compare_reports` 는 KooRemapper 의 빌드 작업본 경로에서 — 배포판과 같은지 모른다). 재질 도구의 인자 이름(`names`·`name`)은 확인하지 못했다. 렌더러와 호출 계획의 인자 키는 구현 때 게이트웨이 `tools/list` 로 맞춰야 한다.
- **StepForge `list_interfaces(part=…)` 의 글롭이 특수문자·공백이 든 부품명에서 어떻게 도는지.** 그래서 계면 실호출을 기본 꺼짐으로 뒀다.
- **`rr_snapshot_calls.response_gz` 가 성공한 스냅샷에서 계속 남는지.** 실패·부분 잡은 30일 뒤 비운다는 주석만 확인했다. 꾸러미 A 층은 원문이 아니라 IR 표에서 만들므로 영향이 없지만 `tool:<call_id>` 인용의 원문 확인에는 영향이 있다.
- **`sh` 영역의 뜻.** 택소노미 label 이 'SH' 이고 좌석 계약은 disp 와 같은 줄이다. 역할 표에 대응을 비워 뒀다.
- **다른 꾸러미 설계서의 최종판.** 같은 폴더의 초안(WP1·WP3a·WP3b·WP4·WP5a·WP5b)에서 나를 가리키는 줄만 grep 으로 읽고 맞췄다(7.4). 쓰이는 중인 것도 있었다(WP3b 는 계약 절이 아직 없었다). `unit_body_max` 12,126자·목록 항목 800자는 WP3a 초안의 예시값이고 구현 뒤 실측으로 바뀐다고 그쪽이 적었다. 같은 함수(`roster.query_text`·`narrative.resolve_cites`·`runner.build_delib_opts`)를 여러 꾸러미가 고친다.
- **줄 기준 상한(20·40줄, 7,000자)에서의 실제 단위 수.** 3.4.3 의 표는 초안의 묶음 수 기준이다. 1.5~1.7배는 추정이다.
- **프런트엔드가 `…(n줄 생략)` 이나 새 응답 필드를 어떻게 보여 주는지.** `frontend/` 를 읽지 않았다.
- **포털·nginx 의 요청 본문 한도.** 패널 근거 6,000자는 지금 브리프(약 10,600자)와 같은 자릿수라 문제없을 것으로 보지만 재지 않았다.
- **`tests/test_planner.py` 밖에 `deferred` 의 불변을 전제하는 시험·화면이 더 있는지.** planner 시험 두 곳(522·553행)과 plan.md 한 줄만 확인했다.
- **합성 스냅샷을 `freeze_snapshot` 으로 얼릴 때 걸리는 게이트(G1~G6)와 모델 상한.** 합성기는 `compute_diff` 에 직접 넣어 확인했고 저장 경로로는 돌려 보지 않았다(DB 에 쓰지 않았다).
