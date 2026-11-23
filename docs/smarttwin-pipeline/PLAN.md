# 스마트트윈 낙하 파이프라인 — dev 가 고칠 수 있는 것을 고친다

> 할 일 [checklist.md](checklist.md) · 결정과 까닭 [context-notes.md](context-notes.md).

사용자 지시(2026-11-12): "우리가 해 줄 수 있는 건 개선해야지." 전처리 → stcx(356대) 해석 → 후처리 → DynaForge 리포트로 이어지는 낙하 트윈 가운데,
운영 측을 기다리지 않고 dev 가 고칠 수 있는 것을 고친다.

## 1. 지금 상태(2026-11-12 조사 — context-notes SP-1)

| 단계 | 운영(cae00 · stcx) | dev |
|---|---|---|
| 전처리 | cae00 DynaForge 는 11-08 판(바이너리 `c5f74c18`). stcx 전처리 이미지는 10-29 판(v135 · v136 안 깔림 — 운영 측 몫) | 헤드 v136 · 노드 VM 꺼짐 |
| 제출 · 해석 | SmartTwinMCP 가 cae00 게이트웨이에 없다(HP-51 · OB-92 — PA-16, stcx `:5013` 확인 전). 포털 R2a 와 DynaForge stcx 제출은 cae00 에서 막혀 있을 것이다(추정) | LS-DYNA 라이선스 만료 · 노드 VM 꺼짐 |
| 후처리 | stcx Post v50(v51 안 깔림 — 운영 측 몫) | 헤드 v51 |
| 리포트 반입 | DynaForge 후처리 예약(REST 직결)은 된다. '운영 첫 실제 전각도 잡 끝까지 한 번'(가이드 §4) 기록이 없다 | DynaForge stcx 설정이 비어 있다 |

## 2. 확인한 결함

- **F1** — Drive 의 `SmartTwinPreprocessor.sif` 가 11-11 에 v136(`1c973c25…`)으로 덮어쓰였다. 2026-11-09 Q5 와 가이드 §1-4 는 v135(`da892a35…`)를 적는다 —
  운영이 지금 받으면 sha 대조에서 멈춘다. pyKooCAE 는 다른 세션에는 알렸지만 포털에는 알리지 않았다.
- **F2** — 가이드 §1-4 가 노드 배포에 `deploy_compute_images.sh` 를 적었다. 그 스크립트는 아무도 읽지 않는 `/opt/apptainers/compute` 에 쓰고, 셈이 서브셸에서
  돌아 늘 '완료' 를 찍는다.
- **F3** — KooSlurm `phase8_containers.sh --image`(운영 문서의 길)가 노드 파일 **크기만** 견줘 같으면 건너뛴다. 크기가 같은 다른 빌드가 실제로 있다(Post
  `ff71b03` · `7bc1f78` 둘 다 1,156,497,408 B). 이번 판들(v50 → v51 · v135 → v136)은 크기가 달라 걸리지 않는다. 복사 뒤 sha256 확인도 없다.
- **F4** — 리포트 셸의 '헤드와 노드 판이 다르다' 경고는 판 비교가 아니라 기능 탐침(`--parallel-runs`)이다. v50 과 v51 을 가리지 못한다.
- **F5** — 가이드가 보라는 잡의 `external_ref.ontology.state` 를 MCP · 화면으로 읽을 수 없다(REST `/api/jobs/{id}/diagnostics` 에만 있다).
- **F6** — 빌드 산출이 Drive 에 늘 같은 이름으로 올라가 앞 판을 덮고, 알림 메일은 sha256 이 아니라 md5 다.

## 3. 고치는 차례

| 차례 | 무엇 | 주인 | 언제 |
|---|---|---|---|
| 1 | 포털 문서 정정 — F1(판 · sha) · F2(노드 배포 길) · F3 주의(배포 뒤 sha 확인) | 포털 | 지금(문서만 — 박스 동작 영향 없음) |
| 2 | 노드 배포를 안전하게 — 크기+시각 견주기 · `--verify-only` · sha 확인(선택) · 같은 파일시스템에 두고 원자 교체 · 옛 스크립트 걷기 | KooSlurm | 가지 → 판 고정 풀린 뒤 |
| 3 | DynaForge API 셋 — `get_job` 에 `external_ref` 요약 · `find_reports` 의 `external_job_key` 거르기 · 최근 반입 리포트에서 '관측된 후처리 판' 보기 | KooRemapper(DynaForge) | 가지 → 판 고정 풀린 뒤 |
| 4 | 포털 절차 씨앗 R2c '결과 귀환 확인'(읽기만 — 잡 → 리포트 → 해석 연결을 가이드 §4 · §5-1 항목대로) | 포털 | 가지 → 판 고정 풀린 뒤 |
| 5 | 읽기 전용 이미지 점검 스크립트(stcx 헤드 · 표본 노드 · NFS 의 판과 기대값 대조 — cae00 붙여넣기) | KooSlurm | 2 와 함께 |
| 6 | 귀환 매니페스트에 이미지 출처(`images{}` — 노드 · SIF · VERSION · KooRemapper 판) — F4 를 대신한다 | KooSlurm · pyKooCAE · KooRemapper | 3 · 5 뒤 |
| 7 | 빌드 산출을 판 이름 + `SHA256SUMS` · `release.json` 으로(덮어쓰기 금지 · 'latest' 는 별칭) — F6 | pyKooCAE · KooD3plotReader | 다음 빌드부터 |
| 8 | 해석기 없는 dev E2E(이미 있는 결과 사본 → 후처리 잡 → DynaForge 반입 → R2c) | KooSlurm · 포털 | 노드 VM 켜기 — 사용자 결정 |
| 9 | SmartTwinMCP 이미지 도구 · cae00 게이트웨이 등재 | KooSlurm(SmartTwinMCP) | PA-16 확인 뒤 |

## 3-1. 7 의 정의 — Drive 이름 규칙(2026-11-23, context-notes SP-4)

자리는 지금 그대로 `ApptainerImages:SmartTwinPreprocessor/` 하나다(전처리 · 후처리가 함께 쓴다). 첫 적용은 **다음 굽기(Pre v142 · Post v54)** 부터 —
v141 · v53 은 지금 꼴 그대로 둔다.

| 갈래 | 이름 | 덮어쓰기 |
|---|---|---|
| 판 파일(SIF) | `SmartTwinPreprocessor_<YYYYMMDD>_v<N>.sif` · `SmartTwinPostprocessor_<YYYYMMDD>_v<N>.sif` · `SmartTwinPostprocessorGUI_<YYYYMMDD>_v<N>.sif` | **금지** |
| 판 파일(설치 묶음) | `SmartTwinPreprocessor_<YYYYMMDD>_v<N>.tar.gz` · `SmartTwinPostprocessor_<YYYYMMDD>_v<N>.tar.gz`(지금 꼴 그대로) | **금지** |
| 판 해시 | `<제품>_<YYYYMMDD>_v<N>.SHA256SUMS` — 그 판 파일 전부, `sha256sum` 꼴(두 칸 띄움 · 파일 이름만) | **금지** |
| 별칭(latest) | `SmartTwinPreprocessor.sif` · `SmartTwinPostprocessor.sif` · `SmartTwinPostprocessorGUI.sif` — 가장 새 판 SIF 와 같은 바이트 | 판이 오를 때만 |
| 별칭 안내 | `<제품>.release.json` — 아래 꼴 | 판이 오를 때만 |

- **쓰는 곳** — 판 해시 · `release.json` 은 pyKooCAE 굽기 스크립트가 Pre · Post 둘 다 쓴다(`serviceApptainers/scripts/release_manifest.py` · 올리기 `notify_build.py --release-json --sums`, 11-23). 날짜는 KST 다(tar 이름도 같은 날짜).
- `<제품>` 은 `SmartTwinPreprocessor` · `SmartTwinPostprocessor` 둘이다(GUI SIF 는 Post 판에 딸린다). `<YYYYMMDD>` 는 굽은 날(KST), `v<N>` 은 제품마다 한 번만 쓴다 —
  같은 날 다시 구우면 N 을 올린다.
- 해시 파일을 판마다 따로 두는 것은 두 세션(pyKooCAE · KooD3plotReader)이 같은 파일을 고치지 않게 하려는 것이다.
- `release.json` 꼴 — `{"product", "version": "v142", "date": "20261124", "files": {"<이름>": {"sha256", "bytes"}}, "alias": {"<별칭 이름>": "<판 파일 이름>"},
  "built_from": {"<리포>": "<커밋>"}}`. 커밋 대신 바이너리 해시가 정본이면 `built_from` 에 그 값을 적는다(예: Pre 의 KooRemapper 바이너리).
- **올리는 차례** — 판 파일 → 판 해시 → Drive 쪽 sha256 이 판 해시와 같은지 확인 → 별칭 SIF → `release.json` 마지막. `release.json` 이 바뀌기 전까지 별칭은
  '아직 앞 판' 으로 읽는다(올리다 끊기면 `release.json` 과 별칭 SIF 의 해시가 어긋나 보인다 — 받는 쪽은 그때 멈춘다).
- **받는 쪽(cae00 · 받은 편지함)** — 별칭 이름을 받아도 된다(지금 가이드 · 절차 그대로). 다만 받은 편지함은 늘 **판 파일 이름 + sha256** 을 함께 적고, 받는 쪽은
  sha256 이 다르면 멈춘다 — 별칭이 그 사이 다음 판으로 바뀌었다는 뜻이다. 그때는 판 파일 이름으로 받는다.
- **알림** — 메일 · 세션 알림은 md5 가 아니라 sha256 을 적는다(F6).
- **지우기** — 판 파일은 지우지 않는 것이 기본이다. 자리가 모자라면 주인 세션이 가장 오래된 판부터 지우되, 가장 새 받은 편지함이 cae00 · stcx 에 깔린 판으로 적은
  판과 그 바로 앞 판은 남긴다.

## 4. 지키는 것

- 판 고정 중이다(cae00 이 2026-11-12 글을 받을 때까지). 다른 리포는 가지에서 짓고 보류가 풀린 뒤 올린다. 포털 문서 정정만 지금 올린다.
- stcx 에 직접 깔지 않는다 — 설치는 운영 측 몫이다. dev 는 깔기를 쉽고 틀리기 어렵게 만드는 쪽(스크립트 · 점검 · 정확한 판)을 한다.
- 이 리포는 공개다 — 내부 주소 · 계정 · 실제 이름을 적지 않는다.
