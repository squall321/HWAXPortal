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
| `agent-server.env` | `<HWAXAgentServer>/.env` | VLLM_BASE_URL·VLLM_MODEL — **ReportArchive 의 LLM 설정을 상속**(`@FROM_RA:` 마커, playbook §8) + **심의(DELIB_*) 튜닝 시드**(temperature·절단 배율·재시도·타임아웃 — cae00 권장 리터럴, dev 미적용) |

- **시크릿 없음**: 킷엔 로컬 URL/aud/경로만. 박스 로컬 시크릿(`SF_SESSION_SECRET`)은
  `@GENERATE_HEX32@` 마커로 표시되어 적용 시점에 openssl 로 생성된다.
- **RA LLM 상속**: `@FROM_RA:LLM_BASE_URL@`·`@FROM_RA:LLM_MODEL@` 마커는 적용 시점에 형제
  ReportArchive `.env` 의 해당 키를 읽어 채운다(agent-server 가 RA 의 상암 LLM 을 '그대로' 씀).
  RA 가 mock(LLM_ 미설정)이면 그 키는 건너뛰어 agent-server 기본값(로컬 vLLM)을 쓴다. RA 는 읽기만 한다.
- **멱등**: 몇 번을 다시 돌려도 이미 있는 키는 건드리지 않는다(값 수정 없음).
  값을 바꾸려면 대상 `.env` 에서 직접 수정.
- **agent-server 는 기본 목록에 없다**: `bash apply-envs.sh agent-server` 로 인자를 명시해야
  적용되고, 적용 후 agent-server 재시작이 필요하다. `DELIB_REASONING_EFFORT` 는 상암 vLLM
  reasoning parser 선확인 전까지 킷에서 주석 상태다(agent-server.env 내 절차 주석 참조).
- 레포 위치는 포털의 형제 디렉토리에서 자동 탐색(`<portal 상위>/`, `~/Projects/`, `~/claude/`).
- MCP 게이트웨이/에이전트의 시크릿 config 는 별도:
  `HWAXMcpGateway/provision-config.sh` (GW_TOKEN·서비스 토큰 자동 발급).

## 값의 출처

dev 박스에서 실제 동작 중인 각 사이트 `.env` 의 포털 블록을 그대로 옮겼다.
`PORTAL_ISSUER` 는 포털 `JWT_ISSUER`(기본 `https://hwax.sec.samsung.net`)와 일치해야 한다.
