# HWAX 멀티 노드 클러스터 배포 — 설계·구현 계획

작성 2026-07-18. 대화에서 확정된 요구와 코드 사실(인벤토리 절)을 근거로 한 구현 계획.
구현 전 계획 문서 — 각 Phase 의 파일·변경·검증을 실행 단위로 적는다.

## 1. 목표와 비목표

**목표.**
- 운영 노드가 여러 대일 때, **하나의 설정 파일(cluster.yaml)**로 서비스↔노드 배치를 선언하고
  **한 커맨드**로 전 노드 배포·기동·검증까지 자동화한다.
- 특정 서비스는 **2~3개 노드에 복제**(replica)하고, 트래픽은 기존 포털 nginx 가 LB 한다.
- heax 의 서브 기능(앱)들도 **앱 단위 배치**가 가능해야 한다(허브 속 허브 — 같은 원칙의 프랙탈).
- **1노드 하위 호환 절대 보장** — cluster.yaml 없으면 지금과 바이트 단위 동일, 1노드
  cluster.yaml 은 지금과 동일한 config 를 생성해야 한다(수용 테스트로 증명).

**비목표.**
- k8s/nomad 도입 안 함 — apptainer 인스턴스 + bash 오케스트레이터 유지.
- 포털 백엔드 복제 안 함(keystore·PAT SQLite 단일 — 2단계 이후 과제).
- DB 복제/HA 안 함 — DB 는 항상 단일 primary, 복제는 무상태 계층만.

## 2. 현재 상태 인벤토리 (코드 확인 완료)

**이미 있는 것 — 설계가 얹힐 지반.**

| 메커니즘 | 위치 | 상태 |
|---|---|---|
| 노드 어피니티 `only_on: <hostname\|[..]>` | `infra/scripts/services.py enabled_here()` | **구현 완료** — 공유 manifest 하나, 타 박스는 skip |
| 원격 실행 `host:` (ssh 키 인증) | services.py | 구현돼 있으나 update-sites 는 원격 제외 중 |
| 아티팩트 채널 (Drive, 노드 무관) | build-all-to-drive / deploy-all-from-drive | 검증 완료 |
| 원커맨드 자가치유 | `infra/scripts/update-all.sh` | 검증 완료(게이트웨이 config 정합·AIDH remote 자동 등) |
| nginx 라우트 생성 | `infra/scripts/gen-nginx-conf.sh` (routes.env → location/proxy_pass) | 구현 완료 — upstream 확장 지점 |
| heax 앱 manifest | 각 앱 `.portal/manifest.yaml` (`mcp:{}` 블록) | 구현 완료 — `state:`/`endpoint:` 확장 지점 |
| heax→게이트웨이 자동연동 | heax `GET /api/v1/mcp/servers` ← 게이트웨이 폴링 | 검증 완료 — 앱 위치가 바뀌어도 base URL 만 맞으면 추종 |

**갭 — URL 이 127.0.0.1 하드코딩인 4곳(=endpoints 계층이 필요한 이유).**

| 소비처 | 파일 | 지금 |
|---|---|---|
| 포털 nginx 라우트 | `backend/config/routes.env` | `signalforge=http://127.0.0.1:17370/` 등 |
| 게이트웨이 백엔드 URL | `HWAXMcpGateway/provision-config.sh` | `http://127.0.0.1:8013/mcp` 등 하드코딩 |
| agent-server→게이트웨이 | `HWAXAgentServer/mcp_servers.json` (provision 이 생성) | `127.0.0.1:9110` |
| 헬스게이트 프로브 | `infra/scripts/update-all.sh` | `127.0.0.1` 고정 |

## 3. 설계

### 3.1 cluster.yaml — 단일 설정 파일 (시크릿 없음, 커밋 대상)

```yaml
# infra/cluster.yaml — 없으면 단일 노드 모드(현행 유지)
nodes:
  gw:   { host: 10.10.1.11, user: koopark }   # 라우팅 두뇌(포털·게이트웨이·agent)
  data: { host: 10.10.1.12, user: koopark }   # 데이터 계열(SF·AIDH)
control: gw          # cluster-deploy 를 돌리는 노드(운영망 내부여야 함)

placement:           # 스칼라=단일, 리스트=복제
  portal: gw
  mcp-gateway: gw
  agent-server: [gw, data]        # 무상태 → 복제 예
  signalforge: data
  ai-data-hub: data
  heax-hub: gw
  mx-white-paper: gw

singleton:           # 복제 금지 가드 — 리스트로 쓰면 배포 거부
  - signalforge      # 크롤러 중복 방지(크롤러 분리 전까지 서비스 단위로)
  - portal           # keystore·PAT SQLite 단일

heax-apps:           # Phase 3 — 앱 단위 배치(허브는 placement 의 heax-hub 노드)
  materialtwin: data            # sqlite → 단일
  laminate_analyzer: [gw, data] # stateless → 복제
```

- 배치 실행은 **placement → 노드별 서비스 목록 산출 → 그 노드에서 update-all 을 서비스
  필터로 실행**. `only_on:` 은 계속 박스 고유 특성(예: dev 전용 vllm)용으로 남긴다 —
  placement(클러스터 배치)와 only_on(박스 특성)의 역할 분리.

### 3.2 endpoints 계층 — 파생 규칙이 핵심

- `cluster-deploy` 가 cluster.yaml + services.yaml 의 포트 정보로 **노드별 endpoints.env 를
  생성·배포**한다. 손으로 쓰는 파일이 아니라 파생물이다.
- **파생 규칙(하위 호환의 핵심):** 소비자와 제공자가 **같은 노드면 무조건 `127.0.0.1`**,
  다른 노드일 때만 제공자 노드 IP. → 1노드에선 전 항목이 127.0.0.1 = 현행 config 와 동일.
- **복제 서비스의 주소는 LB 하나로 수렴:** 소비자는 개별 replica 를 모르고 항상
  `http://<gw노드>:8088/<svc>/`(nginx upstream) 하나만 본다. 복제 수 변경이 소비자
  config 를 건드리지 않는 이유.
- 소비처 4곳 리팩터링: routes.env 생성(스크립트화), provision-config.sh(URL 을 env 로),
  update-all 프로브(endpoints 읽기), agent-server mcp_servers.json(provision 이 게이트웨이
  주소를 endpoints 에서).

### 3.3 cluster-deploy.sh — 얇은 노드 순회 루프

새 배포 엔진이 아니다. 검증된 update-all 을 노드별로 호출하는 루프 + endpoints 생성기.

```
cluster-deploy.sh [--init] [노드...]
 1) cluster.yaml 파싱 → 노드별 서비스 목록 + endpoints.env 생성
 2) 노드 루프:
    - 대상 host == 자기 자신 → ssh 없이 로컬 실행(자기 ssh 요구 없음)
    - 원격 → ssh <user>@<host> 로: 레포 clone/pull → endpoints.env 배치 →
      update-all.sh --services "<이 노드 몫>"
 3) 클러스터 헬스게이트: 모든 노드×모든 서비스(+replica 전수)를 endpoints 기준 프로브,
    ✗ 하나라도 있으면 exit 1
--init (1회): ssh-copy-id, rclone.conf 배포, NO_PROXY(노드 IP 전체) env 주입
```

- **컨트롤 노드는 운영망 내부**(dev 박스→cae00 ssh 불가 확인됨). 흐름은
  "dev: push+Drive 업로드 → 컨트롤 노드: cluster-deploy 한 줄".

### 3.4 복제(replica)와 LB — 상태 프로파일이 규칙을 정한다

- **LB = 기존 포털 nginx.** placement 가 리스트인 서비스는 gen-nginx-conf 가
  `upstream <svc> { server ip1:port; server ip2:port; }` 블록을 생성(수동 failover 는
  nginx 기본 동작). 새 장비 없음.
- **상태 프로파일 분류(가드의 근거).**

| 프로파일 | 서비스 | 복제 |
|---|---|---|
| 무상태 | agent-server, mcp-gateway, laminate | ✅ 자유 |
| 무상태 API + 단일 DB | AIDH·SF·mxwp 의 API/웹 계층 | ✅ (DB 를 별도 배치 항목으로 분리한 뒤) |
| 단일 필수 | SF 크롤러, 백업 cron, 포털 백엔드(keystore), materialtwin(SQLite) | ⚠ singleton 가드 |
| 노드 자원 | vLLM(GPU) | ✅ 노드별 인스턴스 + LB |

- **singleton 가드**: cluster.yaml 파싱 시 singleton 목록의 서비스가 리스트 placement 면
  즉시 배포 거부(설정 오류를 런타임 장애 전에 차단).

### 3.5 heax 앱 계층 (Phase 3)

- 앱 manifest(`.portal/manifest.yaml`)에 `state: stateless|sqlite|db|gpu` 와
  `endpoint:`(선택, 기본 localhost) 필드 추가.
- 허브(Caddy `/apps/{id}/*` 프록시)가 localhost 가정 대신 manifest endpoint 로 프록시.
  복제 앱은 허브 Caddy 에 upstream 생성.
- **게이트웨이 MCP 자동연동은 무수정 추종** — heax registry 가 주는 base URL 을 그대로
  폴링하므로 앱 위치와 무관.
- 데이터 이동: 앱을 다른 노드로 옮기면 그 노드에서 appdata-from-drive 로 해당 앱
  데이터만 복원(이미 앱 단위 분리돼 있음).
- ⚠ 확인 필요: 허브 Caddy 의 앱 프록시 대상이 정의되는 정확한 위치(Caddyfile 생성부) —
  Phase 3 착수 시 HEAXHub deploy/ 를 먼저 읽고 확정.

## 4. 하위 호환 불변식 (전 Phase 공통 수용 기준)

1. **cluster.yaml 부재** → update-all 단독 동작, 현행과 완전 동일(변경 0).
2. **1노드 cluster.yaml** → cluster-deploy 경유 결과가 현행과 동일:
   **수용 테스트 = routes.env·gateway_config·endpoints 생성물과 헬스게이트 출력의 diff 0**
   (dev 박스에서 실측).
3. 같은 노드 간 통신은 항상 127.0.0.1 (루프백 바인딩 서비스 무수정 동작).

## 5. 단계별 구현 계획

### Phase 0 — endpoints 계층 (반나절, 단독 가치 있음)
- [ ] `infra/scripts/gen-endpoints.sh`: services.yaml 포트 + (cluster.yaml 있으면) 배치로
      endpoints.env 생성. cluster.yaml 없으면 전부 127.0.0.1.
- [ ] 소비처 4곳 리팩터링: routes.env 를 endpoints 에서 생성(기존 값과 diff 0 확인),
      provision-config.sh URL 을 env 화(`SF_MCP_URL` 등, 기본값=현행), update-all 프로브
      endpoints 읽기, agent mcp_servers.json 게이트웨이 주소 env 화.
- 검증: dev 박스에서 **생성물 diff 0** + update-all 풀런 헬스게이트 통과.

### Phase 1 — cluster.yaml + cluster-deploy (1노드 동일성) (반나절)
- [ ] `infra/cluster.yaml.example` + 파서(파이썬, services.py 재사용).
- [ ] `infra/scripts/cluster-deploy.sh`: 자기노드 감지·ssh 루프·update-all `--services` 필터
      (update-all 에 필터 인자 추가)·클러스터 헬스게이트.
- [ ] `--init`: ssh-copy-id / rclone.conf 배포 / NO_PROXY 주입.
- 검증: **1노드 수용 테스트(diff 0)** + cluster.yaml 없는 경로 회귀(현행 러닝북 그대로).

### Phase 2 — 복제 + LB + singleton 가드 (반나절~1일)
- [ ] placement 리스트 지원 + singleton 파싱 가드(위반 시 배포 거부).
- [ ] gen-nginx-conf: 리스트 placement → upstream 블록 생성.
- [ ] 헬스게이트 replica 전수 프로브.
- [ ] DB 분리 배치(AIDH postgres·SF postgres 를 독립 항목으로 — API 복제의 전제).
- 검증: dev+cae00 2노드(또는 dev 단독 2-포트 모의)로 agent-server 2-replica 라우팅·failover.

### Phase 3 — heax 앱 단위 배치 (1일, 선행조사 포함)
- [ ] HEAXHub 허브 프록시 생성부 확인(§3.5 확인 필요 항목).
- [ ] manifest `state:`/`endpoint:` 스키마 + 허브 프록시/upstream + singleton(sqlite) 가드.
- [ ] cluster.yaml `heax-apps:` 지원 + 앱 데이터 노드별 복원 흐름 문서화.
- 검증: laminate 2-replica + materialtwin 단일 강제, 게이트웨이 148 tools 유지 확인.

### 운영 전환 순서
1. Phase 0~1 을 dev 에서 검증 → cae00 은 cluster.yaml 없이 현행 유지(무위험).
2. 두 번째 노드 준비되면 cae00 에 cluster.yaml 작성 → `cluster-deploy --init` → 배치 이행.
3. 복제가 필요해지는 시점에 Phase 2, heax 앱 분산이 필요해지는 시점에 Phase 3.

## 6. 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 사내 프록시가 노드 간 호출을 삼킴(기실측: 상암 LLM 건) | `--init` 이 NO_PROXY 에 전 노드 IP 주입, 헬스게이트가 노드 간 프로브로 즉시 검출 |
| 127.0.0.1 바인딩 서비스가 원격 소비자를 못 받음 | 배치 분리되는 서비스만 내부 NIC 바인딩으로 전환(서비스별 확인 항목), 같은 노드는 계속 루프백 |
| aidh :8001 무인증 노출 | 노드 간 개방 전 방화벽(노드 화이트리스트) 또는 키 도입 — Phase 2 DB 분리 시 함께 |
| GW_TOKEN·rat_ 등 시크릿의 노드 배포 | 시크릿은 cluster.yaml 에 두지 않음 — 각 노드 gitignore 파일 유지, --init 은 배포 안내만(자동 복사는 옵트인) |
| ssh 도달성(컨트롤 노드 위치) | control 노드를 운영망 내부로 명시(cluster.yaml `control:`), dev 는 Drive+push 까지만 |
| 배치 오류(복제 금지 서비스 복제 등) | singleton 가드가 파싱 단계에서 거부 |
| RA hands-off | RA 는 placement 대상에서 제외(현행 유지 — 별도 start.sh 운영) |
| update-all 재귀 위험(cluster-deploy→update-all→자기 pull→재실행) | update-all 의 UPDATE_ALL_REEXEC 가드 재사용 + cluster-deploy 는 pull 후 고정 리비전으로 호출 |

## 7. 범위 밖(명시)

- k8s/서비스메시/컨테이너 오케스트레이션 도입.
- 포털 백엔드 복제(keystore 공유 설계 선행 필요 — 별도 과제).
- DB HA/복제, materialtwin postgres 전환(복제 해금 조건으로만 기록).
- Smart Twin Cluster (재작성 중 — 현행 제외 유지).

## 8. 확인 필요(착수 시 우선 해소)

- heax 허브 Caddy 의 앱 프록시 정의 위치·생성 방식 (Phase 3 선행조사).
- update-sites 의 원격 제외 로직과 cluster-deploy 의 관계 정리(원격은 cluster-deploy 가
  전담, update-sites 는 노드 내부용으로 역할 고정).
- vLLM/GLM 의 노드별 env 차이(dev 로컬 vs 상암 원격)를 endpoints 로 흡수할지 서비스
  env 로 남길지 — 현행 유지(서비스 env) 기울기, Phase 1 에서 결정.
