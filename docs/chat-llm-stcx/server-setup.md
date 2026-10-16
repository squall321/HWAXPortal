# 챗은 stcx GPU LLM, 심의는 GLM — cae00 절차

> 이 문서는 cae00 에서 챗만 stcx GPU LLM(Qwen3.8-Flash-Next 10벌)으로 돌리는 사람 몫을 적는다. 설계는 [PLAN.md](PLAN.md), 까닭은
> [context-notes.md](context-notes.md)(CL-D1~), stcx 쪽(잡 · 터널 · 부하분산기)은 「stcx GPU LLM 사용 가이드 v1.1」이다.
> 명령은 따로 적지 않으면 포털 리포 루트(cae00 은 `~/Projects/HWAXPortal`)에서 돈다. 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.

## 0. 이 판을 받기만 하면 — 아무것도 바뀌지 않는다

`infra/.env` 에 `CHAT_LLM_BASE_URL` 이 없으면 update-all 3.5 에 ○ 한 줄(`챗 전용 LLM` — `infra/.env 에 CHAT_LLM_BASE_URL 이 없다`)만 남고
챗 · 띵킹 · 심의가 모두 지금처럼 GLM(`LLM_BASE_URL`)을 쓴다. 에이전트 서버 판은 `fd110a6` 이후, 포털은 3.5c 가 든 판이어야 한다.

## 1. 먼저 — stcx LLM 이 떠 있는가

```bash
~/stcx-llm/llmctl.sh status
curl --noproxy '*' -s http://127.0.0.1:18700/v1/models | python3 -c 'import json,sys; print([(m["id"], m.get("max_model_len")) for m in json.load(sys.stdin)["data"]])'
```

기대 — 잡 10개가 돌고 노드별 응답코드가 200, 아래 줄이 `[('qwen3.8-flash-next', 262144)]`. 502 면 열린 벌이 없다(가이드 8장 — 잡이 없으면
`./llmctl.sh start-all`, 기동 중이면 기다린다). 000 이면 부하분산기가 죽었다(`systemctl --user restart llm-lb`).

## 2. 켜기 — `infra/.env` 두 줄

```
CHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1
CHAT_LLM_MODEL=qwen3.8-flash-next
```

- env-sync 가 넣어 둔 주석 줄(`# CHAT_LLM_BASE_URL=`)이 있으면 그 줄의 `#` 을 지우고 값을 적는다.
- `LLM_BASE_URL` · `LLM_MODEL` 은 그대로 둔다 — 띵킹 · 심의 준비 · 심의 · 카드 대조가 그대로 쓰고, stcx 가 죽었을 때 챗이 넘겨 답하는 곳이다.
- 키는 없다(stcx vLLM 은 인증이 없고 이 주소는 루프백이다). 키가 있는 서버로 바꾸면 `CHAT_LLM_API_KEY` 를 더한다.

## 3. update-all

```bash
./infra/scripts/update-all.sh
```

3.5 에서 기대하는 줄.

- `✓ 챗 전용 LLM: http://127.0.0.1:18700/v1 · qwen3.8-flash-next → 에이전트 서버 .env (띵킹 · 심의는 VLLM_BASE_URL)`
- `✓ 챗 서버가 qwen3.8-flash-next 을 낸다(창 262144 토큰)`

에이전트 서버 `.env` 가 바뀌었으므로 같은 실행의 update-sites 가 에이전트 서버를 다시 띄운다. 도는 심의가 있으면 재기동을 미룬다(○ — 끝난 뒤
update-all 을 한 번 더). ⚠ `챗 서버에 닿지 않는다` 는 막는 오류가 아니다 — 적기는 했고, 그동안 챗은 GLM 으로 넘겨 답한다. 1절로 돌아가 본다.

## 4. 확인

```bash
curl -s http://127.0.0.1:9009/health | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["chat_llm"], ensure_ascii=False, indent=1))'
```

- 기대 — `"enabled": true`, `"model": "qwen3.8-flash-next"`, `"thinking": false`, `"fallback": {"enabled": true, "to": "<GLM 모델>", "count": 0, …}`.
  `ctx_tokens` 는 첫 챗 턴 뒤에 `262144` 로 찬다(그 전에는 null).
- 포털에서 챗을 한 번 보낸다. stcx 쪽에서 요청이 들어왔는지 본다 — `tail -3 ~/stcx-llm/nginx/logs/access.log`(요청마다 어느 벌로 갔는지 `up=`).
- 심의는 GLM 그대로인지 — 심의를 하나 돌리고 stcx access.log 에 그 시각의 요청이 늘지 않는지 본다.
- 에이전트 서버 로그(`../HWAXAgentServer/agent-server.log`)의 기동 줄 — `[agent] 챗 전용 LLM — 127.0.0.1:18700 · qwen3.8-flash-next · 생각 끔 · …`.

## 5. stcx 가 죽으면 — 넘김

연결 실패 · 시간 초과 · 5xx 면 그 LLM 호출을 GLM 으로 넘긴다(턴 전체가 아니다). `/health` 의 `chat_llm.fallback.count` 가 늘고
`last_error` 에 사유가 남는다. 에이전트 서버 로그에는 `[agent] 챗 LLM 넘김 — … → <GLM 모델>(VLLM_*) · 지금까지 N회` 가 1분에 한 줄까지 찍힌다.
stcx 를 다시 올리면(`llmctl.sh start-all`) 다음 호출부터 저절로 stcx 로 간다 — 손댈 것이 없다.

- 토큰이 이미 흐르기 시작한 뒤 그 벌이 죽은 답은 넘기지 못한다(가이드 6장) — 사용자가 다시 보낸다.
- 400(요청이 잘못됐다) · 404(모델 이름이 틀렸다)는 넘기지 않는다 — 404 면 3절의 ⚠ `챗 서버에 … 이 없다` 를 본다.

## 6. 손잡이(선택) — 에이전트 서버 `.env` 에 직접

| 키 | 기본 | 언제 |
|---|---|---|
| `CHAT_LLM_DISABLE_STREAMING` | `LLM_DISABLE_STREAMING` 을 따른다(cae00 은 1 — 비스트리밍) | stcx 의 **스트리밍 도구 호출**을 확인한 뒤 `0` 으로 열면 챗 글이 토큰 단위로 흐른다. 확인 — 도구를 부르는 질문(예: '지식 허브에서 낙하 충격 카드 찾아줘')을 보내 도구 상태 줄이 뜨고 답이 오는지 |
| `CHAT_LLM_ENABLE_THINKING` | `0`(생각 끔) | 답이 얕으면 `1`(모델 기본 — 느려진다) |
| `CHAT_LLM_FALLBACK` | `1` | `0` 이면 넘기지 않는다 |
| `CHAT_LLM_MAX_RETRIES` | `1` | 넘기기 전에 stcx 에 다시 보내는 횟수 |

바꾸면 에이전트 서버를 다시 띄운다(`cd ../HWAXAgentServer && ./start.sh -d`, 또는 update-all — `.env` 가 지문이다).

## 7. 되돌리기

`infra/.env` 의 `CHAT_LLM_BASE_URL=` 를 **빈 값**으로 두고 update-all — 3.5 에 `✓ 챗 전용 LLM 을 껐다` 가 찍히고 에이전트 서버가 다시 뜬다.
줄을 지워도 3.5c 가 적었던 값이면 끈다(`✓ infra/.env 에서 CHAT_LLM_BASE_URL 줄이 빠졌다 — …`). 에이전트 서버 `.env` 에 사람이 직접 다른
값을 적었으면 그 값은 건드리지 않는다(○).

## 8. 알아 둘 것

- **품질** — Qwen3.8-Flash-Next 는 전문 영역에서 일반론 수준이고 틀린 서술이 섞인다(가이드 6장). 그래서 심의 · 띵킹은 GLM 에 남겼다(CL-D1).
- **창** — 챗 턴의 문맥 예산은 stcx 창(262,144)으로 잡는다(GLM 1M 이 아니다). 긴 문서 · 긴 대화는 더 줄여 싣는다.
- **이미지** — Qwen3.8 은 이미지를 읽지만 포털 챗은 아직 이미지를 LLM 에 싣지 않는다(docs/chat-vision).
- **stcx 쪽 제약** — 잡 한도 30일(만료되면 `start-all`), cgroup 격리가 없어 같은 노드의 후처리가 메모리를 과용하면 그 벌이 죽는다(가이드 7장).
