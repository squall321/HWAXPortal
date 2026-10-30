# 10-30 HA-27 · HA-28 · HA-29 · HA-30 설계 맞물림 — 래퍼 차례 · 합치는 차례 · 어긋남

> 대상 설계서 [`design-ha27.md`](design-ha27.md) · [`design-ha28.md`](design-ha28.md) · [`design-ha29.md`](design-ha29.md) · [`design-ha30.md`](design-ha30.md),
> 요청서 정본 [`../request_261030.md`](../request_261030.md), 판단 기록 [`context-notes.md`](context-notes.md).
> 코드 대조는 10-30 읽기 전용으로 했다 — 에이전트 서버 dev `7ca3a2e`(main)와 이미 있는 형제 가지 `wt1030/ha08 · ha26r · ha31 · ha33 · ha34 · vocab`,
> 포털 `bf5cd94`(main)와 가지 `wt1030/ops · seed · ua · vocab` 이다. 줄 번호는 dev 의 것이다. 이 문서는 통합 판단만 적고 리포 코드는 고치지 않았다.

## 0. 한 줄

- 네 설계는 `_cap_tool.capped` 안의 차례에 이미 같은 답을 냈다(유령 ID → HA-30 → HA-29 → 인자 기본값 → 부르기 → HA-28 → 접기 · 자르기 → 배우기).
  어긋남은 차례가 아니라 그 둘레에 있다. 성공 길 열 줄(app.py 2002-2013)을 다섯 가지(HA-27 · HA-28 · HA-30 · 이미 있는 HA-34, 거절 꼴은 HA-29)가 함께 고치고,
  턴 머리 한 줄(4842 `_turn_tool_calls.set(Counter())` 바로 뒤)을 넷이 고친다.
- 합치는 차례는 작은 가지(HA-34 · HA-26r · HA-31 · HA-32 …) → 동작이 같은 골격 커밋 하나 → HA-30 → HA-28 → HA-29 → HA-27 이다(10절).
- 네 설계 어디에도 없던 일을 9절에 적었다. 무게가 큰 셋은 서버가 직접 건 잡(카드 승인 · 확정 종결 · 새어 나온 호출)의 born 배우기,
  카드가 선 턴의 헛기다림(최대 600초), 기존 시험 묶음의 격리(conftest)다.

## 1. 이미 있는 가지와 겹침

| 리포 · 가지 | 행 | 고친 곳 | 네 설계와 겹치는 곳 |
|---|---|---|---|
| 에이전트 `wt1030/ha34` | HA-34 | `_fold_hub_result(name, text, via)` · `capped` 성공 길 두 갈래의 접기 호출 · `/health hub_fold` | 성공 길 열 줄(HA-27 · HA-28 · HA-30 이 같은 줄을 고친다) · `/health` |
| 에이전트 `wt1030/ha26r` | HA-26 재시도 몫 | `_turn_msgs(merged=)` · 턴 `except`(5317) 안 자동 재시도 | HA-29 가 같은 `except` 머리에 '카드가 섰으면 재시도 대신 카드' 를 더한다 |
| 에이전트 `wt1030/ha31` | HA-31 | `is_agent_search(pinned)` · `chat()` · `_denied_feature` | HA-29 가 `chat()` 띵킹 갈래 앞에 카드 답 갈래를 더한다 — `_denied_feature` 도 같은 판정이어야 한다(8절 C-10) |
| 에이전트 `wt1030/vocab` | HA-32 | `_core_rules_text` · README | HA-30 이 바로 아래 `_core_vocab().build`(323)에 `hubs` 를 더한다 — 덩이가 따로라 겹침은 작다 |
| 에이전트 `wt1030/ha33` · `ha08` | HA-33 · HA-08 | VOC 미리보기 · deliberation.py | 없다 |
| 포털 `wt1030/ops` | HP-53 · HP-51 · AD-21 | `he-team.json` 의 `writes` · `confirm` · `sync-he-personas.py` | HA-29 가 읽는 목록이다 — 빈 곳 넷(8절 C-15) |
| 포털 `wt1030/ua` | HP-55 | update-all §7 | HA-27 Q12 의 §7 줄은 이 가지가 든 뒤에 더한다 — 이 가지에는 없다 |
| 포털 `wt1030/vocab` · `seed` | HP-56 · HA-32 · HP-52 | `core_vocab.json` · 절차 씨앗 | 없다(HA-30 `hubs` 는 apps 의 role 만 읽는다) |

## 2. `capped` 안의 한 차례

모든 행이 이 차례를 따른다. 막는 걸음(G)은 부르기 전에 글을 돌려주고, 결과 걸음(R)은 성공한 호출에만 돈다.

```text
capped(*a, _hwax_rc: RunnableConfig = _NO_RC, **kw)          # HA-28 — 기본값을 None 으로 두지 않는다(3.10 Optional 함정)
  G1 invoke_tool 안쪽 거부(_agent_denied)                       기존
  G2 외부 응답자 · 반출 동의 거부(_agent_external_call)          기존 — 여기서 _via_inv 를 정한다
  G3 유령 ID — 정수(_turn_ids)                                  기존
  G4 다른 허브 id — UUID(_cross_hub_id_msg)                      HA-30
  G5 확인 카드(_confirm_gate)                                    HA-29
  G6 챗 인자 기본값(_CHAT_ARG_DEFAULTS)                          기존
  C  out = await orig(*a, **kw) — 예외면 ✖ 글로 끝(아래를 타지 않는다)   기존
  R1 _eff(경유면 안쪽 이름)                                       기존
  R2 _status_wait — 상태 도구 · chat 이면 기다림(멈춤 술어를 본다),
     상태 도구가 아니면 born 배우기(턴 상태만 있으면 chat 과 상관없이)   HA-28 · 8절 C-3 · C-4
  R3 _head, _tail = _chat_result_note(_eff, polled=…) if chat     기존 · HA-28
  R4 _pair · raw = _norm(out[0] if _pair else out) — 한 갈래        골격(HA-27 의 8)
  R5 _sc_keep_raw(raw)                                           HA-27
  R6 body = _maybe_repair_hint(_cap(_fold_hub_result(_eff, raw, _via_inv), result_max))   기존 · HA-34
  R7 _learn_ids(body) · _learn_hub_ids(_eff, body)                기존 · HA-30
  R8 머리 + body + 기다림 안내 + 꼬리 — pair 면 (글, out[1])          HA-28
```

| 걸음 | 행 | 도는 때 | 막으면 모델이 받는 것 | 막은 호출의 회계(8절 C-6) |
|---|---|---|---|---|
| G1 · G2 | 기존 | 늘 | ✖ 거절 글 | 그대로 |
| G3 | 기존 | `_turn_ids` 가 있을 때 | `_PHANTOM_ID_MARK` 글 | blocked 로 센다 · 근거 블록에 남는다(지금) |
| G4 | HA-30 | `_turn_hub_ids` 가 있을 때 | `✖ … 는 다른 허브의 id 다 …` | **blocked 로 세게 바꾼다** · 근거 블록은 지금처럼 |
| G5 | HA-29 | `_turn_confirm` 이 있고 손잡이 켬 | `✖ … [확인 대기] …` · `ctx.pending` 에 쌓는다 | blocked 로 센다 · 근거 블록 · turn_out 에서 뺀다(설계대로) |
| R2 기다림 | HA-28 | `chat=True` 이고 턴 상태가 있을 때 | 마지막 결과 + `[코드 기다림 — …]` | — |
| R2 born | HA-28 | 턴 상태가 있을 때(래퍼 종류와 상관없이) | — | — |
| R5 | HA-27 | 원문 그릇이 있을 때(자기검증 켬 · 관문 켬) | — | — |

- G1 ~ G5 의 반환 꼴 `(msg, None) if response_format == "content_and_artifact" else msg` 는 지금 네 번 되풀이되고 두 번 더 는다. 골격 커밋에서 `_refuse(tool, msg)` 하나로 둔다.
- G3 · G4 · G5 는 모두 '고칠 것은 인자다 · 사람이다' 의 차례다. 인자가 틀린 호출(G3 · G4)에 카드를 띄우면 사람이 틀린 대상을 승인하므로 G5 가 마지막이다(HA-29 · HA-30 설계 같음).
- R2 의 다시 조회는 `orig` 를 같은 인자로 직접 부른다. G1 ~ G6 을 다시 지나지 않고, 접기 · 절단 · 원문 붙잡기 · 배우기는 마지막 결과에 한 번만 걸린다.
- 승인 실행(HA-29 5.4)은 `deliberation._tools_by_name` 의 `chat=False` 래퍼를 지난다. G1 ~ G4 를 다시 지나고 G5 는 승인 열쇠로 통과하며, R2 는 born 만 배우고, R5 · R7 은 그대로 돈다.
- `_hwax_rc` 는 이름 있는 인자라 G1 ~ G5 의 인자 순회(`kw` 와 `a` 안의 dict)에 들지 않고 `orig` 로도 새지 않는다. `deliberation._svc_fallback.guarded(*a, **kw)` 로 다시 싼 도구
  (`_tools_by_name` 의 사용자 토큰 길 · `svc_fallback=True`)는 LangChain 이 설정을 넣지 않지만, 그 길(`chat=False`)에서는 기다리지 않으므로 상관없다(사건을 낼 곳이 없을 뿐이다).

## 3. 턴 상태 — 한 자리

네 행의 문맥 변수는 `_agent_stream_turn` 의 `_turn_tool_calls.set(Counter())`(4842) 바로 뒤, 재촉 → 이어하기(4846)가 `req.message` 를 바꾸기 **전**에 한 덩이로 건다.
HA-29 의 주문 판정이 원문 발화를 봐야 하므로 이 자리가 맞다.

```python
_turn_ids.set(_seed_ids)
_turn_tool_calls.set(Counter())
# ── 10-30 턴 상태 — 재촉 → 이어하기가 req.message 를 바꾸기 전에 건다(HA-29 판정은 원문을 본다)
_turn_hub_ids.set({} if _XHUB_GATE else None)                                    # HA-30
_turn_status_wait.set(_status_wait_mod.new_turn() if _status_wait_mod.on() else None)   # HA-28
_turn_confirm.set(_confirm_ctx(req) if CHAT_CONFIRM_GATE else None)              # HA-29 — 앞 카드의 승인 · 거절도 여기서 가린다
_turn_sc_raw.set(_sc_raw_box() if box is not None else None)                     # HA-27 — 자기검증 감싸개가 준 턴만
```

| 문맥 변수 | 행 | 값 | None 이면 | 읽는 곳 |
|---|---|---|---|---|
| `_turn_hub_ids` | HA-30 | `{uuid: {apps, hub, tool, key, type, label}}` | 막지도 배우지도 않는다 | G4 · R7 |
| `_turn_status_wait` | HA-28 | `{born, seen, spent_s}` | 기다리지 않고 born 도 없다 | R2 |
| `_turn_confirm` | HA-29 | `_ConfirmCtx(utterance, pinned, approved, used, pending, …)` | 관문이 서지 않는다 | G5 · 턴의 끊기 · 카드 · R2 의 멈춤 술어 |
| `_turn_sc_raw` | HA-27 | `{texts, chars, partial}` | 붙잡지 않는다 | R5 · 턴 끝 `box["raw"]` |

- 턴은 `_pinged_stream` 의 태스크 하나(`chat-turn`)가 끝까지 돌려 문맥 변수가 걸음마다 남는다. 도구 코루틴은 복사된 문맥에서 같은 객체를 고쳐 턴이 그 변경을 본다(`_learn_ids` 와 같은 길).
- 심의 · 띵킹 · 분석 루틴 · 카탈로그 · VOC 미리보기는 이 함수를 지나지 않아 넷 다 None 이다. 네 관문은 챗 ReAct 턴에만 선다.
- 턴 끝 `box.update`(5685)는 한 줄로 합친다 — `box.update(draft=text, calls=…, outputs=…, raw=_turn_sc_raw.get(), confirm=ctx.card if ctx else None)`.

## 4. 스트림 사건

| 사건 | 행 | 꼴 | 자기검증 감싸개 | 포털 중계 · 서버 사본 | 화면 |
|---|---|---|---|---|---|
| `status`(tool=null · `wait{phase, tool, state, progress, detail, elapsed_s, max_s, polls}`) | HA-28 | 진행 줄 — 낱말이 바뀌면 곧바로, 같으면 30초에 한 번 | 그대로 지난다 | `tool` 이 없어 활동에 남지 않는다(routes.py 2691) | step 만 상태 줄 · 활동 목록(10분에 20줄 남짓) |
| `status` '확인 대기: X'(tool=X · ok=false · call) | HA-29 | 막은 호출의 '도구 완료' 자리 | 지난다 | 활동에 실패로 남고 절차 원장에 실패 단계로 든다 · 다음 턴 근거에 '[호출 실패]' 로 | 활동 패널 |
| `confirm`(새 이름) | HA-29 | `{id, expires_at, calls[], approve_text, decline_text}` | 붙잡지 않고 지난다 | 바이트 그대로 넘기고 따로 남기지 않는다 — 카드 글은 `result` 로 서버 사본에 든다 | `dispatch` 에 `case 'confirm'` · `ConfirmCard` |
| `status` 승인 실행(call=`cf-…-n`) | HA-29 | '도구 호출 · 완료' 짝 | 지난다 | 활동 · 절차 원장에 보낸 호출로 | 종전과 같다 |
| `meta.self_check` | HA-27 | 상태 `flagged` 새것 · `flags` · `dropped` · `gate` | 감싸개가 만든다 | `meta` 는 서버 사본에 남지 않는다(지금도) | `CheckNote` 의 flagged 갈래(포털 후속) |
| HA-30 막음 | HA-30 | 기존 '도구 완료' ok=false | 지난다 | 활동에 실패로 | 종전과 같다 |

- 새 사건 이름은 `confirm` 하나다. 지금 이름(status · token · result · delib · think · tools · agents · warning · reasoning · meta · user_images · routine · error · done · ping)과 겹치지 않는다.
  HA-28 의 사용자 사건 `hwax_status_wait` 는 서버 안에서 `status` 로 바뀌어 밖으로 나가지 않는다(`hwax_loop_fit` 과 다른 이름).
- 카드 턴의 사건 차례 — `confirm` → (자기검증 켬이면 초안은 '생각' 칸) → 카드 글이 든 본문 `token` → 근거 블록 → `meta` → `result` → `done`.
- 에이전트 `/chat` 스트림을 읽는 것은 포털 중계 하나다(포털 백엔드 `routes.py` 만 부른다 · 에이전트 MCP 서버는 `/chat` 을 읽지 않는다 — 10-30 grep). 다른 소비자를 고칠 일이 없다.

## 5. `/health`

자리는 `self_check`(7220) 다음부터 한 줄씩이다. 같은 줄에 둘이 붙지 않게 아래 차례로 넣는다.

| 칸 | 행 | 내용 | 비고 |
|---|---|---|---|
| `self_check` | HA-27 | 기존 칸 + `fixed_ratio` · `gate{mode, turns, reviewer_fixed, raw_partial, counts}` | 상태 `flagged` 는 `counts` 에 키 이름 그대로 |
| `status_wait` | HA-28 | `on · poll_s · max_s · waits · ended · capped · failed` | 자물쇠는 HA-34 `hub_fold` 꼴 |
| `confirm_gate` | HA-29 | `on · lists{loaded, error, jobs, writes, confirm} · pending · counts{…}` | `lists.loaded` 가 거짓이면 바닥 목록만 돈다 |
| `xhub_gate`(권장 — 8절 C-8) | HA-30 | `on · blocked` | 손잡이를 끈 박스를 밖에서 가린다 |
| `core_vocab` · `tool_cut` · `hub_fold` | 기존 · HA-34 | 그대로 | `hub_fold` 는 `tool_cut` 뒤(HA-34 가지) |

`tests/test_health_contract.py` 는 칸을 골라 보므로 칸을 더해도 깨지지 않는다(10-30 대조).

## 6. 포털 — 중계 · 화면 · 설정 · 문서

- **중계는 네 행 모두 고치지 않는다.** `confirm` 은 바이트 그대로 지나고, tool 이 없는 status 는 활동에 남지 않는다(4절).
- **화면은 HA-27 과 HA-29 둘이 같은 파일을 고친다** — `frontend/src/types/chat.ts`(SelfCheck 상태 · ConfirmCard 형) · `components/chat/MessageList.tsx`(CheckNote · 카드 줄).
  한 포털 가지(`wt1030/chatui`)에서 둘을 함께 하고 빌드는 한 번(`pnpm build` + Drive)이다. 계약 시험(`test_confirm_front.py` 가 형제 리포 `app.py` 의 `_sse("confirm"` 를 읽는다)이
  붉지 않게 에이전트 main 에 HA-29 · HA-27 이 든 **뒤**에 합친다.
- **update-all §7** — HA-27 의 관문 줄(Q12)은 `wt1030/ua`(HP-55)에 없다. 그 가지가 든 뒤 한 커밋으로 `self_check.gate · fixed_ratio`, `status_wait`, `confirm_gate`(목록을 못 읽었으면 ⚠),
  `xhub_gate` 줄을 함께 더한다. 꺼진 것은 ○ 와 '켜려면' 으로 적는다(안 켠 기능도 로그에 — 사용자 지시 09-25).
- **env 킷**(`infra/env-kits/agent-server.env` 챗 절) — 주석 손잡이를 한 커밋으로 넣는다. `CHAT_SELF_CHECK_GATE` · `CHAT_SELF_CHECK_RAW_CHARS`(HA-27),
  `CHAT_STATUS_WAIT_MAX_S` · `CHAT_STATUS_WAIT_POLL_S` · `CHAT_STATUS_TOOLS`(HA-28), `CHAT_CONFIRM_GATE`(HA-29 — 설계 파일 목록에 빠졌다), `CHAT_XHUB_ID_GATE`(HA-30).
- **업데이트 이력은 `backend/config/changelog.yaml`** 맨 위다. HA-28 · HA-29 설계가 적은 `docs/changelog.md` 는 적는 법 안내서다(8절 C-7).
- **공유 문서**(`docs/request-1030/checklist.md` · `context-notes.md` · `server-setup.md`, 에이전트 `README.md`)는 워크트리에서 고치지 않는다. 넷이 같은 파일을 고치면 합칠 때마다 충돌한다.
  합치는 세션이 행을 합칠 때마다 한 번 쓴다(C-6 의 일하는 방식과 같다). `server-setup.md` 는 아직 없다 — 첫 합침에서 만든다.

## 7. 시간 한도 층 — 네 행을 합친 모습

| 층(안 → 밖) | 값 | 행 · 자리 |
|---|---|---|
| 다른 허브 id 검사 · 배우기 | 수 ms(망 없음 — 맵 캐시 · 어휘표 stat) | HA-30 |
| 자기검증 관문 계산 | 스레드 두 번 · 최악 1 ~ 1.5초 | HA-27 |
| 카드 작업량 묻기(목록 받기 + `estimate_cost`) | 15초 | HA-29 |
| 허브 MCP → 허브 백엔드 | GET 60 · POST 120초 | StandardPlatform |
| 다시 조회 한 번 | ≤ min(120, 남은 몫)초 | HA-28 |
| 게이트웨이 도구 호출 | 600초(전송 660) | gateway.py 188 |
| 엔진 MCP 요청 | `MCP_CALL_TIMEOUT_S` 900초 | app.py 129 |
| 턴의 기다림 합 | `CHAT_STATUS_WAIT_MAX_S` 600초 | HA-28 |
| 검토자 LLM | `LLM_TIMEOUT_S` 900 × (1 + 재시도) | 그대로(HA-27 은 다시 묻지 않는다) |
| 챗 스트림 침묵 신호 | ping 15초 · 기다림 진행 줄 ≤ 30초 | app.py 1188 · HA-28 |
| 포털 챗 중계 침묵 | 900초 | 포털 config.py 313 |
| 카드 수명 | 1800초 = `AGENT_CACHE_TTL_S` = 포털 PAT 창 | HA-29 |
| nginx `/agent/` · 챗 PAT | 50400 · 86400초 | 그대로 |
| 턴 단계 | `AGENT_RECURSION_LIMIT` 80(연속 왕복 39) | HA-30 막음은 왕복 하나 · HA-29 는 끊는다 · HA-28 기다림은 호출 하나 |

- 안쪽이 먼저 걸리는 차례는 합쳐도 지켜진다. 새 값은 HA-28 의 120 · 600, HA-29 의 15 · 1800 뿐이고 모두 바깥 층보다 작거나(호출 쪽) 같은 창(카드 수명)에 맞췄다.
- 한 턴의 벽시계 상한은 여전히 없다. 최악은 기다림 600초 + 모델 호출들 + 검토자 한 번이고, ping 과 진행 줄이 중계 900초를 막는다.
- `DELIB_HEARTBEAT_S=0` 박스에서는 HA-28 의 진행 줄만 중계를 살린다. 다시 조회 한 번(≤ 120초) 동안은 진행 줄이 없어 침묵이 최대 150초다(< 900).
- 승인 실행은 보통 호출과 같은 층(600 · 900)이다. `recipe_run` 은 제 `wait_sec`(기본 200) 안에 돌아온다.
- 자동 재시도(`agent.ainvoke`, HA-26r 가 고치는 길)에서 상태 도구가 기다리면 화면에는 재시도 줄과 ping 뿐이다(진행 줄을 받을 `astream_events` 가 없다). 남은 몫은 턴 상태라 600초를 두 번 쓰지 않는다.
- 카드가 선 턴에 같은 단계의 상태 도구가 기다리면 카드는 그 기다림이 끝나야 선다(최대 600초). 8절 C-4 가 이것을 다음 조회 앞(≤ 10초)으로 줄인다.

## 8. 어긋남과 권장 결정

| # | 무엇이 어긋나나 | 권장 |
|---|---|---|
| C-1 | 성공 길 열 줄(2002-2013)을 HA-27(갈래 합치기 · 원문 붙잡기) · HA-28(polled · 안내) · HA-30(배우기) · HA-34(via)가 함께 고친다. 따로 파면 합칠 때마다 같은 덩이가 충돌한다 | HA-34 를 먼저 합치고, 동작이 같은 **골격 커밋** 하나를 main 에 둔 뒤 네 워크트리를 그 위에서 판다 — `_refuse(tool, msg)` · `_pair`/`raw = _norm(…)` 한 갈래 · `_eff` 한 번 · 2절의 걸음 자리 주석 · 3절의 턴 상태 자리 주석. 시험은 test_request_1029(W-5) · test_hub_fold_stats · test_external_llm_risk_gate · test_chat_self_check |
| C-2 | 턴 머리 한 줄(4842)을 넷이 고친다 | 3절의 차례로 한 덩이에 둔다. HA-29 판정이 원문을 보도록 재촉 → 이어하기 앞이다 |
| C-3 | born — HA-28 은 `chat=True` 래퍼에서만 배우고, HA-29 는 '합칠 때 승인 실행 결과를 born 에 한 줄로' 를 권한다. 둘 다 확정 종결(5516) · 새어 나온 호출 직접 실행(5604)을 빠뜨린다 — 그 길로 걸린 잡도 born 이 없다 | HA-28 의 글루를 **턴 상태가 있으면 래퍼 종류와 상관없이** 부르고, 기다림만 `chat=True` 로 묶는다. 승인 실행 · 확정 종결 · 새어 나온 호출이 함께 덮이고 HA-29 쪽 따로 한 줄은 두지 않는다. 심의 엔진은 턴 상태가 None 이라 그대로다 |
| C-4 | 카드가 선 턴의 기다림 — HA-29 는 같은 단계가 끝난 뒤 다음 모델 호출 앞에서 끊으므로, 같은 단계의 상태 도구가 기다리면 카드가 최대 600초 늦게 서고 그 기다림의 결과는 모델이 끝내 보지 못한다 | HA-28 고리에 **멈춤 술어**(`stop()`)를 둔다. 잠 · 다시 조회 앞마다 보고 참이면 접는다(취소처럼 계수에 넣지 않는다). 글루가 `lambda: bool(getattr(_turn_confirm.get(), "pending", None))` 을 넘긴다 — HA-29 가 들기 전에는 늘 거짓이다. `status_wait.py` 는 app 을 읽지 않으므로 술어를 인자로 받는다 |
| C-5 | 시험 격리 — HA-29 는 형제 리포 파일(`he-team.json`)을 읽는 새 경로 설정이고 바닥 목록 24개는 파일이 없어도 돈다. HA-28 은 상태 도구가 '도는 중' 을 주면 10초씩 잔다. 둘을 켠 채면 HA-28 의 실턴 시험 14(`run_checklist` → `get_task`)가 HA-29 를 합친 뒤 카드로 끝난다 | 루트 `conftest.py` 가 `CHAT_CONFIRM_GATE=0` · `CHAT_STATUS_WAIT_MAX_S=0` 을 import 전에 걸고(`CHAT_SELF_CHECK=0` 과 같은 까닭 — 턴 시험이 호출 수 · 글을 센다), 자동 고정물로 `CONFIRM_LISTS_PATH` 를 '없음' 으로 돌린다(코어 어휘표 `_no_core_vocab` 와 같은 꼴 — 메모리 '새 경로 설정은 시험 격리에도'). 각 행 시험은 제 손으로 켠다. 두 행을 함께 켠 시험은 11절 I-1 |
| C-6 | 막은 호출의 회계가 셋이 다르다 — 유령 ID 는 `_budget["blocked"]` 에 세고 근거 블록에 남기며, HA-29 는 세고 근거에서 빼고, HA-30 은 표지가 달라(`_PHANTOM_ID_MARK` 를 일부러 싣지 않는다) 세지 않는다. 그래서 다른 허브 id 로 막힌 호출 하나뿐인 턴은 '도구를 썼다' 로 읽혀 강제 재시도 · 확정 종결이 서지 않는다 | `on_tool_end`(5274)의 blocked 판정에 HA-30 표지(`_XHUB_ID_MARK`, 글 머리 400자)를 더한다. 근거 블록에 막은 호출을 남기는 일은 HA-30 Q10 대로 이번에는 그대로 둔다(유령 ID 와 함께 따로 볼 일) |
| C-7 | 업데이트 이력 자리 — HA-28 · HA-29 는 `docs/changelog.md`, HA-30 은 `backend/config/changelog.yaml` | `backend/config/changelog.yaml` 이 정본이다(안내서 `docs/changelog.md` 의 '항목 추가하기'). KST 날짜 · 큰따옴표 · 기술 항목까지(메모리 '이력에 기술 변경도 전부') |
| C-8 | 밖에서 보는 흔적 — HA-27 · HA-28 · HA-29 는 `/health` 칸을 두고 HA-30 은 로그 한 줄만 둔다. `CHAT_XHUB_ID_GATE=0` 인 박스를 밖에서 가릴 길이 없다 | HA-30 도 `/health.xhub_gate = {on, blocked}` 를 둔다(카운터 하나와 손잡이 값). 재시험의 로그 줄 확인은 그대로다 |
| C-9 | 손잡이를 읽는 때 — HA-27 은 턴마다(`CHAT_SELF_CHECK` 꼴), HA-28 · HA-29 · HA-30 은 기동 때(`CHAT_STABLE_PREFIX` 꼴) | 그대로 둔다. `server-setup.md` 에 한 표로 '바꾸면 재기동이 필요한가' 를 적는다 |
| C-10 | HA-29 는 카드 답을 `chat()` 의 띵킹 갈래 앞에서 일반 챗으로 보낸다. `_denied_feature` 는 '트리거 순서는 chat() 과 같다' 인데 고치지 않는다 — `req.thinking` 이 참인 채 온 카드 답이 권한 판정에서는 띵킹으로 읽힌다 | 카드 답 판정 함수 하나를 `chat()` 과 `_denied_feature` 가 함께 부른다(HA-31 가지가 `is_agent_search(pinned=)` 로 세운 같은 원칙). HA-31 을 먼저 합치고 그 위에서 고친다 |
| C-11 | 승인 실행의 자격 — HA-29 는 `_tools_by_name(app, groups, user=, user_pat=)` 를 기본값으로 부른다. 기본 `svc_fallback=True` 는 사용자 토큰이 거절되면 서비스 계정으로 다시 보낸다 | 승인 실행은 `svc_fallback=False` 로 받는다. 사람이 승인한 잡 · 쓰기가 말없이 다른 자격으로 나가지 않는다(RA 위임 사고 교훈). 거절이면 설계 5.4 의 '보내지 못했다 → 다시 카드' 길로 간다. 작업량 묻기(읽기)는 기본값 그대로 |
| C-12 | 승인 실행은 챗 래퍼가 아니라 챗 인자 기본값(`_CHAT_ARG_DEFAULTS`)을 타지 않는다. 지금 표는 `plm_defect_search`(읽기) 하나라 갈리지 않는다 | 정규 열쇠는 설계대로 기본값 앞 인자로 재고, 승인 실행이 보낼 때 같은 표를 `_arg_defaults_for` 로 더한다 — 표가 잡 도구로 늘어도 처음 호출과 같은 꼴이 나간다 |
| C-13 | HA-27 의 수 뽑기가 시스템 글의 수를 근거로 센다 — UUID 의 첫 묶음이 숫자로 시작하면 그 숫자(0 ~ 99)가 작은 정수로 새고(`(?<![A-Za-z0-9_.])` 가 `-` 뒤를 막지 않는다), HA-30 거절 글은 JSON 이 아니라 그 수가 '강한 수' 가 된다. 유령 ID · 카드 · ✖ 실패 글도 근거가 아닌데 사본(outputs)으로 색인에 든다 | `sc_gate` 의 가림(6.1 의 1)에 UUID 꼴과 `cf-[0-9a-f]{12}` 를 더하고, `_result_ok` 가 거짓인 사본은 색인에서 뺀다(HA-30 이 오류 결과를 배우지 않는 것과 같은 까닭). `sc_gate` 는 app 을 읽지 않으므로 `app._UUID_RE` · `app._CF_ID_RE` 와 같은 꼴인지 시험 하나로 묶는다 |
| C-14 | 카드 턴의 근거 블록 — 카드 글의 예상 작업량(예 '약 1,812초')은 `estimate_cost` 결과가 turn_out 에 없어 '출처 없는 수' 로 찍힌다(100 넘는 수만 — `sig_numbers`) | 근거 블록의 수 대조는 카드 글을 뺀 답으로 한다(`box["confirm"]` 의 글을 떼고 대조 · 붙이기는 그대로) |
| C-15 | HP-53(포털 `wt1030/ops`)이 HA-29 가 기대한 넷을 갖추지 않았다 — ① `risk_job_action`(리스크 잡 취소 · 재개)이 어느 목록에도 없다(HA-29 Q11), ② 운영자 프롬프트 두 줄(sync-he-personas.py `build_prompt` 의 '요청했을 때만' · '확인을 받은 뒤')이 그대로라 관문이 켜진 박스에서 '글로 묻고 → 응 → 카드' 의 이중 확인이 된다, ③ 미리보기의 거꾸로 점검('목록에 있는데 게이트웨이가 읽기로 확인' — 에이전트의 접미 맞추기 `_named` 기준)이 없다, ④ HA-30 8.4 의 예 `failuretrace_relation_add` 는 목록에 없다(허브 쓰기는 object_create · update 등 일곱뿐 — relation_* · bulk_edit · object_restore · alias_candidate_apply 는 목록 밖) | ops 가지에 후속 커밋 하나 — ① `he-expert-risk` confirm 에 `risk_job_action`, ② confirm 줄을 '부르면 서버가 확인 카드로 사람의 승인을 받는다 — 글로 따로 묻지 말고 무엇을 왜 하는지 한 줄 말한 뒤 부른다. 확인 방법은 시스템 규칙을 따른다' 로 — 관문이 꺼진 박스는 HA-29 가 시스템 넷째 규칙을 옛 글('먼저 확인하고 호출')로 되돌리므로 운영자 글이 그 규칙을 가리키게 맺는다, ③ 거꾸로 점검 줄, ④ 허브 쓰기 넷은 cae00 미리보기의 '목록 밖 쓰기' 줄을 보고 사람이 정한다(지금은 묻는다). 맞물림 시험 I-3 은 목록에 있는 `failuretrace_object_update` 로 쓴다 |
| C-16 | 공유 문서 · env 킷 · 에이전트 README 를 넷이 저마다 고친다(설계 파일 목록) | 워크트리는 코드 · 그 행의 시험 · 설계서만 고친다. 공유 파일은 합치는 세션이 한 번 쓴다(6절) |
| C-17 | 화면 두 행(HA-27 flagged · HA-29 카드)이 같은 파일을 고치고, 계약 시험이 형제 에이전트 리포를 읽는다 | 한 포털 가지에서 에이전트 main 합침 뒤에 한다 · 빌드 한 번(6절) |

## 9. 네 설계 어디에도 없는 것

1. 서버가 직접 건 잡의 born — 승인 실행 · 확정 종결 · 새어 나온 호출 직접 실행(C-3).
2. 카드가 선 턴의 헛기다림 — 같은 단계의 상태 도구 기다림이 카드를 최대 600초 늦춘다(C-4).
3. 기존 시험 묶음의 격리 — HA-29 의 형제 파일 경로 · 기본 켬 관문 · HA-28 의 기본 600초 기다림이 남의 턴 시험에 새고, HA-28 시험 14 가 HA-29 뒤 카드가 된다(C-5).
4. `_denied_feature` 와 `chat()` 의 카드 답 판정 맞추기(C-10).
5. 승인 실행의 자격 강등 막기(`svc_fallback=False`, C-11).
6. HP-53 후속 넷 — `risk_job_action` · 운영자 프롬프트 두 줄 · 거꾸로 점검 · 허브 쓰기 넷의 자리(C-15). 그리고 ste 의 쓰기 `set_job_sync` 는 운영자도 바닥 목록도 없어 관문 밖이다(HP-54 가 조건부라 그 결정 전까지 남는다 — `ste_cancel_job` 은 접미 `cancel_job` 으로 confirm 에 걸린다).
7. update-all §7 의 새 `/health` 줄(관문 · 기다림 · 카드 목록 · 다른 허브 id) — HA-27 만 말했고 HP-55 가지에는 없다(6절).
8. 자기검증의 짚은 곳은 서버 사본에 남지 않는다 — 포털 중계가 `meta` 를 저장하지 않아(지금도) 다른 기기 · 서버 사본으로 연 대화에는 `flags` 가 없다. 브라우저 저장(chatStore)은 `meta` 를 통째로 남기므로 QA 용 `dropped` · `gate` 는 저장할 때 빼기를 권한다(쿼터).
9. DW-02 재시험의 길이 바뀐다 — '체크리스트 돌려서 결과 알려줘' 는 HA-29 의 `_ORDER_RE` 에 걸리지 않고(이어 주는 꼴 '돌려서' 를 받지 않는다 — 10-30 그 정규식으로 돌려 봤다),
   잡 부류의 '그 일을 글자로 불렀다' 도 채우지 못해(도구 이름 `run_checklist` · 무엇 칸 값이 말에 없다) 카드가 먼저 선다. 승인 → 승인 실행 → born → 첫 `get_task` 부터 기다림이 기대값이다. `server-setup.md` 의 DW-02 · DW-03 후속 절차에 카드 단추 한 번을 적는다. 잡 이름의 한국어 별칭(체크리스트 → `run_checklist` 등)을 둘지는 cae00 `/health confirm_gate.counts` 를 보고 정한다(지금은 두지 않는다 — HA-29 의 엄한 쪽 선택).
10. 개인 Claude(게이트웨이 MCP 직결) · 분석 루틴 · 띵킹 · 심의 좌석에는 네 관문이 모두 없다 — 설계가 범위 밖으로 둔 것이다(루틴 단계는 게이트웨이 읽기 울타리, 좌석은 읽기 허용 목록). 허브 오류 문구 청은 HA-30 Q9 대로 `outbound.md`(사람이 보냄)로 간다.

## 10. 구현 · 합치는 차례

| 걸음 | 무엇 | 왜 이 차례인가 · 그 합침이 맡는 맞물림 |
|---|---|---|
| 0 | 에이전트 작은 가지 — `wt1030/ha34` → `ha26r` → `ha31` → `vocab`(HA-32) → `ha33` · `ha08`. 포털 — `wt1030/ops` → `seed` → `ua` → `vocab` | `ha34` 가 성공 길을, `ha26r` 가 except 를, `ha31` 이 `chat()` · `_denied_feature` 를, `vocab` 이 `_core_vocab` 둘레를 먼저 고친다 — 네 행이 그 위에서 판다 |
| 1 | 골격 커밋(에이전트 main, 동작 불변) | C-1 · C-2. 그 뒤 네 워크트리(`wt1030/ha27 · ha28 · ha29 · ha30`)를 판다 |
| 2 | HA-30 | 가장 작고 사건 · 화면이 없다. `_UUID_RE` · 허브 도우미를 먼저 세워 HA-27(C-13)이 같은 꼴을 쓴다. C-6 · C-8 을 이 합침에서 |
| 3 | HA-28 | born API · 멈춤 술어 자리(C-3 · C-4)를 HA-29 가 잇는다. 술어 기본값은 늘 거짓이다. `_TOOLS_MAP_CACHE["routine_read"]` 는 `.get` 으로 읽는다(`tests/test_tools_map_retry.py` 가 그 칸 없는 사전으로 통째로 바꿔 끼운다) |
| 4 | HA-29 | C-4 술어 연결 · C-5 conftest · C-10 · C-11 · C-12 · C-14. 맞물림 시험 I-1 · I-2 · I-3 · I-7. HA-26r 뒤라 except 머리의 카드 끝맺음이 `_merged` 재시도 앞에 선다 |
| 5 | HA-27 | 마지막 사본 꼴(HA-28 안내 · HA-29 승인 결과와 카드 · HA-30 거절 글)이 다 선 뒤에 가림(C-13)과 E 시험을 맞춘다. `capped` 쪽은 골격 위 두 줄이다. 맞물림 시험 I-4 · I-5 · I-6 |
| 6 | 에이전트 전체 회귀 한 번 → push | 리포마다 한 번에 하나 · 회귀 도는 동안 커밋하지 않는다 · 결과는 파일로 받고 rc 를 따로 본다(메모리 '파이프가 시험 실패를 가린다') |
| 7 | 포털 — ops 후속(C-15) → `wt1030/chatui`(HA-29 카드 + HA-27 flagged) → §7 줄 · env 킷 · `changelog.yaml` · 공유 문서 → 포털 전체 회귀 → `pnpm build` + Drive → push | 화면 계약 시험이 에이전트 main 을 읽으므로 6 뒤 |
| 8 | cae00 — update-all 한 번에 에이전트 · 게이트웨이 · 포털이 함께 든다(사람 몫) | `server-setup.md` 에 12절 |

- HA-27 이 먼저 끝나면 먼저 합쳐도 된다. 이 차례는 의존이 아니라 '누가 맞물림을 맡나' 다 — 그때는 뒤에 드는 행이 HA-27 의 E 시험을 다시 돌리고 C-13 의 가림을 마저 맞춘다.
- 워크트리에서는 그 행의 시험만 돌린다. 시험 인터프리터는 본 리포 `.venv` 를 절대 경로로 부른다(C-6 — 심링크를 커밋하지 않는다).

## 11. 합친 뒤 맞물림 시험(두 행 이상을 함께 켠다)

| # | 언제 | 무엇 | 기대 |
|---|---|---|---|
| I-1 | HA-29 합침 | DW-02 흐름 — 말 '체크리스트 돌려서 결과 알려줘' · 대본 모델 `run_checklist` → 카드 턴, 다음 턴 단추 글 → 승인 실행이 `{task_id, status: queued}` 를 받고 대본 모델이 `get_task` 를 한 번 부른다(가짜 running → running → done) | 카드 턴에 `run_checklist` 가짜 0번, 승인 턴에 1번. 승인 턴의 첫 `get_task` 부터 기다린다(born 이 승인 실행에서 들었다 — C-3). 모델 입력에 `끝난 상태(done)` |
| I-2 | HA-29 합침 | 한 단계에 `run_job`(카드)과 늘 running 인 `get_task`(born) 가 나란히 | 카드가 `POLL_S` 한 번 안에 선다(C-4) · 기다림 계수에 들지 않는다 |
| I-3 | HA-29 합침 | 말 '이 고장모드 상태 좀 봐 줄래?' · `failuretrace_object_update(object_id=<정본 결과에서 본 id>)`(목록의 `rootdesigndatahub_object_update` 가 접두를 떼어 `object_update` 로 맞는다) | 카드가 아니라 HA-30 글 · `pending` 빔. 같은 호출을 대상 허브 id 로 고쳐 부르면 그때 카드(질문이라 write 부류 주문이 아니다) |
| I-4 | HA-27 합침 | 사본에 HA-30 거절 글(숫자로 시작하는 UUID)과 초안 '불량 3건', 검토자 3 → 5 | `keep`(UUID 조각이 강한 수 3 이 되지 않는다 — C-13) |
| I-5 | HA-27 합침 | HA-28 기다림이 끝난 상태 도구 결과 | 그릇 `texts` 에 마지막 결과 하나 · 안내의 수(분 · 초 · 횟수 · 진행률)는 출처 있는 수 |
| I-6 | HA-27 합침 | 자기검증 켬 · 카드 턴 | 검토자 0번 · `status=skipped` · `box` 에 `raw` 와 `confirm` 이 함께 · 근거 블록이 카드 글의 작업량을 짚지 않는다(C-14) |
| I-7 | HA-29 합침 | `req.thinking=True` · 엔타이틀먼트에 `feat:thinking` 없음 · 단추 글 | `_denied_feature` 가 막지 않고 일반 챗으로 간다(C-10) |
| I-8 | 6 뒤 | `/health` 한 번 | `self_check.gate` · `status_wait` · `confirm_gate` · `xhub_gate` · `hub_fold` 가 함께 있다. 포털 `test_update_all_tool_cut.py` 꼴로 §7 출력이 그 줄을 찍는다 |

변이로 확인할 것(반대 검토 몫) — born 을 `chat=True` 에만 묶음 · 멈춤 술어 빠짐 · conftest 의 두 손잡이 빠짐 · `_denied_feature` 에 카드 판정 빠짐 · `svc_fallback` 기본값 · UUID 가림 빠짐, 각각 위 시험 하나 이상이 붉어야 한다.

## 12. cae00 재시험에 더할 것(사람 몫 — `server-setup.md`)

- `/health` — `self_check.gate.mode` · `status_wait.on` · `confirm_gate.lists.loaded == true`(거짓이면 형제 리포 경로부터) · `xhub_gate.on`.
- DW-02 · DW-03 후속 — 카드가 뜨는 것이 기대값이다(9절 9). 단추를 누른 턴에서 상태 조회가 LLM 왕복 없이 기다리고 진행 줄이 30초 안팎으로 오른다.
- OT-04 · 08 · 09 · DW-05 — 초안 값이 그대로 나가고 `self_check.gate.counts` 의 drop · demote 수가 는다.
- OT-07 — 에이전트 로그 `[gate] … 다른 허브` 줄과 `xhub_gate.blocked`.
- 손잡이 표(C-9) — 다섯 모두 에이전트 서버 `.env` 를 바꾸면 재기동 뒤에 먹는다. `CHAT_SELF_CHECK_GATE` 도 그렇다 — 코드는 턴마다 환경을 읽지만
  start.sh 가 `.env` 를 기동 때 한 번 싣고 서버는 `.env` 를 다시 읽지 않는다(10-30 반대 검토 — 이 줄은 처음에 '재기동 없이' 로 적었다).
