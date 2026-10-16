#!/usr/bin/env bash
# LLM 풀 용량 측정용 GuideLLM SIF 를 굽는다 — 인터넷이 되는 dev 에서 1회, cae00 은 Drive 로 받는다(docs/llm-pool/capacity.md)
#
#   ./infra/scripts/build-guidellm.sh                 # → infra/apptainer/guidellm.sif
#   ./infra/scripts/build-guidellm.sh /some/out.sif   # 다른 자리에(시험 빌드)
#   그 뒤 ./infra/scripts/images-to-drive.sh 가 portal.sif 들과 함께 나른다(cae00 은 images-from-drive.sh 로 받는다).
#
# 판은 아래 상수 그대로다 — 바꾸면 이 파일을 커밋한다(굽는 날마다 다른 판이 들지 않게). 의존성은 GUIDELLM_DEPS_BEFORE 이전에 올라온
# 판만 고른다(pip --uploaded-prior-to) — 같은 스크립트는 언제 다시 구워도 같은 의존성 묶음을 고르고, 어느 판도 2주보다 새것이 아니다.
# torch 는 CPU 판이다(GuideLLM 이 데이터 적재에 쓴다 — GPU 를 쓰지 않는다. 쿠다 판은 이미지가 몇 GB 커진다).
#
# 토크나이저를 이미지에 굽는다 — 합성 프롬프트를 '정확히 N 토큰' 으로 자를 때 쓰는데, 기본은 서버의 모델 이름으로 HF 허브에서 받으려 한다.
# cae00 은 인터넷이 없어 그 자리에서 죽는다. 그래서 운영 모델(GLM-5.2)의 토크나이저 파일 둘을 고정 리비전·sha256 으로 받아
# /opt/tokenizers/glm-5.2 에 둔다(llm-capacity.sh 가 그 경로를 준다). 실행 환경은 HF 오프라인이다(%environment).
#
# 키·주소는 이 이미지에 들지 않는다 — 측정 대상과 키는 실행 때 llm-capacity.sh 가 환경으로만 준다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/infra/apptainer/guidellm.sif}"

BASE_IMAGE="python:3.12.14-slim-bookworm"
PIP_VERSION="26.2.1"
TORCH_VERSION="2.14.1+cpu"
TORCH_INDEX="https://download.pytorch.org/whl/cpu"
GUIDELLM_VERSION="0.8.0"
GUIDELLM_DEPS_BEFORE="2026-10-01T00:00:00Z"
TOKENIZER_REPO="zai-org/GLM-5.2"
TOKENIZER_REV="cf457fa734ab149ffef225f80893eb38c6ff5cdc"
TOKENIZER_JSON_SHA256="19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d"
TOKENIZER_CONFIG_SHA256="98b1271574f41abf89427ae2dda030d94dc9478f0edc5a8bd240db213c6fd5fc"

# apptainer 찾기는 _common.sh 와 같다(리포 안 bin-*/ 의 가장 새 것 → PATH). _common.sh 를 소싱하지 않는다 — infra/.env 를 통째로
# export 해 키가 빌드 환경에 들어간다.
A="${APPTAINER:-}"
if [ -z "$A" ]; then
  for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
fi
A="${A:-apptainer}"
command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A) — ./infra/scripts/bootstrap.sh" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
DEF="$(mktemp --suffix=.def)"
trap 'rm -f "$DEF"' EXIT
cat > "$DEF" <<DEFEOF
Bootstrap: docker
From: $BASE_IMAGE

%labels
    Component hwax-llm-capacity
    GuideLLM $GUIDELLM_VERSION
    Torch $TORCH_VERSION
    DepsUploadedBefore $GUIDELLM_DEPS_BEFORE
    Tokenizer $TOKENIZER_REPO@$TOKENIZER_REV
    TokenizerPath /opt/tokenizers/glm-5.2

%post
    set -eux
    export PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore
    python -m pip install "pip==$PIP_VERSION"
    python -m pip install --no-deps --index-url "$TORCH_INDEX" "torch==$TORCH_VERSION"
    python -m pip install --uploaded-prior-to "$GUIDELLM_DEPS_BEFORE" "guidellm==$GUIDELLM_VERSION"
    python -m pip check
    mkdir -p /opt/hwax /opt/tokenizers/glm-5.2
    python - <<'PY'
import hashlib, urllib.request
base = "https://huggingface.co/$TOKENIZER_REPO/resolve/$TOKENIZER_REV/"
for name, want in (("tokenizer.json", "$TOKENIZER_JSON_SHA256"), ("tokenizer_config.json", "$TOKENIZER_CONFIG_SHA256")):
    data = urllib.request.urlopen(base + name, timeout=300).read()
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        raise SystemExit(f"{name} sha256 {got} != {want}")
    open("/opt/tokenizers/glm-5.2/" + name, "wb").write(data)
    print("tokenizer", name, len(data), got)
PY
    python -m pip freeze > /opt/hwax/guidellm-freeze.txt
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -c "from transformers import AutoTokenizer; t = AutoTokenizer.from_pretrained('/opt/tokenizers/glm-5.2'); print('tokenizer ok', len(t.encode('hello world')))"
    guidellm --version

%environment
    export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1
    export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
    # 홈이 바인드되므로 ~/.local/lib/python3.12 의 패키지가 이미지 것보다 먼저 잡힌다 — dev 실측: 그쪽 httpx·typing_extensions 로 죽었다
    export PYTHONNOUSERSITE=1

%help
    HWAX LLM 풀 용량 측정 — GuideLLM $GUIDELLM_VERSION + GLM-5.2 토크나이저(/opt/tokenizers/glm-5.2).
    판 목록: /opt/hwax/guidellm-freeze.txt. 실행은 리포의 infra/scripts/llm-capacity.sh 가 한다.
DEFEOF

echo "→ GuideLLM $GUIDELLM_VERSION SIF 굽기 → $OUT"
if ! "$A" build --force "$OUT" "$DEF"; then
  echo "  ↻ --fakeroot 로 다시"
  "$A" build --fakeroot --force "$OUT" "$DEF"
fi
echo "✓ $OUT ($(du -h "$OUT" | cut -f1))"
"$A" exec "$OUT" guidellm --version
echo "  판 목록: $A exec $OUT cat /opt/hwax/guidellm-freeze.txt"
echo "  Drive 로: ./infra/scripts/images-to-drive.sh   (cae00: ./infra/scripts/images-from-drive.sh)"
