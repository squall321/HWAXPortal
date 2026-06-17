# HWAX MCP Chat — dev stack runbook

How to bring up / verify / tear down the full MCP-chat chain on this box. The stack
is **not persisted** (processes run via `setsid`/background and die on reboot) — this
is the restart guide. Verified working 2026-06-17.

## The chain

```
ChatDock (portal frontend)
  → portal backend       :8723   /agent/chat  — auth · CSRF · concurrency cap · audit · SSE relay
    → Agent Server       :9009   /chat        — LangGraph ReAct, streams §5 SSE  (repo: HWAXAgentServer)
      → vLLM             :8000   /v1          — Qwen2.5-7B-AWQ, tool calling on  (apptainer :latest)
      → MCP demo server  :8011   /mcp         — FastMCP streamable-http: add/multiply/current_time
```

Ports in use elsewhere on this box (do NOT reuse): 9000 MinIO, 9100, 8001 AIDataHub,
4040 HEAXHub, 5283/8723 portal dev.

## Bring up (in order)

Each service must be **fully detached** so the harness/session ending doesn't kill it.
vLLM uses `setsid` (apptainer FUSE mount dies otherwise); the Python servers use
`setsid` too. Always check the port is free first.

### 1. vLLM (GPU — the heavy one)

```bash
# free VRAM check + kill any leaked EngineCore first
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv
# if a VLLM::EngineCore lingers from a dead run:  kill -9 <pid>

cd /home/koopark/serviceApptainers
setsid bash -c 'APPTAINER_TMPDIR=/data/apptainer_tmp apptainer run --nv \
  --env HF_HOME=/home/koopark/.cache/huggingface --env PYTHONNOUSERSITE=1 \
  vllm-openai-latest.sif \
  --model Qwen/Qwen2.5-7B-Instruct-AWQ --served-model-name qwen2.5-7b-dev \
  --quantization awq --host 0.0.0.0 --port 8000 \
  --max-model-len 16384 --gpu-memory-utilization 0.78 --max-num-seqs 16 \
  --enable-auto-tool-choice --tool-call-parser hermes' \
  > /tmp/vllm-dev.log 2>&1 < /dev/null &
disown
# wait: until curl -s localhost:8000/health; ~1-2 min (model is cached)
```

`PYTHONNOUSERSITE=1` and the two `--*-tool-*` flags are mandatory — see
`docs/dev-vllm-setup.md` §2/§3 for why. Or just run `docs/start-dev-vllm.sh`.

### 2. MCP demo server

```bash
cd /home/koopark/claude/HWAXAgentServer
setsid bash -c '.venv/bin/python mcp_demo_server.py' > /tmp/mcp-demo.log 2>&1 < /dev/null &
disown
# verify tools load:  (GET /mcp returns 406 — that's fine, MCP is POST-only)
```

### 3. Agent Server (LangGraph)

```bash
cd /home/koopark/claude/HWAXAgentServer
VLLM_BASE_URL=http://127.0.0.1:8000/v1 VLLM_MODEL=qwen2.5-7b-dev \
  MCP_SERVERS=demo=http://127.0.0.1:8011/mcp \
  setsid bash -c '.venv/bin/uvicorn app:app --host 0.0.0.0 --port 9009' \
  > /tmp/agent-server.log 2>&1 < /dev/null &
disown
# health should list tools:  curl -s localhost:9009/health
#   {"status":"ok","model":"qwen2.5-7b-dev","tools":["add","multiply","current_time"]}
```

### 4. Portal backend

```bash
cd /home/koopark/claude/HWAXPortal/backend
# agent_server_url default is now :9009 (config.py) — no env override needed
exec .venv/bin/python -m uvicorn app.main:app --port 8723   # run detached/background
```

(Frontend dev server: `pnpm --dir frontend dev` → :5283, proxies /agent to :8723.)

## Verify end-to-end

```bash
cd /tmp; rm -f c.txt
curl -s -c c.txt -L http://127.0.0.1:8723/auth/login >/dev/null     # dev mock login
CSRF=$(grep hwax_csrf c.txt | awk '{print $7}')
curl -s -N -b c.txt -X POST http://127.0.0.1:8723/agent/chat \
  -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" \
  -d '{"message":"123 곱하기 7을 도구로 계산해"}' | grep -E "도구 호출|delta"
# expect:  status 도구 호출: multiply  →  tokens spelling out 861
```

Smoke each layer independently:
- vLLM tool calling: `curl :8000/v1/chat/completions` with a `tools=[...]`, `tool_choice:"auto"` → `finish_reason:"tool_calls"`.
- Agent Server alone: `curl :9009/chat -d '{"message":"55 더하기 45"}'` → `도구 호출: add`.
- Portal echo (no Agent Server needed): `POST :8723/agent/chat?mode=echo`.

## Tear down

```bash
pkill -9 -f "vllm serve"; pkill -9 -f "VLLM::EngineCore"     # vLLM (frees ~13 GB VRAM)
pkill -9 -f "mcp_demo_server"                                # MCP
pkill -9 -f "uvicorn app:app .*9009"                         # Agent Server
pkill -9 -f "uvicorn app.main:app --port 8723"              # portal backend
nvidia-smi --query-gpu=memory.used,memory.free --format=csv  # confirm VRAM freed
```

> `pkill -f "*.sif"` does NOT stop vLLM — the in-container process is `vllm serve`,
> and a `VLLM::EngineCore` child can survive and hold VRAM. Always kill both and
> confirm with `nvidia-smi --query-compute-apps`.

## Known gotchas (all hit + fixed during dev)

| symptom | cause | fix |
|---|---|---|
| `_C.abi3.so: undefined symbol _ZNR5torch7Library4_def…` | host `~/.local` torch shadows container torch | `--env PYTHONNOUSERSITE=1` |
| `CUDA out of memory` but port free | leaked `VLLM::EngineCore` holds VRAM | `kill -9 <EngineCore pid>` |
| vLLM rejects `tool_choice:"auto"` | tool flags missing | `--enable-auto-tool-choice --tool-call-parser hermes` |
| `datetime.UTC` ImportError | Agent venv is Python 3.10 | use `timezone.utc` |
| stale code runs after edit | `__pycache__` | `rm -rf __pycache__` |
| service dies when session ends | foreground/`&` not detached | `setsid … < /dev/null &` (or `exec` in background) |
