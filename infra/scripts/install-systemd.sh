#!/usr/bin/env bash
# Register the HWAX stack with systemd so it updates + starts on boot.
#
#   ./infra/scripts/install-systemd.sh          # install + enable (start on boot)
#   ./infra/scripts/install-systemd.sh --now    # also start it now
#   ./infra/scripts/install-systemd.sh remove    # disable + remove the unit
#
# Rootless user service (systemctl --user) + linger so it survives logout / runs on boot.
# The unit just calls the orchestrator (services.py up --update). The only sudo is the
# one-time `loginctl enable-linger` — no passwords stored anywhere.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
UNIT_SRC="$ROOT/infra/systemd/hwax-stack.service"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/hwax-stack.service"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

if [ "${1:-}" = "remove" ]; then
  systemctl --user disable --now hwax-stack.service 2>/dev/null || true
  rm -f "$UNIT"; systemctl --user daemon-reload
  echo "✓ removed hwax-stack.service"; exit 0
fi

# 1. linger — lets the user manager run without an active login (boot start). One-time sudo.
if [ ! -e "/var/lib/systemd/linger/$USER" ]; then
  echo "→ enabling linger (sudo, one-time)…"
  sudo loginctl enable-linger "$USER"
fi

# 2. render the unit (fill in absolute paths) and install it. Bake THIS box's $PATH into the unit
#    (Environment=PATH) so the orchestrator finds pnpm/node/etc. under systemd's minimal env (heax
#    `make build` needs pnpm). Captured per-box at install — nothing box-specific is hardcoded in repo.
mkdir -p "$UNIT_DIR"
sed -e "s#__PORTAL__#$ROOT#g" -e "s#__PY__#$PY#g" -e "s#__PATH__#$PATH#g" "$UNIT_SRC" > "$UNIT"
systemctl --user daemon-reload
systemctl --user enable hwax-stack.service
echo "✓ installed + enabled hwax-stack.service (starts on boot, updates each service first)"

# 3. optionally start now.
if [ "${1:-}" = "--now" ]; then
  echo "→ starting now (up --update; vLLM load can take ~1-2 min)…"
  systemctl --user start hwax-stack.service
  systemctl --user --no-pager status hwax-stack.service | head -6
fi

echo
echo "Manage:  systemctl --user {status|start|stop|restart} hwax-stack"
echo "Logs:    journalctl --user -u hwax-stack -f"
echo "Ad-hoc:  ./infra/scripts/services.sh {up|down|status|update} [name...]"
