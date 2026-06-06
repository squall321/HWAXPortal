#!/usr/bin/env bash
# ONE-TIME (sudo): let rootless processes bind low ports (>= PORT, default 443), so the rootless
# nginx can listen on :443 — no setcap on the read-only SIF needed. Persists across reboots.
#   sudo ./infra/scripts/grant-net-bind.sh        # → ports >= 443
#   sudo ./infra/scripts/grant-net-bind.sh 80     # → ports >= 80 (if you also want plain :80)
#
# This lowers net.ipv4.ip_unprivileged_port_start system-wide (a mild, common relaxation). To undo:
#   sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1024 && sudo rm /etc/sysctl.d/99-hwax-ports.conf
set -euo pipefail
PORT="${1:-443}"

if [ "$(id -u)" -ne 0 ]; then
  echo "✗ needs root. Run:  sudo $0 ${PORT}"
  exit 1
fi

sysctl -w "net.ipv4.ip_unprivileged_port_start=${PORT}"
f=/etc/sysctl.d/99-hwax-ports.conf
echo "net.ipv4.ip_unprivileged_port_start=${PORT}" > "$f"
echo "✓ rootless processes may now bind ports >= ${PORT}  (persisted: $f)"
echo "  now (as your normal user):  ./infra/scripts/start.sh"
