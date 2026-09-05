# 데이터 /data 통합 · 레지스트리 · DB 동기화 — 체크리스트

단계 게이트: 앞 단계의 "게이트" 가 전부 체크되기 전에는 다음 단계 착수 금지(PLAN §10).
한 단계 = 한 커밋 묶음. 공유 파일(services.py·services.yaml·backup-local.sh) 은 전용 브랜치에서, `git add` 파일 단위.

## 착수 게이트
- [x] 전 박스 ssh 가능(2026-09-05) → 동기화 매체 rsync/ssh, Drive 데이터 채널 불필요
- [ ] PLAN §12 결정 1(토폴로지 개정)·2(prod hostname·/data 종류)·5(SF 소유권)·6(upload-staging) 사용자 답
- [ ] `docs/cluster-deploy/context-notes.md` 에 토폴로지 개정 + `/data/svc` 한 줄 추가 기록(D1 전)
- [x] 작업 중 `hwax-stack.service` 부팅 갱신기 일시 disable — dev 에서 disable(2026-09-05, D0 끝나면 enable) → **재enable 완료**(2026-09-05 dev D1~D4 뒤)

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
- [x] **8 복원 리허설**(mxwp 72·kooremapper 8·heax 23 표·sqlite 3 ✓ · signalforge 임시 인스턴스 75s voc_records +1 · aidh 790s sync_runs +2 — 덤프 이후 라이브 증분, 표 집합 동일 · 잔존 0·:5440/:5441 빈·staging 삭제) — mxwp·koorm·heax 는 **인스턴스 안** `<db>_rehearsal` · **aidh·sf 는 같은 SIF 로 임시 인스턴스**(`/data/hwax/.staging/rehearsal/<svc>`, :5440 — HNSW 3.3GB 재빌드를 라이브 인스턴스(maintenance_work_mem 64MB)에 시키지 않는다; D12 예외) · 입력 = 오늘 daily 덤프(plain SQL → `gunzip -c | psql -v ON_ERROR_STOP=1`, `set -o pipefail`; pg_restore 아님) · 표별 count 대조 · sqlite 3종 python `.backup` + integrity
  - 게이트: 5 인스턴스 `\l` 에 `_rehearsal|_mergestage` 0 · `apptainer instance list | grep -c rehearsal` = 0 · `ss -ltn | grep :5440` 빈 결과 · `/data/hwax/.staging/rehearsal` 삭제
- [ ] **9 cae00** — push 뒤 **cae00 에서**(절차: `docs/cae00-deploy-guide.md` 2026-09-05 절) 사전 확인(`grep -E '^HWAX_(DATA_ROOT|BOX|BOX_ROLE)=' infra/.env` 비어야 · pg 인스턴스 5개 기동 · `hostname -s` · `df -h /data` 여유 ≥ SF+AIDH pg ×1.2 · `ls /usr/local/bin/apptainer_sync.sh` · KooRemapper `git rev-parse --abbrev-ref HEAD` = main) → **infra/.env 에 `HWAX_DATA_ROOT=/data`·`HWAX_BOX_ROLE=staging` 추가** → `update-all` 1회 → §1b heax/kooremapper ✓·6b "등록 14건"·`crontab -l | grep -c backup-local` = 1·**2b) 서비스별 "이동 완료"**(롤백 `↩` 줄 없음)·`services.sh data --check` rc 0·전 서비스 health·기존 PAT 로 게이트웨이 tools/list
- [ ] **롤백 목록(커밋 밖)**: `crontab <scratch>/crontab.before` · `~/.config/hwax/logrotate.conf`·`~/.local/state/hwax/` rm · `/data/hwax/state/db-sync` (원장이라 보관 권고) · 리허설 잔존(DROP WITH (FORCE)·instance stop·rm -r) · `chmod 755 /data/hwax/secrets`(되돌릴 이유 없음) · hwax-stack.service 재enable · **동반 push 된 무관 커밋은 cae00 배포 뒤 되돌릴 수 없다 — push 는 사용자 결정**

## D1~D4 — 이관기(`infra/scripts/data-migrate.sh`)가 수행 — dev 실행 결과(2026-09-05)

수동 절차(옛 D1~D4 항목)는 **레지스트리 기반 이관기**로 대체했다: 서비스별 `pre-move 백업 → 크론 일시정지 → 정지 → 복사·checksum → rename+심링크 → 기동 → 행수 대조(DB post≥pre) → db_paths 치환 → 원장`, 실패 시 자동 롤백(목표 사본은 `.rolled-back-TS` 로 비켜둠). cae00/prod 는 `HWAX_DATA_ROOT=/data` 한 줄 → `update-all 2b`.

- [x] **portal**(D1) 12:17 — users·conv·audit·token_store·jwt 5클래스 → `/data/svc/portal`·`/data/hwax/secrets/portal/jwt`. 게이트: health 200 · 컨테이너 `ls /data/svc/portal` ✓ · 프로세스 env 6종(USER/CONV/TOKEN/AUDIT/JWT_KEYS_DIR/DELIB) 새 경로 ✓ · 행수 conversations 1753·users 3·token_store 38 일치 · 가짜 PAT → portal/gateway 401(스토어 조회 정상) · jwt kid `dev-1` 불변 · `data --check` same · conversations `'/home/'` 포함 = messages.content 4행(본문 언급, 경로 컬럼 아님)
  - [ ] 기존 PAT 로 tools/list 개수·launch-JWT heax SSO 1회 — 브라우저 수동(사용자)
  - [x] `start.sh` D9 바인드(존재 시 동일경로) + 6 env 조건부 `--env` · `apply-envs.sh ARTIFACT_DIR` 줄은 **불필요**(resolve_data 주입 + 심링크) · nginx 로그는 이동 대상 아님(log 종류 — logrotate 몫)
- [x] **mcp-gateway** audit.jsonl(파일형 blob) · **agent-server** artifacts 12:33 — 호스트 프로세스, env 주입 확인(GATEWAY_AUDIT·ARTIFACT_DIR)
- [x] **mx-white-paper**(D4·D3) 12:31 — pg 275M(72표 일치)·minio 14M. **1차 시도 롤백**(minio 파일수 568→554: `.minio.sys/tmp` 를 시작·종료마다 갈아치움 → 대조 규칙 수정) · stop.sh 가 mxwp_api 를 세워 mxwp-mcp 도 죽음 → `restart_also` · 게이트웨이 revive 루프가 1~2분 뒤 재부착(372 도구 복귀)
- [x] **kooremapper**(D4·D3) 12:33 — pg 64M(8표)·storage 4M. needs_bind 사전 재기동 → 컨테이너 `/data/svc/kooremapper` ✓ · `KOORM_STORAGE_DIR` env ✓
- [x] **heax-hub**(D4·D2·D3) 12:35 — pg 70M(23표)·app_data 1035M → `/data/appdata` 루트 심링크·job_storage. 48s(heal.sh 40s). 게이트: /health 200 · 앱 인스턴스 16 · materialtwin 49,386행 동일 · 앱 컨테이너 `/data` 에 materialtwin.db ✓ · materialtwin web 200·stepforge 401(인증 요구=생존) · 런처 가드 `resolve()` 양쪽이라 심링크 루트 허용(실측)
  - [ ] `.agent_work` → `/data/appdata/materialtwin_web/sources/agent_work/` + `source.local_path` 18행 UPDATE(MTW, D2 잔여) · `.pre-*` 13 legacy tar·0바이트 materialtwin.db 정리(D7 사람) · `SECRET_ENCRYPTION_KEY` sha256 매니페스트 기록 · `register_material` 1회(수동)
- [x] **signalforge**(D4) 12:37 — pg 1.9G(11표 일치) · reports·audit 는 추적 파일 → 등록만(`enabled:false`)
- [x] **ai-data-hub**(D4·D3) 12:48 — pg 9.8G(21표 일치)·attachments·figures·mcp_uploads 570M + db_paths 치환 `record_attachments.file_path` 18행·`mcp_uploads.manifest` 4행. **1차 시도(12:41) 롤백**: 치환 SQL 리터럴을 `shlex.quote` 로 만들어 슬래시만 있는 경로가 인용되지 않음(`syntax error at or near "/"`) → `sql_lit()` 로 수정. 롤백이 pg 9.8G 사본 포함 4개를 `.rolled-back-20260905-123758` 로 비켜둠(사람이 지운다). 재실행은 3시간 안의 daily 덤프를 재사용해 21s
- [x] **공통 게이트**: `services.sh data --check` rc 0(이동 종류 전부 same) · 심링크가 `--bind` 소스여도 커널이 해석(mxwp·koorm·heax·sf pg 인스턴스가 `/data/pg/<svc>/pgdata/postmaster.pid` 갱신 — 실측) · 크론 23줄 매번 복원 · 원장 `/data/hwax/state/data-migrate/journal.jsonl`
- [ ] 유예 뒤 `.pre-move-*`(8리포)·`.rolled-back-*`(`/data/pg/mxwp.…-122907`·`/data/svc/mxwp/minio.…-122907`·`/data/pg/aidh.…-123758` 9.8G·`/data/svc/aidh/{attachments,figures,mcp_uploads}.…-123758`) 삭제 — 사람(D7)

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
