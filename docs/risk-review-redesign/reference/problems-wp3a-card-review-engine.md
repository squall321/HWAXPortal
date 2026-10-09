# WP3a 설계서 반대 검토 — 문제 메모 (2026-10-09)

대상 — spec-wp3a-card-review-engine.md. 계약(04-contract.md)이 이미 조정한 어긋남은 다시 적지 않는다.
문제를 찾을 때마다 아래에 덧붙인다.

## P-01 [major] 스냅샷 타깃의 단위(snap_unit)를 받는 프롬프트가 없다 — 다섯 틀이 전부 '변경' 을 전제한다
- 근거. 설계서 전체에 'snap' 이 0건이다(grep). 3.5.1~3.5.5 의 [지시]는 전부 "변경 줄", "이 변경이", "변경 줄로 확인된다", "단위의 변경을 맞대어 보고" 다. 브리프 34행은 단위가 snap 타깃이면 (조립 단위 × 신호군)이라고 못박았고, 계약 C-8 은 kind 에 snap_unit 을 두며, WP2 661행은 "snap 타깃의 전 단위 — 현황 감사는 전 전문가 대상" 이라 적었다.
- 깨지는 모양. 현황 줄(간섭·계면·신호 사실)이 "변경 줄 N줄(전부다)" 머리 아래 실린다. 모델은 없는 전후 값을 읽으려 하거나 "변경이 없어 무관" 으로 답한다. (가)는 rel=no 가 줄줄이 나오고 (나)는 applies=no/na 로 표가 찬다. 인용 대조·행 집합 검사는 전부 통과하므로 틀린 채로 '검토함' 이 된다.
- 고침. 걸음 4(프롬프트)에 단위 종류별 문구 사전을 넣는다 — unit.kind 가 snap_unit 이면 "현황 줄"·"이 설계 현황"·"applies=yes 는 현황 줄로 확인된다" 로 바꾼 틀을 쓴다. FIXED[kind] 는 두 변형 중 긴 쪽으로 잰다. PROMPT_REV 에 두 변형을 다 넣는다. 걸음 4 시험에 snap_unit 단위로 조립한 프롬프트에 '변경' 낱말이 0건임을 단언한다. 5.3 의 심은 위반 픽스처에도 현황형 단위를 넣는다.

## P-02 [major] dev(16K 창)에서 (다)·(라)·(마)는 고정 블록만으로 창을 넘는다 — 'dev 실 LLM 소규모' 걸음이 422 로 막힌다
- 근거. 설계서 3.3 의 식으로 dev 값을 직접 셌다. P_hard=11,999 · ROLE_MAX=DIGEST_MAX=1,199 · HINT 600 · 틀 2,600(가정). (다)의 고정 블록 상한은 limits 예시가 상수로 준다 — longdoc_max 6,000 · known_max 1,200(3.3 응답 예) + 메커니즘 목록 38종(C-30 뒤 52종, 약 1,800자) + 영역 코드 약 300자. 합 = 2,600+1,199+1,199+600+6,000+1,200+1,800+300 = 14,898자 > P_hard 11,999. 단위 본문(B=3,008)을 더하면 17,906자다. 검색을 빼도 11,906자라 배경 카드 전문을 한 장도 못 싣는다. (마)는 peer_rows_max 6,000 이 상수라 2,600+1,199+1,199+600+6,000+3,008 = 14,606자 > 11,999.
- ROLE_MAX·DIGEST_MAX 만 창에 비례하게 줄이고(min(…, P_hard//10)) longdoc_max·known_max·peer_rows_max·메커니즘 목록은 줄이는 식이 없다. 3.3 의 박스별 표에도 dev 의 offcard·cross 칸이 없다.
- 깨지는 모양. 5.3-2 의 단언 "예산 초과 0건" 이 (다)(마)에서 거짓이 된다. C-27 의 켜는 순서(dev 가짜 엔진 → dev 실 LLM 소규모 → cae00)의 둘째 걸음을 세 종류가 못 지난다. 운영 박스로 가서야 처음 도는 종류가 셋이다.
- 고침. 걸음 1 에서 longdoc_max·known_max·peer_rows_max·findings_max 를 상수가 아니라 식으로 둔다(예 — longdoc_max = min(6,000, BODY[offcard]//4), peer_rows_max = min(6,000, BODY[cross]//3), known_max = min(1,200, P_hard//20)). 메커니즘 목록은 P_hard 가 작으면 코드만 싣는다. limits 응답에 kind 별 `fixed`·`body` 와 `runnable: false` + 사유를 싣고, 걸음 1 시험에 "16,384 창에서 다섯 종류 전부 BODY ≥ B + 1,500" 을 단언으로 넣는다. 안 되면 '이 박스에서는 이 종류를 못 돌린다' 를 limits.warnings 에 적고 5.3-2 의 범위에서 뺀다고 명시한다.

## P-03 [major] 팩 빌더가 '도구가 안 보인다·목록 호출이 실패했다' 를 정의하지 않았다 — 전 전문가가 '카드 0장' 으로 얼 수 있다
- 근거. deliberation.py:1389-1392 — `_call` 은 도구가 사전에 없으면 예외가 아니라 `None` 을 돌려준다. 실패는 문자열("(tool … error: …)"·✖ 문구)로 온다(:1402, app.py `_cap_tool`). `_tools_by_name` 은 연결이 없으면 `{}` 를 준다(:1298-1300). 설계서 3.4 는 get_agent_session 의 'agent not found' 와 get_record 의 실패만 규칙을 적었고, list_records 가 None·오류 문구·dict 아님·items 누락일 때의 규칙이 없다. 걸음 6 의 시험 목록에도 그 경우가 없다("0장 → 빈 팩, 모르는 키, 한 장 실패" 뿐).
- 깨지는 모양. 러너 자격이 서비스 PAT 이고 그 그룹에 plat:aidatahub 가 없으면(설계서 9절이 확인 못 했다고 적은 것) AIDataHub 도구가 시야에서 빠진다. list_records 가 None → 구현이 `(d or {}).get("items") or []` 로 읽으면 359명 전원이 cards=[] 정상 팩이 된다. WP3b 는 그것을 `empty` 로 얼리고(3.5.2 표) 훑기·대조를 건너뛴 채 전 셀을 search_only 로 닫는다. 실패가 정상 응답과 똑같이 생긴다.
- 고침. 3.4 걸음 3 앞에 규칙 넷을 넣는다 — ① `tools` 가 비었거나 `list_records`·`get_record`·`get_agent_session` 중 하나라도 없으면 503 `tools_unavailable`(빠진 이름을 싣는다). ② list_records 응답이 dict 가 아니거나 `items` 가 list 가 아니거나 `total` 이 int 가 아니면 502 `card_list_failed`. ③ 모은 id 수 ≠ total 이면 502. ④ get_record 응답의 `id` 가 청한 id 와 다르거나 `doc_type` 이 다르면 그 장을 실패로 센다. 걸음 6 시험에 "도구 사전에 list_records 가 없다 → 503", "list_records 가 '(tool list_records error: …)' 문자열 → 502", "None → 502" 를 넣는다. 가짜 도구는 실제 모양(문자열 JSON, content-item 리스트)으로 답하게 한다.

## P-04 [major] `_agent_search_hits` 로는 새 인자를 실을 수 없다 — A2 는 만들어도 읽는 곳이 없고, A2 없이는 긴 문서 검색이 거의 빈다
- 근거. deliberation.py:2407-2421 — `_agent_search_hits(tools, agent_type, q, *, mode, timeout_s)` 는 인자 dict 를 안에서 `{"agent_type", "q", "mode"}` 로 고정해 만든다. `exclude_doc_types`·`top_k` 를 넘길 자리가 없다. 설계서 3.5.3-1 은 "`_agent_search_hits(...)`. AIDataHub 가 새 인자를 받으면 exclude_doc_types·top_k=12 를 싣고" 라 적었고, 3.11 은 "deliberation.py 를 고치지 않는다(손잡이 하나만)" 고 적었다. 둘이 같이 설 수 없다.
- A2 없이 도는 폴백의 실효. top_k 는 전문가 설정(6~8, 기본 10 — mcp_runtime.py:469)이고 호출자가 못 바꾼다. 카드가 30장 묶인 전문가에게 변경 어휘로 물으면 상위 6~8건은 대개 그 전문가의 지식카드 절이다(카드가 그 영역 질문에 맞게 쓰인 글이라서 — 추정). 거기서 팩의 카드 id 를 빼면 남는 긴 문서 적중이 0~1건이다. 설계서 2.7-3 이 '속 빈 통로' 라고 스스로 부른 것이 폴백 길에서 그대로 남는다.
- 고침. 둘 중 하나를 계획에 적는다. (가) 걸음 8 에서 `card_review` 가 `_call(tools, "agent_search", {...})` 를 직접 부르는 자기 검색 함수를 둔다(시간 한도·폴백·강등 사유 규율을 `_agent_search_hits` 에서 옮겨 적고, 그 사실을 context-notes 에 남긴다). (나) 걸음 9 에 `_agent_search_hits(..., extra: dict | None = None)` 한 줄을 더하고 3.11 의 '손잡이 하나' 를 '둘' 로 고친다. 그리고 A2 를 '권고' 에서 '(다)의 긴 문서 검색이 뜻을 가지려면 필요' 로 올리거나, A2 가 없는 박스에서는 걸음 8 을 끄고 meta.search.note 에 '카드와 같은 top_k 를 다퉈 긴 문서가 밀렸다' 를 적게 한다. 걸음 8 시험에 "적중 6건이 전부 팩의 카드 → used=[] · note 가 비지 않는다" 를 넣는다.

## P-05 [major] `ctx_assumed` 를 만들 재료가 없다 — 구현에 따라 cae00 에서 계획이 영영 안 짜인다
- 근거. app.py:2033-2067 — `_model_context_tokens()` 는 int 만 돌려준다. 가정값인지 아닌지는 모듈 전용 dict `_ctx_cache` 안에만 있다("n" 이 있으면 굳힌 값, "retry_at" 이 있으면 방금 실패). 설계서 2.2 의 늦은 import 목록에 `_ctx_cache` 가 없다. 그리고 2053·2063행 — LLM 서버가 답은 했는데 `max_model_len`/`context_length` 가 없으면 기본값(LLM_CONTEXT_TOKENS, 128,000)을 **굳힌다**("그건 아래에서 굳힌다"). 운영 GLM 서버가 그 필드를 주는지는 아무도 확인하지 않았다(설계서 9절에도 없다).
- 깨지는 모양. 구현자가 손에 있는 것으로 `ctx_assumed = (ctx == 기본값)` 으로 짜면, 창이 정말 128,000 이거나 서버가 창을 안 알려 주는 박스(운영 후보)에서 ctx_assumed 가 영원히 true 다. WP3b 549·796행은 "ctx_assumed 면 계획을 짜지 않고 다음 틱에 다시 묻는다" 이므로 잡이 pack 단계에서 끝없이 돈다. 반대로 `"n" not in _ctx_cache` 로 짜면 '답은 왔는데 창이 없어 128,000 으로 굳은' 박스는 ctx_assumed=false 로 나가고, 실제 창이 더 작으면 계획 전체가 창 밖이다.
- 고침. 걸음 1 에 app.py 한 줄 변경을 넣는다 — `_model_context_tokens()` 옆에 `_model_context_state() -> {"tokens", "source": "server"|"fallback_no_field"|"fallback_unreachable"}` 를 더하고(기존 함수는 그대로), limits 는 `ctx_source` 를 싣는다. `ctx_assumed` 는 `fallback_unreachable` 일 때만 true 로 정의한다. `fallback_no_field` 는 false 로 두되 limits.warnings 에 "LLM 서버가 창 크기를 알려 주지 않는다 — LLM_CONTEXT_TOKENS 를 실제 값으로 적어라" 를 싣고, WP3b 는 그 경고를 잡 머리에 보인다. 3.11 의 'app.py 4줄' 을 고친다. cae00 사전 확인 항목에 "`curl $VLLM_BASE_URL/models` 에 max_model_len 이 있는가" 를 넣는다.

## P-06 [major] 틀 한 글자가 단위 상한(B)·limits_rev·prompt_rev 를 한꺼번에 흔든다 — 며칠짜리 실행 도중의 프롬프트 수정이 전 타깃의 열린 셀을 지운다
- 근거. 설계서 3.3 — FIXED[kind] 는 "틀의 길이를 import 때 실제 문자열로 잰" 값이고 B = int((P − FIXED) × 0.47) 다. 3.8 — prompt_rev 는 "시스템 글·지시 틀 **전부**의 sha256", limits_rev 는 "(창, OUT, 몫, K, prompt_rev)의 해시" 다. WP3b 926행 — 셀을 집을 때 input_hash(= unit_hash|pack_hash|prompt_rev|limits_rev)가 저장값과 다르면 "그 셀의 판정 행을 지우고 처음부터 돈다". WP3b 547행 — B 를 넘는 단위의 셀은 `failed('unit_oversize')` 다. WP2 890행 — 단위는 unit_body_max − 400 에 맞춰 채운다.
- 깨지는 모양. ① (마) cross 틀의 오타 하나를 고쳐 배포하면 prompt_rev 가 바뀌고, 그와 무관한 (나) verdict 의 열린 셀까지 전부 input_hash 가 어긋나 판정 행이 지워진다(돌고 있는 모든 타깃). ② 틀이 20자 길어지면 B 가 9자 줄어 상한에 붙여 만든 단위가 `unit_oversize` 로 떨어진다(운영 창에서는 서버가 soft_over 로 받아 줄 수 있는데도 앱 규칙이 먼저 막는다). ③ K 파일럿 뒤 CARD_REVIEW_K·몫을 바꾸거나 DELIB_MAX_TOKENS 를 고쳐도 같은 일이 난다. 배포는 셀을 기다리지 않는다는 C-25 와 합치면, 평범한 수정 배포 한 번이 진행분을 무른다.
- 고침. 걸음 1·4 를 이렇게 바꾼다. ① FIXED 를 실측이 아니라 **선언한 여유값**으로 둔다 — `TEMPLATE_ALLOW = {verdict: 3,200, sweep: 2,400, …}` 상수, 시험이 `len(실제 틀) ≤ 여유값` 을 단언한다(틀이 여유 안에서 바뀌면 B 가 그대로다). ② prompt_rev 를 종류별로 낸다 — `prompt_rev: {sweep, verdict, offcard, noinput, cross}`, 결과 meta 에는 그 호출 종류의 것만 싣는다. ③ limits_rev 에서 prompt_rev 를 뺀다(창·OUT·몫·K·여유값만). ④ 뜻을 안 바꾸는 수정(오타)과 뜻을 바꾸는 수정을 가르도록 틀마다 손으로 올리는 판 번호(`cr-p1`)를 정본으로 하고 sha 는 '판 번호를 안 올리고 글을 바꿨다' 를 잡는 시험에만 쓴다. WP3b 의 input_hash 가 무엇을 보는지는 이 정의를 따라 다시 적는다.

## P-07 [major] 계약이 빠뜨린 것 — 스트림 봉투·오류 코드 어휘·usage 모양·LLM 한도 손잡이가 WP3a 와 WP5a 에서 서로 다르다
- 근거. 04-contract 는 관문(C-24)·/health(C-25)·infra 표지(C-26)만 맞췄다. 아래 넷은 계약에 없고 두 설계서가 다르게 적었다.
  ① 첫 프레임. WP5a 3.4.4-1 은 "첫 프레임은 `event: review` `{"kind":"hello","rev":"cr-1"}`. 앱은 첫 프레임이 이것이 아니면 `review_unsupported` 로 본다" 다. WP3a 3.7 의 프레임 목록은 `status · ping · result · error · done` 이고 hello 가 없다. 이대로면 새 에이전트 서버의 모든 호출이 review_unsupported → 실행이 `agent_outdated` 로 보류된다.
  ② 오류 코드. WP3a 는 `truncated_empty · no_rows · llm_error · busy`, WP5a 3.3.4('settle 의 정본')는 `output_truncated · review_parse_failed · review_incomplete · review_busy` 다. WP3b 892행은 WP3a 쪽 이름을 쓴다. 분류표에 없는 코드가 어느 부류로 떨어지는지는 어디에도 없다.
  ③ llm_timeout 의 부류. WP3a 는 infra:true(차감 없음), WP5a 는 capacity(차감 있음, knob='CARD_REVIEW_TIMEOUT_S')다. WP3a 는 전용 LLM 인스턴스를 만들지 않고 app.state.delib_llm 을 쓴다고 적었으므로(3.7) CARD_REVIEW_TIMEOUT_S 라는 손잡이는 존재하지 않는다. WP5a 의 /health.card_review{timeout_s, tries, request_worst_s} 도 재료가 delib_llm 에서 와야 한다.
  ④ usage. WP3a 결과 예시는 `attempts: 2` 인데 `usage{prompt_tokens, completion_tokens}` 가 하나다(마지막 시도인지 합인지 안 적었다). C-21 의 셀 열 `llm_calls · tokens_in · tokens_out` 과 WP5a 3.4.4-5 의 `usage{llm_calls, reasks, tokens_in, tokens_out, elapsed_ms, truncated, finish_reason, model}` 는 시도 합계를 요구한다. 마지막 시도만 실으면 토큰 집계가 최대 3배 작게 잡힌다.
- 고침. 계약에 한 조를 더하고 WP3a 3.7·3.8·걸음 5·7 을 그에 맞춘다 — (a) 첫 프레임 hello(rev 포함)를 낸다. (b) 오류 코드 표를 한 벌로 정한다(모듈이 내는 쪽이 정본 — `truncated_empty`·`no_rows`·`llm_error`·`context_overflow`·`llm_timeout`·`llm_unreachable`·`review_busy`·`over_budget`·`bad_request`), WP5a 분류표를 그 이름으로 다시 적고 '모르는 코드는 infra 표지를 따른다' 를 명시한다. (c) llm_timeout 은 한 부류로 정한다(권고 — 첫 시도의 시간 초과는 infra, 같은 셀에서 두 번째면 내용 탓). (d) usage 는 `{llm_calls, tokens_in, tokens_out}` 합계 + `per_attempt[]` 로 싣고, 모르면 null 이다. (e) 손잡이 이름은 실제로 걸리는 `DELIB_TIMEOUT_S`·`DELIB_LLM_MAX_RETRIES` 로 적는다. 걸음 7 시험에 프레임 순서 `review(hello) → status… → result|error → done` 을 단언한다.

## P-08 [major] 보충 호출에서 LLM 이 실패하면 첫 시도에서 받은 행까지 버린다
- 근거. 설계서 3.6 의 흐름은 "시도 소진 → 가진 것으로 끝" 을 파싱·검사 문제에만 적용한다. 3.7 상태기계는 `status{attempt n}` 어느 번에서든 "LLM 시간 초과·연결 실패 → error{llm_timeout|llm_unreachable}" 다. 서버는 상태가 없으므로(원칙 1) error 로 끝나면 1차 시도의 행은 어디에도 남지 않는다.
- 깨지는 모양. 8장 가운데 7장이 온전히 왔고 1장의 인용이 어긋나 보충을 물었는데 그 보충이 1,800초 × 2 를 넘겼다(공유 LLM 이 20석 패널에 밀린 흔한 경우). 요청 전체가 llm_timeout 이 되고 앱은 같은 33,600자 프롬프트를 처음부터 다시 낸다. 한 장 때문에 7장을 다시 사고, 그 재시도도 같은 길을 밟을 수 있다.
- 고침. 3.7 상태기계에 한 줄을 더한다 — "n ≥ 2 에서 LLM 이 실패하면 error 가 아니라 result 로 끝낸다. rows 는 그때까지 합친 것, 빠진 것은 missing, `quality.repair_error = {code, attempt}` 를 싣는다." 걸음 5 시험에 "첫 답 8행 중 1행 인용 불일치 → 둘째 호출이 TimeoutError → result 가 8행(1행은 checks.quote=not_found), repair_error.code=llm_timeout" 을 넣는다. 보충이 판정을 바꿨는지도 남긴다 — merge_rows 가 행마다 `from_attempt` 와, 같은 별칭의 앞 시도 판정이 달랐으면 `flipped_from` 을 싣는다(인용만 고치라고 했는데 FAIL 이 OK 로 바뀌는 것을 앱이 볼 수 있게).

## P-09 [minor] 5.3-3 의 K 파일럿(K=15·30)은 이 설계의 상한 식으로는 만들 수 없다
- 근거. 3.3 — K = min(CARD_REVIEW_K, K_out), K_out = int(OUTCAP × 0.63 // 520). max_tokens 8,192 면 K_out=9, 미설정이어도 19 다. 묶음은 글자로도 닫힌다(CARD_V 13,674자 — 평균 1,600자 카드 8장). K=15 는 CARD_V 약 24,000자(몫 0.33 이상), K=30 은 약 48,000자(몫 0.51 이상)와 OUTCAP 24,800토큰 이상이 있어야 한다. OUTCAP 은 심의와 함께 쓰는 delib_llm 의 max_tokens(DELIB_MAX_TOKENS)이고 요청 단위로 못 바꾼다(3.7 '전용 인스턴스를 만들지 않는다').
- 깨지는 모양. 파일럿을 하려면 cae00 의 DELIB_MAX_TOKENS 와 몫 손잡이를 바꾸고 에이전트 서버를 재기동해야 한다. 그 값은 일반 심의에도 걸리고, P-06 대로 limits_rev 를 바꿔 돌던 실행을 무른다.
- 고침. 걸음 5 에 파일럿 전용 덮어쓰기를 넣는다 — 요청 `extra.pilot{k, card_budget, max_tokens}` 는 env `CARD_REVIEW_PILOT=1` 일 때만 받고(`app.state.mk_delib_llm` 처럼 max_tokens 만 바꾼 LLM 을 그 요청에 쓴다), 결과 meta 에 `pilot: true` 를 싣는다. 아니면 5.3-3 의 K 목록을 1·4·8 로 줄이고 "8 초과는 재지 않는다" 고 적는다.

## P-10 [minor] 걸음 1 의 검증이 걸음 4 의 산출물에 기댄다(선행 조건이 안 맞는다)
- 근거. 4절 — 걸음 1(선행 없음)의 검증이 "3.3절 표의 세 박스 값 단언" 과 "모든 (묶음, B 크기 단위)가 P_hard 안" 이다. 표의 값은 FIXED 에 달렸고 FIXED 는 틀의 실제 길이다(틀은 걸음 4 에서 쓴다). 5.1 의 속성 ④ "build_prompt 에서 OverBudget 이 나지 않는다" 는 걸음 4 의 함수다. 그리고 `limits(llm=None)` 은 '순수' 라 적었지만 안에서 `app._model_context_tokens()` 를 부른다(app.py:2033 — 동기 httpx.get, 5초). 창을 넣어 줄 인자가 없어 시험이 실제 LLM 서버 유무에 따라 16,384 또는 128,000 을 받는다.
- 고침. 시그니처를 `limits(ctx_tokens: int, max_tokens: int, fixed: Mapping[str, int] = TEMPLATE_ALLOW) -> dict` 로 바꾸고(창을 묻는 일은 라우트가 한다), 걸음 1 은 P-06 의 여유값 상수로 표를 단언한다. 속성 ④ 는 걸음 4 로 옮긴다. `GET /limits` 라우트는 창 조회를 `asyncio.to_thread` 로 돌린다(LLM 이 죽은 동안 5초씩 이벤트 루프가 서서 다른 호출의 ping 이 밀린다).

## P-11 [minor] 5.3-1 의 픽스처 '카드 id' 는 record_id 면 박스를 못 건넌다
- 근거. ExpertAgents `src/expertcore/export/aidatahub_records.py:140-143` — "id 는 넣지 않는다 — 서버가 auto_seq 로 채번". AIDataHub `services/seq.py:31-56` — MAX(seq)+1. 같은 카드가 dev 와 cae00 에서 다른 record_id 를 갖는다. 박스 사이에 같은 것은 `content.card.card_id`(MIS-R-001)뿐이다. 설계서 5.3-1 은 "픽스처 파일에는 카드 id 와 기대값만 둔다", 5.3-3 은 그 60쌍을 cae00 에서 돌린다고 적었다.
- 고침. 5.3-1 에 "픽스처의 키는 (agent_key, card_id)" 로 못박고, 실행 스크립트가 그 박스의 팩에서 card_id → 별칭·record_id 를 푼다(못 풀면 그 쌍을 '없음' 으로 센다). 같은 까닭으로 결과 행(3.5.2 출력 예)에 `card_id` 를 record_id 옆에 싣는다 — 반출한 판정을 다른 박스에서 읽을 때 record_id 는 다른 카드를 가리킨다.

## P-12 [major] A1(`get_agent_cards`)을 MCP 도구로 내면 챗과 심의 좌석이 그 도구를 집는다 — 9만~25만 자 응답이 창을 넘긴다
- 근거. deliberation.py:2604-2626 — 좌석 자유 조회의 허용 목록 `_FREE_ALLOW` 는 접두사 `get_` 를 통째로 열고, 닫는 것은 `_FREE_DENY`(get_agent_session·catalog_run·catalog_reload) 셋뿐이다. 새 도구 이름 `get_agent_cards` 는 그대로 통과한다. 챗은 게이트웨이 도구를 전부 바인딩한다(운영 cae00 은 TOOL_MAX=0 — app.py:1741-1743 주석). 챗 도구 결과 절단은 TOOL_RESULT_MAX 200,000자다(app.py:605) — 한국어로 약 19만 토큰이라 128K 창보다 크다. 설계서 3.4 는 이 도구가 한 번에 본문 포함 100장(limit 1~100)을 준다고 적었고, 한 전문가의 카드 전부가 최대 91,780자다(03-cards).
- 깨지는 모양. "실링 전문가가 아는 것 다 보여 줘" 같은 챗 한 번에 모델이 이 도구를 부르면 9만 자가 도구 결과로 들어가 그 턴이 400 으로 죽거나(16K dev 는 확실히) 창의 대부분을 먹는다. 심의 좌석이 자유 조회에서 부르면 좌석 도구 예산(40,000토큰)을 한 번에 쓴다. A1 은 '권고 — 없어도 돈다' 인데 부작용은 챗·심의 쪽에서 난다.
- 고침. 권고 — A1 을 이번 범위에서 뺀다(cuts 참조. 잃는 것은 팩 빌드 호출 수 11,133 → 359 와 목록·본문 사이의 틈 제거). 넣는다면 같은 걸음에 셋을 묶는다 — ① `_FREE_DENY` 에 `get_agent_cards` 를 넣는다(deliberation.py — 3.11 의 '엔진을 건드리는 곳은 하나' 가 바뀐다고 적는다). ② 챗 바인딩에서 뺀다(게이트웨이 tool_areas·숨김 목록 중 어디서 막을지 정하고 시험한다). ③ 기본 limit 을 5 로 낮추고 본문 포함은 `include_content=true` 를 줄 때만. A2 의 `top_k` 도 상한(예 30)을 둔다 — 챗 모델이 top_k=200 을 넣을 수 있다.

## P-13 [minor] LLM 이 4xx 로 거절한 호출이 infra(차감 없음·자동 재시도)로 분류된다 — 창 초과 문구가 다르면 '반으로 나눠 다시' 가 영영 안 걸린다
- 근거. 3.7 상태기계 — "400 창 초과 → context_overflow", "그 밖의 LLM 오류 → llm_error, infra:true, retryable:true". 엔진에는 창 초과를 가르는 코드가 없다(app.py·deliberation.py 에서 'maximum context' 는 주석 4곳뿐 — grep). 판별 문구는 새로 써야 하고 vLLM 문구("maximum context length")에 맞출 수밖에 없다. 운영 GLM 서버의 문구는 확인되지 않았다.
- 깨지는 모양. GLM 이 다른 문구로 400 을 주면 llm_error(infra)다. WP3b 는 차감 없이 백오프로 여섯 번 다시 내고 infra_exhausted 로 끝낸다. 묶음을 반으로 가르는 복구(WP3b 898행)는 context_overflow 에만 걸려 있어 돌지 않는다. 내용 필터·잘못된 요청 같은 결정적 4xx 도 같은 길이라 차단기의 '인프라 연속 5회' 를 채운다.
- 고침. 3.7 표를 고친다 — HTTP 400·413·422 는 문구와 무관하게 `infra:false` 다(`llm_rejected`, 원문 200자를 싣는다). 그 가운데 추정 토큰(est_tokens + OUT)이 창의 85% 를 넘으면 `context_overflow` 로 올린다(문구에 기대지 않는다). 401·403·404 는 `llm_misconfigured`(infra:true, retryable:false — 잡을 멈출 일이다). 429·5xx·연결·시간 초과만 infra 재시도다. 걸음 5 시험에 상태 코드별 한 건씩.

## P-14 [minor] 포털 중계가 챗과 같은 연결 풀(64)을 쓴다 — 전용 상한 48 은 풀보다 크다
- 근거. HWAXPortal backend/app/main.py:113-117 — `app.state.agent_client = httpx.AsyncClient(limits=httpx.Limits(max_connections=settings.max_concurrent_chats, …))`, max_concurrent_chats=64(config.py:289), pool 대기는 agent_request_timeout 30초. 설계서 P1 은 `card_review_max_streams` 48 을 더한다고만 적고 클라이언트는 말하지 않았다.
- 깨지는 모양. 중계가 공유 클라이언트를 쓰면 챗 64 + 카드 대조 48 이 연결 64개를 다툰다. 풀이 차면 챗이 30초 뒤 PoolTimeout 으로 죽는다. 계약 C-24 로 줄이 없어져 실제 동시 스트림은 앱 워커 수(4~6)라 드물지만, 상한 48 이 그것을 허용한다.
- 고침. P1 에 "카드 대조 중계는 전용 `httpx.AsyncClient`(max_connections = card_review_max_streams + 4)를 쓴다" 를 넣고 상한 기본값을 12 로 낮춘다. 시험 — 챗 세마포어를 다 채운 상태에서 카드 대조 요청이 연결을 얻는다.

## P-15 [minor] 단위 크기 식이 두 리포에 복사된다 — 틀이 바뀌면 조용히 어긋난다
- 근거. 설계서 3.5.0 — unit_size 식(줄당 +11, 머리 +160)은 "실제 렌더 길이의 상계(시험으로 못박는다)". WP2 889행 — "크기를 재는 식은 WP3a 의 것을 그대로 쓴다" 며 같은 식을 HWAXRisk 에 적는다. 두 리포는 서로 import 하지 못한다. /plan 은 앱이 계산한 body_chars 를 받아 쓸 뿐 단위를 직접 재지 않는다(3.13 plan 시그니처).
- 고침. `GET /card-review/limits` 에 `unit_size{per_line: 11, base: 160, rev}` 를 싣고 앱은 그 수로 센다(상수를 복사하지 않는다). 걸음 4 의 "unit_size() ≥ 실제 렌더 길이" 시험이 그 수를 지킨다. C-11 의 인용 대조 파리티 벡터 파일도 만드는 걸음이 4절에 없다 — 걸음 3 의 산출물에 `tests/fixtures/card_review/quote_vectors.json`(입력 쌍과 기대 판정)을 더하고 "HWAXRisk 가 같은 파일로 시험한다" 를 적는다.

## P-16 [minor] 품질 한도 선택식에 절벽이 있다 — 창이 43K~100K 인 박스는 더 작은 창보다 예산이 작다
- 근거. 3.3 식 `P = P_soft if P_soft − FIXED ≥ 3,500 else P_hard` 를 그대로 셌다(틀 2,600 가정). 창 42,000 → B 10,790 · CARD_V 12,169. 창 43,500 → B 1,700 · CARD_V 1,918. 창 64,000 → B 4,230 · CARD_V 4,770. 운영 창 128,000 은 기본값 가정일 수 있다(P-05).
- 고침. `P[kind] = min(P_hard, max(P_soft[kind], FIXED[kind] + BODY_MIN[kind]))` 로 바꾼다(BODY_MIN 은 verdict 16,000 · sweep 20,000 정도). 걸음 1 시험에 "창이 커지면 B 가 줄지 않는다(단조)" 속성을 넣는다. 그리고 "단위를 싣는 모든 종류에서 BODY[kind] ≥ unit_body_max" 를 불변식으로 단언한다(지금은 32K 창에서 offcard BODY 7,099 < B 7,707 이다).

## P-17 [minor] 자잘한 어긋남 묶음
- (a) DELIB_HEARTBEAT_S=0(문서에 적힌 '끔' 설정, app.py:542·574)에서 3.7 의 감싸개 `asyncio.wait(…, timeout=DELIB_HEARTBEAT_S)` 는 곧바로 만료돼 ping 을 쉬지 않고 낸다. 엔진처럼 `> 0` 일 때만 timeout 을 주고 0 이면 그냥 기다린다. 걸음 5 시험에 0 인 경우를 넣는다.
- (b) 팩 빌드 동시 2건 세마포어를 어디 두는지 안 적었다. 관문과 같은 까닭(deliberation.py:4084-4085)으로 모듈 전역에 두면 시험(TestClient 마다 루프가 다르다)에서 죽는다. app.state 에 둔다.
- (c) parse_rows 가 줄 단위만 본다. 객체를 여러 줄로 펼쳐 내는 모델(7B 에서 흔하다)은 전 줄이 bad_lines 가 되고 temperature 0 이라 보충도 같은 꼴이다. 줄 단위로 못 읽은 것이 있으면 `_parse_json_multi` 식의 raw_decode 훑기를 한 번 더 한다. `<think>…</think>` 구간은 먼저 떼어 낸다(추론 블록 안의 초안 줄이 행으로 읽힌다 — GLM 이 본문에 섞어 내는지는 미확인).
- (d) 긴 문서 적중에 section_id 가 없는 것(기록 단위 FTS 적중 — search_svc `record_rows`)은 `get_record_sections(sections=[None])` 이 빈 목록이다. 그리고 그 도구는 목록을 돌려줘 원소별 content 로 온다(`_parse_json` 이 아니라 `_parse_json_multi`). 3.5.3-3 에 두 경우를 적는다.
- (e) (나)의 변경 참조 검사가 근거 꾸러미 줄만 댄 판정을 통과시킨다(lines 와 evidence 가 한 L 번호 공간이다). applies=yes 인데 `l` 이 전부 evidence 범위면 `checks.refs="evidence_only"` 로 표지한다(C-15 는 '변경 참조' 를 요구한다).
- (f) 수치 대조의 원천이 '카드 본문 + 인용한 줄' 뿐이라 머리 줄의 규격 번호(ISO 3601 → 3601), 단위 요약의 수치, 모델이 셈한 차이(1.2 → 0.9 에서 0.3)가 전부 nums_missing 이 된다. 원천에 머리 줄·단위 요약·notes 를 더하고, 표지 이름을 '원문에 없는 수치(계산값일 수 있다)' 로 읽히게 적는다.
- (g) plan() 의 훑기 묶음은 글자 수(CARD_S)로만 닫는데 run 은 '카드 40장' 에서 422 다. 작은 카드가 많은 전문가는 자기 계획이 거절된다(지금 최대 35장이라 잠복). plan 에 같은 40장 상한을 건다.
- (h) 카드 종류에 `open-observation`(ExpertAgents models/common.py:41-50 의 7번째 종류 — 인과 미검증 관측)이 있다. 설계서는 6종만 알아 '모르는 종류 → 점검형' 으로 보내는데, [지시]에 그 종류의 judgement 뜻이 없다. 종류 표에 넣고 배경으로 둘지 정한다.
- (i) 판정 행에 인용이 걸린 절 번호가 없다. C-15 의 `card:<record_id>#<section_id>` 를 앱이 만들려면 인용을 다시 찾아야 한다. 서버가 `checks.quote_sid`(절 경계를 넘으면 "")를 싣는다.
- (j) 3.12 의 evidence 항목 key 가 "K03" 인데 K 별칭은 전문가 팩 안에서만 유일하다. 쟁점 패널에 두 전문가의 카드가 실리면 같은 key 가 둘이다. key 는 `<card_id>` 로 한다.
- (k) (라) noinput 은 cards 가 예산을 넘을 때의 규칙이 없다((다)는 '제목으로 내리고 bg_dropped'). 같은 규칙을 적는다.
- (l) 5.2 의 취소 시험(TestClient 로 스트림을 닫는다)은 uvicorn 의 http.disconnect 길을 지나지 않는다. 제너레이터 `aclose()` 직접 시험 하나와, 임시 포트 uvicorn + httpx 로 실제 끊김을 보는 시험 하나로 나눈다(떠 있는 9009 를 쓰지 않는다 — 빈 포트를 잡는다).

## P-18 [major] 카드 밖 리스크가 호출당 F건(운영 6, dev 1)에서 끊기고 더 있는지 묻는 길이 없다
- 근거. 3.5.3 — [지시] "리스크·개선마다 한 줄(최대 {F}줄, 중요한 것부터)", F = min(8, (OUTCAP × 0.63 − 1,400)//600) — max_tokens 8,192 면 6, dev(OUT 4,096)면 1 이다. 검사 ⑦ "F 를 넘는 f 줄은 버리고 dropped_over_cap 에 센다". (다)는 (전문가 × 단위)에 한 번만 부른다(7.3 '카드 밖 = 관련 셀 수').
- 깨지는 모양. 변경 줄이 수십 개인 단위에서 한 전문가가 낼 수 있는 카드 밖 리스크·개선의 천장이 6건이다. 모델은 지시대로 6건에서 멈추므로 dropped_over_cap 도 0 이고, 더 있었는지는 아무도 모른다. 사용자의 첫째 요구('고려할 수 있는 리스크를 최대한')와 정면으로 어긋나는 자리인데 표지가 없다.
- 고침. 3.5.3 에 끝줄을 하나 더 받는다 — `{"t":"more","more":"yes|no"}`(필수). f 줄 수가 F 이거나 more=yes 면 `quality.maybe_more = true` 로 올리고, 앱이 `extra.known` 에 이미 받은 f 의 제목을 실어 같은 호출을 한 번 더 낸다(상한 3회, 호출 수 식 7.3 에 반영). 걸음 4·5 시험에 "f 가 F 줄 → maybe_more" 를 넣는다. dev 는 F=1 이라 이 길이 매번 걸리므로 dev 에서는 형식만 본다고 5.3-2 에 적는다.

## P-02 덧붙임
- 32,768 창에서도 offcard BODY 7,099 < B 7,707 이다(직접 셈). 단위 상한 B 는 verdict 에서만 유도하는데 같은 단위가 (다)(라)(마)에도 통째로 실린다. `unit_body_max = min_kind(그 종류가 단위에 줄 수 있는 몫)` 으로 정의를 바꿔야 한다.

---

## 빼거나 미룰 것(cuts)
1. A1 `get_agent_cards` MCP 도구 + REST `doc_type` 인자 — C-10 이 REST 길을 안 쓴다고 정했으므로 REST 쪽은 읽는 곳이 없다. MCP 도구는 P-12 의 부작용이 있다. 잃는 것 — 팩 빌드 호출 11,133 → 359, 목록과 본문 사이의 틈 제거(지금 전문가당 최대 35장이라 한 쪽에 다 든다).
2. A2 + 걸음 8(긴 문서 검색) — P-04 대로 지금 헬퍼로는 인자를 못 싣고, 없으면 거의 빈다. 첫 판은 (다)를 검색 없이 돌리고 뒤로 미룬다. 잃는 것 — 논문·특허·표준 절이 (다)에 안 실린다. 카드 0장 3명과 material 전문가는 역할 글만으로 답한다(basis 를 'role_only' 로 따로 적는다).
3. (마) cross — 목표(전 전문가의 카드 대조와 상세 보고서)에는 없어도 된다. 잃는 것 — 영역쌍 2차 영향, WP4 쟁점 후보의 한 원천(conflict). 미루면 rr_cross_cells 가 빈 채로 간다.
4. 전수 훑기의 k0 줄과 검사 ④ — 안 걸린 카드는 코드가 여집합으로 낸다. 모델이 30장 번호를 빠짐없이 나열하지 못하면 64,000토큰 프롬프트를 두 번 더 넣는다. 잃는 것 — '카드를 다 봤다' 는 자기 신고(읽었다는 증거는 원래 아니다).
5. applies=no 행의 인용 불일치로 보충 호출을 일으키는 것 — 표지만 남기고 보충은 빠진 행·열거 밖·yes/unknown 행의 인용에만 건다. 잃는 것 — '해당 없음' 행의 인용이 틀린 채 남는다(표본 solo 가 본다).
6. rev 이중 판정 전량(8절 결정 3 의 권고) — 첫 실주행은 전문가 15명 시범에만 전량, 그 밖은 표본. 잃는 것 — 표본 밖 묶음의 순서 편향을 못 잰다. 사용자 결정 사항이다.
7. 관문의 대기 줄(CARD_REVIEW_MAX_WAITING·WAIT_MAX_S)과 포털 전용 상한 48 — C-24 로 이미 줄이 없다. 상한은 12 로.
8. K 파일럿의 K=15·30 — P-09.

## 직접 확인해 맞았던 것(confirmed)
- 대조 커밋 넷이 지금 HEAD 와 같다(7683125 · 7248651 · 9eb744d · 00d5565).
- deliberation.py 의 줄 번호·시그니처 — `_tools_by_name`(1294, user·user_pat 인자) · `_call`(1389) · `_parse_json`(1611, 마지막 dict 를 돌려준다) · `_norm_ws`(1898) · `_SUBSTANTIVE_RE`(1903) · `_agent_search_hits`(2407) · `_llm_limit`(2194) · `_restore_role`(3119, description → system_prompt) · 상수 1.05/0.93/16,000/48,000/56,000 · 좌석 지식 조회의 검색어가 question(4095) · 세마포어를 모듈에 두면 안 된다는 주석(4084-4085).
- 예산 산수 — P_hard 109,368 · B 12,126 · CARD_V 13,674 · K_out 9/19/4 · dev B 3,008 · 엔진 근거 예산 17,967 을 식대로 다시 셌다(틀 2,600 가정 아래 일치).
- app.py — delib_llm 은 늘 별도 인스턴스이고 max_tokens 는 0 이면 미전송(351-356) · `_detach_stream` 이 `_DETACHED_TASKS` 로 delib_active 에 들어간다(545-560, 4264-4270) · /health 는 delib_active·delib_queued 를 낸다 · 서버는 127.0.0.1 에 묶이고 단일 프로세스다(start.sh).
- 포털 — ChatRequest.message 65,536자 · DelibOpts 미선언 키는 model_dump 에서 사라진다 · 단발 한도 600초 · SSE 침묵 13시간 · access.yaml 에서 deliberation 이 plat:aidatahub 를 함의한다.
- AIDataHub — list_records 는 본문 없는 요약(요약 200자)·updated_at 내림차순·limit ≤ 100 · get_record 는 content 전체 · get_record_sections 는 목록 반환 · agent_search 의 top_k 는 retrieval_config 에서만 온다 · 의미 적중 snippet 은 content_text[:200] · 모르는 전문가는 'agent not found: …'.
- 카드 절 머리 줄 — 내보내기 코드(ExpertAgents aidatahub_records.py:119)가 `f"{card.title} — {heading}\n{content}"` 로 만든다. 3.4 의 머리 줄 떼기 규칙이 표본 3장이 아니라 생성 규칙과 맞는다.
- delib-busy.sh 는 delib_active·delib_queued 둘만 읽는다(키를 더해도 안 깨진다).

## 확인하지 못한 것(unknowns)
- 운영 GLM 서버가 /v1/models 에 max_model_len 을 주는가(P-05 의 갈림), 400 창 초과의 문구(P-13), 추론 글을 본문에 섞어 내는가(P-17c), max_tokens 미전송 때의 서버 기본 출력 상한.
- 러너 서비스 PAT 의 주체에 feat:deliberation·plat:aidatahub 가 계산되는가(P-03 이 실제로 터지는 조건).
- cae00 AIDataHub 의 카드 구성이 dev 측정(359명·최대 35장)과 같은가. 전문가당 100장을 넘으면 list_records 쪽 넘김(updated_at 정렬)이 실제로 흔들린다.
- tier:checklist 카드 1,463장의 type 분포. checkable 은 type 만 보므로, 점검표 등급인데 type 이 faq·data 인 카드는 판정 대상에서 빠진다(DB 에 닿지 않아 세지 못했다).
- 역할 문서(description) 길이 분포. ROLE_MAX 2,000 에서 끊기는 전문가가 몇 명인지 모른다(엔진 좌석은 무절단 — _ROLE_CLIP 0).
- 긴 문서 검색 적중에서 카드와 긴 문서의 실제 비율(P-04 의 '거의 빈다' 는 추정이다).
- TestClient 로 스트림을 닫았을 때 이 Starlette 판이 제너레이터를 즉시 닫는가(P-17l).
- WP5a 의 관문 모듈(review_gate)과 WP3a 의 `_Gate` 중 누가 실제 파일을 소유하는가 — 계약은 '전용 관문 하나' 라고만 했다.
