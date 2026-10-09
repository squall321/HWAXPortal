# WP3b 설계서 — 리스크 앱 쪽 셀 원장 · 셀 러너 · 카드 묶음 동결 · 판정 검증 · 전문가별 보고서

작성 2026-10-09. 대조한 코드는 dev HEAD(HWAXRisk 7248651 · HWAXAgentServer 7683125 · AIDataHub 9eb744d · HWAXPortal 00d5565)다.
줄 번호는 그 시점 것이다. 구현할 때는 줄 번호가 아니라 함수 이름으로 다시 찾는다.

---

## 1. 목적과 범위

### 1.1 목적

전문가가 **혼자** 자기 지식카드 전부를 검토 단위 하나에 대조한 결과를, 리스크 앱이 (전문가 × 검토 단위) 칸마다 받아 적고, 코드로 검증하고, 전문가마다 상세 보고서 한 편으로 조립한다.
'빠짐없이 봤다' 를 문장이 아니라 **행 수로 셀 수 있게** 만드는 것이 이 꾸러미의 일이다.

### 1.2 하는 것

| # | 무엇 | 산출 |
|---|---|---|
| 1 | 셀 원장 | 표 `rr_review_cells` · `rr_card_verdicts` · `rr_expert_reports` · `rr_card_packs` · `rr_review_calls`(추가 제안), 상태기계 |
| 2 | 셀 러너 | `panel_loop` 과 별개인 `review_loop`(자기 세마포어, 타깃 안 병렬), `rr_jobs.mode='reviews'` 잡 |
| 3 | 엔진 호출 클라이언트 | 에이전트 서버 `card_review`(WP3a)의 네 끝점을 포털 경유로 부르는 `PortalReviewEngine`(대화 생성 없음) |
| 4 | 카드 묶음 동결 | WP3a 의 팩 응답을 통째로 gz 로 얼리고 해시를 남긴다. 호출마다 거기서 꺼낸 카드를 **그대로** 되보낸다 |
| 5 | 검증(코드) | 판정 행 집합 == 실은 카드 집합, 인용의 묶음 소속, 인용 문구 재대조, 수치, 카드 confidence 로 등급 |
| 6 | 표본(결정론) | 이중 판정 · 음성 재질의의 표본을 해시로 뽑는다. '해당 없음' 표본 재검토(WP4 가 뽑는다)에는 다시 열기와 결과 기록을 내준다 |
| 7 | finding 승격 | 카드 판정 · 카드 밖 리스크 · 입력 결손 질문 1 의 답을 `rr_findings` 로, 등록부 지지 수를 전문가 수로 |
| 8 | 전문가별 보고서 | 코드 조립(LLM 0회), 저장, REST · MCP 응답 계약 |
| 9 | 기존 원장 연결 | `rr_coverage` 롤업을 닫는 규칙, `rr_seat_opinions` 한 행, 쟁점 패널과 겹치지 않는 cycle 대역 |

### 1.3 하지 않는 것

- 검토 단위를 만드는 일(`rr_units` · `rr_unit_builds`, 근거 꾸러미, 결정적 관련성 신호, 로스터의 입력 결손 표기)은 WP2 다. 나는 읽기만 한다.
- 에이전트 서버 `card_review` 모듈(카드 정규화 · 예산 · 프롬프트 · LLM 호출 · 호출 안 보충)은 WP3a 다. 이 문서는 그 계약을 **쓰는 쪽**이다. 프롬프트 정본은 그쪽에 있고 여기에는 앱이 채워 보내는 칸의 글만 적는다.
- 교차 셀(`rr_cross_cells`) · 메커니즘 셀(`rr_mech_cells`) · 2차 영향 호출(`cross`) · 쟁점 패널 편성 · 영역 요약 · 종합 보고서 · `close_level` 재정의는 WP4 다. 나는 그쪽이 읽을 집계 함수와 cycle 대역 규칙만 준다.
- 스키마 버전 번호 배정 · 배포 · update-all 의 '비우기' 신호는 WP5 다.
- 프론트(`frontend/`)는 다른 세션이다. 응답 필드 계약까지만 적는다.
- 이번 판에서 미루는 것 — 타깃 간 셀 승계(같은 단위 내용 해시 · 같은 카드 묶음 해시면 이전 결과 재사용). 승계에 쓸 열(`unit_hash` · `pack_hash`)과 인덱스만 미리 둔다.

---

## 2. 지금 코드

이 꾸러미가 기대거나 건드리는 자리다. 전부 줄을 열어 확인했다.

### 2.1 저장소(HWAXRisk `backend/app/risk_store.py`)

| 자리 | 지금 동작 | 이 꾸러미와의 관계 |
|---|---|---|
| 561~562 `MIGRATIONS` | v1(41표) · v2(`rr_brief_calls`). 허용 연산은 `CREATE TABLE IF NOT EXISTS` · `ADD COLUMN` · `CREATE INDEX IF NOT EXISTS` 뿐이다. 버전 하나가 트랜잭션 하나다(630~639). | 새 표 5개와 `ADD COLUMN` 2건을 새 버전으로 붙인다. 기존 표의 CHECK · UNIQUE 는 못 고친다. |
| 580 `threading.RLock`, 597 `sqlite3.connect(..., check_same_thread=False)` | 프로세스에 **연결 하나**를 REST · MCP · 러너가 같이 쓴다. | 프로세스 안 쓰기는 이 락으로 직렬이다. |
| 599~600 | `PRAGMA journal_mode=WAL` · `foreign_keys=OFF`. `busy_timeout` 은 따로 걸지 않는다. 파이썬 `sqlite3.connect` 기본 `timeout=5.0` 초가 그대로다. | 다른 프로세스가 5초 넘게 쓰기 락을 쥐면 `database is locked` 다(§3.14.3). |
| 674~699 `tx()` | `with self._lock:` 안에서 `BEGIN IMMEDIATE` 를 열고 블록이 끝날 때까지 **락을 쥔다**. 재진입은 합류만 한다. | 긴 트랜잭션은 그동안 REST 읽기까지 막는다. 엔진 호출을 `tx()` 안에서 하면 안 된다. |
| 250~266 `rr_coverage` | PK `(target_key, agent_key)`, `status` CHECK 10종, `panel_id` · `opinion_id` · `model` · `reason` 열. | 전문가 롤업으로 그대로 쓴다. |
| 287~295 `rr_jobs` | 잡의 종류를 가르는 열이 없다. `pause_reason` CHECK 는 `diminishing` · `daily_cap` · `user` 셋이다. 그 밖의 정지 사유는 지금도 `error` 글과 `state_by='code:<사유>'` 로 적는다(runner.py:787~790, 1127). | 종류 열 `mode` 와 보류 열 `hold_code` · `hold_until` · `hold_n` 을 쓴다(WP5a 의 통합 초안이 더한다). |
| 311~323 `rr_seat_opinions` | `panel_id TEXT NOT NULL`, `UNIQUE(target_key, agent_key, cycle)`. | §3.4.2 의 cycle 대역으로 넘는다. |
| 325~356 `rr_findings` | `origin` CHECK 는 `llm` · `human` 둘, `claim_uid UNIQUE`, `panel_id` 는 NULL 허용. | 검토에서 올린 finding 은 `origin='llm'`, `panel_id` NULL 이고 `claim_uid` 의 머리가 `review_id` 다(§3.4.4). |
| 358~379 `rr_registry` | `support` · `contested` · `family_key` 등. | 지지 수 열은 WP4 가 더한다(§3.10.4). |

### 2.2 러너(HWAXRisk `backend/app/runner.py`)

| 자리 | 지금 동작 | 이 꾸러미와의 관계 |
|---|---|---|
| 22 `_LOOPS` | `panel_loop`(5초) · `sync_loop` · `nightly_loop` 셋. | `review_loop`(2초)을 더한다. |
| 714~760 `claim_next_job` | `rr_jobs` 를 종류 구분 없이 훑는다. 733~737 은 그 타깃에 running 패널이 있으면 건너뛰고(타깃당 직렬), 738~740 은 오늘 만든 패널이 `risk_daily_panel_cap`(기본 24) 이상이면 `daily_cap` 으로 멈춘다. | 패널 잡(`mode` 가 NULL · `panels`)만 보게 거른다. 셀은 `rr_panels` 행을 만들지 않으므로 직렬 · 일일 상한에 닿지 않는다. |
| 764~794 `recover_running_panels` | running 패널을 `error('restart')` 로 닫고 좌석을 차감 없이 pending 으로, 그 타깃의 잡을 `paused` 로 둔다(사람이 재개). 785 의 잡 조회도 종류 구분이 없다. | 패널 잡만 보게 거른다. 셀 쪽 복구는 따로 두고 **멈추지 않는다**(§3.7.6). |
| 916~932 `_diminishing`, 942~959 `_error_streak` | 둘 다 `rr_panels` 만 센다(수확 체감 3패널 · 연속 오류 3패널). | 셀에 걸리지 않는다. 손대지 않는다. |
| 1193~1216 `_stop_reader`, 1219~1243 `_progress_writer` | 잡 행을 5초 간격으로 읽어 취소 · 정지를 듣고, 60초 간격으로 `progress_json` 에 마지막 신호를 적는다. | 같은 방식을 셀 러너에 쓴다. |
| 1456~1482 `RiskRunner` | "러너는 직접 LLM 을 부르지 않는다". 세마포어는 `risk_concurrency`(기본 2) 하나다. | 검토 엔진을 주입받는 자리와 `_review_sem` 을 더한다. |
| 1528~1548 `_panel_tick` | 한 틱에 잡 하나를 집어 워커 하나를 띄운다. | 셀 쪽은 한 틱에 빈 자리만큼 채운다. |
| 477~502 `freeze_brief` | 패널이 받은 evidence 전문을 `canonical_json` → gzip → `sha256[:12]` 로 얼린다. | 카드 묶음 동결의 선례다(§3.5). |

### 2.3 엔진 클라이언트(HWAXRisk `backend/app/engine_client.py`)

- 지금 패널은 **포털 경유**다. `POST {HWAXRISK_PORTAL_BASE}/agent/chat`(SSE)에 `message = '/심의 ' + 질문`, `delib_opts` 를 싣는다(28~29, 369~376).
- 자격은 `Authorization: Bearer <PAT>` 다. 러너가 넘긴 사람이 등록한 포털 PAT(남은 수명이 `config.credential_margin_s` = 패널 벽시계 43,200 + 429 대기 3,600 + 600 = 47,400초를 넘을 때만) → 없으면 `secrets.env` 의 서비스 PAT(`HWAXRISK_PORTAL_PAT`) 순이다(254~270).
- 429(포털 `agent_semaphore` 초과)는 `EngineBusy` 로 올리고 러너가 30초 간격 · 총 3,600초까지 다시 묻는다(381~383, runner.py:1031~1071).
- 줄 사이 침묵 한도는 54,000초, 벽시계는 스트림에서 잰다(`_watched`, 123~151). 취소는 프레임마다 `should_stop` 을 물어 스트림을 닫는다.
- **실행마다 포털 대화를 하나 만든다**(358 `create_conversation`). 셀에 그대로 쓰면 셀 수만큼 대화가 쌓인다.
- 좌석 발언은 2,000자에서 자른다(44 `SAY_MAX`, 183). 상세 판정을 `turn` 프레임으로 받으면 잘린다.

### 2.4 포털 · 에이전트 서버

- 포털 `ChatRequest.message` 는 `max_length=65536` 이다(HWAXPortal `backend/app/agent/routes.py`:182). 한 전문가의 카드 전부가 평균 57,072자 · 최대 91,780자라 **`message` 에는 못 싣는다**.
- 포털 릴레이는 본문을 통째로 넘기지 않고 payload 를 **필드마다 손으로** 만든다(같은 파일 533~564). 새 필드는 `ChatRequest` 선언과 릴레이 줄 둘 다 있어야 닿는다.
- 포털 `/agent/chat` 은 챗과 같은 세마포어(`max_concurrent_chats` 64, config.py:289)를 쓰고 넘치면 큐 없이 429 다(1436~1440). 절차 러너는 그 세마포어를 쓰지 않고 자기 것을 만든다(`procedures/runner.py`:160~161).
- 에이전트 서버 `/chat` 에서 '/심의' 는 분리 태스크(`_detach_stream`)로 돌아 구독이 끊겨도 끝까지 간다(app.py:545~595, 3362). 띵킹은 분리 태스크가 **아니다**(3378). `/health` 의 `delib_active` 는 분리 태스크와 MCP 잡만 센다(4264~4282).
- 심의용 LLM 은 호출 시도 1회 1,800초 · SDK 재시도 1회다(app.py:354~356). LLM 논리 호출 1회의 최악은 2×1,800+8 = 3,608초다.
- nginx `/agent/` 는 `proxy_read_timeout 50400s`, 본문 상한 2,048 MB 다(HWAXPortal `infra/nginx/hwax.conf`:204~209, 34). `/apps/`(리스크 앱 REST)는 600초다(85~97).

### 2.5 서술 · 검증(HWAXRisk `backend/app/narrative.py`)

| 자리 | 지금 동작 |
|---|---|
| 193~219 `SpecContext` | `external_check`(213)가 `card:` · `rpt:` · `inc:` 존재 확인 자리인데 채우는 코드가 없다(`_panel_scope` 1502~1508 은 넣지 않는다). |
| 586~651 `_resolve_one` | `card` 는 `external_check` 가 None 이면 `ok=True, verified=False` 로 통과한다(644~646). |
| 496~577 `canonical_text_for` | `card` 분기가 없어 None 을 돌려준다. |
| 673~745 `resolve_cites` | 719 의 인용 대조는 정규화 없는 `quote not in canonical` 이고 canonical 이 None 이면 건너뛴다. 728~735 의 수치 대조는 claim · warrant 의 수치가 **모델이 쓴 quote 들**에 부분 문자열로 있는지만 보고, 하나라도 없으면 그 finding 의 통과한 인용 전부를 `quote_mismatch` 로 만든다. |
| 748~773 `evidence_grade_from_cites` | `card` 또는 `paper` 인용이 하나라도 있으면 '문헌·규격' 이다(768). 카드의 confidence 를 보지 않는다. |
| 933~936 `cluster_key_of` | mechanism · mechanism_detail · subject_key · change_kind 넷을 세로줄로 이은 문자열의 `sha1[:12]`. |
| 971~1055 `_normalize_finding` | finding 하나의 enum 보정 · 메커니즘 정규화 · subject 해석 · 인용 검증 · 등급(주장과 계산 중 낮은 쪽, 1030) · cluster_key 를 한다. 승격에 그대로 쓴다. |
| 1574~1812 `persist_panel_result` | 좌석 의견을 `DELETE ... WHERE panel_id = ?` 뒤 INSERT 한다(1697~1704). cycle 은 `rr_coverage.cycle`, 원장에 없는 좌석은 1 이다(1623~1632). |

`common.parse_ref` 는 `card:<rest>` 를 통째로 `record_id` 로 읽는다(common.py:183~184). 절(section) 표기가 없다.

### 2.6 등록부(HWAXRisk `backend/app/registry.py`)

- 205~206 — `support = len(서로 다른 panel_id)`, 패널이 없으면 llm 원자 수다.
- 403~418 `_recompute_contrib` — `n_raised += support` 로 통계 기여를 만든다.
- 578~586 `_is_stronger` — 사람이 닫을 때의 `support_at_decision` 과 지금 `support` 를 견준다.
- 639~668 `verdict_candidate` — `judgement='FAIL'` 이고 `contested < support` 인 클러스터가 하나라도 있으면 후보가 `no-go` 다(648, 662~663).
- 907~1036 `close_level` — C1 이 Tier A 패널 done ≥ 3 을 요구한다(944~945). 셀만 돈 타깃은 C0 에 머문다(WP4 몫).

### 2.7 편성기(HWAXRisk `backend/app/planner.py`)

- 42~58 — `done` · `done_weak` · `abstain` · `skipped` · `deferred` 는 나가는 전이가 없다. `pending` 에서 갈 수 있는 곳은 `assigned` · `skipped` 뿐이다.
- 371~382 `_queues` — pending 행만 집는다.
- 619~675 `apply_seat_results` — 원장 행이 `assigned|running` 이 아니면 그 좌석은 `updated=False` 로 넘어간다(651~653). 이미 종결된 전문가를 패널에 앉혀도 원장은 안 바뀐다.
- 832~865 `check_invariants` — (2) running 좌석이 있는데 running 패널이 없으면 위반이다(846). 셀 검토 중에 원장 행을 `running` 으로 두면 이 불변식에 걸린다.

### 2.8 AIDataHub · 반출

- 한 전문가의 카드 전부를 본문째 한 번에 주는 길이 지금은 없다. MCP `list_records(agents, doc_type, limit ≤ 100)` 는 요약만 주고 본문은 `get_record` 를 카드마다 부른다. REST `GET /api/records` 는 본문을 주지만 **`doc_type` 쿼리 인자가 없고**(AIDataHub `api_server/src/api/routes/records.py`:99~141) 응답 모델 `RecordOut` 에 `doc_type` 필드도 없다(`routes/_schemas.py`:29~49). 그래서 카드 받기는 앱이 직접 하지 않고 WP3a 의 팩 끝점에 맡긴다(§3.5).
- 리스크 앱 `AdhClient` 는 POST 만 있다(`adh_client.py`:101~117). 이 꾸러미는 거기에 손대지 않는다.
- 반출 표 순서는 `MIGRATIONS` 의 DDL 에서 저절로 나온다(`export.py`:24~33). 들여올 때 `owner_sub` 열이 없는 표는 건너뛴다(335). 이양 · 폐기는 표 목록을 손으로 든다(`routes.py`:756~776, 960~978). `tests/test_store.py`:91 은 v1 밖의 표 집합을 `{"rr_brief_calls"}` 로 못 박는다.
- MCP 도구는 14종이고 `tests/test_mcp_tools.py` · `tests/test_no_write_tools.py` 가 목록을 못 박는다.

### 2.9 읽다가 찾은 것(입력 자료와 다른 사실)

1. **같은 타깃의 두 번째 패널이 지금도 저장에서 실패한다.** `attribute_events` 는 좌석 표에 지정 반대석(`delib-baseline-defender`)을 **늘** 넣고(runner.py:153~157), `persist_panel_result` 는 그 좌석을 의견 명단에 붙여(narrative.py:1616~1621) cycle=1 로 INSERT 한다. 같은 타깃의 다음 패널이 같은 `(target_key, 'delib-baseline-defender', 1)` 을 넣으며 UNIQUE 에 걸린다. 메모리 DB 에서 실제 함수 둘로 재현했다(패널 1 통과, 패널 2 `IntegrityError: UNIQUE constraint failed: rr_seat_opinions.target_key, rr_seat_opinions.agent_key, rr_seat_opinions.cycle`). `_complete_panel` 의 트랜잭션(runner.py:1289)이 통째로 되돌아가므로 그 패널은 `running` 으로 남고, 타깃당 직렬 규칙 때문에 그 타깃은 재기동 때까지 편성되지 않는다. 입력 자료 02-fit 은 "편성기가 전문가를 타깃당 한 번만 앉혀서 드러나지 않는다" 고 적었지만 반대석은 패널마다 앉는다. cae00 에서 실제로 났는지는 확인하지 못했다. WP1 과 WP4 의 설계서도 같은 결함을 따로 찾아 적었다. 고치는 일은 WP1 이고, §3.4.2 의 cycle 대역이 같은 자리를 푼다.
2. `engine_client.py`:31 주석은 "포털이 conv kind `risk-review` 를 받지 않는다" 고 적지만 포털 `ConvCreate.kind` 는 이미 `risk-review` 를 받는다(HWAXPortal `backend/app/agent/routes.py`:230). 이 꾸러미는 대화를 만들지 않으므로 영향은 없다.
3. 입력 자료는 "REST 에 `doc_type` 인자를 더하면 전문가당 1회" 라고만 적었다. 응답에 `doc_type` 필드가 없어, 인자가 무시된 채 논문 · 특허가 섞여 와도 응답만으로는 모른다(FastAPI 는 모르는 쿼리 인자를 말없이 버린다). 그 길을 쓰는 쪽(WP1 의 옛 패널 card 인용 대조)은 본문 모양(`content.card.card_id` · `content.sections`)으로 가려야 한다.

### 2.10 형제 설계서와 맞춘 것

이 문서를 쓰는 동안 같은 폴더에 `spec-wp2-units.md` · `spec-wp3a-card-review-engine.md` 가 생겼다. 경계가 맞닿는 곳을 읽고 **그쪽 계약을 쓰는 쪽으로** 맞췄다. 남은 차이는 §7.3 에 적는다.

| 경계 | 맞춘 값 |
|---|---|
| 카드 받기 · 정규화 · 별칭 | WP3a `POST /agent/card-review/pack` 의 응답을 그대로 얼린다. 앱은 AIDataHub 를 직접 부르지 않고 정규화도 하지 않는다 |
| 배치(묶음) · 예산 | WP3a `GET …/limits` · `POST …/plan` 의 `verdict_decks` · `sweep_decks` · `manifest_pages` 를 쓴다. 앱이 글자 수로 나누지 않는다 |
| 호출 종류 | `sweep`(전수 훑기) · `verdict`(카드 대조 — 변형 `fwd` · `rev` · `solo`) · `offcard`(카드 밖) · `noinput`(입력 결손 두 질문). `cross` 는 WP4 가 부른다 |
| 판정 낱말 | `applies` ∈ yes · no · unknown, `judgement` ∈ OK · WARNING · FAIL · undetermined · na. 변경 줄은 별칭(`L01`)으로 가리키고 서버가 참조로 되돌려 준다 |
| 실패 구분 | `error{code, infra, retryable, knob}` 의 `infra` 가 차감 여부를 정한다 |
| 검토 단위 | WP2 `units.packets` · `units.review_payload` · `unit_signals.for_cell` · `planner.review_order` · `rr_roster.input_gaps_json` · `rr_targets.flow='units'` |

---

## 3. 설계

### 3.1 전체 흐름과 모듈 배치

검토 잡 하나(`rr_jobs.mode='reviews'`)가 타깃 하나를 돈다. 단계는 셋이다.

```
[plan]   격자 만들기        WP2 단위 × rr_roster → rr_review_cells, rr_expert_reports(머리)            코드, 네트워크 없음
[pack]   카드 묶음 동결     WP3a /pack → rr_card_packs(전문가, pack_hash) · /plan → 묶음 계획           LLM 0
[review] 전문가 세션 × N    (가) 훑기 → 셀 분류   (나) 카드 대조   (다) 카드 밖   → 검증 · 정산 → 마감     LLM 호출
(뒤)     WP4 의 후속        교차 · 메커니즘 사냥 · '해당 없음' 표본 재검토가 같은 루프의 자리를 쓴다(§3.7.11)
```

일의 단위는 **전문가 세션**이다. 워커 하나가 전문가 한 명을 집어 그 전문가의 셀을 끝낸다. 전문가끼리는 서로를 읽지 않으므로 세션끼리 병렬이다(타깃 안 병렬). 한 전문가 안에서는 직렬이다 — 같은 역할 · 같은 카드 묶음을 여러 단위에 연달아 보내 프롬프트의 앞부분이 겹치고, 마감(보고서 · finding · 원장)을 한 워커가 경합 없이 한다.

새 파일은 다섯이고 전부 `HWAXRisk/backend/app/` 아래다. 첫 줄에 한국어 한 줄 주석을 둔다.

| 파일 | 맡는 것 | 주요 함수 |
|---|---|---|
| `cardpack.py` | 팩 응답의 무결성 확인 · 동결 · 꺼내기 | `check_pack` · `freeze_pack` · `load_pack` · `card_text` · `cards_for` |
| `review_cells.py` | 격자 · 상태기계 · 선점 · 정산 · 복구 · 불변식 | `plan_cells` · `reset_review` · `claim_next_expert` · `release_expert` · `write_call_result` · `settle_cell` · `recover_running` · `review_invariants` · `review_summary` · `unit_domain_matrix` |
| `review_verify.py` | 받은 행의 재대조 · 표본 · 실효 판정 · 등급 | `accept_rows` · `nq` · `card_grade` · `sample_score` · `effective_rows` |
| `review_runner.py` | 검토 잡 · 전문가 세션 · 요청 조립 · 차단기 · 진행 신호 | `create_review_job` · `review_tick` · `run_expert` · `build_request` · `finalize_expert` · `Breaker` |
| `expert_report.py` | finding 승격 재료 · 보고서 조립 · 렌더 | `build_findings` · `build_report` · `load_report` · `render_report_md` · `summary_md` |

고치는 파일은 `risk_store.py`(DDL · busy_timeout) · `runner.py`(루프 추가, 잡 종류 거르기) · `engine_client.py`(`PortalReviewEngine`) · `narrative.py`(card 분기) · `common.py`(`card:…#절`) · `registry.py`(지지 수) · `planner.py`(`close_review_seat`) · `routes.py` · `mcp_server.py` · `export.py` · `config.py` · `metrics.py`(모델 조인) · `main.py`(단일 인스턴스 잠금)다.

### 3.2 스키마

버전 번호는 WP5 가 배정한다(WP2 는 커밋마다 새 번호를 제안했다 — 그 규칙이면 아래가 걸음 1 의 한 번호다). 전부 추가형이다.

새 표의 어휘 열(상태 · 종류 · 변형)에는 **`CHECK` 를 걸지 않는다**(WP5a 의 규칙). 허용 연산이 `CREATE TABLE` · `ADD COLUMN` · `CREATE INDEX` 뿐이라 한 번 건 `CHECK` 는 어휘를 늘릴 수 없게 만든다 — `rr_jobs.pause_reason` 이 그 예다(§2.1). 어휘는 열 옆 주석에 적고, 코드 상수(`review_cells.CELL_STATES` 등)와 전이 함수 · 시험이 지킨다.

```sql
-- (타깃 × 전문가) 검토 머리 + 보고서. 계획 때 만들고 마감 때 채운다.
CREATE TABLE IF NOT EXISTS rr_expert_reports (
  target_key TEXT NOT NULL, agent_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  domain TEXT NOT NULL, rank_in_domain INTEGER, tier TEXT, review_order INTEGER,   -- planner.review_order(WP2)의 사본
  input_gaps_json TEXT,                         -- rr_roster.input_gaps_json 의 사본(['ecad_absent'] 등). 비어 있지 않으면 입력 결손 전문가다
  review_id TEXT NOT NULL,                      -- sha256('review|'||target_key||'|'||agent_key)[:32]. rr_seat_opinions.panel_id · rr_coverage.panel_id · rr_findings.source_id 자리와 claim_uid 머리에 쓰는 합성 id(hex32)
  state TEXT NOT NULL DEFAULT 'planned',        -- planned | running | ready | partial | blocked (§3.3.2)
  claim_id TEXT, claimed_at INTEGER, job_id TEXT,
  retry_at INTEGER,                             -- 인프라 탓 중단 뒤 이 시각 전에는 다시 집지 않는다(백오프)
  pack_hash TEXT,                               -- rr_card_packs(agent_key, pack_hash) 결속
  pack_status TEXT NOT NULL DEFAULT 'todo',     -- todo | ok | empty | error
  pack_error TEXT, pack_attempts INTEGER NOT NULL DEFAULT 0, pack_frozen_at INTEGER,
  card_basis TEXT,                              -- cards | background_only | none
  plan_json TEXT, limits_rev TEXT,              -- WP3a /plan 응답(verdict_decks · sweep_decks · manifest_pages · oversize)과 그 판
  sweep_state TEXT NOT NULL DEFAULT 'todo',     -- todo | done | skipped | failed
  sweep_json TEXT,                              -- 훑기 결과(단위별 rel · k · why, 어느 단위와도 안 걸린 카드, 도장찍기 표지) 또는 건너뛴 사유
  cells_total INTEGER NOT NULL DEFAULT 0,
  report_gz BLOB, report_hash TEXT, report_bytes INTEGER,     -- 보고서 JSON(§3.11) gzip 과 sha256[:12]
  summary_md TEXT,                              -- ≤1500자. rr_seat_opinions.excerpt_for_rag 의 원천
  revision INTEGER NOT NULL DEFAULT 0,          -- 마감할 때마다 내용이 바뀌었으면 +1
  opinion_id TEXT, findings_n INTEGER, coverage_status TEXT,  -- 마감이 원장에 적은 값의 사본
  model TEXT, prompt_rev TEXT, norm_rev TEXT, verify_rev TEXT,
  stats_json TEXT,                              -- 판정별 건수 · 인용 검증률 · 뒤집힘 · 절단 호출 수 · 사라진 finding
  error TEXT,
  finalized_at INTEGER, created_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, agent_key));
CREATE INDEX IF NOT EXISTS ix_rr_expert_reports_state ON rr_expert_reports(target_key, state, review_order);
CREATE INDEX IF NOT EXISTS ix_rr_expert_reports_review ON rr_expert_reports(review_id);

-- (타깃 × 단위 × 전문가) 셀 원장.
CREATE TABLE IF NOT EXISTS rr_review_cells (
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, agent_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  domain TEXT NOT NULL, unit_seq INTEGER NOT NULL DEFAULT 0,
  state TEXT NOT NULL DEFAULT 'pending',        -- pending | running | reviewed | na_irrelevant | no_input | failed (§3.3.1)
  route TEXT,                                   -- review | na — 훑기 뒤의 분류(NULL = 아직)
  route_det TEXT,                               -- hit | miss | blind — 결정적 신호(WP2 unit_signals.for_cell 의 det)
  route_llm TEXT,                               -- yes | maybe | no | stamp | error | skipped — 훑기의 rel(묶음이 여럿이면 가장 센 것)
  route_forced TEXT,                            -- for_cell.forced 또는 'tier_a' | 'snap' | 'few_units' | 'no_cards' | 'filter_off' | 'human' | 'audit'
  route_json TEXT,                              -- {det: <for_cell 반환 그대로>, sweep: {rel, k[], why}} — '해당 없음' 의 신호값이 이것이다
  basis TEXT,                                   -- cards | search_only | noinput — 이 셀을 무엇으로 봤나(WP3a meta.basis)
  input_gap_json TEXT,                          -- 입력 결손 두 질문의 답 요약 {gaps[], q1_yes, q1_unknown, requests[{item, needs, because[], card}], none_reason}
  attempts INTEGER NOT NULL DEFAULT 0,          -- 내용 탓 실패만 센다
  infra_retries INTEGER NOT NULL DEFAULT 0,     -- 인프라 탓 중단(차감 없음)의 횟수
  retry_at INTEGER,
  error_class TEXT, error_code TEXT, error TEXT,              -- error_class: infra | content
  unit_hash TEXT, pack_hash TEXT, input_hash TEXT,           -- unit_hash = rr_units.content_hash + 근거 꾸러미 pack_hash. input_hash = sha256(unit_hash|pack_hash|prompt_rev|limits_rev)[:16]
  prompt_rev TEXT, verify_rev TEXT, model TEXT,
  calls_n INTEGER NOT NULL DEFAULT 0,
  prompt_chars INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER,   -- 이 셀의 호출들이 실은 글자 수 · 서버가 센 토큰 수의 합
  truncated INTEGER NOT NULL DEFAULT 0,         -- 1 = 정산에 쓴 호출 중 절단이 남아 있다(그러면 reviewed 가 될 수 없다)
  soft_over INTEGER NOT NULL DEFAULT 0,         -- 품질 한도를 넘겨 실은 호출이 있었다
  cards_expected INTEGER, cards_judged INTEGER, -- 점검 카드 수 · 실효 판정이 있는 카드 수
  n_fail INTEGER NOT NULL DEFAULT 0, n_warning INTEGER NOT NULL DEFAULT 0, n_ok INTEGER NOT NULL DEFAULT 0,
  n_na INTEGER NOT NULL DEFAULT 0, n_undetermined INTEGER NOT NULL DEFAULT 0,
  n_offcard INTEGER NOT NULL DEFAULT 0, offcard_state TEXT NOT NULL DEFAULT 'todo',   -- todo | done | none | skipped
  n_flipped INTEGER NOT NULL DEFAULT 0, n_disputed INTEGER NOT NULL DEFAULT 0,
  quote_ok INTEGER NOT NULL DEFAULT 0, quote_n INTEGER NOT NULL DEFAULT 0,   -- 카드 인용: 앱 재대조 통과 수 / 인용이 있던 행 수
  refs_ok INTEGER NOT NULL DEFAULT 0, refs_n INTEGER NOT NULL DEFAULT 0,     -- 변경 줄 참조: 그 단위 소속 확인 통과 수 / 참조가 있던 행 수
  sample_json TEXT,                             -- {dual:bool, na_audit:bool, recheck:[record_id…]} — 결정론 표본
  audit_result TEXT,                            -- clean | miss(감사로 다시 연 셀만)
  extras_json TEXT,                             -- {offcard:[…f 행…], needs:[…], inj:[…]} — 카드에 묶이지 않는 산출
  mechs_json TEXT,                              -- {raised:[code…], considered:[code…]} — WP4 의 메커니즘 격자가 읽는다(considered = 카드 밖 호출의 m.seen)
  handoffs_json TEXT,                           -- [{to_domain, note, change_refs[]}] — 훑기 · 카드 밖 호출의 h 줄. WP4 의 교차 칸이 읽는다
  claim_id TEXT, job_id TEXT,
  status_source TEXT NOT NULL DEFAULT 'code',   -- code | human
  decided_by TEXT, decided_at INTEGER, decide_note TEXT,      -- failed 의 사람 처분 · 사람이 다시 연 기록
  reopened_n INTEGER NOT NULL DEFAULT 0,
  started_at INTEGER, finished_at INTEGER, created_at INTEGER, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id, agent_key));
CREATE INDEX IF NOT EXISTS ix_rr_cells_state ON rr_review_cells(target_key, state);
CREATE INDEX IF NOT EXISTS ix_rr_cells_agent ON rr_review_cells(target_key, agent_key, unit_seq);
CREATE INDEX IF NOT EXISTS ix_rr_cells_reuse ON rr_review_cells(agent_key, unit_hash, pack_hash);

-- 카드 × 단위 판정. 한 (셀, 카드)에 변형마다 한 행, 그중 하나가 실효다.
CREATE TABLE IF NOT EXISTS rr_card_verdicts (
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, agent_key TEXT NOT NULL,
  record_id TEXT NOT NULL, variant TEXT NOT NULL,            -- variant: fwd | rev | solo
  owner_sub TEXT NOT NULL,
  alias TEXT NOT NULL, card_id TEXT, text_sha TEXT NOT NULL,
  applies TEXT NOT NULL,                        -- yes | no | unknown
  judgement TEXT NOT NULL,                      -- OK | WARNING | FAIL | undetermined | na
  cq TEXT,                                      -- 카드 본문에서 복사한 문구
  lines_json TEXT, refs_json TEXT,              -- 변경 줄 별칭(['L02']) · 서버가 되돌린 참조(['c:…'])
  why TEXT, need TEXT,
  sev TEXT, mech TEXT, path TEXT, check_kind TEXT, check_text TEXT,   -- solo 가 채운다. sev: 경미 | 중대 | 치명
  conds_json TEXT,                              -- solo 의 조건별 대조 줄([{cond, l[], met, note}])
  checks_json TEXT,                             -- 서버가 실어 준 {quote, refs, nums_missing, need, coerced}
  quote_ok INTEGER,                             -- 앱이 얼린 팩으로 다시 대조한 값. 1 실재 · 0 불일치 · NULL 인용 없음
  refs_ok INTEGER,                              -- 참조가 전부 그 단위의 것인가
  check_disagree INTEGER NOT NULL DEFAULT 0,    -- 서버의 checks.quote 와 앱의 재대조가 다르다(정규화 규칙이 갈렸다는 신호)
  grade TEXT,                                   -- 이 카드의 등급('문헌·규격' | '경험칙') — §3.8.5 표
  is_effective INTEGER NOT NULL DEFAULT 0,
  agree INTEGER,                                -- fwd ↔ rev 일치(1 · 0 · NULL = 한쪽뿐)
  deck_id TEXT, call_id TEXT NOT NULL, created_at INTEGER,
  PRIMARY KEY(target_key, unit_id, agent_key, record_id, variant));
CREATE INDEX IF NOT EXISTS ix_rr_verdicts_eff ON rr_card_verdicts(target_key, agent_key, is_effective, judgement);
CREATE INDEX IF NOT EXISTS ix_rr_verdicts_unit ON rr_card_verdicts(target_key, unit_id, is_effective, judgement);
CREATE INDEX IF NOT EXISTS ix_rr_verdicts_card ON rr_card_verdicts(record_id, is_effective, judgement);

-- 전문가별 카드 묶음 동결본. 내용 주소(같은 내용이면 같은 행)라 타깃이 늘어도 다시 쌓이지 않는다.
CREATE TABLE IF NOT EXISTS rr_card_packs (
  agent_key TEXT NOT NULL, pack_hash TEXT NOT NULL,           -- WP3a /pack 응답의 pack_hash
  norm_rev TEXT NOT NULL, role_sha TEXT NOT NULL,
  cards_total INTEGER NOT NULL, checkable_n INTEGER NOT NULL, chars_total INTEGER NOT NULL,
  unrenderable_n INTEGER NOT NULL DEFAULT 0,
  manifest_json TEXT NOT NULL,                  -- 본문을 뺀 목록 [{alias, record_id, card_id, text_sha, checkable, type, confidence, grade, title, chars}]
  pack_gz BLOB NOT NULL,                        -- 팩 응답 전체(canonical_json gzip). 호출마다 여기서 꺼내 그대로 보낸다
  source TEXT NOT NULL, fetched_at INTEGER NOT NULL,
  PRIMARY KEY(agent_key, pack_hash));

-- 검토 호출 원장. 서버의 result 프레임 전체를 남긴다.
CREATE TABLE IF NOT EXISTS rr_review_calls (
  call_id TEXT PRIMARY KEY,                     -- 'rc-' || sha256(target|agent|kind|variant|unit|deck_id|page|seq)[:24]
  target_key TEXT NOT NULL, agent_key TEXT NOT NULL, unit_id TEXT, owner_sub TEXT NOT NULL, job_id TEXT,
  kind TEXT NOT NULL,                           -- sweep | verdict | offcard | noinput, 그리고 제공자의 호출(cross · hunt · summary … — §3.7.11)
  variant TEXT, deck_id TEXT, page_no INTEGER, seq INTEGER NOT NULL DEFAULT 0,   -- seq = 같은 논리 호출의 몇 번째 시도인가
  state TEXT NOT NULL,                          -- running | ok | infra_fail | content_fail | aborted
  cards_json TEXT,                              -- 이 호출에 실은 별칭 목록
  request_hash TEXT, input_sha TEXT,            -- 앱이 낸 본문의 해시 · 서버가 돌려준 meta.input_sha
  prompt_chars INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER,
  output_truncated INTEGER NOT NULL DEFAULT 0, soft_over INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER, queued_ms INTEGER, llm_ms INTEGER,        -- 서버 안 보충 횟수 · 자리 대기 · LLM 시간 합
  rows_expected INTEGER, rows_missing INTEGER, bad_lines INTEGER, stamp INTEGER NOT NULL DEFAULT 0,
  model TEXT, prompt_rev TEXT, norm_rev TEXT, limits_rev TEXT,
  result_gz BLOB, result_sha256 TEXT,
  error_code TEXT, error_infra INTEGER, error_retryable INTEGER, error TEXT,
  started_at INTEGER, duration_ms INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_review_calls_cell ON rr_review_calls(target_key, agent_key, unit_id, started_at);
CREATE INDEX IF NOT EXISTS ix_rr_review_calls_job ON rr_review_calls(job_id, started_at);

-- 기존 표에 내가 더하는 열은 없다. 아래는 다른 꾸러미가 더하고 내가 쓰는 열이다(같은 열을 두 번 ALTER 하지 않게 여기에 적지 않는다).
--   rr_jobs.mode('reviews') · hold_code · hold_until · hold_n      — WP5a 통합 초안(WP4 도 mode 를 쓴다)
--   rr_targets.flow · rr_roster.input_gaps_json                    — WP2
--   rr_findings.unit_id · source_kind · source_id · agent_key      — WP4
--   rr_registry.support_experts · support_domains · …              — WP4
```

설계 판단 넷을 적는다.

- **`rr_card_packs` 의 키는 `(agent_key, pack_hash)` 다.** WP3a 는 `(target_key, agent_key)` 를 제안했다. 그렇게 타깃마다 얼리면 타깃 하나에 15~20 MB(추정 — §3.14.2)가 매번 쌓인다. 카드는 자주 바뀌지 않으므로 같은 내용은 한 번만 둔다. 타깃과의 결속은 `rr_expert_reports.pack_hash` 이고, 타깃마다 달라질 수 있는 계획(`plan_json` · `limits_rev`)도 그 행에 둔다. 이 표는 `owner_sub` 가 없는 **박스 지역 사본**이고 반출 · 들여오기에서 뺀다(§3.2.1).
- **`rr_expert_reports` 가 보고서와 실행 머리를 겸한다.** (타깃 × 전문가)에 붙는 것이 다섯(묶음 결속 · 묶음 계획 · 훑기 결과 · 선점 · 보고서)인데 표를 나눌 이유가 없다.
- **`rr_review_calls` 를 더한다.** 셀 하나가 호출 여러 번(묶음 · 뒤집기 · 단독 · 카드 밖)으로 닫히므로 시도별 실패 사유와 서버의 `result` 를 셀 행에 담을 수 없다. WP3a 도 '앱 원장이 `result` 전체와 `meta` 의 정본' 이라고 적었다. 원답이 없으면 검증 규칙을 고친 뒤 다시 풀 수 없다(패널의 `brief_gz` · `rr_panel_calls` 와 같은 이유다). 프롬프트 원문은 싣지 않는다 — 동결한 팩 + 단위 + `prompt_rev` + 별칭 목록으로 다시 만들 수 있고 `input_sha` 가 같은 입력이었음을 확인해 준다.
- **`failed` 의 사람 처분과 재시도 대기는 상태가 아니라 열이다.** 공통 계약의 상태 6종을 그대로 지킨다. 사람이 '그대로 닫는다' 고 한 실패는 `state='failed'` + `decided_by` 가 있는 행이고, 백오프 중인 셀은 `state='pending'` + `retry_at` 이다. 행 누락 · 절단 · 도장찍기 · 검색 근거만도 상태가 아니라 열이다(WP3a 의 제안과 같다).

#### 3.2.1 새 표가 닿는 기존 목록

| 자리 | 고칠 것 |
|---|---|
| `tests/test_store.py`:91 | v1 밖 표 집합에 새 표 5개(와 다른 꾸러미의 표)를 더한다. |
| `export.py` | `LOCAL_ONLY_TABLES = ("rr_card_packs",)` 를 두고 `iter_lines` · `row_digest` 가 건너뛴다. `_SINCE_COLS` 에 `rr_review_cells`(`updated_at`) · `rr_expert_reports`(`updated_at`) · `rr_review_calls`(`started_at`) · `rr_card_verdicts`(`created_at`)를 더한다. |
| `routes.py` `TRANSFER_DERIVED`(763~776) | `rr_review_cells` · `rr_card_verdicts` · `rr_expert_reports` · `rr_review_calls` 를 `target_key IN (…)` 조건으로 더한다. 빠뜨리면 이양 뒤 새 소유자 반출에서 사라진다. |
| `routes.py` `PURGE_BLANK_SQL`(960~978) | `rr_card_verdicts`(`cq` · `why` · `need` · `path` · `check_text` · `conds_json` 을 NULL) · `rr_expert_reports`(`report_gz` · `summary_md` · `sweep_json` NULL) · `rr_review_cells`(`extras_json` · `route_json` · `input_gap_json` NULL) · `rr_review_calls`(`result_gz` NULL). 카드 묶음은 과제 자료가 아니라 사내 지식 사본이라 지우지 않는다. |
| `rr_audit.scope` CHECK | `cell` 이 없다. 셀을 사람이 옮긴 기록은 `scope='coverage'`, `subject_id='<target_key>#<unit_id>#<agent_key>'`, `action` 은 `cell.reopen` 또는 `cell.dispose` 로 적는다. |

### 3.3 상태기계

#### 3.3.1 셀(`rr_review_cells.state`)

| 상태 | 뜻 | 종결인가 |
|---|---|---|
| `pending` | 아직 안 봤다(백오프 중이면 `retry_at` 이 미래다) | 아니다 |
| `running` | 워커가 쥐고 있다(`claim_id` 있음) | 아니다 |
| `reviewed` | 봤다. 카드 대조 길이면 `cards_judged == cards_expected` · `truncated = 0` · 카드 밖 호출이 끝났다. 입력 결손 길이면 질문 1 에 답이 있다 | 그렇다 |
| `na_irrelevant` | 해당 없음. 결정적 신호가 `miss` **그리고** 훑기가 전 묶음에서 `no` **그리고** 도장찍기가 아니다 | 그렇다 |
| `no_input` | 입력 결손. 입력 결손 전문가가 두 질문 호출에서 질문 1 에 답할 것이 없다고 했다(§3.7.4) | 그렇다('검토함' 으로 세지 않는다) |
| `failed` | 내용 탓 실패를 시도 한도(기본 2)까지 썼다. 사유 · 시도 수가 남는다 | 사람 처분 전에는 '열린 실패' 다 |

허용 전이는 아래가 전부다. 표에 없는 전이는 `review_cells._move()` 가 예외로 막는다.

| 에서 | 으로 | 누가 · 언제 |
|---|---|---|
| pending | running | 워커가 셀의 첫 호출을 시작할 때(선점 id 대조) |
| pending | na_irrelevant | 훑기 직후 분류(§3.7.4 표). `route_det='miss'` 이고 `route_forced` 가 비어 있을 때만 |
| running | reviewed | 정산 성공 |
| running | no_input | 입력 결손 두 질문 호출의 정산(질문 1 에 `yes` 가 없고, `unknown` 이 있거나 질문 2 에 요청이 있다) |
| running | pending | 인프라 탓 중단 · 사람의 정지 · 취소 · 앱 종료 · 재기동 복구. `attempts` 를 올리지 않는다. `infra_retries` 만 올리고 `retry_at` 을 건다(정지 · 취소 · 재기동은 그것도 안 한다) |
| running | pending | 내용 탓 실패이고 `attempts + 1 < 한도`. `attempts` 를 올린다 |
| running | failed | 내용 탓 실패이고 `attempts + 1 ≥ 한도`, 또는 `infra_retries` 가 상한(기본 6)을 넘겼다(`error_code='infra_exhausted'`) |
| failed | pending | 사람이 다시 연다(`attempts` · `infra_retries` 를 0 으로) |
| na_irrelevant · no_input | pending | 사람이 다시 열거나 감사 표본으로 뽑혔다(`route='review'`, `route_forced` 는 `human` 또는 `audit`) |
| reviewed | pending | 사람이 `force` 로 다시 열 때만. 그 셀의 판정 행을 같은 트랜잭션에서 지운다 |

`failed` 에 `decided_by` 가 찍히면 '사람이 닫은 실패' 다. 상태는 그대로다.

`no_input` 은 **호출을 한 뒤에만** 생긴다. 코드가 '이 전문가는 ECAD 가 없으니 못 본다' 고 미리 닫지 않는다 — 기구 변경이 회로에 주는 영향(보드 휨 · 스웰링 간극 · 접지 금속과의 거리)은 ECAD 없이도 말할 수 있고, 그것을 묻는 것이 질문 1 이다.

#### 3.3.2 전문가(`rr_expert_reports.state`)

| 상태 | 뜻 |
|---|---|
| `planned` | 열린 셀이 있고 아무도 쥐지 않았다 |
| `running` | 워커가 쥐고 있다 |
| `ready` | 열린 셀이 0 이고 마감했다. 열린 실패도 0 이다 |
| `partial` | 열린 셀이 0 이고 마감했다. 사람이 닫지 않은 `failed` 셀이 남았다 |
| `blocked` | 카드 묶음을 못 받았다(`pack_status='error'`). 백오프 뒤 다시 받는다 |

전이는 `planned → running`(선점), `running → planned`(놓음), `running → ready | partial`(마감), `ready | partial → planned`(셀이 다시 열림), `planned → blocked`(묶음 실패), `blocked → planned`(묶음 성공)다.

#### 3.3.3 검토 잡(`rr_jobs`, `mode='reviews'`)

상태 어휘는 패널 잡과 같다(`queued` · `running` · `paused` · `cancelling` · `cancelled` · `completed` · `failed`). 다른 점은 셋이다.

- 단계가 `progress_json.phase` 에 있다(`plan` → `pack` → `review` → `done`). WP5a 의 `rr_jobs.stage` 열이 생기면 그 열에도 같은 값을 적는다.
- 코드가 멈춘 정지는 `state='paused'` + `hold_code` 다(WP5a 가 더하는 열 — `pause_reason` 은 CHECK 때문에 사람의 정지 `user` 에만 쓴다). 코드는 `breaker`(인프라 실패율) · `content_fail_rate` · `pack_unavailable` · `contract`(요청 계약 불일치 · 권한)다. 사유 글은 지금처럼 `error` 에 적는다.
- `breaker` 와 `pack_unavailable` 은 `hold_until` 이 지나면 **스스로 `queued` 로 돌아온다**. `hold_n` 이 백오프 단계다. 사람이 멈춘 것과 `content_fail_rate` · `contract` 는 사람이 재개한다.

타깃 하나에 살아 있는 검토 잡은 하나다(`queued` · `running` · `paused` · `cancelling` 이 있으면 새로 만들 때 409 `review_job_exists`).

비우기(update-all 이 세우는 신호)와 서버 관문의 '자리 없음' 은 정지가 아니라 **기다림**이다(WP5a 의 구분). 잡은 `running` 인 채 새 호출을 내지 않고, 진행 응답에 사유가 보인다. 그 신호를 읽는 법은 WP5a 가 정한다 — 이 꾸러미는 `should_stop` 과 선점 직전에 묻는 자리 둘을 내준다(§7.2).

### 3.4 기존 원장과의 관계

#### 3.4.1 `rr_coverage` — 전문가 롤업을 언제 닫나

검토가 도는 동안 원장 행은 **`pending` 그대로 둔다**. `running` 으로 옮기면 '도는 패널이 없는데 running 좌석이 있다' 는 불변식 (2)(planner.py:846)에 걸리고, 수백 행이 며칠씩 running 으로 보인다.

닫는 때는 **그 전문가의 열린 셀(`pending` · `running`)이 0 이 되는 순간**이고, 닫는 일은 그 전문가를 쥔 워커의 마감(`finalize_expert`)이 한 트랜잭션으로 한다. 셀이 다시 열렸다 닫히면 마감이 다시 돈다(멱등).

원장에 적는 값은 아래 표로 정한다. 위에서부터 처음 맞는 줄이다.

| 조건(그 전문가의 셀) | `rr_coverage.status` | `reason` |
|---|---|---|
| `reviewed` 0 이고 전부 `na_irrelevant` | `abstain` | `na_all` |
| `reviewed` 0 이고 `no_input` 이 하나라도 있고 나머지는 `na_irrelevant` | `abstain` | `no_input:<gap>`(WP2 의 규약 — 예 `no_input:ecad_absent`. 완결 판정이 이 reason 을 보고 '검토함' 에서 뺀다) |
| `reviewed` 0 이고 열리지 않은 셀이 전부 `failed` | 닫지 않는다(`pending` 유지) | — |
| `reviewed` ≥ 1 이고 **검증된 근거**가 있다 | `done` | 실패 셀이 있으면 `partial:<n>` |
| `reviewed` ≥ 1 이고 검증된 근거가 없다(카드 0장 전문가 포함) | `done_weak` | `no_verified_cite` 또는 `no_cards` |

'검증된 근거' 는 실효 판정 행 가운데 `quote_ok = 1` 이고 `refs_ok = 1` 인 행이 하나 이상 있다는 뜻이다. 판정이 OK 여도 된다 — 카드를 실제로 읽고 변경 줄을 실제로 짚었다는 증거이기 때문이다. 입력 결손 길의 셀은 질문 1 의 `yes` 행 가운데 카드 인용(`k` · `cq`)이 재대조를 통과한 것이 그 근거다.

함께 적는 열은 `opinion_id`(§3.4.2) · `panel_id = review_id` · `origin = 'primary'` · `tier`(영역 내 순위로 A · B · C) · `model` · `finished_at` 이다.

전이는 새 함수 하나로만 한다.

```python
# planner.py
def close_review_seat(store, target_key: str, agent_key: str, *, status: str, review_id: str,
                      opinion_id: str, model: str | None, reason: str | None, tier: str | None) -> dict:
    """검토 마감이 원장 한 행을 닫는다. status ∈ {'done','done_weak','abstain'}.

    행이 pending 이면 그 값으로 닫는다. 이미 이 검토가 닫은 행(panel_id == review_id)이면 값을 다시 적는다
    (실패 셀을 다시 돌려 done_weak → done 이 되는 길). 그 밖(패널이 닫았거나 deferred · skipped · carried)이면
    건드리지 않고 {'updated': False, 'status': <지금 값>} 을 돌려준다.
    """
```

`ALLOWED_TRANSITIONS['pending']` 에 `done` · `done_weak` · `abstain` 을 '검토 마감 전용' 주석과 함께 더한다. 사람 조작(`skip_seat` · `revert_carried`)의 가드는 그대로다.

옛 타깃(이미 패널이 돈 타깃)에 검토를 얹으면 종결된 행은 그대로 남고 보고서 · finding · 의견 행만 생긴다. `deferred` 행도 마찬가지다(그 행을 풀지는 WP2 가 정한다).

검토가 도는 타깃에 옛 방식 Tier 패널 잡이 같이 돌면 pending 전문가가 패널에 앉아 버린다. 그래서 `rr_targets.flow` 가 새 흐름인 타깃(WP2 가 더하는 열)과 살아 있는 검토 잡이 있는 타깃에는 `runner.create_job`(Tier 잡)이 422 `flow_mismatch` 를 돌려준다(WP4 가 같은 가드를 같은 코드로 적었다). 쟁점 패널(WP4)은 그 함수를 쓰지 않는다.

#### 3.4.2 `rr_seat_opinions` — 보고서를 어떻게 적나, 유일 제약을 어떻게 넘나

마감은 전문가마다 의견 행 **하나**를 쓴다. `seat_opinion.v1` 스키마(`additionalProperties: false`, `panel_id` 는 hex32, `cycle ≥ 1`, `raised_finding_ids` 는 `^[0-9a-f]{32}#[FG][0-9]+$`)를 그대로 지킨다.

| 필드 | 값 |
|---|---|
| `panel_id` | `review_id`(hex32). `rr_panels` 에 그 행은 없다. 이 DB 의 외래키는 문자열 계약이다(risk_store.py:592) |
| `cycle` | **`500 + rr_coverage.cycle`** |
| `opinion_id` | `narrative._opinion_id(review_id, agent_key, cycle)` — 지금 함수 그대로 |
| `origin` | `primary` |
| `turns` | 한 건 `{round: 1, say_excerpt: summary_md[:2000], position: '', stance, non_negotiable: ''}` |
| `final_stance` | 실효 판정에 `FAIL` 이 있으면 `oppose`, `WARNING` 만 있으면 `conditional`, 검토했고 둘 다 없으면 `agree`, 검토한 셀이 없으면 `abstain` |
| `tool_calls` · `tool_calls_n` · `tool_calls_ok` | `[]` · `null` · `null`(이 경로는 도구를 부르지 않는다. 0 이 아니라 '해당 없음' 이다) |
| `knowledge_hits_n` | 실효 판정이 있는 서로 다른 카드 수 — 이 열이 처음으로 실제 값을 갖는다 |
| `cited_refs` · `cited_refs_resolved` | 검증된 `card:<record_id>` 와 단위 쪽 참조 |
| `cited_ckeys` | 올린 finding 의 subject ckey |
| `quality` | `{used_tool: null, cited_ir: <단위 참조가 하나라도 검증됐나>, grade_min, dangling_n}` |
| `raised_finding_ids` | 올린 finding 의 `claim_uid`(§3.10.2) |
| `excerpt_for_rag` | `summary_md[:1500]`. 다음 과제의 E7 이 이 줄을 `narr:` 접두로 싣는다(brief.py:1001~1008). 그 접두 줄은 판단어 린터에서 빠진다(brief.py:1253, 1276) |

쓰는 방식은 패널과 같다 — `DELETE FROM rr_seat_opinions WHERE panel_id = ?`(= review_id) 뒤 INSERT. 다시 마감해도 같은 자리다.

유일 제약 `UNIQUE(target_key, agent_key, cycle)` 은 **cycle 대역을 나눠** 넘는다. 표를 고칠 수 없으므로(CHECK · UNIQUE 변경은 허용 연산 밖이다) 값의 자리를 나눈다.

| 누가 쓰는 의견 | cycle |
|---|---|
| 원장 좌석(Tier 패널의 primary · counter) | `rr_coverage.cycle` (1부터, 지금 그대로) |
| 검토(이 꾸러미) | `500 + rr_coverage.cycle` |
| 원장에 세지 않는 의견 — 지정 반대석 · 발굴석(`adversary` · `new`) · **쟁점 패널의 좌석 전부** | `1000 + rr_panels.panel_no` |

cycle 을 원장 값과 맞춰 읽는 코드는 없다(grep 으로 확인 — 쓰는 곳은 `persist_panel_result` · `revert_carried` · AIDataHub `_external_id` 뿐이다). `_external_id` 는 `opinion:<target>:<agent>:<cycle>` 이라 대역이 달라도 유일하다.

이 표의 셋째 줄이 §2.9 (1)의 결함도 같이 푼다. WP1 이 같은 결함을 찾아 `persist_panel_result` 의 원장 밖 좌석 cycle 을 `NONLEDGER_CYCLE_BASE + panel_no` 로 고친다(그 문서 3.1.1 — 기준값 1000). WP4 는 같은 규칙을 기준값 100000 으로 적었다. **두 문서의 기준값이 다르다** — 어느 쪽이든 검토 대역(500대)과 겹치지 않지만 하나로 맞춰야 한다(§7.3). 이 꾸러미는 검토 쪽 줄만 지킨다 — `REVIEW_CYCLE_BASE = 500` 을 `narrative.py` 에 상수로 두고, 원장 밖 기준값보다 작다는 것을 시험이 단언한다.

#### 3.4.3 같은 전문가가 뒤에 쟁점 패널에 다시 앉을 때

걸리는 곳이 둘이고 둘 다 위 규칙으로 풀린다.

1. **pending 만 집는 편성기**(planner.py:375) — 쟁점 패널은 원장을 소진하지 않으므로 `plan_next_panel` 을 쓰지 않는다. WP4 의 편성 함수가 좌석 목록을 직접 정해 `rr_panels` 행을 만들고 `rr_coverage` 는 건드리지 않는다. 뒤따르는 `start_panel_seats` · `apply_seat_results` · `fail_panel_seats` 는 원장 행이 `assigned | running` 일 때만 고치므로(planner.py:608~611, 651~653, 693~694) 종결된 행에는 아무 일도 하지 않는다.
2. **유일 제약** — 쟁점 패널의 의견은 `1000 + panel_no` 대역이라 검토 의견(500대)과도, 같은 전문가가 앉은 다른 쟁점 패널과도 겹치지 않는다.

#### 3.4.4 `rr_findings` · `rr_claim_refs`

검토가 올린 finding 은 `origin='llm'`, `opinion_id = <검토 의견 id>` 이고 `claim_uid` 의 머리가 `review_id` 다. `panel_id` 는 **NULL** 로 둔다(그 열은 주석대로 '패널에서 나온 것' 의 자리이고, 등록부의 패널 수 셈에 검토가 끼지 않게 한다). 대신 WP4 가 더하는 네 열을 채운다 — `source_kind='card_review'` · `source_id=<review_id>` · `unit_id` · `agent_key`. `rr_claim_refs` 는 패널과 같은 모양으로 채운다(`card:<record_id>` 행이 생기므로 `risk_claims_for_ref('card:…')` 가 '이 카드를 근거로 든 지적' 을 돌려준다). 변환 규칙은 §3.10 이다.

`metrics.panel_models`(metrics.py:466~478)는 `rr_findings.panel_id → rr_panels.model_json.model` 조인으로 모델을 찾는다. 검토 finding 은 `panel_id` 가 없으므로 그 함수가 `source_id → rr_expert_reports.model` 을 합쳐 보게 한다. 빠뜨리면 검토에서 온 finding 의 모델이 전부 `unknown` 이다.

### 3.5 카드 묶음 동결

#### 3.5.1 무엇을 얼리나

전문가 한 명의 지식카드 **전부**를 WP3a 의 팩 끝점이 정규 표기로 만들어 준 것(`POST /agent/card-review/pack` 의 응답)을 **통째로** 얼린다. 그 안에 카드마다 `alias` · `record_id` · `card_id` · `type` · `checkable` · `confidence` · `standard_refs` · `sources_n` · `sections[{sid, title, text}]` · `text_sha` · `chars` 가 있고, 팩 머리에 `role` · `role_sha` · `pack_hash` · `norm_rev` 가 있다.

앱은 카드를 정규화하지 않는다. 정규화가 두 곳에 있으면 한쪽만 고쳐졌을 때 '모델이 본 글' 과 '대조하는 글' 이 갈린다. 대신 **얼린 것을 그대로 되보내고, 대조도 그 얼린 글로** 한다. 며칠 도는 동안 카드가 고쳐져도 인용 대조가 흔들리지 않는다.

카드는 둘로 갈린다(가르는 것은 팩의 `checkable` 이다).

| 역할 | 카드 종류 | 쓰임 |
|---|---|---|
| 점검(`checkable = true`) | `design-rule` · `standard-summary` · `failure-case`, 그리고 종류를 모르는 카드 | 카드 대조에서 카드마다 판정 한 행을 받는다 |
| 배경(`checkable = false`) | `concept` · `faq` · `data` | 훑기에서 전문으로 읽히고, 카드 대조에서는 제목만, 카드 밖 호출에서는 훑기에 걸린 것이 전문으로 실린다 |

#### 3.5.2 받고 확인하고 얼린다

```python
# cardpack.py
def check_pack(pack: Mapping[str, Any]) -> list[str]:
    """받은 팩의 무결성 문제 목록(빈 목록 = 통과). 문제가 있으면 얼리지 않는다."""
def freeze_pack(store, pack: Mapping[str, Any]) -> dict:
    """rr_card_packs 에 INSERT OR IGNORE. 반환 {pack_hash, cards_total, checkable_n, chars_total, card_basis}"""
def load_pack(store, agent_key: str, pack_hash: str) -> dict:
    """얼린 팩(프로세스 안 LRU 32). {'role', 'cards': {alias: card}, 'by_record': {record_id: alias}, 'checkable': [별칭…], 'background': [별칭…]}"""
def card_text(card: Mapping[str, Any]) -> str:
    """인용 대조의 원문 — 절 text 를 줄바꿈으로 이은 것(WP3a 의 card_text 와 같은 정의). 머리 줄은 인용 대상이 아니다."""
def cards_for(pack: Mapping[str, Any], aliases: Sequence[str]) -> list[dict]:
    """요청에 실을 카드 항목 — 팩의 항목 그대로(키를 빼거나 고치지 않는다)."""
```

`check_pack` 이 보는 것은 다섯이다. 서버를 믿지 않아서가 아니라, 얼린 것이 며칠 동안 정본이 되기 때문에 들어올 때 한 번 본다.

1. `pack_hash` · `norm_rev` · `role_sha` 가 있고 `agent_key` 가 청한 키와 같다.
2. 별칭이 팩 안에서 유일하고 `record_id` 도 유일하다.
3. 카드마다 `text_sha == sha256("\n".join(f"{sid}\t{title}\n{text}"))` 다(WP3a 가 적은 식). 다르면 전송 중 손상이거나 식이 갈린 것이다.
4. `cards_total == len(cards) + len(unrenderable)`, `checkable_n == checkable 인 카드 수`.
5. 절이 하나도 없는 카드가 `cards` 에 없다(그런 카드는 `unrenderable` 에 있어야 한다).

받는 결과를 넷으로 가른다. **'0장' 과 '못 받았다' 를 섞지 않는다.**

| 응답 | `pack_status` | 그 전문가 |
|---|---|---|
| 200, `cards` ≥ 1 | `ok` | 진행 |
| 200, `cards = []` | `empty` | 진행(§3.5.5) |
| 404 `agent_not_found` | `error`(`pack_error='agent_not_found'`) | `blocked`. 로스터에는 있는데 레지스트리에 없는 키다. 다시 받아도 같으므로 백오프하지 않고 사람에게 보인다 |
| 502 `card_fetch_failed` · 통신 실패 · 시간 초과 · `check_pack` 실패 | `error` | `blocked`. 60초부터 두 배씩(상한 1,800초) 다시 받는다 |

`unrenderable`(본문이 없는 카드)이 있으면 팩은 `ok` 로 얼리고 `unrenderable_n` 을 적는다. 그 카드는 판정받을 수 없으므로 보고서의 '판정하지 못한 카드' 에 사유(본문 없음)와 함께 싣는다. 조용히 빠지지 않는다.

`card_basis` 는 `checkable_n ≥ 1` 이면 `cards`, 카드는 있는데 전부 배경이면 `background_only`, 0장이면 `none` 이다.

#### 3.5.3 묶음 계획

카드를 몇 장씩 끊을지는 앱이 정하지 않는다. 팩을 얼린 직후 `POST /agent/card-review/plan` 에 카드 목록(`alias` · `record_id` · `checkable` · `chars`)과 단위 목록(`unit_id` · `manifest_chars` · `body_chars`)을 보내 계획을 받아 `rr_expert_reports.plan_json` 에 둔다.

```json
{"limits_rev": "a1b2c3d4",
 "verdict_decks": [{"deck_id": "v1", "aliases": ["K01", "K02", "K03", "K04", "K05", "K06", "K07"], "chars": 13120, "soft_over": false},
                   {"deck_id": "v2", "aliases": ["K08", "K09", "K10", "K11", "K12", "K13"], "chars": 11480, "soft_over": false}],
 "sweep_decks":   [{"deck_id": "s1", "aliases": ["K01", "…", "K30"], "chars": 48210}],
 "manifest_pages": [["u:5d0c1e9a77b2", "u:…"]],
 "oversize": {"cards": [], "units": [], "manifest": []}}
```

- 묶음은 **전문가마다 한 벌**이다(단위마다 다르지 않다). 서버가 단위 본문 상한(`limits.verdict.unit_body_max`)을 따로 떼어 두고 카드 몫을 고정하기 때문이다. 그래서 같은 묶음을 여러 단위에 그대로 쓴다.
- `oversize.cards` 에 든 카드는 한 장만 실어도 창을 넘는다(운영 창에서는 약 9만 자를 넘는 카드라 실제로는 없을 것으로 본다). 그 카드는 판정할 길이 없으므로 셀의 `cards_expected` 에서 빼고 `stats_json.unjudged_cards` 에 사유와 함께 남긴다. 그런 카드가 있는 전문가는 마감해도 `ready` 가 아니라 `partial` 이고 보고서 머리에 '창을 넘어 판정하지 못한 카드 n장' 이 찍힌다.
- `oversize.units` 에 든 단위는 본문이 상한을 넘는다. 단위를 쪼개는 것은 WP2 의 일이다(WP2 는 `limits.verdict.unit_body_max` 를 받아 지킨다). 그래도 넘은 단위의 셀은 호출하지 않고 `failed('unit_oversize')` 다. 여기서 자르면 '전량을 봤다' 가 거짓이 된다.
- `limits_rev` 가 `/limits` 의 지금 값과 다르면(모델 · 창 · 출력 상한이 바뀌었다) 계획을 다시 받는다. 열린 셀의 `input_hash` 가 바뀌어 그 셀은 처음부터 돈다.
- `/limits` 가 `ctx_assumed: true` 면(LLM 서버에 창을 못 물었다) 계획을 짜지 않고 다음 틱에 다시 묻는다. 그 사이의 예산은 믿을 수 없다.

#### 3.5.4 언제 얼리고, 도중에 바뀌면

- **잡의 `pack` 단계에서 한꺼번에 얼린다.** 검토 루프 스레드가 틱마다 최대 8명씩 순서대로 받는다. 스레드를 따로 띄우지 않는다 — 선점 경합이 없고 정지에 곧 반응한다. 서버가 팩 빌드를 동시 2건으로 묶으므로 더 쏴도 빨라지지 않는다. 한 건의 최악은 420초(WP3a 의 계산)이고 포털의 단발 한도 600초 아래다.
- 전문가가 그 타깃에서 한 번 묶음을 받으면(`rr_expert_reports.pack_hash`) **그 타깃이 끝날 때까지 그 묶음**이다. 잡을 며칠 뒤 다시 돌려도 다시 받지 않는다. 한 전문가의 셀들이 서로 다른 판의 카드로 판정되는 일이 없다.
- 카드가 그 사이 바뀌었는지는 사람이 물을 때만 본다 — `POST /targets/{key}/packs/refresh` 가 다시 받아 `pack_hash` 를 견주고 달라진 전문가를 돌려준다. 기본은 **알리기만** 한다. `reopen=true` 를 줘야 그 전문가의 묶음을 새 것으로 갈고 셀을 다시 연다(그 셀들의 `input_hash` 가 달라지므로 옛 판정 행은 지워진다).
- `pack_hash` 에는 역할 해시도 들어간다(WP3a 의 정의). 역할 문서만 고쳐져도 다른 묶음이다. 타깃 안에서는 얼린 것을 쓰므로 영향이 없다.
- 전부 못 받으면(게이트웨이 · AIDataHub 불통) 차단기가 잡을 보류 코드 `pack_unavailable` 로 멈춘다(§3.7.6).

#### 3.5.5 카드 0장 · 배경 카드뿐

| 경우 | `card_basis` | 처리 |
|---|---|---|
| 점검 카드 ≥ 1 | `cards` | 훑기 → 카드 대조 → 카드 밖 |
| 카드는 있는데 전부 배경 | `background_only` | 훑기는 한다. 카드 대조는 묶음이 0개라 부르지 않는다. 카드 밖 호출을 긴 문서 검색과 함께 부른다 |
| 카드 0장(지금 3명 — `material-twin-analyst` · `sim-structural-calc` · `sim-thermal-sed`) | `none` | 훑기를 건너뛴다(`route_forced='no_cards'` — 볼 카드가 없는 전문가는 '해당 없음' 을 낼 수 없다). 전 단위에 카드 밖 호출을 긴 문서 검색과 함께 부른다 |

뒤의 둘은 셀이 `reviewed`(`cards_expected = 0`, `basis = 'search_only'`)로 닫히고 원장은 `done_weak`(`reason='no_cards'`)이며 보고서 머리에 '카드 결손 전문가' 라고 적는다. 올린 finding 은 전부 경험칙 등급이다. material 전문가의 물성 카드 2,688건은 팩에 들지 않는다(`doc_type` 이 다르다). 재료 변경의 전후 물성은 WP2 의 근거 꾸러미가 단위에 싣고, 나머지는 카드 밖 호출의 검색이 받는다.

긴 문서 검색어는 앱이 만든다. WP2 의 `units.roster_query(store, target_key)` 가 주는 구절(부품 역할 · 재질 · 변경 낱말)에서 그 단위에 해당하는 것을 3개까지, 300자 안으로 쓴다. `summary_text` 의 머리(신원 줄)로 만들지 않는다. `exclude_record_ids` 에는 팩의 카드 id 전부를 넣는다.

### 3.6 엔진 호출

#### 3.6.1 길과 자격

**포털 경유를 유지한다.** 에이전트 서버에는 인증이 없고 포털이 인증 경계다. 리스크 앱이 에이전트 서버에 직접 닿는 것은 지금 `/health` 읽기 하나뿐이다(engine_client.py:308~312). 그 원칙을 깨지 않는다.

다만 `/agent/chat` 은 못 쓴다. `message` 가 65,536자 상한이고(§2.4), 챗과 같은 세마포어를 쓰며, 대화 저장이 붙어 있다. WP3a 가 정한 전용 중계 넷을 부른다.

| 포털 경로 | 방식 | 앱이 언제 부르나 |
|---|---|---|
| `GET /agent/card-review/limits` | JSON | 잡의 `pack` 단계 처음, 그리고 `limits_rev` 가 어긋났다는 답을 받았을 때 |
| `POST /agent/card-review/pack` | JSON | 전문가마다 한 번(`pack` 단계) |
| `POST /agent/card-review/plan` | JSON | 팩을 얼린 직후 전문가마다 한 번 |
| `POST /agent/card-review/run` | SSE | 호출 1건마다 |

포털은 본문을 통째로 넘기고 신원 칸(`groups` · `user_email` · `user_pat` · `entitlements`)만 검증된 주체에서 덮어쓴다. **대화를 만들지도 저장하지도 않는다.** 정본은 리스크 앱 DB(`rr_review_calls`)다. 권한 키는 심의와 같은 `feat:deliberation` 이다 — 오늘 패널을 돌릴 수 있는 러너 자격이면 셀도 돈다.

자격 규칙은 패널과 같고 **여유만 다르다**.

```python
# config.py
DEFAULT_REVIEW_CALL_TIMEOUT_S = 18000      # 검토 호출 1건의 벽시계(HWAXRISK_REVIEW_CALL_TIMEOUT_S, 0 = 끔)

def review_call_timeout_s(cfg=None) -> int: ...
def review_credential_margin_s(cfg=None) -> int:
    """검토 호출에 사용자 PAT 를 쓰려면 남아 있어야 하는 수명 = 호출 벽시계 + 429 대기 예산 + 600."""
```

- 호출 벽시계 18,000초의 근거 — 서버 쪽 요청 1건의 최악이 15,024초다(자리 대기 3,600 + 긴 문서 검색 600 + 보충 포함 3 × 3,608 — WP3a 의 층 표). 앱의 한도는 그보다 커야 서버의 구체적인 사유가 먼저 온다. 살아 있는 호출을 자르지 않는 쪽으로 넉넉히 잡는다.
- 자격 여유는 18,000 + 3,600 + 600 = 22,200초다. PAT 등록 하한 86,400초(routes.py:36)보다 작아 사슬이 뒤집히지 않는다. 패널 여유(47,400초)보다 작으므로 **호출마다** 자격을 다시 고른다 — 수명이 7시간 남은 PAT 도 셀은 돌린다.
- 줄 사이 침묵 한도 · 429 간격 · 429 총 예산은 지금 손잡이(`HWAXRISK_ENGINE_READ_TIMEOUT_S` 54,000 · `HWAXRISK_ENGINE_BUSY_WAIT_S` 30 · `HWAXRISK_ENGINE_BUSY_MAX_WAIT_S` 3,600)를 그대로 쓴다. 서버는 자리가 없으면 대개 **스트림을 연 채** 줄을 세우고(`status{step:'queued'}`), 대기 줄이 가득 찼을 때만 429 를 준다. 그래서 429 는 드물다.

#### 3.6.2 클라이언트

```python
# runner.py — 프로토콜과 예외의 정본(engine_client 가 runner 를 import 하는 지금 방향을 지킨다)
class ReviewEngine(Protocol):
    def limits(self, *, owner_sub: str | None = None) -> Mapping[str, Any]: ...
    def pack(self, agent_key: str, *, owner_sub: str | None = None) -> Mapping[str, Any]: ...
    def plan(self, cards: Sequence[Mapping], units: Sequence[Mapping], *, owner_sub: str | None = None) -> Mapping[str, Any]: ...
    def run(self, request: Mapping[str, Any], *, owner_sub: str | None = None,
            on_progress: Callable[[Mapping[str, Any]], None] | None = None,
            should_stop: Callable[[], str | None] | None = None) -> Mapping[str, Any]: ...

class EngineRejected(EngineError):
    """card_review 가 거절했다(스트림 전의 422 · 스트림 안의 error 프레임). infra 가 차감 여부를, retryable 이 다시 낼지를 정한다."""
    def __init__(self, code: str, message: str, *, infra: bool, retryable: bool,
                 knob: str | None = None, detail: Mapping | None = None): ...

# engine_client.py
REVIEW_BASE = "/agent/card-review"

class PortalReviewEngine(PortalPanelEngine):
    """앱 → 포털 /agent/card-review/{limits|pack|plan|run}. 대화를 만들지 않는다."""

def collect_review_stream(frames: Iterable[tuple[str, dict]]) -> dict:
    """status → 진행, result → 본문, error → EngineRejected, done → 끝. 반환 = result 프레임의 dict 그대로."""
```

`PortalPanelEngine` 에서 물려받아 쓰는 것은 `_credential`(여유 인자를 받게 넓힌다) · `_client` · `health` · `parse_sse` · `_StreamWatch` · `_watched` 다. `_watched` 는 벽시계 초과의 코드와 손잡이 이름을 인자로 받게 한다(`wall_code='call_timeout'`, `wall_knob='HWAXRISK_REVIEW_CALL_TIMEOUT_S'`). 지금은 문구에 `HWAXRISK_PANEL_TIMEOUT_S` 가 박혀 있다(engine_client.py:146).

응답을 예외로 옮기는 표다. 네 메서드가 같이 쓴다.

| 응답 | 올리는 것 |
|---|---|
| 401 | `PatUnavailable` |
| 403(`denied`) | `EngineRejected('forbidden', infra=False, retryable=False)` — 잡 단위로 멈춘다 |
| 404(`agent_not_found`, 팩) | `EngineRejected('agent_not_found', infra=False, retryable=False)` |
| 422 `bad_request` | `EngineRejected('invalid_request', infra=False, retryable=False)` — 요청 계약이 어긋났다 |
| 422 `over_budget` | `EngineRejected('over_budget', infra=False, retryable=False, detail={need, have, part})` |
| 429 | `EngineBusy`(대화가 없으므로 `conversation=None`). `Retry-After` 가 있으면 그 값과 간격 손잡이 중 큰 쪽을 쉰다 |
| 502(`card_fetch_failed`, 팩) · 그 밖의 5xx · 연결 실패 | `EngineError` |
| `error` 프레임 | `EngineRejected(code, infra=<프레임의 infra>, retryable=<프레임의 retryable>, knob=…)` |
| 읽기 타임아웃 · 흐르던 중 끊김 · 벽시계 · 사람의 정지 | `EngineStreamLost` — 코드는 차례로 `engine_silent` · `engine_stream_cut` · `call_timeout` · `cancelled` |

`run()` 은 `create_conversation` 을 부르지 않고 본문에 `conversation_id` 도 싣지 않는다. 단발 셋(`limits` · `pack` · `plan`)은 스트림이 아니므로 읽기 한도를 포털의 단발 한도보다 조금 크게(660초) 둔다.

`health()` 는 지금 돌려주는 키에 `card_review_active` · `card_review_waiting` · `card_review`(`limit` · `prompt_rev` 등)를 더 옮긴다. 진행판이 '서버가 지금 몇 건을 돌리고 몇 건이 줄 섰나' 를 보여 주는 데 쓴다.

#### 3.6.3 요청 조립(`build_request`)

요청의 모양은 WP3a 가 정했다(그 문서 3.5.0). 앱은 **조각을 모아 끼울 뿐**이고 글을 새로 쓰는 칸은 `unit.notes` · `unit.missing[].note` · `extra.search.queries` 셋뿐이다.

```python
# review_runner.py
def build_request(kind: str, variant: str | None, *, target: Mapping, pack: Mapping, deck_aliases: Sequence[str],
                  unit: Mapping | None, manifest: Sequence[Mapping] = (), extra: Mapping | None = None) -> dict: ...
```

| 요청 칸 | 어디서 오나 |
|---|---|
| `kind` · `variant` | `sweep` · `verdict`(`fwd` · `rev` · `solo`) · `offcard` · `noinput` |
| `target_key` | 타깃 |
| `expert{key, name, domain, role}` | 얼린 팩의 머리 그대로 |
| `cards[]` | `cardpack.cards_for(pack, 별칭들)` — 팩의 항목 그대로. `rev` 는 **순서만** 뒤집는다(별칭은 그대로다) |
| `digest[]` | 그 호출에 전문으로 싣지 않는 카드의 `{alias, type, title}` |
| `unit{unit_id, kind, title, summary, lines[{ref, text}], evidence[{ref, text}], notes, missing[]}` | WP2 의 단위(§7.1). `lines` 는 전량이다 — 앱이 줄이지 않는다 |
| `manifest[{unit_id, kind, title, text}]` | 훑기에서만. WP2 `units.packets` 의 쪽, 서버 계획의 `manifest_pages` 순서 |
| `extra.mechanisms[{code, label}]` · `extra.domains[{key, label}]` | 앱 택소노미 38종(`assets/taxonomy.v1.json`) · 로스터 영역 15개 |
| `extra.known[{alias, judgement, why}]` | 카드 밖 호출에서만. 이 전문가가 이 단위에 낸 실효 판정(1,200자 안 — FAIL · WARNING 먼저, 넘치면 OK · na 를 뺀다) |
| `extra.search{queries, exclude_record_ids}` | 카드 밖 호출에서, 손잡이 `HWAXRISK_REVIEW_SEARCH`(`cardless` 기본 · `all` · `off`)가 허락할 때만(§3.5.5) |

앱이 쓰는 글 셋의 초안이다.

```
unit.notes(읽는 법 — 좌석 계약 seat-contract.v1.json 의 _common 에서 데이터 의미 문장만 옮긴다. 정본이 앱 자산이다)
  interference 의 auto 는 미확정 초안이다. penetration_depth 는 하한 추정치다. contact_area_est 는 공차 밴드 면적이다.
  null · 미측정은 0 이 아니다. {부분 캡처면: 이 스냅샷은 부분 캡처다(capture_partial).}
  {소스 앱 판이 다르면: 기준과 대상의 소스 앱 판이 다르다(<base 판> · <target 판>).}

unit.missing[].note(입력 결손 — rr_roster.input_gaps_json 에서)
  ecad_absent → kind "ecad", note "이 과제에는 회로(ECAD — 배치 · 넷 · 스택업) 변경 정보가 없다"
  mcad_absent → kind "mcad", note "이 과제에는 기구(MCAD) 형상 정보가 없다"

extra.search.queries(긴 문서 검색어 — 각 300자 안, 3개까지)
  "<부품 역할> <재질> <변경 낱말>" 을 WP2 units.roster_query 의 구절에서 그 단위 것만 골라 그대로 쓴다.
```

`unit.notes` 의 문장은 코드가 쓰는 글이라 판단어 린터(`render.lint_text`)를 지나게 한다.

#### 3.6.4 응답

`result` 프레임이 호출 1건의 전부다. 앱은 이것을 `rr_review_calls.result_gz` 에 통째로 얼리고, 행은 §3.8 의 재대조를 거쳐 원장에 옮긴다.

```json
{"kind": "verdict", "variant": "fwd",
 "rows": [{"t": "v", "k": "K03", "record_id": "DOC-CCT-MECH-2026-0000000144", "applies": "yes", "judgement": "FAIL",
           "cq": "0.8 mm 하한을 못 지키는 구간이 있는지 확인한다", "l": ["L01"], "refs": ["c:ab12cd34ef56"],
           "why": "PSA 유효 접착폭이 0.9 mm 로 줄어 최악 공차에서 하한 0.8 mm 를 밑돌 수 있다", "need": "",
           "checks": {"quote": "ok", "refs": "ok", "nums_missing": [], "need": "ok", "coerced": []}}],
 "missing": ["K07"],
 "extras": {"inj": []},
 "quality": {"expected": 8, "ok": 6, "flagged": 1, "missing": 1, "bad_lines": 0, "truncated": false,
             "attempts": 2, "stamp": false, "dropped_over_cap": 0},
 "meta": {"model": "…", "ctx_tokens": 128000, "prompt_rev": "cr-p1:3f9a12c4", "norm_rev": "cr-n1", "limits_rev": "a1b2c3d4",
          "input_sha": "…", "prompt_chars": 31250, "est_tokens": 29762,
          "usage": {"prompt_tokens": 14120, "completion_tokens": 1830}, "finish_reason": "stop",
          "queued_ms": 420, "llm_ms": [93100, 41200], "soft_over": false, "basis": "cards",
          "aliases": {"cards": {"K03": "DOC-…144"}, "lines": {"L01": "c:ab12cd34ef56"}}}}
```

종류별 행과 앱이 그것으로 하는 일이다.

| 종류 | 행(`t`) | 앱이 하는 일 |
|---|---|---|
| `sweep` | `u{u, unit_id, rel, k[], why}` · `k0{k[]}` · `h{u, to, why}` | 셀 분류(§3.7.4). `quality.stamp` 면 그 쪽의 `no` 를 믿지 않는다 |
| `verdict` | `v{k, record_id, applies, judgement, cq, l[], refs[], why, need, checks}` (`solo` 는 `c{cond, l[], met, note}` 줄과 `v` 에 `sev` · `path` · `check_kind` · `check`) | `rr_card_verdicts` 한 행씩 |
| `offcard` | `f{dir, title, mech, mech_free, path, l[], refs[], src, q, sev, conf, check_kind, check}` · `m{seen[]}` · `h` · `need` · `none` | 셀 `extras_json`. `f` 는 finding 후보, `m.seen` 은 WP4 의 메커니즘 셀 재료 |
| `noinput` | `q1{impact, title, path, l[], k, cq, sev, why}` · `q2{item, needs, k, l[], why}` | 셀 `input_gap_json` 과 `extras_json`. `q1` 의 `yes` 는 finding 후보, `q2` 는 '입력이 오면 확인할 것' |

`meta.usage` 는 LLM 서버가 준 실제 토큰 수다. 호출 원장에 그대로 적어 두면 이 박스의 자/토큰 비를 실주행에서 잴 수 있다.

#### 3.6.5 프롬프트

프롬프트의 정본(시스템 글 · 종류별 지시 · 출력 형식)은 WP3a 문서 3.5 절에 있고 이 꾸러미는 그것을 싣지 않는다 — 두 곳에 두면 갈린다. 앱이 프롬프트에 영향을 주는 길은 §3.6.3 의 표가 전부다. 그 가운데 판정의 질을 좌우하는 것이 셋이라 규칙으로 못 박는다.

1. **카드는 얼린 그대로, 묶음은 계획 그대로.** 앱이 카드를 골라 빼거나 순서를 바꾸지 않는다(`rev` 의 뒤집기만 예외다). 그래야 '실은 카드 집합' 이 계획과 같고 빠진 판정을 셀 수 있다.
2. **단독 재질의에 앞 판정을 싣지 않는다.** 실으면 그 답을 따라간다. `extra.known` 은 카드 밖 호출에만 쓴다(되풀이를 막는 용도다).
3. **훑기에는 전 단위를, 카드 대조에는 단위 하나를.** 한 호출에 단위 둘을 넣지 않는다. 끊겼을 때 잃는 것이 호출 하나여야 한다.

### 3.7 러너 — `review_loop`

#### 3.7.1 잡 모델

`rr_jobs` 를 그대로 쓰고 **종류 열 `mode`** 로 가른다(값 `reviews`. WP4 · WP5a 가 같은 열을 쓴다). 표를 따로 두지 않는 이유는 정지 · 재개 · 취소 · 이양 가드 · 폐기 취소가 전부 `rr_jobs` 를 보기 때문이다(routes.py:889, 1022, 2148~2156). 대신 '최근 잡 하나' 를 읽는 자리마다 종류를 걸러야 한다. 빠뜨리면 조용히 틀린다.

| 자리 | 고칠 것 |
|---|---|
| runner.py:718~728 `claim_next_job` 의 두 조회 | 패널 잡만(`COALESCE(mode,'panels') = 'panels'`, WP4 가 붙으면 `IN ('panels','issues')`). 안 거르면 패널 루프가 검토 잡을 집어 `plan_next_panel(tier=None)` 이 `AppError` 를 내고, 잡은 `running` 으로 남아 5초마다 다시 집힌다 |
| runner.py:785 `recover_running_panels` | 패널 잡만 |
| routes.py:2215~2217 `coverage_payload` 의 최근 잡 | 패널 잡만. 검토 잡은 `review.job` 칸으로 따로 준다(§3.12) |
| routes.py:553~558 과제 화면의 잡 목록 | 거르지 않고 `mode` 열을 같이 준다 |
| brief.py:1226~1229 최근 잡 메모 | 패널 잡만. 검토 잡의 메모가 패널 브리프에 실리지 않게 한다 |

```python
# review_runner.py
def create_review_job(store, target_key: str, *, owner_sub: str, requester_sub: str | None = None,
                      scope: Mapping[str, Any] | None = None, user_memo: str | None = None,
                      consent: bool = False, settings=None) -> dict:
    """검토 잡 1건. 네트워크를 부르지 않는다(격자는 여기서, 카드 묶음은 루프가).

    scope = {'tier': 'A'|'B'|'C'|None, 'domains': [...], 'agents': [...], 'units': [...]} — 범위 밖 셀은 pending 으로 남는다.
    거절 — 단위가 없으면 409 units_absent, 살아 있는 검토 잡이 있으면 409 review_job_exists,
           살아 있는 Tier 패널 잡이 있으면 409 panel_job_running, consent 없으면 422, 자격이 없으면 422 pat_unavailable.
    반환 {job_id, cells_planned, experts, units, calls_estimate{low, high}, credential, credential_email, credential_note?}
    """
```

`params_json` 에 `{scope, user_memo, requester, consent, knobs{dual_rate, recheck_rate, sweep, sweep_miss_max, search, finding_policy, sample_salt}}` 를 넣는다. 손잡이를 잡에 **복사해 두므로** 도는 중에 설정이 바뀌어도 그 잡의 표본과 배치는 바뀌지 않는다(결정론의 전제다).

#### 3.7.2 격자(`plan_cells`)

```python
# review_cells.py
def plan_cells(store, target_key: str, *, settings=None) -> dict:
    """로스터 × 검토 대상 단위의 셀과 전문가 머리를 INSERT OR IGNORE 로 만든다(멱등).
    반환 {experts, units, cells_new, cells_total, cells_dropped}."""
def reset_review(store, target_key: str, *, by: str, reason: str) -> dict:
    """그 타깃의 셀 · 판정 · 호출 · 보고서 머리, 그리고 claim_uid 가 '<review_id>#' 로 시작하는 finding 과 panel_id = review_id 인 의견을 한 트랜잭션에서 지운다(사람의 명시 조작)."""
```

- 대상 전문가는 `planner.review_order(store, target_key)`(WP2)가 주는 전원이다. 원장 상태로 거르지 않는다 — 회로 영역을 `deferred` 로 만들지 않는 것이 WP2 의 결정이고(`flow='units'`), 격자는 그 명단을 그대로 따른다. `order` · `tier` · `input_gaps` 를 머리 행에 사본으로 적는다.
- 단위는 활성 빌드의 `rr_units` 가운데 `reviewable = 1` 인 것이다. 제외 단위는 격자에 넣지 않는다.
- `unit_hash` 는 `rr_units.content_hash` 와 그 단위 근거 꾸러미의 `pack_hash` 를 이은 것의 해시다. 꾸러미가 아직 `pending` 이면 격자는 만들되 그 단위의 셀은 집지 않는다(WP2 의 `unit_pack.ensure` 가 채울 때까지).
- **단위가 다시 만들어졌을 때.** WP2 는 재빌드로 단위가 사라지거나 생길 수 있다. `plan_cells` 를 다시 부르면 ① 새 단위의 셀을 더하고 ② 활성 빌드에 없는 단위의 **열린 셀은 지우고**(`cells_dropped`) ③ 그 단위의 종결 셀은 남기되 집계 · 보고서 · finding 에서 뺀다(활성 단위와 조인한다). 내용이 같은 단위는 `unit_id` 가 같으므로 건드리지 않는다. 다음 마감에서 그 전문가의 보고서와 finding 이 활성 단위만으로 다시 조립된다.

#### 3.7.3 루프와 선점

```python
# runner.py
_LOOPS = (("panel_loop", 5.0), ("review_loop", 2.0), ("sync_loop", 60.0), ("nightly_loop", 60.0))

class RiskRunner:
    def __init__(..., review_engine: ReviewEngine | None = None):
        self._review_sem = threading.Semaphore(max(1, settings.risk_review_concurrency))   # 기본 4
        self._review_workers: list[threading.Thread] = []

    def _review_tick(self) -> None:
        """① 자동 재개(차단기 백오프가 지난 잡) ② 잡마다 준비(격자 · 한도 · 카드 묶음 · 계획, 틱당 8명) ③ 빈 자리만큼 전문가를 집어 워커를 띄운다."""
```

한 틱이 하는 일이다.

1. `state='paused' AND mode='reviews' AND hold_code IN ('breaker','pack_unavailable')` 이고 `hold_until ≤ now` 인 잡을 `queued` 로 돌린다.
2. `queued | running | cancelling` 검토 잡을 `created_at` 순으로 본다. `cancelling` 이면 `cancelled` 로 닫는다. 자격을 `resolve_credential_with_note`(검토 여유로)로 다시 고르고 없으면 `error='pat_unavailable…'` 만 적고 넘어간다(패널과 같다).
3. `phase='pack'` 이면 `/limits` 를 한 번 읽고(`ctx_assumed` 면 이 틱은 여기서 끝), `pack_status='todo'`(그리고 백오프가 지난 `error`) 전문가를 `review_order` 순으로 틱당 8명까지 받아 얼리고 계획을 받는다. 범위 안 전문가가 전부 `ok | empty` 가 되거나 남은 것이 백오프 중인 `error` 뿐이면 `phase='review'` 로 간다. 근거 꾸러미가 덜 된 단위가 있으면 `unit_pack.ensure`(WP2)를 이 단계에서 부른다.
4. `self._review_sem.acquire(blocking=False)` 가 되는 동안 `claim_next_expert` 로 전문가를 집어 워커를 띄운다. 패널 틱은 한 번에 하나만 띄우지만 여기서는 빈 자리를 다 채운다.

```python
# review_cells.py
def claim_next_expert(store, job: Mapping[str, Any], *, now: int) -> dict | None:
    """state='planned' 이고 pack_status ∈ ('ok','empty') 이고 retry_at 이 지났고 범위 안 열린 셀이 있는 전문가 1명.
    순서 — review_order ASC(WP2: Tier A → B → C, 그 안에서 영역 내 순위 · 영역 · 키).
    UPDATE … SET state='running', claim_id=?, claimed_at=?, job_id=? WHERE … AND state='planned' 의 rowcount 가 1 일 때만 돌려준다."""
```

- Tier A(영역 1순위 15명)가 가장 먼저 돈다. 그들이 **훑기 놓침률을 재는 표본**이 되고(§3.9.4), 중간에 멈춰도 어디까지 봤는지가 tier 로 나온다.
- 세마포어는 **타깃을 가로질러 하나**다. 타깃당 직렬도 일일 상한도 없다. 서버 쪽 관문이 따로 있다(기본 4, 심의가 도는 동안 2 — WP3a). 앱의 동시 수를 그보다 올려도 넘치는 호출은 서버의 줄에서 기다릴 뿐이다.
- 집을 전문가가 없고 그 잡을 쥔 워커도 없으면 단계가 `done` 으로 넘어간다. 거기서 등록부를 한 번 병합하고(§3.10.4) 잡을 `completed` 로 닫는다. 그 뒤의 후속 잡(교차 · 사냥 · 표본 재검토 → 쟁점 → 종합)을 잇는 것은 WP4 다. 열린 실패 셀이 남아도 `completed` 다. 그 수는 `progress_json.cells.failed` 와 `error`('실패 셀 N — 사람의 처분이 필요하다')에 남는다.

#### 3.7.4 전문가 세션(`run_expert`)

```python
# review_runner.py
def run_expert(store, settings, engine: ReviewEngine, job: Mapping[str, Any], expert: Mapping[str, Any], *,
               stop: threading.Event, progress: "JobProgress", breaker: "Breaker") -> dict:
    """전문가 1명의 열린 셀을 끝까지 돈다. 반환 {agent_key, outcome: 'finalized'|'released'|'blocked', reason?}"""

def finalize_expert(store, settings, target_key: str, agent_key: str, *, claim_id: str) -> dict:
    """열린 셀이 0 이면 finding · 의견 · 보고서 · 원장을 한 트랜잭션으로 쓴다(§3.10 · §3.11 · §3.4)."""
```

세션의 순서다. 호출과 호출 사이마다 `should_stop()` 을 묻고, 각 호출의 결과는 **끝나는 즉시** 트랜잭션 하나로 적는다.

| 순서 | 무엇 | 호출 | 몇 번 |
|---|---|---|---|
| 1 | (가) 훑기 | `sweep` | 훑기 묶음 수 × 단위 목록 쪽 수(대개 1~2) |
| 2 | 분류 | 없음 | — |
| 3a | (나) 카드 대조 | `verdict` · `fwd` | 점검 묶음마다 × 대조할 단위마다. **묶음 먼저, 단위 나중**의 순서로 돈다(같은 묶음을 연달아 보내 프롬프트 앞부분이 겹친다) |
| 3b | 빠진 카드 재질의 | `verdict` · `fwd` | 빠진 카드만 모은 묶음으로(셀마다 최대 2번) |
| 3c | 이중 판정 | `verdict` · `rev` | 표본 셀의 묶음마다(§3.9.1). 음성 표본 카드는 4장씩 따로 묶어 `rev` 로(§3.9.2) |
| 3d | 단독 재질의 | `verdict` · `solo` | `fwd` ≠ `rev` 인 카드, 실효 판정이 FAIL · WARNING 인 카드마다 1장씩 |
| 3e | (다) 카드 밖 | `offcard` | 대조한 단위마다 1번(앞 판정을 `extra.known` 으로) |
| 3′ | 입력 결손 두 질문 | `noinput` | 입력 결손 전문가는 3a~3e **대신** 단위마다 1번 |
| 4 | 셀 정산 | 없음 | 3e(또는 3′)가 끝난 셀부터 |
| 5 | 마감 | 없음 | 열린 셀이 0 일 때 |

이미 결과가 있는 호출은 다시 부르지 않는다 — 판정 행이 있는 (카드, 변형), `offcard_state` 가 끝난 셀, `sweep_state='done'` 인 전문가. 그래서 중간에 끊긴 세션을 다시 집으면 **남은 호출만** 돈다.

**훑기를 건너뛰는 경우**와 그때의 `route_forced` 다. 건너뛰면 전 단위가 대조로 간다.

| 조건 | `route_forced` |
|---|---|
| 카드 0장 | `no_cards` |
| snap 타깃(현황 감사는 전 전문가 대상이다) | `snap` |
| 검토 대상 단위가 5개 이하(거르는 이득보다 호출이 싸다) | `few_units` |
| 잡 손잡이 `sweep='off'`, 또는 놓침률이 임계를 넘겨 그 잡의 필터가 꺼졌다 | `filter_off` |
| Tier A(영역 1순위) | `tier_a` — 훑기는 **하되** 결과와 무관하게 전 단위를 대조한다(놓침률 측정) |
| WP2 의 `for_cell.forced` 가 값이 있다 | 그 값 그대로 |

**훑기 답을 셀로 옮기는 법.** 훑기 묶음이 여럿이면(카드가 많은 전문가) 한 단위에 `u` 줄이 묶음 수만큼 온다. 가장 센 것을 쓴다(yes > maybe > no). 한 쪽의 답에 `quality.stamp` 가 서 있으면(전 단위가 no 이고 사유가 두 가지 이하) 그 쪽의 no 는 `route_llm='stamp'` 로 적고 **no 로 치지 않는다**. 답에 없는 단위는 `error` 다.

**분류표.** '해당 없음' 으로 가는 문은 한 줄뿐이다.

| `route_det`(WP2) | `route_llm`(훑기) | `route_forced` | 결과 |
|---|---|---|---|
| `hit` · `blind` | 무엇이든 | 무엇이든 | `review` |
| `miss` | `yes` · `maybe` · `stamp` · `error` · `skipped` | 무엇이든 | `review` |
| `miss` | `no` | 값이 있다 | `review` |
| `miss` | `no` | 없다 | **`na`** → 셀 `na_irrelevant` |

- `route_det` 은 `unit_signals.for_cell(store, target_key, unit_id, agent_key, card_vocab=…, last_check=…)` 의 `det` 다. 훑기가 `no` 라고 한 셀에만 `last_check=True` 로 한 번 더 부른다 — WP2 는 '해당 없음 직전에만' 도는 마지막 신호(키워드 검색)를 그 인자로 켠다. 반환을 `route_json.det` 에 **그대로** 얼린다. 그것이 '해당 없음' 의 신호값이다.
- 그 함수가 아직 없거나 예외를 내면 전부 `blind` 로 본다 — **아무도 '해당 없음' 이 되지 않고 전수 대조가 된다**(안전한 쪽이 기본이다).
- `card_vocab` 에는 훑기가 그 단위에 걸었던 카드(`k`)의 제목 · 태그 낱말을 준다.

**카드 대조 길의 정산(`settle_cell`).** 아래가 전부 참이면 `reviewed` 다.

1. 계획의 점검 카드(창 초과 카드 제외) 전부에 실효 판정 행이 있다(`cards_judged == cards_expected`).
2. 정산에 쓴 호출 가운데 절단이 남은 것이 없다.
3. 뽑힌 표본(이중 판정 · 음성 재질의 · 단독)이 다 돌았다.
4. 카드 밖 호출이 끝났다(`offcard_state ∈ done · none`).

하나라도 거짓인데 더 부를 호출이 없으면 내용 탓 실패다(§3.7.5).

**입력 결손 길.** 머리 행의 `input_gaps_json` 이 비어 있지 않은 전문가(WP2 가 로스터 동결 때 얼린다 — ECAD 의존 영역이고 `ecad_absent` 인 경우 등)는 `review` 로 분류된 셀마다 `noinput` 호출 한 번으로 닫는다. `cards` 에는 훑기가 그 단위에 건 카드를 전문으로, `digest` 에 나머지 제목을 싣는다.

| 질문 1(`q1` 줄들) | 질문 2(`q2` 줄들) | 셀 |
|---|---|---|
| `impact='yes'` 가 하나라도 있다 | 무엇이든 | `reviewed`(`basis='noinput'`). `yes` 줄은 finding 후보, `q2` 는 '입력이 오면 확인할 것' |
| `yes` 는 없고 `unknown` 이 있다 | 무엇이든 | `no_input` |
| 전부 `no` | 요청(`item` 이 빈 문자열이 아닌 줄)이 1건 이상 | `no_input` |
| 전부 `no` | 요청 0건(까닭만 있다) | `reviewed`(`basis='noinput'`) — 영향도 없고 입력이 와도 볼 것이 없다는 답이다 |

마지막 줄은 WP2 의 표(그쪽은 `q1.status` 가 `answered | no_input` 둘이다)와 WP3a 의 행(`impact` 가 셋이다)을 맞춘 것이다. 두 문서의 낱말이 달라 §7.3 에 적는다.

#### 3.7.5 실패의 구분

호출 하나의 결말을 셋으로 가른다. **가르는 것은 서버가 실어 준 `infra` 다.** 앱은 코드 이름을 따로 외우지 않는다(코드가 늘어도 표가 깨지지 않는다).

| 결말 | 무엇 | 셀에 하는 일 |
|---|---|---|
| **인프라 탓** | `error{infra: true}`(`busy` · `llm_timeout` · `llm_unreachable` · `llm_error` …) · `EngineBusy` 예산 소진 · 연결 실패 · 5xx(`EngineError`) · `engine_stream_cut` · `engine_silent` · 첫 번째 `call_timeout` · 호출 결과를 DB 에 못 적었다 | `running → pending`. `attempts` 그대로, `infra_retries + 1`, `retry_at = now + 백오프`(30 · 60 · 120 · 300 · 600 · 900초). `infra_retries` 가 6 을 넘기면 `failed('infra_exhausted')` |
| **내용 탓** | `error{infra: false}`(`context_overflow` · `truncated_empty` · `no_rows`) · 422 `over_budget` · 같은 호출의 두 번째 `call_timeout` · 앱이 찾은 `cards_unjudged`(재질의 2번 뒤에도 빠진 카드) · `unit_oversize` | 먼저 **줄여서 한 번 더**(아래). 그래도 안 되면 `attempts + 1`. 한도(2) 미만이면 `pending`, 닿으면 `failed(<code>)` |
| **잡 단위** | `PatUnavailable`(401) · `forbidden`(403) · `invalid_request`(422 `bad_request` — 요청 계약이 어긋났다) | 셀은 차감 없이 `pending`. 잡을 멈춘다 — 자격은 `failed('pat_unavailable')`(패널과 같다), 권한 · 계약은 `paused` + 보류 코드 `contract` |

'줄여서 한 번 더' 는 묶음이 원인일 때만 쓴다.

- `context_overflow` · `over_budget` — 먼저 `/limits` 를 다시 읽는다. `limits_rev` 가 달라졌으면 그 전문가의 계획을 다시 받고 처음부터 돈다(차감 없음 — 박스의 창이 바뀐 것이지 내용 탓이 아니다). 같으면 그 묶음을 반으로 나눠 다시 부른다(차감 없음, 1장이 될 때까지).
- `truncated_empty` — 묶음을 반으로 나눠 다시 부른다. 1장에서도 나면 내용 탓 실패다(문구에 서버가 준 손잡이 이름 `DELIB_MAX_TOKENS` 를 붙인다).
- 결과가 왔는데 `quality.truncated` 이고 `missing` 이 있으면 실패가 아니다. 온 행은 적고 빠진 카드만 재질의한다.

사람이 멈춘 것 · 취소 · 앱 종료(`cancelled`)는 실패가 아니다. `pending` 으로 돌리고 아무것도 세지 않는다.

#### 3.7.6 차단기 — 실패율이 치솟으면 셀을 태우지 않고 잡을 멈춘다

```python
class Breaker:
    """잡 하나의 최근 호출 결말을 본다. 창은 프로세스 메모리에 두고, 걸린 결과는 잡 행의 hold_* 열과 progress_json.breaker 에 적는다."""
    WINDOW = 20; MIN_SAMPLES = 10; INFRA_RATE = 0.5; INFRA_STREAK = 5; CONTENT_RATE = 0.5
    BACKOFF_S = (60, 120, 240, 480, 900, 1800); GIVE_UP_TRIPS = 8
    def record(self, outcome: str, code: str = "") -> str | None:    # 반환 None | 'infra' | 'content'
```

- 최근 20회 중(10회 이상 쌓였을 때) 인프라 실패가 절반 이상이거나 **연속 5회**면 잡을 `paused` + `hold_code='breaker'` 로 멈추고 `hold_until` 에 다시 볼 시각을, `hold_n` 에 몇 번째인지를 적는다. `error` 에 "최근 20회 중 12회 인프라 실패(engine_stream_cut 9 · llm_timeout 3) — 240초 뒤 다시 시도한다(3번째)" 처럼 적는다. 돌던 워커들은 다음 호출 경계에서 선점을 놓는다.
- 백오프가 지나면 틱이 잡을 `queued` 로 돌린다. **반쯤 연 상태**로 시작한다 — 호출 하나가 성공할 때까지는 워커를 하나만 띄운다. 성공하면 정상으로, 또 실패하면 다음 백오프로 간다.
- 성공 없이 8번 연달아 걸리면(약 2시간) `hold_until` 을 비우고(자동 재개 없음) 사람의 재개를 기다린다.
- 내용 탓 실패가 최근 20회의 절반 이상이면 보류 코드 `content_fail_rate` 로 멈추고 **자동 재개하지 않는다**. 프롬프트 · 모델 · 파서 가운데 하나가 틀어진 것이라 다시 돌려도 셀의 시도 수만 태운다.
- 재기동하면 차단기 기억은 잡 행의 `hold_code` · `hold_n` · `hold_until` 에서 되살린다.

패널의 '연속 3패널 오류 → 잡 failed'(`ENGINE_FAIL_STREAK`) · 수확 체감 정지 · 일일 상한은 `rr_panels` 만 세므로 셀과 무관하다. 차단기는 그 자리를 셀에 맞는 규칙으로 메운 것이다.

#### 3.7.7 멱등과 선점 id

- **결과 자리가 정해져 있다.** 셀은 PK, 판정은 `(셀, record_id, variant)`, 호출은 `call_id`(논리 키 + 시도 순번의 해시), finding 은 `claim_uid`(§3.10.2), 의견은 `opinion_id`, 보고서는 `(target_key, agent_key)` 다. 같은 셀을 두 번 돌리면 같은 자리에 같은 것이 놓인다.
- **쓰기는 선점 id 를 대조한다.** `write_call_result` · `settle_cell` · `finalize_expert` 는 `… WHERE claim_id = ?` 가 붙은 UPDATE 의 rowcount 를 먼저 보고, 0 이면 아무것도 쓰지 않고 버린다. 재기동 복구가 선점을 지운 뒤에 옛 워커가 늦게 끝나도 결과를 덮지 못한다.
- **입력이 바뀌면 처음부터.** 셀을 집을 때 `input_hash` 를 다시 셈해 저장값과 다르면(단위 내용이나 근거 꾸러미가 바뀌었거나 카드 묶음이 갈렸거나 `prompt_rev` · `limits_rev` 가 올랐다) 그 셀의 판정 행을 지우고 처음부터 돈다(`reopened_n + 1`).
- 엔진 호출은 `tx()` 밖이다. 트랜잭션은 호출 앞(선점)과 뒤(결과)에만 짧게 연다.

#### 3.7.8 재기동 복구

```python
# review_cells.py
def recover_running(store) -> dict:
    """UPDATE rr_review_cells   SET state='pending', claim_id=NULL WHERE state='running';
       UPDATE rr_expert_reports SET state='planned', claim_id=NULL WHERE state='running';
       UPDATE rr_review_calls   SET state='aborted', error_code='restart' WHERE state='running';
       running 검토 잡은 'queued' 로(멈추지 않는다). 반환 {cells, experts, calls, jobs}"""
```

`RiskRunner.start()` 가 `recover_running_panels` 옆에서 부른다. 패널과 다른 점이 둘이다.

- **차감이 없고 `retry_at` 도 걸지 않는다.** 등록된 제공자(§3.7.11)의 `recover` 도 여기서 부른다. 재기동은 누구 탓도 아니다. 이미 적힌 판정 행은 그대로 남아 남은 호출만 다시 돈다. 잃는 것은 돌던 호출 W 건뿐이다.
- **잡을 멈추지 않는다.** 패널은 엔진이 분리 태스크로 계속 돌기 때문에 곧바로 다시 편성하면 같은 심의가 겹친다(runner.py:767~770). 검토 호출은 분리 태스크가 아니어서(WP3a 에 요구한다 — §7.1) 구독이 끊기면 에이전트 서버도 그 호출을 접는다. 겹칠 것이 없으니 사람을 기다릴 이유가 없다.

#### 3.7.9 취소 · 일시정지

잡 행이 정본이다(패널과 같다 — `cancel_job` · `pause_job` 은 행만 고친다). 워커의 `should_stop` 은 `runner._stop_reader` 를 그대로 쓰되 앱 종료 이벤트와 차단기를 같이 본다.

- 호출이 도는 중이면 `_watched` 가 프레임마다(ping 덕에 15초 안) 물어 스트림을 닫는다. 닫힌 호출은 `aborted`, 셀은 `pending`(차감 없음), 전문가는 `planned` 다.
- 429 를 기다리는 중이면 대기 루프가 간격마다 묻는다(`stop.wait(min(간격, 남은 예산))`).
- 호출과 호출 사이면 다음 호출을 시작하지 않는다.
- 재개하면 같은 잡이 이어 돈다. 이미 닫힌 셀과 이미 적힌 판정은 건드리지 않는다.

#### 3.7.10 진행 신호

검토 잡의 `progress_json` 은 아래 모양이고, `JobProgress`(잡마다 하나, 스레드 안전)가 60초 간격으로 적는다. 단계 전환 · 차단기 변화 · 워커의 시작과 끝은 간격을 건너뛰고 바로 적는다. 셀 수는 적을 때 `GROUP BY state` 로 센다.

```json
{
  "mode": "reviews", "phase": "review", "updated_at": 1760000000,
  "packs":   {"total": 359, "ok": 354, "empty": 3, "error": 2},
  "experts": {"total": 359, "planned": 268, "running": 4, "ready": 82, "partial": 3, "blocked": 2},
  "cells":   {"total": 2872, "pending": 1900, "running": 4, "reviewed": 610, "na_irrelevant": 320, "no_input": 12, "failed": 26},
  "calls":   {"ok": 1520, "infra_fail": 14, "content_fail": 9, "aborted": 3, "last_ok_at": 1759999950, "avg_ok_s": 281},
  "workers": [{"agent_key": "mech-ip-sealing", "unit_id": "u:5d0c1e9a77b2", "call_kind": "verdict", "variant": "fwd", "deck_id": "v2",
               "started_at": 1759999800, "last_frame_at": 1759999995, "last_event_at": 1759999940, "last_step": "attempt 1"}],
  "breaker": {"state": "closed", "trips": 0, "hold_until": null, "last": null},
  "sweep":   {"filter": "on", "tier_a_checked": 96, "tier_a_missed": 2, "miss_rate": 0.0208, "stamped_pages": 0},
  "server":  {"card_review_active": 3, "card_review_waiting": 1, "limit": 4},
  "eta":     {"calls_left_low": 2100, "calls_left_high": 2900}
}
```

`workers[]` 가 패널 잡의 `signal` 자리다. `last_frame_at` 은 ping 을 포함한 아무 프레임(연결이 살아 있다), `last_event_at` 은 ping 이 아닌 프레임(호출이 나아간다)이다.

#### 3.7.11 다른 꾸러미의 일을 같은 루프로 — 제공자 접점

WP4 의 단독 호출(2차 영향 · 메커니즘 사냥 · 요약)도 같은 LLM 을 쓴다. 풀을 둘 두면 동시 수의 합이 상한을 넘는다. 그래서 검토 루프가 **세마포어 하나**로 그 일도 돌린다. WP4 가 제안한 모양을 그대로 받는다.

```python
# review_runner.py
class WorkProvider(Protocol):
    name: str                                                    # 'cross' | 'mech_hunt' | 'summary' …
    modes: tuple[str, ...]                                       # 이 제공자가 맡는 rr_jobs.mode — 예 ('post',) · ('synth',)
    def claim(self, store, job: Mapping) -> dict | None: ...     # pending → running. rowcount 가 1 일 때만
    def build_request(self, store, item: Mapping) -> dict: ...   # card_review 요청 본문
    def complete(self, store, item: Mapping, result: Mapping) -> dict: ...
    def fail(self, store, item: Mapping, error: str, *, charge: bool) -> None: ...
    def recover(self, store) -> int: ...                         # 기동 때 running → pending(차감 없음)

def register_provider(provider: WorkProvider) -> None: ...
```

- `_review_tick` 은 `mode='reviews'` 잡에는 전문가 세션을, 등록된 제공자의 `modes` 에 드는 잡에는 그 제공자의 `claim` 을 묻는다. 빈 자리를 채우는 순서는 잡의 `created_at` 이다.
- 제공자의 일 하나는 `engine.run(provider.build_request(item))` 한 번이다. 자격 · 429 대기 · 벽시계 · 취소 · 진행 신호 · 호출 원장(`rr_review_calls`) · 실패 구분(§3.7.5 의 `infra` → `charge=False`) · 차단기를 루프가 대신 해 준다. 제공자는 자기 표의 상태만 옮긴다.
- 재기동 복구는 `RiskRunner.start()` 가 등록된 제공자의 `recover` 를 차례로 부른다.
- 제공자가 없으면 이 절은 아무 일도 하지 않는다. 걸음 8 에서 접점과 가짜 제공자 시험만 넣는다.

### 3.8 검증(코드)

대조의 **구현은 WP3a 에 한 벌** 있다 — 서버가 행마다 `checks{quote, refs, nums_missing, need, coerced}` 를 실어 준다. 앱은 그것을 다시 짜지 않는다. 앱이 하는 일은 넷이다.

1. **집합 회계** — 실은 카드 집합과 판정이 온 카드 집합을 호출 · 셀 · 전문가 단위로 맞춘다. 무엇을 실었는지 아는 쪽은 앱이다.
2. **얼린 글로 재대조** — 카드 인용을 앱이 얼린 팩에 한 번 더 대본다. 원장에 올라가는 등급은 이 값으로 정한다.
3. **등급** — 카드 confidence 로 등급을 정한다(서버는 등급을 모른다).
4. **실효 판정** — 변형이 여럿인 카드에서 하나를 고른다.

```python
# review_verify.py
VERIFY_REV = "verify-1"

def accept_rows(result: Mapping[str, Any], *, kind: str, sent_aliases: Sequence[str], pack: Mapping[str, Any],
                unit_refs: frozenset[str]) -> dict:
    """result 프레임 → {rows: [...원장에 적을 행...], missing: [별칭…], dropped: [(사유, 원행)…], extras: {...}}"""
```

#### 3.8.1 판정 행 집합 == 실은 카드 집합

- 서버가 준 `missing` 을 그대로 믿지 않고 앱이 다시 센다. `v` 행의 `k` 를 모아, 별칭이 이 호출에 실은 집합에 없으면 그 행을 버리고(`dropped: alias_outside_call`), 같은 별칭이 두 번이면 첫 행만 쓴다.
- `record_id` 는 행에 실려 오지만 쓰지 않는다. 앱이 **별칭에서 팩으로** 되돌린 `record_id` 를 쓰고, 둘이 다르면 `dropped: record_mismatch` 다.
- `missing = 실은 집합 − 본 집합`. 비어 있지 않으면 **빠진 카드만 모은 묶음**으로 `verdict · fwd`(또는 그 변형)를 다시 부른다(셀마다 최대 2번). 서버가 요청 안에서 이미 보충을 두 번까지 하므로 여기까지 오는 것은 드물다. 그래도 남으면 그 셀은 내용 탓 실패 `cards_unjudged` 다.
- `applies` · `judgement` 가 열거 밖이거나 서로 안 맞는 행(서버가 `coerced` 로 고치지 못한 것)은 없는 것으로 친다(빠진 카드가 된다).
- 서버가 줄 단위(JSON Lines)로 받으므로 깨진 줄은 그 행만 잃는다. 그 행이 여기서 '빠진 카드 1장' 으로 잡힌다. 조용히 '판정 7건' 으로 읽히지 않는다.

정산의 종결 조건은 `cards_judged == cards_expected` 다(§3.7.4). 한 장이라도 판정 행이 없으면 `reviewed` 가 될 수 없다.

훑기에서도 같은 회계를 한다 — `u` 줄의 단위 집합이 그 쪽의 단위 집합과 같아야 하고, `(u 줄들의 k 합집합) ∪ k0` 이 실은 카드 집합과 같아야 한다. 빠진 단위는 `route_llm='error'`(대조로 간다)다. 어느 줄에도 안 나온 카드는 `sweep_json.cards_unseen` 에 남기고 보고서 품질 칸에 센다(훑기에서 그 카드가 읽혔다는 증거가 없다).

#### 3.8.2 카드 인용 — 얼린 글로 재대조

```python
QUOTE_MIN = 15; QUOTE_SUBSTANTIVE_MIN = 10          # 엔진 _quote_validator · WP3a 와 같은 기준

def nq(s: str) -> str:
    """WP3a 의 _nq 와 같은 규칙 — 공백을 하나로, 강조 기호(* · `) 제거, 굽은 따옴표를 곧은 따옴표로. 양쪽에 같은 함수를 건다."""
```

- 소속 — 별칭이 실은 집합에 있어야 한다(§3.8.1). 원장에 적는 참조는 `card:<record_id>` 다.
- 실재 — `nq(cq)` 가 15자 이상이고 실질 문자(한글 · 영숫자)가 10자 이상이며 `nq(cardpack.card_text(그 카드))` 에 들어 있어야 한다. **그 카드**의 글에만 댄다(다른 카드의 문구를 가져다 쓴 인용은 불일치다).
- 결과는 `quote_ok` 에 1 · 0 · NULL(인용 없음)로 적는다.
- 서버의 `checks.quote` 와 앱의 값이 다르면 `check_disagree = 1` 이고 **앱의 값을 쓴다**. 이 표기는 판정의 결함이 아니라 두 리포의 정규화 규칙이 갈렸다는 신호다. 한 건이라도 나오면 진행판 품질 칸에 뜨게 한다.

재대조를 두는 까닭은 셋이다. 원장이 며칠 뒤에도 답해야 하는 물음('이 인용이 그때 실은 글에 있었나')의 근거가 원장 안에 있어야 한다. 등록부로 가는 finding 은 `narrative._normalize_finding` 을 지나는데 그 함수가 인용을 다시 본다(§3.8.6) — 그때 쓸 원문이 얼린 팩이다. 그리고 서버 판(`norm_rev`)이 오른 뒤 옛 결과를 다시 볼 수 있어야 한다. 규칙은 한 줄짜리 함수 하나이고, 두 리포가 같은 픽스처로 시험한다(§5.1).

#### 3.8.3 변경 줄 참조

- 모델은 줄 별칭(`L02`)만 쓰고 서버가 참조(`c:…`)로 되돌려 준다. 앱은 되돌아온 `refs` 가 전부 **그 단위에 실어 보낸 참조**(변경 줄 + 근거 꾸러미 줄)인지 본다. 통과하면 `refs_ok = 1` 이다.
- `applies='yes'` 인데 참조가 없으면 `refs_ok = 0` 이다(서버도 `checks.refs='missing'` 으로 알린다).
- 변경 줄의 글을 따로 인용받지 않는다. 별칭이 닫힌 집합이라 '어느 줄을 봤나' 가 문구 대조 없이 확정된다.

#### 3.8.4 수치

- 판정 행의 수치는 서버의 `checks.nums_missing` 을 받아 적는다(그 카드 본문과 인용한 줄의 수치 **토큰 집합**에 `why` 의 수치가 있는가). 앱은 다시 세지 않는다.
- 걸린 행은 실패가 아니다. 그 행에서 올라간 finding 의 등급을 경험칙으로 묶고(§3.10.2) 보고서에 표시한다.
- 등록부로 가는 길의 수치 대조는 §3.8.6 의 `number_corpus` 가 맡는다.

#### 3.8.5 등급을 카드 confidence 로 정하는 표

| 카드 `confidence` | 조건 | 등급 |
|---|---|---|
| `fact` | `standard_refs` 가 비어 있지 않거나 `sources_n ≥ 1` | 문헌·규격 |
| `fact` | 출처가 하나도 없다 | 경험칙 |
| `heuristic` · `expert-judgement` · 값 없음 | — | 경험칙 |

```python
def card_grade(card: Mapping[str, Any]) -> str: ...
```

이 등급은 인용이 재대조를 통과한 행(`quote_ok = 1`)에만 뜻이 있다. 통과하지 못한 카드 인용은 등급에 세지 않는다. 지금은 `card:` 인용이 하나만 있어도 확인 없이 '문헌·규격' 이고(narrative.py:768), 이 전문가들의 카드는 `heuristic` 이 7,509 / 10,774 = 69.7% 다(03-cards).

#### 3.8.6 `narrative.py` 를 어떻게 넓히나

등록부로 가는 finding 은 패널이든 검토든 `_normalize_finding` 한 곳을 지난다. 그 함수가 카드 인용을 볼 수 있게 스코프를 넓힌다. 패널 경로의 동작은 바꾸지 않는다 — 새 인자는 기본값이 지금 동작이다.

```python
# common.py — parse_ref 의 card 분기
#   'card:<record_id>'              → {'kind':'card','record_id':…,'ref':'card:<record_id>'}
#   'card:<record_id>#<section_id>' → {'kind':'card','record_id':…,'section_id':…,'ref':'card:<record_id>#<section_id>'}

# narrative.py
@dataclass
class SpecContext:
    ...
    card_pack: Mapping[str, Any] | None = None     # record_id → 얼린 카드(sections · confidence · standard_refs …). None 이면 지금 동작(external_check)
    card_scope: frozenset | None = None            # 이번 전문가 · 이번 패널 좌석에 허용된 record_id. None 이면 묶음 전체
    number_corpus: str | None = None               # 수치 대조의 말뭉치. None 이면 지금 동작(모델의 quote 들)
```

| 함수 | 넓히는 것 |
|---|---|
| `_resolve_one`(644~650) | `kind == 'card'` 이고 `ctx.card_pack is not None` 이면 묶음에서 찾는다. 있으면 `ok=True, verified=True, payload=<그 카드>`, 묶음에 없으면 `not_in_pack`, 묶음에는 있는데 `card_scope` 밖이면 `not_in_scope` 다. `card_pack` 이 None 이면 지금 갈래(`external_check`) 그대로다. |
| `canonical_text_for`(496) | `kind == 'card'` 분기를 더한다. 묶음에서 `cardpack.card_text(카드)` 를, 절이 있으면 그 절의 `text` 를 돌려준다. 없으면 None. |
| `resolve_cites`(719) | `ref_type == 'card'` 인 행의 인용 대조만 `nq(quote) in nq(canonical)` + 길이 하한으로 한다. 다른 스킴은 지금 식 그대로다(그쪽 공백 정규화는 WP1 이 정한다). 통과한 card 행에 `card_grade` 를 싣는다. |
| `resolve_cites`(728~735) | `ctx.number_corpus` 가 있으면 claim · warrant 의 수치를 그 말뭉치의 수치 **토큰 집합**과 견준다(지금 식 `_NUMBER_TOKEN_RE` 로 양쪽을 뽑아 부호를 뗀 값으로 비교). None 이면 지금 식(모델이 쓴 quote 에 부분 문자열로 있는가)이다. 지금 식은 '5' 가 '0.15' 에 걸리고, 하나라도 없으면 통과한 인용 전부를 불일치로 만든다. |
| `evidence_grade_from_cites`(768) | card 행은 `row.get('card_grade')` 가 '문헌·규격' 일 때만 그 등급에 센다. `card_grade` 가 없는 행(묶음 없이 통과한 옛 길)은 지금처럼 '문헌·규격' 이다. |
| `_panel_scope`(1502) | 그 패널의 좌석 가운데 이 타깃에 묶음이 얼어 있는 전문가(`rr_expert_reports.pack_hash`)가 있으면 그 묶음들을 합쳐 `card_pack` 에 넣는다. 쟁점 패널이 카드를 인용할 때 처음으로 실재 확인을 받는다. 묶음이 하나도 없으면 None 이라 옛 타깃은 지금과 같다. |

검토 쪽 스코프는 새 함수가 만든다.

```python
def review_scope(store, target_key: str, agent_key: str, review_id: str, pack: Mapping[str, Any],
                 *, number_corpus: str | None = None) -> SpecContext:
    """_panel_scope 와 같은 타깃 · 스냅샷 · diff 스코프에 panel_id=review_id, seats=(agent_key,), card_pack=묶음을 얹는다."""
```

검토에서 올리는 finding 의 `number_corpus` 는 그 finding 이 인용한 카드들의 글과 인용한 변경 줄 · 근거 꾸러미 줄의 글을 이은 것이다.

#### 3.8.7 실효 판정(`effective_rows`)

한 (셀, 카드)에 변형이 여럿이면 하나를 실효로 고른다. 규칙은 고정이다. 견주는 것은 `(applies, judgement)` 쌍이다.

| 가진 행 | 실효 | 표기 |
|---|---|---|
| `fwd` 뿐 | `fwd` | — |
| `fwd` · `rev` 가 같다 | `fwd` | `agree = 1` |
| `fwd` · `rev` 가 다르고 `solo` 가 있다 | `solo` | `agree = 0`. `solo` 가 `fwd` 와 다르면 `n_flipped` 에 센다 |
| `fwd` · `rev` 가 다르고 `solo` 가 아직 없다 | 둘 중 **더 무거운 쪽**(FAIL > WARNING > undetermined > OK > na) | `agree = 0`, `n_disputed` 에 센다 |
| `fwd` 와 `solo`(양성 확인) | `solo` | 판정이 달라졌으면 `n_flipped` |

단독 재질의가 이기는 까닭은 카드 한 장만 놓고 조건을 하나씩 적게 한 답이 위치 · 묶음 영향을 가장 덜 받기 때문이다. 다만 이것은 가정이다 — 파일럿에서 K=1 을 기준으로 K 별 일치율을 재서 확인한다(§5.4). `solo` 가 실효가 되면 상세 칸(`sev` · `path` · `check` · 조건별 대조)도 그 행의 것을 쓴다.

### 3.9 표본(결정론)

난수를 쓰지 않는다. 표본은 해시로 정해지고, 잡을 다시 돌려도 · 재기동해도 · 처리 순서가 달라도 같다.

```python
# review_verify.py
SAMPLE_SALT = "rr-sample-1"          # 바꾸면 표본이 바뀐다. 잡 params.knobs.sample_salt 에 같이 적는다

def sample_score(purpose: str, *parts: str, salt: str = SAMPLE_SALT) -> float:
    """sha256('|'.join((purpose, salt, *parts))) 의 앞 12 hex 를 [0, 1) 로 옮긴다."""
```

#### 3.9.1 이중 판정(뒤집은 순서)

셀 `(T, U, A)` 는 Tier A 이거나 `sample_score('dual', T, U, A) < dual_rate`(기본 0.15)이면 그 셀의 점검 묶음 전부를 `rev` 로 한 번 더 돈다. 기본 온도가 0 이라 같은 프롬프트를 다시 보내면 같은 답이 온다(app.py:342). 그래서 카드 순서를 뒤집는다(별칭은 그대로라 카드별로 맞댈 수 있다).

`dual_rate = 1.0` 이면 전량이다. WP3a 는 '첫 실주행은 전량' 을 권고했다 — 그 선택은 사용자 몫이다(§8).

#### 3.9.2 음성 재질의와 단독 확인

| 대상 | 뽑는 규칙 | 호출 |
|---|---|---|
| 이중 판정 표본이 아닌 셀의 음성 카드(`OK` · `na`) 가운데 인용이 재대조를 통과하지 못한 것 | 전부 | 4장씩 묶어 `rev` |
| 그 밖의 음성 카드 | `sample_score('recheck', T, U, A, record_id) < recheck_rate`(기본 0.10) | 4장씩 묶어 `rev` |
| `fwd` ≠ `rev`(위 둘과 이중 판정에서 나온 것) | 전부 | 1장씩 `solo` |
| 실효 판정이 FAIL · WARNING | 전부(토의와 등록부에 올리기 전의 확인이고, 상세 보고서의 본문이 여기서 나온다) | 1장씩 `solo` |

음성 표본을 단독이 아니라 작은 `rev` 묶음으로 먼저 보는 것은 호출 수 때문이다. 판정 행의 약 9할이 음성이라 10% 를 1장씩 물으면 카드 대조 본 호출만큼 는다. 4장 묶음으로 걸러 어긋난 것만 단독으로 보낸다.

음성 표본에서 판정이 양성으로 뒤집힌 비율이 **놓침률의 추정치**다. 전문가 · 영역 · 타깃 단위로 `stats_json` 과 보고서 · 진행판에 싣는다. 코드가 못 잡는 거짓 '문제없음' 의 크기를 숫자로 보이게 하는 유일한 장치다.

#### 3.9.3 '해당 없음' 표본 재검토 — 뽑고 판정하는 쪽은 WP4

'해당 없음' 셀의 표본을 뽑고(`rr_cell_audits`), 놓침률의 상한을 계산하고, 놓침이 난 층을 다시 열지 정하는 것은 WP4 의 `audit.py` 다(그 문서 3.4 — 층은 영역 × 사유, 순번은 해시, 처음 59건). 표본도 결정론이고 내 `sample_score` 와 같은 방식이다.

이 꾸러미가 그 일에 내주는 것은 넷이다.

| 함수 | 하는 일 |
|---|---|
| `review_cells.reopen(store, target_key, *, cells=None, agent_key=None, domain=None, state='na_irrelevant', via='audit', by=None, why='') -> int`(`via` 는 `audit` 또는 `human`) | 셀을 `pending` 으로 돌리고 `route='review'` · `route_forced=via` · `sample_json.na_audit` 를 적는다. 그 전문가의 머리를 `planned` 로 돌린다. 반환은 다시 연 셀 수 |
| 검토 루프 | 다시 열린 셀을 **보통 셀과 똑같이** 대조한다(카드 대조 → 카드 밖 → 정산). 따로 도는 길이 없다 |
| `rr_review_cells.audit_result` | 감사로 다시 연 셀이 정산될 때 코드가 적는다 — 실효 판정에 `applies='yes'` 가 하나도 없고 카드 밖 호출이 `none` 이면 `clean`, 아니면 `miss`. 통계 판정은 WP4 가 이 열을 읽어 한다 |
| `review_cells.na_population(store, target_key) -> list[dict]` | 모집단 — `na_irrelevant` 셀과 그 신호값(`route_json`), 영역, 훑기의 사유 |

감사로 본 셀은 `clean` 이어도 `na_irrelevant` 로 되돌리지 않는다. 본 것은 본 것이고 `reviewed` 로 남는다.

훑기는 사유를 **코드가 아니라 글**(`why`, 80자 안)로 준다(WP3a). WP4 의 층은 '영역 × 사유 코드' 를 쓰므로 맞지 않는다 — 층 키로 쓸 수 있는 것은 결정적 신호의 `miss` 목록(`route_json.det.miss` — 예 `S-kind · S-card`)이다. §7.3 에 적는다.

WP4 가 붙기 전의 실주행에서는 Tier A 표본(아래)만으로 훑기의 놓침률을 본다.

#### 3.9.4 Tier A 표본(훑기의 놓침률을 일찍 잰다)

Tier A 전문가는 훑기 답과 무관하게 전 단위를 대조한다(§3.7.4). 그들의 셀 가운데 '훑기는 `no` 였고 결정적 신호도 `miss` 였는데 대조에서 `applies='yes'` 가 나온' 것이 놓침이다. 20건 이상 쌓인 뒤 놓침률이 `sweep_miss_max` 를 넘으면 그 잡의 나머지 전문가는 훑기를 건너뛴다(`route_forced='filter_off'`). Tier A 가 가장 먼저 돌므로(§3.7.3) 이 판단이 잡 초반에 선다.

### 3.10 finding 으로 올리는 길

올리는 때는 전문가 마감이다. 셀마다 올리지 않는 까닭은 같은 전문가가 여러 카드 · 여러 단위에서 같은 것을 지적하면 한 건으로 접어야 하기 때문이다.

#### 3.10.1 무엇이 finding 이 되나

| 원천 | finding 이 되나 |
|---|---|
| 카드 대조의 실효 판정 `FAIL` · `WARNING` | 된다(카드 근거) |
| 카드 밖 호출의 `f` 줄 — `dir='risk'` | 된다(`off_card: true`). `src='exp'` 면 등급은 늘 경험칙 |
| 카드 밖 호출의 `f` 줄 — `dir='improvement'` | 된다(개선 — `direction='improvement'`) |
| 입력 결손 질문 1 의 `impact='yes'` 줄 | 된다(`input_gap: true`) |
| `undetermined` · 질문 2 의 요청 · `need` 줄 | 안 된다. 보고서의 '필요한 추가 정보' 로 간다 |
| `OK` · `na` · `none` | 안 된다 |

#### 3.10.2 변환(코드가 채우는 칸)

`expert_report.build_findings(store, target_key, agent_key, pack, cells, rows, *, policy)` 가 `risk_spec` 의 finding 모양 dict 를 만들고, 하나씩 `narrative._normalize_finding(…, ctx=review_scope(…))` 에 태운다. 그러면 메커니즘 정규화 · subject 해석 · 인용 검증 · 등급 · `cluster_key` 가 패널 finding 과 **같은 코드**로 정해진다.

| finding 칸 | 값 |
|---|---|
| `direction` | `risk` 또는 `improvement`(카드 밖 호출의 `dir`) |
| `domain` · `owner_domain` · `raised_by` | 로스터의 영역 · 같은 값 · `[agent_key]` |
| `mechanism` · `mechanism_detail` | 카드 밖 호출은 `mech`(코드) 또는 `mech_free`. 카드 근거는 단독 재질의 행의 `mech`(WP3a 에 그 칸을 청한다 — §7.1. 없으면 `unclassified`). 택소노미 밖이면 `_normalize_mechanism` 이 `unclassified` 로 내리고 원문을 `mechanism_free` 에 둔다(지금 규칙) |
| `subject` | **모델이 지은 이름이 아니라 인용한 변경 항목에서 코드가 뽑는다.** 재대조를 통과한 `refs` 를 (의미 이벤트 → 구조 · 파라메트릭 항목 → `e:` → `p:` → `d:` → 그 밖) 순으로, 같은 급이면 참조 문자열 순으로 세워 첫 것을 쓴다. 항목의 `subject.ckeys` · `ckey` · `ckey_a/ckey_b` 가 있으면 `{ckeys: […]}`, `d:` 면 `{names: ['dim:<이름>']}`. 쓸 참조가 없으면 단위의 범위(`rr_units.scope_key` 가 `asm:<접두>` 꼴이면 그 조립 단위)로 내리고 그 finding 은 `weak_subject` 가 된다 |
| `change_kind` | 같은 항목의 `change_kind`. 없으면 `none`(snap 타깃은 늘 `none`) |
| `claim` · `warrant` | 카드 근거 — 실효 행의 `why`, 그리고 "근거 카드 <card_id> «<cq>»". 카드 밖 — `title` 과 `path`. 접힌 구성원이 여럿이면 대표(심각도 높은 순 → 인용이 통과한 순 → 별칭 순 → 단위 순)의 것 |
| `cites` | `{ref: 'card:<record_id>', quote: cq}` 와 변경 줄 참조 `{ref, quote: ''}`. 구성원 전부의 합집합에서 통과한 것 먼저, 12건까지 |
| `severity` · `judgement` | §3.10.3 |
| `detectability` · `resolving_check` | 단독 재질의 · 카드 밖 줄의 `check_kind` · `check` 에서 — `tool` · `sim` 은 `sim-detectable`(tool = check 글 앞 80자), `test` 는 `test-only`, `field` 는 `field-only`, 없으면 `unknown`. `resolving_check = {kind, ref: check 글}` |
| `evidence_grade`(주장 등급) | 카드 근거 — 인용한 카드들의 `card_grade` 중 가장 높은 것(인용이 통과한 것만). 카드 밖 `src='exp'` · 긴 문서 발췌(`src='D…'`) · 수치가 걸린 것(`nums_missing`) — `경험칙`. 배경 카드를 댄 카드 밖 줄(`src='K…'`)은 그 카드의 등급. 최종 등급은 지금 규칙대로 주장과 계산 중 낮은 쪽이다(narrative.py:1030) |
| `trigger_condition` | `none` |
| 덧붙이는 칸 | `source: 'card_review'`, `review_id`, `unit_ids`, `cards: [{record_id, card_id, judgement, variant, agree, flipped}]`, `off_card`, `input_gap`, `conf`, `judgement_claimed`, `severity_claimed`, `nums_missing`, `doc_refs`(긴 문서 발췌의 record_id · section_id) |

긴 문서 발췌는 `cites` 에 넣지 않는다. `paper:` 참조는 브리프가 부른 원장(`rr_brief_calls`)에 있는 것만 해석되므로(narrative.py:222~236) 넣으면 전부 dangling 이 된다. `doc_refs` 로 남겨 보고서에 보이게 하고, 그 근거로는 등급을 올리지 않는다.

**한 셀 안에서 접기.** 정규화가 끝난 뒤 같은 단위에서 `(cluster_key, direction)` 이 같은 것은 한 건으로 합친다. 카드 8장이 같은 변경의 같은 메커니즘을 가리키면 finding 은 하나이고 `cards[]` 가 8건이다. 단위를 넘어서는 접지 않는다 — WP4 가 finding 마다 `unit_id` 하나를 읽고(지지 단위 수 · 쟁점의 단위), 같은 전문가가 여러 단위에서 같은 클러스터를 올려도 지지 수는 전문가 수라 한 명이다.

**id 는 내용에서 나온다.** `claim_uid = finding_id = f"{review_id}#{'G' if 개선 else 'F'}{int(sha1(cluster_key + '|' + unit_id)[:8], 16)}"` 다. 스키마 패턴(`^[0-9a-f]{32}#[FG][0-9]+$`)에 맞고, 다시 마감해서 finding 집합이 바뀌어도 **남아 있는 finding 의 id 는 그대로**다. 1부터 번호를 매기면 실패 셀 하나를 다시 돌린 것만으로 뒤 번호가 전부 밀려 `narr:<opinion_id>#F3` 인용과 라벨이 엉뚱한 finding 을 가리킨다.

**쓰기.** 마감 트랜잭션 안에서 `claim_uid` 가 `<review_id>#` 로 시작하는 finding 가운데 새 집합에 없는 것(과 그 `rr_claim_refs`)을 지우고 나머지를 `INSERT OR REPLACE` 한다. WP4 가 같은 일을 하는 공용 함수(`narrative.persist_single_findings`)를 두면 그것을 쓴다 — 교차 · 사냥 응답과 저장 규칙이 하나가 된다. `rr_claim_refs` · `suspect_text` 큐 적재는 `persist_panel_result` 와 같은 규칙이다(narrative.py:1742~1770). 서버가 알려 준 주입 의심(`extras.inj`)이 있는 셀의 finding 은 `recall_eligible = 0` 으로 넣는다(다음 과제의 회수 후보에서 빠진다 — 사람이 승인하면 돌아온다). 택소노미 밖 메커니즘을 큐레이션 큐에 올릴 때는 **타깃 안에서 같은 원문을 한 번만** 올린다 — 359명이 같은 말을 수백 번 올리지 않게 한다.

#### 3.10.3 심각도와 판정 — 기본은 '보류' 정책

등록부의 verdict 후보는 `FAIL` 이고 반대석이 기각하지 않은 클러스터가 하나라도 있으면 `no-go` 다(registry.py:648, 662~663). 검토에는 반대석이 없어 `contested` 가 늘 0 이다. 그래서 카드 대조 한 번의 `FAIL` 을 등록부에 그대로 올리면 **토의 한 번 없이 타깃이 no-go 후보가 된다.**

| 검토가 낸 것 | `hold`(기본)에서 등록부에 적는 값 | `direct` |
|---|---|---|
| 실효 판정 `WARNING` | 단독 재질의의 `sev`(없으면 경미)를 중대까지로 묶고 · WARNING | 같다 |
| 실효 판정 `FAIL`, 단독 재질의가 아직 없거나 뒤집혔다 | 중대 · WARNING | 같다 |
| 실효 판정 `FAIL`, 단독 재질의도 `FAIL` 이고 `quote_ok = 1` · `refs_ok = 1` | 중대 · WARNING | 단독 재질의의 `sev`(중대 · 치명) · FAIL |
| 카드 밖 리스크 · 입력 결손 질문 1 | 모델이 준 `sev` 를 중대까지로 묶고 · WARNING | 같다 |
| 개선 | 경미 · OK | 같다 |

`hold` 에서 심각도를 중대로 묶는 까닭은 `치명` 이 `FAIL` 과만 짝이 되어(`_SEV_JUDGEMENT`, narrative.py:108) 정규화가 판정을 `FAIL` 로 고쳐 버리기 때문이다. 검토가 낸 원래 값은 `judgement_claimed` · `severity_claimed` 에 남고 보고서와 판정 행(`rr_card_verdicts`)에는 `FAIL` 그대로 보인다. 등록부의 `FAIL` 은 쟁점 패널(WP4)이나 사람이 올린다. 어느 정책으로 갈지는 사용자가 정한다(§8).

#### 3.10.4 등록부 병합과 지지 수

- **병합 시점.** `registry.merge(store, target_key)` 는 타깃 전체를 다시 계산한다(그동안 `tx()` 가 락을 쥔다). 전문가 마감마다 부르지 않고 **잡마다 300초에 한 번 이하 + 잡이 멈추거나 끝날 때 한 번**으로 묶는다. 병합은 멱등이고 입력을 `finding_id` 로 정렬하므로(registry.py:166, 195) 순서와 무관하게 같은 결과다.
- **지지 수를 전문가 수로 센다 — 식과 열의 주인은 WP4 다.** 지금 식은 `support = len(서로 다른 panel_id)`, 패널이 없으면 원자 수다(registry.py:205~206). 검토 finding 이 그대로 들어가면 359명이 낸 같은 지적이 '원자 수' 로 세져 한 전문가가 여러 단위에서 올린 만큼 부푼다. WP4 가 `_merge_cluster` 를 고쳐 `support_experts`(서로 다른 제기 전문가) · `support_domains` · `support_units` · `support_verified` 를 채우고, 새 흐름 타깃의 `support` 를 `support_experts` 와 같게 둔다. 선례 통계(`_recompute_contrib`)에는 영역 수를 넣고, 재제기 비교(`_is_stronger`)는 같은 것끼리 견준다(그 문서 3.5.1).
- **그 식이 제대로 세려면 내가 지켜야 하는 것이 넷이다.**
  1. `finding_json.raised_by = [agent_key]` — 한 명, 로스터의 키 그대로. 의장 · 반대석 키를 넣지 않는다.
  2. `rr_findings.agent_key` · `unit_id` · `source_kind='card_review'` · `source_id=review_id` 를 채운다.
  3. 기각 표기를 쓰지 않는다(`status` 는 늘 `open`). 검토에는 기각이 없다.
  4. 인용 검증 결과(`dangling` · `quote_mismatch` · `unverified_refs`)를 `_normalize_finding` 이 낸 그대로 둔다 — `support_verified` 가 그것을 읽는다.
- **WP4 가 늦으면.** 지금 식에서도 깨지지는 않는다(`panel_id` 가 NULL 이라 원자 수로 센다 — 부풀지만 순위에는 쓰이지 않는다. 우선순위 식에 지지 수가 없다 — registry.py:298). 다만 그 상태로 전원 검토를 돌리면 등록부의 지지 수 칸을 믿을 수 없으므로 실주행 D(§5.4)는 WP4 의 병합 변경 뒤에 한다.
- **근접 중복.** 내가 하는 것은 둘이다.
  1. 한 셀 안 — `(cluster_key, direction)` 으로 접는다(§3.10.2).
  2. subject 를 인용한 변경 항목에서 코드가 뽑는다. 같은 변경을 짚은 전문가들은 이름을 어떻게 불렀든 같은 `subject_key` 로 모여 등록부 한 행이 된다.

  택소노미 밖 메커니즘이 한 행으로 뭉치는 것(광학 · 음향 · RF 코드가 없어 cam · sh · rf 57명의 지적이 `unclassified` 로 몰린다)과 메커니즘만 다른 이웃 행을 묶어 보이는 것은 WP4 가 다룬다(그 문서 3.5.2 — 미분류의 세부 자리에 자유 낱말 키를 넣는 제안이 있다). 내 쪽은 `mechanism_free` 원문을 finding 에 잃지 않고 남긴다.

### 3.11 전문가별 보고서(코드 조립, LLM 0회)

```python
# expert_report.py
REPORT_REV = "expert-report-1"

def build_report(store, target_key: str, agent_key: str) -> dict:
    """판정 행 · 셀 · 호출 원장 · 얼린 팩에서 보고서 JSON 을 조립한다. 같은 원장이면 같은 바이트다."""
def load_report(store, target_key: str, agent_key: str) -> dict:
    """마감 때 얼린 보고서 JSON(없으면 E404)."""
def render_report_md(report: Mapping[str, Any], *, unit_id: str | None = None, part: str = "full") -> str:
    """보고서 JSON → 마크다운. part ∈ {'summary','units','cards','full'}"""
def summary_md(report: Mapping[str, Any]) -> str:
    """≤1500자 요약(의견 행의 excerpt_for_rag 와 turns[0]). 코드가 쓰는 문장은 수와 참조뿐이고 전문가의 글은 «» 로 감싼다."""
```

요약 호출을 따로 두지 않는다. 판정 행이 이미 구조화돼 있고, LLM 이 다시 쓰면 검증을 통과한 내용을 빠뜨리거나 새 수치를 만든다(띵킹 모드의 종합이 코드 조립인 것과 같은 이유다 — thinking.py:264~317). '상세' 는 요약 호출이 아니라 **단독 재질의의 본문**(조건별 대조 · 영향 경로 · 닫는 확인)에서 온다.

#### 3.11.1 구조

| 절 | 내용 |
|---|---|
| `head` | `agent_key` · 이름 · 영역 · 영역 내 순위 · tier · `review_id` · 모델 · `prompt_rev` · `norm_rev` · `verify_rev` · `report_rev` · 판번호 · 만든 시각 · 카드 묶음(`pack_hash`, 점검 n장 · 배경 n장 · 본문 없는 카드 n장, 얼린 시각, `card_basis`) · 입력 결손(`input_gaps`) |
| `scope`(본 범위) | 단위마다 한 줄 — 셀 상태, 분류(`route_det` · `route_llm` · `route_forced`), 사유(훑기의 `why` · 실패 코드와 시도 수), 무엇으로 봤나(`basis`), 판정별 건수. 끝에 합계와 **보지 못한 것**(`no_input` · `failed` · 범위 밖이라 남은 `pending`)을 따로 센다 |
| `checklist`(카드 점검표 전 행) | 점검 카드(별칭 순) × 대조한 단위마다 **실효 판정 한 행** — `applies` · `judgement` · 카드 인용과 재대조 표기 · 변경 줄 참조와 소속 표기 · 이유 · 필요 정보 · 등급 · 표기(변형 · 일치 · 뒤집힘 · 다툼 · 수치 미확인 · 서버와 앱의 대조 불일치). 생략하는 행이 없다. 배경 카드는 제목만 '판정 대상 아님' 으로, 본문 없는 카드 · 창을 넘은 카드는 '판정하지 못한 카드' 로 싣는다 |
| `by_unit`(단위별 분석) | 단위마다 FAIL → WARNING(둘은 단독 재질의의 조건별 대조 · 영향 경로 · 닫는 확인까지) → undetermined(필요한 자료와 함께) → OK · na(한 줄씩) 순으로, 그 단위의 카드 밖 우려 · 개선을 뒤에 붙인다 |
| `off_card`(카드 밖 우려) | 전 단위의 카드 밖 줄. 줄마다 근거(`exp` 경험칙 · 배경 카드 · 긴 문서 발췌)와 그 대조 결과, 변경 줄 참조의 소속 여부. `exp` 는 '카드 근거 없음 — 코드가 원문과 대조할 수 없다' 로 표기한다 |
| `input_gap`(입력이 오면 확인할 것) | 입력 결손 전문가만. 질문 2 의 요청(`item` · `needs` · 근거 줄 · 카드)을 단위별로 |
| `handoff`(넘김) | 다른 영역으로 넘긴 것(받는 영역 · 사유 · 어느 단위 · 어느 줄). 훑기의 `h` 와 카드 밖 호출의 `h` 를 합친다 |
| `needs_info`(필요한 추가 정보) | `undetermined` 행의 `need` + 카드 밖 호출의 `need` 줄. 공백 정규화로 겹침을 없애고 단위별로 묶는다 |
| `mechanisms` | 카드 밖 호출의 `m.seen` 을 단위별로(따져 본 메커니즘 — 문제없다고 본 것 포함) |
| `findings` | 올린 finding 의 `claim_uid` · `cluster_key` · 방향 · 심각도 · 판정 · 등급 · 근거 카드 |
| `quality` | 카드 판정 수 / 기대 수, 훑기에서 안 읽힌 카드 수, 카드 인용 재대조율, 변경 줄 참조 소속률, 이중 판정 일치율, 단독 재질의로 뒤집힌 수(양성 → 음성 · 음성 → 양성), 수치 미확인 행 수, 절단된 호출 수, 품질 한도를 넘긴 호출 수, 서버와 앱의 대조 불일치 수, 주입 의심 줄 수, 훑기 답과 대조 결과가 어긋난 단위 수 |

#### 3.11.2 저장과 크기

- 마감 때 `canonical_json(report)` → gzip → `rr_expert_reports.report_gz`, 해시는 `sha256[:12]` 다. 해시가 직전과 다를 때만 `revision` 을 올린다.
- 판정 행에서 언제든 다시 만들 수 있는데도 얼려 두는 이유는 둘이다 — 조립 코드가 바뀐 뒤에도 '그때 내보낸 보고서' 가 남고, WP4 가 부록으로 실을 때 조립을 다시 돌리지 않는다.
- 크기(추정)는 전문가당 원문 60~150 KB, gzip 10~25 KB 다. 359명이면 타깃당 약 5 MB 다.
- 원장의 `opinion_json` 에는 보고서를 넣지 않는다(스키마가 닫혀 있다). 의견 행에는 `summary_md` 만 간다.

### 3.12 REST · MCP 응답 계약

기존 필드는 지우지 않는다. 전부 추가다. 읽기는 `_target_row(target_key, owner_sub)`, 쓰기는 `require_role(project_id, email, 'editor')` + `rr_audit` 한 행이다(지금 관례).

#### 3.12.1 REST

| 메서드 · 경로 | 무엇 |
|---|---|
| `POST /targets/{key}/jobs` | 본문에 `mode`(`panels` 또는 `reviews`, 기본 `panels` — 지금 호출자는 그대로다). `reviews` 면 `scope` · `user_memo` · `consent` 를 받고 `runner.create_job` 대신 `review_runner.create_review_job` 으로 간다 |
| `POST /jobs/{job_id}/{action}` | 그대로다. 검토 잡도 같은 표라 `pause` · `resume` · `cancel` 이 그대로 듣는다 |
| `GET /targets/{key}/coverage` | 응답에 `review` 칸을 더한다(아래) |
| `GET /targets/{key}/cells` | `?agent_key=&unit_id=&domain=&state=&limit=(기본 500, 최대 2000)&offset=` |
| `GET /targets/{key}/cells/{unit_id}/{agent_key}` | 셀 하나 — 셀 행 + 판정 행 전부(변형별) + 호출 목록(`result` 본문 제외) |
| `GET /targets/{key}/experts` | 전문가 머리 목록 `?domain=&state=` |
| `GET /targets/{key}/experts/{agent_key}/report` | 쿼리 `format`(`json` · `md`) · `part`(`summary` · `units` · `cards` · `full`) · `unit_id` |
| `POST /targets/{key}/cells/reopen` | 사람이 다시 연다. 본문 `{filter: {agent_key?, unit_id?, state, error_code?}, reason, force?: bool}` — `state` 는 `failed` · `na_irrelevant` · `no_input` · `reviewed` 가운데 하나다. `reviewed` 는 `force` 가 있어야 한다 |
| `PUT /targets/{key}/cells/{unit_id}/{agent_key}` | 실패 셀의 처분. 본문 `{dispose: true, note}`(note 필수) |
| `POST /targets/{key}/packs/refresh` | 카드가 바뀌었는지 본다. 본문 `{agents?: [...], reopen?: bool}` |

`coverage` 에 더하는 칸이다.

```json
"review": {
  "units": 8,
  "cells": {"total": 2872, "by_state": {"pending": 1900, "running": 4, "reviewed": 610, "na_irrelevant": 320, "no_input": 12, "failed": 26},
            "failed_open": 21, "failed_disposed": 5},
  "experts": {"total": 359, "by_state": {"planned": 268, "running": 4, "ready": 82, "partial": 3, "blocked": 2}},
  "cards": {"expected": 9120, "judged": 9120, "quote_rate": 0.93, "refs_rate": 0.97, "check_disagree": 0},
  "sampling": {"dual_cells": 131, "dual_agree_rate": 0.91, "recheck_rows": 870, "recheck_flip_rate": 0.02,
               "na_audit": {"sampled": 59, "missed": 0}},
  "job": {"id": "…", "mode": "reviews", "state": "running", "hold_code": null, "hold_until": null, "error": null, "credential_email": "…",
          "phase": "review", "progress": {"…": "§3.7.10 의 progress_json 그대로"},
          "signal": {"workers": [{"agent_key": "…", "unit_id": "…", "call_kind": "verdict", "variant": "fwd", "deck_id": "v2",
                                  "started_at": 0, "last_frame_at": 0, "last_event_at": 0, "last_step": "attempt 1",
                                  "frame_idle_s": 12, "event_idle_s": 55}]}}
}
```

`signal.workers[]` 는 잡이 `running` 일 때만 싣고 `*_idle_s` 는 서버 시계로 잰다(패널의 `_live_signal` 과 같은 규칙 — routes.py:2236~2251). `last_step` 은 서버가 흘리는 `status.step`(`queued` · `search` · `attempt`)이다.

`GET /targets/{key}/cells` 의 행이다.

```json
{"unit_id": "u:5d0c1e9a77b2", "unit_seq": 3, "agent_key": "mech-ip-sealing", "domain": "mech",
 "state": "reviewed", "route": "review", "route_det": "hit", "route_llm": "yes", "route_forced": null,
 "route_json": {"det": {"det": "hit", "hits": ["S-role:gasket"], "blind": [], "miss": []}, "sweep": {"rel": "yes", "k": ["K01", "K04"], "why": "…"}},
 "basis": "cards", "input_gap": null,
 "attempts": 0, "infra_retries": 1, "error_class": null, "error_code": null, "error": null, "retry_at": null,
 "cards_expected": 13, "cards_judged": 13,
 "n_fail": 0, "n_warning": 2, "n_ok": 7, "n_na": 3, "n_undetermined": 1, "n_offcard": 1, "offcard_state": "done",
 "n_flipped": 0, "n_disputed": 0, "quote_ok": 12, "quote_n": 13, "refs_ok": 10, "refs_n": 10,
 "calls_n": 4, "prompt_chars": 61240, "prompt_tokens": 27650, "completion_tokens": 3410, "truncated": false, "soft_over": false,
 "sample": {"dual": false, "na_audit": false, "recheck": ["DOC-…-0000000147"]}, "audit_result": null,
 "pack_hash": "9c1e0a7b3d2f4e61", "unit_hash": "5a0c…", "model": "…", "prompt_rev": "cr-p1:3f9a12c4", "verify_rev": "verify-1",
 "status_source": "code", "decided_by": null, "decided_at": null, "decide_note": null,
 "started_at": 0, "finished_at": 0}
```

응답 머리는 `{target_key, total, limit, offset, rows: [...]}` 다.

`GET …/experts/{agent_key}/report?format=json` 은 §3.11.1 의 JSON 에 머리를 붙인다.

```json
{"target_key": "diff:…", "agent_key": "mech-ip-sealing", "state": "ready", "revision": 2, "report_hash": "a1b2c3d4e5f6",
 "finalized_at": 0, "coverage_status": "done", "opinion_id": "…", "review_id": "…",
 "report": {
   "head": {"name": "IP 실링", "domain": "mech", "rank_in_domain": 3, "tier": "B", "model": "…",
            "prompt_rev": "…", "norm_rev": "…", "verify_rev": "…", "report_rev": "…", "input_gaps": [],
            "pack": {"pack_hash": "…", "checkable_n": 13, "background_n": 17, "unrenderable_n": 0, "frozen_at": 0, "card_basis": "cards"}},
   "scope": {"units": [{"unit_id": "…", "unit_seq": 3, "title": "…", "state": "reviewed", "basis": "cards",
                        "route_det": "hit", "route_llm": "yes", "route_forced": null, "reason": null,
                        "counts": {"FAIL": 0, "WARNING": 2, "OK": 7, "na": 3, "undetermined": 1}}],
             "totals": {"reviewed": 3, "na_irrelevant": 4, "no_input": 0, "failed": 1, "pending": 0}},
   "checklist": [{"alias": "K01", "record_id": "…", "card_id": "MIS-R-001", "type": "design-rule", "confidence": "heuristic",
                  "grade": "경험칙", "title": "…",
                  "rows": [{"unit_id": "…", "applies": "yes", "judgement": "WARNING", "variant": "solo", "agree": null, "flipped": false,
                            "cq": "…", "quote_ok": true, "lines": ["L02"], "refs": ["c:9f3a1b2c3d4e"], "refs_ok": true,
                            "why": "…", "need": "", "sev": "중대", "mech": "interface.seal_compression", "path": "…",
                            "check_kind": "sim", "check": "…", "conds": [{"cond": "…", "l": ["L02"], "met": "no", "note": "…"}],
                            "nums_missing": [], "check_disagree": false}]}],
   "background": [{"alias": "K14", "card_id": "MIS-C-001", "type": "concept", "title": "…"}],
   "unjudged_cards": [],
   "by_unit": [{"unit_id": "…", "title": "…", "FAIL": [], "WARNING": ["K01", "K04"], "undetermined": ["K09"],
                "OK": ["K02"], "na": ["K03"], "off_card": [0], "improvements": []}],
   "off_card": [{"unit_id": "…", "dir": "risk", "title": "…", "path": "…", "lines": ["L03"], "refs": ["c:…"], "refs_ok": true,
                 "src": "exp", "q": "", "quote_ok": null, "mech": "mechanical.impact", "sev": "경미", "conf": "medium",
                 "check_kind": "test", "check": "…", "finding_id": "…#F123"}],
   "input_gap": [],
   "handoff": [{"to": "rel", "why": "…", "unit_id": "…", "lines": ["L03"]}],
   "needs_info": [{"unit_id": "…", "items": ["개스킷 홈 깊이 공차"]}],
   "mechanisms": [{"unit_id": "…", "seen": ["interface.seal_compression", "mechanical.impact"]}],
   "findings": [{"claim_uid": "…#F3735928559", "cluster_key": "…", "direction": "risk", "severity": "중대", "judgement": "WARNING",
                 "judgement_claimed": "FAIL", "evidence_grade": "경험칙", "cards": ["MIS-R-001"]}],
   "quality": {"cards_expected": 39, "cards_judged": 39, "cards_unseen_in_sweep": 0, "quote_rate": 0.92, "refs_rate": 1.0,
               "dual_agree_rate": null, "flipped_pos_to_neg": 0, "flipped_neg_to_pos": 0, "nums_missing_rows": 1,
               "truncated_calls": 0, "soft_over_calls": 0, "check_disagree": 0, "inj_lines": 0, "sweep_mismatch_units": 0}}}
```

`/apps/` 의 프록시 한도가 600초이므로 새 경로는 전부 DB 읽기 · 짧은 쓰기다. 네트워크를 부르는 것은 `packs/refresh` 하나이고 명단 조회와 같은 540초 기한을 건다(`HWAXRISK_ROSTER_DEADLINE_S` 선례). 전원을 한 번에 다시 받으면 그 기한을 넘으므로 한 번에 40명까지 받고 `{checked, changed[], remaining}` 을 돌려준다.

#### 3.12.2 MCP

읽기 도구 둘을 더한다. REST 와 같은 함수를 부른다(`mcp_server._scoped`).

| 도구 | 인자 | 반환 |
|---|---|---|
| `risk_get_cells` | `target_key, agent_key=None, unit_id=None, state=None, limit=200` | `GET /targets/{key}/cells` 와 같은 모양 + `review` 요약 칸 |
| `risk_get_expert_report` | `target_key, agent_key, part='summary', unit_id=None` | `part='summary'` 는 머리 + `summary_md` + `quality` + `scope.totals`, `units` · `cards` · `full` 은 마크다운 본문 |

MCP 의 기본을 `summary` 로 두는 것은 응답이 게이트웨이를 거쳐 모델 문맥으로 들어가기 때문이다. `full` 은 수만 자다. `risk_get_coverage` 응답에는 `review` 칸이 그대로 붙는다. 쓰기 도구는 더하지 않는다. `tests/test_mcp_tools.py` · `tests/test_no_write_tools.py` 의 목록에 둘을 더한다(WP2 가 `risk_get_units` 를 더하므로 합쳐 17종이 된다).

### 3.13 설정 손잡이

전부 `config.Settings` 에 더하고 env 이름은 `HWAXRISK_<대문자>` 다. SIF 가 cleanenv 라 **매니페스트 `launch.env` 에 적어야 닿는다**(`config.KNOB_HOME`). 등록 사본(HEAXHub `integrations/hwax-risk`)도 같이 고친다.

| 손잡이 | 기본 | 뜻 |
|---|---|---|
| `HWAXRISK_REVIEW_CONCURRENCY` | 4 | 검토 워커 수(타깃을 가로질러 하나). 서버 관문(`CARD_REVIEW_CONCURRENCY` 기본 4)과 같게 둔다 |
| `HWAXRISK_REVIEW_CALL_TIMEOUT_S` | 18000 | 검토 호출 1건의 벽시계. 0 = 끔 |
| `HWAXRISK_REVIEW_MAX_ATTEMPTS` | 2 | 내용 탓 실패의 시도 한도 |
| `HWAXRISK_REVIEW_SWEEP` | `auto` | `auto`(§3.7.4 표) · `off`(훑기 없이 전수 대조) |
| `HWAXRISK_REVIEW_SWEEP_MISS_MAX` | 0.05 | 놓침률이 이 값을 넘으면 그 타깃의 필터를 끈다 |
| `HWAXRISK_REVIEW_DUAL_RATE` | 0.15 | 이중 판정 표본 비율(1.0 = 전량) |
| `HWAXRISK_REVIEW_RECHECK_RATE` | 0.10 | 음성 판정의 재질의 표본 비율 |
| `HWAXRISK_REVIEW_SEARCH` | `cardless` | 카드 밖 호출에 긴 문서 검색을 붙일 대상 — `cardless`(점검 카드가 없는 전문가만) · `all` · `off` |
| `HWAXRISK_REVIEW_FINDING_POLICY` | `hold` | `hold` · `direct`(§3.10.3) |

묶음 크기 · 프롬프트 크기 · 호출 안 보충 횟수는 서버의 손잡이다(`CARD_REVIEW_K` · `CARD_REVIEW_PROMPT_SHARE` · `CARD_REVIEW_PARSE_RETRIES` — WP3a). 앱에 같은 것을 두지 않는다.

기동 때 사슬 하나를 더 본다(`main.check_credential_chain` 옆). `review_credential_margin_s ≥ PAT_MIN_REMAINING_S` 면 기동을 막는다 — 패널 쪽과 같은 이유다.

### 3.14 수치

#### 3.14.1 셀 수와 호출 수

전문가 359명(카드가 있는 사람 356명), 점검 카드 4,587장(design-rule 2,161 + failure-case 1,393 + standard-summary 1,033), 배경 카드 6,184장이다(03-cards). 점검 카드는 전문가당 평균 12.9장이라 점검 묶음은 평균 2개다. ECAD 가 스텁인 지금은 회로 6개 영역 110명(30.6%)이 입력 결손 전문가라 카드 대조 대신 두 질문 호출 1번으로 간다.

B 를 검토 대상 단위 수, r 을 대조로 가는 셀의 비율, g = 0.306 을 입력 결손 전문가의 비율이라 하자.

| | 식 | B=8 · r=1.0 | B=8 · r=0.5 | B=20 · r=0.3 |
|---|---|---|---|---|
| 셀 | 359 × B | 2,872 | 2,872 | 7,180 |
| 대조로 가는 셀 | 셀 × r | 2,872 | 1,436 | 2,154 |
| (가) 훑기 | 356 × 훑기 묶음(1~2) × 쪽(대개 1). 필터를 껐으면 0 | 0 | 약 430 | 약 430 |
| (나) 카드 대조 `fwd` | 2 × 대조 셀 × (1 − g) | 3,984 | 1,992 | 2,990 |
| (다) 카드 밖 | 대조 셀 × (1 − g) | 1,992 | 996 | 1,495 |
| 입력 결손 두 질문 | 대조 셀 × g | 880 | 440 | 659 |
| 이중 판정 `rev` | 2 × (0.15 × 비결손 대조 셀 + 0.85 × Tier A 비결손 9명 × B) | 720 | 420 | 754 |
| 음성 표본 `rev`(4장 묶음) | 0.10 × 음성 행 ÷ 4 | 618 | 309 | 463 |
| 단독 `solo` | 판정 행 × p⁺(p⁺ = 3% 로 **가정**) + 불일치 | 약 764 | 약 382 | 약 573 |
| '해당 없음' 표본 재검토(WP4 가 다시 여는 셀) | max(59, 5% × na 셀) × 셀당 약 2.4호출 | 0 | 약 173 | 약 605 |
| **호출 합** | | **≈ 8,960** | **≈ 5,140** | **≈ 7,970** |

판정 행(`fwd`)은 비결손 전문가의 점검 카드 약 3,183장 × B × r 이다(25,466 · 12,732 · 19,098 행).

지금 구조의 전원 편성은 72패널 × 49~95회 = 3,528~6,840회다(02-cost). 같은 자릿수다. 다만 지금 구조는 ECAD 부재 때 104명을 아예 앉히지 않으므로(실제 51패널 · 2,499~4,845회) 같은 일을 견주는 것은 아니다.

벽시계는 호출 시간에 비례하는데 **그 값이 없다**. 호출 1회 5분(단독 · 4장 묶음은 2분)으로 놓으면 아래와 같다. 전부 추정이다.

| | B=8 · r=1.0 | B=8 · r=0.5 | B=20 · r=0.3 |
|---|---|---|---|
| 작업 시간 합 | 약 677시간 | 약 394시간 | 약 612시간 |
| 동시 4 | 약 7.1일 | 약 4.1일 | 약 6.4일 |
| 동시 2(심의가 도는 동안의 서버 관문) | 약 14일 | 약 8.2일 | 약 12.8일 |

읽는 법이 셋이다. 첫째, **r 이 전부다.** 결정적 신호(WP2)가 `blind` 뿐이면 r = 1 이고 타깃 하나가 일주일이다. 둘째, 동시 수를 앱에서 올려도 서버 관문(기본 4, 심의가 도는 동안 2)이 상한이다 — 일정을 줄이려면 그 손잡이를 같이 올려야 하고 그것은 LLM 을 얼마나 내줄지의 결정이다(§8). 셋째, 며칠이 걸려도 운영을 막는 것은 아니다 — 호출 하나가 끊겨도 잃는 것은 그 호출뿐이고 재기동 뒤 스스로 이어 돈다.

#### 3.14.2 표 크기(타깃 하나, 추정)

| 표 | 행 수(B=8 · r=0.5) | 크기 |
|---|---|---|
| `rr_review_cells` | 2,872 | 약 3 MB(신호값 · 카드 밖 줄 포함) |
| `rr_card_verdicts` | 약 17,000(fwd 12,732 + rev 약 3,900 + solo 약 400) | 약 14 MB(행당 약 0.8 KB — 인용 · 이유 · 서버의 checks) |
| `rr_review_calls` | 약 5,100 | 약 13 MB(`result` gzip 약 2~3 KB) |
| `rr_expert_reports` | 359 | 약 5 MB |
| `rr_findings` 증가분 | 수백 | 약 1~2 MB |
| **합** | | **약 35~40 MB** |

r = 1 이면 약 65 MB, B=20 · r=0.3 이면 약 55 MB 다. 타깃 50개면 2~3 GB 다. SQLite 한 파일로 감당되는 크기지만 Drive 백업(`sqlite3 .backup` 뒤 tar)이 그만큼 커진다. 닫힌 타깃의 `rr_review_calls.result_gz` 를 N일 뒤 비우는 야간 정리는 이번 판에 넣지 않는다.

`rr_card_packs` 는 **타깃 수와 무관하게 한 벌**이다. 카드 원문이 약 2,050만 자(10,774 × 1,902)이고 UTF-8 로 약 50 MB, gzip 으로 15~20 MB 로 본다(압축률은 재지 않았다). 카드가 바뀐 전문가만 한 행(약 50 KB)씩 는다.

메모리는 문제가 되지 않는다. 묶음 캐시가 32명분(약 5 MB), 워커 하나가 쥐는 것이 묶음 하나와 단위 하나다. 매니페스트의 `memory_gb: 2` 안이다.

#### 3.14.3 SQLite 쓰기 경합

- **프로세스 안.** 연결이 하나이고 `RLock` 이 직렬화한다. 검토가 내는 쓰기는 호출 하나에 트랜잭션 하나(판정 ≤ 8행 + 셀 + 호출 원장)이고, 동시 6 · 호출 5분이면 **분당 1~2건**이다. 처리량은 문제가 아니다.
- 문제는 **락을 오래 쥐는 트랜잭션**이다. `tx()` 가 도는 동안 REST 읽기가 전부 기다린다. 긴 것은 둘이다 — 등록부 병합(finding 수천 건의 `finding_json` 을 읽어 다시 계산한다, 1~3초로 **추정**)과 전문가 마감(수십 ms). 그래서 병합을 300초에 한 번으로 묶고(§3.10.4), 카드 묶음 저장은 전문가마다 따로 커밋한다.
- **프로세스 밖.** `busy_timeout` 을 명시하지 않아 파이썬 기본 5초다. 같은 DB 를 여는 다른 프로세스(백업, 손으로 띄운 두 번째 앱)가 5초 넘게 쓰기 락을 쥐면 `database is locked` 가 호출 결과 저장에서 난다. `open()` 에 `PRAGMA busy_timeout = 30000` 한 줄을 더한다. 호출 결과 저장이 그래도 실패하면 그 호출은 인프라 탓 중단으로 처리한다(판정 행이 안 적혔으니 다음에 그 호출만 다시 돈다).
- WAL 은 그대로다. 연결이 하나라 읽는 쪽이 체크포인트를 막지 않는다.

#### 3.14.4 데이터 디렉터리 잠금

지금은 **잠금이 없다.** 같은 데이터 디렉터리로 앱이 둘 뜨면(HEAXHub 재배포에서 옛 인스턴스가 덜 내려간 사이, 또는 손으로 `uvicorn` 을 한 번 더 띄운 경우) 양쪽 러너가 같은 원장을 돈다. 패널에서는 새 프로세스의 `recover_running_panels` 가 **옛 프로세스가 돌리고 있는** 패널을 `error('restart')` 로 닫는다. 셀에서는 같은 전문가를 두 워커가 집지는 못하지만(선점 UPDATE 가 막는다) 새 프로세스의 복구가 옛 프로세스의 선점을 지워 같은 호출이 두 번 나간다.

방어를 둘 둔다.

1. **러너 단일 인스턴스 잠금.** `$DATA_DIR/runner.lock` 을 열어 `fcntl.flock(LOCK_EX | LOCK_NB)` 를 쥔 프로세스만 러너 루프를 돈다. 못 쥐면 REST 는 정상으로 서고(헬스체크가 깨지지 않는다) 루프는 틱마다 다시 시도한다. **쥔 직후에** 재기동 복구를 돌린다(지금은 `start()` 가 무조건 돌린다). 잠금은 프로세스가 죽으면 커널이 푼다 — 낡은 잠금 파일을 치울 일이 없다. 파이썬이 여는 fd 는 기본이 상속 불가라 자식 프로세스가 물고 남지 않는다. 헬스 경고에 `runner_lock_held` 를 더한다.
2. **선점 id 대조**(§3.7.7). 잠금이 뚫려도(파일시스템이 flock 을 제대로 안 지키는 경우) 늦게 온 결과가 덮어쓰지 못한다.

이 잠금은 패널 러너에도 똑같이 필요한 것이라 소유가 WP5 와 겹친다. §7 에 적는다.

---

## 4. 커밋 단위로 쪼갠 작업 순서

각 걸음은 **그 자체로 시험이 초록**이고 앞 걸음만 필요로 한다. 걸음 0 은 문서다 — 시작 전에 `HWAXRisk/checklist.md` · `context-notes.md` 에 이 설계의 결정(D-번호)과 체크리스트를 옮긴다. 걸음마다 끝에 `cd backend && .venv/bin/python -m pytest -q` 전체를 돌린다.

| # | 커밋 | 선행 | 바뀌는 파일 | 검증 |
|---|---|---|---|---|
| 1 | `feat(store): 검토 원장 표 5개` | WP5a 의 버전 번호(통합 v3 에 싣는다면 그 커밋) | `risk_store.py`(DDL, `busy_timeout`) · `export.py`(`LOCAL_ONLY_TABLES`, `_SINCE_COLS`) · `routes.py`(`TRANSFER_DERIVED`, `PURGE_BLANK_SQL`) · `tests/test_store.py` · `tests/test_export_import.py` | 빈 DB 와 옛 판 DB 양쪽에서 마이그레이션. 새 표 · 열 · 인덱스 존재. 반출 왕복에서 `rr_card_packs` 가 빠지고 나머지 넷이 실린다. 이양 · 폐기 시험에 새 표 행을 심어 owner 가 옮겨지고 원문이 비는지 본다 |
| 2 | `feat(runner): 러너 단일 인스턴스 잠금` | — | `main.py` · `runner.py` · `tests/test_boot.py` | 같은 디렉터리로 러너 둘을 세워 하나만 틱을 돈다. 첫째를 닫으면 둘째가 잠금을 쥐고 **그때** 복구가 돈다. 잠금을 못 쥔 쪽의 `/api/health` 는 200 이고 `warnings` 에 `runner_lock_held` 가 있다 |
| 3 | `fix(jobs): 패널 경로가 패널 잡만 본다` | `rr_jobs.mode` 열(WP5a) | `runner.py`(`claim_next_job` · `recover_running_panels` · `create_job`) · `routes.py`(`coverage_payload`) · `brief.py`(메모 조회) · `tests/test_runner.py` | `mode='reviews'` 잡을 심고 `claim_next_job` 이 None 을 돌려주는지, 재기동 복구가 그 잡을 건드리지 않는지, 진행판의 `job` 이 패널 잡인지 본다 |
| 4 | `feat(cardpack): 팩 확인 · 동결 · 꺼내기` | 1 | `cardpack.py`(신규) · `tests/test_cardpack.py`(신규) · `tests/fixtures/card_review/pack_*.json`(WP3a 와 **같은 픽스처**) | §5.1 의 묶음 시험 전부 |
| 5 | `feat(verify): 받은 행의 회계 · 재대조 · 등급 · 표본` | 4 | `review_verify.py`(신규) · `common.py`(`parse_ref`) · `narrative.py`(`SpecContext` · `_resolve_one` · `canonical_text_for` · `resolve_cites` · `evidence_grade_from_cites` · `review_scope`) · `tests/test_review_verify.py`(신규) · `tests/test_atoms.py` · `tests/test_common.py` | §5.1 의 검증 시험. `card_pack=None` 일 때 기존 시험이 한 줄도 안 바뀌고 통과한다 |
| 6 | `feat(cells): 격자 · 상태기계 · 선점 · 정산 · 복구` | 1 · 5 · WP2 의 `rr_units` · `planner.review_order` | `review_cells.py`(신규) · `planner.py`(`close_review_seat`, `ALLOWED_TRANSITIONS`) · `tests/test_review_cells.py`(신규) · `tests/test_planner.py` | §5.1 의 상태기계 · 불변식 시험 |
| 7 | `feat(engine): PortalReviewEngine — 대화 없이 card-review 넷을 부른다` | — | `runner.py`(`ReviewEngine` · `EngineRejected`) · `engine_client.py` · `config.py`(검토 손잡이 · 여유) · `main.py`(사슬 확인) · `tests/test_engine_client.py` · `tests/fixtures/sse/review_*.sse` | `httpx.MockTransport` 로 §3.6.2 표의 줄을 하나씩. **`/agent/conversations` 로 가는 요청이 0건**임을 단언한다 |
| 8 | `feat(review): review_loop — 잡 · 전문가 세션 · 차단기 · 진행 신호` | 3 · 6 · 7 · WP2 의 `units.*` · `unit_signals.for_cell` | `review_runner.py`(신규) · `runner.py`(`_LOOPS` · `_review_tick` · `start`) · `main.py`(엔진 주입) · `tests/test_review_runner.py`(신규) | §5.2 의 통합 시험 |
| 9 | `feat(review): 검토 finding 승격 · 의견 행 · 원장 마감` | 5 · 6 · WP4 의 `rr_findings` 네 열 | `expert_report.py`(`build_findings`) · `review_runner.py`(`finalize_expert`) · `metrics.py`(`panel_models`) · `tests/test_review_findings.py`(신규) · `tests/test_persist_panel.py` | §5.1 의 승격 시험. 등록부의 지지 수 식은 이 걸음에서 고치지 않는다(WP4) — 여기서는 내 finding 이 `raised_by` 한 명 · `agent_key` · `unit_id` 를 갖는지만 단언한다 |
| 10 | `feat(report): 전문가별 보고서 조립` | 9 | `expert_report.py`(`build_report` · `load_report` · `render_report_md` · `summary_md`) · `tests/test_expert_report.py`(신규) | 같은 원장에서 두 번 조립한 바이트가 같다. 점검표 행 수 == 실효 판정 행 수. `summary_md` ≤ 1,500자 |
| 11 | `feat(api): 셀 · 전문가 보고서 REST 와 MCP 도구 둘` | 8 · 10 | `routes.py` · `mcp_server.py` · `.portal/manifest.yaml`(도구 수 · `launch.env`) · `tests/test_mcp_tools.py` · `tests/test_no_write_tools.py` · `tests/test_p6_routes.py` | 응답 필드가 §3.12 와 한 글자도 다르지 않은지 스냅샷 시험. 남의 타깃은 404 · `not_visible` |
| 12 | `docs: 검토 흐름 운영 문서` | 전부 | `HWAXPortal/docs/design-risk-review/`(이 설계의 정착본) · `HWAXRisk/README.md` · `context-notes.md` | 문서의 손잡이 표가 `config.py` 와 같은지 눈으로 대조 |

걸음 2 · 3 · 7 은 다른 걸음과 독립이라 먼저 내보낼 수 있다. 걸음 5 의 `narrative.py` 변경은 WP1 이 같은 함수(`resolve_cites` 719 · 730, `persist_panel_result` 의 cycle)를 고치므로 **WP1 뒤에** 올린다. 걸음 4~8 은 서버(WP3a)가 뜨기 전에도 가짜 엔진으로 끝낼 수 있다 — 실주행(§5.4)만 서버와 포털 중계를 기다린다.

리스크 앱은 HEAXHub SIF 로 뜬다. 커밋을 push 해도 떠 있는 인스턴스는 바뀌지 않는다 — 실주행 전에 인스턴스를 내리고 다시 올린 뒤 **게이트웨이 실호출로** 새 도구(`risk_get_cells`)가 보이는지 확인한다(소스가 아니라 `tools/list` 다).

---

## 5. 시험

### 5.1 단위 시험(네트워크 없음)

**카드 묶음(`test_cardpack.py`)**

- 픽스처는 WP3a 의 팩 응답 표본을 **두 리포가 같은 파일로** 쓴다(지어낸 카드다 — 사내 카드 원문을 리포에 넣지 않는다). 한쪽만 고치면 다른 쪽 시험이 깨지게 해시를 시험에 적는다.
- `check_pack` — 온전한 팩은 빈 목록. 별칭 중복 · `record_id` 중복 · `text_sha` 불일치 · 개수 불일치 · `agent_key` 불일치를 하나씩 심어 각각 짚는지 본다.
- 문제가 있는 팩은 `rr_card_packs` 에 아무것도 남기지 않는다.
- 같은 팩을 두 번 얼려도 행은 하나다. 다른 타깃이 같은 `pack_hash` 를 가리켜도 행은 하나다.
- `cards_for` 가 돌려준 항목이 팩의 항목과 바이트로 같다(키를 빼거나 순서를 바꾸지 않는다).
- `cards = []` 는 `empty`, 404 는 `error('agent_not_found')`, 502 · 통신 실패는 `error` 다(**`empty` 가 아니다**).
- `card_text` 가 절 `text` 를 줄바꿈으로 이은 것과 같다.

**검증(`test_review_verify.py`)**

- 실은 별칭이 `K01..K08` 인데 결과의 `v` 행이 `K01..K06` + `K13` 이면 `missing=[K07,K08]` 이고 K13 행은 `dropped` 다. 서버가 `missing: []` 라고 했어도 그렇다.
- 같은 별칭 두 번 → 첫 행만 쓴다. 행의 `record_id` 가 팩의 것과 다르면 버린다.
- 카드 본문 `**압축률 20~30%**` 에 대해 `압축률 20~30%` 인용이 통과한다. 줄바꿈이 하나 다른 인용도 통과한다. 14자 인용과 원문에 없는 문구는 `quote_ok=0` 이다.
- 다른 카드의 문구를 가져다 쓴 인용은 `quote_ok=0` 이다(그 카드의 글에만 댄다).
- 서버가 `checks.quote='ok'` 인데 앱의 재대조가 0 이면 `check_disagree=1` 이고 `quote_ok=0` 이 남는다.
- `nq` 파리티 — WP3a 와 같은 입출력 쌍 표(픽스처)를 통과한다.
- 되돌아온 `refs` 에 그 단위에 없는 참조가 있으면 `refs_ok=0` 이다.
- 등급 표 세 줄을 각각.
- `sample_score` — 같은 인자면 같은 값, 인자 순서를 바꾸면 다른 값, 1만 개 표본의 평균이 0.5 ± 0.02 다.
- `effective_rows` 표 다섯 줄을 각각.
- 훑기 회계 — 단위 하나가 답에 없으면 `error`, 카드 하나가 어느 줄에도 없으면 `cards_unseen` 에 든다. 묶음 둘의 답이 `no` 와 `maybe` 면 `maybe` 다. `stamp` 가 선 쪽의 `no` 는 `stamp` 다.
- `narrative` — `card_pack` 을 준 `SpecContext` 에서 묶음 밖 카드는 `not_in_pack` 으로 dangling, `card_scope` 밖은 `not_in_scope`, heuristic 카드 인용만 있는 finding 은 경험칙, 출처 있는 fact 카드는 문헌·규격이다. `number_corpus` 를 주면 '15' 가 '0.15' 에 걸리지 않는다. `card_pack=None` · `number_corpus=None` 이면 `test_atoms.py` 의 기존 단언이 그대로다.

**셀 · 원장(`test_review_cells.py`)**

- 격자 — 셀 수 == 로스터 수 × 검토 대상 단위 수. 두 번 불러도 같다. 단위가 재빌드로 사라지면 그 단위의 열린 셀은 지워지고 종결 셀은 남되 집계에서 빠진다.
- 허용 전이 표의 모든 줄이 통과하고, 표에 없는 전이(`reviewed → na_irrelevant`, `pending → no_input` 등)는 예외다.
- 선점 — 두 스레드가 같은 전문가를 동시에 집으면 하나만 얻는다.
- 선점 id — 복구가 선점을 지운 뒤 옛 `claim_id` 로 온 `write_call_result` 는 0행이고 원장이 안 바뀐다.
- 인프라 탓 중단 → `attempts` 그대로 · `infra_retries+1` · `retry_at` 이 미래. 내용 탓 → `attempts+1`. 한도에서 `failed`.
- 재기동 복구 — `running` 셀 · 전문가가 `pending` · `planned` 로, `attempts` 는 그대로, 이미 적힌 판정 행은 남는다. 검토 잡은 `queued` 다(`paused` 가 아니다).
- 분류표의 네 줄을 각각. `route_det='blind'` 인데 훑기가 `no` 인 셀이 `na_irrelevant` 가 **되지 않는다**. `for_cell` 이 예외를 내면 `blind` 다.
- 입력 결손 길의 표 네 줄을 각각.
- 정산 — `cards_judged < cards_expected` 면 `reviewed` 가 못 된다. 절단이 남은 호출이 있으면 못 된다. 카드 밖 호출이 안 끝났으면 못 된다.
- `close_review_seat` — pending → done 이 되고, 패널이 이미 닫은 행은 안 바뀌고, 이 검토가 닫은 `done_weak` 는 `done` 으로 다시 적힌다. 검토 중인 타깃에서 `check_invariants` 가 빈 목록이다.
- `review_invariants` 가 온전한 원장에서 빈 목록이고, 일부러 깬 원장(실효 행 둘, `claim_id` 없는 running, 신호가 `hit` 인 `na_irrelevant`)에서 그 줄을 짚는다.

**승격 · 지지(`test_registry.py` · `test_persist_panel.py`)**

- 같은 전문가의 카드 3장이 같은 변경 · 같은 메커니즘을 가리키면 finding 은 하나이고 `cards[]` 가 3건이다.
- 전문가 12명이 같은 `cluster_key` 를 올리면 그 finding 12건의 `raised_by` 가 서로 다른 한 명씩이고 `agent_key` · `unit_id` 가 채워져 있다(WP4 의 병합이 이것으로 `support_experts = 12` 를 낸다 — 그 단언은 WP4 의 시험이 한다). 한 전문가가 단위 셋에서 같은 클러스터를 올리면 finding 은 3건이고 `raised_by` 는 같은 한 명이다.
- `claim_uid` 가 스키마 패턴에 맞고, finding 하나가 빠진 뒤 다시 마감해도 **남은 finding 의 id 가 같다**. 개선은 `#G` 다.
- `hold` 정책에서 검토의 `FAIL` 이 등록부에 WARNING · 중대로 들어가고 verdict 후보가 `no-go` 가 아니다. `judgement_claimed` 에 `FAIL` 이 남는다. `direct` 에서 조건을 다 채운 것만 FAIL 이다.
- 카드 밖 `src='exp'` 는 변경 줄 참조가 통과해도 경험칙이다. 긴 문서 발췌는 `cites` 에 안 들어가고 dangling 이 0 이다.
- 의견 행 — `seat_opinion.v1` 스키마 검증을 통과하고 cycle 이 501 이다. 같은 타깃 · 같은 전문가에 패널 의견(cycle 1)이 이미 있어도 INSERT 가 된다.

### 5.2 통합 시험(가짜 엔진)

`tests/test_review_runner.py` 에 `FakeReviewEngine` 을 둔다(`FakePanelEngine` 선례 — test_runner_panel.py:81). `limits` · `pack` · `plan` · `run` 넷을 다 갖고, `run` 은 받은 요청의 카드 본문에서 **실제 부분 문자열을 잘라** `cq` 로, 받은 줄 별칭을 `l` 로 돌려주므로 재대조가 진짜로 통과한다. 결함 주입 스위치가 있다 — 카드 빼먹기 · 모르는 별칭 · 지어낸 인용 · `checks.quote` 거짓말 · 절단 · `context_overflow` · `over_budget` · 429 N회 · `error{infra:true}` · 중간 절단 · 호출 지연 · 도장찍기 훑기.

- **끝까지.** 전문가 6명(영역 3 × 순위 2, 하나는 입력 결손) × 단위 4개. 잡이 `completed` 로 가고, 셀이 전부 종결이고, 호출 원장의 `ok` 수가 계획과 같고, 전문가 6명에게 보고서 · 의견 · 원장 종결이 있고, 등록부에 행이 있다.
- **대화를 만들지 않는다.** 엔진이 받은 `run` 요청 수 == 호출 원장 행 수이고 대화 생성 경로 호출이 0 이다.
- **패널 규칙에 닿지 않는다.** `risk_daily_panel_cap=1` 로 두고 셀 30개가 다 돈다. `rr_panels` 행이 0 이다. 같은 타깃에서 워커 넷이 동시에 돈다(가짜 엔진이 동시 진입 수의 최댓값을 센다 — 2 이상이어야 한다).
- **묶음 순서.** 한 전문가의 `verdict · fwd` 요청이 묶음 먼저 · 단위 나중 순으로 나간다.
- **멱등.** 끝난 잡 위에 같은 범위의 잡을 다시 만들면 `run` 호출이 0 이고 원장이 바이트로 같다. 셀 하나를 `force` 로 다시 열고 돌리면 그 셀의 호출만 나가고 판정 행 수가 같다.
- **재기동.** 호출 중에 러너를 세우고(가짜 엔진이 막고 있는 동안) 새 러너를 띄운다. `attempts` 가 0 이고, 끊긴 호출만 다시 나가고, 잡이 사람 손 없이 `completed` 까지 간다.
- **차단기.** 가짜 엔진이 연속 5회 `infra:true` → 잡이 `paused` · `hold_code='breaker'`. 셀의 `attempts` 는 전부 0 이다. 시계를 백오프만큼 밀면 `queued` 로 돌아오고, 워커가 하나만 뜨고, 성공 하나 뒤 전부 뜬다.
- **내용 탓 급등.** 절반 넘게 `no_rows` → 보류 코드 `content_fail_rate` 로 멈추고 시계를 밀어도 스스로 돌아오지 않는다.
- **줄여서 한 번 더.** `context_overflow` 에 묶음이 반으로 갈려 다시 나가고 `attempts` 가 안 오른다. `limits_rev` 가 바뀌었으면 계획을 다시 받는다.
- **취소 · 정지.** 도는 중에 `cancel_job` → 프레임 하나 안에 스트림이 닫히고 셀이 `pending`, 잡이 `cancelled` 다. `pause_job` 뒤 `resume_job` 이면 이어 돈다.
- **훑기.** 가짜 신호가 `miss` 를 주고 훑기가 `no` 인 셀이 `na_irrelevant` 가 된다. 도장찍기 훑기는 아무 셀도 `na_irrelevant` 로 만들지 못한다. Tier A 의 놓침률이 임계를 넘으면 나머지 전문가가 훑기를 건너뛴다.
- **다시 열기.** `reopen(via='audit')` 로 연 `na_irrelevant` 셀이 보통 셀처럼 대조되고, 가짜 엔진이 `applies='yes'` 를 주면 `audit_result='miss'`, 아니면 `clean` 이다. 어느 쪽이든 `reviewed` 로 남는다.
- **제공자.** 가짜 제공자를 등록하고 `mode='post'` 잡을 심으면 그 일이 같은 세마포어 아래에서 돈다(동시 수의 최댓값이 `HWAXRISK_REVIEW_CONCURRENCY` 를 넘지 않는다). 인프라 탓 실패에 `fail(charge=False)` 가 불린다.
- **카드 0장 전문가.** 훑기 없이 전 단위에 카드 밖 호출이 검색과 함께 나간다. `reviewed`(`cards_expected=0`, `basis='search_only'`), 원장 `done_weak`, 보고서에 표기.
- **묶음 불통.** 한 전문가의 `pack` 만 502 → 그 전문가는 `blocked`, 나머지는 끝까지. 전원 502 → 보류 코드 `pack_unavailable`.
- **두 프로세스.** 임시 디렉터리 하나에 `RiskStore` 둘을 열고 러너 둘을 세운다. 호출이 한 번씩만 나간다(잠금). 잠금을 꺼도(시험용 스위치) 판정 행이 겹쳐 쓰이지 않는다(선점 id).

**계약 시험(리포를 가로지른다).** 가짜 엔진이 진짜 서버와 갈리면 위 시험이 전부 초록인 채 실주행이 깨진다. 그래서 요청 · 응답의 표본(`tests/fixtures/card_review/*.json` — 종류별 요청 1건 · `result` 1건 · `error` 1건)을 WP3a 리포의 같은 이름 파일과 **바이트로 같게** 두고, 양쪽 시험이 그 파일을 읽는다. 앱 쪽은 `build_request` 의 산출이 요청 표본과 키 집합이 같은지, `accept_rows` 가 `result` 표본을 풀어 기대 행을 내는지를 본다. 포털 리포의 가드 시험(리포 셋을 가로지르는 선례가 있다 — `test_cluster_naming.py`)에 두 파일의 해시 일치를 더한다.

### 5.3 dev 에 여러 건짜리 diff 가 없다는 것을 어떻게 넘나

이 꾸러미는 **단위를 읽기만** 한다. 그래서 시험 재료를 세 층으로 만든다.

1. **단위 직접 심기(위 5.1 · 5.2 전부).** 시험이 `rr_units` 행과 로스터를 직접 넣는다. 단위의 변경 줄은 `tests/fixtures/diff_pairs/` 의 여섯 쌍(추가 · 종류 · 재질 · 이동 · 삭제 · 두께)에서 실제 `compute_diff` 가 낸 이벤트 글을 가져다 쓴다 — 줄 모양과 참조 문법이 진짜다.
2. **합성 다건 diff(WP2 와 같이 쓰는 픽스처).** WP2 가 합성 쌍을 두 스냅샷에 얼려 실제 `create_diff` → 단위 저장까지 가는 시험을 둔다(그 문서 5 절). 그 끝에 격자 → 가짜 엔진 → 마감을 잇는 시험 하나를 내가 더한다.
3. **dev 실주행용 과제.** 위 합성 쌍으로 만든 과제를 `POST /api/import` 로 dev 에 넣는다. `corpus_excluded=1` · `excluded_reason='fixture'` 로 표시해 학습 · 통계 · 회수에서 빠지게 한다(그 열이 이미 있다 — risk_store.py:31~32).

### 5.4 실주행

| 단계 | 어디서 | 무엇을 | 통과 기준 |
|---|---|---|---|
| A 형식 | dev(로컬 모델은 7B · 창 16K 로 추정) | 픽스처 과제, Tier A 3명 × 단위 2개 | 호출이 포털 중계를 지나 서버에 닿는다. `limits` 가 그 박스의 창으로 묶음을 1~2장으로 낸다. 판정 행 수 == 카드 수. 포털 대화 목록에 새 대화가 없다. 호출 중 `apptainer instance stop` 뒤 다시 올리면 잡이 스스로 이어 돈다. **판정의 질은 보지 않는다** |
| B 파일럿 | cae00(GLM) | 실제 타깃 하나, Tier A 15명 × 단위 2개 | 호출당 시간 · 실제 토큰(`meta.usage` 로 자/토큰 비) · 절단 0 · 보충 횟수 · 카드 인용 재대조율 · `check_disagree` 0 을 잰다. 이 값으로 §3.14 의 벽시계를 고쳐 적는다 |
| C K 정하기 | cae00 | 같은 (전문가, 단위) 20쌍에 서버 `CARD_REVIEW_K` = 1 · 4 · 8 · 15 | K=1 을 기준으로 K 별 판정 일치율 · 빠진 카드 수 · 위치별 `OK` 비율. 일치율이 급히 꺾이는 직전 값을 쓴다(02-reliability 의 파일럿 — WP3a 와 같이 한다) |
| D 범위 실행 | cae00 | Tier A 범위(`scope.tier='A'`) 잡 하나를 끝까지 | 잡이 `completed`. `review_invariants` 빈 목록. Tier A 의 훑기 놓침률이 나온다. 전문가 보고서를 사람이 3편 읽고 인용 10개를 카드 원문과 손으로 대조한다 |
| E 전원 | cae00 | D 가 통과한 타깃에 범위를 넓힌다 | 차단기 · 재기동 · 배포가 낀 며칠을 지나 끝난다 |

B 를 건너뛰고 E 로 가지 않는다. 호출 시간이 추정의 3배면 E 는 3주다.

---

## 6. 위험과 완화

| # | 깨질 수 있는 경우 | 무슨 일이 나나 | 완화 |
|---|---|---|---|
| 1 | **결정적 신호(WP2)가 늦거나 대부분 `blind` 다** | r = 1 이고 타깃 하나가 일주일(§3.14.1) | 기본이 안전한 쪽(전수)이다. 범위(`scope`)로 Tier A → B → 전원 순으로 끊어 돌린다. 신호가 붙으면 남은 셀부터 줄어든다 |
| 2 | 훑기가 틀린 '해당 없음' 을 낸다 | 본 적 없는 칸이 채워진 것으로 읽힌다 | 문이 하나(신호 `miss` **그리고** 전 묶음 `no` **그리고** 도장찍기 아님 **그리고** 강제 사유 없음). Tier A 전수 대조로 초반에 놓침률을 재고 넘으면 필터를 끈다. 끝에 WP4 의 표본 재검토가 다시 잰다. `na_irrelevant` 는 원장에서 `abstain` 으로 올라가 '검토함' 과 섞이지 않는다 |
| 3 | `OK` 가 틀렸다 | 코드가 대조할 원문이 없어 조용하다 | 카드 인용과 변경 줄 참조를 강제하고, 인용이 재대조를 못 넘은 음성은 전부 · 나머지는 10% 를 순서를 바꿔 다시 묻고, 어긋난 것은 단독으로 가른다. 뒤집힘률을 보고서와 진행판에 싣는다. **이 위험은 줄일 뿐 없애지 못한다** |
| 4 | 가짜 엔진과 진짜 서버의 계약이 갈린다 | 시험은 초록인데 실주행의 첫 호출이 422 거나, 더 나쁘게는 행이 조용히 버려진다 | 요청 · 응답 표본을 두 리포가 같은 파일로 쓰고 해시를 가드 시험이 본다(§5.2). 앱이 모르는 `t` 의 행을 받으면 버리되 `dropped` 에 세고 0 이 아니면 진행판에 띄운다. `invalid_request` 는 잡을 멈춘다(셀을 태우지 않는다) |
| 5 | 두 리포의 인용 정규화가 갈린다 | 서버는 통과시킨 인용을 앱이 불일치로(또는 반대로) 본다 | `check_disagree` 로 드러난다. 0 이 아니면 진행판 품질 칸에 뜬다. 파리티 픽스처가 평소에 잡는다 |
| 6 | 프롬프트가 창을 넘는다 | 서버가 422 `over_budget` 또는 `context_overflow` 로 거절한다 | 계획을 서버가 짠다(앱이 추정하지 않는다). 그래도 나면 한도를 다시 읽고, 판이 같으면 묶음을 반으로 나눈다. 단위가 상한을 넘으면 `failed('unit_oversize')` 로 드러낸다(자르지 않는다) |
| 7 | 출력이 `max_tokens` 에서 잘린다 | 뒤쪽 카드의 판정이 없다 | 서버가 줄 단위로 받아 닫힌 행을 살리고 `quality.truncated` 로 알린다. 앱은 빠진 카드만 다시 묻는다. 절단이 남은 셀은 `reviewed` 가 못 된다 |
| 8 | 앱 재기동 · 배포가 도는 중에 온다 | 돌던 호출 W 건이 끊긴다 | 차감 없이 `pending`, 잡은 스스로 이어 돈다. 이미 적힌 판정은 다시 묻지 않는다 |
| 9 | 에이전트 서버 · 포털 재기동(update-all) | 호출이 줄줄이 끊긴다 | 인프라 탓이라 차감이 없다. 5회 연속이면 차단기가 잡을 멈추고 60초 뒤 하나로 찔러 본다. 서버의 `card_review_active` 는 `delib_active` 와 다른 칸이라 update-all 이 기다리지 않고 재기동한다 — 그 편이 낫다(배포를 며칠 붙들지 않는다) |
| 10 | 심의가 길게 돈다 | 서버 관문이 2 로 내려가 검토가 반 속도가 된다 | 의도한 양보다. 진행판의 `server.limit` 과 워커의 `last_step='queued'` 로 보인다. 앱 쪽 호출 벽시계(18,000초)가 서버의 자리 대기 상한(3,600초)보다 커서 줄 선 호출이 앱에서 먼저 끊기지 않는다 |
| 11 | 두 프로세스가 같은 DB 로 뜬다 | 같은 호출이 두 번 나가고 복구가 서로를 지운다 | 러너 잠금 + 선점 id 대조(§3.14.4) |
| 12 | 워커가 호출 중에 조용히 멈춘다(상대가 끊었다는 말 없이) | 그 전문가가 `running` 으로 남는다 | 침묵 한도(54,000초)가 끊는다. 진행 신호의 `frame_idle_s` 가 그 전에 보인다. 재기동하면 복구된다 |
| 13 | 한 전문가의 셀 일부만 실패 | 보고서가 끝없이 안 나온다 | 열린 셀이 0 이면 실패가 있어도 마감한다(`partial`). 실패 셀은 보고서 '보지 못한 것' 에 사유와 함께 남고, 다시 돌리면 보고서가 판을 올려 다시 나온다 |
| 14 | 다시 마감하며 finding 이 사라진다(단독 재질의로 뒤집혔다 · 단위가 재빌드로 사라졌다) | 그 finding 에 붙은 라벨 · 인용이 고아가 된다 | id 를 내용에서 뽑아 남은 것은 안 바뀐다. 사라진 `claim_uid` 를 `stats_json.dropped_findings` 에 남긴다. 라벨은 타깃이 닫힌 뒤에 붙는 것이라 실제로 겹칠 일은 드물다 |
| 15 | 카드가 심사 도중 바뀐다 | 인용 대조가 거짓 불일치를 낸다 | 타깃 안에서는 얼린 묶음만 쓴다. 바뀌었는지는 사람이 물을 때 알린다 |
| 16 | 단위가 심사 도중 다시 만들어진다(WP2 재빌드) | 셀이 없는 단위 · 단위가 없는 셀 | `plan_cells` 가 다시 맞춘다(§3.7.2). 내용이 같은 단위는 id 가 같아 그대로 간다. 재빌드는 살아 있는 검토 잡이 있으면 WP2 쪽에서 409 로 막아 달라고 청한다(§7.1) |
| 17 | 카드 0장 · 단위 0개 · 로스터 0명 | 빈 잡 | 단위 0 은 409 `units_absent`. 로스터 0 은 격자가 0 이라 잡이 곧 `completed`(셀 0)이고 응답 `cells_planned=0` 으로 드러난다. 카드 0장은 §3.5.5 |
| 18 | 빈 diff(자기 자신과 비교 — dev 의 실물) | 단위가 0 이거나 '변경 없음' 단위 하나 | WP2 의 빌드가 `empty` 면 409 다. 단위를 하나 내면 그대로 돈다(전문가마다 훑기 없이 대조 1셀) |
| 19 | 옛 타깃(패널이 이미 돈 것) | 의견 유일 제약 · 원장 종결 행과 부딪힌다 | 검토 의견은 500대 cycle 이라 안 부딪힌다. 종결된 원장 행은 건드리지 않는다. 그 타깃의 등록부 `support` 는 다음 병합에서 새 정의로 다시 계산된다 — 사람이 닫은 행의 재제기 판정은 지지 축을 건너뛴다 |
| 20 | 박스 차이 — cae00 은 리포가 `~/Projects`, 모델 · 창 크기 · `max_tokens` 가 dev 와 다르다 | dev 에서 맞춘 묶음이 cae00 에서 넘치거나 남는다 | 경로를 코드에 적지 않는다(전부 `$DATA_DIR` 기준). 묶음 계획을 그 박스의 서버에서 받는다. 손잡이는 매니페스트 `launch.env` 에만 적는다 |
| 21 | 박스 간 이관(export → import) | 받는 쪽에 카드 묶음이 없다 | 판정 행에 인용과 대조 결과가 이미 있고 보고서는 얼린 JSON 이라 읽는 데는 지장이 없다. 다시 대조하려면 그 박스에서 묶음을 다시 받는다 — `pack_hash` 가 같으면 같은 카드다. 묶음이 없으면 화면에 '카드 묶음 미보유(이관본)' 로 적는다 |
| 22 | 등록부 병합이 길어져 화면이 멈춘다 | 병합 동안 REST 가 기다린다 | 300초에 한 번으로 묶는다. finding 이 1만 건을 넘는 타깃에서 1회 시간을 재고(실주행 D) 3초를 넘으면 병합을 '바뀐 클러스터만' 으로 좁히는 일을 따로 연다 |
| 23 | 택소노미 밖 메커니즘이 한 행으로 뭉친다 | cam · sh · rf 의 서로 다른 지적이 '분류 밖' 하나로 보인다 | 내 쪽은 `mechanism_free` 원문을 finding 마다 남긴다. 뭉침을 푸는 일(미분류의 세부 키 · 코드 추가)은 WP4 다 |
| 24 | 카드 근거 finding 의 메커니즘 칸이 빈다(서버의 단독 재질의 행에 `mech` 가 없다) | 카드 근거 finding 이 전부 `unclassified` 가 되어 subject · change_kind 만으로 뭉친다 | WP3a 에 그 칸을 청한다(§7.1). 오기 전에는 뭉친 채로 두되 보고서에는 카드별로 풀어 보인다. 카드 밖 줄은 `mech` 가 있어 영향이 없다 |
| 25 | 잡 종류 거르기를 한 군데 빠뜨린다 | 패널 루프가 검토 잡을 5초마다 집었다 놓는다 | 걸음 3 의 시험이 그 자리를 잠근다. 덧붙여 `claim_next_job` 이 집은 잡의 `mode` 가 패널 잡이 아니면 예외로 드러낸다 |
| 26 | 포털 PAT 가 호출 도중 만료 | 401 로 잡이 선다 | 호출마다 여유(22,200초)를 보고 자격을 고른다. 모자라면 서비스 계정으로 내려가고 그 사유를 잡 `error` 에 적는다(패널과 같은 문구 길) |
| 27 | 카드 원문이 리스크 앱 DB 와 그 백업에 복제된다 | 지식카드가 AIDataHub 밖 한 곳에 더 생긴다 | 반출(export)에서는 뺀다. DB 백업에는 실린다 — 사용자 결정 항목이다(§8) |
| 28 | 변경 줄 · 카드 본문에 지시처럼 보이는 문장이 있다(저장형 주입) | 판정 행이 틀어진다 | 도구가 없고 별칭이 닫힌 집합이라 피해가 판정 행에 갇힌다(WP3a). 서버가 알린 의심 줄(`extras.inj`)을 셀에 남기고, 그 셀에서 나온 finding 은 회수 후보에서 뺀다(`recall_eligible = 0`) |

---

## 7. 다른 꾸러미와의 계약

### 7.1 내가 받는 것

| 누구에게서 | 무엇 | 모양 |
|---|---|---|
| **WP2** | 검토 단위 표 | `rr_units(target_key, unit_id, reviewable, seq, kind, scope_key, title, one_liner, refs_json, content_hash, summary_hash, pack_hash, pack_status, …)` · `rr_unit_builds` 의 활성 빌드. `unit_id` 는 내용에서 나온 결정론 값이다 |
| WP2 | 단위 읽기 | `units.manifest` · `units.packets(store, target_key, max_chars=…)`(훑기 목록) · `units.review_payload(store, target_key, unit_id, agent_key)`(카드 대조용) · `units.ref_index` · `units.roster_query`(검색어 구절) |
| WP2 | **줄 목록** | WP3a 의 요청은 단위를 `lines[{ref, text}]` · `evidence[{ref, text}]` 로 받는다. `review_payload` 는 지금 `summary_text` · `pack_text`(글 한 덩이)를 준다. 줄 목록을 같이 달라고 청한다(`review_payload` 에 `lines` · `evidence` 를 더하거나 `get_unit(part='items')` 로). 안 되면 내가 참조 표지로 줄을 가르는 변환을 두지만, 가르는 규칙이 두 곳에 생긴다 |
| WP2 | 결정적 신호 | `unit_signals.for_cell(store, target_key, unit_id, agent_key, *, card_vocab=None, last_check=False) -> {det, forced, hits, blind, miss, values, input_gaps}`. 반환을 셀에 그대로 얼린다 |
| WP2 | 순서 · 입력 결손 | `planner.review_order(store, target_key) -> [{order, agent_key, domain, rank_in_domain, tier, input_gaps}]` · `rr_roster.input_gaps_json` |
| WP2 | 흐름 표지 · 재빌드 가드 | `rr_targets.flow`(새 흐름 값). 살아 있는 검토 잡이 있는 타깃의 단위 재빌드는 409 로 막아 달라고 청한다. 근거 꾸러미는 `unit_pack.ensure` 로 채운다 |
| WP2 | 단위 크기 | 단위 본문이 `limits.verdict.unit_body_max`(WP3a) 안이다. 넘는 단위는 셀이 `failed('unit_oversize')` 가 된다 |
| **WP3a** | 끝점 넷 | `/card-review/limits · pack · plan · run` 과 포털 중계. 요청 · `result` · `error{code, infra, retryable, knob}` 의 모양(그 문서 3.2~3.8) |
| WP3a | 구독이 끊기면 접는다 | `run` 은 분리 태스크가 아니다. 앱이 스트림을 닫으면 LLM 호출을 취소한다. `ping` 은 15초 간격 |
| WP3a | **단독 재질의 행의 `mech`** | `solo` 의 `v` 줄에 메커니즘 코드(`mech` · `mech_free`)를 더해 달라고 청한다. 지금 초안에는 `sev` · `path` · `check` 만 있다. 없으면 카드 근거 finding 이 전부 `unclassified` 로 뭉친다 |
| WP3a | 훑기의 사유 코드(선택) | `u` 줄의 `rel='no'` 에 닫힌 사유 코드를 더하면 WP4 의 표본 층이 선다. 없으면 층 키를 신호의 `miss` 목록으로 쓴다 |
| WP3a | 계약 픽스처 | 요청 · `result` · `error` · 팩 표본과 `_nq` 입출력 표를 두 리포가 같은 파일로 둔다 |
| **WP1** | 원장 밖 좌석의 cycle | `persist_panel_result` 가 원장 밖 좌석에 `NONLEDGER_CYCLE_BASE + panel_no` 를 쓴다. 기준값이 내 `REVIEW_CYCLE_BASE`(500) 보다 크다 |
| WP1 | `resolve_cites` 의 수정 순서 | 인용 공백 정규화 · 수치 토큰 대조를 WP1 이 먼저 고치면 내 걸음 5 는 card 분기와 `number_corpus` 만 얹는다 |
| **WP4** | `rr_findings` 의 네 열 | `unit_id` · `source_kind` · `source_id` · `agent_key`. 내 걸음 9 보다 먼저 있어야 한다 |
| WP4 | 지지 수 식 | `_merge_cluster` 가 제기 전문가 수로 센다(§3.10.4). 실주행 D 전에 있어야 한다 |
| WP4 | 공용 저장 함수(선택) | `narrative.persist_single_findings(...)`. 있으면 내 마감이 그것을 쓴다 |
| **WP5a** | 스키마 | 내 표 다섯을 통합 v3 에 **이 문서의 열로** 싣는다(그 초안은 '소유 꾸러미가 확정한다' 고 적었다). `rr_jobs.mode · hold_code · hold_until · hold_n` |
| WP5a | 러너 잠금 · `busy_timeout` | `runner.lock` 과 `PRAGMA busy_timeout = 30000`(§3.14.3 · §3.14.4 와 같은 내용이 그 문서에 있다 — 한 번만 구현한다. 내 걸음 2 는 WP5a 의 걸음과 같은 커밋이다) |
| WP5a | 비우기 · 밤 창 | 신호를 읽는 함수. 내 루프는 선점 직전과 `should_stop` 에서 그것을 묻는다 |
| WP5a | 매니페스트 | 새 손잡이를 `launch.env` 와 등록 사본에 싣는다 |

### 7.2 내가 주는 것

| 누구에게 | 무엇 | 모양 |
|---|---|---|
| **WP4** | 셀 원장 | `rr_review_cells`(PK `(target_key, unit_id, agent_key)`, `state` 6종). WP4 가 청한 `mechs_json{raised, considered}` · `handoffs_json[{to_domain, note, change_refs}]` 를 열로 둔다. 판정 건수는 `n_fail · n_warning · n_ok · n_na · n_undetermined · n_offcard`, 신호값은 `route_json` 이다 |
| WP4 | 판정 행 | `rr_card_verdicts`(PK 에 `variant` 가 든다 — 한 카드에 `fwd · rev · solo` 가 따로 남는다). 읽을 때는 `is_effective = 1` 을 건다. 낱말은 `applies` + `judgement`(OK · WARNING · FAIL · undetermined · na)다. `OK` 행에도 `refs_json` 이 있다 |
| WP4 | 셀 집계 | `review_cells.review_summary(store, target_key) -> {units, cells{total, by_state, failed_open, failed_disposed}, experts{…}, cards{expected, judged, quote_rate, refs_rate, check_disagree}, sampling{…}}` |
| WP4 | 단위 × 영역 판정 | `review_cells.unit_domain_matrix(store, target_key) -> {unit_id: {domain: {reviewed, na, no_input, failed, n_fail, n_warning, experts[]}}}` |
| WP4 | 다시 열기 · 모집단 | `review_cells.reopen(...)` · `review_cells.na_population(...)` · `audit_result` 열(§3.9.3). 다시 연 셀은 보통 셀처럼 내 루프가 돈다 — 따로 부르는 `run_check` 는 두지 않는다 |
| WP4 | 카드 묶음 | `cardpack.load_for(store, target_key, agent_key) -> {pack_hash, role, cards{alias: …}}` · `review_verify.quote_ok(pack, record_id, quote) -> bool`(그 문서가 `card_packs.load` · `verify_cite` 라 부른 것) |
| WP4 | 전문가 보고서 | `expert_report.load_report(store, target_key, agent_key)` · `render_report_md(...)` · `rr_expert_reports.summary_md` |
| WP4 | 제공자 접점 | `review_runner.WorkProvider` · `register_provider`(§3.7.11). 세마포어 · 자격 · 호출 원장 · 실패 구분 · 차단기를 같이 쓴다 |
| WP4 | 원장 롤업 | `rr_coverage` — `done`(검증 인용 있음) · `done_weak` · `abstain`(`reason='na_all'` 또는 `'no_input:<gap>'`). `panel_id = review_id` 로 '검토가 닫은 행' 을 가린다 |
| WP4 | 카드 인용 검증 | `_panel_scope` 가 좌석의 얼린 묶음을 `card_pack` 으로 싣는다. 쟁점 브리프의 카드 참조는 `card:<record_id>#<절>` 이다 |
| **WP1 · WP4** | 검토 cycle | `REVIEW_CYCLE_BASE = 500`(`500 + rr_coverage.cycle`) |
| **WP5a** | 관측 | `rr_jobs.progress_json`(§3.7.10) · `rr_review_calls`(호출별 시간 · 토큰 · 실패 코드 · `infra`) · `runner.status()` 의 `review_loop` 줄 |
| WP5a | 멈춤 자리 | `should_stop` 과 선점 직전의 물음. 세우면 워커가 다음 호출 경계에서 놓는다. 돌던 호출을 기다릴지는 WP5a 가 정한다(안 기다려도 잃는 것은 W 건이다) |
| **프론트(다른 세션)** | 응답 필드 | §3.12 전부 |

### 7.3 계약 변경 제안과 형제 문서 사이의 차이

**공통 계약 초안에서 바꾸자는 것.**

1. `rr_card_packs` 의 키를 `(agent_key, pack_hash)` 로 한다(내용 주소, `owner_sub` 없음, 반출 제외). 타깃과의 결속 · 묶음 계획은 `rr_expert_reports` 에 둔다. WP3a 는 `(target_key, agent_key)`, WP5a 는 `(owner_sub, pack_hash)` 를 적었다.
2. `rr_expert_reports` 가 (타깃 × 전문가)의 실행 머리(선점 · 묶음 결속 · 훑기 결과)를 겸한다.
3. 표 `rr_review_calls`(호출 원장)를 더한다. WP5a 도 같은 표를 제안했다 — 열은 이 문서의 것을 소유 판으로 낸다(그쪽의 `grid · purpose` 는 WP4 의 단독 호출까지 담으려는 것이라 `kind` 어휘를 넓히면 합쳐진다).
4. 셀 상태는 초안의 6종 그대로다. 실패의 사람 처분과 재시도 대기는 상태가 아니라 열이다. WP5a 초안의 `skipped` · `carried` 는 넣지 않는다.
5. `rr_card_verdicts` 의 키에 변형(`variant`)을 넣고 낱말을 `applies` + `judgement` 로 한다(WP3a 와 같다. WP4 · WP5a 초안은 `verdict(violation · caution · ok …)` 와 변형 없는 키를 적었다).
6. `rr_seat_opinions.cycle` 을 대역으로 나눈다(원장 1~ · 검토 500~ · 원장 밖 좌석은 WP1 · WP4 의 기준값 + panel_no).
7. 참조 문법에 `card:<record_id>#<section_id>` 를 더한다.
8. 검토 finding 은 `panel_id` NULL, `claim_uid = '<review_id>#F<내용에서 나온 수>'` 다(다시 마감해도 id 가 안 바뀐다).

**형제 문서끼리 어긋나 조정이 필요한 것.** 읽은 대로 적는다. 이 문서는 괄호 안의 쪽을 따랐다.

| # | 무엇 | 어긋남 | 이 문서 |
|---|---|---|---|
| 1 | 단위를 엔진에 싣는 모양 | WP2 는 글 한 덩이(`summary_text` · `pack_text`), WP3a 는 줄 목록(`lines[{ref, text}]`) | WP3a(줄 별칭이 있어야 참조가 닫힌 집합이 된다). WP2 에 줄 목록을 청한다 |
| 2 | 원장 밖 좌석의 cycle 기준값 | WP1 은 1000, WP4 는 100000 | 어느 쪽이든 500 보다 크면 된다. 하나로 맞춰야 한다 |
| 3 | `rr_jobs` 의 종류 · 보류 열 | WP4 는 `mode NOT NULL DEFAULT 'panels'` + `chain_json`, WP5a 는 `mode`(NULL 허용) + `stage · hold_code · hold_until · hold_n …` | WP5a 의 열 이름. 패널 잡 판정은 `COALESCE(mode,'panels')` 로 양쪽에 맞게 적었다 |
| 4 | `rr_targets.flow` 의 값 | WP2 는 `'units'`, WP5a 는 `'review_v1'` | 값을 읽지 않고 'NULL · panels 가 아니면 새 흐름' 으로만 본다 |
| 5 | 판정 낱말 · 판정 표의 키 | 위 5번 | WP3a |
| 6 | 입력 결손 두 질문의 답 | WP2 는 `q1.status(answered · no_input)` · `q2.requests[{what, because, card, data_kind}]`, WP3a 는 `q1{impact(yes · no · unknown)}` 줄들 · `q2{item, needs}` 줄들 | WP3a 의 행. 셀 상태로 옮기는 표는 §3.7.4 |
| 7 | '해당 없음' 의 사유 | WP4 의 표본 층은 사유 **코드**, WP3a 의 훑기는 사유 **글** | 코드가 없으므로 신호의 `miss` 목록을 층 키로 내준다. WP3a 에 코드를 청한다(선택) |
| 8 | 서버 관문이 줄을 세우는가 | WP3a 는 스트림을 연 채 최대 3,600초 줄을 세우고 가득 차면 429, WP5a 는 '게이트는 줄을 세우지 않는다 — 곧바로 자리 없음' | 둘 다 받게 짰다(429 → 간격을 두고 다시 묻는다 · `status{queued}` → 기다린다). 다만 호출 벽시계 18,000초는 줄을 세우는 쪽을 전제한 값이다. 줄을 안 세우면 11,400초로 내려도 된다 |
| 9 | 인용 대조를 어디서 하나 | WP3a 는 '서버 한 곳, 앱은 그 결과로 등급만' | 서버의 `checks` 를 받되 앱이 얼린 팩으로 한 번 더 댄다(§3.8.2 의 세 가지 이유). 정규화 규칙은 WP3a 것이 정본이고 파리티 픽스처로 묶는다 |
| 10 | 이중 판정의 기본 | WP3a 는 '첫 실주행은 전량' 권고 | 기본 15% + Tier A 전량, 손잡이로 1.0 까지. 사용자 결정(§8) |
| 11 | '해당 없음' 표본 재검토의 주인 | 공통 뼈대는 3단계(검증)에, WP4 는 자기 표(`rr_cell_audits`)로 | WP4. 나는 다시 열기와 결과 열을 준다 |
| 12 | 셀의 작업 항목 열 이름 | WP5a 초안은 `status · tries · charged · infra_streak · not_before · lease_owner · run_id · tokens_in · tokens_out · llm_calls` | 이 문서는 `state · attempts · infra_retries · retry_at · claim_id · job_id · prompt_tokens · completion_tokens · calls_n`. **뜻은 같다.** 통합 초안이 이름을 굳히면 그대로 따른다(순수 개명이다) |

---

## 8. 사용자가 정해야 하는 것

| # | 정할 것 | 권고 기본값 | 이유 |
|---|---|---|---|
| 1 | 카드 대조의 `FAIL` 하나로 타깃의 판정 후보를 `no-go` 까지 올릴 것인가 | **올리지 않는다**(`hold`). 검토가 등록부에 올리는 판정은 WARNING 까지이고 FAIL 은 쟁점 토의나 사람이 올린다. 전문가 보고서와 판정 행에는 `FAIL` 그대로 보인다 | 검토에는 반대석이 없어 기각이 0 이다. 그대로 올리면 전문가 한 명 · 호출 두 번의 판단으로 타깃 전체가 no-go 후보가 된다. 반대로 `hold` 는 실제 위반이 토의 전까지 등록부에서 '주의' 로 보인다는 값을 치른다 |
| 2 | 공유 LLM 을 며칠 동안 얼마나 내줄 것인가 | **앱 4 · 서버 관문 4(심의가 도는 동안 2)** 로 시작하고 파일럿(§5.4 B)의 호출 시간을 보고 조정한다 | 이 값이 일정을 정한다(§3.14.1 — 단위 8개 · 절반 대조에서 동시 4 면 약 4일, 2 면 약 8일). 올리면 챗과 심의가 밀린다. 심의가 LLM 을 차지하면 챗이 300초 청크 한도에 걸린다는 기록이 있다(02-cost) |
| 3 | 순서를 뒤집은 이중 판정을 전량에 걸 것인가 | **Tier A 는 전량, 나머지는 15%.** Tier A 범위 실행(§5.4 D)의 일치율을 보고 전원 실행의 비율을 정한다 | 전량이면 카드 대조 호출이 두 배다(단위 8개 · 절반 대조에서 약 2,000회 추가). WP3a 는 첫 실주행 전량을 권고했다 — Tier A 전량이 그 측정을 싸게 대신한다. 0 으로 두면 '문제없음' 이 얼마나 틀렸는지 숫자가 없다 |
| 4 | 결정적 신호(WP2)가 준비되기 전에 전원 검토를 돌릴 것인가 | **Tier A 범위까지만** 돌리고 전원은 신호가 붙은 뒤에 | 신호가 없으면 전수(r = 1)이고 단위 8개 타깃이 약 일주일이다. Tier A(15명)는 반나절이고 훑기 놓침률을 재는 표본이 된다 |
| 5 | 지식카드 원문을 리스크 앱 DB 에 복제해 두어도 되는가 | **둔다.** 박스 간 반출(export)에서는 빼고 DB 백업에는 싣는다 | 얼린 원문이 없으면 인용 대조가 재현되지 않는다. 대신 카드 약 1만 장의 글이 앱 DB 와 그 Drive 백업에 한 벌 더 생긴다 |
| 6 | 이미 패널이 돈 옛 타깃에 검토를 얹게 할 것인가 | **허용한다** | 같은 diff 에는 타깃을 하나만 열 수 있어(409) 막으면 그 과제는 새 흐름을 쓸 길이 없다. 원장의 종결 행은 건드리지 않고 보고서 · finding 만 더해진다. 회로 영역의 보류(deferred)를 푸는 것은 WP2 의 `undefer` 가 따로 묻는다 |

---

## 9. 확인하지 못한 것

- **호출 시간.** 호출 1회 5분은 추정이다. 벽시계 표 전체가 이 값에 비례한다. 파일럿 전에는 일정을 약속할 수 없다.
- **양성 비율 p⁺.** 3% 로 가정했다. 단독 재질의 호출 수가 이 값에 그대로 비례한다.
- **실제 diff 의 단위 수 · 관련 비율.** dev 에 실물이 없다. B 와 r 은 전부 가정이다.
- **전문가별 점검 카드 수의 분포.** 평균 12.9장만 안다. 묶음 수가 평균 2개라는 것도 거기서 나온 셈이다.
- **형제 설계서의 계약이 구현까지 그대로 가는지.** WP2 · WP3a · WP4 · WP5a 의 문서를 경계 부분만 읽고 맞췄다. 전부 읽지 않았고, 그 문서들도 서로 다른 곳이 있다(§7.3). 가짜 엔진으로 초록인 시험이 실주행을 보장하지 않으므로 계약 픽스처를 두 리포가 같이 쓰게 했다.
- **WP3a 의 `text_sha` 식과 `_nq` 규칙의 세부.** 문서에 적힌 식으로 무결성 확인과 재대조를 짰다. 구현이 다르면 `check_pack` 이 전부 실패하거나 `check_disagree` 가 쏟아진다 — 픽스처가 먼저 잡아야 한다.
- **묶음의 압축 크기.** 15~20 MB 는 한국어 gzip 을 3:1 로 놓은 추정이다.
- **등록부 병합 1회의 시간**(finding 수천 건). 1~3초는 추정이다.
- **구독이 끊길 때 LLM 서버가 생성을 실제로 멈추는지.** WP3a 가 태스크를 취소한다고 적었고 띵킹 모드가 같은 방식이지만(thinking.py:428~433) 서빙 쪽 동작은 확인하지 못했다. 안 멈춘다면 취소 · 재기동 뒤 한동안 LLM 에 유령 호출이 남는다(결과는 버려지므로 원장은 안전하다).
- **서비스 PAT 의 권한.** `HWAXRISK_PORTAL_PAT` 주체가 `feat:deliberation`(과 팩 · 검색에 필요한 `plat:aidatahub`)을 갖는지 확인하지 못했다. 오늘 패널이 그 자격으로 도는 박스라면 앞의 것은 갖고 있다.
- **데이터 디렉터리의 파일시스템.** `flock` 이 그 위에서 제대로 서는지(로컬 디스크면 선다). WAL 이 이미 도는 것으로 보아 로컬로 추정한다.
- **Drive 백업(`sqlite3 .backup`)이 며칠짜리 쓰기와 겹칠 때의 동작.** 읽기 스냅샷이라 쓰기를 막지 않을 것으로 보지만 재지 않았다.
- **§2.9 (1)의 결함이 cae00 에서 실제로 났는지.** 메모리 DB 에서 실제 함수로 재현했다(WP1 · WP4 도 같은 결함을 따로 찾았다). 운영 원장은 열지 않았다.
- **diff 항목의 필드 이름.** subject 를 뽑을 때 `subject.ckeys` · `ckey` · `ckey_a/ckey_b` · `subject_key` 를 본다(diff.py:429, 620~628, 1044, 1747). 파라메트릭 항목 종류를 전부 열어 보지는 않았다. 못 뽑으면 단위 범위로 내려가므로 깨지지는 않는다.
- **`rr_units.scope_key` 로 단위의 대표 subject 를 삼아도 되는지.** WP2 문서의 열 설명(`asm:<접두>` 꼴)만 보고 정했다.
- **dev 박스의 창 크기.** WP3a 가 16,384 로 계산했다. 그 값이면 dev 에서는 묶음이 1~2장이라 형식 시험만 뜻이 있다.
