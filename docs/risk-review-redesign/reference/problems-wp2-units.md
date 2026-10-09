# WP2 설계서 반대 검토 메모 (problems-wp2-units)

작성 2026-10-09. 대상 spec-wp2-units.md. 문제를 찾을 때마다 덧붙인다.

## W2-01 [major] 전역 단위에 쪼개는 규칙이 없다 — 넘치면 U3 위반으로 빌드가 통째로 failed 다

- 근거(설계서). 3.4.3 의 4단계는 전역 단위를 하나만 만든다(전역 항목 + 한 단위에 들지 않는 조립 항목 + 단위 목록·총량 줄). 6단계의 재분할은 'BFS 순서의 가운데' 인데 전역 단위에는 부품(앵커)이 없어 BFS 순서가 없다. 3.4.5 U3 은 global 도 fits 여야 하고 예외는 '부품 원자 하나가 상한 초과' 뿐이며 위반이면 failed 다. 3.14 는 failed 면 직전 활성이 그대로이고(첫 빌드면 단위 0), 7.1 은 failed 면 검토 잡이 시작하지 않는다고 적는다.
- 근거(코드). `diff.py:1182~1211 _rollup_delta` 는 접두마다 행을 내고 깊은 접두의 변화가 조상 행에도 겹친다(설계서 2.1 도 인정). `diff.py:1118~1141 _dims_delta` 는 명명 치수 전부를 낸다. 부품 추가·삭제가 여러 조립에 퍼진 큰 diff 에서는 '변한 롤업 행' 이 조립 깊이 × 조립 수만큼 생기고 그중 한 묶음에 들지 않는 것은 전부 전역으로 간다.
- dev(16K 창)에서는 더 빨리 터진다. 3.13 의 `caps_for_limits` 로 `max_chars = (3008−400)×0.6 = 1,564자`, `max_lines = max(8, 1564//175) = 8` 이다. 단위 목록 줄만으로도(단위 20개면 20줄) 8줄을 넘는다.
- 결과. '변경이 많은 과제' 라는 바로 그 입력에서 단위 빌드가 failed 가 되고 새 흐름이 시작하지 못한다.
- 고치는 법. 커밋 2 에 (a) 전역 단위 분할 규칙을 넣는다 — 구획(명명 치수 / 롤업은 최상위 접두별 / scope / 모르는 버킷) 순으로 target_lines 까지 채워 `global#0..n` 으로 가른다. (b) 단위 목록·총량 줄은 소유 줄이 아니라 문맥으로 두고 fits 계산에서 빼거나 줄 수에 상한(넘으면 'n개 중 m개 — 전체는 GET /units')을 둔다. (c) U3 에 '전역 단위가 넘치면 failed 가 아니라 분할' 을 명시하고 시험(롤업 변한 행 200개 합성)을 5.1 에 더한다. (d) 전역 단위가 여럿이면 각각이 전원 강제 포함(3.9.1)이라 셀이 359씩 늘어난다는 것을 cells_estimate 에 반영한다.

## W2-02 [major] 앵커 규칙이 실제 edge_changes 의 모양을 모른다 — hier(part_of)·scope(b=None)·bridge 엣지

- 근거(코드, 메모리에서 재현). `adapters/mcad.py:526` 은 캡처마다 전 노드에 `part_of` 엣지를 넣는다(`:879~887`). `diff.py:744~757` 은 가족을 가리지 않고 base·target 엣지 전부를 대조하므로 부품이 하나 추가되면 `p:<조립 노드>↔p:<부품> hier added` 구조 항목이 따로 생긴다. 픽스처 pair_add 에 part_of 를 전 부품에 넣어 돌리니 `c:98a6ef8c571b hier added` 가 나왔다(픽스처 원본은 part_of 가 1건뿐이라 드러나지 않는다 — 설계서의 합성기·픽스처 실험이 이 항목을 못 본 이유다).
- `adapters/dyna.py:344` 의 single_surface scope 엣지는 `b=None` 이다. `diff.py:444~452 _edge_key` 가 빈 문자열과 정렬해 `dn_a=''` 인 edge_change 를 만들고(`↔p:3dfa… contact added`), `contact.added` 이벤트의 `subject.dns` 도 `['', 'p:…']` 다(재현함).
- 설계서 3.4.1 표는 `structural.edge_changes` 의 앵커를 `[dn_a, dn_b]` 로 그대로 쓴다(`p:` 걸러내기는 semantic.events 줄에만 있다). 그대로 구현하면 (1) 추가·삭제 부품마다 (조립 노드, 부품) 쌍 원자가 생기고, 조립 노드의 asm_key 는 부품의 것과 다르므로(픽스처에서 조립 노드 asm_key=None, 부품은 `a_stack/stack_asm`) 분할이 일어난 diff 에서는 전부 **경계 단위**로 간다 — 정보가 없는 줄('hier added')로 검토 대상 단위와 셀이 불어난다. (2) 빈 dn 앵커는 `asm_of('')`·노드 조회에서 예외이거나 유령 부품이 된다 → 빌드 failed. (3) bridge 엣지는 양 끝이 같은 dn 으로 접혀 `A(dn|dn)` 쌍 원자가 된다.
- 고치는 법. 3.4.1 표에 한 줄씩 더한다 — 앵커는 모든 버킷에서 `p:` 로 시작하고 노드 표에 있는 dn 만. `kind_family='hier'` 항목은 자식 부품의 부품 원자에 싣고(부모는 문맥), `part.added/removed/tree_moved` 줄의 파생(↳)으로 접는다. `bridge` 와 양 끝이 같은 dn 인 항목은 부품 원자. 앵커가 0개가 된 항목은 전역. 커밋 1 의 합성기는 실제 캡처처럼 전 노드 part_of·scope 하이퍼엣지를 넣고, 커밋 2 시험에 'hier 변경이 경계 단위를 만들지 않는다'·'b=None 엣지에 예외 없음' 을 넣는다.

## W2-03 [major] 근거 꾸러미 B 층(실호출)의 호출 계획이 틀린 주장 위에 서 있다 — 조건은 영원히 거짓이고 인자는 실제 도구와 다르다

- `compare_reports` 의 조건 '`rr_targets.report_ids_json` 이 2건 이상'(3.8.1). 그 열을 쓰는 운영 코드는 없다 — `grep report_ids_json backend/app` 은 읽는 곳 6곳뿐이고(`planner.py:257`, `routes.py:317·1808·1836·1843`, `registry.py:1225`) `routes.py:2040~2048` 의 타깃 INSERT 열 목록에도 없다. UPDATE 는 시험(`tests/test_project_patch.py:913`)에만 있다. 게다가 `routes.py:1826~1857 list_reports` 는 그 값을 RA `rpt:` 포인터로 읽는다(해석 보고서 id 가 아니다). 그래서 이 조건은 운영에서 늘 거짓이고 compare_reports 는 한 번도 나가지 않는다. 해석 보고서 id 의 실제 자리는 스냅샷 IR 의 `results.report_ids`(`adapters/dyna.py:215`)다.
- `compare_materials` 의 인자. 설계는 `{names: [before, after]}` 인데 실제 시그니처는 `compare_materials(materials: list[str])` 다(`MaterialTwinWeb/backend/mcp_server.py:294`). `get_material` 은 `{name: after}` 가 아니라 `get_material(material_id: int)` 다(같은 파일 162행). 설계서 9절이 '확인하지 못했다' 고 적은 그 부분이고, 확인하니 둘 다 다르다.
- `compare_materials` 는 재료를 못 찾으면 예외가 아니라 `{"error": "비교하려면 유효한 재료 2개 이상 필요", …}` 를 **정상 응답**으로 돌려준다(같은 파일 305~306행). `field_source.FieldSource.fetch`(field_source.py:43~70)는 `reply.ok` 만 보고 성공 행으로 적고, 설계는 재사용 창을 10년으로 준다 → 오류 본문이 그 타깃에서 영구히 '성공' 으로 재사용된다. 나중에 재료가 등록돼도, `force` 로 다시 조립해도 같은 캐시가 나온다.
- 같은 캐시 문제가 '서비스 계정 시야의 빈 응답'(3.8.2)에도 있다. `rr_brief_calls` 의 키는 `(target_key, tool, args_hash)` 이고 자격 열이 없다(risk_store.py:548~558). 서비스 자격으로 받은 빈 결과가 먼저 캐시되면 뒤에 owner 자격으로 다시 조립해도 그 행이 돌아온다. `suspect_scope` 를 적는 것만으로는 굳는 것을 못 막는다.
- 고치는 법. 커밋 7 에서 (a) compare_reports 의 report_ids 는 base·target 스냅샷 IR 의 `results.report_ids` 에서 읽고(`rr_targets.report_ids_json` 을 쓰지 않는다), 두 스냅샷에 결과가 다 있을 때만 계획한다. (b) 재질 호출 인자를 `{materials: [before, after]}` 로 고치고 `get_material` 폴백은 뺀다(id 를 얻는 호출이 하나 더 든다). (c) 호출 계획의 인자 키를 구현 때 게이트웨이 `tools/list` 의 inputSchema 와 대조하는 시험을 둔다(모르는 키면 계획에서 빼고 gaps 에 `schema_mismatch`). (d) FieldSource 를 그대로 쓰지 말고 꾸러미용 얇은 감싸개를 둔다 — 응답에 `error` 키가 있거나 서비스 자격의 빈 결과면 `ok=0` 으로 적어 재사용되지 않게 하고, 재사용 키에 자격 종류를 넣는다. (e) 더 간단히는 B 층 전체를 이번 범위에서 뺀다(cuts 참조).

## W2-04 [major] 꾸러미·신호 조립의 경합과 기한 — REST 한 번이 3,600초를 쓰고, 동시 ensure 가 서로 다른 꾸러미를 얼린다

- `POST /api/targets/{key}/units/evidence`(3.12)는 `unit_evidence.ensure` 를 요청 안에서 돈다. 예산 기본값은 3,600초(3.13)인데 이 앱 앞의 nginx `/apps/` 는 600초에 끊는다(`config.py` 의 `DEFAULT_ROSTER_DEADLINE_S` 주석 — 같은 까닭으로 명단 조회에 540초 기한을 건 것이 커밋 cf4f135 다). 600초 뒤 화면은 빈 504 를 받고 앱은 계속 돈다. 사용자가 다시 누르면 ensure 가 둘이 된다. 검토 잡(WP3b)의 ensure 와 수동 REST ensure 도 같은 식으로 겹친다.
- 3.8.3 은 '단위마다 한 트랜잭션으로 쓴다' 고만 적고 조건이 없다. 두 ensure 가 같은 단위를 `evidence_status IS NULL` 로 보고 각자 실호출해(하나는 성공, 하나는 기한) 각자 쓴다 → 나중 쓰기가 이긴다. 첫 쓰기 뒤에 이미 돈 셀은 다른 `evidence_sha` 를 본 것이 된다. '전문가마다 같은 꾸러미' 라는 동결 규율이 깨진다.
- 자격 여유도 안 맞는다. 3.8.2 는 짧은 호출의 여유 1,800초(`runner.CREDENTIAL_MARGIN_S`)를 쓰는데 조립 예산은 3,600초다. 남은 수명 31분짜리 PAT 로 시작하면 뒤쪽 호출이 401 이고, 그 결과가 `partial` 로 **영구 동결**된다(3.8.3 '일부 실패여도 동결한다'). 게이트웨이 재기동(update-all) 한가운데에 잡이 시작해도 같은 식으로 전 단위의 B 층이 '조회 불가' 로 굳는다.
- 고치는 법. 커밋 7 에 (a) 쓰기를 비교 후 쓰기로 — `UPDATE rr_units SET evidence_* … WHERE target_key=? AND unit_id=? AND evidence_status IS NULL`, rowcount 0 이면 버린다. (b) REST 경로는 `deadline_s` 를 540 이하로 주고 `{built, remaining}` 을 돌려준다(남은 것은 다음 호출·잡이 잇는다). (c) 실패를 둘로 가른다 — 내용 탓(unknown tool·스키마·빈 결과)은 partial 로 동결, 인프라·자격 탓(연결 실패·401·403·기한·5xx)은 동결하지 않고 `evidence_status` 를 NULL 로 남겨 다음 ensure 가 다시 한다(시도 수 상한을 두고 넘으면 partial). (d) 자격 여유는 `HWAXRISK_EVIDENCE_BUDGET_S + 600` 으로 잡는다. `unit_signals.compute` 도 같은 CAS 를 쓴다.

## W2-05 [blocker] 빌드가 empty·failed 인 새 흐름 타깃은 어떤 길로도 심사할 수 없고 되돌릴 길도 없다

- 설계서 3.4.6 은 '변경 0건 → 빌드 empty, 검토 잡은 시작하지 않는다. **종전 패널 흐름은 그대로 돌 수 있다**' 고 적고, 3.14 는 U1·U2·U3·U4·U6 위반과 예외를 failed 로 둔다(첫 빌드면 단위 0).
- 그런데 WP3b(그쪽 3.4.1 끝)와 WP4 는 `rr_targets.flow` 가 새 흐름인 타깃의 Tier 패널 잡을 422 `flow_mismatch` 로 막는다. 타깃은 다시 만들 수 없다 — `routes.py:2025~2027` 이 `target_key = f"{kind}:{ref_id}"` 중복을 409 로 막는다. flow 를 바꾸는 API 는 어느 설계서에도 없다.
- 그래서 WP5 가 `HWAXRISK_REVIEW_FLOW=cells` 로 넘긴 뒤에는 (a) 자기 비교·활성 항목 0건 diff, (b) 전역 단위 넘침(W2-01)·원천 문자열 린터 적중(W2-10)·예외로 failed 가 된 빌드의 타깃이 전부 '검토 잡도 패널 잡도 못 도는' 죽은 타깃이 된다. 고치려면 DB 를 손으로 만져야 한다.
- 고치는 법. 커밋 9(`create_target` 의 flow 결정)에 넣는다 — `units.compute` 가 타깃 INSERT 보다 먼저 도므로(3.12), 빌드 결과가 `ok|oversize` 가 아니면 그 타깃은 `flow='panels'`·`defer_absent=True` 로 열고 응답에 `flow_fallback: {from:'cells', reason:<status|error>}` 를 싣는다. 그리고 셀이 0개인 타깃에 한해 `POST /targets/{key}/flow`(editor, rr_audit 동반)로 cells↔panels 를 바꾸는 길을 하나 둔다. 3.4.6 의 '종전 패널 흐름은 그대로 돌 수 있다' 를 이 규칙으로 고쳐 적고 WP3b·WP4 의 flow_mismatch 가드와 맞춘다. 계약(04)에 한 줄 더한다 — '빌드가 ok·oversize 가 아닌 타깃은 cells 로 열지 않는다'.

## W2-06 [major] U3 가 WP3a 의 단위 본문 상한(B)을 보장하지 못한다 — 넘는 단위는 전 전문가의 셀이 unit_oversize 로 failed 다

- WP3a 는 `unit_size() > unit_body_max` 를 422 `OverBudget` 으로 거절한다(그쪽 걸음 4 'B+1자 단위 → OverBudget'). WP3b 는 그 셀을 `failed('unit_oversize')` 로 둔다(자르지 않는다). 계약 C-18 에서 failed 는 종결이 아니라 사람이 정해야 실행이 끝난다. 단위 하나가 넘으면 359셀이 사람 손을 기다린다.
- 넘는 길 셋.
  1. **머리 여유 400자가 설계서의 예시보다 작다.** 3.13 `caps_for_limits` 는 `max_chars + evidence_max_chars = unit_body_max − 400` 이다. 크기 식의 머리는 `len(title)+len(summary)+len(notes)+Σlen(missing.note)+160` 인데 3.10.4 의 예시 값만 넣어도 title 28 + summary 75 + notes 약 105 + missing 약 50 + 160 = 약 418 이다. G2 주의·부분 캡처 표지·결측 둘(ecad+dyna)이면 더 크다. `missing` 의 실마리는 전문가마다 달라(3.10.4) 같은 단위도 전문가에 따라 크기가 다르다.
  2. **꾸러미 상한을 무엇으로 재는지가 없다.** 크기 식은 근거 줄마다 `len(text)+len(ref)+11` 을 세는데 3.8.3 은 '본문을 evidence_max_chars 에 맞춘다' 고만 적는다(렌더 글자 수로 맞추면 줄마다 참조 길이 + 11 만큼 모자란다). 꾸러미는 A 층이 커서 거의 늘 상한까지 찬다.
  3. **atom_oversize 예외.** 3.4.5 U3 은 부품 원자 하나가 상한을 넘으면 쪼개지 않고 단위 하나로 낸다. 6절 7번은 '16K 창에서의 분할은 WP3 의 덱 분할 몫' 이라고 적지만 WP3 의 덱은 **카드**를 나누지 단위 본문을 나누지 않는다. dev(16K) 는 `max_chars=1,564`·`max_lines=8` 이라 한 부품의 속성 변경 11줄(min_dim·bbox×3·volume·centroid×3·bbox_world×3)만으로 넘는다 — 계약 C-27 의 'dev 실 LLM 소규모' 걸음이 여기서 막힌다.
- 3.13 은 넘는 단위가 있으면 격자 전에 `build_units(force=True, reason='limits')` 로 다시 만든다고 하지만, 꾸러미는 그 뒤(첫 셀 전)에 얼고 다시 만들 길이 없다. 그리고 `build_units`·`compute` 시그니처(3.3)에는 상한을 넘길 인자가 없다(`settings` 뿐이다) — `caps_for_limits` 의 결과를 넣을 자리가 없다.
- WP5b 의 XU10(창 16,384·128,000 에서 넘는 단위 0)은 이 설계로는 통과할 수 없다.
- 고치는 법. (a) 커밋 2 — atom_oversize 예외를 없앤다. 원자가 상한을 넘으면 줄 단위로 가르고 `flags.split.rule='atom_lines'` 와 '(같은 부품 이어짐 i/n)' 줄을 단다(U6 의 '원자는 쪼개지지 않는다' 에 이 예외를 적는다). (b) 커밋 4 — `build_units(..., caps: UnitCaps | None = None)` 인자를 더한다. (c) 커밋 7 — 꾸러미를 얼릴 때 `units.unit_size()` 로 실제 크기를 재서 `unit_body_max − 줄 크기 − 최악 전문가의 머리 크기` 까지만 싣는다(상수 400 을 쓰지 않는다. limits 를 못 받았으면 설정값 상한으로). (d) 시험 — 모든 (단위 × 입력 결손이 가장 긴 영역) 의 `unit_size(review_payload) ≤ unit_body_max` 를 16K·128K 두 창에서 단언한다. 6절 7번의 'WP3 의 덱 분할 몫' 문장은 지운다.

## W2-07 [major] 전역 단위가 항목 0건이어도 서고 전원 강제 포함이다 — WP3a 의 '줄 0개 금지'·'변경 줄 인용 강제' 와 부딪친다

- 3.4.3 4단계 '검토 대상 단위가 둘 이상이면 항목이 0건이어도 만든다(단위 목록·총량 줄을 싣는다)', 3.9.1 'kind=global 단위는 forced hit'(전 전문가).
- WP3a 는 단위의 `lines` 가 0개면 안 되고(그쪽 7절 'WP2 … 줄 0개 금지'), 판정은 변경 줄 별칭(L01…)을 인용해야 하며 앱은 되돌아온 참조가 그 단위에 실은 참조인지 본다(WP3b 1047행). 단위 목록 줄에는 참조가 없다 — 계약 C-8 이 단위를 가리키는 스킴(u:)을 만들지 않기로 했다. 그래서 0건 전역 단위는 (a) lines 가 비어 요청이 거절되거나 (b) 참조 없는 줄을 실어 모든 판정이 `refs_ok=0` 이 된다. 어느 쪽이든 359명 × 카드 묶음 수만큼의 호출이 쓸모없이 나가고 내용 탓 실패 2회 뒤 failed 로 쌓인다.
- 고치는 법. 커밋 2 — 소유 항목이 0건인 전역 단위는 만들지 않는다(단위 사이 조합은 WP4 의 교차 셀 몫이라고 3.11 이 이미 적는다). 소유 항목이 있는 전역 단위만 서고, 단위 목록은 `notes` 가 아니라 `context_json` 에 둔다. 3.4.6·5.1 의 '전역·경계 없음' 시험에 '0건 전역 없음' 을 더한다.

## W2-08 [major] S-card 에 넣는 카드 어휘가 두 설계서에서 다르다 — 그대로 이으면 '독립 신호' 가 훑기의 메아리가 된다

- WP2 3.9.2 — S-card 는 `signature.vocab` ∩ **그 전문가 카드 묶음 전체**의 제목·태그 어휘이고, 묶음이 없거나 0장이면 blind 다. 7.1 은 WP3 가 `card_vocab(store, agent_key, pack_hash) -> {"tokens", "n_cards"} | None` 을 준다고 적는다.
- WP3b(862~864행) — `for_cell(..., card_vocab=…)` 에 '훑기가 **그 단위에 걸었던 카드(k)** 의 제목·태그 낱말' 을 준다. `last_check=True` 는 훑기가 `no` 라고 한 셀에만 부른다 — 그때 k 는 비어 있다.
- 그대로 이으면 훑기가 '무관' 이라 한 바로 그 셀에서 S-card 가 (빈 집합 → 겹침 0 → miss) 가 되거나 (0장 → blind) 가 된다. 앞쪽이면 제외의 근거가 전문가 자기판정 하나로 줄고(C-19 의 '결정적 신호 AND 자기판정' 이 무너진다), 뒤쪽이면 `na_irrelevant` 가 영영 나오지 않는다. 계약 04 는 함수 이름(C-8)만 정하고 이 인자의 뜻을 정하지 않았다.
- 고치는 법. 계약에 한 줄 — `card_vocab` 은 그 전문가의 **얼린 팩 전체**(`rr_expert_reports` 가 가리키는 `pack_hash`)의 제목·태그·종류 어휘다. WP2 커밋 8 의 `for_cell` 은 `card_vocab=None` 이면 스스로 `rr_expert_reports`→`rr_card_packs` 에서 읽고, WP3b 는 훑기의 k 를 넘기지 않는다. 시험 — 훑기 결과를 바꿔도 `for_cell` 의 det 가 같다.

## W2-09 [major] 신호 여럿이 실제로는 거의 늘 hit·blind 다 — 제외는 사실상 일어나지 않고, 그 값을 얻으려는 게이트웨이 호출만 남는다

- S-fts. `fts_search` 는 AND 가 0건이면 토큰 OR 로 다시 찾는다(`AIDataHub/api_server/src/api/services/search_svc.py` 의 2단 전략 — 설계서 2.7 도 인용). 질의가 `signature.vocab` 의 낱말 여럿('두께'·'재질'·'pcb'…)이므로 카드가 있는 전문가는 거의 늘 1행 이상이 나온다. 계약 C-19 가 hybrid_search 를 '늘 top_k 가 와서 변별력이 없다' 며 뺀 것과 같은 성질이다. 게다가 `for_cell(store, target_key, unit_id, agent_key, *, card_vocab, last_check)` 에는 게이트웨이를 부를 자격·설정 인자가 없다(3.3) — 누구 PAT 로 부르는지가 설계에 없다.
- S-desc. `desc_match` 는 질의 토큰이 전문가 프로필에 **부분문자열로** 하나라도 들면 0 보다 크다(`recommend_svc.py:277~290`). 구절에 '변경'·'재질'·'계면' 같은 흔한 낱말이 들어가므로(3.9.2 의 구절 예 '브래킷 두께 변경') 대부분의 프로필에서 hit 다. 호출 수는 단위 × 4(31단위면 124회, top_k≈409)다.
- S-role. 역할 표 첫 판은 정규명 10개다(3.9.3). 변경 부품 중 하나라도 역할 미상이면 hit 아닌 영역이 전부 blind 다 — 실제 단위에는 거의 늘 미상 부품이 있다(추정 — 설계서 9절도 역할 미상 비율을 모른다고 적는다).
- S-mech. `rr_delta_priors` 에 그 change_kind 로 제기된 메커니즘이 쌓일수록 `default_tools` → 영역이 넓어져 hit 가 는다(추정).
- 결과. `det='miss'` 는 거의 나오지 않는다. 누락 쪽으로는 안전하지만, 8절 결정 3 이 사용자에게 묻는 '필터를 켤지' 는 켜도 달라지는 것이 없는 선택이고, `cells_estimate = 로스터 × 단위` 가 그대로 실제 셀 수다. 비용을 줄일 수단이 없는 채로 커밋 8 의 네트워크 신호(S-desc·S-sect·S-fts·S-mech)와 `HWAXRISK_ROUTE_FILTER` 가 들어간다.
- 고치는 법. 이번 범위에서는 `for_cell` 을 순수 계산(강제 포함·S-role·S-kind·S-adj·S-card)으로만 두고 S-desc·S-sect·S-fts·S-mech 를 뺀다. `na_irrelevant` 는 `det='miss'` 가 실제 타깃에서 얼마나 나오는지 5.3 의 3번(cae00 실측)으로 잰 뒤에 켠다 — 그때까지 `HWAXRISK_ROUTE_FILTER` 의 기본을 `off` 로 둔다. 결정 3 의 문안을 '첫 판에는 제외가 없다. 셀 수 = 로스터 × 단위' 로 고친다(cuts 참조).

## W2-10 [major] 원천 문자열이 «» 밖에 서는 자리가 남아 있다 — 재질 이름 하나로 U4 가 깨져 빌드가 failed 다

- 3.6.1 의 `[요약]` 줄은 재질 정규명을 맨글로 적는다(`재질 al6061→al7075`). 3.7.1 의 digest 3)·시그니처 `vocab`·`title` 의 조립 키, 3.8.3 꾸러미 예시의 `compare_materials(names=AL6061,AL7075)` 도 맨글이다. U4 는 요약이 `render.assert_clean` 을 통과하지 못하면 빌드 failed 다(3.4.5).
- 실제 린터에 넣어 확인했다(리포 import, 메모리). `sameas.material_norm_of`(sameas.py:698~722)는 첫 토큰을 소문자로만 바꾸므로 한글이 그대로 남는다 — `강화유리` → L13 `강화` 위반, `안전유리` → L05, `개선품 AL` → L03. 꾸러미 줄은 원문 대문자라 `POKETONE`·`SUS304 OK` 가 L16 `OK` 에 걸린다(패널 브리프는 strict_lint 다 — narrative.py:1430~1436 — 그래서 EP 를 실은 쟁점 패널이 E500 으로 선다). 설계서의 예시 글 자체는 위반 0 이다.
- 커버 유리가 든 과제라면 흔한 이름이다. 그 과제의 빌드는 '코드 결함' 이라는 사유로 failed 가 되고 W2-05 의 죽은 타깃이 된다.
- 고치는 법. 커밋 2 — 규칙을 하나로 못 박는다. '소스 앱에서 온 문자열(부품명·재질 원문과 정규명·조립 키·명명 치수 이름·도구 응답의 문자열 칸)은 어디에 실리든 `sanitize_source_text` 를 거쳐 «» 안에 둔다. 코드가 «» 밖에 쓰는 낱말은 자산과 코드 상수뿐이다.' `[요약]`·digest·title·꾸러미 머리 호출 표기에 적용한다. U4 위반은 failed 가 아니라 '그 칸을 «» 로 다시 감싸 재렌더 → 그래도 안 되면 그 줄만 자리표시자 + `flags.lint_fallback`' 로 낮춘다(전체 빌드를 죽이지 않는다). 5.1 의 린터 시험 입력에 재질 `강화유리`·`POKETONE`, 조립 이름 `안전_커버` 를 넣는다.

## W2-11 [major] `hwax-risk dev-seed-pair` 가 떠 있는 앱의 DB 를 다른 프로세스로 열거나, 엉뚱한 DB 에 쓴다

- 커밋 11 은 `app/cli.py` 에 주입 명령을 더하고 5.3 의 2번은 그 명령으로 '실제 `create_diff`·`POST /targets` 를 탄다' 고 적는다.
- `app/cli.py`(29줄)는 지금 uvicorn 기동뿐이고 하위 명령이 없다. 명령을 셸에서 돌리면 데이터 루트는 `HWAXRISK_DATA_DIR > HEAX_DATA_DIR > <리포>/data` 다(config.py `resolve_data_dir`). 떠 있는 앱은 SIF 안의 `HEAX_DATA_DIR=/data` 를 쓴다(.portal/manifest.yaml 의 launch.env 주석). 그래서 (a) env 없이 돌리면 `<리포>/data/risk_review.db`(실제로 있다 — wal·shm 까지)라는 **다른 DB** 에 쓰고 화면에는 아무것도 안 보인다. (b) env 를 실 경로로 주면 `risk_store.get_store()` 가 열면서 `migrate()` 를 돈다(risk_store.py 의 get_store) — 리포 체크아웃이 떠 있는 SIF 보다 새 스키마면 실 DB 의 `user_version` 이 올라가고, 떠 있는 앱은 다음 재기동에서 'DB 스키마 버전이 앱 코드보다 높습니다' 로 **기동을 거부**한다(같은 파일 migrate 의 `current > latest`). (c) 그 저장소는 '앱 프로세스 하나가 소유' 하고 잠금이 프로세스 안 RLock 이다(RiskStore 문서열) — 두 번째 프로세스의 쓰기 트랜잭션이 sqlite 기본 대기(5초 — `sqlite3.connect` 에 timeout 을 주지 않는다)보다 길어지면 떠 있는 앱의 쓰기가 `database is locked` 로 실패한다(도는 패널의 저장 포함. 얼마나 걸리는지는 재지 않았다 — 추정).
- `POST /targets` 는 heax 신원 되묻기를 거치는 HTTP 경로라 CLI 가 '실제 경로' 를 탈 수도 없다(라우트 함수를 가짜 신원으로 직접 부르게 된다).
- fixture 과제의 `corpus_excluded=1` 은 학습·통계·회수만 거른다(brief.py:664, metrics.py:493·544·838). 스냅샷을 얼릴 때 쓰는 ckey 원장 `rr_part_keys` 는 거르지 않는다(sameas.py:787~843 이 n_projects·aliases 를 갱신한다) — 역할 낱말을 섞어 지은 합성 부품명이 같은 소유자의 실제 부품 ckey 와 겹치면 그 행에 합성 과제가 적립된다.
- 고치는 법. 커밋 11 을 CLI 가 아니라 **앱 프로세스 안의 경로**로 바꾼다 — `POST /api/dev/seed-pair`(설정 `HWAXRISK_DEV_SEED=1` 일 때만 라우터에 붙고 기본은 404, admin 한정, 과제는 `FIX-` 접두·`corpus_excluded=1`·`mcp_visibility='private'` 를 스스로 만든다). 합성 ckey 가 실제 원장과 겹치지 않게 합성 부품의 `material_norm` 에 고정 표지(`fixture`)를 넣는다. LLM 을 부르는 실주행은 WP5b 의 임시 인스턴스(임시 데이터 루트)로 하고, 5.3 의 2번 문단을 그렇게 고친다. CLI 를 꼭 둔다면 실행 전에 '그 DB 를 연 다른 프로세스가 없다' 와 '코드 스키마 버전 == DB 버전' 을 확인하고 아니면 거부한다.

## W2-12 [major] 명단 조회에 구절 호출을 얹으면 540초 기한 안에서 영역 조회가 밀려 영역이 통째로 빠진다

- 지금 `roster.RosterSource.fetch`(roster.py:128~176)는 `recommend_agents` 1회를 **먼저** 부르고 그 뒤에 영역 15개의 `list_agents` 를 부르며, 전부가 한 기한(`HWAXRISK_ROSTER_DEADLINE_S` 540초, nginx `/apps/` 600초 안의 동기 요청)을 나눠 쓴다. 기한이 지난 호출은 보내지도 않고(ra_client.py:100~134) 못 받은 영역은 `domains_failed` 로 빠진 채 로스터가 고정된다(routes.py:2030~2049, `_roster_report` 의 주석 'domains_failed 의 도메인은 좌석이 통째로 없다').
- 설계서 3.10.1 은 구절마다(최대 6) `recommend_agents` 를 부르고 `top_k` 를 '로스터 크기 + 50' 으로 올린다. 그대로 앞에 얹으면 (a) 로스터 크기는 `list_agents` 를 다 받아야 알 수 있는데 순서가 반대이고, (b) 구절 호출이 느린 날(의미 검색·도구 검색이 호출마다 돈다 — `mcp_runtime.py:237~270`) 기한을 먼저 써 버려 영역 조회가 잘린다. '전원 포함' 인 새 흐름에서 영역 하나가 빠지면 그 영역 전문가 전원이 격자에 없다. 응답 크기(409명 × 설명·태그·why)와 지연은 설계서 9절도 모른다고 적었다(추정 — 재지 않았다).
- 3.12 의 순서('units.compute → 로스터 조회(구절 질의) → 한 트랜잭션')에서 `units.roster_query(store, target_key)` 는 아직 없는 타깃 키로 `rr_units` 를 읽는 시그니처다(3.3). 타깃 행과 단위는 그 뒤 트랜잭션에서야 생긴다.
- 3.10.5 의 '아무것도 자동으로 바뀌지 않는다' 와도 어긋난다 — 질의문과 top_k 가 바뀌면 `flow='panels'` 타깃의 영역 내 순위(= Tier A 대표·Tier B 범위)가 달라진다.
- 고치는 법. 커밋 8 의 `roster.py` 수정에 순서를 적는다 — ① `list_agents` 15회를 먼저(필수), ② 남은 기한의 절반까지만 구절 호출(구절 수 상한 6, 기한이 모자라면 받은 구절까지만 쓰고 `relevance_source='partial'` 과 받은 구절 수를 응답에 싣는다), ③ `top_k = len(agents) + 50`. 구절은 저장소가 아니라 계산 결과에서 만든다 — `units.roster_phrases(built: Mapping, max_phrases=6) -> list[str]`(순수 함수)로 시그니처를 바꾼다. 구절 질의는 `flow='cells'` 타깃에만 쓰고 panels 타깃은 WP1 이 고친 `query_text` 그대로 둔다(3.10.5 를 지킨다).

## W2-13 [major] 단위·빌드 행에 바뀌는 칸(active · rev_last · seq · '소유 Uxx')이 있어 박스 간 들여오기와 부분 재빌드에서 어긋난다

- 들여오기 규칙. `export.import_jsonl`(export.py:300~412)은 PK 가 같은 행이 다르면 '사람 확정' 순위가 높을 때만 덮고 그 밖에는 **건너뛴다**. `rr_units`·`rr_unit_builds` 는 순위 0 이라 다르면 늘 건너뛴다. PK 는 없는데 UNIQUE 만 겹치는 새 행은 `unique_conflict` 로 그 줄만 눕힌다(같은 파일 364~371행).
- 설계서 3.2·3.4.8 은 `rr_unit_builds.active`(부분 유니크 인덱스 `ux_rr_unit_builds_active`)와 `rr_units.rev_last` 를 **고쳐 쓰는** 칸으로 둔다('새 빌드에도 있는 unit_id 는 rev_last 만 올린다', '직전 rev 의 active 가 0 이 된다').
- 깨지는 순서. 박스 A 에서 rev 1 로 연 타깃을 B 로 옮긴다 → A 에서 limits 재빌드로 rev 2 가 활성이 된다(3.13 — 설정 상한과 limits 가 다르면 잡 시작 때마다 일어나는 평소 길이다) → 결과를 다시 B 로 들여온다. B 에서는 (T, rev 1) 은 active 값이 달라 건너뛰고, (T, rev 2, active=1) 은 B 의 rev 1 이 아직 active=1 이라 유니크 충돌로 눕고, 이어진 단위는 rev_last 가 달라 건너뛴다. B 의 활성 빌드는 rev 1 로 남고 '활성 단위 = rev_last 가 활성 rev' 규칙으로 rev 1 의 단위들이 살아 있는 반면, 같이 들어온 WP3 의 셀·판정은 rev 2 의 unit_id 를 가리킨다. 보고서·커버리지가 서로 다른 단위 집합 위에서 계산된다. 설계서의 왕복 시험(5.2)은 **빈 DB** 로만 들여와서 이 길을 타지 않는다.
- 부분 재빌드에서도 같은 뿌리다. 요약 글은 `[검토 단위 3/31 …]`·`(소유 U09)`·`(소유 U31)` 처럼 순번을 박아 얼린다(3.6.1). 재빌드에서 id 가 유지된 단위는 `rev_last` 만 오르므로(3.4.8) 글 속의 3/31 과 U09 가 새 빌드의 순번과 어긋난 채 전문가에게 간다. `seq` 열을 고치는지도 적혀 있지 않다(고치지 않으면 같은 seq 가 둘이 된다).
- `rr_unit_builds` 의 failed 행도 걸린다. `builder_version·input_hash·source_hash·mode·caps_json·stats_json·invariants_json` 이 전부 NOT NULL 이고 `active` 의 기본값이 1 이다 — 예외로 죽은 빌드(3.12 '단위 계산이 예외를 내면 … failed 한 행을 남긴다')는 그 값들을 모르고, active 를 0 으로 명시하지 않으면 유니크 인덱스에 걸리거나 활성 자리를 차지한다.
- 고치는 법. 커밋 3 의 DDL 에서 (a) `active` 열과 부분 유니크 인덱스를 뺀다 — 활성 빌드는 '그 타깃에서 status ∈ (ok, empty, oversize) 인 가장 큰 rev' 로 읽는다(파생). (b) `rev_last` 대신 빌드 행에 `unit_ids_json`(그 rev 의 단위 id 와 seq 목록)을 둔다 — 단위 행은 한 번 쓰고 고치지 않는다. (c) 요약 글에는 순번을 박지 않는다 — 머리의 `3/31` 과 `(소유 U09)` 는 읽을 때 `unit_ids_json` 으로 붙이고, 얼린 글에는 `(소유 <unit_id>)` 만 둔다. (d) failed 행을 위해 NOT NULL 칸에 기본값(`''`·`'{}'`)을 준다. (e) 5.2 에 '옛 rev 가 있는 DB 로 들여오기' 시험을 더한다. 꾸러미·신호처럼 NULL → 값으로 한 번 바뀌는 칸은 들여오기에서 건너뛰어도 다음 ensure 가 채우므로 둔다(다만 박스마다 꾸러미가 달라질 수 있다는 것을 README 에 적는다).

## W2-14 [major] WP4·WP3b·WP5b 가 부르는 이름·시그니처 여럿이 이 설계에 없다 — 계약(04)도 정하지 않았다

- 7.4 는 WP4 에 대해 '`units.list_units`·`part_roles`·`unit_domains` 를 그 이름·값으로 맞췄다' 고 적지만 WP4 7.1(그쪽 1511~1517행)이 받는다고 적은 것과 다르다.

| WP4 가 부르는 것 | 이 설계(3.3) |
|---|---|
| `units.unit_text(store, target_key, unit_id, *, ckeys=None, budget=None) -> str` | 없음. `panel_evidence(..., refs=…, budget_chars=…) -> dict` 가 가장 가깝다(거르는 열쇠가 ckey 가 아니라 참조다) |
| `units.evidence_pack(store, target_key, unit_id, *, ckeys=None) -> list[{tool,args,result}]` | 없음 |
| `units.unit_refs(store, target_key, unit_id) -> set[str]` | 없음(`ref_index` 는 타깃 전체의 참조 → 소유 단위) |
| `units.part_roles(store, target_key, ckeys) -> dict[ckey, list[str]]` | `part_roles(store, target_key, unit_id) -> dict[dn, str \| None]` — 인자·키·값이 다 다르다. ckey 는 충돌 노드에서 null 이다(sameas.py:650) |
| `units.role_domains(role) -> list[str]` | 없음 |
| `units.unit_domains(...) -> list[{domain, basis}]` | `-> dict[str, list[str]]` |
| `units.unassigned_n(store, target_key) -> int` | 없음(`invariants_json.U1_unassigned`) |
| `rr_units.ckeys_json`·`size_chars` | 없음(`cids_json`·`summary_chars`·`evidence_chars`) |

- WP3b(그쪽 1657~1658행)는 `units.packets(store, target_key, max_chars=…)` 를 부르고 `review_payload` 가 글 한 덩이를 준다고 전제한다(이 설계는 `manifest_items` 와 줄 구조). WP5b(그쪽 438~441·1066행)는 `rr_units.refs_json`·`content_hash` 를 읽는다(이 설계는 `cids_json`·`unit_hash`).
- 계약 C-8 은 `unit_signals.for_cell`·`units.load_units`·`rr_unit_builds` 만 정했다. 위 이름들은 어느 쪽으로도 정해지지 않았다 — WP4 의 폴백(`cross-pairs.v1.json`, 역할 미상 = `[mech, xd]`)이 조용히 타게 되고, 그러면 같은 부품의 역할이 WP2 신호(미상 = blind)와 WP4 교차 칸(미상 = mech·xd)에서 다르게 읽힌다.
- 고치는 법. 계약에 표 한 장을 더하고(WP2 가 소유) 이 설계 3.3·7.2 에 반영한다 — `units.unit_refs(store, target_key, unit_id) -> set[str]`(소유 + 문맥 + 꾸러미 참조), `units.part_roles(store, target_key, *, unit_id=None, dns=None) -> dict[dn, str | None]`(열쇠는 dn 으로 통일), `units.role_domains(role)`, `unit_domains -> dict[domain, list[basis]]`, `unassigned_n`, 그리고 `panel_evidence` 에 `dns=` 거름 인자. WP4 의 `unit_text`·`evidence_pack` 은 `panel_evidence` 로 접는다고 적는다. 열 이름은 `cids_json`·`unit_hash` 로 통일(WP4·WP5b 가 고친다).

## W2-15 [major] snap 단위의 `joint`·`material_null`·`result` 신호군이 사실상 전량이다 — 결정 6 의 전제와 어긋나고 셀이 수만으로 는다

- 3.5 의 표에서 `joint` 는 'kind ∈ tied·touching·geometric·contact 계면' **전부**가 항목이다(걸러 내는 조건이 없다). `material_null` 은 재질 미기재 리프 전부, `result` 는 `results.part_risk` 행 전부다. 집계 줄로 접는 것은 '신호에 걸리지 않은' 것(예: 0.2mm 초과 clearance)뿐이다.
- 8절 결정 6 은 '리프 1,500·계면 6,000 을 다 항목으로 실으면 단위가 수십 개 늘고 셀이 만 단위로 는다' 며 기본을 '신호 항목 전수 + 나머지 집계' 로 권한다. 그런데 계면의 대부분은 clearance 가 아닌 접합이라(추정 — 실제 비율은 재지 않았다) 기본 모드가 이미 전량에 가깝다. 접합 3,000건이면 `snap_max_lines` 70 으로 40단위가 넘고, snap 은 전 단위가 전원 강제 포함(3.9.1)이라 40 × 359 = 14,000셀이 joint 만으로 나온다. `units_max` 60 은 늘 넘어 빌드가 늘 oversize 다.
- 고치는 법. 커밋 5 에서 `joint`·`material_null`·`orphan`·`result` 는 '표지가 붙은 것만 항목' 으로 좁힌다 — joint 는 status=auto·cross_file·lower_bound·규칙 적중 refs·띠 면적 하위 분위, result 는 요구 한계 대비 여유가 작은 행. 나머지는 조립별 집계 줄(건수·분포)이다. 아니면 snap 단위를 이번 범위에서 미룬다(cuts 참조) — 그 경우 snap 타깃은 W2-05 의 규칙으로 `flow='panels'` 로 연다.

## W2-16 [major] 입력 결손의 배선이 반쪽이다 — mcad_absent 에는 질문이 없고, 옛 타깃의 대표석에는 결손이 적히지 않는다

- 3.10.1 은 `risk_mcad_domains`(mech·cam·xd·disp·sh — config.py:43)이고 `mcad_absent` 면 `'mcad_absent'` 결손을 얼린다. 3.10.4 는 `input_gaps` 가 비어 있지 않으면 WP3b 가 `noinput` 호출로 보낸다고 적는다. 그런데 `input-gap.v1.json` 과 3.10.2 의 문안·실마리는 ECAD 것뿐이다(질문 1 이 '기구 변경이 당신 영역에 주는 영향'). MCAD 가 없는 타깃(해석만 있는 스냅샷 — `ir_builder.py:1097` 이 `mcad_absent` 를 낸다)에서는 가장 큰 다섯 영역(xd 122명 포함 198명)이 카드 대조 대신 뜻이 안 맞는 두 질문으로 가고, 영향을 못 내면 `no_input` 으로 '검토함' 에서 빠진다. 지금은 `risk_mcad_domains` 를 읽는 코드가 없어(설계서 2.3) 그 전문가들이 보통 좌석으로 돈다 — 고치면서 범위가 준다.
- 옛 타깃. `undefer` 는 `deferred(reason='ecad_absent')` 행에만 `input_gaps_json` 을 채운다(3.10.5). 회로 영역의 1순위 대표 6명은 보류된 적이 없어(planner.py:143) 결손이 NULL 로 남는다. 같은 영역에서 104명은 `noinput` 길, 대표 6명은 보통 카드 대조 길로 간다(새 타깃은 110명 전부에 적힌다고 커밋 9 가 단언한다).
- 8절 결정 5 의 까닭('끝난 줄 알았던 타깃이 다시 열린다')은 코드와 다르다. `registry.close_level` 은 저장된 level 보다 낮아지지 않는다(registry.py:999~1001). 보류를 풀면 need 는 오르지만 level 은 `C2(closed)` 그대로다 — 화면에는 닫힌 타깃인데 depth 는 미달로 보인다.
- 고치는 법. 커밋 9 — (a) 이번 범위의 결손은 `ecad_absent` 하나로 한다. `mcad_absent` 는 `rr_roster.input_gaps_json` 에 적지 않고 `unit.missing` 의 타깃 수준 결측 표기로만 싣는다(전문가는 보통 길로 간다). (b) `undefer` 가 아니라 따로 `planner.backfill_input_gaps(target_key)` 를 두어 그 타깃의 ECAD 의존 로스터 행 **전부**(`rr_roster.ecad_dependent=1`)에 결손을 채운다 — undefer 와 옛 타깃에 검토 잡을 처음 얹을 때 부른다. (c) `undefer` 응답에 '저장된 level 은 내려가지 않는다' 와 영역별 need·have 를 싣고, 결정 5 의 문안을 그렇게 고친다.

## W2-17 [minor] 동형 묶음 줄은 참조가 여럿인데 줄 구조는 참조 하나다

- 3.6.3 은 같은 변화 4건 이상을 한 줄로 묶고 참조 12개를 그 줄에 싣는다. 계약 C-14 와 WP3a 의 줄은 `lines[{ref, text}]` — 참조 하나에 별칭(L07) 하나다. 서버는 별칭을 그 줄의 ref 하나로 되돌리고 앱은 그것이 '실어 보낸 참조' 인지 본다(WP3b 1047행). 묶음 줄을 그대로 구조에 넣으면 나머지 11개 참조는 인용도 검증도 되지 않고, text 안에 넣으면 서버가 «» 로 감싸 원천 데이터가 된다.
- 고치는 법. 커밋 2 — 줄 구조(`lines_gz`)는 항목당 한 줄을 유지하고 `group` 키만 단다. 접어 쓰는 것은 사람·패널용 렌더(`summary_gz`)에서만 한다. 줄 수·크기(U3)는 구조 기준으로 센다.

## W2-18 [minor] 단위 id 의 `u:` 접두가 참조 스킴처럼 보인다

- 3.4.4 의 id 는 `u:<hex12>` 이고 요약 머리(`[검토 단위 3/31 · u:5d0c1e9a77b2 · …]`)·꾸러미 머리·패널 질문(3.11 `{unit_id}`)에 `[c:…]`·`[p:…]` 와 나란히 찍힌다. 계약 C-8 은 u: 스킴을 만들지 않기로 했다 — `render.LINT_NEUTRAL_PATTERNS` 의 스킴 목록에도 없다. 좌석이 `[u:…]` 를 인용으로 적으면 모르는 스킴이라 dangling 으로 센다.
- 고치는 법. id 를 `u-<hex12>` 로 하고(WP3a 의 예시도 `u-07` 이다) 모델에게 가는 글에는 순번만 쓴다.

## W2-19 [minor] 패널 질문에 부품 실명이 «» 없이 들어가고, 단위 빌드의 인젝션 적중은 큐에 오르지 않는다

- 3.11 의 질문은 `{title} — {digest}` 와 `낱말: {signature.vocab}` 을 그대로 잇는다. digest 의 6)은 부품 이름이고(3.7.1) title 은 조립 키다 — 소스 앱 문자열이 지시문 자리로 간다. 질문은 린터 대상이 아니라는 것(같은 절)은 판단어 얘기이고 인젝션은 별개다. 지금 질문에도 소스 ref 값과 요약 첫 줄 200자가 들어가지만(runner.py:358~377) 부품 실명 목록을 지시문에 싣는 것은 이 설계가 처음이다.
- `units.compute` 는 DB 를 쓰지 않는다(3.3). 브리프는 `begin_suspect_queue`(brief.py build_brief)로 인젝션 적중 문자열을 `rr_curation_queue` 에 올리는데, 단위 빌드에서 걸린 문자열은 올릴 자리가 없다. 새 흐름은 브리프를 거의 만들지 않으므로 사람이 그 문자열을 볼 길이 없어진다.
- 고치는 법. 커밋 2 — digest 의 이름 칸도 `sanitize_source_text(…, 'label')` 로 감싼다. 커밋 10 — 질문에는 digest 의 1)~5)(코드가 만든 건수·종류·수치 범위)만 넣는다. 커밋 4 — `compute` 가 `suspects[]` 를 돌려주고 `persist` 가 같은 트랜잭션에서 큐에 적재한다.

## W2-20 [minor] cid 가 없는 사실은 단위에 실리지 않는다 — 고아 전이, 스냅샷 강등 표지

- U1 의 기준은 cid 순회다(3.4.5). `structural.orphans_delta`(became_orphan·left_orphan — diff.py:760~768)에는 cid 가 없고 의미 이벤트도 없다. 부품이 모든 접합을 잃었다는 사실은 계면 삭제 줄들에서 유추해야 한다.
- 꾸러미 A 층은 '그 부품이 끼인 계면 전부' 를 싣는다고 하지만(3.8.1) 캡처가 계면을 잘랐으면(`adapters/mcad.py:515` `interfaces_truncated`) 전부가 아니다. 3.10.4 의 `missing` 은 ecad·mcad·dyna 결측과 `semantic_blocked` 만 싣는다.
- 고치는 법. 커밋 2 — `[부품]` 줄의 상태에 `고아됨`·`고아 벗어남` 을 적는다(orphans_delta 에서). 커밋 7 — 두 스냅샷의 `degraded_json` 코드를 `notes` 에 옮긴다('계면 목록이 잘린 캡처다' 등).

## W2-21 [minor] R-32 는 자산만 고쳐서는 닫히지 않는다

- 커밋 2 는 `taxonomy.v1.json` 의 change_kind 축에 `contact_type`·`parameter` 를 더한다. 그런데 finding 의 change_kind 를 `none` 으로 보정하는 목록은 자산이 아니라 `narrative.py:111~114 _CHANGE_KINDS`(12종 하드코딩)이고(`:980~983`), `schemas/risk_spec.v1.json:118` 의 enum 도 12종이다. 두 곳을 같이 고치지 않으면 WP1 이 넘긴 결함(R-32)이 그대로다.
- 계약 C-30 은 이 추가를 '택소노미 1.1' 에 메커니즘 14종과 묶었다. WP2 가 먼저 나가면서 1.1 을 쓰면 WP4 의 14종이 같은 판을 다시 고치게 된다.
- 고치는 법. 커밋 2 의 파일에 `narrative.py`·`schemas/risk_spec.v1.json` 을 더하고 '자산 축 == `_CHANGE_KINDS` == 스키마 enum ⊇ diff 가 내는 change_kind' 시험을 둔다. 판번호는 WP2 가 1.1, WP4 가 1.2 로 적는다(계약에 한 줄).

## W2-22 [minor] 폐기가 지우지 않는 원문이 남는다

- 3.2 의 PURGE 등록은 `summary_gz`·`lines_gz`·`evidence_gz`·`context_json`·`title`·`digest`·`signature_json` 이다. 남는 것 — `scope_key`·`split_from`(조립 경로 원문), `signals_json.phrases`(재질명·역할 낱말로 지은 구절), `evidence_json`·`evidence_gaps_json`(호출 인자에 재질명·보고서 id), `flags_json`.
- 고치는 법. 커밋 3 의 PURGE_BLANK_SQL 에 그 열들을 더하고 '폐기 뒤 rr_units 행에 과제 문자열이 남지 않는다' 시험에 표지 문자열(부품명·재질명)을 심어 전 열을 훑는다.

## W2-23 [minor] 계약(04)의 빈칸 둘과 새 흐름 문이 먼저 열리는 것

- C-1(WP2 가 WP3b·WP4 보다 먼저 나간다)과 C-2(v4 는 새 흐름의 표·열 전부를 한 블록, push 뒤에는 고치지 않는다)가 같이 서려면 WP2 커밋 3 전에 WP3b·WP4·WP5a 의 DDL 이 동결돼 있어야 한다. 커밋 3 의 선행 칸에는 'WP5a 의 블록과 순서를 맞춘다' 뿐이다. 블록을 나눠 낼 것이면(v4 = WP2, v5 = WP3b …) 계약을 그렇게 고쳐야 한다. `rr_targets.flow` 는 WP4 가 더한다고 3.2 가 적는데 커밋 9 가 그 열을 읽는다 — WP4 보다 먼저 나가는 WP2 가 넣어야 한다.
- C-30 의 MCP 도구 수 14 → 18 은 `risk_get_issues·risk_get_cross·risk_get_mech_grid·risk_get_report` 넷이다. 이 설계의 `risk_get_units`(3.12)와 WP3b 의 둘은 세지 않았다. `tests/test_mcp_tools.py:14~29` 의 고정 목록과 매니페스트 설명('MCP 도구 14종')이 꾸러미마다 다른 수로 고쳐진다.
- 커밋 9 는 본문 `flow='cells'` 를 받는다(3.10.1). Tier 잡을 막는 `flow_mismatch` 가드는 WP3b·WP4 의 것이라 그 전에는 cells 타깃에 종전 Tier 잡이 돈다 — 회로 104명이 입력 결손 질문 없이 보통 패널에 앉는다(plan §6.3 이 피하려던 것).
- 고치는 법. 계약에 (a) 스키마 블록을 누가 언제 내는지, (b) 도구 최종 목록을 적는다. 커밋 9 에 `runner.create_job` 의 flow 가드를 같이 넣고, `flow='cells'` 는 설정 스위치(기본 꺼짐 — C-27)가 켜졌을 때만 받는다(아니면 422).

## W2-24 [major] 단위 저장이 타깃 생성 트랜잭션 안에 들어가 지금 도는 패널 흐름의 타깃 생성을 같이 넘어뜨릴 수 있다

- 3.12 는 `POST /targets` 를 '한 트랜잭션으로 타깃 행·`units.persist`·로스터 동결·승계' 로 바꾼다. 예외를 삼키는 것은 계산(`units.compute`)뿐이다('단위 계산이 예외를 내면 타깃은 그대로 만들고'). `persist` 가 던지면(불변식 검사·NOT NULL·직렬화) `store.tx()` 가 통째로 되돌린다(risk_store.py 의 tx — 안쪽 예외는 바깥까지 올라가 전체 rollback 이고 savepoint 가 없다). 타깃이 열리지 않는다.
- 이 훅은 flow 와 무관하게 탄다(3.10.5 '단위 빌드는 종전 타깃에도 해가 없다'). 계약 C-27 대로 새 흐름을 꺼 둔 채 WP2 가 먼저 운영에 나가면, 시험이 본 적 없는 실제 diff 모양(W2-02 의 hier·scope 엣지 등)을 새 코드가 처음 만나는 자리가 **운영의 패널용 타깃 생성**이다.
- 고치는 법. 커밋 4 — `flow='panels'` 타깃은 `create_target` 에서 단위를 만들지 않는다(재려면 `POST /targets/{key}/units` 로 따로). `flow='cells'` 타깃도 타깃·로스터 트랜잭션을 먼저 닫고 `persist` 는 그 뒤 제 트랜잭션에서 한다(실패하면 failed 행 + W2-05 의 flow 되돌림). 시험 — `persist` 가 던지게 만든 상태에서 `POST /targets` 가 200 이고 타깃·로스터가 남는다.

---

## 빼거나 미룰 것(cuts)

1. **근거 꾸러미 B 층(실호출)** — `compare_reports`·`compare_materials`·`get_material`·`list_interfaces` 실호출, 자격 순서, 기한·예산 손잡이 셋, `suspect_scope`. 잃는 것: 꾸러미의 재질 물성 비교표와 보고서 비교 줄, `tool:b-…` 인용. 재질 수치 변화는 diff 의 `material.E/rho/sigy` 항목과 A 층 부품 명세에 일부 남고, 해석 결과는 A 층의 `report_part_risk` 동결본에 남는다. 까닭: 조건·인자가 틀렸고(W2-03), 4,500자 안에서 우선순위가 맨 뒤라 큰 단위에서는 어차피 잘리며, 경합·자격·캐시 문제(W2-04)의 대부분이 이 층에서 난다. 언제: A 층만으로 돈 실제 타깃에서 '판정 불가' 가 재질·결과에 몰리는 것을 본 뒤.
2. **네트워크 신호와 제외 자체** — S-desc·S-sect·S-fts·S-mech, `HWAXRISK_ROUTE_FILTER`, `unit_signals.compute` 의 게이트웨이 호출(단위 × 4 회). 잃는 것: 무관한 셀을 건너뛰는 비용 절감 — 다만 지금 설계로는 거의 일어나지 않는다(W2-09). 순수 계산 신호(강제 포함·S-role·S-kind·S-adj)는 표기와 순서용으로 남긴다. 언제: 역할 표가 확정되고 cae00 실측에서 miss 가 얼마나 나오는지 본 뒤.
3. **snap 단위(커밋 5)와 snap 손잡이 셋** — 잃는 것: 현황(snap) 타깃은 새 흐름을 타지 못하고 패널 흐름에 남는다. 까닭: 사용자 목표는 변경 분석이고, 지금 정의는 전량에 가깝다(W2-15). 언제: diff 흐름이 cae00 시범(C-27)을 지난 뒤.
4. **`mcad_absent` 입력 결손** — 잃는 것 없음(질문·실마리가 아직 없다 — W2-16). R-56 의 `risk_mcad_domains` 소비는 미결로 남긴다.
5. **`panel_question(unit=…)`·`build_delib_opts(unit=…)`(커밋 10 의 runner 쪽)** — 7.4 가 이미 'WP4 가 제 함수로 만들면 만들지 않아도 된다' 고 적었다. `units.panel_evidence`·`review_payload` 만 한다. 잃는 것 없음(같은 일을 두 곳에 만들지 않는다).
6. **`hwax-risk dev-seed-pair` CLI(커밋 11)** — WP5b 의 임시 인스턴스 + `app/devseed.py` 로 대신한다(W2-11). 잃는 것: 배포된 스택(SIF·Caddy·위임)을 합성 쌍으로 한 번에 지나는 확인 — 그것은 cae00 의 실제 타깃에 `POST /units` 를 돌리는 5.3 의 3번이 LLM 호출 없이 대신 본다.
7. **MCP 도구 `risk_get_units`** — REST 로 충분하고 계약 C-30 도 세지 않았다. 잃는 것: MCP 클라이언트가 단위를 읽지 못한다. 언제: 새 흐름의 MCP 읽기 도구를 한꺼번에 정할 때.
8. **동형 묶음을 구조에서 접는 것(3.6.3)** — 렌더에서만 접는다(W2-17). 잃는 것: 전문가 호출의 줄 수 절감(반복 변화가 많은 단위가 더 잘게 나뉜다).

## 직접 확인해 맞았던 주장

- 대조한 HEAD 가 설계서와 같다(HWAXRisk 7248651 · HWAXAgentServer 7683125).
- `rr_diff_events` 에는 의미 이벤트만 간다(diff.py:1743~1753). `part.thickness_changed` 는 `elif` 라 같은 부품의 bbox·volume 변화에 이벤트가 없다(1363~1378) — 픽스처 pair_thick 을 메모리에서 돌려 변경 파라미터 5건·이벤트 1건을 확인했다.
- 계면 이벤트는 `min_gap`·`contact_area_est`·`penetration_depth`·`fs` 넷뿐이다(1425~1428). 한 노드의 속성 하나에 `excluded_reason` 이 있으면 그 노드 이벤트를 전부 건너뛴다(1336~1339). G2 면 이벤트 0(1241~1243). capture_partial 은 파라메트릭·edge_changes 에 사유를 붙이고 이벤트를 비운다(1536~1546). 같은 쌍의 diff 는 재사용한다(1698~1703).
- `SpecContext.diff_item` 은 `structural.dyna.scope_changed` 를 못 찾는다(narrative.py:339~362). `[c:]` 의 정규 표기는 항목 text 이고 인용 대조는 정확 부분문자열이다(render.py:392~419, narrative.py:719 부근).
- 로스터 보류 규칙과 전이표(planner.py:56·143~145), `refresh_roster` 가 ECAD 와 무관하게 pending 으로 넣는 것(199행), 그 둘을 못 박는 시험(tests/test_planner.py:522~553).
- `risk_mcad_domains` 는 소비처가 없다(grep). 로스터 순위는 `summary_text[:500]` 한 번·top 60·`score` 만 읽는다(roster.py:20~21·97·151).
- `runner.panel_question`·`build_delib_opts` 의 지금 시그니처와 줄 번호, `brief.CAPS` 값, 판단어 어휘 17종. 설계서 3.6.1 의 요약 예시는 실제 린터를 위반 0 으로 지난다(돌려 봤다).
- `state._TOP_K = 10`, 마이그레이션 허용 연산과 버전 규칙, `store.tx()` 가 BEGIN IMMEDIATE, 등록 지점 셋(`_SINCE_COLS`·`TRANSFER_DERIVED`·`PURGE_BLANK_SQL`)과 시험 고정값(test_store·test_mcp_tools).
- `desc_match` 는 프로필 부분문자열 비율이고 `recommend_agents` 에 top_k 상한이 없다(recommend_svc.py·mcp_runtime.py:237). `fts_search` 는 좌석 범위를 SQL 로 걸고 AND 0건이면 OR 로 다시 찾는다.
- PLAN_SIZES 합 359·B 누적 114, 회로 6개 영역 110명 = 104 + 대표 6.
- WP1 의 공용 표기 함수(`split_trailing_refs`·`humanize_refs`·`norm_quote`·`name_index`·`event_order`)는 지금 HEAD 에 없다 — 설계서가 'WP1 이 준다' 고 적은 그대로다.

## 확인하지 못한 것

- 실제 diff 의 모양 — 변한 롤업 행 수, hier 엣지 변경 수, 접합 대 clearance 비율, 재질명에 한글이 섞이는지. W2-01·W2-02·W2-10·W2-15 의 발생 빈도가 여기에 달렸다.
- 게이트웨이를 거친 `recommend_agents(top_k≈409)` 의 지연과 응답 크기(네트워크 호출을 하지 않았다). W2-12 의 '기한을 먼저 쓴다' 는 그래서 추정이다.
- cae00 의 실제 `unit_body_max`(WP3a 구현 뒤 실측값). W2-06 의 넘침 폭이 여기에 달렸다.
- 실제 캡처에서 조립 노드의 `asm_key` 값(픽스처는 None). W2-02 의 경계 단위 수가 여기에 달렸다.
- 두 번째 프로세스가 실 DB 를 열었을 때 잠금이 실제로 5초를 넘기는지(W2-11).
- 매니페스트의 `memory_gb: 2` 가 실제로 강제되는지, 두 스냅샷의 `ir_json` 을 통째로 읽는 꾸러미 조립이 그 안에 드는지.
- snap 타깃에서 요구 편집으로 `rr_states` 가 다시 계산될 때 이미 선 단위가 어떻게 되는지(자동 재빌드 경로가 설계에 없다).
- HEAXHub 의 등록 사본 매니페스트(`integrations/hwax-risk`)에 새 손잡이를 같이 적는 걸음이 WP5 에 있는지.
- WP1 이 이 꾸러미로 넘긴다고 적은 것 가운데 `brief.change_digest(unit_id=…)`·`risk_get_diff(part='lines')` 의 묶음 거름 인자는 이 설계에 없다 — 누가 받는지.

## 판정

뼈대(원천을 `diff_json` 세 층으로 삼고, 소유 하나·문맥 반복으로 묶고, 불변식을 코드가 검사하고, 신호는 포함만 시킨다)는 코드 사실 위에 서 있고 2절의 주장은 거의 전부 맞았다. 그러나 이대로 구현하면 빌드가 failed·empty 인 새 흐름 타깃이 어느 길로도 돌지 못하고(W2-05), 그 failed 를 만드는 길이 여럿이다 — 전역 단위 넘침, 실제 엣지 모양, 맨글 재질명. 단위가 WP3a 의 본문 상한을 넘지 않는다는 보장이 없고(W2-06), 꾸러미 B 층은 틀린 조건·인자 위에 있으며(W2-03), 신호는 거의 거르지 못한다(W2-09). 다른 꾸러미가 부르는 함수 여럿이 없다(W2-14). B 층·네트워크 신호·snap 을 미루고 W2-01·02·05·06·07·10·24 를 걸음에 넣으면 선다.

## 작업 메모

- 코드 동작 확인용 탐침 스크립트 셋을 스크래치패드의 `wp2probe/` 에 잠깐 만들어 돌렸고(리포 import 만, 임시 데이터 루트, 바이트코드 미기록) 끝난 뒤 지웠다. 리포 넷(HWAXRisk · HWAXAgentServer · AIDataHub · MaterialTwinWeb)은 읽기만 했고 HWAXRisk 의 `git status` 는 비어 있다.
