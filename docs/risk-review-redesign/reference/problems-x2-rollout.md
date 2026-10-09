# 문제 사냥 X2 — 배포·이행 중간 상태 (2026-10-09)

대상은 일곱 설계서의 4절(커밋 단위 작업 순서)과 spec-wp5a-ops.md 이고, 04-contract.md 가 설계서 본문보다 우선한다.
근거의 파일·줄은 직접 열어 확인한 것만 적는다. 추측은 추측이라고 적는다.
찾는 대로 아래에 덧붙인다.

## X2-01 [major] 이행이 한 번이라도 실패하면 45초마다 DB 전체 사본이 하나씩 쌓인다

- 근거(코드). `HWAXRisk/backend/app/risk_store.py:623-624` — `migrate()` 는 `_existed and current < latest` 이면 **이행을 시도하기 전에** `pre-migrate-<초>` 로 DB 전체를 복사한다. 실패하면 사본은 남고 버전은 그대로다(:639-641). `prune_backups`(WP5a 3.2.5)는 'migrate() 끝' 과 유지 틱에서만 불려 실패 경로에서는 돌지 않는다.
- 근거(코드). `HEAXHub/backend/app/workers/celery_app.py` 의 `reconcile-integrations-every-45s` 가 `integration_launcher.launch` 를 **횟수 상한 없이** 다시 부른다(`integration_tasks.py:96-150`). 매니페스트의 `restart_policy.max_attempts: 3` 은 이 경로가 읽지 않는다(`service_manager.py:322` 만 읽는다).
- 재현(임시 디렉터리, 리포 import 만). v2 DB 에 실패하는 v3 를 물려 `migrate()` 를 세 번 부르면 `pre-migrate-*` 가 셋 남고 `user_version` 은 2 그대로다.
- 결과. WP5a 3.2.6 의 추정대로 DB 가 GB 급이 된 뒤의 v5·v6 이행이 그 박스에서만 실패하면(디스크 부족·`database is locked`·그 박스 데이터에만 걸리는 인덱스) 분당 GB 가 쌓여 `/data` 를 같이 쓰는 전 서비스가 선다. 사본 이름에 출발 버전이 없어, 디스크를 비우려는 사람이 가장 오래된 것(유일하게 옛 SIF 와 맞는 사본)부터 지운다.
- `shutil.copy2` 의 `OSError`(디스크 부족)는 `sqlite3.Error` 가 아니라 잡히지 않는다 — 반쯤 쓴 사본을 남기고 죽는다.
- 고치는 법(WP5a R3 에 넣는다 — R3 를 WP1 S2 보다 **앞** 걸음으로 못 박는다).
  1. 사본 이름을 `pre-migrate-v<current>-<ts>` 로 바꾸고, 같은 출발 버전의 **완성된** 사본이 이미 있으면 다시 만들지 않는다(`.tmp` 로 쓰고 `os.replace`).
  2. 복사 전에 여유 공간 ≥ DB 크기 × 1.2 를 본다. 모자라면 복사도 이행도 하지 않고 사유를 말하며 기동을 막는다.
  3. `prune_backups` 를 사본을 만들기 **전에도** 부르되, 출발 버전이 현재 DB 버전과 같은 사본은 지우지 않는다.
  4. R3 의 시험에 '실패하는 이행을 세 번 돌려도 사본은 하나' 를 더한다.

## X2-02 [major] v3 가 첫 `ADD COLUMN` 이행이다 — 겹쳐 뜬 둘째 프로세스가 `duplicate column name` 으로 죽고, 그 전에 사본을 한 번 더 뜬다

- 근거(코드). `risk_store.py:615` 가 버전을 읽은 뒤 :631 의 `BEGIN`(deferred)까지 잠금이 없다. v1·v2 는 `CREATE … IF NOT EXISTS` 뿐이라 두 번 돌아도 무해했다. v3(WP1 S2)·v4 는 `ALTER TABLE … ADD COLUMN` 이 들어간다(계약 C-2).
- 근거(코드). 허브는 기동 뒤 20초 안에 헬스가 안 오면 상태만 적고 넘어가고(`integration_launcher.py:89`·`:637-650`), 다음 45초 틱에 `_is_healthy` 가 거짓이면 같은 인스턴스에 서버를 하나 더 `exec` 한다(`:478-486` 를 지나 `:611-`). 리스크 앱의 기동은 `migrate()` 의 전체 복사를 포함하므로 DB 가 커질수록 이 창에 든다.
- 재현(임시 디렉터리). 둘째 연결이 `current=2` 를 읽은 뒤 첫째가 v3 를 끝내면 둘째는 `OperationalError: duplicate column name` → `AppError E300` 이다.
- 결과. 둘째는 죽고 첫째는 산다(데이터는 안 깨진다). 다만 둘째도 `pre-migrate` 사본을 따로 뜨고(초가 같으면 같은 파일에 둘이 쓴다), `integration_hwax_risk.log` 에 '마이그레이션 v3 실패' 가 찍혀 운영자가 실패로 읽는다. WP5a R2 의 러너 잠금은 `migrate()` 를 감싸지 않는다(3.3.7 — 잠금은 `RiskRunner.start()` 에서 쥔다).
- 고치는 법(WP1 S2 의 `risk_store.py` 변경에 같이 넣는다 — v3 가 나가는 바로 그 커밋).
  1. `migrate()` 의 버전별 트랜잭션을 `BEGIN IMMEDIATE` 로 열고 **그 안에서** `PRAGMA user_version` 을 다시 읽어 이미 적용됐으면 건너뛴다.
  2. 사본·이행 전체를 데이터 디렉터리의 `migrate.lock`(flock, 기다린다)으로 감싼다. R2 의 `runner.lock` 과 다른 파일이다(이행은 기다려야 하고 러너는 기다리지 않는다).
  3. `tests/test_store.py` 에 '연결 둘이 같은 v2 DB 를 겹쳐 올린다 → 둘 다 성공·사본 하나' 를 더한다.

## X2-03 [major] 되돌리기 L3 의 전제가 틀렸다 — 스키마 버전이 같은 옛 SIF 는 기동을 거부하지 않고 새 흐름의 잡을 패널 잡으로 집는다

- 근거(설계). WP5a 3.2.5 L3 — '옛 코드는 버전이 높은 DB 에서 기동을 거부하므로'. 계약 C-2 는 새 흐름 전부를 v4 한 블록에 싣고 '새 흐름 첫 커밋' 에 넣는다. 그 뒤 수십 커밋(WP2 3~12 · WP3b 1~12 · WP4 1~14 · WP5a R5~R11)이 전부 v4 다.
- 근거(코드). 지금 `claim_next_job`(`runner.py:724-727`)은 `state IN ('queued','running','cancelling')` 만 보고 `mode` 를 모른다. `recover_running_panels`(:783-791)는 `running` 잡 전부를 `queued`·`paused` 로 돌린다. `mode` 로 거르는 수정은 WP3b 걸음 3 이다.
- 결과. v4 는 알지만 걸음 3 이전인 SIF(예 — WP2 만 든 판)로 되돌리면 기동은 되고, `mode='reviews'|'post'|'synth'` 잡을 Tier 패널 잡으로 집어 `flow='cells'` 타깃에 커버리지 패널을 편성한다(전원 포함 로스터라 ECAD 없는 회로 전문가까지 앉는다). 조용히 틀리게 도는 경우다.
- 같은 뿌리. WP2 걸음 9 가 `POST /targets` 본문의 `flow='cells'` 를 받기 시작하는데, 그 타깃에 Tier 잡을 막는 409·422(`target_in_review_flow`·`flow_mismatch`)는 WP3b 걸음 3·WP4 걸음 12·WP5a R6 에 있다. WP2 만 나간 판에서는 cells 타깃에 옛 패널 흐름이 그대로 돈다.
- 고치는 법.
  1. v4 DDL 커밋(WP5a R4)에 문지기 셋을 **같이** 넣는다 — (가) `claim_next_job`·`recover_running_panels`·`coverage_payload` 의 `mode` 필터(WP3b 걸음 3 을 R4 로 당긴다) (나) cells 타깃의 Tier 잡 거절 (다) `HWAXRISK_REVIEW_ENABLED=0` 이면 `flow='cells'` 타깃 생성 거절(409 `review_disabled`). 그러면 'v4 를 여는 SIF 는 전부 문지기를 안다' 가 성립한다.
  2. WP5a 3.2.5 의 L3 줄을 고친다 — '같은 버전 안의 옛 SIF 로는 되돌리지 않는다. 되돌릴 수 있는 SIF 는 v4 문지기 커밋 이후 것뿐이다'. 절차서에 그 커밋 해시를 적는다.
  3. WP5b C0 의 얼린 옛 타깃 시험에 'reviews 잡이 있는 DB 에서 패널 러너가 그 잡을 집지 않는다' 를 R4 와 같은 커밋으로 넣는다.

## X2-04 [major] 비우기(drain)가 '배포 창을 반드시 연다' 는 약속을 지키지 못한다 — 넷이 겹친다

WP5a 3.5.3 의 1f 절과 `_hwax_drain_finish` 를 실제 스크립트에 대 본 결과다.

1. **미룸 판정의 재료가 틀렸다.** WP5a 는 `DEFERRED_ANY` 를 '`_DA_RC`·`_us_rc` 3 과 `DEFERRED_RESTART`' 에서 만든다고 적었다. 그런데 `deploy-all-from-drive.sh:584` 의 종료코드 3 은 **git 갱신 실패**(`_stale`)이고, 심의 때문에 포털·nginx 를 미룬 것은 블록 안의 `_prc=3`(:253)으로 끝나 스크립트 종료코드에 닿지 않는다(0 이다). `update-all.sh:539-541` 도 `_DA_RC=3` 을 '소스 갱신 실패' 로 읽는다. 그대로 구현하면 포털·nginx·heax(리스크 앱)만 미룬 실행은 깃발을 **내리고**, git 이 한 번 삐끗한 실행은 깃발을 **한 시간 세운다**. 둘 다 반대다. 미룸의 정본은 장부(`HWAX_SKIP_LEDGER`)의 '… 재기동 건너뜀' 줄이다.
2. **깃발 수명(1,800초)이 update-all 한 번보다 짧다.** 1f 는 §2 앞에서 한 번 세우고 다시 세우지 않는다. §2(Drive 에서 SIF·app-data 를 받는다 — `dist-from-drive.sh` 주석이 '~2MB/s')·2c(상한 900초)·2d(240초)를 지나 §4 에 닿기 전에 수명이 끝나면, 앱이 새 쟁점 패널을 시작하고 §4 는 그 패널을 보고 에이전트 서버를 미룬다. 리스크 앱 SIF 가 바뀐 실행일수록 §2 가 길다.
3. **남기는 시간(3,600초)이 패널 하나보다 짧다.** 쟁점 패널은 패널 벽시계 43,200초를 그대로 쓰고(WP4 3.14) 타깃당 24건(상한 48)이 이어서 돈다(WP4 `HWAXRISK_ISSUE_PANEL_CAP`). 도는 패널이 한 시간 넘게 남았으면 깃발이 먼저 풀리고, 패널이 끝나는 순간 다음 패널이 시작된다. 사람이 다시 돌린 update-all 은 또 '심의 진행 중' 을 본다. S5 가 도는 며칠 동안 포털·nginx·허브·에이전트 서버·게이트웨이 재프로비저닝이 **기본 동작으로는** 열리지 않는다. 브리프의 '며칠씩 걸려 운영(배포)을 막으면 안 된다' 와 부딪친다.
4. **옛 흐름 사용자는 왜 멈췄는지 볼 길이 없다.** WP5a 3.5.2 는 `claim_next_job`(패널)도 깃발을 보게 한다. 사유는 새 진행 응답 `GET /targets/{key}/review` 의 `waiting` 에만 실린다. 옛 흐름 타깃의 진행판(`coverage_payload`)에는 자리가 없어, `--hold` 를 내리지 않은 박스에서 Tier 잡이 `queued` 인 채 사유 없이 선다.

- 그 밖. 절 이름 '1f' 는 이미 있다(`update-all.sh:459` — ARP 연결. 1g 도 있다). 끝맺음은 `hwax_skip_summary` 와 `rm -f "$HWAX_SKIP_LEDGER"`(:2358-2359) **앞**에서 불러야 장부를 읽을 수 있다.
- 고치는 법(WP5a P1 에 넣는다).
  1. `DEFERRED_ANY` 를 장부에서 만든다 — `_delib_hold`·`restart_svc`·§5 가 미룰 때 `hwax_skip_record` 와 함께 `"$HWAX_SKIP_LEDGER.deferred"` 에 한 줄을 더하고 끝맺음이 그 파일의 유무를 본다. `_DA_RC` 는 쓰지 않는다. 시험에 'git 실패(rc 3)만 있는 실행은 깃발을 내린다 · 포털만 미룬 실행은 남긴다' 를 넣는다.
  2. `hr()` 가 § 머리마다 `HWAX_DRAIN_RAISED=1` 이면 `hwax_drain on` 을 다시 부른다(수명 갱신). 한 줄이다.
  3. 미룬 재기동이 있을 때의 남김을 시간이 아니라 조건으로 한다 — `/drain` 에 `until_idle: true`(= `delib_active + delib_queued` 가 0 이 된 뒤 `grace_s` 동안 유지, 상한은 패널 벽시계 43,200초)를 더하고 `_hwax_drain_finish` 가 그것을 쓴다. `HWAX_DRAIN_HOLD_S` 는 `grace_s` 의 기본(1,800)이 된다. A1 의 `DrainState.set` 과 시험에 같이 넣는다.
  4. 절차서 `review-ops.md` ④ 에 'S5 가 도는 중의 배포' 를 따로 적는다 — `review-drain.sh status` 로 도는 패널의 남은 시간을 보고, 끝난 뒤 깃발이 살아 있는 동안 update-all 을 다시 돌린다.
  5. `coverage_payload` 의 `job` 에 `waiting{reason:'draining', by, until}` 을 더한다(R6 — 옛 흐름 화면이 읽는 응답이다).
  6. 새 절의 이름은 '1h' 로 한다.

## X2-05 [major] 판이 섞였을 때의 문지기가 `run` 의 첫 프레임과 `/health.capabilities` 둘뿐이다 — 단발 JSON 셋과 뒤에 더해지는 호출 종류는 '보류' 가 아니라 '실패' 로 떨어진다

- 근거(설계). 섞인 판을 다루는 것은 WP5a 3.9.2 하나다(`hello` 프레임·`capabilities`·`agent_outdated`·`portal_outdated`). WP3a·WP3b·WP4 본문에는 이 낱말이 한 번도 없다(grep 0건). 계약 C-12·C-13·C-25 도 `hello` 와 종류별 능력을 정하지 않았다.
- 근거(순서). 실행의 첫 호출은 `run` 이 아니라 `GET limits` → `POST pack` → `POST plan` 이다(WP3b 3.6.1 — S0b 가 셀보다 먼저다). 이 셋은 SSE 가 아니라 `hello` 가 없다.
- 근거(코드). 옛 포털은 모르는 `/agent/…` GET 에 JSON 404(`HWAXPortal/backend/app/main.py:277-278`), POST 에 405 를 낸다. WP3b 3.6.2 의 표는 404 를 팩의 `agent_not_found`(infra 아님·재시도 안 함)로 읽고 405 는 줄이 없다.
- 근거(순서). cae00 의 update-all 한 번은 포털(§2, git) → 리스크 앱(§2, Drive SIF) → 에이전트 서버(§4, git) 순서이고 포털·에이전트 서버는 심의가 돌면 각각 따로 미뤄진다(`deploy-all-from-drive.sh:242`, `update-sites.sh:207-214`). 묻는 시각이 달라 '새 앱 + 옛 포털 + 새 에이전트 서버' 가 다음 update-all 까지 남을 수 있다. 이때 `capabilities` 는 참이라 호출이 나간다.
- 결과 ①. 옛 포털이 POST 에 404 를 내는 구성(SPA 를 내지 않는 포털)에서는 전 전문가의 팩이 `agent_not_found`(재시도 안 함)로 닫히고, 405 를 내는 구성(cae00 — SPA 를 낸다)에서는 표에 없는 갈래라 구현자가 고르는 대로 간다(`EngineError` 면 내용 실패로 차감된다). 어느 쪽이든 '보류하고 스스로 다시 잰다' 가 아니라서, 포털을 올린 뒤 사람이 전문가마다 '다시' 를 눌러야 한다.
- 결과 ②. WP4 걸음 13 이 `card_review.py` 에 호출 종류를 더한다(`hunt`·`summary` — `cross` 는 C-13 의 다섯에 들어 있다. WP4 3.11.3). 그 판의 앱이 WP3a 판 에이전트 서버를 만나면 `capabilities=['card_review']` 는 참이고 요청은 422 `bad_request` → `invalid_request`(재시도 안 함)다. 교차·사냥·요약 칸이 내용 실패로 닫힌다. 게다가 이 창은 **심사 자신이 연다** — S5 의 쟁점 패널이 `delib_active` 를 올려 에이전트 서버 재기동을 미루게 하고, 패널이 끝나면 곧바로 `synth` 가 옛 서버에 `summary` 를 보낸다.
- 고치는 법.
  1. 계약에 한 줄을 더한다 — 네 엔드포인트 어디서든 **404·405·501 과 JSON 이 아닌 본문**은 `review_unsupported`(부류 config, 차감 없음, 실행을 `portal_outdated`·`agent_outdated` 로 보류하고 300초마다 다시 잰다)다. `agent_not_found` 는 상태 코드가 아니라 본문의 `code` 로만 읽는다. WP3b 걸음 7 의 표와 `tests/test_engine_client.py` 에 줄을 더한다.
  2. `GET /card-review/limits` 응답과 `/health.card_review` 에 `rev` 와 `kinds: [...]` 를 싣는다(WP3a 걸음 7). 앱은 단계마다 필요한 종류(S1 `sweep` · S2 `verdict`·`offcard`·`noinput` · S4 `cross`·`hunt` · S6 `summary`)가 `kinds` 에 있을 때만 그 단계의 항목을 집고, 없으면 `agent_outdated` 로 보류한다(WP5a R6 의 `advance`). 422 의 `code='unknown_kind'` 도 같은 보류로 옮긴다.
  3. `hello` 를 계약에 올리거나(WP3a 걸음 5·7 의 프레임 목록에 더한다) 버린다. 지금은 WP5a R6 만 `hello` 를 기다리고 WP3a 3.7 의 프레임 목록(`status·ping·result·error·done`)에는 없다 — A3 의 시험이 빠지면 모든 `run` 이 `review_unsupported` 가 된다.
  4. WP5a 5.3 의 가짜 엔진 시나리오에 '포털만 옛 판'(limits 404) · '종류 하나만 모르는 에이전트 서버' 를 더한다.

### X2-01·X2-02 덧붙임 — 둘이 겹치면 수렴하지 않는다(산수는 추정)

- 근거(코드). uvicorn 은 lifespan 시작(= `migrate()` 포함, `HWAXRisk/backend/app/main.py:113`)을 **포트를 묶기 전에** 돈다. 그래서 겹쳐 뜬 서버는 포트 충돌로 죽기 전에 사본을 뜨고 이행을 시도한다. 허브는 헬스가 안 온 프로세스를 죽이지 않고 다음 틱에 하나를 더 띄운다(`integration_launcher.py:478-486` — `already_running` 조건에 헬스가 들어 있다).
- 추정. 사본 하나에 걸리는 시간 T 가 45초를 넘는 순간(디스크 100MB/s 면 DB 약 4.5GB, NFS 45MB/s 면 약 2GB)부터 틱마다 프로세스가 하나씩 늘고 각자 전체 사본을 뜬다. 사본끼리 디스크를 나눠 쓰므로 T 가 더 길어진다. 이행이 걸린 기동(`current < latest`)에서만 난다 — 즉 **DB 가 커진 뒤의 v5·v6 배포 날**이다. WP3b 3.14 의 추정이 타깃 50개에 2~3GB 다.
- X2-02 의 `migrate.lock`(기다리는 flock)과 X2-01 의 '같은 출발 버전 사본은 한 번' 이 같이 있어야 막힌다. 둘 중 하나만으로는 안 된다.
- 계획서에 옮길 한 줄. **R3 를 '이행 안전 묶음' 으로 넓혀 WP1 S2 앞에 둔다** — 사본 이름·한 번·여유 공간·`migrate.lock`·`BEGIN IMMEDIATE` 안 재확인·버전별 DDL 해시.

## X2-06 [major] 리스크 앱이 cae00 에 닿는 길이 어느 4절·절차서에도 없고, 어느 판이 떠 있는지 말해 주는 것도 없다

- 근거(코드). cae00 의 리스크 앱은 git 이 아니라 Drive 의 SIF 로 온다 — `HEAXHub/deploy/apptainer/dist-from-drive.sh` 끝의 'per-app SIFs → var/sifs/'. 그 SIF 는 dev 에서 `HWAXPortal/infra/scripts/build-all-to-drive.sh` 의 heax 블록(:76-87 — `dist-to-drive.sh` · `appdata-to-drive.sh`)이 올린다. `dist-to-drive.sh` 는 `var/sifs/<slug>.sif` 를 **있는 그대로** 싣는다(스캔이 아직 안 돌았거나 빌드가 실패했으면 옛 SIF 가 간다).
- 근거(설계). 일곱 설계서의 4절과 WP5a 3.12 의 절차서 목차 어디에도 `build-all-to-drive`·`dist-to-drive` 가 없다(grep 0건). 적힌 것은 dev 의 '인스턴스를 내리고 다시 올린다' 와 cae00 의 'update-all 이 허브째 내렸다 올린다' 뿐이다.
- 근거(코드). `HWAXRisk/backend/app/config.py:20` — `APP_VERSION = "0.1.0"` 고정이고 빌드 커밋을 싣는 자리가 없다. `/api/health` 로 가를 수 있는 것은 `schema_version` 하나다. 새 흐름의 수십 커밋이 전부 v4 라(계약 C-2) 그 사이의 판은 구별되지 않는다. update-all §6 헬스게이트는 리스크 앱을 묻지 않는다(`update-all.sh` 에 `hwax_risk` 는 §5 의 위임 점검 세 줄뿐이다).
- 결과. ① Drive 올리기를 빠뜨리면 cae00 은 새 포털·새 에이전트 서버·새 JS 에 **옛 리스크 앱**으로 초록 완주한다. ② 설계서들이 적은 '배포 순서 권고'(WP1 4.4 · WP5a 4절 끝)는 cae00 에서 고를 수 없다 — update-all 한 번의 순서는 포털 → 리스크 앱 → AIDataHub → 에이전트 서버로 고정이고, 리스크 앱의 판은 'dev 가 마지막으로 올린 SIF' 다. ③ 등록 사본 매니페스트가 SIF 지문에 들어간다(`integration_sif_builder.py:279` — `sha256(commit + manifest_json + template)`). H1 을 dev 빌드보다 늦게 넣으면 cae00 의 스캔이 '지문 불일치' 로 재빌드를 시도한다. ④ `appdata-to-drive.sh` 가 dev 의 `risk_review.db` 를 통째로 싣는다 — 카드 묶음·호출 원문이 쌓이면 GB 다. cae00 은 update-all 마다 그것을 받아 풀고, 병합은 하지 않고(`_materialtwin_merge.py` 는 그 표를 모른다) 라이브 DB 를 `pre-merge` 로 한 번 복사한다(`appdata-merge-from-drive.sh:35`).
- 고치는 법.
  1. WP5a P4 의 `review-ops.md` 와 각 설계서 4절의 '반영' 문단에 **cae00 반영 순서**를 박는다 — (가) HWAXRisk push (나) dev: `redeploy-app.sh hwax-risk --rebuild` 로 그 커밋의 SIF 를 굽고 띄운 뒤 `/apps/hwax_risk/api/health` 확인 (다) dev: `build-all-to-drive.sh heax` (라) cae00: update-all (마) cae00: `/apps/hwax_risk/api/health` 의 `build`·`schema_version`·`capabilities` 대조.
  2. WP5a R5 에 넣는다 — `/api/health` 에 `build`(SIF 빌드 훅 `backend/scripts/heaxhub-build.sh` 가 `git rev-parse --short HEAD` 를 `app/_build.txt` 로 적는다. 못 읽으면 `unknown`)와 `capabilities`(예 `result_presave`·`units`·`cells`·`issues`·`synth` — 꾸러미가 붙을 때 그 커밋이 더한다)를 싣는다. 에이전트 서버의 `capabilities` 와 짝이다.
  3. WP5a P1 에 넣는다 — update-all §6 에 리스크 앱 한 줄(`/apps/hwax_risk/api/health` 가 200 이 아니면 `fail`, 200 이면 `build`·`schema_version` 을 찍는다).
  4. '배포 순서' 문장을 고친다 — cae00 에서 순서를 고르는 손잡이는 **Drive 에 SIF 를 언제 올리느냐** 하나다. 에이전트 서버·포털을 먼저 올리려면 SIF 를 올리기 전에 update-all 을 한 번 돈다.
  5. (HEAXHub, 선택) `appdata-to-drive.sh` 에서 `hwax_risk/` 를 뺀다 — 병합되지 않는 DB 를 매번 GB 씩 나르지 않는다. 첫 배포 씨앗이 필요하면 `GET /api/export` 로 옮긴다.

## X2-07 [major] 되돌리기 L1·L3 가 적힌 대로 되지 않는다 — 박스별 값이 닿는 길과 옛 SIF 의 자리

- L1(기능 끄기 — WP5a 3.2.5 '앱 재기동 한 번').
  - 근거(코드). 박스별 값은 HEAXHub `.env` 의 `APPTAINERENV_HWAXRISK_*` 로만 줄 수 있다(WP5a 3.8.2). 런처는 **띄우는 프로세스의 `os.environ`** 에서 그 값을 싣는다(`apt_runner.py:213-220`·`:292`). `redeploy-app.sh` 는 `.env` 를 소싱하지만(:24-26) 45초 재조정을 도는 celery 워커는 허브를 띄울 때의 값을 쥐고 있다.
  - 결과. `.env` 를 0 으로 고치고 `redeploy-app.sh hwax-risk` 만 돌리면 그 인스턴스는 꺼진 채 뜬다. 그 뒤 워커가 그 앱을 다시 띄우는 순간(헬스 탐침 실패·크래시) 워커의 옛 값(1)으로 **조용히 다시 켜진다.** 확실히 끄려면 허브 전체를 재기동해야 하고, 그것은 WP5a P2 가 넣는 심의 보호에 막힌다. `tests/test_manifest.py:65-67` 의 주석이 같은 이유로 '`.env` 는 대안이 못 된다' 고 적어 두었다. 켜는 쪽(시범)도 같은 길이라, 값이 빠진 재기동에서 도는 실행이 `disabled` 로 선다.
  - WP2 3.13·WP3b 3.13·WP4 3.14 는 '손잡이는 매니페스트 `launch.env` 에 적는다' 고 하고 WP5a 3.8.2 는 '박지 않는다' 고 한다. 매니페스트는 두 박스가 같은 파일이고(등록 사본과 `diff` 0) SIF 지문에 들어가므로 박스별 스위치의 자리가 못 된다. 계약에 결론이 없다.
- L3(옛 SIF 로).
  - 근거(코드). `dist-from-drive.sh` 의 `_install_if_changed` 는 `cp -p` 로 덮어쓴다. 앞 판 SIF 는 박스에 남지 않는다. Drive 의 `dist-<ts>` 에서 손으로 찾아 와야 한다.
- 고치는 법.
  1. 기능 스위치를 env 가 아니라 **데이터 디렉터리의 상태**로 둔다 — `PUT /api/meta/review {"enabled": bool, "reason"}`(관리자, `rr_audit` 한 행)가 **DB 의 살림 표**에 적고, 러너와 라우트는 매 틱·매 요청 그 값을 읽는다. 데이터 디렉터리의 낱 파일로 두면 안 된다 — `appdata-merge-from-drive.sh` 의 비-DB 시드 루프(:48-54)가 라이브에 없는 파일을 dev 것으로 심어, dev 에서 켠 스위치가 cae00 을 켠다(같은 이유로 WP5a 의 `runner.lock` 도 dev 의 pid 가 적힌 채 건너갈 수 있다 — 잠금은 fd 라 무해하지만 `holder()` 가 읽는 글은 믿지 않는다). `HWAXRISK_REVIEW_ENABLED` 는 그 값이 없을 때의 기본값으로만 쓴다. 재기동이 필요 없고 박스마다 따로이며 어느 프로세스가 띄워도 같다. WP5a R5(설정)·R7(라우트)에 넣고 R11 은 '코드 기본값 뒤집기' 그대로 둔다.
  2. 계약에 한 줄 — 새 손잡이는 `launch.env` 에 넣지 않는다(WP2·WP3b·WP4 의 문장을 고친다. `test_manifest.py` 의 두 키 고정은 그대로다).
  3. (HEAXHub) `_install_if_changed` 가 앱 SIF 를 덮기 전에 앞 판을 `<slug>.sif.prev`(+`.hash.prev`)로 하나 남긴다. 절차서 ⑥ 에 L3 의 명령 네 줄(앞 판 SIF 복원 · `pre-migrate-v<N>` 복원 · `redeploy-app.sh` · 헬스 확인)을 적는다.

## X2-08 [major] WP5a P2 의 heax 물음을 적힌 대로 넣으면 '심의 중이라 미룸' 이 '배포 실패' 가 된다

- 근거(코드). heax 블록의 끝은 `… ) && ok "heax up" || skip "heax failed (see the log lines above)"` 다(`deploy-all-from-drive.sh:337`). `skip` 은 실패 장부에 적고(:179) 스크립트는 `exit 4` 로 끝나며(:585), update-all 은 그것을 `fail "deploy-all 에서 배포 항목이 skip/실패했다"` 로 받아 끝에 `exit 1` 을 낸다(`update-all.sh:543-545`, `:2371`).
- 근거(설계). WP5a 3.5.3 의 삽입문은 `if _delib_hold …; then exit 3; fi` 다. 포털 블록은 같은 `exit 3` 을 `|| _prc=$?` 와 `case … 3) ;;` 로 받는데(:251-253) heax 블록에는 그 갈래가 없다. P2 의 검증은 '물음이 `dist-from-drive` 줄보다 앞인지를 소스에서 본다' 뿐이라 이것을 잡지 못한다.
- 결과. P2 가 나간 뒤로는 심의가 하나라도 도는 동안의 update-all 이 전부 `✗ 핵심 체인 실패` 로 끝난다. 리스크 심사가 며칠 도는 박스에서는 그것이 평소 상태다 — 늘 켜진 경보가 된다.
- 고치는 법(P2 에 넣는다). heax 블록의 끝을 포털 블록과 같은 꼴로 바꾼다 — `… ) || _hrc=$?` 뒤 `case "${_hrc:-0}" in 0) ok "heax up" ;; 3) ;; *) skip "heax failed …" ;; esac`. 시험은 소스 순서가 아니라 **블록을 떼어 스텁으로 돌려** '심의 중이면 종료코드 0·skip 0건·○ 한 줄' 을 본다(`test_update_all_은_미룬_재기동을_실패로_세지_않는다` 와 같은 방식).

## X2-09 [major] v4 '한 블록' 을 싣는 커밋이 4절 어디에도 없다 — 네 걸음이 각자 DDL 을 더하고, dev 는 push 한 것이 곧 적용된다

- 근거(계약). C-2 — 'v4 = 새 흐름의 표·열 전부를 한 블록으로(새 흐름 첫 커밋). 한 번 push 된 버전의 DDL 은 고치지 않는다'. C-1 — WP2 ∥ WP3a → WP3b → WP4.
- 근거(4절). DDL 을 더하는 걸음이 넷이다 — WP2 걸음 3(`rr_unit_builds`·`rr_units`·`rr_roster.input_gaps_json`. '그 블록이 나가기 전이면 거기에, 나간 뒤면 v4') · WP3b 걸음 1(표 5개. '통합 v3 에 싣는다면 그 커밋') · WP4 걸음 1(표 8개와 열 약 20개. 'WP5 의 판번호') · WP5a R4('새 표 여덟'). 합치면 새 표는 **15개**다(2 + 5 + 8). R4 의 여덟에는 `rr_unit_builds`·`rr_mech_hunts`·`rr_cell_audits`·`rr_issues`·`rr_summaries`·`rr_reports`·`rr_close_acks` 가 없고, 계약이 버린 열(`rr_panels.purpose·turns_gz`, `rr_roster.pack_hash`)이 있다.
- 근거(코드). dev 는 push 마다 5분 스캔이 SIF 를 굽고(`celery_app.py` 의 `scan-integrations-every-5min`), 허브 재기동·박스 재부팅·다른 세션의 `redeploy-app.sh` 때 그 SIF 가 뜬다. 프런트 세션이 같은 리포 main 을 쓴다(브리프). 즉 dev 에서는 **main 에 올린 DDL 이 사람이 정하지 않은 때에 적용된다.** `CREATE TABLE IF NOT EXISTS` 는 이미 있는 표에 아무것도 하지 않으므로, 적용된 뒤 블록을 고치면 그 박스만 조용히 옛 모양으로 남고 시험(빈 DB)은 초록이다.
- 결과. 순서대로(C-1) 구현하면 WP2 가 v4 를 열고, WP3b·WP4 는 '이미 나간 블록' 을 만난다. 그때 블록에 문장을 덧붙이면 v4 를 적용한 박스에 표가 없다(`no such table` — cae00·dev 에서만). 덧붙이지 않으면 v5·v6 가 되어 C-2 의 '한 블록' 이 깨진다. PK·NOT NULL 은 허용 연산으로 고칠 수 없으므로(예 — C-15 의 `variant`, C-23 의 방향 열, C-9 의 `(agent_key, pack_hash)`) 먼저 나간 판이 틀리면 표 이름을 바꿔야 한다.
- 고치는 법. 둘 중 하나를 계획서가 고른다(권고는 가).
  - (가) **R4 를 'v4 통합 DDL 확정' 걸음으로 다시 적고 WP2 걸음 3 앞에 둔다.** 내용은 WP2·WP3b·WP4 의 DDL 을 계약 C-3~C-23 의 이름으로 맞춘 15표 + 열 전부다. WP2 걸음 3·WP3b 걸음 1·WP4 걸음 1 에서는 DDL 을 빼고 반출·폐기·이양 배선과 시험만 남긴다. R4 의 검증에 'PK 가 C-9·C-15·C-23 과 같다' 를 넣는다. 구현하다 모자란 것은 v5 로 더한다.
  - (나) 꾸러미마다 판을 준다(v4 = WP2, v5 = WP3b, v6 = WP4)고 C-2 를 고친다. 표를 그 꾸러미가 구현될 때 굳힐 수 있다. 대가는 이행 세 번(사본 세 번)과 dev↔cae00 반출이 막히는 창 셋이다.
  - 어느 쪽이든 R3 의 '버전별 DDL 해시 고정' 이 **첫 DDL 걸음(WP1 S2)보다 앞**이어야 하고, 적용한 해시를 박스에 남긴다 — `_schema_migrations.app_version` 에 `0.1.0+ddl:<sha8>` 로 적고, 기동 때 코드의 해시와 다르면 `/api/health.warnings` 에 `schema_drift:v<N>` 을 싣는다(dev 가 초안 판을 먹은 것이 보인다).

## X2-10 [major] '기능 기본값 꺼짐' 인 동안에도 옛 흐름이 바뀌는 자리가 넷 있다

C-27 은 시범이 끝날 때까지 기본 꺼짐이라고만 정했다. 꺼진 채로도 도는 코드를 4절에서 골랐다(WP1 의 수리는 의도된 변화라 뺐다).

1. **새 타깃의 로스터 순위(WP2 걸음 8 · 3.10.1).** 순위 질의가 `summary_text` 한 번에서 `units.roster_query` 구절마다 한 번(최대 6회)으로, `RECOMMEND_TOP_K` 가 60 에서 로스터 크기 + 50 으로 바뀐다. 흐름을 가리지 않는다. `rank_in_domain` 이 달라지면 Tier A(영역 1순위 15명)의 사람이 달라진다 — 옛 흐름 패널에 앉는 사람이 바뀐다. WP2 3.10.5 의 '아무것도 자동으로 바뀌지 않는다' 와 어긋난다.
2. **타깃 열기의 시간(WP2 걸음 4 · 3.12).** `create_target` 이 로스터 조회 **앞에** `units.compute` 를 돈다. 이 요청은 nginx `/apps/` 600초 안의 동기 요청이고 로스터 조회의 기한이 540초다(`HWAXRisk/backend/app/config.py:87-91` — '넘겨 듣는 폭 15초를 더해도 600 보다 작아야'). 남는 여유는 45초다. 큰 diff 의 단위 계산이 그보다 길면 빈 504 뒤에 타깃이 생기고 다시 누르면 409 인 사고(cf4f135 가 고친 것)가 돌아온다. 추천 호출이 기한을 먼저 쓰면 뒤 도메인의 `list_agents` 가 `domains_failed` 로 빠져 로스터에 영역이 통째로 없다(`roster.py:162-178`).
3. **`flow='cells'` 타깃(WP2 걸음 9).** 본문의 `flow` 를 받기 시작한다. 검토 실행은 `review_disabled` 로 막히고(WP5a L1) Tier 잡 거절(422 `flow_mismatch`)은 뒤 걸음(WP3b 걸음 3·WP4 걸음 12·WP5a R6)에 있다. 그 사이의 판에서는 전원 포함 로스터(보류 0명) 위에 옛 패널이 돈다 — ECAD 없는 회로 전문가 104명이 입력 결손 처리 없이 패널에 앉는다.
4. **깃발(WP5a R6).** `claim_next_job` 이 비우기를 보므로 옛 흐름 Tier 잡도 update-all 마다 30분~1시간 선다(의도된 것이나 사유가 옛 화면에 없다 — X2-04 의 4).

- 그 밖. 손잡이가 둘이다 — `HWAXRISK_REVIEW_FLOW`(WP2, 새 타깃의 기본 흐름)와 `HWAXRISK_REVIEW_ENABLED`(WP5a). R11 은 뒤의 것만 뒤집는다. 그대로면 '기본 켬' 뒤에도 새 타깃은 `panels` 로 열린다.
- 고치는 법.
  1. WP2 걸음 8 의 구절 질의·top_k 를 `flow=='cells'` 타깃에만 건다. `panels` 타깃은 WP1 뒤의 질의(R-25) 그대로다. 걸음 8 의 검증에 '`panels` 타깃의 `fetch` 호출 인자가 종전과 같다' 를 넣는다.
  2. WP2 걸음 4 — `units.compute` 에 벽시계 상한(예 20초)을 두고, 넘으면 타깃을 먼저 만든 뒤 `rr_unit_builds(status='failed', error='deadline')` 로 남긴다(`POST /targets/{key}/units` 로 다시 만든다). 로스터 기한은 `540 − 단위 계산에 쓴 시간` 으로 넘긴다. `list_agents` 를 추천 호출보다 **먼저** 돈다(명단이 순위보다 중요하다).
  3. WP2 걸음 9 — 기능이 꺼져 있으면 `flow='cells'` 를 409 `review_disabled` 로 거절한다(X2-03 의 문지기와 같은 커밋).
  4. `HWAXRISK_REVIEW_FLOW` 를 없애고 '기능이 켜져 있으면 새 타깃의 기본은 cells' 로 유도한다(본문의 `flow` 로 타깃마다 고를 수는 있다). R11 한 걸음으로 둘 다 바뀐다.

## X2-11 [major] 옛 타깃을 새 흐름으로 넘기는 길이 계약에 없다 — cae00 시범이 기댈 유일한 길인데 꾸러미마다 다르다

- 근거(코드). 타깃 키는 `f"{kind}:{ref_id}"` 이고 있으면 409 다(`HWAXRisk/backend/app/routes.py:2025-2027`). 같은 리비전 쌍에 타깃을 하나 더 열 수 없다. 실제 리비전 쌍은 cae00 에만 있고(브리프) 거기 타깃은 전부 옛 흐름으로 열렸다. C-27 의 '대표 15명 시범' 은 옛 타깃 위에서 돈다.
- 근거(설계). 넘기는 규칙이 셋이다. WP5a 3.2.4 — 검토 실행을 시작하면 `flow` 를 뒤집는다. WP3b 8절 6 — 허용한다, 원장의 종결 행과 `deferred` 행은 그대로 둔다, 격자는 로스터 전원이다. WP2 3.10.1 — `flow` 와 `input_gaps_json` 은 `create_target` 의 로스터 동결 때만 정해지고, 옛 타깃은 사람이 `undefer` 를 부른다(그때 푼 행에만 입력 결손이 적힌다). WP4 3.11.1 — 새 흐름 타깃에 패널 잡은 422 다(넘긴 뒤 되돌아갈 길이 없다).
- 결과. 넘긴 옛 타깃에서 ① 회로 영역 전문가 110명의 `input_gaps_json` 이 NULL 이라 `noinput` 길로 가지 않는다(C-20 과 반대 — ECAD 가 없는데 있는 것처럼 카드 대조를 한다. 영역 1순위 6명은 `undefer` 를 불러도 NULL 이다) ② 104명의 `rr_coverage` 가 `deferred` 로 남아 롤업이 닫히지 않고 WP4 의 '새 흐름에는 deferred 가 없다' 가 깨진다 ③ `close_level` 이 옛 기본(C2)이라 `HWAXRISK_UNITS_CLOSE_LEVEL`(C3)이 걸리지 않는다. 시범의 수치(놓침률·no_input 비율)가 새로 연 타깃과 다르게 나온다.
- 고치는 법(WP2 걸음 9 에 넣고 계약에 한 줄).
  1. `planner.adopt_cells_flow(store, target_key, *, decided_by, reason)` — 한 트랜잭션으로 (가) 살아 있는 잡이 있으면 409 (나) `flow='cells'` (다) 로스터 **전 행**의 `input_gaps_json` 을 동결 규칙으로 다시 채운다(1순위 포함) (라) `deferred(ecad_absent)` 를 `pending` 으로 (마) `close_level` 을 새 흐름 기본으로 (바) `rr_audit(scope='target', action='target.flow')`. 끝에 `units.build_units`.
  2. 길은 `POST /api/targets/{key}/flow {"to":"cells","reason"}`(소유자·관리자, 기능이 켜져 있을 때만) 하나다. 검토 실행 생성은 `panels` 타깃에서 `flow` 를 말없이 뒤집지 않고 409 `flow_not_adopted` 로 이 길을 가리킨다(WP5a 3.2.4 의 그 줄을 고친다).
  3. 시험은 WP5b C0 의 얼린 옛 타깃으로 — 넘긴 뒤 1순위 회로 전문가의 `review_payload.input_gaps == ['ecad_absent']`, `deferred` 0, 옛 패널·의견·등록부 행 수 불변.
  4. 절차서 ② '시범 실행 순서' 에 이 걸음을 적는다.

## 작은 것들

### X2-12 [minor] 비우기 깃발 파일이 에이전트 서버 리포 루트에 생길 수 있다

- 근거(코드). WP5a 3.5.1 의 기본 경로는 `delib_jobs.JOB_DIR.parent / "drain.json"` 이다. `JOB_DIR` 은 `artifacts` 의 실제 경로 옆이라(`HWAXAgentServer/delib_jobs.py:48-52`) `/data` 이관을 안 한 박스에서는 리포 루트다. `.gitignore` 는 `/delib-jobs`·`/artifacts` 만 가린다.
- 고치는 법. A1 에 `.gitignore` 의 `/drain.json` 한 줄을 넣는다.

### X2-13 [minor] 계약 문구 묶음(E5 + P2 + S16)의 '같은 날' 은 push 기준이다 — cae00 에는 세 전송로로 따로 닿는다

- 근거(코드). JS 는 update-all §1·1a 에서 곧바로(`update-all.sh:264-268`), 앱 자산은 Drive 의 SIF 로(§2), 엔진은 §4 에서 심의가 없을 때만 바뀐다. `check_chair_parity.py` 는 dev 의 워킹트리 셋을 볼 뿐 박스의 뜬 판을 보지 않는다.
- 결과. 창 동안 좌석은 엔진의 옛 계약문과 앱이 E0c 로 싣는 새 계약표(`runner.py:313-330`·`:427`)를 같이 받고, `model_json.seat_contract_rev` 는 새 판을 가리킨다. 깨지지는 않는다. 판별로 품질을 견줄 때 그 창의 패널이 섞인다.
- 그 밖. WP5b C1 뒤로는 리스크 리포의 `pytest` 가 형제 리포 워킹트리와 묶인다 — 세 커밋 사이에 다른 세션의 '전체 초록' 이 붉다.
- 고치는 법. WP1 4.4 에 두 줄 — (가) 세 커밋은 한 세션이 E5 → P2 → S16 순서로 이어서 올린다 (나) cae00 에는 S16 이 든 SIF 를 Drive 에 올린 **뒤** update-all 한 번으로 보내고, 에이전트 서버가 미뤄졌으면(○) 그것이 올라올 때까지의 패널을 `chair_rev` 로 가려 본다.

### X2-14 [minor] WP5a 가 적은 '§3 은 새 덤프면 DROP 뒤 복원' 은 지금 코드가 아니다

- 근거(코드). `update-all.sh:591-594` — `merge-from-drive.sh` 로 병합한다('MERGE(비파괴) … DROP 안 함'). 덤프가 같으면 건너뛴다(:589-590).
- 결과. 설계의 결정(묶음을 셀보다 먼저 전부 얼린다)은 그대로 맞다(병합도 `updated_at` 최신 우선으로 카드를 바꾼다). 다만 P4 의 절차서·`server-setup.md` 에 'DROP' 을 옮겨 적으면 틀린 사실이 문서에 남는다. `aidh_unreachable` 보류가 §3 때문에 걸릴 일도 거의 없다.
- 고치는 법. WP5a 2.6·3.3.6 의 그 문장을 '병합한다' 로 고친다.

### X2-15 [minor] 꺼진 기능의 코드가 다른 것을 내릴 수 있는 자리 — 무조건 import 와 새 기동 검사

- 근거(설계). WP3a 걸음 7 은 `app.py` 가 `card_review` 라우터를 한 줄로 붙이고, WP5a A2 는 `review_gate` 를 `app.py` 에 배선한다. 에이전트 서버는 `deliberation`·`thinking` 을 머리에서 import 한다(`HWAXAgentServer/app.py:51`·`:88`) — 같은 자리에 들어가면 새 모듈의 import·초기화 오류가 챗·심의 전체를 내린다. `CARD_REVIEW_TZ` 에 없는 시간대를 적은 박스가 그 예다(WP5a `load_config` 는 숫자만 '경고하고 기본값' 이라고 적었다).
- 근거(설계). WP5a R5 의 `check_review_chain` 과 WP3b 3.13 의 사슬 검사는 **기동을 막는다.** 리스크 앱이 기동을 거부하면 옛 흐름까지 같이 서고 허브가 45초마다 다시 띄운다.
- 고치는 법. (가) A2·WP3a 걸음 7 — 두 모듈의 import 와 관문 초기화를 `try` 로 감싸 실패하면 `capabilities` 에서 빼고 `/health` 에 사유를 싣는다. 시간대가 틀리면 경고하고 기본값으로 돈다. (나) R5 — 검토 사슬이 뒤집힌 박스는 기동을 막지 않고 사전 점검의 `blocking` 과 `/api/health.warnings` 로 말한다(실행 생성만 409).

### X2-16 [minor] C-30 의 'MCP 도구 14 → 18' 은 산수가 안 맞는다

- 근거(4절). WP2 걸음 4 가 `risk_get_units` 로 15, WP3b 걸음 11 이 둘을 더해 17, WP4 걸음 12 가 넷을 더한다 — 21 이다. WP4 3.12.2 도 'WP3 가 더하는 것은 따로다' 라고 적었다.
- 결과. 걸음마다 `tests/test_mcp_tools.py` 의 고정 수와 매니페스트 설명의 수가 다르게 적히고, 절차서의 '게이트웨이 `tools/list` 로 확인' 이 기대할 수가 틀린다.
- 고치는 법. 계약의 수를 '14 → 15(WP2) → 17(WP3b) → 21(WP4)' 로 고치고, 확인은 수가 아니라 이름(`risk_get_units`·`risk_get_cells`·`risk_get_issues`)으로 한다.

## 심각도 정리

- blocker — X2-04(비우기가 배포 창을 열지 못한다. 미룸 판정의 재료가 틀렸고, 기본값으로는 S5 가 도는 며칠 동안 재기동이 열리지 않는다).
- major — X2-01·X2-02(이행 사본·겹친 기동) · X2-03(같은 버전의 옛 SIF·문지기 순서) · X2-05(섞인 판의 문지기) · X2-06(Drive 길·판 식별) · X2-07(L1·L3) · X2-08(P2 의 종료코드) · X2-09(v4 블록) · X2-10(꺼져 있어도 바뀌는 것) · X2-11(옛 타깃 넘기기).
- minor — X2-12 ~ X2-16.

## 빼거나 합칠 것(cuts)

| 무엇 | 왜 | 대신 |
|---|---|---|
| WP3a 걸음 9·P2(엔진 `knowledge_query`·포털 `DelibOpts`) | WP1 E1·P1 과 같은 줄을 고치고 같은 새 시험 파일(`tests/test_knowledge_query_opt.py`)을 만든다. WP1 이 먼저 나간다(C-1) | WP1 것만 남긴다 |
| WP4 걸음 0b·0c | WP1 S1(cycle 대역)·S15(`raised`)와 같은 수리다 | WP1 것만 남기고 WP4 는 0a·0d 만 |
| WP3b 걸음 2(러너 잠금)·걸음 1 의 `busy_timeout` | WP5a R2·R1 과 같은 일이다. 새 파일(`runlock.py`)과 `main.py`·`runner.py` 를 둘이 고친다 | R1·R2 한 벌 |
| WP5a R6·R7 의 `review_runner.py`(새)·셀 REST | WP3b 걸음 6·8·11 이 같은 새 파일과 같은 경로를 만든다. 둘 다 구현하면 검토 루프가 둘이다 | WP3b 가 파일을 만들고 WP5a 는 규약(실패 분류표·보류 코드·봉투)과 시험 뼈대만 준다. 걸음 표를 하나로 합친다 |
| WP3a 걸음 5 의 줄 세우는 관문(`_Gate`·`CARD_REVIEW_MAX_WAITING`·`WAIT_MAX_S`) | C-24 가 '줄을 세우지 않는다' 로 정했다. A1 의 `review_gate` 와 겹친다 | A1 한 벌 |
| WP5a R4 의 '새 표 여덟' 초안 DDL | 실제는 15표이고 PK 셋이 계약과 다르다(X2-09) | 통합 DDL 확정 걸음 |
| `HWAXRISK_REVIEW_FLOW` 손잡이(WP2) | `HWAXRISK_REVIEW_ENABLED` 와 뜻이 겹치고 R11 이 하나만 뒤집는다(X2-10) | 켜짐 여부에서 유도 |
| `DEFERRED_ANY` 를 `_DA_RC` 로 만드는 것(WP5a 3.5.3) | 3 은 git 실패다(X2-04) | 장부 표식 |
| 스위치를 `APPTAINERENV_*`·`launch.env` 로 주는 것 | 워커 환경과 갈리고 매니페스트는 두 박스가 같은 파일이다(X2-07) | DB 살림 표의 스위치 |

## 직접 확인해 맞았던 것(confirmed)

- 이행은 버전 하나가 트랜잭션 하나이고 실패하면 버전·표가 그대로다(임시 DB 로 재현). 코드보다 높은 버전은 사본 없이 기동을 거부한다. v2 → v4 를 한 기동에 올려도 사본은 한 번이다(`risk_store.py:623-624` 가 루프 앞이다).
- `_split_statements` 는 `ALTER … ; -- 주석` 한 줄, 주석 속 쌍점·따옴표를 바르게 나눈다. `ADD COLUMN … NOT NULL DEFAULT 'panels'` 는 행이 있는 표에서 돌고 옛 행은 `panels` 로 읽힌다(임시 DB 로 확인). 계약 C-5 의 `flow`·`mode` 기본값이 옛 타깃·옛 잡을 그대로 옛 흐름에 둔다.
- 반출은 열을 `PRAGMA table_info` 로 읽는다(`export.py:107`) — `ADD COLUMN` 으로 더한 열이 저절로 실린다.
- 파리티 검사기가 보는 것은 `_CHAIR_ITEMS['risk-review']`·`_CHAIR_ADVERSARY['risk-review']`·`_RISK_SEAT_CONTRACT` ↔ JS ↔ 앱 자산의 `contract` 뿐이다. 이것을 건드리는 걸음은 WP1 의 E5·P2·S16 셋뿐이다. `_RISK_KEEP_TOOLS`(E3)·`card_review.py`·택소노미 1.1 은 걸리지 않는다(엔진·JS 는 메커니즘 코드를 나열하지 않는다).
- 게이트웨이는 백엔드마다 60초에 한 번 `list_tools` 지문을 다시 보고 바뀌면 재집계한다(`gateway.py` G3 블록). 새 리스크 도구는 재프로비저닝 없이 뜬다. 이 재설계에 게이트웨이 리포 변경은 없다.
- nginx 는 `/agent/` 전체에 스트리밍 설정과 침묵 한도를 건다(`hwax.conf.tmpl:82-87`). `/agent/card-review/*` 에 conf 변경이 필요 없다.
- JS 파이프라인은 cae00 에서 update-all 1a 가 매번 동기화한다. dev 에서는 손으로 돈다.
- WP1 4.4 의 섞인 상태 표(새 앱 + 옛 포털·옛 엔진, 옛 앱 + 새 엔진)는 코드와 맞는다 — `card:` 참조는 지금 `parse_ref` 가 이미 받는다(`common.py:183-184`).
- WP5a 2.6·2.7 의 사실 — heax 블록에 심의 물음이 없다 · `dist-from-drive` 가 제자리에서 덮는다 · 45초 재조정 · 20초 헬스 대기 · `cp … pre-merge` — 는 전부 코드와 맞는다.
- 에이전트 서버의 재기동 미룸은 `git pull` **뒤에** 묻는다(`update-sites.sh:185`·`:207`). 디스크의 코드는 새것이고 프로세스는 옛것이다. 다만 `deliberation`·`thinking` 은 머리에서 import 돼 있어 늦은 import 로 판이 섞이지는 않는다.
- dev 의 리스크 앱 DB 는 지금 약 1MB 이고 사본이 하나다. X2-01·X2-02 의 수렴 문제는 새 흐름의 자료가 쌓인 뒤의 일이다.

## 확인하지 못한 것(unknowns)

- cae00 의 HEAXHub 스캔이 GitHub 에서 HWAXRisk 를 받아 SIF 를 **스스로** 구울 수 있는지. 된다면 cae00 에서도 'main 에 push = 다음 허브 재기동 때 반영' 이고 update-all 이 문지기가 아니다. `integrations_scanner.py:685-700` 은 '받지 못하면 받아 둔 SIF 로 띄운다' 만 말한다.
- cae00 의 update-all §2 가 실제로 얼마나 걸리는지(깃발 수명 1,800초와의 비교). Drive 속도 '~2MB/s' 는 스크립트 주석의 값이다.
- cae00 에 `risk_review.db` 가 이미 있는지와 크기, 데이터 디렉터리의 파일시스템(flock·복사 속도).
- `recommend_agents` 를 top_k 약 400 으로 여섯 번 부를 때의 시간(X2-10 의 2).
- SIF 안의 uvicorn 판이 dev 가상환경과 같은지(lifespan 이 포트 묶기보다 먼저라는 것은 dev 의 `uvicorn/server.py` 로만 봤다).
- SIF 빌드 훅에서 `.git` 이 보이는지(X2-06 의 `build` 를 훅이 적을 수 있는지). 안 보이면 `APP_VERSION` 을 배포 단위마다 손으로 올리는 수밖에 없다.
- 프런트(다른 세션)가 새 409·422 코드와 `waiting` 을 어떻게 보여 주는지.
- 쟁점 패널 하나가 실제로 몇 시간 도는지(X2-04 의 3 은 벽시계 상한 43,200초와 '20석 넘는 심의는 몇 시간' 이라는 스크립트 주석에 기댔다).

## 총평(verdict)

이행 코드 자체는 원자적이고 옛 타깃·옛 잡은 기본값 덕에 옛 흐름에 그대로 남는다 — 스키마가 자료를 망치는 길은 찾지 못했다. 깨지는 곳은 그 둘레다. 비우기 신호가 적힌 대로는 배포 창을 열지 못하고(미룸 판정 재료가 틀렸고 수명이 패널보다 짧다), heax 물음은 미룸을 배포 실패로 만든다. 섞인 판의 문지기가 `run` 과 `/health` 둘뿐이라 단발 호출과 뒤에 붙는 호출 종류가 보류 대신 실패로 떨어지고, 같은 v4 안의 옛 SIF 와 WP2 만 나간 판에서는 새 흐름의 잡·타깃이 옛 패널 경로로 돈다. 리스크 앱이 cae00 에 닿는 Drive 길·판 식별·박스별 스위치·옛 타깃 넘기기가 어느 절차에도 없어 시범이 기댈 길이 비어 있다. v4 통합 DDL 과 이행 안전 묶음(R3)을 맨 앞에 못 박으면 나머지는 걸음 순서 조정으로 풀린다.
