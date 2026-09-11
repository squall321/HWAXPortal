# 전문가 조직도 재편 · HE팀 MCP 페르소나 · 에이전트 심층 보기 — 계획

## 사용자가 말한 것 (2026-09-11)

1. 조직도 폴더를 체계적으로 — **전문 지식 에이전트** 아래 **스마트폰 HW 지식**(신뢰성·디스플레이·기구
   구조…)·**스마트폰 SW 지식**, 그 아래에 전문가. 별도 **플랫폼 에이전트** 폴더.
2. 플랫폼 에이전트 안에 **HE팀** 폴더 — MCP 앱마다 그 도구를 자유자재로 쓰는 페르소나. 선택하고 대화하면
   **정확히 그 MCP 를 위한 사전 지식과 행동**을 한다. 예: laminate analyzer·thermal shock·SignalForge·
   MX White Paper·Material Twin Web·ODB hub·Web Design Agents·Report Archive·StepForge·DynaForge·
   Paper Ingest·Web Research Broker·HWAX 전문가 심의·ARP·HWAX Risk Review.
   ARP·ODB hub 는 dev 에 MCP 가 없어 cae00 에서 만들어야 한다.
3. (추가) 조직도에서 전문가 하나를 **전체 화면으로 깊게** — 설명 전문과 **지식카드 전체·각 카드 내용**.
   지금은 '보유 지식 20건' 제목만 보인다.

순서 — ① 조직도 계층 → ② HE팀 페르소나(선택하면 동작) → ③ 에이전트 심층 보기.

## 조사로 확정된 사실

- 조직도는 프론트 `personaCatalog.ts` 가 키 첫 세그먼트(도메인 코드)로 접는다. 라벨 정본이 없어서
  `DOMAIN_LABEL` 이 프론트에 있다. 쓰는 곳 셋 — PersonaBrowser(챗)·SeatBrowser(심의)·PersonaPicker.
- 전문가 = AIDataHub 에이전트 레코드. 칸 — `system_prompt`(따로 있음)·`description`·`common_tags`·
  `sample_queries`·`response_config`(자유 dict, 비어 있음). 쓰기는 localhost REST 로 인증 없이 된다.
- 챗 '전문가 지정'(pinned_agent)은 `get_agent_session` 의 system_prompt(없으면 description)를 4,000자까지
  역할로 넣고 "agent_search 우선"을 지시하며 지식카드를 미리 조회한다. **앱 도구 바인딩은 별개 경로**
  (pinned_apps)라 지금은 페르소나를 골라도 그 앱 도구가 따라오지 않는다.
- AIDataHub 는 admin system_prompt 뒤에 자기 도구 안내(agent_search…)를 붙인다 — `<!-- no-tool-guide -->`
  표지가 있으면 안 붙인다. HE 페르소나는 이 표지가 필요하다(쓸 도구가 앱 도구다).
- 이미 앱 이름을 단 에이전트 6개 — material-twin-analyst·mx-whitepaper-analyst·market-voc-analyst·
  dynaforge-report·kooremapper-iga·kooremapper-modelmeta. 지식카드 분석가라 '플랫폼 에이전트'에 둔다.
- 상세의 '20건'은 `list_records(limit=20)` 고정값이다. 역할도 description 200자대만 준다.

## 설계

**① 조직도** — 루트(전문 지식 에이전트 / 플랫폼 에이전트) → 분류(스마트폰 HW·SW·공통·업무 / HE팀·앱 지식)
→ 도메인 → 그룹 → 사람. 도메인→분류 표를 `personaCatalog.ts` 에 두고, 모르는 도메인은 **미분류**로 보여
준다(새 도메인이 사라지지 않게). 두 브라우저의 트리·개요를 공용 컴포넌트로 뽑아 한 번만 고친다.

**② HE팀** — 키 `he-<앱>`. 정본은 추적 파일 `infra/personas/he-team.json`(사람이 쓴 앱별 사전 지식·작업
순서·함정) + `infra/scripts/sync-he-personas.py`(게이트웨이 `/tools-map` 에서 그 앱 도구를 영역별로 붙여
AIDataHub 에 upsert). ARP·ODB 는 앱 키 대신 이름 규칙으로 찾아, cae00 에서 같은 스크립트를 돌리면 생긴다.
`response_config.mcp_apps` 로 앱을 묶고, 에이전트서버가 페르소나를 고르면 그 앱 도구를 자동 바인딩하고
"agent_search 우선" 대신 "이 앱 도구 우선"으로 지시한다. 심의 자동 좌석 추천에서는 뺀다(도구 운영자라
도메인 좌석을 밀어낸다) — 조직도에서 사람이 고르는 건 된다.

**③ 심층 보기** — 전체 화면 한 명: 역할 전문(system_prompt)·예시 질문·태그, 지식카드 **전체**(페이지·검색),
카드를 누르면 **본문**. 에이전트서버에 목록·본문 엔드포인트, 포털 프록시.

## 범위 밖

- ARP·ODB hub 의 **사전 지식 문구**(dev 에 없어 도구를 모른다) — 스크립트가 도구 목록으로 뼈대를 만들고,
  문구는 cae00 에서 보강한다.
