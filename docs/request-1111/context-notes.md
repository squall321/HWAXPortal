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

## R11-3 HP-53 — dev 에도 있는 앱의 목록 밖 쓰기를 가르고, RA 도구는 도구마다 선택 칸으로

- dev 의 지금 판(SRC-14 포함)으로 다시 셌다. 넣은 것은 DynaForge writes 일곱 · confirm 셋, AIDataHub `draft_agent`, MX 백서 `upload_image_bytes`,
  WDA `approval_record`(WDA 세션이 쓰기라고 확인), SmartTwin writes 셋, StepForge `link_plm_tasks` 다. 마지막은 SRC-03 의 새 도구로, `dry_run` 이
  기본이고 MCP 로도 적용하므로 writes 다(StepForge `app/mcp_server.py` 의 `@register(mcp, MODIFY)`).
- 지우기 · 끊기 · 폐기 · 합치기 · 옮기기 · 타입 대응은 되돌리기 어렵다고 보고 confirm 에 넣었다. 나머지는 writes 다.
- 이름은 쓰기 꼴인데 읽기인 둘은 게이트웨이 읽기 목록에 넣었다. RA `run_saved_search` 와 리스크 `risk_propose_board_transform` 이다(게이트웨이 `38ac79f`).
- RA 는 dev 게이트웨이에 없어 이름을 dev 에서 맞대 볼 수 없다. 필수 목록(writes · confirm)에 그 박스에 없는 이름이 하나라도 있으면 동기화가 통째로
  멈춘다. 그래서 RA 쓰기 열여덟(writes 열하나 · confirm 일곱)은 도구마다 `needs_tool` 선택 칸으로 넣었다(SP 0.4.72 와 같은 꼴). 이름은 RA 최신판
  (origin/main `b552f09` — 받기만 하고 그 리포에는 쓰지 않았다)의 데코레이터 도구와 견줘 48개 모두 있음을 확인했다.
- DocForge 운영자의 RA 선택 앱도 같은 꼴로 RA 운영자의 쓰기 · 확인 전부(40)를 도구마다 칸으로 넣었다.
- 앱이 통째로 없으면 동기화 알림이 칸마다 같은 앱 이름을 적었다(`reportarchive, reportarchive, … 외 33개`). 한 번만 적게 고쳤다
  (`sync-he-personas.py` `_with_optional`).
- dev 대조(게이트웨이를 새 읽기 목록으로 다시 띄운 뒤)에 남은 알림은 둘이다. StepForge onto_* 셋은 C-30 그대로다 — MCP 로는 미리 보기만 되고 적용은
  챗의 REST 다리 확인 카드다. Laminate 둘은 Laminate 0.29.0(도구 43개 모두에 표지)이 Drive 에 오르면 사라진다.
