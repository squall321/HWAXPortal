# 새 MCP 온보딩 체크리스트 — 진입 구조가 자동 흡수하는 것과 아닌 것

새 MCP 백엔드를 붙일 때 이것만 지키면 진입 구조(search_tools·invoke_tool·챗 관련도
선택)가 나머지를 자동으로 흡수한다. 어기면 조용히 깨지는 자리들이다.

## 이름 규약 (가장 중요 — 전부 접두사 기반 자동화에 걸린다)

- [ ] **읽기 도구는 `list_/get_/search_/find_/describe_/compare_` 로 시작** —
      심의 자유조회 허용(_FREE_ALLOW)·게이트웨이 캐시(_CACHEABLE)가 자동 적용된다.
- [ ] **쓰기 도구는 위 접두사를 절대 쓰지 않는다** — 읽기 접두사를 단 쓰기는 캐시에
      걸려 TTL 동안 무음 드롭된다(실사고: report_ingest → _CACHE_DENY 로 땜질).
- [ ] **파괴·제어 도구는 `delete_/remove_/cancel_/purge_/destroy_` 또는
      `*_control/*_set_state` 로 짓는다** — invoke_tool(범용 실행기) 차단이 이 패턴
      기반이라, `reset_x`·`wipe_x` 같은 이름은 그물을 빠져나간다. 새 패턴이 필요하면
      게이트웨이 _INVOKE_DENY_* 에 같이 추가.
- [ ] 다른 백엔드와 도구 이름이 겹치는지 확인 — 게이트웨이가 충돌만 프리픽스를 붙여
      이름이 바뀐다(gotcha '도구 이름 충돌').

## 설명(description) 품질

- [ ] 첫 문장에 "언제 이 도구를 쓰는가"(입구 판단 기준). RA 사례의 교훈 — 설명이
      길어도 입구 안내가 없으면 모델이 헤맨다.
- [ ] 도구가 10개를 넘으면 자기 사용법 도구(get_guide 패턴)를 고려하고, 조회 입구
      1~2개를 정해 다른 도구 설명에서 그리로 안내한다.
- [ ] 한국어 도메인 용어가 새로 생기면 게이트웨이 search_tools 의 _SYN(한→영 동의어)에
      한 줄 추가 — 도구 이름이 영어라 이게 검색 품질을 좌우한다.

## 배선 (자동이지만 확인)

- [ ] heax-hub 앱: 매니페스트 `mcp:{}` 만 있으면 레지스트리 폴링이 발견한다.
      config 백엔드: gateway_config.json 항목 + `./start.sh restart`.
- [ ] **배포 확인은 소스가 아니라 게이트웨이 `tools/list`(또는 list_tool_apps)로** —
      앱 소스에 있어도 배포 SIF 가 낡으면 안 뜬다(gotcha '배포 안 된 도구').
- [ ] 사용자별 데이터를 다루는 앱이면 위임 배선 — heax 계열은 per_user_sso, 외부
      서비스는 PORTAL_CONN_BACKENDS(RA 방식: 사용자가 토큰 등록).
- [ ] Claude Code 마찰 줄이려면 읽기 도구를 포털 .claude/settings.json 사전 허용에 추가(선택).

## cae00

- [ ] SIF/코드 배포 경로(update-all §2 또는 앱별) + 게이트웨이 config 프로비저닝.
- [ ] 반영 후 cae00 게이트웨이 list_tool_apps 로 앱 status=ok 확인.
