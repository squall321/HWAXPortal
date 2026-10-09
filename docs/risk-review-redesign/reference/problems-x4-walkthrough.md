# X4 — 타깃 하나를 처음부터 끝까지 따라가 본 결과 (2026-10-09)

따라간 타깃은 diff · 변경 150건 · 전문가 359명(회로 110명 ECAD 없음 · 카드 0장 3명)이다. 같은 길을 (가) snap (나) 변경 2건 (다) G2 차단 (라) 취소·일시정지 (마) 에이전트 서버 재기동 (바) 새 리비전의 두 번째 타깃으로 다시 걸었다.
읽은 것은 00-brief · 04-contract 전문, spec-wp2 · wp3a · wp3b · wp4 의 3절·7절 전문, HWAXRisk `routes.py`(타깃 생성·잡) · `runner.py`(잡·복구·_finish_job) · `planner.py`(로스터·승계) · `narrative.py`(tool 참조 해석), HWAXAgentServer `app.py`(_model_context_tokens)다. WP5a 는 보류 코드·사람 처분 절만 grep 으로 읽었다.
04-contract 가 이미 맞춘 것(이름·상태 어휘·cycle 대역·관문이 줄을 세우지 않는 것 등)은 적지 않았다.

표기 — [blocker] 이대로 구현하면 끝나지 않거나 운영 단계를 못 넘는다 · [major] 한 기능이 틀리게 돈다 · [minor] 작은 어긋남.

---

## 단계별 담당(따라간 길)

| 단계 | 맡는 곳 |
|---|---|
| 타깃 생성 · flow 결정 · 로스터 동결 | WP2 3.10.1 · 3.12(`routes.create_target` → `units.compute` → 로스터 조회 → 한 트랜잭션으로 타깃 행·`units.persist`·`freeze_roster(defer_absent=False)`·승계) |
| 단위 빌드 | WP2 3.4(`rr_unit_builds` · `rr_units`), 근거 꾸러미 3.8(`unit_evidence.ensure`), 신호 3.9(`unit_signals.compute` · `for_cell`) |
| 잡 시작 | WP3b 3.7.1(`create_review_job` — 격자 `plan_cells`, 네트워크 없음) → 3.7.3 틱(`/limits` · `/pack` · `/plan`) |
| 전문가 세션 | WP3b 3.7.4(`run_expert`) — 호출은 WP3a 3.5(`sweep` · `verdict` · `offcard` · `noinput`), 검증 WP3b 3.8, 정산 `settle_cell`, 마감 `finalize_expert`(보고서 3.11 · finding 3.10 · 롤업 3.4.1) |
| 사후 | WP4 3.11.2(`advance_post`) — 병합 3.5 · 2차 영향 3.2 · 결손 사냥 3.3 · 표본 재검토 3.4 |
| 쟁점 | WP4 3.6(`select_issues`) → 3.7(`plan_issue_panel` · 엔진 3라운드 · `resolve_issue`) |
| 종합 · 완결 | WP4 3.8(`synth` · `assemble_report`) · 3.9(`closure.close_level_cells` · `ack_residual`) |

---

## 문제

### X4-01 [blocker] 단위 크기를 박스 한도에 맞추는 재빌드에 주인이 없고, 격자가 한도보다 먼저 선다

- 근거. WP2 3.13 은 "검토 잡이 격자를 만들기 **전에** WP3b 가 limits 를 읽고, 어느 단위든 `unit_size > unit_body_max` 이면 `build_units(force=True, reason='limits')` 를 `caps_for_limits` 로 다시 부른다" 고 적고 7.1 에서 그것을 WP3 에 받는 것으로 적었다. WP3b 는 반대로 적었다 — 3.7.1 `create_review_job` 은 "네트워크를 부르지 않는다(격자는 여기서)", `/limits` 는 그 뒤 pack 단계 틱에서 처음 읽고(3.7.3 의 3), 3.5.3 은 "단위를 쪼개는 것은 WP2 의 일이다 … 그래도 넘은 단위의 셀은 호출하지 않고 `failed('unit_oversize')`", 7.1 은 "살아 있는 검토 잡이 있는 타깃의 단위 재빌드는 409 로 막아 달라" 다. 어느 문서에도 `caps_for_limits` 를 부르는 줄이 없다(WP3b 전문 grep 0건). 계약 C-17 은 한도를 limits 로 받는다고만 적고 누가 언제 다시 빌드하는지는 적지 않았다.
- 무슨 일이 나나. dev 는 창이 16,384 라 `unit_body_max` 가 약 3,008자다(WP3a 3.3 표). 단위 기본 상한은 요약 7,000 + 꾸러미 4,500 이다(WP2 3.3 `UnitCaps`). 타깃은 설정값으로 빌드되므로 dev 의 모든 단위가 한도를 넘는다 → 전 셀이 `failed('unit_oversize')` 가 되고, 다시 빌드하려 해도 살아 있는 잡이 409 로 막는다. C-27 의 둘째 걸음(dev 실 LLM 소규모)이 그대로 막힌다. 운영(128K)도 여유가 626자뿐이다(12,126 − 11,500) — `FIXED` 틀 길이가 가정(2,600자)보다 길게 실측되거나 전문가별 `missing.note` 가 붙으면 일부 단위가 넘고, 그 단위 × 359명 셀이 통째로 실패한다.
- 고치는 법. WP3b 걸음 8(review_loop) 의 pack 단계 **맨 앞**에 '단위 맞춤' 을 넣는다 — ① `/limits` 를 읽는다 ② `rr_unit_builds.caps_json.limits_rev` 와 다르고 어느 단위든 넘으면 그 잡이 직접 `units.build_units(force=True, reason='limits', caps=caps_for_limits(limits))` 를 부른다(이 호출만 409 가드를 면한다 — 잡 id 를 인자로 넘긴다) ③ 그 뒤에 `plan_cells` 를 부른다. `create_review_job` 은 격자를 만들지 않고 잡 행만 만든다(셀 수 추정은 `cells_estimate` 로 준다). `caps_for_limits` 는 꾸러미·`notes`·`missing.note` 최댓값을 뺀 값으로 `max_chars` 를 잡는다. WP2 걸음(단위 빌드)의 시험에 '창 16,384 한도로 빌드하면 넘는 단위 0' 을 넣는다.

### X4-02 [blocker] '해당 없음' 표본 재검토를 실제로 돌리는 주체가 없어 후속(post) 잡이 끝나지 않는다

- 근거. WP4 3.11.2 는 post 잡이 시작 때 `audit.plan_audit` 로 `rr_cell_audits` 행을 만들고, 마감 조건을 "세 표에 `pending · running` 이 없다" 로 둔다. 그 행을 돌리는 길로 WP4 는 `cells.run_check(…, purpose='audit')`(7.1)와 제공자 `'cell_audit'`(3.11.4)를 기대한다. WP3b 7.2 는 "다시 연 셀은 보통 셀처럼 내 루프가 돈다 — 따로 부르는 `run_check` 는 두지 않는다" 고 못 박았고, 3.7.11 에서 검토 루프는 "`mode='reviews'` 잡에는 전문가 세션을, 등록된 제공자의 `modes` 에 드는 잡에는 그 제공자의 `claim` 을" 준다. 제공자의 일 하나는 `engine.run` 한 번인데 셀 하나의 대조는 호출 여러 번이다. 계약 C-18 은 전이(`na_irrelevant → running → reviewed | na_irrelevant`)만 적었다.
- 무슨 일이 나나. post 잡이 도는 동안에는 살아 있는 reviews 잡이 없다. `review_cells.reopen(via='audit')` 로 셀을 `pending` 으로 돌려도 집는 사람이 없고, `rr_cell_audits` 는 `pending` 으로 남아 post 가 마감하지 못한다. '해당 없음' 셀이 하나라도 있는 타깃(필터를 켠 모든 타깃)에서 사슬이 post 에서 멈춘다. 사람이 할 수 있는 조작도 정의돼 있지 않다.
- 고치는 법. 표본 재검토를 reviews 잡의 마지막 단계로 옮긴다. WP3b 걸음 8 에 `phase='audit'` 를 더한다 — 집을 전문가가 없어지면 `audit.plan_audit` → `review_cells.reopen(via='audit')` → 같은 잡이 그 셀을 돈다 → 다 돌면 `audit.apply_audit_round` → 층이 다시 열리면 같은 잡이 이어 돈다(회차 상한 3) → 그 뒤에 `completed`. WP4 걸음(audit.py)은 `plan_audit` · `apply_audit_round` 두 함수와 표만 내고 제공자 `'cell_audit'` 와 `run_check` 를 계획에서 뺀다. post 의 마감 조건에서 `rr_cell_audits` 를 뺀다. 2차 영향이 `reopen_src` 로 지목한 강제 표본만 'post 마감 → reviews(강제 셀만) → post(회차 +1)' 로 남긴다. C-18 에 "돌리는 주체는 reviews 잡" 한 줄을 더한다.

### X4-03 [major] 표본 재검토의 결과 어휘와 종결 상태가 두 문서에서 다르다

- 근거. WP3b 3.9.3 — `audit_result` 는 `clean | miss`(적용 판정이 하나라도 있거나 카드 밖이 `none` 이 아니면 `miss`)이고 "감사로 본 셀은 `clean` 이어도 `na_irrelevant` 로 되돌리지 않는다 … `reviewed` 로 남는다". WP4 3.4.1 — 결과는 `risk_miss | relevance_miss | kept` 셋이고 `kept` 는 "셀은 `na_irrelevant` 그대로다", 층을 다시 여는 것은 `risk_miss` 뿐이다. 계약 C-18 은 두 종결을 다 허용하고 C-21 은 열 이름(`audit_result`)만 적었다.
- 무슨 일이 나나. WP4 가 `audit_result='miss'` 를 놓침으로 읽으면 '적용되지만 문제없음' 한 건에도 그 층의 '해당 없음' 셀을 전부 다시 연다(3.4.4). `clean` 셀이 `reviewed` 로 남으면 WP4 의 모집단("`na_irrelevant` 이고 아직 재검토하지 않은 셀")과 `kept` 셈이 맞지 않는다.
- 고치는 법. WP3b 걸음 6(정산)에서 `audit_result` 를 `risk_miss | relevance_miss | kept` 셋으로 적는다(조건은 WP4 3.4.1 표 그대로). 종결 상태는 WP3b 쪽(본 것은 `reviewed`)으로 통일하고, WP4 의 `kept` 셈은 `rr_cell_audits.state` 로만 한다. C-18 의 끝 상태에서 `| na_irrelevant` 를 지운다.

### X4-04 [major] `na_irrelevant` 의 사유 코드를 만드는 곳이 없어 표본의 층이 영역 하나로 뭉친다

- 근거. C-19 는 "사유는 `reason_code` + `reason_text` 둘 다 적는다" 고 했고 WP4 3.4.3 의 층은 `<영역>|<사유 코드>` 다. WP3a 3.5.1 의 훑기 `u` 줄에는 `why`(80자 글)뿐이다. WP3b 3.9.3 은 "층 키로 쓸 수 있는 것은 결정적 신호의 `miss` 목록" 이라고 했는데, `na_irrelevant` 는 양방향 신호가 **전부** miss 일 때만 나므로(WP2 3.9.2 합치는 식) 그 목록은 모든 셀에서 같다.
- 무슨 일이 나나. 층이 영역 15개로 줄어든다. xd(122명)에서 `risk_miss` 한 건이 나면 "그 층의 남은 '해당 없음' 셀을 전부 다시 연다"(WP4 3.4.4)가 xd 의 '해당 없음' 셀 전부(단위 20개면 최대 2,000셀대)에 걸린다.
- 고치는 법. WP3a 걸음(sweep 프롬프트)에 `rel='no'` 줄의 닫힌 코드 `nr` 을 더한다 — `no_object`(이 단위에 내 카드가 다루는 대상이 없다) · `no_condition`(대상은 있으나 적용 조건이 성립하지 않는다) · `out_of_domain` · `other`. 검사 ⑥ 에 `nr` 열거를 넣는다. WP3b 는 셀에 `reason_code=nr`, `reason_text=why` 를 적는다. 묶음이 여럿이면 코드가 다른 경우 `other` 로 둔다.

### X4-05 [major] '해당 없음' 으로 가는 문이 사실상 열리지 않는다 — 신호 넷이 구조적으로 blind 다

- 근거와 원인 넷.
  1. `unit_signals.compute` 를 부르는 곳이 없다. WP2 7.1 은 "첫 셀 전에 `unit_evidence.ensure` · `unit_signals.compute` 를 부른다" 를 WP3 에 받는 것으로 적었지만 WP3b 3.7.3 틱에는 `ensure` 뿐이다(WP3b 전문 grep — `compute` 0건).
  2. S-card 의 재료가 어긋난다. WP2 7.1 은 팩 전체의 "제목·태그 어휘"(`card_vocab(store, agent_key, pack_hash)`)를 기대한다. WP3b 3.7.4 는 "훑기가 그 단위에 걸었던 카드(`k`)의 제목·태그 낱말" 을 준다. `last_check` 는 훑기가 `no` 인 셀에만 부르는데 WP3a 3.5.1 규칙상 `rel=no` 면 `k=[]` 이다 — 정작 필요한 셀에서 어휘가 빈다. 또 팩에는 태그가 없다(WP3a 3.4 팩 응답 · WP3b `manifest_json` 어디에도 `tags` 가 없다). WP2 3.9.2 는 "0장이면 blind" 다.
  3. S-fts 는 게이트웨이 `fts_search` 를 불러야 하는데 `for_cell(store, target_key, unit_id, agent_key, *, card_vocab, last_check)` 에 설정·자격 인자가 없다(WP2 3.3, WP3b 7.1 이 같은 시그니처를 받아 적었다). 못 부르면 blind 다.
  4. S-role 은 "변경 부품 중 역할 미상이 하나라도 있으면 hit 아닌 영역 전부 blind" 인데 역할 표 첫 판이 낱말 10개다(WP2 3.9.3). S-kind 도 "표에 없는 change_kind·code 가 있으면 전 영역 blind" 인데 바닥 표의 키는 change_kind 뿐이라 `codes`(`part.thickness_changed` · `param.volume` …)를 대조하면 늘 blind 다.
- 무슨 일이 나나. `det` 가 `miss` 가 되는 셀이 없어 r = 1 이다. 누락 쪽은 아니지만 WP3b 3.14.1 의 식에 단위 28개(변경 150건의 추정)를 넣으면 셀 10,052 · 호출 약 31,000건이고, 그 문서의 가정(호출 5분 · 단독과 4장 묶음 2분 · 동시 4)으로 약 25일이다(추정). 심의가 도는 동안은 동시 2 라 그 두 배다. 훑기 호출 약 430건은 쓰이지 않는 답을 받는다.
- 고치는 법. ① WP3b 걸음 8 의 pack 단계에 `unit_signals.compute(store, settings, target_key, credential_sub=…)` 호출을 넣고 `signals_status` 가 NULL 인 단위의 셀은 분류하지 않는다. ② `card_vocab` 는 WP3b 걸음 3(cardpack)에 `cardpack.card_vocab(store, agent_key, pack_hash) -> {tokens, n_cards}` 로 두고 팩 전체의 제목 + 절 제목 낱말로 만든다(태그는 팩에 없으므로 계약에서 '태그' 를 뺀다). ③ `for_cell` 에 `settings` 와 `credential_sub` 를 더하거나 S-fts 를 `compute` 쪽 사전 계산으로 옮긴다(전문가 × 단위마다 1회라 '해당 없음 후보' 에만 건다). ④ S-kind 는 `change_kinds` 만 표에 대조한다고 WP2 3.9.2 에 못 박고, S-role 의 blind 는 '역할 미상 부품이 그 단위 변경 줄의 과반' 일 때로 좁힐지 사용자 결정 항목에 올린다.

### X4-06 [major] 훑기를 건너뛰면 훑기 결과(`k`)를 읽는 세 곳이 빈손이 된다 — 회로 110명은 카드 본문 0장으로 답한다

- 근거. WP3b 3.7.4 는 snap 타깃 · 단위 5개 이하 · `sweep='off'`(또는 필터 꺼짐) · 카드 0장에서 훑기를 건너뛴다. 그런데 `noinput` 의 `cards` 는 "훑기가 그 단위에 건 카드를 전문으로"(WP3b 3.7.4 · WP3a 3.5.4), `offcard` 의 전문 배경 카드는 "앱이 (가)의 `k` 로 고른다"(WP3a 3.5.3), 배경 카드는 "훑기에서 전문으로 읽히고 카드 대조에서는 제목만"(WP3b 3.5.1)이다.
- 무슨 일이 나나. 훑기가 없으면 ① 입력 결손 전문가(110명)의 `noinput` 호출에 전문 카드가 0장이다 — 카드를 대면 `checks.quote='digest_only'` 라 검증된 근거가 못 되고 롤업은 `done_weak` 다. ② 배경 카드(6,184장, 전체의 57%)는 어느 호출에서도 본문이 실리지 않는다. WP2 8절 결정 3 의 권고(첫 운영은 필터를 끈다)와 snap 타깃 전부, 변경 2건짜리 작은 diff 가 이 경우다. "모든 전문가의 지식카드로 답하게" 가 가장 먼저 도는 설정에서 깨진다. 또 `noinput` 에 실을 카드가 예산을 넘을 때의 처리가 WP3a 3.5.4 에 없다(`offcard` 만 '제목으로 내린다' 가 있다) — 그대로면 422 `over_budget` 이고 `noinput` 에는 묶음이 없어 '반으로 나눠 다시' 도 못 한다.
- 고치는 법. '훑기 실행' 과 '훑기 답으로 거르기' 를 가른다. WP3b 걸음 8 의 표에서 snap · `few_units` · `filter_off` 는 **훑기는 하고 분류만 강제**(Tier A 와 같은 처리)로 바꾼다. 건너뛰는 것은 카드 0장뿐이다. `noinput` 은 WP3a 걸음에 '`cards` 가 `CARD_V` 를 넘으면 `verdict_decks` 순서로 나눠 덱마다 1호출, 답은 앱이 합친다' 를 더하고, 훑기 `k` 가 비면 점검 카드 덱 전부를 싣는다.

### X4-07 [major] 2차 영향(`cross`) 호출의 입력·출력 모양이 WP3a 와 WP4 에서 다르다

- 근거. 계약 C-13 은 `cross` 가 다섯 종류 가운데 하나이고 출력이 JSON Lines 라는 것까지만 맞췄다. WP3a 3.5.5 의 행은 `x{impact, title, path, a[], l[], sev, conf, check_kind, check}` · `conflict{a, l, why}` · `none{why}` 이고 입력은 `digest`(받는 쪽 대표의 카드 **제목**)와 `extra.peer.rows[{agent_key, card_title, judgement, why, lines}]`(6,000자, 넘으면 422)다. WP4 3.2.3~3.2.4 는 `effects[{claim, mechanism, mechanism_free, subject, change_refs, card_refs, basis, severity, judgement, detectability, resolving_check, contradicts, why}]` · `no_effect.reason_code`(닫힌 넷) · `reopen_src.needed` · `needs` · `mechanisms_considered` 를 읽고, 입력에는 대표의 점검 카드 **전문**과 `src_digest`(V1·R1 번호 줄, '해당 없음 n명' 머리 포함)를 싣는다.
- 무슨 일이 나나. WP3a 모양대로면 ① `none` 에 `reason_code` 가 없어 WP4 3.2.4 의 1 번이 '형식 실패' 로 보고 다시 묻다가 `failed` 가 된다(교차 칸의 다수가 '영향 없음' 이다). ② `reopen_src` 가 없어 강제 표본이 죽는다 — WP4 가 "어느 전문가의 카드에도 없는 창발 리스크를 잡는 유일한 길" 이라고 적은 길이다. ③ `mechanism` 이 없어 교차 finding 이 전부 `unclassified` 로 한 클러스터에 뭉친다. ④ `mechanisms_considered` 가 없어 메커니즘 격자의 '검토함' 이 비고 사냥 호출이 는다. ⑤ `x` 줄에 카드 인용 칸이 없고 카드도 제목뿐이라 2차 영향 finding 의 등급이 전부 경험칙이다(WP4 3.2.4 의 3 번 검증이 할 일이 없다).
- 고치는 법. 계약에 `cross` 행 정의 한 절을 더하고 WP3a 걸음(cross 프롬프트)을 그것으로 고친다 — `x{dir, title, mech, mech_free, path, a[], l[], k, cq, sev, judgement, conf, check_kind, check}` · `conflict{a[], l[], why}` · `none{code: no_path|out_of_domain|covered_by_src|needs_input, why}` · `reopen{why}` · `m{seen[]}` · `need{what}`. 입력은 `cards`(대표의 점검 카드 — 예산을 넘는 꼬리는 서버가 제목으로 내리고 `meta.bg_dropped`) + `digest` + `extra.peer.rows[{id:'V1'|'R1', agent_key, kind, card_title, judgement, sev, mech, why, lines}]` + `extra.peer.head`(검토·해당 없음·입력 결손 인원)로 한다. WP4 걸음(cross.py)의 `apply_cross_result` 는 이 행을 읽게 고친다(`subject` 는 WP3b 3.10.2 처럼 인용한 변경 줄에서 코드가 뽑는다 — 모델에게 받지 않는다).

### X4-08 [major] 결손 사냥(`hunt`)과 요약(`summary`) 호출을 받는 끝점이 계약에 없다

- 근거. C-13 은 호출 종류를 다섯으로 닫았다(`sweep · verdict · offcard · noinput · cross`). WP4 3.11.3 은 `hunt` 와 `summary` 를 더 쓰고 "일반 호출이 없으면 이 꾸러미가 `card_review.py` 에 종류 셋을 더한다" 고 적었다. `summary` 는 전문가 없는 중립 서기 호출이고 출력이 JSON 객체 하나인데, `/card-review/run` 요청은 `expert{key…}` 가 있고 출력이 JSON Lines 다. `limits` 응답에 두 종류의 예산이 없어 WP4 의 '180행 · 60,000자' 를 박스 창에 맞출 값이 없다. 거절 코드도 다르다(WP4 는 `input_too_large{budget_chars}`, WP3a 는 422 `over_budget{need, have, part}`).
- 무슨 일이 나나. 배포 순서(C-1)가 WP3a → WP3b → WP4 라, WP4 걸음에서 다른 리포(HWAXAgentServer)의 끝난 모듈에 종류를 더하고 `prompt_rev` 가 바뀐다 — `prompt_rev` 가 바뀌면 열린 셀의 `input_hash` 가 달라져 처음부터 돈다(WP3b 3.7.7).
- 고치는 법. 계약 C-13 을 일곱으로 고치고 WP3a 걸음에 `hunt`(행 `r{code, verdict: risk|none|cannot_judge, reason_code, l[], k, cq, sev, judgement, why, needs}` · `extra{mech, mech_free, …}`, 물은 코드 전부가 한 줄씩 와야 한다)와 `summary`(`expert` 없이, 출력은 한 객체 — `kind` 별로 파서를 가른다)를 처음부터 넣는다. `limits` 에 `hunt{p, codes_max}` · `summary{p, rows_max, input_max}` 를 더한다. 거절 코드는 `over_budget` 하나로 통일한다. `prompt_rev` 는 종류별로 나눠(`prompt_rev[kind]`) 한 종류의 틀을 고쳐도 다른 종류의 셀이 다시 돌지 않게 한다.

### X4-09 [major] 카드에 메커니즘 표지가 없는데 쟁점 선정·격자 자격·finding 분류가 그것을 읽는다

- 근거. 카드의 태그는 `type · confidence · tier` 뿐이다(03-cards 수치와 표본 JSON 의 `content.card` 키). WP3a 3.4 의 정규 표기와 WP3b `rr_card_packs.manifest_json` 에도 메커니즘이 없다. `verdict` 의 `fwd · rev` 행에는 `mech` 가 없고(WP3a 3.5.2), `solo` 에도 없어 WP3b 7.1 이 따로 청했으며, `noinput` 의 `q1` 행에도 없다(WP3a 3.5.4). 그런데 WP4 7.1 은 `rr_card_verdicts.mechanism_code(카드 태그)` 와 `cards[{…tags}]` 를 받는 것으로 적고, 3.6.1 `split_verdict`("같은 대분류의 카드로 '적용되고 문제없음'"), 3.3.2 자격 ⓑ("카드 가운데 메커니즘 태그가 m 인 것"), 3.2.3 카드 우선순위 ⓑ 가 그것을 읽는다. C-15 는 "메커니즘 = 택소노미 코드" 라는 낱말만 적었다.
- 무슨 일이 나나. ① `split_verdict`(가중 1.3 — 쟁점 유형 가운데 가장 앞)가 한 건도 서지 않는다. ② 입력 결손 110명의 `q1` 영향 finding 이 전부 `unclassified` 다 — `cluster_key = sha1(mechanism|detail|subject_key|change_kind)` 라 같은 부품·같은 변경 종류에 대한 서로 다른 영향(보드 휨 · 스웰링 간극 · RF)이 한 행으로 뭉친다. `mech_free` 도 없어 WP4 3.3.4 (다)의 분리도 안 듣는다.
- 고치는 법. WP3a 걸음에서 `solo` 의 `v` 줄과 `noinput` 의 `q1` 줄에 `mech` · `mech_free` 를 더한다(`extra.mechanisms` 를 두 종류에도 싣는다). '문제없음' 행에는 받지 않는다. WP4 걸음(issues.py)의 `split_verdict` 조건을 카드 태그가 아니라 자산으로 바꾼다 — "리스크 클러스터의 변경 참조와 겹치는 변경 줄에 `applies=yes · judgement=OK` 를 낸 **다른 전문가**이고 그 전문가의 영역이 `mech-owners` 의 `owners(m) ∪ related(m)` 에 든다". 격자 자격 ⓑ 와 교차 카드 우선순위 ⓑ 는 계획에서 뺀다(ⓐ 만 남긴다).

### X4-10 [major] 보류(`hold`) 정책 아래에서는 여러 명이 낸 FAIL 이 쟁점이 되지 못하고 '중대 · WARNING' 으로 굳는다

- 근거. WP3b 3.10.3 의 기본 `hold` 는 검토가 낸 FAIL 을 등록부에 '중대 · WARNING' 으로 적고 "등록부의 `FAIL` 은 쟁점 패널(WP4)이나 사람이 올린다" 고 했다. WP4 3.6.1 의 유형은 등록부 값을 읽는다 — `split_severity` 는 "경미 대 치명" 또는 "FAIL 과 OK 가 함께", `solo_severe` 는 `support_experts == 1`, 3.6.2 의 P1 은 `sev3 == 3 or judgement == 'FAIL'`, 3.10.2 의 주의 등급 A 도 같은 조건이다.
- 무슨 일이 나나. `hold` 에서는 카드 검토가 올린 원자에 치명도 FAIL 도 없다(그 값을 가질 수 있는 것은 교차 · 사냥 응답이 낸 원자뿐이다). 그래서 카드 검토끼리의 `split_severity` 와 P1 은 설 수 없다. 단독 재질의까지 FAIL 로 확인됐고 두 명 이상이 낸 위반(가장 센 신호)은 `solo_severe` 도 아니어서 어느 쟁점 유형에도 들지 않는다 — 패널에 가지 못하고 등록부에 WARNING 으로 남으며 주의 등급은 B 가 상한이다. 종합 보고서 1쪽의 '등급 A 전부' 와 판정 후보 `no-go` 가 자동 경로로는 나오지 않는다.
- 고치는 법. WP4 걸음(issues.py)에 유형 `held_fail` 을 더한다 — 클러스터 구성원 가운데 `finding_json.judgement_claimed == 'FAIL'` 이고 단독 재질의가 FAIL 로 확인한(`quote_ok = 1 · refs_ok = 1`) 원자가 하나라도 있으면 쟁점이다(가중 1.4, `p_class='P1'`). `split_severity` 와 P1 · 주의 등급의 `severe` 는 `severity_claimed` · `judgement_claimed` 를 함께 읽는다. 시험에 'hold 정책 + 2명 FAIL → 쟁점 1건 · P1' 을 넣는다.

### X4-11 [major] Tier A 시범이 스스로 전원 실행으로 번지고, Tier 마다 후속·쟁점이 돌아 쟁점 상한을 인공물이 태운다

- 근거. WP4 3.11.1 의 사슬은 `reviews → post → issues → synth → (마감 레벨이 C3 이고 Tier 가 남았으면 다음 Tier 의 reviews)` 다. WP2 3.10.3 은 새 흐름 타깃의 마감 기본을 C3 으로 적는다. 지금 코드의 같은 자리(`runner._finish_job`, runner.py:900~913)는 다음 Tier 잡을 `consent=True` 로 스스로 만든다. C-27 과 WP5a 3.11 은 "대표 15명(`tiers:['A']`)으로 먼저 도는 것이 시범" 이라고 적었다. WP4 3.6.1 (2) `solo_severe` 는 `support_experts == 1` 이고 3.6.2 의 상한은 "타깃당 24건" 이다.
- 무슨 일이 나나. ① 시범으로 Tier A 를 돌리면 사슬이 사람 동의 없이 B → C 로 이어져 전원 실행이 된다. ② Tier A 단계에는 영역마다 한 명뿐이라 중대 이상 리스크가 거의 다 '단독' 이다 — `solo_severe` 가 쟁점 상한 24건(패널 한 건이 엔진 3라운드 · 최대 12시간 · 타깃 안 직렬)을 먼저 쓰고, 전원이 돈 뒤에 드러난 진짜 갈림은 `untried_cap` 으로 밀린다. ③ 사냥 호출도 Tier A 단계에서 '아무도 안 봤다' 는 이유로 먼저 나간다.
- 고치는 법. WP4 걸음(잡 사슬)에서 다음 Tier 로 넘어가는 줄을 뺀다 — `synth` 가 끝나면 `next: {tier, cells_estimate, calls_estimate}` 를 응답에 싣고 사람이 시작한다(또는 뿌리 잡에 `auto_next_tier: true` 를 명시했을 때만 잇는다). `select_issues` 는 `solo_severe` 를 '그 단위에서 그 메커니즘의 소유·관련 영역 셀이 전부 종결' 일 때만 세우고 그 전에는 `deferred_scope`(상한에 세지 않는다)로 둔다. `plan_hunts` 도 같은 조건을 건다. 쟁점 상한은 `selected_round` 별이 아니라 '범위가 전원인 회차' 에만 건다.

### X4-12 [major] 카드 묶음을 못 받은 전문가가 남은 채 잡이 `completed` 로 끝나고, 그 `pending` 셀을 닫을 길이 없다

- 근거. WP3b 3.7.3 의 3 — "범위 안 전문가가 전부 `ok | empty` 가 되거나 남은 것이 백오프 중인 `error` 뿐이면 `phase='review'` 로 간다". 묶음 재시도는 `phase='pack'` 일 때의 일로만 적혀 있다. `claim_next_expert` 는 `pack_status ∈ ('ok','empty')` 만 집고, "집을 전문가가 없고 그 잡을 쥔 워커도 없으면 단계가 `done`" 이며 잡은 `completed` 다. 404 `agent_not_found` 는 "백오프하지 않고 사람에게 보인다"(3.5.2). C-18 의 `skipped` 는 "사람의 넘김" 이라고만 했고 WP3b 의 사람 처분은 `failed` 셀에만 있다(3.12.1 `PUT …/cells/{unit}/{agent}` `{dispose}`). WP4 3.9.4 의 4 는 `pending` 을 사람 확인으로 넘길 수 없는 것으로 못 박았다.
- 무슨 일이 나나. pack 단계에서 AIDataHub 가 몇 분 흔들리면 그때 걸린 전문가는 그 잡에서 빠진 채 잡이 끝나고 사슬이 post → issues → synth 로 넘어간다. 보고서는 그 전문가 없이 조립된다. 로스터 동결 뒤 레지스트리에서 지워진 전문가(`agent_not_found`)의 셀은 영원히 `pending` 이라 C3 가 닫히지 않고 풀 조작도 없다.
- 고치는 법. WP3b 걸음 8 에서 ① 묶음 재시도를 단계와 무관하게 틱마다 한다(`pack_status='error'` 이고 `retry_at` 이 지난 전문가, 틱당 8명). ② 종료 조건을 '`planned · running` 0 **그리고** 재시도할 `blocked` 0' 으로 고친다 — 재시도할 `blocked` 가 남으면 잡을 끝내지 않고 보류 코드 `aidh_unreachable`(WP5a 3.3.3 의 어휘)로 둔다. ③ `agent_not_found` 전문가의 셀은 코드가 `failed('agent_not_found')` 로 옮겨 사람 처분(다시 · 넘김)의 대상이 되게 한다. C-18 에 `skipped` 의 출발 상태(`failed` 만)를 적는다.

### X4-13 [major] 근거 꾸러미의 실호출 id 와 단위 줄 색인을 읽는 곳이 없어 `tool:b-…` 인용이 '지어낸 참조' 로 세진다

- 근거. WP2 3.8.3 · 7.1 은 B 층 호출(`compare_materials` · `compare_reports` …)의 `tool:b-…` 를 인용으로 인정하려면 "셀·패널의 `SpecContext.call_ids` 에 `evidence_json.calls[].call_id` 를 더해야 한다(WP3·WP4 에 계약)" 고 적고 `review_payload.evidence_call_ids` 와 `units.line_index`(`SpecContext.unit_lines`)를 낸다. WP3b 3.8.6 의 `review_scope` 는 "`_panel_scope` 와 같은 스코프에 `card_pack` 을 얹는다" 뿐이고, WP3b · WP4 전문에 `call_ids` · `evidence_call_ids` · `unit_lines` · `line_index` 가 한 번도 나오지 않는다(grep 0건). 지금 코드에서 `tool:` 참조는 `ctx.call_ids`(= `rr_snapshot_calls.call_id`)에 있어야 통과한다(narrative.py:210, 636~637).
- 무슨 일이 나나. 재질 변경의 전후 물성(material 전문가 한 명이 기대는 유일한 근거 — WP3a 3.3 '세 부류')을 인용한 finding 의 `tool:b-…` 가 dangling 이 되어 등급에서 빠지고 `rr_claim_refs.dangling=1` 로 남는다. snap 단위의 `e:` · `p:` 줄은 대조 기준(`unit_lines`)이 없어 지금처럼 인용문 대조를 건너뛴다.
- 고치는 법. WP3b 걸음 5(narrative 확장)의 `review_scope` 에 두 줄을 더한다 — `call_ids = _panel_scope 의 call_ids | 그 전문가가 대조한 단위들의 evidence_call_ids`, `unit_lines = units.line_index(store, target_key)`. WP4 걸음(쟁점 브리프)의 `_panel_scope` 갈래에도 `issue.unit_id` 의 것을 같은 식으로 더한다. 시험에 'B 층 호출을 인용한 finding 의 dangling 0' 을 넣는다.

### X4-14 [major] 전역 단위와 문맥 줄이 카드 대조 호출에 실릴 자리가 없다 — 0건짜리 전역 단위는 요청 계약에 걸려 잡을 세운다

- 근거. WP2 3.4.3 의 4 — "검토 대상 단위가 둘 이상이면 항목이 0건이어도 [전역 단위를] 만든다(단위 목록·총량 줄을 싣는다 — 묶음 사이 조합을 보는 자리다)", 3.9.1 은 `kind=global` 을 전원 강제 포함으로 둔다. 문맥 줄(이웃 · 경계 · 참고 · 롤업)과 `[부품]` 표는 `context_json` 과 `summary_gz`(사람·패널용 렌더)에만 있고 `review_payload` 의 `lines` 는 소유 줄이다(3.10.4). C-14 의 단위 구조는 `{unit_id, kind, title, summary, lines[{ref, text}], evidence, notes, missing}` 로 닫혀 있고 WP3a 7.1 은 "줄 0개 금지" 다. WP3b 3.7.5 는 422 `bad_request` 를 잡 단위 정지(`paused` + `contract`)로 다룬다.
- 무슨 일이 나나. ① 소유 줄이 0건인 전역 단위의 호출은 `lines` 가 빈다. WP3a 가 '줄 0개 금지' 를 요청 검증으로 걸면 422 가 되고, 첫 호출에서 잡 전체가 `contract` 보류로 선다(자동 재개 없음). 전역 단위는 전원 강제 포함이라 Tier A 첫 전문가에서 바로 난다. ② 줄을 채워 보내더라도 '단위 목록 · 총량' 줄에는 항목 참조가 없다(C-8 이 단위 참조 스킴을 금했다) — `applies=yes` 판정이 가리킬 참조가 없어 그 단위의 finding 은 전부 `weak_subject` 이고 subject 가 비어 한 클러스터로 뭉친다. ③ 묶음 단위의 전문가는 경계 항목을 문맥으로 보지 못한다(WP2 가 U6 까지 두어 만든 문맥 반복이 카드 대조 경로에서는 읽히지 않는다).
- 고치는 법. C-14 에 `context[{ref, text, owner_unit}]` 를 더한다. WP3a 걸음(프롬프트)은 변경 줄 뒤에 '문맥 줄(다른 단위가 맡은 변경 — 판정 근거로 인용할 수 있다)' 블록으로 싣고 같은 L 번호 대역을 이어 매긴다. `unit_size` 식에 넣는다. WP3b 3.8.3 의 소속 확인은 '변경 줄 + 문맥 줄 + 근거 줄' 로 넓힌다. WP2 걸음에서 전역 단위의 '단위 목록' 은 단위마다 대표 변경 줄 1~3개(절댓값 큰 순)를 **그 항목의 `c:` 참조로** 문맥 줄에 싣게 고치고, `lines` 와 `context` 가 둘 다 0건인 단위는 `reviewable=0` 으로 둔다.

### X4-15 [major] 근거 꾸러미 조립의 시간 모형이 검토 루프의 틱과 맞지 않는다

- 근거. WP2 3.8.3 의 `ensure` 는 호출마다 300초 · 전체 3,600초 예산으로 돌고 "전체 예산을 넘기면 남은 호출은 '기한' 으로 적는다", `partial` 도 "동결하고 그 뒤로는 고치지 않는다(다시 하려면 force)". WP3b 3.7.3 은 그것을 2초 틱의 pack 단계에서 부르고 "스레드를 따로 띄우지 않는다" 고 했다. 그 틱이 취소 처리 · 자동 재개 · 다른 타깃 잡의 워커 띄우기 · WP4 제공자 배분을 다 한다.
- 무슨 일이 나나. 예산대로 부르면 틱이 최대 한 시간 막혀 그동안 다른 타깃의 잡과 취소가 멈춘다. 틱을 살리려고 짧은 기한을 넘기면 '기한' 줄이 박힌 `partial` 꾸러미가 동결되어 359명 전원이 `[조회 불가 — 기한]` 을 본다(도구 실패가 아니라 틱 기한 탓이다).
- 고치는 법. WP3b 걸음 8 에서 꾸러미·신호 준비를 워커 자리 하나를 쓰는 준비 작업(`prep`)으로 돌린다(검토 세마포어를 함께 쓴다). `phase='review'` 는 검토 대상 단위 전부의 `evidence_status` 가 NULL 이 아닐 때만 연다. WP2 걸음(unit_evidence)에서 예산 초과로 못 부른 호출이 있는 단위는 동결하지 않고 `evidence_status` 를 NULL 로 남겨 다음 `ensure` 가 잇게 한다('기한' 은 호출 자체가 300초를 넘겼을 때만 적는다).

### X4-16 [major] (가) snap 타깃은 거르는 장치가 전부 꺼져 있어 셀이 만 단위로 서고, 2차 영향의 재료 정의가 없다

- 근거. WP2 3.9.1 은 "snap 타깃의 전 단위" 를 강제 포함으로, WP3b 3.7.4 는 snap 이면 훑기를 건너뛰고 `route_forced='snap'` 으로 둔다. WP2 3.5 의 `joint` 신호군은 tied · touching · geometric · contact 계면 **전부**이고 단위 줄 상한은 70 이다. WP2 8절 6 은 스스로 "리프 1,500 · 계면 6,000 … 셀이 만 단위로 는다" 고 적었다. WP4 3.2.1 `unit_pairs` 는 "그 단위에 속한 `iface.*` · `contact.*` 이벤트의 대상 쌍" 과 "그 단위에서 바뀐 부품" 으로 정의돼 있는데 snap 에는 이벤트도 바뀐 부품도 없다. WP4 3.9.2 의 '미배정 변경 항목' 과 '노출 전수' 도 diff 기준이다(WP2 U1 은 `walk_cids(diff)`).
- 무슨 일이 나나. 단위가 60개면 셀이 21,540 이고 전부 깊이 검토다. WP3b 3.14.1 의 식으로 호출이 5만 건을 넘는다(추정 — 그 문서의 표는 단위 20 · r 0.3 까지만 셈했다). `geometry` 원천의 교차 칸은 0건이 되고 C1 의 1번(미배정 0)은 정의가 없어 구현자가 임의로 정하게 된다.
- 고치는 법. WP2 걸음(신호)의 강제 포함 표에서 'snap 타깃의 전 단위' 를 빼고 snap 단위에도 S-role · S-kind(신호군 → 영역 바닥 표를 `unit-routing` 에 `snap_floor` 로 더한다)를 건다. Tier A 강제는 남는다. `create_review_job` 은 snap 이면 `cells_estimate · calls_estimate` 를 보여 주고 동의를 받는다. WP4 걸음(cross.py)의 `unit_pairs` 에 snap 갈래 — "그 단위가 소유한 `e:` 줄의 양끝 부품" — 를 더한다. `units.unassigned_n` 은 snap 에서 '신호 조건에 걸렸는데 어느 단위도 소유하지 않은 항목 수' 로 정의한다.

### X4-17 [major] (바) 새 리비전의 타깃이 열려도 앞 타깃의 잡과 사슬은 계속 돌고, 새 타깃은 그 뒤에 줄을 선다

- 근거. 지금 코드는 새 타깃을 만들 때 같은 과제의 앞 타깃에 `superseded_by` 만 적는다(routes.py:1920~1927). 그 열을 읽는 곳은 목록 필터 하나뿐이고(routes.py:1803) 잡을 세우는 코드는 없다. WP3b 3.7.3 은 세마포어가 "타깃을 가로질러 하나" 이고 3.7.11 은 "빈 자리를 채우는 순서는 잡의 `created_at`" 이다. 네 설계서 어디에도 `superseded_by` 가 나오지 않는다.
- 무슨 일이 나나. 앞 리비전의 검토(몇 주짜리일 수 있다)가 끝날 때까지 새 리비전은 자리를 거의 받지 못한다 — 먼저 만든 잡이 집을 전문가가 남아 있는 한 빈 자리를 다 채운다. 낡은 리비전의 post · 쟁점 패널 · 종합까지 사슬이 스스로 이어 돈다. 같은 이유로 변경 2건짜리 급한 타깃도 앞선 큰 타깃 뒤에서 기다린다.
- 고치는 법. WP2 걸음(create_target)에서 앞 타깃이 `flow='cells'` 이고 살아 있는 잡이 있으면 그 잡을 `paused` + `hold_code='superseded'`(자동 재개 없음)로 세우고 응답 `superseded.paused_jobs` 에 싣는다(이어 돌릴지는 사람이 정한다). WP3b 걸음 8 의 자리 배분을 잡별 돌려 주기(틱마다 잡을 한 바퀴 돌며 한 자리씩)로 바꾼다. 옛 흐름 타깃 → 새 흐름 타깃 승계에서는 `apply_carry_over` 가 좌석을 `carried` 로 닫는데(planner.py:785~805) `close_review_seat` 는 `carried` 행을 건드리지 않으므로(WP3b 3.4.1), `flow='cells'` 타깃을 만들 때는 좌석 승계를 부르지 않는다(등록부 `invalidate` 만 한다).

### X4-18 [major] 결손 사냥의 호출 id 가 겹치고, 상한에 걸려 남은 `unseen` 칸은 사람 확인으로도 못 닫는다

- 근거. WP4 3.1.2 — `hunt_id = 'mh-' + sha1(target_key|unit_id|domain|post_round)[:16]` 가 PK 다. 3.3.3 — "한 호출의 코드 수 상한은 10 이다(넘으면 호출을 나눈다)", "타깃당 호출 상한은 200 이다. 넘는 칸은 `unseen` 으로 남고 완결 잔여에 잡힌다". 부록 A 에서 첫 소유가 mech 인 코드는 11개다(택소노미 1.1 이면 13개). 3.9.3 C3 의 6 은 "메커니즘 칸에 `unseen · hunting` 이 없다" 이고 3.9.4 의 잔여 `mech_open` 은 `cannot_judge · no_owner · failed` 만 센다.
- 무슨 일이 나나. 한 단위에서 mech 소유 코드가 11개 이상 `unseen` 이면 둘로 나눈 호출이 같은 id 를 받아 둘째가 들어가지 못한다 — 그 칸은 `unseen` 으로 남는다. 상한 200 에 걸린 칸도 `unseen` 이다. 둘 다 C3 의 6 을 영원히 거짓으로 만들고, 잔여 목록에 없어 사람이 확인해 넘길 수도 없다.
- 고치는 법. WP4 걸음(mechgrid.py)에서 `hunt_id` 에 조각 번호를 넣는다(`…|post_round|part_no`). 상한에 걸린 칸은 `unseen` 이 아니라 새 상태 `deferred_cap` 으로 적고 `mech_open` 잔여에 `deferred_cap` 을 더한다(교차 칸과 같은 처리). C3 의 6 은 그대로 둔다.

### X4-19 [major] 입력 결손 전문가를 strong 비율의 분모에서 빼 달라는 WP2 의 요구가 완결 판정에 없다

- 근거. WP2 3.10.2 · 7.1 — "입력 결손 전문가는 strong 비율의 분모에서도 뺀다". WP4 3.9.3 C2 의 3 — "strong 비율 0.7 이상 — `rr_coverage` 의 `done / (done + done_weak)`", 예외가 없다. WP3b 3.4.1 — 입력 결손 길의 셀은 질문 1 의 `yes` 가운데 카드 인용이 재대조를 통과해야 `done` 이고 아니면 `done_weak` 다. C-20 은 `abstain` 규약만 맞췄다.
- 무슨 일이 나나. 훑기가 없는 설정(X4-06)에서는 입력 결손 전문가가 카드 본문을 못 받아 `reviewed` 가 되어도 전부 `done_weak` 다. 예 — 일반 246명 가운데 221명 `done` · 25명 `done_weak`, 입력 결손 110명 가운데 60명 `done_weak`, 카드 0장 3명 `done_weak` 면 221 / 309 = 0.715 다. 조금만 기울면 0.7 아래로 떨어져 C2 가 서지 않고 C3 도 못 선다.
- 고치는 법. WP4 걸음(closure.py)의 strong 비율에서 `rr_roster.input_gaps_json` 이 비어 있지 않은 전문가와 `card_basis='none'` 전문가를 분자·분모에서 빼고, 뺀 수를 `detail.strong_excluded{input_gap, no_cards}` 로 응답에 싣는다.

### X4-20 [major] WP4 가 부르는 WP2 함수의 인자·반환 모양이 WP2 정의와 다르다 — 어긋나면 교차 칸이 조용히 `mech ↔ xd` 로 떨어진다

- 근거. WP4 7.1 — `units.part_roles(store, target_key, ckeys) -> dict[ckey, list[str]]` · `units.role_domains(role)` · `units.unit_domains(…) -> list[{domain, basis}]` · `units.unit_text` · `units.evidence_pack` · `units.unit_refs` · `units.unassigned_n` · `signature_json{change_kinds[], roles[], materials[]}`. WP2 3.3 · 3.7 — `part_roles(store, target_key, unit_id) -> dict[부품(대표 노드 dn), str | None]` · `unit_domains(…) -> dict[영역, list[신호]]` · `change_kinds` 와 `materials` 는 dict 이고 나머지 넷은 이름이 없다(`panel_evidence` · `get_unit` · `ref_index` · `invariants_json.U1_unassigned` 가 가장 가깝다). C-8 은 `load_units` 와 `for_cell` 두 이름만 맞췄다.
- 무슨 일이 나나. WP4 3.2.1 은 역할을 못 찾으면 "`[mech, xd]` 로 본다" 는 폴백이 있다. 키(ckey 대 dn)가 어긋나면 예외 없이 전 부품이 '모름' 이 되어 `geometry` 교차 칸이 mech ↔ xd 한 쌍뿐이 된다 — rf · pwr · disp 로 가는 2차 영향 물음이 빠지는데 오류는 나지 않는다. 부록 B 의 보강 규칙도 `materials` 를 목록으로 읽으면 한 번도 맞지 않는다.
- 고치는 법. 계약에 WP2 → WP4 접점 한 절을 더하고 WP2 걸음에 그대로 구현한다 — `units.part_roles(store, target_key, unit_id) -> {dn: {ckey, role, domains[]}}`, `units.unit_domains(…) -> {domain: [signal…]}`, `units.unit_refs(store, target_key, unit_id) -> set`(소유 줄 + 문맥 줄 + 근거 줄의 참조), `units.unassigned_n`. WP4 걸음(cross.py)은 dn 으로 묻고, '모름' 폴백을 탄 부품 수를 `basis_json.roles_unknown_n` 으로 남겨 진행판에 보이게 한다. 단위 본문과 꾸러미는 `units.panel_evidence` 하나로 읽는다.

### X4-21 [minor] 단위 목록 항목의 크기 식이 다르다

- 근거. WP2 3.3 · 3.13 — `digest_max = sweep.manifest_item_max − 20`(780자, 글만 잰다). WP3a 7.1 — 항목 크기는 `len(text) + len(title) + len(kind) + 14 ≤ 800` 이다. 제목이 30자만 돼도 넘는다. `plan` 이 돌려주는 `oversize.manifest` 를 WP3b 가 어떻게 다루는지는 3.5.3 에 없다(`cards` · `units` 만 있다).
- 고치는 법. WP2 `digest_of` 가 WP3a 식 그대로(`title` · `kind` 포함) 재서 자른다. WP3b 걸음 3 에 "`oversize.manifest` 의 단위는 훑기에서 빠지므로 `route_llm='skipped'`" 한 줄을 넣는다.

### X4-22 [minor] 생성 때 게이트웨이가 불통이었던 타깃은 나중의 최초 로스터 고정이 옛 규칙을 탄다

- 근거. WP2 3.10.1 은 `routes.create_target` 과 `planner.refresh_roster` 만 고친다고 적었다. 지금 코드에는 셋째 길이 있다 — `routes.refresh_roster` 의 '고정된 적이 없는 타깃' 갈래가 `planner.freeze_roster(…, ecad_absent=…)` 를 직접 부른다(routes.py:2108~2112). 새 시그니처의 기본값은 `defer_absent=True` 다.
- 무슨 일이 나나. `flow='cells'` 타깃인데 회로 104명이 `deferred` 로 고정되고 `input_gaps_json` 이 빈다 — 격자는 그들을 일반 전문가로 돌리고(결측 표지 없이 카드 대조) 롤업은 `deferred` 행을 닫지 못한다.
- 고치는 법. WP2 걸음(전원 포함)에서 그 갈래도 타깃의 `flow` 를 읽어 `defer_absent` · `mcad_absent` 를 넘긴다. 시험 하나('로스터 0 으로 열린 cells 타깃의 뒤늦은 고정에 deferred 0').

### X4-23 [minor] `units.roster_query` 의 모양이 쓰임 둘과 맞지 않는다

- 근거. WP2 3.3 — `roster_query(store, target_key, *, max_phrases=6) -> list[str]`(타깃 단위, 저장된 단위를 읽는다). 3.9.2 는 "단위마다 최대 4구절" 을 이 함수가 만든다고 하고, WP3b 3.5.5 · 3.6.3 은 긴 문서 검색어를 "그 구절에서 그 단위 것만 골라" 쓴다. 3.12 의 `create_target` 순서는 `units.compute` → 로스터 조회 → `units.persist` 라 조회 시점에는 저장된 단위가 없다.
- 고치는 법. WP2 걸음에서 `units.phrases(built_or_store, *, unit_id=None, max_phrases=…) -> list[str]` 로 바꾼다 — 타깃 구절은 `compute` 결과에서, 단위 구절은 `rr_units.signals_json.phrases` 에서 준다. 카드 0장 전문가의 검색어가 타깃 공통 구절이 되지 않게 한다.

### X4-24 [minor] reviews 잡이 끝난 뒤 post 잡을 만드는 자리가 정해지지 않았다

- 근거. WP3b 3.7.3 — "그 뒤의 후속 잡을 잇는 것은 WP4 다". WP4 3.11.1 — "지금 `_finish_job` … 같은 방식으로 단계를 잇는다". reviews 잡의 종료는 `review_runner` 안에서 나고 `runner._finish_job` 을 타지 않는다. 범위를 좁힌 잡(전문가 몇 명 · 단위 몇 개)이 끝났을 때도 post 로 넘어가는지, 사람이 `POST …/jobs {mode}` 로 단계를 따로 시작할 때 다른 종류의 살아 있는 잡과 겹쳐도 되는지도 없다(장벽은 WP4 3.0 이 전제로 둔 것이다).
- 고치는 법. WP3b 걸음 8 에 훅 `review_runner.on_job_done(store, job)` 을 두고 WP4 걸음이 `post.chain_next` 를 등록한다. 사슬은 범위가 Tier 전체일 때만 잇는다. `create_review_job` 과 WP4 의 잡 생성에 '그 타깃에 다른 종류의 살아 있는 잡이 있으면 409 `stage_conflict`' 를 넣는다.

### X4-25 [minor] 자동 보류 중인 잡을 사람이 '멈춤' 으로 굳힐 수 없다

- 근거. 지금 `pause_job` 은 `queued · running` 이 아니면 409 다(runner.py:675~677). WP3b 3.7.3 의 1 은 `paused` 이고 `hold_code ∈ (breaker, pack_unavailable)` 이며 `hold_until` 이 지난 잡을 `queued` 로 돌린다.
- 무슨 일이 나나. 차단기가 세운 잡을 사람이 멈추려 하면 409 가 나고 백오프 뒤 스스로 다시 돈다. 남는 수단은 취소뿐이다.
- 고치는 법. WP3b 걸음 8 에서 `pause_job` 이 `paused` + 자동 재개형 `hold_code` 인 잡을 받으면 `hold_code=NULL · hold_until=NULL · pause_reason='user'` 로 바꾼다. 자동 재개 조회에 `pause_reason IS NULL` 을 건다.

### X4-26 [minor] 에이전트 서버가 다른 판으로 다시 뜬 것을 앱이 호출 전에 알 길이 없다

- 근거. WP3b 3.6.1 은 `/limits` 를 다시 읽는 때를 "`limits_rev` 가 어긋났다는 답을 받았을 때" 로 적었는데 WP3a 3.7 의 상태기계에는 그런 답이 없고(422 는 `bad_request` · `over_budget` 뿐), 요청 본문(3.5.0)에 `prompt_rev` · `limits_rev` 가 실리지 않는다. `input_hash` 대조는 셀을 **집을 때** 앱이 가진 값으로 한다(WP3b 3.7.7).
- 무슨 일이 나나. (마) 배포로 프롬프트 틀이 바뀐 서버가 뜨면 도는 셀은 앞 호출은 옛 판, 뒤 호출은 새 판으로 채워진다. WP3a 3.8 의 "판이 다른 결과를 섞지 않는다" 가 깨지지만 드러나지 않는다.
- 고치는 법. WP3a 걸음에서 요청에 `expect{prompt_rev, limits_rev}` 를 받고 다르면 스트림 전에 409 `rev_mismatch{prompt_rev, limits_rev}` 로 답한다. WP3b 는 그 답에서 `/limits` 를 다시 읽고 그 전문가의 계획과 열린 셀을 처음부터 돌린다(차감 없음).

### X4-27 [minor] `ctx_assumed` 의 뜻이 운영 LLM 에서 갈릴 수 있다

- 근거. WP3a 3.3 — `ctx_assumed` 면 "앱은 계획을 짜지 않고 다시 묻는다", WP3b 3.7.3 — "이 틱은 여기서 끝". 지금 `_model_context_tokens` 는 `/v1/models` 가 답했는데 창 크기 칸이 없으면 기본값(128,000)을 **굳힌다**(HWAXAgentServer app.py:2053~2065, 주석 "다시 물어도 같다").
- 무슨 일이 나나. 그 경우를 `ctx_assumed=true` 로 치면 pack 단계가 사유 없이 영원히 돈다. `false` 로 치면 가정한 창으로 예산을 짠다. 어느 쪽인지 정의가 없다.
- 고치는 법. WP3a 걸음에서 `ctx_assumed` 는 '못 물어봐서 다시 물을 예정' 일 때만 참으로 하고, 굳힌 기본값은 `ctx_source='fallback'` + `warnings` 로 알린다. WP3b 는 `ctx_assumed` 가 10분 넘게 이어지면 잡을 보류(`agent_outdated` 와 같은 자동 재개형 코드)로 세워 사유가 화면에 보이게 한다.

### X4-28 [minor] 범위 밖 셀을 만드는지가 문서마다 다르고 C1 이 거기에 걸려 있다

- 근거. WP3b 3.7.1 — "범위 밖 셀은 `pending` 으로 남는다"(격자는 로스터 × 단위 전부). WP5a 3.11 — "범위 밖의 셀은 **만들지 않는다**". WP4 3.9.3 C1 의 1 — "격자가 완전하다", 3.9.2 — "격자 = 셀 수 / (로스터 × 단위 수)". 계약에 없다.
- 고치는 법. 계약에 "격자는 늘 전부 만든다. 범위는 집는 조건이다" 를 적는다(C1 이 Tier A 만 돈 상태에서 서야 하므로).

### X4-29 [minor] '따져 본 메커니즘' 을 받는 쪽은 12개까지만 믿는데 묻는 쪽은 "전부" 를 적으라고 한다

- 근거. WP3a 3.5.3 의 지시 — "이 단위에서 따져 본 메커니즘 **전부**(문제없다고 본 것도 넣는다)", 검사 ② 는 코드가 목록 안인지만 본다. WP4 3.3.2 자격 ⓐ — "그 셀의 `considered` 길이가 12 이하" 가 아니면 자격 없이 `n_unqualified` 로만 센다(`HWAXRISK_MECH_CONSIDER_MAX`).
- 무슨 일이 나나. 목록 38~52개를 받은 모델이 13개 이상을 적으면 그 셀의 '검토함' 이 통째로 버려진다. 격자가 `unseen` 으로 남아 사냥 호출이 늘고 상한 200 에 닿는다(X4-18 과 겹친다).
- 고치는 법. WP3a 걸음(offcard 프롬프트)에 "최대 `extra.seen_max` 개 — 당신 영역에서 실제로 맞대어 본 것만" 을 넣고 넘으면 `quality.seen_over_cap` 을 세운다. 앱이 `extra.seen_max = HWAXRISK_MECH_CONSIDER_MAX` 를 싣는다.

### X4-30 [minor] 완결 판정이 읽는 '노출 전수' 를 만드는 곳이 없다

- 근거. WP4 3.9.2 — "전문가 × 변경 항목 노출 수 / 기대 수 | WP2 · WP3", 응답 예 `exposure{unassigned_changes, exposed: 53850, expected: 53850}`. WP2 는 단위별 `n_changes` 까지만, WP3b 는 셀 상태와 카드 수까지만 낸다. '해당 없음' 셀은 변경 줄이 아니라 780자 요약(`digest`)만 봤다(WP2 3.7.1).
- 고치는 법. WP4 걸음(closure.py)에서 코드로 유도한다고 적는다 — `expected = 로스터 × Σ n_changes`, `exposed = Σ(reviewed · no_input 셀의 n_changes)`, '해당 없음' 셀 몫은 `exposed_digest_only` 로 따로 낸다(본 것과 요약만 본 것을 한 수로 합치지 않는다).

### X4-31 [minor] (다) G2 차단 타깃에 검토 잡을 걸 때 묻는 것이 없다

- 근거. G2 실패는 미확정 same-as 가 한 건이라도 있으면 선다(diff.py:534). WP2 3.4.6 은 차단 타깃도 구조·파라메트릭층으로 평소대로 묶고 잡에 동의를 요구하는 것은 `oversize` 뿐이다. "diff 와 IR 은 불변" 이라(WP2 3.4.8) same-as 를 확정하면 diff 를 새로 만들어야 하고 새 타깃은 처음부터 다시 돈다(C-18 — `carried` 는 이번 범위 밖).
- 무슨 일이 나나. 이름만 바뀐 부품이 '삭제 + 추가' 로 실린 단위를 전원이 검토한 뒤, 확정 한 번에 그 일이 통째로 다시 돈다.
- 고치는 법. WP3b 걸음 8 의 `create_review_job` 이 `rr_unit_builds.blocked_by` 가 있으면 `pending_sameas_n` 과 '확정 뒤에는 새 타깃으로 다시 돈다' 를 응답에 싣고 `consent_blocked: true` 를 요구한다.

---

## 덜어낼 것

- 표본 재검토용 제공자 `'cell_audit'` 와 `cells.run_check`(X4-02) — reviews 잡의 한 단계로 넣으면 필요 없다.
- 단위 5개 이하에서 훑기를 건너뛰는 `few_units` 규칙(X4-06) — 훑기는 전문가당 1~2호출이고 그 답을 세 곳이 읽는다.
- 메커니즘 격자의 자격 ⓑ(카드 태그)와 교차 카드 우선순위 ⓑ(X4-09) — 읽을 태그가 없다.
- 사슬의 '다음 Tier 자동 시작'(X4-11).
- 새 흐름 타깃의 좌석 승계 호출(X4-17).
- 필터를 끄는 손잡이 둘 가운데 하나 — WP2 `HWAXRISK_ROUTE_FILTER=off`(전 셀 강제 포함)와 WP3b `HWAXRISK_REVIEW_SWEEP=off`(훑기 없이 전수 대조)는 같은 일을 두 곳에서 한다. 하나만 남긴다.

## 직접 확인해 맞는 것

- G2 차단 diff 는 구조·파라메트릭층만으로 단위가 선다 — 지금 코드가 `{"blocked_by": "G2", "events": []}` 만 비우고 아래 층을 남긴다(diff.py:1242~1243). WP2 3.4.6 의 처리와 맞는다. 이벤트를 전제로 깨지는 곳은 WP4 `unit_pairs` 의 첫 원천뿐이고 둘째 원천(바뀐 부품의 계면)이 받는다.
- 카드 검토가 닫은 좌석은 다음 타깃으로 `carried` 되지 않는다 — `apply_carry_over` 가 `tool_calls_ok ≥ 1` 을 요구하고(planner.py:788) 검토 의견은 그 값이 null 이다(WP3b 3.4.2). 새 흐름끼리의 두 번째 타깃은 전원이 다시 본다.
- 두 번째 타깃에서 id 가 겹치지 않는다 — `review_id` · `cross_id` · `hunt_id` · `issue_id` · `summary_id` · `call_id` · `report_uid` 가 전부 `target_key` 를 해시에 넣고 `rr_units` 의 PK 도 `(target_key, unit_id)` 다. `rr_card_packs` 만 타깃을 가로질러 재사용된다(내용 주소).
- 취소는 잃는 것이 돌던 호출뿐이다 — 셀은 `pending`, 전문가는 `planned`, 판정 행은 남고(WP3b 3.7.9), 새 reviews 잡의 `plan_cells` 가 멱등이라 남은 호출만 돈다. 지금 `cancel_job` 은 `paused · queued` 잡을 곧바로 `cancelled` 로 닫는다(runner.py:690~702).
- 변경 1~2건이면 단위 하나(전역·경계 없음)이고 격자는 359셀이다(WP2 3.4.6). 깨지는 곳은 없다. 다만 X4-06 때문에 회로 110명이 카드 본문 없이 답한다.
- 쟁점 패널이 끝난 전문가를 다시 앉혀도 원장과 부딪치지 않는다 — `plan_issue_panel` 은 `rr_coverage` 를 건드리지 않고 의견은 `100000 + panel_no` 대역이다(C-7 · WP4 3.7.5).
- '카드 0장' 이 자격의 시야 탓에 거짓으로 생기지는 않는다 — AIDataHub `list_records` 는 호출자 신원으로 거르지 않는다(AIDataHub `api_server/src/api/mcp_runtime.py`:892~918). 자격에 `plat:aidatahub` 가 없으면 도구 자체가 안 보여 팩이 오류로 끝난다(0장으로 보이지 않는다).

## 확인하지 못한 것

- 운영 GLM 의 `/v1/models` 가 창 크기를 주는지(X4-27 의 갈림). `.env` 와 네트워크를 열지 않았다.
- 실제 diff · snap 의 단위 수. 변경 150건 → 단위 약 28개, snap → 60개 안팎은 WP2 3.4.3 의 합성 표와 줄 상한에서 어림한 값이다. X4-05 · X4-16 의 호출 수는 WP3b 3.14.1 의 식과 '호출 5분' 가정을 그대로 쓴 추정이다.
- `FIXED[verdict]` 의 실측값. 운영에서 단위 한도 여유가 626자라는 것(X4-01)은 WP3a 가 가정한 틀 길이 2,600자에 기댄다.
- `failed` 셀에 이미 적힌 판정 행(예 — 13장 가운데 12장)이 그 전문가의 finding 과 보고서에 들어가는지. WP3b 3.10 은 '마감 때 올린다' 고만 적었다. 빠진다면 FAIL 판정이 실패 셀과 함께 묻힌다.
- 근거 꾸러미의 줄 가운데 참조가 없는 것(인접 그래프 줄 · 머리 줄)을 `evidence[{ref, text}]` 에 어떻게 싣는지. `ref` 가 비면 그 줄을 가리킨 판정의 참조가 빈 문자열이 된다.
- 표본 모집단이 0(필터를 끈 타깃 · 작은 diff)일 때 C2 의 6 번('29건 이상 또는 전수')이 참인지.
- WP5a · WP5b · WP1 의 전문. 보류 코드와 사람 처분 절만 읽었다 — 위 문제 가운데 그쪽이 이미 받은 것이 있을 수 있다(읽은 범위에서는 없었다).
