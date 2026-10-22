# 심의 엔진 운영 요청 — 새 심의 잠시 멈춤 · 재기동에도 남는 대기열 · 재기동 없는 동시 한도 · 섞인 GLM 풀의 창 (2026-10-22)

> 요청서 사본(2026-10-22 사용자가 붙여 넣은 것). 요청자 메일 주소는 이름만 남겼다(이 리포는 GitHub 에 있다). 대조 결과와 정정은
> [context-notes.md](context-notes.md) DO-D2.

요청일 2026-10-22 · 요청자 koo.park(HWAX Portal 운영) · 대상 **HWAXAgentServer**(곁가지 HWAXPortal `infra/scripts`)

기준 — HWAXAgentServer `9d4c931`(cae00 에서 도는 판). origin/main `e436d15` 은 9커밋 앞서지만 이 문서의 자리(`delib_jobs.py` · `mcp_server.py` ·
`app.py` 창 조회)는 바꾸지 않는다(10-22 대조). 아래 `파일:줄` 은 `9d4c931` 기준이다.

**한 줄** — 10-22 새벽에 동시 심의 한도를 2 → 6 으로 올리는데 반나절이 걸렸다. 한도가 모듈 상수라 **재기동이 들고**, 재기동은 **도는 잡과 줄 선 잡을
모두 닫으며**, 그 사이 새 심의를 **잠시 멈출 스위치가 없어** 사람이 손으로 비는 때를 기다렸다. 그리고 GLM 두 대(창 300K · 1M)를 한 풀로 묶자 엔진이
**큰 쪽 창을 집어** 작은 서버로 간 큰 호출이 400 이 될 수 있었다(박스 설정으로 막아 두었다). 아래 다섯 가지를 엔진에 청한다.

---

## 0. 10-22 에 실제로 겪은 일

| 시각 | 일 |
|---|---|
| 05:42 | 한도 6건으로 바꾸려 했으나 심의 2건 진행 · 5건 대기. 재기동하면 7건이 모두 '중단됨' 이 되어 미뤘다 |
| 05:46 | 박스 `.env` 에 `DELIB_JOB_MAX_RUNNING=6` · `DELIB_JOB_MAX_RUNNING_PER_USER=6` 을 적고, '심의 0건이 2분 이어지면 에이전트만 재기동' 하는 감시 스크립트를 박스에 띄웠다 |
| 06:35~07:01 | 한 묶음의 심의 4건이 끝나자 줄 선 2건이 곧바로 빈자리에 들어가 돌기 시작했다 — 운영자가 '잡아 두고 재기동' 하려던 때를 놓쳤다 |
| 07:19 | 남은 2건이 결정문까지 끝나고 나서야 재기동했다. 끊긴 잡은 없었다 — 운이 좋았다 |

같은 날 확인한 엔진의 사실:

| 자리 | 사실 |
|---|---|
| `delib_jobs.py:60` · `:68-69` · `:76` | `MAX_RUNNING` · `MAX_RUNNING_PER_USER` · `QUEUE_MAX` 는 import 때 env 를 한 번 읽는 모듈 상수다 — 바꾸려면 재기동이다 |
| `delib_jobs.py:807` `reap_orphans` | 재기동 뒤 파일에 running · queued 로 남은 잡을 `interrupted` 로 닫는다. 줄 선 잡은 「띄울 때 쓸 인자(호출자 토큰 · 근거 본문 · 좌석)는 메모리에만 있었으니 다시 줄을 세울 수가 없다」(같은 함수 docstring) |
| `delib_jobs.py:600` `start` ← `mcp_server.py:420` `deliberate_start` · `:546` `deliberate_continue` | 심의 잡은 이 두 MCP 도구로만 시작된다(포털 챗의 심의도 같다) |
| `app.py:5750~` `POST /drain` · `review_gate.py:266` `DrainState` | 비우기 깃발은 카드 대조(`card_review.py:2760`) · 외부 응답자 호출(`:3149-3159`)만 막는다. `delib_jobs.py` 에는 drain 을 보는 줄이 없다 — 새 심의 시작은 막지 못한다 |
| `deliberate_start` 인자(`mcp_server.py:420-436`) vs 잡 파일 칸 | 인자는 question · job · rounds · modifiers · evidence · personas · tools · apps · human_note · search_sources · options · stop_after_round · save_report · advanced 다. 파일에는 question · kind · label · chair_template · opts · seats · seat_roles 등만 남는다 — 근거(evidence) · 좌석 지정(personas) · human_note 가 없어 파일만으로 같은 심의를 다시 낼 수 없다 |
| `app.py:2884` `_CTX_FALLBACK` · `:2944-2985` `_model_context_tokens` | 창은 `VLLM_BASE_URL/models` 의 첫 답(`max_model_len`)으로 굳힌다(`:2985` `_ctx_cache["n"] = n`). `LLM_CONTEXT_TOKENS` 는 '물어보기 실패 때' 값일 뿐이라 서버 답을 누를 수 없다 |

---

## 1. 요청 — 다섯 가지

| # | 무엇 | 왜 | 고칠 자리(제안) |
|---|---|---|---|
| R1 | **새 심의 잠시 멈춤 스위치** — `deliberate_start` · `deliberate_continue` 가 새 잡을 만들지 않고 「점검 중 — N분 뒤 다시」 를 `retry_after` 와 함께 돌려준다. 도는 잡은 끝까지 간다. `/health` 에 상태가 보인다 | 재기동 전에 새 잡이 들어와 빈자리를 채우는 것을 막는다(0절 06:35~07:01). 지금은 사람이 '아무도 안 거는 때' 를 기다릴 수밖에 없다 | 기존 `/drain` 의 scope 에 심의를 더하는 꼴이 자연스럽다(예 `scope: delib` 또는 `all` 이 심의까지). 깃발은 이미 파일이고 재기동을 넘긴다(`review_gate.py:266` 규칙). 검사 자리는 `delib_jobs.start`(`:600`) 첫머리 |
| R2 | **줄 선 잡이 재기동을 넘긴다** — 줄에 설 때 시작 인자 전부를 잡 옆 파일(0600)에 적고, 재기동 뒤 `reap_orphans` 가 queued 를 닫지 않고 같은 순서로 다시 세운다 | 지금은 재기동 한 번에 줄이 사라지고 호출자가 다시 걸어야 한다. R1 과 함께면 '잡아 두고 재기동 → 그대로 들어감' 이 된다 | `delib_jobs.py` 의 enqueue 자리(`:711` 근처 queued 레코드) · `reap_orphans`(`:807`). ⚠ 호출자 토큰은 파일에 적지 않는다 — 신원(이메일 · 소속)만 적고 다시 세울 때 게이트웨이 위임으로 새로 받는다 |
| R3 | **도는 잡의 이어하기** — 재기동으로 끊긴 잡에 체크포인트가 있으면 `deliberate_continue` 한 번으로(또는 자동으로) 끊긴 라운드부터 다시 돈다 | 결정문 직전에 끊기면 몇십 분이 사라진다. 잡에 `checkpoint` 칸은 이미 있다(`delib_jobs.py:525-526` · `:883-884`) | `reap_orphans` 가 interrupted 로 닫을 때 체크포인트 유무를 남기고, 이어하기가 그 체크포인트를 받게 |
| R4 | **재기동 없는 동시 한도** — `MAX_RUNNING` · `MAX_RUNNING_PER_USER` · `QUEUE_MAX` 를 시작 판정 때마다 읽는다(박스 파일 또는 루프백 관리 주소 `POST /limits`) | 한도 하나 바꾸는데 재기동이 들고, 재기동이 위 R1~R3 의 문제를 부른다 | `delib_jobs.py:60-76` 을 함수로(읽는 때 env · 파일을 본다). 내리는 쪽은 도는 잡을 끊지 않고 새 시작만 줄인다 |
| R5 | **섞인 GLM 풀의 창** — `LLM_CONTEXT_TOKENS` 를 '상한' 으로도 쓴다(`min(서버 답, env)`), 또는 풀 안 서버들의 창 중 가장 작은 값을 쓴다. 창을 영원히 굳히지 않고 주기로 다시 묻는다 | 10-21 부터 cae00 은 GLM 두 대를 nginx 풀(`least_conn`)로 쓴다. 창이 300K · 1M 로 다르면 첫 답이 1M 일 때 300K 서버로 간 큰 좌석 호출이 400(maximum context length)이다. 10-20 에도 같은 일로 free-gather 2건이 죽었다 | `app.py:2944-2985`. 지금은 박스 nginx 가 `/v1/models` 만 작은 서버로 보내 막고 있다(2절) — 엔진이 고치면 그 설정을 걷는다 |

### 운영 스크립트(HWAXPortal `infra/scripts`) — R1 이 들어온 뒤

| # | 자리 | 할 일 |
|---|---|---|
| O1 | `update-all.sh` · 박스 `update-collab.sh` 의 에이전트 재기동 앞 | 카드 대조 비우기(1h)와 같은 꼴로 R1 스위치를 세우고, 도는 심의가 0 이 되기를 기다린 뒤 재기동하고, 끝에서 내린다. 지금은 심의가 돌면 '재기동 미룸' 으로 넘어가 새 설정이 늦게 반영된다 |
| O2 | 같은 곳 | R2 가 들어오면 재기동 뒤 다시 선 줄의 수를 사후 확인에 찍는다 |

---

## 2. 박스에서 한 것(요청 아님 — 엔진이 고치면 걷는다)

1. `~/Projects/HWAXAgentServer/.env` — `DELIB_JOB_MAX_RUNNING=6` · `DELIB_JOB_MAX_RUNNING_PER_USER=6`(10-22 07:19 재기동으로 반영 · 프로세스 env 확인).
2. `~/stcx-llm/nginx.conf`(llm-lb, apptainer nginx · systemd 사용자 서비스) 18800 블록 — `location = /v1/models` 를 창 300K 서버로만 보낸다. 엔진
   `/health` `context_tokens` = 300000. 두 서버의 창이 같아지거나 R5 가 들어오면 이 블록을 지운다. 백업 `~/portal-backups/delib20-20261022-054611/`.
3. 감시 스크립트 `~/agent-restart-when-idle.sh` — 이번 한 번 쓰고 끝났다(로그 `~/portal-backups/agent-restart-when-idle-20261022-054647.log`).
