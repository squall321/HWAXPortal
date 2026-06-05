#!/usr/bin/env bash
# Stop + start the HWAX stack (picks up routes.env / infra/.env edits), then show status.
set -euo pipefail
. "$(dirname "$0")/_common.sh"
require_apptainer

"$REPO_ROOT/infra/scripts/stop.sh"
echo
"$REPO_ROOT/infra/scripts/start.sh"
echo
"$REPO_ROOT/infra/scripts/status.sh"
