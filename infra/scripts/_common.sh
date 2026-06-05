#!/usr/bin/env bash
# Shared environment for HWAX Portal Apptainer orchestration (portal + nginx).
# Mirrors the MXWhitePaper infra pattern: load infra/.env, name-isolated instances,
# host network, rootless. Instance names are hwax_* so they coexist with mxwp_* etc.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

[ -f infra/.env ] || { echo "✗ infra/.env not found. Run: cp infra/.env.example infra/.env"; exit 1; }
set -a; . ./infra/.env; set +a

# ── Paths ───────────────────────────────────────────────────────────
APPT_DIR="$REPO_ROOT/infra/apptainer"
NGINX_DIR="$REPO_ROOT/infra/nginx"
DATA_DIR="$REPO_ROOT/infra/data"
LOG_DIR="$DATA_DIR/logs"
mkdir -p "$DATA_DIR/portal-secrets" "$LOG_DIR"

# ── Images (.sif) ───────────────────────────────────────────────────
PORTAL_SIF="$APPT_DIR/portal.sif"
NGINX_SIF="$APPT_DIR/nginx.sif"

# ── Instances ───────────────────────────────────────────────────────
INST_PORTAL=hwax_portal
INST_NGINX=hwax_nginx

# ── Ports / defaults (override via infra/.env) ──────────────────────
: "${HTTP_PORT:=8080}"
: "${PORTAL_PORT:=8723}"
: "${PUBLIC_BASE_URL:=http://localhost:${HTTP_PORT}}"
: "${ROUTES_PATH:=config/routes.env}"
: "${APPTAINER:=apptainer}"

require_apptainer() {
  command -v "$APPTAINER" >/dev/null 2>&1 || {
    echo "✗ '$APPTAINER' not found in PATH"; exit 1;
  }
}

instance_running() {
  "$APPTAINER" instance list --json 2>/dev/null \
    | grep -q "\"instance\": *\"$1\"" || return 1
}
