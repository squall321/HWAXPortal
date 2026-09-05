# 데이터 /data 통합 · 경로 레지스트리 · DB 동기화 — 계획 (v1, 2026-09-05)

> 요구(2026-09-05): ① update-all 체인 전 프로젝트의 데이터를 `/data` 로 통합하고 프로젝트별
> 마이그레이션을 디테일하게, ② **포털이 프로젝트별 데이터 경로를 환경설정으로 관리**하고
> 동기화가 그 경로를 쓰게, ③ **DB 동기화 전용 기능** — cae00 을 업데이트 시험(staging)으로,
> 프로덕션을 따로 두고 본 서버로 데이터를 동기화하며 운영.
>
> 이 계획은 `docs/cluster-deploy/plan.md`(v2, 2026-08-02)의 §2 `/data` 레이아웃·§3.1b·§4·§9 를
> **그대로 따르고 앞당긴다**(P0.3·P2.4·P3.1b 의 선행 작업). 유일한 개정은 토폴로지(cae00→staging,
> prod 신설)로, §12 결정 1 에서 승인을 받는다. 근거는 14+1 프로젝트 실측 인벤토리(2026-09-05,
> 반증 검증 포함)와 설계 패널(독립 3안 → 채점 → 1위안 파괴 검증)이며, 그 과정은
> `context-notes.md` 에 있다. 파일:행 인용은 그 날짜의 dev 체크아웃 기준이다.

## 0. 한 장 요약

- **코드는 적게, 절차는 신중하게.** 경로 결정 지점이 프로젝트당 1~4줄(`_common.sh` 한 줄 + 바인드
  한 줄)이고 포털·게이트웨이는 이미 환경변수를 받는다. 무거운 것은 postgres 5개 이동과 순서·검증이다.
- **켜지 않으면 아무것도 안 바뀐다.** `HWAX_DATA_ROOT` 미설정 = 현행과 diff 0 (plan §4 "기본값=현행").
- **옛 경로는 심링크로 영구 브리지**한다. 크론·워치독·수동 기동은 env 없이 옛 경로로 뜨므로(파괴검증
  R1) 브리지를 걷는 "완료 상태"는 두지 않는다. 단 심링크는 **먼저 gitignore 에 올려야** 한다 —
  `dir/` 패턴은 심링크를 무시하지 않아 `git stash -u`(update-all·deploy-all 매 실행)가 치운다(파괴검증 B1).
- **컨테이너 서비스는 바인드+env 를 한 재기동에.** 컨테이너 안에서 호스트 `/data` 는 보이지 않는다
  (실측 B2). 대상 디렉터리가 존재하면 동일경로 `--bind` 를 건다(env 조건 없이).
- **박스 간 전부 ssh 가능(2026-09-05 확인) → 데이터 동기화는 rsync/ssh + 기존 merge 스크립트(입력 경로만 치환).** Drive 는 코드·아티팩트 반입과 오프사이트 백업만.
- **소유권을 표 단위로 명시한다.** 콘텐츠(dev 정본) 는 publish, 사용자 데이터(prod 정본) 는 mirror,
  staging 은 어떤 데이터의 owner 도 아니다. 목록에 없는 표는 동기화 대상이 아니다(누락 = 안전).
- **가장 큰 실측 문제는 보존정책이다.** SF 30분 덤프×7일 = 84G, AIDH 이중 덤프 75G, materialtwin
  죽은 사본 924M, 무회전 로그 2G+. 이건 코드 몇 줄로 수십 GB 를 돌려받는다.
- **무백업 정본 DB 가 4개다** — HEAX pg(users·PAT·secret_values), KooRemapper pg(users·PAT), RA pg,
  포털 users.sqlite. D0 에서 백업부터 편입한다(RA 는 hands-off 원칙대로 블루-그린 컷오버 덤프가 첫 백업).

## 1. 실측 요약 (왜 필요한가)

| 항목 | 실측(dev, 2026-09-05) |
|---|---|
| 리포 안에 쌓인 데이터 | SignalForge 88G 중 `backups/` 84G(30분 pg_dump 385개), AIDataHub 59G 중 `deploy/apptainer` 53G(backups 42G + PGDATA 9.6G), HEAXHub `var/` 11G(sifs 8.7G 재생성분 + app_data 1.1G 중 죽은 `.pre-*` 924M), STE `var/bundle` 9.6G(오프라인 번들, 재생성) |
| 정본 postgres 5 | HEAX :5732 71M · KooRemapper :5436 65M · SF :5434 1.9G · AIDH :5435 9.6G(pgvector) · MXWP :5532 276M. 전부 uid 1000 소유(rootless subuid 미사용 — 파괴검증 확인) |
| 정본 sqlite | 포털 4(users·conversations 9.6M·token_store·agent_audit), HEAX app_data 4(materialtwin 84M 정본 2,663종·stepforge·risk_review **WAL 2M/본파일 4K**·voicerecorder), /data/SmartTwinMCP 2, STE ste.db(헤드노드) |
| 무백업 | HEAX pg · Koorm pg · RA pg · 포털 users/agent_audit/jwt · 블롭 전부(AIDH attachments 14M·mcp_uploads 571M, Koorm storage, SF reports 300M, MXWP minio) · SmartTwinMCP · 복호 키(SECRET_ENCRYPTION_KEY·cred.key·jwt) |
| DB 안 절대경로 | AIDH `record_attachments.file_path` 18/73행 + `mcp_uploads.manifest.sif_path` 4행(dev 절대경로) · MTW `source.local_path` 18행(`.agent_work`) · StepForge 는 컨테이너 경로(`/data/...`)라 호스트 이동 무관 |
| 기존 동기화 프리미티브 | SF `merge-from-drive.sh`(자연키 upsert, **updated_at 열 자체가 없음** — 파괴검증 B4), AIDH `merge-from-drive.sh`(updated_at 가드), materialtwin 병합기 **2개 경쟁**(`_materialtwin_merge.py` vs MTW `app.sync`), MXWP dump/merge 미배선, HEAX appdata-merge 는 materialtwin 외 sqlite **no-op** |
| 채널 없음 | 포털 sqlite · Koorm pg · HEAX pg · RA pg · gateway audit |
| 잔재·크론 | 가짜 크론(스크래치패드 backup-local, 매일 실패)·`/usr/local/bin/apptainer_sync.sh`(파일 없음)·15번째 프로젝트 AINativeAutomationWorkbench 크론·`a.txt`(세션 쿠키 원문, 미추적) |
| /data 이름공간 | `/data/backup` 2.2T(레거시, 무관) · `/data/backups`(HWAX 38G + cluster_setup 2.6G 등 잡동사니) · `/data/hwax`(searxng 시크릿; cluster-deploy 배포 루트로 예약) · `/data/Projects` 741G(무관) |

## 2. 원칙

| # | 원칙 | 근거 |
|---|---|---|
| D1 | `HWAX_DATA_ROOT` 미설정 = 현행 diff 0. 레지스트리·`services.py` 는 env 없으면 아무것도 주입하지 않는다. | plan §9-1·§4 |
| D2 | 옛 경로는 **gitignore 된** 심링크로 영구 브리지. 완료 상태에 "브리지 제거" 없음. | 파괴검증 B1·R1 |
| D3 | 백업 없이 이동 없음 — 이동 직전 스냅샷 + 복원 리허설 1회 선행. | plan §9-5 |
| D4 | 키와 DB 는 짝(`keys_with`). 검증은 키 파일 sha256 만, 원문은 어느 채널에도 안 실린다. | HEAX `.env` SECRET_ENCRYPTION_KEY·HWAXRisk cred.key·포털 jwt |
| D5 | 박스 고유 파일(`identity`)은 절대 복사하지 않는다. | 렌더된 유닛·crontab·origin.json·integration_state·.env·gateway_config·mcp_servers.json·.last-merged |
| D6 | SQLite 는 로컬 fs 만(`stat -f -c %T` 가 `nfs*|cifs|fuse*` 면 거부). PAT store 는 plan 4.2 Postgres 이관이 정답 — 이 계획은 파일째 옮기기만. | context-notes(cluster-deploy):44-47 |
| D7 | 삭제는 사람이 한다. 도구는 `.pre-move`·`pre-sync` 사본을 만들 뿐, `prune` 을 명시적으로 부를 때만 보존정책 안에서 지운다. | SF·AIDH restore 계열이 전부 DROP DATABASE 인 현실 |
| D8 | 한 박스에서 한 인스턴스만 세운다. `apptainer instance stop --all`(MXWP `update.sh:188`) 류는 이관 창 금지. | 실측: 시스템·번들 apptainer 의 instance list 가 동일 40개 → 전부 죽는다 |
| D9 | **컨테이너 서비스는 바인드+env 를 한 재기동에.** 대상 디렉터리가 있으면 동일경로 `--bind` (env 조건 없이). | 파괴검증 B2 |
| D10 | 비-HEAX 서비스 데이터는 `/data/appdata` 에 두지 않는다(`/data/svc/<svc>/`). | plan §2 의 `/data/appdata/<app>` = HEAX 앱 격리 경계, 런처가 canonical 을 서브디렉터리로 씀(B3) |
| D11 | **기준선이 전부 초록일 때만 첫 이동을 시작한다.** D0 게이트 = 전 서비스 health · 백업 전부 산출+복원 리허설 통과 · `data --check` divergent 0 · update-all 1회 정상. 이 스냅샷을 "기준선" 으로 원장에 기록하고, 이관 중에는 **이관과 무관한 수리를 섞지 않는다**(타 리포 수리는 §12-7 로 분리, 각자 커밋). | 사용자 전제(2026-09-05) "다 문제없다는 전제에서 시작" — 문제가 있으면 그것이 이관 때문인지 원래 있었는지 가릴 수 없다 |
| D12 | **프로젝트별 DB 는 완전히 분리한다.** postgres 는 서비스마다 자기 인스턴스·PGDATA(`/data/pg/<svc>/`)·포트·롤·비밀번호. 한 클러스터로 합치지 않고, 스테이징 DB(`_mergestage`·`_syncstage`)도 그 서비스 인스턴스 안에만. sqlite 는 앱/서비스 디렉터리 안에만. 동기화 도구는 두 서비스의 DB 를 절대 교차 조회·조인하지 않는다. | 사용자 전제(2026-09-05). 지금도 5 인스턴스가 분리돼 있다(아래 현황) — 이관이 그것을 무너뜨리면 안 된다 |

**DB 격리 현황(실측)과 이관 후.**

| 서비스 | 지금 | 이관 후 | 비고 |
|---|---|---|---|
| MXWP | 자체 인스턴스 `mxwp_postgres` :5532, 롤 mxwp | `/data/pg/mxwp`, 동일 | pgvector pg15 |
| KooRemapper | `koorm_postgres` :5436, 롤 koorm | `/data/pg/kooremapper` | pg15 |
| HEAX | `heax-pg` :5732, 롤 heaxhub | `/data/pg/heax` | pg16 |
| SignalForge | `sf_postgres` :5434, 롤 signalforge | `/data/pg/signalforge` | pg16 |
| AIDH | `aidh_postgres` :5435, 롤 aidh | `/data/pg/aidh` | pgvector pg16 |
| **RA** | **시스템 PG14 :5433 을 다른 DB(newskoo)와 공유** — 유일하게 격리가 약한 곳 | green 은 자체 인스턴스 `/data/pg/reportarchive`(§7.9 두 안 중 이쪽을 권고) | blue 는 hands-off, 컷오버까지 그대로 |
| sqlite | 앱/서비스별 파일 | `/data/appdata/<app>/`·`/data/svc/<svc>/` — 서비스 경계 = 디렉터리 경계 | 공유 파일 없음 |

## 3. 소유권 모델

세 박스 — **dev**(저작·큐레이션) · **staging = cae00**(업데이트 시험) · **prod**(신규, 사용자 정본).
박스 역할은 `infra/.env` 의 `HWAX_BOX_ROLE=dev|staging|prod` (미설정 = 어떤 동기화도 거부).

| 구분 | 무엇 | 정본 | 방향·모드 |
|---|---|---|---|
| **콘텐츠·큐레이션** | materialtwin 카탈로그, AIDH doc_types·org_*·mcp_upstreams·큐레이션 agents, MXWP documents·tags·divisions, HEAX thermal 모델·앱 SIF, AIDH e5 모델, PaperIngest proposals/knowledge, SF voc_categories·platforms·products 마스터, delib-runs | **dev** | dev → staging → prod **publish**(자연키 merge, 비파괴 / 불변물은 replace) |
| **사용자 생성** | 포털 users·PAT·conversations·agent_audit, HEAX pg users·PAT·apps·secret_values·jobs, Koorm pg users·PAT·sessions·storage, RA 전부, AIDH record_attachments 파일·mcp_uploads, StepForge projects, HWAXRisk 원장, voicerecorder, MXWP users·api_tokens·audit_logs | **prod**(편입 전까지 cae00) | prod → staging **mirror**(시험 데이터 리프레시). dev 로는 안 간다 |
| **양쪽 쓰기(혼합)** | AIDH agents(양 박스 create_agent)·records, SF voc_records(양 박스 크롤) | 표 안 행 단위 | publish 만, 충돌 행은 적용하지 않고 보고(§8.6). **권고: SF 크롤은 prod 단일 + mirror**(§12 결정 5) |
| **박스 고유** | identity 클래스, 슬럼 호스트 로컬(SmartTwinMCP jobs.db, STE ste.db) | 각 박스 | none |

같은 DB 안에 두 소유권이 공존하면(AIDH records vs record_attachments, MXWP documents vs users)
레지스트리 `tables:` 로 쪼갠다 — MXWP `dump_data.py:5-8` 이 콘텐츠 표만 나르는 것과 같은 방식.
**staging 은 어떤 데이터셋의 owner 도 될 수 없다**(스키마 검증). prod 편입은 cae00 사용자 데이터를
prod 로 `seed`(대상이 비어 있을 때만 성립) 1회 → 그 순간부터 cae00 은 staging.

## 4. /data 레이아웃 (cluster-deploy §2 정본 + 이 계획이 채우는 자리 ★)

```
/data/hwax/                          §2 배포 루트 (versions/ current/ cluster.yaml endpoints/ 그대로)
  secrets/                           §2 — 0700 으로 고친다(현재 0755) ★
    portal/jwt/<kid>.key|.pub        ★ backend/secrets/jwt  (config.py:113 JWT_KEYS_DIR)
    searxng/                         현행 그대로
  state/db-sync/{journal.jsonl,last-applied/,conflicts/}   ★ 동기화 원장(AIDH .last-merged 대체 — update-all.sh:169-171)
/data/pg/<svc>/                      §2 — mxwp · kooremapper · heax · signalforge · aidh (RA 는 green 만)
/data/appdata/<app>/                 §2 — **HEAX 앱 전용** 유지. HEAX var/app_data → 여기로 루트 통째 (materialtwin_web step_forge hwax_risk voice_recorder thermal_shock_mcp web_design_agents paper_ingest web_research_mcp)
/data/svc/<svc>/                     ★ 신설 — 비-HEAX 서비스 런타임 데이터 (plan §2 에 한 줄 추가 개정)
  portal/{users,conversations,agent_audit,token_store}.sqlite   (token_store 는 secrets 트리 아님 — plan §7 4.2 이관 전 임시)
  agent-server/artifacts/   mcp-gateway/audit.jsonl
  aidh/{attachments,figures,mcp_uploads}   signalforge/{reports,audit}   mxwp/{minio,meili}
  kooremapper/storage   heax-hub/job_storage
/data/models/                        §2 — voice_recorder · hf(e5·bge, HF_HOME, 선택)
/data/backups/hwax/<box>/<svc>/{daily,pre-move,pre-sync,legacy,sync-out}/   ★ <box> 층 신설 (잡동사니·03:30:01 파일명 충돌 해결)
/data/logs/<box>/<svc>/              ★ 신설 — 회전 대상 로그
/data/wal/  /data/sim/  /data/reports/   §2 예약 그대로
/data/SmartTwinMCP/ /data/delib-runs/ /data/paper_patent_corpus/   기존 유지(백업 편입만; 코퍼스는 external 불간섭)
```

이름 충돌: `/data/hwax/upload-staging`(빈 폐기 후보) 만 `rmdir`. `/data/backups` 의 무관 잔재
(cluster_setup·dpkg.*·alternatives)와 root 소유 `/data/backup`·`/data/server_backup`·`/data/project.tar.gz`
·`/data/Projects` 는 **불간섭 목록**으로 적어 실수 삭제를 막는다(§12 결정 9).

## 5. 레지스트리 — 포털이 경로를 관리하는 방식

세 층이다. **스키마·기본값** = `infra/services.yaml` 의 서비스별 `data:` 블록(추적, 시크릿 없음).
**박스 오버레이** = `infra/.env` 의 `HWAX_DATA_ROOT=/data`·`HWAX_BOX`·`HWAX_BOX_ROLE` 와 클래스별
`HWAX_DATA_<SVC>_<CLASS>=<abs>`. **조회·검증** = `services.py data [svc] [--check]`.
db-sync(§8)·backup-local 은 같은 해석기(`resolve_data`)를 import 한다.

`services.py` 는 `infra/.env` 를 **스스로 읽되 세 키만 뽑는다**(`HWAX_DATA_ROOT`·`HWAX_BOX`·`HWAX_BOX_ROLE`, 인라인 주석 제거) —
자식 환경으로 export 하지 않는다. **유닛에 `EnvironmentFile` 을 추가하지 않는다**(사전점검 NO-GO): infra/.env 의 `COOKIE_SECURE` 줄에
인라인 주석이 있어 systemd 가 값을 오독하고, 무엇보다 `APP_ENV=dev`·`SESSION_SECRET` 등이 services.py 가 띄우는 **모든 자식 서비스에 상속**된다
(heax Settings 가 `APP_ENV=dev` 를 거부해 죽은 2026-09-04 실사고와 같은 경로). 데이터 전용 등록(smarttwinmcp·ste)은 `services:` 가 아니라
별도 최상위 `data_only:` **매핑**에 둔다 — update-sites.sh 무인자 모드가 대상으로 잡지 않고, services.py 가 `start` 없는 항목에서 KeyError 를 내지 않는다.

**바인드는 services.py 가 하지 않는다** — apptainer 명령은 각 리포 `start.sh` 안이다. 계약은
"start 스크립트는 `<root_env>` 를 존중하고, 대상 디렉터리가 존재하면 동일경로로 바인드한다"(D9).

```yaml
data:
  root_env: SF_DATA_ROOT            # 서비스 스크립트가 읽는 루트 env (생략 가능)
  managed: true                     # false = 데이터만 등록(SmartTwinMCP·STE)
  box_scope: local                  # local | slurm-head
  classes:                          # ⚠ 리스트(- name:) 가 아니라 **이름 키 매핑** — update-all.sh §6b 가 `^\s+- name:` 를 grep 해
    pg:                             #   서비스 등록 목록을 만들기 때문(사전점검 실측). 매핑이면 그 grep 에 안 걸린다.
      kind: postgres                # postgres|sqlite|blob|model|log|cache|backup|secret|identity|external
      path: pg/signalforge          # $HWAX_DATA_ROOT 기준
      current: data/postgres        # 현행(리포 상대 또는 ~ 절대) — 브리지·롤백·--check 의 기준
      env: SF_PG_DIR                # 주입 env (없으면 root_env 만)
      bind: /var/lib/postgresql/data
      instance: sf_postgres         # pg_dump·정지에 필요 (3.1b 같은 박스 가정)
      port: 5434
      owner: { dev: content, staging: mirror, prod: canonical }
      sync: publish-merge           # publish-merge|publish-replace|mirror|seed|none
      tables:
        voc_categories: { keys: [code] }
        voc_records:                # ⚠ updated_at 열 없음(실측). 기존 행은 콘텐츠 열만 갱신
          keys: [platform_id, external_id]
          exclude_cols: [id]
          update_cols: [content_original, content_translated, language_detected, country_code, source_url,
                        author_name, published_at, likes_count, comments_count, shares_count, engagement_score, content_hash]
          # 운영 편집 보존(목록 밖): sentiment_score, sentiment_label, categories, topics, processed_at, unmapped_reason, archived_at
      keys_with: []                 # 짝인 secret 클래스 (heax pg → [secret_encryption_key])
      fs: local                     # sqlite 는 강제
      retention: { hourly: 24, daily: 7, pre_sync: 3 }
  identity: [.env, celerybeat-schedule*]   # 복사·동기화 금지 목록
```

`--check` 는 클래스마다 `same`(같은 inode = 브리지 완료) / `divergent`(둘 다 존재·다름 = **위험**) /
`only-current`(미이동) 를 낸다. `divergent` 하나라도 있으면 종료코드 1 → update-all preflight 에 물린다.
`only-target` 상태는 두지 않는다(D2). `services.py` 변경은 세 곳 — `resolve_data()` 추가,
`start_one():109` 의 `env_prefix({**resolve_data(svc), **(svc.get('env') or {})})`, `main()` 에 `data` 액션.

포털 예시(요지): users/conversations/agent_audit/token_store → `svc/portal/`(sqlite, env 이미 존재:
`USER_STORE_PATH`·`CONV_STORE_PATH`·`AGENT_AUDIT_LOG_PATH`·`TOKEN_STORE_PATH`), jwt → `hwax/secrets/portal/jwt`
(`JWT_KEYS_DIR`, `keys_with` 로 token_store 와 짝), upload_staging 은 `enabled: false`(§7.1), nginx 로그 →
`logs/<box>/portal`, delib_runs → 현행 `/data/delib-runs` 그대로(`owner: dev content, publish-replace`).

## 6. 공통 이동 절차

**M-PG (Postgres).**
```
0  backup-local <svc> → /data/backups/hwax/$BOX/<svc>/pre-move/<TS>.sql.gz + .sha256 ; 복원 리허설 1회 완료 확인
1  이 인스턴스만 정지 (--all 금지). SF 는 크론 7·16·17·18(watchdog — 정지한 인스턴스를 되살린다)·21·23 먼저 주석
2  rsync -aHAX --numeric-ids <current>/ /data/pg/<svc>/      (uid 1000 소유 확인됨 — 일반 rsync 로 충분)
3  rsync -aHAXn --checksum 0줄 · PG_VERSION 일치 · du 비교
4  mv <current> <current>.pre-move-<TS> ; ln -s /data/pg/<svc> <current>     (심링크 이름이 .gitignore 에 있는지 D0 에서 확인됨)
5  start.sh 가 env(HWAX_DATA_ROOT) 를 보면 /data 경로를 직접, 아니면 심링크로 — 바인드 source 심링크는 커널이 해석(실측 OK)
6  health · 핵심 표 count(*) = 0단계 · \dx 동일 · backup-local <svc> 1회 정상
7  유예(14일 또는 backup-local 정상 2회 중 늦은 쪽) 뒤 `db-sync prune --pre-move <svc>` (사람이 부른다)
롤백: 정지 → rm 심링크 → mv .pre-move 되돌리기 → 기동. 5~6 사이 쓰기가 있었으면 pg_dump 한 번 더 뜨고 병합 판단.
```

**M-SQLITE.** 쓰기자 **전부** 정지(materialtwin 은 컨테이너·크론·catalog 스크립트 셋). `sqlite3` CLI 가
박스에 없다(파괴검증 B5) — python 으로:
```bash
python3 - "$SRC" "$DST" <<'PY'
import sqlite3, sys
s = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); d = sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()
PY
python3 -c 'import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute("pragma integrity_check").fetchone()[0])' "$DST"
```
`cp` 금지(risk_review.db 본파일 4K·WAL 2M — 단독 cp 는 빈 DB). 디렉터리 단위 심링크(파일 심링크는
-wal/-shm 위치가 갈릴 수 있다). 컨테이너 서비스(포털·Koorm)는 D9 — 바인드+env 를 같은 재기동에.

**M-BLOB.** 가동 중 `rsync -a` 1차 → 정지 → `rsync -a` 델타(`--delete` 금지) → `rsync -an --checksum` 0줄
→ 심링크 → DB 절대경로 행 UPDATE(정지 상태, `BEGIN; UPDATE … replace(prefix); -- 갱신 행수 = 사전 count;
갱신된 경로 전수 존재 확인; COMMIT`) → 기동. 롤백 = pre-move 덤프 또는 역 replace.

## 7. 프로젝트별 계획 (15)

각 항목: 현재→목표 / 결정 지점(파일:행)과 방법 / 특이점 / DB 절대경로 / 롤백 / 단계.

### 7.1 HWAXPortal
- `backend/data/{users,conversations}.sqlite`·`backend/secrets/{token_store,agent_audit}.sqlite` → `/data/svc/portal/` ; `backend/secrets/jwt/` → `/data/hwax/secrets/portal/jwt/` ; `infra/data/nginx-access.log` → `/data/logs/<box>/portal/`.
- 결정 지점: `backend/app/config.py:50·113·116·118·164` 가 이미 env. **바꿀 것** — `infra/scripts/start.sh` 에 D9 바인드(`for d in $ROOT/svc/portal $ROOT/hwax/secrets/portal; [ -d ] && --bind $d:$d`) + `--env` 목록(start.sh:51-70)에 5개 env 조건부 전달. nginx 로그는 `hwax.conf.tmpl:21` 경로를 `${HWAX_NGINX_LOG_DIR:-/workspace/infra/data}` 로 렌더 + nginx 인스턴스 동일경로 바인드.
- **gitignore 선행(B1)**: `.gitignore` 에 `backend/data`·`backend/secrets`(슬래시 없이), `infra/.gitignore` 에 `data`. 현재 `backend/data` 는 패턴 자체가 없다.
- 특이점: `JWT_AUTOGEN_KEYS=true`(start.sh:59) + `keystore.py:35-47` 은 **키 디렉터리가 비면 조용히 새 키를 민팅** → token_store 와 jwt 는 한 단계에서 함께, 기동 전 키 존재·기동 후 kid 개수 불변 확인. `dev-1.key` 0644 → `install -m 0600`. 순서 agent_audit → users → conversations → token_store+jwt.
- upload-staging(`~/.hwax`, 6h TTL 캐시): StepForge 컨테이너가 `$HOME` 마운트로 같은 경로를 읽는 전제(start.sh:56) — `/data` 로 옮기면 HEAX 런처 바인드가 하나 더 필요. `enabled: false`, §12 결정 6.
- DB 절대경로: conversations 가 artifacts URL 을 절대경로로 갖는지 이관 전 `LIKE '/home/%'` 스캔.
- 단계 D1. 롤백 = 심링크 제거 + rename(클래스별).

### 7.2 HWAXAgentServer
- `artifacts/`(ARTIFACT_KEEP=500 mtime 삭제, app.py:634-645) → `/data/svc/agent-server/artifacts/`. `.env`·`mcp_servers.json` 은 identity.
- 결정 지점: app.py:401-402 `ARTIFACT_DIR` env. 두 기동 경로가 같은 값을 보도록 — services.yaml `data:` 주입 + `infra/env-kits/apply-envs.sh agent-server` 가 `HWAX_DATA_ROOT` 있을 때만 `.env` 에 `ARTIFACT_DIR` 줄 추가. gitignore `artifacts`(슬래시 없이).
- `.venv` 는 게이트웨이의 인터프리터이기도 하다(`HWAXMcpGateway/start.sh:21-22`) — 정리 대상 아님.
- 단계 D1.

### 7.3 HWAXMcpGateway
- `audit.jsonl`(감사 = 데이터) → `/data/svc/mcp-gateway/audit.jsonl`(파일 심링크 — `.gitignore:5` 에 파일 패턴이라 안전). `gateway_config.json`·`.bak*`·`provision.env`·`mcp_servers.json` = identity(로컬 민팅 토큰), 자리 이동도 하지 않음(config 경로 이원화 — `provision-config.sh:33`·`sync-provision-env.sh:14-15`).
- 결정 지점: gateway.py:55 `GATEWAY_AUDIT`(os.environ 직접). **`.env` 처방은 무효** — gateway.py·start.sh 어디도 `.env` 를 읽지 않는다(심사 확인). services.yaml `data:` 주입(services.py 경로) + `./start.sh restart` 경로(update-forges)는 네이티브 프로세스라 파일 심링크가 살려 준다.
- 단계 D1.

### 7.4 HEAXHub (+ 앱 8: materialtwin_web·step_forge·hwax_risk·voice_recorder·thermal_shock_mcp·web_design_agents·paper_ingest·web_research_mcp)
- `var/pg` → `/data/pg/heax` ; `var/app_data` → `/data/appdata` **루트 통째 심링크**(앱별 심링크는 런처 traversal 가드 `integration_launcher.py:81-84 resolve()` 에 걸린다 — B3) ; `job_storage`(.env:38 절대경로) → `/data/svc/heax-hub/job_storage` ; `var/logs` 794M·`var/caddy/caddy.log` 557M → 회전. `var/sifs`·`integration_workspaces`·`dist-bundle` 는 cluster-deploy versions/ 몫(범위 밖). `dev2.db`(untracked 84M, 참조 0) → §12.
- 결정 지점: ① `deploy/apptainer/start.sh:72-73` `--bind "$PWD/var/pg…"` → `${HEAX_PG_DIR:-$PWD/var/pg}`. ② `integration_launcher.py:56` → `Path(os.environ.get("HEAX_APP_DATA_ROOT") or _REPO_ROOT/"var"/"app_data")` — 컨테이너 쪽 `/data`(:512,:539) 무변경이라 **앱 코드 무변경**, StepForge 컨테이너 절대경로 유효. HEAX 백엔드는 네이티브(uvicorn, `.env` 소싱)라 env 가 먹는다. ③ `.env:38-39` JOB_STORAGE_ROOT·WORKSPACE_ROOT 값 교체. gitignore `var`·`job_storage`(슬래시 없이).
- **HEAX pg 키**: `.env:54 SECRET_ENCRYPTION_KEY` 가 `secret_values` 와 짝. pre-move 매니페스트에 sha256 기록. **현재 백업 없음** → D0 backup-local WANT 에 `heax`(`instance://heax-pg pg_dump -p 5732`).
- **materialtwin_web 특이점**(쓰기자 3 + 스키마 선행): 크론 19행(30분 `sync-to-drive.sh`)이 `sync.py:394→db.py:128-129` 로 **라이브 DB 에 alembic upgrade 를 적용**해 라이브 스키마(b3c4d5e6f7a8)가 컨테이너 코드(a7b8c9d0e1f2)보다 앞서 있다(실측). 이동 전에 ① 컨테이너 SIF 를 라이브 스키마와 맞추거나(재빌드 SIF 000122a 포함) ② 크론 export 를 `.backup` 사본에서 하도록 바꾼다(§7.15). 절차: 크론 19·20 주석 → 컨테이너 정지 → `pgrep -f scripts/catalog` 0 → `.backup` → integrity → 표 11개 행수(material 2,663 · property_value 42,209 · source 3,013 …) → `curves/` rsync → 기동.
- DB 절대경로: materialtwin `source.local_path` 18행(`.agent_work`, §7.15) + `/tmp` 1행 + 코퍼스 637행(external, 그대로). risk_review.db 는 이관 전 스캔.
- 복사 금지: `var/integration_state/*.json`·`var/external-apps.yaml`·`hwax_risk/origin.json`(hostname — `HWAXRisk/backend/app/main.py:61 box_match`, `:66 secrets_valid`)·`var/caddy/bootstrap.json`. `.pre-*` 13개 924M → `tar --zstd` 로 legacy 보관 후 삭제(§12), 0바이트 `var/app_data/materialtwin.db` 삭제(glob `**/*.db` 에 걸려 tar·백업에 실림).
- 단계 D2(app_data) → D4(pg, kooremapper 뒤·signalforge 앞; 창에 포털 SSO 핸드오프 잠깐 단절 — 야간).

### 7.5 KooRemapper (DynaForge)
- `platform/infra/data/postgres`(users 33·PAT 95, **무백업**) → `/data/pg/kooremapper` ; `platform/storage`(4.9M, 상대경로) → `/data/svc/kooremapper/storage` ; `platform/.env`(JWT) identity.
- 결정 지점: `_common.sh:63 DATA_DIR="${KOORM_DATA_ROOT:-$PLATFORM_ROOT/infra/data}"` 한 줄(start.sh:39-40·90-91·150-151 이 전부 `$DATA_DIR`). `.env` 로딩(:16)이 DATA_DIR(:63)보다 앞서 **리포 `.env` 에 `KOORM_DATA_ROOT` 를 두면 크론 @reboot 경로까지 먹는다**. storage 는 `config.py:61 storage_dir = _PLATFORM_ROOT/"storage"`(`__file__` 기준, 컨테이너 안 `/workspace/platform/storage`) — `KOORM_STORAGE_DIR`(pydantic `KOORM_` prefix) 를 start.sh `--env` 목록(:8-17)에 추가 + `[ -d /data/svc/kooremapper ] && --bind` (B2: 컨테이너는 `/data` 를 못 본다, 실측).
- 특이점: `users_id_seq` 1198(pytest 잔재, storage 고아 263개) — 병합 불가 근거 → `sync: mirror` 만. D0 backup-local WANT 에 `kooremapper`. gitignore `platform/infra/data`·`platform/storage`.
- 단계 D3(storage) → D4 둘째(mxwp 다음).

### 7.6 SignalForge
- `data/postgres` 1.9G → `/data/pg/signalforge` ; `backups/` 84G → `/data/backups/hwax/<box>/signalforge/` + 보존 축소(§9) ; `reports/` 300M·`audit/` → `/data/svc/signalforge/` ; `logs/` 125M·`~/.apptainer/instances/logs/…/sf-crawler-worker.err` 902M → 회전 ; `.env`·`celerybeat-schedule*` identity.
- ⚠ **`reports/`(추적 파일 248)·`audit/`(추적 9) 는 심링크로 바꿀 수 없다**(사전점검 실측 — 심링크로 바꾸면 워크트리에서 추적 파일이 삭제로 보인다). 이 둘은 env/바인드 방식(`REPORT_DIR`·`/reports`·`/audit` 바인드)으로만 옮기거나, SF 리포에서 산출물 추적 해제 커밋이 선행돼야 한다(§12-7). D3 에서 SF 블롭은 **pg·backups·logs 만** 심링크.
- 결정 지점: `scripts/_common.sh:10 DATA_DIR="${SF_DATA_ROOT:-$PROJECT_ROOT/data}"` **+ `load_env()` 끝에 재평가**(`DATA_DIR="${SF_DATA_ROOT:-$DATA_DIR}"`) — DATA_DIR 이 load_env(:63-77) 보다 먼저 평가되어 리포 `.env` 만으로는 안 먹는다(B6). backups 는 `backup-to-drive.sh:119-130` 로컬 디렉터리 → `SF_BACKUP_DIR`. reports 는 crawler 가 컨테이너 안 `parents[2]/reports` 라 7/7 이후 **깨져 있음** — 이관과 별개 수리(`up.sh:208·214` crawler 바인드에 `/reports`), §12 결정 7.
- 특이점: 크론 7·16·17·18(watchdog)·21·23 정지 후 M-PG. `signalforge_mergestage` 잔존 확인. gitignore `data`·`backups`·`logs`·`reports`·`audit`.
- 소유권: voc_records 양 박스 크롤 + updated_at 없음 → §12 결정 5(권고: prod 단일 크롤 + mirror).
- 단계 D3(reports·audit) → D4 넷째.

### 7.7 AIDataHub
- `deploy/apptainer/data/postgres` 9.6G → `/data/pg/aidh` ; `data/{attachments,figures}` → `/data/svc/aidh/` ; `api_server/mcp_uploads/_uploads` 571M(참조 4/6) → `/data/svc/aidh/mcp_uploads` ; `deploy/apptainer/backups` 42G → 폐지·통합(§9) ; `logs/pre-update-db-20260721-042917.sql.gz` 393M → legacy ; `~/.cache/huggingface` → `/data/models/hf`(선택).
- 결정 지점: `_common.sh:13 DATA_DIR="${AIDH_DATA_ROOT:-$APPT_DIR/data}"` + load_env(:86-100) 뒤 재평가(B6). `start_api.sh:30-31` 이 기동마다 `api_server/.env` 에 ATTACHMENTS_DIR/FIGURES_DIR 절대경로를 재렌더 — 이동 후 첫 기동이 곧 갱신(손편집 금지). **API 는 네이티브**(`start_api.sh` "Apptainer 없이") 라 `AIDH_MCP_UPLOADS_DIR`(`mcp_upload_svc.py:484-489` os.environ) 는 `deploy/apptainer/.env` 에 두면 `load_env` 의 `set -a` 로 uvicorn 이 상속한다(파괴검증 R6/S9). gitignore `deploy/apptainer/data`·`deploy/apptainer/backups`·`api_server/mcp_uploads/_uploads`.
- **DB 절대경로 UPDATE 필수**: `record_attachments.file_path` 18/73행(`mcp_upload_svc.py:1207,1232`), `mcp_uploads.manifest.sif_path` 4행(`apptainer_build_svc.py:205`) — prefix replace 22행. 미참조 SIF 2개 246M 은 복사하지 않고 목록(§12).
- 특이점: `aidh_mergestage` 잔존 확인. 확장 vector 0.8.2·pgcrypto 는 같은 postgres.sif. `.last-merged` 는 db-sync 원장이 대체(update-all.sh:169-171).
- 단계 D3(블롭+22행) → D4 마지막.

### 7.8 MXWhitePaper
- `infra/data/postgres` 276M → `/data/pg/mxwp` ; `infra/data/minio` 17M(354+175 객체) → `/data/svc/mxwp/minio` ; Meili 인덱스는 **바인드가 죽어 있어**(start.sh:83 은 `infra/data/meili` 를 붙이지만 `--db-path`/`MEILI_DB_PATH` 가 없어 실제는 리포 루트 `data.ms` 107M) — `MEILI_DB_PATH=/meili_data` 수리 없이는 `enabled: false` ; `infra/backups` 34M → legacy ; `.env.bak` 복사 금지·삭제 권고.
- 결정 지점: `infra/scripts/_common.sh:44 DATA_DIR="${MXWP_DATA_ROOT:-$REPO_ROOT/infra/data}"` (`.env` 로딩 :10 이 앞서 리포 `.env` 로 먹는다). gitignore `infra/data`·`data.ms`·`infra/backups`.
- **`update.sh:188 instance stop --all`** — 이관 창 전면 금지, 수리 요청(§12 결정 7).
- 단계 D3(minio) → D4 첫째(가장 작아 절차 검증용).

### 7.9 ReportArchive — hands-off, 블루-그린
- 현행(blue) 에는 **아무것도 하지 않는다**(env·심링크·재기동 금지, `services.yaml:134-140 update: false` 유지, backup-local 제외 유지 — 2026-08-02 결정).
- green 은 처음부터 `/data` 규약: `DATABASE_URL=…/report_automation_green`(같은 PG14 클러스터에 DB 추가) 또는 `/data/pg/reportarchive`, `UPLOAD_DIR=/data/svc/reportarchive/uploads`, `EMBED_BUNDLES_DIR=…/uploads/embed_bundles`(`.env.production.example:52` 규약), APP_PORT 3100·MCP_PORT 3102, 별도 체크아웃(plan §3.2 "같은 박스 변형").
- 레지스트리 `managed: false, sync: none`. 컷오버 덤프(`pg_dump | psql` + `upload_dir_path` rsync)는 db-sync `snapshot --readonly` 만 빌려 쓴다. 함정: `files.storage_path` 상대경로(안전)·쓰기 중 스냅샷 파일 누락·`orphan_cleanup`(파일 없으면 DB 행 삭제)·systemd 타이머 유닛 이름 고정·pgvector 0.8.3 필요.
- 단계 D6. 롤백 = routes.env 한 줄.

### 7.10 StepForge
- 정본은 HEAX appdata `step_forge/`(§7.4 에서 함께). DB 가 컨테이너 절대경로(`/data/projects/…`, ingest.py:62-65, jobs.py:118-120)라 호스트 이동 **투명**. 리포 `var/`(dev 폴백, `var/materials/local.json` SIGY 1건)는 이관 대상 아님.
- `sync_material_db.py` 는 `data_root()` 로 목적지를 정한다 — 문서에 `STEPFORGE_DATA_DIR=/data/appdata/step_forge` 명시. `core/materials.py:33 DB_CANDIDATES` 의 KooRemapper 절대경로는 cae00 에서 조용히 깨지는 유형(기록).
- 동기화: projects·stepforge.db 사용자 생성 → `sync: mirror` 명시(현행 appdata-merge 의 "조용한 no-op" 제거).

### 7.11 SmartTwinExplorer — 범위 밖, 등록만
- 별 박스(헤드노드 VM `/opt/ste/state/ste.db` + WAL 2.4M, `/srv/ste/jobs`). 레지스트리 `managed: false, box_scope: slurm-head, sync: none`. 백업 채널 부재는 §12 결정 13. `/srv/ste/munge.key 0644` 가 NFS 공유에 있음 — 데이터 배치 아닌 보안 결함(별건).

### 7.12 SmartTwinMCP
- **이미 `/data`** (`/data/SmartTwinMCP/{jobs,audit}.db`, `/etc/systemd/system/smarttwin-mcp.service:27-28` 절대경로). 이동 없음. 할 일: D0 backup-local WANT 에 `smarttwinmcp`(python `.backup`), 레지스트리 `managed: false, sync: none`(jobs.db 는 슬럼 호스트당 1개 설계). NFS 전환 시 두 박스가 같은 WAL SQLite 를 연다 — §12 결정 10.

### 7.13 HWAXRisk
- 정본 HEAX appdata `hwax_risk/`(risk_review.db + WAL, `cred.key` 44B = `keys_with`, `origin.json` = identity). §7.4 에서 이동. 동기화 `mirror` — mirror 받은 staging 은 cred.key 가 달라 `portal_pat_enc` 복호 불가 = "이관 직후" 상태가 **정상**(경고만 내고 진행, 원장 보존 우선).

### 7.14 PaperIngest
- HEAX appdata `paper_ingest/` 비어 있음(자리만). 진짜 데이터는 external — `/data/paper_patent_corpus` 223G(HWAX 밖 소유, 불간섭), `~/claude/ExpertAgents/knowledge` 130M(remote 없는 git, 미커밋 27 = 유일본), `ExpertGrounding` 174M(remote 없음). **재생성 불가한 작은 원장만** backup-local 편입: `_index/manifest.json`(17M, 잃으면 144G 재색인)·`_index/_verdicts/discarded.jsonl`·`knowledge_grounding/agent_papers.json`·`_index/proposals/` + ExpertAgents/knowledge `git bundle`. 컨테이너 `CORPUS_DIR=/data/corpus`(manifest.yaml:27) 어긋남 수리는 HEAX 매니페스트 소유(§12 결정 7).

### 7.15 MaterialTwinWeb
- 정본 DB 는 HEAX appdata(§7.4). 이 리포 몫: ① `backend/var/data/materialtwin.db`(70종, 1단 낡은 스키마) 는 샌드박스 — 단 `.mcp.json` 이 이걸 가리켜 이 리포의 Claude 가 라이브 2,663종을 못 본다(§12 결정 7). ② `.agent_work/` 327M = 라이브 `source.local_path` 18행이 참조하는 출처 원문 → `/data/appdata/materialtwin_web/sources/agent_work/` M-BLOB + 18행 UPDATE(+`/tmp` 1행은 파일 구해 UPDATE) + 심링크. gitignore `.agent_work`. ③ 크론 19·20행 — export 를 **`.backup` 사본에서**(`sync-to-drive.sh:31` 자리: `TMP=$(mktemp -d); python .backup → $TMP; cp -r curves; MATERIALTWIN_DATA_DIR=$TMP`) — 라이브에 alembic 이 닿지 않게. ④ 병합기는 `_materialtwin_merge.py` 하나로 통일, `app.sync import`(sync-from-drive.sh) 운영 금지. data-bundles 크론은 D5 뒤 정지(소비자 없음). `MaterialTwin/sif` Drive 중복 4.8G → §12.

## 8. DB 동기화 — 기존 스크립트 + ssh 전송 + 경로 치환

**결정(2026-09-05, 사용자)**: 박스 간 전부 ssh 가능 → **새 병합 엔진을 만들지 않는다.** 지금 update-all·deploy-all 이 부르는
merge 스크립트를 그대로 두고, (1) 입력 덤프가 Drive 다운로드가 아니라 rsync 로 온 **로컬 파일**이 되게, (2) 어느 박스가
어느 박스로 무엇을 보내는지를 레지스트리 `owner`(§3)로 통제하고, (3) 원장에 남긴다. Drive 는 코드·아티팩트 반입과
오프사이트 백업 자리만 지킨다(cluster-deploy context-notes:20-24 결정과 일치).

### 8.1 흐름 — 세 단계, 전부 기존 도구
```
[소스 박스]  덤프 생산 = 기존   backup-local.sh <svc>(daily) · SF backup-to-drive.sh 의 로컬 덤프 · HEAX appdata-to-drive.sh 의 tar 생성부(업로드 전 단계)
      │  rsync -a --partial (ssh)   /data/backups/hwax/<src>/<svc>/daily/<TS>… → <dst>:/data/hwax/.staging/inbound/<svc>/<TS>/   + sha256 검증(불일치 = 중단)
[대상 박스]  사전 스냅샷 = 기존   backup-local.sh <svc> 1회 → pre-sync/<TS>/ 로 복사 (롤백 지점은 여기 하나)
             merge = 기존         AIDH  AIDH_MERGE_DUMP=<file> deploy/apptainer/merge-from-drive.sh        (이미 로컬 입력 지원 :24-32)
                                  SF    SF_MERGE_DUMP=<file>   scripts/drive-sync/merge-from-drive.sh      (:33-37 에 6줄 — AIDH 와 같은 모양)
                                  HEAX  HEAX_APPDATA_TAR=<file> deploy/apptainer/appdata-merge-from-drive.sh (:20-22 에 6줄) → _materialtwin_merge.py 그대로
                                  MXWP  infra/scripts/data-merge.sh <tar> --on-conflict=skip                (이미 로컬 입력)
             원장 append          /data/hwax/state/db-sync/journal.jsonl  { ts, svc, class, from, to, mode, snapshot_ts, pre_sync_path, result, counts, operator }
```
얇은 래퍼 `infra/scripts/db-sync.sh <push|pull|mirror|status|rollback> --svc <s> --to|--from <box> [--plan]` (bash ~150줄) 이 위
세 단계를 순서대로 부르고 `HWAX_BOX_ROLE × owner` 로 방향을 검사할 뿐이다. 박스 목록은 `infra/boxes.yaml`(gitignore, `{prod: {host, user}}`).
`--from <box>` 를 다른 박스에서 부르면 `ssh <box> 'backup-local.sh <svc>'` 로 소스에서 덤프를 만들고 받아 온다(3.1b 같은 박스 가정 유지).

### 8.2 사용자 데이터 mirror — 채널이 없던 4곳도 기존 도구로
- **postgres**(Koorm·HEAX·그리고 콘텐츠 표 밖의 SF/AIDH/MXWP 사용자 표): 소스 backup-local 덤프 → rsync → 대상에서 pre-sync 후
  **기존 restore 계열**(`restore-db.sh` — DROP DATABASE 지만 staging 에선 그것이 mirror 의 정의). restore 스크립트가 없는 Koorm·HEAX 는
  `pg_restore --clean --if-exists` 4줄. `exclude_on_mirror` 표(시크릿·PAT 해시)는 복원 뒤 TRUNCATE + `provision-config.sh --force` 재민팅.
- **sqlite**(포털 4종·HEAX 앱 4종): `.backup` 파일 rsync → 서비스 정지 → 파일 교체(`mv -T`) → 기동.
- **블롭**: `rsync -a` (identity·cache·`*.db-wal`·`*.pid` `--exclude`).
- **prod 는 mirror 수신 무조건 거부**(`HWAX_BOX_ROLE=prod`). prod 편입 1회는 "prod 가 비어 있을 때만 허용되는 mirror" = `seed`.
- **키**: mirror 받은 staging 은 복호 불가가 정상(HEAX `secret_values`·HWAXRisk `portal_pat_enc`) — 재프로비저닝으로 해소. 키 원문은 어느 채널에도 안 실린다.

### 8.3 방향·소유권 — §3 그대로
콘텐츠(dev owner) → staging → prod **publish**(기존 merge, 비파괴). 사용자 데이터(prod owner) → staging **mirror**. staging 은 owner 불가.
`mirror→canonical`·`own→타박스` 거부. 목록(`tables:`)에 없는 표는 대상 아님. staging→prod publish 는 **자동 없음** — update-all(staging) 헬스게이트 뒤 사람이 `db-sync push --to prod`.

### 8.4 기존 스크립트 안의 소규모 수정 (충돌 처방 — 우선순위순)
1. AIDH `agent_sample_embeddings`(autoincrement 대리키) 동기화 제외·대상 재계산 — 1줄 삭제.
2. AIDH `agents` 기존 행 `DO NOTHING`(신규만 삽입) + 다른 행은 `conflicts/<TS>.jsonl` 보고 — 양 박스 create_agent 덮어쓰기 방지.
3. AIDH `records` 충돌키를 자연키 `(data_type,team,group,year,seq)`(`models.py:72-80`)로, id 제외·자식 FK 재매핑(`_materialtwin_merge.py:539-556` 방식).
4. SF `voc_records` `DO UPDATE SET` 을 `update_cols` 허용목록으로(§5 실측 컬럼 — `updated_at` 없음), FK 로 버린 행 수 보고. (§12 결정 5 가 "prod 단일 크롤" 이면 이 표는 publish 대상에서 빠져 수정 불필요.)
5. materialtwin — `_materialtwin_merge.py` 하나만, MTW `app.sync import` 운영 금지. 크론 export 는 `.backup` 사본에서(§7.15).
6. HEAX 비-DB 시드 루프(`appdata-merge-from-drive.sh:48-54`)에 identity·cache `--exclude`.

### 8.5 검증·원장·상태
기존 merge 스크립트의 출력(표별 삽입·갱신·`fk_violations`·`*_misses`·`ownership_diffs`)을 그대로 원장에 첨부 · 행수 대조(merge: 후 ≥ 전 / mirror: 후 = 소스) ·
sha256 · `alembic_version` 이 대상 코드가 아는 리비전인지(소스가 앞서면 거부 — 지금 dev materialtwin 이 이 상태) · 서비스 `health` ·
`services.py data --check` divergent 0. `db-sync status` 는 원장 `last-applied` 로 "박스×서비스 마지막 적용 TS" 한 표(age>26h ✗).
`--plan` 은 매니페스트와 대상 count 만 읽고 예상만 낸다(AIDH `--dry-run` 이 다운로드도 안 하던 혼란을 피하려 이름을 바꿈).

### 8.6 Drive 의 자리
- 코드·아티팩트: `build-all-to-drive.sh` → `deploy-all-from-drive.sh` **무변경**.
- 데이터 동기화: **Drive 를 거치지 않는다.** dev→cae00 의 db-dumps 다운로드 단계만 rsync 로 바뀌고 merge 는 동일. update-all §3(AIDH)·deploy-all(SF·heax appdata)은 `DB_SYNC=1` 이면 inbound 파일을, `0`(기본) 이면 종전 Drive 를 본다 — 같은 덤프로 결과 diff 0 확인 뒤 기본값 전환.
- 오프사이트 백업: SF·AIDH `backup-to-drive` 일 1회 크론은 유지하되 보존 3세대(§9). 평문 문제는 §12-3(선택). `*/30` push(SF 16·MTW 19)는 동기화 목적이 사라져 D5 뒤 정지.
- `HEAX_DRIVE_*`·`SF_DRIVE_*` 등 기존 remote 설정은 손대지 않는다.

### 8.7 낭비 줄이기 (사용자 요구: 기존 방식은 유지하되 동기화의 낭비는 줄인다)

지금의 낭비(실측): SF 가 30분마다 232MB 전량 덤프(하루 11GB, 로컬 84G + Drive 11.8GiB) · AIDH 가 같은 DB 를 하루 두 번 4.4G 전량 덤프
(임베딩 포함) · MTW 30분 번들(소비자 없음) · SIF 가 Drive 에 두 번 · cae00 이 매 update-all 마다 4.4G 를 내려받아 merge. 줄이는 법 — 우선순위순.

| # | 방법 | 효과 | 기존 방식과의 관계 |
|---|---|---|---|
| 1 | **덤프는 하루 한 번, 한 파일** — backup-local 의 daily 덤프가 곧 동기화 소스. 별도 덤프 없음 | SF 하루 48회→1회, AIDH 2회→1회. 디스크 ~150G 회수 | backup-local 그대로, 크론 7·16·17·19 정리만 |
| 2 | **안 바뀌면 안 보낸다** — 전송 전에 소스 manifest(표별 행수·max(updated_at)·sha)와 대상 원장 `last-applied` 비교, 같으면 종료 | 콘텐츠가 안 바뀐 날(대부분)은 전송 0 | 래퍼의 첫 단계, 스크립트 무수정 |
| 3 | **표 단위 덤프** — publish 는 `pg_dump -t <콘텐츠 표>` 만(레지스트리 `tables:`). 사용자 표·파생 표(embeddings)는 안 실림 | AIDH 4.4G → 수십 MB 급(record_sections 임베딩 8.3G 가 빠짐) | merge 스크립트는 받은 덤프의 표만 처리 — 입력이 작아질 뿐 동작 동일 |
| 4 | **증분(워터마크)** — `updated_at`/`created_at`/`collected_at` 이 있는 표는 `WHERE col > <last-applied>` 로 COPY 한 델타만(AIDH records·agents 는 updated_at, SF voc_records 는 collected_at 삽입 워터마크, materialtwin 은 content_hash). 워터마크 없는 표만 전량 | 일상 전송이 KB~MB | merge 의 upsert 는 델타 입력에도 동일하게 동작(자연키 ON CONFLICT) |
| 5 | **블롭은 rsync 델타** — `rsync -az --partial` 이 바뀐 파일만. sha256 은 manifest 로 1회 | curves·attachments·storage 는 변경분만 | — |
| 6 | **주기 분리** — 콘텐츠 publish 일 1회(03:50), 사용자 mirror 주 1회, 오프사이트 백업 일 1회 3세대 | 30분 주기 소멸 | 크론 16·19 정지 |
| 7 | **Drive 중복 제거** — MaterialTwin/sif(4.8G) 는 HEAXHub/dist 와 중복 → 정지, db-dumps 3세대 | Drive 용량·업로드 시간 | §12-8 |

증분(4)의 정직한 한계: 삭제는 전파되지 않는다(비파괴 원칙과 일치 — 삭제는 어차피 안 나른다). 워터마크 열이 없거나 신뢰할 수 없는 표
(SF voc_records 의 분류·감성 갱신은 collected_at 이 안 움직인다)는 전량 덤프로 후퇴하되 표 단위라 여전히 작다. 첫 동기화(last-applied 없음)는 전량.

### 8.7 스케줄
03:30 각 박스 backup-local(기존) · 03:50 dev→staging `push`(콘텐츠) · staging→prod 는 수동 · 일요일 04:30 prod→staging `mirror`(§12-4 마스킹) · 매일 05:00 prod `/data/backups/hwax/prod/` → staging rsync(오프박스 2차 보관).

## 9. 보존·정리 정책

| 대상 | 현재 | 정책 | 변경 지점 |
|---|---|---|---|
| SF 로컬 덤프 | 30분 × 7일 = 385개 84G | **시간별 24 + 일별 7**(≈7G), `/data/backups/hwax/<box>/signalforge/` | `backup-to-drive.sh:119-130` `-mtime +7` → 개수 기반 prune(sha256·RESTORE-GUIDE 동반). 크론 16행 `*/30` → 매시. D5 뒤 정지 |
| AIDH 이중 덤프 | `deploy/apptainer/backups` 42G(KEEP 10) + `/data/backups/aidh` 33G | **한 곳**(daily 7, Drive 3). backup-to-drive 로컬 출력을 `…/aidh/daily` 로, backup-local 당일 덤프 있으면 재덤프 생략 | AIDH `backup-to-drive.sh` 로컬 경로·KEEP |
| materialtwin `.pre-*` 13개 924M | 정책 없음 | `tar --zstd` 1회 legacy 보관 후 삭제. 0바이트 `var/app_data/materialtwin.db` 삭제. 이후 pre-merge 는 pre-sync 3세대 | `appdata-merge-from-drive.sh:35` 경로 |
| pre-move / pre-sync | 신설 | 14일 또는 backup-local 정상 2회 중 늦은 쪽 / 최근 3세대. `db-sync prune` 만 | `dbsync/prune.py` |
| backup-local 세대 정리 | `find $BACKUP_ROOT` 전체 `-mtime +7`(:144-145) — 수동 아카이브·무관 잔재까지 삭제 | `hwax/$BOX/*/daily` 로 한정 | `backup-local.sh:144-145` |
| backup-local 파일명·로그 | `<svc>-<TS>` 두 박스 충돌 · `/data/backups/backup.log` 하드코딩(:30) | `<svc>-<box>-<TS>` · `$BACKUP_ROOT/hwax/$BOX/backup.log` | `backup-local.sh:30·35·44-55·97·121` |
| backup-local WANT | aidh signalforge mxwp materialtwin portal(2파일) | + `heax`(pg :5732) `kooremapper`(pg) `portal` 4파일+jwt 0600 tar `gateway`(audit) `smarttwinmcp` `delib-runs` `paper-index`(4 원장) `expertagents`(git bundle) `secrets`(rclone.conf 등 0600 tar, Drive 로는 절대 안 나감). RA 제외 유지 | `backup-local.sh:18` WANT + 함수 |
| 로그 회전 | 없음(caddy 557M·worker 488M·sf-crawler-worker.err 902M·gateway.log 20M·mcp-gateway.log 33M·nginx-access·mtw-sync·backup.log·uvicorn.log.1 309M) | 사용자 logrotate `daily, rotate 14, compress, delaycompress, copytruncate, maxsize 200M` — **단 O_APPEND 쓰기자에만**(사전점검: gateway.log·apptainer `.out/.err` 는 O_APPEND, **HEAX worker/backend·AIDH uvicorn 은 `nohup >` 라 O_APPEND 아님 → copytruncate 시 sparse 구멍**). 이 셋은 기동 스크립트 `>`→`>>` 1글자 수정(§12-7) 뒤 편입, caddy 는 Caddy 자체 `roll` 설정, nginx 는 컨테이너 안이라 USR1 경로 확인 뒤 | 신규 `infra/logrotate/hwax.conf` + `install-logrotate.sh`(멱등, update-all 호출) |
| Drive 보존 | SF db-dumps 53개 11.8GiB, AIDH 5세대 20.6GiB, MTW sif 4.8GiB 중복, 고아 채널(HEAXHub/browser·app-data/{voice_recorder,web_design_agents}·AIDataHub/sync) | D5 뒤 db-dumps 3세대, 고아는 §12 결정 후 purge | 각 `*-to-drive.sh` RETAIN |
| 가짜·죽은 크론 | 24행 fakerepo backup-local(매일 실패) · 1행 `apptainer_sync.sh`(파일 없음) | 제거(24행 확정, 1행 출처 확인 후) | crontab |

## 10. 단계와 검증 게이트

각 단계는 독립 커밋 묶음. 다음 단계는 앞 게이트 통과 뒤에만. cluster-deploy Phase 대응을 적는다.

| 단계 | 내용 | 성공 판정(자동) | 롤백 | 대응 |
|---|---|---|---|---|
| **D0 무영향 추가** | ① 8개 리포 `.gitignore` 에 심링크 이름(슬래시 없이; SF 는 `reports`·`audit` 제외) 선행 커밋 ② `services.yaml data:`(클래스 매핑) 전 서비스 + `data_only:` + `services.py resolve_data`/`data --check` + `infra/.env` 세 키만 자체 읽기(EnvironmentFile 금지) ③ db-sync `snapshot·verify·status` 만 ④ backup-local WANT 확장·경로 한정·파일명 박스·로그 경로 ⑤ logrotate(O_APPEND 쓰기자만) ⑥ python sqlite 헬퍼 ⑦ `chmod 0700 /data/hwax/secrets`, `rmdir /data/hwax/upload-staging` ⑧ 가짜 크론 제거(사용자 확인) ⑨ 복원 리허설(pg 5·sqlite 3, staging DB/임시 파일) | `HWAX_DATA_ROOT` 미설정에서 `services.py up/status/down` 출력 diff 0 · `data --check` 전 클래스 `only-current` · 심링크 후보 경로 `git status --porcelain <link>` 빈 결과(`check-ignore <link>/` 는 fatal — 쓰지 말 것) · backup-local WANT 전부 sha256 산출 · 리허설 로그 | revert 로 충분(추가만) | P0.3 |
| **D1 포털 자기 것** | §7.1(agent_audit→users→conversations→token_store+jwt, 바인드+env 한 재기동) · §7.2 artifacts · §7.3 audit.jsonl · nginx 로그 | 로그인 · 기존 PAT 로 게이트웨이 tools/list 개수 동일 · conversations count 동일 · launch-JWT heax SSO 1회 · jwt kid 개수 불변 · `data --check` same · 심링크+bind 커널 해석 실측 기록 | 클래스별 심링크 제거 + rename | P1.2 데이터판 |
| **D2 HEAX appdata** | MTW 크론 읽기 전용화(§7.15③) → `HEAX_APP_DATA_ROOT` env + `var/app_data → /data/appdata` 루트 심링크(§7.4) · `.agent_work` + 18행 UPDATE · `.pre-*` legacy 보관 | HEAXHub /health 200 + 앱 8개 페이지 · 표별 count · integrity ok · `register_material` 1회 · `source.local_path` 존재 100% · 컨테이너 `/data` 내용 동일 | 루트 심링크 제거 + rename | P5 선행 |
| **D3 비-HEAX 블롭** | AIDH attachments·figures·mcp_uploads(+22행) · SF reports·audit · MXWP minio(+meili 수리 결정 시) · Koorm storage(+`KOORM_STORAGE_DIR` bind) · HEAX job_storage | DB 경로 행 전수 존재 · 첨부 다운로드 표본 200 · MinIO 객체 354+175 · `data --check` same | 심링크 제거 + 역 replace(pre-move) | — |
| **D4 Postgres** | M-PG: mxwp(276M) → kooremapper → heax(키 sha 기록) → signalforge(1.9G, 크론 6개 정지) → aidh(9.6G) | `pg_isready` · 표별 count · `\dx` · 앱 health · backup-local 1회 · `data --check` same | M-PG 롤백 | P2.4 를 dev 로컬 /data 에서 선행 |
| **D5 db-sync 적용 verbs** | `stage·apply·rollback·prune·push/pull` · update-all/deploy-all 세 merge 를 `DB_SYNC` 로 이중화 · `*/30` Drive push 정지 · AIDH 이중 덤프 통합 | 같은 덤프로 종전 merge 와 `--plan` diff 0 · 원장 1건 · 롤백 리허설 1회 · divergent 0 | `DB_SYNC=0`(종전 경로 그대로) | P3.1b |
| **D6 prod 편입** | prod 에 D0~D4 레이아웃(`HWAX_DATA_ROOT=/data`) · cae00→prod `seed`(콘텐츠 publish + 사용자 데이터 1회, 키 봉투 수동, **cae00 쓰기 정지 창**) · 소유권 전환(cae00=staging) · RA 블루-그린(§7.9) · 주간 mirror · prod `provision-config.sh` 새로 | prod 전 서비스 health · cae00 발급 PAT 가 prod 게이트웨이에서 유효 · RA rat_ 토큰 유효 · 첫 mirror 성공 · 오프박스 백업 도착 | prod 미노출 유지(DNS 전환 전) | plan "cae00 전환" 재정의(§12 결정 1) |

각 단계 시작 전 `context-notes.md` 에 시작·실측·결정을, `checklist.md` 에 체크박스를.

## 11. 리스크·함정 (증명된 것 우선)

1. **B1 심링크가 `git stash -u` 에 치워진다** — gitignore `dir/` 패턴은 심링크를 무시하지 않는다(실측 git 2.34). `update-all.sh:76`·`deploy-all-from-drive.sh:106` 매 실행. 치워진 뒤 `_common.sh` 의 `mkdir -p` → initdb → 빈 DB / 포털은 새 JWT 민팅. **D0 ① 가 선행 조건.**
2. **B2 컨테이너는 호스트 `/data` 를 못 본다** — 포털(`start.sh:49-50`)·Koorm(apptainer.conf 바인드 없음) 실측. 바인드된 디렉터리 안의 심링크는 컨테이너 안에서 dangling → `user_store.py:55 mkdir` FileExistsError 로 기동 실패. → D9.
3. **B3 HEAX 런처 traversal 가드**(`integration_launcher.py:81-84 resolve()`) — 앱별 심링크는 예외. 루트 통째 + env. 비-HEAX 를 `/data/appdata` 에 두면 `appdata-to-drive.sh`·`backup-local.sh` 가 그것까지 tar 에 담아 Drive 평문 → `/data/svc` 분리(D10).
4. **B4 SF voc_records 스키마** — updated_at 없음, 설계 초안의 update_cols 7개 중 6개가 존재하지 않는 열. §5 의 목록이 실측본.
5. **B5 `sqlite3` CLI 없음** — python 헬퍼.
6. **B6 `services.py` 가 env 를 못 받는다** + SF·AIDH `_common.sh` 는 `.env` 로딩 전에 DATA_DIR 평가 → 자체 읽기 + 재평가.
7. **R1 크론·워치독 재기동은 env 없이 옛 경로** → 브리지 영구(D2).
8. `JWT_AUTOGEN_KEYS` 조용한 민팅(`keystore.py:35-47`) · WAL sqlite `cp` 사고 · DB 절대경로 행(AIDH 22·MTW 19) · `SECRET_ENCRYPTION_KEY`·`cred.key` 짝 · MTW 크론이 라이브 스키마를 앞당김(지금 실측 상태 — 컨테이너 재기동 시 기동 실패 가능) · MXWP `update.sh:188 --all` · SF watchdog 이 정지한 pg 를 되살림 · `hwax-stack.service` 가 부팅마다 `git pull --ff-only`(이관 중 미커밋 편집 = 옛 코드) — 전용 브랜치 + 작업 중 유닛 일시 disable · update-all §3.5 가 agent-server `.env` 를 `sed -i` · RA `orphan_cleanup` · 게이트웨이 토큰 3중 사본(identity) · `/data/backups` 전역 find · 03:30:01 파일명 충돌 · Drive 평문 덤프(age 승인 전까지 기존 채널 유지, D5 뒤 정지) · 단일 rclone 자격증명(백업 없음) · `a.txt` 세션 쿠키 원문 · prod 편입 이중 정본 창(cae00 쓰기 정지) · `stat -f %T` 는 ext4 를 `ext2/ext3` 로 보고(거부목록 방식) · `find <심링크>` 는 하위를 안 봄(trailing slash) · 동시 세션 작업 충돌(services.py·services.yaml·backup-local.sh 공유 — `git add -A` 금지).

## 12. 결정 필요 (사용자)

1. **토폴로지 개정 승인** — plan §0·§9-7 "cae00 은 클러스터 검증 완료까지 불간섭" → "prod 편입(D6) + cae00 강등→staging". 이 계획은 개정을 전제로 썼다.
2. **prod 박스** — hostname·계정, `/data` 가 로컬인지 NFS 인지(NFS 면 sqlite 클래스를 singleton 노드 로컬로). ~~ssh 가능 여부~~ → **전부 ssh 가능(확인)**.
3. (선택, 우선순위 낮음) **오프사이트 Drive 백업의 암호화(age)** — 동기화는 Drive 를 안 거치므로 남는 것은 SF·AIDH 일 1회 백업 덤프의 평문 문제만.
4. **prod→staging mirror 를 원문으로 할지 마스킹**(PAT 해시·이메일·대화 원문이 시험 박스에 복제된다).
5. **SF voc_records 소유권** — 권고: prod 단일 크롤 + dev/staging 은 mirror(updated_at 부재가 실확인됐으므로 가장 정합). 대안: 양쪽 크롤 유지 + `update_cols` 허용목록.
6. **upload-staging** — `~/.hwax` 유지·이관 제외(권고) vs HEAX 런처 바인드 추가.
7. **타 리포 수리 8건** — MTW catalog 23개 절대경로 env 화 + `.mcp.json` 라이브 DB 지정 · MXWP `update.sh:188 --all` 제거 + `MEILI_DB_PATH` · SF crawler `/reports` 바인드 + `reports/`·`audit/` 산출물 추적 해제(248+9) · PaperIngest `/data/corpus` 바인드 · HEAX 런처 `HEAX_APP_DATA_ROOT`(D2 선행) · **HEAX `deploy/apptainer/start.sh` worker/backend 로그 `>`→`>>`** · **AIDH `start_api.sh` uvicorn 로그 `>`→`>>`** · HEAX Caddy 로그 `roll` 설정.
8. **삭제 확인** — HEAX `dev2.db` 84M(참조 0) · `.pre-*` 924M(아카이브 후) · 0바이트 materialtwin.db · AIDH 미참조 SIF 2개 246M · AIDH logs 안 393M 덤프 · MXWP `.env.bak` · 포털 루트 stale `.env` · `a.txt` · crontab 1·24행 · Drive 고아 채널.
9. **`/data/backups` 잔재**(cluster_setup 2.6G·dpkg.*) 이동 여부·소유자.
10. **SmartTwinMCP 유닛 `/data` 절대경로** — NFS 전환 시 `<hostname>/` 하위 vs 노드 로컬.
11. **RA 블루-그린 시점·green DB 위치**(같은 PG14 클러스터 DB 추가 vs `/data/pg/reportarchive`).
12. **PAT store Postgres 이관(plan 4.2) 시점** — D1 과 합칠지 분리할지(이 계획은 분리).
13. STE ste.db 백업 채널 · `/srv/ste/munge.key` 처리(별 박스).
14. ExpertAgents/knowledge·ExpertGrounding git remote 부여(dev 유일본).
15. cae00 `var/app_data` 정리(이미 시드된 `.pre-*`·0바이트 db·origin.json) 를 D6 전에.
16. AIDH `:8001` 무인증 — prod 편입 전 화이트리스트/키.
17. HF 모델 캐시 `/data/models/hf` 이동 여부(선택, 10G 미만).

## 13. 범위 밖

cluster-deploy 의 versions/current 스테이징(SIF·dist·venv), 시뮬 데이터 파이프라인(`/data/sim`), RA `upload_dir_path`
→ `/data/reports` 샤딩(plan §12), DB 스트리밍 복제, STE 헤드노드 데이터, `/data/paper_patent_corpus` 본체.
