# 설계안 반박 검토 결과 (2026-10-08)

## 기존 코드 정합 (fit)

**판정** 설계안의 뼈대(카드 대조는 혼자 먼저, 토의는 쟁점만)는 이 코드베이스에 얹을 수 있고 지금 구조보다 목표에 맞다. 지금은 좌석당 지식카드가 3,500자(한 전문가 카드 평균 57,072자의 6.1%)만 실리고, 그 선별 질의에는 변경 어휘가 없다. 다만 세 운반체 후보는 모두 그대로는 못 쓴다. 띵킹 모드는 소집·상한·시간 한도·저장이 챗용이고, 심의 엔진은 최소 2석·1R 스키마 고정에 근거 예산이 128K 창에서 약 17,967자이며, 리스크 앱에는 LLM 클라이언트도 LLM 비밀도 없다. 그래서 1~3단계는 에이전트 서버에 새 모듈(thinking.py 처럼 deliberation 의 순수 헬퍼만 가져다 쓰는 card_review)로 두고, 앱이 변경 묶음·카드 묶음 동결·검증·셀 원장을 맡는 구성이 가장 작다. 그대로 두면 목표를 못 이루는 곳은 다섯이다(1단계가 조용한 누락 관문이 되는 것, 원장·완결 판정이 묶음×전문가를 못 담는 것, 카드 전량을 실을 예산이 없는 것, 카드 판정 전수성과 인용 검증을 코드가 보장하지 않는 것, 타깃당 직렬 실행). 첫 걸음은 새 단계가 아니라 브리프 결함 셋을 고치는 것이고, 이것만으로 지금 도는 패널 전부가 나아진다.

### 치명 결함과 고치는 법
- **결함** 1단계(카드 제목 30개 + 묶음 한 줄 요약만 보는 짧은 LLM 판정)가 관문이 되면 '해당 없음 + 이유' 가 조용한 누락 통로가 된다. 그 전문가는 묶음 전량도 카드 본문도 보지 않은 채 빠지는데, 커버리지 표에는 칸이 채워져 '빈 칸 없음' 이 달성된 것으로 읽힌다. ECAD 어댑터가 스텁이라 회로 변경 이벤트가 없으므로 ECAD 6개 영역 110명(30.6%)은 대부분 이 길로 빠진다.
  - 근거: HWAXPortal/docs/thinking-mode/context-notes.md D2(예심 탈락 AND) · HWAXRisk/backend/app/planner.py:141-147(ecad_absent 면 rank≠1 을 deferred) · config.py:41(_DEFAULT_ECAD_DOMAINS) · 측정값(pcb19+pwr18+rf19+soc20+passive18+mem16=110)
  - 고침: 탈락을 AND 로 둔다. 결정적 신호(카드 태그·부품명·재료명 어휘 겹침, hybrid_search(agent_type, q=묶음 질의) 적중)가 전부 0 이고 자기판정도 '무관' 일 때만 2단계를 건너뛴다(띵킹 D2 와 같은 규율). 애매하면 2단계로 보내고, '해당 없음' 은 묶음 전량과 카드 전문을 본 2단계의 출력으로도 받는다. 셀 상태를 넷으로 가른다 — reviewed · na_irrelevant(사유+신호값) · no_input(입력 부재, ECAD 등 — 지금의 deferred/ecad_absent 승계) · unreviewed/failed. no_input 은 '검토함' 비율에 세지 않는다. na 셀의 일정 비율을 무작위로 2단계에 태워 거짓 '해당 없음' 비율을 지표로 남긴다.
- **결함** 원장·스키마·완결 판정이 (묶음 × 전문가)를 담지 못하고, 5단계가 기존 제약과 충돌한다. rr_coverage 는 PK(target_key, agent_key), rr_seat_opinions 는 UNIQUE(target_key, agent_key, cycle)라 1~3단계에서 의견을 남긴 전문가를 5단계 패널에 다시 앉히면 persist_panel_result 의 INSERT 가 유일 제약에 걸린다(DELETE 는 같은 panel_id 만 지운다). plan_next_panel 은 pending 좌석만 집는다. close_level 의 C1 은 Tier A 패널 done ≥ 3 을 요구해 패널 없이 개별 검토만 돈 타깃은 영영 C0 다. 기본 마감 C2 는 114/359명(31.8%)에서 닫히고, 최근 3패널 신규 클러스터 0 이면 잡이 자동 정지하며, 일일 패널 상한 기본 24 가 걸린다. 마이그레이션은 CREATE TABLE·ADD COLUMN·CREATE INDEX 만 허용이라 UNIQUE 를 못 푼다.
  - 근거: HWAXRisk/backend/app/risk_store.py:262,322,561 · narrative.py:1697-1704 · planner.py:375,844 · registry.py:945 · runner.py:32,738,1390 · config.py:209-210
  - 고침: 개별 검토를 rr_panels 행으로 흉내 내지 않는다(일일 상한 24·수확 체감 정지·타깃당 running 1 불변식에 전부 걸린다). 스키마 v2 로 새 표를 더한다 — rr_bundles · rr_review_cells(PK target_key, bundle_id, agent_key) · rr_card_packs(동결 원문) · rr_card_verdicts · rr_expert_reports. rr_coverage 행은 그 전문가의 셀이 전부 종결됐을 때 한 번 닫는 롤업으로 남기고('전문가는 타깃마다 한 번' 유지), rr_seat_opinions 에는 3단계 보고서 요약 1행만 쓴다. 5단계 패널은 rr_coverage 를 건드리지 않는 별도 편성 함수(planner.plan_dispute_panel)로 만들고, 그 패널의 좌석 발언은 rr_seat_opinions 가 아니라 rr_panels 에 ADD COLUMN 한 turns_gz 에 둔다. close_level 에 '셀 unreviewed·failed 0' 규칙을 더하고 Tier A 패널 수 조건은 패널 경로에만 남긴다.
- **결함** 2단계의 '자기 카드 전부(약 30장 원문) + 묶음 변경 전량 + 도구' 를 실을 그릇이 지금 없다. 심의 엔진의 좌석 근거 예산은 128K 창에서 17,967자로 떨어진다(직전 라운드 몫 48,000자와 도구 스키마 40,000토큰을 먼저 뗀다). 한 전문가 카드 평균 57,072자는 그 3.18배, 최대 91,780자는 5.11배다. 도구를 바인딩한 한 호출에 전부 실으면 최악 토큰 환산(1.05자/토큰)에서 p95 전문가부터 창을 넘는다.
  - 근거: HWAXAgentServer/deliberation.py:166,202,206-235(_pre_budget·_evid_budget) · :4047(2석 미만이면 no_personas) · :4403-4411(1R 스키마 lens·reads·recommendation·concerns 고정) · HWAXPortal/backend/app/agent/routes.py:89(rounds ge=2) · deliberation.py:3001-3005(조회 턴과 발언 턴을 가른 이유)
  - 고침: 새 모듈이 자기 예산을 갖는다(직전 라운드 몫 없음). 엔진이 이미 쓰는 두 턴 분리를 따른다 — ① 조회 턴(도구 바인딩, 문맥은 묶음 + 카드 제목만, _free_gather_one·_tools_for_seat 재사용) ② 판정 턴(도구 없는 텍스트 턴, 카드 전문 + 묶음 전량 + 조회 결과). 판정 턴 잔여는 평균 전문가 약 54,242토큰(약 56,954자), 최대 전문가 약 21,187토큰(약 22,246자)이므로 묶음 본문 상한(예: 20,000자, 넘으면 하위 조립 단위로 쪼갠다)과 카드 묶음 분할 규칙(창을 넘으면 카드 K장씩 결정적으로 나눠 여러 번)을 0단계·2단계 계약에 못 박는다. 카드는 JSON 원문이 아니라 본문 텍스트 + id 로 렌더해 구조 오버헤드를 뺀다.
- **결함** '카드마다 판정' 의 전수성과 4단계 검증을 지금 코드가 보장하지 않는다. card: 인용은 external_check 가 연결돼 있지 않아 늘 ok·미검증으로 통과하고, canonical_text_for 에 card 분기가 없어 인용문 대조를 건너뛰며, 그 인용 하나로 등급이 '문헌·규격' 이 된다. 코퍼스 카드의 67.9% 가 heuristic 등급인데도 그렇다. 출력 쪽에서는 30~35장 판정 JSON 이 max_tokens 에서 잘리거나 모델이 일부 카드를 건너뛰어도 알 길이 없고, 앱의 SSE 수집은 좌석 발언을 2,000자에서 자르므로 상세 보고서가 turns 로는 못 온다. 대조는 정확 부분문자열(quote not in canonical)이라 공백·개행만 달라도 불일치가 된다.
  - 근거: HWAXRisk/backend/app/narrative.py:213,644-651,496-579(card 분기 없음),719,768,1666 · engine_client.py:44,183,202 · HWAXAgentServer/deliberation.py:1641-1655(max_tokens 절단 표식) · :1658-1707(validator 훅) · 측정값(heuristic 15,877/23,378)
  - 고침: 앱이 카드 묶음을 직접 받아 gz 로 동결하고(freeze_brief 와 같은 방식, pack_hash) 그 묶음을 모델에 보낸다. 검증은 네트워크가 아니라 동결본으로 한다 — SpecContext 에 card_pack 을 더해 _resolve_one 의 card 분기와 canonical_text_for 의 card 분기를 채운다. 출력 계약을 압축한다 — 위반 가능·주의·판단 불가는 {card, quote, change_ref, why}, 문제없음·무관은 id 배열. 코드가 'id 합집합 == 묶음의 카드 id 집합' 을 검사하고 빠진 카드만 다시 묻는다(_persona_round 의 validator 훅 재사용). 인용 실재는 호출 안 검증(재시도 1회)과 앱 사후 검증 두 번 보고, 대조는 공백 정규화 후 포함으로 한다(_norm_ws). 등급은 카드 tier 로 매긴다 — fact 이고 sources·standard_refs 가 있으면 문헌·규격, heuristic·expert-judgement 는 경험칙. 결과는 turns 가 아니라 전용 프레임(잘리지 않는 decision 자리 또는 새 kind)으로 내린다.
- **결함** 실행 단위가 타깃당 직렬이다. claim_next_job 은 그 타깃에 running 패널이 있으면 건너뛰고, 불변식 (2)도 타깃당 running 패널 1개를 요구한다. HWAXRISK_CONCURRENCY=2 는 타깃 사이의 동시성이다. 2단계 호출이 묶음 8개·관련 비율 35% 가정에서 약 1,005회인데 이것이 한 타깃 안에서 한 줄로 돈다. 또 PortalPanelEngine.run 은 실행마다 포털 대화를 하나 만들므로 셀 수만큼 대화가 쌓인다.
  - 근거: HWAXRisk/backend/app/runner.py:714-760,1528-1548 · planner.py:840-847 · engine_client.py:354-358(실행마다 create_conversation) · HWAXAgentServer/thinking.py:52-56
  - 고침: 셀 러너를 패널 루프와 따로 둔다 — RiskRunner 에 review_loop 와 전용 세마포어(새 설정 HWAXRISK_REVIEW_CONCURRENCY)를 더하고, 셀끼리는 서로를 읽지 않으니 타깃 안에서 병렬로 돌린다. 패널 불변식·일일 상한·수확 체감 정지는 셀에 적용하지 않는다. 포털 대화는 셀마다 만들지 않는다(전문가당 1개 또는 생략 — 정본은 앱 DB). 공유 LLM 을 심의·띵킹과 나눠 쓰므로 에이전트 서버 쪽 모듈에도 자체 세마포어를 둔다(띵킹이 180초→600초로 올린 사유가 바로 이 경합이다).

### 개선
- [걸음 1 — 가장 작은 첫 걸음] 브리프 결함 셋을 고친다(앱 리포만, 스키마·엔진 불변). ① brief._item_e3·_item_e4 가 diff_json 최상위가 아니라 diff_json.parametric 에서 dims_delta·result_delta 를 읽게 한다. ② brief._item_e2 정렬을 abs(magnitude) 로 바꾼다. ③ runner.panel_question 의 '요약 첫 줄' 과 roster.query_text 를 summary_text 머리가 아니라 [의미]·[치수]·[재료] 구획(부품명·변경 종류)에서 만든다.
  - 이유: 지금 패널 전부가 즉시 나아진다. diff 타깃의 치수·결과 칸이 늘 비어 나가고, 감소 변화가 먼저 잘리며, 좌석 지식카드 질의(q=패널 질문)와 로스터 순위 질의가 '[대상] base … ir=…' 신원 줄과 비교가능성 깃발로만 만들어진다 — 변경 어휘가 0 이다. 재사용 = render._summarize_diff 의 구획, render.event_text·param_text. 위험 = 브리프 해시가 바뀌어 brief_drift 가 전 패널에 찍힌다(1회성), strict_lint(판단어) 에 새 문구가 걸릴 수 있다, 로스터 순위는 이미 고정된 타깃에는 반영되지 않는다(freeze_roster 는 INSERT OR IGNORE).
  - 비용: 반나절~1일. 검증 = tests/test_brief.py·test_runner.py 에 '감소 변화가 남는다'·'diff 타깃 E3·E4 가 비지 않는다'·'질문에 부품명이 든다' 시험 추가 후 pytest 전체. 실주행 = dev 의 기존 diff 타깃으로 패널 1건, GET /api/panels/{id}/brief 에서 E3·E4 본문과 질문 문자열 확인.
- [걸음 2] 카드 원문 받는 길 + card 인용 검증(4단계를 먼저, 기존 패널에도 적용). AIDataHub REST GET /api/records 에 doc_type 쿼리 인자를 더한다(query_records 는 이미 doc_type 을 받는다 — 라우트가 안 넘길 뿐). 앱은 adh_client 에 GET 메서드와 agent_cards(agent_key) 를 더하고, narrative.SpecContext.external_check 를 실제로 배선하며 canonical_text_for 에 card 분기를 넣는다. 등급은 카드 tier 로 매긴다. knowledge_hits_n 은 SSE evidence 의 '<좌석> · 지식카드' 소스로 센다.
  - 이유: 새 단계 없이도 값이 난다 — 지금 등록부의 card: 인용이 처음으로 실재·인용문 대조를 받고 등급이 바로잡힌다. 그리고 2단계가 쓸 '한 전문가 카드 전부를 한 번에' 가 생긴다. 지금은 한 호출로 받는 길이 없다 — MCP list_records(agents, doc_type, limit≤100)는 요약 200자만 주고 본문은 get_record 를 카드마다 불러야 한다(전문가당 1+약 30회, 전체 359+10,774=11,133회). REST 목록은 content 를 주지만 doc_type 을 못 걸러 논문·특허까지 딸려 온다. 위험 = 등급이 내려가 등록부 priority 가 움직인다(W_GRADE 0.8→0.6), ADH 불통 시에는 지금처럼 '미검증' 으로 남겨 회귀가 없게 한다, 좌석이 본 것은 700자 스니펫이라 스니펫이 카드 본문의 부분문자열인지에 따라 불일치가 늘 수 있다(미확인).
  - 비용: ADH 2~3줄 + 시험, 앱 1~2일. 검증 = tests/test_persist_panel.py 에 가짜 카드 묶음으로 실재·불일치·tier 별 등급 시험, AIDataHub 라우트 시험에 doc_type 필터 1건. 실주행 = 저장된 패널의 decision_text 로 persist 를 사본 DB 에서 다시 돌려 card 인용의 dangling·quote_mismatch 수를 센다.
- [걸음 3] 0단계 변경 묶음 + 셀 원장(읽기 전용 노출까지). 새 파일 app/bundles.py 의 build_bundles(store, target_key) 가 rr_diffs.diff_json 의 structural·parametric·semantic 전부를 rr_ir_nodes.asm_key 접두와 1홉 이웃(diff._neighborhood 와 같은 규칙)으로 분할한다. 묶음 줄은 render.event_text·param_text 의 정규 표기 그대로 쓴다. 스키마 v2 로 rr_bundles·rr_review_cells 를 만든다.
  - 이유: 변경 전량이 처음으로 잘리지 않고 남고, 줄마다 [c:…] 가 붙어 기존 인용 검증(canonical_text_for 의 c 분기)을 그대로 탄다. 재사용 = diff.changed_ckeys, rr_diff_events.subject_key·ckeys_json, rollup_delta 의 asm_key, brief.clip_lines·lint_items. 주의 = rr_diff_events 에는 의미 이벤트만 있다(구조·파라메트릭은 diff_json 안에만 산다). 위험 = 한 조립 단위가 너무 커서 창을 넘는 묶음, 조각이 너무 많아 셀 수가 폭증, 묶음 id 가 비결정이면 커버리지 키가 흔들린다, snap 타깃에는 diff 가 없어 묶을 재료가 다르다.
  - 비용: 앱 3~4일. 검증 = 속성 시험 셋(분할 — 모든 design_relevant cid 가 정확히 한 묶음에, 결정성 — 입력 순서를 섞어도 같은 bundle_id, 크기 상한). 실주행 = 실제 diff 한 건의 묶음 수·크기 분포를 재서 B 와 상한값을 정한다.
- [걸음 4] 1~3단계 — 에이전트 서버 새 모듈 card_review.py + 앱 셀 러너. 모듈은 thinking.py 와 같은 방식으로 deliberation 에서 _tools_by_name·_call·_llm_text·_parse_json·_first_dict·_persona_round·_restore_role·_sse·_free_gather_one·_tools_for_seat 를 가져다 쓰고 delib_llm 을 쓴다. 앱은 engine_client.PortalPanelEngine 의 전송부(자격·429 대기·벽시계·취소·진행 신호)를 그대로 쓰는 run_review 를 더하고, runner 에 review_loop 를 둔다. 3단계 보고서는 띵킹처럼 코드가 조립하고 LLM 은 요약 한 문단에만 쓴다. 포털 ChatRequest 에 새 필드를 선언한다.
  - 이유: 세 대안을 코드로 대조한 결론이다. 띵킹 모듈 자체는 못 쓴다 — recommend_agents top_k 로 소집하고(고정 명단 불가), 답변 상한 5명, 지식 예산 2,500자, 도구 없음, 챗 LLM(app.state.llm), 저장 없음. 엔진의 '혼자 쓰는 좌석' 모드는 최소 2석·포털 rounds≥2·1R 스키마·근거 예산·JS 정본과의 바이트 파리티에 전부 걸린다. 앱 직접 호출은 LLM 클라이언트·비밀·의존성이 없고 '러너는 직접 LLM 을 부르지 않는다' 는 계약을 깬다. 위험 = 자유 조회 도구 풀 조립이 _deliberation_stream 안에 인라인이라 함수로 뽑아야 한다(엔진 본체를 건드리는 유일한 자리), 포털에 필드를 선언하지 않으면 model_dump 에서 조용히 유실된다, 요청 본문이 6~9만 자가 된다, 공유 LLM 경합.
  - 비용: 에이전트 서버 4~5일 + 포털 반나절 + 앱 5~7일. 검증 = test_thinking.py 방식의 가짜 LLM 시험(전수성 검사·인용 검증·분할·기권과 오류 구분), 포털↔에이전트 필드 계약 시험, 앱은 httpx.MockTransport 로 셀 러너 시험. 실주행 = dev 에서 Tier A 대표 15명 × 묶음 1개(형식만 — dev 모델은 7B), 본 판정은 cae00 GLM 에서 같은 타깃의 기존 패널 결과와 견준다(새 클러스터 수·카드 판정 수·검증 통과율).
- [걸음 5] 5단계 쟁점 패널 + 누락 점검. planner.plan_dispute_panel 이 rr_registry 의 merged_json.domains ≥ 2 인 행과 같은 subject_key 에서 판정이 갈린 rr_card_verdicts 를 골라, 그 묶음을 지적한 전문가들 + adjacency 인접석 + 기준선 옹호석으로 패널을 짠다. 브리프는 그 묶음 전량과 해당 전문가들의 개별 판정을 싣는다. 누락 점검은 코드가 (묶음 × 메커니즘 38종) 표를 만들어 아무도 제기하지 않은 칸만 묻는다.
  - 이유: 지금 엔진·러너·등록부 병합을 그대로 쓴다(run_panel → engine → persist_panel_result → merge_panel). 바뀌는 것은 좌석 선정과 브리프뿐이다. 위험 = 엔진 근거 예산(128K 에서 약 17,967자)에 묶음 전량 + 개별 판정이 들어가야 한다 — brief.CAPS 와 다른 상한표가 필요하다, rr_seat_opinions 유일 제약(위 결함 참조), 메커니즘→영역 대응표가 자산에 없다(taxonomy 에는 default_tools 만 있다).
  - 비용: 앱 4~5일 + 자산 1종. 검증 = test_planner.py 에 쟁점 선정 결정성 시험, test_persist_panel.py 에 '이미 의견이 있는 좌석을 다시 앉혀도 저장된다' 시험. 실주행 = 걸음 4 결과에서 쟁점 묶음 1건으로 패널 1건.
- [걸음 6] 6단계 종합 + 완결 판정. registry.build_report·build_consolidated_report 에 영역별 요약 15건(LLM 15회 + 종합 1회)과 부록(전문가별 보고서, 묶음×전문가 표)을 더하고, close_level 에 셀 규칙을 넣는다.
  - 이유: 보고서 조립·RA 분할 저장(split_rich_text 1,900자)·export 는 이미 있다. 위험 = 부록이 359건이라 RA 한 보고서의 항목 상한과 분할 수가 커진다(미확인).
  - 비용: 앱 3일. 검증 = test_registry.py 에 '빈 칸이 있으면 레벨이 오르지 않는다'·'no_input 은 검토함으로 세지 않는다' 시험. 실주행 = 걸음 4·5 를 마친 타깃 한 건의 보고서 생성.
- [백엔드 계약 — 프런트 세션에 넘길 응답 필드] GET /targets/{key}/coverage 에 bundles[{bundle_id, seq, title, one_liner, n_changes, size_chars}] 와 cells{total, by_status{reviewed, na_irrelevant, no_input, unreviewed, running, failed}} 를 더한다. 새 GET /targets/{key}/cells?domain=&bundle_id= 는 행 {bundle_id, agent_key, domain, status, na_reason, na_basis{lexical, tag_hits, search_hits, self}, cards_total, n_violation, n_caution, n_ok, n_undetermined, n_off_card, quote_verified_rate, model, started_at, finished_at} 를 준다. 새 GET /targets/{key}/experts/{agent_key}/report 는 {agent_key, domain, pack_hash, cards_total, by_bundle[{bundle_id, verdicts[{record_id, card_id, title, tier, verdict, quote, quote_verified, change_refs, why}], off_card_finding_ids}], long_docs[{record_id, title}], summary_md, model} 를 준다. POST /targets/{key}/jobs 는 mode('panels'|'reviews')를 받고 cells_planned·llm_calls_estimate 를 돌려준다. MCP 에는 risk_get_bundles·risk_get_expert_report 를 더한다.
  - 이유: 기존 필드는 지우지 않는다(by_domain·by_status·strong·level 유지) — 프런트가 다른 세션 몫이라 추가만 한다. MCP 는 REST 와 같은 함수를 부르는 구조(mcp_server._scoped)를 따른다.
  - 비용: routes.py 에 payload 함수 4개, mcp_server.py 에 도구 2개. tests/test_mcp_tools.py·test_no_write_tools.py 가 도구 목록을 못 박고 있어 같이 고친다.
- 긴 문서(논문·특허·규격·물성 카드)는 agent_search 가 아니라 hybrid_search(agent_type=키, q=묶음 질의, top_k=N) 로 찾고, 이미 전문을 실은 카드 id 는 앱이 적중에서 뺀다.
  - 이유: agent_search 는 top_k 를 에이전트 설정에서 읽어(기본 10) 호출자가 못 바꾸고 doc_type 필터도 없다. 그대로 쓰면 이미 실은 카드가 상위를 다시 차지한다. material 전문가 1명은 물성 카드 2,688건(약 1억 자)이라 '전부' 가 불가능하므로 이 경로가 유일하다.
  - 비용: 앱 반나절. ADH 변경 없이 된다. 더 깔끔하게 하려면 ADH 검색 도구에 doc_types·exclude_doc_types 인자를 더한다(1일).
- 좌석 귀속에서 자동 주입 지식카드를 도구 성공으로 세지 않는다 — attribute_events 가 소스 꼬리 '지식카드' 를 따로 세어 knowledge_hits_n 으로 보내고 tool_calls_ok 에서는 뺀다.
  - 이유: 엔진은 지식카드를 받은 좌석마다 evidence(source='<키> · 지식카드')를 내는데, 앱은 ' · ' 앞이 좌석 키인 evidence 를 전부 도구 성공으로 센다. 도구를 한 번도 안 부른 좌석이 used_tool=true → done(강) 이 되어 C2 의 strong 비율(0.7)과 tool_use_rate 가 부풀 수 있다(코드 대조로 확인, 실주행 미확인).
  - 비용: 앱 2시간 + tests/test_runner.py 1건. 고치면 기존 타깃의 strong 비율이 내려갈 수 있다.
- 프롬프트 순서를 '역할 → 카드 전문 → 묶음' 으로 고정하고, 창이 허락하면 한 호출에 묶음 여러 개를 태운다.
  - 이유: 같은 전문가의 호출들이 같은 머리(카드 묶음)를 공유하므로 서버가 접두 캐시를 지원하면 반복 비용이 준다. 평균 전문가는 카드 뒤에 약 56,954자가 남아 묶음 2~3개를 한 번에 볼 수 있다(호출 수 감소).
  - 비용: 코드 비용 거의 없음. 효과는 GLM 엔드포인트의 접두 캐시 지원 여부에 달렸다(미확인). 묶음을 합치면 판정 품질이 떨어질 수 있어 실측으로 정한다.
- 전량 실행 전에 Tier A 대표 15명으로 A/B 를 먼저 한다 — 같은 타깃에서 지금 패널 3건 대 개별 검토 15명 × 묶음.
  - 이유: 카드 30장을 한 번에 판정시키는 품질(가운데 카드를 건너뛰는지)과 호출당 지연을 모른다. 15명이면 최악에도 호출 수가 15 + 15×B 로 작다.
  - 비용: 걸음 4 직후 cae00 에서 하루. 지표 = 검토한 카드 수/전체, 인용 검증 통과율, 새 클러스터 수, 호출당 초.

### 숫자
- 현행 전량 편성 = Tier A 15석(3패널) + B 99석(20패널) + C 245석(49패널) = 72패널. b_cut = Σ max(1, ceil(0.3·|d|)) = 114. 패널당 호출 est_low = S·R + S·(R−1)·2 + T + 3 = 49, est_high = S·R·2 + S·(R−1)·4 + 2T + 3 = 95 (S=6, R=3, T=4) → 72×49 = 3,528 ~ 72×95 = 6,840회.
- 기본 마감(C2)에 필요한 종결 좌석 = Σ (|d|<3 이면 전원, 아니면 max(3, ceil(0.3·|d|))) = 114명 = 359의 31.8%. ECAD 부재 시 ECAD 6개 영역은 rank 1 만 남아 필요 85명, deferred 104명(110−6), 비-deferred 로스터 255명.
- 일일 패널 상한 기본 24 → 현행 72패널은 3.0일. 개별 검토 359건을 패널 행으로 흉내 내면 359/24 = 15.0일.
- 좌석 지식카드 주입 3,500자 ÷ 전문가 카드 평균 57,072자 = 6.1%(p95 4.5%, 최대 3.8%). 한 줄 700자 상한이므로 좌석당 최대 5줄 → 전원 합 상한 5×359 = 1,795 스니펫 = 카드 10,774장의 16.7%(전부 카드이고 겹치지 않는다는 가정의 상한, 실제는 논문·특허와 경쟁 — 카드는 전문가당 묶인 기록 평균 138건 중 약 30건 = 22%).
- 엔진 좌석 근거 예산(128K 창) = (128,000 − int(48,000/1.05) − 56,000) × 1.05 × 0.93 = 26,286토큰 → 25,668자, 그중 근거 몫 70% = 17,967자. 카드 평균 57,072자는 3.18배, p95 77,775자는 4.33배, 최대 91,780자는 5.11배.
- 카드 묶음 토큰 = 최악 환산(1.05자/토큰) 평균 54,354 · p95 74,071 · 최대 87,409토큰. token_estimate 기준(657토큰/장) 평균 30×657 = 19,710 · p95 34×657 = 22,338 · 최대 35×657 = 22,995토큰. 전체 10,774×657 = 약 708만 토큰.
- 판정 턴(도구 없음) 잔여 = 128,000 − 16,000(출력·시스템) − 1,904(역할 2,000자) − 1,500(지시) − 카드. 평균 54,242토큰(56,954자) · p95 34,525토큰(36,251자) · 최대 21,187토큰(22,246자). 도구 스키마 40,000토큰을 같은 호출에 묶으면 평균 14,242 · p95 −5,475 · 최대 −18,813토큰(넘친다).
- 설계안 호출 수 = 1단계 359 + 2단계 359·B·r + 3단계 0(코드 조립) + 6단계 16(영역 15 + 종합 1) + 5단계 D×(49~95). 예 — B=8, r=0.35 면 2단계 1,005회, 5단계 제외 합 1,380회. B=8, r=1.0(관문 없이 전부)이면 2,872회, 합 3,247회. B=12, r=0.5 면 2,154회, 합 2,529회. 현행 3,528~6,840회와 같은 자릿수거나 적다. (B·r·D 는 가정이다.)
- 커버리지 셀 수 = 359×B. B=8 이면 2,872칸, B=12 면 4,308칸, B=20 이면 7,180칸.
- 카드 원문 조회 호출 수(현재 길) = list_records 359 + get_record 10,774 = 11,133회. REST 에 doc_type 인자를 더하면 359회(전문가당 1회, 카드 최대 35장 ≤ 쪽 상한 100).
- 카드 등급 태그 비율(코퍼스 23,378장) = heuristic 67.9% · fact 28.9% · expert-judgement 3.1%. card 인용이면 무조건 '문헌·규격' 인 지금 규칙은 약 71% 를 한 등급 올려 적는다.
- 변경 내용 칸 = E1 1,650 + E2 1,100 + E3 700 + E4 600 = 4,050자(brief.CAPS). summary_text 구획 예산 = 대상 220 · 비교가능성 200 · 구조 260 · 의미 700 · 치수 420 · 재료 100 · 결과 160 · 씨앗 60, 전체 상한 2,000자. panel_question 이 쓰는 앞 200자는 전부 '대상' 구획 안이고, 로스터 질의의 앞 500자는 대상 + 비교가능성 + 구조 머리다.
- ECAD 6개 영역 전문가 = 19+18+19+20+18+16 = 110명 = 30.6%. 0장 전문가 3명. 긴 문서 합 = 22,421 + 5,371 + 2,688 + 864 = 31,344건, 글자 합 약 978M + 544M + 102M + 52M = 약 16.8억 자(전량 주입 불가, 검색 필수).
- 벽시계 추정(가정 — 판정 호출 1회 5분) = 1,005회 × 5분 = 83.75시간을 동시성으로 나눈다. 직렬 3.5일, 동시 4 면 약 21시간, 동시 6 이면 약 14시간. 호출당 지연은 측정값이 없다.

### 코드 사실
- diff 타깃의 치수·결과 칸이 비는 원인 — _item_e3·_item_e4 는 diff_json 최상위에서 dims_delta·result_delta 를 찾는데, compute_diff 는 그것을 parametric 아래에 둔다(같은 앱의 narrative.SpecContext.dim 은 parametric 에서 읽는다). — `HWAXRisk/backend/app/brief.py:514`
- E2 이벤트 정렬 키가 -(magnitude) 로 부호가 살아 있다. clip_lines 가 뒤에서부터 버리므로 음수(감소) 변화가 먼저 잘린다. 또 rr_diff_events 에는 의미 이벤트만 펼쳐지고 구조·파라메트릭 항목은 diff_json 안에만 있다(diff.py:1743 _event_rows 주석). — `HWAXRisk/backend/app/brief.py:487`
- 패널 질문의 '요약 첫 줄' 은 summary_text 앞 200자이고, 그 자리는 render._summarize_diff 의 [대상] 구획(base 라벨·스냅샷 id·ir 해시, 예산 220자)이다. 좌석 지식카드 검색 질의가 이 문자열이라 변경 어휘가 없다. — `HWAXRisk/backend/app/runner.py:358`
- 로스터 순위 질의도 summary_text 앞 500자(QUERY_TEXT_MAX)이고 recommend_agents 는 상위 60명만 점수를 준다. 나머지는 relevance 0 으로 키 순서가 된다. — `HWAXRisk/backend/app/roster.py:20`
- card·rpt·inc 인용은 external_check 가 None 이면 ok=True·verified=False 로 통과한다. external_check 를 채우는 코드는 리포 어디에도 없다(grep 결과 선언 1곳·사용 2곳뿐). _panel_scope 가 만드는 SpecContext 에도 없다. — `HWAXRisk/backend/app/narrative.py:645`
- evidence_grade_from_cites 는 grade_ok 인 인용 중 card 또는 paper 가 하나라도 있으면 '문헌·규격' 을 준다. canonical_text_for 에 card 분기가 없어 canonical 이 None 이고, 그러면 인용문 대조를 건너뛰어 grade_ok 가 된다. 대조 자체는 정확 부분문자열이다(:719). — `HWAXRisk/backend/app/narrative.py:768`
- 좌석 의견의 knowledge_hits_n 은 None 고정이다('세는 원천이 아직 없다' 주석). 한편 attribute_events 는 evidence 소스의 ' · ' 앞이 좌석 키면 tool_calls_ok 를 올리는데, 엔진은 지식카드를 받은 좌석마다 source='<키> · 지식카드' evidence 를 낸다(deliberation.py:4131 부근). 자동 주입이 도구 성공으로 세진다. — `HWAXRisk/backend/app/runner.py:195`
- 커버리지 원장 PK 는 (target_key, agent_key), 좌석 의견은 UNIQUE(target_key, agent_key, cycle)다. 스키마 변경은 CREATE TABLE IF NOT EXISTS·ADD COLUMN·CREATE INDEX IF NOT EXISTS 만 허용한다(:561 주석). rr_findings.origin 은 llm|human 둘뿐이고 claim_uid 는 '<panel_id>#F1' 꼴이다. — `HWAXRisk/backend/app/risk_store.py:322`
- persist_panel_result 는 rr_seat_opinions 를 panel_id 로만 지우고 다시 넣는다. 같은 타깃·같은 cycle 에 그 전문가의 다른 패널 의견이 있으면 INSERT 가 유일 제약에 걸린다(지금은 편성기가 전문가를 타깃당 한 번만 앉혀서 드러나지 않는다). — `HWAXRisk/backend/app/narrative.py:1697`
- close_level 의 C1 은 Tier A 패널 done ≥ 3 을 요구하고, C2 는 영역별 종결 ≥ max(3, ceil(0.3·|d|)) 와 strong 비율 0.7, C3 는 전원 종결이다. 완결 판정이 패널 수에 묶여 있다. — `HWAXRisk/backend/app/registry.py:945`
- 등록부 지지 수는 support = 서로 다른 panel_id 수(없으면 llm 원자 수)다. panel_id 가 NULL 인 개별 검토 finding 이 패널 finding 과 한 클러스터에 섞이면 지지가 패널 수로만 세진다. — `HWAXRisk/backend/app/registry.py:206`
- 타깃당 직렬 — claim_next_job 은 그 타깃에 running 패널이 있으면 건너뛰고, 일일 패널 수가 risk_daily_panel_cap(기본 24) 이상이면 잡을 daily_cap 으로 멈춘다. 세마포어 risk_concurrency(기본 2)는 워커 수다. C1 이상에서 최근 3패널이 새 클러스터 0 이면 잡을 diminishing 으로 멈춘다(:1390). — `HWAXRisk/backend/app/runner.py:733`
- 리스크 앱에 LLM 클라이언트가 없다. 의존성은 mcp·fastapi·uvicorn·pydantic·jsonschema·pyyaml·httpx·cryptography 뿐이고, 비밀 5종에 LLM 키가 없으며, RiskRunner 독스트링이 '러너는 직접 LLM 을 부르지 않는다' 고 적는다. 엔진으로 가는 길은 포털 POST /agent/chat 하나다(engine_client.py:370, 메시지 머리 '/심의 '). — `HWAXRisk/backend/pyproject.toml:6`
- 앱의 SSE 수집은 좌석 발언을 SAY_MAX=2000자로 자르고 events 는 400건까지만 둔다. 결정문(delib decision 프레임)과 result.content 는 자르지 않는다. 실행마다 포털 대화를 하나 만든다(:358). — `HWAXRisk/backend/app/engine_client.py:44`
- AdhClient 는 X-API-Key 로 AIDataHub 에 직접 닿고(REST import, MCP call_tool 범용), call_tool 로 list_records·get_record 를 지금도 부를 수 있다. GET 용 메서드는 없다(_post_json 만 있다). — `HWAXRisk/backend/app/adh_client.py:158`
- 앱이 agent_search 에 required_tags·exclude_tags·retrieval_config 를, hybrid_search 에 tags·exclude_tags 를 실어 보내는데(adh_client.py:165-196, 호출처 brief.py:1077·1567), AIDataHub MCP 도구 시그니처는 agent_search(agent_type, q, mode)·hybrid_search(q, top_k, data_types, agent_type)뿐이다. 범위 태그 인자를 받는 자리가 도구에 없다. — `AIDataHub/api_server/src/api/mcp_runtime.py:435`
- 한 전문가의 카드 전부를 원문으로 한 번에 주는 도구는 없다. MCP list_records 는 agents·doc_type 필터와 limit≤100 을 받지만 to_summary(본문 제외, summary 200자)만 준다. 본문은 get_record(record_id)가 content 째로 준다. get_context_bundle 은 max_records 기본 10 에 sample_queries 관련도로 고르는 묶음이라 전수가 아니다. — `AIDataHub/api_server/src/api/mcp_runtime.py:892`
- REST GET /api/records 는 RecordOut(content 포함)을 limit≤100 으로 주고 agent 필터가 있지만 doc_type 쿼리 인자가 없다. 서비스 함수 query_records 는 doc_type 을 이미 받는다(record_query_svc.py:31,48). — `AIDataHub/api_server/src/api/routes/records.py:99`
- agent_search 는 top_k 를 에이전트 retrieval_config 에서 읽고(기본 10) 범위는 그 전문가에 묶인 모든 기록이다. doc_type 필터가 없어 지식카드가 논문·특허 섹션과 같은 top_k 를 다툰다. search_svc 에는 doc_type 참조가 없다. — `AIDataHub/api_server/src/api/mcp_runtime.py:468`
- 엔진의 좌석 지식 주입은 심의 시작 때 한 번, _agent_search_hits(tools, 좌석 키, question) 결과를 DELIB_KNOWLEDGE_BUDGET 3,500자까지 싣는다. 한 줄은 knowledge_line 이 700자에서 자른다(:2404). — `HWAXAgentServer/deliberation.py:4071`
- 엔진은 좌석이 2석 미만이면 no_personas 로 끝난다. risk-review 는 기준선 옹호석을 합성으로 얹으므로 전문가 1명 + 옹호석 = 2석은 통과하지만, 포털 DelibOpts.rounds 는 ge=2 이고(HWAXPortal/backend/app/agent/routes.py:89) stop_after_round=1 은 결정문 없이 체크포인트 글만 낸다(:4732-4743) — risk_spec 이 없어 finding 이 0 이 된다. — `HWAXAgentServer/deliberation.py:4047`
- 좌석 사전 근거 예산은 창에서 유도한다 — 직전 라운드 몫 _SEAT_CTX 48,000자와 _EVID_RESERVE(도구 스키마 40,000 + 16,000토큰)를 뗀 나머지에 0.93 을 곱하고 그 70% 가 근거 몫이다. 넘는 항목은 뒤에서 통째로 빠진다(:4232-4236). — `HWAXAgentServer/deliberation.py:206`
- 자유 조회 도구 풀 조립(허용 접두·리스크 읽기 도구·앱 범위·스키마 예산)은 _deliberation_stream 안에 인라인이다(약 :3736-3830). _free_gather_one·_tools_for_seat 는 모듈 함수라 그대로 가져다 쓸 수 있다. 조회 턴과 발언 턴을 가른 이유가 독스트링에 있다(:3001). — `HWAXAgentServer/deliberation.py:3802`
- _persona_round 는 파싱 실패·요구 키 결손·validator 지적 시 재호출하는 훅을 갖고, _llm_text 는 max_tokens 절단을 표식으로 남긴다(:1641-1655). 인용 실재 검증은 공백 정규화 후 포함으로 한다(_norm_ws :1898, _quote_validator :2022). — `HWAXAgentServer/deliberation.py:1658`
- 띵킹 모드는 recommend_agents(top_k=THINK_CANDIDATES 10)로 소집하고, 답변 상한 5명, 지식 예산 2,500자, 좌석 한도 600초, 동시 4, 도구 없음이다. LLM 은 app.state.llm(챗용)이고 심의용 delib_llm 이 아니다(:356). 결과는 SSE 로만 나가고 저장·잡 원장이 없다. deliberation 에서 가져오는 것은 헬퍼 11개뿐이다(:23-35). — `HWAXAgentServer/thinking.py:40`
- 에이전트 서버에는 전문가 카드 목록·카드 한 장을 읽는 결정적 경로가 이미 있다 — /catalog/agent/records(list_records 래핑, 쪽 상한 100)와 /catalog/record(get_record 래핑, 본문 60,000자 상한). 같은 도구 조합을 새 모듈이 쓸 수 있다. — `HWAXAgentServer/app.py:4143`
- 포털 ChatRequest 는 필드를 선언해야 에이전트 서버로 넘어간다(thinking 필드 주석 '여기 선언하지 않으면 조용히 유실된다'). delib_opts 는 DelibOpts 모델로 범위가 강제된다(evidence 120건, personas 20석, rounds 2~8). — `HWAXPortal/backend/app/agent/routes.py:211`
- 묶음의 재료가 IR 에 있다 — rr_ir_nodes 에 asm_key·material_norm·name_norm, rr_ir_edges 에 kind_family·ck_a·ck_b·subject_key, 의미 이벤트에 subject.ckeys·neighborhood.ckeys, rollup_delta 에 asm_key. 1홉 이웃 규칙은 iface·contact 계열에서 clearance 를 뺀 것이다(diff.py:472). — `HWAXRisk/backend/app/risk_store.py:127`
- 택소노미 자산의 mechanism 축은 38종이고 항목 필드는 code·mechanism·detail·label·description·default_detectability·default_tools 다. 영역(domain)과의 대응은 자산에 없다. 인접 영역표는 adjacency.v1.json 에 15개 영역 전부 있다. — `HWAXRisk/backend/app/assets/taxonomy.v1.json:`

### 확인하지 못한 것
- GLM 의 실제 토큰 환산 — 카드 묶음이 전문가당 19,710토큰(token_estimate 기준)인지 54,354토큰(엔진의 최악 환산)인지에 따라 카드 분할이 필요한 전문가 수가 달라진다. 운영 박스에서 표본 3~5명으로 재야 한다.
- 운영 LLM 의 설정과 용량 — 심의용 max_tokens 값(판정 JSON 이 잘리는지), 접두 캐시 지원 여부, 6만 토큰 프롬프트 1회의 지연, 동시 몇 건까지 받는지. 벽시계 추정은 전부 이 값에 달렸다.
- 실제 diff 에서 묶음이 몇 개 나오고 얼마나 큰지(B 와 크기 분포), 전문가당 관련 묶음 비율(r), 쟁점 패널 수(D). 호출 수 계산의 세 변수가 전부 가정이다.
- 카드 30~35장을 한 호출에서 판정시켰을 때의 품질(가운데 카드를 건너뛰거나 뭉개는지). 전수성은 코드로 강제할 수 있지만 판정의 질은 A/B 로만 알 수 있다.
- 앱이 AIDataHub MCP 도구에 싣는 미지원 인자(required_tags·exclude_tags·tags·retrieval_config)가 런타임에 조용히 무시되는지 거절되는지 확인하지 못했다(실행하지 않았다). 무시된다면 범위 태그 필터가 걸리지 않은 채 회수되고 있을 수 있다 — 이 설계와 별건이지만 긴 문서 검색을 같은 도구로 할 것이라 먼저 확인해야 한다.
- agent_search 의 snippet 이 카드 본문(content_text)의 그대로의 부분문자열인지 — 걸음 2 에서 기존 패널의 card 인용문을 대조할 때 불일치가 얼마나 날지를 정한다.
- 검색 적중에 doc_type 이 실려 오는지 확인하지 못했다(search_svc 에 doc_type 참조가 없다는 것만 확인). 그래서 카드 제외는 앱이 가진 카드 id 집합으로 하는 안을 냈다.
- 포털·nginx 의 요청 본문 한도와 포털 동시 실행 자리(max_concurrent_chats — 주석상 64)가 6~9만 자 요청 수백 건을 받는지, 개별 검토가 챗·심의와 그 자리를 나눠 써도 되는지.
- snap 타깃(스냅샷 한 건 전체)은 diff 가 없어 0단계 묶음을 무엇으로 만들지 정해지지 않았다(상태 신호·규칙 적중을 조립 단위로 묶는 안이 가능해 보이나 코드를 그 관점으로 읽지 않았다).
- ECAD 어댑터가 스텁인 동안 ECAD 6개 영역 110명에게 무엇을 보여 줄지 — 기구 변경만으로 회로 전문가가 판단할 수 있는 범위가 있는지는 도메인 판단이다. 설계안은 그 칸을 '입력 부재' 로 따로 적는 것까지만 정할 수 있다.
- material 전문가 1명(물성 카드 2,688건)과 지식카드 0장 전문가 3명의 처리 — 검색만으로 도는 검토를 '검토함' 으로 셀지.
- 묶음 × 메커니즘 누락 점검에 필요한 '메커니즘 → 담당 영역' 대응표가 자산에 없다. 누가 만들고 누가 승인하는지 정해야 한다.
- recommend_agents 의 top_k 상한과, 묶음별로 359명 전원의 desc_match 를 한 번에 받을 수 있는지 확인하지 못했다(로스터는 60 을 쓴다). 안 되면 1단계의 결정적 신호는 앱의 어휘 겹침과 hybrid_search 적중 둘로 간다.
- MCP L2 경로(HWAXPortal/infra/pipeline/hwax-risk-review.js)와 JS 정본 파리티에 새 단계가 주는 영향은 읽지 않았다. 5단계만 기존 경로를 쓰므로 영향이 작을 것으로 보나 추정이다.
- RA 보고서 한 건에 전문가별 부록 359건을 싣는 것이 RA 의 항목·분할 상한 안에 드는지 확인하지 못했다.


