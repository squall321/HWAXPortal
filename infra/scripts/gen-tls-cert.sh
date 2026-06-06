#!/usr/bin/env bash
# Generate a self-signed TLS cert for the portal (no sudo) → infra/tls/hwax.{crt,key}.
# Browsers warn until you drop in the corp-issued cert at the same paths (then restart).
#   ./infra/scripts/gen-tls-cert.sh           # skip if present
#   ./infra/scripts/gen-tls-cert.sh --force   # regenerate
set -euo pipefail
. "$(dirname "$0")/_common.sh"

command -v openssl >/dev/null 2>&1 || { echo "✗ openssl not found (apt-get install openssl)"; exit 1; }

TLS_DIR="$REPO_ROOT/infra/tls"
CRT="$REPO_ROOT/${TLS_CERT_PATH:-infra/tls/hwax.crt}"
KEY="$REPO_ROOT/${TLS_KEY_PATH:-infra/tls/hwax.key}"
NAME="${TLS_SERVER_NAME:-hwax.sec.samsung.net}"
FORCE=0; [ "${1:-}" = "--force" ] && FORCE=1
mkdir -p "$(dirname "$CRT")" "$(dirname "$KEY")"

if [ -f "$CRT" ] && [ -f "$KEY" ] && [ "$FORCE" -eq 0 ]; then
  echo "✓ TLS cert exists: $CRT  (--force to regenerate)"
  exit 0
fi

echo "→ generating self-signed cert for '$NAME' (+ localhost)…"
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout "$KEY" -out "$CRT" \
  -subj "/CN=${NAME}/O=HWAX Portal" \
  -addext "subjectAltName=DNS:${NAME},DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
chmod 600 "$KEY"; chmod 644 "$CRT"
echo "✓ wrote:"
echo "    cert: $CRT"
echo "    key : $KEY"
echo "  (self-signed → browser warning. Replace both files with the corp cert later, then restart.)"
