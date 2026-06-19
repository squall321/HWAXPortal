#!/usr/bin/env bash
# Cleanly restart vLLM. The orchestrator's `down` intentionally does NOT touch vLLM
# (stop:"true") because a plain port-kill orphans a VLLM::EngineCore that keeps holding
# VRAM → the next start OOMs. This script kills BOTH the server and the EngineCore, waits
# for the VRAM to free, then starts it back via the orchestrator.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "→ stopping vLLM (server + EngineCore)…"
pkill -9 -f "vllm serve" 2>/dev/null || true
pkill -9 -f "VLLM::EngineCore" 2>/dev/null || true
# Also catch any compute-app still on the GPU named like vllm/EngineCore.
for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null); do
  ps -p "$pid" -o args= 2>/dev/null | grep -qiE "vllm|EngineCore" && kill -9 "$pid" 2>/dev/null || true
done
sleep 4
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader 2>/dev/null | sed 's/^/   VRAM: /'

echo "→ starting vLLM…"
"$ROOT/infra/scripts/services.sh" up vllm
