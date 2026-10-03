# TestScope — HWAX 포털에 붙이기(ste 방식 위임 + 타일 SSO) 요청

> 대상: TestScope 개발 담당 · 2026-10-03 · 보낸 쪽: HWAX 포털(`docs/sso-delegation/`)
> 요약: TestScope 에 **엔드포인트 둘**(`POST /api/auth/sso`, `POST /api/auth/portal-callback`)과 **접두 경로(`/testscope/`) 대응**을 넣어 주세요.
> 포털·게이트웨이 쪽은 준비돼 있습니다 — 서버 설정 몇 줄로 켭니다([server-setup.md](server-setup.md) B).
> 아래 파일 위치는 TestScope `d900254`(v0.49.2) 기준으로 확인한 것입니다.

## 0. 무엇이 되는가

| 길 | 사용자가 겪는 것 | 필요한 것 |
|---|---|---|
| Claude Code·포털 챗·심의 | TestScope 도구를 **그 사람 명의로** 쓴다. 토큰을 붙여 넣을 것이 없다 | §1 · §5 |
| 브라우저 | 포털 앱 목록의 TestScope 타일을 누르면 본인 계정으로 들어간다(처음이면 계정이 생긴다) | §2 · §3 · §4 |

포털 게이트웨이는 ste·HWAX Risk·DynaForge 와 **같은 계약**으로 부릅니다 — 공유 비밀로 "이 사람" 을 알려 그 자리에서 토큰을 받아 12시간 쓰고,
401 이면 한 번 다시 받습니다. 포털은 TestScope 토큰을 저장하지 않습니다.

## 1. `POST /api/auth/sso` — 게이트웨이 위임(서버 간)

| | 내용 |
|---|---|
| 요청 헤더 | `X-Heax-Gateway-Secret`(TestScope 전용 공유 비밀) · `X-Heax-User-Email`(필수 — 포털이 인증한 사람) · `X-Heax-User-Name`(선택, **퍼센트 인코딩** — 한글 이름) · `X-Heax-Client`(`gateway`) |
| 응답 200 | `{"access_token": "<tsc_pat_…>", "token_type": "bearer", "expires_in": <그 토큰 만료까지 초>}` — 맨 모델(TestScope 관례) 그대로. 게이트웨이는 응답 안 `access_token` 을 찾아 쓴다 |
| 오류 | 비밀이 비어 있으면 **404**(꺼짐) · 비밀 불일치 401 · 대기(TSC-AUTH-0008)·정지/삭제(0002) 403 · 이메일 없음 400 |
| 설정(`backend\.env`) | `HEAX_SSO_SECRET`(빈 값·32자 미만 = 꺼짐) · `HEAX_SSO_JIT_CREATE`(기본 true) · `HEAX_SSO_SCOPES`(기본 `read,equipment:write,catalog:write`) · `HEAX_SSO_PAT_DAYS`(기본 1) |

- **사람 세션이 아니라 기계 자격(PAT)을 내주세요.** TestScope 는 PAT 로 들어온 쓰기를 '후보' 로 다룹니다(ADR 0009, `shared/request_context.get_actor_token`) —
  AI 가 하는 쓰기도 그 규칙을 그대로 타야 합니다. 기존 PAT 발급 서비스(`app/modules/auth/services.py` 의 토큰 생성)를 서버 안에서 부르면 됩니다.
- 토큰 이름 `HWAX 게이트웨이(<client>)`, 수명 `HEAX_SSO_PAT_DAYS`일(게이트웨이 캐시 12시간보다 길게), 범위 `HEAX_SSO_SCOPES`(범위는 좁힐 뿐 그 사람 권한이 그대로 걸린다).
  **발급할 때 같은 이름의 살아 있는 직전 토큰을 회수**해 주세요 — 안 그러면 하루에 몇 개씩 쌓이고, 게이트웨이가 쥔 옛 토큰도 살아 있습니다.
- 사람 찾기는 `lower(User.email)` 일치(로그인 ID 가 이메일이 아닐 수 있으니 `@` 를 요구하지 않음). 없으면 JIT(켜져 있을 때): `status=active`,
  `display_name` = 이름 헤더(없으면 이메일 앞부분, 100자), 비밀번호는 **아무도 모르는 난수의 해시**(`scripts/mcp_probe_account.py` 선례 — `password_hash` 가 NOT NULL),
  `must_change_password=False`, 소속 없음(읽기 위주 — 쓰기는 부서가 정해진 뒤). 계정 생성 감사 기록이 있으면 같이 남겨 주세요.
- 비밀 비교는 **상수 시간**(`hmac.compare_digest`), 비밀·토큰은 로그에 남기지 않기. 접속 이력에서 갈라 보이게 `shared/access_log.py` 의 action 매핑에
  `'/auth/sso'` → `SSO_DELEGATE` 정도를 더하고, 엔드포인트에서 `request.scope['tsc_user_id']` 를 넣어 주세요(지금 로그인 행은 user_id 가 비어 남습니다).
- 요청 본문이 없는 POST 라 `Request` 기반 모델 규칙(`tests/architecture/test_request_schemas.py`)과는 부딪히지 않습니다.

## 2. `POST /api/auth/portal-callback` — 타일 SSO(브라우저)

- 본문: **form** 필드 `token`(포털이 브라우저에서 자동 POST — `python-multipart` 는 이미 있음).
- 토큰: 포털 launch JWT — **RS256**·헤더 `kid`, 공개키는 포털 JWKS(`<포털>/.well-known/jwks.json`). 클레임 `iss=https://hwax.sec.samsung.net` ·
  `aud=testscope` · `scope=launch` · `email` · `name` · `sub` · `groups` · `iat` · `nbf` · `exp`(발급 후 **90초**) · `jti`.
  반드시 확인: 서명(RS256 고정)·`aud`·`iss`·`exp`(오차 30초)·`scope == "launch"`·**`jti` 1회용**(새 표 — 예 `sso_used_jti`, 마이그레이션 `0051_…`, `app/all_models.py` 등록).
- 사람 찾기·JIT·상태 판정은 §1 과 같게.
- 성공: 기존 세션 발급(`services.issue_session`) → refresh 쿠키 → **303 `{prefix}/`**(화면은 뜰 때 `POST /api/auth/refresh` 로 세션을 되살리므로 화면 쪽 변경 없이 로그인된다).
  실패: 303 `{prefix}/login?sso_error=<짧은 한국어 이유>` — 'JWKS 에 못 닿음' 과 '토큰이 틀림' 과 '계정 상태' 를 갈라 주세요(사람이 할 일이 다르다).
- 설정: `PORTAL_JWKS_URL`(빈 값 = **404**, 독립 실행 안전) · `PORTAL_ISSUER`(기본 위 값) · `PORTAL_AUDIENCE`(기본 `testscope`) · `PORTAL_JIT_CREATE`(기본 true).
- 의존성: `backend/requirements.txt` 에 **`cryptography`(+ `cffi`·`pycparser`) 고정**이 필요합니다 — PyJWT 의 RS256·`PyJWKClient` 가 그것 없이 안 돕니다(지금 목록에 없음,
  오프라인 wheel 묶음이 이 파일로 만들어짐).
- 참고 구현: ReportArchive `backend/app/modules/sso/portal.py`(같은 계약, 같은 포털). 다만 TestScope 는 세션이 refresh 쿠키라 RA 의 `#sso_token=` 대신 쿠키 + 303 이 맞습니다.

## 3. 접두 경로 `/testscope/`

포털 nginx 는 `/testscope/` 를 떼고 TestScope(`:8020/`)로 넘기며 `X-Forwarded-Prefix: /testscope` 를 붙입니다. 지금 TestScope 는 뿌리에서만 돕니다 —
화면 자산·API·라우터·쿠키가 전부 `/` 기준이라(아래), 포털 아래에서 열면 `/api/…` 가 **포털의 API 로** 갑니다(오류도 없이).

| 자리 | 지금 | 바꿀 것 |
|---|---|---|
| `backend/app/main.py:97-126` SPA catch-all | `index.html` 그대로 | `X-Forwarded-Prefix`(형식 검사: `^/[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$`, 64자, 아니면 무시)로 `<base href="{prefix}/">` 를 `<head>` 바로 뒤에(접두사가 없으면 `<base href="/">`) |
| `backend/app/modules/auth/routes.py:37` `COOKIE_PATH="/api/auth"` | 고정 | 쿠키 설정·삭제 둘 다 `{prefix}/api/auth`(login·refresh·logout·portal-callback) — 삭제 경로가 다르면 로그아웃이 안 된다 |
| `frontend/vite.config.ts` | `base` 없음(`/`) | `base: './'` — 한 빌드가 직결(`:8020/`)과 포털 아래 둘 다에서 돈다(경로를 빌드에 굽지 않기) |
| `frontend/src/routes/router.tsx:108` | basename 없음 | `<base>` 에서 읽은 접두사를 basename 으로 |
| `frontend/src/shared/api/client.ts:13` `BASE='/api'` | 뿌리 절대 | 접두사 + `/api` |
| 그 밖의 뿌리 절대 주소 | — | 첨부 내려받기·미리보기, `window.location` 이동 등을 같은 도우미로(감사 필요) |

접두사가 없으면 오늘과 **똑같이** 돌아야 합니다(직결 사용자·MCP 왕복 CI).

## 4. 로그인 화면

`frontend/src/modules/auth/LoginPage.tsx` 가 `?sso_error=` 를 보여 주게(지금은 `location.state.from` 만 읽음). 글자로만 그리기(HTML 금지),
"포털에서 다시 들어오세요" 한 줄.

## 5. MCP — 게이트웨이가 닿게

- 포털 게이트웨이(cae00)가 TestScope MCP(`:8022/mcp`, streamable-http)에 닿아야 합니다 — `.env` 의 `MCP_HOST`·`MCP_ALLOWED_HOSTS`(배포.md MCP 절).
  Host 는 포트까지 글자 그대로 비교되니 게이트웨이가 부르는 주소 그대로 넣어야 합니다.
- 게이트웨이는 호출마다 `Authorization: Bearer <§1 토큰>` 을 실어 새 세션을 엽니다(MCP 서버가 그대로 REST 로 나르는 지금 구조 그대로면 됩니다).
- `tools/list` 는 토큰 없이 됩니다(지금 그대로) — 게이트웨이는 그것으로 도구를 모읍니다.

## 6. 문서·릴리스(그쪽 관례)

ADR 0010(포털 연결: ste 방식 위임·타일 SSO·JIT 와 승인제의 충돌·접두 경로), README·배포.md(새 `.env` 키 — 배포가 옛 `.env` 를 들고 오므로 **서버에 손으로**),
화면 안 가이드, OpenAPI·타입 재생성(CI 「생성 타입 최신성」), 버전(기능 = minor).

## 7. 다 됐는지 확인(TestScope 쪽)

1. `HEAX_SSO_SECRET` 없이 `POST /api/auth/sso` → 404 · 넣고 비밀 없이 → 401 · 맞는 비밀 + 이메일 → 200 `access_token`(그 토큰으로 `GET /api/auth/me` 가 그 사람).
2. 같은 요청을 두 번 → 토큰 목록에 `HWAX 게이트웨이(gateway)` 가 **하나만** 살아 있다.
3. `PORTAL_JWKS_URL` 없이 `POST /api/auth/portal-callback` → 404 · 넣고 아무 문자열 → 303 `…/login?sso_error=…`.
4. `X-Forwarded-Prefix: /testscope` 로 `GET /` → `<base href="/testscope/">` · 접두사 없이 → `<base href="/">`, 직결 화면이 그대로 뜬다.
5. 포털 운영자에게 **§1 비밀과 같은 값**을 주세요(포털 `infra/.env` 의 `TESTSCOPE_SSO_SECRET`). 안전한 경로로.
