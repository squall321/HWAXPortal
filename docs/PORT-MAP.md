# 포트 배정표

서비스가 여러 PC 로 흩어지면 각 박스가 어떤 포트를 쓰는지는 `.env` 안에만 있고,
`.env` 는 박스별 파일이라 리포로 넘어오지 않는다. 그래서 **누가 어느 포트를 쓰는지
아무 데도 안 적혀 있는 상태**가 되고, 새 박스를 세울 때마다 충돌을 현장에서 발견한다.

실제 사고(2026-08-19, cae00) — DynaForge 의 기본 DB 포트 5433 이 그 박스에 apt 로 깔린
시스템 PostgreSQL 두 번째 클러스터(pid 1539)와 겹쳤다. 우리 컨테이너는 IPv4 바인드에
실패하고 IPv6·유닉스소켓으로만 떴는데, 증상은 한참 뒤 alembic 의
`password authentication failed for user koorm` 로 나타났다 — 원인과 증상이 전혀 달라
보인다. dev 는 같은 충돌을 겪고 이미 5436 으로 옮겨 놨지만, 그 사실이 cae00 에 전달될
경로가 없었다.

## DB (PostgreSQL)

각 프로젝트는 시스템 postgres 를 공유하지 않고 **자기 postgres 를 apptainer 인스턴스로**
띄운다(데이터도 리포 안). 그래서 포트만 안 겹치면 서로 간섭하지 않는다.

| 포트 | 프로젝트 | 인스턴스 | 설정 위치 |
|---|---|---|---|
| 5432 | MXWhitePaper | `mxwp_postgres` | `MXWhitePaper/.env` |
| 5434 | SignalForge | `sf_postgres` | `SignalForge/backend/.env` |
| 5435 | AIDataHub | `aidh_postgres` | `AIDataHub/api_server/.env` |
| 5436 | **DynaForge (KooRemapper)** | `koorm_postgres` | `KooRemapper/platform/.env` |
| 5732 | HEAXHub | `heax-pg` | `HEAXHub/.env` |

**5433 은 쓰지 않는다.** Debian/Ubuntu 계열에서 apt 로 깔린 두 번째 PostgreSQL 클러스터가
쓰는 포트다. DynaForge 의 옛 기본값이었고 위 사고의 원인이다.

**5432 도 위험하다** — 시스템 postgres 의 첫 클러스터 기본값이다. MXWhitePaper 가 쓰고 있으나,
시스템 postgres 가 도는 박스에 배치하려면 먼저 확인해야 한다.

## 포털 스택의 서비스 포트

포털 리포가 띄우거나 바로 기대는 리스너다(박스마다 같은 기본값 — 바꾸면 이 표와 그 설정을 함께 고친다).

| 포트 | 무엇 | 듣는 곳 | 설정 |
|---|---|---|---|
| 8723 | 포털 백엔드(SPA 도 낸다) | 루프백 | `infra/.env` `PORTAL_PORT` |
| 8088 | 포털 nginx(정문) | 모든 인터페이스 | `infra/.env` `HTTP_PORT` |
| 9009 | 에이전트 서버(챗·심의 SSE) | 루프백 | `HWAXAgentServer/.env` |
| 9110 | MCP 게이트웨이 | 루프백 | `HWAXMcpGateway` |
| 8730 | **LLM 라우터**(풀을 켠 박스만 — `LLM_UPSTREAMS`) | 루프백 | `infra/.env` `LLM_ROUTER_PORT` |
| 8740 | **상시 상태판**(Gatus — 켠 박스만, `STATUS_BOARD`) | 루프백 | `infra/.env` `STATUS_BOARD_PORT` |
| 8750 | **호출 추적**(Phoenix — 켠 박스만, `CALL_TRACE`. 화면·API·OTLP 수신이 한 포트다) | 루프백 | `infra/.env` `CALL_TRACE_PORT` |

**LLM 라우터는 8730 이다** — 처음엔 9130(그 전엔 9120 — 게이트웨이 시험의 knox-bridge 예시와 겹쳐 피했다)이었으나 아래 허브 앱 포트 풀 안이라 어디에도 배포하기 전에 옮겼다(2026-10-16, docs/llm-pool LP-D16).

**9100~9999 는 HEAXHub 의 앱 포트 풀이다**(`HEAXHub/.env` 의 `APP_PORT_RANGE_LOW`·`APP_PORT_RANGE_HIGH`). 허브는 앱을 띄울 때마다 이 범위에서
그 순간 비어 있는 포트를 골라 준다(풀어 준 포트를 먼저 다시 쓴다). 그래서 이 범위의 고정 포트는 그 서비스가 내려가 있는 틈에 허브 앱에게
넘어갈 수 있다 — 그러면 그 서비스는 포트를 못 잡고, 기동 판정은 그 앱의 응답을 '이미 떠 있다' 로 읽는다. 새 고정 포트는 이 범위 밖에서
고른다. 상태판을 8740 으로 둔 까닭이다(2026-10-16 dev 실측 — 허브 앱이 9132·9145 를 쥐고 있었다). 게이트웨이(9110)는 이
범위 안이다 — 늘 떠 있어 허브가 비켜 가지만 같은 틈이 있다(오래 쓰여 와 옮기지 않는다). LLM 라우터는 같은 까닭으로 8730 으로 옮겼다.

**호출 추적(Phoenix)은 포트 하나다.** Phoenix 는 gRPC OTLP 수신기(기본 4317)를 따로 여는데 PHOENIX_HOST 를 보지 않고 모든 인터페이스에 열어서,
띄우는 셈(`infra/call-trace/phoenix_serve.py`)이 그 수신기를 끈다 — 기록기는 8750 의 `/v1/traces` 로만 보낸다. 기동 화면에 찍히는
`OTLP over gRPC …:4317` 줄은 듣지 않는 포트다(docs/improvement-1015/call-trace.md).

## DynaForge 는 두 값을 함께 바꿔야 한다

포트를 옮길 때 `KooRemapper/platform/.env` 의 두 값이 반드시 같아야 한다. 한쪽만 바꾸면
기동 전 정합 검사(`platform/infra/scripts/_common.sh`)가 막는다.

```
POSTGRES_PORT=5436
KOORM_DATABASE_URL=postgresql+asyncpg://koorm:<비밀번호>@127.0.0.1:5436/koorm
```

포트만 바뀌고 DB 파일은 그대로다 — 데이터는 안전하다.

## 새 박스에 배치할 때

1. 쓰려는 포트가 비었는지 먼저 본다: `ss -lntH 'sport = :<포트>'`
2. 시스템 postgres 가 있는지 본다: `sudo ss -lptn | grep postgres`
3. 겹치면 이 표에 없는 번호를 골라 쓰고, **이 표에 추가한다**

DynaForge 의 `start.sh` 는 포트가 남에게 잡혀 있으면 기동을 멈추고 점유 프로세스와
비어 있는 포트를 함께 알려준다 — 그래도 여기 적어 두는 편이 다음 사람에게 빠르다.
