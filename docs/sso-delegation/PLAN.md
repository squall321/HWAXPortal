# 하위 서비스 계정·토큰 자동 연결 — 계획

> 2026-10-03 · 요청: "레포트 아카이브나 테스트스코프 같은 것도 계정이랑 토큰이 다 이어지게. SSO 가 되니까."
> 범위 결정(사용자): **환경설정은 서버 쪽에서 사람이 한다, 코드는 여기서 고친다.** TestScope 쪽에 필요한 것은
> [testscope-requirements.md](testscope-requirements.md) 로 따로 넘긴다.

## 1. 지금(조사 2회 × 반박 검증, 2026-10-03)

| | 브라우저 SSO(타일 → 본인으로 로그인) | 토큰(Claude·챗·심의가 본인 명의로 호출) |
|---|---|---|
| RA | 코드는 양쪽에 있다(포털 jwt-handoff ↔ RA v0.167.0 portal-callback). RA 서버 `.env` 의 `PORTAL_JWKS_URL` 이 비면 꺼진다 — 운영에서 켜졌는지는 미확인 | **수동.** 사람이 RA 에서 `rat_` 를 발급해 포털 '외부 연결' 에 붙인다. 안 붙이면 거부(09-29 결정), 90일 뒤 만료 |
| TestScope | dev 에 없음(cae00 에만). 타일 정의도 없다 | 포털 연결 장치가 RA 로 박혀 있어(포털 SERVICES·화면·게이트웨이 표) **불가** |

SSO 로그인이 하위 서비스 토큰을 만들지 않는 이유는 단순하다 — 그 일을 하는 코드가 없다. RA 쪽에는 필요한 엔드포인트가 **이미 다 있다**.

## 2. 목표

포털에 로그인한 사람은(그 서비스 권한이 있으면) **아무것도 붙여 넣지 않아도** Claude Code·웹 챗·심의가 RA 를 본인 계정으로 쓴다.
TestScope 도 같은 틀로, TestScope 가 [계약](testscope-requirements.md)을 갖추고 서버 설정을 켜면 코드 수정 없이 붙는다.
'신원 있는 호출은 본인 토큰으로만'(RA 재연결 D-13, 사용자 결정)은 그대로 — 자동 연결은 그 '본인 토큰' 을 사람 손 없이 채울 뿐이다.

## 3. 방법 — RA 코드는 한 줄도 안 고친다

```
포털 로그인(SSO·이메일) ─┐
게이트웨이 첫 호출(미연결) ┼─▶ ensure(email, service)
'자동으로 연결' 버튼     ─┘        │  권한(plat:<service>)·정지·사용자 거절(opt-out) 확인, 사람별 잠금, 실패 백오프
                                   ├─ 연결 없음/만료 → ① 포털이 launch 토큰을 서버에서 직접 서명(aud=<service>)
                                   │                  ② POST {base}/api/auth/portal-exchange {token} → 서비스 세션 JWT
                                   │                  ③ GET  {base}/api/me  → 이메일 대조(포털 이메일과 다르면 저장 안 함)·조직 후보
                                   │                  ④ POST {base}/api/me/mcp-tokens {name, expires_days:90} → 개인 토큰 + id
                                   │                  ⑤ 저장(source=auto, remote_id, expires_at) → 게이트웨이 캐시 무효화
                                   └─ 만료 14일 전 → 회전: 지금 토큰으로 ④ 새로 발급 → 저장 → DELETE 옛 id(교환 없음)
```

- **교환은 처음 한 번만.** RA 는 교환마다 접속 이력에 '포털 로그인' 을 남기고 SAML 부서 힌트(sso_profile)를 덮어쓴다 — 로그인마다
  교환하면 RA 통계가 부풀고 부서 힌트가 지워진다. 회전은 토큰 자신으로 한다(RA 의 /api/me/mcp-tokens 는 PAT 로도 열린다).
- **직접 등록한 토큰을 이긴다/덮지 않는다.** 사람이 붙인 토큰(source=manual)은 자동이 손대지 않는다.
- **사람이 끊으면 자동도 멈춘다.** '해제' 는 opt-out 을 남긴다(다시 켜는 버튼이 있다). 자동 토큰을 끊으면 서비스 쪽 토큰도 지운다.
- **정지하면 회수.** 관리자가 사람을 정지하면 자동 토큰을 서비스에서 지우고, 내부 조회가 정지된 사람에게 토큰을 내주지 않는다.
- **저장은 암호화.** connections.token 은 Fernet 으로 감싼다(키 `secrets/jwt/conn.fernet`, 등록된 비밀 디렉터리 — 백업·미러 대상 아님).
  옛 평문 행은 기동 때 한 번 감싼다. 키를 잃으면 토큰이 '없음' 이 되고, 자동 연결이 다시 만든다(직접 등록분은 다시 붙여야 한다).
- **권한 없는 사람은 계정을 만들지 않는다.** RA 는 모르는 이메일이면 JIT 로 계정을 만든다 — 그래서 `plat:<service>` 가 있는 사람만.

## 4. 계약(구현이 따르는 정본)

### 4-1. 포털 백엔드

| 무엇 | 어디 |
|---|---|
| 서비스 표 `ConnService(key,label,audience,grant,token_hint,workspaces,base_url)` | `app/auth/conn_services.py`(새) — reportarchive(base=RA_BASE_URL), testscope(base=TESTSCOPE_BASE_URL, 비면 이 박스에 없음) |
| 엔진 `ensure / rotate / revoke_auto / revoke_all_auto / login_task / last_error` | `app/auth/conn_autolink.py`(새) |
| 저장 — connections 에 `source·remote_id·expires_at·updated_at`, `connection_optouts` 표, 토큰 암호화 | `app/auth/user_store.py` |
| 라우트 일반화 `/auth/connections[/{service}[/auto|/workspaces|/workspace]]`, 내부 조회의 자동 연결 | `app/auth/routes/connections.py` |
| 로그인 훅(BackgroundTask) | `routes/session.py complete_login` · `routes/local.py login` |
| 정지 훅 | `routes/local.py set_user_status` |
| 그 밖의 소비처 | `agent/routes.py`(PPT 가져오기 전 ensure) · `procedures/routes.py`(옛 '서비스 계정 폴백' 문구) |
| 설정 | `CONN_AUTO_LINK`(true) · `CONN_PAT_DAYS`(90) · `CONN_ROTATE_DAYS`(14) · `CONN_KEY_PATH` · `CONN_LOOKUP_WAIT_S`(6) · `TESTSCOPE_BASE_URL`('') |
| 권한·타일 | access.yaml `plat:testscope`(hide_unless_routed) · systems.yaml testscope jwt-handoff 타일(라우트가 있을 때만 켜짐 — registry 변경) |

`GET /auth/connections` 응답(화면이 쓰는 정본):
```json
{"services": [{"key": "reportarchive", "label": "Report Archive", "token_hint": "rat_…", "workspaces": true,
               "auto_available": true, "connected": true, "source": "auto", "tail": "abcd", "workspace": "dev",
               "created_at": 1790000000, "expires_at": 1797776000, "optout": false,
               "last_error": {"kind": "disabled", "message": "…", "at": 1790000000} }],
 "reportarchive": {"tail": "abcd", "workspace": "dev", "created_at": 1790000000} }
```
(`reportarchive` 최상위 키는 옛 화면 호환 — 새 dist 가 먼저 뜬 창·옛 dist 를 든 탭.)

`GET /internal/connections/{service}?email=` (게이트웨이 전용, 공유 시크릿) — 종전 계약 그대로(200 `{token, workspace}` · 404 · 403 · 503)에
더해: 사람이 정지면 404, 연결이 없거나 만료면 **자동 연결을 시도해 최대 `CONN_LOOKUP_WAIT_S` 기다린 뒤** 결과를 준다(못 기다리면 404 —
작업은 이어서 돌고, 끝나면 게이트웨이 캐시를 비운다). 만료가 가까우면 회전을 뒤에서 걸고 지금 토큰을 준다.

### 4-2. 게이트웨이(HWAXMcpGateway)

- 백엔드→서비스 표 = 코드 기본 `{"reportarchive": "reportarchive"}` ∪ `gateway_config.json` 의 `portal.conn_backends`(박스별, 사람이 넣는다).
  TestScope 는 **명시적으로 넣을 때만** 본인 토큰 필수로 바뀐다 — 지금 서비스 계정으로 돌고 있을 수 있는 cae00 을 배포만으로 막지 않는다.
- 서비스별 라벨·조직 헤더(RA 만 `X-Workspace-Slug`)·거부 문구(새 위치 `/tokens?tab=connect`, "포털에 한 번 로그인하면 자동으로 연결").
- `provision-config.sh --force` 가 `portal.conn_backends` 를 이어받는다(09-29 api_base 사고와 같은 모양을 막는다).

### 4-3. 화면

'개인 토큰 › 외부 연결' 탭이 서비스마다 카드 — 상태(자동 연결됨 · 만료일 / 직접 등록 · 끝자리 / 연결 안 됨 + 이유), '자동으로 연결',
'해제', 접어 둔 '직접 토큰 붙여넣기', RA 만 '보고서를 저장할 조직'. 인라인 스타일 금지(ESLint).

## 5. 서버 쪽에서 사람이 할 일(코드 밖) — [server-setup.md](server-setup.md)

RA 서버 `.env` 의 `PORTAL_JWKS_URL`(RA 담당) · cae00 `infra/.env` 의 `RA_HOST`(이미 있으면 그대로) · TestScope 를 켤 때
`backend/.env TESTSCOPE_BASE_URL`·`routes.local.env testscope=`·게이트웨이 `testscope` 백엔드와 `portal.conn_backends`.

## 6. 하지 않는 것

- RA·TestScope 코드 수정(RA 리포는 hands-off, TestScope 소스는 여기 없다 — 요구사항 문서로 넘긴다).
- 서비스 계정(`RAT_TOKEN`) 정리 — 신원 없는 내부 호출 몫은 그대로.
- 포털 로그아웃 때 토큰 회수 — 로그아웃해도 Claude Code 는 계속 쓴다(정지만 회수).
