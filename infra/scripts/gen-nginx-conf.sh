#!/usr/bin/env bash
# Generate infra/nginx/hwax.conf from the template + routes.env.
# Each `system-id=URL` line → a `location /system-id/ { proxy_pass URL/; }`.
# URLs are used as-is: localhost, another server's IP, or a domain all work.
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ROUTES_FILE="$REPO_ROOT/backend/${ROUTES_PATH}"
TMPL="$NGINX_DIR/hwax.conf.tmpl"
OUT="$NGINX_DIR/hwax.conf"
# 접근 로그 디렉터리 — nginx 는 디렉터리를 만들어 주지 않는다. conf 가 가리키는 자리를 보장.
mkdir -p "$(dirname "$NGINX_DIR")/data"

# Per-route extra directives. Most services need nothing; a few have traffic the defaults
# break. Keyed by the FULL id so a nested id (e.g. "svc/api") can differ from its parent.
#   ste — CAE decks are uploaded through this proxy. nginx's default client_max_body_size is
#         1m, so a 50MB deck would 413 before ever reaching the backend (which allows 2048m).
#         request_buffering off streams the upload instead of spooling it to disk first, which
#         is also what makes the browser's XHR progress bar track reality. buffering off keeps
#         log tails and result downloads from being held whole in nginx.
#   apps / heax-hub — heax-hub 에 등록된 앱들이 사는 경로다(/apps/<id>/, /heax-hub/ 는 허브 UI
#         이자 같은 업스트림으로 벗겨져 들어간다). 여기로 시뮬레이션 모델 파일이 올라간다 —
#         MaterialTwin 물성 원본, DynaForge K파일·메시가 수십~수백 MB 다. ste 와 사정이 같은데
#         상한만 안 걸려 있었다: nginx 기본 1m 이라 3MB 로도 413 이 났다(실측). 백엔드가 아무리
#         큰 걸 받아도 여기서 먼저 잘린다. 업로드 실패가 앱 버그로 보이는 전형적인 자리다.
loc_extras() { # $1=id
  case "$1" in
    ste|apps|heax-hub)
      cat <<'EOF'
            client_max_body_size 2048m;
            proxy_request_buffering off;
            proxy_buffering off;
            proxy_read_timeout 600s;
EOF
      ;;
  esac
}

loc_block() {  # $1=id  $2=url  (unquoted heredoc: ${} expands, \$ stays literal for nginx)
  local id="$1" url="$2"
  # X-Forwarded-Prefix = the SERVICE root prefix (first path segment of the id), so a prefix-aware
  # backend (e.g. HEAXHub's agent manifest building absolute installer/download URLs) can prepend it
  # and emit https://<host>/<id>/... rather than a prefix-less URL the portal would 404. For a nested
  # id like "mx-white-paper/api" the prefix is still the service root "/mx-white-paper".
  local svc="/${id%%/*}"
  # ⚠️ nginx inheritance: proxy_set_header is inherited from the outer level ONLY when the current
  # level declares NO proxy_set_header of its own. Declaring X-Forwarded-Prefix here therefore DROPS
  # every outer header — Host, X-Real-IP, X-Forwarded-For/-Proto/-Host, and (worst) Upgrade/
  # Connection. Measured effect: a WebSocket upgrade to /heax-hub/…/_stcore/stream came back 200
  # instead of 101 (streamlit never connects), and prefix-aware backends lost the X-Forwarded-Host
  # they use to rebuild public URLs. So re-declare the full set in every generated location.
  cat <<EOF
        location /${id}/ {
            proxy_set_header Host              \$host;
            proxy_set_header X-Real-IP         \$remote_addr;
            proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_set_header X-Forwarded-Host  \$http_host;
            proxy_set_header Upgrade           \$http_upgrade;
            proxy_set_header Connection        \$connection_upgrade;
            proxy_set_header X-Forwarded-Prefix ${svc};
$(loc_extras "${id}")
            proxy_pass ${url};
        }
EOF
  # Slashless entry point, OPT-IN per id. `location /id/` does not match a bare `/id`, so
  # without this the request falls to the portal catch-all and returns the portal SPA with
  # HTTP 200 — the user sees the portal home instead of the service, with nothing signalling why.
  #
  # Not enabled for everyone on purpose: a 301 changes what already-working clients see, and
  # some turn a POST /id into GET /id/ when they follow it. Existing services have shipped
  # without it, so opting them in is their owners' call, not a side effect of adding STE.
  # To enable another service, add its id to this list.
  case " ste " in
    *" $id "*) printf '        location = /%s { return 301 /%s/; }\n' "$id" "$id" ;;
  esac
}

# 박스별 오버레이 — routes.env 는 git 추적이라 dev·cae00 이 같은 파일을 쓴다. 그런데 ste 처럼
# 박스마다 주소가 다른 항목이 있고, deploy 의 git_update 가 `git reset --hard` 를 걸어 로컬
# 수정을 매번 지운다(stash 로 치워진다). 그래서 손으로 고칠 방법이 아예 없었다.
# routes.local.env(gitignore)가 있으면 같은 키를 덮어쓴다 — 없는 키는 base 그대로다.
ROUTES_LOCAL="$REPO_ROOT/backend/config/routes.local.env"
ROUTES_MERGED="$ROUTES_FILE"
if [ -f "$ROUTES_LOCAL" ]; then
  _merged="$(mktemp)"; trap 'rm -f "$_merged"' EXIT
  # local 이 정의한 키 목록(주석·빈 줄 제외)
  _lkeys="$(sed -n 's/^[[:space:]]*\([A-Za-z0-9_/-][A-Za-z0-9_/-]*\)[[:space:]]*=.*/\1/p' "$ROUTES_LOCAL")"
  # base 에서 그 키들만 빼고 복사한 뒤 local 을 덧붙인다(= local 이 이긴다).
  # xargs 는 쓰지 않는다 — 주석 줄의 홑따옴표에 걸려 죽는다(실측).
  while IFS= read -r _l || [ -n "$_l" ]; do
    _k="${_l%%=*}"; _k="${_k#"${_k%%[![:space:]]*}"}"; _k="${_k%"${_k##*[![:space:]]}"}"
    case "$_l" in ''|\#*) printf '%s\n' "$_l"; continue ;; esac
    if printf '%s\n' "$_lkeys" | grep -qxF "$_k"; then continue; fi
    printf '%s\n' "$_l"
  done < "$ROUTES_FILE" > "$_merged"
  cat "$ROUTES_LOCAL" >> "$_merged"
  ROUTES_MERGED="$_merged"
  echo "  · routes.local.env 오버레이: $(printf '%s\n' "$_lkeys" | grep -c .)개 키 재정의"
fi

# STE 주소는 박스마다 다르다. 오버레이가 없는데 base 에 (사설망) ste 주소가 살아 있으면 그 박스는
# 남의 dev VM 주소를 물려받아 죽은 upstream 라우트가 생긴다(cae00 이 정확히 그 상태였다). 경고한다.
if [ ! -f "$ROUTES_LOCAL" ]; then
  _ste_host="$(sed -n 's|^[[:space:]]*ste=[[:space:]]*http://\([^:/]*\).*|\1|p' "$ROUTES_MERGED" 2>/dev/null | head -1)"
  case "$_ste_host" in
    10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*)
      echo "  ⚠ routes.local.env 없음 + base ste= 가 사설망 주소($_ste_host) — 이 박스 전용 STE 주소를 routes.local.env 에 두거나 base 의 ste= 를 비활성화하세요(안 그러면 죽은 /ste/ upstream 이 생깁니다)." >&2 ;;
  esac
fi

locations=""
count=0
if [ -f "$ROUTES_MERGED" ]; then
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
  done < "$ROUTES_MERGED"
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
