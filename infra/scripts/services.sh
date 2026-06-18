#!/usr/bin/env bash
# Thin wrapper around the orchestrator (infra/scripts/services.py).
#   ./infra/scripts/services.sh up [name ...]      # start the whole stack (or named)
#   ./infra/scripts/services.sh status [name ...]   # health probe
#   ./infra/scripts/services.sh down [name ...]     # stop
#
# Reads infra/services.yaml. Local services auto-discover their repo dir; remote services
# use SSH key auth (no passwords). See infra/services.yaml for the manifest.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Prefer the portal backend venv (has PyYAML); fall back to system python3.
PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

exec "$PY" "$ROOT/infra/scripts/services.py" "$@"
