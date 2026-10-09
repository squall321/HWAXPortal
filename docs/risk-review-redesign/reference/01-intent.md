# 현재 구조 — 코드 대조 + 반박 검증 결과 (2026-10-08, dev HEAD: HWAXRisk 7248651 · HWAXAgentServer 7683125)

## 계획 문서의 의도 (intent)

### 검증 반영 최종 답
계획은 패널의 심의 대상을 타깃 전체, 곧 스냅샷 한 장(`snap:`) 또는 diff 한 건(`diff:`) 통째로 정했고(plan.md:48·3353), 코드도 타깃 kind 를 'snap'·'diff' 둘로만 받으며 커버리지를 PK(target_key, agent_key)로 묶는다(risk_store.py:232·262). 패널 질문은 한 물리 현상이 아니라 '변경(또는 현황)이 각 도메인에서 어떤 리스크와 개선을 낳는가'이고(runner.py:372-377), 계획이 가른 축은 영역이 아니라 도메인 관점이다(15도메인 약 350석, 패널마다 서로 다른 도메인 4석과 인접 도메인 1석, 기준선 옹호 지정석 1석). 영역·변경 군집·서브시스템 단위로 패널이나 브리프를 가르는 안은 검토·기각·보류 기록이 없고, 가까운 기록은 scope 자동 축소를 기본에서 뺀 §10 #39, evidence 12칸 상향을 접어 둔 §10 #40, 카탈로그 MCAD-09(파트별 구역·층, 질문 예 '변경이 제품의 어느 구역·어느 층에 몰려 있나', 스냅샷 미수집)와 MCAD-61(검출 scope, scope_out 생산자가 없어 G5 무력), S26U 실사용 요청 '리스크 앱 근거 12 → 40' 을 CAPS 재배분이 필요하다며 하지 않은 것(docs/delib-engine-feedback/PLAN.md:79)이다. 350석을 한 번씩 앉히는 회계는 사용자 원 요구('과제/과제쌍 심사를 한 전문가는 한번 하면 넘어가게 … 전체 HW/XD 가 한번씩')를 그대로 옮긴 것이고 타깃이 로스터·커버리지·등록부·verdict 와 C1~C3 완결 판정의 단위라서 전원이 같은 타깃을 보는데, 분할안과 견줘 논증한 문장은 없으며 문자적 충족은 C3(ECAD 있으면 71패널, 계획 추정 12~21 GPU-h/타깃)이고 기본 마감은 C2 다. 변경점이 매우 많은 과제에 대한 방침은 없고 절단 규칙만 있어서, 변경 내용 네 항목의 라인 상한 합은 4,050자(E1 1650·E2 1100·E3 700·E4 600, 오버헤드 포함이고 E1 은 E2~E4 와 겹친다)이며 브리프가 결정론이라 같은 타깃의 모든 패널이 똑같이 잘린 같은 부분을 본다. 잘리는 순서도 중요도순이 아닌데, E2 는 부호 있는 magnitude 내림차순이라 얇아짐·좁아짐 같은 음수 변화가 먼저 잘리고(brief.py:484-488), E1 [의미]는 change_kind 별 앞 5건이 (code, cid 해시) 순이며(diff.py:1498), E3 은 계획의 '여유 오름차순'이 구현되지 않아 치수 이름순이다(diff.py:1128). 좌석이 잘린 나머지를 읽을 길도 러너 경로에는 없어서, 러너가 여는 앱은 StepForge·DynaForge 둘뿐이라 `risk_get_diff` 가 좌석 도구에 없고(runner.py:302-310, deliberation.py:733-745) 자유조회는 소스의 지금 상태를 라운드당 3회(합 6회), 호출당 900자·블록 3,500자로 읽는다. 이 4,050자의 전제였던 '엔진 12칸·11,000자'는 엔진 HEAD 에 더는 없고(120건, 항목당 150,000자, 합계는 컨텍스트 유도·천장 500,000자 — deliberation.py:175·176·194) 지금 막는 것은 리스크 앱 자신의 표다(brief.py:18-19·29-31, planner.py:27). 규모 쪽 문은 모델 크기 하나(리프 1500·계면 6000 초과 시 409 model_too_large 후 allow_large)이고, 대응이 불확실한 파트가 1건이라도 있으면 G2 가 pair 의미 이벤트를 통째로 0건으로 만든다(diff.py:1241-1243). 계획이 변경을 좁혀 다루는 장치는 리비전 사이에만 있어서 changed_ckeys 와의 교집합으로 등록부 클러스터를 stale 로, 좌석을 carried 로 넘기고(§4.8, plan.md:2003), 서브어셈블리 키(asm_key·rollups.by_assembly·rollup_delta)는 이벤트 한 줄(asm.rollup_changed)과 finding 주체로만 쓰인다. cad-capabilities.md 에서 좌석에 닿는 변경 정보량과 닿는 항목은 좌석 통로(141종 중 32종), tol 해시 미독(간극·접착 띠·관통 변화 이벤트 전부 제외), E0 절단(10-08 수정, 상한 500 은 두고 남는 자리를 빌려 준다), 좌석 도구가 얼린 판이 아닌 지금 상태를 읽는 것, dev 원장에 실제 리비전 쌍이 0건이라는 것이다. 따라서 영역별 분석은 기각된 안이 아니라 다뤄진 적 없는 안이며, 영역을 타깃으로 만들면 PK 때문에 350석 회계가 영역 수만큼 곱해지므로 타깃은 두고 브리프와 질문을 가르는 쪽이 계획의 회계와 덜 부딪친다는 것은 계획에 없는 추론이다.

### 바로잡은 것
- 'E3 은 700자 안에서 여유 오름차순으로 잘린다'는 계획 문구(plan.md:3167)일 뿐 구현이 아니다. `_item_e3`(HWAXRisk/backend/app/brief.py:509-539)에는 limit·margin 열도 정렬도 없고 dims_delta 는 치수 이름순이다(diff.py:1128). 넘치면 이름 뒤쪽 치수가 잘린다.
- '넘치는 변경은 크기순으로 떨어져 나간다'는 부정확하다. E2 의 정렬 키는 부호 있는 magnitude 다(brief.py:484-488, delta = after − before 는 diff.py:399) — 얇아짐·간극 축소 같은 음수 변화가 크기 없는 이벤트(추가·삭제·롤업 변화, 0 으로 취급)보다도 뒤에 서서 가장 먼저 잘리고, mm·rank·요소 수가 한 줄로 비교된다. E1 [의미]의 'change_kind 별 앞 5건'은 (code, cid 해시) 순이다(diff.py:1498, render.py:734).
- '라인 상한 합 4,050자'의 산술은 맞지만 그 전제가 낡았다. 계획이 근거로 든 '엔진 12항목·11,000자'(plan.md:3157·3694)는 엔진 HEAD 에 없다 — 근거 120건(HWAXAgentServer/deliberation.py:175), 항목당 150,000자(:176), 합계는 모델 컨텍스트에서 유도하고 천장 500,000자(:194), 포털 스키마도 120(HWAXPortal/backend/app/agent/routes.py:146). 지금 4,050자를 막는 것은 리스크 앱 자신의 표다(brief.py:18-19·29-31, planner.py:27 MAX_EVIDENCE=12). 또 4,050 은 오버헤드·프레이밍을 포함한 라인 상한이고 E1 은 E2~E4 와 내용이 겹친다(plan.md:3165).
- '더 보려면 자유조회에 기대야 한다'는 rr_diff 에 대해서는 성립하지 않는다. 러너가 여는 앱은 heax-step_forge·heax-kooremapper_mcp 둘뿐이고(runner.py:302-310, adapters/registry.py:26-30), `risk_get_diff` 는 앱 heax-hwax_risk 가 apps 에 있을 때만 열리며(deliberation.py:733-734·3757) `_RISK_KEEP_TOOLS`(:741-745)에도 없다. 좌석은 잘린 나머지 이벤트를 읽을 수 없고, 열린 것은 소스의 지금 상태를 읽는 도구뿐이다(호출당 900자·블록 3,500자, :3098).
- '영역별 분할 관련 기록은 카탈로그 포함 0건, zone·구역은 무관한 뜻뿐'은 틀렸다. cad-capabilities-catalog.md:128-137 의 MCAD-09(파트별 zone·layer, 질문 예 '변경이 제품의 어느 구역(코너·에지·중앙)·어느 층에 몰려 있나', 스냅샷 미수집, 프레임이 리비전 사이에 흔들리면 구역 diff 가 설계 변경으로 나온다는 경고)와 :816-822 의 MCAD-61(검출 scope{match, match_path, bbox}, 'scope_out 생산자가 없어 G5 가 무력')이 있다. 패널을 가르자는 결정은 아니지만 영역 분석의 재료로 적힌 가장 가까운 기록이다.
- '가장 가까운 기록은 둘'에서 좌석에 닿는 양을 직접 다룬 보류 기록 둘이 빠졌다. plan.md:4817 의 §10 #40(evidence 12칸 상향 — '접어 둔다(엔진 무수정)')과 docs/delib-engine-feedback/PLAN.md:51·79(S26U 실사용 요청 3-3 '리스크 앱 근거 상한 12 → 40' 을 'CAPS 재배분이 따로 필요하다'며 하지 않음), 같은 폴더 context-notes.md:23(D-4 'CAPS 산술은 손대지 않는다').
- '서브어셈블리 키와 교집합 판정은 등록부 주체와 재심 면제에만 쓰인다'는 과소 서술이다. rollup_delta 가 의미 이벤트 `asm.rollup_changed`('서브어셈블리 수준 요약', plan.md:1580, diff.py:1465-1480)와 요약 [구조]의 '롤업 변화 N'(render.py:719)으로 브리프에 실리고, 교집합은 등록부 stale 표기와 E5 접두에도 쓰인다(registry.py:765-841, brief.py:686-698). 다만 어느 것도 한 타깃의 브리프를 가르지는 않는다.
- '규모 쪽 문은 모델 크기 하나뿐'에 G2 가 빠졌다. same-as pending 이 1건이라도 있으면 pair 의미층이 통째로 차단돼 이벤트가 0건이다(diff.py:1241-1243, plan.md:1295). 이름·형상이 크게 바뀐 과제가 먼저 부딪히는 것은 이것이고, 푸는 길은 사람의 SameAsResolver 확정이다.
- '실제 리비전 쌍으로 돈 적이 없다'는 dev 원장 한정이다. cae00 실사용 팀(S26U 잠재리스크 심사)이 있고 그 패널은 근거 41~49건을 실었다(docs/delib-engine-feedback/PLAN.md:3, deliberation.py:172, 포털 routes.py:144-146) — 리스크 앱 브리프의 12칸 설계보다 서너 배 많은 양이 실제로 쓰였다.
- '기준 과제가 없는 신규 과제는 snap 타깃으로 본다'는 계획에 명시된 방침이 아니라 추론이다. 계획에 있는 것은 snap 의 정의('단일 현황', plan.md:48·3353)와 계보 없는 과제의 선례 회수(§5.9)뿐이다.

### 놓쳤던 사실
- 엔진의 근거 상한이 바뀌었는데 리스크 앱 표는 그대로다. HWAXAgentServer/deliberation.py:168-176·194 — 주석 '종전 값(항목 2,000자 · 합계 11,000자)', 현재 `_EVID_ITEMS` 120 · `_EVID_ITEM_MAX` 150000 · `_EVID_BUDGET` 500000(실제 예산은 컨텍스트에서 유도). HWAXRisk/backend/app/brief.py:16-19 는 여전히 `CLAMP_RESULT 2000` · `ENGINE_BUDGET = 11000` · `EVIDENCE_MAX_ITEMS = 12`. 좌석에 닿는 변경 정보량은 엔진이 아니라 앱 표가 정한다.
- 잘린 브리프는 결정론이라 같은 타깃의 모든 패널(ECAD 있으면 71패널, plan.md:3388)이 똑같은 부분집합을 본다. E1~E4 는 ctx 만 받고(brief.py:449-572) 정렬이 고정이다. 변경이 많으면 350석이 같은 앞부분을 반복해 보고 잘린 나머지는 0석이 본다.
- 질문과 지식카드 검색에 변경 내용이 거의 없다. 패널 질문에 실리는 요약은 앞 200자([대상] 줄)뿐이고(runner.py:358), 좌석별 지식카드 검색은 그 질문을 그대로 쓴다(deliberation.py:4095 `_agent_search_hits(tools, p["key"], question)`). 한 현상을 묻는 일반 심의와 달리 검색어가 '각 도메인에서 어떤 리스크와 개선'이라는 일반문이다.
- 1R 자유조회 단계의 문맥에서 브리프가 밀려날 수 있다. 조회 문맥은 `base[:4000]`(deliberation.py:4487)이고 base 는 질문 → 지정 도구 결과(≤5,000자) → 브리프 순으로 이어 붙는다(:4315-4319). diff 타깃은 지정 도구가 list_interfaces·interface_graph 등이라(planner.py:255-275) 그 결과가 길면 변경 표(E1~E4)는 조회 단계에 안 보인다. 조회 단계의 역할문도 280자에서 잘려(:3006) 뒤에 붙는 좌석 계약이 빠진다.
- 영역 경로로 읽힐 수 있는 유일한 장치(G5 partial_scope)는 배선이 없다. 스냅샷 요청에 scope 인자가 없고(routes.py:1125-1131), scope 는 StepForge detect 잡에서 복사만 되며(adapters/mcad.py:556·581), `scope_out` 플래그를 붙이는 코드가 앱에 없다(소비처만 state.py:252 · diff.py:118-120 · ir_builder.py:521·646). 카탈로그 MCAD-61(cad-capabilities-catalog.md:816-822)이 같은 사실을 적었다.
- 계획이 변경을 좁혀 다루는 장치는 한 타깃 안이 아니라 리비전 사이에 있다. §4.8(plan.md:2003 이하) — changed_ckeys 와 겹치는 등록부 클러스터만 stale, 인용이 안 겹치는 좌석은 carried(planner.py:759-773, registry.py:765-841). 변경 주체 단위로 재검토 범위를 줄이는 설계가 이미 있으므로 같은 키(ckey·asm_key)로 한 타깃 안을 가르는 것은 새 개념이 아니다.
- 영역을 별도 타깃으로 만들 때의 비용이 계획 수치로 나온다. 커버리지 PK 가 (target_key, agent_key) 라(risk_store.py:262) 영역 N개면 350석 회계가 N번 돈다. 타깃당 C3 는 71패널·계획 추정 12~21 GPU-h(plan.md:3388·3656)이고, 패널 벽시계 기본값은 계획의 40분이 아니라 43,200초다(config.py:60). 타깃 kind 도 CHECK 로 둘뿐이라(risk_store.py:232) 새 kind 는 스키마 변경이다.
- 좌석 통로에 StepForge 자체 비교 도구는 열려 있다. 카탈로그 :757 — 'compare_revisions·compare_snapshots·compare_part_view(좌석 열림)'. 좌석이 변경을 더 보는 실제 길은 얼린 rr_diff 가 아니라 소스의 지금 상태를 견주는 이 도구들이다(cad-capabilities.md:38 의 세대 고정 문제와 겹친다).
- 계획 §10.9 후속 백로그 46건(plan.md:4832 이하)에도 영역·변경 군집 분할은 없다. 가까운 것은 B24(cross_domain 항목의 원자 미저장)와 B35(60행 등록부의 한 장 요약)뿐이다 — '다뤄진 적 없는 안'이라는 결론을 보강한다.

### 확인된 코드 근거(파일:줄 — 인용)
- (a) 심사 대상(타깃)은 스냅샷 한 장 또는 diff 한 건 전체이고, 로스터·커버리지·등록부·verdict 가 그 단위에 묶인다. — `HWAXPortal/docs/design-risk-review/plan.md:48` — `심사 대상. `snap:<snapshot_id>`(단일 현황) 또는 `diff:<diff_id>`(기준 대비 변경). `rr_targets` 행이며 로스터·커버리지·등록부·verdict 의 소유 단위다.`
- (a) §6.1 이 메뉴의 한 줄 정의도 '정해진 타깃(snap 또는 diff)'을 전체 전문가가 본다고 적는다. — `HWAXPortal/docs/design-risk-review/plan.md:3353` — `전체 HW/XD 전문가가 정해진 타깃(`snap:` 단일 현황 또는 `diff:` 기준 대비 변경)에 대해 각자 도구를 실호출해 리스크·개선·성격을 판정한 **리스크 심사 보고서를 만든다**`
- (a) 패널에 던지는 질문은 하나의 물리 현상이 아니라 타깃 전체의 변경을 각 도메인이 판정하라는 것이다. — `HWAXPortal/docs/design-risk-review/plan.md:3557` — `기준 {base 과제코드} 대비 변경(또는 현황)이 각 도메인에서 어떤 리스크와 개선을 낳는가를 도구 근거로 판정하라.`
- (a) 계획 의사코드에서 변경 내용 항목 E1~E4 는 타깃 종류만 입력으로 받는다(패널·좌석과 무관). — `HWAXPortal/docs/design-risk-review/plan.md:3188` — `items += [E1, E2, E3, E4](target.kind)`
- (a) 계획 의사코드에서 좌석을 입력으로 받는 항목은 E0c 와 E7 뿐이다(E7 줄). — `HWAXPortal/docs/design-risk-review/plan.md:3193` — `items.append(E7(panel.seats, target))`
- (a) 실제 실행 코드도 같다 — E1 은 타깃 문맥(ctx)만 받는다. — `HWAXRisk/backend/app/brief.py:1326` — `_item_e1(ctx),`
- (a) 실제 실행 코드에서 좌석을 받는 항목은 E0c(좌석 계약표)와 E7(좌석 개인 기억)이다. — `HWAXRisk/backend/app/brief.py:1325` — `_item_e0c(seats),`
- (a) 실제 실행 코드의 E7 은 좌석 목록을 받는다. — `HWAXRisk/backend/app/brief.py:1332` — `_item_e7(store, ctx, seats, adh),`
- (a) E2 이벤트 표는 diff 전체에서 의미·구조층을 뽑으며 도메인·영역 필터가 없다. — `HWAXRisk/backend/app/brief.py:481` — `"WHERE diff_id = ? AND layer IN ('semantic','structural')",`
- (a) 좌석 편성은 도메인 라운드로빈이며 변경 내용·영역을 입력으로 쓰지 않는다. — `HWAXRisk/backend/app/planner.py:405` — `"""primary 4석(서로 다른 도메인, 잔량 최대부터 라운드로빈) + counter 1석(인접 표)."""`
- (b) 가장 가까운 기록 1 — 같은 타깃의 패널은 '같은 IR'을 본다는 전제로 직렬로 묶었다. — `HWAXPortal/docs/design-risk-review/plan.md:3405` — `타깃당 패널은 **직렬**이다(같은 IR 을 두 패널이 동시에 보면 등록부 병합 순서가 흔들린다).`
- (b) 가장 가까운 기록 2 — 모델 상한 초과 시 scope 자동 축소안(②)은 열린 질문 #39 에 있고, 잘린 것이 설계 변경으로 보일 위험이 적혀 있다(기본은 ① 409 후 명시 승인). — `HWAXPortal/docs/design-risk-review/plan.md:4808` — `② scope 를 자동으로 좁혀 부분 IR 을 만들지, ③ 상한 없이 예산만 늘릴지. ②는 무엇을 잘랐는지가 설계 변경으로 보이는 위험이 있다`
- (b) 계획의 'scope'는 StepForge 부분 검출 범위(G5)이지 패널 분할 단위가 아니다. — `HWAXPortal/docs/design-risk-review/plan.md:690` — `| scope | detect 잡 params.scope 또는 graph.json.scope 가 있으면 그대로 복사한다. non-null 이면 봉투 `partial=true`(G5). |`
- (b) 계획의 '클러스터'는 finding 병합 키(cluster_key)이지 변경 군집이 아니다. — `HWAXPortal/docs/design-risk-review/plan.md:111` — `| cluster_key | `sha1(mechanism, mechanism_detail, subject_key, change_kind)[:12]`.`
- (c) '한 번씩' 회계는 사용자 원 요구에서 왔고 그 단위가 '과제/과제쌍'이다. — `HWAXPortal/docs/design-risk-review/context-notes.md:11` — `특정 과제/과제쌍 심사를 한 전문가는 **한번 하면 넘어가게**(커버리지 회계) 해서 전체 HW/XD 가 한번씩`
- (c) 그 요구를 PK(target_key, agent_key) DB 제약으로 구현했다. — `HWAXPortal/docs/design-risk-review/plan.md:542` — `커버리지 원장 PK(target_key, agent_key)가 "한 번 하면 넘어감" 을 DB 제약으로 보장해 같은 전문가가 같은 타깃을 두 번 보지 않으며`
- (c) 계획은 전원 한 번씩의 문자적 충족이 C3 이고 C2 는 비용 타협임을 명시한다. — `HWAXPortal/docs/design-risk-review/plan.md:3656` — `사용자 요구는 "전체 HW/XD 전문가가 한 번씩" 이며 그 문자적 충족은 **C3** 다. C2 는 비용(§6.10, C3 ≈12~21 GPU-h/타깃)에 대한 타협이지 요구의 충족이 아니다.`
- (c) 패널은 6석 고정이고 350석 커버리지는 같은 타깃에 대한 회차 반복으로 채운다. — `HWAXPortal/docs/design-risk-review/plan.md:3368` — `좌석 과다 방지 원칙(sim +2·test +2)과 같은 선에서 패널당 6석 고정이고, 커버리지는 회차로 채운다.`
- (c) 같은 의견이 반복되면 버리지 않고 병합해 support 를 올린다 — 여러 좌석이 같은 대상을 본다는 전제 위의 재현성 신호다. — `HWAXPortal/docs/design-risk-review/context-notes.md:78` — `의견 같음 → 드랍이 아니라 `cluster_key` 병합으로`
- (c) Tier A 의 목적은 모든 도메인이 그 타깃을 한 번은 보는 것이다. — `HWAXPortal/docs/design-risk-review/plan.md:3385` — `| A 대표 | 모든 도메인이 한 번은 본다 | `rank == 1`(15명) | 15 | 3 | 3 |`
- (d) diff 요약은 총 2000자이고 넘치는 항목은 접는다 — 변경이 많을 때의 유일한 처리다. — `HWAXPortal/docs/design-risk-review/plan.md:1631` — `총 ≤2000자. 섹션 순서 고정이고 섹션별 상한을 넘으면 그 섹션 안에서 뒤 항목을 `… 외 N건` 으로 접는다.`
- (d) 의미 이벤트는 change_kind 별 최대 5건만 요약에 실린다. — `HWAXPortal/docs/design-risk-review/plan.md:1638` — `change_kind 별 최대 5건 `code subject before→after (unit) [c:]``
- (d) 실제 코드도 change_kind 별 앞 5건만 싣는다. — `HWAXRisk/backend/app/render.py:734` — `texts = by_kind[kind][:5]`
- (d) 실제 코드도 나머지를 '… 외 N건'으로 접는다. — `HWAXRisk/backend/app/render.py:736` — `body = " · ".join(texts) + (f" · … 외 {extra}건" if extra > 0 else "")`
- (d) E2 이벤트 표는 1100자 안에서 크기 내림차순으로 싣는다(도메인 무관). — `HWAXPortal/docs/design-risk-review/plan.md:3166` — `magnitude 내림차순 | rr_diff_events(semantic → structural 순) | 1100 |`
- (d) E3 치수 표는 여유 오름차순 정렬로 위반·근접 항목이 먼저 남게 한다. — `HWAXPortal/docs/design-risk-review/plan.md:3167` — `margin 오름차순으로 정렬해 위반·근접 항목이 잘리지 않게 한다`
- (d) 브리프 항목은 상한을 넘으면 줄 단위로 잘린다. — `HWAXPortal/docs/design-risk-review/plan.md:3209` — `절단 규칙. 줄 단위로 자르고 잘린 줄 수를 `…(n줄 생략)` 로 남긴다.`
- (d) 실제 코드의 항목별 라인 상한 — 변경 내용 네 항목 합이 1650+1100+700+600=4050 이다. — `HWAXRisk/backend/app/brief.py:29` — `"E0": 500, "E0c": 1000, "E1": 1650, "E2": 1100, "E3": 700, "E4": 600,`
- (d) 잘린 요약의 전문은 REST 로만 열린다(브리프에는 실리지 않는다). — `HWAXPortal/docs/design-risk-review/plan.md:3165` — `pair 면 `summary_text`(§3.4.2 순서 그대로, 실효 상한까지 줄 경계 절단 — 뒤 섹션 `[씨앗]`·`[재료]` 부터 `…(n줄 생략)`, 전문은 `GET /api/diffs/{id}?part=summary``
- (d) 규모에 대한 문은 모델 크기 상한 하나다(변경 건수 상한·분할은 없다). — `HWAXPortal/docs/design-risk-review/plan.md:1099` — `리프 > `risk_max_leaf`(1500) 또는 계면 > `risk_max_interfaces`(6000)면 `409 model_too_large {leaf, interfaces, caps, hint:'scope 를 좁히거나 allow_large=true 로 재요청'}` 를 내고 `
- (d) 좌석이 브리프 밖 사실을 더 보는 통로는 자유조회이고 좌석당 최대 6회다. — `HWAXPortal/docs/design-risk-review/plan.md:3417` — ``tool_budget` 3/라운드 → 좌석당 ≤6 실호출`
- (d) 좌석 프롬프트 전체 상한 — evidence 합 10600자, 자유조회 블록 3500자/석, 지정 도구 주입 5000자. — `HWAXPortal/docs/design-risk-review/plan.md:3694` — `프롬프트 상한 — evidence 라인 합 ≤10600자(엔진 예산 11000, §5.6.1 예산표·오버헤드 규칙), 지식카드 3500자/석, 자유조회 블록 3500자/석, tool_inject 5000자`
- (d) 좌석 관련도(편성 순서)도 요약 앞 500자로만 계산한다 — 변경이 많으면 앞부분만 반영된다. — `HWAXPortal/docs/design-risk-review/plan.md:3374` — `관련도 `relevance` = `recommend_agents(q=<summary_text 또는 rr_state 요약 앞 500자>, top 60)` 의 점수(목록 밖은 0).`
- (d) 실제 코드의 관련도 질의문 상한도 500자다. — `HWAXRisk/backend/app/roster.py:21` — `QUERY_TEXT_MAX = 500          # plan §6.3 — summary_text 앞 500자`
- (d) 비용 가드로는 수확 체감 정지가 있다(신규 클러스터가 안 나오면 멈춤) — 분할이 아니라 조기 종료다. — `HWAXPortal/docs/design-risk-review/plan.md:3406` — `수확 체감 정지 — 최근 3패널이 각각 신규 클러스터(§4 등록부 병합에서 새로 생긴 cluster_key) < 1 을 추가했고 C1 이 충족되면 잡을 `paused(reason=diminishing)` 로 두고 사용자에게 마감을 제안한다.`
- 영역 분할의 재료 1 — IR 에 서브어셈블리 단위 집계가 이미 있다. — `HWAXPortal/docs/design-risk-review/plan.md:1026` — ``rollups.by_assembly[]{path_prefix(asm_key 접두), depth, n_leaf, edges_internal{kind: count}, edges_external{kind: count}, orphan_leaf}`.`
- 영역 분할의 재료 2 — finding 주체 키에 서브어셈블리 형식이 있다. — `HWAXPortal/docs/design-risk-review/plan.md:980` — `서브어셈블리 `asm:<asm_key>``
- 영역 분할의 재료 3 — '좌석이 인용한 부품 ∩ 바뀐 부품' 교집합 판정이 있으나 다음 리비전의 재심 면제(carried)에만 쓴다. — `HWAXPortal/docs/design-risk-review/plan.md:3632` — `새 타깃(같은 과제·새 스냅샷/diff): 이전 타깃 done & cited_refs≠∅ & used_tool & (cited ckey ∩ 변경 ckey)=∅ & finished_at ≥ now−risk_carried_days → carried(carried_from_opinion_id`
- (e) 좌석이 실제로 받는 브리프 총량 실측 — 3,667자(픽스처 기준). — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:11` — `오늘 좌석이 받는 브리프를 그대로 재현하면 3,667자이고 내용은 "판 3장 · 접합 계면 2개" 가 전부다.`
- (e) 0단계 배선 수리 표의 좌석 통로 항목 — 141종 중 32종만 열림, 좌석당 3회. — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:56` — `| 좌석 통로 | 141종 중 32종만 열림, 좌석당 3회 |`
- (e) 0단계 배선 수리 표 — 검출 잣대 해시를 안 읽어 리비전 변화 이벤트가 지금은 전부 제외된다. — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:48` — `| 검출 잣대(tol) 해시 | 어댑터가 받는 응답에 값이 있는데 안 읽는다 | 간극·접착 띠·관통의 **리비전 변화 이벤트가 살아난다**(지금은 전부 제외) |`
- (e) 좌석이 부른 도구 결과는 얼린 스냅샷이 아니라 소스의 현재 상태를 읽고 그 패널 안에서만 인용된다. — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:38` — `좌석이 부른 도구 결과는 그 패널 안에서만 인용되고, 얼린 판이 아니라 소스의 **지금** 상태를 읽는다.`
- (e) E0 스코프가 상한 500 에 잘리던 결함(문서 §9, 2026-10-08 수정 표기). — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:207` — `브리프 스코프(E0)가 906자인데 상한 500 에 잘려 결측·소스·잣대 4줄이 빠진다.`
- (e) 능력 조사의 판단 — 가르는 단위가 도메인이 아니라 좌석이어야 한다(ECAD 의존에 한한 서술). — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:186` — `지금 심사는 ECAD 의존을 **도메인 단위**로 가른다(pcb·pwr·rf·soc·passive·mem 은 보류). 실제로는 좌석 단위다`
- (e) 실제 리비전 쌍으로 검증된 적이 없다 — 변경이 많을 때의 거동은 실측 0건. — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:82` — `검증된 적도 없다(변화 이벤트 0행).`
- (e) 0단계의 범위 정의. — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:193` — `| 0 | 배선 수리 — §3.1 의 표, §6 의 해석 잇기, §9 의 결함 | 심사 앱·심의 엔진 |`

### 확인하지 못한 것
- 영역별 분할안이 '한 번도 다뤄지지 않았다'는 판정은 남아 있는 문서 기준이다. 계획을 만든 1·2차 워크플로의 중간 산출(doc_20·doc_22·gap_21·crit_* 와 scratchpad 파트 파일)은 리포에 없어, 그 단계에서 분할안이 논의됐다가 빠졌는지는 확인하지 못했다(context-notes.md:69 '워크플로 산출 파트 파일은 scratchpad 에만').
- 키워드 검색(영역별·군집·서브시스템·subsystem·zone·partition·파티션·구역·부위별·조각·slice)은 0건이거나 무관한 뜻(화면 구역·엔진 slice(0,12)·센서 구역)뿐이었다. 다른 낱말로 적힌 같은 취지의 문장이 4,868줄 plan.md 어딘가에 있을 가능성은 배제하지 못한다 — 통독한 절은 §0.1·§0.7·§1·§2.7.4·§2.9·§2.11.3·§3.1·§3.2.4·§3.2.7·§3.3·§3.4·§4.8·§5.6·§6 전체·§10.4~10.9 이다.
- 계획이 인용한 엔진 쪽 상한(evidence 12항목·라인 합 11000·좌석 자유조회 3500자·tool_inject 5000자)은 계획 문면과 HWAXRisk brief.py 상수로만 확인했고, HWAXAgentServer/deliberation.py 의 실제 값은 이 질문에서 대조하지 않았다.
- '좌석에게 닿는 변경 정보가 4,050자를 넘지 못한다'는 것은 항목별 라인 상한(CAPS)의 합에서 나온 산술이다. 실제 변경이 많은 diff 로 브리프를 조립해 잰 값이 아니다 — 원장에 실제 리비전 쌍이 0건이라 잴 대상이 없다(cad-capabilities.md:82).
- 전원이 같은 타깃을 보게 한 '이유'는 계획이 명시적으로 논증한 것이 아니라 사용자 요구 인용·PK 설계·support 병합 규칙에서 읽어 낸 것이다. 분할 대비 장단을 비교한 문장은 찾지 못했다.
- 영역을 별도 타깃으로 만들 때와 한 타깃 안의 브리프 조각으로만 쓸 때 커버리지 회계·등록부 병합이 각각 어떻게 달라지는지는 계획에 없는 내용이라 판단하지 않았다.
