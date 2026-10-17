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
python3 - 18700 <<'PY'
import json, os, sys, urllib.request
key = open(os.path.expanduser("~/stcx-llm/api_key")).read().strip()      # 키는 명령줄에 싣지 않는다
op, seen = urllib.request.build_opener(urllib.request.ProxyHandler({})), set()
for _ in range(10):   # 부하분산기(18700)면 여러 벌에 나뉘어 간다 — 창이 섞여 있으면 값이 둘 나온다
    req = urllib.request.Request(f"http://127.0.0.1:{sys.argv[1]}/v1/models", headers={"Authorization": f"Bearer {key}"})
    with op.open(req, timeout=10) as r:
        seen |= {(m["id"], m.get("max_model_len")) for m in json.load(r)["data"]}
print(sorted(seen))
PY
```

기대 — 잡 10개가 돌고 노드별 응답코드가 200, 아래 줄이 `[('qwen3.8-flash-next', 262144)]`(9절로 1M 을 켠 뒤에는 `1010000`). 키 없이
`curl` 로 물으면 401 이다(stcx LLM 은 키가 켜져 있다 — 2절). 502 면 열린 벌이 없다(가이드 8장 — 잡이 없으면 `./llmctl.sh start-all`,
기동 중이면 기다린다). 000 이면 부하분산기가 죽었다(`systemctl --user restart llm-lb`). 끝의 `18700` 을 벌별 포트(18711~18720)로 바꾸면 그
한 벌만 본다(9절 시범).

## 2. 켜기 — `infra/.env` 두 줄

```
CHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1
CHAT_LLM_MODEL=qwen3.8-flash-next
```

- env-sync 가 넣어 둔 주석 줄(`# CHAT_LLM_BASE_URL=`)이 있으면 그 줄의 `#` 을 지우고 값을 적는다.
- `LLM_BASE_URL` · `LLM_MODEL` 은 그대로 둔다 — 띵킹 · 심의 준비 · 심의 · 카드 대조가 그대로 쓰고, stcx 가 죽었을 때 챗이 넘겨 답하는 곳이다.
- **키가 있어야 한다** — stcx LLM 은 키가 없으면 401 이다(10-17 cae00 실측 · 예전 판 이 줄의 '키는 없다' 는 틀렸다). 원본은 `~/stcx-llm/api_key`,
  `infra/.env` 에 `CHAT_LLM_API_KEY=` 한 줄로 넣는다(값은 추적 파일에 적지 않는다). update-all 3.5c 가 매번 에이전트 서버 `.env` 로 옮기므로
  **에이전트 서버 `.env` 만 고치면 다음 update-all 이 옛 키로 되돌린다.** 키가 틀리면 3.5c 가 `⚠ 챗 서버가 키를 거절했다(HTTP 401)` 를
  찍고, 그동안 챗은 GLM 으로 넘겨 답한다(에이전트 서버가 401 · 403 을 넘기는 판부터 — 느리다).
- 키를 바꿀 때 — stcx rolling(약 20분) 동안 옛 키 · 새 키가 섞여 일부 호출이 401 이 된다. 그 호출은 GLM 으로 넘어간다(`/health` 의
  `chat_llm.fallback.count` · `last_error` 로 보인다).

## 3. update-all

```bash
./infra/scripts/update-all.sh
```

3.5 에서 기대하는 줄.

- `✓ 챗 전용 LLM: http://127.0.0.1:18700/v1 · qwen3.8-flash-next → 에이전트 서버 .env (띵킹 · 심의는 VLLM_BASE_URL)`
- `✓ 챗 서버가 qwen3.8-flash-next 을 낸다(창 262144 토큰)` — 9절로 1M 을 켠 뒤에는 `창 1010000 토큰`

에이전트 서버 `.env` 가 바뀌었으므로 같은 실행의 update-sites 가 에이전트 서버를 다시 띄운다. 도는 심의가 있으면 재기동을 미룬다(○ — 끝난 뒤
update-all 을 한 번 더). ⚠ `챗 서버에 닿지 않는다` 는 막는 오류가 아니다 — 적기는 했고, 그동안 챗은 GLM 으로 넘겨 답한다. 1절로 돌아가 본다.

## 4. 확인

```bash
curl -s http://127.0.0.1:9009/health | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["chat_llm"], ensure_ascii=False, indent=1))'
```

- 기대 — `"enabled": true`, `"model": "qwen3.8-flash-next"`, `"thinking": true`, `"effort": "xhigh"`, `"max_tokens": 0`(보내지 않음 — stcx 서버가
  131,072 로 막는다), `"output_reserve": 65536`, `"fallback": {"enabled": true, "to": "<GLM 모델>", "count": 0, …}`(10-18 부터 — 6절).
  `ctx_tokens` 는 첫 챗 턴 뒤에 `262144` 로 찬다(그 전에는 null — 9절로 1M 을 켠 뒤에는 `1010000`, 10분 안에 따라온다).
- 포털에서 챗을 한 번 보낸다. stcx 쪽에서 요청이 들어왔는지 본다 — `tail -3 ~/stcx-llm/nginx/logs/access.log`(요청마다 어느 벌로 갔는지 `up=`).
- 심의는 GLM 그대로인지 — 심의를 하나 돌리고 stcx access.log 에 그 시각의 요청이 늘지 않는지 본다.
- 에이전트 서버 로그(`../HWAXAgentServer/agent-server.log`)의 기동 줄 — `[agent] 챗 전용 LLM — 127.0.0.1:18700 · qwen3.8-flash-next · 생각 켬(xhigh) · 출력 상한 서버 기본(보내지 않음) · 출력 몫 65,536 토큰 · …`.
- 같은 `/health` 의 `tool_cut`(챗 도구 절단 — 뺀 수 · 앱, null 이면 다 붙었다)과 `vision`(서버마다 그림을 받는지 — 첫 그림 턴 전에는 비어 있다).

## 5. stcx 가 죽으면 — 넘김

연결 실패 · 시간 초과 · 5xx 면 그 LLM 호출을 GLM 으로 넘긴다(턴 전체가 아니다). `/health` 의 `chat_llm.fallback.count` 가 늘고
`last_error` 에 사유가 남는다. 에이전트 서버 로그에는 `[agent] 챗 LLM 넘김 — … → <GLM 모델>(VLLM_*) · 지금까지 N회` 가 1분에 한 줄까지 찍힌다.
stcx 를 다시 올리면(`llmctl.sh start-all`) 다음 호출부터 저절로 stcx 로 간다 — 손댈 것이 없다.

- 토큰이 이미 흐르기 시작한 뒤 그 벌이 죽은 답은 넘기지 못한다(가이드 6장) — 사용자가 다시 보낸다.
- **'창이 모자라다' 400 은 넘긴다**(에이전트 서버 `35c048b` 부터 — CL-D9). vLLM 이 `This model's maximum context length is N tokens` 로
  거절한 호출이다. 벌마다 창이 다를 때(9절 시범 · rolling 동안) 난다. `last_error` 가 `ChatCtxOverflow: …` 다.
- 다른 400(요청이 잘못됐다) · 404(모델 이름이 틀렸다)는 넘기지 않는다 — 404 면 3절의 ⚠ `챗 서버에 … 이 없다` 를 본다.

## 6. 손잡이(선택) — 에이전트 서버 `.env` 에 직접

| 키 | 기본 | 언제 |
|---|---|---|
| `CHAT_LLM_DISABLE_STREAMING` | `LLM_DISABLE_STREAMING` 을 따른다(cae00 은 1 — 비스트리밍) | stcx 의 **스트리밍 도구 호출**을 확인한 뒤 `0` 으로 열면 챗 글이 토큰 단위로 흐른다. 확인 — 도구를 부르는 질문(예: '지식 허브에서 낙하 충격 카드 찾아줘')을 보내 도구 상태 줄이 뜨고 답이 오는지 |
| `CHAT_LLM_ENABLE_THINKING` | `1`(생각 켬 — 10-18 사용자 결정, 그 전엔 0) | 답이 너무 느리면 `0`. 끄면 강도 · 출력 몫도 꺼진다 |
| `CHAT_LLM_REASONING_EFFORT` | `xhigh` | 생각을 켰을 때의 강도(`low`·`medium`·`high`·`xhigh`). 빈 값이면 보내지 않는다(모델 기본) |
| `CHAT_LLM_MAX_TOKENS` | `0`(보내지 않음) | stcx 서버가 `--override-generation-config` 로 131,072 에서 막는다(요청서 v1.1 0장). 따로 묶을 때만 |
| `CHAT_LLM_OUTPUT_RESERVE` | 생각 켜면 `65536` | 챗 턴의 창에서 출력 몫으로 비우는 토큰(창 절반까지) — 입력이 창을 다 채우면 생각할 자리가 없다(CD-D4 · CD-D6) |
| `CHAT_LLM_VISION` · `LLM_VISION` | `auto` | 챗 서버 · VLLM_* 가 그림을 받는지. auto 는 그림이 실릴 때 한 번 묻는다(빨간 그림 탐침), `1`·`0` 은 묻지 않는다 |
| `VISION_MAX_IMAGES` · `VISION_MAX_BYTES` | `12` · 8MiB | 한 발화 · 한 장 상한 — 포털 · 화면도 같은 수라 올리려면 세 곳을 같이(`test_chat_images_route`) |
| `VISION_HISTORY_IMAGES` · `VISION_TRANSCRIBE_MAX` | `6` · `8` | 앞 대화의 그림을 다시 싣는 수 · 띵킹 · 심의가 판독하는 수(최근부터) |
| `THINK_LLM` | GLM | `chat` 이면 띵킹 좌석이 챗 전용 LLM(Qwen)으로 돈다(docs/chat-depth-context CD-D8) |
| `CHAT_LLM_FALLBACK` | `1` | `0` 이면 넘기지 않는다 |
| `CHAT_LLM_MAX_RETRIES` | `1` | 넘기기 전에 stcx 에 다시 보내는 횟수 |

바꾸면 에이전트 서버를 다시 띄운다(`cd ../HWAXAgentServer && ./start.sh -d`, 또는 update-all — `.env` 가 지문이다).

## 7. 되돌리기

`infra/.env` 의 `CHAT_LLM_BASE_URL=` 를 **빈 값**으로 두고 update-all — 3.5 에 `✓ 챗 전용 LLM 을 껐다` 가 찍히고 에이전트 서버가 다시 뜬다.
줄을 지워도 3.5c 가 적었던 값이면 끈다(`✓ infra/.env 에서 CHAT_LLM_BASE_URL 줄이 빠졌다 — …`). 에이전트 서버 `.env` 에 사람이 직접 다른
값을 적었으면 그 값은 건드리지 않는다(○).

## 8. 알아 둘 것

- **품질** — Qwen3.8-Flash-Next 는 전문 영역에서 일반론 수준이고 틀린 서술이 섞인다(가이드 6장). 그래서 심의 · 띵킹은 GLM 에 남겼다(CL-D1).
- **창** — 챗 턴의 문맥 예산은 두 서버 창 중 작은 값이다. stcx 가 262,144 인 동안은 그 값이라 긴 문서 · 긴 대화를 더 줄여 싣고,
  도구 설명도 창의 45%(117,964 토큰)까지만 붙는다. 넘치면 질문과의 관련도 순으로 세워 뒤에서 빼고 안내대 셋(`search_tools` · `invoke_tool` ·
  `list_tool_apps`)은 늘 남긴다(10-18 부터 — 그 전엔 게이트웨이 순서 뒤쪽의 앱이 통째로 빠졌다, 수정 제안서 F1). 뺀 수 · 앱은 `/health`
  `tool_cut` · 에이전트 서버 로그 `— 뺀 것:` · update-all 헬스게이트 「챗 도구 절단 N개」. 9절로 1M 을 켜면 GLM 때와 같다.
- **그림** — 10-18 부터 챗이 올린 그림 · 도구 그림 · 앞 대화의 그림을 모델에 싣는다(docs/chat-depth-context T5 · CD-D11). 챗 서버가 그림을
  받는지는 첫 그림 턴에 한 번 묻는다(`/health` `vision`). 띵킹 · 심의는 GLM 이 받으면 그림, 못 받으면 Qwen 이 옮긴 판독문을 근거로 싣는다.
- **stcx 쪽 제약** — 잡 한도 30일(만료되면 `start-all` — 10-17 에 띄운 잡은 **11-15 전후에 끝난다**, 11-14 전에 `~/stcx-llm/llmctl.sh rolling`), cgroup 격리가 없어 같은 노드의 후처리가 메모리를 과용하면 그 벌이 죽는다(가이드 7장).

## 9. Qwen 도 1M 창으로 — stcx 쪽(사람 몫, 사용자 결정 10-18)

Qwen3.8-Flash-Next 의 원래 창은 262,144 토큰이다. YaRN(RoPE 늘이기, factor 4)을 켜면 vLLM 이 262,144 × 4 = 1,048,576 까지 받는다. 띄우는
길이는 Qwen 계열 모델 카드가 검증한 **1,010,000** 으로 한다. 포털 · 에이전트 서버는 고칠 것이 없다 — 에이전트 서버가 10분마다
`/v1/models` 의 `max_model_len` 을 다시 읽어 챗 턴의 창을 두 서버 중 작은 값으로 잡는다(CL-D5). 까닭과 근거는 CL-D9 다.

### 9.1 먼저 — 에이전트 서버 판

```bash
git -C ../HWAXAgentServer merge-base --is-ancestor 35c048b HEAD && echo "판 됨" || echo "update-all 먼저"
```

시범 · rolling 동안에는 부하분산기 뒤에 262,144 벌과 1,010,000 벌이 섞인다. 에이전트가 새 벌에서 1M 을 읽고 만든 긴 요청이 옛 벌로
가면 vLLM 이 '창이 모자라다' 400 을 낸다. 이 판부터는 그 호출을 GLM 으로 넘긴다(5절). 그 전 판이면 그 챗은 실패한다.

### 9.2 덮어쓰기 한 줄 만들기(cae00)

모델의 `config.json` 에서 지금 rope 설정을 읽어 YaRN 세 칸(`rope_type` · `factor` · `original_max_position_embeddings`)만 바꾼 한 줄을 만든다.
나머지 칸(그림 모델의 `mrope_section` 등)은 그대로 싣는다 — 맨 위 칸 덮어쓰기는 묶음을 통째로 바꾸기 때문이다.

```bash
cd ~/stcx-llm
ssh stcx cat /data2/llm/models/Qwen3.8-Flash-Next-FP4-Local/config.json > flash-next.config.json
python3 - flash-next.config.json <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
tc = cfg.get("text_config")
# 그림도 읽는 모델(VLM)은 글 모델 설정이 text_config 아래다 — rope 칸이 거기 있으면 거기, 아니면 맨 위
node, path = ((tc, ["text_config"]) if isinstance(tc, dict) and {"rope_parameters", "rope_scaling", "rope_theta"} & set(tc)
              else (cfg, []))
native = node.get("max_position_embeddings")
rope = dict(node.get("rope_parameters") or node.get("rope_scaling") or {})
for k in ("rope_theta", "partial_rotary_factor"):   # 옛 꼴(칸이 rope 묶음 밖) — 맨 위 덮어쓰기는 묶음을 통째로 바꾸므로 함께 싣는다
    if k not in rope and k in node:
        rope[k] = node[k]
rope.pop("type", None)
print(f"# 지금 — {'.'.join(path) or '(맨 위)'} · max_position_embeddings={native} · rope={json.dumps(rope)}", file=sys.stderr)
if native != 262144 or "rope_theta" not in rope:
    sys.exit("⚠ 원래 창이 262144 가 아니거나 rope_theta 가 없다 — 이 줄은 쓰지 않는다(모델 카드의 YaRN 절을 따른다)")
rope.update(rope_type="yarn", factor=4.0, original_max_position_embeddings=native)
out = {"rope_parameters": rope}
for k in reversed(path):
    out = {k: out}
print(json.dumps(out, separators=(",", ":")))
PY
```

- 기대 — `# 지금 — text_config · max_position_embeddings=262144 · …` 한 줄과 `{"text_config":{"rope_parameters":{…,"rope_type":"yarn",…,
  "factor":4.0,"original_max_position_embeddings":262144}}}` 한 줄. 이 한 줄이 9.3 의 `ROPE_JSON` 이다.
- 모델 카드에 YaRN 절이 있으면 견준다 — `ssh stcx "grep -n -i -A8 yarn /data2/llm/models/Qwen3.8-Flash-Next-FP4-Local/README.md" | head -40`.
  rope 칸 값이 다르면 카드를 따른다. 단 카드의 `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` 은 **옮기지 않는다**(9.3).
- 이 생성기는 dev 에서 vLLM 0.23.0 의 실제 설정 함수로 확인했다 — 덮어쓰기가 `text_config` 에 합쳐지고 1,010,000 이 그 env 없이 통과한다.
  stcx 이미지는 10-15 판 파생이라 다를 수 있다 — 9.4 시범이 가린다.

### 9.3 sbatch 고치기(stcx)

```bash
ssh stcx cp -p /data2/llm/bin/llm_qwen38_flash_next_node.sbatch /data2/llm/bin/llm_qwen38_flash_next_node.sbatch.bak_20261018_262k
```

`/data2/llm/bin/llm_qwen38_flash_next_node.sbatch` 를 연다(`ssh stcx` 뒤 편집기).

- 손잡이 자리(`MAXCG` 옆)에 두 줄을 더한다 — `MAXLEN="${MAXLEN:-1010000}"` 와 `ROPE_JSON='<9.2 의 한 줄>'`(작은따옴표).
- `vllm serve` 줄에 `--max-model-len "$MAXLEN" --hf-overrides "$ROPE_JSON"` 를 더한다. `--max-model-len` 이 이미 있으면 그 값을 바꾼다(둘 두지 않는다).
- `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` 은 **넣지 않는다.** 덮어쓰기가 맞게 들어가면 vLLM 이 1,048,576 까지 스스로 받는다. 덮어쓰기가 틀리면 그
  env 없이는 기동이 `User-specified max_model_len (1010000) is greater than the derived max_model_len (… 262144 …)` 로 바로 멈춘다. env 를
  켜 두면 틀린 채로 떠서 학습한 위치(262,144) 너머를 그대로 쓴다 — vLLM 스스로 'NaN 이 난다' 고 경고하는 길이다.

```bash
ssh stcx "bash -n /data2/llm/bin/llm_qwen38_flash_next_node.sbatch && grep -n -e '--max-model-len' -e '--hf-overrides' -e MAXLEN -e ROPE_JSON /data2/llm/bin/llm_qwen38_flash_next_node.sbatch"
```

### 9.4 시범 한 벌(cae00)

```bash
cd ~/stcx-llm
./llmctl.sh status                                   # 시범 노드와 그 잡 ID 를 고른다(포트 표는 가이드 1장 — 예: icn401-0401-h06 = 18711)
./llmctl.sh stop <그 노드의 잡ID>
./llmctl.sh start flash-next icn401-0401-h06
./llmctl.sh log <새 잡ID> 80                         # 같은 노드면 약 8분
```

로그에서 볼 것.

- `User-specified max_model_len … is greater than the derived max_model_len` 이 있으면 덮어쓰기가 안 먹었다 — 잡이 바로 끝난다. 9.2 · 9.3 을
  다시 본다(그동안 그 노드는 비어 있다 — 급하면 9.7 로 되돌리고 `start`).
- `GPU KV cache size: … tokens` · `Maximum concurrency for 1,010,000 tokens per request: …x` — 1M 대화를 벌마다 몇 개 동시에 담는지다. 가이드의
  262K 때 '벌마다 약 19개'(KV 50.3 GiB)로 셈하면 약 4.9 다. 짧은 요청의 동시 처리는 줄지 않는다(실제 길이만큼만 잡는다).
  1 보다 작으면 기동이 `To serve at least one request with the model's max seq len` 으로 멈춘다.

`./llmctl.sh status` 에서 그 노드의 응답코드가 200 이 되면(터널이 20초마다 보고 그 포트를 연다) 그 벌 하나에만 묻는다.

```bash
python3 - 18711 <<'PY'      # 1절의 창 확인과 같은 것 — 18711 은 시범 노드의 포트
import json, os, sys, urllib.request
key = open(os.path.expanduser("~/stcx-llm/api_key")).read().strip()
req = urllib.request.Request(f"http://127.0.0.1:{sys.argv[1]}/v1/models", headers={"Authorization": f"Bearer {key}"})
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as r:
    print([(m["id"], m.get("max_model_len")) for m in json.load(r)["data"]])
PY
```

기대 `[('qwen3.8-flash-next', 1010000)]`. 다음은 긴 글 시험이다 — 글 한가운데 숨긴 수를 찾는지와 걸린 시간을 잰다(크기를 토큰 수로 적는다).

```bash
python3 - 18711 200000 500000 900000 <<'PY'
import json, os, random, sys, time, urllib.error, urllib.request
port, sizes = sys.argv[1], [int(x) for x in sys.argv[2:]]
key = open(os.path.expanduser("~/stcx-llm/api_key")).read().strip()
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
line = "The sky over the harbor was the color of a television tuned to a dead channel. "   # 약 17토큰
for n in sizes:
    secret, k = str(random.randint(100000, 999999)), n // 17
    text = (f"run {random.random()}\n" + line * (k // 2) + f"The secret number is {secret}. " + line * (k - k // 2)
            + "\nWhat is the secret number in the text above? Answer with the number only.")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"}, data=json.dumps({
        "model": "qwen3.8-flash-next", "max_tokens": 16, "temperature": 0, "messages": [{"role": "user", "content": text}],
        "chat_template_kwargs": {"enable_thinking": False}}).encode())
    t = time.monotonic()
    try:
        with op.open(req, timeout=3600) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"{n:>9,} → HTTP {e.code} {e.read()[:160]!r}")
        continue
    ans = (out["choices"][0]["message"]["content"] or "").strip()
    print(f"{n:>9,} → 입력 {out['usage']['prompt_tokens']:,} 토큰 · {time.monotonic() - t:,.0f}초 · "
          f"{'찾음' if secret in ans else '못 찾음'} ({ans[:30]!r})")
PY
```

- 기대 — 셋 다 `찾음`. 걸린 시간을 CL-D9 에 적는다(1M 에 가까운 첫 요청은 분 단위일 수 있다 — 그동안 그 벌의 다른 요청이 느려진다).
- 견줌 — 같은 명령을 옛 벌의 포트(예: 18712)로 돌리면 500,000 · 900,000 은 `HTTP 400 … maximum context length is 262144` 다. 시범 벌이
  새 설정으로 떴다는 확인이 된다.
- 짧은 글 — 가이드 2장의 `llm_lb_bench.py` 를 `LLM_URL=http://127.0.0.1:18711` 로 시범 벌에만 돌려 가이드 6장의 1벌 수치(동시 8건
  779 · 32건 1,212 tok/s)와 견준다. 평소 묻는 질문 몇 개(예: 가이드 5장의 hourglass 질문)를 시범 벌과 옛 벌에 같은 온도 0 으로 던져 답을
  견준다. 정적 YaRN 은 짧은 글에도 늘인 위치를 쓴다 — Qwen 카드도 '짧은 글 성능에 영향이 있을 수 있다' 고 적는다. 눈에 띄게 나빠지면
  9.7 로 되돌리고 알린다.

### 9.5 rolling(cae00)

```bash
cd ~/stcx-llm && ./llmctl.sh rolling      # 5벌씩 — 시범 노드도 한 번 더 뜬다(빼려면 가이드 2장처럼 노드를 적는다)
```

이 rolling 이 잡 한도(30일)도 새로 잡는다 — 11-14 전에 하면 8절의 '11-14 전 rolling' 을 겸하고, 다음 만료는 rolling 한 날 + 30일이다.

### 9.6 확인

- `./llmctl.sh status` — 10벌 200. 1절의 창 확인(18700, 열 번 묻는다)이 `[('qwen3.8-flash-next', 1010000)]` 하나만 낸다(둘이면 아직 섞여 있다).
- 에이전트 서버 — 10분 안에 `/health` 의 `chat_llm.ctx_tokens` 가 `1010000`(재기동 필요 없음). 다음 update-all 3.5 는 `창 1010000 토큰`.
- 도구 — 챗 턴의 도구 예산이 창의 45%(454,500 토큰)라 게이트웨이 도구가 다 붙는다. 시범 전과 뒤에 한 번씩
  `grep -c "tool budget" ~/Projects/HWAXAgentServer/agent-server.log` 를 적어 두고 챗 몇 번 뒤에 다시 센다 — 늘지 않으면 아무 도구도 잘리지
  않았다(그 줄은 잘릴 때만 찍힌다). 포털 챗에서 MaterialTwin 도구를 부르는 질문을 하나 해 본다.
- 넘김 — 시범 · rolling 동안 `chat_llm.fallback.count` 가 늘고 `last_error` 가 `ChatCtxOverflow: …` 일 수 있다(섞인 동안의 정상 거동). 10벌이 다
  1M 이 된 뒤에는 그 사유로는 더 늘지 않는다.

### 9.7 되돌리기

```bash
ssh stcx cp -p /data2/llm/bin/llm_qwen38_flash_next_node.sbatch.bak_20261018_262k /data2/llm/bin/llm_qwen38_flash_next_node.sbatch
cd ~/stcx-llm && ./llmctl.sh rolling
```

에이전트 서버는 10분 안에 262,144 로 따라온다. 그사이 섞인 동안의 긴 요청은 9.1 의 판이 GLM 으로 넘긴다. 가이드(「stcx GPU LLM 사용 가이드
v1.1」)의 '컨텍스트 262,144' · sbatch 손잡이(`MAXLEN` · `ROPE_JSON`)는 가이드 쪽에서 고친다(v1.2).
