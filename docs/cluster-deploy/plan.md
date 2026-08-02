# HWAX 멀티 노드 클러스터 배포 — 설계·구현 계획 (v2)

v1 작성 2026-07-18 · **v2 갱신 2026-08-02** — 공유 스토리지(/data) 도입 확정으로 전제가 바뀌어 갱신.
구현 전 계획 문서 — 각 Phase 의 파일·변경·검증·롤백을 실행 단위로 적는다. v1 전문은 git 이력 참조.

**v1 → v2 에서 바뀐 것.**

| 항목 | v1 | v2 |
|---|---|---|
| 클러스터 내부 아티팩트 채널 | Drive (노드별 pull) | **/data 버전 스테이징 + current 심볼릭** (Drive 는 dev→배포서버 반입 채널로만 유지) |
| DB 배치 | 노드 로컬 고정 | **/data/pg/<svc> 허용** (hard mount + singleton 이중 가드 전제) |
| 포털 이중화 | 비목표 | **단계적 목표** (secrets → /data, PAT store → Postgres, nginx upstream) |
| 규모 전제 | 2~3노드 | **18노드** + 노드별 검색용 소형 LLM + HPC GLM 5.2 |
| 부하 전제 | 1인 | **동시 100명**, 시뮬 데이터 7GB/건, 보고서 10만 건 |

v1 의 핵심 기계(endpoints 계층·cluster.yaml·singleton 가드·nginx upstream LB·노드 순회
fan-out)는 그대로 유효하다 — v2 는 그 위에 스테이징/버전 계층과 이중화 단계를 얹는다.

## 0. 확정 전제 (2026-08-02 대화)

- **클러스터**: 신규 서버 18대, 전 노드에 `/data` 공통 마운트(NFS, 스토리지 자체 이중화). 1PB.
- **LLM 토폴로지**: 각 노드에 검색용 소형 LLM(임베딩·도구 랭킹), HPC 에 GLM 5.2(챗·심의 추론).
- **배포 서버**: 클러스터 노드 중 1대 지정. 소스는 그 서버의 `~/Projects/` 체크아웃.
  `update-all` 한 번으로 → git pull → Drive 반입 → **/data 버전 스테이징** → current 스위치 →
  **cluster.yaml 배치대로 각 노드 재기동** → 클러스터 헬스게이트.
- **dev 머신**: 완전히 같은 스크립트·같은 yaml 형식. 노드가 127.0.0.1 하나뿐이라 한 박스에 전부.
- **cae00(현 운영)**: 클러스터가 검증 완료될 때까지 **현행 방식 그대로, 손대지 않는다.**
  전환은 마지막에 별도 결정.
- **RA**: 현행 인스턴스는 **일절 불간섭**(사용자 결정 2026-08-02 — 백업 편입도 보류).
  클러스터 이관은 **블루-그린**: 새 노드에 별도 RA 인스턴스를 세워 PAT·SSO 연동을 먼저
  검증하고, 컷오버 때 기존 DB+파일을 복원해 전환한다(§Phase 3.2). 성립 근거(실측):
  RA 의 rat_ PAT·비밀번호가 전부 DB 안 해시(sha256/bcrypt)라 **DB 복원과 함께 기존 자격증명이
  그대로 살아난다** — 게이트웨이 토큰 재발급 불필요.
  ⚠ 기록해 두는 위험: 컷오버 전까지 RA 는 백업이 없는 유일한 실데이터 서비스다.
- **데이터 원칙**: DB 는 메타/검색(경로·체크섬·본문 JSONB·임베딩), 실물 파일(시뮬 7GB·보고서
  첨부)은 `/data` — AIDH(`/attachments` file_path)·RA(`files.storage_path`) 가 이미 이 구조임을
  코드로 확인했다(2026-08-02). Postgres 필드 한계(1GB)로 7GB 는 애초에 DB 에 못 들어간다.
- k8s/nomad 도입 안 함(유지) — apptainer + bash. 단 배치 계층을 얇게 유지해 향후 교체 가능하게.

## 1. 목표 상태 (한 그림)

```
[dev]  push + build-all-to-drive ──▶ Drive
                                       │
[배포서버 ~/Projects]  update-all ─────┤
  1. git pull (전 레포)                │
  2. deploy-from-drive (반입) ◀────────┘
  3. stage-to-data:  /data/hwax/versions/<svc>/<ver>/   (불변, sha256 검증)
  4. current 스위치:  /data/hwax/current/<svc> → versions/<svc>/<ver>   (원자적)
  5. fan-out:  cluster.yaml 순서대로  ssh <node> update-node.sh
     (순서: DB·백엔드 → 게이트웨이 → 소비자.  복제 서비스는 한 노드씩 롤링)
  6. 클러스터 헬스게이트: 전 노드 × 전 서비스(+replica 전수) 프로브, 실패 시 exit 1

롤백 = current 를 직전 버전(state/last-good)으로 되돌리고 해당 서비스만 롤링 재기동
```

dev 머신은 같은 흐름에서 노드가 자기 하나뿐이라 ssh 없이 로컬 실행 — 스크립트 분기 없음.

## 2. /data 레이아웃 (정본)

```
/data/hwax/                          ← 클러스터 배포 루트
  versions/<svc>/<YYYYMMDD-sha7>/    ← SIF·dist·src(+venv) — append-only 불변
  current/<svc> → ../versions/<svc>/<ver>     ← 유일한 가변 포인터 (ln -sfn 원자 교체)
  cluster.yaml                       ← 배치 정본 (시크릿 없음)
  endpoints/<node>.env               ← gen-endpoints 산출물 (파생물, 손으로 안 씀)
  secrets/                           ← jwt keys·session_secret·provision.env (0700/0600)
  state/
    locks/<svc>.lock                 ← singleton 런타임 가드 ({hostname, pid, ts})
    last-good/<svc>                  ← 마지막 헬스게이트 통과 버전 (롤백 대상)
    deploy.log                       ← 배포 이력 (누가·언제·무슨 버전)
/data/pg/<svc>/                      ← PGDATA — singleton + hard mount 필수 (§9 가드)
/data/appdata/<app>/                 ← HEAX 앱 런타임 데이터 (앱별 서브디렉터리 = 격리 경계)
/data/models/                        ← LLM 가중치 (검색용 소형 LLM·TTS 등)
/data/backups/   /data/wal/          ← DB 복구 자산 (backup-local.sh 대상)
/data/sim/<project>/<run>/           ← 시뮬 실물 7GB/건 (범위 밖 — 레이아웃만 예약, §12)
/data/reports/                       ← RA 첨부 실물 (upload_dir_path 이관 후보 — §12)
```

**절대 규칙**: `versions/` 는 append-only. 어떤 스크립트도 기존 버전 디렉터리에 쓰지 않는다.
가동 중 인스턴스는 옛 경로(inode)를 물고 있으므로 스위치에 영향받지 않는다 — SF 502 사고
(가동 중 SIF 덮어쓰기 → squashfs 파손, 2026-08-01 실사고)가 **구조적으로 불가능**해진다.
18노드 공유에서 그 사고는 전 노드 동시 장애가 되므로 이 규칙이 클러스터의 제1 전제다.

## 3. cluster.yaml — 배치 정본 (v1 스키마 확장)

```yaml
# /data/hwax/cluster.yaml — 없으면 단일 노드 모드(현행과 완전 동일)
schema: 2
data_root: /data/hwax
control: node01                       # update-all 을 돌리는 배포 서버 (운영망 내부)

nodes:
  node01: { host: 10.10.1.11, user: koopark, roles: [entry] }   # nginx 진입점
  node02: { host: 10.10.1.12, user: koopark }
  # … node18 까지. dev 는 nodes: { dev: {host: 127.0.0.1} } 하나.

placement:                            # 스칼라=단일, 리스트=복제(롤링 재기동 대상)
  portal:        [node01, node02]     # Phase 4 이후 (그 전엔 스칼라)
  mcp-gateway:   node01
  agent-server:  [node01, node02]
  ai-data-hub:   node03
  ai-data-hub-db: node03              # DB 는 API 와 분리 항목 (pgdata: /data/pg/aidh)
  signalforge:   node04
  signalforge-db: node04
  heax-hub:      node05
  report-archive: node06              # placement 만 — 기동은 RA 자체 start.sh (소스 무수정)
  search-llm:    all                  # 노드마다 1개 (임베딩·검색 — endpoints 가 자기 노드로 해석)

singleton:                            # 리스트 placement 면 파싱 단계에서 배포 거부
  - ai-data-hub-db
  - signalforge-db
  - report-archive                    # DB + 스케줄러 동반
  - sf-crawler                        # 크롤러 중복 수집 방지
```

- **endpoints 파생 규칙(v1 유지)**: 소비자·제공자가 같은 노드면 무조건 `127.0.0.1`,
  다르면 제공자 노드 IP. 복제 서비스는 항상 entry 노드 nginx upstream 하나로 수렴 —
  복제 수 변경이 소비자 config 를 건드리지 않는다.
  → 1노드(dev)에선 전 항목 127.0.0.1 = 현행 config 와 diff 0.
- `only_on:` 은 박스 고유 특성(dev 전용 vllm)용으로 존치 — placement 와 역할 분리(v1 결정 유지).
- 127.0.0.1 하드코딩 소비처 4곳(v1 인벤토리: routes.env·provision-config.sh·
  mcp_servers.json·update-all 프로브)이 endpoints 리팩터링 대상이라는 사실도 그대로다.

## 4. 버전 스테이징 — stage-to-data.sh (신규, v2 핵심)

```
stage-to-data.sh <svc> [--src <dir>] [--from-drive]
 1) ver = $(date +%Y%m%d)-$(git -C <repo> rev-parse --short HEAD)
 2) /data/hwax/versions/<svc>/<ver>/ 가 이미 있으면 → sha256 검증만 하고 skip (멱등)
 3) 임시 디렉터리에 복사(SIF·dist·src+venv) → sha256 manifest 생성
 4) mv 로 versions/<svc>/<ver>/ 원자 배치 (같은 파일시스템 내 rename)
 5) current 스위치는 하지 않는다 — update-all 이 전 서비스 스테이징 후 일괄 스위치
GC: 최근 5세대 + last-good 보존, 나머지 삭제 (가동 중 버전은 확인 후)
```

- **코드형 서비스**(agent-server·gateway — venv 로 실행): src 를 `git archive` 로 내보내고
  venv 를 배포 서버에서 1회 빌드해 함께 스테이징. 전 노드가 같은 `/data` 경로로 마운트하므로
  venv 절대경로가 일치해 그대로 동작한다. **전제: 18노드 OS·glibc·Python 동질**(§11).
  이질이면 노드별 venv 빌드로 후퇴(스테이징은 src 만, venv 는 update-node 가 빌드).
- **컨테이너형**(portal·nginx·SF·AIDH 등): SIF + dist 스테이징. 포털 백엔드처럼 레포를
  바인드 마운트하는 서비스는 바인드 소스를 `current/<svc>/src` 로 전환
  (**기본값=현행 레포 경로** — cluster.yaml 있을 때만 /data 경로. 환경변수 하나로 분기).

## 5. update-all 통합 흐름 (배포 서버)

기존 update-all 의 1)~6) 단계는 그대로 두고, **cluster.yaml 이 존재할 때만** 추가된다.

```
 2.5) stage-to-data: 반입된 아티팩트·레포를 버전 스테이징 (전 서비스)
 2.6) preflight-cluster: §9 사전점검 — 하나라도 실패하면 스위치 전에 중단 (이 시점까지 무해)
 2.7) current 일괄 스위치 + state/deploy.log 기록
 4')  update-sites 대신 fan-out: 노드 순서 = DB·백엔드 → 게이트웨이 → 소비자
      (2026-08-02 재기동 순서 교정과 동일 원리 — 가짜 DOWN 방지)
      각 노드: ssh <node> "bash /data/hwax/current/portal/src/infra/scripts/update-node.sh"
      update-node.sh: cluster.yaml 에서 자기 몫 산출 → services down/up (current 경로) → 노드 헬스
      복제 서비스는 한 노드씩: down→up→health 통과 후 다음 노드 (무중단)
 6')  클러스터 헬스게이트: endpoints 기준 전 노드×전 서비스 프로브 + 게이트웨이 tools 수
      + 챗 스모크. 통과 시 state/last-good/<svc> 갱신. 실패 시 exit 1 + 롤백 명령 출력.
```

- cluster.yaml 이 **없으면 현행 update-all 과 완전 동일** — cae00 과 dev 일상은 무영향.
- `update-node.sh` 는 ssh 중첩 없이 **로컬 동작만** 한다(services.py 로컬 경로 재사용).
  update-sites 의 "원격 skip" 은 legacy 로 존치 — 클러스터 경로가 이를 대체한다.
- fan-out 은 스위치된 **고정 버전**을 호출한다(자기 pull 재귀 없음 — UPDATE_ALL_REEXEC
  가드는 배포 서버 단계에만 존재).

## 6. LLM 배치

| 역할 | 위치 | 배선 |
|---|---|---|
| 챗·심의 추론 (GLM 5.2) | HPC | agent-server `VLLM_BASE_URL` — endpoints 에서 해석 (현행 @FROM_RA 규칙 유지) |
| 검색·임베딩 (소형 LLM) | 각 노드 | `search-llm: all` — 소비자(agent-server 의 embedder/`AIDH_HTTP`)는 endpoints 가 **자기 노드 127.0.0.1** 로 해석. 가중치는 /data/models 공유 |
| dev 로컬 (qwen 7B) | dev 박스 | `only_on: smarttwincluster` 존치 |

- 노드별 소형 LLM 덕에 임베딩 호출이 노드 밖으로 안 나간다 — 100명 동시에서 네트워크 병목 회피.
- `_embed` 64개 청크(2026-08-01 수정)는 그대로 유효 — 소형 GPU/CPU 서빙 보호.

## 7. 포털 이중화 (v1 비목표 → v2 단계적 목표)

실측 결과(2026-08-02) 포털이 쥔 상태는 셋뿐이다.

| 상태 | 실체 | 해법 | 단계 |
|---|---|---|---|
| 세션·리프레시 서명 | `HS256` + `session_secret` (문자열 1개) | `/data/hwax/secrets` 정본화 — 전 노드 동일 | Phase 4 |
| launch-JWT 키쌍 | `secrets/jwt/<kid>.key/.pub` | 같은 방식 (kid 로테이션 기존 지원) | Phase 4 |
| PAT·jti 저장소 | SQLite (`used_jti`·`pat` 테이블 2개) | **Postgres 이관 필수** — SQLite 는 NFS 잠금 신뢰 불가 | Phase 4 |

- `session_secret` 통일 시점에 **기존 세션 전원 로그아웃 1회** — 공지 후 실행.
- PAT 이관이 **가장 위험한 전환**이다(개인 Claude 에 등록된 토큰이 무효화될 수 있음):
  이관 스크립트 + 사전 스냅샷 + 이중 read(구 SQLite fallback) 기간 후 완전 전환.
  실패 대비책 = /tokens 설정 배치파일(재발급·재등록 자동화 — 2026-08-02 구축 완료, 4종 클라이언트).
- 진입점 자체(entry nginx)의 HA 는 **VIP(keepalived) 필요 — 사내 네트워크 협의 대상**(§11).
  그 전까지 DNS → entry 노드 1대가 SPOF 임을 명시하고 운영한다.

## 8. 100명 동시 대비 (배치와 별개지만 클러스터 전에 필요)

- **pgbouncer**(transaction 모드) — 실측: `max_connections=100`·`shared_buffers=128MB`(기본값)·
  앱 풀 미설정(SQLAlchemy 암묵 5+10). 다중 노드 × 앱 풀이면 커넥션 고갈이 먼저 온다.
- PG 튜닝: `shared_buffers` RAM 25% 수준, 앱 풀 크기 명시.
- **대용량 파일 서빙 분리**: 7GB 시뮬·수MB 보고서를 FastAPI 가 스트리밍하지 않는다 —
  nginx `X-Accel-Redirect`(인증은 앱, 전송은 nginx). §12 별도 트랙.

## 9. 안전 불변식 (전 Phase 공통 — 위반하는 커밋은 되돌린다)

1. **cluster.yaml 부재 = 현행과 완전 동일.** 수용 테스트가 자동으로 증명한다
   (no-yaml vs 1노드 yaml — config 생성물·헬스게이트 출력 diff 0).
2. **versions/ 는 append-only.** current 스위치는 `ln -sfn` 원자 교체만.
3. **DB 는 항상 정확히 1노드.** 3중 가드 — ① 파서가 singleton 의 리스트 placement 거부,
   ② 기동 스크립트가 `state/locks/<svc>.lock` 의 타 호스트 기록을 보면 기동 거부(명시적
   override 플래그로만 해제), ③ PGDATA 서비스는 preflight 가 hard mount 미확인 시 기동 거부.
4. **모든 커밋에서 update-all 이 동작한다.** "전환 중이라 지금은 안 됨" 상태 금지.
5. **백업 없이 이관 없음.** 데이터를 옮기는 모든 단계는 직전 스냅샷 + 복원 리허설이 선행
   조건이다. RA 는 블루-그린 컷오버 덤프(§3.2-③)가 그 스냅샷을 겸한다.
6. **시크릿은 /data/hwax/secrets (0700) 만.** cluster.yaml·레포·Drive 에 시크릿 금지.
   NFS 특성상 uid 로만 보호되므로 노드 계정 통제가 전제임을 명시.
7. **cae00 은 클러스터 검증 완료까지 불간섭.** 전환은 마지막 별도 결정.

## 10. Phase 계획

### Phase 0 — 기반 (기존 동작 무영향, 추가만) — dev 에서
- **0.1 endpoints 계층** (v1 Phase 0 그대로): `gen-endpoints.sh` + 소비처 4곳 리팩터링
  (routes.env 생성·provision-config env 화·헬스게이트·mcp_servers.json). 검증: 생성물 diff 0.
- **0.2 (보류 — 사용자 결정 2026-08-02)** RA 백업 편입은 하지 않는다. RA 는 블루-그린으로
  이관하며(§3.2), 컷오버용 덤프가 사실상 첫 백업이 된다. 그 전까지의 무백업 위험은 §0 에 기록.
- **0.3 stage-to-data.sh + /data/hwax 레이아웃**: 신규 경로에 쓰기만 — 아무도 아직 읽지 않음.
  검증: 버전 생성·sha256·GC·멱등성. dev 의 /data 는 로컬 디스크라 즉시 개발 가능.
- 롤백: 불필요(추가만). cae00 영향: 없음.

### Phase 1 — 1노드 클러스터 경로 (dev 에서 동등성 증명)
- **1.1** cluster.yaml 파서(+스키마 검증·singleton 가드·미정의 노드 거부) — services.py 재사용.
- **1.2** `update-node.sh` + services `--services` 필터 + current 경로 소비(env, 기본=현행).
- **1.3** dev 1노드 cluster.yaml 수용 테스트: **외부 관측 동등성** — 헬스게이트 출력·게이트웨이
  tools 수·챗 스모크 동일. (실행 경로가 /data 로 바뀌는 것은 의도이므로 diff 대상은
  endpoints 산출물과 관측 동작이다 — v1 의 "config diff 0" 기준을 이렇게 정밀화한다.)
- **1.4** 롤백 리허설: current 를 직전 버전으로 → 재기동 → 이전 버전 서빙 실측.
- **1.5** 원자 스위치 리허설: 가동 중 스위치 → 기존 인스턴스 무중단 실측.
- 롤백: cluster.yaml 삭제 = 현행 복귀. cae00 영향: 없음.

### Phase 2 — 다노드 fan-out (신규 노드 2~3대 파일럿)
- 진입 조건: Phase 1 수용 테스트 통과 (+ aidh 복구 리허설은 2.4 안에서 수행).
- **2.1** `preflight-cluster.sh`: ssh 도달성(BatchMode)·/data 마운트 동일성(마커 파일)·
  hard mount·디스크 여유·시계 동기(JWT nbf/iat 보호)·sha256 재검증·NO_PROXY 주입.
- **2.2** fan-out + 순서 + 노드별 헬스 + 클러스터 헬스게이트.
- **2.3** 파일럿: 무상태 MCP 1개(laminate)를 2노드 배치 — 게이트웨이 도구 수 불변 확인.
- **2.4** DB 1개(aidh) /data/pg 이동 리허설: singleton 락·hard mount 가드 실측 +
  복구 리허설 재실행. **의도적 이중 기동 시도가 거부되는 것까지 실측.**
- 롤백: cluster.yaml 편집으로 파일럿 노드 제거. cae00 영향: 없음(별개 장비).

### Phase 3 — 본 배치 (18노드 서비스 이관)
- **3.1** 서비스별 이관: 한 번에 한 서비스 — yaml 에 노드 반영 → fan-out → 헬스 → 다음.
  search-llm all-nodes 롤아웃 포함.
- **3.1b 데이터 동기·백업의 노드 인식화** (실측 2026-08-02: merge-from-drive.sh 와
  backup-local.sh 가 전부 `apptainer exec instance://…` — **같은 박스 인스턴스 가정**).
  DB 가 다른 노드로 가면 그 단계는 소유 노드에서 돌아야 한다 — fan-out 이 update-all 의
  3)단계(AIDH merge)·1b)단계(백업)·SF_RESTORE_DB 를 placement 의 DB 소유 노드로 위임하도록
  확장. 1노드에선 현행과 동일(자기 자신에게 위임).
- **3.2** RA 이관 — **블루-그린** (기존 인스턴스는 컷오버 순간까지 불간섭).
  ```
  ① 새 노드에 RA 인스턴스 기동 (자체 deploy.sh, DB 는 /data/pg/reportarchive 신규)
  ② 기계 검증: 웹·MCP(:3002)·스케줄러 동작, (선택) portal_sso 연동 — 병행 인스턴스라
     소스 수정 시도가 안전. 단 SSO get-or-create 는 이메일 일치 전제(기존 대화 확정)
  ③ 컷오버 창: 구 RA 쓰기 정지 → pg_dump + upload_dir_path 파일 rsync → 새 DB 복원
     ⚠ DB 만으론 부족 — files.storage_path 가 가리키는 실물 디렉터리 동반 필수
     ⚠ ②에서 만든 테스트 계정·토큰은 복원이 덮는다 — 최종 연동 확인은 복원 뒤에.
        반대로 기존 rat_ 토큰·비밀번호는 DB 해시라 복원과 함께 그대로 산다(실측) —
        게이트웨이 config 의 토큰 교체 불필요
  ④ 구 인스턴스 완전 정지(스케줄러 중복 발송 방지) → 포털 라우트를 새 RA 로 전환
  ⑤ 롤백 = 라우트를 구 RA 로 되돌림 (구 인스턴스는 강등 전까지 보존)
  ```
  **같은 박스 변형(구 RA 와 green 이 한 서버일 때)** — 절차 동일, 격리 5종만 추가.
  전부 설정 가능함을 실측(2026-08-02): APP_PORT(웹 :3000→예 :3100) · MCP_PORT(:3002→:3102) ·
  DATABASE_URL 의 DB 이름(같은 Postgres 에 DB 하나 더 — 두 번째 서버 불필요) ·
  upload_dir(별도 경로) · 설치 디렉터리(별도 체크아웃). ⚠ systemd 타이머(scheduler·
  orphan-cleanup)는 유닛 이름이 고정이라 green 에 설치하면 기존 유닛을 덮는다 —
  컷오버(④) 때 구 인스턴스 정지와 함께 넘긴다. 컷오버는 로컬 복사(pg_dump|psql + rsync)
  + routes.env 한 줄이라 오히려 쉬워짐. 트레이드오프: 같은 박스면 노드 장애 보호는 없음 —
  최종 목적지가 클러스터 노드라면 green 을 처음부터 그 노드에 세우는 쪽이 두 번 일 안 함.

  ⚠ **RA 작업 공통 주의(사용자 지시)**: RA 는 어떤 단계에서도 현행 인스턴스·레포·DB 를
  직접 건드리지 않는다. 읽기(pg_dump·파일 복사)만 허용, 쓰기·수정·재기동은 green 쪽에만.
  컷오버의 "구 인스턴스 정지"가 유일한 예외이며 그 직전 덤프가 반드시 선행돼야 한다.
- 롤백: 서비스 단위 — 이전 배치로 yaml 되돌림. cae00: 이 시점까지 병행 운영.

### Phase 4 — 이중화·100명 대비
- **4.1** secrets → /data 정본화 (세션 로그아웃 1회 — 공지 후 야간).
- **4.2** PAT store → Postgres (스냅샷 + 이중 read 기간 + 완전 전환. 롤백 절차 사전 문서화).
- **4.3** portal·agent-server 복제 + entry nginx upstream + singleton 재확인.
- **4.4** pgbouncer + PG 튜닝 + 앱 풀 명시.
- **4.5** 진입점 VIP (사내 협의 결과에 따라).
- 각 항목 독립 커밋 — 하나가 밀려도 나머지가 진행된다.

### Phase 5 — HEAX 앱 노드 배치 (v1 Phase 3 승계 — 후속)
- 앱 상태 로컬 JSON(`var/integration_state`) → DB(`node` 컬럼 — port_allocator 가 이미 DB 기반),
  원격 기동(services.py ssh 경로 재사용), **용량 인식 배치**, `resources:` 필수화(무제한 앱
  등록 거부), /data/appdata 앱별 바인드 마운트 격리 강제.
- 근거: 2026-08-02 dev 박스 OOM(프로세스 2,671개·RSS 합 247GiB·code 638개 100GiB) —
  남의 앱을 받는 플랫폼에서 자원 상한 없는 배치는 반드시 재발한다.

### cae00 전환 (마지막, 별도 결정)
- 클러스터 Phase 3 안정 운영 후: cae00 데이터를 backup-local 스냅샷 → 클러스터 DB 로 merge
  (기존 merge-from-drive 비파괴 패턴 재사용) → DNS/진입점 전환 → cae00 예비 강등.

## 11. 결정 필요 (사용자/조직)

| 항목 | 내용 | 막히는 것 |
|---|---|---|
| 노드 동질성 | 18대 OS·glibc·Python 동일 여부 | venv 공유(§4). 다르면 노드별 빌드 후퇴 |
| 진입점 VIP | keepalived 용 VIP — 사내 네트워크 협의 | 진입점 HA(§7). 전까지 entry 노드 SPOF |
| 배포 서버 지정 | 18대 중 어느 노드 + ssh 키 배포 | Phase 2 착수 |
| 검색용 LLM | 모델·서빙(vLLM/llama.cpp)·GPU 유무 | search-llm 서비스 정의 |
| NFS fsync | 스토리지 쓰기캐시의 fsync 정직성 | PGDATA /data 배치 최종 승인 |
| cae00 전환 시점 | 클러스터 안정 후 일정 | 최종 단계 |

## 12. 범위 밖 (별도 트랙 — 이 계획과 독립)

- 시뮬 데이터 등록·서빙 파이프라인(경로 등록 방식·X-Accel-Redirect·체크섬·청크 업로드).
- RA `upload_dir_path` → /data/reports 이관 + 디렉터리 샤딩(10만 건 대비).
- k8s 전환 — 배치 계층을 얇게 유지해 선택지만 보존.
- DB 스트리밍 복제(HA) — 콜드 페일오버(§2 구조로 확보)로 시작, 필요해지면 후속.
- Smart Twin Cluster — 재작성 중, 현행 제외 유지.

## 13. 리스크와 완화 (v1 표 승계 + v2 추가)

| 리스크 | 완화 |
|---|---|
| NFS 위 PGDATA 손상 | hard mount 강제(preflight) · singleton 3중 가드 · fsync 정직성 확인(§11) · WAL 아카이브 /data/wal |
| 두 노드가 같은 DB 기동 | 파서 거부 + 락파일 + preflight — 3중 (§9-3) |
| PAT 이관 실패 = 개인 Claude 전원 재설정 | 스냅샷 · 이중 read · /tokens 설정 배치파일(재등록 자동화 기구축) |
| 세션 전원 로그아웃 | 1회로 국한, 공지 후 야간 실행 |
| venv 공유가 노드 이질성으로 깨짐 | §11 동질성 확인 선행, 노드별 빌드 후퇴 경로 명시(§4) |
| /data I/O 경합(7GB 스트림 vs DB fsync) | DB 전용 export/QoS 협의, 악화 시 PGDATA 로컬 NVMe 후퇴(레이아웃 §2 는 불변) |
| 스토리지 자체 장애 | 이중 컨트롤러 전제(구매 사양) + /data/backups 의 별도 매체 2차 백업 검토 |
| 여러 세션 동시 작업 충돌(실사고 2회) | 클러스터 작업 전용 브랜치, 공유 파일(services.py·gen-nginx-conf.sh) 담당 명시, git add -A 금지 유지 |
| 사내 프록시가 노드 간 호출 삼킴 | preflight NO_PROXY 주입 + 노드 간 프로브 (v1 승계) |
| update-all 재귀 | UPDATE_ALL_REEXEC 가드 + fan-out 고정 버전 호출 (v1 승계) |
| aidh :8001 무인증 노출 | 노드 간 개방 전 방화벽 화이트리스트 또는 키 도입 — DB 분리 시 함께 (v1 승계) |
