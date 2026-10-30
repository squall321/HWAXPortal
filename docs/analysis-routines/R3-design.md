# 분석 루틴 R3 — 챗(Qwen) 길 설계(10-30)

계획 [PLAN.md](PLAN.md) · 계약 [contracts.md](contracts.md) · 판단 [context-notes.md](context-notes.md). 이 문서가 R3 구현의 **정본 계약**이다 — 게이트웨이 ·
포털(백엔드 · 화면) · 에이전트 서버가 이 꼴을 그대로 짓는다. 근거는 코드 지도 여섯(10-30, 읽기만 — 에이전트 턴 · 떼어 낸 작업 · 선례 · 포털 중계 ·
화면 · R2 계약 실물)이다. R4 의 핵심(인사이트 · 보고서 제출)도 여기서 함께 짓는다 — 실행기가 끝까지 가야 R3 을 시험할 수 있다.

## 0. 한 줄

챗에서 루틴을 골라 보내면 **에이전트 서버의 실행기(`routine.py`)가 코드로 단계를 돈다** — 단계마다 그 단계 허용 도구만 묶은 작은 ReAct 가 조회하고(호출은 전부
게이트웨이 `routine_call` 로), 도구 없는 따로 턴이 단계 봉투를 쓰고, 포털이 원장과 맞대 상태를 고친다. 끝나면 인사이트를 쓰고 `routine_report_submit` 으로
보고서 · RA 초안까지. 브라우저가 떠나도 돈다.

## 1. 결정(R3-D1 ~ D12)

| # | 결정 | 까닭 |
|---|---|---|
| D1 | **챗 실행도 에이전트가 게이트웨이 `routine_run_start` 로 만든다**(contracts §5 의 '중계가 만든다' 를 뒤집는다). 대화와 잇기는 새 인자 `conversation_id` | 두 실행자(Qwen · Claude)가 같은 도구 · 같은 계약을 탄다(AR-D3). 중계는 얇게 둔다. 중계가 만들면 `start_run` 이 이벤트 루프에서 sqlite · 게이트웨이 왕복을 하고, 실패 까닭이 화면에서 'Request failed' 로 뭉개진다 |
| D2 | 에이전트는 루틴 도구를 **MCP 원 세션**(JSON-RPC 를 httpx 로 — 포털 `GatewaySession` 과 같은 꼴)으로 부른다 | 일반 로더(`_get_tools_retry`)는 `_agent_denied` 로 루틴 도구를 거른다(R2, 일반 챗 거부 — 그대로 둔다). 어댑터는 `isError` 를 예외로 바꾸고 머리 JSON 과 본문을 `""` 로 붙인다 |
| D3 | 단계 도구 = 그 사람의 도구 목록에서 **허용 목록 `{백엔드: [원래 이름]}` 만** 골라, 겉(이름 · 설명 · 인자 스키마)은 그대로 · 속은 `routine_call(run_id, step, "백엔드:원래 이름", 인자)`. 안내대 도구(`search_tools` · `invoke_tool` …) 없음. 호출은 **실행마다 하나씩**(잠금) | 울타리 · 원장이 Claude 길과 같다. 병렬 호출은 예산 검사(부르기 전)와 원장 쓰기(부른 뒤) 사이에서 예산을 넘기거나 `call_id` 가 겹친다 |
| D4 | 단계 봉투는 **도구 없는 따로 턴**(JSON · 생각 끔)이 쓴다. 상태는 코드가 먼저 정하고 포털이 원장과 맞대 고친다 | 도구 왕복 뒤의 모델은 JSON 계약을 깬다(`deliberation._free_gather_one` 의 교훈). 호출 없이 '했다' 는 포털이 skipped 로 고친다(R2) |
| D5 | 심의 단계 — `deliberate_start` 는 `routine_call`(근거는 게이트웨이가 앞 단계 원문으로, `save_report` 는 게이트웨이가 false 로), 진행은 `deliberate_status` 를 **직접**(원장 · 예산을 안 쓴다), 결과는 `routine_call(deliberate_result)` — **시간 상한 뒤에도 결과 읽기는 된다** | 상태를 `routine_call` 로 물으면 줄마다 원장 한 줄 · 예산 하나를 쓴다(기본 8). 심의는 분 ~ 시간이라 시간 상한에 걸려 결정문을 못 받으면 이미 쓴 GLM 시간이 루틴에서 사라진다. 루틴 보고서가 RA 초안을 따로 쓰므로 심의의 RA 초안은 겹친다 |
| D6 | **쓰기 도구 분류의 정본은 게이트웨이 `_tool_is_write`**(readOnlyHint · destructiveHint → 이름 낱말). `/tools-map` 이 `write` 목록을 싣고 포털 계획이 그것을 뺀다(도구를 적은 단계도). 게이트웨이 `routine_call` 도 막는다 — 심의 단계의 `deliberate_start` 만 예외 | R2 의 `is_write_tool`(절차 목록 + 차단 접두)은 dev 에서 `create_document` · `update_block` · `run_operation` · `recipe_run` · `save_result_to_path` · `set_job_sync` 를 읽기로 통과시켰다 — 도구를 비운 단계에 쓰기 도구가 묶여 Qwen 이 잡을 낼 수 있었다(AR-D5 위반). 저장 때 검사는 그대로 둔다(옛 게이트웨이 대비) |
| D7 | **떼어 낸 작업** — 에이전트 레지스트리 `_RUNS{run_id}`(구독자 여럿 · 다시 붙기), 브라우저가 떠나도 돈다. 동시 상한 `ROUTINE_MAX_RUNNING`(기본 2, 넘으면 거절 — v1 은 줄 없음). `/health` `routine_active` 를 따로 싣고 `delib_active` 에도 더한다. 카드 검토 반감(`_delib_human`)에는 안 센다. 심의 멈춤(`/drain scope=delib`) 중엔 새 시작 · 이어서를 거절 | `delib_active` 에 더하면 update-all · start.sh · deploy-all 의 기다림 다섯 곳이 고침 없이 루틴을 기다린다(AR-D8). 루틴은 챗 LLM(Qwen)이라 GLM 을 보호하는 카드 검토 반감과 무관하다. 멈춤을 안 지키면 `hwax_delib_wait` 가 수렴하지 않는다 |
| D8 | **이어서** — 같은 프로세스에 살아 있으면 다시 붙고(지금까지 낸 프레임 다시 보내기 + 이어지는 프레임), 없으면 `routine_run_start(run_id=…)` → 포털 `POST /runs/{id}/resume`(running · interrupted → running, 시간 상한에 닿았으면 마감을 '지금 + minutes') 뒤 끝난 단계를 건너뛰고 잇는다. `interrupted` 는 v1 에서 아무도 찍지 않는다 — 재기동 뒤 running 으로 남은 실행은 사람이 '이어서' · '멈춤' 을 누른다 | 사람 PAT 는 재기동 때 사라진다(저절로 다시 돌지 않는다 — AR-D8). 재기동 순간에 원장에 쓰는 것은 2초 유예 안에서 믿을 수 없다. 다시 붙기가 없으면 두 탭이 같은 실행을 두 번 돈다 |
| D9 | **중계** — 루틴 턴은 긴 idle(심의와 같은 값), 브라우저가 떠나도 상류를 끝까지 읽어 대화에 남긴다. 어시스턴트 meta 에 `routine = {run_id, routine_id, title, state}` 포인터만(정본은 포털 원장). `from_chat.record` 는 건너뛴다 | 루틴 호출은 `routine_calls` 원장에 이미 있다 — 절차 원장(`runs`)에 또 넣으면 두 벌이다(R2 에서 원장을 나눈 까닭). 화면은 run_id 로 포털에서 단계를 다시 읽는다 |
| D10 | 대화 종류는 `chat` 그대로 — `kind=routine` 을 만들지 않는다 | 새 종류는 세 곳(포털 `ConvCreate` · 화면 `ConvKind` · 게이트웨이 `save_conversation` enum)을 함께 고쳐야 하고, 빠지면 사이드바 필터(`m.kind === serverKind`)가 대화를 숨긴다. 루틴 턴은 메시지 meta 로 보인다 |
| D11 | 보고서 — 단계 절은 봉투(요약 · 발견 · 인용)에서 **코드가** 짓고 인사이트 절만 LLM 이 쓴다(`[call_id]` 인용 필수). 출처 없는 수치(`evidence.unsourced_numbers`)가 있으면 한 번 고쳐 쓰게 한다. 보고서 글은 `token`, 단계 글은 '생각' 칸(`reasoning`) | AR-D7. 자기검증의 '못 고치면 초안을 낸다' 규칙을 따른다 — 검사 실패가 보고서를 죽이지 않는다 |
| D12 | RA `ask` 다시 올리기 — 포털이 보고서를 낼 때 RA 블록을 저장하고, 끝난 실행의 `POST /report` 는 저장본을 돌려준다(올리기만 다시) | R2 결함: `ra_next` 가 `upload=true` 로 다시 내라고 하지만 실행이 `done` 이라 늘 409 였다(게이트웨이 시험은 포털을 가짜로 세워 못 봤다) |

## 2. 흐름

```
화면(루틴 칩 · 입력) ──POST /agent/chat {message, routine:{id, version?, inputs} | {run_id}}──▶ 포털 중계
  중계: feat:routines · 챗 PAT 있어야 · payload.routine · 긴 idle · 브라우저가 떠나도 끝까지 읽음 · meta.routine
       ──▶ 에이전트 /chat: routine 가지 — 맨 앞(심의 · 띵킹 · 슬래시보다 먼저), _pinged_stream 으로 감싸지 않는다
           run_routine: (다시 붙기) · 멈춤 확인 · 동시 상한 · _RUNS 에 작업 → 구독
           _drive: 원 세션(사람 PAT) → routine_run_start(새 · 이어서) → routine{plan}
             단계마다: routine_get(run_id)로 다시 읽기(풀린 할 일 · 앞 단계 키) → 막힘 · 상한 · 상태 확인
               platform/cite: 묶음(허용 목록 → routine_call) → 작은 ReAct(예산 · 초) → 봉투 턴(JSON) → routine_step_done
               deliberation: routine_call(start) → deliberate_status 직접(진행 프레임) → routine_call(result) → 봉투 턴 → routine_step_done
               waiting → routine{gate} · 끝 / failed · cancelled → routine{done} · 끝
             다 닫히면: 인사이트 턴 → (출처 없는 수치면 한 번 고침) → routine_report_submit → token(보고서) · routine{report} · result · routine{done} · done
```

## 3. 계약

### 3.1 요청 칸 `routine`(포털 `ChatRequest` · 에이전트 `ChatRequest`)

```json
{"id": "<루틴 id>", "version": 3, "inputs": {"model": "S26"}}      // 새 실행
{"run_id": "<실행 id>"}                                             // 이어서 · 다시 붙기
```

- 포털 모델 `RoutineReq` — `extra=forbid`. `id` ≤ 64 · `version` ≥ 1 또는 없음 · `inputs` 객체(키 24개 · 값은 문자열 · 수 · 참거짓 · 객체 · 목록, 직렬화 20,000자 이하) ·
  `run_id` ≤ 64. **`id` 와 `run_id` 중 하나는 있어야 한다**(둘 다 비면 422). 형 맞추기는 포털 `/routines-api` 가 실행을 만들 때 한다(`_coerce`).
- 에이전트 모델은 `routine: dict | None = None`(심의 `delib_opts` 처럼 원 사전 — 실행기가 검사한다). **두 곳에 다 선언한다** — 하나라도 빠지면 조용히 버려진다
  (포털 시험이 에이전트 `ChatRequest` 를 AST 로 읽어 본다).
- `message` 는 그대로 필수다(1자 이상). 화면은 사람이 쓴 글이 없으면 `루틴: <제목>` 을 보낸다. 실행기는 이 글을 '사용자가 덧붙인 말' 로 단계 · 인사이트 프롬프트에 싣는다.
- `conversation_id` 는 지금처럼 따로 온다 — 실행기가 `routine_run_start(conversation_id=…)` 로 넘긴다.

### 3.2 SSE `routine` 이벤트

`event: routine` 한 종류, `data.kind` 로 가른다. **모든 프레임에 `run_id`**(실행 id 를 아직 모를 때 — 시작 실패 — 는 `routine` 을 안 내고 `error` 만 낸다).

| kind | 칸 | 언제 |
|---|---|---|
| `plan` | `run_id, routine_id, version_no, title, purpose, state, resumed(bool), steps[{id, title, kind, state, backends, label}], report{title, sections, upload}` | 실행을 만들었거나 이었거나 다시 붙었을 때(다시 붙기는 지금 원장의 모양) |
| `step` | `run_id, step, title, state:"running", detail?` | 단계 시작 · 심의 진행(`detail`: '라운드 2/3 · 좌석 발언' 같은 한 줄) |
| `step_done` | `run_id, step, state, reason, summary(600자까지), flags[], calls` | `routine_step_done` 뒤 — `state` 는 **포털이 고친 값** |
| `gate` | `run_id, step, candidates[{label, key}], message` | 실행이 `waiting`(고를 것) — 이 프레임 뒤 스트림이 끝난다 |
| `report` | `run_id, ra_upload, ra_report_id?, ra_error?, ra_next?, coverage{counts, not_ok}, warnings[]` | 보고서를 낸 뒤 |
| `done` | `run_id, state, reason?` | 스트림의 마지막 `routine` 프레임 — `done` · `waiting` · `failed` · `cancelled` · `running`(실행기 오류로 멈춤 — 이어서 가능) |

- 단계 안 도구 호출은 지금의 `status` 프레임 꼴 그대로(시작 · 끝, `call` 로 짝) + 칸 둘: `routine_step`(단계 id) · `routine_call`(원장 `call_id`, 끝 프레임에만).
  `tool` 은 노출 이름, `via` 는 백엔드 키. 중계의 활동(activity) 저장이 그대로 받는다.
- 단계 글(작은 ReAct 의 AI 글 · 봉투 요약)은 `reasoning{delta}` — 단계마다 머리 줄 `\n\n### 〔<step id>〕 <제목>\n` 을 먼저.
- 보고서 본문은 `token{delta}`(400자 조각) → `result{type:"text", content}` → `done{}`. 보고서에 못 간 끝(고를 것 · 실패 · 멈춤 · 오류)도 짧은 안내 글을
  `token` · `result` 로 낸다 — 중계는 답 글이 비면 대화에 남기지 않는다.
- 오류 — `error{code, message, retryable?, retry_after_s?}` 뒤 `done{}`. code: `routine_bad_request` · `routine_no_pat` · `routine_busy`(retryable, retry_after_s 60) ·
  `delib_paused`(심의 멈춤과 같은 꼴) · `routine_gateway`(게이트웨이 · 포털이 거절 — `ROUTINE_ERROR:` 뒤 글을 그대로) · `routine_internal`.

### 3.3 대화 meta

중계가 어시스턴트 메시지 meta 에 `routine` 을 남긴다: `{run_id, routine_id, title, state}`(그 턴의 `routine` 프레임에서 — 마지막 값이 이긴다). 단계 · 보고서는
남기지 않는다 — 화면이 `GET /routines-api/runs/{run_id}` · `GET /routines-api/runs/{run_id}/report` 로 읽는다(주인만). 활동(`activity`)은 지금처럼 남는다.

### 3.4 게이트웨이(HWAXMcpGateway) — 바뀌는 것

1. `routine_run_start` — 인자 둘 추가: `conversation_id`(≤ 64, 포털 `RunIn.conversation_id` 로) · `run_id`(주면 이어서 — `POST /runs/{run_id}/resume`, 나머지 인자는 안 본다).
2. `routine_call`
   - **쓰기 도구 거절**: 풀린 `(백엔드, 원래 이름)` 이 `_tool_is_write` 면 `ROUTINE_ERROR: 단계 안에서는 쓰지 않는다(v1) — '<bk>:<orig>' 는 쓰기 도구로 분류된다(readOnlyHint · 이름 꼴). 읽기 도구만 부른다`.
     예외는 `hwax-deliberation:deliberate_start`(심의 단계 — 계획의 `kind == "deliberation"` 일 때만).
   - `deliberate_start` 에 `save_report` 가 없으면 `false` 를 넣는다(근거 채움과 같은 자리).
   - 시간 상한 예외: 실행 보기의 `run.limit_kind == "time"` 이고 도구가 `hwax-deliberation:deliberate_result` 면 상한 거절을 건너뛴다(호출 상한은 그대로).
3. `_routine_portal` — 5xx 는 `포털 오류(HTTP <n>) — 잠시 뒤 다시`(글 몸이 JSON 이 아니어도). '포털이 낡았다' 는 404 + 비 JSON(또는 detail `Not Found`)일 때만.
4. `/tools-map` — 칸 `write` 추가: 노출 이름 목록(정렬), `_tool_is_write(도구, 원래 이름)` 가 참인 것. 다른 칸은 그대로.
5. 도구 설명 — `routine_call`: 심의 단계의 순서(start 는 routine_call · 진행은 deliberate_status 를 직접 · 결과는 routine_call — 시간 상한 뒤에도 된다)와 쓰기 거절.
   `routine_run_start`: `conversation_id` · `run_id`(이어서).
6. **MCP prompts**(R2 남은 일) — `prompts/list` 는 부른 사람(사람 PAT)이 볼 수 있는 루틴 하나에 하나 `routine-<루틴 id>`(title = 루틴 제목, arguments = 루틴 변수 — 필수 표시),
   GW_TOKEN · 익명 · 포털 실패는 빈 목록. `prompts/get` 은 그 루틴을 돌리는 지시문(routine_get → routine_run_start(inputs) → 단계마다 routine_call → routine_step_done →
   routine_report_submit, 울타리 · 인용 · 키 규칙)에 받은 인자를 inputs 로 박아 돌려준다. capabilities 에 prompts 가 실리는지 본다.
7. `_INSTRUCTIONS` 12번 — 분석 루틴 한 항목(위 순서 · 울타리 밖 도구 금지 · 결과에 나온 값만 키로).

### 3.5 포털 `/routines-api` — 바뀌는 것(R2 결함 고침 포함)

1. `POST /runs/{id}/resume`(주인, PAT 또는 세션 + CSRF) — `running` · `interrupted` → `running`. 시간 상한에 닿았으면 `deadline = 지금 + limits.minutes*60`.
   `waiting` 은 409 `고를 것이 있다 — 고른 뒤 이어서`, `done` · `failed` · `cancelled` 는 409 `실행이 <state> 다`. 돌려주는 것은 `run_view`.
2. `run_view` — 단계마다 `findings`(봉투의 발견, 없으면 `[]`) · 실행에 `limit_kind`(`"time"` · `"calls"` · `null`) · 할 일의 `{{run.started}}` 를 실행 시작 시각(KST `YYYY-MM-DD HH:MM`)으로.
3. `GET /runs/{id}/report`(주인) — `{run_id, state, report_ready, report_md, ra_upload, ra_report_id, ra_error}`(보고서가 없으면 `report_ready:false` · `report_md:""`).
4. `POST /runs/{id}/report` — 실행이 `done` 이고 저장한 보고서가 있으면 **다시 렌더하지 않고 저장본**(`report_md` · `ra` 블록 · 커버리지 · 경고)을 돌려준다(게이트웨이의 `ask` 다시 올리기).
   RA 블록은 렌더할 때 실행 행의 새 칸(`report_json`, 없으면 붙이는 이주)에 저장한다.
5. 보고서 렌더는 **실행이 묶인 판**(`version_id`)의 스펙을 읽는다 — `_readable`(공개 범위 · 보관)을 다시 타지 않는다(주인이 도중에 보관 · 비공개로 바꿔도 이 실행의 보고서는 난다).
6. `add_call` — 개수 세기와 넣기를 한 쓰기 트랜잭션(`BEGIN IMMEDIATE`)으로. 시간 상한 예외(D5)를 같은 규칙으로.
7. **쓰기 분류(D6)** — `_catalog` 가 `/tools-map` 의 `write` 를 읽어 도구마다 `write`(참 · 거짓 · 모름)를 단다. `plan_steps` — 도구를 적은 단계: 적은 것 ∩ 내 목록 ∩ 쓰기 아님,
   뺀 것은 준비도 까닭에 적는다. 도구를 비운 단계: 내 목록 − `is_write_tool` − 게이트웨이 쓰기. 게이트웨이가 `write` 를 안 주면(옛 판) `is_write_tool` 만 —
   계획에 `write_class: "gateway" | "name"` 을 단다. `/platforms` 의 읽기 표지도 같은 판정.
8. 읽기 전용 PAT(scopes 가 read 만)는 실행 쓰기 길(`POST /runs` · `/resume` · `/calls` · `/steps/*/done` · `/pick` · `/report` · `/ra` · `/cancel`)에서 403 —
   게이트웨이를 거치지 않고 포털로 바로 와도 원장에 못 쓴다.

## 4. 에이전트 서버 `routine.py`(새 파일) · `app.py` 고리

- 맨 첫 줄 한국어 머리 주석. `app` 은 함수 안에서 늦게 import(순환 — `thinking.py` 선례).
- 손잡이(env): `ROUTINE_MAX_RUNNING`(2) · `ROUTINE_LLM`(`chat` | `glm`, 기본 chat) · `ROUTINE_DELIB_POLL_S`(20) · `ROUTINE_RESULT_CHARS`(도구 결과를 LLM 에 보이는 상한, 기본
  `_free_result_chars` 꼴로 창에서) · `ROUTINE_HISTORY_FRAMES`(다시 붙기용 기록, 400).
- **원 세션** `_GwSession(user_pat, groups, user)` — initialize → notifications/initialized → tools/call → DELETE. 머리: Bearer 사람 PAT · `X-HWAX-Groups`(비면 뺀다) ·
  `X-HWAX-User`. 끊기 · 503 draining · 세션 만료는 한 번 다시 연다. 결과는 마지막 `data:` 줄의 `result{content, isError}`. 첫 블록이 `ROUTINE_ERROR:` 로 시작하면 거절(원장 없음).
  `routine_call` 은 첫 블록을 `json.JSONDecoder().raw_decode` 로 머리 JSON 으로 읽고 나머지가 본문이다.
- `run_routine(app, req)` — 비동기 생성기(SSE 바이트):
  1. 검사 — `routine` 꼴(`id` 또는 `run_id`) · `user_pat` 비면 `routine_no_pat` · 심의 멈춤이면 `delib_paused`(그 꼴 그대로).
  2. 다시 붙기 — `run_id` 가 `_RUNS` 에 살아 있으면 기록 프레임을 다시 보내고 이어지는 프레임을 구독한다(새 작업 없음).
  3. 동시 상한 — 살아 있는 실행이 `ROUTINE_MAX_RUNNING` 이상이면 `routine_busy`.
  4. `_Live(run_id 미정)` 를 만들고 `asyncio.create_task(_drive(...))` — 레지스트리에 강한 참조. 구독자가 끊겨도(취소) 작업은 돈다.
- `_drive` — 작업 안에서 ContextVar 를 세운다: 챗 LLM 창(`_think_llm` 꼴 — `ROUTINE_LLM=chat` 이고 `chat_llm_cfg` 가 있으면 `ctx_override = win − min(out, win//2)`) ·
  `_chat_affinity`(대화 id) · `_turn_ids`(입력 · 넘긴 키의 정수로 씨앗 — 유령 ID 막이) · 호출 추적 `tag(kind="routine", job=run_id)`.
  1. 새 실행 `routine_run_start(routine_id, version, inputs, conversation_id)` 또는 이어서(`routine_get(run_id)` → 상태가 `running` · `interrupted` 면 `routine_run_start(run_id=…)`,
     `waiting` 이면 고를 것을 다시 `gate` 로, `done` 이면 `GET` 할 길이 없으니 '이미 끝났다 — 화면에서 보고서를 연다' 안내, `failed` · `cancelled` 는 그 상태로 끝).
  2. 사람의 도구 목록 — `_get_tools_retry(_with_groups(연결, groups, user, user_pat))`(**서비스 계정으로 떨어지지 않는다** — 401 이면 실패를 낸다) + `/tools-map`(`app._tools_map()`).
     `(백엔드, 원래 이름) → 노출 도구` 표: 노출 이름 → 백엔드는 tools-map, 원래 이름은 포털과 같은 규칙(`bk.replace("-","")+"_"` 접두면 떼고 아니면 그대로).
  3. 단계 차례대로 — 매번 `routine_get(run_id)` 로 다시 읽는다. 실행이 `running` 이 아니면 멈춘다. 닫힌 단계는 건너뛴다. `run.limit_reached` 면 남은 열린 단계를
     `skipped`(까닭 '실행 상한 — <limit>')로 닫고 보고서로 간다.
  4. **platform · cite 단계**
     - 묶음: 허용 목록의 각 도구를 노출 도구에서 찾아 같은 이름 · 설명 · `args_schema` 의 새 `StructuredTool` 로 — 속은 `routine_call(run_id, step, "bk:orig", 인자)`.
       목록에 없는 허용 도구는 빼고 단계 글에 적는다. 결과 쪽이 여럿이면(`pages`) 도구 `routine_page(call_id, page)` 를 함께 묶는다(속은 `routine_get(run_id, call_id, page)`).
     - 도구가 LLM 에 돌려주는 글: `[근거 <call_id>] ` + 본문(상한 `ROUTINE_RESULT_CHARS`, 잘리면 그렇게 적음) + 쪽 안내. 거절(`ROUTINE_ERROR`)은 그 글 그대로 — 예산을 다 썼다는
       거절이면 모델이 멈추게 '더 부르지 말고 정리하라' 를 붙인다.
     - 실행마다 잠금 하나 — 병렬 tool_calls 도 한 번에 하나씩 나간다. 호출마다 `status` 시작 · 끝 프레임(3.2).
     - 프롬프트(시스템): 단계 역할 · 할 일(풀린 goal) · 루틴 목적 · 사용자가 덧붙인 말 · 앞 단계(`uses`)의 요약 · 키 · 발견(인용 id 포함) · 기대 키(`expect.keys`) ·
       예산(호출 · 초) · 규칙(이 도구만 · 값은 결과에서만 · 근거 id 를 [ ] 로 · 모르면 모른다 · 충분하면 그만 부른다 · 한국어).
     - 작은 ReAct: `create_react_agent(llm, 단계 도구)` → `astream(stream_mode="values", recursion_limit=calls*2+5)` — 부분 결과가 살게. 시간 상자 `budget.seconds`(작은
       ReAct 작업을 취소하고 지금까지의 메시지를 쓴다 — Python 3.10 이라 `asyncio.timeout` 없음). 새 AI 글은 `reasoning` 으로.
     - 봉투 턴(도구 없음 · 생각 끔 · 출력 상한 4,096): 입력은 할 일 · 기대 키 · 이 단계 호출들(call_id · 도구 · 인자 요약 · 결과 발췌 — 창 몫 안에서) · AI 메모.
       출력 JSON `{status, reason, summary, keys, findings[{text, refs}], candidates}`. 검사(`_persona_round` 꼴, 한 번 다시): status 는 8 상태 중 · refs 는 이 단계 call_id 만 ·
       키 값은 이 단계 결과 어딘가에 글자 그대로 있어야(없으면 빼고 까닭에 적는다) · 상한(요약 6,000 · 발견 20 · 글 500 · 키 16 · 후보 20)에 맞춰 자른다.
       못 쓰면 코드 봉투: 성공 호출이 있으면 `ok`, 호출이 다 실패면 `failed`, 호출 0 이면 `skipped`, 요약은 AI 메모.
     - 작은 ReAct 가 터지거나 시간이 다 되면 그때까지의 호출로 봉투 턴을 돈다(까닭에 '시간 예산' · 예외 한 줄).
  5. **deliberation 단계**
     - `routine_call(step, "hwax-deliberation:deliberate_start", {question, job, advanced?})` — `question` = 루틴 목적 + 풀린 할 일 + 사용자가 덧붙인 말, `job` = 계획
       `deliberation.job`(없으면 `mechanism`), `chair_template` 이 있으면 `advanced={"chair_template": …}`. `evidence` · `save_report` 는 넣지 않는다(게이트웨이가 채운다).
     - 결과 본문 JSON 에서 `job_id`. 없으면 봉투 `failed`.
     - `deliberate_status(job_id)` 를 원 세션으로 **직접**(routine_call 아님) `ROUTINE_DELIB_POLL_S` 마다 — `routine{step, detail}` 로 라운드 · 단계 한 줄. 끝(`done` · `error` ·
       `cancelled` · `interrupted`)까지, 또는 실행이 멈춤 · 취소될 때까지(사이사이 `routine_get(run_id)` 로 실행 상태를 본다).
     - `routine_call(step, "hwax-deliberation:deliberate_result", {job_id})`(쪽이 여럿이면 `routine_page` 로 이어 붙인다) → 봉투 턴(결정문 요약 · 발견은 결과 call_id 인용).
       심의가 `done` 이 아니면 `failed`(까닭: 심의 상태 · job_id — 서버에서 계속 돌 수 있다).
  6. 봉투를 `routine_step_done` 으로 → 고친 상태로 `step_done` 프레임. `run_state` 가 `waiting` 이면 `gate` 프레임 · 안내 글 · `done(waiting)` 으로 끝, `failed` · `cancelled` 면
     안내 글 · `done(<state>)` 으로 끝.
  7. **인사이트 · 보고서** — `routine_get(run_id)` 로 단계 요약 · 발견 · 상태를 읽고:
     - 단계 절(코드): `요약` + `- 발견 [ref …]` 줄. 막힌 단계는 절을 비워 둔다(포털이 커버리지로 말한다).
     - 인사이트 턴(LLM, 생각은 챗 기본): 목적 · 사용자가 덧붙인 말 · 단계마다 요약과 발견(인용 id) · 막힌 단계 → 마크다운. 규칙: 주장마다 `[call_id]` · 수치는 근거에서만 ·
       빈 곳을 숨기지 않는다.
     - `evidence.unsourced_numbers(인사이트, 근거 글)` 이 무엇을 찾으면 그 목록을 주고 한 번 고쳐 쓰게(인용을 달거나 뺀다). 고친 글이 더 나쁘거나 실패하면 첫 글.
     - `routine_report_submit(run_id, sections={<step>: 절, "insight": 인사이트})` → `report_md` 를 `token` 400자 조각으로 · `routine{report}` · `result` · `routine{done}` · `done`.
  8. 예외 — 어디서든 터지면 `error{code:"routine_internal"|"routine_gateway"}` · 안내 글 · `routine{done, state:"running"}`(이어서 가능) · `done`. 원장은 포털에 남는다.
- `app.py` 고리
  - `ChatRequest.routine: dict | None = None`.
  - `_denied_feature` — `routine` 이 있으면 `feat:routines` 를 본다(`entitlements` 가 `None` 이면 지금처럼 막지 않는다). `_FEATURE_LABEL` 에 '분석 루틴'.
  - `chat()` — `_denied_feature` · 추적 tag 바로 뒤, 심의 멈춤 · 슬래시 · 띵킹보다 **먼저** `req.routine` 가지. `_pinged_stream` 으로 감싸지 않는다(브라우저가 떠나도 돈다).
  - `/health` — `routine_active`(살아 있는 실행 수) · `routine_max`. `_delib_load()` 의 active 에 `routine_active` 를 더한다(`_delib_human` 은 그대로).
  - 수명 — 끝날 때 살아 있는 루틴 작업을 취소한다(원장은 running 으로 남는다 — 이어서).
- 시험 — 가짜 게이트웨이(원 세션 JSON-RPC 꼴 그대로: 머리 + 본문 · `ROUTINE_ERROR` · isError) · 가짜 챗 모델(`_ScriptLLM` 꼴, tool_calls · 글 · JSON):
  단계 도구 ⊆ 허용 목록(묶인 이름 집합을 단언) · 안내대 도구 없음 · 호출은 모두 `routine_call` 로 · 병렬 tool_calls 도 하나씩 · 호출 없이 '했다' → 봉투는 보내되 포털이 고친
  상태가 프레임에 · 키는 결과에 있는 값만 · 예산 거절 뒤 멈춤 · 시간 상자 · 심의 단계(start → status 직접 → result) · gate 로 끝 · 다시 붙기(두 번째 구독이 기록을 받고 작업은
  하나) · 동시 상한 · 사람 PAT 없으면 거절 · 서비스 계정으로 안 떨어짐 · 멈춤 중 거절 · `/health` 셈 · SSE 꼴(포털 `_parse_sse_frame` 이 읽는 꼴).

## 5. 포털 중계(`app/agent/routes.py`)

- `ChatRequest.routine: RoutineReq | None`(3.1). 있으면 `ensure(principal, "feat:routines")`(403) — `check_chat` 바로 뒤, 동시 상한 세마포어 **앞**.
- `_relay_stream` payload 에 `routine`(`model_dump(exclude_none)`). 챗 PAT 가 비면(발급 실패) 에이전트를 부르지 않고 SSE `error{code:"routine_no_pat"}` · `done`.
- idle — 루틴 턴은 심의 가지(긴 idle). ReadTimeout 문구도 심의 쪽('서버에서 계속 돌 수 있다').
- **브라우저가 떠나도 상류를 끝까지 읽는다**(루틴 턴만): `gen` 의 finally 가 pump 를 취소하지 않고, pump 작업을 모듈 집합에 강하게 쥐고, 소비자가 없으면 브라우저 큐에
  더 넣지 않는다(64MB 대기에 걸려 멈추지 않게). 끝나면 지금처럼 저장 · 허가 반납.
- 저장 — `routine` 프레임을 읽어 `meta.routine = {run_id, routine_id, title, state}`(3.3). 루틴 턴은 `from_chat.record` 를 건너뛴다.
- 시험 — payload 에 routine · 에이전트 `ChatRequest` 에 그 칸(AST) · feat:routines 403 · PAT 없으면 오류 프레임 · 긴 idle · 브라우저가 떠난 뒤에도 끝까지 읽어 meta.routine 저장 ·
  from_chat 건너뜀 · 루틴 아닌 턴은 지금 그대로(끊으면 취소).

## 6. 화면(`frontend/src`)

- `api/routines.api.ts` — `getRun(runId)` · `getRunReport(runId)` · `pickCandidate(runId, step, key)` · `cancelRun(runId)` · 형(`RunView`, `RunStep`).
- `types/chat.ts` — `RoutineEvent{kind; run_id; …}` · `Message.routine?: RoutineState`(`{run_id, routine_id?, title, state, steps[{id, title, kind, state, summary?, reason?, flags?}],
  gate?{step, candidates}, report?{ra_report_id?, ra_error?, ra_next?}, resumed?}`).
- `components/chat/routine.ts`(.ts — 노드 시험이 읽는다) — `mergeRoutine(prev, event)` · `routineFromRunView(view)` · 상태 라벨 · 사슬 글(R1 `RoutinesView` 의 `READY_LABEL` ·
  `chain()` 을 여기로 옮겨 함께 쓴다).
- `api/chat.api.ts` — `StreamHandlers.onRoutine` · `dispatch` 에 `case 'routine'` · `streamChat` 옵션 `routine`(본문 맨 위 칸 — **`delib_opts` 에 넣지 않는다**).
- `state/ChatContext.tsx` — 켜 둔 루틴 `armedRoutine` + ref(띵킹 토글 꼴) · `sendMessage` 가 켜 둔 루틴을 실어 보내고 끈다(한 번 쓰기) · `resumeRoutine(runId)` ·
  `onRoutine` → `patch(... mergeRoutine)`. 다시 보내기(`retryLast`)는 루틴 턴이면 이어서(`run_id`)로.
- `Composer` — `showRoutine` 속성(챗 페이지에서만) + `can('feat:routines')` 이면 도구 줄에 `RoutineToggle`(알약). 누르면 `RoutinePicker`(Modal): 내 루틴 목록 → 하나 고르면
  판 · 변수 칸(절차 화면의 변수 입력 꼴 — enum 은 select, json 은 textarea, '예시 넣기' 는 칸을 채우지 않는다) · 준비도(단계마다 표지, 게이트웨이가 없으면 '모름') → '켜기'.
  켜 둔 루틴은 알약 글이 루틴 제목 · ×. 사람 글이 비면 `루틴: <제목>` 을 보낸다.
- `RoutineView`(메시지 안, 보고서 글 위) — 머리(제목 · 실행 상태) · 단계 칩 줄(상태 색 · 호출 수) · 펼치면 단계 요약 · 까닭 · 표지 · 고를 것(후보 버튼 → `pickCandidate` 뒤
  `resumeRoutine`) · 버튼 '이어서'(실행이 running 인데 이 화면이 흐르고 있지 않을 때) · '멈춤'(`cancelRun`). 흐르지 않는 메시지는 `getRun` 으로 채우고(복원 · 다시 열기),
  실행이 끝나지 않았으면 5초마다 다시 읽는다(화면에 보일 때만). 보고서 글은 지금의 글 칸(token).
- 저장 — `chatStore` 저장 꼴에 `routine`(저장 거르개에 `m.routine` 추가) · `serverMessagesToLocal` 이 `meta.routine` 을 되살린다.
- CSS — 접두 `rt-chat-`(또는 `rv-`), 토큰만. 좁은 폭(390px)에서 도구 줄이 넘치지 않게.
- 시험 — 노드 시험(`mergeRoutine` · `routineFromRunView` · dispatch 의 routine), `pnpm build`(CSS 변수 검사) · `pnpm lint`(경고 0) · e2e 경로는 그대로.

## 7. 하지 않는 것 · 미룸

- 줄(queue) — 동시 상한을 넘으면 거절한다(v1). 줄은 쓰임을 본 뒤.
- `interrupted` 자동 표시 — 재기동 때 찍지 않는다(D8). 화면은 '이어서' · '멈춤' 을 준다.
- 심의 단계 외 쓰기 · 작업 제출(AR-D5).
- `kind=routine` 대화 종류(D10).
- 진짜 Claude · 진짜 Qwen 시험 — 가짜 LLM 으로 계약을 본다(10-15 결정 · AR-D10). 실주행은 cae00(R5).

## 8. 구현하며 바뀐 것(10-30 — 구현 · 블랙박스 · 맞대기 · 알려진 결함 고침에서)

설계와 실물이 어긋나면 이 절이 이긴다. 까닭은 [context-notes.md](context-notes.md) C-11.

- **다시 붙기가 멈춤 확인보다 먼저**(§4 의 번호 차례를 §2 흐름 차례로). 다시 붙기는 새 일을 시작하지 않으므로 심의 멈춤 중에도 주인이 도는 실행을 볼 수 있다 —
  update-all 의 기다림은 그대로 수렴한다. 새 시작 · 원장에서 잇기는 멈춤 중 거절이다.
- **다시 붙기는 같은 사람만**(이메일 소문자 비교). 남의 run_id 로는 '실행을 찾을 수 없다' — 새어 나간 실행 id 로 남의 단계 글을 보지 못하게. 다시 붙을 때는 지금 원장으로 지은
  새 plan(`resumed: true`)을 먼저 보내고 기록에서 옛 plan 은 뺀다. 기록에는 상태 프레임의 `detail_full` · `result_full` 을 빼고 넣는다(실행마다 메모리 상한).
- **보고서 절은 인사이트만 실행기가 쓴다** — 단계 절은 포털이 봉투(요약 · 키 · 발견)로 짓는다(Claude 길과 한 곳). 포털은 실행자가 절 글을 주면 그 글에 이미 있는 발견을
  다시 붙이지 않는다(Claude 가 요약에 발견을 섞어 써도 한 번만 보인다). 처음 설계(§4.7 — 단계 절을 실행기가 지음)는 발견을 두 번 찍었다.
- **내 도구 목록이 비면 멈춘다**(running 으로 — 이어서 가능). 처음 구현은 열린 단계를 전부 건너뜀으로 닫고 보고서까지 내 실행이 `done` 으로 끝났다(이어갈 수 없다).
- **멈춤 표지에 포털의 실행 상태 거절도**(`실행이 cancelled 상태다` 같은 원장 쓰기 거절) — 그 뒤 그 단계는 더 부르지 않는다.
- **이어서 — running 으로 남은 단계** — 심의 단계는 원장의 마지막 성공한 `deliberate_start` 의 job_id 를 다시 써서 지켜본다(그 잡이 error · cancelled · interrupted 면 새로).
  플랫폼 단계는 앞 프로세스의 호출을 원장에서 읽어 봉투 턴의 근거와 프롬프트('이미 부른 것')에 싣는다.
- **포털** — 계획 행에 단계 `label` · 준비도(`/readiness`)도 게이트웨이 쓰기 분류를 따른다(고르기 화면이 '됨' 이라 했다가 실행에서 막히지 않게) · 끝난 실행의 저장 보고서
  응답에 `ra_report_id` · `ra_error` · `ra_upload` · `GET /routines` 의 변수에 `required` · 호출 원장 쓰기는 한 쓰기 트랜잭션 안에서 실행 상태 · 단계 닫힘 · 예산 · 상한을 다시
  본다 · 상한 판정은 호출 상한이 시간 상한보다 먼저(둘 다 닿았으면 `calls` — 시간 예외로 결과 읽기가 호출 상한을 넘지 않게) · 읽기 전용 판정은 게이트웨이 `is_read_only` 와
  같은 규칙(read 가 있고 write 가 없으면).
- **게이트웨이** — 저장 보고서에 `ra_report_id` 가 이미 있으면 RA 초안을 다시 만들지 않는다(auto 재시도 · ask 다시 올리기) · 포털이 403(루틴 권한 없음)이면 prompts/list 는
  조용히 빈 목록(info 로그) · 지침 12번은 11번(리스크 길잡이)이 있는 박스에서 10 · 12 · 11 차례로 실린다(2,048자 상한 안 · 기존 시험의 앞부분 고정).
- **중계** — 답 글이 빈 루틴 턴도 run_id 포인터를 남긴다(짧은 안내 글 + meta.routine) · 두 탭이 같은 실행을 끝까지 읽으면 보고서를 한 번만 남긴다((대화, run_id) 잠금 +
  같은 끝 상태 · 같은 글(공백 정규화)의 어시스턴트 메시지가 있으면 건너뜀 — 글이 다른 답(끝난 실행의 RA 초안 올리기 안내)은 남긴다) · 떼어 읽는 루틴 펌프는 동시에 8개까지(넘으면 그 턴은 끊으면 끊긴다 — 에이전트 실행은 따로 돈다) · 떼어 읽는 동안 챗 허가를
  쥔다(연결 풀이 허가 수와 같다).
- **화면** — 실행 보기 폴링은 5초로 시작해 1분 동안 바뀐 것이 없으면 30초로 늦추고(사람이 누르거나 바뀌면 다시 5초), 화면 밖(닫힌 독 · 스크롤 밖 · 숨은 탭)에선 읽지 않는다 ·
  다른 메시지가 흐르는 동안 이어서 · 멈춤 · 고르기 단추를 잠근다(이 실행을 흘리는 메시지의 '멈춤' 은 한 번에 멈춘다 — ■ 는 화면 연결만 끊는다) · 끝난 실행엔 늘 '보고서 보기' ·
  띵킹 · 전문가 고정과 함께 켜면 루틴이 이긴다는 표시 · 루틴 턴은 페르소나 도장을 찍지 않는다 · 심의 넘김(`extraDelibOpts`) 턴에는 켜 둔 루틴을 싣지 않는다.
- **(반대 검토 뒤) 단계 울타리는 '읽기로 확인된 것만'** — 쓰기 분류(D6, 이름 동사 규칙)로는 `risk_job_action`(되돌릴 수 없는 취소) · `single_drop_simulation`(Slurm 잡 제출) ·
  `docforge_convert` 같은 이름이 '쓰기 아님' 으로 묶였다(앱들이 readOnlyHint 를 안 단다). 게이트웨이 `_routine_read` — readOnlyHint false · destructiveHint 면 아니다, readOnlyHint true ·
  읽기 목록(`read_tools.json` ∪ 박스 덧씌우기 `read_tools.local.json`)이면 읽기, 그 밖엔 이름 조각에 읽기 낱말(get · list · search · find · query · describe · lookup · resolve ·
  show · count · status · summary · profile · detail · history · compare · read · view · inspect · neighbors · similar · evidence · revisions · facets · stats · overview · catalog ·
  info · preview · estimate …)이 있고 쓰기 동사가 없을 때만 읽기 — **모르면 읽기가 아니다**. `/tools-map` 의 `routine_read` 를 포털 계획이 따르고(`write_class: gateway_read`)
  `routine_call` 도 같은 판정으로 막는다. 심의 단계의 심의 도구 셋만 예외.
- **심의 단계** — 결정문 읽기(`deliberate_result`)는 단계 호출 예산에서도 빠진다(실행 호출 상한은 그대로). 잠깐의 거절(심의 멈춤 · 줄 가득)은 실패가 아니라 기다렸다 다시 —
  기다리는 동안(멈춤이 풀리길 · 줄 선 심의가 시작되길)은 '쉼'(parked)이라 `delib_active` 에 안 센다(update-all 의 기다림이 수렴하게). 실행을 멈추면 시작한 심의도 접는다
  (`deliberate_cancel`). 이어서는 원장의 마지막 성공한 `deliberate_start` 를 다시 쓴다.
- **사용자가 덧붙인 말은 실행에 남는다**(`note` — 시작 때 한 번). 이어서 · 다시 붙기 · 고른 뒤 잇기에서 프롬프트가 '루틴 이어서: …' 로 바뀌지 않는다.
- **RA `ask` 를 챗에서** — 끝난 실행에 `routine {run_id, upload_ra: true}` 를 보내면 실행기가 `routine_report_submit(upload=true)` 로 올린다(화면의 'RA 초안 올리기').
- **키의 근거** — 그 단계의 **성공한** 호출 결과에 글자 그대로 있고, 그 호출의 인자에는 없는 값만(받은 인자를 되돌려 준 값 · 실패한 호출은 근거가 아니다). 포털 · 실행기가 같은 규칙.
- **고르기는 기다리는 실행에서만**(`/pick` — 멈춘 실행을 되살리지 않는다).
- **(마지막 빈틈 고침)** 게이트웨이 — `deliberate_start` 가 돌았는데 원장 쓰기가 거절되면(그 사이 실행이 멈춤 · 상한) 막 시작한 심의를 접고 그렇게 말한다(고아 심의 없음) ·
  읽기 목록에 이름 규칙이 막던 진짜 읽기 넷(`ai-data-hub:get_record` · `get_record_sections` · `describe_record_schema` — 'record' 가 쓰기 동사 · `heax-hwax_risk:risk_next_step`).
  이 목록은 읽기 전용 PAT 의 허용 목록이기도 하다(FU-D17) — 읽기라서 맞다. 화면 — 덧붙인 말은 선에서 2,000자로(코드 포인트 단위 — 반쪽 이모지가 422 를 부른다) ·
  run_id 를 받기 전에 ■ 로 끊긴 루틴 턴의 '다시 시도' 는 이 대화 · 같은 루틴의 최근 실행을 찾아 이어서로 바꾼다(실행 목록이 `conversation_id` 를 싣는다) · 루틴이 흐르는
  동안 ■ 안내는 '화면 연결만 끊는다 — 멈춤은 루틴 칸에서' 다.
- **(반대 검토 2차, 10-30)** 읽기 낱말에서 동사로도 읽히는 셋(fetch · resolve · trace)을 뺐다 — `fetch_rerank_model`(모델을 내려받아 덮어쓴다) · `resolve_thread`(RA 토론 닫기)가
  읽기로 들었다. 그 낱말로 들던 진짜 읽기는 소스를 보고 읽기 목록에 넣었고, 이 박스에서 못 보는 것(코어 허브 `rootdesigndatahub:object_resolve`)은 cae00 이
  `read_tools.local.json` 에 더한다(server-setup.md). 읽기 목록 파일에 **막는 목록**(`deny`)이 생겼다 — 다른 모든 규칙보다 먼저 본다(이름이 읽기 같아도 박스가 닫는다).
  이름 규칙은 쓰기 동사를 그대로 본다(`status` · `history` · `preview` 같은 읽기 꼬리가 쓰기 동사를 덮지 않는다). 심의 단계의 `deliberate_start` 는 인자를 다듬는다(tools · apps 빼고
  save_report · wiki 거짓 — 엔진이 그 사람의 도구로 미리 부르거나 위키에 쓰지 않게). 멈춤은 그 실행이 시작한 심의도 접는다(실행기가 없어도 — 포털이 사람 이름으로
  `deliberate_cancel`), Claude 는 `routine_run_start(run_id, cancel=true)` 로 멈춘다.

