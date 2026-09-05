# 데이터 /data 통합 · 레지스트리 · DB 동기화 — 체크리스트

단계 게이트: 앞 단계의 "게이트" 가 전부 체크되기 전에는 다음 단계 착수 금지(PLAN §10).
한 단계 = 한 커밋 묶음. 공유 파일(services.py·services.yaml·backup-local.sh) 은 전용 브랜치에서, `git add` 파일 단위.

## 착수 게이트
- [x] 전 박스 ssh 가능(2026-09-05) → 동기화 매체 rsync/ssh, Drive 데이터 채널 불필요
- [ ] PLAN §12 결정 1(토폴로지 개정)·2(prod hostname·/data 종류)·5(SF 소유권)·6(upload-staging) 사용자 답
- [ ] `docs/cluster-deploy/context-notes.md` 에 토폴로지 개정 + `/data/svc` 한 줄 추가 기록(D1 전)
- [x] 작업 중 `hwax-stack.service` 부팅 갱신기 일시 disable — dev 에서 disable(2026-09-05, D0 끝나면 enable)

## D0 — 무영향 추가 (P0.3) — 사전점검 2회 반영판

**전 기간 규칙**: dev 에서 `update-all`·`deploy-all-from-drive` **금지**(update-all.sh:126 이 deploy-all 을 무조건 불러 dev 리포 6개를 stash+reset — 미푸시 커밋·라이브 쓰기 파일 소실). "update-all 1회 정상" 게이트는 **push 뒤 cae00 에서만**. 각 단계는 별 커밋, `git add <파일>` 단위, `git add -A` 금지.

- [x] **0 기준선·백업** — `crontab -l > <scratch>/crontab.before`(24행) · 9리포 `git status --porcelain` 전문 저장 · `services.sh status` 출력 저장(기준선; **vllm 은 dev 전용·stateless 라 기준선에서 제외** — 원장에 기록) · dev `systemctl --user disable hwax-stack.service`(D0 기간, 끝나면 enable — 부팅마다 형제 리포 pull 하는 갱신기)
- [x] **1 크론** — 24행(fakerepo backup-local) 제거 · 1행 `apptainer_sync.sh` 제거(dev 는 파일 부재 확인; cae00 은 `ls /usr/local/bin/apptainer_sync.sh` 로 조건부) → `crontab -l | grep -c fakerepo` = 0
- [x] **2 권한** — `chmod 700 /data/hwax/secrets` · `rmdir /data/hwax/upload-staging` → searxng `curl :8888/` 200 유지
- [x] **3 .gitignore 8리포** — **앵커 `/name`**(단일 세그먼트는 슬래시 없으면 모든 깊이에 걸림): HWAXPortal `backend/data` `backend/secrets` + infra `/data` · SignalForge `/data` `/backups` `/logs`(**reports·audit 제외 — 추적 248·9, 추적 패키지 crawler/reports·reports/audit 와도 충돌**) · AIDataHub `/data`(deploy/apptainer) `deploy/apptainer/backups` `api_server/mcp_uploads/_uploads` · MXWhitePaper `infra/data` `/data.ms` `infra/backups` · KooRemapper `platform/infra/data` `platform/storage` · HEAXHub `/var` `/job_storage` · HWAXAgentServer `/artifacts`. **MaterialTwinWeb `.agent_work` 는 D2 로 이관**(어떤 stash -u 경로에도 없음, 미푸시 161 커밋 동반 push 문제)
  - push: HWAXPortal·SignalForge·AIDataHub·MXWhitePaper·HWAXAgentServer 즉시 · **KooRemapper 는 feat 커밋 → main ff → 둘 다 push**(cae00 은 origin/main 으로 reset) · **HEAXHub 는 로컬 커밋 후 push 대기**(타 세션 미푸시 2커밋 동반 — 사용자 확인)
  - 게이트: `git show --stat HEAD` = .gitignore 1파일 · 스크래치 clone 에 `ln -s /nonexistent <name>` 후 `git status --porcelain` 빈 결과(실경로 검사는 D0 시점 공허)
- [x] **4 services.yaml + services.py + .env.example — 한 커밋** — `data:` 블록(classes **이름 키 매핑**, `identity:` 글롭 값은 따옴표) + 최상위 **`data_only:` 매핑**(smarttwinmcp·ste — `services:` 소비자 4곳 어디에도 안 보임; services-yaml-readers 가 제안한 grep 앵커·enabled_here·update:false 수정은 **불필요, 하지 않음**) · `services.py` `_infra_env()`(허용 키 `HWAX_(DATA_ROOT|BOX|BOX_ROLE|DATA_[A-Z0-9_]+)` 만, `shlex.split(comments=True)` 첫 토큰, **빈 값 = 미설정**, os.environ 미변경 — resolve_data 인자로만) · `resolve_data()` · `start_one` env 병합 · `data [svc] [--check]`(상태 `same/divergent/only-current/absent/n/a`) · `.env.example` 에 `HWAX_DATA_ROOT=` `HWAX_BOX=` `HWAX_BOX_ROLE=` 빈 값 · **유닛 무수정(EnvironmentFile 금지)**
  - 게이트: `python3 -c 'import yaml;yaml.safe_load(open("infra/services.yaml"))'` · `services.sh status` 출력·rc 가 0단계 저장본과 diff 0 · `grep -oP '^\s+- name: \K\S+' infra/services.yaml | sort -u | wc -l` = **14**(변경 전과 동일) · `services.sh data --check` divergent 0·only-target 0 · `HWAX_DATA_ROOT=/x services.sh data portal` 이 오버라이드를 보임
- [x] **5 헬퍼 + db-sync 읽기 전용** — `infra/scripts/lib/sqlite_backup.py`(docstring: 생성된 -wal/-shm 은 지우지 않음) · db-sync `status·verify·keys-check` 만(**`snapshot` 은 D0 에서 aidh·sf 에 치지 않음** — 03:30 daily 덤프를 입력으로) · `/data/hwax/state/db-sync/` 생성 → `db-sync status` 1회 뒤 `find /data/hwax/state -newer <marker>` 가 journal 만
- [x] **6 backup-local** — `skip()`(소스 부재 = 정보, 인스턴스 미동작 = bad) · WANT 확장(heax·kooremapper·portal 4파일+jwt·gateway·smarttwinmcp·delib-runs·paper-index·expertagents(bundle **+ 작업트리 tar** — bundle 은 커밋만 담는다)·secrets) · **heax 는 HEAXHub `.env` DATABASE_URL 파싱 → `--env PGPASSWORD`**(scram, 리터럴 금지, 로그 미출력) · `BOX="${HWAX_BOX:-$(env_get infra/.env HWAX_BOX || hostname -s)}"`(python 과 같은 우선순위) · 산출 `hwax/$BOX/<svc>/daily/<svc>-<box>-<TS>` · **옛 8세대는 `mv -n` 으로 새 `daily/` 편입**(mtime 보존 → 자동 정리; legacy 동결 아님) · 정리 find = `hwax/$BOX/*/daily` **+ `$BACKUP_ROOT/aidh/pre-merge-*.sql.gz`**(AIDH merge-from-drive.sh:46 이 계속 씀) · 산출 확장자 `.sql.gz`/`.tar.gz` 통일 · secrets·portal 절 `( umask 077; … )` + `mkdir -m 700` · **install-cron 치환형**(`grep -qF "$SELF"` 멱등은 새 LINE 을 영원히 안 설치) → 수동 1회 실행 → `--install-cron`
  - 게이트: 존재 소스 전부 `.sha256`·부재는 skip·rc 0 · `[ -s …/heax/daily/heax-*.sql.gz ]` · `crontab -l | grep -c backup-local` = 1(새 로그 경로) · `du -sh /data/backups/*`
- [x] **7 logrotate** — `infra/logrotate/hwax.conf.tmpl`(추적, `__ROOT__`·`__HOME__`) → `install-logrotate.sh` 가 `~/.config/hwax/logrotate.conf` 로 렌더(`install -m 0644`, `command -v logrotate || skip`) · 크론 **매시** `17 * * * *` + `-s ~/.local/state/hwax/logrotate.status` · 대상 = **O_APPEND 검증분만**(`~/.apptainer/instances/logs/*/koopark/*.{out,err}`·gateway.log·nginx-access.log·HEAX `integration_*.log`) + 정지 로그; HEAX worker/backend·AIDH uvicorn(자체 회전 있음)·caddy 는 제외 · `backup.log` 는 옛·새 경로 둘 다 `missingok`
  - 게이트: `logrotate -d <렌더 conf>` — 대상 목록 일치, "bad file mode" 없음
- [~] **8 복원 리허설**(mxwp·kooremapper·heax·sqlite 3 ✓ — signalforge·aidh 임시 인스턴스 진행 중) — mxwp·koorm·heax 는 **인스턴스 안** `<db>_rehearsal` · **aidh·sf 는 같은 SIF 로 임시 인스턴스**(`/data/hwax/.staging/rehearsal/<svc>`, :5440 — HNSW 3.3GB 재빌드를 라이브 인스턴스(maintenance_work_mem 64MB)에 시키지 않는다; D12 예외) · 입력 = 오늘 daily 덤프(plain SQL → `gunzip -c | psql -v ON_ERROR_STOP=1`, `set -o pipefail`; pg_restore 아님) · 표별 count 대조 · sqlite 3종 python `.backup` + integrity
  - 게이트: 5 인스턴스 `\l` 에 `_rehearsal|_mergestage` 0 · `apptainer instance list | grep -c rehearsal` = 0 · `ss -ltn | grep :5440` 빈 결과 · `/data/hwax/.staging/rehearsal` 삭제
- [ ] **9 cae00** — D0 브랜치 → main → push → **cae00 에서** 사전 확인(`grep -E '^HWAX_(DATA_ROOT|BOX|BOX_ROLE)=' infra/.env` 비어야 · `apptainer instance list | grep -E 'heax-pg|koorm_postgres'` · `hostname -s` · `df -h /data` · `ls /usr/local/bin/apptainer_sync.sh` · KooRemapper `git rev-parse --abbrev-ref HEAD`) → `update-all` 1회 → §1b heax/kooremapper ✓·부재 소스 skip·6b "등록 14건"·`crontab -l | grep -c backup-local` = 1·`git check-ignore -v <name>` 이 새 줄
- [ ] **롤백 목록(커밋 밖)**: `crontab <scratch>/crontab.before` · `~/.config/hwax/logrotate.conf`·`~/.local/state/hwax/` rm · `/data/hwax/state/db-sync` (원장이라 보관 권고) · 리허설 잔존(DROP WITH (FORCE)·instance stop·rm -r) · `chmod 755 /data/hwax/secrets`(되돌릴 이유 없음) · hwax-stack.service 재enable · **동반 push 된 무관 커밋은 cae00 배포 뒤 되돌릴 수 없다 — push 는 사용자 결정**

## D1 — 포털 자기 것 (P1.2 데이터판)
- [ ] `infra/scripts/start.sh` — D9 바인드(존재 시 동일경로) + 5개 env 조건부 `--env`
- [ ] `hwax.conf.tmpl:21` 로그 경로 렌더 + nginx 동일경로 바인드
- [ ] `apply-envs.sh agent-server` `ARTIFACT_DIR` 조건부 줄
- [ ] pre-move 스냅샷(backup-local portal) → agent_audit → users → conversations → token_store+jwt(`install -m 0600`) 순 M-SQLITE
- [ ] conversations `LIKE '/home/%'` 스캔 결과 기록
- [ ] agent-server artifacts M-BLOB · gateway audit.jsonl 파일 심링크
- [ ] 심링크 + `--bind` 커널 해석 1회 실측 기록(context-notes)
- [ ] **게이트**: 로그인 · 기존 PAT 로 게이트웨이 tools/list 개수 동일 · conversations count 동일 · launch-JWT heax SSO 1회 · jwt kid 개수 불변 · `data --check` same · 포털 컨테이너 안 `ls /data/svc/portal` 정상

## D2 — HEAX appdata (P5 선행)
- [ ] 결정 7 HEAX 런처 `HEAX_APP_DATA_ROOT` env(integration_launcher.py:56) 반영 확인
- [ ] MTW 크론 19·20 export 를 `.backup` 사본에서(§7.15③) 먼저 · 컨테이너 SIF 스키마 = 라이브 스키마 확인
- [ ] 크론 19·20 주석 → 컨테이너 8개 정지 → `pgrep -f scripts/catalog` 0
- [ ] `var/app_data → /data/appdata` 루트 통째(M-SQLITE·M-BLOB 혼합, WAL 포함 `.backup`) · `.env` `HEAX_APP_DATA_ROOT` · `.pre-*` 13개 legacy tar 후 삭제 · 0바이트 materialtwin.db 삭제
- [ ] `.agent_work` → `/data/appdata/materialtwin_web/sources/agent_work/` + `source.local_path` 18행 UPDATE + `/tmp` 1행
- [ ] risk_review.db · stepforge.db `LIKE '/home/%'` 스캔 기록
- [ ] **게이트**: HEAXHub /health 200 + 앱 8 페이지 · 표별 count(materialtwin 11표) · integrity ok · `register_material` 1회 · `source.local_path` 존재 100% · `heax_app_step_forge` 안 `/data` 내용 동일 · 크론 19·20 복구(읽기 전용판)

## D3 — 비-HEAX 블롭
- [ ] AIDH `_common.sh:13` + load_env 재평가 · `deploy/apptainer/.env` `AIDH_MCP_UPLOADS_DIR` · attachments·figures·mcp_uploads M-BLOB · `record_attachments.file_path` 18행 + `mcp_uploads.manifest.sif_path` 4행 UPDATE · 미참조 SIF 2개 목록
- [ ] SF `_common.sh:10` + load_env 재평가 · reports·audit M-BLOB(crawler `/reports` 바인드는 결정 7)
- [ ] MXWP `_common.sh:44` · minio M-BLOB · meili 는 `MEILI_DB_PATH` 수리 결정 전 `enabled:false`
- [ ] Koorm `_common.sh:63` · storage M-BLOB · start.sh `KOORM_STORAGE_DIR` `--env` + 존재 시 `--bind`
- [ ] HEAX `job_storage` M-BLOB + `.env` 값
- [ ] **게이트**: DB 경로 행 전수 존재 · AIDH 첨부 다운로드 표본 200 · MinIO 객체 354+175 · Koorm 세션 파일 다운로드 1건 · `data --check` same

## D4 — Postgres (P2.4 dev 선행)
- [ ] 순서: mxwp → kooremapper → heax → signalforge → aidh. 각각 M-PG 0~7
- [ ] heax: `SECRET_ENCRYPTION_KEY` sha256 을 pre-move 매니페스트에 · 야간 창(SSO 핸드오프 단절)
- [ ] signalforge: 크론 7·16·17·18·21·23 주석 → 이동 → 복구 · `signalforge_mergestage` 잔존 확인
- [ ] aidh: `aidh_mergestage` 잔존 확인 · 9.6G 복사 시간 기록
- [ ] **게이트**(svc 별): `pg_isready` · 표별 count = 사전 · `\dx` 동일 · 앱 health · backup-local 1회 정상 · `data --check` same
- [ ] 유예 뒤 `db-sync prune --pre-move` (사람)

## D5 — 동기화 배선 (P3.1b) — 기존 스크립트 + ssh
- [ ] `infra/boxes.yaml`(gitignore) + ssh 키 확인(dev↔cae00↔prod BatchMode)
- [ ] `db-sync.sh push|pull|mirror|status|rollback` 얇은 래퍼(~150줄) — rsync → pre-sync(backup-local) → 기존 merge 호출 → 원장
- [ ] 로컬 입력 입구 6줄: SF `merge-from-drive.sh:33-37` `SF_MERGE_DUMP` · HEAX `appdata-merge-from-drive.sh:20-22` `HEAX_APPDATA_TAR` (AIDH 는 이미 있음)
- [ ] 기존 merge 소규모 수정(PLAN §8.4 순서): AIDH embeddings 제외 → agents DO NOTHING+보고 → records 자연키 → SF update_cols(결정 5 에 따라) → HEAX 시드 `--exclude`
- [ ] mirror: Koorm·HEAX `pg_restore --clean` 4줄 + `exclude_on_mirror` TRUNCATE + `provision-config.sh --force` · sqlite `.backup` rsync→`mv -T`
- [ ] update-all §3·deploy-all SF/heax merge 를 `DB_SYNC` 플래그로 이중화(기본 0) → 같은 덤프로 결과 diff 0 → 기본값 전환
- [ ] SF·MTW `*/30` Drive push 정지 · AIDH 이중 덤프 통합 · Drive db-dumps 3세대
- [ ] **게이트**: 원장 1건 · 롤백 리허설(pre-sync 복원) 1회 · `divergent` 0 · `db-sync status` 0 · Drive 채널(코드) 무변경 확인

## D6 — prod 편입
- [ ] prod 박스 준비(결정 2) · `HWAX_DATA_ROOT=/data` 레이아웃 · update-all 1회
- [ ] 키 봉투 수동 전달(HEAX SECRET_ENCRYPTION_KEY · 포털 jwt · HWAXRisk cred.key · rclone.conf) — 어느 채널에도 안 실림
- [ ] cae00 쓰기 정지(포털 maintenance) → `seed`(콘텐츠 publish + 사용자 데이터 1회) → prod `provision-config.sh` 새로 → 소유권 전환(cae00 `HWAX_BOX_ROLE=staging`)
- [ ] RA 블루-그린(§7.9) 컷오버
- [ ] 첫 `mirror prod→staging`(결정 4 마스킹) · 오프박스 백업 rsync
- [ ] **게이트**: prod 전 서비스 health · cae00 발급 PAT 가 prod 게이트웨이에서 유효 · RA rat_ 토큰 유효 · 첫 mirror 성공 · 오프박스 백업 도착 · DNS 전환
