# MCP 앱 켜고 끄기 — 관심 없는 앱을 내 허브 목록·검색에서 뺀다

> 2026-09-29 사용자 요청: "mcp 를 등록하면 hwax 하나가 아니라 서브 mcp 각각이 등록되게 할 수 있나 — on/off 가
> 있었으면. 포털에서 관심 없는 기능의 mcp 를 검색 안 되게 끄는 것도 필요". 사실 조사(게이트웨이·포털·클라이언트·
> 웹 챗 네 갈래)와 설계안 비교를 거쳐 사용자가 정했다(context-notes D-1).

## 1단계(이번) — 포털 스위치, 게이트웨이가 그 사람의 개인 MCP 시야에서 숨긴다

| 무엇 | 어디 |
|---|---|
| 끈 앱 목록 저장(사용자별, 권한과 따로) | 포털 `users.hub_muted_apps`(JSON 배열) |
| 내 앱 표·스위치 API | 포털 `GET /auth/access/apps`(표) · `PUT /auth/access/apps/{key}` `{muted: bool}`(앱 하나씩 — 저장소가 잠금 안에서 읽고-고쳐-쓴다, D-6) — 앱 목록은 게이트웨이 `/tools-map` 에서 서버가 만든다 |
| 게이트웨이로 전달 | 포털 `/internal/access/entitlements` 응답에 `muted_apps` 한 칸(기존 60초 캐시를 그대로 탄다) |
| 숨김 | 게이트웨이 PAT 분기가 `x-hwax-muted-apps` 헤더를 싣고, `tools/list`·`search_tools`·`list_tool_apps`·`by='area'` 가 거른다 |
| 즉시 반영 | 스위치를 바꾸면 포털이 게이트웨이 `/conn-invalidate` 를 부르고, 게이트웨이는 그 사람의 권한 캐시도 비운다 |
| 화면 | 토큰 페이지에 "허브에 보일 앱" 표(앱·도구 수·연결·권한·스위치) |

### 규칙(사용자 결정)
- **개인 MCP 클라이언트만** 숨긴다(Claude Code·Desktop·Gemini·Codex 가 쓰는 개인 PAT). 포털 웹 챗(챗 PAT),
  절차 실행기(절차 PAT), 에이전트 서버·심의(GW_TOKEN)는 영향 없다.
- **숨김만** 한다. 이름을 정확히 주면 `invoke_tool` 로 호출된다(끄기는 권한이 아니라 선호).
- 단위는 **게이트웨이 앱**(search_tools 결과의 app). `_gateway`(허브 자체 도구)는 끌 수 없다.
- 새로 붙는 앱은 **켬**이 기본(저장값이 '끈 목록'이라 자연히 그렇다).
- 끔(muted)과 권한 없음(denied)은 **다른 칸**이다 — 모델이 끈 앱을 권한 요청으로 안내하면 안 된다.

### 한계(화면에 적는다)
- 게이트웨이는 목록 변경을 클라이언트에 알리지 않는다(listChanged=false). **열린 Claude 세션의 도구 목록은
  재연결해야** 바뀐다(Claude Code `/mcp` 재연결·재시작, Desktop 완전 종료 후 재시작). `search_tools` 는 바로 바뀐다.
- REST 다리(`rest_catalog`·`rest_call`)는 1단계에서 영향 없다(사이트 키가 앱 키와 다르다).

## 2단계(선택, 나중) — 원하는 앱만 "따로 붙이기"
게이트웨이 `/mcp/<app>` 엔드포인트(그 앱 도구만, 원래 이름) + 토큰 페이지의 단일 앱 등록 스니펫. 앱은
'허브 안'·'끔'·'따로 등록' 중 한 곳에만 있게 한다. 1단계를 써 본 뒤 정한다(D-1).

## 2단계 대신 — 개인 Claude 보기(2026-10-31, docs/request-1029 E-4)
앱별 서버(`/mcp/<app>`)는 하지 않는다 — 도구 이름이 `mcp__hwax-<앱>__X` 로 바뀌어 허용 규칙이 깨지고 서버 항목 · PAT 사본 · 프로세스가 앱 수만큼 는다(D-1).
대신 **한 서버(`hwax`) · 같은 이름**으로 목록 크기만 고르는 보기 셋을 둔다(설계 [`../request-1029/design-e2-e4.md`](../request-1029/design-e2-e4.md) 2절, 결정은
[`../request-1029/context-notes.md`](../request-1029/context-notes.md) C-38 · C-39).

| 보기 | 개인 PAT 의 tools/list |
|---|---|
| 전체(기본) | 지금 그대로 |
| 묶음 | 고른 도구 영역(게이트웨이 `tool_areas.json`)의 도구 + 정본 허브 읽기 도구 다섯 + 허브 자체 도구. 형제 허브 사본은 싣지 않는다 |
| 가벼운 | `search_tools` · `invoke_tool` 둘 |

- **끄기와 같은 길** — 포털 `users.hub_view` → 권한 응답 `view` → 게이트웨이 PAT 분기 → 목록. 같은 면제(웹 챗 PAT · 절차 PAT · GW_TOKEN 은 늘 전체) · 같은 캐시 깨기.
- **끄기와 다른 점** — 끄기는 목록과 `search_tools` 에서 함께 빼지만, 보기는 **목록만** 줄인다(검색 · 부르기 · 이름 · 권한은 그대로). 끈 앱은 어느 보기에서도 빠진다.
  그리고 포털 보기는 연결 머리 `X-HWAX-View: portal` 로 청한 연결에만 얹는다 — 토큰 페이지의 등록 배치 · 명령이 Claude Code · Desktop 에 단다. 머리가 없는 개인
  PAT(내 토큰으로 서버에서 도는 리스크 심사 · 위키 앱, 스크립트)는 늘 전체다 — tools/list 로 도구가 있나를 보는 앱이 사람의 보기를 받으면 도구가 없다고
  읽었다(10-31 반대 검토, [`../request-1029/context-notes.md`](../request-1029/context-notes.md) C-41). 끄기는 종전대로 모든 개인 PAT 에 건다.
- 화면은 토큰 페이지 '허브에 보일 앱' 탭의 표 위다. 연결 머리 `X-HWAX-View`(full · light · bundle:<영역>,… — `portal` 은 사람 설정을 따른다)가 사람 설정을 덮는다 — 리포 `.mcp.json` 은 늘 full 이라
  리포 파이프라인(D-7 의 BY_NAME 자리)은 사람 설정과 상관없이 전체 목록으로 돈다.
- 열린 세션의 목록은 끄기처럼 재연결해야 바뀐다(listChanged 를 알리지 않는다).
