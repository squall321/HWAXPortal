#!/usr/bin/env bash
# ONLINE build host: build every service for the HWAX portal sub-path and push the artifacts to
# Google Drive, so cae00 can deploy with `deploy-all-from-drive.sh` (no build there).
# Run on a machine that CAN reach npm + Docker Hub and has pnpm + apptainer + rclone.
#
#   ./infra/scripts/build-all-to-drive.sh                 # all
#   ./infra/scripts/build-all-to-drive.sh portal mxwp     # only named
set -euo pipefail
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local v="$1" n="$2"; [ -n "$v" ] && { printf '%s' "$v"; return; }
  for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
PORTAL_DIR="${PORTAL_DIR:-$SELF_REPO}"
MXWP_DIR="$(find_repo "${MXWP_DIR:-}" MXWhitePaper)"
HEAX_DIR="$(find_repo "${HEAX_DIR:-}" HEAXHub)"
WANT="${*:-portal mxwp heax}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }
hr() { printf '\n\033[1;36m── %s ───────────────────────────────────────\033[0m\n' "$*"; }

if want portal; then
  hr "HWAX Portal — build SPA + sif → Drive"
  ( cd "$PORTAL_DIR"
    pnpm --dir frontend install --frozen-lockfile=false && pnpm --dir frontend build
    ./infra/scripts/build.sh                       # portal.sif + nginx.sif (skips if present)
    ./infra/scripts/images-to-drive.sh )
fi

if want mxwp && [ -n "$MXWP_DIR" ]; then
  hr "MX White Paper — build dist + bake web.sif → Drive"
  ( cd "$MXWP_DIR"
    pnpm install --frozen-lockfile=false && pnpm schema:gen
    VITE_BASE_PATH=/mx-white-paper/ pnpm --filter @mx/web build
    apptainer build --force infra/apptainer/web.sif infra/apptainer/web.def   # bakes dist
    ./infra/scripts/images-to-drive.sh )
fi

if want heax && [ -n "$HEAX_DIR" ]; then
  hr "HEAX Hub — build dist → Drive"
  ( cd "$HEAX_DIR"
    pnpm --dir frontend install --frozen-lockfile=false
    HEAX_BASE_PATH=/heax-hub/ pnpm --dir frontend build
    ./deploy/apptainer/dist-to-drive.sh )
fi

hr "Done — AIDataHub has no build (cae00 just git pulls). Now on cae00: deploy-all-from-drive.sh"
