#!/usr/bin/env bash
# Verify rclone + a Google-Drive remote, then write HWAX_DRIVE_REMOTE into infra/.env.
# The heavy OAuth is a one-time `rclone config` (type: drive); this just wires it up.
#   ./infra/scripts/setup-drive-sync.sh --remote=ApptainerImages:HWAXPortal/images
# Standalone (does not require infra/.env to exist yet).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV="$REPO_ROOT/infra/.env"

REMOTE_ARG=""
for a in "$@"; do
  case "$a" in
    --remote=*) REMOTE_ARG="${a#*=}" ;;
    -h|--help) sed -n '2,6p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown arg: $a"; exit 1 ;;
  esac
done

command -v rclone >/dev/null 2>&1 \
  || { echo "✗ rclone not installed:  apt-get install rclone  (or https://rclone.org/install/)"; exit 1; }

# Take remote from --remote, else existing infra/.env value.
REMOTE="$REMOTE_ARG"
[ -z "$REMOTE" ] && [ -f "$ENV" ] && REMOTE="$(sed -n 's/^HWAX_DRIVE_REMOTE=//p' "$ENV" | tail -1)"
if [ -z "$REMOTE" ]; then
  echo "Configured rclone remotes:"; rclone listremotes 2>/dev/null | sed 's/^/  /'
  echo "✗ pass --remote=<name:path>, e.g. --remote=ApptainerImages:HWAXPortal/images"
  exit 1
fi
REMOTE="${REMOTE%/}"
RNAME="${REMOTE%%:*}"

rclone listremotes 2>/dev/null | grep -qx "${RNAME}:" \
  || { echo "✗ rclone remote '${RNAME}:' not found. Configure it once:  rclone config  (type: drive)"; exit 1; }
rclone lsd "${RNAME}:" >/dev/null 2>&1 \
  || { echo "✗ cannot reach '${RNAME}:' (auth/network). Try:  rclone config reconnect ${RNAME}:"; exit 1; }
echo "✓ rclone remote '${RNAME}:' reachable"

[ -f "$ENV" ] || cp "$REPO_ROOT/infra/.env.example" "$ENV"
if grep -qE '^HWAX_DRIVE_REMOTE=' "$ENV"; then
  sed -i "s#^HWAX_DRIVE_REMOTE=.*#HWAX_DRIVE_REMOTE=$REMOTE#" "$ENV"
else
  printf '\nHWAX_DRIVE_REMOTE=%s\n' "$REMOTE" >> "$ENV"
fi
echo "✓ infra/.env → HWAX_DRIVE_REMOTE=$REMOTE"
echo "  push images (build host):  ./infra/scripts/images-to-drive.sh"
echo "  pull images (any server):  ./infra/scripts/images-from-drive.sh"
