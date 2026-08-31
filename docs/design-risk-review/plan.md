<!-- 설계 리스크 심사 메뉴의 구현 계획서 — 공통 정본(§0)부터 IR·diff·서술·저장·워크플로·학습·통합·단계·열린 질문(§1~§10)까지 구현자가 바로 쓰는 필드·slug·API·상태기계·수치 게이트를 한 문서로 고정한다 -->

# 설계 리스크 심사 — 계획

이 문서는 설계 리스크 심사를 HEAX 앱 `hwax_risk`(리포 `HWAXRisk`)로 만들고 HWAX Portal 에는 '리스크 심사' 메뉴 창을 붙이는 구현 계획이다. 과제의 MCAD(StepForge)·Dyna(DynaForge)·ECAD(ODB hub 어댑터 계약, 스텁) 소스를 읽기 전용으로 읽어 불변 설계 IR 스냅샷(rr_ir)으로 동결하고, 단일 스냅샷의 상태(rr_state)와 두 스냅샷의 3층 diff(rr_diff)를 결론 없이 코드가 정리하며, HW/XD 전문가 로스터 ≈350석이 한 번씩 자기 도구를 실호출해 낸 finding·gain·성격 서술을 IR id 에 앵커된 원자로 앱 DB(`$HEAX_DATA_DIR/risk_review.db`)·ReportArchive KG(관리 API·MCP 만, RA 코드 무수정)·AIDataHub 3층에 저장하고, 그 저장물을 다음 과제와 계보 없는 다른 connectivity 의 심사 브리프에 원천 그대로 되먹여 '리스크 심사 보고서' 를 낸다. §0 이 전 절이 공유하는 이름의 정본이고, §1~§10 은 그 이름만 써서 스키마·임계·상태 전이·API 인자·통과 기준을 적는다. 기존 심의 메뉴·엔진·소스 앱은 additive 변경(dict 항목·조건부 1줄·`systems.yaml` 타일 1건)만으로 잇고 기존 기능은 손상하지 않는다.

## 목차

| 번호 | 제목 |
|---|---|
| §0 | 공통 정본(spine) — 용어·참조 규약·저장 3층·파일·API·상수·1차 비평 반영 |
| §1 | 핵심 명제 — 한 줄 정의·산출물·하지 않는 것·헌법 준수 |
| §2 | 설계 IR(rr_ir) — 봉투·노드·엣지·소스 매핑표·same-as 사다리·전역 정규 키·dims_named·원장·ir_hash·게이트 입력·어댑터 계약 |
| §3 | 그래프 diff 와 상태 평가 — rr_state(G1~G7·signals·character_seed·feature_vector·rule_hits)·rr_diff 3층·의미 이벤트·summary_text·판단어 린터 |
| §4 | 과제 평가 서술 — risk_spec·finding·cites·seat_opinion·character_narrative·등록부 병합·무효화·실례 |
| §5 | 저장과 재사용 — 앱 DB DDL·RA KG 6축 12관계·AIDataHub doc_type·id 연결·prior_evidence E0~E9·유사 검색·다른 connectivity 회수 |
| §6 | 전문가 크로스도메인 워크플로 — 로스터·planner·좌석 계약·Job 'risk-review'·runner·커버리지 상태기계·완결 판정·비용·MCP 등급 |
| §7 | 학습 루프 — 택소노미·인덱스·유사 검색·delta 선례·승격 상태기계·라벨·지표·배지 |
| §8 | 포털·MCP 통합 — 포털 창·앱 hwax_risk(REST·SPA·MCP·러너)·MCP 파리티·무손상 변경 목록·반영 절차 |
| §9 | 단계 계획 — P0~P7 목표·산출물·의존·수치 통과 기준·리스크 |
| §10 | 열린 질문·결정 필요 — 승인·보안·소스 계약·저장소·전문가 범위·어휘·예산·워크플로·앱 등록·배치 |

---


# §0 공통 정본(spine)

이 절은 계획서 전체가 공유하는 이름의 정본이다. 각 절(§1~§10)은 여기 있는 이름만 쓰고, 정의(필드·임계·상태 전이)는 담당 절이 적는다. 여기 없는 이름을 절이 새로 쓰려면 이 절에 먼저 추가한다. 1차 합성 후반부(doc_20, §6.4~§10)의 어휘를 그대로 채택했고, 1차 완결성 비평(gap_21)이 코드 대조로 확인한 모순 10건의 수정 결과를 이름 수준에서 반영했다(§0.7 에 목록).

## 0.1 용어·약어 사전

한 줄씩이다. 괄호 안은 그 용어를 정의하는 절이다.

### 0.1.1 대상·정체성

| 용어 | 정의 |
|---|---|
| 과제(project) | 심사 단위인 설계 프로젝트. 앱 DB `rr_projects` 행이 권위 id 이고 RA `project` 축에 code=앱 DB id 로 복제된다. (§2) |
| 소스(source) | 과제에 연결된 원천 앱 참조. kind ∈ `mcad`(StepForge) · `dyna`(DynaForge K파일) · `dyna_result`(DynaForge 리포트) · `ecad`(ODB hub 어댑터, 스텁). (§2) |
| 스냅샷(snapshot) | 소스들을 한 시점에 읽기 전용으로 동결한 불변 IR. `rr_snapshots` 행, id 는 `snapshot_id`. 같은 `(project_id, ir_hash)` 는 UNIQUE 로 재추출 시 기존 행을 반환한다. (§2) |
| rr_ir | 설계 IR JSON 정본(ir_version '1.0', ECAD 편입 시 '1.1'). `rr_snapshots.ir_json` 에만 원본이 있고 노드·엣지·same_as·dims_named·results·rollups·gates·missing·warnings·character_seed·feature_vector 를 담는다. (§2) |
| ir_hash | nodes·edges·same_as(confirmed/manual 만)·dims_named 를 키 정렬 canonical JSON 으로 직렬화한 sha256. provenance·시각·snapshot_id 는 제외해 같은 소스·같은 tol 이면 재추출해도 같다. (§2) |
| rr_state | 단일 스냅샷의 결정론 상태 평가 JSON(결론 없음). gates·signals·missing·character_seed·rule_hits·feature_vector 를 담고 `rr_states.state_json` 에 저장한다. (§3) |
| rr_diff | base/target 두 스냅샷의 3층(구조·파라메트릭·의미) diff JSON(diff_version '1.0', 결론 없음). `rr_diffs.diff_json` 에 저장하고 `summary_text` 를 동반한다. (§3) |
| summary_text | rr_diff(또는 rr_state)에서 코드가 결정론으로 만든 ≤2000자 요약. 줄마다 `[c:]` 등 참조를 달고 판단어 린터를 통과해야 생성된다. (§3) |
| 판단어 린터(judgement linter) | render.py 의 금지 어휘 필터. `위험·개선·악화·안전·문제·양호·리스크` 등 평가어가 코드 생성 문장에 있으면 생성 실패로 처리한다. 원천 인용(note 원문 등)은 제외한다. (§3) |
| 게이트(gate) G1~G7 | diff·심의 진입 전 rr_state 가 계산하는 7개 검문. G1 dup_or_anon_names · G2 sameas_pending · G3 iface_unconfirmed · G4 coordinate · G5 partial_scope · G6 unit_scale · G7 yardstick_parity(pair 전용, tol_parity+result_parity). G6 fail 은 `blocked=true`, G2 fail 은 pair 의미층 차단, 나머지는 진입 허용·표기 강제다. (§3) |
| target / target_key | 심사 대상. `snap:<snapshot_id>`(단일 현황) 또는 `diff:<diff_id>`(기준 대비 변경). `rr_targets` 행이며 로스터·커버리지·등록부·verdict 의 소유 단위다. (§6) |
| stale / superseded_by | 상태가 아니라 타깃 속성이다. 스냅샷은 불변이므로 IR 이 바뀌면 새 타깃이 생기고 옛 타깃은 `superseded_by` 로 닫힌다. (§6) |
| external_sync | `rr_targets.external_sync_json{ra: pending\|done\|unavailable, adh: pending\|done\|unavailable}`. 외부 반영 상태를 완결 레벨과 분리해 표기한다(C1 조건에서 RA 절을 뺀 대체물). (§5, §6) |

### 0.1.2 IR 내부 식별자

| 용어 | 정의 |
|---|---|
| nid | IR 노드 id. `'p:' + sha1(canon_key)[:12]`. canon_key 는 mcad `'mcad:'+path(프로젝트명 접두 제거)` / dyna `'dyna:'+sha256[:8]+':'+pid` / ecad `'ecad:'+refdes`. 재파싱으로 StepForge n{seq} 가 바뀌어도 불변이다. (§2) |
| eid | IR 엣지 id. `'e:' + sha1(kind_family + sorted(nid_a, nid_b))[:12]`. 방향 kind(part_of·load_path·net)는 정렬하지 않는다. (§2) |
| cid | rr_diff 변경 항목 id. `'c:' + sha1(...)[:12]`. node_changes·edge_changes·dims_delta·result_delta·rollup_delta·의미 이벤트 모두 cid 를 갖는다. (§3) |
| ckey / canonical_part_key | 과제 무관 전역 정규 부품 키. `'ck:' + sha1(name_norm_canon + '\|' + geom_bucket + '\|' + material_norm)[:12]`. name_norm_canon 은 `rr_dim_vocab` 과 같은 정규식·사전 규칙, geom_bucket 은 size_sorted 를 0.5 mm 버킷·volume 을 5% 버킷으로 반올림한 값이다. `rr_part_keys` 원장에서 사람이 merge/rename 하면 병합 결과가 우선한다. 결정론 pair 대응(ledger·exact_path·pid_map, 또는 fingerprint·name_norm score ≥0.95)으로 이어진 base↔target 노드의 계산 ckey 가 다르면 ir_builder 가 target 계산값을 `status='merged', decided_by='code:pair_correspondence'` 로 base 유효 ckey 에 자동 승계한다(§2.7.3 — 두께·부피 변경으로 geom_bucket 이 바뀌어도 같은 물리 부품은 리비전 간 키를 유지한다). 과제 간·connectivity 간 finding 회수의 키다. (§2, §5) |
| dn | 설계 노드 대표 nid. same_as(confirmed 또는 auto score ≥ 0.9)로 묶인 그룹의 대표이고 미결이면 자기 nid 다. diff 의 노드 대응은 dn 으로 한다. (§2) |
| subject_key | finding 이 가리키는 주체 키. 파트면 `ckey`, 계면이면 정렬한 무순서 쌍 `ckA\|ckB`, 명명 치수면 `dim:<name>`, 서브어셈블리면 `asm:<asm_key>`(§2.7.4 정규화, `rollups.by_assembly.path_prefix` 와 일치할 때만 부여). cluster_key 와 rr_iface_alias 의 입력이다. (§4) |
| asm_key | 서브어셈블리 롤업 키. path 접두(프로젝트명 제거)를 정규화한 문자열이고 rr_iface_alias 의 별칭 원천이다. (§2) |
| name_norm | 표시명 정규화. 소문자 → `#\d+$` 제거 → auto_named 이면 `_\d+$` 제거 → Dyna `Group\Name` 은 구분자 뒤만 → `[^a-z0-9]+`→`_` → 양끝 `_` 제거. (§2) |
| geom_fp | 정의 좌표계 기하 지문 `sha1(kind, sorted(round(size,2)), round_sig(volume,3), round_sig(area,3), round(centroid_def−bbox_center,2))`. 배치 불변이다. (§2) |
| same_as | 같은 물리 부품을 가리키는 두 노드의 대응 레코드 `{a, b, method, score, status, evidence, decided_by, decided_at}`. 스냅샷 내부(mcad↔dyna↔ecad)와 스냅샷 간(base↔target) 에 같은 사다리를 쓴다. (§2) |
| same-as 사다리 | 순서 고정 매칭 단계 `ledger → pid_map(part_mesh) → exact_path → fingerprint → title_norm/name_norm → fuzzy(헝가리안) → manual`. score < 0.9 인 auto 는 `pending` 으로 G2 에 계수된다. (§2) |
| dims_named | 과제에서 이름 붙인 치수 `{name, value, unit, method, ref, formula, owner_sub}`. 정의는 `rr_dim_defs`(과제별 extractor), 이름 사전은 `rr_dim_vocab`(과제 무관). 새 스냅샷마다 자동 재평가되고 ref 가 사라지면 null(미측정)이다. (§2) |
| rollups | 리프 엣지를 asm_key 접두로 집계한 `by_assembly[]{path_prefix, n_leaf, edges_internal, edges_external, orphan_leaf}`. (§2) |
| results | dyna_result 가 있을 때만 존재하는 결과 오버레이 `{report_ids, kind, sim_params_hash, part_risk[], findings[], energy_edges}`. kind 불일치면 만들지 않고 `missing.result_kind_mismatch=true`. (§2) |
| missing | 결측 플래그 `{ecad_absent, dyna_absent, dyna_result_absent, result_kind_mismatch, world_transform_absent, volume_null, material_density_unsourced}`. 결측이어도 심사는 돌되 결정문·서술에 남는다. (§2) |
| character_seed | rr_state 가 결정론 규칙표(`character-seed-rules.v1.json`)로 만든 성격 씨앗 태그 목록 `char:<axis>:<value>`. 결론이 아니라 서술의 씨앗이다. (§3, §4) |
| feature_vector | 스냅샷의 22차원 표준화 특징 벡터(고정 순서, 결측은 known 플래그로 마스킹). 유사 과제 kNN 재료이고 `rr_states.feature_json` 에 있다. (§3, §7) |
| rule_hits | `rr_rules(status=active)` 를 IR 에 즉시 실행한 결과 `[{rule, severity, pass, found, why_it_matters, fix_hint, payload_hash}]`. 심사 없이도 새 그래프에 알려진 리스크가 붙는 경로다. (§3, §7) |
| 원장(ledger) | 재검출·재추출에 유실되지 않도록 스냅샷 밖에 보관하는 사람 확정. `rr_iface_ledger`(계면 kind/status), `rr_sameas`(same-as confirmed/rejected), `rr_part_keys`(ckey 병합). 새 스냅샷 생성 시 재적용되어 `status=manual_ledger` 로 IR 에 반영된다. (§2) |
| rr_snapshot_calls | 스냅샷 생성 중 모든 소스 호출의 원문 로그(gzip). `tool:<call_id>` 참조의 대상이다. (§2, §5) |

### 0.1.3 서술·판정 레코드

| 용어 | 정의 |
|---|---|
| risk_spec | 패널 결정문 산문 뒤 ```json 펜스에 의장이 내는 기계판독 규격(schema 'risk_spec', version '1.0'). `scope·findings·gains·cross_domain·character·open_items·coverage·verdict·verdict_conditions·evidence_profile` 를 담는다. parse_risk_spec 이 파싱한다. (§4) |
| parse_risk_spec | parseSimSpec 복제 파서(펜스 우선 → 마지막 균형 중괄호 → 실패 null 비치명). 앱 단일 구현(`backend/app/narrative.py`)이고 P0 산출물이다. MCP 경로 결과도 앱 REST `/panels/{id}/complete`(또는 앱 MCP `risk_submit_panel_result`) 로 보내 같은 파서를 탄다. (§4) |
| finding | risk_spec.findings[] 의 원자 1건. 필드 `id, direction, domain, mechanism, mechanism_detail, change_kind, subject{ckeys, names}, trigger_condition, severity, judgement, detectability{level, tool}, evidence_grade, precedent, cites[{ref, quote}], tool_calls, claim, warrant, resolving_check, owner_domain, raised_by, contested_by, contest_note, status`. `rr_findings` 행. (§4) |
| gain | direction=improvement 인 finding. risk_spec.gains[] 에 같은 필드로 담고 rr_findings 에 direction 으로 구분한다. (§4) |
| cross_domain | risk_spec.cross_domain[] `{id, from_domain, to_domain, path, cites, raised_by}`. 한 도메인 변경이 다른 도메인에 미치는 2차 리스크 경로다. (§4) |
| open_item | risk_spec.open_items[] `{id, question, resolving_check{kind, ref}, owner_domain}`. 판정 불가를 닫는 확인 목록이다. (§4) |
| resolving_check | finding·open_item 이 닫히는 방법 `{kind: tool\|sim\|test\|field, ref}`. 등록부 병합 시 문자열 집합으로 보존되어 다음 단계 체크리스트가 된다. (§4) |
| cites / cite | 서술 원자의 근거 링크 `{ref, quote}`. ref 는 §0.2 문법을 따르고 quote 는 원천 정규 표기 문자열을 축어로 담는다. (§4) |
| dangling | cites.ref 가 스코프의 IR·diff·호출 로그·허용 선행 서술·카드에 실재하지 않을 때 붙는 플래그. 버리지 않고 evidence_grade 를 경험칙으로 강등한다. (§4) |
| feature_snapshot | finding.cites 가 가리키는 IR 속성값의 사본(`rr_findings.finding_json.feature_snapshot`). IR 이 바뀌어도 당시 수치를 보존하고 규칙 조건 범위의 재료가 된다. (§4, §7) |
| seat_opinion | 좌석 1석 × 타깃 1개의 의견 레코드(코드 추출, LLM 재요약 없음). `{opinion_id, target_key, panel_id, agent_key, domain, origin, turns[{round, say_excerpt, position, stance, non_negotiable}], final_stance, tool_calls[], tool_calls_n, tool_calls_ok, knowledge_hits_n, cited_refs[], quality{used_tool, cited_ir, grade_min}, raised_finding_ids[], excerpt_for_rag}`. `rr_seat_opinions` 행. (§4) |
| stance | 좌석 최종 입장 `agree \| conditional \| oppose \| abstain`. abstain 또는 '판정 불가' 는 커버리지 `abstain` 종결이다. (§4, §6) |
| used_tool | 좌석 귀속 도구 호출 성공 여부. SSE evidence.source `'<key> · <tool>'` 로 성공 호출을, status.step `'<key> 조회: <tool>'` 로 시도 호출을 세어 `tool_calls_ok`·`tool_calls_n` 을 따로 둔다. 지정 도구(delib_opts.tools) 결과는 좌석 귀속 불가라 넣지 않는다. (§6) |
| cited_refs | 좌석 발언에서 정규식으로 뽑은 참조 목록(`[c:]`·`[e:]`·`[p:]`·`[d:]`·`name:A\|B`). carried 판정과 IR 인용률의 원자료다. (§4, §6) |
| character_narrative | 패널 단위 성격 서술 = risk_spec.character `{one_liner, facets[{facet, statements[{id, text, polarity, by, cites, tags, confidence}], na_reason}]}`. facet 8종 순서 `intent(설계 의도) · constraint(제약) · anomaly(이례성) · lineage(계보) · vulnerability(취약 계면) · strength(강점) · tradeoff(맞교환) · unknown(미지)`. (§4) |
| character_statement | character_narrative 의 문장 원자. `rr_character` 행 `{id, project_id, facet, tag, statement, polarity, cites_json, by, first_target_key, support_panels, support_targets, status, superseded_by}`. (§4) |
| character_profile | 과제 단위 성격 프로파일. `character.py` 가 character_seed(L0) → 패널 진술(L2) → 사람 확정 순으로 status `seed → panel → confirmed`(또는 `superseded`) 를 올리며 합성한다. AIDataHub `project_character` 1레코드/과제 UPSERT. (§4, §5) |
| 성격 통제 어휘(character vocab) | `character-vocab.v1.json`. 축 `char:structure · char:interface · char:tolerance · char:maturity · char:analysis · char:change_style · char:philosophy`. 어휘 밖 값은 `x:` 접두 자유 제안(≤3/서술)이고 타깃 3·패널 2 에서 같은 값이 나오면 승격 후보다. (§4, §7) |
| design_trait | RA reference 축. value = 성격 태그 문자열(예 `char:structure:adhesive_dependent`). `exhibits` 관계로 project·design_snapshot 에 연결되어 KG 에서 같은 성격의 과제를 찾는 열쇠다. (§5) |
| evidence_grade | 근거 등급 4단 `측정 · 문헌·규격 · 도구예측 · 경험칙`. cites 의 ref 종류에서 자동 산출한다(inc/rpt(test)→측정, card(standard/paper)→문헌·규격, tool→도구예측, 없음→경험칙). (§4) |
| precedent | 선례 범위 `in_range \| out_of_range \| none`. 인용 수치가 코퍼스 feature 범위 안인지(corpus_n ≥ 5 일 때만)를 코드가 저장 시 부여한다. (§4, §7) |
| severity / judgement | 심각도 `경미 \| 중대 \| 치명` 과 판정 `OK \| WARNING \| FAIL \| undetermined`. 매핑 경미→OK/WARNING, 중대→WARNING/FAIL, 치명→FAIL. 정규화 컬럼 `sev3 ∈ 1\|2\|3`. (§4, §7) |
| verdict | 판정 `go \| conditional \| no-go \| undetermined`. 등록부 집계는 '후보' 이고 사람이 `verdict_final` 을 UI 로 확정한다(자동 승인 없음). (§4, §6) |
| evidence_profile | 결정문 헤더의 근거 프로파일 `{tool, card, precedent{verified, dismissed}, heuristic, measured}`. seat_opinion 합계와 대조해 불일치는 `quality.flag=header_mismatch`. (§4) |

### 0.1.4 등록부·학습

| 용어 | 정의 |
|---|---|
| rr_registry / 등록부 | 타깃 단위로 finding 을 cluster_key 로 병합한 표. `{target_key, cluster_key, merged_json, support, contested, severity, judgement, evidence_grade, precedent, status, verified_by_json}`. (§4) |
| cluster_key | `sha1(mechanism, mechanism_detail, subject_key, change_kind)[:12]`. subject 는 rr_iface_alias 별칭 수준으로 정규화한 뒤 계산한다. (§4, §7) |
| contested | 지정 반대석이 기각을 요구한 횟수. 등록부 행에 표기되고 C2 조건·adversary_false_reject 지표에 쓰인다. (§4, §6) |
| 등록부 status | `open \| verified \| dismissed \| mitigated \| superseded`. verified/dismissed 는 라벨 또는 사람 UI 로만 바뀐다. (§4, §7) |
| prior_evidence | 다음 타깃의 delib_opts.evidence 를 조립하는 `narrative.prior_evidence(target)`. 슬롯 E0~E9 고정, 헌법 P1(결론 금지·원천만·'검증 대상' 프레이밍). (§5) |
| E0 | 스코프·게이트·소스 id 표(항상 첫 항목). 소스 앱 id 를 명시해 지정 도구 인자 구성이 skip 되지 않게 한다. (§5) |
| E0c | 좌석 계약표(seat_contract) — 도메인별 필수 호출·산출 형식. 엔진 상수 `_RISK_SEAT_CONTRACT` 와 이중화한 evidence 항목이다. (§5, §6) |
| E1 | diff summary_text(pair) 또는 rr_state 요약(snap). (§5) |
| E2 | 의미·구조 변화 표(cid 포함). (§5) |
| E3 | dims_named delta 표. (§5) |
| E4 | 결과 delta 표(result_parity 일 때만 수치). (§5) |
| E5 | 계보 이전 등록부 상위 클러스터(status open\|verified, cluster_key 병기). (§5) |
| E6 | 유사 과제 성격 진술(status confirmed 또는 panel(support_panels ≥ 2) 상위 3, 출처 태그). (§5) |
| E7 | 이번 패널 좌석 5명의 이전 발췌(좌석당 줄 ≤220자, 좌석 합 ≤1100자, 항목 라인 상한 1400자 — §5.6.1 엔진 라인 오버헤드 규칙, 고정 슬롯). (§5) |
| E8 | delta 선례 표(rr_delta_priors 수치만). (§5) |
| E9 | warnings·rule_hits 원문. (§5) |
| rr_delta_priors | `(change_kind, mechanism, mechanism_detail)` 별 `n_raised, n_targets, n_verified, n_dismissed`. 값은 타깃별 기여 표 `rr_delta_contrib(change_kind, mechanism, mechanism_detail, target_key)` 의 합으로 재합산되어 패널 재병합에 멱등이다(§4.7.1·§7.4). 선례 정밀도 = n_verified/(n_verified+n_dismissed). (§7) |
| rr_iface_alias | 무순서 `(canonical_a, canonical_b)` 를 키로 한 계면 별칭 사전. 다른 connectivity 에서 같은 계면을 인식한다. 사람 확정 별칭은 RA `add_object_alias`(part 축)에도 이중 보관한다. (§5, §7) |
| rr_claim_refs | ref → claim 역색인 `(claim_uid, ref_type, ref, quote)`. "이 엣지에 대해 누가 뭐라 했나" 조인이다. (§5, §7) |
| carried | 새 타깃(같은 과제·새 스냅샷)에서 이전 done 좌석을 재심 면제하는 커버리지 종결 상태. 조건은 cited_refs≠∅·used_tool·cited_refs 의 ckey ∩ 변경 ckey = ∅·≤ risk_carried_days. (§6) |
| 라벨(label) | 실측 검증 `rr_labels{finding_id, pattern_id, source: incident\|test_run\|voc\|sim\|expert_review\|manual, outcome: confirmed\|refuted\|inconclusive, matched_by: auto\|manual, match_score, evidence_ref}`. (§7) |
| 패턴(pattern) | 반복 finding 의 승격 단위 `rr_patterns.status: candidate → known → rule → predictor \| deprecated \| suspended`. 승격은 항상 사람 승인이다. (§7) |
| 규칙(rule) | `rr_rules{condition_json(DSL), severity, why_it_matters, fix_hint, backtest_json, status: draft\|active\|retired}`. 평가기는 부작용 없음·결정론이다. (§7) |
| 조건 DSL | `{all:[{ref, op, value}], any:[]}`, ref 는 IR/diff 경로, op ∈ `eq\|ne\|gte\|lte\|between\|in\|exists`. (§7) |
| 택소노미(taxonomy) | `taxonomy.v1.json` 8축 — domain(15) · mechanism{thermal, mechanical, interface, electrical, material, process}+detail · change_kind · trigger_condition · severity↔judgement · detectability · evidence_grade+precedent · direction. 부가 status. 목록 밖 detail 은 `unclassified` + `mechanism_free`. (§7) |
| 버전 스탬프 | `taxonomy_version · rule_version · planner_version · ir_version · diff_version · adapter_version` 을 finding·패널·보고서에 남긴다. (§7) |
| rr_metrics | 지표 저장 `(period, dimension: expert\|domain\|mechanism\|pattern\|project\|global, key, metric, value, n)`. 지표 이름 `precision · recall_proxy · lead_time_days · calibration · adversary_false_reject · evidence_grade_dist · out_of_range_ratio · unclassified_ratio · coverage_pct · precedent_hit_rate · known_share · rule_precision_trend`. (§7) |
| '루프 작동' 배지 | 최근 5타깃 이동평균이 precedent_hit_rate ≥ 0.5 · known_share ≥ 0.3 · unclassified_ratio ≤ 0.2 일 때 코드가 붙이는 표시. (§7) |
| 큐레이션 큐 | `rr_curation_queue{kind: unclassified_code\|pattern_candidate\|label_match\|x_tag_promote, payload_json, status}`. (§7) |

### 0.1.5 전문가 워크플로

| 용어 | 정의 |
|---|---|
| HWXD 도메인 15 | `xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material`. Settings `risk_roster_domains` 로 조정한다. (§6) |
| ECAD 의존 도메인 6 | `pcb · pwr · rf · soc · passive · mem`. Settings `risk_ecad_domains`. ecad_absent 면 대표 1석 외 `deferred`. (§6) |
| agent_key | 전문가 좌석 키(예 `mech-housing-structure`). 접두사가 도메인이다(`_dom_of`). (§6) |
| 로스터(rr_roster) | 타깃 생성 시 고정된 좌석 목록 `{target_key, agent_key, domain, relevance, rank_in_domain}`. 실측 ≈350석. (§6) |
| 커버리지(rr_coverage) | PK(target_key, agent_key) 회계 원장. status ∈ `pending · assigned · running · done · done_weak · abstain · failed · skipped · deferred · carried`. 종결 = `done \| done_weak \| abstain \| skipped \| deferred \| carried`. (§6) |
| coverage_key | `<target_key>:<agent_key>` 문자열. RA assessment.coverage_key 속성과 AIDataHub external_id 에 쓴다. (§5, §6) |
| 패널(rr_panels) | 심의 대화 1건. 6석(primary 4 + counter 1 + adversary 1)·3라운드. status ∈ `planned · running · done · error`. `seats_json · quality_json · llm_calls · risk_spec_json · risk_spec_parsed · engine · tool_mode`. (§6) |
| origin | 좌석 출신 `primary(로스터석) · counter(반대 도메인석) · adversary(지정 반대석, 합성 push, 원장 미집계)`. `extra_seats` 는 로스터 외 키가 착석했을 때의 기록이며 불변식은 `extra_seats == ∅` 이다. (§6) |
| delib-baseline-defender | 지정 반대석 키. `_CHAIR_ADVERSARY["risk-review"]`(PY) / `CHAIR_ADVERSARY['risk-review']`(JS) 로 합성 push 된다. (§6) |
| Tier A/B/C | 편성 단계. 패널 수 = ceil(추가 좌석 / 5)(§6.4.1 규칙, 이 행이 정본). A 대표(`rank_in_domain == 1`, 15석, 3패널) · B 심층(`rank ≤ ceil(0.3·\|d\|)`, 누적 114석, +20패널 — ECAD 부재 85석 +14) · C 전원(나머지, 실측 350 기준 236석 +48 — ECAD 부재 246 기준 161석 +33, 명시 승인제). 실측 ≈350 합 3/20/48=71, ECAD 부재 3/14/33=50. `planner.tier_plan(target)` 이 로스터 실측에서 같은 규칙으로 다시 계산한다. (§6) |
| 인접 표(adjacency) | counter 석을 뽑는 도메인 인접 사전 `adjacency.v1.json`(Settings `risk_adjacency` 로 덮어씀). (§6) |
| planner | `planner.py` 결정론 편성기(LLM 없음). 같은 입력이면 같은 seats_json. (§6) |
| runner | 앱 `backend/app/runner.py` 백그라운드 실행기(앱 프로세스 안에서 실행). 세마포어 `risk_concurrency`, 포털 `POST /agent/chat` 을 포털 PAT(`HWAXRISK_PORTAL_PAT`, aud `mcp-gateway`) Bearer 로 호출(SSE, 포털 감사·세마포어·conv_store 저장 동반), SSE 캡처, 파싱·병합·외부 반영·완결 판정. agent-server `:9009` 직접 호출은 같은 박스 전용 폴백이다. (§6, §8) |
| rr_jobs | 배치 잡. state ∈ `queued · running · paused(reason: diminishing\|daily_cap\|user) · cancelling · cancelled · completed · failed`. 취소는 패널 경계에서만 반영. (§6) |
| 완결 레벨 | `C0 · C1(대표 완료) · C2(심층 완료) · C3(전원 완료)`, 기본 마감은 Settings `risk_default_close_level`(C2\|C3, 기본 C2 → `level='C2(closed)'`). C3 가 요구('전원 한 번씩')의 문자적 충족이고 C2 는 비용 타협임을 §6 표 위에 명시한다. (§6) |
| 좌석 계약(seat contract) | 도메인별 1R 필수 호출·권장 도구·산출 형식 표. 주경로는 엔진 상수 `_RISK_SEAT_CONTRACT`(chair_template=='risk-review' 일 때 deliberation.py :2044 `p["role"] = await _restore_role(...)` 직후에 `p["role"]` 접미로 붙여 `_persona_round`(:889) 의 sysmsg 에 들어간다 — 라운드 사용자 프롬프트 prompt_fn 이 아니다), 보조는 E0c. 호출자가 personas[].role 에 접미를 넣는 방식은 `_restore_role` 이 덮어쓰므로 쓰지 않는다. (§6) |
| tool_mode | 패널 도구 등급 `tools \| evidence_only`. MCP 경로(hwax-deliberate.js)는 좌석 도구 호출 경로가 없어 `engine='mcp', tool_mode='evidence_only'` 로 기록하고 C2 strong 비율 계산에서 제외한다. (§6, §8) |
| quality.flag | 패널 품질 경고 값 `over_budget · rescreen_seats · coverage_mismatch · header_mismatch · low_tool_use · low_ir_cite · adversary_silent · adversary_overreject · spec_parse_failed · model_changed_midrun`(마지막은 D6 — 패널 시작·종료의 agent-server `/health` `model`·`vllm` 불일치, §6.7.2). 실패가 아니라 표기다. (§6) |
| 수확 체감 정지 | 최근 3패널이 각각 신규 클러스터 < 1 이고 C1 충족이면 `paused(reason=diminishing)`. (§6) |
| 통합 보고서 | 레벨 상승 시 코드가 RA `deliberation` 템플릿으로 조립하는 타깃 보고서(v1/v2/v3). (§6, §8) |

### 0.1.6 통합·운영

| 용어 | 정의 |
|---|---|
| Job 'risk-review' | delibTaxonomy JOBS 8행째. 트리거 `/심의 `, chair_template `risk-review`, ConvKind `risk-review`. (§8) |
| delib_opts | 엔진 호출 옵션. 이 기능이 쓰는 키 `chair_template · modifiers · rounds · free_tools · tool_budget · personas[{key, role, origin}] · tools(≤6) · apps(≤3) · evidence(≤12)`. `human_note`·`continue_summary` 는 러너가 절대 싣지 않는다(user_memo 는 evidence 항목). (§6, §8) |
| _RISK_READ_TOOLS | deliberation.py 앱 조건부 읽기 도구 화이트리스트(앱키가 apps 에 있을 때만 통과). 검사 지점은 자유조회 목록 조립식 `_g`(:1897-1898, `_free_tool_ok` 접두사 검문과 or)이다 — 목록의 전 항목이 `_FREE_ALLOW` 접두사에 걸리지 않아 `_narrow`(:1916-1918) 이전에 이미 빠지기 때문이다. 쓰기 도구 미포함. (§6, §8) |
| _RISK_KEEP_TOOLS | chair_template=='risk-review' 일 때 앱 제한과 무관하게 남기는 명시 목록 `('search_objects','get_object','get_subgraph','search_reports','predict_sed','check_design_rules','pcb_warpage_surrogate','get_reference_cases')`. 검사 지점 2곳 — `_g` 조립식(:1897-1898, 접두사 검문과 or — `pcb_warpage_surrogate` 가 접두사에 걸리지 않아 필요)과 `_narrow`(:1916-1918, `_MATERIAL_TOOLS` 와 같은 방식의 or 1줄 — keep 도구는 apps 밖 앱 소속이라 필요). (§6, §8) |
| 통과 경로(pass path) | 계약표 도구가 자유조회 목록에 남는 이유 열 `app \| keep \| material \| free_allow`. (§6) |
| hwax_risk(HEAX 앱) | 이 기능의 자산을 소유하는 HEAX 앱(B 결정, §0.7 #12). 이름 대응표 — 매니페스트 `id: hwax_risk` · 표시명 `HWAX Risk Review` · 리포 `HWAXRisk`(`/home/koopark/claude/HWAXRisk`, GitHub `squall321/HWAXRisk`) · HEAXHub 등록 디렉터리 `integrations/hwax-risk/` · SIF `var/sifs/hwax-risk.sif` · Caddy 경로 `/apps/hwax_risk/*`(포털 오리진 `/apps/hwax_risk/` 및 `/heax-hub/apps/hwax_risk/`, forward_auth 뒤) · REST base `/apps/hwax_risk/api/…`(앱 내부 `/api/…`) · MCP `/apps/hwax_risk/mcp`(앱 내부 `/mcp`) → 게이트웨이 백엔드 키 `heax-hwax_risk`(heax_registry 자동 흡수) · 데이터 디렉터리 `$HEAX_DATA_DIR`(SIF `/data`, 호스트 `HEAXHub/var/app_data/hwax_risk/`) · DB 파일 `$HEAX_DATA_DIR/risk_review.db` · 시크릿 `$HEAX_DATA_DIR/secrets.env`(0600). 매니페스트 확정값 `schema_version 2 · app_type web_app · execution_target linux_runner · build{python_venv, stack fastapi_react, python 3.12} · launch{service, health /api/health, env{HWAXRISK_DATA_DIR:/data, PYTHONNOUSERSITE:"1"}} · permissions.visibility company · status beta · mcp{expose, path /mcp, streamable_http, allowed_groups []}`. (§8) |
| hwax-risk(MCP) | 앱이 노출하는 MCP 서버 이름(`backend/app/mcp_server.py`). 도구 `risk_get_snapshot · risk_get_diff · risk_get_registry · risk_claims_for_ref · risk_get_brief · risk_submit_panel_result`(§0.5.2). 게이트웨이 경유 호출은 heax 서비스 PAT(admin) 신원으로 도달하므로 쓰기 도구는 `actor`(이메일, 게이트웨이 신고값·미검증) 인자를 받는다. 에이전트 직접 등록 `claude mcp add --transport http hwax-risk <포털베이스>/apps/hwax_risk/mcp`(헤더 `Authorization: Bearer heax_pat_…`). (§8) |
| 포털 창(portal window) | 포털이 이 기능에 두는 것의 전부 — `systems.yaml` 타일 `hwax-risk`(jwt-handoff, audience `heax-hub`) · 라우트 `/risk` · NavLink '리스크 심사' · `RiskLaunchPage.tsx`(launch → 앱 링크 2단). 포털 SPA 는 heax bearer 가 없어 앱 REST 를 직접 fetch 하지 않는다. (§8) |
| L1 / L2 파리티 | L1 = `hwax-deliberate chairTemplate:'risk-review'` 단발(원장 미연동). L2 = `hwax-risk-review.js` 오케스트레이터가 게이트웨이 `heax-hwax_risk` 도구 `risk_get_brief` 로 브리프를 받아 패널을 돌리고 `risk_submit_panel_result` 로 되돌림(앱 REST `/panels/{id}/complete` 와 같은 파서). (§8) |
| check_chair_parity.py | PY/JS 의 `CHAIR_ITEMS · CHAIR_ADVERSARY · RISK_SEAT_CONTRACT · 제목 삼항` 문자열 바이트 동일 검증 스크립트. (§8, §9) |
| 러너 자격(runner credential) | B 에서 '사용자 PAT 대리 발급' 은 없다 — 포털에 타인 명의 PAT 발급 API 가 없고 `_chat_user_pat`(routes.py:158)는 릴레이 내부 전용이라 앱이 호출할 수 없다. 러너는 (a) 서비스 계정 포털 PAT `HWAXRISK_PORTAL_PAT`(aud `mcp-gateway`, scope api, ttl_days 0 가능) 를 기본 자격으로 쓰고, (b) 타깃 owner 가 앱 설정(`PUT /api/me/portal-pat`)에 등록한 자기 포털 PAT 가 있으면 그 패널은 그 PAT 로 호출한다(DynaForge per_user_sso 가 PAT email 로 발동). (b) 가 없으면 dyna 읽기는 서비스 시야(세션 0건) 라 `dyna_absent` 강등이고 도구 귀속은 그대로 SSE 로 잡힌다. 어느 경우든 좌석 도구 스코핑(X-HWAX-Groups)은 호출 PAT 의 groups 로 굳는다. (§8, §9, §10) |
| ODB 어댑터 계약 | ODB hub 가 이행할 4도구 `odb_get_board · odb_list_components · odb_list_nets · odb_get_stackup`(상한 컴포넌트 2000·넷 5000). 어댑터 계약만 두고 코드는 스텁이다. (§2, §9) |

## 0.2 식별자·참조 규약

### 0.2.1 참조 문법(cites.ref · cited_refs · summary_text 각주 공통)

문자열 하나가 원천 한 곳을 가리킨다. 대괄호는 산문 안 표기이고 JSON 필드 안에서는 대괄호 없이 쓴다. 파서는 대괄호 유무를 모두 받는다.

| 표기 | 가리키는 것 | 해석 대상 | 존재 검증 |
|---|---|---|---|
| `[p:<12hex>]` | IR 노드(nid) | `rr_ir.nodes[nid]` | 스코프 스냅샷(pair 면 base·target 둘 다) |
| `[e:<12hex>]` | IR 엣지(eid) | `rr_ir.edges[eid]` | 동일 |
| `[c:<12hex>]` | diff 변경 항목(cid) | `rr_diff.*[cid]` | 스코프 diff |
| `[d:<name>]` | 명명 치수 | `rr_ir.dims_named[name]` 또는 `rr_diff.dims_delta[name]` | 스코프 |
| `name:<A>\|<B>` | 이름으로 부른 계면(정렬 무관) | name_norm 으로 nid 쌍 → eid 해석, 다의면 dangling | 스코프 |
| `tool:<call_id>` | 스냅샷 생성 호출 원문 | `rr_snapshot_calls.call_id` | 스코프 |
| `tool:conv:<conv_id>#<idx>` | 심의 중 좌석 자유조회 호출 | conv_store activity[idx] | 해당 대화 |
| `card:<record_id>` | AIDataHub 지식카드 | `get_record` | 존재만 |
| `narr:<opinion_id>#<finding_id>` | 이전 좌석 의견의 finding | `rr_seat_opinions` → rr_findings | 계보·유사 과제·E7 에 실린 것만 허용 |
| `narr:<character_id>` | 이전 성격 진술 | `rr_character.id` | E6 에 실린 것만 허용 |
| `reg:<target_key>#<cluster_key>` | 이전 등록부 클러스터 | `rr_registry` | E5 에 실린 것만 허용 |
| `warn:<code>#<ref>` | IR warnings 항목 | `rr_ir.warnings` | 스코프 |
| `gate:G<n>` | 게이트 | `rr_state.gates` | 스코프 |
| `sig:<key>` | rr_state signals 항목 | `rr_state.signals` | 스코프 |
| `rule:<rule_id>` | rule_hits 의 규칙 | `rr_rules` | active |
| `rpt:<report_id>` | RA 보고서(DynaForge report_id 는 `dyna:rpt:<id>`) | RA/DynaForge | 존재만 |
| `inc:<ra_object_id>` | RA incident·test_run 객체 | `get_object` | 존재만 |
| `[문헌·규격]`, `[경험칙]` 등 | 근거 등급 표기(참조 아님) | — | — |

규칙. (1) 산문의 수치는 `quote` 안의 정규 표기 문자열에 문자 그대로 있어야 한다(render.py 가 IR·diff 항목마다 정규 표기를 만들고 브리프·자유조회 결과가 같은 문자열을 쓴다). (2) 실재하지 않는 참조는 `dangling=true` 로 보존하고 등급을 경험칙으로 강등한다. (3) `narr:`·`reg:` 는 브리프에 실린 것만 인용할 수 있다(지어낸 선례 차단). (4) 정규 표기 예 `min_gap=0.012 mm`, `penetration_depth≥0.05 mm(lower_bound)`, `bbox_dz 1.20→1.00 mm (−16.7%)`, `contact_area_est=812.4 mm²(밴드면적)`.

### 0.2.2 키·id 형식

| 이름 | 형식 |
|---|---|
| snapshot_id · diff_id · panel_id · job_id · opinion_id · finding_id(행) · character_id · narrative 계열 id | 앱 DB uuid hex32(포털 conv_store `_uid` 패턴 복제) |
| target_key | `snap:<snapshot_id>` \| `diff:<diff_id>` |
| coverage_key | `<target_key>:<agent_key>` |
| cluster_key | `sha1(mechanism\|mechanism_detail\|subject_key\|change_kind)[:12]` |
| subject_key | `ck:…` \| `ck:…\|ck:…`(정렬) \| `dim:<name>` \| `asm:<asm_key>`(§2.7.4 — 프로젝트명 제거·name_norm_canon 적용) |
| pair_key(rr_iface_ledger) | `<path_a>\|<path_b>`(정렬, 프로젝트명 제거) |
| alias_key(rr_iface_alias) | `<ckey_a>\|<ckey_b>`(정렬) |
| risk_spec 내부 id | findings `F<n>`, gains `G<n>`, cross_domain `X<n>`, character statements `C<n>`, open_items `O<n>` — 패널 안에서만 유일하고 저장 시 `<panel_id>#F1` 로 전역화 |
| RA 인스턴스 | `code=<앱 DB id>(≤64)`, `value='<과제코드>@<source>@<YYYYMMDD-hhmm>'` |
| AIDataHub `_external_id` | `opinion:<target_key>:<agent_key>:<cycle>` · `panel:<panel_id>` · `character:<project_id>`(project_character 는 과제당 1레코드 UPSERT) · `pattern:<pattern_id>` · `digest:<snapshot_id>` |
| 태그(공통) | `hwax-risk-review · hwax:project:<id> · hwax:target:<key> · hwax:snapshot:<id> · hwax:panel:<no> · hwax:expert:<agent_key> · hwax:domain:<d> · sev:<max> · mechanism:<m> · verdict:<v> · char:<axis>:<value> · x:<free>` |
| RA 보고서 tags | `['심의','chat-deliberation','risk-review','hwax:target:<key>','hwax:panel:<no>']`(패널) · `['리스크심사','consolidated','hwax:target:<key>','hwax:project:<id>','verdict:<v>']`(통합) |
| 대화(conv_store) | `kind='risk-review'`, title 접두 `[리스크심사] {과제} P{n}` |
| 질문 문자열 접두 | `[리스크심사 {과제코드} {target_key}] …` |

### 0.2.3 SSE 캡처 규약(스키마 변경 없음)

| 이벤트 | 러너가 읽는 것 |
|---|---|
| `personas` | 착석 키·origin. 로스터 외 키 → `extra_seats`(불변식 위반 시 `quality.flag=rescreen_seats`). `role` 은 엔진이 280자로 자른다(:2090) — 좌석 계약 접미 검증에는 쓰지 않는다(P0 (7)) |
| `turn` | 좌석 발언(round, say, position, stance, non_negotiable) → seat_opinion.turns |
| `status{step, tool}` | `step` 이 `'<key> 조회: <tool>'` 이면 좌석 시도 호출(tool_calls_n) |
| `evidence{source}` | `source` 가 `'<key> · <tool>'` 이면 좌석 성공 호출(tool_calls_ok, used_tool) |
| `decision` | 산문 + risk_spec 펜스 |
| `outcome{report_id, tally}` | RA report_id |
| `warning(_pat_degraded)` · `error` | 패널 error → 5석 pending(retry+1) |

## 0.3 저장 3층 총목록(이름만)

### 0.3.1 앱 DB `$HEAX_DATA_DIR/risk_review.db`(hwax_risk 앱 `backend/app/risk_store.py`, ID 권위)

물리 위치는 앱 데이터 디렉터리의 단일 SQLite 파일 하나다(SIF `/data/risk_review.db`, 호스트 실행 `HEAXHub/var/app_data/hwax_risk/risk_review.db`, 리포 로컬 폴백 `<HWAXRisk>/data/risk_review.db`). 확장자 `.db` 는 `appdata-to-drive.sh` 가 `sqlite .backup` 원자 스냅샷을 뜨는 조건이다(WAL 켜도 안전). dev→cae00 은 첫 배포 시드 복사만 자동이고 이후 병합은 없으므로, 재분석 멱등 규칙(같으면 지지+1 병합·다르면 add)을 쓰는 앱 자체 `export/import`(JSONL, §0.5.1) 가 P1 이후 이동 경로다. 표 목록·rr_* 스키마·원자·해시 규약은 A 계획과 동일하다.

| 표 | 역할(정의 절) |
|---|---|
| rr_projects | 과제(§2, §5) |
| rr_sources | 과제 소스 참조·probe 결과(§2) |
| rr_snapshots | 스냅샷·rr_ir 원본·ir_hash(§2) |
| rr_snapshot_calls | 소스 호출 원문 gzip 로그(§2) |
| rr_ir_nodes · rr_ir_edges | IR 조회용 펼침 표(nid·eid·ckey·name_norm·geom_fp 인덱스)(§2, §5) |
| rr_part_keys | ckey 원장(candidate\|confirmed\|merged, merged_into, aliases)(§2, §5) |
| rr_sameas | same-as 원장(스냅샷 내부·pair, confirmed\|rejected 재적용)(§2) |
| rr_iface_ledger | 계면 kind/status 확정 원장(§2) |
| rr_dim_vocab | 명명 치수 이름 사전(과제 무관)(§2) |
| rr_dim_defs | 과제별 치수 extractor(§2) |
| rr_states | rr_state·feature_json·rule_hits·character_seed(§3) |
| rr_diffs | rr_diff 원본·summary_text·comparability(§3) |
| rr_diff_events | 의미 이벤트 펼침 표(cid·code·change_kind 인덱스)(§3) |
| rr_targets | 타깃·level·verdict_final·external_sync_json·superseded_by(§6) |
| rr_roster | 고정 로스터(§6) |
| rr_coverage | 커버리지 회계 PK(target_key, agent_key) + 부분 유니크 인덱스 `rr_cov_active`(§6) |
| rr_panels | 패널(§6) |
| rr_jobs | 배치 잡(§6) |
| rr_seat_opinions | seat_opinion(§4) |
| rr_findings | finding·gain 원자(§4) |
| rr_registry | 타깃 등록부(§4) |
| rr_claim_refs | ref 역색인(§5) |
| rr_character | character_statement·프로파일 status(§4) |
| rr_iface_alias | 계면 별칭 사전(§5, §7) |
| rr_delta_priors | 변경-델타 선례 통계 — `rr_delta_contrib` 의 합(§4, §7) |
| rr_delta_contrib | 타깃별 delta 기여 행 `(change_kind, mechanism, mechanism_detail, target_key)`, 등록부 병합마다 UPSERT(멱등)(§4, §7) |
| rr_labels | 검증 라벨(§7) |
| rr_patterns | 패턴 승격 상태(§7) |
| rr_rules | 규칙 DSL·백테스트(§7) |
| rr_metrics | 지표(§7) |
| rr_curation_queue | 큐레이션 큐(§7) |
| rr_id_map | 앱 DB id ↔ RA entity id ↔ AIDataHub record id 보조 매핑(§5) |

공통 규약. 모든 표에 `owner_sub` 를 두고 조회는 owner_sub 로 좁힌다. owner_sub 값의 원천은 앱 `identity.py` 가 heax `GET /api/v1/auth/me` 로 해석한 사용자(UI·REST 경로) 또는 MCP 쓰기 도구의 `actor` 인자(게이트웨이 경로, 미검증 표기)이며 값 형식은 §8 이 정한다. 조직 공유 자산(rr_findings·rr_registry·rr_patterns·rr_metrics·rr_iface_alias·rr_delta_priors)은 `visibility ∈ private\|org` 컬럼을 두되 기본값은 private 이고 P6 에서 결정한다(§10).

### 0.3.2 ReportArchive KG(관리 REST 로 부트스트랩 1회, 인스턴스는 MCP 4종 `create_object · update_object · add_object_alias · link_objects`, RA 코드 무수정)

신규 축 6(POST /api/entity-types).

| 축 | kind_class | 역할(정의 절) |
|---|---|---|
| expert | reference | value=agent_key(§5) |
| design_snapshot | record | 스냅샷 요약·ir_hash·portal_snapshot_id(§5) |
| design_diff | record | diff 카운트·comparability(§5) |
| assessment | record | 패널×좌석 판정·coverage_key·verdict(§5) |
| risk_finding | record | 등록부 클러스터 또는 finding 원자(§5) |
| design_trait | reference | value=성격 태그(§5) |

기존 축 재사용. `project · part · model · failure_mode · defect · incident · test_run`(수정 금지, part 축 별칭은 `add_object_alias` 로만).

신규 관계 12(POST /api/relation-types, 전부 directed).

| slug | src → dst | 비고 |
|---|---|---|
| snapshot_of | design_snapshot → project | |
| derived_from | design_snapshot → design_snapshot | acyclic |
| diff_of | design_diff → design_snapshot | 관계 속성 role ∈ base\|target |
| assesses | assessment → project \| design_snapshot \| design_diff | evidence_report_id=패널 RA 보고서 |
| assessed_by | assessment → expert | |
| raised_by | risk_finding → assessment | evidence_report_id=통합 보고서 |
| concerns | risk_finding → part \| model \| failure_mode \| defect | |
| mitigated_by | risk_finding → design_diff | |
| verified_by | risk_finding → incident \| test_run | 라벨 confirmed |
| refuted_by | risk_finding → incident \| test_run | 라벨 refuted |
| exhibits | project \| design_snapshot → design_trait | 관계 속성 support number · origin enum[auto,seat,chair] |
| revision_of | project → project | acyclic, 과제 계보 전용(기존 `supersedes/variant_of` 는 model 축 전용이라 재사용 금지) |

부트스트랩 통과 기준은 "list_object_types 에 6축·12관계, 2회 실행 시 생성 0건, 기존 15축·17관계 무변경" 이다(§9 P0).

### 0.3.3 AIDataHub(REST `POST /api/records/import?external_source=hwax-risk` + `_external_id` UPSERT, `create_doc_type`·`create_agent` 1회 — 호출자는 hwax_risk 앱, `X-API-Key`=`HWAXRISK_AIDH_API_KEY`)

| 이름 | 종류 | 역할(정의 절) |
|---|---|---|
| risk_review_opinion | doc_type(llm_context, 7섹션) | seat_opinion 서술 레코드(§4, §5) |
| risk_review_panel | doc_type(llm_context) | 패널 결정 산문·risk_spec(§5) |
| project_character | doc_type(llm_context) | character_profile 1레코드/과제(§4, §5) |
| risk_pattern_card | doc_type(llm_context, P6) | known 패턴 카드(§7) |
| design_snapshot_digest | doc_type(data_extract, 선택) | 카운트·상위 계면 표(§5) |
| risk-review-memory | 의사 에이전트(create_agent) | 좌석 개인 기억 회수 범위. 의견 레코드 `agents` 에는 실 전문가 키를 넣지 않는다(§5, §10) |

규약. team/group 은 사용자 확인값만 쓰고 자동 채움 금지, `bind_records_to_agent`·`patch_agent` 호출 금지, e5 코사인은 상대 순위만 쓴다.

### 0.3.4 기존 저장소(무수정)

conv_store(kind 값 `risk-review` 추가만) · token_store · RA 보고서(`deliberation` 템플릿+tags, 'risk-review' typed 템플릿은 관리자 등록 후 선택) · StepForge/DynaForge DB(읽기 전용, REST GET·읽기 도구만).

## 0.4 파일·모듈 이름 총목록

### 0.4.1 앱 리포 `HWAXRisk`(신규 리포, 매니페스트 id `hwax_risk`)

리포 경로 `/home/koopark/claude/HWAXRisk`(GitHub `squall321/HWAXRisk`, 매니페스트 `source.url` 정본 — `file://` dev 경로는 cae00 스캔 fetch 실패 메일을 반복시키므로 쓰지 않는다). ThermalShockMCP 의 `app/{main,config,mcp_server}.py` 골격과 `HEAX_DATA_DIR` 폴백 규칙을 복제하되, UI 를 함께 싣기 위해 HEAX `fastapi_react` 스택 계약(저장소 루트에 `backend/`·`frontend/`, SIF 안 `/app/backend`·`/app/frontend/dist`, entrypoint `uvicorn app.main:app --host 127.0.0.1 --port $PORT --root-path $ROOT_PATH`, health `/api/health`)에 맞춰 `app` 패키지를 `backend/` 아래에 둔다. 아래 파일명은 A 계획의 모듈명을 그대로 옮긴 것이다.

| 파일 | 역할 |
|---|---|
| `.portal/manifest.yaml` | 매니페스트 정본(값은 §0.1.6 hwax_risk 행). 등록 사본은 HEAXHub `integrations/hwax-risk/.portal/manifest.yaml`(동일 내용, §0.4.4) |
| `backend/pyproject.toml` | deps `fastapi · uvicorn[standard] · 'mcp>=1.10,<2'(2.0 은 FastMCP 제거) · pydantic · httpx`, setuptools `packages.find include app*` |
| `backend/app/__init__.py` | 패키지(플래그 없음 — 앱 존재가 곧 활성) |
| `backend/app/main.py` | FastAPI `app`. 등록 순서 고정 — ① `/api/health`·`/api/*` REST 라우터 ② MCP 라우트 이식 — `mcp._session_manager = None` 후 `for r in mcp.streamable_http_app().routes: app.router.routes.append(r)`(기본 `streamable_http_path='/mcp'` 의 `Route('/mcp')` 가 exact 매칭, 리다이렉트 없음 — MaterialTwinWeb `backend/app/main.py:53-61` 선례) ③ 마지막에 `app.mount('/', StaticFiles(directory=<main.py 기준 ../../frontend/dist>, html=True))`. lifespan 에 `mcp.session_manager.run()` 과 러너 기동. `app.mount('/mcp', …)` 는 Starlette Mount 가 슬래시 없는 `/mcp` 를 307 → `/mcp/` 로 보내 MCP 클라이언트·게이트웨이가 따라가지 못하고(2026-08-31 실측, D7), thermal 방식 `mount('/', mcp_app)` 은 SPA 마운트를 삼키므로 둘 다 쓰지 않는다 |
| `backend/app/config.py` | Settings(§0.5.3). 데이터 루트 = `HWAXRISK_DATA_DIR` > `HEAX_DATA_DIR` > `<리포>/data`, DB `risk_review.db`, 시크릿 `secrets.env`(0600, 기동 시 로드) |
| `backend/app/identity.py` | 인바운드 신원 해석 — `Authorization: Bearer` 우선, 없으면 쿠키 `heax_access_token` 값을 Bearer 로 삼아 heax `GET /api/v1/auth/me`(`HWAXRISK_HEAX_API`) 조회 `{id, email, display_name, role, organization}`, 토큰 sha256 키 TTL 캐시(60 s). 둘 다 없으면 익명 읽기 전용. `X-Heax-User-*` 헤더는 service 모드 앱에 복사되지 않고 위조 가능하므로 신원으로 쓰지 않는다 |
| `backend/app/risk_store.py` | RiskStore(sqlite3+Lock, CREATE TABLE IF NOT EXISTS, owner_sub 강제, `PRAGMA journal_mode=WAL`) |
| `backend/app/adapters/base.py` | `IrAdapter{kind, version, discover(registry), capture(ref, principal) -> AdapterResult}` |
| `backend/app/adapters/registry.py` | 게이트웨이 `/tools-map`·heax `/api/v1/mcp/servers` 로 소스 앱 발견(앱명 하드코딩 금지) |
| `backend/app/adapters/mcad.py` | StepForge REST 원문(Caddy `/apps/step_forge/api` `/tree`, `/artifacts/graph/`, `/parts`, 헤더 `Authorization: Bearer <HWAXRISK_HEAX_SERVICE_PAT>`)+게이트웨이 MCP `heax-step_forge` 읽기 |
| `backend/app/adapters/dyna.py` | DynaForge `inspect_file`·`report_*` 읽기(게이트웨이 MCP `heax-kooremapper_mcp`, 호출 PAT 는 §0.1.6 러너 자격 (b)), 브리지 검증, `_group_of` 재구현 |
| `backend/app/adapters/ecad_stub.py` | ODB 계약 4도구 존재 검사, 부재 시 `ecad_absent` |
| `backend/app/adapters/ecad.py` | P7 실연동(계약 이행 시) |
| `backend/app/ir_builder.py` | rr_ir 조립·ir_hash·rollups·dims_named 재평가·원장 재적용 |
| `backend/app/sameas.py` | same-as 사다리·헝가리안·ckey 부여·원장 재적용 |
| `backend/app/diff.py` | 3층 diff·임계·comparability·rollup·의미 이벤트 |
| `backend/app/state.py` | rr_state·게이트 G1~G7·signals·character_seed·feature_vector·rule_hits |
| `backend/app/render.py` | 정규 표기·summary_text·판단어 린터 |
| `backend/app/taxonomy.py` | `assets/taxonomy.v1.json` 로더·버전·unclassified 처리 |
| `backend/app/planner.py` | Tier·라운드로빈·인접 표·deferred·carried 편성 |
| `backend/app/runner.py` | 배치 러너·세마포어·포털 `POST /agent/chat`(포털 PAT Bearer)·SSE 캡처·상태기계 |
| `backend/app/registry.py` | 등록부 병합·완결 판정 C0~C3·통합 보고서 조립 |
| `backend/app/narrative.py` | parse_risk_spec·cites 해석·seat_opinion 추출·prior_evidence(E0~E9) |
| `backend/app/character.py` | character_profile 합성·승격 |
| `backend/app/ra_client.py` | RA 쓰기 4종·좌석 조회를 게이트웨이 MCP(`HWAXRISK_GATEWAY_MCP`, 포털 PAT Bearer) 로 호출하는 래퍼(멱등 upsert, get_object 후 병합). RA 토큰은 앱이 보유하지 않는다 |
| `backend/app/adh_client.py` | AIDataHub REST import UPSERT·doc_type·agent(`X-API-Key`) |
| `backend/app/routes.py` | FastAPI 라우터 prefix `/api`(§0.5.1), 인증 `identity.py` |
| `backend/app/mcp_server.py` | FastMCP `hwax-risk` 도구(§0.5.2), `TransportSecuritySettings(enable_dns_rebinding_protection=False)`(loopback+Caddy 전제) |
| `backend/app/export.py` | JSONL export/import(P1+, 멱등 병합 규칙 재사용) |
| `backend/app/assets/{taxonomy, character-vocab, character-seed-rules, adjacency, rules-seed, seat-contract}.v1.json` | 런타임 자산 정본(A 계획의 `docs/design-risk-review/*.v1.json` 을 여기로 이동, 문서 디렉터리에는 두지 않는다) |
| `backend/app/schemas/{rr_ir, rr_state, rr_diff, risk_spec, seat_opinion}.v1.json` | JSON 스키마 + 유효/무효 픽스처 |
| `backend/scripts/bootstrap_ra_ontology.py` | 6축·12관계 멱등 부트스트랩(dry-run 기본, 실행자 env `RA_ADMIN_PAT`) |
| `backend/scripts/bootstrap_adh.py` | doc_type·의사 에이전트 생성(실행자 env `HWAXRISK_AIDH_API_KEY`) |
| `backend/tests/` | pytest(스키마 라운드트립·게이트 픽스처·diff 합성 쌍·상태기계 불변식·편성 결정론·SSE 귀속·기동 순서 `/api/health`·`/mcp` initialize·`/` index.html) |
| `backend/tests/golden/sif-e2e.ir.json` | 골든 IR |
| `frontend/package.json` · `pnpm-lock.yaml` · `vite.config.ts`(`base: './'`) | Vite+React TS, fetch 는 `'api/…'` 상대경로 |
| `frontend/src/api/risk.api.ts` | REST 클라이언트 |
| `frontend/src/App.tsx` | 라우트 `/`, `/projects/:id`, `/compare`, `/targets/:key`, `/settings` |
| `frontend/src/pages/{RiskHomePage, ProjectPage, SnapshotPage, ComparePage, TargetPage, SettingsPage}.tsx` | A 계획 `pages/risk/*` 와 동일 역할. SettingsPage 는 사용자 포털 PAT 등록(§0.1.6 러너 자격 (b)) |
| `frontend/src/components/{SameAsResolver, GateBanner, DiffView, PanelRunner, RecallPreview, CoverageHeatmap}.tsx` | 부품 |

### 0.4.2 포털에 남는 파일(`HWAXPortal/`, 메뉴·타일·systems.yaml·env — 전부 additive)

| 파일 | 변경 |
|---|---|
| `backend/config/systems.yaml` | 타일 1건 `id: hwax-risk · name: 리스크 심사 · integration_type: jwt-handoff · audience: heax-hub · url: /heax-hub/api/v1/auth/portal-callback · handoff_mode: auto_post · handoff_param: token · status: available · required_role: (선택)`. 적용 `POST /systems/reload`(admin) |
| `frontend/src/App.tsx` | 라우트 `/risk` 1건(기존 6 라우트 무변경) |
| `frontend/src/components/layout/AppHeader.tsx` | NavLink '리스크 심사' 1건 — 카탈로그(`visible_for(groups)`)에 `hwax-risk` 타일이 있을 때만 표시(env 플래그 없음) |
| `frontend/src/pages/risk/RiskLaunchPage.tsx`(신규) | 얇은 셸 — ① `/launch/hwax-risk`(HEAX SSO, 쿠키 `heax_access_token` 획득) ② 앱 링크 `/apps/hwax_risk/` 새 탭(`window.open(..., '_blank', 'noopener')`) 2단. 앱 REST fetch 없음 |
| `frontend/src/components/chat/delibTaxonomy.ts` | JobId·JOBS·JOB_ROUTING 에 `risk-review`(심의 메뉴 L1 단발 진입, 유지) |
| `frontend/src/api/conversations.api.ts` | ConvKind `risk-review` |
| `backend/app/agent/routes.py` | DelibOpts personas `origin` 통과 · conv kind 화이트리스트 `risk-review`(2줄) |
| `backend/config/routes.env` · `infra/nginx/*` | 변경 없음(`/apps/` → Caddy, `/heax-hub/` strip 이미 존재) |
| 포털 env(`.env`) | 변경 없음(PAT 기본 audiences 에 `mcp-gateway` 포함) |

포털에 두지 않는 것(A 계획에서 이동·폐기). `backend/app/risk/` 패키지 → 앱 `backend/app/`. `/api/risk` 라우트 → 앱 `/apps/hwax_risk/api`. `data/risk_review.sqlite` → `$HEAX_DATA_DIR/risk_review.db`. `risk_review_enabled`·`risk_store_path` Settings → 폐기. `frontend/src/pages/risk/{RiskHomePage,…}` → 앱 `frontend/`. `backend/tests/risk/` → 앱 `backend/tests/`.

### 0.4.3 심의 엔진·파리티(additive, A 계획과 동일)

`HWAXAgentServer/deliberation.py`(`_CHAIR_ITEMS['risk-review']`, `_CHAIR_ADVERSARY['risk-review']`, doc_title, `_RISK_READ_TOOLS`, `_RISK_KEEP_TOOLS`, `_RISK_SEAT_CONTRACT`, `_resolve_opts` origin 통과) · `HWAXPortal/infra/pipeline/hwax-deliberate.js`(`CHAIR_ITEMS`·`CHAIR_ADVERSARY`·`RISK_SEAT_CONTRACT`·제목 삼항) · `HWAXPortal/scripts/check_chair_parity.py`(PY/JS 문자열 바이트 동일 검증) · `HWAXPortal/infra/scripts/sync-workflows.sh`(`.claude/workflows` 사본 동기, 기존 파일) · `HWAXAgentServer/tools/delib_metrics.py`(리스크 지표 7종 추가). 호출자가 포털 챗에서 앱 러너로 바뀔 뿐 항목 내용은 바뀌지 않는다.

### 0.4.4 HEAXHub(등록 1건 + 선택 additive)

| 파일 | 역할 |
|---|---|
| `integrations/hwax-risk/.portal/manifest.yaml` | 매니페스트 전용 디렉터리(심볼릭 링크 아님, 앱 리포 `.portal/manifest.yaml` 과 동일 내용)를 HEAXHub 에 커밋 → 5분 스캔(즉시 트리거 `backend/.venv/bin/python -c 'from app.workers.integration_tasks import scan_integrations_periodic as s; print(s()["by_action"])'`) → dev 가 `var/sifs/hwax-risk.sif`(+`.hash`) 빌드 → `var/app_data/hwax_risk/` 생성. 로그 `var/logs/sif_build_hwax-risk.log`·`var/logs/integration_hwax_risk.log` |
| cae00 배포(코드 없음, 절차) | dev `dist-to-drive.sh` 가 per-app SIF 를 Drive 로 → cae00 `deploy-all-from-drive.sh`/`update.sh` 의 `dist-from-drive.sh` 가 `var/sifs/` 배치 → 매니페스트는 HEAXHub git pull 로 도착 → 45 초 reconcile 이 SIF 로 기동(cae00 SIF 빌드 금지) → state 파일 생성 → `GET /api/v1/mcp/servers` 노출 → 게이트웨이 revive 루프가 `heax-hwax_risk` 흡수. 재빌드 후 전환 `redeploy-app.sh hwax-risk`. `deploy-all` 류는 dev 에서 돌리지 않는다 |
| app-data 왕복(코드 없음) | `build-all-to-drive.sh` → `appdata-to-drive.sh`(`var/app_data` 전체 tar, `*.db` 는 `.backup` 스냅샷, `latest/`+타임스탬프 5개) · 복원 `appdata-merge-from-drive.sh`(첫 배포 시드만, 이후 라이브 DB 무동작) · 강제 `HEAX_RESTORE_APPDATA=1 appdata-from-drive.sh`. `secrets.env` 도 함께 Drive 로 나가므로 제외 규칙은 §10 결정 |
| (선택) `backend/app/api/v1/portal_sso.py` | 콜백 `next` allowlist(`/heax-hub/apps/<slug>/`) additive — 채택 시 포털 `RiskLaunchPage` 2단이 1단이 된다(§10) |
| (선택) `backend/app/services/proxy_manager.py` | service 모드 `copy_identity`(launch.portal_auth 게이트) additive — 미채택이 기본이고 앱 `identity.py` 되묻기가 정본(§10) |

### 0.4.5 게이트웨이·파이프라인·문서

| 파일 | 역할 |
|---|---|
| `HWAXPortal/infra/pipeline/hwax-risk-review.js` | L2 오케스트레이터(+`.claude/workflows` 사본) — 게이트웨이 도구 `risk_get_brief` → `hwax-deliberate` 패널 → `risk_submit_panel_result` |
| `HWAXMcpGateway/gateway_config.json` | 변경 없음 — `heax-hwax_risk` 백엔드는 `heax_registry` 폴링으로 자동 흡수(코드·설정 변경 0). `rest.heax`·`portal.audience_ok` 추가는 P0 제외(앱이 heax 서비스 PAT 로 StepForge 를 직접 읽음, §10) |
| `HWAXPortal/docs/design-risk-review/plan.md` | 이 계획서 |
| `HWAXPortal/docs/design-risk-review/checklist.md` · `context-notes.md` | 체크리스트·결정 기록 |
| `HWAXRisk/docs/odb-adapter-contract.md`(앱 리포) | ODB 어댑터 계약 — 정본은 앱 리포(어댑터 코드와 같은 리포, 실존). 포털 `docs/design-risk-review/` 에는 두지 않는다(§2.5.3) |
| `HWAXPortal/docs/deliberation-quality/method-menu/decision-table.md` | Job 8행째·계약·파리티·기존 심의 영향 기록 |

문서 디렉터리는 `docs/design-risk-review/` 로 고정한다(1차 합성의 `docs/risk-review/` 표기는 이 이름으로 통일). 런타임 JSON 자산 6종(`taxonomy · character-vocab · character-seed-rules · adjacency · rules-seed · seat-contract`.v1.json)의 정본은 앱 리포 `backend/app/assets/` 이고(§0.4.1) 이 문서 디렉터리에는 두지 않는다 — 다른 절이 파일명만 부를 때는 그 경로를 뜻한다.

## 0.5 API·MCP·Settings 이름 총목록

### 0.5.1 앱 REST base `/apps/hwax_risk/api`(앱 내부 prefix `/api`, 정의는 §8)

브라우저·헤드리스 공통 호출 형식 `<Caddy 오리진>/apps/hwax_risk/api/<path>`(포털 오리진 `/apps/hwax_risk/api/<path>` 도 같은 곳으로 간다). Caddy forward_auth 가 쿠키 `heax_access_token` 또는 `Authorization: Bearer <heax JWT | heax_pat_…>` 로 200/401/403 을 판정하고 앱 `identity.py` 가 같은 자격으로 호출자를 해석한다. 경로 목록(A 계획과 동일, prefix 만 이동) — `GET /health` · `GET /me` · `PUT /me/portal-pat`(사용자 포털 PAT 등록, §0.1.6 러너 자격 (b)) · `POST /projects` · `GET /projects` · `GET /projects/{id}` · `POST /projects/{id}/sources` · `POST /projects/{id}/snapshots` · `GET /snapshots/{id}?part=ir|state|nodes|edges|calls` · `POST /projects/{id}/dims` · `GET /sameas?base=&target=` · `POST /sameas/decide` · `PUT /projects/{id}/iface-ledger` · `POST /diffs` · `GET /diffs/{id}?part=diff|summary|events` · `POST /targets` · `POST /targets/{key}/jobs` · `POST /jobs/{id}/pause|resume|cancel` · `GET /targets/{key}/coverage|registry|panels|brief` · `PUT /targets/{key}/verdict` · `PUT /registry/{cluster}/status` · `POST /panels/{id}/complete` · `GET /projects/{id}/character|similar` · `GET /refs/{ref}` · `GET /snapshots/{id}/rule_hits` · `GET /precedents?diff_id=` · `POST /targets/{key}/refresh_roster` · `GET /meta/taxonomy|adapters|metrics` · `GET /export?since=`·`POST /import`(JSONL, dev↔cae00 이동, P1+).

### 0.5.2 앱 MCP(`/apps/hwax_risk/mcp` → 게이트웨이 백엔드 `heax-hwax_risk`)

앱 내부 `/mcp`(FastMCP streamable_http). 노출 조건 = 매니페스트 `status beta|stable` + `mcp.expose true` + 기동 이력(state 파일) + heax 서비스 PAT 사용자 가시성 안. 게이트웨이는 `Authorization: Bearer <heax 서비스 PAT>` 로 호출하므로 최종 사용자·그룹은 앱에 전달되지 않는다. 도구 — `risk_get_snapshot(snapshot_id, part)` · `risk_get_diff(diff_id, part)` · `risk_get_registry(target_key)` · `risk_claims_for_ref(ref)` · `risk_get_brief(target_key, tier='B')`(prior_evidence E0~E9 를 delib_opts.evidence 형식으로 반환, L2 진입, `tier='A'` 는 `{error:'tier_a_web_only'}`) · `risk_submit_panel_result(panel_id, engine, decision_text, turns, report_id, actor, model?)`(`actor` = 이메일, 게이트웨이 신고값·미검증 표기. `model?` = 호출자 신고 모델명 → `rr_panels.model_json{captured:'caller_reported'}`, 없으면 `'unknown'` — D6, §6.11). `mcp.allowed_groups` 는 빈 목록(전체 공개)으로 시작하고 그룹 스코핑은 §10 결정이다.

### 0.5.3 Settings(앱 `backend/app/config.py`, env 접두 `HWAXRISK_`)

Settings 속성명은 A 계획의 `risk_*` 를 그대로 두고 env 는 `HWAXRISK_<대문자>` 로 읽는다(예 `risk_concurrency` ← `HWAXRISK_CONCURRENCY`). HEAX 가 강제하는 env(앱이 덮을 수 없음) — `PORT · HOST=127.0.0.1 · HEAX_DATA_DIR · ROOT_PATH=/apps/hwax_risk`(+`BASE_PATH` 동의어 5종). 앱 env(매니페스트 `launch.env` 또는 `secrets.env`) — `HWAXRISK_DATA_DIR`(매니페스트 `/data`, 우선순위 `HWAXRISK_DATA_DIR > HEAX_DATA_DIR > <리포>/data`) · `HWAXRISK_PORTAL_BASE`(기본 `http://127.0.0.1:5283`, 포털 nginx 오리진 — `/agent/chat` SSE 는 nginx `proxy_buffering off` 경로여야 한다) · `HWAXRISK_HEAX_API`(기본 `http://127.0.0.1:4040`, `/api/v1/auth/me`) · `HWAXRISK_HEAX_BASE`(기본 `http://127.0.0.1:4180`, Caddy `/apps/step_forge/api`) · `HWAXRISK_GATEWAY_MCP`(기본 `http://127.0.0.1:9110/mcp`) · `risk_roster_domains`(15) · `risk_ecad_domains`(6) · `risk_adjacency`(JSON) · `risk_concurrency=2` · `risk_daily_panel_cap=24` · `risk_default_close_level='C2'` · `risk_carried_days=90` · `risk_panel_llm_cap=120` · `adh_team` · `adh_group`. 시크릿(`$HEAX_DATA_DIR/secrets.env`, 0600, HEAX secret_manager 는 integration 앱에 배선되지 않음) — `HWAXRISK_PORTAL_PAT`(서비스 계정 포털 PAT, aud `mcp-gateway`) · `HWAXRISK_HEAX_SERVICE_PAT`(`heax_pat_…`, StepForge 직접 읽기) · `HWAXRISK_AIDH_API_KEY`. `RA_ADMIN_PAT` 는 `bootstrap_ra_ontology.py` 실행자 env 만이고 앱 런타임은 RA 토큰을 갖지 않는다. 폐기 — `risk_review_enabled`(앱 존재가 활성)·`risk_store_path`(파일명 `risk_review.db` 고정)·`ra_admin_pat`·`adh_api_key`(이름 변경). 앱은 `GW_TOKEN · X-Heax-Gateway-Secret · kr_ · rat_` 토큰을 보유하지 않는다.

### 0.5.4 엔진 상수·문자열(PY/JS 바이트 동일)

`_CHAIR_ITEMS["risk-review"]` / `CHAIR_ITEMS['risk-review']` · `_CHAIR_ADVERSARY["risk-review"]` / `CHAIR_ADVERSARY['risk-review']` · `_RISK_SEAT_CONTRACT` / `RISK_SEAT_CONTRACT` · doc_title '리스크 심사 보고서' · `_RISK_READ_TOOLS`(PY 전용) · `_RISK_KEEP_TOOLS`(PY 전용).

## 0.6 공유 상수표(절 간 수치 불일치 방지)

| 항목 | 값 | 위치(정본이 사는 곳) |
|---|---|---|
| 패널 좌석 | 6(primary 4 + counter 1 + adversary 1), rounds 3, free_tools 1, tool_budget 3, modifiers 기본 `['toulmin']`(Tier A 는 `premortem` 추가 선택) | 앱 `backend/app/planner.py` 상수 |
| delib_opts 상한 | tools ≤6, apps ≤3, evidence ≤12항목. 엔진 클램프(PY `_resolve_opts` :464-467 / JS :128-130) source ≤120·tool ≤80·args ≤400·result ≤2000. 예산 11000 은 `result` 가 아니라 라인 `· [source · tool(args)] result` 전체 길이의 누적(PY :2164-2168 / JS :130-133)이며 초과 항목부터 통째 드롭. 앱 예산표(§5.6.1)는 라인 기준 합 10600 으로 드롭 0 을 보장 | 엔진(`deliberation.py`·`hwax-deliberate.js`) 클램프 + 앱 `narrative.py` 예산표 |
| 프롬프트 상한 | tool_inject 5000자, 지식카드 3500자/석, 자유조회 블록 3500자/석, role ≤2000자 | 엔진 `deliberation.py` |
| 저장 상한 | turns 60/대화, activity 60, RA rich_text 1900자 분할, seat_opinion say_excerpt ≤2000자·excerpt_for_rag ≤1500자 | 포털 conv_store(turns·activity) · 앱 `ra_client.py`(rich_text) · 앱 `narrative.py`(excerpt) |
| E7 슬롯 | 좌석당 줄 ≤220자(참조 접두 포함), 좌석 합 ≤1100자, 항목 라인 상한 1400자(오버헤드 ≈171 + 프레이밍 ≤80 을 뺀 실효 ≥1100) | 앱 `narrative.py` |
| 예산 게이트 | 좌석 수·rounds 로 사전 산정한 LLM 호출이 `risk_panel_llm_cap`(120) 초과 예상이면 rounds=2 로 편성, 사후 초과는 `quality.flag=over_budget`(재실행 없음) | 앱 `planner.py`(사전) · `runner.py`(사후) |
| 재시도 | 패널 error → retry+1, retry > 2 → skipped(reason=engine_fail). `parse_retries` 하한 2 는 search_sources 사용 시에만(toulmin 무관). 포털 `/agent/chat` 429(세마포어 초과)는 error 가 아니라 대기 후 재시도(패널 카운트 무증가) | 앱 `runner.py` |
| 동시성 | risk_concurrency 2(타깃 다를 때만), 타깃당 패널 직렬, 일일 상한 24. 포털 세마포어·nginx 1 h·`timeout_s ≤1800` 아래 | 앱 `config.py`(`HWAXRISK_CONCURRENCY`·`HWAXRISK_DAILY_PANEL_CAP`) |
| carried | ≤ risk_carried_days(90) | 앱 `config.py`(`HWAXRISK_CARRIED_DAYS`) |
| 완결 | C1 = 15 도메인 종결 ≥1 AND Tier A 3패널 done. C2 = 도메인별 종결 ≥ max(3, ceil(0.3·\|d\|)) AND strong 비율 ≥0.7 AND contested 표기 완료 AND 파싱 실패 0. C3 = 로스터 전원 종결 AND skipped ≤5% AND failed 0. RA 반영은 조건에 넣지 않고 external_sync 로 표기 | 앱 `registry.py` |
| 패널 품질 목표 | 도구 사용률 ≥80%(귀속 가능 좌석), IR 인용률 ≥50%(name: 포함), 반대석 기각률 10~40%, 귀속 성공률 ≥95% | 앱 `runner.py`(quality_json) · `delib_metrics.py`(지표) |
| 패턴 승격 | candidate: 타깃 ≥3·project ≥2·expert ≥2. known: 큐레이터 승인 AND (confirmed ≥1 OR finding ≥5 across project ≥3). rule: n_labeled ≥10·precision ≥0.6·recall ≥0.5. predictor: n_labeled ≥50·project ≥15·CV R² ≥0.6 또는 AUROC ≥0.75 | 앱 `character.py`·`registry.py`(승격 판정) |
| 로스터 실측 | ≈350(xd 122 · sim 22 · cam 21 · rel 20 · soc 20 · disp 19 · mech 19 · pcb 19 · rf 19 · passive 18 · pwr 18 · sh 17 · mem 16 · std 8 · material 1), ECAD 부재 시 deferred ≈105 | 앱 `planner.py`(런타임 재계산) |
| Tier 패널 수 | 패널 수 = ceil(추가 좌석 / 5). 실측 ≈350: A 3 · B +20(누적 114석) · C +48(236석), 합 71. ECAD 부재(deferred ≈104): A 3 · B +14(85석) · C +33(161석), 합 50. §0.1.5 Tier 행·§6.4.1 표와 동일 수치 | 앱 `planner.py` |
| 좌석 계약·인접·어휘·규칙 시드 | `seat-contract · adjacency · character-vocab · character-seed-rules · rules-seed · taxonomy`.v1.json | 앱 `backend/app/assets/`(정본) · 엔진 `_RISK_SEAT_CONTRACT`/`RISK_SEAT_CONTRACT`(좌석 계약 사본, parity 검증) |
| 앱 리소스 | `resources{cpu 1, memory_gb 2, gpu false}`(enforce_instance_limits 시 cgroup 강제), 헬스 대기 20 s | HEAXHub `integrations/hwax-risk/.portal/manifest.yaml` |

## 0.7 1차 비평 반영 결정(이름 수준)

| # | gap_21 항목 | 이 정본의 결정 |
|---|---|---|
| 1 | §1~§6.3 부재 | §2·§3·§4·§5 가 rr_ir·G1~G7·의미 이벤트·E0~E9 예산표·summary_text 규칙을 이 사전의 이름으로 적는다 |
| 2 | ckey 가 쌍 단위 | `ckey = canonical_part_key`(과제 무관 계산식) 로 재정의, rr_iface_alias 는 무순서 ckey 쌍, §7.3 4단계는 'canonical 매치 + geom_fp 근접' |
| 3 | role 접미 유실(`_restore_role`) | 주경로를 `_RISK_SEAT_CONTRACT`/`RISK_SEAT_CONTRACT` 엔진 상수(chair 조건부)로 확정, E0c 로 이중화, parity 검증 대상 포함 |
| 4 | apps 제한이 rel·std·pcb 도구 제거 | `_RISK_READ_TOOLS`(앱 조건부)·`_RISK_KEEP_TOOLS`(chair 조건부)를 자유조회 조립식 `_g`(:1897-1898)의 접두사 검문과 or 로 넣고 `_narrow` 에 keep or 1줄, 계약표에 '통과 경로' 열 |
| 5 | status.persona 없음 | §0.2.3 캡처 규약(step 접두·evidence.source 분리), tool_calls_n/tool_calls_ok |
| 6 | 전원 요구 대 C2 마감 | `risk_default_close_level`, 진행판 '미착석 N명(C3 미달)' 배지 |
| 7 | P0 파서 시점·C1 의 RA 의존 | parse_risk_spec 은 P0 산출물, C1 에서 RA 절 제거·`external_sync` |
| 8 | 좌석 개인 기억 회수 | E7 고정 슬롯(좌석당 줄 ≤220자), risk-review-memory 유지, 실 전문가 키 기입 대안은 §10 |
| 9 | `_chat_user_pat`·revision_of 미확인 | PAT 발급은 P0 실측 항목 + 폴백 명시, `revision_of{project→project, acyclic}` 를 12관계 표에 포함, 6축·12관계 전표 §0.3.2 |
| 10 | toulmin 재시도·120 초과 재실행 | §0.6 예산 게이트(사전 편성·사후 flag), toulmin 재시도 줄 삭제 |
| 11 | 불변식 검증력 | `extra_seats == ∅` 로 강화, human_note·continue_summary 미탑재 명시 |
| 12 | B 결정(2026-08-31): 자산은 앱, 포털은 창 | 이 기능을 별도 HEAX 앱 `hwax_risk`(리포 `HWAXRisk`, §0.1.6 이름 대응표)로 만든다. 심사 결과가 누적·정리되는 자산 전부(IR 스냅샷·diff·의견 원자·등록부·성격 프로파일·커버리지 원장·학습 산출)는 앱이 소유한다 — 전용 DB `$HEAX_DATA_DIR/risk_review.db`(§0.3.1) + REST `/apps/hwax_risk/api`(§0.5.1) + MCP `/apps/hwax_risk/mcp`(§0.5.2) + UI(앱 SPA) + 러너(앱 프로세스) + app-data Drive 왕복(§0.4.4). 포털은 '심의' 와 별개의 새 메뉴 창 하나만 둔다 — `systems.yaml` 타일 `hwax-risk`·라우트 `/risk`·NavLink·`RiskLaunchPage`(§0.4.2), 포털 SPA 는 앱 REST 를 직접 fetch 하지 않는다. 바뀌지 않는 것 — rr_* 스키마 33표·원자·해시 규약·prior_evidence E0~E9·커버리지 상태기계·학습 루프·재분석 멱등 규칙(같으면 지지+1 병합·다르면 add(dissent/stale))·엔진 additive 항목(`_CHAIR_ITEMS['risk-review']`·지정 반대석·좌석 계약·`_RISK_READ_TOOLS`·`_RISK_KEEP_TOOLS`)·RA 6축 12관계·AIDataHub doc_type. 바뀌는 것 — 위치(포털 sqlite → 앱 DB), 호출 경로·인증(포털 세션 → Caddy forward_auth + 앱 `identity.py` 되묻기, 러너 → 포털 PAT Bearer, 게이트웨이 MCP → heax 서비스 PAT + `actor`), P0 산출물(§9 — 앱 리포 골격·매니페스트 등록·기동 3점 테스트) |

## 0.8 목차(고정)

| 번호 | 제목 | 이 절이 정의하는 것 |
|---|---|---|
| §0 | 공통 정본(spine) | 이 문서 |
| §1 | 핵심 명제 | 메뉴가 하는 일 한 줄(애매동사 금지)·산출물·하지 않는 것·헌법 준수 |
| §2 | 설계 IR | rr_ir 스키마(노드·엣지·same_as·dims_named·rollups·results·missing)·ckey·원장·어댑터 계약·ir_hash·rr_snapshot_calls |
| §3 | 그래프 diff 와 상태 평가 | rr_state(G1~G7·signals·character_seed·feature_vector·rule_hits)·rr_diff 3층·의미 이벤트 코드표·임계·comparability·summary_text·판단어 린터 |
| §4 | 과제 평가 서술 | risk_spec·finding·seat_opinion·character_narrative(facet 8)·cites 검증·등록부 병합·verdict 집계·통합 보고서 블록 |
| §5 | 저장과 재사용 | 3층 스키마 전문(DDL·RA 속성·doc_type 섹션)·id 매핑·prior_evidence E0~E9 예산표·유사 검색·다른 connectivity 회수 |
| §6 | 전문가 크로스도메인 워크플로 | 로스터·planner·좌석 계약·Job 'risk-review'·runner 시퀀스·커버리지 상태기계·완결 판정·비용·MCP 실행 등급 |
| §7 | 학습 루프 | 택소노미·인덱스·delta 선례·패턴 승격 상태기계·조건 DSL·라벨 5경로·지표·배지 |
| §8 | 포털·MCP 통합 | 포털 창·앱 hwax_risk(REST·SPA·MCP·러너)·MCP 파리티(L1/L2)·무손상 변경 목록·반영 절차 |
| §9 | 단계 계획 | P0~P7 목표·산출물·의존·수치 통과 기준·리스크·'이 단계만으로 얻는 것' |
| §10 | 열린 질문·결정 필요 | 승인·보안·예산·어휘·ODB·공유 정책·앱 등록·배치 결정 목록 |

---


# §1 핵심 명제

## 1.1 한 줄(애매동사 없이)

HEAX 앱 `hwax_risk`(표시명 HWAX Risk Review, 경로 `/apps/hwax_risk`, 리포 `HWAXRisk`)는 과제의 MCAD(StepForge)·Dyna(DynaForge)·ECAD(ODB hub 어댑터, 스텁) 소스를 **읽어** 불변 설계 IR 스냅샷(rr_ir)으로 **동결하고**, 단일 스냅샷의 상태(rr_state) 또는 두 스냅샷의 3층 diff(rr_diff)를 결론 없이 코드가 **정리하며**, HW/XD 전문가 로스터 ≈350석이 한 번씩 자기 도구로 검토한 의견을 IR id 에 앵커된 finding·gain·성격 서술로 자기 DB(`$HEAX_DATA_DIR/risk_review.db`)에 **저장하고**, 그 저장물을 다음 과제·계보 없는 다른 connectivity 의 심사 브리프에 원천 그대로 **되먹여** '리스크 심사 보고서' 를 **낸다**. 포털 '리스크 심사' 메뉴는 그 앱 화면을 **여는** 창이고(타일·launch·링크), 자산은 전부 앱이 소유한다(B 결정, §0.7 #12). 앞 문장의 다섯 동사가 각각 §2(동결)·§3(정리)·§4(저장 형식)·§5(되먹임)·§6(로스터 실행)의 정의 대상이고, '여는' 은 §8 의 정의 대상이다.

## 1.2 무엇을 만들고 왜 유용한가

지금 각 허브는 자기 도메인 안에서만 그래프를 안다. StepForge 는 파트·계면 그래프를, DynaForge 는 PID·접촉·하중경로를, ODB hub 는 넷·컴포넌트·스택업을 낼 수 있지만, 셋을 한 과제의 한 시점으로 묶어 주는 정본이 없고, 재파싱·재검출이 노드 id 와 사람 확정을 지우며, 두 과제를 비교할 키도 없다. 그래서 전문가가 "이번 과제에서 두께가 0.2 mm 줄고 접합이 닿음으로 바뀌었다" 는 사실 위에 자기 관점의 리스크를 말해도 그 말은 대화 로그로 흩어지고 다음 과제에서 다시 꺼낼 수 없다. 이 기능이 만드는 것은 그 빈자리를 채우는 네 층이다. 첫째, 세 소스를 읽기 전용으로 읽어 노드·엣지·same_as·dims_named·results 를 한 JSON(rr_ir)으로 정규화하고 `(project_id, ir_hash)` 로 동결해 재추출해도 같은 값이 나오는 불변 스냅샷을 둔다(§2). 둘째, 그 스냅샷에서 게이트·신호·성격 씨앗·규칙 히트를, 두 스냅샷에서 구조·파라메트릭·의미 3층 diff 와 판단어 없는 summary_text 를 코드가 결정론으로 만들어 전문가가 "무엇이 바뀌었나" 를 읽는 데 LLM 을 쓰지 않게 한다(§3). 셋째, 전문가 패널의 결정문 뒤 기계판독 risk_spec 에서 finding·gain·cross_domain·성격 진술을 뽑아 모든 문장이 `[c:]·[e:]·[p:]·[d:]` 참조를 달고 근거 등급이 자동 산출되는 원자로 저장한다(§4). 넷째, 그 원자가 과제 무관 정규 키(ckey·subject_key)와 cluster_key 로 색인되어 계보가 있든 없든 다음 타깃의 브리프 E5~E8 에 "검증 대상" 으로 실리고, 라벨이 붙으면 delta 선례·패턴·규칙으로 승격되어 배치를 만들수록 새 그래프에 알려진 리스크가 심사 없이도 먼저 붙는다(§5, §7). 유용한 이유는 세 가지다. 전문가 350명이 각자 도구를 직접 호출해 IR 수치를 축어로 인용하지 않으면 의견이 저장되지 않으므로(used_tool·cited_refs) 감상이 아니라 근거 있는 서술만 쌓이고, 커버리지 원장 PK(target_key, agent_key)가 "한 번 하면 넘어감" 을 DB 제약으로 보장해 같은 전문가가 같은 타깃을 두 번 보지 않으며, 성격 통제 어휘 8 facet 이 숫자 diff 로는 드러나지 않는 "이 과제는 접합 지배형이고 미확정 계면이 설계 여유를 결정한다" 같은 성격을 검색 가능한 형태로 남긴다. 이 네 층이 사는 곳은 하나다 — HEAX 앱 `hwax_risk` 의 전용 DB·REST·MCP·UI 가 소유하고 app-data Drive 백업으로 지속되며(§0.3.1, §0.4.4), 포털은 메뉴·타일·launch 창만 둔다. 그래서 심의 엔진·RA·AIDataHub 는 앱의 부산물 저장처이고 정본 소비자는 앱 DB 다.

## 1.3 기존 자산 위의 조립(무엇을 어떻게 쓰고 무엇을 건드리지 않나)

이 기능은 신규 엔진이 아니라 아래 자산을 래퍼·dict 항목·읽기 도구·관리 API 로 잇는 조립층이다.

| 자산 | 이 기능이 가져다 쓰는 것 | 쓰는 방식 | 건드리지 않는 것 |
|---|---|---|---|
| StepForge(`heax-step_forge`) | tree.json·graph.json·/parts REST 원문, MCP 읽기 도구(list_parts·list_interfaces·interface_graph·project_tree·part_mesh_map·mesh_report·job_status·inspect_report) | 읽기 전용 — 앱 `adapters/mcad.py` 가 heax 서비스 PAT(`HWAXRISK_HEAX_SERVICE_PAT`)로 Caddy `/apps/step_forge/api` GET + 게이트웨이 MCP `heax-step_forge`(포털 PAT). StepForge 는 자체 인증·소유권이 없어 서비스 시야가 전체 시야다. rest_proxy heax 사이트는 쓰지 않는다 | stepforge.db 무쓰기. `set_interface·confirm_interfaces·run_job` 은 사람이 명시 버튼으로만 실행(§2.10 'StepForge 에 반영') |
| DynaForge(`heax-kooremapper_mcp`) | `inspect_file`(meta.modelmeta 정본)·`report_summary/part_risk/findings/energy_flow/worst_cases`·전사 집계 3종(material_usage·section_contact_usage·corpus_summary) | 앱 `adapters/dyna.py` 가 게이트웨이 MCP 를 '그 사용자의 포털 PAT'(앱 설정 등록, §0.1.6 러너 자격 (b)) 로 호출해 per_user_sso 가 PAT email 로 발동. 미등록이면 서비스 PAT 시야(세션 0건) = `dyna_absent` 강등(§2.13) | `run_operation` 자동 실행 금지(modelmeta detect 는 사용자 실행 후 download_result 결과를 어댑터에 전달). 도구 시그니처·응답 형식 불변. KooRemapper C++ 확장(SECID 등) 범위 밖. `kr_`·`X-Heax-Gateway-Secret` 은 앱이 보유하지 않는다 |
| ODB hub(ECAD) | 어댑터 계약 4도구 `odb_get_board·odb_list_components·odb_list_nets·odb_get_stackup` | 계약 문서 + `ecad_stub.py` 존재 검사 | 실연동 코드 없음(P7 조건부). 계약 밖 필드 가정 금지 |
| ReportArchive KG | 신규 6축·12관계(§0.3.2), `deliberation` 템플릿 보고서, `search_objects·get_object·get_subgraph·search_reports` 좌석 조회 | 관리 REST 부트스트랩 1회 + MCP 인스턴스 쓰기 4종(`create_object·update_object·add_object_alias·link_objects`) | RA 코드 커밋·푸시 금지(hands-off). 기존 15축·17관계 무변경. part 축 별칭은 `add_object_alias` 로만 |
| AIDataHub | doc_type 5종·의사 에이전트 `risk-review-memory`(§0.3.3), `agent_search·recommend_agents·hybrid_search·get_record` | 앱 `adh_client.py` 가 REST `POST /api/records/import?external_source=hwax-risk` UPSERT(`X-API-Key`=`HWAXRISK_AIDH_API_KEY`), `create_doc_type·create_agent` 1회(`bootstrap_adh.py`) | `bind_records_to_agent·patch_agent` 호출 금지. team/group 자동 채움 금지. e5 코사인 절대값 비교 금지 |
| 심의 엔진 2종(`deliberation.py`·`hwax-deliberate.js`) | chair_template `risk-review` 항목, 지정 반대석 `delib-baseline-defender`, 좌석 계약 상수, 앱 조건부 읽기 도구 목록, `_RISK_KEEP_TOOLS` 1줄 통과 | dict 항목·상수·조건 1줄 추가(§8.4), `check_chair_parity.py` 바이트 동일 검증. 호출자는 앱 러너 — 포털 `POST /agent/chat` 을 포털 PAT Bearer 로(감사·세마포어·단명 user_pat 부착·conv_store 저장 동반), MCP 경로는 `hwax-risk-review.js` | 라운드 루프 본체·`_FREE_ALLOW` 전역·`_restore_role`·SSE 스키마·기존 8 chair·5 modifier·delib_opts 기존 키 의미·`/agent/chat` 계약 |
| HWAX Portal(창) | 메뉴·타일·launch 만 — `systems.yaml` 타일 `hwax-risk`(jwt-handoff, audience `heax-hub`), 라우트 `/risk`, NavLink '리스크 심사', `RiskLaunchPage.tsx`(launch → `/apps/hwax_risk/` 2단), delibTaxonomy Job `risk-review`(L1), conv_store kind `risk-review` | `POST /systems/reload` 로 타일 반영, 프론트 additive 3파일, 백엔드 additive 2줄(§0.4.2). 앱 REST 직접 fetch 없음(포털 SPA 는 heax bearer 부재·리프레시 불가) | 기존 라우트 6개·NavLink 4개·conv_store/token_store 스키마(kind 값 추가만)·`/agent/chat` 계약·routes.env·nginx·env |
| hwax-risk HEAX 앱(자산 소유) | DB `$HEAX_DATA_DIR/risk_review.db`(rr_* 33표)·REST `/apps/hwax_risk/api`·MCP `/apps/hwax_risk/mcp`(→ `heax-hwax_risk`)·UI(앱 SPA)·러너(앱 프로세스)·`identity.py`·`secrets.env` | HEAX 계약대로 — 매니페스트 `integrations/hwax-risk/` 1건, `fastapi_react` SIF, Caddy `/apps/hwax_risk/*` forward_auth, `HEAX_DATA_DIR` 주입, app-data Drive 왕복, heax_registry MCP 자동 흡수(§0.4.1, §0.4.4). 선례 = ThermalShockMCP(`main/config/mcp_server`·`HEAX_DATA_DIR` 폴백)·materialtwin-web(`fastapi_react`+UI+MCP) | HEAXHub 코드(선택 additive 2건은 §10 결정)·게이트웨이 코드·설정(자동 흡수)·다른 앱의 app_data |
| 선례 패턴 | thermal_shock 예측기 수명주기(학습데이터·재학습·버전), laminate `check_design_rules` 출력 형식(rule_hits), StepForge `compare_interfaces` 규약(kind 강도 순위·lost/gained/changed), `parseSimSpec`(risk_spec 파서), build-plan dry_run 게이트(G1~G7) | 형식·규약 복제 | 해당 앱 코드 |

## 1.4 산출물(사용자가 손에 쥐는 것)

| 산출물 | 형태 | 위치(정본 / 부산물) | 정의 절 |
|---|---|---|---|
| 포털 메뉴 창 | 타일 `hwax-risk` → `/launch/hwax-risk`(HEAX SSO) → `/apps/hwax_risk/` 새 탭 | 포털 `systems.yaml`·`RiskLaunchPage.tsx` | §8 |
| 과제 현황판 | rr_projects·소스 카드·스냅샷 목록·게이트 배너·character_seed·rule_hits | 앱 DB / 앱 UI `/projects/:id` | §2, §3, §8 |
| 스냅샷(rr_ir) | 불변 JSON + 노드/엣지 표 + mermaid, `GET /apps/hwax_risk/api/snapshots/{id}?part=ir\|state\|nodes\|edges\|calls` | 앱 DB `rr_snapshots` / RA `design_snapshot` 축·AIDataHub `design_snapshot_digest`(선택) | §2 |
| 비교 화면(rr_diff) | base/target 선택 → SameAsResolver → GateBanner → DiffView(3층) + summary_text | 앱 DB `rr_diffs` / 앱 UI `/compare` · RA `design_diff` 축 | §3 |
| 심사 타깃(rr_targets) | `snap:` 또는 `diff:` 단위 진행판·로스터·커버리지 히트맵·'미착석 N명(C3 미달)' 배지 | 앱 DB `rr_targets·rr_roster·rr_coverage` / 앱 UI `/targets/:key` | §6 |
| 패널 결정문 + risk_spec | RA `deliberation` 템플릿 보고서(패널마다), 대화(conv_store kind `risk-review`, owner = 호출 PAT sub) | 앱 DB `rr_panels`(risk_spec_json 정본) / RA 보고서(엔진이 게이트웨이 서비스 `rat_` 자격으로 저장)·포털 conv_store | §4, §6 |
| 의견 원자·finding | seat_opinion·finding·gain·cross_domain | 앱 DB `rr_seat_opinions·rr_findings` / RA `assessment·risk_finding` 축·AIDataHub `risk_review_opinion·risk_review_panel` | §4, §5 |
| 등록부(rr_registry) | cluster_key 병합 표·verdict 후보·사람 확정 `verdict_final` | 앱 DB `rr_registry` / 앱 UI | §4 |
| 리스크 심사 보고서(통합) | 레벨 상승(C1/C2/C3) 시 RA 보고서 v1/v2/v3 | RA 보고서(앱 `ra_client.py` 가 게이트웨이 도구로 생성) / 앱 DB `rr_targets.external_sync_json` | §4, §6 |
| 과제 성격 프로파일(character_profile) | facet 8 진술 + status seed→panel→confirmed, AIDataHub `project_character` | 앱 DB `rr_character` / AIDataHub `project_character`·RA `design_trait` 축 | §4, §5 |
| 유사 과제·선례 | 계보·feature_vector kNN·hybrid_search·subject_key 회수, E5~E8 | 앱 DB(`rr_states.feature_json`·`rr_registry`·`rr_iface_alias`) / AIDataHub 검색 | §5, §7 |
| 학습 산출 | rr_delta_priors·rr_patterns·rr_rules(rule_hits)·rr_metrics·'루프 작동' 배지 | 앱 DB / AIDataHub `risk_pattern_card`(P6) | §7 |
| 이동·백업 | Drive app-data 스냅샷(`risk_review.db` .backup), `GET /export`·`POST /import` JSONL(P1+) | HEAXHub `var/app_data/hwax_risk/` ↔ Drive `app-data/latest/` | §0.4.4, §9 |

## 1.5 하지 않는 것

- 소스 앱에 쓰지 않는다. StepForge parse/detect/set_interface, DynaForge run_operation 은 사람이 버튼으로 실행하고 화면은 "세션에 산출 파일이 생긴다" 를 명시한다.
- LLM 이 rr_ir·rr_state·rr_diff·summary_text 를 만들지 않는다. 전부 결정론 코드이고 판단어 린터를 통과해야 생성된다.
- 브리프(delib_opts.evidence)에 결론을 넣지 않는다. 이전 finding·성격 진술·선례도 "검증 대상" 프레이밍으로 원문만 싣는다.
- verdict 를 자동 승인하지 않는다. 등록부 집계는 후보이고 `verdict_final` 은 사람이 UI 로 확정한다.
- 패턴·규칙·예측기를 자동 활성화하지 않는다. 승격은 항상 사람 승인이다.
- RA 코드를 수정하지 않는다. ODB hub 를 실연동하지 않는다(계약과 스텁만).
- 기존 심의 메뉴(8 chair·5 modifier·핸드오프·시뮬 2단·시험 계획)의 동작을 바꾸지 않는다.
- 게이트웨이 서비스 계정으로 타 사용자의 DynaForge private 세션·리포트를 열지 않는다.
- 포털 SPA 가 앱 REST 를 직접 fetch 하지 않는다(heax bearer 부재·TTL 만료 후 조용한 401). 포털은 launch 로 앱 화면을 열 뿐이고 포털 백엔드가 앱 REST 를 대리 호출하지도 않는다(신원이 서비스 계정으로 뭉개짐).
- 앱이 사용자 대신 포털 PAT 를 발급하지 않는다(발급 API 부재). 앱은 `GW_TOKEN·X-Heax-Gateway-Secret·kr_·rat_` 토큰을 보유하지 않고, `X-Heax-User-*` 헤더를 신원으로 믿지 않는다.
- HEAXHub·게이트웨이 코드를 수정하지 않는다(매니페스트 1건 등록만). HEAX 선택 additive 2건(콜백 `next`·service 모드 copy_identity)은 §10 결정 전까지 미채택이다.

## 1.6 헌법 준수(설계에 박힌 형태)

| 헌법 | 이 계획에서의 구현 |
|---|---|
| 브리프에 결론 금지·원천만 | summary_text 판단어 린터(§3), prior_evidence E0~E9 원문·출처 태그·'검증 대상' 프레이밍(§5), RecallPreview 는 항목 제외만 가능·추가 불가(§8) |
| 지정 반대석으로 거수기 방지 | `_CHAIR_ADVERSARY["risk-review"]='delib-baseline-defender'` 합성 push, 기각률 10~40% 정상 밴드·`adversary_silent/overreject` 플래그(§6) |
| 산출은 결정 문서 | 결정문 산문 + ```json risk_spec 펜스(§4), parse_risk_spec 은 P0 산출물 |
| 두 엔진 파리티 | `CHAIR_ITEMS·CHAIR_ADVERSARY·RISK_SEAT_CONTRACT·제목` 바이트 동일(`check_chair_parity.py`), 파서·병합·저장은 앱 단일 구현(`backend/app/narrative.py`), MCP 경로는 `/panels/{id}/complete` 로 되돌림(§8) |
| 애매동사 금지 | 각 절이 '사람 실행' 과 '코드 실행' 을 표로 구분한다(§2.10, §2.13, §6.7) |
| 메타 순수 리터럴 | whenToUse·CHAIR_ITEMS 문자열 연결 금지(§8) |
| 기존 기능 무손상 | 자산은 별도 HEAX 앱 `hwax_risk` 에 격리(전용 DB `$HEAX_DATA_DIR/risk_review.db`·자기 프로세스·자기 SIF) — 포털 백엔드에 라우터·sqlite·플래그를 넣지 않는다. 포털 변경은 `systems.yaml` 타일 1건 + 프론트 additive 3파일 + 백엔드 additive 2줄(§0.4.2), 엔진 변경은 additive 목록(§8.4)·`_FREE_ALLOW` 전역 무수정, HEAXHub 는 매니페스트 1건, 게이트웨이는 변경 0(자동 흡수). 기존 6 라우트·4 NavLink·`/agent/chat` 계약·다른 HEAX 앱의 app_data 는 손대지 않는다 |
| 사람 게이트 | same-as confirm/reject(§2.6), 계면 원장(§2.10), verdict_final(§4), 패턴 승격(§7), 'StepForge 에 반영' 버튼(§2.10) |

---

# §2 설계 IR(rr_ir)

## 2.1 원칙(구현자 계약)

1. 정본은 하나다. `rr_ir` JSON(ir_version '1.0', ECAD 편입 시 '1.1')만 어댑터가 쓰고 diff·state·render·브리프·MCP 도구가 읽는다. 소스 앱 이름은 `sources[].kind` 와 `app_key` 로만 등장하고 코드 어디에도 앱명을 하드코딩하지 않는다(`adapters/registry.py` 가 게이트웨이에서 발견).
2. 스냅샷은 불변이다. 재추출은 새 `snapshot_id` 를 만들되 같은 `(project_id, ir_hash)` 는 UNIQUE 라 기존 행을 반환한다. 어떤 코드도 `rr_snapshots.ir_json` 을 UPDATE 하지 않는다.
3. 모든 수치는 단위를 동반한다. 길이 mm·면적 mm2·부피 mm3·응력 MPa·가속도 G. 밀도는 파일 원문 값과 `density_unit` 문자열을 그대로 보존하고 환산하지 않는다.
4. `null` 은 미측정이지 0 이 아니다. 어떤 집계·해시·거리 계산도 null 을 0 으로 치환하지 않고 `known` 플래그로 마스킹한다.
5. IR 의 어느 필드에도 평가어가 없다. `warnings[].message` 는 소스 원문(StepForge note 등)을 축어로 담고, IR 빌더가 만드는 message 는 render.py 의 판단어 린터를 통과해야 한다.
6. 소스 앱에는 읽기만 한다. 어댑터는 REST GET·MCP 읽기 도구만 호출하고, 쓰기 행위(StepForge parse/detect/set_interface, DynaForge run_operation)는 화면 버튼으로 사람이 실행한 뒤 그 결과를 다시 읽는다.
7. 사람 확정은 스냅샷 밖 원장(`rr_iface_ledger·rr_sameas·rr_part_keys`)에 두고 스냅샷 생성 시 재적용한다. 소스가 확정을 지워도 앱은 잃지 않는다.
8. 모든 소스 호출은 `rr_snapshot_calls` 에 원문 gzip 으로 남고 `tool:<call_id>` 로 인용된다. 재현성은 코드가 아니라 로그로 증명한다.

## 2.2 스냅샷 봉투(envelope)

```json
{
  "ir_version": "1.0",
  "snapshot_id": "<hex32 — 앱 DB 권위 id>",
  "project_id": "<rr_projects.id>",
  "owner_sub": "<heax email — identity.py /auth/me 되묻기, §5.2.1>",
  "label": "M22 DV1 2026-08-31",
  "captured_at": 1756600000,
  "derived_from": "<같은 과제의 직전 snapshot_id | null>",
  "partial": false,
  "sources": [
    {"kind": "mcad", "app_key": "heax-step_forge", "adapter_version": "1.0", "channel": "rest+mcp",
     "ref": {"stepforge_project_id": "001a02ba21cd51064a68c35", "project_name": "sif-e2e",
             "detect_job_id": "01J…", "detect_finished_at": 1756590000,
             "step_files": [{"relpath": "a_stack.step", "sha256": "…", "header_unit": "millimetre", "schema_ap": "AUTOMOTIVE_DESIGN"}]},
     "source_hash": "<sha256(sorted step sha256 + tol_config_hash + detect_job_id)>",
     "tol_config_hash": "<sha256(TolConfig 19키 정렬 JSON) | null>",
     "tol_known_keys": ["tied_gap", "clearance_gap", "tied_area", "tied_width"],
     "scope": null,
     "stats": {"files": 1, "nodes": 6, "leaf_instances": 3, "assemblies": 1, "max_depth": 3, "auto_named_nodes": 0, "interfaces": 2, "orphans": 0},
     "degraded": [], "captured_at": 1756600000},
    {"kind": "dyna", "app_key": "heax-kooremapper_mcp", "adapter_version": "1.0", "channel": "mcp",
     "ref": {"session_id": "01J…", "file_id": "01J…", "filename": "assembled_tied.k", "sha256": "…", "origin_job_id": null,
             "modelmeta_detect": false, "detect_result_file_id": null, "includes": []},
     "source_hash": "<K파일 sha256>",
     "stats": {"nodes": 12000, "elements": 9800, "parts": 3, "bbox_min": [0,0,0], "bbox_max": [50,50,3.2], "size": [50,50,3.2],
               "keyword_counts": {"*PART": 3, "*SECTION_SOLID": 1, "*CONTACT_TIED_SURFACE_TO_SURFACE": 1},
               "contacts_total": 1, "unresolved_sides": 0, "edges_truncated": false, "truncated_scan": false},
     "conventions": {},
     "context": {"corpus_usage": {"materials": [], "sections": [], "contacts": [], "fetched_at": 1756600000}},
     "degraded": ["no_secid"], "captured_at": 1756600000},
    {"kind": "dyna_result", "app_key": "heax-kooremapper_mcp", "adapter_version": "1.0", "channel": "mcp",
     "ref": {"report_ids": ["01J…"], "report_kind": "sphere", "session_id": "01J…"},
     "source_hash": "<sorted report_ids 의 sha256>",
     "binding": {"bound_to_dyna_source_hash": "<K파일 sha256>", "method": "user_declared"},
     "degraded": [], "captured_at": 1756600000},
    {"kind": "ecad", "app_key": null, "adapter_version": "0.0-stub", "channel": null, "ref": {}, "source_hash": null,
     "degraded": ["ecad_absent"], "captured_at": null}
  ],
  "units": {"length": "mm", "area": "mm2", "volume": "mm3", "stress": "MPa", "accel": "G", "density": "as_in_file"},
  "nodes": [], "edges": [], "same_as": [], "dims_named": [],
  "rollups": {"by_assembly": []},
  "results": null,
  "missing": {"ecad_absent": true, "dyna_absent": false, "dyna_result_absent": false, "result_kind_mismatch": false,
              "world_transform_absent": false, "volume_null": false, "material_density_unsourced": true},
  "warnings": [{"severity": "WARNING", "code": "auto_named", "message": "<소스 원문>", "ref": "a_stack.step#P3_a_stack", "source_kind": "mcad"}],
  "gates": {}, "character_seed": [], "feature_vector": {},
  "ir_hash": "<sha256>",
  "versions": {"ir_version": "1.0", "adapter_versions": {"mcad": "1.0", "dyna": "1.0", "dyna_result": "1.0", "ecad": "0.0-stub"},
               "taxonomy_version": "1.0", "seed_rules_version": "1.0", "vocab_version": "1.0"}
}
```

`sources[]` 항목 규칙.

| 필드 | 규칙 |
|---|---|
| kind | `mcad · dyna · dyna_result · ecad` 4종. 한 스냅샷에 kind 당 최대 1건(dyna_result 는 report_ids 배열로 여러 리포트를 담되 kind 는 같아야 한다). |
| channel | `rest+mcp · mcp · rest · null`. REST 원문을 못 읽어 MCP 만 쓴 mcad 는 `degraded` 에 `mcp_degraded` 를 넣고 world_transform·노드 id 가 없는 채로 진행한다. |
| source_hash | mcad = sha256(정렬한 step sha256 목록 + tol_config_hash + detect_job_id). dyna = SessionFile.sha256. dyna_result = sha256(정렬한 report_ids). ecad = 어댑터가 낸 `source_hash`(계약 §2.13). |
| tol_config_hash | projects.tol_config(REST GET 가능 시)와 detect 잡 params 4키(tied_gap·clearance_gap·tied_area·tied_width)를 합쳐 TolConfig 19키 기본값 위에 덮어쓴 뒤 키 정렬 JSON sha256. 둘 다 못 읽으면 null 이고 `degraded: tol_config_unknown`. `tol_known_keys` 에 실제로 읽은 키를 남긴다. |
| scope | detect 잡 params.scope 또는 graph.json.scope 가 있으면 그대로 복사한다. non-null 이면 봉투 `partial=true`(G5). |
| stats | 카운트만 담는다. ir_hash 계산에서 제외한다. |
| context | dyna 의 전사 집계(material_usage·section_contact_usage·corpus_summary 원문 발췌)를 담는다. 파일·세션·소유자를 담지 않는 조직 분포이므로 노드 필드가 아니라 봉투 문맥이고 ir_hash 에서 제외한다(§3 signals 의 '조직 관행 대비' 재료). |
| binding | dyna_result 전용. `method ∈ user_declared \| same_session_weak`. 사용자가 K파일을 지정하면 user_declared, 지정하지 않았고 리포트 session_id 가 dyna 소스 session_id 와 같으면 same_session_weak, 둘 다 아니면 dyna_result 를 싣지 않고 `missing.dyna_result_absent=true`. |
| degraded | 어댑터가 채우는 문자열 코드. `mcp_degraded · no_world_transform · no_node_id · volume_null_pre_d168 · tol_config_unknown · interfaces_truncated · no_secid · truncated_scan · edges_truncated · detect_absent · ecad_absent · report_parts_mismatch`. |

`missing` 플래그의 의미와 산출 규칙.

| 플래그 | true 조건 |
|---|---|
| ecad_absent | ecad 소스가 없거나 어댑터 4도구가 게이트웨이에 없다. |
| dyna_absent | dyna 소스가 없다(러너 자격 (b) 소유자 포털 PAT 부재 포함 — §0.1.6). |
| dyna_result_absent | dyna 는 있으나 결속된 리포트가 없다. |
| result_kind_mismatch | 지정한 report_ids 의 kind 가 서로 다르다. 이때 `results=null`. |
| world_transform_absent | mcad 가 REST tree.json 을 못 읽어 `bbox_world·centroid_world` 가 전부 null. |
| volume_null | mcad 리프 파트의 volume 이 전부 null(D-168 이전 파싱). 화면은 'parse 잡 재실행 필요(사용자 실행)' 를 안내한다. |
| material_density_unsourced | mcad 노드 중 `attrs.density` 가 있으나 `density_unit` 이 없거나, dyna `material.db` 가 null 인 노드가 1개 이상. |

## 2.3 노드(Node)

| 필드 | 타입 | 규칙 |
|---|---|---|
| nid | str | `'p:' + sha1(canon_key)[:12]`. 재파싱으로 StepForge `n{seq}` 가 바뀌어도 불변. |
| canon_key | str | mcad `'mcad:' + path(프로젝트명 접두 제거, 예 `/a_stack.step/STACK_ASM/PLATE_1`)`. dyna `'dyna:' + sha256[:8] + ':' + pid`(sha256 은 K파일). dyna 가상 접촉 노드 `'dyna:' + sha256[:8] + ':contact:' + contact_index`. ecad `'ecad:' + refdes`, 넷 `'ecad:net:' + net_name`, 레이어 `'ecad:layer:' + idx`. |
| domain | enum | `mcad \| dyna \| ecad`. dyna_result 는 노드를 만들지 않고 dyna 노드의 `results` 오버레이로만 존재한다. |
| kind | enum | `part \| assembly \| file \| pid \| contact_set \| component \| net \| layer`. mcad 리프 인스턴스(shape_def 보유)가 `part`, XCAF assembly 가 `assembly`, step-file 노드가 `file`. project-root·file-group 은 만들지 않는다. |
| label | str | 소스 표시명 원문(mcad name, dyna title, ecad refdes). |
| local_key | str | 소스 고유키 원문(mcad path 전체, dyna pid 정수 문자열, ecad refdes). |
| name_norm | str | §2.7.1 규칙으로 정규화한 표시명. |
| name_norm_canon | str | name_norm 에 `rr_dim_vocab` 과 같은 사전·정규식을 적용한 과제 무관 정규명(§2.7.1). ckey 계산 입력. |
| group | str/null | dyna 는 리포트 파서 `_group_of` 규칙(`\` 또는 `/` 앞부분, 없으면 `Other`)을 K파일 title 에 재적용한 값. mcad 는 부모 assembly 의 name_norm. ecad 는 side(top/bottom). |
| ckey | str/null | §2.7.3 canonical_part_key. same-as 클러스터 conflict 이면 null. |
| dn | str | 대표 nid(§2.7.5). 미결이면 자기 nid. |
| parent_nid | str/null | mcad 하이라키 부모(part_of 엣지와 중복 보관 — 롤업 편의). dyna·ecad 는 null. |
| asm_key | str/null | §2.7.4. mcad 만. |
| attrs | obj | 도메인별 typed dict(아래). |
| geom_fp | str/null | §2.7.2 기하 지문. 기하가 없으면 null. |
| status_flags | list | `auto_named \| duplicate_name \| missing_geometry \| construction_only \| multi_solid \| volume_null \| shell_volume_zero \| scope_out`. |
| provenance | obj | `{adapter, app_key, tool: "REST /tree" \| "list_parts" \| "inspect_file" \| …, call_id, node_id_at_capture: "n12"(참고용), captured_at}`. ir_hash 제외. |

attrs — mcad `part`(assembly·file 은 `{depth, relpath, sha256?}` 만).

```
{shape_kind: solid|shell|face|compound|compsolid|other,
 bbox_def[6], size_def[3](= bbox_def 치수, 정렬 전), size_sorted[3](내림차순),
 bbox_world[6]|null, centroid_def[3]|null, centroid_world[3]|null,
 volume|null, area|null, min_dim(= min(size_def))|null,
 material|null, density|null, density_unit|null, color|null,
 instance_count, has_geometry, depth, solid_count|null, construction_only|null,
 shape_def_id(참고), step_file(relpath), xcaf_entry(참고, 키 금지)}
```

`bbox_world` 는 tree.json `nodes[].world_transform`(4x4 row-major) 을 `bbox_def` 8꼭짓점에 적용해 재계산한 축정렬 bbox 이고, `centroid_world` 는 같은 변환을 `centroid_def` 에 적용한 값이다. world_transform 이 없으면 둘 다 null 이고 `missing.world_transform_absent` 가 선다. `bbox_def·centroid_def` 는 정의 좌표계(배치 전) 값이라 위치 비교에 쓰지 않고 지문(geom_fp)에만 쓴다.

attrs — dyna `pid`.

```
{title, elem_class: solid|shell|mixed, n_elems,
 bbox_min[3], bbox_max[3], size[3], size_sorted[3], area_ext, volume|null, proj{x,y,z},
 material: {mid, keyword|null, name|null, E|null, nu|null, rho|null, sigy|null,
            db: null | {match_basis: name-mat|name-part|mid, db_mid, name, tag, category, mat_type, E_GPa, rho_g_cm3, PR}},
 secid: null, section_hint: {has_section_shell: bool, has_section_solid: bool}(keyword_counts 에서),
 bridge: null | {source_path, worked_name, mesh_key, mesh_status}(part_mesh 표 동결분)}
```

dyna `volume` 은 shell 파트에서 modelmeta 가 0 을 내므로 `elem_class=shell AND volume==0` 이면 null 로 저장하고 `status_flags` 에 `shell_volume_zero` 를 넣는다(null≠0 원칙). `secid` 는 modelmeta 가 내지 않으므로 항상 null 이고 `degraded: no_secid` 로 명시한다. dyna 의 bbox 는 모델 좌표계 축정렬이라 회전하면 어긋나므로 지문은 size_sorted 와 volume 으로만 만든다.

attrs — dyna `contact_set`(single_surface 하이퍼엣지의 가상 노드).

```
{contact_index, contact_type: "*CONTACT_AUTOMATIC_SINGLE_SURFACE", title, n_members}
```

attrs — ecad(계약 §2.13.5, 스텁).

```
component: {refdes, part_number|null, footprint|null, side: top|bottom, x, y, rot, pin_count, nets[], height|null, value|null}
net:       {net_name, pin_count, layers[], net_class|null}
layer:     {idx, name, type: signal|plane|dielectric|soldermask|silkscreen, thickness|null, material|null, copper_weight|null}
```

## 2.4 엣지(Edge)

| 필드 | 타입 | 규칙 |
|---|---|---|
| eid | str | `'e:' + sha1(kind_family + '|' + sorted(nid_a, nid_b).join('|'))[:12]`. 방향 kind(`part_of·load_path·net`)는 정렬하지 않고 `a + '|' + b` 그대로. kind 가 tied→touching 으로 바뀌어도 eid 는 같아 diff 가 `kind_changed` 로 잡는다. |
| kind | enum | `tied \| touching \| clearance \| interference`(mcad 검출) · `geometric`(dyna detect=true 근접) · `contact`(dyna *CONTACT 쌍) · `scope`(dyna single_surface, 가상 노드 → 멤버) · `bridge`(mcad↔dyna 메시 계보, same_as 와 별도) · `part_of`(하이라키) · `load_path`(dyna_result energy_flow.edges) · `net`(ecad 컴포넌트→넷). |
| kind_family | enum | `iface`(tied·touching·clearance·interference·geometric) · `contact`(contact·scope) · `hier`(part_of) · `bridge` · `load_path` · `net`. |
| a, b | str | 노드 nid. `scope` 는 a = contact_set nid, b = null, `members[]` 에 pid nid 목록. |
| members | list | scope 전용. |
| domain | enum | `mcad \| dyna \| dyna_result \| ecad \| cross`(bridge). |
| status | enum | `auto \| confirmed \| manual \| manual_ledger \| rejected`. 소스 값(auto·confirmed·manual) 위에 원장 재적용 결과(`manual_ledger·rejected`)가 덮는다(§2.10). `rejected` 엣지는 IR 에 남되 rollups·orphan 계산·diff 구조층에서 제외한다. |
| attrs | obj | 아래. |
| provenance | obj | 노드와 같고 `detected_at|null`, `params_hash(=tol_config_hash)` 추가. ir_hash 제외. |

attrs — mcad 계면(`iface` family).

```
{min_gap, contact_area_est(공차 밴드 면적 — 접촉면적 아님), band_width, normal_align|null,
 penetration_depth|null, penetration_depth_is_lower_bound: bool(부울 경로가 아니면 true),
 penetration_volume|null(부울 경로에서만), cross_file: bool, face_pairs_count|null,
 note(소스 원문 한국어 문장), tol_config_hash|null}
```

attrs — dyna `contact` `{contact_index, contact_type, title, fs|null}` · `scope` `{contact_index, contact_type, title}` · `geometric` `{gap_min, gap_avg, pairs}` · `bridge` `{pid, worked_name, mesh_key, mesh_status, bridge_stale: bool}` · `part_of` `{depth_delta: 1}` · `load_path` `{report_id, case_key, name, peak_force, total_work, confidence}` · `net` `{pin|null}`.

kind 강도 순위(diff 의 coupling 방향 판정용, StepForge `compare_interfaces` 규약 그대로) — `interference:3 > tied:2 > touching:1 > clearance:0`. `geometric` 은 touching 과 같은 1 로 둔다.

## 2.5 소스 매핑표 3

각 표는 "소스 필드 → rr_ir 필드" 이고 세 번째 열이 손실·주의다. 어댑터 코드(`adapters/mcad.py·dyna.py·ecad_stub.py`)는 이 표 밖의 필드를 만들지 않는다.

### 2.5.1 StepForge → rr_ir(mcad)

| 소스 필드(채널) | rr_ir 필드 | 손실·주의 |
|---|---|---|
| tree.json `project`(REST `/tree`) | `sources[mcad].ref.project_name`, canon_key 의 접두 제거에 사용 | path 는 `/{project}/…` 로 시작하므로 반드시 제거한다. |
| tree.json `unit_system` | G6 입력(`units.length` 와 대조) | 'mm' 외 값이면 G6 fail. |
| tree.json `files[].{relpath, sha256, size_bytes, schema_ap, header_unit}` | `sources[mcad].ref.step_files[]`, source_hash 입력 | header_unit 이 millimetre 가 아니면 warnings `unit_mismatch` 와 함께 G6 입력. |
| tree.json `nodes[].{id, parent_id, kind, name, path, depth, seq, shape_def_id, transform, world_transform, auto_named, color}` | kind `assembly\|file\|part` 노드, `parent_nid`, `attrs.depth`, `bbox_world·centroid_world`(world_transform 적용), `status_flags.auto_named`, `provenance.node_id_at_capture` | project-root·file-group 은 노드로 만들지 않는다. `instance` 중 shape_def_id 가 없는 것은 노드로 만들지 않고 warnings `missing_geometry` 로 남긴다. |
| tree.json `shape_defs{id}.{kind, bbox, volume, area, centroid, material, density, density_unit, instance_count, has_geometry, solid_count, construction_only, xcaf_entry, step_file}` | `attrs.mcad.*` | bbox·centroid 는 정의 좌표계. xcaf_entry 는 참고 필드이며 키로 쓰지 않는다. |
| tree.json `summary` | `sources[mcad].stats` | ir_hash 제외. |
| tree.json `warnings[]{severity, code, message, ref}` | `warnings[]`(+`source_kind='mcad'`) | 코드 목록 `file_load_failed·not_a_step·unit_mismatch·materials_found·empty_tree·construction_geometry·missing_geometry·multi_solid_leaf·auto_named·empty_geometry_summary·duplicate_names·suspect_coordinate_systems·files_all_overlap` 을 그대로 보존한다. `orphan_parts` 는 tree.json 에 남지 않으므로 graph.json orphans 로 대체한다. |
| REST `/parts`(`id, shape_def_id` 포함) | 노드 id ↔ path 해석 표(`provenance.node_id_at_capture`) | MCP list_parts 는 노드 id 를 내지 않는다. |
| MCP `list_parts`(limit ≤500, name_like) | REST 불가 시 폴백으로 같은 attrs 채움, `degraded: mcp_degraded·no_node_id·no_world_transform` | volume/area/centroid/material 이 전부 null 이면 `degraded: volume_null_pre_d168`, `missing.volume_null=true`. |
| MCP `list_interfaces`(kind 필터, limit ≤500) `{node_a, node_b, name_a, name_b, kind, min_gap, contact_area_est, band_width, penetration_depth, penetration_volume, cross_file, status, note}` | kind `tied\|touching\|clearance\|interference` 엣지, `attrs` 전부, `status` | node_a/b 는 `n{seq}` 이므로 REST /parts 표로 path→nid 를 푼다(MCP 만이면 name_a/name_b 로 풀되 동명이면 `warnings: ambiguous_edge_endpoint` 후 엣지 제외). kind 4종을 각각 호출해 최대 2000행, 초과분은 `degraded: interfaces_truncated`. normal_align·face_pairs·params·detected_at 은 MCP·REST 모두 내지 않으므로 `normal_align=null`, `face_pairs_count=null`, `detected_at=null`. |
| REST `/artifacts/graph/`(graph.json) `nodes[]{id, name, path, shape_def, degree}`, `edges[]`, `orphans[]`, `counts`, `scope?` | 리프 정점 id→path 해석(REST /parts 대체), `counts` 로 엣지 수 검증, `orphans` → rollups.orphan_leaf, `scope` → `sources[mcad].scope`(G5) | graph.json edges 는 attrs 가 적어 위상 검증에만 쓴다. |
| MCP `interface_graph(fmt=json)` `{counts, orphans, edges[:limit]}` | 검증용(counts 일치 확인) | nodes 를 내지 않으므로 정점 해석에 쓰지 않는다. |
| MCP `job_status(detect_job_id)` `{status, params{tied_gap, clearance_gap, tied_area, tied_width, scope}, finished_at}` | `sources[mcad].ref.detect_job_id·detect_finished_at`, tol_config_hash 입력, `scope` | `status != done` 이면 캡처를 중단하고 `409 detect_not_done` 을 낸다(자동 재실행 금지). |
| REST `GET /projects/{id}`(`tol_config`, 있을 때) | tol_config_hash 입력 | 없으면 잡 params 4키만으로 계산하고 `tol_known_keys` 에 기록. |
| MCP `part_mesh_map` `{source_path, worked_name, mesh_key, kind, status, pid, …}` | kind `bridge` 엣지(mcad part ↔ dyna pid), `attrs.dyna.bridge`, same-as `pid_map` 단계 입력 | pid 는 메시 실행마다 재부여될 수 있으므로 표를 스냅샷에 동결하고 K파일 sha256 과 잡 계보가 다르면 `bridge_stale=true`. |
| MCP `mesh_report` `worked_interfaces·interface_diff` | `sources[mcad].stats.mesh_report`(참고) | IR 엣지로 만들지 않는다. 해석 접촉 IR 은 dyna 소스가 정본이다. |
| MCP `inspect_report` `worst_interference[10]` | 검증용 | 엣지 attrs 와 대조해 불일치면 `warnings: source_inconsistent`. |
| MCP `mass_estimate·get_part_rules·render_3d·view_3d` | 사용 안 함(좌석 자유조회 도구로만) | — |

### 2.5.2 DynaForge → rr_ir(dyna·dyna_result)

| 소스 필드(채널) | rr_ir 필드 | 손실·주의 |
|---|---|---|
| `inspect_file(session_id, file_id)` → `meta.{nodes, elements, parts, bbox_min, bbox_max, size, valid}` | `sources[dyna].stats`, G6 입력(모델 bbox 크기) | valid=false 면 캡처 중단 `409 kfile_invalid`. |
| `meta.includes[]` | `sources[dyna].ref.includes` | *INCLUDE 는 1단계만 추적된 결과다. |
| `meta.part_titles[≤50]` | 사용 안 함 | 50개 절단·8MB 스캔 한계. modelmeta.parts 가 정본. |
| `meta.keyword_counts{'*KEYWORD': n}` | `sources[dyna].stats.keyword_counts`, `attrs.section_hint`, §3 signals(BC·초기속도·하중 카드 존재 힌트) | 파트별 정보가 아니다. ir_hash 제외. |
| `meta.truncated_scan` | `degraded: truncated_scan` | — |
| `meta.modelmeta.parts[]{pid, title, elem_class, n_elems, bbox_min, bbox_max, area_ext, volume, proj, material{mid, kfile{keyword, name, E, nu, rho, sigy}, db{…}}}` | kind `pid` 노드, `label=title`, `group=_group_of(title)`, `attrs.dyna.*` | shell volume 0 → null(`shell_volume_zero`). secid 없음(`no_secid`). |
| `meta.modelmeta.connectivity.contact_edges[]{a, b, a_title, b_title, contact, type, title, fs}` | kind `contact` 엣지 `attrs{contact_index=contact, contact_type=type, title, fs}` | SET_PART/SET_NODE/SET_SEGMENT → PID 환원은 modelmeta 가 이미 했으므로 재파싱하지 않는다. |
| `connectivity.single_surface[]{contact, type, title, pids[]}` | kind `contact_set` 가상 노드 + kind `scope` 하이퍼엣지 `members=pids→nid` | STYP 5(전 파트)면 members 는 전체 pid 이고 §3 signal `single_surface_global` 입력. |
| `connectivity.geometric_edges[]{a, b, gap_min, gap_avg, pairs}` | kind `geometric` 엣지 | detect=true 산출을 사용자가 `run_operation('modelmeta', {detect:true})` 를 실행한 뒤 `download_result` 로 받아 어댑터에 넘긴 경우에만 존재(`ref.modelmeta_detect=true, detect_result_file_id`). 없으면 `degraded: detect_absent`. |
| `connectivity.{contacts_total, unresolved_sides, edges_truncated}` | `sources[dyna].stats`, `edges_truncated` → `degraded` | unresolved_sides > 0 이면 warnings `contact_side_unresolved`. |
| `meta.modelmeta.conventions` | `sources[dyna].conventions` | ir_hash 제외. |
| `list_session_files` → `SessionFile{id, filename, sha256, kind, origin_job_id, created_at}` | `sources[dyna].ref`, canon_key 접두 `sha256[:8]`, source_hash | 파일은 불변이므로 sha256 이 곧 버전이다. |
| `material_usage · section_contact_usage · corpus_summary`(전사 집계) | `sources[dyna].context.corpus_usage` | 파일·세션·소유자 무관 조직 분포. 노드·엣지 필드가 아니고 ir_hash 제외. §3 signals 의 '조직 관행 대비' 와 character_seed 입력으로만 쓴다. |
| `report_summary(report_id)` → `ReportRead{id, kind, label, project_name, test_dir, doe_strategy, sim_params, parts[{part_id, name, group}], findings[], summary, n_cases}` | `results.{report_ids, kind, summary, sim_params_hash}`, `results.parts_map[pid→nid]` | `sim_params_hash = sha256(kind, unit_system, drop_height, impactor.mass, impactor.velocity, yield_stress)`(없는 키는 null 로 직렬화). `parts[].name` 의 name_norm 이 같은 pid 의 K파일 title name_norm 과 다르면 warnings `report_parts_mismatch`(결속 의심). |
| `report_part_risk(report_id)` → `parts[{part_id, part_name, worst_stress{value, case_key}, worst_g, worst_disp, min_safety_factor}]` | `results.part_risk[]{nid, pid, worst_stress, worst_g, worst_disp, min_safety_factor}` | sphere/impact 는 min_safety_factor 가 항상 null 이다. null 을 '안전' 으로 읽지 않는다. |
| `report_findings(report_id)` → `[{severity, title, detail, recommendation}]` | `results.findings[]` 원문 보존 | 정성 소견 씨앗(§4). deep 은 항상 []. |
| `report_energy_flow(report_id, case)` → `energy_flow.edges[{src, dst, name, peak_force, total_work, confidence}]`, `nodes[]`, `propagation_order` | kind `load_path` 엣지(`domain='dyna_result'`), `results.energy_edges`(원문) | src/dst 가 pid 인지 P2 픽스처로 확정한 뒤 nid 로 사상한다. deep 은 edges 가 없고 `contacts[{name, peak_fmag}]` 만 있어 load_path 를 만들지 않는다. |
| `report_worst_cases(report_id, metric, limit=5)` | `results.worst_cases[≤5]{case_key, identity, max_stress, max_g, max_disp, min_safety_factor}` | — |
| `report_case · report_directional · report_scatter · report_part_series · report_corpus` | IR 에 넣지 않음 | 좌석 자유조회 도구로만 쓴다. |
| `compare_reports` | IR 에 넣지 않음 | §3 결과층 diff 가 ckey 치환 후 같은 조인을 앱(`diff.py`)에서 수행한다(엔진 무수정). |
| `publish_report_to_datahub` 의 `eng_meta{project, dev_revision{phase, round}, design_variation}` | `rr_projects.stage` 규약 참조(정규식 `(pre\|dv\|pv\|pra\|mp)([123r])?`) | 호출하지 않는다(쓰기). 규약만 채택. |

### 2.5.3 ODB hub 어댑터 계약 → rr_ir(ecad, ir_version '1.1')

계약 정본은 앱 리포 `HWAXRisk/docs/odb-adapter-contract.md`(어댑터 코드 `adapters/ecad_stub.py`·`ecad.py` 와 같은 리포, 실존 — 포털 `docs/design-risk-review/` 에는 사본을 두지 않는다)이고 아래가 그 필드 표다. ODB hub 가 이 4도구를 게이트웨이 manifest `mcp:{}` 로 노출하면 `adapters/registry.py` 가 발견하고 `ecad_stub.py` 가 `ecad.py`(P7)로 교체된다. 그 전까지 스냅샷은 `missing.ecad_absent=true` 다.

| 도구(인자) | 응답 필드 | rr_ir 필드 | 상한·주의 |
|---|---|---|---|
| `odb_get_board(job_ref)` | `{board_id, name, units: mm\|mil, outline_bbox[4], thickness, layer_count, n_components, n_nets, odb_version, source_hash}` | `sources[ecad].ref.{board_id, name}`, `source_hash`, G6 입력(units 가 mil 이면 어댑터가 mm 로 환산하고 `degraded: unit_converted_mil`) | 보드 1장 = 소스 1건. |
| `odb_list_components(job_ref, side?, offset, limit)` | `items[{refdes, part_number, footprint, side, x, y, rot, pin_count, nets[], height, value}]`, `total`, `next_offset` | kind `component` 노드, `attrs.ecad.component`, kind `net` 엣지(component→net, pin 당 1건 아니라 넷 당 1건) | limit ≤2000/호출, 총 상한 2000(초과 시 `degraded: components_truncated`). x·y 는 보드 원점 기준 mm. |
| `odb_list_nets(job_ref, offset, limit)` | `items[{net_name, pin_count, layers[], net_class}]`, `total`, `next_offset` | kind `net` 노드 | 총 상한 5000(`degraded: nets_truncated`). |
| `odb_get_stackup(job_ref)` | `layers[{idx, name, type, thickness, material, copper_weight}]` | kind `layer` 노드, `dims_named` 자동 후보 `ecad_stackup_total`(두께 합, §2.8 시드 예약 이름) | type 어휘는 §2.3 attrs 의 5종으로 고정. |

계약 조건. (1) 4도구 전부 읽기 전용이고 `job_ref` 는 ODB hub 가 발급한 불투명 문자열이다. (2) 인증은 게이트웨이 PAT 전달 규약(DynaForge 와 같음)을 따른다. (3) 응답은 JSON 이고 좌표·두께 단위는 `odb_get_board.units` 로 선언한다. (4) ecad↔mcad/dyna same-as 는 1차에서 `ledger·title_norm/name_norm(refdes 또는 part_number 토큰)` 만 허용하고 기하 지문(footprint bbox ↔ mcad part bbox)은 계약 이행 후 P7 에서 켠다. (5) 계약 밖 필드(패드·비아·트레이스 폭)는 이 버전에서 가정하지 않는다.

## 2.6 크로스도메인 same-as 사다리

같은 물리 부품을 가리키는 두 노드의 대응은 스냅샷 내부(mcad↔dyna↔ecad, `scope='intra'`)와 스냅샷 간(base↔target, `scope='pair'`, §3 의 correspondence)에 **같은 함수** `sameas.resolve(nodes_a, nodes_b, edges_a, edges_b, scope, ledger)` 를 쓴다. 순서는 고정이고 앞 단계에서 확정된 노드는 뒤 단계 후보에서 빠진다.

### 2.6.1 레코드

```json
{"id": "sa:<hex12>", "scope": "intra|pair", "a": "<nid>", "b": "<nid>",
 "method": "ledger|pid_map|exact_path|fingerprint|name_norm|fuzzy|manual",
 "score": 0.93, "status": "auto|pending|confirmed|rejected",
 "evidence": {"name_sim": 1.0, "geom_sim": 0.98, "material_eq": 1.0, "neighbor_sim": 0.8,
              "bridge": {"mesh_key": "…", "stale": false}, "rank_in_row": 1, "n_candidates": 3},
 "decided_by": null, "decided_at": null, "ledger_id": null}
```

`status` 규칙. `ledger` 결과는 `confirmed`(또는 `rejected`), 결정론 단계(pid_map·exact_path)와 score ≥ 0.90 인 단계는 `auto`, 0.70 ≤ score < 0.90 은 `pending`(G2 계수), 사람이 확정하면 `confirmed`. `rejected` 는 레코드로 남겨 뒤 단계가 같은 쌍을 다시 제안하지 못하게 한다. ir_hash 에는 `confirmed` 만 들어간다.

### 2.6.2 단계표(순서 고정)

| # | 단계 | 적용 범위 | 조건 | score·status |
|---|---|---|---|---|
| 1 | `ledger` | intra·pair | `rr_sameas` 에 `(scope, a_stable, b_stable)` 행이 있다. stable key = mcad `canon_key`(프로젝트명 제거 path) · dyna `name_norm_canon + '@' + elem_class`(pid·sha 는 K파일마다 바뀌므로 쓰지 않음) · ecad `refdes`. `scope='global'` 행은 ckey 쌍으로 대조한다. | 1.0 · confirmed / rejected |
| 2 | `pid_map` | intra(mcad↔dyna) | `bridge` 엣지(part_mesh 표)가 있고 `bridge_stale=false`. stale 판정은 K파일 filename 이 mesh_report.artifacts.kfile 과 같고 pid 최대값이 part_mesh 행 수 이하일 때 false, 아니면 true. stale 이면 이 단계를 건너뛰고 6단계로 내린다. | 1.0 · auto |
| 3 | `exact_path` | pair(같은 도메인) | mcad `canon_key` 동일, ecad `refdes` 동일. dyna 는 canon_key 에 sha 가 들어 있어 이 단계 대상이 아니다(5단계로). | 1.0 · auto |
| 4 | `fingerprint` | pair(같은 도메인) · intra(mcad↔dyna) | 같은 도메인은 `geom_fp` 동일 AND name_sim ≥ 0.5 → 0.95 auto, `geom_fp` 동일 AND name_sim < 0.5 → 0.85 pending(개명·교체 의심). mcad↔dyna 는 `size_sorted` 3축 상대오차 모두 ≤ 2% AND (둘 다 solid 이면 volume 상대오차 ≤ 3%, 한쪽 volume null 이면 조건 생략 후 0.05 감점) 인 후보가 1:1 이면 0.90 auto, 1:N 이면 6단계로. | 위 표기 |
| 5 | `name_norm` | intra·pair | `name_norm_canon` 완전 일치이고 후보 1:1 → 0.95 auto. 1:N → 6단계. ecad↔mcad/dyna 는 refdes 또는 part_number 토큰이 mcad name_norm_canon 토큰과 일치할 때만 이 단계를 탄다. | 0.95 · auto |
| 6 | `fuzzy` | intra·pair | 남은 노드로 도메인 쌍별 이분 그래프를 만들고 아래 점수로 헝가리안 배정. | ≥0.90 auto · 0.70~0.90 pending · <0.70 미생성 |
| 7 | `manual` | intra·pair | `POST /api/sameas/decide {a, b, decision: confirm\|reject, scope}` → `rr_sameas` 기록. 다음 스냅샷(또는 '재해석 적용')에서 1단계로 흡수된다. | 1.0 · confirmed / rejected |

### 2.6.3 fuzzy 점수와 배정

```
score        = 0.35·name_sim + 0.35·geom_sim + 0.10·material_eq + 0.20·neighbor_sim
name_sim     = max(token_jaccard(canon_a, canon_b), levenshtein_ratio(canon_a, canon_b))       # canon = name_norm_canon, 0..1
geom_sim     = 1 − min(1, Σ|sa_i − sb_i| / Σ sb_i)  (size_sorted 3축)
               둘 다 solid·volume known 이면 0.5·위값 + 0.5·(1 − min(1, |va − vb| / vb))
material_eq  = 1 (토큰 교집합 ≠ ∅) | 0 (둘 다 known 인데 교집합 ∅) | 0.5 (한쪽 null)
neighbor_sim = jaccard(이미 확정된 same_as 로 사상한 이웃 ckey 집합)  (iface·contact family 1홉, 양쪽 이웃 0 이면 0.5)
```

후보 가지치기는 `geom_sim ≥ 0.5 OR name_sim ≥ 0.5` 인 쌍만 비용 행렬에 넣고 나머지는 비용 ∞ 다. 비용 = 1 − score, 미배정 허용을 위해 더미 행·열(비용 0.30 = 1 − 0.70)을 붙인다. 배정은 `scipy.optimize.linear_sum_assignment` 가 있으면 그것, 없으면 동봉한 순수 파이썬 O(n³) 구현(노드 ≤ 500 이라 충분)이다. 동점은 `(score desc, canon_key_a asc, canon_key_b asc)` 로 깨서 같은 입력이면 같은 출력이 나온다. `evidence.rank_in_row·n_candidates` 로 사람이 왜 이 쌍인지 볼 수 있게 한다.

### 2.6.4 클러스터·conflict·사람 게이트

- 클러스터 = `status ∈ {confirmed} ∪ {auto AND score ≥ 0.90}` 인 same_as 의 연결 성분. `pending` 은 성분에 넣지 않는다.
- 한 성분에 같은 도메인 노드가 2개 이상이면 `conflict` 다. 성분 전체의 `ckey=null`, `dn=자기 nid`, warnings `sameas_conflict{ref: nids}` 를 남기고 G2 에 계수한다. 사람이 하나를 reject 하면 풀린다.
- 사람 게이트는 SameAsResolver(§8)에서 `pending`·`conflict`·`auto(fuzzy)` 를 표로 보여주고 confirm/reject 를 모아 `POST /api/sameas/decide` 로 보낸 뒤 '재해석 적용' 버튼이 `rr_snapshot_calls` 원문으로 ir_builder 를 다시 돌려(소스 재호출 없음) 새 스냅샷(`derived_from`=이전)을 만든다. 스냅샷은 바뀌지 않고 새로 생긴다.
- ecad 는 1차에서 1·5·7 단계만 허용한다(§2.5.3 계약 조건 4).

## 2.7 과제 무관 전역 정규 키

gap_21 (2) 의 수정이다. 1차 합성의 ckey 는 base/target 쌍 단위로 부여되어 과제 간 키가 아니었다. 여기서는 아래 키 전부를 **과제 id·nid·pid·path·스냅샷 id 를 입력에 넣지 않고** 계산한다. 그래서 계보가 없는 과제 Z 의 노드가 과제 X 의 노드와 같은 ckey(또는 근접 매치)를 가지면 X 의 finding·별칭·선례가 Z 에서 떠오른다(§5, §7).

### 2.7.1 name_norm · name_norm_canon

`name_norm`(표시명 정규화, §0.1.2) — 소문자 → `#\d+$` 제거 → `auto_named` 이면 `_\d+$` 제거 → Dyna `Group\Name` 은 구분자(`\` 또는 `/`) 뒤만 → `[^a-z0-9]+` → `_` → 양끝 `_` 제거.

`name_norm_canon`(과제 무관 정규명) — name_norm 을 `_` 로 토큰화한 뒤 순서대로 적용한다.

1. 과제 코드 토큰 제거. `rr_projects.code` 전체(소유자 무관, 소문자)와 `rr_dim_vocab.stop_tokens`(예 `rev, ver, new, old, final, tmp, copy`) 에 있는 토큰을 뺀다.
2. 두께·치수 표기 토큰 제거. `^\d+(_\d+)?t$`, `^t\d+(_\d+)?$`, `^\d+(_\d+)?mm$` 에 맞는 토큰을 뺀다(두께는 geom_bucket 이 담는다).
3. 동의어 치환. `rr_dim_vocab.synonyms_json`(과제 무관, `vocab_version`)으로 머리 토큰을 정규어로 바꾼다. 시드 v1 은 `pcb ← board, main_board, mainboard, pba` · `battery ← batt, bat, cell` · `display ← disp, lcd, oled, panel` · `housing ← hsg, case, cover` · `bracket ← brkt, bkt` · `tape ← adhesive, adh, psa` · `screw ← scr, bolt` · `frame ← frm, chassis` · `shield_can ← shield, can, emi_can` · `fpcb ← fpc, flex` 이고 사람이 `rr_dim_vocab` UI 로 늘린다.
4. 남은 토큰을 `_` 로 다시 잇는다. 비면 name_norm 을 그대로 쓴다.

인스턴스 순번(`plate_1` 의 `_1`)은 auto_named 가 아니면 유지한다. 같은 설계 안의 `plate_1·plate_2` 는 다른 부품이고, 과제 간에 이름이 다르게 붙은 같은 부품은 `rr_part_keys` 병합으로 사람이 잇는다.

### 2.7.2 geom_fp(기하 지문)

`geom_fp = sha1(kind, sorted(round(size_def, 2)), round_sig(volume, 3), round_sig(area, 3), round(centroid_def − bbox_def_center, 2))[:16]`. mcad 는 정의 좌표계 값이라 평행이동·회전에 불변이다. dyna 는 `kind=elem_class`, `size_sorted`(모델 축정렬 bbox), `volume`(null 이면 문자열 `na`), `area_ext`, 중심 오프셋 `na` 로 계산하므로 회전에 민감하다(문서화된 한계, 4단계가 size 상대오차로 보강). ecad component 는 `footprint` 문자열과 `pin_count` 로만 만든다(계약 이행 전까지 `null` 허용). 기하가 없으면 null 이다.

### 2.7.3 ckey(canonical_part_key)

```
ckey          = 'ck:' + sha1(name_norm_canon + '|' + geom_bucket + '|' + material_norm)[:12]
geom_bucket   = 'x'.join(str(round(s / 0.5) * 0.5) for s in size_sorted) + '@v' + (str(round(log(volume) / log(1.05))) if volume else '?')
material_norm = mcad attrs.material 의 첫 토큰(동의어 치환 후) | dyna material.db.tag ?? material.db.name ?? material.kfile.name 의 첫 토큰 | ecad part_number 첫 토큰 | 'na'
```

- 계산 입력은 클러스터 대표 `dn`(§2.7.5) 의 attrs 다. 클러스터의 모든 노드가 같은 ckey 를 갖는다. conflict 클러스터는 null 이다.
- `rr_part_keys` 원장을 먼저 탄다. 행 `{ckey PK, status: candidate|confirmed|merged, merged_into, display_name, name_norm_canon, geom_bucket, material_norm, aliases_json[{project_id, domain, label, local_key}], ra_part_entity_id, first_project_id, n_projects, created_by, updated_at}`. 계산된 ckey 가 `merged` 면 `merged_into` 를 따라간 유효 ckey 를 노드에 부여한다(체인 최대 5). 행이 없으면 `status='candidate'` 로 삽입하고 aliases 에 이 과제의 원문 이름·local_key 를 더한다(새 과제면 `n_projects += 1`).
- 사람 조작은 `POST /api/sameas/decide` 의 `decision ∈ merge_key | rename_key | confirm_key | unmerge_key` 로 받는다(`{ckey_from, ckey_into}` / `{ckey, display_name}` / `{ckey}` / `{ckey}`). `unmerge_key` 는 §5.9.2 의 병합 취소(`merged_into=NULL, status='confirmed'`)이며 아래 자동 승계 행에도 적용된다. 병합은 원장에만 쓰고 기존 스냅샷의 ckey 는 바뀌지 않으며, 조회·회수 코드는 항상 유효 ckey(merged_into 해석 후, `resolve_ckey()`)로 조인한다.
- **결정론 대응에 의한 ckey 승계(자동 병합, ir_builder).** pair 스코프 same-as(§2.6.2)가 `method ∈ {ledger, exact_path, pid_map}` 이거나 `method ∈ {fingerprint, name_norm}` 이고 `score ≥ 0.95` 로 base 노드 ↔ target 노드를 이었는데 두 노드의 계산 ckey 가 다르면(두께·부피 변경으로 volume 버킷이 옮겨 간 경우가 전형이다 — 이 기능이 추적하는 `dimension_tuning` 자체가 volume 을 5% 넘게 바꾼다), ir_builder 가 §2.11.3 6단계의 ckey 부여 시점에 `rr_part_keys` 에 `{ckey: <target 계산값>, status: 'merged', merged_into: <base 유효 ckey(resolve_ckey 후)>, decided_by: 'code:pair_correspondence', decided_at: now, merge_evidence_json: {method, score, base_snapshot_id, target_snapshot_id, base_nid, target_nid}}` 를 `INSERT OR IGNORE` 로 자동 삽입하고(그 ckey 에 이미 `confirmed` 행이나 사람이 만든 `merged` 행이 있으면 건드리지 않는다) target 노드에는 유효 ckey(base)를 부여한다. 적용 범위 — 같은 과제 계보(`rr_diffs.pair_kind='same_project_revision'`, 또는 `rr_projects.predecessor_project_id` 체인으로 이어진 두 과제)에서는 기본 켬. `cross_project` 쌍에서는 자동 삽입하지 않고 target 계산 ckey 행의 `aliases_json.merged_candidates[]` 에 `{ckey_into: <base 유효 ckey>, method, score}` 제안만 적어 SameAsResolver 가 '정규 키 병합 제안' 으로 보이고 사람이 `merge_key` 한다. 사람은 언제든 `unmerge_key` 로 되돌릴 수 있고 되돌리면 그 행은 `status='confirmed'` 독립 키가 된다(기존 스냅샷의 노드 ckey 는 불변, 조회는 유효 ckey 재해석). 이 규칙으로 §4.9 의 PROTECT_FILM(min_dim 0.080→0.060, 부피 ≈−25%)·OCA_TOP(+50%)은 DV2 계산 ckey 가 DV1 과 다르더라도 DV1 유효 ckey 를 승계해 subject_key·cluster_key 가 리비전 간 동일하게 유지된다(P2 (11)). 승계는 pair 대응이 있을 때만 일어나므로 신규 파트(unmatched_target)는 여전히 새 ckey 다.
- 근접 매치(계보 없는 과제에서 회수할 때, §5.9.4·§7.3 4단계 'canonical 매치 + geom_fp 근접')의 정의는 `name_norm_canon` 동일 AND `material_norm` 동일 AND size 버킷 3축 각각 ±1 단(0.5 mm) 이내 이며 **volume 버킷은 보지 않는다**(리비전 간 두께·부피 변경이 5% 로그 버킷을 여러 칸 넘기므로 volume 을 조건에 넣으면 §4.9 규모의 변경을 잡지 못한다). 파트 단독 subject(`ck:`)와 계면 양끝 모두에 같은 정의를 쓴다. `rr_part_keys` 의 세 컬럼(`name_norm_canon · geom_bucket · material_norm`)으로 SQL 조인이 되도록 컬럼을 분리해 두고 geom_bucket 의 size 부분과 `@v` 부분은 조회 시 분리 비교한다. 근접 매치 결과는 화면에 '정규 키 병합 제안' 으로 보이고 사람이 merge_key 하기 전에는 별개 키다(E5 에는 `[경로: subject·별칭후보]` 태그로 실린다).
- 버킷 경계 흔들림(0.5 mm·5% 경계 근처 값이 재추출마다 다른 버킷으로 가는 것)은 소스 값이 같으면 라운딩도 같으므로 재현성 문제는 없다. 설계 변경으로 경계를 넘으면 **계산값**은 새 ckey 지만, 위 승계 규칙이 결정론 pair 대응으로 이어진 노드에 base 유효 ckey 를 부여하므로 같은 물리 부품은 리비전 사이에서 키를 유지한다. 대응이 없는 신규 파트만 새 ckey 다. volume 축을 5% 버킷 대신 2배(log2) 버킷으로 완화하거나 geom_bucket 에서 빼고 size 3축 0.5 mm 버킷만 두는 안은 §10 (14c) 결정 항목이다(기본값은 5% 유지 + 자동 승계).
- RA `part` 축 값 = `display_name`(없으면 name_norm_canon), `code = ckey`, 원문 이름들은 `add_object_alias` 로 단다(§5).

### 2.7.4 asm_key

mcad path `/{project}/{relpath}/{asm…}/{name}#n` 에서 프로젝트명을 떼고, 각 세그먼트의 `#\d+$` 를 지운 뒤 name_norm_canon 을 적용해 `/` 로 잇는다. 노드의 `asm_key` 는 부모 체인까지(리프 이름 제외)이고, 롤업 접두는 깊이 1..max 의 모든 접두다. 예 `/a_stack.step/STACK_ASM/PLATE_1` → 노드 asm_key `a_stack/stack_asm`, 접두 `a_stack`, `a_stack/stack_asm`. `rr_iface_alias` 의 사람용 별칭 문자열은 `asm_key/name_norm_canon` 쌍이고 키는 ckey 쌍이다(§5).

### 2.7.5 dn(대표 nid)

클러스터 대표는 `mcad part > dyna pid > ecad component` 순, 같은 도메인이면 `canon_key` 오름차순이다. 미결(클러스터 없음)이면 자기 nid 다. diff 의 노드 대응·rollups·정규 표기의 이름은 dn 의 label 을 쓴다.

### 2.7.6 subject_key(요약)

finding 이 가리키는 주체 키(§4 정의). 파트 `ck:…`, 계면 `ck:A|ck:B`(정렬), 명명 치수 `dim:<name>`, 서브어셈블리 `asm:<asm_key>`(§2.7.4 — 프로젝트명 제거·name_norm_canon 적용한 접두, `rollups.by_assembly.path_prefix` 와 일치하는 것만). 입력이 ckey·vocab 이름·정규화된 asm_key 뿐이라 과제 무관이다(asm_key 는 파일명·어셈블리명이 같은 과제 사이에서만 일치하므로 E5 는 `[경로: subject·asm]` 태그를 병기한다). scope 하이퍼엣지를 가리키는 finding 은 `[e:]` 로 인용하되 subject 는 좌석이 이름 붙인 멤버 ckey ≤ 2 로 적는다(§4).

## 2.8 dims_named(명명 치수)

과제에서 "리스크를 가르는 치수" 로 이름 붙인 값이다. 이름 사전은 과제 무관(`rr_dim_vocab`), 추출 정의는 과제별(`rr_dim_defs`), 값은 스냅샷마다 자동 재평가되어 `rr_ir.dims_named[]` 에 들어가고 ir_hash 에 포함된다.

레코드 `{name, value, unit, method: measured|derived|declared, ref, formula, owner_sub, null_reason}`. `ref` 는 값을 읽은 nid/eid(derived 는 입력 ref 목록), `formula` 는 extractor 문자열 원문, `null_reason ∈ ref_missing | ambiguous | attr_null | scope_out`.

`rr_dim_vocab` 행 `{name PK, unit, kind: overall|thickness|gap|offset|count|param|result|other, description, synonyms_json, stop_tokens(공유), created_by, vocab_version}`. 시드 v1 예약 이름 `overall_x · overall_y · overall_z · total_volume · n_leaf · ecad_stackup_total` 은 모든 과제에 자동 정의된다(`rr_dim_defs.owner_sub='system'`).

`rr_dim_defs` 행 `{project_id, name(FK vocab), extractor, owner_sub, created_at}`. extractor 제한 문법.

| 형식 | 예 | method |
|---|---|---|
| `node[ck=<ckey>].<attr_path>` | `node[ck=ck:3f2a9c1e0b7d].attrs.min_dim` | measured |
| `node[asm=<asm_key>/<name_norm_canon>].<attr_path>` | `node[asm=a_stack/stack_asm/plate_1].attrs.volume` | measured |
| `edge[ck=<ckA>\|<ckB>].<attr_path>` | `edge[ck=ck:…\|ck:…].attrs.min_gap` | measured |
| `edge[name=<A>\|<B>].<attr_path>` | `edge[name=plate_1\|plate_2].attrs.penetration_depth` | measured(다의면 null·ambiguous) |
| `result[ck=<ckey>].<metric>` | `result[ck=ck:…].worst_stress` | measured(results 없으면 null) |
| `overall.bbox_world.<x\|y\|z>` · `overall.volume` · `overall.n_leaf` | — | measured |
| `dim(<name>) <op> dim(<name>)`, op ∈ `+ − * /` | `dim(display_z) - dim(battery_z)` | derived |
| `sum\|min\|max(node[asm=<prefix>*].<attr_path>)` | `sum(node[asm=a_stack/*].attrs.volume)` | derived |
| `const:<value>` | `const:0.35` | declared |

규칙. (1) `ck=` 선택자는 유효 ckey(merged_into 해석)로 푼다. 그래서 치수 정의는 ckey 가 같은 다른 과제로 '치수 정의 복사' 가 가능하다(§8 ProjectPage). (2) ref 가 사라지면 값은 null 이고 `null_reason` 이 남는다. 0 으로 두지 않는다. (3) 단위는 vocab 의 unit 이 정본이고 attr 단위와 다르면 정의 등록 시 `400 unit_mismatch` 다. (4) `POST /api/projects/{id}/dims` 는 정의를 저장만 하고 값은 다음 스냅샷(또는 '재해석 적용')에서 계산된다.

## 2.9 rollups · results · warnings

`rollups.by_assembly[]{path_prefix(asm_key 접두), depth, n_leaf, edges_internal{kind: count}, edges_external{kind: count}, orphan_leaf}`. 접두마다 1행이고 리프 엣지(iface·contact family, status ≠ rejected)를 양끝 노드의 asm_key 로 분류한다. `orphan_leaf` 는 `tied·touching·interference·geometric·contact` 어느 엣지에도 끼지 않는 리프 수다(clearance 는 닿음이 아니므로 제외 — StepForge graph.py 규약). G5 partial 이면 scope 밖 리프는 `scope_out` 으로 세지 않는다.

`results`(dyna_result 가 있고 kind 가 같을 때만) `{report_ids[], kind: deep|sphere|impact, sim_params_hash, summary(원문), parts_map{pid: nid}, part_risk[{nid, pid, worst_stress{value, case_key}, worst_g, worst_disp, min_safety_factor}], findings[{severity, title, detail, recommendation}], energy_edges[](원문), worst_cases[≤5]}`. 같은 값이 dyna pid 노드의 `attrs.results{report_id, worst_stress, worst_g, worst_disp, min_safety_factor}` 오버레이로도 들어가 **노드 투영을 통해 ir_hash 에 반영된다**(같은 설계에 새 리포트를 붙이면 새 스냅샷이 된다). 리포트가 2건 이상이면 파트별 최악값은 report_ids 순서의 첫 리포트를 쓰고 나머지는 `results.part_risk[].by_report{}` 로 병기한다.

`warnings[]{severity: CRITICAL|WARNING|INFO, code, message, ref, source_kind}`. 소스 원문 코드(§2.5.1)에 IR 빌더 코드를 더한다.

| code | severity | 조건 |
|---|---|---|
| ambiguous_edge_endpoint | WARNING | MCP 만으로 캡처해 name_a/name_b 가 동명 파트에 다의 → 엣지 제외 |
| source_inconsistent | WARNING | inspect_report·interface_graph counts 가 엣지 표와 불일치 |
| contact_side_unresolved | WARNING | modelmeta unresolved_sides > 0 |
| report_parts_mismatch | WARNING | 리포트 parts[].name 과 K파일 title 의 name_norm 불일치 |
| sameas_conflict | WARNING | §2.6.4 |
| bridge_stale | WARNING | §2.6.2 2단계 |
| ledger_needs_review | INFO | §2.10 |
| ledger_pair_absent | INFO | 원장 pair_key 에 해당하는 엣지가 이번 검출에 없음 |
| tol_config_unknown | INFO | tol_config_hash null |
| dyna_pat_absent | WARNING | 러너 자격 (b) 소유자 포털 PAT 없어 dyna 소스 생략(서비스 PAT 시야는 세션 0건) |
| ecad_absent | INFO | 어댑터 미발견 |

message 는 소스 원문이거나 render.py 정규 표기 문자열이고 판단어 린터를 통과한다.

## 2.10 원장(ledger) 재적용 — 재검출·재추출을 이기는 사람 확정

StepForge 는 재검출 시 `interfaces` 를 삭제·재삽입해 confirmed/manual 이 사라지고(job_worker.py:457-470), 재파싱은 노드 id 를 재부여한다. DynaForge 는 파트 별칭을 저장할 곳이 없다. 그래서 사람 확정 3종은 앱 DB 원장에만 쓰고 스냅샷 생성 때 재적용한다.

| 원장 | 행 | 재적용 지점 | 결과 |
|---|---|---|---|
| `rr_iface_ledger` | `{id, project_id, pair_key('<path_a>\|<path_b>' 정렬·프로젝트명 제거), kind_override\|null, status: confirmed\|rejected\|manual, note, decided_by, decided_at, snapshot_id_at_decision, geom_fp_a, geom_fp_b}` | mcad iface 엣지 조립 직후 | pair_key 가 맞는 엣지의 `status=manual_ledger`(rejected 면 `rejected`), kind_override 가 있으면 `kind` 를 덮고 소스 kind 는 `attrs.kind_source` 에 보존. 끝점 geom_fp 가 저장값과 다르면 적용은 하되 warnings `ledger_needs_review`. 엣지가 없으면 `ledger_pair_absent`. |
| `rr_sameas` | `{id, scope: intra\|pair\|global, project_id, pair_id, a_stable, b_stable, method, score, status: confirmed\|rejected, decided_by, decided_at, snapshot_id_at_decision}`(stable key 는 §2.6.2 1단계, DDL 은 §5.2.2 C) | same-as 사다리 1단계 | §2.6.2 |
| `rr_part_keys` | §2.7.3 | ckey 부여 | merged_into 해석 |

우선순위. 원장 `rejected` > 원장 `manual/confirmed` > 소스 `manual` > 소스 `confirmed` > 소스 `auto`.

사람 실행과 코드 실행의 구분.

| 행위 | 누가 | 어떻게 |
|---|---|---|
| 계면 kind/status 확정 | 사람 | ComparePage·SnapshotPage 에서 행 선택 → `PUT /api/projects/{id}/iface-ledger` |
| same-as confirm/reject, ckey 병합 | 사람 | SameAsResolver → `POST /api/sameas/decide` |
| 원장 재적용 | 코드 | 스냅샷 생성·'재해석 적용' 때 ir_builder 가 자동 |
| 'StepForge 에 반영' | 사람 | 버튼이 원장 행마다 `set_interface(name_a, name_b, kind, note)` 를 호출. 이름 기반이라 동명 파트가 함께 바뀜을 경고하고 rowcount 를 표시. 자동 호출 없음 |
| StepForge parse/detect 재실행, DynaForge modelmeta(detect) | 사람 | 화면 안내 문구 "세션/프로젝트에 산출물이 생긴다" 뒤 버튼. 코드가 `run_job·run_operation` 을 호출하지 않는다 |

## 2.11 ir_hash · 버전 · 스냅샷 동결 · rr_snapshot_calls

### 2.11.1 ir_hash

```
ir_hash = sha256(canonical_json({
  "nodes":     sorted([{nid, canon_key, domain, kind, name_norm, name_norm_canon, ckey, dn, asm_key, status_flags, attrs: R(attrs)} ...], key=nid),
  "edges":     sorted([{eid, kind, a, b, members, status, attrs: R(attrs)} ...], key=eid),
  "same_as":   sorted([{a, b, method} for status == 'confirmed'], key=(a, b)),
  "dims_named": sorted([{name, value: round(value, 3), unit, method} ...], key=name)
}))
```

`R()` 은 반올림 규칙 — 길이 0.001 mm, 면적·부피 4 유효자리, 비율·정렬도 0.001, fs 0.01, 응력 0.1 MPa, 가속도 0.1 G, 문자열은 원문, null 은 null. `canonical_json` 은 키 정렬·구분자 `(',', ':')`·`ensure_ascii=False`·NaN 금지다. provenance·captured_at·snapshot_id·sources[].stats/context/captured_at·warnings·rollups·gates·character_seed·feature_vector 는 입력에 없다. 그래서 같은 소스·같은 tol·같은 원장이면 재추출해도 같고, P1 통과 기준 (1) '2회 추출 ir_hash 동일' 이 이것을 검증한다.

### 2.11.2 버전

| 스탬프 | 값·규칙 |
|---|---|
| ir_version | '1.0'. ecad 노드가 1개 이상이면 '1.1'(추가 kind 뿐, 필드 삭제 없음). 독자는 `≤ 현재` 를 모두 읽고, 서로 다른 ir_version 의 diff 는 허용하되 `comparability.ir_version_parity=false` 로 표기한다(§3). 기존 스냅샷을 다시 쓰지 않는다. |
| adapter_versions{kind} | 매핑표(§2.5)가 바뀌면 올린다. 스냅샷·finding·보고서에 남는다. |
| taxonomy_version · seed_rules_version · vocab_version | 스냅샷 생성 시점의 파일 버전. |
| derived_from | 같은 과제의 직전 스냅샷 id. RA `derived_from(design_snapshot→design_snapshot)` 로 복제. |
| 과제 계보 | `rr_projects.predecessor_project_id`(과제→과제, 사용자 지정, §5.2.2 A)가 RA `revision_of{project→project, acyclic}` 로 복제된다. StepForge `revision_of` 는 미구현이므로 앱 DB 가 유일한 원천이다. |

### 2.11.3 스냅샷 동결 절차(`POST /api/projects/{id}/snapshots {label, kinds[], report_ids?, detect_result_file_id?}` → 202 `{job_id}`, 백그라운드 잡, 예산 180 s, 진행은 `GET /api/projects/{id}` 의 `jobs[]` 폴링 — §8.2.3·§8.2.4)

1. `adapters/registry.py` probe — 각 소스 kind 의 app_key 가 게이트웨이에 있고 필요한 도구가 전부 보이는지 확인. 없으면 kind 별로 `degraded`/`missing` 을 세우고 계속한다(mcad 가 없으면 `409 source_unreachable`).
2. mcad 캡처 — `job_status(detect_job_id)` 가 done 이 아니면 `409 detect_not_done`. REST `/tree` → `/artifacts/graph/` → `/parts` → MCP `list_interfaces`×kind 4 → `part_mesh_map` → `inspect_report`(검증). REST 실패 시 MCP `list_parts·project_tree` 폴백 + `mcp_degraded`.
3. dyna 캡처 — 요청자(`rr_projects.owner_sub`)의 `_user_credentials` 행(러너 자격 (b), §0.1.6)이 없으면 `missing.dyna_absent` + `dyna_pat_absent` 로 건너뛴다. 있으면 `list_session_files` → `inspect_file` → (detect 결과 파일 지정 시) `download_result` → 전사 집계 3종.
4. dyna_result 캡처 — `report_summary` → `report_part_risk` → `report_findings` → `report_energy_flow` → `report_worst_cases(limit 5)`, 리포트 ≤3건. kind 불일치면 `results=null` + `result_kind_mismatch`.
5. ecad — `ecad_stub.discover` 만. 부재면 `ecad_absent`.
6. 조립 — 노드·엣지 → `rr_iface_ledger` 재적용 → same-as 사다리(+`rr_sameas`) → 클러스터·dn·ckey(+`rr_part_keys`) → dims_named 재평가 → rollups → results 오버레이 → warnings.
7. `state.py` 호출 — 게이트 G1~G6·character_seed·feature_vector·rule_hits 를 계산해 rr_ir.gates 등에 복사한다(정의는 §3).
8. `ir_hash` 계산 → `(project_id, ir_hash)` 존재하면 기존 `snapshot_id` 를 `{reused: true}` 로 반환하고 이번 호출 로그는 그 스냅샷에 덧붙인다. 없으면 `rr_snapshots` 삽입 + `rr_ir_nodes·rr_ir_edges` 펼침 + `rr_states` 삽입.
9. `ra_client.upsert_design_snapshot`(비치명, 실패는 `external_sync.ra=pending`) 후 잡 결과 `{snapshot_id, ir_hash, reused, partial, blocked, gates_summary, degraded}` 를 `jobs[]` 에 남긴다(요청 응답 자체는 1단계 전에 돌려준 202 `{job_id}` 다).

G6 fail(`blocked=true`)이어도 스냅샷은 저장된다. 차단되는 것은 그 스냅샷으로 diff·타깃을 만드는 것이다(`409 gate_blocked`).

### 2.11.4 rr_snapshot_calls

행 `{call_id PK('<snapshot_id[:8]>-<seq:03d>'), snapshot_id, owner_sub, source_kind, channel: mcp|rest, tool, args_json, args_hash, ok: bool, http_status|null, response_sha256, response_gz BLOB, response_bytes, started_at, duration_ms, error|null}`. 모든 소스 호출(폴백·검증 호출 포함)을 순서대로 남긴다. `tool:<call_id>` 참조는 이 행을 가리키고 `GET /api/refs/tool:<call_id>` 가 소유자에게 gunzip 원문을 돌려준다. '재해석 적용' 은 이 원문만으로 6~9 단계를 다시 돌리므로 소스가 그새 바뀌어도 같은 원천에서 새 원장을 적용한 스냅샷을 만들 수 있다. 보존은 스냅샷과 같이 간다(스냅샷 삭제 시 함께 삭제).

## 2.12 게이트 G1~G7 의 IR 입력·임계·효과

게이트는 rr_state(§3)가 계산·판정하지만 입력은 전부 rr_ir 필드이므로 여기서 입력과 임계를 못박는다. 레코드 `{key, count, threshold, pass, blocking: bool, effect: [코드], detail: [ref…]}`. G1~G6 는 단일 스냅샷, G7 은 pair 전용으로 `rr_diff.comparability` 에 산다. `blocked = not G6.pass` 하나뿐이다.

| 키 | IR 입력 | 임계(pass 조건) | fail 효과 |
|---|---|---|---|
| G1 dup_or_anon_names | mcad `part` 노드 중 `status_flags ∋ auto_named \| duplicate_name` 수 n_anon, 리프 수 n_leaf | n_anon ≤ max(5, 0.10·n_leaf) | 진입 허용. E0 에 '익명/중복 이름 N/M' 표기, 좌석 계약이 이름 대신 `[p:]` 인용을 강제(§6), character_seed `char:maturity:anon_names_high` 부여(§3.2.4). |
| G2 sameas_pending | `same_as.status == pending` 수 + `sameas_conflict` 수(pair 는 base·target intra 와 pair correspondence 를 합산) | 0 | pair 의미층(rr_diff.semantic) 생성 차단, 구조·파라메트릭층은 생성. snap 은 표기만. 해제는 SameAsResolver 확정 후 재해석. |
| G3 iface_unconfirmed | `kind == interference AND status == auto` 엣지 수 | 0 | 진입 허용. 해당 엣지 정규 표기에 `(auto, 미확정)` 접미 강제, 의미 이벤트 `unconfirmed=true`(§3). |
| G4 coordinate | warnings code ∈ {suspect_coordinate_systems, files_all_overlap} 수 | 0 | 진입 허용. `cross_file=true` 엣지의 confidence 를 `low` 로 강등하고 정규 표기에 `(cross_file, 좌표계 의심)` 접미. |
| G5 partial_scope | `sources[].scope` 가 non-null 인 소스가 있을 때 범위 밖 리프 수(count, §3.2.2 와 동일 신호) | 0 | 진입 허용. `partial=true`. pair diff 에서 scope 밖 노드는 `scope_out` 으로 표기하고 added/removed 로 세지 않음(§3). E0 표기. |
| G6 unit_scale | (a) warnings `unit_mismatch` 수, (b) mcad `unit_system != 'mm'`, (c) dyna 모델 size 대각선 ÷ mcad 전체 bbox_world 대각선 = r(둘 다 있을 때), (d) ecad `odb_get_board.units` 환산 실패 | (a)=0 AND (b) false AND r ∈ [0.95, 1.05](계산 불가면 `unknown`, pass 표기) AND (d) 없음 | **blocked=true**. diff·타깃 생성 `409 gate_blocked`. 사용자가 소스(단위)를 고쳐 재캡처해야 풀린다. |
| G7 yardstick_parity(pair) | `tol_parity` = base·target `tol_config_hash` 동일(어느 쪽 null 이면 false, reason `tol_unknown`). `result_parity` = 양쪽 `results` 존재 AND kind 동일 AND `sim_params_hash` 동일 | 둘 다 true | 진입 허용. tol false → iface 파라메트릭 delta 전부 `excluded_reason='tol_differs'\|'tol_unknown'`, kind_changed 이벤트 `caveat='tol_differs'`. result false → result delta 미생성(정성만), E4 에 수치 없음. |

게이트 무시는 없다. fail 이면서 진입 허용인 게이트는 E0 와 결정문 헤더에 반드시 표기되고(§4 evidence_profile 옆), 표기 누락은 `quality.flag=header_mismatch` 다.

## 2.13 어댑터 계약

### 2.13.1 `adapters/base.py`

```python
class Probe(TypedDict): app_key: str | None; reachable: bool; tools_present: list[str]; rest_ok: bool | None
class AdapterResult(TypedDict): nodes: list; edges: list; warnings: list; degraded: list[str]; source: dict; call_ids: list[str]
class IrAdapter:
    kind: str            # 'mcad' | 'dyna' | 'dyna_result' | 'ecad'
    version: str         # adapter_version
    required_tools: tuple[str, ...]
    def discover(self, registry: AppRegistry) -> Probe: ...
    def capture(self, ref: dict, principal: Principal, recorder: CallRecorder) -> AdapterResult: ...
```

어댑터는 순수 함수다. DB 에 쓰지 않고, 호출은 전부 `recorder.call(channel, tool, args)` 를 거쳐 `rr_snapshot_calls` 에 남는다. 노드·엣지의 nid·eid·ckey 는 어댑터가 아니라 `ir_builder.py` 가 붙인다(어댑터는 canon_key·local_key 까지).

### 2.13.2 `adapters/registry.py`

게이트웨이 `list_tool_apps` 와 앱 manifest 를 읽어 도구 이름 집합으로 kind 별 app_key 를 찾는다. mcad = `{list_parts, list_interfaces, interface_graph, project_tree, part_mesh_map, job_status}` ⊆ tools, dyna = `{inspect_file, list_session_files, report_summary, report_part_risk, report_energy_flow}`, ecad = 4도구. 후보가 여럿이면 `rr_sources.app_key`(소스 등록 시 사용자가 고른 값)를 쓴다. REST 원문 경로는 Caddy `{HWAXRISK_HEAX_BASE}/apps/{app_slug}/api/projects/{id}/tree · /artifacts/graph/ · /parts` 이고 헤더는 `Authorization: Bearer <HWAXRISK_HEAX_SERVICE_PAT>`, 메서드는 GET 만이다(§8.2.11 — 게이트웨이 `rest_proxy` 에 heax 사이트를 두지 않는다, §10 #2). `app_slug` 는 heax `GET {HWAXRISK_HEAX_API}/api/v1/mcp/servers` 항목의 `id`(게이트웨이 키 `heax-<id>` 의 `<id>`, §8.2.11 보조 조회)에서 읽는다. `rr_sources` 행 `{id, project_id, owner_sub, kind, app_key, ref_json, probe_json{reachable, tools_present, rest_ok, last_probe_at}, created_at}`.

### 2.13.3 `adapters/mcad.py`

호출 상한 REST 4 + MCP 6. 순서·폴백은 §2.11.3 2단계. `interfaces_truncated`(kind 별 500 초과) 시 graph.json edges 로 위상만 채우고 attrs 는 null 이다. tol_config_hash 는 §2.2 규칙. world bbox 재계산은 4x4 row-major 를 8꼭짓점에 곱해 축정렬 min/max 를 취한다(P1 통과 기준 (3) ±0.01 mm).

### 2.13.4 `adapters/dyna.py`

- 자격은 §0.1.6 러너 자격이다 — 요청자(`rr_projects.owner_sub`)의 `_user_credentials` 행(b)이 있으면 그 포털 PAT 로 게이트웨이 `heax-kooremapper_mcp` 를 호출하고(DynaForge per_user_sso 가 PAT email 로 발동), 없으면 (a) 서비스 PAT 시야는 세션 0건이라 호출하지 않고 `missing.dyna_absent` + `dyna_pat_absent` 로 강등한다(P0 통과 기준 (9)(b) 실측). 대리 발급·브라우저 세션 캡처 모드는 없다. 게이트웨이 서비스 계정으로 private 세션을 여는 코드는 없다(P2 통과 기준 (8)).
- `meta.modelmeta` 만 정본이다. `part_titles` 를 쓰지 않는다. `_group_of` 는 리포트 파서 규칙을 그대로 재구현한다(`\` 또는 `/` 앞이 group, 없으면 `Other`).
- detect=true 결과는 `ref.detect_result_file_id` 로 지정된 SessionFile 을 `download_result` 로 읽는다. 어댑터가 `run_operation` 을 호출하는 경로는 없다.
- 리포트는 ≤3건, kind 동일. `energy_flow.edges` 의 src/dst 가 pid 임을 P2 픽스처로 확정한 뒤 nid 로 사상하고, 확정 전에는 `load_path` 엣지를 만들지 않고 `results.energy_edges` 원문만 둔다.
- 결속 `binding.method` 는 §2.2 규칙. `report_parts_mismatch` 가 리포트 파트의 30% 를 넘으면 결속을 `same_session_weak` 로 강등하고 warnings 에 남긴다.

### 2.13.5 `adapters/ecad_stub.py` → `adapters/ecad.py`(P7)

스텁은 `discover` 만 구현하고 `capture` 는 빈 결과 + `ecad_absent` 다. 계약(§2.5.3)이 이행되어 4도구가 발견되면 `ecad.py` 가 component/net/layer 노드와 `net` 엣지를 만들고 ir_version 을 '1.1' 로 올린다. 그 전에 ecad 를 가정하는 코드는 `missing.ecad_absent` 분기뿐이다(§6 ECAD 의존 도메인 deferred).

## 2.14 스키마·픽스처·검증

- `schemas/rr_ir.v1.json`(JSON Schema 2020-12)이 §2.2~§2.9 의 필드·enum·필수 키를 고정한다. 유효 픽스처 3(mcad 단독·mcad+dyna·mcad+dyna+dyna_result)·무효 픽스처 5(단위 누락·nid 형식 위반·status 어휘 밖·null→0 치환·ir_version 없음)를 둔다.
- 골든 `backend/tests/golden/sif-e2e.ir.json` 은 재파싱·재검출 후의 sif-e2e(리프 3·엣지 2)이고 P1 통과 기준 (1)(2)(3)(8) 의 대상이다.
- 결정론 테스트 — 같은 `rr_snapshot_calls` 원문으로 ir_builder 를 2회 돌려 ir_hash 동일, 노드 순서를 섞어도 동일.
- 키 단위 테스트 — `name_norm·name_norm_canon·geom_fp·ckey·asm_key` 각 20케이스(동의어·두께 토큰·auto_named·Dyna Group\Name·프로젝트 코드 제거).
- same-as 테스트 — 브리지 선언 케이스 정밀도 100%, 이름 교란 20% 합성 30쌍 정밀도 ≥0.95·재현율 ≥0.9, conflict 픽스처에서 ckey null·G2 계수(P2 (2)(3)).
- 원장 테스트 — confirm 후 재캡처에서 `manual_ledger` 복원, 기하 변화 시 `ledger_needs_review`, rejected 엣지가 rollups·orphan 에서 제외(P2 (4)).
- 게이트 픽스처 5케이스(G1 fail·G2 fail·G4 fail·G5 partial·G6 blocked)에서 `{pass, blocking, effect}` 일치, G6 fail 시 `POST /api/diffs` 가 `409 gate_blocked`(P1 (4)).
- 규모 — 노드 500·엣지 2000 합성에서 캡처 조립(소스 호출 제외) < 5 s, 누락 0(P1 (5)).
- 판단어 — 빌더가 만드는 모든 `warnings[].message` 와 정규 표기가 린터 통과(P1 (6)).

---


# §3 그래프 diff 와 상태 평가

이 절은 코드가 만드는 두 산출물의 규격이다. 하나는 단일 스냅샷의 상태 평가 `rr_state`(§0.1.1), 다른 하나는 두 스냅샷의 3층 diff `rr_diff`(§0.1.1)다. 둘 다 LLM 이 개입하지 않는 결정론 산출이고, 어느 필드에도 판단이 들어가지 않는다(헌법 P1). 좌석과 의장은 이 두 산출물의 항목 id(`sig:`·`[c:]`·`[p:]`·`[e:]`·`[d:]`, §0.2.1)를 인용해 §4 의 서술을 만든다. 따라서 이 절의 모든 항목은 (1) 안정된 id 를 갖고 (2) 정규 표기 문자열을 동반하며 (3) 판단어 린터를 통과한다.

이름은 전부 §0 정본을 따른다. 모듈은 `state.py`(rr_state·게이트·signals·character_seed·feature_vector·rule_hits), `diff.py`(3층 diff·임계·comparability·rollup·의미 이벤트), `render.py`(정규 표기·summary_text·판단어 린터)다(§0.4.1).

## 3.1 두 산출물의 자리와 원칙

| 산출물 | 입력 | 만드는 시점 | 저장 | 서술이 인용하는 단위 |
|---|---|---|---|---|
| rr_state | rr_ir 1개(+ rr_rules active) | 스냅샷 동결 직후 자동(`POST /api/projects/{id}/snapshots` 의 잡 마지막 단계) | `rr_states(snapshot_id PK, state_json, feature_json, rule_hits_json, character_seed_json, summary_text, state_version, created_at)` | `sig:<key>` · `gate:G<n>` · `rule:<rule_id>` · `warn:<code>#<ref>` |
| rr_diff | rr_ir 2개(base·target) + 두 rr_state + pair 대응(§2 same-as 사다리) | `POST /api/diffs` 요청 시 동기 계산(노드 500·엣지 2000 에서 5 s 이내) | `rr_diffs(id PK, base_snapshot_id, target_snapshot_id, diff_json, comparability_json, stats_json, summary_text, summary_status, diff_version, created_at, UNIQUE(base,target))` + `rr_diff_events(diff_id, cid, code, change_kind, subject_key, ckeys_json, magnitude, unit, rel, confidence, design_relevant, unconfirmed, excluded_reason, text, PRIMARY KEY(diff_id, cid))` | `[c:<cid>]` · `[d:<name>]` · `gate:G7` |

원칙 다섯 가지다.

1. 결정론. 같은 `(ir_hash_base, ir_hash_target, taxonomy_version, rule_version)` 이면 바이트 동일 `diff_json`·`summary_text` 가 나온다. `rr_states.state_json` 도 같은 `(ir_hash, rule_version)` 이면 동일하다. 시각·snapshot_id·provenance 는 해시 입력에서 제외한다(§0.1.1 ir_hash 규칙과 같은 이유).
2. null 은 미측정이다. 어느 집계도 null 을 0 으로 치환하지 않는다. 한쪽이 null 인 파라메트릭 항목은 `flag='null_one_side'` 로 delta 를 만들지 않는다.
3. 원천 문자열은 그대로 인용한다. StepForge `note`, tree.warnings `message`, DynaForge `findings[].title/detail`, 규칙의 `why_it_matters` 는 코드가 다시 쓰지 않고 `«…»` 로 감싸 원문 그대로 둔다. 판단어 린터는 `«…»` 안을 보지 않는다.
4. 비율이 정본이고 절대값은 잡음 하한이다(map_1 D-120). 파라메트릭 변경 판정은 절대 하한과 상대 임계를 함께 쓰고, 상위 표는 절대·상대 두 순위를 병기한다.
5. 비교가능성은 데이터다. 다른 잣대(tol)·다른 리포트 kind·부분 검출·단위 불일치는 항목별 `excluded_reason` 과 diff 헤더 `comparability` 로 남기지 항목을 조용히 버리지 않는다.

## 3.2 rr_state 규격(state_version '1.0')

### 3.2.1 봉투

```json
{"state_version":"1.0","snapshot_id":"<hex32>","ir_hash":"<sha256>","project_id":"<hex32>",
 "rule_version":"rules-1.0","taxonomy_version":"1.0","seed_rules_version":"seed-1.0",
 "computed_at":1756600000,
 "blocked":false,
 "gates":{"G1":{},"G2":{},"G3":{},"G4":{},"G5":{},"G6":{}},
 "missing":{"ecad_absent":true,"dyna_absent":false,"dyna_result_absent":false,"result_kind_mismatch":false,
            "world_transform_absent":false,"volume_null":false,"material_density_unsourced":true},
 "signals":{"<key>":{"kind":"count|ratio|scalar|vec|top|hist|flag|table","value":null,"unit":null,
                     "refs":[],"text":"<정규 표기>","derived_from":[],"known":true}},
 "character_seed":[{"tag":"char:structure:multi_file_assembly","rule":"seed.structure.multi_file","cites":["sig:counts.files"],"text":"files=2"}],
 "feature_vector":{"version":"fv-1.0","names":[],"values":[],"known":[],"transform":[]},
 "precedent":{"corpus_n":0,"per_feature":{},"out_of_range_count":0},
 "rule_hits":[{"rule":"R-001","severity":"중대","pass":false,"found":{},"why_it_matters":"«…»","fix_hint":"«…»","payload_hash":"<sha256>","refs":[]}],
 "summary_text":"<≤2000자, 결론 없음, 줄마다 참조>",
 "summary_status":"ok|lint_failed"}
```

`missing` 은 rr_ir 의 값을 그대로 옮긴다(§2 가 정의, rr_state 는 재계산하지 않는다). `blocked` 는 G6 fail 일 때만 true 다(§0.1.1 게이트 정의). G7 은 pair 전용이라 rr_state 에는 없고 rr_diff.comparability 에만 있다.

### 3.2.2 게이트 G1~G7 — 신호·임계·효과

각 게이트 레코드는 `{key, count, threshold, pass, blocking, effect, ack_by, ack_at, ack_reason, detail:[ref…]}` 다(IR 입력·임계는 §2.12, `blocking=true` 는 G6 뿐). `effect` 는 코드가 그 게이트 상태에서 실제로 무엇을 하는지의 enum 이고 사람이 바꿀 수 없다. `ack` 는 pass=false 인 게이트에 사람이 사유를 적고 진행하는 기록이며, ack 가 붙어도 `pass` 는 false 로 남는다(브리프 E0 에 '게이트 fail·ack 사유' 로 실린다).

| 게이트 | 신호(count) | threshold | pass=false 일 때 effect | ack |
|---|---|---|---|---|
| G1 dup_or_anon_names | `auto_named` 또는 `duplicate_name` 플래그가 있는 리프 노드 수 | `≤ max(5, 0.10·leaf)` | `mark` — 해당 노드의 정규 표기에 `(auto_named)` 접미 강제, same-as 사다리(§2)가 이 플래그를 읽어 name_norm 단계 점수를 낮춘다, character_seed `char:maturity:anon_names_high` 부여 | 가능 |
| G2 sameas_pending | `same_as.status='pending'`(auto score < 0.9) 건수 + 같은 도메인 노드 2개가 한 클러스터에 든 conflict 수 | `= 0` | snap: `mark` — pending 노드는 dn 이 자기 nid 이고 results 오버레이 조인을 하지 않는다. pair: `block_semantic` — 의미층 이벤트를 만들지 않고 `semantic.blocked_by='G2'`, 구조·파라메트릭층은 대응 확정분만으로 만든다 | 불가(POST /api/sameas/decide 로 해소) |
| G3 iface_unconfirmed | `kind='interference'` 이고 `status='auto'` 인 엣지 수. `status='manual_ledger'`(원장 재적용, §2)와 `confirmed`·`manual` 은 세지 않는다 | `= 0` | `mark` — 그 엣지의 정규 표기에 `status=auto(미확정 초안)` 고정, 의미 이벤트 `iface.interference_new` 에 `unconfirmed=true`, E0 에 '미확정 간섭 N건' | 가능 |
| G4 coordinate | tree.warnings 중 `suspect_coordinate_systems`·`files_all_overlap` 건수 | `= 0` | `degrade_cross_file` — `cross_file=1` 인 엣지를 signals 의 top 표에서 제외하고 정규 표기에 `(cross_file, 좌표계 의심)` 접미, 의미 이벤트 confidence 를 low 로 강등 | 가능 |
| G5 partial_scope | §2.12 와 동일 — `sources[].scope` 가 non-null 인 소스가 있을 때 범위 밖 리프 수(count). interfaces 행의 `params`·`detected_at` 혼합도는 계산하지 않는다(MCP `list_interfaces`·REST 모두 두 필드를 내지 않아 `detected_at=null` 로 저장된다, §2.5.1) | `= 0` | `mark_partial` — 스냅샷 `partial=true`. pair 에서는 범위 밖 파트가 끝점인 엣지 변경에 `excluded_reason='partial_scope'` 를 달고 의미 이벤트를 만들지 않는다. summary_text 첫 줄에 `부분 검출(범위 밖 리프 N)` | 가능 |
| G6 unit_scale | tree.warnings `unit_mismatch` 건수 + mcad `unit_system != 'mm'` 이면 +1 + (dyna 가 있을 때) `dyna 모델 bbox 대각 / mcad bbox_world 대각` 이 `[0.95, 1.05]` 밖이면 +1(계산 불가면 `unknown`, 계수 0) + ecad `odb_get_board.units` 환산 실패면 +1(§2.12) | `= 0` | `block` — `blocked=true`. diff 생성(`POST /api/diffs`)은 409, 타깃 생성도 409. 사람이 소스를 고쳐 새 스냅샷을 만들어야 한다 | 불가 |
| G7 yardstick_parity(pair) | `tol_parity=false` 이면 +1, `result_parity=false` 이면 +1 | `= 0` | `exclude_by_reason` — tol 불일치면 gap 계열(min_gap·contact_area_est·band_width·penetration_*) 파라메트릭 항목 전부 `excluded_reason='tol_differs'`, 결과 불일치면 `result_delta` 를 만들지 않고 `excluded_reason='result_kind_differs'` 또는 `'sim_params_differ'` | 불가(잣대는 고칠 수 없다) |

G7 세부. `tol_parity` 는 base·target 의 `sources[kind=mcad].tol_config_hash` 가 같으면 true 다. 한쪽이라도 tol 스냅샷을 얻지 못했으면(§2 가 `tol_keys_known=false` 로 표기) `tol_parity=null` 이고 gap 계열은 `excluded_reason='tol_unknown'` 이다. `result_parity` 는 두 스냅샷 `results.kind` 가 같고 `results.sim_params_hash` 가 같을 때 true 다. kind 가 같고 sim_params_hash 만 다르면 `result_delta` 는 만들되 항목마다 `excluded_reason='sim_params_differ'` 를 붙여 수치를 표에는 싣고 의미 이벤트 `result.*` 는 만들지 않는다. `tol_config_hash` 가 REST `GET /projects/{id}` 의 `tol_config` 없이 잡 params 4키(`tied_gap·clearance_gap·tied_area·tied_width`)만으로 계산된 스냅샷(`tol_known_keys` 길이 4, §2.5.1)이 한쪽이라도 있으면 `tol_parity` 값은 그대로 두되 G7 레코드 `detail` 에 `reason='tol_keys_partial(4)'` 를 병기해 E0·comparability 표에 실리게 한다(잣대 동일성이 4키 범위에서만 확인됐다는 사실 표기이지 fail 이 아니다).

게이트 픽스처 5케이스(P1 통과 기준 (4)의 정의). `backend/tests/fixtures/gates/`.

| 케이스 | 구성 | 기대 |
|---|---|---|
| gate_f1_clean | 리프 6, 이름 유일, interference 0, warnings ∅, scope null | G1~G6 pass, blocked=false |
| gate_f2_anon | 리프 40 중 auto_named 9 (threshold = max(5, 0.10·40) = 5) | G1 fail(9 > 5), effect=mark, 나머지 pass. 대조군으로 리프 10·auto 4 는 4 ≤ 5 라 pass 임을 같은 픽스처의 서브케이스로 둔다 |
| gate_f3_unit | tree.warnings `unit_mismatch` 1 | G6 fail, blocked=true, `POST /api/diffs` 409 |
| gate_f4_iface | interference 2(auto 1·manual_ledger 1) | G3 fail count=1(manual_ledger 미계수), 그 엣지 정규 표기에 `status=auto(미확정 초안)` |
| gate_f5_partial | scope{match:['PLATE*']}, warnings `suspect_coordinate_systems` 1, cross_file 엣지 1 | G4 fail·G5 fail, partial=true, cross_file 엣지 top 표 제외 |

### 3.2.3 signals — 단일 과제 서술의 인용 단위

단일 스냅샷 타깃(`snap:`)에는 diff 항목이 없으므로 좌석이 인용할 원자는 `sig:<key>` 다. 키 목록은 고정이고(state_version 이 바뀌어야 추가된다) 값은 IR 에서 결정론으로 나온다. 각 signal 은 `{kind, value, unit, refs, text, derived_from, known}` 을 갖고, `text` 는 render.py 가 만든 정규 표기라 좌석은 그 문자열을 그대로 `quote` 에 복사한다.

| 키(`sig:` 뒤) | kind | 값·규칙 | refs |
|---|---|---|---|
| counts.files · counts.leaf · counts.assemblies | count | tree.summary 의 files·leaf_instances·assemblies | — |
| counts.edges.tied · .touching · .clearance · .interference | count | IR edges kind 별 | — |
| counts.edges.status.auto · .confirmed · .manual · .manual_ledger | count | IR edges status 별(interference 포함 전체) | — |
| counts.orphans | count | rollups 의 orphan_leaf 합(clearance 는 접촉이 아님, graph.py 규약) | `[p:]…` 상위 10 |
| counts.cross_file | count | cross_file=1 엣지 수 | — |
| counts.auto_named · counts.duplicate_names | count | 리프 노드 플래그 수 | `[p:]…` 상위 10 |
| counts.materials_distinct · counts.material_null | count | material_norm 종류 수 · material null 리프 수 | — |
| counts.dyna.pids · counts.dyna.contacts_by_type · counts.dyna.single_surface | count·table | dyna 노드 수, `{contact_type: n}`, scope 하이퍼엣지 수. dyna_absent 면 known=false | — |
| counts.ecad.components · counts.ecad.nets | count | ecad_absent 면 known=false(값 null) | — |
| ratios.tied_ratio | ratio | tied/(tied+touching+clearance+interference), 분모 0 이면 known=false | — |
| ratios.orphan_ratio · ratios.unconfirmed_ratio · ratios.cross_file_ratio · ratios.auto_named_ratio · ratios.material_null_ratio | ratio | orphans/leaf · status=auto/edges · cross_file/edges · auto_named/leaf · material_null/leaf | — |
| ratios.thin_ratio | ratio | `min_dim < 0.3 mm` 인 리프/leaf. min_dim=min(bbox_def dims)이며 축정렬 판재가 아니면 두께가 아니라는 사실을 text 에 `(min_dim 근사)` 로 병기 | — |
| ratios.sameas_coverage | ratio | dyna 노드 중 dn 이 mcad 노드와 같은 그룹인 비율. dyna_absent 면 known=false | — |
| scale.bbox_world | vec | mcad bbox_world 합집합 dims [dx,dy,dz] mm. world_transform_absent 면 known=false | — |
| scale.diag · scale.total_volume | scalar | bbox_world 대각 mm · 리프 volume 합 mm³(volume_null 면 known=false) | — |
| scale.mass_est | scalar | 출처 있는 밀도(§2 material.density source≠null)가 전 리프에 있을 때만 값, 아니면 known=false 이고 text 에 `(밀도 출처 없음 N건)` | — |
| top.interference[k] (k≤10) | top | penetration_depth 내림차순, 항목 `{eid, ckA, ckB, names, penetration_depth, lower_bound, status, cross_file}` | `[e:]` |
| top.tight_clearance[k] | top | clearance 중 min_gap 오름차순 | `[e:]` |
| top.tied_band_area[k] | top | tied 중 contact_area_est 내림차순(밴드면적임을 text 에 명기) | `[e:]` |
| top.thin_parts[k] · top.volume[k] · top.degree[k] | top | min_dim 오름차순 · volume 내림차순 · 리프 차수(clearance 제외) 내림차순 | `[p:]` |
| hist.gap_mm | hist | bins `[0, 0.01, 0.05, 0.1, 0.2, 0.5]` 의 min_gap 분포(clearance·touching·tied) | — |
| hist.degree | hist | 차수 0·1·2·3·4+ | — |
| rollup.by_assembly | table | rr_ir.rollups 그대로 `{asm_key, path_prefix, n_leaf, edges_internal, edges_external, orphan_leaf}` | — |
| results.part_risk_top[k] · results.findings · results.load_path_top[k] | top·table | dyna_result 가 있을 때만. part_risk 는 worst_stress 내림차순 `{dn, ckey, pid, part_name, worst_stress{value, case_key}, worst_g, worst_disp, min_safety_factor}`(sphere/impact 는 min_safety_factor null 을 그대로), findings 는 DynaForge `{severity, title, detail}` 원문 `«…»`, load_path 는 energy_edges total_work 내림차순 | `[p:]`·`[e:]`·`dyna:rpt:<id>` |
| results.over_yield[k] | top | `sim_params.yield_stress` 가 있을 때 `worst_stress/yield_stress` 내림차순, 없으면 known=false. 판정이 아니라 비율이다 | `[p:]` |
| warnings.by_code | table | `{code: n}` + 각 code 의 첫 메시지 `«…»` | `warn:<code>#<ref>` |
| dims_named | table | rr_ir.dims_named 그대로(null 은 `미측정`) | `[d:<name>]` |
| gates.summary | table | G1~G6 의 pass/fail/ack | `gate:G<n>` |

정규 표기 예. `sig:top.interference[1]` → `PLATE_2↔BRACKET_L interference penetration_depth≥0.05 mm(lower_bound) status=auto(미확정 초안) [e:9a1f3c2b0d4e]`. `sig:ratios.tied_ratio` → `tied_ratio=0.62 (tied 13 / 21)`. `sig:scale.mass_est` → `mass_est=미측정 (밀도 출처 없음 4건)`.

### 3.2.4 character_seed — 결정론 성격 씨앗(`character-seed-rules.v1.json`)

씨앗은 §4 성격 서술의 L0 층이다. 값은 통제 어휘(§4.6 `character-vocab.v1.json`)의 부분집합만 쓰고, 축 `char:philosophy` 는 씨앗이 절대 내지 않는다(좌석 전용). 씨앗 하나는 `{tag, rule, cites[], text}` 이고 `text` 는 조건을 충족한 수치의 정규 표기다. 씨앗은 결론이 아니라 '이 수치가 이렇다' 의 재서술이며, 그래서 §4 의 facet 서술이 씨앗을 인용하되 씨앗으로 대체되지는 않는다.

| tag | 조건(전부 rr_state signals 로 계산) | cites |
|---|---|---|
| `char:structure:multi_file_assembly` | counts.files ≥ 2 | sig:counts.files |
| `char:structure:thin_stack` | ratios.tied_ratio ≥ 0.6 AND ratios.thin_ratio ≥ 0.3 | sig:ratios.tied_ratio, sig:ratios.thin_ratio |
| `char:structure:fastener_dense` | name_norm 이 `screw|bolt|nut|rivet|pem` 정규식에 맞는 리프 ≥ 0.10·leaf | sig:counts.leaf + 해당 `[p:]` ≤10 |
| `char:structure:adhesive_dependent` | name_norm 이 `tape|adhesive|glue|psa|oca|ocr|bond` 에 맞는 리프 ≥1 AND 그 리프가 끝점인 tied 엣지 ≥ 0.3·counts.edges.tied | 해당 `[e:]` ≤10 |
| `char:structure:rigid_frame_load_path` | 리프 1개의 차수(clearance 제외) ≥ 0.3·leaf AND 그 리프 volume 이 top.volume[1..3] 안 | `[p:]` 1 |
| `char:interface:<alias>` | top.interference[1..3] 각 엣지. alias 는 rr_iface_alias 의 별칭이 있으면 그것, 없으면 `name_norm_a + '_' + name_norm_b`(정렬) | `[e:]` |
| `char:tolerance:tight` | clearance 엣지 중 min_gap ≤ 0.1 mm 비율 ≥ 0.3 | sig:hist.gap_mm |
| `char:tolerance:loose` | clearance 엣지 중 min_gap ≥ 0.3 mm 비율 ≥ 0.5 | sig:hist.gap_mm |
| `char:tolerance:moderate` | 위 둘 다 아니고 clearance ≥ 3 | sig:hist.gap_mm |
| `char:maturity:auto_iface_high` | ratios.unconfirmed_ratio ≥ 0.8 | sig:ratios.unconfirmed_ratio |
| `char:maturity:confirmed` | ratios.unconfirmed_ratio ≤ 0.2 AND edges ≥ 5 | sig:ratios.unconfirmed_ratio |
| `char:maturity:anon_names_high` | G1 fail | gate:G1 |
| `char:analysis:no_dyna` · `dyna_structure_only` · `dyna_with_results` | missing.dyna_absent / dyna 있고 dyna_result_absent / 둘 다 있음(result_kind_mismatch 면 structure_only) | — |
| `char:change_style:<v>` | pair 전용. rr_diff 의 의미 이벤트 change_kind 최빈값 → dimension→`dimension_tuning`, topology→`topology_change`, material→`material_swap`, placement→`placement_shift`. rr_diff.character_seed 에 담긴다 | `[c:]` 최빈 change_kind 상위 3 |

씨앗 규칙표는 버전(`seed-1.0`)을 갖고 rr_state 에 스탬프된다. 값 추가는 마이너, 임계 변경은 마이너이되 `rr_states` 재계산 스크립트를 동반한다.

### 3.2.5 feature_vector — 22차원 고정 순서

| # | name | 원천 | transform | known=false 조건 |
|---|---|---|---|---|
| 1 | n_leaf | counts.leaf | log1p | — |
| 2 | n_files | counts.files | log1p | — |
| 3 | n_tied | counts.edges.tied | log1p | — |
| 4 | n_touching | counts.edges.touching | log1p | — |
| 5 | n_clearance | counts.edges.clearance | log1p | — |
| 6 | n_interference | counts.edges.interference | log1p | — |
| 7 | orphan_ratio | ratios.orphan_ratio | id | leaf=0 |
| 8 | cross_file_ratio | ratios.cross_file_ratio | id | edges=0 |
| 9 | bbox_x | scale.bbox_world[0] | log1p | world_transform_absent |
| 10 | bbox_y | scale.bbox_world[1] | log1p | 동일 |
| 11 | bbox_z | scale.bbox_world[2] | log1p | 동일 |
| 12 | total_volume | scale.total_volume | log1p | volume_null |
| 13 | n_materials | counts.materials_distinct | log1p | — |
| 14 | material_null_ratio | ratios.material_null_ratio | id | leaf=0 |
| 15 | thin_ratio | ratios.thin_ratio | id | volume_null(bbox 는 있으므로 실제로는 leaf=0 만) |
| 16 | median_gap | hist.gap_mm 의 중앙값 | log1p(mm) | clearance+touching+tied=0 |
| 17 | min_gap | top.tight_clearance[1].min_gap | log1p(mm) | clearance=0 |
| 18 | max_pen_depth | top.interference[1].penetration_depth | log1p(mm) | interference=0 |
| 19 | n_dyna_pids | counts.dyna.pids | log1p | dyna_absent |
| 20 | n_dyna_contacts | Σ counts.dyna.contacts_by_type | log1p | dyna_absent |
| 21 | shell_ratio | dyna elem_class=shell pid 비율 | id | dyna_absent |
| 22 | n_ecad_cmp | counts.ecad.components | log1p | ecad_absent |

`values` 는 transform 후 원값이고 표준화(z-score)는 조회 시 코퍼스(owner_sub 무관 익명 집계는 §10 결정 전까지 owner_sub 범위)에서 한다. `known=false` 차원은 거리 계산에서 마스킹한다(양쪽 known 인 차원만으로 코사인, 차원 수 < 12 이면 유사도 null). `precedent.per_feature` 는 corpus_n ≥ 5 일 때 각 feature 가 코퍼스 [min, max] 안이면 `in_range`, 밖이면 `out_of_range`, corpus_n < 5 이면 `none` 이다(열충격 out_of_range 개념, map_3). 이 값은 §4 finding.precedent 의 재료다.

### 3.2.6 rule_hits — 시드 6종(`rules-seed.v1.json`)과 출력 형식

rr_rules(status=active) 를 IR 에 즉시 실행한다. 조건 DSL 은 §7 의 `{all:[{ref, op, value}], any:[]}` 이고 평가기는 부작용 없음·결정론이다. 출력 항목은 laminate `check_design_rules` 형식을 따른다.

```json
{"rule":"R-001","version":"rules-1.0","severity":"중대","pass":false,
 "found":{"count":2,"refs":["e:9a1f3c2b0d4e","e:77c0aa1b2d3e"],"text":"interference status=auto 2건"},
 "why_it_matters":"«간섭이 auto 로 남아 있으면 억지끼움 의도인지 설계오류인지 확정되지 않은 것이다»",
 "fix_hint":"«set_interface 로 kind 확정 또는 형상 수정 후 재검출»",
 "payload_hash":"<sha256(rule_id|version|found canonical)>","refs":["e:9a1f3c2b0d4e","e:77c0aa1b2d3e"]}
```

`why_it_matters`·`fix_hint` 는 규칙 저작자(사람)의 문장이라 `«…»` 원문 인용이고 린터 대상이 아니다. severity 는 택소노미 축 ⑤(경미|중대|치명)를 쓴다(laminate 의 hard|guideline|info 는 등록 시 치명|중대|경미 로 매핑).

| id | 이름 | 조건 DSL(요지) | severity |
|---|---|---|---|
| R-001 | interference_auto_present | `all:[{ref:'edge.kind',op:'eq',value:'interference'},{ref:'edge.status',op:'eq',value:'auto'}]` count ≥ 1 | 중대 |
| R-002 | tight_clearance_cluster | `all:[{ref:'edge.kind',op:'eq',value:'clearance'},{ref:'edge.min_gap',op:'lte',value:0.2}]` count ≥ 5 | 경미 |
| R-003 | thin_leaf_tied_both_sides | `all:[{ref:'node.min_dim',op:'lte',value:0.3},{ref:'node.degree_tied',op:'gte',value:2}]` count ≥ 1 | 중대 |
| R-004 | unit_mismatch_warning | `all:[{ref:'warnings.code',op:'in',value:['unit_mismatch']}]` exists | 치명 |
| R-005 | cross_file_with_suspect_coords | `all:[{ref:'edge.cross_file',op:'eq',value:1},{ref:'warnings.code',op:'in',value:['suspect_coordinate_systems','files_all_overlap']}]` | 중대 |
| R-006 | dyna_contact_without_mcad_tie | `all:[{ref:'edge.kind',op:'eq',value:'contact'},{ref:'edge.mapped_mcad_kind',op:'in',value:[null,'clearance']}]` count ≥ 1 — dyna contact 쌍을 dn 으로 mcad 에 사상했을 때 tied·touching·interference 엣지가 없음 | 중대 |

`edge.mapped_mcad_kind`·`node.degree_tied`·`node.min_dim` 은 평가기가 IR 위에 만드는 파생 ref 이고 목록은 §7 조건 DSL 의 ref 사전에 등록한다. 시드는 P1 에서 '사람이 손으로 쓴 규칙' 으로 활성화되며(crit_14 권고) 패턴 승격 산출이 아니다.

### 3.2.7 rr_state 의 summary_text(snap 타깃의 E1)

§3.4 의 생성기(render.py)가 같은 린터·같은 정규 표기로 만든다. 순서 고정이다.

1. `[대상] 과제 {code} 스냅샷 {snapshot_id[:8]} ir_hash={…[:12]} 소스 mcad={…} dyna={…|absent} dyna_result={…|absent} ecad=absent` 
2. `[게이트] G1 pass · G2 pass · G3 fail(1, ack 없음) · G4 pass · G5 pass · G6 pass [gate:G3]`
3. `[구조] 파일 2 · 리프 21 · 어셈블리 4 · 엣지 tied 13 touching 3 clearance 4 interference 1 · 고아 2 · cross_file 3 [sig:counts.*]`
4. `[상위 계면] 간섭 1 → PLATE_2↔BRACKET_L penetration_depth≥0.05 mm(lower_bound) status=auto(미확정 초안) [e:9a1f3c2b0d4e] · 근접 간극 상위 3 → … [e:…]`
5. `[치수] dims_named → battery_to_frame_gap=0.35 mm [d:battery_to_frame_gap] · hinge_plate_thickness=미측정 [d:hinge_plate_thickness]`
6. `[재료] 재질 종류 5 · 미기재 4 [sig:counts.material_null]`
7. `[Dyna] pid 18 · CONTACT_AUTOMATIC_SINGLE_SURFACE 1 · TIED_NODES_TO_SURFACE 6 · 결과 sphere n_cases 26 · worst_stress 상위 3 → … [p:…]` (dyna 없으면 `[Dyna] absent`)
8. `[규칙] R-001 fail(2건) [rule:R-001] · R-004 pass`
9. `[씨앗] char:structure:multi_file_assembly · char:tolerance:tight · char:analysis:dyna_with_results`
10. `[결측] ecad_absent · material_density_unsourced`

## 3.3 rr_diff 규격(diff_version '1.0')

### 3.3.1 봉투

```json
{"diff_version":"1.0","diff_id":"<hex32>","project_id":"<hex32>",
 "base":{"snapshot_id":"…","ir_hash":"…","label":"F7-DV1 2026-07-02"},
 "target":{"snapshot_id":"…","ir_hash":"…","label":"F7-DV2 2026-08-20"},
 "taxonomy_version":"1.0","rule_version":"rules-1.0",
 "comparability":{"tol_parity":true,"tol_keys_known":true,"unit_parity":true,"result_parity":true,
                  "scope_parity":true,"coordinate_ok":true,"partial_any":false,
                  "G7":{"count":0,"threshold":0,"pass":true,"effect":"none","detail":[]},
                  "base_blocked":false,"target_blocked":false},
 "correspondence":{"matched":[{"dn":"p:…","nid_base":"p:…","nid_target":"p:…","ckey":"ck:…","method":"exact_path","score":1.0,"status":"confirmed"}],
                   "unmatched_base":["p:…"],"unmatched_target":["p:…"],"pending_n":0,
                   "method_counts":{"ledger":0,"pid_map":0,"exact_path":18,"fingerprint":2,"name_norm":1,"fuzzy":0,"manual":0}},
 "structural":{"node_changes":[],"edge_changes":[],"orphans_delta":{},"hierarchy_moves":[],"dyna":{}},
 "parametric":{"node_params":[],"edge_params":[],"materials":[],"dims_delta":[],"result_delta":[],"rollup_delta":[]},
 "semantic":{"blocked_by":null,"events":[]},
 "character_seed":[{"tag":"char:change_style:dimension_tuning","cites":["c:…","c:…"]}],
 "stats":{"nodes_added":1,"nodes_removed":0,"nodes_matched":21,"edges_added":2,"edges_removed":1,"edges_kind_changed":1,
          "params_changed":7,"params_noise":31,"params_excluded":0,"events":9,"events_by_change_kind":{"dimension":5,"topology":3,"material":1},
          "events_by_confidence":{"high":7,"medium":2,"low":0}},
 "summary_text":"<≤2000자>","summary_status":"ok",
 "created_at":1756700000}
```

`base_blocked`·`target_blocked` 는 두 rr_state 의 `blocked` 이고 어느 하나라도 true 면 `POST /api/diffs` 는 409 `{gates}` 로 끝나 diff 행이 생기지 않는다.

### 3.3.2 cid — 항목 id 규칙

모든 항목은 `cid = 'c:' + sha1(layer + '|' + code_or_attr + '|' + key_a + '|' + key_b + '|' + attr)[:12]` 를 갖는다. `key_a`·`key_b` 는 dn(노드) 또는 정렬한 dn 쌍(엣지), 명명 치수면 `dim:<name>`, 롤업이면 `asm:<asm_key>`, 결과면 `dn|metric`. `attr` 은 파라메트릭 항목의 속성명, 나머지는 빈 문자열이다. dn 은 §2 대응 확정 후의 대표 nid 라 같은 두 스냅샷을 다시 diff 해도 cid 가 같고, 사람이 same-as 를 바꾸면 그 노드의 cid 만 바뀐다. `[c:<cid>]` 가 §4 cites 의 대상이며 `rr_claim_refs` 역색인의 키다.

### 3.3.3 구조층(structural)

| 배열 | 항목 필드 | 규칙 |
|---|---|---|
| node_changes | `{cid, op: added\|removed\|replaced\|split\|merged\|moved_in_tree, dn, nid_base, nid_target, ckey, label, kind, domain, neighborhood_1hop:[ckey…], correspondence_method, confidence}` | added = unmatched_target, removed = unmatched_base. replaced = removed X·added Y 가 1홉 이웃(tied·touching·interference·contact)을 ≥ 50% 공유하고 fuzzy 점수 0.5~0.7. split/merged = 1↔n 대응에서 지문 부피 합이 2% 안. moved_in_tree = 같은 dn 의 parent asm_key 가 다름 |
| edge_changes | `{cid, op: added\|removed\|kind_changed\|status_changed, eid_base, eid_target, dn_a, dn_b, ckey_a, ckey_b, kind_from, kind_to, rank_from, rank_to, rank_delta, status_from, status_to, cross_file, excluded_reason, confidence}` | 끝점 dn 을 사상한 뒤 kind_family 무관 정렬 쌍으로 잇는다. rank 는 interference 3 > tied 2 > touching 1 > clearance 0(StepForge compare_interfaces 규약, map_1). dyna `contact`·`scope`·`geometric`, load_path, ecad net 도 같은 배열에 kind_family 로 구분해 담는다. status_changed 는 kind 가 같고 status 만 다른 경우(원장 재적용 포함)로 의미 이벤트를 만들지 않는다 |
| orphans_delta | `{base:[dn], target:[dn], became_orphan:[dn], left_orphan:[dn]}` | clearance 제외 차수 0 |
| hierarchy_moves | node_changes 의 moved_in_tree 부분집합 | — |
| dyna | `{contacts_added:[cid], contacts_removed:[cid], scope_changed:[{cid, contact_index, pids_before, pids_after, dns_before, dns_after}]}` | scope 하이퍼엣지는 pid 집합 비교 |

### 3.3.4 파라메트릭층(parametric)과 변경 임계 v1

항목 공통 필드 `{cid, dn|eid|name, ckey(s), attr, before, after, delta, rel_delta, unit, flag, lower_bound, excluded_reason, size_pct, text}`. `flag ∈ changed | noise | incomparable | null_one_side`. `size_pct` 는 그 파트 volume 의 target 스냅샷 내 백분위(0~100)로 상위 표 병기용이다.

| attr | 절대 하한 | 상대 임계 | 판정(둘 다 만족해야 changed) | 비고 |
|---|---|---|---|---|
| bbox_def_dims[i] · centroid_world[i] · bbox_world_dims[i] | 0.02 mm | 0.5% | AND | centroid_world 는 world_transform 있을 때만 |
| min_dim(두께 근사) | 0.02 mm | 2% | AND | text 에 `(min_dim 근사)` |
| volume | — | 1% | rel | volume_null 이면 null_one_side |
| area | — | 1% | rel | |
| min_gap | 0.005 mm | 10% | AND | tol_parity false → excluded tol_differs |
| contact_area_est | 0.01·d²(d=작은 파트 bbox 대각) | 20% | AND | 밴드면적임을 text 에 명기, tol 종속 |
| band_width | 0.05·d | 20% | AND | tol 종속 |
| penetration_depth | 0.001 mm | — | abs | `lower_bound=true` 면 text 에 `≥` 와 `(lower_bound)`, 두 쪽 lower_bound 면 delta 는 만들되 `flag='incomparable'` |
| penetration_volume | 1e-6 mm³ | 5% | AND | 부울 경로 값만, 아니면 null_one_side |
| material.E · rho · sigy · nu | — | 1% | rel | 문자열 재료명 변경은 materials[] 로 |
| contact.fs | 0.01 | — | abs | dyna |
| n_elems | — | 20% | rel | `design_relevant=false` |
| worst_stress · worst_g · worst_disp | — | 5% | rel | result_parity 필요, 아니면 excluded |
| dims_named value | 이름별 `rr_dim_vocab.tol_abs` 있으면 그 값, 없으면 0.02 mm | 이름별 `tol_rel` 있으면 그 값, 없으면 1% | AND | ref 가 사라져 null 이면 null_one_side 이고 의미 이벤트 `dim.named_unmeasured` |

파라메트릭 항목의 `text` 는 정규 표기 `PLATE_1 bbox_dz 1.20→1.00 mm (−16.7%) [c:3fa2…]` 형식이며 §0.2.1 규칙 (4) 의 예와 같다. 상위 표는 두 순위를 병기한다 — `|delta|` 절대 상위 5 와 `|rel_delta|` 상대 상위 5 를 합쳐 중복 제거하고 각 줄에 `size_pct` 를 붙인다(미세 파트가 상대 순위만으로 상단을 독점하는 것을 막는다).

`materials[]` 는 `{cid, dn, ckey, field: name|material_norm|mid|keyword|match_basis, before, after}` 이고 `rollup_delta[]` 는 `{cid, asm_key, path_prefix, n_leaf:{before,after}, edges_internal:{before,after}, edges_external:{before,after}, orphan_leaf:{before,after}}` 다. `result_delta[]` 는 `{cid, dn, ckey, pid_before, pid_after, metric, before, after, delta, rel_delta, unit, case_key_before, case_key_after, kind, excluded_reason}` 다.

### 3.3.5 의미층(semantic) — 이벤트 코드표 v1

의미층은 '무엇이 어떻게 바뀌었나' 의 기술(記述) 분류다. 코드명은 방향 판단을 담지 않도록 중립 명사로만 짓는다(crit_18 — `weakened`·`thinned` 같은 이름은 좌석이 결론으로 읽는다). 이벤트 레코드는 다음과 같다.

```json
{"cid":"c:5b0e…","code":"iface.rank_down","change_kind":"topology",
 "subject":{"dns":["p:…","p:…"],"ckeys":["ck:…","ck:…"],"eids":{"base":"e:…","target":"e:…"},"names":["HINGE_PLATE_L","DISPLAY_PANEL"]},
 "subject_key":"ck:1a2b…|ck:9f8e…",
 "before":"tied","after":"touching","magnitude":{"value":-1,"unit":"rank","rel":null},
 "derived_from":["c:edge_changes…"],
 "neighborhood":{"k":1,"ckeys":["ck:…"]},
 "confidence":"high","design_relevant":true,"unconfirmed":false,"lower_bound":false,"excluded_reason":null,
 "text":"HINGE_PLATE_L↔DISPLAY_PANEL kind tied→touching (rank 2→1) min_gap=0.000→0.018 mm [c:5b0e…]"}
```

| code | change_kind | 전제·임계 | 비고 |
|---|---|---|---|
| part.added / part.removed | count | 구조층 unmatched | G2 pending 이면 의미층 전체 차단 |
| part.replaced | type | 구조층 replaced | confidence ≤ medium |
| part.split / part.merged | count | 구조층 split/merged | |
| part.resized | dimension | bbox_def_dims changed AND centroid_world Δ < 0.05 mm(또는 world 없음) | |
| part.thickness_changed | dimension(sub=thickness) | min_dim changed | text 에 `(min_dim 근사)` |
| part.moved | placement | bbox_def_dims 전부 noise AND centroid_world Δ ≥ max(0.05 mm, 0.002·diag) | world_transform_absent 면 만들지 않음 |
| part.rotated | placement | bbox_def_dims noise AND bbox_world_dims changed | 동일 |
| part.material_changed | material | materials[] 항목 또는 E/rho/sigy changed | |
| part.tree_moved | topology | hierarchy_moves | |
| iface.added / iface.removed | topology | edge_changes added/removed, kind_family ∈ mcad 4종 | rank ≥ 1 인 것만. clearance 의 등장·소멸은 `iface.clearance_appeared/cleared` 로 따로 낸다 |
| iface.clearance_appeared / iface.clearance_cleared | topology | clearance 엣지 added/removed | tol_differs 면 excluded |
| iface.rank_up / iface.rank_down | topology | kind_changed rank_delta > 0 / < 0 | interference 로의 상승은 아래 코드가 우선 |
| iface.interference_new / iface.interference_cleared | topology | kind_to = interference / kind_from = interference | `unconfirmed = (status=auto)` |
| iface.gap_changed | dimension(sub=gap) | edge_params min_gap changed | tol 종속 |
| iface.band_area_changed | dimension(sub=band_area) | contact_area_est changed | tol 종속 |
| iface.penetration_changed | dimension(sub=penetration) | penetration_depth changed | lower_bound 전파 |
| contact.added / contact.removed / contact.type_changed / contact.friction_changed / contact.scope_changed | topology / topology / contact_type / parameter / topology | dyna 구조·파라메트릭층 | |
| mesh.density_changed | discretization | n_elems changed | `design_relevant=false` |
| result.part_metric_shift | result | result_delta changed AND result_parity | metric 별 1건 |
| loadpath.edge_added / loadpath.edge_removed / loadpath.work_shift | load_path | energy_edges 구조·total_work rel ≥ 10% | result_parity 필요 |
| dim.named_changed | dimension(named) | dims_delta changed | `[d:<name>]` 병기 |
| dim.named_unmeasured | consistency | dims_delta null_one_side(ref 소실) | |
| asm.rollup_changed | topology | rollup_delta 의 edges_internal 또는 edges_external 변화 ≥ 1 | 서브어셈블리 수준 요약 |
| cross.bridge_stale | consistency | mcad 노드 part.resized/thickness_changed 인데 same_as 로 묶인 dyna pid 의 bbox·n_elems 가 전부 noise | 메시 미갱신 신호 |
| ecad.net_changed / ecad.component_moved / ecad.stackup_changed | electrical | 예약(어댑터 계약 이행 후) | |

confidence 규칙. `high` = 관련 대응이 ledger·pid_map·exact_path 이고 관련 엣지 status 가 auto 가 아님. `medium` = 대응이 fingerprint·name_norm 이거나 엣지 status=auto(interference 제외). `low` = 대응이 fuzzy(auto ≥0.9) 이거나 lower_bound 이거나 G4 fail 상태의 cross_file 엣지. `design_relevant=false` 는 mesh.density_changed 와 status_changed 유래 항목뿐이다.

합성 픽스처 6종(P2 통과 기준 (1)의 정의). `backend/tests/fixtures/diff_pairs/`. 각 쌍은 golden IR 에 한 가지 변형만 준 것이고 기대 이벤트는 정확히 그 1건, 나머지 항목은 noise 또는 없음이다.

| 쌍 | 변형 | 기대 이벤트 | 기대 구조·파라메트릭 |
|---|---|---|---|
| pair_add | 리프 1 추가(tied 1) | part.added 1, iface.added 1 | nodes_added 1, edges_added 1 |
| pair_remove | 리프 1 삭제 | part.removed 1, iface.removed n(그 리프의 rank≥1 엣지 수) | |
| pair_kind | tied → touching(min_gap 0.000→0.018) | iface.rank_down 1, iface.gap_changed 1 | kind_changed 1 |
| pair_thick | PLATE_1 bbox_dz 1.20→1.00 | part.thickness_changed 1, part.resized 0(min_dim 이 dz 이므로 thickness 가 우선) | node_params changed 1 |
| pair_mat | PLATE_1 material AL6061→AL7075 | part.material_changed 1 | materials 1 |
| pair_move | BRACKET_L world_transform 평행이동 2.0 mm | part.moved 1 | centroid_world changed 1, bbox_def noise |

self-diff(같은 스냅샷 둘) 는 이벤트 0·changed 0 이어야 한다.

### 3.3.6 comparability 와 excluded_reason

`excluded_reason ∈ tol_differs | tol_unknown | result_kind_differs | sim_params_differ | unit_scale | partial_scope | suspect_coords | null_one_side | sameas_pending | bridge_stale`. 제외된 항목은 diff_json 에 남고(수치도 남는다) 의미 이벤트를 만들지 않으며 summary_text 에는 `[제외] tol_differs 12건` 처럼 건수만 실린다. 브리프 E2·E3·E4 는 제외 항목을 싣지 않되 E0 에 제외 사유별 건수를 적는다(§5).

## 3.4 summary_text 생성 규칙(render.py)

### 3.4.1 정규 표기(canonical text)

render.py 는 IR 노드·엣지·signal·diff 항목마다 정규 표기 문자열 하나를 만든다. 이 문자열은 (1) 브리프 E1~E4·E9, (2) rr_state/rr_diff 의 `text` 필드, (3) §4 cites.quote 의 대조 원본, (4) RA 보고서 표의 셀에 똑같이 쓰인다. 자유조회 결과(MCP 원시 JSON)는 정규 표기가 아니므로 좌석이 거기서 수치를 옮기면 `tool:conv:` 참조로만 인정된다(§4.4).

형식 규칙. 길이 mm 소수 3자리(0.012 mm), 면적 mm² 소수 1자리, 부피 mm³ 유효 3자리, 비율 소수 2자리, 응력 MPa 정수, 변화는 `before→after unit (±rel%)`, 하한은 `≥값(lower_bound)`, 미확정은 `status=auto(미확정 초안)`, 결측은 `미측정`, 이름은 `label` 원문에 auto_named 면 `(auto_named)` 접미, 계면은 `A↔B`(정렬 무관, 표시는 name_norm 오름차순), 참조는 줄 끝에 `[p:…]`·`[e:…]`·`[c:…]`·`[d:…]`·`[sig:…]`·`[gate:G<n>]`·`[rule:…]`·`[warn:…]`.

### 3.4.2 pair summary_text 의 순서와 예산

총 ≤2000자. 섹션 순서 고정이고 섹션별 상한을 넘으면 그 섹션 안에서 뒤 항목을 `… 외 N건` 으로 접는다.

| 순서 | 섹션 | 내용 | 상한 |
|---|---|---|---|
| 1 | `[대상]` | base/target 라벨·snapshot_id[:8]·ir_hash[:12]·소스 앱 id·partial | 220자 |
| 2 | `[비교가능성]` | tol_parity·result_parity·unit·scope·coordinate, 제외 사유별 건수, G2 pending_n | 200자 |
| 3 | `[구조]` | `+N파트 −M파트 교체 r · 계면 +a −b · rank 상승 c 하락 d · 간섭 신규 e 해소 f · 고아 +g −h · 롤업 변화 i` 각 항목 뒤 대표 cid 1개 | 260자 |
| 4 | `[의미]` | change_kind 별 최대 5건 `code subject before→after (unit) [c:]`, confidence low 는 `(confidence=low)` 접미 | 700자 |
| 5 | `[치수]` | dims_delta 전부(명명 치수는 항상 실린다) + 파라메트릭 상위 표(절대 5·상대 5 병합, size_pct 병기) | 420자 |
| 6 | `[재료]` | materials 전부 | 100자 |
| 7 | `[결과]` | result_parity 면 result_delta 상위 5, 아니면 `결과 비교 제외(result_kind_differs)` | 160자 |
| 8 | `[씨앗]` | rr_diff.character_seed 태그 | 60자 |

snap summary_text 는 §3.2.7 의 10줄이다.

### 3.4.3 판단어 린터(judgement linter)

린터는 코드 생성 문장에만 적용된다. `«…»` 원문 인용, label·note·title·warnings.message 원문, 규칙의 why_it_matters/fix_hint, 태그 문자열(`char:`·`x:`), 도구·파일·앱 id 는 검사 대상이 아니다. 렌더러는 이 제외 구간을 문자열 조립 시점에 `«…»` 로 감싸 두므로 린터는 `«…»` 를 지우고 남는 텍스트만 본다.

어휘 사전은 `render.JUDGEMENT_LEXICON`(모듈 상수, 버전 'lex-1.0')이다. 항목은 `{id, pattern(정규식), allow(예외 정규식 목록)}` 이고 매칭은 정규식 단위다(부분 문자열이 아니다 — crit_11·crit_13 의 오작동 지적을 반영).

| id | pattern | allow(예외) |
|---|---|---|
| L01 | `위험` | — |
| L02 | `리스크` | `리스크\s?심사`, `risk-review`, `hwax-risk` |
| L03 | `개선` | — |
| L04 | `악화` | — |
| L05 | `안전(?!율\|계수\|_factor)` | `min_safety_factor`, `안전율`, `안전계수` |
| L06 | `문제` | — |
| L07 | `양호\|불량\|우수\|열악\|적절\|부적절\|바람직` | — |
| L08 | `취약\|강건\|튼튼\|허약` | — |
| L09 | `심각\|우려\|경고(?!\s?코드)` | `warning`(코드·enum 값), `WARNING`(DynaForge severity 원문) |
| L10 | `권장\|권고\|필요하\|해야\s?한다\|해야\s?함` | `재검사 필요`(StepForge note 원문은 이미 «» 안) |
| L11 | `과다\|과소\|부족\|충분` | — |
| L12 | `좋(다\|은\|아)\|나쁘\|나쁜` | — |
| L13 | `약화\|강화\|저하\|향상\|열화` | — |
| L14 | `결함\|오류\|실패\|성공` | `file_load_failed`(warn code), `failed`(잡 status enum), `success`(케이스 필드명) |
| L15 | `치명\|중대\|경미` | severity enum 값이 `severity=` 뒤에 오는 경우(`severity=(치명\|중대\|경미)`) |
| L16 | `OK\|FAIL\|PASS(?!_)` | `pass=(true\|false)`, `G\d (pass\|fail)`(게이트 표기), `judgement=` 뒤 |
| L17 | `추천\|제안\|판단\|결론\|평가` | `상태 평가`(문서 제목), `평가어` |
| L18 | `증가\|감소\|커짐\|작아짐` 은 허용어다(정량 방향, 판단 아님) — 사전에 없다 | — |

출력은 `{ok, lexicon_version, violations:[{section, line_no, token, id}]}` 다. 위반이 1건이라도 있으면 `render.summarize()` 는 `JudgementLintError` 를 던진다. 테스트(P1 (6)·P2 (6)·P5 (8))는 이 예외 0건을 검증한다. 운영 중 예외가 나면 코드 결함이므로 `summary_text=''`·`summary_status='lint_failed'` 로 행을 저장하고 로그에 violations 를 남기며, E1 은 그 타깃에서 표 항목(E2~E4)만으로 조립된다(브리프가 막히지는 않는다). 사전 버전은 `rr_states.state_json.lexicon_version`·`rr_diffs.diff_json.lexicon_version` 에 스탬프된다.

린터는 §5 의 prior_evidence 조립 문장(E0·E5·E6·E8 의 코드 생성 문장)에도 같은 상수로 적용된다. 좌석·의장 산문(§4)은 판단이 허용되므로 린터 대상이 아니다.

## 3.5 저장·조회·테스트

- `rr_states` 는 스냅샷당 1행이고 재계산은 `rule_version`·`seed_rules_version`·`state_version` 이 바뀔 때만 한다(같은 ir_hash 재계산은 바이트 동일). `feature_json` 은 `{names, values, known}` 만 따로 두어 kNN 조회가 state_json 을 파싱하지 않게 한다.
- `rr_diffs.diff_json` 은 전문이고 `rr_diff_events` 는 의미 이벤트 펼침 표(cid·code·change_kind·subject_key 인덱스)다. `GET /api/diffs/{id}?part=events` 는 펼침 표를, `?part=summary` 는 summary_text 와 comparability 만 돌려준다.
- `GET /api/refs/{ref}` 는 `sig:`·`c:`·`gate:`·`rule:` 도 해석해 원문 필드와 정규 표기를 돌려준다(§8).
- 테스트. (a) 게이트 픽스처 5케이스(§3.2.2). (b) 합성 쌍 6종 + self-diff(§3.3.5). (c) 임계 경계 테스트 — 각 attr 의 절대 하한·상대 임계 바로 아래/위 1쌍씩. (d) cid 안정성 — same-as 확정 전후 변경 노드 외 cid 불변. (e) 린터 — 사전 16항 각각의 양성 1문장·예외 1문장, `«…»` 안 위반어 통과. (f) 결정론 — 같은 입력 2회 바이트 동일. (g) 성능 — 노드 500·엣지 2000 합성에서 diff < 5 s, state < 2 s.

# §4 과제 평가 서술

이 절이 사용자가 가장 강조한 물음 — "그래프 diff 나 현재 과제 상태에 대한 평가를 어떤 식으로 정리해서 특정 과제에 대한 평가를 서술하고, 그 남겨놓은 데이터를 다음 과제에서 활용하거나 다른 connectivity 를 만들 때 사용할 수 있게 할 것인가" — 의 답이다. 답의 골자는 세 문장이다. (1) 서술은 문서가 아니라 원자(finding·gain·cross_domain·character_statement·open_item)이고, 문서(결정문·보고서·프로파일)는 원자를 코드가 조립한 뷰다. (2) 모든 원자는 §3 의 id 를 `cites` 로 달아야 저장·재사용 대상이 되고, 근거 등급은 그 cites 에서 코드가 산출한다. (3) 원자의 주체는 이름이 아니라 과제 무관 정규 키(`ckey`·`subject_key`, §0.1.2)라서 계보가 없는 과제·다른 connectivity 에서도 같은 부품·같은 계면의 서술이 회수된다.

## 4.1 서술 스택 L0~L4 와 생산 주체

| 층 | 이름 | 생산자 | 저장(§5) | 재사용 단위 | 판단 허용 |
|---|---|---|---|---|---|
| L0 | rr_ir · rr_state · rr_diff | 코드 | rr_snapshots · rr_states · rr_diffs · rr_diff_events | `[p:]`·`[e:]`·`[c:]`·`[d:]`·`sig:`·`gate:`·`rule:` | 없음(린터) |
| L1 | seat_opinion | 좌석(LLM 발언) + 코드 추출(재요약 없음) | rr_seat_opinions · AIDataHub `risk_review_opinion` | 발췌·stance·tool_calls·cited_refs | 있음 |
| L2 | 패널 결정문 + risk_spec | 의장(LLM) + parse_risk_spec | rr_panels.risk_spec_json · rr_findings · rr_character · rr_claim_refs · RA 패널 보고서 · AIDataHub `risk_review_panel` | finding·gain·cross_domain·character_statement·open_item | 있음 |
| L3 | rr_registry(타깃 등록부) | 코드(병합) | rr_registry · RA `risk_finding`·`assessment` | 클러스터·resolving_check 집합 | 없음(집계) — verdict 는 '후보' |
| L4 | character_profile(과제 성격 프로파일) | 코드(누적) + 사람 확정 | rr_character(status) · AIDataHub `project_character` · RA `design_trait`/`exhibits` | character_statement(태그) | 사람 확정만 |

L1·L2 는 판단해도 된다. 다음 과제에 재주입될 때 `prior_evidence`(§5)가 '검증 대상, 결론 아님' 프레이밍과 출처 태그를 붙이므로 헌법 P1 은 재주입 경로에서 지켜진다. L0 와 L3·L4 의 코드 생성 문장은 §3.4.3 린터를 통과해야 한다.

## 4.2 risk_spec 규격(schema 'risk_spec', version '1.0')

의장 결정문 산문 8항목(§6.6 `_CHAIR_ITEMS['risk-review']`) 뒤에 ```json 펜스로 낸다. 규칙은 sim_spec 선례(map_3) 세 가지 그대로다 — 값은 산문과 일치, 모르면 빈 문자열(지어내지 않는다), 다음 단계가 재파싱 없이 승계한다. 산문과 기계판독의 병기가 필수인 이유는 산문은 사람이 읽고 기계판독은 등록부·다음 브리프·KG 가 읽기 때문이며, 둘의 불일치는 파서가 `quality.flag=header_mismatch`(§4.2.4) 로 잡는다.

### 4.2.1 최상위 필드

```json
{"schema":"risk_spec","version":"1.0","taxonomy_version":"1.0",
 "scope":{"kind":"snap|diff","target_key":"diff:<hex32>","project_refs":["<project_id>"],
          "ir_refs":["<base snapshot_id>","<target snapshot_id>"],"diff_ref":"<diff_id>|null","ir_hash":"<target ir_hash>"},
 "findings":[{…§4.3…}],
 "gains":[{…§4.3, direction=improvement…}],
 "cross_domain":[{"id":"X1","from_domain":"mech","to_domain":"disp","path":"…","cites":[{"ref":"c:…","quote":"…"}],"raised_by":["mech-housing-structure"]}],
 "character":{"one_liner":"≤140자","facets":[{"facet":"intent","statements":[{…§4.6…}],"na_reason":null},"…8종…"]},
 "open_items":[{"id":"O1","question":"≤200자","resolving_check":{"kind":"tool|sim|test|field","ref":"report_part_risk(case=corner_45)"},"owner_domain":"sim"}],
 "coverage":{"seats":[{"key":"mech-housing-structure","domain":"mech","origin":"primary"}],"domains_seated":["mech","sim","xd","disp","rel"],"domains_missing":["pcb","pwr","rf","soc","passive","mem","cam","sh","std","material"]},
 "verdict":"go|conditional|no-go|undetermined",
 "verdict_conditions":["…"],
 "evidence_profile":{"tool":0,"card":0,"precedent":{"verified":0,"dismissed":0},"heuristic":0,"measured":0}}
```

| 필드 | 타입·규칙 | 산문 대응 항목 |
|---|---|---|
| scope | kind 는 target_key 접두와 일치해야 한다(불일치면 `spec_parse_failed`). ir_hash 는 target 스냅샷의 것 | (1) |
| findings[] · gains[] | §4.3 원자. id 는 `F<n>`·`G<n>` 패널 내 유일. gains 는 direction=improvement 로 고정하고 다르면 파서가 보정 | (3)·(4) |
| cross_domain[] | `{id X<n>, from_domain, to_domain, path(≤400자, 경로 서술), cites[], raised_by[]}`. from≠to 이어야 한다 | (6) |
| character | §4.6 character_narrative. facets 는 8종 순서 고정·전부 존재(없으면 파서가 `na_reason='좌석 미기재'` 보충) | (5) |
| open_items[] | `{id O<n>, question, resolving_check{kind, ref}, owner_domain}`. resolving_check.kind=tool 이면 ref 는 도구명(+인자 요지) | (7) |
| coverage | seats 는 실제 착석 키. 러너가 SSE `personas` 와 대조해 불일치면 `quality.flag=coverage_mismatch`(경고, §6) | (8) |
| verdict · verdict_conditions | 판정 후보. 사람이 `PUT /api/targets/{key}/verdict` 로 `verdict_final` 확정(§6) | (8) |
| evidence_profile | `{tool, card, precedent{verified, dismissed}, heuristic, measured}` 정수. 의장이 세되 코드가 seat_opinion 합계와 대조 | 헤더 |

### 4.2.2 parse_risk_spec(narrative.py, P0 산출물)

parseSimSpec 복제다. 순서는 (1) 결정문 텍스트에서 마지막 ```json 펜스를 찾아 파싱, (2) 없으면 텍스트 끝에서 역방향으로 마지막 균형 중괄호 블록을 파싱, (3) `schema=='risk_spec'` 이 아니면 실패, (4) 실패는 null 이고 비치명이다 — 패널은 done 으로 남되 `rr_panels.risk_spec_parsed=false`·`quality.flag=spec_parse_failed`, finding 0건, C2 조건(미해결 파싱 실패 패널 0)에 걸려 해결 대상이 된다 — 해결은 §6.9 의 절차(사용자가 decision 텍스트를 보정해 `POST /api/panels/{id}/complete` 로 파서만 재실행, 또는 '제외' 표기)이고 LLM 재실행은 없다. 파서는 앱 단일 구현(`narrative.py`)이고 MCP 경로(L2 오케스트레이터)는 결정문 텍스트를 `POST /api/panels/{id}/complete` 로 보내 같은 파서를 탄다(§8). 이것으로 gap_21 의 'P0 통과 기준이 P3 산출물에 의존' 모순을 닫는다 — P0 통과 기준 (6) 은 이 파서로 검증한다.

파싱 후 정규화(코드, 순서 고정).

1. enum 보정 — `direction·severity·judgement·detectability.level·evidence_grade·precedent·polarity·confidence·verdict·status` 가 목록 밖이면 값을 `invalid_enum[]` 에 보존하고 기본값(`neutral`·`경미`·`undetermined`·`unknown`·`경험칙`·`none`·`inference`·`low`·`undetermined`·`open`)으로 채운다.
2. 택소노미 매핑 — `mechanism`·`mechanism_detail`·`change_kind`·`trigger_condition` 을 `taxonomy.py` 의 동의어 사전(`synonyms{}` — 예 '간섭'→interface.interference, '낙하'→mechanical.drop_stress, 'CTE'→thermal.cte_mismatch)으로 정규화한다. 사전에 없으면 `mechanism_detail='unclassified'`·`mechanism_free=<원문>` 으로 저장하고 `rr_curation_queue(kind=unclassified_code)` 에 넣는다. 의장 프롬프트에 코드 목록을 주입하지 않는다(crit_14 — 주입 채널이 없고 예산을 잠식한다). 좌석 계약(§6.5)이 '메커니즘은 도메인 언어로 쓰되 한 단어로' 만 요구한다.
3. severity↔judgement 정합 — 매핑표(경미→OK|WARNING, 중대→WARNING|FAIL, 치명→FAIL) 밖 조합은 judgement 를 severity 쪽으로 보정하고 `parse_warnings[]` 에 남긴다. `sev3 ∈ 1|2|3` 정규화 컬럼을 채운다.
4. subject 해석 — `subject.names[]` 를 name_norm 으로 스코프 IR 에서 dn → ckey 로 해석해 `subject.ckeys[]` 를 채운다(의장이 ckey 를 직접 쓴 경우 존재 검증만). 1:N 이면 미해석. names 가 1개이고 파트로 해석되지 않으면 §2.7.4 규칙으로 정규화한 문자열이 스코프 스냅샷(pair 면 target)의 `rollups.by_assembly[].path_prefix` 와 일치하는지 본다 — 일치하면 `subject.asm_key` 를 채우고 subject_key 는 `asm:<asm_key>` 가 된다(의장이 `asm:` 접두로 직접 쓴 경우 존재 검증만). 전부 미해석이면 `subject_unresolved=true`·`subject_key=''`.
5. subject_key 산출(§4.3.2).
6. cites 검증(§4.4) — dangling·quote_mismatch 플래그, evidence_grade 자동 산출.
7. precedent 부여(§4.3.3).
8. feature_snapshot 동결(§4.3.4).
9. evidence_profile 대조(§4.2.4).
10. 전역 id 화 — `<panel_id>#F1` 형식으로 rr_findings.id, character statements 는 rr_character.id(uuid) 와 `<panel_id>#C1` 별칭.

### 4.2.3 결정문(산문) 과 risk_spec 의 병기 규칙

산문 (3)(4) 의 각 항목은 `F<n>`·`G<n>` 을 문두에 쓴다. 산문 (5) 의 facet 문장은 `C<n>` 을 문두에 쓴다. 파서는 산문에서 `^\s*[FGCXO]\d+` 를 정규식으로 뽑아 risk_spec id 집합과 대조하고, 산문에만 있고 spec 에 없는 id 는 `parse_warnings[]` 에 `prose_only_id` 로, spec 에만 있는 id 는 `spec_only_id` 로 남긴다. 어느 쪽도 파싱 실패는 아니다. RA 패널 보고서는 산문 그대로이고(엔진 저장, 무수정) 통합 보고서(§4.8)는 spec 에서 조립한다.

### 4.2.4 evidence_profile 대조(header_mismatch)

코드가 seat_opinion 들에서 `Σ tool_calls_ok`(tool), `Σ knowledge_hits_n`(card), 이번 패널 finding 중 `precedent.verified/dismissed` 집계, cites 가 비어 있거나 dangling 인 finding 수(heuristic), cites 에 `inc:`·`rpt:`(test) 가 있는 finding 수(measured) 를 계산해 의장 값과 비교한다. 어느 항이든 |차| > max(2, 0.3·코드값) 이면 `rr_panels.quality_json.flag` 에 `header_mismatch` 를 넣고 코드값을 `evidence_profile_computed` 로 병기한다. 보고서·브리프는 코드값을 쓴다.

## 4.3 finding — 서술 원자

### 4.3.1 필드 전체

| 필드 | 타입·enum | 규칙 |
|---|---|---|
| id | `F<n>` / `G<n>` → 저장 시 `<panel_id>#F<n>` | 패널 내 유일 |
| direction | `risk \| improvement \| neutral` | gains[] 는 improvement 고정 |
| domain | 택소노미 ① 15값 | raised_by 첫 좌석의 접두(`_dom_of`)와 다르면 parse_warnings |
| mechanism · mechanism_detail | 택소노미 ② `{thermal, mechanical, interface, electrical, material, process}` + detail | 정규화 실패 시 `unclassified` + `mechanism_free` |
| change_kind | 택소노미 ③ `dimension \| placement \| topology \| material \| type \| count \| discretization \| result \| load_path \| consistency \| electrical \| none` | snap 타깃은 `none` 이 기본 |
| subject | `{ckeys:[ck:…], names:[…], asm_key?}` | 파트 1개 또는 계면 2개 또는 명명 치수(names=['dim:<name>']) 또는 서브어셈블리 1개(names=['<asm 경로>'] 또는 `['asm:<asm_key>']`, 파서 4단계가 rollups.path_prefix 와 대조) |
| subject_key | §4.3.2 | 코드 산출 |
| trigger_condition | 택소노미 ④ `env.* \| load.* \| time.* \| mfg.* \| use.* \| none` + 자유 텍스트 `trigger_text`(≤120자) | 예 `load.drop`, `trigger_text='코너 1.0 m'` |
| severity · judgement · sev3 | ⑤ `경미\|중대\|치명` · `OK\|WARNING\|FAIL\|undetermined` · 1\|2\|3 | 매핑표 보정 |
| detectability | `{level: sim-detectable \| test-only \| field-only \| unknown, tool}` | sim-detectable 이면 tool 필수(없으면 unknown 으로 보정) |
| evidence_grade | ⑦ `측정 \| 문헌·규격 \| 도구예측 \| 경험칙` | 코드 산출(§4.4.3)이 의장 값을 덮는다. 의장 값은 `evidence_grade_claimed` 로 보존 |
| precedent | `in_range \| out_of_range \| none` | 코드 산출(§4.3.3) |
| cites | `[{ref, quote}]` | §4.4 |
| tool_calls | `[string]` 의장 기입(도구명+인자 요지) → 코드가 `tool:conv:<conv_id>#<idx>` 로 해석해 `tool_call_refs[]` 를 채운다 | 좌석은 activity 인덱스를 알 수 없으므로 코드가 좌석 키·도구명·라운드로 대응(crit_18) |
| claim | ≤600자 한 단락. 주어에 파트·계면 실명 | |
| warrant | ≤1200자. 왜 그 원천이 그 claim 을 지지하는가 | |
| resolving_check | `{kind: tool \| sim \| test \| field, ref}` | 등록부에서 문자열 집합으로 보존 |
| owner_domain | 15값 | 닫을 책임 도메인 |
| raised_by | `[agent_key]` ≥1 | SSE personas 집합 밖 키는 `parse_warnings` + 첫 키만 인정. 의장 종합이면 `['chair']` |
| contested_by · contest_note | `[agent_key]` · ≤300자 | 지정 반대석 기각 요구 기록. `delib-baseline-defender` 가 들어 있으면 등록부 contested +1 |
| status | `open` 고정(저장 시) | 이후 전이는 등록부·라벨(§4.7·§7) |
| 코드 부가 | `dangling:[ref]`, `quote_mismatch:[ref]`, `subject_unresolved`, `feature_snapshot{}`, `tool_call_refs[]`, `taxonomy_version`, `rule_version`, `planner_version`, `ir_version`, `diff_version` | |

### 4.3.2 subject_key 와 cluster_key(과제 무관성)

`subject_key` 는 finding 이 가리키는 주체의 과제 무관 키다(§0.1.2). 파트면 `ckey`, 계면이면 `rr_iface_alias` 로 별칭 정규화한 뒤 정렬한 무순서 쌍 `ckA|ckB`, 명명 치수면 `dim:<name>`(이름은 `rr_dim_vocab` 정규명), 서브어셈블리면 `asm:<asm_key>`(§2.7.4 정규화 접두 — '힌지 서브어셈블리 접합 밀도가 낮다' 처럼 파트 ≤2 로 적을 수 없는 finding 의 주체이며, §4.2.2 4단계에서 `rollups.by_assembly.path_prefix` 와 일치할 때만 부여되고 아니면 `subject_unresolved`). `asm:` 주체는 cluster_key·`rr_registry.subject_key`·`rr_claim_refs` 를 다른 형식과 똑같이 쓰고 E5 회수(§5.9.4 S_Z)·패턴 후보 계수에 들어간다. 과제 간에는 파일명·어셈블리명이 같을 때만 일치하므로 E5 줄에 `[경로: subject·asm]` 태그를 병기한다. ckey 는 `canonical_part_key`(name_norm_canon + geom_bucket + material_norm 의 해시, §2)라 프로젝트명·인스턴스 접미·자동명이 달라도 같은 부품이면 같은 값이 나온다 — gap_21 두 번째 항목('ckey 가 쌍 단위')의 수정이다.

`cluster_key = sha1(mechanism + '|' + mechanism_detail + '|' + subject_key + '|' + change_kind)[:12]`. 도메인·ir_refs·좌석은 키에 넣지 않는다(crit_19 — 좌석마다 다르게 붙는 ir_refs 를 키에 넣으면 같은 리스크가 흩어져 support 가 1 에 머문다). `subject_unresolved` 인 finding 은 subject_key='' 로 클러스터되되 등록부 행에 `weak_subject=true` 가 붙고 E5 회수·패턴 후보 계수에서 제외된다.

### 4.3.3 precedent 부여

finding.cites 가 가리키는 IR 속성값(§4.3.4 feature_snapshot) 중 feature_vector 22차원과 대응하는 값(예 min_gap·penetration_depth·bbox·volume)이 있으면 코퍼스(corpus_n ≥ 5) [min, max] 와 대조해 하나라도 밖이면 `out_of_range`, 전부 안이면 `in_range`, corpus_n < 5 이거나 대응 값이 없으면 `none`. `out_of_range` 는 evidence_grade 를 바꾸지 않고 별도 표기다(선례 없음은 근거 약화가 아니라 '첫 사례' 사실이다). 저장 시 `precedent_corpus_n` 을 병기한다.

### 4.3.4 feature_snapshot

cites 의 `[p:]`·`[e:]`·`[c:]`·`[d:]`·`sig:` 가 가리키는 원천 값을 `{ref: {attr: value, unit}}` 로 finding_json 안에 복사한다. IR 이 재추출되어 nid 가 바뀌거나 스냅샷이 바뀌어도 '당시 수치' 가 남고, §7 규칙 자동 초안(confirmed 범위 [min,max])과 라벨 매칭의 재료가 된다. 복사 상한은 ref 당 12 속성·finding 당 40 속성이다.

## 4.4 cites — 근거 링크 규약

### 4.4.1 문법과 존재 검증

`cites[] = [{ref, quote}]`. ref 는 §0.2.1 문법이고 JSON 안에서는 대괄호 없이 쓴다(파서는 대괄호 유무를 모두 받는다). 검증 스코프는 타깃이 가리키는 스냅샷(pair 면 base·target 둘 다)·diff·rr_state·해당 대화의 activity·브리프에 실린 narr/reg/card 다.

| ref 종류 | 해석 | 실패 시 |
|---|---|---|
| `p:` `e:` `c:` `d:` `sig:` `gate:` `rule:` `warn:` | 스코프 IR·diff·state 조회 | dangling |
| `name:A\|B` | name_norm(A), name_norm(B) → 스코프 IR 에서 nid 쌍 → eid. 어느 쪽이 다의(같은 name_norm 노드 2개 이상)면 실패 | dangling(`name_ambiguous`) |
| `tool:<call_id>` | rr_snapshot_calls | dangling |
| `tool:conv:<conv_id>#<idx>` | conv_store activity[idx] 존재 + 그 항목의 persona 가 raised_by 에 속함 | dangling |
| `card:<record_id>` | AIDataHub get_record 존재(캐시 24h) | dangling |
| `narr:` `reg:` | 이번 패널 브리프(E5·E6·E7)에 실린 id 집합에 속하는지 | dangling(`not_in_brief`) — 지어낸 선례 차단 |
| `rpt:` `inc:` | RA get_report / get_object 존재 | dangling |

dangling 은 cites 를 버리지 않고 `dangling:[ref]` 에 보존한다(정보 손실 없음, 사람이 나중에 고칠 수 있다).

### 4.4.2 quote 대조(수치 축어)

`quote` 는 정규 표기 문자열(§3.4.1)을 축어로 담아야 한다. 검증은 두 단계다. (1) claim·warrant 텍스트의 수치 토큰(정규식 `[-+]?\d+(\.\d+)?\s?(mm|mm²|mm³|MPa|G|%)?`)이 quote 안에 문자 그대로 있어야 한다. (2) quote 가 그 ref 의 정규 표기와 일치해야 한다 — 코드가 ref 로 정규 표기를 다시 만들어 `quote` 가 그 문자열의 부분열인지 본다(crit_18 — quote 가 좌석이 쓴 문자열이라 자기참조 검사가 된다는 지적의 해소). `tool:conv:` 참조는 정규 표기가 없으므로 (2) 를 activity `result_preview` 원문 부분열 검사로 대신한다. (1) 실패는 `quote_mismatch:[ref]`, (2) 실패는 `quote_mismatch` 와 함께 그 cite 의 등급 기여를 없앤다.

### 4.4.3 evidence_grade 자동 산출

cites 중 dangling·quote_mismatch 가 아닌 것만 센다. 등급은 아래 표의 첫 행부터 순서대로 판정한다. DynaForge 결과 오버레이(`dyna:rpt:`·`sig:results.*`·result_delta `[c:]`)는 실행된 해석의 수치이지만 실측이 아니므로 열충격 선례(예측 vs 실측)와 같은 선에서 `도구예측` 이다. `측정` 은 RA `inc:` 와 test_run 문서 `rpt:` 만이다.

| cites 에 존재 | evidence_grade |
|---|---|
| `inc:` 또는 RA test_run 문서 `rpt:` | 측정 |
| (위 없음) `card:`(standard·paper·checklist·lessons_learned) | 문헌·규격 |
| (위 없음) `tool:`·`sig:`·`c:`·`e:`·`p:`·`d:`·`rule:`·`dyna:rpt:` | 도구예측 |
| 없음 또는 전부 dangling/quote_mismatch | 경험칙 |

의장이 적은 값이 더 높으면 코드값으로 내리고 `evidence_grade_claimed` 에 보존한다. 더 낮으면 의장 값을 존중한다(스스로 낮춘 것은 정보다).

### 4.4.4 rr_claim_refs 역색인

저장 시 finding·gain·cross_domain·character_statement·open_item 의 모든 cites 를 `rr_claim_refs(claim_uid, ref_type, ref, quote)` 에 펼친다. claim_uid 는 `<panel_id>#F1` 같은 전역 id 다. `GET /api/refs/{ref}` 와 `risk_claims_for_ref(ref)` 가 이 표를 조인해 "이 엣지에 대해 누가 뭐라 했나" 를 돌려준다. ref 가 `e:`·`p:` 이면 dn·ckey 로 확장해 다른 스냅샷의 같은 부품 claim 도 함께 돌려준다(§5).

## 4.5 seat_opinion — 좌석 1석 × 타깃 1개의 의견 레코드

코드 추출이며 LLM 재요약이 없다(P1). 좌석의 정성 서술은 좌석 발언 JSON 뒤에 별도 펜스로 받지 않는다 — 두 엔진의 좌석 턴은 '라운드당 JSON 객체 하나' 계약이고 turn.say 는 클립된 합성문이라 별도 JSON 이 도달할 자리가 없다(crit_16·crit_18 로 확인). 좌석의 성격 서술은 의장이 risk_spec.character 의 statements[].by 로 좌석 키를 병기해 담고(§4.6), seat_opinion 은 발언 발췌·입장·도구 회계·인용 목록만 갖는다.

```json
{"opinion_id":"<hex32>","target_key":"diff:…","panel_id":"…","agent_key":"mech-housing-structure","domain":"mech","origin":"primary",
 "cycle":1,
 "model":"<rr_panels.model_json.model 사본 — D6>",
 "turns":[{"round":1,"say_excerpt":"≤2000자","position":"…","stance":"conditional","non_negotiable":"…"},
          {"round":2,"…":"…"},{"round":3,"…":"…"}],
 "final_stance":"conditional",
 "tool_calls":[{"tool":"list_interfaces","args_gist":"kind=interference","ok":true,"activity_idx":7,"round":1}],
 "tool_calls_n":3,"tool_calls_ok":2,"knowledge_hits_n":2,
 "cited_refs":["e:9a1f3c2b0d4e","c:5b0e11aa22bb","name:UTG|HOUSING_FRONT","d:utg_edge_gap"],
 "cited_refs_resolved":["e:9a1f3c2b0d4e","c:5b0e11aa22bb","e:41d2c0ffee11","d:utg_edge_gap"],
 "cited_ckeys":["ck:3f9a2b1c0d4e","ck:aa10bb20cc30"],
 "quality":{"used_tool":true,"cited_ir":true,"grade_min":"도구예측","dangling_n":0},
 "raised_finding_ids":["<panel_id>#F1","<panel_id>#G1"],
 "character_sentences":["…정규식 `성격|성향|철학|경향|의도` 를 포함한 발언 문장 ≤5, 각 ≤240자…"],
 "excerpt_for_rag":"≤1500자 — 1R say_excerpt 앞 900자 + 최종 라운드 position 앞 600자"}
```

추출 규칙.

- `turns` 는 SSE `turn` 이벤트(§0.2.3)에서 좌석 키가 일치하는 것을 라운드 순으로 담고, `say_excerpt` 는 conv_store persona 메시지 content 를 2000자에서 자른다.
- `tool_calls_n` 은 `status.step` 이 `'<key> 조회: <tool>'` 인 이벤트 수, `tool_calls_ok` 는 `evidence.source` 가 `'<key> · <tool>'` 인 이벤트 수다(gap_21 다섯 번째 항목의 규약). 입력 소스는 러너가 직접 읽은 SSE 스트림 또는 `POST /api/panels/{id}/complete` 의 `events[]`(§8.2.3, L2 오케스트레이터·재제출 호출자가 SSE 를 읽으며 캡처)이고 두 소스에 같은 정규식(§6.7 7단계)을 쓴다. 둘 다 없으면 포털 `GET /agent/conversations/{cid}`(러너 자격 PAT) 응답의 `meta.activity`(tool 붙은 status 만 보존, evidence 미보존 — routes.py:891-899)로 `tool_calls_n` 만 복원하고 `tool_calls_ok=null`·`used_tool=null` 로 둔다(§6.11 분모 제외). `used_tool = tool_calls_ok ≥ 1`(null 이면 null). 지정 도구(delib_opts.tools) 결과는 좌석 귀속이 불가하므로 세지 않는다. `activity_idx` 는 conv_store activity 에서 같은 좌석·같은 도구·같은 라운드의 항목을 시각 순으로 대응해 채우고, 대응 실패면 null.
- `cited_refs` 는 세 라운드 발언 전체에서 정규식으로 뽑는다 — `\[?(p|e|c|d):[0-9a-f]{12}\]?` · `\[?d:[A-Za-z0-9_]+\]?` · `sig:[A-Za-z0-9_.\[\]]+` · `name:[^\s|]+\|[^\s\]]+` · `narr:`·`reg:`·`card:`·`rule:`·`gate:G\d`. `cited_refs_resolved` 는 name: 을 eid 로 해석한 결과(다의는 제외)이고 `cited_ckeys` 는 resolved 를 dn → ckey 로 확장한 집합이다. `cited_ir = |cited_refs_resolved ∩ {p:,e:,c:,d:,sig:}| ≥ 1`.
- `grade_min` 은 이 좌석이 raised_by 인 finding 들의 evidence_grade 최솟값(없으면 null).
- `model` 은 패널 행 `rr_panels.model_json.model` 의 사본이다(D6 — 좌석마다 다르지 않고 `opinion_json` 안에만 있으며 별도 컬럼은 없다). 브리프 E0 의 첫 줄 헤더에 `model=<name>` 토큰을 덧붙여 다음 과제가 어느 모델의 의견인지 알게 한다(§5.6.1 E0 라인 상한 안, 별도 항목 아님).
- `raised_finding_ids` 는 risk_spec 의 raised_by 에 이 좌석 키가 든 finding·gain 의 전역 id 다. 반대석은 raised_by 가 아니라 contested_by 에 나타나므로 `contested_finding_ids` 를 따로 둔다.
- `character_sentences` 는 정규식 발췌이고 statements 가 아니다(의장이 C<n> 으로 올린 것만 rr_character 에 간다). E7 의 좌석 발췌(좌석 줄 ≤220자, 참조 접두를 뺀 발췌 ≈125자)는 이 필드와 excerpt_for_rag 에서 자른다(§5).

커버리지 종결 판정(§6)에 쓰는 값은 `turns 수 · final_stance · used_tool · cited_refs≠∅` 네 가지다. `carried` 조건(§0.1.5)의 `cited_refs ≠ ∅` 는 `cited_refs_resolved ≠ ∅` 로 판정한다 — 인용을 하나도 못 단 좌석이 교집합 ∅ 로 자동 면제되는 구멍(crit_19)을 막는다.

AIDataHub `risk_review_opinion` 레코드(§5 가 doc_type 을 정의)의 7섹션 매핑은 다음과 같고 본문은 전부 원문 발췌다.

| 섹션 id | 제목 | 내용(코드 조립) |
|---|---|---|
| 1 | 대상과 변화 요약 | 타깃 헤더 + summary_text 앞 600자 |
| 2 | 관점(도메인) 평가 | turns[round=1].say_excerpt |
| 3 | 리스크 목록 | raised_finding_ids 중 direction=risk 를 3.1, 3.2… 로 `[{sev3}] {mechanism.detail} — {claim} / 근거 {evidence_grade}: {warrant 앞 400자} / 닫는 확인: {resolving_check} / cites {refs}` |
| 4 | 개선되는 점 | direction=improvement 동일 형식 |
| 5 | 권고·추가 확인 | 최종 라운드 position + open_items 중 owner_domain 일치 항목 |
| 6 | 과제 성격(정성) | risk_spec.character 에서 by 에 이 좌석이 든 statements 원문 + character_sentences |
| 7 | 반박·소수의견 | contested_finding_ids 와 contest_note, 이 좌석을 인용한 타 좌석 2R 발언 발췌 ≤800자 |

섹션 제목 문자열은 §5.4.1 `expected_sections` 와 바이트 동일하고, 상한·조립 세부는 §5.4.3 이 정본이다.

## 4.6 character_narrative — 과제 성격 서술(정성 특징이 살아남는 자리)

숫자 diff 만으로는 "이 과제가 어떤 과제인가" 가 드러나지 않는다. character_narrative 는 그 물음에 답하는 자리이고, 패널 단위로 의장이 risk_spec.character 에 낸다. 구조는 `{one_liner, facets[8]}` 이고 facet 마다 `statements[]` 와 `na_reason` 을 갖는다(§0.1.3). 각 statement 는 통제 어휘 태그 + 자유 문장 + cites 3요소이며, 문장은 판단해도 되지만 근거 없는 문장은 서술이 아니라 가설(`polarity=hypothesis`)이다.

### 4.6.1 statement 필드

```json
{"id":"C3","facet":"vulnerability",
 "text":"≤240자 한 문장. 주어에 파트·계면 실명",
 "polarity":"observation|inference|hypothesis",
 "by":["disp-utg-cover","mech-housing-structure"],
 "cites":[{"ref":"c:7d21…","quote":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%)"}],
 "tags":["char:interface:utg_housing_front","char:tolerance:tight"],
 "confidence":"high|medium|low"}
```

`by` 는 그 문장을 낸 좌석 키 배열이다(의장 종합이면 `['chair']`). `confidence` 는 LLM 자기보고라 프로파일 우선순위에 쓰지 않는다(crit_14) — 정렬은 support(지지 패널 수)·evidence_grade 순이다. `tags` 는 통제 어휘(§4.6.3) 또는 `x:` 자유 제안(서술당 ≤3)이다.

### 4.6.2 facet 8종 — 묻는 것·최소 근거·작성 규칙·na_reason

| facet | 묻는 것 | 최소 근거 ref 종류(≥1) | 작성 규칙(파서가 검사) | na_reason 자동 부여 조건 |
|---|---|---|---|---|
| intent 설계 의도 | 이 구조가 무엇을 이루려 하는가(박형·강성·열경로·낙하 강건·경량·서비스성) | `sig:`·`p:`·`e:`·`d:`·`c:` | 의도는 추론이므로 polarity=inference 기본, 근거는 '무엇이 그렇게 보이게 하는가' | statements 0 → '좌석 미기재' |
| constraint 제약 | 무엇이 설계를 가두는가(공간·재료·공정·플랫폼·규격) | `d:`·`p:`·`warn:`·`card:`·`narr:` | 치수·bbox·재료 지정을 축어 인용. 조직 관행은 `card:` 또는 `tool:` | 동일 |
| anomaly 이례성 | 코퍼스·관행 대비 무엇이 특이한가 | `sig:`(precedent out_of_range)·`warn:`·`c:` | corpus_n < 5 이면 코퍼스 대비는 쓸 수 없고 warnings·규칙 대비만 | corpus_n<5 이고 warn·rule 인용 없음 → '비교 불가(코퍼스 n<5)' |
| lineage 계보 | 전임 과제와 무엇이 같고 다른가 | pair: `c:`·`d:`, snap: `narr:`·`reg:`(E5·E6 에 실린 것) | pair 스코프는 `c:` 인용 ≥1 필수 | snap 이고 E5·E6 이 비었으면 '선행 과제 미지정' |
| vulnerability 취약 계면·경로 | 어디가 약한가 | `e:`·`c:`·`sig:top.*`·`sig:results.*` | 계면·파트 실명 + 수치 축어. 이 facet 의 statement 는 findings[] 중 하나 이상과 cites 를 공유해야 한다 | 공유 없음 → '리스크 항목과 미연결' |
| strength 강점 | 어디가 강건한가·변경으로 좋아진 것 | `e:`·`c:`·`sig:`·`d:` | vulnerability 와 대칭. gains[] 와 cites 공유 ≥1 | gains 0 이면 '개선 항목 없음' — 그 자체가 반대석 지표(§6) |
| tradeoff 맞교환 | 무엇을 얻고 무엇을 내줬나 | `c:`·`d:` | statements ≥2, 두 statement 의 cites 가 서로 다른 cid 를 포함, 그 cid 집합이 gains[].cites 와 findings[].cites 양쪽과 각각 ≥1 교집합 | 미충족 → '단면만 기술' |
| unknown 미지 | 판단 못 한 것과 닫는 방법 | `gate:`·`sig:`(known=false)·missing 플래그·`warn:` | open_items 와 1:1 대응(statement 마다 `O<n>` 을 text 에 병기) | open_items 0 → '미지 항목 없음' (허용, 단 ecad_absent 면 파서가 unknown 에 자동 statement `ECAD 부재로 pcb·pwr·rf·soc·passive·mem 관점 미평가 [gate:…]` 를 by=['code'] 로 추가) |

facet 8종은 전부 존재해야 한다. 파서는 누락 facet 을 `na_reason='좌석 미기재'` 로 보충하고 `quality_json.facets_filled = n/8` 을 기록한다. 8 facet 중 5 미만이 채워진 패널은 `quality.flag=low_ir_cite` 와 별개로 지표 `facets_filled` 가 C2 통합 보고서 표에 실린다(실패가 아니라 표기).

### 4.6.3 성격 통제 어휘 `character-vocab.v1.json`

```json
{"version":"vocab-1.0",
 "axes":{
  "char:structure":["multi_file_assembly","adhesive_dependent","rigid_frame_load_path","thin_stack","fastener_dense","flex_dominant","foldable_hinge","sandwich","wound","stacked"],
  "char:interface":"<alias from rr_iface_alias or name_norm_a_name_norm_b>",
  "char:tolerance":["tight","moderate","loose"],
  "char:maturity":["auto_iface_high","confirmed","anon_names_high","ledger_applied"],
  "char:analysis":["no_dyna","dyna_structure_only","dyna_with_results","ecad_absent","ecad_present"],
  "char:change_style":["dimension_tuning","topology_change","material_swap","placement_shift","mixed"],
  "char:philosophy":["mass_first","stiffness_first","thermal_first","cost_first","serviceability_first","thin_first","drop_first","yield_first"]},
 "seed_axes":["char:structure","char:interface","char:tolerance","char:maturity","char:analysis","char:change_style"],
 "seat_only_axes":["char:philosophy"],
 "free_prefix":"x:","free_max_per_narrative":3,
 "promote":{"targets":3,"panels":2}}
```

규칙. (1) 어휘 밖 값은 `x:` 접두로 옮긴다(파서 보정). (2) `x:<value>` 가 서로 다른 타깃 3 이상·패널 2 이상에서 같은 값으로 나오면 `rr_curation_queue(kind=x_tag_promote)` 에 올라가고 사람이 승인하면 어휘 마이너 버전이 오른다(§7). (3) 태그 하나당 그 태그를 단 statement 가 ≥1 이어야 유지된다(태그만 있고 문장이 없으면 태그를 지운다). (4) `char:interface:*` 값은 rr_iface_alias 에 별칭이 있으면 그것으로 정규화한다.

### 4.6.4 character_profile 합성(character.py)

과제 단위 프로파일은 `rr_character(id, project_id, facet, tag, statement, polarity, cites_json, by, first_target_key, support_panels, support_targets, status, superseded_by)` 행의 집합이다. status 는 `seed → panel → confirmed`(또는 `superseded`) 로만 오른다.

1. seed(L0) — rr_state.character_seed 마다 행 1개(`facet` 은 축 매핑표 structure→intent, interface→vulnerability, tolerance→constraint, maturity→unknown, analysis→unknown, change_style→lineage, by=['code']).
2. panel(L2) — 행 단위는 statement 1건이다. `tag` 컬럼은 대표 태그(statement `tags[]` 중 통제 어휘(`char:` 접두) 첫 항목, 없으면 NULL)이고 전체 태그는 `tags_json`(통제 어휘 + `x:` 자유 태그, 순서 보존)에 둔다 — 태그가 2개인 문장도 행은 1개다. 병합은 `(project_id, facet, 대표 tag)` 가 같고 **대표 tag 가 NULL 이 아닐 때**만 한다 — 그 행이 있으면 `support_panels+1`(같은 타깃이면 support_targets 는 그대로), 이후 문장은 `variants_json[]` 에 축어 보존하고 `tags_json` 은 합집합(순서 보존)으로 갱신하며, 없으면 새 행(statement 원문은 첫 문장). 무태그 문장(§4.9 C6·C8 처럼 `tags:[]`)은 병합하지 않고 각각 새 행으로 두며 `support_panels=1`·`support_targets=1` 로 시작한다(무태그 문장끼리 한 행으로 합쳐지지 않는다). polarity 가 갈리면 `dissent_json[]` 에 보존한다(다수결로 지우지 않는다 — crit_13·crit_18). 병합 조건에 임베딩 유사도를 쓰지 않는다(e5 절대값 비교 금지).
3. confirmed — 사람이 ProjectPage 에서 확정. `superseded` 는 사람이 다른 행을 우선으로 지정할 때만.

프로파일 표시·재사용 순서는 `status(confirmed > panel > seed) → support_panels → evidence_grade(cites 로 산출) → 최신` 이고 confidence 는 쓰지 않는다. AIDataHub `project_character` 1레코드/과제 UPSERT 와 RA `design_trait`+`exhibits(support, origin)` 반영은 §5 다. E6 에 실리는 것은 `status=confirmed` 또는 `panel(support_panels ≥ 2)` 상위 3 이다(§0.1.4).

## 4.7 등록부 병합(rr_registry)과 verdict 집계

### 4.7.1 병합 규칙(registry.py, 패널 완료마다 재계산·멱등)

- 입력 = 타깃의 모든 패널 finding·gain(status 무관).
- 클러스터 = cluster_key(§4.3.2) 동일. 행 `{target_key, cluster_key, merged_json, support, contested, severity, judgement, evidence_grade, precedent, status, verified_by_json, weak_subject, priority}`.
- `severity` = max(경미<중대<치명), `judgement` = 최악(FAIL > WARNING > undetermined > OK), `support` = 제기 패널 수(같은 패널의 중복 finding 은 1), `contested` = contested_by 에 `delib-baseline-defender` 가 든 finding 수, `evidence_grade` = 최고 등급, `precedent` = 최빈(동률이면 out_of_range 우선), `resolving_checks` = `{kind}:{ref}` 문자열 집합(중복 제거·정렬), `direction` = 최빈(risk 와 improvement 가 같은 클러스터에 섞이면 두 행으로 분리한다 — direction 을 cluster_key 에 넣지 않되 병합 시 분리).
- `merged_json` 은 대표 claim(evidence_grade 최고 → support 최고 → 최신 순 첫 finding 의 원문)·`member_ids[]`·`raised_by 합집합`·`contest_notes[]`·`cites 합집합`·`feature_snapshot 합집합` 을 담는다.
- `priority`(정렬용, 결정론) = sev3 × w_det × w_grade. w_det = field-only 3 · test-only 2 · unknown 2 · sim-detectable 1. w_grade = 측정 1.0 · 도구예측 0.9 · 문헌·규격 0.8 · 경험칙 0.6. contested 이면 ×0.8. 이 값은 표 정렬에만 쓰고 판정에 쓰지 않는다.
- `status` 초기값 open. `verified`·`dismissed` 는 라벨(§7) 또는 사람 UI(`PUT /api/registry/{cluster}/status`)로만, `mitigated` 는 사람 UI 로만(같은 엔드포인트가 값 `mitigated` 를 받는다 — §8 에 표기), `superseded` 는 §4.8.
- **타깃별 기여 재계산(멱등).** `registry.merge(target)` 는 이 타깃의 클러스터를 `(change_kind, mechanism, mechanism_detail)` 로 묶어 `rr_delta_contrib(change_kind, mechanism, mechanism_detail, target_key)` 행을 `n_raised = Σ support(direction=risk)`, `n_improvement = Σ support(direction=improvement)`, `sev_hist_json`, `resolving_checks_json` 값으로 UPSERT 한다(`INSERT … ON CONFLICT DO UPDATE`, 이 타깃의 이전 기여를 덮어쓴다). 같은 트랜잭션에서 영향받은 조합의 `rr_delta_priors` 행을 `n_raised = Σ contrib.n_raised`, `n_targets = COUNT(DISTINCT target_key)`, `n_improvement = Σ`, `sev_hist_json` 합, `top_resolving_checks_json` 빈도 상위 3 으로 **재합산**한다(증분 `+=` 없음). 그래서 패널 완료마다 병합을 다시 돌려도 support 가 중복 가산되지 않고 E8 의 분모·'패턴 후보' 임계(타깃 ≥3)가 하루 동안 틀린 값을 들지 않는다. `n_verified·n_dismissed` 는 §7.4 라벨 훅이 유지하고 야간 정합 검사가 `rr_labels` 로 대조한다. `change_kind ∈ {discretization, none}` 은 기여 행을 만들지 않는다.

### 4.7.2 verdict 후보 집계(코드) 와 사람 확정

| 조건(등록부 status ∈ open·verified 만 계산) | 후보 |
|---|---|
| judgement=FAIL 클러스터 ≥1 이고 그 클러스터가 contested 가 아님(contested < support) | no-go |
| 위 아님 AND WARNING 클러스터 ≥1 | conditional |
| 위 아님 AND 모든 클러스터 OK | go |
| 클러스터의 evidence_grade 가 전부 경험칙이거나 undetermined 가 과반 | undetermined(위 판정보다 우선) |

집계는 '후보' 다. 타깃 화면에서 사람이 `verdict_final` 을 확정하며 자동 승인은 없다. 패널마다 의장이 낸 verdict 는 `rr_panels.risk_spec_json.verdict` 에 남고 통합 보고서 minutes 에 패널별로 나열된다.

### 4.7.3 통합 보고서 블록(코드 조립, RA `deliberation` 템플릿, 레벨 상승마다 새 버전)

| 블록 | 내용 |
|---|---|
| background(rich_text, 1900자 분할) | 타깃 헤더·소스 id·게이트 표·comparability·summary_text 원문·완결 레벨(C1/C2/C3)·미착석 N명(C3 미달) 배지 |
| results(rich_text 표, 1900자 분할) | (a) 등록부 표 — priority 순 `cluster_key · direction · domain · mechanism.detail · change_kind · subject(names) · severity/judgement · evidence_grade · precedent · support/contested · status · 대표 claim 앞 160자 · cites 상위 3`. (b) 개선 등록부(direction=improvement) 같은 형식. (c) 과제 성격 — facet 8 순서로 `status(confirmed>panel>seed)` 상위 문장 각 ≤2, 문장마다 `by`·cites·태그. (d) 교차 도메인 X 항목 |
| recommendation(bulleted_list) | verdict 후보·verdict_final(있으면)·verdict_conditions 합집합·resolving_checks 집합(kind 별)·open_items 병합(중복 제거) |
| minutes(rich_text) | 패널 목록(panel_no·conv_id·report_id·좌석·origin·tool_calls_ok 합·반대석 기각 수·verdict)·커버리지 도메인×상태 카운트·품질 플래그 |

tags 는 §0.2.2 통합 규약, entity_ids 는 `[project, design_snapshot(s), design_diff?, assessment…]`(RA 객체가 있을 때만, 없으면 생략하고 external_sync 표기).

## 4.8 스냅샷 변경 시 무효화 규칙

스냅샷은 불변이고 서술 원자는 타깃에 묶여 있으므로 '무효화' 는 원자를 고치는 것이 아니라 새 타깃에서 무엇을 승계하고 무엇을 다시 묻는가를 정하는 규칙이다. 판정 기준은 nid 변경이 아니라 '인용 주체에 변경이 있었는가' 다(crit_18 — nid 는 path 해시라 두께가 절반이 돼도 그대로다).

1. 새 타깃 T′(같은 과제, 스냅샷 S′ 또는 diff(S, S′))가 생기면 옛 타깃 T 는 `superseded_by=T′` 로 닫힌다(§6). T 의 rr_findings·rr_registry·rr_seat_opinions 는 그대로 남는다.
2. 코드가 `diff(S, S′)`(있으면 재사용, 없으면 생성) 에서 `changed_ckeys` = node_changes ∪ edge_changes(끝점) ∪ parametric changed(design_relevant) ∪ dims_delta changed 의 ckey 집합을 만든다. `changed_ckeys` 와 대조 상대(`cited_ckeys`·등록부 `subject_ckeys`·member cites 의 ckey)는 모두 `resolve_ckey()`(§5.9.1, merged_into 끝까지 해석)를 거친 **유효 ckey** 로 비교한다 — base 스냅샷 S 의 노드 ckey 와 target S′ 의 계산 ckey 가 §2.7.3 자동 승계로 병합돼 있으면 양쪽이 같은 base 유효 ckey 로 해석되므로 stale·carried 판정이 어느 스냅샷 키로 계산했는지에 따라 갈리지 않는다(diff 항목의 `ckey` 필드 자체가 §3.3.2 대응 확정 후 dn 의 유효 ckey 다).
3. T 의 각 등록부 클러스터에 대해 `subject_ckeys ∩ changed_ckeys ≠ ∅` 또는 `member cites 의 ckey ∩ changed_ckeys ≠ ∅` 이면 그 클러스터는 `stale_for=T′` 표기(행은 불변, `rr_registry.stale_json[T′]=true`). E5 는 stale 클러스터를 `[변경 주체 — 재검증 대상]` 접두로, 나머지를 `[미변경 주체]` 로 싣는다.
4. T 의 각 seat_opinion 에 대해 `cited_ckeys ∩ changed_ckeys = ∅` 이고 `cited_refs_resolved ≠ ∅` 이고 `used_tool` 이고 ≤ risk_carried_days 이면 T′ 로스터에서 그 좌석은 `carried`(§6), 아니면 pending(cycle+1).
5. character 행은 project 단위라 옮기지 않는다. 다만 statement 의 cites ckey 가 changed_ckeys 에 들면 `rr_character.needs_review=true` 로 표기하고 ProjectPage 가 '재확인' 배지를 단다. confirmed 행도 status 는 유지한다(사람만 바꾼다).
6. T′ 의 첫 패널 결정문에서 같은 cluster_key 의 finding 이 다시 나오면 T′ 등록부 행이 새로 생기고 T 의 행은 `superseded`(superseded_by=`T′#<cluster_key>`)가 된다. 나오지 않으면 T 의 행은 open 그대로 남되 T′ 의 C1 완료 시 `stale_json[T′].unraised=true` 로 표기되어 사람이 `mitigated` 를 판단할 재료가 된다.
7. 명명 치수의 ref 가 사라져 값이 null 이 되면(`dim.named_unmeasured`) 그 `[d:]` 를 인용한 finding 은 stale 이며 E3 에 `미측정` 으로 실린다.

## 4.9 실례 — 폴더블 낙하 / UTG 에지 여유(base F7-DV1 → target F7-DV2)

사내 맥락 예시 1건을 JSON 과 산문으로 채운다. id 는 형식만 맞춘 예시값이다.

### 4.9.1 상황과 L0

과제 `F7`(폴더블 단말) DV1→DV2 개념설계 변동. 변경 요지는 베젤 축소를 위해 UTG(초박 유리) 에지와 전면 하우징 립 사이 간극을 줄이고, 보호필름(PF) 두께를 낮추고, OCA 를 두껍게 하고, 힌지 플레이트와 디스플레이 패널의 접합을 접착에서 접촉으로 바꾼 것이다. 소스는 StepForge 프로젝트 2건(DV1·DV2, 각 STEP 1파일, 리프 27)과 DynaForge 리포트 2건(kind=sphere, 낙하고 1.0 m, 동일 sim_params) 이며 ECAD 는 부재다.

rr_diff 발췌(의미 이벤트 5건, 파라메트릭·결과 항목 각 2건).

```json
{"diff_version":"1.0","diff_id":"7f3e9c1a2b4d6e8f0a1b2c3d4e5f6071",
 "base":{"snapshot_id":"a1…","ir_hash":"c0ffee…","label":"F7-DV1 2026-07-02"},
 "target":{"snapshot_id":"b2…","ir_hash":"beef00…","label":"F7-DV2 2026-08-20"},
 "comparability":{"tol_parity":true,"tol_keys_known":true,"unit_parity":true,"result_parity":true,"scope_parity":true,"coordinate_ok":true,
                  "G7":{"count":0,"threshold":0,"pass":true,"effect":"none","detail":[]}},
 "semantic":{"blocked_by":null,"events":[
  {"cid":"c:7d21a0b1c2d3","code":"iface.gap_changed","change_kind":"dimension",
   "subject":{"ckeys":["ck:3f9a2b1c0d4e","ck:aa10bb20cc30"],"names":["UTG","HOUSING_FRONT"],"eids":{"base":"e:41d2c0ffee11","target":"e:41d2c0ffee11"}},
   "subject_key":"ck:3f9a2b1c0d4e|ck:aa10bb20cc30","before":0.350,"after":0.180,"magnitude":{"value":-0.170,"unit":"mm","rel":-0.486},
   "confidence":"high","design_relevant":true,"unconfirmed":false,
   "text":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%) [c:7d21a0b1c2d3]"},
  {"cid":"c:9e8d7c6b5a40","code":"dim.named_changed","change_kind":"dimension",
   "subject":{"ckeys":[],"names":["dim:utg_edge_gap"]},"subject_key":"dim:utg_edge_gap","before":0.350,"after":0.180,
   "magnitude":{"value":-0.170,"unit":"mm","rel":-0.486},"confidence":"high","design_relevant":true,
   "text":"utg_edge_gap 0.350→0.180 mm (−48.6%) [d:utg_edge_gap] [c:9e8d7c6b5a40]"},
  {"cid":"c:1122aabbccdd","code":"part.thickness_changed","change_kind":"dimension",
   "subject":{"ckeys":["ck:5e6f70819293"],"names":["PROTECT_FILM"]},"subject_key":"ck:5e6f70819293","before":0.080,"after":0.060,
   "magnitude":{"value":-0.020,"unit":"mm","rel":-0.25},"confidence":"high","design_relevant":true,
   "text":"PROTECT_FILM min_dim 0.080→0.060 mm (−25.0%) (min_dim 근사) [c:1122aabbccdd]"},
  {"cid":"c:3344eeff0011","code":"part.thickness_changed","change_kind":"dimension",
   "subject":{"ckeys":["ck:8a9b0c1d2e3f"],"names":["OCA_TOP"]},"subject_key":"ck:8a9b0c1d2e3f","before":0.050,"after":0.075,
   "magnitude":{"value":0.025,"unit":"mm","rel":0.50},"confidence":"high","design_relevant":true,
   "text":"OCA_TOP min_dim 0.050→0.075 mm (+50.0%) (min_dim 근사) [c:3344eeff0011]"},
  {"cid":"c:5b0e11aa22bb","code":"iface.rank_down","change_kind":"topology",
   "subject":{"ckeys":["ck:1a2b3c4d5e6f","ck:9f8e7d6c5b4a"],"names":["HINGE_PLATE_L","DISPLAY_PANEL"],"eids":{"base":"e:c0de00112233","target":"e:c0de00112233"}},
   "subject_key":"ck:1a2b3c4d5e6f|ck:9f8e7d6c5b4a","before":"tied","after":"touching","magnitude":{"value":-1,"unit":"rank","rel":null},
   "confidence":"medium","design_relevant":true,"unconfirmed":true,
   "text":"HINGE_PLATE_L↔DISPLAY_PANEL kind tied→touching (rank 2→1) min_gap 0.000→0.018 mm status=auto(미확정 초안) [c:5b0e11aa22bb]"},
  {"cid":"c:6677889900aa","code":"result.part_metric_shift","change_kind":"result",
   "subject":{"ckeys":["ck:3f9a2b1c0d4e"],"names":["UTG"]},"subject_key":"ck:3f9a2b1c0d4e","before":412,"after":468,
   "magnitude":{"value":56,"unit":"MPa","rel":0.136},"confidence":"high","design_relevant":true,
   "text":"UTG worst_stress 412→468 MPa (+13.6%) case corner_45→corner_45 kind=sphere [c:6677889900aa]"},
  {"cid":"c:bbccddeeff00","code":"result.part_metric_shift","change_kind":"result",
   "subject":{"ckeys":["ck:9f8e7d6c5b4a"],"names":["DISPLAY_PANEL"]},"subject_key":"ck:9f8e7d6c5b4a","before":355,"after":331,
   "magnitude":{"value":-24,"unit":"MPa","rel":-0.068},"confidence":"high","design_relevant":true,
   "text":"DISPLAY_PANEL worst_stress 355→331 MPa (−6.8%) case face_up→face_up kind=sphere [c:bbccddeeff00]"}]},
 "character_seed":[{"tag":"char:change_style:dimension_tuning","cites":["c:7d21a0b1c2d3","c:1122aabbccdd","c:3344eeff0011"]}],
 "stats":{"nodes_added":0,"nodes_removed":0,"nodes_matched":27,"edges_added":0,"edges_removed":0,"edges_kind_changed":1,"params_changed":6,"params_noise":58,"events":7,
          "events_by_change_kind":{"dimension":4,"topology":1,"result":2}},
 "summary_text":"[대상] base F7-DV1 2026-07-02 (a1…, ir c0ffee…) → target F7-DV2 2026-08-20 (b2…, ir beef00…) · mcad stepforge 001a…/002b… · dyna_result dyna:rpt:01J…/01K… · ecad absent\n[비교가능성] tol_parity=true · result_parity=true(kind=sphere, sim_params_hash 동일) · unit ok · scope 전판 · 좌표계 ok · 제외 0건 · same-as pending 0\n[구조] +0파트 −0파트 · 계면 +0 −0 · rank 상승 0 하락 1 [c:5b0e11aa22bb] · 간섭 신규 0 해소 0 · 고아 +0 −0 · 롤업 변화 1 [c:a5a5b6b6c7c7]\n[의미] dimension: UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%) [c:7d21a0b1c2d3] · utg_edge_gap 0.350→0.180 mm (−48.6%) [d:utg_edge_gap] [c:9e8d7c6b5a40] · PROTECT_FILM min_dim 0.080→0.060 mm (−25.0%) (min_dim 근사) [c:1122aabbccdd] · OCA_TOP min_dim 0.050→0.075 mm (+50.0%) (min_dim 근사) [c:3344eeff0011] | topology: HINGE_PLATE_L↔DISPLAY_PANEL kind tied→touching (rank 2→1) min_gap 0.000→0.018 mm status=auto(미확정 초안) [c:5b0e11aa22bb] | result: UTG worst_stress 412→468 MPa (+13.6%) case corner_45 [c:6677889900aa] · DISPLAY_PANEL worst_stress 355→331 MPa (−6.8%) case face_up [c:bbccddeeff00]\n[치수] utg_edge_gap 0.350→0.180 mm (−48.6%) [d:utg_edge_gap] · hinge_radius 1.500→1.500 mm (0.0%) [d:hinge_radius] · 절대 상위: OCA_TOP min_dim +0.025 mm (size_pct 12) [c:3344eeff0011] · PROTECT_FILM min_dim −0.020 mm (size_pct 9) [c:1122aabbccdd] · 상대 상위: 동일\n[재료] 변경 0\n[결과] UTG worst_stress 412→468 MPa (+13.6%) [c:6677889900aa] · DISPLAY_PANEL worst_stress 355→331 MPa (−6.8%) [c:bbccddeeff00] · over_yield UTG 0.78→0.89 (yield_stress=525 MPa) [sig:results.over_yield[1]]\n[씨앗] char:change_style:dimension_tuning"}
```

summary_text 의 `[의미]` 줄이 change_kind 별로 사실만 나열하고 어느 줄에도 판단어가 없다는 점이 §3 의 요구이며, 좌석은 `[c:…]` 를 그대로 복사해 인용한다.

ckey 주석. PROTECT_FILM(`ck:5e6f70819293`, 부피 ≈−25%)·OCA_TOP(`ck:8a9b0c1d2e3f`, +50%)은 DV2 에서 volume 5% 로그 버킷이 각각 ≈6칸·≈8칸 이동해 **계산** ckey 가 DV1 과 다르다. 두 노드는 pair same-as `exact_path`(canon_key 동일, score 1.0)로 이어졌으므로 §2.7.3 자동 승계가 `rr_part_keys` 에 `{ckey: <DV2 계산값>, status:'merged', merged_into:'ck:5e6f70819293', decided_by:'code:pair_correspondence'}`(OCA_TOP 은 `merged_into:'ck:8a9b0c1d2e3f'`) 행을 넣고 DV2 노드에 DV1 유효 ckey 를 부여한다. 그래서 이 예시의 diff 항목·finding·등록부가 양쪽에 같은 ckey 를 쓰는 것이 규칙과 일치하며, P2 (11) 픽스처가 바로 이 두 파트다.

### 4.9.2 L2 risk_spec(패널 1, 6석 — mech·sim·xd·disp primary, rel counter, 지정 반대석)

```json
{"schema":"risk_spec","version":"1.0","taxonomy_version":"1.0",
 "scope":{"kind":"diff","target_key":"diff:7f3e9c1a2b4d6e8f0a1b2c3d4e5f6071","project_refs":["F7"],
          "ir_refs":["a1…","b2…"],"diff_ref":"7f3e9c1a2b4d6e8f0a1b2c3d4e5f6071","ir_hash":"beef00…"},
 "findings":[
  {"id":"F1","direction":"risk","domain":"mech","mechanism":"mechanical","mechanism_detail":"drop_stress","change_kind":"dimension",
   "subject":{"ckeys":["ck:3f9a2b1c0d4e","ck:aa10bb20cc30"],"names":["UTG","HOUSING_FRONT"]},
   "trigger_condition":"load.drop","trigger_text":"코너 자세 1.0 m",
   "severity":"중대","judgement":"WARNING",
   "detectability":{"level":"sim-detectable","tool":"report_part_risk"},
   "evidence_grade":"도구예측","precedent":"none",
   "cites":[{"ref":"c:7d21a0b1c2d3","quote":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%)"},
            {"ref":"c:6677889900aa","quote":"UTG worst_stress 412→468 MPa (+13.6%) case corner_45→corner_45 kind=sphere"},
            {"ref":"sig:results.over_yield[1]","quote":"over_yield UTG 0.78→0.89 (yield_stress=525 MPa)"}],
   "tool_calls":["report_part_risk(report_id=01K…)","list_interfaces(kind=clearance, name_like=UTG)"],
   "claim":"UTG 에지와 HOUSING_FRONT 립 사이 간극이 0.350→0.180 mm 로 줄면서 코너 낙하(corner_45) 에서 UTG 최대 응력이 412→468 MPa 로 올라 항복 대비 0.89 에 이른다.",
   "warrant":"간극 축소로 코너 충돌 시 하우징 립이 UTG 에지에 먼저 닿는 접촉 순서가 되며 sphere 리포트 corner_45 케이스가 그 위치에서 최대 응력을 보인다. 두 리포트는 kind·sim_params 가 같아 수치 비교가 유효하다.",
   "resolving_check":{"kind":"sim","ref":"sphere 리포트 corner 계열 케이스에서 UTG 에지 요소 응력 시계열 확인(report_part_series)"},
   "owner_domain":"mech","raised_by":["mech-housing-structure","sim-drop-impact"],"contested_by":[],"contest_note":"","status":"open"},
  {"id":"F2","direction":"risk","domain":"disp","mechanism":"mechanical","mechanism_detail":"drop_stress","change_kind":"dimension",
   "subject":{"ckeys":["ck:3f9a2b1c0d4e","ck:5e6f70819293"],"names":["UTG","PROTECT_FILM"]},
   "trigger_condition":"load.drop","trigger_text":"에지 우선 접촉",
   "severity":"중대","judgement":"undetermined",
   "detectability":{"level":"test-only","tool":""},
   "evidence_grade":"도구예측","precedent":"none",
   "cites":[{"ref":"c:1122aabbccdd","quote":"PROTECT_FILM min_dim 0.080→0.060 mm (−25.0%) (min_dim 근사)"},
            {"ref":"c:7d21a0b1c2d3","quote":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%)"}],
   "tool_calls":["list_parts(name_like=FILM)"],
   "claim":"보호필름이 0.080→0.060 mm 로 얇아진 상태에서 에지 우선 접촉이 되면 UTG 에지 치핑 개시 하중이 낮아질 수 있으나 해석 모델에 에지 결함 분포가 없어 판정 불가다.",
   "warrant":"UTG 에지 강도는 연마 결함 크기에 지배되고 이 값은 IR·리포트 어디에도 없다. 필름 두께 감소는 에지로 전달되는 접촉 하중을 키우는 방향의 사실이다.",
   "resolving_check":{"kind":"test","ref":"UTG 에지 4점 굽힘 + 코너 낙하 시험(DV2 시제 n≥5)"},
   "owner_domain":"disp","raised_by":["disp-utg-cover"],"contested_by":["delib-baseline-defender"],
   "contest_note":"에지 결함 데이터 없이 중대로 두는 것은 과잉 — undetermined 로 낮출 것","status":"open"},
  {"id":"F3","direction":"risk","domain":"xd","mechanism":"process","mechanism_detail":"tolerance","change_kind":"dimension",
   "subject":{"ckeys":["ck:3f9a2b1c0d4e","ck:aa10bb20cc30"],"names":["UTG","HOUSING_FRONT"]},
   "trigger_condition":"mfg.tolerance","trigger_text":"조립 공차 누적",
   "severity":"경미","judgement":"WARNING",
   "detectability":{"level":"sim-detectable","tool":"list_interfaces"},
   "evidence_grade":"도구예측","precedent":"none",
   "cites":[{"ref":"d:utg_edge_gap","quote":"utg_edge_gap 0.350→0.180 mm (−48.6%)"},
            {"ref":"sig:hist.gap_mm","quote":"gap_hist_mm [0,0.01)=1 [0.01,0.05)=3 [0.05,0.1)=2 [0.1,0.2)=4 [0.2,0.5)=6"}],
   "tool_calls":["list_interfaces(kind=clearance)"],
   "claim":"utg_edge_gap 0.180 mm 는 이 조립체의 clearance 분포에서 하위 구간에 들고 조립 공차 누적분이 없어 실물 간극이 0 이 될 수 있다.",
   "warrant":"명명 치수가 공칭값이며 공차 스택 값은 IR 에 없다. 근접 간극 구간 분포가 그 사실을 보여준다.",
   "resolving_check":{"kind":"tool","ref":"rr_dim_defs 에 utg_edge_gap_tol 정의 후 재평가"},
   "owner_domain":"xd","raised_by":["xd-mech-assembly"],"contested_by":[],"contest_note":"","status":"open"}],
 "gains":[
  {"id":"G1","direction":"improvement","domain":"sim","mechanism":"mechanical","mechanism_detail":"drop_stress","change_kind":"dimension",
   "subject":{"ckeys":["ck:9f8e7d6c5b4a","ck:8a9b0c1d2e3f"],"names":["DISPLAY_PANEL","OCA_TOP"]},
   "trigger_condition":"load.drop","trigger_text":"면 낙하(face_up)",
   "severity":"경미","judgement":"OK",
   "detectability":{"level":"sim-detectable","tool":"report_part_risk"},
   "evidence_grade":"도구예측","precedent":"none",
   "cites":[{"ref":"c:3344eeff0011","quote":"OCA_TOP min_dim 0.050→0.075 mm (+50.0%) (min_dim 근사)"},
            {"ref":"c:bbccddeeff00","quote":"DISPLAY_PANEL worst_stress 355→331 MPa (−6.8%) case face_up→face_up kind=sphere"}],
   "tool_calls":["report_part_risk(report_id=01K…)"],
   "claim":"OCA 가 0.050→0.075 mm 로 두꺼워지면서 면 낙하에서 DISPLAY_PANEL 최대 응력이 355→331 MPa 로 내려갔다.",
   "warrant":"같은 kind·같은 sim_params 리포트의 같은 케이스(face_up) 수치이며 변경 항목 중 패널 위 적층에서 바뀐 것은 OCA 두께뿐이다.",
   "resolving_check":{"kind":"sim","ref":"OCA 두께 0.075 mm 고정 후 corner 계열 케이스 재확인"},
   "owner_domain":"sim","raised_by":["sim-drop-impact","delib-baseline-defender"],"contested_by":[],"contest_note":"","status":"open"}],
 "cross_domain":[
  {"id":"X1","from_domain":"mech","to_domain":"disp",
   "path":"간극 축소(mech) → 코너 낙하 접촉 순서가 하우징 립→UTG 에지로 바뀜 → 에지 치핑 모드(disp) 가 지배 실패모드로 이동",
   "cites":[{"ref":"c:7d21a0b1c2d3","quote":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%)"}],"raised_by":["disp-utg-cover"]},
  {"id":"X2","from_domain":"mech","to_domain":"rel",
   "path":"HINGE_PLATE_L↔DISPLAY_PANEL 접합이 tied→touching 이면 접이 사이클 중 상대 미끄럼이 생겨 패널 하부 마모·들뜸(rel) 이 새 경로가 된다",
   "cites":[{"ref":"c:5b0e11aa22bb","quote":"HINGE_PLATE_L↔DISPLAY_PANEL kind tied→touching (rank 2→1) min_gap 0.000→0.018 mm status=auto(미확정 초안)"}],"raised_by":["rel-fold-cycle"]}],
 "character":{
  "one_liner":"베젤 축소를 위해 UTG 에지 여유를 절반으로 줄이고 적층 두께를 재배분한 폴더블 DV2 — 에지 우선 접촉이 새 지배 경로다.",
  "facets":[
   {"facet":"intent","na_reason":null,"statements":[
     {"id":"C1","text":"이 변동은 두께가 아니라 베젤 폭을 줄이려는 변경이다 — 바뀐 치수는 UTG 에지 간극과 필름·OCA 두께뿐이고 전체 bbox_z 는 6.600→6.600 mm 로 같다.","polarity":"inference","by":["xd-mech-assembly"],
      "cites":[{"ref":"d:utg_edge_gap","quote":"utg_edge_gap 0.350→0.180 mm (−48.6%)"},{"ref":"sig:scale.bbox_world","quote":"bbox_world [158.2, 72.1, 6.600] mm"}],
      "tags":["char:philosophy:thin_first"],"confidence":"high"}]},
   {"facet":"constraint","na_reason":null,"statements":[
     {"id":"C2","text":"힌지 반경 1.500 mm 가 DV1 그대로라 접이 곡률은 고정 제약이고, 적층 두께 재배분은 그 반경 안에서만 이루어졌다.","polarity":"observation","by":["mech-housing-structure"],
      "cites":[{"ref":"d:hinge_radius","quote":"hinge_radius 1.500→1.500 mm (0.0%)"}],"tags":["char:structure:foldable_hinge"],"confidence":"high"}]},
   {"facet":"anomaly","na_reason":"비교 불가(코퍼스 n<5)","statements":[]},
   {"facet":"lineage","na_reason":null,"statements":[
     {"id":"C3","text":"DV1 대비 파트 추가·삭제 없이 치수 4건과 접합 1건만 바뀐 리비전이라 구조는 계승, 계면 성격만 이동했다.","polarity":"observation","by":["chair"],
      "cites":[{"ref":"c:5b0e11aa22bb","quote":"HINGE_PLATE_L↔DISPLAY_PANEL kind tied→touching (rank 2→1)"}],"tags":["char:change_style:dimension_tuning"],"confidence":"high"}]},
   {"facet":"vulnerability","na_reason":null,"statements":[
     {"id":"C4","text":"UTG 에지↔HOUSING_FRONT 립이 이 리비전의 취약 계면이다 — 간극 0.180 mm 에서 코너 낙하 응력이 468 MPa 로 항복 대비 0.89 다.","polarity":"inference","by":["mech-housing-structure","sim-drop-impact"],
      "cites":[{"ref":"c:7d21a0b1c2d3","quote":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%)"},{"ref":"c:6677889900aa","quote":"UTG worst_stress 412→468 MPa (+13.6%)"}],
      "tags":["char:interface:utg_housing_front","char:tolerance:tight"],"confidence":"high"}]},
   {"facet":"strength","na_reason":null,"statements":[
     {"id":"C5","text":"두꺼워진 OCA 가 면 낙하에서 패널 응력을 331 MPa 로 낮춰 면 낙하 여유는 DV1 보다 커졌다.","polarity":"observation","by":["sim-drop-impact","delib-baseline-defender"],
      "cites":[{"ref":"c:bbccddeeff00","quote":"DISPLAY_PANEL worst_stress 355→331 MPa (−6.8%)"}],"tags":["char:structure:stacked"],"confidence":"high"}]},
   {"facet":"tradeoff","na_reason":null,"statements":[
     {"id":"C6","text":"베젤 폭(간극 0.170 mm 절감)을 얻고 코너 낙하 에지 여유(응력 +56 MPa)를 내줬다.","polarity":"inference","by":["chair"],
      "cites":[{"ref":"c:7d21a0b1c2d3","quote":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%)"},{"ref":"c:6677889900aa","quote":"UTG worst_stress 412→468 MPa (+13.6%)"}],"tags":[],"confidence":"medium"},
     {"id":"C7","text":"OCA 두께 +0.025 mm 로 면 낙하 응력 −24 MPa 를 얻는 대신 접이 영역 적층 강성이 올라 힌지 접합을 touching 으로 풀어야 했다.","polarity":"hypothesis","by":["mech-housing-structure"],
      "cites":[{"ref":"c:3344eeff0011","quote":"OCA_TOP min_dim 0.050→0.075 mm (+50.0%)"},{"ref":"c:bbccddeeff00","quote":"DISPLAY_PANEL worst_stress 355→331 MPa (−6.8%)"},{"ref":"c:5b0e11aa22bb","quote":"HINGE_PLATE_L↔DISPLAY_PANEL kind tied→touching (rank 2→1)"}],"tags":["x:stack_stiffness_budget"],"confidence":"low"}]},
   {"facet":"unknown","na_reason":null,"statements":[
     {"id":"C8","text":"UTG 에지 결함 분포와 조립 공차 스택이 IR 에 없어 F2·F3 은 판정 불가다(O1·O2).","polarity":"observation","by":["disp-utg-cover","xd-mech-assembly"],
      "cites":[{"ref":"d:utg_edge_gap","quote":"utg_edge_gap 0.350→0.180 mm (−48.6%)"}],"tags":[],"confidence":"high"},
     {"id":"C9","text":"ECAD 부재로 pcb·pwr·rf·soc·passive·mem 관점(FPC 접힘 영역·커넥터 위치)은 미평가다(O3).","polarity":"observation","by":["code"],
      "cites":[{"ref":"sig:counts.ecad.components","quote":"ecad.components=미측정 (ecad_absent)"}],"tags":["char:analysis:ecad_absent"],"confidence":"high"}]}]},
 "open_items":[
  {"id":"O1","question":"UTG 에지 결함 크기 분포(연마 조건별)가 있는가","resolving_check":{"kind":"test","ref":"UTG 에지 4점 굽힘 n≥30 와이블"},"owner_domain":"disp"},
  {"id":"O2","question":"utg_edge_gap 의 조립 공차 스택(±)은 얼마인가","resolving_check":{"kind":"tool","ref":"rr_dim_defs utg_edge_gap_tol 정의 후 재평가"},"owner_domain":"xd"},
  {"id":"O3","question":"HINGE_PLATE_L↔DISPLAY_PANEL 이 실제로 접착 해제인가 검출 오분류인가","resolving_check":{"kind":"tool","ref":"set_interface 로 사람 확정 후 재스냅샷"},"owner_domain":"mech"}],
 "coverage":{"seats":[{"key":"mech-housing-structure","domain":"mech","origin":"primary"},{"key":"sim-drop-impact","domain":"sim","origin":"primary"},
                      {"key":"xd-mech-assembly","domain":"xd","origin":"primary"},{"key":"disp-utg-cover","domain":"disp","origin":"primary"},
                      {"key":"rel-fold-cycle","domain":"rel","origin":"counter"},{"key":"delib-baseline-defender","domain":"delib","origin":"adversary"}],
             "domains_seated":["mech","sim","xd","disp","rel"],"domains_missing":["pcb","pwr","rf","soc","passive","mem","cam","sh","std","material"]},
 "verdict":"conditional",
 "verdict_conditions":["O3 확정 후 HINGE 접합이 tied 로 복원되지 않으면 rel 재심","O2 공차 스택 반영 시 utg_edge_gap 최소값 ≥ 0.10 mm"],
 "evidence_profile":{"tool":9,"card":3,"precedent":{"verified":0,"dismissed":0},"heuristic":0,"measured":0}}
```

파서 결과. F1·F3·G1 은 cites 전부 실재·quote 일치 → evidence_grade 도구예측 유지. F2 는 반대석 contest 가 있어 등록부 contested=1. C7 은 polarity=hypothesis 이고 `x:stack_stiffness_budget` 는 자유 태그로 큐 대상(다른 타깃 2곳에서 더 나와야 승격 후보). anomaly facet 은 corpus_n<5 라 na_reason 자동. C9 는 코드가 unknown facet 에 넣은 자동 statement 다. evidence_profile 은 seat_opinion 합계(tool_calls_ok 합 9, knowledge_hits 3)와 일치해 header_mismatch 없음.

### 4.9.3 산문(결정문 (3)(4)(5) 발췌 — 산문과 spec 이 같은 id 를 쓴다)

(3) 도메인별 리스크 판정. F1 [mech·sim] UTG 에지와 HOUSING_FRONT 립 사이 간극이 0.350→0.180 mm 로 줄면서(−48.6%) 코너 낙하 corner_45 에서 UTG 최대 응력이 412→468 MPa 로 올라 항복 대비 0.89 에 이른다 [c:7d21a0b1c2d3][c:6677889900aa][sig:results.over_yield[1]]. 중대·WARNING, sim-detectable(report_part_risk), [도구예측], 선례 none. F2 [disp] 보호필름 0.080→0.060 mm 와 에지 우선 접촉이 겹치면 에지 치핑 개시 하중이 낮아질 수 있으나 결함 분포가 없어 판정 불가 — 반대석은 "결함 데이터 없이 중대는 과잉" 으로 undetermined 를 요구했고 의장은 severity 중대·judgement undetermined 로 둔다 [c:1122aabbccdd]. F3 [xd] utg_edge_gap 0.180 mm 는 공칭값이고 공차 스택이 없다 [d:utg_edge_gap]. 경미·WARNING.

(4) 개선되는 점. G1 [sim, 반대석 동의] OCA 0.050→0.075 mm 로 면 낙하 패널 응력 355→331 MPa [c:3344eeff0011][c:bbccddeeff00]. 경미·OK, [도구예측].

(5) 과제 성격. C1 (설계 의도) 이 변동은 두께가 아니라 베젤 폭을 줄이려는 변경이다 — 바뀐 치수는 UTG 에지 간극과 필름·OCA 두께뿐이고 전체 bbox_z 는 6.600 mm 로 같다 [d:utg_edge_gap][sig:scale.bbox_world] (xd-mech-assembly). C2 (제약) 힌지 반경 1.500 mm 가 그대로라 접이 곡률은 고정 제약이다 [d:hinge_radius] (mech-housing-structure). (이례성) 비교 불가(코퍼스 n<5). C3 (계보) DV1 대비 파트 추가·삭제 없이 치수 4건·접합 1건만 바뀐 리비전이다 [c:5b0e11aa22bb] (의장). C4 (취약 계면) UTG 에지↔HOUSING_FRONT 립이 취약 계면이다 — 간극 0.180 mm 에서 코너 낙하 응력 468 MPa, 항복 대비 0.89 [c:7d21a0b1c2d3][c:6677889900aa] (mech·sim). C5 (강점) 두꺼워진 OCA 가 면 낙하 패널 응력을 331 MPa 로 낮췄다 [c:bbccddeeff00] (sim·반대석). C6·C7 (맞교환) 베젤 폭을 얻고 코너 에지 여유를 내줬다 [c:7d21a0b1c2d3][c:6677889900aa] (의장); OCA 두께로 면 낙하 여유를 얻는 대신 적층 강성 예산 때문에 힌지 접합을 풀었다는 것은 가설이다 [c:3344eeff0011][c:5b0e11aa22bb] (mech, hypothesis). C8·C9 (미지) 에지 결함 분포·공차 스택·ECAD 부재(O1·O2·O3).

### 4.9.4 L1 seat_opinion 발췌(disp-utg-cover)

```json
{"opinion_id":"0d1s…","target_key":"diff:7f3e9c1a…","panel_id":"p001…","agent_key":"disp-utg-cover","domain":"disp","origin":"primary","cycle":1,
 "turns":[{"round":1,"say_excerpt":"UTG↔HOUSING_FRONT clearance min_gap 0.350→0.180 mm (−48.6%) [c:7d21a0b1c2d3] 를 보면 코너 접촉이 립이 아니라 에지로 옮겨간다. list_parts 로 PROTECT_FILM 두께를 확인했고 0.060 mm 다. 에지 결함 분포가 없어 치핑 개시 하중은 말할 수 없다…","position":"에지 우선 접촉 구조로의 이동 자체가 리스크 항목","stance":"conditional","non_negotiable":"에지 결함 분포 없이 OK 판정 금지"},
          {"round":2,"say_excerpt":"반대석의 '중대 과잉' 지적은 받아들이되 judgement 는 undetermined 로 두고 severity 는 유지…","position":"…","stance":"conditional","non_negotiable":"…"},
          {"round":3,"say_excerpt":"…","position":"F2 undetermined·O1 시험 선행","stance":"conditional","non_negotiable":"…"}],
 "final_stance":"conditional",
 "tool_calls":[{"tool":"list_parts","args_gist":"name_like=FILM","ok":true,"activity_idx":11,"round":1},{"tool":"list_interfaces","args_gist":"kind=clearance name_like=UTG","ok":true,"activity_idx":12,"round":1}],
 "tool_calls_n":2,"tool_calls_ok":2,"knowledge_hits_n":1,
 "cited_refs":["c:7d21a0b1c2d3","c:1122aabbccdd","name:UTG|HOUSING_FRONT"],
 "cited_refs_resolved":["c:7d21a0b1c2d3","c:1122aabbccdd","e:41d2c0ffee11"],
 "cited_ckeys":["ck:3f9a2b1c0d4e","ck:aa10bb20cc30","ck:5e6f70819293"],
 "quality":{"used_tool":true,"cited_ir":true,"grade_min":"도구예측","dangling_n":0},
 "raised_finding_ids":["p001…#F2"],"contested_finding_ids":[],
 "character_sentences":["이 리비전의 성격은 '에지 우선 접촉' 으로의 이동이다."],
 "excerpt_for_rag":"…"}
```

### 4.9.5 L3 등록부(패널 1 완료 시점)

| cluster_key | direction | mechanism.detail | change_kind | subject | sev/judg | grade | precedent | support/contested | status | resolving_checks |
|---|---|---|---|---|---|---|---|---|---|---|
| sha1(mechanical\|drop_stress\|ck:3f9a…\|ck:aa10…\|dimension)[:12] | risk | mechanical.drop_stress | dimension | UTG↔HOUSING_FRONT | 중대/WARNING | 도구예측 | none | 1/0 | open | `sim:sphere corner 계열 UTG 에지 응력 시계열` |
| sha1(mechanical\|drop_stress\|ck:3f9a…\|ck:5e6f…\|dimension)[:12] | risk | mechanical.drop_stress | dimension | UTG↔PROTECT_FILM | 중대/undetermined | 도구예측 | none | 1/1 | open | `test:UTG 에지 4점 굽힘 + 코너 낙하 n≥5` |
| sha1(process\|tolerance\|ck:3f9a…\|ck:aa10…\|dimension)[:12] | risk | process.tolerance | dimension | UTG↔HOUSING_FRONT | 경미/WARNING | 도구예측 | none | 1/0 | open | `tool:rr_dim_defs utg_edge_gap_tol` |
| sha1(mechanical\|drop_stress\|ck:8a9b…\|ck:9f8e…\|dimension)[:12] | improvement | mechanical.drop_stress | dimension | DISPLAY_PANEL↔OCA_TOP | 경미/OK | 도구예측 | none | 1/0 | open | `sim:OCA 0.075 고정 corner 재확인` |

verdict 후보 = conditional(WARNING ≥1, FAIL 0). 다음 과제(예 F7-PV1 또는 계보 없는 폴더블 G2)에서 `subject_key = ck:3f9a…|ck:aa10…` 가 같은 ckey 로 잡히면 첫 행이 E5 에 `[reg:diff:7f3e…#<cluster_key>] 중대/WARNING 도구예측 support 1 — "UTG 에지와 HOUSING_FRONT 립 사이 간극이 …" (검증 대상)` 으로 실린다. 계보가 없어도 ckey 가 이름·기하 버킷·재료로 계산되므로 `UTG`·`HOUSING_FRONT` 에 해당하는 부품이 있는 어떤 폴더블 과제에서든 같은 키가 나온다. 같은 과제의 다음 리비전(F7-PV1)에서는 §2.7.3 자동 승계가 두께·부피를 손댄 파트에도 DV1 유효 ckey 를 이어 주고, 계보 없는 과제에서 크기 버킷이 어긋난 부품은 §5.9.4 근접 매치(size ±1 버킷·volume 무관)가 `[경로: subject·별칭후보]` 로 받는다.

## 4.10 검증 항목(§9 통과 기준의 정의)

- (P0) parse_risk_spec 이 펜스·중괄호 폴백·schema 검증·null 비치명을 픽스처 6종(정상·펜스 없음·중괄호 깨짐·schema 다름·facet 7개·enum 위반)에서 기대대로 동작.
- (P3) §4.9 규모의 실패널 1건에서 findings ≥3·gains ≥1·facet 8 존재·dangling 0(name: 해석 포함)·quote_mismatch 0·evidence_profile header_mismatch 없음. `cited_refs_resolved` 추출이 픽스처 발언 20건에서 정밀도 ≥0.95.
- (P3) 등록부 병합이 같은 finding 집합 2회 병합에 멱등(rr_registry 행·`rr_delta_contrib`·`rr_delta_priors` 값 불변, §9.4 (12)), cluster_key 가 ir_refs 순서·좌석과 무관.
- (P4) §4.8 무효화 — 합성 새 스냅샷(UTG 간극만 변경)에서 첫·둘째·셋째 클러스터만 stale, 넷째(OCA) 는 미변경, disp 좌석은 pending(cited_ckeys 교집합 ≠ ∅), sim 좌석은 carried 조건 충족.
- (P5) 계보 없는 합성 과제에서 subject_key 동일 클러스터 회수 ≥1(§9 P5 (5)).
- 린터 — 통합 보고서 background·recommendation 의 코드 생성 문장 판단어 0(results 의 claim 원문은 «» 인용).

---


# §5 저장과 재사용

이 절은 사용자가 가장 어렵다고 짚은 곳을 맡는다. 그래프 diff 와 상태 평가를 §3·§4 가 서술로 정리했다면, 여기서는 그 서술을 **어디에 어떤 형태로 남기고**, **다음 과제(계보가 있는 과제)와 다른 connectivity(계보가 없는 과제)에서 어떤 키로 다시 꺼내 쓰는가** 를 구현자가 바로 옮길 수 있는 수준으로 적는다. 이름은 전부 §0 의 것이고, 정의가 다른 절에 있는 필드는 그 절 번호를 단다. 1차 완결성 비평(gap_21)이 이 절에 요구한 수정 — E0~E9 예산표의 항목별 상한, 과제 무관 전역 키(ckey)와 계면 별칭 사전, `revision_of` 를 포함한 6축·12관계 전표, C1 에서 RA 의존을 뺀 `external_sync`, 좌석 개인 기억 회수 경로(E7 고정 슬롯)와 오염 방지 선택의 결과 명시 — 는 모두 반영된 상태로 적었다.

## 5.1 3층 분담과 원칙

B 토폴로지(§0.7 #12)에서 1층은 포털이 아니라 HEAX 앱 `hwax_risk` 의 전용 DB 다. 2층·3층(RA KG·AIDataHub)은 A 계획과 같은 2차 색인이고, 바뀐 것은 **쓰는 주체(앱 프로세스)·쓰기 경로·자격의 보관 위치** 뿐이다. 표 목록·rr_* 스키마·원자·해시 규약·prior_evidence·커버리지 상태기계는 그대로다.

| 층 | 담는 것 | 안 담는 것 | 쓰기 경로 | 인증 |
|---|---|---|---|---|
| 앱 DB `$HEAX_DATA_DIR/risk_review.db`(hwax_risk 앱 `backend/app/risk_store.py`) | 과제·소스·스냅샷·rr_ir 원본·호출 로그·원장(same-as·계면·ckey)·rr_state·rr_diff·타깃·로스터·커버리지·패널·잡·seat_opinion·finding·등록부·claim 역색인·성격 진술·계면 별칭·delta 선례·라벨·패턴·규칙·지표·큐레이션 큐·3자 id 매핑 — **ID 권위와 정본** | 조직 단위 의미 검색(AIDataHub 몫), 다중 관계 탐색(RA 몫) | 앱 프로세스 안에서만 쓴다 — stdlib sqlite3 + `threading.Lock`, 모든 쿼리 `owner_sub`. 진입은 앱 REST `/apps/hwax_risk/api/*`(UI·헤드리스)와 앱 MCP `/apps/hwax_risk/mcp` 쓰기 도구(`risk_submit_panel_result`)와 앱 러너(`runner.py`) 셋뿐이고 포털 백엔드는 이 DB 를 열지 않는다 | Caddy forward_auth(heax 쿠키 `heax_access_token` 또는 `Authorization: Bearer <heax JWT \| heax_pat_…>`) 통과 후 앱 `identity.py` 가 같은 자격으로 heax `GET /api/v1/auth/me` 를 되물어 신원 확정(캐시 TTL 60 s). MCP 경로는 heax 서비스 PAT 신원 + `actor` 인자(미검증 표기) |
| ReportArchive KG | 과제·스냅샷·diff·판정·finding·전문가·성격 태그 사이의 **관계**와 enum/number/date/text 급 소형 속성, 기존 `part · model · failure_mode · defect · incident · test_run` 축과의 연결, 심의·통합 보고서 | 서술 본문(longtext 는 검색·임베딩 대상이 아님), 노드 수천 개 그래프 원본(속성에 JSON 타입 없음) | 부트스트랩 1회는 관리 REST(`/api/entity-types` · `/properties` · `/api/relation-types`, 실행자 셸의 `backend/scripts/bootstrap_ra_ontology.py`). 인스턴스는 **앱 → 게이트웨이 MCP** `reportarchive` 백엔드의 쓰기 4종 `create_object · update_object · add_object_alias · link_objects`, 보고서는 `create_report_draft · update_report_draft`(§5.3.5). 대안 경로는 RA REST 직접(§5.3.5, 기본 미채택). RA 코드 무수정 | 부트스트랩은 실행자 env `RA_ADMIN_PAT`(RA `rat_` 시스템관리자 토큰, 앱 밖). 앱 런타임은 게이트웨이 호출 자격 `HWAXRISK_PORTAL_PAT`(포털 PAT, aud `mcp-gateway`, `$HEAX_DATA_DIR/secrets.env`) 만 보유하고 RA 토큰은 게이트웨이의 서비스 `rat_`+`X-Workspace-Slug` 가 대신한다(RA 소유자 = 서비스 계정) |
| AIDataHub | 좌석 서술(risk_review_opinion)·패널 결정문(risk_review_panel)·과제 성격(project_character)·패턴 카드(risk_pattern_card)·스냅샷 다이제스트 표(design_snapshot_digest) — 섹션 단위 임베딩으로 **RAG 회수 대상** | 관계·커버리지 회계·IR 원본·유니크 제약이 필요한 것 | **앱 발신** REST `POST {HWAXRISK_AIDH_BASE}/api/records/import?external_source=hwax-risk` + `_external_id` UPSERT(앱 `backend/app/adh_client.py`), `create_doc_type`·`create_agent` 각 1회(실행자 셸의 `backend/scripts/bootstrap_adh.py`) | `X-API-Key: <HWAXRISK_AIDH_API_KEY>`(`$HEAX_DATA_DIR/secrets.env`, 부트스트랩 스크립트는 같은 이름의 실행자 env) |

원칙.

1. **ID 권위는 앱 DB 다.** RA 는 `code=<앱 DB id>` 로, AIDataHub 는 `external_id_map(source='hwax-risk', external_id)` 로 앱 DB id 를 따라간다. 외부 id 는 앱 DB `rr_id_map` 과 각 행의 `ra_entity_id · adh_record_id` 컬럼에 되돌려 적는다. 포털·RA·AIDataHub 어느 쪽도 rr_* id 를 발급하지 않는다.
2. **외부 반영은 비치명이고 완결 레벨과 분리된다.** RA·AIDataHub·게이트웨이가 없어도 C1~C3 는 도달하며, 반영 상태는 `rr_targets.external_sync_json{ra, adh}` 로 따로 보인다(§5.5.3). C1 조건에 'RA assessment 생성 완료' 를 넣지 않는다(gap_21 #7).
3. **원본은 한 곳에만 있다.** IR·diff·finding·성격 진술의 정본은 앱 DB 이고 RA·AIDataHub 는 투영이다. 투영이 어긋나면 앱이 다시 밀어 넣는다(UPSERT 멱등). 앱 DB 자체의 사본(Drive app-data 스냅샷·JSONL export)은 백업·이관 수단이지 두 번째 정본이 아니다(§5.2.5).
4. **재주입은 원문 발췌만이다(헌법 P1).** 다음 과제 브리프에 실리는 것은 코드가 만든 정규 표기와 출처 태그가 붙은 원문 발췌뿐이고, 요약 재작성·결론 문장은 금지다. 코드 생성 문장은 판단어 린터(§3)를 통과해야 한다.
5. **사람 확정은 스냅샷 밖 원장에 둔다.** `rr_sameas · rr_iface_ledger · rr_part_keys · rr_iface_alias` 는 재추출·재검출에 유실되지 않고 새 스냅샷에 재적용된다(§2).
6. **조직 공유는 컬럼으로 표기하고 P6 에서 켠다.** 공유 자산(`rr_findings · rr_registry · rr_patterns · rr_metrics · rr_iface_alias · rr_delta_priors`)에 `visibility ∈ private|org` 를 두고 기본값은 `private` 이다. `org` 행은 owner_sub 와 무관하게 읽기만 허용하고 쓰기는 소유자·큐레이터만 한다.

## 5.2 앱 DB `$HEAX_DATA_DIR/risk_review.db`

물리 위치는 hwax_risk 앱 데이터 디렉터리의 단일 SQLite 파일 하나다 — SIF 실행 `/data/risk_review.db`, 호스트 실행 `HEAXHub/var/app_data/hwax_risk/risk_review.db`, 리포 로컬 폴백 `<HWAXRisk>/data/risk_review.db`(§0.3.1). A 계획의 `HWAXPortal/data/risk_review.sqlite` 는 폐기다. 파일명·확장자는 고정이고 Settings 로 바꾸지 않는다(`risk_store_path` 폐기) — 확장자 `.db` 가 `appdata-to-drive.sh` 의 `.backup` 원자 스냅샷 조건이기 때문이다(§5.2.5). rr_* 33 표의 DDL 은 A 계획과 바이트 동일하다(§5.2.2).

### 5.2.1 공통 규약

| 항목 | 규약 |
|---|---|
| 모듈 | 앱 `backend/app/risk_store.py` 의 `RiskStore`. 포털 `conv_store.py` 의 골격을 복제한다(코드 의존 없음) — `sqlite3.connect(path, check_same_thread=False)`, `threading.Lock`, 생성자에서 `CREATE TABLE IF NOT EXISTS` 전부 실행(§5.2.5 (6) 마이그레이션 v1), `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=OFF`(외래키는 문자열 계약, DB 제약으로 강제하지 않는다) |
| 경로 | `config.py` 데이터 루트 = `HWAXRISK_DATA_DIR` > `HEAX_DATA_DIR` > `<리포>/data`(§0.5.3), 파일명 `risk_review.db` 고정. `main.py` lifespan 에서 `app.state.risk_store` 를 항상 생성한다(활성 플래그 없음 — 앱 존재가 활성, `risk_review_enabled` 폐기). 쓰기 주체는 앱 프로세스 하나뿐이다(REST 핸들러·MCP 도구·러너 스레드가 같은 `RiskStore` 인스턴스와 Lock 을 공유) |
| id | uuid hex32(`uuid.uuid4().hex`, 포털 `conv_store._uid` 와 같은 형식). 예외는 자연키 — `target_key · coverage_key · cluster_key · ckey · alias_key · call_id · nid · eid · cid` |
| 시각 | `INTEGER` epoch 초(UTC). 컬럼명은 `*_at` |
| JSON | `TEXT` 컬럼명 `*_json`, 키 정렬 canonical JSON(`json.dumps(sort_keys=True, ensure_ascii=False, separators=(',',':'))`)으로 저장해 해시 비교가 가능하게 한다 |
| 대용량 | `rr_snapshots.ir_json` 은 TEXT 원문(500 노드·2000 엣지 기준 ≈400~900 KB), `rr_snapshot_calls.response_gz` 만 gzip BLOB |
| 소유권 | 모든 표에 `owner_sub TEXT NOT NULL`. 값은 **heax 사용자 이메일**(소문자, HEAX authz 가 `X-Heax-User-Email` 로 내는 그 값)이다. 원천 — (UI·REST) 앱 `identity.py` 가 전달된 `Authorization: Bearer` 또는 쿠키 `heax_access_token` 을 Bearer 로 삼아 heax `GET /api/v1/auth/me`(`HWAXRISK_HEAX_API`) 를 되물어 얻은 `email`(토큰 sha256 키 캐시 TTL 60 s). service 모드 앱에는 `X-Heax-User-*` 헤더가 복사되지 않고 클라이언트가 위조해 보낼 수 있으므로 헤더 자체는 절대 읽지 않는다. (MCP) `risk_submit_panel_result.actor` 인자의 이메일 — 게이트웨이 신고값·미검증이며 행의 `evidence_refs_json`/`quality_json` 에 `actor_verified:false` 로 남긴다. (러너) 잡을 만든 사용자의 owner_sub 를 `rr_jobs.owner_sub` 에서 승계한다. 익명(둘 다 없음)은 쓰기 불가·`visibility='org'` 행 읽기만. 조회는 `WHERE owner_sub=?` 를 기본으로 하고 `visibility='org'` 행만 예외로 읽는다 |
| 상태 enum | `CHECK(status IN (...))` 로 DB 에서 막는다. 값 목록은 §0 정의를 그대로 쓴다 |
| 스키마 버전 | `PRAGMA user_version` 에 정수 버전(정본). 마이그레이션은 `ALTER TABLE … ADD COLUMN` 과 인덱스 추가만 허용하고 컬럼 삭제·타입 변경은 하지 않는다(새 표를 만들고 복사). 적용 절차·이력 표·다운그레이드 금지는 §5.2.5 (6) |
| 삭제 | 행 삭제 없음. 대체는 `superseded_by`, 폐기는 status 값으로 표기한다 |

### 5.2.2 DDL 전문

A. 정체성·소스(§2 정의).

```sql
CREATE TABLE IF NOT EXISTS rr_projects (
  id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  code TEXT NOT NULL, name TEXT, stage TEXT,
  predecessor_project_id TEXT,                  -- 계보(UI 입력) → RA revision_of
  adh_team TEXT, adh_group TEXT,                -- 사용자 확인값, 자동 채움 금지
  ra_entity_id INTEGER, adh_character_record_id TEXT,
  character_status TEXT CHECK(character_status IN ('seed','panel','confirmed')) DEFAULT 'seed',
  created_at INTEGER, updated_at INTEGER,
  UNIQUE(owner_sub, code));

CREATE TABLE IF NOT EXISTS rr_sources (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('mcad','dyna','dyna_result','ecad')),
  app_key TEXT, ref_json TEXT NOT NULL, ref_key TEXT NOT NULL,   -- ref_key = kind:app_key:정렬 ref 문자열
  bridge_declared INTEGER DEFAULT 0, probe_json TEXT, probe_at INTEGER,
  adapter_version TEXT, created_at INTEGER,
  UNIQUE(project_id, ref_key));
```

B. 스냅샷·IR(§2).

```sql
CREATE TABLE IF NOT EXISTS rr_snapshots (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  ir_version TEXT NOT NULL, ir_hash TEXT NOT NULL,
  ir_json TEXT NOT NULL,                        -- rr_ir 원본(유일)
  source_ids_json TEXT NOT NULL,                -- [{kind, app_key, ref, hash, tool_version, tol_params}]
  kinds_json TEXT NOT NULL,                     -- ['mcad','dyna',…]
  node_count INTEGER, edge_count INTEGER, missing_json TEXT, warnings_n INTEGER,
  degraded TEXT,                                -- null | 'mcp_degraded'
  adapter_versions_json TEXT, ra_entity_id INTEGER, adh_digest_record_id TEXT,
  created_at INTEGER,
  UNIQUE(project_id, ir_hash));
CREATE INDEX IF NOT EXISTS ix_rr_snapshots_project ON rr_snapshots(project_id, created_at);

CREATE TABLE IF NOT EXISTS rr_snapshot_calls (                -- 행 정의는 §2.11.4
  call_id TEXT PRIMARY KEY,                     -- '<snapshot_id[:8]>-<seq:03d>'
  snapshot_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  seq INTEGER NOT NULL, source_kind TEXT NOT NULL, app_key TEXT,
  channel TEXT NOT NULL CHECK(channel IN ('mcp','rest')), tool TEXT NOT NULL,
  args_json TEXT, args_hash TEXT, ok INTEGER NOT NULL DEFAULT 1, http_status INTEGER,
  response_sha256 TEXT, response_gz BLOB, response_bytes INTEGER,
  started_at INTEGER, duration_ms INTEGER, error TEXT);
CREATE INDEX IF NOT EXISTS ix_rr_calls_snapshot ON rr_snapshot_calls(snapshot_id, seq);

CREATE TABLE IF NOT EXISTS rr_ir_nodes (
  snapshot_id TEXT NOT NULL, nid TEXT NOT NULL, owner_sub TEXT NOT NULL,
  kind TEXT, source_kind TEXT, name TEXT, name_norm TEXT,
  ckey TEXT, dn TEXT, geom_fp TEXT, asm_key TEXT, material_norm TEXT,
  size_sorted_json TEXT, volume REAL, attrs_json TEXT,
  PRIMARY KEY(snapshot_id, nid));
CREATE INDEX IF NOT EXISTS ix_rr_nodes_ckey ON rr_ir_nodes(ckey);
CREATE INDEX IF NOT EXISTS ix_rr_nodes_name ON rr_ir_nodes(name_norm);
CREATE INDEX IF NOT EXISTS ix_rr_nodes_fp ON rr_ir_nodes(geom_fp);

CREATE TABLE IF NOT EXISTS rr_ir_edges (
  snapshot_id TEXT NOT NULL, eid TEXT NOT NULL, owner_sub TEXT NOT NULL,
  kind TEXT NOT NULL, kind_family TEXT NOT NULL, a TEXT NOT NULL, b TEXT NOT NULL,
  ck_a TEXT, ck_b TEXT, subject_key TEXT, status TEXT, attrs_json TEXT,
  PRIMARY KEY(snapshot_id, eid));
CREATE INDEX IF NOT EXISTS ix_rr_edges_subject ON rr_ir_edges(subject_key);
CREATE INDEX IF NOT EXISTS ix_rr_edges_kind ON rr_ir_edges(snapshot_id, kind);
```

C. 원장(§2, 재적용 대상).

```sql
CREATE TABLE IF NOT EXISTS rr_part_keys (
  ckey TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private',
  status TEXT NOT NULL CHECK(status IN ('candidate','confirmed','merged')) DEFAULT 'candidate',
  merged_into TEXT, display_name TEXT,          -- §2.7.3 display_name(RA part 축 value)
  name_norm_canon TEXT NOT NULL, geom_bucket TEXT NOT NULL, material_norm TEXT NOT NULL,
  aliases_json TEXT,                            -- [{project_id, domain, label, local_key, name_norm}] 동의어 원장(§2.7.3)
  ra_part_entity_id INTEGER, first_project_id TEXT, first_snapshot_id TEXT, first_nid TEXT,
  n_projects INTEGER DEFAULT 1, n_snapshots INTEGER DEFAULT 1,
  merge_evidence_json TEXT,                     -- §2.7.3 자동 승계 근거 {method, score, base_snapshot_id, target_snapshot_id, base_nid, target_nid}(사람 병합은 NULL)
  created_by TEXT, decided_by TEXT, decided_at INTEGER, created_at INTEGER, updated_at INTEGER);   -- decided_by = 'code:pair_correspondence' | 사용자 sub
CREATE INDEX IF NOT EXISTS ix_rr_part_keys_canon ON rr_part_keys(name_norm_canon);
CREATE INDEX IF NOT EXISTS ix_rr_part_keys_merged ON rr_part_keys(merged_into);

CREATE TABLE IF NOT EXISTS rr_sameas (
  id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  scope TEXT NOT NULL CHECK(scope IN ('intra','pair','global')),   -- intra: 한 스냅샷 안 mcad↔dyna↔ecad, pair: base↔target, global: ckey 쌍(§2.6.2 1단계)
  pair_key TEXT NOT NULL,                       -- intra: project_id, pair: 정렬한 두 project_id '|' 결합, global: '-'
  a_stable TEXT NOT NULL, b_stable TEXT NOT NULL,   -- stable key(§2.6.2 1단계): mcad canon_key · dyna name_norm_canon+'@'+elem_class · ecad refdes · global 은 ckey
  method TEXT, score REAL, status TEXT NOT NULL CHECK(status IN ('confirmed','rejected')),
  evidence TEXT, decided_by TEXT, decided_at INTEGER, snapshot_id_at_decision TEXT,
  UNIQUE(scope, pair_key, a_stable, b_stable));

CREATE TABLE IF NOT EXISTS rr_iface_ledger (
  project_id TEXT NOT NULL, pair_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  kind_override TEXT, status TEXT NOT NULL CHECK(status IN ('confirmed','rejected','manual')),
  note TEXT, geom_fp_a TEXT, geom_fp_b TEXT, needs_review INTEGER DEFAULT 0,
  decided_by TEXT, decided_at INTEGER, snapshot_id_at_decision TEXT,
  PRIMARY KEY(project_id, pair_key));

CREATE TABLE IF NOT EXISTS rr_dim_vocab (                     -- 행 정의는 §2.8
  name TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('overall','thickness','gap','offset','count','param','result','other')),
  unit TEXT, description TEXT, synonyms_json TEXT, stop_tokens_json TEXT,
  tol_abs REAL, tol_rel REAL,                   -- §3.3.4 dims_named 변경 임계(없으면 0.02 mm · 1%)
  vocab_version TEXT, created_by TEXT, created_at INTEGER);

CREATE TABLE IF NOT EXISTS rr_dim_defs (                      -- 행 정의는 §2.8
  project_id TEXT NOT NULL, name TEXT NOT NULL, owner_sub TEXT NOT NULL,
  extractor TEXT NOT NULL,                      -- §2.8 제한 문법 문자열(node[ck=…].attr · edge[name=A|B].attr · dim(a)-dim(b) · const:…)
  created_by TEXT, created_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(project_id, name));
```

D. 상태·diff(§3).

```sql
CREATE TABLE IF NOT EXISTS rr_states (
  snapshot_id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  state_json TEXT NOT NULL, feature_json TEXT NOT NULL,
  rule_hits_json TEXT, character_seed_json TEXT, gates_json TEXT NOT NULL,
  summary_text TEXT, summary_status TEXT CHECK(summary_status IN ('ok','lint_failed')),   -- §3.2.7
  blocked INTEGER DEFAULT 0, state_version TEXT, rule_version TEXT, taxonomy_version TEXT, computed_at INTEGER);

CREATE TABLE IF NOT EXISTS rr_diffs (
  id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  base_snapshot_id TEXT NOT NULL, target_snapshot_id TEXT NOT NULL,
  base_project_id TEXT NOT NULL, target_project_id TEXT NOT NULL,
  pair_kind TEXT CHECK(pair_kind IN ('same_project_revision','cross_project')),
  diff_version TEXT NOT NULL, diff_json TEXT NOT NULL, summary_text TEXT NOT NULL,
  summary_status TEXT CHECK(summary_status IN ('ok','lint_failed')),
  stats_json TEXT, comparability_json TEXT, gates_json TEXT, diff_hash TEXT,
  ra_entity_id INTEGER, created_at INTEGER,
  UNIQUE(base_snapshot_id, target_snapshot_id));

CREATE TABLE IF NOT EXISTS rr_diff_events (
  diff_id TEXT NOT NULL, cid TEXT NOT NULL, owner_sub TEXT NOT NULL,
  layer TEXT NOT NULL CHECK(layer IN ('structural','parametric','semantic')),
  code TEXT NOT NULL, change_kind TEXT, subject_key TEXT, ckeys_json TEXT,
  magnitude REAL, unit TEXT, rel REAL,
  confidence TEXT CHECK(confidence IN ('high','medium','low')),
  design_relevant INTEGER DEFAULT 1, unconfirmed INTEGER DEFAULT 0, excluded_reason TEXT,
  text TEXT,                                    -- 정규 표기(§3.4.1)
  PRIMARY KEY(diff_id, cid));
CREATE INDEX IF NOT EXISTS ix_rr_events_code ON rr_diff_events(code);
CREATE INDEX IF NOT EXISTS ix_rr_events_kind ON rr_diff_events(change_kind);
CREATE INDEX IF NOT EXISTS ix_rr_events_subject ON rr_diff_events(subject_key);
```

E. 타깃·워크플로(§6).

```sql
CREATE TABLE IF NOT EXISTS rr_targets (
  target_key TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('snap','diff')), ref_id TEXT NOT NULL,
  project_id TEXT NOT NULL, base_project_id TEXT, ir_hash TEXT NOT NULL,
  principal_json TEXT, consent_at INTEGER, roster_frozen_at INTEGER,
  level TEXT NOT NULL DEFAULT 'C0',             -- C0 | C1 | C2 | C2(closed) | C3
  close_level TEXT,                             -- Settings risk_default_close_level 스냅샷(C2|C3)
  verdict_candidate TEXT, verdict_final TEXT CHECK(verdict_final IN ('go','conditional','no-go','undetermined')),
  verdict_note TEXT, verdict_by TEXT, verdict_at INTEGER,
  external_sync_json TEXT NOT NULL,             -- §5.5.3
  superseded_by TEXT, report_ids_json TEXT, planner_version TEXT,
  created_at INTEGER, updated_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_targets_project ON rr_targets(project_id, created_at);

CREATE TABLE IF NOT EXISTS rr_roster (                        -- §6.3
  target_key TEXT NOT NULL, agent_key TEXT NOT NULL, owner_sub TEXT NOT NULL, domain TEXT NOT NULL,
  relevance REAL, rank_in_domain INTEGER, ecad_dependent INTEGER DEFAULT 0, frozen_at INTEGER,
  PRIMARY KEY(target_key, agent_key));

CREATE TABLE IF NOT EXISTS rr_coverage (                      -- §6.8.1
  target_key TEXT NOT NULL, agent_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  domain TEXT NOT NULL, tier TEXT, origin TEXT CHECK(origin IN ('primary','counter')),
  status TEXT NOT NULL CHECK(status IN ('pending','assigned','running','done','done_weak','abstain',
                                        'failed','skipped','deferred','carried')) DEFAULT 'pending',
  cycle INTEGER DEFAULT 1, retry INTEGER DEFAULT 0,
  panel_id TEXT, opinion_id TEXT, adh_record_id TEXT, ra_assessment_id INTEGER,
  carried_from_opinion_id TEXT, reason TEXT,
  model TEXT,                                   -- 종결 시 그 패널의 rr_panels.model_json.model 사본(진행판·통합 보고서 모델 혼합 표, D6)
  started_at INTEGER, finished_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, agent_key));
-- 부분 유니크 인덱스 rr_cov_active(§6.8.1): 활성(assigned|running) 행만 담는 작은 인덱스로 편성기의 rowcount 선점 UPDATE 와 불변식 검사를 빠르게 한다.
-- 다른 타깃 동시 착석은 막지 않는다(Tier A 는 두 타깃이 같은 대표 15명을 원한다). '전문가 전역 동시 1석' 정책으로 바꾸려면 열을 (agent_key) 로 줄이는 마이그레이션 1건이다.
CREATE UNIQUE INDEX IF NOT EXISTS rr_cov_active ON rr_coverage(agent_key, target_key) WHERE status IN ('assigned','running');
CREATE INDEX IF NOT EXISTS ix_rr_cov_status ON rr_coverage(target_key, status);

CREATE TABLE IF NOT EXISTS rr_panels (
  id TEXT PRIMARY KEY, target_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  panel_no INTEGER NOT NULL, tier TEXT, seats_json TEXT NOT NULL,
  chair_template TEXT NOT NULL DEFAULT 'risk-review', modifiers_json TEXT, rounds INTEGER,
  engine TEXT CHECK(engine IN ('web','mcp')), tool_mode TEXT CHECK(tool_mode IN ('tools','evidence_only')),
  conv_id TEXT, report_id INTEGER,
  status TEXT NOT NULL CHECK(status IN ('planned','running','done','error')) DEFAULT 'planned',
  decision_text TEXT, risk_spec_json TEXT, risk_spec_parsed INTEGER DEFAULT 0,
  quality_json TEXT, llm_calls INTEGER, llm_calls_planned INTEGER,
  budget_json TEXT,                             -- §6.10.2 {S, R, T, est_low, est_high, cap, rounds_planned, tools_planned}
  evidence_refs_json TEXT,                      -- 이 패널 브리프에 실린 E0~E9 항목의 ref 목록(인용 추적)
  model_json TEXT,                              -- D6 모델 출처 {runtime, provider, model, endpoint_host, captured ∈ health_snapshot|caller_reported|unavailable, engine_rev, chair_rev, seat_contract_rev, model_end?}(§6.7.2 1·7단계, §6.11)
  retry INTEGER DEFAULT 0, error TEXT, started_at INTEGER, ended_at INTEGER, created_at INTEGER,
  UNIQUE(target_key, panel_no));

CREATE TABLE IF NOT EXISTS rr_jobs (
  id TEXT PRIMARY KEY, target_key TEXT NOT NULL, owner_sub TEXT NOT NULL, tier TEXT,
  state TEXT NOT NULL CHECK(state IN ('queued','running','paused','cancelling','cancelled','completed','failed')),
  pause_reason TEXT CHECK(pause_reason IN ('diminishing','daily_cap','user')),
  concurrency INTEGER DEFAULT 1, params_json TEXT, progress_json TEXT,
  panels_done INTEGER DEFAULT 0, panels_total INTEGER, error TEXT, created_at INTEGER, updated_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_jobs_state ON rr_jobs(state, created_at);
```

F. 서술·판정(§4).

```sql
CREATE TABLE IF NOT EXISTS rr_seat_opinions (
  opinion_id TEXT PRIMARY KEY, target_key TEXT NOT NULL, panel_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  agent_key TEXT NOT NULL, domain TEXT NOT NULL,
  origin TEXT CHECK(origin IN ('primary','counter','adversary','new')),   -- adversary·new 는 원장 미집계 의견(§6.7 8단계·§6.8.3 4)
  cycle INTEGER DEFAULT 1,
  opinion_json TEXT NOT NULL,                   -- seat_opinion 전체(§0.1.3)
  final_stance TEXT CHECK(final_stance IN ('agree','conditional','oppose','abstain')),
  tool_calls_n INTEGER, tool_calls_ok INTEGER, knowledge_hits_n INTEGER,
  cited_refs_json TEXT, quality_json TEXT, raised_finding_ids_json TEXT,
  excerpt_for_rag TEXT,                         -- ≤1500자, E7·AIDataHub 섹션 2 의 원천
  adh_record_id TEXT, ra_assessment_id INTEGER, created_at INTEGER,
  UNIQUE(target_key, agent_key, cycle));
CREATE INDEX IF NOT EXISTS ix_rr_opinions_agent ON rr_seat_opinions(agent_key, created_at);

CREATE TABLE IF NOT EXISTS rr_findings (
  finding_id TEXT PRIMARY KEY, claim_uid TEXT NOT NULL UNIQUE,   -- '<panel_id>#F1' | '#G1'
  target_key TEXT NOT NULL, panel_id TEXT NOT NULL, opinion_id TEXT,
  project_id TEXT NOT NULL, snapshot_id TEXT, diff_id TEXT, owner_sub TEXT NOT NULL,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private',
  direction TEXT NOT NULL CHECK(direction IN ('risk','improvement','neutral')),
  domain TEXT, mechanism TEXT, mechanism_detail TEXT, mechanism_free TEXT,
  change_kind TEXT, subject_key TEXT, ckeys_json TEXT, trigger_condition TEXT,
  severity TEXT CHECK(severity IN ('경미','중대','치명')), sev3 INTEGER,
  judgement TEXT CHECK(judgement IN ('OK','WARNING','FAIL','undetermined')),
  detectability TEXT, detect_tool TEXT,
  evidence_grade TEXT, precedent TEXT CHECK(precedent IN ('in_range','out_of_range','none')),
  dangling INTEGER DEFAULT 0, cluster_key TEXT NOT NULL,
  finding_json TEXT NOT NULL,                   -- finding 전체 + feature_snapshot + precedent_refs
  status TEXT NOT NULL CHECK(status IN ('open','verified','dismissed','mitigated','superseded')) DEFAULT 'open',
  status_reason TEXT, superseded_by TEXT,
  ra_entity_id INTEGER, adh_record_id TEXT,
  taxonomy_version TEXT, rule_version TEXT, ir_version TEXT, diff_version TEXT,
  created_at INTEGER, updated_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_findings_cluster ON rr_findings(cluster_key);
CREATE INDEX IF NOT EXISTS ix_rr_findings_subject ON rr_findings(subject_key);
CREATE INDEX IF NOT EXISTS ix_rr_findings_mech ON rr_findings(mechanism, mechanism_detail, change_kind);
CREATE INDEX IF NOT EXISTS ix_rr_findings_project ON rr_findings(project_id, status);

CREATE TABLE IF NOT EXISTS rr_registry (
  target_key TEXT NOT NULL, cluster_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private',
  merged_json TEXT NOT NULL,                    -- 대표 finding + member finding_ids + resolving_checks 집합 + precedent_clusters
  support INTEGER DEFAULT 1, contested INTEGER DEFAULT 0,
  direction TEXT, mechanism TEXT, mechanism_detail TEXT, change_kind TEXT, subject_key TEXT,
  severity TEXT, sev3 INTEGER, judgement TEXT, evidence_grade TEXT, precedent TEXT,
  weak_subject INTEGER DEFAULT 0, priority REAL,   -- §4.3.2 · §4.7.1
  status TEXT NOT NULL CHECK(status IN ('open','verified','dismissed','mitigated','superseded')) DEFAULT 'open',
  verified_by_json TEXT, stale_json TEXT,       -- §4.8 {<T′>: {stale: bool, unraised: bool}}
  superseded_by TEXT, ra_entity_id INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, cluster_key));
CREATE INDEX IF NOT EXISTS ix_rr_registry_cluster ON rr_registry(cluster_key);
CREATE INDEX IF NOT EXISTS ix_rr_registry_subject ON rr_registry(subject_key, status);

CREATE TABLE IF NOT EXISTS rr_claim_refs (
  claim_uid TEXT NOT NULL, ref_type TEXT NOT NULL, ref TEXT NOT NULL, quote TEXT,
  owner_sub TEXT NOT NULL, target_key TEXT NOT NULL, dangling INTEGER DEFAULT 0,
  PRIMARY KEY(claim_uid, ref_type, ref));
CREATE INDEX IF NOT EXISTS ix_rr_claim_refs_ref ON rr_claim_refs(ref);

CREATE TABLE IF NOT EXISTS rr_character (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  facet TEXT NOT NULL CHECK(facet IN ('intent','constraint','anomaly','lineage','vulnerability','strength','tradeoff','unknown')),
  tag TEXT, tags_json TEXT,                     -- tag = 대표 태그(통제 어휘 첫 항목, 없으면 NULL — 병합 키), tags_json = 전체 태그 배열(§4.6.4 2)
  statement TEXT NOT NULL, polarity TEXT, cites_json TEXT, by_json TEXT,   -- by_json = 좌석 키 배열(§4.6.1 by)
  variants_json TEXT, dissent_json TEXT,        -- §4.6.4 2 후속 문장·상반 polarity 축어 보존
  first_target_key TEXT, support_panels INTEGER DEFAULT 1, support_targets INTEGER DEFAULT 1, confidence REAL,
  needs_review INTEGER DEFAULT 0,               -- §4.8 5
  status TEXT NOT NULL CHECK(status IN ('seed','panel','confirmed','superseded')),
  superseded_by TEXT, decided_by TEXT, decided_at INTEGER, created_at INTEGER, updated_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_character_project ON rr_character(project_id, facet, status);
CREATE INDEX IF NOT EXISTS ix_rr_character_tag ON rr_character(tag);
```

G. 학습(§7).

```sql
CREATE TABLE IF NOT EXISTS rr_iface_alias (
  alias_key TEXT PRIMARY KEY,                   -- '<ckey_a>|<ckey_b>' 정렬
  canonical_a TEXT NOT NULL, canonical_b TEXT NOT NULL, owner_sub TEXT NOT NULL,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private',
  aliases_json TEXT NOT NULL,                   -- [{name_a, name_b, asm_key_a, asm_key_b, project_id, snapshot_id}]
  source TEXT NOT NULL CHECK(source IN ('auto','human')), score REAL,
  ra_alias_ids_json TEXT, n_targets INTEGER DEFAULT 0, created_at INTEGER, updated_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_alias_a ON rr_iface_alias(canonical_a);
CREATE INDEX IF NOT EXISTS ix_rr_alias_b ON rr_iface_alias(canonical_b);

CREATE TABLE IF NOT EXISTS rr_delta_priors (
  change_kind TEXT NOT NULL, mechanism TEXT NOT NULL, mechanism_detail TEXT NOT NULL,
  n_raised INTEGER DEFAULT 0, n_targets INTEGER DEFAULT 0, n_verified INTEGER DEFAULT 0, n_dismissed INTEGER DEFAULT 0,
  n_improvement INTEGER DEFAULT 0, sev_hist_json TEXT, top_resolving_checks_json TEXT,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private', stats_version TEXT, updated_at INTEGER,
  PRIMARY KEY(change_kind, mechanism, mechanism_detail));
-- rr_delta_priors 의 n_raised·n_targets·n_improvement·sev_hist_json·top_resolving_checks_json 은 아래 기여 표의 합으로만 쓴다(§4.7.1, 증분 += 없음).

CREATE TABLE IF NOT EXISTS rr_delta_contrib (                 -- §4.7.1 타깃별 기여(등록부 병합마다 UPSERT, 멱등)
  change_kind TEXT NOT NULL, mechanism TEXT NOT NULL, mechanism_detail TEXT NOT NULL, target_key TEXT NOT NULL,
  owner_sub TEXT NOT NULL,
  n_raised INTEGER DEFAULT 0, n_improvement INTEGER DEFAULT 0,
  sev_hist_json TEXT, resolving_checks_json TEXT, updated_at INTEGER,
  PRIMARY KEY(change_kind, mechanism, mechanism_detail, target_key));
CREATE INDEX IF NOT EXISTS ix_rr_delta_contrib_target ON rr_delta_contrib(target_key);

CREATE TABLE IF NOT EXISTS rr_labels (
  id TEXT PRIMARY KEY, finding_id TEXT NOT NULL, pattern_id TEXT, project_id TEXT, owner_sub TEXT NOT NULL,
  source TEXT NOT NULL CHECK(source IN ('incident','test_run','voc','sim','expert_review','manual')),
  outcome TEXT NOT NULL CHECK(outcome IN ('confirmed','refuted','inconclusive')),
  severity_observed TEXT, matched_by TEXT NOT NULL CHECK(matched_by IN ('auto','manual')),
  match_score REAL, evidence_ref TEXT NOT NULL, evidence_note TEXT, occurred_at INTEGER,
  labeled_by TEXT, labeled_at INTEGER,
  UNIQUE(finding_id, source, evidence_ref));
CREATE INDEX IF NOT EXISTS ix_rr_labels_finding ON rr_labels(finding_id);
CREATE INDEX IF NOT EXISTS ix_rr_labels_pattern ON rr_labels(pattern_id);

CREATE TABLE IF NOT EXISTS rr_patterns (
  id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private',
  cluster_key_norm TEXT NOT NULL,               -- subject 를 별칭 수준으로 정규화한 cluster_key
  mechanism TEXT, mechanism_detail TEXT, change_kind TEXT, subject_class TEXT,
  status TEXT NOT NULL CHECK(status IN ('candidate','known','rule','predictor','deprecated','suspended')),
  n_findings INTEGER, n_targets INTEGER, n_projects INTEGER, n_experts INTEGER,
  n_confirmed INTEGER DEFAULT 0, n_refuted INTEGER DEFAULT 0, precision REAL,
  feature_ranges_json TEXT, card_record_id TEXT, design_trait_tag TEXT,
  curated_by TEXT, promoted_at INTEGER, suspended_reason TEXT, created_at INTEGER, updated_at INTEGER,
  UNIQUE(cluster_key_norm));
CREATE INDEX IF NOT EXISTS ix_rr_patterns_status ON rr_patterns(status);

CREATE TABLE IF NOT EXISTS rr_rules (
  id TEXT PRIMARY KEY, pattern_id TEXT, rule_version TEXT NOT NULL,
  mechanism TEXT, mechanism_detail TEXT, change_kind TEXT,
  condition_json TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('경미','중대','치명')),
  why_it_matters TEXT NOT NULL, fix_hint TEXT, backtest_json TEXT,
  source TEXT NOT NULL CHECK(source IN ('seed','pattern')),
  status TEXT NOT NULL CHECK(status IN ('draft','active','retired')) DEFAULT 'draft',
  activated_by TEXT, activated_at INTEGER, created_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_rules_status ON rr_rules(status);

CREATE TABLE IF NOT EXISTS rr_metrics (
  period TEXT NOT NULL, dimension TEXT NOT NULL CHECK(dimension IN ('expert','domain','mechanism','pattern','project','global')),
  key TEXT NOT NULL, metric TEXT NOT NULL, value REAL, n INTEGER, computed_at INTEGER,
  visibility TEXT CHECK(visibility IN ('private','org')) DEFAULT 'private',
  PRIMARY KEY(period, dimension, key, metric));

CREATE TABLE IF NOT EXISTS rr_curation_queue (
  id TEXT PRIMARY KEY, owner_sub TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('unclassified_code','pattern_candidate','label_match','x_tag_promote')),
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('open','done','rejected')) DEFAULT 'open',
  decision_json TEXT, decided_by TEXT, decided_at INTEGER, created_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_queue ON rr_curation_queue(kind, status, created_at);
```

H. 3자 id 매핑(§5.5).

```sql
CREATE TABLE IF NOT EXISTS rr_id_map (
  portal_kind TEXT NOT NULL CHECK(portal_kind IN ('project','snapshot','diff','opinion','registry','character','pattern','expert','trait')),
  portal_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  ra_entity_id INTEGER, ra_type_slug TEXT, adh_record_id TEXT, adh_external_id TEXT,
  ra_synced_at INTEGER, adh_synced_at INTEGER,
  PRIMARY KEY(portal_kind, portal_id));
CREATE INDEX IF NOT EXISTS ix_rr_id_map_ra ON rr_id_map(ra_entity_id);
CREATE INDEX IF NOT EXISTS ix_rr_id_map_adh ON rr_id_map(adh_record_id);
```

### 5.2.3 조회 경로와 인덱스가 답하는 질문

| 질문 | 조인 |
|---|---|
| 이 엣지·이 변경에 대해 누가 뭐라 했나 | `rr_claim_refs(ref=?)` → `claim_uid` → `rr_findings` 또는 `rr_character` |
| 이 파트 계열(ckey)에 붙은 finding 은 | `rr_ir_nodes.ckey` ↔ `rr_findings.ckeys_json`(LIKE) 또는 `rr_registry.subject_key` LIKE `'%'||ckey||'%'` |
| 같은 계면이 다른 과제에서 어떤 finding 을 낳았나 | `rr_iface_alias(canonical_a|b)` → `alias_key` → `rr_registry.subject_key` 정확 매치 |
| 이 전문가가 과거 유사 과제에서 뭐라 했나 | `rr_seat_opinions(agent_key)` 최신순 → `excerpt_for_rag`, `raised_finding_ids_json` |
| 이 변경 조합의 선례 정밀도는 | `rr_delta_priors(change_kind, mechanism, mechanism_detail)` |
| 어떤 스냅샷이 같은 성격 태그를 가졌나 | `rr_character(tag, status)` → `project_id`(RA 는 `exhibits` 로 동일 질문) |
| 커버리지 진행판 | `rr_coverage(target_key, status)` 집계 15×10 |

### 5.2.4 크기·보존

스냅샷 1건은 `ir_json` ≈0.4~0.9 MB, 호출 로그 gzip ≈0.2~0.5 MB, 펼침 표 ≈0.3 MB 다. 과제 50건·스냅샷 200건이면 ≈300 MB 로 sqlite 단일 파일 범위 안이고 매니페스트 `resources.memory_gb 2` 안에서 WAL·인덱스가 돈다. 삭제는 하지 않고 `superseded_by` 로 닫는다. 백업·복원·이관은 §5.2.5 다.

### 5.2.5 데이터 지속·백업·이관

**(1) 지속 경계 — 쓰기는 `$HEAX_DATA_DIR` 아래뿐이다.** 앱이 만드는 파일은 `risk_review.db`(+`-wal`·`-shm`) · `secrets.env`(0600) · `origin.json` · `exports/`(JSONL) 넷이고 전부 `$HEAX_DATA_DIR` 직속이다. 이 디렉터리는 HEAX 런처가 호스트 `HEAXHub/var/app_data/hwax_risk/` 를 만들어 SIF 에 `/data` 로 bind 하는 곳이라 앱 재시작·SIF 재빌드·`redeploy-app.sh hwax-risk`·HEAXHub `git pull` 을 거쳐도 남는다(런처는 이 디렉터리를 지우지 않는다). SIF 내부 `/app/*`·workspace·`/tmp` 는 재빌드·재기동에 사라지므로 어떤 상태도 두지 않는다(런타임 자산 JSON 6종은 읽기 전용이라 SIF 안 `backend/app/assets/` 가 맞다). 기동 시 `config.py` 가 데이터 루트(`HWAXRISK_DATA_DIR > HEAX_DATA_DIR > <리포>/data`)를 `mkdir -p` 하고 `os.access(root, W_OK)` 실패면 기동을 중단해 헬스 20 초 안에 500 으로 드러낸다(조용한 폴백 금지).

**(2) `origin.json` — 이 데이터가 어느 박스의 몇 버전인지.** 기동마다 `{"hostname": socket.gethostname(), "app_version": <pyproject version>, "schema_version": <PRAGMA user_version>, "written_at": <epoch>}` 를 `$HEAX_DATA_DIR/origin.json` 에 다시 쓴다(apptainer 는 `--hostname` 없이 뜨므로 SIF 안에서도 호스트 이름이 잡힌다). Drive tar 에 함께 실리므로 복원·이관 전에 출처를 파일 하나로 확인하고, (5)·(7) 의 박스 판정이 이 값을 읽는다.

**(3) 백업 — `appdata-to-drive.sh`.** HEAXHub `deploy/apptainer/appdata-to-drive.sh` 가 `var/app_data` 전체를 tar 로 묶어 Drive `<HEAX_DRIVE_REMOTE 부모>/app-data/app-data-<UTC ts>/` 와 `latest/` 에 올린다(보존 `HEAX_DRIVE_RETAIN` 기본 5). `*.db` 는 `sqlite3 .backup` 원자 스냅샷으로 교체되고 `-wal/-shm` 은 제외되므로 WAL 을 켠 채 쓰기 중이어도 일관된 사본이다 — 파일명을 `risk_review.db` 로 고정한 이유이고, `.sqlite` 였다면 원본 파일 복사가 되어 체크포인트 전 WAL 내용이 빠진다. 주기 — (a) dev 에서 `HWAXPortal/infra/scripts/build-all-to-drive.sh` 가 매 실행마다 호출한다(:84, 실패 비치명). (b) 운영 개시(P4 완료) 후 dev crontab 에 일 1회 `bash /home/koopark/claude/HEAXHub/deploy/apptainer/appdata-to-drive.sh` 항목을 추가한다(AIDataHub `backup-to-drive.sh` 04:45 항목과 같은 형식, 사용자 몫·앱 코드 없음). (c) 스키마 마이그레이션 직전과 export 직전에는 (6)·(5) 의 로컬 사본이 따로 생긴다. 앱은 백업 시각을 DB 에 적지 않는다. 주의 — 이 tar 에는 `secrets.env` 도 실린다(§0.4.4). 제외 규칙(HEAX 스크립트 `--exclude` additive 또는 앱 측 암호화 저장)은 §10 결정이고, 결정 전에는 `secrets.env` 의 PAT 3종을 무기한(`ttl_days 0`) 이 아니라 365 일로 발급해 회전 가능하게 둔다.

**(4) 복원.** 단일 앱 복원은 Drive tar 에서 `hwax_risk/risk_review.db` 만 꺼내 한다 — ① HEAX 인스턴스 `heax_app_hwax_risk` 정지 ② 라이브 `risk_review.db`·`-wal`·`-shm` 을 `risk_review.db.pre-restore-<ts>` 로 이동 ③ 스냅샷 파일을 `risk_review.db` 로 복사(권한은 런처 사용자) ④ 기동 → `origin.json` 과 `GET /api/health` 의 `schema_version` 이 앱 코드와 맞는지 확인(낮으면 (6) 이 자동 승급, 높으면 기동 실패). 전체 복원 `HEAX_RESTORE_APPDATA=1 appdata-from-drive.sh` 는 `var/app_data` 전체(다른 앱 데이터 포함)를 Drive `latest/` 로 덮으므로 hwax_risk 단독 사고에는 쓰지 않는다. `appdata-merge-from-drive.sh` 는 라이브 DB 가 있으면 `_materialtwin_merge.py` 를 돌리지만 PLAN 표(materialtwin 표)가 원본에 없어 `continue` 로 무동작이며, 실행마다 `risk_review.db.pre-merge-<ts>` 사본을 남긴다 — 운영자가 5개 초과분을 지운다(앱은 지우지 않는다).

**(5) cae00 이관.** 첫 배포 — dev `build-all-to-drive.sh` → Drive `latest/` → cae00 `deploy-all-from-drive.sh` 안의 `appdata-merge-from-drive.sh` 가 `var/app_data/hwax_risk/risk_review.db` 가 **없을 때만** 시드 복사하고, 비-DB 파일(`origin.json`·`secrets.env`)도 라이브에 없을 때만 복사한다. 이후 — cae00 라이브 DB 는 배포가 건드리지 않으므로 dev→cae00 이동은 앱 `GET /api/export?since=<epoch>`(JSONL, 첫 줄 헤더 `{"schema_version", "app_version", "origin"}`, 이어서 표 순서 §5.2.2 A→H 로 `{"table", "row"}` 줄) → cae00 `POST /api/import`(P1+, `export.py`) 뿐이다. import 는 별도 병합 규칙을 두지 않고 §4.7.1 등록부 병합·§2.10 원장 재적용 규칙을 그대로 재사용한다 — 같은 `claim_uid` 는 지지+1 병합, 다르면 add(dissent/stale), 사람 확정(`human`·`confirmed`)이 자동(`auto`·`candidate`)을 이긴다. 시크릿은 이관 대상이 아니다 — 포털 PAT 는 발급 박스 포털의 JWKS 로만 검증되고 heax PAT·AIDH 키도 박스별 DB 에 있으므로 dev 의 `secrets.env` 는 cae00 에서 전부 401 이다. 규칙 — 기동 시 `origin.json.hostname` 이 현재 호스트와 다르면(첫 배포 시드 직후가 그렇다) 앱은 `secrets.env` 를 무효로 보고 `external_sync` 를 `unavailable` 로 시작하며 SettingsPage 에 '이 박스의 자격을 입력' 을 띄운다. 운영자는 cae00 포털·heax·AIDataHub 에서 서비스 PAT·heax PAT·API 키를 새로 발급해 cae00 `secrets.env` 를 채우고 앱을 재기동한 뒤(시크릿은 기동 시 로드, 첫 기동이 이미 `origin.json` 을 cae00 호스트명으로 다시 썼으므로 재기동부터는 유효) '재동기' 를 누른다(§5.5.3).

**(6) 스키마 마이그레이션 규칙 — `PRAGMA user_version` + 순서 리스트, alembic 미사용.** alembic 은 쓰지 않는다(SQLAlchemy 의존이 없고 stdlib sqlite3 만 쓴다, `pyproject` deps §0.4.1). 정본은 `PRAGMA user_version` 정수이고, `risk_store.py` 의 `MIGRATIONS: list[tuple[int, list[str]]]`(버전 오름차순, v1 = §5.2.2 DDL 전문)를 기동 시 `user_version < n` 인 항목만 순서대로 **한 버전 = 한 트랜잭션**으로 적용하고 같은 트랜잭션에서 `PRAGMA user_version = n` 을 올린다. 이력은 rr_ 접두가 아닌 `_schema_migrations(version INTEGER PRIMARY KEY, applied_at INTEGER, app_version TEXT)` 에 남긴다(33 표 밖의 살림 표, export 대상 아님). 허용 연산은 `CREATE TABLE IF NOT EXISTS`(신규 표)·`ALTER TABLE … ADD COLUMN`(기본값 있는 컬럼)·`CREATE INDEX IF NOT EXISTS` 셋뿐이고, 컬럼 삭제·타입 변경·CHECK 변경은 새 표 생성 → 복사 → 이름 교체로만 한다. 다운그레이드는 없다 — 적용 직전 `risk_review.db.pre-migrate-<ts>` 사본을 남기고, 되돌릴 일은 그 사본으로 (4) 절차를 밟는다. 앱 코드가 DB 보다 낮으면(`user_version > MIGRATIONS[-1][0]`) 기동 실패다. `GET /api/health` 응답은 `{"ok": true, "app_version", "schema_version"}` 이다(§8 REST 정의가 이 형식을 따른다).

**(7) 박스 간 divergence 금지.** ① 정본 박스는 하나다 — 운영 정본은 cae00, dev 는 검증·시드 박스다(§10 이 달리 정하기 전의 기본). 사람 확정(원장 4표 `rr_sameas · rr_iface_ledger · rr_part_keys · rr_iface_alias`·`rr_targets.verdict_final`·`rr_registry.status`·큐레이션 결정)은 정본 박스에서만 하고 dev 는 재현 데이터로만 쓴다. ② `POST /api/import` 는 헤더의 `schema_version` 이 현재 `user_version` 과 같을 때만 받는다(다르면 409 `schema_mismatch`, 먼저 양쪽 앱을 같은 SIF 로 올린다). ③ Drive `app-data/latest/` 는 백업이지 동기 채널이 아니다 — dev `build-all-to-drive.sh` 가 `latest/` 를 덮어쓰므로 cae00 데이터는 `origin.json.hostname` 이 cae00 인 타임스탬프 폴더로만 찾고, `latest/` 를 정본으로 읽지 않는다. ④ 같은 `owner_sub`·같은 자연키 행이 두 박스에서 서로 다르게 사람 확정된 경우 import 는 그 행을 건너뛰고 응답 `conflicts[]{table, key, local, incoming}` 에 적는다(자동 병합·마지막 쓰기 승리 없음). ⑤ `HEAX_RESTORE_APPDATA=1` 은 hwax_risk 데이터에 쓰지 않는다. ⑥ 두 박스가 동시에 같은 타깃의 패널을 돌리지 않는다 — 배치 러너는 정본 박스에서만 켜고 dev 는 `risk_daily_panel_cap` 을 검증용 소수로 둔다.

## 5.3 ReportArchive KG(관리 REST 부트스트랩 1회·앱 → 게이트웨이 MCP 인스턴스 쓰기·RA 코드 무수정)

### 5.3.1 신규 축 6(POST /api/entity-types → POST /api/entity-types/{type_id}/properties)

RA 속성 타입은 `text · longtext · number · date · year · bool · enum · entity_ref · url` 9종뿐이고 키는 `^[a-z][a-z0-9_]*$`(≤48) 이며 JSON 형은 없다. 그래서 IR·diff 원본은 절대 넣지 않고 카운트·해시·enum·요약만 넣는다. `value` 는 축 안에서 대소문자 무시 유니크(≤255)이고 `code`(≤64) 는 비유니크이므로 `code=<앱 DB id>` 로 멱등을 잡고 `value` 에는 시각·source 를 넣어 충돌을 막는다.

| slug | kind_class | value 규약 | code | 속성(key: data_type, 비고) |
|---|---|---|---|---|
| `expert` | reference | `<agent_key>` | `<agent_key>` | `domain: text` · `adh_agent_type: text`(=value) · `active: bool` |
| `design_snapshot` | record | `<과제코드>@<source>@<YYYYMMDD-hhmm>`(source 는 kinds 가 2개 이상이면 `merged`) | `<snapshot_id>` | `source: enum[mcad,dyna,ecad,merged]` · `captured_at: date` · `ir_version: text` · `ir_hash: text` · `node_count: number` · `edge_count: number` · `portal_snapshot_id: text` · `blocked: bool` · `missing: text`(콤마 목록) · `summary: longtext`(rr_state 요약 ≤2000, 판단어 린터 통과분) |
| `design_diff` | record | `<base코드>→<target코드>@diff@<YYYYMMDD-hhmm>` | `<diff_id>` | `base_snapshot: entity_ref(design_snapshot)` · `target_snapshot: entity_ref(design_snapshot)` · `pair_kind: enum[same_project_revision,cross_project]` · `added: number` · `removed: number` · `changed: number` · `semantic_events: number` · `tol_parity: bool` · `result_parity: bool` · `portal_diff_id: text` · `summary: longtext`(summary_text 앞 2000자) |
| `assessment` | record | `<과제코드>@<agent_key>@<target_key 앞 17자>` | `<opinion_id>` | `coverage_key: text` · `expert_key: text` · `domain: text` · `origin: enum[primary,counter]` · `stance: enum[agree,conditional,oppose,abstain]` · `panel_verdict: enum[go,conditional,no-go,undetermined]` · `panel_id: text` · `panel_no: number` · `reviewed_at: date` · `tool_calls_ok: number` · `cited_ir: bool` · `engine: enum[web,mcp]` · `record_id: text`(AIDataHub 의견 레코드 id) |
| `risk_finding` | record | `<과제코드>@<mechanism>.<detail>@<cluster_key>` | `<target_key>#<cluster_key>`(≤50) | `cluster_key: text` · `direction: enum[risk,improvement,neutral]` · `severity: enum[경미,중대,치명]` · `judgement: enum[OK,WARNING,FAIL,undetermined]` · `domain: enum[15 도메인]` · `mechanism: enum[thermal,mechanical,interface,electrical,material,process]` · `mechanism_detail: text` · `change_kind: enum[dimension,placement,topology,material,type,count,discretization,result,load_path,consistency,electrical,none]` · `evidence_grade: enum[measured,literature,tool_predicted,heuristic]`(label 측정·문헌·규격·도구예측·경험칙) · `precedent: enum[in_range,out_of_range,none]` · `status: enum[open,verified,dismissed,mitigated,superseded]` · `support: number` · `contested: number` · `subject_key: text` · `statement: longtext`(대표 finding claim 원문 ≤600) · `portal_registry_key: text` · `opinion_record_id: text` |
| `design_trait` | reference | `char:<axis>:<value>`(예 `char:structure:adhesive_dependent`) | value 와 동일 | `axis: text` · `token: text` · `vocab_version: text` · `status: enum[vocab,proposed]`(`x:` 승격 후보는 proposed) |

기본 단위는 등록부 클러스터다. finding 원자는 `risk_finding` 으로 만들지 않고 `statement` 에 대표 claim 만 담는다(원자는 앱 DB `rr_findings` 와 AIDataHub 의견 레코드 §3 절에 있다). 축당 기대 인스턴스 수는 타깃 하나에 `assessment ≤350 · risk_finding ≤60` 이고 `expert` 는 로스터 규모(≈350)에서 멈춘다.

### 5.3.2 신규 관계 12(POST /api/relation-types → POST /api/relation-types/{slug}/properties, 전부 `directed:true, transitive:false`)

| slug | src 축 | dst 축 | acyclic | 관계 속성 | 엣지 근거 |
|---|---|---|---|---|---|
| `snapshot_of` | design_snapshot | project | false | — | — |
| `derived_from` | design_snapshot | design_snapshot | true | — | — |
| `diff_of` | design_diff | design_snapshot | false | `role: enum[base,target]`(한 diff 가 2 엣지, UNIQUE(src,dst,relation) 에 걸리지 않음) | — |
| `assesses` | assessment | project · design_snapshot · design_diff | false | — | `evidence_report_id`=패널 RA 보고서 |
| `assessed_by` | assessment | expert | false | — | — |
| `raised_by` | risk_finding | assessment | false | — | `evidence_report_id`=통합 보고서(없으면 패널 보고서) |
| `concerns` | risk_finding | part · model · failure_mode · defect | false | — | `evidence_note`=`reg:<target_key>#<cluster_key>` |
| `mitigated_by` | risk_finding | design_diff | false | — | `evidence_note`=`[c:<cid>]` |
| `verified_by` | risk_finding | incident · test_run | false | `label_id: text` · `match_score: number` · `source: enum[incident,test_run,voc,sim,expert_review,manual]` | `evidence_note`=라벨 evidence_ref |
| `refuted_by` | risk_finding | incident · test_run | false | 위와 동일 | 위와 동일 |
| `exhibits` | project · design_snapshot | design_trait | false | `support: number` · `origin: enum[auto,seat,chair]` | `evidence_note`=`narr:<character_id>` |
| `revision_of` | project | project | true | — | — |

기존 `supersedes / variant_of` 는 `model` 축 전용이므로 과제 계보에 재사용하지 않고 `revision_of` 를 신설한다(gap_21 #9). 보고서↔객체 연결은 기존 `documents`(report_entities 파생)를 `entity_ids` 로 쓰고 새 관계를 만들지 않는다. `part` 축의 별칭은 `add_object_alias` 로만 추가하고 축 정의는 손대지 않는다.

### 5.3.3 페이로드 형태

축 생성(`EntityTypeCreate`).

```json
POST /api/entity-types
{"slug":"design_snapshot","label":"설계 스냅샷","icon":"snapshot","multi":false,"sort_order":110,
 "description":"HWAX 리스크 심사 — 소스 앱을 한 시점에 동결한 설계 IR 헤더(원본은 hwax_risk 앱 DB rr_snapshots)","kind_class":"record"}
```

속성 정의(`PropertyDefCreate`, 축마다 반복).

```json
POST /api/entity-types/{type_id}/properties
{"key":"source","label":"소스","data_type":"enum","required":true,"multi":false,
 "enum_options":[{"value":"mcad","label":"MCAD(StepForge)"},{"value":"dyna","label":"Dyna(DynaForge)"},
                 {"value":"ecad","label":"ECAD(ODB hub)"},{"value":"merged","label":"병합"}],
 "sort_order":1,"help":"kinds 가 2개 이상이면 merged"}
{"key":"base_snapshot","label":"기준 스냅샷","data_type":"entity_ref","ref_type_slug":"design_snapshot","required":true,"multi":false,"sort_order":1}
{"key":"node_count","label":"노드 수","data_type":"number","required":false,"multi":false,"sort_order":5}
```

관계 종류(`RelationTypeCreate`)와 관계 속성.

```json
POST /api/relation-types
{"slug":"diff_of","label":"비교 대상","inverse_label":"비교됨","directed":true,"transitive":false,"acyclic":false,
 "src_axis_slugs":["design_diff"],"dst_axis_slugs":["design_snapshot"],
 "description":"design_diff 가 base/target 스냅샷을 가리킨다. 관계 속성 role 로 구분"}
POST /api/relation-types/diff_of/properties
{"key":"role","label":"역할","data_type":"enum","required":true,"multi":false,
 "enum_options":[{"value":"base","label":"기준"},{"value":"target","label":"대상"}],"sort_order":1}
POST /api/relation-types
{"slug":"revision_of","label":"후속 과제","inverse_label":"선행 과제","directed":true,"transitive":false,"acyclic":true,
 "src_axis_slugs":["project"],"dst_axis_slugs":["project"],"description":"과제 계보(모델 축 supersedes/variant_of 와 별개)"}
```

### 5.3.4 `backend/scripts/bootstrap_ra_ontology.py`(멱등, dry-run 기본)

실행 형태. 앱 리포의 스크립트를 **실행자 셸**에서 `RA_ADMIN_PAT=rat_… python backend/scripts/bootstrap_ra_ontology.py --base <RA REST 오리진> [--apply]` 로 1회 돌린다. 축·관계 정의 API(`/api/entity-types` · `/api/relation-types`)는 게이트웨이 `reportarchive` 도구 24종에 없으므로 이 스크립트만 RA REST 를 `Authorization: Bearer <RA_ADMIN_PAT>` 로 직접 부르고, 앱 런타임(`ra_client.py`)은 이 토큰을 갖지도 부르지도 않는다(§0.5.3). dev·cae00 각각의 RA 에 한 번씩 실행한다.

절차. (1) `GET /api/entity-types` · `GET /api/relation-types` 로 현재 목록을 읽는다. (2) 계획표(스크립트 안 상수 `AXES · PROPS · RELATIONS · REL_PROPS`, 위 §5.3.1~§5.3.2 와 문자 동일)와 대조해 **없는 것만** 생성 후보로 만든다. (3) 있는 것의 정의가 계획표와 다르면(enum 값·축 제약·acyclic) `drift` 로 보고만 하고 절대 `update_type · update_relation_type` 을 호출하지 않는다(RA hands-off). (4) 기본은 dry-run 으로 생성 후보·drift 표를 출력하고 `--apply` 일 때만 순서대로 생성한다 — 축 → 축 속성 → 관계 종류 → 관계 속성(관계 종류가 축 slug 를 참조하므로 순서 고정). (5) 결과를 `{created:{types:n, props:n, relations:n, rel_props:n}, skipped:{…}, drift:[…]}` JSON 으로 출력하고 drift 가 있으면 종료 코드 2 다. (6) 기존 15축·17관계는 읽기만 하고 한 필드도 쓰지 않는다.

통과 기준(§9 P0 (2) 와 동일). `list_object_types` 에 6축·12관계가 보이고, 스크립트 2회 실행 시 두 번째는 created 전부 0 이며, 기존 15축·17관계의 slug·label·제약이 실행 전후 바이트 동일하다(스크립트가 전후 덤프를 비교해 보고).

### 5.3.5 인스턴스 쓰기 규약(`ra_client.py` — 앱 → 게이트웨이 MCP `reportarchive` 쓰기 4종, 대안 RA REST)

호출 경로(기본). 앱 `backend/app/ra_client.py` 가 `HWAXRISK_GATEWAY_MCP`(기본 `http://127.0.0.1:9110/mcp`, 박스 밖이면 `<포털베이스>/mcp-gw/mcp`) 에 streamable_http 클라이언트로 붙어 `Authorization: Bearer <HWAXRISK_PORTAL_PAT>`(`$HEAX_DATA_DIR/secrets.env`, 서비스 계정 포털 PAT, aud `mcp-gateway`) 로 도구 `create_object · update_object · add_object_alias · link_objects`(쓰기 4종)·`get_object · search_objects · get_subgraph · list_object_types`(읽기)·`get_report · update_report_draft`(보고서)를 부른다. 게이트웨이가 RA 백엔드 자격(서비스 `rat_` + `X-Workspace-Slug`)을 대신 실으므로 앱은 RA 토큰을 보유하지 않고 RA 소유자는 서비스 계정이다 — 사용자 귀속은 RA 가 아니라 `assessment.expert_key`·앱 DB `owner_sub` 가 맡는다. 러너 자격 (b)(사용자 등록 PAT) 가 있는 패널이라도 KG 쓰기는 항상 서비스 PAT 로 한다. 호출 타임아웃은 게이트웨이 `GATEWAY_CALL_TIMEOUT` 120 s, 앱 측은 1회 즉시 재시도 후 §5.5.3 큐로 넘긴다. 패널 RA 보고서(`create_report_draft`)는 엔진이 심의 중 서비스 `rat_` 로 만들고 앱은 `update_report_draft` 만 한다.

호출 경로(대안, 기본 미채택). 게이트웨이가 없는 박스에서만 `ra_client` 가 같은 인터페이스 뒤에서 RA REST 를 직접 부른다(객체·관계·별칭 API 경로는 RA OpenAPI 에서 P0 에 실측, 인증 `Authorization: Bearer rat_…`). 이 경로는 `rat_` 을 앱 `secrets.env` 에 두어야 하므로 §0.5.3 '앱은 `rat_` 미보유' 와 상충한다 — 채택 여부와 시크릿 이름은 §10 결정이고, 채택 전에는 코드에 REST 분기를 두지 않는다.

| 호출 | 형태 | 멱등 규칙 |
|---|---|---|
| `create_object` | `{type_slug, value, code, properties}` → `{created, object{id, value, type_slug, code, properties, status}}` | `resolve_existing(code → value 대소문자 무시 → 별칭)` 이 기존을 돌려주면 `created:false`. 같은 code 로 재호출은 안전하다 |
| `update_object` | `{id, properties}` — **통째 교체** | 반드시 `get_object(id)` 후 병합해 보낸다(`ra_client.upsert_props(id, patch)` 헬퍼가 병합·전송을 한 곳에서 한다) |
| `link_objects` | `{src_id, dst_id, relation, properties?, evidence_report_id?}` → `{ok}` 또는 `{error}` | `UNIQUE(src,dst,relation)` 이라 재호출은 속성·근거만 갱신된다. 축 제약·acyclic 위반은 error 로 오며 재시도하지 않고 `external_sync.last_error` 에 남긴다 |
| `add_object_alias` | `{entity_id, alias}` | 같은 축 안 정규화 유니크. 이미 그 엔티티의 별칭이면 멱등, 다른 엔티티와 충돌하면 error → 큐레이션 큐(`label_match` 와 같은 처리, payload 에 충돌 상대 id) |

쓰기 순서(타깃 하나의 패널 종료 시). ① `project`(code=rr_projects.id, value=과제 표시명, 없으면 생성) ② `design_snapshot`(snapshot_of, derived_from) ③ `design_diff`(diff_of ×2) ④ `expert`(로스터 좌석, 없으면 생성) ⑤ `assessment`(assesses, assessed_by) ⑥ `risk_finding`(raised_by, concerns, mitigated_by) ⑦ `design_trait` + `exhibits` — `rr_character.tags_json` 의 통제 어휘(`char:`) 태그마다 `design_trait` 1객체·`exhibits` 1엣지(`support=support_panels`, `origin`, `evidence_note='narr:<character_id>'`)로 잇고, `x:` 자유 태그는 승격(§7.7 x_tag_promote) 전에는 잇지 않으며, 무태그 문장은 엣지 0 이다 ⑧ 패널 RA 보고서 `update_report_draft` 는 `get_report` 후 tags·entity_ids 를 **합쳐서** 보낸다(전체 교체 API). ⑥의 `concerns → part` 는 `rr_part_keys.ra_part_entity_id` 가 있을 때만 잇고, 없으면 잇지 않는다(part 축 값을 자동 생성하지 않는다). 실패는 어느 단계든 비치명이며 §5.5.3 재시도 큐로 간다.

### 5.3.6 KG 활용 쿼리

읽기 호출도 §5.3.5 와 같은 경로(앱 → 게이트웨이 MCP `reportarchive`, 서비스 PAT)다. 다른 심의 좌석의 자유조회(`_RISK_KEEP_TOOLS` 의 `search_objects · get_object · get_subgraph`)는 엔진이 부르는 것이고 이 절의 호출자는 앱 `ra_client` 다.

- **과제 주변 판정 이력 한 콜.** `get_subgraph(project_entity_id, relations=['revision_of','snapshot_of','diff_of','assesses','raised_by','concerns','exhibits','verified_by','refuted_by'], depth=3)`. 서브그래프는 노드 `{id, value, type_slug, degree}` 와 엣지 `{src, dst, relation}` 만 주고 속성·근거를 싣지 않으므로 `ra_client.subgraph_enriched()` 가 노드별 `get_object` 를 병렬 호출해 속성을 붙인다(상한 200 노드, 초과 시 type_slug 우선순위 risk_finding > assessment > design_diff 로 자른다).
- **같은 성격의 과제.** `search_objects(type='project', relations=[{relation:'exhibits', dst_id:<design_trait id>}])`. 정성 태그의 그래프 검색이 여기서 성립한다.
- **부품 기준 리스크.** `search_objects(type='risk_finding', relations=[{relation:'concerns', dst_id:<part id>}], props=[{key:'severity', op:'in', value:['중대','치명']}])`.
- **계보 사고.** `get_subgraph(project, relations=['revision_of','has_defect','caused_by','verified_by'], depth=2)` → incident 노드를 `get_object` 로 보강해 `occurred_on · impact · action_status` 를 E5 옆 원문으로 싣는다.
- **라벨 동기.** `search_objects(type='incident', props=[{key:'occurred_on', op:'gte', value:<마지막 동기일>}])`(§7.6).

## 5.4 AIDataHub(앱 발신 REST import UPSERT·doc_type 5종·의사 에이전트 1)

### 5.4.1 doc_type(`create_doc_type` 각 1회, 중복은 error 로 무해)

| code | mode | expected_sections | 레코드 단위 |
|---|---|---|---|
| `risk_review_opinion` | llm_context | `['대상과 변화 요약','관점(도메인) 평가','리스크 목록','개선되는 점','권고·추가 확인','과제 성격(정성)','반박·소수의견']` | 좌석 1석 × 타깃 1개 × cycle |
| `risk_review_panel` | llm_context | `['심사 대상과 비교 축','변경 원장','도메인별 리스크 판정','개선되는 점','과제 성격 서술','교차 도메인 상호작용','확인 필요·미지영역','합의·소수의견·신뢰도','risk_spec']` | 패널 1건 |
| `project_character` | llm_context | `['과제 개요·소스','관찰 태그와 유사 과제','설계 의도','제약','이례성','계보','취약 계면','강점','맞교환','미지','판정 이력','다음 확인']` | 과제 1건(UPSERT) |
| `risk_pattern_card` | llm_context(P6) | `['패턴 정의','발현 조건','선례 과제','검증 통계','권고 확인']` | known 패턴 1건 |
| `design_snapshot_digest` | data_extract(선택) | — (DATA 형 표, 임베딩 생략) | 스냅샷 1건 |

```json
create_doc_type({"doc_type":{"code":"risk_review_opinion","name":"리스크 심사 좌석 의견",
  "description":"HWAX 리스크 심사에서 전문가 좌석 1석이 타깃 1개에 대해 남긴 서술(코드 추출, LLM 재요약 없음)",
  "expected_sections":["대상과 변화 요약","관점(도메인) 평가","리스크 목록","개선되는 점","권고·추가 확인","과제 성격(정성)","반박·소수의견"],
  "mode":"llm_context"}}, api_key)
```

부트스트랩 호출자는 앱 리포 `backend/scripts/bootstrap_adh.py`(실행자 셸, env `HWAXRISK_AIDH_API_KEY`)이고 위 형식대로 게이트웨이 도구 `create_doc_type{doc_type, api_key}` · `create_agent{agent, api_key}` 를 `Authorization: Bearer <HWAXRISK_PORTAL_PAT>` 로 부른다(`api_key` 인자는 AIDH `X-API-Key` 평문). dev·cae00 각각의 AIDataHub 에 1회씩이다.

### 5.4.2 레코드 공통 규약과 REST 호출 형태

| 필드 | 값 |
|---|---|
| `data_type` | `DOC`(digest 만 `DATA`) — id 는 `{DATA_TYPE}-{TEAM}-{GROUP}-{YEAR}-{SEQ}` 자동 부여(auto_seq) |
| `team · group` | `rr_projects.adh_team · adh_group`(과제 등록 화면에서 사용자가 1회 지정, 자동 채움 금지) |
| `year` | 생성 연도 |
| `title` | `[리스크심사] <과제코드> / <agent_key> / <target_key>`(opinion) · `[리스크심사] <과제코드> P<n> 결정문`(panel) · `[과제성격] <과제코드>`(character) · `[리스크패턴] <mechanism>.<detail>/<change_kind>`(card) |
| `summary` | 1~3줄, 코드 생성(opinion 은 `quality` 한 줄 + 최대 sev, character 는 `one_liner`) |
| `tags` | 공통 `hwax-risk-review · hwax:project:<rr_projects.id> · hwax:target:<target_key> · hwax:snapshot:<id> · hwax:panel:<no> · hwax:expert:<agent_key> · hwax:domain:<d> · sev:<max> · mechanism:<m>(finding 마다) · verdict:<v> · char:<axis>:<value> · x:<free>` |
| `agents` | **항상 `['risk-review-memory']` 하나만.** 실 전문가 agent_key 는 넣지 않는다(§5.4.7) |
| `project` | 과제 표시명(`rr_projects.name`) |
| `related_record_ids` | 같은 타깃의 다른 좌석 의견 id(opinion), 그 패널의 좌석 의견 id 전부(panel) |
| `content.meta` | `{schema_version:'1.0', portal:{project_id, target_key, snapshot_id, diff_id, panel_id, opinion_id, ir_hash}, ra:{project_entity_id, assessment_id, report_id}, engine, tool_mode, taxonomy_version}` |
| `content.sections` | `[{id, title, level, text, children?}]` — id 는 VARCHAR(20) 안의 번호 표기(`'3'`, `'3.1'`), 각 섹션 id·title 필수. `AIDH_CHUNK_WINDOW=on` 이면 2000자 초과 섹션은 허브가 1000/256 으로 나누므로 섹션 하나를 2000자 이하로 유지한다 |
| `_external_id` | `opinion:<target_key>:<agent_key>:<cycle>` · `panel:<panel_id>` · `character:<project_id>` · `pattern:<pattern_id>` · `digest:<snapshot_id>` |

```
POST {HWAXRISK_AIDH_BASE}/api/records/import?external_source=hwax-risk
X-API-Key: <HWAXRISK_AIDH_API_KEY>
Content-Type: application/json
{"records":[{ "data_type":"DOC","team":"…","group":"…","year":2026,"title":"…","doc_type":"risk_review_opinion",
             "summary":"…","tags":[…],"agents":["risk-review-memory"],"project":"…","related_record_ids":[…],
             "content":{"meta":{…},"sections":[…]},"_external_id":"opinion:diff:7f3e…:mech-housing-structure:1"}],
 "dry_run":false}
```

호출 주체는 hwax_risk 앱 프로세스(러너 후처리 스레드, `backend/app/adh_client.py`)이고 자격은 `$HEAX_DATA_DIR/secrets.env` 의 `HWAXRISK_AIDH_API_KEY` 다(`X-API-Key` 는 AIDH `require_api_key` 가 읽는 헤더이며 `AUTH_REQUIRED` 값과 무관하게 항상 보낸다). 베이스는 `HWAXRISK_AIDH_BASE`(기본 `http://127.0.0.1:8001`, 게이트웨이 `rest.ai-data-hub.base` 와 같은 오리진)이고 게이트웨이 `rest_proxy` 는 거치지 않는다(포털 PAT audience 에 `ai-data-hub` 를 넣을 필요 없음). `external_source` 값은 `hwax-risk` 로 고정한다(A 계획의 `hwax-portal` 폐기 — 두 값이 섞이면 `external_id_map` 이 같은 `_external_id` 를 두 레코드로 만든다). MCP `import_record` 는 `_external_id` 를 받지 못해 재실행 시 중복을 만들므로 앱 코드는 REST 만 쓴다. 응답의 `record_id` 는 `rr_seat_opinions.adh_record_id · rr_panels(evidence_refs_json 의 panel 항목) · rr_projects.adh_character_record_id · rr_id_map` 에 적는다. 저장 직후 허브가 signature 임베딩을 계산하므로 별도 색인 호출은 없다.

### 5.4.3 `risk_review_opinion` 7섹션 규약(코드 조립, LLM 재요약 없음)

| id | 제목 | 내용 생성 규칙 | 상한 |
|---|---|---|---|
| `1` | 대상과 변화 요약 | E0 원문 + summary_text(E1) 앞 600자. 전부 원천 인용 | 1000자 |
| `2` | 관점(도메인) 평가 | `seat_opinion.turns[round=1].say_excerpt` 원문(좌석 1R 독립 발언) | 2000자 |
| `3` | 리스크 목록 | `raised_finding_ids` 중 direction=risk 를 `3.1, 3.2 …` 하위 섹션으로. 각 text = `[<severity>/<judgement>] <mechanism>.<detail> — <claim> / 근거 <evidence_grade>: <warrant> / 닫는 확인: <resolving_check> / 인용: <cites ref 목록> / 선례: <precedent> / 반대석: <contest_note 또는 없음>` | 하위 섹션당 1200자, 최대 12개 |
| `4` | 개선되는 점 | direction=improvement finding 을 `4.1 …` 로 같은 형식 | 동일 |
| `5` | 권고·추가 확인 | `turns[round=3]` 최종 입장(final_stance·non_negotiable 원문) + 이 좌석 owner_domain 의 open_items 원문 | 1500자 |
| `6` | 과제 성격(정성) | 이 좌석이 `by` 인 character statements(§4) 원문, facet 라벨 접두 | 1200자 |
| `7` | 반박·소수의견 | 2R 에서 이 좌석을 인용한 타 좌석·지정 반대석 발언 원문 발췌(인용 계약의 quote 부분) | 800자 |

`excerpt_for_rag`(≤1500자)는 섹션 2 앞 700자 + 섹션 3·4 각 항목 첫 줄(claim)로 코드가 만들고 `rr_seat_opinions` 에도 같은 문자열을 둔다 — E7 은 이 문자열의 앞부분(좌석 줄 220자에서 참조 접두를 뺀 ≈125자, §5.6.3)을 쓴다.

### 5.4.4 `risk_review_panel` 섹션

결정문 산문 8항목을 §6.6 `_CHAIR_ITEMS['risk-review']` 의 항목 순서 그대로 `1~8` 섹션에 나누고(의장 산문의 `(n)` 번호 접두로 분할, 실패 시 전체를 `1` 에 두고 `meta.split=false`), `9`=`risk_spec` 는 파싱된 JSON 을 `json.dumps(indent=0)` 원문으로 넣는다(2000자 초과 시 `9.1 findings · 9.2 gains · 9.3 character · 9.4 open_items` 로 나눈다). 섹션 5(과제 성격 서술)가 `hybrid_search` 의 주요 적중 단위다.

### 5.4.5 `project_character` 섹션(과제 1건 UPSERT, `character.py`)

| id | 제목 | 내용 |
|---|---|---|
| `1` | 과제 개요·소스 | `rr_projects` 코드·이름·stage·predecessor, 최신 스냅샷의 sources·counts·gates·missing 원문 |
| `2` | 관찰 태그와 유사 과제 | `character_seed` 태그 + §5.7 유사 과제 상위 3(코드·경로·순위) |
| `3`~`10` | 설계 의도 · 제약 · 이례성 · 계보 · 취약 계면 · 강점 · 맞교환 · 미지 | facet 별 `rr_character` 행을 status 순(confirmed → panel(support_panels 내림차순) → seed)으로, 각 줄 `[<status>·지지 <support_panels>패널/<support_targets>타깃·<by>] <statement> ← <cites ref 목록>`. 각 facet 상한 1500자, 초과분은 잘라내고 `…(n건 생략)` |
| `11` | 판정 이력 | 타깃별 level·verdict_final·통합 보고서 `rpt:` 목록 |
| `12` | 다음 확인 | 열린 등록부 클러스터의 resolving_checks 집합(중복 제거, kind 별) |

`_external_id='character:<project_id>'` 로 스냅샷·패널이 늘 때마다 같은 레코드를 덮어쓴다. 레코드 id 는 불변이라 `narr:` 인용의 대상이 바뀌지 않는다.

### 5.4.6 `design_snapshot_digest`(선택)·`risk_pattern_card`(P6)

- `design_snapshot_digest` — `data_type:'DATA'`, `content:{headers:['kind','name_a','name_b','min_gap_mm','status'], rows:[상위 30 계면], caption:'<snapshot_id>'}`, `_external_id='digest:<snapshot_id>'`. `find_similar_data` 는 표 헤더 시그니처 기반이라 이 표에만 쓰고 서술 유사에는 쓰지 않는다(§7.3).
- `risk_pattern_card` — §7.5 known 승격 시 1건. 섹션 `1 패턴 정의(cluster_key_norm·mechanism·change_kind·subject_class)` · `2 발현 조건(feature_ranges 원문, DSL 초안)` · `3 선례 과제(project 코드·타깃·finding claim 원문 ≤5)` · `4 검증 통계(n_findings·n_projects·n_confirmed·n_refuted·precision, n 병기)` · `5 권고 확인(top_resolving_checks)`. `_external_id='pattern:<pattern_id>'`.

### 5.4.7 의사 에이전트 `risk-review-memory` 와 회수 경로 — 오염 방지 선택과 그 결과

선택. 의견·패널·성격 레코드의 `agents` 에는 실 전문가 키를 넣지 않고 의사 에이전트 `risk-review-memory` 하나만 넣는다. 이유는 실측 전문가 781명의 `required_doc_type · required_tags · retrieval_config` 가 전부 비어 있어 `bind_records_to_agent` 는 `common_tags` 겹침만으로 바인딩하고, 레코드 `agents` 에 실 키를 직접 넣으면 그 전문가의 **모든 일반 심의** `agent_search`(엔진 :2100-2144, q=question 고정, top_k 10) 결과에 리스크 의견이 섞여 들기 때문이다. `bind_records_to_agent · patch_agent` 는 호출하지 않는다.

```json
create_agent({"agent":{"agent_type":"risk-review-memory","name":"리스크 심사 기억",
  "domain":"xd","description":"HWAX 리스크 심사 좌석 의견·패널 결정문·과제 성격 레코드의 회수 범위(의사 에이전트, 좌석으로 착석하지 않음)",
  "common_tags":["hwax-risk-review"]}}, api_key)
```
정확한 필드 집합은 `describe_agent_schema` 로 P0 에서 실측해 채우되 위 다섯 키는 필수다. 이 에이전트는 로스터에 절대 들어가지 않는다(`planner.py` 가 `risk-review-memory` 를 제외 목록에 고정).

결과(명시). 이 선택으로 **엔진의 좌석별 자동 `agent_search`(자기 agent_type) 로는 그 전문가의 이전 리스크 발언이 절대 회수되지 않는다.** 좌석 개인 기억은 오직 앱(`narrative.prior_evidence`)이 조립하는 E7 고정 슬롯(§5.6.3)으로만 좌석에 도달한다. 대안(레코드 `agents` 에 실 키를 넣되 `required_tags` 와 `retrieval_config` 는 건드리지 않음)은 §10 열린 질문 (8a) 로 넘긴다.

회수 경로 4개.

| 경로 | 호출 | 누가·언제 | 결과가 실리는 곳 |
|---|---|---|---|
| (a) 좌석 자동 지식 주입 | 엔진 `agent_search(<좌석 agent_type>, q=question, mode=hybrid)` 3500자 | 엔진, 라운드마다(수렴 제외) | 좌석 지식카드 블록 — 리스크 의견은 오지 않고 지식카드만 온다(오염 없음) |
| (b) 좌석 개인 기억 | 1차 `rr_seat_opinions WHERE agent_key=? AND target_key<>?` 최신순, 2차 `agent_search('risk-review-memory', q='<과제코드> <summary_text 앞 200자>', mode='hybrid', required_tags=['hwax:expert:<agent_key>'], retrieval_config={top_k:3})` | 앱 `narrative.prior_evidence`(AIDH 호출은 `adh_client`, 자격 `HWAXRISK_AIDH_API_KEY`), 패널 편성 직후 | E7(좌석당 줄 ≤220자) |
| (c) 유사 서술 | `hybrid_search(q=<summary_text 앞 300자>, tags=['hwax-risk-review','mechanism:<m>'])` top 5 + `tag_search(['char:'+t for t in character_seed])` | 앱 `adh_client`, §7.3 3단계 | E5·E6 후보, '유사 과제' 탭 |
| (d) 다른 심의의 등록부 열람 | `hwax-risk` 앱 `risk_get_registry(target_key)` · `risk_claims_for_ref(ref)`(P5) | sim-plan 등 다른 심의 좌석의 자유조회 | 그 심의의 자유조회 블록 |

e5 코사인은 절대값 비교를 하지 않고 상대 순위만 쓴다(무관한 문장도 0.89 가 정상).

## 5.5 ID 연결과 동기 상태

### 5.5.1 외래키 규약(DB 제약 없는 문자열 계약)

| 방향 | 키 | 비고 |
|---|---|---|
| 앱 DB → RA | `entity.code = <앱 DB id>`(project=rr_projects.id · snapshot_id · diff_id · opinion_id · `<target_key>#<cluster_key>` · agent_key · 성격 태그) | `value` 는 §5.3.1 규약, 재호출은 `created:false` |
| RA → 앱 DB | `properties.portal_*_id`(text 중복 보관 — 속성 키 이름은 A 계획 그대로 `portal_` 접두를 유지하고 값은 앱 DB id 다) + `rr_id_map.ra_entity_id` | 서브그래프 결과에서 앱 화면으로 돌아오는 경로 |
| 앱 DB → AIDataHub | `external_id_map(source='hwax-risk', external_id=<§5.4.2 규약>)` | 재실행 UPSERT, 레코드 id 불변 |
| AIDataHub → 앱 DB | `tags hwax:project:<id> · hwax:target:<key> · hwax:snapshot:<id>` + `content.meta.portal.*`(키 이름 유지, 값은 앱 DB id) | `tag_search` 로 역조회 가능 |
| RA → AIDataHub | `assessment.record_id · risk_finding.opinion_record_id · design_snapshot(없음)` | 텍스트 id |
| AIDataHub → RA | `content.meta.ra.{project_entity_id, assessment_id, report_id}` + `tags hwax:project:` 의 앱 DB id 를 `rr_id_map` 으로 변환 | |
| 앱 DB 내부 | `rr_coverage.opinion_id → rr_seat_opinions`, `rr_findings.opinion_id · panel_id`, `rr_registry.merged_json.member_finding_ids`, `rr_claim_refs.claim_uid → rr_findings.claim_uid \| rr_character.id`, `rr_labels.finding_id`, `rr_patterns ← rr_rules.pattern_id` | 삭제 없음이라 댕글링은 `superseded_by` 로만 생긴다 |
| 대화·보고서(앱 밖) | `rr_panels.conv_id → 포털 conv_store(kind='risk-review')`(러너가 포털 `POST /agent/chat` 에 `conversation_id` 를 실었을 때만 포털 릴레이가 저장, owner=호출 PAT sub), `rr_panels.report_id · rr_targets.report_ids_json → RA report`, `finding.cites tool:conv:<conv_id>#<idx> → conv_store activity`(앱은 SSE 를 직접 캡처해 `rr_snapshot_calls`·`rr_seat_opinions.turns` 에 남기므로 conv_store 부재여도 인용 해석은 된다) | |

### 5.5.2 `rr_id_map`

모든 외부 반영 성공 시 `INSERT OR REPLACE`. 한 앱 DB 객체가 RA 와 AIDataHub 에 각각 있는지 한 줄로 보이고, RA 서브그래프 노드 id → 앱 DB 객체 역변환(`ix_rr_id_map_ra`)과 AIDataHub 레코드 id → 앱 DB 객체 역변환(`ix_rr_id_map_adh`)에 쓴다. 컬럼명 `portal_kind · portal_id` 는 A 계획 DDL 그대로 두고(§5.2.2 H 불변) 뜻만 '앱 DB 종류·id' 로 읽는다. 각 원본 표의 `ra_entity_id · adh_record_id` 컬럼은 조회 편의용 중복이고 정합 검사는 야간 잡이 `rr_id_map` 기준으로 한다.

### 5.5.3 `external_sync` 상태기계(타깃 단위, 완결 레벨과 분리)

```json
rr_targets.external_sync_json =
{"ra":  {"state":"pending|done|unavailable","attempts":0,"next_at":0,"last_error":null,"done_at":null,
         "pending_ops":[{"op":"create_object","type_slug":"assessment","code":"<opinion_id>","payload_ref":"opinion:<id>"}, …]},
 "adh": {"state":"pending|done|unavailable","attempts":0,"next_at":0,"last_error":null,"done_at":null,
         "pending_ops":[{"op":"import","external_id":"opinion:…"}, …]}}
```

| 전이 | 조건 |
|---|---|
| `pending → done` | 그 타깃의 `pending_ops` 가 비었고 마지막 패널 이후 새 op 가 없음 |
| `pending → pending`(재시도) | 실패 시 `attempts+1`, `next_at = now + min(15분 × 2^attempts, 6시간)`. 러너 후처리 스레드가 `next_at ≤ now` 인 타깃의 op 를 순서대로 다시 보낸다 |
| `pending → unavailable` | `ra` 는 `HWAXRISK_PORTAL_PAT` 미설정·게이트웨이 `/health` 실패·401/403, `adh` 는 `HWAXRISK_AIDH_API_KEY` 미설정·401/403, 또는 attempts ≥ 8, 또는 `origin.json.hostname` 불일치(§5.2.5 (5)). 운영자가 `$HEAX_DATA_DIR/secrets.env` 를 채우고(앱 재기동으로 로드) 타깃 화면 '재동기'(`POST /api/targets/{key}/resync`, 소유자만) 를 누르면 `pending(attempts=0, next_at=0)` 으로 되돌아가고 러너 후처리 스레드가 다음 주기에 집는다 |
| 새 패널 종료 | `done` 이었어도 새 op 가 쌓이면 `pending` |

C1~C3 판정은 이 값을 읽지 않는다. 타깃 화면과 통합 보고서 헤더에 `RA 반영: done|pending(n)|unavailable · AIDataHub 반영: …` 로 표기만 한다(gap_21 #7). 재시도는 앱 프로세스 안의 러너 후처리 스레드가 하고 포털·게이트웨이는 큐를 모른다. `unavailable` 상태에서도 다음 과제 브리프(E5~E8)는 앱 DB 원장만으로 조립되므로 재사용 루프는 끊기지 않는다 — 끊기는 것은 (c) 유사 서술 경로와 KG 그래프 검색뿐이며 그 사실을 E0 에 `외부 검색 미가용` 한 줄로 적는다.

### 5.5.4 역참조 예

- RA 서브그래프에서 `risk_finding` 노드를 클릭 → `code` 를 `'#'` 로 나눠 `rr_registry(target_key, cluster_key)` → 앱 화면 `/apps/hwax_risk/targets/<key>#<cluster>`(앱 SPA 라우트 `/targets/:key`).
- AIDataHub `hybrid_search` 적중 레코드 → `tags hwax:target:` → `rr_targets` → 그 레코드가 어느 좌석·어느 패널의 것인지 `rr_seat_opinions.adh_record_id`.
- 좌석 발언의 `narr:<opinion_id>#<finding_id>` → `rr_seat_opinions` → `rr_findings` → `rr_labels`(선례가 실제로 맞았나) 가 한 조인이다.

## 5.6 다음 과제에서 꺼내 쓰는 경로 — `prior_evidence` E0~E9 예산표

`narrative.prior_evidence(target, panel)` 가 다음 패널의 `delib_opts.evidence`(≤12 항목, 엔진 클램프 source ≤120·tool ≤80·args ≤400·result ≤2000, 예산 11000 초과 항목은 엔진이 통째 드롭) 를 조립한다. 엔진 상한에 기대지 않고 앱(`narrative.py`)이 항목별 상한을 먼저 강제해 **드롭 0** 을 보장한다(P5 통과 기준 (1)). 같은 조립 결과를 웹 러너는 `delib_opts.evidence` 로, MCP L2 는 `risk_get_brief(target_key)` 응답으로 받는다. 측정 단위는 `result` 문자열이 아니라 엔진이 실제로 누적하는 **라인** `· [{source} · {tool}({args})] {result}` 의 `len` 이다(deliberation.py :2162-2168 `_line = f"· [{_src}{_meta}] {_res}"`, hwax-deliberate.js :128-133 동일 식). 그래서 항목마다 source·tool·args·구두점 오버헤드(§5.6.1 규칙)가 붙고 예산표는 그것을 포함해 합 10600 으로 잡는다. P3 (1)·P5 (1) 에서 엔진 로그의 evidence 채택 수가 보낸 항목 수와 같은지(드롭 0) 확인한다.

### 5.6.1 항목·원천·상한

| # | source | 내용 | 원천 | 상한(자) | 결측 시 |
|---|---|---|---|---|---|
| E0 | `rr_scope` | 스코프 kind·target_key·과제코드(base/target)·snapshot_id·ir_hash·게이트 G1~G7 pass/fail·missing 플래그·**소스 앱 id**(`stepforge project_id=… · dynaforge session_id=… file_id=… report_ids=[…] · ecad absent`)·tol_params·adapter_version·외부 검색 가용 여부. 항상 첫 항목 | rr_targets·rr_snapshots·rr_states.gates | 500 | 없음(필수) |
| E0c | `seat_contract` | 이번 패널에 앉은 5석 도메인의 좌석 계약 행(`seat-contract.v1.json`)만 — 도메인당 ≤200자, 통과 경로 열 포함 | seat-contract.v1.json | 1000 | 없음(필수) |
| E1 | `rr_diff`/`rr_state` | pair 면 `summary_text`(§3.4.2 순서 그대로, 실효 상한까지 줄 경계 절단 — 뒤 섹션 `[씨앗]`·`[재료]` 부터 `…(n줄 생략)`, 전문은 `GET /api/diffs/{id}?part=summary` 이고 `[의미]`·`[치수]`·`[결과]` 는 E2·E3·E4 가 표로 따로 싣는다), snap 이면 rr_state 요약(counts·worst_interference·thin_clearances·orphans·rollup_top, 줄마다 `[sig:]`·`[p:]`·`[e:]`) | rr_diffs.summary_text·rr_states | 1900 | 없음(필수) |
| E2 | `rr_diff.events` | 의미·구조 이벤트 표 — `[c:<cid>] <code> <subject 실명> <정규 표기 before→after> conf=<x> <unconfirmed|excluded_reason>` magnitude 내림차순 | rr_diff_events(semantic → structural 순) | 1100 | snap: `[pair 전용 — 해당 없음]` |
| E3 | `rr_diff.dims` | 명명 치수 delta 표 `[d:<name>] <base>→<target> <unit> (<rel>%) method=<m>`; snap 이면 현재 값 표 | rr_diffs.diff_json.dims_delta / rr_ir.dims_named | 700 | `[명명 치수 없음 — rr_dim_defs 0건]` |
| E4 | `rr_diff.results` | 결과 delta 표(`result_parity` 일 때만 수치, 아니면 `[result_parity=false — 정성만]`); snap 이면 part_risk 상위 5 | rr_diffs.diff_json.result_delta / rr_ir.results | 600 | `[dyna_result 부재]` |
| E5 | `rr_registry.prior` | 계보(revision_of 3홉) 타깃과 유사 과제(§5.7)의 등록부 상위 클러스터 — `reg:<target_key>#<cluster_key> | <mechanism>.<detail> | <subject 실명> | <severity>/<judgement> | status <open|verified> | support n · contested m | claim 원문 ≤160자 | [경로: 계보|벡터|텍스트|subject|subject·asm|subject·별칭후보]` sev3·support 내림차순 | rr_registry(status open|verified) | 1000 | `[선행 등록부 없음 — 이 과제 계보·유사 과제 0건]` |
| E6 | `rr_character.similar` | 유사 과제 성격 진술 상위 3 — `narr:<character_id> | <과제코드> | <facet> | <tag> | <statement 원문 ≤200자> | by <key> | [<confirmed|panel:n>·경로 k]` | rr_character(status confirmed 또는 panel(support_panels ≥2)) | 800 | `[유사 과제 성격 진술 없음 — 코퍼스 n_projects=…]` |
| E7 | `rr_seat_opinions.self` | **이번 패널 좌석 5명의 이전 발췌(고정 슬롯)** — 좌석당 줄 ≤220자 `narr:<opinion_id>#<finding_id> | <agent_key> | <이전 과제코드>/<target_key 앞 12> | <excerpt_for_rag 앞 (220 − 접두 길이) ≈125자>` | §5.6.3 | 1400(좌석당 줄 220 · 좌석 합 ≤1100 · 프레이밍 ≤80 · 오버헤드 ≈171) | 좌석별 `[<agent_key>: 이전 발언 없음]` |
| E8 | `rr_delta_priors` | 이번 diff 의 (change_kind, mechanism, detail) 조합별 `n_raised · n_targets · n_verified · n_dismissed · precision=v/(v+d) (n=v+d)` 수치만, 조합당 1줄 | rr_delta_priors | 500 | `[선례 없음 — 코퍼스 n_targets=…, 이 조합 첫 사례]`, snap: `[pair 전용 — 해당 없음]` |
| E9 | `rr_state.warnings_rules` | warnings 상위(severity 순, `warn:<code>#<ref>` 원문 ≤350) + `rule_hits` pass=true(`rule:<id> <severity> found=<앞 3> why_it_matters 원문` ≤350) | rr_ir.warnings·rr_states.rule_hits | 700 | `[warnings 0 · rule_hits 0]` |
| M | `user_memo` | 사용자가 타깃 잡 생성 시 넣은 메모(§6, `human_note` 로는 절대 싣지 않음) | rr_jobs.params_json.user_memo | 400 | 항목 생략 |
| 합 | | 12 항목 | | **10600**(라인 기준 — 엔진 예산 11000 대비 여유 400) | |

각 항목은 `{source, tool, args, result}` 형태이며 `tool` 은 원천 표 이름, `args` 는 target_key(E7 은 agent_key 목록)다. `result` 첫 줄은 코드가 붙이는 프레이밍 `[검증 대상 — 결론 아님 · 원천: <source> · 생성: <YYYY-MM-DD>]` 이고 이 줄도 상한에 포함된다. 결측 문구는 80자 이하다.

**엔진 라인 오버헤드 규칙(상한은 라인 기준이다).** 엔진은 항목마다 `line_i = f"· [{source} · {tool}({args})] {result}"` 를 만들어 그 길이를 누적하고(PY :2164, JS :130 — 그 전에 source ≤120·tool ≤80·args ≤400·result ≤2000 으로 클램프, PY `_resolve_opts` :464-467 / JS :128-130), `Σ len(line) > 11000` 이 되는 항목부터 드롭한다(PY :2165, JS :131). 따라서 위 표의 상한 CAP[i] 는 **라인 길이**의 상한이고 `result` 의 실효 상한은 `CAP[i] − overhead_i`, `overhead_i = len(source) + len(tool) + len(args) + 10` 이다(고정 10 = 앞 `"· ["` 3자 + 구분 `" · "` 3자 + 괄호 `"("`·`")"` 2자 + 닫음 `"] "` 2자. tool 이나 args 가 비면 그 부분과 구분자는 빠진다). 예 — E1 pair: source `rr_diff`(7) + tool `summary_text`(12) + args `diff:<hex32>`(37) + 10 = 66 → result ≤1834, 프레이밍 줄(≤80)을 빼면 summary_text ≈1750자. E7: args 가 agent_key 5개(≈124) → overhead ≈171 → result ≤1229 = 프레이밍(≤80) + 좌석 줄 5×220(1100). 12항목 오버헤드 합은 ≈900 이고, 표 합을 11000 이 아니라 10600 으로 둔 것은 여유다 — 드롭 0 의 보장은 여유 400 이 아니라 '항목마다 라인 길이 ≤ CAP[i] 이고 Σ CAP = 10600 ≤ 11000' 에서 온다. `clip_lines` 는 `result` 를 실효 상한에 맞춰 줄 경계로 자르고, 총합 검증은 §5.6.2 의 assert 가 엔진과 같은 식으로 한다.

### 5.6.2 조립 알고리즘(`narrative.prior_evidence`, 결정론)

```
def prior_evidence(target, panel):
    items = [E0(target), E0c(panel.seats)]
    items += [E1, E2, E3, E4](target.kind)                     # 원천 표에서 정규 표기로 렌더(render.py)
    lineage = ra_or_local_lineage(target.project_id, hops=3)     # RA revision_of 우선, 없으면 앱 DB rr_projects.predecessor 체인
    similar = similar_projects(target, k=5)                      # §5.7 호출 계약, §7.3 알고리즘
    items.append(E5(lineage, similar, target))                   # 경로 태그 병기
    items.append(E6(similar))
    items.append(E7(panel.seats, target))                        # §5.6.3
    items.append(E8(target.diff_id) if target.kind=='diff' else NA('pair 전용'))
    items.append(E9(target.snapshot_id))
    if job.user_memo: items.append(M(job.user_memo))
    def line(it): return f"· [{it.source} · {it.tool}({it.args})] {it.result}"   # 엔진(:2164 / JS :130)과 같은 식
    for it in items:
        it.source, it.tool, it.args = it.source[:120], it.tool[:80], it.args[:400]           # 엔진 클램프 선적용(:464-466)
        overhead = len(it.source) + len(it.tool) + len(it.args) + 10                          # §5.6.1 오버헤드 규칙
        it.result = clip_lines(it.result, min(2000, CAP[it.key] - overhead))                 # 줄 경계 절단 + '…(n줄 생략)'
        assert len(line(it)) <= CAP[it.key]
    assert sum(len(line(it)) for it in items) <= 11000 and len(items) <= 12                   # Σ CAP = 10600 이라 항상 참
    lint_judgement_words(items, exempt=('quote 영역', '원문 인용 줄'))  # 위반은 생성 실패(§3 린터)
    panel.evidence_refs_json = collect_refs(items)               # reg:/narr:/rule:/c:/d: 목록 — 인용 추적
    return items
```

절단 규칙. 줄 단위로 자르고 잘린 줄 수를 `…(n줄 생략)` 로 남긴다. 한 줄이 상한을 넘으면 그 줄은 통째로 뺀다(참조 id 가 잘린 채 실리지 않게). 순서는 위 표의 순서로 고정한다 — E0·E0c·E1 은 필수, 뒤 항목은 결측 문구로 대체한다. 두 번째 이후 사이클(carried 좌석이 pending 으로 돌아온 재심)에서는 E7 에 그 좌석의 **직전 같은 타깃 발췌**를 우선 싣는다.

린터 적용 범위. 코드가 쓰는 문장(E0·E1·E2·E3·E4·E8·E9 의 표 행·프레이밍 줄·결측 문구)은 판단어 0 이어야 한다. `reg:`·`narr:`·`rule:` 의 원문 인용은 원천 인용이라 제외하되 줄 첫머리의 참조 태그로 원문임이 드러나야 한다. `rule.why_it_matters` 는 사람이 쓴 시드 파일 문장(§7.5)이라 같은 예외다.

### 5.6.3 E7 고정 슬롯(좌석 개인 기억)

대상은 `seats_json` 의 origin primary 4 + counter 1 이다(adversary 는 합성 좌석이라 없다). 좌석마다 후보를 다음 순서로 고르고 첫 적중을 싣는다.

1. `rr_seat_opinions WHERE agent_key=? AND target_key<>? AND raised_finding_ids_json<>'[]'` 를 (a) 같은 과제 계보(revision_of 체인·predecessor)의 타깃 → (b) 그 의견 finding 의 `subject_key` 가 이번 타깃 IR 의 subject_key 집합과 교집합 ≠ ∅ → (c) 최신순 으로 정렬한 1건. 좌석 줄은 `narr:<opinion_id>#<finding_id> | <agent_key> | <과제코드>/<target_key 앞 12> | <발췌>` 전체가 ≤220자이고 발췌는 `excerpt_for_rag[:220 − len(접두)]`(≈125자), 참조는 그 좌석이 제기한 첫 finding 의 `narr:<opinion_id>#<finding_id>`.
2. 앱 DB 에 없으면 AIDataHub `agent_search('risk-review-memory', q='<과제코드> <summary_text 앞 200자>', mode='hybrid', required_tags=['hwax:expert:<agent_key>'], retrieval_config={'top_k':3})` 의 첫 적중 섹션 원문(같은 220자 줄 규칙, 발췌 ≈125자. 참조는 그 레코드 `content.meta.portal.opinion_id` 로 재구성한 `narr:`). RA·AIDataHub 미가용이면 이 단계는 건너뛴다.
3. 둘 다 없으면 `[<agent_key>: 이전 발언 없음]`.

`raised_finding_ids_json='[]'` 인 의견(발언은 했으나 finding 을 제기하지 않은 좌석)은 `narr:` 문법이 finding id 를 요구하므로 싣지 않는다. 좌석당 줄 220자·좌석 합 1100자는 다른 항목이 비어도 늘리지 않는다(고정 슬롯). 산술 — E7 라인 상한 1400 − 오버헤드(source `rr_seat_opinions.self` 21 + tool `rr_seat_opinions` 16 + args agent_key 5개 ≈124 + 고정 10 ≈ 171) − 프레이밍 줄 ≤80 = ≥1149 ≥ 1100 이므로 5줄이 항상 들어간다(§5.6.1 규칙). P5 통과 기준 (3) 이 5명 표본 재현율 ≥0.8 로 이 슬롯을 검증한다.

### 5.6.4 인용 추적

브리프에 실린 `reg: · narr: · rule: · c: · d:` 목록을 `rr_panels.evidence_refs_json` 에 남기고, 패널 종료 후 `cited_refs`(§4)와 교집합을 세어 `quality_json.prior_cites_n`(선행 서술·등록부 인용 finding 수)과 `quality_json.evidence_used_ratio`(실린 ref 중 인용된 비율)를 기록한다. `narr:`·`reg:` 인용은 브리프에 실린 것만 유효하고(지어낸 선례 차단), 실리지 않은 참조는 `dangling` 으로 경험칙 강등된다.

## 5.7 유사 리스크·유사 과제 검색(호출 계약)

알고리즘은 §7.3 이고 여기서는 누가 무엇을 받아 어디에 싣는가를 고정한다.

| 호출 | 입력 | 출력 | 실리는 곳 |
|---|---|---|---|
| `GET /apps/hwax_risk/api/projects/{id}/similar?k=5`(앱 내부 `/api/projects/{id}/similar`) | 과제의 최신 스냅샷 feature_vector·character_seed·summary_text | `{lineage:[{project_id, code, hops, relation}], vector:[{project_id, snapshot_id, cosine, rank, top_features:[3]}], text:[{record_id, project_id, rank, section_id}], subject:[{subject_key, n_registry, n_verified}], merged:[{project_id, score, paths:[…]}], corpus_n}` — `corpus_n<5` 면 `vector:[]`, reason 병기 | ProjectPage '유사 과제' 탭(경로별로 따로 보여주고 섞지 않는다), E5·E6 후보 |
| `GET /apps/hwax_risk/api/precedents?diff_id=`(앱 내부 `/api/precedents`) | diff 의 semantic 이벤트 | `{delta_priors:[{change_kind, mechanism, mechanism_detail, n_raised, n_targets, n_verified, n_dismissed}], clusters:[{reg_ref, target_key, project_code, cluster_key, subject_names, severity, status, support, claim, path}], rule_hits:[…], pattern_candidates:[{pattern_id, status, n_projects, precision}]}` | ComparePage '선례' 패널, E5·E8 |
| `GET /apps/hwax_risk/api/targets/{key}/brief?tier=&exclude=E6,E8`(앱 내부 `/api/targets/{key}/brief`) | 제외할 항목 키 | 조립된 evidence 배열(§5.6) 미리보기 | RecallPreview — **항목 제외만 가능, 추가·편집 불가**(P1 을 UI 로 보장) |
| `hwax-risk` `risk_get_registry(target_key)` · `risk_claims_for_ref(ref)` · `risk_get_brief(target_key, tier='B')` | | 등록부 행 / ref 역색인 결과 / 위 brief 와 같은 evidence 배열 | 다른 심의 좌석의 자유조회(P5), L2 오케스트레이터 진입(`risk_get_brief`) |

경로는 Caddy 오리진 기준(`<heax Caddy 오리진>/apps/hwax_risk/api/…`, 포털 오리진 `/apps/hwax_risk/api/…` 도 동일)이고 인증은 §5.1 1층 행과 같다. 응답에는 왜 유사한지의 분해(세 경로 점수·공유 태그·가장 가까운 feature 3개)를 함께 내 사람이 판단한다. 절대 코사인 임계는 어디에도 없다.

## 5.8 전임 과제 서술 인용

좌석이 이전 과제의 서술을 근거로 쓸 수 있는 방법과 그 결과 처리다.

1. **허용 범위.** `narr:<opinion_id>#<finding_id>` 는 E7·E5(유사 과제 경로)에 실린 것만, `narr:<character_id>` 는 E6 에 실린 것만, `reg:<target_key>#<cluster_key>` 는 E5 에 실린 것만 인용할 수 있다. 파서(§4)는 `panel.evidence_refs_json` 과 대조해 없는 참조를 `dangling=true` 로 남기고 근거 등급을 경험칙으로 강등한다 — 버리지 않는다.
2. **인용의 효과.** finding 이 `reg:` 를 인용하면 등록부 병합 시 `rr_registry.merged_json.precedent_clusters` 에 그 ref 를 추가하고 `rr_findings.finding_json.precedent_refs` 에도 적는다. `precedent` 값(in_range/out_of_range/none)은 인용 여부가 아니라 인용 수치가 코퍼스 feature 범위 안인지로 코드가 따로 부여한다(§4·§7).
3. **선례의 검증 상태 노출.** E5 줄에 `status verified` 또는 `dismissed` 가 붙으면 반대석은 "그 선례는 과거에 기각됐다" 를 통계로 말할 수 있다(§6 반대석 역할 문구). 예측값(도구예측)만 있는 선례는 `open` 으로 남아 있다.
4. **기록.** `quality_json.prior_cites_n ≥ 1` 인 패널 수가 P5 통과 기준 (4) 이고, 인용된 선례 finding 은 `rr_findings.finding_json.cited_by_later[]` 에 후속 `claim_uid` 를 누적한다(선례가 실제로 쓰였는지의 원자료).
5. **RA.** 선례 인용 자체는 새 관계로 만들지 않는다(12관계 고정). 후속 finding 의 `raised_by` 만 만들고 선례 링크는 앱 DB `rr_findings.finding_json.precedent_refs` 로만 보관한다.

## 5.9 다른 connectivity(계보 없는 과제)에서의 재사용 단위

계보(revision_of)가 없는 새 과제 Z 에서 과제 X 의 finding 이 떠오르려면 과제 무관 키가 필요하다. 1차 합성의 ckey 는 base/target 쌍 단위여서 이 요구를 만족하지 못했다(gap_21 #2). 여기서는 전역 키 3개 — `ckey`(파트) · `alias_key`(계면) · `subject_key`(finding 주체) — 를 정의하고 회수 알고리즘을 적는다.

### 5.9.1 `canonical_part_key`(ckey) 계산

계산식은 §2.7.3 이 정본이고 여기 옮겨 적는다(바이트 동일).

```
name_norm        = §2.7.1 규칙(소문자 → '#\d+$' 제거 → auto_named 이면 '_\d+$' 제거 → Dyna 'Group\Name' 은 구분자 뒤만 → '[^a-z0-9]+'→'_' → 양끝 '_' 제거)
name_norm_canon  = §2.7.1 규칙(과제 코드·stop_tokens 제거 → 두께·치수 토큰 제거 → rr_dim_vocab.synonyms_json 동의어 치환(hsg|housing→housing) → '_' 재결합). 동의어 사전 초기 항목은 §2.7.1 시드 v1, 명명 규칙 합의는 §10 열린 질문 (14a)
geom_bucket      = 'x'.join(str(round(s / 0.5) * 0.5) for s in size_sorted) + '@v' + (str(round(log(volume) / log(1.05))) if volume else '?')   # 0.5 mm 버킷·부피 5% 버킷(volume null → '@v?')
material_norm    = mcad attrs.material 의 첫 토큰(동의어 치환 후) | dyna material.db.tag ?? material.db.name ?? material.kfile.name 의 첫 토큰 | ecad part_number 첫 토큰 | 'na'
ckey             = 'ck:' + sha1(name_norm_canon + '|' + geom_bucket + '|' + material_norm)[:12]
```

프로젝트명·인스턴스 접미·자동명 번호·좌표계가 계산에 들어가지 않으므로 다른 과제에서 같은 파트를 같은 이름 계열·비슷한 크기·같은 재료로 넣으면 같은 ckey 가 나온다. 버킷 경계에 걸리는 경우는 §5.9.4 의 geom_fp 근접 매치가 받는다. 사람이 `rr_part_keys` 에서 merge/rename 하면 병합 결과가 우선한다 — 조회 시 `merged_into` 를 끝까지 따라가 대표 ckey 로 치환한다(`resolve_ckey()`).

### 5.9.2 `rr_part_keys` 원장

- 스냅샷 생성 시 새 ckey 는 `status=candidate` 로 `INSERT OR IGNORE`, 기존이면 `n_snapshots+1`, `aliases_json` 에 `{name_norm, project_id, source_kind}` 를 추가(중복 제거).
- 사람 확정(`confirmed`)은 SnapshotPage 노드 표에서 한다. 병합은 `status=merged, merged_into=<대표>` 이고 대표 쪽 `aliases_json` 에 흡수한다. 병합 취소(`POST /api/sameas/decide {decision:'unmerge_key', ckey}`, §2.7.3 자동 승계 행 포함)는 새 행을 만들지 않고 `merged_into=NULL, status=confirmed, merge_evidence_json=NULL` 로 되돌린다.
- `ra_part_entity_id` 는 RA `part` 축에 같은 이름의 값이 **이미 있을 때만** 사람이 연결한다(자동 생성 금지). 연결되면 `aliases_json` 의 이름들을 `add_object_alias(part)` 로 RA 에도 이중 보관한다.
- `visibility=org` 인 ckey 만 다른 사용자의 스냅샷에서 동의어 치환에 쓰인다(P6 결정 전까지는 자기 것만).

### 5.9.3 계면 별칭 사전 `rr_iface_alias`

- 키는 무순서 ckey 쌍 `alias_key='<ckey_a>|<ckey_b>'`(정렬). `canonical_a/b` 는 `resolve_ckey()` 를 거친 대표다.
- 스냅샷의 모든 계면 엣지(kind_family ∈ tied·touching·clearance·interference·contact)마다 `INSERT OR IGNORE`(source=auto, score=1.0) 하고 `aliases_json` 에 `{name_a, name_b, asm_key_a, asm_key_b, project_id, snapshot_id}` 를 누적한다. `asm_key`(§2) 가 별칭의 원천이라 '어느 서브어셈블리의 어떤 이름으로 불렸나' 가 사전에 남는다.
- **근접 별칭 제안.** 한쪽 ckey 는 같고 다른 쪽이 다른 계면이 있을 때 다른 쪽 노드끼리 geom_fp 근접(§5.9.4)이면 `source=auto, score=0.8` 의 새 alias 행을 만들고 두 alias_key 를 서로의 `aliases_json.merged_candidates` 에 적는다. 사람이 SameAsResolver 에서 확정하면 `source=human, score=1.0` 이 되고 두 행은 대표 하나로 병합된다.
- 사람 확정 별칭은 RA `part` 축에도 `add_object_alias` 로 이중 보관한다(양쪽 파트가 RA part 에 연결돼 있을 때만). `ra_alias_ids_json` 에 결과를 적는다.
- `subject_key` 계산과 `cluster_key` 계산은 항상 이 사전을 거쳐 별칭 수준으로 정규화한 뒤 한다(§0.1.4). 따라서 다른 connectivity 에서 만든 finding 도 같은 `cluster_key` 로 모인다.

### 5.9.4 회수 알고리즘(subject_key 정확 매치 + geom_fp 근접)

새 타깃 Z(계보 없음)의 브리프를 조립할 때 §7.3 4단계가 다음을 한다.

```
S_Z = { subject_key(e) for e in rr_ir_edges[Z.snapshot] } ∪ { ckey(n) for n in rr_ir_nodes[Z.snapshot] } ∪ { 'dim:'+name for name in dims_named }
      ∪ { 'asm:'+p for p in rr_ir.rollups.by_assembly[].path_prefix }        # 전부 resolve_ckey() 후 유효 ckey 로
# 1) 정확 매치
hits = rr_registry WHERE subject_key IN S_Z AND status IN ('open','verified') AND (owner_sub=? OR visibility='org')
# 2) 근접 매치(정확 매치가 0건인 subject 에 대해서만) — 파트 근접 정의는 §2.7.3(size ±1 버킷 · material 동일 · volume 무관)
near_part(x) = rr_part_keys WHERE name_norm_canon = x.name_norm_canon AND material_norm = x.material_norm
               AND |size_bucket_i(ckey) − size_bucket_i(x)| <= 1 for all i(0.5 mm 단)      # geom_bucket 의 '@v' 부분은 보지 않는다
               AND resolve_ckey(ckey) != resolve_ckey(x.ckey)
# 2a) 파트 단독 subject(ck:)
for n in Z 리프 노드 with no exact hit on ckey(n):
    for k in near_part(n):
        alias_candidate_part(n.ckey, k.ckey)                     # rr_part_keys.aliases_json.merged_candidates 제안(사람이 merge_key)
        hits += rr_registry WHERE subject_key = resolve_ckey(k.ckey)   # 경로 태그 [subject·별칭후보]
# 2b) 계면 subject(ck|ck)
for e in Z 계면 엣지 with no exact hit:
    for side in (a, b):
        cands = rr_ir_nodes WHERE ckey = e.ck_other_side          # 한쪽은 ckey 동일
        near  = near_part(e.side)                                 # §2.7.3 정의(이름 계열이 같고 크기 버킷이 ±1 안)
                ∪ [n for n in rr_ir_nodes WHERE abs(size_sorted[i]-e.side.size_sorted[i]) / max(…) <= 0.05 for all i
                   AND abs(volume - e.side.volume)/max(…) <= 0.05 AND material_norm == e.side.material_norm]   # 이름이 다른 경우의 geom_fp 근접
        for n in near: alias_candidate(e.ck_side, n.ckey)         # §5.9.3 근접 별칭 제안(score 0.8)
        hits += rr_registry WHERE subject_key = sorted_pair(e.ck_other_side, n.ckey)   # 별칭 후보 경유 회수, 경로 태그 [subject·별칭후보]
# 2c) asm: subject 는 정확 매치만(파일명·어셈블리명이 같은 과제 사이에서만 일치) — 경로 태그 [subject·asm]
# 3) 정렬·절단
rank by (exact > alias_candidate), sev3 desc, support desc, updated_at desc → E5 상한 안에서 자름
```

정확 매치는 `[경로: subject]`(`asm:` 주체는 `[경로: subject·asm]`), 근접 매치는 `[경로: subject·별칭후보 score=0.8]` 로 E5 줄에 표기해 좌석과 반대석이 그 대응 자체를 검증 대상으로 본다. 근접 매치는 G2 게이트 대상이 아니다(diff 의 same_as 가 아니라 회수 후보일 뿐이다).

### 5.9.5 원장 상속 제안(connectivity 구축 재사용)

새 과제의 스냅샷을 만들 때 `rr_iface_ledger`(다른 과제, 같은 alias_key 로 매핑되는 pair_key)와 `rr_sameas(scope=intra)`(같은 ckey 쌍)의 사람 확정을 **상속 후보**로 SameAsResolver·계면 표에 제시한다. 자동 적용은 하지 않고 `status=auto, score=0.8` 로 붙여 사람이 확정하게 한다(확정하면 그 과제의 원장 행이 새로 생긴다). 이로써 과제가 쌓일수록 새 connectivity 의 same-as·계면 확정 작업이 줄어든다 — 이것이 '다른 connectivity 를 만들 때 남겨놓은 데이터를 쓰는' 두 번째 경로다(첫째는 §5.9.4 의 finding 회수, 셋째는 §7.5 의 rule_hits 다).

### 5.9.6 통과 기준(§9 와 동일)

- P2 (11). 같은 파트를 다른 프로젝트명·다른 인스턴스 접미·다른 자동명으로 넣은 합성 두 프로젝트에서 ckey 일치율 ≥0.95, subject_key 일치율 ≥0.95. 같은 프로젝트의 합성 리비전(§4.9 PROTECT_FILM 두께 −25%·OCA_TOP 부피 +50% 변형)에서 §2.7.3 자동 승계를 거친 subject_key 일치율 ≥0.95, §4.9 픽스처의 F2·G1 cluster_key 가 DV1→DV2 동일.
- P5 (5). 계보 없는 합성 과제(revision_of 없음)에서 동일 계면(subject_key 동일 또는 geom_fp 근접)의 이전 finding 이 E5 로 회수 ≥1 이고 경로 태그가 `subject` 또는 `subject·별칭후보` 다.
- P5 추가. 상속 후보가 제시된 계면을 사람이 확정한 뒤 재캡처하면 `status=manual_ledger` 로 복원된다(P2 (4) 와 같은 규칙이 과제 간에도 성립).

---


# §6 전문가 크로스도메인 워크플로

이 절은 "전체 HW/XD 전문가가 한 번씩 각자 도구를 다뤄 리스크를 생각해 보는 과정" 을 하나의 메뉴로 만드는 실행 계약이다. 이름은 전부 §0 정본을 따르고, 1차 합성(doc_20 §6.4~§6.11)의 어휘·수치를 보존하되 1차 비평(gap_21)이 코드로 확인한 모순 4건(좌석 계약 role 접미 유실, apps 제한이 계약 도구 제거, SSE status 에 persona 필드 없음, toulmin 재시도·120 초과 재실행)과 공백(전원 요구 대 C2 마감, C1 의 RA 의존, PAT 발급 미확인, 불변식 검증력)을 고친 채로 적는다. 고친 자리는 본문에 `[gap 수정]` 으로 표시한다.

## 6.1 이 메뉴가 하는 일(한 줄, 애매동사 금지)

"전체 HW/XD 전문가가 정해진 타깃(`snap:` 단일 현황 또는 `diff:` 기준 대비 변경)에 대해 각자 도구를 실호출해 리스크·개선·성격을 판정한 **리스크 심사 보고서를 만든다**". 산출은 결정 문서(패널 결정문 + risk_spec + 타깃 등록부 + 통합 보고서)까지다.

하지 않는 것. 설계 변경 실행, 시험 수행, StepForge `set_interface/confirm_interfaces` 나 DynaForge `run_job/run_operation` 의 자동 호출, verdict 자동 승인, 보고서 자동 배포. 좌석은 읽기 전용 도구만 자유조회하고(§6.5), 사람 확정은 앱 DB 원장(§2)과 verdict UI(§6.9)에서만 일어난다.

이 절이 정의하는 것. 로스터 고정(§6.3) → 결정론 편성(§6.4) → 좌석 계약(§6.5) → Job 'risk-review'(§6.6) → 러너 시퀀스(§6.7) → 커버리지 회계 상태기계(§6.8) → 완결 판정(§6.9) → 비용·예산(§6.10) → MCP 경로 등급(§6.11). 서술 스키마(risk_spec·finding·seat_opinion)는 §4, 브리프 E0~E9 는 §5, 통합 보고서 블록은 §4·§8 이 정의하고 여기서는 호출만 한다.

## 6.2 좌석 유형과 패널 구조

| 좌석 | origin | 수 | 누구 | 역할 |
|---|---|---|---|---|
| 로스터석 | `primary` | 4 | `rr_coverage` 에서 `pending` 인 HW/XD 전문가(도메인 내 relevance 순) | 자기 도메인 관점에서 IR/diff 를 도구로 검증하고 finding/gain 을 제기 |
| 반대 도메인석 | `counter` | 1 | primary 도메인들의 인접 표(§6.4)에서 뽑은 다른 도메인의 `pending` 전문가(원장에서 소진) | 주 도메인이 못 보는 2차 리스크·교차 도메인 상호작용(cross_domain) |
| 기준선 옹호 지정석 | `adversary` | 1 | 합성 좌석 `delib-baseline-defender`(엔진 `_CHAIR_ADVERSARY["risk-review"]` 가 자동 push, 원장 미집계) | 과잉 경보 억제·개선점 대변·근거등급 낮은 finding 기각 요구 |
| 재심 신규석 | `new` | 0 | — | 발동 조건(human_note·continue_summary 존재)을 러너가 만들지 않으므로 앉지 않는다(§6.7, 불변식 `extra_seats == ∅`) |

패널 = 6석(로스터석 5 + 지정석 1), rounds 3(초기 독립 → 반박·인용 → 수렴), `free_tools=1`, `tool_budget=3`, `chair_template='risk-review'`, modifiers 기본 `['toulmin']`(Tier A 잡은 `premortem` 추가 선택). 좌석 과다 방지 원칙(sim +2·test +2)과 같은 선에서 패널당 6석 고정이고, 커버리지는 회차로 채운다. 좌석 착석 경로는 엔진의 continue_personas 경로다 — `delib_opts.personas` 가 있으면 발굴(`_discover`)과 반대 도메인 좌석(`_counter_seats`)을 건너뛰고 지정 좌석만 앉히므로(deliberation.py:2036-2044) 편성기가 정한 5석이 그대로 앉고, `_restore_role` 이 `get_agent_session` 으로 원본 role 을 복원한다(:1360-1369).

## 6.3 전문가 풀 산정과 로스터 고정(`rr_roster`)

- 도메인 집합 HWXD 도메인 15 = `xd · sim · cam · rel · soc · disp · mech · pcb · rf · passive · pwr · sh · mem · std · material` — `list_agent_domains` 결과에서 `sw`(408), `oss`, `misc`, `kooremapper`, `dynaforge` 를 제외한 것. 코드 상수가 아니라 Settings `risk_roster_domains`(기본값 위 15개)로 두어 사용자가 조정한다(cam·soc·std·material 포함 여부는 열린 질문 §10).
- 로스터 생성 시점 = 타깃 생성(`POST /api/targets`, consent:true) 시점. 코드가 도메인마다 `list_agents(compact=true, domain=d)` 로 키를 모아 `rr_roster{target_key, agent_key, domain, relevance, rank_in_domain, frozen_at, owner_sub}` 에 **고정**(`rr_targets.roster_frozen_at`)하고 같은 키로 `rr_coverage` 행을 `pending` 으로 만든다. 도메인은 `_dom_of(agent_key)` = 키의 첫 `-` 앞 접두사이며 `list_agents` 의 domain 값과 대조해 다르면 `list_agents` 값을 쓴다.
- 관련도 `relevance` = `recommend_agents(q=<summary_text 또는 rr_state 요약 앞 500자>, top 60)` 의 점수(목록 밖은 0). 도메인 내 정렬 = relevance desc, agent_key asc → `rank_in_domain`(1부터). 이 순서가 Tier 편성 순서다. 전문가별 이력 보정(§7.2 과거 IR 인용률)은 P6 이후 relevance 에 가산한다.
- ECAD 의존 도메인 6 = Settings `risk_ecad_domains`(기본 `pcb · pwr · rf · soc · passive · mem`). 타깃 스냅샷의 `missing.ecad_absent=true` 이면 이 도메인의 로스터 행은 `rank_in_domain=1` 대표 1석만 `pending` 으로 두고 나머지는 처음부터 `deferred(reason=ecad_absent)` 종결 상태로 만든다. 같은 과제에 ECAD 가 있는 스냅샷이 동결되어 새 타깃이 생기면 그 타깃의 로스터에서 `pending` 으로 되살아난다.
- 로스터 갱신은 사용자가 `POST /api/targets/{key}/refresh_roster` 를 누를 때만 일어난다. `list_agents` 에 새로 생긴 키만 `pending` 행으로 추가하고 `rank_in_domain` 은 기존 최대값 다음부터 붙인다(이미 편성된 패널의 결정론을 깨지 않는다). 기존 행(종결·비종결)은 불변이다.
- 실측 규모 ≈350(xd 122 · sim 22 · cam 21 · rel 20 · soc 20 · disp 19 · mech 19 · pcb 19 · rf 19 · passive 18 · pwr 18 · sh 17 · mem 16 · std 8 · material 1). ECAD 부재 시 deferred = 110 − 6 = 104 ≈105 석이고 pending ≈245 석이다. 이 수치는 `POST /api/targets` 응답 `{roster_size, deferred, tier_plan, cost_estimate}` 로 사용자에게 먼저 보이고 동의를 받는다.

## 6.4 패널 편성기 `planner.py`(결정론, LLM 없음)

### 6.4.1 Tier 정의와 산술

| Tier | 목적 | 좌석 범위(`rank_in_domain` 조건) | 누적 좌석(≈350) | 패널 수 ECAD 있음 | 패널 수 ECAD 부재 |
|---|---|---|---|---|---|
| A 대표 | 모든 도메인이 한 번은 본다 | `rank == 1`(15명) | 15 | 3 | 3 |
| B 심층 | 도메인별 상위 30% | `rank ≤ ceil(0.3·\|d\|)` | 114 | +20 | +14 |
| C 전원 | 로스터 소진 | 전원(deferred 제외) | 350 / 246 | +48 | +33 |
| 합계 | | | | 71 | 50 |

산술. 도메인별 `ceil(0.3·|d|)` = xd 37 · sim 7 · cam 7 · rel 6 · soc 6 · disp 6 · mech 6 · pcb 6 · rf 6 · passive 6 · pwr 6 · sh 6 · mem 5 · std 3 · material 1 → 합 114(A 15 포함). ECAD 부재면 6 도메인이 대표 1석만 남아 114 − 29 = 85. 패널 수 = ceil(추가 좌석 / 5). C 는 350 − 114 = 236 → 48패널, ECAD 부재면 246 − 85 = 161 → 33패널. §0.1.5 Tier 행과 §0.6 상수표 'Tier 패널 수' 행이 이 표와 같은 규칙·같은 수치(3/20/48, ECAD 부재 3/14/33)를 정본으로 들고 있고, `planner.tier_plan(target)` 이 같은 규칙으로 로스터 실측에서 다시 계산해 `POST /api/targets` 응답과 진행판에 낸다(`backend/tests/test_planner.py` 가 세 곳의 수치를 대조한다).

### 6.4.2 편성 알고리즘(`plan_next_panel(target_key, tier) -> seats_json | None`)

1. Tier 범위 안의 `pending` 행을 도메인별 큐로 만든다(정렬 `rank_in_domain` asc).
2. primary 4석 — 큐 잔량이 가장 큰 도메인부터(동률이면 도메인명 asc) 라운드로빈으로 1명씩 뽑아 **서로 다른 도메인 4석**. 잔량 있는 도메인이 4 미만이면 같은 도메인 최대 2석까지 허용하고, Tier C 에서 xd 는 최대 3석·비-xd ≥2석을 강제한다(xd 85석이 C 의 과반이라 편중을 막는 규칙).
3. counter 1석 — primary 좌석 순서대로 그 도메인의 인접 표 목록을 순회해 아직 이 패널에 앉지 않은 도메인의 `pending` 1명(rank 최소). 인접 표 v1(`adjacency.v1.json`, Settings `risk_adjacency` 로 덮어씀) `mech↔[pcb,disp,sh] · pcb↔[mech,pwr,rf,std] · sim↔[rel,mech,material] · rel↔[sim,material,std] · pwr↔[pcb,rf,soc,passive] · rf↔[pcb,pwr,mem] · disp↔[mech,xd] · cam↔[mech,xd] · soc↔[pwr,mem,sh] · passive↔[pwr,pcb] · sh↔[mech,soc] · mem↔[soc,rf] · std↔[rel,pcb] · material↔[sim,rel] · xd↔[mech,disp,cam]`. 인접에 `pending` 이 없으면 잔량 최대의 다른 도메인, 그것도 없으면 counter 없이 4석(엔진 최소 2석 조건은 항상 만족).
4. 선점 — `INSERT OR IGNORE INTO rr_coverage(...) VALUES(... 'pending')` 뒤 `UPDATE rr_coverage SET status='assigned', panel_id=?, origin=? WHERE target_key=? AND agent_key=? AND status='pending'` 를 좌석마다 실행하고 총 rowcount 가 좌석 수(정상 5, 꼬리 패널은 2~4)와 다르면 트랜잭션을 롤백한다(동시 편성 경쟁 방지). 부분 유니크 인덱스 `rr_cov_active` 는 §6.8 에 정의한다.
5. `rr_panels` 행 생성 — `{id, target_key, panel_no(타깃 내 1부터), tier, seats_json, status='planned', engine='web', tool_mode='tools', budget_json(§6.10), created_at}`. `seats_json = [{key, domain, origin, rank_in_domain}]` 이고 **role 은 저장하지 않는다**(엔진이 복원, 계약은 엔진 상수 — §6.5). 같은 원장 상태·같은 Settings 이면 같은 seats_json 이 나온다(결정론 테스트 `backend/tests/test_planner.py`).
6. 편성은 미리 전부 하지 않고 러너가 다음 패널을 요구할 때마다 1건씩 한다(사용자가 그 사이 `skipped`·carried 되돌림을 했을 수 있다). Tier 범위의 `pending` 이 0 이면 `None` 을 돌려주고 잡은 `completed` 로 간다.

### 6.4.3 회차·중단 규칙

- 타깃당 패널은 **직렬**이다(같은 IR 을 두 패널이 동시에 보면 등록부 병합 순서가 흔들린다). 서버 전역 동시 패널은 Settings `risk_concurrency=2`(타깃이 다를 때만). 단일 vLLM 에서 2 는 처리량 2배가 아니므로 벽시계 추정은 직렬 기준이다(§6.10).
- 수확 체감 정지 — 최근 3패널이 각각 신규 클러스터(§4 등록부 병합에서 새로 생긴 cluster_key) < 1 을 추가했고 C1 이 충족되면 잡을 `paused(reason=diminishing)` 로 두고 사용자에게 마감을 제안한다. 제안 문구는 `risk_default_close_level`(§6.9)에 따라 "C2 로 마감" 또는 "C3 까지 계속" 이고, 재개하면 편성이 이어진다.
- 일일 상한 Settings `risk_daily_panel_cap=24` 를 넘기면 `paused(reason=daily_cap)` 로 두고 다음 날 00:00(서버 로컬) 이후 첫 폴링에서 자동 재개한다.
- 잡 상태 `rr_jobs.state ∈ queued · running · paused(reason: diminishing|daily_cap|user) · cancelling · cancelled · completed · failed`. 취소·일시정지는 패널 경계에서만 반영된다(진행 중 패널은 끝까지 간다). 연속 3패널 `error` 면 `failed(error=engine_fail_streak)`.

## 6.5 좌석별 도구 사용 계약

### 6.5.1 세 경로(엔진 기능 그대로)

| 경로 | 무엇 | 예산 | 누가 정하나 |
|---|---|---|---|
| 지정 도구 `delib_opts.tools`(≤6) | 패널 공통 필수 근거 — 심의 전 코드가 LLM 인자 구성으로 실호출(:1972-2031, self-repair 1회), tool_inject ≤5000자를 전 좌석이 공유 | 도구당 LLM 1~2회 | 편성기. pair: `list_interfaces`, `interface_graph`, `report_part_risk`(dyna_result 있을 때), `compare_reports`(report_ids 2개 이상일 때만). single: `list_interfaces`, `interface_graph`, `inspect_report`, `report_part_risk`. 전사 분포 도구(`section_contact_usage`·`material_usage`)는 넣지 않는다. 인자는 **target 스냅샷의 소스 id** 로 구성되게 질문 문자열과 E0 에 target id 를 먼저 쓰고 base id 는 괄호로 뒤에 둔다(base 쪽 수치는 E2~E4 표에 이미 있다) |
| 자유 조회 free_tools | 좌석이 발언 전 ReAct 로 직접 호출(1R·2R, 수렴 라운드 제외 :2288), 같은 도구·인자 캐시 공유(:1278-1298), 결과 블록 3500자/석 | `tool_budget` 3/라운드 → 좌석당 ≤6 실호출 | 좌석(도메인 계약이 방향을 준다) |
| 지식카드 `agent_search` | 좌석 자신의 지식카드 3500자/석, `q=question` 고정(:2119) | 1회/라운드, LLM 0 | 엔진(오염 없음 — 의견 레코드 `agents` 에 실 전문가 키를 넣지 않는다, §5) |

`delib_opts.apps = ['heax-step_forge', 'heax-kooremapper_mcp', <ECAD 어댑터 앱키 또는 생략>]`(≤3). 앱키는 하드코딩하지 않고 `adapters/registry.py` 가 게이트웨이 `/tools-map` 에서 kind 별로 발견한 값을 쓴다.

### 6.5.2 자유조회 통과 경로 3종 `[gap 수정 — apps 제한이 계약 도구를 제거하던 모순]`

자유조회 목록은 두 단계로 만들어진다. (1) 조립식 `_g`(deliberation.py:1897-1898)가 게이트웨이 도구 전부를 `_free_tool_ok(n)`(접두사 `_FREE_ALLOW` :1233-1240, 거부 `_FREE_DENY` :1241)로 **먼저** 거르고, (2) 앱 제한 분기(:1914-1927)의 `_narrow`(:1916-1918)가 `apps` 가 있으면 그 `_g` 를 `agent_search`·`_MATERIAL_TOOLS`·지정 앱 소속 도구로만 좁힌다. 두 가지 결손이 있다. (a) `_RISK_READ_TOOLS` 의 전 항목(project_tree·interface_graph·inspect_report·mass_estimate·mesh_report·part_mesh_map·inspect_file·report_*·section_contact_usage·operation_usage·corpus_summary·risk_*·odb_*)과 `_RISK_KEEP_TOOLS` 의 `pcb_warpage_surrogate` 는 `_FREE_ALLOW` 접두사에 하나도 걸리지 않아(map_4 실계산과 동일) (1) 에서 이미 `_g` 에 없으므로 `_narrow` 의 or 조건만으로는 살릴 수 없다 — 그렇게 구현하면 §6.5.3 계약표의 'app+read' 열(mech 의 interface_graph·inspect_report·mass_estimate, sim 의 report_*·inspect_file, rel 의 report_findings, disp/cam/sh 의 report_part_risk, P5 hwax-risk 4종, P7 odb_*)이 전부 죽는다. 검사 지점은 `_g` 조립식이어야 한다. (b) RA(`reportarchive`)·열충격(`heax-thermal_shock_mcp`)·laminate·AIDataHub 도구는 접두사는 통과해도 apps 에 없어 (2) 에서 제거되므로 keep 목록은 `_narrow` 에도 or 가 필요하다. 변경은 다음 두 곳이며 `_FREE_ALLOW`·`_FREE_DENY`·`_MATERIAL_TOOLS` 전역 목록은 바꾸지 않는다.

```python
# deliberation.py :1897-1898 — 조립식 조건 확장(≈3줄). :1915 의 `_amap = _app_of_tools()` 는 이 앞으로 올리고 :1915 의 대입은 지운다.
_amap = _app_of_tools()                     # 게이트웨이 불통이면 {} — read 분기만 비활성, free_allow·keep 은 그대로
_apps = set(opts.delib_apps)
_g = {n: _wrap_cached(t, _fcache)
      for n, t in (await _tools_by_name(app, groups, user=user, user_pat=user_pat)).items()
      if n.lower() not in _FREE_DENY and (                                   # _FREE_DENY(get_agent_session) 가 항상 우선
          _free_tool_ok(n)
          or (_amap.get(n) in _apps and n in _RISK_READ_TOOLS.get(_amap.get(n), ()))
          or (opts.chair_template == "risk-review" and n in _RISK_KEEP_TOOLS))}
# :1916-1918 `_narrow` — keep 도구는 apps 밖 앱 소속이라 1줄만 더한다(read 도구는 이미 앱 소속이라 세 번째 조건으로 통과)
_narrow = {n: t for n, t in _g.items()
           if n == "agent_search" or n in _MATERIAL_TOOLS
           or _amap.get(n) in _apps
           or (opts.chair_template == "risk-review" and n in _RISK_KEEP_TOOLS)}
```

세 경로를 명시해 표로 잡는다.

| 통과 경로 | 정의 | 조건 | 다른 심의 영향 |
|---|---|---|---|
| `app`(+`free_allow` 또는 +`read`) | 도구가 `apps` 의 앱에 속하고, (a) 전역 접두사 `_FREE_ALLOW`(:1233-1240)를 통과하거나 (b) `_RISK_READ_TOOLS[<앱키>]` 명시 목록에 있음. (b) 의 검사 지점은 `_g` 조립식(:1897-1898)의 두 번째 or 조건이고 `_narrow` 는 앱 소속 조건으로 그대로 통과한다 | chair_template 무관 | (b)는 apps 로 그 앱을 고른 다른 심의도 같은 읽기 도구를 얻는다 — 의도된 읽기 전용 확장, decision-table.md "기존 심의 영향" 항목 |
| `keep` | `_RISK_KEEP_TOOLS` 명시 목록 — `('search_objects','get_object','get_subgraph','search_reports','predict_sed','check_design_rules','pcb_warpage_surrogate','get_reference_cases')`, P5 에서 `risk_get_snapshot·risk_get_diff·risk_get_registry·risk_claims_for_ref` 4종 추가 | `chair_template == 'risk-review'` 일 때만. 검사 지점 2곳 — `_g` 조립식(:1897-1898)의 세 번째 or 조건(`pcb_warpage_surrogate` 는 접두사 검문에 걸리지 않으므로 여기서 살린다, 나머지 7종은 `search_·get_·predict_·check_` 접두사로도 통과)과 `_narrow`(:1916-1918)의 or 1줄(`_MATERIAL_TOOLS` 와 같은 방식 — RA·laminate·열충격 앱이 apps 에 없어도 남긴다) | 0(조건부). `_FREE_ALLOW` 전역 목록은 바꾸지 않고 P0 통과 기준 (5)(8) 이 실측한다 |
| `material` | `_MATERIAL_TOOLS`(MaterialTwin `get_material·compare_materials·find_materials_in_property_range·list_materials` 등, P0 (5) 단위 테스트에서 실측 확인) | 엔진이 항상 남김 | 0 |

`_RISK_READ_TOOLS`(deliberation.py, 앱 조건부 — 쓰기 도구 미포함).
```
_RISK_READ_TOOLS = {
 "heax-step_forge": ("project_tree","interface_graph","inspect_report","mass_estimate","mesh_report","part_mesh_map"),
 "heax-kooremapper_mcp": ("inspect_file","report_summary","report_case","report_findings","report_part_risk","report_energy_flow","report_directional","report_worst_cases","report_part_series","report_scatter","report_corpus","section_contact_usage","operation_usage","corpus_summary"),
 "heax-hwax_risk": ("risk_get_snapshot","risk_get_diff","risk_get_registry","risk_claims_for_ref"),   # P5 — 앱키는 게이트웨이 registry 발견값(heax-<매니페스트 id>), A 계획의 'hwax-risk' 아님
 # <ECAD 어댑터 앱키>: ("odb_get_board","odb_list_components","odb_list_nets","odb_get_stackup")   # P7, 앱키는 registry 발견값
}
```
쓰기 도구(`run_job·run_operation·set_interface·confirm_interfaces·remesh_parts·upload_*·add_training_data·create_object·update_object·link_objects·import_record·bind_records_to_agent·patch_agent`)는 어느 경로에도 절대 없다.

### 6.5.3 도메인별 계약표(`seat-contract.v1.json` 이 원천)

| 도메인 | 1R 발언 전 필수 호출(≥1) | 권장 | 산출 형식 | 통과 경로 |
|---|---|---|---|---|
| mech | `list_interfaces(kind=interference\|touching)` 또는 `interface_graph` | `inspect_report`, `mass_estimate(densities 출처 명시)`, `list_parts(name_like)` | 계면 실명 쌍 + min_gap/penetration(하한 표기) + `[e:]`·`[c:]`·`name:A\|B` 인용 | list_interfaces·list_parts: app+free_allow / interface_graph·inspect_report·mass_estimate: app+read |
| xd | `list_parts` 또는 `list_interfaces(kind=clearance)` | `project_tree`, `get_part_rules` | 조립 순서·공차 여유·서비스성, `[d:]` dims_named 인용 | list_parts·list_interfaces·get_part_rules: app+free_allow / project_tree: app+read |
| sim | `report_part_risk` 또는 `compare_reports`(pair, report_ids ≥2) | `report_energy_flow`, `report_worst_cases`, `inspect_file` | 파트별 최악값·over_yield_ratio·load_path 엣지 인용, kind 불일치면 정성만 | compare_reports: app+free_allow / report_*·inspect_file: app+read |
| rel | `report_findings` 또는 RA `search_objects(type=incident)` | `report_worst_cases`, `predict_sed`(패키지 배치 치수 있을 때), `get_reference_cases` | trigger_condition 명시, precedent in/out_of_range, `inc:` 인용 | report_findings: app+read / search_objects·predict_sed·get_reference_cases: keep |
| pcb·pwr·rf·soc·passive·mem | ODB 어댑터 `odb_*`(ECAD 앱이 apps 에 있을 때) 또는 `list_parts(name_like)`; 부재 시 `ecad_absent` 를 발언에 명기 | `check_design_rules`, `pcb_warpage_surrogate`, `predict_sed`, RA `get_subgraph` | 보드 근접 계면·스택업 변화, 결측이면 undetermined 허용 | odb_*: app+read(P7) / list_parts: app+free_allow / check_design_rules·pcb_warpage_surrogate·predict_sed·get_subgraph: keep |
| material | `get_material` 또는 `compare_materials` | `material_usage`, `find_materials_in_property_range` | 재료 교체 물성 delta 수치 | get_material·compare_materials·find_materials_in_property_range: material / material_usage: app+free_allow |
| disp·cam·sh | `list_interfaces`(모듈 주변 계면) | `interface_graph`, `report_part_risk` | 모듈 경계 계면 실명 | list_interfaces: app+free_allow / interface_graph·report_part_risk: app+read |
| std | `check_design_rules` 또는 RA `search_objects` | `search_reports`, `get_object` | 규격 번호 인용([문헌·규격]) | 전부 keep |

계약 문구(공통, `_common`). "[리스크 심사 좌석 계약] 1R 발언 전 당신 도메인 도구를 1개 이상 실제 호출하고 결과 수치와 id([c:]/[e:]/[p:]/[d:]/name:A|B)를 인용하라. 인용 없는 주장은 [경험칙]으로 등급이 내려간다. 근거는 검증 대상이지 결론이 아니다. interference·touching 의 'auto' 는 미확정 초안이고 penetration_depth 는 하한 추정치이며 contact_area_est 는 접촉면적이 아니라 공차 밴드 면적이다. null 은 미측정이지 0 이 아니다. 리스크만 나열하지 말고 개선점도 같은 형식으로 내라. 판정 불가면 '판정 불가 — 다음 확인 X' 로 답하라. 도구 호출 경로가 없는 실행(evidence_only)에서는 [근거]의 수치를 같은 형식으로 인용하라." 도메인 줄은 표의 필수·권장·산출 형식을 `[<dom>] 필수: … 권장: … 산출: …` 한 줄(≤500자)로 직렬화한 것이다.

### 6.5.4 계약 전달 경로 `[gap 수정 — personas[].role 접미가 _restore_role 에 덮여 유실되던 모순]`

주경로 = 엔진 상수. 코드 대조 결과 `_restore_role`(deliberation.py:1358-1369)은 `get_agent_session` 이 description 을 돌려주면 호출자가 준 role 을 버리고 원본으로 교체하며(`_ROLE_CLIP=0`, :2043-2044 에서 모든 continue_personas 에 적용), 실 전문가 키는 전원 description 이 있으므로 role 접미 방식은 100% 유실된다. 따라서 personas[].role 접미 방식은 **쓰지 않는다**(러너는 `role:''` 로 보낸다). 대신 다음을 확정 변경으로 둔다.

1. `HWAXAgentServer/deliberation.py` 에 상수 `_RISK_SEAT_CONTRACT = {"_common": "...", "mech": "...", "xd": "...", "sim": "...", "rel": "...", "pcb": "...", "pwr": "...", "rf": "...", "soc": "...", "passive": "...", "mem": "...", "material": "...", "disp": "...", "cam": "...", "sh": "...", "std": "..."}` 를 순수 문자열 리터럴로 둔다(ECAD 6 도메인은 같은 문자열을 키마다 반복해 둔다 — 조회를 단순하게).
2. 삽입 지점 = `deliberation.py` :2044 직후. continue_personas 복원 루프(:2043-2044 `for p in personas: p["role"] = await _restore_role(tools, p["key"], p.get("role") or "")`) 안에서 복원 직후에 다음 3줄을 붙인다 — `if opts.chair_template == "risk-review": dom = _dom_of(p["key"]); if dom in _RISK_SEAT_CONTRACT: p["role"] = (p["role"] or "") + "\n" + _RISK_SEAT_CONTRACT["_common"] + "\n" + _RISK_SEAT_CONTRACT[dom]`. 좌석 시스템 메시지는 `_persona_round`(:889-891)가 `persona.get('role')` 로 만들므로 이 `p["role"]` 이 그대로 sysmsg 에 들어간다(라운드별 `prompt_fn`(:2227·2237·2272·2320)은 사용자 프롬프트이지 시스템 메시지가 아니라 삽입 지점이 아니다). 원본 role 은 `_restore_role` 이 복원한 그대로이고 계약은 **뒤에** 붙으며, `_resolve_opts` 의 role `[:2000]` 클램프(:434)와 `_ROLE_CLIP` 은 그 앞에서 이미 끝났으므로 접미는 잘리지 않는다. 합성 지정석 `delib-baseline-defender` 는 루프 뒤 :2078 에서 append 되므로 미부착이고 `_dom_of`='delib' 라 표에도 없다(자기 역할 문구만). 비-continue 경로(:2063 `_discover` 발굴)에는 접미를 붙이지 않는다 — 러너(§6.7 5단계)와 L2 오케스트레이터(§8.3.4)는 항상 personas 를 보내 continue_personas 경로를 타고, personas 없는 L1 핸드오프 단발은 E0c 보조 경로만 닿는다.
3. `hwax-deliberate.js` 에 `RISK_SEAT_CONTRACT` 를 같은 키·같은 문자열로 두고 chairTemplate==='risk-review' 일 때 좌석 프롬프트에 같은 규칙으로 붙인다.
4. `check_chair_parity.py` 가 앱 리포 `backend/app/assets/seat-contract.v1.json`(`--contract`, §8.3.2)을 직렬화한 문자열과 PY/JS 상수를 바이트 비교한다(원천은 JSON, 상수는 손으로 옮긴 리터럴 — 메타 순수 리터럴 규칙).
5. 보조 경로 = E0c. 러너가 evidence 항목 `{source:'seat_contract', tool:'seat-contract.v1', args:'<이번 패널 착석 도메인>', result:'<그 도메인들의 계약 행(도메인당 ≤200자), 합 ≤1000자 — §5.6.1 예산표>'}` 를 E0 바로 뒤에 싣는다. 대화 기록·RA 보고서에 계약이 보이게 하고 MCP evidence_only 경로(§6.11)에서도 같은 표가 닿게 하는 이중화다.

P0 통과 기준 (7) 은 `_persona_round`(:889-891) 의 sysmsg 덤프(DELIB 디버그 로그 또는 `_llm_text` 입력 캡처)에서 "5/5 좌석의 시스템 프롬프트에 `[리스크 심사 좌석 계약]` 과 `[<dom>]` 줄이 원본 role 뒤에 있음" 을 실측으로 확인한다. SSE `personas` 이벤트(:2089-2091)는 role 을 280자로 잘라 보내므로 접미가 보이지 않는다 — 검증 수단이 아니다.

### 6.5.5 사후 검증(코드, `rr_seat_opinions.quality` · `rr_panels.quality_json`)

좌석별 `tool_calls_n`(시도)·`tool_calls_ok`(성공)·`used_tool`·`cited_refs`·`cited_ir`·`grade_min`·stance 는 §6.7 4단계의 SSE 귀속 규약으로 코드가 뽑는다. 패널 `quality_json = {tool_use_rate, ir_cite_rate, grade_dist{측정, 문헌·규격, 도구예측, 경험칙}, adversary_reject_rate, attribution_rate, new_clusters, llm_calls_observed, pat_degraded, flags[]}`.

| quality.flag | 조건 | 뜻 |
|---|---|---|
| `low_tool_use` | 귀속 가능 좌석(웹 엔진 5석) 중 `used_tool` 비율 < 0.8 | 계약 미이행 경향 |
| `low_ir_cite` | `cited_ir` 비율 < 0.5(name: 해석 포함) | 근거 없는 주장 경향 |
| `adversary_silent` | 반대석 기각 요구(contested 합) = 0 | 지정석 무력 의심 |
| `adversary_overreject` | 기각 요구 finding / 전체 finding > 0.6 | 과잉 경보 의심(정상 밴드 0.1~0.4) |
| `header_mismatch` | 결정문 evidence_profile ≠ seat_opinion 합계(§4) | 헤더 근거 프로파일 불일치 |
| `spec_parse_failed` | `parse_risk_spec` 결과 null | 등록부 병합 불가(§6.9 C2 조건) |
| `over_budget` | `llm_calls_observed` > `risk_panel_llm_cap` | 재실행 없음, 표기만(§6.10) |
| `rescreen_seats` | `extra_seats ≠ ∅` | 불변식 위반(§6.8) |
| `coverage_mismatch` | 결정문 (8) 커버리지 문단의 좌석 집합 ≠ 원장 seats | 경고 수준 |

기준 미달 패널은 실패가 아니라 flag 만 달리고 Tier 마감 통합 보고서 minutes 에 표로 나온다. 패널 품질 목표(§0.6)는 도구 사용률 ≥80%, IR 인용률 ≥50%, 반대석 기각률 10~40%, 귀속 성공률 ≥95% 다.

## 6.6 심의 Job 'risk-review'

### 6.6.1 chair_template 산출 항목(두 엔진 동일 문자열)

PY `_CHAIR_ITEMS["risk-review"]` / JS `CHAIR_ITEMS['risk-review']`, doc_title '리스크 심사 보고서'(PY doc_title dict :2375-2378 1줄, JS :375 삼항 1항목). 문자열은 다음과 바이트 동일해야 한다.

"리스크 심사 보고서 8개 항목 — (1) 심사 대상과 비교 축: 단일 과제 현황인지 기준 과제 대비 변경인지, IR 해시·소스 앱·게이트 상태·결측(ECAD 부재 등)을 그대로 적어라, (2) 변경 원장: [근거] 의 diff 요약을 항목별로 — 이름 있는 치수 delta·의미 변화(kind_changed·재료 교체)·구조 변화(추가/삭제/고아)·Dyna 접촉/재료/결과 delta 를 표로, 수치가 조회되지 않았으면 '조회 못함' 이라 쓰고 지어내지 마라, (3) 도메인별 리스크 판정: 좌석마다 {finding id, 리스크 항목, 영향 경로(계면·파트 실명과 [c:]/[e:]/[p:]/name: 참조), 발현 조건, 심각도 경미/중대/치명과 판정 OK/WARNING/FAIL/undetermined, 탐지 가능성(어떤 도구·시험으로), 근거 등급 [측정]/[문헌·규격]/[도구예측]/[경험칙], 선례 범위 in_range/out_of_range/none, 제기 좌석, 반대석 이의}, (4) 개선되는 점: 변경으로 좋아진 것을 (3)과 같은 형식으로 — 리스크만 나열한 심사는 불합격이다, (5) 과제 성격 서술: 숫자가 아닌 정성적 특징을 facet 8종(설계 의도·제약·이례성·계보·취약 계면·강점·맞교환·미지) 순서로 각 1~2문장, 문장마다 참조와 제기 좌석을 달아 다음 과제가 인용할 수 있게, 해당 없으면 사유를 적어라, (6) 교차 도메인 상호작용: 한 도메인 변경이 다른 도메인에 미치는 2차 리스크와 그 경로, (7) 확인 필요·미지영역: finding 별 resolving_check — 어떤 도구 조회·해석·시험으로 닫히는지, 판정 불가는 그대로 두라, (8) 합의·소수의견·신뢰도: 판정 go/conditional/no-go/undetermined 와 조건, 반대석 기각이 받아들여진 finding 과 살아남은 finding 을 구분, 참여 도메인과 미착석 인접 도메인. 결정문 산문 뒤에 기계판독 규격 risk_spec 을 ```json 펜스 블록에 함께 내라 — {schema:'risk_spec',version:'1.0',taxonomy_version,scope:{kind,target_key,project_refs,ir_refs,diff_ref,ir_hash},findings:[{id,direction,domain,mechanism,mechanism_detail,change_kind,subject:{ckeys,names},trigger_condition,severity,judgement,detectability:{level,tool},evidence_grade,precedent,cites:[{ref,quote}],tool_calls,claim,warrant,resolving_check,owner_domain,raised_by,contested_by,contest_note,status}],gains:[…같은 필드…],cross_domain:[{id,from_domain,to_domain,path,cites,raised_by}],character:{one_liner,facets:[{facet,statements:[{id,text,polarity,by,cites,tags,confidence}],na_reason}]},open_items:[{id,question,resolving_check:{kind,ref},owner_domain}],coverage:{seats,domains_seated,domains_missing},verdict,verdict_conditions,evidence_profile}. 값은 산문 (2)(3)(4)(5)(6)(8)과 일치해야 하고 모르면 빈 문자열로, 참조는 [근거]에 있는 id 나 도구 결과의 이름만 쓰라. 이 규격을 등록부 병합·다음 과제 심사가 재파싱 없이 승계한다."

파서 `parse_risk_spec`(펜스 우선 → 마지막 균형 중괄호 → 실패 null 비치명)은 앱 단일 구현(`narrative.py`)이고 P0 산출물이다(§4). 실패는 패널 `risk_spec_parsed=false`·`quality.flag=spec_parse_failed` 로 남고 LLM 재실행은 하지 않는다.

### 6.6.2 지정 반대석

PY `_CHAIR_ADVERSARY["risk-review"]` / JS `CHAIR_ADVERSARY['risk-review']` — `{key:'delib-baseline-defender', label:'기준선 옹호 지정석', role:'이 심사의 기준선 옹호 지정석(반대석). 변경이 리스크라는 단정을 반증하라 — 그 diff 가 실제 물리 경로(계면·하중·열·전기)로 이어지는지 도구 결과로 따지고, 기준 과제에 이미 있던 리스크를 변경 탓으로 돌리는 것을 막고, 수치·참조 없는 finding 은 [경험칙]으로 강등하거나 기각을 요구하며, 선례가 과거에 기각(dismissed)된 것이면 그 통계를 인용하고, 변경으로 좋아진 점을 같은 형식으로 대변하라. 과잉 경보가 이 심사의 거수기다.'}`. origin `adversary` 로 합성 push(:2076-2079 방식), 원장 미집계, 지식카드 hits 없음(비치명). 기각 요구는 §4 등록부 병합에서 `contested` 로 계수되어 C2 조건과 `adversary_false_reject` 지표(§7)에 쓰인다.

### 6.6.3 modifiers 기본값과 evidence 채널

- modifiers 기본 `['toulmin']`(주장에 claim·warrant 강제 — risk_spec 의 `claim/warrant` 필드와 대응). 잡 옵션 `modifiers?` 가 오면 화이트리스트 5종 안에서 합집합으로 싣고 `toulmin` 은 항상 남긴다. Tier A 잡은 UI 가 `premortem` 을 기본 체크 상태로 제안한다. `voi`·`eliminative`·`anon1r` 은 사용자 선택.
- evidence(≤12항목·result ≤2000자·라인 합 ≤11000자 — 라인 = `· [source · tool(args)] result`, 초과 항목 통째 드롭 :2158-2173, 앱 예산표는 라인 기준 합 10600 §5.6.1)는 `narrative.prior_evidence(target)` 가 §5 예산표대로 조립한다. 순서 고정 — E0(스코프·게이트·소스 id) · E0c(좌석 계약표) · E1(summary_text 또는 rr_state 요약) · E2(의미·구조 변화 표) · E3(dims_named delta) · E4(결과 delta) · E5(계보 등록부) · E6(유사 과제 성격 진술) · E7(좌석 5명 이전 발췌 고정 슬롯) · E8(delta 선례 수치) · E9(warnings·rule_hits) = 11항목, 12번째 슬롯은 잡의 `user_memo`(있을 때, `{source:'user_memo', tool:'note', result:<원문 ≤2000자>}`). 헌법 P1 — 전부 원천·수치·원문 발췌이고 결론 문장이 없다(render.py 판단어 린터 통과가 조립 조건).
- 지정 도구 결과(tool_inject)와 evidence 는 좌석 공용이라 어느 좌석의 `used_tool` 에도 계수하지 않는다.

### 6.6.4 패널 1건의 delib_opts(앱 러너 조립) `[gap 수정 — role 접미·human_note 제거]`

```json
{"chair_template":"risk-review","modifiers":["toulmin"],"rounds":3,"free_tools":1,"tool_budget":3,
 "personas":[{"key":"mech-housing-structure","role":"","origin":"primary"},
             {"key":"sim-drop-impact","role":"","origin":"primary"},
             {"key":"rel-thermal-cycle","role":"","origin":"primary"},
             {"key":"xd-mech-assembly","role":"","origin":"primary"},
             {"key":"pcb-stackup","role":"","origin":"counter"}],
 "tools":["list_interfaces","interface_graph","report_part_risk","compare_reports"],
 "apps":["heax-step_forge","heax-kooremapper_mcp"],
 "evidence":[{"source":"rr_state","tool":"gates","args":"diff:7f3e…","result":"…"},
             {"source":"seat_contract","tool":"seat-contract.v1","args":"mech,sim,rel,xd,pcb","result":"…"},
             {"source":"rr_diff","tool":"summary_text","args":"diff:7f3e…","result":"…"},
             "…≤12"]}
```

러너가 **절대 싣지 않는 키** — `human_note`, `continue_summary`, `non_negotiables`, `search_sources`, `stop_after_round`, `build_plan`. 앞 둘은 `_RESCREEN`(:2050-2061)의 재심 신규석 2석 추가를 발동시키고, `search_sources` 는 `rebut_quote` 를 켜 `parse_retries` 하한 2 를 만든다(:470-480). 이 부재가 불변식 `extra_seats == ∅` 와 §6.10 예산의 전제다. 사용자 메모는 evidence 12번째 슬롯으로만 간다.

질문 문자열 = "[리스크심사 {과제코드} {target_key}] 기준 {base 과제코드} 대비 변경(또는 현황)이 각 도메인에서 어떤 리스크와 개선을 낳는가를 도구 근거로 판정하라. 소스 stepforge project_id={target project_id}(base {base project_id}) dynaforge session_id={…} file_id={…} report_ids=[{…}]. diff 요약 첫 줄: {summary_text 200자}". 과제코드·요약 앞부분이 question 에 있어야 좌석 `agent_search(q=question)` 이 과제 문맥을 갖는다. 트리거는 기존 `/심의 ` 이고 chair_template 으로 라우팅한다(app.py 분기 변경 0, delibTaxonomy `JOB_ROUTING['risk-review']={trigger:'/심의 ', chair:'risk-review'}`). 포털 `routes.py` DelibOpts 는 personas 항목에 `origin: Literal['primary','counter']|None` 을, `_resolve_opts` 는 personas 매핑(:434-435 `o.continue_personas = [{"key": …, "role": …}]` — 이 줄이 origin 을 버린다)에 origin 통과 1줄을 추가한다(없으면 조용히 유실 — method-menu 선례).

## 6.7 실행 시퀀스(`runner.py`, 백그라운드 스레드, 세마포어 `risk_concurrency`)

러너는 hwax_risk 앱 프로세스 안의 데몬 스레드다(앱 `backend/app/runner.py`, `main.py` lifespan 의 `start()`/`stop()`, 포털 프로세스에는 러너가 없다 — B 결정 §0.7 #12). 심의 엔진(agent-server `deliberation.py`)을 부르는 경로는 §6.7.1 후보 비교로 (A) 를 확정하고, §6.7.2 가 패널 1건의 12단계를 적는다.

### 6.7.1 엔진 호출 경로 — 후보 비교·확정·함의·폴백

| 후보 | 호출 형태 | 인증·신원 | 좌석 도구 스코핑(`X-HWAX-Groups`) | conv_store·포털 감사·세마포어 | DynaForge 사용자 세션 | 가용 조건 | 판정 |
|---|---|---|---|---|---|---|---|
| (A) 앱 → 포털 `POST {HWAXRISK_PORTAL_BASE}/agent/chat` | `Authorization: Bearer <포털 PAT>`(aud `mcp-gateway`, scope api), CSRF 불요, 응답 SSE | 포털이 PAT 의 sub·email·groups 를 신원으로 채우고 본문 신원은 무시한다(`principal_pat_or_session`, deps.py:74). 포털이 그 주체로 30분 창 단명 `user_pat` 를 찍어 agent-server 에 실어 준다(`_chat_user_pat`, routes.py:158 — 앱이 부를 수 없는 릴레이 내부 함수) | PAT 의 groups 로 강제(자칭 불가) | conv_store 저장(`conversation_id` 지정 시, owner = PAT sub)·감사로그·`agent_semaphore`(초과 429) 전부 동반 | PAT email 로 `per_user_sso.kooremapper_mcp` 발동 — 러너 자격 (b) 면 사용자 세션, (a) 면 서비스 시야(0건) | 포털 nginx 오리진에 닿는 어느 박스(SIF 안도 호스트 네트워크라 `127.0.0.1:5283` 도달) | **확정(기본)** |
| (B) 앱 → agent-server `POST {HWAXRISK_AGENT_URL}/chat`(기본 `http://127.0.0.1:9009`) | 무인증(루프백), 본문 `{message, groups[], user_email, user_pat:'', history, delib_opts}` | 앱이 groups·user_email 을 자칭한다 — 검증 주체 없음 | 본문 groups 가 그대로 실린다 | 없음 — conv_store 저장 0·포털 감사 0, `save_conversation` 은 CONV_UNAVAILABLE | `user_email` 로 발동은 되나 `user_pat` 없이는 게이트웨이 GW_TOKEN 서비스 신원 | agent-server 와 같은 박스 | **폴백** — (A) 가 연결 불가일 때만(§6.7.1 폴백 규칙) |
| (C) 앱 → 게이트웨이 MCP 워크플로 `hwax-deliberate.js` | Claude Code Workflow 스크립트 | — | — | — | — | 서버 코드가 부를 API 가 아니다(워크플로는 LLM 에게 도구 호출을 지시하는 스크립트) | **제외** — L1/L2 는 사람이 Claude Code 에서 돌리는 경로(§6.11) |
| (D) 포털 백엔드가 앱 대신 엔진을 부르는 서버측 프록시 | 포털에 리스크 라우트·heax 시크릿 추가 | 신원이 서비스 계정으로 뭉개진다 | — | — | — | 포털 백엔드 코드 변경 필요 | **기각** — 포털은 창만 둔다(§0.7 #12) |

선택 근거. (1) (A) 만이 포털 감사로그·세마포어·conv_store 저장·단명 `user_pat` 부착을 포털 코드 0줄로 얻는다 — 러너는 `/agent/chat` 계약(§0.1.6 delib_opts)만 지키면 된다. (2) 좌석 도구 스코핑이 '앱이 자칭한 그룹' 이 아니라 '포털이 검증한 PAT 의 groups' 로 강제되어 읽기 전용·스코프 원칙이 포털 한 곳에서 집행된다. (3) 대리 발급은 없다 — 포털에 타인 명의 PAT 발급 API 가 없고 `_chat_user_pat` 는 릴레이 내부 전용이므로 러너 자격은 §0.1.6 의 (a) 서비스 계정 PAT `HWAXRISK_PORTAL_PAT` · (b) 타깃 owner 가 `PUT /api/me/portal-pat` 로 등록한 자기 PAT 두 가지뿐이다. (4) (B) 는 같은 박스에서만 성립하고 포털 저장·감사가 빠지므로 정본 경로가 될 수 없다.

함의(확정).
- **좌석 도구 스코핑** — 패널의 자유조회 목록은 호출 PAT 의 groups ∩ 백엔드 `allowed_groups` 다. (a) 서비스 PAT 의 groups 는 발급 시점에 굳으므로 서비스 계정은 소스 앱(`heax-step_forge`·`heax-kooremapper_mcp`)과 RA·AIDataHub 백엔드가 요구하는 그룹을 전부 가진 계정으로 발급한다(§10). 러너는 호출에 쓴 PAT 의 groups 를 `rr_panels.quality_json.call_groups[]` 에 적어 `low_tool_use` 원인 분석에 쓴다(DDL 무변경, JSON 키 추가).
- **DynaForge 사용자 세션** — `per_user_sso.kooremapper_mcp` 는 PAT email 로 발동한다. (b) 가 있는 타깃의 패널은 dyna 도구가 그 사용자의 세션을 보고, (a) 만 있으면 `list_sessions` 0건이 정상이라 어댑터가 `missing.dyna_absent` 를 남기고 패널 `quality.pat_degraded=true` 다. 러너는 패널 시작 시 (b) 유무를 정해 `quality_json.credential ∈ service|owner` 로 남긴다.
- **결정문 저장 위치** — ① RA 보고서: 어느 경로든 엔진이 게이트웨이 서비스 `rat_` 로 `create_report_draft(template 'deliberation')` 를 만들므로 RA 소유자는 서비스 계정이고 앱은 `update_report_draft` 로 tags 만 병합한다(§5.3.5). ② conv_store: (A) 에서만 저장되고 owner = 호출 PAT 의 sub — (a) 면 서비스 계정 소유, (b) 면 사용자 소유다. `rr_panels.conv_id` 에 id 를 적고 `tool:conv:<conv_id>#<idx>` 참조(§0.2.1)는 러너가 같은 PAT 로 `GET {HWAXRISK_PORTAL_BASE}/agent/conversations/{cid}` 를 읽어 해석한다(포털 `/deliberate` 목록은 `serverKind='deliberation'` 필터라 이 대화를 0건 노출한다). ③ 앱 DB: 정본. SSE 를 파싱해 `rr_seat_opinions.turns · rr_findings · rr_panels.decision_text/risk_spec_json` 에 넣고 앱 화면(TargetPage 패널 기록)은 앱 DB 만 그린다 — RA·conv_store 는 부산물이며 앱 화면은 포털 conv_store 를 읽지 않는다.
- **폴백 (B) 규칙** — `HWAXRISK_AGENT_URL` 이 비어 있으면 폴백은 꺼져 있다(기본). 켜진 박스에서 (A) 가 연결 오류(ConnectError·타임아웃 30 s)를 3회 연속 내면 그 패널만 (B) 로 돌린다 — 401/403 은 자격 문제라 폴백하지 않고 `rr_jobs.error='pat_unavailable'` 로 잡을 멈춘다. (B) 본문의 `groups` 는 서비스 PAT 클레임에서 복사하고 `user_pat` 는 빈 문자열, `user_email` 은 (b) 가 있을 때만 싣는다. 기록은 `quality_json.call_path='agent_direct'`(정본 경로는 `'portal'`), `conv_id=null`, 진행판 `direct` 배지이며 원장 계수는 (A) 와 같다.

### 6.7.2 패널 1건의 12단계

1. **잡 선택·패널 잠금** — `rr_jobs.state ∈ {queued, running}` 잡을 집고(같은 타깃에 `running` 패널이 있으면 건너뜀 → 타깃당 직렬), 일일 상한을 검사한 뒤 `planner.plan_next_panel` 로 다음 패널을 만든다. `rr_panels.status='running'`, 좌석 `rr_coverage.status='running'`, `started_at`. 러너 자격이 (a)(b) 어느 쪽도 없으면(§5.2.5 (5) `origin.json.hostname` 불일치로 `secrets.env` 무효인 경우 포함) 잡을 집지 않고 `rr_jobs.error='pat_unavailable'` 만 갱신한다(상태는 그대로, 자격이 생기면 다음 주기에 집는다). 패널 시작 직전에 agent-server `GET {HWAXRISK_AGENT_URL 이 있으면 그 값, 없으면 http://127.0.0.1:9009}/health`(읽기 전용, 타임아웃 2 s — 폴백 (B) 의 활성화와 무관)의 `model`·`vllm` 을 읽어 `rr_panels.model_json = {runtime:'agent-server', provider:'vllm', model, endpoint_host: <vllm base_url 의 호스트>, captured:'health_snapshot', engine_rev: <응답에 engine_rev 또는 version 이 있으면 그 값, 없으면 null>, chair_rev: <_CHAIR_ITEMS['risk-review'] 텍스트 sha256[:12]>, seat_contract_rev: <seat-contract.v1.json sha256[:12]>}` 에 적는다(D6). `/health` 불통이면 `{captured:'unavailable', model:'unknown'}` 이고 패널은 그대로 진행한다.
2. **사전 예산 산정** `[gap 수정 — 사후 재실행 폐기]` — §6.10 식으로 `budget_json{est_low, est_high, cap, rounds_planned}` 를 계산하고 `est_high > risk_panel_llm_cap` 이면 `rounds_planned=2` 로 편성한다. 기본 구성(6석·3R·tools 4)에서는 발동하지 않는다.
3. **러너 자격 결정**(§0.1.6) — `rr_targets.owner_sub` 의 `_user_credentials` 행(§8.2.3 `PUT /api/me/portal-pat`)이 있고 `pat_exp > now + timeout_s` 면 (b) 그 PAT, 아니면 (a) `HWAXRISK_PORTAL_PAT`. 결과를 `quality_json.credential` 에 적는다. 대리 발급·브라우저 세션 모드는 없다.
4. **대화 생성** — `POST {HWAXRISK_PORTAL_BASE}/agent/conversations {kind:'risk-review', title:'[리스크심사] {과제} P{n}'}` 를 3단계 PAT Bearer 로 만든다(conv_store 스키마 무수정, kind 값 추가만, owner = PAT sub). 4xx·연결 실패면 대화 없이 진행하고 `rr_panels.conv_id=null`(비치명).
5. **delib_opts 조립** — §6.6.4. personas 는 seats_json 순서대로 `role:''`, tools·apps 는 타깃 kind 와 소스 존재 여부로, evidence 는 `prior_evidence` 결과 + E0c + user_memo.
6. **엔진 호출** — 경로 (A) `POST {HWAXRISK_PORTAL_BASE}/agent/chat` 본문 `{message, conversation_id, history: [], delib_opts}`, 헤더 `Authorization: Bearer <3단계 PAT>` · `Accept: text/event-stream`, httpx 스트림(읽기 타임아웃 `timeout_s + 60`, nginx `/agent/` 는 `proxy_buffering off`·1 h). 429(세마포어 초과)는 error 가 아니라 30 s 대기 후 재시도(패널 카운트 무증가, §0.6). 포털 `agent_semaphore`·conv_store 저장·turns[:60]·activity[:60] 캡을 기존 코드 그대로 통과하며 배치 점유 슬롯은 `risk_concurrency`(2) 이하다. 연결 오류 3회면 §6.7.1 폴백 규칙.
7. **SSE 캡처(스키마 변경 없음)** `[gap 수정 — status.persona 필드 부재]` — status 이벤트 스키마는 `{step, tool, detail?, personas?, tools_used?}` 이고 좌석 키는 문자열에만 실린다(:2304-2308). 러너는 다음 규약으로 좌석을 귀속한다. 같은 정규식을 `narrative.extract_seat_opinion` 이 `POST /api/panels/{id}/complete` 의 `events[]`(L2 오케스트레이터·재제출이 실어 보내는 압축 로그 `{kind: status|evidence|personas, step?, tool?, source?, personas?}`, ≤400건)에도 똑같이 적용한다(입력 소스만 다르다, §8.2.3).

| 이벤트 | 파싱 | 러너가 쓰는 곳 |
|---|---|---|
| `personas{personas[{key, origin}]}` | 키 집합 P | `P − (seats ∪ {'delib-baseline-defender'})` 가 `extra_seats`; ≠∅ 이면 `quality.flag=rescreen_seats` |
| `turn{round, persona, say, position?, stance?, non_negotiable?}` | persona ∈ seats | `seat_opinion.turns[]`(say_excerpt ≤2000자), `cited_refs` 정규식 추출(§4) |
| `status{step, tool}` | `step` 이 정규식 `^(?P<key>\S+) 조회: (?P<tool>\S+)$` 에 맞고 key ∈ seats | 좌석 **시도** 호출 `tool_calls_n += 1`, `tool_calls[].{tool, activity_idx}` |
| `evidence{source, text, included}` | `source` 를 `' · '` 로 분리한 앞부분이 key ∈ seats | 좌석 **성공** 호출 `tool_calls_ok += 1`, `result_preview`(≤2000자); `used_tool = tool_calls_ok ≥ 1` |
| `evidence`(source 가 좌석 키가 아님) | E0~E9·지정 도구 주입 | 좌석 귀속 없음(공용) |
| `decision{text}` | 산문 + 펜스 | `parse_risk_spec` |
| `outcome{report_id, tally}` | | `rr_panels.report_id`, external_sync.ra 대상 |
| `warning`(`_pat_degraded`) · `error` | | `quality.pat_degraded` / 패널 `error` |

빈 결과 호출은 status 만 나오고 evidence 는 안 나오므로 `tool_calls_n ≥ tool_calls_ok` 가 항상 성립한다. 지정 도구(`delib_opts.tools`) 결과는 좌석 귀속 불가라 어느 카운트에도 넣지 않는다. 귀속 성공률 = (좌석 키로 해석된 status+evidence 수)/(좌석 조회 형식으로 보이는 전체 수) 를 `quality.attribution_rate` 에 남기고 P3 통과 기준은 픽스처 스트림 ≥0.95 다. 정규식이 깨지면 `used_tool` 이 전부 false 로 떨어져 `done_weak` 가 급증하므로 `low_tool_use` 와 `attribution_rate < 0.95` 가 동시에 뜨면 화면이 "귀속 파서 점검" 을 표시한다. 스트림이 `done`(또는 `error`)으로 닫힌 직후 1단계와 같은 `GET /health` 를 다시 읽어 `model` 또는 `vllm` 이 시작 스냅샷과 다르면 `quality.flag=model_changed_midrun` 을 세우고 종료값을 `model_json.model_end` 에 남긴다(D6 — 시작값이 정본, 재실행 없음. 1단계가 `unavailable` 이었으면 비교하지 않는다).

8. **파싱·추출** — `parse_risk_spec(decision.text)` → `rr_findings`(finding·gain, cites 해석·dangling·feature_snapshot·evidence_grade·precedent 부여는 §4) · `rr_character(status='panel')` · `rr_seat_opinions`(좌석 5 + adversary 1, adversary 는 원장 미집계지만 의견은 저장, `owner_sub` 는 `rr_panels.owner_sub` 승계) · `rr_claim_refs`. 파싱 실패면 findings 없이 좌석 의견만 저장한다. 전부 앱 DB `risk_review.db` 이며 포털 저장소에는 쓰지 않는다.
9. **커버리지 갱신** — 좌석마다 §6.8 규칙으로 `done | done_weak | abstain | failed` 를 기록하고 `opinion_id` 를 잇는다. 패널 `error`(엔진 error 이벤트·타임아웃 40분·연결 끊김)면 좌석 5석 전부 `pending(retry+1)`, `retry > 2` 면 `skipped(reason=engine_fail)`, 패널 행은 `status='error'` 로 남긴다.
10. **등록부 병합** — §4 규칙으로 `rr_registry` 갱신(cluster_key 병합·support·contested), `rr_delta_contrib` UPSERT 후 `rr_delta_priors` 재합산(§4.7.1, 멱등), 신규 클러스터 수를 `quality.new_clusters` 에 기록(수확 체감 판정 입력).
11. **외부 반영(비치명·재시도 큐, 앱 발신)** — RA 는 게이트웨이 MCP(`HWAXRISK_GATEWAY_MCP`, `Authorization: Bearer <HWAXRISK_PORTAL_PAT>` — (b) 패널이라도 KG 쓰기는 항상 서비스 PAT, §5.3.5)로 `update_report_draft` tags 병합(`['심의','chat-deliberation','risk-review','hwax:target:<key>','hwax:panel:<no>']`, `get_report` 후 병합)과 assessment/risk_finding/exhibits `create_object`+`link_objects` 를 보내고, AIDataHub 는 앱 `adh_client.py` 가 REST `POST {HWAXRISK_AIDH_BASE}/api/records/import?external_source=hwax-risk`(`X-API-Key: <HWAXRISK_AIDH_API_KEY>`, opinion·panel `_external_id` UPSERT, §5.4.2)로 보낸다. 관리자 PAT·RA `rat_` 토큰은 앱 런타임에 없다. 결과는 `rr_targets.external_sync_json{ra, adh}`(§5.5.3 상태기계, 재시도는 러너 후처리 스레드)로만 표기하고 완결 판정(§6.9)에는 넣지 않는다.
12. **완결 판정·다음 패널** — §6.9 레벨 계산 → 상승 시 통합 보고서 새 버전. 수확 체감·일일 상한·취소(`cancelling` → 이 패널 종료 후 `cancelled`)·일시정지는 여기 패널 경계에서만 반영한다. 다음 패널이 없으면 잡 `completed`.

재기동 복구. `stop()`(SIF 재빌드·`redeploy-app.sh hwax-risk`·HEAX 인스턴스 정지)은 실행 중 패널을 기다리지 않고 스트림을 닫는다. 다음 `start()` 는 `rr_panels.status='running'` 을 `error(retry+1)` 로, 그 5석을 `pending` 으로 되돌린 뒤 `rr_jobs.state ∈ {queued, running}` 을 다시 집는다(포털 쪽 conv_store 대화는 그대로 남고 `conv_id` 로만 연결된다). 두 박스가 같은 타깃의 패널을 동시에 돌리지 않는 규칙은 §5.2.5 (7) ⑥ 이다.

## 6.8 커버리지 회계 상태기계('한번 하면 넘어감')

### 6.8.1 원장 행과 제약

`rr_coverage{target_key, agent_key, domain, origin(primary|counter|NULL), status, panel_id, cycle INT DEFAULT 1, retry INT DEFAULT 0, opinion_id, adh_record_id, ra_assessment_id, carried_from_opinion_id, reason, started_at, finished_at, owner_sub, PRIMARY KEY(target_key, agent_key)}`. coverage_key 문자열 `<target_key>:<agent_key>` 는 RA assessment.coverage_key 와 AIDataHub external_id 에 쓴다.

부분 유니크 인덱스 `CREATE UNIQUE INDEX rr_cov_active ON rr_coverage(agent_key, target_key) WHERE status IN ('assigned','running')`. PK 와 열이 겹치지만 활성 행만 담는 작은 인덱스라 편성기의 rowcount 선점 UPDATE 와 불변식 검사가 전체 표를 훑지 않는다. 다른 타깃 동시 착석은 막지 않는다(Tier A 는 두 타깃이 같은 대표 15명을 원하므로 막으면 편성이 바뀐다). 정책을 "전문가 전역 동시 1석" 으로 바꾸려면 이 인덱스 열을 `(agent_key)` 로 줄이는 마이그레이션 1건이다(Settings 아님).

### 6.8.2 상태와 전이

```
            planner                runner                       runner/capture
pending ──────────► assigned ─────────────► running ───┬──► done       (turn≥1 & decision & (used_tool | cited_refs≠∅))
   ▲                  │ 편성 롤백(rowcount≠좌석수)  │           ├──► done_weak  (turn≥1 & decision & used_tool=false & cited_refs=∅)
   │                  ▼                        │ 패널 error  ├──► abstain    (final_stance=abstain 또는 '판정 불가' 발언)
   └────────────── pending(retry+1) ◄──────────┘           └──► failed     (turn=0) ─ retry≤2 → pending(retry+1) / retry>2 → skipped(reason=no_turn)
                                                  패널 error: retry>2 → skipped(reason=engine_fail)
사용자: 비종결(pending|assigned|running|failed) → skipped(reason 필수)   /   carried → pending(cycle+1) 되돌리기
로스터 생성: ECAD 의존 도메인 & ecad_absent & rank_in_domain≠1 → deferred(reason=ecad_absent)
새 타깃(같은 과제·새 스냅샷/diff): 이전 타깃 done & cited_refs≠∅ & used_tool & (cited ckey ∩ 변경 ckey)=∅ & finished_at ≥ now−risk_carried_days → carried(carried_from_opinion_id), 아니면 pending(cycle+1)
```

- 종결 상태 = `done | done_weak | abstain | skipped | deferred | carried`. 비종결 = `pending | assigned | running | failed`.
- `done` 대 `done_weak` 분기는 좌석 귀속(§6.7 7단계)의 `used_tool` 또는 `cited_refs≠∅` 다. MCP `evidence_only` 패널은 `tool_calls_n=null` 이므로 `cited_refs≠∅` 이면 `done`, 아니면 `done_weak` 이고 C2 strong 비율에서는 제외한다(§6.11). 웹 폴백 패널(§8.2.4)에서 `events[]` 없이 완료돼 `used_tool=null` 인 좌석도 같은 규칙이다 — `cited_refs≠∅` 이면 `done`, 아니면 `done_weak`, strong 비율 분모·분자 제외(§6.11).
- `abstain` 은 좌석 최종 stance 가 `abstain` 이거나 최종 라운드 발언이 '판정 불가' 로 시작할 때. 헌법 F6 이 허용하는 정당한 종결이고 C1 계수에 들어간다.
- `deferred` 는 타깃 안에서 바뀌지 않는다(사용자가 되돌릴 수도 없다). ECAD 스냅샷이 생기면 새 타깃에서 `pending` 으로 재생성된다.
- `carried` 판정의 "변경 ckey" 는 이전 타깃 스냅샷 → 새 타깃 스냅샷의 diff(있으면 rr_diff, 없으면 `diff.py` 를 저장 없이 실행)에서 `node_changes·edge_changes·dims_delta` 에 걸린 ckey 집합이다. `cited_refs` 의 `[p:]`→그 노드 ckey, `[e:]`·`name:A|B`→양끝 ckey, `[c:]`→그 cid 의 ckey, `[d:name]`→dims_delta 에 name 이 있으면 교집합으로 본다. 교집합 판정은 canonical_part_key 기준이라 재파싱으로 nid 가 바뀌어도 성립한다. `done_weak`·`abstain` 은 carried 대상이 아니다. 사용자는 TargetPage 에서 carried 를 `pending(cycle+1)` 으로 되돌릴 수 있고 리비전마다 전원 재심을 원하면 Settings `risk_carried_days=0` 으로 끈다.
- `stale` 은 상태가 아니라 타깃 속성이다. 스냅샷은 불변이므로 IR 이 바뀌면 새 타깃이 생기고 옛 타깃은 `rr_targets.superseded_by` 로 닫힌다. 옛 타깃의 원장 행은 그대로 남아 계보·E7 의 원천이 된다.
- PK 로 같은 전문가는 같은 타깃에 두 번 앉지 않는다. 같은 타깃에서 `cycle` 이 오르는 경우는 carried 되돌리기뿐이고 그때도 행은 하나다(이전 opinion_id 는 `carried_from_opinion_id` 에 남는다).

### 6.8.3 회계 불변식(`backend/tests/test_coverage_sm.py`) `[gap 수정 — extra_seats 정의 강화]`

1. 상태별 카운트 합 = `roster_size`.
2. `running` 좌석 수 ≤ 5 × `running` 패널 수, 타깃당 `running` 패널 ≤ 1.
3. `done | done_weak | abstain` 좌석은 `opinion_id` 를 보유하고, `carried` 는 `carried_from_opinion_id` 를 보유한다.
4. 패널 `personas` SSE 이벤트의 좌석 키 집합 == `seats(로스터 5) ∪ {'delib-baseline-defender'}` **이고 `extra_seats == ∅`**. 러너가 `human_note`·`continue_summary` 를 싣지 않으므로 `_RESCREEN` 경로가 발동하지 않는 것이 보장 조건이며, 위반은 `quality.flag=rescreen_seats` 로 기록하되 패널 결과는 버리지 않는다(추가 좌석의 발언은 원장 미집계, 의견은 `origin='new'` 로 저장).
5. `seats_json` 의 좌석은 전부 `rr_roster` 에 존재한다(로스터 외 편성 0).
6. 결정문 (8) 커버리지 문단의 좌석 집합과 원장 seats 의 대조는 경고 수준(`coverage_mismatch`)이다.
7. 편성 결정론 — 같은 원장 상태·Settings 로 `plan_next_panel` 2회 → 같은 seats_json. 동시 편성 2스레드 → 같은 전문가 이중 `assigned` 0(rowcount 롤백).

## 6.9 완결 판정(코드 계산, `registry.close_level(target)`)

**요구 대비 편차.** 사용자 요구는 "전체 HW/XD 전문가가 한 번씩" 이며 그 문자적 충족은 **C3** 다. C2 는 비용(§6.10, C3 ≈12~21 GPU-h/타깃)에 대한 타협이지 요구의 충족이 아니다. 기본 마감 레벨은 Settings `risk_default_close_level`(`C2|C3`, 기본 `C2`)이고 타깃 생성 시 `close_level` 로 덮어쓸 수 있다. 어느 설정에서든 C3 전까지 TargetPage 진행판은 **'미착석 N명(C3 미달)'** 배지(N = 비종결 좌석 수)를 상시 표시해 '한 번씩' 이 끝나지 않았음이 숨지 않게 한다. `[gap 수정]`

| 레벨 | 조건 | 산출 |
|---|---|---|
| C0 | 종결 좌석 0 | — |
| C1 대표 완료 | 15 도메인 모두 종결 상태(§6.8.2 — `done \| done_weak \| abstain \| skipped \| deferred \| carried`) ≥1 AND Tier A 패널 3개 `done` | 통합 보고서 v1. RA 반영은 조건이 아니라 `external_sync.ra` 표기 `[gap 수정 — RA 미가용이면 C1 영구 미달이던 모순]` |
| C2 심층 완료 | deferred 아닌 도메인별 종결 ≥ max(3, ceil(0.3·\|d\|))(\|d\|<3 이면 전원) AND strong 비율 done/(done+done_weak) ≥ 0.7(웹 엔진 좌석만, MCP evidence_only 제외) AND 반대석 기각 finding 이 등록부에 `contested` 표기 완료 AND 미해결 `spec_parse_failed` 패널 0 | 통합 보고서 v2. 기본 설정이면 `level='C2(closed)'`, 잡 `completed` |
| C3 전원 완료 | deferred 아닌 로스터 전원 종결 AND `skipped` ≤ 5% AND `failed` 0 | 통합 보고서 v3, `level='C3'` |
| 최종 verdict | 사람이 `PUT /api/targets/{key}/verdict {verdict, note}` 로 `verdict_final` 확정(등록부 집계는 후보, 자동 승인 없음) | RA assessment.verdict 갱신(external_sync) |

- `spec_parse_failed` 해결 = 사용자가 decision 텍스트를 보정해 `POST /api/panels/{id}/complete` 로 재제출(파서만 재실행, LLM 재실행 아님) 또는 '제외' 표기(그 패널 좌석은 `done_weak` 로 강등). 재실행으로 C2 를 뚫지 않는다.
- `risk_default_close_level='C2'` — Tier B 잡이 끝나고 C2 가 충족되면 `C2(closed)` 로 마감하고 미착석 도메인·미소진 인원을 통합 보고서 minutes 에 기록한다. Tier C 는 `POST /api/targets/{key}/jobs {tier:'C', consent:true}` 명시 승인으로만 시작한다.
- `risk_default_close_level='C3'` — Tier B 완료 후 코드가 Tier C 잡을 자동 `queued` 하고(승인 재요청 없음, 타깃 생성 동의에 비용 표가 있었다) C3 에서만 마감한다. 수확 체감 정지는 이 설정에서도 발동하지만(비용 가드) 재개는 Tier C 를 잇는다.
- 레벨은 단조 증가만 한다. 새 스냅샷으로 타깃이 superseded 되면 새 타깃은 C0 에서 시작하고 carried 가 즉시 계수된다.

통합 보고서 버전 — v1(C1)·v2(C2)·v3(C3)은 코드가 RA `deliberation` 템플릿(블록 구성은 §4·§8)으로 `create_report_draft` 하고 이후 버전은 `update_report_draft` 페이지 추가로 잇는다. tags `['리스크심사','consolidated','hwax:target:<key>','hwax:project:<id>','verdict:<v>']`. 근거 등급이 전부 경험칙이면 제목 접두 `[가설 단계]`. RA 미가용이면 `external_sync.ra=unavailable` 로 두고 앱 TargetPage 가 같은 내용을 렌더한다(레벨은 이미 올라 있다).

## 6.10 비용·라운드 예산(로컬 vLLM GLM, GPU 시간 추정)

### 6.10.1 패널당 호출 구조 `[gap 수정 — toulmin 재시도 줄 삭제]`

| 항목 | 패널당(6석·3R) | 비고 |
|---|---|---|
| 좌석 발언 | 18회(+파싱 재시도 ≤18) | `parse_retries=1`. 하한 2 는 `rebut_quote` 조건이고 `rebut_quote` 는 `search_sources` 가 있을 때만 켜지는데(:470-480) 러너는 `search_sources` 를 싣지 않는다. toulmin 은 재시도와 무관하다 |
| 자유조회 ReAct | 6석×2R = 12 invoke × LLM 2~4턴 = 24~48회, 도구 실호출 ≤36(캐시 공유 실측 ≈15~20, 추정) | `tool_budget` 3, 수렴 라운드 제외 |
| 지정 도구 | 4도구 × 1~2 = 4~8회 | self-repair 포함 |
| 반대 도메인 축 명명 | 0 | continue_personas 경로라 `_counter_seats` 를 건너뜀 |
| 의장·핵심요약·쉬운설명 | 3회 | `chair_bestof` 0 |
| 지식카드·전문가 기억 | LLM 0(검색만) | `agent_search` 6~12회 |
| 합계 | ≈50~95 LLM 호출, 벽시계 ≈10~18분 | 좌석 병렬·라운드 직렬, 호출당 8~12s 가정 |

| 규모 | ECAD 있음 | ECAD 부재 | 실행 시점 |
|---|---|---|---|
| Tier A(3패널) | ≈150~285회, ≈30~55분 | 같음 | 즉시 |
| Tier B | +20패널 ≈1,000~1,900회, ≈3.5~6h | +14패널 ≈700~1,330회, ≈2.5~4.5h | 야간 큐 |
| Tier C | +48패널 ≈2,400~4,560회, ≈8~15h | +33패널 ≈1,650~3,135회, ≈5.5~10h | 명시 승인(C2 기본) 또는 자동(C3 기본), 주말/야간 |
| 타깃 C3 합계 | ≈3,550~6,750회, ≈12~21h | ≈2,500~4,750회, ≈8.5~15h | 직렬 기준 |

프롬프트 상한 — evidence 라인 합 ≤10600자(엔진 예산 11000, §5.6.1 예산표·오버헤드 규칙), 지식카드 3500자/석, 자유조회 블록 3500자/석, tool_inject 5000자, role ≤2000자(+계약 접미 ≤900자는 :2044 직후 `p["role"]` 에 붙어 `_resolve_opts` 의 `[:2000]` 클램프(:434)와 `_ROLE_CLIP` 뒤이므로 클램프 밖, §6.5.4). 저장 상한 — turns 60/대화(18 발언이라 여유), activity 60, RA rich_text 1900자 분할.

### 6.10.2 사전 예산 게이트와 사후 표기 `[gap 수정 — 120 초과 재실행 폐기]`

- 사전 산정(결정론, 편성 시) — `S`=좌석 수(adversary 포함 6), `R`=rounds, `T`=지정 도구 수. `est_low = S·R + S·(R−1)·2 + T + 3`, `est_high = S·R·2 + S·(R−1)·4 + 2T + 3`. 기본 구성 `est_low=49`, `est_high=95`. `est_high > risk_panel_llm_cap(120)` 이면 `rounds_planned=2` 로 편성(재계산 `est_high=59`), 그래도 초과면 tools 를 `['list_interfaces','interface_graph']` 2개로 줄인다. 결과는 `rr_panels.budget_json{S, R, T, est_low, est_high, cap, rounds_planned, tools_planned}` 에 남는다. 기본 구성에서는 발동하지 않으며 cap 을 낮추거나 tools 6개를 쓸 때만 작동한다.
- 사후 표기 — 정확한 LLM 호출 수는 agent-server 로그에만 있으므로 러너는 SSE 로 관측 가능한 근사 `llm_calls_observed = turn 수 + 좌석 조회 시도 status 수 × 3 + T + 3` 을 `rr_panels.llm_calls` 에 기록한다. `> cap` 이면 `quality.flag=over_budget` 를 달고 **재실행하지 않는다**(재실행은 PK 상 같은 좌석의 재착석이자 비용 2배다). 같은 타깃에서 연속 2패널 `over_budget` 이면 잡의 이후 패널을 `rounds_planned=2` 로 편성한다(적응은 앞으로만). P3 통과 기준 (8) 은 로그 실측과 `est_low~est_high` 의 차이 ≤30% 다.
- 벽시계 타임아웃 40분 → 패널 `error`(§6.7 9단계). 단일 vLLM 에서 `risk_concurrency=2` 는 처리량 2배가 아니므로 벽시계 추정은 직렬 기준이고, dev 박스 OOM 이력(메모리) 때문에 야간 배치는 `concurrency=1` 옵션을 UI 에 둔다.

## 6.11 MCP 경로의 실행 등급

앱 MCP(`hwax-risk`, 게이트웨이 백엔드 `heax-hwax_risk`, §0.5.2)는 심의 엔진이 아니라 **원장 접점**이다. 심의는 두 엔진만 한다 — agent-server `deliberation.py`(호출자 = 앱 러너, §6.7 (A)/(B))와 Claude Code 워크플로 `hwax-deliberate.js`(호출자 = 사람). 앱 MCP 도구는 그 사이에서 브리프 공급(`risk_get_brief`)·결과 회수(`risk_submit_panel_result`)·읽기 4종만 담당하고 LLM 을 부르지 않는다. `hwax-deliberate.js` 에는 좌석 도구 호출 경로(free_tools·tools·apps)도 읽기 전용 강제도 없으므로 그 엔진으로 돌린 패널은 evidence_only 등급으로만 원장에 들어간다.

| 경로 | 엔진 | 앱 MCP 도구와의 관계 | 원장 기록 | 커버리지 계수 |
|---|---|---|---|---|
| 웹 러너(정본) | agent-server — 앱 러너가 포털 `/agent/chat` 을 호출(§6.7 (A), 폴백 (B)) | 앱 MCP 를 거치지 않는다(같은 프로세스 안에서 `narrative.py` 직접 호출) | `engine='web'`, `tool_mode='tools'`, `tool_calls_n/ok`·`extra_seats` 는 SSE 귀속(§6.7 7단계) | §6.8 전체 규칙, C2 strong 비율 분모·분자 포함 |
| L1 단발 | `hwax-deliberate chairTemplate:'risk-review'`(evidence·personas 를 호출자가 줌) | 없음 — 원장 미연동. 사람이 결과를 `risk_submit_panel_result(panel_id, engine:'mcp', decision_text, turns, report_id, actor, model?)` 로 보내면 아래 L2 규칙(패널이 `planned` 로 미리 편성돼 있어야 하며 없으면 409) | — | — |
| L2 오케스트레이터 | `hwax-risk-review.js` 가 `risk_get_brief(target_key, tier)` 로 패널 목록·delib_opts 초안·E0~E9 를 받아 패널마다 `hwax-deliberate.js` 를 자식 호출하고 결과(decision·turns·report_id)를 `risk_submit_panel_result` 로 되돌림(§8.3.4) | 앱 MCP 2도구가 진입·회수 접점. 파서·병합·저장은 앱 한 곳(`POST /api/panels/{id}/complete` 와 같은 함수 → `parse_risk_spec` → §6.7 8~12단계)이고 JS 는 파싱하지 않는다 | `engine='mcp'`, `tool_mode='evidence_only'`, `tool_calls_n=null`, `used_tool=null`, `quality_json.actor`(이메일, `actor_verified:false`) | 좌석은 `cited_refs≠∅` 이면 `done`, 아니면 `done_weak`. C2 strong 비율 분모·분자 제외 |
| 재제출(web) | 없음(LLM 재실행 없음) | `POST /api/panels/{id}/complete {engine:'web', decision_text, turns?, events?[]}` — `spec_parse_failed` 보정(§6.9) 또는 외부 캡처 `events[]` 반입 | 기존 `engine`·`tool_mode` 유지. `events[]` 가 있으면 §6.7 7단계 정규식으로 `tool_calls_n/ok`·`extra_seats` 재계산, 없으면 기존 값 유지 | 재계산 결과대로 |

- 신원. 게이트웨이 경유 호출은 heax 서비스 PAT(admin) 신원으로 앱에 도달하고 최종 사용자·그룹은 전달되지 않는다(`per_user_sso` 미등록 앱, gateway.py:859-893). 따라서 `risk_submit_panel_result.actor`(이메일)는 게이트웨이 신고값이며 앱은 `rr_seat_opinions.quality_json`·`rr_panels.evidence_refs_json` 에 `actor_verified:false` 로 표기하고(DDL 무변경), `owner_sub` 는 `rr_panels.owner_sub`(편성 시 확정된 타깃 owner)를 승계한다 — actor 로 owner_sub 를 바꾸지 않는다. `risk_get_brief` 는 `actor` 가 owner 인 타깃과 `visibility='org'` 행만 돌려주고 actor 미해석이면 응답에 `reason='caller_unresolved'` 를 남긴다. 검증된 신원은 UI·REST 경로(`identity.py`)에서만 부여된다.
- 모델 출처(D6). MCP 경로에는 agent-server `/health` 스냅샷이 없으므로 `risk_submit_panel_result(…, model?)`·`POST /api/panels/{id}/complete{model?}` 의 호출자 신고값을 `rr_panels.model_json = {runtime:'claude-code', provider: <신고값 또는 null>, model: <신고값 또는 'unknown'>, captured:'caller_reported', engine_rev: <hwax-deliberate.js git sha 신고값 또는 null>, chair_rev, seat_contract_rev}` 로 적는다 — `actor` 와 같은 미검증 등급이고 `model_changed_midrun` 은 세우지 않는다. L2 `hwax-risk-review.js` 는 `args.model` 을 그대로 넘기고 없으면 `'unknown'` 이다. 종결 좌석의 `rr_coverage.model` 은 웹·MCP 공통으로 그 패널의 `model_json.model` 을 복사한다.
- `hwax-risk-review.js` 가 좌석 프롬프트에 "도구를 호출하지 말고 [근거]만으로 판정하라" 를 넣고, 계약 상수의 마지막 문장(evidence_only 절)이 이를 받는다. E0c 가 evidence 에 실려 계약표 자체는 MCP 경로에도 닿는다.
- Tier A 대표 패널과 무인 배치(야간 큐)는 웹 러너 전용이다. MCP 경로는 사용자가 Claude Code 에서 직접 돌리는 보충 회차로만 쓰고 진행판에 `engine=mcp` 배지가 붙는다. `risk_get_brief(target_key, tier:'A')` 는 `{error:'tier_a_web_only'}` 를 돌려준다.
- 앱 MCP 의 다른 소비자. `_RISK_KEEP_TOOLS` 의 P5 4종(`risk_get_snapshot · risk_get_diff · risk_get_registry · risk_claims_for_ref`)은 다른 심의(예 sim-plan)의 좌석이 등록부를 자유조회하는 읽기 경로이며 이 절의 실행 등급과 무관하다. 게이트웨이 `/tools-map` 에 이 도구들이 보이는 시점은 앱이 기동·레지스트리 노출된 뒤다(§8.2.5).
- 이 비대칭은 decision-table.md 파리티 표에 "JS: evidence-only(N/A: free_tools·tools·apps), RISK_SEAT_CONTRACT 동일 바이트" 로 기록한다.

## 6.12 이 절의 테스트 목록(`backend/tests/`)

| 파일 | 검증 |
|---|---|
| `test_planner.py` | Tier 산술(≈350 픽스처 → 3/20/48, ECAD 부재 3/14/33), 결정론 2회 동일, 동시 편성 롤백, Tier C xd ≤3·비-xd ≥2, counter 인접 표 순회, ECAD 대표 1석만 pending |
| `test_coverage_sm.py` | §6.8.3 불변식 7종, 전이표 전수(허용 전이 외 예외), carried 조건 4항 각각의 반례, `risk_carried_days=0` 으로 carried 0 |
| `test_sse_attribution.py` | 픽스처 SSE 스트림(status/evidence 혼합·빈 결과 호출·지정 도구 주입·adversary 발언)에서 tool_calls_n/ok·used_tool·extra_seats 정확, 귀속 성공률 ≥0.95, 깨진 접두 형식은 미귀속으로 남고 예외 없음. 같은 픽스처를 `events[]`(§8.2.3)로 넣어도 동일 결과·귀속 성공률 ≥0.95, `events[]` 없음 → `tool_calls_ok=null`·`used_tool=null` |
| `test_budget.py` | est_low/high 식, cap 초과 시 rounds_planned=2, 사후 over_budget 표기와 재실행 0, 연속 2패널 후 rounds 강등 |
| `test_close_levels.py` | C1(RA unavailable 상태에서도 도달), C2 strong 비율·MCP 제외·spec_parse_failed 미해결 차단·해결 후 통과, C3 skipped 5% 경계, `risk_default_close_level` 두 값의 잡 전이, '미착석 N명' 계산 |
| `test_seat_contract.py`(agent-server 측) | chair≠risk-review 에서 `_RISK_SEAT_CONTRACT`·`_RISK_KEEP_TOOLS` 비활성, chair=risk-review 에서 5/5 좌석 sysmsg(`_persona_round`)에 접미 존재·adversary 미부착, apps 지정 상태에서 `search_objects`·`check_design_rules`(keep)·`interface_graph`·`inspect_report`·`report_part_risk`(app+read) 통과·`set_interface`·`get_agent_session` 차단 |

---

# §7 학습 루프

배치(타깃 1개의 커버리지 회차)가 쌓일수록 리스크 이해도가 올라가는 기전이다. 루프 한눈에.

```
[스냅샷/diff] → [브리프: 원천 + 선례 원문·통계 + 유사 과제 성격 + rule_hits(§5.6)] → [패널 심의 → risk_spec(§4)]
   → [finding 인덱싱(택소노미 코드·cluster_key·subject_key·feature_snapshot·벡터)(§7.2)]
   → [라벨 유입(incident/test_run/voc/sim/expert_review/manual)(§7.6)]
   → [지표 재계산(precision·recall_proxy·lead_time·calibration·…)(§7.6)] → [패턴 마이너: candidate(§7.5)]
   → [큐레이션: known] → [규칙 생성·백테스트: rule] → [수치 타깃·표본 충족: predictor(별도 앱)]
   → 다음 타깃의 E5·E8·E9 와 새 스냅샷의 rule_hits 로 되먹임
```

루프가 도는지의 증거는 §7.6 의 '루프 작동' 배지 3지표다. 1차 합성 §7 의 구조(7.1~7.6)를 보존하고 gap_21 의 수정(cluster_key 의 별칭 정규화·§7.3 4단계·E7·external_sync 무관)을 반영했으며 7.7 을 더했다.

## 7.1 리스크 택소노미 v1(앱 리포 `backend/app/assets/taxonomy.v1.json`, 로더 `taxonomy.py`, 프론트는 `GET /api/meta/taxonomy`)

8축과 부가 status 는 §0.1.4 그대로다.

| 축 | 값 | 비고 |
|---|---|---|
| ① `domain` | 15(§0.1.5, 좌석 키 접두사 `_dom_of`) | Settings `risk_roster_domains` 와 동일 목록 |
| ② `mechanism` + `mechanism_detail` | `thermal{cte_mismatch, thermal_shock, hotspot, thermal_resistance, solder_fatigue}` · `mechanical{drop_stress, bending, buckling, fatigue, vibration, press_fit, rattle, mass}` · `interface{tied, touching, clearance, interference, tied_loss, clearance_close, adhesive_area, tolerance_stackup, cross_file_untrusted}` · `electrical{net, si_pi, emi, creepage, pad_lift}` · `material{creep, moisture, corrosion, property_uncertain, adhesive_aging, supplier_change}` · `process{tolerance, solder, adhesive_cure, screw_torque, warpage}` | detail 이 목록 밖이면 `unclassified` 저장 + `mechanism_free` 원문 보존 + 큐레이션 큐 |
| ③ `change_kind` | `dimension · placement · topology · material · type · count · discretization · result · load_path · consistency · electrical · none` | §3 의미 이벤트 code family 와 1:1(`discretization` 은 설계 변경이 아니므로 delta 선례에서 제외) |
| ④ `trigger_condition` | `env.{thermal_cycle, humidity, shock, salt}` · `load.{drop, bend, press, torsion}` · `time.{aging, creep}` · `mfg.{tolerance, process_variation}` · `use.{scenario}` · `none` | 접두 family 만 검증하고 하위 토큰은 자유 |
| ⑤ `severity` ↔ `judgement` | `경미→OK|WARNING` · `중대→WARNING|FAIL` · `치명→FAIL`, `undetermined` 는 어느 severity 와도 짝 | 정규화 `sev3 ∈ 1|2|3` |
| ⑥ `detectability` | `sim-detectable{tool 필수}` · `test-only` · `field-only` · `unknown` | `detect_tool` 은 게이트웨이 도구명 |
| ⑦ `evidence_grade` + `precedent` | `측정 · 문헌·규격 · 도구예측 · 경험칙` + `in_range · out_of_range · none` | 등급은 cites 에서 자동, precedent 는 코퍼스 범위에서 자동(§4) |
| ⑧ `direction` | `risk · improvement · neutral` | gains 는 improvement |
| 부가 `status` | `open · verified · dismissed · mitigated · superseded` | 라벨·사람 UI 로만 verified/dismissed |

파일 구조.

```json
{"taxonomy_version":"1.0","axes":{
  "mechanism":[{"code":"interface.interference","mechanism":"interface","detail":"interference","label":"간섭",
                "description":"…≤300","default_detectability":"sim-detectable","default_tools":["list_interfaces","interface_graph"],
                "version_added":"1.0","status":"active","merged_into":null}, …],
  "change_kind":[…],"trigger_condition":[…],"severity_judgement":{"경미":["OK","WARNING"],"중대":["WARNING","FAIL"],"치명":["FAIL"]},
  "detectability":[…],"evidence_grade":[…],"precedent":[…],"direction":[…],"status":[…]},
 "failure_map":[{"ra_failure_mode_category":"crack","mechanisms":["mechanical.drop_stress","mechanical.bending"]}, …],
 "voc_map":[{"voc_category":"…","mechanisms":[…]}]}
```

우선순위 점수(정렬용, 판정 아님)는 §4.7.1 의 `priority = sev3 × w_det × w_grade`(w_det field-only 3 · test-only 2 · unknown 2 · sim-detectable 1, w_grade 측정 1.0 · 도구예측 0.9 · 문헌·규격 0.8 · 경험칙 0.6, contested 이면 ×0.8) 하나만 쓴다. 등록부·통합 보고서의 기본 정렬 키다.

버전 규칙. 값 추가는 마이너(재색인 불필요), 의미 변경은 메이저(재매핑 스크립트 필수, 이전 값은 `rr_findings.status_reason` 에 보존). 삭제 금지, 통합은 `merged_into`. `taxonomy.py` 는 파일을 읽어 `validate(finding) → (normalized, invalid_enum[])` 를 제공하고 enum 위반은 값을 보존한 채 `invalid_enum` 에 기록한다(파서 비치명 규약). 택소노미 성장 루프 — `unclassified` finding 이 생기면 `rr_curation_queue(kind=unclassified_code, payload={finding_id, mechanism_free, candidates:[e5 top-3 코드 + 토큰 겹침]})` 를 넣고, 큐레이터가 `map`(기존 코드) 또는 `new`(코드 신설, 마이너 버전 증가) 를 결정하면 해당 finding 들의 `mechanism_detail · taxonomy_version` 을 갱신한다. 같은 `mechanism_free` 클러스터가 ≥5건·≥3과제면 큐 항목에 `신설 권고` 배지를 코드가 붙인다.

## 7.2 인덱싱(배치가 쌓일수록 두터워지는 것)

| 인덱스 | 키 | 원천 | 용도 |
|---|---|---|---|
| 클러스터 인덱스 | `cluster_key = sha1(mechanism|mechanism_detail|subject_key_norm|change_kind)[:12]`, `subject_key_norm` 은 `rr_iface_alias`·`rr_part_keys.merged_into` 를 거친 별칭 수준 | rr_registry·rr_findings | 같은 계면·같은 변경의 finding 재발 추적(과제·connectivity 무관) |
| delta 선례 표 | `(change_kind, mechanism, mechanism_detail)` | rr_delta_priors | 이번 diff 에 "과거 N건 제기·V건 검증·D건 기각" |
| 특징 벡터 | `snapshot_id → 22차원 표준화 벡터 + known 마스크` | rr_states.feature_json | 유사 과제 kNN |
| 계면 별칭 사전 | 무순서 `(canonical_a, canonical_b)` + asm_key 별칭 | rr_iface_alias | 다른 connectivity 에서 같은 계면 인식(§5.9) |
| 서술 임베딩 | AIDataHub sections(384)·signature(768) | risk_review_opinion·risk_review_panel·project_character | hybrid_search·agent_search(risk-review-memory) |
| claim 역색인 | `ref → claim_uid` | rr_claim_refs | "이 엣지·이 변경에 대해 누가 뭐라 했나" |
| 전문가별 이력 | `agent_key → opinion·tool_calls_ok·cited_refs·정밀도` | rr_seat_opinions·rr_metrics(expert) | 로스터 관련도 보정(과거 IR 인용률·정밀도 높은 전문가 우선), E7 |
| feature 스냅샷 | finding.cites 가 가리키는 IR 속성값 사본 | rr_findings.finding_json.feature_snapshot | IR 이 바뀌어도 당시 수치 보존, 규칙 조건 범위·예측기 학습 재료 |

finding 삽입 시 즉시(코드, 순서 고정). ① 택소노미 검증·`sev3` ② `subject_key` 계산(별칭 정규화) ③ `cluster_key` ④ `feature_snapshot = {refs:[{ref, attrs:{min_gap, penetration_depth, contact_area_est, dz, volume, material.E …}}], diff:[{cid, before, after, delta, rel_delta}], project_fv: feature_vector 발췌 8키(§3.2.5 이름 — n_leaf, n_tied, n_interference, min_gap, orphan_ratio, n_materials, thin_ratio, max_pen_depth)}` ⑤ `precedent` 부여(코퍼스 n ≥5 일 때만) ⑥ `rr_claim_refs` 역색인 ⑦ 등록부 병합 후 `rr_delta_contrib` UPSERT·`rr_delta_priors` 재합산(§4.7.1·§7.4) ⑧ 벡터는 AIDataHub 의견 레코드 섹션 임베딩에 위임한다(앱은 벡터 저장 없음 — 텍스트 검색은 AIDataHub 의 몫이라는 §5.1 분담). 버전 스탬프(§7.7)를 같이 적는다.

## 7.3 유사 검색(알고리즘, 호출 계약은 §5.7)

1. **계보** — RA `get_subgraph(project, relations=['revision_of','derived_from','snapshot_of'], depth=3)` 로 3홉, RA 미가용이면 `rr_projects.predecessor_project_id` 체인 3홉. 점수 = 3 − (hops − 1).
2. **특징 벡터** — `rr_states.feature_json` 의 22차원을 코퍼스 z-score(야간 잡이 평균·표준편차를 `rr_metrics(dimension=global, metric=fv_mean_<k>|fv_std_<k>)` 에 버전과 함께 보관)로 표준화하고 `known` 마스크로 결측 차원을 제외한 코사인 top 5. **상대 순위만** 쓰고 절대 임계는 없다. 코퍼스 n_snapshots <5 면 이 경로는 비운다.
3. **텍스트** — AIDataHub `hybrid_search(q=summary_text 앞 300자, tags=['hwax-risk-review','mechanism:<상위 mechanism>'])` top 5 → 레코드 `tags hwax:project:` 로 과제 환원. 미가용이면 비운다.
4. **subject 정확 매치 + geom_fp 근접** — §5.9.4. 계보가 없어도 같은 파트·같은 계면을 가리키는 등록부 클러스터를 회수한다.

교집합 가중(계보 3 · 벡터 2 · 텍스트 1 · subject 2)으로 `merged` 목록을 만들되 화면은 경로별로 따로 보여준다. E5 는 `merged` 상위 과제의 등록부 클러스터를, E6 은 그 과제들의 성격 진술을 싣는다. 재순위 보정(클러스터 단위) — `+0.10 labels.confirmed ≥1`, `−0.10 labels.refuted > labels.confirmed`, `+0.05 same change_kind`, `+0.05 same material_norm`. 선례 0건이면 E5·E8 에 결측 문구(`[선례 없음 — 코퍼스 n_targets=…, 이 조합 첫 사례]`)를 원문으로 넣어 좌석이 `precedent=none` 을 적게 한다(out_of_range 개념의 텍스트 이식).

## 7.4 변경-델타 리스크

- **기여 행(멱등).** 등록부 병합(`registry.merge(target)`, §4.7.1) 시 pair 타깃의 클러스터를 `(change_kind, mechanism, mechanism_detail)` 로 묶어 `rr_delta_contrib(…, target_key)` 에 `n_raised = Σ support(direction=risk)`, `n_improvement = Σ support(direction=improvement)`, `sev_hist_json`, `resolving_checks_json` 을 UPSERT 하고, 같은 트랜잭션에서 영향받은 조합의 `rr_delta_priors` 를 기여 표의 합(`n_raised`·`n_improvement` 합, `n_targets = COUNT(DISTINCT target_key)`, `sev_hist_json` 합, `top_resolving_checks_json` 빈도 상위 3)으로 재합산한다. 같은 타깃을 몇 번 재병합해도 기여 행은 덮어써지므로 값이 부풀지 않는다. `change_kind ∈ {discretization, none}` 은 집계하지 않는다.
- **라벨 훅.** `rr_labels` 삽입 시 그 finding 의 조합에 `outcome=confirmed → n_verified+1`, `refuted → n_dismissed+1`(inconclusive 는 무변화). 등록부 `status` 를 사람이 `verified|dismissed` 로 바꿔도 같은 훅이 돈다(source=expert_review). 예측값(도구예측)만으로는 verified 를 올리지 않는다.
- **선례 정밀도.** `precision = n_verified/(n_verified+n_dismissed)`, 분모 <5 면 `n<5` 를 병기하고 정밀도 대신 카운트만 보여준다.
- **E8 문구(수치만).** `placement/interface/interference: n_raised 7 · n_targets 5 · n_verified 3 · n_dismissed 1 · precision 0.75 (n=4)`.
- **delta 후보(코드, LLM 아님).** diff 생성 시 semantic 이벤트마다 (a) `rr_rules(status=active)` 실행 → `rule_hits`(E9) (b) `rr_patterns(status ∈ known|rule)` 중 `change_kind` 일치 + `feature_ranges_json` 부분 일치 → `pattern_candidates[{pattern_id, status, n_projects, precision, direction}]`(`/precedents` 응답, E8 뒤 1줄 `패턴 P-017 interface.interference/placement: 선례 7건·5과제·precision 0.71`). 좌석이 채택·기각하고 결정문 finding 이 `reg:`·패턴을 인용하면 `rr_patterns.n_findings` 가 증가한다.
- **정합 검사(야간).** 야간 잡이 `rr_delta_contrib` 합과 `rr_registry ⨝ rr_labels` 로 다시 계산한 값을 `rr_delta_priors` 와 대조해 불일치 조합만 재합산하고 `rr_metrics(dimension=global, metric=nightly_delta_priors_drift)` 에 건수를 남긴다(`stats_version` 증가). 증분 오류를 '바로잡는' 장치가 아니라 정합을 '확인하는' 장치다 — 병합 자체가 멱등이라 정상 운영에서 drift 는 0 이다.
- **모델 층화·승격 가드(D6).** 모델 축은 저장 표를 늘리지 않고 조회·판정 시 조인으로 층화한다 — `rr_findings.panel_id → rr_panels.model_json.model`. `GET /api/precedents` 는 조합별 총합(위 E8 문구) 옆에 `by_model[{model, n_raised, n_targets, n_verified, n_dismissed}]` 를 같은 조인으로 계산해 싣고, `rr_metrics(dimension ∈ pattern|mechanism)` 는 `key` 에 `@model=<name>` 접미를 붙인 행을 총합 행과 병렬로 낸다(§7.6 지표 정의 불변). 승격 가드 — Settings `risk_promote_distinct_models`(기본 1 = 가드 없음, §8.2.6)가 2 이상이면 §7.5 candidate 조건에 '그 패턴의 finding 을 낸 서로 다른 `model` 수 ≥ N' 을 더한다(사람 승인은 그대로). E8 문구는 총합만 쓴다.

## 7.5 '알려진 리스크' 승격 상태기계(`rr_patterns.status`)

| 전이 | 조건(수치, §0.6) | 트리거 | 산출 |
|---|---|---|---|
| ∅ → `candidate` | 같은 `cluster_key_norm`(subject 는 별칭 수준) finding 이 타깃 ≥3 AND 서로 다른 project ≥2 AND 서로 다른 expert ≥2 | 야간 마이너 | `rr_patterns` 행 + `rr_curation_queue(kind=pattern_candidate)` |
| `candidate` → `known` | 큐레이터 승인 AND (`labels.confirmed ≥1` OR finding ≥5 across project ≥3) | 사람(UI) | AIDataHub `risk_pattern_card`(P6), RA 는 `risk_pattern` 객체를 만들지 않고 `design_trait`(status=proposed → 사람이 vocab 승격) 태그와 `exhibits` 로만, `delta 후보` 참여 시작 |
| `known` → `rule` | 조건 DSL 작성(자동 초안: `feature_snapshot` 수치 속성의 confirmed finding 범위 `[min, max]` 를 `between` 조건으로) AND 백테스트 `n_labeled ≥10 · precision ≥0.6 · recall ≥0.5`(시간순 홀드아웃, 뒤 30%) | 사람 승인 | `rr_rules(status=active, source=pattern)` — 새 스냅샷의 `rule_hits` 에서 즉시 작동 |
| `rule` → `predictor`(S2) | 수치 타깃 존재(test_run 측정값·incident 발생 여부·sim 지표) AND `n_labeled ≥50` AND `n_projects ≥15` AND 5-fold CV `R² ≥0.6`(회귀) 또는 `AUROC ≥0.75`(분류) | 사람 승인 | 별도 MCP 앱(열충격 수명주기 복제: `add_training_data → train_model(CV 비교) → activate_model(롤백) · data_sha256 · feature_ranges · out_of_range`) — 이 계획의 코드 범위 밖, 계약서만 P7 |
| any → `suspended` | 최근 20 라벨 precision <0.3 | 자동 제안(큐) | `delta 후보·rule_hits` 에서 제외, 선례 링크 유지, 사람이 복귀 또는 폐기 |
| any → `deprecated` | 큐레이터 폐기 | 사람 | 동일 제외, 이력 보존 |

승격은 항상 사람 승인이고 자동 활성화는 없다. 승격 결정 엔드포인트는 `PUT /api/registry/{cluster}/status` 와 같은 패턴의 큐레이션 결정 API 로 §8 이 P6 에서 정의하며, 백테스트 미달(`precision <0.6 · recall <0.5 · n<10`)이면 422 를 돌려주고 상태를 바꾸지 않는다(P6 (4)). `rule → predictor` 는 게이트 미충족 시 학습 코드가 0줄이어야 한다(P6 (7)).

열충격 선례와의 대응. `add_training_data` ↔ 라벨 삽입(record_id = finding_id+label_id 중복키), `train_model` ↔ 백테스트·CV, `activate_model` ↔ status 전이, `get_model_info` ↔ `rr_patterns` 통계, `out_of_range` ↔ `precedent=out_of_range`, `FAIL/WARNING/OK` ↔ `judgement`. 예측값은 학습에 되먹이지 않고 라벨만 쓴다.

조건 DSL(`rr_rules.condition_json`)과 평가기(`state.py`, 부작용 없음·결정론).

```json
{"all":[{"ref":"edge.kind","op":"eq","value":"interference"},
        {"ref":"edge.penetration_depth","op":"gte","value":0.05},
        {"ref":"diff.change_kind","op":"in","value":["placement","dimension"]}],
 "any":[]}
```

`ref` 접두 `node.* · edge.* · dims.<name> · state.<signal> · diff.*` 는 IR/diff 경로이고 `op ∈ eq|ne|gte|lte|between|in|exists` 다. `edge.*`·`node.*` 조건은 "하나라도 만족하는 원소가 있으면 pass" 이고 `found` 에 만족한 nid/eid 를 전부 담는다. `diff.*` 는 diff 스코프에서만 평가되고 snap 스코프에서는 `exists=false` 로 취급한다. 출력은 `{rule, rule_version, severity, pass, found, why_it_matters, fix_hint, payload_hash}`, `payload_hash = sha1(rule_id|rule_version|ir_hash|diff_hash?)` 로 같은 IR 에 두 번 돌리면 같은 값이다(P6 (5)).

시드 규칙 6종(`rules-seed.v1.json`, source=seed, P1 부터 active — 패턴 마이닝 산출이 아니라 사람이 쓴 규칙이라 코퍼스 0 에서도 가시 효과가 난다). id·이름·조건 DSL 은 §3.2.6 이 정본이고 여기서는 같은 6종의 `why_it_matters` 원문만 적는다.

| id | 이름(§3.2.6) | 조건(요지) | severity | why_it_matters(원문 인용 대상) |
|---|---|---|---|---|
| R-001 | interference_auto_present | `edge.kind=interference AND edge.status=auto` ≥1 | 중대 | 간섭이 auto 로 남아 있으면 억지끼움 의도인지 설계오류인지 확정되지 않은 것이고, 계면 확정 전에는 penetration 값이 하한 추정치다 |
| R-002 | tight_clearance_cluster | `edge.kind=clearance AND edge.min_gap≤0.2` 개수 ≥5 | 경미 | 0.2 mm 이하 여유 계면이 5개 이상이면 공차 누적 검토 대상이다 |
| R-003 | thin_leaf_tied_both_sides | `node.min_dim≤0.3 AND node.degree_tied≥2` ≥1 | 중대 | 0.3 mm 이하 박판 리프가 양면 tied 이면 적층 응력과 접착 면적이 그 판 하나에 걸린다 |
| R-004 | unit_mismatch_warning | `warnings.code IN ('unit_mismatch')` exists | 치명 | 단위 불일치 경고가 있는 소스의 치수·간극 수치는 근거로 쓸 수 없다(G6 blocked 와 같은 사실) |
| R-005 | cross_file_with_suspect_coords | `edge.cross_file=1 AND warnings.code IN (suspect_coordinate_systems, files_all_overlap)` | 중대 | 좌표계 의심 상태의 cross_file 계면은 근거로 쓸 수 없다 |
| R-006 | dyna_contact_without_mcad_tie | `edge.kind=contact AND edge.mapped_mcad_kind IN (null, clearance)` ≥1 | 중대 | 해석 접촉 쌍이 MCAD 계면에 없으면 해석 모델과 설계 형상의 결합 정의가 어긋난 것이다 |

시드 밖 후보(P6 큐레이션에서 `rule` 로 승격할 후보이며 시드 파일에는 넣지 않는다).

| 후보 id | 조건(요지) | severity | why_it_matters |
|---|---|---|---|
| R-007 | `state.orphan_ratio ≥0.3` | 경미 | 리프 노드의 30% 이상이 계면 없이 떠 있어 검출 범위·조립 관계를 확인해야 한다 |
| R-008 | `node.material.density_unsourced=true AND state.dyna_present=true` | 경미 | 밀도 출처가 없는 파트의 질량·관성은 해석 입력과 대조해야 한다 |
| R-009 | `diff.change_kind=material AND edge.kind IN (tied,interference) AND 같은 subject` | 중대 | 재료 교체가 결합 계면에 직접 걸려 강성·CTE 경로가 함께 바뀐다 |

`why_it_matters · fix_hint` 는 시드 파일의 사람이 쓴 문장을 원문 인용하며 E9 에 `rule:<id>` 태그로 실린다.

## 7.6 적중 추적(라벨과 지표)

라벨 유입 5경로(`rr_labels`, `matched_by auto|manual`).

| # | 경로 | 매칭 | 자동 확정 |
|---|---|---|---|
| 1 | RA `incident` — 야간 `search_objects(type='incident', props=[{key:'occurred_on', op:'gte', value:<마지막 동기>}])` → `caused_by` 로 part/defect | 3항 — (a) 과제 일치(`revision_of` 계보 포함) (b) part 별칭 ↔ ckey(`rr_part_keys.aliases_json`·RA alias) (c) defect/failure_mode category ↔ mechanism(`taxonomy.failure_map`) — `match_score = 일치 수/3` | `1.0` 만 `auto confirmed` + RA `verified_by` 링크(관계 속성 label_id·match_score·source). 그 외는 `rr_curation_queue(kind=label_match)` |
| 2 | RA `test_run`/`rel_test` — `tested_by` 결과 속성(pass/fail 이 있을 때) | 1 과 같은 매칭 AND finding.trigger_condition 이 그 시험 환경과 일치할 때만. `fail=confirmed · pass=refuted` | 1.0 만 auto, `refuted` 는 RA `refuted_by` 링크 |
| 3 | DynaForge 후속 리포트 — 같은 과제 뒤 스냅샷의 `results.findings` CRITICAL | 같은 ckey AND 같은 `mechanical.*` 코드 | 항상 큐(도구예측 등급, 가중 0.5, `source=sim`) — verified 로 자동 승격 없음 |
| 4 | SignalForge VOC — 과제→product_code 매핑이 있을 때 `get_top_issues(product_code, 90d)`·`get_kg_relations('product:<code>')` category → `taxonomy.voc_map` | 매핑표 일치 | 항상 큐(`source=voc`) |
| 5 | 사람 — finding·등록부 화면에서 `confirmed|refuted|inconclusive` + `evidence_ref`(`inc:`·`rpt:`·자유 텍스트) | — | `matched_by=manual`, `source=expert_review|manual` |

라벨이 붙으면 같은 트랜잭션에서 `rr_findings.status`·`rr_registry.status`(verified/dismissed)·`rr_delta_priors`(§7.4 훅)·`rr_patterns.n_confirmed|n_refuted`·RA `risk_finding.status`(get_object 후 병합, 비치명) 를 갱신한다.

지표(`rr_metrics`, 야간 + 라벨 훅, dimension `expert|domain|mechanism|pattern|project|global`, `n` 병기).

| metric | 정의 | 최소 n |
|---|---|---|
| `precision` | `confirmed/(confirmed+refuted)`(inconclusive 제외) | 5 |
| `recall_proxy` | 심사된 과제에서 발생한 incident 중 선행 finding(같은 ckey·같은 mechanism family)이 있던 비율 | 3 |
| `lead_time_days` | `median(incident.occurred_on − finding.created_at)` | 3 |
| `calibration` | 예측 `sev3` × 관측 `severity_observed` 3×3 혼동행렬(JSON), 과대경보율 = 예측 치명 중 관측 경미 비율 | 5 |
| `adversary_false_reject` | 반대석이 기각(결정문에서 contested 후 dismissed)했으나 이후 confirmed 된 finding 비율 | 5 |
| `evidence_grade_dist` | 4등급 분포(JSON) | 1 |
| `out_of_range_ratio` | `precedent ∈ {none, out_of_range}` 비율 | 1 |
| `unclassified_ratio` | `mechanism_detail=unclassified` / 총 finding | 1 |
| `coverage_pct` | 타깃별 종결 좌석 / roster_size, deferred 제외 | 1 |
| `precedent_hit_rate` | 새 타깃 의미 변화(semantic 이벤트) 중 E5·E8 선례 ≥1 이 있던 비율 | 1 |
| `known_share` | finding 중 `rr_patterns(status ≥ known)` 에 속한 비율 | 1 |
| `rule_precision_trend` | active 규칙 백테스트 precision 의 최근 5회 이동평균 | 1 |

판정 규칙('루프 작동' 배지). 최근 5타깃 이동평균이 `precedent_hit_rate ≥0.5 · known_share ≥0.3 · unclassified_ratio ≤0.2` 를 모두 만족하면 코드가 배지를 붙이고, 아니면 병목을 표기한다 — 라벨 부족(`n_labels < 20`), 큐 적체(`open ≥ 30` 또는 최고령 항목 > 14일), 커버리지 미달(최근 5타깃 `coverage_pct < 0.5`). 지표는 `n < 최소 n` 이면 값 대신 `n<k` 로 정직하게 표기한다.

되먹임 규칙. 전문가별 `precision(n≥5)` 은 공개 랭킹이 아니라 로스터 `relevance` 보정(§6 planner, ±0.1)과 패턴 승격 가중(precision ≥0.5 → 1.0, 미만 0.5, n<5 → 0.8)에만 쓴다. 코드별 과대경보율 ≥0.5 이면 그 코드의 `default_detectability · description` 재검토를 큐레이션 큐(`unclassified_code` 와 같은 화면)에 올린다. T0 하네스 `HWAXAgentServer/delib_metrics.py` 에 리스크 지표 7종(도구 사용률 · IR 인용률 · 근거등급 분포 · out_of_range · 반대석 기각률 · 클러스터 중복률 · risk_spec 파싱 성공률)을 추가한다(P4).

## 7.7 버전 스탬프·큐레이션 큐·야간 잡

버전 스탬프. `taxonomy_version · rule_version · planner_version · ir_version · diff_version · adapter_version` 을 finding(`rr_findings` 컬럼 + `finding_json`)·패널(`quality_json.versions`)·통합 보고서(헤더 key_value)에 남긴다. 버전이 다른 레코드를 섞어 지표를 낼 때는 `rr_metrics.key` 에 `@<taxonomy_version>` 접미로 분리한다.

큐레이션 큐(`rr_curation_queue.kind`).

| kind | payload | 결정 |
|---|---|---|
| `unclassified_code` | `{finding_id, mechanism_free, candidates:[…]}` | `map:<code>` · `new:<code>` · reject |
| `pattern_candidate` | `{pattern_id, cluster_key_norm, n_findings, n_projects, n_experts, sample_claims:[≤5]}` | `known` 승인 · reject |
| `label_match` | `{finding_id, source, evidence_ref, match_score, matched:{project, part, mechanism}}` | `confirmed|refuted|inconclusive` · reject |
| `x_tag_promote` | `{tag:'x:…', n_targets, n_panels, statements:[character_id…]}` — 타깃 ≥3 · 패널 ≥2 에서 같은 값 | `char:<axis>:<value>` 로 승격(어휘 마이너 버전 증가, RA design_trait status=vocab) · reject |

야간 잡(앱 `runner.py` 의 `nightly_loop` 스레드 — §8.2.9, 로컬 시각 00:30 에 1회, 순서 고정, 각 단계 멱등). ① 라벨 동기(RA incident·test_run → 큐/auto, DynaForge 후속 리포트 → 큐) ② `rr_delta_priors` 정합 검사(`rr_delta_contrib` 합·`rr_labels` 대조, 불일치만 재합산 — §7.4) ③ 패턴 마이너(candidate 표면화, suspended 자동 제안) ④ 지표 재계산·배지 ⑤ feature_vector z-score 통계 갱신 ⑥ `x:` 태그 승격 스캔 ⑦ `external_sync` 재시도(§5.5.3) ⑧ `rr_id_map` 정합 검사. 실패한 단계는 다음 단계를 막지 않는다. 야간 잡은 `rr_jobs`(배치 잡 전용 표)에 행을 만들지 않고 애플리케이션 로그와 `rr_metrics(dimension=global, metric=nightly_<step>_ok)` 에만 결과를 남긴다.


---


# §8 포털·MCP 통합

이 절은 §2~§7 이 정의한 것을 B 토폴로지(§0.7 #12)대로 다섯 자리에 파일 단위로 얹는다 — 포털(창 하나, §8.1) · HEAX 앱 hwax_risk(자산·REST·SPA·MCP·러너, §8.2) · 심의 엔진(additive 항목, §8.3) · HEAXHub(매니페스트 등록 1건, §8.2.2) · 게이트웨이(설정 변경 0, 자동 흡수, §8.3.5). 이름은 전부 §0 정본을 쓴다. 앱 REST base 는 `/apps/hwax_risk/api`(앱 내부 `/api`), 앱 MCP 는 `/apps/hwax_risk/mcp`, 기능 플래그는 없다(앱 존재가 활성 — `risk_review_enabled` 폐기). 포털 백엔드에는 리스크 라우트·Settings·러너가 없고, 포털이 바뀌는 것은 메뉴·타일·`systems.yaml` 과 conv kind 2줄뿐이다(§8.4). 아래 줄 번호는 2026-08-31 기준 실파일에서 확인한 것이고(deliberation.py · routes.py · hwax-deliberate.js · proxy_manager.py · authz.py · integration_launcher.py · gateway.py), 구현 시점에 다시 확인한다.

## 8.1 포털(창) — 신규 메뉴 '리스크 심사'

### 8.1.1 방식 확정 — `systems.yaml` jwt-handoff 타일 + `/launch` 로 앱 UI 열기

| 후보 | 무엇 | 인증 경로 | 판정·이유 |
|---|---|---|---|
| (i) 타일 + `/launch/hwax-risk` + 앱 링크 | 포털 라우트 `/risk` 의 얇은 셸이 HEAX SSO 를 거치게 한 뒤 `/apps/hwax_risk/` 를 새 탭으로 연다 | `POST /systems/hwax-risk/launch`(세션 쿠키 + `X-CSRF-Token`) → RS256 launch JWT(aud `heax-hub`, scope `launch`, 90 s, jti 1회) hidden POST → HEAX `POST /api/v1/auth/portal-callback` 이 쿠키 `heax_access_token`(path=/, httpOnly, samesite=lax) + localStorage `heaxhub.auth` 를 심음(portal_sso.py:207-212) → 이후 `/apps/hwax_risk/*` 는 Caddy forward_auth 가 그 쿠키로 통과(authz.py:102) | **채택.** 기존 패턴(`LaunchPage.tsx:14-31`, `PortalHomePage.tsx:29-39`)을 그대로 쓰고 포털 코드는 셸 페이지 1개뿐이다. 토큰이 URL 에 남지 않고 포털 CSRF 는 `/launch` 한 번만 쓰인다 |
| (ii) 포털 SPA 가 앱 REST `/apps/hwax_risk/api/*` 를 직접 fetch | 포털 페이지가 앱 데이터를 그린다 | 포털 SPA 는 포털 세션 쿠키·`hwax_csrf` 만 갖는다(`client.ts apiFetch`, credentials include). Caddy `/apps/<id>/` 게이트는 쿠키 `heax_access_token` 또는 heax PAT 만 본다(authz.py:102-117) | **기각.** SSO 뒤엔 같은 오리진이라 fetch 가 한동안 통과하지만 리프레시가 HEAX SPA 안에서만 일어나 TTL 만료 후 조용히 401 이 된다. 포털 SPA 가 heax 토큰 수명을 관리하게 되고 앱 화면이 두 리포에 갈라진다 |
| (iii) 포털 백엔드 서버측 프록시(heax 서비스 PAT + `x-forwarded-user`) | 포털 라우트가 앱 REST 를 대리 호출 | heax 서비스 PAT 를 포털 시크릿에 추가 | **기각.** 신원이 서비스 계정으로 뭉개지고 포털에 시크릿·라우트가 는다(§0.7 #12 '포털은 창만') |
| (iv) iframe 임베드 | 포털 페이지 안에 `/apps/hwax_risk/` 를 iframe 으로 | (i) 와 같음 | **기각.** 포털 nginx·HEAX 에 X-Frame-Options/frame-ancestors 설정이 없어 기술적으로는 가능하나 SSO 미완료 시 401 흰 화면·중첩 인증 UX 가 남는다. 새 탭이 단순하다 |

포털 프론트가 앱 REST 를 직접 fetch 하지 않는 이유(요약). ① 자격이 다르다 — 포털 세션은 Caddy 게이트를 못 넘고 heax 자격은 포털 SPA 가 관리하지 않는다. ② 수명이 다르다 — heax 쿠키 리프레시는 HEAX SPA 몫이라 포털 화면은 만료를 감지할 수 없다. ③ 소유가 다르다 — 자산은 앱이 소유하고 화면도 앱이 그린다(B). 그래서 포털 창은 '연다' 만 한다.

### 8.1.2 `backend/config/systems.yaml` 타일 1건

```yaml
- id: hwax-risk
  name: 리스크 심사
  tagline: 설계 IR·diff 위의 전문가 리스크 심사
  description: StepForge·DynaForge 스냅샷을 동결·비교하고 HW/XD 전문가 패널이 리스크·개선·성격을 판정해 등록부로 누적합니다.
  accent: rose
  category: engineering
  status: available
  integration_type: jwt-handoff
  audience: heax-hub
  url: /heax-hub/api/v1/auth/portal-callback
  handoff_mode: auto_post
  handoff_param: token
  # required_role: <포털 그룹명>   # 선택 — 두면 그 그룹만 타일·NavLink 가 보인다
  sort_order: 60
```

적용은 `POST /systems/reload`(admin) 이고 포털 재기동이 없다. `audience` 는 HEAX `PORTAL_AUDIENCE`('heax-hub', config.py:59)와 같아야 하며 기존 `heax-hub` 타일(systems.yaml:15-28)과 같은 값이다 — 두 타일이 같은 콜백으로 가도 HEAX 는 jti 로만 재사용을 막으므로 충돌이 없다. 필드 정의는 `backend/app/schemas/system.py:24-40`.

### 8.1.3 라우트 1개 · NavLink 1개 · `RiskLaunchPage.tsx`

- `frontend/src/App.tsx` `createBrowserRouter([...])`(:14) 의 `{ path: '*' }` 앞에 기존 항목과 같은 모양으로 `{ path: '/risk', element: <ProtectedRoute><AppShell><RiskLaunchPage /></AppShell></ProtectedRoute> }` 1개를 추가한다. 기존 6 라우트(`/login`, `/`, `/deliberate`, `/apps`, `/tokens`, `/launch/:systemId`)는 무변경이다.
- `frontend/src/components/layout/AppHeader.tsx`(:33-47) 의 NavLink 4개 뒤에 `'리스크 심사' → /risk` 1개를 append 한다. 표시 조건은 카탈로그(`GET /systems`, `visible_for(groups)`)에 `id === 'hwax-risk'` 타일이 있을 때다 — env 플래그·앱 헬스 조회 없음. 타일이 안 보이는 사용자(`required_role` 밖)에게는 헤더가 종전과 같다.
- `frontend/src/pages/risk/RiskLaunchPage.tsx`(신규, 파일 첫 줄 한국어 주석) — 얇은 셸 2단. ① 'HEAX 로그인' 버튼: `navigate('/launch/hwax-risk')` → 기존 `LaunchPage` 가 `launchSystem()` 후 hidden POST 를 자동 submit → HEAX 콜백이 쿠키·localStorage 를 심고 `/heax-hub/`(`portal_sso_landing` 고정, `next` 파라미터 없음)로 착지한다. ② '리스크 심사 열기' 버튼: `window.open('/apps/hwax_risk/', '_blank', 'noopener')`(포털 nginx `/apps/` → Caddy `/apps/`, routes.env:41). 페이지는 앱 REST 를 fetch 하지 않고 상태 조회도 없다 — 새 탭이 401 이면 "① 을 먼저 누르세요" 안내 문구를 정적으로 둔다. 2단인 이유는 HEAX 콜백 랜딩이 `/heax-hub/` 고정이라 포털 메뉴가 곧바로 `/apps/hwax_risk/` 로 착지시키지 못하기 때문이고, HEAX `portal_sso.py` 에 allowlist 된 `next` form 필드를 additive 로 넣는 선택(§0.4.4)이 채택되면 ①②가 한 단이 된다(§10).

### 8.1.4 심의 메뉴에 남는 것 — Job 'risk-review' L1 진입(유지)

`frontend/src/components/chat/delibTaxonomy.ts` 는 `JobId` 유니언(:5) · `JOBS` 배열(:29~37, 7행) · `JOB_BY_ID`(Record) · `JOB_ROUTING`(Record, :66) · `suggestJob`(:94) 로 이루어져 있고, `Record<JobId, …>` 가 키를 강제하므로 `JobId` 에 값을 더하고 `JOB_ROUTING` 에 항목을 빠뜨리면 `tsc -b` 가 실패한다. 변경 3곳(기존 7행 객체의 텍스트는 1바이트도 바꾸지 않는다).

```ts
// (1) JobId 유니언 끝에 추가
export type JobId = /* 기존 7개 */ | 'risk-review';

// (2) JOBS 배열 8행째(배열 마지막 원소 뒤에 append)
{ id: 'risk-review', group: 'judge', name: '리스크 심사',
  engine: 'IR diff · FMEA · 기준선 옹호석',
  when: '과제 현황 평가 · 이전 과제 대비 변경 · 개념설계 변동',
  out: '리스크 심사 보고서 · risk_spec 등록부 · 과제 성격 서술',
  note: '설계 IR 과 diff 원천 위에서 HW/XD 전문가가 회차로 각자 도구를 실호출해 리스크·개선·성격을 판정합니다 — 실행이 아니라 판정 문서까지가 산출입니다.',
  placeholder: '심사할 과제(또는 기준 과제와 비교 과제)를 입력하세요… 정식 흐름은 리스크 심사 메뉴에서 시작합니다.' },

// (3) JOB_ROUTING 항목 — 트리거는 기존 '/심의 ' 그대로, chair 로만 라우팅(app.py 분기 변경 0)
'risk-review': { trigger: '/심의 ', chair: 'risk-review' },
```

`suggestJob(usedTools)` 에는 분기 1개를 기존 분기들 **뒤에** append 한다 — `usedTools` 에 `interface_graph · list_interfaces · compare_reports · risk_get_diff · risk_get_registry` 중 하나라도 있으면 `{id:'risk-review', why:'설계 그래프·리포트 비교 도구를 썼습니다'}`. 기존 분기가 먼저 매치되면 기존 결과가 그대로 나온다(회귀 0). 카피 규칙은 method-menu decision-table.md 를 따른다 — 상황이 헤드라인(`when`), 방법론이 서브(`engine`), 애매동사 금지. `HandoffBrief.tsx`·`DeliberatePage.tsx`·`StartPicker.tsx` 는 `JOBS` 를 순회하므로 코드 변경 없이 8번째 카드가 나타나고, 챗 핸드오프(`startHandoff`, HandoffBrief.tsx:82)에서 이 Job 을 고르면 `delib_opts.chair_template='risk-review'` 와 대화 activity 원천이 evidence 로 실려 **원장 미연동 단발 심사(L1)** 가 된다 — P0 만으로 얻는 기능이다. `placeholder` 의 "정식 흐름은 리스크 심사 메뉴에서 시작합니다" 는 `/risk` 창을 가리킨다.

ConvKind. `frontend/src/api/conversations.api.ts:6` `ConvKind = 'chat' | 'deliberation' | 'risk-review'`, 백엔드 `backend/app/agent/routes.py:129` `ConvCreate.kind: Literal["chat", "deliberation", "risk-review"]`(conv_store `kind` 는 CHECK 없는 TEXT, conv_store.py:37, DDL 변경 없음). `state/ChatContext.tsx:293` 이 `m.kind === serverKind` 로 거르므로 `/deliberate` 에는 앱 러너가 만든 패널 대화(§6.7 4단계)가 0건 노출된다(P3 통과 기준). 포털에는 패널 대화 열람 화면이 없다 — 앱 TargetPage 가 앱 DB 로 그린다(§8.2.4).

### 8.1.5 포털이 두지 않는 것(A 계획에서 이동·폐기)

`/risk-review/*` 라우트 4개 · `pages/risk/{RiskHomePage, ProjectPage, SnapshotPage, ComparePage, TargetPage}` · `components/{SameAsResolver, …}` · `api/risk.api.ts` · `useRiskEnabled()` 훅 → 앱 `frontend/`(§8.2.4). `backend/app/risk/` 패키지 · `/api/risk/*` 라우트 · Settings 14 필드 · `main.py` register/lifespan 4줄 · `data/risk_review.sqlite` → 앱(§8.2). `<ChatProvider serverKind="risk-review">` 재사용 계획 폐기(앱은 포털 컴포넌트를 import 할 수 없고 conv_store 를 읽지 않는다). 포털 `.env` · `routes.env` · nginx 변경 없음(`/apps/` → Caddy, `/heax-hub/` strip, `/agent/` 스트리밍 설정이 이미 있다).

## 8.2 앱 hwax_risk(리포 `HWAXRisk`)

### 8.2.1 리포 구조(`thermal_shock_mcp` 골격 복제 + `fastapi_react` 스택 계약)

`ThermalShockMCP` 의 `app/{main,config,mcp_server}.py` 골격과 `HEAX_DATA_DIR` 폴백 규칙(config.py:13-38)을 복제하되, UI 를 함께 싣기 위해 `fastapi_react` 스택(HEAXHub `config/stacks.yaml:72-88`, SIF 정의 `backend/app/services/sif_templates/fastapi_react.def`)이 요구하는 저장소 루트 레이아웃 `backend/` + `frontend/` 를 따른다. 파일별 역할은 §0.4.1 이 정본이고 여기서는 배치만 적는다.

```
HWAXRisk/
├── .portal/manifest.yaml                 # §8.2.2 정본(HEAXHub integrations/hwax-risk/.portal/manifest.yaml 과 동일 내용)
├── README.md · checklist.md · context-notes.md
├── backend/
│   ├── pyproject.toml                    # fastapi · uvicorn[standard] · 'mcp>=1.10,<2' · pydantic · httpx, packages.find include app*
│   ├── app/
│   │   ├── main.py                       # FastAPI app — 등록 순서 §8.2.10
│   │   ├── config.py · identity.py · risk_store.py
│   │   ├── ir_builder.py · sameas.py · diff.py · state.py · render.py · taxonomy.py
│   │   ├── planner.py · runner.py · registry.py · narrative.py · character.py
│   │   ├── ra_client.py · adh_client.py · routes.py · mcp_server.py · export.py
│   │   ├── adapters/{base,registry,mcad,dyna,ecad_stub,ecad}.py
│   │   ├── assets/{taxonomy,character-vocab,character-seed-rules,adjacency,rules-seed,seat-contract}.v1.json
│   │   └── schemas/{rr_ir,rr_state,rr_diff,risk_spec,seat_opinion}.v1.json
│   ├── scripts/{bootstrap_ra_ontology,bootstrap_adh}.py   # 실행자 셸 전용 — 앱 런타임이 부르지 않는다
│   └── tests/  (+ golden/sif-e2e.ir.json, fixtures/)
└── frontend/
    ├── package.json · pnpm-lock.yaml · vite.config.ts(base './') · tsconfig.json
    └── src/{App.tsx, api/risk.api.ts, pages/*.tsx, components/*.tsx}
```

SIF 안 경로는 `/app/backend`(`pip install -e`)·`/app/frontend/dist`(`pnpm build`) 이고 `main.py` 의 정적 디렉터리는 `main.py` 기준 `../../frontend/dist` 라 리포 로컬 실행과 SIF 에서 같다. 무거운 의존성이 없으므로 `backend/scripts/heaxhub-build.sh` 훅은 두지 않는다. `source.url` 은 GitHub `squall321/HWAXRisk` 다(`file://` dev 경로는 cae00 스캔 fetch 실패 메일을 반복시켜 쓰지 않는다, §0.4.1). 모든 신규 소스 파일의 첫 줄은 한국어 역할 주석이다.

실존 스캐폴드 대조(2026-08-31, §10.8 #28). `/home/koopark/claude/HWAXRisk`(커밋 0건)는 루트 `app/` + `pyproject.toml` + `tests/` + `docs/*.v1.json` 과 `build.stack fastapi`(`app/static/index.html` 플레이스홀더, `mount('/', mcp_app)`)로 시작했다. #28 기본값 (i) 은 P0 착수 시 위 레이아웃으로 이동한다 — `app/`→`backend/app/`, `pyproject.toml`→`backend/pyproject.toml`, `tests/`→`backend/tests/`, `docs/*.v1.json`→`backend/app/assets/`(package-data), `frontend/` 신설, 매니페스트 `build.stack fastapi_react`. (ii) 를 고르면 P0 는 루트 `app/` + `fastapi` 를 유지하고 SPA 가 들어오는 P1 착수 시 같은 이동을 한다 — 그 동안 이 문서의 `backend/app/…`·`backend/tests/…`·`backend/scripts/…` 경로는 `backend/` 접두를 뗀 경로로 읽고, `main.py` 의 정적 디렉터리는 `app/static/`(플레이스홀더 `index.html`)이며, P0 통과 기준 (11) 의 앱 `pnpm build` 와 SettingsPage 는 P1 로 미룬다(`PUT /api/me/portal-pat` 는 REST 만으로 (17) 을 통과시킨다). 어느 쪽이든 §9.1 A-δ 의 코드 델타(`/mcp` 서브마운트 + 마지막 `/` 정적 마운트 · `identity.py` 되묻기 · MCP 6종 시그니처 · `_schema_migrations` · 매니페스트 company/2 GB/`launch.env`/`/api/health` · REST prefix `/api` · DB 파일명 `risk_review.db`)는 P0 착수 즉시 적용한다.

### 8.2.2 매니페스트 전체(`.portal/manifest.yaml`, 등록 사본 HEAXHub `integrations/hwax-risk/.portal/manifest.yaml`)

```yaml
schema_version: 2
id: hwax_risk
name: HWAX Risk Review
version: 0.1.0
owner: cae-automation
status: beta
description: 설계 IR 스냅샷·diff 위에서 HW/XD 전문가 패널이 리스크·개선·성격을 판정하고 등록부로 누적하는 심사 앱
app_type: web_app
execution_target: linux_runner
build:
  type: python_venv
  stack: fastapi_react
  python_version: "3.12"
launch:
  mode: service
  health_check:
    type: http
    path: /api/health
  restart_policy:
    policy: on_failure
    max_attempts: 3
  env:
    HWAXRISK_DATA_DIR: /data
    PYTHONNOUSERSITE: "1"
permissions:
  visibility: company
resources:
  cpu: 1
  memory_gb: 2
  gpu: false
source:
  type: git
  url: https://github.com/squall321/HWAXRisk.git
  ref: main
mcp:
  expose: true
  path: /mcp
  transport: streamable_http
  description: 리스크 심사 등록부·스냅샷·diff 조회와 패널 결과 회수(risk_get_brief·risk_submit_panel_result). 에이전트 등록 예) claude mcp add --transport http hwax-risk <포털베이스>/apps/hwax_risk/mcp
  allowed_groups: []
```

값 근거. `status: beta` 는 MCP 레지스트리 노출 조건(`beta|stable`, mcp.py:34)이면서 익명 통과(COMPANY+STABLE, authz.py:109-117)를 막는다. `visibility: company` 인 이유는 `team` 이 owner(seed admin)와 포털 SSO 사용자(`organization=''`, portal_sso.py:148)의 `organization` 일치를 요구해 카탈로그·레지스트리에서 통째로 안 보일 수 있기 때문이다(permission_service.py:43-60). `launch.env` 는 평문(git)이라 비밀이 아닌 값만 둔다. 루트 `mcp` 키와 `source.ref` 키는 `manifest.schema.v2.json` 에 없지만(루트·`source` 모두 `additionalProperties:false` — 엄격 검증 시 정확히 이 2건, `tags` 는 루트 스키마에 있어 통과) 스캐너는 `validate_manifest` 를 부르지 않고(`manifest_validator.py:41`, 호출 0건) `thermal_shock_mcp`·`materialtwin-web` 도 같은 형태로 등록돼 있다. `version` 문자열을 올리면 새 AppVersion 이 생긴다. 이름 대응(디렉터리 `hwax-risk` = SIF `hwax-risk.sif` = workspace, `id: hwax_risk` = `/apps/hwax_risk` = state 파일 = 인스턴스 `heax_app_hwax_risk`)은 §0.1.6 표가 정본이다.

### 8.2.3 FastAPI 라우터 — REST 계약(`routes.py`, prefix `/api`, 앱 base `/apps/hwax_risk/api`)

호출 형식·인증은 §0.5.1. 모든 핸들러는 `Depends(identity.current)`(§8.2.8)로 `Identity` 를 받고, 쓰기(POST/PUT)는 `anonymous=false` 를 요구하며(아니면 401), 모든 쿼리는 `owner_sub = identity.email` 로 좁힌다(`visibility='org'` 행만 예외). A 계획의 경로표를 prefix 만 옮겨 그대로 두고 신규 6행(`/health · /me · /me/portal-pat · /targets/{key}/resync · /export · /import`)을 더했다.

| 메서드·경로 | 요청 | 응답 | 오류 |
|---|---|---|---|
| `GET /health` | (익명 허용, forward_auth 뒤라 실제로는 인증 사용자 또는 HEAX 헬스 프로브) | `{ok: true, app_version, schema_version}`(§5.2.5 (6)) | DB 쓰기 불가·마이그레이션 불일치는 기동 실패라 응답 자체가 없다 |
| `GET /me` | | `{email, display_name, role, organization, anonymous, portal_pat{registered, email, groups[], exp} \| null, box{hostname, secrets_valid}}` — PAT 값은 돌려주지 않는다 | |
| `PUT /me/portal-pat` | `{pat: '<포털 PAT>' \| null}` — null 은 삭제 | `{registered, email, groups[], exp}` | 422 `pat_invalid`(서명 검증은 포털 몫 — 앱은 `GET {HWAXRISK_PORTAL_BASE}/agent/conversations?limit=1` 를 그 Bearer 로 호출해 200 이 아니면 거부) · 422 `pat_email_mismatch`(클레임 `email` ≠ `identity.email`) · 422 `pat_audience`(`aud` 에 `mcp-gateway` 없음 또는 `scope≠api`) · 422 `pat_expiring`(`exp − now < 86400`) |
| `POST /projects` | `{code≤40, name≤200, stage?, predecessor_project_id?, adh_scope{team, group}}` | `rr_projects` 행 | 409 `UNIQUE(owner_sub, code)` |
| `GET /projects` | | `{projects[{id, code, name, stage, sources[{kind, app_key, status}], last_snapshot_at, open_targets, coverage_pct, level}]}` | |
| `GET /projects/{id}` | | `{project, sources, snapshots[헤더], targets[헤더], jobs[{id, kind, state, progress}], character_top_tags}` | 404 |
| `POST /projects/{id}/sources` | `{kind, app_key, ref, bridge_declared?}` | `{ok, probe{reachable, detail, capture_mode}}` | 422 kind∉4종 |
| `POST /projects/{id}/snapshots` | `{kinds[], report_ids?, detect_result_file_id?}` | 202 `{job_id}` → 완료 시 `{snapshot_id, ir_hash, gates, degraded}` | 409 같은 `(project_id, ir_hash)` 는 기존 snapshot_id 반환(200) |
| `GET /snapshots/{id}?part=ir\|state\|nodes\|edges\|calls` | | part 별 JSON(`ir` 는 16 MB 초과 시 `calls` 제외 스트리밍) | 404 |
| `GET /snapshots/{id}/rule_hits` | | `rule_hits[]` | |
| `POST /projects/{id}/dims` | `{name, kind, unit, extractor}` | `rr_dim_defs` 행(name 은 `rr_dim_vocab` 에 없으면 candidate 로 등록) | 422 extractor 구문 |
| `GET /sameas?base=&target=` | | `{pairs[{a, b, method, score, status}], pending_n, G2}` | |
| `POST /sameas/decide` | `[{a, b, decision: confirm\|reject, scope: intra\|pair\|global}]`(same-as, §2.6.2 7단계) 또는 `[{decision: merge_key\|rename_key\|confirm_key\|unmerge_key, ckey_from?, ckey_into?, ckey?, display_name?}]`(ckey 원장, §2.7.3 — `unmerge_key` 는 `code:pair_correspondence` 자동 승계 행 되돌리기 포함) — 한 배열에 섞어 보낼 수 있다 | `{updated, G2}` | 422 decision 어휘 밖 |
| `PUT /projects/{id}/iface-ledger` | `[{pair_key, kind_override, status, note}]` | 확정 원장 | |
| `POST /diffs` | `{base_snapshot_id, target_snapshot_id}` | `{diff_id, counts, comparability}` | 409 `{gates}`(G6 fail = `blocked`) · 200 기존 diff(UNIQUE 쌍) |
| `GET /diffs/{id}?part=diff\|summary\|events` | | JSON | |
| `POST /targets` | `{kind: snap\|diff, ref_id, consent: true}` — `rr_targets.principal_json` 에 `Identity` 스냅샷 저장 | `{target_key, roster_size, deferred, tier_plan, cost_estimate}` | 422 `consent≠true` · 409 이미 열린 타깃 |
| `POST /targets/{key}/jobs` | `{tier: A\|B\|C, concurrency≤2, modifiers?, user_memo?, consent?}` | `{job_id, panels_planned, llm_calls_estimate, credential: service\|owner}` | 422 Tier C 는 `consent:true` 필수(§6.9 명시 승인제) · 422 `reason=pat_unavailable`(러너 자격 (a)(b) 둘 다 없음, §6.7 3단계) · 422 `reason=tier_a_web_only`(MCP 경로가 Tier A 요청, §8.3.4) |
| `POST /jobs/{id}/pause\|resume\|cancel` | | `{state}` (패널 경계 반영) | |
| `GET /targets/{key}/coverage` | | `{job, roster_size, by_domain[15][status→n], unseated_n, level, close_level}` | |
| `GET /targets/{key}/registry` | | `rr_registry[]` + verdict 후보 | |
| `GET /targets/{key}/panels` | | `rr_panels[]`(conv_id · report_id · quality_json) | |
| `GET /targets/{key}/brief?tier=` | | `{panels[{panel_id, seats_json, delib_opts}], evidence E0~E9, budget{bytes, dropped}}` — MCP `risk_get_brief` 와 같은 함수 | 422 `reason=tier_a_web_only` |
| `PUT /targets/{key}/verdict` | `{verdict, note}` | 사람 확정 | |
| `PUT /registry/{cluster}/status` | `{status: verified\|dismissed\|mitigated, evidence_ref?, note?}` | verified·dismissed 는 라벨 생성(`source=manual`, §7.6 5경로), mitigated 는 사람 표기만(§4.7.1) | 422 status 어휘 밖 |
| `POST /panels/{id}/complete` | `{engine: mcp\|web, conv_id?, decision_text, turns[], report_id?, events?[], model?}` — `model?` 는 호출자 신고 모델명(`rr_panels.model_json{captured:'caller_reported'}`, 없으면 `'unknown'`, D6 §6.11), `events[]` 는 러너가 아닌 호출자(L2 오케스트레이터·재제출, §6.11)가 SSE 를 읽으며 캡처한 압축 로그 `[{kind: 'status'\|'evidence'\|'personas', step?, tool?, source?, personas?}]`, ≤400건(초과분은 앞 400건만 받고 응답에 `events_truncated=true`), 문자열 필드 각 ≤200자 | `{parsed, findings_n, coverage_updated, attribution_rate}` — 파서는 앱 단일 구현(`narrative.py`), MCP `risk_submit_panel_result` 와 같은 함수. `events[]` 가 있으면 §6.7 7단계 정규식으로 `tool_calls_n/ok`·`used_tool`·`extra_seats` 를 계산하고, 없으면 `engine='mcp'` 는 `tool_calls_n=null`·`used_tool=null`(§6.11 분모 제외), `engine='web'` 재제출은 기존 값 유지 | 409 패널이 `running`(또는 재제출 대상 `done`·`error`)이 아님 · 422 `events[]` 항목 형식 위반 |
| `POST /targets/{key}/resync` | (소유자 전용) | `{ra: pending, adh: pending}` — `external_sync` 를 `pending(attempts=0, next_at=0)` 으로 되돌린다(§5.5.3) | 403 소유자 아님 |
| `GET /projects/{id}/character` · `/similar` | | 프로파일 3층 · 출처별 top-k | |
| `GET /refs/{ref}` | §0.2.1 문법 | `{ref_type, resolved, payload}` — `tool:conv:<cid>#<idx>` 는 러너 자격 PAT 로 포털 `GET /agent/conversations/{cid}` 를 읽어 해석 | 404 dangling |
| `GET /precedents?diff_id=` | | `rr_delta_priors` 수치만 | |
| `POST /targets/{key}/refresh_roster` | | `{added_pending}` (기존 종결 행 불변) | |
| `GET /meta/taxonomy` · `/adapters` · `/metrics` | | 택소노미 · 발견된 소스 앱(`apps[{app_key, kind, tools_ok, choices[]}]`) · 지표 | |
| `GET /export?since=<epoch>` | (소유자 행만) | JSONL 스트림 — 첫 줄 `{schema_version, app_version, origin}`, 이어서 §5.2.2 A→H 표 순서로 `{table, row}` 줄. 살림 표(`_schema_migrations`·`_user_credentials`)는 제외. 같은 내용을 `$HEAX_DATA_DIR/exports/<ts>.jsonl` 에도 남긴다(§5.2.5) | |
| `POST /import` | JSONL 본문(P1+, `export.py`) | `{inserted, merged, skipped, conflicts[]{table, key, local, incoming}}` — §4.7.1 등록부 병합·§2.10 원장 재적용 규칙 재사용, 사람 확정이 자동을 이김 | 409 `schema_mismatch`(헤더 `schema_version` ≠ `PRAGMA user_version`) |

`GET /meta/adapters` 의 `choices[]` 는 소스 카드 선택지(StepForge `list_projects`, DynaForge `list_sessions → list_session_files`, `list_reports`)를 읽기 도구로만 채운 것이다. `rr_targets.principal_json` 은 신원 스냅샷일 뿐 러너가 이것으로 PAT 를 발급하지 않는다(§6.7 3단계 — 러너 자격은 (a)(b) 뿐).

### 8.2.4 SPA(React/Vite, `frontend/`)

- 빌드·경로. Vite `base: './'`, fetch 는 `'api/…'` 상대경로(`fetch('api/health')` → `/apps/hwax_risk/api/health`). 라우터는 `HashRouter` 다 — Caddy 가 `/apps/hwax_risk/` 접두를 떼고 `main.py` 가 `StaticFiles(html=True)` 로 `index.html` 만 돌려주므로 딥링크는 `/apps/hwax_risk/#/targets/<key>` 형식이어야 새로고침에 안전하다(BrowserRouter 용 catch-all 라우트를 두지 않는다). 라우트 5개 — `#/`(RiskHomePage) · `#/projects/:id`(ProjectPage, `?snapshot=` 이면 같은 화면에 SnapshotPage) · `#/compare`(ComparePage, `?base=&target=`) · `#/targets/:key`(TargetPage, `:key` 는 `snap:<id>`/`diff:<id>` URL 인코딩) · `#/settings`(SettingsPage).
- API 클라이언트 `src/api/risk.api.ts` — §8.2.3 을 1:1 로 감싸고 SSE 는 쓰지 않는다. 진행 상태는 폴링 — 스냅샷 잡 `GET api/projects/{id}`(`jobs[]`), 배치 잡 `GET api/targets/{key}/coverage`(`job`), 주기 5 s, 화면을 떠나면 중단. 오류 규약 — 401 → "포털 메뉴 '리스크 심사' 에서 HEAX 로그인을 먼저 하세요" 안내(앱에는 로그인 화면이 없고 리다이렉트도 없다), 404 → 소유자 불일치, 409 → 게이트/중복, 422 → 검증 메시지 표시.
- 그래프 렌더는 앱 번들의 `mermaid` npm 의존으로 한다(포털 `components/chat/renderers` 는 다른 리포라 재사용하지 않는다). 지표 차트(P6 `GET api/meta/metrics`)는 dataviz 규약을 따르고 TargetPage 하단 '품질' 카드에 둔다.

| 화면 | 구역(위→아래) | 호출 API(`api/` 상대) | 쓰기 행위 |
|---|---|---|---|
| `RiskHomePage` | 과제 카드 그리드(code · name · stage · 소스 3 아이콘 상태 · 최근 스냅샷 시각 · 열린 타깃 수 · 커버리지 % · level 배지) · 상단 탭 과제/비교(diff 목록)/타깃/보고서 · '과제 등록' 폼(code ≤40 · name ≤200 · stage 정규식 `(pre\|dv\|pv\|pra\|mp)([123r])?` · predecessor_project_id 선택 → RA `revision_of` · adh_scope{team, group} 사용자 입력 1회, 자동 채움 없음) · 상단 배너: `GET api/me` 의 `box.secrets_valid=false` 면 "이 박스의 자격이 없습니다 — 설정" 링크 | `GET/POST projects` · `GET me` | 없음 |
| `ProjectPage` | 헤더(과제 · 계보 링크 · external_sync 배지) · 소스 카드 3장(mcad/dyna/ecad — `unlinked → linked → unreachable`, 연결 시 probe 결과 표시; ecad 는 어댑터 미발견이면 '연결 대기(스텁)') · '스냅샷 동결' 버튼(kinds 체크 · report_ids · detect_result_file_id 입력) → 잡 진행바 → 완료 시 `?snapshot=` 로 `SnapshotPage` · 스냅샷 목록 · dims 정의 편집(`rr_dim_defs`) · iface-ledger 편집 · 성격 프로파일(L0 seed · L2 panel · confirmed 3층 나란히, P5 에서 confirm 버튼) · 유사 과제(출처별 top-k, 섞지 않음) | `GET projects/{id}` · `POST projects/{id}/sources` · `POST projects/{id}/snapshots`(202) · `POST projects/{id}/dims` · `PUT projects/{id}/iface-ledger` · `GET projects/{id}/character` · `GET projects/{id}/similar` · `GET meta/adapters`(소스 선택지 `choices[]`) | 없음. `volume`/`material` 이 전부 null 이면 배너 '재파싱 필요' 와 StepForge 앱 링크(같은 오리진 `/apps/step_forge/`, 새 탭)만 보여주고 앱이 `run_job` 을 호출하지 않는다 |
| `SnapshotPage` | 개요(ir_hash · 소스 · captured_at · counts · missing 플래그) · 게이트 표(G1~G7, `GateBanner`) · 노드 표(nid · name · ckey · dn · geom_fp · flags, 검색) · 엣지 표(eid · kind · status · min_gap · penetration_depth 하한 표기) · mermaid(StepForge EDGE_STYLE 규약, 300 엣지 초과 시 상위 서브어셈블리만) · dims_named 표 · rule_hits 표(`{rule, severity, pass, found, why_it_matters, fix_hint}`) · character_seed 칩 · warnings · 호출 로그 목록(`tool:<call_id>`) · '단발 심사 열기'(포털 `/deliberate` 를 새 탭으로 열고 E0·E1 텍스트를 클립보드에 복사 — 포털 startHandoff 를 앱이 부를 수 없다, P1) · '타깃 만들기'(`POST targets {kind:'snap'}`) | `GET snapshots/{id}?part=ir\|state\|nodes\|edges\|calls` · `GET snapshots/{id}/rule_hits` · `GET refs/{ref}` | 없음 |
| `ComparePage` | base/target 선택(과제 → 스냅샷, 같은 과제 또는 계보 과제 우선 표시) · `SameAsResolver`(자동 매칭 표 method · score · status, 행별 confirmed/rejected, '자동 매칭 전부 수용' 은 score ≥ 0.9 만 일괄 confirmed 로 두고 `decided_by=owner_sub` 기록) · `GateBanner`(G6 fail → `blocked=true` 로 'diff 생성' 비활성, G2 fail → '의미층 차단' 표기, 나머지 표기 강제) · 'diff 생성' · `DiffView` 3층(구조 · 파라메트릭 · 의미, before/after mermaid, `summary_text` 각 줄 `[c:]` 각주 클릭 → 항목 하이라이트, 선례 패널 `GET precedents?diff_id=` P5) · '타깃 만들기'(`POST targets {kind:'diff', consent:true}`) | `GET sameas?base=&target=` · `POST sameas/decide` · `POST diffs`(409 `{gates}`) · `GET diffs/{id}?part=diff\|summary\|events` · `GET precedents` · `POST targets` | 없음(StepForge `set_interface/confirm_interfaces` 호출 없음 — 확정은 앱 원장에만) |
| `TargetPage` | 헤더(target_key · 과제 · ir_hash · level `C0…C3`/`C2(closed)` · verdict_final · `external_sync{ra, adh}` 배지 + '재동기' 버튼(소유자) · superseded_by 링크 · **'미착석 N명(C3 미달)' 배지 상시**) · `CoverageHeatmap`(행 = 15 도메인, 열 = 커버리지 10 상태 카운트, 셀 클릭 → 좌석 목록 · opinion 링크 · `carried → pending` 되돌리기 · `skipped(reason)` 입력) · `PanelRunner`(Tier A/B/C · modifiers · user_memo · 예상 패널 수 · LLM 호출 추정 · 시작/일시정지/재개/취소 · 일일 상한 잔량 · concurrency ≤2 · 자격 표시 `credential service\|owner` 와 owner PAT 미등록 시 "DynaForge 사용자 데이터는 서비스 시야" 경고) · 패널 목록(P{n} · engine `web\|mcp` · `call_path` · tool_mode · status · quality.flag 칩 · 기록 열기(`PanelTranscript`) · RA 보고서 링크 · conv_id 표기) · 등록부 표(`cluster_key` · mechanism · subject · severity · judgement · evidence_grade · precedent · support/contested · status, 필터 severity/domain/direction/status, 행 클릭 → cites → `GET refs/{ref}` 팝오버, status 변경) · verdict 확정(후보 표시 → 사람이 `verdict_final` 확정, 자동 승인 없음) · `RecallPreview`(`GET brief?tier=` 의 E0~E9 를 출처 태그와 함께, **항목 제외만 가능·추가 불가**) · 통합 보고서 링크(v1/v2/v3 RA report_id) · '로스터 갱신' | `GET targets/{key}/coverage\|registry\|panels\|brief` · `POST targets/{key}/jobs` · `POST jobs/{id}/pause\|resume\|cancel` · `PUT targets/{key}/verdict` · `PUT registry/{cluster}/status` · `POST targets/{key}/refresh_roster` · `POST targets/{key}/resync` · `GET refs/{ref}` | 없음(원장 상태 변경은 전부 앱 DB) |
| `SettingsPage` | 내 신원(`GET me`) · 포털 PAT 등록/삭제(`PUT me/portal-pat`, 발급 안내 링크 `<포털>/tokens` — aud 에 `mcp-gateway` 포함·ttl ≤365 일·scope api) · 등록된 PAT 의 email·groups·exp 표시(값은 표시하지 않는다) · 이 박스 상태(`box.hostname`, `secrets_valid`, §5.2.5 (5) 불일치 경고) · 동의 문구 고정 표시 "등록한 PAT 는 내 타깃의 무인 패널이 소스 앱을 읽을 때만 쓰이고(읽기 전용) 심의 결정문은 내 이름의 포털 대화로 저장됩니다" | `GET me` · `PUT me/portal-pat` | `_user_credentials` 1행 |

부품 `src/components/{SameAsResolver, GateBanner, DiffView, PanelRunner, PanelTranscript, RecallPreview, CoverageHeatmap}.tsx` 는 위 표의 구역과 1:1 이다. `PanelTranscript` 는 앱 DB 의 `rr_seat_opinions.turns`(좌석·라운드·발언 발췌)·`rr_panels.decision_text`·`risk_spec_json` 표를 그린다 — 포털 `DelibView` 를 재사용하지 않고 conv_store 를 읽지 않는다.

화면 상태 어휘(배지 = 저장 값과 같은 문자열).

| 대상 | 값 |
|---|---|
| 소스 카드 | `unlinked · linked · unreachable` |
| 스냅샷 잡 | `queued · running · done · failed` |
| 타깃 level | `C0 · C1 · C2 · C2(closed) · C3` + 속성 `superseded_by` |
| 커버리지 | `pending · assigned · running · done · done_weak · abstain · failed · skipped · deferred · carried` |
| 패널 | `planned · running · done · error` + `engine web\|mcp` + `call_path portal\|agent_direct` + `tool_mode tools\|evidence_only` + `credential service\|owner` + `quality.flag[]` |
| 배치 잡 | `queued · running · paused(reason) · cancelling · cancelled · completed · failed` + `error pat_unavailable` 표기 |
| external_sync | `ra: pending\|done\|unavailable` · `adh: pending\|done\|unavailable` |
| 등록부 | `open · verified · dismissed · mitigated · superseded` |

헌법이 화면에 나타나는 자리.
- 브리프(`RecallPreview`)는 제외만 가능하고 추가할 수 없다 — 사용자 결론 주입 차단(P1).
- 코드 생성 문장(`summary_text` · rr_state 요약 · E0~E9)은 판단어 린터를 통과한 것만 화면에 나오고, 린터 실패는 '요약 생성 실패' 로 표시된다.
- 앱 화면에는 소스 앱 쓰기 버튼이 없다. StepForge parse/detect · DynaForge `run_operation(modelmeta, detect)` 는 각 앱 화면에서 사용자가 실행하고, 앱은 그 산출(`detect_result_file_id` · report_ids)을 **지정**만 받는다.
- verdict 는 등록부 집계로 '후보' 만 보여주고 사람이 확정한다. 자동 승인·자동 배포 없음.

### 8.2.5 MCP 서버 `hwax-risk`(`mcp_server.py`, 앱 내부 `/mcp` → `/apps/hwax_risk/mcp` → 게이트웨이 `heax-hwax_risk`)

- 구성. `FastMCP('hwax-risk', transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))`(기본 `streamable_http_path='/mcp'`, loopback+Caddy 전제, LaminateAnalyzerMCP `mcp_server.py:29-33` 선례) 의 `streamable_http_app().routes`(실체는 `Route('/mcp')` 하나) 를 `main.py` 가 메인 라우터에 이식하고(`mcp._session_manager = None` 선행, MaterialTwinWeb 선례) lifespan 에서 `async with mcp.session_manager.run()` 을 연다. `app.mount('/mcp', …)` 는 슬래시 없는 `/mcp` 에 307 을 내고(D7 실측), thermal 방식 `mount('/', mcp_app)` 은 SPA 마운트를 삼키므로 둘 다 쓰지 않는다(§0.4.1). `mcp>=1.10,<2` 핀.
- 도구 6종(§0.5.2 시그니처, 등록부 조회 = `risk_get_registry`).

| 도구 | 인자 | 응답·상한 | 쓰기 |
|---|---|---|---|
| `risk_get_snapshot` | `snapshot_id, part ∈ ir\|state\|nodes\|edges\|calls` | part 별 JSON, `nodes` 는 상위 500 + `truncated`, `calls` 는 헤더만 | 아니오 |
| `risk_get_diff` | `diff_id, part ∈ diff\|summary\|events` | JSON, `events` ≤500 + `truncated` | 아니오 |
| `risk_get_registry` | `target_key, status?, severity?, domain?` | `rr_registry` 행 ≤200 + verdict 후보 | 아니오 |
| `risk_claims_for_ref` | `ref`(§0.2.1 문법) | `rr_claim_refs` 조인 ≤100 | 아니오 |
| `risk_get_brief` | `target_key, tier='B'` | `GET /api/targets/{key}/brief?tier=` 와 같은 함수 — `{panels[{panel_id, seats_json, delib_opts}], evidence E0~E9, budget}`. `tier:'A'` 는 `{error:'tier_a_web_only'}` | 아니오(패널 행 `planned` 생성은 포함 — 편성은 결정론이라 멱등) |
| `risk_submit_panel_result` | `panel_id, engine ∈ mcp\|web, decision_text, turns[], report_id?, actor`(이메일)`, model?`(호출자 신고 모델명, D6) | `POST /api/panels/{id}/complete` 와 같은 함수. `actor` 는 `quality_json.actor` + `actor_verified:false` 로만 기록, `owner_sub` 는 패널 행 승계(§6.11) | 예 |

- 신원. 게이트웨이 경유 호출은 heax 서비스 PAT(admin) 로 도달하고 최종 사용자·그룹은 오지 않는다. 에이전트 직접 등록(`claude mcp add --transport http hwax-risk <포털베이스>/apps/hwax_risk/mcp`, 헤더 `Authorization: Bearer heax_pat_…`)도 Caddy forward_auth 만 통과할 뿐이다. MCP 경로 신원은 §6.11 규칙(`actor`, 미검증) 하나로 통일하고 `identity.py` 는 REST 에만 붙는다.
- 게이트웨이 흡수(설정·코드 변경 0). 앱이 기동해 state 파일이 생기고 매니페스트 `status beta`·`mcp.expose` 가 맞으면 heax `GET /api/v1/mcp/servers`(mcp.py:51-98) 가 `{id:'hwax_risk', path:'/apps/hwax_risk/mcp', transport, allowed_groups:[]}` 를 내고, 게이트웨이 `_discover_heax`(gateway.py:204-258)·revive 루프가 백엔드 `heax-hwax_risk`(url = `heax_registry.base` + path, 헤더 = heax 서비스 PAT)를 만든다. `allowed_groups: []` 라 전체 공개이고 `/tools-map` 에 `risk_*` 6종이 보인다. 게이트웨이 `heax_registry.token` 계정이 hwax_risk 를 볼 수 있어야 하는데 `visibility: company` 라 활성 사용자면 충분하다. `per_user_sso` 에는 등록하지 않는다(사용자 위임 불필요 — 쓰기는 `actor` 표기로 충분).

### 8.2.6 Settings(`config.py`, env 접두 `HWAXRISK_`)

Settings 속성명은 A 계획의 `risk_*` 를 그대로 두고 env 는 `HWAXRISK_<대문자>` 로 읽는다(§0.5.3). `pydantic-settings` 없이 `os.environ` 직접 파싱(의존성 최소).

| env | 속성 | 기본 | 용도 |
|---|---|---|---|
| `HWAXRISK_DATA_DIR` | `data_dir` | (매니페스트 `/data`) | 데이터 루트. 우선순위 `HWAXRISK_DATA_DIR > HEAX_DATA_DIR > <리포>/data`, 기동 시 `mkdir -p` + `W_OK` 검사 실패면 기동 중단(§5.2.5 (1)) |
| `HWAXRISK_PORTAL_BASE` | `portal_base` | `http://127.0.0.1:5283` | 포털 nginx 오리진 — `/agent/chat`·`/agent/conversations`(§6.7) |
| `HWAXRISK_HEAX_API` | `heax_api` | `http://127.0.0.1:4040` | heax 백엔드 — `/api/v1/auth/me`(§8.2.8)·`/api/v1/mcp/servers`(§8.2.11) |
| `HWAXRISK_HEAX_BASE` | `heax_base` | `http://127.0.0.1:4180` | Caddy — StepForge REST `/apps/step_forge/api`(§8.2.11) |
| `HWAXRISK_GATEWAY_MCP` | `gateway_mcp` | `http://127.0.0.1:9110/mcp` | 게이트웨이 MCP(RA 쓰기·좌석 조회·소스 읽기), `/tools-map` 은 같은 오리진 |
| `HWAXRISK_AIDH_BASE` | `aidh_base` | `http://127.0.0.1:8001` | AIDataHub REST(§5.4.2) |
| `HWAXRISK_AGENT_URL` | `agent_url` | `''`(폴백 꺼짐) | §6.7 (B) 폴백 — 같은 박스에서만 `http://127.0.0.1:9009` |
| `HWAXRISK_ROSTER_DOMAINS` | `risk_roster_domains` | 15 도메인 csv | 로스터 도메인 |
| `HWAXRISK_ECAD_DOMAINS` | `risk_ecad_domains` | `pcb,pwr,rf,soc,passive,mem` | ecad_absent 시 deferred |
| `HWAXRISK_ADJACENCY` | `risk_adjacency` | `''` → `assets/adjacency.v1.json` | counter 석 인접 표 |
| `HWAXRISK_CONCURRENCY` | `risk_concurrency` | `2` | 동시 패널(타깃 다를 때만) |
| `HWAXRISK_DAILY_PANEL_CAP` | `risk_daily_panel_cap` | `24` | 일일 패널 상한(앱 프로세스 로컬 날짜 경계) |
| `HWAXRISK_DEFAULT_CLOSE_LEVEL` | `risk_default_close_level` | `C2` | 기본 마감 레벨 |
| `HWAXRISK_CARRIED_DAYS` | `risk_carried_days` | `90` | carried 유효기간 |
| `HWAXRISK_PANEL_LLM_CAP` | `risk_panel_llm_cap` | `120` | 사전 예산 게이트 |
| `HWAXRISK_PROMOTE_DISTINCT_MODELS` | `risk_promote_distinct_models` | `1` | §7.4 승격 선택 가드(D6) — 2 이상이면 candidate 조건에 '서로 다른 `model` ≥ N 에서 재현' 추가, 1 이면 가드 없음 |
| `HWAXRISK_ADH_TEAM` · `HWAXRISK_ADH_GROUP` | `adh_team` · `adh_group` | `None` | 사용자 확인값 없을 때 폴백 없음 — None 이면 import 를 `adh=unavailable` 로 미룬다 |

HEAX 가 강제하는 env(앱이 덮을 수 없음, integration_launcher.py:321-353) — `PORT · HOST=127.0.0.1 · HEAX_DATA_DIR · ROOT_PATH=/apps/hwax_risk`(+`BASE_URL_PATH·NEXT_PUBLIC_BASE_PATH·SCRIPT_NAME·BASE_PATH·HEAX_BASE_PATH` 동의어, `DASH_URL_BASE_PATHNAME`). 앱은 `ROOT_PATH` 를 URL 생성에만 쓰고 라우트는 `/` 기준으로 선언한다. 선택 상속 `LLM_*`·프록시·`SSL_CERT_FILE` 등은 앱이 읽지 않는다(LLM 은 엔진 몫). P0 확인 항목 — dev 런처가 이 앱을 SIF 로 띄우는지 확인한다. 호스트 프로세스로 뜨면 `launch.env` 의 `HWAXRISK_DATA_DIR=/data` 가 호스트 `/data` 를 가리키므로 그 경우 매니페스트에서 그 줄을 빼고 `HEAX_DATA_DIR` 폴백만 쓴다. 폐기 — `risk_review_enabled`(앱 존재가 활성) · `risk_store_path`(파일명 `risk_review.db` 고정) · `ra_admin_pat` · `adh_api_key`(이름 변경, §8.2.7).

### 8.2.7 시크릿(`$HEAX_DATA_DIR/secrets.env`, 0600)

HEAX 통합 앱에 시크릿을 넣는 공식 경로가 없으므로(`secret_manager.inject_for_app` 은 `service_manager` 전용, 스캐너·런처 호출 0건) 앱이 직접 보관한다. 형식은 `KEY=VALUE` 줄(따옴표 없음, `#` 주석 허용), 기동 시 1회 로드(python-dotenv 미사용, 직접 파싱), 회전은 파일 교체 후 앱 재기동이다. 파일이 없으면 앱은 기동하되 `external_sync` 를 `unavailable` 로 시작하고 러너는 잡을 집지 않는다(`rr_jobs.error='pat_unavailable'`).

| 키 | 발급처 | 용도 | 발급 규칙 |
|---|---|---|---|
| `HWAXRISK_PORTAL_PAT` | 포털 `/tokens`(서비스 계정 로그인) | 러너 자격 (a) — `/agent/chat`·`/agent/conversations`·게이트웨이 MCP(RA 쓰기·좌석 조회·DynaForge 읽기 서비스 시야) | aud 에 `mcp-gateway`, scope api, ttl 365 일(무기한 `ttl_days 0` 은 Drive tar 노출 결정 §10 전까지 금지, §5.2.5 (3)). groups 는 소스 앱·RA·AIDataHub 백엔드가 요구하는 그룹 전부 |
| `HWAXRISK_HEAX_SERVICE_PAT` | heax `POST /api/v1/auth/tokens`(서비스 계정 로그인, `heax_pat_…`) | StepForge REST 직접 읽기(`/apps/step_forge/api`)·`/api/v1/mcp/servers` 조회 | StepForge(visibility team)를 볼 수 있는 계정. 앱 코드는 GET 만 낸다(쓰기 메서드 0건, 코드 검사로 보장) |
| `HWAXRISK_AIDH_API_KEY` | AIDataHub 관리자 | `X-API-Key`(REST import·doc_type·agent) | `AUTH_REQUIRED` 값과 무관하게 항상 보낸다 |

앱이 보유하지 않는 토큰 — `GW_TOKEN`(agent-server 전용) · `X-Heax-Gateway-Secret`(게이트웨이·HEAX 전용) · DynaForge `kr_` · RA `rat_`(게이트웨이가 대신 싣는다) · RA 관리자 PAT(`RA_ADMIN_PAT` 는 `bootstrap_ra_ontology.py --base <RA REST 오리진>` 실행자 셸 env 뿐). 러너 자격 (b) 의 사용자 PAT 는 앱 DB 살림 표 `_user_credentials(owner_sub TEXT PRIMARY KEY, portal_pat TEXT NOT NULL, pat_sub TEXT, pat_email TEXT, pat_groups_json TEXT, pat_exp INTEGER, registered_at INTEGER)` 에 둔다 — rr_ 접두 아님, `_schema_migrations` 와 같은 살림 표로 `risk_store.py` 가 `CREATE TABLE IF NOT EXISTS` 로 만들고 export 대상이 아니며, 노출 등급은 `secrets.env` 와 같다(Drive tar 제외 규칙 §10 은 `secrets.env` 와 `risk_review.db` 의 이 표를 함께 다룬다). `origin.json.hostname` 불일치(§5.2.5 (5)) 시 `secrets.env` 와 `_user_credentials` 전부를 무효로 본다.

### 8.2.8 신원(`identity.py`) — `X-Heax-User-*` 를 쓰지 않는 이유와 `/auth/me` 되묻기

사실. Caddy 내부 service 라우트는 `_forward_auth_handler()` 를 `copy_identity=False` 로 세워(proxy_manager.py:141) authz 가 만든 `X-Heax-User-Email/Name`(authz.py:122-125) 이 앱에 복사되지 않고, 클라이언트가 위조해 보낸 동명 헤더는 덮이지 않고 그대로 통과한다. 반면 원본 `Cookie`·`Authorization` 은 업스트림에 그대로 전달된다(:59-61). `copy_identity` 는 proxy 모드 + `launch.portal_auth` 에서만 켜진다(:346-347, DynaForge 선례).

설계(HEAX 무수정).
- `identity.current(request) -> Identity{email(소문자), display_name, role, organization, anonymous: bool, source ∈ bearer\|cookie\|none}`. 토큰 = `Authorization: Bearer` 값이 있으면 그것, 없으면 쿠키 `heax_access_token` 값. 토큰이 있으면 `GET {HWAXRISK_HEAX_API}/api/v1/auth/me` 를 그 Bearer 로 호출해 `{id, email, display_name, role, organization}` 을 얻고(deps.py:25-41 `get_current_user` 는 Bearer 전용 — JWT 와 `heax_pat_` 둘 다 받는다), 응답을 `sha256(token)` 키로 TTL 60 s 캐시한다. `/me` 가 401 이면 앱도 401, 5xx·연결 실패면 503(캐시 히트는 그대로 쓴다) — 이 구분은 P1 쓰기 라우트와 함께 들어간다. **P0(읽기 전용, 커밋 0498839)는 401·불통·토큰 없음 전부 `anonymous`(source none)로 통일하고 불통 결과는 캐시하지 않는다**(D7·앱 context-notes D6). 같은 이유로 `PUT /me/portal-pat` 의 포털 검증 호출 불통은 P0 에서 422 `pat_invalid` 로 보이며, P1 에서 503 `pat_verify_unavailable` 로 분리한다(§8.2.3 오류 표에 추가 예정).
- 토큰이 없으면 `anonymous=true`(visibility company + status stable 일 때만 도달 가능, beta 인 동안은 forward_auth 가 401 로 막는다) — `visibility='org'` 행 읽기만, 쓰기는 401.
- `X-Heax-User-*` 헤더는 어느 경로에서도 읽지 않는다(위조 가능). `owner_sub` 값은 `Identity.email` 이며 §5.2.1 소유권 규약과 같다.
- 대안(미채택, §10) — HEAXHub `proxy_manager.register_app_route/_build_route` 에 `copy_identity` 를 `launch.portal_auth` 게이트로 additive 로 여는 변경. 채택돼도 `identity.py` 의 되묻기가 정본이고 헤더는 보조 확인에만 쓴다.

### 8.2.9 러너(백그라운드 스레드·세마포어·재기동 복구)

`RiskRunner(store, settings)` 는 `main.py` lifespan 이 `start()`/`stop()` 하는 객체이고 스레드 3개를 띄운다 — `panel_loop`(5 s 폴링, `threading.Semaphore(risk_concurrency)`, 타깃당 직렬, §6.7.2 12단계) · `sync_loop`(60 s, §5.5.3 `external_sync` 재시도·`next_at ≤ now` 인 타깃의 op 순서 전송) · `nightly_loop`(60 s 폴링으로 로컬 시각 00:30 경과를 검사해 하루 1회 §7.7 야간 잡 ①~⑧ 을 순서대로 실행 — 각 단계 멱등, 실패한 단계는 다음 단계를 막지 않고, `rr_jobs` 에 행을 만들지 않으며 결과는 앱 로그와 `rr_metrics(dimension=global, metric=nightly_<step>_ok)` 에만 남긴다. 당일 실행 여부는 `rr_metrics(dimension=global, metric=nightly_run_at)` 의 마지막 값으로 판정해 재기동으로 이중 실행하지 않고, 앱이 00:30 을 지나 떴으면 기동 직후 1회 실행한다. 포털에는 야간 잡이 없다 — §0.7 #12). `stop()` 은 `threading.Event` 를 세우고 최대 5 s 만 join 한 뒤 HTTP 스트림을 닫는다. 재기동 복구는 §6.7.2 끝 문단(실행 중 패널 → `error(retry+1)`, 5석 `pending`, 잡 재집기). 러너는 앱 프로세스 하나에만 있고(REST 핸들러·MCP 도구와 같은 프로세스·같은 `RiskStore` Lock), 두 박스 동시 실행 금지는 §5.2.5 (7) ⑥. 러너가 `delib_opts` 에 절대 싣지 않는 키는 §6.6.4(`human_note`·`continue_summary`·`non_negotiables`·`search_sources`·`stop_after_round`·`build_plan`). 포털 대화형 심의 슬롯 점유는 최대 `risk_concurrency`(2) 이며 P4 통과 기준 (7) 이 이를 잰다.

### 8.2.10 헬스·기동 순서·`origin.json`

`main.py` lifespan 순서 — ① `config.py` 데이터 루트 결정·`mkdir -p`·`W_OK`(실패 = 예외로 기동 중단) ② `RiskStore` 생성·`MIGRATIONS` 적용(`pre-migrate-<ts>` 사본, §5.2.5 (6))·살림 표 2 ③ `origin.json` 갱신 `{hostname, app_version, schema_version, written_at}` ④ `secrets.env`·`_user_credentials` 유효성(hostname 일치) 판정 ⑤ `identity` 캐시 초기화 ⑥ `async with mcp.session_manager.run()` ⑦ `runner.start()`. 종료는 역순. 라우트 등록 순서(모듈 import 시) — `/api/health` 및 `/api/*` 라우터 → MCP `Route('/mcp')` 이식(§0.4.1 ②) → 마지막에 `app.mount('/', StaticFiles(directory=<../../frontend/dist>, html=True))`. `GET /api/health` 는 `{ok: true, app_version, schema_version}` 이고 HEAX 헬스 대기 20 s(integration_launcher.py:89-90) 안에 200 이어야 한다 — 마이그레이션이 길면 기동 실패로 보이므로 v1 DDL 적용은 1 s 안에 끝난다(빈 DB). P0 기동 3점 테스트(`backend/tests/test_boot.py`) — `GET /api/health` 200 · `POST /mcp` initialize 200(세션 헤더 포함) · `GET /` 이 `index.html`.

### 8.2.11 어댑터 발견·소스 읽기(게이트웨이 설정 변경 0)

- `adapters/registry.py` 는 `GET {HWAXRISK_GATEWAY_MCP 오리진}/tools-map`(gateway.py:954, 무인증) 으로 도구명→앱키 맵을 받아 **도구명 집합**으로 어댑터 kind 를 바인딩한다 — §2.13.2 의 집합 그대로 mcad = `{list_parts, list_interfaces, interface_graph, project_tree, part_mesh_map, job_status}` ⊂ 앱 도구, dyna = `{inspect_file, list_session_files, report_summary, report_part_risk, report_energy_flow}`, ecad = ODB 계약 4도구. 앱 이름 문자열은 코드에 없다(헌법 P8). 보조로 heax `GET {HWAXRISK_HEAX_API}/api/v1/mcp/servers`(Bearer `HWAXRISK_HEAX_SERVICE_PAT`) 를 읽어 앱 id ↔ 게이트웨이 키(`heax-<id>`) 대응을 확인한다. 발견 결과가 `GET /api/meta/adapters` 다.
- StepForge REST 원문(`/tree`, `/artifacts/graph/`, `/parts`)은 Caddy `{HWAXRISK_HEAX_BASE}/apps/step_forge/api/…` 를 `Authorization: Bearer <HWAXRISK_HEAX_SERVICE_PAT>` 로 직접 읽는다(GET 만). StepForge 는 자체 인증·소유권이 없어(rest.py·mcp_server.py·db.py 에 Depends/HTTPBearer/owner 0건) 서비스 시야가 전체 시야다. 게이트웨이 `rest_proxy` 에 `heax` 사이트를 추가하는 안(설정 3곳 — gateway `rest.heax`·`portal.audience_ok`·포털 `PAT_DEFAULT_AUDIENCES`)은 P0 에서 제외하고 §10 에 남긴다.
- DynaForge 는 사용자 스코프 데이터라 게이트웨이 MCP `heax-kooremapper_mcp` 도구(`inspect_file`·`list_session_files`·`report_*`)를 러너 자격 PAT 로 호출한다 — (b) 면 `per_user_sso` 가 PAT email 로 사용자 세션을 열고, (a) 면 0건이 정상이라 `dyna_absent` 다(§6.7.1). 직접 REST(:8700, `kr_` PAT)는 쓰지 않는다.
- 게이트웨이가 불통이면 `registry.py` 는 `{}` 를 돌려주고 어댑터는 `capture_mode='mcp_degraded'` 또는 `unreachable` 로 강등해 결측(`missing.world_transform_absent` 등)을 남긴다(§2). StepForge 에 `export_ir` 도구를 추가하는 안은 §10 결정 사항이다.

## 8.3 MCP 파리티

### 8.3.1 엔진 상수·문자열(PY/JS 바이트 동일)

| 항목 | PY `HWAXAgentServer/deliberation.py` | JS `HWAXPortal/infra/pipeline/hwax-deliberate.js` | 변경량 |
|---|---|---|---|
| 결정문 항목 | `_CHAIR_ITEMS["risk-review"]`(dict :99) | `CHAIR_ITEMS['risk-review']`(:318) | 항목 1 |
| 지정 반대석 | `_CHAIR_ADVERSARY["risk-review"]`(:344) = `{key:'delib-baseline-defender', label, role}` | `CHAIR_ADVERSARY['risk-review']`(:92) | 항목 1, origin 'adversary' 합성 push 는 기존 코드(:2076 / :98) |
| 문서 제목 | `doc_title` dict(:2375)에 `"risk-review": "리스크 심사 보고서"` | 제목 삼항(:375)에 `CHAIR_TEMPLATE === 'risk-review' ? '리스크 심사 보고서' :` 1항 | 각 1 |
| 좌석 계약 | `_RISK_SEAT_CONTRACT = {"_common": str, <15 도메인 키>: str}`(§6.5.4) + continue_personas 복원 루프 :2044(`p["role"] = await _restore_role(...)`) 직후 3줄 `if opts.chair_template == "risk-review": dom = _dom_of(p["key"]); if dom in _RISK_SEAT_CONTRACT: p["role"] = (p["role"] or "") + "\n" + _RISK_SEAT_CONTRACT["_common"] + "\n" + _RISK_SEAT_CONTRACT[dom]` — 시스템 메시지는 `_persona_round`(:889)가 `persona['role']` 로 만들므로 여기가 삽입 지점이고(라운드 `prompt_fn` :2227 등은 사용자 프롬프트), `_restore_role` **뒤**라 덮어쓰기에 유실되지 않으며, 합성 지정석은 :2078 에서 루프 뒤에 append 되어 붙지 않는다(`_dom_of`='delib' 라 표에도 없다) | `RISK_SEAT_CONTRACT` 동일 dict + 페르소나 시스템 프롬프트 조립부 조건 1줄 | 상수 1 + 3줄 / 상수 1 + 1줄 |
| whenToUse | — | meta.whenToUse(:51) 문장 1개 추가 "risk-review(리스크 심사 보고서·risk_spec, 기준선 옹호 지정석 자동)". 순수 문자열 리터럴, `+` 연결 금지(커밋 3f0d933) | 1 |
| origin 통과 | `_resolve_opts`(:366) personas 매핑(:434-435, `o.continue_personas = [{"key": …, "role": …}]` — 이 줄이 origin 을 버린다)에 `"origin": p.get("origin") if p.get("origin") in ("primary", "counter") else None` | 이미 `personas[].origin` 을 받는다 | PY 1줄 |
| 읽기 도구 | `_RISK_READ_TOOLS`(앱 조건부) · `_RISK_KEEP_TOOLS`(chair 조건부) — 검사 지점은 자유조회 조립식 `_g`(:1897-1898)이다. `_amap = _app_of_tools()` 를 :1915 에서 이 앞으로 올리고 조립식의 `if _free_tool_ok(n)` 을 `if n.lower() not in _FREE_DENY and (_free_tool_ok(n) or (_amap.get(n) in set(opts.delib_apps) and n in _RISK_READ_TOOLS.get(_amap.get(n), ())) or (opts.chair_template == "risk-review" and n in _RISK_KEEP_TOOLS))` 로 확장(≈3줄)하며, `_narrow`(:1916-1918)에는 `or (opts.chair_template == "risk-review" and n in _RISK_KEEP_TOOLS)` 1줄만 남긴다(read 도구는 이미 앱 소속이라 `_narrow` 를 통과한다 — §6.5.2 코드 블록). `_narrow` 에만 넣으면 접두사에 걸리지 않는 read 도구는 `_g` 에 애초에 없어 무효다. `_FREE_DENY`(get_agent_session)는 그대로 우선한다 | N/A(JS 는 좌석 도구 호출 경로 없음) | PY 전용 ≈3+1+1줄 |

`_RISK_SEAT_CONTRACT`·`RISK_SEAT_CONTRACT` 의 원천은 앱 리포 `backend/app/assets/seat-contract.v1.json`(§0.4.1) 이고 두 상수는 그 파일에서 생성한 문자열을 붙여 넣는다. 앱은 같은 JSON 을 E0c evidence 항목으로도 싣는다(이중화). `_RISK_READ_TOOLS` 확장은 chair_template 무관이라 apps 로 그 앱을 고른 다른 심의도 같은 읽기 도구를 얻는다 — 의도된 읽기 전용 확장이며 decision-table.md '기존 심의 영향' 항목에 적는다. `_RISK_KEEP_TOOLS` 는 chair 조건부라 다른 심의 영향이 0 이다.

### 8.3.2 `HWAXPortal/scripts/check_chair_parity.py`(위치 확정 — 포털 리포)

위치는 포털 리포 `HWAXPortal/scripts/` 하나로 확정한다(앱 리포에 두지 않는다). 이유 — 비교 대상 두 엔진 파일이 `HWAXAgentServer/deliberation.py` 와 `HWAXPortal/infra/pipeline/hwax-deliberate.js` 로 앱 리포 밖에 있고, 엔진 additive 항목의 반영 절차(agent-server 재기동·`sync-workflows.sh`)가 포털·엔진 쪽 작업이며, 스크립트가 앱 리포에 있으면 앱 SIF 빌드 대상에 엔진 검사 코드가 섞인다. 리포 루트 `scripts/` 는 현재 없으므로 P0 에서 만든다(기존 `infra/scripts/sync-workflows.sh`(§0.4.3)는 그대로 둔다).

동작. (1) `deliberation.py` 를 `ast.parse` 해 `_CHAIR_ITEMS · _CHAIR_ADVERSARY · _RISK_SEAT_CONTRACT · doc_title` 대입문을 `ast.literal_eval` 로 평가한다(암시적 문자열 연결도 평가된다). (2) `hwax-deliberate.js` 에서 `CHAIR_ITEMS · CHAIR_ADVERSARY · RISK_SEAT_CONTRACT` 객체 리터럴의 `'risk-review'`/도메인 키 값을 백틱 템플릿 리터럴 정규식으로 뽑고 `\`` 와 `\\` 만 언이스케이프한다. 제목은 삼항식에서 `'risk-review' ? '…'` 리터럴을 뽑는다. (3) `seat-contract.v1.json` 을 읽는다. (4) 항목마다 세 원천(PY · JS · JSON — 제목·결정문·반대석은 PY · JS)의 `.encode('utf-8')` 바이트를 비교한다. (5) 종료 코드 0 동일 / 1 불일치(첫 상이 바이트 오프셋과 앞뒤 40자 출력) / 2 추출 실패. `--all` 이면 기존 7 템플릿도 보고하되 `--strict` 없이는 exit 0 이다.

인자(경로 3개, 기본값은 포털 리포 루트 기준 형제 리포). `--py ../HWAXAgentServer/deliberation.py` · `--js infra/pipeline/hwax-deliberate.js` · `--contract ../HWAXRisk/backend/app/assets/seat-contract.v1.json`(JSON 정본은 앱 리포 §0.4.5). 호출처 2곳 — 사람(P0 통과 기준 (1), §8.4.4 반영 절차)과 앱 `backend/tests/test_parity.py`(env `HWAX_PORTAL_REPO` 가 가리키는 포털 리포의 스크립트를 subprocess 로 호출, env 가 없으면 `pytest.skip` — SIF 안에는 포털 리포가 없다).

### 8.3.3 L1 — 단발 심사(원장 미연동)

`hwax-deliberate` 에 `chairTemplate:'risk-review'` 만 주면 결정문 8항목 + risk_spec 펜스 + 기준선 옹호 지정석이 붙은 단발 심사가 된다. 원장·등록부는 만들지 않는다. 결과를 원장에 넣고 싶으면 사람이 앱 MCP `risk_submit_panel_result(panel_id, 'mcp', decision_text, turns, report_id, actor)` 또는 REST `POST /api/panels/{id}/complete` 로 보낸다(패널이 `planned` 상태로 미리 편성돼 있어야 하며, 없으면 409). P0 통과 기준 (6) 이 이 경로다.

### 8.3.4 L2 — `HWAXPortal/infra/pipeline/hwax-risk-review.js` 오케스트레이터(P5)

- args `{targetKey, tier: 'B'|'C', panels?: 1, actor?, model?}`(`model?` = 이 워크플로를 돌리는 LLM 의 모델명 신고값, §6.11 `caller_reported`). 포털 REST fetch·PAT 인자가 없다 — 앱과의 접점은 게이트웨이 도구 `risk_get_brief`·`risk_submit_panel_result`(백엔드 `heax-hwax_risk`) 둘뿐이라 §10 #13 의 'REST fetch 허용 여부' 는 이 경로에 영향이 없다. `actor` 는 워크플로가 실행 환경의 포털 PAT email(있으면) 또는 사용자 입력에서 채운다(앱은 미검증으로 표기).
- 시퀀스. (1) `risk_get_brief(target_key, tier)` 로 패널 목록(`panel_id · seats_json · delib_opts 초안 · evidence E0~E9`)을 받는다. (2) 패널마다 `workflow({scriptPath:'infra/pipeline/hwax-deliberate.js'}, {question, personas: seats_json, chairTemplate:'risk-review', modifiers, evidence, rounds: 3, saveReport: true})` 를 자식 호출한다. (3) 결과 `{decision, turns, report_id}` 를 `risk_submit_panel_result(panel_id, 'mcp', decision_text, turns, report_id, actor, model)` 로 되돌린다(`model` 은 `args.model` 그대로, 없으면 `'unknown'` — D6). (4) 실패한 패널은 제출하지 않고 `{panel_id, error}` 만 반환한다 — 앱 러너의 재시도 규칙(§6.8)이 처리한다.
- 파싱·병합·원장·외부 반영은 앱 한 곳에서만 한다. 워크플로는 risk_spec 을 파싱하지 않는다.
- 좌석 프롬프트에 "도구를 호출하지 말고 [근거]만으로 판정하라" 를 넣고, 앱은 `engine='mcp', tool_mode='evidence_only'` 로 기록한다(§6.11). Tier A 대표 패널과 무인 배치는 웹 러너 전용이며 워크플로가 `tier:'A'` 를 요청하면 `risk_get_brief` 가 `{error:'tier_a_web_only'}` 를 돌려준다.
- `meta.whenToUse` 는 순수 리터럴이다. `.claude/workflows` 사본은 `infra/scripts/sync-workflows.sh` 로 동기한다.

### 8.3.5 앱 MCP 와 게이트웨이 — 자동 흡수(설정·코드 변경 0)

- 서버·도구·마운트는 §8.2.5 다. A 계획의 '포털 MCP 앱(`/api/risk/mcp`, `gateway_config.json` 백엔드 항목 수동 추가)' 은 폐기한다 — 게이트웨이 `heax_registry` 폴링이 heax `GET /api/v1/mcp/servers` 에서 `hwax_risk` 를 읽어 `heax-hwax_risk` 를 만들므로 `gateway_config.json` 은 변경 0 이고 게이트웨이 재시작도 없다(§0.4.5). 필요 조건은 매니페스트 `status beta|stable` + `mcp.expose true` + state 파일(기동 이력) + heax 서비스 PAT 계정의 가시성(company 라 활성 사용자면 통과).
- 게이트웨이가 `/tools-map` 에 `risk_*` 6종을 노출하면 `_RISK_READ_TOOLS['heax-hwax_risk']`(P5 — 앱키는 registry 발견값이므로 A 계획의 `'hwax-risk'` 키 문자열은 `'heax-hwax_risk'` 로 바뀐다, §6.5.2 코드 블록의 주석 갱신)로 다른 심의 좌석(예 sim-plan)이 apps 에 `heax-hwax_risk` 를 넣어 등록부를 자유조회한다.
- 호출자 신원은 §6.11 규칙 — 게이트웨이는 `heax-<id>` 백엔드에 `x-hwax-user`·PAT 를 전달하지 않으므로(gateway.py:746 `_request_user` 는 per_user_sso 앱에서만 읽힘) A 계획의 'X-HWAX-User 대조' 는 성립하지 않는다. 쓰기 도구의 `actor` 인자(미검증 표기)가 그 자리를 대신하고 `owner_sub` 는 패널 행을 승계한다. `risk_get_brief` 는 `actor` 가 owner 인 타깃과 `visibility='org'` 행만 돌려주며 해석 실패면 `reason='caller_unresolved'` 다.

### 8.3.6 파리티 표(decision-table.md 에 그대로 옮긴다)

| 항목 | 웹(deliberation.py) | MCP(hwax-deliberate.js) |
|---|---|---|
| 결정문 8항목 + risk_spec 펜스 | `_CHAIR_ITEMS['risk-review']` | `CHAIR_ITEMS['risk-review']` (바이트 동일) |
| 기준선 옹호 지정석 | `_CHAIR_ADVERSARY['risk-review']` 합성 push | `CHAIR_ADVERSARY['risk-review']` 합성 push |
| 좌석 계약 | `_RISK_SEAT_CONTRACT`(chair 조건부) | `RISK_SEAT_CONTRACT`(chair 조건부) |
| 지정 도구 tools ≤6 | 실호출·tool_inject | N/A(evidence-only) |
| 자유조회 free_tools·apps | `_RISK_READ_TOOLS`·`_RISK_KEEP_TOOLS` | N/A(evidence-only) |
| evidence ≤12 | 동일 예산 | 동일 예산(:120-137) |
| 호출자 | 앱 러너 → 포털 `/agent/chat`(포털 PAT) → agent-server | 사람 → Claude Code 워크플로 → 게이트웨이 도구 |
| 원장·등록부·성격 저장 | 앱 러너 → 앱 `narrative.py` | 앱 MCP `risk_submit_panel_result`(= REST `/api/panels/{id}/complete`) → 같은 `narrative.py` |
| 신원 | 포털 PAT(검증) · `credential service\|owner` | `actor`(미검증, `actor_verified:false`) |
| tool_mode | `tools` | `evidence_only`(C2 strong 비율 제외) |
| 제목 | doc_title '리스크 심사 보고서' | 삼항 '리스크 심사 보고서' |

### 8.3.7 decision-table.md 갱신 항목

Job 표 8행째(`risk-review` · 판단 그룹 · 트리거 `/심의 ` · chair `risk-review`) · delib_opts 계약(`personas[].origin ∈ primary|counter` 통과, `human_note·continue_summary` 러너 미탑재) · 기존 심의 영향(`_RISK_READ_TOOLS` 앱 조건부 읽기 확장, `_RISK_KEEP_TOOLS` chair 조건부) · 파리티 표(§8.3.6, 호출자·신원 행 포함) · 호출 경로(앱 러너 → 포털 `/agent/chat`, §6.7.1) · 반영 절차(§8.4.4).

## 8.4 무손상 원칙과 변경 목록

원칙 하나 — 기존 동작은 `chair_template≠'risk-review'` 이고 `apps` 에 소스 앱이 없을 때 1바이트도 달라지지 않는다. B 에서는 여기에 둘이 더해진다 — 포털이 바뀌는 것은 메뉴·타일·`systems.yaml`(+conv kind 2줄)뿐이고 포털 env·백엔드 라우트·Settings·러너는 없다. 앱 hwax_risk 는 별도 프로세스·별도 DB 라 앱을 정지해도 포털·심의·HEAX 카탈로그가 종전과 같다. 그래서 모든 기존 파일 변경은 dict 항목 추가·조건부 1줄·Record 키 추가·타일 1건·라우트 1건으로만 한다.

### 8.4.1 기존 파일 변경(전부 additive) — 엔진 항목 표는 A 계획과 동일

| 파일 | 변경 | 줄 수 |
|---|---|---|
| `HWAXAgentServer/deliberation.py` | `_CHAIR_ITEMS['risk-review']`(:99) · `_CHAIR_ADVERSARY['risk-review']`(:344) · `doc_title` 1항목(:2375) · `_resolve_opts` personas `origin` 통과 1줄(:434-435) · 상수 `_RISK_READ_TOOLS`·`_RISK_KEEP_TOOLS`·`_RISK_SEAT_CONTRACT` 3개 · 자유조회 조립식 `_g` 조건 확장 ≈3줄(:1897-1898) + `_amap = _app_of_tools()` 상향 1줄(:1915 → 조립식 앞) · `_narrow` keep or 1줄(:1916-1918) · continue_personas 복원 루프 :2044 직후 chair 조건부 계약 접미 3줄 | ≈ 상수 3 + 12 |
| `HWAXPortal/infra/pipeline/hwax-deliberate.js` | `CHAIR_ITEMS`(:318)·`CHAIR_ADVERSARY`(:92) 항목 각 1 · 제목 삼항(:375) 1항 · `RISK_SEAT_CONTRACT` 상수 + 조건 1줄 · whenToUse(:51) 문장 1 | ≈ 상수 2 + 4 |
| `HWAXPortal/backend/app/agent/routes.py` | `ConvCreate.kind` Literal(:129)에 `"risk-review"`. `DelibOpts.personas` 는 `list[dict]`(:73)라 `origin` 이 이미 통과한다 — 주석 1줄만 | 1~2 |
| `HWAXPortal/backend/config/systems.yaml` | 타일 `hwax-risk` 1건(§8.1.2) → `POST /systems/reload` | ≈ 14 |
| `frontend/src/components/chat/delibTaxonomy.ts` | JobId 값 1 · JOBS 8행째 · JOB_ROUTING 항목 1 · suggestJob 분기 1(append) | ≈ 8 |
| `frontend/src/api/conversations.api.ts` | ConvKind 값 1(:6) | 1 |
| `frontend/src/App.tsx` | 라우트 객체 1(`/risk`) | ≈ 10 |
| `frontend/src/components/layout/AppHeader.tsx` | NavLink 1(카탈로그에 `hwax-risk` 타일 있을 때 표시) | ≈ 5 |
| `frontend/src/pages/risk/RiskLaunchPage.tsx` | 신규 1파일(얇은 셸 2단, §8.1.3) | ≈ 60(신규) |
| `HWAXAgentServer/tools/delib_metrics.py` | 리스크 지표 7종 함수 추가(기존 지표 함수 무수정, §0.4.3). 지표 원천은 앱 REST `GET /api/meta/metrics`(heax 서비스 PAT) | 함수 7 |
| `HWAXPortal/scripts/check_chair_parity.py` | 신규 1파일(§8.3.2) | 신규 |
| `docs/deliberation-quality/method-menu/decision-table.md` | §8.3.7 항목 | 문서 |
| `HEAXHub/integrations/hwax-risk/.portal/manifest.yaml` | 신규 1파일(§8.2.2, 매니페스트 전용 디렉터리) | ≈ 40(신규) |
| `HWAXMcpGateway/gateway_config.json` | **변경 없음**(`heax-hwax_risk` 는 `heax_registry` 자동 흡수) | 0 |
| 포털 `backend/app/main.py` · `backend/app/config.py` · `.env` · `routes.env` · nginx | **변경 없음**(A 계획의 main.py 4줄·config.py 14 필드·`RISK_REVIEW_ENABLED` 폐기) | 0 |

### 8.4.2 건드리지 않을 것

`_deliberation_stream` 라운드 루프 본체 · `_FREE_ALLOW` 전역 접두사 목록(:1233) · `_MATERIAL_TOOLS`(:1251) · `_restore_role`(:1360) 본체 · `_RESCREEN` 기본값(:307, 러너가 human_note·continue_summary 를 싣지 않으므로 발동하지 않는다 — plan_5 의 `rescreen` 옵션 신설은 채택하지 않는다) · `_chat_user_pat`(routes.py:158) 본체 · `principal_pat_or_session`(deps.py:74) · `agent_semaphore` · `/agent/chat` 계약(요청·SSE 스키마) · 기존 8 chair_template·5 modifier 문자열 · delib_opts 기존 키 의미 · SSE 이벤트 스키마(§0.2.3 은 파싱 규약이지 스키마 변경이 아니다) · RA 블록 구조·save_conversation 스키마 · conv_store/token_store 스키마(kind 값 추가만) · 기존 라우트 6개(`/`, `/login`, `/deliberate`, `/apps`, `/tokens`, `/launch/:systemId`)와 NavLink 4개 텍스트 · ChatContext 필터 로직 · `LaunchPage.tsx`·`downstream.py`·`portal_sso` 콜백 계약 · MCP 도구명 · delibTaxonomy 기존 7 Job 객체 텍스트 · 포털 `main.py`·`config.py`·`.env`·`routes.env`·nginx 템플릿 · HEAXHub 코드(`proxy_manager.py`·`portal_sso.py` 선택 additive 2건은 §10 결정 전 미착수, `integration_launcher`·`integrations_scanner`·`appdata-*.sh`·`dist-*.sh` 무수정) · `HWAXMcpGateway` 코드·`gateway_config.json` · StepForge/DynaForge/RA/AIDataHub 코드(RA 는 관리 REST 부트스트랩 1회 + MCP 인스턴스 쓰기 4종만, AIDataHub 는 `create_doc_type`·`create_agent`·REST import 만, StepForge/DynaForge 는 읽기 도구·REST GET 만) · `set_interface/confirm_interfaces/run_job/run_operation/remesh_parts/upload_*` 자동 실행 금지 · `bind_records_to_agent`·`patch_agent` 호출 금지 · 기존 sqlite 파일(conversations·tokens) 무접촉 · 다른 HEAX 앱의 `var/app_data/<id>/`.

### 8.4.3 회귀 검사(불변 조건과 검사 방법)

| 불변 조건 | 검사 |
|---|---|
| 포털 백엔드 라우트 목록 무변경(`/api/risk/*` 부재), `/agent/*` 응답 동일 | 포털 `openapi.json` 스냅샷 diff 0 + `/agent/conversations` 생성·조회 pytest 스모크 |
| 포털 Settings 필드·`.env` 키 무변경 | `config.py` diff 0, `.env.example` diff 0 |
| 타일 `hwax-risk` 가 안 보이는 사용자(`required_role` 밖)에게 헤더 NavLink 4개·라우트 동작 종전과 동일, 보이는 사용자에게 NavLink 5개 | playwright(그룹 2종) |
| `/risk` 셸이 앱 REST 를 fetch 하지 않는다 | playwright 네트워크 캡처 — `/apps/hwax_risk/api/*` 요청 0건 |
| 기존 8 chair e2e 결정문 형식 불변 | `hwax-deliberate default/diagnosis/sim-plan` 각 1건 골든 비교(항목 제목 순서) |
| apps 에 step_forge 없는 심의에서 `inspect_report` 차단, apps=['heax-step_forge'] 에서 `interface_graph`·`inspect_report` 통과(chair 무관), chair≠risk-review 에서 `_RISK_KEEP_TOOLS` 비활성, `get_agent_session` 은 어느 조합에서도 부재 | `_g` 조립·`_narrow` 단위 테스트(픽스처 tools-map) |
| `_restore_role` 이 원본 role 을 복원하고 계약이 그 뒤에 붙는다 | `_persona_round` sysmsg 덤프 테스트(SSE personas 의 280자 절단 role 은 검사 대상이 아니다) |
| 두 엔진 문자열 바이트 동일 | `check_chair_parity.py` exit 0 |
| 게이트웨이 도구 수 드리프트 — 앱 기동·레지스트리 노출 전 0, 후 +6(`risk_*`), 그 외 백엔드 도구 수 불변 | `/tools-map` len·키 집합 비교 |
| 프론트 빌드·Job 카드 8개·기존 7개 텍스트 불변 | `tsc -b && vite build` + playwright 스모크(`/deliberate`) |
| `/deliberate` 목록에 risk-review 대화 0건 | playwright + conv_store 조회 |
| conv_store·token_store 스키마 무변경 | `PRAGMA table_info` 스냅샷 비교 |
| 앱 정지 상태(`heax_app_hwax_risk` stop)에서 포털 홈·챗·심의·`/apps`·HEAX 카탈로그·다른 앱 라우트(`/apps/step_forge/`) 응답 코드 동일 | 스모크 curl 표(정지 전후) |
| 앱 기동 3점 — `GET /api/health` 200 · `POST /mcp` initialize 200 · `GET /` index.html, Caddy `/apps/hwax_risk/` 익명 401 | 앱 `tests/test_boot.py` + curl |
| HEAX `GET /api/v1/mcp/servers` 에 `hwax_risk` 1건, 다른 앱 항목 불변 | curl(heax 서비스 PAT) diff |
| 배치 중 대화형 심의 슬롯 점유 ≤ `risk_concurrency` | P4 (7) |
| 계획서에 '포털' 주체 잔재 0건 — 파서·원장·러너·야간 잡·예산표·TargetPage 의 주체는 앱(B, §0.7 #12) | `grep -cE '포털 (원장\|권위\|러너\|단일\|백그라운드\|예산표\|TargetPage)\|포털(에서 수행\|은 벡터)' docs/design-risk-review/plan.md` = 0 |

### 8.4.4 반영 절차(운영, 사용자 몫 — 앱 등록·빌드 → app-data → 게이트웨이 자동 흡수 → cae00 이관)

순서대로.

1. **엔진 additive 반영** — agent-server 재기동(`deliberation.py` 상수·`_g` 조립 조건·`_narrow`·:2044 계약 접미) → `infra/scripts/sync-workflows.sh`(hwax-deliberate.js 변경, P5 부터 hwax-risk-review.js) → erag 재색인(whenToUse 변경) → `scripts/check_chair_parity.py` exit 0 확인.
2. **포털 창** — `backend/config/systems.yaml` 타일 추가 → `POST /systems/reload`(admin) → 프론트 빌드·배포(App.tsx·AppHeader·RiskLaunchPage) → 포털 백엔드 재기동(routes.py `ConvCreate.kind` 2줄). 포털 `.env` 변경 없음.
3. **앱 등록·빌드(dev)** — HEAXHub `integrations/hwax-risk/.portal/manifest.yaml` 커밋 → 5분 스캔 또는 즉시 트리거(`backend/.venv/bin/python -c 'from app.workers.integration_tasks import scan_integrations_periodic as s; print(s()["by_action"])'`) → `var/logs/sif_build_hwax-risk.log` 에서 SIF 빌드 성공 → 45 초 reconcile 이 `var/sifs/hwax-risk.sif` 로 기동 → `var/logs/integration_hwax_risk.log` → `curl -o /dev/null -w %{http_code} http://localhost:4180/apps/hwax_risk/` 가 401(정상 게이트) → 로그인 후 `/apps/hwax_risk/api/health` 200.
4. **app-data** — `var/app_data/hwax_risk/` 생성 확인 → `secrets.env`(0600, `HWAXRISK_PORTAL_PAT`·`HWAXRISK_HEAX_SERVICE_PAT`·`HWAXRISK_AIDH_API_KEY`, 각 발급처 §8.2.7) 작성 → `redeploy-app.sh hwax-risk`(재기동, 시크릿 로드) → `GET /api/health` 의 `schema_version`·`origin.json.hostname` 확인 → 부트스트랩 `backend/scripts/bootstrap_ra_ontology.py --base <RA REST 오리진> --apply`(실행자 env `RA_ADMIN_PAT`, 승인 후) · `backend/scripts/bootstrap_adh.py`(실행자 env `HWAXRISK_AIDH_API_KEY`, doc_type 3종·risk-review-memory) → 운영 개시 후 dev crontab 에 `appdata-to-drive.sh` 일 1회(§5.2.5 (3)).
5. **게이트웨이 자동 흡수(작업 없음, 확인만)** — heax `GET /api/v1/mcp/servers`(서비스 PAT)에 `hwax_risk` 등장 → 게이트웨이 revive 루프가 `heax-hwax_risk` 를 만들면 `GET :9110/tools-map` 에 `risk_*` 6종 → 게이트웨이 재시작 없음. 흡수가 안 되면 순서대로 확인 — 매니페스트 `status beta`·`mcp.expose` → state 파일 `var/integration_state/hwax_risk.json` → `heax_registry.token` 계정의 가시성. restart 스크립트를 쓸 일이 생기면 `-sTCP:LISTEN` 주의(메모리 restart-kill-port-hazard).
6. **cae00 이관** — dev `HWAXPortal/infra/scripts/build-all-to-drive.sh`(SIF·app-data 를 Drive 로) → cae00 `update.sh` 또는 `deploy-all-from-drive.sh`(`dist-from-drive.sh` 가 `var/sifs/hwax-risk.sif` 배치, 매니페스트는 HEAXHub git pull, `appdata-merge-from-drive.sh` 첫 배포 시드) → reconcile 기동 → cae00 에서 서비스 PAT·heax PAT·AIDH 키를 새로 발급해 cae00 `secrets.env` 작성(dev 시크릿은 cae00 에서 401, §5.2.5 (5)) → `redeploy-app.sh hwax-risk` → SettingsPage/TargetPage '재동기'. 이후 dev→cae00 데이터 이동은 `GET /api/export` → `POST /api/import` 뿐이다. dev 박스에서 `deploy-all` 류를 돌리지 않는다(메모리 deploy-all-resets-dev-repo).

# §9 단계 계획

## 9.0 읽는 법

단계마다 목표 · 산출물 · 의존 · 수치 통과 기준 · 리스크와 완화 · "이 단계만으로 얻는 것" 을 적는다. 각 단계는 그 자체로 사용자가 무언가를 등록·조회·심사할 수 있는 완결 기능이어야 하고, 통과 기준은 전부 코드나 스크립트로 판정 가능한 숫자다. 1차 계획(doc_20 §9)을 정본으로 보존하되 gap_21 이 확인한 것을 다음처럼 고쳤다 — parse_risk_spec 을 P0 산출물로 당김(공백 7), C1 조건에서 RA 절을 빼고 `external_sync` 로 표기(공백 7), P0 (9) 에 러너 자격 실측 3항(공백 9), `_RISK_SEAT_CONTRACT`·`_RISK_KEEP_TOOLS` 를 P0 확정 변경으로(공백 3·4), P3 에 SSE 귀속 성공률(공백 5), P4 에 미착석 배지·`risk_default_close_level`(공백 6), P5 에 계보 없는 과제 회수·E7 슬롯(공백 2·8), 비용 표의 toulmin 재시도 줄 삭제·사전 예산 게이트(공백 10), `extra_seats == ∅`(공백 11). 문서 디렉터리는 `docs/design-risk-review/` 다.

B 개정(§0.7 #12)으로 이 절에서 바뀐 것은 셋뿐이다. ① 산출물 위치 — A 계획의 포털 `backend/app/risk/`·`frontend/src/pages/risk/`·`backend/tests/risk/`·`data/risk_review.sqlite` 는 전부 앱 리포 `HWAXRisk` 의 `backend/app/`·`frontend/src/`·`backend/tests/`·`$HEAX_DATA_DIR/risk_review.db` 로 옮겼고 포털에는 창(§8.1)만 남는다. ② 러너 경로 — 앱 프로세스의 `runner.py` 가 포털 `POST /agent/chat` 을 포털 PAT Bearer 로 부른다(§6.7.1 (A), 러너 자격 (a)(b) — 대리 발급 없음). ③ P0 산출물 — 앱 리포 스캐폴드·HEAXHub 매니페스트 등록·SIF 기동·Caddy 라우트·게이트웨이 자동 흡수·app-data Drive 왕복이 P0 에 들어오고, 게이트웨이 `rest.heax` 설정 변경·포털 `/api/risk` 라우트·포털 Settings 14 필드는 빠진다. rr_* 스키마·원자·해시·상태기계·E0~E9·학습 루프·엔진 additive 항목의 내용은 A 계획 그대로다.

의존 사슬은 P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 이 기본이고, 병행 가능한 것은 §9.9 에 있다.

## 9.1 P0 부트스트랩 — 계약·엔진 손잡이·저장소 준비

목표. B 토폴로지의 뼈대를 세운다 — 앱 리포 `HWAXRisk` 스캐폴드가 HEAX 앱 `hwax_risk` 로 등록·기동되어 `/api/health`·`/mcp`·SPA 셸이 Caddy `/apps/hwax_risk/*` 뒤에서 응답하고, 게이트웨이가 `heax-hwax_risk` 를 설정 변경 없이 자동 흡수하며, 엔진 additive 항목과 저장소 3층 계약(앱 DB v1 DDL · RA 6축 12관계 · AIDataHub doc_type)이 준비되어 이후 단계가 계약 위에서만 움직이게 한다. 포털 창은 타일·라우트·NavLink 로 앱을 열고, 챗 핸드오프 카드에서 단발 리스크 심사(L1)가 즉시 돌아간다.

산출물(A 앱 리포 · B HEAXHub 등록 · C 포털 창 · D 엔진 additive · E 문서).

A. 앱 리포 `HWAXRisk`(`/home/koopark/claude/HWAXRisk`, GitHub `squall321/HWAXRisk`) 스캐폴드 — ThermalShockMCP `app/{main,config,mcp_server}.py` 골격과 `HEAX_DATA_DIR` 폴백 규칙 복제 + `fastapi_react` 레이아웃(§8.2.1). 모든 신규 소스 파일 첫 줄은 한국어 역할 주석. 실존 — 2026-08-31 커밋 0건 스캐폴드가 이미 있고(§10.8 #28) 이 목록과의 대조·즉시 델타는 목록 끝 'A-δ' 다.
- `.portal/manifest.yaml` — §8.2.2 확정값 전문(`schema_version 2 · id hwax_risk · name HWAX Risk Review · version 0.1.0 · owner cae-automation · status beta · app_type web_app · execution_target linux_runner · build{python_venv, fastapi_react, "3.12"} · launch{service, health_check /api/health, restart on_failure 3, env{HWAXRISK_DATA_DIR:/data, PYTHONNOUSERSITE:"1"}} · permissions.visibility company · resources{cpu 1, memory_gb 2, gpu false} · source{git, https://github.com/squall321/HWAXRisk.git, main} · mcp{expose true, path /mcp, streamable_http, description, allowed_groups []}`).
- `backend/pyproject.toml`(`fastapi · uvicorn[standard] · 'mcp>=1.10,<2' · pydantic · httpx`, setuptools `packages.find include app*`, version 0.1.0).
- `backend/app/main.py` — 등록 순서 고정 ① `/api/health`·`/api/*` 라우터 ② MCP `Route('/mcp')` 이식(`mcp._session_manager = None` 후 `streamable_http_app().routes` 를 `app.router.routes` 에 append, §0.4.1) ③ 마지막에 `app.mount('/', StaticFiles(directory=<main.py 기준 ../../frontend/dist>, html=True))`. lifespan §8.2.10 ①~⑦(`session_manager.run()` · `runner.start()`). `app.mount('/mcp', …)`(307) 과 thermal 방식 `mount('/', mcp_app)` 은 쓰지 않는다.
- `backend/app/config.py` — 데이터 루트 `HWAXRISK_DATA_DIR > HEAX_DATA_DIR > <리포>/data`, `mkdir -p`+`W_OK`(실패 = 기동 중단), Settings §8.2.6 전 필드(env 접두 `HWAXRISK_`, 속성명 `risk_*`), `$HEAX_DATA_DIR/secrets.env`(0600) 로드.
- `backend/app/identity.py` — `identity.current(request) -> Identity{email, display_name, role, organization, anonymous, source ∈ bearer|cookie|none}`, `Authorization: Bearer` 우선 → 쿠키 `heax_access_token` → heax `GET {HWAXRISK_HEAX_API}/api/v1/auth/me` 되묻기, `sha256(token)` 키 TTL 60 s 캐시. `X-Heax-User-*` 헤더는 읽지 않는다(§8.2.8).
- `backend/app/risk_store.py` — `MIGRATIONS: list[tuple[int, list[str]]]` v1 = §5.2.2 DDL 전문(rr_* 33표) + 살림 표 `_schema_migrations`·`_user_credentials`(`CREATE TABLE IF NOT EXISTS`, export 제외), `PRAGMA user_version`·`journal_mode=WAL`, 적용 전 `risk_review.db.pre-migrate-<ts>` 사본. 쓰기 경로는 P1~.
- `backend/app/routes.py`(prefix `/api`) — `GET /health {ok, app_version, schema_version}` · `GET /me` · `PUT /me/portal-pat`(422 `pat_invalid · pat_email_mismatch · pat_audience · pat_expiring`) · `GET /meta/taxonomy` · `GET /meta/adapters`. 나머지 경로(§8.2.3)는 P1~P5.
- `backend/app/mcp_server.py` — `FastMCP('hwax-risk', streamable_http_path='/', transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))`, 도구 6종 시그니처 등록(§0.5.2 — `risk_get_snapshot · risk_get_diff · risk_get_registry · risk_claims_for_ref · risk_get_brief(target_key, tier='B') · risk_submit_panel_result(panel_id, engine, decision_text, turns, report_id, actor)`). P0 본문은 `{error:'not_implemented', ready_in:'P1|P2|P3|P5'}` 이고 실구현은 P1(snapshot)·P2(diff)·P3(registry·claims·submit)·P5(brief).
- `backend/app/narrative.py` v0 = `parse_risk_spec`(parseSimSpec 복제, 펜스 우선 → 마지막 균형 중괄호 → 실패 null 비치명) + `schemas/risk_spec.v1.json` 검증. cites 해석·seat_opinion 추출·prior_evidence 는 P1·P3. `backend/app/taxonomy.py`(`assets/taxonomy.v1.json` 로더).
- `backend/app/assets/{taxonomy, character-vocab, character-seed-rules, adjacency, rules-seed, seat-contract}.v1.json`(런타임 자산 6종 정본 — 문서 디렉터리에 두지 않는다, §0.4.5) · `backend/app/schemas/{rr_ir, rr_state, rr_diff, risk_spec, seat_opinion}.v1.json` + 유효/무효 픽스처 각 ≥2.
- `backend/app/adapters/{base,registry}.py` v0 — `registry.py` 가 게이트웨이 `GET {HWAXRISK_GATEWAY_MCP 오리진}/tools-map` 도구명 집합으로 kind 를 바인딩(앱 이름 문자열 없음)해 `GET /api/meta/adapters` 를 채운다. `mcad/dyna/ecad_stub/ecad` 는 P1·P2·P7.
- `backend/app/runner.py` 골격 — `RiskRunner(store, settings).start()/stop()`, 스레드 `panel_loop`(5 s)·`sync_loop`(60 s), 잡이 없으면 idle, 러너 자격 (a)(b) 부재 판정과 `rr_jobs.error='pat_unavailable'` 표기 로직만. 패널 실행은 P3.
- `backend/app/export.py` 자리만(P1). `backend/app/{ir_builder, sameas, diff, state, render, planner, registry, character, ra_client, adh_client}.py` 는 각 단계.
- `backend/scripts/bootstrap_ra_ontology.py --base <RA REST 오리진>`(6축 · 속성 · 12관계, dry-run 기본, 멱등, §0.3.2 전표를 스크립트 상단 표로 포함 — `revision_of{project→project, acyclic}` 포함, 실행자 env `RA_ADMIN_PAT` 만) · `backend/scripts/bootstrap_adh.py`(doc_type `risk_review_opinion · risk_review_panel · project_character`, 의사 에이전트 `risk-review-memory`, `external_source=hwax-risk`, 실행자 env `HWAXRISK_AIDH_API_KEY`). 둘 다 실행자 셸 전용이고 앱 런타임이 부르지 않는다.
- `backend/tests/` — `test_boot.py`(기동 3점: `/api/health` 200 · `/mcp` initialize · `/` index.html) · `test_parity.py`(env `HWAX_PORTAL_REPO` 의 `scripts/check_chair_parity.py` subprocess, env 없으면 skip) · `test_schemas.py`(라운드트립·무효 픽스처) · `test_parser.py`(`parse_risk_spec` 펜스·중괄호·실패 null) · `test_identity.py`(Bearer/쿠키/위조 헤더/캐시).
- `frontend/` — Vite `base: './'` · HashRouter · `App.tsx` 라우트 5(`#/`, `#/projects/:id`, `#/compare`, `#/targets/:key`, `#/settings`) · `pages/{RiskHomePage, ProjectPage, SnapshotPage, ComparePage, TargetPage}.tsx` 는 P0 에서 제목+"P1~P4 에서 채움" 셸 · `pages/SettingsPage.tsx` 완성(`GET me` · `PUT me/portal-pat` · `box{hostname, secrets_valid}` · 동의 문구 §8.2.4) · `api/risk.api.ts`(health · me · portal-pat, `fetch('api/…')` 상대경로) · `mermaid` npm 의존 선언 · `pnpm-lock.yaml`.
- `README.md · checklist.md · context-notes.md`.

A-δ. 실존 스캐폴드 대조·즉시 델타(2026-08-31 실측, §10.8 #28 — P0 착수 즉시 적용, 항목 끝 괄호는 관련 통과 기준 번호). 실존 리포 `/home/koopark/claude/HWAXRisk`(커밋 0건)에 이미 있는 것 — `.portal/manifest.yaml` · 루트 `pyproject.toml` · `app/{main, config, identity, risk_store, narrative, taxonomy, mcp_server, api, cli, errors}.py` · `app/schemas/*.v1.json` 5종(+유효/무효 픽스처) · `docs/*.v1.json` 6종 · `docs/odb-adapter-contract.md` · `tests/{test_health, test_config_datadir, test_store, test_parse_risk_spec, test_schemas, test_mcp_tools, test_manifest, test_identity}.py` · `README.md · checklist.md · context-notes.md · docs/plan.md`. 없는 것 — `adapters/` · `runner.py` · `routes.py`(`api.py` 가 대신) · `scripts/` · `export.py` · `frontend/` · `test_boot.py` · `test_parity.py`.
- 레이아웃(#28 기본 (i)) — `app/`→`backend/app/`, `pyproject.toml`→`backend/pyproject.toml`(`httpx` 를 runtime deps 로, package-data 에 `assets/*.json`), `tests/`→`backend/tests/`, `docs/*.v1.json`→`backend/app/assets/`(`docs/` 에서 제거, §0.4.5), `frontend/` 신설, 매니페스트 `build.stack fastapi`→`fastapi_react`. (ii) 를 고르면 이 줄만 P1 로 미룬다(§8.2.1).
- `main.py` — `app.mount('/', mcp.streamable_http_app())` 를 지우고 MCP `Route('/mcp')` 이식(§0.4.1 ②) + 마지막 `app.mount('/', StaticFiles(directory=<main.py 기준 ../../frontend/dist>, html=True))`((ii) 면 `app/static/`)로 바꾼다. `GET /health`(prefix 밖, 응답 `{status, app_id, version, schema_version, data_dir}`)는 `GET /api/health {ok: true, app_version, schema_version}` 으로 옮기고 옛 경로는 지운다. lifespan 에 §8.2.10 ③ `origin.json` ④ 시크릿·`_user_credentials` 유효성 ⑤ identity 캐시 ⑦ `runner.start()` 를 더한다 — (13).
- `.portal/manifest.yaml` — `launch.health_check.path /health`→`/api/health` · `build.stack fastapi`→`fastapi_react`((i)) · `permissions.visibility team`→`company` · `resources.memory_gb 1`→`2` · `launch.env{HWAXRISK_DATA_DIR: /data, PYTHONNOUSERSITE: "1"}` 추가 · `mcp.allowed_groups: []` 추가 · `description` 의 `/api/v1`·`/health`·`hwax_risk.db`·'도구 3종' 문구를 §8.2.2 값으로 고친다. `source.url https://github.com/squall321/HWAXRisk.git`·`tags`·`mcp.expose/path/transport` 는 그대로 — (14).
- `identity.py` — `X-Heax-User-Email` 읽기와 `source='header_unverified'` 를 제거하고 §8.2.8 의 `identity.current(request) -> Identity{email, display_name, role, organization, anonymous, source ∈ bearer|cookie|none}`(Bearer → 쿠키 `heax_access_token` → heax `GET {HWAXRISK_HEAX_API}/api/v1/auth/me`, `sha256(token)` TTL 60 s 캐시)로 교체하고, `api.py` 의 `resolve_identity` 호출을 `Depends(identity.current)` 로 바꾼다 — (17).
- `mcp_server.py` — P0 도구 3종(`risk_health · risk_get_taxonomy · risk_get_meta`)을 지우고 §0.5.2 6종 시그니처(본문 `{error:'not_implemented', ready_in:'P1|P2|P3|P5'}`)를 등록한다. `FastMCP('hwax-risk', streamable_http_path='/', …)` — (13)(15) `tools/list` == 6.
- `risk_store.py` — 이력 표 `schema_migrations(version, applied_at)`→`_schema_migrations(version INTEGER PRIMARY KEY, applied_at INTEGER, app_version TEXT)`, `MIGRATIONS` v1 을 4표에서 §5.2.2 33표 전문 + `_user_credentials` 로, 적용 직전 `risk_review.db.pre-migrate-<ts>` 사본 — (16).
- `config.py` — `DB_FILENAME = "hwax_risk.db"`→`"risk_review.db"`(§0.3.1 — 확장자 `.db` 가 `appdata-to-drive.sh` `**/*.db` `.backup` 조건, 실스크립트 :31), env 접두 `HWAXRISK_` 는 그대로, Settings §8.2.6 전 필드와 `$HEAX_DATA_DIR/secrets.env`(0600) 로드 추가 — (16).
- `api.py`→`routes.py`, prefix `/api/v1`→`/api`(§0.5.1), `GET /health` · `GET /me` · `PUT /me/portal-pat` 추가(`/meta/vocab` 은 유지) — (17).
- `tests/` — `test_health.py`→`test_boot.py`(기동 3점), `test_parse_risk_spec.py`→`test_parser.py`, `test_parity.py` 신설, `test_mcp_tools.py` 는 6종·`not_implemented` 검사로, `test_identity.py` 는 Bearer/쿠키/위조 헤더 무시/`/auth/me` 실호출 1회로, `test_manifest.py` 의 허용 오류를 루트 `mcp`·`source.ref` 2건으로 고정 — (1)(10)(14)(17).
- `README.md · context-notes.md · checklist.md · docs/plan.md` — `hwax_risk.db`→`risk_review.db`, `/api/v1`→`/api`, `/health`→`/api/health`, `schema_migrations`→`_schema_migrations`, 도구 3종→6종으로 고치고 `.sqlite` 문자열은 역사 언급까지 0건으로 지운다(`.db` 만이 `.backup` 조건). `context-notes.md` D2 의 '경로·이름은 이 노트가 정본' 을 '이름·경로·계약 정본은 포털 `plan.md`(§10.8 #28)' 로 고치고, 포털 `context-notes.md` 에 #28 결정을 적는다.
- 신규(실존 없음) — `adapters/{base,registry}.py` v0 · `runner.py` 골격(`panel_loop`·`sync_loop`·`nightly_loop`, §8.2.9) · `scripts/{bootstrap_ra_ontology,bootstrap_adh}.py` · `export.py` 자리 · `frontend/`(P0 (11), (ii) 면 P1).

B. HEAXHub 등록(코드 0, §8.4.4 3~5) — `integrations/hwax-risk/.portal/manifest.yaml`(매니페스트 전용 디렉터리, 심볼릭 링크 아님 — 앱 리포 `.portal/manifest.yaml` 과 동일 내용) 커밋 → 5분 스캔 또는 즉시 트리거 → dev 가 `var/sifs/hwax-risk.sif`(+`.hash`) 빌드 → 45 초 reconcile 기동(인스턴스 `heax_app_hwax_risk`) → Caddy 라우트 `/apps/hwax_risk` · `/apps/hwax_risk/*`(forward_auth → strip → `127.0.0.1:<port>`) 자동 등록 → `var/app_data/hwax_risk/` 생성(SIF `/data` bind) → `secrets.env`(0600, `HWAXRISK_PORTAL_PAT · HWAXRISK_HEAX_SERVICE_PAT · HWAXRISK_AIDH_API_KEY`, §8.2.7) 작성 → `redeploy-app.sh hwax-risk` → 게이트웨이 `heax-hwax_risk` 자동 흡수 확인(`gateway_config.json`·게이트웨이 재시작 없음).

C. 포털 창(§8.1, 전부 additive) — `backend/config/systems.yaml` 타일 `hwax-risk`(name 리스크 심사 · jwt-handoff · audience heax-hub · url `/heax-hub/api/v1/auth/portal-callback` · auto_post/token · accent rose · category engineering · status available · sort_order 60) + `POST /systems/reload` · `frontend/src/App.tsx` 라우트 `/risk` 1건 · `AppHeader.tsx` NavLink '리스크 심사'(카탈로그에 `hwax-risk` 타일 있을 때만) · `frontend/src/pages/risk/RiskLaunchPage.tsx`(launch → 앱 링크 2단) · `delibTaxonomy.ts`(JobId · JOBS 8행째 · JOB_ROUTING · suggestJob 분기 append) · `conversations.api.ts` ConvKind · `backend/app/agent/routes.py` `ConvCreate.kind` 값. 포털 백엔드 라우트·Settings·`.env`·`routes.env`·nginx 변경 0(A 계획의 `/api/risk/*`·Settings 14 필드·`RISK_REVIEW_ENABLED` 폐기).

D. 엔진 additive(§8.3.1, A 계획과 동일) — `deliberation.py` 항목 `_CHAIR_ITEMS · _CHAIR_ADVERSARY · doc_title · _RISK_SEAT_CONTRACT(+:2044 직후 p["role"] 접미 3줄) · _RISK_READ_TOOLS · _RISK_KEEP_TOOLS(+자유조회 조립식 _g 조건 확장 ≈3줄 :1897-1898 + _amap 상향 1줄 + _narrow keep or 1줄 :1916-1918) · _resolve_opts origin 1줄(:434-435)`. `hwax-deliberate.js` 항목 `CHAIR_ITEMS · CHAIR_ADVERSARY · 제목 삼항 · RISK_SEAT_CONTRACT · whenToUse(순수 리터럴)`. `HWAXPortal/scripts/check_chair_parity.py`(인자 `--py ../HWAXAgentServer/deliberation.py --js infra/pipeline/hwax-deliberate.js --contract ../HWAXRisk/backend/app/assets/seat-contract.v1.json`, 리포 루트 `scripts/` 신설). `HWAXAgentServer/tools/delib_metrics.py` 에 `risk_spec 파싱 성공률` 1종(나머지 6종은 P4).

E. 문서 — 포털 `docs/design-risk-review/{plan.md, checklist.md, context-notes.md}` · 앱 리포 `HWAXRisk/docs/odb-adapter-contract.md`(정본, 실존 — §2.5.3) · 포털 `docs/deliberation-quality/method-menu/decision-table.md` §8.3.7 항목.

의존. 없음. B 는 스캐너·SIF 빌드가 동작하는 dev 박스에서 한다(cae00 은 SIF 빌드 금지). 게이트웨이 설정·코드 변경은 없다.

통과 기준.
1. `check_chair_parity.py` 가 결정문·반대석(key/label/role)·좌석 계약 16 문자열(15 도메인 + `_common`, §6.5.4)·제목 을 PY/JS/JSON 바이트 동일로 보고, exit 0. 앱 `backend/tests/test_parity.py` 는 `HWAX_PORTAL_REPO` 설정 시 같은 결과, 미설정 시 skip 1.
2. RA `list_object_types` 에 신규 6축·12관계가 보이고, `bootstrap_ra_ontology.py --base <RA REST 오리진> --apply` 2회 실행 시 두 번째는 생성 0건, 기존 15축·17관계 무변경(dry-run 출력과 실행 후 조회 diff 0). 실행자 env 는 `RA_ADMIN_PAT` 뿐이고 앱 `secrets.env`·코드에 RA 토큰 문자열 0건(grep `rat_`·`RA_ADMIN_PAT` = 0).
3. AIDataHub `list_doc_types` 에 3종, `list_agents` 에 `risk-review-memory` 존재, 재실행 시 생성 0. `POST /api/records/import?external_source=hwax-risk` dry_run 1건이 `X-API-Key` 로 200, 키 없이 401(또는 `AUTH_REQUIRED=false` 박스에서는 anonymous 통과를 context-notes 에 기록).
4. StepForge 직접 읽기(게이트웨이 `rest.heax` 불요) — `GET {HWAXRISK_HEAX_BASE}/apps/step_forge/api/projects/{id}/tree` 가 `Authorization: Bearer <HWAXRISK_HEAX_SERVICE_PAT>` 로 200, 헤더 없이 401, 게이트웨이 MCP `heax-step_forge` `project_tree` 가 `HWAXRISK_PORTAL_PAT` 로 같은 노드 수. 앱 코드 정적 검사 — `/apps/step_forge` 를 부르는 HTTP 메서드는 GET 뿐(POST/PUT/DELETE 0건). `gateway_config.json` diff 0.
5. 기존 8 chair e2e 각 1건 결정문 형식 불변. 단위 테스트(픽스처 tools-map) — apps 에 step_forge 없는 심의에서 `inspect_report` 차단, apps=['heax-step_forge'] 지정 시 `interface_graph`·`inspect_report` 가 자유조회 목록에 존재(`chair_template='default'` 에서도), `chair_template='default'`·apps 없음에서는 둘 다 부재(접두사 검문 그대로), `chair_template='default'` 에서 `_RISK_KEEP_TOOLS` 8종이 자유조회 목록에 없음, `chair_template='risk-review'` 에서 있음(apps 지정 유무 모두, `pcb_warpage_surrogate` 포함), `get_agent_session` 은 어느 조합에서도 부재.
6. `/심의 ` + `chair_template='risk-review'` 단발 심의 3회 — `parse_risk_spec` 성공 ≥2/3, 반대석 `origin=adversary` 착석 3/3, 지정 personas 의 `origin primary/counter` 가 `personas` SSE 이벤트에 보존 3/3, `extra_seats == ∅` 3/3.
7. `_persona_round`(:889-891) sysmsg 덤프(DELIB 디버그 로그 또는 `_llm_text` 입력 캡처)에서 `[리스크 심사 좌석 계약]`(`_common`)과 `[<dom>]` 줄이 원본 role 뒤에 검출 5/5석(합성 반대석 `delib-baseline-defender` 는 미부착, §6.5.4), `chair_template='default'` 에서는 0/6. SSE `personas` 이벤트는 role 을 280자로 잘라(:2090) 접미가 보이지 않으므로 검증 수단으로 쓰지 않는다.
8. apps=['heax-step_forge','heax-kooremapper_mcp'] 지정 상태에서 rel 좌석이 `search_objects` 를, sim 좌석이 `report_part_risk` 를 실호출한 SSE `status.step '<key> 조회: <tool>'` 또는 `evidence.source '<key> · <tool>'` 가 각각 ≥1(P0 (6) 의 3회 중) — 전자는 keep 경로(RA 앱이 apps 에 없음), 후자는 app+read 경로(접두사 검문 불통과)의 실증이다.
9. 러너 자격 실측 기록(context-notes.md, 대리 발급 없음 — §0.1.6). (a) `HWAXRISK_PORTAL_PAT`(서비스 계정, aud `mcp-gateway`, scope api)로 SIF 안 앱 프로세스에서 `POST {HWAXRISK_PORTAL_BASE}/agent/conversations {kind:'risk-review'}` 가 conv_id 를 돌려주고 `POST {HWAXRISK_PORTAL_BASE}/agent/chat` 이 200 + SSE `done` 까지 수신(`Accept: text/event-stream`, nginx `/agent/` 경유). (b) `PUT /api/me/portal-pat` 로 등록한 사용자 PAT 로 같은 호출 시 agent-server → 게이트웨이 → DynaForge `per_user_sso` 가 그 사용자 세션을 열어 `list_sessions` ≥1(세션 있는 사용자), (a) 서비스 PAT 로는 0건(정상 = `dyna_absent`). (c) aud 에 `mcp-gateway` 없는 PAT 는 `PUT /api/me/portal-pat` 422 `pat_audience`, `/agent/chat` 401, `exp − now < 86400` 인 PAT 는 422 `pat_expiring`. (a) 가 실패하면 폴백은 브라우저 세션이 아니라 §6.7.1 (B)(같은 박스 `HWAXRISK_AGENT_URL`)이며 P2 (8)·P3 (7) 의 기대값을 그 기준으로 바꾼다.
10. pytest 앱 `backend/tests/` 스키마 라운드트립 5종 통과, 무효 픽스처 거부 ≥10건, `parse_risk_spec` 픽스처(펜스 · 균형 중괄호 · 실패 null) 3종 통과.
11. 포털 프론트 `tsc -b && vite build` 통과, playwright — `/deliberate` Job 카드 8개 · 기존 7개 카드 텍스트 불변 · `/risk` 에 버튼 2개('HEAX 로그인'·'리스크 심사 열기') · `/risk` 체류 중 네트워크 캡처에 `/apps/hwax_risk/api/*` 요청 0건 · 타일이 안 보이는 그룹은 NavLink 4개. 앱 `frontend/` `pnpm install --frozen-lockfile && pnpm build` 통과, `dist/index.html` 존재.
12. 포털 무변경 — 포털 `openapi.json` 스냅샷 diff 0(`/api/risk/*` 부재, 포털에는 이 라우트가 존재한 적이 없다), `/agent/conversations` 생성·조회 응답이 변경 전 스냅샷과 동일, 포털 `config.py`·`.env.example` diff 0. 앱 정지(`heax_app_hwax_risk` stop) 전후 포털 홈·챗·심의·`/apps`·HEAX 카탈로그·`/apps/step_forge/` 응답 코드 동일(curl 표).
13. 앱 기동 3점 — 로컬(`uvicorn app.main:app --host 127.0.0.1 --port 8765 --root-path /apps/hwax_risk`)과 SIF 양쪽에서 `GET /api/health` 200 `{ok:true, app_version:'0.1.0', schema_version:1}`(첫 응답 ≤20 s, 빈 DB v1 DDL 적용 ≤1 s) · `POST /mcp` initialize 200 + `mcp-session-id` 헤더 + `tools/list` 6종 · `GET /` 가 `index.html`(`text/html`). Caddy `GET http://localhost:4180/apps/hwax_risk/` 익명 401, heax 쿠키 또는 `heax_pat_` 로 200·`/apps/hwax_risk/api/health` 200.
14. 매니페스트·등록 — `manifest_validator.validate_manifest` 수동 실행에서 루트 `mcp` 키와 `source.ref` 키(스키마 v2 미정의 — 루트와 `source` 가 `additionalProperties:false`, `tags` 는 루트 스키마에 있어 오류가 아니다) 외 오류 0(thermal 선례와 같은 2건만), 스캐너 즉시 트리거 `by_action` 에 `hwax-risk` 1건, 카탈로그 `GET /api/v1/apps` 에 `{id:'hwax_risk', status:'beta', visibility:'company'}`, `var/logs/sif_build_hwax-risk.log` 성공, `var/sifs/hwax-risk.sif`+`.hash` 존재, state 파일 `var/integration_state/hwax_risk.json` 존재, Caddy 설정에 `/apps/hwax_risk` 및 `/apps/hwax_risk/*` 라우트 2건, `var/logs/integration_hwax_risk.log` 에 uvicorn 기동 줄.
15. 게이트웨이 자동 흡수 — heax `GET /api/v1/mcp/servers`(서비스 PAT)에 `{id:'hwax_risk', path:'/apps/hwax_risk/mcp', transport:'streamable_http', allowed_groups:[]}` 1건, 게이트웨이 재시작 없이 `heax_registry.poll_s`×2 안에 `GET :9110/tools-map` 에 앱키 `heax-hwax_risk` 도구 `risk_*` 6종, 다른 백엔드 도구 수 불변(len 차 정확히 +6), `gateway_config.json` diff 0. 게이트웨이 경유 `risk_get_registry` 호출이 `{error:'not_implemented'}` 를 돌려준다(경로 실증).
16. 데이터 경로·app-data 왕복 — SIF 기동 후 호스트 `HEAXHub/var/app_data/hwax_risk/` 에 `risk_review.db`(`PRAGMA user_version`=1, rr_* 33표 + 살림 2표) · `origin.json`(`hostname` = dev 호스트명, `schema_version` 1) · `exports/` 존재, SIF 안 `/data` 내용과 동일. `appdata-to-drive.sh` 1회 → Drive `app-data/latest/` tar 에 `hwax_risk/risk_review.db`(`.backup` 스냅샷, `-wal`·`-shm` 제외) 포함 → `var/app_data/hwax_risk/` 를 비운 뒤 `appdata-merge-from-drive.sh` → 복원 DB `PRAGMA integrity_check` ok · `user_version` 1 · 표 수 동일. `redeploy-app.sh hwax-risk` 재기동 후 DB·`origin.json` 보존(inode 무관, 행 수 동일).
17. 신원 해석 — `GET /apps/hwax_risk/api/me` 가 (i) 쿠키 `heax_access_token` 만으로 `{email, source:'cookie', anonymous:false}` (ii) `Authorization: Bearer heax_pat_…` 로 `source:'bearer'` (iii) 위조 헤더 `X-Heax-User-Email: other@example.com` 을 함께 보내도 `email` 불변 (iv) 토큰 없음은 Caddy 401(앱 미도달) (v) 같은 토큰 10회 연속 호출에 heax `/api/v1/auth/me` 실호출 1회(TTL 60 s 캐시). `PUT /api/me/portal-pat` 오류 4종(`pat_invalid · pat_email_mismatch · pat_audience · pat_expiring`) 픽스처 각 1건 422, 정상 등록 시 `_user_credentials` 1행 · `GET /me.portal_pat.email` 일치 · `null` 로 삭제 시 0행.

리스크와 완화. `/mcp` 서브마운트 구성은 실측(mcp 1.29.1, 2026-08-31, D7)에서 슬래시 없는 `POST /mcp` 에 307 을 내 폐기했고, `Route('/mcp')` 이식(§0.4.1 ②)이 initialize 200 + `mcp-session-id` 까지 확인됐다 → (13) 은 이식 구성에서 재확인한다(`mount('/', mcp_app)`·`mount('/mcp', …)` 둘 다 금지). dev 런처가 SIF 가 아니라 호스트 프로세스로 띄우면 `launch.env` 의 `/data` 가 호스트 `/data` 를 가리킨다 → 매니페스트에서 그 줄을 빼고 `HEAX_DATA_DIR` 폴백만(§8.2.6). RA 관리자 PAT·AIDataHub API 키 발급 지연 → (2)(3) 을 보류하고 P1~P4 를 앱 DB 만으로 진행, 외부 반영은 `external_sync=unavailable`. 서비스 계정 포털 PAT·heax PAT 발급 지연 → (4)(9)(a) 보류, 러너는 `pat_unavailable`, P1 의 StepForge 읽기는 게이트웨이 MCP 경로(`HWAXRISK_PORTAL_PAT`)만으로 `mcp_degraded`. `source.url` 이 GitHub 가 아닌 `file://` 이면 cae00 스캔 fetch 실패 메일 반복 → §10 #24. `heax_registry.token` 계정이 hwax_risk 를 못 보면 (15) 실패 → `visibility company`+활성 사용자 확인(§10 #23). GLM 펜스 준수율 <95% → 균형 중괄호 폴백이 (6) 을 채우는지 기록.

이 단계만으로 얻는 것. 챗 핸드오프 카드 '리스크 심사' 와 MCP `hwax-deliberate chairTemplate:'risk-review'` 로 evidence 기반 단발 심사(결정문 8항목 + risk_spec + 기준선 옹호 지정석)가 즉시 돌아간다. 포털 메뉴 '리스크 심사' → HEAX SSO → 앱 셸 `/apps/hwax_risk/`(SettingsPage 에서 자기 포털 PAT 등록)이 열리고, 게이트웨이 `/tools-map` 에 `risk_*` 6종이 보이며(본문은 P1~P5 에서 채움), dev 의 app-data 백업·복원 경로가 검증된 상태다.

## 9.2 P1 단일 과제 IR 스냅샷·상태 평가·게이트·규칙(MCAD)

목표. StepForge 프로젝트 1건을 손실 없이 rr_ir 로 동결하고 rr_state·G1~G7·character_seed·rule_hits·feature_vector 를 코드로 낸다.

산출물(전부 앱 리포 `HWAXRisk`). `backend/app/risk_store.py` 쓰기 경로(P1 표 — rr_projects · rr_sources · rr_snapshots · rr_snapshot_calls · rr_ir_nodes · rr_ir_edges · rr_part_keys · rr_dim_vocab · rr_dim_defs · rr_states · rr_id_map, DDL 은 P0 v1 마이그레이션이 이미 만들었다), `backend/app/adapters/{mcad, ecad_stub}.py`(mcad 는 Caddy `{HWAXRISK_HEAX_BASE}/apps/step_forge/api` GET 원문 + 게이트웨이 MCP `heax-step_forge` 읽기, 자격 `HWAXRISK_HEAX_SERVICE_PAT`·`HWAXRISK_PORTAL_PAT`, §8.2.11), `ir_builder.py`, `sameas.py` v0(ckey 부여 · rr_part_keys candidate 등록 · 원장 재적용 골격, 사다리는 P2), `state.py`, `render.py`, `routes.py`(projects · sources · snapshots · dims · refs · rule_hits · meta/adapters choices), rr_rules 시드 6종 로드(`assets/rules-seed.v1.json`), 앱 `frontend/src/pages/{RiskHomePage, ProjectPage, SnapshotPage}.tsx`(HashRouter `#/` · `#/projects/:id?snapshot=`), `narrative.prior_evidence` v0(E0 · E1 · E9) + SnapshotPage '단발 심사 열기'(포털 `/deliberate` 를 새 탭으로 열고 E0·E1 텍스트를 클립보드에 복사 — 앱은 포털 `startHandoff` 를 부를 수 없다, §8.2.4), `ra_client` v0(게이트웨이 MCP `HWAXRISK_GATEWAY_MCP` 로 project · design_snapshot `create_object` upsert · `revision_of` `link_objects`, 포털 PAT Bearer, 비치명), `export.py` v0(`GET /api/export?since=` · `POST /api/import`, P1 표 11종, 첫 줄 헤더 `{schema_version, app_version, origin}`, 409 `schema_mismatch`), 골든 `backend/tests/golden/sif-e2e.ir.json`. 포털 변경 0.

의존. P0.

통과 기준.
1. sif-e2e(재파싱·재검출 후) 리프 노드 3·엣지 2 가 REST graph.json 과 일치, 2회 추출 ir_hash 동일, 같은 `(project_id, ir_hash)` 재요청 시 기존 snapshot_id 반환.
2. Caddy GET 원문(`HWAXRISK_HEAX_SERVICE_PAT`)만 읽고 StepForge sqlite mtime 불변(전후 stat 비교), 앱 → StepForge 호출 로그에 GET 외 메서드 0건.
3. world_center 가 tree.json world_transform 로 손계산한 값과 ±0.01 mm.
4. G1~G7 계산이 픽스처 5케이스와 일치, G6 fail 시 `blocked=true`, G7 은 pair 전용이라 snap 에서 `n/a`.
5. 500 파트 초과 합성 모델에서 노드 누락 0(REST), ir_builder ≤10 s.
6. render/summary 에 판단어 0(린터, 원천 인용 제외), rr_state 요약 각 줄에 `[p:]`/`[e:]`/`sig:`/`gate:` 참조 ≥1.
7. rule_hits 6종이 픽스처에서 기대값과 일치, 같은 IR 2회 → payload_hash 동일.
8. rr_snapshot_calls 에 모든 소스 호출 원문 gzip 저장, `GET /refs/tool:<call_id>` 가 원문을 돌려준다.
9. ckey 결정론 — 같은 파트 2회 추출 동일, 표시명 접미 `#2`·`_3` 변형 후에도 동일, 재료만 바뀌면 상이.
10. prior_evidence v0 — 항목마다 라인 `· [source · tool(args)] result` 길이 ≤ CAP(§5.6.1), 라인 합 ≤10600·result ≤2000, 엔진 로그 evidence 채택 수 == 보낸 항목 수(드롭 0), 판단어 0.
11. 앱 `ruff`·pytest(`backend/tests/`) 통과, 앱 `pnpm build` 통과, 기존 포털 `/deliberate` 스모크 통과, 포털 `/agent/*` 응답 동일(포털 코드 변경 0).
12. export/import 라운드트립 — `GET /api/export?since=0` 를 빈 DB 의 앱에 `POST /api/import` 하면 P1 표 11종 행 수·ir_hash 동일(`conflicts[]` 0), 헤더 `schema_version` 을 바꾼 JSONL 은 409 `schema_mismatch`, 같은 JSONL 2회 import 는 두 번째 `inserted 0`. 출력 사본이 `$HEAX_DATA_DIR/exports/<ts>.jsonl` 에 남는다.
13. 모델 출처(D6) — `PRAGMA table_info` 에 `rr_panels.model_json`·`rr_coverage.model` 존재. `runner.snapshot_model(origin)` 단위 테스트 — agent-server `GET /health` 픽스처 `{model:'qwen2.5-7b-dev', vllm:'http://127.0.0.1:8000/v1'}` 에서 `model_json{runtime:'agent-server', provider:'vllm', model, endpoint_host:'127.0.0.1', captured:'health_snapshot', engine_rev, chair_rev, seat_contract_rev}` 를 만들고, 시작·종료 픽스처의 `model` 이 다르면 `quality.flag` 에 `model_changed_midrun` 을 더하며(같으면 없음), 불통 픽스처(ConnectError·2 s 타임아웃)는 `{captured:'unavailable', model:'unknown'}` 에 예외 0. `GET /api/export` JSONL 의 `rr_panels`·`rr_coverage` 행에 두 컬럼이 실린다(P1 은 표만 있고 패널 실행은 P3 — 이 항목은 스키마·함수 검사다).

리스크와 완화. 기존 프로젝트 volume/material null → parse·detect 재실행은 사용자가 StepForge 에서 실행(화면 안내·앱 링크 `/apps/step_forge/`). heax 서비스 PAT 미발급 또는 StepForge visibility(team) 밖 계정 → Caddy 401 → `mcp_degraded` 강등 + `missing.world_transform_absent`(게이트웨이 MCP 경로만). 골든 프로젝트 부재 → §10 (15).

이 단계만으로 얻는 것. 앱 화면(`/apps/hwax_risk/`)에서 과제 등록 · 스냅샷 현황판 · 게이트 · 성격 씨앗 · 규칙 히트 · 단발 심사 브리프(E0 · E1 · E9), 그리고 dev↔cae00 데이터 이동 수단(export/import v0).

## 9.3 P2 Dyna 어댑터·same-as·원장·3층 diff·summary_text

목표. MCAD+Dyna 를 한 IR 로 합치고 두 스냅샷의 구조/파라메트릭/의미 diff 와 결론 없는 요약을 낸다.

산출물(전부 앱 리포). `backend/app/adapters/dyna.py`(`inspect_file`·`list_session_files`·`report_*` 읽기 — 게이트웨이 MCP `heax-kooremapper_mcp` 를 러너 자격 PAT 로 호출, (b) 사용자 등록 PAT 면 `per_user_sso` 사용자 세션 · (a) 서비스 PAT 면 0건 = `dyna_absent`(§8.2.11), 브리지 검증, `_group_of` 재구현), `sameas.py`(사다리 7단 · 헝가리안 · 원장 재적용 · ckey), `rr_sameas · rr_iface_ledger` 재적용·`ledger_needs_review` 규칙, `diff.py`(3층 · 임계 · comparability · rollup · 의미 이벤트 · 판단어 린터), `rr_diffs · rr_diff_events`, `routes.py`(sameas · iface-ledger · diffs), `mcp_server.py` `risk_get_snapshot`·`risk_get_diff` 실구현, 앱 `frontend/src/components/{SameAsResolver, GateBanner, DiffView}.tsx` · `pages/ComparePage.tsx`(`#/compare?base=&target=`), `prior_evidence` v1(E2 · E3 · E4), 합성 픽스처 6종(추가/삭제/kind_changed/두께/재료/이동), `ra_client` design_diff + `diff_of(role)`, `export.py` 표 추가(rr_sameas · rr_iface_ledger · rr_diffs · rr_diff_events).

의존. P1.

통과 기준.
1. 합성 쌍 6종에서 의미 이벤트가 정확히 해당 1건 + 오탐 0, 동일 스냅샷 self-diff 이벤트 0·delta 0.
2. 브리지 선언 케이스에서 mcad↔dyna same-as 정밀도 100%, 선언 없는 케이스는 name_norm/geom_fp 로만.
3. 이름 교란 20% 합성 30쌍에서 same-as 정밀도 ≥0.95·재현율 ≥0.9, score <0.9 auto 는 전부 `pending` 으로 G2 에 계수.
4. 원장 confirm 후 재캡처 스냅샷에 `status=manual_ledger` 복원, 기하 변화 시 `ledger_needs_review`.
5. tol 다른 쌍(G7 tol_parity fail)에서 gap 계열 delta 전부 `excluded_reason='tol_differs'`, kind 다른 리포트(result_parity fail)에서 result delta 없음.
6. summary_text ≤2000자 · 린터 위반 0 · 모든 줄에 `[c:]`, 정규 표기 문자열이 diff 항목 quote 와 축어 일치.
7. 노드 500·엣지 2000 에서 diff <5 s, 그때 앱 프로세스(SIF 인스턴스) RSS 피크를 context-notes 에 기록(§10 #27 의 입력 — 1.5 GB 초과면 매니페스트 `memory_gb` 상향).
8. (a) 서비스 PAT 만 있는 타깃에서 DynaForge `list_sessions` 0건이 정상 결과로 처리되어 `missing.dyna_absent=true` 기록 · 예외 0 · 다른 사용자 세션 노출 0, (b) 등록 PAT 가 있는 타깃에서만 그 사용자 세션의 K파일·리포트가 IR 에 들어간다. 앱 코드에 `kr_`·`X-Heax-Gateway-Secret` 문자열 0건.
9. energy_flow.edges 의 src/dst 가 pid 인지 픽스처로 확정·context-notes 기록.
10. G2 fail 인 pair 에서 diff 는 생성되되 의미층이 `semantic.blocked_by='G2'`(이벤트 0건, §3.3.1) 로 표기, `POST /targets` 는 허용(진입 허용·표기 강제).
11. 같은 파트를 다른 프로젝트명·다른 인스턴스 접미·다른 자동명으로 넣은 합성 두 프로젝트에서 ckey 일치율 ≥0.95, subject_key 일치율 ≥0.95(§5.9.6). 같은 프로젝트의 합성 리비전(§4.9 PROTECT_FILM 두께 −25%·OCA_TOP 부피 +50% 변형)에서 §2.7.3 자동 승계(`rr_part_keys` 에 `decided_by='code:pair_correspondence'` 행 2건)를 거친 subject_key 일치율 ≥0.95, §4.9 픽스처의 F2·G1 cluster_key 가 DV1→DV2 동일.

리스크와 완화. 러너 자격 (b) 미등록(P0 (9)(b) 결과 의존) → dyna 소스는 `dyna_absent` 로 진행하고 TargetPage 가 "DynaForge 사용자 데이터는 서비스 시야" 경고를 띄운다(§10 #4). DynaForge 실데이터(세션 0·리포트 0) → 사용자가 세션·리포트를 먼저 만든다(§10 (15)). fuzzy pending 누적 → G2 가 의미층만 막는 정상 동작.

이 단계만으로 얻는 것. 앱 화면의 두 과제 비교(3층 diff · before/after 그래프 · 결론 없는 요약)와 pair 단발 심사(E0~E4), 게이트웨이 도구 `risk_get_snapshot`·`risk_get_diff` 로 다른 심의가 스냅샷·diff 를 읽는 경로.

## 9.4 P3 risk-review 패널 e2e·서술 저장(단일 패널, 웹·MCP L1)

목표. 패널 1건을 웹 엔진에서 돌려 결정문+risk_spec 을 파싱해 좌석 의견·finding·성격을 3층에 저장하고, MCP 단발(L1) 결과를 `/panels/{id}/complete` 로 원장에 넣는다.

산출물(전부 앱 리포). `backend/app/narrative.py` 완성(cites 해석 · dangling · evidence_grade 자동 산출 · seat_opinion 추출 · E0c 계약 항목 · prior_evidence v2 E0~E4+E9), `runner.py` 단일 패널 모드(§6.7.1 (A) — 포털 `POST {HWAXRISK_PORTAL_BASE}/agent/chat` 을 포털 PAT Bearer 로 · 러너 자격 결정 (a) `HWAXRISK_PORTAL_PAT` / (b) `_user_credentials` 등록 PAT · `POST /agent/conversations {kind:'risk-review'}` · SSE 캡처 §0.2.3 · 사전 예산 게이트 · 커버리지 갱신 · `quality_json.{call_path, credential, call_groups[]}` 기록 · (B) 폴백 규칙), `registry.py` 병합기(cluster_key · contested · verdict 후보), `character.py`(L2 panel 진술 저장), `ra_client`(게이트웨이 MCP — assessment · risk_finding · exhibits `create_object`+`link_objects` · 보고서 tags 병합 `get_report` 후 `update_report_draft`, 항상 서비스 PAT), `adh_client`(REST `POST {HWAXRISK_AIDH_BASE}/api/records/import?external_source=hwax-risk`, `X-API-Key`, UPSERT `risk_review_opinion · risk_review_panel`), `rr_targets · rr_panels · rr_seat_opinions · rr_findings · rr_registry · rr_claim_refs · rr_character` 쓰기 경로, `routes.py`(targets · targets/{key}/jobs 단일 패널 · panels/{id}/complete · targets/{key}/resync · refs), `mcp_server.py` `risk_get_registry · risk_claims_for_ref · risk_submit_panel_result` 실구현, 앱 `frontend/src/pages/TargetPage.tsx` 최소(패널 1건 실행 · 결과 표 · 등록부 · `credential`·`call_path` 배지 · '재동기') + `components/PanelTranscript.tsx`(앱 DB 로 렌더, conv_store 미접촉), decision-table.md 갱신, SSE 픽스처 스트림 3종(정상 · 도구 0 · 오류). 포털 변경 0.

의존. P0 · P2.

통과 기준.
1. 웹 1패널(6석 · 3R)에서 risk_spec 파싱 성공, findings ≥3 · gains ≥1 · facet 8종 존재(na_reason 허용) · dangling 0(`name:` 해석 포함).
2. 좌석 도구 사용률 ≥80%(귀속 가능 좌석 기준) · IR 인용률 ≥50% · 반대석 기각 ≥1건이 등록부 `contested` 에 기록.
3. `personas` 이벤트 좌석 집합 == seats(로스터) ∪ {adversary} AND `extra_seats == ∅`, origin primary/counter 보존. 러너가 보낸 요청 페이로드에 `human_note`·`continue_summary` 키 부재(단언).
4. SSE 귀속 성공률 ≥95% — 픽스처 스트림 3종에서 `status.step '<key> 조회: <tool>'` → `tool_calls_n`, `evidence.source '<key> · <tool>'` → `tool_calls_ok` 가 기대 표와 일치(지정 도구 결과는 0 귀속). 같은 픽스처를 `events[]` 로 압축해 `POST /panels/{id}/complete {engine:'web', events[]}` 로 보내는 경로(§8.2.3)에서도 귀속 성공률 ≥0.95 이고 SSE 직접 경로와 같은 `tool_calls_n/ok`, `events[]` 없이 보내면 `tool_calls_ok=null`·`used_tool=null`.
5. 패널 대화가 포털 conv_store 에 `kind='risk-review'` · owner = 호출 PAT 의 sub 로 저장되고 `/deliberate` 목록에 0건 노출, 제목 접두 `[리스크심사]`, `rr_panels.conv_id` 에 그 id, `quality_json.call_path='portal'`, `credential ∈ service|owner` 가 3단계 결정과 일치. 앱 TargetPage 의 패널 기록은 앱 DB 만 읽는다(네트워크 캡처에 `/agent/conversations` 호출은 러너의 `tool:conv:` 해석뿐).
6. AIDataHub 재실행 시 레코드 중복 0(`external_source=hwax-risk`, `_external_id` UPSERT), RA assessment `create_object` 2회 호출 시 `created:false`, 의견 레코드 `agents` 배열에 실 전문가 키 0건. 앱 런타임 로그·코드에 `rat_`·`RA_ADMIN_PAT` 0건(RA 쓰기는 게이트웨이 서비스 자격).
7. 러너 자격 지속 — (b) 등록 PAT 가 있는 타깃에서 패널 시작 70분 뒤 두 번째 패널에서도 같은 PAT 로 DynaForge 도구 호출 성공(재발급 없음, `pat_exp > now + timeout_s` 검사만), `pat_exp` 를 `now + timeout_s − 1` 로 조작한 픽스처에서는 (a) 로 강등되어 `credential='service'` · `quality.pat_degraded=true` · dyna absent 표기. (a) 만 있는 타깃은 처음부터 dyna absent 표기(P0 (9)(a) 결과 기준).
8. 사전 예산 — 좌석 6 · rounds 3 산정이 `risk_panel_llm_cap`(120) 이내면 rounds 3, 초과 예상이면 rounds 2 로 편성. 실측 LLM 호출 ≤120 · 벽시계 ≤20분, agent-server 로그 실측 호출 수와 `est_low~est_high` 의 차이 ≤30%(§6.10.2). 사후 초과 시 `quality.flag=over_budget` 만 붙고 재실행 0(rr_panels 행 수 불변).
9. MCP `hwax-deliberate chairTemplate:'risk-review'` 단발 결과를 게이트웨이 도구 `risk_submit_panel_result(panel_id, 'mcp', decision_text, turns, report_id, actor)` 또는 REST `POST /api/panels/{id}/complete {engine:'mcp'}` 로 보내면 원장에 `tool_mode=evidence_only` 로 반영, 좌석은 `done`·`tool_calls_n=null`, `quality_json.actor` + `actor_verified:false` 기록, `owner_sub` 는 패널 행 승계(actor 로 바뀌지 않음), 두 경로의 `rr_findings` 행이 바이트 동일(같은 파서).
10. `evidence_profile` 헤더와 seat_opinion 합계 불일치 시 `quality.flag=header_mismatch` 가 붙는 픽스처 1건.
11. 기존 `/deliberate`·핸드오프 회귀 0, 포털 `openapi.json` diff 0.
12. 등록부 병합 멱등 — 같은 패널 결과로 `registry.merge(target)` 를 2회 실행해도 `rr_registry` 행·`rr_delta_contrib`·`rr_delta_priors` 값이 바이트 동일(§4.7.1, §4.10).
13. 폴백 (B) — `HWAXRISK_AGENT_URL=''`(기본)이면 (A) 연결 오류 3회 후에도 (B) 로 가지 않고 패널 `error(retry+1)`; dev 에서 `HWAXRISK_AGENT_URL=http://127.0.0.1:9009` 로 켜고 (A) 를 막으면 3회 후 (B) 로 패널 1건 완주하며 `call_path='agent_direct'` · `conv_id=null` · 진행판 `direct` 배지, 원장 계수는 (A) 와 동일. (A) 에 401 을 주입하면 폴백 없이 `rr_jobs.error='pat_unavailable'`, 잡 state 불변.
14. `POST /api/targets/{key}/resync` — `external_sync.ra='unavailable'` 타깃이 `pending(attempts=0, next_at=0)` 으로 돌아가고 `sync_loop` 다음 주기(≤60 s)에 재시도 1회, 비소유자 403.

리스크와 완화. GLM 펜스 준수율 <95% → 균형 중괄호 폴백, 실패는 `risk_spec_parsed=false` 로 남기고 재실행 후보(자동 재실행 없음). RA 관리자 PAT 부재 → `external_sync.ra=unavailable`, C 레벨 판정과 무관. 서비스 계정 포털 PAT 부재 → 러너 `pat_unavailable`, 이 단계는 (b) 등록 PAT 를 가진 사용자 타깃으로만 검증한다.

이 단계만으로 얻는 것. 등록부 · 성격 서술 · 좌석 의견이 3층(앱 DB 정본 · RA · AIDataHub)에 저장되는 완결 심사 1건과 MCP 결과의 원장 반영, 러너 경로 (A) 의 감사·conv_store 동반 실증.

## 9.5 P4 커버리지 원장·편성·배치 러너·완결 판정·통합 보고서

목표. 로스터를 Tier A/B/C 로 소진하는 배치를 원장 상태기계 위에서 돌리고 레벨별 통합 보고서를 낸다.

산출물(전부 앱 리포). `backend/app/planner.py`(Tier · 라운드로빈 · 인접 표 · deferred · carried · 결정론), `rr_roster · rr_coverage`(부분 유니크 인덱스 `rr_cov_active`) · `rr_jobs` 쓰기 경로, `runner.py` 배치 모드(`panel_loop` 세마포어 `risk_concurrency` · pause/resume/cancel · 수확 체감 정지 · 일일 상한 · 재기동 복구, 호출 경로는 P3 과 같은 (A)), 완결 판정 C1~C3(`registry.py`), 통합 보고서 조립기(게이트웨이 MCP 로 RA `deliberation` 템플릿 v1/v2/v3), 앱 `frontend/src/pages/TargetPage.tsx` 완성 + `components/{CoverageHeatmap, PanelRunner}.tsx`(Tier · 자격 표시 · verdict 확정 · 미착석 배지), `GET /api/meta/metrics`, `HWAXAgentServer/tools/delib_metrics.py` 지표 6종 추가(원천 = 앱 `GET /api/meta/metrics`, heax 서비스 PAT — 도구 사용률 · IR 인용률 · 근거등급 분포 · out_of_range · 반대석 기각률 · 클러스터 중복률), 상태기계 불변식 테스트(`backend/tests/test_coverage_sm.py`). 포털 변경 0.

의존. P3.

통과 기준.
1. Tier A 3패널 완주 후 15 도메인 종결 ≥1 → `level='C1'`, 통합 보고서 v1 생성. **RA 미가용 상태(게이트웨이 `reportarchive` 백엔드 불통 또는 RA 도구 403 — `HWAXRISK_PORTAL_PAT` 자체는 유효)에서도 C1 도달**하고 `external_sync.ra='unavailable'` 로 표기(RA 는 C 조건이 아니다).
2. 원장 불변식 통과 — 상태별 카운트 합 = roster_size, running 좌석 ≤ 5 × running 패널, done/done_weak 는 opinion_id 보유, 같은 (target_key, agent_key) 이중 착석 0.
3. 편성 결정론(같은 입력 2회 → 같은 seats_json), 동시 편성 2회 호출에도 같은 전문가 이중 착석 0(rowcount ≠ 5 롤백).
4. 패널 실패 주입 시 5석 `pending(retry 1)` 복귀, 3회 실패 후 `skipped(reason=engine_fail)`.
5. ecad_absent 타깃에서 ECAD 의존 도메인이 대표 1석 외 `deferred(reason=ecad_absent)` ≈105석.
6. 새 스냅샷 타깃에서 carried 가 조건(cited_refs≠∅ · used_tool · ckey 교집합 ∅ · ≤ risk_carried_days) 충족 좌석에만 적용되고, 화면에서 pending 으로 되돌릴 수 있다.
7. Tier B 완주 벽시계 ≤6 h(concurrency 2), 배치 중 사용자 대화형 심의 슬롯 점유 ≤2, 일일 상한 24 초과 시 `paused(reason=daily_cap)`.
8. done_weak 비율이 quality 에 기록되고 C2 strong 비율(MCP 패널 제외)에 반영, 파싱 실패 패널 >0 이면 C2 미달.
9. 진행판에 '미착석 N명(C3 미달)' 배지가 C3 전까지 상시 표시되고 N = 비종결 + deferred 제외 로스터 수와 일치.
10. `risk_default_close_level='C3'` 로 두면 C2 에서 `closed` 가 되지 않고 Tier C 승인 프롬프트가 뜬다. 기본 C2 에서는 `level='C2(closed)'` 와 minutes 에 미착석 도메인·미소진 인원 기록.
11. 수확 체감 정지 — 최근 3패널 신규 클러스터 <1 AND C1 → `paused(reason=diminishing)` 픽스처 1건.
12. 재기동(`redeploy-app.sh hwax-risk` 또는 HEAX 인스턴스 `heax_app_hwax_risk` stop/start) 후 `running` 패널이 `error(retry+1)`·5석 `pending` 으로 복구되고 잡이 이어진다. 포털 conv_store 의 그 대화는 그대로 남고 `conv_id` 로만 연결된다.

리스크와 완화. 야간 GPU 점유 · dev 박스 OOM(메모리 dev-box-oom-pattern) → 일일 상한 · concurrency 1 옵션. 매니페스트 `memory_gb 2` 가 cgroup 으로 강제되면(enforce_instance_limits) 배치 중 RSS 를 P2 (7) 기록과 비교해 §10 #27 로 올린다. xd 편중 → Tier C 규칙(xd 최대 3석 · 비-xd ≥2석).

이 단계만으로 얻는 것. "전체 HW/XD 전문가가 한 번씩" 회계(C3 가 문자적 충족, C2 는 비용 타협)와 레벨별 리스크 심사 보고서.

## 9.6 P5 재사용 루프 — 브리프 되먹임·유사 검색·delta 선례·포털 MCP 앱·MCP 오케스트레이터

목표. 이전 등록부·성격 진술·전문가 기억·delta 선례가 다음 타깃 evidence 로 자동 들어가고, 계보 없는 과제에서도 같은 부품·계면의 finding 이 떠오르며, 다른 심의가 등록부를 읽고, MCP 에서 원장 연동 배치(L2)가 된다.

산출물. 앱 리포 — `backend/app/narrative.py` `prior_evidence` 완성(E5~E8 · 계면 별칭 · kNN · hybrid_search · agent_search(risk-review-memory) · 예산표), `rr_delta_priors · rr_iface_alias`, `rr_part_keys` merge/rename UI(앱 `ProjectPage`), `mcp_server.py` `risk_get_brief(target_key, tier='B')` 실구현(P0 골격 채움 — 게이트웨이 `heax-hwax_risk` 흡수는 P0 (15) 에서 끝났고 설정 변경 0), 성격 프로파일 승격 UI(seed → panel → confirmed, AIDataHub `project_character` UPSERT), `components/RecallPreview.tsx`, `GET /api/precedents`, `GET /api/projects/{id}/similar` 4경로. 엔진·포털 리포 — `deliberation.py` `_RISK_READ_TOOLS['heax-hwax_risk']`(앱키는 registry 발견값이라 A 계획의 `'hwax-risk'` 가 아니다, §8.3.5), `HWAXPortal/infra/pipeline/hwax-risk-review.js`(L2 오케스트레이터, args `{targetKey, tier, panels?, actor?, model?}`) + `sync-workflows.sh`.

의존. P4.

통과 기준.
1. 같은 과제 계보의 두 번째 타깃 evidence 에 E5(등록부) · E6(성격) · E7(좌석 발췌) · E8(delta 선례)이 실리고 라인 합 ≤10600 · 항목 ≤12 · 엔진 로그의 evidence 채택 수 == 보낸 항목 수(드롭 0) — 12항목 전부를 상한까지 채우고 args 를 최대 길이(`diff:`+hex32 37자, E7 은 agent_key 5개)로 둔 픽스처로 검증한다.
2. kNN 이 합성 유사 스냅샷을 top1 로 회수(상대 순위만).
3. `agent_search('risk-review-memory', required_tags=['hwax:expert:<a>'])` 가 그 전문가의 이전 발췌를 top-3 에 포함(5명 표본 재현율 ≥0.8), E7 슬롯이 좌석당 줄 ≤220자 · 좌석 합 ≤1100자 · 항목 라인 ≤1400자 를 지킨다.
4. 후임 패널에서 `narr:` 또는 `reg:` 를 인용한 finding ≥1, 브리프에 없는 `narr:`/`reg:` 인용은 dangling 처리.
5. **계보 없는 합성 과제**(revision_of 없음, 다른 connectivity)에서 같은 ckey 쌍 계면이 `rr_iface_alias` 를 거쳐 이전 과제 finding 을 E5 로 회수 ≥1.
6. sim-plan 심의 좌석이 apps 에 `heax-hwax_risk` 를 넣고 `risk_get_registry` 자유조회 성공(SSE `status.step '<key> 조회: risk_get_registry'` ≥1), `/tools-map` 도구 수는 P0 (15) 기준 불변(`risk_*` 6종은 이미 P0 부터 노출), apps 에 넣지 않은 심의에서는 `risk_*` 가 자유조회 목록에 없음.
7. MCP 워크플로 `hwax-risk-review.js` 1패널이 `risk_get_brief(target_key, 'B')` → `hwax-deliberate` → `risk_submit_panel_result` 경유로 원장 `done`, `engine=mcp` 배지, `tier:'A'` 요청은 `{error:'tier_a_web_only'}`(REST `GET /api/targets/{key}/brief?tier=A` 는 422). 워크플로는 포털 REST 를 fetch 하지 않는다(스크립트에 `fetch(` 0건).
8. prior_evidence 문장 판단어 0, `[선례 없음 — n=0]` 부정 증거 항목이 첫 사례에 실린다.
9. MCP 호출자 귀속 — 게이트웨이 경유(heax 서비스 PAT 신원) `risk_submit_panel_result.actor` 가 `quality_json.actor` + `actor_verified:false` 로 기록되고 `owner_sub` 는 패널 행 승계, `risk_get_brief` 는 요청 actor 가 owner 인 타깃과 `visibility='org'` 행만 돌려주며 actor 미해석(빈 값·형식 위반)이면 `reason='caller_unresolved'`·빈 결과. 앱 코드는 `X-HWAX-User`·`X-Heax-User-*` 헤더를 읽지 않는다(grep 0건).

리스크와 완화. e5 코사인 절대값 편향 → 상대 순위만(메모리 e5-embedder-baseline). 게이트웨이 `heax_registry.token` 계정이 hwax_risk 를 못 보면 도구가 사라진다(company 라 활성 사용자면 통과, §10 #23). 워크플로 실행 환경에 포털 PAT 가 없으면 `actor` 는 args 필수(§10 #13).

이 단계만으로 얻는 것. 배치가 쌓일수록 브리프가 두터워지는 폐루프, 다른 connectivity 회수, 다른 심의(sim-plan 등)가 게이트웨이 도구로 등록부를 읽는 경로, Claude Code 에서 돌리는 L2 보충 회차.

## 9.7 P6 학습 루프 — 라벨·지표·패턴 승격·규칙 백테스트·조직 공유 정책

목표. 실측(incident/test_run/후속 리포트)으로 finding 을 검증해 규칙 후보를 승격하고 학습 곡선을 계측한다.

산출물(전부 앱 리포). `rr_labels · rr_patterns · rr_rules(active 승격) · rr_metrics · rr_curation_queue` 쓰기 경로(DDL 은 P0 v1), 라벨 동기 잡(`sync_loop` 확장 — RA incident · test_run 은 게이트웨이 MCP 읽기, DynaForge 후속 리포트는 러너 자격 PAT, SignalForge VOC 는 게이트웨이 도구, 수동은 `PUT /api/registry/{cluster}/status`), 조건 DSL 평가기 · 백테스트(시간순 홀드아웃), 지표 대시보드(앱 `TargetPage` 하단 '품질' 카드, `GET /api/meta/metrics`, dataviz 규약) · '루프 작동' 배지, `risk_pattern_card` doc_type(`bootstrap_adh.py` 추가), `visibility` 정책(org 토글, §10 #11 결정 후, `owner_sub` 조회 예외), RA 'risk-review' typed 템플릿 등록 절차서(관리자, RA 코드 무수정). 포털 변경 0.

의존. P5.

통과 기준.
1. RA incident 픽스처 3건 동기에서 match_score 1.0 만 auto confirmed, 그 외 큐(자동 확정 0).
2. 수동 라벨 20건 후 expert/domain/mechanism 차원 precision · calibration · lead_time 산출, n<5 는 '표본 부족' 표기.
3. 합성 코퍼스(30타깃, 패턴 2종)에서 candidate 2건 정확 표면화 · 거짓 후보 0.
4. rule 승격 API 가 백테스트 미달(precision <0.6 또는 recall <0.5 또는 n_labeled <10) 시 422, 승격 후 새 스냅샷 rule_hits 에 즉시 반영.
5. rule_hits 결정론(같은 IR 2회 → payload_hash 동일).
6. 택소노미 큐 map/new 처리 후 taxonomy_version 증가 · 이전 값 보존 · 기존 finding 재매핑 스크립트 dry-run 0 오류.
7. S2 게이트(n_labeled ≥50 · project ≥15) 미충족 시 예측기 학습 코드 0줄.
8. `visibility=org` 토글 후 타 사용자가 등록부를 읽되 쓰기 0, 토글 전 타 사용자 읽기 0.

리스크와 완화. 라벨 유입 속도 → 지표가 n<5 로 오래 머묾(정직하게 표기). 공유 정책은 사용자 결정. 두 박스 운영이면 라벨·승격은 정본 박스(§10 #21)에서만 하고 dev 는 export/import 로 받는다.

이 단계만으로 얻는 것. 검증된 선례·규칙과 루프 작동 여부의 계측(앱 DB 에 누적, `GET /api/meta/metrics` 로 엔진 지표 스크립트가 읽음).

## 9.8 P7 ODB 실연동·예측기 승격(조건부)

목표. ODB hub 가 계약을 이행하면 ECAD 를 IR 1.1 로 편입하고, 라벨이 충족되면 예측기 앱 계약을 이행한다.

산출물. 앱 리포 `backend/app/adapters/ecad.py`(계약 4도구 `odb_get_board · odb_list_components · odb_list_nets · odb_get_stackup` — `adapters/registry.py` 가 `/tools-map` 도구명 집합으로 발견, ODB hub 는 external_link 라 게이트웨이 백엔드가 아니므로 계약 이행 시 별도 MCP 노출이 선행), ir_version 1.1(`MIGRATIONS` v2 — 컬럼 추가만), refdes↔파트 사전 UI(앱 `ProjectPage`), `ecad.*` 의미 이벤트, SedInput 매핑 어댑터(`predict_sed` 를 좌석 도구로 — `_RISK_KEEP_TOOLS` 에 이미 있음), 예측기 MCP 앱 계획서(thermal_shock 수명주기 복제 — hwax_risk 와 같은 HEAX 앱 등록 절차 §8.4.4 3, 별도 리포·별도 매니페스트, 라벨 원천은 hwax_risk `GET /api/export`).

의존. P6(예측기) · P2 이후 언제든(ECAD 어댑터, 계약 합의 시).

통과 기준.
1. 계약 테스트 4도구 스키마 · 상한(컴포넌트 2000 · 넷 5000) 통과, 초과 시 `truncated` 경고.
2. ODB 샘플 1건에서 component↔mcad same-as 정밀도 ≥0.9, `missing.ecad_absent=false`, deferred 좌석이 새 타깃에서 pending 재생성.
3. `predict_sed` out_of_range 시 finding.precedent='out_of_range' 자동 강등.
4. 예측기는 n_labeled ≥50 · project ≥15 확인 전 활성화 불가(활성화 API 422).

리스크와 완화. ODB hub 구조 미상 — 계약이 바뀌면 어댑터만 교체(IR 은 ir_version 으로 흡수).

## 9.9 의존·병행·예산 요약

| 단계 | 선행 | 병행 가능 | 패널 비용(§6.10) | 사용자 결정 필요(§10) |
|---|---|---|---|---|
| P0 | — | 문서·스키마·parity·엔진 additive(D)는 즉시. 앱 스캐폴드(A)와 포털 창(C)은 서로 병행. HEAXHub 등록(B)은 앱 로컬 `/api/health`·`/mcp`·`/`(P0 (13) 로컬 절반) 통과 후. RA/AIDataHub 부트스트랩은 (1)(10) 승인 후. app-data 왕복(16)은 SIF 기동 후 | 단발 3회 | 착수 전 필수 (3)(23)(24) · 기본값으로 진행 가능 (1)(8)(10)(16)(17)(18)(19)(20)(25) |
| P1 | P0 | 프론트 3화면은 P0 (13) 뒤 바로. `export.py` v0 는 표 11종 쓰기 경로 뒤 | 0 | (15)(14)(14b)(2) |
| P2 | P1 | dyna 어댑터는 P0 (9)(b) 결과 확정 후 | 0 | (4)(15)(15a)(14a)(14c)(27) |
| P3 | P0·P2 | narrative/registry 는 P2 와 병행(픽스처 diff 로). 러너 (A) 경로는 P0 (9)(a) 통과 후 | 1패널 ≈50~95회 | (3)(6a)(6c)(17) |
| P4 | P3 | planner 결정론 테스트는 P3 와 병행 | Tier A 3패널, Tier B +14~20(§6.4.1 로스터 실측 산술) | (5)(6)(7)(6b)(12a) |
| P5 | P4 | `hwax-risk-review.js`·`_RISK_READ_TOOLS['heax-hwax_risk']` 는 P3 뒤 착수 가능(앱 MCP 흡수는 P0 (15) 에서 완료) | 후임 타깃 1건 | (8a)(13)(13a)(26) |
| P6 | P5 | — | 0(라벨·지표) | (11)(12) |
| P7 | P6 / P2+(9) | ECAD 어댑터는 계약 합의 즉시 | — | (9)(14a) |
| cae00 이관(단계 아님, §8.4.4 6) | P3 통과 + (21)(22) | dev 검증 뒤 언제든. 이관 뒤 dev→cae00 데이터 이동은 `GET /api/export` → `POST /api/import` 뿐 | 0 | (21)(22)(18) |

비용 표에서 'toulmin 켜면 parse_retries 하한 2' 줄은 삭제했다 — 하한 2 는 `rebut_quote` 조건이고 그것은 `search_sources` 가 있을 때만 켜진다. 120 초과는 사후 재실행이 아니라 사전 편성(rounds 2)과 사후 `over_budget` 표기다. 표의 '사용자 결정 필요' 번호는 §10 개정 번호이고, A 계획의 (3) 대리 발급·(13b) 게이트웨이 백엔드 수동 등록·(16) X-HWAX-User 대조는 B 에서 사라져 각각 (3) 러너 자격·자동 흡수(결정 없음)·(16) 되묻기/(17) actor 로 바뀌었다.

# §10 열린 질문·결정 필요

사용자가 답해야 하는 것만 모았다. 항목마다 질문 · 답이 없을 때 계획이 가정하는 기본값 · 영향 단계 · 결정이 필요한 시점을 적는다. 번호는 §9.9 표가 참조한다. B 개정으로 사라진 결정 — 포털 sqlite 저장·포털 Settings·`risk_review_enabled` 플래그·게이트웨이 백엔드 수동 등록(구 13b)·사용자 PAT 대리 발급(구 3)·`X-HWAX-User` 대조(구 16) — 는 표에서 뺐고, 새로 생긴 결정은 17~28 번과 §10.8 이다. 어떤 항목도 답이 없다고 P0~P4 가 멈추지 않는다 — 기본값 열이 그 상태에서 계획이 취하는 동작이다.

## 10.1 승인·보안

| # | 질문 | 기본값(미결 시) | 영향 | 시점 |
|---|---|---|---|---|
| 1 | RA 시스템관리자 PAT — B 에서는 포털 secrets 가 아니라 `backend/scripts/bootstrap_ra_ontology.py --base <RA REST 오리진> --apply` 를 돌리는 실행자 셸 env `RA_ADMIN_PAT` 로 1회만 쓰고, 앱 런타임·`secrets.env` 에는 두지 않는다(이후 인스턴스 쓰기 4종 `create_object · update_object · add_object_alias · link_objects` 는 게이트웨이 서비스 `rat_` 경유). 관리 REST 부트스트랩 1회를 승인하는가(RA 코드 무수정) | 미승인 — P0 (2) 보류, P1~P5 는 앱 DB 만으로 진행, `external_sync.ra='unavailable'`. C 레벨 판정은 영향 없음 | P0 (2) · P3 (6) · P4 (1) | P0 착수 전 |
| 2 | 게이트웨이 `rest.heax` 필요 여부 — B 기본은 불필요다(앱이 `HWAXRISK_HEAX_SERVICE_PAT` 로 Caddy `/apps/step_forge/api` 를 GET 으로 직접 읽는다, §8.2.11). 그래도 앱 자격을 포털 PAT 하나로 통일하려고 게이트웨이 `rest.heax`(heax 서비스 토큰 inject, GET/HEAD 만)·`portal.audience_ok`·포털 `PAT_DEFAULT_AUDIENCES` 3곳을 바꿀 것인가. 둘 다 싫으면 StepForge 에 `export_ir` 읽기 도구 1개 추가(코드 변경 · SIF 재빌드)를 허용할 것인가 | 불필요 — 설정 변경 0, heax 서비스 PAT 발급(§8.2.7). 셋 다 불가면 어댑터 `mcp_degraded`(world 좌표 결측) | P0 (4) · P1 (2)(3) | P1 착수(선택) |
| 3 | 러너 자격(§0.1.6, 대리 발급 없음) — (a) 서비스 계정 포털 PAT `HWAXRISK_PORTAL_PAT` 발급을 승인하는가(발급 계정 · groups 는 소스 앱 `heax-step_forge`·`heax-kooremapper_mcp`·RA·AIDataHub 백엔드가 요구하는 그룹 전부 · scope api · aud `mcp-gateway` · ttl 365 일). (b) 사용자가 앱 SettingsPage 에서 자기 포털 PAT 를 등록하는 UX(`PUT /api/me/portal-pat`, 동의 문구 §8.2.4)를 P0 에 두는 것을 승인하는가 | (a) 승인 가정 · 발급 계정 = cae-automation 서비스 계정 · (b) P0 포함. (a) 미승인이면 러너 `rr_jobs.error='pat_unavailable'` — 스냅샷·diff·L1 단발은 되고 무인 패널만 멈춘다(브라우저 세션 폴백 없음) | P0 (9) · P3 (7) · P4 전체 | P0 |
| 4 | DynaForge 사용자 스코프 — `per_user_sso.kooremapper_mcp` 는 호출 PAT 의 email 로 발동하므로 (b) 등록 PAT 가 있는 타깃만 사용자 세션을 본다(P0 (9)(b) 실측). (b) 미등록 타깃의 dyna 소스를 `dyna_absent` 로 둘 것인가, DynaForge 세션 visibility 를 department 로 넓혀 서비스 시야로 읽게 할 것인가 | `dyna_absent` 강등 + TargetPage 경고(§8.2.4) | P2 (8) · P3 (7) | P0 (9) 직후 |
| 16 | 브라우저 신원 해석 — 앱 `identity.py` 가 전달된 쿠키 `heax_access_token`/Bearer 로 heax `GET /api/v1/auth/me` 를 되묻는 방식(HEAX 무수정, §8.2.8)으로 갈지, HEAXHub `proxy_manager._build_route/register_app_route` 에 `copy_identity`(launch.portal_auth 게이트, integration_launcher 호출 지점 4곳) additive 를 넣어 `X-Heax-User-*` 를 받을지 | 되묻기(HEAX 무수정). additive 를 채택해도 되묻기가 정본이고 헤더는 보조 확인 | P0 (17) · §5.2.1 소유권 | P0 |
| 17 | MCP 호출자 귀속 — 게이트웨이 경유 호출은 heax 서비스 PAT 신원이라 `risk_submit_panel_result.actor` 를 미검증(`actor_verified:false`)으로 기록하고 `owner_sub` 는 패널 행을 승계한다(§6.11). 이대로 갈지, HWAXMcpGateway 가 `heax-` 백엔드에 `x-hwax-user` 를 전달하도록 바꿀지(게이트웨이 코드 변경) | `actor` 미검증 · 게이트웨이 무수정 | P0 mcp 시그니처 · P3 (9) · P5 (9) | P5 착수 전 |
| 18 | 앱 시크릿 보관 — `$HEAX_DATA_DIR/secrets.env`(0600)과 `_user_credentials`(앱 DB)는 `appdata-to-drive.sh` 가 `var/app_data` 전체를 Drive 로 밀 때 함께 나간다. ① 그대로 두고 PAT ttl ≤365 로 노출 한도만 둘지, ② HEAX `appdata-to-drive.sh` 에 제외 패턴(`*/secrets.env`)을 additive 로 넣을지(HEAX 스크립트 변경), ③ 앱이 DB 컬럼을 암호화할지(키 보관처가 또 필요) | ① — 무기한 PAT(`ttl_days 0`) 금지 · ttl 365 · 회전은 파일 교체 + 앱 재기동 | P0 (16) · §5.2.5 (3) · §8.2.7 | P0 |
| 19 | HEAX 콜백 딥링크 — `portal_sso.py` 에 allowlist(`/heax-hub/apps/<slug>/`)된 `next` form 필드와 포털 `LinkedSystem` 필드 1개(`downstream.py:76` fields) additive 를 넣어 `RiskLaunchPage` 2단을 1단으로 만들지 | 미채택 — 2단 UX(§8.1.3). 채택 시 HEAXHub·포털 두 리포 변경 | P0 C · §8.1.3 | P0(선택) |

## 10.2 데이터 소스 계약

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 9 | ODB hub 어댑터 계약 4도구(`odb_get_board · odb_list_components · odb_list_nets · odb_get_stackup`, 상한 컴포넌트 2000 · 넷 5000)와 refdes 명명 규약을 ODB 모듈 소유자와 합의해야 한다. 게이트웨이 manifest `mcp:{}` 자동 발견으로 붙을 수 있는가 | 계약 문서 `odb-adapter-contract.md` 만 두고 코드는 `ecad_stub`. ECAD 의존 도메인 6 은 deferred | P7 (1)(2) · 로스터 deferred ≈105석 | P2 이후 언제든 |
| 14a | 크로스도메인 부품 명명 규칙(ECAD refdes ↔ MCAD 파트명 ↔ Dyna `Group\Name`)이 조직에 있는가. 있으면 `name_norm_canon` 사전 규칙으로, 없으면 과제별 수동 사전(`rr_part_keys` merge/rename) | 없음 가정 — 사다리 `title_norm/name_norm → fuzzy → manual` | P2 (2)(3) · P5 (5) · P7 (2) | P2 착수 |
| 14c | ckey 의 geom_bucket volume 축 — 현재 5% 로그 버킷은 두께·부피를 손댄 리비전에서 계산 ckey 를 바꾸고 §2.7.3 자동 승계(결정론 pair 대응)가 이를 잇는다. volume 축을 2배(log2) 버킷으로 완화할지, geom_bucket 에서 빼고 size 3축 0.5 mm 버킷만 둘지(계보 없는 과제 간 정확 매치가 늘고 승계 의존이 줄어드는 대신 크기가 같고 부피만 다른 부품이 한 키로 묶인다) | 5% 유지 + 자동 승계(계획안). 바꾸면 `rr_part_keys.geom_bucket`·`rr_ir_nodes.ckey` 재계산 스크립트 1건과 ir_version 유지(ckey 는 ir_hash 입력이므로 기존 스냅샷은 재계산하지 않고 유효 ckey 재해석만) | P2 (11) · P5 (5) · §5.9.4 | P2 착수 |
| 15 | 기존 StepForge 프로젝트 재파싱·재검출(volume/material 채움, 노드 id 재부여)을 사용자가 StepForge 에서 실행하는 절차와 골든 프로젝트(sif-e2e) 준비. DynaForge 는 세션 1건 · K파일 1건 · 리포트 1건 이상이 선행 조건이다 | 사용자 실행. 없으면 P1 (1) · P2 (8)(9) 는 합성 픽스처로만 | P1 · P2 | P1 착수 전 |
| 15a | Dyna 결과 리포트↔K파일 결속은 DynaForge 가 모른다. 스냅샷 생성 시 사용자가 `report_ids` 를 지정하는 방식(`bridge_declared`)으로 충분한가 | 지정 방식. 미지정이면 `missing.dyna_result_absent` | P2 (5)(9) | P2 |

## 10.3 저장소·공유

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 10 | AIDataHub — 의견 레코드의 team/group 값(앱 과제 등록 화면에서 사용자가 1회 입력 · 자동 채움 금지)과 열람 범위, 의사 에이전트 `risk-review-memory` 를 `create_agent` 로 만드는 것, `external_source=hwax-risk`(구 `hwax-portal`), hwax-risk 용 `X-API-Key`(`HWAXRISK_AIDH_API_KEY`)의 발급 주체, 실운영 `AUTH_REQUIRED` 값(false 면 키 없이 anonymous 쓰기가 통과하지만 앱은 값과 무관하게 항상 키를 보낸다)의 승인·확인 | 승인 가정, 키는 AIDataHub 관리자 발급. 미승인이면 `external_sync.adh='unavailable'`, E6·E7 은 앱 DB 만으로 조립(agent_search 경로 없음) | P0 (3) · P3 (6) · P5 (3) | P0 |
| 8a | 좌석 개인 기억 회수 — 계획은 의견 레코드 `agents` 에 실 전문가 키를 넣지 않고(지식카드 오염 방지) `risk-review-memory` + E7 고정 슬롯(좌석당 줄 ≤220자)으로 회수한다. 대안은 레코드 `agents` 에 실 전문가 키를 넣되 `required_tags`·`retrieval_config` 는 건드리지 않는 것이다(사실 맵 권고). 어느 쪽인가 | 계획안(의사 에이전트 + E7) | P5 (3) | P5 착수 |
| 11 | `rr_findings · rr_registry · rr_patterns · rr_metrics · rr_iface_alias · rr_delta_priors` 의 조직 공유(`visibility=org`) 여부와 범위(dept 단위인가 전사인가). 기본은 private | private, P6 (8) 에서 토글 구현 | P6 (8) · hwax-risk 결과 범위 | P6 |
| 12 | RA 'risk-review' typed 템플릿(findings table · coverage key_value)과 report_type(`design-review` · `product-review`) 등록 시점과 주체. RA hands-off 라 관리 설정으로만 가능하다 | P6 전까지 `deliberation` 템플릿 + tags | P6 절차서 | P6 |
| 12a | 통합 보고서 DOCX 내보내기가 필요한가(RA 보고서 링크와 화면 렌더만으로 충분한가) | 불필요 — RA 보고서 v1/v2/v3 만 | P4 | P4 |
| 20 | app-data 백업 주기·보존 — dev crontab 에 HEAXHub `deploy/apptainer/appdata-to-drive.sh` 를 일 1회 어느 시각에 둘지(`build-all-to-drive.sh` 안의 호출은 빌드 때만 돈다), Drive `RETAIN` 5 를 유지할지, dev 실행이 `app-data/latest/` 를 덮는 것을 감수할지(§5.2.5 (7) ③ — cae00 은 타임스탬프 폴더로만 식별) | 일 1회 03:30(DB 는 `.backup` 원자 스냅샷이라 야간 배치 중에도 안전), RETAIN 5, `latest/` 는 백업일 뿐 동기 채널이 아님 | P0 (16) · §5.2.5 (3) | P0 |
| 21 | 데이터 정본 박스 — 운영 정본을 cae00 으로 두고 dev 는 검증·시드 박스로 둘지(§5.2.5 (7)), 아니면 cae00 미이관·dev 단일 정본으로 갈지. 사람 확정(원장 4표 · `verdict_final` · 큐레이션)은 정본 박스에서만 하고 배치 러너도 정본 박스에서만 켠다 | cae00 정본 + dev 검증. 이관 전까지 dev 가 임시 정본 | P4 이후 운영 · P6 라벨 · export/import | cae00 이관 전 |

## 10.4 전문가 범위·마감 수준

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 5 | 로스터 도메인 15(`risk_roster_domains`)와 ECAD 의존 도메인 6(`risk_ecad_domains`)의 확정. cam·soc·std·material(1명)을 HW/XD 로 볼지, xd 122명 전원을 로스터에 넣을지(Tier C 에서 xd 최대 3석 규칙) | 15 · 6 · xd 전원 | P4 (5)(9) · 비용 | P4 착수 |
| 6 | 기본 마감 레벨 — 요구('전원 한 번씩')의 문자적 충족은 C3 이고 C2 는 비용 타협이다. `risk_default_close_level` 을 C2 로 둘지 C3 로 둘지, Tier C 명시 승인제와 일일 상한 24 · concurrency 2 가 GPU 예산(Tier C ≈5~15 h/타깃)에 맞는가 | C2 + Tier C 승인제 + '미착석 N명(C3 미달)' 배지 상시 | P4 (7)(9)(10) | P4 착수 |
| 7 | carried 규칙의 90일 유효기간(`risk_carried_days`)과 ckey 교집합 기준이 조직 관행에 맞는가. 리비전마다 전원 재심을 원하면 carried 를 끈다(0일) | 90일 | P4 (6) | P4 |
| 6a | 패널당 LLM 호출 상한 120(`risk_panel_llm_cap`)과 초과 예상 시 rounds 2 편성이 허용되는가(3R 이 아니면 반박 라운드가 1회로 준다) | 120 · rounds 2 강등 | P3 (8) | P3 |

## 10.5 어휘·사전

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 8 | 성격 통제 어휘 v1(`character-vocab.v1.json` 7축)과 택소노미 v1(8축)의 확정 주체(설계 XD 리더 제안)와 `x:` 자유 태그 승격 임계(타깃 3 · 패널 2) | 초안 그대로, 승격은 큐레이션 큐 + 사람 승인 | P0 문서 · P6 (6) | P0(초안) · P6(확정) |
| 14 | 이름 있는 치수 사전(`rr_dim_vocab`)의 초기 항목(예 `battery_to_frame_gap · hinge_plate_thickness · display_to_housing_gap`)을 누가 정하나. 과제 유형별 필수 디멘전 템플릿이 필요한가 | 빈 사전으로 시작, 과제에서 `POST /projects/{id}/dims` 로 정의한 이름이 candidate 로 쌓인다 | P1 dims · E3 | P1 |
| 14b | 규칙 시드 6종(`rules-seed.v1.json`, §3.2.6 — R-001 interference_auto_present · R-002 tight_clearance_cluster(min_gap ≤0.2 mm ≥5) · R-003 thin_leaf_tied_both_sides(min_dim ≤0.3 mm) · R-004 unit_mismatch_warning · R-005 cross_file_with_suspect_coords · R-006 dyna_contact_without_mcad_tie)의 임계값 승인과 시드 밖 후보 R-007~R-009(§7.5)의 채택 여부 | 초안 임계 | P1 (7) | P1 |

## 10.6 예산

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 6b | 로컬 vLLM GLM 의 야간 배치 창(시각 · 시간)과 dev 박스 메모리 상한(세션 적체 OOM 이력) — Tier B ≈3~5.5 h, Tier C ≈5~15 h 를 어느 창에 돌릴지 | 야간 22:00~06:00, concurrency 2, 일일 24 | P4 (7) | P4 |
| 6c | RA · AIDataHub 외부 반영 재시도 큐의 보관 기간(무기한인가, N일 후 `unavailable` 확정인가). 되돌리기는 소유자의 `POST /api/targets/{key}/resync` | 30일 후 `unavailable` 확정(attempts ≥ 8 도 동일), 화면 '재동기' 버튼 | P3 (14) · P4 | P3 |
| 27 | 앱 리소스 — 매니페스트 `resources{cpu 1, memory_gb 2, gpu false}` 는 `enforce_instance_limits` 활성 시 cgroup 으로 강제된다. SQLite + FastAPI + 러너 스레드 2(SSE 스트림 ≤2)에 2 GB 가 충분한지를 P2 (7)(노드 500 · 엣지 2000 diff)와 P4 배치 중 RSS 로 확인한다 | 2 GB 유지. 측정 RSS 피크가 1.5 GB 를 넘으면 `memory_gb: 3` · `version 0.1.1` 로 매니페스트 편집 | P0 매니페스트 · P2 (7) · P4 | P2 |

## 10.7 워크플로·MCP

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 13 | Workflow 스크립트(`hwax-risk-review.js`)의 앱 접점은 게이트웨이 도구 `risk_get_brief`·`risk_submit_panel_result` 둘뿐이라 포털 REST fetch 허용 여부는 B 에서 영향이 없다(§8.3.4). 남는 질문 — `actor` 이메일을 실행 환경의 포털 PAT(`HWAX_PAT` 관행) email 클레임에서 채울지, args 로 받을지 | PAT 가 있으면 그 email, 없으면 `args.actor` 필수(비면 앱이 `caller_unresolved`) | P5 (7)(9) | P5 착수 |
| 13a | MCP 경로 패널을 `evidence_only` 로 원장에 넣되 C2 strong 비율에서 제외하는 비대칭을 받아들이는가. 받아들이지 않으면 MCP 경로는 L1 단발로만 두고 L2 를 만들지 않는다 | 비대칭 수용(§6.11) | P5 (7) | P5 |
| 26 | `mcp.allowed_groups` — 빈 목록(전체 공개)으로 시작한다. 그룹 스코핑을 걸 것인가, 걸면 어떤 포털 그룹 이름(예 `portal-admin` 은 포털 `config.upload_allowed_groups` 에서 확인됨)인가. 값이 있으면 러너 서비스 PAT 의 groups 와 교집합이 있어야 좌석 자유조회에 `risk_*` 가 남고(§6.7.1), 게이트웨이 `heax_registry.token` 계정 가시성과는 별개다 | `[]` 유지. 접근 통제는 앱 REST 의 `owner_sub`·`visibility` 로 | P0 매니페스트 · P5 (6) | P5 |

## 10.8 앱 등록·배치(B 신규)

| # | 질문 | 기본값 | 영향 | 시점 |
|---|---|---|---|---|
| 22 | cae00 이관 승인·시점 — §8.4.4 6 절차(dev `build-all-to-drive.sh` → cae00 `update.sh` 또는 `deploy-all-from-drive.sh` → reconcile 이 `var/sifs/hwax-risk.sif` 로 기동 → cae00 포털·heax·AIDataHub 에서 서비스 PAT·heax PAT·API 키 재발급 → cae00 `secrets.env` → `redeploy-app.sh hwax-risk` → '재동기')를 언제 처음 돌릴지, cae00 쪽 서비스 계정 3개를 누가 만들지. dev 에서는 `deploy-all` 류를 돌리지 않는다 | P3 통과 후 첫 이관, 승인 전까지 dev 에서만 운영. cae00 사내 TLS 프록시(메모리 hwax-server-ops-gotchas)라 빌드는 dev 에서만 | 운영 · (21) · §5.2.5 (5) | P3 통과 후 |
| 23 | 매니페스트 확정값 승인 — `id hwax_risk · name HWAX Risk Review · owner cae-automation · status beta · visibility company · resources{1, 2, false}`. `team` 을 원하면 owner(seed admin)의 `seed_admin_org` 와 포털 SSO 사용자 `organization('')` 일치를 cae00 `.env` 에서 먼저 확인해야 한다(불일치면 카탈로그·MCP 레지스트리에서 통째로 안 보이고 게이트웨이 흡수도 안 된다). `stable` 승격 시점 — `stable`+`company` 는 익명 통과(`portal_auth` 없음)라 앱 `identity.py` 의 익명 읽기 규칙이 실제로 발동한다 | 표기값 그대로. `stable` 은 P4 통과 후 매니페스트 `status` 편집(`version` 도 올림) | P0 (14)(15) · §8.2.2 | P0 착수 전 |
| 24 | 리포 위치 — `source.url` 을 GitHub 공개 리포 `https://github.com/squall321/HWAXRisk.git`(ref main)으로 둘지, 사내 미러로 둘지, dev 전용 `file:///home/koopark/claude/HWAXRisk` 로 둘지. `file://` 은 cae00 스캔이 5분마다 fetch 실패를 FAILED 로 기록하고 운영자 메일을 낼 수 있다(integrations_scanner.py:291-305 근거, 빈도는 추정). 공개 리포면 사내 IP·시크릿·호스트명을 커밋하지 않는다(메모리 stc-cluster-usage) | GitHub 공개 리포 `squall321/HWAXRisk`. 리포에 `.env`·`secrets.env`·`data/` 를 `.gitignore` | P0 (14) · cae00 스캔 | P0 착수 전 |
| 25 | 러너 엔진 호출 경로 승인 — (A) 앱 → 포털 `POST /agent/chat`(포털 PAT Bearer, 감사로그·세마포어·conv_store 동반)을 정본으로 두고, (B) 앱 → agent-server `:9009` 직접(무인증 · 같은 박스 · 앱이 groups 를 자칭)을 `HWAXRISK_AGENT_URL` 이 설정된 박스에서만 연결 오류 3회 후 폴백으로 허용하는 것(§6.7.1). (B) 를 아예 금지할지 | (A) 정본, (B) 는 기본 꺼짐(`HWAXRISK_AGENT_URL=''`) — dev 에서만 켜 P3 (13) 실측 | P0 (9) · P3 (13) · P4 | P0 |
| 28 | 스캐폴드 관례 확정 — 실존 리포 `/home/koopark/claude/HWAXRisk`(2026-08-31, 커밋 0건 P0 스캐폴드)가 이 계획서와 이름·레이아웃이 달랐다(리포명 `HwaxRisk`·env 접두 `HWAX_RISK_`·`backend/`+`frontend/`·`fastapi_react`·`/api`·`/api/health`·MCP 6종·`_schema_migrations`·company·2 GB ↔ 실존 `HWAXRisk`·`HWAXRISK_`·루트 `app/`·`fastapi`·`/api/v1`·`/health`·MCP 3종·`schema_migrations`·team·1 GB). **이름은 실존 리포를 따르는 것으로 이 개정에서 확정했다** — 리포 `HWAXRisk`·GitHub `squall321/HWAXRisk`·`source.url https://github.com/squall321/HWAXRisk.git`·env 접두 `HWAXRISK_`(Settings 속성명 `risk_*` 는 그대로). **레이아웃은 결정이 필요하다** — (i) P0 착수 시 계획대로 `backend/`+`frontend/`+`build.stack fastapi_react` 로 이동, (ii) P0 는 루트 `app/`+`fastapi` 로 두고 SPA 가 들어오는 P1 착수 시 전환(§8.2.1 단계 표기). 어느 쪽이든 §9.1 A-δ 의 코드 델타(마운트·신원·MCP 6종·살림 표 이름·매니페스트 값·헬스 경로·REST prefix·자산 위치·DB 파일명)는 P0 착수 즉시 적용한다. 정본은 이 계획서 하나이고, 앱 `context-notes.md` D2 의 '경로·이름은 이 노트가 정본' 선언과 `/api/v1`·`hwax_risk.db` 표기는 이 결정 뒤 계획서 값으로 고친다 | (i) — 리포 커밋 0건이라 이동 비용 ≈0 이고 P0 통과 기준 (11)(13)·SettingsPage(#3 (b)) 계약이 그대로 선다. (ii) 를 고르면 P0 (11) 의 `pnpm build` 와 SettingsPage 가 P1 로 밀린다 | P0 A·A-δ · §8.2.1 · §8.2.2 · P0 (11)(13)(14)(15)(16)(17) | P0 착수 전 |

번호가 겹치는 보조 항목(8a · 12a · 14a 등)은 같은 결정 묶음의 하위 질문이다. 위 표의 어떤 항목도 답이 없다고 P0~P4 가 멈추지 않는다 — 기본값 열이 그 상태에서 계획이 취하는 동작이다. 답이 오면 `docs/design-risk-review/context-notes.md`(앱 리포 `HWAXRisk/context-notes.md` 에도 같은 항목)에 결정과 근거를 적고 앱 Settings 기본값·매니페스트 값·문서 임계값을 그에 맞춘다.
