# M2 실행 계획 — WP3a 카드 대조 엔진(`card_review`)과 포털 중계

> 2026-10-12 작성. 닻을 다시 확인한 HEAD 는 HWAXAgentServer `7644284` · HWAXPortal `5d2c748` · HWAXRisk `c3f46ba` · AIDataHub `b401f88` 이다.
> 우선순위는 PLAN.md > problems.md > reference/04-contract.md > reference/spec-wp3a-card-review-engine.md(이하 '설계서') 다.
> 줄 번호는 참고용이다. 고칠 자리는 함수 이름과 문자열로 찾는다.

## 범위

M2 에서 하는 것은 아래 여덟 걸음이다(PLAN 3절 M2 · 체크리스트 M2).

- 에이전트 서버 — 설계서 4절의 `WP3a 1~7`. 새 모듈 `card_review.py` 와 작은 관문 파일 `review_gate.py` 를 두고, `app.py` 에는 창 출처 함수 하나·라우터 한 줄·`/health` 칸·관문 초기화만 더한다. `deliberation.py` 에는 `_tools_by_name` 의 추가형 인자 하나만 더한다.
- 호출 종류는 `sweep`·`verdict`(변형 `fwd·rev·solo`)·`offcard` 셋이다(PLAN 3절 M2).
- 포털 — `WP3a P1` 중계 넷(`/agent/card-review/{limits,pack,plan,run}`).
- 시험 — WP5b `C7`(엔진·포털 쪽 몫)과 `C8`(엔진 쪽 가짜 LLM)이 이 걸음들에 붙는다. `C5`(리스크 앱 합성 카드)는 걸음 2 의 카드 모양을 따른다.

일부러 빼는 것은 이렇다.

| 무엇 | 처분 | 근거 |
|---|---|---|
| `WP3a 8` 긴 문서 검색, `noinput` 호출 | M3 | PLAN 3절 M2 '쓰지 않는 것'·M3 |
| `cross`(2차 영향) | M4 | PLAN 5절 |
| AIDataHub `A1 get_agent_cards`·`A2 agent_search` 인자 | M4 | PLAN 3절 M4, 문제 P-12 |
| `WP3a 9`·`P2`(엔진·포털 `knowledge_query`) | M1 에서 끝났다 | 체크리스트 `WP1 E1·P1`, X3-16 |
| 스냅샷 단위(`snap_unit`) 틀 | M4 — 들어오면 422 로 크게 거절한다 | PLAN 5절 '현황 타깃의 단위', 문제 P-01 |
| `hello` 첫 프레임·`review_unsupported`·빈 탐침 | 뺀다 — `GET /limits` 의 404 와 `/health.capabilities` 가 같은 일을 한다 | problems.md WP5a 빼는 것 1, X2-05 |
| 관문 대기 줄(`CARD_REVIEW_MAX_WAITING`·`WAIT_MAX_S`) | 뺀다 — 줄을 세우지 않는다 | C-24, problems.md X2 빼는 것 |
| K 파일럿 덮어쓰기 손잡이 | 뺀다 — M0-b 는 함수를 직접 불러 K 를 고른다 | P-09, X3-12 |
| 챗을 세는 관문·밤 창·비우기(`/drain`) | M3(밤 창은 뺀다) | PLAN 3절 M3 `WP5a A1·A2`, PLAN 5절 |
| 작은 창에서 묶음·단위를 다시 쪼개는 장치 | 만들지 않는다 — `ctx_too_small` 로 거절한다 | PLAN 4절 '단위 맞춤', D-22 |
| `limits.engine_evid_budget` | 싣지 않는다 — 쟁점 패널(M3)은 이미 있는 `/health.evid_budget` 을 읽는다 | M1 `WP1 E4` |

## 걸음

짓는 차례는 1 → 2 → 3 → 4 → 6 → 5 → 7 → P1 이다. 1·2·3·4·6 이 끝나면 M0-b 탐침이 포털·리스크 앱 없이 출발할 수 있다(PLAN 3절 M0-b). 5 까지 가면 가짜 LLM 으로 전체가 돌고, 7 + P1 이 있어야 리스크 앱(WP3b 7)이 붙는다.

### WP3a 1 — 예산·한도·묶음 계획(순수)과 창 출처

**목적.** 이 박스에서 한 호출에 무엇을 얼마나 실을 수 있는지를 창에서 유도해 알려 주고, 창이 모자라면 쪼개지 않고 거절한다.

**바꾸는/새 파일과 함수.**
- `HWAXAgentServer/card_review.py`(새, 첫 줄 한국어 역할 주석) — `limits(ctx_tokens, ctx_source, max_tokens, *, retrying=False, env=os.environ) -> dict`(순수), `plan(cards, units, lim) -> dict`(순수), `TEMPLATE_ALLOW`·`BODY_MIN` 상수.
- `HWAXAgentServer/app.py` — `_model_context_tokens()`(지금 2307행, 이름 그대로) 옆에 `_model_context_state() -> {"tokens", "source", "retrying"}` 를 더한다. 지금은 int 만 돌려주고 가정값인지가 `_ctx_cache`(2252행) 안에만 있으며, 답은 왔는데 창 칸이 없으면 기본값을 굳힌다(2334행 주석 '그건 아래에서 굳힌다'). `_ctx_cache["src"]` 를 적게 하고 `LLM_CONTEXT_TOKENS` 를 사람이 적었는지(`_CTX_FALLBACK`, 2250행)를 기억한다. 기존 함수의 반환과 호출자는 바꾸지 않는다.
- 가져다 쓰는 엔진 상수 — `deliberation._EVID_KO_CPT`(225행, 1.05) · `_PRE_SAFETY`(740행, 0.93) · `_CHAIR_RESERVE`(172행, 16,000). 셋 다 이름 그대로 있다. M1 의 `_room()`·`_ROOM_SHARE`(270행대)는 쓰지 않는다 — 도구 스키마 몫을 떼는 좌석 회계라 이 모듈과 다르다.

**계약.**
- 창 출처 `ctx_source` 는 셋이다 — `server`(LLM 서버가 창을 알려 줬다) · `env`(서버가 창 칸 없이 답했거나 닿지 않았는데 `LLM_CONTEXT_TOKENS` 를 사람이 적었다) · `fallback`(코드 기본값 128,000). `ctx_retrying` 은 방금 묻지 못해 60초 뒤 다시 묻는 중일 때 참이다. `ctx_assumed` 라는 이름은 쓰지 않는다(X4-27).
- 식(설계서 3.3 을 PLAN 4절에 맞춰 고친 것).
  - `OUT = max(mt, min(16000, ctx//4))`, `P_hard = int((ctx − OUT) × 1.05 × 0.93)` — 거절 문턱은 이것 하나다.
  - `P[kind] = min(P_hard, max(int(ctx × 1.05 × SHARE[kind]), TEMPLATE_ALLOW[kind] + BODY_MIN[kind]))` — 절벽을 없앤 식이다(P-16). `SHARE` 는 `verdict 0.25 · sweep 0.50 · offcard 0.30` 이고 넘으면 거절이 아니라 `soft_over` 표지다.
  - 고정 천장을 두지 않는다 — `ROLE_MAX = P//10`, `DIGEST_MAX = P//20`(sweep 은 0), `KNOWN_MAX = P//20`(offcard), 메커니즘 목록은 `P//20` 을 넘으면 코드만 싣는다. 설계서의 `min(2000, …)`·`min(2600, …)`·`known 1,200`·`longdoc 6,000` 은 버린다(PLAN 4절 C-17·C-32, P-02).
  - verdict — `unit_body_max = int(BODY × 0.47)`, `card_budget = BODY − unit_body_max`, `K = max(1, min(CARD_REVIEW_K, K_out))`, `K_out = int(OUTCAP × 0.6 × 1.05 // 520)`, `OUTCAP = mt or OUT`.
  - sweep — `manifest_page_max = int(BODY × 0.20)`, `card_budget = BODY − manifest_page_max`, `units_per_page_max = max(1, (OUTCAP × 0.63 − 400)//150)`, `manifest_item_max = max(800, manifest_page_max // units_per_page_max)`.
  - offcard — `findings_max = max(1, (OUTCAP × 0.63 − 1400)//600)` 로 출력 몫에서만 유도한다(설계서의 `min(8, …)` 천장을 뺀다 — P-18).
  - 최상위 `unit_body_max` 는 단위를 싣는 종류(verdict·offcard) 가운데 작은 값이다(P-02 덧붙임). WP2·WP3b 는 이 값 하나를 읽는다.
  - `runnable{kind}` 와, M2 종류 가운데 하나라도 거짓이면 `ctx_too_small{need_ctx_tokens}` 와 문구를 싣는다(PLAN 4절 '단위 맞춤'). 이 박스에서 새 흐름은 그 사유로 멈춘다.
  - `unit_size{per_line:11, base:160}`·`manifest_item{overhead:14}` 를 숫자로 싣는다 — 두 리포가 식을 베끼지 않는다(P-15, X4-21).
  - `limits_rev` = (창·OUT·mt·K·SHARE·TEMPLATE_ALLOW·BODY_MIN·식 판)의 sha 앞 8자. `prompt_rev` 는 넣지 않는다(P-06).
  - 응답의 판 칸 — `api_rev:"cr-1"` · `kinds:["sweep","verdict","offcard"]` · `prompt_rev{kind}` · `norm_rev` · `model`.
- 손잡이와 기본값 — `CARD_REVIEW_K`(8) · `CARD_REVIEW_SHARE_VERDICT`(0.25) · `CARD_REVIEW_SHARE_SWEEP`(0.50) · `CARD_REVIEW_SHARE_OFFCARD`(0.30). 설계서 7.2 의 `_PROMPT_SHARE`·`_SWEEP_SHARE` 두 이름은 셋으로 바꾼다.
- `plan()` — 입력 `cards[{alias, record_id, checkable, chars}]`·`units[{unit_id, manifest_chars, body_chars}]`. 출력 `{limits_rev, verdict_decks[{deck_id, aliases, chars, soft_over}], sweep_decks, manifest_pages, oversize{cards, units, manifest}, soft_over{units}}`. 묶음은 팩의 고정 순서로 글자 수와 K 를 함께 보고 닫는다. `oversize.units` 는 창(`P_hard`)을 넘는 단위만이고, `unit_body_max` 를 넘지만 창 안이면 `soft_over.units` 다. 설계서의 '카드 40장'·'팩 300장' 같은 건수 천장은 두지 않는다(verdict 만 K).
- 어림값(틀 여유값 가정, 시험이 실제 값을 못박는다).

| | cae00 1,048,576 · `max_tokens` 미설정 | dev 16,384 · 미설정 |
|---|---|---|
| `P_hard` | 약 1,008,000자 | 11,999자 |
| verdict `unit_body_max` · `card_budget` | 약 108,000 · 122,000자 | 약 3,000 · 3,400자 |
| `K`(`K_out`) | 8(19) | 4(4) |
| sweep 쪽당 단위 · 항목 상한 | 64 · 약 1,500자 | 14 · 800자 |
| offcard `findings_max` | 14 | 2 |

**수용 기준.**
- 창 출처 세 경우가 서로 다른 값으로 나온다 — 서버 칸 있음은 `server`, 칸 없음에 env 있음은 `env`, 칸 없음에 env 없음과 조회 예외는 `fallback`(예외는 `ctx_retrying=true`)(P-05·X3-08·X4-27).
- `limits()` 는 네트워크를 타지 않는다. 창 조회는 라우트가 `asyncio.to_thread` 로 한다(P-10).
- 창이 커지면 `unit_body_max` 가 줄지 않는다(단조, P-16). 단위를 싣는 종류마다 `BODY ≥ unit_body_max` 다(P-02 덧붙임).
- 틀 글을 여유값 안에서 바꿔도 `limits_rev`·`unit_body_max` 가 그대로다(P-06).
- 낮은 고정 천장(2,000·2,600·1,200·6,000·8)이 코드에 없다(PLAN 4절).
- `plan()` — 점검형 카드는 정확히 한 묶음이거나 `oversize` 이고, 묶음 장수 ≤ K 이며, 같은 입력이면 `deck_id` 가 같다.

**시험.** `tests/test_card_review_budget.py`(새). 세 박스(1,048,576·128,000/8,192·16,384) 값 단언, 16K~2M 무작위 창의 단조 속성, 카드 0~120장·200~95,000자 무작위 `plan()` 속성. 창 출처는 실제 `_model_context_state` 에 `_ctx_cache` 를 비우고 `httpx.get` 을 갈아 끼워 본다(손으로 쓴 사전이 아니라 생산자 함수를 거친다 — PLAN 9절).

**의존.** 없음(M1 이 들어간 HEAD 위에서 시작한다).

**크기.** 5시간(`plan()` 포함).

### WP3a 2 — 카드 정규화·렌더(순수)

**목적.** `get_record` 한 건을 판정과 인용 대조에 쓸 정규 글로 바꾸는 곳을 하나로 둔다(C-11).

**바꾸는/새 파일과 함수.** `card_review.py` — `normalize_card(rec) -> dict | None`, `card_text(card)`, `render_card(card, alias)`, `pack_hash(...)`, `NORM_REV = "cr-n1"`. 지어낸 카드 `tests/fixtures/card_review/cards/*.json`. 파리티 벡터 `tests/fixtures/card_review/contract/card_norm_vectors.json`(입력 기록 → 정규 글·`text_sha`).

**계약.** 설계서 3.4 의 필드표 그대로이고, 아래만 다르다.
- 결과에 `card_id` 를 늘 싣는다 — record_id 는 박스마다 다르다(P-11).
- 종류 `open-observation`(ExpertAgents 의 일곱째 종류, 지금 코퍼스에는 0장)은 배경 카드로 둔다. 그 밖의 모르는 종류는 점검형으로 둔다(P-17h).
- 역할은 `description`, 없으면 `app._role_doc(system_prompt)`(4384행, 이름 그대로)다. 팩에는 전문을 둔다(설계서의 8,000자 천장을 뺀다). 끊는 것은 프롬프트 조립(걸음 4)뿐이고 `_cut_mark` 표식을 단다.
- 머리 줄 떼기·`«»` 지우기·CRLF·빈 절 빼기·절 없는 카드의 `unrenderable` 은 설계서대로다.

**수용 기준.** 같은 입력이면 같은 `text_sha`·`pack_hash` 다(QP2). 머리 줄은 인용 원문에 들지 않는다. 절 없는 카드가 조용히 빠지지 않는다. 카드 모양은 WP5b `C5`(리스크 앱 `tests/synth/cards.py`)의 AIDataHub 기록 모양과 한 벌이다.

**시험.** `tests/test_card_review_cards.py`(새). 종류별 지어낸 카드 일곱, `content.card` 없이 태그만 있는 카드, 절 없는 카드, `«»`·`**굵게**`·표가 든 절. 실 카드 본문은 리포에 넣지 않는다.

**의존.** 없음.

**크기.** 3시간.

### WP3a 3 — 출력 파서·검사·합치기(순수)

**목적.** 모델 출력을 행 단위로 읽고, 별칭을 되돌리고, 인용·참조·수치를 대조해 행마다 `checks` 를 싣는다. 대조 구현은 서버 하나이고 앱은 얼린 팩으로 한 번 더 본다(C-11).

**바꾸는/새 파일과 함수.** `card_review.py` — `parse_rows(text, kind)`, `check_rows(kind, variant, rows, ctx)`, `merge_rows(kind, old, new, attempt)`, `repair_hint(problems, attempt, total)`, `_nq()`. 가져다 쓰는 것 — `deliberation._norm_ws`(2419행) · `_SUBSTANTIVE_RE`(2424행) · `_parse_json_multi`(2011행 — 설계서 2.2 표에는 없지만 M1 전부터 있다) · `evidence.sig_numbers`(18행). `_parse_json` 은 LLM 출력에 쓰지 않는다(설계서 2.2). 벡터 `tests/fixtures/card_review/contract/quote_vectors.json`.

**계약.**
- 받는 모양 — 한 줄에 객체 하나가 정본이고, 배열·`{"rows":[…]}`·코드 펜스도 받는다. `<think>…</think>` 구간을 먼저 뗀다. 줄 단위로 못 읽은 것이 있으면 `raw_decode` 훑기를 한 번 더 한다(P-17c).
- 모양 맞추기 — 목록 자리에 문자열 하나가 오면 한 항목 목록으로 읽고, 다른 모양은 빈 값으로 읽되 `checks.shape` 에 원래 값을 남긴다. 글자로 쪼개지 않는다(D-25 와 같은 규율).
- 검사 — 설계서 3.5.1·3.5.2·3.5.3 표에 더해 `checks.quote_sid`(인용이 걸린 절, P-17i), `checks.refs="evidence_only"`(변경 줄·문맥 줄 없이 근거 줄만 댔다, P-17e), 수치 원천에 머리 줄·단위 요약·`notes` 를 넣고 표지 이름을 `nums_unsourced` 로 한다(P-17f).
- sweep 은 `k0` 줄을 받지 않는다. 어느 단위의 `k` 에도 없는 카드는 서버가 여집합(`unmatched_cards`)으로 낸다(problems.md WP3a 빼는 것 4).
- offcard 는 끝줄 `{"t":"more","more":"yes|no"}` 를 받는다. `f` 가 `findings_max` 줄이거나 `more=yes` 면 `quality.maybe_more=true` 다(P-18·X1-16). M2 에는 긴 문서가 없으므로 `src` 의 `D` 별칭은 모르는 별칭이다. 제목만 실린 카드를 대면 `digest_only` 다.
- 같은 별칭이 두 번이면 문제가 적은 쪽을 남기고, 판정이 갈렸으면 `dup_conflict` 를 단다(C8 거동 9). 열거 밖 값은 불확실한 쪽으로 고친다(거동 11). 실리지 않은 별칭의 행은 버린다(거동 7, Q5).
- 보충을 일으키는 문제는 빠진 행·열거 밖·읽히지 않은 줄·`applies∈{yes,unknown}` 행의 인용 문제뿐이다. `applies=no` 행의 인용 불일치는 표지만 남긴다(problems.md WP3a 빼는 것 5).
- `merge_rows` 는 행마다 `from_attempt` 를, 앞 시도와 판정이 다르면 `flipped_from` 을 싣는다(P-08·X1-26).
- 절단 — `finish_reason` 을 못 읽으면 `truncated=null`(모름)이고 0 으로 치지 않는다. 마지막 줄이 깨졌으면 `tail_broken=true` 다(X1-22).

**수용 기준.** WP5b 3.4.4 의 Q1~Q8 이 벡터로 통과한다. 17번째 줄 하나가 깨져도 그 행만 빠진다(30행이 1행으로 줄지 않는다 — C8 거동 2·3). 거동 5·6·7·9·10·11·12·13 이 파서 층에서 기대대로 남는다.

**시험.** `tests/test_card_review_rows.py`·`tests/test_card_review_quote_vectors.py`(새). 벡터 파일은 시험이 만들고 손으로 고치지 않는다(WP5b R8).

**의존.** 걸음 2(`card_text`).

**크기.** 6시간.

### WP3a 4 — 프롬프트 셋과 조립 한 자리, LLM 호출 감싸개

**목적.** 모든 프롬프트가 한 자리(`_assemble`)를 지나 창 초과를 호출 전에 거절하게 하고, 판정·인용·출력 계약을 틀로 고정한다.

**바꾸는/새 파일과 함수.** `card_review.py` — `build_prompt(req, lim, hint="") -> (system, human, ctx)`, `_assemble()`(`OverBudget(need, have, part)`), `unit_size(unit)`, `PROMPT_REV`, `_ask(llm, system, human) -> (text, meta)`. `_ask` 는 M1 에 생긴 `app._finish_reason(msg)`(806행)를 쓰고 `response_metadata["token_usage"]`, 없으면 `usage_metadata` 를 읽는다. 엔진에는 지금도 토큰 사용량을 읽는 코드가 0건이다(grep).

**계약.**
- 시스템 글·사람 글 머리·블록 순서는 설계서 3.5.0 그대로다(한국어 고정·«» 규율·닫힌 별칭·모르면 unknown). 역할은 `ROLE_MAX` 에서, 배경 카드 제목은 `DIGEST_MAX` 에서 `_cut_mark`(deliberation.py 2272행) 표식을 달고 끊는다.
- 단위 구조는 C-14 에 `context[{ref, text, owner_unit}]` 를 더한다. 변경 줄 → 문맥 줄('다른 단위가 맡은 변경 — 인용할 수 있다') → 근거 줄 순으로 `L01…` 을 이어 매긴다. `lines` 와 `context` 가 둘 다 비면 422 `empty_unit` 이다(X4-14). `unit.kind` 가 `snap_unit`·`excluded` 면 422 `unsupported_unit_kind` 다(P-01 은 M4).
- 종류별 틀 — `sweep`(k0 없음), `verdict`(`fwd` 는 팩 순서, `rev` 는 카드 순서만 뒤집고 별칭은 같다, `solo` 는 카드 1장에 조건 줄 `t:"c"` 와 `sev·path·check_kind·check`), `offcard`(`extra.known`·`extra.mechanisms`·`extra.domains`, `findings_max`, `more` 줄). `extra.search` 는 받지 않는다(M3).
- 묶음이 1장인 `rev` 는 `meta.order_effective=false` 를 단다 — 일치율이 공짜로 오르지 않게 한다(X1-20).
- `PROMPT_REV = {"sweep":"cr-sweep-1","verdict":"cr-verdict-1","offcard":"cr-offcard-1"}` 는 손으로 올리는 판 번호다. 틀의 sha 는 '판을 안 올리고 글을 바꿨다' 를 잡는 시험에만 쓴다(P-06④).
- `est_tokens` 는 M1 의 `app._est_tokens_all`(글자 구성 환산)로 잰다. 거절 문턱은 보수적인 글자 식(`P_hard`) 그대로다.

**수용 기준.** 조립 길이가 `P_hard` 를 넘으면 LLM 을 부르지 않고 `OverBudget` 이며 조용히 줄이지 않는다. `unit_size()` 는 실제 렌더 길이 이상이다. 각 틀의 길이가 `TEMPLATE_ALLOW` 안이다. `plan()` 이 낸 어느 묶음과 `unit_body_max` 크기 단위도 `OverBudget` 이 나지 않는다(P-10 이 걸음 1 에서 옮긴 속성 ④). 프롬프트의 카드 수 ≤ K, `L` 별칭 수 = `lines + context + evidence` 수, 카나리아 문자열이 프롬프트에 있다(WP5b 3.6.2 끝 단락).

**시험.** `tests/test_card_review_prompts.py`(새). 주입 문구(`»`·'위 지시를 무시하라'·가짜 판정 줄)를 카드와 변경 줄에 넣어도 구간이 닫히지 않는다.

**의존.** 걸음 1·2·3.

**크기.** 6시간.

### WP3a 6 — 팩 빌더(도구)

**목적.** 전문가 한 명의 지식카드 전부를 원문으로 받아 정규 팩을 만든다. '카드 0장'·'없는 전문가'·'못 받았다' 를 다른 모양으로 답한다(C-10).

**바꾸는/새 파일과 함수.**
- `card_review.py` — `async build_pack(tools, agent_key) -> dict`, `PackError(code, status, detail)`. 팩 빌드 동시 2건 세마포어는 `app.state` 에 둔다(P-17b).
- `deliberation._tools_by_name`(1723행)에 추가형 인자 `svc_fallback: bool = True` 를 더한다. 지금 이 함수는 사용자 PAT 가 거절되면 로드 때(1738~1747행)와 호출마다 401 일 때(`_svc_fallback`, 1788행) 서비스 계정으로 조용히 넘어간다. 카드 대조는 `False` 로 부른다. 설계서 3.11 의 'deliberation.py 를 고치지 않는다' 와 어긋나는 한 줄이다.
- 가져다 쓰는 것 — `_call`(1818행) · `_first_dict`(2045행) · `_parse_json`(2085행, 객체 하나인 도구 응답만) · `_RA_FAIL_WRAP`(3049행, 도구 실패 문구 두 꼴) · `_AUTH_REJECT_MARK`(29행) · `_KN_CONC`(2873행, 6) · `app.CATALOG_RESULT_MAX`(626행, 2,000,000).

**계약.**
- 요청 `{agent_key}` + 신원 칸 넷. 도구는 `_tools_by_name(app, groups, CATALOG_RESULT_MAX, user=user_email, user_pat=user_pat, svc_fallback=False)` 다.
- 실패 규칙(P-03) — 도구 사전이 비었거나 `list_records`·`get_record`·`get_agent_session` 가운데 하나라도 없으면 503 `tools_unavailable{missing}`. 자격 거절이면 `credential_rejected`(내려가지 않는다 — PLAN 7절 M2 앞 셋째). `user_pat` 이 비어 오면 `credential_missing` 이다. `get_agent_session` 실패 문구에 `agent not found` 가 있으면 404 `agent_not_found`. `list_records` 응답이 dict 가 아니거나 `items` 가 list 가 아니거나 `total` 이 int 가 아니면 502 `card_list_failed`. 모은 id 수가 `total` 과 다르면 502 `card_list_unstable`(AIDataHub 정렬이 `updated_at` 내림차순이라 쪽 넘김 중 수정이 끼면 흔들린다 — record_query_svc.py 71행). `get_record` 가 한 장이라도 실패하거나 id·`doc_type` 이 다르면 502 `card_fetch_failed{failed}` 다. 일부만 든 팩은 주지 않는다.
- 쪽 넘김 — `list_records(agents=[키], doc_type="expert_knowledge_card", limit=100, offset=…)`. AIDataHub 의 `limit` 은 여전히 1~100 이다(mcp_runtime.py 955행).
- 개별 조회 — 동시 `_KN_CONC`, 호출마다 `asyncio.wait_for` 60초. 최악은 목록 60초 + 35장 ÷ 6 × 60초 = 420초로 포털 단발 한도 600초 안이다.
- 응답 — 설계서 3.4 의 모양에 `card_id`, `unrenderable`, `credential:"user"`(WP5b P-08 — 서버가 실제로 쓴 자격), `source:"list+get"`, `norm_rev`, `pack_hash` 를 싣는다. 역할은 전문이다.

**수용 기준.** 0장은 `cards:[]` 정상 팩, 없는 전문가는 404, 목록 실패·도구 부재·자격 거절은 각자의 코드다(P-03). 사용자 PAT 가 거절돼도 서비스 계정으로 성공하지 않는다(WP5b P-08). 기존 `tests/test_cred_fallback.py` 가 그대로 통과한다(기본값 `True` 는 종전 동작).

**시험.** `tests/test_card_review_pack.py`(새). 가짜 도구는 실제 모양으로 답한다 — 문자열 JSON, content-item 목록, `(tool … error: …)`, `✖ 도구 … 호출 실패:`, 401 표식. 도구 사전에 `list_records` 가 없음 → 503, 실패 문구 → 502, `None` → 502, 35장 중 1장 실패 → 팩 전체 실패.

**의존.** 걸음 2.

**크기.** 4시간.

### WP3a 5 — 실행기(관문·ping·보충·오류 분류)와 가짜 LLM

**목적.** 요청 1건 = (전문가 × 단위 × 묶음 1개)의 논리 호출 1건을 공유 LLM 에서 안전하게 돌린다. 줄을 세우지 않고, 끊기면 접고, 빠진 행만 다시 묻는다.

**바꾸는/새 파일과 함수.**
- `HWAXAgentServer/review_gate.py`(새) — `ReviewGate(limit_fn)`, `try_acquire(tag) -> Ticket | Busy`(동기·무대기), `release(ticket, outcome, usage)`, `snapshot()`. WP5a A1 의 파일 이름과 API 를 지금 최소로 낸다 — M3 의 A1 이 같은 파일에 밤·챗·비우기를 더한다(관문이 두 벌이 되지 않게 — X3·problems.md X2 빼는 것).
- `card_review.py` — `async run(app, req)`(SSE 제너레이터), 스트림 감싸개(약 20줄).
- `tests/fakes/llm.py`(새) — `FakeLLM(script)`, `calls`, 최대 동시 수 계수. WP5b C8 의 엔진 쪽 한 벌이다.

**계약.**
- 관문 — `CARD_REVIEW_CONCURRENCY`(4), `CARD_REVIEW_CONCURRENCY_WITH_DELIB`(2, `app._delib_load()[0] > 0` 일 때 — 4603행), `CARD_REVIEW_RETRY_AFTER_S`(30). 자리는 제너레이터 **안에서** 잡는다 — 바깥에서 잡으면 스트림이 시작되기 전에 끊길 때 자리가 샌다(포털 `/chat` 의 세마포어 주석과 같은 까닭). 자리가 없으면 1초 안에 `error{code:"review_busy", reason, retry_after_s, limit, active}` → `done` 이다(C-24).
- 프레임 — `status{step:"attempt", n}` · `ping{idle_s, ts}` · `result` · `error` · `done`. `hello` 는 없다. `_detach_stream`(555행)을 쓰지 않는다 — `_DETACHED_TASKS` 에 들어가 `delib_active` 를 올리고 끊겨도 끝까지 돈다(C-25).
- ping — `asyncio.wait({일}, timeout=DELIB_HEARTBEAT_S)`(552행, 15초)로 기다리고 안쪽을 취소하지 않는다. `DELIB_HEARTBEAT_S ≤ 0` 이면 timeout 없이 기다린다(P-17a). 제너레이터가 닫히면 `finally` 에서 LLM 태스크를 취소하고 자리를 돌려준다.
- LLM — `app.state.delib_llm`(366행)을 그대로 쓴다. 요청 단위 시간 덮어쓰기는 받지 않는다. 논리 호출 1회 최악 = (1+`DELIB_LLM_MAX_RETRIES`) × `DELIB_TIMEOUT_S` + 8 = 3,608초, 요청 최악 = (1+`CARD_REVIEW_PARSE_RETRIES` 2) × 3,608 = 10,824초다(대기 줄이 없어 설계서의 15,024초보다 짧다).
- 오류 어휘(P-07 — 엔진이 내는 쪽이 정본이고 앱의 `review_ops.py` 가 부류를 정한다).

| code | 언제 | infra | retryable | knob |
|---|---|---|---|---|
| `review_busy` | 관문에 자리가 없다 | (기다림) | 예 | `CARD_REVIEW_CONCURRENCY*` |
| `llm_unreachable` | 연결 실패 | 예 | 예 | `VLLM_BASE_URL`·`LLM_CONNECT_TIMEOUT_S` |
| `llm_timeout` | 시도 한도 초과 | 예 | 예 | `DELIB_TIMEOUT_S` |
| `llm_error` | 429·5xx·그 밖 | 예 | 예 | — |
| `llm_misconfigured` | 401·403·404 | 예 | 아니오(잡을 세울 일) | `VLLM_API_KEY`·`VLLM_MODEL` |
| `llm_rejected` | 400·413·422(창 초과 아님), 원문 200자 | 아니오 | 아니오 | — |
| `context_overflow` | 400 이고 추정 토큰 + OUT ≥ 창의 85%(문구에 기대지 않는다) | 아니오 | 아니오(나누지 않는다) | `LLM_CONTEXT_TOKENS` |
| `truncated_empty` | 첫 시도가 절단이고 0행 | 아니오 | 아니오 | `DELIB_MAX_TOKENS` |
| `no_rows` | 모든 시도가 0행 | 아니오 | 예 | — |

- 메시지와 손잡이는 `deliberation._llm_fail_note`(2757행)를 쓰고, 부류는 예외 사슬과 `status_code` 로 가른다(P-13).
- 보충 중(n ≥ 2) LLM 이 실패하면 `error` 가 아니라 `result` 로 끝내고 `quality.repair_error{code, attempt}` 를 싣는다(P-08).
- `result.meta.usage = {llm_calls, tokens_in, tokens_out, per_attempt[]}` 는 시도 합계이고, 모르면 `null` 이다(P-07④). `meta.basis` 는 `cards` 또는 `role_only`(카드 0장, M2 에는 검색이 없다)다.
- 손잡이 — `CARD_REVIEW_PARSE_RETRIES`(2).

**수용 기준.** 12건을 동시에 쏘면 가짜 LLM 이 센 최대 동시 수가 4 이하이고, `_delib_load` 를 1 로 바꾸면 2 이하다. 자리 없음은 1초 안에 `error → done` 이다. 스트림을 닫으면 LLM 태스크가 실제로 `cancelled()` 이고 `review_active` 가 0 으로 돌아온다(WP5a 5.2 의 2). LLM 이 0.3초 걸리는 동안 ping 간격 0.05초로 ping 이 3개 이상이다. 도는 동안 `/health.delib_active` 가 변하지 않는다(C-25). 보충은 빠진 행만 묻는다(둘째 프롬프트의 지적 블록에 그 K 번호만 있다).

**시험.** `tests/test_card_review_run.py`·`tests/test_review_gate.py`(새). WP5b C8 거동 1·2·4·8·14 부터(PLAN 3절 M2), 나머지 거동은 걸음 3 의 파서 시험과 겹치지 않게 연쇄(`[broken_line, oracle]`)로만 더한다. 취소는 제너레이터 `aclose()` 로 본다(실제 끊김은 걸음 7).

**의존.** 걸음 3·4. 관문은 WP5a A1(M3)이 넓힌다.

**크기.** 8시간.

### WP3a 7 — 라우트 넷·요청 검증·`/health`·계약 예제

**목적.** 네 끝점을 내고, 섞인 판이 실패가 아니라 크게 드러나게 하고, 리스크 앱이 같은 바이트로 읽을 계약 예제를 만든다.

**바꾸는/새 파일과 함수.**
- `card_review.py` — `router = APIRouter(prefix="/card-review")`. `GET /limits`(창 조회는 `to_thread`), `POST /pack`, `POST /plan`, `POST /run`(SSE). 요청 모델은 `extra="forbid"` 다 — 선언하지 않은 칸이 조용히 사라지는 사고를 이쪽에서도 막는다(422 `unknown_fields`). `validate_run_request(body) -> list` 를 앱 없이 import 할 수 있게 둔다(WP5b 3.5 의 서브프로세스 요청 검증).
- `app.py` — `card_review` import 와 `include_router` 를 감싼다. import 가 실패해도 기동은 계속하고 `capabilities` 에서 빠진다(X2-15). `health()`(4613행)에 `review_active`·`capabilities:["card_review"]`·`card_review{rev, kinds, limit, limit_reason, active, timeout_s, tries, attempts_max, request_worst_s, prompt_rev, totals{calls, ok, error, busy, truncated, repaired, over_budget, context_overflow, tokens_in, tokens_out, tokens_unknown_calls}, last_error}` 를 더한다. 기존 키는 그대로다. `app.state.review_gate` 를 기동 때 만든다.
- `tests/fixtures/card_review/contract/` — `result_{sweep_ok, verdict_ok, verdict_repaired, verdict_missing, verdict_truncated, offcard_ok}.json`·`error_{truncated_empty, llm_timeout, context_overflow, review_busy}.json`·`limits_1m.json`·`llm_transcript_*.txt` 와 걸음 2·3 의 벡터 둘. `tests/test_card_review_contract.py` 가 만들고 `CARD_REVIEW_CONTRACT_UPDATE=1` 로만 다시 뜬다(M1 의 `RISK_FRAMES_UPDATE` 선례).
- `README.md` — `### Card review` 절을 새로 둔다. `### Time limits` 표에 넣지 않는다 — 넣으면 포털 `test_infra_env_kit_agent_server.py` 가 킷에 같은 손잡이를 요구한다. 시간 사슬에 넣는 일은 M3 `WP5a P3` 다.

**계약.**
- 스트림 전 거절 — 422 `bad_request`·`unknown_fields`·`unsupported_kind`(`noinput`·`cross`)·`unsupported_unit_kind`·`empty_unit`·`deck_too_large`(verdict 카드 > K, `solo` 는 1장)·`over_budget{need, have, part}`·`ctx_too_small`, 409 `rev_mismatch{prompt_rev, limits_rev}`, 403 `denied`. 요청의 `expect{prompt_rev, limits_rev}` 가 지금 판과 다르면 409 다(X4-26).
- 권한 — `entitlements` 가 왔는데 `feat:deliberation` 이 없으면 403 이다(`None` 이면 옛 호출로 통과 — `app._denied_feature` 504행과 같은 규칙).
- 크기 상한 — 건수 천장을 따로 두지 않는다. 프롬프트는 `_assemble` 이, 본문 폭주는 포털(`_WINDOW_CHARS`)이 막는다.
- `request_worst_s` 는 걸음 5 의 식을 이 박스의 실제 값으로 셈해 싣는다(problems-wp5a 130행). 한도가 꺼진 박스는 `null` 이다.

**수용 기준.** TestClient 로 422·409·403 과 프레임 순서(`status → ping* → result|error → done`, 자리 없음은 `error → done`). `/health` 에 새 키가 있고 카드 대조가 도는 동안 `delib_active`·`delib_queued` 가 그대로다(WP5a 5.2 의 1). 임시 포트의 실제 uvicorn + httpx 로 구독을 끊으면 LLM 태스크가 취소된다(P-17l — 떠 있는 9009 를 쓰지 않고 빈 포트를 잡으며, 하네스는 절대경로를 쓰고 `pkill -f` 를 쓰지 않는다). `python -c "import card_review"` 가 env·LLM 없이 된다. 가짜 LLM 원문으로 `run` 을 돌린 마지막 프레임이 예제 파일과 같다(시각·밀리초 제외 — WP5b C7 엔진 쪽).

**시험.** `tests/test_card_review_http.py`·`tests/test_card_review_contract.py`·`tests/test_card_review_disconnect.py`(새). 엔진 리포 시험 전체(지금 1,415건)를 돌린다.

**의존.** 걸음 5·6. 리스크 앱 `tests/rr/test_card_review_contract.py`(WP3b·C7 리스크 쪽)가 이 예제를 형제 경로로 읽는다.

**크기.** 6시간.

### WP3a P1 — 포털 중계 넷

**목적.** 리스크 앱 러너가 PAT 로 부르면 포털이 신원 칸 넷만 덮어써 에이전트 서버로 넘긴다. 대화를 만들지 않고 `/agent/chat` 을 쓰지 않는다(C-12).

**바꾸는/새 파일과 함수.**
- `HWAXPortal/backend/app/agent/routes.py`(1,722줄) — `/agent/card-review/limits`(GET)·`/pack`·`/plan`·`/run`(POST). 쓰는 것 — `ensure(principal, "feat:deliberation")`(deps.py 86행) · `_chat_user_pat`(302행) · `is_synthetic` · `_unary_timeout`(526행) · `_audit`(514행) · `_WINDOW_CHARS`(70행).
- `config.py` — `card_review_max_streams: int = 12`.
- `main.py` — 전용 `app.state.card_review_client = httpx.AsyncClient(limits=Limits(max_connections=card_review_max_streams + 4))` 와 전용 세마포어를 만들고 닫는다. 지금 공유 클라이언트는 `max_connections = max_concurrent_chats`(64)라 챗과 연결을 다툰다(P-14).
- `backend/tests/test_card_review_relay.py`(새).

**계약.**
- 본문 — 원 본문 바이트가 `_WINDOW_CHARS`(4,194,304)를 넘으면 413 이다. 설계서의 600,000자 상한은 버린다(1백만 토큰 창의 단일 sweep 은 카드 9만 자 + 목록 10만 자 안팎이다). JSON 으로 읽어 `groups = principal.groups`, `user_email = principal.email`, `user_pat = _chat_user_pat(...) or ""`, `entitlements = sorted(합성 그룹)` 을 덮어쓰고 나머지 칸은 손대지 않는다. 호출자가 실어 보낸 신원 칸은 버린다.
- 단발(limits·pack·plan) — `_unary_timeout`(600초). 시간 초과는 기본값 진행이 아니라 504 `agent_timeout` 이다(도우미 폴백 규칙을 따르지 않는다). 에이전트 서버의 4xx JSON 은 상태와 본문을 그대로 넘긴다(앱이 `code·need·have` 를 읽는다). 404 는 `agent_outdated` 로 적는다(옛 에이전트 서버). 5xx·연결 실패는 502 `agent_5xx`·`agent_unreachable` 이다.
- run — 전용 세마포어가 차면 429 `{code:"engine_busy", retry_after_s:30}` 이다(기다림 부류 — PLAN 4절 C-24·C-26). 획득과 제너레이터 사이를 `/chat` 처럼 보호한다. 바이트를 그대로 흘리고, 침묵 한도(`agent_stream_idle_timeout_s`, 13시간)에 걸리면 `error{agent_stream_idle}` 를 낸다. 앱 쪽 연결이 끊기면 `client.stream` 문맥이 닫혀 에이전트 쪽 연결도 닫힌다(problems-wp5a 186행).
- 감사 — `card_review_pack_*`·`card_review_run_{start,done,error}` 에 주체·종류·전문가 키·단위 id·본문 바이트 수·sha256·상류 상태만 적는다. 본문은 싣지 않는다.

**수용 기준.** WP5b C7 포털 단언 ①~⑤ — 나간 본문이 받은 본문과 신원 칸 넷만 다르다, 호출자가 보낸 `groups`·`entitlements`·`user_email`·`user_pat` 이 버려진다, 크기 경계(상한 통과·+1 거절), `feat:deliberation` 없으면 403 이고 에이전트 서버로 아무것도 안 나간다, 감사 행에 본문이 없다. 챗 세마포어를 다 채운 상태에서도 카드 대조가 연결을 얻는다(P-14). 422·409·429 가 상태 그대로 통과한다.

**시험.** `httpx.MockTransport` 로 에이전트 서버를 흉내 낸다. 포털 시험 전체(지금 2,128건)를 돌린다.

**의존.** 걸음 7 의 계약(목으로 먼저 지을 수 있다). 리스크 앱 `WP3b 7`(`PortalReviewEngine`)이 이 중계를 부른다.

**크기.** 5시간.

### 문서(걸음마다 덧붙인다)

`docs/risk-review-redesign/checklist.md` 의 M2 칸을 고치고, `context-notes.md` 에 이 계획의 결정(창 출처 셋, 오류 어휘, 관문 파일, `svc_fallback`, 중계 본문 상한)을 날짜와 함께 덧붙인다. 엔진 README `### Card review` 와 업데이트 이력의 '기술' 항목을 같은 커밋 묶음에 넣는다(기본 꺼짐이라 사용자 화면 변화는 없다). 1.5시간.

**합계.** 순수 실행 약 44.5시간(1: 5 · 2: 3 · 3: 6 · 4: 6 · 6: 4 · 5: 8 · 7: 6 · P1: 5 · 문서 1.5)이다. 이 프로젝트의 감사 라운드 재작업을 얹으면 55시간 안팎이다. 아래 열린 물음 6 을 받으면 1.5시간이 더 든다.

## M1 이후 달라진 것

| 설계서가 가정한 것 | 지금 코드·사실 | 어떻게 바꾸나 |
|---|---|---|
| 운영 창 128,000 토큰(설계서 3.3 표) | cae00 은 1,048,576 토큰을 서버에서 읽는다(M0-a, D-20) | 묶음 크기를 묶는 것은 창이 아니라 K(8)와 출력 몫이다. `unit_body_max` 는 약 108,000자로 단위 쪽이 넘을 일이 없다. 단위 크기의 품질 상한은 WP2 가 M0-b·M0-c 로 정한다 |
| `ROLE_MAX 2,000`·`DIGEST_MAX 2,600`·`known 1,200`·`longdoc 6,000`·`F ≤ 8`·팩 역할 8,000자·요청 600,000자 | M1 이 같은 꼴의 고정 상한을 엔진·포털에서 창 유도로 바꿨다(`_room()`·`_role_req_max()` 1M 에서 9,692자, 포털 `_WINDOW_CHARS`) | 전부 창 몫(`P//10` 등)이나 출력 몫으로 유도하고 끊으면 `_cut_mark` 표식을 단다 |
| `ctx_assumed` 를 만들 수 있다 | `_model_context_tokens()` 는 여전히 int 만 주고 '칸 없는 답' 이면 기본값을 굳힌다(app.py 2307·2334행) | `app._model_context_state()` 를 더하고 `ctx_source(server·env·fallback)`·`ctx_retrying` 을 싣는다. 10분 보류(`ctx_unknown`)는 WP3b 몫이다(X3-08) |
| `context_overflow` 면 앱이 묶음을 반으로 나눠 다시 낸다(WP3b 설계서 898·899행) | PLAN 4절·D-22 가 작은 창용 다시 쪼개기를 없앴다 | 엔진은 `retryable:false` 로 답하고 앱은 셀을 사유와 함께 실패시킨다. 창이 모자란 박스는 `limits.ctx_too_small` 로 처음부터 멈춘다 |
| `/health` 에 `card_review_active`·`card_review_waiting` | C-25 가 `review_active`·`capabilities` 로 이름을 정했고 C-24 가 대기 줄을 없앴다 | 계약 이름을 쓰고 `waiting` 은 싣지 않는다. WP3b 의 `health()` 옮기기 칸도 그 이름으로 고친다 |
| `deliberation.py` 를 고치지 않는다(설계서 3.11) | `_tools_by_name` 이 사용자 PAT 거절을 서비스 계정으로 조용히 넘긴다(로드·호출 두 곳) | 추가형 인자 `svc_fallback` 하나를 더한다(기본값은 종전 동작) |
| 포털 `ChatRequest.message` 65,536자라 챗 길로 못 간다(설계서 2.6) | M1 이 `_WINDOW_CHARS`(4,194,304)로 올렸다 | 별도 중계의 까닭은 '선언 안 한 칸 유실·대화 생성·챗 세마포어' 로 남는다. 계약(C-12)은 그대로다 |
| `knowledge_query` 를 WP3a 9·P2 에서 넣는다 | 엔진 `_KNOWLEDGE_Q_MAX`·`_KNOWLEDGE_Q_KEYS_MAX`(112·113행), 포털 `DelibOpts.knowledge_query`(str·dict)·`save_report` 가 M1 에 들어왔다 | 이 꾸러미에서 지운다 |
| `/health` 에 `engine_evid_budget` 을 따로 싣는다 | `/health.evid_budget` 이 M1 `WP1 E4` 로 이미 있다 | `limits` 에 싣지 않는다 |
| `_llm_text` 와 같은 열 줄을 `_ask` 로 둔다 | M1 이 `app._finish_reason()`(806행)과 글자 구성 환산 `app._est_tokens_all()` 을 만들었다 | `_ask` 가 둘을 쓴다. 토큰 사용량을 읽는 코드는 여전히 0건이라 `_ask` 가 처음이다 |
| 줄 번호(설계서 2.2 표) | 이름은 전부 그대로이고 줄만 밀렸다 — `_tools_by_name` 1294→1723, `_call` 1389→1818, `_parse_json` 1611→2085, `_norm_ws` 1898→2419, `_agent_search_hits` 2407→3007, `_llm_limit` 2194→2734, `_llm_fail_note` 2217→2757, `_restore_role` 3119→3830, app `_model_context_tokens` 2033→2307, `_role_doc` 4045→4384, `_delib_load` 4264→4603, `DELIB_HEARTBEAT_S` 542→552 | 함수 이름으로 찾는다. `_SEAT_CTX` 는 이제 바닥값이고 실제 몫은 `_seat_ctx()` 다(이 모듈은 쓰지 않는다) |
| `_restore_role` 의 방식을 따른다 | `_restore_role` 은 `system_prompt` 로 내려갈 때 `_role_doc` 을 걸지 않는다 | 팩은 `_role_doc` 을 직접 건다 |
| 게이트웨이가 큰 도구 결과를 넘기는지 모른다(설계서 9절) | M1 이 게이트웨이의 결과 절단을 없앴다(큰 결과는 캐시하지 않고 넘긴다 — truncation.md) | 카드 9만 자도 한 응답으로 온다. 폴백 길은 어차피 한 장씩이다 |
| AIDataHub `list_records`·`get_record`·`get_agent_session` 의 모양 | 그대로다 — `limit` 1~100, `updated_at`·`id` 내림차순, 모르는 키는 `agent not found:`·`record not found:` 예외 | 설계서대로 쓴다. 정렬이 흔들리는 경우만 `card_list_unstable` 로 크게 알린다 |
| 시험 디렉터리 | `tests/` 78개 파일, `tests/fakes/` 는 없다. 형제 리포 계약 예제 선례가 `tests/fixtures/risk_contract/panel_frames.jsonl` 이다 | 같은 자리 옆에 `tests/fixtures/card_review/contract/` 와 `tests/fakes/llm.py` 를 둔다 |
| 파리티 검사기 `scripts/check_chair_parity.py`(엔진 리포) | 검사기는 포털 리포 `scripts/check_chair_parity.py` 에 있다 | 새 파일은 세 상수를 건드리지 않으므로 걸리지 않는다. 걸음마다 그대로 돌린다 |
| 엔진 README 의 손잡이 | 포털 `test_infra_env_kit_agent_server.py` 가 README `### Time limits` 표의 손잡이를 킷에서 찾는다 | 카드 대조 손잡이는 별도 절에 적는다(M3 의 시간 사슬 걸음에서 합친다) |

## 열린 물음

1. **(PLAN 7절 M2 앞) 카드 원문을 리스크 앱 DB 에 복제하고 보고서에 인용하나.** 이 꾸러미의 계약은 '팩 응답을 앱이 통째로 얼린다' 에 서 있다(C-10·C-11, QP1·QP2). '복제하지 않는다' 가 답이면 앱의 얼린 팩 재대조가 사라지고 인용 재대조를 서버에 다시 물어야 해 걸음 3·7 의 계약이 바뀐다. 권고는 PLAN 대로 복제한다(판정당 인용 200자 상한은 앱 몫, 박스 간 반출 제외).
2. **(PLAN 7절 M2 앞) 카드 대조의 FAIL 하나로 과제 판정 후보를 '불가' 까지 올리나.** 이 꾸러미에는 영향이 없다(등급은 앱의 정책). 권고대로 WARNING 까지다.
3. **(PLAN 7절 M2 앞) 긴 작업 중 자격이 만료되면.** 이 꾸러미는 '멈추고 알린다' 를 전제로 `svc_fallback=False`·`credential_rejected`·`credential_missing` 을 둔다. 권고는 PLAN 대로다. 다른 답이면 걸음 6 의 실패 규칙과 `credential` 칸만 바뀐다.
4. **관문 기본값과 이름.** C-24 는 4/2, WP5a 는 낮 2·밤 6 이었다. 권고는 C-24 의 4/2 를 WP5a 의 이름(`CARD_REVIEW_CONCURRENCY`·`CARD_REVIEW_CONCURRENCY_WITH_DELIB`)으로 `review_gate.py` 에 두고, 챗을 세는 낮춤은 M2 의 챗 첫 응답 지연 실측 뒤 M3 에 넣는 것이다.
5. **오류 어휘의 정본과 `llm_timeout` 의 부류.** WP5a 3.3.4 의 이름(`output_truncated`·`review_parse_failed`·`review_incomplete`)과 이 표가 다르다. 권고는 엔진이 내는 위 표를 계약에 한 조로 적고 WP3b `review_ops.py` 가 그 이름으로 분류하는 것이다. `llm_timeout` 은 엔진이 `infra:true` 로 내고(PLAN 4절 C-24·C-26), 같은 호출의 두 번째 시간 초과를 내용 탓으로 치는 것은 앱이 정한다(P-07③). 메인 에이전트가 WP3b 계획과 맞춰야 한다.
6. **dev 배선 리허설을 무엇으로 하나.** dev LLM 은 16K 창이라 1백만 토큰 예산을 실제 스택으로 볼 수 없고, OpenAI 호환 가짜 LLM 서버(WP5b C13 의 `tests/fakes/llm_server.py`)는 M4 로 미뤘다. 그대로면 체크리스트의 'dev 가짜 LLM 배선 리허설' 을 탈 것이 없다. 권고는 걸음 5 의 `FakeLLM` 대본을 그대로 내는 작은 서버(약 80줄, `/v1/models` 의 `max_model_len` 을 인자로)를 M2 로 당겨 임시 에이전트 서버를 빈 포트에 띄우는 것이다(1.5시간). 운영 코드에 가짜 손잡이를 두지 않는다는 D-15 와 부딪치지 않는다.
7. **offcard 에 배경 카드를 얼마나 싣나.** 설계서는 훑기의 `k` 로 고른 것만 싣는다. M2 는 거르기가 꺼져 있고 1백만 토큰 창에는 전문가 카드 전부(최대 약 9만 자)가 들어간다. 권고는 M2 파일럿에서 앱이 배경 카드 전부를 `k` 순으로 앞에 세워 싣는 것이다(훑기를 놓쳐도 빠지지 않는다 — X1-11 과 같은 뿌리). 엔진은 어느 쪽이든 받고, 넘치면 꼬리를 제목으로 내리며 `meta.bg_dropped` 로 알린다. WP3b 가 정한다.
8. **`open-observation` 종류.** 지금 코퍼스에 0장이라 영향이 작다. 권고는 배경 카드다. 점검형으로 두려면 verdict 틀에 그 종류의 판정 뜻을 한 줄 더해야 한다.
9. **WP3b 가 읽는 이름 셋을 바꾼다.** `ctx_assumed` → `ctx_source`·`ctx_retrying`, `limits.verdict.unit_body_max` → 최상위 `unit_body_max`(종류별 값도 남긴다), `card_review_active` → `review_active`. 메인 에이전트가 WP2·WP3b 계획에 같이 적어야 한다.

## 실측이 필요한 값

| 값 | 어디서 재나 | 그때까지 내보내는 기본값 |
|---|---|---|
| 호출 초 p50·p95(sweep·verdict·offcard 따로) | M0-b, M2 | `DELIB_TIMEOUT_S` 1,800초 × 2 시도 + 8. 요청 최악 10,824초(앱 셀 벽시계는 이보다 커야 한다 — WP3b) |
| 글자/토큰 비 | M0-b(`meta.usage.tokens_in` 과 `prompt_chars`) | 거절 문턱은 1.05 · 0.93, `est_tokens` 는 `_est_tokens_all` |
| GLM 이 `max_tokens` 를 안 보낼 때의 실제 출력 상한 | M0-b(절단 비율·`finish_reason`) | `OUT` 16,000토큰 가정 → `K_out` 19 · 쪽당 단위 64 · `findings_max` 14 |
| 묶음 장수 K | M0-b 의 K 팔 {1, 4, 8, K_out}(함수를 직접 불러 고른다) | `CARD_REVIEW_K` 8 |
| 종류별 몫(SHARE) | M0-b·M2 의 `soft_over` 와 일치율 | verdict 0.25 · sweep 0.50 · offcard 0.30(넘어도 거절이 아니라 표지) |
| 보충 시도 수와 보충 비율 | M2(`quality.attempts`·`repaired`) | `CARD_REVIEW_PARSE_RETRIES` 2 |
| 동시 수가 챗에 주는 영향 | M2 의 챗 첫 응답 지연 | 4, 심의가 돌면 2 |
| GLM 응답에 `finish_reason`·`token_usage` 가 실리나 | M0-b | 못 읽으면 `truncated=null`·`usage=null`(0 으로 치지 않는다) |
| GLM 이 창 초과를 어떤 상태·문구로 거절하나 | M0-b(창 근처 프롬프트 한 번) | 400 + 추정이 창의 85% 이상이면 `context_overflow`, 그 밖의 400 은 `llm_rejected` |
| GLM 이 `<think>` 를 본문에 섞나 | M0-b | 파서가 늘 뗀다 |
| 순서 뒤집힘 비율(`fwd`·`rev`)·양성 비율·훑기 `rel=no` 비율·offcard `maybe_more` 비율 | M2 | 이중 판정 전량(PLAN 3절 M2 실행 설정) |
| 목록 항목 상한 | M2(훑기 품질) | `max(800, manifest_page_max // units_per_page_max)` — cae00 약 1,500자 |
| 접두 캐시가 보충 호출 비용을 줄이나 | M0-b | 없다고 보고 시도 상한 3 |
| 전문가별 카드 수·역할 문서 길이(cae00) | 팩 빌드 결과(M2) | 건수 천장 없음, 역할 전문 |
