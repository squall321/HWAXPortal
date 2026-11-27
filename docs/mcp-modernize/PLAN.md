# MCP 현대화 — stateless · 정밀한 계약 · 목적 묶음 · Skills · Events

> 할 일 [checklist.md](checklist.md) · 결정과 까닭 [context-notes.md](context-notes.md) · 앱에 보내는 공통 계약 [contract.md](contract.md) ·
> 조사 원본 [audit/](audit/)(계약 · 찾기 · 쓰는 쪽 · 사내 넷).

사용자 요청(2026-11-27).
- 「여기서 개발 연계된 모든 MCP 들은 최신화 · 고도화를 해줘. 다 정밀하게 되게끔. 사내에 있는 것도 포함해서, 많은 도구들에서 목적에 따라 도구모음과 각 기능 MCP 에
  제대로 접근하고 활용할 수 있게끔 계획을 세우고 MCP 를 고도화해. 필요하면 서브에이전트를 나눠서.」
- 「실제 MCP 가 cae00 에서는 거의 2천 개다.」
- 「(stateless 로) 같은 거. 적어도 여기 프로젝트는 모두 바꿔야 하고 cae00 에도 이 비전을 팔로업하게 해야 해. stateless MCP 뿐만 아니라 이후 로드맵 대응도 —
  Skills over MCP 나 MCP Events.」

## 1. 지금 상태(2026-11-27 조사 — context-notes MM-1 · MM-2)

| 무엇 | 지금 |
|---|---|
| 규모 | dev 백엔드 18 · 도구 797 · cae00 백엔드 35 · 도구 1,984(11-26). cae00 전용 약 1,200 — SP 허브 다섯 · ComponentCore · MatNexus · TestScope 가 그 85% |
| 세션 | 게이트웨이(사람이 붙는 쪽)는 세션을 쥔다(FastMCP 기본). 앱은 일곱이 stateless, 아홉이 세션을 쥔다. 근거 원장(`verify_answer`) · 재기동 막기가 세션 번호에 기댄다 |
| SDK · Python | 앱 전부 공식 SDK 1.27 ~ 1.30(`mcp.server.fastmcp`). 2026-07-28 스펙은 SDK 2.x(2.0.0 = 2026-07-28, 지금 2.3.0)가 낸다 — Python 3.11 이상. 게이트웨이 · 에이전트 서버는 3.10 venv |
| 인자 계약 | 인자 2,998 중 설명 37.9% · enum 13 · 숫자 경계 11. 12개 앱이 0% — 뜻을 docstring 산문에만 쓰고, 1.x FastMCP 는 「Args:」 를 스키마로 옮기지 않는다 |
| 읽기 · 쓰기 표지 | dev 273/797 · cae00 83.5% 없음. 읽기 · 쓰기 판정이 일곱 벌이고 서로 어긋난다(모순 6 · 모름 136) |
| 목적 단위 | 없다. 영역(`tool_areas.json`)은 사실상 앱과 1:1. 목적 다섯 흉내에서 셋이 입구 도구를 20위 밖으로 냈다. 검색 auto 쌍 hit@5 0.383 |
| 노출 단위 | 보기 셋(full · bundle · light) 채택 0, 앱별 엔드포인트 없음, prompts 는 루틴뿐, 서버 지침은 2,048자 상한에 2,031자 |
| 쓰는 쪽 | 목적 → 도구 규칙이 다섯 벌(웹 챗 · 좌석 · 루틴 · 위임 · 개인 Claude). 2,000개에서 웹 챗은 창의 45% 를 도구 정의에 쓰고, 개인 Claude 는 이름만으로 시작 문맥 37k ~ 39k 토큰 |
| 측정 | 앱마다 한 장의 품질 카드가 없다. 감사 원장이 실패 사유를 비워 둔다(60일 실패 129 중 97). 사내 앱 정답쌍이 거의 없다 |

## 2. 목표

1. **stateless** — 우리 프로젝트의 MCP 서버 전부(게이트웨이 · 앱 · 심의)가 2026-07-28 스펙의 새 세대로 말하고, 옛 세대 클라이언트도 같은 자리에서 그대로 받는다
   (dual-era). 서버가 세션을 쥐지 않아 재기동 · 여러 대로 늘리기에 끊기지 않는다.
2. **정밀한 계약** — 도구마다 무엇 · 언제 · 형제 안내 · 인자 설명 · 단위 · 범위 · enum · 읽기/쓰기 표지 · 결과 꼴이 스키마에 있다. 판정은 게이트웨이 한 곳에서 한다.
3. **목적 단위 접근** — 목적 묶음 정본 표 하나를 검색 · 목록 · 보기 · prompts · skills · 웹 챗 · 심의 좌석 · PC 킷이 함께 읽는다. 「목적 → 묶음 → 기능 MCP」 로 좁힌다.
4. **로드맵 대응** — Skills over MCP(`io.modelcontextprotocol/skills`)로 목적 묶음과 워크플로를 서버가 낸다. MCP Events(`io.modelcontextprotocol/events`)로
   잡 끝 · 새 차수 · 보고서 게시를 밀어 준다. Tasks 는 SDK 가 아직 없어 지켜본다.
5. **cae00 팔로업** — 같은 판이 cae00 에 깔리고, 사내 앱은 공통 계약 · 점검 한 벌 · 앱 주인 요청서로 같은 비전을 따른다.

## 3. 방향(까닭은 context-notes MM-3)

- **두 걸음으로 stateless.** 1단계는 SDK 1.x 그대로 `stateless_http=True`(Python 그대로 · 앱마다 한 줄). 2단계는 SDK 2.x 로 옮겨 새 세대를 같은 자리에서 낸다
  (2.x 는 플래그 없이 두 세대를 다 받는다). 2단계는 Python 3.11 이상과 바뀐 API(이름 · 생성자 · httpx2 · lifespan · 예외 가림)를 다룬다.
- **게이트웨이가 먼저.** 세션 번호에 기댄 것(근거 원장 · 재기동 막기 · 검색 고리)을 사람 · 대화 handle 열쇠로 옮긴 뒤 게이트웨이를 stateless 로 바꾼다.
  게이트웨이 → 앱 호출은 2.x 클라이언트 `mode="auto"` 로 옛 앱 · 새 앱을 다 부른다.
- **판정은 게이트웨이 한 곳.** 읽기 · 쓰기 부류 · 영역 · 목적 · 입구 도구를 게이트웨이가 정해 `/tools-map` 과 노출 사본에 싣고, 쓰는 쪽은 그것을 읽는다.
  쓰는 쪽마다 다른 정책(D-18 · 확인 카드 · 루틴 울타리 · 절차 관문 · 창별 예산)은 모으지 않는다.
- **목적 묶음 정본은 게이트웨이 `tool_purposes.json`(+ 박스 덧씌우기 `.local.json`).** 씨앗은 HE팀 운영자의 workflow · samples 다. 한 표에서 검색 층 · `list_tool_apps(by='purpose')` ·
  보기 `purpose:<key>` · prompts `purpose-<key>` · skill `skill://hwax/<key>/SKILL.md` 를 만든다.
- **Skills over MCP 는 목적 묶음의 내보내기 꼴.** skill 을 받지 못하는 클라이언트(지금 Claude 클라이언트 지원은 확인 안 됨)에는 같은 글을 prompts · 자원 ·
  게이트웨이 도구로 낸다. 워크플로 정본(`infra/pipeline/*.js`)도 skill 로 함께 낸다.
- **Events 는 게이트웨이가 허브.** 확장 `io.modelcontextprotocol/events` 의 poll · stream 을 먼저, webhook 은 바깥으로 나가는 길이라 뒤로 미룬다(서명 · SSRF 막기).
  첫 이벤트는 잡 끝(ste · stcx · DocForge · 심의 · 리스크 · 발표자료) · 새 CAD 차수(자동 파이프라인 `auto_changes`) · RA 게시다.
- **앱 몫은 그 세션에.** 공통 계약 [contract.md](contract.md) 를 함께 보내고, 세션 없는 리포는 사용자 결정에 따른다. 판 고정 · 라운드 규칙을 지킨다.
- **기본값을 바꾸는 것은 그림자 · 측정 뒤.** 검색 · 웹 챗 · 좌석의 순위 변화는 평가셋에서 나빠진 쌍 0 을 보고 켠다. 끄면 지금과 바이트까지 같게 짓는다.

## 4. 마일스톤

| 차례 | 무엇 | 주인 | 재는 것 |
|---|---|---|---|
| **M0 측정 바닥** | 앱별 품질 카드 스크립트(표지 원값 · 설명 길이 · 중복 설명 · 인자 설명 · 중첩 인자 · enum · 지연/크기 백분위) · 감사 원장에 실패 사유 · 점수판이 중첩 인자를 세게 · 도구 수 셋 맞추기 · 보기/prompts 채택 셈을 날마다 남기기 · dev `.env` 의 16K 시절 도구 값 걷기 | 포털(게이트웨이 · 에이전트 서버) | 카드가 dev · cae00 에서 같은 꼴로 나온다 |
| **M1 stateless** | 1단계: 우리 앱 전부 `stateless_http=True`. 게이트웨이의 세션 기댐 떼기 → 게이트웨이 stateless. 2단계: SDK 2.x(dual-era) — 포털 몫 넷 먼저(게이트웨이 · 에이전트 서버 · AI 데이터 허브 · 리스크 앱), 이어 앱 세션 | 포털 · 앱 세션 | 옛 클라이언트(개인 Claude) · 새 클라이언트(2.x Client) 둘 다 tools/list · 호출 · 재기동 뒤 끊김 0 |
| **M2 정밀한 계약** | 공통 계약 아홉 항목(contract.md) · 앱 길목 헬퍼(docstring 「Args:」 → Field 설명) · 게이트웨이 일괄(설명 들여쓰기 걷기 · 쓰기 분류가 확인된 읽기 목록 먼저 · 읽기/쓰기 한 판정) · SmartTwin `_register_direct` 가 카탈로그 스키마를 살리기 | 앱 세션 · 포털 | 인자 설명 0.379 → 0.9 · 표지 100% · 판정 모순 0 · 모름 0 |
| **M3 목적 단위** | `tool_purposes.json` + 덧씌우기 · 검색 목적 층과 작은 고침(쓰기 낱말 · 띄어쓰기 접기 · 표지로 감점) · `list_tool_apps(by='purpose')` · 앱 입구 `entry` · 보기 `purpose:<key>` · prompts · 웹 챗 목적 예산 · 좌석 후보 그림자 · PC 킷 목적 고르기 | 포털 | 목적 쌍 purpose@1 · 앱 입구 app@1 · auto hit@5 0.383 → 0.7 · 턴당 도구 토큰 |
| **M4 Skills · Events** | 게이트웨이 Skills 확장(목적 묶음 · 워크플로 skill, 받지 못하는 클라이언트는 prompts · 자원) · Events 확장(poll · stream — 잡 끝 · 새 차수 · RA 게시) · 자동 파이프라인 감지를 이벤트로 · Tasks 는 SDK 를 지켜본다 | 포털 · 이벤트를 내는 앱 | skills/list · events/poll 이 2.x 클라이언트로 돈다 · 자동 파이프라인이 묻기 없이 새 차수를 받는다 |
| **M5 cae00 팔로업** | 받은 편지함 — 비전 · 받는 차례 · 점검 한 벌(MQ-1 ~ MQ-6) · 박스 덧씌우기 안내 · Python 3.11+ 와 바퀴 꾸러미. 사내 앱 주인 요청서(공통 계약 + 그 앱의 카드 줄) | 포털(글) · 사용자(사내 팀에 건넴) | cae00 카드가 dev 와 같은 꼴로 온다 · 사내 앱 표지 · 인자 설명이 오른다 |

M0 · M1 1단계 · M2 게이트웨이 일괄은 나란히 간다. M3 은 M0 의 카드와 평가셋 위에서, M4 는 M1 2단계(SDK 2.x) 위에서 간다.

## 5. 리포 · 주인

| 리포 | 주인 | 몫 |
|---|---|---|
| HWAXMcpGateway | 포털(이 세션) | 세션 떼기 · dual-era · 판정 한 곳 · 목적 표 · 검색 · 보기 · prompts · Skills · Events · 카드 · 감사 사유 |
| HWAXAgentServer | 포털 | 심의 MCP stateless · 웹 챗 목적 예산 · 좌석 후보 그림자 · venv 3.11+ |
| AIDataHub · HWAXRisk | 포털 | stateless(이미) · SDK 2.x · 인자 설명 · 표지 |
| HWAXPortal | 포털 | PC 킷 목적 고르기 · 보기 화면 · 자동 파이프라인 judge(2.x 예외 가림) · 받은 편지함 |
| StepForge · KooRemapper(DynaForge) · ReportArchive · SignalForge · MXWhitePaper · MaterialTwinWeb · LaminateAnalyzerMCP · WebDesignAgents · DocForge · SmartTwinExplorer · KooSlurm(SmartTwin MCP) · HEAXHub | 그 세션 | contract.md 의 아홉 항목 · stateless 1단계 · SDK 2.x · 이벤트를 내는 앱은 이벤트 |
| ThermalShockMCP · WebResearchMCP · PaperIngest | 열린 세션 없음 | 사용자 결정(context-notes MM-4) |
| 사내 앱(SP 허브 다섯 · ComponentCore · MatNexus · TestScope · ODB 허브 · ARP · FMEA · SIREN · SimFlow 등) | 사내 팀 | 공통 계약 · 그 앱의 카드 줄 — 사용자가 건넨다 |

## 6. 지키는 것

- 이 리포는 공개다 — 내부 주소 · 계정 · 토큰 · 사람 이름 · 과제 이름을 적지 않는다.
- 판 고정 · 라운드 규칙(받은 편지함 · 동결)을 지킨다. 7차 라운드는 87 이 쓴다 — 이 갈래의 cae00 몫은 따로 이름 붙인 글로 내고 87 과 차례를 맞춘다.
- ReportArchive 리포에는 커밋하지 않는다(그 세션 몫).
- 바꾸는 것마다 시험을 먼저 · 전체 회귀 뒤 완료 · 기본값을 바꾸는 것은 그림자 뒤.
- 옛 클라이언트(개인 Claude 의 지금 판)가 끊기지 않는다 — dual-era 는 목표가 아니라 바닥이다.
