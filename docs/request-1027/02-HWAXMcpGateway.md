# HWAXMcpGateway — 수정 요청 (2026-10-27 · cae00 운영 기준)


요청 HWAX Portal 운영(cae00) · 대상 저장소 HWAXMcpGateway(`gateway.py` · `provision-config.sh` · `rest_proxy.py` · `tool_areas.json` · 시험 `test_gateway.py` · `test_provision_urls.py`) · 기준 판 cae00 `7c12cb7`(10-25 피드백 · 온톨로지 시험 · 10-27 재확인) · `f8e7920`(MCP 업로드 · 파트너 타일 · update-all 안전) · `095c93a`(10-17 수정 목록) · `8e30ee5`(FMEA 연결) · update-all 로 받는 플랫폼: 예.


줄 번호는 각 행에 적은 기준 판의 것이다. 「10-27 재확인」은 cae00 `7c12cb7` 을 읽기만 해서 본 결과다. 자세한 근거는 출처 칸이 가리키는 원문 절에 있다. 항목 번호 가운데 제품 코드처럼 읽힐 수 있는 것(S · A · M · X · P 로 시작하는 짧은 번호)은 원문 번호에 '-' 를 넣어 적었다(예 10-25 시험 M-14).


**한 줄**


- 가장 급한 것은 `search_tools` 순위 함수 하나다. 코어 질문 16개 중 15개에서 상위 8에 허브 온톨로지 읽기 도구가 0개이고, 품질 질의에는 심의 · 쓰기 도구가 위로 온다(HG-01).


- 사람별 위임 단발 세션(`_oneshot`)을 건드리는 셋 — ODB 토큰을 헤더로(HG-02) · 401 일 때만 재발급(HG-03) · SimFlow REST 중계(HG-04) — 은 한 번에 보내고 시험 한 벌로 본다.


- 감사 기록이 오류 봉투를 ok 로 적어 실패를 셀 수 없다(HG-06). 도구 `_meta` 와 `ui://` 리소스가 떨어져 게이트웨이에 붙은 Claude Desktop 에서도 패널이 안 뜬다(HG-07).


- heax PAT 를 지운 뒤에 새로 찍는 순서라 발급이 한 번 실패하면 heax 앱 9개가 챗에서 빠진다(HG-08). 지금은 박스가 토큰을 고정해 막아 두었다.


- '(시험)' 라벨 prod 앱(dynaforge-prod · stepforge-prod) 처리와 나가는 응답의 개인정보 가림 범위는 사용자 결정 뒤에 반영한다(5절).


**건수**


| 높음 | 중간 | 낮음 · 선택 | 질문 | 결정 필요 |
|---|---|---|---|---|
| 4 | 4 | 5 | 4 | 2 |


## 1. 높음 — 먼저 고칠 것


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HG-01 | `search_tools` 가 코어 정본 읽기 도구를 위로 올리지 못한다. 품질 질의에는 심의 · 쓰기 도구를 위로 올리고 plm-search-agent 도구는 찾지 못한다. | 기준 `7c12cb7` · `gateway.py:2486-2511`(_SYN — 원인 · 불량 · 설계 · 계획 · 선택 → deliberate) · `:2516-2536`(부분문자열 빈도 · 이름 적중 4점 · 쓰기 감점 없음) · 게이트웨이 환경에 GATEWAY_TOOL_SEARCH_EMBED_URL 없음. 16개 중 15개에서 상위 8에 허브 온톨로지 읽기 도구 0개다. '시장 불량 원인 대책'(limit 10)은 상위 10 중 deliberate_* 8개이고 plm_defect_search · VOC 도구는 0개다. OT-16 은 상위 8 중 6개가 쓰기 · 적용 도구다. 점수가 같으면 이름순이라 사본 허브가 앞, 정본이 뒤다. HEAD `7c12cb7` 재확인 — `_SYN`(:2486)에 원인 · 불량 · 설계 → deliberate 가 그대로이고, 점수(:2516-2536)에 쓰기 감점 · same_in 이 없다. | 온톨로지 동의어를 허브 읽기 도구에 잇는다(과제 · 과제코드 → object_resolve · plm_task, 고장모드 → failure_mode, 시험항목 → test_item, 가상검증 → sim_capability, 관리 기준 → criterion, 물성 · 영률 → material_property, 전작 → predecessor · graph_neighbors). quality · voc 도구에 불량 · 시장 · 원인 · 대책 · 사례 가중을 준다. 쓰기 낱말이 없는 질문에서는 쓰기 · 잡 시작 도구를 감점하고 write 표지를 단다. 같은 설명의 허브 도구는 정본 하나만 올리고 나머지는 `same_in: [...]` 로 접는다. 진짜 앱 라벨 적중에도 이름 적중과 같은 가중을 준다. plm-search-agent 를 quality 영역에 묶을지 검토한다. 임베딩 RRF 는 따로 본다. | 온톨로지 시험 C-5 · C-4(가중 부분) · 10-25 피드백 GW-1 — 높음은 C-5 를 따름(광범위) |
| HG-02 | ODB 서비스 토큰을 백엔드 URL 쿼리(`?token=`)에 싣는다. 토큰이 접속 · 프록시 로그에 남는다. 사람별 위임 때 팀 토큰(쿼리)과 사용자 토큰(헤더)이 한 요청에 같이 가서, ODB 가 쿼리를 먼저 보면 사용자 호출이 팀 계정으로 찍힌다. | 기준 `f8e7920` · `provision-config.sh:561-563` · `:448-451`(직전 config 이어받기) · `:573`(ARP 블록 주석) · `test_provision_urls.py:793` · `:802` · 관련 `gateway.py:3485-3492` → `_oneshot`. HEAD `7c12cb7` 에서도 쿼리 꼴이다(HEAD 7c12cb7 기준 이어받기 :507-510 · url :621 · ARP 주석 :632). ODB 는 10-15 에 `/mcp` 가 Bearer 를 받는다고 회신했다. | odb-hub 를 `url=<base>/mcp` 와 `headers.Authorization`(Bearer)로 싣는다. 이어받기는 헤더를 먼저 보고 옛 쿼리 꼴도 읽는다. 시험 기대값을 헤더 꼴로 바꾸고, 직전 config 가 쿼리 꼴일 때 이어받는 경우를 하나 더한다. ARP 블록 주석(`:573`, HEAD 기준 :632)도 고친다. | 파트너 타일 T4 · 10-17 수정 목록 G1 — 높음은 T4 를 따름(위임) |
| HG-03 | 사람별 위임 호출이 실패하면 시간 초과만 빼고 어떤 실패에도 토큰을 강제로 다시 발급하고 한 번 재시도한다. 동시 401 은 각자 발급해 덮어쓴다. 발급마다 이전 토큰이 무효화되는 앱(SimFlow)과 맞지 않는다. | 기준 `f8e7920` · `gateway.py:3671-3697` · `USER_PAT_TTL_S=43200`. 10-16 에 SimFlow `/auth/sso` 가 500 을 내자 한 호출이 발급을 두 번 불렀다(사용자 1명 · 호출 6). | 401(예외 묶음 안은 재귀로 본다 — `_oneshot` 이 두 겹으로 감싼다)이나 `_token_rejected(res)` 일 때만 다시 발급한다. 5xx · 연결 오류 · 발급 실패에는 다시 발급하지 않는다. 강제 재발급을 `_user_pat(app, email, stale=…)` 로 바꿔 잠금 안에서 캐시 토큰이 `stale` 과 같을 때만 새로 받는다. (선택) `per_user_sso` 항목에 앱별 캐시 수명 `ttl_s` 를 둔다. | MCP 업로드 T1 |
| HG-04 | REST 중계(`/api/<site>/…`)에 SimFlow 가 없다(404). per_user 사이트는 위층이 401 을 내도 캐시 토큰을 계속 쓴다. | 기준 `f8e7920` · `provision-config.sh`(dyna-forge 블록 뒤 `:801` 부근) · `rest_proxy.py` · `gateway.py` `rest_call`. 10-27 재확인 — `7c12cb7` 의 `rest_proxy.py` · `provision-config.sh` 에 simflow · `_forget_user_pat` 가 없다. SimFlow 는 발급할 때마다 이전 토큰을 무효화한다. | `per_user_sso` 에 simflow 가 있으면 `rest["simflow"] = {"base": <sso_url 의 origin>, "per_user": "simflow"}` 를 더한다. `rest_proxy` 는 위층 401 이고 쓴 토큰이 캐시와 같을 때만 `_forget_user_pat(app, email, tok)` 로 캐시를 버리고, `X-Gateway-Token-Evicted: 1` 로 게이트웨이 자신의 401 과 구별한다(흘려보낸 본문이라 안에서 재시도하지 않는다). `rest_call` 은 같은 처리 뒤 한 번 재시도한다. | MCP 업로드 U1 |


## 2. 중간


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HG-05 | 영역 분류의 미분류가 61.8% 다. 코어 허브 도구가 '사내 지식 검색' 영역에 하나도 없다. include_tools=false 가 영역 요약에 먹지 않는다. | 10-27 `/tools-map` 기준 미분류 996/1612(61.8%) · 허브 셋 각 102/103 · componentcore 182/183 · matnexus 128/128 · fmea 23/23 · odb-hub 39/39 · arp 30/30 미분류 · '사내 지식 검색' 영역(55개)에 코어 허브 도구 0개. 10-25 옛 판 측정은 58% 였다. 저장소 `tool_areas.json` 의 apps · patterns(분류 커밋 `676da93` · `c99029d` 뒤에도 남음). | patterns 맨 앞에 코어 정규식(→ knowledge)을 넣는다(온톨로지 시험 4절 '영역 규칙' 문안). apps 기본값 — 허브 셋 → data, componentcore → cad, matnexus → material, fmea → quality, odb-hub → cad, arp → result, simflow · simengbay · ste → sim, dynaforge-prod → result, stepforge-prod → cad. fmea 불량사례와 `voc_*` 는 quality · voc 로 옮긴다. include_tools=false 를 영역 요약에도 적용한다. 선언 플랫폼(connect) 도구는 선언에 `area` 칸을 둘지, 게이트웨이가 `desc` 로 가를지 정해 알려 달라(지금은 apps 에 키가 없어 fmea 23/23 이 unclassified 다). | 온톨로지 시험 C-9 · 10-25 피드백 GW-4 · FMEA 연결 1-9⑦ — 중간은 C-9 를 따름(재측정) |
| HG-06 | 감사 기록이 오류 봉투를 ok=True 로 적는다. 예외로 끝난 호출만 ok=False 다. 그래서 점검기와 사용 통계가 실패를 셀 수 없다. | failuretrace_graph_neighbors(자주검증 id)는 [APP-GRAPH-0001] 인데 ok=True · 48자다. find_reports 빈 출력은 ok · chars 0 이다. SignalForge get_ontology 의 {error: numpy 없음}(124자)도 ok=True 다. task_revisions 404 · 권한 거절처럼 예외로 끝난 것만 ok=False 다. | 응답에 error 키(또는 isError)가 있으면 ok=false 로 적는다. | 온톨로지 시험 N-13 |
| HG-07 | 집계 때 도구 `_meta` 를 버리고 `resources/*` 처리기가 없다. 그래서 게이트웨이(`/mcp-gw/mcp`)에 붙은 Claude Desktop 에서도 SimFlow · ARP 패널이 뜨지 않는다. | 기준 `f8e7920` · `gateway.py:734-743`(name · description · 스키마 · annotations · title 만 옮긴다) · `:694` 부근(집계) · `_INSTRUCTIONS` 1번. 10-27 재확인 — `7c12cb7` 에 list_resources · read_resource 처리기가 없다. SimFlow 백엔드는 패널 도구 6종에 `_meta.ui.resourceUri` 와 리소스 6개를 이미 낸다. | 도구를 다시 만들 때 `_meta`(최소 `_meta.ui` 와 옛 키 `"ui/resourceUri"`)를 옮긴다. 이름을 바꿔도 resourceUri 는 바꾸지 않는다. `_low.list_resources` · `list_resource_templates` · `read_resource` 처리기를 둔다 — `ui://` URI ↔ 백엔드 표(실패하면 직전 목록 유지), 도구와 같은 그룹 · 끈 앱 규칙으로 거르기, 숨긴 백엔드 URI 는 없는 URI 와 같은 오류, `resources/read` 는 사람별 위임 단발 세션, 크기 상한 · 감사 · 겹치는 URI 이름공간. 안내문 1번에 '패널 도구는 invoke_tool 이 아니라 직접 부른다' 를 더한다. `test_gateway.py` 에 `_meta.ui.resourceUri` 생존 시험을 더한다. | MCP 업로드 M-1 |
| HG-08 | heax 게이트웨이 PAT(이름 hwax-gateway-mcp)를 먼저 지우고 새로 찍는다. 발급이 한 번 실패하면 heax 앱 9개(리스크 · StepForge · DynaForge · 재료)가 챗에서 한꺼번에 빠지는데 update-all 은 ✓ 를 낸다. | 기준 `f8e7920` · `provision-config.sh:155`(같은 이름 PAT 를 먼저 지움) · `:248-258`(10-25 판 154-159행). `7c12cb7` 의 '발급이 실패하면 앞 config 의 토큰으로 잇기'는 반영됐지만 잇는 토큰이 방금 지운 것이다. HEAD `7c12cb7` 에서도 그대로다(HEAD 7c12cb7 기준 `mint_heax` 안에서 154-158행 지우기 → 159행 발급, 호출은 303-304행). | 새 PAT 를 받은 뒤에 옛것을 지운다. 시험 — 발급을 실패시키면 직전 토큰으로 config 가 써지고 heax 백엔드 수가 그대로다. | update-all 안전 U6-1 |


## 3. 낮음 · 선택


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HG-09 | 목록 자격이 없는 외부 연결을 60초마다 다시 붙이려 해 포털에 404 가 쌓인다. | `gateway.py:197`(REVIVE_INTERVAL_S=60) · `:1145`(`_conn_reconcile`). 10-25 에 stepforge-prod 'no-list-token' 으로 포털 로그 404 가 하루 약 1,400줄이었다. 10-27 재확인 — `/health` conn_platforms 4개(dynaforge-prod · fmea · matnexus · stepforge-prod)가 모두 ok 라 지금은 증상이 없다. | 404 부정 캐시를 5~10분으로 늘리거나 지수 백오프를 넣는다. 상태가 바뀔 때만 로그를 남긴다. `/health` 에 since 를 싣는다. | 10-25 피드백 GW-2 — 원래 중간, 10-27 연결 ok 로 낮춤 |
| HG-10 | `list_tool_apps` 가 개인 토큰이 없는 외부 연결도 ok 로 보여 준다. 에이전트가 쓸 수 있다고 믿고 불렀다가 거절당한다. | 10-25 dynaforge-prod 는 72 tools ok 인데 같은 사용자의 dynaforgeprod_whoami 는 'refused: no-connection'(64 ms)이었다. | 호출자 기준 needs_connect 칸과 `/tokens?tab=connect` 안내를 싣는다. | 10-25 피드백 GW-3 |
| HG-11 | 재기동할 때 열린 스트림이 응답 없이 끊겨 그 순간의 도구 호출이 실패한다. | 10-25 19:41:15 'ASGI callable returned without completing response' 98건이다. | down 전에 새 세션 수락을 멈추고, 진행 중인 CallTool 이 0 이 될 때까지 짧게 기다린다(graceful shutdown). | 10-25 피드백 GW-5 |
| HG-12 | `search_tools` 응답이 도구 설명 전문(각 수천 자)과 args 스키마를 그대로 싣는다. LLM 문맥을 낭비한다. | 10-25 `search_tools('시장 불량 원인 대책', 10)` 응답에 deliberate_* 설명 전문과 args 스키마가 실렸다. | 기본으로 한 줄 요약과 required 인자만 준다. | 10-25 피드백 PLM-23(게이트웨이 몫 — PLM 쪽 몫은 보류) |
| HG-13 | MCP 안내문의 유사도 수치가 옛 임베딩(e5) 기준이다(「무관한 문장끼리도 0.87~0.90」). BGE-M3 에서는 무관 1위가 최대 약 0.57 이다. | 기준 `095c93a` · `gateway.py:1212`. 10-27 재확인 — `7c12cb7` 의 `gateway.py:1410` 에 같은 문장이 있다. | 모델에 묶이지 않는 표현으로 바꾼다. | 10-17 수정 목록 G3 |


## 4. 질문 · 확인 요청


| # | 묻는 것 | 왜 · 근거 | 출처 |
|---|---|---|---|
| HG-14 | MCP 세션 클라이언트(`mcp.client.streamable_http`)가 안에서 만드는 클라이언트가 trust_env 를 따르는지 알려 달라. 따른다면 `trust_env=False` 를 검토해 달라. | `os.environ` 방식(NO_PROXY)이 MCP 세션 안의 클라이언트까지 덮는지 확인하지 못했다. 덮지 못하면 사내 백엔드 호출이 프록시를 타서 IP 제한 백엔드가 403 을 낸다(RA, 10-03). | 포털 9차 §7-3 |
| HG-15 | 금고 방식 리터럴(`gateway.py:159`, 10-03 기준)을 지웠는지 알려 달라. | 순서는 RA 의 홈 워크스페이스 보장(RA SSO §2) → 포털 정리 → 리터럴 제거다. 금고 등록자 9명을 어디로 옮길지는 우리 결정이 먼저다. 지금 줄 번호가 바뀌어 박스에서 확정하지 못했다. | 포털 8차 §6-5 · §6 |
| HG-17 | connect 반영이 최대 약 2분(정책 60초 + 패스 60초) 늦다. `POST /refresh` 로 충분한지, 포털이 mtime 변화를 보면 게이트웨이를 깨울지 의견을 달라. | 기준 `8e30ee5` · 게이트웨이 `gateway.py:1417-1420` · `:186` · 포털 `policy.py:350-366`. | FMEA 연결 1-9⑨ |
| HG-18 | `/health` 에 기동 때 보정한 NO_PROXY 결과를 실을 수 있는지 알려 달라. | 포털 update-all §6 의 'NO_PROXY 에 없는 내부 목적지' 표시는 거짓 경보다. 포털은 게이트웨이 목적지를 게이트웨이 `/health` 의 보정 결과로 판정하려 한다(보정 자리 `gateway.py:85-134`). 10-27 재확인 — 지금 `/health` 에 그 칸이 없다. | 10-25 피드백 PT-6 |


## 5. 결정 필요 (사용자)


| # | 정할 것 | 선택지 | 권고(원문) · 주의 | 출처 |
|---|---|---|---|---|
| HG-19 | '(시험)' 라벨 prod 앱(dynaforge-prod 72개 · stepforge-prod 158개)을 웹 챗 검색에서 어떻게 다룰지. 지금 OT-02 · 03 · 13 상위가 dynaforgeprod_* 이고 OT-14 1위가 stepforgeprod_find_plm_task 다. 챗 PAT 은 끔 목록에서 면제돼(`gateway.py:4857-4859`) 포털에서 앱을 꺼도 웹 챗에는 적용되지 않는다. | (가) 빼기 — X-HWAX-Via=chat 이면 `search_tools` 에서 두 앱을 뺀다(에이전트 CHAT_EXCLUDE_APPS 와 짝). 원문 대안은 연결 토큰을 등록한 사람에게만 싣는 것이다. (나) 라벨 바로잡기 — '(시험)' 라벨은 박스 권한표(backend/config 의 *.local.yaml, 62-89행 중 label 66 · 78행 · 안내 문구 85행)에서 온다. 박스에서 고치면 게이트웨이 코드 변경은 없다. | 원문 권고는 (가)다. 주의 — 두 앱은 10-23 가동 · 10-27 코어 연결로 실제 운영 데이터를 가진 앱이 됐다. '(시험)' 라벨이 낡았을 수 있다. (나)를 고르면 '시험' 낱말 적중 잡음이 사라지고, 정본과 겹치는 결과는 HG-01 의 정본 하나만 올리기로 줄인다. | 온톨로지 시험 C-4(게이트웨이 몫) |
| HG-20 | 게이트웨이로 나가는 응답의 개인정보 가림 범위. | (가) 기본으로 가린다(사람 이름 · IMEI 꼴 숫자 · 일련번호 꼴 · 계정 ID · 작성자 이름). 원문은 필요한 화면에만 준다. (나) 사람 이름만 가린다. (다) 그대로 둔다. | 10-25 권고는 (가)다. 걸리는 출력은 SignalForge author_name · FailureTrace pd_defect 의 검출자 · 작업자 이름 · PLM 응답이다. PLM 쪽 몫은 PLM 보류에 묶여 있다. | 10-25 피드백 D5 · PLM-11(게이트웨이 몫) · SF-10 · 온톨로지 시험 N-18 |


## 6. 다른 플랫폼과 맞물린 것


- **'(시험)' 라벨 prod 앱(C-4)** — 이 플랫폼 몫은 `search_tools` 처리(HG-19)다. 에이전트 묶음 후보에서 빼기는 HWAXAgentServer 요청서(03-HWAXAgentServer.md HA-23), 박스 권한표 label · 오버레이와 결정 기록은 우리 몫 문서(90-OURS-box-todo.md OB-04)다. KooRemapper · StepForge 는 할 일이 없다(04 · 05 의 6절). 출처 온톨로지 시험 C-4.


- **검색 순위(HG-01)** — 이 플랫폼 몫은 동의어 · 감점 · 정본 하나만이다. 허브 도구 설명 첫 줄의 설치별 tagline 은 Datahub-platform 요청서(12-Datahub-platform.md DP-03), 앱 설명 문안(hwax-batch CSV → 게이트웨이의 hwax-batch 블록, 손으로 고치지 않는다)은 우리 몫 문서(90-OURS-box-todo.md OB-33)다. 에이전트 쪽 늘 묶기 · 프롬프트 규칙은 03-HWAXAgentServer.md HA-02 · HA-03 이다. 품질 질의에 걸려야 할 VOC · PLM 검색 쪽은 바꿀 것이 없다(08-SignalForge.md · 15-plm-search-agent.md 의 6절). 출처 온톨로지 시험 C-5 · C-10 · C-11 · C-2 · C-3.


- **영역 분류(HG-05)** — 이 플랫폼 몫은 `tool_areas.json` 이다. 영역 고르기 화면(`ToolCatalogBlock.tsx:59` · `:74` · `StartPicker.tsx:75`)은 이 파일을 그대로 보여 포털 쪽 할 일은 없다(01-HWAXPortal.md 6절). 허브 · FMEA · MatNexus · ODB · ARP · SimFlow · MX 백서 쪽도 할 일이 없다(12 · 13 · 14 · 09 의 6절에 알렸다). 출처 온톨로지 시험 C-9 · 10-25 피드백 GW-4 · FMEA 연결 1-9⑦.


- **단발 세션 셋(HG-02 · HG-03 · HG-04)** — 한 번에 보내고 시험 한 벌로 본다. HG-02 의 포털 시험(`backend/tests/test_update_all_gateway_expectations.py:636` `ODB_CFG` · `:706`)에 헤더 꼴 config 를 더하는 것은 01-HWAXPortal.md HP-28 이다. ODB 가 쿼리와 헤더가 같이 오면 헤더를 먼저 보는지, 반영 뒤 접속 기록에 본인 이메일이 찍히는지는 14-Partner-apps.md PA-09 다. SimFlow 위임 발급의 네 가지 질문은 14-Partner-apps.md PA-13 이다. 출처 파트너 타일 T4 · T4-2 · 운영쪽-1 · MCP 업로드 T1 · U1.


- **SimFlow 챗 업로드(HG-04)** — HG-04 가 먼저다. 포털 업로드 목적지 SimFlow(aud `simflow`, 500MB 사전 차단)와 nginx `/simflow/` 큰 업로드 · 긴 스트리밍은 01-HWAXPortal.md HP-15 · HP-13 이다. SimFlow 업로드 상한(500MB 와 600MB 가 다르다)과 확장자 목록 확인은 14-Partner-apps.md PA-12 다. 출처 MCP 업로드 U2 · U2-1 · 파트너 타일 T3.


- **REST 다리의 사이트별 aud** — 게이트웨이 규칙은 그대로 둔다. 발급 청중을 맞추는 쪽은 01-HWAXPortal.md HP-15(챗 PAT 에 `simflow`)와 07-hwax-risk.md RK-02(PAT 버튼에 `step-forge`)다. 출처 MCP 업로드 U2 · 리스크 자격 R2.


- **패널(HG-07)** — 이 플랫폼 몫은 1단계 중계다. 에이전트의 `ui_resource` SSE 와 패널 도구 숨기기(M-2 가 들어오면 푼다)는 03-HWAXAgentServer.md HA-20 · HA-05, 포털 챗 호스트(샌드박스 iframe · 브리지 보안 규칙)는 01-HWAXPortal.md HP-42 다. 패널 전용 업로드 도구의 표지와 패널이 부르는 도구 목록은 14-Partner-apps.md PA-07 · PA-14 다. 출처 MCP 업로드 M-0 · M-1 · M-2.


- **heax PAT 순서(HG-08)** — 이 플랫폼 몫은 발급 뒤 지우기다. update-all 재검증이 키가 아니라 heax 백엔드 수를 보게 하는 것과 repair_mcp 앞의 심의 확인은 01-HWAXPortal.md HP-09 · HP-08 이다. 박스의 `provision.env` `HEAX_MCP_TOKEN` 고정은 HG-08 이 들어오면 우리가 걷는다(90-OURS-box-todo.md OB-76). 출처 update-all 안전 U6-1 · U6-3 · U5-2.


- **재기동 끊김(HG-11)** — 포털 update-sites 의 재기동 순서를 graceful shutdown 에 맞추는 것은 01-HWAXPortal.md HP-25 다. 출처 10-25 피드백 GW-5.


- **오류 봉투(HG-06)** — 이 플랫폼 몫은 감사의 ok 판정이다. 빈 출력 대신 봉투를 내는 것은 04-KooRemapper-DynaForge.md KR-08(find_reports)이다. 허브의 오류 봉투 꼴은 그대로 둔다(12-Datahub-platform.md 6절). SignalForge 의 'numpy 없음' 응답은 08-SignalForge.md SG-01 로 사라진다. 출처 온톨로지 시험 N-13 · N-5.


- **개인정보 가림(HG-20)** — 이 플랫폼 몫은 게이트웨이로 나가는 응답의 공통 가림이다. 원천에서 가리는 것은 08-SignalForge.md SG-11(작성자 이름) · 12-Datahub-platform.md DP-08(검출자 · 작업자 이름) · 15-plm-search-agent.md PL-03 이다. 같은 결정이 08-SignalForge.md SG-18 · 15-plm-search-agent.md PL-10 · 03-HWAXAgentServer.md HA-25 에도 있고, 결정 기록은 90-OURS-box-todo.md OB-07 이다. 출처 10-25 피드백 D5 · SF-10 · 온톨로지 시험 N-18.


- **RA 금고 리터럴(HG-15)** — RA 의 홈 워크스페이스 보장은 11-ReportArchive.md RP-01 · RP-15, 위임 경로에서 `X-Workspace-Slug` 빼기는 01-HWAXPortal.md HP-33 이다. 금고 등록자 9명을 옮길지는 사용자 결정이다(90-OURS-box-todo.md OB-23). 출처 포털 8차 §6 · RA SSO §2 · 포털 9차 §6.


- **MX 백서 `wiki_*` 노출** — 위키가 꺼져 있는데 도구 14개가 보이는 것은 MXWhitePaper 요청서(09-MXWhitePaper.md MW-01)에서 등록을 조건부로 고친다. 게이트웨이에 따로 청할 코드는 없다. 출처 10-25 피드백 MX-2.


- **KooRemapper 위임 표준 계약** — KooRemapper 가 `POST /api/v1/auth/sso/verify` 와 `X-Heax-Client: gateway` 를 받으면(04-KooRemapper-DynaForge.md KR-18), 게이트웨이 설정의 손 위임 항목을 표준 스크립트 꼴로 옮긴다(우리 몫, 90-OURS-box-todo.md OB-83). 출처 KooRemapper 실행기 K8.


## 7. 다시 볼 시험


| 시험 | 언제 | 볼 것 |
|---|---|---|
| OT-01~16 전부 | HG-01 과 에이전트 HA-01~04 · C-4 결정을 반영한 뒤 | `search_tools` 상위 8과 에이전트 `/health` tool_cut 을 다시 재고, 온톨로지 시험 5절대로 웹 챗 16개를 돌린다. |
| OT-02 · 03 · 13 · 14 | HG-19 결정 반영 뒤 | 결정대로 prod 앱이 빠지거나 라벨이 바로잡혀 '시험' 낱말 적중이 사라지고, 정답 도구가 상위에 온다. |
| OT-12 · OT-13 | HG-06 뒤 | 오류 봉투가 감사에 ok=false 로 적힌다. 그 전까지 점검기는 120자 이하 응답을 '작은 응답(오류 의심)' 으로 따로 센다. |
| HG-02 확인 | 반영 뒤 재프로비저닝 | `gateway_config.json` 의 odb-hub `url` 에 `token=` 이 없고 `headers.Authorization` 이 있다(값은 찍지 않고 모양만 본다). `/health` 의 odb-hub 가 정상이고, 사람별 위임 감사 줄이 as-user-pat · 본인 이메일이다. |
| HG-07 확인 | 반영 뒤 | Claude Desktop 을 `/mcp-gw/mcp` 로 붙여 `open_workflow_panel` 을 부르면 패널이 뜨고 `ui/initialize` 가 끝난다. 패널의 `tools/call` 이 그 사람 명의(as-user-pat)로 SimFlow 에 닿고 `ui/open-link` 가 된다. |
| HG-08 확인 | 반영 뒤 | 발급을 실패시키면 직전 토큰으로 config 가 써지고 heax 백엔드 수가 그대로다. |
| 10-25 피드백 M-16 | HG-10 반영 뒤 | 개인 토큰이 없는 사용자에게 `list_tool_apps` 가 needs_connect 를 보이고, 등록한 사용자의 dynaforgeprod_whoami 는 본인 이메일로 답한다. |


## 8. 이 문서에서 뺀 것


- 게이트웨이 기동 env 의 IDENTITY_FWD 에 plm-defect 더하기 — PLM 보류(사용자 「일단 PLM 관련은 그대로 두자」, 10-25 D3)라 넣지 않았다. 별도 PLM 신원 요청서도 보내지 않는다.


- 노출 스키마의 plm_defect_search enrich 기본값 — PLM 보류(10-25 D4)라 넣지 않았다.


- PLM 응답의 개인정보 가림 중 PLM 쪽 몫 — PLM 보류다. 게이트웨이 공통 가림 범위만 HG-20 에 남겼다.


- ODB 토큰이 든 URL 의 로그 가림 — httpx 요청 줄 끄기와 쿼리 비밀 가림은 `5e867e9` 로 반영됐다. 남은 헤더 전환은 HG-02 다.


- heax PAT 발급 실패 때 앞 config 의 토큰으로 잇기 — `7c12cb7` 로 반영됐다. 남은 순서 문제는 HG-08 이다.


- FMEA 연결 문서의 게이트웨이 표(GW2 · GW3 · GW7 · GW9~13 · GW18 · GW19)와 신원 없는 호출 거절 — `974e7ed` 등으로 반영됐다.


- StepForge prod · DynaForge prod 연결 토큰 등록 — 사용자가 등록했다. 10-27 재확인으로 conn_platforms 4개가 모두 ok 다.


- 10-25 영역 분류 재측정 — 10-27 에 다시 쟀다(61.8%). HG-05 에 합쳤다.


- 선언 플랫폼 도구의 영역 질문(FMEA 연결 1-9⑦) — 같은 `tool_areas.json` 건이라 HG-05 에 합쳤다. 그래서 HG-16 번호는 비어 있다.


- 토큰 교체 — 요청하지 않는다(사용자 결정).


- stcx SmartTwinMCP 게이트웨이 등록 — 박스 `provision.env` 에 주소를 넣고 update-collab 로 반영하는 우리 몫이다(`gateway_config.json` 손 편집 금지). 우리 몫 문서(90-OURS-box-todo.md OB-34)로 옮겼다.


- MX 백서 사람별 위임(per_user_sso 에 mx-white-paper) — 박스 설정이고 사용자 결정 D7 대기다. 우리 몫 문서(90-OURS-box-todo.md OB-08)와 MXWhitePaper 요청서(09-MXWhitePaper.md MW-10)에 있다.


- 시험 스크립트가 게이트웨이 설정을 grep 할 때의 값 가림 — 우리 스크립트 몫이다(90-OURS-box-todo.md OB-40).


- 게이트웨이가 부모 환경만 물려받아 NO_PROXY 를 못 받는 문제(`services.py` Popen) — 포털 기동 경로 몫이라 01-HWAXPortal.md HP-11 에 있다.


- ARP 서버 간 `/mcp` 서비스 토큰 — 10-27 박스 실측으로 게이트웨이의 arp 백엔드가 토큰을 싣고 정상이다. 상대 팀 확인만 남아 14-Partner-apps.md PA-10 에 있다.
