#!/usr/bin/env bash
# Register the Google-Drive remote for image sync — server-side fully scripted.
# Installs rclone no-sudo if missing, then registers the remote one of three ways:
#   (interactive)  paste the JSON token from `rclone authorize "drive" <id> <secret>` run on a
#                  browser machine  → writes [<remote>] into ~/.config/rclone/rclone.conf
#   --token-file=F  same, token JSON read from a file (non-interactive)
#   --rclone-conf=F  copy an entire rclone.conf you already have (e.g. scp'd from a build host)
# Then verifies, creates the Drive path, and writes HWAX_DRIVE_REMOTE into infra/.env.
#
#   ./infra/scripts/setup-drive-sync.sh
#   ./infra/scripts/setup-drive-sync.sh --remote-name=ApptainerImages --path=HWAXPortal/images
#   ./infra/scripts/setup-drive-sync.sh --rclone-conf=/path/to/rclone.conf
#   ./infra/scripts/setup-drive-sync.sh --token-file=/path/to/token.json
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$(dirname "${BASH_SOURCE[0]}")"
ENV="$REPO_ROOT/infra/.env"
CONF="${HOME}/.config/rclone/rclone.conf"

# Optional custom Google OAuth app creds (read from infra/.env — gitignored — so they're not in
# the repo). Leave unset to use rclone's built-in default client (works fine; just run
# `rclone authorize "drive"` without args). Set HWAX_GDRIVE_CLIENT_ID / _SECRET to use your own app.
[ -f "$REPO_ROOT/infra/.env" ] && { set -a; . "$REPO_ROOT/infra/.env"; set +a; }
OAUTH_CLIENT_ID="${HWAX_GDRIVE_CLIENT_ID:-}"
OAUTH_CLIENT_SECRET="${HWAX_GDRIVE_CLIENT_SECRET:-}"

REMOTE_NAME="ApptainerImages"
REMOTE_PATH="HWAXPortal/images"
TOKEN_FILE=""
CONF_SRC=""
for a in "$@"; do
  case "$a" in
    --remote-name=*) REMOTE_NAME="${a#*=}" ;;
    --path=*)        REMOTE_PATH="${a#*=}" ;;
    --remote=*)      REMOTE_NAME="${a#*=}"; REMOTE_NAME="${REMOTE_NAME%%:*}"
                     case "${a#*=}" in *:*) REMOTE_PATH="${a#*:}" ;; esac ;;
    --token-file=*)  TOKEN_FILE="${a#*=}" ;;
    --rclone-conf=*) CONF_SRC="${a#*=}" ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown arg: $a"; exit 1 ;;
  esac
done
REMOTE_PATH="${REMOTE_PATH%/}"

# ── rclone (install no-sudo if missing) ──────────────────────────────────────
"$HERE/bootstrap-rclone.sh"
RCLONE="rclone"
[ -x "$REPO_ROOT/infra/bin/rclone" ] && RCLONE="$REPO_ROOT/infra/bin/rclone"
"$RCLONE" version >/dev/null 2>&1 || { echo "✗ rclone unavailable after bootstrap"; exit 1; }

mkdir -p "$(dirname "$CONF")"; chmod 700 "$(dirname "$CONF")" 2>/dev/null || true

# ── Option A: drop in an entire rclone.conf you copied over ───────────────────
if [ -n "$CONF_SRC" ]; then
  [ -f "$CONF_SRC" ] || { echo "✗ --rclone-conf file not found: $CONF_SRC"; exit 1; }
  [ -f "$CONF" ] && cp "$CONF" "${CONF}.bak-$$"
  cp "$CONF_SRC" "$CONF"; chmod 600 "$CONF"
  echo "✓ installed rclone.conf from $CONF_SRC"
fi

# ── Register the remote if it isn't there yet ────────────────────────────────
if "$RCLONE" listremotes 2>/dev/null | grep -qx "${REMOTE_NAME}:"; then
  echo "✓ rclone remote '${REMOTE_NAME}:' already configured"
else
  # Get the token: from --token-file, else interactive paste.
  TOKEN=""
  if [ -n "$TOKEN_FILE" ]; then
    [ -f "$TOKEN_FILE" ] || { echo "✗ --token-file not found: $TOKEN_FILE"; exit 1; }
    TOKEN="$(cat "$TOKEN_FILE")"
  else
    # Use custom app creds only if provided (HWAX_GDRIVE_CLIENT_ID/_SECRET in infra/.env);
    # otherwise rclone's built-in default client.
    if [ -n "$OAUTH_CLIENT_ID" ] && [ -n "$OAUTH_CLIENT_SECRET" ]; then
      AUTH_CMD="rclone authorize \"drive\" \"$OAUTH_CLIENT_ID\" \"$OAUTH_CLIENT_SECRET\""
    else
      AUTH_CMD="rclone authorize \"drive\""
    fi
    cat <<EOF

  Register '${REMOTE_NAME}:' (headless OAuth — Google login happens on a browser machine):
  ───────────────────────────────────────────────────────────────────────────
  ① On any machine WITH a browser (your PC), with rclone installed, run:

       ${AUTH_CMD}

  ② A browser opens → log into Google → "Allow".
  ③ Copy the WHOLE JSON token it prints (one line, with the braces):
       {"access_token":"ya29...","token_type":"Bearer","refresh_token":"1//...","expiry":"..."}
  ───────────────────────────────────────────────────────────────────────────
EOF
    printf "  Paste the JSON token here + Enter: "
    read -r TOKEN
  fi
  echo "$TOKEN" | grep -q '"access_token"' \
    || { echo "✗ that doesn't look like an rclone token (no access_token field)"; exit 1; }

  [ -f "$CONF" ] && cp "$CONF" "${CONF}.bak-$$"
  {
    printf '\n[%s]\ntype = drive\nscope = drive\n' "$REMOTE_NAME"
    [ -n "$OAUTH_CLIENT_ID" ]     && printf 'client_id = %s\n' "$OAUTH_CLIENT_ID"
    [ -n "$OAUTH_CLIENT_SECRET" ] && printf 'client_secret = %s\n' "$OAUTH_CLIENT_SECRET"
    printf 'token = %s\nteam_drive =\n' "$TOKEN"
  } >> "$CONF"
  chmod 600 "$CONF"
  echo "✓ wrote remote '${REMOTE_NAME}:' → $CONF"
fi

# ── Verify + ensure the path exists ──────────────────────────────────────────
"$RCLONE" lsd "${REMOTE_NAME}:" >/dev/null 2>&1 \
  || { echo "✗ cannot reach '${REMOTE_NAME}:' (token expired/invalid or network). Re-run with a fresh token, or: $RCLONE config reconnect ${REMOTE_NAME}:"; exit 1; }
echo "✓ '${REMOTE_NAME}:' reachable"
if ! "$RCLONE" lsf "${REMOTE_NAME}:${REMOTE_PATH}" >/dev/null 2>&1; then
  T="$(mktemp)"; echo init > "$T"
  "$RCLONE" copy "$T" "${REMOTE_NAME}:${REMOTE_PATH}/.init/" 2>/dev/null || true
  "$RCLONE" delete "${REMOTE_NAME}:${REMOTE_PATH}/.init/" 2>/dev/null || true
  rm -f "$T"
fi

# ── Write infra/.env ─────────────────────────────────────────────────────────
[ -f "$ENV" ] || cp "$REPO_ROOT/infra/.env.example" "$ENV"
FULL="${REMOTE_NAME}:${REMOTE_PATH}"
if grep -qE '^HWAX_DRIVE_REMOTE=' "$ENV"; then
  sed -i "s#^HWAX_DRIVE_REMOTE=.*#HWAX_DRIVE_REMOTE=$FULL#" "$ENV"
else
  printf '\nHWAX_DRIVE_REMOTE=%s\n' "$FULL" >> "$ENV"
fi
echo "✓ infra/.env → HWAX_DRIVE_REMOTE=$FULL"
echo
echo "  push images (build host):  ./infra/scripts/images-to-drive.sh"
echo "  pull images (any server):  ./infra/scripts/images-from-drive.sh"
