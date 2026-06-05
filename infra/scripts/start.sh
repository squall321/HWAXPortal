#!/usr/bin/env bash
# Start the HWAX stack: portal + nginx as Apptainer instances (host network, rootless).
# Order: build images → build SPA (host) → generate nginx conf → portal → nginx.
set -euo pipefail
# Ensure apptainer exists (no-op if present; downloads/extracts it no-sudo otherwise).
# Runs BEFORE _common.sh so the freshly-extracted binary is picked up.
"$(dirname "$0")/bootstrap.sh"
. "$(dirname "$0")/_common.sh"
require_apptainer

"$(dirname "$0")/build.sh"

# 1. SPA must be built (host). Skip if dist already present.
if [ ! -f "$REPO_ROOT/frontend/dist/index.html" ]; then
  if command -v pnpm >/dev/null 2>&1; then
    echo "→ building SPA (frontend/dist)…"
    ( cd "$REPO_ROOT/frontend" && pnpm install --frozen-lockfile=false && pnpm build ) \
      > "$LOG_DIR/spa-build.log" 2>&1 \
      || { echo "✗ SPA build failed (see $LOG_DIR/spa-build.log)"; exit 1; }
  else
    echo "✗ frontend/dist missing and pnpm not on host."
    echo "  Build the SPA on a machine with Node, copy frontend/dist here, then re-run."
    exit 1
  fi
fi
echo "✓ SPA ready (frontend/dist)"

# 2. Generate nginx conf from routes.env
"$(dirname "$0")/gen-nginx-conf.sh"

# 3. Portal (single-origin: serves SPA + API). All config via --env (overrides backend/.env).
if instance_running "$INST_PORTAL"; then
  echo "✓ $INST_PORTAL already running"
else
  echo "→ start $INST_PORTAL (:$PORTAL_PORT)"
  "$APPTAINER" instance start \
    --bind "$REPO_ROOT:/workspace" \
    --env "APP_ENV=${APP_ENV:-prod}" \
    --env "SERVE_FRONTEND=true" \
    --env "JWT_AUTOGEN_KEYS=true" \
    --env "FRONTEND_DIST=../frontend/dist" \
    --env "PORT=${PORTAL_PORT}" \
    --env "PUBLIC_BASE_URL=${PUBLIC_BASE_URL}" \
    --env "FRONTEND_URL=${PUBLIC_BASE_URL}" \
    --env "COOKIE_SECURE=${COOKIE_SECURE:-false}" \
    --env "SESSION_SECRET=${SESSION_SECRET:-change-me-infra-dev}" \
    --env "AUTH_PROVIDER=${AUTH_PROVIDER:-mock}" \
    --env "MOCK_USER_EMAIL=${MOCK_USER_EMAIL:-hwax.demo@samsung.com}" \
    --env "MOCK_USER_NAME=${MOCK_USER_NAME:-HWAX Demo User}" \
    --env "MOCK_USER_GROUPS=${MOCK_USER_GROUPS:-portal-admin}" \
    --env "ROUTES_PATH=${ROUTES_PATH}" \
    --env "SAML_MOCK_IDP_ENABLED=false" \
    "$PORTAL_SIF" "$INST_PORTAL"
fi

echo "→ waiting for portal…"
ok=0
for _ in $(seq 1 30); do
  if curl -fsS -m 2 "http://127.0.0.1:${PORTAL_PORT}/health" >/dev/null 2>&1; then
    ok=1; echo "✓ portal ready"; break
  fi
  sleep 1
done
[ "$ok" = 1 ] || echo "  ⚠ portal not ready in 30s — check: $APPTAINER instance list / logs $INST_PORTAL"

# 4. nginx (path-routing)
if instance_running "$INST_NGINX"; then
  echo "✓ $INST_NGINX already running"
else
  echo "→ start $INST_NGINX (:$HTTP_PORT)"
  "$APPTAINER" instance start --bind "$REPO_ROOT:/workspace" "$NGINX_SIF" "$INST_NGINX"
fi

echo
echo "✓ HWAX up"
echo "  portal (direct) : http://127.0.0.1:${PORTAL_PORT}"
echo "  via nginx       : http://127.0.0.1:${HTTP_PORT}   (public: ${PUBLIC_BASE_URL})"
echo "  routes          : edit backend/${ROUTES_PATH} → ./infra/scripts/restart.sh"
