<!-- 연결 사이트들의 포털 SSO .env 블록 킷 + 일괄 배포 스크립트 -->
# env-kits — 연결 사이트 포털 SSO `.env` 일괄 배포

각 사이트의 `.env`(gitignore — 클론에 안 딸려옴)에 필요한 **포털 SSO 연동 블록**을
킷으로 모아두고, 새 서버에서 한 번에 배포한다. 이게 없으면 포털 타일에서 SSO 진입 시
`{"detail":"Portal SSO not enabled"}`(heax) 등으로 거부된다.

## 새 서버에서

```bash
cd <포털레포>
bash infra/env-kits/apply-envs.sh -n     # 계획 확인(dry-run)
bash infra/env-kits/apply-envs.sh        # 적용 — 없는 키만 추가, 기존 값 절대 보존
./infra/scripts/services.sh down heax-hub signalforge mx-white-paper ai-data-hub
./infra/scripts/services.sh up   heax-hub signalforge mx-white-paper ai-data-hub
```

## 킷 구성

| 킷 | 대상 .env | 내용 |
|---|---|---|
| `heax-hub.env` | `<HEAXHub>/.env` | PORTAL_JWKS_URL·AUDIENCE·ISSUER·SSO_LANDING |
| `signalforge.env` | `<SignalForge>/.env` | PORTAL_* + 세션 쿠키 + `SF_SESSION_SECRET`(자동 생성) |
| `mx-white-paper.env` | `<MXWhitePaper>/.env` | PORTAL_* + `REFRESH_COOKIE_PATH=/`(sub-path 필수) |
| `ai-data-hub.env` | `<AIDataHub>/deploy/apptainer/.env` | PORTAL_* + COOKIE_SECURE |

- **시크릿 없음**: 킷엔 로컬 URL/aud/경로만. 박스 로컬 시크릿(`SF_SESSION_SECRET`)은
  `@GENERATE_HEX32@` 마커로 표시되어 적용 시점에 openssl 로 생성된다.
- **멱등**: 몇 번을 다시 돌려도 이미 있는 키는 건드리지 않는다(값 수정 없음).
  값을 바꾸려면 대상 `.env` 에서 직접 수정.
- 레포 위치는 포털의 형제 디렉토리에서 자동 탐색(`<portal 상위>/`, `~/Projects/`, `~/claude/`).
- MCP 게이트웨이/에이전트의 시크릿 config 는 별도:
  `HWAXMcpGateway/provision-config.sh` (GW_TOKEN·서비스 토큰 자동 발급).

## 값의 출처

dev 박스에서 실제 동작 중인 각 사이트 `.env` 의 포털 블록을 그대로 옮겼다.
`PORTAL_ISSUER` 는 포털 `JWT_ISSUER`(기본 `https://hwax.sec.samsung.net`)와 일치해야 한다.
