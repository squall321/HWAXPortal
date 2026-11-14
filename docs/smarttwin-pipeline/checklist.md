# 스마트트윈 낙하 파이프라인 개선 — 할 일

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

- [x] 조사 — 이미지 쓰임 · 설치 길 · 판 점검 · 끝까지 한 번 · dev E2E 가능성 · 열린 결함(SP-1)
- [x] 결함 셋 직접 확인 — F1 Drive Pre v136 덮어씀 · F2 옛 배포 스크립트 · F3 크기만 견주기
- [x] 사용자 결정 — D1 전처리 v136 · D2 dev 노드 VM 켜서 돌린다 · D3 dev 값은 세션들이 dev 전용으로 맞춘다(SP-2)
- [x] 1 포털 문서 정정 — 2026-11-12 Q15(전처리 SIF + NFS tar · 후처리 v51 · 노드 배포 길 · 확인 값) · 가이드 §1-4 · §5-1 · 2026-11-09 Q3 · Q5 에 대신함 표시
- [x] 2 KooSlurm(-de) — 노드 배포 안전 지음(가지 `feat/dropline-node-deploy` `357c7b65` · `af33570a` · `4279c9de` · `f4722b03` · `6f4ddf29`, 판 고정 동안 안 올림, 11-14):
  크기 + 시각이 같아야 같은 판(설치가 원본 시각을 고정 — 같은 크기 다른 빌드 · 옛 판 되돌림을 잡음) · `--verify-only`(아무것도 안 씀, 노드별 표, 다르면 exit 1) ·
  `--sha256` / `--sha256-sample N`(원본은 한 번만) · 원자적 교체(대상 파일시스템에 임시 → rename, 열린 옛 SIF 는 옛 inode) · 컨트롤러 사본도 같은 절차 ·
  phase3 Step 16 이 `apptainer/deploy_compute_images.sh` 를 더는 부르지 않음(파일은 gitignore 라 cae00 · icn401 의 사본은 손으로 지운다 — 받은 편지함 몫) ·
  덤으로 phase8 의 `$SCP_OPTS` 미정의 · set -e 요약 줄 · `--image` 가 --dry-run · --nodes-file 을 무시하던 것도 고침. 지역 시험 62 통과
- [ ] 2b node001 에서 `--verify-only` 실측 — dev 노드 VM 을 켜야 한다(지금 남은 메모리 31 GB, 30 GB 규칙에 걸림 — 사용자 결정) · 그쪽 사용자 승인
- [x] 5 KooSlurm(-35) — 읽기 전용 이미지 점검 `cluster/utils/image_version_check.sh`(가지 `feat/dropline-check-e2e` `de55def2` · dev 전 항목 OK) — 다음 라운드 받은 편지함에
- [x] 3 DynaForge(fd) — 가지 `dropline-1112`(`734e735` API 셋 · `8073ebb` 점검 스크립트 · 절차) — 판 고정 풀린 뒤 main · dev API 재기동
- [ ] 7 pyKooCAE(굽기 스크립트 — 그쪽 사용자 결정 대기) · KooD3plotReader — 판 이름 산출 · `SHA256SUMS` · 포털에도 알림
- [ ] 4 포털 절차 씨앗 R2c(가지)
- [ ] 6 귀환 매니페스트 이미지 출처(3 · 5 뒤)
- [ ] 8 해석기 없는 dev E2E — 준비 끝(KooSlurm `70774ded` · DynaForge dev 값 · e2etest), ① node001 배포까지 하고 멈춤(메모리 30 GB 밑 — 사용자 결정, SP-3).
      다음에 ② 부터 — 메모리 확보 뒤 사용자에게 다시 묻는다
- [ ] 9 SmartTwinMCP — cae00 받은 편지함에 PA-16(stcx `:5013`) 확인 묻기
