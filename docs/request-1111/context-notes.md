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

## R11-4 SignalForge cae00 알림 · 벡터 — 사용자 결정 넷, 모두 권장안(11-11)

SignalForge 세션이 켜는 길을 제안했다(알림 ① dev 계산 → 병합 · 벡터 ② cae00 cron, ③ cae00 Redis · beat 는 권하지 않음). 사용자가 정할 넷을 선택지로
물었고 넷 다 권장안을 골랐다.

| 물음 | 고른 것 | 버린 것 |
|---|---|---|
| cae00 화면에 dev 운영 알림 넷(수집 상태 · 운영 상태 위반 · 운영 감시 · 백업 실패) | **가린다 — 결함 급등만** | 보인다(dev 수집이 멈추면 cae00 도 안다) |
| 지표 규칙 다섯(dev 에서도 평가가 안 걸려 0건) | **지금은 안 켠다** | dev 에서 켠다(병합으로 cae00 에도) |
| 바깥 웹훅 | **dev 에서만**(cae00 은 웹훅 주소를 비운다 · 보낸 표시가 병합으로 따라간다) | cae00 에서만 · 보내지 않는다 |
| cae00 ollama + bge-m3 | **둔다 — cae00 cron 증분**(2시간마다 600초) | 지금은 안 둔다(낱말 검색만) |

- 가리는 자리(병합에서 빼기 · 화면에서 거르기)는 SignalForge 판단에 맡겼다. 다만 cae00 이 그 알림을 다시 보내거나 세지 않게 했다.
- ollama 설치 · cron 한 줄은 cae00 사람 몫이다. SignalForge 착지 알림을 받으면 받은 편지함에 싣는다.

## R11-5 HP-64 — 병합 뒤 운영자 되돌리기를 update-all §3 이 저절로(병합 `c0f454ba`)

cae00 요청 (나)를 그대로 지었다. 새 모드 `sync-he-personas.py --backup <폴더>` 와 §3 끝의 차례(미리보기 → 백업 · 개수 확인 → `--apply` → 다시 미리보기)다.
요청서와 다르게 정한 것이 셋이다.

- **미리보기가 먼저다.** 어긋남이 있을 때만 백업 · 반영한다. 어긋남이 없는 실행은 백업도 남기지 않는다(✓ 한 줄).
- **정본에 없는 he-* 는 세지 않는다.** 백업에는 넣는다. 11-11 cae00 은 행 21 · git 운영자 19 였다. 남는 둘이 정본에 없는 행이면 글자 그대로의 '개수가
  같아야 한다' 는 실행마다 막힌다. 그래서 '합친 정의의 운영자가 다 들었나' 로 센다.
- **덧씌우기가 깨졌으면 반영하지 않는다.** 깨진 덧씌우기는 버려지고 기본 정의로 돈다. 그대로 `--apply` 하면 박스의 덧씌우기 고침을 기본 판으로 덮는다.

알고 받을 것.
- 저절로는 운영자를 새로 만들지 않는다. 새 운영자(미리보기 `+`)가 있으면 ⚠ 로 멈추고 사람이 `--apply` 한다.
- 어느 박스에도 행이 생길 수 없는 운영자가 정의에 있으면 실행마다 멈춘다. 그 박스 덧씌우기에서 `null` 로 뺀다. 지금은 없다 — dev 가 만든 행은 병합으로
  cae00 에 오고, cae00 에만 있는 앱의 운영자는 cae00 이 만든다.
- 되돌리는 명령은 따로 없다. 백업 파일의 칸을 PATCH 한다. 백업은 `daily/` 밖이라 세대 정리가 지우지 않는다(한 벌에 100KB 안팎).
- AIDataHub 를 못 읽으면 모름으로 다루고(rc 2) 반영하지 않는다. 0건 백업(11-09 의 다른 칸 거르기)도 여기서 막힌다(rc 1).
- 시험은 새 단위 8 · 구역 12(진짜 스크립트를 가짜 게이트웨이 · AIDataHub 와 임시 백업 자리에 돌린다)이고, 사본에서 코드를 13가지로 일부러 깨 모두 잡혔다.
  전체 회귀는 4,628 통과 · 실패 2(ste_doctor · tlscert — 앞선 기준 판에도 있던 것)다.

