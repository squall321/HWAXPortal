# Report Archive — HWAX 포털 사람별 위임(ste 방식) 되살리기 요청

> 대상: Report Archive 개발 담당 · 2026-10-03 · 보낸 쪽: HWAX 포털(`docs/sso-delegation/`)
> 요약: 09-26 `4a96cef` 에서 걷어낸 **`app/modules/sso/heax.py`(POST /api/auth/sso)를 되살려 주세요.** 거기에 한 가지만 더 —
> **`X-Workspace-Slug` 없이 온 위임 토큰 요청은 그 사람의 홈 부서로 처리.** 브라우저 타일 SSO(portal-callback, jwt-handoff)는 지금 그대로 둡니다.

## 왜 다시 필요한가

포털 담당이 "하위 서비스 연결은 다 ste 처럼" 으로 정했습니다. Claude Code·포털 챗·심의가 RA 를 부를 때 **포털 게이트웨이가 공유 비밀로
그 사람의 RA 토큰을 즉석에서 받아** 그 명의로 부릅니다(ste·HWAX Risk·DynaForge 와 같은 방식). 사람이 RA 토큰(`rat_…`)을 발급해 포털에
붙여 넣던 일이 없어지고, 포털은 RA 토큰을 저장하지 않습니다. 브라우저 SSO 는 4a96cef 의 판단대로 표준 jwt-handoff 가 맞으니 건드리지 않습니다 —
이번 요청은 **서버 간 위임 경로 하나**입니다.

## 1. 되살릴 것 — `4a96cef^:backend/app/modules/sso/heax.py`

옛 모듈이 그대로 계약입니다(포털·게이트웨이는 그 모양에 맞춰 둡니다).

| | 내용 |
|---|---|
| `POST /api/auth/sso` | 헤더 `X-Heax-Gateway-Secret`(RA 전용 공유 비밀) · `X-Heax-User-Email`(필수) · `X-Heax-User-Name`(퍼센트 인코딩) · `X-Heax-Client`(`gateway`·`hwax-portal`) |
| 응답 200 | `{"success": true, "data": {"access_token", "token_type": "bearer", "expires_in", "needs_workspace"}}` |
| 오류 | 비밀이 비어 있으면 404(꺼짐) · 비밀 불일치 401 · 비활성·JIT 꺼짐 403 · 이메일 없음 400 |
| 설정 | `HEAX_SSO_SECRET`(비면 꺼짐) · `HEAX_SSO_JIT_CREATE` · `HEAX_SSO_ALLOWED_IPS`(선택 — 포털 박스 IP) |
| 회수 | `POST /api/auth/sso/revoke`(세대 번호 `hg`) — 있으면 좋고, 포털은 아직 부르지 않습니다 |

라우터 등록(`app.include_router(heax_sso_router, prefix="/api/auth/sso")`)과 `shared/auth` 의 세대 확인(`src=heax`·`hg`)도 같은 커밋에서 빠졌으니 함께 되살려 주세요.

## 2. 토큰 수명

게이트웨이는 받은 토큰을 **최대 12시간** 씁니다. 응답의 `expires_in` 이 있으면 그보다 조금 일찍 다시 받도록 포털 쪽을 고쳐 두었습니다.
그래도 위임 토큰은 **12시간 이상**(지금 기본값 그대로 괜찮습니다)이면 됩니다. 401 을 받으면 게이트웨이가 한 번 다시 받습니다.

## 3. 더 부탁드리는 것 — 부서 헤더가 없을 때

지금 RA MCP 는 받은 `X-Workspace-Slug` 를 그대로 백엔드에 넘기고, 백엔드 대부분이 그 헤더를 요구합니다(없으면 400). 게이트웨이 설정에는
**서비스 계정의 부서**(예: `dev`)가 적혀 있는데, 사람별 호출에 그 값이 남으면 남의 부서로 읽고 씁니다(09-29 VOC 와 같은 모양). 그래서 게이트웨이는
사람별 호출에서 그 헤더를 **뺍니다.** 부탁드리는 것:

- 위임 토큰(`src=heax`)으로 온 요청에 `X-Workspace-Slug` 가 없으면 **그 사람의 `home_workspace_slug`** 로 처리해 주세요.
- 홈 부서가 아직 없는 사람(방금 JIT 로 생긴 사람)은 지금처럼 개인 공간(`personal-<id>`)으로, 또는 "RA 에서 부서를 먼저 고르세요" 로 분명히 거절해 주세요 — 조용히 실패하지만 않으면 됩니다.

(포털 화면에서 보고서를 쌓을 조직을 고르던 기능은 이 방식에서는 쓰지 않습니다 — 부서는 RA 가 자기 프로필로 정하는 것이 맞다고 봤습니다.)

## 4. 다 됐는지 확인(RA 쪽)

1. `HEAX_SSO_SECRET` 없이 `POST /api/auth/sso` → **404**.
2. 넣고 비밀 없이 → **401**, 맞는 비밀 + `X-Heax-User-Email: <있는 사람>` → 200 + `access_token`.
3. 그 토큰 + `X-Workspace-Slug` 없이 `GET /api/reports?mine=true`(또는 MCP `list_reports`) → 그 사람 홈 부서 기준 결과.
4. 포털 운영자에게 **같은 비밀 값**을 주세요(포털 `infra/.env` 의 `RA_SSO_SECRET`). 비밀은 메신저 평문 말고 안전한 경로로.

## 5. 포털 쪽은 이미 준비돼 있습니다

포털 운영자가 `RA_SSO_SECRET` 한 줄을 넣고 update-all 을 돌리면 — 게이트웨이가 RA 를 사람별 위임으로 부르고(`per_user_sso.reportarchive`,
부서 헤더는 뺌), 포털의 PPT 가져오기도 같은 경로로 그 사람 토큰을 받습니다. 그 전까지는 종전 '토큰 등록' 방식이 그대로 돕니다.
