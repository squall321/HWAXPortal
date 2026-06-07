#!/usr/bin/env bash
# ONE-SHOT cae00 deploy: pull every service's prebuilt artifact from Google Drive and start it.
# cae00 is a corporate-network server (npm + Docker Hub unreachable), so NOTHING is built here —
# each artifact was built ONLINE and pushed to Drive. This script only pulls + starts.
#
#   ./infra/scripts/deploy-all-from-drive.sh                 # all services
#   ./infra/scripts/deploy-all-from-drive.sh portal heax     # only the named ones
#   PORTAL_DIR=~/Projects/HWAXPortal MXWP_DIR=~/Projects/MXWhitePaper \
#   HEAX_DIR=~/Projects/HEAXHub AIDH_DIR=~/Projects/AIDataHub ./infra/scripts/deploy-all-from-drive.sh
#
# Prereqs (once): rclone configured with the shared remote (ApptainerImages:) on this host, and each
# repo's .env has its *_DRIVE_REMOTE / *_IMAGES_REMOTE + the sub-path env (MXWP_BASE_PATH=/mx-white-paper/
# already baked into web.sif; HEAX_BASE_PATH=/heax-hub/ baked into its dist; AIDH_ROOT_PATH=/ai-data-hub).
set -euo pipefail

# ── Repo locations (override via env). Default: siblings of this repo, then ~/Projects. ─────────
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() {  # $1=env-override  $2=dirname
  local v="$1" name="$2"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  for cand in "$PARENT/$name" "$HOME/Projects/$name" "$HOME/claude/$name"; do
    [ -d "$cand" ] && { printf '%s' "$cand"; return; }
  done
}
PORTAL_DIR="${PORTAL_DIR:-$SELF_REPO}"
MXWP_DIR="$(find_repo "${MXWP_DIR:-}" MXWhitePaper)"
HEAX_DIR="$(find_repo "${HEAX_DIR:-}" HEAXHub)"
AIDH_DIR="$(find_repo "${AIDH_DIR:-}" AIDataHub)"

WANT="${*:-portal mxwp heax aidh}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }
hr() { printf '\n\033[1;36m── %s ───────────────────────────────────────\033[0m\n' "$*"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
skip() { printf '  \033[1;33m⚠ skip:\033[0m %s\n' "$*"; }

# ── 1. Portal (the hub) ─────────────────────────────────────────────────────
if want portal; then
  hr "HWAX Portal  ($PORTAL_DIR)"
  ( cd "$PORTAL_DIR"
    git pull --ff-only 2>/dev/null || true
    [ -f infra/.env ] || cp infra/.env.example infra/.env
    ./infra/scripts/images-from-drive.sh      # portal.sif + nginx.sif + frontend/dist
    HWAX_NO_BUILD=1 ./infra/scripts/start.sh ) && ok "portal up" || skip "portal failed (see above)"
fi

# ── 2. MX White Paper (web.sif has the prebuilt dist baked in) ───────────────
if want mxwp; then
  if [ -n "$MXWP_DIR" ]; then
    hr "MX White Paper  ($MXWP_DIR)"
    ( cd "$MXWP_DIR"
      git pull --ff-only 2>/dev/null || true
      [ -f .env ] || cp .env.example .env
      ./infra/scripts/images-from-drive.sh    # web.sif (dist baked) — postgres/meili/minio already present
      ./infra/scripts/start.sh ) && ok "mxwp up" || skip "mxwp failed (see above)"
  else skip "MXWhitePaper repo not found (set MXWP_DIR=)"; fi
fi

# ── 3. HEAX Hub (Caddy serves the pulled dist) ──────────────────────────────
if want heax; then
  if [ -n "$HEAX_DIR" ]; then
    hr "HEAX Hub  ($HEAX_DIR)"
    ( cd "$HEAX_DIR"
      git pull --ff-only 2>/dev/null || true
      [ -f .env ] || { [ -f .env.example ] && cp .env.example .env; }
      ./deploy/apptainer/dist-from-drive.sh   # frontend/dist (+ optional caddy sif)
      HEAX_NO_BUILD=1 bash deploy/apptainer/start.sh ) && ok "heax up" || skip "heax failed (see above)"
  else skip "HEAXHub repo not found (set HEAX_DIR=)"; fi
fi

# ── 4. AI Data Hub (no build, no Drive artifact — git pull + root_path) ──────
if want aidh; then
  if [ -n "$AIDH_DIR" ]; then
    hr "AI Data Hub  ($AIDH_DIR)"
    ( cd "$AIDH_DIR"
      git pull --ff-only 2>/dev/null || true
      AIDH_ROOT_PATH=/ai-data-hub ./boot.sh ) && ok "aidh up" || skip "aidh failed (see above)"
  else skip "AIDataHub repo not found (set AIDH_DIR=)"; fi
fi

hr "Done"
echo "  Portal:  https://hwax.sec.samsung.net/   (tiles: /heax-hub/ /ai-data-hub/ /mx-white-paper/)"
echo "  Health:  curl -k https://127.0.0.1:\${HTTPS_PORT:-443}/health"
