#!/usr/bin/env bash
# Stop the HWAX Apptainer instances (nginx, then portal).
set -euo pipefail
. "$(dirname "$0")/_common.sh"
require_apptainer

stop_instance() {
  local name="$1"
  if instance_running "$name"; then
    echo "→ stop $name"
    "$APPTAINER" instance stop "$name" || true
  else
    echo "✓ $name not running"
  fi
}

stop_instance "$INST_NGINX"
stop_instance "$INST_PORTAL"

echo "✓ HWAX stopped"
