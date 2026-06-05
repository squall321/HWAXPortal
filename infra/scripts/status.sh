#!/usr/bin/env bash
# Show HWAX instances + healthchecks.
set -euo pipefail
. "$(dirname "$0")/_common.sh"
require_apptainer

echo "═════ Apptainer instances ═════"
"$APPTAINER" instance list 2>/dev/null | grep -E "INSTANCE|hwax_" || echo "  (no hwax_* instances running)"

echo
echo "═════ Healthchecks ═════"
check() {
  local name="$1" url="$2"
  printf "  %-18s " "$name"
  if curl -fsS -m 3 "$url" >/dev/null 2>&1; then echo "✓ $url"; else echo "✗ $url"; fi
}
check "portal (direct)" "http://127.0.0.1:${PORTAL_PORT}/health"
check "nginx → portal"  "http://127.0.0.1:${HTTP_PORT}/health"

echo
echo "═════ Active path routes (routes.env) ═════"
ROUTES_FILE="$REPO_ROOT/backend/${ROUTES_PATH}"
if [ -f "$ROUTES_FILE" ]; then
  grep -vE '^\s*(#|$)' "$ROUTES_FILE" | while IFS='=' read -r id url; do
    id="$(echo "$id" | xargs)"; url="$(echo "$url" | xargs)"
    [ -n "$id" ] && [ -n "$url" ] && printf "  /%-22s → %s\n" "${id}/" "$url"
  done
  grep -qvE '^\s*(#|$)' "$ROUTES_FILE" || echo "  (none enabled — all tiles 'coming_soon')"
fi
