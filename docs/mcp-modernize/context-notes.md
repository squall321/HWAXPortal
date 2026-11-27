# 결정 기록 — MCP 현대화

> 계획 [PLAN.md](PLAN.md) · 할 일 [checklist.md](checklist.md).

## MM-1 조사(2026-11-27) — 네 갈래 · 원본은 audit/

서브에이전트 넷이 읽기만 해서 조사했다(리포 변경 0). 원본은 [audit/](audit/) 에 옮겨 두었다(스크래치패드는 지워진다).

- **계약**(audit/contract.md) — dev tools/list 797(백엔드 765 + 게이트웨이 32 — 서비스 시야). 설명 합 51만 자 중 StepForge 가 52.7%. 인자 2,998 중 설명 1,136(0.379) ·
  스키마에도 설명에도 없는 인자 750 · enum 13 · 숫자 경계 11/709 · 자유형 객체 237 · 표지 273 · outputSchema 107(모두 FastMCP 자동 껍데기). 앱이 「Args:」 를 써도
  1.x FastMCP 는 스키마로 옮기지 않는다. SmartTwin 은 카탈로그에 인자 103개 · 설명 100% 를 갖고도 `_register_direct` 가 `args: object` 로 버린다.
  감사 원장이 `isError` 결과의 사유를 비운다(60일 실패 129 중 97).
- **찾기**(audit/discovery.md) — 목적 단위가 없다(영역 = 앱). 보기 셋 채택 0(셈이 프로세스 메모리라 재기동마다 0). 앱별 엔드포인트 없음(9-29 D-1 미룸 · 10-31 보기
  셋으로 갈음). prompts 는 루틴뿐(서비스 토큰 분기는 늘 빈 목록). 서버 지침 2,031/2,048자. 오프라인 평가 — doc 42 hit@5 0.857 · auto 107 hit@5 0.383.
  목적 흉내 다섯 중 셋(낙하 해석 준비 · 보고서 쓰기 · 설계 리스크)이 입구 도구를 20위 밖으로. 「쓰기」 · 「작성」 이 쓰기 의도 낱말에 없어 보고서 작성 도구가 감점된다.
- **쓰는 쪽**(audit/consumers.md) — 목적 → 도구 규칙 다섯 벌 · 읽기/쓰기 판정 일곱 벌(게이트웨이 셋 · 좌석 접두 · 챗 확인 카드 · 포털 `MUST_GATE` · 파괴 막이).
  좌석 접두 후보 238 과 panel_read 244 가 겹치는 것은 84. 웹 챗은 cae00 에서 창의 45% 를 도구 정의에 쓴다. dev `.env` 가 16K 시절 값(도구 40 · 설명 120자).
- **사내**(audit/onprem.md) — cae00 백엔드 35 · 도구 1,984. cae00 전용 약 1,200(추정) — SP 허브 다섯 ≈ 580 · ComponentCore 183 · MatNexus 128 · TestScope 99 가 85%.
  표지 없음 83.5% · 새 사내 앱 넷 인자 설명 0% · 1,000자 넘는 설명 296 · 미분류 321. 점검 한 벌 MQ-1 ~ MQ-6 초안이 audit/onprem.md 5-1 에 있다.

## MM-2 스펙 · SDK(2026-11-27 확인 — 원문)

- **2026-07-28 스펙**(https://modelcontextprotocol.io/specification/2026-07-28/changelog) — `Mcp-Session-Id` 와 `initialize` 핸드셰이크를 없앴다(SEP-2567 · SEP-2575).
  요청마다 `_meta` 에 `io.modelcontextprotocol/protocolVersion` · `clientCapabilities`. `server/discover` 필수. 연결 사이 상태는 서버가 낸 handle 을 도구 인자로.
  서버 → 클라이언트 요청(sampling · elicitation · roots)은 `InputRequiredResult` 다시 묻기(MRTR, SEP-2322)로. 모든 결과에 `resultType`. `Mcp-Method` · `Mcp-Name` 머리.
  목록 결과에 `ttlMs` · `cacheScope`. Tasks 는 확장 `io.modelcontextprotocol/tasks` 로 빠졌다(SEP-2663). Roots · Sampling · Logging · HTTP+SSE 는 낡음.
  같은 자리에서 두 세대를 다 내는 dual-era 서버가 허용된다(basic/versioning).
- **Skills 확장**(https://modelcontextprotocol.io/extensions/skills/overview) — SEP-2640 Final · 확장 Beta. `skills/list` · `skills/get` · 파일은 `resources/read` ·
  `skill://` 권장 · SKILL.md frontmatter `name` · `description`. 호스트가 매니페스트의 sha256 · 크기를 검증하고 승인한다. 클라이언트 지원표에서 Claude 클라이언트 칸은
  비어 있다(11-24 베타 발표 기사가 있으나 지원표로 확인되지 않음).
- **Events 확장**(https://modelcontextprotocol.io/extensions/events/overview) — SEP-3415 Final · 확장 Beta. `events/poll` · `events/stream` · `events/subscribe`(webhook,
  Standard Webhooks HMAC). 이벤트 `{eventId, name, timestamp, data, cursor}`. poll · stream 은 순서 보장, webhook 은 best-effort.
- **Python SDK 2.x**(https://py.sdk.modelcontextprotocol.io/migration/ · /run/legacy-clients/) — 2.0.0 이 2026-07-28 에 나왔고 지금 2.3.0. 두 세대를 플래그 없이
  같은 자리에서 낸다(옛 세대는 세션을 프로세스 dict 에 둔다 — `stateless_http=True` 는 옛 세대 쪽에만 먹는다). Python 3.11 이상. `FastMCP` → `MCPServer`
  (`mcp.server.mcpserver`) · 생성자의 전송 인자는 `streamable_http_app()` · `run()` 으로 · httpx → httpx2 · 일반 예외는 「Error executing tool <이름>」 으로 가려진다
  (`ToolError` 로 내야 보인다) · 127.0.0.1 로 뜨면 DNS rebinding 막기가 기본으로 켜진다. 인자 설명은 `Field(description=)` 만 — docstring 은 읽지 않는다.
  Skills 는 내장 확장(`Skills(list_skills=…, get_skill=…)`)이 있다. Tasks 는 「아직 구현 안 함」. Events 는 문서에 없다.
- 우리 판 — 앱 전부 1.27 ~ 1.30. 게이트웨이 · 에이전트 서버는 에이전트 서버 venv(Python 3.10 · mcp 1.28.0)로 돈다. dev 호스트에는 3.11 ~ 3.13 이 있다. cae00 은 모른다.

## MM-3 방향과 까닭(2026-11-27)

- **두 걸음.** SDK 2.x 는 이름 · 생성자 · httpx2 · lifespan · 예외 가림까지 바뀌어 리포마다 하루 일이고 Python 3.11 이 든다(게이트웨이 · 에이전트 서버 · KooRemapper
  MCP venv 는 3.10). 그래서 1단계(1.x 그대로 `stateless_http=True`)로 서버가 세션을 쥐지 않게 먼저 만들고, 2단계에서 새 세대를 연다. 1단계만으로도 재기동 · 여러 대에서
  끊기지 않는다. 다만 옛 세대 stateless 에서는 서버 → 클라이언트 알림이 버려진다 — 우리 앱은 그 채널을 쓰지 않는다(확인할 것 — checklist M1).
- **게이트웨이가 먼저인 까닭.** 사람(개인 Claude)이 붙는 자리가 게이트웨이 하나다. 앱이 새 세대여도 게이트웨이가 세션을 쥐면 재기동마다 사람 쪽이 끊긴다.
  세션 번호에 기댄 것 셋 — 근거 원장 열쇠(`_evid_key`) · 재기동 막기(세션 머리 없는 POST = 새 세션) · 질의 기록의 뒤이은 호출 잇기 — 을 사람 · 대화 handle 로 옮긴다.
- **판정 한 곳.** 일곱 벌의 읽기/쓰기 판정이 어긋나(모순 6 · 모름 136) 같은 도구가 챗에서는 열리고 좌석에서는 막힌다. 부류는 게이트웨이가 정하고(앱 표지 ∪ 확인된
  목록 — 앱 표지보다 느슨하게는 못 한다), 쓰는 쪽의 정책은 그 부류 위에 그대로 둔다.
- **목적 표를 게이트웨이에 두는 까닭.** 검색 · 목록 · 보기 · prompts · skills 를 내는 곳이 게이트웨이이고, 웹 챗 · 좌석 · PC 킷은 이미 `/tools-map` 을 읽는다.
  포털 core_vocab 곁에 두면 한 번 더 건너야 한다. 박스 덧씌우기(`.local.json`)는 search_tuning · core_vocab 과 같은 꼴(merge patch · 깨지면 통째로 버림)로 한다.
- **Skills 는 목적 표의 내보내기.** 같은 글을 skill · prompt · 자원 · 도구로 내므로 클라이언트 지원을 기다리지 않는다. 2.x 의 내장 Skills 확장을 쓴다(M1 2단계 뒤).
- **Events 를 게이트웨이 허브로.** SDK 2.x 에 Events 구현이 없어 앱마다 짓게 하면 열 벌이 된다. 앱은 「바뀐 것 목록」 읽기 도구만 내고(자동 파이프라인 `auto_changes` 와
  같은 꼴), 게이트웨이가 커서로 묻고 확장 꼴로 다시 낸다. webhook 은 바깥으로 나가는 길이라 서명 · SSRF 막기와 함께 뒤에.
- **docstring 대신 채우기(게이트웨이 일괄 A)는 임시.** 「Args:」 꼴이 확인된 앱만, 점수판에 「게이트웨이가 채움」 을 따로 센다. 앱이 Field 로 옮기면 그 앱은 끈다.
  enum 은 게이트웨이가 넣지 않는다(닫힌 집합인지 모르고, 엄격한 클라이언트가 지금 되는 호출을 막을 수 있다).

## MM-4 ~ MM-6 사용자 결정 셋(2026-11-27)

- **MM-4 세션 없는 리포 셋은 이 세션이 직접**(권장안) — ThermalShockMCP · WebResearchMCP · PaperIngest. 가지에서 고치고 시험 뒤 main, SIF 는 허브가 짓고 Drive 는 라운드에.
- **MM-5 읽기 · 쓰기 표지는 게이트웨이 판정으로 노출**(권장안) — 10월의 「클라이언트 표지는 앱이 적은 그대로」(report-figures RF-39)를 사용자 결정으로 뒤집는다.
  앱 표지 ∪ 확인된 읽기 목록을 노출 사본에 싣고, 모르는 도구는 읽기로 표시하지 않으며, 앱 표지보다 느슨하게 바꾸지 않는다.
- **MM-6 cae00 은 7차 라운드에 1단계까지**(권장안 아님 — 권장은 8차부터) — 7차 글을 조금 미루고 게이트웨이 stateless · 앱 1단계(`stateless_http=True`)를 함께 싣는다.
  87 에 알리고 차례를 맞춘다. SDK 2.x · 목적 묶음 · Skills · Events 는 그 뒤 라운드마다.

## MM-7 바로잡음(2026-11-27 — 앱 세션 답에서)

- **SDK 2.x 의 Python 하한** — MM-2 의 「Python 3.11 이상」 은 SDK 문서(설치 쪽)를 옮긴 것이다. PyPI `mcp` 2.0.0 · 2.3.0 의 `requires_python` 은 `>=3.10` 이다(PyPI JSON 확인 ·
  DynaForge 세션이 휠 METADATA 로 같은 값). 설치는 3.10 에서도 막히지 않는다. 문서가 3.11 을 말하는 까닭(지원 범위 · 시험 행렬)은 확인하지 못했으니, 3.10 venv 에서
  2.x 를 쓸 때는 시험을 먼저 돌려 본다. 게이트웨이 · 에이전트 서버를 3.12 venv 로 옮기는 계획은 그대로 둔다(안전한 쪽).
- **운영 런타임** — DynaForge MCP 는 운영에서 3.10 venv 가 아니라 `mcp.sif`(python 3.12 · mcp 1.28.0)로 돈다. 3.10 은 박스의 시험 · 스모크 venv 뿐이다. DynaForge 는 허브 등록이 아닌
  자체 빌드(Drive `dist-*`)라 알릴 숫자는 Drive 판과 `SHA256SUMS` 의 `mcp.sif` 파일 sha256 이다(허브 캐시 열쇠 없음).
- **Laminate 표지** — 앱 세션에 「표지가 없다」 고 보낸 것은 틀렸다. 품질 카드로 43/43 표지가 있다(조사 원본 audit/contract.md 를 옮기다 생긴 잘못). 앱에 보내는 숫자는 품질 카드로 다시 잰다.
- **MaterialTwin `property_key`** — 어휘는 157 이 아니라 276(라이브 정의 11-23). 스키마 enum 대신 설명에 찾는 도구 이름 + 서버가 가까운 후보를 담은 오류(동적 enum 은 재기동 전
  새 정의를 거절하고 스키마가 재기동마다 바뀌어 캐시와 어긋난다).
- **1.x stateless 의 동작 변화**(DynaForge 탐침) — initialize 세션 번호 없음 · initialize 없이 불러도 200 · 옛 세션 번호도 200 · GET 은 열린 채 빈 SSE · DELETE 405.

## MM-8 판정 합치기는 넘어가는 동안 그림자(사용자 결정 2026-11-27, 권장안)

게이트웨이 M2(가지 `wt1127/m2`)는 읽기 · 쓰기 판정을 한 함수(`_tool_class` — 앱 표지 > override > 확인된 읽기 목록 > 이름(쓰기만) > unknown)로 합친다.
엄격하게 켜면 이름 낱말만으로 읽기로 열리던 도구가 루틴 · 위임 · 상태 기다림에서 닫힌다(dev 아침 자료 190 — 그날 올린 앱 표지로 51 이 다시 열려 약 140,
cae00 은 표지 없음 83.5% 라 훨씬 많다). 이름으로 여는 것은 안전 구멍이지만(순위 규칙은 울타리가 아니다 — 취소 · 잡 제출이 샌 기록) cae00 루틴이 멈출 수 있어,
**7차에는 `GATEWAY_TOOL_CLASS_UNIFIED=shadow`(기본)** — 표지 노출 · tool_class · 검색 감점 · write 는 한 판정, 루틴 · 위임 · 상태 기다림 · 패널은 옛 판정 그대로,
「엄격이었으면 닫혔을」 도구를 `/health contract` · `/tools-map would_close` 에 센다. 앱 표지가 다 오른 다음 라운드에 `1`(엄격)로 바꾼다 — would_close 가 0 에
가까워진 것을 cae00 카드로 보고 정한다. 판단 둘은 받아들임: override 가 앱 readOnlyHint=False 를 이긴다(RF-39 · R-14 를 지키려고, 노출 표지는 앱 값 그대로) ·
닫기 목록은 deny 근거로 write.
