# WP3b 셀 원장·러너 설계서 — 반대 검토 메모

대상 설계서는 `spec-wp3b-cells-runner.md` 다. 대조한 코드는 HWAXRisk 7248651(dev HEAD) 등이다.
문제를 찾을 때마다 아래에 덧붙인다. 계약(04-contract.md)이 이미 조정한 어긋남은 다시 적지 않는다.

## P-01 [blocker] `review_runner.py` 를 두 설계서가 서로 다른 뼈대로 만든다 — 계약이 주인을 정하지 않았다

- 근거. WP3b §3.1·§3.7 과 걸음 8 은 `review_runner.py` 를 **전문가 세션 단위**(`claim_next_expert`·`run_expert`·`finalize_expert`·메모리 `Breaker`·`WorkProvider`)로 만든다. WP5a §3.3(spec-wp5a-ops.md:401~560)과 걸음 R6 은 같은 파일을 **작업 항목 단위**(`Grid`·`Item`·`Outcome`·`Executor`·`claim_next`·`settle`·`recover(boot_id)`·`advance` S0~S6)로 만든다.
- 계약 C-21 은 열 이름만 WP5a 로 통일했다. 그런데 이름만 바꿔서는 맞지 않는다 — `lease_owner` 는 프로세스 boot_id 이고 WP3b 의 `claim_id` 는 선점마다 새 값이다(WP3b §3.7.7 의 '늦게 온 결과가 덮지 못한다' 는 선점마다 새 값이어야 선다). `tries` 는 '호출을 내보낸 횟수' 이고 WP3b `attempts` 는 내용 탓 실패 수다(= `charged`). `infra_streak` 는 연속 수(성공하면 0), WP3b `infra_retries` 는 누적이다. WP3b §7.3 #12 의 '순수 개명' 은 틀렸다.
- 보류 코드 어휘도 다르다(WP3b `breaker·pack_unavailable·content_fail_rate·contract` vs WP5a `llm_outage·aidh_unreachable·needs_disposition·credential·engine_busy·agent_outdated…`). 차단기 창도 다르다(WP3b 는 프로세스 메모리, WP5a 는 `rr_review_calls` 최근 20건). 실패 분류의 정본도 둘이다(WP3b §3.7.5 는 서버의 `infra` 한 비트, WP5a §3.3.4 는 코드별 표 + `wait·capacity·input` 부류).
- 이대로 가면. 두 꾸러미가 같은 파일·같은 시험 파일(`tests/test_review_runner.py`)을 다른 구조로 쓴다. 먼저 들어간 쪽이 뒤쪽 걸음을 통째로 무효로 만든다.
- 고치는 법. 계획서 맨 앞에 '러너 뼈대의 주인' 을 한 줄로 정한다. 권고 — **선점 단위는 전문가 세션(WP3b)** 으로 한다(훑기·묶음 계획·마감·보고서가 전부 전문가 단위이고, WP5a 의 Grid 에는 훑기와 마감이 들어갈 표가 없다). **실패 분류표·보류 코드·백오프·차단기·`recover`·잠금은 WP5a §3.3.4~3.3.7 을 유일한 구현**으로 하고 WP3b §3.7.5·§3.7.6 을 지운다. 열은 C-21 대로 쓰되 `lease_owner` 에는 `<boot_id>:<claim uuid>` 를 넣어 두 뜻을 다 담는다. `WorkProvider`(WP4 제안)와 `Executor`(WP5a) 는 하나로 합친다. WP3b 걸음 8 과 WP5a R6 을 한 걸음으로 합치고 파일 소유자를 적는다.

## P-02 [blocker] 서버 관문이 '자리 없음' 을 1초 안에 돌려주면(C-24) WP3b 표는 그것을 인프라 실패로 세어 셀을 failed 로 굳히고 차단기를 계속 튕긴다

- 근거. 계약 C-24 는 줄을 세우지 않고 `error{code:'review_busy', retry_after_s}` 로 답한다고 정했고, 기본 동시 수는 앱 4 · 서버 4, **챗·심의가 돌면 서버 2** 다. WP3b §3.7.5 는 '가르는 것은 서버가 실어 준 `infra` 다. 앱은 코드 이름을 따로 외우지 않는다' 고 하고 `error{infra:true}(busy …)` 를 인프라 탓으로 둔다 — `infra_retries + 1`, 백오프 30·60·120·300·600·900초, 6 을 넘기면 `failed('infra_exhausted')`. §3.7.6 차단기는 인프라 **연속 5회** 에 잡을 `paused` 로 만든다.
- 이대로 가면. 심의 하나가 도는 동안(패널 벽시계 12시간) 앱 워커 4 중 2 가 호출마다 1초 안에 `review_busy` 를 받는다. 워커는 전문가를 놓고(§3.7.5), 2초 뒤 틱이 다음 전문가를 집어 또 `review_busy` 를 받는다. 성공 호출은 5분에 한두 건인데 `review_busy` 는 2초마다 두 건이라 **수 초 안에 연속 5회** 가 차 차단기가 선다. 잡이 `paused` 가 되면 `_stop_reader`(runner.py:1193~1216, `STOP_JOB_STATES` 에 `paused` 가 있다)가 **멀쩡히 돌던 호출 2건의 스트림도 닫는다**. 60초 뒤 반쯤 열려 한 건이 성공하면 다시 4 워커가 뜨고 같은 일이 되풀이된다. 순서가 앞선 전문가의 첫 셀은 30+60+120+300+600+900초(약 34분) 안에 7번 튕겨 `failed('infra_exhausted')` 가 되고 사람의 처분을 기다린다. 챗·심의와 같이 도는 것이 정상 운영이므로 이것은 드문 경우가 아니다.
- 계약의 빈칸. C-26 은 실패를 인프라·내용 둘로만 가른다. '기다림' 부류가 계약에 없다(WP5a §3.3.4 에만 `wait` 가 있다). `review_busy` 프레임에 `infra` 표지가 실리지 않으면 더 나쁘다 — WP3b 표로는 내용 탓이 되어 2회 만에 `failed` 이고, 차단기는 `content_fail_rate` 로 멈춰 스스로 돌아오지도 않는다.
- 고치는 법. (1) 계약에 세 번째 부류 `wait` 를 넣는다 — `review_busy`·포털 429·비우기. `infra_retries`·`attempts`·차단기 어디에도 세지 않는다. (2) `review_busy` 를 받은 워커는 **셀과 전문가를 놓지 않고** 그 자리에서 `stop.wait(retry_after_s)` 뒤 같은 호출을 다시 낸다(지금 `EngineBusy` 대기 루프 runner.py:1037~1066 과 같은 자리). 놓으면 다음 전문가가 같은 벽에 부딪힐 뿐이다. (3) 러너는 `review_busy` 프레임의 `limit`(또는 `/health` 의 `card_review.limit`)을 읽어 그 수를 넘겨 새 워커를 띄우지 않는다. (4) 차단기가 잡을 멈출 때 `paused` 가 아니라 '새 호출을 내지 않음' 표지로 하거나, 워커의 `should_stop` 이 `hold_code` 가 있는 `paused` 는 '호출 경계에서 놓기' 로 읽게 한다(§3.7.6 의 '다음 호출 경계에서 선점을 놓는다' 가 지금 `_stop_reader` 로는 성립하지 않는다). (5) §5.2 통합 시험에 '가짜 엔진이 동시 2 를 넘는 호출에 review_busy 를 준다 → 셀의 infra_retries 0 · 차단기 닫힘 · 잡 completed' 를 넣는다.

## P-03 [blocker] 훑기를 건너뛰는 길에서는 배경 카드(전체의 57%)와 입력 결손 전문가의 카드가 어느 호출에도 전문으로 실리지 않는다

- 근거(설계서). §3.5.1 — 배경 카드는 '훑기에서 전문으로 읽히고, 카드 대조에서는 제목만, 카드 밖 호출에서는 **훑기에 걸린 것**이 전문으로 실린다'. §3.7.4 — 입력 결손 길의 `noinput` 은 '`cards` 에는 **훑기가 그 단위에 건 카드**를 전문으로'. 같은 절의 표 — snap 타깃 · 검토 단위 5개 이하(`few_units`) · `sweep='off'` · 놓침률 초과(`filter_off`)면 **훑기를 부르지 않는다**(§3.14.1 표도 '필터를 껐으면 훑기 0' 으로 센다).
- 이대로 가면. 그 네 경우에 훑기의 `k` 가 없으므로 카드 밖 호출의 `cards` 는 비고(배경 카드는 제목만), `noinput` 호출의 `cards` 도 빈다. 배경 카드는 6,184 / 10,774 장(57%)이고(§3.14.1), 입력 결손 전문가는 110명(30.6%)이다. 가장 보수적이라고 고른 길('전수 대조')에서 오히려 카드의 절반 이상이 읽히지 않는다. `sweep_json.cards_unseen` 도 훑기가 없으면 셀 수 없어 품질 칸에 드러나지 않는다.
- 드문 길이 아니다. snap 타깃은 **늘** 이 길이다(현황 감사 타깃 전부). 단위 5개 이하인 작은 diff 도 늘 그렇다. 그리고 §3.9.4 는 Tier A 셀에서 '훑기 no · 신호 miss 인데 대조에서 `applies='yes'` 가 하나라도 나온' 것을 놓침으로 세고 5% 를 넘으면 나머지 344명의 훑기를 끈다. 범용 규칙 카드에 `applies=yes · OK` 가 한 장만 나와도 놓침이므로 5% 는 쉽게 넘는다(추정). §5.2 의 '끝까지' 시험은 단위 4개이고 '패널 규칙' 시험은 셀 30개(전문가 6 × 단위 5)라 둘 다 `few_units` 길이다 — 훑기가 도는 길과 건너뛰는 길이 시험에서 갈려 있지 않고, dev 픽스처 과제가 단위 5개 이하면 실주행 A 도 구멍이 있는 길만 돈다.
- 고치는 법. 걸음 8 에서 '건너뛴다' 를 '분류에 쓰지 않는다' 로 바꾼다 — 훑기는 카드가 있는 전문가에게 **늘** 부르고(전문가당 1~2회라 전체 호출의 5% 안쪽이다), `route_forced` 가 서 있으면 그 답을 셀 분류에만 쓰지 않는다(Tier A 와 같은 처리). 훑기를 정말 못 부른 전문가(실패)는 카드 밖 · `noinput` 호출에 배경 카드를 서버 계획의 `sweep_decks` 순서로 돌려 가며 전문으로 싣는 폴백을 `build_request` 에 적는다. §5.2 에 '`few_units` · `filter_off` 에서도 모든 카드가 어느 호출의 `cards` 에 한 번은 전문으로 실렸다' 는 단언을 넣는다(가짜 엔진이 받은 별칭을 모아 팩과 견준다).

## P-04 [major] 단위(`scope.units`)로 범위를 좁힌 잡은 전문가 마감이 영영 돌지 않는다 — 설계서가 정한 파일럿 A·B 가 보고서도 finding 도 내지 못한다

- 근거(설계서). §3.7.1 — '범위 밖 셀은 pending 으로 남는다'. §3.4.1 · §3.3.2 · §3.7.4 — 마감(`finalize_expert`)은 '그 전문가의 열린 셀(`pending` · `running`)이 0 이 되는 순간' 에만 돈다. §3.10 — finding 을 올리는 때는 전문가 마감이다. §3.11.1 의 `scope` 절은 반대로 '범위 밖이라 남은 pending' 을 보고서에 싣는다고 적는다(마감이 pending 을 안고 돈다는 전제다).
- 이대로 가면. §5.4 의 A(Tier A 3명 × 단위 2개)와 B(Tier A 15명 × 단위 2개)는 전문가마다 범위 밖 pending 셀이 남아 마감 조건이 거짓이다. 워커는 전문가를 `planned` 로 놓고, 집을 전문가가 없으니 잡은 `completed` 가 된다. 전문가 보고서 0편 · finding 0건 · 의견 0행 · 등록부 변화 없음이다. D 의 통과 기준('보고서를 사람이 3편 읽는다')으로 가기 전에 B 에서 볼 것이 없다.
- 고치는 법. 걸음 6 · 8 에서 마감 조건을 '**이 잡의 범위 안** 열린 셀이 0' 으로 바꾼다. 범위 밖 pending 이 남은 전문가는 `partial`(사유 `scope`)로 마감해 보고서 · finding · 의견을 쓰되 `rr_coverage` 는 닫지 않는다(pending 유지 — 전 단위를 보지 않았다). §3.3.2 의 `partial` 뜻에 '범위 밖 미검토 셀' 을 더하고, `test_review_runner.py` 에 '`scope.units` 잡이 끝나면 보고서가 있고 원장은 pending 이다' 를 넣는다.

## P-05 [major] 카드 근거 finding 의 `warrant` 문구가 수치 대조를 늘 깨뜨린다 — 인용 전부가 `quote_mismatch` 가 된다

- 근거(코드). `narrative._number_tokens` 는 «…» 와 `card:…` 같은 참조 표기는 가리지만 맨 글자는 가리지 않는다. 설계서 §3.10.2 의 `warrant` 는 "근거 카드 <card_id> «<cq>»" 다. 직접 돌려 봤다 — `_number_tokens("근거 카드 MIS-R-001 «0.8 mm …»")` 는 `['001']` 을 낸다(`_NUMBER_TOKEN_RE`, narrative.py:147. 앞 글자가 `-` 라 뒤보기 조건을 지난다). `record_id` 를 쓰면 `['2026', '0000000144']` 다.
- `resolve_cites`(narrative.py:728~735)는 claim · warrant 의 수치 토큰이 하나라도 말뭉치에 없으면 **통과한 인용 전부**를 `quote_mismatch` 로 만든다. 설계서의 `number_corpus` 는 '인용한 카드들의 글 + 인용한 줄의 글' 이고 카드 머리(card_id)는 인용 대상이 아니라고 §3.5.2 가 못 박았다. 그러니 `001` 은 말뭉치에 없다.
- 이대로 가면. 카드 근거 finding 마다 `quote_mismatch` 에 인용 전부가 들어간다. WP4 의 `support_verified`(검증을 통과한 인용이 달린 원자의 전문가 수 — spec-wp4 §3.5.1)가 카드 근거 finding 에서 늘 0 이 되고 주의 등급(`attention_of` 의 `strong`)이 내려간다. §5.1 의 시험('15 가 0.15 에 걸리지 않는다')은 이 경우를 넣지 않아 초록이다.
- 고치는 법. 걸음 9 의 변환표에서 `warrant` 를 "근거 카드 [card:<record_id>] «<cq>»" 로 쓴다(참조 표기는 `mask_neutral` 이 가린다). `test_review_findings.py` 에 '실제 card_id 모양(MIS-R-001)과 record_id 모양으로 만든 카드 근거 finding 의 `unquoted_numbers` 가 비어 있다' 를 넣는다. `why` 에 든 '조건 2 개' 같은 셈 숫자도 같은 규칙에 걸리므로, 수치 하나가 없을 때 인용 전부를 불일치로 만드는 지금 식을 card 스코프에서는 '그 수치만 표기' 로 바꾸는지 WP1 과 한 줄로 정한다.

## P-06 [major] 얼린 카드 전문이 `finding_json` 에 통째로 복사된다 — 반출에 카드 원문이 실리고 병합이 느려진다

- 근거(코드). `_normalize_finding` 은 `finding["_resolved_cites"] = resolved["cites"]` 를 남기고(narrative.py:1050), 그 행에는 `payload`(해석된 대상)와 `canonical`(정규 글)이 들어 있다(681~722). `persist_panel_result` 는 그 dict 를 `json.dumps(atom)` 으로 `rr_findings.finding_json` 에 그대로 쓴다(1736). 지우는 코드는 없다(grep `_resolved_cites` — 쓰는 곳 넷, 지우는 곳 0).
- 근거(설계서). §3.8.6 — card 분기는 `payload=<그 카드>`(절 전부가 든 얼린 카드), `canonical_text_for` 는 `cardpack.card_text(카드)` 를 돌려준다.
- 이대로 가면. 카드 인용 하나마다 카드 본문이 두 번(payload · canonical) finding 에 박힌다(카드 평균 1,902자, 한 finding 에 인용 12건까지). (1) 설계서가 '카드 묶음은 반출에서 뺀다 · 폐기 때도 지우지 않는 사내 지식 사본' 이라고 한 원문이 `rr_findings` 를 타고 **반출 JSONL 에 실린다**. (2) `registry.merge` 는 부를 때마다 타깃의 finding 전부의 `finding_json` 을 읽어 푼다(registry.py:160~173 `_load_findings` — 읽기와 풀기는 `tx()` 밖이지만 부른 스레드, 곧 검토 루프를 그동안 붙든다). §3.14.2 는 finding 증가분을 1~2 MB 로 셌지만 카드 밖 `f` 줄(셀당 최대 6)까지 더하면 수천 건 × 5~30 KB 다(추정 — 타깃당 수십 MB). 300초마다 그만큼을 다시 읽는다. 직접 돌려 확인했다 — 지금 코드로 `_normalize_finding` 을 태운 dict 에 `_resolved_cites[].payload · canonical` 이 남는다.
- 고치는 법. 걸음 5 에서 card 분기의 `payload` 를 `{record_id, card_id, type, confidence, grade}` 로 줄이고, 걸음 9 의 `build_findings` 가 저장 전에 `_resolved_cites` 의 card 행에서 `canonical` 을 떼어 낸다(대조 결과 `ok · quote_mismatch · card_grade` 만 남긴다). `test_review_findings.py` 에 '`finding_json` 에 카드 절 본문이 없다(픽스처 카드의 긴 문장으로 부분 문자열 검사)' 와 '반출 JSONL 에도 없다' 를 넣는다.

## P-07 [major] 근거 꾸러미 줄(`tool:…`)을 인용한 finding 이 전부 dangling 이 된다

- 근거(코드). `_resolve_one` 의 `tool` 분기는 `ctx.call_ids` 에 그 id 가 없으면 `ok=False` 다(narrative.py:636~638). `ok=False` 는 `resolve_cites` 에서 dangling 으로 센다(699~705). `call_ids` 를 채우는 코드는 지금 어디에도 없다(grep — 선언 한 줄과 읽는 두 줄뿐). `_panel_scope` 도 넣지 않는다.
- 근거(설계서). §3.8.3 은 판정 행의 참조가 '변경 줄 + 근거 꾸러미 줄' 이면 `refs_ok=1` 로 본다. §3.10.2 는 그 참조를 `cites` 에 `{ref, quote:''}` 로 넣어 `_normalize_finding` 에 태운다. `review_scope` 는 '`_panel_scope` 와 같은 스코프에 card_pack 을 얹는다' 고만 적는다. WP2 는 이 일을 받는 쪽 몫으로 적었다(spec-wp2-units.md:627 — 'B 층의 `tool:b-…` 를 인용으로 인정하려면 셀 · 패널의 `SpecContext.call_ids` 에 `evidence_json.calls[].call_id` 를 더해야 한다(WP3 · WP4 에 계약)').
- 이대로 가면. 코드가 도구로 조회해 실어 준 근거(재료 비교 등)를 짚은 지적일수록 `rr_findings.dangling=1` 이 되고 `rr_claim_refs.dangling=1` 로 남는다. 셀에서는 `refs_ok=1` 인데 등록부에서는 '지어낸 참조' 다.
- 고치는 법. 걸음 5 의 `review_scope` 가 `call_ids` 에 (그 스냅샷들의 `rr_snapshot_calls.call_id`) ∪ (그 finding 의 단위들의 `evidence_call_ids`)를 넣는다. `_panel_scope` 도 같은 값을 넣게 WP4 와 한 함수로 둔다. `test_review_verify.py` 에 '꾸러미 줄 `tool:b-…` 를 인용한 finding 의 dangling 이 0' 을 넣는다.

## P-08 [major] 카드 묶음을 받는 순간의 '0장' · '없는 전문가' 가 타깃 끝까지 굳는다 — 그리고 `blocked` 전문가의 재시도가 `pack` 단계에만 있다

- 근거(설계서). §3.5.2 — 200 · `cards=[]` 는 `empty` 로 얼리고 진행, 404 `agent_not_found` 는 '다시 받아도 같으므로 **백오프하지 않고**' `blocked`. §3.5.4 — 한 번 받은 묶음은 '그 타깃이 끝날 때까지', 잡을 며칠 뒤 다시 돌려도 다시 받지 않는다. §3.7.3 걸음 3 — 묶음 받기는 `phase='pack'` 일 때만 돌고, 남은 것이 백오프 중인 `error` 뿐이면 `phase='review'` 로 넘어간다. 같은 절 — 집을 전문가가 없으면 잡은 `completed` 다.
- 근거(운영). cae00 의 update-all §3 은 새 덤프가 오면 AIDataHub 를 DROP 뒤 복원한다(spec-wp5a-ops.md:111 · 553). 팩은 `list_records` 의 `total` 과 `get_agent_session` 으로 만든다(spec-wp3a §3.4). 복원 창에 닿은 요청은 '전문가 없음'(404) 이거나 `total=0`(빈 팩) 으로 돌아올 수 있다(추정 — 복원 도중의 응답 모양은 확인하지 못했다).
- 이대로 가면. (1) 복원 창에 받은 전문가가 `empty` 로 얼어 카드 30장짜리 전문가가 '카드 결손 전문가' 로 며칠을 돌고 `done_weak(no_cards)` 로 닫힌다. 실패가 정상 응답과 같은 모양이다. (2) 그 창의 404 는 재시도 없이 영구 `blocked` 다. (3) `review` 단계로 넘어간 뒤에는 백오프가 지난 `error` 전문가도 다시 받는 걸음이 없어 그 전문가의 셀은 pending 인 채 잡이 `completed` 가 된다.
- 고치는 법. 걸음 8 에서 (가) 묶음 재시도를 단계와 무관하게 매 틱 돈다. `blocked` 전문가가 남아 있고 다시 받을 예정이면 잡을 `completed` 로 닫지 않는다. (나) `agent_not_found` 도 다른 오류처럼 백오프해 3회까지 다시 받고 그 뒤에 사람에게 보인다. (다) `cards=[]` 는 곧바로 `empty` 로 얼리지 않는다 — 그 전문가의 세션을 집기 직전에 한 번 더 받아 두 번 다 0장일 때만 `empty` 다. (라) `pack` 단계 끝에 `empty` 가 max(5, 로스터의 3%) 를 넘으면 보류(`pack_suspect`)로 멈춘다(지금 실측은 359명 중 3명이다 — 03-cards.md). (마) `test_review_runner.py` 에 '첫 응답 0장 · 둘째 응답 30장이면 `ok` 로 언다' 와 '`review` 단계에서 `error` 전문가가 다시 받아진다' 를 넣는다.

## P-09 [major] 검토 잡끼리 차례가 없다 — 먼저 만든 잡이 며칠 동안 자리 넷을 다 쓴다

- 근거(설계서). §3.7.3 — 잡을 `created_at` 순으로 보고 `_review_sem` 이 빌 때마다 그 순서로 전문가를 집는다. 세마포어는 타깃을 가로질러 하나, 타깃당 직렬도 일일 상한도 없다. §3.7.11 — '빈 자리를 채우는 순서는 잡의 created_at'. §3.14.1 — 전원 잡 하나가 4~14일이다.
- 이대로 가면. 전원 잡이 도는 동안 다른 과제의 Tier A 범위 잡(반나절짜리)은 앞 잡이 끝날 때까지 한 호출도 받지 못한다. WP4 의 후속 잡(`post` · `synth`)도 같은 세마포어를 쓰므로 다른 타깃의 전원 잡 뒤에 선다. '며칠이 걸려도 운영을 막지 않는다' 는 목표가 리스크 심사 자신에게는 성립하지 않는다.
- 고치는 법. 걸음 8 의 선점 순서를 '잡 → 전문가' 가 아니라 '**살아 있는 잡을 돌아가며 한 명씩**' 으로 한다(잡마다 최소 1자리). 덧붙여 전문가 순서의 첫 키를 tier 로 두어 어느 잡이든 Tier A 가 다른 잡의 Tier C 보다 먼저 집히게 한다. `test_review_runner.py` 에 '잡 둘을 심고 가짜 엔진이 받은 호출의 타깃이 번갈아 나온다' 를 넣는다. 동시에 도는 잡 수를 1 로 묶는 쪽(WP5a `HWAXRISK_REVIEW_RUNS_PARALLEL`)을 택하면 그 사실과 대기 순번을 잡 응답에 싣는다.

## P-10 [major] 사람의 정지가 자동 재개에 진다 — 보류 열을 지우는 자리가 없다

- 근거(코드). `runner._set_job`(runner.py:653~668)은 `state · pause_reason · error · state_by · state_at` 만 적는다. `pause_job` 은 `queued · running` 에서만 되고(670~678), `resume_job` 은 `paused → queued` 로만 옮긴다(681~687). 설계서 §3.12.1 은 '`POST /jobs/{job_id}/{action}` 은 그대로다' 라고 적는다.
- 근거(설계서). §3.7.3 걸음 1 — `state='paused' AND mode='reviews' AND hold_code IN ('breaker','pack_unavailable') AND hold_until ≤ now` 이면 `queued` 로 돌린다. §3.7.6 — 반쯤 연 동안과 재기동 뒤에도 차단기 기억을 `hold_code · hold_n · hold_until` 에 둔다.
- 이대로 가면. (1) 차단기가 한 번 걸렸다 풀린 잡(`hold_code='breaker'`, `hold_until` 과거)을 사람이 정지하면 `pause_reason='user'` 만 적히고 `hold_*` 는 그대로라, 2초 뒤 틱이 그 잡을 `queued` 로 되돌린다. (2) 차단기로 멈춰 있는 잡(`paused`)은 `pause_job` 이 409 라 사람이 '계속 멈춰 둬' 라고 할 길이 취소뿐이다. LLM 점검 때 멈춰 두려던 잡이 백오프마다 스스로 깨어난다. (3) 사람이 `content_fail_rate` 보류를 `resume` 하면 `hold_code` 가 남아 진행판이 계속 보류로 읽힌다.
- 고치는 법. 걸음 3(또는 8)에서 `_set_job` 이 `mode='reviews'` 잡의 전이마다 `hold_code · hold_until · hold_n` 을 함께 다룬다 — 사람의 pause 는 `hold_code='user'` · `hold_until=NULL` 로 덮고, resume · cancel 은 셋을 비운다. `pause_job` 은 코드가 멈춘 `paused` 에도 듣게 한다(사람의 정지로 바꿔 적는다). 자동 재개 조회에 `pause_reason IS NULL` 을 더한다. 시험 — '차단기 보류 중 pause → 시계를 밀어도 queued 로 안 돌아온다'.

## P-11 [major] 스키마 확정이 가장 먼저 나가야 하는데(v4 한 블록) 이 설계서의 DDL 은 아직 계약과 다르고 P-01 을 기다린다

- 근거. 계약 C-2 — v4 는 새 흐름의 표 · 열 전부를 **한 블록**으로 새 흐름 첫 커밋에 싣고, push 된 버전의 DDL 은 고치지 않는다. C-1 — WP2 가 WP3b 보다 먼저 나간다. 코드 — `migrate()` 는 `version <= current` 인 버전을 건너뛴다(risk_store.py:628~629). v4 로 올라간 DB 에는 나중에 v4 블록에 더한 표가 생기지 않는다.
- 설계서 §3.2 의 DDL 은 C-21 의 열 이름(`tries · charged · infra_streak · not_before · lease_owner · heartbeat_at · run_id · tokens_in …`)이 아니라 제 이름(`attempts · infra_retries · retry_at · claim_id · job_id · prompt_tokens …`)이고, 상태도 C-18 의 `skipped` 가 없다. 어느 뼈대로 가느냐(P-01)에 따라 필요한 열이 달라진다(`lease_owner` 에 무엇을 넣나, 전문가 머리의 선점 열).
- 이대로 가면. 걸음 1 을 WP3b 차례에 따로 커밋하면 이미 v4 인 dev · cae00 DB 에 표 다섯이 없다(`no such table: rr_review_cells`). 반대로 v4 를 WP2 와 함께 먼저 내보내면 이 설계서의 DDL 이 고쳐지지 않은 채 굳는다.
- 고치는 법. 계획서의 순서를 'P-01 결정 → §3.2 DDL 을 C-18 · C-21 로 다시 써서 확정 → v4 블록 커밋(걸음 1 의 `export.py · routes.py · tests/test_store.py` 변경을 그 커밋에 같이 싣는다) → WP2 → …' 로 적는다. WP3b 가 구현 중에 더 필요한 열은 v5 의 `ADD COLUMN` 으로만 낸다. 걸음 1 의 검증에 '표 다섯이 없는 v4 DB 를 일부러 만들어 올렸을 때 기동이 무엇을 말하는가' 를 넣는다(말없이 뜨고 첫 잡에서 죽는 것을 막는다).

## P-12 [major] 다시 마감할 때의 `INSERT OR REPLACE` 가 finding 에 사람 · 라벨이 적은 것을 지운다

- 근거(코드). `rr_findings` 에는 마감 뒤에 고쳐지는 열이 있다 — 라벨 훅이 `status · status_source · status_decided_by · status_decided_at · status_reason` 을 적고(metrics.py:381~386), 큐레이션 승인이 `recall_eligible = 1` 로 되돌린다(routes.py:3518~3521). `ra_entity_id · adh_record_id · created_at` 도 행에 산다.
- 근거(설계서). §3.10.2 — 마감 트랜잭션은 새 집합에 없는 finding 을 지우고 나머지를 `INSERT OR REPLACE` 한다. 마감은 셀이 다시 열렸다 닫힐 때마다 다시 돈다(§3.4.1) — 실패 셀 다시 열기, WP4 의 표본 재검토, 단위 재빌드 뒤.
- 이대로 가면. 사람이 승인해 회수로 되돌린 finding(`extras.inj` 로 `recall_eligible=0` 이던 것)이 다음 마감에서 다시 0 이 된다. 라벨로 `verified · dismissed` 가 된 finding 이 `open` 으로 돌아가고 `created_at` 이 새로 찍힌다(반출의 `since` 창이 흔들린다).
- 고치는 법. 걸음 9 에서 `INSERT … ON CONFLICT(finding_id) DO UPDATE SET <코드가 정하는 열만>` 으로 쓴다. `status*` · `recall_eligible`(사람 승인 뒤) · `ra_entity_id` · `adh_record_id` · `created_at` 은 건드리지 않는다. WP4 의 `persist_single_findings` 를 쓰더라도 같은 규칙을 그 함수에 적는다. 시험 — '라벨로 verified 가 된 finding 이 다시 마감한 뒤에도 verified 다'.

## P-13 [major] 다시 마감하며 지운 finding 의 등록부 행이 남는다 — 병합은 행을 지우지 않는다

- 근거(코드). `registry.merge` 는 지금 있는 finding 으로 만든 클러스터 행만 쓰고(registry.py:540~555), 구성원이 사라진 `rr_registry` 행을 지우는 코드가 없다(`DELETE FROM rr_registry` 는 리포 어디에도 없다). `verdict_candidate` 는 그 타깃의 `open · verified` 행 전부를 읽는다(639~664).
- 근거(설계서). §3.10.2 — 마감은 새 집합에 없는 finding 을 지운다. 지워지는 때가 흔하다 — `reviewed` 셀을 `force` 로 다시 열었을 때(§3.3.1), 단위 재빌드 뒤 사라진 단위의 finding(§3.7.2), `reset_review`(§3.7.2), 단독 재질의에 메커니즘 칸이 생겨 `cluster_key` 가 바뀔 때(§6 위험 24 의 해소 시점). 패널 흐름에서는 같은 패널을 다시 제출할 때만 지워져 드물었다.
- 이대로 가면. 사라진 지적의 클러스터가 등록부에 옛 지지 수 · 옛 판정으로 남아 `verdict_candidate`(conditional · no-go)와 WP4 의 쟁점 선정 · 종합 보고서에 들어간다. `reset_review` 뒤에는 등록부 전체가 유령이다. `stats_json.dropped_findings`(위험 14)는 전문가 쪽 기록일 뿐 등록부를 고치지 않는다.
- 고치는 법. 걸음 9 에 한 줄 — 마감이 finding 을 지웠으면 병합 뒤에 '이 타깃의 등록부 행 가운데 이번 병합이 쓰지 않은 행' 을 정리한다. `status_source='code'` 행은 지우고, 사람 · 라벨이 정한 행은 `support=0` 과 `stale_json` 표기로 남긴다(사람의 결정을 지우지 않는다). 병합의 주인이 WP4 이므로 `registry.merge(…, prune=True)` 로 그쪽 걸음에 넣고 WP3b 의 마감 · `reset_review` 가 그 인자로 부른다. 시험 — '`force` 로 다시 연 셀의 finding 이 사라진 뒤 그 클러스터 행이 없고 `verdict_candidate` 가 바뀐다'.

## 작은 어긋남(minor)

- m-01 실패 셀이 남은 전문가의 원장 롤업이 `done` 이다(§3.4.1 표 넷째 줄 — `reviewed ≥ 1` 이면 실패 셀이 몇 개든 `done` + `reason='partial:<n>'`). 8칸 중 7칸이 실패여도 지금 `coverage_summary` 의 strong 비율과 영역별 done 수에 온전한 검토로 들어간다. 걸음 6 에서 열린 실패 셀이 있으면 `done_weak`(reason `partial:<n>`)로 적는다.
- m-02 단독 재질의 수에 상한이 없다(§3.9.2 — FAIL · WARNING 전부를 1장씩). §3.14.1 은 양성률 3% 를 가정했는데 30% 면 단위 8개 전수에서 약 7,600회가 더 붙어 일정이 1.8배가 된다(추정). 잡 응답의 `calls_estimate` 를 넘기면 멈춰 묻는 보류(WP5a 의 `budget`)를 걸음 8 에 넣는다.
- m-03 `/limits` 가 `ctx_assumed: true` 인 동안 틱이 말없이 끝난다(§3.5.3 · §3.7.3). 기한도 보류도 진행판 문구도 없다. 2초마다 포털을 두드리며 무한히 `pack` 단계다. 10분 넘으면 진행판 `waiting` 에 사유를 적고 60초 간격으로 늦춘다.
- m-04 묶음 받기와 `unit_pack.ensure` 를 루프 스레드가 직접 한다(§3.5.4 — 틱당 8명, 한 건 최악 420초 · 읽기 한도 660초). 그 동안 다른 잡의 워커 배치 · 자동 재개 · `cancelling → cancelled` 가 멈춘다. '정지에 곧 반응한다' 는 HTTP 호출 한가운데서는 성립하지 않는다. 틱당 1명으로 줄이거나 워커 자리에서 받는다.
- m-05 내용 탓 재시도가 같은 요청을 그대로 다시 보낸다(§3.7.5). temperature 0 이라(app.py:342) `no_rows` · `cards_unjudged` 는 같은 답이 온다. 서버의 보충은 문구에 시도 번호를 넣어 이것을 피한다(spec-wp3a §3.6). 앱 재시도에는 카드 순서를 뒤집어 보낸다(`rev` 와 같은 수법).
- m-06 `claim_uid` 의 수 부분이 32비트다(§3.10.2 `sha1(...)[:8]`). 한 전문가 안에서 두 (cluster_key, unit_id) 가 겹치면 `INSERT OR REPLACE` 가 한 finding 을 말없이 덮는다. 12 hex 로 늘린다(스키마 패턴 `[FG][0-9]+` 은 그대로 맞는다).
- m-07 보고서의 `head` 에 판번호와 만든 시각이 들어 있다(§3.11.1). §3.11 의 '같은 원장이면 같은 바이트' 와 §3.11.2 의 '해시가 다를 때만 revision 을 올린다' 가 성립하지 않는다(시각이 해시를 늘 바꾼다). 두 값은 행의 열에만 두고 JSON 에서 뺀다.
- m-08 `reset_review`(§3.7.2)가 검토가 닫은 `rr_coverage` 행(`panel_id = review_id`)을 되돌리지 않고 등록부도 다시 병합하지 않는다. 지운 뒤 원장은 없는 의견을 가리키는 `done` 이고 등록부에는 지운 finding 의 행이 남는다.
- m-09 실패 셀 처분(`PUT …/cells/{unit_id}/{agent_key}`)에 묶음 형태가 없다(§3.12.1). 단위 하나가 `unit_oversize` 면 359칸, LLM 사고 한 번이면 수백 칸을 한 칸씩 처분해야 잡이 끝난다(C-18). 다시 열기처럼 `filter` 를 받게 한다.
- m-10 폐기(`PURGE_BLANK_SQL`, §3.2.1)가 `rr_review_cells.handoffs_json · error · decide_note` 를 비우지 않는다(모델 · 사람이 쓴 과제 글이다). 폐기는 잡을 `cancelled` 로만 바꾸므로(routes.py:1021~1025) 그 뒤 20초 안에 끝난 호출의 결과가 비운 타깃에 다시 적힌다 — 폐기가 그 타깃의 `claim_id` 를 지워 늦은 쓰기를 버리게 한다.
- m-11 이미 있는 시험과 스키마의 고정값이 걸음의 '바뀌는 파일' 에 빠져 있다. `tests/test_runner.py:12` 는 스레드 이름 셋을 못 박는다(걸음 8 에서 깨진다). `seat_opinion.v1` 은 `contested_finding_ids` · `character_sentences` 가 필수인데 §3.4.2 표에 없다. `routes.JobBody.tier` 는 필수 칸이라 `mode='reviews'` 본문이 422 다(걸음 11). `RiskRunner(store=None, settings=None)` 로 `start()` 하는 시험이 있어 잠금 코드는 설정 없음을 받아야 한다(걸음 2).
- m-12 잠금을 못 쥔 까닭을 가르지 않는다(§3.14.4). 남이 쥐고 있음(`BlockingIOError`)과 파일시스템이 잠금을 못 받음(그 밖의 `OSError`)을 같이 '못 쥠' 으로 보면, 후자의 박스에서는 러너가 영영 돌지 않아 지금 도는 패널 흐름까지 멈춘다. 후자는 크게 적고 잠금 없이 돈다.
- m-13 검토 호출의 줄 사이 침묵 한도로 패널 값(54,000초)을 그대로 쓴다(§3.6.1). ping 이 15초 간격이므로 죽은 연결 하나가 워커 자리를 15시간 붙든다. 검토 호출에는 따로 짧은 값(예 300초)을 둔다.
- m-14 옛 타깃에 검토를 얹을 때(§8 결정 6) 그 로스터에는 `input_gaps_json` 이 없다(WP2 이전에 얼었다). 회로 전문가가 입력 결손 길이 아니라 카드 대조 길로 간다. `create_review_job` 이 옛 로스터면 `undefer`(WP2)를 먼저 하라고 409 로 답한다.
- m-15 실주행 A 의 '호출 중 `apptainer instance stop` 뒤 다시 올린다'(§5.4)에 인스턴스 이름이 없다. 허브는 45초마다 죽은 앱을 스스로 다시 띄우므로(spec-wp5a-ops.md:117) 손으로도 올리면 둘이 뜬다. 절차에 '`instance list` 출력에서 리스크 앱 인스턴스 이름을 먼저 확인하고, 다시 올리는 것은 허브에 맡긴다' 를 적는다.
- m-16 WP4 병합 변경 전의 파일럿(§5.4 A~C)에서도 마감은 `registry.merge` 를 부른다. 그때 `support` 는 원자 수라 `_recompute_contrib` 가 과제 사이 선례 통계(`rr_delta_priors`)에 부푼 값을 넣는다(registry.py:403~418 · 554~555). 다음 병합에서 고쳐지지만 그 사이 다른 과제의 브리프가 읽는다. 파일럿 타깃은 `corpus_excluded=1` 로 두거나 WP4 전에는 새 흐름 타깃의 기여 계산을 건너뛴다.

## 빼거나 미룰 것(cuts)

- 제공자 접점(`WorkProvider` · `register_provider`, §3.7.11)과 가짜 제공자 시험. 쓰는 쪽(WP4)이 붙을 때 그 걸음에서 넣는다. 잃는 것은 없다(P-01 에서 `Executor` 와 하나로 합쳐야 하므로 지금 넣으면 두 번 짠다).
- `POST /targets/{key}/packs/refresh` 와 `reopen=true`(§3.5.4 · §3.12.1). 첫 실주행에는 P-08 의 '0장 재확인' 만 있으면 된다. 잃는 것 — 심사 도중 카드가 바뀐 전문가를 알아내는 길(대신 `reset_review` 뒤 다시 돈다).
- 음성 판정의 10% 무작위 재질의(4장 `rev` 묶음, §3.9.2 둘째 줄). Tier A 전량 이중 판정 · 인용 불일치 음성 전부 · FAIL/WARNING 단독은 남긴다. 잃는 것 — Tier A 밖 전문가의 거짓 '문제없음' 추정치. Tier A 범위 실행(D)의 일치율을 본 뒤 넣는다.
- Tier A 놓침률로 잡 도중 필터를 끄는 자동 전환(§3.9.4 `sweep_miss_max`). 놓침률은 재서 보이기만 한다. 잃는 것 — 훑기가 나쁠 때의 자동 전수 전환(WP4 의 표본 재검토가 같은 일을 층 단위로 한다). 판정 기준('applies=yes 한 장이면 놓침')을 실측 전에 굳히지 않게 된다.
- `HWAXRISK_REVIEW_FINDING_POLICY=direct` 갈래(§3.10.3). `hold` 하나만 둔다. 잃는 것 — 검토의 FAIL 을 등록부에 곧바로 올리는 길(결정 1 의 권고가 `hold` 다).
- MCP 도구 `risk_get_cells` · `risk_get_expert_report`(§3.12.2). 계약 C-30 의 도구 넷에 없다. REST 만 둔다. 잃는 것 — MCP 로 셀 원장을 읽는 길(WP4 의 `risk_get_report` 가 보고서를 준다).
- `over_budget` · `context_overflow` 의 묶음 반 나누기(§3.7.5). 계획을 서버가 짜고 넘치면 422 로 미리 거절하므로 한도를 다시 읽어 계획을 다시 받는 것으로 충분하다. `truncated_empty` 의 반 나누기는 남긴다(출력 상한은 계획이 못 본다). 잃는 것 — 서버의 예산 식이 틀렸을 때의 자동 우회.
- 승계용 인덱스 `ix_rr_cells_reuse`(§3.2). 승계를 구현하는 판에서 `CREATE INDEX IF NOT EXISTS` 로 더한다. 잃는 것은 없다.

## 직접 확인해 맞았던 주장

- 저장소는 프로세스에 연결 하나 · `RLock` · WAL · `busy_timeout` 미설정이고 `tx()` 가 블록 끝까지 락을 쥔다(risk_store.py:580 · 597~600 · 674~699).
- `rr_seat_opinions` 는 `panel_id NOT NULL` · `UNIQUE(target_key, agent_key, cycle)` 이고 cycle 을 원장과 맞춰 읽는 코드는 없다(쓰는 곳은 `persist_panel_result` · `revert_carried` · `make_external_id` 뿐).
- `claim_next_job` · `recover_running_panels` 는 잡 종류를 가르지 않고, 타깃당 직렬 · 일일 상한은 `rr_panels` 만 센다(runner.py:714~760 · 764~794).
- `PortalPanelEngine.run` 은 실행마다 대화를 만들고 `/agent/chat` 의 `message` 상한은 65,536자다(engine_client.py:358, 포털 routes.py:182).
- `_resolve_one` 의 card 갈래는 `external_check` 가 없으면 확인 없이 통과하고, `evidence_grade_from_cites` 는 card 인용 하나로 '문헌·규격' 을 준다(narrative.py:644~646 · 768). `canonical_text_for` 에 card 분기가 없다.
- 등록부 지지 수는 서로 다른 `panel_id` 수이고 패널이 없으면 원자 수다(registry.py:205~206).
- `planner` 의 종결 상태는 나가는 전이가 없고 `apply_seat_results` 는 `assigned|running` 행만 고친다. running 좌석이 있는데 running 패널이 없으면 불변식 (2) 위반이다(planner.py:47~58 · 651~653 · 846).
- `seat_opinion.v1` 은 닫힌 스키마이고 `panel_id` hex32 · `cycle ≥ 1` · finding id 패턴이 설계서가 적은 대로다.
- `attribute_events` 는 지정 반대석을 늘 좌석 표에 넣는다(runner.py:153~157) — §2.9 (1) 의 결함이 설 조건이 코드에 있다.
- 리스크 앱은 uvicorn 한 프로세스로 뜨고 매니페스트는 cpu 1 · memory 2 GB 다.

## 확인하지 못한 것

- AIDataHub 복원 도중에 온 `list_records` · `get_agent_session` 이 실제로 어떤 모양으로 답하는지(P-08 의 전제).
- cae00 의 LLM(GLM) 엔드포인트 `/models` 가 창 크기를 주는지. 안 주면 에이전트 서버는 기본값을 굳히는데(app.py `_model_context_tokens`) 그때 `ctx_assumed` 가 참으로 남는지는 WP3a 구현에 달렸다(m-03).
- 데이터 디렉터리의 파일시스템이 `flock` 을 받는지(m-12). SQLite WAL 이 도는 것으로 보아 받을 것으로 추정한다.
- 모델이 범용 규칙 카드에 `applies=yes` 를 얼마나 내는지. Tier A 놓침 판정과 양성률(m-02)이 여기에 달렸다.
- 카드 밖 `f` 줄의 실제 건수 분포. `rr_findings` 크기와 병합 시간(P-06)의 추정이 여기에 달렸다.
- 사용자 PAT 의 통상 수명. 며칠짜리 잡이 서비스 계정으로 넘어가는 빈도와, 서비스 PAT 주체가 `feat:deliberation` · `plat:aidatahub` 를 갖는지.
- 포털 중계 `/agent/card-review/run` 이 챗 세마포어(64)를 같이 쓰는지, 침묵 한도 프레임(`agent_stream_idle`)을 지금 코드 그대로 내는지(WP3a 미구현).
- 허브가 탐침을 놓쳐 앱을 하나 더 띄울 때 둘째 프로세스의 기동 복구가 포트 바인드보다 먼저 도는지(uvicorn 의 lifespan 순서 — 열어 보지 않았다).

## 판정

원장 쪽(셀 · 변형별 판정 행 · 얼린 팩 · cycle 대역 · 내용에서 나오는 finding id)은 코드 사실 위에 서 있고 직접 연 주장은 거의 다 맞았다.
그러나 이대로는 구현을 시작할 수 없다 — 같은 `review_runner.py` 를 WP5a 가 다른 뼈대로 만들고(P-01), 계약 C-24 의 '자리 없음 즉답' 을 이 설계서의 실패 표가 인프라 실패로 세어 챗 · 심의와 같이 도는 평소에 셀을 `failed` 로 굳힌다(P-02).
목표에 바로 닿는 구멍도 있다 — 훑기를 건너뛰는 길(snap 타깃 · 작은 diff · 필터 꺼짐)에서는 배경 카드 57% 와 입력 결손 전문가의 카드가 한 번도 전문으로 실리지 않는다(P-03).
finding 승격에는 지금 코드로 돌려 보면 바로 드러나는 결함이 셋(P-05 · P-06 · P-07) 있고, 단위 범위 잡은 마감이 돌지 않아 설계서가 정한 파일럿이 보고서를 내지 못한다(P-04).
blocker 셋을 계획서에서 먼저 정하고 major 열 건을 걸음에 넣으면 선다.
