# 스마트트윈 낙하 파이프라인 개선 — 할 일

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

- [x] 조사 — 이미지 쓰임 · 설치 길 · 판 점검 · 끝까지 한 번 · dev E2E 가능성 · 열린 결함(SP-1)
- [x] 결함 셋 직접 확인 — F1 Drive Pre v136 덮어씀 · F2 옛 배포 스크립트 · F3 크기만 견주기
- [x] 사용자 결정 — D1 전처리 v136 · D2 dev 노드 VM 켜서 돌린다 · D3 dev 값은 세션들이 dev 전용으로 맞춘다(SP-2)
- [x] 1 포털 문서 정정 — 2026-11-12 Q15(전처리 SIF + NFS tar · 후처리 v51 · 노드 배포 길 · 확인 값) · 가이드 §1-4 · §5-1 · 2026-11-09 Q3 · Q5 에 대신함 표시
- [ ] 2 KooSlurm(-de) — 노드 배포 안전(그쪽 사용자 확인 뒤)
- [x] 5 KooSlurm(-35) — 읽기 전용 이미지 점검 `cluster/utils/image_version_check.sh`(가지 `feat/dropline-check-e2e` `de55def2` · dev 전 항목 OK) — 다음 라운드 받은 편지함에
- [x] 3 DynaForge(fd) — 가지 `dropline-1112`(`734e735` API 셋 · `8073ebb` 점검 스크립트 · 절차) — 판 고정 풀린 뒤 main · dev API 재기동
- [ ] 7 pyKooCAE(굽기 스크립트 — 그쪽 사용자 결정 대기) · KooD3plotReader — 판 이름 산출 · `SHA256SUMS` · 포털에도 알림
- [ ] 4 포털 절차 씨앗 R2c(가지)
- [ ] 6 귀환 매니페스트 이미지 출처(3 · 5 뒤)
- [ ] 8 해석기 없는 dev E2E — KooSlurm 준비 끝(`70774ded` · 시험 잡 9000001 · 결과 사본), DynaForge dev 값 두 줄 · e2etest 사용자 남음 → node001 켜기 → ①~⑥
- [ ] 9 SmartTwinMCP — cae00 받은 편지함에 PA-16(stcx `:5013`) 확인 묻기
