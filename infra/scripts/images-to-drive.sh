#!/usr/bin/env bash
# Push the built .sif images (+ SPA dist) to Google Drive via rclone, so OTHER servers pull
# them instead of building from Docker Hub (which is rate-limited / blocked on some hosts).
# Mirror of MXWhitePaper's data-dump-to-drive.sh, but for images.
#
# Run on a machine that HAS the images:  ./infra/scripts/build.sh  (once) then this.
# Needs in infra/.env:  HWAX_DRIVE_REMOTE=ApptainerImages:HWAXPortal/images
set -euo pipefail
"$(dirname "$0")/bootstrap-rclone.sh"   # ensure rclone (no-op if present; installs no-sudo otherwise)
. "$(dirname "$0")/_common.sh"

"$RCLONE" version >/dev/null 2>&1 \
  || { echo "✗ rclone unavailable — run ./infra/scripts/bootstrap-rclone.sh"; exit 1; }
REMOTE="${HWAX_DRIVE_REMOTE:-}"
[ -n "$REMOTE" ] \
  || { echo "✗ HWAX_DRIVE_REMOTE not set in infra/.env (e.g. ApptainerImages:HWAXPortal/images)"; exit 1; }
REMOTE="${REMOTE%/}"
RETAIN="${HWAX_DRIVE_RETAIN:-3}"

[ -f "$PORTAL_SIF" ] && [ -f "$NGINX_SIF" ] \
  || { echo "✗ images missing — build first:  ./infra/scripts/build.sh"; exit 1; }

TS="$(date -u +%Y%m%d-%H%M%SZ)"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
cp "$PORTAL_SIF" "$NGINX_SIF" "$STAGE/"

# Bundle the pre-built SPA too (so node-less servers don't need to build it).
if [ -f "$REPO_ROOT/frontend/dist/index.html" ]; then
  ( cd "$REPO_ROOT/frontend" && tar -czf "$STAGE/frontend-dist.tar.gz" dist )
  echo "  · included frontend/dist"
fi

# Checksums over an EXPLICIT file list (so SHA256SUMS doesn't checksum itself).
( cd "$STAGE"
  files="portal.sif nginx.sif"
  [ -f frontend-dist.tar.gz ] && files="$files frontend-dist.tar.gz"
  sha256sum $files > SHA256SUMS )

echo "→ uploading to $REMOTE/images-$TS/  (+ latest/)"
"$RCLONE" copy --progress "$STAGE/" "$REMOTE/images-$TS/"
"$RCLONE" sync --progress "$STAGE/" "$REMOTE/latest/"   # exact mirror so stale files drop

# Retention: keep last N timestamped sets (name sort = chronological).
if [ "$RETAIN" -gt 0 ]; then
  echo "→ retention: keep last $RETAIN image set(s)"
  TO_DELETE="$("$RCLONE" lsf --dirs-only "$REMOTE/" 2>/dev/null \
    | sed 's#/$##' | grep -E '^images-' | sort | head -n -"$RETAIN" || true)"
  for d in $TO_DELETE; do
    [ -z "$d" ] && continue
    echo "  · deleting $d/"
    "$RCLONE" purge "$REMOTE/$d" 2>/dev/null || echo "    ⚠ purge failed (ignore)"
  done
fi

echo
echo "✓ pushed to $REMOTE"
echo "  On another server:  set HWAX_DRIVE_REMOTE in infra/.env  →  ./infra/scripts/images-from-drive.sh"
