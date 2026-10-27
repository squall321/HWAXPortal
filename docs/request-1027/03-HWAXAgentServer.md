# HWAXAgentServer — 수정 요청 (2026-10-27 · cae00 운영 기준)


요청 HWAX Portal 운영(cae00) · 대상 저장소 HWAXAgentServer(`app.py` 챗 에이전트 · `deliberation.py` · `delib_jobs.py` · `mcp_server.py`) · 기준 판 cae00 `5502825`(10-25 피드백 · 온톨로지 시험 · 10-27 재확인) · `bb307c6`(심의 멈춤 후속 F1~F4) · `9d4c931`(심의 멈춤 R3) · `c4e4823`(지식카드) · `51f85e3`(10-18 제안) · MCP 업로드는 10-16 origin/main(커밋 표기 없음) · 심의엔진은 10-07 cae00 소스(커밋 표기 없음) · update-all 로 받는 플랫폼: 예.


줄 번호는 각 행에 적은 기준 판의 것이다. 「10-27 재확인」은 cae00 `5502825` 소스와 `/health` 를 읽기만 해서 본 결과다. 자세한 근거는 출처 칸이 가리키는 원문 절에 있다. 항목 번호 가운데 제품 코드처럼 읽힐 수 있는 것(S · A · M · X · P 로 시작하는 짧은 번호)은 원문 번호에 '-' 를 넣어 적었다(예 10-25 시험 M-14).


**한 줄**


- 포털 웹 챗은 코어 질문 16개 중 13개에서 정답 도구를 묶지도 찾지도 못한다. 도구 캐시 키(HA-01) · 코어 도구 늘 묶기(HA-02) · 프롬프트 규칙(HA-03)을 먼저 고친다.


- 허브의 큰 응답이 챗 문맥(262,144 토큰)을 넘겨 턴이 오류로 끝난다. `_cap_tool` 에서 허브 응답을 접는다(HA-04).


- 패널을 그리지 못하는 포털 챗이 패널 전용 도구를 부른다. 정확한 이름 집합 하나로 막는다(HA-05).


- 원 주인이 아닌 사람의 심의 이어하기가 원 잡의 근거 본문 · 좌석 · human_note 를 넘겨받는다. 권한 문제라 먼저 본다(HA-06).


- '(시험)' 라벨 prod 앱 처리 · 챗 경로의 PLM enrich · 사람 이름 가림은 사용자 결정 뒤에 반영한다(5절).


**건수**


| 높음 | 중간 | 낮음 · 선택 | 질문 | 결정 필요 |
|---|---|---|---|---|
| 6 | 5 | 9 | 2 | 3 |


## 1. 높음 — 먼저 고칠 것


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HA-01 | TOOL_MAX=0(무캡) 경로에서 캐시 키에 질의와 핀이 빠진다. 그래서 30분 창의 첫 질문으로 고른 도구 묶음을 다음 질문에도 그대로 쓴다. 창 중간에 앱 핀을 켜면 프롬프트 안내만 바뀌고 묶음은 그대로라, 잘린 도구는 invoke_tool 로만 닿는다. | 기준 `5502825` · `app.py:2394-2399`(pin_key · q_key 는 TOOL_MAX>0 일 때만) · `:2408`(캐시 키) · `:1903-1914`(무캡 경로 절단) · `:4330-4344`(핀 안내) · 포털 `backend/app/agent/routes.py:402`(챗 PAT 30분 창). 10-25 19:41 재기동 뒤 10-27 16:4x 까지 POST /chat 44회에 tool load 27회 · 예산 절단 25회다. 17회는 앞 묶음을 다시 썼다. HEAD `5502825` 재확인 — pin_key · q_key 는 여전히 TOOL_MAX>0 일 때만 키에 든다. | 무캡 경로에서 절단이 일어나면 q_key · pin_key 를 캐시 키에 넣는다. 아니면 사용자별로는 원본 도구 목록만 캐시하고 `_select_tools` 는 턴마다 돌린다(도구 벡터는 이미 캐시되므로 질의 임베딩 1회만 든다). | 온톨로지 시험 C-1 |
| HA-02 | 코어 허브 도구가 도구 절단에서 빠진다. 10-20 이후 웹 챗 도구 호출 722건 중 자주검증 허브 호출은 1건이다. | 기준 `5502825` · `app.py:1658-1672`(_TOOL_PRIORITY) · `:1810`(_GUIDE_FRONT) · `:1914`(_fit_schema keep). /health tool_cut 1,613 → 225(예산 88,473 토큰)였고, 재기동 뒤 절단 25회 모두에서 자주검증 허브가 빠졌다(평균 103개 중 89개). 10-27 재확인 — `/health` tool_cut(16:30)은 1,613 → 183 이고 자주검증 Datahub 97개가 빠졌다. HEAD `5502825` 에 `_ONTO_CORE` 가 없고 `_TOOL_PRIORITY` 에 허브 도구가 없다. | `_ONTO_CORE` 를 두어 늘 묶는다 — rootdesigndatahub_{object_resolve, objects_resolve_many, objects_list, objects_summary, object_get, object_fields, graph_neighbors, search} · failuretrace_{object_resolve, objects_list, objects_summary, graph_neighbors} · list_tasks · task_revisions · compare_task_revisions · find_plm_task. 사용자에게 보이는 것만 keep 에 넣는다(약 15개, 4~6천 토큰, 예산의 5~7%). | 온톨로지 시험 C-2 |
| HA-03 | SYSTEM_PROMPT 에 허브 · 코어 · plm_task 에 관한 말이 없다. app.py 는 MCP 서버 instructions 를 읽지 않아 게이트웨이 안내문과 허브 platform_profile 이 웹 챗에 닿지 않는다. 코어 질문이 코어 타입이 없는 앱(RA · MatNexus · ComponentCore · FMEA)으로 간다. | 기준 `5502825` · `app.py:129-219`(168-173 search_tools 안내 뒤에 넣는다). OT-02 · 03 · 04 · 12 · 13 의 실패 꼴은 규칙 한 줄씩으로 막을 수 있다. | 온톨로지 시험 4절 '프롬프트 규칙' 일곱 줄을 넣는다. ① 정본은 rootdesign 이고 object_resolve 를 먼저, candidates 이면 사용자에게 묻는다. ② plm_task 식별자는 과제명, 과제코드는 별칭 · task_code 다. ③ 개수는 total 이나 objects_summary 로 센다. ④ 관계는 graph_neighbors 로 본다. ⑤ 허브를 건널 때는 key 로 다시 resolve 한다. ⑥ not_configured · 404 · 빈 출력은 '조회 실패' 로 말한다(시험 앱 문구는 HA-23 결정을 따른다). ⑦ RA · MatNexus · ComponentCore 로 코어 질문을 보내지 않는다. | 온톨로지 시험 C-3 · N-17(챗 몫) |
| HA-04 | 허브의 큰 응답이 챗 문맥을 넘겨 턴이 오류로 끝난다. 도구 결과 상한 TOOL_RESULT_MAX 기본이 200,000자라 사실상 상한이 없다. StepForge 는 자기 컷(6,000자)이 'TOOL_RESULT_MAX 와 같아야 한다' 고 안내해 두 값이 어긋난다. | 기준 `5502825` · `app.py:1027`(기본 200,000, 박스 .env 에 없음) · `:1410`(_cap_tool). /health chat_llm.last_error 'ChatCtxOverflow … maximum context length is 262144 tokens' · GLM 으로 넘긴 것 5회, GLM 도 300,000 토큰 초과로 실패 · chat error 2건(10-26 09:53 · 10-27 06:00:41). 시험 단일 응답 135,566 · 104,048 · 50,738자. HEAD `5502825` 의 `:1027` 기본값도 200,000 그대로다. | `_cap_tool` 에 허브 응답 접기를 넣는다 — `*_objects_summary` 는 group_options 빼기, `*_object_get` 은 related 를 관계별 수 + 앞 N줄로, objects_list 는 ref_labels · properties_schema 걷기. 박스 .env 값(4만~6만 자)과 StepForge 컷 값은 우리가 맞춘다(90-OURS-box-todo.md OB-29). | 온톨로지 시험 C-6 · N-10 — 높음은 C-6 을 따름(챗오류) |
| HA-05 | 패널을 그리지 못하는 포털 챗이 패널 전용 도구를 묶어 부른다. 사용자는 패널 없이 글 몇 줄만 본다. `open_resin_panel` 설명은 '묻지 않아도 먼저 호출' 이다. | 기준 10-16 origin/main · `app.py:1850-1856`(_AGENT_DENY_TOOLS · _agent_denied · _get_tools_retry) · `app.py:1070-1080`(invoke_tool 이름과 `<앱키>_` 별칭 막기). 10-14 에 open_resin_panel 1회 · open_workflow_panel 3회(결과 261~1,008자)를 불렀다. 10-27 재확인 — `5502825` 의 app.py 에 패널 이름 막기가 없다(grep 0). 줄은 옮겨졌다(HEAD 5502825 기준 거부 집합 :2284 · `_agent_denied` :2287-2290 · `_get_tools_retry` 거르기 :2363 · invoke_tool 막기 :1459-1468). | 같은 거부 경로에 별도 집합(정확한 이름만)을 더한다 — open_workflow_panel · open_resin_panel · open_camfpcb_panel · open_frc_panel · open_gi_panel · open_magnet_panel · panel_upload_begin · panel_upload_append · panel_upload_commit. ARP `arp_upload_open` 을 넣을지 함께 정한다. `*panel*` 무늬는 쓰지 않는다(risk_list_panels 가 걸린다). `_AGENT_DENY_TOOLS` 자체는 건드리지 않는다(`tests/test_external_llm_review_fixes.py:384` 가 고정한다). M-2 가 들어오면 이 집합을 푼다. | MCP 업로드 M-0 |
| HA-06 | 원 주인이 아닌 사람(같은 소속 · 관리자)의 심의 이어하기가 원 잡의 시작 인자 파일(근거 본문 · 좌석 · human_note)을 그대로 쓴다. 원장에는 수만 남았던 근거가 그 사람의 새 잡에 실리고, 원 주인의 한 번뿐인 이어하기도 소진된다. | 기준 `bb307c6` · `mcp_server.py:579`(_resume) · `:620` · `:632`(HEAD 5502825 기준 `_resume` :572). | 시작 인자 파일은 주인 본인의 이어하기에만 쓴다. 다른 사람에게는 남은 손잡이와 좌석만 넘긴다. | 심의 멈춤 F1 |


## 2. 중간


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HA-07 | 어휘 토큰화에 잡음(한 글자 · 띄어 쓴 조사 · 채움말)이 남아 긴 설명의 도구에 우연 적중한다. 앱 라벨 '(시험)' 때문에 '시험' 이 든 질문마다 230개가 적중한다(C-4 실측). | 기준 `5502825` · `app.py:1947-1971`(_TOOL_STOP · _JOSA_T · _tok_query) · `:1851-1856`(rel = 적중 토큰 / 질의 토큰) · `:1861`(lex_order). 15/16 질문에서 허브 핵심 도구(object_resolve · graph_neighbors · search)의 적중이 잡음과 우연 적중뿐이다. | 한 글자 한글 토큰과 조사 단독 토큰을 버리고 채움말(있으면 · 같이 · 뭐야 · 그리고 등)을 불용어에 더한다. 점수를 토큰 수 비율이 아니라 IDF 가중으로 바꾼다. 앱 라벨 적중은 질의가 앱을 지목할 때만 센다. | 온톨로지 시험 C-7 · C-4(라벨 적중 실측) |
| HA-08 | 위키가 꺼져 있는데 심의 옵션 'MX 백서 위키에도 남기기' 를 켜면 결정문 끝마다(다단이면 단마다) 내부 오류 문구가 붙는다. | 기준 `5502825` · `deliberation.py:3339-3349`(_wiki_note 가 '⚠ MX 백서 위키에 남기지 못했다 — …' 를 붙임) · `:3359`(_wiki_submit). 10-25 업데이트로 생겼다. | 위키가 꺼져 있으면 `_wiki_submit` 을 건너뛰고 한 줄만 남긴다. 다단 심의에서는 한 번만 시도한다. 켜짐 여부를 어디서 읽을지는 포털 몫(PT-1)과 같은 신호로 맞춘다. | 10-25 피드백 PT-1(에이전트 몫) |
| HA-09 | 재기동으로 끊긴 심의의 이어하기가 끝난 라운드 다음부터 다시 돈다. 끊긴 라운드와 해석 설계 · 시험 설계는 처음부터 다시 해서, 결정문 직전에 끊기면 몇십 분이 사라진다. | 기준 `9d4c931` · `delib_jobs.py:807`(reap_orphans) · 체크포인트 칸 `:525-526` · `:883-884`. `bb307c6` 판의 이어하기도 잡의 checkpoint 칸을 쓰지 않는다(F4). | `reap_orphans` 가 잡을 interrupted 로 닫을 때 체크포인트 유무를 남긴다. `deliberate_continue` 한 번으로(또는 자동으로) 그 체크포인트에서 끊긴 라운드부터 다시 돌게 한다. | 심의 멈춤 R3 · F4 |
| HA-10 | 심의 잡 폴더(`args/` · `state/`)와 잡 원장의 권한이 넓다. | 기준 `bb307c6` · `delib_jobs.py:308` 근처. 폴더가 상위 폴더를 따라 2775(공유 그룹)로 만들어진다(파일은 0600). 잡 원장은 664 다. | 폴더는 0700 으로 만들고 잡 원장은 0640 이하로 낮춘다. | 심의 멈춤 F2 |
| HA-11 | 심의 엔진이 agent_search 를 날짜 컷오프 없이 불러, 소급 검증에서 출시 뒤에 들어온 레코드도 근거로 잡힌다. | `deliberation.py:1830`(10-07 cae00 소스). AIDataHub 검색에는 날짜 필터가 없다(`search_svc.py` grep 0건). | AIDataHub 가 `as_of` 를 받게 되면 엔진이 그 값을 함께 보낸다. AIDataHub 쪽은 믿을 날짜 칸부터 정해야 한다(created_at 은 원문 날짜가 아니라 허브 반입일이다). | 심의엔진 2-2(엔진 몫) |


## 3. 낮음 · 선택


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HA-12 | 자기검증 검토자가 도구 없는 턴에서도 일반 지식 수치에 '(근거 없음 — 추정)' 을 달고 '고침' 으로 판정한다(표본 1). | 기준 `5502825` · `app.py` `_SELF_CHECK_ASK` 의 ②는 표시하라고 하는데 `_self_check_messages` 의 도구 없는 턴 블록은 ①③④만 본다고 적는다. `_self_check_skip` 은 이 턴을 건너뛰지 않았다. 자기검증은 `d8011e0` 에서 들어왔다. | 도구 · 문서가 없는 턴에서는 ②를 빼거나 '일반 지식 수치는 표시하지 않는다' 로 바꾸고 회귀 시험을 넣는다. | 10-25 피드백 AG-1 |
| HA-13 | 자기검증 런타임이 `/health` 에 없어 운영자가 검토자의 실패 · 지연을 알 수 없다. | 10-25 `/health` 키 목록에 self_check 가 없다. 10-27 재확인 — `5502825` 의 `/health` 에도 없다. | `/health` 에 `self_check {on, counts, ms p50/p95, last_error}` 를 싣는다. 포털 update-all §7 스모크가 그것을 읽는다(포털 몫). | 10-25 피드백 AG-2 |
| HA-14 | 자기검증이 끝나야 본문이 나오고, '고침' 이면 답 전체를 다시 써 긴 답의 체감 지연이 커진다(추정). | 작은 검토 0.948 s · decode 221~253 tok/s · `_self_check_stream` · `_self_check_messages` 는 검토자에 max_tokens 를 보내지 않는다. 큰 입력의 prefill 은 재지 않았다. | 검토 입력에 별도 상한을 두고, '고침' 은 패치(고친 줄)로 받는다. ms p95 를 모아 상한을 정한다. | 10-25 피드백 AG-3 |
| HA-15 | 영어 질문에도 한국어로만 답한다. | 기준 `5502825` · `app.py:130` '반드시 한국어로만 답하세요'(10-27 재확인) · OT-07. | '사용자 질문의 언어로 답하되 기본은 한국어, 중국어 전환 금지' 로 바꾼다. | 온톨로지 시험 C-14 |
| HA-16 | 도구 의미 색인이 하나뿐이라 작은 도구 목록이 큰 색인을 밀어내고, 다음 챗 턴이 1,613개를 다시 임베딩한다. | 기준 `5502825` · `app.py:1688`(_TOOL_VEC 전역 하나) · `:1722-1736`(_ensure_tool_vecs) · 로그 1613 → 10 → 1613 → 10. | 서명(sig)별 작은 LRU 캐시를 두어 공존시킨다. | 온톨로지 시험 C-15 |
| HA-17 | 심의 좌석이 조회로 받은 그림의 판독만 끄는 손잡이가 없다. `VISION_TRANSCRIBE_MAX=0` 은 챗과 띵킹의 판독까지 함께 끈다. | 기준 `bb307c6` · `deliberation.py:4093` → `app.py:5345-5382`. | 좌석 그림 판독 전용 env 를 두고 그 상태를 `/health` 에 보인다. | 심의 멈춤 F3 |
| HA-18 | (선택) 긴 카드를 나눠 보일 때 글자 위치 그대로 잘라 마크다운 표 · 코드펜스 · `$$` 수식 한가운데서 끊길 수 있다. | 기준 `c4e4823` · `app.py:6116`. | 절단점을 그 절 안의 마지막 빈 줄로 당긴다. | 지식카드 K3-2 |
| HA-19 | (나중에) 모의해석(SIM) 카드가 「원문(JSON)」 섹션 하나로만 보인다(1,506자/86줄 · 2,312자/119줄 · 1,903자/89줄). | 기준 `c4e4823` · `_record_view` `app.py:4598-4600` · `:4631-4636`(JSON 폴백) · `_cell` `:4591` · 근거 AIDataHub `api_server/src/api/schemas/sim.py:30-53`. | `content.components` 가 dict 목록이면 부품 표(pid · title · elem_class · n_elems · area_ext · volume · material.name)로 싣는다. `connectivity.contact_edges` 와 `attachments` 는 짧은 섹션으로, 나머지 키는 마지막 「원문(JSON)」 섹션에 남긴다. 표를 채우면 폴백 조건(`:4631`)이 꺼지므로 남은 JSON 은 따로 붙인다. 포털은 바꿀 것이 없다. | 지식카드 K9-2 |
| HA-20 | (2단계) 도구 결과의 `_meta` 를 버려 패널을 알릴 길이 없다. | 기준 10-16 origin/main · `app.py:3400-3445`(on_tool_end 는 status SSE 만 낸다) · langchain-mcp-adapters 결과 변환이 structuredContent 만 남긴다. | `_meta.ui.resourceUri` 가 있는 도구의 결과를 그대로(content · structuredContent · `_meta`) 받아(MultiServerMCPClient tool interceptor) 새 SSE `ui_resource` {호출 id · 도구 · 백엔드 · resourceUri · 도구 입력 · 도구 결과}를 낸다. 게이트웨이 1단계 중계와 브리지 보안 규칙이 먼저다. | MCP 업로드 M-2 ① |


## 4. 질문 · 확인 요청


| # | 묻는 것 | 왜 · 근거 | 출처 |
|---|---|---|---|
| HA-21 | 카탈로그가 바뀌어도 `agent_cache` 가 옛 도구 묶음을 기한 없이 둔다. 새 도구는 search_tools · invoke_tool 로 바로 닿는데, 이것으로 충분한지 아니면 카탈로그가 바뀌면 캐시를 비울지 답해 달라. | `app.py:2385`(FMEA 연결 문서 10-21, 에이전트 커밋 표기 없음). HA-01 과 같은 캐시라 함께 고치면 한 번에 끝난다. | FMEA 연결 1-9⑧ |
| HA-22 | (관찰) stcx 챗 LLM 으로 바꾼 뒤 한 대화에서 '도구 미호출(예고만) — 강제 지시로 1회 재시도' 가 4번 났다. 이 형식을 파서 · 프롬프트가 다 받는지 아는 것이 있으면 알려 달라. | 기준 `51f85e3`. 그때는 도구가 빠진 문제(10-18 F1)와 겹쳐 원인을 가르지 못했다. 우리가 같은 질의로 다시 잰다(90-OURS-box-todo.md OB-71). 그때도 잦으면 따로 청한다. | 10-18 제안 F5 |


## 5. 결정 필요 (사용자)


| # | 정할 것 | 선택지 | 권고(원문) · 주의 | 출처 |
|---|---|---|---|---|
| HA-23 | '(시험)' 라벨 prod 앱(dynaforge-prod 72개 · stepforge-prod 158개)을 웹 챗 묶음 후보에 둘지. 지금 OT-02 · 03 · 13 상위가 dynaforgeprod_* 이고 OT-14 1위가 stepforgeprod_find_plm_task 다. | (가) 빼기 — CHAT_EXCLUDE_APPS(기본 dynaforge-prod, stepforge-prod)로 묶음 후보에서 뺀다. 프롬프트 규칙 ⑥ 에 '(시험) 앱은 부르지 않는다' 를 넣는다. (나) 라벨 바로잡기 — '[… prod(시험)]' 라벨은 `app.py:1596-1605` `_tag_tool_app` 이 앞에 붙이기만 하고, 글자는 박스 권한표(backend/config 의 *.local.yaml, label 66 · 78행 · 안내 문구 85행)에서 온다(app.py 에는 '(시험)' 글자가 없다). 박스에서 고치면 에이전트 코드 변경은 없다. | 원문 권고는 (가)다. 주의 — 두 앱은 10-23 가동 · 10-27 코어 연결로 실제 운영 데이터를 가진 앱이 됐다. '(시험)' 라벨이 낡았을 수 있다. (나)를 고르면 HA-07 의 '시험' 적중 잡음이 사라지고, 정본과 겹치는 결과는 게이트웨이 정본 하나만 올리기(HG-01)로 줄인다. | 온톨로지 시험 C-4(에이전트 몫) |
| HA-24 | 챗 경로에서 plm_defect_search 의 enrich 기본을 0 으로 감쌀지. 기본 enrich=5 는 PLM 원본을 다시 부른다. 10-20 이후 웹 챗 plm-defect 호출은 72건이고, PLM 한도는 하베스터 · 챗 · 웹이 하나를 같이 쓴다. | (가) 보류 유지 — 게이트웨이 노출 enrich 기본값(10-25 D4)과 같은 손잡이라 PLM 보류를 풀 때 함께 보낸다. (나) 챗 쪽만 먼저 — `app.py:129-219` 프롬프트 한 줄 또는 `_cap_tool` 의 인자 기본 덮개로 enrich=0 을 쓰고, 사용자가 '실시간 상태' 를 요구할 때만 올린다. | 원문은 중간 개발 요청으로 적고 'PLM 쪽 코드가 아니라 챗 쪽 기본값이라 보류 대상이 아닐 수 있다' 고 했다. 보류 범위인지 사용자가 정한다. 보류가 아니면 (나)다(10-25 D4 도 0 을 권했다). | 온톨로지 시험 C-13 |
| HA-25 | FailureTrace pd_defect 행의 label · content_text 에 실린 검출자 · 작업자 이름을 어디서 가릴지. | (가) FailureTrace 출력에서 이름 칸을 가린다(12-Datahub-platform.md DP-08). (나) 챗 어댑터에서 사람 이름 패턴을 걸러 낸다(에이전트). | 원문 1안은 (가)다. (나)는 (가)가 안 될 때의 대안이다. 가릴 범위 자체는 10-25 D5(게이트웨이로 나가는 응답 기본 가림 권고, 02-HWAXMcpGateway.md HG-20 · 90-OURS-box-todo.md OB-07)와 묶여 있다. | 온톨로지 시험 N-18 · 10-25 피드백 D5 |


## 6. 다른 플랫폼과 맞물린 것


- **'(시험)' 라벨 prod 앱(C-4)** — 이 플랫폼 몫은 묶음 후보 처리(HA-23)다. `search_tools` 쪽은 HWAXMcpGateway 요청서(02-HWAXMcpGateway.md) HG-19, 박스 권한표 label · 오버레이와 결정 기록은 우리 몫 문서(90-OURS-box-todo.md OB-04)다. KooRemapper · StepForge 는 할 일이 없다(04 · 05 의 6절). 출처 온톨로지 시험 C-4.


- **도구 캐시 · 상한(HA-01)** — 포털 update-all 이 원격 LLM 이면 TOOL_MAX=0 을 '전량 바인딩' 이라며 다시 덮는다. HA-01 을 고치기 전에는 덮지 않게 하는 것은 01-HWAXPortal.md HP-07 이다. 포털 챗 PAT 30분 창(`routes.py:402`)은 바꿀 것이 없다. 출처 온톨로지 시험 C-1 · C-8 · 10-25 피드백 PT-3.


- **큰 응답(HA-04)** — 원천에서 줄이는 것은 Datahub-platform 요청서(12-Datahub-platform.md DP-01 — ref_labels 를 페이지에 한 번 · group_options 기본 제외 · related 접기)와 StepForge 요청서(05-StepForge.md ST-02 — find_plm_task 의 sync 는 status · as_of · problems 만)다. 박스 .env 의 TOOL_RESULT_MAX(4만~6만 자)와 STEPFORGE_CHAT_CUT 같은 값 맞추기는 우리 몫 문서(90-OURS-box-todo.md OB-29)다. 출처 온톨로지 시험 C-6 · N-10 · N-11.


- **코어 도구 찾기(HA-02 · HA-03)** — 게이트웨이 `search_tools` 동의어 · 정본 하나만은 02-HWAXMcpGateway.md HG-01, 허브 도구 설명의 설치별 tagline 은 12-Datahub-platform.md DP-03, hwax-batch 앱 설명 문안은 90-OURS-box-todo.md OB-33 이다. 코어 운영자 페르소나 he-data-coreontology 는 01-HWAXPortal.md HP-20 과 90-OURS-box-todo.md OB-32 이고, 에이전트는 기존 운영자 key_tools 우선 길(`app.py:4234-4247`)을 그대로 쓴다. 출처 온톨로지 시험 C-5 · C-10 · C-11 · C-12.


- **과제코드 규칙(HA-03 ②)** — 과제코드를 task_code · 별칭으로도 대조하는 것은 04-KooRemapper-DynaForge.md KR-01 과 05-StepForge.md ST-01 이다. SignalForge 거울의 같은 가정은 08-SignalForge.md SG-03 이다. 일반 사용자가 ontology_sync_state 를 못 읽는 채로 두면(04-KooRemapper-DynaForge.md KR-17), 프롬프트에 'list_tasks 의 sync_enabled · last_status · last_run_at 을 본다' 한 줄을 더하는 대안이 있다. 출처 코어 요청 K-1 · S-1 · 온톨로지 시험 N-7.


- **위키가 꺼졌을 때(HA-08)** — 챗 버튼 · 심의 옵션 숨기기와 켜짐 여부 내보내기는 01-HWAXPortal.md HP-16, `wiki_*` 조건부 등록은 09-MXWhitePaper.md MW-01 이다. 출처 10-25 피드백 PT-1 · MX-2.


- **자기검증 관측(HA-13)** — update-all §7 스모크가 `/health` 의 self_check 를 읽게 하는 것은 01-HWAXPortal.md HP-24 다. 출처 10-25 피드백 AG-2.


- **패널(HA-05 · HA-20)** — 게이트웨이의 `_meta` · `ui://` 리소스 중계(02-HWAXMcpGateway.md HG-07)가 먼저다. 포털 챗 호스트(샌드박스 iframe · 브리지 · 보안 규칙)는 01-HWAXPortal.md HP-42 다. SimFlow 패널 도구 설명 다듬기는 14-Partner-apps.md PA-04 다. M-2 가 들어오면 HA-05 의 집합을 푼다. 출처 MCP 업로드 M-0 · M-1 · M-2.


- **날짜 컷오프(HA-11)** — `as_of` 를 받고 믿을 날짜 칸을 정하는 것은 AIDataHub 요청서(10-AIDataHub.md AD-07)다. 출처 심의엔진 2-2.


- **카드 보기(HA-18 · HA-19)** — 재료 카드의 6만 자 절단은 원천(MaterialTwinWeb)에서 절 여러 개로 내보내기로 정해졌다(06-HEAXHub.md HH-01). SIM 카드 표는 포털이 이미 그린다. 출처 지식카드 K3-9 · K9-2.


- **심의 한도와 맞출 것** — 포털 업무 절차 `procedures_concurrency = 2` 와 리스크 앱 `risk_concurrency = 2` 를 심의 6 에 맞출지는 01-HWAXPortal.md HP-45 와 07-hwax-risk.md RK-08 이다. 웹 심의 좌석 상한 20(포털 3곳)은 01-HWAXPortal.md HP-49 다. 에이전트 몫은 없다. 출처 심의 멈춤 §3 · 심의엔진 4-2.


- **update-all 자동 복구** — 포털 repair_mcp 가 재기동 전에 `/health` 의 심의 상태를 보게 된다(01-HWAXPortal.md HP-08). 에이전트 몫은 없다. 출처 update-all 안전 U5-2.


## 7. 다시 볼 시험


| 시험 | 언제 | 볼 것 |
|---|---|---|
| OT-01~16 전부 | HA-01~04 와 게이트웨이 HG-01 · C-4 결정을 반영한 뒤 | `search_tools` 상위와 `/health` tool_cut 을 다시 재고, 온톨로지 시험 5절대로 웹 챗 16개를 돌린다. |
| OT-02 · 03 · 04 · 12 · 13 | HA-03 뒤 | 정본 resolve 먼저 · 과제명 key · total 로 세기 · 허브 건널 때 다시 resolve · 조회 실패를 '없음' 으로 말하지 않기. |
| OT-04 · 09 · 11 · 12 · 14 | HA-04 뒤 | 같은 질문에서 ChatCtxOverflow 가 나지 않고 답이 정답 수를 유지한다. |
| OT-07 | HA-15 뒤 | 영어 질문에 영어로 답하면 가산이다. |
| OT-15 | HA-24 결정 뒤 | plm_defect_search 가 기본 enrich 로 불리지 않는다. |
| 10-25 피드백 M-7 · M-8 · M-9 · M-10 | HA-12~14 뒤 | 도구 없는 턴의 '(근거 없음 — 추정)' 재현 여부(M-9), '검증 ✓ (N초)' 와 지연, 중지 동작(M-10). |
| 10-25 피드백 M-12 | HA-08 뒤 | 위키가 꺼져 있으면 심의가 위키 제출을 시도하지 않고, 결정문 끝에 오류 문구가 단마다 붙지 않는다. |
| HA-05 확인 | 반영 뒤 | 포털 챗에서 'simflow 로 수지 도포 돌려줘' 가 `open_*_panel` 이 아니라 `prepare_run` 으로 시작한다. |


## 8. 이 문서에서 뺀 것


- 심의 좌석 자유 조회 허용 목록(`_FREE_ALLOW`)에 PLM 읽기 도구 더하기 — PLM 보류(사용자 「일단 PLM 관련은 그대로 두자」)라 넣지 않았다. 별도 PLM 신원 요청서도 보내지 않는다.


- 박스 .env 의 TOOL_RESULT_MAX · STEPFORGE_CHAT_CUT 값 — 우리 몫이다(90-OURS-box-todo.md OB-29).


- 심의 설정값 DELIB_DECISION_CTX=24000 · DELIB_EVID_ITEMS=120 — 설정으로 처리하기로 한 우리 몫이다(심의엔진 §5, 90-OURS-box-todo.md OB-30).


- 박스 .env 의 DELIB_JOB_MAX_RUNNING=6 · DELIB_JOB_MAX_RUNNING_PER_USER=6 을 걷을지 — 엔진 `bb307c6` 이 `POST /limits` 를 받으므로 우리가 정한다(심의 멈춤 §2-1, 90-OURS-box-todo.md OB-84).


- 새 심의 멈춤 · 재기동에도 남는 대기열 · 재기동 없는 한도 · 섞인 GLM 풀의 창 — `bb307c6` 로 반영됐다(심의 멈춤 R1 · R5).


- 심의엔진 §1 · §2-1 · §3 · §4-1 · 4-3 · 4-4 와 좌석 상한의 엔진 쪽 — `b7c76c9` · `d51a156` 로 반영됐다.


- 지식카드 K3 요청 1~8(`ae73f44`) · K5 의 에이전트 몫(`3bba0c5`) · K9 요청 1(`ed908c6`) — 반영됐다.


- 지식카드 K3-9 의 에이전트 대안(읽기 칸에서 properties 를 덧붙이기) — 원천(MaterialTwinWeb)에서 고치기로 정해져 요청하지 않는다.


- 10-18 제안 F1 · F2 — 반영됐다.


- 챗 자기검증 기본 켬 — 사용자 결정(SC-D1)이라 그대로 둔다.


- env 킷의 DELIB_TIMEOUT_S 주석과 동작 어긋남 — 포털 infra 몫이고 값(1800)이 코드 기본값과 같아 동작은 같다(01-HWAXPortal.md HP-39).


- 챗 LLM 모델 서버 재기동 일정 · 키 전달 — 우리 몫이다(Qwen 안내, 90-OURS-box-todo.md OB-01 · OB-02 · OB-03).
