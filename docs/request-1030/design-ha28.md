# HA-28 설계 — 잡 상태 조회는 코드가 기다린다

요청서 정본 [`../request_261030.md`](../request_261030.md) 1절 HA-28 · 7절 'DW-02 후속 · DW-03(후속 포함)'. 판단 기록 [`context-notes.md`](context-notes.md).
이 글은 설계만 적는다(구현 전). 줄 번호는 dev HEAD `7ca3a2e`(HWAXAgentServer) 기준이고, 요청서의 `app.py:1317` 은 cae00 판 `969e723` 의 줄이다.

## 0. 한 줄

상태 조회 도구(이름 목록으로 안다)가 '도는 중' 을 돌려주면, **이 턴에 건 잡이거나 같은 호출의 되풀이일 때만** 도구 래퍼 안에서 코드가 10초마다 같은 호출을 다시 하며 끝나거나 턴의 상한(600초)에 닿을 때까지 기다린다. 그동안 LLM 은 부르지 않고, 화면에는 진행 줄을 흘리고, LLM 에는 마지막 결과 하나와 '코드가 얼마나 기다렸고 끝났는지 · 상한인지' 한 줄만 넘긴다.

## 1. 요청 행

- 무엇이 — DW-02 후속. run_checklist 를 건 뒤 get_task 를 26번 불렀고 LLM 요청이 29번 · 85초였다. 끝을 못 보고 저장된 옛 결과로 답했다. 같은 도구 네 번째의 '앞 결과를 써라' 꼬리는 폴링에 맞지 않는다.
- 할 일 — 상태 조회 도구(get_task · job_status · heaxstep_forge_job_status · docforge_status · doe_status · study_get 등)는 코드가 간격(예 10초) · 상한(예 10분)까지 기다렸다가 끝났거나 상한에 닿은 결과만 LLM 에 넘긴다. 기다리는 동안 화면에 진행률을 흘린다.
- 다시 볼 시험 — DW-02 후속 · DW-03 후속('상태 조회가 LLM 왕복 없이 기다린다').
- QA 원문(`qa-digital-worker/QA-DIGITAL-WORKER-20261030.md`)은 이 박스에 없다. 위 수치는 요청서 글 그대로다.

## 2. 지금 동작(코드 근거)

### 2.1 도구 래퍼 `_cap_tool.capped`(app.py:1832 · 1886)

챗에 묶는 도구는 `_agent_for`(2926)가 `_prep_tool(t, arg_defaults=_CHAT_ARG_DEFAULTS, chat=True)`(3012)로 감싼다. 심의 · 카탈로그 · 확정 종결의 직접 실행은 `deliberation._tools_by_name`(1848)이 `chat=False` 로 감싼다. `capped` 의 차례는 이렇다.

1. invoke_tool 거절 — 외부 응답자 과제 도구 · 패널 전용 도구(1889-1903).
2. 외부 응답자 심의 · 반출 동의 칸 거절(1904-1918).
3. 유령 ID 게이트 — 이번 턴 출처 없는 정수 id(1919-1937, `_phantom_id_arg` 1606).
4. 인자 기본값 채우기(1938-1953).
5. 부르기 `out = await orig(*a, **kw)`(1955). 예외는 ✖ 문구로 바꿔 돌려준다(1956-2001).
6. 경유면 안쪽 이름(`_eff`, 2003-2005) → `_chat_result_note`(머리 · 되풀이 꼬리, 2006) → `_fold_hub_result` → `_cap` → `_maybe_repair_hint` → `_learn_ids` → `머리 + 본문 + 꼬리`(2007-2013).

래퍼는 에이전트 캐시(30분)와 함께 재사용되므로 턴 상태는 문맥 변수로 읽는다(`_turn_ids` 1410 · `_turn_tool_calls` 1413, 턴 시작에서 4841-4842 로 세운다).

### 2.2 되풀이 꼬리 두 가지

- `_chat_result_note`(1813) — 같은 노출 이름을 이 턴에 네 번째부터 부르면 결과 끝에 '앞 결과로 답할 수 있는지 먼저 보라. 같은 조건으로 다시 부르면 결과가 같다' 를 단다(`_TOOL_REPEAT_NOTE_AT = 4`, 1414 — cae00 판의 `app.py:1317` 이 이 상수 줄이다).
- `_agent_stream_turn` 의 on_tool_start(5224) — 같은 이름 · 같은 인자가 `TOOL_REPEAT_WARN`(3, 2109)번째면 화면에 '같은 호출 반복 감지 — 결과가 바뀌지 않습니다' 를 낸다.

둘 다 '다시 불러도 결과가 같다' 를 전제한다. 상태 도구는 결과가 바뀌므로 둘 다 틀린 말이다.

### 2.3 턴의 스트림

- `_agent_stream_turn`(4807)이 `agent.astream_events(..., version="v2")`(5169)를 돌며 사건을 SSE 로 바꾼다. 도구 시작 · 끝은 `status`(5246 · 5289), 루프 입력 맞추기는 사용자 사건 `on_custom_event` 이름 `hwax_loop_fit` → `warning`(5209-5219)이다.
- 그 사용자 사건은 `_loop_fit_prompt`(3178)가 `adispatch_custom_event(..., config=config)`(3187)로 낸다. 주석대로 파이썬 3.10(이 venv)은 비동기 사건에 실행 맥락이 저절로 따라가지 않아 config 를 넘겨야 한다.
- 도구가 도는 동안 스트림 소비자는 그래프 사건이 와야 깬다. 그래서 문맥 변수 목록(`_TURN_IMAGE_EVENTS` 꼴)에 쌓아 두면 도구가 끝난 뒤에야 흘러 나간다. 도는 중에 흘리려면 사용자 사건이어야 한다.
- 챗 스트림은 `_pinged_stream`(1246)이 감싼다(5770). `DELIB_HEARTBEAT_S`(15초, 1188) 동안 아무 프레임이 없으면 `ping` 을 낸다. 구독이 끊기면(중지 · 탭 닫기) 턴 태스크를 취소한다(1284-1286).
- 자기검증 감싸개 `_self_checked_turn`(4611)은 token 만 생각 칸으로 돌리고 status 는 그대로 흘린다(4642).
- 포털 중계는 `tool` 이 있는 status 만 서버 사본의 활동(activity)에 남긴다(HWAXPortal `backend/app/agent/routes.py:2691`). 화면은 status 의 step 을 상태 줄로 보이고, 직전과 글이 같은 step 은 활동 목록에 다시 쌓지 않는다(`frontend/src/state/ChatContext.tsx:961-968`).

### 2.4 시간 한도(실제 값)

| 층 | 값 | 자리 |
|---|---|---|
| 게이트웨이 도구 호출 한 건 | `GATEWAY_CALL_TIMEOUT` 600초(바깥 660) | HWAXMcpGateway `gateway.py:188` |
| 엔진의 도구 호출 한 건 | `MCP_CALL_TIMEOUT_S` 900초(MCP 세션 read_timeout) | app.py:129 · 454-456 |
| 챗 LLM 한 호출 | `LLM_TIMEOUT_S` 900 · 스트림 조각 300 | 기다리는 동안 LLM 호출이 없어 무관하다 |
| 챗 스트림 침묵 신호 | `DELIB_HEARTBEAT_S` 15초 ping | app.py:1188 · 1246 |
| 포털 챗 중계 침묵 한도 | `AGENT_CHAT_IDLE_TIMEOUT_S` 900초 | HWAXPortal `backend/app/config.py:313` · `routes.py:866` |
| nginx `/agent/` 침묵 | `NGINX_AGENT_READ_TIMEOUT` 50400초 | HWAXPortal `infra/scripts/gen-nginx-conf.sh:258` |
| 챗 PAT 수명 | `CHAT_PAT_TTL_S` 86400초 | HWAXPortal `backend/app/config.py:255` |
| 한 턴의 벽시계 | 없다(`AGENT_RECURSION_LIMIT` 80 은 단계 수) | app.py:2107 |

DW-02 의 26번 폴링은 재귀 한도(연속 왕복 39회) 안이다. 턴을 끝낸 것은 코드가 아니라 모델이다.

### 2.5 게이트웨이 `/tools-map` 에는 '상태' 표지가 없다

dev 게이트웨이(`67d8d00` 이후)의 `/tools-map` 칸은 `map · backends · apps · areas · area_meta · unclassified · arg_scores · write · routine_read` 다(`gateway.py:6461-6475`, dev 에서 읽기 전용으로 받아 확인). 상태 도구를 가리키는 칸은 없다. `areas` 의 `sim` 은 '잡 상태 · 중지 · 재실행' 을 묶어 제출 도구까지 들어 있어 표지로 못 쓴다. `routine_read`(읽기로 확인된 도구 — `_routine_read` 4703)와 `write` 는 cae00 판 `44f4b8d` 에는 없다(`git show 44f4b8d:gateway.py` 에 0건). 에이전트 서버는 지금 `map · areas · area_meta` 만 캐시한다(app.py:2500 · 2567).

노출 이름의 접두는 이름이 겹칠 때만 붙고 꼴은 `<앱키에서 '-' 를 뺀 것>_<원래 이름>` 이다(`gateway.py:1144` · 1153-1155). `heaxstep_forge_job_status` 는 `heax-step_forge` 의 `job_status` 다.

### 2.6 앱별 상태 응답 꼴(이 박스의 소스로 확인)

| 도구(노출 이름) | 상태 칸 · 낱말 | 진행률 | 근거 |
|---|---|---|---|
| ODB 허브 `get_task`(cae00) | `status` queued · running · done · error | `progress` 0~1 실수 · `message` | ODB `api/tasks.py:21` · `api/schemas.py:69` · `api/routers/checklist.py:24-56`(run_checklist 는 같은 꼴로 queued) |
| ODB `job_status` | `status` caching · ready · error · unknown | 0~1 | ODB `api/routers/jobs.py:224` · `schemas.py:61` |
| StepForge `job_status`(`heaxstep_forge_job_status`) | `status` pending · running · done · failed · cancelled | `progress` 0~100 정수 | StepForge `app/db.py:93` · `app/mcp_server.py:1624` · run_job 은 `{job_id, status: pending}`(1249) |
| DocForge `docforge_status` | `status` queued · running · done · failed · cancelled, 오류는 `{ok:false, error, status:<HTTP 정수>}` | `progress` 0~100 정수 · `stage` | DocForge `docforge/mcp_server.py:67` · `service.py:84` · `jobs/ledger.py:27`, convert 는 `{job_id, status: queued}`(service.py:106) |
| DynaForge(KooRemapper) `get_job` | `status` queued · running · succeeded · failed · canceled | `progress` 정수 또는 null | KooRemapper `platform/backend/app/models.py:243` · `platform/mcp_server/server.py:247` |
| ste `get_job_status` | `state` PENDING · RUNNING · COMPLETED · FAILED · CANCELLED(취소 직후 CANCELLING) | 없음 | SmartTwinExplorer `backend/mcp_server/server.py:166` — 설명이 '끝날 때까지 이 도구로 폴링한다' 다 |
| AbaqusMCP `doe_status` | `state` CREATED · GENERATED · CANARY · SUBMITTED · COMPLETED · PARTIAL · CANCELLED · HALTED | counts | AbaqusMCP `packages/core/.../doe/campaign.py:47` · `packages/mcp-server/.../tools_doe.py:216` — 진행 중이면 note 가 '이 세션에서 계속 기다리지 말고 사용자에게 보고' 다 |
| SmartTwinMCP `job_status`(`smarttwinmcp_job_status`) | 맨 위 상태 칸 없음(`squeue` 사전 안) | 없음 | SmartTwinMCP `tools/job_status/1.0.0/script.sh` |
| `study_get` | 이 박스의 어느 리포에도 없다 | — | `grep` 0건 |
| `deliberate_status`(hwax-deliberation) | `status` queued · running · done · error · cancelled · interrupted | round | HWAXAgentServer `routine.py:68` |

## 3. 요청서 할 일과 코드가 어긋나는 곳

1. '도구 쪽 상태 표지' 는 없다(2.5). 이름 목록으로 간다.
2. 할 일의 예시는 노출 이름과 원래 이름이 섞여 있다. `heaxstep_forge_job_status` 의 원래 이름은 `job_status` 다. 목록은 원래 이름으로 두고 노출 이름에서 앱 접두를 벗겨 대조한다.
3. `study_get` 은 이 박스에서 확인할 수 없다. `doe_status` 는 앱이 진행 중 응답에 '이 세션에서 계속 기다리지 말라' 를 싣는다(2.6) — 기다림과 결이 다르다(8절 Q3).
4. '상태 조회 도구는 기다렸다가 끝난 결과만 넘긴다' 를 모든 호출에 걸면, 상태만 묻는 질문('잡 42 어떻게 돼 가?')이 최대 10분 붙잡힌다. 이 턴에 건 잡과 되풀이 호출로 좁힌다(4.4).
5. 꼬리는 `_chat_result_note`(dev 1813) 하나가 아니다. 화면의 '결과가 바뀌지 않습니다'(5224)도 같은 전제다. 둘 다 면제한다(4.9).

## 4. 설계

### 4.1 어디에 — 한 곳의 갈고리

새 모듈 `HWAXAgentServer/status_wait.py`(표준 라이브러리만 — app 을 읽지 않는다)에 판정 · 고리 · 문구 · 계수를 두고, app.py 는 붙이는 자리만 만진다. HA-29 · HA-30 이 같은 `capped` 를 고치므로 app.py 쪽 변경을 줄여 합칠 때 겹침을 작게 한다.

`capped` 안 차례(앞 셋은 그대로, HA-29 · HA-30 은 그 행의 설계가 정한다).

| 차례 | 무엇 | 행 |
|---|---|---|
| 1 | invoke_tool 거절 | 기존 |
| 2 | 외부 응답자 거절 | 기존 |
| 3 | 유령 ID 게이트 | 기존 |
| 4 | 다른 허브 id 관문(부르기 전) | HA-30 |
| 5 | 확인 카드 관문(부르기 전) | HA-29 |
| 6 | 인자 기본값 | 기존 |
| 7 | 부르기 — 예외면 ✖ 문구로 끝(이 갈고리는 안 탄다) | 기존 |
| **8** | **`_status_wait(...)` — 상태 도구면 기다린다 · 아니면 잡 시작 결과에서 id 를 배운다** | **HA-28** |
| 9 | 머리 · 꼬리(`_chat_result_note`, 면제 깃발을 받는다) → 접기(HA-34 계수) → `_cap` → 고침 힌트 → `_learn_ids` | 기존 |
| 10 | `머리 + 본문 + 기다림 안내 + 꼬리` | HA-28 이 안내 한 칸을 더한다 |

갈고리는 게이트를 지난 **성공한** 호출에만 돈다. 다시 조회는 `orig` 를 같은 인자로 직접 부르므로 게이트를 다시 지나지 않는다(첫 호출이 이미 지났다). 접기 · 절단 · id 배우기는 마지막 결과 하나에만 걸린다.

app.py 변경(줄은 dev 기준).

```python
_NO_RC: RunnableConfig = {}          # ⚠ 기본값을 None 으로 두지 않는다 — 3.10 의 get_type_hints 가 Optional 로 바꿔 LangChain 이 config 를 안 넣는다

async def capped(*a, _hwax_rc: RunnableConfig = _NO_RC, **kw):   # 1886
    ...                                  # 1~6 그대로
    try:
        out = await orig(*a, **kw)       # 1955
    except Exception as exc:
        ...                              # 그대로(여기서 return)
    out, _wait_note, _polled = (await _status_wait(getattr(tool, "name", ""), kw, out,
                                                   lambda: orig(*a, **kw), _hwax_rc)
                                if chat else (out, "", False))
    ...
    _head, _tail = _chat_result_note(_eff, polled=_polled) if chat else ("", "")   # 2006
    ...
    return (_head + body + _wait_note + _tail, out[1])   # 2010 · 2013 도 같은 꼴
```

- `_hwax_rc` 는 LangChain 이 넣는 실행 설정이다. `StructuredTool._arun` 이 코루틴에 `RunnableConfig` 형 인자가 있으면 그 이름으로 넣는다(langchain_core 1.4.7 `tools/structured.py:122-123`, 판정 `tools/base.py:1373-1388` 은 `type_ is RunnableConfig`). 이 venv(파이썬 3.10)에서 `= None` 이면 `get_type_hints` 가 `Optional[RunnableConfig]` 로 읽어 넣지 않는다 — 스크래치 탐침으로 확인했다(`= None` → 없음, 빈 사전 기본값 → `_hwax_rc`). 이름이 겹칠 도구 인자는 없다(앞 밑줄).
- `_status_wait`(app.py, 새 글루 함수 하나)가 하는 일 — `_inner_tool(name, kw)` 로 안쪽 이름 · 인자를 얻고, `_TOOLS_MAP_CACHE` 에서 앱 키와 `routine_read` 를 읽고(망 호출 없음 — `_app_label_cached` 와 같다), 턴 상태 `_turn_status_wait` 를 읽고, 사건 내기(`adispatch_custom_event(status_wait.EVENT, data, config=_hwax_rc)` — config 에 callbacks 가 없으면 내지 않고, 실패는 삼킨다)를 넘겨 `status_wait.handle(...)` 를 부른다. 턴 상태가 없거나(심의 · 카탈로그 · 시험의 직접 호출) 기능이 꺼져 있으면 `(out, "", False)` 를 그대로 돌려준다.
- `_agent_stream_turn` 4842 다음 줄 — `_turn_status_wait.set({"born": set(), "seen": Counter(), "spent_s": 0.0})`. 문맥 변수 정의는 `_turn_tool_calls`(1413) 옆이다. 자동 재시도 · 강제 호출 재시도도 같은 턴이라 같은 상태를 쓴다.
- 스트림 갈래 하나 — 5209 의 `elif` 옆에 `elif kind == "on_custom_event" and event.get("name") == status_wait.EVENT: yield _sse("status", status_wait.frame(event.get("data") or {}))`.
- `_TOOLS_MAP_CACHE` — 초기값에 `"routine_read": None` 을, 2567 갱신에 `"routine_read": frozenset(data["routine_read"]) if isinstance(data.get("routine_read"), list) else None` 을 더한다(옛 게이트웨이는 None — '모름').
- import 둘 — `from langchain_core.runnables import RunnableConfig` · `import status_wait as _status_wait_mod`.
- `/health` — 7220(`self_check`) 다음 줄에 `"status_wait": _status_wait_mod.health()`. HA-34 의 `hub_fold` 는 `tool_cut`(7225) 뒤라 겹치지 않는다.

### 4.2 상태 도구 알아보기

```
BUILTIN = {"get_task", "job_status", "get_job_status", "get_job", "docforge_status", "doe_status", "study_get"}
```

- 원래 이름 `base` — 노출 이름이 `map` 에서 앱 키 `k` 를 가지고 `k.replace("-", "") + "_"` 로 시작하면 그 접두를 벗긴 것, 아니면 노출 이름 그대로. 소문자로 견준다.
- 상태 도구 = `base ∈ BUILTIN ∪ EXTRA` 이고 아래 울타리를 지난다.
  - 게이트웨이가 `routine_read` 를 주면(새 판) 노출 이름이 그 안에 있어야 한다 — 읽기로 확인된 것만 되풀이해 부른다.
  - 주지 않으면(옛 판 `44f4b8d`) `BUILTIN` 만 연다. 박스 덧붙임 `EXTRA` 는 울타리가 있을 때만 먹는다 — 잘못 적은 쓰기 도구(`run_job` 등)를 10초마다 부르는 사고를 막는다.
- 넣지 않는 것 — `deliberate_status`(심의는 시간 단위, 웹 심의는 `/심의` 길이 따로 흘린다), `job_log` · `list_jobs` · `*_system_status`(잡 하나의 상태가 아니다), `get_job_details`(레지스트리 상세 — 확인 안 함).
- 기능이 꺼져 있으면(`CHAT_STATUS_WAIT_MAX_S=0`) 어떤 이름도 상태 도구가 아니다 — 종전 그대로(꼬리 포함).

### 4.3 결과에서 상태 읽기 `job_state(text)`

- 결과 글 — 어댑터 반환은 `(내용 조각 목록, artifact)` 이다(`content_and_artifact`, langchain_mcp_adapters 0.3.0 `tools.py:226-280`). 조각의 `text` 를 이어 붙인다. `_norm` 은 그림을 아티팩트로 저장하는 부작용이 있어 중간 조회에는 쓰지 않는다(마지막 결과만 종전 길로 간다).
- JSON 객체가 아니면 `None`(모름 — 기다리지 않는다). 배열도 `None`.
- 볼 사전 — 맨 위, 그다음 맨 위의 `job` · `task` · `campaign` · `study` · `run` · `data` 칸이 사전이면 그것. 처음 걸린 것을 쓴다.
- 상태 낱말 — 그 사전의 `status` · `state` · `job_status` · `job_state` 차례로, **문자열**이고 아래 표에 있는 첫 값. 소문자로 바꾸고 `-` · 빈칸은 `_` 로. 정수 `status`(DocForge 오류 404 등)는 낱말이 아니다.

| 갈래 | 낱말 |
|---|---|
| 도는 중 | queued · pending · running · submitted · started · starting · in_progress · processing · caching · canary · configuring · completing · cancelling · canceling · license_wait |
| 끝 | done · succeeded · success · completed · complete · finished · ready · failed · failure · error · cancelled · canceled · timeout · timed_out · interrupted · killed · aborted · partial · halted · node_fail · preempted · out_of_memory · boot_fail · deadline · resubmitted · stopped · expired · rejected |
| 모름(기다리지 않는다) | 그 밖 전부 — created · generated · paused · suspended · held · waiting · unknown … |

- 진행률(화면에만) — 같은 사전의 `progress` · `progress_pct` · `percent` · `pct` 가운데 첫 수. 0~1 사이 **실수**면 100배(ODB), 정수면 그대로(StepForge · DocForge · DynaForge), 0~100 으로 자른다. null 이면 없음.
- 한 줄 설명(화면에만) — `message` · `stage` · `step` · `phase` 가운데 첫 문자열, 공백을 줄여 80자.
- 실패 판정기(`_result_ok`)는 쓰지 않는다. ✖ 문구 · 평문 오류는 JSON 객체가 아니라 '모름' 이 되고, `{"status": "failed"}` 는 '끝' 이다 — 둘 다 기다리지 않는다.

### 4.4 언제 기다리나

다음이 모두 참일 때만 기다린다.

1. 챗 래퍼(`chat=True`)이고 턴 상태가 있다(챗 ReAct 턴 — 심의 · 띵킹 · 루틴 · 카탈로그 길은 없다).
2. 상태 도구다(4.2).
3. 첫 결과가 '도는 중' 이다(4.3).
4. 둘 중 하나.
   - **이 턴에 건 잡** — 호출 인자 가운데 이름이 `^(id|.*_id)$`(`_ID_ARG_RE`, 1416)인 칸의 값(문자열 · 정수, 불 아님)이 턴 상태 `born` 에 있다.
   - **같은 호출의 되풀이** — 같은 원래 이름 · 같은 인자(정렬한 JSON 앞 400자)를 이 턴에 두 번째 이상 부른다(`seen` — 상태 도구 호출마다 결과와 상관없이 하나 는다).
5. 턴의 기다림 몫이 남았다(`spent_s < MAX_S`). 없으면 기다리지 않고 '몫을 다 썼다' 안내만 단다.

`born` 을 채우는 법 — 상태 도구가 **아닌** 챗 도구의 성공한 결과(글 20,000자 이하)에서 4.3 과 같은 사전을 보고, 상태 낱말이 '도는 중' 이면 그 사전의 `^(id|.*_id)$` 칸 값을 문자열로 넣는다. StepForge `run_job`(`{job_id, status: pending}`) · ODB `run_checklist`(`{task_id, job_id, status: queued}`) · DocForge `docforge_convert`(`{job_id, status: queued}`) · DynaForge `run_operation`(`{id, status: queued}`)이 걸린다. 목록 속 잡(`{"jobs": [...]}`)과 끝난 잡은 걸리지 않는다. 이름으로 '잡 시작 도구' 를 가리지 않는다 — 게이트웨이 `write` 는 `docforge_convert` · `export_step` · `remesh_parts` 를 쓰기로 보지 않는다(dev `/tools-map` 확인).

이 규칙의 결과.

| 대화 | 동작 |
|---|---|
| 'ODB 체크리스트 돌려서 결과 알려줘'(DW-02) | run_checklist → get_task 첫 호출부터 기다린다. LLM 호출은 셋(걸기 · 조회 · 답). |
| '잡 42 어떻게 돼 가?' | 한 번 조회하고 지금 상태로 답한다. 결과 끝에 '끝난 결과가 필요하면 같은 호출을 한 번 더' 안내가 붙는다. |
| '잡 42 끝날 때까지 기다렸다가 알려줘' | 첫 조회 뒤 LLM 이 같은 호출을 한 번 더 하면 그때부터 코드가 기다린다. |
| 최근 잡 목록을 보고 마지막 잡 상태 | 목록 속 id 는 born 이 아니다 — 한 번 조회. |

### 4.5 기다리는 고리

```
t0 = now; polls = 0; last = first; told = t0
phase "start" 사건
loop:
    left = budget - (now - t0)                       # budget = MAX_S - turn.spent_s(기다림 시작 때)
    await asyncio.sleep(min(POLL_S, max(0, left)))
    try:
        nxt = await asyncio.wait_for(again(), timeout=min(POLL_CALL_MAX_S, max(POLL_S, budget - (now - t0))))
    except asyncio.TimeoutError → outcome "fail"(답하지 않았다), last 그대로
    except Exception → outcome "fail"(예외 이름 · 앞 200자), last 그대로
    polls += 1
    st = job_state(text_of(nxt))
    st 가 None → last = nxt, outcome "shape"
    st 가 끝 → last = nxt, outcome "end"
    도는 중 → last = nxt; 낱말이 바뀌었거나 now - told ≥ TELL_S 면 phase "wait" 사건
    now - t0 ≥ budget → outcome "cap"
끝 사건(phase = outcome) · turn.spent_s += now - t0 · 계수 · 로그 한 줄
```

- 상한에 닿기 전 마지막 잠 뒤에도 한 번 더 조회한다 — LLM 이 받는 결과가 상한 시점의 것이다.
- 다시 조회 한 번의 한도는 `min(120, max(POLL_S, 남은 몫))` 초다. 게이트웨이 한도(600)와 `MCP_CALL_TIMEOUT_S`(900)보다 먼저 걸린다. 한도에 걸리면 그 호출을 취소한다(읽기라 안전하다).
- 예외 한 번에 멈춘다. LLM 이 같은 호출을 다시 하면(되풀이 규칙) 남은 몫 안에서 다시 기다린다.
- 같은 턴의 병렬 호출(한 메시지의 도구 둘)은 각자 기다림 시작 때의 남은 몫을 보고 돈다. 끝난 뒤 합에 더한다(보수적 — 벽시계는 그보다 짧다).
- `asyncio.CancelledError` 는 잡지 않는다(3.8 부터 `Exception` 밖이다).

### 4.6 화면에 흘리기

- 사건 이름 `hwax_status_wait`. 자료 `{phase, tool, state, progress, detail, elapsed_s, max_s, polls}` — phase 는 start · wait · end · cap · fail · shape.
- 스트림 갈래가 `status` 로 바꾼다. `tool` 은 **None** 이다 — 중계가 서버 사본 활동에 남기지 않고(routes.py:2691), 다음 턴 근거(호출 · 결과 짝)에 섞이지 않는다. 꼴은 `{"step": <한 줄>, "tool": null, "wait": {자료}}` 이다. 지금 화면은 `wait` 을 모르고 버린다 — step 만 상태 줄로 보인다(프런트 변경 없음).
- step 한 줄.
  - start — `코드가 잡이 끝나기를 기다립니다 — get_task · running 30% · 10초마다 다시 봄 · 최대 10분`
  - wait — `잡을 기다리는 중 — get_task · running 45% · running rules · 1분 30초 지남`
  - end — `잡이 끝났습니다 — get_task · done · 2분 10초 기다림`
  - cap — `기다림 상한 10분 — get_task 는 아직 running 80% · 지금 상태로 답합니다`
  - fail — `잡 상태를 다시 보지 못해 기다림을 멈춥니다 — get_task · <까닭>`
  - shape — `잡 상태를 더 읽을 수 없어 기다림을 멈춥니다 — get_task`
- 간격 — start · 끝은 늘, 낱말이 바뀌면 곧바로, 같은 낱말이면 `TELL_S`(30초)에 한 번. 10분 기다림이면 활동 목록에 20줄 남짓이다.
- 사건은 도구가 도는 동안 흘러 나온다 — 스크래치 탐침(langgraph 1.2.5 · `create_react_agent`)에서 on_tool_start 와 on_tool_end 사이에 0.2초 간격으로 왔다. 사건의 run_id 는 도구 노드(도구의 부모)라 도구 호출의 `call` 키와 잇지 않는다.

### 4.7 멈춤(사용자 중지)

■ 중지 · 탭 닫기 → 포털 중계가 상류를 닫고(routes.py:2617 주석) → `_pinged_stream` 이 턴 태스크를 취소한다 → `asyncio.sleep` · 다시 조회가 곧바로 취소된다(탐침 — 소비자 취소 0.5초 뒤 도구 안 기다림이 `CancelledError` 로 끝났다). 잡 자체는 앱에서 계속 돈다 — 기다림만 멈춘다. 잡을 끊는 것은 사람이 취소 도구로 한다(HA-29 의 확인 대상).

### 4.8 LLM 이 받는 것

`머리 + 마지막 결과(접기 · 절단 그대로) + 기다림 안내 + 꼬리(상태 도구는 비움)`. 안내는 늘 `[코드 기다림 — ` 로 시작한다(시험 · 사람이 찾는 표지).

| 경우 | 안내 |
|---|---|
| end | `[코드 기다림 — get_task 를 2분 10초 기다려(10초마다 13번 다시 조회) 끝난 상태(done)를 받았다. 위가 끝난 뒤의 결과다 — 이 결과로 답하라]` |
| cap | `[코드 기다림 — get_task 를 10분 기다렸지만 이 턴의 상한(10분)에 닿았다. 아직 끝나지 않았다(상태 running, 진행률 80%). 위는 끝나기 전의 마지막 조회다 — 이번 잡의 결과는 아직 없다. 예전에 저장된 결과를 이번 결과처럼 답하지 말고, 지금 상태와 '끝난 뒤 다시 물어 달라' 를 알려라. 이 턴에는 더 기다리지 않는다]` |
| budget | `[코드 기다림 — 이 턴의 기다림 상한(10분)을 이미 다 써 기다리지 않았다. 아직 끝나지 않았다(상태 running). 예전 결과로 대신 답하지 말고 지금 상태를 알려라]` |
| fail | `[코드 기다림 — get_task 를 3분 기다리다 다시 조회가 실패했다(<까닭>). 위는 그 전 마지막 조회다(상태 running) — 끝난 결과가 아니다]` |
| shape | `[코드 기다림 — get_task 를 1분 기다리는 사이 결과에서 진행 상태를 더 읽을 수 없어 멈췄다. 위가 마지막 조회 결과다]` |
| snapshot(기다릴 조건이 아닌 도는 중 — 4.4 의 4 가 거짓) | `[코드 기다림 — 아직 끝나지 않았다(상태 running, 진행률 30%). 진행 상태만 물었으면 지금 상태로 답하라. 끝난 결과가 필요하면 같은 도구를 같은 인자로 한 번 더 부르라 — 코드가 10초마다 다시 보며 최대 10분 기다린다(그 사이 LLM 을 부르지 않는다)]`. '최대 N' 은 이 턴에 남은 몫이고, 몫이 0 이면 이 줄 대신 budget 안내를 단다. |
| 첫 결과가 끝 · 모름 · 상태 도구 아님 | 없음 |

'예전에 저장된 결과로 답하지 말라' 는 DW-02 의 실패(끝을 못 보고 저장된 옛 결과로 답함)를 겨눈다. 시간 표기는 `N분 M초` · `M초`.

### 4.9 되풀이 꼬리 · 반복 경고 면제

- `_chat_result_note(name, polled=False)` — 호출 수는 종전처럼 센다. `polled` 가 참(상태 도구이고 결과에서 상태 낱말을 읽었다 — 도는 중이든 끝이든)이면 꼬리를 달지 않는다. 상태를 못 읽은 상태 도구(SmartTwinMCP `job_status` 등)는 종전 꼬리가 그대로다 — 코드가 기다려 줄 수 없는 꼴에서 LLM 루프를 막는 것은 여전히 꼬리다.
- on_tool_start 의 반복 경고(5224) — 안쪽 이름(`_inner_tool`)이 상태 도구면 내지 않는다. 기능이 꺼져 있으면 종전 그대로다.

### 4.10 `/health` · 로그

- `/health.status_wait = {on, poll_s, max_s, waits, ended, capped, failed}` — 기동 뒤 합, 자물쇠는 HA-34 `hub_fold` 와 같은 꼴(스레드 풀의 /health 와 이벤트 루프의 기다림). waits 는 시작한 기다림, 나머지는 끝난 갈래(shape 는 failed 에 센다 · 취소된 것은 어디에도 안 센다).
- 기다림마다 로그 한 줄 — `[status-wait] get_task: end — 130초 · 다시 조회 13번 · 상태 done`. HA-34 의 교훈(흔적이 없으면 재시험이 효과를 못 가린다)을 따른다.

### 4.11 손잡이

| 이름 | 기본 | 뜻 |
|---|---|---|
| `CHAT_STATUS_WAIT_MAX_S` | `600` | 한 턴에 코드가 잡을 기다리는 시간의 **합** 상한(초). `0` 이면 끈다 — 종전 그대로(LLM 이 폴링하고 꼬리 · 경고도 종전). |
| `CHAT_STATUS_WAIT_POLL_S` | `10` | 다시 조회 간격(초). 2 보다 작은 값은 2 로 읽는다. |
| `CHAT_STATUS_TOOLS` | 빈 값 | 상태 도구로 더할 원래 이름(쉼표). 게이트웨이가 `routine_read` 를 줄 때, 그 안의 도구에만 먹는다. |

상수(손잡이 아님) — `TELL_S` 30(진행 줄 간격) · `POLL_CALL_MAX_S` 120(다시 조회 한 번의 한도 위쪽) · 잡 시작 결과를 읽는 글 길이 20,000자. 시험은 모듈 속성을 바꿔 짧게 돈다. 기동 때 한 번 읽는다(반영은 재기동).

### 4.12 시간 한도 층

| 안쪽 → 바깥쪽 | 값 | 규칙 |
|---|---|---|
| 다시 조회 한 번 | ≤ min(120, 남은 몫) | 게이트웨이 600 · MCP_CALL_TIMEOUT_S 900 보다 먼저 걸린다 — 무엇이 느린지 우리 문구로 말한다 |
| 게이트웨이 도구 호출 | 600(바깥 660) | 그대로 |
| 엔진 도구 호출(LLM 이 부른 첫 호출) | 900 | 그대로 |
| 한 턴의 기다림 합 | 600 | 챗 PAT 86400 보다 한참 작다 |
| 침묵 | ping 15 · 진행 줄 ≤ 30(+ 다시 조회 한 번 ≤ 120) | 포털 챗 중계 900 · nginx 50400 보다 작다 — ping 을 꺼도(`DELIB_HEARTBEAT_S=0`) 침묵은 150초를 넘지 않는다 |

기다리는 동안 LLM 호출이 없으므로 `LLM_TIMEOUT_S` · 스트림 조각 한도와는 겹치지 않는다. `CHAT_STATUS_WAIT_MAX_S` 를 900 보다 크게 올려도 ping · 진행 줄이 침묵 한도를 막는다. 기다리는 동안 포털 동시 챗 퍼밋 하나(`max_concurrent_chats` 64)와 브라우저 연결 하나를 쥔다.

## 5. 다른 행과의 맞물림

- **HA-29(확인 카드)** — 부르기 **전** 관문이다(차례 5). 확인으로 멈춘 잡 시작은 결과가 없으니 born 도 없다. 사람이 확인한 턴에 잡이 걸리면 그 턴의 상태 조회가 기다린다. HA-29 의 '잡 시작 도구' 판정(이름 · writes)과 born(결과 꼴)은 시점이 달라 합치지 않는다. ST-12 가 잡 시작 응답에 '예상 작업량' 을 실으면, HA-29 확인 문구와 함께 이쪽 snapshot 안내에도 실을 수 있다(지금은 하지 않는다).
- **HA-30(다른 허브 id)** — 부르기 전 관문(차례 4)이고 허브 도구만 본다. 상태 도구와 겹치지 않는다. HA-30 이 턴의 'id → 앱' 원장을 세우면 born 을 그 원장의 한 칸으로 옮길 수 있다(합칠 때 판단 — 지금은 따로).
- **HA-34(접기 흔적)** — 접기는 차례 9 라 마지막 결과에만 한 번 걸린다. `/health` 줄은 서로 다른 자리다.
- **HA-27(자기검증)** — 검토자의 근거(outputs)는 마지막 결과 + 안내다. 안내의 수(분 · 초 · 횟수 · 진행률)는 근거 글에 들어가 '출처 없는 수' 로 잡히지 않는다.
- **HA-26** — 안내는 도구 결과 안이다. 시스템 메시지를 더하지 않는다.
- **W-5(10-29)** — 꼬리는 상태를 읽은 상태 도구만 면제한다(4.9). 나머지 도구는 그대로다.

## 6. 바뀌는 파일

- `HWAXAgentServer/status_wait.py`(새) — 이름 판정 · 상태 읽기 · born · 고리 · 안내 · 화면 프레임 · 계수.
- `HWAXAgentServer/app.py` — `capped` 인자 하나와 갈고리 한 줄 · 반환에 안내 한 칸, `_status_wait` 글루, 문맥 변수 하나와 턴 시작 한 줄, 스트림 갈래 하나, `_chat_result_note` 의 `polled`, 반복 경고 면제, `_TOOLS_MAP_CACHE.routine_read`, `/health` 한 줄, import 둘.
- `HWAXAgentServer/tests/test_status_wait.py`(새).
- `HWAXAgentServer/README.md` — Time limits 절에 손잡이 세 줄과 사슬 한 줄('chat status wait — one re-poll ≤ min(120, left) < gateway 600 < MCP_CALL_TIMEOUT_S 900, the whole wait ≤ CHAT_STATUS_WAIT_MAX_S per turn').
- `HWAXPortal/infra/env-kits/agent-server.env` — 주석 손잡이 세 줄(챗 절).
- `HWAXPortal/docs/request-1030/` — checklist · context-notes(결정) · server-setup(cae00 재시험 절차), `HWAXPortal/docs/changelog.md`(업데이트 이력).

포털 프런트 · 중계 · 게이트웨이는 바꾸지 않는다.

## 7. 시험(이 글만 보고 쓸 수 있게)

공통 — 가짜 상태 도구는 진짜 어댑터 꼴로 만든다. `StructuredTool(name=…, coroutine=…, args_schema={JSON 스키마 사전}, response_format="content_and_artifact")` 가 `([{"type": "text", "text": json.dumps(<2.6 의 실제 꼴>)}], None)` 을 돌려준다(가짜는 진짜 꼴로). 손잡이는 모듈 속성으로 줄인다(`status_wait.POLL_S = 0.02` · `MAX_S` · `TELL_S = 0`). 도구 → 앱 캐시는 `tests/test_request_1029.py` 의 `_cache(monkeypatch, mapping, labels)` 꼴로 앉히고 `routine_read` 칸도 시험마다 정한다. 실제 턴은 `tests/test_chat_loop_fit.py` 의 `_agent(monkeypatch, llm, tools)`(앱의 `_agent_for` + 게이트웨이 스텁)와 `_ScriptLLM` · `_LoopLLM` 꼴의 대본 모델, `app._agent_stream(app.app, req)` 를 쓴다(`CHAT_SELF_CHECK=0` 은 conftest 가 이미 건다).

순수 판정.

1. `status_wait.is_status_tool` — `("heaxstep_forge_job_status", "heax-step_forge", None)` → 참, `("smarttwinmcp_job_status", "smart-twin-mcp", None)` → 참, `("get_task", None, None)` → 참, `("docforge_status", …)` · `("get_job", …)` · `("get_job_status", …)` · `("doe_status", …)` · `("study_get", …)` → 참. `job_log` · `list_jobs` · `heaxkooremapper_mcp_system_status` · `deliberate_status` · `run_job` · `get_task_report` → 거짓. `routine_read = {"other"}` 이면 `get_task` → 거짓. `CHAT_STATUS_TOOLS="render_status"` 는 `routine_read` 가 None 이면 거짓, `{"render_status"}` 면 참. `MAX_S = 0` 이면 전부 거짓.
2. `status_wait.job_state` — ODB `{"task_id":"t1","status":"running","progress":0.45,"message":"running rules"}` → 도는 중 · 45 · "running rules". StepForge `{"id":"j","status":"pending","progress":0}` → 도는 중 · 0. DocForge `{"status":"done","progress":100,"stage":"S7"}` → 끝. DynaForge `{"status":"succeeded"}` · `{"status":"canceled"}` → 끝. ste `{"job_id":"x","state":"RUNNING"}` → 도는 중, `{"state":"COMPLETED"}` → 끝. AbaqusMCP `{"state":"SUBMITTED"}` → 도는 중, `{"state":"HALTED"}` · `{"state":"PARTIAL"}` → 끝, `{"state":"GENERATED"}` → 모름. DocForge 오류 `{"ok":false,"error":"잡이 없다","status":404}` → 모름. `{"status":"ok","state":"running"}` → 도는 중(첫 낱말이 표 밖이면 다음 칸). `{"job":{"status":"queued"}}` → 도는 중. `[{"status":"running"}]` · `"✖ 도구 get_task 호출 실패: …"` · SmartTwinMCP `{"ok":true,"job_id":3,"squeue":{…}}` → 모름.
3. `status_wait.born_ids` — StepForge `{"job_id":"j-1","kind":"graph","status":"pending"}` → `{"j-1"}`, ODB `{"task_id":"t1","kind":"checklist","job_id":"j1","status":"queued","progress":0.0}` → `{"t1","j1"}`, DynaForge `{"id":"01H","status":"queued"}` → `{"01H"}`, `{"jobs":[{"id":"x","status":"running"}]}` → 빈 집합, `{"job_id":"z","status":"done"}` → 빈 집합, 20,001자 글 → 빈 집합.

도구 래퍼(턴 상태를 손으로 세운다 — `a._turn_status_wait.set({"born": {...}, "seen": Counter(), "spent_s": 0.0})`).

4. born 이 `{"t1"}` 이고 가짜 `get_task` 가 running, running, done 을 차례로 준다 → `tool.ainvoke({"task_id": "t1"})` 한 번에 가짜가 3번 불리고, 반환 글에 `"status": "done"` 과 `[코드 기다림 — ` · `끝난 상태(done)` 가 있고, `번째 불렀다` 는 없다.
5. born 이 비었다 → 첫 호출은 가짜 1번 · 반환에 `한 번 더 부르라`(snapshot). 같은 인자로 두 번째 호출 → 기다린다(가짜가 더 불린다). 인자가 다르면(`{"task_id": "t2"}`) 첫 호출처럼 기다리지 않는다.
6. 늘 running 인 가짜 · `MAX_S = 0.1` → 반환에 `아직 끝나지 않았다` · `이 턴에는 더 기다리지 않는다` · `예전에 저장된 결과`, 턴 상태 `spent_s ≥ 0.1`. 이어서 같은 호출 → 가짜는 1번만 더 불리고 반환에 `이미 다 써`.
7. 다시 조회에서 예외(`RuntimeError("502")`) → 마지막 running 결과 + `다시 조회가 실패했다(RuntimeError`. 다시 조회가 10초 잠드는 가짜 · `MAX_S = 0.2` → 0.5초 안에 끝나고 `다시 조회가 실패했다` 와 `답하지 않았다`.
8. 턴 상태 없음(문맥 변수 기본값) → 기다리지 않고 안내도 없다(심의 · 카탈로그 길). `chat=False` 로 감싼 도구도 같다.
9. `MAX_S = 0` → 기다리지 않고 안내가 없으며, 같은 상태 도구를 네 번째 부르면 종전 꼬리 `4번째 불렀다` 가 붙는다(종전 그대로). 켜져 있을 때 상태를 읽은 상태 도구 다섯 번 → 꼬리 없음, 상태를 못 읽는 결과(SmartTwinMCP 꼴)를 주는 상태 도구 네 번째 → 꼬리 있음.
10. invoke_tool 경유 — `invoke_tool.ainvoke({"name": "get_task", "arguments": {"task_id": "t1"}})`(born `{"t1"}`) → 기다리고, 다시 조회는 invoke_tool 의 원래 코루틴을 같은 인자로 부른다. `arguments` 가 JSON 문자열이어도 같다.
11. 유령 ID 게이트가 먼저다 — 출처 없는 정수 `registry_id=98765` 로 부른 상태 도구는 가짜가 0번 불리고 게이트 문구만 돌아온다.
12. 다시 조회는 게이트를 다시 지나지 않고 `_hwax_rc` 가 가짜 인자로 새지 않는다 — 가짜가 받은 인자 사전에 `_hwax_rc` 가 없다.
13. `tool.ainvoke` 를 부모 실행 없이 부르면(사건을 낼 곳이 없다) 오류 없이 기다린다.

실제 턴(`_agent_stream`).

14. 대본 모델 — 1호 `run_checklist(job_id="j1")` · 2호 `get_task(task_id=<1호 결과의 task_id>)` · 3호 답. 가짜 `get_task` 는 running(0.3) · running(0.6) · done. 기대 — 모델 호출 3번, `get_task` 가짜 3번, SSE 에 `"도구 호출: get_task"` 와 `"도구 완료: get_task"` 가 한 번씩이고 그 사이에 `wait.phase` 가 start → (wait …) → end 인 status 가 있으며 그 status 의 `tool` 은 null, `"같은 호출 반복 감지"` 없음, 3호 모델 입력의 마지막 ToolMessage 에 `"status": "done"` 과 `끝난 상태(done)`.
15. 같은 대본에서 첫 wait 프레임을 받은 뒤 턴 태스크를 취소 → `3 × POLL_S` 뒤에도 가짜 호출 수가 늘지 않는다(기다림이 멈췄다).
16. 대본 모델이 `get_task(task_id="t5")` 만 한 번 부르고 답한다(born 없음) → 모델 호출 2번, 가짜 1번, 마지막 ToolMessage 에 `한 번 더 부르라`.
17. `/health` — `status_wait` 에 `on · poll_s · max_s · waits · ended · capped · failed` 가 있고, 4 를 한 번 돌린 뒤 waits · ended 가 1씩 는다(`tests/test_health_contract.py` 의 `client` 고정물).
18. `langchain_core.tools.base._get_runnable_config_param(<챗으로 감싼 도구>.coroutine)` 가 `"_hwax_rc"` 다 — 기본값을 None 으로 바꾸면 붉다(3.10 의 Optional 함정 고정).

변이로 확인할 것(반대 검토 몫) — born 을 안 채움 · 되풀이 규칙 빠짐 · 상한 회계 빠짐 · `tool` 을 null 대신 이름으로 냄 · 꼬리 면제를 이름만으로 함 · 다시 조회 한도 빠짐 · 기본값 None, 각각 위 시험 하나 이상이 붉어야 한다.

## 8. 위험 · 열린 질문(권하는 답)

- **Q1 언제 기다리나.** 모든 상태 조회에 기다리면 상태만 묻는 질문이 10분 붙잡힌다. → 이 턴에 건 잡 · 같은 호출의 되풀이로 좁힌다(4.4). 되풀이 안내(snapshot)가 LLM 에게 기다리는 길을 알려 준다.
- **Q2 상한 600초가 무거운 잡에 맞나.** StepForge 판 전체 drop_check 는 10% 에서 30분(ST-12), DOE 캠페인은 시간 단위다 — 그런 잡은 10분 기다리고 '아직' 을 받는다. → 요청서 예대로 600 으로 두고 박스에서 줄일 수 있게 한다. 진행률로 남은 시간을 어림해 일찍 접지는 않는다(ST-12 — 진행률이 30분 멈춰 어림이 틀린다). ST-12 가 '예상 작업량' 을 실으면 그때 다시 본다.
- **Q3 doe_status 를 기본 목록에 둘까.** AbaqusMCP 는 진행 중 응답에 '이 세션에서 계속 기다리지 말라' 를 싣는다. → 둔다. 요청서 목록이고, 기다림은 상한이 있으며 상한 안내가 '사용자에게 알려라' 로 앱의 뜻과 같은 곳에 닿는다. 운영자가 원치 않으면 cae00 에서 `CHAT_STATUS_WAIT_MAX_S` 로 줄인다.
- **Q4 study_get 은 확인할 수 없다.** → 목록에 두되 꼴을 못 읽으면 기다리지 않는다(종전과 같다). cae00 에서 `/tools-map` 과 응답 한 번을 보고 맞지 않으면 다음 판에서 뺀다(사람 몫, server-setup 에 한 줄).
- **Q5 deliberate_status 를 넣을까.** → 넣지 않는다. 심의는 시간 단위이고 웹 심의는 `/심의` 길이 진행을 따로 흘린다.
- **Q6 게이트웨이에 '상태 도구' 표지를 더할까.** → 지금은 아니다. 앱 쪽 표지 계약이 없고, 이름 목록 + `routine_read` 울타리로 충분하다.
- **Q7 박스 덧붙임 `CHAT_STATUS_TOOLS` 를 둘까.** → 둔다. cae00 에만 있는 상태 도구를 커밋 없이 더한다. 잘못 적은 쓰기 도구를 되풀이해 부르지 않게 게이트웨이가 읽기로 확인한 도구에만 먹는다.
- **Q8 `/health` 칸을 둘까.** → 둔다. HA-34 교훈 — 흔적이 없으면 cae00 재시험이 효과를 가리지 못한다.
- **Q9 진행 줄이 활동 목록에 쌓인다.** → 30초 간격으로 묶어 10분에 20줄 남짓. 한 줄을 갱신해 보이려면 프런트 몫이다(다음에, 지금은 하지 않는다).
- **Q10 사용자가 멈추면 답이 없다.** 잡은 계속 돈다. → 그대로 둔다. 중지는 중지다(C-5). 진행 줄은 화면에 남는다.
- **위험 R1 잘못 알아본 도구를 되풀이해 부른다.** 막는 것 — 정확한 원래 이름 목록 · `routine_read` 울타리 · 결과가 '도는 중' 꼴일 때만 · 다시 조회는 같은 인자.
- **위험 R2 퍼밋 · 연결을 최대 10분 쥔다.** 동시 챗 64 가운데 하나다. 재기동(update-all)은 기다리는 턴을 끊는다 — 종전 챗과 같다(챗은 delib_active 에 세지 않는다).
- **위험 R3 감사 · 사용 보고서의 상태 도구 호출 수가 는다.** 10초에 한 건, 기다림마다 최대 60건이다. 게이트웨이 `audit.jsonl` 과 E-8 보고서의 '불린 수' 를 읽을 때 감안한다.
- **위험 R4 진행률 단위.** 0~1 실수와 0~100 정수를 가르는 규칙(실수 ≤ 1 → 100배)은 화면 표시에만 쓰고 LLM 에는 원문이 간다.
- **위험 R5 엉뚱한 born.** 상태 도구가 아닌 읽기 도구가 맨 위에 도는 잡 하나를 돌려주면(예 `get_job_details`) 같은 턴의 그 잡 상태 조회가 기다린다. 드물고 상한이 있다 — 보이면 born 을 게이트웨이 `routine_read` 밖의 도구 결과로 좁힌다.

## 9. 하지 않는 것

- 잡을 시작하는 쪽에서 코드가 곧바로 기다리지 않는다(어느 상태 도구를 부를지 모른다) — 기다림은 상태 도구 호출 안에서만이다.
- 잡 취소 · 재시도 · 결과 내려받기를 코드가 대신하지 않는다.
- 프런트 · 포털 중계 · 게이트웨이를 바꾸지 않는다.
- 심의 좌석 · 띵킹 · 분석 루틴의 도구 호출에는 걸지 않는다(턴 상태가 없다).
