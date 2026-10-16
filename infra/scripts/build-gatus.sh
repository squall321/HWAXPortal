#!/usr/bin/env bash
# 상시 상태판(Gatus) SIF 를 고정한 판으로 굽는다 — 인터넷이 되는 박스(dev)에서 한 번. 운영 박스는 Drive 로 받는다(images-from-drive).
#
#   ./infra/scripts/build-gatus.sh              # → infra/apptainer/gatus.sif
#   ./infra/scripts/build-gatus.sh <출력 경로>
#   ./infra/scripts/images-to-drive.sh          # 구운 뒤 — Drive latest/ 에 portal·nginx 와 함께 올린다
#
# 판 고정 — 태그와 다이제스트를 함께 적는다. 태그는 옮겨 붙일 수 있어 받기는 다이제스트로 하고, 받은 이미지의 판 라벨
#   (org.opencontainers.image.version)이 태그와 같은지 본다 — 다이제스트만 바꾸고 태그를 안 고친 실수를 여기서 잡는다.
#   판을 올릴 때는 아래 두 줄과 docs/improvement-1015/status-board.md 의 판을 함께 고친다.
# 한 겹 더 굽지 않는다 — 공식 이미지(scratch 위에 /gatus 하나)가 apptainer 로 그대로 돈다(셸이 없어도 exec 가 된다 — 2026-10-16 dev 실측).
# 받는 동안은 옆의 임시 파일에 쓰고 끝나면 이름을 바꾼다 — 도는 상태판 밑의 SIF 를 제자리에서 덮지 않는다(squashfs 가 깨진다).
#   임시 이름은 점으로 시작하고 .sif 로 끝난다(gitignore 의 `*.sif` 에 걸리고, deploy-all 지문의 `infra/apptainer/*.sif` 글롭에는 안 든다).
set -euo pipefail
GATUS_VERSION="v5.37.0"                                                                    # 2026-09-24 공개
GATUS_DIGEST="sha256:094eb186e55235db367e90e9d56140e5897b7044c41de23cde4cc18e6da1242e"    # 그 태그의 다중 아키텍처 목록(OCI index) — amd64 를 골라 받는다
GATUS_IMAGE="docker://twinproduction/gatus@$GATUS_DIGEST"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/infra/apptainer/gatus.sif}"
# apptainer 찾기는 띄우는 스크립트(status-board.sh)와 같다 — 리포 안 bin-*/ 의 가장 새 것 → PATH.
A="${APPTAINER:-}"
if [ -z "$A" ]; then
  for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
fi
A="${A:-apptainer}"
command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A) — ./infra/scripts/bootstrap.sh" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp "$(dirname "$OUT")/.gatus.sif.XXXXXX.sif")"
trap 'rm -f "$TMP"' EXIT
echo "→ Gatus $GATUS_VERSION 받기($GATUS_IMAGE)"
"$A" pull --force "$TMP" "$GATUS_IMAGE"
_ver="$("$A" inspect --labels "$TMP" 2>/dev/null | sed -n 's/^org\.opencontainers\.image\.version: //p' | head -1)"
if [ "$_ver" != "$GATUS_VERSION" ]; then
  echo "✗ 받은 이미지의 판이 '${_ver:-모름}' 이다 — 적어 둔 태그 $GATUS_VERSION 와 다르다. 두 줄(GATUS_VERSION·GATUS_DIGEST)을 함께 고친다" >&2
  exit 1
fi
mv -f "$TMP" "$OUT"
trap - EXIT
echo "✓ $OUT  (Gatus $GATUS_VERSION · $(du -h "$OUT" | cut -f1))"
echo "  Drive 로 나르기: ./infra/scripts/images-to-drive.sh   (운영 박스: ./infra/scripts/images-from-drive.sh — update-all §2 가 부른다)"
