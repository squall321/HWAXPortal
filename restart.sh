#!/usr/bin/env bash
# HWAX Portal — restart the dev servers cleanly.
#   ./restart.sh         stop anything on the portal ports, then start backend + frontend
#   ./restart.sh stop    just stop them
#   ./restart.sh --bg    restart in the background (logs → restart.log), return to the shell
#
# Ports: backend 8723, frontend 5283 (uncommon to avoid collisions on shared boxes).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BACK_PORT=8723
FRONT_PORT=5283

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "  • stopping :${port} (pid: ${pids//$'\n'/ })"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 0.6
    pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
    # shellcheck disable=SC2086
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  else
    echo "  • :${port} already free"
  fi
}

stop_all() {
  echo "▶ stopping portal servers…"
  kill_port "$BACK_PORT"
  kill_port "$FRONT_PORT"
}

preflight() {
  if [ ! -x "backend/.venv/bin/python" ]; then
    echo "✗ backend/.venv missing. Run setup first:" >&2
    echo "    python3.13 -m venv backend/.venv && backend/.venv/bin/pip install -e backend" >&2
    exit 1
  fi
  if [ ! -d "frontend/node_modules" ]; then
    echo "✗ frontend deps missing. Run:  pnpm --dir frontend install" >&2
    exit 1
  fi
  if [ ! -f "backend/.env" ]; then
    echo "  ! backend/.env not found — copying from .env.example (dev defaults)"
    cp .env.example backend/.env
  fi
}

case "${1:-}" in
  stop)
    stop_all
    echo "✓ stopped."
    ;;
  --bg)
    preflight
    stop_all
    echo "▶ starting in background → $ROOT/restart.log"
    nohup pnpm dev >restart.log 2>&1 &
    sleep 3
    echo "✓ backend  → http://localhost:${BACK_PORT}"
    echo "✓ frontend → http://localhost:${FRONT_PORT}"
    echo "  logs: tail -f restart.log   |   stop: ./restart.sh stop"
    ;;
  "")
    preflight
    stop_all
    echo "▶ starting dev servers (backend :${BACK_PORT}, frontend :${FRONT_PORT})…"
    echo "  → http://localhost:${FRONT_PORT}    (Ctrl-C to stop)"
    exec pnpm dev
    ;;
  *)
    echo "usage: ./restart.sh [stop|--bg]" >&2
    exit 2
    ;;
esac
