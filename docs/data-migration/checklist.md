# 데이터 /data 통합 · 레지스트리 · DB 동기화 — 체크리스트

단계 게이트: 앞 단계의 "게이트" 가 전부 체크되기 전에는 다음 단계 착수 금지(PLAN §10).
한 단계 = 한 커밋 묶음. 공유 파일(services.py·services.yaml·backup-local.sh) 은 전용 브랜치에서, `git add` 파일 단위.

## 착수 게이트
- [x] 전 박스 ssh 가능(2026-09-05) → 동기화 매체 rsync/ssh, Drive 데이터 채널 불필요
- [ ] PLAN §12 결정 1(토폴로지 개정)·2(prod hostname·/data 종류)·5(SF 소유권)·6(upload-staging) 사용자 답
- [ ] `docs/cluster-deploy/context-notes.md` 에 토폴로지 개정 + `/data/svc` 한 줄 추가 기록
- [ ] 작업 중 `hwax-stack.service` 부팅 갱신기 일시 disable 절차 합의(PLAN §11)

## D0 — 무영향 추가 (P0.3)
- [ ] 8개 리포 `.gitignore` 에 심링크 이름(슬래시 없이) 커밋 — HWAXPortal(`backend/data` `backend/secrets` / infra: `data`) · SignalForge(`data` `backups` `logs` `reports` `audit`) · AIDataHub(`deploy/apptainer/data` `deploy/apptainer/backups` `api_server/mcp_uploads/_uploads`) · MXWhitePaper(`infra/data` `data.ms` `infra/backups`) · KooRemapper(`platform/infra/data` `platform/storage`) · HEAXHub(`var` `job_storage`) · HWAXAgentServer(`artifacts`) · MaterialTwinWeb(`.agent_work`)
- [ ] `infra/.env.example` 에 `HWAX_DATA_ROOT=` `HWAX_BOX=` `HWAX_BOX_ROLE=` 추가(주석: 미설정 = 현행)
- [ ] `services.py` — `_infra_env()` · `resolve_data()` · `start_one` env 병합 · `data [svc] [--check]` 액션 · `managed:false` skip
- [ ] `services.yaml` — 전 서비스 `data:` 블록(+ `smarttwinmcp`·`ste` 등록 항목) · PLAN §5 SF voc_records 실측 컬럼
- [ ] `infra/systemd/hwax-stack.service` `EnvironmentFile=-__PORTAL__/infra/.env` + `install-systemd.sh` 렌더
- [ ] db-sync `snapshot · verify · status · keys-check` (적용 verbs 없이) + `manifest.json` 스키마 + 원장 경로
- [ ] `backup-local.sh` — WANT 확장(heax·kooremapper·portal 4파일+jwt·gateway·smarttwinmcp·delib-runs·paper-index·expertagents·secrets) · 산출 경로 `hwax/$BOX/<svc>/daily` · 파일명 `<svc>-<box>-<TS>` · find 범위 한정 · 로그 경로
- [ ] python sqlite `.backup`/integrity 헬퍼(`infra/scripts/lib/sqlite_backup.py`)
- [ ] `infra/logrotate/hwax.conf` + `install-logrotate.sh`(멱등) + update-all 호출
- [ ] `chmod 0700 /data/hwax/secrets` · `rmdir /data/hwax/upload-staging`(비어 있음 확인)
- [ ] crontab 24행(fakerepo backup-local) 제거 — 사용자 확인 후 · 1행 `apptainer_sync.sh` 출처 확인
- [ ] 복원 리허설: pg 5종(staging DB 로드·표 행수 대조) · sqlite 3종(임시 파일 `.backup`·integrity)
- [ ] **게이트**: `HWAX_DATA_ROOT` 미설정에서 `services.py up/status/down` 출력 diff 0 · `data --check` 전 클래스 `only-current` · 심링크 후보 경로 `git status --porcelain <path>` 빈 결과 · backup-local WANT 전부 sha256 산출 · 리허설 로그 존재 · `update-all` 1회 정상

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
