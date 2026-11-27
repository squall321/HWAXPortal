# StepForge 요청 — 자동 파이프라인 원천(`auto_changes`)(2026-11-27)

> 보낸 곳: StepForge 세션. 정본 계약은 [../contract.md](../contract.md) v1.1(§0 공통 · §1 원천). 배경은 [../PLAN.md](../PLAN.md).

포털이 「과제 · 차수에 새 CAD 가 올라오면 정해 둔 해석을 저절로」 돌리려 한다(사용자 결정 11-27, 포털은 기본 꺼짐으로 미리 짓는 중). StepForge 는
**원천** — 새 CAD 개정을 포털에 알리는 쪽이다. 해석은 하지 않는다.

## 청할 것

- **SF-AP1 `auto_changes(since, limit)`** — 계약 §1 꼴. 마지막으로 본 뒤 새로 생기거나 파싱이 끝난 과제(= CAD 개정)를 쪽 커서로 끝까지.
  - `subject.project` = 허브 `plm_task` key(`get_project_meta.plm_task.key` — 과제코드 `task_code` 가 아님). 못 이었으면 null.
  - `subject.revision` = 개발 단계 코드(DynaForge `dev_rev` 낱말 `pre` · `dv1` … · `mp`). **지금 StepForge 에는 이 칸이 없다**(`rev_label` 은 자유
    이름). 허브의 과제 차수(DynaForge `task_revisions` 의 `<과제명>@<code>`)와 잇는 길을 먼저 검토해 주세요. 모르면 null(포털이 막힘으로 세운다 —
    짐작 금지).
  - `subject.refs.step_forge` = 과제 id. 앞 판을 `supersedes` 로 이은 것이 있으면 `refs` 에 함께(선택).
  - `inputs[]` = 업로드 파일(`step_files`)의 sha256 · 올린 시각.
  - `ready.parsed` = 마지막 parse 잡이 끝난 상태일 때만 true.
  - 커서 — 지금 목록에 갱신 시각이 없다(`created_at` · `last_parse.at` 뿐). 커서가 「새 과제 + 파싱 끝 시각」을 함께 넘을 수 있게 정해 주세요.
- **SF-AP2 서비스 신원** — 지금 MCP 길은 신원을 안 읽어 전부 보인다(정책 `read: all_projects`). 그대로면 된다. 게이트웨이 허용 목록에 적을 이름은
  `heax-step_forge:auto_changes` 다(운영 박스 파일).
- **SF-AP3 표지** — `readOnlyHint: true`.

## 시험으로 보일 것

계약 §4 의 3 · 5 · 6(isError false 에 error 없음 · 모르는 key · 단계는 null · 서비스 신원으로도 전부) + 쪽을 끝까지 넘김.

## 순서 · 올리기

- 포털은 계약 꼴의 가짜로 먼저 짓는다. StepForge 는 가지에서 지어도 되고, main · Drive 는 87 의 운영 회차에 맞춘다(ST-25 처럼 착지 값 — 커밋 ·
  Drive 판 · SIF 수 둘 · 운영 손 할 일).
- 과제 · 파트 이름을 공개 리포 · 받은 편지함에 적지 않는다.
