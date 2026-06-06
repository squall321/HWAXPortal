#!/usr/bin/env bash
# Pull pre-built .sif images (+ SPA dist) from Google Drive into infra/apptainer/, so start.sh
# skips the Docker-Hub build entirely. Mirror of MXWhitePaper's data-merge-from-drive.sh.
#
# Needs in infra/.env:  HWAX_DRIVE_REMOTE=ApptainerImages:HWAXPortal/images
# After this:  ./infra/scripts/start.sh   (build will "skip — exists")
set -euo pipefail
"$(dirname "$0")/bootstrap-rclone.sh"   # ensure rclone (no-op if present; installs no-sudo otherwise)
. "$(dirname "$0")/_common.sh"

"$RCLONE" version >/dev/null 2>&1 \
  || { echo "✗ rclone unavailable — run ./infra/scripts/bootstrap-rclone.sh"; exit 1; }
REMOTE="${HWAX_DRIVE_REMOTE:-}"
[ -n "$REMOTE" ] \
  || { echo "✗ HWAX_DRIVE_REMOTE not set in infra/.env (e.g. ApptainerImages:HWAXPortal/images)"; exit 1; }
REMOTE="${REMOTE%/}"

# Source = latest/ if it has the images, else the newest images-<TS>/ dir.
SRC="$REMOTE/latest"
if ! "$RCLONE" lsf "$SRC/" 2>/dev/null | grep -q '^portal\.sif$'; then
  NEWEST="$("$RCLONE" lsf --dirs-only "$REMOTE/" 2>/dev/null \
    | sed 's#/$##' | grep -E '^images-' | sort | tail -n 1 || true)"
  [ -n "$NEWEST" ] \
    || { echo "✗ no images on $REMOTE (no latest/ or images-*/). Push from a build host first:"; \
         echo "    ./infra/scripts/images-to-drive.sh"; exit 1; }
  SRC="$REMOTE/$NEWEST"
fi
echo "→ source: $SRC"

STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
"$RCLONE" copy --progress "$SRC/" "$STAGE/"

# Verify integrity before staging.
if [ -f "$STAGE/SHA256SUMS" ]; then
  ( cd "$STAGE" && sha256sum -c SHA256SUMS ) \
    || { echo "✗ checksum verification failed — not staging"; exit 1; }
  echo "  ✓ checksums OK"
else
  echo "  ⚠ no SHA256SUMS on remote — skipping integrity check"
fi
[ -f "$STAGE/portal.sif" ] && [ -f "$STAGE/nginx.sif" ] \
  || { echo "✗ portal.sif/nginx.sif missing in $SRC"; exit 1; }

mkdir -p "$APPT_DIR"
cp "$STAGE/portal.sif" "$STAGE/nginx.sif" "$APPT_DIR/"
echo "  ✓ staged portal.sif + nginx.sif → $APPT_DIR"

if [ -f "$STAGE/frontend-dist.tar.gz" ]; then
  ( cd "$REPO_ROOT/frontend" && tar -xzf "$STAGE/frontend-dist.tar.gz" )
  echo "  ✓ extracted frontend/dist"
fi

echo
echo "✓ images ready — now run:  ./infra/scripts/start.sh   (build skips, boots from these images)"
