#!/usr/bin/env bash
# Generate infra/nginx/hwax.conf from the template + routes.env.
# Each `system-id=URL` line → a `location /system-id/ { proxy_pass URL/; }`.
# URLs are used as-is: localhost, another server's IP, or a domain all work.
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ROUTES_FILE="$REPO_ROOT/backend/${ROUTES_PATH}"
TMPL="$NGINX_DIR/hwax.conf.tmpl"
OUT="$NGINX_DIR/hwax.conf"

loc_block() {  # $1=id  $2=url  (unquoted heredoc: ${} expands, \$ stays literal for nginx)
  local id="$1" url="$2"
  cat <<EOF
        location /${id}/ {
            proxy_pass ${url};
        }
EOF
}

locations=""
count=0
if [ -f "$ROUTES_FILE" ]; then
  while IFS= read -r raw || [ -n "$raw" ]; do
    line="$(printf '%s' "$raw" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    case "$line" in ''|\#*) continue ;; esac
    case "$line" in *=*) ;; *) continue ;; esac
    id="$(printf '%s' "${line%%=*}" | xargs)"
    url="$(printf '%s' "${line#*=}" | xargs)"
    [ -n "$id" ] && [ -n "$url" ] || continue
    url="${url%/}/"   # trailing slash → nginx strips the /id/ prefix when proxying
    locations="${locations}$(loc_block "$id" "$url")"$'\n'
    count=$((count + 1))
  done < "$ROUTES_FILE"
fi

# Assemble: template up to {{LOCATIONS}} + generated blocks + template after, then sub ports.
{
  sed '/{{LOCATIONS}}/,$d' "$TMPL"
  printf '%s' "$locations"
  sed '1,/{{LOCATIONS}}/d' "$TMPL"
} | sed -e "s/{{HTTP_PORT}}/${HTTP_PORT}/g" -e "s/{{PORTAL_PORT}}/${PORTAL_PORT}/g" > "$OUT"

echo "✓ generated $OUT  (routes file: backend/${ROUTES_PATH}, ${count} system route(s))"
