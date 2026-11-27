# DynaForge(KooRemapper) 요청 — 자동 파이프라인 원천 + 전각도 낙하 해석(2026-11-27)

> 보낸 곳: KooRemapper 세션. 정본 계약 [../contract.md](../contract.md) v1.1(§0 공통 · §1 원천 · §2 해석). 배경 [../PLAN.md](../PLAN.md).

포털이 「과제 · 차수에 새 입력이 오면 정해 둔 해석을 저절로」 돌리려 한다(사용자 결정 11-27, 포털은 기본 꺼짐으로 미리 짓는 중). DynaForge 는
**원천**(새 덱 · 세션을 알림)이자 **전각도 낙하 해석의 주인**이다 — 공학 수치가 stcx 잡 → 후처리 예약 → sphere 리포트 사슬에서 나오기 때문이다
(ste 전각도는 완료 판정만 줘서 v1 에서 쓰지 않는다).

## 청할 것

- **KR-AP1 `auto_changes(since, limit)`** — 계약 §1 꼴. 새로 생기거나 바뀐 세션(덱)을 쪽 커서로 끝까지(지금 `list_sessions` 는 200 에서 잘린다).
  - `subject.project` · `revision` — 세션에 과제 · 개발 단계 칸이 없다(`linked_cad` 만). 세션을 허브 과제 · 차수(`list_tasks` · `task_revisions`)에
    잇는 칸 또는 `linked_cad` 로 StepForge 과제의 key · 차수를 따라가는 길을 정해 주세요. 모르면 null.
  - `inputs[]` = 세션 파일의 sha256. `ready.model_registered`(또는 그쪽이 정한 이름) = 해석에 넣을 수 있는 덱이 갖춰졌을 때.
- **KR-AP2 전각도 낙하 해석 다섯** — 계약 §2 의 `auto_profiles` · `auto_check` · `auto_submit` · `auto_status` · `auto_result`(+ 선택 `auto_cancel`).
  - profile 예 — 전각도 26방향 · 162방향(그쪽이 정한 조건 · 높이 · 판정 기준의 출처).
  - 제출 — 세션 덱 → stcx(SmartTwinMCP `fullangle_drop_simulation` 또는 `catalog_run`) → 후처리 예약(`run_operation(postprocess)`) → sphere 리포트.
    이 사슬을 `run_ref` 하나로 묶고 `auto_status` 가 다섯 낱말로 바꿔 준다(Job `succeeded` → `done` · `canceled` → `cancelled`).
  - 결과 봉투 — sphere 리포트의 공학 수치(이름 · 단위 · 값 · 기준 · 판정)와 그림 ref. 기준이 없으면 `verdict: unknown`.
  - `idem_key` 로 두 번 내지 않기(계약 §2).
  - 입력이 안 됐거나 클러스터가 못 받으면 `auto_check` 가 `missing` 으로 — 특히 **공유 폴더 SH-01 · 02 전에는 `infra`**(업로드 입력을 계산 노드가 못
    읽는다, 포털 docs/request-1125/cluster-shared-folder-request-20261127.md).
- **KR-AP3 서비스 신원 시야** — 서비스 신원은 게이트웨이 서비스 계정 명의로 닿아 지금은 그 계정 것 + 공개 세션만 보이고 캠페인은 0 이다.
  `auto_*` 도구에 한해 모든 과제를 읽게, 제출은 그쪽이 정한 서비스 계정 · KooSlurm 위임으로(운영이 계정을 정한다 — 받은 편지함 물음으로 함께 묻는다).
- **KR-AP4 표지** — `auto_submit` · `auto_cancel` 은 `readOnlyHint` 없음, 나머지는 `readOnlyHint: true`.

## 시험으로 보일 것

계약 §4 전부.

## 순서 · 올리기

- 포털은 계약 꼴의 가짜로 먼저 짓는다. KooRemapper 는 가지에서 지어도 되고 main · Drive 는 87 의 운영 회차에 맞춘다(착지 값 — 커밋 · Drive 판 ·
  이관 · 운영 손 할 일).
- 낙하 실주행은 KooSlurm SH-01 · 02 뒤다. 그 전에는 `auto_check` 가 `infra` 로 막는 것까지가 받아들이기다.
