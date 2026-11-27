# MCP 를 쓰는 쪽의 고르기 · 묶기 · 부르기 조사 (2026-11-27)

읽기만 했다. 리포 · 설정 · 서비스는 건드리지 않았고 쓰기 도구는 부르지 않았다. 읽은 것은 소스, 문서, dev 에서 인증 없이 열리는 GET 창구(게이트웨이 `/health` · `/tools-map`, 에이전트 서버 `/health`), 에이전트 서버 로그, 게이트웨이 감사 기록(유형과 수만)이다.

표기는 둘이다. **[확인]** 은 코드 · 실측 · 문서 수치로 본 것이다. **[짐작]** 은 그 수치에서 어림한 것이고 cae00 에서 재야 한다.

---

## 0. 한눈에

- 쓰는 쪽은 여섯이다. 웹 챗, 심의 좌석(띵킹 포함), 분석 루틴, 절차, 위임(토큰 절감 2판), 개인 Claude(워크플로 포함)다. 자동 파이프라인은 계약 도구 다섯만 부른다.
- 목적 → 도구를 정하는 규칙은 쓰는 쪽마다 따로 있다. 목적을 고르는 규칙이 다섯 벌, 읽기 · 쓰기 판정이 일곱 벌, 목적(영역) 분류표가 넷이다 **[확인]**.
- 같은 목적인데 보는 도구 무리가 다르다. 코어 객체 조회는 웹 챗만 허브 도구 16개를 늘 묶는다. 심의 좌석은 허브 도구를 부르지 못한다(이름 접두 규칙에 안 걸린다) **[확인]**.
- 심의 좌석의 읽기 판정(이름 접두)과 게이트웨이의 읽기 판정(panel_read)은 dev 에서 겹치는 것이 84개뿐이다. 접두만 통과하는 것이 154개, 게이트웨이만 읽기로 보는 것이 160개다 **[확인]**.
- cae00 은 도구가 1,947~1,984개다 **[확인 — 문서]**. 웹 챗은 도구 정의 예산을 "창의 45%" 로 잡는다. 그래서 묶이는 수가 도구 수가 아니라 창 크기를 따라간다. Qwen 262,144 창이면 약 210~225개(11%), Claude 턴(창 1,000,000)이면 약 1,000개를 한 호출에 싣는다 **[확인 — 식 · 짐작 — 개수]**.
- 위임은 그 사람의 읽기 도구 전부를 예산 없이 묶는다. cae00 규모면 호출마다 수십만 토큰이다 **[짐작]**.
- 개인 Claude 는 보기(전체 · 묶음 · 가벼운)가 이미 있지만 쓰이지 않는다. dev 기동 뒤 tools/list 는 전체 6 · 묶음 0 · 가벼운 0 이다 **[확인]**. cae00 은 세션마다 도구 이름 목록만으로 시작 문맥이 36.9k~38.8k 토큰 뛴다 **[확인 — 문서]**.
- 10-29 · 10-30 QA 의 도구 실패 넷(엉뚱한 앱 · LLM 폴링 · 묻지 않은 잡 · 다른 허브 id)은 코드로 모두 고쳐졌다. 남은 것은 cae00 재시험, 박스 손잡이 켜기, 그리고 11-10 시험에서 새로 나온 WD-02(도구가 안 묶인 턴에 호출을 지어냄) · WD-10(대상 고정) · A-2 다.
- dev 는 웹 챗 정본이 Claude Opus 5.5 인데 `.env` 가 16K Qwen 시절 값(도구 40개 · 설명 120자 · 예산 12,000)으로 남아 있다. dev 에서 본 Claude 챗 도구 선택은 실제보다 나쁘게 보인다 **[확인 — 설정 · 짐작 — 품질 영향]**.

---

## 1. 규모와 도구 하나의 값

| 항목 | 값 | 근거 |
|---|---|---|
| dev 게이트웨이 | 도구 796(백엔드 765 · 게이트웨이 자체 31) · 백엔드 18 · 영역 미분류 0 · 접두가 붙은 이름 25 | `/tools-map` 실측 **[확인]** |
| dev 읽기 · 쓰기 표 | write 198 · routine_read 437 · panel_read 244 | 같은 곳 **[확인]** |
| cae00 게이트웨이 | 1,947(백엔드 34, 11-21) · 1,970(11-24) · 1,972 · 1,984 | `docs/leftovers-1121/context-notes.md:466` · `docs/token-saving/context-notes.md:121` · `docs/request-1125/request.md:2997` · `docs/request-1125/context-notes.md:374` **[확인]** |
| cae00 표지 | 1,972개 중 83.5% 가 readOnlyHint 없음 | `docs/request-1125/request.md:2997` **[확인]** |
| cae00 같은 도구 사본 | 데이터허브 5종의 같은 도구 116개(합 464개, 23.5%) | `docs/request-1125/request.md:2995`(G-4) **[확인]** |
| 웹 챗 절단 실측 | 10-27 1,613 → 225 · 10-30 1,379 → 209(예산 88,473 토큰) | `docs/request-1027/01-HWAXPortal.md:54` · `docs/request-1030/platforms/90-OURS.md:70` **[확인]** |
| 웹 챗 프롬프트 | 요청 평균 108,275 토큰 중 약 80% 가 도구 설명 | `docs/request_261029.md:209`(W-2) **[확인]** |
| 도구 하나의 정의 | 묶인 도구 기준 약 390~420 토큰(88,473 ÷ 225 · ÷ 209) | 위 두 줄에서 셈 **[짐작]** |
| cae00 전체를 다 실으면 | 1,970 × 약 400 ≈ 0.8M 토큰 | 위 어림 **[짐작]** |

에이전트 서버의 셈법은 `(이름 + 설명 + 인자 스키마 글자) ÷ 3 + 8` 이다(`HWAXAgentServer/app.py:3242` `_tool_schema_cost`, `deliberation.py:5034` `_tool_cost`). 보수적으로 크게 잡는 셈이다.

---

## 2. 쓰는 쪽별 지금 길

### 2.1 웹 챗(에이전트 서버 `app.py`)

**도구 목록 받기.** 턴마다 게이트웨이에서 그 사람(그룹 · PAT)의 도구를 받는다(`app.py:5045` `_get_tools_retry`, `:5088` `_agent_for`). 30분 캐시이고(`AGENT_CACHE_TTL_S`, `:133`), 무캡 길은 캐시를 타도 턴마다 원본에서 다시 고른다(HA-01, `:5139`) **[확인]**.

**고르기(`_select_tools`, `app.py:3390`).** 차례는 다음과 같다 **[확인]**.
1. 콕 집은 것(`first` — 사용자 핀 · 운영자 입구 도구 `key_tools` · `_OPERATOR_GATEWAY_TOOLS` `:3100`).
2. 사용자 핀(`pinned_tools` 최대 12 · `pinned_apps` 최대 3 — 앱은 그 앱 도구 전부로 펼침, `:7464-7480`).
3. 지목한 전문가의 분야 도구(`prefer` — 심의 좌석과 같은 `_seat_tool_prefer`, 최대 `CHAT_PERSONA_PREFER_N`=12, `:7508-7515`).
4. 어휘(IDF) + 의미(AIDataHub 임베딩) RRF 융합 순위(`_relevance_order`, `:3357`).
5. 상시 핵심 `_TOOL_PRIORITY` 37개(`:3076`)와 온톨로지 고정 몫 `_ONTO_CORE` 16개(`:3260`, 정본은 포털 `backend/config/core_vocab.json` 의 `ontology`).

**예산.** 두 길이 있다 **[확인]**.
- 캡 길(`TOOL_MAX>0`, 코드 기본 200) — 관련도 상위 N개 + `TOOL_SCHEMA_BUDGET`(기본 40,000) + 핵심 예약(`:3436-3460`).
- 무캡 길(`TOOL_MAX=0`, cae00) — 예산은 `CHAT_TOOL_SCHEMA_BUDGET` 이 있으면 그 값, 없으면 `max(4000, 창 × 0.45)`(`:3418`). 넘치면 관련도 순으로 세우고 뒤에서 뺀다. 안내대 셋(search_tools · invoke_tool · list_tool_apps)과 온톨로지 고정 몫은 늘 앞에 남긴다(`:3426-3432`).

**운영자 · 전문가 · 팀.** HE팀 운영자(19명, 포털 `infra/personas/he-team.json`)를 고르면 그 앱이 앱 핀으로 펼쳐지고 상시 예약이 안내대 넷(`_GUIDE_TOOLS`, `:3095`)으로 준다. 보조 운영자는 입구 도구만 빌려준다(`:7458-7468`). 도메인 전문가는 `prefer` 로만 순서를 바꾼다. 전문가 팀(주 1 + 보조 4)은 같은 길이다 **[확인]**.

**모델마다 다른가.** 고르는 규칙은 같다. 다른 것은 창이다. 챗 턴의 창은 문맥 변수로 덮는다(`app.py:7260-7268`) **[확인]**.
- stcx Qwen 턴 — `min(챗 창, VLLM 창) − 출력 몫`.
- Claude 턴 — `CLAUDE_CHAT_CONTEXT(1,000,000) − min(max_tokens 64,000, 창의 절반)` = 936,000. 무캡 길이면 도구 예산이 약 421,000 토큰이 된다.
- 에이전트 캐시 열쇠에 Claude 칸이 따로 든다(`:5121-5129`).
- Claude 턴은 Anthropic 공식 SDK 길(langchain-anthropic `ChatAnthropic`)이고 `tool_choice` any · tool 을 auto 로 바꾼다(`chat_claude.py:156-158`). Anthropic 의 도구 찾기(tool search tool · defer_loading)는 쓰지 않는다.

**프롬프트 규칙.** 시스템 글에 도구 이름이 박혀 있다(`app.py:161-207` — search_tools · invoke_tool, get_guide · search_reports · get_reports_digest, list_materials 우선 등). 코어 규칙 ①~⑦은 어휘표에서 짓는다(`:209`, `:312` `_core_rules_text`) **[확인]**.

**부르기 관문.** 도구를 부를 때 네 겹이 선다 **[확인]**.
- 확인 카드 — 운영자 정의의 writes · confirm(dev 231 · 145) + 잡 바닥 목록 26(`app.py:4146` `_CONFIRM_JOB_TOOLS`, `:4213` `_confirm_lists`, `:4323` `_confirm_class`).
- 상태 기다림 — HA-28, `status_wait.py:119` 이름 목록 ∩ routine_read.
- 다른 허브 id 막이 — HA-30, `:2246`.
- 유령 id 막이 — `:2053`.

**결과 크기.** `TOOL_RESULT_MAX`(기본 200,000자 · cae00 10-29 60,000 · dev 6,000)로 자르고 표지를 단다(`app.py:1742` · `:1775`). 이력 밖 도구 결과 몫을 따로 뗀다(`:5287`). 허브 목록은 접는다(HA-34) **[확인]**.

**dev 설정.** `HWAXAgentServer/.env` 는 `TOOL_MAX=40` · `TOOL_DESC_MAX=120` · `TOOL_SCHEMA_BUDGET=12000` · `TOOL_RESULT_MAX=6000` 이다. 주석은 "dev(qwen 16K) 전용 축소" 다. 그런데 같은 파일이 `CLAUDE_CHAT_FOR=all` 이고, `/health` 도 `tool_max 40 · tool_desc_max 120 · claude_chat.ctx_tokens 1,000,000` 이다 **[확인]**. dev 의 Claude 챗은 도구 40개와 120자에서 잘린 설명(인자 설명까지 — `_slim_tool`, `:2967`)으로 고른다. `_slim_tool` 주석에도 120자 절단이 인자 유효값을 잘라 값을 지어낸 사례가 있다 **[짐작 — dev QA 가 실제보다 나쁘게 나온다]**.

### 2.2 심의 좌석 · 띵킹(에이전트 서버 `deliberation.py` · `thinking.py`)

**후보(pool).** 아래 조립식으로 짓는다(`deliberation.py:6762-6800`) **[확인]**.
- 받아들이는 길은 넷이다.
  - 그 사람의 도구 가운데 이름 접두 허용 `_FREE_ALLOW`(40개 접두 · 이름, `:4551`)에 걸리는 것. 원래 이름으로 판정한다(F0).
  - 선언 백엔드의 게이트웨이 확인 읽기(panel_read — HA-36).
  - 리스크 앱 조건부 읽기(`_RISK_READ_TOOLS`, `:980`).
  - 리스크 의장 유지 목록(`_RISK_KEEP_TOOLS`, `:1144`).
- 빼는 것은 `_FREE_DENY`(`:4572`), 리스크 심사의 RA 보고서 읽기 · 과제 인사이트 · 절차 머리(D-18), 웹 소스 토글이다.
- 사람이 앱을 고르면(`delib_apps`) 그 앱 + `agent_search` + 물성 목록 `_MATERIAL_TOOLS`(`:4583`)로 좁힌다.

**좌석별 선정(`_tools_for_seat`, `:5184`).** 순위는 `_seat_tool_rank`(`:5116`)로 매긴다 **[확인]**.
- 도구 영역(게이트웨이 `tool_areas.json` 을 `/tools-map` 으로 받은 것)과 좌석 역할 낱말을 영역 낱말표 `_AREA_HINT`(`:5076`, 10영역 — research · expert · data · system 줄 없음)에 대 본다.
- 입구 도구(search · list · find · guide · describe)에 가산점을 준다.
- 예산은 `min(DELIB_FREE_TOOL_TOKENS 40,000, 창 × 0.8 × 0.45 − 4,000)` 이다(`:4880`).

**허브 도구.** 정본 허브의 object_resolve · objects_list · graph_neighbors 는 접두에 안 걸려 좌석이 부르지 못한다. 좌석에 열지는 미결이다(`docs/ontology-first/context-notes.md:17-43` — "§5.4 가 한 번에 정한다") **[확인]**.

**띵킹.** 띵킹 좌석에는 도구를 묶지 않는다. recommend_agents · agent_search · get_agent_session 만 코드가 부른다(`thinking.py:150` · `:588`) **[확인]**.

### 2.3 분석 루틴 · 절차 · 위임

**루틴(포털 `backend/app/procedures/routines.py`, 실행기 에이전트 서버 `routine.py`).** 목적 → 도구는 사람이 짠다 — 단계마다 백엔드와 도구를 고른다. 묶는 것은 `(적은 도구, 안 적었으면 그 백엔드 도구 전부) ∩ 내 목록 ∩ 게이트웨이 routine_read − 포털 is_write_tool`(`routines.py:378` `allowed_tools`, `:35` `is_write_tool`)이다. 실행기는 그 목록만 작은 ReAct 에 묶는다(`routine.py:978` `_bind`, `:1412` `_gather`). 안내대는 묶지 않고 스키마 예산도 없다 **[확인]**. StepForge 단계에 도구를 안 적으면 dev 에서 읽기 157개가 한꺼번에 묶인다(약 60k 토큰) **[짐작]**.

**절차(포털 `backend/app/procedures/`).** 한 번 한 도구 연쇄를 그대로 재생한다. 목적 → 도구 선택은 없다. 쓰기 관문은 포털의 손 목록이다(`models.py:26` `MUST_GATE` 31개 · `WARN_PREFIX` · `WARN_EXACT` · `GW_DENY_PREFIX` · `GW_DENY_SUFFIX`) **[확인]**.

**위임(에이전트 서버 `offload.py`, 기본 꺼짐).** 울타리는 그 사람의 도구 ∩ routine_read − 이 서버 도구 − 게이트웨이 자체 도구이고, `apps`(최대 10)를 주면 그 앱만이다(`offload.py:251` `read_fence`). 그 전부를 예산 · 관련도 없이 `create_react_agent` 에 묶는다(`:379` `_react`, `:426`). 단계 상한은 기본 12 · 최대 30 이다(`:70`) **[확인]**.
- dev 비율(437/765 = 57%)로 cae00 을 어림하면 읽기 도구가 약 1,100개, 정의만 호출마다 약 0.45M 토큰이다 **[짐작]**.
- 262,144 창이면 400 이 난다. 1M 창이면 한 호출이 그만큼 싣는다.
- 11-24 측정의 "위임 23건 서버 입력 22.45M(건당 0.98M)"(`docs/request-1125/request.md:3007`, A-1 — "단계마다 무엇을 다시 싣나 확인해 달라")과 크기가 맞는다 **[짐작 — 확인 필요]**.

### 2.4 개인 Claude · 리포 워크플로

**연결.** 게이트웨이 `/mcp` 한 곳에 붙는다(포털 경유 `<포털>/mcp-gw/mcp`). 토큰 페이지 배치가 Claude Code · Desktop 등록에 `X-HWAX-View: portal` 머리를 단다(`frontend/src/lib/setupBat.ts:80-83` · `:483` · `:851`). 결과 손잡이 `X-HWAX-Result: ref` 는 선택 칸이고 기본 꺼짐이다(`:86-89`). 리포 `.mcp.json` 은 늘 `X-HWAX-View: full` 이다(워크플로가 이 등록으로 돈다) **[확인]**.

**보기(게이트웨이 `gateway.py`).** 보기는 tools/list 에만 걸린다. 검색 · 부르기 · 권한은 그대로다(`:322-331`, `:10127` `_listed_tools`) **[확인]**.
- 전체 — 내 권한 안의 도구 전부(끈 앱 · 시험 사본만 빠짐, `:10110` `_visible_tools`).
- 묶음 `bundle:<영역>,…` — 고른 영역(`tool_areas.json`)의 도구 + 정본 읽기 + 게이트웨이 자체 도구 전부. 형제 사본은 뺀다.
- 가벼운 — search_tools · invoke_tool 둘(`:10124`).
- 포털 설정은 사람마다 하나다(`users.hub_view`, `backend/app/access/hub_view.py`, 화면 `frontend/src/components/HubViewPanel.tsx`). 목적이나 과제마다 고르는 길은 없다. 앱별 서버(`/mcp/<app>`)는 하지 않기로 했다(도구 이름이 `mcp__hwax-<앱>__X` 로 바뀌어 허용 규칙이 깨진다, `docs/mcp-app-toggle/PLAN.md:35-36`).
- 허브에 보일 앱 끄기(`X-HWAX-Muted-Apps`)는 목록 · 검색에서 뺀다.

**지금 쓰임.** dev 기동 뒤 `tools_list_by_view` 는 전체 6 · 묶음 0 · 가벼운 0 이다(게이트웨이 `/health`) **[확인]**. cae00 은 11-24 비교 64회에서 "PC 연결이 머리를 보내지 않아 쓰인 적이 없다" 고 적었다(`docs/request-1125/request.md:2963`) **[확인 — 문서]**.
- 같은 문서 기준 1,9xx 개 이름이 세션 시작 문맥을 36.9k~38.8k 토큰 올린다(`:2959`).
- ToolSearch 로 스키마를 불러온 도구가 315개, 찾기 호출이 도구 호출의 22.6% 다(G-2, `:2991`).
- 2만 자 넘는 결과 35건이 결과 글자의 44% 다(`:2961`).

**워크플로(`infra/pipeline/*.js`).** 좌석 에이전트는 Claude Code 의 ToolSearch(지연 로드)로 도구를 찾는다(`docs/token-saving/context-notes.md:82` — "빼면 MCP 도구를 처음부터 다 싣는다"). 프롬프트에 "목록에 없으면 invoke_tool" 안내(BY_NAME)가 박혀 있다(`hwax-deliberate.js:792` 등) **[확인]**.

### 2.5 자동 파이프라인(참고)

포털 `backend/app/autopipe/` 는 앱 계약 다섯(auto_profiles · auto_check · auto_submit · auto_status · auto_result)만 서비스 토큰으로 부른다. LLM 은 서술만 한다. 목적 → 도구 고르기가 없다 **[확인 — CLAUDE.md · docs/auto-pipeline]**.

---

## 3. 규칙이 몇 벌인가

### 3.1 목적 → 도구(고르는 규칙) — 다섯 벌

| # | 쓰는 쪽 | 규칙 | 자리 |
|---|---|---|---|
| 1 | 웹 챗 | 어휘 + 의미 RRF + 핀 · 운영자 입구 · 전문가 prefer + 상시 핵심 37 + 온톨로지 16 + 창 비율 예산 | `app.py:3357-3475` |
| 2 | 심의 좌석 | 이름 접두 후보 → `_AREA_HINT` × 역할 낱말 순위 → 좌석 예산(대체 좌석은 `_trim_free_tools` 질의 낱말) | `deliberation.py:4551` · `:5043` · `:5116` · `:5184` |
| 3 | 루틴 | 사람이 고른 백엔드 · 도구 ∩ routine_read | 포털 `routines.py:378` |
| 4 | 위임 | 그 사람 읽기 전부(또는 앱 ≤10) — 고르기 없음 | `offload.py:251` |
| 5 | 개인 Claude | 게이트웨이 보기(영역) + Claude Code ToolSearch + 게이트웨이 search_tools(`search_tuning.json` · 어휘표 동의어 · onto 손잡이) | `gateway.py:10127` · `:3560` |

웹 챗의 안전망과 개인 Claude 의 찾기가 같은 게이트웨이 `search_tools` 를 쓴다. 이것 하나만 쓰는 쪽 공통이다.

### 3.2 읽기 · 쓰기 판정 — 일곱 벌

| # | 판정 | 쓰는 곳 | 자리 |
|---|---|---|---|
| 1 | 게이트웨이 `_tool_is_write`(표지 → override → 이름 동사) | `/tools-map write` · 검색 감점 | `gateway.py:4080` · `:3602` |
| 2 | 게이트웨이 `_routine_read`(닫기 → 표지 → override → 읽기 목록 → 이름 낱말) | 루틴 · 위임 · 읽기 전용 PAT · 상태 기다림 | `gateway.py:9733` |
| 3 | 게이트웨이 `_panel_read`(2 에서 이름 낱말 뺌) | 패널 · 좌석의 선언 백엔드 | `gateway.py:9759` |
| 4 | 좌석 `_FREE_ALLOW` 이름 접두 | 심의 좌석 | `deliberation.py:4551` |
| 5 | 챗 확인 카드(운영자 writes · confirm + 잡 바닥 26) | 웹 챗 | `app.py:4146` · `:4213` |
| 6 | 포털 `MUST_GATE` · WARN · GW_DENY | 절차 · 루틴 | 포털 `procedures/models.py:26-69` |
| 7 | 게이트웨이 파괴 · 제어 막이 | invoke_tool 등 | 게이트웨이 |

서로 어긋난다(dev 실측) **[확인]**.
- 게이트웨이 안에서도 6개가 write 이면서 routine_read · panel_read 다(get_record · get_record_sections · describe_record_schema · get_sync_settings · risk_propose_board_transform · run_saved_search). 이름 동사(record · sync · propose · run) 판정과 읽기 목록이 부딪친다.
- 백엔드 도구 136개는 write 도 read 도 아니다(모름).
- 좌석 접두 후보 238 과 panel_read 244 가 겹치는 것은 84개다. 접두만 통과하는 154개는 게이트웨이가 읽기로 확인하지 않은 것이다(예 agent_search · catalog_* · compare_*). panel_read 에만 있는 160개는 좌석이 못 쓰는 확인된 읽기다(대부분 StepForge).

### 3.3 목적(영역) 분류표 — 넷

| 표 | 자리 | 쓰는 곳 |
|---|---|---|
| `tool_areas.json`(영역 14 · 앱 기본값 · 이름 패턴 · 도구 지정) | 게이트웨이 | `/tools-map areas` · list_tool_apps by=area · 묶음 보기 · 좌석 순위 · 챗 prefer |
| `_AREA_HINT`(영역 10의 낱말) | `deliberation.py:5076` | 좌석 · 챗 prefer(시험이 영역 키를 맞댐) |
| 코어 어휘표 `core_vocab.json`(정본 · 규칙 낱말 · 검색 동의어 · 앱 역할 · personas · ontology) | 포털 `backend/config` | 챗 규칙 · 고정 몫, 게이트웨이 검색 · 소개 줄 · 묶음 보기의 정본 읽기 |
| `he-team.json`(운영자 19 — 앱 · key_tools · writes · confirm · optional) | 포털 `infra/personas` | 챗 운영자 · 확인 카드 · 팀 · 루틴 팀 |

이름을 박은 손 목록도 따로 있다. `_TOOL_PRIORITY` 37 · `_ONTO_CORE` 16 · `_MATERIAL_TOOLS` 18 · `_CONFIRM_JOB_TOOLS` 26 · 상태 도구 BUILTIN · `_RISK_*` · 프롬프트 안의 도구 이름이다. dev 에서 `_TOOL_PRIORITY` 의 `semantic_search` 는 이름이 겹쳐 `aidatahub_semantic_search` · `signalforge_semantic_search` 로 노출된다. 그래서 캡 길의 상시 예약에 안 걸린다 **[확인]**. 도구가 늘수록 겹침 접두가 늘어 손 목록이 더 빗나간다 **[짐작]**.

### 3.4 같은 목적, 다른 무리 — 예

| 목적 | 웹 챗 | 심의 좌석 | 루틴 | 개인 Claude |
|---|---|---|---|---|
| 코어 객체(과제 · 고장모드 · 시험항목) | 허브 도구 16 늘 묶음 + 규칙 ①~⑦ | 허브 도구 못 부름(접두 밖) | 작성자가 허브 백엔드를 고르면(읽기 표지가 있으면) | 전체 보기에서 이름 목록 · 묶음 보기의 정본 읽기 · ontology_lookup(손잡이 기본 끔) |
| 물성 | 관련도 + 상시 핵심의 물성 도구 | `_MATERIAL_TOOLS` 18 늘 남김 | MaterialTwin 백엔드 단계 | 전체 · search_tools |
| 잡 상태 | 상태 기다림(코드 폴링) | 접두 밖(job_status 는 안 열림) | 읽기 표지가 있으면 | 모델이 직접 부름(wait_s) |

### 3.5 하나로 모을 수 있는 것과 없는 것

**모을 수 있다.**
- 영역(하는 일) 분류 — `tool_areas.json` 이 이미 정본이다. `_AREA_HINT` 낱말과 운영자 입구 도구를 그 표의 칸으로 옮길 수 있다.
- 도구마다 읽기 · 쓰기 · 잡 · 파괴 · 모름 부류 — 게이트웨이 한 곳에서 내고, 쓰는 쪽은 덧씌움만 쥔다.
- 목적별 입구 도구 · 예약 도구 — 지금 `_TOOL_PRIORITY` · `_ONTO_CORE` · `key_tools` 로 흩어져 있다.

**모으면 안 된다(정책이라 쓰는 쪽마다 다르다).**
- D-18(리스크 심사 앞 패널 · 인사이트 · 보고서 감춤), 확인 카드의 "이번 말이 시켰나" 판정, 루틴의 단계 울타리, 절차의 재생 관문, 패널 PAT 막이.
- 예산(창이 쓰는 쪽마다 다르다)과 결과 상한.
- 절차는 기록된 구체 호출이라 목적 표를 읽을 자리가 없다.

---

## 4. 2,000개 규모에서 각 길

| 쓰는 쪽 | 턴(호출)마다 싣는 정의 | 후보를 고르는 규칙이 2,000개에서 | 깨지는 곳 |
|---|---|---|---|
| 웹 챗 Qwen 262K | 약 88k 토큰 · 약 210~225개(11%) **[확인 · 짐작]** | 어휘 + 의미 RRF 상위. 2,000개 임베딩은 64개씩 약 31번(첫 턴 · 카탈로그가 바뀔 때) | 관련도가 빗나가면 search_tools 왕복. 묶음 순서가 턴마다 바뀌어 앞부분 캐시는 고정 몫까지만 맞는다(W-3) |
| 웹 챗 Qwen 1M(켰다면) | 약 425k 토큰 · 약 1,000개 **[짐작]** | 같음 | 호출마다 비용 · 지연이 창 크기에 비례해 는다. 도구를 늘릴수록 고르는 정확도가 떨어진다(`app.py:7461` 주석 — 상위 40개가 호출의 79%) |
| 웹 챗 Claude(cae00 무캡) | 약 421k 토큰 · 약 1,000개 **[확인 — 식 · 짐작 — 개수]** | 같음 | Opus 5.5 입력 $4/1M — 캐시 없는 첫 호출은 정의만 약 $1.7, 캐시 읽기는 약 $0.08 **[짐작]**. `CHAT_TOOL_SCHEMA_BUDGET` 이 비면 이렇다 |
| 웹 챗 dev Claude | 12k 토큰 · 40개 · 설명 120자 **[확인]** | 같음 | 설명 절단으로 인자 꼴을 모른다 |
| 심의 좌석(GLM 20만) | 좌석마다 40k 토큰 · 약 100개 **[짐작]** | 후보 ≈ 접두 비율 31% × 1,970 ≈ 600 **[짐작]** → 영역 낱말 순위. 같은 점수면 게이트웨이 순서 | 같은 영역 안 수백 개가 같은 점수로 묶이면 게이트웨이 순서가 정한다. 20석 × 3라운드면 정의만 약 2.4M 토큰 **[짐작]** |
| 루틴 단계 | 고른 도구(안 적으면 백엔드 읽기 전부) | 사람이 고른다 | 큰 백엔드 단계에 도구를 안 적으면 수백 개 |
| 위임 | 읽기 전부 ≈ 1,100개 · 약 0.45M 토큰 **[짐작]** | 없음 | 262K 창이면 400 · 1M 이면 호출마다 큰 입력(위 2.3) |
| 개인 Claude 전체 보기 | 시작 문맥 +36.9k~38.8k(이름) **[확인 — 문서]** + 불러온 스키마 | ToolSearch(Claude Code) + search_tools | 데이터허브 사본 464개가 이름 목록에 그대로 있다(G-4) |
| 개인 Claude 가벼운 보기 | 두 도구 | search_tools 만 | 패널 도구 17개가 목록에서 빠져 화면이 안 열린다(G-1) |

---

## 5. 실패 신호

### 5.1 dev 로그 · 감사(유형 · 수만)

- `HWAXAgentServer/agent-server.log` 는 11-27 기동 뒤 1만 3천여 줄이다. `[agent]` 줄은 9개(기동 · 창 조회 실패 4)뿐이고 챗 도구 선택 줄(tool select · tool budget)은 0이다. dev 웹 챗은 이 기간에 거의 안 쓰였다. 실패 신호로는 쓸모가 적다 **[확인]**.
- 게이트웨이 감사(`/data/svc/mcp-gateway/audit.jsonl`, 10-28 ~ 11-27)는 1,234줄이다 **[확인]**.
  - 경로별 호출 — gw-token 722 · chat 58 · pat 16 · ticket 6. 연결 단계 실패가 428 이다.
  - 연결 단계 실패의 까닭 — 토큰 수명 끝(expired) 395 · 검증 안 된 토큰 31 · bearer 없음 2. 개인 연결의 PAT 수명이 끝나 조용히 못 붙는 꼴이고, 이 조사 세션의 hwax 연결도 같은 까닭(expired)으로 실패했다.
  - chat 경로 실패 13 — MaterialTwin 물성 도구 인자 오류가 대부분이다.
  - 11-03 두 시간 안에 `heaxstep_forge_job_status` 가 185번 불렸다(서비스 자격). 코드 폴링인지 스크립트인지는 이 기록으로 가를 수 없다 **[짐작 — 그날 그림 점검 스크립트 시험과 겹친다]**.

### 5.2 10-29 · 10-30 QA 요청서의 도구 실패 — 지금 어디까지

| 실패 꼴 | 요청 | 고친 것(코드) | 남은 것 |
|---|---|---|---|
| 코어 질문이 FMEA · ARP · MatNexus · RA 로 샌다(10-29 OT-06~10 FAIL) | 10-29 A~E | 코어 규칙 · 어휘표 · 고정 몫 16 · 가족 접기(E-2) · 비코어 낮추기 손잡이(기본 끔) · 보기(E-4) · ontology_lookup(손잡이 기본 끔). 10-30 재시험 16문항 PASS 12 · PARTIAL 3 · FAIL 1(10-29 는 9 · 3 · 4) | cae00 재시험 · `noncore_demote` 켜기(사람) · onto 손잡이 재기 · O-3 예산 A/B(30,000 · 40,000) · 좌석은 허브 도구를 아직 못 씀(`docs/request-1029/checklist.md:33` · `:70` · `:131`) |
| 잡 상태를 LLM 으로 폴링(DW-02 get_task 26번 · LLM 29번) | HA-28 | 상태 도구는 코드가 10초 간격 · 600초까지 기다린다(`status_wait.py`, dev `/health status_wait on`) | 상태 도구 판정이 이름 목록(BUILTIN · EXTRA) ∩ routine_read 라 새 앱 상태 도구는 박스 덧붙임이 필요하다 |
| 묻지 않고 무거운 잡(DW-03 run_job 1,812초) | HA-29 | 확인 카드(운영자 writes · confirm + 잡 바닥 26, `app.py:4146`) | 이름 목록 밖의 잡 · 쓰기는 샌다(반대 검토에서 extract_surface_to_cad 를 뒤늦게 더함). WD-07 — RA 보고서 생성 · 태그 · 발행이 RA 운영자가 아닌 대화에서는 카드 없이 나갔다(11-10, `docs/request-1125/request.md:1335`) — 미배정 |
| 다른 허브 id 를 넘김(OT-07) | HA-30 | 부르기 전에 돌려준다(`app.py:2246`, dev `xhub_gate on`) | WD-10 — 대상 고정이 없어 36번 · 196초 동안 엉뚱한 보드 판을 골랐다(`request-1125/request.md:1389`) — 미배정 |
| (새) 도구가 안 묶인 턴에 호출을 지어냄(없는 job id · 표결표) | WD-02 | 없음 | 미배정 · P1 · 권한 순서 첫째(`request-1125/request.md:1233`) |
| (새) 규칙 낱말이 없는 턴에도 코어 규칙 · 예약 16개(약 17k자) | A-2 | 없음 | 미배정 |
| (새) 개인 Claude 이름 목록 · 큰 결과 | G-1 ~ G-5 · P-1 | 장치는 있다(보기 · 결과 손잡이) | 운영 쪽 한 판 측정 뒤(`request-1125/request.md:2967-2975`) |

에이전트 서버 몫은 모두 미배정이다(`docs/request-1125/PLAN.md:14`). 에이전트 서버 git 최근 15개 커밋에 WD · A-2 는 없다 **[확인]**.

---

## 6. 개인 Claude — 목적별로 필요한 MCP 만 붙이는 길

**지금 고를 수 있는 것.** 아래 넷이 다다 **[확인]**.
1. 포털 '허브에 보일 앱'(앱 끄기 — 목록 · 검색에서 뺀다).
2. 포털 보기 하나 — 전체 · 묶음(영역 여럿) · 가벼운. 토큰 페이지 배치로 등록한 연결(`X-HWAX-View: portal`)에만 먹는다.
3. 연결 머리를 손으로 바꾸기 — `X-HWAX-View: bundle:cad,mesh` 처럼. 리포 `.mcp.json` 은 `HWAX_GATEWAY_VIEW` 환경변수다.
4. 결과 손잡이 칸 — `X-HWAX-Result: ref`, 박스 스위치 `GATEWAY_RESULT_REFS` 와 함께.

**없는 것.**
- 목적(예 "낙하 해석" · "품질 원인") 단위의 보기. 영역은 앱 단위에 가깝다 — StepForge 가 통째로 cad 다.
- 과제 · 작업마다 바꾸는 길. 보기는 사람마다 하나이고 열린 세션은 재연결해야 바뀐다.
- 이름 목록에서 같은 도구 사본을 빼는 일(G-4).

**제약.** 연결을 목적별로 여럿 등록할 수는 있다(같은 PAT · 다른 머리). 그러면 서버 이름마다 도구 이름 접두가 달라져 허용 규칙 · 워크플로가 깨진다. 그래서 앱별 서버를 하지 않았다(`docs/mcp-app-toggle/PLAN.md:36`). 워크플로는 늘 전체 보기여야 한다(좌석이 목록 밖 도구를 못 보면 안 된다 — `.mcp.json` 주석) **[확인]**.

---

## 7. 고도화 안

### 안 1. 목적 묶음 정본 — `tool_areas.json` 을 넓힌다

- **무엇.** 게이트웨이 영역 표에 `purposes` 칸을 더한다. 목적 하나는 다음을 갖는다.
  - 영역들.
  - 입구 도구(원래 이름 — 지금의 `key_tools` · `_ONTO_CORE` · `_TOOL_PRIORITY` 가운데 그 목적 몫).
  - 낱말(지금 `_AREA_HINT`).
  - 예약 여부.
  - `/tools-map` 에 `purposes` 로 싣는다.
  - 쓰는 쪽은 처음엔 읽기만 한다(그림자 — 고른 결과를 지금 결과와 견줘 적기만).
- **손댈 곳.**
  - 게이트웨이 `tool_areas.json` · `gateway.py:2964` `_area_of` 곁 · `/tools-map`(`:12448`).
  - 에이전트 서버 `deliberation.py:5076` `_AREA_HINT`(표에서 읽고 지금 값은 기본값으로) · `app.py:3076` `_TOOL_PRIORITY` · `:3260` `_ONTO_CORE`.
  - 포털 `he-team.json` key_tools(목적의 입구로 참조).
- **기본값에서 바뀌는 것.** 없음(칸만 더하고 소비자는 그림자).
- **위험.** 표가 하나 더 는다. 분류가 틀리면 모든 쓰는 쪽이 한꺼번에 틀린다. cae00 전용 앱(선언 백엔드 · 허브 셋)의 줄은 cae00 덧씌우기가 필요하다(어휘표와 같은 merge patch 꼴).
- **재는 법.**
  - cae00 `/tools-map` 에서 목적에 안 든 도구 수.
  - 그림자 로그의 '지금 고른 것 vs 목적 묶음' 겹침.
  - `tool_search_eval` 정답쌍을 목적별로 hit@5.

### 안 2. 웹 챗 도구 계획 정밀화 — 창 비율이 아니라 목적과 절대 예산

- **무엇.**
  1. 턴의 목적을 1~3개로 정한다 — 앞 턴 활동 · 핀 · 운영자 · 어휘표 낱말 · 영역 설명 임베딩. 그 목적의 도구 + 안내대 + 예약 + 핀만 묶는다. 예산은 절대값(`CHAT_TOOL_SCHEMA_BUDGET` 기본을 0 → 예 40,000)이다.
  2. 묶음 차례를 목적 블록 · 이름순으로 고정해 접두 캐시를 살린다.
  3. Claude 턴은 Anthropic 도구 찾기(tool search tool — regex · BM25, 나머지에 `defer_loading`)를 쓴다. 안내대 · 예약만 늘 싣고 나머지는 지연한다. langchain-anthropic 이 서버 도구 · `defer_loading` 칸을 그대로 넘기는지는 확인해야 한다 **[짐작]**.
  4. WD-02 — 대화에 심의 · 리스크 잡 맥락이 있으면 deliberate_* · risk_* 를 그 턴에 묶고, 이번 턴 활동에 없는 job id · 행동 주장을 짚는다.
  5. A-2 — 규칙 낱말이 없는 턴은 코어 규칙 · 예약을 뺀다.
  6. dev `.env` 의 16K 시절 값(TOOL_MAX · TOOL_DESC_MAX · TOOL_SCHEMA_BUDGET)을 걷어 dev Claude QA 가 실제를 비추게 한다.
- **손댈 곳.** 에이전트 서버 `app.py:3390` `_select_tools` · `:3418` 예산 식 · `:5088` `_agent_for` 캐시 열쇠 · `chat_claude.py:310` `build`(도구 찾기) · `:7442-7530` 턴 조립. dev `HWAXAgentServer/.env`(사람 확인 뒤).
- **기본값에서 바뀌는 것.**
  - cae00 Qwen 턴은 약 210개 · 88k 토큰에서 약 100개 · 40k 토큰으로 준다.
  - Claude 턴은 약 1,000개 · 421k 토큰에서 수십 개 + 찾기로 준다.
  - 손잡이 기본 끔으로 짓고 cae00 에서 켜는 쪽이 안전하다.
- **위험.**
  - 목적 판정이 빗나가면 search_tools → invoke_tool 왕복이 는다(W-2 의 경고).
  - Claude 지연 로드는 캐시 · 생각 블록 규칙과 맞물린다(도구가 덧붙는 꼴이라 앞부분은 보존된다고 문서는 말한다).
  - WD-02 의 행동 주장 판정이 잘못 짚을 수 있다.
- **재는 법.**
  - 같은 16문항 · 운영자 14명(10-29 · 10-30 틀) — PASS 수 · 첫 도구 · 턴당 모델 호출 수.
  - 턴당 프롬프트 토큰 · search_tools 비율 · `/health tool_cut`.
  - Claude 는 `usage.cache_read_input_tokens` 와 턴당 비용.

### 안 3. 심의 좌석의 목적별 도구 — 이름 접두 대신 게이트웨이 확인 읽기

- **무엇.**
  1. 후보를 `_FREE_ALLOW` 대신 게이트웨이 panel_read(확인된 읽기) ∩ 그 사람 시야로 짓는다. 닫기 · D-18 · 물성 예외는 그대로다.
  2. 의장 틀마다 목적을 붙인다 — diagnosis → quality · voc · result · knowledge, sim-plan → sim · mesh · calc · material.
  3. 좌석 순위를 목적 묶음 + 페르소나 연결(E-5 의 domains → areas)로 매긴다.
  4. 같은 점수 안의 차례는 게이트웨이 순서가 아니라 화두 임베딩 유사도로 정한다.
  5. 허브 도구를 좌석에 열지는 ontology-first §5.4 결정과 함께 정한다.
- **손댈 곳.** 에이전트 서버 `deliberation.py:6762-6800`(후보 조립) · `:5116` · `:5184` · `:4551`(접두 표는 읽기 목록에 없는 옛 도구의 덧씌움으로만). 게이트웨이 `read_tools.json`(접두로만 열리던 154개 가운데 진짜 읽기를 읽기 목록에).
- **기본값에서 바뀌는 것.** dev 후보가 238 → 244 로 바뀐다. 같은 것은 84개다. 154개가 빠지고 160개(StepForge 읽기 등)가 든다 **[확인 — 수]**. 손잡이로 짓고 그림자부터 하는 것이 맞다.
- **위험.**
  - D-18 누수 — 리스크 심사는 지금 판정 그대로 두어야 한다(F0 때 `reportarchive_list_reports` 가 열릴 뻔한 일, `docs/ontology-first/context-notes.md:39`).
  - agent_search 처럼 좌석의 핵심 통로가 panel_read 밖이면 덧씌움이 먼저 필요하다.
- **재는 법.**
  - 에이전트 서버 `/seat-eval` · `seat_questions`.
  - 좌석당 조회 수 · 거절 수 · `free_tools_unavailable` 경고 수.
  - 결정문 수치의 출처 비율(`evidence.unsourced_numbers`).

### 안 4. PC 킷의 목적별 연결 — 보기를 목적 프리셋으로

- **무엇.**
  1. 포털 보기 화면에 목적 프리셋을 둔다(안 1 의 목적 → `bundle:<영역>`, 예 "CAD · 해석" · "품질 · VOC" · "보고서 · 문서"). 영역을 하나하나 고르지 않게 한다.
  2. 개인 Claude 가 대화 중 보기를 바꾸는 게이트웨이 도구를 둔다(포털 저장 + `notifications/tools/list_changed` — G-3). 재연결 없이 목록이 바뀐다.
  3. G-1 — 가벼운 보기에 패널 도구 · verify_answer · list_tool_apps 를 더한다.
  4. G-4 — 데이터허브 사본을 한 벌 + `hub` 인자로.
  5. P-1 — 배치의 기본 머리에 결과 손잡이를 둔다.
  - 연결은 하나로 둔다(도구 이름 접두를 지킨다).
- **손댈 곳.** 포털 `frontend/src/components/HubViewPanel.tsx` · `backend/app/access/hub_view.py` · `frontend/src/lib/setupBat.ts:86-89`. 게이트웨이 `gateway.py:10124`(가벼운) · `:10127`(묶음) · capabilities · 사본 접기.
- **기본값에서 바뀌는 것.** 프리셋 · 도구는 없음(고르는 사람만). P-1 · G-4 는 모든 연결의 목록이 바뀐다.
- **위험.**
  - 묶음 밖 도구를 모델이 모르고 "없다" 고 할 수 있다(안내 note 가 있지만 모델이 읽어야 한다).
  - listChanged 를 mcp-remote 가 넘기는지 모른다(G-3 확인 항목).
  - G-4 는 옛 접두 이름을 쓰는 워크플로 · 허용 규칙이 별칭으로 계속 돌아야 한다.
- **재는 법.**
  - 게이트웨이 `/health tools_list_by_view`.
  - 세션 시작 문맥 토큰(기준 36.9k~38.8k).
  - 찾기 호출 비율(기준 22.6%) · 11-24 틀 64회의 패배율.

### 안 5. 읽기 · 쓰기 부류를 게이트웨이 한 판정으로

- **무엇.** 게이트웨이가 도구마다 부류(확인된 읽기 · 쓰기 · 잡 시작 · 파괴 · 모름)를 정해 `/tools-map` 과 tools/list 의 annotations(G-5)에 싣는다. 좌석 접두 · 잡 바닥 목록 · 상태 도구 목록 · 포털 MUST_GATE 는 그 부류를 읽고, 지금 목록은 덧씌움(더 엄하게만)으로 남긴다. 먼저 고칠 것은 둘이다.
  - 게이트웨이 안의 모순 6개(write 이면서 routine_read).
  - 모름 136개(dev) — cae00 은 표지 없는 83.5% 에서 얼마인지 센다.
- **손댈 곳.** 게이트웨이 `gateway.py:4080` · `:9733` · `:9759` · `read_tools.json`. 에이전트 서버 `app.py:4146` · `status_wait.py:119` · `deliberation.py:4551`. 포털 `procedures/models.py:26`.
- **기본값에서 바뀌는 것.** 그림자 단계에서는 없음(다른 판정을 로그 · `/health` 에 센다).
- **위험.**
  - 좌석 · 위임에 열리는 도구가 바뀐다.
  - 절차 관문을 느슨하게 하면 안 된다(덧씌움은 더 엄하게만).
  - 앱 표지가 틀리면 한꺼번에 틀린다(RF-39 처럼 앱이 표지를 바꾸는 일).
- **재는 법.** 판정 셋의 불일치 수(지금 dev — 모순 6 · 모름 136 · 좌석 ↔ panel_read 어긋남 314)가 0 으로 가는지. 좌석 · 루틴의 거절 수.

### 안 6. 위임 · 루틴의 묶음 예산

- **무엇.** 위임 울타리(`read_fence`) 뒤에 웹 챗과 같은 관련도 · 절대 예산 고르기를 넣는다(`_select_tools` 재사용 — 맡긴 일 글이 질의). 또는 `apps` 를 필수로 한다. 루틴 단계에 도구를 안 적었으면 계획 화면에서 개수 · 추정 토큰을 보이고 상한을 둔다. 먼저 A-1 의 "단계마다 무엇을 다시 싣나" 를 잴 때 도구 정의 몫을 같이 잰다.
- **손댈 곳.** 에이전트 서버 `offload.py:251` · `:426` · `routine.py:978`. 포털 `procedures/routines.py:378`(계획의 추정 토큰).
- **기본값에서 바뀌는 것.** 위임은 기본 꺼짐이라 켠 박스만 바뀐다. 루틴은 표시만 는다.
- **위험.** 관련도가 빗나가면 위임이 덜 찾는다(OF-2 '덜 찾음' 과 겹친다).
- **재는 법.** 위임 잡당 서버 입력 토큰(기준 0.98M) · 패배율(기준 25%) · 같은 과제 재측정.

### 차례 제안

1. 안 2 의 dev `.env` 정리(사람 확인 · 재기동)와 안 6 의 측정 — 값싸고 지금 판단을 흐리는 것을 걷는다.
2. 안 5 그림자 — 다른 안이 기대는 부류를 먼저 세운다.
3. 안 1 그림자.
4. 안 2(웹 챗) · 안 3(좌석) · 안 4(PC) 켜기 — cae00 에서 잰 뒤.

WD-02 · A-2 는 안 2 안에서 함께 받는 것이 자리가 맞다.

---

## 8. 열린 물음(사람 · cae00)

- cae00 stcx Qwen 이 1,010,000 창으로 떠 있나. 떠 있으면 웹 챗 · 위임의 도구 정의가 호출마다 약 0.4M 토큰이다 **[짐작]**. `/health` 의 `chat_llm.ctx_tokens` 와 `tool_cut.budget` 으로 본다.
- cae00 에 `CHAT_TOOL_SCHEMA_BUDGET` 이 적혀 있나(O-3 A/B 전이면 비었다). Claude 개별 허가가 켜져 있으면 그 사람의 턴은 약 421k 토큰 예산이다.
- cae00 `/tools-map` 의 write · routine_read · panel_read 수, 모름 수, 좌석 접두 후보 수. 이 문서의 dev 수와 견준다.
- 좌석에 허브 도구를 열지(ontology-first §5.4).
- 11-03 dev 의 job_status 185번이 어느 경로(상태 기다림 · 스크립트)였는지.
