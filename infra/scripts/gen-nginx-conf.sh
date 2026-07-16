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
  # X-Forwarded-Prefix = the SERVICE root prefix (first path segment of the id), so a prefix-aware
  # backend (e.g. HEAXHub's agent manifest building absolute installer/download URLs) can prepend it
  # and emit https://<host>/<id>/... rather than a prefix-less URL the portal would 404. For a nested
  # id like "mx-white-paper/api" the prefix is still the service root "/mx-white-paper".
  local svc="/${id%%/*}"
  cat <<EOF
        location /${id}/ {
            proxy_set_header X-Forwarded-Prefix ${svc};
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
    # proxy_pass semantics: a trailing-slash/path URI makes nginx STRIP the /<id>/ prefix; a bare
    # host PASSES it through. Our proxied services all serve at their root (Caddy / FastAPI / `serve`)
    # and bake the base into their assets, so we always want STRIP. Normalize: if the URL is just a
    # host with NO path (e.g. http://h:5173), append "/" so the prefix is stripped — regardless of
    # whether routes.env had the slash. A URL that already has a path (…/api/, …/dashboard/) is left
    # as-is (it maps /<id>/ → that path).
    case "$url" in
      http://*/*|https://*/*) : ;;                 # already has a path → leave as-is
      http://*|https://*)     url="${url%/}/" ;;    # bare host → force trailing slash (strip)
    esac
    locations="${locations}$(loc_block "$id" "$url")"$'\n'
    count=$((count + 1))
  done < "$ROUTES_FILE"
fi

# Streaming locations (chat SSE + MCP streamable-http). The HTTP server has these hardcoded in
# the template; the TLS server (built here) MUST carry the same, or /agent (chat) and /mcp-gw
# (personal-Claude MCP) would fall through to the buffered catch-all over HTTPS. Keep in sync
# with hwax.conf.tmpl. proxy_pass with a trailing slash STRIPs the /<loc>/ prefix.
stream_locations="$(cat <<'EOF'
        location /agent/ {
            proxy_pass http://127.0.0.1:{{PORTAL_PORT}};
            proxy_buffering off; proxy_cache off; gzip off;
            proxy_read_timeout 1h; proxy_connect_timeout 300s;
        }
        location /mcp-gw/ {
            proxy_pass http://127.0.0.1:9110/;
            proxy_buffering off; proxy_cache off; gzip off;
            proxy_read_timeout 1h; proxy_connect_timeout 300s;
        }
EOF
)"

# Build the optional TLS server block (same locations + the cert, when ENABLE_TLS=true).
# Cert/key are under the repo, which is bind-mounted at /workspace inside the nginx container.
tls_server=""
if [ "${ENABLE_TLS:-false}" = "true" ]; then
  CERT_C="/workspace/${TLS_CERT_PATH:-infra/tls/hwax.crt}"
  KEY_C="/workspace/${TLS_KEY_PATH:-infra/tls/hwax.key}"
  tls_server="$(cat <<EOF

    # HTTPS — main entry. Self-signed until the corp cert is dropped in at the same paths.
    server {
        listen {{HTTPS_PORT}} ssl;
        server_name {{TLS_SERVER_NAME}};
        ssl_certificate     ${CERT_C};
        ssl_certificate_key ${KEY_C};
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_session_cache shared:SSL:4m;

        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

${locations}${stream_locations}        location / {
            proxy_pass http://127.0.0.1:{{PORTAL_PORT}};
        }
    }
EOF
)"
fi

# Assemble: inject {{LOCATIONS}} (HTTP server) → inject {{TLS_SERVER}} → substitute the tokens.
TMP1="$(mktemp)"; trap 'rm -f "$TMP1"' EXIT
{ sed '/{{LOCATIONS}}/,$d' "$TMPL"; printf '%s' "$locations"; sed '1,/{{LOCATIONS}}/d' "$TMPL"; } > "$TMP1"
{ sed '/{{TLS_SERVER}}/,$d' "$TMP1"; printf '%s' "$tls_server"; sed '1,/{{TLS_SERVER}}/d' "$TMP1"; } \
  | sed -e "s/{{HTTP_PORT}}/${HTTP_PORT}/g" \
        -e "s/{{PORTAL_PORT}}/${PORTAL_PORT}/g" \
        -e "s/{{HTTPS_PORT}}/${HTTPS_PORT:-443}/g" \
        -e "s/{{TLS_SERVER_NAME}}/${TLS_SERVER_NAME:-_}/g" > "$OUT"

tls_note=""; [ "${ENABLE_TLS:-false}" = "true" ] && tls_note=" + TLS :${HTTPS_PORT:-443}"
echo "✓ generated $OUT  (routes file: backend/${ROUTES_PATH}, ${count} system route(s)${tls_note})"
