# M2 실행 계획 — WP3b 셀 원장 · 러너 · 카드 묶음 · 검증 · 전문가 보고서 · 품질 수치

> 2026-10-12 작성. 닻은 HWAXRisk `c3f46ba`(설계서 대조 시점 `7248651` 뒤 72커밋)에서 `grep` 으로 다시 찾은 것이다.
> 우선순위는 PLAN.md > problems.md > reference/04-contract.md > reference/spec-wp3b-cells-runner.md 다.
> 걸음 이름 S1~S13 은 짓는 차례이고, 괄호 안이 설계서 4절의 WP3b 걸음 번호다. 이 문서는 계획이며 코드는 아직 한 줄도 없다(`card_review`·`rr_units`·`review_cells` 는 세 리포 어디에도 없다).

## 범위

### 들어오는 것

| 걸음 | WP3b | 무엇 |
|---|---|---|
| S1 | 1 | 스키마 v4 가운데 내 몫(새 표 다섯 · `rr_jobs` 열 넷 · `rr_findings` 열 넷)과 반출·이양·폐기 배선. dev 리허설(S13)이 끝날 때까지 push 하지 않는다 |
| S2 | (WP5a 몫) | 순수 모듈 `review_ops.py`(실패 부류 셋 + 잡 단위 · 백오프 · 보류 코드 표 · 차단기 판정)와 검토 손잡이 넷 |
| S3 | 4 | 카드 묶음 확인 · 동결 · 꺼내기(`cardpack.py`) |
| S4 | 5 | 받은 행의 회계 · 얼린 팩 재대조 · 카드 등급 · 실효 판정(`review_verify.py`)과 `narrative.py` 의 카드 갈래 |
| S5 | 6 | 셀 원장 · 상태기계 · 선점 · 정산 · 복구 · 불변식(`review_cells.py`), 검토 잡 만들기, `planner.close_review_seat` |
| S6 | 3 | 패널 경로가 패널 잡만 본다 · 흐름 가드 · 보류 열과 사람의 정지 |
| S7 | 7 | 대화 없이 `card-review` 넷을 부르는 엔진 클라이언트와 시험 디렉터리의 가짜 엔진 한 벌 |
| S8 | 8 | 검토 루프(선점 단위 = 전문가 세션, 기다림 부류, 차단기, 재기동 복구, 진행 신호) |
| S9 | 9 | finding 승격 · 의견 행 · 원장 마감 |
| S10 | 10 | 전문가별 보고서(코드 조립, LLM 0회) |
| S11 | — | 품질 수치 모듈 `review_quality.py`(격자 · 카드 · 절단 · 인용 · 뒤집힘 · 호출 초 + 실측표 항목) |
| S12 | 11 | REST(한 벌) · MCP 읽기 도구 둘 · `risk_start_job` 의 `mode` |
| S13 | 1 의 끝 | dev 리허설 → v4 확정 → push · SIF 교체 · 게이트웨이 `tools/list` 확인 → cae00 파일럿 지원 |

M2 실행 설정은 코드 기본값으로 둔다(손잡이로 두지 않고 `launch.env` 에도 적지 않는다 — `tests/test_manifest.py` 가 `launch.env` 를 두 키로 못 박는다, X2-07).
- 훑기 켬 — 카드가 있는 전문가는 늘 부른다. 답은 셀 분류에 쓰지 않는다(`route='review'`, `route_forced='filter_off'`). 근거 PLAN §4 '훑기', WP3b P-03.
- 거르기 끔 — `na_irrelevant` 로 가는 코드 자체를 만들지 않는다.
- 순서를 뒤집은 이중 판정 전량 — `dual_rate=1.0` 을 잡 `params_json.knobs` 에 복사한다(결정론의 전제).

### 빠지는 것

- WP3b 2(러너 단일 인스턴스 잠금)는 M1 에서 끝났다(`app/runlock.py` · `RiskRunner.start/_await_lock/_begin`). 남은 일은 셀 복구 함수를 `_begin` 에 하나 더 거는 것뿐이다(S8).
- `busy_timeout` 은 M1 에서 끝났다(`risk_store.BUSY_TIMEOUT_S = 30` → `sqlite3.connect(timeout=…)`).
- WP3b 12(문서)는 마일스톤 끝 문서 걸음에 합친다.
- 입력 결손 호출(`noinput`) · `no_input` 상태 · `rr_roster.input_gaps_json` 은 M3 다. M2 는 ECAD 의존이면서 ECAD 가 없는 전문가를 범위에 넣지 않는다(S5 의 거절).
- 결정적 신호(`unit_signals.for_cell`) · 훑기 거르기 · `sweep_miss_max` 자동 전환 · '해당 없음' 표본 재검토는 M4 다.
- 음성 판정 10% 무작위 재질의(4장 `rev` 묶음)는 뺀다(문제 목록의 cuts). 이중 판정 전량이 그 측정을 대신한다.
- 긴 문서 검색(`extra.search`)은 M3 다(WP3a 8). 카드 0장 전문가는 M2 에서 역할만으로 카드 밖 호출을 한다(`basis='role_only'`).
- 등록부 병합 · 지지 수 · 쟁점 · 종합 · 완결 판정 · `_panel_scope` 의 카드 묶음 배선은 M3(WP4)다(열린 물음 4).
- 실패 셀 처분 REST(`retry`·`skip` 묶음) · `reset_review` 는 M3, `packs/refresh` 는 뺀다.
- 제공자 접점(`WorkProvider`) · `direct` 정책 · 승계 인덱스 `ix_rr_cells_reuse` · 묶음 반 나누기(`over_budget`·`context_overflow`·`truncated_empty`)는 뺀다(cuts · D-22).
- HWAXRisk `frontend/` 는 다른 세션이다. 응답 필드까지만 한다.
- WP2(단위) · WP3a(에이전트 서버 `card_review`) · 포털 중계 `P1` · WP5b `C5·C7·C8·C9·C15` 는 다른 계획서다. 여기에는 받는 계약만 적는다.

## 걸음

### S1 스키마 v4 — 내 몫 (WP3b 1, M2 분)

- **목적.** 셀 원장 다섯 표와 기존 표 열 여덟을 v4 한 블록에 싣는다. WP2 의 표(`rr_units`·`rr_unit_builds`·`rr_targets.flow`)와 **같은 블록 · 같은 커밋**이다(C-2 — 버전은 마일스톤마다 하나).
- **파일 · 닻(지금 코드).**
  - `risk_store.py:581` `MIGRATIONS = [(1, _DDL_V1), (2, _DDL_V2), (3, _DDL_V3)]` 에 `(4, _DDL_V4)` 를 더한다. 허용 연산은 `CREATE TABLE IF NOT EXISTS` · `ADD COLUMN` · `CREATE INDEX IF NOT EXISTS` 셋이다. 이행 잠금(`migrate.lock`)과 사본(`pre-migrate-v3-*`)은 M1 코드가 그대로 맡는다.
  - `tests/test_store.py:232` `PUSHED_DDL_SHA256` 에 4 를 적는다. 로컬 커밋마다 고쳐도 되고 push(S13) 때 굳는다.
  - `tests/test_store.py` 의 규약 시험(`owner_sub` 이 있거나 `SHARED_TABLES`)은 `rr_card_packs` 를 받지 못한다. 집합 `LOCAL_ONLY_TABLES = {"rr_card_packs"}` 를 시험과 `export.py` 가 같이 읽게 한다. 91행의 'v1 밖 표 집합' 도 고친다.
  - `export.py:23` `_table_order()` 가 `LOCAL_ONLY_TABLES` 를 뺀다. `_SINCE_COLS`(43행)에 넷(`rr_review_cells:updated_at` · `rr_expert_reports:updated_at` · `rr_review_calls:started_at` · `rr_card_verdicts:created_at`)을 더한다. `_EXPORT_SKIP_COLUMNS`(83행)에 `rr_review_calls.result_gz` 를 더한다(`rr_panels.result_gz` 선례). `rr_card_verdicts.cq` 는 반출에서 200자로 줄이고 원래 길이를 `cq_chars` 로 싣는 작은 변환을 둔다(열린 물음 1).
  - `routes.py:792` `TRANSFER_DERIVED` 에 새 표 넷을 `target_key IN (…)` 조건으로 더한다(`rr_card_packs` 는 소유자가 없다).
  - `routes.py:991` `PURGE_BLANK_SQL` 에 넷을 더한다 — 판정(`cq·why·need·path·check_text·conds_json·checks_json`) · 머리(`report_gz·summary_md·sweep_json`) · 셀(`extras_json·route_json·mechs_json·handoffs_json·error·decide_note` — m-10) · 호출(`result_gz·quality_json`). 같은 트랜잭션에서 그 타깃 셀·머리의 `lease_owner` 를 비워 폐기 뒤 늦게 끝난 호출의 쓰기를 버리게 한다(m-10). 카드 묶음은 지우지 않는다.
- **계약(v4 의 내 몫 — 어휘 열에 CHECK 없음, C-3).**

| 표 | 키 | 열 |
|---|---|---|
| `rr_expert_reports` | PK(target_key, agent_key) | owner_sub · domain · rank_in_domain · tier · review_order · review_id(hex32) · state · lease_owner · claimed_at · run_id · not_before · pack_hash · pack_status · pack_error · pack_attempts · pack_frozen_at · card_basis · plan_json · limits_rev · sweep_state · sweep_json · cells_total · report_gz · report_hash · report_bytes · summary_md · revision · opinion_id · findings_n · coverage_status · model · prompt_rev · norm_rev · verify_rev · stats_json · error · finalized_at · created_at · updated_at |
| `rr_review_cells` | PK(target_key, unit_id, agent_key) | owner_sub · domain · unit_seq · state · route · route_forced · route_json · basis · run_id · lease_owner · heartbeat_at · priority · tries · charged · infra_streak · not_before · error_code · error_class · error · knob · credential_kind · model · llm_calls · tokens_in · tokens_out · elapsed_ms · truncated(0·1·NULL=모름) · rows_expected · rows_missing · stamp · soft_over · cards_expected · cards_judged · n_fail · n_warning · n_ok · n_na · n_undetermined · n_disputed · n_flipped · n_offcard · offcard_state · offcard_capped · quote_ok · quote_n · refs_ok · refs_n · bg_full_n · bg_title_only_n · unit_hash · pack_hash · input_hash · prompt_rev · verify_rev · extras_json · mechs_json · handoffs_json · sample_json · status_source · decided_by · decided_at · decide_note · reopened_n · started_at · finished_at · created_at · updated_at |
| `rr_card_verdicts` | PK(target_key, unit_id, agent_key, record_id, variant) | owner_sub · alias · card_id · section_id · text_sha · applies · judgement · cq · lines_json · refs_json · why · need · sev · mech · mech_free · path · check_kind · check_text · conds_json · checks_json · quote_ok · refs_ok(NULL=참조 없음) · check_disagree · grade · is_effective · agree · split · revised_from · deck_id · call_id · created_at |
| `rr_card_packs` | PK(agent_key, pack_hash) | norm_rev · role_sha · cards_total · checkable_n · chars_total · unrenderable_n · manifest_json · pack_gz · source · fetched_at — owner_sub 없음, 반출 제외(C-9) |
| `rr_review_calls` | PK call_id | target_key · agent_key · unit_id · owner_sub · run_id · kind · variant · deck_id · page_no · seq · state · outcome_class · cards_json · request_hash · input_sha · prompt_chars · tokens_in · tokens_out · output_truncated · finish_reason · soft_over · attempts · queued_ms · llm_ms · rows_expected · rows_missing · bad_lines · stamp · dropped_over_cap · bg_dropped · model · prompt_rev · norm_rev · limits_rev · credential_kind · result_gz · result_sha256 · quality_json · error_code · error_infra · error_retryable · error · started_at · duration_ms |
| `rr_jobs` 에 ADD | — | mode(NULL = panels · `panels` · `reviews`) · hold_code · hold_until · hold_n |
| `rr_findings` 에 ADD | — | unit_id · source_kind · source_id · agent_key — WP4(v5) 몫이던 것을 M2 의 승격(S9)이 쓰므로 v4 로 당긴다 |

  - 열 이름은 C-21 이다. 뜻은 WP3b 의 것을 담는다(P-01) — `tries` = 그 셀에 낸 호출 수(기다림 제외), `charged` = 내용 탓 실패 수(설계서 `attempts`), `infra_streak` = 연속 인프라 실패(성공하면 0, 백오프 지수), `lease_owner` = `<boot_id>:<선점 uuid>`(선점마다 새 값이라 늦은 쓰기를 막는다), `run_id` = `rr_jobs.id`, `not_before` = 백오프 시각, `tokens_in·out` = 서버 `meta.usage` 합.
  - 인덱스 — 셀 `(target_key, state)` · `(target_key, agent_key, unit_seq)`, 판정 `(target_key, agent_key, is_effective, judgement)` · `(target_key, unit_id, is_effective)`, 호출 `(target_key, agent_key, unit_id, started_at)` · `(run_id, started_at)`, 머리 `(target_key, state, review_order)` · `(review_id)`.
  - v5 로 미루는 열 — `input_gap_json` · `route_det` · `route_llm` · `audit_kind` · `audit_result` · `ix_rr_cells_reuse`.
- **수용 기준.** P-11(C-21 이름 · 한 블록 · 뒤에 필요한 열은 v5 의 ADD COLUMN 으로만), C-3, C-9, X1-27(격자의 분모는 늘 로스터 × 검토 대상 단위), m-10. 나갈 기준 1·2 의 바닥이다.
- **시험.** `tests/rr/test_legacy_flow.py` 의 v2 얼린 DB 를 v4 로 올려 골든이 그대로다. 지금 코드로 만든 v3 DB(패널 결과 `result_gz` 가 든 행)를 v4 로 올려 행이 그대로다. 새 표에 행을 실제 생산자(S3·S5·S8 이 생긴 뒤 그 함수)로 넣고 반출 → 빈 DB 들여오기 왕복에서 `rr_card_packs`·`result_gz` 가 빠지고 `cq` 가 200자다. 이양·폐기 시험에 새 표 행을 넣어 소유자가 옮겨지고 원문이 빈다.
- **의존.** WP2 계획의 v4 DDL(같은 블록). 이 걸음이 블록 파일의 주인이고 WP2 의 문장을 받아 싣는다.
- **크기.** 5시간.

### S2 `review_ops.py` 와 검토 손잡이 (WP5a 몫의 순수 모듈 — PLAN §4)

- **목적.** 실패 분류 · 백오프 · 보류 코드 · 차단기 판정을 한 곳의 순수 함수로 둔다. 러너(S8)와 엔진 클라이언트(S7)가 부른다. WP5a R6 은 지웠으므로 이 모듈이 그 표의 유일한 구현이다.
- **파일 · 닻.** 새 `app/review_ops.py`(첫 줄 한국어 주석). `config.py:112` `Settings` 와 `load_settings`(184행)에 손잡이 넷, `config.py:263` `credential_margin_s` 옆에 `review_call_timeout_s()` · `review_read_timeout_s()` · `review_credential_margin_s()`. `main.py:53` `check_credential_chain` 옆에 `check_review_chain`(WP5a R5 의 최소분 — 그 계획과 겹치면 그쪽이 가져간다).
- **계약.**
  - `classify(code, *, infra=None, retryable=None, http_status=None) -> Outcome{klass, charge, hold_code, retry_after_s, knob}`. `klass` 는 `wait · infra · content · job · cancelled` 다. 셀의 실패 부류는 PLAN §4 대로 셋(인프라 · 내용 · 기다림)이고 `job` 은 셀을 차감 없이 놓고 잡을 보류하는 갈래다.

| 부류 | 코드 | 셀에 하는 일 |
|---|---|---|
| wait | `review_busy`(서버 관문 즉답) · `engine_busy`(포털 429) · `draining` | 아무것도 세지 않는다. 같은 자리에서 `retry_after_s` 뒤 같은 호출을 다시 낸다(D-10) |
| infra | `agent_unreachable` · `agent_5xx` · `portal_unreachable` · `portal_5xx` · `engine_stream_cut` · `engine_silent` · `llm_unreachable` · `llm_timeout` · `llm_error` · `busy`(옛 판 서버의 대기 초과) · `restart` · `store_write_failed` · 같은 호출의 첫 `review_timeout` | `charged` 그대로, `infra_streak+1`, `not_before = now + backoff` |
| content | `no_rows` · `truncated_empty` · `cards_unjudged` · `review_parse_failed` · 같은 호출의 두 번째 `review_timeout` · 표에 없는 코드(원문 보존) | `charged+1`, 한도(2) 미만이면 `pending`, 닿으면 `failed(<code>)` |
| job | `pat_unavailable` · `credential_expired` → `credential` · 403 `forbidden` · 422 `bad_request` · `check_disagree` 초과 → `contract` · `review_unsupported`(404 · 첫 프레임 없음) → `agent_outdated` · `over_budget` · `context_overflow` · plan 의 `oversize` → `ctx_too_small` · 창 출처 `fallback` 600초 → `ctx_unknown` · 팩 502 지속 → `aidh_unreachable` | 셀은 차감 없이 `pending`, 잡은 `paused` + `hold_code` |
| cancelled | 사람의 정지 · 취소 · 앱 종료 | 차감 없이 `pending` |

  - 표가 이긴다. 서버의 `infra` 비트는 표에 없는 코드에만 쓴다 — `llm_timeout` 처럼 설계서끼리 부류가 갈린 코드를 한 자리에서 정한다(열린 물음 9).
  - `backoff_s(infra_streak, *, salt) = min(30·2^(n−1), 900)` 초에 해시로 정한 ±20% 흩뿌림(난수를 쓰지 않는다).
  - `HOLD_CODES` — `user`(사람) · `credential` · `content_fail_rate` · `contract` · `ctx_too_small` 은 자동 재개 없음, `llm_outage`(300 → 600 → 1,200 → 2,400 → 3,600초) · `aidh_unreachable`(300 → 1,800초) · `agent_outdated`(300초) · `ctx_unknown`(창 출처가 `server`·`env` 로 돌아오면)은 자동 재개.
  - `breaker_verdict(last20) -> None | 'llm_outage' | 'content_fail_rate'` — 끝난 호출 20건(10건 이상일 때)에서 인프라 10건 이상이면 `llm_outage`, 내용 탓이 절반 이상이면 `content_fail_rate`. 창은 `rr_review_calls` 에서 읽는다(재기동해도 같다). wait 는 세지 않는다.
  - 손잡이 — `HWAXRISK_REVIEW_CONCURRENCY`(4) · `HWAXRISK_REVIEW_CALL_TIMEOUT_S`(18,000, 0 = 끔) · `HWAXRISK_REVIEW_READ_TIMEOUT_S`(300 — ping 이 15초라 죽은 연결이 자리를 15시간 붙들지 않게, m-13) · `HWAXRISK_REVIEW_MAX_CHARGED`(2). `review_credential_margin_s = 호출 벽시계 + 600`(기다림은 호출마다 자격을 다시 고르므로 넣지 않는다).
  - `check_review_chain` — 자격 여유 < `routes.PAT_MIN_REMAINING_S`(86,400), 읽기 한도 < 호출 벽시계가 아니면 기동을 막는다.
- **수용 기준.** P-01(분류 · 보류 · 백오프 · 차단기는 이 모듈 하나), P-02(1)(기다림은 어디에도 세지 않는다), PLAN §4 C-24·C-26 · '단위 맞춤' · '모델 창', D-10, D-22, m-13, X2-07(손잡이는 코드 기본값 — `launch.env` 에 적지 않는다).
- **시험.** 표의 줄마다 `classify` 한 번. 표에 없는 코드는 서버 비트를 따르고 원문이 남는다. `backoff_s` 는 같은 인자면 같은 값이고 900초를 넘지 않는다. `breaker_verdict` 는 wait 20건이면 None 이다. 뒤집힌 손잡이로 `check_review_chain` 이 기동을 막는다.
- **의존.** 없다.
- **크기.** 3시간.

### S3 카드 묶음 확인 · 동결 · 꺼내기 (WP3b 4)

- **목적.** WP3a `/pack` 응답을 통째로 얼리고, 호출마다 거기서 꺼낸 카드를 **그대로** 되보낸다. 대조도 그 얼린 글로 한다(D-14).
- **파일 · 닻.** 새 `app/cardpack.py` — `check_pack` · `freeze_pack`(INSERT OR IGNORE, 전문가마다 따로 커밋) · `load_pack`(프로세스 LRU 32) · `card_text`(절 `text` 를 줄바꿈으로 이은 것, 머리 줄 제외) · `cards_for`(팩 항목 그대로, `rev` 는 순서만) · `load_for(store, target_key, agent_key)`. 지금 코드에 선례는 `runner.freeze_brief`(686행 — canonical_json → gzip → sha256[:12])다.
- **계약.**
  - `check_pack` 다섯 — `pack_hash`·`norm_rev`·`role_sha` 가 있고 `agent_key` 가 청한 키와 같다, 별칭·`record_id` 유일, 카드마다 `text_sha == sha256("\n".join(f"{sid}\t{title}\n{text}"))`, `cards_total == len(cards) + len(unrenderable)` · `checkable_n` 일치, 절 없는 카드는 `unrenderable` 에만 있다.
  - 받은 결과 — 200·카드 ≥1 → `ok`, 200·0장 → **두 번 연달아 0장이고** 그 전문가의 앞선 묶음(`rr_card_packs`)에도 카드가 없을 때만 `empty`, 아니면 `error('suspect_empty')`(P-08 · X1-25), 404 `agent_not_found` → `error` 이고 백오프하며 3번까지, 502 `card_fetch_failed` · 통신 실패 · `check_pack` 실패 → `error` 이고 60초부터 두 배(상한 1,800초) 6번까지. 한도를 넘긴 전문가의 셀 처리는 S8 이다.
  - `card_basis` — 점검 카드 ≥1 이면 `cards`, 전부 배경이면 `background`, 0장이면 `none`.
- **수용 기준.** C-9 · C-10 · C-11, P-08('0장' 과 '못 받았다' 를 섞지 않는다), 나갈 기준 2(대조 원문이 원장 안에 있다).
- **시험.** 픽스처는 에이전트 서버의 실제 `build_pack`/`normalize_card` 가 지어낸 카드로 만든 응답을 바이트 그대로 복사한 `tests/fixtures/card_review/contract/pack_*.json` 이다(WP5b C7 — 해시를 포털 가드 시험이 본다). 손으로 쓴 팩은 쓰지 않는다. 결함 다섯을 하나씩 심어 각각 짚는지, 문제 있는 팩은 행을 남기지 않는지, 같은 팩을 두 번 · 두 타깃에서 얼려도 행이 하나인지, `cards_for` 가 바이트로 같은지, 0장 한 번은 `empty` 가 아닌지 본다.
- **의존.** S1, WP3a 의 팩 픽스처(계약 파일).
- **크기.** 4시간.

### S4 받은 행의 회계 · 얼린 팩 재대조 · 등급 · 실효 판정 (WP3b 5)

- **목적.** '저장된 판정의 카드는 그 호출에 실은 카드이고, 대조 통과 인용은 얼린 원문에 있다'(나갈 기준 2)를 코드로 지킨다. 등록부로 가는 finding 이 패널과 같은 `_normalize_finding` 을 지나며 카드 인용을 처음으로 실재 확인받게 한다.
- **파일 · 닻.**
  - 새 `app/review_verify.py` — `VERIFY_REV` · `nq` · `accept_rows` · `card_grade` · `effective_rows` · `sweep_accounting` · `dual_plan`.
  - `common.py:201` `parse_ref` 의 card 갈래에 `card:<record_id>#<section_id>` 를 더한다(282행의 역방향도).
  - `narrative.py:269` `SpecContext` 에 `card_pack` · `card_scope` · `number_corpus` 를 더한다(`call_ids` 는 286행에 이미 있다). `_resolve_one`(741행)의 card 갈래, `canonical_text_for`(647행)의 card 갈래, `resolve_cites`(845행)의 card 행 대조와 수치 대조, `evidence_grade_from_cites`(920행)의 card 행 등급.
  - `narrative._panel_scope`(1664행)에서 타깃 · 스냅샷 · diff · IR 부분을 `_target_scope(store, target_key)` 로 떼고(패널 동작은 그대로), 새 `review_scope(store, target_key, agent_key, review_id, pack, *, number_corpus)` 가 그것을 쓴다.
- **계약.**
  - `nq` = `render.norm_quote`(M1 이 만든 정규화) + 마크다운 강조 기호(`*`·`` ` ``) 제거 + 굽은 따옴표를 곧은 따옴표로. 서버 `_nq` 와 같은 입출력 벡터 파일로 묶는다(서버의 실제 함수가 만든 파일).
  - `accept_rows` — 별칭이 실은 집합 밖이면 버린다(`alias_outside_call`), 같은 별칭은 첫 행, `record_id` 는 행의 값이 아니라 별칭 → 팩으로 되돌린 값(다르면 `record_mismatch`), 열거 밖·정합 안 맞음은 빠진 카드, `missing` 은 앱이 다시 센다. `l`·`refs` 가 문자열 하나로 오면 한 항목 목록으로 읽는다(글자로 쪼개지 않는다 — D-25 의 교훈).
  - `quote_ok` — 서버 `checks.quote == 'ok'` **그리고** `nq(cq)` 가 15자 이상 · 실질 10자 이상이고 **그 카드**의 `nq(card_text)` 의 부분 문자열일 때만 1, 둘이 갈리면 `check_disagree = 1` 이고 0(X1-21), 인용이 없으면 NULL. 맞은 첫 절을 `section_id` 로 적는다(사람이 `card:<record_id>#<sid>` 로 원문을 찾게).
  - `refs_ok` — 되돌아온 참조가 하나도 없으면 NULL(X1-05), 전부 그 단위에 실어 보낸 참조(변경 줄 + 근거 꾸러미 줄)면 1, 아니면 0. `applies='yes'` 인데 참조가 없으면 0 이다.
  - `card_grade` — `confidence='fact'` 이고 `standard_refs` 또는 `sources_n ≥ 1` 이면 '문헌·규격', 나머지는 '경험칙'. `quote_ok = 1` 인 행에만 뜻이 있다.
  - `effective_rows` — 설계서 §3.8.7 표에 X1-14 의 한 줄을 더한다. 어느 변형이든 FAIL·WARNING 이 있었는데 실효가 OK·na 가 되면 실효를 `undetermined` 로 두고 `split = 1`, `n_disputed` 에 센다.
  - `dual_plan` — 이중 판정 전량. `rev` 요청의 본문 해시가 `fwd` 와 같으면(1장 묶음) 부르지 않고 `agree = NULL` 로 두며 그 카드를 `solo` 로 보낸다(X1-20).
  - `sweep_accounting` — `u` 줄의 단위 집합 == 그 쪽의 단위 집합, `(k 합집합) ∪ k0` == 실은 카드 집합. 빠진 단위는 `route_llm` 대신 `sweep_json` 에 `error`, 어느 줄에도 없는 카드는 `cards_unseen`.
  - `narrative` 카드 갈래 — `card_pack` 이 있으면 묶음에서 찾는다(있으면 `verified=True`, 없으면 `not_in_pack`, 범위 밖이면 `not_in_scope`). `payload` 는 `{record_id, card_id, type, confidence, grade}` 로 줄인다(P-06 — 카드 본문이 `finding_json` 에 들어가지 않게). card 행 등급은 `row.card_grade` 가 '문헌·규격' 일 때만 그 등급이다. `card_pack=None` 이면 지금 갈래(`external_check`)와 지금 등급 규칙(`GRADE_RULES = "cites-2"`, D-19)이 한 줄도 안 바뀐다.
  - `number_corpus` 가 있으면 claim·warrant 의 수치를 말뭉치의 수치 **토큰 집합**(`_numbers_in`)과 견주고, 없는 수치는 `unquoted_numbers` 에만 적고 통과한 인용 전부를 불일치로 만들지 않는다(P-05 — 그 finding 의 등급은 S9 에서 경험칙으로 묶는다). `None` 이면 지금 식 그대로다.
  - `review_scope` 의 `call_ids` = 그 타깃 스냅샷들의 `rr_snapshot_calls.call_id` ∪ 그 단위들의 근거 꾸러미 호출 id(P-07). `_panel_scope` 의 `call_ids` 는 M2 에서 건드리지 않는다(패널 경로 불변).
- **수용 기준.** 나갈 기준 2, C-11 · C-15, P-05 · P-06 · P-07, X1-05 · X1-14 · X1-20 · X1-21, D-19(소급 없음), D-24(패널 경로 불변).
- **시험.** 설계서 §5.1 '검증' 목록 전부. 공유 `nq` 벡터 통과. 실제 card_id 모양(`MIS-R-001`)과 record_id 모양으로 만든 카드 근거 finding 의 `unquoted_numbers` 가 비어 있다(P-05). 정규화한 finding 에 카드 절 본문이 없다(P-06). 근거 꾸러미 줄 `tool:…` 을 인용한 finding 의 dangling 이 0(P-07). `card_pack=None` 에서 `tests/test_atoms.py` · `test_cite_scope.py` · 옛 타깃 골든이 그대로다. 입력 카드는 S3 의 공유 팩, 결과 행은 WP3a 계약 파일의 `result` 표본이다.
- **의존.** S3.
- **크기.** 8시간.

### S5 셀 원장 · 상태기계 · 잡 만들기 · 원장 닫기 (WP3b 6)

- **목적.** 격자를 늘 '로스터 전원 × 검토 대상 단위' 로 만들고, 범위는 '집지 않는 것' 으로만 구현한다(X1-27). 셀 · 전문가의 전이를 한 함수가 막는다.
- **파일 · 닻.**
  - 새 `app/review_cells.py` — `CELL_STATES` · `EXPERT_STATES` · `_move` · `plan_cells` · `claim_next_expert` · `release_expert` · `write_call_result` · `settle_cell` · `fail_open_cells` · `recover_running` · `review_invariants` · `review_summary`.
  - 새 `app/review_runner.py` 의 첫 함수 `create_review_job`(네트워크 없음 — 루프는 S8).
  - `planner.py:47` `ALLOWED_TRANSITIONS['pending']` 에 `done · done_weak · abstain`(검토 마감 전용 주석)을 더하고 `close_review_seat` 를 새로 둔다. `planner.check_invariants`(862행)는 검토 중에도 원장을 `pending` 으로 두므로 그대로 통과해야 한다.
- **계약.**
  - 셀 상태 — `pending · running · reviewed · na_irrelevant · no_input · failed · skipped`(C-18 어휘 일곱). M2 가 쓰는 전이는 `pending→running` · `running→reviewed` · `running→pending`(기다림 · 인프라 · 취소 · 재기동 · 한도 미만 내용 탓) · `running→failed`(내용 탓 한도 · 호출 수 상한 · 팩 한도 초과) · `pending→failed`(팩 한도 초과 · `agent_not_found`)다. `skipped` 는 `failed` 에서만 간다(PLAN §4, 처분 REST 는 M3). `na_irrelevant`·`no_input` 은 어휘만 있다.
  - 전문가 상태 — `planned · running · ready · partial · blocked`. `partial` 은 열린 실패 셀이 있거나 범위 밖 `pending` 이 남은 채 마감한 것이다(P-04).
  - `plan_cells` — `planner.review_order`(WP2)의 전원 × 활성 빌드의 `reviewable = 1` 단위, INSERT OR IGNORE, 전부 `pending`. 재빌드로 사라진 단위의 열린 셀은 지우고 종결 셀은 집계에서 뺀다(설계서 §3.7.2).
  - `claim_next_expert(store, job, now, boot_id)` — 범위 안 · `planned` · `not_before` 지남 · 열린 셀이 있는 전문가 하나. 살아 있는 검토 잡을 돌아가며(도는 전문가가 가장 적은 잡부터) 집는다(P-09). `UPDATE … SET state='running', lease_owner=? WHERE … AND state='planned'` 의 rowcount 가 1 일 때만 돌려준다.
  - `write_call_result` · `settle_cell` · `finalize`(S9)는 `… WHERE lease_owner = ?` 의 rowcount 가 0 이면 아무것도 쓰지 않는다. 엔진 호출은 `tx()` 밖이다.
  - `settle_cell` 의 `reviewed` 조건 — `cards_judged == cards_expected`, 정산에 쓴 호출에 `truncated = 1` 이 없다(NULL 은 '모름' 으로 세고 막지 않는다 — X1-22), 계획한 `rev`·`solo` 가 다 돌았다, 카드 밖 호출이 `done | none` 이다. 아니고 더 부를 호출이 없으면 내용 탓 실패다.
  - `review_summary` — 상태별 수, `reviewed` 를 `basis` 로 가른 수(`cards · background · role_only` — X1-04), 범위 안 · 범위 밖 `pending`, 열린 실패, 전문가 상태별 수.
  - `create_review_job(store, target_key, *, owner_sub, requester_sub, scope, user_memo, consent, consent_source, settings)` — 범위 키는 `tiers · domains · agents · unit_ids` 넷(PLAN §4 REST). 자격은 요청자 → 소유자의 **사용자 PAT 만**이고 남은 수명 > 검토 여유일 때만 쓴다. 서비스 PAT 로 내려가지 않는다(사용자 결정 3). `params_json = {scope, user_memo, requester, consent, consent_source, credential{kind, email, exp}, knobs{dual_rate: 1.0, sweep: "on", filter: "off", max_charged: 2, sample_salt}}`, `tier` 는 NULL. 예상 소요가 PAT 남은 수명보다 길면 `credential_note` 를 싣는다.
  - 거절 — 409 `review_job_exists` · 409 `panel_job_running`(queued·running·paused·cancelling) · 409 `repersist_pending`(`runner.awaiting_repersist` 가 비지 않음 — 검토 마감이 그 패널이 되돌려 둔 `pending` 좌석을 닫으면 다시 저장이 `seats_moved` 로 영영 거절된다, RR-ADV-1) · 422 `units_absent`(WP2 빌드가 `ok·oversize` 가 아님) · 422 `consent_required` · 422 `pat_unavailable`(고칠 곳 — 포털 PAT 등록) · 422 `input_gap_m3`(범위에 `rr_roster.ecad_dependent = 1` 이면서 `routes._ecad_absent_for_target` 인 전문가) · 422 `scope_empty`.
  - 반환 — `{job_id, mode: "reviews", cells_total, cells_in_scope, experts_in_scope, units, calls_estimate{low, high}, credential{kind, email, exp}, credential_note?}`.
  - `close_review_seat` 의 롤업 표 — 위에서 처음 맞는 줄이다. ① `reviewed` ≥1 이고 `applies='yes'` 이면서 `quote_ok = 1`·`refs_ok = 1` 인 실효 행이 있다 → `done`(실패 셀이 있으면 `done_weak` + `partial:<n>` — m-01) ② `reviewed` ≥1 이고 그런 행이 없다 → `done_weak`(`no_verified_cite` · `no_cards`) ③ `reviewed` 0 이고 남은 것이 실패뿐 · 범위 밖 `pending` 이 있다 · 어느 줄에도 안 맞는다 → 닫지 않는다(X1-05 · X1-23). 패널이 닫은 행 · `deferred` · `carried` 는 건드리지 않는다. M2 에서 원장을 닫는 것은 `flow='cells'` 대상뿐이다(열린 물음 5).
- **수용 기준.** C-18(PLAN §4 판), X1-04 · X1-05 · X1-23 · X1-27, P-04 · P-09, m-01, RR-ADV-1 회귀, 사용자 결정 3, 나갈 기준 1(격자가 완전하다).
- **시험.** 단위는 `app/devseed.py` 합성 쌍 → 실제 캡처 · `create_diff` → WP2 단위 빌드로 만든다(`tests/factories.py`). 셀 수 == 로스터 × 검토 대상 단위, 두 번 불러도 같다. 전이표의 모든 줄과 표에 없는 전이(`reviewed→na_irrelevant`, `pending→skipped` 등)가 예외다. 두 스레드가 같은 전문가를 집으면 하나만 얻는다. 복구가 선점을 지운 뒤 옛 `lease_owner` 의 쓰기가 0행이다. 거절마다 실제 생산자로 만든 상태(패널 잡은 `runner.create_job`, 다시 저장 대기는 M1 의 `persist_error` 길)에서 본다. `close_review_seat` 세 갈래와 검토 중 `check_invariants` 빈 목록.
- **의존.** S1 · S4, WP2 의 `rr_units` · `rr_unit_builds` · `planner.review_order`.
- **크기.** 9시간.

### S6 패널 경로는 패널 잡만 본다 · 흐름 가드 · 보류 열 (WP3b 3)

- **목적.** 한 `rr_jobs` 표에 두 종류가 들어와도 패널 러너가 검토 잡을 집거나 멈추거나 보여 주지 않게 한다. 두 방식 공존(D-24)의 회귀 가드다.
- **파일 · 닻(지금 위치).**
  - `runner.claim_next_job`(931행)의 두 조회(`daily_cap` 재개 · `queued/running/cancelling`)에 `AND COALESCE(mode,'panels') = 'panels'`. 집은 잡이 패널 잡이 아니면 예외로 드러낸다(설계서 위험 25).
  - `runner.recover_running_panels`(1050행)의 `SELECT id, target_key FROM rr_jobs WHERE state = 'running'` 에 같은 조건.
  - `runner.create_job`(799행) — `rr_targets.flow = 'cells'` 면 422 `flow_mismatch`, 살아 있는 검토 잡이 있으면 409 `review_job_running`.
  - `runner._set_job`(870행) · `pause_job`(887) · `resume_job`(898) · `cancel_job`(907) — 검토 잡이면 `hold_*` 를 같이 다룬다. 사람의 `pause` 는 `hold_code='user'`·`hold_until=NULL` 로 덮고 코드가 멈춘 `paused` 에도 듣는다. `resume`·`cancel` 은 셋을 비운다(P-10 · X4-25). 패널 잡의 동작은 그대로다.
  - `routes.coverage_payload`(2267행)의 최근 잡 → 패널 잡만(`job` 칸의 뜻 불변). 검토 잡은 S12 의 `review.job` 칸이다.
  - `routes` 과제 화면 잡 목록(586행 부근) — 거르지 않고 `mode` 를 싣는다.
  - `brief.py:1810` 최근 잡 메모 → 패널 잡만.
  - `entry.start_job`(319행, 살아 있는 잡 조회 335행) · `entry.next_step`(656행 잡 조회) → 패널 잡만(검토 잡은 S12).
  - `routes` `GET /targets/{key}/brief`(2834행)와 MCP `risk_get_brief` — `flow='cells'` 면 422 `cells_flow_web_only`(WP4 §3.12 와 같은 코드 — Claude Code 보충 회차는 cells 대상에서만 막는다, D-24).
  - 이양 가드(920행) · 폐기(1053행)는 종류와 무관하게 그대로다(검토 잡도 세고 취소한다).
- **수용 기준.** 설계서 위험 25, P-10, X4-25, D-24 의 회귀 가드(옛 타깃 골든 · 합성 40건 패널 셋 연속 `done` 이 그대로).
- **시험.** 검토 잡은 S5 의 `create_review_job` 으로 만든다. `claim_next_job` 이 None, 재기동 복구가 그 잡을 건드리지 않음, 진행판 `job` 이 패널 잡, 브리프 메모가 패널 잡 것, cells 대상의 Tier 잡 422, 코드 보류 중 `pause` 뒤 시계를 밀어도 `queued` 로 안 돌아옴. `tests/rr/test_legacy_flow.py` · `tests/rr/test_panel_ledger.py` · `test_runner_panel.py` 전부 그대로.
- **의존.** S1 · S5, WP2(또는 D-24 계획)의 `rr_targets.flow`.
- **크기.** 4시간.

### S7 엔진 클라이언트 — 대화 없이 `card-review` 넷 (WP3b 7)

- **목적.** 포털 중계 `/agent/card-review/{limits,pack,plan,run}` 을 부르고, 응답을 S2 의 부류로 옮긴다. 대화를 만들지 않는다(나갈 기준 3). 자격은 잡이 정한 사용자 PAT 하나다.
- **파일 · 닻.**
  - `runner.py:85` `PanelEngine` 옆에 `ReviewEngine` 프로토콜, 106행 `EngineBusy` 에 `retry_after_s`, 새 `EngineRejected(code, message, *, infra, retryable, knob, detail)`. 프로토콜 · 예외의 정본이 러너인 지금 방향(engine_client 가 runner 를 import)을 지킨다.
  - `engine_client.py:249` `PortalPanelEngine` 을 물려받는 `PortalReviewEngine` · `collect_review_stream` · `build_review_engine`. `_watched`(119행)는 벽시계 코드 · 손잡이 이름을 인자로 받게 넓힌다(지금 문구에 `HWAXRISK_PANEL_TIMEOUT_S` 가 박혀 있다 — 패널 호출은 종전 값 그대로). `parse_sse` · `_StreamWatch` · `_client`(R10 루프백 처리 포함)는 그대로 쓴다.
  - `health()`(320행)가 `card_review_active` · `card_review_waiting` · `card_review.limit` 을 옮긴다.
  - 새 `tests/synth/fake_review_engine.py` — **가짜 엔진은 이것 한 벌이다**(D-15 · 운영 코드의 `stub` 손잡이 없음). WP5b C9 가 이 파일을 넓힌다.
- **계약(에이전트 서버 `card_review` 에 기대하는 모양 — WP3a 3.2~3.8 위에 PLAN §4 가 덧씌운 판).**

| 경로 | 요청 | 응답 |
|---|---|---|
| `GET …/limits` | — | `{model, ctx_tokens, ctx_source: server·env·fallback, llm_max_tokens, out_tokens, p_hard, verdict{unit_body_max, card_budget, k}, sweep{manifest_page_max, card_budget, units_per_page_max}, offcard{p, findings_max, known_max}, prompt_rev, norm_rev, limits_rev, gate{limit, busy_limit}}` |
| `POST …/pack` | `{agent_key}` | 팩(WP3a 3.4 — `cards[]{alias, record_id, card_id, title, type, checkable, confidence, causal_status, review_status, standard_refs, sources_n, sections[{sid, title, text}], text_sha, chars}`, `unrenderable`, `cards_total`, `checkable_n`, `chars_total`, `role`, `role_sha`, `pack_hash`, `norm_rev`). 404 `agent_not_found`, 502 `card_fetch_failed{failed[]}` |
| `POST …/plan` | `{agent_key, cards[{alias, record_id, checkable, chars}], units[{unit_id, body_chars, manifest_chars}]}` | `{limits_rev, verdict_decks[{deck_id, aliases[], chars, soft_over}], sweep_decks[…], manifest_pages[[unit_id…]], oversize{cards[], units[], manifest[]}}` |
| `POST …/run`(SSE) | `{kind: sweep·verdict·offcard, variant: fwd·rev·solo·null, target_key, expert{key, name, domain, role}, cards[], digest[], unit{unit_id, kind, title, summary, lines[{ref, text}], evidence[{ref, text}], notes, missing[]} 또는 null, manifest[], extra{domains, mechanisms, known}}` | 프레임 `status{step: queued·attempt, n}` · `ping{idle_s, ts}` · `result{kind, variant, rows[], missing[], extras{inj[]}, quality{expected, ok, flagged, missing, bad_lines, truncated(true·false·null), attempts, stamp, dropped_over_cap}, meta{model, ctx_tokens, prompt_rev, norm_rev, limits_rev, input_sha, prompt_chars, usage{prompt_tokens, completion_tokens}, finish_reason, queued_ms, llm_ms[], soft_over, basis, bg_dropped, aliases{cards, lines}}}` · `error{code, message, infra, retryable, knob?, retry_after_s?}` · `done` |

  - 자리가 없으면 서버는 줄을 세우지 않고 1초 안에 `review_busy`(스트림 전 429 + `Retry-After` 또는 `error{code:'review_busy', retry_after_s}`)로 답한다(C-24). 두 모양 다 `wait` 다.
  - 응답 → 예외 — 401 `PatUnavailable` · 403 `EngineRejected('forbidden')` · 404(옛 포털 · 옛 서버) `EngineRejected('review_unsupported')` · 422 `bad_request`·`over_budget{need, have, part}` · 429 `EngineBusy(retry_after_s)` · 5xx · 연결 실패 `EngineError('portal_5xx'·'portal_unreachable')` · `error` 프레임 → `EngineRejected(code, infra, retryable, knob)` · 읽기 한도 · 중간 절단 · 벽시계 · 사람의 정지 → `EngineStreamLost('engine_silent'·'engine_stream_cut'·'review_timeout'·'cancelled')`. 분류는 S2 의 `classify` 가 한다.
  - `run()` 은 `create_conversation` 을 부르지 않고 `conversation_id` 를 싣지 않는다. 단발 셋의 읽기 한도는 660초(포털 단발 600초보다 조금 크게)다.
  - 자격 — `_review_credential(email)` 은 그 사람이 등록한 PAT 만 쓴다. 남은 수명 ≤ `review_credential_margin_s` 면 `PatUnavailable('credential_expired')` 이고 서비스 PAT 로 내려가지 않는다(사용자 결정 3 · 지금 `PortalPanelEngine._credential` 266행의 서비스 강등과 다르다).
- **수용 기준.** 나갈 기준 3(대화 0건), C-12 · C-24, 사용자 결정 3, P-02(1)(`review_busy` 는 wait), m-13, D-15.
- **시험.** `httpx.MockTransport` 로 표의 줄마다 하나. `/agent/conversations` 로 가는 요청 0건. 서비스 PAT 가 어떤 요청 머리에도 실리지 않는다. SSE 표본은 에이전트 서버의 실제 `run` 이 가짜 LLM 원문으로 낸 프레임을 저장한 공유 파일(`tests/fixtures/card_review/contract/*.sse` — WP5b C7)이다. 가짜 엔진의 `run` 은 받은 카드 본문에서 실제 부분 문자열을 잘라 `cq` 로, 받은 줄 별칭을 `l` 로 돌려주고, 결함 스위치(카드 빼먹기 · 모르는 별칭 · 지어낸 인용 · `checks.quote` 거짓 · 절단 · `review_busy` N회 · `error{infra:true}` · 중간 절단 · 지연 · 자격 만료 · 창 출처 `fallback` · `oversize`)를 갖는다. 가짜 엔진의 응답 키 집합이 공유 `result` 표본과 같은지 시험이 본다.
- **의존.** S2, WP3a 계약 파일 · 포털 중계 P1(실주행만).
- **크기.** 7시간.

### S8 검토 루프 — 전문가 세션 (WP3b 8)

- **목적.** 검토 잡 하나가 계획된 범위의 셀을 끝까지 돌고, 끊겨도 차감 없이 스스로 이어 돈다(나갈 기준 3). 선점 단위는 전문가 세션이다(PLAN §4, D-8).
- **파일 · 닻.**
  - `runner.py:25` `_LOOPS` 에 `("review_loop", 2.0)`(`tests/test_runner.py:12` `THREADS` 를 같이 고친다 — m-11). `RiskRunner.__init__`(1972행)에 `review_engine=None` 과 `_review_sem`(`HWAXRISK_REVIEW_CONCURRENCY`). `_loop` 에 `review_loop` 갈래. `_begin`(2107행)이 `recover_running_panels` 바로 뒤에 `review_cells.recover_running` 을 부른다 — 러너 잠금을 쥔 프로세스만 복구한다(M1 의 규칙 그대로). `stop()` 이 검토 워커도 join 한다. `RiskRunner(store=None, settings=None)` 시험이 그대로 돈다(m-11).
  - `main.py:124` 러너 생성에 `review_engine=engine_client.build_review_engine(store, settings)`.
  - `review_runner.py` 에 `review_tick` · `run_pack` · `run_expert` · `build_request` · `JobProgress` · `should_stop_review`.
- **계약.**
  - **틱(2초).** ① `paused` 이고 자동 재개 보류 코드이며 `hold_until ≤ now` 이고 `pause_reason` 이 사람의 것이 아닌 잡을 `queued` 로(반쯤 연 상태 — 성공 하나까지 워커 하나). ② `cancelling` → `cancelled`. ③ 빈 자리 = `min(_review_sem 남은 자리, 서버 관문 limit − 내가 도는 수)`(서버 limit 은 `engine.health()` 를 30초 캐시 — P-02(3)) 만큼 워커를 띄운다. ④ 단계 — `pack`(범위 안 전문가의 팩이 전부 `ok·empty·한도 초과` 가 될 때까지) → `review` → 범위 안 `pending·running` 이 0 이면 `completed`(열린 실패 N 은 `progress_json.cells.failed` 와 `error` — C-18). 팩 받기도 워커 자리에서 한다(루프 스레드가 HTTP 를 붙들지 않는다 — m-04, 셀보다 먼저 전부 얼린다 — WP5a 3.3.6).
  - **창 확인.** 틱마다 `/limits` 를 한 번(60초 캐시). `ctx_source='fallback'` 이면 새 호출을 내지 않고 `progress_json.waiting{reason:'ctx_fallback'}`, 600초 이어지면 `ctx_unknown` 보류와 '무엇을 적어야 하나'(에이전트 서버의 창 설정) 문구. plan 의 `oversize` 가 비지 않으면 다시 쪼개지 않고 `ctx_too_small` 보류(그 단위 · 카드 · 박스의 창을 적는다 — D-22). `limits_rev` 가 바뀌면 그 전문가의 계획을 다시 받고 `input_hash` 가 바뀐 셀만 처음부터.
  - **전문가 세션(`run_expert`).** 셀을 집을 때 `input_hash = sha256(unit_hash|pack_hash|prompt_rev|limits_rev)[:16]` 를 다시 셈해 다르면 그 셀의 판정을 지우고 처음부터(`reopened_n+1`). 이미 결과가 있는 호출은 다시 부르지 않는다. 호출과 호출 사이마다 `should_stop` 을 묻는다.

| 순서 | 호출 | 몇 번 |
|---|---|---|
| 1 | `sweep` | `card_basis ∈ cards·background` 이면 늘(묶음 × 쪽). 실패해도 분류에 안 쓰므로 진행한다(`sweep_state='failed'`) |
| 2 | `verdict·fwd` | 점검 묶음마다 × 범위 안 셀마다, 묶음 먼저 · 단위 나중 |
| 3 | `verdict·fwd`(빠진 카드만) | 셀마다 최대 2번 |
| 4 | `verdict·rev` | 전량(같은 본문이면 부르지 않고 `solo` 로 — X1-20) |
| 5 | `verdict·solo` | `fwd≠rev` 인 카드, 1장 묶음의 이중 판정, 실효 FAIL·WARNING — 카드마다 1번, 앞 판정을 싣지 않는다 |
| 6 | `offcard` | 셀마다 1번. `cards` = 배경 카드 **전부**(훑기 `k` 에 걸린 것 먼저, 나머지 팩 순서 — 서버가 넘치는 꼬리를 제목으로 내리면 `bg_title_only_n` 에 적는다, P-03 · X1-11), `digest` = 전 카드 제목, `extra.known` = 그 셀의 실효 판정(FAIL·WARNING 먼저, 상한은 `limits.offcard.known_max`, 넘친 수를 호출 원장에 적는다). `f` 줄 수가 `findings_max` 와 같으면 받은 제목을 `known` 에 더해 '이것 말고 더' 를 최대 3번 다시 묻는다(`offcard_capped` — X1-16) |
| 7 | 셀 정산 · 전문가 마감 | 범위 안 열린 셀이 0 이면 S9 |

  - `card_basis='none'` 이면 1~5 없이 6 만 역할로 부른다(`basis='role_only'`, 검색은 M3).
  - `build_request` 가 새로 쓰는 글은 `unit.notes`(좌석 계약 `_common` 의 데이터 의미 문장, 린터 통과) 하나다. `unit.lines` · `evidence` 는 WP2 `units.review_payload` 의 것 그대로이고 앱이 줄이지 않는다. `extra.mechanisms` 는 `assets/taxonomy.v1.json`, `extra.domains` 는 로스터 영역 15개다.
  - **결말 처리(S2 의 부류).** wait — 셀 · 전문가를 놓지 않고 `stop.wait(retry_after_s)` 뒤 같은 호출, `progress_json.waiting{reason, since, retry_at}` 만 적는다. infra — 그 셀 `pending` + `not_before`, 전문가를 `planned` 로 놓고 워커가 끝난다. content — `charged+1`(한도 2), 한도면 `failed(<code>)`. job — 셀 차감 없이 `pending`, 잡 `paused` + `hold_code`. 셀당 호출 수 상한 `tries ≥ 3 × (2·묶음 수 + 점검 카드 수 + 4)` 이면 `failed('call_cap')`(m-02).
  - **팩 한도 초과.** `agent_not_found` 3번 · 502 6번을 넘긴 전문가의 범위 안 셀은 `failed('agent_not_found'·'pack_unavailable')` 로 옮겨 잡이 닫힐 수 있게 한다(X1-25). 범위 안 전원이 502 면 `aidh_unreachable` 보류.
  - **차단기.** 호출이 끝날 때마다 `breaker_verdict`(S2). `llm_outage` 는 자동 재개, `content_fail_rate` 는 아니다. 잡의 `check_disagree` 가 5 를 넘으면 `contract` 보류(X1-21).
  - **멈춤 물음(`should_stop_review`).** `cancelling·cancelled`, 사람의 `paused`(`hold_code='user'`), 러너 종료(`_stop`)면 스트림을 닫는다(셀 `pending`, 아무것도 세지 않음). 코드 보류(`llm_outage` 등)는 도는 호출을 닫지 않고 다음 호출을 시작하지 않는다(P-02(4) — 지금 `runner._stop_reader` 1686행은 `paused` 면 무조건 닫는다).
  - **재기동 복구(`recover_running`).** 셀 `running→pending`, 전문가 `running→planned`, 호출 `running→aborted('restart')`, 검토 잡은 `running` 그대로(멈추지 않는다). 차감도 `not_before` 도 없다. 검토 호출은 분리 태스크가 아니므로 겹칠 심의가 없다.
  - **자격.** 호출마다 잡 `params.credential.email` 의 PAT 를 다시 고르고, 못 쓰면 `credential` 보류와 '포털에서 PAT 를 다시 발급해 등록하고 재개한다 — 서비스 계정으로 내려가지 않는다' 문구.
  - **진행 신호(`progress_json`, 60초 간격 · 단계 · 차단기 · 워커 변화는 즉시).** `{mode, phase, packs{total, ok, empty, error}, experts{…}, cells{total, by_state, by_basis, in_scope, failed}, calls{ok, infra_fail, content_fail, wait, aborted, last_ok_at, avg_ok_s}, workers[{agent_key, unit_id, call_kind, variant, deck_id, started_at, last_frame_at, last_event_at, last_step}], breaker{state, trips, hold_until}, waiting, server{active, limit}}`. 설계서의 `sweep.filter·miss_rate`·`eta` 는 M4 다.
- **수용 기준.** 나갈 기준 1 · 3, C-18 · C-24 · C-26, D-8 · D-9 · D-10 · D-22, P-02 · P-03 · P-04 · P-08 · P-09 · P-10, m-02 · m-03 · m-04 · m-11 · m-13, X1-11 · X1-16 · X1-20 · X1-22 · X1-25, PLAN §4 '모델 창'.
- **시험(가짜 엔진, 실제 단위 · 실제 팩 픽스처).** 끝까지(전문가 6명 — 배경뿐 1 · 카드 0장 1 포함 — × 단위 4, 잡 `completed`, 셀 전부 종결, 호출 원장 `ok` 수가 계획과 같음). 대화 0건. 패널 규칙에 안 닿음(`risk_daily_panel_cap=1`, `rr_panels` 0행, 같은 타깃 동시 진입 최댓값 ≥2). 묶음 먼저 순서. 멱등(끝난 범위로 다시 만든 잡의 `run` 0회). 재기동(호출 중 러너를 세우고 새 러너 — `charged` 0, 끊긴 호출만 다시, 사람 손 없이 `completed`). `review_busy` 를 동시 2 초과에 주는 가짜 엔진 — `infra_streak` 0 · 차단기 닫힘 · `completed`(P-02(5)). 인프라 연속 → `llm_outage` → 시계를 밀면 반쯤 연 재개. 내용 탓 급등 → `content_fail_rate` 이고 스스로 안 돌아옴. 취소 · 정지 · 재개. `scope.unit_ids` 잡 → 보고서 있음 · 원장 `pending`(P-04). 팩 502 한 명 → 그 사람 셀만 `failed`, 전원 → `aidh_unreachable`. 0장 첫 응답 · 30장 둘째 응답 → `ok`(P-08). 창 출처 `fallback` → 기다림 → 600초 뒤 `ctx_unknown`. `oversize` → `ctx_too_small`. 자격 만료 → `credential` 보류 · 서비스 PAT 0회. 모든 카드가 어느 호출의 `cards` 에 한 번은 전문으로 실렸다(P-03). 잡 둘이 번갈아 집힘(P-09). 차단기 보류 중 사람의 `pause` 가 유지됨(P-10). 이 모든 시험 뒤 옛 타깃 골든과 합성 패널 셋 연속 `done` 이 그대로다(D-24).
- **의존.** S5 · S6 · S7, WP2 `units.review_payload`(줄 목록) · `units.packets`(훑기 목록).
- **크기.** 15시간.

### S9 finding 승격 · 의견 행 · 원장 마감 (WP3b 9)

- **목적.** 전문가 마감 한 트랜잭션에서 finding · 의견 행 · 원장 행 · 보고서(S10)를 쓴다. 다시 마감해도 같은 자리다.
- **파일 · 닻.** `expert_report.build_findings`(새), `review_runner.finalize_expert`(새), `narrative._normalize_finding`(1161행 — 그대로 태운다), `narrative._opinion_id`(1659행), `narrative.NONLEDGER_CYCLE_BASE = 100000`(1656행) 옆에 `REVIEW_CYCLE_BASE = 500`, `metrics.panel_models`(466행), `registry._load_findings`(159행) · `registry._contested_marking_done`(882행) · `brief.py:1307`(타깃의 메커니즘 수).
- **계약.**
  - 원천 — 실효 FAIL·WARNING(카드 근거), 실효 `undetermined` 이면서 `split = 1`(가장 무거운 변형을 `judgement_claimed` 로 — X1-14), 카드 밖 `f` 줄(`dir` 에 따라 risk·improvement). `undetermined`·`need` 는 finding 이 아니라 보고서 '필요한 추가 정보' 다.
  - 변환은 설계서 §3.10.2 표 그대로이고 바꾸는 것은 넷이다. `warrant` 는 "근거 카드 [card:<record_id>] «<cq>»"(P-05). `cites` 는 상한 없이 통과한 것 먼저(D-21). 정규화 뒤 card 행의 `canonical` 을 떼어 낸다(P-06). `claim_uid = f"{review_id}#{'G' 또는 'F'}{int(sha1(cluster_key+'|'+unit_id)[:12], 16)}"`(m-06 — 스키마 패턴 `[FG][0-9]+` 그대로).
  - 정책은 `hold` 하나다(사용자 결정 2). 등록부로 갈 판정은 WARNING 까지, 심각도는 중대까지이고 원래 값은 `judgement_claimed`·`severity_claimed` 에 남는다. `direct` 갈래는 만들지 않는다.
  - 쓰기 — 셀 안에서 `(cluster_key, direction)` 으로 접는다. `INSERT … ON CONFLICT(finding_id) DO UPDATE SET <코드가 정하는 열만>` — `status*` · `recall_eligible`(사람 승인 뒤) · `ra_entity_id` · `adh_record_id` · `created_at` 은 건드리지 않는다(P-12). 새 집합에 없는 `<review_id>#…` finding 과 그 `rr_claim_refs` 를 지운다. `rr_findings` 의 v4 열 넷(`unit_id`·`source_kind='card_review'`·`source_id=review_id`·`agent_key`)을 채우고 `panel_id` 는 NULL, `raised_by = [agent_key]`. `extras.inj` 가 있는 셀의 finding 과 M2 의 검토 finding 전부는 `recall_eligible = 0`(열린 물음 6). 택소노미 밖 메커니즘은 타깃 안에서 같은 원문을 한 번만 큐에 올린다.
  - 의견 행 — `seat_opinion.v1` 필수 칸 전부(`contested_finding_ids: []`, `character_sentences: []` 포함 — m-11). `panel_id = review_id`, `cycle = 500 + rr_coverage.cycle`, `origin='primary'`, `turns[0] = {round: 1, say: summary_md, say_excerpt: 2,000자(줄였으면 원문 길이 표식), position: '', stance, non_negotiable: ''}`, `final_stance` 는 FAIL → oppose, WARNING·카드 밖 리스크 → conditional, 보류뿐 → abstain(X1-15), 그 밖 → agree. `DELETE … WHERE panel_id = review_id` 뒤 INSERT.
  - 원장 — S5 의 `close_review_seat`(`flow='cells'` 대상만).
  - M2 에서는 등록부에 병합하지 않는다. 같은 타깃의 패널 경로가 검토 finding 을 읽지 않게 `registry._load_findings` · `_contested_marking_done` · `brief.py:1307` 에 `COALESCE(source_kind,'') <> 'card_review'` 를 건다(열린 물음 4 — 병합 · 지지 수는 M3 의 WP4).
  - `metrics.panel_models` 가 `rr_findings.source_id → rr_expert_reports.model` 을 합쳐 본다.
- **수용 기준.** 사용자 결정 2, P-05 · P-06 · P-07 · P-12, m-06 · m-11 · m-16(병합하지 않으므로 선례 통계가 부풀지 않는다), X1-14 · X1-15, D-24(패널 등록부 불변), C-7(검토 의견 500 대역 < 원장 밖 100000).
- **시험.** 같은 전문가의 카드 3장이 같은 변경 · 같은 메커니즘이면 finding 하나에 `cards[]` 3건. 전문가 12명이 같은 클러스터면 `raised_by` 가 서로 다른 한 명씩. finding 하나가 빠진 뒤 다시 마감해도 남은 id 가 같다. 라벨로 `verified` 가 된 finding 이 다시 마감 뒤에도 `verified`(P-12). `hold` 에서 등록부로 갈 값이 WARNING · 중대이고 `judgement_claimed='FAIL'`. 의견 행이 스키마를 통과하고 cycle 이 501 이며 같은 전문가의 패널 의견(cycle 1)과 함께 들어간다. 패널을 돌린 타깃에 검토를 얹어도 `registry.merge` 결과 · `close_level` 이 바이트로 같다. 반출 JSONL 에 카드 절 본문이 없다. 입력은 전부 S8 의 루프를 가짜 엔진으로 돌려 만든 원장이다.
- **의존.** S4 · S5 · S8.
- **크기.** 7시간.

### S10 전문가별 보고서 (WP3b 10)

- **목적.** 판정 행 · 셀 · 호출 원장 · 얼린 팩에서 전문가 한 명의 상세 보고서를 코드로 조립한다(LLM 0회). 사용자가 형식을 승인하는 대상이다(나갈 기준 4).
- **파일 · 닻.** 새 `app/expert_report.py` — `REPORT_REV` · `build_report` · `load_report` · `render_report_md(report, *, unit_id=None, part='full')` · `render_pages(report, page_chars)` · `summary_md`. 지금 코드에 선례는 `registry.split_rich_text`(120행)와 `render.lint_text`(259행)다.
- **계약.**
  - 절은 설계서 §3.11.1 에서 `input_gap` 을 뺀 것이다 — `head`(이름 · 영역 · 순위 · tier · review_id · 모델 · prompt_rev · norm_rev · verify_rev · report_rev · 카드 묶음 `{pack_hash, 점검 n · 배경 n · 본문 없음 n, card_basis}`) · `scope`(단위마다 상태 · 무엇으로 봤나 · 판정별 수, 끝에 **보지 못한 것** — 실패 · 범위 밖) · `checklist`(점검 카드 × 대조한 단위마다 실효 판정 한 행, 생략 없음) · `background` · `unjudged_cards` · `by_unit`(FAIL → WARNING(단독 재질의의 조건별 대조 · 영향 경로 · 닫는 확인) → 보류(필요 자료) → 걸림 없음 순) · `off_card` · `handoff` · `needs_info` · `mechanisms` · `findings` · `quality`(S11 의 전문가 몫).
  - 판번호와 만든 시각은 JSON 에 넣지 않고 행의 열(`revision`·`finalized_at`)에만 둔다. 같은 원장이면 같은 바이트이고 해시가 바뀔 때만 `revision+1`(m-07).
  - 인용 표시는 판정당 200자다(사용자 결정 1). 넘으면 `…(cq N자 중 200자)` 를 붙인다. 행마다 `card:<record_id>#<section_id>` 와 `quote_ok` 를 실어 사람이 카드 원문과 대조할 수 있게 한다(나갈 기준 4 — 인용 10개 대조).
  - 코드가 쓰는 문장은 린터를 지나고 표기는 WP5b 3.11.3 의 낱말(걸림 없음 · 보류 · 미완)을 쓴다. 전문가의 글은 «» 로 감싼다.
  - `summary_md` 는 의견 행 `excerpt_for_rag` 의 원천이라 1,500자이고, 줄였으면 원래 길이를 적는다. 보고서 본문은 자르지 않는다.
  - 쪽 나누기 — `render_pages` 가 마크다운을 쪽(기본 25,000자 — Claude Code 의 MCP 결과 상한을 바깥 한도로 보고 쪽으로 나눈다, truncation.md 원칙)으로 가르고, 블록 모양은 WP4 의 통합 보고서 쪽 `{page_no, kind, title, blocks{background[], results[], recommendation[], minutes[]}}` 와 같게 둔다(PLAN §4 REST — 응답 키를 WP4 모양으로).
- **수용 기준.** 나갈 기준 4, 사용자 결정 1, m-07, D-21(본문 무절단), X1-03(보고서에 '카드 판정 N/N' 만 따로 싣지 않는다 — S11 의 폭포를 쓴다), C-16(범주 접기 한 곳).
- **시험.** 같은 원장에서 두 번 조립한 바이트가 같다. 점검표 행 수 == 실효 판정 행 수. 200자 넘는 `cq` 에 길이 표식. 코드 문장 린터 위반 0. 쪽을 이어 붙이면 `full` 마크다운과 같다. 원장은 S8 루프가 만든 것이다.
- **의존.** S9 · S11(품질 절).
- **크기.** 6시간.

### S11 품질 수치 모듈

- **목적.** 원장에서 품질 수치를 계산해 진행 응답 · 전문가 보고서 · M2 실측표가 같은 수를 읽게 한다(C-29). 나갈 기준 5 의 원천이다.
- **파일.** 새 `app/review_quality.py` · 새 `app/assets/review-quality.v1.json`(기준판 `rq-1`) · 새 `app/audit.py`(`binom_upper(k, n)` 하나 — 정확 이항 단측 95%, WP4 가 M3 에 같은 파일을 넓힌다 — X3 cuts).
- **계약.** `compute(store, target_key, *, agent_key=None) -> {policy_version, model, prompt_rev, limits_rev, ledger_hash, grid, cards, truncation, citation, flips, seconds, pilot, out_of_bounds[]}`. 값마다 `{value, num, den, upper95?, threshold?, within?}` 이고 표본이 `min_n` 미만이면 `value = None`(0 으로 적지 않는다). `block(store, target_key)` 는 `{key:'quality', title, text, json}` 이고 셀이 없는 옛 타깃에는 한 줄만 낸다.

| 칸 | 정의 |
|---|---|
| 격자 | 셀 상태별 수, `reviewed` 의 `basis` 별 수(X1-04), 범위 안 · 밖, 전문가 상태별 수 |
| 카드 | 폭포 — 분모 = Σ(전문가 팩의 카드 전부) × 검토 대상 단위. 줄 = 카드별 판정 받음 · 배경(판정 대상 아님 — 전문으로 읽힘 · 제목만) · 본문 없음 · 실패 · 범위 밖 셀. `judged/expected`(늘 100%)는 불변식으로만 둔다(X1-03) |
| 절단 | `output_truncated` 1 · 0 · NULL(모름) 호출 수(X1-22), 품질 한도를 넘긴 호출(`soft_over`), 카드 밖 줄 상한에 닿은 수(`offcard_capped`·`dropped_over_cap`) |
| 인용 | 카드 인용 통과율 — 분모 = 실효 판정 행 전부, 걸림 · 걸림 없음 따로(X1-06). 변경 줄 참조 통과율 — 분모 = `applies='yes'` 실효 행. `check_disagree` 수 |
| 뒤집힘 | 순서 — `fwd` 와 `rev` 가 다른 카드 / `agree` 가 NULL 이 아닌 카드(같은 본문으로 건너뛴 것 제외 — X1-20). 단독 — 걸림 → 걸림 없음 · 걸림 없음 → 걸림(모집단을 갈라 낸다 — X1-14), `split` 수 |
| 호출 초 | 종류(`sweep`·`verdict/fwd·rev·solo`·`offcard`)별 `duration_ms` 의 p50 · p95 · 최대, `queued_ms` 와 기다림 수를 따로 |
| 실측(pilot) | 셀당 호출 수, 양성 비율(실효 걸림 / 실효 행), 훑기 '무관' 비율(`rel=no` 단위 / 훑기 단위 — 분류에는 안 쓴다), 토큰(입력 · 출력 합과 자/토큰 비 = `prompt_chars / tokens_in`), 타깃의 새 표 바이트(표마다 `SUM(length(…))`) |

  - 챗 첫 응답 지연은 이 모듈이 재지 않는다. 그동안의 포털 · 에이전트 서버 로그에서 따로 잰다(실측표 항목 — 열린 물음 없음, 절차서 몫).
  - 진행 응답에 실을 때는 `JobProgress` 가 60초마다 계산해 `progress_json.quality` 에 넣은 값을 읽는다(5초 폴링이 매번 계산하지 않게).
- **수용 기준.** 나갈 기준 1(격자 · 카드 누락 · 절단이 수로 보인다) · 2(인용 통과율) · 5, C-29, X1-03 · X1-04 · X1-06 · X1-14 · X1-20 · X1-22, WP5b 3.11.3 숨기지 않는 규칙 여섯.
- **시험.** 지표마다 손으로 센 작은 원장(S8 루프로 만든 원장)과 값이 같다. 문면의 수 == `json` 의 수. 문면 린터 위반 0. 표본 미달은 null 과 n. 옛 타깃은 한 줄.
- **의존.** S8(원장) · S9.
- **크기.** 6시간.

### S12 REST · MCP (WP3b 11)

- **목적.** 웹과 Claude 가 같은 함수로 검토를 시작하고 지켜보고 보고서를 읽는다(D-23 — 입구 둘, 원장 하나).
- **파일 · 닻.** `routes.py:2170` `JobBody` · 2182행 `create_job` 라우트, 2267행 `coverage_payload`, 새 라우트 넷. `mcp_server.py` 의 새 도구 둘과 `risk_start_job`(354행) 인자. `entry.start_job`(319행) · `entry.next_step`(475행 — 잡 단계의 지켜볼 도구). `.portal/manifest.yaml` 의 `mcp.description`. `tests/test_mcp_tools.py` · `tests/test_no_write_tools.py` · `tests/test_p6_routes.py` · `tests/test_mcp_entry.py`.
- **계약(REST 한 벌 — PLAN §4).**

| 경로 | 무엇 |
|---|---|
| `POST /targets/{key}/jobs` | 본문 + `mode`(`panels` 기본 · `reviews`) · `scope{tiers?, domains?, agents?, unit_ids?}`. `tier` 는 `reviews` 에서 생략 가능(m-11). `reviews` 는 S5 의 `create_review_job` 으로 가고 `consent_source` 는 지금 `CONSENT_SOURCES` 규칙 그대로 |
| `POST /jobs/{job_id}/{pause·resume·cancel}` | 그대로(S6 의 보류 열 규칙) |
| `GET /targets/{key}/coverage` | 기존 칸 불변 + `review`(셀이 없는 타깃은 null) — `{units, cells{total, by_state, by_basis, in_scope, out_of_scope_pending, failed_open}, experts{total, by_state}, cards(폭포), quality(요약), job{id, mode, state, hold_code, hold_until, hold_n, error, credential_email, phase, progress, waiting, signal{workers[… frame_idle_s, event_idle_s]}}}`. `/review` 경로는 만들지 않는다 |
| `GET /targets/{key}/cells?agent_key&unit_id&domain&state&limit(500, 최대 2000)&offset` | `{target_key, total, limit, offset, next_offset?, rows[]}` — 행 열은 S1 의 이름 그대로 |
| `GET /targets/{key}/cells/{unit_id}/{agent_key}` | 셀 + 판정 행 전부(변형별) + 호출 목록(`result` 본문 제외) |
| `GET /targets/{key}/experts?domain&state` | 머리 목록 |
| `GET /targets/{key}/experts/{agent_key}/report?format=json·md&part=summary·units·cards·full&unit_id&version&page` | `{target_key, agent_key, state, version(=revision), report_hash, finalized_at, coverage_status, opinion_id, review_id, pages_total, page_no, next_page?, page{…}}` 또는 `format=json` 이면 S10 의 JSON 전체 |

  - 읽기는 지금 관례(`_target_row(target_key, owner_sub)`), 쓰기는 `require_role(… 'editor')` + `rr_audit`(scope `job`). 새 경로는 전부 DB 읽기 · 짧은 쓰기다(`/apps/` 프록시 600초).
  - MCP — 읽기 도구 둘 `risk_get_cells(target_key, agent_key=None, unit_id=None, state=None, limit=200, offset=0)` · `risk_get_expert_report(target_key, agent_key, part='summary', unit_id=None, page=1)`. `risk_start_job` 에 `mode='panels'` · `scope=None` 을 더한다(새 도구를 만들지 않는다 — 쓰기 · 위임 확인 · 동의 설명은 지금 문구 규칙 그대로). `risk_get_coverage` 는 `coverage_payload` 를 그대로 써서 `review` 가 저절로 붙는다. `risk_next_step` 은 검토 잡이 있으면 지켜볼 도구로 `risk_get_coverage`(review) · `risk_get_cells` · `risk_get_expert_report` 를, `credential`·`ctx_*`·`agent_outdated` 보류면 그 막힘과 고칠 곳을 낸다. 대상을 열 때 두 방식을 나란히 보이는 것은 D-24 계획(WP2 3·4)의 몫이다.
  - 도구 수는 26 → 28 이다(WP2 의 `risk_get_units` 까지 29). PLAN §4 C-30 의 '17종' 은 M1 의 입구 12종 전의 셈이다.
- **수용 기준.** PLAN §4 REST · C-30(새 도구 셋 중 둘), D-23 · D-24, m-11, X1-27(분모), 나갈 기준 4(보고서가 웹 · Claude 양쪽에서 읽힌다).
- **시험.** 응답 필드를 스냅샷 시험으로 못 박는다(프런트 세션의 계약). 남의 타깃은 404 · `not_visible`. `TOOL_NAMES` · `CALLS` · `_INSTRUCTIONS` 갱신. 쓰기 도구 목록 불변(`risk_start_job` 은 이미 쓰기). 위임 단언 없는 Bearer 로 `risk_start_job(mode='reviews')` 는 `delegation_required`. 쪽을 다 받으면 `part='full'` 과 같다.
- **의존.** S8 · S10 · S11.
- **크기.** 6시간.

### S13 리허설 · v4 확정 · push · cae00 파일럿 지원

- **목적.** v4 를 dev 리허설로 검증한 뒤에만 push 한다(C-2 · D-7). M2 나갈 기준을 cae00 실제 타깃에서 댈 수 있게 한다.
- **차례.**
  1. 리스크 앱 시험 전체(`cd backend && .venv/bin/python -m pytest -q`)와 형제 리포 계약 파일 해시 가드.
  2. dev 실 LLM 실주행 — 임시 데이터 디렉터리 · 임시 포트의 로컬 코드(push 전이라 SIF 가 아니다), 합성 과제는 `tests/synth/inject_dev.py` 로 넣고, dev 포털 중계 · 에이전트 서버 `card_review`(WP3a 가 먼저 올라가 있어야 한다)를 부른다. 전문가 3명 × 가장 작은 단위 2개. 대화 0건 · 판정 행 수 == 카드 수 · 도는 중 임시 프로세스를 죽였다 띄워도 차감 없이 `completed` 를 본다. 판정의 질은 보지 않는다. dev 창(16,384토큰)에서 단위가 넘치면 `ctx_too_small` 거절이 나는 것 자체를 확인하고 열린 물음 11 로 간다. 하네스는 절대경로를 쓰고 `pkill -f` 를 쓰지 않는다.
  3. 리허설이 표 모양을 바꾸라고 하면 v4 DDL 을 고친다(push 전이라 고칠 수 있다). `PUSHED_DDL_SHA256[4]` 를 굳힌다.
  4. push → hwax-risk SIF → dev 인스턴스 교체(`apptainer instance list` 출력에서 이름을 확인하고 내린다, 다시 올리는 것은 허브에 맡긴다 — m-15) → 이행 사본 `pre-migrate-v3-*` 확인 → 게이트웨이 `tools/list` 에서 `risk_get_cells`·`risk_get_expert_report` 를 실제로 본다.
  5. cae00 파일럿(사용자) — M0-d 의 실제 변경 비교 타깃, `scope.agents` 로 입력 결손이 아닌 영역 대표 9명 × 검토 대상 단위 전부, 이중 판정 전량. 사람 몫은 마일스톤 절차서(출력 문구 기준)에 적는다.
- **수용 기준.** 나갈 기준 1~5 의 증거를 모은다(아래 표).
- **의존.** S1~S12, WP3a 1~7 · 포털 P1 의 dev 배포, WP2 의 단위.
- **크기.** 8시간(cae00 벽시계 · 사용자 시간 제외).

### 나갈 기준 대응

| 나갈 기준 | 지키는 걸음 | 보는 곳 |
|---|---|---|
| 1 격자 완전 · `reviewed` 셀 카드 누락 0 · 절단 0 | S1 · S5 · S8 · S11 | `review_invariants` 빈 목록, `coverage.review.cells`, 품질 '격자 · 카드 · 절단' |
| 2 판정 카드 = 그 호출에 실은 카드, 통과 인용은 얼린 원문에 | S3 · S4 · S8 | `accept_rows` 의 `dropped`·`check_disagree`, 불변식(판정 행 `call_id` 의 `cards_json` ⊇ 그 별칭), 품질 '인용' |
| 3 포털 대화 0건 · 앱 재기동에도 차감 없이 이어 돔 | S7 · S8 | 포털 대화 목록, 셀 `charged` 0 · `aborted('restart')` 호출만 다시 |
| 4 전문가 보고서 9편 · 사용자가 3편 읽고 인용 10개 대조 | S9 · S10 · S12 | `GET …/experts/{agent}/report`, `risk_get_expert_report`, 행마다 `card:<record_id>#<sid>` |
| 5 실측표 갱신 | S11 | 품질 '호출 초 · 실측' 칸, 새 표 바이트 |

### 크기 합

S1 5 · S2 3 · S3 4 · S4 8 · S5 9 · S6 4 · S7 7 · S8 15 · S9 7 · S10 6 · S11 6 · S12 6 · S13 8 = **88시간**. PLAN §8 의 M2 어림(약 110시간)은 WP3a · WP2 · 포털 · WP5a R5 · WP5b 걸음까지 합친 값이라, 이 계획만으로 그 8할이다. M2 전체는 150시간 안팎으로 본다.

## M1 이후 달라진 것

- **스키마는 v3 이다.** `rr_panels.result_gz·result_hash·result_saved_at`(`risk_store.py:572`). v4 를 더하는 커밋은 `tests/test_store.py:232` `PUSHED_DDL_SHA256` 에 해시를 적어야 초록이다. `rr_jobs` 에는 아직 `mode·hold_*` 가 없다 — WP5a 의 'v3 통합 초안' 은 나가지 않았으므로 v4 가 더한다. `rr_findings` 의 네 열(WP4)도 없다 — v4 로 당긴다.
- **설계서의 걸음 둘이 이미 끝났다.** `busy_timeout`(`BUSY_TIMEOUT_S = 30`)과 러너 잠금(`runlock.RunnerLock` · `boot_id`, `RiskRunner.start → _await_lock → _begin`)이다. 셀 복구는 `_begin` 안, `recover_running_panels` 뒤에 건다. 잠금을 못 쥔 까닭을 가르지 않는 것(m-12 — `runlock.acquire` 가 모든 `OSError` 를 '못 쥠' 으로 본다)은 남아 있다. 이 계획의 범위는 아니다.
- **원장 밖 좌석 회차는 100000 + panel_no 다**(`narrative.NONLEDGER_CYCLE_BASE`). 설계서가 적은 WP1(1000)·WP4(100000) 의 어긋남은 100000 으로 풀렸다. 검토 대역 500 과 겹치지 않는다.
- **결과 선저장 · 다시 저장 · 포기가 생겼다**(`runner.save_panel_result` 1426행 · `repersist_panel` 1497행 · `abandon_repersist` 1027행 · `awaiting_repersist` 1006행). 다시 저장을 기다리는 패널은 좌석을 `pending` 으로 돌려놓은 채 남는다. 검토 마감이 그 좌석을 닫으면 다시 저장이 `seats_moved` 로 영영 거절된다 — 그래서 S5 에 409 `repersist_pending` 을 두었다(설계서에 없던 충돌).
- **러너 함수의 자리가 옮겨졌다.** `claim_next_job` 931행 · `recover_running_panels` 1050행 · `_stop_reader` 1686행 · `_progress_writer` 1712행 · `RiskRunner` 1969행이다(설계서의 714·764·1193·1219·1456행). `_stop_reader` 의 `STOP_JOB_STATES` 는 `paused` 면 무조건 스트림을 닫는다 — 검토 잡의 코드 보류에는 그대로 쓸 수 없다(S8).
- **패널 잡이 소유자 자격 → 서비스 계정으로 내려간다**(`resolve_credential_with_note` 305행, `PortalPanelEngine._credential` 266행). 사용자 결정 3 은 검토 잡에서 이 강등을 막으라 한다 — 검토 경로는 그 함수들을 쓰지 않고 자기 자격 함수를 둔다(S5 · S7).
- **Claude 입구가 생겼다.** MCP 도구가 26종이다(읽기 14 + 입구 12, `mcp_server.py`, 쓰기는 `entry.require_delegate` 로 위임 단언만). 검토 잡도 `risk_start_job` 하나로 세운다. `consent_source`(`routes.CONSENT_SOURCES` — web·mcp·api)를 검토 잡에도 남긴다. PLAN §4 C-30 의 도구 수(17)는 낡았다 — M2 끝은 29다.
- **`narrative` 의 판들이 바뀌었다.** 인용 정규화는 `render.norm_quote`(R-40), 수치 대조는 값 집합(`_numbers_in`, R-41), 등급 규칙은 판이 있다(`GRADE_RULES = "cites-2"` · 소급 없음 D-19), 확인 못 한 card 인용은 등급을 올리지 못한다. 카드 갈래는 이 위에 얹는다. 의장 출력의 모양 맞추기(`_coerce_shapes`, D-25)는 패널 결정문 전용이고, 카드 대조 행에는 같은 교훈(문자열 하나를 글자로 쪼개지 않는다)만 `accept_rows` 에 옮긴다.
- **`_resolved_cites` 가 여전히 `payload`·`canonical` 을 `finding_json` 에 싣는다**(`persist_panel_result` 의 `json.dumps(atom)` — 2047행). P-06 은 카드 갈래에서만 막는다. `_panel_scope` 는 여전히 `call_ids` 를 채우지 않는다(P-07 — 검토 쪽 `review_scope` 만 채운다).
- **시험 바닥이 생겼다.** C0 옛 타깃 얼리기는 끝났다(`tests/rr/test_legacy_flow.py` · `tests/fixtures/legacy/` — checklist 의 미체크는 낡은 표기다). 합성기(`app/devseed.py`) · 공장(`tests/factories.py`) · 씨앗 출처 래칫(`tests/rr/test_fixture_provenance.py`) · dev 주입(`tests/synth/inject_dev.py`)이 있어 손으로 쓴 입력 없이 단위 · 원장을 만들 수 있다.
- **매니페스트 `launch.env` 는 두 키로 못 박혀 있다**(`tests/test_manifest.py:68`). 검토 손잡이는 코드 기본값으로 두고 매니페스트에 적지 않는다.
- **창은 1,048,576토큰(cae00)이고 작은 창 장치는 만들지 않는다**(D-21 · D-22). 설계서의 '묶음 반 나누기' · '단위 본문 상한으로 다시 빌드' 는 `ctx_too_small` 거절로 바뀐다. 포털 메시지 한 칸은 이제 4,194,304자지만 카드 대조는 `/agent/chat` 을 쓰지 않으므로 무관하다.

## 열린 물음

1. **카드 원문 복제와 인용(사용자 결정, M2 앞).** 권고 — 얼린 카드 전부를 `rr_card_packs` 에 두고 반출에서 뺀다. 판정 행의 `cq` 는 원문 그대로 두되(재대조에 필요하다) 보고서 표시와 반출에서는 판정당 200자로 줄이고 원래 길이를 적는다. 호출 원장 `result_gz` 는 반출에서 뺀다. DB 백업(Drive)에는 실린다 — 그것까지 빼려면 백업 경로를 따로 고쳐야 하고 이번 범위 밖이다.
2. **FAIL 하나로 과제 판정을 올리나(사용자 결정, M2 앞).** 권고 — 올리지 않는다. 정책은 `hold` 하나이고 `direct` 를 만들지 않는다. 보고서와 판정 행에는 FAIL 이 그대로 보인다. 여럿이 FAIL 로 본 클러스터를 쟁점으로 올리는 일(X1-18 · X4-10)은 M3 의 WP4 다.
3. **자격 만료(사용자 결정, M2 앞).** 권고 — 검토 잡은 시작할 때부터 사용자 PAT 만 받는다(서비스 PAT 는 패널 경로에만 남는다). 도중에 수명이 여유 밑으로 내려가면 `credential` 로 멈춘다. '알린다' 는 잡 `error` · `coverage.review.job.hold_code` · `risk_next_step` 의 막힘으로 보이는 것을 뜻한다(메일 · 푸시 통로는 앱에 없다). 예상 소요가 PAT 남은 수명보다 길면 잡을 만들 때 `credential_note` 로 미리 말한다.
4. **M2 에서 등록부에 병합하나.** 권고 — 하지 않는다. `rr_findings` 와 `rr_claim_refs` 에는 쓰고(보고서 · `risk_claims_for_ref('card:…')` 가 읽는다), 같은 타깃의 패널 경로가 그 finding 을 읽지 않게 거른다. 지금 식으로 병합하면 지지 수가 원자 수로 부풀고(m-16) 패널을 돌린 대상의 등록부가 비교 도중 바뀐다(D-24). 병합 · 지지 수 · 정리(P-13)는 M3 의 WP4 와 같이 넣는다.
5. **패널 대상에 얹은 검토가 `rr_coverage` 를 닫나.** 권고 — 닫지 않는다(`flow='cells'` 대상만 닫는다). 닫으면 그 대상의 다음 Tier 패널이 그 전문가를 앉히지 않아 두 방식의 비교가 섞인다. 보고서 · 의견 · finding 은 쓴다.
6. **M2 검토 finding 의 회수 자격.** 권고 — `recall_eligible = 0` 으로 넣는다. 형식이 승인되기 전(나갈 기준 4)의 산출이 다른 과제의 학습 통계 · 선례에 들어가지 않게 한다. 의견 행의 E7 회수(`brief.py:1600`)는 설계서대로 둔다 — 막으려면 그 조회에 대역 조건 한 줄이 든다(사용자가 원하면 넣는다).
7. **9명 고르기와 카드 0장 대표.** 권고 — 코드가 고르지 않고 `scope.agents` 로 명시한다(ECAD 아닌 영역 9개의 1순위). 1순위가 카드 0장일 수 있다(카드 0장 3명 가운데 `material-twin-analyst` 는 material 영역이다 — 순위는 로스터를 열어 봐야 안다). 그러면 그 영역에서 카드가 있는 다음 순위를 쓰거나, 역할만으로 도는 `role_only` 셀(원장 `done_weak(no_cards)`)을 받아들인다. 사용자가 고른다.
8. **배경 카드를 카드 밖 호출에 전부 싣나.** 권고 — 싣는다. 1백만 토큰 창에서는 평균 3만여 자가 들어가고, 훑기 `k` 에 기대면 걸리지 않은 배경 카드가 한 번도 본문으로 읽히지 않는다(P-03 · X1-11). 넘치면 서버가 제목으로 내리고 그 수가 원장과 보고서에 남는다.
9. **`llm_timeout` 의 부류.** WP3a 는 인프라(차감 없음), WP5a 는 용량(차감 있음)이다. 권고 — 인프라로 두고 차단기에 센다. 같은 호출에서 앱 벽시계가 두 번 끊으면 그때 내용 탓으로 센다.
10. **v4 를 리허설까지 붙잡아 두는 동안의 충돌.** M2 의 HWAXRisk 커밋 전부가 로컬에 며칠~몇 주 머문다. 다른 세션(프런트 등)이 그사이 `MIGRATIONS` 에 v4 를 먼저 넣으면 부딪친다. 권고 — HWAXRisk `context-notes.md` 에 'v4 는 리스크 심사 재설계 M2 몫' 을 먼저 적고, 날마다 원격을 받아 rebase 한다. 프런트 세션은 백엔드 스키마를 건드리지 않는다는 규칙을 다시 확인한다.
11. **dev 실 LLM 리허설이 창 때문에 거절될 수 있다.** dev 창(16,384토큰)의 단위 본문 상한은 약 3,000자다(WP3a 3.3 의 예시). 합성 40건 과제의 단위가 넘으면 `ctx_too_small` 이다. 권고 — 가장 작은 단위 2개로 범위를 잡고, 그래도 거절되면 그것을 거절 길의 시험으로 기록한 뒤 배선 확인은 가짜 엔진 통합 시험과 cae00 파일럿에 맡긴다. dev 에이전트 서버를 잠시 큰 창 모델에 붙이는 길은 사용자 몫이다.
12. **진행 응답의 품질 수치 비용.** 권고 — `progress_json.quality` 에 60초마다 넣고 `coverage` 는 그것을 읽는다. M3 의 전원(셀 수천)에서도 5초 폴링이 원장을 다시 세지 않는다.

## 실측이 필요한 값

| 값 | 출하 기본 | 재는 곳 | 바꾸는 자리 |
|---|---|---|---|
| 호출 시간(종류별 p50 · p95) | 벽시계 18,000초 · 줄 사이 침묵 300초 | M0-b, M2 파일럿(S11 '호출 초') | `HWAXRISK_REVIEW_CALL_TIMEOUT_S` · `…_READ_TIMEOUT_S` |
| 셀당 호출 수 | 상한 `3 × (2·묶음 수 + 점검 카드 수 + 4)` | M2 파일럿(S11 '실측') | `review_ops` 상수 |
| 동시 수 | 앱 4, 서버 관문 limit 을 넘겨 띄우지 않는다(서버 4 · 바쁠 때 2) | M2 의 챗 첫 응답 지연과 함께 | `HWAXRISK_REVIEW_CONCURRENCY` · 서버 `CARD_REVIEW_CONCURRENCY(_BUSY)` |
| 순서 뒤집힘 비율 | 이중 판정 전량(`dual_rate` 1.0) | M2 파일럿 | M3 앞에서 비율을 정한다 |
| 양성 비율 | 단독 재질의 = 실효 걸림 전부(상한 없음) | M2 파일럿 | M3 앞에서 상한을 정한다 |
| 훑기 '무관' 비율 | 재기만 한다(분류에 안 씀) | M2 파일럿 | M4 의 거르기 결정 |
| 내용 탓 한도 · 빠진 카드 재질의 | 2 · 셀마다 2번 | M2 파일럿 | `HWAXRISK_REVIEW_MAX_CHARGED` · 상수 |
| 카드 밖 줄 상한에 닿는 빈도 | 같은 단위 재질의 최대 3번 | M2 파일럿(`offcard_capped`) | 상수 |
| 차단기 | 최근 20건(10건 이상) — 인프라 10건 · 내용 탓 절반 | M2 파일럿 | `review_ops` 상수 |
| 인프라 백오프 | `min(30·2^(n−1), 900)`초 ±20% | M2 파일럿 | `review_ops` 상수 |
| 서버·앱 인용 대조 불일치 | 잡당 5건이면 `contract` 보류 | M2 파일럿 | 상수 |
| 창 출처 `fallback` 지속 | 600초면 `ctx_unknown` | cae00 재고(창은 서버가 알려 준 값) | 상수(PLAN §4) |
| 팩 재시도 | 404 3번 · 502 6번(60초부터 두 배, 상한 1,800초) · 0장은 두 번 확인 | M2 파일럿 | 상수 |
| 표시 상한 | 보고서 인용 200자(사용자 결정) · 요약 1,500자 · MCP 쪽 25,000자 | 사용자 형식 승인(나갈 기준 4) | `expert_report` 상수 |
| DB 증가분 | 추정 — 전원 타깃당 35~65MB, M2(9명)는 그 몇 % | M2 파일럿(S11 새 표 바이트) | 백업 계획(M3) |
| 묶음 크기 K · 단위 본문 상한 | 서버가 정한다(앱은 상수를 두지 않는다) | M0-b | 서버 `CARD_REVIEW_K` · `limits` |
| 챗 첫 응답 지연 | 평소의 2배 안(M3 나갈 기준) | M2 동안 포털 · 에이전트 서버 로그 | 동시 수 |
