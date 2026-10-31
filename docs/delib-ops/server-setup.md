# 심의 엔진 운영 — cae00 에서 할 일(사람 몫)

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 요청서 [request.md](request.md).
> 기준 — 엔진 HWAXAgentServer `1567dba` 이상, 포털 HWAXPortal 의 delib-ops 커밋 이상(2026-10-22 대조). 박스 상태는 적지 않는다 — 아래 확인 명령으로 그때 본다.
> 주소 `127.0.0.1:9009` 는 에이전트 서버의 루프백이다(포털은 `/drain` · `/limits` 를 중계하지 않는다). 사내 프록시를 타지 않게 `--noproxy '*'` 를 붙인다.

## 0. 올리기

`./infra/scripts/update-all.sh` 한 번이면 엔진과 포털 스크립트가 함께 온다.

⚠ **첫 실행은 옛 엔진 위에서 돈다.** 그 실행의 §4 는 아직 새 심의 멈춤을 모르는 엔진을 보고 종전대로 한다(심의가 돌면 재기동을 미룬다).
엔진이 새 판으로 한 번 뜬 뒤부터 update-all 이 '멈추고 기다려 재기동' 한다(O1). 심의가 도는 동안 꼭 올려야 하면 비는 때를 기다리거나
`AGENT_RESTART_FORCE=1` 이다(도는 심의는 `interrupted` 로 끊기고, 새 엔진에서 아래 5절로 잇는다 — 옛 엔진이 줄 선 잡은 시작 인자 파일이 없어
'시작하지 못했다' 로 닫힌다).

## 1. 확인

```bash
curl -s --noproxy '*' http://127.0.0.1:9009/health | python3 -c '
import json, sys
h = json.load(sys.stdin)
for k in ("limits", "context", "context_tokens", "delib_paused", "delib_pause", "delib_queue_durable", "delib_requeued"):
    print(k, "=", h.get(k))'
```

- `limits` — 지금 걸린 한도 셋과 출처(`env` · `file`). 깨진 덮개면 `error` 가 있다.
- `context` — 창을 정한 근거(`source` · 마지막 `server` 답 · `samples` · `env_cap` · 넓히지 않은 큰 답 `wider` · `asked_s_ago`).
- `delib_paused` 거짓 · `delib_queue_durable` 참 · `delib_requeued` 는 이번 기동에 다시 세운 줄 수.
  셋 중 하나라도 `None` 이면 아직 옛 엔진이다.

## 2. 섞인 GLM 풀의 창(R5) — 박스 nginx 우회를 걷는다(요청서 2절 2)

**순서가 중요하다 — 상한을 먼저 적고, 그다음에 우회를 걷는다.** 엔진은 풀 안 어느 서버가 답했는지 모르고, 바쁜 작은 서버를 least_conn 이
비켜 가면 몇 번을 물어도 큰 창만 볼 수 있다(DO-D4). 상한이 정본이다.

1. `~/Projects/HWAXAgentServer/.env` 에 `LLM_CONTEXT_TOKENS=300000`(풀 안 **작은** 서버의 창)을 적는다. 이미 있으면 그대로 둔다.
2. 에이전트 서버를 다시 띄운다(다음 update-all · 또는 심의가 없을 때 `./start.sh -d`).
3. 1절 명령으로 본다 — `context_tokens` 300000, `context.env_cap` 300000. `context.source` 는 서버가 1M 을 답했으면 `env`, 300K 서버가
   답했으면 `server` 다(둘 다 맞다).
4. 그다음 `~/stcx-llm/nginx.conf` 18800 블록의 `location = /v1/models` 를 지우고 llm-lb 를 다시 읽힌다. 백업은
   `~/portal-backups/delib20-20261022-054611/` 에 있다.
5. 600초쯤 뒤 다시 본다 — `context.samples` 에 두 서버의 창이 섞여 보여도 `context_tokens` 는 300000 그대로여야 한다. 큰 답은
   `context.wider` 에 적힐 수 있다(넓히지 않았다는 뜻이다 — 정상).

두 서버의 창이 같아지면 상한 줄을 지워도 된다(그때는 서버 답 그대로다). 다시 물은 답은 **줄일 때만** 받는다 — 서버를 더 큰 창으로 바꾸면
에이전트 서버를 재기동해야 넓어진다(`context.wider` 가 그 값을 보인다).

## 3. 동시 한도(R4) — 재기동 없이

박스 `.env` 의 `DELIB_JOB_MAX_RUNNING=6` · `DELIB_JOB_MAX_RUNNING_PER_USER=6`(10-22 에 적은 것)은 **그대로 둔다** — env 층이다. 앞으로 바꿀 때는
덮개를 쓴다.

```bash
# 바꾸기 — 준 칸만 덮는다(null 이면 그 칸의 덮개를 지운다). 올리면 줄이 곧바로 빠지고, 내리면 도는 심의는 그대로 새 시작만 줄을 선다.
curl -s --noproxy '*' -X POST http://127.0.0.1:9009/limits -H 'content-type: application/json' \
  -d '{"max_running": 8, "by": "<이름>", "reason": "<까닭>"}'
# 보기
curl -s --noproxy '*' http://127.0.0.1:9009/limits
# 덮개 지우기(env 값으로 돌아간다)
curl -s --noproxy '*' -X POST http://127.0.0.1:9009/limits -H 'content-type: application/json' -d '{"reset": true, "by": "<이름>"}'
```

범위는 전역 1~1000 · 사용자별 0~1000(0 = 전역을 따른다) · 줄 0~1000 · 좌석 합 0~1000(0 = 끔) 이다. 덮개 파일은 `<DELIB_JOB_DIR>/state/limits.json` 이고 손으로 고쳐도
다음 판정부터 읽는다(깨지면 읽지 않고 env 값으로 돌며 `limits.error` 에 까닭이 뜬다).

**좌석 합 상한(`max_seats_running` — 기본 꺼짐).** 위 셋은 심의 **건수**를 센다 — 3석 심의도 20석 심의도 1건이다. 한 심의는 단계마다 좌석 수만큼
LLM 호출을 한꺼번에 내니, LLM 서버가 받는 수를 묶으려면 좌석 합을 건다. 걸면 좌석이 많은 심의는 건수 한도 안이어도 자리가 나기를 기다린다
(먼저 선 심의부터 · 혼자면 넘어도 돈다). 리스크 쟁점 패널(웹 심의)은 합에 들지 않는다 — 리스크 앱이 `HWAXRISK_CONCURRENCY`(기본 2)개씩 연다.

1. 걸기 전에 바쁜 때의 좌석 합을 며칠 본다 — `curl -s --noproxy '*' http://127.0.0.1:9009/health` 의 `delib_seats_running`.
2. 값은 LLM 용량 측정([../llm-pool/capacity.md](../llm-pool/capacity.md))이 권한 동시 수(서버 둘의 합)에서 카드 대조 관문 몫
   (`CARD_REVIEW_CONCURRENCY`)을 뺀 수를 넘지 않게 잡는다 — 그 측정은 카드 대조 길이로 재므로 심의 호출에는 어림이다. 측정 전이면 1 에서 본
   평소 꼭대기보다 조금 위로 걸어 '그보다 많이 몰릴 때만' 줄을 세운다.

```bash
curl -s --noproxy '*' -X POST http://127.0.0.1:9009/limits -H 'content-type: application/json' \
  -d '{"max_seats_running": <수>, "by": "<이름>", "reason": "<까닭>"}'
# 끄기 — 그 칸의 덮개를 지운다(env 기본 0)
curl -s --noproxy '*' -X POST http://127.0.0.1:9009/limits -H 'content-type: application/json' -d '{"max_seats_running": null, "by": "<이름>"}'
```

## 4. 새 심의 멈춤(R1) — 손으로

```bash
# 세우기(30분) — 새 심의 · 이어하기는 '점검 중 — 약 N분 뒤 다시' 로 거절된다. 줄 선 심의는 붙잡히고, 도는 심의는 끝까지 간다.
curl -s --noproxy '*' -X POST http://127.0.0.1:9009/drain -H 'content-type: application/json' \
  -d '{"on": true, "scope": "delib", "ttl_s": 1800, "by": "<이름>", "reason": "<까닭>"}'
# 보기 — 멈춤 · 도는 수 · 줄 선 수
curl -s --noproxy '*' http://127.0.0.1:9009/health | python3 -c '
import json, sys; h = json.load(sys.stdin); print(h["delib_paused"], h["delib_pause"], h["delib_active"], h["delib_queued"])'
# 내리기 — 세운 이름으로(남이 내리려면 "force": true). 내리면 붙잡아 둔 줄이 그 자리에서 든다.
curl -s --noproxy '*' -X POST http://127.0.0.1:9009/drain -H 'content-type: application/json' \
  -d '{"on": false, "scope": "delib", "by": "<이름>"}'
```

- ⚠ 내리기에서 `"scope": "delib"` 를 빼면 **리스크 검토 비우기 깃발(카드 대조)** 을 내리는 요청이다.
- 사람이 풀 때까지 세우려면 `ttl_s` 대신 `"hold": true` 다. 수명은 6시간이 상한이다(그보다 길게는 hold).
- 리스크 앱이 띄우는 패널은 막지 않는다(막으면 패널이 오류로 닫힌다). 함께 멈추려면 `./infra/scripts/review-drain.sh` 로 비우기 깃발도 세운다.

10-22 새벽의 '잡아 두고 재기동' 은 이제 이렇게 한다 — 멈춤을 세운다 → `delib_active` 가 0 이 되기를 본다 → `./start.sh -d`(줄만 서 있으면 막지
않는다 — 줄은 재기동 뒤 같은 차례로 다시 선다) → 멈춤을 내린다. update-all 은 이것을 저절로 한다(O1 — 도는 심의를 `HWAX_DELIB_WAIT_S`
기본 600초까지 기다리고, 못 기다리면 종전대로 미룬다. 재기동 뒤 '다시 선 줄 N건' 을 찍는다).

> **2026-10-31 덧붙임 — 게이트웨이 · SignalForge 도 같은 기다림 하나를 지난다(사용자 결정 A25 (가)).** 도는 좌석은 게이트웨이로 도구를
> 부른다 — 심의 중에 게이트웨이나 SignalForge(그 `down.sh` 는 MCP 까지 내린다)를 내리면 그 순간의 호출이 실패한다. 그래서 update-all 은
> 셋 가운데 **처음으로 재기동할 것**(§2 의 SignalForge → §4 의 signalforge-mcp · 게이트웨이 · 에이전트 서버 차례) 앞에서 위 멈춤을 세우고
> 한 번 기다린다. 끝나면 멈춤을 세워 둔 채 셋을 다 재기동하고(멈춤은 실행 끝에서 내린다), 600초 안에 못 끝나면 셋 다 미루고 멈춤을 그
> 자리에서 내린다 — 뒤의 재기동은 다시 기다리지 않는다(묻는 순간 비었으면 재기동한다). 미룬 것은 `○ signalforge 재기동 건너뜀` ·
> `○ signalforge-mcp 재기동 건너뜀` · `○ mcp-gateway 재기동 건너뜀` · `○ agent-server 재기동 건너뜀` 으로 남는다(끝 요약에도). 바뀌지
> 않아 재기동하지 않는 실행 · 내려가 있는 서비스는 기다리지 않는다. 강행은 그대로 `AGENT_RESTART_FORCE=1` 이다. 손으로 돌리는
> `update-sites.sh mcp-gateway` · `deploy-all-from-drive.sh signalforge` 는 종전대로 묻지 않는다. AIDataHub · KooRemapper · 자기치유
> (`redeploy-app.sh`)는 그대로다. 멈춤의 수명은 기다림 + 30분이다 — §2 에서 세워지면 실행 끝이나 그 수명 가운데 먼저 오는 때까지 새 심의를
> '점검 중' 으로 받는다. 기다림 하나가 덮는 것은 그 멈춤이 서 있는 동안뿐이라, §2 에서 기다렸는데 §4 까지가 수명보다 길어 멈춤이 풀렸으면
> §4 는 그 사이 시작된 심의를 한 번 더 기다린다(`· …: 앞에서 기다렸지만 update-all 의 새 심의 멈춤이 지금은 서 있지 않다 … 한 번 더 기다린다`
> — O1 과 같다). §2 가 SignalForge 를 미뤘으면 §4 의 signalforge-mcp 도 묻지 않고 함께 미룬다(`○ signalforge-mcp 재기동 건너뜀 — 이 실행이 §2 에서
> SignalForge 재기동을 미뤘다 …`) — 그 사이 심의가 끝났어도 DB 이관(`SF_MIGRATE=1`) · 병합 없이 sf-mcp 만 새 코드로 뜨지 않게 한다.
> **예외 하나 — Drive 에서 SignalForge SIF 가 새로 왔으면(의존성이 바뀐 판) SignalForge 는 기다리지 않고 곧바로 재기동한다**
> (`· signalforge: 받기가 떠 있는 인스턴스 밑의 SIF 를 갈았다 — 도는 심의를 묻지 않고 지금 재기동한다`). 받기가 떠 있는 인스턴스의 이미지를
> 이미 덮어써, 기다리거나 미루면 깨진 이미지 위에서 돈다 — 그때 도는 좌석의 VOC 도구 호출은 끊긴다(심의가 없을 때 돌리면 피한다).

## 5. 끊긴 심의 이어하기(R3)

재기동으로 끊긴 MCP 심의는 진행 조회(`deliberate_status`)의 `resume` 에 끝난 라운드 수와 이어 돌 라운드 수가 있다. `deliberate_continue(previous_job_id=<그 잡>)`
한 번이면 남은 라운드만 돈다 — 사람 의견은 비워도 되고, 처음 근거 · 지정 좌석 · 사람 의견 · 손잡이를 그대로 쓴다. 한 잡은 한 번만 잇는다.
웹 심의(포털 화면 · 리스크 패널)는 잡이 아니라 잇지 못한다 — 그래서 O1 이 재기동 전에 끝나기를 기다린다.

## 6. 박스 스크립트 `update-collab.sh`

이 리포에 없다(박스 몫). 같은 일을 하려면 `~/Projects/HWAXPortal/infra/scripts/lib/delib-busy.sh` 를 읽어 다음 순서로 부른다.

```bash
. ~/Projects/HWAXPortal/infra/scripts/lib/delib-busy.sh
_o="$(hwax_delib_pause on http://127.0.0.1:9009/health update-collab 2400 "update-collab 재기동")"; _rc=$?   # 3 = 멈춤을 모르는 엔진 — 보내지 않았다
[ "$_rc" = 0 ] && hwax_delib_wait http://127.0.0.1:9009/health 600       # 0 = 도는 심의가 끝났다 · 1 = 시간이 다 됐다
# … 재기동 …
hwax_delib_pause off http://127.0.0.1:9009/health update-collab
```

## 7. 걷을 것(요청서 2절)

1. `.env` 의 `DELIB_JOB_MAX_RUNNING=6` · `DELIB_JOB_MAX_RUNNING_PER_USER=6` — 그대로 둔다(3절).
2. nginx `/v1/models` 블록 — 2절 순서대로(상한을 먼저).
3. 감시 스크립트 `~/agent-restart-when-idle.sh` — 이미 끝났다. 다시 쓸 일이 없다(4절이 그 일을 한다).
