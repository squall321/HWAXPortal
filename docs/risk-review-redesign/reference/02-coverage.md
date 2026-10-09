# 설계안 반박 검토 결과 (2026-10-08)

## 누락 가능성 (coverage)

**판정** 방향(전문가마다 자기 카드로 따로 대조하고 토의는 쟁점에만 쓴다)은 목표에 맞고 비용도 현행 범위 안이다. 359명을 거르지 않고 8묶음 전부 돌려도 4,006~4,374회로 현행 3,528~6,840회 안에 든다. 그러나 지금 문면대로는 '빠짐없이' 를 보장하지 못한다. 완결 기준인 '빈 칸 없음' 은 제목만 본 '해당 없음' 으로도 전부 채워지고, 회로 영역 104명은 현 원장이 로스터 고정 때 종결(deferred)로 만들어 설계안에 들어오지도 못하며, 영역이 만나는 자리의 리스크는 '누군가 이미 지적했을 때만' 토의가 열린다. 셀 수 있게 하려면 회계 단위를 (전문가)에서 (전문가 × 검토 단위 × 카드)로 내리고, 교차(단위 × 영역쌍)와 메커니즘(단위 × 38종)을 별도 행으로 두며, '해당 없음' 은 표본 재검토로 놓침률을 재야 한다. 현 완결 판정(C1 이 Tier A 패널 3개 done 을 요구)과 러너 규칙(타깃 직렬·일일 24패널·수확 체감 정지)은 이 흐름과 그대로는 맞지 않아 같이 고쳐야 한다.

### 치명 결함과 고치는 법
- **결함** 완결 기준 '빈 칸 없음' 이 '해당 없음' 만으로 충족된다. 1단계가 카드 제목과 묶음 한 줄 요약만으로 거르고, 그 판정을 다시 보는 장치가 없다. 제목(메커니즘·물리 어휘)과 묶음 한 줄(CAD 부품명 어휘)은 어휘가 겹치지 않아 '어휘 겹침' 결정적 신호도 약하다. 한 줄 요약은 관련성을 일으키는 세부(감소 변화·크기·재질)를 버린다.
  - 근거: 현 원장은 abstain·skipped·deferred·carried 를 전부 종결로 세고(HWAXRisk/backend/app/planner.py:42, registry.py:38·937-938) C3 조건에는 abstain 상한이 없다(registry.py:979-987 — skipped 5% 이하·failed 0 뿐). 이벤트 문구는 소스 앱 부품명을 그대로 담는다(brief.py:499 주석, diff.py:1316 text=f"{dn_a}↔{dn_b} contact.added"). AIDataHub 는 '자료는 있는데 말이 안 맞아 전문가가 거절' 을 실측으로 적어 두었다(AIDataHub/api_server/src/api/mcp_runtime.py:455-457). 띵킹 모드는 같은 이유로 탈락을 근거 0건 그리고 어휘 미달 둘 다일 때만 한다(HWAXAgentServer/thinking.py:156-161).
  - 고침: 1단계를 거르는 단계가 아니라 보내는 단계로 바꾼다. (a) 제목 대신 카드 원문을 준다 — 도구 없는 텍스트 호출이면 117,600자가 들어가 최대 전문가(91,780자)도 실린다. (b) '해당 없음' 은 결정적 신호 miss 그리고 LLM miss 일 때만, 사유 코드와 함께. 한쪽이라도 hit 이거나 신호를 계산할 재료가 없으면(blind) 2단계로 보낸다. (c) Tier A 15명은 거르지 않고 전 묶음을 2단계로 돌려 1단계 예측과 대조해 그 타깃의 놓침률을 잰다. 임계를 넘으면 그 타깃은 필터를 끈다. (d) '해당 없음' 셀을 무작위 59건 이상 2단계로 재검토해 적발 0건이어야 C3 이다(놓침률 5% 이하, 95% 신뢰). 적발되면 그 사유 코드의 셀 전부를 다시 연다.
- **결함** 회로 6개 영역 104명이 설계안에 들어오지 못한다. 현 원장이 로스터 고정 순간 종결 상태 deferred 로 만들고 그 상태는 타깃 안에서 바뀌지 않는다. 들어온다 해도 'ECAD 가 없어 못 본다' 가 '관련 없다' 와 같은 칸('해당 없음')으로 닫혀, 입력 결손이 완결로 집계된다. 반대로 기구 변경이 회로에 주는 영향(보드 휨·스웰링 간극·안테나 접지 금속·MLCC 균열·TIM 간극)은 ECAD 없이도 말할 수 있는데 이 길이 막혀 있다.
  - 근거: planner.py:143-145(ecad_dep 그리고 ecad_absent 그리고 rank≠1 → deferred), planner.py:56(deferred 의 허용 전이 없음), routes.py:1883(ecad_absent 기본값 True), adapters/ecad_stub.py:29-41(capture 가 빈 결과 + ecad_absent). C1 은 deferred 를 종결로 세어 회로 영역을 '봤다' 로 치고(registry.py:937-943), C3 은 deferred 를 분모에서 뺀다(registry.py:979-981). HWAXPortal/docs/design-risk-review/cad-capabilities.md:186-187 은 'ECAD 의존은 도메인이 아니라 좌석 단위' 라고 결론 냈다(pwr 스웰링 계열은 MCAD 간극 하나면 되고, 센서·카메라 좌석은 ECAD 가 필요하며, 메모리 10석은 ECAD 가 와도 못 푼다).
  - 고침: 새 흐름의 타깃에서는 deferred 를 만들지 않고 110명 전원을 1단계에 넣는다. 셀 상태에 blocked_input(입력 결손)을 '해당 없음' 과 따로 두고, 그 셀에는 '무엇이 오면 판정 가능한가' 를 정보 요청으로 남긴다. 회로 전문가에게는 질문을 둘로 준다 — ① 이 기구 변경이 내 영역에 만드는 영향(기구→회로 방향), ② ECAD 가 오면 확인할 항목. blocked_input 이 남은 타깃은 'C3(입력 결손 N셀)' 로 표기하고 사람 확인(rr_gate_acks 와 같은 ack 관례)으로만 닫는다.
- **결함** 영역이 만나는 자리의 리스크를 잡는 5단계 발동 조건이 '둘 이상 영역이 같은 부품을 지적했거나 판정이 충돌' 이다. 어느 한 전문가의 카드에도 없는 창발 리스크는 정의상 아무도 지적하지 않으므로 토의가 열리지 않는다. 남는 그물은 '38종 누락 점검' 한 번인데, 이것은 영역 지식 없는 호출 한 번의 자유 응답이고 택소노미 자체가 기구 쪽에 치우쳐 있다.
  - 근거: 인접 표의 고유 쌍은 22개로 가능한 105쌍의 21% 이고 mech–rf·mech–pwr·mech–soc·disp–rf·mech–rel·mech–material 이 없다(HWAXRisk/backend/app/assets/adjacency.v1.json — 편성기 counter 석용 표다, planner.py:431-454). 메커니즘 38종은 interface 9·mechanical 8·material 6·thermal 5·electrical 5·process 5 이고 광학·음향·RF 성능·방수·ESD·자기 간섭 코드는 0건이다(assets/taxonomy.v1.json). 이웃 관계는 clearance 를 뺀 1홉이다(diff.py:472-483, 477 줄) — 비접촉 근접(스웰링·충돌·RF 결합)은 이웃으로 잡히지 않는다. 좌석 선정은 변경 내용을 보지 않고 변경→영역 표가 없다(측정값).
  - 고침: 교차를 원장의 1급 행으로 둔다 — (단위 × 영역쌍). 생성은 코드가 한다(묶음 안 변경 계면과 clearance 를 포함한 근접 쌍의 양끝 부품 역할 → 영역, 거기에 인접 표를 더한다). 닫는 방법은 '2차 영향 패스' 다. 2단계가 끝난 뒤 영역 A 의 그 단위 결과('문제없음' 판정 포함)를 영역 B 대표에게 주고 '이 변경과 이 판정이 당신 영역에 만드는 리스크' 를 묻는다(쌍마다 양방향). 5단계 패널은 여기서 충돌이 난 칸에만 연다. 누락 점검은 (단위 × 메커니즘) 행렬로 바꾼다 — 2단계 출력에 '검토한 메커니즘 코드 목록' 을 필수로 받아 코드가 집계하고, 0명인 칸을 소유 영역에 다시 배정한다. 택소노미 밖 메커니즘(mechanism_free)은 따로 세어 영역별 목록으로 낸다.
- **결함** 변경 묶음의 재료가 지금 표에 없고, 묶음에 들어갈 수 없는 이벤트가 있으며, 묶음 경계가 회계에 없다. 묶음별로만 보면 묶음을 가로지르는 리스크(공차 누적·질량·열 예산·같은 하중 경로 위의 두 변경)는 어느 호출에도 함께 실리지 않는다.
  - 근거: rr_diff_events 에는 의미층만 저장된다(diff.py:1743-1745 독스트링 '구조·파라메트릭 항목은 diff_json 안에만 산다'). G2 게이트가 실패하면 의미 이벤트가 0건이다(diff.py:1241-1243). dim.named_changed·dim.named_unmeasured·asm.rollup_changed 는 ckeys=[] 라 부품 기준 묶기에 걸리지 않는다(diff.py:1451·1459·1474). design_relevant=false 와 excluded_reason 항목은 변경 ckey 집합에서 빠진다(diff.py:620-637). 택소노미에는 전역 누적 메커니즘 mechanical.mass·interface.tolerance_stackup 이 있다.
  - 고침: (i) 이벤트 보존 불변식을 둔다 — 타깃의 모든 변경 항목 cid 가 어느 단위엔가 속하고 미배정은 0 이다. 부품 키 없는 이벤트는 '전역 단위', 제외분은 '제외 단위(사유별)' 로 눈에 보이게 둔다. (ii) 묶음 원천은 rr_diff_events 가 아니라 diff_json 의 구조·파라메트릭층까지다. G2 차단이면 묶음 머리에 '의미층 차단' 을 적는다. (iii) 두 묶음에 걸친 계면·근접 쌍은 '경계 단위' 로 따로 만들어 양쪽 묶음에 관련된 전문가의 합집합에 배정한다. (iv) 3단계를 요약이 아니라 '전역 패스' 로 올린다 — 자기 결과와 모든 단위의 시그니처를 주고 '묶음 간 조합 리스크' 를 필수 칸으로 받으며, 전문가마다 전역 단위 셀이 하나 있어야 한다.
- **결함** 스냅샷 타깃에서는 0단계가 나눌 변경 이벤트가 없어 설계안이 서지 않는다. 설계안의 모든 단계가 '묶음' 을 전제한다.
  - 근거: 브리프 E2 는 snap 타깃에 '[pair 전용 — 해당 없음]' 을 낸다(brief.py:473-476). snap 의 원천은 rr_states 의 summary_text 와 signals 다(brief.py:457-466, state.py:995-1038·298).
  - 고침: '검토 단위' 를 추상화한다. diff 는 변경 묶음, snap 은 (1단 조립 단위 × 신호군 — 상위 간섭·근접 간극·rule_hits·재질 미기재·명명 치수·요구)으로 만든다. snap 에서는 관련성 필터를 끈다(현황 감사는 전 전문가 대상이다). design-rule 4,695장·standard-summary 2,270장 계열 카드가 체크리스트가 되므로 '판단 불가(데이터 없음)' 비율을 별도 계수로 내고, 그 사유를 정보 요청으로 모은다.
- **결함** 현 완결 판정과 러너 규칙이 이 흐름과 그대로는 맞지 않는다. 칸을 전부 채워도 C1 이 서지 않고, 단독 검토를 패널 행으로 적으면 반대로 중간에 멈춘다. strong 비율 조건도 무력해진다.
  - 근거: C1 은 Tier A 패널 3개 done 을 요구한다(registry.py:944-945) — 1~3단계가 패널이 아니면 0 이고 C2·C3 은 C1 을 전제한다(registry.py:976·987). rr_seat_opinions.panel_id 는 NOT NULL 이다(risk_store.py:312). 패널 행으로 적으면 타깃당 running 패널 1개 불변식(planner.py:844-845)·타깃 직렬 집기(runner.py:733-737)·일일 상한 24(config.py:209 — 359건이면 15일)·수확 체감 정지(runner.py:1390·916-933 — 최근 3패널 신규 클러스터 0 이면 정지, '해당 없음' 이 이어지는 꼬리에서 걸린다)에 걸린다. card: 인용은 존재 확인 없이 통과하므로(narrative.py:645-646) 전원이 done 이 되어 strong 0.7 조건이 뜻을 잃는다. 덧붙여 runner.py:1384 는 level.get('raised') 를 보는데 close_level 반환(registry.py:1008-1035)에 그 키가 없어 통합 보고서 자동 생성 분기가 참이 되지 않는다(registry·runner·routes 세 파일 grep 범위).
  - 고침: close_level 을 셀 기반으로 다시 정의한다(improvements 의 회계 항목). 단독 검토는 rr_panels 가 아니라 새 실행 표(rr_reviews)에 적고 의견의 panel_id 자리에는 review_id 를 쓴다(이 DB 의 외래키는 문자열 계약이다). 수확 체감·일일 상한·타깃 직렬은 5단계 패널에만 적용한다 — 단독 검토는 서로를 읽지 않으므로 병렬로 돌리고 등록부 병합은 끝난 뒤 정렬 순서로 한 번 한다. strong 은 '4단계에서 원문 대조를 통과한 인용 1건 이상 또는 도구 호출 성공' 으로 다시 정의한다. raised 분기는 previous_level 과 level 비교로 고친다.
- **결함** 2단계의 '카드 전부 원문 + 도구' 를 한 호출에 실으면 상위 5% 전문가는 엔진 자체 기준으로 창을 넘고, 30장 가운데 몇 장을 실제로 판정했는지 세는 장치가 없다. 넘치면 400 이거나 조용한 절단이다 — 설계안이 없애려던 결함이 2단계에서 다시 생긴다.
  - 근거: 엔진의 한국어 보수 계수는 1.05자/토큰이고(HWAXAgentServer/deliberation.py:199) 도구를 묶은 좌석은 스키마·출력 몫으로 56,000토큰을 뗀다(deliberation.py:202). 128,000 − 56,000 = 72,000토큰 = 75,600자인데 전문가 카드 전부의 p95 는 77,775자·최대 91,780자다(측정값). 현행은 좌석당 3,500자만 싣는다(deliberation.py:4071).
  - 고침: 2단계를 둘로 나눈다. 2a 는 도구 없는 텍스트 호출로 카드 대조만 한다(가용 117,600자 — 최대 전문가도 25,820자가 묶음 몫으로 남는다). 2b 는 '위반 가능·주의' 가 난 카드에 한해 도구로 수치를 확인한다. 코드가 판정 행 수와 동결한 카드 수를 대조해 빠진 카드만 다시 묻는다(카드 판정 누락 0 이 셀 종결 조건). 입력 글자 수와 절단 여부를 셀에 적고 절단이 있으면 종결로 치지 않는다. 묶음이 길면 카드를 10~15장씩 나눠 묻는다.
- **결함** 카드 0장인 전문가 3명은 1단계에서 볼 제목이 없고 2단계에서 대조할 카드가 없어 '해당 없음' 또는 내용 없는 '검토함' 으로 칸만 채운다. material 영역은 전문가가 1명이라 그 한 명이 걸러지거나 실패하면 영역 전체가 비는데, 재질 변경 이벤트를 그 전문가의 물성 카드 2,688건(평균 38,114자, 전부 실을 수 없다)에 잇는 결정적 경로가 없다.
  - 근거: 측정값(0장 3명, material 1명에 물성 카드 2,688건). agent_search 는 묶인 레코드가 0건이면 거절로 답한다(mcp_runtime.py:508-516) — 카드 0장과 레코드 0건은 다른 사실이다. part.material_changed 이벤트는 material_norm·mid 를 갖는다(diff.py:1020-1037·1406).
  - 고침: 셀에 근거 기반(card_basis)을 적는다 — cards | docs_only | none. 0장 전문가는 '해당 없음' 을 낼 수 없고(결정적 신호 blind) 역할 문서 + 긴 문서 검색 + 도구로 검토하며, 결과는 경험칙 등급·done_weak 로 집계하고 보고서에 '카드 결손 전문가' 로 따로 적는다. 재질 변경 이벤트는 재질명으로 물성 카드를 직접 조회해(검색어가 아니라 키 조회) material 전문가의 그 단위 입력에 싣는다. 전문가가 1~2명인 영역은 실패 시 자동 재시도 뒤 사람에게 올린다.

### 개선
- [회계 1 — 행과 열] 표 여섯을 덧붙인다. ① rr_units(target_key, unit_id) — 검토 단위. kind 는 bundle·boundary·global·excluded·snap_unit, 열은 시그니처(change_kind·부품 키·재질·계면 종류·크기 양쪽 부호)·cid 목록·시그니처 해시·전량 요약. ② rr_roster_cards(target_key, agent_key, card_id) — 로스터 고정 때 카드 목록과 판번호를 동결한 분모. ③ rr_cells(target_key, agent_key, unit_id) — 전문가 × 단위. ④ rr_card_verdicts(target_key, agent_key, unit_id, card_id) — 카드 × 단위 판정(위반 가능·주의·문제없음·판단 불가·적용 조건 불성립)과 인용·대조 결과. ⑤ rr_cross_cells(target_key, unit_id, domain_a, domain_b) — 교차. ⑥ rr_mech_cells(target_key, unit_id, mechanism_code) — 메커니즘. rr_coverage 의 PK(target_key, agent_key)와 상태 10종은 그대로 두고 셀의 롤업으로 쓴다.
  - 이유: '전문가는 타깃마다 한 번' 만으로는 그 한 번에 무엇을 봤는지 셀 수 없다. 마이그레이션은 CREATE TABLE·ADD COLUMN·CREATE INDEX 만 허용되고(risk_store.py:561) rr_coverage.status 는 CHECK 로 10종에 묶여 있어(risk_store.py:253-254) 새 상태를 거기에 넣을 수 없다 — 그래서 세부 상태는 새 표에 두고 기존 표는 롤업으로 남긴다. 기존 화면·MCP(risk_get_coverage)·C 레벨 이름이 깨지지 않는다.
  - 비용: 새 표 6, planner 에 단위 생성·셀 생성 함수, registry.close_level 재작성, 불변식 시험. 프론트는 다른 세션 몫이라 뺀다.
- [회계 2 — 셀 상태값] rr_cells.state 는 pending → routed(검토 대상) | na(해당 없음) | blocked_input(입력 결손) → running → reviewed | reviewed_weak | failed(재시도 2회까지) | skipped(사람·사유 필수) | carried. 함께 적는 열은 route_det(hit·miss·blind), route_llm(hit·miss), reason_code, card_basis, cards_expected, cards_judged, 판정별 건수, 카드 밖 리스크 수, 검토한 메커니즘 코드, 입력 글자 수, 절단 여부, 감사 여부와 결과. na 는 route_det=miss 그리고 route_llm=miss 그리고 reason_code 가 있을 때만 쓸 수 있다.
  - 이유: 지금 설계안의 세 값(검토함·해당 없음(사유)·미검토)으로는 '관련 없음' 과 '못 봄(ECAD 없음)' 과 '봤지만 카드 몇 장을 빠뜨림' 이 같은 칸에 섞인다. 리스크 심사에서 위험한 쪽은 놓침이므로 na 로 가는 문만 좁힌다.
  - 비용: 1단계 출력 스키마에 사유 코드 목록(예: 영역 밖 역할·적용 조건 없는 카드뿐·거버넌스 카드뿐)을 정해야 한다.
- [회계 3 — 불변식] U1 이벤트 보존: 타깃의 변경 항목 cid 전부가 어느 단위엔가 속한다(미배정 0, 제외분은 excluded 단위에). C-1 격자 완전성: 셀 수 = 로스터 수 × (excluded 를 뺀 단위 수). C-2 카드 완전성: reviewed 셀은 cards_judged = cards_expected 이고 절단 0. C-3 인용 실재: 위반 가능·주의 판정의 인용은 4단계 원문 대조를 거친 것만 근거 등급에 반영. X-1 교차 완전성: geometry 유래 교차 셀에 pending 0. M-1 메커니즘 완전성: (단위 × 38종)에서 '아무도 검토 안 함' 0. 기존 불변식 1(상태 합 = 로스터 수)·3(종결 좌석은 의견 보유)·5(로스터 밖 편성 0)는 그대로 둔다.
  - 이유: '빠짐없이 봤다' 를 문장이 아니라 코드가 실패시키는 등식으로 만든다. 현 불변식(planner.py:832-865)은 좌석 단위까지만 본다.
  - 비용: check_invariants 확장과 시험. U1 은 0단계 구현과 같이 나온다.
- [회계 4 — rr_coverage 롤업과 Tier] 전문가의 셀이 전부 종결이고 reviewed 가 1개 이상이며 검증된 인용 또는 도구 성공이 있고 3단계 보고서가 있으면 done, 검증 근거가 없으면 done_weak(카드 0장 전문가 포함), 전 셀이 na 면 abstain(reason=na_all, 의견 행은 1단계 판정 기록)으로 적는다. deferred 는 새 흐름 타깃에서 만들지 않는다. carried 는 셀로 내린다 — 단위 시그니처 해시와 카드 판번호가 이전 타깃과 같을 때만 그 셀을 넘긴다. Tier 는 걸러내는 기준이 아니라 실행 순서로 쓴다. A(영역 1순위 15명)는 필터 없이 전 단위를 2단계로 돌려 1단계의 놓침률을 재는 보정 집합으로 삼는다.
  - 이유: 지금 carried 는 (타깃, 전문가) 단위라 묶음 하나만 바뀌어도 전부 다시 돌거나 전부 넘어간다(planner.py:754-806). Tier A 는 15명이 어차피 먼저 도는 자리라 보정 비용이 15 × 단위 수 호출뿐이다.
  - 비용: 8단위면 보정 호출 120회. rank 는 recommend_agents 상위 60 밖이면 0 이라 키 순서다(roster.py:20·175) — '1순위' 의 뜻이 약하므로 1단계 결과로 실행 순서를 다시 매기는 것을 권한다.
- [회계 5 — 완결 판정] C1 = Tier A 15명의 셀 전부 종결(na 없음) + 단위마다 route_det=hit 인 모든 영역에 reviewed 1개 이상 + U1 성립. C2 = C1 + Tier B 범위 셀 종결 + strong 0.7 이상(검증 인용 기준) + Tier A 대조로 잰 1단계 놓침률 공표 + geometry 유래 교차 셀 전부 reviewed + 반대석 기각 표기. C3 = 전 셀 종결(pending·running·failed 0) + C-2 전 셀 성립 + na 표본 감사 59건 이상 적발 0 + 교차 셀 pending 0 + 메커니즘 칸 미검토 0 + skipped 5% 이하. blocked_input 이 남으면 'C3(입력 결손 N셀)' 로 표기하고 사람 ack 로만 닫는다. 보고서 머리에 숫자 여섯을 찍는다 — 셀 총수와 상태별 수, 카드 판정 수/기대 수, 인용 검증률, 교차 셀 닫힘, 메커니즘 칸 닫힘, na 감사 결과.
  - 이유: 현 C1 은 deferred 도 종결로 세어 회로 영역을 통과시키고(registry.py:937-943) C3 은 abstain 이 몇 명이든 통과한다(registry.py:979-987). 레벨 이름과 단조 증가 규칙(registry.py:42·998-1000)은 유지한다.
  - 비용: close_level 재작성과 진행판 응답 필드 추가. 표본 감사 59건의 2단계 호출.
- 카드 적용 시그니처를 카드당 한 번 만들어 둔다. 카드 원문에서 '어떤 변경 종류·부품 역할·재질·계면·메커니즘에 적용되는가' 를 택소노미 코드로 뽑아 card_id + 판번호로 캐시한다. 묶음 시그니처와의 교집합이 1단계의 결정적 신호(route_det)가 된다.
  - 이유: 설계안의 결정적 신호(카드 태그·부품명 어휘 겹침)는 CAD 부품명과 카드 어휘가 달라 약하다. 적용 조건끼리 맞추면 판정이 재현되고 감사할 수 있다. 타깃마다 다시 하지 않는다.
  - 비용: 1회성 10,774회 짧은 호출(카드 평균 657토큰 입력). 카드가 개정되면 그 카드만 다시 한다. 사람 표본 검수가 필요하다.
- 부품 역할 → 영역 표를 만든다(변경 → 영역 표). 부품 키마다 역할(배터리·안테나 방사체·실드캔·카메라 모듈 등)과 관련 영역을 적고, 교차 셀 생성과 route_det 의 입력으로 쓴다. 첫 판은 1단계 결과에서 역산해 채우고 사람이 확정한다.
  - 이유: 좌석 선정이 변경 내용을 보지 않는 근본 원인이 이 표의 부재다(측정값). 인접 표는 영역 대 영역이라 '이 부품이 어느 영역 것인가' 를 답하지 못한다.
  - 비용: 원장 표 하나와 사람 확정 화면(기존 ckey 원장 rr_part_keys 에 열 추가로 가능). 과제가 쌓일수록 재사용된다.
- xd 122명 처리. (a) 영역 요약은 LLM 이 122건을 읽게 하지 말고 2단계 출력을 기존 finding 스키마로 받아 cluster_key 로 코드가 병합한 뒤 그 병합 결과를 요약한다. (b) 지지 수를 '전문가 수' 와 '영역 수' 로 나눠 적는다. (c) xd 를 하위 군(키 둘째 토막 기준)으로 묶어 군별 요약을 먼저 만든다. (d) 거버넌스 성격 카드는 카드 시그니처에서 '설계 형상과 무관' 으로 분류해 사유 코드로 닫는다.
  - 이유: xd 122명 × 발언 중앙값 2,000자 = 244,000자로 128K 창을 넘는다 — 한 호출 요약은 조용한 절단이 된다. 지금 support 는 패널 수로 세고 패널이 없으면 구성원 수로 센다(registry.py:205-206) — 단독 검토에서는 같은 지적이 xd 에서 수십 번 나와 지지 수가 부풀 수 있다. cluster_key 는 메커니즘·세부·대상·변경 종류의 해시라 영역과 좌석이 들어가지 않는다(narrative.py:933-936).
  - 비용: 2단계 출력을 finding 스키마에 맞추는 프롬프트·파서 작업. registry 병합에 열 2개.
- 4단계 검증을 3단계 앞으로 옮기고 지금 끊긴 배선을 잇는다. 카드 번호 실재 확인(external_check 연결)·인용 문구의 카드 원문 포함 대조·수치 대조를 2단계 직후에 돌려, 등급이 내려간 결과로 전문가 보고서를 쓴다. 좌석별 카드 적중 수(knowledge_hits_n)를 실제 값으로 채운다.
  - 이유: 지금은 card: 인용이 확인 없이 통과하고(narrative.py:645-646) 그것만으로 근거 등급이 '문헌·규격' 으로 오른다(narrative.py:768). 등급이 우선순위 가중에 들어가므로(registry.py:20·298 — 문헌·규격 0.8, 경험칙 0.6) 지어낸 카드 번호가 우선순위를 33% 올린다. 검증을 보고서 뒤에 두면 틀린 인용이 보고서에 남는다.
  - 비용: 동결한 카드 원문(rr_roster_cards)이 있으면 대조는 순수 코드다.
- 긴 문서(논문 22,421·특허 5,371·규격 864)는 '묶음 내용으로 만든 검색어' 만 쓰지 말고, 위반 가능·주의가 난 카드의 sources·standard_refs 를 따라 직접 조회하는 길을 먼저 쓴다. 검색은 보조로 두고 셀에 '조회함·적중 0·미조회' 를 적는다.
  - 이유: 검색어 기반은 무엇을 놓쳤는지 셀 수 없다. agent_search 는 묶인 레코드 전체가 범위이고 기본 top_k 가 10 이라(mcp_runtime.py:469·489-495) 카드와 긴 문서가 같은 10칸을 다툰다. 카드가 이미 출처를 들고 있다(카드 필드 sources·standard_refs).
  - 비용: 레코드 직접 조회 호출이 늘어난다. 평균 43,629~101,242자 문서라 섹션 단위로 가져와야 한다.
- 0단계에서 지금의 절단·정렬 결함을 고칠 때 묶음 요약의 정렬을 절대값 기준으로 하고, 한 묶음 전량 요약이 호출 창을 넘으면 자르지 말고 묶음을 다시 나눈다(나눈 사실을 단위 행에 적는다).
  - 이유: 지금 E2 는 부호 있는 크기 내림차순이라 감소 변화가 뒤로 가서 먼저 잘린다(brief.py:487). 전량을 약속했으면 넘칠 때의 규칙이 있어야 한다.
  - 비용: 작다. 0단계 구현에 포함된다.

### 숫자
- ECAD 부재 시 deferred = (19−1)+(18−1)+(19−1)+(20−1)+(18−1)+(16−1) = 104명. 활성 = 359−104 = 255명(71.0%). 회로 6개 영역 전체 = 19+18+19+20+18+16 = 110명(30.6%).
- Tier 누적 = A 15 · B 114(Σceil(0.3·|d|) = 37+7+7+6+6+6+6+6+6+6+6+6+5+3+1) · C 359. 패널 = 3 + ceil(99/5) 20 + ceil(245/5) 49 = 72. ECAD 부재면 B 누적 114−29 = 85, 패널 = 3 + ceil(70/5) 14 + ceil(170/5) 34 = 51.
- 패널당 호출(좌석 6·라운드 3·지정 도구 4 가정) = 하한 6·3 + 6·2·2 + 4 + 3 = 49, 상한 6·3·2 + 6·2·4 + 2·4 + 3 = 95. 72패널 = 3,528~6,840회(측정값의 3,500~6,800 과 맞는다). 51패널 = 2,499~4,845회.
- 현행 카드 노출률 = 3,500자 / 57,072자 = 6.1%(좌석당). 전체로도 359×3,500 = 125.7만 자 / 2,049만 자(10,774×1,902) = 6.1%. 줄 상한 700자라 3,500/700 = 5줄이 바닥이고 그 칸을 논문·특허와 나눠 쓴다.
- 카드 전부의 토큰 = 낙관(카드 token_estimate) 657×30 = 19,710토큰(1,902/657 = 2.9자/토큰), 엔진 보수 계수 1.05자/토큰이면 평균 57,072/1.05 = 54,354 · p95 77,775/1.05 = 74,071 · 최대 91,780/1.05 = 87,410토큰.
- 도구를 묶은 호출의 가용분 = 128,000 − 56,000 = 72,000토큰 = 75,600자. 평균 전문가는 75,600 − 57,072 = 18,528자가 묶음·지시문 몫이고, p95(77,775자)부터는 묶음 0자여도 넘친다(상위 5% = 18명 이상).
- 도구 없는 텍스트 호출의 가용분 = 128,000 − 16,000 = 112,000토큰 = 117,600자. 최대 전문가도 117,600 − 91,780 = 25,820자가 남는다.
- 설계안 호출 수(추정식) = 359 + 359·B·r + 359 + P·(49~95) + B + 16. B=8·r=0.5·P=8 이면 359 + 1,436 + 359 + 392~760 + 8 + 16 = 2,570~2,938회. r=1(거르지 않음)이면 359 + 2,872 + 359 + 392~760 + 24 = 4,006~4,374회. 1단계로 거르는 이득은 최대 1,436회이고 현행 범위 안에서 포기할 수 있는 크기다.
- 카드 판정 행 수 = 10,774 × B × r. B=8·r=0.5 → 43,096행, r=1 → 86,192행.
- 1단계를 카드 원문으로 돌릴 때 입력 = 359 × 57,072 = 2,049만 자. 2단계(1,436회 × 57,072 = 8,196만 자)의 1/4.
- '해당 없음' 표본 감사 크기 = 적발 0건일 때 놓침률 상한 p ≤ 1 − 0.05^(1/n). n=59 → 5%, n=149 → 2%, n=299 → 1%(95% 신뢰).
- 영역 요약 한 호출 적합성 = xd 122 × 2,000자 = 244,000자 ≈ 232,381토큰(1.05 기준)으로 128K 초과. sim 22 × 2,000 = 44,000자는 들어간다. 전문가 보고서가 6,000자면 sim 도 132,000자 ≈ 125,714토큰으로 지시문과 합쳐 넘친다.
- 인접 표 = 고유 쌍 22 / C(15,2) 105 = 21%, 없는 쌍 83. 비대칭 4건(sim→mech, cam→mech, passive→pcb, xd→mech 는 반대 방향이 없다).
- 택소노미 38종 = interface 9 + mechanical 8 + material 6 + thermal 5 + electrical 5 + process 5. 광학·음향·RF 성능 코드 0 — cam 21 + sh 17 + rf 19 = 57명 영역의 고유 메커니즘은 mechanism_free 로만 들어간다.
- xd = 122/359 = 34.0%, 카드 약 122×30 = 3,660장. 카드 보유 전문가 356명 기준 10,774/356 = 30.3장.
- 단독 검토를 패널 행으로 적으면 일일 상한 24 에 걸려 359/24 = 15일이 든다.
- Tier A 보정 비용 = 15명 × 단위 수. 8단위면 120회. 교차 셀 상한 = 단위당 105쌍 × 양방향 2 = 210회, 인접 표만이면 22쌍 × 2 = 44회.

### 코드 사실
- 커버리지 종결 상태는 done·done_weak·abstain·skipped·deferred·carried 여섯이고, deferred·abstain 은 나가는 전이가 없다. — `HWAXRisk/backend/app/planner.py:42`
- 로스터 고정 때 ECAD 의존 영역의 1순위가 아닌 전문가를 처음부터 deferred(reason=ecad_absent)로 만든다. — `HWAXRisk/backend/app/planner.py:143`
- Tier 는 rank_in_domain 상한이다 — A 는 1, B 는 ceil(0.3·영역 크기), C 는 제한 없음. — `HWAXRisk/backend/app/planner.py:230`
- 패널 호출 추정식 est_low = S·R + S·(R−1)·2 + T + 3, est_high = S·R·2 + S·(R−1)·4 + 2T + 3. — `HWAXRisk/backend/app/planner.py:284`
- 좌석 종결은 발언 0 → failed, 기권 → abstain, 도구 사용 또는 인용 있음 → done, 둘 다 없음 → done_weak 로 정한다. — `HWAXRisk/backend/app/planner.py:558`
- 불변식 2 — 타깃당 running 패널은 1개 이하여야 한다. — `HWAXRisk/backend/app/planner.py:844`
- C1 은 영역마다 종결 좌석 1개 이상(deferred 도 종결로 센다) 그리고 Tier A 패널 3개 done 이다. — `HWAXRisk/backend/app/registry.py:944`
- C2 는 C1 + 영역별 종결 max(3, ceil(0.3·활성)) + strong 비율 0.7 이상 + 반대석 표기 + 파싱 실패 0 이다. — `HWAXRisk/backend/app/registry.py:976`
- C3 은 C2 + deferred 아닌 전원 종결 + skipped 5% 이하 + failed 0 이다. abstain 상한은 없다. — `HWAXRisk/backend/app/registry.py:987`
- 클러스터 지지 수는 패널 수로 세고 패널이 없으면 구성원 수로 센다. — `HWAXRisk/backend/app/registry.py:206`
- 우선순위 = sev3 × 검출 가중 × 근거 등급 가중(문헌·규격 0.8, 경험칙 0.6). 지지 수는 들어가지 않는다. — `HWAXRisk/backend/app/registry.py:298`
- close_level 반환 dict 에 raised 키가 없다(level·previous_level 만 있다). — `HWAXRisk/backend/app/registry.py:1008`
- 러너는 level.get('raised') 가 참일 때만 통합 보고서를 만든다 — 위 사실과 합치면 이 분기는 참이 되지 않는다. — `HWAXRisk/backend/app/runner.py:1384`
- rr_coverage 의 PK 는 (target_key, agent_key) 이고 status 는 CHECK 로 10종에 묶여 있다. — `HWAXRisk/backend/app/risk_store.py:250`
- rr_seat_opinions 는 panel_id 가 NOT NULL 이고 UNIQUE(target_key, agent_key, cycle) 이다. — `HWAXRisk/backend/app/risk_store.py:311`
- 마이그레이션 허용 연산은 CREATE TABLE IF NOT EXISTS · ADD COLUMN · CREATE INDEX IF NOT EXISTS 뿐이다. — `HWAXRisk/backend/app/risk_store.py:561`
- 관련도는 recommend_agents 상위 60명의 점수이고 목록 밖은 0.0 이다 — 영역 안 순위는 그 뒤 키 순서로 매겨진다. — `HWAXRisk/backend/app/roster.py:175`
- ecad_absent 는 missing_json 에 값이 없으면 True 로 본다. — `HWAXRisk/backend/app/routes.py:1883`
- ECAD 어댑터는 스텁이다 — capture 가 노드·엣지 0 과 ecad_absent 를 돌려준다. — `HWAXRisk/backend/app/adapters/ecad_stub.py:29`
- rr_diff_events 에는 의미층 이벤트만 저장된다(구조·파라메트릭 항목은 diff_json 안에만 있다). — `HWAXRisk/backend/app/diff.py:1743`
- G2 게이트가 실패하면 의미 이벤트를 만들지 않는다(events 빈 목록). — `HWAXRisk/backend/app/diff.py:1241`
- dim.named_changed·dim.named_unmeasured·asm.rollup_changed 이벤트는 ckeys 가 빈 목록이다. — `HWAXRisk/backend/app/diff.py:1451`
- 1홉 이웃 계산은 clearance 엣지를 뺀다. — `HWAXRisk/backend/app/diff.py:477`
- 브리프 E2 는 snap 타깃에 '[pair 전용 — 해당 없음]' 을 낸다. — `HWAXRisk/backend/app/brief.py:473`
- E2 정렬 키가 −magnitude 라 부호 있는 크기 내림차순이다(감소 변화가 뒤로 간다). — `HWAXRisk/backend/app/brief.py:487`
- 패널 질문은 과제 코드·타깃 키·소스 id·요약 앞 200자이고 변경 목록이 없다. 좌석 agent_search 의 질의가 이 문자열이다. — `HWAXRisk/backend/app/runner.py:358`
- 잡 집기는 그 타깃에 running 패널이 있으면 건너뛴다(타깃 직렬). — `HWAXRisk/backend/app/runner.py:733`
- 레벨이 C0 이 아니고 최근 3패널의 신규 클러스터가 0 이면 잡을 paused(diminishing)로 둔다. — `HWAXRisk/backend/app/runner.py:1390`
- 기본값 HWAXRISK_CONCURRENCY=2, HWAXRISK_DAILY_PANEL_CAP=24. ECAD 의존 영역 기본값은 pcb·pwr·rf·soc·passive·mem 이다(41행). — `HWAXRisk/backend/app/config.py:208`
- card·rpt·inc 참조는 external_check 가 없으면 ok=True·verified=False 로 통과한다. — `HWAXRisk/backend/app/narrative.py:645`
- card 또는 paper 인용이 있으면 근거 등급이 '문헌·규격' 이 된다. — `HWAXRisk/backend/app/narrative.py:768`
- 좌석 의견의 knowledge_hits_n 은 None 으로 저장된다. — `HWAXRisk/backend/app/narrative.py:1666`
- cluster_key = sha1(mechanism|mechanism_detail|subject_key|change_kind)[:12] 이고 영역·좌석은 들어가지 않는다. — `HWAXRisk/backend/app/narrative.py:933`
- 인접 표는 영역 15개에 고유 쌍 22개다. mech–rf·mech–pwr·mech–soc 가 없다. — `HWAXRisk/backend/app/assets/adjacency.v1.json:`
- 택소노미 메커니즘 38종은 interface 9·mechanical 8·material 6·thermal 5·electrical 5·process 5 다. — `HWAXRisk/backend/app/assets/taxonomy.v1.json:`
- 한국어 보수 계수 _EVID_KO_CPT = 1.05자/토큰, 도구 묶은 좌석의 예약분 _EVID_RESERVE = 40,000 + 16,000 토큰이다. — `HWAXAgentServer/deliberation.py:199`
- 좌석 지식카드 주입 예산은 3,500자이고 조회 질의는 패널 질문 그대로다(4095행). 한 줄은 700자에서 끊는다(2404행). — `HWAXAgentServer/deliberation.py:4071`
- 띵킹 모드 예심 탈락은 근거 0건 그리고 어휘 일치 미달일 때만이다(AND). 검색이 실패한 좌석은 통과시킨다. — `HWAXAgentServer/thinking.py:156`
- agent_search 의 범위는 그 전문가에 묶인 레코드 전체이고 기본 top_k 는 10 이다. 묶인 레코드가 0건이면 거절로 답한다(515행). — `AIDataHub/api_server/src/api/mcp_runtime.py:469`
- 주석에 실측이 적혀 있다 — 구어로 물으면 자료가 있는 전문가가 거절한다(말이 안 맞아 점수가 임계 밑). — `AIDataHub/api_server/src/api/mcp_runtime.py:455`
- 능력 조사 결론 — ECAD 의존은 도메인이 아니라 좌석 단위다. 메모리 10석은 ECAD 가 와도 근거가 안 생긴다. — `HWAXPortal/docs/design-risk-review/cad-capabilities.md:186`

### 확인하지 못한 것
- 실제 diff 한 건의 이벤트 수와 묶음 수 분포. 원장에 실물이 없어(능력 조사 기록 — 판 3장 픽스처) B 와 관련 비율 r 은 가정값이다.
- 1단계 LLM 판정의 실제 놓침률. 측정이 없다 — 그래서 Tier A 대조와 표본 감사를 제안했다.
- 카드 제목의 실제 모양과 길이, 카드 적용 조건이 본문 어느 섹션에 있는지. DB 에 접속하지 않아 카드 실물을 보지 못했다.
- 10,774장이 고유 카드 수인지 전문가별 합계인지. 레코드의 agents 는 배열이라 한 카드가 여러 전문가에 묶일 수 있다. 전문가당 30장 × 356명과 맞으므로 공유는 거의 없다고 추정했다.
- 카드 0장 3명이 누구이고 어느 영역인지, 그들에게 논문·특허는 묶여 있는지.
- 카드 token_estimate 의 산식. 657토큰/1,902자 = 2.9자/토큰은 엔진 보수 계수 1.05 와 2.8배 차이라, 실제 토크나이저로 재야 2단계 한 호출 적합성이 확정된다.
- 운영 모델의 출력 상한(max_tokens). 카드 30장 판정이 한 응답에 다 나오는지 확인하지 못했다.
- 전문가별 retrieval_config(top_k·data_type_filter·score_threshold) 값. 지금 3,500자 안에 카드와 논문이 어떤 비율로 실리는지 모른다.
- xd 122명의 하위 구성(키 구조)과 카드 내용의 중복도. 능력 조사는 '다수가 거버넌스 좌석' 이라고만 적었다.
- 2단계 대형 입력 호출 1회의 지연. 측정이 없어 벽시계를 추정하지 못했다.
- recommend_agents 상위 60 밖 299명의 순위가 키 순서라는 것이 실제 로스터에서 Tier A '대표' 를 얼마나 왜곡하는지.
- runner.py:1384 의 raised 분기를 채우는 다른 경로가 있는지. registry·runner·routes 세 파일만 grep 했고 시험 코드는 보지 않았다.
- 부품명 → 역할 → 영역 표를 만들 원천의 품질(소스 앱 부품명의 규칙성).
- '2차 영향 패스' 가 창발 리스크를 실제로 얼마나 잡는지. 제안이고 검증된 것이 아니다.


