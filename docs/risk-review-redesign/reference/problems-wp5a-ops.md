# WP5a(스키마 이행·설정·배포·운영) 설계서 반대 검토 — 문제 메모

대상 설계서는 `spec-wp5a-ops.md` 다. 계약(`04-contract.md`)이 이미 조정한 어긋남은 다시 적지 않는다.
문제를 찾을 때마다 아래에 덧붙인다(작업이 끊겨도 남게).

## P-01 [blocker] 러너의 주인이 둘이다 — 계약이 열 이름만 맞추고 러너 구조는 정하지 않았다

- WP5a 3.3 은 새 파일 `review_runner.py` 가 `Grid·Item·Outcome·Executor·claim_next·settle·recover·advance` 를 갖는다고 적는다(집는 단위 = 항목, 실행 하나가 S0~S6 단계를 표에서 읽어 나아간다). 걸음 R6 이 이 파일을 '새' 로 만든다.
- WP3b 3.1(167~169줄)·걸음 8(1506줄)도 같은 이름의 새 파일 `review_runner.py` 를 만든다. 내용은 `create_review_job·review_tick·run_expert·Breaker·WorkProvider` 이고 집는 단위는 **전문가 세션**(`review_cells.claim_next_expert`)이다. WP4(1242줄)는 `WorkProvider` 를 구현한다 — `Executor` 가 아니다.
- 겹치는 것(계약에 조정이 없다) — 러너 잠금(WP5a R2 `runlock.py` ↔ WP3b 걸음 2 `main.py`), busy_timeout(양쪽), 차단기 규칙(WP5a '최근 20건 중 10건' `llm_outage` ↔ WP3b '20회 중 절반 또는 연속 5회' `breaker`), 보류 코드 어휘(WP5a `llm_outage·aidh_unreachable·agent_outdated·budget·credential·needs_disposition·restart·disabled` ↔ WP3b `breaker·content_fail_rate·pack_unavailable·contract`), 워커 천장(6 ↔ 4, C-24 는 관문 기본 4), 호출 벽시계(14,400 ↔ 18,000), 재시도 상한 이름(`MAX_CHARGED` ↔ `MAX_ATTEMPTS`).
- 계약 C-5 의 잡 종류 다섯(`panels|reviews|post|issues|synth`)은 WP3b·WP4 의 '종류마다 잡 행' 모형이다. WP5a 의 '실행 하나 = 잡 하나 + `stage` S0~S6' 모형(`advance`, 진행 응답의 `stages[]`, `scope.stages`, 예산의 두 번째 재기, `parent_job`)은 그 위에 서지 않는다. C-21 은 반대로 셀 단위 lease 열(WP5a)을 정본으로 삼았다 — 두 모형이 한 표에 섞인다.
- WP3b 설계서에는 `drain`·`draining` 이 한 번도 나오지 않는다(grep 0건). WP3b 러너가 채택되면 앱에서 비우기를 읽는 자리(WP5a 3.5.2)가 아예 없다.
- 고치는 법 — 계획서에 한 줄로 못 박는다. **러너 루프·상태기계·선점·차단기의 주인은 WP3b(`review_cells.py`·`review_runner.py`)다.** WP5a 의 R6 은 지우고, WP5a 가 주는 것은 러너가 부르는 순수 함수 모듈 하나(`review_ops.py` — 실패 분류표 `classify(error_code) → (부류, 차감, 다음)`, 백오프 식, `read_agent_env`, 보류 코드 표와 자동 재개 판정)로 줄인다. 보류 코드 어휘는 한 표로 합친다(`breaker` 하나로, `llm_outage` 는 버린다). R2 와 WP3b 걸음 2 는 한 커밋으로 합친다(`runlock.py` 는 WP5a 것, 배선은 WP3b 것). R7 의 `stages[]`·`scope.stages` 는 C-5 의 잡 종류 사슬로 다시 적는다.

## P-02 [major] deploy-all heax 블록에 넣는 `exit 3` 이 '미룸' 이 아니라 '실패' 로 집계된다

- 설계 3.5.3 의 조각은 heax 서브셸 안에 `if _delib_hold …; then exit 3; fi` 한 줄만 넣는다.
- 지금 heax 블록의 끝은 `) && ok "heax up" || skip "heax failed (see the log lines above)"` 다(`deploy-all-from-drive.sh:337`). `skip` 은 `$DEPLOY_FAILED_FILE` 에 한 줄을 적고(:179) 끝에서 `exit 4` 가 된다(:585). update-all 은 `_DA_RC=4` 를 `fail "deploy-all 에서 배포 항목이 skip/실패했다"` 로 읽는다(`update-all.sh:543-545`).
- 포털 블록은 이 때문에 `|| _prc=$?` 로 받고 `case … 3) ;;` 로 가른다(:252-254, 주석 '실패가 아니라 skip 으로 세지 않고(exit 4 가 된다)').
- 그대로 구현하면 심의가 도는 동안의 모든 update-all 이 '✗ 배포 항목 1건 skip/실패' 로 끝난다. P2 의 검증('물음이 dist-from-drive 줄보다 앞인지를 소스에서 본다')은 이것을 못 잡는다.
- 고치는 법 — P2 에 '서브셸 끝을 포털 블록과 같은 꼴(`|| _hrc=$?` · `case "$_hrc" in 0) ok;; 3) ;; *) skip;; esac`)로 바꾼다' 를 넣고, 시험에 '심의가 돌 때 deploy-all 의 종료코드가 0 이고 DEPLOY_FAILED 에 heax 가 없다' 를 더한다(포털 블록 시험 `test_심의가_돌면_포털과_nginx_를_내리지_않는다` 와 같은 꼴로 실제로 돌린다).

## P-03 [major] `DEFERRED_ANY` 를 만들 재료가 틀렸다 — 포털·nginx·heax 를 미룬 실행에서 비우기가 그대로 풀린다

- 설계 3.5.3 은 `DEFERRED_ANY` 를 '지금의 `_DA_RC`·`_us_rc` 3 과 `DEFERRED_RESTART` 에서 만든다' 고 적는다.
- `_DA_RC = 3` 은 미룸이 아니라 **소스 갱신 실패**다(`deploy-all-from-drive.sh:584` `[ "$_stale" = 1 ] && exit 3`, `update-all.sh:539-542`). 포털·nginx 를 심의 때문에 미룬 deploy-all 은 **0 으로 끝난다**(서브셸의 3 은 `_prc` 에서 삼킨다 — :252-254, nginx 는 `_nghold`).
- `DEFERRED_RESTART` 는 update-all 의 변수가 아니라 `update-sites.sh:164` 의 지역 변수다(자식 프로세스). update-all 에 닿는 것은 `_us_rc = 3` 뿐이고, 그것도 에이전트 서버에 **바뀐 것이 있어 재기동이 필요했을 때만** 3 이다(지문이 같으면 묻지도 않고 0 — `update-sites.sh:183-191`).
- 결과 — 가장 흔한 경우(포털 커밋만 있고 에이전트 서버는 그대로)에 포털·heax 를 미뤄도 `DEFERRED_ANY` 가 비어 `_hwax_drain_finish` 가 깃발을 내린다. 다음 쟁점 패널이 곧 시작되고 다음 update-all 도 또 미룬다 — 3.1 원칙 2('배포 창이 반드시 열리게')가 서지 않는다. 반대로 git 실패(3)에는 깃발이 한 시간 남는다.
- 고치는 법 — P1 에 넣는다. 미룬 사실은 종료코드가 아니라 **장부**에서 읽는다 — `_delib_hold`·update-sites·§5 재프로비저닝이 전부 `hwax_skip` 으로 적는다(`lib/skip-ledger.sh:20-23`). `_hwax_drain_finish` 는 `$HWAX_SKIP_LEDGER` 에 이름이 '재기동 건너뜀'·'재프로비저닝 건너뜀' 으로 끝나는 줄이 있는가로 정한다(deploy-all 은 update-all 의 자식이고 장부 경로를 환경으로 물려받는지 구현 때 확인한다 — 안 물려받으면 `_delib_hold` 가 표식 파일을 하나 남기게 한다). 시험은 '포털만 미뤘고 에이전트 서버는 무변경' 인 실행에서 깃발이 남는지를 본다.

## P-04 [major] 비우기 깃발의 수명(1,800초)이 update-all 한가운데에서 끝난다 — 지키려던 §4·§5 재기동 앞에서 풀린다

- 설계 3.5.3 의 1f 는 §2 앞에서 깃발을 **한 번** 세우고(수명 1,800초) 곧바로 도는 셀을 최대 600초 기다린다. 그 뒤로 다시 세우는 자리가 없다(끝맺음은 요약 직전뿐이다).
- 깃발이 지켜야 하는 재기동은 그 뒤에 온다 — §2(포털·heax·nginx) → §3(AIDataHub 덤프 복원) → 2c(ste, 상한 900초 `update-all.sh:627`) → §4(에이전트 서버) → §5(게이트웨이 재프로비저닝). §2 의 SIF 내려받기에는 상한이 없고 Drive 가 약 2MB/s 다(`docs/update-all-skip-unchanged/context-notes.md:6` — 'SIF 수백 MB 짜리 서비스 하나가 수 분'). 기다림 600초를 빼면 §2~§3 에 남는 것이 1,200초다.
- 수명이 끝나면 앱이 새 쟁점 패널을 시작할 수 있고, 그러면 §4 가 `hwax_delib_busy` 로 에이전트 서버 재기동을 미룬다 — 깃발을 만든 까닭 그대로의 일이 긴 배포에서 난다.
- 고치는 법 — P1 에 넣는다. ① `hr()`(§ 머리, `update-all.sh:66-73`)에서 `HWAX_DRAIN_RAISED=1` 이면 `hwax_drain on "$HWAX_DRAIN_TTL_S"` 를 다시 부른다(실패는 삼킨다, `-m 2`). ② 수명을 '세운 때' 가 아니라 '마지막으로 다시 세운 때' 부터 재게 한다(`DrainState.set` 이 until 을 늘리기만 한다). ③ 시험 — 가짜 서버로 §가 셋 지나는 동안 `/drain on` 이 § 수만큼 왔는지를 본다.

## P-05 [major] update-all 이 사람이 세운 고정(`--hold`, 되돌리기 L0)을 조용히 지운다

- 3.2.5 의 L0 은 `review-drain.sh on --hold` 이고 L2 는 '고친 커밋으로 앞으로 간다(빌드 + 배포)' 다. 그 배포가 update-all 이다.
- 1f 는 무조건 `hwax_drain on 1800 update-all` 을 보낸다. 3.5.1 의 `DrainState.set` 에는 '이미 고정이면 그대로 둔다' 는 규칙이 없다 — 고정이 수명 1,800초짜리로 바뀐다. 끝맺음 `_hwax_drain_finish` 는 `HWAX_DRAIN_RAISED=1` 이면 `hwax_drain off` 를 보낸다.
- 결과 — 고장 난 판을 멈춰 두고 고친 판을 올리는 바로 그 update-all 이 끝나는 순간, 사람이 확인하기 전에 심사가 다시 돈다.
- 고치는 법 — A1 의 `DrainState` 규칙에 둘을 적는다. ① `hold=True` 인 깃발은 `hold=False` 요청으로 바뀌지 않는다(응답에 `hold:true, by:<세운 사람>` 을 그대로 돌려준다). ② `off` 는 `by` 를 받고, 세운 주체와 다르면 내리지 않는다(`review-drain.sh off` 만 `force` 로 내린다). P1 의 1f 는 응답의 `hold` 가 참이면 `HWAX_DRAIN_RAISED` 를 세우지 않고 '사람이 고정해 둔 깃발이 있다 — 건드리지 않는다' 를 찍는다. 시험 한 줄 — 고정 뒤 1f·끝맺음을 지나도 `GET /drain` 이 `hold:true` 다.

## P-06 [major] `running` 으로 남은 항목을 되찾는 것이 기동 때의 `recover` 뿐이다 — 도는 중에 생긴 고아는 실행을 영영 못 끝낸다

- 3.3.1 의 `recover` 는 '`lease_owner` 가 내 boot_id 가 아닌 running' 만 되돌리고 '프로세스 잠금을 쥔 뒤에만 부른다'. `heartbeat_at` 은 집을 때 한 번 적히고 **읽는 곳이 없다**(설계서 전체에서 DDL·claim 두 곳뿐).
- 같은 프로세스 안에서 항목이 `running` 으로 남는 길이 셋 있다. ① `settle` 자체가 실패한다 — 3.3.7 이 연결에 busy_timeout 30초를 주는데, 둘째 프로세스나 바깥 도구(`sqlite3` CLI·허브의 병합기)가 30초 넘게 쓰기 잠금을 쥐면 `database is locked` 가 올라온다(디스크가 찬 경우도 같다). ② 실행기가 3.3.1 의 여섯 예외 밖의 것을 올린다(파서의 KeyError 등 — '그 밖' 줄은 **오류 코드**의 그 밖이지 예외의 그 밖이 아니다). ③ 반출한 원장에 `running` 행이 섞여 다른 박스로 들어온다(`export.py` 는 상태를 고치지 않는다).
- 3.3.6 의 `advance` 는 '그 단계 격자에 pending·running 이 0 인가' 로 단계 끝을 본다. 고아가 하나면 그 단계가 끝나지 않고, 보류 코드도 없어 화면에는 `running` 으로만 보인다.
- 같은 뿌리의 문제 하나 더 — `settle`·취소의 쓰기 조건이 적혀 있지 않다. 3.2.7 은 폐기가 `running` 을 `skipped(project_purged)` 로 닫는다고 하고, 3.11.3 은 취소가 '항목은 pending 으로 돌아간다' 고 한다. 조건 없이 쓰면 폐기 뒤 늦게 온 결과가 `skipped` 를 덮고, 방금 비운 원문(`rr_card_verdicts.quote·why`, `rr_review_calls.output_gz`)을 다시 적는다.
- 고치는 법 — 러너 걸음(P-01 로 정한 주인의 걸음)에 둘을 넣는다. ① 검토 루프의 틱마다 '`lease_owner` 는 내 것인데 살아 있는 워커 목록에 없는 running' 을 차감 없이 `pending` 으로 돌린다(`error_code='worker_lost'`, 로그 한 줄). 워커의 바깥 `except Exception` 은 예외를 내용 실패가 아니라 이 길로 보낸다. ② 항목에 닿는 모든 쓰기(성공·실패·취소·판정 행 저장)는 한 트랜잭션에서 `UPDATE … WHERE <PK> AND status='running' AND lease_owner=?` 의 rowcount 1 을 먼저 확인하고, 0 이면 판정·호출 행을 **쓰지 않고** 버린다. 시험 — 워커가 호출 중일 때 폐기를 부르고 가짜 엔진을 풀어 결과가 와도 원문 열이 비어 있는지.

## P-07 [major] 기능을 켜는 손잡이가 둘이고 서로를 모른다 — R11 로 켜도 새 타깃은 옛 흐름으로 만들어진다

- WP5a 의 스위치는 `HWAXRISK_REVIEW_ENABLED`(3.8.1, R11 이 기본을 1 로)이다. 다른 설계서 어디에도 이 이름과 409 `review_disabled` 가 없다(WP2·WP3b·WP4·WP5b grep 0건).
- WP2 의 스위치는 `HWAXRISK_REVIEW_FLOW`(코드 기본 `panels`)이고, 새 타깃의 흐름·보류 해제·입력 결손 기록이 **타깃을 만들 때** 이 값으로 정해진다. WP2 는 '전환은 WP5' 라고 적었다(spec-wp2 740·877·1052줄). WP5a 의 손잡이 표·R11·절차서 목록에 이 이름이 없다.
- 타깃 키는 `f"{kind}:{ref_id}"` 이고 같은 키는 409 다(`routes.py:2025-2027`). 흐름을 잘못 단 타깃은 다시 만들 수 없다.
- 결과 — R11 뒤에도 화면에서 만든 타깃은 `flow='panels'` 이고 회로 영역 104명이 `deferred` 로 얼어 있다(프런트는 이 설계의 범위 밖이라 본문에 `flow` 를 싣는다는 보장이 없다). cae00 시범도 같다.
- 박스별로 켜는 길도 약하다 — 3.8.2 는 `launch.env` 에 박지 않고 HEAXHub `.env` 의 `APPTAINERENV_HWAXRISK_*` 로 주라고 한다. 그 길은 `.env` 를 싣지 않은 기동에서 조용히 빠지고(`apt_runner.py:213-220` 은 런처의 `os.environ` 만 본다), 앱 리포의 시험이 '대안이 못 된다' 고 적어 둔 길이다(`tests/test_manifest.py:64-67`). 며칠 도는 cae00 시범 도중에 빠지면 실행이 `disabled` 로 선다.
- 고치는 법 — ① 스위치를 하나로 한다. R5 에 '`HWAXRISK_REVIEW_FLOW` 의 기본값은 `HWAXRISK_REVIEW_ENABLED` 를 따른다(켜지면 `cells`)' 를 넣고 R11 의 검증에 '기본값에서 만든 타깃이 `flow='cells'`·deferred 0' 을 더한다. WP3b 의 `create_review_job` 이 `review_disabled` 를 내게 한다. ② 박스별 값은 데이터 디렉터리의 파일로 준다 — `secrets.env` 를 읽는 것과 같은 방식(`config.load_secrets`, `config.py:279`)으로 `$DATA_DIR/knobs.env` 를 `load_settings` 가 읽는다(추적 파일이 아니고, 재배포에도 남고, 박스마다 다르다). R5 의 `GET /api/meta/runtime` 은 출처에 `knobs.env` 를 더한다. ③ 절차서의 시범 순서에 '타깃을 만들기 **전에** 켠다' 를 적는다.

## P-08 [major] 리허설(5.4)이 떠 있는 dev 서비스를 끊고, 가짜 엔진으로는 재려는 길을 지나지 않는다

- 리허설 2 는 `AGENT_RESTART_FORCE=1 ./start.sh -d` 다. 이 손잡이는 도는 심의를 묻지 않고 끊는 값이다(`HWAXAgentServer/start.sh:118-128` — '진행 중 N건은 interrupted 로 끊기고 대기는 사라진다'). dev 에이전트 서버는 여러 세션이 같이 쓴다. `review_active` 는 재기동을 막지 않으므로(3.5.3) 강행 손잡이 없이도 리허설은 된다.
- 리허설 3 은 `redeploy-app.sh hwax-risk` 다 — 허브가 띄운 **실 앱**을 내렸다 올린다. 5.4 표는 운영 동작을 '임시 데이터 디렉터리의 임시 앱' 에서 본다고 했는데 `redeploy-app.sh` 는 임시 앱을 모른다. 실 앱에서 가짜 엔진(`HWAXRISK_REVIEW_ENGINE=stub`)을 켜면 정해진 가짜 판정이 실 DB 의 타깃에 `reviewed` 로 들어간다(가짜 결과에 표지를 남기라는 규칙이 없다).
- 리허설 1·2 는 가짜 엔진으로 잴 수 없다. 가짜 엔진은 앱 안에서 끝나 에이전트 서버를 부르지 않는다(3.8.1 '`stub` 이면 LLM 없이 정해진 결과를 낸다', `engine_client.build_review_engine`). 그래서 `review_active` 는 늘 0 이고 '0 이 되는 데 걸린 시간' 도, 재기동에 끊긴 항목의 `agent_unreachable` 도 생기지 않는다. 통과 기준이 전부 자명하게 참이 된다.
- 고치는 법 — 5.4 를 이렇게 바꾼다. ① 가짜를 **에이전트 서버 쪽**에 둔다(가짜 LLM 을 문 임시 에이전트 서버 — `test_thinking.py` 방식 — 를 빈 포트에 띄우고, 임시 포털(`SERVE_FRONTEND` 없이)과 임시 앱(`HWAXRISK_DATA_DIR`·`HWAXRISK_AGENT_URL`·`HWAXRISK_PORTAL_BASE` 를 임시 것으로)을 잇는다). 비우기·재기동·앱 교체는 이 임시 벌에서 한다. ② 실 dev 서비스에는 `status` 류 읽기만 한다. `AGENT_RESTART_FORCE` 는 리허설에서 쓰지 않는다고 적는다. ③ 앱의 `stub` 엔진은 시험 전용으로 두고, 데이터 디렉터리가 허브의 실 경로면 기동을 거부하거나 결과 행에 `model='stub'` 을 적어 보고서·지표에서 빠지게 한다. ④ 임시 벌을 띄우고 내리는 스크립트는 절대경로와 `command -v` 대역 확인을 쓴다(2026-09-28 사고의 규율).

## P-09 [major] 3.2.7 의 '고칠 곳 전부' 에 소유자 이양이 없다 — 이양 뒤 새 표의 행이 옛 소유자에 남는다

- 설계 2.2 와 3.2.7 은 새 표가 걸리는 자리를 반출·폐기·지표·학습·야간·시험·매니페스트로 적고 '고칠 곳 전부' 라고 한다.
- 이양은 표 목록을 손으로 든다 — `routes.py:756-759` `TRANSFER_PROJECT_TABLES`(11표)와 `:761-779` `TRANSFER_DERIVED`(16표). v2 의 `rr_brief_calls` 도 여기에 손으로 들어가 있고 주석이 '빠뜨리면 새 소유자의 반출에서 해석 원장이 사라진다' 고 적는다(:771).
- WP2(`rr_units`·`rr_unit_builds`)와 WP3b(셀·판정·보고서·호출 넷)는 제 표를 넣는다고 적었다. WP4 설계서에는 `TRANSFER_` 가 한 번도 없다(교차·메커니즘 격자와 쟁점 표). 통합 블록(v4)의 주인인 이 설계서의 R4 에도 없다.
- 결과 — 이양한 과제에서 교차·메커니즘·쟁점 행의 `owner_sub` 가 옛 사람으로 남는다. 새 소유자의 반출에서 빠지고(`export.py:178-180`), 들여오면 `owner_conflict` 로 눕고(:351-356 — `export.py:355`), 소유자 대조(`_owned_row`)를 쓰는 조작이 404 가 된다.
- 고치는 법 — R4 에 둘을 넣는다. ① `owner_sub` 를 가진 새 표 전부를 이양 목록에 넣는다(`project_id` 가 있으면 `TRANSFER_PROJECT_TABLES`, 없으면 `TRANSFER_DERIVED`). ② 목록이 다시 새지 않게 시험을 하나 둔다 — '`owner_sub` 열이 있는 `rr_*` 표는 전부 이양 두 목록 중 하나에 있거나 명시한 면제 집합(`rr_audit` 등)에 있다', 같은 꼴로 '`project_id`·`target_key` 를 가진 표의 TEXT·BLOB 열은 `PURGE_BLANK_SQL` 에 있거나 면제 집합에 있다'(3.2.7 의 폐기 목록은 `rr_units.title` 처럼 과제 글이 드는 열을 이미 빠뜨렸다 — WP2 는 `title`·`digest` 를 비운다고 적는다).

## P-10 [major] 사전 점검(3.9.3)의 절반은 읽을 길이 없다 — 계약 C-10·C-12 뒤로 남은 것

- `aidatahub` 칸(전문가 359·카드 10,774·전문가별 카드 수·카드 0장 전문가)과 `roster_vs_aidatahub` 는 전 전문가의 카드를 세야 나온다. C-10 은 앱이 AIDataHub REST·서비스 키 경로를 쓰지 않는다고 정했다 — 남는 길은 전문가마다 `/card-review/pack` 을 부르는 것뿐이고 그것이 곧 묶음 동결이다(WP3b 553줄 — 한 건 최악 420초, 서버가 동시 2건). 사전 점검은 nginx `/apps/` 600초 안의 동기 요청이다(`config.py` 의 `DEFAULT_ROSTER_DEADLINE_S` 주석 — 명단 조회 하나가 이미 540초 기한을 쓴다). '실행 생성도 안에서 같은 함수를 부른다' 고 했으므로 생성 요청도 같이 걸린다.
- `gateway_tools` 칸은 WP2 가 주는 `REQUIRED_TOOLS` 를 읽는다(7.1). 어느 설계서도 이 상수를 만들지 않는다(WP2·WP3a·WP3b·WP4·WP5b grep 0건).
- `portal_forwards_review` 칸은 '본문 없는 탐침 요청 → `hello` 프레임' 에 기댄다. `hello` 프레임은 이 설계서에만 있다(WP3a·WP3b·WP4 grep 0건). C-12 로 전용 엔드포인트가 생겨 옛 포털·옛 에이전트 서버는 404 로 갈린다 — 3.9.2 가 막으려던 '평범한 챗으로 처리돼 엉뚱한 글이 온다' 는 더는 일어나지 않는다.
- 고치는 법 — R7 의 사전 점검을 싼 것만 남긴다. `review_enabled` · `runner_lock` · 포털 `/health` · 에이전트 서버 `/health`(capabilities·상한·draining) · **`GET /agent/card-review/limits` 한 번**(C-17 로 어차피 부른다 — 200 이면 포털이 넘기고 에이전트 서버가 안다, 404 면 어느 쪽이 옛 판인지 응답 주체로 가른다) · 자격 · 시간 사슬 · 디스크. 카드 수·카드 0장·명단 대조는 사전 점검에서 빼고 묶음 단계의 결과(진행 응답 `S0b` 의 `packs·no_cards·error`)로 낸다. `gateway_tools` 는 WP2 가 근거 꾸러미에 쓰는 도구 목록을 상수로 내놓는 걸음을 WP2 계획에 더한 뒤에 넣는다(없으면 이 칸을 뺀다). `hello` 프레임·`review_unsupported`·빈 탐침은 지운다.

## P-11 [minor] `/api/health` 가 락을 잡는 자리가 둘인데 설계는 하나만 든다

- 2.3·3.3.7 은 `get_store().schema_version()` 만 든다. 같은 핸들러가 `health_warnings()` 로 `routes.vocab_recompute_pending(get_store())` 도 부른다(`main.py:151·164-167`, `routes.py:3070-3077` — `store.query_one` 이 락을 잡는다).
- R1 의 시험('락을 쥔 채 200ms 안에 200')이 잡아 주기는 한다. 다만 고칠 방법이 설계에 없다 — 버전만 캐시하면 시험이 여전히 걸린다.
- 덧붙여 허브 탐침은 주소 넷 가운데 하나만 500 미만이면 산 것으로 본다(`integration_launcher.py:1364-1382`). 셋째·넷째 주소는 락을 잡는 핸들러가 아니라(정적 마운트 또는 라우터의 404) 스레드풀이 락 대기로 다 차지 않는 한 곧바로 500 미만을 답한다 — '락 때문에 탐침이 실패해 둘째 프로세스가 뜬다' 는 3.3.7 의 설명은 그대로는 성립하지 않는다(코드로 읽은 추정이다 — 돌려 보지는 않았다. 둘째 프로세스가 뜨는 것은 기동이 길어지거나 이벤트 루프가 막혔을 때다). R1·R2 는 그래도 값이 있다.
- 고치는 법 — R1 에 '`vocab_recompute_pending` 은 기동 때와 사전 편집 때 갱신하는 메모리 값으로 낸다(또는 `acquire(timeout=0)` 로 못 잡으면 직전 값을 낸다)' 를 넣는다.

## P-12 [minor] 러너 잠금의 시험이 운영 모양(같은 포트)을 넣지 않는다

- 허브가 다시 띄우는 둘째 프로세스는 **같은 포트**를 받는다(`port_allocator.allocate_port` 의 멱등 갈래, `port_allocator.py:68-83`). uvicorn 은 lifespan 기동을 **먼저** 하고 포트를 묶으며, 묶기에 실패하면 lifespan 종료 뒤 `exit(1)` 이다(uvicorn 0.49 `Server.startup` 에서 확인). 즉 둘째는 `get_store()·migrate()·runner.start()` 를 다 돈 뒤 1초쯤 뒤에 죽는다.
- R2 의 시험과 리허설 4 는 '포트만 다르게' 띄운다. 운영 모양에서만 나는 일 둘을 놓친다. ① 둘째의 종료 경로(`runner.stop()` → `release()`)가 잠금 **파일을 지우면** 첫째는 지워진 inode 를 쥔 채 남고 셋째가 새 파일로 잠금을 얻는다(러너 둘). ② 못 쥔 프로세스가 주인 정보를 덮어쓰면(`open(…, 'w')`) `holder()` 가 죽은 pid 를 말한다.
- '못 쥐면 60초마다 다시 시도' 는 운영에서는 일어나지 않는다(그 전에 죽는다). 값이 있는 것은 '못 쥐면 복구·루프를 돌지 않는다' 한 줄이다.
- 잠금을 쥐는 자리도 `migrate()` 뒤다. v5 이후 GB 급 DB 의 이행은 사본 복사만 수십 초라 그 사이 둘째가 떠서 같은 이행과 사본을 겹쳐 시도한다(둘째는 `duplicate column` 으로 죽는다 — 데이터는 안 깨지지만 GB 사본이 하나 더 남는다).
- 고치는 법 — R2 에 넣는다. 잠금 파일은 지우지 않고, 주인 정보는 잠금을 얻은 뒤에만 적는다. 잠금은 `get_store()` **앞**에서 시도하고 못 쥐면 이행도 하지 않는다(연결만 연다 — 버전이 코드보다 낮으면 503 으로 답한다). 시험에 '같은 포트로 둘째를 띄우면 둘째가 죽고, 첫째의 running 패널과 잠금 파일 내용이 그대로다' 를 더한다.

## P-13 [minor] 차단기가 풀리자마자 다시 걸린다 — 창을 비우는 규칙이 없다

- 3.3.5 는 '최근 끝난 호출 20건 가운데 실패 10건 이상이면 보류', '탐침이 성공하면 푼다' 를 적는다. 탐침 하나가 성공해도 창은 실패 19 + 성공 1 이다. 다음 틱에 같은 식이 다시 참이 되고 `hold_n` 이 올라 간격이 한 단 늘어난다(300 → … → 3,600초). 성공 11건이 쌓일 때까지 한 건씩만 나간다.
- 5.1 의 단언('성공하면 풀리고 hold_n 이 0')은 푼 **직후**만 본다.
- 고치는 법 — 창을 '마지막으로 푼 시각 뒤에 시작한 호출' 로 자른다(`rr_jobs.state_at` 또는 새 값 하나). 5.3 의 'LLM 이 20건 연속 죽는다' 시나리오에 '살아난 뒤 다음 20건 동안 보류가 다시 서지 않는다' 를 더한다. (P-01 로 WP3b 의 `Breaker` 가 주인이 되면 그쪽 규칙 '10회 이상 쌓였을 때' 에 같은 창 자르기를 넣는다.)

## P-14 [minor] 코드가 세운 보류 중에는 사람이 멈출 수 없다

- 3.11.3 의 정지는 '지금 것' 이다. `pause_job` 은 상태가 `queued`·`running` 일 때만 받는다(`runner.py:676-677` — 그 밖은 409). 자동 재개가 붙은 보류(`llm_outage`·`engine_busy`·`agent_outdated`·`aidh_unreachable`·`restart`·`disabled`)에 선 실행은 `paused` 라 정지가 거절되고, 간격이 지나면 스스로 다시 돈다. 남는 것은 취소뿐이다.
- 3.3.3 의 표는 `user` 를 `hold_code` 의 한 값으로 적고 3.11.3 은 `pause_reason='user'` 로 적는다 — 사람의 정지를 어느 열에 적는지도 둘로 갈린다.
- 고치는 법 — 검토 잡의 정지 규칙을 적는다. `paused` 이고 `hold_code` 가 자동 재개 코드면 정지를 받아 `hold_code='user'`·`hold_until=NULL`·`pause_reason='user'` 로 바꾼다. 사람의 정지는 두 열에 다 적는다(자동 재개 조회는 `hold_code` 만 본다).

## P-15 [minor] 비우기가 옛 패널 잡도 세우는데 그 사실이 옛 화면에 안 보인다 · 취소가 걸린다

- 3.5.2 는 `claim_next_job` 이 깃발을 보면 '그 틱에는 아무 잡도 집지 않는다. 잡 상태는 바꾸지 않는다' 고 한다. 사유는 새 진행 응답의 `waiting` 에만 실린다 — 옛 흐름(Tier 잡)의 진행판은 잡 행의 `error` 를 읽는다(`runner.py:744-747` 이 `pat_unavailable` 을 그렇게 적는다). 끝맺음이 깃발을 한 시간 남기거나 사람이 `--hold` 를 잊으면, 옛 흐름의 잡은 `queued` 로 사유 없이 선다.
- `claim_next_job` 은 집기 전에 `cancelling → cancelled` 를 닫는다(:730-732). 깃발을 함수 머리에서 보고 돌아가면 그동안 취소한 잡이 `cancelling` 에 걸린다.
- 6절은 고정된 깃발을 'update-all 의 헬스게이트가 누가 언제 세웠는지 말한다' 고 하는데 P1 의 조각에는 그 줄이 없다.
- 고치는 법 — R6 에서 깃발 확인을 `cancelling` 정리 **뒤**에 두고, 건너뛴 패널 잡에는 `error='draining: …(by, until)'` 을 적는다(풀리면 지운다). P1 에 §6 헬스게이트 한 줄('비우기 깃발 on · by · until/hold')을 더한다.

## P-16 [minor] `hwax_drain` 에 주소 인자가 없다 — 시험과 사람용 스크립트가 실물 9009 를 두드리게 된다

- 3.5.3 의 서명은 `hwax_drain on|off|status [ttl_s] [reason] [hold]` 다(`hwax_review_state` 는 주소를 받는다). 1f 와 끝맺음을 떼어 돌리는 P1 의 시험이 주소를 못 바꾸면 dev 의 떠 있는 에이전트 서버에 `/drain on` 이 간다(A2 가 배포된 뒤에는 실제로 30분 동안 심사와 패널 집기가 선다).
- 지금 시험은 이 때문에 구획의 주소를 지어낸 서버로 바꾸고 '실물 주소가 남았으면 실패' 를 단언한다(`test_update_all_delib_restart_gate.py:313-315`).
- 고치는 법 — `hwax_drain` 의 첫 인자 뒤에 주소를 받게 하거나 `HWAX_AGENT_HEALTH_URL` 하나로 셋이 같이 읽게 한다. P1 의 검증에 '하네스가 돌리는 본문에 `127.0.0.1:9009` 가 남지 않는다' 를 그대로 옮긴다. `review-drain.sh` 시험도 같은 규율을 쓴다.

## P-17 [minor] 그 밖의 작은 어긋남

- **깃발 파일의 자리.** 기본값 `delib_jobs.JOB_DIR.parent / "drain.json"` 은 `ARTIFACT_DIR` 를 안 준 박스에서 리포 루트다(`delib_jobs.py:48-52`). `.gitignore` 에 없어 미추적 파일로 뜬다(A2 의 파일 목록에 `.gitignore` 가 없다). 또 `review_gate.py` 가 `delib_jobs` 를 모듈 머리에서 import 하면, `/health` 가 일부러 감싼 실패(`app.py:4264-4270` '심의 MCP 가 비활성이어도 /health 는 답해야 한다')가 서버 기동 실패로 바뀐다. A1·A2 에 '`.gitignore` 에 `/drain.json`' 과 '경로는 `ARTIFACT_DIR` 에서 직접 유도한다' 를 넣는다.
- **R10 의 파일 목록.** 클라이언트를 만드는 자리는 일곱이다 — `engine_client.py:276`·`adh_client.py:98`·`ra_client.py:64`·`identity.py:91`·`roster.py:240`·`runner.py:1421`·`routes.py:127`. R10 은 넷만 든다(명단 조회·PAT 폐기 대조·PAT 등록이 빠졌다). 그리고 `trust_env=False` 는 프록시만이 아니라 `SSL_CERT_FILE` 도 끈다 — 허브가 사내 CA 를 그 변수로 넣어 준다(`integration_launcher.py:567-570`). 루프백이 아닌 https 대상(RA)이 같은 클라이언트를 쓰면 TLS 검증이 깨진다. `trust_env` 대신 `mounts={"all://127.0.0.1": None, "all://localhost": None}` 로 루프백만 프록시에서 뺀다.
- **감사 행의 scope.** 항목 다시·넘김과 상한 고치기는 `rr_audit` 한 행을 남긴다(3.11.3). `rr_audit.scope` 는 CHECK 로 열 값뿐이다(`risk_store.py:504`) — `cell`·`review` 같은 새 값은 500 이 된다. R7 에 '셀 조작은 `scope='coverage'`, 상한은 `scope='job'`' 을 적는다.
- **사슬 시험이 읽을 줄.** P3 은 `_env_float("CARD_REVIEW_TIMEOUT_S", …)` 를 읽겠다고 하는데 그 손잡이의 기본값은 수가 아니라 `DELIB_TIMEOUT_S` 를 따르는 것이다(3.8.1). 지금 식은 이름 바로 뒤의 **수**만 읽는다(`test_time_limit_chain_contract.py:49-50`) — 못 읽으면 실패다. P3 에 '따르는 식을 문자열로 확인하고 값은 `DELIB_TIMEOUT_S` 의 것을 쓴다' 를 적는다. 단언 4(AIDataHub 호출 한도)와 3.6.1 의 `HWAXRISK_AIDH_CALL_TIMEOUT_S`·`HWAXRISK_PACK_FREEZE_CONCURRENCY`·보류 `aidh_unreachable` 은 C-10 으로 대상이 사라졌다 — `/card-review/pack` 단발 호출의 줄(서버 최악 420초 < 포털 단발 600초 < 앱 660초, WP3b 553·646줄)로 바꾼다.
- **`request_worst_s` 의 식.** 3.4.3 의 식은 LLM 호출만 센다. 카드 밖 호출은 긴 문서 검색 600초가 더 든다(WP3b 594줄의 층 표). `CARD_REVIEW_TIMEOUT_S` 를 2,400 으로만 올려도 서버 최악(15,024)이 앱이 올려 쓴 벽시계(14,724)를 넘는다. 이 값은 식을 다시 적지 말고 WP3a 의 층 표가 계산해 `/health` 에 싣게 한다. 한도를 끈 박스(0)에서는 `null` 을 싣고 앱은 제 값을 쓴다.
- **사본 정리의 주기.** 3.2.5 는 '하루 한 번', 3.10.3 은 '한 시간에 한 번' 이다. 하나로 적는다.
- **heax 물음의 자리.** 3.5.3 의 물음은 `dist-from-drive.sh` 앞에서 **늘** 묻는다. 허브는 지문이 같으면 재기동을 스스로 생략하는데(`deploy-all-from-drive.sh:326-331`), 이 자리에서는 바뀐 것이 있는지 알 수 없어 심의가 도는 동안의 모든 실행이 '미뤘다' 고 말한다. nginx 블록은 이 때문에 '정말 갈아 끼울 때만' 묻는다(:486-493, 시험 `test_conf_가_그대로면_심의가_돌아도_미뤘다고_말하지_않는다`). 내려받기(캐시까지)와 설치(`_install_if_changed`)를 갈라 캐시와 설치본이 다를 때만 묻게 하면 같은 규율이 된다 — HEAXHub `dist-from-drive.sh` 에 `--fetch-only` 한 갈래를 더하는 일이다.
- **`flow`·`mode` 의 NULL.** 3.2.3 은 둘 다 NULL 허용으로 더하고 WP4 초안은 `NOT NULL DEFAULT 'panels'` 다(WP2 183줄, WP3b 1716줄). 계약 C-5 는 값만 정했다. NULL 을 허용하면 `flow = 'panels'` 로 거르는 조회가 옛 타깃을 놓친다 — `ADD COLUMN … NOT NULL DEFAULT 'panels'` 로 한 줄 정한다(상수 DEFAULT 라 허용 연산 안이다).
- **changelog 예문의 수.** 3.12 의 예문('낮에 2건·밤에 6건')은 C-24(기본 4, 챗·심의가 돌면 2, 밤 상향은 꺼짐)로 틀린 말이 된다. P4 에서 수를 다시 적는다.
- **R8 이 고치는 파일.** 끊긴 패널의 잡을 멈추는 곳은 `runner.py:785-790` `recover_running_panels` 이고 거기는 `hold_code` 를 적지 않는다(잡을 `mode` 로 가르지도 않는다 — 같은 타깃의 검토 잡까지 `paused` 로 만든다). R8 의 파일 목록은 `review_runner.py` 뿐이라 자동 재개가 볼 `hold_code='restart'` 가 생기지 않는다.

## P-18 [major] 미룬 재기동 뒤 깃발을 한 시간 남겨도 배포 창은 열리지 않는다 — 도는 패널이 그보다 길다

- 3.5.3 과 8절 5번은 '심의 때문에 재기동을 미뤘으면 비우기를 3,600초 더 둔다 — 그동안 새 패널이 시작되지 않아 다음 실행에 틈이 열린다' 고 한다.
- 패널은 타깃당 직렬이다(`runner.py:733-737`). 도는 패널이 있는 동안에는 깃발이 없어도 그 타깃의 다음 패널이 시작되지 않는다 — 깃발이 일하는 것은 **도는 패널이 끝난 뒤**뿐이다.
- 패널 하나는 몇 시간이다. 코드가 그렇게 적는다 — '3라운드 패널은 LLM 단계가 직렬로 약 15번 이어져 … 7.5시간이다 — 그래서 12시간이다'(`config.py` 의 `DEFAULT_PANEL_TIMEOUT_S = 43200` 주석).
- 그래서 깃발(1시간)이 패널(수 시간)보다 먼저 끝나고, 패널이 끝나는 순간 다음 쟁점 패널이 곧바로 시작된다. 쟁점 단계가 며칠 이어지는 실행에서는 `AGENT_RESTART_FORCE=1` 말고는 배포할 틈이 없다 — 1절의 첫 문장('며칠 도는 심사가 배포를 영영 막지도 않는다')과 3.1 원칙 2 가 서지 않는다.
- 고치는 법 — A1 의 깃발에 '비워질 때까지' 갈래를 둔다. `POST /drain {on:true, until_idle:true, grace_s:1800, max_s:46800}` — `delib_active + delib_queued` 가 처음 0 이 된 때부터 `grace_s` 뒤에 풀리고, 그 전에는 `max_s`(패널 벽시계 43,200 + 3,600)까지 유지한다. `_hwax_drain_finish` 는 미룬 재기동이 있으면 이 갈래로 세우고 ○ 에 '도는 심의가 끝나면 30분 창이 열린다 — 그 안에 update-all 을 다시 돌린다' 를 적는다. 8절 5번의 물음을 '몇 초 남기나' 에서 '창을 몇 분 열어 두나' 로 바꾼다. (더 단순한 길은 `HWAX_DRAIN_HOLD_S` 의 기본을 46,800 으로 올리는 것인데, 사람이 잊으면 13시간 동안 심사가 선다.)

## P-19 [major] 실패한 칸 하나가 뒤 단계를 전부 세운다 — 계약 C-18 과 3.3.3 의 `needs_disposition`

- 3.3.2 는 '`failed` 는 종결이 아니다 — 실행이 끝나려면 사람이 다시 또는 넘김을 정해야 한다' 고 하고, 3.3.3 은 '남은 것이 failed 뿐이면 `needs_disposition` 으로 보류, 자동 재개 없음' 이다. 계약 C-18 이 같은 문장을 받았다.
- 계약 C-5 는 검토·후처리·쟁점·종합을 **잡 종류의 사슬**로 둔다. 검토 잡이 끝나지 않으면 뒤 잡이 시작되지 않는다. WP3b 는 반대로 적었다 — '열린 실패 셀이 남아도 `completed` 다'(809줄), 보고서는 `partial` 로 낸다(374·1631줄).
- 실패 칸은 드물지 않다. 이 설계서의 리허설 가정이 내용 실패 3% 다(5.3). 상한 2회면 칸 하나가 끝내 실패할 확률이 0.1% 안팎이고 359명 × 20단위 = 7,180칸이면 예닐곱 칸이다. 거기에 다시 돌려도 낫지 않는 것(`context_overflow`, 명단에는 있는데 카드를 못 받은 전문가의 `pack_fetch_failed`)이 더해진다.
- 결과 — 며칠 도는 무인 실행이 거의 매번 검토 단계 끝에서 사람을 기다린다. 그동안 교차·쟁점·전문가 보고서·종합이 하나도 나오지 않는다. 3.1 의 '프로세스가 어디서 죽어도 사람 손 없이 이어 돈다' 와 목표('모든 전문가의 상세 보고서')에 닿지 못한다.
- 고치는 법 — 계약 C-18 을 이렇게 고쳐 적는다. '`failed` 는 **타깃의 완결 판정**에서 종결이 아니다(완결을 못 받는다). 잡은 열린 칸이 0 이면 `completed` 로 닫고 뒤 잡을 잇는다.' `needs_disposition` 은 보류 코드에서 빼고, 진행 응답의 `failures` 와 `notes`(⚠ '실패한 칸 N — 다시 또는 넘김을 정해야 완결된다')·보고서의 '보지 못한 것' 으로 낸다. 사람이 '다시' 를 누르면 그 칸만 도는 작은 검토 잡이 생기고 그 전문가의 보고서가 판을 올려 다시 나온다(WP3b 1631줄의 규칙 그대로).

## 덜어낼 것(cuts) — 이번 목표에 없어도 되는 장치

1. **`hello` 프레임 · `review_unsupported` · 빈 탐침 · 보류 `agent_outdated`/`portal_outdated` 두 갈래.** C-12 로 전용 엔드포인트가 생겨 옛 판은 404 로 갈린다. `GET /agent/card-review/limits` 한 번이 같은 일을 한다. 잃는 것 — 없다.
2. **밤·주말 창 전부**(`CARD_REVIEW_CONCURRENCY_NIGHT`·`NIGHT_HOURS`·`NIGHT_WEEKENDS`·`TZ`·`in_night`·`AgentEnv.night`·`scope.window='night_only'`). C-24 가 이미 기본을 꺼 두었다. 코드까지 미루면 시간대·자정 넘김 시험과, `night_only` 실행이 낮 내내 `running` 으로 앉아 `RUNS_PARALLEL=1` 뒤의 실행을 굶기는 문제가 같이 없어진다. 잃는 것 — 밤에 스스로 빨라지는 것(시범에서 낮 상한이 챗을 밀어내는 것이 확인된 뒤에 넣는다).
3. **밀림 감지로 상한을 내리는 장치**(`CONCURRENCY_ON_STALL`·`STALL_COOLDOWN_S`·`stalled_recently`). 계수(`chat_stall_total`·`seat_lost_total`)는 시범의 판정 기준이라 남긴다. 잃는 것 — 챗이 밀릴 때 10분 동안 스스로 물러나는 것(사람이 상한을 내리면 된다).
4. **도는 중의 예산 보류**(`budget` 보류 · `llm_calls_cap` · `PUT /jobs/{id}/budget` · `max_cells` · `MAX_CALLS` 의 거절 · S0 뒤의 두 번째 재기). 만들 때의 추정과 동의는 남긴다. 되묻기가 끝없이 도는 고장은 칸마다의 상한(차감 2 · 시도 20 · 되묻기 2)이 이미 막는다. 잃는 것 — 모르는 고장이 호출을 태울 때의 마지막 그물. 대신 얻는 것 — 추정이 1.25배를 넘겼다는 이유로 밤중에 서는 일이 없다.
5. **`rr_metrics` 의 검토 지표 12종과 하루 한 번 재계산 틱**(3.10.3 · R9 의 절반). 타깃별 값은 진행 응답이 내고 품질 지표는 C-29 의 `review_quality.py` 가 맡는다. 모델 귀속 고치기(`source_models`)는 남긴다 — 다만 키는 WP3b 의 `source_id → rr_expert_reports.model` 이다(7.1 의 '`panel_id` 자리에 `rc-…`' 는 WP3b 가 `panel_id` 를 NULL 로 두므로 읽을 것이 없다). 잃는 것 — 과제를 가로지른 추세 행.
6. **쓰이지 않는 카드 묶음 정리**(`HWAXRISK_PACK_RETAIN_DAYS` · `last_used_at`). 내용 주소라 카드가 바뀔 때만 수십 MB 가 는다. 정리 조건('어느 셀·로스터도 가리키지 않고')은 C-9 로 결속이 `rr_expert_reports` 로 옮겨져 틀린 표를 본다 — 잘못 지우면 인용 재대조가 깨진다. 잃는 것 — 디스크 수십 MB.
7. **반출의 표 고르기**(`?tables=` · `X-Risk-Export-Rows`). 잃는 것 — GB 급 반출을 나눠 받는 길(들여오기가 통째로 메모리에 올리는 문제는 어차피 남는다 — 9절).
8. **끊긴 쟁점 패널의 자동 재개**(R8 · `HWAXRISK_PANEL_AUTORESUME_MAX_S`). 신호가 박스 전체의 `delib_active` 라 남의 심의가 돌면 6시간 뒤 조건 없이 재개하고, 그때는 지금 규칙이 막으려던 겹침이 다시 난다. 고칠 자리(`recover_running_panels`)도 걸음에 없다. 잃는 것 — 쟁점 단계에서 앱이 재기동하면 사람이 재개를 눌러야 한다(지금 Tier 잡과 같다).
9. **update-all 이 도는 셀을 기다리는 600초**(`hwax_review_wait` · `HWAX_DRAIN_WAIT_S`). 3.1 원칙 1 이 '셀은 끊겨도 싸다' 이다. 며칠 도는 실행 동안의 모든 update-all 이 10분씩 길어지고, 그 10분이 깃발 수명을 먹는다(P-04). 잃는 것 — 배포마다 도는 호출 몇 건의 LLM 시간.
10. **R10(루프백은 프록시를 타지 않는다).** 지금 cae00 에서 깨졌다는 근거가 없고(9절), 목록이 절반이며 `SSL_CERT_FILE` 을 같이 끄는 위험이 있다. 사전 점검이 실제로 닿아 보므로, 닿지 않는다는 것이 확인된 뒤에 넣는다. 잃는 것 — 없다(확인 전에는).
11. **v4 블록의 읽는 곳 없는 열.** 한 번 넣은 열은 지울 수 없다(3.2.1). `carried_from` · `ix_rr_cells_input`(재사용은 C-18 로 구현하지 않는다) · `rr_roster.pack_hash`·`cards_n`(C-9) · `rr_card_packs.source_box`·`last_used_at` · `chunks_total`·`chunks_done`('표시일 뿐') · `rr_jobs.stage`·`parent_job`(C-5 의 잡 사슬과 겹친다)은 읽는 코드가 정해진 뒤에 다음 버전으로 더한다.


## 직접 확인해 맞았던 주장

- `MIGRATIONS` 는 v2 까지이고 버전 하나가 트랜잭션 하나다(`risk_store.py:562·608-646`). 설계 3.2.3 의 DDL 34문장을 지금 분할기(`_split_statements`)로 나눠 v2 메모리 DB 에 한 트랜잭션으로 넣어 봤다 — 오류 0, 가운데를 깨뜨리면 표 0·버전 2 로 되돌아간다(sqlite 3.37).
- 반출 표 목록은 `MIGRATIONS` 의 `CREATE TABLE` 에서 저절로 나온다(`export.py:20-34`). `owner_sub`·`visibility` 가 둘 다 없는 표는 거르지 않고 전부 싣는다(:178-182).
- `rr_jobs.pause_reason`·`rr_metrics.dimension`·`rr_audit.scope` 는 CHECK 어휘다. `rr_panels.tier`·`rr_jobs.tier` 에는 CHECK 가 없다(계약 C-6 의 `tier='I'` 가 선다).
- `_loop` 에는 `panel_loop`·`sync_loop` 분기뿐이다 — 야간 잡은 돌지 않는다(`runner.py:1485-1500`).
- `/health` 의 `delib_active` 는 `len(_DETACHED_TASKS) + delib_jobs.running_count()` 이고 `context_tokens` 가 이미 실린다(`app.py:4264-4283`). `start.sh` 는 그 둘을 `grep` 으로 읽는다(:105-112).
- heax 블록에는 심의 물음이 없고(`deploy-all-from-drive.sh:292-337`), `dist-from-drive.sh` 는 바뀐 앱 SIF 를 `cp -p` 로 제자리에서 덮는다(:40·:84), 지문에 `var/sifs` 가 든다(:326).
- 허브는 45초마다 정합을 돌리고(`celery_app.py:70-73`) 탐침은 주소 넷·2초다(`integration_launcher.py:88·1364-1382`). 인스턴스가 살아 있으면 그 안에 서버를 하나 더 `exec` 한다(:582-623).
- 매니페스트 `launch.env` 는 호스트의 `APPTAINERENV_*` 를 이긴다(`apt_runner.py:213-220`). `test_manifest.py:68` 이 `launch.env` 를 두 키로 못 박는다. 두 매니페스트 사본은 지금 같다.
- 에이전트 서버에는 `.env.example` 이 없다. 포털에는 `/agent/*` 를 통째로 넘기는 길이 없어 `/drain` 이 포털로 새지 않는다(`agent/routes.py` 의 라우트 22개를 훑었다).
- `cae00` 의 `appdata-merge-from-drive.sh` 는 모든 `.db` 를 `cp` 로 사본을 뜨고(:35) 지우는 코드가 없다.

## 확인하지 못한 것

- cae00 에서 update-all 한 번이 실제로 몇 분인지(P-04 는 Drive 속도와 상한 없는 단계에서 추정했다).
- 리스크 앱 SIF 안의 uvicorn 판(P-12 의 '기동 먼저, 포트 나중' 은 호스트의 0.49 에서 봤다).
- cae00 의 HEAXHub `.env` 가 모든 기동 경로에서 실리는지(P-07 — `start.sh`·`redeploy-app.sh` 는 싣는다).
- 포털의 새 중계(`/agent/card-review/*`)가 앱 쪽 연결이 끊겼을 때 에이전트 서버 쪽 연결을 닫는지 — WP3a 의 몫이고 5.2 의 2번 시험은 에이전트 서버 안에서만 본다(포털을 지나는 모양은 시험에 없다).
- update-all.sh 는 2,373줄 가운데 잠금·정지 규율·§2·§4·§5 의 해당 줄만 읽었다. 형제 설계서는 접점만 읽었다.
