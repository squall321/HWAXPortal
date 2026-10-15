# 화면 요청서 — 리스크 앱 M3(완결 표기 · 셀 처분 · 쟁점 · 종합 보고서)(HWAXRisk `frontend/` 세션에)

보내는 쪽: 백엔드 세션(포털 리포 `docs/risk-review-redesign/`) · 2026-10-15 · 대조한 코드는 HWAXRisk `a27e569`(가지 `m3`, main 합침 전). 계약은 [M3.md](M3.md) 4.10·4.11, [reference/m3-synthesis.md](reference/m3-synthesis.md) 3.8·3.11, [reference/m3-cells.md](reference/m3-cells.md) 3.7 이고, 아래의 칸 이름·값·경로·문구는 그 커밋의 코드에서 확인했다. 백엔드 칸이 들어간 커밋은 끝의 '반영' 에 적는다.

## 0. 먼저 — 모든 화면에 걸리는 것

- **대상.** 이 요청서의 칸은 카드 대조 대상(`flow='cells'`)에만 있다. 패널 대상의 응답은 M2 와 바이트로 같다(진행판의 `review` 칸만 M2 부터 있다).
- **M2 의 카드 대조 화면도 아직 없다.** 지금 `api/risk.api.ts` 는 셀·전문가·전문가 보고서·단위·검토 잡 경로를 부르지 않는다. 이 요청서는 그 위에 얹는 것이라 필요한 M2 경로도 함께 적고 표시를 단다 — **새**(M3 에서 생김) · **바뀜**(있던 경로에 칸·값이 더해짐) · **M2**(M2 부터 있고 화면에 아직 없음).
- **오류 본문.** `{error: {code, message}, …detail}` 이다(detail 칸은 최상위에 펼쳐진다). `message` 는 고칠 곳까지 말하는 한국어라 그대로 보이면 된다. 본문 모양 자체가 틀리면(예: 300자를 넘는 사유) FastAPI 기본 422 `{detail: […]}` 로 온다 — 글자 수는 화면이 먼저 막는다.
- **남의 것.** 과제 구성원이 아닌 사람에게는 모든 쓰기·읽기 경로가 '없는 것' 과 같은 404 다(문구에 과제 id 가 없다). 읽기(GET)는 지금 **대상 주인만** 연다 — 과제 구성원도 404 다(구성원 열람은 M4, 포털 context-notes D-53). 쓰기는 과제 편집자(editor) 이상이고 등급 미달은 403 `role_insufficient`, 완결 확인만 소유자·관리자다. 화면은 404 를 '없음', 403 을 '권한 없음' 으로 보이면 된다.
- **폴링.** 진행판(`GET …/coverage`)은 5초 폴링을 전제로 완결 캐시를 읽는다(원장을 다시 세지 않는다). 그 자리에서 다시 세는 것은 `GET …/closure?fresh=1` 하나이고 버튼으로만 부른다.
- **쪽을 잇는 목록.** 쟁점·등록부 응답에 `ledger_rev`(거른 목록 전체의 지문)가 온다. 앞 쪽과 다르면 그사이 원장이 바뀐 것이니 offset 0 부터 다시 받는다.
- 경로는 지금처럼 상대 `api/…` 다(앱 `/apps/hwax_risk/` 아래). 아래에서는 `/api/…` 로 적는다.

## 1. 대상 개요 — 완결 표기 · 사슬 단계 · 마지막 보고서 판

**왜.** M3 의 카드 대조 대상은 검토 잡이 마감 범위를 닫으면 쟁점 → 종합 보고서까지 사람 손 없이 이어 돈다(사슬). 지금 화면의 `LevelBadge(level)` 는 저장 레벨만 보여 '무엇이 남아 C3 가 아닌지' 를 말하지 못한다.

**백엔드가 주는 것 — 바뀜.** `GET /api/targets/{key}/coverage` 에 cells 대상만 칸 넷이 더해진다.

```text
level_label: string     // 완결 표기 "<레벨>(<막힌 까닭 · 잔여>)"
                        // 예 "C2 · C3 대기(입력 결손 110명·250셀(mem·pcb) · 미토의 쟁점 7건(주장 FAIL 7) · 2차 영향 미실행(넘김 0건 표만) · 결손 사냥 미실행)"
qualifiers: [{item, n, label, blocking, acked, basis_n, basis_hash, ack?: {state, by, at, reason}, …item 별 칸}]   // 6절의 표
stage: {mode: "issues" | "synth", job_id, state, hold_code, pause_reason, error, advice?} | null   // 살아 있는(없으면 마지막) 쟁점·종합 잡
report: {version_no, trigger, narrative_state, created_at} | null                                 // 마지막 종합 보고서 판의 머리
```

- `level` 은 저장 레벨이고 내려가지 않는다. `close_level` 은 이 판에서 cells 로 열거나 바꾼 대상이 `C3`, M2 때 cells 로 연 대상은 `C2` 그대로다.
- 맨 레벨 이름은 잔여가 0 일 때만 나온다. M3 의 cells 대상에는 '2차 영향 미실행' · '결손 사냥 미실행' 이 늘 붙어 맨 `C3` 가 나오지 않는다 — 최선이 `C3(2차 영향 미실행(넘김 N건 표만) · 결손 사냥 미실행)` 이다.
- 괄호 안에는 잔여 앞에 막힌 까닭이 먼저 선다 — `심사할 단위 없음` · `미배정 N` · `격자 결손 N셀` · `열린 셀 N` · `판정 누락 N셀` · `보고서 누락 N명` · `쟁점 진행 N건` · `깊이 미달 <영역> have/need` · `후속 낡음(쟁점 선정 전 | 재검토 N셀 | 셀 바뀜 | 종합 전 | 보고서 판)` · `재개방 N셀`. 머리 `C2 · C3 대기` 는 C3 조건은 다 됐는데 막음 잔여 확인을 기다린다는 뜻이고, `C2 · 마감 대기` 는 마감 레벨이 C2 인 대상의 같은 뜻이다.
- `stage.state` 는 `queued · running · paused · cancelling · completed · failed · cancelled` 다. `stage.error` 가 `pat_unavailable:` 로 시작하면 그 잡을 돌릴 사용자 PAT 가 없어 줄에서 집히지 않는다(PAT 를 등록하면 저절로 집힌다). `restart:` 로 시작하는 멈춤은 앱 재기동이 도는 쟁점 패널을 닫은 것이다 — 사람이 재개해야 한다(자동 재개는 M4). `draining:` 은 update-all 이 비우는 동안이다. `stage.advice == "issue_yield_low"` 는 최근 쟁점 패널 다섯이 전부 기각·판정 못 함이라는 알림이다(잡은 멈추지 않는다 — 계속할지 사람이 정한다).
- `report.trigger` — `reviews_partial`(좁은 범위 검토 뒤 — 마감 범위 미완) · `reviews_closed`(마감 범위 검토 끝) · `issues_closed`(쟁점 단계 끝) · `synth_done`(영역 요약·종합까지 끝) · `ack`(확인·확인 취소가 표기를 바꿈) · `manual`(사람이 다시 냄). `level_up` 은 어휘에만 있고 지금 세우는 곳이 없다. `narrative_state` 는 `none · partial · full`(LLM 서술이 붙은 정도 — 표·수는 늘 코드다).

**할 일**
- 대상 머리에 `level_label` 을 그대로 보인다(지금의 레벨 배지 옆). 막음 잔여 가운데 확인 안 된 것(`blocking && !acked`)이 있으면 6절 화면으로 가는 표지를 단다.
- 사슬 배지 — `stage` 로 '쟁점 패널 중 · 종합 중 · 멈춤(재개 버튼) · 끝' 을, `report` 로 '종합 보고서 v{version_no}' 링크(5절)를 보인다. 멈춘 사슬 잡의 재개는 지금의 `resumeJob` 그대로다.
- **M2 시절 잡 뒤의 사슬 시작.** M2 앱이 세운 검토 잡이 끝난 대상에는 쟁점·종합이 저절로 서지 않는다(사슬은 M3 코드가 세운 잡에서만 시작한다 — 포털 D-45 ④). Claude 길잡이는 그때 검토 잡을 한 번 더 세우게 한다(셀이 다 닫혀 있어 검토 호출 없이 곧바로 끝나고 그 끝에서 사슬이 선다). 화면에서는 `stage == null && report == null && review.job?.state == "completed" && review.cells.by_state.pending == 0` 이면 '쟁점·종합 시작' 버튼(3-1 의 `POST …/jobs {mode: "reviews"}`)을 보인다. 그 잡이 사슬 표지를 가졌는지는 칸으로 주지 않는다 — 더 정확히 가르려면 백엔드 세션에 칸을 청해 주십시오.

## 2. 진행판 — 검토 잡(`review` 칸)

**왜.** 전원(359명) 검토는 며칠 돈다. 거르기·입력 결손·다시 연 셀의 동의·관문 기다림이 진행판에 생겼고, 사람이 읽고 처분해야 하는 칸이다.

**백엔드가 주는 것.** `GET /api/targets/{key}/coverage` 의 `review`(cells 대상 — 검토 잡 전에도 있다).

```text
review: {
  units, cells{total, by_state, by_basis, in_scope, out_of_scope_pending, failed_open, form_only},   // M2
  experts{total, by_state}, cards, quality, order[…], job | null,                                     // M2
  dispositions: {retried, skipped},                                   // 새 — 사람이 다시 연 셀(그 뒤 입력이 안 바뀐 것) · 넘긴 셀
  filter: {mode: "off" | "shadow" | "on", approved: bool | null,      // 새 — 거르기(가장 최근 검토 잡이 얼린 값)
           would_filter, filtered, audited,
           audit{risk_miss, relevance_miss, undetermined, kept, upper95, upper95_conservative, n_audit, floor_met, pending},
           shadow{would_filter, sampled, risk_miss, upper95}, widened: [영역], off: bool, saved_calls_est},
  noinput: {experts, cells, by_outcome{impact, unknown, request, none}}   // 새 — 입력 결손
}
review.job: {id, mode: "reviews", state, hold_code, hold_until, hold_n, error, credential_email, scope, phase,
             progress{packs, experts, cells, calls, breaker, server, reopened_extra}, waiting, signal}   // M2 + 아래
```

- **바뀜 `review.job.phase`** — `live`(근거 꾸러미 실호출 — 단위마다 해석 보고서·재질 물성의 지금 상태를 사용자 PAT 로 한 번 얼린다) → `pack` → `review` 이고, 끝나면 그 상태 이름(`completed` 따위)이다. 잡 안에서도 전문가마다 단계가 따로 간다.
- **새 `review.job.progress.reopened_extra`** — 잡을 만들 때 동의받은 추정 밖에서 다시 연 셀(넓힘 · 늦은 넘김 · 보충 표본 · 살아 있는 잡에 얹은 사람의 다시)의 몫이다.
  `{cells, runs, calls_est, consented{cells, calls_est}, unconsented{cells, calls_est}, allowance, expected, max_calls, hold: null | "consent_extra" | "max_calls"}`. 여유 `allowance = max(ceil(0.2 × (expected + 동의한 몫)), 30)` 이다. 동의 안 받은 몫이 여유를 넘으면 잡이 `consent_extra` 로, 추정 합이 상한(`max_calls`, 기본 30,000)을 넘으면 `max_calls` 로 멈춘다(3-5).
- **바뀜 `review.job.hold_code`** — 새 코드 둘 `consent_extra` · `max_calls`(둘 다 자동 재개 없음). `error` 에 백엔드 문장이 실린다. 예 '다시 연 셀 N개(호출 추정 M회)가 여유 A회(동의받은 추정 E회의 20% · 최소 30회)를 넘었다 — 사람이 그 몫에 동의하면(재개 consent=true) 이어 돌고, 동의하지 않으면 그 셀을 넘긴다(넘김의 filter state=pending). 아무것도 차감하지 않았고 그 셀은 이 잡에 묶인 채 기다린다'. 나머지 보류 코드(user · credential · ctx_too_small · contract · llm_misconfigured · content_fail_rate · llm_outage · aidh_unreachable · agent_outdated · ctx_unknown)는 M2 그대로다.
- **바뀜 `review.job.waiting`** `{reason, since, retry_at, note?, source?}` — 새 이유 둘이다. 잡은 `running` 이고 보류가 아니다.
  - `health_unknown` — 앱이 에이전트 서버 `/health` 에서 카드 대조 관문을 읽지 못해 새 카드 대조 호출을 내지 않는다. 읽히면 저절로 이어 돈다.
  - `draining` — update-all 이 카드 대조를 비우는 중이거나 엔진이 비우기로 거절했다. 끝나면 저절로 이어 돈다.
  - 둘 다 `note` 에 백엔드 문장이 있고 '마감 · 근거 꾸러미는 그 사이에도 돈다' 로 끝난다.
- `review.cells.by_state` 의 `na_irrelevant` 는 '거름', `no_input` 은 '입력 결손 — 판정 못 함' 으로 보인다(상태 이름은 그대로다). `by_basis` 의 `unset` 은 지금 카드 0장 전문가의 긴 문서 발췌 셀(`search_only`)을 함께 센다 — 정확한 갈래는 `GET …/closure` 의 `counts.cells.reviewed_by_basis` 에 있다.
- `review.filter.approved` 는 그 잡이 만들 때 얼린 승인 문이다. 배정표가 초안인 동안 `false` 이고 그동안은 아무 셀도 걸러지지 않는다(`filtered` 0). `audit.upper95` 는 표본 놓침의 정확 이항 95% 상한(0~1, 표본이 없으면 null)이다.

**할 일**
- 거르기 줄 — '거름 {filtered}셀 · 표본 {audited} · 놓친 걸림 {audit.risk_miss} · 95% 상한 {upper95 × 100}%', `approved == false` 면 '배정표 승인 전 — 거르지 않는다'. `widened` 가 있으면 '넓힌 영역 …', `off` 면 '이 대상의 거르기를 껐다(넓힌 영역 셋 이상)'.
- 입력 결손 줄 — '입력 결손 {experts}명 · {cells}셀(영향 있음 {impact} · 모름 {unknown} · 확인할 것 {request} · 없음 {none})'.
- 처분 줄 — '사람이 다시 연 셀 {retried} · 넘긴 셀 {skipped}'.
- 잡 줄 — `phase`(live 는 '근거 꾸러미 실호출'), `waiting.note`(있으면 그대로), `reopened_extra.cells > 0` 이면 '다시 연 셀 N(추정 M회 · 여유 A회)', 보류면 `error` 와 3-5 의 재개·넘김 버튼.
- `progress.calls{ok, infra_fail, content_fail, wait, aborted, last_ok_at, avg_ok_s}`(M2)로 '호출 ok N / 추정 E' 와 남은 시간 어림을 보이면 며칠짜리 잡을 읽기 쉽다. 추정 E 는 `review.job.progress.reopened_extra.expected`(잡을 만들 때의 `calls_estimate.expected` — 진행판의 잡 줄에 실리는 유일한 자리)이고 거르기 없음 가정이라 실제보다 크다.

## 3. 셀 격자와 처분 — 다시 · 넘김 · 동의

### 3-1. 검토 잡 시작(M2 경로 · 바뀐 응답)

`POST /api/targets/{key}/jobs {mode: "reviews", scope?: {tiers?, domains?, agents?, unit_ids?}, user_memo?, consent?}` — `scope` 를 빼면 로스터 전원이다.

- 응답 `{job_id, mode, cells_total, cells_in_scope, experts_in_scope, units, calls_estimate{low, expected, high, basis}, credential{kind, email, exp}, undeferred, credential_note?}`. **바뀜** — `calls_estimate` 에 `expected` 와 한 줄 설명 `basis` 가 생겼고, 동의 문턱·상한은 `expected`(거르기 없음 가정)와 견준다. `undeferred` 는 범위 안에서 저절로 풀린 보류 좌석 수다.
- 동의 — `expected` 가 1,500(`HWAXRISK_REVIEW_CONSENT_CALLS`)을 넘으면 `consent` 없이는 422 `consent_required`(detail `{calls_estimate, knob}`)이고 **아무것도 바꾸기 전에** 온다. 그래서 동의 없이 한 번 불러 추정을 보이고, 사람이 동의하면 `consent: true` 로 다시 부르면 된다. `expected` 가 30,000(`HWAXRISK_REVIEW_MAX_CALLS`)을 넘으면 409 `review_too_large` 다 — 범위를 나눠 돈다.
- **없어진 거절** — 422 `input_gap_m3`. 입력 결손 전문가(ECAD 에 기대는데 ECAD 가 없다)도 범위에 들고, 그 셀은 판정 대신 입력 결손 두 질문으로 닫힌다.
- 그 밖의 거절은 M2 그대로다 — 409 `review_disabled` · `review_job_exists` · `review_in_flight` · `panel_job_running` · `repersist_pending`, 422 `units_absent` · `scope_invalid` · `scope_empty` · `pat_unavailable`.

### 3-2. 셀 격자(M2 경로 · 칸이 더해짐)

`GET /api/targets/{key}/cells?agent_key&unit_id&domain&state&job_id&route&limit(기본 500, 최대 2000)&offset` → `{target_key, total, limit, offset, next_offset?, rows[]}`.

- **새 쿼리** `route = review | filtered | audit | noinput`(거르기 분류의 길).
- **새 행 칸** `filter_reason` — 두 신호가 다 무관이라 거른(거를 수 있던) 셀만 한 줄이고 아니면 null 이다. 꼴은 `코드 신호 무관(관련 영역 xd·sim) · 훑기 무관 «…»` 이다(«» 안은 훑기 까닭 80자를 위생 처리한 LLM 글).
- 행에 이미 있는 열 가운데 M3 에서 뜻이 생긴 것 — `route`(review · filtered · audit · noinput) · `route_forced`(거르지 않은 까닭 — rank1 · global_unit · no_cards · input_gap · widened · filter_off · handoff · human_retry · tier_a_pending · filter_audit · filter_floor) · `basis`(cards · background · role_only · search_only · noinput) · `status_source` · `decided_by` · `decided_at` · `decide_note`(사람의 처분) · `reopened_n`.
- 셀 하나 `GET /api/targets/{key}/cells/{unit_id}/{agent_key}`(M2)도 `cell.filter_reason` 을 싣는다.

### 3-3. 다시(retry) — 새

`POST /api/targets/{key}/cells/retry`

```text
{cells?: [[unit_id, agent_key], …] | filter?: {job_id?, agent_key?, unit_id?, domain?, error_code?, state?},
 reason?: string(4~300), force?: false, start?: true, consent?: false}
→ {target_key, matched, retried, not_failed, keys_total, keys[≤50], experts, changed, audit_id,
   job: {action: "created" | "adopted" | "waiting" | "none", job_id?, calls_estimate?, adopted?, waiting?, hold?}}
```

- `cells` 와 `filter` 가운데 정확히 하나를 준다. 기본은 `failed` 셀만 다시 연다. `force: true` 면 `reviewed` · `no_input` 도 다시 열고(그 셀의 판정 행을 지운다) 사유가 필수다 — 엔진 판이 오르기 전에 끝난 셀을 새 판으로 다시 볼 때 쓴다. **Claude 의 `risk_job_action(retry_failed)` 에는 force 가 없다** — force 다시는 이 화면이 유일한 길이다.
- 대상이 아닌 셀은 `not_failed` 로 세고 손대지 않는다. 바꿀 것이 없으면 200 `changed: false` 다.
- `job.action` — 살아 있는 검토 잡의 범위가 그 셀을 덮으면 `adopted`(그 잡이 집는다 — `hold` 가 실리면 그 셀 몫 때문에 그 잡이 멈췄다, 3-5), 덮지 않으면 `waiting`(다음 잡이 집는다), 살아 있는 잡이 없고 `start` 면 다시 연 셀만 묶은 검토 잡을 만든다(`created` — 추정도 그 셀만이고 동의 문턱은 3-1 그대로다), `start: false` 면 `none`.
- 거절 — 422 `cells_selector_invalid`(둘 다 · 둘 다 없음 · 모르는 칸 · 격자에 없는 셀 — detail 에 `unknown_keys` · `cells` 따위), 422 `reason_required`(detail `{min: 4, max: 300, chars}`), 422 `consent_required`(**아무것도 바꾸기 전에** — 추정을 보이고 동의를 받아 `consent: true` 로 다시), 409 `review_too_large`, 그리고 3-1 의 잡 거절들(잡을 만들다 거절되면 처분도 되돌린다).

### 3-4. 넘김(skip) — 새

`POST /api/targets/{key}/cells/skip {cells? | filter?, reason: string(4~300, 필수)}` → 3-3 과 같은 꼴(`retried` 대신 `skipped`, `job.action` 은 `created` · `adopted` · `none`, 더해 `job.resumed?`)에 걸림 셈이 붙는다.

```text
hits: int | null, hits_by: {card, offcard, noinput} | null, hits_basis: "members" | "pack_missing", hits_note?: string
```

- `failed → skipped` 만이다. 그 전문가는 다시 마감되고 보고서 '보지 못한 것' 에 '넘김 — «사유»' 로 남는다. 넘긴 셀이 이미 받은 걸림은 버리지 않고 '넘긴 셀 — 일부만 판정' 으로 보고서·finding 에 남는다 — `hits` · `hits_by` 가 그 수다(카드 판정 · 카드 밖 지적 · 입력 결손 영향 있음).
- **새 `hits_basis: "pack_missing"`** — 얼린 카드 묶음이 이 박스에 없는 전문가(들여온 원장)라 지금 셀 수 없다. `hits` · `hits_by` 가 null 이고 `hits_note` 가 까닭이다 — **0 이 아니라 '모름'** 으로 보여 주십시오.
- 다시 연 셀 몫으로 멈춘 잡에서 동의를 기다리는 셀도 넘길 수 있다(`filter: {state: "pending"}` — 그 셀은 `failed(consent_declined)` 를 거쳐 차감 없이 `skipped` 가 된다). 몫이 여유 안으로 돌아오면 그 잡이 이어 돌고 응답에 `job.resumed: true` 가 실린다.

### 3-5. 동의 — 재개와 넘김

- 잡이 `hold_code: "consent_extra"` 로 멈췄으면 `reopened_extra` 의 기다리는 셀 수(`unconsented.cells`)와 추정 호출(`unconsented.calls_est`)을 사람에게 보이고, 동의하면 **`POST /api/jobs/{id}/resume?consent=true`**(새 쿼리)로 재개한다. 동의 없이 재개하면 422 `consent_required`(detail `{reopened_extra}` — 아무것도 바꾸지 않는다)다. 동의하지 않으면 3-4 의 넘김(`filter: {state: "pending"}`)이다.
- `hold_code: "max_calls"` 면 동의로 풀리지 않는다 — 재개는 409 `max_calls`(detail `{reopened_extra, knob: "HWAXRISK_REVIEW_MAX_CALLS"}`)다. 기다리는 셀을 넘기거나 운영자가 상한을 올린 뒤 재개한다. 이때 화면은 재개 버튼 대신 넘김 버튼을 앞에 둔다.
- 사람이 멈췄거나 자격 보류인 잡도 몫이 넘쳐 있으면(`reopened_extra.hold` 가 있고 `hold_code` 와 다르다) 재개에 같은 동의가 든다 — 보류 코드가 아니라 `reopened_extra.hold` 로 판단한다.
- 일시정지 · 재개 · 취소(`POST /api/jobs/{id}/{pause | resume | cancel}`)는 잡 주인(대상 주인)만이다 — 다른 사람은 구성원이어도 404 다. 멈추지 않은 잡의 재개는 409 `E100` 이다.

### 3-6. 보류 풀기 — 새(패널 대상 전용)

`POST /api/targets/{key}/undefer {reason: string(4~300)}` → `{target_key, undeferred, agents[≤50], agents_total, changed, level, note, depth}`.

- 패널 대상(검토를 얹은 대상 포함)의 보류(`deferred`) 좌석을 사람이 푼다. cells 대상은 검토 잡을 만들 때 범위 안 보류가 저절로 풀리므로 이 버튼이 필요 없다.
- 그 대상에 도는 잡이 있으면 409 `job_live` 다. 응답의 `note` 는 '저장된 레벨은 내려가지 않는다 — 푼 좌석이 영역 깊이의 분모에 든다(depth).' 다.

### 3-7. 전문가 보고서(M2 경로)

`GET /api/targets/{key}/experts`(머리 목록) · `GET /api/targets/{key}/experts/{agent_key}/report?format=md&part=summary|units|cards|full&page&version`(쪽)은 M2 그대로다(보고서 판 `expert-report-2`). M3 의 표지 — '거름 — 까닭' · '넘긴 셀 — 일부만 판정' · '다툼 표지 — 두 번째 판정 못 함' · '문맥 줄을 댔다(그 단위 소속 줄이 아니다)' · '긴 문서 검색 못 함(search_failed — 역할만으로 답했다)' · 입력 결손 절 · '실호출 근거(tool:b-…)는 지금 상태다 — 스냅샷 뒤에 바뀌었을 수 있다' — 는 md 쪽 글에 한국어로 이미 들어 있다. `format=md` 쪽을 그대로 그리면 따로 할 일이 없다(`format=json` 을 직접 그린다면 finding 의 `partial_cell` · `conflict_unjudged`, 입력 결손 줄의 `ref_context` 를 보인다).

**할 일(3절 전체)**
- 셀 격자 화면 — 전문가 × 단위 칸에 상태(거름 · 입력 결손 표기 포함)와 `filter_reason` 말풍선, `route` 거름 칩, `state=failed` 거름.
- 고른 셀(또는 '이 잡의 실패 셀 전부' = `filter: {job_id, state: "failed"}`)에 '다시'·'넘김'. 넘김과 force 다시는 사유 입력 필수(4~300자). `consent_required` 를 받으면 `calls_estimate.expected` 와 `basis` 를 보이고 동의를 받아 다시 보낸다.
- 넘김 응답의 `hits` 를 '이미 판정된 걸림 N(카드 a · 카드 밖 b · 입력 결손 c)' 으로, `pack_missing` 이면 `hits_note` 를 보인다.
- 잡이 `consent_extra` · `max_calls` 로 멈췄으면 3-5 의 재개(동의)·넘김(기다리는 셀) 두 버튼.

## 4. 쟁점 — 새

**왜.** 검토가 마감 범위를 닫으면 코드가 쟁점(hold 가 FAIL 을 가린 클러스터 · 한 사람만 중대 이상으로 본 클러스터 · 같은 줄에 OK 를 낸 다른 전문가가 둘 이상인 클러스터)을 골라 쟁점 패널(3라운드 심의)로 다시 본다. 패널 결론이 원판정을 덮되 원래 분포를 같은 줄에 남긴다(사용자 결정 D-34). 상한 밖은 '미토의' 로 남고 사람이 올리거나 건너뛸 수 있다 — 그 길은 웹뿐이다(Claude 에 쓰기 도구가 없다).

**백엔드가 주는 것.**

`GET /api/targets/{key}/issues?state=a,b&p_class=P1&type=held_fail&limit=100(최대 500)&offset=0`

```text
{target_key, total, limit, offset, next_offset?, ledger_rev, cap: {base: 24, hard: 48, run},
 rows: [{issue_id, rank, types[], p_class, priority, anchor_cluster_key, unit_id, state, state_reason, outcome, outcome_json,
         distribution: {raisers, raisers_by_domain{}, by_judgement_claimed{}, by_severity{}, opposers},
         panel_id, seats: [{key, domain, issue_role}], selected_round, attempts, charged, reargue}]}
```

- 순서는 `issue_id` 다(쪽을 잇는 안정 열쇠). 선정 순위는 행의 `rank` 이니 순위대로 보이려면 화면이 정렬한다.
- `types` ⊂ `held_fail`(hold 가 가린 FAIL · 치명 주장) · `solo_severe`(한 사람만 중대 이상) · `split_verdict`(같은 줄에 OK 를 낸 다른 전문가 2명 이상). `p_class` — `P1`(검증된 FAIL · 치명) · `P2` · `P3`.
- `state` — `queued · planned · running · resolved · inconclusive · untried_cap · withdrawn · skipped`. `state_reason` — `cap`(상한 밖) · `engine_fail` · `job_failed` · `chain_cancelled` · `spec_parse_failed` · `no_decision` · `no_matching_atom` · `human` · `reraised`.
- `outcome` — `upheld` · `downgraded` · `escalated` · `rejected` · `undetermined`. 보고서는 '유지 · 하향 · 상향 · 기각 · 판정 못 함' 으로 쓴다. `outcome_json` = `{panel_id, atom_finding_ids[], severity_after, judgement_after, grade_after, contest_note}`.
- `seats[].issue_role` — `raiser`(제기) · `opposer`(반대) · `adjacent`(인접 영역).
- **`reargue`(새)** — null 이거나 `{label, at, round, basis_hash, panel_basis_hash, raisers_added[], raisers_removed[], opposers_added[], opposers_removed[], claimed_before{}, claimed_after{}, new_panel_failed?}` 다. 패널이 판정한 뒤 근거(제기 · 반대 · 주장값)가 바뀐 쟁점이다. `label` 은 '패널 판정 — 근거 바뀜, 다시 토의 필요' 이고 새 패널이 결정을 못 내면 '(새 패널 결정 못 함)' 이 붙는다. 새 패널이 정할 때까지 옛 판정(`outcome`)이 그대로 보인다.
- `cap.run` 은 지금까지 돌았거나 도는 쟁점 패널 수다. P1 을 48 까지 먼저, P2 · P3 은 합계가 24 에 닿을 때까지 돈다(P1 이 24 를 넘으면 P2 · P3 은 돌지 않는다).

`PUT /api/issues/{issue_id} {action: "queue" | "skip", reason: string(1~300)}` → `{issue_id, state, job_id}`

- `queue` — 상한 밖(`untried_cap`)이나 끝난 쟁점을 다시 줄 세운다(상한을 넘기는 사람의 결정이고 내용 탓 셈을 0 으로 돌린다). 살아 있는 쟁점 잡이 없으면 잡을 세운다(`job_id`). `skip` — 건너뛴다(`skipped` — 완결 잔여 '미토의 쟁점' 에 든다, `job_id` null).
- 거절 — 409 `issue_in_flight`(편성 · 도는 쟁점은 바꾸지 않는다), 422 `reason_required`(빈 사유), 422 `E100`(모르는 action), 403 `role_insufficient`(편집자 미만), 404 '쟁점을 찾을 수 없습니다 — {id}.'(없거나 남의 것). 사유 300자 초과는 FastAPI 422 다.
- 사람의 결정은 다음 자동 고르기가 바꾸지 않는다.

쟁점 패널 자체는 `GET /api/targets/{key}/panels?kind=issue`(**바뀜** — 행에 `kind`(coverage · issue)와 `issue_id`, 쟁점 패널의 `tier` 는 `"I"`)와 `GET /api/panels/{id}/transcript`(그대로)다. 쟁점 패널은 포털 대화를 만든다(`conv_id`).

**할 일**
- 대상 화면에 쟁점 탭 — 행마다 '제기 N명(판정별 분포) · 반대 M명 → 쟁점 패널 <결과>', 상태와 사유, `reargue.label` 이 있으면 굵게, 패널 발언 링크.
- 상한 밖 · 끝난 쟁점에 '올리기' · '건너뛰기'(사유 입력 필수), 편성 · 도는 쟁점에는 버튼을 끈다.
- 쪽을 이을 때 `ledger_rev` 가 바뀌면 처음부터 받는다.

## 5. 종합 보고서 — 새

**왜.** 사슬의 단계마다 앱이 보고서 판을 세운다(앱 사본이 정본 — RA 투영은 M4). 표 · 수는 코드이고 서술만 LLM 이다.

**백엔드가 주는 것.**

`GET /api/targets/{key}/report?part=summary&page=1&version=<n>&format=md`

```text
// 머리(쪽마다 같다)
{target_key, version, report_uid, title, level_label, narrative_state, trigger, counts, created_at,
 format: "md", part, pages_total, page_no, next_page?,
 page: {page_no, kind: "synthesis_report", title, blocks: {background[], results[], recommendation[], minutes[]}}}
// format=json — 판 전체
{…머리, format: "json", pages: [{page_no, kind: "summary" | "domain" | "mechanisms" | "appendix", title, blocks{…}}]}
```

- `part` — `summary`(본문 — 완결 · 잔여 · 수 · 종합 서술 · 주의 A 전부 · B 상위 30 · 개선 · 넘김 · 쟁점 결과 / 판정 후보 · 미토의 쟁점 · 카드 FAIL 수 · 정보 요청 / 쟁점 패널 · 영역 × 셀 상태 · 거름 표본 · 품질 · 사람 확인) · `domains`(로스터 영역마다 한 쪽) · `mechanisms` · `appendix`(전문가 색인 — 로스터 전원 한 줄씩) · `full`.
- blocks 의 값은 **마크다운 줄 배열**이다. md 쪽 하나에는 블록 하나만 차 있다(블록이 바뀌는 자리에서도 쪽을 나눈다). 쪽을 차례로 이으면 그 part 전체다 — 자르지 않는다.
- **지금 판만 읽힌다.** `version` 은 고르는 칸이 아니라 대조 칸이다 — 첫 쪽의 `version` 을 둘째 쪽부터 실어 보내면 그사이 새 판이 섰을 때 409 `report_version_moved`(detail `{version, asked}`, 글 '보고서 판이 {asked} 에서 {version} 로 바뀌었다 — 처음 쪽부터 다시 받는다.')로 알려 쪽이 섞이지 않는다.
- 판이 없으면 404 `report_absent`('이 대상에는 종합 보고서 판이 아직 없다 — POST /targets/{key}/report 로 만든다.')다. 모르는 part · format · page 는 422 `E100` 이다.
- `title` 은 `리스크 심사 보고서 v{n} [{level_label}] — {target_key}` 이고, 근거 등급이 전부 경험칙이면 앞에 `[가설 단계]` 와 빈칸 하나가 붙는다.
- 서술이 없으면 본문에 굵게 '서술 없음 — 까닭 글(까닭 코드)' 이 선다. 까닭 — `no_rows`(이 영역이 제기에 참여한 클러스터가 없다) · `content_fail` · `infra_exhausted` · `ctx_too_small` · `checks_failed`.

`POST /api/targets/{key}/report {refresh_summaries: false | true}`(편집자 이상)

- `false` — 지금 원장으로 코드 조립 판을 그 자리에서 세운다 → `{target_key, report_uid, version_no, pages_n, level_label, counts, narrative_state, created}`. 직전 판과 내용이 같으면 새 판을 만들지 않고 `created: false` 로 그 판을 돌려준다.
- `true` — 종합 잡(영역 요약 → 과제 종합 → 판)을 세운다 → `{target_key, job_id, credential, error?}`. 사용자 PAT 가 없으면 잡은 서고 `error: "pat_unavailable: …"` 가 실린다(등록하면 집힌다). **살아 있는 종합 잡이 있어도 새 잡을 세운다** — `stage.mode == "synth"` 가 살아 있는 동안은 버튼을 꺼 주십시오.
- 거절 — 422 `flow_mismatch`(패널 대상), 409 `project_purged`(폐기된 과제), 404 · 403 은 0절 규칙.

**할 일**
- 보고서 화면 — part 탭(본문 · 영역 · 메커니즘 · 부록), 쪽 넘김(`next_page`), 둘째 쪽부터 `version` 을 실어 보내고 409 면 1쪽부터 다시. 줄 배열을 마크다운으로 그린다.
- 머리에 `title` · `trigger` · `created_at`, `narrative_state != "full"` 이면 '서술 일부 · 없음 — 표는 다 있다'.
- '다시 내기'(코드 조립 판)와 '요약부터 다시'(종합 잡) 두 버튼.

## 6. 완결과 확인 — 새

**왜.** 잔여(입력 결손 · 실패 · 넘김 · 미토의 쟁점 · 다시 토의 · 거름 · 품질 …)가 남으면 레벨이 오르지 않거나 표기에 붙는다. 막음 잔여는 소유자 · 관리자가 사유와 함께 확인해야 C3 로 오른다. 확인 길은 웹뿐이다(Claude 에 쓰기 도구가 없다).

**백엔드가 주는 것.**

`GET /api/targets/{key}/closure?fresh=0|1`

```text
{target_key, flow: "cells", level, previous_level, raised, close_level, level_current, regressed, level_label, c1, c2, c3,
 qualifiers: [{item, n, label, blocking, acked, basis_n, basis_hash, ack?: {state: "valid" | "stale" | "revoked", by, at, reason}, …}],
 counts: {roster, units{reviewable, excluded_by_reason, unassigned}, cells{expected, actual, by_state, reviewed_by_basis, verdict_gaps},
          experts{…, reports{expected, ready, partial, blocked, missing}}, filter{…}, failed{…}, skipped{…}, no_input{…},
          issues{by_state, by_outcome, p1{…}, held_fail{…}, open, cap{base, hard}}, registry{clusters, attention{A, B, C, D}, card_fail_claimed},
          handoffs{lines, pairs}, mechanisms_reported{codes, free}, quality{out_of_bounds[], strong_ratio_cells}, invariants[]},
 roster_size, status_counts, unseated_n,
 detail: {depth{<영역>: {active, have, need, cardless, exempt?}}, strong_ratio_cells, skipped_ratio, cells_hash, fresh{…}},
 acks: [{item, ack_at, ack_by, ack_reason, basis_n, basis_hash, revoked_by, revoked_at, state: "valid" | "stale" | "revoked"}]}
// 패널 대상은 패널 판정 응답에 flow: "panels" 가 붙는다
```

잔여 낱말 — 응답의 차례 그대로다.

| item | label 꼴 | 막음 | 더 실리는 칸 |
|---|---|---|---|
| `input_gap` | `입력 결손 {명}명·{셀}셀(<영역 전원이 결손인 영역>)` | 늘 | `experts` · `domains` |
| `failed` | `실패 {n}셀` | 늘 | `by_code` |
| `skipped` | `사람 넘김 {n}셀(몰림 {k}칸)` | 늘 | `crowded[]` |
| `issues_untried` | `미토의 쟁점 {n}건(주장 FAIL {k})` | 늘 | `p1` · `held_fail` · `sentences[]`('전문가 N명이 FAIL 로 봤으나 미토의') |
| `issues_reraised`(**새**) | `패널 판정 — 근거 바뀜, 다시 토의 필요 {n}건` | 늘 | `issue_ids[≤20]` |
| `filtered` | `거름 {n}셀(표본 S · 놓친 걸림 M · 95% 상한 X%)` | 표본 바닥 미달 · 상한 5% 초과 · 대상의 거르기 끔이면 | `audit` |
| `unit_excluded` | `부분 캡처 — 제외 {n}건` | 늘 | `by_reason` · `others` |
| `quality` | `검토 품질 기준 밖 {n}항` | 늘 | `out_of_bounds` · `strong_ratio_cells` |
| `undetermined` | `보류 {n}/{of}({%})` | 20% 초과면 | `of` · `ratio` |
| `no_cards` | `카드 0장 {n}명` | 표기 | — |
| `depth_no_cards` | `카드 없는 영역 — 역할 판단만 · {영역…}` | 표기 | `domains` · `mixed` |
| `cross_not_run` | `2차 영향 미실행(넘김 {n}건 표만)` | 표기(M3 에서 늘 있다) | `pairs` |
| `mech_not_run` | `결손 사냥 미실행` | 표기(M3 에서 늘 있다) | — |

`POST /api/targets/{key}/closure/acks/{item} {reason: string(1~300), basis_hash}` → `{item, ack_at, ack_by, basis_hash, basis_n, level, level_label, report_version}`

`DELETE /api/targets/{key}/closure/acks/{item}` → `{item, revoked_by, revoked_at, level, level_label, report_version}`

- `basis_hash` 는 지금 읽은 그 잔여 행의 값을 그대로 보낸다. 그사이 잔여 집합이 바뀌었으면 409 `residual_changed`(detail `{item, basis_hash, basis_n}` — 지금 값, 글 '그 사이 잔여가 바뀌었다 — 다시 읽고 확인한다.')다 — 다시 읽어 사람에게 보이고 다시 확인받는다.
- 확인 뒤 집합이 바뀌면(실패가 하나 늘었다 따위) 그 확인은 `stale` 이 되고 그 잔여는 다시 막는다. 취소는 행을 지우지 않고 표기한다.
- 거절 — 422 `ack_not_allowed`(막음 잔여가 아니거나 패널 대상 — 글 '확인으로 넘길 수 있는 막음 잔여가 아니다 — {item}.'), 422 `reason_required`(빈 사유), 403 `role_insufficient`(편집자 · 보기), 404(남 · 없는 대상), DELETE 의 404 '취소할 확인이 없습니다 — {item}.'. 300자 초과는 FastAPI 422 다.
- **새 `report_version`** — 확인과 확인 취소는 둘 다 보고서 판(`trigger: "ack"`)을 세우고 그 판 번호를 돌려준다. 내용이 같으면 앞 판 번호이고, 판 조립이 실패하면 null 이다(확인 자체는 섰다).

**할 일**
- 완결 화면 — `level_label`, 잔여 표(label · 막음/표기 · 확인 상태와 확인한 사람 · 사유 · 시각), C1 · C2 · C3 조건(`c1` · `c2` · `c3`, `detail.depth` 의 영역별 have/need), `regressed` 면 '지금 계산 {level_current} — 저장 레벨은 내려가지 않는다'.
- 막음이고 `acked` 가 아닌 잔여마다 '확인'(사유 입력 필수 · `basis_hash` 그대로), 확인된 것에 '확인 취소'. 응답의 `level_label` 로 머리를, `report_version` 으로 보고서 링크를 고친다.
- '다시 세기' 버튼 = `?fresh=1`.

## 7. 등록부 — 바뀜

`GET /api/targets/{key}/registry?status&severity&domain&attention=A,B&unit_id&source=panels&offset` → `{target_key, rows[], truncated, total, next_offset?, ledger_rev, verdict_candidate, verdict_final}`

- **새 쿼리** `attention`(쉼표로 여럿) · `unit_id`(그 단위가 제기에 든 행) · `source=panels`(패널 finding 만으로 다시 센 비교 보기 — 저장하지 않는다, 패널을 돌린 뒤 cells 로 바꾼 대상의 '바꾸기 전 등록부') · `offset`. 모르는 source 는 422 `E100` 이다. REST 는 한 번에 전부를 준다(쪽 나누기는 MCP 만).
- **새 행 칸**(v5 열 일곱 — cells 대상에서 뜻이 있고 패널 대상에서는 참고값) — `support_experts` · `support_domains` · `support_units` · `support_verified`(서로 다른 제기 전문가 · 영역 · 단위 · 검증된 인용을 낸 전문가 수), `attention`(`A · B · C · D` — **읽는 순서이지 판정이 아니다**), `issue_id`, `issue_state`(`queued · planned · running · upheld · downgraded · escalated · rejected · undetermined · untried_cap · skipped · withdrawn`).
- **`merged` 에 더한 칸**(cells 대상) — `claimed{judgement, severity, sev3, fail_experts, critical_experts, verified_fail_experts}`(hold 가 등록부를 WARNING · 중대로 묶어도 원래 주장값) · `distribution{by_judgement_claimed, by_severity, raisers_by_domain}`(전문가 수로 센 분포) · `unit_ids[]` · `before_issue{severity, sev3, judgement, evidence_grade, claimed, distribution, support_*}`(쟁점 패널이 행을 덮기 전 값 — 덮였을 때만) · `issue_reraised{label, …}`(4절의 다시 토의 표기).
- 정렬 — cells 대상은 주의 등급 → 우선순위 → 지지 영역 수 → 지지 전문가 수 → 키이고, 패널 대상은 그대로다.
- 카드 인용은 판정당 200자이고 원래 길이가 `<칸>_chars` 에 있다(M2 규칙이 `merged_json` 까지 넓어졌다).

**할 일**
- 등록부 표에 주의 등급 열과 지지 수(전문가 · 영역 · 단위 · 검증)를 더하고, 쟁점 패널이 덮은 행은 한 줄에 '원래 — 제기 N명(FAIL a · WARNING b) → 쟁점 패널 <결과>' 를 함께 보인다(D-34 '덮되 분포를 남긴다'). `issue_reraised` 가 있으면 그 표기.
- 주의 등급 거름(A · B 를 기본으로), 단위 거름, '패널만 본 비교 보기' 토글(`source=panels`).

## 8. 짓지 않는 것

- 순수 Claude 길(잡 옵션 `llm` · `consent_external`, 보류 `external_worker`, 보고서 '판단 LLM' 줄)은 이 판에 없다(포털 D-48 — M3 뒤, 기본 꺼짐). 화면에 자리를 만들지 않는다.
- MCP 만의 줄이기(등록부 행의 `merged_json` 빼기와 `merged.lists_total`, 진행판 잔여의 `<칸>_n`, 잡 범위 · 워커의 앞 몇)는 REST 에 없다 — 화면은 REST 의 전부를 받는다.
- 쟁점 올리기 · 건너뛰기, 완결 확인, force 다시는 Claude 에 길이 없다 — 이 화면이 유일한 길이다.

## 반영

- 백엔드 칸이 들어간 커밋 — HWAXRisk 가지 `m3`(2026-10-14~15, 대조 `a27e569` — main 합침 · push 는 조정자 몫).
  - 완결 판정과 진행판의 `level_label` · `qualifiers` — `d72d5ea` · `ecd1a47` · `5f483fc`(S3-8). 진행판의 `stage` · `report` — `7bdb60c`(S3-5).
  - 쟁점 · 보고서 REST — `4238a08`(S3-10). 영역 요약과 종합 보고서 — `11eff6d`(S3-9). `issue_yield_low` — `65d1f20`.
  - 셀 처분(다시 · 넘김) — `0cb3e2d`(C3-4). 전원 포함 · 보류 풀기 — `77ec171`(C3-2). 거르기 보이기(`filter_reason` · `review.filter` · `review.noinput`) — `66fd395`(C3-8). `calls_estimate.expected` · 동의 — `a63124a`(C3-10). 근거 꾸러미 실호출과 단계 `live` — `669c4df`(C3-12).
  - 반대 검토 뒤 — `ledger_rev` · 쟁점 id 순 `f6642f2`, 확인의 `report_version` `821d2c2`, 남에게 없는 것과 같은 404 `c68fd8d` · `49a1e26` · `8053ebe`, 쟁점 행 `reargue` `5ab3c10`, 다시 연 셀 몫(`reopened_extra` · `consent_extra` · `max_calls` · 재개 `?consent`) `f4117ba` · `c294c33` · `cac80b6`, 넘김의 `hits_basis: "pack_missing"` `4a34feb`, `waiting.reason` 의 `health_unknown` · `draining` `8d8d14b`.
- 화면을 내보내면 백엔드 세션에 알려 주십시오. 포털 절차서(`server-setup-m3.md` 5 · 6절)의 '웹 화면이 생기기 전에는' 문장을 고친다.
