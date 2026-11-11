# 11-11 cae00 결과 보고 — 결정 · 까닭

> 원문 [request.md](request.md) · 계획 [PLAN.md](PLAN.md).

## R11-1 보고서의 기준 판은 core-link 병합 전이다

cae00 이 11-11 에 돌린 판(포털 `9f1b3ddc` 등)은 core-link 를 main 에 올리기 전이다. 보류(core-link CK-7)가 지켜졌다. 그래서 보고서의 HP-53 수 · 미리 보기는
게이트웨이 쓰기 낱말 link · edit · sync(SRC-14)가 들어가기 전 판으로 센 것이다. 다음 update-all 뒤에는 목록 밖 쓰기가 더 짚힌다. HP-53 은 dev 의 지금 판
(SRC-14 포함)으로 다시 센다.

## R11-2 PA-21 — 해석기 SIF 는 공유 `/data/SmartTwinSolutions/<해석기>/`

KooSolverContainer 가 코드로 답했다. `/opt/apps/sif` · `/opt/apps/sif-web` 은 헤드 로컬이고, 백엔드 preflight 는 헤드를 계산 노드로 쓰지 않는다. 지금 ste 에서
도는 앱(koo-sph · koo-openlb · condensation 대체 경로)이 모두 공유 자리를 쓴다. 새 앱 넷의 `app.yaml` · 래퍼가 `/opt/apps/sif` 를 박아 두었다. 그래서 고치는 판은
06 이 D-23 과 한 묶음으로 짓는다. 셋째 물음(앱 스크립트를 노드가 어떻게 읽나)은 condensation 잡의 성공 기록 하나로 갈리므로 운영에 되물었다(받은 편지함
2026-11-11 Q1).
