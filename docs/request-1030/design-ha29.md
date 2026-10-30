# HA-29 설계 — 사람이 시키지 않은 잡 · 쓰기는 코드가 확인 카드로 멈춘다

정본 요청은 [`../request_261030.md`](../request_261030.md) 의 HA-29(높음)이고, 짝 행은 HP-53(운영자 `writes` · `confirm` 채우기)이다. 판단 기록은 [`context-notes.md`](context-notes.md) C-5 다.
기준 판은 dev 의 에이전트 서버 `7ca3a2e` · 포털 `4b08412` · 게이트웨이 `67d8d00` 이다. 요청서의 줄 번호(cae00 `969e723`)는 함수 이름으로 다시 찾았고, 아래 줄 번호는 모두 dev 판이다.
이 문서는 설계만 한다. 구현은 형제 워크트리(`HWAXAgentServer-wt-1030-ha29` · `HWAXPortal-wt-1030-ha29`)에서 한다(C-6).

## 0. 한 줄

- 막는 도구는 셋으로 가른다. **잡 시작**(에이전트 코드의 바닥 목록 24개), **쓰기**(운영자 정의 `writes`), **되돌리기 어려운 것**(운영자 정의 `confirm`)이다. 목록은 에이전트 서버가 형제 리포의 `infra/personas/he-team.json` 을 직접 읽는다 — HP-53 이 채우면 재기동 없이 들어온다.
- 관문은 `_cap_tool.capped` 안의 한 자리에 helper 하나(`_confirm_gate`)로 둔다. 거절 관문 둘 · 유령 ID 관문 · HA-30 뒤, 인자 기본값과 호출 앞이다.
- 막으면 도구를 부르지 않는다. 그 도구 단계가 끝나면 다음 모델 호출 앞에서 턴을 끊고, 결정적인 확인 카드(SSE `confirm` 사건 + 본문 끝의 글)를 낸다. 모델의 뒷말은 믿지 않는다.
- 확인은 카드 번호(`cf-` + 16진 12자)로 잇는다. 카드는 서버 메모리에 30분 둔다. 다음 사람 말이 그 카드에 대한 승인(카드의 **실행** 단추, 또는 '응 · 실행' 같은 짧은 답)이면, 서버가 승인된 호출을 **인자 그대로 한 번** 보내고 모델은 그 결과를 알린다.
- 예상 작업량은 지금 두 가지만 미리 알 수 있다. StepForge `run_job` 은 읽기 도구 `estimate_cost` 로 묻고(15초 상한), SmartTwin 제출 도구는 인자 · 스키마 기본값의 `time_limit`(Slurm 시간 상한)을 싣는다. 나머지는 '미리 알려 주지 않는다' 고 적는다.

## 1. 지금 동작(dev)

### 1.1 확인은 프롬프트 한 줄뿐이다

- 시스템 프롬프트 `_SP_HEAD`(app.py:134-181)의 넷째 규칙(:161-163)이 "등록·발행·삭제·잡 제출처럼 되돌리기 어려운 도구는 무엇을 어디에 하는지 사용자에게 먼저 확인하고 호출하세요" 다. 코드 강제는 없다.
- 운영자 정의의 두 목록은 포털 `infra/scripts/sync-he-personas.py` 의 `build_prompt`(:62-87)가 프롬프트 두 줄(:74 '요청했을 때만 부른다' · :76 '확인을 받은 뒤 부른다')로 만들어 AIDataHub 페르소나에 넣는다. 에이전트 서버는 그 운영자를 고른 턴에만 그 글을 이 턴의 안내로 싣는다(`_agent_stream_turn` 의 운영자 갈래, app.py:5012-5025). 에이전트 서버 코드는 목록 자체를 읽지 않는다(`_persona_meta` app.py:3997 은 apps · key_tools 만 꺼낸다).
- DW-03 은 StepForge 운영자 대화였다. `run_job` 은 그 운영자의 `writes` 에 이미 있었는데(he-team.json:51) 두 번 걸렸다 — 글로 된 규칙이 지켜지지 않은 것이다.

### 1.2 도구가 지나는 래퍼

모든 챗 도구는 `_prep_tool`(app.py:2085)이 `_cap_tool`(app.py:1832)로 감싼다. 챗 묶음은 `_agent_for` 의 `_prep_tool(t, arg_defaults=_CHAT_ARG_DEFAULTS, chat=True)`(app.py:3012), 직접 실행 길은 `deliberation._tools_by_name`(deliberation.py:1848, 같은 `_prep_tool`)이다. `capped`(app.py:1886-2013)의 차례는 이렇다.

| 차례 | 자리 | 하는 일 |
|---|---|---|
| ① | :1889-1903 | `invoke_tool` 안쪽 이름 거절(`_agent_denied` — 외부 응답자 과제 · 패널 · 루틴 도구) |
| ② | :1904-1918 | 외부 응답자 칸 거절(`_agent_external_call` — `deliberate_start` · `risk_start_job` · `rest_call`) |
| ③ | :1919-1937 | 유령 ID 관문(`_turn_ids` 가 None 이면 챗 밖이라 통과) |
| ④ | :1938-1953 | 챗 인자 기본값(`_CHAT_ARG_DEFAULTS`) |
| ⑤ | :1954-2001 | 원래 호출, 예외를 글로 바꿈 |
| ⑥ | :2002-2013 | 접기 · 자르기 · 앱 머리 · 되풀이 꼬리 · `_learn_ids` |

쓰기 · 잡 판정은 어디에도 없다. `/tools-map` 캐시(`_TOOLS_MAP_CACHE`, app.py:2500)도 map · areas 만 쥔다.

### 1.3 한 턴 안에서 도구가 불리는 길

`_agent_stream_turn`(app.py:4807) 안에서 도구가 불리는 길은 여섯이고, 모두 위 래퍼를 지난다.

1. ReAct 흐름 — `async for event in _timed_events(agent.astream_events(...))`(:5169).
2. 예외 뒤 자동 재시도 — `agent.ainvoke`(:5373). 그래프를 처음부터 다시 돌린다.
3. 도구 미호출 강제 재시도 — `agent.ainvoke`(:5448).
4. 확정 종결 — 예고문에서 도구를 고르고 LLM 이 인자를 짜 `_call(_tmap, _tn, _argd)`(:5516)로 **직접** 부른다. 지금은 예고만 한 `run_job` 도 이 길로 걸릴 수 있다.
5. 새어 나온 호출 직접 실행 — `_call(_tmap, c["name"], ...)`(:5604), 그 전의 비스트리밍 재시도(:5556).
6. 빈 답 구제 — `agent.ainvoke`(:5654).

langgraph 1.2.5 · prebuilt 1.1.0 의 `create_react_agent`(version v2)는 도구 호출을 따로 된 작업으로 나란히 돌리고, 기본 `ToolNode` 오류 처리는 `ToolInvocationError` 밖의 예외를 그대로 올린다. 그래서 관문이 예외를 던지면 턴의 `except` 로 가서 2번(그래프 재실행)이 돈다 — 관문은 **던지지 않고 글을 돌려줘야** 한다(지금의 거절 관문들과 같다).

### 1.4 다음 턴이 받는 이력

- 포털 `ChatHistoryMessage`(backend/app/agent/routes.py:121-136)는 `role` · `content` · `evidence` · `images` 만 에이전트에 넘긴다(`to_agent`). 답의 `meta` 는 넘기지 않는다.
- 화면의 `buildHistory`(frontend/src/components/chat/history.ts)는 메시지의 `text` 를 `content` 로 싣고, `text` 는 `result` 사건의 `content` 로 끝난다(ChatContext.tsx `onResult`). 서버 사본도 같은 `result` 글을 남긴다(routes.py `pump` 의 `final`). 그래서 **답 본문에 코드가 넣은 글은 다음 턴 이력에 그대로 돌아온다** — 근거 블록 표지 `_EVIDENCE_MARK`(app.py:1579)가 이미 이 길로 유령 ID 관문과 맞물린다.
- 포털 중계 `_relay_stream`(routes.py:794-919)은 SSE 를 바이트 그대로 넘긴다. 모르는 사건 이름도 브라우저에 간다. 화면 `dispatch`(frontend/src/api/chat.api.ts:60-114)는 `switch` 에 없는 사건을 버린다.

### 1.5 게이트웨이의 쓰기 표지는 울타리가 못 된다(dev 실측)

`/tools-map` 의 `write`(gateway.py:6472)는 `_tool_is_write`(gateway.py:3187 — 표지가 없으면 이름 낱말 `_WRITE_NAME` :2938)다. 10-30 08:39 dev 실측(도구 564개, write 122개)이다.

- 잡을 거는 도구 · 상태를 바꾸는 도구를 놓친다 — 요청서가 이름 댄 `docforge_convert` 와 낙하 제출 `fullangle_drop_simulation` · `single_drop_simulation`, 운영자 `writes` 의 `job_collect` · `job_postprocess`, 잡 취소 · 재개 `risk_job_action` 이 `write=False` 다.
- 읽기를 쓰기로 적는다 — `get_record` · `get_record_sections` · `describe_record_schema`(낱말 `record`) · 계산 도구 `run_progressive_failure` · `run_sensitivity_analysis` 가 `write=True` 다.

검색 순위의 감점용 이름 규칙이고(메모리 '순위 규칙은 울타리가 아니다'), 이 행의 관문 출처로 쓰지 않는다.

## 2. (1) 무엇을 막나 — 목록과 그 출처

### 2.1 출처 비교

| 길 | 장점 | 비용 · 문제 | 판정 |
|---|---|---|---|
| 게이트웨이 `/tools-map` 의 `write` | 새 자료가 없다 | 1.5 의 실측대로 무거운 잡을 놓치고 읽기를 막는다. 캐시 칸도 새로 둬야 한다 | 쓰지 않는다 |
| 에이전트 코드의 고정 목록만 | 결정적이다 · 파일 의존 없음 | 운영자 정의와 두 벌이 된다. 새 앱마다 에이전트 코드를 고친다 | 바닥(잡 시작)만 |
| 포털이 챗 요청에 목록을 실어 보냄 | 정본이 포털에 있다 | 포털 `ChatRequest` · 중계 · 에이전트 `ChatRequest` 세 곳과 두 리포 AST 계약 시험이 늘고, 포털을 안 거치는 호출(시험 · 도구)은 빈다 | 쓰지 않는다 |
| 에이전트가 `../HWAXPortal/infra/personas/he-team.json` 을 직접 읽음 | HP-53 이 채우는 그 정본 하나를 본다. AIDataHub 동기화(AD-21 의 500)와 무관하다. 바뀐 시각을 보고 재기동 없이 다시 읽는다. 선례가 있다(코어 어휘표 `CORE_VOCAB_PATH`, app.py:250 — 형제 리포 파일 직접 읽기) | 형제 리포 배치에 묶인다(이미 받아들인 꼴 — dev ~/claude · cae00 ~/Projects 둘 다 형제다). 이름이 노출 이름이거나 접두 별칭이라 맞추기가 필요하다 | **쓴다** |

권하는 길은 **he-team.json 직접 읽기 + 잡 시작 바닥 목록**이다. C-5('잡 · 쓰기 도구는 운영자를 두든 말든 위험이 같다')대로 목록은 운영자를 고른 대화에만이 아니라 **모든 챗 턴**에 건다.

### 2.2 세 부류

| 부류 | 출처 | '이번 말이 시켰다' 로 통과하나 | 승인 |
|---|---|---|---|
| `job`(잡 시작) | 에이전트 바닥 목록 `_CONFIRM_JOB_TOOLS` | 엄격 — 주문 동사 + 그 일을 글자로 부름(4.1) | 카드 승인, 인자 그대로 한 번 |
| `write`(쓰기) | he-team.json 의 모든 `writes`(선택 앱 `optional[].writes` 포함) | 너그러움 — 주문 동사만(4.1) | 같음 |
| `confirm`(되돌리기 어려움) | he-team.json 의 모든 `confirm`(선택 앱 포함) | 통과 없음 — 늘 카드 | 같음 |

- 겹치면 `confirm` > `job` > `write` 다(더 엄한 쪽).
- `job` 을 따로 두는 까닭은 FP 비용이 다르기 때문이다. 문서 작성 운영자(MX 백서 `insert_block` · RA `create_report_draft` …)의 쓰기까지 글자 그대로의 이름을 요구하면, 한국어로 시킨 저작 흐름이 쓰기마다 한 번씩 끊긴다. 잡은 단일 러너 · 클러스터 · GLM 을 몇 분 ~ 몇 시간 잡으므로 엄하게 둔다(DW-03 — 1,812초).
- 바닥 목록(24개, `_named` 규칙으로 접두 별칭까지 맞는다)이다. 요청서가 이름을 댄 것 · 클러스터 제출 · HP-53 이 '잡' 으로 든 것 · StepForge 의 다른 잡 넣기(`run_job` docstring "잡을 넣는 다른 도구(export_step·remesh_parts·build_cavity)" — 같은 단일 러너) · 심의와 리스크 잡이다.

```python
_CONFIRM_JOB_TOOLS = (
    "run_job", "run_checklist", "run_analysis", "run_compare", "run_curvature", "docforge_convert",
    "submit_job", "slurm_submit_job", "smarttwin_submit", "submit_lsdyna_job", "fullangle_drop_simulation",
    "single_drop_simulation", "job_rerun", "catalog_run", "recipe_run", "run_recipe", "run_operation",
    "remesh_parts", "export_step", "build_cavity", "intake", "deliberate_start", "deliberate_continue", "risk_start_job")
```

- he-team.json 을 못 읽으면(없음 · 꼴 틀림) 바닥 목록만으로 돈다. 그 사실을 로그 한 줄(처음 한 번)과 `/health` 의 `confirm_gate.lists` 에 싣는다. 요청서가 이름을 댄 잡은 파일이 없어도 막힌다.
- dev 모의(위 바닥 + 지금의 he-team.json, `/tools-map` 564개에 대어 봄)에서 막히는 도구는 103개(job 20 · write 56 · confirm 27)이고, 그 가운데 게이트웨이가 읽기로 확인한 `routine_read` 와 겹치는 것은 0개다. 접미 맞추기(`_named`)가 읽기를 잘못 막은 예가 없다.

### 2.3 이름 맞추기

- 판정 이름은 노출 이름이고, `invoke_tool` 이면 안쪽 이름(`kw["name"]`)이다.
- 부류는 지금 거절 관문과 같은 규칙 `_named`(app.py:2852 — 이름 그대로이거나 `n.endswith("_" + t)`)로 본다. 그래서 `heaxstep_forge_run_job` · `ste_submit_job` · `smarttwinmcp_submit_job` 이 바닥의 `run_job` · `submit_job` 에 맞는다.
- he-team.json 의 이름은 노출 이름이거나 접두 별칭(`<앱 키에서 하이픈을 뺀 것>_<이름>`, sync-he-personas.py :140-146)이다. 읽을 때 그 페르소나의 `apps` · `optional[].app` 의 접두를 떼어 낸 꼴도 함께 넣는다(`heaxstep_forge_cancel_job` → `cancel_job` 도). 그래야 모델이 맨 이름으로 불러도 맞는다.
- 승인 · 중복 판정의 열쇠는 `(base, canon)` 이다. `base` 는 맞은 목록 이름(가장 긴 것), `canon` 은 인자의 정규 글이다 — dict(JSON 글이면 풀어서)에서 값이 `None` · `""` · `[]` · `{}` 인 칸을 재귀로 빼고 키 차례 JSON(`sort_keys` · `separators=(",", ":")`)으로 적는다. 못 읽는 글은 그대로 쓴다(같은 글일 때만 같다).

### 2.4 손잡이

- `CHAT_CONFIRM_GATE` — 기본 `1`, `0` 이면 관문이 아무것도 막지 않고 시스템 프롬프트 넷째 규칙도 종전 글이다. 기동 때 한 번 읽는다(`CHAT_STABLE_PREFIX` 와 같은 꼴). 박스에서 관문이 오작동하면 코드 되돌림 없이 끄는 길이다.
- 그 밖의 값(카드 수명 1800초 · 작업량 묻기 15초 · 카드 저장 상한 256)은 상수다. 요청이 손잡이를 청하지 않았다.

## 3. 관문 자리 — `_cap_tool.capped` 의 한 곳

```text
capped(*a, **kw)
  ① invoke_tool 거절(_agent_denied)              — 지금
  ② 외부 응답자 칸 거절(_agent_external_call)     — 지금
  ③ 유령 ID 관문(_turn_ids)                       — 지금
  ④ HA-30 다른 허브 id 관문                        — HA-30 행
  ⑤ HA-29 확인 관문  _confirm_gate(tool, a, kw)   — 이 행(한 줄 호출)
  ⑥ 챗 인자 기본값(_CHAT_ARG_DEFAULTS)            — 지금
  ⑦ 원래 호출(예외면 ✖ 글로 끝)                     — 지금
  ⑧ HA-28 _status_wait — 성공한 호출 뒤, 상태 도구면 코드가 기다리고 아니면 잡 시작 결과에서 id(born)를 배운다 — HA-28 행
  ⑨ 접기 · 자르기 · 머리 · 꼬리 · _learn_ids(HA-30 은 그 옆에서 허브 id 를 배운다) — 지금
```

HA-28 · HA-30 설계서(`design-ha28.md` 6절 표 · `design-ha30.md` 6절)와 같은 차례다.

- ① ② 뒤인 까닭 — 승인해도 보낼 수 없는 호출에 카드를 띄우면 사람에게 의미 없는 질문을 한다.
- ③ ④ 뒤인 까닭 — 지어낸 ID · 다른 허브의 id 를 실은 호출에 카드를 띄우면 사람이 틀린 대상의 호출을 승인한다. 인자를 먼저 고치게 한다.
- ⑥ 앞인 까닭 — 승인 열쇠(canon)를 모델이 준 인자로 잰다. 기본값은 코드가 결정적으로 더하므로 다시 불러도 같다.
- ⑧ 과의 관계 — 상태 조회 도구는 어느 목록에도 없으므로 HA-28 의 기다리기와 겹치지 않는다. 막은 호출은 ⑦ 에 닿지 않으므로 born 도 없다. 승인된 잡이 시작된 뒤 모델이 상태를 물으면 HA-28 이 기다린다(7절 HA-28 줄 — 승인 실행의 born).
- 세 행(HA-28 · 29 · 30)이 같은 함수를 만지므로 위 차례를 고정하고, 각 행은 helper 하나를 한 줄로 부른다. 거절 글 반환의 꼴(`(msg, None) if response_format == "content_and_artifact" else msg`)은 지금 네 번 되풀이된다 — 세 행이 같은 작은 helper(`_refuse(tool, msg)`)를 쓰면 병합이 쉽다(선택).

### 3.1 `_confirm_gate(tool, a, kw) -> str | None`

```text
ctx = _turn_confirm.get()            # 이 턴의 확인 맥락(4.3) — None 이면 챗 밖(심의 좌석 · 띵킹 · 루틴 · 카탈로그 · 시험)이라 통과
if ctx is None or not CHAT_CONFIRM_GATE: return None
via = tool.name == "invoke_tool"
for args in (kw, *dict 위치 인자):    # 지금 관문들과 같은 순회
    name, targs = (args["name"], args.get("arguments")) if via else (tool.name, args)
    kind, base = _confirm_class(name)   # None | "job" | "write" | "confirm"
    if kind is None: return None
    key = (base, _confirm_canon(targs))
    if key in ctx.approved and key not in ctx.used:          # 승인된 호출(5.4 — 서버가 보낸다)
        ctx.used.add(key); return None
    if kind != "confirm" and key not in ctx.used and _confirm_ordered(ctx, kind, name, base, targs):
        ctx.used.add(key); ctx.counts["ordered"] += 1; return None
    ctx.pending.append({name, via, base, kind, args: targs, canon, again: key in ctx.used})
    return _CONFIRM_REFUSAL(name)      # 글 — 아래
return None
```

- 확인 · 표시 · 중복 셈은 `await` 없이 한 번에 한다. 나란히 도는 호출이 있어도 한 이벤트 루프 안이라 경합이 없다.
- 같은 호출(같은 열쇠)이 이 턴에 이미 나갔으면 다시 막는다(`again`). 예외 뒤 자동 재시도(1.3 의 2번)가 그래프를 다시 돌려도 이미 보낸 잡을 또 걸지 않는다.
- 모델이 보는 글(막은 호출의 도구 결과)이다. 표지 `_CONFIRM_MARK = "[확인 대기]"` 를 싣고 `_TOOL_FAIL_MARK` 로 시작한다 — 그래서 `_result_ok` 가 거짓이고(app.py:3864), 활동 · 절차 원장이 이 호출을 성공으로 접지 않는다.

```text
✖ 도구 {name} 호출 보류: [확인 대기] — 사용자가 이번 말로 시킨 작업이 아니라 보내지 않았다. 서버가 사용자에게 확인 카드를 띄운다.
이번 턴에는 이 도구를 다시 부르지 말고(인자를 바꿔도 같다) 무엇을 왜 하려 했는지 한 줄로 말하고 끝내라. 인자 문제가 아니다.
```

## 4. (2) '이번 사람 말이 분명히 시켰다' 판정

### 4.1 주문 판정 `_confirm_ordered`

판정에 쓰는 글은 **이번 요청의 `req.message` 원문 하나**다.

- 이 턴의 안내(운영자 역할 글 · 지식카드 발췌 · 붙인 문서)는 HA-26 이후 사람 발화 머리에 붙지만(`_with_turn_notes`, app.py:368) 판정에는 넣지 않는다. 문서 · 도구 결과 속 '돌려줘' 가 주문이 되지 않게 한다.
- 재촉 → 이어하기(app.py:4846-4854)가 `req.message` 를 앞 질문 + 끊긴 답(모델 글)으로 바꾸기 **전에** 판정 맥락을 만든다. 끊긴 답의 모델 글이 주문으로 읽히지 않게 한다.
- 이 말이 카드에 대한 답(4.2)이면 판정 글은 빈 글이다 — 확인 답('실행' · '응')은 새 주문이 아니다. 승인은 카드에 적힌 호출에만 간다.

규칙이다(질문 · 부정은 주문을 지운다 — 어긋나면 카드 쪽으로 간다).

| 부류 | 주문으로 치는 조건 |
|---|---|
| `job` | `_ORDER_RE` 가 맞고 · `_ASK_RE` 와 `_NEG_RE` 가 안 맞고 · **그 일을 글자로 불렀다** — 도구 이름(노출 · 맨 이름) · '무엇' 칸 값 · 파일 이름 가운데 하나가 말에 있거나(대소문자 무시), 그 도구가 이번 요청의 `pinned_tools`(사람이 콕 집은 도구)에 있다 |
| `write` | `_ORDER_RE` 가 맞고 · `_ASK_RE` 와 `_NEG_RE` 가 안 맞는다 |
| `confirm` | 없음(늘 카드) |

- '무엇' 칸은 `kind` · `operation` · `tool` · `job` · `recipe` · `name` · `action` · `scenario` · `template` 이다. 맨 위 칸과 한 단계 아래 dict(예 `params.tool`)까지 보고, 글 값 3 ~ 64자만 쓴다. 식별자 칸(`project_id` · `session_id` · `job_id` …)은 쓰지 않는다 — 'P1 돌려줘' 가 그 과제의 아무 잡이나 통과시키면 DW-03 이 그대로 남는다.
- 파일 이름은 '/' 가 있고 확장자로 끝나는 글 값의 끝 조각이다(`docforge_convert(path=…/x.pptx)` 를 'x.pptx 변환해 줘' 가 부른다).

```python
_ORDER_RE = re.compile(
    r"(?:실행|재실행|제출|시작|변환|등록|생성|저장|업로드|추가|수정|변경|삭제|취소|적용|반입|게시)\s*(?:을|를)?\s*"
    r"(?:해\s*(?:줘|주세요|주십시오|줄래|봐)|하자|합시다|하세요|해라|하라|해(?=\s*[.!~]*\s*$))"
    r"|(?:돌려|걸어|만들어|올려|지워|넣어|바꿔|고쳐|붙여)\s*(?:줘|주세요|주십시오|줄래|봐|라)"
    r"|(?:돌려|걸어|만들어|올려|지워|넣어|바꿔|고쳐|붙여|돌리자|걸자)(?=\s*[.!~]*\s*$)"
    r"|(?:^|[\s,.;!])(?:please\s+)?(?:run|rerun|submit|start|launch|execute|convert|create|register|upload|save|delete|remove|cancel|apply)\b",
    re.I | re.M)
_ASK_RE = re.compile(r"\?|(?:까요?|나요|니|냐|는지|을지|ㄹ지|어때|되나|돼|될까|가능해|가능할까)\s*[.!~]*\s*$", re.M)
_NEG_RE = re.compile(r"(?:지\s*마|지\s*말|하지\s*않|말고|말아|안\s*(?:돼|된|해|함)|금지|멈춰|중지|그만|아니(?:요|야|오)?(?=[\s.,!~]|$)|아뇨"
                     r"|\bno\b|\bnope\b|don'?t|do\s+not|never|\bstop\b)", re.I)
```

판정 예(시험 벡터)이다.

| 사람 말 | 호출 | 결과 |
|---|---|---|
| `drop_check 돌려줘` | `run_job(kind="measure", params={"tool":"drop_check"})` | 통과(job — `params.tool` 을 글자로 불렀다) |
| `drop_check 돌려줘` | `run_job(kind="graph")` | 카드(graph 는 시키지 않았다 — DW-03 의 첫 잡) |
| `판 전체 낙하 점검 돌려줘` | `run_job(kind="measure", params={"tool":"drop_check"})` | 카드(그 일을 글자로 부르지 않았다) |
| `P1 돌려줘` | `run_job(project_id="P1", kind="graph")` | 카드(식별자는 대상이 아니다) |
| `drop_check 결과 보여줘` · `drop_check 실행 결과는?` · `drop_check 돌려도 돼?` · `drop_check 는 돌리지 마` | `run_job(... drop_check)` | 카드(주문 동사 없음 · 질문 · 부정) |
| `x.pptx 변환해 주세요` | `docforge_convert(path="/stage/x.pptx")` | 통과(파일 이름) |
| `이 표를 문서에 블록으로 추가해줘` | `insert_block(...)`(write) | 통과 |
| `이 문서 요약해줘` | `insert_block(...)` | 카드 |
| `delete_project 로 P1 지워줘` | `delete_project(...)`(confirm) | 카드(늘) |
| `이 판 질량 알려줘` | `list_projects` · `mass_estimate` | 통과(목록 밖 — 관문과 무관) |

### 4.2 '앞 카드를 승인한다' 판정

대기 상태는 **두 곳**에 있다.

- 서버 메모리 `_CONFIRM_PENDING`(OrderedDict) — `{카드 id: {user, conv, exp, at, calls: [{name, via, base, kind, args, canon, app, args_text, workload}]}}`. `user` 는 `req.user_email` 소문자, `conv` 는 `req.conversation_id`(비면 빈 글)다. 수명 1800초, 상한 256개(넘으면 오래된 것부터), 같은 (user, conv) 의 새 카드가 서면 그 대화의 옛 카드는 지운다. 프로세스 하나(uvicorn 단일 — 루틴 레지스트리 `routine._RUNS` 와 같은 전제)라 메모리로 충분하다. 재기동하면 사라지고, 그때 승인 답은 '찾지 못했다' 로 처리되어 다시 카드가 뜬다(닫힌 쪽).
- 답 본문 끝의 카드 글 — 그 안의 `확인 번호 cf-xxxxxxxxxxxx` 가 이력(1.4)으로 돌아온다. 구조화 칸(`meta`)은 이력에 실리지 않으므로 이 길을 쓴다. 번호는 `secrets.token_hex(6)` 이라 추측할 수 없고, 서버 저장분 · 사용자 · 대화가 맞아야만 쓸모가 있다 — 모델이 카드 글을 흉내 내도 승인이 되지 않는다.

`_CF_ID_RE = re.compile(r"\bcf-[0-9a-f]{12}\b")`. 턴 시작에 판정한다(`_confirm_ctx(req)`).

1. `last` = 이력의 **마지막 항목이 어시스턴트일 때** 그 글의 카드 번호들. 마지막 항목이 아니면 카드는 이미 지나갔다(확인은 바로 다음 말로만 한다).
2. 이번 말에 `last` 의 번호가 있으면(단추) — `_NEG_RE` 가 맞거나 말이 '취소' 로 시작하면 **거절**, 아니면 **승인**이다. 이번 말에 번호가 있는데 `last` 에 없으면(지난 카드) 무시한다.
3. 번호가 없고 `last` 가 있으면 — 말 전체가 `_DECLINE_RE` 면 **거절**, 말 전체가 `_AFFIRM_RE` 이고(비지 않고 30자 이하) `_NEG_RE` 가 안 맞으면 **승인**이다.
4. 승인 · 거절이면 저장분을 꺼낸다(`pop` — 한 번만). user · conv 가 다르거나 기한이 지났거나 없으면 **찾지 못함**이다.

```python
_AFFIRM_RE = re.compile(
    r"^(?:(?:응|어|네|넵|넹|예|그래|좋아|좋아요|ㅇㅇ|ㅇㅋ|오케이|ok|okay|yes|y|go)[\s,.!~]*)?"
    r"(?:(?:실행|진행|확인|승인|돌려|걸어|시작)\s*(?:해|해요|하자|합니다|할게|하세요|해라|해\s*줘|해\s*주세요|줘|주세요)?)?[\s.!~]*$", re.I)
_DECLINE_RE = re.compile(r"^(?:아니(?:요|야|오)?|아뇨|no|nope|취소|그만|됐어|괜찮아|하지\s*마|안\s*해)[\s.!~]*$", re.I)
```

- 단추가 보내는 글은 서버가 카드 사건에 실어 준다(`approve_text` = `실행 — 확인 번호 cf-…`, `decline_text` = `취소 — 확인 번호 cf-… 는 실행하지 않음`). 화면은 그 글을 그대로 보낸다 — 꼴이 두 리포에 두 벌로 생기지 않는다.
- 판정 결과는 이 턴의 맥락 `ctx` 에 둔다 — 승인이면 `ctx.approved = {(base, canon): call}`, 판정 글은 빈 글, 상태줄 '확인 카드 cf-… 승인 — 승인된 호출 N건을 보냅니다'. 거절이면 이 턴의 안내에 '[확인 카드 cf-… 거절 — 사용자가 그 호출을 원하지 않는다. 같은 호출을 다시 하지 마라]'. 찾지 못함이면 상태줄 '확인 번호를 찾지 못했다(30분이 지났거나 서버가 다시 떴다) — 필요하면 다시 확인 카드가 뜬다'.
- 띵킹 모드가 켜진 채 단추를 누르면 `chat()`(app.py:5708)이 그 말을 띵킹으로 보낸다(:5761). 그래서 `chat()` 의 띵킹 갈래 앞에 '이 말이 이력 끝 카드의 답이면 일반 챗으로 간다' 를 한 줄 둔다(4.2 의 1 ~ 3 과 같은 판정 함수).

### 4.3 턴 맥락 `_turn_confirm`

`_turn_ids` · `_turn_tool_calls`(app.py:1410-1413)와 같은 꼴의 ContextVar 다. 값은 변하는 객체 하나라 도구 작업(복사된 맥락)과 턴이 같은 객체를 본다 — 유령 ID 관문이 이미 이 길로 돈다.

```text
_ConfirmCtx(utterance: str, pinned: frozenset, approved: dict, used: set, pending: list, note: str, card: str, counts)
```

`_agent_stream_turn` 머리(`_turn_tool_calls.set(Counter())` 바로 뒤, :4842)에서 `_turn_confirm.set(_confirm_ctx(req))` 한다. 이 턴에서 시작하는 모든 도구 길(1.3 의 여섯)이 같은 맥락을 본다. 심의 좌석(`deliberation._free_tool_ok` — 읽기 허용 목록) · 띵킹(정해진 도구 셋) · 루틴(`routine.py` — 게이트웨이 단계 울타리)은 이 함수를 지나지 않으므로 맥락이 None 이고 관문이 서지 않는다.

## 5. (3) 멈춤 — 턴을 끊고 카드를 낸다

### 5.1 흐름 끊기(`_agent_stream_turn`)

- `on_tool_end`(:5252)에서 결과 글에 `_CONFIRM_MARK` 가 있으면 다음을 한다.
  - `_budget["blocked"] += 1`(유령 ID 와 같은 셈 — '도구를 썼다' 로 세지 않는다).
  - 그 호출을 `turn_calls` 에서 뺀다(`on_tool_start` 가 넣을 때 `run_id → 자리` 를 적어 둔다). 근거 블록 · 자기검증 · 다음 턴 출처에 '조회한 것' 으로 남지 않는다. `turn_out` 에도 넣지 않는다.
  - 상태 사건 `{"step": "확인 대기: {도구} — 사람의 확인 전에는 보내지 않습니다", "tool": 도구, "ok": false, "call": run_id, "result_preview": 막은 글}` 을 낸다(완료 사건 대신 — '도는 중' 으로 남지 않게).
  - `_hold = True`.
- `_hold` 인 채로 **다음 `on_chat_model_start`** 가 오면 루프를 나간다. 같은 단계의 나란한 도구(읽기 등)는 다 끝난 뒤이므로 그 결과는 살고, 막 시작한 모델 호출만 접힌다. 흐름이 그 전에 끝나면 그대로 끝난다.
- 나간 뒤 `_timed_events` 생성기를 `aclose()` 한다(그 `finally` 가 `astream_events` 를 닫는다). 닫다가 난 예외는 로그 한 줄로 삼킨다 — 턴의 `except` 로 가면 자동 재시도가 그래프를 다시 돈다.
- 턴의 `except`(:5317) 머리에서도 `ctx.pending` 이 있으면 재시도 · 오류 문구 대신 카드로 끝낸다(재귀 한도 등이 끊기와 겹친 경우).
- 루프 뒤 구제 길 넷(강제 재시도 :5437 · 확정 종결 :5473 · 새어 나온 호출 :5552 · 빈 답 구제 :5638)은 `ctx.pending` 이 있으면 건너뛴다. 그 길 안에서 관문이 새로 막았으면(직접 실행 결과에 `_CONFIRM_MARK`) 그 결과를 LLM 으로 요약하지 않는다.

### 5.2 카드 내기(턴 끝, 근거 블록 앞)

`ctx.pending` 이 비지 않았으면 다음을 한다.

1. 카드 id 를 짓고 `_CONFIRM_PENDING` 에 넣는다(같은 대화의 옛 카드 지움 · 상한 · 수명).
2. 예상 작업량을 묻는다(6절 — 필요할 때만, 전체 15초). 묻는 동안 상태줄 '확인 카드 — 예상 작업량을 묻는 중' 을 낸다.
3. SSE `confirm` 사건을 낸다.

```json
{"id": "cf-7f3a9c2e41d0", "expires_at": 1730277000000,
 "calls": [{"tool": "run_job", "app": "StepForge", "kind": "job",
            "args_text": "kind=measure · params.tool=drop_check · project_id=P1",
            "workload": "약 60초(40 ~ 90초 · 근거 history) — 추정이며 하한일 수 있다", "again": false}],
 "approve_text": "실행 — 확인 번호 cf-7f3a9c2e41d0",
 "decline_text": "취소 — 확인 번호 cf-7f3a9c2e41d0 는 실행하지 않음"}
```

4. 본문 끝에 결정적 카드 글을 붙인다(다른 기기 · 서버 사본 · 단추 없는 화면에서도 글로 확인할 수 있다).

```text
---
**확인이 필요합니다** — 이번 말로 시키지 않은 작업이라 보내지 않았습니다.
1. StepForge `run_job` · kind=measure · params.tool=drop_check · project_id=P1 — 예상 작업량: 약 60초(40 ~ 90초 · 근거 history) — 추정이며 하한일 수 있다
실행하려면 **실행** 을 누르거나 '실행' 이라고 답하세요. 다른 말을 하면 보내지 않습니다. (확인 번호 `cf-7f3a9c2e41d0` · 30분)
```

- `confirm` 부류는 첫 줄이 '되돌리기 어려운 작업이라 보내기 전에 확인합니다' 다. `again` 이면 그 줄 끝에 '(이 턴에 같은 호출을 이미 보냈다 — 다시 보내면 하나 더 선다)' 를 붙인다.
- `args_text` 는 정규 인자에서 맨 위 글 · 수 칸을 `k=v`, 한 단계 아래 dict 는 `k.sub=v`, 목록은 `k=[N개]` 로 적고 값은 60자, 줄 전체는 300자에서 자른다. 전체 인자는 저장분에 있다.
- 글은 `_INTERRUPTED_RE`(app.py:1458)에 걸리지 않는다(끝이 확인 번호다) — '계속' 재촉이 카드 턴을 끊긴 턴으로 읽지 않는다.
- 사건 차례는 `confirm` → 카드 글(`token`) → 근거 블록(막지 않은 조회가 있었으면) → `meta` → `result` → `done` 이다.

### 5.3 자기검증과 근거 블록

- `box.update(draft=..., calls=..., outputs=..., confirm=카드)` 를 싣는다. `_self_checked_turn`(app.py:4611)은 `box.get("confirm")` 이면 검토자를 부르지 않는다 — `check = {"status": "skipped", "reason": "확인 카드로 멈춘 턴 — 검증할 답이 없다"}`. 검토자가 카드 글(번호 포함)을 고치지 못하게 한다. `_self_check_skip`(:4403)만으로는 안 된다 — 앞서 조회한 도구가 있으면 검토가 돈다.
- 감싸개가 있는 길에서는 안쪽 턴이 카드 글을 `token` 으로 내지 않고 초안에만 넣는다(초안은 '생각' 칸으로 가므로 두 번 보이지 않게). `confirm` 사건은 감싸개가 붙잡지 않는 사건이라 바로 지나간다.

### 5.4 승인된 턴 — 서버가 그 호출을 보낸다

`ctx.approved` 가 있으면 이번 턴의 안내를 다 모은 뒤 · 메시지를 짓기 전(`_turn_msgs` 호출 :5153 바로 앞)에 다음을 한다.

1. `_tools_by_name(app, req.groups, user=req.user_email, user_pat=req.user_pat)` 로 도구를 받는다(확정 종결 :5478 과 같은 길 — 결과에 앱 머리가 없는 깨끗한 글).
2. 카드에 적힌 차례대로, **처음 부른 꼴 그대로** 한 번씩 보낸다 — `invoke_tool` 로 불렀던 것은 `invoke_tool(name, arguments)` 로(게이트웨이의 `invoke_tool` 파괴 · 제어 이름 거절 gateway.py:2475-2476 · :6037-6053 은 그대로 걸린다), 직접 불렀던 것은 그 이름으로(목록에 없어졌으면 `invoke_tool` 로). 이 호출도 래퍼를 지나고(①~④ 를 다시 지난다 — 확인은 '사람이 시켰다' 이지 'id 가 맞다' 가 아니다, `design-ha30.md` 6절 5), 관문은 승인 열쇠를 보고 통과시키며 `used` 에 적는다.
3. 상태 사건(`도구 호출: X` · `도구 완료: X`, `call = "<카드 id>-<n>"`, `ok` · `result_preview` · `result_full`)을 확정 종결의 직접 실행과 같은 꼴로 낸다. `turn_calls` · `turn_out` 에 넣는다(근거 블록 · 절차 원장에 '보낸 것' 으로 남는다). 보낸 수를 `_budget["calls"]` 에도 센다 — 안 세면 모델이 결과만 알리고 끝난 턴이 '도구 0회' 로 읽혀 강제 재시도 · 확정 종결(1.3 의 3 · 4번)이 돈다.
4. 이번 턴의 안내에 붙인다.

```text
[확인 카드 cf-… 승인 — 서버가 사람의 승인으로 이 호출을 보냈다]
- run_job(kind=measure · params.tool=drop_check · project_id=P1) → {결과, _cut_mark 로 6,000자까지}
이 호출을 다시 하지 마라(같은 잡이 하나 더 선다). 결과(잡 id · 상태)를 사용자에게 알리고, 잡이면 상태 조회 도구로 진행을 볼 수 있다.
```

- 승인된 인자의 정수는 이 턴의 유령 ID 출처(`_seed_ids`)에 넣는다 — 사람이 카드에서 본 값이다. 안 넣으면 카드 턴에 다른 조회가 없어 근거 블록이 없던 경우 ③ 관문이 정수 id 를 막는다.
- 도구 목록을 못 받으면 승인된 호출을 `ctx.pending` 으로 되돌리고(`workload` 자리에 '승인했지만 도구 목록을 받지 못해 보내지 못했다'), 안내로 모델에게 그렇게 말하게 한다 — 턴 끝에 새 카드가 선다.
- 모델이 같은 호출을 또 부르면 `used` 라서 카드(`again`)다. 승인 뒤 인자를 바꿔 부르면(예: 시작 실패 뒤 고친 인자) 그 새 호출은 카드다.
- 모델 재현에 기대는 길(승인된 턴에 모델이 같은 인자로 다시 부르게 하는 길)은 쓰지 않는다. Qwen 이 칸을 하나 빼거나 더하면 카드가 되풀이되고, 아예 부르지 않으면 단추가 아무 일도 안 한 셈이 된다.

### 5.5 화면(포털 프론트)

- `src/api/chat.api.ts` — `StreamHandlers.onConfirm?: (e: ConfirmCard) => void` 와 `dispatch` 의 `case 'confirm'`. 이것이 없으면 사건이 버려진다(1.4).
- `src/types/chat.ts` — `ConfirmCall { tool; app?; kind: 'job' | 'write' | 'confirm'; args_text; workload?; again? }`, `ConfirmCard { id; expires_at; calls; approve_text; decline_text }`, `Message.confirm?: ConfirmCard`.
- `src/state/ChatContext.tsx` — `onConfirm: (e) => patch(cid, botId, (m) => ({ ...m, confirm: e }))`.
- `src/components/chat/confirm.ts`(새, 순수 함수) — `confirmActive(messages, msgId, streaming, now)` 는 그 메시지가 활성 대화의 **마지막 어시스턴트 메시지**이고 · 받는 중이 아니고 · `now < expires_at` 일 때만 참이다. 누르면 새 메시지가 붙어 저절로 마지막이 아니게 된다(따로 '결정' 상태를 두지 않는다).
- `src/components/chat/ConfirmCard.tsx`(새) — 호출마다 앱 · 도구 · `args_text` · 예상 작업량 · `again` 한 줄, 단추 **실행** · **취소**. 단추는 `sendMessage(card.approve_text, undefined, null)` · `sendMessage(card.decline_text, undefined, null)` 이다(셋째 인자 `null` — 켜 둔 루틴을 싣지 않는다, ChatContext.tsx:116 의 약속). 활성이 아니면 단추를 숨기고 '이 확인은 끝났습니다(대화가 이어졌거나 30분이 지났다)' 를 보인다.
- `src/components/chat/MessageList.tsx` — `Row` 에서 글 칸 뒤, 도구 카탈로그 앞에 `{msg.confirm && <ConfirmCard msg={msg} />}`(:165 근처).
- `src/state/chatStore.ts` — `StoredMessage.confirm` 을 저장 · 되살린다(id 가 글이고 calls 가 배열일 때만). 새로고침 뒤에도 30분 안이면 단추가 산다. 서버 사본에는 카드 글만 있고(포털 중계는 고치지 않는다), 다른 기기에서는 '실행' 이라고 답하면 된다.
- 스타일은 루틴 보기(`.rv`)와 같은 `src/styles/chat.css` 에 두고 기존 CSS 변수만 쓴다(빌드의 `check-css-vars.mjs`).

### 5.6 바뀌는 리포 · 파일

| 리포 | 파일 | 무엇 |
|---|---|---|
| HWAXAgentServer | `app.py` | `_SP_HEAD` 넷째 규칙(손잡이에 따라) · 목록 읽기(`CONFIRM_LISTS_PATH` · `_CONFIRM_JOB_TOOLS` · `_confirm_lists` · `_confirm_class` · `_confirm_canon`) · 판정(`_ORDER_RE` · `_ASK_RE` · `_NEG_RE` · `_AFFIRM_RE` · `_DECLINE_RE` · `_CF_ID_RE` · `_confirm_ordered`) · 맥락(`_turn_confirm` · `_ConfirmCtx` · `_confirm_ctx`) · `_confirm_gate` 와 `capped` 의 한 줄 · 저장(`_CONFIRM_PENDING`) · `_agent_stream_turn` 의 끊기 · 구제 길 건너뛰기 · 카드 · 승인 실행 · `_self_checked_turn` 의 건너뛰기 · `chat()` 의 띵킹 앞 한 줄 · `/health` 의 `confirm_gate` |
| HWAXAgentServer | `tests/test_confirm_gate.py`(새) | 9절의 A · B 묶음 |
| HWAXPortal | `frontend/src/api/chat.api.ts` · `frontend/src/types/chat.ts` · `frontend/src/state/ChatContext.tsx` · `frontend/src/components/chat/MessageList.tsx` · `frontend/src/state/chatStore.ts` | 5.5 |
| HWAXPortal | `frontend/src/components/chat/ConfirmCard.tsx` · `frontend/src/components/chat/confirm.ts`(새) · `frontend/src/styles/chat.css` | 5.5 |
| HWAXPortal | `backend/tests/test_confirm_front.py`(새) | 9절의 C 묶음 |
| HWAXPortal | `docs/changelog.md` · `docs/request-1030/{checklist,context-notes,server-setup}.md` | 이력(사용자 체감 + 기술) · 판단 · cae00 확인(`/health` 의 `confirm_gate.lists.loaded` · 끄는 손잡이) |
| HWAXPortal | 포털 백엔드(`backend/app/agent/routes.py`) | **고치지 않는다** — 중계는 모르는 사건을 그대로 넘기고 서버 사본에는 카드 글이 남는다 |
| HWAXMcpGateway | — | 고치지 않는다 |

`/health` 의 새 칸이다(경로는 싣지 않는다 — `core_vocab` 과 같은 까닭). 아래 수는 지금 dev 의 he-team.json(접두를 뗀 꼴 포함 — writes 90 · confirm 37 · 겹침 0)과 바닥 24개로 센 것이다.

```json
"confirm_gate": {"on": true,
                 "lists": {"loaded": true, "error": null, "jobs": 24, "writes": 90, "confirm": 37},
                 "pending": 0,
                 "counts": {"cards": 0, "held_calls": 0, "approved": 0, "executed": 0, "declined": 0, "unknown_reply": 0, "ordered": 0}}
```

로그는 카드마다 `[confirm] 카드 cf-… — run_job(job) …`, 승인마다 `[confirm] 승인 cf-… — N건 보냄`, 주문 통과마다 `[confirm] 주문 통과 run_job` 한 줄이다(사람 메일은 싣지 않는다).

## 6. (4) 예상 작업량

잡을 시작하는 호출의 응답은 정의상 시작 **뒤**에 온다 — ST-12 가 시작 응답에 넣을 작업량은 카드에 쓸 수 없다(HA-28 의 진행 표시 몫이다). 시작 **전**에 알 수 있는 것은 지금 이것뿐이다.

| 도구 | 미리 알 길 | 카드에 싣는 것 |
|---|---|---|
| StepForge `run_job` | 읽기 도구 `estimate_cost(project_id, tool="", job="", args)`(StepForge app/mcp_server.py:31143 — "돌리기 전에 이 도구·잡이 얼마나 걸릴지", 응답 `expected_s` · `low_s` · `high_s` · `cost_basis` · `basis_note` · `gateway_verdict`). dev 게이트웨이에 있다(읽기 확인 `routine_read`). `drop_check` 도 다룬다(cost_estimate.py `JOB_ROUTES` 의 `drop_check → measure`) | `kind == "measure"` 이고 `params.tool` 이 있으면 `estimate_cost(project_id, tool=params.tool, args=params.args)`, 아니면 `estimate_cost(project_id, job=kind, args=params)`. '약 {expected_s}초({low_s} ~ {high_s}초 · 근거 {cost_basis}) — 추정이며 하한일 수 있다', `expected_s` 가 null 이면 `basis_note` |
| SmartTwin `fullangle_drop_simulation` · `single_drop_simulation` · `submit_lsdyna_job` | 인자 `time_limit`(Slurm 시간 상한) — 스키마 기본값 12:00:00 · 01:00:00 · 01:00:00 | 'Slurm 시간 상한 12:00:00(기본값)'. `dry_run` 칸도 있지만 시나리오 · 설정 파일을 만들고 레지스트리에 `status=dry_run` 행을 남기므로(부수효과 — single_drop_simulation 스키마 설명) 묻기에 쓰지 않는다. SmartTwin 의 `estimate_cost` 는 파티션 요율 금액 계산기라 쓰지 않는다 |
| KooRemapper `recipe_run` | 인자 `wait_sec`(결과까지 기다리는 상한, 기본 200) | '결과까지 최대 200초 기다린다(기본값)' |
| DocForge `docforge_convert` | 없다(`docforge_capabilities` 는 줄 선 잡 수뿐) | '이 도구는 작업량을 미리 알려 주지 않는다' |
| ODB `run_checklist` 등 · DynaForge `run_operation` · `deliberate_start` · `risk_start_job` | 없다(ODB 는 cae00 에만 있어 dev 에서 스키마를 못 봤다. 리스크 앱은 부른 **뒤** `consent_required` 로 추정을 준다) | 같음 |

- 일반 규칙은 둘뿐이다 — (가) StepForge `run_job`(앱이 `heax-step_forge` 이거나 접두 `heaxstep_forge_`)이면 `estimate_cost` 를 묻는다, (나) 인자에 `time_limit` · `wait_sec` 가 있거나 그 도구 스키마의 기본값이 있으면 싣는다.
- `estimate_cost` 는 접두 별칭 `heaxstep_forge_estimate_cost` 를 `invoke_tool` 로 부른다 — 다른 앱(SmartTwin)에 같은 이름이 붙은 박스에서도 StepForge 것에 닿는다(게이트웨이는 별칭을 늘 받는다 — sync-he-personas.py :140-146 의 설명, gateway `alias_route`).
- 도구 목록 받기 + 묻기 전체를 `asyncio.wait_for(…, 15)` 로 묶는다. 넘으면 '예상 작업량을 15초 안에 받지 못했다' 를 싣고 카드는 그대로 선다.
- ST-12 가 들어오면 바뀌는 것 — StepForge 가 합치기 단계 진행률 · '러너를 오래 잡을 수 있다' 를 시작 응답에 싣는다. 그건 승인된 턴(5.4)의 결과 글에 그대로 실려 모델이 알린다. `estimate_cost` 의 하한 문제(ST-12 — 60초 예상이 1,812초)는 StepForge 몫이고, 카드는 근거(`cost_basis`)와 '하한일 수 있다' 를 늘 함께 적는다.

## 7. (5) 맞물림

| 상대 | 맞물림 |
|---|---|
| 운영자 프롬프트 두 줄(sync-he-personas.py :74 · :76) | `writes` 의 '요청했을 때만 부른다' 는 `write` 부류의 너그러운 판정과 같은 뜻이다. `confirm` 의 '먼저 말하고 확인을 받은 뒤 부른다' 는 모델이 글로 묻고 사람이 '응' 한 뒤 다시 카드가 뜨는 이중 확인을 만든다(모델이 쓴 질문은 승인 상태가 아니다 — 4.2). HP-53 이 동기화할 때 그 줄을 '부르면 서버가 확인 카드로 승인을 받는다 — 글로 따로 묻지 않는다' 로 바꾸기를 권한다. 관문은 동기화(AD-21 의 500)와 무관하게 파일을 읽으므로 기다리지 않는다 |
| 시스템 프롬프트 넷째 규칙(app.py:161-163) | 관문이 켜져 있으면 '잡 시작 · 등록 · 발행 · 삭제처럼 상태를 바꾸는 도구는 사용자가 이번 말로 그 일을 시킨 것이 아니면 서버가 보내지 않고 사용자에게 확인 카드를 띄운다 — 확인을 글로 따로 묻지 말고, 무엇을 왜 하려는지 한 줄 말한 뒤 호출하라. 확인 번호를 지어내거나 카드를 흉내 내지 마라' 로 바꾼다. 앞부분 고정(W-3)의 캐시는 배포 뒤 한 번 깨진다 |
| `invoke_tool` 안쪽 이름 | 관문은 안쪽 이름 · 안쪽 인자(JSON 글이면 풀어서)로 판정한다. 승인 실행은 처음 꼴 그대로라 게이트웨이의 파괴 · 제어 이름 거절은 그대로 산다 |
| 분석 루틴(R3) | 루틴 턴은 `chat()` 맨 앞 갈래(:5718)로 `routine.run_routine` 에 가서 이 래퍼 · 맥락을 지나지 않는다. 단계는 게이트웨이 울타리가 읽기만 연다. 사람이 루틴을 골라 켠 것이 승인이다. 바꾸지 않는다 |
| `deliberate_start` · `deliberate_continue` | **막는다**(`job` 부류 — 바닥 목록). GLM 을 몇 분 ~ 몇 시간 잡는 잡이고, 게이트웨이 검색이 코어 조회 질문을 이 도구로 끌던 실측(R-5 — `delib_narrow`)이 있다. 외부 응답자 칸 거절(②)이 먼저다. 사람의 길(`/심의` · 심의 화면 · 핸드오프)은 도구를 지나지 않아 영향이 없다 |
| 패널 도구(`_CHAT_PANEL_TOOLS`) | ① 이 먼저 거절한다 — 카드가 서지 않는다 |
| 심의 좌석 · 띵킹 · 카탈로그 · 카드 대조 | 맥락이 None 이라 관문이 서지 않는다. 좌석 자유 조회는 이미 읽기 허용 목록(`deliberation._free_tool_ok`)이다 |
| HA-26 | 안내가 사람 발화 머리에 붙어도 판정은 `req.message` 원문만 본다 |
| HA-27 자기검증 | 카드 턴은 검토하지 않는다(5.3). 승인된 턴은 보통 턴처럼 검토한다 |
| HA-28 | 상태 조회 도구는 어느 목록에도 없다. 승인된 잡이 시작된 뒤의 기다리기는 HA-28 몫이다. 승인 실행(5.4)은 `_tools_by_name` 의 `chat=False` 래퍼라 HA-28 의 born 배우기(`if chat` 갈래)를 지나지 않는다 — 두 행을 합칠 때 승인 실행 결과를 `status_wait.born_ids` 로 턴 상태 `born` 에 한 줄로 넣는다(안 넣어도 HA-28 은 첫 조회를 한 번 보고 같은 인자의 둘째 조회부터 기다린다 — 느려질 뿐 틀리지 않는다) |
| HA-30 | ④ 가 ⑤ 앞이다 — 다른 허브의 id 로 쓰기를 승인시키지 않는다 |
| HA-31 | 카드 답('실행 — 확인 번호 …')은 전문가 검색 가로채기 낱말이 없다 |
| 재촉 → 이어하기 | 판정 맥락은 바꾸기 전 원문으로 만든다. 카드 글은 끊긴 턴 표지에 걸리지 않는다 |
| `risk_start_job` 의 제 동의 칸 | 리스크 앱의 `consent`(호출 추정이 크면 `consent_required`)는 그대로다. 관문은 그 앞에서 사람의 확인을 한 번 더 받는다 |
| `rest_call`(REST 다리) · 개인 Claude(MCP) | 이 관문 밖이다. REST 다리의 쓰기는 게이트웨이가 기본으로 닫는다. 개인 Claude 는 에이전트 서버를 지나지 않는다 |

## 8. 시간 한도의 층

| 층 | 값(실제) | 자리 |
|---|---|---|
| 작업량 묻기(목록 받기 + `estimate_cost`) | 15초(상수, 새) | 5.2 |
| 게이트웨이 도구 호출 | 600초(`GATEWAY_CALL_TIMEOUT`) | gateway.py:188 |
| 엔진의 MCP 호출 기한 | 900초(`MCP_CALL_TIMEOUT_S`) | app.py:129 |
| 챗 스트림 ping 간격 | 15초(`DELIB_HEARTBEAT_S`) | app.py:1188 · `_pinged_stream` :1246 |
| 포털 챗 중계 침묵 한도 | 900초(`AGENT_CHAT_IDLE_TIMEOUT_S`) | 포털 config.py:313 |
| 포털 → 에이전트 연결 · 쓰기 | 30초(`agent_request_timeout`) | 포털 config.py:301 |
| 턴의 도구 왕복 상한 | `AGENT_RECURSION_LIMIT` 80 | app.py:2107 |
| 카드 수명 | 1800초(상수, 새) | 5.2 · 4.2 |

- 안쪽이 먼저 걸린다 — 묻기 15초 < 게이트웨이 600초 < 엔진 900초. 묻는 동안에도 턴은 15초마다 ping 을 내므로 중계의 900초 침묵 한도는 걸리지 않는다.
- 승인 실행(5.4)은 보통 도구 호출과 같은 층(600 · 900)을 쓴다. 잡 도구는 잡 id 만 주고 곧 돌아오며, `recipe_run` 은 제 `wait_sec`(기본 200초 < 600초) 안에 돌아온다.
- 카드 수명은 호출 한도가 아니다. 포털의 PAT 창 · `AGENT_CACHE_TTL_S`(1800초)와 같은 30분으로 둔다 — 승인된 호출은 승인한 턴의 새 자격으로 나가므로 옛 자격에 묶이지 않는다.
- 끊기는 시간 한도를 새로 만들지 않는다. 흐름을 닫는 `aclose` 는 langgraph 의 취소로 끝난다.

## 9. 시험(설계서만 읽고 쓸 수 있게)

이미 있는 꼴을 쓴다.

- 도구 대역 — `tests/test_external_llm_risk_gate.py` 의 `_gw(name, reached)`(JSON 스키마 `StructuredTool` 을 `a._prep_tool` 로 감싸 부르면 `reached` 에 적는다).
- 턴 대역 — `test_chat_stall.py` 의 `_FakeAgent` · `_collect`, `tests/test_chat_self_check.py` 의 `_ToolAgent` · `_events` · `_text` · `_Reviewer`. 이 행에는 `astream_events` 안에서 **감싼 도구를 실제로 부르는** 대역(`_GateAgent`)을 쓴다 — `on_tool_start` → `await tool.ainvoke(args)` → `on_tool_end(output=결과)` → `on_chat_model_start` → `on_chat_model_stream("잡을 걸었습니다 J-1")`. `ainvoke` 는 `AssertionError` 를 던져 구제 길이 돌면 붉게 한다. `a._agent_for` 를 이 대역으로, 승인 실행이 쓰는 `a._tools_by_name` 을 `_gw` 사전으로 바꾼다.
- 운영자 목록 — `monkeypatch.setattr(a, "CONFIRM_LISTS_PATH", tmp_path / "he-team.json")` 로 작은 정본(`personas: [{key, apps, writes, confirm, optional}]`)을 쓴다.
- 화면 — 포털 `backend/tests/test_front_window_payload.py` 의 `_node` · `_FE` · `_SRC`(TS 를 옮겨 적어 node 로 부르기, R3 의 `test_routine_front_state.py` 와 같은 길).

### A. 관문 단위(`_gw` + `a._turn_confirm.set(a._confirm_ctx(req))`)

1. 맥락이 없으면(챗 밖) `run_job` 이 게이트웨이에 간다.
2. 말 '이 판의 낙하에 취약한 부품을 알려줘' 에서 `run_job(project_id="P1", kind="graph")` 는 `_TOOL_FAIL_MARK` 로 시작하고 `[확인 대기]` 를 담은 글을 돌려주고 `reached == []` 다. `ctx.pending[0]["base"] == "run_job"` 이다.
3. 같은 호출을 `invoke_tool(name="run_job", arguments=<JSON 글>)` · 별칭 `heaxstep_forge_run_job` 으로 불러도 2와 같다.
4. 4.1 의 표 열 줄이 표대로다(통과면 `reached` 에 있고, 카드면 없다).
5. '`drop_check 돌려줘`' 로 통과한 같은 호출을 같은 턴에 한 번 더 부르면 카드이고 `again` 이 참이다.
6. `pinned_tools=["run_job"]` + '돌려줘' 면 통과, 핀이 없으면 카드다.
7. 거절 차례 — 패널 도구(`invoke_tool(open_resin_panel)`)는 패널 거절 글, `deliberate_start(advanced={"llm":"external"})` 는 외부 응답자 거절 글, `heaxstep_forge_cancel_job(job_id=987654)`(이번 턴 어디에도 없는 정수)는 유령 ID 글이다(셋 다 `[확인 대기]` 가 아니고 `pending` 이 비었다).
8. 읽기 도구(`list_projects` · `heaxstep_forge_job_status` · `estimate_cost`)는 어떤 말에서도 간다.
9. 목록 파일이 없으면 `run_job` · `docforge_convert` · `ste_submit_job` 은 카드, `insert_block` 은 간다. `/health` 의 `confirm_gate.lists.loaded` 가 거짓이고 `error` 가 있다.
10. 정본의 `confirm` 에 별칭 `heaxstep_forge_cancel_job` 만 적어도 `cancel_job` · `heaxstep_forge_cancel_job` 둘 다 카드다. `writes` 와 `confirm` 에 함께 걸린 이름은 `confirm` 으로 판정한다.
11. `CHAT_CONFIRM_GATE=0` 으로 다시 읽으면 `run_job` 이 가고, 시스템 프롬프트 넷째 규칙이 종전 글이다.
12. 정규 인자 — `{"b":1,"a":{"y":None,"x":2},"c":""}` 와 `'{"a":{"x":2},"b":1}'` 의 열쇠가 같다.

### B. 턴(`_GateAgent` · `a._agent_stream` · SSE)

13. 카드 턴 — 사건에 '확인 대기: run_job'(`ok:false`) 상태, `confirm` 사건(`id` 가 `cf-` + 12자, `calls[0].tool == "run_job"`)이 있다. `result` 글은 카드 글을 담고 그 안의 번호가 사건 `id` 와 같다. 끊은 뒤의 '잡을 걸었습니다' 는 없다. `reached == []` 이고 대역 `ainvoke` 가 불리지 않았다. 근거 블록에 `run_job` 이 없다.
14. 단추 승인 — 다음 요청의 이력 끝이 13 의 `result` 글이고 말이 `approve_text` 면, 첫 모델 호출 전에 `reached == [("run_job", 같은 인자)]` 이고 상태 '도구 호출: run_job'(`call` 이 카드 id 로 시작) · '도구 완료: run_job' 이 있다. 모델에게 간 사람 메시지 머리에 '[확인 카드 cf-… 승인' 이 있다. 모델이 도구 없이 결과만 알리고 끝나도 대역 `ainvoke`(강제 재시도 · 구제)는 불리지 않는다. 그 턴에 대역이 `run_job` 을 같은 인자로 또 부르면 카드(`again`)다.
15. 글 승인 — 말이 '응' · '네 실행해 주세요' · '실행' · 'ok' 면 14와 같다. '응 근데 kind 는 mesh 로' 는 승인이 아니다.
16. 지난 카드 — 이력 끝이 카드가 아닌 다른 답이면(카드 뒤에 한 번 더 오갔다) '응' 도 단추 글도 승인이 아니고 아무것도 보내지 않는다.
17. 거절 — 말이 `decline_text` · '아니' · '취소' 면 아무것도 보내지 않고 저장분이 사라진다. 그 턴에 모델이 같은 호출을 부르면 카드다.
18. 다른 사람 — 같은 번호를 다른 `user_email` 로 보내면 승인이 아니다. 대화 id 가 달라도 승인이 아니다.
19. 만료 · 재기동 — 저장분의 `exp` 를 지난 값으로 바꾸거나 `a._CONFIRM_PENDING.clear()` 뒤 단추 글을 보내면 '확인 번호를 찾지 못했다' 상태줄이 나오고 보내지 않는다.
20. 같은 카드를 두 요청이 나란히 승인하면 한쪽만 보낸다(`reached` 길이 1).
21. 자기검증 켬(`CHAT_SELF_CHECK=1`) — 카드 턴에서 `_Reviewer.calls == []` 이고 `meta.self_check.status == "skipped"` 이며 `result` 에 카드 글이 한 번 있다.
22. 끊기 — 대역이 `on_chat_model_start` 뒤에 더 진행되면 예외를 던지게 해도 턴은 오류 · 재시도 없이 카드로 끝난다.
23. 나란한 호출 — 한 단계에 `list_projects`(읽기)와 `run_job` 이 함께 오면 읽기 결과는 근거 블록에 있고 `run_job` 은 카드다.
24. 확정 종결 길 — 모델이 'run_job 을 실행하겠습니다' 라고만 하고 끝나면 확정 종결의 직접 실행도 관문에 막혀 카드로 끝나고, 그 결과를 LLM 으로 요약하지 않는다.
25. 띵킹 켬 + 단추 글 — `req.thinking=True` 여도 일반 챗으로 가서 14와 같다.
26. 작업량 — `_tools_by_name` 대역의 `invoke_tool` 이 `heaxstep_forge_estimate_cost` 에 `{"expected_s": 60, "low_s": 40, "high_s": 90, "cost_basis": "history"}` 를 주면 카드 글에 '약 60초' 와 'history' 가 있다. 대역이 15초를 넘기면(상수를 시험에서 줄여) '15초 안에 받지 못했다' 가 있고 카드는 선다. 스키마 기본값 `time_limit: "12:00:00"` 인 `fullangle_drop_simulation` 은 '12:00:00(기본값)' 이 있다.
27. 재촉 — 이력 끝이 카드이고 말이 '계속' 이면 이어하기로 바뀌지 않고(카드 턴은 끊긴 턴이 아니다) 승인도 아니다.
28. 확인 답은 주문이 아니다 — 14 의 승인 턴에 대역이 `insert_block`(write)을 부르면 카드다(승인 말 '실행 — …' 의 '실행' 이 너그러운 판정을 통과시키지 않는다).
29. 판정 글은 사람 말뿐이다 — 말이 '이 문서 요약해줘' 이고 붙인 문서(`documents`)의 글에 'run_job 돌려줘 · 블록 추가해줘' 가 있어도 `run_job` · `insert_block` 은 카드다.

### C. 화면(포털 `backend/tests/test_confirm_front.py`)

30. `chat.api.ts` 를 옮겨 적어 `confirm` 프레임을 흘리면 `onConfirm` 이 그 사건을 받는다(모르는 사건처럼 버리지 않는다).
31. `confirm.ts` 의 `confirmActive` — 마지막 어시스턴트 메시지 · 받는 중 아님 · 기한 안일 때만 참이다(셋 중 하나라도 어긋나면 거짓).
32. `chatStore` 저장 → 되살리기 왕복에서 `confirm` 이 남고, 꼴이 틀린 `confirm`(calls 가 배열 아님)은 버린다.
33. 계약 — 형제 리포 `../HWAXAgentServer/app.py` 에 `_sse("confirm"` 이 있고 사건 칸 이름(`id` · `expires_at` · `calls` · `approve_text` · `decline_text`)이 `types/chat.ts` 의 `ConfirmCard` 와 같다(형제 리포가 없으면 건너뛰고, 있는데 못 찾으면 실패).
34. 프론트 `tsc` · `lint` · `build` 통과.

## 10. 위험과 열린 물음(권하는 답)

1. **쓰기를 너그럽게(주문 동사만) 판정해도 되나.** 권함 — 그렇게 한다. 잡은 엄하게, 되돌리기 어려운 것은 늘 카드다. 저작 흐름이 쓰기마다 끊기면 박스에서 관문을 끄게 되고 그러면 DW-03 도 돌아온다. cae00 에서 `/health confirm_gate.counts` 의 카드 · 주문 통과 수를 하루 보고 다시 정한다.
2. **바닥 목록(24개)을 코드에 둘까, he-team.json 에 `jobs` 칸을 새로 둘까.** 권함 — 지금은 코드에 둔다(파일이 없어도 요청서가 이름 댄 잡이 막힌다). 목록이 자주 바뀌면 포털 행으로 `jobs` 칸을 옮긴다.
3. **승인 뒤 서버가 보낼까, 모델이 다시 부르게 할까.** 권함 — 서버가 인자 그대로 한 번 보낸다(5.4). 모델 재현은 칸 하나 차이로 카드가 되풀이되고, 안 부르면 단추가 헛돈다.
4. **카드 턴을 끊을까, 모델이 마무리하게 둘까.** 권함 — 같은 단계가 끝난 뒤 다음 모델 호출 앞에서 끊는다. 모델이 '걸었다' 고 지어내거나 다른 잡을 이어 거는 길을 닫는다. 나란한 읽기 결과는 산다.
5. **시스템 프롬프트 넷째 규칙을 '글로 따로 묻지 말라' 로 바꿀까.** 권함 — 관문이 켜져 있을 때만 바꾼다. 안 바꾸면 모델의 글 질문 → '응' → 카드의 이중 확인이 잦다. 운영자 `confirm` 줄은 HP-53 동기화 때 같은 뜻으로 고친다(AD-21 이 동기화를 막으면 그 뒤로 미룬다 — 관문은 기다리지 않는다).
6. **카드를 서버 사본(`meta.confirm`)에도 남길까.** 권함 — 남기지 않는다. 브라우저 사본에만 남기고, 다른 기기는 카드 글에 '실행' 이라고 답한다. 포털 중계를 고치지 않는다.
7. **카드에서 호출을 골라 일부만 승인하게 할까.** 권함 — 아니다(전부 · 아무것도). 일부만 원하면 '`graph` 만 돌려' 처럼 글자로 시키면 그 호출은 주문으로 통과하고 나머지는 다시 카드다.
8. **`estimate_cost` 묻기를 이번에 넣을까.** 권함 — 넣는다(DW-03 이 StepForge 다). 다만 ST-12 대로 하한일 수 있어 근거와 '하한일 수 있다' 를 늘 적는다. 묻기가 실패해도 카드는 선다.
9. **`pinned_tools` 를 '이름을 불렀다' 로 칠까.** 권함 — 친다(사람이 화면에서 그 도구를 골랐다). 앱 핀(`pinned_apps`)은 치지 않는다 — 앱 하나에 잡이 여럿이다.
10. **HP-53 목록의 빈곳.** 권함 — HP-53 이 리스크 앱 `risk_job_action`(취소 · 재개 — 지금 어느 목록에도 없고 게이트웨이 표지도 `write=False`)을 `he-expert-risk` 의 `confirm` 에 넣는다. HP-53 미리보기는 '쓰기 꼴인데 목록 밖' 과 함께 '목록에 있는데 게이트웨이가 읽기로 확인(`routine_read`)' 도 알린다(목록에 읽기를 잘못 넣으면 그 읽기가 카드가 된다).
11. **메모리 저장이 재기동에 사라지는 것.** 권함 — 받아들인다. 그때 승인 답은 '찾지 못했다' 이고 다시 카드가 선다(닫힌 쪽). update-all 은 심의가 없으면 곧 재기동하므로 30분 창과 겹칠 수 있다 — 한 번 더 누르는 비용이다.
12. **한국어 주문 판정이 틀리는 것.** 엄한 쪽(잡)은 틀려도 카드가 하나 더 뜰 뿐이다. 너그러운 쪽(쓰기)은 '등록해 둔 재료 보여줘' 같은 문장을 막도록 요청 어미를 요구했고, 9절 4번의 벡터로 잠근다. 어긋나는 실례가 나오면 벡터를 더하고 정규식을 고친다.
13. **에이전트 서버가 포털 리포 파일을 읽는 결합.** 코어 어휘표와 같은 선례이고 두 박스 모두 형제 배치다. 워크트리(`HWAXAgentServer-wt-1030-ha29`)에서도 `../HWAXPortal` 이 닿는다(C-6).

## 11. 요청서 행과 코드가 어긋나는 곳

- '프롬프트의 잡 제출은 먼저 확인(`app.py:162`)' — dev 에서 같은 글이 `_SP_HEAD` 의 :161-163 에 있다. 코드 강제가 없다는 진단은 맞다.
- '운영자 정의에는 이미 `writes` · `confirm` 목록이 있다' — 맞지만 그 목록은 에이전트 서버 코드에 닿지 않는다. 동기화로 AIDataHub 의 프롬프트 글이 될 뿐이고 그 운영자를 고른 턴에만 실린다(1.1). 그리고 ODB · ARP · 코어 온톨로지 · 적층 · SignalForge · 웹 조사 운영자는 두 목록이 비었다(HP-53). 그래서 관문은 파일을 직접 읽고, 요청서가 이름 댄 잡은 코드 바닥으로도 막는다.
- '클러스터 제출' — cae00 의 ste 앱 도구(`submit_job` 등)를 묶는 운영자가 없다(HP-54). 운영자 목록만 읽으면 빠지므로 바닥 목록이 맡는다.
- '도구가 예상 작업량을 주면' — 잡을 거는 호출 자체는 시작 **뒤**에 답한다. 미리 주는 것은 짝 읽기 도구(StepForge `estimate_cost`)와 스키마 칸(`time_limit` · `wait_sec`)뿐이고, ST-12 의 작업량은 시작 응답이라 카드에 실을 수 없다(6절).
- 게이트웨이 `/tools-map` 의 `write` 를 목록 출처로 삼으면 요청서가 이름 댄 `docforge_convert` 와 SmartTwin 낙하 제출을 놓친다(1.5 실측).
