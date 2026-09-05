# 데이터 /data 통합 · 레지스트리 · DB 동기화 — 컨텍스트 노트

결정과 그 이유. PLAN.md 가 "무엇" 이면 여기는 "왜". 결정을 뒤집을 때는 여기 근거를 먼저 반박할 것.

## 2026-09-05 — 계획 수립

### 요구의 출발점
- 사용자: update-all 체인 프로젝트들이 각자 리포 안에 데이터를 쌓아 관리가 어렵다 → `/data` 통합.
  이어서 "포털이 프로젝트별 데이터 경로를 환경설정으로 관리하고 동기화가 그 경로를 쓰게",
  "DB 동기화 전용 기능 — cae00 은 업데이트 시험용, 프로덕션은 따로, 본 서버로 데이터 동기화".

### 어떻게 계획을 만들었나 (재현 가능성)
- **인벤토리**: 14개 프로젝트를 병렬 실측(경로·종류·크기·설정 지점 파일:행·update-all 처리·박스 절대경로·리스크)
  → 각 결과를 반증 검증(경로 존재·설정 근거 grep·gitignore·누락 탐색) → 횡단 비평(백업 커버리지·merge 프리미티브·
  크론·Drive 레이아웃·공유 디렉터리·동시 쓰기 충돌). MaterialTwinWeb 은 크론에서 발견돼 보충 인벤토리.
  29+2 에이전트, 오류 0. 결과 다이제스트는 세션 스크래치패드(`inventory-compact.md`)에 있고, 내부 IP·절대경로가
  섞여 있어 리포에는 넣지 않았다 — PLAN §1 이 그 요약이다.
- **설계 패널**: 같은 사실 팩으로 독립 3안(되돌리기 우선 / 최소변경 우선 / 운영관측 우선) → 심사 2인
  6축 채점(정렬·근거·롤백·커버·단순·요구) → 1위안 파괴 검증(실제 코드·파일시스템으로 반증).
  채점 합계 rollback-first 100 · minimal-change 98 · ops-first 90 — 근접해서 1위안을 뼈대로 나머지 둘의
  아이디어를 접목했다(아래).
- 기존 계획 `docs/cluster-deploy/`(v2, 2026-08-02) 를 먼저 읽고 정렬했다. 이 계획은 그 Phase 0.3·2.4·3.1b 의
  선행 작업이며, 유일한 개정은 토폴로지다.

### 파괴 검증이 증명한 것 — 설계를 바꾼 지점
1. **심링크는 gitignore 되지 않는다**(`dir/` 패턴, git 2.34 실측). `update-all.sh:76`·`deploy-all-from-drive.sh:106`
   의 `git stash push -u` 가 매 실행 심링크를 치우고, `_common.sh` 들의 `mkdir -p` 가 빈 디렉터리를 만들어 initdb →
   빈 DB, 포털은 `JWT_AUTOGEN_KEYS` 로 새 키 민팅. → **D0 ① 8개 리포 `.gitignore` 에 슬래시 없는 이름 선행 커밋**이
   모든 이동의 전제. 게이트는 `git status --porcelain <link>` 빈 결과(`check-ignore <link>/` 는 fatal).
2. **컨테이너 안에서 호스트 `/data` 는 보이지 않는다**(포털 `start.sh:49-50` 두 바인드, Koorm apptainer.conf 바인드 없음,
   실측). 바인드된 디렉터리 안의 심링크는 컨테이너에서 dangling → `user_store.py:55 mkdir` FileExistsError.
   → 설계 초안의 "5단계(심링크만) → 6단계(env)" 를 버리고 **바인드+env 를 한 재기동에**(D9). 바인드는 env 조건이
   아니라 **대상 디렉터리 존재**로 건다. 바인드 source 가 심링크인 것은 커널이 해석해 무해(실측).
3. **HEAX 런처 traversal 가드**(`integration_launcher.py:81-84 resolve()`) 가 앱별 심링크를 거부. 루트 통째 심링크만
   통과. 그런데 루트를 옮기면 `appdata-to-drive.sh`·`backup-local.sh` 가 `/data/appdata` 아래 전부를 tar 에 담는다.
   → **비-HEAX 서비스는 `/data/svc/<svc>/`** (D10). plan §2 에 한 줄 추가 개정. `/data/appdata` 는 §2 원문대로 HEAX 앱 전용.
4. **SF `voc_records` 에 `updated_at` 이 없다.** 설계 초안 update_cols 7개 중 6개가 존재하지 않는 열이었다. 실측 컬럼으로
   교체(PLAN §5). "기존 행은 콘텐츠 열만, 신규 행만 전체" 규칙.
5. **`sqlite3` CLI 가 박스에 없다.** 기존 도구도 전부 python sqlite3 모듈이다. → python 헬퍼.
6. **`services.py` 는 어떤 경로에서도 `infra/.env` 를 읽지 않는다**(update-all·update-sites·hwax-stack.service).
   SF·AIDH `_common.sh` 는 DATA_DIR 을 `load_env` 보다 먼저 평가해 리포 `.env` 오버라이드도 안 먹는다(MXWP·Koorm 은 먹음).
   → `services.py` 자체 파서 + 유닛 `EnvironmentFile` + SF/AIDH `load_env` 뒤 재평가.
7. **크론·워치독 재기동은 env 없이 옛 경로로 뜬다**(SF `watchdog.sh:31`, HEAX `watchdog.sh:212`, AIDH `watchdog.sh:58`,
   Koorm `supervisor.sh:18`). → **브리지(심링크)는 영구**. `only-target`(브리지 제거) 상태를 없앴다. env 는 컨테이너
   바인드와 미래 정리용이고, 런타임 정합성은 심링크가 보장한다. 이 결정으로 "포털이 관리" 의 의미가 명확해졌다 —
   레지스트리 = 선언(current→target)과 검증(`--check`), 심링크 = 런타임 브리지, env = 바인드가 필요한 곳.

### 심사가 잡은 사실오류 (PLAN 에 반영)
- AIDH `.last-merged` 마커는 `update-all.sh:169-171`(§3 블록 165-178). 초안의 `:62` 는 git username 메시지 줄.
- HWAXRisk `box_match`·`secrets_valid` 는 `backend/app/main.py:61·:66`(초안 `main.py:42·47` 은 인벤토리 오류 승계).
- 게이트웨이는 `.env` 를 읽지 않는다(`gateway.py` os.environ 직접, `start.sh` 소싱 없음) → `.env` 처방 삭제, 파일 심링크 + services.yaml 주입.
- 포털 `--env` 목록은 `start.sh:51-70`. SF 크론 정지 목록에 7행(04:30 backup-to-drive) 추가.
- AIDH `AIDH_MCP_UPLOADS_DIR` 는 `api_server/.env` 가 아니라 `deploy/apptainer/.env`(`load_env` `set -a` 가 네이티브 uvicorn 에 상속).
- SF 로컬 덤프 정리는 `backup-to-drive.sh:119-130`(크론 7 이 부름), `sync-to-drive.sh` 는 참조 0건.
- `risk_review.db` 는 db·-wal·-shm 셋을 함께 cp 하면 보존된다. 단독 `.db` cp 만 문제. 그래도 `.backup` 권고 유지.
- PGDATA 5개 전부 uid 1000(rootless subuid 미사용) — 일반 `rsync -a` 로 충분(초안의 fakeroot 가정 해소).

### 다른 두 안에서 가져온 것
- minimal-change: HEAX `var/app_data → /data/appdata`·`var/pg → /data/pg/heax` 통째 심링크(코드 최소) · env 폴백 + 심링크
  **둘 다** · `publish_tables`/`exclude_on_mirror` 표 단위 소유권 · update-all 무수정(db-sync 를 옆에) · `HWAX_BOX_ROLE × owner`
  정책 표 · SF `SF_MERGE_DUMP` 6줄 입구 · `services.py data <svc>` 가 KEY=VALUE 줄을 내는 이음새.
- ops-first: `manifest.json` 스키마(행수·alembic·pg_version·extensions·sha·keys 지문·excluded·scrubbed) · pg mirror 를
  `_syncstage → RENAME 2회`(DROP 창 0) · `empty-target` preflight · `status` 한 화면 판정 규칙·종료코드 · "staging 은 owner 가
  될 수 없다" 스키마 검증 · owner=prod 클래스 Drive 전송 거부 · SF 크롤 prod 단일화 권고 · `HWAX_BOX` hostname 폴백.

### 소유권 모델을 이렇게 정한 이유
- 인벤토리의 동시 쓰기 충돌 목록(AIDH agents 덮어쓰기·records 자연키 위반·embeddings id 충돌, SF voc_records 편집 되돌림,
  materialtwin 병합기 2개, Koorm users_id_seq 어긋남, 포털 sqlite 채널 없음)은 전부 **"누가 정본인가" 가 암묵적**이어서 생겼다.
  현행 merge 스크립트들은 "dev 가 이긴다" 를 코드에 박아 두었다. 표 단위 `owner`·`tables` 로 명시하면 가드 코드 없이
  대부분 소멸한다(사용자 생성 표를 publish 대상에서 빼면 덮어쓸 일이 없다).
- "본 서버로 데이터 동기화" 의 방향이 데이터 종류마다 다르다는 것을 사용자에게 드러내야 한다 — 콘텐츠는 dev→prod publish,
  사용자 데이터는 prod 정본·staging 은 mirror. 하나의 방향으로 뭉개면 한쪽이 조용히 덮인다. §12 결정 5(SF) 가 남은 유일한 회색지대.

### token_store 를 secrets 트리에 두지 않은 이유
- plan §7·cluster context-notes:44-47 은 PAT store 를 "Postgres 이관 필수, SQLite 는 NFS 잠금 신뢰 불가" 로 정했다.
  `/data/hwax/secrets` 는 미래 공유 트리다. 파일째 옮기는 것은 임시이고 자리는 `/data/svc/portal/`. plan 4.2 이관 시점은 §12 결정 12.

### 보존정책이 이 계획의 가장 싼 수확인 이유
- SF 84G 는 버그가 아니라 정책(30분 × 7일 로컬 보존)의 정상 상태였다. Drive 쪽에는 이미 "24h 전량 + 일별 5일" 이 있다.
  같은 규칙을 로컬에도 — 시간별 24 + 일별 7 ≈ 7G. AIDH 는 같은 DB 를 하루 두 번(04:45 Drive 행 42G + 03:30 backup-local 33G)
  덤프하고 있었다. 이 둘만 고쳐도 150G 가 돌아온다.

### 범위에서 뺀 것과 이유
- STE(별 박스, 에어갭), `/data/paper_patent_corpus`(HWAX 밖 소유), cluster-deploy versions/current(SIF·dist), RA 소스(hands-off,
  블루-그린 결정 2026-08-02 유지). `~/serviceApptainers` 440G 중 HWAX 몫은 10G 미만 — 나머지는 HPC 자산이라 별 소유자 결정.

### 미결(§12) 중 착수 전 꼭 필요한 것
- 1 토폴로지 개정, 2 prod 박스(ssh 가능 여부가 db-sync 전송 매체를 정한다), 5 SF 소유권, 6 upload-staging, 7 HEAX 런처 env(D2 선행).

### 2026-09-05 결정 — "다 ssh 되니까 최대한 기존 방식을 쓰면서 경로만 변환"
- 사용자 결정. 결과: §8 을 새 병합 엔진에서 **기존 merge 스크립트 + rsync 전송 + 경로 치환** 으로 재작성. 채점 2위(minimal-change)의
  핵심을 채택한 것이다. 새로 쓰는 코드는 얇은 래퍼(~150줄) + 두 스크립트의 로컬 입력 입구 6줄씩 + 채널 없던 4곳의 mirror(기존 restore 계열).
- Drive 는 데이터 동기화에서 빠진다(코드·아티팩트 반입 + 오프사이트 백업만). 이유: 실측된 문제(평문·단일 자격증명·비결정 스냅샷·업로드 타임아웃)를
  ssh 가 전부 우회하고, cluster-deploy 의 "Drive 는 반입 채널로만" 결정과도 맞는다. §12-3(암호화)은 선택으로 격하.
- 이어서 "동기화할 때의 낭비는 줄여야" — §8.7 신설. 원칙: 덤프는 하루 한 번 한 파일(백업 = 동기화 소스), 안 바뀌면 안 보냄, 표 단위, 워터마크 증분,
  블롭은 rsync 델타. 기존 merge 스크립트는 입력이 작아질 뿐 동작이 같다는 점이 "기존 방식 유지" 와 양립하는 근거.
- "경로가 변환된다" 의 의미: `_common.sh` 한 줄 + gitignore 된 심링크 + 컨테이너 바인드. 스크립트·크론·merge 는 옛 경로 이름으로 계속 동작한다.

### 2026-09-05 전제 두 개 (사용자)
- "다 문제없다는 전제에서 시작" → D11. 기준선이 초록이 아니면 이관 뒤 문제가 이관 탓인지 가릴 수 없다. 알려진 기존 문제
  (materialtwin 라이브 스키마 > 컨테이너, MXWP meili 바인드, SF crawler reports) 는 기준선 기록에 "원래 있던 것" 으로 적고 이관과 섞지 않는다.
- "프로젝트별 DB 는 잘 분리" → D12. 지금도 postgres 5 인스턴스가 포트·PGDATA·롤로 분리돼 있고 이관은 PGDATA 위치만 바꾼다.
  유일한 약점은 RA 가 시스템 PG14 를 다른 DB 와 공유하는 것 — green 은 자체 인스턴스(`/data/pg/reportarchive`) 로 권고.
  동기화 도구는 서비스 간 DB 를 절대 교차하지 않는다(표 단위 덤프·서비스별 원장).

### 2026-09-05 D0 사전점검 (사용자: "시스템이 이상해지면 안 되니 꼼꼼히 더 점검") — GO with adjustments
dev 에서 읽기 전용 실측. 조정 없이 갔으면 깨졌을 것 셋(★).
- ★ **`hwax-stack.service` 에 `EnvironmentFile=infra/.env` → NO-GO.** `COOKIE_SECURE` 줄 인라인 주석을 systemd 가 값으로 읽고, 로드된 `APP_ENV=dev`·`SESSION_SECRET`
  등이 services.py 의 모든 자식 서비스에 상속된다(heax Settings 는 `APP_ENV=dev` 거부 — 09-04 실사고 재현 경로). → services.py 가 파일에서 `HWAX_*` 세 키만 파싱, export 안 함.
- ★ **SF `reports/`(추적 248)·`audit/`(추적 9) 는 심링크 불가.** 다른 22개 경로는 추적 0. → SF 는 pg·backups·logs 만 심링크, reports/audit 는 env·바인드 또는 추적 해제 선행.
- ★ **copytruncate 는 O_APPEND 쓰기자에만 안전.** /proc fdinfo 실측: gateway.log·apptainer `.err` 는 O_APPEND, HEAX worker.log(471M)/backend.log·AIDH uvicorn.log 는 `nohup >` 라
  O_APPEND 아님 → truncate 뒤 sparse 구멍. → logrotate 범위 축소 + 타 리포 `>`→`>>` 1글자 수정을 §12-7 에 추가.
- **update-all §6b 가 `grep '^\s+- name:'` 로 services.yaml 을 읽는다** → `data:` 안 클래스는 리스트가 아니라 매핑. 데이터 전용 등록은 `data_only:` 매핑(update-sites 무인자 모드·services.py KeyError 회피).
- 그 외 확인: services.py/update-sites 는 PyYAML(추가 키 무해), system python3 yaml 6.0.3(폴백 OK) · 5 pg 인스턴스에 잔존 스테이징 DB 없음, SIF 마다 pg_dump/pg_restore/psql 있음(pg15.17/15.18/16.14/16.14/16.13)
  · /home 222G·/data 3.6T 여유 · logrotate 3.19 · /data/hwax 는 searxng 만 읽음(0700 안전), upload-staging 비어 있고 참조 0 · crontab 1행 스크립트 부재(dpkg 소유 아님)
  · WIP: HWAXPortal D0 대상 파일 미커밋 0, 8리포 .gitignore 전부 미변경(파일 단위 커밋 안전); HEAXHub 미푸시 2·MTW 미푸시 161 → 그 두 리포는 .gitignore 커밋만 하고 push 는 소유자 몫
  · cae00 인스턴스 이름은 같은 코드(HEAXHub start.sh:58 `heax-pg`, Koorm `_common.sh:71`)라 동일; `hostname -s` = cae00/smarttwincluster 로 <box> 적합.
- 워크플로(9 에이전트)는 두 번 한도로 실패 뒤 세 번째에 완주(0 오류) — 인라인 결과를 전부 확인하고 다음을 더했다(2차 반영, checklist D0 재작성).
  - **H1 dev 에서 update-all 금지(NO-GO)**: `update-all.sh:126` 이 deploy-all 을 호스트 가드 없이 무조건 부른다 → dev 리포 6개 stash+reset(미푸시 커밋·SF 라이브 쓰기 추적 파일 7개 소실). "update-all 1회 정상" 게이트는 push 뒤 cae00 에서만. dev 게이트는 `services.sh status` diff·backup-local 수동·6b grep 14·`data --check` 로 분해.
  - dev `hwax-stack.service` 가 **enabled·active**(`systemctl --user`) — 부팅마다 형제 리포 `git pull --ff-only`. D0 기간 disable.
  - 오늘 dev 기준선은 **vllm down** 으로 `services.sh status` rc=1 → vllm(dev 전용·stateless·update:false)은 기준선에서 제외하기로.
  - 단일 세그먼트 gitignore 이름은 **앵커 `/name`** — 슬래시 없는 `reports` 는 추적 패키지 `crawler/reports/`, `audit` 는 `reports/audit/` 에도 걸린다(실측). 무시된 심링크는 `git stash -u` 에서 살아남고 `git clean -fdx` 만 지우는데 8리포·포털 스크립트에 `git clean` 없음(실측 — D2 브리지 영구의 안전 근거).
  - 리허설: aidh 덤프가 HNSW 인덱스 3개(3.3GB, 86만 벡터)를 CREATE — 라이브 인스턴스(maintenance_work_mem 64MB) 안에서 하면 수 시간 + /home 89% → **같은 SIF 임시 인스턴스**(/data, :5440 빈 포트 실측) 로. D12 에 예외 한 줄. backup-local 덤프는 plain SQL 이라 `psql -v ON_ERROR_STOP=1`(pg_restore 아님, ON_ERROR_STOP 없으면 거짓 초록).
  - heax-pg 는 127.0.0.1 도 scram-sha-256(다른 4개는 trust) → backup-local 이 그대로면 heax 는 매일 '0바이트 실패'. DATABASE_URL 파싱으로 `--env PGPASSWORD`.
  - `--install-cron` 멱등 판정이 `grep -qF "$SELF"` → 줄 내용을 바꿔도 dev·cae00 어디서도 영원히 갱신 안 됨 → 치환형. crontab 24행은 SELF 를 포함하지 않아 별도 제거(순서상 먼저).
  - 옛 8세대(38G)는 `legacy/` 동결이 아니라 `mv -n` 으로 새 `daily/` 편입(mtime 보존 → 자동 정리, 사람 삭제 0). AIDH `merge-from-drive.sh:46` 의 `/data/backups/aidh/pre-merge-*` 는 update-all 마다 4.4G 를 계속 쓰므로 정리 find 유지.
  - `data_only:` 최상위 매핑 채택으로 services-yaml-readers 가 제안한 3건(update-all:969 grep 앵커·enabled_here skip·update:false)은 **불필요 → 수정하지 않음**(수술적 변경). 6b 등록 건수 14 유지가 정답.
  - `data --check` 상태에 `same(현행유지)`·`absent`·`n/a` 추가, 게이트 = divergent 0·only-target 0, update-all 배선은 D1 이후.
  - `$BOX`/`HWAX_*` 해석은 bash(backup-local)·python(services.py) 이 같은 우선순위(`os.environ > infra/.env > hostname -s`, 빈 값 = 미설정) — 아니면 디렉터리 이름이 갈린다.
  - MTW `.agent_work` gitignore 는 D0 묶음에서 빼 D2 로(어떤 stash -u 경로에도 없고, 미푸시 161 커밋 동반 push 가 실코드 배포가 됨). KooRemapper 는 feat 커밋 → main ff → 둘 push(cae00 은 origin/main reset). HEAXHub 는 타 세션 미푸시 2커밋 + 활성 세션 7개 → 로컬 커밋만, push 는 소유자 확인.
  - 커밋 밖 부작용(crontab·logrotate 상태파일·/data/hwax/state·리허설 잔존·chmod)은 checklist 롤백 목록으로. 첫 조치 전 `crontab -l` 저장.

## 작업 로그
- 2026-09-05: 인벤토리·패널·계획 수립. 코드 변경 0. 다음 = 착수 게이트(§12 답) → D0.
