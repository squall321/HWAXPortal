# M3 실행 계획 — 리스크 앱 셀 확장(전원 포함 · 입력 결손 · 실패 셀 처분 · 거르기 · 호출 줄이기)

> 2026-10-14 작성. 닻은 HWAXRisk `3aea93b`(스키마 v4 동결 · MCP 도구 29종) · HWAXAgentServer `412edde` 에서 함수 이름과 문자열로 다시 찾았다. 설계서의 줄 번호는 믿지 않았다.
> 우선순위 — [PLAN.md](../PLAN.md) > [M2.md](../M2.md)(M2 계약 정본, 이 문서가 그 위에 선다) > **이 문서** > [problems.md](../problems.md) > [04-contract.md](04-contract.md) > `spec-*.md`.
> 형제 계획 둘과 나눠 짠다 — `m3-synthesis.md`(택소노미 1.2 · 메커니즘 → 영역 표 · 등록부 · 쟁점 · 완결 판정 · **v5 블록의 주인**)와 `m3-engine-ops.md`(에이전트 서버 · 포털 · 게이트웨이). 그쪽에 기대는 자리는 7절에 모았다.
> 읽기만 해서 썼다. 코드·시험을 돌리지 않았고 리포에 아무것도 쓰지 않았다.
> 걸음 이름 `C3-n` 은 이 꾸러미(cells)의 걸음 번호다. 완결 레벨 `C3` 와 무관하다.

## 1. 범위

### 1.1 하는 것

| 걸음 | 무엇 | 근거 |
|---|---|---|
| C3-0 | 시작 걸음 — 문제를 수용 기준으로 옮기고 닻을 다시 찾는다 | PLAN 9절 |
| C3-1 | v5 블록의 이 꾸러미 몫(`rr_unit_live` 한 표) | PLAN 4절 C-2 |
| C3-2 | 전원 포함 — `input_gap_m3` 거절을 없애고 보류(`deferred`)를 푼다 | PLAN M3 `WP2 9`, D-16·D-17 |
| C3-3 | 입력 결손 호출(`noinput`)의 앱 쪽 배선 — 요청·받은 행·셀 정산·finding·보고서 | PLAN M3 '입력 결손 호출', WP2 3.10.2 |
| C3-4 | 실패 셀 처분 REST(`retry`·`skip`)와 감사, Claude 입구, 롤업 표의 빈 줄 | PLAN M3 '실패 셀 처분 REST', `WP5a R7`(다시·넘김), X1-01·X1-23 |
| C3-5 | 거르기의 코드 신호 — 변경 → 메커니즘 → 영역 | D-33 ②, D-34 |
| C3-6 | 거르기 분류 — 훑기 뒤에 셀을 거르거나 검토로 보낸다 | D-33 ①② |
| C3-7 | 표본 재검토 · 대표 그림자 · 넓힘 · 보충 표본 | D-33 ③, X1-12·X1-13 |
| C3-8 | 보이기 — 셀 격자 · 진행판 · 전문가 보고서 · 품질 수치(`WP5b C10`) · 완결 몫 인터페이스 | D-33 ④, M3 나갈 기준 1·5 |
| C3-9 | 이중 판정은 걸린 카드에만, 대표는 보정용으로 전량 | D-33 첫 줄 |
| C3-10 | 호출 추정 · 동의 · 상한 다시 세기(`WP5a R7` 상한·동의), 동시 8 | D-33 · D-34 |
| C3-11 | 359명 규모 — 전문가별 단계 · 셈 비용 · MCP 와이어 25,000자 | M3 나갈 기준, R3B-1 |
| C3-12 | 근거 꾸러미 실호출(B 층) | PLAN M3 `WP2 7(실호출)`, 권고값 '캡처에 없던 도구만' |
| C3-13 | 보안 시험의 리스크 앱 몫(`WP5b C12`) | WP5b 3.10 |
| C3-14 | 대역 일치와 계약 예제(`WP5b C14`) | WP5b 3.5·3.6 |
| C3-15 | 문서 · 업데이트 이력 · 매니페스트 · HEAXHub 사본(`WP2 12` · `WP5b C16` · `WP5a H1`) | — |
| C3-16 | dev 리허설(359명 × 20단위, 가짜 LLM 1M 창) · v5 확정 · push · SIF · `tools/list` | PLAN 4절 C-2 |

### 1.2 하지 않는 것

| 무엇 | 까닭 |
|---|---|
| 등록부 병합 · 쟁점 선정 · 쟁점 패널 · 영역 요약 · 종합 보고서 · 완결 판정(`WP4 1·2·3·7·8·9·10·12·14`) | `m3-synthesis.md` 의 몫이다. 이 문서는 그쪽이 읽을 셀 셈(`closure_cells`)과 롤업 사유를 낸다 |
| 택소노미 1.2(14종)와 메커니즘 → 영역 배정표 | `m3-synthesis.md` 의 몫이다. 이 문서는 그 표에 기대는 인터페이스만 정한다(3.3) |
| 엔진의 `noinput` 종류 · 긴 문서 검색(`WP3a 8`) · 관문 기본값 · `/drain` · 챗 지연 측정 | `m3-engine-ops.md` 의 몫이다. 앱 쪽 배선만 여기에 둔다 |
| WP4 3.4 의 '해당 없음' 표본 재검토(`rr_cell_audits`·`plan_audit`·`required_n` 다단) | D-33 이 표본 재검토를 '거른 셀의 5% 를 끝까지 판정' 으로 정했다. C3-7 이 그것을 맡는다 — `rr_cell_audits` 표를 만들지 않는다(형제 계획에 알린다) |
| 2차 영향 · 결손 사냥 · 현황 타깃 단위 · RA 저장 · 지표 · 밤 창 | PLAN M4 |
| 단위 재빌드의 `force` 와 셀 비우기(`reset_review`) | M2 결정 #6 이 M3 로 미뤘지만 M3 범위 표에 없다. 새 대상에서 전원을 돌리면 재빌드가 필요 없다(열린 물음 a-14) |
| `rr_roster.input_gaps_json` 열 | 입력 결손은 `rr_roster.ecad_dependent`(v1)와 타깃 스냅샷의 `missing.ecad_absent`(불변)로 늘 같은 값이 계산된다. 옛 타깃도 같다(W2-16 의 '대표석에 결손이 안 적힌다' 가 계산으로 사라진다). 한 번 넣은 열은 지울 수 없다 |
| `mcad_absent` 입력 결손 | W2-16 — 질문·실마리가 없다. 단위 `missing` 표기로만 싣는다(지금 그대로) |
| 사전 점검(`WP5a R7` 의 preflight) | PLAN M3 의 R7 은 '상한·동의·다시·넘김' 넷이다. 막힘은 `risk_next_step` 이 이미 말한다 |
| 네트워크 신호(`recommend_agents`·`fts_search`)와 카드 어휘 신호 | W2-08·W2-09 — 거의 늘 '관련' 이라 거르지 못하고 호출만 는다. 코드 신호는 순수 계산이다 |
| 프런트(`frontend/`) | 다른 세션 몫이다. 응답 필드까지만 한다 |

## 2. 지금 코드 — 다시 찾은 닻(HWAXRisk `3aea93b`)

| 닻 | 지금 | M3 에서 |
|---|---|---|
| `review_runner.create_review_job` 의 `gaps = [r for r in picked["experts"] if r["input_gaps"]]` → 422 `input_gap_m3` | 입력 결손 전문가를 범위에 넣으면 거절 | 거절을 지운다(C3-2) |
| `review_runner.create_review_job` 의 `params["knobs"] = {"dual_rate": 1.0, "sweep": "on", "filter": "off", …}` | 이중 판정 전량 · 거르기 끔을 잡에 얼린다 | `dual`·`filter`·`audit_pct`·`routing_rev`·`live` 를 얼린다(C3-6·C3-9·C3-12) |
| `review_runner.CALLS_PER_CELL = (3, 14)` · `calls_estimate` | 359명 × 20단위면 높은 끝 7,180 × 14 + 359 × 2 = **101,238 회** → `HWAXRISK_REVIEW_MAX_CALLS`(30,000) 넘어 409 `review_too_large` | 전원 실행이 지금 코드로는 시작조차 안 된다. C3-10 이 식을 고친다 |
| `_Session.run()` — 훑기 → fwd(묶음 먼저) → 빠진 카드 재질의 → `review_verify.dual_plan`(rev) → `_solos` → `_offcard` → `_settle` | 훑기 답은 분류에 쓰지 않는다 | 훑기 뒤에 `_classify` 를 끼운다(C3-6). rev 는 걸린 카드만(C3-9) |
| `_Cell.dual_decks` · `_solo_set` 의 `decks.get(alias) in cell.dual_decks and "rev" not in have` | rev 를 물은 **묶음**을 기억한다 | 걸린 카드만 rev 하면 같은 묶음의 안 걸린 카드가 단독 재질의로 잘못 간다 — 별칭 집합 `dual_aliases` 로 바꾼다(C3-9) |
| `review_verify.dual_plan(fwd_request, dual_rate, sample_key, salt)` | 묶음 전체 rev, 같은 본문이면 solo | 걸린 별칭만 담는 `dual_plan_flagged` 를 더한다(C3-9) |
| `review_verify.sweep_accounting` → `sweep_json.units[unit_id] = {rel, k, why, missing_in}` · rel 순위 yes > maybe > error > stamp > no | 도장(`stamp`)의 no 는 stamp 로 적는다 | 훑기 신호의 원천(C3-6) |
| `review_runner.prompt_key(lim)` — 종류 판 **전부**를 이어 셀 `input_hash` 에 넣는다 | 엔진이 `noinput`·`summary` 를 더하거나 판 하나를 올리면 모든 `pending` 셀이 처음부터 돈다 | 그 셀이 부르는 종류만 잇는다(C3-3, `m3-engine-ops.md` 의 요청) |
| 엔진 `card_review._check_u` — `rel:no` 인데 `k` 가 있으면 `maybe` 로 올린다. `_settle` 의 `stamp` = 전부 no · 사유 둘 이하 | — | 그대로 쓴다(포함이 이긴다) |
| `review_cells.CELL_TRANSITIONS` | `na_irrelevant`·`no_input` 은 어휘만, `failed → skipped` 만 사람 길 | 전이 다섯을 더한다(3.1) |
| `planner.ALLOWED_TRANSITIONS["deferred"] = frozenset()` · `freeze_roster(ecad_absent=…)` 의 `rank != 1` 보류 | 보류는 영구 종결 | `deferred → pending` 을 연다(C3-2, WP2 3.10.5) |
| `planner.review_rollup` | `reviewed` 0 이면 '닫지 않는다(nothing_reviewed)' | 전부 거름 · 전부 입력 결손 · 전부 넘김인 전문가가 영영 안 닫힌다 — 줄을 더한다(3.9) |
| `planner.close_review_seat` — `flow='cells'` 만 닫고 `deferred` 행은 건드리지 않는다 | — | 보류를 안 풀면 `deferred`(종결 어휘)로 남아 거짓 완결이 된다 — C3-2 가 푼다 |
| `review_cells.review_summary` · `review_quality` 의 폭포 줄 `filtered`(= `na_irrelevant`) · `no_input` | 칸은 있고 값은 늘 0 | 실제 값이 들어온다(C3-8) |
| `review_runner.ReviewLoop._complete_or_phase` — 범위 안 누구라도 묶음이 `todo`·`error` 면 단계 `pack`, `_spawn` 은 그 단계 목적만 집는다 | 한 전문가의 묶음 재시도가 잡 전체를 붙든다(M2.md 8절, 최악 약 1시간) | 359명에서 막힌다 — 전문가별 단계로 바꾼다(C3-11) |
| `review_cells.expert_tally` — 타깃 셀 전부를 읽고 파이썬에서 전문가로 거른다 | 마감마다 7,180행 | SQL 에서 거른다(C3-11) |
| `entry._review_start_step` · `_cells_answer` 의 `runnable = [… if not r.get("input_gaps")]` · 문구 '입력 결손 전문가를 넣으면 422 input_gap_m3' | — | 문구와 셈을 고친다(C3-2) |
| `entry.job_action` · MCP `risk_job_action(job_id, action)`(pause·resume·cancel) | — | 처분 두 갈래를 더한다(C3-4, 새 도구 없음) |
| 엔진 `card_review.UNSUPPORTED_KINDS = ("noinput", "cross")` → 422 `unsupported_kind` | 앱의 별칭표에서 `unsupported_kind` 는 `contract` 보류(자동 재개 없음) | 앱이 `limits.kinds` 를 먼저 보고 `noinput` 이 없으면 `agent_outdated`(300초 자동 재개)로 멈춘다(C3-3) |
| 엔진 `review_gate.knobs` — `CARD_REVIEW_CONCURRENCY` 4, `_WITH_DELIB` 기본 `min(2, conc)` | — | D-34 의 '8, 심의 중 절반' 은 손잡이 두 개를 다 바꿔야 선다(엔진 몫, 7절) |
| 엔진 `card_review` — `v["k"] = max(1, min(k_knob, v["k_out"]))`(1M 창에서 `k_out` 19 — M0-b 커밋) | `CARD_REVIEW_K` 8 | K 를 키워도 출력 몫(19장)에서 멈춘다(10절) |
| `config.REVIEW_KNOBS` · `Knob(kind="int"|"bool")` | 선택지 손잡이가 없다 | `kind="choice"` 를 더한다(3.11) |
| `rr_audit.scope` CHECK — `project·snapshot·diff·target·registry·coverage·job·panel·finding·member` | — | 셀 처분은 `coverage`, 보류 해제도 `coverage`(WP5a P-17) |

## 3. 계약 제안

여기 적은 이름·값이 이 꾸러미의 정본 후보다. 형제 계획과 갈리면 M3 실행 계획(M2.md 와 같은 자리의 문서)이 정한다.

### 3.1 셀의 상태 · 경로 어휘

상태 어휘는 C-18 의 일곱 그대로다(`pending · running · reviewed · na_irrelevant · no_input · failed · skipped`). **거른 셀의 DB 상태는 `na_irrelevant` 다** — 이름을 바꾸지 않고(C-18 · WP3b · WP4 · 품질 폭포가 이 이름을 쓴다), 밖으로는 '거름(filtered)' 으로 보인다(열린 물음 a-1).

| 열 | 값 | 뜻 |
|---|---|---|
| `route` | `review` · `filtered` · `audit` · `noinput` | 이 셀이 간 길. `audit` = 거를 셀이었는데 표본으로 뽑혀 끝까지 판정 |
| `route_forced` | `rank1` · `global_unit` · `no_cards` · `input_gap` · `widened` · `filter_off` · `handoff` · `human_retry` · `tier_a_pending` · `filter_audit` · `filter_floor` · NULL | 거르지 않은(또는 다시 연) 까닭. 하나만 적고 나머지는 `route_json.forced_all` |
| `route_json` | 3.2 의 판정 기록 | 분류할 때의 두 신호와 규칙을 그대로 얼린다 |
| `basis` | `cards` · `background` · `role_only` · `search_only` · `noinput` · `filtered` | `reviewed` 셀을 무엇으로 봤나에 둘을 더한다 — `noinput`(입력 결손 두 질문), `filtered`(`na_irrelevant` 셀 — 카드로 보지 않았다) |
| `sample_json` | `{filter_audit{score, picked_by: rate·floor·domain_floor, result}, shadow{would_filter, result}}` | 표본 재검토와 대표 그림자의 결과(3.4) |

더하는 전이(`review_cells.CELL_TRANSITIONS`).

| 에서 → 으로 | 누가 · 언제 |
|---|---|
| `running → na_irrelevant` | 분류(C3-6) — 두 신호가 다 무관이고 강제 사유가 없다 |
| `running → no_input` | `noinput` 정산(C3-3) |
| `na_irrelevant → pending` | 넓힘 · 늦은 넘김 · 보충 표본(C3-7). `reopened_n+1`, `route_forced` 를 적는다 |
| `failed → pending` | 사람의 다시(C3-4). `tries`·`charged`·`infra_streak` 를 0 으로 |
| `reviewed · no_input → pending` | 사람의 `force` 다시(C3-4). 그 셀의 판정 행(`rr_card_verdicts`)을 같은 트랜잭션에서 지운다(WP3b 3.3.1). 쓰는 곳 — 엔진 판이 오르기 전에 끝난 M2 파일럿 셀을 새 판(`cr-verdict-2` 의 `mech`)으로 다시 돌린다(`m3-engine-ops.md` A12) |
| `skipped`(넘김)은 지금처럼 `failed` 에서만 | PLAN 4절 C-18 |

### 3.2 거르기 규칙

한 셀 (단위 u, 전문가 a, 영역 d)의 분류는 위에서 처음 맞는 줄이다. 분류는 그 전문가의 세션에서 훑기 바로 뒤에 한 번 한다(같은 입력이면 같은 답 — 재기동해도 같다).

| # | 조건 | 결과 | `route_forced` |
|---|---|---|---|
| 1 | 잡의 `filter` 가 `off` | 검토 | `filter_off` |
| 2 | a 가 그 영역의 1순위(`rank_in_domain = 1`, Tier A) | 검토(그림자 판정만 적는다 — 3.4) | `rank1` |
| 3 | u 가 전역 단위(`kind = global`) | 검토 | `global_unit` |
| 4 | a 의 카드가 0장(훑기 없음) | 검토 | `no_cards` |
| 5 | a 가 입력 결손 전문가이고, 그 훑기가 결측 블록을 받지 못했다(요청에 `extra.missing` 이 없었거나 답의 `meta.prompt_rev.sweep` 이 결측 문장 전 판 `cr-sweep-1`) | 검토(`noinput` 길) | `input_gap` |
| 6 | 그 타깃에서 d 가 넓혀졌거나 타깃 전체 거르기가 꺼졌다(3.4) | 검토 | `widened` · `filter_off` |
| 7 | 다른 전문가의 훑기가 u 를 d 로 넘겼다(`h` 줄, 분류 시점까지 온 것) | 검토 | `handoff` |
| 8 | 그 대상의 1순위 셀(검토 대상 단위 전부 — 잡 범위와 상관없이)이 아직 다 종결되지 않았다 | 검토 | `tier_a_pending` |
| 9 | 코드 신호(u, d) = `unrelated` **그리고** 훑기(u, a) = `unrelated` | 거름 — 단 `sample_score('filter_audit', T, u, a) < audit_pct/100` 이면 표본(`route='audit'`, `route_forced='filter_audit'`) | — |
| 10 | 그 밖(어느 한쪽이 `related` 또는 `unknown`) | 검토 | — |

- **모르면 검토다.** 코드 신호의 `unknown`(표에 없는 변경 코드 · 영역이 비어 있는 메커니즘), 훑기의 `maybe`·`yes`·`stamp`·`error`·답에 없는 단위·훑기 실패(`sweep_state='failed'`)는 전부 '관련' 쪽이다.
- 훑기가 `unrelated` 인 것은 `rel == 'no'` 이고 `k` 가 비고 그 쪽이 도장(`stamp`)이 아닐 때뿐이다.
- 8번은 X1-12 (4)다 — 대표 그림자의 놓침률이 서기 전에 B·C 의 셀을 거르지 않는다. 기다리지 않고 검토로 보낸다(비용만 든다). 1순위를 범위에서 뺀 잡(`scope.tiers=['B']` 등)은 그래서 거르지 않는다 — 검토 순서가 이미 1순위를 먼저 집으므로 전원 잡에서는 앞의 몇 명만 이 줄에 걸린다.
- 5번은 X1-17 이다 — 결측을 모르는 훑기는 회로 전문가의 'ECAD 가 없어 보이는 것이 없다' 와 '무관하다' 를 가르지 못한다. `m3-engine-ops.md` 계약 6 이 훑기 요청의 `extra.missing[{kind, note}]` 를 받아 '결측 입력이 와도 무관한 단위만 no, 결측 때문에 가릴 수 없으면 maybe' 를 지시에 더한다. 앱은 입력 결손 전문가의 훑기에 그 칸을 싣고(실마리는 3.6 의 `input-gap.v1.json`), 그 판의 답일 때만 그 전문가의 셀을 거른다. 옛 판 엔진의 답이면 거르지 않는다(열린 물음 a-2).
- `route_json` 모양은 아래와 같다.

```json
{"rule": "both_unrelated", "decision": "filtered|review|audit", "filter": "on", "routing_rev": "change-routing-1.0|mech-owners-1.0|tax-1.2",
 "code": {"verdict": "unrelated|related|unknown", "related_domains": ["mech","xd","sim"],
          "via": {"mech": ["mechanical.bending"], "role": ["housing"], "always": []}, "unmapped": []},
 "sweep": {"verdict": "unrelated|related|unknown", "rel": "no", "k": [], "why": ["…"], "stamp": false},
 "handoff": [{"from": "<agent_key>", "why": "…"}], "forced_all": [], "audit": {"score": 0.0312, "pct": 5}}
```

### 3.3 코드 신호 — 변경 → 메커니즘 → 영역

메커니즘 → 영역 배정표는 `m3-synthesis.md` 3.2 가 새 자산 `mech-owners.v1.json`(소유 · 관련, 52행, `review_status`)으로 낸다(D-34). **변경 → 메커니즘** 표는 어디에도 없다(01-domainmap — 변경 → 영역 방향은 코드에 없다). 그래서 이 꾸러미가 자산 하나를 낸다.

`app/assets/change-routing.v1.json`(새, 판 `change-routing-1.0`, `status: seed`).

```json
{"version": "change-routing-1.0", "status": "seed",
 "codes": [
   {"match": "part.thickness_changed", "mechanisms": ["mechanical.bending", "mechanical.drop_stress", "interface.clearance_close", "process.warpage"]},
   {"match": "iface.gap_changed",      "mechanisms": ["interface.clearance", "interface.clearance_close", "interface.tolerance_stackup"]},
   {"match": "param.material.*",       "mechanisms": ["material.property_uncertain", "material.supplier_change", "thermal.cte_mismatch"]},
   {"match": "result.part_metric_shift", "mechanisms": ["mechanical.drop_stress"]},
   {"match": "mesh.density_changed",   "mechanisms": []}
 ],
 "change_kinds": {"dimension": ["…"], "placement": ["…"], "material": ["…"], "none": null},
 "roles": {"pcb": ["pcb", "passive", "soc", "mem"], "battery": ["pwr"], "display": ["disp"], "shield_can": ["rf", "pcb"],
           "fpcb": ["pcb"], "housing": ["mech", "xd"], "frame": ["mech", "xd"], "bracket": ["mech", "xd"],
           "screw": ["mech", "xd"], "tape": ["mech", "material"]},
 "always": []}
```

- 줄의 `code`(`units.py` 의 `_item` — `node.<op>`·`edge.<family>.<op>`·`scope.changed`·`param.<attr>`·`param.material.<field>`·`param.dim`·`param.<metric>`·`param.rollup`·의미 이벤트 33종·모르는 버킷 `<layer>.<rest>`)를 `codes` 의 `match`(정확 일치 또는 끝의 `*` 접두)로 찾고, 없으면 그 줄의 `change_kind` 를 `change_kinds` 로 찾는다. 둘 다 없거나 값이 `null` 이면 그 줄은 `unmapped` 이고 **그 단위 전체가 `unknown`** 이다(관련으로 이미 잡힌 영역은 그대로).
- `mechanisms: []` 는 '설계 변경이 아니다' 라는 뜻이다(메시 밀도 등). 관련 영역을 더하지 않지만 `unknown` 도 아니다.
- 역할은 단위 줄에 나오는 부품의 정규명 토큰(`ir_builder.SEED_SYNONYMS` 의 정규명 10종)에서 뽑는다. 역할은 **더하기만** 한다 — 역할 미상 부품이 `unknown` 을 만들지 않는다(그러면 W2-09 처럼 거르기가 사라진다. 두 번째 신호인 훑기가 그 몫을 맡는다).
- 결과 — `code_signal(u)[d] ∈ related · unrelated · unknown`. `related` = d 가 (줄의 메커니즘들 → 배정표의 소유 ∪ 관련) ∪ (역할 → 영역) ∪ `always` 에 든다. `unknown` = 그 단위에 `unmapped` 줄이 있고 d 가 `related` 가 아니다. 나머지는 `unrelated`.
- **승인 문.** 배정표의 `review_status` 가 `approved` 가 아니면 코드 신호는 전 영역 `unknown` 이다(`m3-synthesis.md` 3.2 의 승인 문과 같은 규칙 — 승인 전에는 거르기가 사실상 꺼진다). 이 문서의 변경 → 메커니즘 표도 같은 칸(`status: seed|approved`)을 두고 둘 다 `approved` 일 때만 연다.
- 판 표지 `routing_rev = change-routing 판 | mech_owners_version | taxonomy_version` 을 셀 `route_json` 과 잡 `knobs` 에 얼린다.
- 시험이 표의 닫힘을 지킨다 — devseed 대본 전부와 `tests/fixtures/diff_pairs` 를 실제 `compute_diff` → `units.compute` 로 돌려 나온 줄 코드가 전부 `codes` 나 `change_kinds` 로 풀린다(모르는 버킷만 예외). 메커니즘 코드는 전부 택소노미 1.2 의 활성 코드다.

**형제 계획에서 받는 인터페이스**(`m3-synthesis.md` 3.2 의 이름 그대로).

```python
taxonomy.mech_owners() -> dict[str, {"owners": tuple, "related": tuple}]   # 활성 메커니즘 → 영역
taxonomy.domains_for(codes) -> dict[str, "owner" | "related"]               # 메커니즘 코드 묶음 → 영역(이 문서가 부르는 것)
taxonomy.mech_owners_meta() -> {"version", "review_status", "reviewed_at"}  # 판과 승인 문
```

- 그쪽 불변식 '15개 영역이 전부 어느 행엔가 나온다' 가 이 문서에 꼭 필요하다(닿지 않는 영역은 코드 신호가 늘 '무관' 이라 훑기 하나로 걸러진다 — 두 신호 규칙이 무너진다).
- 사용자가 배정표를 한 번 훑을 때(D-34) 변경 → 메커니즘 표와 역할 표도 같이 훑는다(열린 물음 b-1).

### 3.4 표본 재검토 · 대표 그림자 · 넓힘

- **표본(즉시).** 3.2 의 9번에서 `sample_score('filter_audit', T, u, a) < audit_pct/100`(기본 5%)이면 그 셀은 걸러지지 않고 끝까지 판정된다(`route='audit'`). 해시라 재기동해도 같은 셀이 뽑힌다.
- **보충 표본(잡 끝).** 그 잡 범위의 검토가 다 닫혀 잡을 마치기 직전에(`_complete_or_phase` 의 completed 갈래 앞) 거른 셀 전체(타깃)를 `sample_score` 오름차순으로 세워 표본 수를 `n_audit = max(ceil(audit_pct% × N_filtered), min(N_filtered, 59))` 까지 채우고, 거른 셀이 있는 영역마다 최소 1건을 채운다. 모자라는 만큼 그 잡 범위 안의 거른 셀을 `na_irrelevant → pending`(`route_forced='filter_floor'`)으로 다시 열고 잡은 계속 돈다. 59 는 '놓침 0 이면 95% 상한 5%' 의 최소 표본이다(WP4 3.4.2 의 표). 작은 대상에서 5% 가 0~몇 건이라 상한이 뜻을 잃는 것을 막는다(열린 물음 a-3).
- **대표 그림자.** 1순위 전문가(거르지 않는다)의 셀 가운데 3.2 의 9번이 참이었을 셀(`would_filter`)을 `sample_json.shadow` 에 적고, 정산 때 그 결과를 적는다. 대가 없이 얻는 표본이다(X1-12 의 정의 — '거르기가 닫았을 셀' 의 놓침).
- **결과 넷**(정산 때 `review_verify.audit_outcome` 이 정한다 — X1-13).

| 결과 | 조건 |
|---|---|
| `risk_miss` | 실효 FAIL·WARNING 이 하나라도 있다(실효 `undetermined` + `split=1` 포함), 또는 카드 밖 리스크(`dir=risk`)의 심각도가 중대·치명 |
| `relevance_miss` | 걸림은 없지만 `applies='yes'` 실효 행이 있거나 카드 밖 줄(경미·개선)이 있다 |
| `undetermined` | 위 둘이 아니고 `applies='unknown'`·`undetermined` 행이 있다 |
| `kept` | 전부 `na` 이고 카드 밖이 `none` |

- **넓힘.** 표본이나 그림자에서 `risk_miss` 가 나오면 그 영역 d 를 그 타깃에서 넓힌다 — d 의 거른 셀을 전부 다시 열고(`route_forced='widened'`), 이후 d 의 분류는 6번에 걸린다. 넓힌 영역이 **셋 이상**이면 그 타깃의 거르기를 끈다(남은 거른 셀 전부 다시 연다). 넓힘 상태는 저장하지 않고 원장에서 유도한다(`sample_json.*.result = 'risk_miss'` 인 셀의 영역) — 재기동·반출에도 같다.
- **늦은 넘김.** 어느 전문가의 훑기가 `h` 줄로 u 를 d 로 넘기면, 그때 이미 걸러진 (u, d 의 전문가) 셀을 다시 연다(`route_forced='handoff'`).
- **다시 열린 셀**은 보통 셀과 똑같이 돈다. 그 전문가 머리는 `ready·partial → planned` 로 돌아가고(`review_cells._reopen`), 다시 마감하면 보고서 `revision` 이 오르며 등록부는 형제 계획의 `registry.merge(prune=True)` 로 정리된다(P-13).
- **비율.** 보고서·진행판은 `risk_miss / 표본`(정확 이항 95% 상한 `audit.binom_upper`)과 보수 상한 `(risk_miss + undetermined) / 표본`을 따로 싣는다. 그림자는 따로 센다(무작위 표본이 아니다). 넓힌 영역의 표본은 넓힌 뒤에도 표본 셈에 남는다.

### 3.5 이중 판정 — 걸린 카드에만

- 잡 `knobs.dual`: `flagged`(기본) · `all`(M2 동작). 잡 `knobs.dual_calib = 'tier_a'` — 1순위 전문가의 셀은 늘 묶음 전체를 rev 한다(보정용 — 순서 뒤집힘과 걸림 없음 → 걸림 뒤집힘을 무작위가 아닌 고정 모집단에서 재는 유일한 자리. 열린 물음 a-6).
- `flagged` 일 때 셀 · 묶음마다 fwd 실효(빠진 카드 재질의 뒤)가 FAIL·WARNING 인 별칭이 둘 이상이면 그 별칭만 담은 rev 요청 하나를 낸다(카드 순서는 엔진이 뒤집는다 — M2 결정 #19). 하나뿐이면 rev 를 내지 않는다 — 그 카드는 이미 단독 재질의(`solo`)로 간다(`_solo_set` 의 '실효가 걸림' 갈래). 걸린 카드는 그래서 늘 두 번 이상 판정된다(fwd + solo, 둘 이상이면 rev 까지).
- `_Cell.dual_decks` 를 `dual_aliases`(rev 를 실은 별칭 집합)로 바꾼다. `_solo_set` 의 'rev 를 물었는데 rev 행이 없다' 갈래는 별칭으로 판단한다.
- `effective_rows` 는 그대로다 — rev 가 없는 카드는 fwd(와 solo)가 실효이고 `agree` 는 NULL 이다.
- M2 잡(`knobs.dual_rate` 만 있고 `dual` 이 없다)은 `all` 로 읽는다. 다시 계획해도 이미 돈 셀의 결과는 바뀌지 않는다(입력 지문에 `dual` 이 들지 않는다 — 계획만 바뀐다).
- `m3-engine-ops.md` B2(사용자 몫)는 같은 걱정에서 '걸리지 않은 묶음의 무작위 10% rev' 를 묻는다. 앱 쪽은 손잡이 하나(`HWAXRISK_REVIEW_DUAL_NEG_PCT`, 기본 0)와 `sample_score('dual_neg', T, u, a, deck) < pct` 한 줄이다. 1순위 보정과 겹치지 않는다(보정은 재기, 무작위 10% 는 그 밖 전문가의 거짓 '문제없음' 을 실제로 잡는다). 권고는 열린 물음 b-3.

### 3.6 입력 결손 호출 — 앱이 보내고 기대하는 것(엔진 계약은 `m3-engine-ops.md`)

- 대상 — `planner.review_order` 의 `input_gaps` 가 빈 목록이 아닌 전문가(ECAD 의존 6영역 · 타깃에 ECAD 없음 — 110명). 3.2 의 5번으로 늘 검토로 가고, 그 셀은 `verdict`·`offcard` 대신 단위마다 `noinput` 한 번이다(WP3b 3.7.4 의 3′).
- 요청 — `run_body("noinput", variant=None, cards=<팩 전부 — 훑기 k 에 걸린 것 먼저, 나머지 팩 순서>, digest=<전 카드 제목>, unit=<review_payload>)`. `unit.missing` 에 `{kind:'ecad', note:<영역 실마리>}` 를 싣는다. 실마리는 새 자산 `app/assets/input-gap.v1.json`(영역 6개 — passive '소자 위치의 변형률·지지 스팬', soc 'Z 간극·TIM 접촉', mem '언더필·스택업', pwr '팩 주변 간극과 허용치', rf '방사체·접지 금속과의 거리', pcb '보드 고정점·지지 스팬·보드 근접 계면' — WP2 3.10.2 와 `cad-capabilities.md`)이다. 넘치는 카드는 엔진이 제목으로 내리고 `bg_dropped` 로 알린다(오프카드와 같은 규칙).
- 결과 행(`m3-engine-ops.md` 계약 2 그대로) — `{t:'q1', impact:'yes|no|unknown', title, mech, mech_free, path, l:[…], k, cq, sev, why}` · `{t:'q2', item(없으면 ""), needs, k, l, why}` · `{t:'more', more:'yes|no'}` · `{t:'inj', at, text}`. `quality.maybe_more` 가 참이면(q1 이 `items_max` 에 닿았거나 `more=yes`) 앱이 받은 q1 의 `title` 을 `extra.known` 에 실어 '이것 말고 더' 를 최대 3번 다시 묻는다(카드 밖의 `MORE_REASKS` 와 같은 규칙 — X1-16). `limits.kinds`·`cell_kinds` 에 `noinput`, `prompt_rev.noinput`(`cr-noinput-1`), `runnable.noinput` 이 있다.
- **셀 지문의 판.** 지금 `review_runner.prompt_key(lim)` 은 종류 판 전부를 잇는다 — 엔진이 `summary`·`noinput` 을 더하거나 판 하나를 올리면 그 종류를 부르지 않는 셀까지 처음부터 돈다. `prompt_key(lim, kinds)` 로 바꿔 그 셀이 실제로 부르는 종류만 잇는다(카드 전문가 `sweep·verdict·offcard`, 입력 결손 전문가 `sweep·noinput` — `m3-engine-ops.md` 의 요청).
- 앱의 회계(`review_verify.accept_rows(kind='noinput')`) — `l` 은 그 단위의 줄이어야 하고(Q8), `k` 는 실은 별칭이어야 하며, `cq` 는 그 카드의 얼린 원문으로 다시 대조한다(`quote_ok`). 문자열 하나로 온 목록은 한 항목으로 읽는다(D-25).
- 정산(WP3b 3.7.4 의 표).

| q1 | q2 | 셀 | `extras_json.noinput.outcome` |
|---|---|---|---|
| `impact='yes'` 가 하나라도 | 무엇이든 | `reviewed`(`basis='noinput'`) | `impact` |
| `yes` 없고 `unknown` 있음 | 무엇이든 | `no_input` | `unknown` |
| 전부 `no` | 요청 ≥1 | `no_input` | `request` |
| 전부 `no` | 요청 0(까닭만) | `reviewed`(`basis='noinput'`) | `none` |

- 저장 — 받은 행은 `extras_json.noinput{q1[], q2[], outcome}` 과 호출 원장 `result_gz`. 카드 판정 표(`rr_card_verdicts`)에는 쓰지 않는다(PK 가 카드 × 변형이라 맞지 않는다).
- finding — q1 `yes` 줄이 finding 후보다(`source_kind='card_review'`, `basis` 표지 `noinput`, 메커니즘은 `mech`). 정책은 `hold` 그대로(사용자 결정 2). q2 는 보고서의 '입력이 오면 확인할 것' 이다.
- 엔진이 아직 `noinput` 을 모르면(`limits.kinds` 에 없음) 앱은 그 호출을 내지 않고 잡을 `agent_outdated`(300초 자동 재개)로 멈춘다 — `unsupported_kind` 를 받아 `contract`(자동 재개 없음)로 서는 길을 피한다. `m3-engine-ops.md` 는 옛 엔진에 보내면 `contract` 보류라고 적었다 — 앱이 먼저 `kinds` 를 보면 그 길이 생기지 않는다(M3.md 에서 한 줄로 맞춘다).

### 3.7 실패 셀 처분 — REST · Claude

| 경로 | 권한 | 본문 | 응답 |
|---|---|---|---|
| `POST /api/targets/{key}/cells/retry` | editor | `{cells?: [[unit_id, agent_key]…], filter?: {job_id?, agent_key?, unit_id?, domain?, error_code?, state?}, reason?, force?: false, start?: true, consent?: false}` | `{target_key, matched, retried, not_failed, keys_total, keys[≤50], experts, job{action: created·adopted·waiting·none, job_id?, calls_estimate?}, audit_id, changed}` |
| `POST /api/targets/{key}/cells/skip` | editor | `{cells?, filter?, reason}`(사유 필수, 4~300자) | `{target_key, matched, skipped, not_failed, keys_total, keys[≤50], experts, job{action: created·adopted·none, job_id?}, audit_id, changed}` |
| `POST /api/targets/{key}/undefer` | editor | `{reason}` | `{target_key, undeferred, agents[≤50], agents_total, changed}` |
| MCP `risk_job_action(job_id, action, reason=None, filter=None)` | 쓰기(위임 신원) | `action` 에 `retry_failed`·`skip_failed` 를 더한다. 그 잡이 찍은(`run_id`) `failed` 셀이 기본 집합이고 `filter` 로 좁힌다 | 위 REST 와 같은 모양 |

- `cells` 와 `filter` 는 하나만 준다(둘 다·둘 다 없음·모르는 칸은 422 `cells_selector_invalid`). 다시는 기본이 `failed` 만이고, `force:true` 면 `reviewed`·`no_input` 도 다시 연다(사유 필수, 판정 행을 지운다 — 3.1). 넘김은 `failed` 만이다. 대상이 아닌 셀은 `not_failed` 로 세고 손대지 않는다. 바꿀 것이 없으면 200 `changed:false`(지금 `job_action` 의 관례).
- **다시** — 한 트랜잭션에서 `failed → pending`, `tries = charged = infra_streak = 0`, `not_before·error_*` 비움, `reopened_n+1`, `route_forced='human_retry'`(거르지 않는다), `status_source='human'`·`decided_by`·`decided_at`·`decide_note`. 그 전문가 머리 `ready·partial·blocked → planned`(`blocked` 는 묶음 시도 수를 비운다 — 묶음 실패로 진 셀의 다시가 묶음부터 받게). 살아 있는 검토 잡이 있고 그 범위가 그 셀을 덮으면 `run_id` 를 그 잡으로 찍고(`adopted`), 덮지 않으면 다음 잡을 기다린다(`waiting`). 살아 있는 잡이 없고 `start` 면 그 셀들의 (전문가, 단위)로 범위를 잡은 검토 잡을 만든다(`created` — `create_review_job` 그대로, 동의 문턱도 그대로). 동의가 필요한데 없으면 **아무것도 바꾸기 전에** 422 `consent_required` 다.
- **넘김** — `failed → skipped`, 같은 사람 표기 열. 그 전문가 머리 `partial·blocked → planned` 로 두어 다시 마감되게 한다 — 살아 있는 잡이 있으면 그 잡에 찍고, 없으면 셀 0개짜리 마감 잡(`scope.agents` = 그 전문가들, 호출 추정 0)을 세운다. 묶음을 못 받은 전문가(`pack_status='error'`)도 마감 목적으로 집히게 `claim_next_expert(purpose='finalize')` 의 묶음 조건에 `error` 를 더한다(보고서는 `write_blocked` 갈래로 쓴다).
- **감사** — 요청 하나에 `rr_audit` 한 행(`scope='coverage'`, `subject_id=<target_key>`, `action='cells.retry'·'cells.skip'·'coverage.undefer'`, `after_json{n, selector, keys_sha, keys[≤200]}`, `reason`, MCP 길은 `actor_verified=0`·`channel='mcp'`). 셀마다의 기록은 셀 행의 `decided_by·decided_at·decide_note` 다(WP5b 3.10.5 의 '행위 하나에 행 하나').

### 3.8 보류 해제

- `flow='cells'` 대상의 검토 잡을 만들 때 범위 안 전문가의 `rr_coverage` 가 `deferred(reason='ecad_absent')` 면 같은 트랜잭션에서 `pending` 으로 풀고 `rr_audit` 한 행(`coverage.undefer`, `reason='review_scope'`, 요청자)을 남긴다. 풀지 않으면 `close_review_seat` 가 그 행을 건드리지 않아 `deferred`(종결 어휘)로 남고 완결이 거짓으로 선다.
- `flow='panels'` 대상(검토를 얹은 대상 포함)은 풀지 않는다 — 원장을 닫지 않는 길이고(M2 결정 #8) 패널 편성이 바뀐다. 사람이 원하면 `POST /targets/{key}/undefer` 로 푼다(WP2 3.10.5 — 도는 잡이 있으면 409 `job_live`, 응답에 '저장된 레벨은 내려가지 않는다' 와 영역별 need·have 를 싣는다 — W2-16 (c)).
- `planner.ALLOWED_TRANSITIONS['deferred'] = {'pending'}`. `tests/test_planner.py` 의 '종결 상태에서 나가는 길은 carried 뿐' 단언을 의도를 적어 고친다.
- 로스터 동결(`freeze_roster`)은 바꾸지 않는다 — WP2 3.10.1 의 `defer_absent=False` 는 `create_target` 의 `persist_error` 되돌림(`flow → panels`)과 부딪친다(이미 보류 없이 얼린 로스터가 패널 대상이 된다). 푸는 때를 잡 생성으로 옮기면 그 길이 없다.

### 3.9 원장 롤업 표(`planner.review_rollup`) — 처음 맞는 줄

| # | 셀 | `rr_coverage` | 사유 |
|---|---|---|---|
| 1 | 열린 셀(pending·running)이 있다 | 닫지 않는다 | `open_cells` |
| 2 | `reviewed` ≥1, 전부 `basis='noinput'` | `done_weak` | `input_gap:ecad_absent`(실패·넘김이 있으면 `input_gap:ecad_absent;partial:<n>`) |
| 3 | `reviewed` ≥1, 실패·넘김 셀이 있다 | `done_weak` | `partial:<n>`(지금 그대로) |
| 4 | `reviewed` ≥1, 검증된 근거가 있다 | `done` | — |
| 5 | `reviewed` ≥1, 검증된 근거가 없다 | `done_weak` | `no_cards` · `no_verified_cite` |
| 6 | `reviewed` 0, 열린 실패(`failed`)가 있다 | 닫지 않는다 | `failed_open:<n>` |
| 7 | `reviewed` 0, 넘김 ≥1 | `skipped` | `cells_skipped:<n>`(X1-23) |
| 8 | `reviewed` 0, `no_input` ≥1 | `abstain` | `no_input:ecad_absent` |
| 9 | `reviewed` 0, 전부 거름 | `abstain` | `filtered:<n>` |

`abstain`·`skipped` 를 깊이·strong 분모에서 빼는 것은 완결 판정(형제 계획)의 몫이다(X1-02). 이 표는 사유 문자열을 그 판정이 읽을 수 있게 고정한다.

### 3.10 완결 몫 인터페이스 — `review_cells.closure_cells`

형제 계획의 완결 판정과 종합 보고서 머리가 읽는다. 원장에서 GROUP BY 로 세어 5초 폴링에도 쓸 수 있다.

```python
review_cells.closure_cells(store, target_key) -> {
  "grid": {"roster": 359, "units": 20, "expected": 7180, "actual": 7180},
  "by_state": {"pending": 0, "running": 0, "reviewed": 4188, "na_irrelevant": 2992, "no_input": 0, "failed": 0, "skipped": 0},
  "by_basis": {"cards": …, "background": …, "role_only": …, "search_only": …, "noinput": …, "filtered": …},
  "failed": {"open": 0, "by_code": {}},
  "skipped": {"n": 0, "experts": 0, "by_note": [{"note": "…", "n": 0, "by": "…"}]},
  "filtered": {"n": 2992, "would_filter": 3150, "by_domain": {"mech": {"filtered": …, "audited": …}},
               "audit": {"sampled": 158, "floor_met": true, "risk_miss": 0, "relevance_miss": 3, "undetermined": 1, "kept": 154,
                         "upper95": 0.019, "upper95_conservative": 0.030},
               "shadow": {"would_filter": 120, "risk_miss": 0, "upper95": 0.025},
               "widened": [], "off": false},
  "no_input": {"experts": 110, "cells": 2200, "by_outcome": {"impact": …, "unknown": …, "request": …, "none": …}},
  "undetermined": {"rows": …, "cells": …},
  "out_of_scope_pending": 0, "invariants": []}
```

- `invariants` 는 `review_invariants` 의 M3 판이다 — `failed` 인데 `error_code` 가 빈 셀 · `skipped` 인데 `decided_by`·`decide_note` 가 빈 셀 · `na_irrelevant` 인데 `route='filtered'`·`route_json.rule` 이 없는 셀 · `no_input` 인데 `extras_json.noinput` 이 없는 셀 · 격자 수 ≠ 로스터 × 검토 대상 단위. M3 나갈 기준 1('모든 셀이 종결이거나 사유 있는 failed')의 코드 판정이 `by_state.pending + running == 0 and invariants == []` 이다.
- 잔여 낱말 제안(형제 계획이 표기를 정한다) — `failed`(열린 실패와 코드별 수) · `skipped`(넘김 수와 사유) · `no_input`(전문가 수 · 셀 수 · 결과별) · `filter_audit`(표본이 `floor_met` 가 아니거나 상한이 5% 를 넘음) · `undetermined`(X1-15 — 보류 행).

### 3.11 손잡이

리스크 앱(환경변수 > `$DATA_DIR/knobs.env` > 코드 기본값 — M2.md 4.5 그대로).

| 이름 | 기본 | 뜻 |
|---|---|---|
| `HWAXRISK_REVIEW_CONCURRENCY` | **4 → 8** | 앱 검토 워커 수(D-34). 서버 관문 limit 을 넘겨 띄우지 않는 것은 그대로 |
| `HWAXRISK_REVIEW_FILTER`(새, 선택지) | `on` | `off` · `shadow`(분류만 적고 거르지 않는다 — 그 대상 전체가 그림자) · `on` |
| `HWAXRISK_FILTER_AUDIT_PCT`(새) | 5 | 거를 셀 가운데 끝까지 판정하는 비율(%, 0~100). 하한 59건·영역당 1건은 코드 상수 |
| `HWAXRISK_REVIEW_DUAL`(새, 선택지) | `flagged` | `flagged`(걸린 카드만 rev, 1순위는 전량) · `all`(M2 동작) |
| `HWAXRISK_REVIEW_DUAL_NEG_PCT`(새) | 0 | 걸림 없는 묶음의 무작위 rev 비율(%) — `m3-engine-ops.md` B2 를 사용자가 고르면 10 |
| `HWAXRISK_EVIDENCE_LIVE`(새, 불리언) | 1 | 근거 꾸러미 실호출(B 층). 0 이면 `rr_unit_live.status='none'` |

- 선택지 손잡이를 위해 `config.Knob` 에 `kind="choice"` 와 `choices` 를 더한다(목록 밖 값은 기동을 막는다 — 불리언과 같은 규율).
- 코드 상수 — `AUDIT_MIN_N = 59` · `AUDIT_DOMAIN_FLOOR = 1` · `WIDEN_ALL_AT = 3` · `LIVE_MAX_TRIES = 6`(60초부터 두 배).
- 잡에 얼리는 값 — `params_json.knobs = {dual, dual_calib, filter, audit_pct, audit_min_n, routing_rev, live, sweep:'on', max_charged, sample_salt}`. 도는 중에 손잡이가 바뀌어도 그 잡은 그대로다.
- 엔진 손잡이(`m3-engine-ops.md`) — `CARD_REVIEW_CONCURRENCY` 8, `CARD_REVIEW_CONCURRENCY_WITH_DELIB` 4(기본을 `max(1, conc // 2)` 로), `CARD_REVIEW_K` 는 M0-b 실측값. 포털 `card_review_max_streams`(12)는 앱 동시 수 + 단발(limits·pack·plan) 몫보다 커야 한다 — 8 이면 그대로 된다.

### 3.12 오류 코드(새 것)

| code | 상태 | 어디 | 뜻 |
|---|---|---|---|
| `cells_selector_invalid` | 422 | retry·skip | `cells`·`filter` 가 둘 다거나 둘 다 없거나 모르는 칸 |
| `reason_required` | 422 | skip·undefer | 사유가 비었거나 4자 미만·300자 초과 |
| `job_live` | 409 | undefer | 그 대상에 도는 잡(어느 mode 든)이 있다 |
| `consent_required` | 422 | retry(`start`) | 기존 코드 — 바꾸기 전에 낸다 |
| `noinput` 미지원 → 잡 보류 `agent_outdated` | — | 루프 | `limits.kinds` 에 `noinput` 이 없다 |
| `live_infra_exhausted` · `live_schema_mismatch` · `live_error_body` · `live_denied` | — | `rr_unit_live.gaps_json` | B 층 호출의 실패 사유(셀 오류가 아니다) |

없어지는 것 — 422 `input_gap_m3`. 앱의 `review_ops` 별칭표에 그 이름을 남겨 옛 클라이언트의 재시도 안내가 깨지지 않게 한다.

### 3.13 v5 — 이 꾸러미의 몫

**한 표뿐이다.** 셀 상태·거르기·표본·처분·입력 결손은 v4 의 열(`route`·`route_forced`·`route_json`·`basis`·`sample_json`·`extras_json`·`decided_*`·`reopened_n`)과 `rr_jobs.params_json`·`progress_json` 으로 담는다. v4 주석이 v5 로 미뤄 둔 `input_gap_json`·`route_det`·`route_llm`·`audit_kind`·`audit_result`·`ix_rr_cells_reuse` 는 **넣지 않는다**(각각 계산 · `route_json` · `sample_json` 으로 충분하고 승계는 구현하지 않는다). 블록 파일의 주인은 `m3-synthesis.md` 이고 아래 문장을 그 블록에 덧붙인다.

```sql
CREATE TABLE IF NOT EXISTS rr_unit_live (                     -- 검토 단위의 실호출 근거(B 층). 단위마다 한 번 얼리고 고치지 않는다
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, owner_sub TEXT NOT NULL,
  status TEXT,                                  -- NULL(아직) | ok | partial | none | skipped(셀이 이미 돈 단위)
  plan_json TEXT NOT NULL DEFAULT '[]',         -- 결정적 호출 계획 [{tool, args, call_id, state, code}]
  lines_gz BLOB, live_sha TEXT, live_chars INTEGER,          -- 렌더한 근거 줄([{ref:'tool:b-…', text}]) gzip
  credential_kind TEXT, credential_email TEXT,  -- 부른 자격(사용자 PAT 만 — 사용자 결정 3)
  gaps_json TEXT,                               -- 못 받은 호출과 사유
  attempts INTEGER NOT NULL DEFAULT 0, not_before INTEGER,  -- 인프라 실패 재시도
  frozen_at INTEGER, created_at INTEGER NOT NULL, updated_at INTEGER,
  PRIMARY KEY(target_key, unit_id));
```

- 등록 — `export._SINCE_COLS['rr_unit_live'] = ('updated_at', 'created_at')` · `routes.TRANSFER_DERIVED` 에 `target_key IN (… project_id = ?)` · `routes.PURGE_BLANK_SQL` 에 `lines_gz`·`plan_json`(재질명이 든다 — `'[]'`)·`gaps_json`(NULL). 반출에 싣는다(사용자 결정 1 의 반출 제외는 카드 원문 `rr_card_packs` 뿐이다).
- `tests/test_store.py::PUSHED_DDL_SHA256[5]` 는 블록이 확정되는 커밋(C3-16)에서 굳힌다. 그 전에는 로컬 커밋으로만 쌓는다(PLAN 4절 C-2).
- 표 규약 시험(`owner_sub` · PK · CHECK 없음)과 v4 → v5 이행 멱등 · `pre-migrate-v4-*` 사본.

## 4. 걸음

순서는 의존 순이다. 걸음마다 리스크 앱 시험 전체(`cd backend && .venv/bin/python -m pytest -q`)와 `ruff check app tests` 가 초록이어야 다음으로 간다. 모든 걸음의 회귀 가드는 M2 와 같다(D-24) — `tests/rr/test_legacy_flow.py` 전부, `tests/rr/test_panel_ledger.py` 의 패널 셋 연속 `done`, 그리고 M2 의 `tests/test_review_loop.py` 끝까지 시험(M2 손잡이 `dual=all`·`filter=off` 로 그대로 초록).
소비자 시험의 입력은 생산자로 만든다(PLAN 9절) — 단위는 `devseed` → 캡처 → `create_diff` → `units`, 원장은 `tests/synth/review_rig.py` 의 루프를 가짜 엔진으로 돌려 만든다.

### C3-0 시작 걸음

- **목적.** 이 문서의 걸음이 닿는 설계서 절과 문제(`X1-01·02·04·10·11·12·13·14·15·17·23·25·27`, `W2-03·04·08·09·16`, `P-03·04·08·13·19`, `m-09·m-14`, WP5a `P-06·P-10·P-17`)를 걸음의 수용 기준으로 옮기고, 2절의 닻을 그 날의 HEAD 로 다시 grep 한다. HWAXRisk `context-notes.md` 에 'v5 는 재설계 M3 몫 — 블록은 m3-synthesis 가 쥐고 m3-cells 가 덧붙인다' 를 먼저 적는다.
- **가지.** 리스크 앱은 형제 계획과 같은 통합 가지 `m3` 에서 짓고 꾸러미마다 하위 가지(`m3-cells`)를 날마다 rebase 한다(열린 물음 a-15). v5 는 C3-16 전에는 push 하지 않는다.
- **수용 기준.** 2절의 닻 표가 그 날 HEAD 로 맞다. 형제 계획 두 편과 3.3·3.6·3.10·3.13 의 인터페이스를 한 번 맞춰 본 기록이 있다.
- **크기.** 2시간.

### C3-1 v5 의 이 꾸러미 몫

- **목적.** `rr_unit_live` 를 형제 계획의 v5 블록에 덧붙이고 반출·이양·폐기에 등록한다.
- **파일·닻.** `app/risk_store.py`(`MIGRATIONS` 는 지금 `[(1…), (2…), (3…), (4, _DDL_V4)]`), `app/export.py::_SINCE_COLS`, `app/routes.py::TRANSFER_DERIVED`·`PURGE_BLANK_SQL`, `tests/test_store.py::PUSHED_DDL_SHA256`, `tests/test_export_import.py`, `tests/rr/test_v4_upgrade.py`(v5 판을 옆에).
- **계약.** 3.13.
- **수용 기준.** 빈 DB · 얼린 v2 · v3 · v4 DB 에서 v5 이행이 멱등이고 사본이 하나 생긴다. 반출 → 빈 DB 들여오기 왕복에서 `lines_gz` 가 같다. 폐기 뒤 심어 둔 재질명이 어느 열에도 없다. 표 규약 시험 통과.
- **시험.** 행은 C3-12 의 `unit_live.ensure` 로 만든다(손 INSERT 금지 — C4 래칫). C3-12 전에는 표 존재·규약만 본다.
- **의존.** 형제 계획의 v5 블록 파일. **크기.** 3시간.

### C3-2 전원 포함 — 입력 결손 문 열기 · 보류 해제

- **목적.** 359명 전원(회로 110명 포함)을 한 잡의 범위로 받는다.
- **파일·닻.** `app/review_runner.py::create_review_job`(`gaps` 거절 블록 삭제, 같은 트랜잭션에 보류 해제), `app/planner.py`(`ALLOWED_TRANSITIONS['deferred']`, 새 `undefer(store, target_key, *, agents=None, decided_by, reason, channel)`), `app/routes.py`(새 `POST /targets/{key}/undefer`, `_ecad_absent_for_target` 그대로), `app/entry.py::_review_start_step`·`_cells_answer`(`runnable` 셈에서 `input_gaps` 거름 삭제, 문구에서 `input_gap_m3` 삭제), `app/review_ops.py`(별칭 `input_gap_m3` 보존).
- **계약.** 3.8. `review_order` 는 바꾸지 않는다(입력 결손은 계산값).
- **수용 기준.** 회로 6영역 110명이 든 범위로 잡이 선다. `flow='cells'` 대상에서 범위 안 보류 104명이 `pending` 이 되고 감사 한 행이 남는다. `flow='panels'`(얹은 대상) 은 보류가 그대로다. REST undefer 는 도는 잡이 있으면 409 `job_live`, 바꿀 것이 없으면 `changed:false`. 패널 대상의 Tier 편성 시험(`test_freeze_roster_defers_ecad_dependents_except_rank_one`·`test_tier_plan_with_ecad_absent`)이 그대로 초록이다(W2 3.10.5). 길잡이가 입력 결손 전문가를 '돌 수 있는' 셈에 넣는다.
- **시험.** `tests/test_review_routes.py`·`tests/test_planner.py`·`tests/test_mcp_entry.py`. 대상은 `factories.make_diff_target`(ECAD 없음 — 실제 `freeze_roster` 가 보류를 만든다)과 `make_target(flow=…)`.
- **의존.** C3-0. **크기.** 6시간.

### C3-3 입력 결손 호출 배선(앱 쪽)

- **목적.** 입력 결손 전문가의 셀이 `noinput` 한 번으로 닫히고, 그 결과가 finding·보고서·품질에 실린다.
- **파일·닻.** `app/engine_client.py::run_body`(종류 `noinput`, 입력 결손 전문가의 `sweep` 에 `extra.missing`), `app/review_verify.py::accept_rows`(지금 `if kind not in ("verdict", "offcard", "sweep")` — `noinput` 갈래, `q1`·`q2`·`more`·`inj` 줄), `app/review_runner.py::_Session.run`(입력 결손 전문가는 훑기 뒤 셀마다 `_noinput(cell)` — `maybe_more` 면 `known` 을 실어 최대 3번 더 — 하고 3a~3e 를 건너뛴다)·`prompt_key(lim, kinds)`(그 전문가 길의 종류만), `_Session._settle`·`review_cells.settle_cell`(3.6 의 정산표, `running → no_input`), `app/units.py::review_payload`·`_target_missing`(영역 실마리를 `missing.note` 에), 새 `app/assets/input-gap.v1.json`, `app/expert_report.py::build_findings`(q1 yes 승격)·`_scope_section`·새 `_input_gap_section`(M2 가 뺀 `input_gap` 절을 되살린다)·`_needs_section`(q2 를 접어 싣는다), `app/review_quality.py`(폭포에 `noinput_reviewed` 줄 — 지금은 `reviewed` 갈래가 판정 0 · 미판정 = 점검 카드 수로 세어 거짓 '미판정' 이 된다), `tests/synth/fake_review_engine.py`(`noinput` 응답).
- **계약.** 3.6. 루프는 호출 전에 `limits.kinds` 를 본다(엔진 미지원이면 `agent_outdated`). `card_basis='none'`(카드 0장)인 입력 결손 전문가도 역할만으로 `noinput` 을 부른다.
- **수용 기준.** 3.6 정산표의 네 줄이 각각 그 상태·`basis`·`outcome` 이 된다. `maybe_more` 면 다시 묻고 같은 제목은 한 번만 남는다. 엔진의 `summary` 판만 오른 `limits` 로 다시 계획해도 셀 지문이 그대로다(카드 전문가 · 입력 결손 전문가 둘 다). `noinput` 셀의 `cards_expected` 는 NULL 이고 품질 폭포의 `invariant.holds` 가 깨지지 않는다. q1 yes 가 finding 이 되고 `judgement_claimed` 가 남는다(정책 `hold`). 보고서에 '입력 결손 — 영역 실마리 · 영향(인용) · 입력이 오면 확인할 것' 이 실린다. 엔진이 `noinput` 을 모르는 동안 셀은 차감 없이 `pending` 이고 잡은 `agent_outdated` 다. 받은 행의 `l` 이 남의 단위 참조면 버린다(Q8). 회로 전문가 전원이 `no_input` 인 대상에서 롤업이 `abstain(no_input:ecad_absent)` 다(3.9 의 8번).
- **시험.** `tests/test_review_loop.py`(가짜 엔진 — 결손 전문가 2 · 일반 2 × 단위 4), `tests/test_review_verify.py`, `tests/test_expert_report.py`, `tests/test_review_quality.py`. 엔진 쪽 요청 검증은 C3-14 의 계약 시험.
- **의존.** C3-2, 엔진의 `noinput` 계약(`m3-engine-ops.md` 계약 2 · E3-2 — 그 전에는 가짜 엔진과 이 문서 3.6 의 모양으로 짓고 계약 예제가 오면 C3-14 가 맞춘다). **크기.** 13시간.

### C3-4 실패 셀 처분(retry · skip) · 롤업 줄

- **목적.** 잡이 '실패 N' 으로 끝난 뒤 사람이 웹과 Claude 에서 그 셀을 다시 돌리거나 사유를 달아 넘긴다. 넘김·거름·입력 결손만 남은 전문가도 원장이 닫힌다.
- **파일·닻.** `app/routes.py`(새 경로 둘, `JobBody` 는 그대로), `app/review_cells.py`(새 `select_cells(store, target_key, *, cells=None, filter=None)` · `retry_cells` · `skip_cells`, `CELL_TRANSITIONS` 에 `failed → pending`, `claim_next_expert(purpose='finalize')` 의 묶음 조건), `app/review_runner.py`(처분이 세우는 잡 — 다시는 `create_review_job` 그대로, 넘김은 마감 잡), `app/planner.py::review_rollup`(3.9), `app/entry.py::job_action`(두 갈래 — 지금 `_ALREADY` 표 옆)·`_cells_answer`(실패 셀이 남은 잡 뒤의 걸음 둘), `app/mcp_server.py::risk_job_action`(인자 `reason`·`filter` 더함, 설명에 '쓰기 — 사용자 확인 뒤'), 진행판 `review.dispositions{retried, skipped}`.
- **계약.** 3.7 · 3.9.
- **수용 기준.** 다시 — 기본은 `failed` 만 바뀌고 `not_failed` 가 센다, `force` 면 `reviewed` 셀의 판정 행이 지워지고 다시 돌며 사유가 없으면 422 다, 살아 있는 잡이 덮으면 그 잡이 집는다(`adopted`), 없으면 새 잡이 선다(`created`), 동의가 필요하면 바꾸기 전에 422 다, 묶음 실패로 진 셀의 다시가 묶음부터 다시 받는다. M2 파일럿 모양의 원장(대표 9명이 `cr-verdict-1` 로 끝남)에 `force` 다시를 걸면 새 판으로 돌고 보고서 판이 오른다(`m3-engine-ops.md` A12). 넘김 — 사유 없으면 422, 넘긴 뒤 그 전문가가 다시 마감되고 보고서 '보지 못한 것' 에 '넘김 — 사유' 로 남으며 롤업이 3.9 대로다(넘김만 남은 전문가 → `skipped(cells_skipped:<n>)`). 감사 — 요청 하나에 한 행, MCP 는 `actor_verified=0`. `pending → skipped` 는 여전히 예외다(C-18). 위임 단언 없는 Bearer 의 `risk_job_action(retry_failed)` 은 `delegation_required` 다. 도구 수는 그대로다.
- **시험.** `tests/test_review_routes.py`·`tests/test_review_cells.py`(전이표 · 표에 없는 전이 예외)·`tests/test_review_mcp.py`·`tests/test_planner.py`(롤업 표 아홉 줄). 실패 셀은 가짜 엔진의 결함 스위치(`cards_unjudged` 두 번 · 팩 502 여섯 번)로 루프가 만든다.
- **의존.** C3-2(입력 결손 셀의 롤업 줄은 C3-3 뒤에 켠다). **크기.** 11시간.

### C3-5 코드 신호 — 변경 → 메커니즘 → 영역

- **목적.** 단위 × 영역마다 '관련 · 무관 · 모름' 을 순수 계산으로 낸다.
- **파일·닻.** 새 `app/relevance.py`(첫 줄 한국어 주석 — `load_routing()` · `line_mechanisms(line, routing)` · `part_roles(names)` · `code_signal(unit_lines, part_names, *, routing, owners) -> {domain: {verdict, via, unmapped}}` · `routing_rev()`), 새 `app/assets/change-routing.v1.json`(`taxonomy.VOCAB_ASSETS` 에 이름을 더해 `/meta/vocab` 이 판을 보인다), `app/units.py`(활성 단위의 전체 줄 — `get_unit(part='lines')` 의 `code`·`change_kind` 와 부품 이름), `app/ir_builder.py::SEED_SYNONYMS`(역할 낱말), 형제 계획의 `taxonomy.domains_for`·`mech_owners_meta`.
- **계약.** 3.3. 배정표가 오기 전에는 시험용 대역(택소노미 1.1 의 38종에 손으로 단 영역)을 시험 디렉터리에만 둔다 — 운영 코드는 형제 계획의 함수만 부른다.
- **수용 기준.** 표의 닫힘(3.3 끝). 같은 입력이면 같은 답(줄 순서를 섞어 세 번). 모르는 코드가 하나 든 단위는 관련이 아닌 영역 전부가 `unknown`. 역할 미상 부품은 `unknown` 을 만들지 않는다. `mechanisms: []` 줄만 있는 단위(메시 밀도)는 전 영역 `unrelated`. 배정표나 변경 → 메커니즘 표 가운데 하나라도 `approved` 가 아니면 전 영역 `unknown` 이다(승인 문 — 승인 칸 하나만 고친 커밋이 거르기를 연다). 로스터 15영역이 전부 어느 메커니즘에서 닿는다(형제 계획의 단언과 같은 것을 이쪽에서도 두 표를 합친 결과로 본다).
- **시험.** 새 `tests/test_relevance.py` — syn40·syn150·diff_pairs 6쌍의 실제 단위.
- **의존.** C3-0, 형제 계획의 택소노미 1.2(시험 대역으로 먼저 짓는다). **크기.** 7시간.

### C3-6 거르기 분류

- **목적.** 훑기 뒤에 셀마다 3.2 의 규칙으로 거르거나(`na_irrelevant`), 표본으로 끝까지 판정하거나, 검토로 보낸다.
- **파일·닻.** `app/review_runner.py::_Session.run`(`self._sweep()` 바로 뒤에 `self._classify(cells)`), `_Session._classify`(새 — 강제 사유 · `relevance.code_signal` · `self.sweep['units']` · 다른 머리의 `sweep_json.handoffs` · Tier A 범위 셀 닫힘 · 넓힘 상태), `app/review_cells.py`(새 `filter_cell(...)` — `running → na_irrelevant`, `route`·`route_json`·`basis='filtered'`·`finished_at`, 선점 대조), `app/review_verify.py::sample_score('filter_audit', …)`, `create_review_job` 의 `knobs`, `app/config.py`(손잡이 셋과 `Knob(kind="choice")`).
- **계약.** 3.1 · 3.2 · 3.11. 거른 셀은 그 세션의 `live()` 에서 빠져 아무 호출도 받지 않는다. 표본으로 뽑힌 셀은 `route='audit'` 로 보통 셀과 똑같이 돈다. `filter='shadow'` 면 9번이 참이어도 검토로 보내고 `sample_json.shadow` 만 적는다.
- **수용 기준.** 3.2 의 열 줄 각각 — 1순위·전역 단위·카드 0장·결측 블록 없는 입력 결손·넓힌 영역·넘김·Tier A 대기 셀이 하나도 걸러지지 않는다. 결측 블록을 받은 판(`cr-sweep-2`)의 답이면 입력 결손 전문가의 셀도 두 신호 규칙으로 걸러진다. 훑기 `maybe`·`stamp`·`error`·답 없음·훑기 실패, 코드 `unknown` 이면 검토다. 걸러진 셀의 `route_json` 에 두 신호와 규칙·판 표지가 있다. 같은 원장 · 같은 손잡이면 다시 돌려도 같은 셀이 걸러지고 같은 셀이 표본이 된다(재기동 포함). 표본 비율 0 이면 표본이 없고(하한은 C3-7), 100 이면 아무것도 걸러지지 않는다. M2 잡(`filter='off'`)은 종전과 바이트가 같은 원장이다.
- **시험.** 새 `tests/test_review_filter.py`(가짜 엔진의 훑기 답을 단위마다 정해 주는 스위치를 `fake_review_engine.py` 에 더한다 — 그 답 모양은 엔진 계약 예제 `llm_transcript_sweep_*.txt` 를 실제 엔진이 낸 것과 같다), `tests/test_review_loop.py`.
- **의존.** C3-5, C3-2(입력 결손 강제). **크기.** 8시간.

### C3-7 표본 재검토 · 대표 그림자 · 넓힘 · 보충 표본

- **목적.** 거른 셀의 놓침을 재고, 놓침이 나오면 그 영역의 거르기를 거두며, 그 비율을 남긴다.
- **파일·닻.** `app/review_verify.py`(새 `audit_outcome(effective, offcard_rows) -> 'risk_miss'|'relevance_miss'|'undetermined'|'kept'`), `app/review_runner.py::_Session._settle`(표본·그림자 셀의 결과를 `sample_json` 에, `risk_miss` 면 `widen`), `app/review_cells.py`(새 `reopen_filtered(store, target_key, *, domain=None, unit_id=None, agents=None, via, run_id)` — `na_irrelevant → pending`, `reopened_n+1`, 머리 `_reopen`; 새 `widened_domains(store, target_key)`·`filter_off(store, target_key)` — 원장에서 유도), `ReviewLoop._complete_or_phase`(completed 갈래 앞에 `audit_topup(store, job)` — 3.4 의 보충 표본), `_Session._sweep`(넘김 `h` 줄을 쓴 뒤 늦은 넘김 다시 열기), `app/audit.py::binom_upper`(그대로 씀).
- **계약.** 3.4.
- **수용 기준.** 표본 셀이 `risk_miss` 면 그 영역의 거른 셀이 전부 다시 열리고 이후 그 영역은 거르지 않으며, 셋째 영역에서 대상 전체 거르기가 꺼진다. 그림자 셀의 `risk_miss` 도 같다. 잡 끝 보충 표본이 `n_audit = max(ceil(5% N), min(N, 59))` 와 영역당 1건을 채운 뒤에야 잡이 `completed` 다(채울 셀이 그 잡 범위 밖이면 채우지 못한 수를 진행판·`closure_cells.filtered.audit.floor_met=false` 로 낸다). 다시 열린 셀이 돌고 그 전문가가 다시 마감되면 보고서 `revision` 이 오른다. 넓힘 상태는 재기동 뒤에도 같다(저장 없이 유도). 결과 넷의 분류가 X1-13 표와 같다(`applies='unknown'` 뿐인 셀은 `kept` 가 아니라 `undetermined`).
- **시험.** `tests/test_review_filter.py`(가짜 엔진이 표본 셀 하나에 FAIL 을 내게 하는 스위치), `tests/test_review_verify.py`(`audit_outcome` 결정표), `tests/test_review_loop.py`(재기동 뒤 넓힘 유지).
- **의존.** C3-6. 다시 마감 뒤 등록부 정리는 형제 계획의 `registry.merge(prune=True)`(그 전에는 M2 그대로 병합하지 않으므로 해가 없다). **크기.** 10시간.

### C3-8 보이기 — 셀 격자 · 진행판 · 보고서 · 품질(`WP5b C10`) · 완결 몫

- **목적.** 거름·표본·넓힘·입력 결손·처분이 웹·Claude·보고서·완결 판정에 숫자와 까닭으로 보인다(D-33 ④).
- **파일·닻.** `app/routes.py`(`CELL_BRIEF_COLUMNS` 에 `route`·`route_forced`·`basis` 와 `filter_reason`(route_json 에서 한 줄로 — 코드 신호 관련 영역 · 훑기 why 앞 80자), `cells_payload` 에 `route=` 거름, `review_payload` 에 `filter`·`noinput`·`dispositions`), `app/review_cells.py`(새 `closure_cells` · `review_invariants` 판 올림 · `review_summary` 의 `by_basis` 에 `noinput`·`filtered`·`search_only`), `app/expert_report.py`(`_scope_section` — 거른 단위를 '보지 못한 것' 이 아니라 따로 `filtered[]`(까닭)로, `_head_section` 에 거름·표본 수, `REPORT_REV` 올림), `app/review_quality.py`(거르기 칸 · 입력 결손 칸 · 뒤집힘 모집단 둘), `app/assets/review-quality.v1.json`(`rq-2` — `filter.audit.risk_miss: {upper_max: 0.05}`, `min_n 59`, `flips.order` 의 모집단을 보정용으로), `app/entry.py::_cells_answer`(`facts.filter`·`facts.failed_cells{n, by_code}`·`facts.no_input` — 목록이 아니라 셈).
- **계약.** 3.10. 진행판 `review.filter = {mode, would_filter, filtered, audited, audit{risk_miss, relevance_miss, undetermined, kept, upper95}, shadow{…}, widened[], off, saved_calls_est}`. 품질 블록 문면 한 줄 예 — `[거름] 칸 2,992 거름(거를 수 있던 3,150 중) · 표본 158 걸림 0(95% 상한 1.9%) · 대표 그림자 120 걸림 0 · 넓힌 영역 없음`. 숨기지 않는 규칙 여섯(WP5b 3.11.3)을 지킨다 — 표본 미달은 '표본 수 미달(n=…)'.
- **수용 기준.** 격자 · 진행판 · 보고서 · 품질 · `closure_cells` 다섯이 같은 수다(한 원장에서 다섯을 뽑아 견준다). 거른 셀마다 까닭 한 줄이 보고서 표에 있다. 품질 문면의 수 == json 의 수, 문면 린터 위반 0. 옛 타깃은 한 줄. 판정 행·셀이 없는 영역도 표에 0 으로 나온다(빼지 않는다).
- **시험.** `tests/test_review_quality.py`·`tests/test_expert_report.py`·`tests/test_review_routes.py`·`tests/test_review_mcp.py`. 원장은 C3-6·C3-7 의 루프가 만든 것.
- **의존.** C3-3 · C3-4 · C3-7. **크기.** 9시간.

### C3-9 이중 판정은 걸린 카드에만 · 대표는 보정용 전량

- **목적.** 모든 카드는 한 번 판정되고, 걸린 카드만 두 번 이상 판정된다(D-33). 걸림 없음 → 걸림 뒤집힘은 1순위의 전량 이중 판정으로 계속 잰다.
- **파일·닻.** `app/review_verify.py`(새 `dual_plan_flagged(fwd_request, flagged_aliases) -> {rev, solo, reason}` — `reason ∈ dual · single_flag · none_flagged · same_body`), `app/review_runner.py::_Session.run`(rev 고리 — `knobs.dual` 과 1순위 여부로 갈래), `_Cell.dual_decks → dual_aliases`, `_Session._solo_set`(별칭 기준), `create_review_job` 의 `knobs`, `app/review_quality.py`(`flips.order` 를 보정 모집단으로, 새 `flips.flagged_pos_neg` — 걸린 fwd 가 rev·solo 에서 풀린 비율).
- **계약.** 3.5.
- **수용 기준.** `flagged` 에서 걸림 0 인 묶음은 rev 0회, 걸림 하나면 rev 0회·solo 1회, 둘 이상이면 그 별칭만 실은 rev 1회와 solo 각 1회. 안 걸린 카드가 solo 로 새지 않는다. 1순위 셀은 묶음 전체 rev. `all` 은 M2 와 호출 원장이 같다. M2 잡을 다시 이어도 `all` 로 돈다. 엔진의 요청 검증기(C7 길 — 형제 리포 서브프로세스)가 걸린 별칭만 실은 rev 본문을 422 없이 받는다.
- **시험.** `tests/test_review_verify.py`·`tests/test_review_loop.py`(가짜 엔진의 걸림 스위치 — 카드 0·1·3장 걸림)·`tests/test_card_review_request_contract.py`.
- **의존.** C3-0. **크기.** 6시간.

### C3-10 호출 추정 · 동의 · 상한(`WP5a R7` 의 상한·동의) · 동시 8

- **목적.** 전원 잡이 추정의 높은 끝(101,238회) 때문에 거절되지 않게 하고, 동의는 현실에 가까운 수로 받는다.
- **파일·닻.** `app/review_runner.py`(`CALLS_PER_CELL`·`SWEEP_CALLS_PER_EXPERT`·`calls_estimate`·`create_review_job` 의 문턱 두 줄·`credential_note` 의 소요 셈), `JobProgress`(묶음 단계가 끝나면 실제 묶음 수로 다시 센 `calls_estimate_live` — 보이기만 한다), `app/config.py`(`HWAXRISK_REVIEW_CONCURRENCY` 기본 8), `.portal/manifest.yaml` 설명.
- **계약.** `calls_estimate(cells_by_kind, experts, *, k, dual, filter) -> {low, expected, high, basis}`.
  - `expected`(거르기 없음 가정) = 일반 셀 × (D + 0.1 빠진 카드 + rev + 0.1 solo + 1.05 카드 밖) + 입력 결손 셀 × 1.05 + 1순위 보정 rev(1순위 셀 × D) + 훑기(카드 있는 전문가 수). D = ceil(12.9 / k)(점검 카드 평균 12.9 — 03-cards, 평균의 올림이라 보수 쪽이다), rev = `flagged` 면 0.05, `all` 이면 D. k 는 그 박스의 마지막 `limits.verdict.k`(전문가 머리 `plan_json` 에 얼린 값 가운데 최신)이고 없으면 8.
  - `low` = 거를 수 있는 셀의 70% 가 걸러진다는 가정, `high` = 지금 식(셀당 14).
  - 동의(`HWAXRISK_REVIEW_CONSENT_CALLS`)와 거절(`HWAXRISK_REVIEW_MAX_CALLS`)은 `expected` 와 견준다(열린 물음 a-11). 응답 `basis` 에 가정(k·셀당 수·호출 5분)을 문장으로 싣는다.
  - 도는 중의 예산 보류는 두지 않는다(WP5a cuts 4 — 셀마다의 `call_cap` 이 끝없는 되묻기의 그물이다).
- **수용 기준.** 359명 × 20단위(가짜 단위, k = 8)에서 `expected` 가 약 20,000(4,980 × 3.3 + 2,200 × 1.05 + 1순위 360 + 훑기 356)으로 30,000 밑이고 잡이 선다(동의 필요). `dual=all` 이면 rev 몫이 D 로 늘어난 값이 나온다. 응답 `basis` 의 문장이 쓴 가정(k · 셀당 수)과 같다. 동시 8 에서 앱 워커가 서버 limit(가짜 `/health` 4)를 넘겨 뜨지 않는다.
- **시험.** `tests/test_review_routes.py`·`tests/test_review_loop.py`(서버 limit 4·8 두 경우).
- **의존.** C3-6 · C3-9. **크기.** 5시간.

### C3-11 359명 규모

- **목적.** 전원 · 셀 7천여 개에서 루프·진행판·MCP 가 막히거나 넘치지 않는다.
- **파일·닻.** `ReviewLoop._complete_or_phase`·`_spawn`(단계를 잡 단위가 아니라 전문가 단위로 — 묶음이 `ok·empty` 인 전문가는 남이 묶음을 다시 받는 동안에도 검토로 집힌다. 집는 목적 순서는 `pack → review → finalize`, M2.md 8절의 위험 해소), `review_cells.expert_tally`(SQL 에서 전문가로 거른다), `JobProgress`(품질 훅 간격을 계산 시간에 맞춘다 — `max(60, 30 × 지난 계산 초)`), `app/mcp_server.py`(`_fit_rows`·`_fit_list` 를 새 응답에도), 새 `tests/rr/test_scale_359.py`.
- **수용 기준.** 합성 로스터 359명(영역 15 · 실제 크기 비율 · 회로 110 · 카드 0장 3)× 단위 20 의 원장(가짜 엔진으로 일부를 돌려 만든 것)에서 — `plan_cells` 1초 안, `coverage` 의 `review` 0.5초 안, `closure_cells` 0.5초 안, `review_quality.compute` 2초 안(넘으면 간격이 늘어난다는 것을 본다). MCP 응답 전부(`risk_get_coverage` 기본·`order_offset`·`seat_offset` · `risk_next_step` · `risk_get_cells` · `risk_job_action(retry_failed)` · `risk_get_expert_report` 각 part)의 와이어 글자가 25,000 안이고 쪽을 이으면 전부다(R3B-1). 한 전문가의 팩이 502 를 여섯 번 내는 동안 다른 전문가의 셀이 돈다.
- **시험.** `tests/rr/test_scale_359.py`(`RR_FULL=1` 일 때만 7,180셀 전부 — 기본은 359 × 3단위로 같은 단언), `tests/test_review_loop.py`.
- **의존.** C3-3 · C3-6 · C3-8. **크기.** 7시간.

### C3-12 근거 꾸러미 실호출(B 층, `WP2 7`)

- **목적.** 캡처에 없던 지금 상태 둘(재질 물성 비교 · 해석 보고서 비교)을 단위 근거에 더하되, 같은 단위를 본 전문가가 모두 같은 근거를 보게 한다.
- **파일·닻.** 새 `app/unit_live.py`(첫 줄 한국어 주석 — `plan_calls(store, target_key)`·`ensure(store, settings, target_key, credential, *, deadline_s)`·`lines_for(store, target_key, unit_id)`), `app/field_source.py`(얇은 감싸개 — 응답에 `error` 키가 있으면 실패로 적고 재사용하지 않는다, 재사용 키에 자격 종류를 넣는다 — W2-03 (d)), `app/units.py::review_payload`(근거 줄 뒤에 B 층 줄), `app/review_cells.py::cell_input_hash`(`live_sha` 인자 — 값이 있을 때만 지문에 든다, 없으면 M2 식 그대로), `app/narrative.py::review_scope`(`call_ids` 에 B 층 `b-…`), `ReviewLoop`(잡 단계 `live` 를 `pack` 앞에 — 대상마다 워커 하나), 게이트웨이 `tools/list` 의 `inputSchema`.
- **계약.**
  - 계획(결정적) — ① 두 스냅샷 IR 의 `results.report_ids` 가 다 있으면 `compare_reports` 한 번(앞 두 건 — `rr_targets.report_ids_json` 은 쓰지 않는다, W2-03 (a)) → 결과 변화 줄(`param.<metric>`·`result.*`)이 있는 단위에 붙인다. ② 재질 변화 줄의 (전, 후) 쌍마다 `compare_materials(materials=[전, 후])` 한 번(타깃 안에서 같은 쌍은 재사용 — `get_material` 폴백은 없다, W2-03 (b)) → 그 쌍이 든 단위에 붙인다.
  - 인자 키는 `tools/list` 의 스키마와 대조하고 모르는 키면 계획에서 빼고 `live_schema_mismatch` 로 적는다(W2-03 (c)).
  - 자격은 그 잡의 사용자 PAT 하나다(사용자 결정 3 — 서비스 계정으로 내려가지 않는다. WP2 3.8.2 의 서비스 강등은 쓰지 않는다).
  - 실패 — 내용 탓(오류 본문 · 스키마 · 403 · 모르는 도구)은 `partial` 로 얼린다. 인프라 탓(연결 · 5xx · 시간 초과)은 얼리지 않고 `attempts+1`·`not_before`(60초부터 두 배, 6번) 뒤 `live_infra_exhausted` 로 `partial`(W2-04 (c)). 자격 만료는 잡 `credential` 보류(M2 그대로).
  - 쓰기는 비교 후 쓰기(`… WHERE status IS NULL`, 바뀐 행 0 이면 버린다 — W2-04 (a)).
  - 셀이 하나라도 이미 돈(`pending` 이 아닌) 단위는 `skipped` 로 얼린다 — M2 파일럿 대상의 셀 지문이 바뀌어 처음부터 도는 것을 막는다.
  - 응답은 원문을 붓지 않는다 — 도구별 렌더러가 수치·id 칸만 줄로 만들고 문자열은 `sanitize_source_text(…, limit=0)` 로 «» 안에 둔다. 렌더러가 모르는 모양은 줄마다 «…».
  - 단위의 셀은 그 단위의 `rr_unit_live.status` 가 서기 전에는 시작하지 않는다(`status` 가 NULL 인 단위의 셀은 집지 않는다).
- **수용 기준.** 같은 대상을 두 잡이 동시에 얼려도 단위마다 한 번만 쓴다. 오류 본문은 성공으로 굳지 않는다. 인프라 실패는 얼리지 않고 다시 한다. 셀이 이미 돈 단위는 `skipped` 이고 그 셀의 `input_hash` 가 그대로다. B 층 줄을 인용한 finding 이 dangling 이 아니다(P-07). 서비스 PAT 가 어떤 요청에도 실리지 않는다. 손잡이 0 이면 전 단위 `none` 이고 호출 0 이다.
- **시험.** 새 `tests/test_unit_live.py`(`httpx.MockTransport` 의 가짜 게이트웨이 — 오류 본문 · 스키마 어긋남 · 5xx 여섯 번 · 403 · 지연), `tests/test_review_loop.py`(`live` 단계 뒤 셀 시작), `tests/test_narrative_cards.py`.
- **의존.** C3-1. 게이트웨이에 두 도구가 사용자 PAT 시야로 뜨는지(`m3-engine-ops.md`). **크기.** 14시간.

### C3-13 보안 시험의 리스크 앱 몫(`WP5b C12`)

- **목적.** 새 경로·도구·데이터 길이 남의 과제를 흘리거나 카드 원문을 내보내거나 주입 문구를 판정으로 바꾸지 않는다.
- **파일.** 새 `tests/rr/test_security_visibility.py`(경로 목록은 라우터에서 뽑는다 — 새 경로를 넣고 시험을 잊지 않게. 남의 대상에 retry·skip·undefer·cells·experts 가 404, MCP `risk_job_action(retry_failed)` 가 범위 밖에 `not_visible`), 새 `tests/rr/test_security_canary.py`(합성 카드의 인용되지 않는 절에 심은 `CANARY-<hex>` 가 한 바퀴 — 거르기 · 표본 · `noinput` · 처분 · 다시 마감 — 뒤 모든 REST·MCP 응답·반출 파일·로그·`rr_audit` 에 없다. 있어도 되는 곳은 `rr_card_packs` 와 LLM 프롬프트뿐), 새 `tests/rr/test_injection.py`(① `noinput` 의 q1·q2 `why`·`item` 에 심은 주입이 보고서·finding·다음 프롬프트(`extra.known`)에서 «» 안에만 있다, ② B 층 응답의 재질명에 심은 주입이 근거 줄에서 자리표시자이고 큐레이션 큐에 한 줄이 생긴다, ③ 훑기 `h` 줄의 `why` 가 늦은 넘김 기록과 보고서에서 «» 안에만 있다, ④ `route_json.sweep.why` 가 거름 까닭 한 줄로 갈 때 린터를 지난다).
- **수용 기준.** 위 넷 모두 붉었다 초록이 되는 것을 사본 변이로 본다(위생 한 줄을 지운 사본에서 붉다 — 사본만, 끝나면 `git diff` 를 줄 단위로 대조한다).
- **의존.** C3-3 · C3-4 · C3-12. **크기.** 6시간.

### C3-14 대역 일치와 계약 예제(`WP5b C14`)

- **목적.** 가짜 엔진의 `noinput` 과 걸린 카드 rev 가 실제 엔진의 모양과 같다.
- **파일.** `tests/synth/fake_review_engine.py`, `tests/test_fake_review_engine.py`(응답 키 집합 == 엔진 계약 예제), `tests/test_card_review_request_contract.py`(앱이 조립한 `noinput`·`rev(걸린 별칭만)` 본문이 엔진 검증기를 지난다 — 형제 리포가 곁에 있는데 못 읽으면 skip 이 아니라 실패, P-22), 엔진 쪽 계약 예제 `run_noinput_*.sse`·`result_noinput.json`·`llm_transcript_noinput_*.txt`(만드는 것은 `m3-engine-ops.md`).
- **수용 기준.** 가짜 엔진에서 `noinput` 의 `q2` 줄을 빼면 대역 일치 시험이 붉다.
- **의존.** C3-3 · C3-9, 엔진의 계약 예제. **크기.** 3시간.

### C3-15 문서 · 업데이트 이력 · 매니페스트 · HEAXHub 사본(`WP2 12` · `WP5b C16` · `WP5a H1`)

- **파일.** `HWAXPortal/docs/design-risk-review/plan.md`(§6.3 보류 · §6.4.1 Tier · §6.8.2 전이 — 보류는 이제 풀린다, Tier 는 범위가 아니라 순서), `HWAXPortal/backend/config/changelog.yaml`(사용자 체감과 기술 변경 전부 — 큰따옴표, 날짜는 KST, 분류 '기술' 포함), `HWAXRisk/README.md`(손잡이 표), `HWAXRisk/.portal/manifest.yaml` 설명(새 흐름 한 줄 · 처분 · 거르기 · `knobs.env` 키 넷 — `launch.env` 는 그대로), `HEAXHub/integrations/hwax-risk/.portal/manifest.yaml`(같은 날 복사 — 두 파일의 `diff` 가 빈다, 지금 빈 것을 확인했다), `HWAXRisk/context-notes.md`, 포털 `docs/risk-review-redesign/server-setup-m3.md` 의 셀 몫(처분 명령 · 거르기 손잡이 · 확인할 출력 문구 — 줄 번호 대신 문구), `docs/risk-review-redesign/checklist.md`·`context-notes.md`.
- **수용 기준.** `tests/test_manifest.py`·포털 `test_changelog.py`·`test_cluster_naming.py` 통과. 절차서의 명령을 dev 에서 하나씩 돌려 출력과 맞춘다. 커밋 ↔ 이력 항목 대응표에 빠짐 0.
- **의존.** 전부. **크기.** 5시간.

### C3-16 dev 리허설 · v5 확정 · push

- **차례.**
  1. 리스크 앱 시험 전체와 형제 리포 계약 파일 해시 가드.
  2. 리허설 하네스 `tests/synth/rehearsal_d.py` 를 넓힌 `rehearsal_m3.py` — 빈 포트·스크래치 디렉터리에 가짜 LLM(1M 창, `noinput` 대본 포함)·임시 에이전트 서버·임시 포털·리스크 앱. 합성 로스터 359명(영역 15, 회로 110, 카드 0장 3)× 단위 20 가운데 영역마다 3명 × 단위 6 으로 셀 약 270개를 끝까지 — 거름·표본·넓힘(가짜 LLM 이 표본 하나에 FAIL)·입력 결손 넷 결과·처분(다시·넘김)·재기동 두 번·서버 limit 8→4(심의 가짜 하나 띄움). 전원 7,180셀은 가짜 엔진 통합 시험(C3-11)이 본다. 하네스는 절대경로를 쓰고 `pkill -f` 를 쓰지 않는다. 실 저장소 무접촉(파일 크기·mtime·fd)을 M2 단계 D 처럼 단언한다.
  3. 리허설이 표 모양을 바꾸라고 하면 v5 를 고친다(형제 계획과 같이) → `PUSHED_DDL_SHA256[5]` 를 굳힌다.
  4. push → hwax-risk SIF → dev 인스턴스 교체(`apptainer instance list` 출력에서 이름을 확인하고 내리며, 다시 올리는 것은 허브에 맡긴다) → 이행 사본 `pre-migrate-v4-*` 확인 → 게이트웨이 `tools/list` 에서 `risk_job_action` 의 새 인자를 실제로 본다(`backend/scripts/rr_gateway_check.py`).
- **수용 기준.** 6절 표의 증거가 모인다. 셀당 호출 수 실측(가짜 LLM)이 10절 표의 모형과 같은 자릿수다.
- **의존.** C3-0~C3-15, 형제 계획 둘의 dev 배포. **크기.** 9시간(사용자 시간·cae00 벽시계 제외).

## 5. 짓는 순서

| 단계 | 갈래 A(전원·입력 결손·처분) | 갈래 B(거르기) | 갈래 C(호출) | 갈래 D(B 층) |
|---|---|---|---|---|
| 1 | C3-0 → C3-2 | C3-5(시험 대역으로) | C3-9 | C3-1(형제 블록 뒤) |
| 2 | C3-3 | C3-6 | — | C3-12 |
| 3 | C3-4 | C3-7 | C3-10 | — |
| 4 | C3-8 · C3-11 · C3-13 · C3-14 | | | |
| 5 | C3-15 → C3-16 | | | |

- 갈래끼리 파일이 겹치는 곳은 `review_runner._Session.run`(C3-3 의 입력 결손 갈래 · C3-6 의 `_classify` · C3-9 의 rev 고리)이다. 같은 함수의 다른 줄이라 C3-6 을 먼저 합치고 나머지를 그 위에 rebase 한다.
- 각 단계 끝에 반대 검토 한 라운드를 돌린다. 검토 에이전트의 변이 실험은 사본에서만 하고, 끝나면 `git diff` 를 줄 단위로 대조한다(탐침이 남은 사고 두 번).

## 6. 나갈 기준에 이 꾸러미가 대는 것

| M3 나갈 기준 | 이 꾸러미의 걸음 | 보는 곳 |
|---|---|---|
| 1 모든 셀이 종결이거나 사유 있는 `failed`, 수와 사유가 종합 보고서 머리에 | C3-3 · C3-4 · C3-6 · C3-7 · C3-8(`closure_cells`) | `closure_cells.by_state` 의 `pending + running == 0` 과 `invariants == []`, `failed.by_code`·`skipped.by_note`·`filtered`·`no_input` 이 형제 계획의 보고서 머리에 그대로 |
| 2 전문가 보고서 359편 | C3-3(입력 결손 보고서) · C3-4(넘김 뒤 다시 마감, 묶음 실패 전문가도) · C3-7(다시 열린 뒤 다시 마감) · C3-11 | 머리 359행이 전부 `ready·partial`(`blocked` 0)이고 보고서가 있다 |
| 4 영역 요약·종합의 수 == 완결 판정 | C3-8 | 다섯 곳이 같은 수(C3-8 수용 기준) |
| 5 완결 표기의 잔여 — 입력 결손·실패·사람 넘김 | C3-3 · C3-4 · C3-8 | 3.10 의 잔여 낱말과 3.9 의 사유 |
| 6 update-all 비우기 · 챗 지연 2배 안 | C3-10(동시 8 · 서버 limit 따르기) — 비우기·지연 측정은 `m3-engine-ops.md` | 진행판 `waiting{reason:'draining'}` |
| 359명 규모 · MCP 와이어 25,000자 | C3-11 | `tests/rr/test_scale_359.py` |

## 7. 형제 계획에 기대는 곳

| 상대 | 무엇 | 없으면 |
|---|---|---|
| `m3-synthesis.md` | v5 블록 파일과 그 확정(C3-1 · C3-16) | `rr_unit_live` 를 넣을 자리가 없다 — C3-12 가 선다 |
| `m3-synthesis.md` | `mech-owners.v1.json` 과 `taxonomy.mech_owners`·`domains_for`·`mech_owners_meta`(3.3 — 그쪽 3.2 의 이름), 메커니즘 1.2 의 코드 목록, '15영역이 다 닿는다' 단언, 승인 문 | C3-5 가 시험 대역에서 못 나온다 — 코드 신호가 `unknown` 이라 거르기가 사실상 꺼진 채 돈다 |
| `m3-synthesis.md` | 사용자가 배정표를 훑을 때 이 문서의 변경 → 메커니즘 표 · 역할 표도 같이(열린 물음 b-1) | 코드 신호의 질이 검증되지 않은 채 돈다 |
| `m3-synthesis.md` | 완결 판정이 `closure_cells` 와 3.9 의 사유를 읽는다. `abstain(filtered:·no_input:)`·`skipped(cells_skipped:)` 를 깊이·strong 분모에서 뺀다(X1-02). WP4 3.4 의 `rr_cell_audits`·`plan_audit` 을 만들지 않는다(표본 재검토는 C3-7 이 맡는다) | 거짓 완결 · 두 벌의 표본 재검토 |
| `m3-synthesis.md` | `registry.merge(prune=True)` — 다시 마감이 지운 finding 의 등록부 행 정리(P-13) | 처분·넓힘 뒤 유령 클러스터 |
| `m3-synthesis.md` | 사슬(`WP4 7`)이 잡 `completed` 뒤에 잇는다 — C3-7 의 보충 표본은 `completed` **앞**이다. 같은 함수(`_complete_or_phase`)를 둘이 고친다 | 보충 표본 전에 쟁점·종합이 시작된다 |
| `m3-synthesis.md` | M2 결정 #25(카드 대조 finding 의 메커니즘)와 `noinput` q1 의 `mech` 를 같은 규칙으로 | `process.unclassified` 로 접힌다 |
| `m3-synthesis.md` | MCP 도구 수 — 이 문서는 새 도구를 만들지 않는다(`risk_job_action` 인자만). M3 끝 31종 그대로 | — |
| `m3-engine-ops.md` | 엔진 `noinput`(계약 2 · E3-2 — `q1`·`q2`·`more`, `items_max`, `limits.kinds`·`cell_kinds`·`prompt_rev`·`runnable`)과 계약 예제 | 입력 결손 셀이 `agent_outdated` 로 서서 잡이 끝나지 않는다(범위에서 빼고 나머지는 돈다) |
| `m3-engine-ops.md` | 훑기의 결측 블록(계약 6 — `extra.missing`, `cr-sweep-2`) | 입력 결손 전문가의 셀을 거르지 않는다(3.2 의 5번) — 호출 약 +1,500 |
| `m3-engine-ops.md` | 단독 재질의·`q1` 줄의 `mech`(계약 5)와 그 판 올림을 살아 있는 검토 잡이 없을 때 배포 | 판이 오르는 순간 `pending` 셀이 처음부터 돈다(C3-3 의 `prompt_key` 가 범위를 좁힌다) |
| `m3-engine-ops.md` 가 이 문서에 바라는 것 | `prompt_key` 를 셀이 부르는 종류만으로(C3-3) · 앱 동시 수 기본 8(C3-10 — 그쪽 사슬 시험이 xfail 에서 풀린다) · 끝난 M2 파일럿 셀을 다시 돌리는 REST(C3-4 의 `force` — 그쪽 A12) | — |
| `m3-engine-ops.md` | 관문 기본값 8 · 심의 중 `conc // 2`, `/health.card_review.limit` 모양 그대로 | 앱 8 이 서버 4 에 묶인다 |
| `m3-engine-ops.md` | M0-b 실측 뒤 `CARD_REVIEW_K`(≤ `k_out`) | 묶음이 8장에 머문다(호출 약간 많을 뿐) |
| `m3-engine-ops.md` | `WP3a 8` 긴 문서 검색(`extra.search`·`meta.search`) — 앱 쪽 두 줄(카드 0장 전문가에 `search` 를 싣고 `basis='search_only'`)은 C3-3 과 같은 커밋에 넣는다 | 카드 0장 셋이 `role_only` 그대로 |
| `m3-engine-ops.md` | 챗 첫 응답 지연을 재고 2배를 넘으면 알린다(D-34) · `/drain` | 동시 8 의 영향을 모른다 |
| `m3-engine-ops.md` | 게이트웨이가 `compare_reports`·`compare_materials` 를 사용자 PAT 시야로 띄운다 | B 층이 `partial` 로만 언다 |
| `m3-engine-ops.md` | B2(무작위 10% rev)를 사용자가 고르면 앱은 `HWAXRISK_REVIEW_DUAL_NEG_PCT` 하나 | 걸림 없는 셀의 거짓 '문제없음' 은 1순위 보정으로만 잰다 |

## 8. 위험

| 위험 | 대비 |
|---|---|
| 거르는 비율 φ 를 모른다. 메커니즘 → 영역 표가 넓으면(메커니즘 하나가 영역 여럿) 코드 신호가 거의 늘 '관련' 이라 거르기가 일어나지 않는다 | 대표 그림자로 첫 잡의 Tier A 에서 φ 와 놓침을 공짜로 잰다. `filter=shadow` 로 대상 전체를 재고 켤 수도 있다. 절감 폭은 10절 표의 범위로만 말한다 |
| 반대로 표가 좁으면 훑기 하나가 거르기를 정한다 | 15영역이 다 닿는다는 단언(3.3). 대표 그림자·표본·넓힘 |
| 넓힘이 늦게 오면 마감한 전문가가 다시 열려 보고서 판이 계속 오른다 | Tier A 가 먼저 돌고(검토 순서) 그동안 B·C 는 거르지 않는다(3.2 의 8번). 넓힘은 영역 단위, 셋째에서 전체 끔 |
| 걸린 카드만 이중 판정하면 걸림 없음 → 걸림(놓침) 측정이 사라진다 | 1순위 셀 전량 이중 판정(3.5) — 약 +225 호출 |
| 입력 결손 전문가 110명이 대상마다 2,200셀 × 1호출을 쓴다 | 엔진의 훑기 결측 블록(`cr-sweep-2`)이 들어오면 두 신호 규칙으로 걸러진다(a-2). 그 전의 답으로는 거르지 않는다(X1-17) |
| 배정표 승인이 늦으면 거르기가 하나도 일어나지 않는다(승인 문) | 그동안은 10절 A(약 15,340회)다. 승인 칸 하나만 고친 커밋이 연다 — 표를 훑는 일정을 실주행 앞에 둔다(b-1) |
| 엔진 `noinput` 이 늦다 | 입력 결손 셀만 `agent_outdated` 로 서고 범위에서 빼면 나머지는 돈다. 완결은 잔여로 막힌다 |
| 사람이 같은 실패 셀을 되풀이해 다시 돌린다 | 셀당 호출 상한(`call_cap`)은 그대로, `reopened_n` 을 진행판에 보인다 |
| B 층 도구의 인자·이름·권한이 박스마다 다르다 | `tools/list` 스키마 대조, 실패는 `partial` 과 사유로 보인다. 첫 컷 후보다(열린 물음 a-10) |
| B 층 응답이 주입 통로가 된다 | 렌더러가 수치·id 만 뽑고 문자열은 «», 시험 C3-13 ② |
| 셀 지문에 `live_sha` 가 들어 M2 파일럿 대상이 처음부터 돈다 | 셀이 이미 돈 단위는 `skipped`, 값이 없으면 M2 식 그대로 |
| 같은 함수(`_Session.run`·`_complete_or_phase`)를 이 문서의 갈래 셋과 형제 계획이 고친다 | 5절의 합치는 순서 · 통합 가지 `m3` |
| 359명에서 진행판 품질 계산이 매 60초 원장 락을 몇 초 쥔다 | C3-11 의 시간 단언과 간격 조절 |
| 동시 8 이 챗을 민다 | 손잡이 하나(앱·엔진)로 박스에서 바로 낮춘다. 측정은 엔진 몫 |
| 처분 잡과 형제 계획의 후속 사슬이 같은 대상에서 겹친다 | 처분이 세우는 잡도 `mode='reviews'` 라 사슬은 그 잡이 `completed` 일 때 다시 잇는다(형제 계획의 '마감 범위 전원이 끝났을 때만' 규칙) |

## 9. 열린 물음

### (a) 계획에서 정한다 — 권고대로 간다

| # | 물음 | 권고 |
|---|---|---|
| a-1 | 거른 셀의 상태 이름 | DB 는 `na_irrelevant` 그대로, `route='filtered'`·`basis='filtered'`, 밖으로는 '거름'. C-18·WP3b·WP4·품질 폭포가 이미 그 이름이다 |
| a-2 | 입력 결손 전문가도 거르나 | 거른다 — 단 그 훑기가 결측 블록을 받은 판(`m3-engine-ops.md` 계약 6)의 답일 때만. 옛 판의 답이면 거르지 않는다(X1-17) |
| a-3 | 표본 5% 가 작은 대상·영역에서 0~몇 건이 될 때 | `max(5%, min(N, 59))` 와 영역당 1건. 59 는 완결의 '상한 5%' 를 댈 수 있는 최소 표본이다 |
| a-4 | '넓힌다' 의 단위 | 영역. 셋째 영역에서 대상 전체를 끈다. 넓힘은 원장에서 유도한다(저장하지 않는다) |
| a-5 | 놓침의 정의 | 결과 넷(3.4), 넓힘을 일으키는 것은 `risk_miss`, 상한은 `risk_miss` 와 `risk_miss + undetermined` 둘을 싣는다 |
| a-6 | 걸린 카드의 rev 를 어떻게 | 걸린 별칭이 둘 이상일 때만 그 별칭만 rev, 하나면 solo 가 두 번째 판정이다. 1순위는 전량(보정) |
| a-7 | Claude 의 처분 입구 | 새 도구를 만들지 않고 `risk_job_action` 에 `retry_failed`·`skip_failed` 와 `reason`·`filter` 를 더한다(도구 수 31 그대로) |
| a-8 | 보류를 언제 푸나 | `flow='cells'` 대상의 검토 잡을 만들 때 범위 안만. 패널 대상은 사람의 REST 로만 |
| a-9 | `rr_roster.input_gaps_json` | 넣지 않는다 — 계산값이 늘 같다 |
| a-10 | B 층을 M3 에 두나 | 둔다(PLAN M3). 도구 둘 · 사용자 PAT 만 · 단위마다 한 번 · 셀이 돈 단위는 `skipped`. 일정이 밀리면 가장 먼저 M4 로 뺀다(14시간) |
| a-11 | 동의·거절을 무엇과 견주나 | `expected`(거르기 없음 가정)와 견준다. 지금 식(`high`)은 전원에서 늘 거절이다 |
| a-12 | 전역 단위는 거르나 | 거르지 않는다(묶음 사이 조합 — 질량·공차 누적은 전원이 본다, WP2 3.9.1) |
| a-13 | 늦게 온 넘김(`h` 줄) | 이미 걸러진 그 (단위, 영역) 셀을 다시 연다 |
| a-14 | 단위 재빌드의 `force`·셀 비우기 | M3 에 넣지 않는다. 전원 실주행은 새 대상에서 한다 |
| a-15 | 형제 계획과 같은 리포를 어떻게 | 통합 가지 `m3` 와 꾸러미별 하위 가지, 날마다 rebase. v5 블록 파일은 `m3-synthesis` 가 쥔다 |
| a-16 | `noinput` 이 전부 `no` 이고 요청 0 인 셀 | `reviewed(basis='noinput', outcome='none')` — WP3b 3.7.4. X1-17 의 `na_irrelevant` 대안은 거름과 섞여 쓰지 않는다 |
| a-17 | 입력 결손만으로 본 전문가의 롤업 | `done_weak(input_gap:ecad_absent)` — 주 입력 없이 본 것이라 `done` 으로 올리지 않는다 |
| a-18 | 묶음 단계가 잡 전체를 붙드는 것(M2.md 8절) | 전문가별 단계로 바꾼다(C3-11) |
| a-19 | 처분 권한 | 잡을 세울 수 있는 editor(넘김도 같다). 잔여 확인(ack)은 형제 계획의 '소유자·관리자' 다 |
| a-20 | 거르기의 기본값 | `on`(D-33). 대표 그림자가 첫 놓침률을 대고, 첫 cae00 전원 실주행 전에 M2 파일럿 대상에서 `shadow` 로 한 번 재는 것을 절차서에 둔다. 승인 문(3.3)이 닫혀 있는 동안은 손잡이와 상관없이 거르지 않는다 |
| a-21 | 끝난 셀(`reviewed`)을 사람이 다시 돌리나 | 돌린다 — `cells/retry` 의 `force`(사유 필수). 엔진 판이 오른 뒤 M2 파일럿 셀을 새 판으로 다시 보는 길이다(`m3-engine-ops.md` A12) |
| a-22 | 판정과 카드 밖을 한 호출로 합치나(D-33 어림에 닿는 유일한 길) | M3 에서는 합치지 않는다 — `m3-engine-ops.md` A1 과 같다. 보강한 M0-b 의 '합친 팔' 결과로 M4 에서 정한다. 그 사이 어림은 10절이다 |

### (b) 사용자가 정한다

| # | 물음 | 권고 |
|---|---|---|
| b-1 | 메커니즘 → 영역 배정표를 훑을 때 이 문서의 **변경 → 메커니즘 표**와 **부품 역할 → 영역 표**도 같이 훑나 | 같이 훑는다. 거르기의 코드 신호는 세 표의 곱이라 하나만 보면 결과가 보이지 않는다. 초안에 '이 표로 거른 셀 수(대표 그림자 결과)' 를 붙여 보인다 |
| b-2 | D-33 의 어림(호출 3,000~5,000)을 고친다 — 지금 설계로는 거르기가 잘 들어도 약 6,400회, 가운데 값은 약 8,000~10,000회다(10절). 이 수로 전원 실주행 일정(동시 8 에서 3~4일)을 받아들이나 | 받아들인다. 더 줄이는 길(카드 밖을 판정에 합침, a-22)은 M0-b 와 M3 실측 뒤에 정한다 |
| b-3 | `m3-engine-ops.md` B2 — 걸림 없는 묶음의 무작위 10% rev 를 더하나(셀당 약 +0.1, 전원 약 +500회) | 첫 전원 실주행은 1순위 보정(전량 이중 판정)만으로 돌고, 보정의 '걸림 없음 → 걸림' 비율이 5% 를 넘으면 그 대상부터 10% 를 켠다. 같은 물음이 두 문서에 있으니 사용자 답 하나로 둘 다 정한다 |

## 10. 호출 수 어림 — 전과 후

가정 — 로스터 359명(입력 결손 110 · 그 밖 249), 검토 대상 단위 20, 셀 7,180(입력 결손 2,200 · 그 밖 4,980). 거르지 않는 그 밖 셀 — 1순위 9명 180 · 카드 0장 3명 60 · 전역 단위 1개 가정 237 = 477, 거를 수 있는 셀 약 4,500. 훑기는 카드가 있는 전문가마다 1회(1M 창 — 묶음 1 · 쪽 1) 356회.

셀당 호출(그 밖 검토 셀).

| | fwd | 빠진 카드 | rev | solo | 카드 밖 | 합 |
|---|---|---|---|---|---|---|
| M2 설정(리허설 실측 3.8 — 이를 나눈 것) | 1.25 | 0.1 | 1.25 | 0.15 | 1.05 | **3.8** |
| M3 `flagged` | 1.25 | 0.1 | 0.05 | 0.1 | 1.05 | **2.55 → 아래 셈은 2.5**(K 를 19 로 키우면 fwd 가 1.0 쪽으로, 2.3) |

입력 결손 셀은 `noinput` 1회 + 보충 0.05 = 1.05. 1순위 보정 rev 는 180셀 × 1.25 = 225.

| 판 | 검토 셀 | 거른 셀(끝) | 표본 | 호출 | 벽시계(호출 5분, 동시 8 · 심의 중 4) |
|---|---|---|---|---|---|
| 기준 — M2 설정으로 전원(이중 판정 전량 · 거르기 없음) | 7,180 | 0 | 0 | 7,180 × 3.8 + 356 ≈ **27,640** | 12.0일 · 24.0일 |
| A — 걸린 카드만 이중 판정, 거르기 끔 | 7,180 | 0 | 0 | 4,980 × 2.5 + 2,200 × 1.05 + 225 + 356 ≈ **15,340** | 6.7일 · 13.3일 |
| B — A + 거르기 φ = 0.3 | 5,898 | 1,282 | 68 | 3,698 × 2.5 + 2,310 + 225 + 356 ≈ **12,140** | 5.3일 · 10.5일 |
| C — A + 거르기 φ = 0.5 | 5,043 | 2,137 | 113 | 2,843 × 2.5 + 2,310 + 581 ≈ **10,000** | 4.3일 · 8.7일 |
| D — A + 거르기 φ = 0.7 | 4,188 | 2,992 | 158 | 1,988 × 2.5 + 2,310 + 581 ≈ **7,860** | 3.4일 · 6.8일 |
| E — D + 입력 결손 셀도 φ = 0.7(엔진의 훑기 결측 블록 뒤 — a-2) | 2,805 | 4,375 | 231 | 4,970 + 817 × 1.05 + 581 ≈ **6,410** | 2.8일 · 5.6일 |
| F — E + 카드 밖을 판정에 합침(a-22 — M3 에서는 안 한다) | 2,805 | 4,375 | 231 | 1,988 × 1.5 + 858 + 581 ≈ **4,420** | 1.9일 · 3.8일 |

- φ 는 '거를 수 있는 셀 가운데 두 신호가 다 무관인 비율' 이고 잰 적이 없다. PLAN 6절의 '훑기 무관 비율' 가정(0.3~0.5)에 코드 신호의 AND 가 더 깎는다. 입력 결손 셀도 엔진의 결측 블록이 들어오면 같은 규칙으로 걸러지므로(a-2), C(φ 0.5)와 E 사이 — 약 8,000~10,000회 — 를 가운데로, E 를 잘 된 경우로 본다. 배정표가 승인되기 전에는 A(15,340)다.
- B2(무작위 10% rev, b-3)를 켜면 검토 셀마다 약 +0.1회다(C 에서 약 +500).
- 표본은 `max(5% × 거를 셀, 59)`, 표본 셀은 2.5회다. 표본은 '검토 셀' 에 들어 있다.
- 호출 5분은 PLAN 6절의 가정이다. M0-b 가 잰다. 3배면 벽시계가 3배다.
- 기준이 D-33 의 '약 28,800' 과 맞는다(셀당 4 대 3.8). M2 의 `calls_estimate` 높은 끝(셀당 14)으로는 같은 범위가 101,238 회라 지금 코드가 거절한다(2절).

## 11. 크기

| 걸음 | 시간 |
|---|---|
| C3-0 시작 | 2 |
| C3-1 v5 몫 | 3 |
| C3-2 전원 포함 · 보류 해제 | 6 |
| C3-3 입력 결손 호출 · 셀 지문의 판 | 13 |
| C3-4 실패 셀 처분(끝난 셀 `force` 포함) · 롤업 | 11 |
| C3-5 코드 신호 | 7 |
| C3-6 거르기 분류 | 8 |
| C3-7 표본 · 그림자 · 넓힘 | 10 |
| C3-8 보이기 · 품질 · 완결 몫 | 9 |
| C3-9 이중 판정 걸린 것만 | 6 |
| C3-10 추정 · 동의 · 동시 8 | 5 |
| C3-11 359명 규모 | 7 |
| C3-12 B 층 실호출 | 14 |
| C3-13 보안 시험 | 6 |
| C3-14 대역 일치 | 3 |
| C3-15 문서 · 이력 · H1 | 5 |
| C3-16 리허설 · push | 9 |
| 반대 검토 라운드와 재작업(M2 의 비율 — 걸음 합의 약 15%) | 19 |
| **합** | **약 143** |

PLAN 8절의 M3 어림(80시간)은 세 꾸러미 전부의 값이다. 이 꾸러미만 그 1.8배다 — M2 가 110 → 230 으로 두 배였던 것과 같은 모양이다. 줄일 수 있는 것은 C3-12(14시간 — M4 로)와 C3-7 의 늦은 넘김 다시 열기(약 1.5시간)다.

## 12. 실측이 필요한 값

| 값 | 출하 기본 | 재는 곳 | 바꾸는 자리 |
|---|---|---|---|
| 거르는 비율 φ(두 신호 AND) | 모름 — 10절의 범위 | 첫 잡의 대표 그림자 · M2 파일럿 대상 `shadow` | 표 셋(b-1) |
| 표본 · 그림자의 놓침률 | 넓힘 셋째 영역에서 전체 끔 | 진행판 `review.filter` | `HWAXRISK_FILTER_AUDIT_PCT` · `WIDEN_ALL_AT` |
| 걸린 비율(양성) · 걸린 카드의 rev 비율 | 셀당 rev 0.1 가정 | 품질 '실측' | 3.5 |
| 걸린 fwd 가 solo·rev 에서 풀리는 비율 | 재기만 | 품질 `flips.flagged_pos_neg` | M4 의 단독 재질의 규칙 |
| 순서 뒤집힘(보정 모집단) | `flips.order` 10% 안 | 1순위 전량 이중 판정 | `rq-2` |
| 입력 결손 셀의 결과 분포(영향 · 요청 · 없음) | 재기만 | `closure_cells.no_input` | a-2 |
| B 층 성공률과 실패 사유 | 재기만 | `rr_unit_live.status`·`gaps_json` | a-10 |
| K(엔진) | 8(`k_out` 19 까지) | M0-b | 엔진 `CARD_REVIEW_K` |
| 셀당 호출 수(종류별) | 2.5 가정 | 품질 '실측' | 추정 상수 |
| 동시 8 의 챗 첫 응답 지연 | 평소 2배 안 | 엔진 몫 | 앱·엔진 동시 수 |
| 359명 × 20단위 원장의 DB 증가분 | 타깃당 35~65MB(설계 추정, 거르면 준다) | 리허설 · cae00 | 백업 |

## 13. D-33 · D-34 에 대해 — 적힌 대로 두면 틀리는 곳

1. **D-33 의 호출 어림(3,000~5,000)은 낙관적이다.** 검토하는 셀마다 카드 밖 호출이 1회 있고 입력 결손 셀도 1회씩 든다. 거르기 φ = 0.7 을 입력 결손 셀까지 걸어도 약 6,400회이고, 가운데 값은 약 8,000~10,000회다(10절). 3,000~5,000 에 닿으려면 카드 밖을 판정에 합쳐야 한다(a-22 — M3 에서는 안 한다). 셀 어림(2,000~2,500)도 φ ≈ 0.75 를 입력 결손 전문가에게까지 건 값이다 — 그것은 엔진의 훑기 결측 블록(X1-17 의 고침)이 들어온 뒤에야 할 수 있다.
2. **'걸린 것에만 이중 판정' 은 놓침 측정을 없앤다.** M2 가 재려던 걸림 없음 → 걸림 뒤집힘(거짓 '문제없음' 의 크기)은 음성 카드를 두 번 물어야 나온다. 1순위 셀만 전량 이중 판정으로 남긴다(+225회). `m3-engine-ops.md` 도 같은 걱정을 B2(무작위 10%)로 올렸다(b-3).
3. **D-33 은 배정표가 승인되기 전에는 아무것도 줄이지 않는다.** 형제 계획의 승인 문(배정표 `review_status`)이 닫혀 있으면 코드 신호가 전부 '모름' 이라 거르기가 일어나지 않는다. 사용자가 표를 훑는 것(D-34)이 거르기의 앞 조건이다.
4. **코드 신호에 필요한 표가 하나 더 있다.** 메커니즘 → 영역 표만으로는 변경을 영역에 잇지 못한다 — 변경 → 메커니즘 표가 택소노미에도 코드에도 없다(01-domainmap). 이 문서가 그 표를 내고, 사용자가 훑을 표는 둘이 아니라 셋이다(b-1).
5. **'K 를 키워 카드 전부를 한 호출에' 는 창이 아니라 출력 몫에서 멈춘다.** 엔진의 `k = min(CARD_REVIEW_K, k_out)` 이고 1M 창의 `k_out` 은 19 다. 점검 카드가 19장을 넘는 전문가는 여전히 두 묶음이다. rev 가 걸린 카드만으로 줄면 K 의 절감은 fwd 몫뿐이라 셀당 약 0.25회로 작다. 앱에는 K 손잡이가 필요 없다(엔진이 묶음을 짜고 앱은 `plan_json` 에 얼린다) — 추정식만 `limits.verdict.k` 를 읽는다(C3-10).
6. **'거른 셀의 5%' 는 작은 대상·영역에서 표본이 0 이 된다.** 59건 하한과 영역당 1건을 둔다(a-3). 그래야 형제 계획의 완결 조건('놓침 상한 5%')을 댈 수 있다.
7. **'넓힌다' 의 단위가 적혀 있지 않다.** 영역 단위로 정했다(a-4).
8. **D-34 의 '심의가 돌면 절반' 은 지금 코드 규칙이 아니다.** 엔진의 심의 중 상한은 별도 손잡이(`CARD_REVIEW_CONCURRENCY_WITH_DELIB`)이고 기본이 `min(2, conc)` 다 — 8 로 올려도 그 손잡이를 따로 바꾸지 않으면 심의 중 2 다. `m3-engine-ops.md` E3-7 이 기본을 `max(1, conc // 2)` 로 고친다. 앱 손잡이(`HWAXRISK_REVIEW_CONCURRENCY`) 기본도 4 라 같이 올려야 8 이 된다(C3-10).
9. **D-34 의 '낮 시간 동시 수' 는 낮·밤 구분이 없는 값이다.** 밤 창은 뺐다(PLAN 5절). 하루 내내 8 이다.
10. **D-34 의 '챗 지연이 2배를 넘으면 알린다' 는 지금 코드에 없다.** `m3-engine-ops.md` 가 엔진 로그의 경고 한 줄과 실주행 전 기준선 탐침으로 맡는다. 알림은 로그 한 줄이라 사람이 보아야 듣는다 — 리스크 앱 진행판에는 오지 않는다.
11. **D-16 · D-34 의 '전원' 은 지금 코드로 시작조차 안 된다.** 호출 추정의 높은 끝(셀당 14)이 101,238 회라 `review_too_large` 다. C3-10 이 고친다.
