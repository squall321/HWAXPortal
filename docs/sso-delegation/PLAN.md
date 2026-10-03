# 하위 서비스 사람별 연결 — RA 는 ste 방식 준비, TestScope 는 토큰 등록

> 2026-10-03 · 요청: "레포트 아카이브나 테스트스코프도 계정이랑 토큰이 다 이어지게" → "다 그냥 ste 처럼 연결하고 싶다" →
> "RA 도 ste 방식으로 바꾼대". 범위(사용자): **서버 설정은 cae00·각 서버에서 사람이 한다, 코드는 여기서 고친다.**
> RA·TestScope 코드는 여기서 수정하지 않는다(사용자 결정). RA 쪽에 넘길 것은 [ra-request.md](ra-request.md).
> **개정(2026-10-03, D-15): TestScope 는 다른 조직의 포털이라 ste 방식이 아니라 구 RA 방식(사람이 그쪽 토큰을 포털에 등록)으로 붙인다** —
> TestScope 코드 수정이 필요 없다(개인 토큰·`/api/auth/me` 가 이미 있다). 아래 TestScope ste 방식 서술은 걷었다.
> 이전안(포털이 토큰을 발급·저장·갱신하는 '자동 연결')은 걷었다 — 결정 이력은 context-notes D-1~D-12.

## 1. ste 방식이란

| 길 | 무엇 | 포털이 쥐는 것 |
|---|---|---|
| Claude·챗·심의(게이트웨이) | 게이트웨이 `heax_registry.per_user_sso.<백엔드>` — 공유 비밀로 서비스의 `POST /api/auth/sso` 에 "이 사람"을 알려 그 사람 토큰을 받아(12시간 캐시) 그 명의로 부른다. 401 이면 한 번 다시 받는다. 받지 못하면 **거부**(서비스 계정으로 강등하지 않는다) | 없음 |
| 포털이 서비스를 직접 부르는 곳(RA PPT 가져오기) | 포털이 같은 비밀로 같은 엔드포인트를 부른다(`/ste/credential` 과 같은 선례) | 없음 |
| 브라우저 | 표준 jwt-handoff 타일(launch JWT → 서비스 `portal-callback`). ste 의 브라우저 중계는 헤드노드가 JWKS 를 못 받아서 생긴 예외라 따르지 않는다 | 없음 |

`POST /api/auth/sso` 계약(ste·HWAX Risk·옛 RA `sso/heax.py` 와 같다):
요청 헤더 `X-Heax-Gateway-Secret`(서비스 전용 공유 비밀) · `X-Heax-User-Email`(필수) · `X-Heax-User-Name`(선택, 퍼센트 인코딩) · `X-Heax-Client`(`gateway`·`hwax-portal` — 발급이 서로를 회수하지 않게 가른다).
응답 200 JSON 안 어딘가의 `access_token`(게이트웨이는 깊이 찾는다) · `expires_in`. 비밀이 비면 404(꺼짐), 틀리면 401, 정지·JIT 꺼짐 403.

## 2. 고치는 것(코드 — 이 박스)

### 2-1. 게이트웨이(HWAXMcpGateway)
- `per_user_sso.<앱>.strip_headers`(목록) — 서비스 설정에만 맞는 헤더를 사람별 호출에서 뺀다. RA 는 `["X-Workspace-Slug"]`(서비스 부서가 남으면 남의 부서로 읽고 쓴다).
  **했다**(시험 포함).
- 안내 문구의 옛 페이지 이름('API 토큰') → '개인 토큰 › 외부 연결'·'개인 토큰 › 허브에 보일 앱'. **했다**.
- `provision-config.sh` — ste 와 같은 규칙으로 `RA_SSO_SECRET` → `per_user_sso.reportarchive`(sso_url = `RA_SSO_URL` > 직전 config > 기본, client `gateway`,
  strip_headers X-Workspace-Slug). TestScope 는 위임이 아니라 포털 연결 경로(`PORTAL_CONN_BACKENDS`)이고 백엔드는 `TESTSCOPE_MCP_URL` 로 만든다(D-15).

### 2-2. 포털(HWAXPortal)
- 설정 `RA_SSO_SECRET`(빈 값 = RA 는 종전 '토큰 등록' 방식) · `RA_SSO_URL`(빈 값 = `RA_BASE_URL` + `/api/auth/sso`).
  `infra/.env` → `start.sh --env` → 포털. **자동 생성하지 않는다** — RA 쪽이 준비되기 전에 생기면 게이트웨이가 위임을 켜고 그 순간 RA 호출이 거부로 바뀐다.
- `app/auth/ra_sso.py` — 그 사람 RA 토큰을 받는 도우미(`ste_credential.py` 모양, 짧은 메모리 캐시). PPT 가져오기가 이것을 쓴다(없으면 등록 토큰).
- 절차 사전검사 — `RA_SSO_SECRET` 이 있으면 '연결 없음' 경고를 내지 않는다.
- `GET /auth/connections` 에 `reportarchive_mode: "sso" | "token"` — 화면이 '자동(포털 로그인으로)' 과 '토큰 등록' 을 가른다.
- update-all — `RA_SSO_SECRET` 을 infra/.env 에서 읽어(STE 와 같은 줄) provision 에 넘기고 `RA_SSO_URL` 을 RA_BASE_URL 에서 유도한다.
  게이트웨이 provision.env 에 `TESTSCOPE_MCP_URL` 이 있으면 기대 목록에 testscope.
- TestScope 타일(jwt-handoff, `hide_unless_routed` — `testscope=` 라우트가 있는 박스에서만) · 권한 `plat:testscope`. **했다**(registry·schema·yaml).
- 화면 — '외부 연결' 의 RA 카드: `sso` 면 "포털 로그인으로 본인 명의 — 등록할 것 없음, 보고서는 RA 에서 고른 내 부서에" 만 보이고 붙여넣기·조직 고르기는 숨긴다.
- 배치파일 — `claude` 명령이 없어도 Claude Code 사용자 설정에 등록(D-9), 자리는 Claude Code 와 같은 규칙(D-11).

### 2-3. TestScope — 구 RA 방식(토큰 등록), TestScope 코드 수정 없음
- 포털 '개인 토큰 › 외부 연결' 에 TestScope 카드 — 사용자가 TestScope 에서 발급한 `tsc_pat_…`(범위 read 필수, 쓰기는 equipment:write·catalog:write)를 붙인다.
  포털이 `TESTSCOPE_BASE_URL` 의 `GET /api/auth/me`(맨 모델 `email`)로 주인을 확인해 포털 이메일과 같을 때만 저장한다(RA 와 같은 fail-closed).
- 게이트웨이 `PORTAL_CONN_BACKENDS` 에 testscope — 등록된 본인 토큰으로만 부르고, 없으면 거부·연결 안내(조직 헤더 없음). 백엔드는 `TESTSCOPE_MCP_URL`(provision.env)로 만든다.
- 타일은 그쪽 주소로 바로 여는 외부 링크 — 주소는 `backend/config/systems.local.yaml` 의 `testscope: {url: …}`, 없으면 숨긴다.
- TestScope 쪽에 필요한 것은 코드가 아니라 운영 설정뿐 — 게이트웨이 박스에서 MCP(:8022)에 닿게(server-setup B).

## 3. 서버 쪽(사람) — [server-setup.md](server-setup.md)

RA: RA 담당이 [ra-request.md](ra-request.md) 대로 고친 뒤 비밀을 RA·포털(`infra/.env RA_SSO_SECRET`)에 같은 값으로(그 전까지는 토큰 등록 그대로).
TestScope: 포털 `backend/.env TESTSCOPE_BASE_URL` · `systems.local.yaml testscope.url` · 게이트웨이 `provision.env TESTSCOPE_MCP_URL`, TestScope MCP 를 게이트웨이 박스에서 닿게. 그다음 update-all.

## 4. 하지 않는 것

- 포털이 하위 서비스 토큰을 발급·저장·갱신하는 것(이전안 — 걷었다).
- 포털 화면에서 RA 조직을 고르는 것(ste 방식에서는 RA 가 그 사람의 홈 부서로 정한다 — ra-request §3).
- 공유 비밀을 서비스끼리 묶는 것(서비스마다 따로. HEAXHub `gateway_shared_secret` 재사용 금지 선례).
