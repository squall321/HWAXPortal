# WP4 설계서 반대 검토 메모 (2026-10-09)

대상 — spec-wp4-issues-synthesis.md. 계약(04-contract.md)이 설계서 본문보다 우선한다는 전제로 읽었다.
문제를 찾는 대로 아래에 덧붙인다.

## P-01 [blocker] 후속 사슬(post→issues→synth)이 Tier 범위 잡마다 돈다 — 대표 15명 결과로 닫은 쟁점·격자·교차 칸이 전원 결과를 덮는다

- 근거(설계서) — 3.11.1 "reviews 끝 → post → issues → synth → (마감 레벨이 C3 이고 Tier 가 남았으면 다음 Tier 의 reviews)", "잡 행의 tier 는 범위(A·B·C)를 그대로 잇는다". 3.6.3 "resolved·inconclusive 는 건드리지 않는다. 새 영역이 다시 제기했으면 reraised_json 만". 3.3.2 "사냥이 닫은 칸(hunted_*·cannot_judge)은 건드리지 않는다". 3.2.4 "다시 묻는 조건 — 후속 회차가 올라갔을 때". 3.5.3 "rejected → code_status='rejected_in_panel'", 3.10.2 "rejected_in_panel → 등급 D(건수만)".
- 근거(코드·형제) — WP3b 3.7.1 `create_review_job(scope={'tier': 'A'|'B'|'C'|None})`, 3.7.3 "Tier A(영역 1순위 15명)가 가장 먼저 돈다". 계약 C-27 "cae00 대표 15명 시범 뒤에 켠다". `config.py:210` 기본 마감 레벨 C2. `registry.py:641` verdict 후보는 status IN ('open','verified') 만 센다.
- 깨지는 길 — ① Tier A 범위(영역당 1명)에서는 중대 이상 클러스터의 `support_experts` 가 거의 다 1 이라 `solo_severe` 가 전부 걸린다. 쟁점 상한 24(P1 48)가 Tier A 에서 소진된다. ② 그 패널(로스터 2석 + 기준선 옹호석)이 기각하면 행이 `rejected_in_panel` 로 가고, Tier B·C 에서 30명이 같은 클러스터를 제기해도 쟁점은 `resolved` 라 다시 열리지 않는다(`reraised_json` 은 '새 영역' 일 때만 표기). 등록부 행은 등급 D(건수만)·판정 후보 제외로 남는다. ③ Tier A 때 사냥이 닫은 메커니즘 칸(`hunted_none`)은 뒤 Tier 에서 누가 제기해도 격자에서 `raised` 로 바뀌지 않는다. ④ 교차 칸은 Tier A 의 한 명 결과로 답이 났고, Tier 가 바뀔 때 `post_round` 가 오르는지 설계서에 없다(오른다면 상한 3 을 Tier 셋이 다 써서 표본 재개방 회차가 0 이 되고, 안 오르면 영영 다시 묻지 않는다).
- 결과 — "모든 전문가가 고려할 수 있는 리스크를 최대한" 이 목표인데 가장 적은 인원의 판정이 가장 많은 인원의 판정을 영구히 덮는다. 시범(15명) 뒤 같은 타깃을 전원으로 넓히는 C-27 의 순서가 그대로 이 길이다.
- 고치는 법(계획서에 옮길 것) — 걸음 7(잡 사슬)에 규칙을 넣는다. "post·issues 는 그 타깃의 **마감 범위 전원**(close_level 이 C3 면 로스터 전원, C2 면 Tier B 범위)의 셀에 pending·running 이 없을 때만 자동으로 잇는다. 그보다 좁은 범위의 reviews 잡 뒤에는 `registry.merge` + `synth`(code_only 보고서)만 잇는다." 사람이 좁은 범위에서 post 를 따로 시작하는 것(`POST jobs {mode}`)은 허용하되, 그때 만든 쟁점·사냥·교차 칸에 `scope_tier` 를 적고 범위가 넓어지면 ⓐ `resolved` 쟁점 가운데 `basis_hash`(제기자 집합)가 바뀐 것을 `queued` 로 되돌리고 ⓑ `rebuild_grid` 가 `hunted_none` 칸에 새 `raised_by` 가 생기면 `raised` 로 덮고 ⓒ 교차 칸의 양성 줄 집합 해시 비교를 `post_round` 와 무관하게 매 post 시작 때 한다. 걸음 5·8 의 시험에 "Tier A 에서 기각된 클러스터를 Tier C 에서 5명이 제기하면 행이 D 로 남지 않는다" 를 넣는다. `post_round` 는 '표본 재개방 회차' 로만 쓰고 Tier 전환과 분리한다(3.0 용어표·3.14 의 상한 3).

## P-02 [blocker] WP3b 의 기본 정책 `hold` 아래에서는 카드 대조 finding 이 등록부에 치명·FAIL 로 들어오지 않는다 — P1·등급 A·split_severity 가 주 경로에서 죽고, 전원이 FAIL 이라 한 클러스터는 쟁점이 되지 않아 영영 FAIL 이 못 된다

- 근거(형제) — WP3b 3.10.3 "hold(기본) — 실효 판정 FAIL 도 등록부에는 중대·WARNING. 원래 값은 judgement_claimed·severity_claimed 에 남는다. 등록부의 FAIL 은 쟁점 패널(WP4)이나 사람이 올린다", 3.13 `HWAXRISK_REVIEW_FINDING_POLICY=hold`. WP4 설계서에는 `hold`·`judgement_claimed`·`severity_claimed` 라는 낱말이 한 번도 없다(grep 0건). 계약에도 없다.
- 근거(설계서) — 3.6.2 `p_class = "P1" if sev3 == 3 or judgement == "FAIL"`. 3.10.2 `severe = sev3 == 3 or judgement == "FAIL"` 이어야 등급 A. 3.6.1 `split_severity` = "두 단계 벌어짐(경미 대 치명) 또는 FAIL 과 OK 가 함께". 쟁점 유형 다섯 어디에도 "전문가가 FAIL 이라 했는데 등록부가 보류 중" 이 없다.
- 깨지는 길 — 카드 대조에서 12명이 같은 변경을 FAIL 로 본 클러스터는 등록부에 중대·WARNING · 제기 12명으로 선다. 단독도 아니고(`solo_severe` 아님) '문제없음' 반대자도 없으면 쟁점이 아니다. 쟁점이 아니니 패널이 안 열리고, 패널이 안 열리니 FAIL 로 올릴 주체가 없다. 판정 후보는 `conditional` 에 머물고(`registry.py:662-665`) 보고서 "주의 등급 A 전부" 는 빈 표다. "P1 은 상한의 예외" 는 2차 영향·사냥 finding(이쪽은 `_normalize_finding` 에 모델 값이 그대로 들어가 치명이 될 수 있다)에만 걸려, 한 명짜리 2차 영향이 12명짜리 카드 위반보다 먼저 토의된다.
- 시험과의 어긋남 — 5.2 "P1 30건이면 30건이 전부 queued" 는 공장이 FAIL 원자를 직접 넣어야 통과한다. 운영 경로(hold)는 그 모양을 만들지 않는다.
- 고치는 법 — ① 3.6.1 에 여섯째 유형 `held_fail` 을 더한다 — 살아 있는 원자의 `finding_json.judgement_claimed == 'FAIL'`(또는 `severity_claimed == '치명'`)이 1건 이상인 클러스터. 반대 측이 없으면 인접 석으로 앉힌다. ② `p_class`·`attention_of`·`split_severity` 의 입력을 `max(등록부 값, claimed 값)` 으로 바꾼다(등록부 열은 그대로 두고 `merged_json.claimed_max{severity, judgement, n}` 을 병합이 채운다 — 걸음 2). ③ `held_fail` 이 상한 밖(`untried_cap`)이면 보고서 recommendation 에 "전문가 N명이 FAIL 로 봤으나 미토의" 를 건수가 아니라 행으로 싣는다. ④ 걸음 2·8 의 공장은 WP3b `expert_report.build_findings(policy='hold')` 를 실제로 거친 finding 으로 단언한다. 계약에 C-33 으로 "hold 정책과 쟁점 선정의 이음" 을 적는다.

## P-03 [major] `split_verdict` 와 메커니즘 자격 ⓑ 가 기대는 '카드의 메커니즘 태그' 는 없다

- 근거(자료) — `03-cards.md` 카드 JSON 의 `card` 머리는 `tier·type·card_id·sources·expert_id·fact_refs·confidence·causal_status·review_status·standard_refs·token_estimate` 뿐이다. 태그 분포도 type·tier·confidence 셋뿐이다. 메커니즘 태그가 없다.
- 근거(형제) — WP3b 3.2 `rr_card_verdicts.mech` 는 "solo 가 채운다"(WARNING·FAIL 확인과 표본에만 도는 단독 재질의). OK 행에는 메커니즘이 없다. WP3b 7.1 은 그 `mech` 칸조차 "WP3a 에 청한다, 지금 초안에는 없다" 고 적었다.
- 근거(설계서) — 3.6.1 `split_verdict` = "다른 전문가가 **같은 대분류의 카드로** '적용되고 문제없음'". 3.3.2 ⓑ "'적용' 판정을 낸 카드 가운데 **메커니즘 태그가 m** 인 것". 3.2.3 카드 우선순위 ⓑ "같은 태그의 카드". 7.1 `rr_card_verdicts.mechanism_code(카드 태그)`.
- 깨지는 길 — 대분류 조건을 못 세우면 둘 중 하나다. 조건을 빼면 인기 있는 변경 줄(예 배면 커버 두께)에는 100명 넘는 전문가 가운데 '적용·OK' 가 반드시 있어(WP3b 3.9.2 "판정 행의 약 9할이 음성") 중대 클러스터가 거의 전부 `split_verdict` 가 되고, 가중 1.3(최고)이라 상한 24 를 가짜 불일치가 채운다. 조건을 두면 OK 행에 값이 없어 한 건도 안 잡힌다. 자격 ⓑ 는 늘 거짓이라 ⓐ(영역 + 길이 12)만 남는다(P-04).
- 고치는 법 — 걸음 8 의 `split_verdict` 를 "같은 단위에서 같은 변경 참조에 대해 ⓐ 같은 메커니즘 **코드**의 finding 을 낸 전문가와 ⓑ 그 코드를 `mechs_json.considered` 에 적고 그 변경 참조에 `applies='yes'·OK`(`quote_ok=1`)를 낸 전문가가 함께 있다" 로 다시 정의한다(카드 태그가 아니라 셀의 `mechs_json` 과 판정 행의 `refs_json` 만 쓴다). 반대자 2명 이상일 때만 올린다(설정값). 3.3.2 ⓑ 와 3.2.3 ⓑ 는 지운다. 7.1 의 `mechanism_code(카드 태그)` 요구를 뺀다.

## P-04 [major] 도장찍기 한도 12 의 근거가 설계서 자신의 부록과 어긋난다 — 성실한 mech·xd·rel 전문가가 자격을 잃고, 사냥 상한을 넘긴 `unseen` 은 C3 를 영영 막는다

- 근거(설계서) — 3.3.2 "12 는 한 영역이 소유·관련으로 걸리는 코드 수의 최댓값 근처". 부록 A 를 세어 보면(스크립트로 집계) 소유+관련 코드 수는 mech 28 · rel 17 · material 16 · xd 15 · sim 14 · disp 13 · pcb 13 이고, 1.1 의 14종을 더하면 mech 40 · xd 23 · rel 21 이다. 12 를 넘는 영역이 15개 중 7개다.
- 근거(설계서) — 3.3.3 "타깃당 호출 상한 200. 넘는 칸은 unseen 으로 남고 완결 잔여에 잡힌다". 그런데 3.9.3 C3-6 은 "메커니즘 칸에 unseen·hunting 이 없다" 이고, 3.9.4 의 잔여 `mech_open` 은 `cannot_judge·no_owner·failed` 만 센다. `unseen` 을 확인(ack)으로 넘기는 길도, 사람이 칸을 넘기는 REST 도 없다(3.12.1 에 `PUT /mech/...` 가 없다 — 교차 칸과 쟁점에만 있다).
- 깨지는 길 — mech 전문가가 실제로 15개 메커니즘을 따져 `considered` 에 적으면 길이 조건으로 ⓐ 자격을 전부 잃는다(`n_unqualified` 로만 센다). 칸이 `unseen` 으로 남아 사냥이 는다. 단위 25개면 격자 1,300칸이고 (단위 × 첫 소유 영역) 묶음이 단위당 12~15건이라 300건을 넘겨 상한 200 에 걸린다. 걸린 칸은 `unseen` 인 채 C3-6 을 막고 풀 길이 env 상향 + 재기동뿐이다.
- 고치는 법 — ① 걸음 5 에서 길이 한도를 상수 12 가 아니라 "그 전문가 영역의 `owners ∪ related` 코드 수" 로 둔다(자산에서 계산). 도장찍기는 "영역 밖 코드까지 전부 적었다" 로 잡는다. ② 3.9.4 의 `mech_open` 에 `unseen(상한 초과)` 을 넣고 3.3.1 상태에 `deferred_cap` 을 더한다(교차 칸과 같은 처리). ③ 3.12.1 에 `PUT /mech/{target}/{unit}/{code}` `{action: run|skip, reason}` 을 더한다. 걸음 9 의 시험에 "사냥 상한을 넘긴 타깃이 확인으로 C3 에 닿는다" 를 넣는다.

## P-05 [major] '해당 없음' 표본 재검토를 실제로 돌릴 주체가 없다 — WP4 는 `cells.run_check` 를 부르고 WP3b 는 그 함수를 두지 않는다

- 근거(설계서) — 3.4.1 "표본으로 뽑힌 셀에 WP3 의 카드 대조(check)를 그대로 돌린다", 3.11.1 표 "post — 한 일 단위: 교차 칸·사냥 호출·**표본 셀**", 3.11.4 제공자 이름에 `cell_audit`, 7.1 `cells.run_check(store, engine, target_key, unit_id, agent_key, purpose='audit')`.
- 근거(형제) — WP3b 7.2 "다시 연 셀은 보통 셀처럼 내 루프가 돈다 — **따로 부르는 run_check 는 두지 않는다**", 3.9.3 "검토 루프가 다시 열린 셀을 보통 셀과 똑같이 대조한다. 따로 도는 길이 없다", 3.7.11 "제공자의 일 하나는 `engine.run(provider.build_request(item))` **한 번**이다"(셀 검토는 묶음별 verdict·rev·solo·offcard 로 호출이 여럿이다), 3.3.3 "타깃 하나에 살아 있는 검토 잡은 하나", 3.7.3 "`_review_tick` 은 mode='reviews' 잡에만 전문가 세션을 돈다". 계약은 C-18 의 전이만 적고 주체를 정하지 않았다.
- 깨지는 길 — post 잡은 `rr_cell_audits` 행을 `pending` 으로 만들지만 그것을 집을 제공자가 설 수 없다(호출 한 번짜리가 아니다). 표본 셀을 `reopen(via='audit')` 으로 열어도 그 셀을 돌릴 `reviews` 잡이 없고, 만들면 그 잡이 끝날 때 3.11.1 의 "reviews 끝 → post" 가 **새 post 잡**을 또 만든다(같은 회차의 post 가 둘). post 의 마감 조건 "세 표에 pending·running 이 없다" 는 영영 참이 되지 않거나, 표본이 안 돈 채 참이 된다. 또 6절의 타깃 장벽("셀에 pending·running 이 없을 때만 계획")을 post 자신의 표본 재개방이 깬다.
- 고치는 법 — 걸음 6·7 을 다음으로 바꾼다. ① post 를 세 국면으로 가른다 — `plan`(병합·교차 칸·격자·사냥 계획·표본 선정) → `audit_wait` → `close`. ② `plan` 끝에 `review_cells.reopen(cells=표본, via='audit')` 을 부르고 `mode='reviews'` · `chain_json.purpose='audit'` · `scope.cells=[…]` 인 자식 잡을 만든다. post 잡은 `running` 인 채 그 잡의 종료를 기다린다(교차·사냥 제공자는 그동안 돈다 — 표본 셀은 `na_irrelevant` 였으므로 보내는 영역 요약에 영향이 없다). ③ reviews 잡 종료 훅은 `purpose` 가 `audit` 이면 새 post 를 만들지 않는다. ④ `close` 는 `rr_review_cells.audit_result`(WP3b)와 셀 건수로 `risk_miss·relevance_miss·kept` 를 가른다. `rr_cell_audits.state` 의 `running·failed` 는 셀 상태에서 유도하고 따로 굴리지 않는다. ⑤ 7.1 에서 `cells.run_check` 를 지우고 WP3b 의 `reopen`·`na_population`·`audit_result` 로 바꾼다. 걸음 7 의 통합 시험에 "표본 59건이 실제 검토 루프(가짜 엔진)로 돌고 post 가 한 번만 마감한다" 를 넣는다.

## P-06 [major] 사슬을 굴리는 손이 비어 있다 — `advance_post` 를 부르는 곳, post·synth 잡을 닫는 곳, reviews→post 를 잇는 곳, `persist_single_findings` 를 만드는 곳이 어느 설계서에도 없다

- 근거(설계서) — 3.11.2 `advance_post` "후속 잡의 한 틱(멱등)", 3.11.4 `WorkProvider` 는 `claim·build_request·complete·fail·recover` 다섯뿐(틱·시작·마감 훅 없음). 4절 걸음 7 의 바뀌는 파일은 `post.py · runner.py(claim_next_job · _finish_job · 복구)` 이고 `review_runner.py` 가 없다. 7.1 은 `narrative.persist_single_findings` 를 "WP3 에서 받는 것" 으로 적었다.
- 근거(형제) — WP3b 3.7.11 "`_review_tick` 은 등록된 제공자의 modes 에 드는 잡에는 그 제공자의 `claim` 을 묻는다" 가 전부다(claim 이 None 일 때 '아직' 과 '끝' 을 가르는 규칙, 잡을 `completed` 로 닫는 규칙이 없다). WP3b 3.7.3 "그 뒤의 후속 잡을 잇는 것은 WP4 다"(검토 잡은 `review_runner` 안에서 `completed` 로 닫힌다 — `runner._finish_job` 을 지나지 않는다). WP3b 7.1 은 `persist_single_findings` 를 "WP4 에서 받는 것(선택)" 으로 적었다 — 둘이 서로에게서 받는다. 계약에 이 함수는 없다.
- 근거(코드) — `runner.py:900-913` `_finish_job` 은 `run_panel` 이 편성할 패널이 없을 때만 불린다(`runner.py:998-999`). post·synth 는 `claim_next_job` 대상이 아니라(3.7.4 `mode IN ('panels','issues')`) 이 길로 닫히지 않는다. `narrative._normalize_finding(…, ctx: SpecContext, …)`(`narrative.py:970`)은 패널 스코프가 있어야 돌고, 지금 스코프를 만드는 함수는 `_panel_scope(store, panel_id)`(`narrative.py:1453`) 하나다.
- 깨지는 길 — 구현자가 접점을 문자 그대로 만들면 ① post 잡은 집히지만 교차 칸이 0개라(계획을 아무도 안 불렀다) `claim` 이 None 만 돌려주고 잡이 `running` 에 남는다. ② reviews 가 끝나도 post 가 생기지 않는다. ③ 교차·사냥 응답을 finding 으로 올릴 함수가 없다.
- 고치는 법 — ① 계약에 접점을 적는다. `WorkProvider` 에 `tick(store, job) -> {'done': bool, 'next': [{mode, chain}]}` 를 더하고, `_review_tick` 이 제공자 잡마다 `claim` 전에 `tick` 을 부르며 `done` 이면 잡을 `completed` 로 닫고 `next` 를 만든다. WP3b 의 검토 잡 마감에는 `on_job_closed(store, job)` 콜백 자리를 두고 WP4 가 `post.on_reviews_closed` 를 등록한다. ② 걸음 7 의 파일에 `review_runner.py`(접점 두 줄)와 `tests/test_review_runner.py` 를 넣고 선행에 "WP3b 걸음 8(제공자 접점)" 을 적는다. ③ `persist_single_findings` 와 그것이 쓰는 스코프(`narrative.single_scope(store, target_key, agent_key, unit_id)` — 대표의 얼린 카드 묶음·단위 줄 색인을 싣는다)는 **WP4 걸음 2** 가 만든다고 못박고 WP3b 는 그것을 쓴다(순서 — WP3b 걸음 9 보다 먼저 나가야 하므로 걸음 2 를 WP3b 앞으로 당기거나 WP3b 가 만든다. 계약에서 주인을 하나로 정한다).

## P-07 [major] 계약 C-13 의 `cross` 는 WP3a 판인데, WP4 의 뒤 단계가 읽는 칸이 그 출력에 없다 — `hunt`·`summary` 는 계약의 다섯 종류에 아예 없다

- 근거(계약) — C-13 "호출 종류 다섯 — sweep · verdict · offcard · noinput · cross. 요청 1건 = 전문가 × 단위 × 카드 묶음 1개. 출력은 JSON Lines".
- 근거(형제) — WP3a 3.5.5 `cross` 의 입력은 `unit` · `digest`(받는 대표의 카드 **제목만**) · `extra.peer` 이고 출력 줄은 `x{impact, title, path, a[], l[], sev, conf, check_kind, check}` · `conflict{a[], l[], why}` · `none{why}` 다.
- 근거(설계서) — 3.2.3·3.2.4 는 `effects[].mechanism`(격자와 클러스터 키), `card_refs`(카드 인용), `mechanisms_considered`(격자의 '검토함'), `reopen_src`(표본 강제 — 3.2.1 "창발 리스크를 잡는 유일한 길"), `no_effect.reason_code`(네 낱말)을 읽는다. 3.11.3 은 `hunt`·`summary` 를 더 쓰고, 일반 호출이 없으면 걸음 13 이 `card_review.py` 에 종류 셋을 더한다고 했다.
- 깨지는 길 — 계약대로 WP3a 의 `cross` 를 쓰면 ① 2차 영향 finding 에 메커니즘이 없어 전부 `process|unclassified` 로 정규화된다(`narrative.py:963-966`). 카드 대조에서 나온 같은 리스크의 클러스터와 키가 달라 합쳐지지 않고 `support_experts=1` 짜리 새 행이 된다. ② `mechanisms_considered` 가 없어 격자의 그 입력이 0 이다. ③ `reopen_src` 가 없어 3.4.3 의 강제 표본이 한 건도 안 생긴다. ④ 카드 본문이 실리지 않으니 "카드를 함께 인용하라" 가 불가능하고 2차 영향은 전부 경험칙이다. ⑤ `summary` 는 전문가도 단위도 카드도 없는 호출이라 C-13 의 요청 정의에 들지 않는다.
- 고치는 법 — 계약에 C-13b 를 더한다. "`cross` 의 `x` 줄에 `mech`·`mech_free` 를 더하고(offcard 의 `f` 줄과 같은 규칙), `m{seen[]}` 줄과 `reopen{a[], why}` 줄을 받는다. `none` 에 `code`(no_path·out_of_domain·covered_by_src·needs_input)를 더한다. `cards`(전문)를 받는다(없으면 digest). 종류 `hunt`(행 = 물은 코드 전부, `missing` 은 빠진 코드)와 `summary`(expert 없음, 중립 서기 시스템 글)를 여섯째·일곱째로 둔다." 이 변경은 WP3a 걸음 9(그쪽이 'WP4 가 쓰는 것' 이라 적은 걸음)에 넣고 WP4 걸음 13 을 지운다(같은 모듈을 두 꾸러미가 고치지 않는다). WP4 의 3.2.3 출력 예는 JSON Lines 로 다시 쓴다. 걸음 4·5 의 시험은 WP3a 의 계약 픽스처(`tests/fixtures/card_review/contract/`)의 `cross` 결과를 그대로 먹인다.

## P-08 [major] 통합 보고서가 사슬의 맨 끝에서만 조립된다 — 쟁점 잡이나 요약 잡이 멈추면 보고서가 한 판도 없다

- 근거(설계서) — 3.8.4 "보고서를 만드는 때 — 종합 잡이 끝났을 때 · 레벨이 올랐을 때 · 확인했을 때 · 사람이 시킬 때". 3.8.1·6절 "LLM 이 죽어도 보고서는 나온다(code_only)". 3.11.1 "취소된 잡은 다음 잡을 만들지 않는다". 3.7.7 "연속 3패널 오류 → 잡 실패 — 쟁점 패널에 적용한다".
- 근거(코드·형제) — `runner.py:1104-1105` 연속 오류면 잡 `failed`. WP3b 3.7.6 차단기는 제공자 잡에도 건다(3.7.11 "실패 구분·차단기를 루프가 대신 해 준다") — 인프라 실패율이 높으면 `paused(breaker)` 로 8번(약 2시간) 뒤 사람을 기다리고, 내용 실패율이 높으면 `content_fail_rate` 로 **자동 재개 없이** 멈춘다. 인프라 실패는 차감이 없어 요약 행은 `pending` 에 머문다(`code_only` 로 가지 않는다).
- 깨지는 길 — ① 쟁점 패널 셋이 연달아 엔진 오류면 issues 잡이 `failed` 로 끝나고 synth 가 안 생긴다. ② LLM 이 내려가 있으면 synth 잡은 차단기에 잡혀 멈추고 `assemble_report` 는 불리지 않는다. ③ dev(16K 창)에서는 요약 입력이 `over_budget`(422, 내용 탓)로 거듭 거절돼 `content_fail_rate` 차단기가 synth 잡을 세운다. 세 경우 모두 며칠 돈 카드 대조 결과가 있는데 과제 보고서가 없다. 새 흐름에서는 `close_level(persist=True)` 를 부르는 곳도 쟁점 패널 완료와 synth 끝뿐이라 레벨도 C0 에 머문다.
- 고치는 법 — ① 걸음 10 을 둘로 가른다. 10a "코드 조립본" — LLM 0회. post 의 `close` 국면이 끝나면 `closure.close_level(persist=True)` 와 `synth.assemble_report(trigger='post_done')` 를 그 자리에서 부른다(요약 자리는 "서술 없음"). 10b "서술" — synth 잡이 요약을 붙여 새 판을 낸다. ② issues 잡이 `failed` 로 닫혀도 남은 `queued` 쟁점을 `untried_cap`(사유 `engine_fail`)으로 옮기고 synth 를 잇는다(3.11.1 표에 "failed 도 잇는다, cancelled 만 끊는다"). ③ 요약 제공자의 `fail` 은 `over_budget` 을 차감·차단기 집계에서 빼고 서버가 준 `have` 로 행 수를 한 번에 맞춘다. 같은 요약이 2회 실패하면 그 행을 `code_only` 로 닫는다(인프라 실패도 6회 뒤 `code_only`). ④ 걸음 7 의 시험에 "엔진이 전부 실패해도 `rr_reports` 에 판이 하나 있다" 를 넣는다.

## P-09 [major] 사슬이 다음 잡을 만들 때 요청자·자격을 잇는 규칙이 없다 — 며칠 뒤 자격이 없으면 사슬이 예외로 끊기고 흔적이 없다

- 근거(코드) — `runner.py:900-913` `_finish_job` 은 다음 잡을 `create_job(..., owner_sub=job["owner_sub"], modifiers, user_memo, consent=True)` 로 만든다(`requester_sub` 를 넘기지 않는다). `runner.py:613-616` `create_job` 은 자격이 없으면 `AppError("pat_unavailable", 422)` 를 던진다. `config.py` 주석의 PAT 등록 하한은 86,400초(하루)다.
- 근거(설계서) — 3.11.1 "같은 방식으로 단계를 잇는다". 6절 표에 자격 만료 줄이 없다. WP3b 3.7.1 `create_review_job` 도 "자격이 없으면 422 pat_unavailable" 이다.
- 깨지는 길 — 검토 4~8일(WP3b 8절) 뒤에 post·issues·synth·재개방 reviews 가 차례로 만들어진다. 그 시점에 요청자 PAT 가 만료돼 있으면 ① 요청자가 승계되지 않아 쟁점 패널 좌석 조회가 소유자·서비스 시야로 바뀐다(진행판은 요청자 자격이라 적혀 있던 실행이다). ② 소유자·서비스 자격도 없으면 다음 잡 생성이 예외로 죽는다. 앞 잡은 이미 `completed` 라 화면에는 "끝났다" 만 보이고 사슬은 조용히 멈춘다.
- 고치는 법 — 걸음 7 에 넣는다. ① 사슬이 만드는 잡은 `params_json` 의 `requester·consent·user_memo·modifiers·knobs` 를 앞 잡에서 복사하고 `chain_json.root_job_id` 를 잇는다. ② 사슬 생성은 자격 검사를 하지 않는다(행은 반드시 만든다 — `state='queued'`, 자격이 없으면 `error='pat_unavailable…'`). 집는 쪽(`claim_next_job` · `_review_tick`)이 이미 자격 없는 잡을 건너뛰며 사유를 적는다(`runner.py:741-748`). ③ 자격이 바뀌면 `rr_jobs.credential_email` 과 보고서 머리의 "자격이 도중에 바뀌었다" 표기(WP5a 3.x)를 그대로 쓴다. ④ 6절에 "자격 만료" 줄을 넣고 시험 — 가짜 자격 해석기가 사슬 중간부터 None 을 돌려줘도 다음 잡 행이 생기고 `error` 가 적힌다.

## P-10 [major] 다시 물은 교차 칸·격자가 옛 결과를 치우지 않는다 — 사라진 2차 영향이 등록부에 남고, 사냥이 닫은 칸은 뒤에 제기돼도 '없음' 으로 보인다

- 근거(설계서) — 3.2.4 "다시 묻는 조건 — … pending 으로 되돌린다", 5번 "`claim_uid = '<cross_id>#F<n>'`"(응답 안 순번). 응답 처리 여덟 걸음에 "이 칸이 앞서 만든 finding 을 지운다" 가 없다. 3.3.2 "사냥이 닫은 칸은 건드리지 않는다".
- 근거(형제) — WP3b 3.10.2 는 같은 문제를 "새 집합에 없는 finding 과 그 `rr_claim_refs` 를 지운다 · id 는 내용 해시에서(순번이면 뒤 번호가 밀린다)" 로 풀었다.
- 깨지는 길 — 칸을 다시 물어 영향이 3건에서 1건으로 줄면 `#F2·#F3` 이 `rr_findings` 에 남아 병합마다 살아난다. `none` 으로 바뀌어도 옛 finding 3건은 그대로다. 순번이라 다시 물은 `#F1` 이 다른 내용이면 `INSERT` 가 `claim_uid UNIQUE`(`risk_store.py:326`)에 걸리거나(REPLACE 면 `cluster_key` '삽입 시 동결' 이 깨진다) 한다. 격자는 `hunted_none` 인 칸에 뒤 회차 전문가가 그 메커니즘으로 finding 을 내도 `raised` 로 바뀌지 않아 보고서 격자 표와 등록부가 어긋난다.
- 고치는 법 — 걸음 4·5 에 넣는다. ① 교차·사냥 finding 의 id 를 `'<cross_id>#F' + int(sha1(cluster_key|unit_id)[:8], 16)` 로 둔다(WP3b 와 같은 식). ② `apply_cross_result`·사냥 응답 저장은 한 트랜잭션에서 `source_id = cross_id`(또는 `hunt_id`)인 옛 finding 가운데 새 집합에 없는 것과 그 `rr_claim_refs` 를 지운다. ③ `rebuild_grid` 는 `hunted_none·cannot_judge` 칸이라도 `raised_by` 가 1명 이상이면 `raised` 로 올리고 `hunt_id` 는 남긴다(`hunted_risk` 만 건드리지 않는다). 시험 — "영향 3 → 1 로 다시 답하면 finding 이 1건", "hunted_none 칸에 뒤늦은 제기가 오면 raised".

## P-11 [major] 계약 C-2 는 새 흐름의 표·열 전부를 v4 한 블록으로 **첫 커밋에** 싣게 한다 — WP4 의 표 여덟은 가장 늦게 검증되는데 가장 먼저 굳는다

- 근거(계약) — C-1 순서 WP1 → (WP2 ∥ WP3a) → WP3b → WP4. C-2 "v4 = 새 흐름의 표·열 전부를 한 블록으로(새 흐름 첫 커밋). 한 번 push 된 버전의 DDL 은 고치지 않는다".
- 근거(코드) — `risk_store.py:561` 허용 연산은 `CREATE TABLE IF NOT EXISTS · ADD COLUMN · CREATE INDEX IF NOT EXISTS` 뿐이다. PK·UNIQUE 는 뒤에 못 고친다(`rr_seat_opinions` 의 UNIQUE 가 그 예 — 설계서 3.7.5).
- 깨지는 자리(이 검토에서 이미 나온 것) — `rr_cross_cells` 는 대표가 2명인 영역(xd)의 호출 둘을 한 행에 담지 못한다(`rep_agent_key·output_gz·prompt_hash·attempts` 가 하나뿐 — 3.2.2 의 3번과 3.1.2 가 어긋난다). `rr_close_acks` 의 PK `(target_key, item)` 는 다시 확인하면 앞 확인 행을 덮는다(관례로 든 `rr_gate_acks` 는 '취소는 표기' 인데 재확인 이력이 남지 않는다). `rr_mech_cells` 에 상한 초과 상태·사람 처분 사유 열이 모자란다(P-04). 운영 열 이름은 C-21 로 또 바뀐다.
- 고치는 법 — 계약 C-2 를 고친다. "v4 = WP2·WP3b 의 표·열. **WP4 의 표 여덟과 열은 WP4 걸음 1 에서 v5 로** 싣는다(걸음 4~10 의 시험이 그 DDL 위에서 초록인 뒤 push 한다)." WP4 걸음 1 의 선행을 "WP5 의 판번호" 에서 "v5, WP3b 병합 뒤" 로 바꾼다. 그 전에 위 세 자리를 고친다 — 교차 칸 대표는 1명으로(아래 cuts), `rr_close_acks` PK 에 `ack_at` 을 더하고 '유효한 확인' 은 `revoked_at IS NULL` 인 최신 행으로 읽는다.

## P-12 [major] C2 조건 5 가 기대는 `_unresolved_parse_failures` 는 `error` 로 닫힌 패널을 전부 센다 — 쟁점 패널이 한 번이라도 끊기면 C2(기본 마감)가 영영 안 된다

- 근거(코드) — `registry.py:892-904` 는 `status IN ('done','error')` 이고 `risk_spec_parsed = 0` 이며 `quality.spec_excluded` 가 없는 패널을 센다. `spec_excluded` 를 **쓰는** 코드는 앱에 없다(grep — 읽는 곳 `registry.py:901` 한 줄뿐, 시험이 직접 UPDATE 한다 `tests/test_registry.py:718-720`). `runner.py:776-781` 재기동 복구와 `runner.py:1098-1103` 엔진 오류는 패널을 `error` 로 닫고 `risk_spec_parsed` 는 0 으로 남는다.
- 근거(설계서) — 3.9.3 C2-5 "파싱 못 한 쟁점 패널이 0 이다(`_unresolved_parse_failures`)". 3.11.5·3.7.4 "쟁점 패널이 끊기면 `error('restart')` 로 닫고 쟁점을 `queued` 로" — 다시 돌 때는 새 `panel_no` 의 새 행이고 옛 `error` 행은 남는다.
- 깨지는 길 — 쟁점 패널 24~48건이 하루 이틀 도는 동안 재기동·스트림 유실·엔진 자리 없음으로 `error` 행이 하나라도 생기면(코드 주석이 "벽시계 12시간이라 패널 도중의 재기동은 드문 일이 아니다" 라 적은 일이다) 그 행이 영구히 1 로 세져 `c2` 가 거짓이다. 사람이 풀 API 가 없다. 새 흐름 타깃은 C1 에 머문다.
- 고치는 법 — 걸음 9 에서 새 흐름의 조건 5 를 패널이 아니라 **쟁점**으로 센다 — "P1 쟁점 가운데 `state='inconclusive'` 이고 사유가 `spec_parse_failed` 인 것이 0". 옛 `error` 패널 행은 그 쟁점의 최신 패널이 아니면 세지 않는다. 걸음 9 의 시험 — "쟁점 패널이 restart 로 한 번 끊긴 뒤 다시 돌아 resolved 면 c2 가 참". 옛 흐름의 같은 함수는 손대지 않는다(WP1 에 알린다 — 옛 흐름에서도 `error` 패널 하나가 C2 를 막고 풀 길이 없다).

## P-13 [major] 기본 마감(C2)에서는 입력 결손이 깊이 조건을 그냥 통과하고 표기에도 안 붙는다 — WP2 가 빼 달라고 한 것을 안 뺐다

- 근거(설계서) — 3.9.3 C2-2 "셀이 전부 종결인 전문가 수 … 지금 식(`registry.py:950-958`)을 `rr_coverage` 롤업 위에서 그대로 쓴다". 3.9.4 규칙 2 "잔여가 0 이 아니면 맨 **C3** 로 적지 않는다"(C2·C2(closed) 의 표기 규칙은 없다). 3.9.3 "새 흐름에는 deferred 가 없다".
- 근거(코드) — 지금 식은 `active = size − deferred` 로 보류 좌석을 분모·분자에서 뺀다(`registry.py:951-955`). `abstain` 은 종결이다(`registry.py:38`). `config.py:210` 기본 마감은 C2 다.
- 근거(형제) — WP3b 3.4.1 입력 결손 전문가의 롤업은 `abstain` + `reason='no_input:<gap>'`. WP2 7.1 "WP4 — `close_level` 이 `rr_coverage.reason LIKE 'no_input:%'` 를 '검토함' 에서 빼고 입력 결손 전문가를 strong 분모에서 뺀다".
- 깨지는 길 — ECAD 가 없는 과제(지금 dev·cae00 의 보통 경우)에서 회로 여섯 영역 110명이 전부 `abstain(no_input)` 이어도 '종결' 로 세져 깊이 조건이 참이다. 타깃은 `C2(closed)` 로 닫히고 표기는 맨 `C2(closed)` 다. 옛 흐름은 같은 경우를 `deferred` 로 분모에서 빼고 화면에 보였는데, 새 흐름은 그 구분을 잃는다. 사람 확인(ack)도 C3 에서만 요구된다.
- 고치는 법 — 걸음 9. ① C2-2 의 분자·분모에서 `reason LIKE 'no_input:%'` 인 행을 뺀다(옛 식의 `deferred` 자리). 남는 인원이 0 인 영역은 조건을 면하되 잔여 `no_input` 으로 잡는다. ② `level_label` 규칙을 레벨과 무관하게 건다 — 잔여가 0 이 아니면 `C2(closed)(입력 결손 N셀)` 처럼 붙인다. ③ 마감 레벨이 C2 인 타깃도 `no_input` 잔여의 확인을 받아야 `C2(closed)` 가 된다(안 받으면 `C2 · 마감 대기(…)`). 시험 — "회로 영역 전원이 no_input 인 타깃은 확인 전에 C2(closed) 가 아니다".

## P-14 [minor→major] 교차 칸의 `handoff` 는 LLM 이 쓴 영역 이름을 검증 없이 키로 쓴다

- 근거(설계서) — 3.2.1 의사코드 `add(cand, cell.domain, h.to_domain, "handoff")` — `a != b` 검사는 geometry 갈래에만 있다. `state = "pending" if dst in roster_domains else "no_rep"`. 원천 가중은 handoff 가 4.0 으로 가장 높다. 3.9.4 잔여 `cross_open` 은 `no_rep` 을 센다.
- 근거(형제) — WP3a 3.5.3 `{"t":"h","to":"영역 코드",…}` 의 검사 ①~⑦ 에 `to` 가 영역 목록 안인지가 없다.
- 깨지는 길 — 모델이 `to` 에 "audio"·"안테나"·자기 영역을 쓰면 PK 가 다른 `no_rep` 행(또는 자기 자신에게 묻는 행)이 생긴다. 우선순위가 가장 높아 단위당 상한 24 의 앞자리를 먹고, C3 에서 "교차 미실행 N칸" 으로 사람 확인을 요구한다. 359명 × 단위 수의 셀이 넘김을 자유롭게 쓰면 단위당 방향쌍이 210 에 가까워져 대부분이 `deferred_cap` 이 된다(추정 — 넘김 빈도는 실측이 없다). WP2 의 `part-roles`(pcb → pcb·passive·soc·mem)로 세면 역할 셋(battery·housing·pcb)짜리 단위 하나의 geometry 만으로 방향 행이 28 이라 "handoff·geometry 는 상한에 거의 걸리지 않는다" 는 설계서의 셈도 맞지 않는다.
- 고치는 법 — 걸음 4. ① 넘김의 `to_domain` 은 택소노미 영역 코드로 정규화하고(라벨·동의어 사전), 못 맞추면 행을 만들지 않고 `basis_json.invalid_handoffs[]` 와 보고서 품질 표에 센다. 자기 영역은 버린다. ② 같은 (단위, src→dst) 넘김은 지목한 전문가 수를 우선순위에 넣는다(1명이 쓴 넘김과 20명이 쓴 넘김을 가른다). ③ 단위당 상한은 원천별로 따로 둔다(handoff·geometry 는 상한 없음 + 타깃 상한만). 계약에 "WP3a 는 `h.to` 를 받은 영역 목록으로 검사한다" 를 더한다.

## P-15 [minor] 소유 영역 표가 material 을 일곱 코드의 첫 소유로 두는데, 그 영역의 유일한 전문가는 지식카드가 0장이다

- 근거 — 부록 A 의 `material.*` 6종과 `process.adhesive_cure` 는 첫 소유가 material 이다. 3.3.3 "칸의 소유 영역은 owners(m) 가운데 로스터에 있는 **첫** 영역". `03-cards.md` — material 영역 1명, "카드 0장인 전문가 — material-twin-analyst". 부록 A 끝의 "그 호출이 실패하면 둘째 소유 영역으로 내려간다" 는 3.3.3 본문에 없다(실패가 아니라 답이 오므로 내려갈 일도 없다).
- 깨지는 길 — 재질 메커니즘 사냥이 전부 카드 없는 한 명에게 가서 `basis='heuristic'` 답으로 칸이 닫힌다. rel 20명(관련 카드 보유)에게는 가지 않는다.
- 고치는 법 — 걸음 5 의 대표 선정에 "점검형 카드가 1장 이상인 사람" 을 먼저 두고, 소유 영역에 그런 사람이 없으면 다음 소유 영역으로 내려간다. 부록 A 의 material 계열 첫 소유를 `rel` 로 바꾸거나 둘 다에게 묻는다. 시험 — "첫 소유 영역의 전원이 카드 0장이면 둘째 소유 영역 대표가 뽑힌다".

## P-16 [minor] WP1 이 먼저 내는 보고서 자리(`rr_targets.report_gz` · `GET /targets/{key}/report`)와 WP4 의 `rr_reports` 가 겹친다

- 근거 — WP1 3.9 "`build_consolidated_report` 가 `UPDATE rr_targets SET report_gz…` 로 적는다. `GET /api/targets/{target_key}/report?fresh=0|1` → `{target_key, level, report_level, built_at, stored, report{title, tags, blocks, level}}`. 보고서 조립 실패는 패널 완료를 무르지 않는다(try/except)". 계약 C-2 는 그 세 열을 v3 에 넣었다. WP4 3.12.1 은 같은 경로를 "(새)" 로 적고 `?version=&page=` · `pages` 모양을 준다. 3.7.4 는 "`raised` 면 `rr_reports` 에 남긴다" 만 적고 try/except 가 없다(`runner.py:1383-1385` 는 완료 트랜잭션 안이다).
- 깨지는 길 — WP1 뒤에 WP4 가 나가면 같은 경로의 응답 모양이 바뀌거나(프런트가 본 `report.blocks` 가 사라진다) 옛 흐름 보고서가 두 곳에 따로 적힌다. WP4 판 조립이 완료 트랜잭션 안에서 예외를 내면 패널 완료 전체가 롤백돼 패널이 `running` 에 남는다(2.2 ① 과 같은 모양의 고착).
- 고치는 법 — 걸음 10 에 적는다. "`GET /targets/{key}/report` 는 WP1 의 키(`level·report_level·built_at·stored·report{title,tags,blocks}`)를 그대로 주고 `version_no·pages[]·level_label·counts` 를 더한다(`report.blocks` 는 1쪽). `rr_targets.report_gz` 는 더 쓰지 않고 읽을 때 `rr_reports` 가 없으면 폴백으로만 읽는다. 조립 호출은 완료 트랜잭션 **밖**에서 try/except 로 감싼다(WP1 규칙 그대로)."

## P-17 [minor] 묶음 — 작은 어긋남과 틀린 주장

1. **틀린 코드 주장.** 2.2 ⑧·9절 "risk_spec 스키마의 domain enum 은 12개(mem·std·material 이 없다)" — 실제는 15개다(`schemas/risk_spec.v1.json` definitions.domain = xd·sim·cam·rel·soc·disp·mech·pcb·rf·passive·pwr·sh·mem·std·material, seat_domain 은 delib 까지 16). 12개인 것은 `change_kind` enum 이다. 설계가 기대는 자리는 아니지만 9절의 미확인 항목에서 지운다. 같은 스키마의 `finding.mechanism` enum 은 대분류 6개다 — 3.3.4 의 "mechanism enum 값 추가" 는 대분류 `optical·acoustic·rf` 셋을 뜻한다고 걸음 3 에 못박는다.
2. **MCP 도구 수.** 3.12.2·걸음 12·계약 C-30 "14 → 18". WP2 가 `risk_get_units`(15), WP3b 가 `risk_get_cells`·`risk_get_expert_report`(17)를 먼저 더하므로 WP4 뒤는 21 이다. 걸음 12 의 단언을 "앞 목록 + 넷" 으로 쓰고 C-30 을 고친다.
3. **dev 에서 쟁점 근거가 통째로 빠진다.** 엔진 근거 예산은 16K 창에서 2,000자다(`deliberation.py:226` `max(2000, …)`, `:234`). 근거 순서가 I0(600) → I0c(1,000, `runner.py:427` 이 둘째 칸에 끼운다) → I1 이라 I1(쟁점 정의)부터 뒤가 전부 떨어진다(`deliberation.py:4236-4238` 은 넘는 첫 항목에서 끊고 뒤를 다 버린다). 5.3 의 dev 확인 "결정문의 finding 이 닻 클러스터에 붙었는지" 는 구조적으로 통과할 수 없다. 걸음 8 — I1 을 맨 앞에, I4·I5 를 그다음에 두고 예산은 `limits.engine_evid_budget`(WP3a)에서 받는다(C-32). 5.3 의 그 줄은 cae00 으로 옮긴다.
4. **쟁점 결과 판정의 구멍.** `mixed_direction` 쟁점에서 패널이 "개선이다" 로 정하면 닻 키의 리스크 원자가 없어 `inconclusive(no_matching_atom)` 가 된다(3.7.6 표). 닻 키의 살아 있는 원자가 둘 이상일 때 어느 값을 쓰는지도 없다. 걸음 8 — "닻 키에 개선 원자만 있으면 `resolved/rejected`", "여럿이면 `sev3` 최댓값" 을 표에 더한다.
5. **옛 패널이 쟁점 결과를 덮는다.** `POST /panels/{id}/complete` 재제출과 늦게 끝난 옛 워커가 `resolve_issue` 를 부를 때 그 패널이 쟁점의 현재 `panel_id` 인지 보지 않는다(3.7.6·3.12.1). `resolve_issue` 는 `rr_issues.panel_id == panel_id` 일 때만 쓰고, 아니면 결과만 패널 행에 남긴다.
6. **별칭 접기.** 3.5.2 가 종합 직전에 병합 후보를 사람 큐에 올리는데, 사람이 병합하면 `resolve_cluster_key`(`registry.py:534-537`)가 닻 키를 새 키로 접어 3.5.3 의 `anchor_cluster_key` 조회가 빗나간다. `merge()` 가 쟁점을 넘길 때 닻 키도 `resolve_cluster_key` 를 거치게 하고, 한 행에 쟁점 결과가 둘이면 더 엄한 쪽을 쓴다. 3.3.4(다)로 갈린 미분류 클러스터는 `family_key` 가 여전히 같아(`registry.py:349-353` 은 열 값 `unclassified` 로 만든다) `scan_cluster_merge` 가 방금 가른 것들을 병합 후보로 다시 올린다 — 미분류는 `family_key` 에도 `free_key` 를 넣는다.
7. **쟁점 패널의 인용 스코프.** WP2 7.1 은 "쟁점 패널이 `SpecContext.call_ids`·`unit_lines` 를 채우지 않으면 `tool:b-…` 인용이 dangling" 이라 적었고 WP3b 7.2 는 `_panel_scope` 가 좌석의 얼린 카드 묶음을 싣는다고 했다. WP4 걸음 8 의 파일 목록에 `narrative.py`(`_panel_scope` 의 쟁점 갈래 · 닻 키 맞춤 · 성격 진술 건너뛰기)가 없다. 넣는다.
8. **비공개 과제.** 3.8.5 는 비공개면 통합 보고서를 RA 에 안 올리는 것을 "지금 관례" 라 했는데, 패널 한 건마다 엔진이 RA 심의 보고서를 만든다(`deliberation.py:5011` `save_report` 기본 1, 러너는 그 값을 싣지 않고 포털 `DelibOpts` 에 선언도 없다). 쟁점 패널 24~48건의 보고서(쟁점 근거 I4~I6 의 원문이 든다)는 비공개 과제에서도 RA 에 생긴다. 8절 6번 질문에 이 사실을 같이 적고, 막으려면 엔진·포털에 `save_report` 를 선언하는 걸음이 필요하다(이번 범위 밖이면 그렇게 적는다).
9. **단위 0개.** 6절 "보고서는 수치가 0 인 채로 한 판 나온다" — WP3b `create_review_job` 은 단위가 없으면 409 `units_absent` 라 사슬이 시작되지 않는다. 그 줄을 "사람이 `POST /targets/{key}/report` 를 부르면" 으로 고친다.
10. **재제기 비교의 폴백.** 3.5.1 "기준선에 영역 수가 없으면 `support` 로 비교" — 새 흐름의 `support` 는 전문가 수라 옛 타깃에서 사람이 기각한 행(`support_at_decision` 1~3)이 새 타깃마다 '더 강한 근거' 로 표기된다(`registry.py:578-586`). 폴백은 새 행의 `support_domains` 를 옛 `support_at_decision` 과 견준다.
11. **5.3 의 dev 실주행.** 합성 타깃을 어디에 두는지(운영 중인 dev 앱 DB 인지 임시 인스턴스인지), 앱을 어떻게 다시 띄우는지가 없다. 운영 DB 에 넣으면 합성 finding 이 과제 간 통계(`rr_delta_priors` — `registry.py:466-512` 는 코퍼스 제외를 보지 않는다)에 섞인다. "임시 데이터 디렉터리 + 빈 포트의 앱 인스턴스(HEAXHub 인스턴스는 건드리지 않는다)" 로 못박고, 재기동은 그 임시 프로세스만 한다.
12. **판단어 린터와 화면 말.** 3.2.3 요약 초안의 "문제없음"·"판단 불가"·"중대/WARNING"·"결론이 아니다" 는 `render.py:58-71` 의 L06·L15·L16·L17 에 걸린다(허용 꼴은 `severity=중대` · `judgement=OK` · "결론 아님"). 계약 C-16 의 두 문장(화면 말은 `verdict_class` 한 곳 / 코드 문장은 린터 통과)이 서로 부딪친다. 걸음 4 에서 요약 줄을 `judgement=…`·`severity=…` 꼴로 쓰거나, 그 요약이 판정 행의 전사라는 근거로 린터 대상에서 뺀다고 계약에 적는다.
13. **5초 폴링.** 3.9.2 "전부 GROUP BY 집계라 폴링에서 불러도 된다" — `coverage_payload` 는 폴링마다 `close_level(persist=False)` 를 부르고(`routes.py:2214`) 새 경로의 C2-5 는 `_contested_marking_done`(`registry.py:874-889` — 그 타깃 `rr_findings.finding_json` 전부를 읽어 JSON 을 푼다)을 쓴다. finding 이 수천 건이면 폴링마다 수 MB 다. 판정 결과를 병합·셀 마감 때 계산해 `rr_targets` 에 캐시하고 폴링은 캐시와 GROUP BY 만 읽는다.
14. **노출 전수.** 3.9.2 `counts.exposure{exposed, expected}` 를 내는 함수가 WP2·WP3b 어디에도 없다(`units.unassigned_n` 도 없다 — WP2 는 `rr_unit_builds.invariants_json.U1_unassigned` 를 준다). 격자가 완전하면 늘 같은 값이라 뜻도 없다. `unassigned_changes` 만 남기고 뺀다.
15. **snap 타깃의 교차 칸.** 3.2.1 `unit_pairs` 는 "그 단위의 iface.*·contact.* **이벤트**" 와 "그 단위에서 **바뀐** 부품" 으로만 정의돼 있다. snap 단위에는 이벤트도 바뀐 부품도 없고 변경 종류가 `none` 이라 보강 쌍 S1·S3·S4·S6·S7·S8 도 안 걸린다. 현황 타깃의 2차 영향은 넘김과 S2·S5 뿐이다. 걸음 4 — snap 단위는 그 단위가 소유한 `e:` 참조의 양끝 부품으로 쌍을 만든다고 적거나, "snap 은 넘김만" 이라고 범위를 밝힌다.

---

## 뺄 것 · 미룰 것 (cuts)

| 무엇 | 왜 | 잃는 것 | 언제 다시 |
|---|---|---|---|
| 결손 사냥 호출(`rr_mech_hunts` · `plan_hunts` · `hunt` 종류)과 C3 조건 6. 격자 집계와 보고서 표는 남긴다 | 방법이 검증된 적 없고(설계서 9절) 자격 규칙의 전제 둘이 틀렸으며(P-03·P-04) 소유 표가 승인 전이다('sh' 뜻 미상). 전원이 이미 전 단위를 본다 | 아무도 안 적은 메커니즘을 다시 묻는 능동 질의. 그 칸은 격자에 '미검토' 로 보인다 | 첫 전원 실주행에서 미검토 칸의 수와 분포를 본 뒤 |
| 교차 칸의 `supplement` · `adjacency` 원천과 `cross-pairs.v1.json` | geometry 가 닿거나 가까운 쌍을 양방향으로 이미 만든다. 승인할 자산이 하나 준다. adjacency 는 설계서가 "0 에 가까우면 먼저 끈다" 고 한 원천이다 | 닿지도 가깝지도 않은 부품 사이의 물리 쌍(열 경로 등) | 교차 칸이 새로 만든 클러스터 수를 잰 뒤 |
| 큰 영역 대표 2명(3.2.2 의 3번) | xd 한 영역에만 걸리고 행 스키마·제공자 계약(일 하나 = 호출 하나)과 안 맞는다 | xd 의 2차 영향 답이 한 사람 의견이 된다 | 대표 한 명의 답이 얇다는 실측이 나오면 |
| 표본 재검토의 층 자동 재개방 · 회차 3 · 강제 표본. 표본 59건(또는 전수)을 돌려 상한을 공표하고 놓침 셀만 reviewed 로 바꾸는 데까지 | 놓침 1건에 층 전체를 여는 규칙은 5% 허용 기준과 어긋난다(참 놓침률 3% 면 59건에서 1건 이상 나올 확률 83%). 주체 문제(P-05)도 단순해진다 | 자동 수렴. 상한이 5% 를 넘으면 C3 는 대기로 남고 사람이 층 재개방을 누른다 | 층별 놓침 분포가 실측으로 나온 뒤 |
| RA 저장(걸음 11 — `push_report_to_ra` · `ra_*` 열 · 쪽 단위 이어 보내기 · 판마다 새 RA 보고서) | 기본값(비공개)에서는 한 번도 안 돈다. RA 한도·소유 워크스페이스·재전송 동작을 모른다(설계서 9절). 전송기가 운영에서 돈 적이 없다(`main.py:118`) | RA 에서 통합 보고서를 못 본다(앱 REST·MCP 로 읽는다) | 8절 6번 결정과 `describe_template` 확인 뒤 별도 걸음 |
| 영역 요약의 단위별 분할과 롤업(`scope_kind='domain_unit'`) | 등급 A·B 행은 코드 표로 전부 실린다. 2단 요약은 의존 순서와 입력 해시가 복잡하다 | 행이 180 을 넘는 영역(xd)의 서술이 상위 180행만 본다 | xd 요약이 실제로 얇다고 읽히면 |
| 쟁점 유형 `split_severity` · `mixed_direction` | hold 정책 아래 `split_severity` 는 발화하지 않는다. `mixed_direction` 은 결과 판정 구멍이 있다(P-17-4) | 리스크·개선이 엇갈린 대상의 자동 토의(보고서 표에는 나란히 보인다) | `held_fail` · `split_verdict` · `solo_severe` · `cross_dissent` 가 안정된 뒤 |
| `topic_key`(L2 묶음) · `view=topics` | 프런트가 다른 세션이고 보고서는 등급으로 이미 접힌다 | 같은 부품의 클러스터를 묶어 보는 화면 | 프런트가 그 화면을 만들 때 |
| `scripts/replay_post.py`(기록 재생) | 설계서도 "실물이 생긴 뒤" 라 적었다 | LLM 없는 회귀 재생 | cae00 첫 실제 타깃 뒤 |
| MCP 읽기 도구 `risk_get_cross` · `risk_get_mech_grid` | 보고서 도구가 같은 표를 준다 | MCP 에서 칸 단위 조회 | 요청이 있을 때 |

## 직접 확인해 맞았던 주장 (confirmed)

- 2.2 ① — `attribute_events` 는 반대석 키를 늘 넣고(`runner.py:153-157`), 회차는 `rr_coverage` 에서만 읽어 반대석은 1 이며(`narrative.py:1623-1631`), `UNIQUE(target_key, agent_key, cycle)`(`risk_store.py:322`)에 두 번째 패널이 걸린다. 지우는 것은 같은 `panel_id` 뿐이다.
- 2.2 ② — INSERT 가 상태를 문자열 `"open"` 으로 박는다(`narrative.py:1737` 부근). 병합은 열을 읽는다(`registry.py:196-198`).
- 2.2 ③ — `close_level` 반환에 `raised` 가 없고(`registry.py:1012-1036`) 러너는 그 키를 본다(`runner.py:1384`). `RA_REPORT_TOOLS` 에 `create_report_draft` 가 없고(`ra_client.py:23`) 전송기가 주입되지 않는다(`main.py:118`).
- 2.2 ④⑤⑥⑦ — `_cross_domain_lines` 의 키(`registry.py:1148-1160`), `open_items` 의 `text`(`registry.py:1296-1299`), 영역 필터의 `merged.domain`(`routes.py:2320`), `report_ids_json` 의 두 뜻(`planner.py:257-274` · `routes.py:1826-1858`), 미분류 접기(`narrative.py:963-966`).
- 엔진 — 2라운드면 반박이 없다(`deliberation.py:4338-4339`). 지정 반대석 자동 착석(`:4043-4046`). 128K 창의 근거 예산 17,967자(식을 손으로 다시 계산). RA 항목 2,000자 상한과 쪽 추가 호출(`:132-136` · `:5052-5057`). 1R 조회 문맥 `base[:4000]`(`:4487`).
- 자산 — 인접 표 고유 쌍 22개 · 비대칭 4건 · mech–rf 등 6쌍 부재. 택소노미 38종 = 9·8·6·5·5·5.
- 통계 — 필요한 표본 59 · 93 · 124 · 153 · 181.
- 스키마 — `rr_panels.tier` 에 CHECK 없음, `rr_audit.scope` 에 `target` 있음, `rr_gate_acks.gate` 는 G1~G7 CHECK, `rr_jobs.pause_reason` 은 세 값 CHECK.
- 그 밖 — `test_close_level_*` 13건, 쟁점 패널 예산 추정 87 ≤ 120, JS 엔진 한도 12건 · 11,000자 · 2,000자, `create_report_draft` · `update_report_draft` 의 `dry_run` · `page` 인자(도구 스키마로 확인).

## 확인하지 못한 것 (unknowns)

- 계약 C-18 "failed 는 종결이 아니다 — 사람이 정해야 **실행이 끝난다**" 가 검토 잡의 종료를 막는다는 뜻인지. WP3b 는 "열린 실패가 남아도 completed" 라 적었다. 막는다는 뜻이면 실패 셀 하나에 후속 사슬 전체가 사람을 기다린다.
- 운영자가 같은 타깃을 Tier 범위로 나눠 돌릴지(P-01 의 전제). C-27 의 시범 순서와 "같은 diff 에는 타깃 하나" 규칙으로는 그렇게 된다고 읽었다.
- 의장이 쟁점 패널에서 기각을 `status='rejected_in_panel'` 로 적는 비율, 닻의 네 필드를 따르는 비율(설계서도 미확인으로 적었다).
- 넘김(`h` 줄)이 실제로 얼마나 자주 나오는지, 클러스터 수, 쟁점 수 — 실물 다건 diff 가 없다.
- RA 쪽 — 블록·쪽 한도, 서비스 쓰기 자격으로 만든 보고서의 소유 워크스페이스, 같은 쪽 재전송의 병합 동작. `RaClient` 는 운영에서 한 번도 돈 적이 없어 cae00 의 프록시·NO_PROXY·사내 CA 를 처음 지난다.
- 프런트가 `tier='I'` · `level_label` · `GET /reports` 의 `report_id` 없음에 어떻게 반응하는지(프런트는 읽지 않았다).
- cae00 의 모델 창 크기와 로스터 구성(자료는 dev 기준 359명 · material 1명 · 128K 가정이다).
- 재배포 때 옛 프로세스와 새 프로세스의 러너가 겹치는 구간이 있는지(WP5a 의 러너 잠금이 먼저 나가는지). 겹치면 P-17-5 의 가드가 필수다.
- 비우기 신호가 선 동안 `claim_next_job` 이 새 쟁점 패널을 집지 않게 하는 고리(WP5a 가 한다고 적었고 WP4 에는 없다).
- 코드는 돌리지 않았다. 2.2 ① 의 재현은 줄을 읽어 확인한 것이다.

## 판정 (verdict)

뼈대(셀 기반 완결 판정 · 병합 수리 · 쟁점만 패널로)와 지금 코드에 대한 주장은 거의 맞는다(틀린 것은 domain enum 12개 한 건). 그러나 이대로는 서지 않는다 — 이음매 두 곳이 목표를 뒤집는다. 후속 사슬이 Tier 범위마다 돌아 대표 15명의 기각·사냥 결과가 전원 결과를 덮고(P-01), WP3b 의 기본 정책 `hold` 때문에 여럿이 FAIL 로 본 클러스터일수록 쟁점이 못 돼 FAIL 이 안 된다(P-02). 그 밖에 사슬과 표본 재검토를 실제로 굴리는 손이 어느 설계서에도 없고(P-05·P-06), 계약의 `cross` 호출에는 WP4 가 읽는 칸이 없다(P-07). 계획서에 옮기기 전에 P-01·P-02·P-05·P-06·P-07·P-08 을 고치고 cuts 로 범위를 줄이면 선다.
