#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start-dev-vllm.sh — dev inference backend for HWAX Portal MCP Chat (계획서 §3-1)
#
#   Server : RTX 5070 Ti (Blackwell sm_120), 16 GB VRAM
#   Model  : Qwen/Qwen2.5-7B-Instruct-AWQ (4-bit, ~6 GB)
#   Runtime: Apptainer + official vLLM nightly image (ships sm_120 kernels)
#   API    : OpenAI-compatible, http://127.0.0.1:8000/v1  (consumed by Agent Server)
#
# See docs/dev-vllm-setup.md for the WHY behind every value.
#
# ⚠️ First run pulls a ~10 GB image and a ~6 GB model. Do NOT run blindly.
#    Review docs/dev-vllm-setup.md §3 and confirm disk/VRAM first.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Config (override via env) ────────────────────────────────────────────────
SIF="${VLLM_SIF:-/home/koopark/serviceApptainers/vllm-openai-nightly.sif}"
IMAGE="${VLLM_IMAGE:-docker://vllm/vllm-openai:nightly}"   # nightly = sm_120 kernels
MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
SERVED_NAME="${VLLM_SERVED_NAME:-qwen2.5-7b-dev}"          # stable name; prod swaps weights behind it
PORT="${VLLM_PORT:-8000}"                                  # vLLM's port (Agent Server calls this), NOT the portal's 9000
HOST="${VLLM_HOST:-0.0.0.0}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-16384}"               # 16K KV fits 16 GB; raise only after watching nvidia-smi
GPU_MEM_UTIL="${VLLM_GPU_MEM_UTIL:-0.80}"                  # ~1.5 GB already used by another proc → 0.80, not 0.90
MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-16}"
HF_HOME_DIR="${HF_HOME:-/home/koopark/.cache/huggingface}"
APPTAINER_TMPDIR_DIR="${APPTAINER_TMPDIR:-/data/apptainer_tmp}"  # build scratch (needs ~2x image size)

echo "==> vLLM dev launcher"
echo "    image : $IMAGE"
echo "    sif   : $SIF"
echo "    model : $MODEL  (served as '$SERVED_NAME')"
echo "    api   : http://127.0.0.1:${PORT}/v1"

# ── Preflight: GPU present + free VRAM ───────────────────────────────────────
if ! command -v nvidia-smi >/dev/null; then
  echo "!! nvidia-smi not found — is this the GPU host?" >&2; exit 1
fi
echo "==> current GPU state (another process may already hold VRAM):"
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv

# ── Pull image once (~10 GB) ─────────────────────────────────────────────────
if [[ ! -f "$SIF" ]]; then
  echo "==> SIF not found; pulling $IMAGE (this is large, one-time)…"
  mkdir -p "$APPTAINER_TMPDIR_DIR" "$(dirname "$SIF")"
  APPTAINER_TMPDIR="$APPTAINER_TMPDIR_DIR" apptainer pull "$SIF" "$IMAGE"
else
  echo "==> reusing existing SIF: $SIF"
fi

# ── Launch OpenAI-compatible server ──────────────────────────────────────────
# Model auto-downloads into HF_HOME on first run if not pre-pulled (see docs §3.2).
echo "==> starting vLLM (Ctrl-C to stop)…"
exec apptainer run --nv \
  --env "HF_HOME=${HF_HOME_DIR}" \
  "$SIF" \
  --model "$MODEL" \
  --served-model-name "$SERVED_NAME" \
  --quantization awq \
  --host "$HOST" \
  --port "$PORT" \
  --max-model-len "$MAX_MODEL_LEN" \
  --gpu-memory-utilization "$GPU_MEM_UTIL" \
  --max-num-seqs "$MAX_NUM_SEQS"

# ── Verify (in another shell) ────────────────────────────────────────────────
#   curl -s http://127.0.0.1:8000/v1/models | python3 -m json.tool
#   curl -s http://127.0.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' \
#     -d '{"model":"qwen2.5-7b-dev","messages":[{"role":"user","content":"안녕"}],"max_tokens":32}'
