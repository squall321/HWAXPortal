# 꾸러미 사이 계약 — 조정 결과 (2026-10-09, 설계서 일곱 편의 어긋남을 하나로 맞춘 판)

설계서끼리 다르게 적은 것은 **이 문서가 이긴다.** 설계서 본문은 아직 고치지 않았다(문제 사냥이 끝난 뒤 계획서에 반영한다).

## 순서와 스키마 버전

- C-1 배포 순서는 WP1 → (WP2 ∥ WP3a) → WP3b → WP4 다. WP5 는 각 걸음에 붙는다. WP1 은 뒤 꾸러미 없이도 값이 있어야 하고 먼저 나간다.
- C-2 스키마 — v2 는 이미 쓰였다(`rr_brief_calls`). **v3 = WP1 의 ADD COLUMN** (`rr_panels.result_gz·result_hash·result_saved_at`, `rr_targets.report_gz·report_level·report_built_at`). **v4 = 새 흐름의 표·열 전부를 한 블록으로**(새 흐름 첫 커밋). 한 번 push 된 버전의 DDL 은 고치지 않고 다음 버전(v5…)으로 더한다. WP5a 의 '전부 v3' 는 v4 로 읽는다.
- C-3 새 표의 어휘 열(status·kind·verdict…)에 CHECK 를 걸지 않는다. 어휘는 코드 상수와 시험이 지킨다. 새 표는 `owner_sub TEXT NOT NULL` 과 PK 를 갖고 과제 원문이 드는 표는 `project_id` 도 갖는다. 원문은 `*_gz BLOB` + `*_sha` + `*_chars`. **예외 — `rr_card_packs`** 는 과제 자료가 아니라 코퍼스 사본이라 owner_sub 가 없다(C-9).

## 이름

- C-4 좌석 dict 의 키는 `key`, 표의 열은 `agent_key`. 읽는 쪽은 `common.seat_key()` 하나를 쓴다.
- C-5 흐름 판별 — `rr_targets.flow` = `'panels'`(옛) | `'cells'`(새). 잡 종류 — `rr_jobs.mode` = `'panels'|'reviews'|'post'|'issues'|'synth'`(열 이름은 mode 하나, kind 는 쓰지 않는다). 코드가 멈춘 정지는 `hold_code·hold_until·hold_n`.
- C-6 패널 — `rr_panels.kind`(`'coverage'|'issue'`)·`issue_id`·`result_gz`. `purpose`·`turns_gz` 는 쓰지 않는다. 쟁점 패널은 `tier='I'`.
- C-7 `rr_seat_opinions.cycle` 대역 — 원장 좌석 1~499(지금 뜻 그대로) · 검토 의견 500 + `rr_coverage.cycle` · 원장 밖 패널 좌석(반대석·추가 좌석·쟁점 패널 전 좌석) **100000 + panel_no**. WP1 이 먼저 나가므로 WP1 도 100000 을 쓴다(1000 아님).
- C-8 검토 단위 `kind` = `bundle|boundary|global|excluded|snap_unit`. 단위를 가리키는 인용 스킴(u:)은 만들지 않는다. 근거 꾸러미 열은 `evidence_*`, 카드 묶음은 `pack_*`. 신호 함수는 `unit_signals.for_cell`, 단위 읽기는 `units.load_units`. 머리 표 `rr_unit_builds(target_key, rev)` 를 둔다.

## 카드 묶음

- C-9 `rr_card_packs` 의 키는 내용 주소 `(agent_key, pack_hash)`. owner_sub 없음, 반출 제외. 타깃과의 결속·묶음 계획(`plan_json·limits_rev·norm_rev`)은 `rr_expert_reports`(타깃 × 전문가의 실행 머리를 겸한다)에 둔다.
- C-10 카드를 받는 길은 **하나** — 에이전트 서버 `POST /card-review/pack`(게이트웨이 도구 `list_records`+`get_record`, 호출자 신원 위임). 앱은 그 응답을 통째로 얼린다. AIDataHub REST·서비스 키 경로(`adh.agent_cards`)는 쓰지 않는다. '카드 0장' 과 '못 받았다' 는 다른 모양으로 답한다. AIDataHub 의 `get_agent_cards` 도구는 권고(없어도 돈다).
- C-11 카드의 정규 글(본문·종류·등급·causal_status)을 만드는 곳은 에이전트 서버 `card_review.normalize_card` 하나다. 인용 대조는 서버 `checks` + 앱의 얼린 팩 재대조 두 번이고, 두 리포가 같은 벡터 파일로 파리티를 시험한다.

## 호출과 판정

- C-12 엔드포인트 — 에이전트 서버 `/card-review/{limits,pack,plan,run}`, 포털 중계 `/agent/card-review/*`(본문을 통째로 넘기고 신원 칸 넷만 덮어쓴다). `/agent/chat` 을 쓰지 않는다. 대화(conv)를 만들지 않는다.
- C-13 호출 종류 다섯 — `sweep`(전수 훑기) · `verdict`(변형 `fwd|rev|solo`) · `offcard`(카드 밖) · `noinput`(입력 결손 두 질문) · `cross`(2차 영향). 요청 1건 = 전문가 × 단위 × 카드 묶음 1개의 논리 호출 1건. 출력은 JSON Lines.
- C-14 단위는 구조로 싣는다 — `unit{unit_id, kind, title, summary, lines[{ref, text}], evidence[{ref, text}], notes, missing[]}`. 카드 K01…·변경 줄 L01… 별칭을 모델이 쓰고 코드가 `record_id`·`c:/e:/p:/d:` 로 되돌린다.
- C-15 판정 낱말 — 적용 `applies` = `yes|no|unknown`, 준수 `judgement` = `OK|WARNING|FAIL|undetermined|na`, 심각도 = 경미·중대·치명, 방향 = `risk|improvement`, 메커니즘 = 택소노미 코드. `rr_card_verdicts` 의 PK 는 `(target_key, unit_id, agent_key, record_id, variant)`. **'문제없음' 도 행으로 둔다**(카드 문구와 변경 참조 인용을 함께 요구한다). 참조 문법에 `card:<record_id>#<section_id>` 를 더한다.
- C-16 판정 범주 접기와 화면 말은 `review_quality.verdict_class` 한 곳. 코드가 만드는 문장은 판단어 린터를 지난다.
- C-17 단위 본문 상한 B·묶음 카드 합·K 는 상수가 아니라 `GET /card-review/limits` 로 박스마다 받는다(128K 창이면 B≈12,126자·K=8, dev 16K 창이면 B≈3,008자). `rr_units`·`rr_expert_reports` 는 그때의 `limits_rev` 를 적는다.

## 셀

- C-18 셀 상태 — `pending · running · reviewed · na_irrelevant · no_input · failed · skipped`. `skipped` 는 사람의 넘김(사유 필수). `carried`(리비전 간 재사용)는 어휘만 예약하고 이번 범위에서 구현하지 않는다. `failed` 는 종결이 아니다 — 사람이 '다시' 또는 '넘김' 을 정해야 실행이 끝난다. 표본 재검토 전이 `na_irrelevant → running → reviewed | na_irrelevant` 를 둔다.
- C-19 `na_irrelevant` 는 결정적 신호 `det=='miss'` **그리고** 전수 훑기 자기판정이 무관일 때만. hit·blind·강제 포함이면 쓸 수 없다. 검색 적중(agent_search·hybrid_search)은 제외 신호로 쓰지 않는다(늘 top_k 건을 돌려줘 변별력이 없다). 사유는 `reason_code` + `reason_text` 둘 다 적는다.
- C-20 `no_input` — 입력 결손 전문가(로스터의 `input_gaps_json`)가 `noinput` 호출의 질문 1 에 영향(yes)을 하나도 내지 못한 셀. 영향을 냈으면 `reviewed` + 입력 결손 표기. 새 흐름은 `deferred` 를 만들지 않는다. `rr_coverage` 롤업은 `abstain` + `reason='no_input:<gap>'`.
- C-21 세 격자(`rr_review_cells`·`rr_cross_cells`·`rr_mech_cells`)의 운영 열 이름은 WP5a 것으로 통일 — `run_id · priority · tries · charged · infra_streak · error_code · error_class · error · knob · not_before · lease_owner · heartbeat_at · credential_kind · model · llm_calls · tokens_in · tokens_out · elapsed_ms · truncated`. 셀의 호출 품질 열 — `rows_expected · rows_missing · stamp · basis('cards'|'search_only'|'noinput') · soft_over · mechs_json{raised, considered} · handoffs_json · pack_hash · audit_kind · audit_result`.
- C-22 호출 원장 `rr_review_calls`(끝난 호출 1회 = 1행, 결과 프레임 gz·토큰·오류 코드·`quality_json`·`credential_kind`). 열 정의는 WP3b 판이 소유한다.
- C-23 `rr_cross_cells` 의 키는 `(target_key, unit_id, src_domain, dst_domain)` — 방향이 있다.

## 운영

- C-24 LLM 경합은 에이전트 서버의 전용 관문 하나가 맡는다. **줄을 세우지 않는다** — 자리가 없으면 1초 안에 `error{code:'review_busy', retry_after_s}` 로 답하고 앱이 백오프한다. 기본 동시 4, 챗·심의가 돌면 2(둘 다 env). 밤·주말 상향은 손잡이로 두되 기본은 꺼 둔다.
- C-25 카드 대조 호출은 `delib_active` 에 세지 않는다. `/health` 에 `review_active · draining · capabilities · card_review{…} · drain{…}` 를 더한다(기존 키 불변). 비우기 신호는 에이전트 서버 `/drain`(수명 30분). 셀은 끊겨도 차감 없이 스스로 다시 돈다 — 배포가 셀을 기다리지 않는다. 몇 시간짜리 쟁점 패널만 지금의 심의 보호를 받는다.
- C-26 실패는 인프라 탓(차감 없음·자동 재시도·백오프)과 내용 탓(2회 뒤 failed)으로 가른다. 서버가 `infra` 표지를 싣는다. 실패율이 치솟으면 차단기가 잡을 멈추고 백오프 뒤 스스로 재개한다.
- C-27 기능 기본값은 꺼짐. dev 가짜 엔진 리허설 → dev 실 LLM 소규모 → cae00 대표 15명 시범 뒤에 켠다.

## 시험 자산

- C-28 합성기는 한 벌 — `app/devseed.py`(어댑터 결과 수준에서 시작해 실제 생산자가 IR·diff 를 만든다) + `tests/factories.py`(저장 도우미). 단위 불변식 이름은 WP2 가 U1~U6, WP5b 의 단언은 XU1~XU10.
- C-29 품질 지표는 새 표 없이 `app/review_quality.py`(지표 사전·기준 자산 `review-quality.v1.json`·블록 조립). 상한 함수는 `audit.binom_upper` 하나.

## 그 밖

- C-30 택소노미 1.1(메커니즘 14종 추가) + 새 자산 `mech-owners.v1.json`·`cross-pairs.v1.json`. `change_kind` 2종(contact_type·parameter) 추가. MCP 도구 14 → 18(`risk_get_issues·risk_get_cross·risk_get_mech_grid·risk_get_report`). MCP L2 경로(JS)는 새 흐름 타깃에서 막고 안내문만 고친다.
- C-31 좌석이 리스크 앱 도구를 쓰는 통로는 `delib_opts.apps` 가 아니라 엔진의 `_RISK_KEEP_TOOLS`. 지식카드 검색어는 새 요청 키 `delib_opts.knowledge_query`.
- C-32 브리프 예산은 상수가 아니라 프로파일(`brief.BriefProfile` — MCP 는 옛 값, 웹은 엔진이 알려 주는 근거 예산에서 유도).
