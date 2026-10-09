# WP5a 설계서 — 횡단(스키마 이행 · 설정 · 배포 · 운영)

기준 커밋은 HWAXRisk `7248651`, HWAXAgentServer `7683125`, HWAXPortal `00d5565` 이다(2026-10-09, dev 워킹트리 clean).
코드의 파일·줄은 직접 열어 확인한 것만 적었다. 입력 자료에서 옮긴 숫자는 '입력 자료' 라고 적었다.
호출 시간·토큰 수는 전부 추정이다(운영 LLM 실측이 없다).

---

## 1. 목적과 범위

새 흐름(전문가 × 검토 단위의 카드 대조 → 쟁점 토의 → 종합)이 dev 와 cae00 에서 **며칠씩** 돌 때, 운영을 막거나 조용히 틀어지지 않게 하는 것이 목적이다.
이 꾸러미가 지키는 문장은 넷이다.

- 배포 한 번이 며칠 돈 심사를 지우지 않는다. 반대로 며칠 도는 심사가 배포를 영영 막지도 않는다.
- 심사가 도는 동안 챗·띵킹·일반 심의가 밀리지 않는다.
- 프로세스가 어디서 죽어도, 다시 뜨면 사람 손 없이 하던 자리에서 이어 돈다(사람이 필요한 멈춤은 사유와 조치를 말한다).
- 건너뛴 것·강등된 것·기다리는 것은 전부 보인다(○ 와 '켜려면').

### 하는 것

| # | 무엇 | 리포 |
|---|---|---|
| 1 | 스키마 v3 의 이행 규약·순서·공존·되돌리기·백업, 그리고 새 표가 반출·폐기·지표·학습·정리에 걸리는 자리 | HWAXRisk |
| 2 | 실행 원장의 운영 열과 상태기계(집기·백오프·보류·자동 재개·차단기·재기동 복구), 프로세스 잠금 | HWAXRisk |
| 3 | LLM 경합 게이트(낮·밤 창, 챗·심의에 양보), `/health` 의 새 계수 | HWAXAgentServer |
| 4 | 비우기 신호(`/drain`)와 update-all·deploy-all 의 배선 | HWAXAgentServer · HWAXPortal |
| 5 | 시간 한도의 층에 새 호출 경로를 끼우는 자리와 사슬 시험 | 세 리포 |
| 6 | 새 손잡이 목록(이름·기본값·읽는 곳·적는 곳), 매니페스트·환경 키트 | 세 리포 · HEAXHub |
| 7 | 사전 점검(박스 차이를 재서 말한다), 진행·실패·토큰 관측, 지표 | HWAXRisk · HWAXAgentServer |
| 8 | 예산 게이트(추정 → 동의 → 상한), 범위 손잡이, 정지·재개 | HWAXRisk |
| 9 | 서버 절차서·시간 한도 표·changelog·CLAUDE.md 문서 표 | HWAXPortal |

### 하지 않는 것

- 검토 단위를 어떻게 나누는가(WP2), 카드 대조의 프롬프트·판정·검증(WP3), 쟁점 토의·종합·완결 판정(WP4). 이 문서는 그 꾸러미들이 **운영 규약을 지키기 위해 가져야 하는 열과 봉투**만 정한다.
- 프런트엔드(다른 세션). 백엔드 응답 계약까지만 적는다.
- ReportArchive·TestScope 리포.
- 사용자가 웹·MCP 로 직접 시작한 심의의 대기 줄이 재기동을 막는 문제(지금도 있는 일이다 — 비우기 신호는 리스크 앱의 자동 작업만 멈춘다).
- LLM 서버 쪽 우선순위 스케줄링(서빙 설정을 확인하지 못했다 — 9절).

---

## 2. 지금 코드

### 2.1 스키마 이행 — `HWAXRisk/backend/app/risk_store.py`

- 버전은 `PRAGMA user_version` 이 정본이고 지금 **2** 다. `MIGRATIONS = [(1, _DDL_V1), (2, _DDL_V2)]`(:562). v2 는 `rr_brief_calls` 하나를 더했다(:547-559).
- 허용 연산은 `CREATE TABLE IF NOT EXISTS` · `ADD COLUMN` · `CREATE INDEX IF NOT EXISTS` 뿐이다(:561 주석). CHECK 어휘 확장은 할 수 없다 — v2 주석이 그 때문에 표를 따로 만들었다고 적는다(:542-546).
- `migrate()`(:608-646) — 버전 하나가 트랜잭션 하나다. 기존 DB 에 적용할 버전이 있으면 직전에 `risk_review.db.pre-migrate-<ts>` 로 **DB 전체를 복사**한다(`_backup_unlocked` :648-653, WAL 체크포인트 뒤 `shutil.copy2`). 사본을 지우는 코드는 없다. DB 버전이 코드보다 높으면 기동을 거부한다(:618-622).
- 연결은 하나이고(`sqlite3.connect(..., check_same_thread=False)` :597) `busy_timeout` 을 주지 않는다(파이썬 기본 5초). 프로세스 안에서는 `RLock` 하나가 전 호출을 직렬화한다(:580, `tx()` :674-699).
- 살림 표 둘(`_schema_migrations` · `_user_credentials`)은 버전 밖이고 반출하지 않는다(:564-570).

### 2.2 새 표를 알아야 하는 자리

| 자리 | 지금 동작 | 줄 |
|---|---|---|
| 반출 표 목록 | `MIGRATIONS` 의 `CREATE TABLE` 문에서 **자동으로** 뽑는다 — 새 표는 저절로 실린다 | `export.py:24-34` |
| 반출 소유자 필터 | `owner_sub` 열이 있으면 그 값으로 거르고, 없으면 공용 표로 본다(들여올 때 병합하지 않는다) | `export.py:178-182`, `:335-337` |
| 반출 과제 필터 | `project_id` 열이 있는 표만 폐기·코퍼스 제외 과제를 뺀다 | `export.py:183-189` |
| since 열 | `_SINCE_COLS` 에 없는 표는 `since` 와 무관하게 전부 싣는다 | `export.py:43-79`, `:190` |
| 들여오기 | 헤더 `schema_version` 이 이 박스와 다르면 409 `schema_mismatch`. 표에 PK 가 없으면 500. 본문 전체를 문자열로 받아 메모리에서 푼다 | `export.py:300-316`, `:338-339` |
| 사람 확정 우선 | 표마다 분기가 손으로 적혀 있다 | `export.py:82-103` |
| 폐기(purge) | 원문 열을 비우는 SQL 이 표마다 손으로 적혀 있다(`PURGE_BLANK_SQL`). 잡은 상태로 걸러 취소하고 커버리지는 `skipped(project_purged)` 로 닫는다 | `routes.py:960-978`, `:1021-1030` |
| 지표 | `rr_metrics.dimension` 은 CHECK 로 여섯(expert·domain·mechanism·pattern·project·global)뿐이다. `recompute` 는 이번 계산에 없는 옛 자리를 지운다(`nightly_%` 만 예외) | `risk_store.py:487`, `metrics.py:1139-1147` |
| 모델 귀속 | finding 의 모델은 `panel_id → rr_panels.model_json.model`, 전문가는 `opinion_id → rr_seat_opinions.agent_key` 로만 붙는다 | `learning.py:181-188`, `metrics.py:466-478`, `:622-623` |
| 야간 잡 | `run_nightly` 는 있지만 **러너가 부르지 않는다.** `_LOOPS` 에 `nightly_loop` 가 있고 `_loop` 본문에는 `panel_loop`·`sync_loop` 분기만 있다 | `runner.py:22`, `:1485-1500`, `nightly.py:500` |

### 2.3 러너·재기동·자격 — `HWAXRisk/backend/app/runner.py` · `engine_client.py` · `config.py`

- `RiskRunner`(:1456) 는 스레드 셋(`panel_loop` 5초 · `sync_loop` 60초 · `nightly_loop` 60초)과 세마포어 `risk_concurrency`(기본 2, `config.py:208`)를 갖는다. 워커 하나가 패널 하나를 돈다(`_panel_tick` :1528-1548).
- `claim_next_job`(:714-760) 은 그 타깃에 `running` 패널이 있으면 건너뛰고(타깃당 직렬), 일일 상한 24 에 걸리면 `paused(daily_cap)` 로 둔다. 잡을 `mode` 로 가르는 열은 없다.
- `rr_jobs.pause_reason` 은 CHECK 로 `diminishing|daily_cap|user` 셋뿐이다(`risk_store.py:290`). 그 밖의 멈춤 사유는 `error` 문자열과 `state_by='code:<사유>'` 에 적는다(`_set_job` :653-667).
- 재기동 복구 `recover_running_panels`(:764-794) — `running` 패널을 `error('restart')` 로 닫고 좌석을 차감 없이 되돌린 뒤 그 타깃의 잡을 **`paused` 로 둔다**(사람이 재개). 까닭은 엔진이 그 심의를 분리 태스크로 끝까지 돌리고 있어, 곧바로 재개하면 같은 좌석으로 두 번째가 겹쳐 돌기 때문이다.
- 차감하지 않는 중단은 `UNCHARGED_CODES`(:57)로 모여 있다 — `panel_timeout`·`engine_silent`·`engine_stream_cut`·`cancelled`·`restart`·`chair_failed`·`engine_busy`·`stopped`.
- 포털 429 는 `EngineBusy` 로 올라와 30초 간격·총 3,600초까지 기다리고(`config.py:67`·`:72`, `runner.py:1031-1066`), 다 쓰면 좌석을 깎지 않고 잡을 멈춘다.
- 자격은 요청자 → 타깃 owner → 서비스 순이다(`resolve_credential_with_note` :258-287). 사용자 PAT 는 남은 수명이 `credential_margin_s`(패널 벽시계 43,200 + 429 예산 3,600 + 600 = **47,400초**)를 넘을 때만 쓴다(`config.py:263-279`). PAT 등록 하한은 86,400초다(`routes.py:36`). 여유가 하한 이상이면 기동을 막는다(`main.py:52-65`).
- 엔진 클라이언트는 포털 `POST /agent/chat` 하나만 안다(`engine_client.py:29`, `:336-415`). 줄 사이 침묵 한도 54,000초(`config.py:65`), 패널 벽시계 43,200초(`config.py:60`)를 앱이 스트림에서 잰다(`_watched` :123-159).
- 앱의 httpx 클라이언트는 `trust_env` 를 건드리지 않는다(리포 전체 grep 0건) — 컨테이너에 프록시 환경변수가 있으면 그것을 탄다.
- `/api/health` 는 `get_store().schema_version()` 을 부른다(`main.py:144-155`) — **저장소 락을 잡는다.**

### 2.4 시간 한도의 층

정본은 `HWAXPortal/docs/change-request-8-10/server-setup.md` §4-8 의 표(14층)와 `docs/delib-engine-feedback/context-notes.md` D-17 이다. 요지만 옮긴다.

- 누적 시간 — LLM 연결 10초 < 시도 1회 1,800초(`DELIB_TIMEOUT_S`) < 논리 호출 3,608초(2 × 1,800 + 8) < 좌석 발언 하나 10,824초(3 × 3,608) < 리스크 패널 벽시계 43,200초 < 자격 여유 47,400초 < PAT 등록 하한 86,400초.
- 침묵 — 엔진 ping 15초(`DELIB_HEARTBEAT_S`) < 포털 릴레이 46,800초 < nginx `/agent/` 50,400초 < 리스크 앱 54,000초.
- 엔진에는 심의 전체 벽시계가 없다(안쪽이 전부 유한하다).
- 다섯 리포의 기본값을 소스에서 읽어 '안쪽 < 바깥' 을 묻는 시험이 이미 있다 — `HWAXPortal/backend/tests/test_time_limit_chain_contract.py`. 읽는 식은 엔진의 `_env_float("이름", 기본값)` 과 리스크 앱 `config.py` 의 상수다.

### 2.5 같은 LLM 을 쓰는 것들 — `HWAXAgentServer`

| 쓰는 것 | LLM 인스턴스 | 동시 상한 | 줄 |
|---|---|---|---|
| 챗(ReAct) | `app.state.llm`(900초·재시도 2, 스트리밍 청크 침묵 300초) | 에이전트 서버에는 없다. 포털 `max_concurrent_chats` 64 뿐이다 | `app.py:345-347`, `start.sh:56`, 포털 `config.py:289` |
| 띵킹 | `app.state.llm`, 좌석당 600초 | `THINK_CONCURRENCY` 4 — **요청마다 새로 만드는 세마포어**라 전역 상한이 아니다 | `thinking.py:49`·`:56`·`:357` |
| 웹 심의·리스크 패널(`/chat` 의 `/심의`) | `delib_llm`(1,800초·재시도 1) | 없다. `_detach_stream` 으로 분리 태스크가 되고 좌석 전원이 라운드마다 한꺼번에 부른다. 리스크 러너의 패널은 `delib_jobs` 를 거치지 않는다 | `app.py:545-603`, `:3362` |
| MCP 심의 잡 | `delib_llm` | 전역 `DELIB_JOB_MAX_RUNNING` 2, 사용자별(기본 = 전역), 대기 줄 20(메모리 전용) | `delib_jobs.py:57`·`:65-66`·`:73` |
| 좌석 지식카드 조회 | (LLM 아님 — AIDataHub) | `DELIB_KNOWLEDGE_CONCURRENCY` 6 | `deliberation.py:2333` |

- **에이전트 서버 어디에도 LLM 호출의 전역 상한은 없다.**
- `/health` 의 `delib_active` 는 `len(_DETACHED_TASKS) + delib_jobs.running_count()`, `delib_queued` 는 `len(delib_jobs._PENDING)` 이다(`app.py:4264-4283`). 띵킹과 챗은 세지 않는다.
- `_llm_text`(`deliberation.py:1641-1655`)는 글만 돌려준다. 토큰 사용량을 읽는 코드는 없다(`usage_metadata` grep 0건). 출력이 상한에서 잘리면 표식만 붙인다.
- 서버는 루프백에 묶이고 인증이 없다(`start.sh:37-50`).

### 2.6 배포·재기동 보호 — `HWAXPortal/infra/scripts`

- `lib/delib-busy.sh` 의 `hwax_delib_busy` 가 `/health` 의 두 수를 읽어, 합이 0 보다 크면 "<진행> <대기>" 를 찍고 0 을 낸다. 모르면 2·4 이고 부르는 쪽은 **0 일 때만** 건너뛴다. `AGENT_RESTART_FORCE=1` 이면 묻지 않는다.
- 묻는 자리는 셋이다 — 포털 블록(`deploy-all-from-drive.sh:242`, `images-from-drive` **앞**), nginx(`:486-491`), 에이전트 서버(`update-sites.sh:207-211`). 게이트웨이 재프로비저닝도 묻는다(`update-all.sh:1268`).
- **heax 블록(`deploy-all-from-drive.sh:292-337`)에는 물음이 없다.** `dist-from-drive.sh` 가 바뀐 앱 SIF 를 `cp -p` 로 **제자리에서 덮어쓰고**(`HEAXHub/deploy/apptainer/dist-from-drive.sh:40`·`:84`), 지문에 `var/sifs` 가 들어 있어(`:326`) 앱 SIF 하나만 바뀌어도 허브 전체가 내렸다 올라온다.
- 에이전트 서버 `start.sh` 는 떠 있는 서버의 `/health` 를 `grep -oE '"delib_active": *[0-9]+'` 로 읽고(:105-112), 합이 0 보다 크면 `exit 3` 이다(:118-128). 유예는 2초 뒤 강제 종료다(:100, :136-141).
- update-all 의 순서는 §1 포털 pull → §1c env-sync(:300-304) → §2 deploy-all(포털·mxwp·heax·signalforge·aidh·kooremapper·nginx) → §3 AIDataHub 데이터 동기화(새 덤프면 DROP 뒤 복원) → §4 update-sites(게이트웨이·에이전트 서버) → §5 정합 → §6 헬스게이트다. 정지 신호는 § 머리에서 듣는다(:142-151). EXIT 트랩은 없다.

### 2.7 HEAXHub 가 앱을 띄우고 갈아 끼우는 방식

- 실제로 쓰이는 매니페스트는 **등록 사본** `HEAXHub/integrations/hwax-risk/.portal/manifest.yaml` 이다(런처가 `integrations/<slug>` 를 읽는다 — `integration_tasks.py:96-100`). 지금 앱 리포의 것과 내용이 같다.
- 컨테이너는 `--cleanenv` 다. 들어가는 환경은 ① 매니페스트 `launch.env`(지금 `PYTHONNOUSERSITE`·`HWAXRISK_PORTAL_BASE` 둘) ② 런처가 물려주는 것(`HEAX_APP_LLM_*`, **프록시 변수 여덟**, 검색 정책 — `integration_launcher.py:684-727`) ③ HEAX 제어 변수다. 같은 키면 매니페스트가 호스트의 `APPTAINERENV_*` 를 이긴다(런처가 `APPTAINERENV_<키>` 로 다시 싣는다).
- 생사 탐침 — celery beat 가 **45초마다** `reconcile_integrations` 를 돌린다(`celery_app.py:70-73`). 탐침은 주소 넷을 차례로 2초씩 묻고 하나라도 500 미만이면 살아 있음이다(`integration_launcher.py:88`, `:1364-1382`). 넷 다 실패하면 런처가 **같은 인스턴스 안에 서버 프로세스를 하나 더** 띄운다(server-setup §6 이 '프로세스 잠금 없음' 으로 적어 둔 일이다).
- dev — push 하면 5분 스캔이 SIF 를 `.sif.building` 에 굽고 `os.replace` 로 바꾼다(`integration_sif_builder.py:318`·`:382`). 떠 있는 인스턴스는 건드리지 않는다. 교체는 `redeploy-app.sh hwax-risk` 다(`apptainer instance stop` → `launch`).
- 메모리 상한(`resources.memory_gb: 2`)은 `enforce_instance_limits` 가 켜졌을 때만 걸리고 기본은 꺼짐이다(`HEAXHub/backend/app/config.py:88`).
- 앱 데이터 — `appdata-to-drive.sh` 가 `var/app_data/**/*.db` 를 sqlite backup 으로 떠 Drive 에 올린다(`cred.key`·`secrets.env`·`*.db.pre-*` 는 뺀다). cae00 의 `appdata-merge-from-drive.sh` 는 **모든 `.db` 마다** `cp "$live" "$live.pre-merge-<ts>"` 를 하고(:35) 병합기를 부르는데, 병합기는 materialtwin 표만 안다(없는 표는 건너뛴다 — `_materialtwin_merge.py:531-538`). 즉 cae00 은 update-all 마다 `risk_review.db` 의 사본을 하나씩 남기고 병합은 하지 않는다. 사본을 지우는 코드는 없다.

### 2.8 설정이 닿는 길

| 대상 | 정본 | 박스별로 바꾸는 길 |
|---|---|---|
| 리스크 앱 | 코드 기본값(`config.py`) → 매니페스트 `launch.env`(두 사본) | HEAXHub `.env` 의 `APPTAINERENV_HWAXRISK_*`(매니페스트에 같은 키가 없을 때만 먹는다. `.env` 를 싣지 않은 재배포에서는 빠진다 — 앱 `context-notes.md` D36) |
| 에이전트 서버 | 코드 기본값 → `<HWAXAgentServer>/.env`(`start.sh` 가 읽는다. 줄 끝 설명을 떼지 않는다) | 같은 파일. 예시는 `HWAXPortal/infra/env-kits/agent-server.env`(주석 줄은 옮겨 적히지 않는다). **`.env.example` 이 없어 env-sync 대상이 아니다** |
| 포털 | `infra/.env.example` → `infra/.env` | env-sync(update-all 1c)가 없는 키를 끝에 덧붙인다 |
| update-all 손잡이 | 스크립트 머리 주석 | 그 실행의 환경변수 |

`test_manifest.py:68` 이 `launch.env` 를 **정확히 두 키**로 못 박고 있다.

### 2.9 입력 자료에서 바로잡은 것

1. 새 표는 v2 가 아니라 **v3** 이다. v2 는 이미 `rr_brief_calls` 가 썼다(`02-fit.md` 가 '스키마 v2 로 새 표를 더한다' 고 적었다).
2. '띵킹은 동시 4' 는 전역 상한이 아니다. 요청마다 세마포어를 새로 만든다(`thinking.py:357`). 에이전트 서버에는 LLM 전역 상한이 아예 없다.
3. 야간 잡은 돌지 않는다. `nightly_loop` 의 본문이 비어 있다(`runner.py:1485-1500`). 지표는 `POST /meta/metrics/recompute` 를 손으로 부를 때만 다시 계산된다.
4. `02-cost.md` 가 확인하지 못했다고 적은 '리스크 앱 재배포가 update-all 의 어디서 일어나나' — heax 블록이고 심의 보호가 없으며 SIF 를 제자리에서 덮어쓴다(2.6).
5. 에이전트 서버가 패널 도중에 죽으면 포털 릴레이가 `error{code:'agent_unreachable'}` 를 낸다(포털 `agent/routes.py:598-604`). 리스크 앱은 이것을 `EngineError` 로 받아 `engine_error: …` 로 닫으므로 **좌석을 차감한다**(`engine_client.py:221-226`, `runner.py:1081-1083`·`:1097-1106`). 같은 사건이 `engine_stream_cut` 으로 오면 차감하지 않는다. WP1 이 볼 결함이다.
6. 매니페스트 설명의 'rr_* 41표' 는 낡았다(v2 로 42표다).
7. `config.KNOB_HOME` 의 '`.env` 는 닿지 않는다' 는 절반만 맞다. HEAXHub `.env` 의 `APPTAINERENV_*` 는 닿는다(매니페스트에 같은 키가 없을 때).

---

## 3. 설계

### 3.1 원칙

1. **셀은 끊겨도 싸다.** 셀 하나는 멱등이고, 끊기면 차감 없이 스스로 다시 돈다. 그래서 배포는 셀을 기다리지 않아도 된다(낭비를 줄이려고 잠깐 기다릴 뿐이다).
2. **패널만 지킨다.** 몇 시간짜리 쟁점 패널은 지금 보호를 그대로 쓰되, 비우기 신호로 **새 패널이 시작되지 않게** 해서 배포 창이 반드시 열리게 한다.
3. **상한은 LLM 을 보는 쪽에 둔다.** 동시 수의 정본은 에이전트 서버의 게이트 하나다. 앱의 워커 수는 그 위의 천장일 뿐이다.
4. **기다림과 멈춤을 가른다.** 밤 창·비우기·자리 없음은 기다림이다(실행은 `running` 이고 사유가 보인다). 사람이 풀어야 하는 것만 멈춤이다.
5. **어긋난 조합은 조용히 돌지 않는다.** 세 리포가 따로 배포되므로, 한쪽이 옛 판이면 쓰레기를 내는 대신 사유를 말하고 멈춘다.

### 3.2 스키마 이행

#### 3.2.1 새 표가 지키는 규약

| 규약 | 까닭(코드 근거) |
|---|---|
| 모든 새 표에 `owner_sub TEXT NOT NULL` 과 PK 를 둔다 | 없으면 반출이 공용 표로 보고 들여올 때 병합하지 않는다. PK 가 없으면 들여오기가 500 이다(`export.py:335-339`) |
| 과제 원문이 드는 표에는 `project_id TEXT NOT NULL` 을 둔다 | 반출이 폐기·코퍼스 제외 과제를 이 열로만 뺀다(`export.py:183-189`). 예외는 `rr_card_packs`(카드는 과제 원문이 아니다) |
| 어휘 열에 `CHECK` 를 걸지 않는다 | 어휘 확장이 허용 연산 밖이 된다(`rr_jobs.pause_reason` 이 그 예다). 어휘는 코드 상수와 시험이 지킨다 |
| 더하는 열은 NULL 허용이거나 상수 DEFAULT 다 | `ADD COLUMN` 의 조건이고, 옛 INSERT 문이 깨지지 않는다 |
| 원문은 `*_gz BLOB` + `*_sha`(해제본 sha256) + `*_chars` 로 둔다 | `rr_panels.brief_gz`·`rr_panel_calls.result_gz` 와 같은 꼴이다. 폐기 때 BLOB 을 NULL 로 비운다 |
| 시각 열 이름은 `created_at`·`updated_at`·`started_at`·`finished_at`(epoch 초) | `_SINCE_COLS` 에 그대로 적는다 |
| 한 번 push 된 버전의 DDL 은 고치지 않는다 | cae00 은 그 버전을 이미 적용했고 다시 돌리지 않는다. 고칠 것은 다음 버전으로 더한다 |

#### 3.2.2 버전과 순서

**권고는 v3 하나에 전부 싣고, 그것을 새 흐름의 첫 커밋으로 넣는 것이다**(표는 기능이 붙을 때까지 비어 있다).

- 꾸러미 넷이 나란히 구현되므로 버전 번호를 꾸러미별로 나누면 `MIGRATIONS` 줄에서 번호 다툼이 난다.
- 이행마다 DB 전체 사본이 하나 생긴다(2.1). 한 번이면 사본도 한 번이다.
- dev ↔ cae00 반출·들여오기는 버전이 같아야 한다. 버전이 여러 번 바뀌면 어긋나는 창이 그만큼 생긴다.
- 대가는 열을 미리 굳히는 것이다. 구현하다 모자란 열은 v4 로 더한다(쓰지 않게 된 열은 남는다 — 지울 수 없다).

v3 안의 문장 순서는 부모 → 자식이다(반출 순서가 이 순서를 그대로 쓴다. 외래키는 문자열 계약이라 순서가 깨져도 돌기는 한다).

`rr_units` → `rr_card_packs` → `rr_review_cells` → `rr_review_calls` → `rr_card_verdicts` → `rr_expert_reports` → `rr_cross_cells` → `rr_mech_cells` → 기존 표의 `ADD COLUMN` → 인덱스.

#### 3.2.3 v3 DDL 통합 초안

열 옆의 `[ops]` 는 이 꾸러미가 요구하는 것이고, 나머지는 소유 꾸러미가 확정한다. 표 이름과 PK 는 공통 계약 초안 그대로다.

```sql
-- v3 — 리스크 심사 재설계(검토 단위 · 셀 원장 · 카드 판정 · 교차 · 메커니즘). 어휘는 CHECK 가 아니라 코드가 지킨다.

CREATE TABLE IF NOT EXISTS rr_units (                         -- 검토 단위(WP2). diff = 변경 묶음 · snap = (조립 단위 × 신호군)
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL,            -- unit_id 는 내용에서 유도한 결정적 값(입력 순서를 섞어도 같다)
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  seq INTEGER NOT NULL, kind TEXT NOT NULL,                   -- bundle | boundary | global | excluded | snap_unit
  title TEXT, signature_json TEXT, unit_hash TEXT NOT NULL,   -- unit_hash = 시그니처·cid 목록·요약의 sha256[:16] — 셀 재사용 키의 반쪽
  cids_json TEXT NOT NULL, n_changes INTEGER NOT NULL DEFAULT 0,
  summary_gz BLOB, summary_sha TEXT, summary_chars INTEGER,   -- 전량 요약(잘림 0)
  evidence_gz BLOB, evidence_sha TEXT, evidence_chars INTEGER,-- 근거 꾸러미(지정 도구를 단위당 한 번 돌린 결과)
  evidence_status TEXT,                                       -- ok | partial | failed | none
  evidence_gaps_json TEXT,                                    -- [ops] 못 돌린 도구와 사유 [{tool, code, note}] — 무음 강등 금지
  builder_version TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id));
CREATE INDEX IF NOT EXISTS ix_rr_units_seq ON rr_units(target_key, seq);

CREATE TABLE IF NOT EXISTS rr_card_packs (                    -- 전문가 카드 묶음 동결본(WP3). 내용 주소 — 타깃이 아니라 해시가 키다
  owner_sub TEXT NOT NULL, pack_hash TEXT NOT NULL,           -- pack_hash = sha256(정렬한 (record_id, content_sha))[:16]
  agent_key TEXT NOT NULL, domain TEXT,
  cards_n INTEGER NOT NULL, cards_json TEXT NOT NULL,         -- 목차 [{record_id, card_id, title, type, tier, confidence, content_sha, chars}]
  content_gz BLOB, content_sha TEXT, content_chars INTEGER,   -- 본문 전량
  token_estimate INTEGER,
  source_box TEXT,                                            -- [ops] 어느 박스의 AIDataHub 에서 얼렸나(hostname)
  fetched_at INTEGER NOT NULL, last_used_at INTEGER,          -- [ops] 정리 기준
  PRIMARY KEY(owner_sub, pack_hash));
CREATE INDEX IF NOT EXISTS ix_rr_card_packs_agent ON rr_card_packs(agent_key, fetched_at);

CREATE TABLE IF NOT EXISTS rr_review_cells (                  -- 셀 원장(WP3). 전문가 × 검토 단위
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, agent_key TEXT NOT NULL,
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL, domain TEXT NOT NULL, tier TEXT,
  status TEXT NOT NULL DEFAULT 'pending',                     -- pending | running | reviewed | na_irrelevant | no_input | failed | skipped | carried
  status_source TEXT NOT NULL DEFAULT 'code', decided_by TEXT, decided_at INTEGER, reason TEXT,
  route_det TEXT, route_llm TEXT, na_basis_json TEXT, card_basis TEXT,          -- 라우팅(WP2·3)
  pack_hash TEXT, unit_hash TEXT, prompt_rev TEXT, input_hash TEXT,             -- input_hash = sha256(unit_hash|pack_hash|prompt_rev|model)[:16]
  cards_expected INTEGER, cards_judged INTEGER,
  n_violation INTEGER, n_caution INTEGER, n_ok INTEGER, n_undetermined INTEGER, n_off_card INTEGER,
  quote_total_n INTEGER, quote_verified_n INTEGER,
  ok_card_ids_json TEXT, mech_codes_json TEXT, carried_from TEXT,
  audit_kind TEXT, audit_result TEXT,                         -- [관측] na 재검토 표본 — audit_result = confirmed | overturned
  -- [ops] 작업 항목 공통 열(3.3.1)
  run_id TEXT, priority INTEGER NOT NULL DEFAULT 0,
  tries INTEGER NOT NULL DEFAULT 0, charged INTEGER NOT NULL DEFAULT 0, infra_streak INTEGER NOT NULL DEFAULT 0,
  error_code TEXT, error_class TEXT, error TEXT, knob TEXT,
  not_before INTEGER, lease_owner TEXT, heartbeat_at INTEGER,
  credential_kind TEXT, model TEXT,
  llm_calls INTEGER, tokens_in INTEGER, tokens_out INTEGER, elapsed_ms INTEGER, truncated INTEGER DEFAULT 0,
  chunks_total INTEGER, chunks_done INTEGER,
  created_at INTEGER NOT NULL, started_at INTEGER, finished_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id, agent_key));
CREATE INDEX IF NOT EXISTS ix_rr_cells_claim ON rr_review_cells(status, not_before, priority);
CREATE INDEX IF NOT EXISTS ix_rr_cells_agent ON rr_review_cells(target_key, agent_key, status);
CREATE INDEX IF NOT EXISTS ix_rr_cells_input ON rr_review_cells(input_hash);

CREATE TABLE IF NOT EXISTS rr_review_calls (                  -- [ops · 계약 추가 제안] LLM 호출 원장 — 끝난 호출 1회 = 1행
  call_id TEXT PRIMARY KEY,                                   -- 'rc-<uuid>'
  run_id TEXT, target_key TEXT NOT NULL, owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  grid TEXT NOT NULL,                                         -- cell | cross | mech | summary
  unit_id TEXT, agent_key TEXT, domain_a TEXT, domain_b TEXT, mechanism_code TEXT,
  purpose TEXT NOT NULL,                                      -- screen | judge | reask | audit | cross | mech | area_summary | final_summary
  chunk_no INTEGER, attempt INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,                                       -- ok | error | cut | timeout  ('자리 없음' 은 적지 않는다 — 계수로만)
  error_code TEXT, error_class TEXT, error TEXT, knob TEXT,
  model TEXT, card_review_rev TEXT, prompt_rev TEXT, input_hash TEXT,
  chars_in INTEGER, tokens_in INTEGER, tokens_out INTEGER,    -- 모르면 NULL(0 이 아니다)
  llm_calls INTEGER, reasks INTEGER, truncated INTEGER DEFAULT 0, finish_reason TEXT,
  elapsed_ms INTEGER, credential_kind TEXT,
  output_gz BLOB, output_sha TEXT, output_chars INTEGER,      -- 모델 원출력 전문(재파싱·재현용)
  started_at INTEGER NOT NULL, finished_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_review_calls_cell ON rr_review_calls(target_key, unit_id, agent_key, started_at);
CREATE INDEX IF NOT EXISTS ix_rr_review_calls_run ON rr_review_calls(run_id, started_at);
CREATE INDEX IF NOT EXISTS ix_rr_review_calls_err ON rr_review_calls(target_key, status, error_code);

CREATE TABLE IF NOT EXISTS rr_card_verdicts (                 -- 카드별 판정(WP3)
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, agent_key TEXT NOT NULL, record_id TEXT NOT NULL,
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  card_id TEXT, verdict TEXT NOT NULL, applicability TEXT,
  quote TEXT, quote_verified INTEGER, change_refs_json TEXT, why TEXT, grade TEXT,
  call_id TEXT,
  audit_verdict TEXT, audit_flipped INTEGER,                  -- [관측] 재질의 표본 — 뒤집힘률의 원천(안 물었으면 NULL)
  created_at INTEGER NOT NULL, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id, agent_key, record_id));
CREATE INDEX IF NOT EXISTS ix_rr_verdicts_unit ON rr_card_verdicts(target_key, unit_id, verdict);

CREATE TABLE IF NOT EXISTS rr_expert_reports (                -- 전문가별 보고서(WP3·4)
  target_key TEXT NOT NULL, agent_key TEXT NOT NULL,
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL, domain TEXT NOT NULL,
  pack_hash TEXT, cells_n INTEGER, summary_md TEXT,
  report_gz BLOB, report_sha TEXT, report_chars INTEGER,
  opinion_id TEXT, model TEXT, builder_version TEXT,
  created_at INTEGER NOT NULL, updated_at INTEGER,
  PRIMARY KEY(target_key, agent_key));

CREATE TABLE IF NOT EXISTS rr_cross_cells (                   -- 단위 × 영역쌍(WP4)
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, domain_a TEXT NOT NULL, domain_b TEXT NOT NULL,
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  origin TEXT, status TEXT NOT NULL DEFAULT 'pending', agent_key TEXT, result_json TEXT, reason TEXT,
  status_source TEXT NOT NULL DEFAULT 'code', decided_by TEXT, decided_at INTEGER,
  run_id TEXT, priority INTEGER NOT NULL DEFAULT 0,
  tries INTEGER NOT NULL DEFAULT 0, charged INTEGER NOT NULL DEFAULT 0, infra_streak INTEGER NOT NULL DEFAULT 0,
  error_code TEXT, error_class TEXT, error TEXT, knob TEXT,
  not_before INTEGER, lease_owner TEXT, heartbeat_at INTEGER, credential_kind TEXT, model TEXT,
  llm_calls INTEGER, tokens_in INTEGER, tokens_out INTEGER, elapsed_ms INTEGER, truncated INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL, started_at INTEGER, finished_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id, domain_a, domain_b));
CREATE INDEX IF NOT EXISTS ix_rr_cross_claim ON rr_cross_cells(status, not_before, priority);

CREATE TABLE IF NOT EXISTS rr_mech_cells (                    -- 단위 × 메커니즘(WP4)
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, mechanism_code TEXT NOT NULL,
  owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', covered_by_json TEXT, agent_key TEXT, result_json TEXT, reason TEXT,
  status_source TEXT NOT NULL DEFAULT 'code', decided_by TEXT, decided_at INTEGER,
  run_id TEXT, priority INTEGER NOT NULL DEFAULT 0,
  tries INTEGER NOT NULL DEFAULT 0, charged INTEGER NOT NULL DEFAULT 0, infra_streak INTEGER NOT NULL DEFAULT 0,
  error_code TEXT, error_class TEXT, error TEXT, knob TEXT,
  not_before INTEGER, lease_owner TEXT, heartbeat_at INTEGER, credential_kind TEXT, model TEXT,
  llm_calls INTEGER, tokens_in INTEGER, tokens_out INTEGER, elapsed_ms INTEGER, truncated INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL, started_at INTEGER, finished_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id, mechanism_code));
CREATE INDEX IF NOT EXISTS ix_rr_mech_claim ON rr_mech_cells(status, not_before, priority);

-- 기존 표에 더하는 열(전부 NULL 허용)
ALTER TABLE rr_targets ADD COLUMN flow TEXT;                  -- NULL = 패널 흐름(종전) | 'review_v1' = 새 흐름
ALTER TABLE rr_roster  ADD COLUMN pack_hash TEXT;             -- 이 타깃에서 그 전문가에게 얼린 카드 묶음(분모)
ALTER TABLE rr_roster  ADD COLUMN cards_n INTEGER;
ALTER TABLE rr_jobs ADD COLUMN mode TEXT;                     -- NULL | 'panels' = 종전 Tier 잡 · 'reviews' = 검토 실행
ALTER TABLE rr_jobs ADD COLUMN stage TEXT;                    -- S0 | S0b | S1 | S2 | S3 | S4 | S5 | S6
ALTER TABLE rr_jobs ADD COLUMN hold_code TEXT;                -- 3.3.3 의 보류 코드(pause_reason 의 CHECK 를 피하는 자리)
ALTER TABLE rr_jobs ADD COLUMN hold_until INTEGER;            -- 자동 재개를 다시 재는 시각
ALTER TABLE rr_jobs ADD COLUMN hold_n INTEGER DEFAULT 0;      -- 같은 코드로 이어서 멈춘 횟수(백오프 단계)
ALTER TABLE rr_jobs ADD COLUMN scope_json TEXT;               -- 사람이 고른 범위(3.11)
ALTER TABLE rr_jobs ADD COLUMN budget_json TEXT;              -- 추정·동의·상한(3.11)
ALTER TABLE rr_jobs ADD COLUMN notes_json TEXT;               -- 건너뛴 것·강등된 것의 장부(○) — 코드별로 합친 200건 이내
ALTER TABLE rr_jobs ADD COLUMN parent_job TEXT;               -- 쟁점 패널 잡이 가리키는 검토 실행(WP4)
ALTER TABLE rr_panels ADD COLUMN purpose TEXT;                -- NULL | 'tier' | 'dispute' (WP4)
ALTER TABLE rr_panels ADD COLUMN unit_id TEXT;                -- (WP4)
ALTER TABLE rr_panels ADD COLUMN turns_gz BLOB;               -- (WP4) 쟁점 패널의 좌석 발언 전문
```

`_split_statements`(`risk_store.py:529-538`)는 줄 단위로 `sqlite3.complete_statement` 를 보므로 `ALTER` 는 한 줄에 한 문장씩 적는다. `_CREATE_TABLE_RE`(`export.py:20`)는 `CREATE TABLE` 만 보므로 `ALTER` 는 반출 순서에 영향이 없다.

#### 3.2.4 옛 타깃 · 옛 잡 · 도는 잡과의 공존

| 무엇 | 규칙 |
|---|---|
| 옛 타깃(`flow IS NULL`) | 패널 흐름 그대로다. 로스터·커버리지(`deferred` 포함)·완결 판정을 건드리지 않는다 |
| 옛 타깃에 검토 실행을 시작 | 그 타깃에 살아 있는 패널 잡이 없을 때만 받는다(있으면 409 `panel_job_active`). 받으면 `flow='review_v1'` 을 적는다. 옛 패널·의견·등록부는 남고 새 흐름의 입력으로 쓰인다(어떻게 쓰는지는 WP4) |
| 새 흐름 타깃에 Tier 잡을 시작 | 409 `target_in_review_flow`. 패널은 검토 실행이 쟁점 단계에서 만든다 |
| 옛 잡(`mode IS NULL`) | `claim_next_job` 이 `mode IS NULL OR mode='panels'` 만 집는다. 동작은 종전과 같다 |
| 이행 순간에 돌던 패널 | 앱이 다시 뜨는 것이므로 지금 복구가 그대로 처리한다(`error('restart')`, 잡 멈춤) |
| 한 타깃에 검토 실행 둘 | 살아 있는 `mode='reviews'` 잡이 있으면 409 `review_active` |
| MCP L2 경로(`hwax-risk-review.js` → `risk_submit_panel_result`) | 건드리지 않는다(더하기만 한다) |

#### 3.2.5 되돌리기와 백업

되돌리기는 네 단이고 위에서부터 쓴다.

| 단 | 무엇 | 걸리는 시간 | 잃는 것 |
|---|---|---|---|
| L0 | 비우기 고정 — `./infra/scripts/review-drain.sh on --hold`(3.5). 새 셀·패널이 시작되지 않는다 | 즉시, 그 박스에서 | 없다 |
| L1 | 기능 끄기 — `HWAXRISK_REVIEW_ENABLED=0`. 새 실행은 409 `review_disabled`, 도는 실행은 `hold_code='disabled'` 로 멈춘다. 패널 흐름은 그대로다 | 앱 재기동 한 번 | 없다(표와 결과는 남는다) |
| L2 | 고친 커밋으로 앞으로 간다 | 빌드 + 배포 | 없다 |
| L3 | 옛 SIF 로 되돌린다 — 옛 코드는 버전이 높은 DB 에서 기동을 거부하므로(2.1) `risk_review.db.pre-migrate-<ts>` 로 DB 도 되돌려야 한다 | 수동 | 이행 뒤의 전부 |

L3 를 쓰지 않게 하는 것이 L1 이다. 기능 손잡이의 코드 기본값은 시범이 끝날 때까지 **꺼짐**이다(8절).

백업은 셋을 한다.

- `pre-migrate-<ts>` 는 지금대로 만든다. 만든 뒤 **가장 새것 둘만 남기고 지운다**(`prune_backups`).
- cae00 의 `risk_review.db.pre-merge-<ts>`(2.7 — 병합 없이 쌓인다)도 같은 함수가 가장 새것 둘만 남긴다. 앱이 제 데이터 디렉터리를 정리하는 것이라 HEAXHub 를 고치지 않아도 된다.
- 첫 검토 실행을 시작하기 전의 반출은 사람 몫이다(절차서에 `GET /api/export` 한 줄로 적는다).

```python
# risk_store.py
BACKUP_KEEP = 2

def prune_backups(db_path: Path, *, keep: int = BACKUP_KEEP) -> list[str]:
    """`<db>.pre-migrate-*` · `<db>.pre-merge-*` 를 갈래마다 가장 새것 keep 개만 남기고 지운다. 지운 파일 이름을 돌려준다.
    지우지 못한 것은 건너뛴다(기동을 막지 않는다). 부르는 곳 — migrate() 끝 · 유지 틱(하루 한 번)."""
```

#### 3.2.6 용량

입력 자료의 수(전문가 359명, 카드 10,774장, 카드 원문 합 약 2,050만 자)로 잰 추정이다.

| 표 | 타깃 하나당 | 근거 |
|---|---|---|
| `rr_card_packs` | 타깃과 무관하게 한 벌 — gzip 뒤 수 ~ 십수 MB(추정) | 내용 주소라 타깃마다 복사되지 않는다. 타깃마다 얼리면 타깃 수만큼 곱해진다 |
| `rr_review_cells` | 359 × 단위 수 — 8 이면 2,872행, 20 이면 7,180행 | 행당 1KB 안팎 |
| `rr_card_verdicts` | 10,774 × 단위 수 × 관련 비율 — 8·전부면 86,192행, 20·전부면 215,480행 | '문제없음' 까지 행으로 두면 이 수다. 셀의 `ok_card_ids_json` 으로 접으면 다섯에 하나쯤으로 준다(7절의 계약 변경 제안) |
| `rr_review_calls` | 호출 수만큼 — 수천 행, 원출력 gzip 포함 행당 수 KB | 3.10 |

타깃 하나에 수십 ~ 백여 MB, 열 개면 GB 에 닿는다. 그래서 사본 정리(3.2.5)와 아래 둘을 같이 넣는다.

- 반출에 표 고르기를 더한다 — `GET /api/export?tables=rr_targets,rr_review_cells,…`(없으면 전부). 응답 머리에 `X-Risk-Export-Rows` 를 싣는다.
- 쓰이지 않는 카드 묶음을 지운다 — 어느 셀·로스터도 가리키지 않고 `last_used_at` 이 `HWAXRISK_PACK_RETAIN_DAYS`(기본 180일)보다 오래된 행.

#### 3.2.7 새 표가 걸리는 자리(고칠 곳 전부)

| 파일 | 무엇을 |
|---|---|
| `export.py` `_SINCE_COLS` | 새 표 여덟의 시각 열 — `rr_units`·`rr_expert_reports`·`rr_card_verdicts`: `("updated_at","created_at")` · `rr_card_packs`: `("fetched_at",)` · `rr_review_cells`·`rr_cross_cells`·`rr_mech_cells`: `("updated_at","created_at")` · `rr_review_calls`: `("started_at",)` |
| `export.py` `_human_rank` | 세 격자 표에서 `status_source='human'` 이면 1 |
| `export.py` | `tables=` 고르기 |
| `routes.py` `PURGE_BLANK_SQL` | `rr_units`(summary_gz·evidence_gz·signature_json·cids_json → 비움) · `rr_review_cells`(reason·na_basis_json·error) · `rr_review_calls`(output_gz·error) · `rr_card_verdicts`(quote·why·change_refs_json) · `rr_expert_reports`(summary_md·report_gz) · `rr_cross_cells`·`rr_mech_cells`(result_json) · `rr_panels` 의 `turns_gz` |
| `routes.py` `purge_project` | 세 격자의 `pending`·`running` 행을 `skipped(project_purged)` 로 닫는다(커버리지와 같은 처리) |
| `metrics.py` | `panel_models` 를 `source_models` 로 넓힌다 — 패널 id 와 **셀의 호출 id** 둘 다 모델로 푼다. `_review_rows` 를 더한다(3.10.3) |
| `learning.py` `collect_atoms` | `model_of` 를 같은 `source_models` 로 바꾼다 |
| `nightly.py` `STAMP_KEYS` | `card_review_rev`·`review_prompt_rev`·`unit_builder_version` |
| `tests/test_store.py` | 소유권 시험을 v1 표에서 **전 버전의 표**로 넓힌다. 버전별 DDL 해시를 못 박는다(3.2.1 의 마지막 규약) |
| 매니페스트 두 사본 | 설명의 표 수·도구 수(3.8.2) |


### 3.3 실행 원장과 상태기계

새 파일 `HWAXRisk/backend/app/review_runner.py` 가 이 절의 전부를 갖는다. `runner.py` 의 패널 경로는 그대로 두고, `RiskRunner` 가 `review_loop` 스레드 하나와 워커 풀을 더 갖는다.

#### 3.3.1 작업 항목 규약 — 격자 셋이 같은 열을 쓴다

`rr_review_cells`·`rr_cross_cells`·`rr_mech_cells` 는 3.2.3 의 공통 열을 같은 이름으로 갖는다. 그래서 집기·백오프·복구가 표 이름만 바꿔 한 벌로 돈다.

```python
# review_runner.py
@dataclass(frozen=True)
class Grid:
    table: str                      # 'rr_review_cells' | 'rr_cross_cells' | 'rr_mech_cells'
    name: str                       # 'cell' | 'cross' | 'mech'
    key_cols: tuple[str, ...]       # PK 열
    stage: str                      # 이 격자를 도는 단계

GRIDS: tuple[Grid, ...]             # 단계 순서대로

@dataclass(frozen=True)
class Item:
    grid: Grid; key: tuple; target_key: str; run_id: str; owner_sub: str; tries: int; charged: int

@dataclass(frozen=True)
class Outcome:                      # 실행기(WP3·WP4)가 러너에 돌려주는 것
    status: str                     # 종결 상태(reviewed·na_irrelevant·no_input …) 또는 'retry'
    error_code: str | None = None
    error_class: str | None = None  # wait | infra | capacity | content | input | credential | config | human
    retry_after_s: int | None = None
    knob: str | None = None
    usage: Mapping[str, Any] | None = None   # {llm_calls, tokens_in, tokens_out, elapsed_ms, truncated, model}

class Executor(Protocol):           # 격자마다 하나 — WP3(cell)·WP4(cross·mech)가 구현한다
    def prepare(self, store, run: Mapping) -> None: ...             # 코드 단계(멱등). 이 단계의 항목을 만든다
    def execute(self, store, item: Item, engine, *, should_stop, on_progress) -> Outcome: ...

def claim_next(store, grids: Sequence[Grid], *, now: int, boot_id: str, run_ids: Sequence[str]) -> Item | None:
    """다음 항목 하나를 집는다. `UPDATE … SET status='running', lease_owner=?, heartbeat_at=?, tries=tries+1, started_at=?
    WHERE <PK> AND status='pending'` 의 rowcount 가 1 일 때만 집힌 것이다(선점은 UPDATE 하나로 한다).
    순서 — 실행(먼저 만든 것) → 단계 → priority 내림차순 → not_before → PK. `not_before > now` 는 건너뛴다."""

def settle(store, item: Item, outcome: Outcome, *, now: int, cfg) -> str:
    """결과를 항목에 적고 다음 상태를 돌려준다. 실패 분류표(3.3.4)의 유일한 구현이다."""

def recover(store, *, boot_id: str, now: int) -> dict:
    """lease_owner 가 내 boot_id 가 아닌 running 항목을 차감 없이 pending 으로 돌린다(error_code='restart'. charged 는 그대로이고 tries 는 센 채로 둔다 — 그물 20 이 재기동만 겪는 항목도 잡는다).
    프로세스 잠금(3.3.7)을 쥔 뒤에만 부른다 — 그때 남의 lease 는 전부 죽은 프로세스의 것이다."""
```

실행기가 올리는 예외는 러너가 `Outcome` 으로 옮긴다 — `ReviewBusy`(게이트) · `EngineBusy`(포털 429) · `EngineStreamLost` · `PatUnavailable` · `ReviewUnsupported`(봉투의 첫 프레임이 없다) · `EngineError(code)`.

#### 3.3.2 셀(작업 항목) 상태기계

```
pending ──집기──▶ running ──┬─ 성공 ───────────────▶ reviewed | na_irrelevant | no_input        (종결)
   ▲                        ├─ 기다림(wait) ────────▶ pending   not_before = now + retry_after     tries 되돌림
   │                        ├─ 인프라(infra) ───────▶ pending   not_before = now + 백오프          차감 없음
   │                        ├─ 용량·내용 ───────────▶ pending   charged += 1                       (상한 미만)
   │                        │                       ▶ failed                                       (상한 도달)
   │                        ├─ 입력(input) ─────────▶ failed    재시도 안 함
   │                        └─ 재기동·잠금 이전 ────▶ pending   차감 없음
   ├── 사람: 다시 ── failed
   └── 재사용 판정 ─▶ carried                                                                     (종결)
failed ── 사람: 넘김(사유 필수) ─▶ skipped                                                         (종결)
pending ─ 사람: 넘김 ─▶ skipped
```

- 종결은 `reviewed`·`na_irrelevant`·`no_input`·`skipped`·`carried` 다. `failed` 는 종결이 아니다 — 실행이 끝나려면 사람이 '다시' 또는 '넘김' 을 정해야 한다.
- `tries` 는 실제로 호출을 내보낸 횟수다(기다림은 세지 않는다). `charged` 는 그 항목 탓으로 센 실패다. `infra_streak` 는 연속 인프라 실패 수이고 성공하면 0 이 된다.
- 상한은 `HWAXRISK_REVIEW_MAX_CHARGED`(기본 2)와 `HWAXRISK_REVIEW_MAX_TRIES`(기본 20 — 인프라 실패만으로 끝없이 도는 항목의 그물, 넘으면 `failed(infra_exhausted)`)다.

#### 3.3.3 실행(잡) 상태기계와 보류 코드

상태 어휘는 `rr_jobs.state` 의 일곱 그대로다. `mode='reviews'` 인 잡에서 `paused` 의 사유는 `hold_code` 에 적는다(`pause_reason` 은 사람의 정지 `user` 에만 쓴다).

```
queued ──▶ running ──▶ completed
              │  ▲
              ▼  │ (자동 재개 또는 사람의 재개)
            paused[hold_code]
running ── 사람: 취소 ─▶ cancelling ─▶ cancelled        running ── 고칠 수 없는 오류 ─▶ failed
```

| `hold_code` | 누가 세우나 | 자동 재개 | 다시 재는 간격 | 사람이 할 일 |
|---|---|---|---|---|
| `user` | 사람(`pause`) | 아니다 | — | 재개 |
| `budget` | 호출 수·셀 수가 동의한 상한에 닿았다 | 아니다 | — | 상한을 올리거나 닫는다(3.11) |
| `credential` | 시작할 때 쓰던 사용자 PAT 를 더 쓸 수 없다 | 아니다 | — | PAT 를 다시 등록하고 재개(3.7) |
| `needs_disposition` | 남은 것이 `failed` 뿐이다 | 아니다 | — | 항목마다 '다시' 또는 '넘김' |
| `llm_outage` | 차단기(3.3.5) | 그렇다 | 300 → 600 → 1,200 → 2,400 → 3,600초 | 없다(오래가면 LLM 을 본다) |
| `engine_busy` | 포털 429 가 3,600초 이어졌다 | 그렇다 | 600초 | 없다 |
| `agent_outdated` · `portal_outdated` | 에이전트 서버가 카드 대조를 모른다 · 포털이 요청 칸을 넘기지 않는다(3.9.2) | 그렇다 | 300초 | 그 서비스를 새 판으로 올린다 |
| `aidh_unreachable` | 카드 묶음 동결 중 AIDataHub 가 답하지 않는다 | 그렇다 | 300 → 1,800초 | 없다 |
| `restart` | 쟁점 패널이 재기동에 끊겼다 | 그렇다 | 60초(조건 — 에이전트 서버 `delib_active == 0`) | 없다 |
| `disabled` | `HWAXRISK_REVIEW_ENABLED=0` | 켜지면 | 300초 | 손잡이 |

**기다림은 보류가 아니다.** 비우기·밤 전용 창·게이트의 자리 없음은 실행을 `running` 으로 둔 채 진행 응답의 `waiting{reason, since, retry_at, note}` 로만 보인다.

`restart` 의 자동 재개가 지금 패널 규칙과 다른 점은 조건이다. 지금 사람 재개를 요구하는 까닭은 엔진이 끊긴 심의를 계속 돌리고 있어서인데(2.3), 그 심의가 끝났는지는 `/health` 의 `delib_active` 로 볼 수 있다. 0 이 되면 겹칠 것이 없다. 상한 `HWAXRISK_PANEL_AUTORESUME_MAX_S`(기본 21,600초)를 넘기면 조건과 무관하게 재개한다(남의 심의가 계속 돌아 0 이 안 되는 박스의 그물이다). 이 규칙은 검토 실행이 만든 쟁점 패널 잡에만 건다. 종전 Tier 잡에 걸지는 WP1·WP4 가 정한다.

#### 3.3.4 실패 분류표 — `settle` 의 정본

| `error_code` | 어디서 나오나 | 부류 | 차감 | 다음 |
|---|---|---|---|---|
| `review_busy` | 에이전트 서버 게이트 | wait | 없음 | 응답의 `retry_after_s` 뒤 |
| `engine_busy` | 포털 429 | wait | 없음 | 30초 뒤. 3,600초 이어지면 실행을 `engine_busy` 로 보류 |
| `draining` | 앱이 비우기를 봤다 | wait | 없음 | 풀릴 때까지 집지 않는다 |
| `agent_unreachable` · `agent_5xx` | 포털 릴레이의 error 프레임 | infra | 없음 | 백오프 |
| `engine_stream_cut` | 스트림 중간 절단(`RemoteProtocolError`·`ReadError`) | infra | 없음 | 백오프 |
| `engine_silent` | 앱의 침묵 한도 · 포털의 `agent_stream_idle` | infra | 없음 | 백오프 |
| `portal_unreachable` · `portal_5xx` | 연결 실패 · 502·503·504 | infra | 없음 | 백오프 |
| `llm_unreachable` | LLM 연결 오류 | infra | 없음 | 백오프 + 차단기 |
| `restart` | 재기동 복구 | infra | 없음 | 0 ~ 30초 흩뿌려(한꺼번에 다시 나가지 않게) |
| `llm_timeout` | LLM 호출이 재시도까지 한도를 넘겼다 | capacity | 있음 | 15분 뒤. `knob='CARD_REVIEW_TIMEOUT_S'` 를 같이 적는다. 차단기에도 센다 |
| `review_timeout` | 앱의 호출 벽시계 | capacity | 있음 | 같다. `knob='HWAXRISK_REVIEW_CALL_TIMEOUT_S'` |
| `output_truncated` | 출력이 `max_tokens` 에서 잘렸다(되묻기 뒤에도) | content | 있음 | 곧바로 |
| `review_parse_failed` | 응답을 풀지 못했다 | content | 있음 | 곧바로 |
| `review_incomplete` | 카드 번호 집합이 맞지 않는다(되묻기 뒤에도) | content | 있음 | 빠진 카드만(WP3) |
| `context_overflow` | LLM 이 창 초과로 거절했다 | input | — | 재시도하지 않는다. 분할은 WP3. 못 나누면 `failed` |
| `pack_missing` · `unit_missing` · `pack_fetch_failed` | 입력이 없다 | input | — | `failed` |
| `pat_unavailable` | 자격 없음 · 포털 401·403 | credential | 없음 | 실행을 `credential` 로 보류 |
| `review_unsupported` | 봉투의 첫 프레임이 없다 | config | 없음 | 실행을 `agent_outdated`·`portal_outdated` 로 보류 |
| `cancelled` | 사람의 취소 | human | 없음 | — |
| 그 밖 | — | content | 있음 | 곧바로(모르는 코드는 원문을 `error` 에 남긴다) |

#### 3.3.5 백오프와 차단기

- 인프라 백오프 — `min(30 × 2^(infra_streak − 1), 900)` 초에 ±20% 흩뿌림. 1회 30초, 6회부터 900초다.
- 차단기 — 그 실행의 최근 끝난 호출 20건(`rr_review_calls`) 가운데 인프라·용량 실패가 10건 이상이면 실행을 `llm_outage` 로 보류한다. 다시 잴 때는 **항목 하나만** 먼저 돌린다(탐침). 성공하면 풀고, 실패하면 간격을 한 단 올린다. 이것이 없으면 LLM 이 죽은 밤에 항목 수천 개가 `tries` 를 태운다.
- 탐침에 쓰는 것은 실제 항목이다(따로 만든 프롬프트가 아니다).

#### 3.3.6 재기동 뒤 어디서부터 다시 도나

| 죽은 것 | 그때 도는 것 | 다시 뜬 뒤 |
|---|---|---|
| 리스크 앱(SIF 교체·허브 재기동·크래시) | 셀 호출 — 구독이 끊기면 에이전트 서버가 그 LLM 호출을 취소한다(분리 태스크가 아니다 — 7절) | `recover` 가 `running` 을 `pending` 으로(차감 없음). 실행은 `running` 그대로라 첫 틱부터 이어 돈다 |
| 〃 | 쟁점 패널 | 지금 복구(`error('restart')`) + 실행 보류 `restart` → `delib_active == 0` 이면 자동 재개 |
| 〃 | 코드 단계(단위 생성·묶음 동결·검증) | 단계마다 멱등이다. `advance` 가 표를 보고 빠진 것만 다시 한다 |
| 에이전트 서버 | 셀 호출 | 포털이 `agent_unreachable` 을 낸다 → infra 백오프 → 다시 |
| 포털·nginx | 셀 호출 | `engine_stream_cut` → infra 백오프 → 다시 |
| AIDataHub(재기동·§3 의 DROP 뒤 복원) | 묶음 동결·긴 문서 검색 | 동결은 보류 `aidh_unreachable`, 검색은 그 호출의 infra 실패 |
| 게이트웨이 | 근거 꾸러미의 도구 호출 | 그 도구만 `evidence_gaps_json` 에 남고 단위는 `partial` 이다(WP2). 재시도 규칙은 WP2 |
| LLM 서버 | 전부 | 차단기 |
| 박스 재부팅 | 전부 | 위의 합. 비우기 깃발은 파일에 남아 수명까지 유지된다(3.5.1) |

**실행은 표의 순수 함수로 나아간다.** `advance(store, run)` 은 메모리 상태를 믿지 않는다 — 단위가 있나, 묶음이 다 얼었나, 이 단계의 항목이 다 종결인가를 매 틱 표에서 읽어 다음 일을 정한다. 그래서 재기동은 '다시 계산' 일 뿐이다.

```python
def advance(store, run: Mapping, env: "AgentEnv", *, now: int, cfg) -> dict:
    """실행 하나를 한 걸음 민다. 반환 {stage, did, claimable_grids, hold?}.
    S0 단위·근거 꾸러미(WP2) → S0b 카드 묶음 동결(전 전문가 — 셀보다 먼저 끝낸다) → S1 훑기 → S2 대조 → S3 검증·표본
    → S4 교차·메커니즘 → S5 쟁점 패널 → S6 보고서. 단계가 끝났는지는 그 단계 격자에 pending·running 이 0 인가로 본다."""
```

카드 묶음을 **셀보다 먼저 전부** 얼리는 까닭은 운영에 있다. cae00 의 update-all §3 은 새 덤프가 오면 AIDataHub 를 DROP 뒤 복원한다(2.6). 며칠 도는 실행 한가운데에서 카드가 바뀌면 앞 셀과 뒤 셀이 다른 카드를 본다.

#### 3.3.7 프로세스 잠금과 헬스

허브는 45초마다 2초 탐침을 하고, 실패하면 같은 데이터 디렉터리 위에 서버를 하나 더 띄운다(2.7). 둘째 프로세스가 `recover` 를 돌리면 첫째가 돌리는 항목을 `pending` 으로 되돌려 같은 셀이 두 번 돈다. 며칠 도는 실행에서는 드문 일이 아니게 된다.

```python
# 새 파일 runlock.py
class RunnerLock:
    """데이터 디렉터리의 `runner.lock` 을 fcntl.flock(LOCK_EX | LOCK_NB) 으로 쥔다. 쥔 프로세스만 러너 루프와 복구를 돈다."""
    def __init__(self, data_dir: Path) -> None: ...
    def acquire(self) -> bool: ...      # 못 쥐면 False(기다리지 않는다). 파일에는 pid·boot_id·시각을 적는다(사람이 읽는 용)
    def held(self) -> bool: ...
    def holder(self) -> dict | None: ...# 못 쥐었을 때 파일에 적힌 주인
    def release(self) -> None: ...
```

- `RiskRunner.start()` 는 잠금을 쥔 뒤에만 `recover_running_panels`·`review_runner.recover` 와 루프를 시작한다. 못 쥐면 REST·MCP 만 열고, 60초마다 다시 시도한다(첫째가 죽으면 커널이 잠금을 풀어 둘째가 이어받는다).
- 못 쥔 프로세스의 `/api/health` 는 `warnings` 에 `runner_lock_held` 를 싣는다. 잡 조작(정지·취소)은 표를 고치는 것이라 어느 프로세스가 받아도 러너에 닿는다(러너는 표를 읽는다 — `_stop_reader`).
- 두 프로세스가 같은 DB 를 쓰게 되므로 연결에 `PRAGMA busy_timeout = 30000` 을 준다(지금은 기본 5초).
- `/api/health` 는 저장소 락을 잡지 않는다. 스키마 버전은 기동 때 `app.state.schema_version` 에 담아 둔 값을 낸다(이행은 기동 때만 일어난다). 반출이나 병합이 락을 몇 초 쥐어도 탐침이 실패하지 않는다.

### 3.4 LLM 경합 — 게이트

#### 3.4.1 무엇을 막나

카드 대조 호출 하나는 입력이 수만 토큰이다(입력 자료 — 전문가 카드 평균 57,072자). 이것이 며칠 동안 이어진다. 지금 구조에서 가장 먼저 다치는 것은 챗이다 — 챗 스트리밍은 첫 토큰을 300초 안에 받아야 하고(`LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S`), 띵킹 좌석은 600초다.

막는 방법은 셋을 겹친다.

1. **전용 게이트** — 카드 대조 호출의 동시 수를 에이전트 서버 한 곳에서 센다. 챗·심의·띵킹의 길은 건드리지 않는다.
2. **양보** — 챗·띵킹이 돌고 있거나 심의가 돌고 있으면 게이트의 상한이 내려간다. 챗이 실제로 밀린 흔적(청크 침묵 초과)이 나오면 일정 시간 한 자리로 내린다.
3. **밤 창** — 낮에는 낮은 상한, 밤과 주말에는 높은 상한.

LLM 서버 쪽 우선순위는 쓰지 않는다(서빙 설정을 모른다 — 9절).

#### 3.4.2 정책 함수

새 파일 `HWAXAgentServer/review_gate.py`.

```python
@dataclass(frozen=True)
class GateConfig:
    day: int                 # CARD_REVIEW_CONCURRENCY            기본 2
    night: int               # CARD_REVIEW_CONCURRENCY_NIGHT      기본 6
    with_chat: int           # CARD_REVIEW_CONCURRENCY_WITH_CHAT  기본 2
    with_delib: int          # CARD_REVIEW_CONCURRENCY_WITH_DELIB 기본 2
    on_stall: int            # CARD_REVIEW_CONCURRENCY_ON_STALL   기본 1
    stall_cooldown_s: int    # CARD_REVIEW_STALL_COOLDOWN_S       기본 600
    night_hours: tuple[int, int]   # CARD_REVIEW_NIGHT_HOURS      기본 (19, 8) — 시작 시 포함, 끝 시 제외, 자정을 넘는다
    weekends_night: bool     # CARD_REVIEW_NIGHT_WEEKENDS         기본 True
    tz: str                  # CARD_REVIEW_TZ                     기본 'Asia/Seoul'(박스 시간대에 기대지 않는다)
    retry_after_s: int       # CARD_REVIEW_RETRY_AFTER_S          기본 30

def load_config(env: Mapping[str, str] = os.environ) -> GateConfig: ...
    # deliberation._env_int 와 같은 규칙 — 숫자가 아니면 경고하고 기본값. 음수는 0 으로 읽는다.

def in_night(now: datetime, cfg: GateConfig) -> bool: ...

def limit_for(now: datetime, *, chat_active: int, delib_active: int, stalled_recently: bool,
              draining: bool, cfg: GateConfig) -> tuple[int, str]:
    """지금 허용하는 동시 수와 그 까닭. 순서대로 본다 —
    draining → (0, 'draining') · stalled_recently → (min(base, on_stall), 'chat_stall')
    · chat_active > 0 → (min(base, with_chat), 'chat') · delib_active > 0 → (min(base, with_delib), 'delib')
    · 그 밖 → (base, 'night' | 'day').  base = night 창이면 cfg.night, 아니면 cfg.day.  순수 함수다."""

class ReviewGate:
    def __init__(self, cfg: GateConfig, *, load: Callable[[], tuple[int, int, bool]],
                 drain: "DrainState", clock: Callable[[], datetime]) -> None: ...
        # load() → (chat_active, delib_active, stalled_recently). 이벤트 루프 안에서만 쓴다.
    def try_acquire(self, tag: str) -> "Ticket | Busy": ...
        # 동기·무대기다(await 가 없다 — 세고 넣는 사이에 다른 태스크가 끼지 못한다).
        # Busy(reason, retry_after_s, limit, active)
    def release(self, ticket: "Ticket", *, outcome: str, usage: Mapping | None) -> None: ...
        # outcome ∈ ok | error | cancelled | timeout. 누계를 올린다. usage 의 토큰이 None 이면 tokens_unknown_calls 를 올린다
    def snapshot(self) -> dict: ...     # /health 의 card_review 칸
```

기본값이 뜻하는 것은 한 줄이다 — **밤이고 아무도 안 쓸 때 6, 그 밖에는 2.** 낮 상한을 0 으로 두면 밤 전용이 된다(8절).

**게이트는 줄을 세우지 않는다.** 자리가 없으면 곧바로 '자리 없음' 을 답하고(3.4.4) 앱이 쉬었다 다시 온다. 줄을 세우면 기다리는 요청이 포털의 자리와 연결을 쥔 채 앱의 호출 벽시계를 태우고, 비우기와 재기동 때 버려지는 것이 는다.

#### 3.4.3 `/health` 에 더하는 것

기존 키는 이름도 뜻도 바꾸지 않는다(`delib_active`·`delib_queued` 는 셸 둘이 읽는다 — 2.6). **카드 대조 호출은 `delib_active` 에 세지 않는다.** 세면 며칠 동안 0 이 되지 않아 update-all 이 재기동을 영영 미룬다.

셸이 `grep` 으로 읽을 수 있게 수 둘은 최상위에 평평하게 둔다.

```json
{
  "status": "ok",
  "delib_active": 1,
  "delib_queued": 0,
  "review_active": 2,
  "draining": false,
  "capabilities": ["card_review"],
  "card_review": {
    "rev": "cr-1",
    "limit": 2, "limit_reason": "delib", "active": 2,
    "limits": {"day": 2, "night": 6, "with_chat": 2, "with_delib": 2, "on_stall": 1},
    "window": {"night": true, "night_hours": "19-08", "weekends_night": true, "tz": "Asia/Seoul"},
    "timeout_s": 1800, "tries": 2, "reask_max": 2, "request_worst_s": 10824,
    "heartbeat_s": 15, "quiet_ok_s": 30, "retry_after_s": 30,
    "totals": {"since": 1791500000, "calls": 412, "ok": 398, "error": 7, "timeout": 2, "cancelled": 5, "busy": 131,
               "tokens_in": 24811230, "tokens_out": 1203441, "tokens_unknown_calls": 0, "truncated": 3}
  },
  "drain": {"on": false, "until": null, "by": null, "reason": null, "hold": false, "set_at": null},
  "load": {"since": 1791500000, "chat_active": 0, "think_active": 0, "chat_stall_total": 0,
           "last_chat_stall_at": null, "seat_lost_total": 0}
}
```

- `request_worst_s` = (1 + `reask_max`) × (`tries` × `timeout_s` + 8). 앱이 제 벽시계를 이 값 위로 맞춘다(3.6).
- `quiet_ok_s` 는 heartbeat 가 켜져 있으면 2 × `heartbeat_s`, 꺼져 있으면 `request_worst_s` 다.
- `load` 의 수는 `chat()` 의 두 갈래(`_agent_stream`·`run_thinking`, `app.py:3378-3382`)를 세는 얇은 감싸개로 얻는다. `chat_stall_total` 은 `_stream_chunk_limit_note` 가 사유를 돌려줄 때(`app.py:264-278`), `seat_lost_total` 은 `seat_lost` 경고를 낼 때(`deliberation.py:4728`) 올린다.
- 누계는 프로세스 수명 동안의 값이다(`since`). 재기동하면 0 부터다.

#### 3.4.4 카드 대조 호출이 지켜야 하는 봉투(운영 쪽)

모듈 본문은 WP3 의 것이다. 운영이 기대는 것은 아래 일곱이다.

| # | 규약 | 까닭 |
|---|---|---|
| 1 | 첫 프레임은 `event: review` `data: {"kind":"hello","rev":"cr-1"}` 다 | 옛 에이전트 서버·옛 포털은 이 프레임을 내지 못한다. 앱은 첫 프레임이 이것이 아니면 `review_unsupported` 로 본다 |
| 2 | 본문에 들어가기 전에 `gate.try_acquire()` 를 부르고, `Busy` 면 `event: error` `data: {"code":"review_busy","reason":"…","retry_after_s":30,"limit":2,"active":2}` 뒤 `done` 으로 **1초 안에** 끝낸다 | 3.4.2 |
| 3 | `_detach_stream` 을 타지 않는다. 구독이 끊기면 진행 중인 LLM 호출이 취소돼야 한다 | 결과를 받을 곳이 사라진 호출이 LLM 을 계속 쓰지 않게 한다. `_DETACHED_TASKS` 에 들어가면 `delib_active` 도 오른다 |
| 4 | LLM 을 기다리는 동안 `DELIB_HEARTBEAT_S` 간격으로 `event: ping` 을 낸다(`_subscribe` 와 같은 방식 — 기다리는 태스크를 취소하지 않고 `asyncio.wait(timeout)`) | 침묵 한도 |
| 5 | 끝 프레임(`result`)에 `usage{llm_calls, reasks, tokens_in, tokens_out, elapsed_ms, truncated, finish_reason, model}` 를 싣는다. 토큰을 모르면 `null` 이다 | 관측. 0 과 모름을 섞지 않는다 |
| 6 | 실패는 `event: error` `data: {"code", "message", "knob"?}` 다. 코드는 3.3.4 의 어휘를 쓴다(`llm_timeout`·`llm_unreachable`·`context_overflow`·`output_truncated`·`review_parse_failed`·`review_incomplete`) | 분류표 |
| 7 | `finally` 에서 `gate.release(ticket, outcome=…, usage=…)` 를 부른다 | 자리가 새지 않게 한다(포털 세마포어가 샌 선례 — 포털 `agent/routes.py:1442-1446`) |

`review_busy` 프레임의 예는 아래와 같다.

```
event: review
data: {"kind": "hello", "rev": "cr-1"}

event: error
data: {"code": "review_busy", "reason": "chat", "retry_after_s": 30, "limit": 2, "active": 2,
       "message": "카드 대조 자리가 없다 — 챗이 도는 동안 2건까지 받는다(CARD_REVIEW_CONCURRENCY_WITH_CHAT). 30초 뒤 다시 묻는다"}

event: done
data: {}
```

#### 3.4.5 앱 쪽 — 워커 수와 게이트를 맞춘다

```python
# review_runner.py
@dataclass(frozen=True)
class AgentEnv:
    reachable: bool; supports_review: bool; rev: str | None
    limit: int | None; limit_reason: str | None; draining: bool; drain: Mapping | None
    delib_active: int | None; request_worst_s: int | None; heartbeat_s: float | None; quiet_ok_s: int | None
    context_tokens: int | None; night: bool | None; seen_at: int

def read_agent_env(settings, *, client_factory=None, ttl_s: int = 15) -> AgentEnv:
    """에이전트 서버 `/health` 를 읽는다(15초 캐시, 한도 2초 — PortalPanelEngine.health 와 같은 주소·같은 한도).
    못 읽으면 reachable=False 이고 limit·draining 은 모름(None·False)이다 — 모른다고 멈추지 않는다(상한의 정본은 게이트다)."""
```

- 한 틱에 새로 띄우는 워커 수는 `min(HWAXRISK_REVIEW_CONCURRENCY, env.limit 또는 그 값) − 도는 워커 수` 다. `env.draining` 이면 0 이다.
- 밤 전용으로 청한 실행(`scope.window='night_only'`)은 `env.night` 이 참일 때만 집는다.
- 동시에 도는 실행 수는 `HWAXRISK_REVIEW_RUNS_PARALLEL`(기본 1)이다. 먼저 만든 실행이 풀을 다 쓰고, 다음 실행은 `queued` 로 기다린다(끝나는 시각을 말할 수 있게 한다).
- 패널 워커(`HWAXRISK_CONCURRENCY` 2)와 검토 워커는 세마포어가 따로다.

### 3.5 비우기 신호

#### 3.5.1 에이전트 서버 — 깃발 하나

```python
# review_gate.py
class DrainState:
    """'새 셀·새 패널을 받지 않는다' 깃발. 파일에 남겨 재기동을 넘긴다(수명이 지나면 스스로 풀린다)."""
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None: ...
        # path 기본값 = delib_jobs.JOB_DIR.parent / "drain.json" (DRAIN_STATE_PATH 로 바꾼다)
    def set(self, *, on: bool, ttl_s: int = 1800, by: str = "", reason: str = "", hold: bool = False) -> dict: ...
        # hold=True 면 수명이 없다(사람이 내릴 때까지). ttl_s 는 60 ~ 86400 으로 죈다.
    def active(self) -> bool: ...        # 수명이 지났으면 False 이고 파일을 지운다
    def snapshot(self) -> dict: ...      # {on, until, by, reason, hold, set_at}
```

```
POST /drain   {"on": true, "ttl_s": 1800, "by": "update-all", "reason": "deploy", "hold": false}
           →  {"on": true, "until": 1791501800, "hold": false, "review_active": 2, "delib_active": 1, "delib_queued": 0}
GET  /drain →  같은 꼴
```

- 인증은 없다. 이 서버는 루프백에만 묶이고 `/chat` 도 같은 신뢰 수준이다(2.5).
- 깃발이 서면 게이트는 `review_busy(reason='draining')` 만 답한다. **챗·띵킹·사람이 시작한 심의는 막지 않는다.**
- 깃발은 에이전트 서버 재기동을 넘긴다. 수명(기본 1,800초)이 그물이다 — update-all 이 죽어도 30분 뒤에는 풀린다.

#### 3.5.2 리스크 앱 — 깃발을 보면 집지 않는다

- `review_loop` 는 `env.draining` 이면 새 항목을 집지 않는다. 도는 항목은 끝까지 간다(셀은 수 분이다).
- `claim_next_job`(패널) 도 같은 `env` 를 본다. `draining` 이면 그 틱에는 아무 잡도 집지 않는다. 잡 상태는 바꾸지 않는다.
- 진행 응답의 `waiting` 에 `{reason:'draining', by, since, until, note:'배포 준비 — 새 셀·패널을 시작하지 않는다'}` 가 실린다.
- 에이전트 서버에 못 닿으면 '비우는 중이 아니다' 로 읽는다. 그때는 호출 자체가 인프라 실패로 돌아오므로 따로 멈출 까닭이 없다.

#### 3.5.3 update-all · deploy-all

`lib/delib-busy.sh` 에 함수 셋을 더한다. `hwax_delib_busy` 는 한 글자도 바꾸지 않는다.

```bash
# hwax_review_state [health url]
#   "<review_active> <draining 0|1> <delib_active> <delib_queued>" 를 찍고 0.
#   새 칸이 없으면(옛 판) 3 · 받지 않거나 깨진 응답이면 2 · 내리 시간 초과면 4.  --noproxy '*' · -m 4 는 hwax_delib_busy 와 같다.
# hwax_drain on|off|status [ttl_s] [reason] [hold]
#   에이전트 서버 /drain 을 부른다. 0 = 됐다 · 3 = 그 서버가 /drain 을 모른다(404·405 — 옛 판) · 2 = 받지 않는다.
#   실패해도 부르는 쪽을 멈추지 않는다 — 비우기는 예의이지 관문이 아니다.
# hwax_review_wait <max_s>
#   review_active 가 0 이 될 때까지 30초마다 한 줄씩 찍으며 기다린다. 0 = 비었다 · 1 = 시간이 다 됐다(남은 수를 찍는다) · 2·3·4 = 모른다.
# ⚠ 셋 다 0 이 아닌 값을 정상으로 돌려준다 — `set -e` 스크립트에서는 `… || _rc=$?` 로 받는다(hwax_delib_busy 와 같은 주의).
```

update-all 에 절 하나와 끝맺음 하나를 더한다.

```bash
# ── 1f) 리스크 검토 비우기 — §2 앞. 새 셀·패널이 이 실행의 재기동과 겹쳐 시작되지 않게 한다 ──
hr "1f) 리스크 검토 비우기"
_dr=0; hwax_drain on "${HWAX_DRAIN_TTL_S:-1800}" update-all >/dev/null || _dr=$?
case "$_dr" in
  0) HWAX_DRAIN_RAISED=1
     if [ "${AGENT_RESTART_FORCE:-0}" = 1 ] || [ "${HWAX_DRAIN_WAIT_S:-600}" = 0 ]; then
       echo "  · 비우기 신호를 세웠다 — 도는 셀을 기다리지 않는다"
     else
       _wr=0; hwax_review_wait "${HWAX_DRAIN_WAIT_S:-600}" || _wr=$?
       [ "$_wr" = 1 ] && echo "  ⚠ 셀이 아직 돈다 — 더 기다리지 않고 간다. 끊긴 셀은 차감 없이 다시 돈다(더 기다리려면 HWAX_DRAIN_WAIT_S)"
     fi ;;
  3) hwax_skip "리스크 검토 비우기" "에이전트 서버가 /drain 을 모른다(옛 판) — 도는 셀이 있어도 세울 신호가 없다" \
               "이번 실행이 에이전트 서버를 새 판으로 올린 뒤부터 걸린다" ;;
  *) echo "  · 에이전트 서버가 답하지 않는다 — 비울 것이 없다" ;;
esac

# ── 끝맺음 — 요약 직전과 § 머리의 정지 지점에서 부른다. 못 불렀으면 수명이 푼다 ──
_hwax_drain_finish() {
  [ "${HWAX_DRAIN_RAISED:-0}" = 1 ] || return 0
  if [ -n "${DEFERRED_ANY:-}" ] && [ "${HWAX_DRAIN_HOLD_S:-3600}" != 0 ]; then
    hwax_drain on "${HWAX_DRAIN_HOLD_S:-3600}" "update-all: 미룬 재기동이 있다" >/dev/null || true
    hwax_skip "리스크 검토 재개" "미룬 재기동이 있어 비우기를 ${HWAX_DRAIN_HOLD_S:-3600}초 더 둔다 — 그동안 새 셀·패널이 시작되지 않아, 도는 심의가 끝나면 다시 돌릴 틈이 생긴다" \
              "심의가 끝난 뒤 update-all 을 다시 돌린다 · 지금 풀려면 ./infra/scripts/review-drain.sh off"
  else
    hwax_drain off >/dev/null || true
  fi
}
```

- `DEFERRED_ANY` 는 이 실행에서 심의 때문에 미룬 재기동이 하나라도 있었다는 표시다(지금의 `_DA_RC`·`_us_rc` 3 과 `DEFERRED_RESTART` 에서 만든다).
- 기다리는 한도의 기본은 **600초**다. 셀 하나는 보통 수 분이고, 넘기면 끊고 간다(원칙 1). 패널은 기다리지 않는다 — 지금처럼 미루고(○), 대신 비우기를 한 시간 남겨 **다음 실행에는 틈이 열려 있게** 한다.
- `AGENT_RESTART_FORCE=1` 이면 기다리지 않는다(사람이 끊기로 한 실행이다).

deploy-all 의 heax 블록에 물음 하나를 더한다. 자리는 `dist-from-drive.sh` **앞**이다 — 그 스크립트가 떠 있는 인스턴스 밑의 SIF 를 제자리에서 덮어쓴다(2.6). 포털 블록이 `images-from-drive` 앞에서 묻는 것과 같은 이유다(`deploy-all-from-drive.sh:239-242`).

```bash
      set_remote .env HEAX_DRIVE_REMOTE HEAXHub/dist
      # 도는·줄 선 심의가 있으면 허브를 내리지 않는다 — 리스크 앱과 좌석이 부르는 도구(StepForge 등)가 전부 이 허브에 산다.
      if _delib_hold http://localhost:4180/health "heax 재기동 건너뜀" "새 앱 SIF 를 받지 않았다. 허브와 앱은 옛 것 그대로다"; then exit 3; fi
      ./deploy/apptainer/dist-from-drive.sh || exit 1
```

새 스크립트 `infra/scripts/review-drain.sh` 는 사람이 쓰는 얇은 감싸개다.

```
./infra/scripts/review-drain.sh status              # 깃발과 review_active · delib_active
./infra/scripts/review-drain.sh on [--ttl 1800]     # 세운다(수명 뒤 스스로 풀린다)
./infra/scripts/review-drain.sh on --hold           # 사람이 내릴 때까지 — 되돌리기 L0
./infra/scripts/review-drain.sh off
```

에이전트 서버 `start.sh` 는 판정을 바꾸지 않는다(`delib_active + delib_queued` 만 본다). `review_active` 가 0 보다 크면 한 줄만 더 찍는다 — `· 카드 대조 N건이 돈다 — 재기동으로 끊긴다(리스크 앱이 차감 없이 다시 돌린다)`.

### 3.6 시간 한도의 층 — 새 경로가 끼는 자리

#### 3.6.1 표

server-setup §4-8 의 표에 아래 줄을 더한다. 번호는 그 표의 줄 사이에 끼는 자리다.

| 자리 | 층(안쪽 → 바깥) | 기본 | 손잡이 | 적는 곳 |
|---|---|---|---|---|
| 2 와 같은 줄 | 카드 대조의 LLM 호출 한 번(시도 1회) | 1,800초 | `CARD_REVIEW_TIMEOUT_S`(없으면 `DELIB_TIMEOUT_S` 를 따른다. 0 = 한도 없음) | 에이전트서버 `.env` |
| 3 과 같은 줄 | 그 호출의 재시도까지 | 3,608초(2 × 1,800 + 8) | `DELIB_LLM_MAX_RETRIES`(1) — 심의와 같이 쓴다 | 에이전트서버 `.env` |
| 4 와 같은 줄 | 카드 대조 요청 하나(되묻기까지) | 10,824초(3 × 3,608) | `CARD_REVIEW_REASK_MAX`(2) | 에이전트서버 `.env` |
| 10 앞 | 리스크 앱이 카드 대조 요청 하나를 기다리는 벽시계 | 14,400초(4시간). 에이전트 서버가 알린 `request_worst_s` + 300 보다 작으면 그 값으로 올려 쓴다 | `HWAXRISK_REVIEW_CALL_TIMEOUT_S`(0 = 끔) | 매니페스트 `launch.env` |
| 10 앞 | 카드 대조 호출의 자격 여유 | 15,000초(벽시계 + 600) | 유도값 | — |
| 신호 옆 | 카드 대조 스트림의 침묵 한도(앱) | 1,800초. heartbeat 가 꺼진 박스에서는 2 × `quiet_ok_s` 로 올려 쓴다 | `HWAXRISK_REVIEW_READ_TIMEOUT_S` | 매니페스트 `launch.env` |
| 5 옆 | 카드 묶음 동결 — AIDataHub REST 호출 하나 | 180초(AIDataHub 의 풀 대기 60 + 문장 90 보다 크다) | `HWAXRISK_AIDH_CALL_TIMEOUT_S` | 매니페스트 `launch.env` |
| — | 비우기 깃발의 수명 | 1,800초(미룬 재기동이 있으면 3,600초) | `HWAX_DRAIN_TTL_S` · `HWAX_DRAIN_HOLD_S` | update-all 실행의 환경 |
| — | update-all 이 도는 셀을 기다리는 시간 | 600초 | `HWAX_DRAIN_WAIT_S`(0 = 기다리지 않는다) | update-all 실행의 환경 |

#### 3.6.2 안쪽이 먼저 걸리는가

누적 시간 사슬은 아래와 같다.

```
LLM 연결 10  <  시도 1,800  <  논리 호출 3,608  <  요청 하나 10,824  <  앱 벽시계 14,400  <  자격 여유 15,000  <  PAT 등록 하한 86,400
                                                                                         <  chat PAT 최소 잔여 84,600(86,400 − 발급 창 1,800)
```

- 안쪽 셋은 전부 유한하다. 그래서 에이전트 서버에는 요청 전체를 재는 한도를 만들지 않는다(엔진에 심의 전체 벽시계를 두지 않는 것과 같은 이유다).
- 박스에서 `DELIB_TIMEOUT_S` 나 `CARD_REVIEW_TIMEOUT_S` 를 올리면 `request_worst_s` 가 커진다. 앱은 그 값을 `/health` 에서 읽어 **제 벽시계를 스스로 올려 쓴다** — `effective = max(HWAXRISK_REVIEW_CALL_TIMEOUT_S, request_worst_s + 300)`. 한쪽만 고쳐도 순서가 뒤집히지 않는다. 올려 쓴 사실은 진행 응답의 `notes` 에 한 줄 남는다.
- 올려 쓴 값에 600 을 더한 것이 PAT 등록 하한(86,400)에 닿으면 사용자 PAT 로는 시작하지 못한다. 그때의 문구는 손잡이 이름 둘을 말한다. 요청 상한값(`DELIB_TIMEOUT_MAX_S` 14,400)을 박스 기본값으로 적으면 이 일이 난다(3 × (2 × 14,400 + 8) = 86,424).
- 기동 검사 `check_review_chain(settings)` — 설정값만으로 `HWAXRISK_REVIEW_CALL_TIMEOUT_S + 600 ≥ PAT 등록 하한` 이면 기동을 막는다(`check_credential_chain` 과 같은 방식, `main.py:52-65`).

침묵 사슬은 아래와 같다.

```
엔진 ping 15  <  앱의 카드 대조 침묵 한도 1,800  <  포털 릴레이 46,800  <  nginx 50,400      (패널 경로의 앱 한도 54,000 은 그대로다)
```

**여기는 지금 규칙과 일부러 다르다.** 지금은 앱의 침묵 한도가 가장 바깥이다(안쪽의 구체적인 문구가 먼저 오게). 카드 대조에서는 앱이 가장 먼저 놓는다. 까닭은 둘이다.

- 죽은 연결을 15시간 쥐고 있으면 워커 자리 하나가 그동안 묶인다. 셀은 끊겨도 싸다 — 빨리 놓고 다시 도는 쪽이 낫다.
- ping 이 15초마다 오므로 1,800초는 살아 있는 스트림에 걸리지 않는다(120번을 내리 놓쳐야 한다).

heartbeat 를 끈 박스(`DELIB_HEARTBEAT_S=0`)에서는 요청 하나가 통째로 조용할 수 있다. 그래서 앱은 `/health` 의 `quiet_ok_s` 를 읽어 `effective = max(HWAXRISK_REVIEW_READ_TIMEOUT_S, 2 × quiet_ok_s)` 로 쓴다. 꺼진 박스에서는 21,648초가 되고, 진행 응답에 `○ heartbeat 가 꺼져 있다 — 죽은 연결을 6시간 뒤에야 놓는다` 가 남는다.

#### 3.6.3 사슬 시험에 더할 것

`HWAXPortal/backend/tests/test_time_limit_chain_contract.py` 가 읽을 수 있게 기본값을 지금과 같은 꼴로 적는다 — 에이전트 서버는 `_env_float("CARD_REVIEW_TIMEOUT_S", …)`·`_env_int("CARD_REVIEW_REASK_MAX", 2)`, 리스크 앱은 `config.py` 의 `DEFAULT_REVIEW_CALL_TIMEOUT_S = 14400`·`DEFAULT_REVIEW_READ_TIMEOUT_S = 1800`·`DEFAULT_AIDH_CALL_TIMEOUT_S = 180`.

더하는 단언은 넷이다.

1. (1 + 되묻기) × 논리 호출 < 앱의 카드 대조 벽시계.
2. 앱의 카드 대조 벽시계 + 600 < PAT 등록 하한, 그리고 < chat PAT 최소 잔여.
3. heartbeat × 4 < 앱의 카드 대조 침묵 한도 < 포털 릴레이 침묵 한도.
4. AIDataHub 풀 대기 + 검색 문장 한도 < 앱의 AIDataHub 호출 한도.

### 3.7 자격

- 카드 대조 호출은 호출마다 자격을 다시 고른다(패널과 같은 함수, 여유만 다르다 — `review_credential_margin_s() = effective 벽시계 + 600`). 요청 하나가 수 분이므로 사용자 PAT 는 만료 4시간 10분 전까지 쓰인다(패널은 13시간 10분 전에 끊긴다).
- 포털이 에이전트 서버에 넘기는 chat PAT 는 요청마다 새로 찍힌다(30분 창, 수명 24시간 — 포털 `agent/routes.py:274-320`). 셀 하나는 이 수명과 무관하다.
- 며칠 도는 실행에서 문제가 되는 것은 **등록된 사용자 PAT 가 도중에 끝나는 것**이다. 지금 규칙은 말없이 다음 자격(소유자 → 서비스)으로 내려가고 잡 행에 사유 한 줄을 남긴다. 서비스 계정은 조직 공개 자료만 본다 — 실행의 앞 셀과 뒤 셀이 다른 시야로 돌게 된다.
  - 실행을 만들 때 자격 종류를 `budget_json.credential{kind, email, exp}` 에 적는다. 예상 소요가 남은 수명보다 길면 응답에 `credential_note` 를 싣는다('PAT 가 30시간 남았는데 예상 소요가 54시간이다').
  - 도는 중에 그 자격을 못 쓰게 되면 `HWAXRISK_REVIEW_ON_CRED_CHANGE` 를 따른다. 기본은 `hold` — 실행을 `credential` 로 멈추고 사람에게 알린다. `continue` 면 내려간 자격으로 계속 돌고, 그 뒤의 항목에는 `credential_kind` 가 다르게 적히며 보고서 머리에 '자격이 도중에 바뀌었다' 가 찍힌다(8절).
- 포털이 401·403 을 주면 그 항목은 `pat_unavailable` 이고 실행은 `credential` 로 멈춘다(재시도해도 낫지 않는다).

### 3.8 설정

#### 3.8.1 새 손잡이

리스크 앱 — `HWAXRisk/backend/app/config.py` 의 `Settings` 와 `load_settings`. 전부 코드 기본값으로 돈다.

| 이름 | 기본 | 뜻 | 읽는 곳 |
|---|---|---|---|
| `HWAXRISK_REVIEW_ENABLED` | `0`(시범 뒤 `1` 로 뒤집는다) | 새 흐름을 받는가 | `routes`(409 `review_disabled`) · `review_runner` |
| `HWAXRISK_REVIEW_CONCURRENCY` | 6 | 검토 워커의 천장(실제 수는 게이트가 정한다) | `review_runner` |
| `HWAXRISK_REVIEW_RUNS_PARALLEL` | 1 | 동시에 도는 실행 수 | `review_runner` |
| `HWAXRISK_REVIEW_CALL_TIMEOUT_S` | 14,400 | 요청 하나의 벽시계(0 = 끔) | `engine_client` · `config.review_credential_margin_s` · `main.check_review_chain` |
| `HWAXRISK_REVIEW_READ_TIMEOUT_S` | 1,800 | 카드 대조 스트림의 침묵 한도 | `engine_client` |
| `HWAXRISK_REVIEW_MAX_CHARGED` | 2 | 항목 탓 실패의 상한 | `review_runner.settle` |
| `HWAXRISK_REVIEW_MAX_TRIES` | 20 | 인프라 실패까지 합친 그물 | 〃 |
| `HWAXRISK_REVIEW_ON_CRED_CHANGE` | `hold` | 자격이 도중에 바뀌면 `hold` \| `continue` | `review_runner` |
| `HWAXRISK_REVIEW_CONSENT_CALLS` | 1,500 | 추정 호출 수가 이것을 넘으면 명시 동의를 요구한다 | `routes`(실행 생성) |
| `HWAXRISK_REVIEW_MAX_CALLS` | 30,000 | 이것을 넘는 실행은 거절한다(관리자의 `allow_large` 로만 연다) | 〃 |
| `HWAXRISK_REVIEW_EST_CALL_S` | 300 | 실측이 20건 모이기 전에 쓰는 호출당 초(추정용) | `routes`(추정·남은 시간) |
| `HWAXRISK_REVIEW_ENGINE` | `portal` | `stub` 이면 LLM 없이 정해진 결과를 낸다(시험·리허설 전용 — 5절) | `engine_client.build_review_engine` |
| `HWAXRISK_PACK_FREEZE_CONCURRENCY` | 4 | 카드 묶음을 한 번에 몇 명씩 얼리나(AIDataHub 풀 12 를 심의의 조회 6 과 나눠 쓴다) | 묶음 동결(WP3) |
| `HWAXRISK_PACK_RETAIN_DAYS` | 180 | 쓰이지 않는 카드 묶음을 남기는 날 수 | 유지 틱 |
| `HWAXRISK_AIDH_CALL_TIMEOUT_S` | 180 | AIDataHub REST 호출 하나 | `adh_client` |
| `HWAXRISK_PANEL_AUTORESUME_MAX_S` | 21,600 | 재기동에 끊긴 쟁점 패널을 조건 없이 재개하는 상한 | `review_runner` |

에이전트 서버 — `review_gate.py`(게이트)와 카드 대조 모듈(WP3). 전부 코드 기본값으로 돈다.

| 이름 | 기본 | 뜻 |
|---|---|---|
| `CARD_REVIEW_CONCURRENCY` | 2 | 낮의 동시 수(0 = 낮에는 돌지 않는다) |
| `CARD_REVIEW_CONCURRENCY_NIGHT` | 6 | 밤 창의 동시 수 |
| `CARD_REVIEW_CONCURRENCY_WITH_CHAT` | 2 | 챗·띵킹이 도는 동안의 상한 |
| `CARD_REVIEW_CONCURRENCY_WITH_DELIB` | 2 | 심의가 도는 동안의 상한 |
| `CARD_REVIEW_CONCURRENCY_ON_STALL` | 1 | 챗이 밀린 흔적이 난 뒤의 상한 |
| `CARD_REVIEW_STALL_COOLDOWN_S` | 600 | 그 상한을 유지하는 시간 |
| `CARD_REVIEW_NIGHT_HOURS` | `19-08` | 밤 창(시작 시 포함·끝 시 제외) |
| `CARD_REVIEW_NIGHT_WEEKENDS` | 1 | 토·일은 종일 밤 창으로 본다 |
| `CARD_REVIEW_TZ` | `Asia/Seoul` | 밤 창을 재는 시간대 |
| `CARD_REVIEW_RETRY_AFTER_S` | 30 | 자리 없음 답에 싣는 다시 묻기 간격 |
| `CARD_REVIEW_TIMEOUT_S` | (`DELIB_TIMEOUT_S` 를 따른다) | 카드 대조 LLM 호출 시도 1회 |
| `CARD_REVIEW_REASK_MAX` | 2 | 요청 하나 안에서 되묻는 횟수 |
| `DRAIN_STATE_PATH` | (잡 기록 디렉터리 옆 `drain.json`) | 비우기 깃발 파일 |

update-all 실행의 환경변수 — `HWAX_DRAIN_WAIT_S`(600) · `HWAX_DRAIN_TTL_S`(1,800) · `HWAX_DRAIN_HOLD_S`(3,600). `.env` 에 적는 값이 아니다(`AGENT_RESTART_FORCE` 와 같은 자리).

포털 `infra/.env` 에 더하는 손잡이는 **없다.** 카드 대조 호출은 포털의 챗 자리(`MAX_CONCURRENT_CHATS` 64)를 같이 쓴다 — 워커 천장이 6 이라 그 자리를 채우지 못한다.

#### 3.8.2 매니페스트(두 사본) · 환경 키트 · env-sync

- **`launch.env` 에 새 손잡이를 박지 않는다.** 코드 기본값이 두 박스에서 다 맞게 정해져 있고(박스 차이는 게이트가 받는다), 매니페스트에 박은 키는 호스트의 `APPTAINERENV_*` 를 이겨 박스별로 바꿀 길을 막는다(2.7). `HWAXRISK_PORTAL_BASE` 가 박혀 있는 것은 코드 기본값이 배포 박스에서 틀리기 때문이다 — 그 조건에 드는 새 손잡이는 없다.
- 박스 하나에서만 다르게 돌릴 값(dev 의 `HWAXRISK_REVIEW_ENABLED=1`·`HWAXRISK_REVIEW_ENGINE=stub`)은 그 박스 HEAXHub `.env` 의 `APPTAINERENV_HWAXRISK_…` 로 준다. 들어갔는지는 앱이 말하게 한다(3.9.3 의 `GET /api/meta/runtime`).
- 매니페스트에서 고치는 것은 설명 글뿐이다 — 표 수(41 → 실제 수), MCP 도구 수, 새 흐름 한 줄. 두 사본을 같은 커밋 시각에 맞춘다. `test_manifest.py` 의 `launch.env` 단언은 그대로 통과한다.
- 에이전트 서버 손잡이는 `HWAXPortal/infra/env-kits/agent-server.env` 에 **주석으로** 더한다(지금 '시간 한도' 블록과 같은 꼴 — 설명은 값 줄 위에, 값 줄은 `# KEY=값` 만). 주석 줄은 박스 `.env` 로 옮겨 적히지 않으므로 코드 기본값이 정본이다.
- env-sync(update-all 1c)는 이 꾸러미로 할 일이 없다. 포털 `.env.example` 에 더하는 키가 없고, 에이전트 서버에는 `.env.example` 이 없다(2.8).

### 3.9 박스 차이

#### 3.9.1 무엇이 다른가

| 무엇 | dev | cae00 | 설계가 기대는 것 |
|---|---|---|---|
| 리포 루트 | `~/claude/<Repo>` | `~/Projects/<Repo>` | 스크립트는 제 위치에서 루트를 유도한다. 이 설계가 더하는 경로는 전부 상대다(`drain.json` 은 잡 기록 디렉터리 옆, `runner.lock` 은 데이터 디렉터리 안) |
| LLM | 로컬 vLLM(작은 모델 — 창이 작다) | GLM(128K 급) | 카드 묶음을 몇 조각으로 나눌지는 `/health` 의 `context_tokens` 로 정한다(WP3). dev 에서는 조각이 많아 형식 확인만 한다 |
| 사내 프록시 | 없음 | 있음 — 허브가 프록시 변수를 앱 컨테이너에 물려준다(2.7) | 앱이 루프백 주소(포털·에이전트 서버·AIDataHub·게이트웨이)를 부를 때는 `trust_env=False` 로 프록시를 타지 않는다. 지금은 `NO_PROXY` 에 기대고 있다 |
| AIDataHub 의 전문가·카드 | 원본 | update-all §3 이 dev 덤프로 복원한 사본(늦을 수 있다) | 수를 가정하지 않고 사전 점검이 잰다. 묶음은 실행 머리에서 얼린다 |
| 게이트웨이 도구 | — | SIF 가 낡으면 소스에 있는 도구도 안 뜬다 | 필요한 도구는 게이트웨이에 실제로 물어 확인한다 |
| 재배포 | 5분 스캔이 SIF 만 굽는다(떠 있는 앱은 그대로) | update-all 이 허브째 내렸다 올린다 | 3.5.3 |
| 시간대 | — | — | 밤 창은 `CARD_REVIEW_TZ` 로 잰다(박스 시간대에 기대지 않는다) |

#### 3.9.2 버전이 어긋난 조합

세 리포가 따로 배포된다. cae00 의 update-all 한 번 안에서도 순서는 포털 → 리스크 앱(heax) → AIDataHub → 에이전트 서버다 — 새 리스크 앱이 옛 에이전트 서버를 만나는 몇 분이 반드시 있고, 에이전트 서버 재기동이 심의 때문에 미뤄지면 그 몇 분이 몇 시간이 된다.

| 조합 | 조용히 일어날 일 | 막는 것 |
|---|---|---|
| 새 앱 + 옛 에이전트 서버 | 카드 대조 요청이 평범한 챗으로 처리돼 엉뚱한 글이 온다 | `/health.capabilities` 에 `card_review` 가 없으면 실행을 `agent_outdated` 로 보류. 봉투의 첫 프레임(`hello`)이 없으면 `review_unsupported` |
| 새 앱 + 새 에이전트 서버 + 옛 포털 | 포털이 선언하지 않은 요청 칸을 버린다(`agent/routes.py:209-211` 의 주석이 같은 사고를 적었다) | 같은 `hello` 검사. 에이전트 서버는 능력이 있는데 `hello` 가 없으면 `portal_outdated` 로 적는다 |
| 옛 앱 + 새 에이전트 서버 | 없다(옛 앱은 새 길을 부르지 않는다) | — |
| 새 update-all + 옛 에이전트 서버 | `/drain` 이 404 다 | ○ 한 줄(3.5.3) |

보류는 300초마다 다시 재고 스스로 풀린다. 문구는 어느 쪽이 옛 판인지와 올리는 명령을 말한다.

#### 3.9.3 사전 점검

`GET /api/meta/review-preflight?target_key=…` — 실행을 만들기 전에 화면과 절차서가 부른다. 실행 생성도 안에서 같은 함수를 부르고, `blocking` 이 하나라도 있으면 409 로 그 목록을 돌려준다.

```json
{
  "ok": false,
  "checks": [
    {"key": "review_enabled", "ok": true, "value": "1"},
    {"key": "runner_lock", "ok": true, "value": "held(pid 41233)"},
    {"key": "portal", "ok": true, "value": "200 /health", "base": "http://127.0.0.1:8088"},
    {"key": "agent_server", "ok": true, "value": {"rev": "cr-1", "context_tokens": 128000, "heartbeat_s": 15,
                                                  "request_worst_s": 10824, "limit": 2, "limit_reason": "day", "draining": false}},
    {"key": "portal_forwards_review", "ok": true, "value": "hello 프레임 확인(빈 요청 1회)"},
    {"key": "aidatahub", "ok": true, "value": {"experts": 359, "by_domain": {"xd": 122, "sim": 22}, "cards": 10774,
                                              "cards_per_expert": {"min": 0, "median": 30, "max": 35}, "zero_card_experts": 3}},
    {"key": "roster_vs_aidatahub", "ok": true, "value": {"roster": 359, "missing_in_aidatahub": 0}},
    {"key": "gateway_tools", "ok": false, "severity": "warning", "value": {"required": 7, "present": 6, "missing": ["compare_revisions"]},
     "how": "게이트웨이에 그 도구가 없다 — 근거 꾸러미에서 그 도구의 칸이 '못 돌림' 으로 남는다. HEAXHub 의 앱 SIF 가 낡았는지 본다"},
    {"key": "credential", "ok": true, "value": {"kind": "requester", "expires_in_s": 512000, "margin_s": 15000}},
    {"key": "time_chain", "ok": true, "value": {"call_timeout_s": 14400, "read_timeout_s": 1800, "raised": false}},
    {"key": "disk", "ok": true, "value": {"db_mb": 212, "free_mb": 184000, "backups": 2}}
  ],
  "blocking": [],
  "warnings": ["gateway_tools"]
}
```

- 게이트웨이 도구는 **소스가 아니라 게이트웨이에 물어** 확인한다 — 그 실행의 자격으로 MCP `tools/list` 를 부른다(`McpHttpClient` 에 `list_tools()` 를 더한다). `/tools-map` 은 권한으로 가려진 앱을 구분하지 못한다.
- `portal_forwards_review` 는 실제로 한 번 부른다(본문 없는 탐침 요청 — 에이전트 서버가 `hello` 뒤 곧바로 끝낸다. 게이트 자리를 쓰지 않는다).
- `GET /api/meta/runtime`(관리자) — 지금 걸린 검토 손잡이의 값과 출처(`env`·`default`), `AgentEnv`, 러너 잠금 주인을 준다. 값이 컨테이너에 실제로 들어갔는지 보는 자리다. 비밀은 싣지 않는다.

### 3.10 관측

#### 3.10.1 진행 응답

`GET /api/targets/{key}/review` — 수는 요청 때 표에서 센다(5초 캐시). 잡 행에 계수를 쌓지 않는다(뜨거운 행 하나를 워커 여섯이 고치지 않게 한다). MCP `risk_get_coverage` 응답에도 같은 블록을 `review` 로 싣는다(REST 와 같은 함수).

```json
{
  "target_key": "diff:9f2c…",
  "run": {"job_id": "b1e0…", "state": "running", "stage": "S2", "hold": null,
          "scope": {"domains": null, "tiers": ["A", "B"], "unit_ids": null, "window": "any"},
          "credential": {"kind": "requester", "email": "user@example.com", "expires_in_s": 512000},
          "created_at": 1791500000, "started_at": 1791500100},
  "stages": [
    {"stage": "S0", "label": "검토 단위·근거 꾸러미", "state": "done", "units": 12, "evidence_gaps": 1},
    {"stage": "S0b", "label": "카드 묶음 동결", "state": "done", "agents": 359, "packs": 356, "no_cards": 3},
    {"stage": "S1", "label": "전수 훑기", "state": "done", "done": 359, "total": 359},
    {"stage": "S2", "label": "카드 대조", "state": "running", "done": 812, "total": 1436, "running": 2, "failed": 3},
    {"stage": "S3", "label": "검증·표본 재질의", "state": "waiting"},
    {"stage": "S4", "label": "교차·메커니즘", "state": "waiting"},
    {"stage": "S5", "label": "쟁점 토의", "state": "waiting"},
    {"stage": "S6", "label": "보고서", "state": "waiting"}
  ],
  "cells": {"total": 4308,
            "by_status": {"pending": 624, "running": 2, "reviewed": 805, "na_irrelevant": 2760, "no_input": 110,
                          "failed": 3, "skipped": 0, "carried": 4},
            "by_domain": {"mech": {"total": 228, "reviewed": 120, "na_irrelevant": 60, "pending": 46, "failed": 2}}},
  "failures": {"by_code": {"review_incomplete": 2, "llm_timeout": 1},
               "retries": {"agent_unreachable": 4, "engine_stream_cut": 2},
               "waits": {"review_busy": 131, "engine_busy": 0}},
  "usage": {"llm_calls": 1203, "tokens_in": 61200000, "tokens_out": 3100000, "tokens_unknown_calls": 0,
            "truncated": 2, "call_s": {"p50": 212, "p95": 640, "n": 812}},
  "quality": {"cards_judged": 24100, "cards_expected": 24130, "quote_verified_rate": 0.93,
              "flip_rate": {"value": 0.04, "n": 120}, "na_miss_rate": {"value": 0.0, "n": 59}},
  "budget": {"llm_calls_cap": 4000, "llm_calls_used": 1203, "consented_by": "user@example.com"},
  "gate": {"limit": 2, "limit_reason": "day", "active": 2, "draining": false, "agent": "ok", "seen_at": 1791586000},
  "waiting": null,
  "running": [{"grid": "cell", "unit_id": "u-3a1…", "agent_key": "mech-ip-sealing", "started_at": 1791585900,
               "last_frame_at": 1791585995, "last_step": "카드 대조 2/2"}],
  "eta": {"remaining_calls": 624, "at_current_limit_s": 66144, "basis": "p50 212초 × 624 ÷ 2", "measured": true},
  "notes": [{"mark": "○", "code": "evidence_tool_missing", "n": 1, "first_at": 1791500200, "last_at": 1791500200,
             "text": "근거 꾸러미에서 compare_revisions 를 돌리지 못했다 — 게이트웨이에 그 도구가 없다",
             "how": "HEAXHub 의 앱 SIF 를 새로 받은 뒤 그 단위의 근거 꾸러미를 다시 만든다"}]
}
```

- `flip_rate`(뒤집힘률) = 재질의한 판정 가운데 바뀐 수 ÷ 재질의한 수(`rr_card_verdicts.audit_flipped`). `na_miss_rate`(놓침률) = 다시 본 '해당 없음' 셀 가운데 뒤집힌 수 ÷ 다시 본 수(`rr_review_cells.audit_result`). 표본이 없으면 `value` 는 `null` 이고 `n` 은 0 이다.
- `running` 의 마지막 신호는 러너가 메모리에 갖고, 60초마다 `rr_jobs.progress_json` 에 적는다(잠금을 못 쥔 프로세스가 답할 때는 그 값을 쓴다).
- `notes` 는 `rr_jobs.notes_json` 이다. 같은 코드는 한 줄로 합치고 건수와 처음·마지막 시각을 둔다. 200줄을 넘으면 가장 오래된 것부터 버리고 버린 수를 맨 끝 줄에 적는다.

#### 3.10.2 호출 원장 `rr_review_calls`

- 끝난 호출마다 한 행이다(성공·오류·절단·시간 초과). '자리 없음' 과 포털 429 는 행으로 적지 않고 진행 응답의 `waits` 에 센다(며칠 동안 30초마다 쌓이면 표가 그것으로 찬다).
- 실패 사유 분포·호출 시간 분위·토큰 합·차단기의 창(최근 20건)이 전부 이 표의 SQL 이다.
- 원출력 전문(`output_gz`)을 남긴다. 파서를 고친 뒤 LLM 을 다시 부르지 않고 다시 풀 수 있다.
- 토큰은 에이전트 서버가 LLM 응답에서 읽은 값이다. 못 읽으면 `NULL` 이고 `chars_in` 은 앱이 센 값이라 늘 있다.

#### 3.10.3 `metrics.py` 에 더할 것

`recompute()` 안에 `_review_rows(rows, store)` 를 더한다(이번 계산에 없는 자리는 `_drop_stale` 이 지우므로 반드시 이 함수 안에서 낸다). 차원은 지금 CHECK 의 여섯 안에서 쓴다 — 타깃 차원이 없으므로 타깃별 값은 진행 응답이 내고, 여기는 과제·영역·전문가·전체로 모은다.

| 지표 | 차원 | 값 | 최소 n |
|---|---|---|---|
| `review_cell_reviewed_ratio` | project · domain · global | `reviewed` ÷ (전체 − `no_input`) | 1 |
| `review_cell_na_ratio` | project · domain · global | `na_irrelevant` ÷ 전체 | 1 |
| `review_cell_no_input_ratio` | project · domain · global | `no_input` ÷ 전체 | 1 |
| `review_cell_failed_ratio` | project · global | (`failed` + `skipped`) ÷ 전체 | 1 |
| `review_cards_judged_ratio` | expert · domain · global | Σ `cards_judged` ÷ Σ `cards_expected` | 1 |
| `review_quote_verified_rate` | expert · domain · global | Σ `quote_verified_n` ÷ Σ `quote_total_n` | 5 |
| `review_flip_rate` | expert · domain · global | 3.10.1 의 뒤집힘률 | 20 |
| `review_na_miss_rate` | domain · global | 3.10.1 의 놓침률 | 20 |
| `review_call_s_p50` · `review_call_s_p95` | global · `@model=<이름>` 접미 | `rr_review_calls.elapsed_ms` 의 분위 | 20 |
| `review_tokens_in_per_call` · `review_tokens_out_per_call` | global · `@model=` 접미 | 평균(모르는 호출은 뺀다) | 20 |
| `review_infra_retry_ratio` | global | 인프라 실패 호출 ÷ 끝난 호출 | 20 |
| `review_truncated_ratio` | global · `@model=` 접미 | 잘린 호출 ÷ 성공 호출 | 20 |

`MIN_N` 에 위 최소 n 을 더한다(미달이면 값은 비우고 n 만 남는다 — 지금 규칙).

지표가 자동으로 다시 계산되는 길이 지금 없다(2.2). 이 꾸러미는 `sync_loop` 에 **유지 틱**을 더한다 — 한 시간에 한 번 사본 정리(3.2.5)·쓰이지 않는 카드 묶음 정리, 하루에 한 번 `metrics.recompute`. 야간 잡 전체(패턴 채굴·큐레이션 큐)를 배선하는 것은 범위 밖이다(7절 WP1 에 넘긴다).

#### 3.10.4 로그 문구

로거는 `hwax_risk.review` 다. 머리는 `[review <job 8자>]` 이고 표식은 update-all 과 같다 — `✓` 됐다 · `✗` 실패 · `⚠` 경고 · `○` 건너뛰었거나 기다린다(사유와 '켜려면' 을 같이 적는다).

| 때 | 문구 |
|---|---|
| 실행 시작 | `[review b1e0a2c4] 시작 — 타깃 diff:9f2c… · 전문가 359 · 단위 12 · 추정 호출 1,436~4,308 · 자격 requester(남은 142시간) · 워커 천장 6` |
| 단계 넘어감 | `[review b1e0a2c4] ✓ S1 전수 훑기 끝 — 359/359 · 대조로 보낸 셀 1,436 · 해당 없음 2,760 · 입력 없음 110 · 31분` |
| 한 시간마다 | `[review b1e0a2c4] S2 812/1,436 · 실패 3 · 다시 돈 것 6 · 호출 p50 212초 · 지금 상한 2(day) · 남은 시간 약 18.4시간` |
| 기다림 | `[review b1e0a2c4] ○ 기다린다 — 비우는 중(update-all · 14:02 부터 · 14:32 에 풀린다)` |
| 기다림 | `[review b1e0a2c4] ○ 기다린다 — 밤 전용으로 청한 실행이다(19시부터 돈다). 낮에도 돌리려면 범위의 window 를 any 로 바꾼다` |
| 건너뜀 | `[review b1e0a2c4] ○ 근거 꾸러미에서 compare_revisions 를 돌리지 못했다 — 게이트웨이에 그 도구가 없다. 켜려면: HEAXHub 의 앱 SIF 를 새로 받는다` |
| 항목 다시 | `[review b1e0a2c4] u-3a1…×mech-ip-sealing 다시 — agent_unreachable(차감 없음, 3번째, 120초 뒤)` |
| 항목 실패 | `[review b1e0a2c4] ✗ u-3a1…×mech-ip-sealing 실패 — review_incomplete(카드 31장 중 29장만 판정, 2번 차감). 사람이 다시 또는 넘김을 정한다` |
| 보류 | `[review b1e0a2c4] ⚠ 멈췄다(llm_outage) — 최근 20건 중 12건이 LLM 연결 실패다. 300초 뒤 항목 하나로 다시 잰다` |
| 보류 | `[review b1e0a2c4] ⚠ 멈췄다(agent_outdated) — 에이전트 서버가 카드 대조를 모른다(/health 에 card_review 가 없다). 올리려면: 포털 리포에서 ./infra/scripts/update-sites.sh agent-server` |
| 올려 씀 | `[review b1e0a2c4] ○ 호출 벽시계를 14,400 → 21,924초로 올려 쓴다 — 에이전트 서버의 요청 최악이 21,624초다(CARD_REVIEW_TIMEOUT_S 3600)` |
| 자격 | `[review b1e0a2c4] ⚠ 멈췄다(credential) — user@example.com 의 PAT 가 4.1시간 남아 더 쓰지 못한다. 포털에서 다시 발급해 등록하고 재개한다` |
| 끝 | `[review b1e0a2c4] ✓ 끝 — 셀 4,308(검토 1,402 · 해당 없음 2,760 · 입력 없음 110 · 넘김 2 · 승계 34) · 호출 1,611 · 입력 8,210만 토큰 · 38.4시간` |

### 3.11 비용 통제

#### 3.11.1 추정 → 동의 → 상한

실행 생성은 지금의 `POST /api/targets/{key}/jobs` 에 `mode` 를 더해 받는다.

```json
{
  "mode": "reviews",
  "scope": {"domains": ["mech", "rf", "pwr"], "tiers": ["A"], "unit_ids": null, "unit_kinds": null,
            "stages": ["S0", "S0b", "S1", "S2", "S3"], "window": "night_only", "max_cells": null},
  "user_memo": "…",
  "consent": false,
  "dry_run": true
}
```

`dry_run` 이면 아무것도 만들지 않고 추정만 돌려준다.

```json
{
  "estimate": {
    "experts": 15, "units": {"known": false, "assumed": 12},
    "cells_grid": 180,
    "llm_calls": {"low": 195, "high": 429, "by_stage": {"S1": 15, "S2": {"low": 180, "high": 360}, "S3": {"low": 0, "high": 54}}},
    "tokens_in": {"low": 3900000, "high": 28000000},
    "wall_s": {"at_day_limit": 64350, "at_night_limit": 21450, "call_s": 300, "measured": false},
    "basis": "단위 수는 아직 모른다(가정 12). S0 이 끝나면 다시 센다. 호출당 300초는 가정이다"
  },
  "gate": {"consent_required": false, "consent_threshold_calls": 1500, "max_calls": 30000},
  "credential": {"kind": "requester", "email": "user@example.com", "expires_in_s": 512000},
  "credential_note": null,
  "preflight": {"ok": true, "blocking": [], "warnings": ["gateway_tools"]}
}
```

- 추정 호출 수의 위쪽 끝이 `HWAXRISK_REVIEW_CONSENT_CALLS` 를 넘으면 `consent:true` 가 있어야 만든다(지금 Tier C 의 동의와 같은 자리). `HWAXRISK_REVIEW_MAX_CALLS` 를 넘으면 409 `review_too_large` 이고 범위를 줄이라는 문구가 온다. 관리자가 `allow_large:true` 로만 연다(`model_too_large` 와 같은 관례).
- 만들 때 `budget_json = {estimate, llm_calls_cap, cells_cap, consented_by, consented_at, credential}` 을 적는다. `llm_calls_cap` 은 동의한 위쪽 끝 × 1.25 다(되묻기·표본의 여유).
- **두 번 잰다.** 만들 때는 단위 수를 모른다. S0(단위)과 S0b(묶음)가 끝나면 정확한 위쪽 끝을 다시 세고, 그것이 상한을 넘으면 실행을 `budget` 으로 멈춘다('단위가 12 가 아니라 31 이다 — 추정 호출이 429 에서 1,108 로 올랐다').
- 도는 중에 쓴 호출 수(`rr_review_calls` 의 행 수)가 상한에 닿아도 `budget` 으로 멈춘다. 되묻기가 끝없이 도는 고장의 그물이다.
- 상한 고치기 — `PUT /api/jobs/{id}/budget {"llm_calls_cap": 2000, "reason": "…"}`(소유자·관리자, `rr_audit` 에 `job.budget` 한 행).

#### 3.11.2 사람이 범위를 고르는 손잡이

| `scope` 의 칸 | 뜻 | 기본 |
|---|---|---|
| `domains` | 돌릴 영역(로스터의 영역 키) | 전부 |
| `tiers` | 어느 Tier 까지 — 실행 순서도 이 순서다(A 먼저) | `["A","B","C"]` |
| `unit_ids` · `unit_kinds` | 돌릴 검토 단위 | 전부(`excluded` 제외) |
| `stages` | 어느 단계까지 | 전부 |
| `window` | `any` \| `night_only` | `any` |
| `max_cells` | 격자 셀 수의 상한(넘으면 만들 때 409) | 없음 |

범위 밖의 셀은 **만들지 않는다**(만들고 '해당 없음' 으로 닫지 않는다 — 안 본 것과 관련 없는 것이 섞인다). 진행 응답은 범위 밖의 수를 `out_of_scope` 로 따로 준다. 범위를 넓히는 것은 같은 타깃에 새 실행을 만드는 것이고, 이미 종결된 셀은 다시 돌지 않는다(PK 가 같다).

`tiers:["A"]` 로 먼저 도는 것이 시범의 꼴이다 — 대표 15명이 전 단위를 돌아 호출 시간·토큰·놓침률을 잰 뒤 나머지를 연다.

#### 3.11.3 정지 · 재개 · 취소 · 사람의 처분

| 조작 | 길 | 도는 항목 | 그 뒤 |
|---|---|---|---|
| 정지 | `POST /api/jobs/{id}/pause`(지금 것) | 끝까지 간다(셀은 수 분 — 끊으면 버려진다). 새 항목은 집지 않는다 | `paused`, `pause_reason='user'` |
| 재개 | `POST /api/jobs/{id}/resume`(지금 것) | — | `queued` → 첫 틱에 이어 돈다. `hold_code`·`hold_n` 을 지운다 |
| 취소 | `POST /api/jobs/{id}/cancel`(지금 것) | 스트림을 닫는다(`should_stop` — 패널과 같은 방식). 항목은 `pending` 으로 돌아간다 | `cancelling` → `cancelled`. 종결된 셀은 남는다 |
| 실패한 항목 다시 | `POST /api/targets/{key}/cells/retry {"grid":"cell","keys":[…]}` | — | `pending`, `charged=0`, `rr_audit` 한 행 |
| 실패한 항목 넘김 | `PUT /api/targets/{key}/cells/skip {"grid":"cell","keys":[…],"reason":"…"}` | — | `skipped`, `status_source='human'`, 사유 필수, `rr_audit` 한 행 |

쟁점 패널이 도는 중의 정지·취소는 지금 패널 규칙 그대로다(스트림을 닫는다).

### 3.12 문서

| 파일 | 무엇을 |
|---|---|
| `HWAXPortal/docs/design-risk-review/review-ops.md`(새 파일) | **서버 절차서.** 사람이 정하는 것만 적는다 — ① 실행 전 확인(명령과 기대 출력: `/health` 의 새 칸, 사전 점검, 러너 잠금, 디스크) ② 시범 실행 순서 ③ 낮·밤 상한을 바꾸는 법 ④ 비우기(`review-drain.sh`)와 update-all 의 새 줄 읽는 법 ⑤ 멈춘 실행을 푸는 법(보류 코드 표) ⑥ 되돌리기 네 단 ⑦ 아직 안 된 것. 줄 번호를 적지 않고 화면에 찍히는 문구로 가리킨다. 박스 상태는 적지 않고 재는 명령을 적는다. 머리에 대조한 커밋과 날짜를 박는다 |
| `HWAXPortal/docs/change-request-8-10/server-setup.md` §4-8 | 3.6.1 의 줄을 표에 더한다. §4-0 의 '미룬다' 문단에 `review_active` 는 미루는 까닭이 아니라는 것과 비우기를 적는다. §6 에서 '프로세스 잠금'·'heax 의 앱 교체' 두 줄을 고친 대로 바꾼다 |
| `HWAXPortal/infra/env-kits/agent-server.env` | 3.8.1 의 에이전트 서버 손잡이를 주석 블록으로 |
| `HWAXPortal/infra/scripts/update-all.sh` 머리 주석 | `HWAX_DRAIN_*` 셋 |
| `HWAXPortal/backend/config/changelog.yaml` | 사용자가 겪는 변화로 한 덩이(`tag: 심의`) — 예: `"리스크 심사가 며칠 돌아도 **업데이트를 막지 않습니다.** 도는 카드 대조는 잠깐 쉬었다가 스스로 이어 돕니다."` · `"심사가 도는 동안에도 챗이 밀리지 않게, 카드 대조는 낮에 2건·밤에 6건까지만 한꺼번에 돕니다."` · `"진행 화면이 몇 번째 단계의 몇 건째인지, 왜 기다리는지를 알려 줍니다."`. items 는 큰따옴표로 감싼다 |
| `HWAXPortal/CLAUDE.md` 문서 표 | '설계 리스크 심사' 줄에 `review-ops.md`(재설계 운영 — 비우기·낮밤 상한·보류 코드)를 더한다 |
| `HWAXPortal/docs/cae00-deploy-guide.md` | 날짜 박은 '반영분' 절 — update-all 의 새 줄(1f)과 `○` 둘, 처음 한 번 볼 것 |
| `HWAXPortal/docs/design-risk-review/context-notes.md` · `HWAXRisk/context-notes.md` | 결정 기록 — 셀은 지키지 않고 패널만 지킨다 · 게이트는 줄을 세우지 않는다 · 침묵 한도의 순서를 카드 대조에서만 뒤집은 까닭 · 어휘에 CHECK 를 걸지 않는 까닭 · v3 를 한 번에 넣은 까닭 |
| `HWAXRisk/README.md` | 손잡이 표와 `GET /api/meta/runtime` |

### 3.13 프롬프트

이 꾸러미에는 LLM 프롬프트가 없다. 차단기의 탐침도 실제 항목 하나를 돌리는 것이다(3.3.5). 사람에게 가는 글은 3.10.4 의 문구가 전부다.

---

## 4. 커밋 단위로 쪼갠 작업 순서

리포 머리글자는 R = HWAXRisk, A = HWAXAgentServer, P = HWAXPortal, H = HEAXHub 다. 프런트 파일은 건드리지도 스테이징하지도 않는다.
R1·R2·R3·R10·A1·A2·P2 는 새 흐름과 무관하게 **지금 구조에도 이득**이라 먼저 넣을 수 있다.

| # | 커밋 | 선행 | 바뀌는 파일 | 검증 |
|---|---|---|---|---|
| R1 | `fix(health)` 헬스가 저장소 락을 잡지 않는다 · 연결에 busy_timeout 30초 | 없음 | `main.py` · `risk_store.py` · `tests/test_boot.py` | 다른 스레드가 `store.tx()` 를 쥔 채 `/api/health` 를 불러 200ms 안에 200 이 오는지. 고치기 전에는 이 시험이 걸려 멈춘다는 것을 먼저 본다 |
| R2 | `feat(runner)` 데이터 디렉터리 잠금 — 쥔 프로세스만 러너와 복구를 돈다 | 없음 | `runlock.py`(새) · `runner.py` · `main.py` · `tests/test_runlock.py` | 실제 프로세스 둘을 같은 디렉터리로 띄워 둘째가 `running` 패널을 건드리지 않는지 · 첫째를 죽이면 둘째가 이어받는지(재시도 간격을 줄여서) · `/api/health` 의 `runner_lock_held` |
| R3 | `feat(store)` 이행 규약의 시험과 사본 정리 | 없음 | `risk_store.py`(`prune_backups`) · `tests/test_store.py` | v1·v2 의 DDL 해시 고정 · 전 버전 표의 `owner_sub`·PK 규약 · `pre-migrate-*`·`pre-merge-*` 를 셋씩 만들어 둘만 남는지 |
| R4 | `feat(schema v3)` 새 표 여덟 · 기존 표의 열 · 반출·폐기 배선 | R3 · 7절의 열 합의 | `risk_store.py` · `export.py` · `routes.py`(`PURGE_BLANK_SQL`·`purge_project`) · `tests/test_store.py` · `tests/test_export_import.py` | 행이 든 v2 DB 를 v3 로 올려 옛 행이 그대로인지 · 사본이 하나 생기는지 · 새 표 전부에 한 행씩 넣고 반출 → 빈 DB 에 들여와 행 수와 해시가 같은지(BLOB 포함) · 폐기 뒤 원문 열이 비는지 · 옛 `claim_next_job` 시험 전부 통과 |
| R5 | `feat(config)` 검토 손잡이 · 기동 검사 · `GET /api/meta/runtime` · 매니페스트 설명 | R4 | `config.py` · `main.py` · `routes.py` · `.portal/manifest.yaml` · `tests/test_boot.py` · `tests/test_manifest.py` | 손잡이마다 기본값·덮어쓰기 · `check_review_chain` 이 뒤집힌 값에서 기동을 막는지 · 매니페스트 시험 통과(`launch.env` 는 그대로 둘) |
| H1 | `chore(hwax-risk)` 등록 사본을 앱 리포의 것과 같게 | R5 와 같은 날 | `integrations/hwax-risk/.portal/manifest.yaml` | 두 파일의 `diff` 가 비는지 |
| A1 | `feat(review gate)` 게이트·비우기 깃발(순수 로직) | 없음 | `review_gate.py`(새) · `tests/test_review_gate.py` | `limit_for` 의 표(낮·밤·주말·자정 넘김·챗·심의·밀림·비우기) · `try_acquire` 가 상한에서 `Busy` 를 내는지 · `release` 누락 없이 자리가 돌아오는지 · 깃발의 수명·고정·파일 복원 |
| A2 | `feat(health·drain)` `/health` 의 새 칸 · `POST/GET /drain` · 챗·밀림 계수 · `start.sh` 한 줄 | A1 | `app.py` · `start.sh` · `tests/test_health_contract.py`(새) | `delib_active`·`delib_queued` 가 최상위에 그대로인지 · `start.sh` 의 `grep` 식이 새 응답에서 같은 수를 읽는지(응답 문자열을 실제로 그 식에 넣는다) · 깃발을 세운 뒤 `review_active` 만 있는 서버는 `start.sh` 가 재기동하는지 |
| A3 | (WP3) 카드 대조 모듈이 3.4.4 의 봉투를 지킨다 | A2 | WP3 의 파일 · `tests/test_card_review_ops_contract.py`(이 꾸러미가 뼈대를 준다) | 5.2 의 여섯 단언 |
| P1 | `feat(update-all)` 비우기 — 함수 셋 · 1f 절 · 끝맺음 · `review-drain.sh` | A2 | `infra/scripts/lib/delib-busy.sh` · `update-all.sh` · `review-drain.sh`(새) · `backend/tests/test_update_all_delib_restart_gate.py` | 가짜 `/health`·`/drain` 서버로 — 깃발을 세우고 내리는 호출이 기록되는지 · 옛 판(404)에서 ○ 가 찍히는지 · 셀이 남으면 한도 뒤에 가는지 · 미룬 재기동이 있으면 깃발을 남기는지 · `hwax_delib_busy` 의 기존 시험 전부 통과 |
| P2 | `fix(deploy-all)` heax 블록도 심의를 묻는다(`dist-from-drive` 앞) | 없음 | `deploy-all-from-drive.sh` · 같은 시험 파일 | 지금 있는 `test_deploy_all_의_포털과_nginx_재기동은_전부_심의를_묻고_난_뒤다` 와 같은 꼴로 heax 를 더한다(물음이 `dist-from-drive` 줄보다 앞인지를 소스에서 본다) |
| R6 | `feat(review runner)` 검토 루프 — 집기·분류·백오프·차단기·보류·자동 재개·복구 · 가짜 엔진 | R2 · R4 · R5 | `review_runner.py`(새) · `runner.py`(`RiskRunner` 배선, `claim_next_job` 의 `mode`·비우기) · `engine_client.py`(`build_review_engine`·가짜 엔진·전송부의 오류 분류) · `tests/test_review_runner.py` | 5.1 · 5.3 |
| R7 | `feat(routes)` 실행 생성(추정·동의·범위) · 진행 응답 · 사전 점검 · 항목 다시·넘김 · 상한 고치기 | R6 | `routes.py` · `mcp_server.py`(`risk_get_coverage` 에 `review`) · `ra_client.py`(`list_tools`) · `tests/test_review_routes.py` · `tests/test_mcp_tools.py` | 추정의 산술 · 동의 문턱 · 범위 밖 셀이 만들어지지 않는지 · 진행 응답의 수가 표와 같은지 · 사람 조작이 `rr_audit` 에 남는지 |
| R8 | `feat(panels)` 재기동에 끊긴 쟁점 패널의 자동 재개 | R6 · WP4 의 패널 잡 | `review_runner.py` · `tests/test_review_runner.py` | `delib_active` 가 0 이 아닐 때는 그대로, 0 이 되면 재개, 상한을 넘기면 조건 없이 재개 |
| R9 | `feat(metrics·유지)` 검토 지표 · 모델 귀속 · 유지 틱 | R6 | `metrics.py` · `learning.py` · `nightly.py`(`STAMP_KEYS`) · `runner.py`(`sync_loop`) · `tests/test_metrics.py` | 셀·호출을 손으로 심어 각 지표의 값과 n · 최소 n 미달이면 값이 비는지 · 다시 계산해도 옛 자리가 남지 않는지 |
| R10 | `fix(net)` 루프백 주소는 프록시를 타지 않는다 | 없음 | `engine_client.py` · `adh_client.py` · `ra_client.py` · `identity.py` 의 클라이언트 생성부 · 시험 | `HTTP_PROXY` 를 죽은 주소로 준 환경에서 루프백 호출이 그대로 되는지(실제 소켓으로) |
| P3 | `test(시간 한도 사슬)` 카드 대조의 줄을 사슬에 넣는다 | A3 · R5 | `backend/tests/test_time_limit_chain_contract.py` | 3.6.3 의 단언 넷. 값을 못 찾으면 건너뛰지 않고 실패한다(지금 규칙) |
| P4 | `docs` 절차서 · 시간 한도 표 · 키트 · changelog · CLAUDE.md | 전부 | 3.12 의 파일 | `test_changelog.py` · 절차서의 명령을 dev 에서 하나씩 실제로 돌려 출력과 맞춘다 |
| R11 | `feat(review)` 기본값을 켠다(`HWAXRISK_REVIEW_ENABLED` 의 기본을 1 로) | 5.4 의 시범 통과 · 사용자 승인 | `config.py` · 시험 · 절차서 | 시범 결과표 |

배포 순서는 AIDataHub(WP3 의 조회 인자) → 에이전트 서버(A1·A2·A3) → 포털(WP3 의 요청 칸·P1·P2) → 리스크 앱이다. 순서가 틀려도 조용히 틀어지지 않는다(3.9.2).

커밋할 때는 그 리포의 `git status` 를 자르지 않고 전부 본다(여러 세션이 같은 리포를 쓴다).

---

## 5. 시험

### 5.1 단위

| 대상 | 단언 |
|---|---|
| 이행 | v2 → v3 가 한 트랜잭션이다(가운데 문장을 깨뜨리면 버전이 2 로 남고 표가 하나도 생기지 않는다) · 다시 열어도 사본이 늘지 않는다 · 코드보다 높은 버전은 기동을 막는다(지금 시험 유지) |
| 표 규약 | 전 버전의 `rr_*` 표가 `owner_sub` 를 갖거나 공용 표 넷 중 하나다 · 전부 PK 가 있다 · v3 의 표에 `CHECK(` 가 없다 |
| 반출 | 새 표가 `TABLE_ORDER` 에 부모 → 자식 순서로 있다 · `_SINCE_COLS` 에 새 표가 빠짐없이 있다(없으면 실패 — 빠지면 `since` 가 조용히 무시된다) |
| `claim_next` | 워커 여덟이 같은 항목 풀을 동시에 집어도 한 항목은 한 번만 집힌다 · `not_before` 가 지나지 않은 것은 건너뛴다 · 순서(실행 → 단계 → 우선 → PK) |
| `settle` | 3.3.4 의 줄마다 — 부류, `charged`·`tries`·`infra_streak` 의 변화, 다음 상태, `not_before`. 모르는 코드는 내용 실패로 세고 원문이 남는다 |
| 백오프 | 1 → 30초, 6 이상 → 900초, 흩뿌림 ±20% 안 |
| 차단기 | 최근 20건 중 인프라 10건에서 보류 · 탐침은 한 건만 나간다 · 성공하면 풀리고 `hold_n` 이 0 이 된다 |
| 보류 | 코드마다 자동 재개 여부와 간격 · 기다림(비우기·밤 창·자리 없음)이 실행을 `paused` 로 만들지 않는다 |
| `recover` | 남의 `lease_owner` 는 `pending` 으로(차감 없음), 내 것은 그대로 |
| `limit_for` | 낮 2 · 밤 6 · 금요일 23시(밤) · 토요일 13시(주말) · 07:59 와 08:00 · 챗이 돌면 2 · 밀린 직후 1 · 비우기 0 · 시간대가 UTC 인 박스에서도 서울 기준 |
| 게이트 | 상한까지 받고 그다음은 `Busy`(기다리지 않는다) · 예외로 끝난 호출도 자리를 돌려준다 · 상한이 도는 중에 내려가면 도는 것은 두고 새것만 막는다 |
| 깃발 | 수명 뒤 스스로 풀린다 · 고정은 안 풀린다 · 파일에서 되살아난다 · 깨진 파일은 '없음' 으로 읽고 지운다 |
| 셸 | `hwax_review_state` 가 새 판·옛 판·죽은 서버·매달린 서버를 0·3·2·4 로 가른다 · 운영자 셸의 프록시를 타지 않는다 · `hwax_delib_busy` 의 출력이 새 `/health` 에서 종전과 글자까지 같다 |
| 추정 | 전문가·단위·조각 수에서 호출 수의 아래·위 · 동의 문턱 · 두 번째 재기에서 상한을 넘으면 `budget` |

### 5.2 봉투 계약(에이전트 서버 — WP3 의 모듈이 통과해야 한다)

가짜 LLM 으로 돌린다(`test_thinking.py` 의 방식).

1. 도는 카드 대조 호출이 있어도 `/health` 의 `delib_active` 는 0 이고 `review_active` 는 1 이다.
2. 구독을 끊으면 LLM 호출 태스크가 취소되고 `review_active` 가 0 으로 돌아온다(실제 `asyncio` 태스크의 `cancelled()` 를 본다).
3. 자리가 없을 때의 응답은 1초 안에 끝나고 `hello` → `error(review_busy, retry_after_s)` → `done` 순서다.
4. LLM 이 heartbeat 의 세 배만큼 조용하면 그 사이에 `ping` 이 둘 이상 온다.
5. 첫 프레임은 늘 `hello` 다(성공·실패·자리 없음 모두).
6. 끝 프레임의 `usage` — 토큰을 주는 가짜 LLM 에서는 수가, 안 주는 가짜 LLM 에서는 `null` 이 온다(0 이 아니다).

### 5.3 통합 — 가짜 엔진으로 며칠을 몇 분에 돈다

`HWAXRISK_REVIEW_ENGINE=stub` 의 가짜 엔진은 LLM 없이 정해진 결과를 내고, 씨앗으로 실패를 섞는다(인프라 15% · 내용 3% · 자리 없음 10% · 시간 초과 1%). 호출 시간은 밀리초로 줄인다.

| 시나리오 | 단언 |
|---|---|
| 셀 2,000개(전문가 100 × 단위 20)를 끝까지 | 전부 종결이거나 `failed` 이고 `pending`·`running` 이 0 · 성공 행이 셀마다 하나(`rr_review_calls` 에서 같은 셀·같은 조각의 `ok` 가 둘 이상이면 실패) · 인프라 실패가 `charged` 를 올리지 않았다 · 동시 실행 수가 `min(천장, 게이트 상한)` 을 한 번도 넘지 않았다(가짜 엔진이 최댓값을 잰다) |
| 가운데서 러너를 버리고 같은 DB 에 새 러너를 띄운다(세 번) | 위와 같다. 재기동 전의 `running` 은 전부 차감 없이 다시 돌았다 |
| 가운데서 비우기를 세웠다 내린다 | 세운 시각 뒤로 새로 시작한 호출이 없다(`started_at`) · 내린 뒤 이어 돈다 · 실행은 그동안 `running` 이다 |
| LLM 이 20건 연속 죽는다 | `llm_outage` 로 멈춘다 · 그 뒤 창마다 호출이 한 건씩만 나간다 · 살아나면 스스로 풀린다 · 그동안 `tries` 가 20 을 넘긴 항목이 없다 |
| 에이전트 서버가 옛 판이다(가짜 `/health` 에 능력 없음) | 호출이 한 건도 나가지 않고 `agent_outdated` · 능력이 생기면 300초(줄인 값) 안에 풀린다 |
| 자격이 가운데서 끝난다 | 기본(`hold`)에서 `credential` 로 멈춘다 · `continue` 에서는 뒤 항목의 `credential_kind` 가 바뀌고 `notes` 에 한 줄 |
| 쓴 호출이 상한에 닿는다 | `budget` 으로 멈춘다 · 상한을 올리면 이어 돈다 |
| 검토 실행과 Tier 잡을 같은 타깃에 | 뒤에 온 쪽이 409 다(양쪽 순서 다) |
| 과제를 폐기한다(도는 중) | 실행은 취소되고 남은 항목은 `skipped(project_purged)` · 원문 열이 빈다 · 반출에 그 과제가 없다 |

### 5.4 실주행

dev 에는 변경이 여러 건인 실제 diff 가 없다(자기 자신과 견준 빈 건뿐이다). 넘는 길은 넷이고, 무엇을 무엇으로 확인하는지를 가른다.

| 무엇을 확인하나 | 어디서 · 무엇으로 |
|---|---|
| 러너·게이트·비우기·복구의 **운영 동작** | dev — 가짜 엔진. diff 가 필요 없다. 합성 타깃(전문가 100 × 단위 20)을 시험 픽스처 생성기로 **임시 데이터 디렉터리**에 심는다(`HWAXRISK_DATA_DIR` 을 scratch 로 준 임시 앱 — 실 DB 를 건드리지 않는다) |
| 봉투·배선이 **실제 LLM 과 포털을 지나** 도는가 | dev — 합성 diff(이벤트 수십 건을 조립 단위 서넛에 흩은 픽스처, WP2 가 만든다)를 임시 데이터 디렉터리에 들여와 전문가 2명 × 단위 1개. dev 모델은 창이 작아 판정의 질은 보지 않는다. 형식·조각 나누기·토큰 계수·ping 만 본다 |
| 판정의 **양과 시간**(호출당 초 · 글자당 토큰 · 잘림 · 놓침률) | cae00 — 실제 리비전 쌍이 있는 타깃 하나에 `tiers:["A"]`·`window:"night_only"` 로 대표 15명. 예산 게이트가 호출 수를 묶는다 |
| 심사가 도는 동안 **챗이 밀리는가** | cae00 — 위 시범 동안 `/health.load.chat_stall_total` 과 사람의 체감. 낮 상한 2 로 한 시간, 밤 상한 6 으로 한 시간 |

리허설은 순서대로 한다.

1. **비우기** — 가짜 엔진으로 도는 중에 `review-drain.sh on` → `status` 의 `review_active` 가 0 이 되는 데 걸린 시간 → `off` → 이어 도는지. 통과 기준은 새 호출 0 건과 실행 상태 `running` 유지다.
2. **에이전트 서버 재기동** — dev 에서 도는 중에 `AGENT_RESTART_FORCE=1 ./start.sh -d`. 끊긴 항목이 `agent_unreachable` 로 적히고 `charged` 가 그대로이며 2분 안에 다시 도는지.
3. **앱 교체** — dev 에서 도는 중에 HEAXHub 의 `redeploy-app.sh hwax-risk`. 새 프로세스가 잠금을 쥐고 `running` 을 되돌려 이어 도는지.
4. **둘째 프로세스** — 같은 데이터 디렉터리로 앱을 하나 더 띄운다(포트만 다르게). 둘째의 `/api/health` 에 `runner_lock_held` 가 있고 도는 항목이 흔들리지 않는지.
5. **update-all** — dev 에서는 돌리지 않는다(리포를 되돌린다). 함수와 절을 떼어 가짜 서버로 시험한 것(P1)으로 대신하고, 실물은 cae00 에서 사용자가 절차서의 확인 줄로 본다.

cae00 시범의 통과 기준(8절의 사용자 결정과 함께 기본값을 굳힌다).

| 잰 것 | 기준 | 못 미치면 |
|---|---|---|
| 호출당 초의 p50·p95 | 적는다(기준 없음) | `HWAXRISK_REVIEW_EST_CALL_S` 를 잰 값으로 |
| 요청 하나의 최악이 벽시계 안인가 | p95 < 14,400초 | 조각을 줄인다(WP3) |
| 잘린 호출 | 0 | 박스의 `DELIB_MAX_TOKENS` 를 본다 · 출력 형식을 줄인다(WP3) |
| 토큰을 모르는 호출 | 0 | LLM 응답에 사용량이 실리는지 본다(9절) |
| 낮 상한 2 에서 `chat_stall_total` 의 증가 | 0 | 낮 상한을 1 또는 0 으로 |
| 밤 상한 6 에서 좌석 유실(`seat_lost_total`)의 증가 | 0 | 밤 상한을 4 로 |
| 차감 없는 다시 돌기의 비율 | 5% 아래 | 사유별로 본다 |

---

## 6. 위험과 완화

### 경합

| 깨지는 경우 | 완화 |
|---|---|
| 허브가 탐침을 놓쳐 앱을 하나 더 띄운다 → 둘째의 복구가 첫째의 항목을 되돌린다 | 프로세스 잠금(3.3.7). 탐침이 락에 막히지 않게 헬스를 락 밖으로 |
| 워커 여섯과 화면의 5초 폴링과 반출이 저장소 락 하나를 다툰다 | 항목 하나의 쓰기는 트랜잭션 하나(행 수십 개). 진행 응답은 5초 캐시. 반출은 표 고르기 |
| 두 프로세스가 같은 DB 에 쓴다(잠금을 못 쥔 쪽의 REST) | busy_timeout 30초. 잡 조작은 행 하나를 고치는 짧은 쓰기다 |
| 게이트가 세는 사이에 다른 요청이 끼어 상한을 넘는다 | `try_acquire` 에 `await` 가 없다(이벤트 루프 하나). 시험이 동시 100 요청으로 본다 |
| 깃발이 선 채로 남아 심사가 영영 안 돈다 | 수명. 고정(`--hold`)은 사람이 세운 것이고 진행 응답·`/health`·update-all 의 헬스게이트가 누가 언제 세웠는지 말한다 |
| 검토 실행과 Tier 잡이 같은 타깃의 커버리지를 같이 고친다 | `flow` 표지와 409 둘(3.2.4) |
| 낮 상한 2 가 그 박스의 LLM 에는 이미 많다 | 챗이 밀린 흔적이 나면 10분 동안 1 로 내린다. 낮 0(밤 전용)은 손잡이 하나다 |
| 게이트가 보지 못하는 LLM 사용자(RA·다른 HEAX 앱)가 있다 | 막지 못한다. 차단기와 시간 초과 계수로 드러날 뿐이다(9절) |

### 재기동

| 깨지는 경우 | 완화 |
|---|---|
| update-all 이 죽어 깃발을 못 내린다 | 수명 1,800초 |
| 깃발을 세운 뒤 에이전트 서버가 재기동해 깃발이 사라진다 | 파일에 남긴다 |
| 에이전트 서버가 죽는 순간의 셀이 좌석처럼 차감된다(2.9 의 5) | 분류표가 `agent_unreachable` 을 인프라로 둔다. 패널 쪽은 WP1 |
| 재기동 직후 수백 항목이 한꺼번에 다시 나간다 | 워커 천장과 게이트가 묶는다. 되돌린 항목에는 흩뿌린 `not_before`(0 ~ 30초)를 준다 |
| 앱이 끊긴 뒤에도 에이전트 서버가 그 호출을 계속 돌린다 | 분리 태스크로 만들지 않는다(봉투 3). 시험 5.2 의 2 |
| 재기동이 잦아 한 항목이 끝내 못 끝난다 | `tries` 의 그물 20 → `failed(infra_exhausted)` 로 사람에게 간다 |
| 며칠 도는 동안 사람이 시작한 심의가 늘 하나씩 있어 배포 틈이 안 난다 | 이 설계가 풀지 않는다(1절). 비우기는 리스크 앱의 몫만 뺀다. 남는 길은 지금처럼 `AGENT_RESTART_FORCE=1` |

### 부분 실패

| 깨지는 경우 | 완화 |
|---|---|
| 셀의 조각 셋 중 둘만 끝나고 죽는다 | 판정 행은 PK 로 덮어쓰는 쓰기라 다시 써도 같다. 다시 돌 때 빠진 카드만 묻는다(WP3). `chunks_done` 은 표시일 뿐 정본은 판정 행이다 |
| LLM 응답은 받았는데 적기 전에 죽는다 | 그 호출만 잃는다(다시 돈다) |
| 단위를 반쯤 만들고 죽는다 | 단위 생성은 트랜잭션 하나다(WP2 에 요구). `advance` 는 단위 수가 아니라 '끝났다' 표지(`rr_jobs.stage` 가 S0 을 지났는가)를 본다 |
| 카드 묶음을 일부만 얼렸다 | 전문가마다 멱등이다. 다 얼기 전에는 셀을 만들지 않는다. 끝내 못 얼린 전문가의 셀은 `failed(pack_fetch_failed)` 로 사람에게 간다('입력 없음' 으로 닫지 않는다 — 회로 입력 부재와 섞인다) |
| 근거 꾸러미의 도구 하나가 실패한다 | 단위는 `partial` 이고 못 돌린 도구가 `evidence_gaps_json` 과 `notes`(○)에 남는다 |
| 사람이 '넘김' 으로 실패를 덮는다 | 사유 필수 · `rr_audit` · 보고서의 '넘긴 셀' 수(WP4) |

### 큰 입력

| 깨지는 경우 | 완화 |
|---|---|
| 단위가 예상의 몇 배다 | 두 번째 예산 재기(3.11.1)가 S0 뒤에 멈춘다 |
| 카드 묶음이 창을 넘는다(dev 의 작은 모델 · 물성 카드 2,688건의 전문가) | 조각 수는 `/health.context_tokens` 로 정한다(WP3). 못 나누면 `context_overflow` 로 곧바로 `failed`(재시도해도 낫지 않는 것을 태우지 않는다) |
| 요청 본문이 크다 | nginx 는 2,048MB 다(`hwax.conf.tmpl:34`). 포털 `ChatRequest.message` 는 65,536자라 카드를 거기에 실을 수 없다 — 전용 칸이 필요하다(WP3 에 요구) |
| DB 가 GB 가 된다 | 사본 정리 · 카드 묶음 내용 주소 · 반출의 표 고르기 · '문제없음' 을 행으로 두지 않는 안(7절) |
| 들여오기가 본문 전체를 메모리에 올린다 | 지금 그대로다(2.2). 큰 반출은 표를 골라 나눈다. 줄 단위 들여오기는 뒤로 미룬다(9절) |
| 포털 감사 로그·접속 로그가 호출 수만큼 는다 | 호출당 두 줄이다. 수천 줄 규모라 그대로 둔다 |

### 빈 입력

| 깨지는 경우 | 완화 |
|---|---|
| 변경이 0 건인 diff(dev 의 자기 비교) | 단위 0 → 실행은 곧바로 `completed` 이고 `notes` 에 `○ 검토 단위가 없다 — 변경 항목 0건` 이 남는다(조용히 끝나지 않는다) |
| AIDataHub 가 비어 있다(새 박스 · 복원 전) | 사전 점검이 `experts 0` 으로 막는다 |
| 로스터에는 있는데 AIDataHub 에 없는 전문가 | 사전 점검의 `missing_in_aidatahub` 경고. 그 전문가의 셀은 `failed(pack_fetch_failed)` |
| 카드 0 장인 전문가 | 묶음 동결이 `cards_n=0` 인 묶음을 만든다(실패가 아니다). 어떻게 검토하는지는 WP3 |
| 범위를 좁혀 셀이 0 이다 | 만들 때 409 `scope_empty` |

### 옛 데이터

| 깨지는 경우 | 완화 |
|---|---|
| v2 DB 를 가진 박스 | 이행은 더하기만 한다. 옛 행은 그대로다(R4 의 시험) |
| 옛 타깃의 `deferred` 좌석 | 건드리지 않는다. 새 흐름에서 그 전문가를 어떻게 넣는지는 WP2·WP3 |
| 옛 판 SIF 로 되돌린다 | 기동을 거부한다(2.1). 되돌리기는 L0·L1 을 먼저 쓴다(3.2.5) |
| 버전이 다른 박스끼리 반출·들여오기 | 409 `schema_mismatch`(지금 그대로). 두 박스를 같은 SIF 로 맞춘 뒤 한다 |
| cae00 첫 배포가 dev 의 DB 를 씨앗으로 받는다(2.7) | 지금도 있는 일이다. 새 표의 dev 시범 데이터가 따라간다 — 시범은 임시 데이터 디렉터리에서 한다(5.4) |

### 박스 차이

| 깨지는 경우 | 완화 |
|---|---|
| 앱 컨테이너가 프록시를 타고 루프백을 부른다 | R10. 사전 점검이 포털·에이전트 서버·AIDataHub 에 실제로 닿아 본다 |
| 박스 시간대가 서울이 아니다 | `CARD_REVIEW_TZ` |
| heartbeat 를 끈 박스 | 침묵 한도를 올려 쓰고 ○ 로 말한다(3.6.2) |
| 호출 한도를 올린 박스 | 벽시계를 올려 쓴다(3.6.2) |
| 매니페스트에 박은 값이 한 박스에서만 틀리다 | 박지 않는다(3.8.2) |
| HEAXHub `.env` 의 값이 재배포에서 빠진다 | `GET /api/meta/runtime` 이 값의 출처를 말한다 |
| 한쪽 리포만 새 판이다 | 3.9.2 |

---

## 7. 다른 꾸러미와의 계약

### 7.1 내가 받는 것

| 누구에게서 | 무엇 |
|---|---|
| WP2 | `rr_units` 의 열 확정 · 단위 생성이 트랜잭션 하나이고 `unit_id`·`unit_hash` 가 결정적일 것 · 근거 꾸러미에서 못 돌린 도구를 `evidence_gaps_json` 에 남길 것 · 필요한 게이트웨이 도구 이름의 목록(사전 점검이 쓴다 — `REQUIRED_TOOLS: tuple[str, ...]`) · 합성 diff 픽스처 생성기 |
| WP3 | `Executor`(3.3.1)를 지키는 셀 실행기 · 카드 대조 모듈이 3.4.4 의 봉투 일곱을 지킬 것 · 오류 코드를 3.3.4 의 어휘로 낼 것 · `usage` · `card_review_rev`·`prompt_rev` · 포털 `ChatRequest`(또는 전용 엔드포인트)에 요청 칸을 선언할 것 · 카드 묶음을 셀보다 먼저 전부 얼릴 것(`rr_card_packs`, `rr_roster.pack_hash`) · 재질의 표본의 결과를 `audit_*` 열에 적을 것 · 본문 없는 탐침 요청을 받으면 `hello` 뒤 곧바로 끝낼 것(사전 점검이 쓴다 — 게이트 자리를 쓰지 않는다) · finding 을 `rr_findings` 에 넣을 때 `panel_id` 자리에 호출 id(`rc-…`)를, `opinion_id` 에 전문가 의견 행을 줄 것(모델·전문가 귀속이 지금 조인으로 붙는다 — 2.2) |
| WP4 | `rr_cross_cells`·`rr_mech_cells` 의 실행기(같은 `Executor`) · 쟁점 패널 잡을 검토 실행과 **다른 잡 행**으로 만들 것(`parent_job` — 패널의 진행 기록이 실행의 행을 덮지 않게) · 쟁점 패널에 일일 상한·수확 체감 정지를 어떻게 걸지 · 새 흐름 타깃의 완결 판정 |
| WP1 | 2.9 의 5(에이전트 서버가 죽은 패널의 차감) · 야간 잡 배선 여부 · 종전 Tier 잡에도 자동 재개를 걸지 |
| WP5 의 다른 갈래 | 카드 대조 호출의 권한(심의와 같은 권한 키로 막을 것) · 새 MCP 도구의 쓰기 금지 시험 |

### 7.2 내가 주는 것

| 무엇 | 이름 |
|---|---|
| 이행의 틀 | `MIGRATIONS` 에 v3 한 줄 · 3.2.1 의 규약과 그 시험 · `prune_backups` |
| 작업 항목 규약 | `Grid`·`Item`·`Outcome`·`Executor` · `claim_next`·`settle`·`recover`·`advance` |
| 실패 분류 | 3.3.4 의 표(코드 → 부류 → 차감 → 다음) |
| 보류와 자동 재개 | `rr_jobs.hold_code`·`hold_until`·`hold_n` · 3.3.3 의 표 |
| 게이트 | `review_gate.ReviewGate.try_acquire/release` · `Busy(reason, retry_after_s, limit, active)` |
| 비우기 | `POST/GET /drain` · `AgentEnv.draining` · `hwax_drain`·`hwax_review_state`·`hwax_review_wait` |
| `/health` 의 칸 | `review_active` · `draining` · `capabilities` · `card_review{…}` · `drain{…}` · `load{…}` |
| 에이전트 서버 사정 | `read_agent_env() -> AgentEnv`(창 크기·상한·밤 창·요청 최악·heartbeat) |
| 호출 원장 | `rr_review_calls` 와 그것을 적는 `record_call(store, item, outcome, *, purpose, chunk_no, output)` |
| 가짜 엔진 | `HWAXRISK_REVIEW_ENGINE=stub` — 실행기를 LLM 없이 돌려 볼 수 있다 |
| 관측 | `GET /api/targets/{key}/review` · `notes` 에 적는 `note(store, job_id, code, text, how, mark='○')` · `metrics._review_rows` |
| 비용 | 실행 생성의 `scope`·`estimate`·`consent` · `budget_json` · `PUT /api/jobs/{id}/budget` |
| 사전 점검 | `GET /api/meta/review-preflight` · `GET /api/meta/runtime` |

### 7.3 공통 계약 초안에서 바꾸자는 것

1. **표를 하나 더한다 — `rr_review_calls`(LLM 호출 원장).** 실패 사유 분포·토큰·호출 시간·차단기·재파싱이 전부 여기서 나온다. 셀의 합계 열만으로는 조각이 여럿인 셀을 이어 돌릴 수 없다.
2. **`rr_card_packs` 의 키를 내용 주소로 한다 — PK(`owner_sub`, `pack_hash`).** 타깃마다 얼리면 십수 MB 가 타깃 수만큼 곱해진다. 타깃과의 연결은 `rr_roster.pack_hash` 와 `rr_review_cells.pack_hash` 다.
3. **셀 상태에 `skipped`(사람의 넘김)와 `carried`(재사용)를 더한다.** `failed` 를 닫을 종결 상태가 없으면 실행이 끝나지 않는다.
4. **새 표의 어휘 열에 CHECK 를 걸지 않는다.** 상태 하나를 더하려고 표를 새로 만들 수는 없다.
5. **새 표는 전부 `owner_sub`·PK 를 갖고, 과제 원문이 드는 표는 `project_id` 도 갖는다.**
6. **실행은 `rr_jobs` 의 행이다(`mode='reviews'`).** 더하는 열은 `mode`·`stage`·`hold_code`·`hold_until`·`hold_n`·`scope_json`·`budget_json`·`notes_json`·`parent_job` 이고, 타깃에는 `flow` 를 더한다.
7. **세 격자가 3.3.1 의 운영 열을 같은 이름으로 갖는다.**
8. **카드 대조 호출은 분리 태스크가 아니고 `delib_active` 에 세지 않는다.**
9. (제안 — WP3 가 정한다) **'문제없음' 판정은 행이 아니라 셀의 `ok_card_ids_json` 으로 둔다.** 행 수가 다섯에 하나쯤으로 준다(3.2.6). '문제없음' 에도 이유를 남기기로 하면 행으로 둬야 한다.
10. **v3 하나에 전부 싣고 첫 커밋으로 넣는다**(3.2.2).

---

## 8. 사용자가 정해야 하는 것

| # | 정할 것 | 권고 기본값 | 까닭 |
|---|---|---|---|
| 1 | 낮의 카드 대조 동시 수 | **2**(밤·주말 6) | 지금 리스크 패널 하나가 순간 6 건을 부른다 — 2 는 그보다 가볍다. 다만 며칠 이어진다는 점이 다르다. 0(밤 전용)으로 두면 챗에 주는 영향은 없고 심사 기간이 두세 배가 된다. 시범에서 `chat_stall_total` 이 오르면 0 으로 내린다 |
| 2 | 밤 창 | **19시 ~ 08시와 토·일 종일**(서울 시각) | 실사용 팀의 근무 시간을 피한다. 야간에 심의를 돌리는 팀이 있으면 좁힌다 |
| 3 | 사용자 PAT 가 실행 도중 끝나면 | **멈추고 알린다** | 서비스 계정으로 이어 돌면 앞 셀과 뒤 셀이 다른 시야로 돈다. 멈추면 사람이 PAT 를 다시 등록할 때까지 진행이 0 이다. 사람이 며칠 자리를 비우는 실행이면 '계속' 이 낫다 |
| 4 | 예산의 문턱 | **추정 1,500회 초과는 명시 동의, 30,000회 초과는 거절** | 입력 자료의 추정으로 단위 8 · 전원이 4,000회 안팎이다. 1,500 은 대표 15명 시범은 그냥 지나가고 전원 실행은 반드시 한 번 묻게 하는 값이다 |
| 5 | update-all 이 재기동을 미뤘을 때 비우기를 얼마나 남기나 | **1시간** | 남기지 않으면 다음 실행 때도 새 패널이 돌고 있다. 길게 남기면 사람이 다시 돌리는 것을 잊은 동안 심사가 선다(1시간 뒤 스스로 풀린다) |
| 6 | 패널이 돌 때 HEAX Hub 재기동도 미룬다 | **미룬다** | 리스크 앱과 좌석이 부르는 도구가 그 허브에 산다. 대가는 다른 HEAX 앱의 갱신도 그 실행에서 같이 미뤄지는 것이다 |
| 7 | 새 흐름을 켜는 순서 | **기본 꺼짐 → dev 가짜 엔진 리허설 → cae00 대표 15명 밤 시범 → 기본 켬** | 호출 시간·토큰·낮 상한이 전부 추정이다. 시범 없이 전원을 돌리면 틀린 기본값으로 며칠을 쓴다 |
| 8 | cae00 시범에 쓸 타깃과 시각 | (사용자가 고른다) | 실제 리비전 쌍은 cae00 에만 있다. 밤 한 번이면 된다 |

---

## 9. 확인하지 못한 것

- **cae00 의 실제 설정값.** `.env` 를 열지 않았다 — `DELIB_TIMEOUT_S`·`DELIB_MAX_TOKENS`·`DELIB_HEARTBEAT_S`, HEAXHub `.env` 의 `NO_PROXY`·`APPTAINERENV_HWAXRISK_*`, `enforce_instance_limits`, 박스 시간대. 설계는 값을 가정하지 않고 사전 점검과 `/health` 로 읽게 했다.
- **리스크 러너가 cae00 에서 실제로 패널을 돌린 적이 있는지.** 실사용 팀은 MCP 로 심의를 직접 불렀다(입력 자료). 앱 → 포털 길이 그 박스의 프록시 환경에서 도는지는 모른다(R10 이 그 대비다).
- **운영 LLM 의 호출 시간·동시 용량·접두 캐시·우선순위 지원.** 낮 2 · 밤 6 · 호출당 300초는 전부 가정이다. 5.4 의 시범이 잰다.
- **LLM 응답에 토큰 사용량이 실리는지.** 코드에 읽는 자리가 없어 본 적이 없다. 안 실리면 토큰은 `NULL` 이고 글자 수만 남는다.
- **게이트가 보지 못하는 LLM 사용자**(Report Archive, 다른 HEAX 앱, PaperIngest)가 얼마나 쓰는지.
- **`apptainer instance stop` 이 앱에 주는 종료 유예.** 도움말로 `--timeout` 손잡이가 있다는 것만 봤다. 설계는 유예에 기대지 않는다(항목은 기동 때 되돌린다).
- **데이터 디렉터리의 파일시스템.** `flock` 은 로컬 디스크에서 확실하다. NFS 면 잠금이 다르게 돌 수 있다(cae00 의 `/data` 를 보지 않았다).
- **cae00 에 `risk_review.db.pre-merge-*` 가 실제로 쌓여 있는지.** 스크립트로는 그렇다(2.7). 박스를 보지 않았다.
- **update-all 전체.** 2,300줄 가운데 §1c·§2·§4·§5 의 해당 줄과 정지 규율만 읽었다. 끝맺음을 부를 자리(요약 직전·정지 지점)는 구현할 때 다시 본다.
- **포털의 요청 칸이 어떤 꼴이 될지.** `ChatRequest` 에 칸을 더하는지 전용 엔드포인트인지는 WP3 의 결정이다. 3.4.4 의 봉투는 어느 쪽이든 선다.
- **AIDataHub REST 가 전문가의 카드 본문을 한 번에 주는지.** 입력 자료(`02-fit.md`)의 인용이고, 이 꾸러미는 라우트 시그니처만 다시 봤다(`routes/records.py:99-113` — `agent` 필터는 있고 `doc_type` 인자는 없다).
- **들여오기를 줄 단위로 바꾸는 일.** GB 급 반출을 받는 쪽의 메모리는 이 설계가 풀지 않았다.
- **다른 꾸러미의 최종 열.** 3.2.3 은 초안이다. 열이 바뀌면 `PURGE_BLANK_SQL`·`_SINCE_COLS` 의 목록(3.2.7)을 같이 고친다.
