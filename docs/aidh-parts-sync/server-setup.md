# AIDataHub 조각 스냅숏 — cae00 사람 몫

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 할 일 [checklist.md](checklist.md). 고친 날 2026-11-05(KST).
**설정할 것은 없다.** update-all §3 이 저절로 조각 길을 먼저 쓰고, 안 되면 예전의 전체 덤프 길로 간다. dev 가 하루 한 번(전체 덤프 뒤) 조각을 낸다.

## 0. 받는 판

| 리포 | 판 | 무엇 |
|---|---|---|
| AIDataHub | `918681d`(병합 — 앞선 병합 `7e98ad6` · `190ca57` · `5abff48` 를 잇는다) | 같은 줄은 다시 쓰지 않기 · 자식 표는 레코드를 이긴 쪽 · `fetch-parts.sh`(낡은 목록이면 5) · `merge-from-drive.sh` 조각 길 · `rollback-parts.sh` |
| 포털 | 0절 표(`docs/request-1030/server-setup.md`)의 같은 줄 | update-all §3 조각 길 먼저 · `backup-local.sh` 가 앞 모습 폴더도 7일 |

둘 다 update-all 이 받는다(§1 포털 · §2 AIDataHub 코드). 조각 자리는 전체 덤프 자리 옆이다 — `AIDH_DRIVE_REMOTE` 가 `<리모트>:AIDataHub/db-dumps` 면
`<리모트>:AIDataHub/db-parts`.

## 1. 첫 update-all — 조각 전부

- 첫 실행은 '병합함' 표식이 없어 **조각 전부**를 받는다(dev 첫 내기 실측 — 아래 표). 전체 덤프 길보다는 짧다 — 스테이징 색인을 짓지 않고 전체
  스냅숏(`pg_dump`)을 뜨지 않는다. 그 뒤로는 바뀐 조각만이고, 바뀐 것이 없는 날은 목록 하나만 받고 끝난다.
- 볼 줄 — 첫 실행 `✓ AIDH 조각 merge(바뀐 조각만 — dev 신규 반영 + cae00 데이터 보존)`, 다음부터 대개 `✓ AIDH 조각 변화 없음 — merge 생략`.
- 절 · 첨부 · 전문가 연결 줄 끝의 `이 박스 판이 이긴 레코드 K건의 줄 N개는 그대로` — 이 박스에서 고친 카드(더 새로움)의 자식은 dev 판으로 덮지 않는다(사용자
  결정 11-05, AP-16). 전체 덤프 길에도 같다.
- 디스크
  - 받은 조각 `~/Projects/AIDataHub/deploy/apptainer/backups/parts-cache/files` — 병합을 적으면(`--commit`) 비운다.
  - 덮을 줄의 앞 모습 `/data/backups/aidh/pre-parts-<시각>/` — 첫 병합은 운영 행 거의 전부라 전체 스냅숏만큼 크다. 포털 백업 cron(`backup-local.sh`)이
    7일 지나면 지운다(전체 길의 `pre-merge-*.sql.gz` 와 같은 줄).

| dev 첫 내기(2026-11-05 08:33 KST — 캐시가 빈 채 · 다른 시험과 겹쳐) | 값 |
|---|---|
| 조각 | 264 파일 · 6.4 GiB(전체 덤프 10.3 GiB) — 절 64 조각 5.6 GiB(조각 최대 100 MB) · 레코드 64 조각 0.8 GiB(최대 13 MB) · 표본 36 MB · 나머지 수 MB |
| 내기 시간 | 1,719초(29분) |
| 올리기 시간 | 708초(12분 — 9 MiB/s 남짓) · Drive 에 목록 하나 + 264 파일 |
| 레코드 하나가 바뀐 날 받는 것 | 그 레코드의 레코드 · 절 조각 둘 — 110 MB 안팎 |

## 2. 잘 안 될 때

- `⚠ AIDH 조각 merge 실패(rc N) — 아래 전체 덤프 길로 다시 한다` — 전체 길이 이어서 돈다(그 덤프를 이미 병합했으면 `덤프 변화 없음`). 원인은
  `/tmp/aidh-merge.log` · `/tmp/aidh-merge-load.log`. dev 와 cae00 의 PostgreSQL · pgvector 판이 다르면 이진 조각이 실리지 않는다(같은 SIF 라 같아야 한다).
- `⚠ AIDH 조각 목록이 전체 덤프보다 하루 넘게 낡았다` — dev 의 하루 한 번 조각 내기가 멈췄다. 이 실행은 전체 덤프 길로 병합된다(데이터는 받는다).
  받은 편지함으로 알린다 — dev 쪽에서 고친다.
- `⚠ AIDH 조각 merge 는 됐지만 dev 에만 있는 열이 빠졌다` — 운영 DB 이행(`start_api.sh` 의 alembic)이 늦었다. 이행 뒤 손으로 한 번(아래).
- `○ AIDH 조각 동기화 — Drive 에 조각 목록이 없다` — dev 의 하루 한 번 내기가 아직 안 돌았거나 이 박스가 그 자리를 못 본다. 전체 길로 병합된다.
  `rclone lsf <리모트>:AIDataHub/db-parts/` 로 목록(`manifest-*.json`)이 보이는지 보고 받은 편지함으로.
- 잠깐 끄기 — `AIDH_SYNC_MODE=full ./infra/scripts/update-all.sh`(그 실행만 전체 덤프 길).
- 손으로 한 번 —
  ```bash
  cd ~/Projects/AIDataHub && ./deploy/apptainer/fetch-parts.sh \
    && AIDH_MERGE_PARTS=1 ./deploy/apptainer/merge-from-drive.sh && ./deploy/apptainer/fetch-parts.sh --commit
  ```
  `fetch-parts.sh` 의 끝 코드 — 0 받음 · 10 바뀐 것 없음 · 4 목록 없음 · 5 목록이 낡음.
- 되돌리기 — merge 출력 끝 줄의 폴더로
  ```bash
  cd ~/Projects/AIDataHub && bash deploy/apptainer/rollback-parts.sh /data/backups/aidh/pre-parts-<시각>
  ```
  병합 뒤 이 박스에서 같은 줄을 또 고쳤으면 그 고침도 앞 모습으로 간다 — 되돌리기 전에 본다.

## 3. 알릴 것(받은 편지함)

첫 조각 merge 가 끝난 update-all 의 §3 줄 — `받음 N 파일 · 크기 · 초` · `staging 에 조각 N개를 실었다` · 걸린 시간, 그리고 그다음 update-all 이
`조각 변화 없음` 으로 끝났는지.
