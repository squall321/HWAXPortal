# MaterialTwin 이관 잔여 셋 · 크론 둘 — MaterialTwinWeb 세션에(요청 · 2026-10-31)

| 항목 | 내용 |
|---|---|
| 받는 곳 | MaterialTwinWeb 세션(데이터 주인). |
| 근거 | 데이터 이관 [checklist](../checklist.md) D2 잔여 줄('`.agent_work` → … `source.local_path` 18행 UPDATE …' — 10-31 판 45줄)에 붙은 사용자 결정 10-31 A4 ①('MaterialTwin 담당 세션에 넘긴다' — followups-1017 X1 ~ X3 '데이터 정리는 MaterialTwin 담당' 과 같은 길) · 같은 날 A2 ①(D5 는 보류 유지, 그러나 D5 줄의 MaterialTwin 크론 둘은 D5 와 무관하게 MaterialTwin 담당 몫 — 10-31 판 55줄 ⑤ · 59줄) · [PLAN](../PLAN.md) §7.4 · §7.15 · §9 · §12 8번(결정 17) · [triage-1031](../../leftovers-1017/triage-1031.md) A2 · A4 |
| 대조한 것 | MaterialTwinWeb main `4273720` · dev 박스 2026-10-31 15:00 KST 무렵. 크기는 `du`, 행 수는 운영 DB 를 읽기 전용(`immutable`)으로 열어 셌다. 옮기거나 지운 것은 없다. |
| 범위 | dev 박스다. cae00 에 같은 것이 있는지는 그쪽이 본다. |

경로는 MaterialTwinWeb 리포 기준이거나 앱 데이터 자리(`$HEAX_DATA_DIR` — 허브가 컨테이너에 `/data` 로 붙인다. dev 호스트에서는 허브
`var/app_data/materialtwin_web` 이 가리키는 `<데이터 루트>/appdata/materialtwin_web/`) 기준이다.

## 1. 이관 잔여 셋

| # | 무엇 | 자리 | 크기 · 수(10-31) |
|---|---|---|---|
| ① | `.agent_work/` — 작업 산출물(원문 PDF · 추출 글 · 그림 · 배치 폴더) | 리포 안 `.agent_work/` — `.gitignore:55` 라 추적되지 않는다(stash 위험 없음) | 485M · 꼭대기 50개 · 파일 702 |
| ② | `source.local_path` 가 오래 가지 않는 자리를 가리키는 행 | 운영 DB `source` 표(3,165행 가운데 `local_path` 가 찬 903행) | 19행 — 18행은 `.agent_work/` 안의 원문(배치 폴더 w3e 1 · w37av 1 · w43ec 4 · w56rd 1 · w57sa 1 · w58tb 5 · w58tc 1 · w60va 4, 파일 18개 모두 있고 합 약 27MB), 1행은 세션 임시 폴더(`/tmp/…`)라 파일이 이미 없다. source id — 2341 · 3641 · 4552 · 4658 · 4685 ~ 4688 · 4753 · 4765 ~ 4770 · 4775(임시 폴더) · 4810 ~ 4812 |
| ③ | `materialtwin.db.pre-*` 작업 사본 | `$HEAX_DATA_DIR/` | 31개 · 2.4G(08-11 ~ 09-16, 하나 20 ~ 86MB) + 그 가운데 13개 곁의 `-shm` · `-wal` 26개 |

②의 나머지 884행(코퍼스 · 측정 카탈로그 · 규격 자료를 가리킨다)은 이 요청 밖이다(PLAN §7.4 — 그대로).

**바라는 것**
1. ② 의 18행 — 가리키는 원문을 오래 가는 자리로 옮기고 그 행을 고친다. PLAN §7.15 ② 의 안은 `$HEAX_DATA_DIR/sources/agent_work/<배치>/<파일>`
   (컨테이너에서 보이는 자리)이다. 자리는 그쪽이 정한다.
2. ② 의 id 4775 — 원문을 다시 구해 같은 자리로 옮기거나, 못 구하면 `local_path` 를 비우고 까닭을 남긴다. 출처 행은 지우지 않는다.
3. ① 의 나머지(원문 18개를 뺀 것) — 남길 것과 지울 것을 그쪽이 가른다.
4. ③ — PLAN §9 의 처방(한 번 묶어 보관한 뒤 지운다)을 따를지, 그대로 둘지 그쪽이 정한다. 묶는다면 둔 곳과 크기를 적는다.
5. **지우기는 확인 뒤** — ① · ③ 모두 지울 목록(경로 · 크기)을 먼저 보이고, 사람이 확인한 묶음만 지운다(데이터 이관 결정 17 — PLAN §12 8번 '목록
   확인 뒤 지우기'). 이 요청은 지우라는 것이 아니라 목록을 만들어 확인받으라는 것이다.

## 2. MaterialTwin 크론 둘(A2 — D5 와 무관하게 MaterialTwin 담당 몫)

dev 사용자 crontab(10-31 대조 — 줄 번호는 박스마다 다르니 내용으로 찾는다)에 둘이 있다.

| 크론 | 무엇 |
|---|---|
| `*/30 * * * *` `HEAX_DATA_DIR=<허브>/var/app_data/materialtwin_web` `scripts/drive-sync/sync-to-drive.sh --no-sif` | 30분마다 운영 DB 로 이식 번들을 만들어 Drive `data-bundles` 에 올린다(5세대 — `scripts/drive-sync/PROJECT.conf:10` · `_common.sh:15`) |
| `25 5 * * *` `scripts/drive-sync/sync-to-drive.sh --no-data` | 매일 SIF 를 Drive 에 올린다(같은 해시면 건너뛴다) |

**문제 둘 — 30분 크론**
- **ⓐ 라이브 DB 에 이행을 돈다.** `sync-to-drive.sh:31-32` 가 `python -m app.sync export` 를 부르고, `backend/app/sync.py:394` 의 `init_db()` 가
  `backend/app/db.py:128-129` 에서 `alembic upgrade head` 를 라이브 DB 에 돈다. 그래서 라이브 스키마가 떠 있는 컨테이너 코드보다 앞설 수 있다(09-05
  실측 — PLAN §7.4). 컨테이너가 다시 뜰 때 모르는 리비전으로 기동이 깨질 수 있다(PLAN §11).
- **ⓑ 받는 곳이 없다.** 포털 · 허브 배포 스크립트에서 이 묶음을 받는 곳이 0이다(10-31 grep — update-all · deploy-all 은 AIDataHub · SignalForge 묶음만
  받는다). 박스 사이 MaterialTwin 데이터는 허브 app-data 병합으로 간다(PLAN §7.15 ④).

**바라는 것**
1. ⓐ — export 가 라이브 DB 에 이행을 돌지 않게 한다. PLAN §7.15 ③ 의 안(`.backup` 사본을 임시 폴더에 떠서 거기서 뽑는다)이든, export 길에서
   upgrade 를 빼는 것이든 그쪽이 고른다.
2. ⓑ — 받는 곳이 정말 없는지 그쪽이 확인한 뒤 크론을 멈추거나(크론 줄을 지우는 것은 박스의 사람 걸음) 남길 까닭을 적는다.
3. 매일 SIF 크론은 이 요청에 넣지 않는다 — Drive 에서 허브 배포 묶음과 겹친다는 지적(PLAN §8 · §9 의 Drive 중복)은 따로 정한다.

## 3. 받아들임

- ② 의 19행이 오래 가는 자리를 가리키고(또는 빈 값과 까닭), 컨테이너 안에서 그 파일이 열린다.
- ① · ③ 은 지울 목록(경로 · 크기)이 사람 확인을 거쳤고 확인한 것만 지웠다. 지운 기록이 그쪽 context-notes 에 있다.
- 30분 크론이 한 번 돈 뒤에도 라이브 DB 의 `alembic_version` 이 그대로다(사본에서 뽑았다는 시험 또는 로그).
- 크론 ⓑ 의 판단(멈춤 · 남김)이 그쪽 기록에 있다.

## 4. 하지 않을 것

- 확인 전에 지우지 않는다(결정 17).
- `source` 행을 지우지 않는다 — 원문의 자리만 고친다.
- 라이브 DB 를 그대로 `cp` 하지 않는다 — WAL 사본은 깨진다(PLAN §11 'WAL sqlite cp 사고'). `.backup` 을 쓴다.
- 포털 · 허브의 병합 스크립트는 고치지 않는다 — D5 는 보류 중이고 같은 병합 스크립트를 다른 갈래가 고친다(A2).

## 5. 누가 답하나

MaterialTwinWeb 세션. 끝나면 무엇을 옮기고 · 고치고 · 지웠는지(확인받은 목록과 함께)와 크론 판단을 알려 준다. 포털 메인 세션이 받아 데이터 이관
체크리스트의 D2 잔여 줄과 D5 줄들에 적는다.
