# 클러스터 배포 — 구현 체크리스트 (v2)

plan.md v2 (2026-08-02) 의 실행 추적용. 구현 착수 전에는 전부 미체크가 정상.
Phase 게이트: 이전 Phase 의 "검증" 항목이 전부 체크되기 전에는 다음 Phase 착수 금지.

## Phase 0 — 기반 (기존 동작 무영향)

### 0.1 endpoints 계층 (v1 승계)

- [ ] `infra/scripts/gen-endpoints.sh` (cluster.yaml 없으면 전부 127.0.0.1)
- [ ] routes.env 를 endpoints 에서 생성 — 현행과 diff 0 확인
- [ ] provision-config.sh 백엔드 URL env 화(기본값=현행 127.0.0.1)
- [ ] update-all 헬스게이트 endpoints 소비
- [ ] agent mcp_servers.json 게이트웨이 주소 env 화
- [ ] 검증: dev 풀런 — 생성물 diff 0 + 헬스게이트 통과

### 0.2 RA — 보류 (사용자 결정 2026-08-02)

- RA 는 일절 불간섭. 백업 편입 안 함 — 이관은 Phase 3.2 블루-그린으로, 컷오버 덤프가
  첫 백업을 겸한다. 그 전까지 무백업 위험은 plan §0 에 기록됨.

### 0.3 /data 스테이징 계층

- [ ] /data/hwax 레이아웃 생성 스크립트 (versions/current/secrets/state)
- [ ] `infra/scripts/stage-to-data.sh` — 버전 스테이징 + sha256 manifest + 멱등
- [ ] GC (최근 5세대 + last-good 보존)
- [ ] 검증: dev 로컬 /data 에서 스테이징·재실행 멱등·GC 실측. 기존 서비스 무영향 확인

## Phase 1 — 1노드 클러스터 경로 (dev 동등성)

- [ ] `infra/cluster.yaml.example` (schema 2) + 파서 — 스키마 검증·singleton 가드·미정의 노드 거부
- [ ] `infra/scripts/update-node.sh` (로컬 동작만 — ssh 중첩 없음)
- [ ] services `--services` 필터 + current 경로 소비 (env, 기본값=현행 레포 경로)
- [ ] update-all: cluster.yaml 존재 시 2.5~2.7(스테이징·preflight·스위치)·4'(fan-out)·6'(클러스터 게이트) 분기
- [ ] 수용 테스트: dev 1노드 yaml — 헬스게이트 출력·게이트웨이 tools 수·챗 스모크 ≡ no-yaml
- [ ] 회귀 테스트: cluster.yaml 부재 경로 = 현행 러닝북 그대로 (자동 비교 스크립트)
- [ ] 롤백 리허설: current 를 직전 버전으로 → 이전 버전 서빙 실측
- [ ] 원자 스위치 리허설: 가동 중 스위치 → 기존 인스턴스 무중단 실측

## Phase 2 — 다노드 fan-out (파일럿 2~3대)

진입 조건: [ ] Phase 1 수용 테스트 통과

- [ ] `infra/scripts/preflight-cluster.sh` — ssh 도달성·/data 마운트 동일성·hard mount·
      디스크 여유·시계 동기·sha256 재검증·NO_PROXY
- [ ] fan-out (순서: DB·백엔드 → 게이트웨이 → 소비자, 복제는 노드별 롤링)
- [ ] 클러스터 헬스게이트 (전 노드 × 전 서비스 + replica 전수) + last-good 갱신
- [ ] 파일럿: laminate MCP 2노드 배치 — 게이트웨이 도구 수 불변
- [ ] DB 이동 리허설: aidh PGDATA → /data/pg/aidh — singleton 락·hard mount 가드 실측
- [ ] 의도적 이중 기동 시도 → 거부되는 것 실측
- [ ] 복구 리허설 재실행 (/data 배치 후에도 백업·복원 동작)

## Phase 3 — 본 배치 (18노드)

- [ ] 서비스별 이관 (한 번에 한 서비스, 각각 헬스 통과 후 다음)
- [ ] search-llm all-nodes 롤아웃 (모델·서빙 방식은 §11 결정 후)
- [ ] 데이터 동기·백업 노드 인식화 (plan §3.1b — merge·backup·SF restore 를 DB 소유 노드로 위임)
- [ ] RA 블루-그린 (plan §3.2): 새 인스턴스 기동 → 기계 검증(웹·MCP·스케줄러, 선택 SSO)
- [ ]   컷오버: 구 RA 쓰기 정지 → pg_dump + upload 파일 rsync → 복원 → 연동 확인(기존 rat_ 토큰 생존 확인)
- [ ]   구 인스턴스 완전 정지(스케줄러 중복 방지) → 포털 라우트 전환 → 롤백 경로 확인
- [ ] cae00 병행 운영 확인 (클러스터 작업이 cae00 에 영향 0)

## Phase 4 — 이중화·100명 대비

- [ ] secrets → /data/hwax/secrets 정본화 (세션 로그아웃 1회 — 공지 후 야간)
- [ ] PAT store SQLite → Postgres (스냅샷 → 이중 read → 완전 전환, 롤백 절차 사전 문서화)
- [ ] portal·agent-server 복제 + entry nginx upstream (gen-nginx-conf upstream 블록 — v1 승계)
- [ ] 헬스게이트 replica 전수 프로브 (v1 승계)
- [ ] pgbouncer + PG 튜닝(shared_buffers 등) + 앱 커넥션 풀 명시
- [ ] 진입점 VIP (사내 협의 결과에 따라)

## Phase 5 — HEAX 앱 노드 배치 (v1 Phase 3 승계)

- [ ] 선행조사: 허브 Caddy 앱 프록시 정의 위치 확정 (v1 승계)
- [ ] 앱 상태 var/integration_state JSON → DB (`node` 컬럼)
- [ ] 원격 기동 (services.py ssh 경로 재사용)
- [ ] `resources:` 필수화 — 미기재 앱 등록 거부 + 노드 용량 인식 배치
- [ ] /data/appdata 앱별 바인드 마운트 격리 강제
- [ ] cluster.yaml `heax-apps:` 지원 (v1 승계 — v2 재작성에서 누락됐던 항목 복원)
- [ ] 앱 SIF 를 허브 로컬 var/sifs → /data 스테이징으로 (어느 노드든 앱 기동 가능하게)
- [ ] manifest `state:`/`endpoint:` + 허브 프록시/upstream + sqlite singleton 가드 (v1 승계)
- [ ] 검증: laminate 2-replica + materialtwin 단일 강제 + 게이트웨이 도구 수 유지 (v1 승계)

## cae00 전환 (마지막 — 별도 결정 후)

- [ ] cae00 데이터 스냅샷 → 클러스터 DB merge (비파괴 패턴 재사용)
- [ ] DNS/진입점 전환
- [ ] cae00 예비 강등 + 롤백 경로 확인
