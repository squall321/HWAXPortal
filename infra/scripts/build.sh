#!/usr/bin/env bash
# Build portal.sif + nginx.sif from their .def files (idempotent; --force to rebuild).
# Pulls base images from docker hub. Tries DIRECT first (works on boxes with direct egress),
# then falls back to HWAX_FALLBACK_PROXY (the corporate egress) only if direct fails — so the
# same script works both on this dev box (direct) and inside the locked-down Samsung network.
set -euo pipefail
. "$(dirname "$0")/_common.sh"
require_apptainer

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

PROXY_ENV="${HTTPS_PROXY:-${HTTP_PROXY:-${https_proxy:-${http_proxy:-}}}}"
FALLBACK_PROXY="${HWAX_FALLBACK_PROXY:-}"

_build() {  # $1=sif $2=def $3=proxy(""=direct); remaining args → extra apptainer flags (--fakeroot)
  local sif="$1" def="$2" proxy="$3"; shift 3
  if [ -n "$proxy" ]; then
    HTTP_PROXY="$proxy" HTTPS_PROXY="$proxy" http_proxy="$proxy" https_proxy="$proxy" \
      NO_PROXY="localhost,127.0.0.1,::1" no_proxy="localhost,127.0.0.1,::1" \
      "$APPTAINER" build "$@" --force "$sif" "$def"
  else
    "$APPTAINER" build "$@" --force "$sif" "$def"
  fi
}

build_def() {
  local sif="$1" def="$2"
  if [ "$FORCE" -eq 0 ] && [ -f "$sif" ]; then
    echo "✓ skip $(basename "$sif") (exists — use --force to rebuild)"
    return
  fi
  echo "→ build $(basename "$sif") from $(basename "$def")"

  # Attempt order: env-proxy-or-direct → +fakeroot → fallback-proxy → fallback +fakeroot
  _build "$sif" "$def" "$PROXY_ENV"            && return
  echo "  ↻ retry with --fakeroot"
  _build "$sif" "$def" "$PROXY_ENV" --fakeroot && return
  if [ -n "$FALLBACK_PROXY" ] && [ "$FALLBACK_PROXY" != "$PROXY_ENV" ]; then
    echo "  ↻ retry via fallback proxy $FALLBACK_PROXY"
    _build "$sif" "$def" "$FALLBACK_PROXY"            && return
    _build "$sif" "$def" "$FALLBACK_PROXY" --fakeroot && return
  fi

  echo "✗ build failed for $(basename "$sif")."
  echo "  Docker Hub blocked or rate-limited (TOOMANYREQUESTS)? Don't build here — fetch the"
  echo "  pre-built images instead (built once on a machine that can reach Docker Hub):"
  echo "    ./infra/scripts/images-from-drive.sh      # via Google Drive (rclone), or"
  echo "    scp <host>:.../infra/apptainer/*.sif $APPT_DIR/   # manual copy"
  exit 1
}

build_def "$NGINX_SIF"  "$APPT_DIR/nginx.def"   # fast (alpine) — proves the path first
build_def "$PORTAL_SIF" "$APPT_DIR/portal.def"  # slower (pip install)

echo "✓ images ready in $APPT_DIR"
