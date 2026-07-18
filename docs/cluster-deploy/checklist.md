# 클러스터 배포 — 구현 체크리스트

plan.md 의 실행 추적용. 구현 착수 전에는 전부 미체크가 정상.

## Phase 0 — endpoints 계층

- [ ] `infra/scripts/gen-endpoints.sh` (cluster.yaml 없으면 전부 127.0.0.1)
- [ ] routes.env 를 endpoints 에서 생성 — 현행과 diff 0 확인
- [ ] provision-config.sh 백엔드 URL env 화(기본값=현행 127.0.0.1)
- [ ] update-all 헬스게이트 endpoints 소비
- [ ] agent mcp_servers.json 게이트웨이 주소 env 화
- [ ] 검증: dev 풀런 — 생성물 diff 0 + 헬스게이트 통과

## Phase 1 — cluster.yaml + cluster-deploy (1노드 동일성)

- [ ] `infra/cluster.yaml.example` + 파서(singleton 가드 포함)
- [ ] `infra/scripts/cluster-deploy.sh` — 자기노드 감지 / ssh 루프 / 클러스터 헬스게이트
- [ ] `update-all.sh --services` 필터 인자
- [ ] `--init` (ssh-copy-id · rclone.conf · NO_PROXY)
- [ ] 수용 테스트: 1노드 cluster.yaml ≡ 현행 (config·헬스 출력 diff 0)
- [ ] 회귀: cluster.yaml 부재 경로 = 현행 러닝북 그대로

## Phase 2 — 복제 + LB

- [ ] placement 리스트 + singleton 배포 거부
- [ ] gen-nginx-conf upstream 블록 생성
- [ ] 헬스게이트 replica 전수 프로브
- [ ] AIDH·SF DB 를 독립 배치 항목으로 분리(API 복제 전제)
- [ ] 검증: 2-replica 라우팅·failover 실측

## Phase 3 — heax 앱 단위 배치

- [ ] 선행조사: 허브 Caddy 앱 프록시 정의 위치 확정
- [ ] manifest `state:`/`endpoint:` + 허브 프록시/upstream + sqlite singleton 가드
- [ ] cluster.yaml `heax-apps:` 지원
- [ ] 검증: laminate 2-replica + materialtwin 단일 강제 + 게이트웨이 도구 수 유지
