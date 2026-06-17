# Dev vLLM Setup — RTX 5070 Ti (Blackwell sm_120) + Qwen2.5 7B AWQ

> **Scope.** This is the **dev inference backend** for HWAX Portal MCP Chat
> (계획서 §3-1, decision §7-E). It runs vLLM with an OpenAI-compatible HTTP API
> on **this** server's RTX 5070 Ti. The portal never talks to vLLM directly — the
> **Agent Server** (LangGraph, 별도 서비스) does. The portal only needs the Agent
> Server URL in `routes.env`. So vLLM's port is an **internal contract between
> vLLM and the Agent Server**, independent of the portal's `agent-server=…:9000`.
>
> **prod** is a separate B300 host with Qwen 72B; code is identical, only
> `routes.env` IP/model swap (§3-1). This document is dev-only.
>
> **✅ INSTALLED & VERIFIED 2026-06-16 on this box.** vLLM `:latest` (0.23.0) runs
> Qwen2.5-7B-AWQ on the 5070 Ti and answers in Korean over `/v1/chat/completions`.
> GPU use ~13.7 GB / 16 GB, KV cache 104K tokens. Two gotchas were hit and fixed:
>
> 1. **Use `:latest`, not `:nightly`.** The 2026-06-16 nightly image shipped a
>    broken `_C.abi3.so` (its own torch ABI mismatch). `:latest` (0.23.0) is clean.
> 2. **`PYTHONNOUSERSITE=1` is REQUIRED.** apptainer bind-mounts `$HOME`, so the
>    host `~/.local/.../torch` shadows the container torch and breaks vLLM's `_C`
>    (undefined symbol `_ZNR5torch7Library4_def…`). Without the env var, BOTH
>    nightly and latest fail identically — it is NOT an image bug, it's host bleed.
>
> Launch with `docs/start-dev-vllm.sh` (already updated with both fixes).

---

## 0. TL;DR — recommended path

**Use the official vLLM `:latest` container via Apptainer, with `PYTHONNOUSERSITE=1`.**
On a consumer Blackwell card (sm_120), `:latest` (v0.23.0) ships kernels
**pre-compiled for SM 12.0** — no source build, and the container's PyTorch never
clobbers the `~/.local` one other projects (stable-diffusion, xformers, …) depend on.
(The 2026-06-14 research recommended `:nightly`; the 2026-06-16 install proved
`:latest` is the right tag and that nightly's build was broken — see §2.)

```text
Apptainer (vllm/vllm-openai:latest, --nv, PYTHONNOUSERSITE=1)  →  Qwen/Qwen2.5-7B-Instruct-AWQ
   --max-model-len 16384  --gpu-memory-utilization 0.78  --port 8000
   --enable-auto-tool-choice  --tool-call-parser hermes
```

A pip-venv alternative is in §4, but read §5 first — it has real footguns on this
box. Either way the model and launch flags (§3.3) are the same.

---

## 1. Measured environment (this server, 2026-06-14)

| Item | Value | Note |
|---|---|---|
| GPU | NVIDIA GeForce RTX 5070 Ti | Blackwell, **sm_120** |
| VRAM total / free | 16303 MiB / ~14283 MiB free | ~1.5 GB already used by an existing `api_server` python process — **check `nvidia-smi` before launch** |
| Driver / CUDA | 580.159.03 / CUDA 13.0 | meets Blackwell's CUDA ≥ 12.8 requirement |
| OS / glibc | Ubuntu 22.04.5 / glibc 2.35 | manylinux_2_35 wheels OK |
| Python | 3.10.12 (system) | vLLM supports 3.10–3.13 |
| **torch (already installed)** | **2.9.0+cu128**, `cuda.is_available()=True` on the 5070 Ti | in `~/.local` (user site). **Shared** — `Required-by: accelerate, xformers, torchvision, koo-stable-diffusion-manager, …`. Do **NOT** install vLLM into this environment (§5). |
| vLLM | not installed | — |
| Containers | `apptainer 1.3.3` (+ `--nv` works), `singularity`. **No docker, no conda.** | existing GPU runs on this box use `apptainer … --nv`; `nvidia-container-cli` absent so `--nvccli` is unavailable — plain `--nv` is correct. |
| Disk | `/home` 571 GB free, `/data` 3.6 TB free | image (~10 GB) + HF cache fit on `/home`; can redirect to `/data` if preferred |
| HF cache | `~/.cache/huggingface` (19 GB) | already has `Qwen2.5-Coder-7B-Instruct-AWQ` **metadata only** (12K, blobs not downloaded). The plain `Qwen2.5-7B-Instruct-AWQ` is **not** cached yet. |

**Load-bearing fact:** PyTorch **stable** `2.9.0+cu128` already runs on this exact
5070 Ti here. The widely-cited "you must build from source / no cu128 stable
wheels exist" advice (vLLM forum, early–mid 2025) is **stale** for this box — the
cu128 PyTorch deadlock it describes is already resolved here. That said, the
*vLLM* wheel still has a version-pin mismatch (§5), which is why the container
path is recommended.

---

## 2. Version compatibility — what actually supports sm_120

Researched 2026-06-14 (sources at the bottom). Summary:

- **Blackwell sm_120 needs CUDA ≥ 12.8 and a PyTorch built with cu128+** — met here (driver CUDA 13.0, torch 2.9.0+cu128).
- **OLD stable (e.g. `v0.9.0`) did NOT support sm_120** — `CUDA error: no kernel
  image is available` on RTX 5090/5070 Ti. That is what the 2026-06-14 research saw.
- **ACTUAL INSTALL (2026-06-16) overturned the nightly recommendation:**
  - `vllm/vllm-openai:**latest**` (v0.23.0, torch 2.12+cu130) **DOES ship sm_120
    kernels** and runs Qwen2.5-7B-AWQ on this 5070 Ti — verified, answers in Korean.
    **Use `:latest`.**
  - `vllm/vllm-openai:**nightly**` (the 2026-06-16 build) shipped a **broken
    `_C.abi3.so`** (its own torch ABI mismatch) — do NOT use it. The "nightly is the
    only path" advice above is superseded.
- **AWQ on vLLM**: fully supported. `Qwen/Qwen2.5-7B-Instruct-AWQ` is a 4-bit AWQ
  build, ~6 GB weights; `--quantization awq` is explicit (vLLM also auto-detects).

**⚠️ The real gotcha was NOT the GPU — it was host bleed.** apptainer bind-mounts
`$HOME`, so the host `~/.local/.../torch` shadows the container torch and breaks
vLLM's `_C` (undefined symbol `_ZNR5torch7Library4_def…`) — identically on BOTH
nightly and latest. **`PYTHONNOUSERSITE=1` is mandatory** (makes Python ignore the
user site so the container's own torch loads). With it, `:latest` just works.

---

## 3. Recommended: Apptainer + official `:latest` image

This box already runs GPU workloads via `apptainer … --nv` (rootless, no docker).
We pull the official vLLM `:latest` OCI image into a `.sif` and run it.
**Simplest path: just run `docs/start-dev-vllm.sh`** (does the pull + launch with all
the fixes baked in). The manual steps below are the same thing, expanded.

### 3.1 Pull the image (one-time, ~7.6 GB)

```bash
# Land big artifacts on /home (571 GB free) — or swap to /data if you prefer.
export VLLM_SIF_DIR=/home/koopark/serviceApptainers
export APPTAINER_TMPDIR=/data/apptainer_tmp   # build scratch; needs ~2x image size
mkdir -p "$APPTAINER_TMPDIR"

# :latest (v0.23.0) ships sm_120 kernels AND has a consistent torch/_C (nightly did not).
apptainer pull "$VLLM_SIF_DIR/vllm-openai-latest.sif" \
  docker://vllm/vllm-openai:latest
```

### 3.2 Download the model (one-time, ~6 GB) — optional pre-pull

vLLM will auto-download on first launch into `~/.cache/huggingface`. To pre-pull
explicitly (so the first server start isn't blocked on a 6 GB download):

```bash
# huggingface_hub CLI (already present via the existing HF cache tooling)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-AWQ \
  --local-dir-use-symlinks False
# downloads to ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ
```

> The cache currently holds only the **Coder** AWQ variant's metadata. The plain
> instruct `Qwen2.5-7B-Instruct-AWQ` (what the plan specifies) is a separate repo
> and will be a fresh ~6 GB pull.

### 3.3 Launch the OpenAI-compatible server

```bash
# Sanity: confirm free VRAM first (an api_server already holds ~1.5 GB).
nvidia-smi --query-gpu=memory.free --format=csv

apptainer run --nv \
  --env HF_HOME=/home/koopark/.cache/huggingface \
  --env PYTHONNOUSERSITE=1 \
  /home/koopark/serviceApptainers/vllm-openai-latest.sif \
  --model Qwen/Qwen2.5-7B-Instruct-AWQ \
  --quantization awq \
  --port 8000 \
  --host 0.0.0.0 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.78 \
  --served-model-name qwen2.5-7b-dev \
  --max-num-seqs 16 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

> `PYTHONNOUSERSITE=1` is mandatory (host `~/.local` torch bleed — see §2/§5).
> `--enable-auto-tool-choice --tool-call-parser hermes` turn on Qwen2.5 tool calling
> (the Agent Server's LangGraph ReAct loop needs it). gpu-util 0.78 leaves headroom
> for other GPU users on this shared box; raise toward 0.80 if the card is idle.
> **If you hit `CUDA out of memory`**, check `nvidia-smi --query-compute-apps` for a
> leaked `VLLM::EngineCore` from a prior run and `kill -9` it — `pkill -f *.sif`
> won't catch it (the in-container process is `vllm serve`, not the .sif name).

**Why these values (16 GB card):**

| Flag | Value | Reason |
|---|---|---|
| `--gpu-memory-utilization` | **0.80** | ~1.5 GB is already taken by another process; 0.90 risks OOM at startup. 0.80 of 16 GB ≈ 13 GB budget. Raise toward 0.85 only after confirming the GPU is otherwise idle. |
| `--max-model-len` | **16384** | AWQ weights ≈ 6 GB; the rest is KV cache. 16K keeps KV comfortably inside ~7 GB headroom. The model supports 32K (and 128K via YaRN), but 32K KV cache is tight on 16 GB — start at 16K, raise if `nvidia-smi` shows room. |
| `--quantization awq` | explicit | vLLM auto-detects, but explicit avoids ambiguity. (Newer vLLM may suggest `awq_marlin` — accept its auto-upgrade.) |
| `--max-num-seqs` | 16 | caps concurrent sequences so KV cache doesn't blow up under the portal's concurrency (계획서 §7-G semaphore caps upstream anyway). |
| `--served-model-name` | `qwen2.5-7b-dev` | stable name the Agent Server targets; prod swaps the weights behind the same name. |

> **Port note (계획서 §2-C):** `--port 8000` is **vLLM's** port, consumed by the
> Agent Server, **not** the portal. The portal's `routes.env` `agent-server=…:9000`
> points at the *Agent Server*, which in turn calls `http://127.0.0.1:8000/v1`.
> These two ports are deliberately different. On this box ports 4180/8001/5173/
> 8800/17370/18000/17370 are already used by other services; 8000 and 9000 are free.

A ready-to-edit launcher is at **`docs/start-dev-vllm.sh`** (do not run blindly —
it pulls/downloads on first run).

---

## 4. Alternative: pip venv (only if you can't use the container)

**Isolated venv is mandatory** — never `pip install vllm` into `~/.local` (§5).

```bash
# Fresh venv with its OWN torch (do NOT reuse ~/.local torch).
python3 -m venv /home/koopark/vllm-dev-venv
source /home/koopark/vllm-dev-venv/bin/activate
pip install --upgrade pip

# Install the vLLM cu128 wheel + matching cu128 torch in ONE resolve.
# (The default vLLM wheel pulls cu129 torch; the +cu128 wheel + cu128 index
#  keeps everything on the CUDA 12.8 line that this driver/card is proven on.)
export VLLM_VERSION=0.23.0          # latest stable as of 2026-06-12; bump as needed
export CUDA_VERSION=128
export CPU_ARCH=$(uname -m)         # x86_64
pip install \
  "https://github.com/vllm-project/vllm/releases/download/v${VLLM_VERSION}/vllm-${VLLM_VERSION}+cu${CUDA_VERSION}-cp38-abi3-manylinux_2_35_${CPU_ARCH}.whl" \
  --extra-index-url https://download.pytorch.org/whl/cu${CUDA_VERSION}

# Launch (same flags as §3.3, just no apptainer wrapper):
vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ \
  --quantization awq --port 8000 --host 0.0.0.0 \
  --max-model-len 16384 --gpu-memory-utilization 0.80 \
  --served-model-name qwen2.5-7b-dev --max-num-seqs 16
```

**⚠️ Risk on this exact pip path (verify, don't assume):** vLLM `v0.23.0` pins
`torch==2.11.0`. The `+cu128` wheel + cu128 index *should* resolve a cu128 torch,
but whether a cu128 build of torch 2.11.0 exists on the PyTorch index at install
time is **not guaranteed** and was the source of the historical "deadlock." If the
resolver fails or installs a non-sm_120 torch, you'll hit `no kernel image`
(§6). The container (§3) sidesteps this entirely by shipping a pre-matched,
sm_120-compiled torch+vLLM. **Prefer §3 unless you have a reason not to.**

---

## 5. Why NOT install into the existing `~/.local` (critical)

The installed `torch 2.9.0+cu128` lives in `~/.local/lib/python3.10/site-packages`
and is **`Required-by:` accelerate, xformers, torchvision, torchaudio, peft, timm,
basicsr, realesrgan, gfpgan, koo-stable-diffusion-manager**, etc.

- A bare `pip install vllm` (user site) would **upgrade torch to 2.11.0** (vLLM's
  pin) and very likely **break those other projects** on this shared box.
- It would also probably pull a **cu129** torch, drifting off the cu128 line the
  card is proven on.

→ Therefore: **container (own userspace) or a dedicated venv (own torch). Never
the global user environment.** This is the single most important constraint here.

---

## 6. Verify it works (curl)

Once the server logs `Application startup complete` / `Uvicorn running on
http://0.0.0.0:8000`:

```bash
# 1) Model is served?
curl -s http://127.0.0.1:8000/v1/models | python3 -m json.tool
# expect: data[0].id == "qwen2.5-7b-dev"

# 2) Chat completion (OpenAI-compatible) — the exact shape the Agent Server uses.
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "qwen2.5-7b-dev",
        "messages": [{"role":"user","content":"한 줄로 자기소개 해줘."}],
        "max_tokens": 64,
        "temperature": 0.7
      }' | python3 -m json.tool
# expect: choices[0].message.content non-empty

# 3) Health
curl -s http://127.0.0.1:8000/health   # 200 OK when ready
```

---

## 6-1. 어디에 IP를 넣나 — dev↔prod 스왑은 주소 한 줄

vLLM은 OpenAI 호환 API라, **연결할 쪽에 `http://<IP>:<port>/v1` 주소만 넣으면 그 서버 모델을 알아서 쓴다**(코드 변경 0). 계층은 3단:

```
포털 routes.env        Agent Server 설정           vLLM (--host 0.0.0.0)
agent-server=          OPENAI_BASE_URL=            Qwen 모델 실행
http://<AGENT-IP>:9000/  http://<vLLM-IP>:8000/v1   http://0.0.0.0:8000/v1
```

- **vLLM을 외부 IP로 호출하려면 `--host 0.0.0.0`으로 띄워야 한다**(이 문서의 기동 명령에 이미 포함). 그래야 다른 호스트의 Agent Server가 `http://<이서버-IP>:8000/v1`로 접근 가능.
- dev↔prod 전환 = **이 vLLM 주소만 교체**:

| | vLLM 주소 (Agent Server가 호출) |
|---|---|
| dev | `http://127.0.0.1:8000/v1` — 이 서버 5070 Ti, Qwen 7B |
| prod | `http://<B300-IP>:8000/v1` — B300, Qwen 72B |

- 포털 `routes.env`의 `agent-server=…:9000`은 **그 앞단 Agent Server**를 가리킨다(vLLM이 아님). vLLM 주소는 Agent Server 설정에 들어간다 — 둘을 헷갈리지 말 것.
- 방화벽: 다른 호스트에서 접근하면 그 포트(8000)가 사내망에서 열려 있어야 한다.

**VRAM monitoring while it runs:**

```bash
watch -n 2 'nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv'
# steady-state for 7B-AWQ @16K should sit roughly 11–13 GB used. If it climbs to
# ~16 GB and OOMs under load, lower --max-model-len or --gpu-memory-utilization.
```

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `CUDA error: no kernel image is available for execution on the device` | vLLM/torch **not compiled for sm_120** (an OLD stable image or a non-cu128 torch) | Use `vllm/vllm-openai:latest` (§3) — verified to ship sm_120 kernels. For pip, force the `+cu128` wheel + cu128 index (§4); confirm `python -c "import torch;print(torch.cuda.get_device_capability())"` returns `(12, 0)`. |
| `ImportError: …/_C.abi3.so: undefined symbol: _ZNR5torch7Library4_def…` | host `~/.local` torch shadows the container torch (apptainer binds `$HOME`) | Add `--env PYTHONNOUSERSITE=1` to the `apptainer run` (§3.3). Hits BOTH nightly and latest without it. |
| `CUDA error: out of memory` at engine init while `nvidia-smi` shows the port free | leaked `VLLM::EngineCore` from a prior run still holds VRAM | `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` → `kill -9 <EngineCore pid>`. `pkill -f *.sif` misses it (in-container name is `vllm serve`). |
| `torch.cuda.is_available() == False` inside container | `--nv` missing or driver mismatch | Always pass `--nv`. Verify host `nvidia-smi` works first. |
| OOM at startup (`CUDA out of memory`) | KV cache + weights > free VRAM (remember ~1.5 GB is pre-used) | Lower `--gpu-memory-utilization` to 0.75, and/or `--max-model-len` to 8192. Check `nvidia-smi` for other processes. |
| OOM only under concurrent load | KV cache exhausted by many sequences | Lower `--max-num-seqs` (e.g. 8) or `--max-model-len`. |
| Slow first request | model downloading / CUDA graph capture / weight load | Pre-pull model (§3.2); first launch always slower. |
| `awq` rejected / suggests `awq_marlin` | newer vLLM kernel preference | Drop `--quantization awq` and let vLLM auto-pick `awq_marlin` (faster on Blackwell). |
| Apptainer can't write HF cache | container HOME mismatch | Pass `--env HF_HOME=/home/koopark/.cache/huggingface` (already in §3.3); ensure it's writable. |
| `--nvccli` errors | `nvidia-container-cli` not installed on this box | Don't use `--nvccli`; plain `--nv` is correct here. |
| Image pull fails on `/home` space | scratch in `$APPTAINER_TMPDIR` too small | Point `APPTAINER_TMPDIR` at `/data` (3.6 TB free). |

---

## 8. Open items / risks

1. ✅ **sm_120 on 5070 Ti** — RESOLVED. `:latest` (v0.23.0) runs Qwen2.5-7B-AWQ on
   this 5070 Ti, verified 2026-06-16 (Korean inference + tool calls). No longer a risk.
2. **pip path torch pin** — vLLM v0.23.0 ⇒ torch 2.12; a pip install would clobber
   the `~/.local` torch other projects use. The container avoids it — prefer it (§4).
3. **32K context** — flags use 16K for safety on 16 GB. 32K may fit but is
   untested here; raise only after watching `nvidia-smi` headroom.
4. **Tag drift** — `:latest` also moves. Pin a dated digest once you have a
   known-good one (current good: v0.23.0) so dev is reproducible.
5. **Shared GPU** — chrome/AIDataHub/ollama and leaked EngineCores can hold VRAM;
   we run at 0.78 for headroom. Check `nvidia-smi --query-compute-apps` before launch.
6. **Not persisted** — dev vLLM/MCP/Agent run via `setsid`/background; they die on
   reboot. Register as apptainer instances / a supervisor before relying on them.

---

## Sources

- vLLM GPU install docs (cu128 wheel command, Blackwell ≥ CUDA 12.8): https://docs.vllm.ai/en/stable/getting_started/installation/gpu/
- vLLM releases (v0.23.0, 2026-06; torch 2.11.0 pin via requirements/cuda.txt): https://github.com/vllm-project/vllm/releases
- vLLM forum — official `vllm-openai:nightly` ships SM 12.0 kernels (stable v0.9.0 fails on 5090): https://discuss.vllm.ai/t/docker-image-vllm-vllm-openai-v0-9-0-doesnt-work-on-5090/761
- vLLM forum — working RTX 5090 setup with torch 2.9.0 cu128: https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492
- GitHub #13306 — RTX 5090 / sm_120 support tracking: https://github.com/vllm-project/vllm/issues/13306
- GitHub #41614 — RTX 5070 Ti (sm_120) setup notes: https://github.com/vllm-project/vllm/issues/41614
- ligma.blog — RTX 5070 Ti vLLM guide (AWQ, --gpu-memory-utilization 0.90, --max-model-len): https://ligma.blog/post1/
- Qwen2.5-7B-Instruct-AWQ model card (4-bit AWQ, 32K/128K context, vLLM recommended): https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ
