#!/usr/bin/env bash
# 호출 추적(Phoenix) SIF 를 고정한 판으로 굽는다 — 인터넷이 되는 박스(dev)에서 한 번. 운영 박스는 Drive 로 받는다(images-from-drive).
#
#   ./infra/scripts/build-phoenix.sh              # → infra/apptainer/phoenix.sif
#   ./infra/scripts/build-phoenix.sh <출력 경로>
#   ./infra/scripts/images-to-drive.sh            # 구운 뒤 — Drive latest/ 에 portal·nginx 와 함께 올린다
#
# 판 고정 — 태그와 다이제스트를 함께 적는다(build-gatus.sh 와 같다). 받기는 다이제스트로 하고, 받은 이미지의 판 라벨
#   (org.opencontainers.image.version — Phoenix 는 'arize-phoenix-v<판>')이 적어 둔 판과 같은지 본다 — 다이제스트만 바꾸고 판을 안 고친
#   실수를 여기서 잡는다. 판을 올릴 때는 아래 두 줄과 docs/improvement-1015/call-trace.md 의 판을 함께 고친다. 새 판에서는 띄우는 셈
#   (infra/call-trace/phoenix_serve.py)이 끄는 gRPC 수신기 자리가 그대로인지도 본다 — 없으면 띄우기가 멈춘다(모든 인터페이스에 열리지 않게).
# 한 겹 더 굽지 않는다 — 공식 이미지(distroless 의 python 3.13 + /phoenix/.venv)가 apptainer 로 그대로 돈다(2026-10-16 dev 실측).
# 받는 동안은 옆의 임시 파일에 쓰고 끝나면 이름을 바꾼다 — 도는 Phoenix 밑의 SIF 를 제자리에서 덮지 않는다(squashfs 가 깨진다).
#   임시 이름은 점으로 시작하고 .sif 로 끝난다(gitignore 의 `*.sif` 에 걸리고, deploy-all 지문의 `infra/apptainer/*.sif` 글롭에는 안 든다).
set -euo pipefail
PHOENIX_VERSION="20.19.0"                                                                   # 2026-10-01 공개
PHOENIX_DIGEST="sha256:d240d8d4e364ee3483ed2de41ec12b760cc90bb0d4c6e2f190388772aba6fe1f"   # 그 판의 다중 아키텍처 목록(OCI index) — amd64 를 골라 받는다
PHOENIX_IMAGE="docker://arizephoenix/phoenix@$PHOENIX_DIGEST"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/infra/apptainer/phoenix.sif}"
# apptainer 찾기는 띄우는 스크립트(call-trace.sh)와 같다 — 리포 안 bin-*/ 의 가장 새 것 → PATH.
A="${APPTAINER:-}"
if [ -z "$A" ]; then
  for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
fi
A="${A:-apptainer}"
command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A) — ./infra/scripts/bootstrap.sh" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp "$(dirname "$OUT")/.phoenix.sif.XXXXXX.sif")"
trap 'rm -f "$TMP"' EXIT
echo "→ Phoenix $PHOENIX_VERSION 받기($PHOENIX_IMAGE)"
"$A" pull --force "$TMP" "$PHOENIX_IMAGE"
_ver="$("$A" inspect --labels "$TMP" 2>/dev/null | sed -n 's/^org\.opencontainers\.image\.version: //p' | head -1)"
if [ "$_ver" != "arize-phoenix-v$PHOENIX_VERSION" ]; then
  echo "✗ 받은 이미지의 판이 '${_ver:-모름}' 이다 — 적어 둔 판 arize-phoenix-v$PHOENIX_VERSION 와 다르다. 두 줄(PHOENIX_VERSION·PHOENIX_DIGEST)을 함께 고친다" >&2
  exit 1
fi
mv -f "$TMP" "$OUT"
trap - EXIT
echo "✓ $OUT  (Phoenix $PHOENIX_VERSION · $(du -h "$OUT" | cut -f1))"
echo "  Drive 로 나르기: ./infra/scripts/images-to-drive.sh   (운영 박스: ./infra/scripts/images-from-drive.sh — update-all §2 가 부른다)"
