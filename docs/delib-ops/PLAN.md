# 심의 엔진 운영 — 새 심의 멈춤 · 재기동을 넘기는 대기열 · 끊긴 잡 이어하기 · 재기동 없는 한도 · 섞인 풀의 창 (2026-10-22)

> 요청서 [request.md](request.md)(사양 — R1~R5 · O1 · O2) · 체크리스트 [checklist.md](checklist.md) · 결정 [context-notes.md](context-notes.md) ·
> cae00 절차(사람 몫) [server-setup.md](server-setup.md).
> 대상은 HWAXAgentServer(엔진)와 HWAXPortal `infra/scripts`(운영 스크립트)다. **완료 10-22** — 엔진 `2e5dad6`(R4) · `41a3996`(R5) · `e7df642`(R1~R3) ·
> `1567dba`(R2' start.sh), 포털 `5ea295d`(R2' lib · O1 · O2). 뒤이어 10-22 — 이어하기 요약을 좌석 몫으로 엔진 `8c37ba2`(DO-D15) · 좌석 합 상한
> 엔진 `43234c6`(R4' · DO-D16).

## 1. 무엇 · 왜

10-22 새벽 동시 심의 한도를 2 → 6 으로 올리는 데 반나절이 걸렸다. 한도가 모듈 상수라 재기동이 들고, 재기동은 도는 잡과 줄 선 잡을 모두 닫으며,
그 사이 새 심의를 잠시 멈출 스위치가 없었다. GLM 두 대(창 300K · 1M)를 한 풀로 묶자 엔진이 큰 쪽 창을 집을 수 있었다. 이번에 다섯 가지를
엔진에, 둘을 운영 스크립트에 넣는다.

## 2. 대조로 바뀐 전제(DO-D2)

- **웹 심의는 잡이 아니다.** 포털 심의 화면 · 리스크 앱 패널은 `/agent/chat` 의 `/심의` · `/시뮬심의` · `/시험계획` 트리거로 열리는 **분리 스트림**이다
  (`app._detach_stream`). 잡(`delib_jobs`)은 MCP 두 도구로만 열린다. 그래서 R1 의 멈춤은 MCP 두 도구와 웹 세 트리거를 함께 막는다.
- **엔진은 체크포인트를 내지 않는다.** 잡의 `checkpoint` 칸은 있지만 엔진이 `checkpoint` 사건을 한 번도 내지 않아 늘 비어 있다. R3 은 원장의
  좌석 발언(라운드 번호가 실린 전사)과 R2 의 시작 인자 파일로 이어 간다.
- **MCP 잡에는 원래 호출자 토큰이 없다.** 두 도구 모두 `user_pat` 를 넘기지 않고 신원 헤더(이메일 · 그룹)로 게이트웨이에 붙는다. 시작 인자
  파일에 적을 토큰이 애초에 없다. 그룹은 줄에 설 때의 값으로 돈다 — 지금 메모리 줄도 같다.

## 3. 바꾸는 것

| # | 무엇 | 어디 |
|---|---|---|
| R4 | 동시 한도 셋(`MAX_RUNNING` · `MAX_RUNNING_PER_USER` · `QUEUE_MAX`)을 판정 때마다 읽는다 — 박스 파일(`<잡 원장>/state/limits.json`)이 env 위에 덮인다. `GET · POST /limits`(루프백, `/drain` 과 같은 신뢰), 올리면 줄을 곧바로 띄운다. 내리면 도는 잡은 그대로 · 새 시작만 준다. `/health` 에 지금 값과 출처(DO-D3) | 엔진 `delib_jobs` · `app` |
| R4' | **좌석 합 상한**(사용자 요청 10-22 — '심의와 리스크 심사는 쓰는 에이전트 수가 다르다') — 위 셋은 잡 수를 세 3석도 20석도 1건이다. 네 번째 한도 `max_seats_running`(`DELIB_JOB_MAX_SEATS_RUNNING` · `/limits` · 기본 0 = 끔)이 도는 GLM 잡의 좌석 합을 묶는다. 앉기 전은 어림, 앉으면 고치고 줄을 다시 본다 · 혼자면 넘어도 돈다 · 먼저 선 잡의 좌석을 가로채지 않는다 · 외부 응답자 잡 · 웹 심의(리스크 패널은 앱이 2개씩)는 합에 넣지 않는다(DO-D16) | 엔진 `delib_jobs` · `app` · `mcp_server` |
| R5 | `LLM_CONTEXT_TOKENS` 를 서버 답의 **상한**으로도 쓴다(`min(서버, env)`, 출처는 env). 창을 굳히지 않고 `LLM_CONTEXT_TTL_S`(기본 600초)마다 뒤에서 다시 묻는다(묻는 동안 호출자는 기다리지 않는다). 한 번 물을 때 `LLM_CONTEXT_SAMPLES`(3)번 물어 가장 작은 값. **다시 물은 답은 줄일 때만 받는다** — 넓히기는 재기동 때(DO-D4) · `/health.context` | 엔진 `app._model_context_tokens` |
| R1 | **새 심의 멈춤** — 비우기 깃발과 같은 규칙(수명 상한 · 주인 · 고정 · 원자적 쓰기)의 **따로 된 파일**(`<잡 원장>/state/delib-pause.json` · `scope: delib`). 켜져 있으면 MCP `deliberate_start` · `deliberate_continue` 가 「점검 중 — 약 N분 뒤 다시」(retry_after_s)로 거절하고, 웹 세 트리거도 SSE `error`(`delib_paused`)로 거절한다(앱이 띄운 리스크 패널은 앱이 비우기 깃발로 스스로 멈춘다 — 엔진이 거절하면 패널이 오류로 닫힌다). **줄 선 잡도 띄우지 않는다**(잡아 두고 재기동). 도는 잡은 끝까지 간다. 끄면 그 자리에서, 수명으로 풀리면 15초 주기 펌프가 줄을 띄운다. `POST /drain {scope:"delib"}` · `/health` 의 `delib_paused` · `delib_pause`(`GET /drain` 은 그대로 — DO-D5) | 엔진 `review_gate` · `delib_jobs` · `app` · `mcp_server` |
| R2 | **줄이 재기동을 넘긴다** — 잡마다 시작 인자 전부를 `<잡 원장>/args/<id>.json`(0600)에 적고(토큰 없음), 재기동 뒤 줄 선 잡을 처음 줄 선 차례(`queued_at`)로 다시 세운다(멈춤이 켜져 있으면 그대로 붙잡는다). 정상 종료(TERM)로 접힌 도는 잡은 `interrupted` 로 남는다. `/health` 의 `delib_queue_durable` · `delib_requeued`(DO-D6 · DO-D7) | 엔진 `delib_jobs` · `mcp_server` |
| R3 | **끊긴 잡 이어하기** — 재기동으로 끊긴 잡에 끝난 라운드 수를 남기고(`resume`), `deliberate_continue(previous_job_id=<끊긴 잡>)` 한 번으로(사람 의견은 선택 인자가 됐다) 끝난 라운드의 좌석별 마지막 입장을 요약으로 싣고 **남은 라운드만**(하한 2) 돈다. 시작 인자 파일이 있으면 처음의 근거 · 지정 좌석 · 손잡이를 그대로 쓴다. 한 잡은 한 번만 잇는다(DO-D8~D10) | 엔진 `delib_jobs` · `mcp_server` |
| R2' | 재기동 판정이 줄 선 수를 막는 수로 세지 않는다 — 떠 있는 서버가 줄을 파일로 넘기는 판(`delib_queue_durable` 이 정확히 `true`)일 때만(DO-D11) | 엔진 `start.sh` · 포털 `lib/delib-busy.sh` |
| O1 | 에이전트 서버를 다시 띄울 일이 있고 심의가 돌면, 새 심의 멈춤을 세우고 `HWAX_DELIB_WAIT_S`(기본 600초)까지 도는 심의가 끝나기를 기다린 뒤 재기동한다(못 기다리면 종전대로 미루고 멈춤은 그 자리에서 내린다). 재기동 판정이 있는 `update-sites.sh` 의 에이전트 갈래에 둔다 — update-all 아래면 재기동한 멈춤을 update-all 끝에서 내린다(표지 파일로 넘긴다 — DO-D12) | 포털 `update-sites.sh` · `update-all.sh` · `lib/delib-busy.sh` |
| O2 | 에이전트 서버가 이번에 다시 떴으면(리스너 pid · 시작 시각) 재기동 뒤 다시 선 줄의 수를 찍는다(`/health` 의 `delib_requeued` — DO-D13) | 포털 `update-all.sh` |

## 4. 하지 않는 것

- 박스 `update-collab.sh`(이 리포에 없다 — cae00 운영 스크립트). 같은 함수를 쓰게 하는 것은 박스 몫이다.
- 2절의 박스 설정 걷기(운영 쪽 — 엔진을 올린 뒤 사람이).
- 끊긴 잡의 **자동** 이어하기(요청서의 '또는 자동으로') — 이어하면 새 잡 id 가 생겨 원래 잡을 보던 호출자가 모르는 잡이 돈다. 사람이 한 번 부른다.
- 엔진 상태 그대로의 재개(라운드 중간의 근거 풀 · 좌석 채택 기록까지) — 원장에 없다. 끝난 라운드의 입장으로 이어 간다(DO-D10).
- 웹 심의(포털 화면 · 리스크 패널)의 재기동 넘기기 · 이어하기 — 잡이 아니라 분리 스트림이다(DO-D2 ①). O1 이 재기동 전에 끝나기를 기다린다.
- 사람이 멈춤을 세우는 셸 도구(`review-drain.sh` 같은 것) — 손잡이는 루프백 `curl` 한 줄이다(server-setup.md). 필요하면 그때 만든다.

## 5. 확인

엔진 시험(한도 · 창 · 멈춤 · 줄 넘기기 · 이어하기 · `/drain` · `/health` · 웹 트리거) · 엔진 전체 시험 · 포털 계약 시험(엔진을 읽는 것) ·
포털 셸 시험(`delib-busy` · update-all 블록) · 변이. 끝난 리포부터 올린다.

**한 것(10-22)** — 엔진 시험 `test_delib_limits` 13 · `test_ctx_reask` 14 · `test_delib_ops` 23 · start.sh 가드 36, 엔진 전체 2,554 통과 · 변이 R4 1 ·
R5 9 · R1~R3 · R2' 28 잡힘(빈틈 넷을 메운 뒤). 포털 `test_delib_pause_ops` 35 · 포털 전체 3,239 통과(빠진 둘은 이 작업 전부터 있던 환경 탓 —
EC-D6) · 변이 17 잡힘(빈틈 셋을 메운 뒤 — 그 하나는 명령 치환 안에서 bash 가 `set -e` 를 물려주지 않아 시험이 위험을 못 보던 것).
