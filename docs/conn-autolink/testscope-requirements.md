# TestScope 가 HWAX 포털에 붙으려면 — 요구사항

> 대상: TestScope 개발·운영 담당 · 2026-10-03 · 출처: HWAX 포털 `docs/conn-autolink/`
> 한 줄 요약: **Report Archive(v0.167.0)와 같은 엔드포인트 다섯 개와 설정 셋**을 갖추면, 포털은 코드 수정 없이 서버 설정만으로
> TestScope 를 ① 타일 SSO ② 사용자별 토큰 자동 연결 ③ Claude·챗 도구 호출(본인 명의)로 붙인다.
> RA 의 구현(`ReportArchive/backend/app/modules/sso/portal.py`, `modules/users/routes.py` 의 `/me/mcp-tokens`)을 그대로 참고하면 된다.

## 0. 무엇이 되는가

| 단계 | 사용자가 겪는 것 | TestScope 에 필요한 것 |
|---|---|---|
| ① 타일 SSO | 포털 앱 목록에서 TestScope 를 누르면 본인 계정으로 들어간다(계정이 없으면 생긴다) | §1 · §2(callback) · §5 |
| ② 토큰 자동 연결 | 포털에 로그인하면 TestScope 개인 토큰이 저절로 발급·갱신된다. 붙여 넣을 것이 없다 | §2(exchange) · §3 · §4 |
| ③ 도구 호출 | Claude Code·포털 챗이 TestScope 도구를 **그 사람 명의로** 부른다 | §6 |

①만, 또는 ①②만 먼저 해도 된다. ②가 없으면 사람이 TestScope 에서 토큰을 발급해 포털 '외부 연결' 에 붙여 넣는 수동 경로가 남는다(§3 만 있으면 된다).

## 1. 포털이 보내는 로그인 토큰(launch JWT) 검증

- 서명: **RS256**, 헤더 `kid`. 공개키는 포털 JWKS(`<포털>/.well-known/jwks.json`, 운영 주소는 포털 운영자가 준다)에서 받는다. 5분 정도 캐시.
- 클레임: `iss = https://hwax.sec.samsung.net` · `aud = testscope` · `scope = launch` · `email`(소문자로 비교) · `name` · `sub` · `groups` ·
  `iat` · `nbf` · `exp`(발급 후 **90초**) · `jti`(1회용).
- 반드시 확인: 서명·`aud`·`iss`·`exp`(시계 오차 30초 정도 허용)·`scope == "launch"`·**`jti` 재사용 거부**(DB 에 넣고 중복이면 401).
- 계정 연결은 **이메일로만**(소문자). 계정이 없으면 만든다(JIT, 설정으로 끌 수 있게 — RA 는 `PORTAL_JIT_CREATE`). 비활성 계정은 403.
- 설정(`.env`): `PORTAL_JWKS_URL`(비어 있으면 §2 의 두 엔드포인트가 **404** — 독립 실행 안전), `PORTAL_ISSUER`(기본 위 값), `PORTAL_AUDIENCE`(기본 `testscope`),
  `PORTAL_JIT_CREATE`(기본 true).

## 2. 엔드포인트 둘 — 같은 검증, 다른 응답

### `POST /api/auth/portal-callback` (브라우저 — 타일 클릭)
- 본문: **form** 필드 `token`(포털이 브라우저에서 자동 POST 한다).
- 성공: TestScope 자체 세션을 세우고 첫 화면으로 303. 실패: 로그인 화면으로 303(`?sso_error=…`).
- 포털은 이 주소를 `/testscope/api/auth/portal-callback` 으로 부른다 — 포털 nginx 가 `/testscope/` 를 떼고 넘긴다(§5).

### `POST /api/auth/portal-exchange` (서버 간 — 토큰 자동 연결의 첫 단계)
- 본문: JSON `{"token": "<launch JWT>"}`. 브라우저 헤더(Origin·쿠키·CSRF)가 **없다** — 이것을 요구하면 안 된다.
- 성공 200: `{"success": true, "data": {"access_token": "<TestScope 세션 토큰>", "token_type": "bearer", "expires_in": <초>}}`
- 실패: 401(검증 실패·재사용) · 403(비활성·JIT 꺼짐) · 404(기능 꺼짐) — 본문 `{"success": false, "message": "<사람이 읽을 이유>"}`.
  포털은 이 숫자로 "TestScope 쪽 포털 연결이 꺼져 있다(404)", "계정이 막혀 있다(403)" 를 사용자에게 그대로 보여 준다.
- 호출마다 접속 이력을 남긴다면 `User-Agent: HWAXPortal-autolink/1` 로 사람 로그인과 가를 수 있다(포털이 그 값을 싣는다).

## 3. `GET /api/me` — 토큰 주인 확인

- 인증: `Authorization: Bearer <§2 세션 토큰 또는 §4 개인 토큰>` **둘 다** 받아야 한다.
- 응답 200: `{"success": true, "data": {"user": {"email": "<소문자 이메일>", "name": "…"}}}` (RA 는 여기에 `memberships`·`home_workspace_slug` 가 더 있지만
  TestScope 는 없어도 된다 — 조직 선택은 RA 만 쓴다).
- 포털은 이 이메일을 포털 계정 이메일과 대조해, 다르면 **저장하지 않는다**(남의 토큰 등록 방지). 이메일이 없으면 등록을 거절한다.
- 401 은 "토큰이 만료·폐기됐다" 로 읽는다.

## 4. 개인 토큰(PAT) — 발급·목록·삭제

| 메서드·경로 | 본문 / 응답 |
|---|---|
| `POST /api/me/mcp-tokens` | 본문 `{"name": "HWAX 포털 자동 연결", "expires_days": 90}`(1~3650, `null` 이면 무기한). 응답 200 `{"success": true, "data": {"token": "<평문 — 이 응답에서 한 번만>", "info": {"id": <int>, "name": "…", "token_prefix": "…", "created_at": "…", "expires_at": "<ISO 또는 null>", "last_used_at": null, "revoked_at": null}}}` |
| `GET /api/me/mcp-tokens` | `{"success": true, "data": [<info>…]}` (평문 없음) |
| `DELETE /api/me/mcp-tokens/{id}` | 200 `{"success": true, "data": null}` · 남의 것·없는 것 404 |

- 세 경로 모두 **§2 세션 토큰과 개인 토큰 둘 다** 받아야 한다 — 포털은 처음 한 번만 교환하고, 그 뒤 갱신(만료 14일 전)은 지금 토큰으로
  새 토큰을 발급한 뒤 옛 id 를 지운다(교환이 남기는 접속 이력·부작용을 매번 만들지 않으려고).
- 토큰 접두사를 정해 알려 달라(RA 는 `rat_`) — 포털 화면 안내에 쓴다. 스코프가 있다면 포털 자동 발급 토큰에 줄 기본 스코프를 정해 달라
  (설계 문서 §4-4 는 '최소 스코프(read 등)'). 쓰기 도구를 Claude 에서 쓰려면 쓰기 스코프도 필요하다.
- 만료·폐기된 토큰은 API 에서 401 로 분명히 거절할 것.

## 5. 경로와 네트워크

- **서브 경로 `/testscope/`** 아래에서 돌 수 있어야 한다(타일 SSO 용). 포털 nginx 가 `/testscope/` 를 떼고 TestScope 로 넘기며
  `X-Forwarded-Prefix: /testscope` 를 붙인다 — 화면 자산·리다이렉트가 이 접두사를 따라야 한다(RA 와 같은 방식).
- **닿아야 하는 방향 셋**: TestScope → 포털 JWKS(§1), 포털 백엔드 → TestScope API(§2~§4), 포털 게이트웨이 → TestScope MCP(§6).
  TestScope 가 윈도우 PC(:8020)에서 돈다면 방화벽·주소 고정이 필요하다(설계 문서 §6-3 미결 항목).
- https 로 연다면 사내 CA 체인을 포털 쪽에 줘야 한다. 사내망 http 가 더 간단하다.

## 6. 도구 호출(Claude·챗) — MCP

- **streamable-http MCP** 엔드포인트(예: `/mcp`). 포털 게이트웨이는 호출마다 `Authorization: Bearer <그 사람의 TestScope 개인 토큰>` 을 실어
  새 세션을 연다(initialize → call_tool) — 세션 상태에 기대지 말 것. 그 토큰 주인 **명의로** 도구를 실행해야 한다(읽기 범위·쓰기 귀속).
- 도구 목록(`tools/list`)은 게이트웨이가 **서비스 자격**(설정에 적는 토큰, 또는 무인증)으로 모은다 — 서비스 자격으로 목록이 나와야 도구가 보인다.
- 토큰 거절은 401 또는 MCP `isError` 로 분명히 돌려줄 것(게이트웨이는 재시도하지 않고 사용자에게 다시 연결하라고 안내한다).
- REST 만 있고 MCP 가 없다면 ③은 별도로 상의해야 한다(게이트웨이 REST 다리는 사이트를 코드로 등록한다).

## 7. 다 됐는지 확인하는 법(TestScope 쪽)

1. `PORTAL_JWKS_URL` 없이 `POST /api/auth/portal-exchange` → **404** (꺼져 있음).
2. 넣고 아무 문자열로 POST → **401**.
3. 포털 운영자가 타일을 켠 뒤 TestScope 타일을 눌러 본인 계정으로 들어가지는지.
4. 포털 '개인 토큰 › 외부 연결' 의 TestScope 카드에서 **자동으로 연결** → '자동 연결됨 · 만료 YYYY-MM-DD' 가 뜨는지.
5. TestScope `GET /api/me/mcp-tokens` 에 'HWAX 포털 자동 연결' 토큰이 하나만 있는지(갱신 때 옛 것이 지워지는지).
