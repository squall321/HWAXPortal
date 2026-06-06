#!/usr/bin/env bash
# Install rclone WITHOUT sudo by unzipping the single static binary to infra/bin/rclone.
#   ./infra/scripts/bootstrap-rclone.sh           auto: cached zip if present, else download
#   ./infra/scripts/bootstrap-rclone.sh --offline cached zip only (air-gapped); fail if absent
#   ./infra/scripts/bootstrap-rclone.sh --online  force download
#
# Result: infra/bin/rclone  (auto-picked up by _common.sh's $RCLONE resolver).
# rclone is a dependency-free static binary, so this needs no root and no system packages.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN_DIR="$REPO_ROOT/infra/bin"
PKG_DIR="$REPO_ROOT/infra/packages"
[ -f "$REPO_ROOT/infra/.env" ] && { set -a; . "$REPO_ROOT/infra/.env"; set +a; }
FALLBACK_PROXY="${HWAX_FALLBACK_PROXY:-}"

case "$(dpkg --print-architecture 2>/dev/null || uname -m)" in
  amd64|x86_64) ARCH=amd64 ;;
  arm64|aarch64) ARCH=arm64 ;;
  *) ARCH=amd64 ;;
esac

MODE=auto
for a in "$@"; do
  case "$a" in
    --online) MODE=online ;;
    --offline) MODE=offline ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown arg: $a"; exit 1 ;;
  esac
done

# 0. Already usable? (local binary, or PATH rclone)
if [ -x "$BIN_DIR/rclone" ] && "$BIN_DIR/rclone" version >/dev/null 2>&1; then
  echo "✓ rclone already installed: $BIN_DIR/rclone ($("$BIN_DIR/rclone" version 2>/dev/null | head -1))"
  exit 0
fi
if command -v rclone >/dev/null 2>&1; then
  echo "✓ rclone already on PATH: $(command -v rclone) ($(rclone version 2>/dev/null | head -1))"
  exit 0
fi

command -v unzip >/dev/null 2>&1 || { echo "✗ 'unzip' not found (apt-get install unzip)"; exit 1; }
mkdir -p "$BIN_DIR" "$PKG_DIR"

# 1. Locate a cached zip (offline) or download (online).
find_cached_zip() {
  local f
  for f in "$PKG_DIR"/rclone-*-linux-"${ARCH}".zip "$PKG_DIR"/rclone-*.zip; do
    [ -e "$f" ] && { printf '%s' "$f"; return 0; }
  done
  return 1
}

zip="$(find_cached_zip || true)"
if [ -n "$zip" ]; then
  echo "→ using cached zip: $zip"
elif [ "$MODE" = offline ]; then
  echo "✗ --offline but no rclone-*-linux-${ARCH}.zip in $PKG_DIR/"
  echo "  Build the bundle on an online machine:  ./infra/scripts/download-packages.sh"
  exit 1
else
  zip="$PKG_DIR/rclone-current-linux-${ARCH}.zip"
  url="https://downloads.rclone.org/rclone-current-linux-${ARCH}.zip"
  echo "→ downloading rclone (${ARCH})…"
  if ! curl -fL --retry 2 --connect-timeout 15 -o "$zip" "$url"; then
    if [ -n "$FALLBACK_PROXY" ]; then
      echo "  ↻ retry via fallback proxy $FALLBACK_PROXY"
      HTTPS_PROXY="$FALLBACK_PROXY" HTTP_PROXY="$FALLBACK_PROXY" \
        curl -fL --retry 2 -o "$zip" "$url" || { echo "✗ download failed (direct + proxy)"; exit 1; }
    else
      echo "✗ download failed. Pre-stage rclone-*.zip in $PKG_DIR/ and re-run --offline."; exit 1
    fi
  fi
fi

# 2. Extract the single binary (no sudo).
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
unzip -q -o "$zip" -d "$TMP"
SRC=""
for c in "$TMP"/rclone-*/rclone "$TMP"/rclone; do [ -f "$c" ] && SRC="$c" && break; done
[ -n "$SRC" ] || { echo "✗ rclone binary not found inside $zip"; exit 1; }
cp "$SRC" "$BIN_DIR/rclone"
chmod +x "$BIN_DIR/rclone"

# 3. Verify.
"$BIN_DIR/rclone" version >/dev/null 2>&1 || { echo "✗ extracted rclone won't run"; exit 1; }
echo "✓ rclone ready (no sudo): $BIN_DIR/rclone ($("$BIN_DIR/rclone" version 2>/dev/null | head -1))"
echo "  next: register the Drive remote →  ./infra/scripts/setup-drive-sync.sh"
