#!/usr/bin/env bash
# MCP 앱이 게이트웨이까지 실제로 등록됐는지 5단계로 짚어 어디서 막혔는지 알려주는 점검 스크립트.
#
# "배치로 띄우면 바로 등록된다"는 사실이 아니다. 등록은 아래 체인을 전부 통과해야 성립하고,
# 각 단계마다 게이트와 지연이 있다. 이 스크립트는 그 체인을 순서대로 확인한다.
#
#   1) 매니페스트   mcp.expose:true + id            (선언이 없으면 애초에 후보가 아니다)
#   2) 기동 상태    var/integration_state/<id>.json (한 번도 안 뜬 앱은 레지스트리가 뺀다)
#   3) 앱 실서빙    base + /apps/<id><path>          (프로세스가 실제로 응답하는가)
#   4) 레지스트리   GET /api/v1/mcp/servers          (HEAX Hub 가 노출하는가 — 즉시 반영)
#   5) 게이트웨이   GET /tools-map                   (합류했는가 — 최대 60초 지연)
#
# 게이트웨이까지 붙어도 포털 챗의 앱 목록·도구맵은 300초 TTL 캐시라 최대 5분 더 걸린다.
# 즉 최악의 전파 시간은 대략 6분이다.
#
# 사용법
#   check-mcp-registration.sh                # 등록된 모든 heax MCP 앱 요약
#   check-mcp-registration.sh <app_id>       # 한 앱을 5단계로 상세 점검
#   check-mcp-registration.sh --watch <id>   # 등록될 때까지 추적(최대 8분)
#
# 토큰은 스크립트에 넣지 않는다 — 게이트웨이 설정 파일(600)에서 읽는다.
set -uo pipefail

GW_CONFIG="${GATEWAY_CONFIG:-/home/koopark/claude/HWAXMcpGateway/gateway_config.json}"
GW_HTTP="${GW_HTTP:-http://127.0.0.1:9110}"
HUB_ROOT="${HUB_ROOT:-/home/koopark/claude/HEAXHub}"
REVIVE_S="${GATEWAY_REVIVE_INTERVAL:-60}"   # 게이트웨이 재폴링 주기(기본 60초)
AGENT_CACHE_S=300                            # agent-server 의 /tools-map·apps 캐시 TTL

C_OK=$'\033[32m'; C_NG=$'\033[31m'; C_WARN=$'\033[33m'; C_DIM=$'\033[2m'; C_0=$'\033[0m'
[ -t 1 ] || { C_OK=; C_NG=; C_WARN=; C_DIM=; C_0=; }

need() { command -v "$1" >/dev/null || { echo "필요한 명령이 없습니다: $1" >&2; exit 2; }; }
need curl; need jq

[ -r "$GW_CONFIG" ] || { echo "게이트웨이 설정을 읽을 수 없습니다: $GW_CONFIG" >&2; exit 2; }
SERVERS_URL=$(jq -r '.heax_registry.servers_url // empty' "$GW_CONFIG")
HEAX_BASE=$(jq -r '.heax_registry.base // empty' "$GW_CONFIG")
HEAX_TOKEN=$(jq -r '.heax_registry.token // empty' "$GW_CONFIG")
[ -n "$SERVERS_URL" ] || { echo "gateway_config.json 에 heax_registry.servers_url 이 없습니다" >&2; exit 2; }

ok()   { printf '  %s✔%s %s\n' "$C_OK" "$C_0" "$1"; }
ng()   { printf '  %s✘%s %s\n' "$C_NG" "$C_0" "$1"; }
warn() { printf '  %s!%s %s\n' "$C_WARN" "$C_0" "$1"; }
dim()  { printf '    %s%s%s\n' "$C_DIM" "$1" "$C_0"; }

# 레지스트리 응답을 한 번만 받아 재사용한다(단계마다 다시 치면 그 사이 상태가 바뀐다).
fetch_registry() {
  curl -sS --max-time 10 -H "Authorization: Bearer ${HEAX_TOKEN}" "$SERVERS_URL" 2>/dev/null
}
fetch_toolsmap() {
  curl -sS --max-time 10 "${GW_HTTP}/tools-map" 2>/dev/null
}

summary() {
  local reg tm
  reg=$(fetch_registry); tm=$(fetch_toolsmap)
  if ! jq -e . >/dev/null 2>&1 <<<"$reg"; then
    ng "레지스트리 응답이 JSON 이 아닙니다 — HEAX Hub 가 떠 있는지, PAT 가 유효한지 확인하세요"
    dim "$SERVERS_URL"
    return 1
  fi
  printf '%s레지스트리(HEAX Hub)%s — 노출 중인 MCP 앱\n' "$C_DIM" "$C_0"
  jq -r '.servers[]? | "  \(.id)\t\(.name // "-")\t\(.path)"' <<<"$reg" | column -t -s $'\t'
  echo
  printf '%s게이트웨이%s — 합류한 heax 백엔드\n' "$C_DIM" "$C_0"
  if jq -e '.apps' >/dev/null 2>&1 <<<"$tm"; then
    jq -r '.apps[]? | select(.app | startswith("heax-"))
           | "  \(.app)\t도구 \(.tool_count // 0)개\t\(if .reachable then "연결됨" else "연결안됨" end)\t\(.label // "-")"' \
      <<<"$tm" | column -t -s $'\t'
  else
    ng "게이트웨이 /tools-map 을 읽지 못했습니다 (${GW_HTTP})"
  fi
  echo
  # 레지스트리엔 있는데 게이트웨이엔 없는 앱 = 전파 중이거나 연결 실패
  local missing
  missing=$(comm -23 \
    <(jq -r '.servers[]?.id' <<<"$reg" | sed 's/^/heax-/' | sort) \
    <(jq -r '.apps[]?.app' <<<"$tm" 2>/dev/null | sort))
  if [ -n "$missing" ]; then
    warn "레지스트리에 있으나 게이트웨이에 없는 앱 — 최대 ${REVIVE_S}초 후 합류하거나, 앱이 응답하지 않는 것입니다"
    while read -r m; do [ -n "$m" ] && dim "$m"; done <<<"$missing"
  fi
  # 도구 0개로 붙어 있는 앱 — '등록됨'으로 보이지만 실제로는 아무 기능도 주지 않는다.
  # 사용자에겐 앱 목록에 이름만 있고 쓸 도구가 없는 상태로 보인다.
  local dead
  dead=$(jq -r '.apps[]? | select((.app|startswith("heax-")) and ((.tool_count // 0) == 0)) | .app' <<<"$tm" 2>/dev/null)
  if [ -n "$dead" ]; then
    warn "합류했으나 도구가 0개인 앱 — MCP 프로세스가 죽었을 가능성이 높습니다"
    while read -r d; do
      [ -n "$d" ] && dim "$d   →   $(basename "$0") ${d#heax-}"
    done <<<"$dead"
  fi
}

detail() {
  local id="$1" reg tm rc=0
  printf '앱 %s%s%s 등록 체인 점검\n\n' "$C_OK" "$id" "$C_0"

  # ── 1) 매니페스트 ─────────────────────────────────────────────────────────
  printf '1) 매니페스트 선언\n'
  local mf
  mf=$(grep -rl "^[[:space:]]*id:[[:space:]]*['\"]\?${id}['\"]\?[[:space:]]*$" \
         "${HUB_ROOT}/integrations"/*/.portal/manifest.yaml 2>/dev/null | head -1)
  if [ -z "$mf" ]; then
    ng "manifest.yaml 을 찾지 못했습니다 (integrations/*/.portal/manifest.yaml 에 id: ${id} 없음)"
    dim "매니페스트의 id 가 곧 App.id 이자 상태파일 이름이자 게이트웨이 키(heax-<id>)입니다"
    rc=1
  else
    ok "매니페스트: ${mf#$HUB_ROOT/}"
    if grep -qE '^[[:space:]]*expose:[[:space:]]*true' "$mf"; then
      ok "mcp.expose: true"
    else
      ng "mcp.expose 가 true 가 아닙니다 — 선언이 없으면 레지스트리 후보가 아닙니다"
      rc=1
    fi
  fi

  # ── 2) 기동 상태 파일 ─────────────────────────────────────────────────────
  printf '\n2) 기동 이력(상태 파일)\n'
  local sf="${HUB_ROOT}/var/integration_state/${id}.json"
  if [ -f "$sf" ]; then
    local pid alive
    pid=$(jq -r '.pid // empty' "$sf" 2>/dev/null)
    ok "상태 파일 있음: var/integration_state/${id}.json"
    if [ -n "$pid" ]; then
      if kill -0 "$pid" 2>/dev/null; then alive="살아 있음"; else alive="죽어 있음"; fi
      dim "pid ${pid} — ${alive}"
      # 레지스트리는 pid 생존을 보지 않는다. 죽어 있어도 계속 노출되고 게이트웨이는 붙지 못한다.
      [ "$alive" = "죽어 있음" ] && warn "프로세스가 죽었지만 레지스트리는 계속 노출합니다(설계상 의도) — 게이트웨이는 연결에 실패합니다"
    fi
  else
    ng "상태 파일 없음 — 한 번도 기동된 적이 없어 레지스트리가 제외합니다"
    dim "배치가 launch 까지 갔는지 확인하세요. 빌드/기동 실패면 상태 파일이 생기지 않습니다"
    rc=1
  fi

  # ── 3) 앱이 실제 MCP 로 응답하는가 ────────────────────────────────────────
  # "응답이 온다"로 판정하면 안 된다. 프로세스가 죽으면 Caddy 가 같은 경로에서 앱의 정적
  # 프론트엔드를 200 으로 돌려주고, 그걸 통과시키면 '살아 있다'는 거짓 판정이 나온다
  # (실측: web_design_agents 가 /mcp 에서 text/html 200 을 반환). MCP initialize 를
  # 실제로 걸어 Mcp-Session-Id 가 오는지로 판정한다.
  printf '\n3) MCP 프로토콜 응답\n'
  local sub url hdr body status
  sub=$( [ -n "$mf" ] && sed -n '/^mcp:/,/^[^[:space:]]/p' "$mf" | grep -oP 'path:\s*\K\S+' | head -1 )
  sub="${sub:-/mcp}"
  url="${HEAX_BASE}/apps/${id}${sub}"
  hdr=$(mktemp); body=$(mktemp)
  curl -sS --max-time 8 -D"$hdr" -o "$body" -X POST \
    -H "Authorization: Bearer ${HEAX_TOKEN}" -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"check-mcp-registration","version":"1"}}}' \
    "$url" >/dev/null 2>&1
  status=$(head -1 "$hdr" | tr -d '\r')
  if grep -qi '^mcp-session-id:' "$hdr"; then
    ok "MCP 서버가 응답합니다 — ${status}"
    dim "$url"
  else
    ng "MCP 로 응답하지 않습니다 — ${status:-연결 실패}"
    dim "$url"
    if grep -qi '^content-type:.*text/html' "$hdr"; then
      dim "정적 HTML 이 돌아옵니다 — MCP 프로세스가 죽어 Caddy 가 앱 프론트엔드를 대신 서빙 중입니다"
    fi
    dim "게이트웨이는 이 백엔드에 붙어도 도구를 0개로 집계합니다"
    rc=1
  fi
  rm -f "$hdr" "$body"

  # ── 4) 레지스트리 노출 ────────────────────────────────────────────────────
  printf '\n4) HEAX Hub 레지스트리\n'
  reg=$(fetch_registry)
  if jq -e --arg i "$id" '.servers[]? | select(.id==$i)' >/dev/null 2>&1 <<<"$reg"; then
    ok "레지스트리에 노출 중"
    jq -r --arg i "$id" '.servers[]? | select(.id==$i)
        | "    name: \(.name // "-")\n    path: \(.path)\n    description: \(if (.description // "") == "" then "(없음)" else .description end)\n    allowed_groups: \(.allowed_groups | tostring)"' <<<"$reg"
    if [ "$(jq -r --arg i "$id" '[.servers[]?|select(.id==$i)|.description//""][0]' <<<"$reg")" = "" ]; then
      warn "description 이 비어 있습니다 — 앱 단위 선택 UI 에 설명이 안 보입니다"
      dim "manifest 의 mcp.description 또는 앱 description 을 채우세요"
    fi
  else
    ng "레지스트리에 없습니다"
    dim "게이트는 넷입니다 — status(beta/stable), current_version, mcp.expose, 기동 이력"
    dim "그리고 게이트웨이 PAT 의 가시성 밖이면 fail-closed 로 빠집니다"
    rc=1
  fi

  # ── 5) 게이트웨이 합류 ────────────────────────────────────────────────────
  printf '\n5) 게이트웨이 합류\n'
  tm=$(fetch_toolsmap)
  if jq -e --arg k "heax-${id}" '.apps[]? | select(.app==$k)' >/dev/null 2>&1 <<<"$tm"; then
    jq -r --arg k "heax-${id}" '.apps[]? | select(.app==$k)
        | "  합류함 — 도구 \(.tool_count // 0)개, \(if .reachable then "연결됨" else "연결안됨(재연결 대기)" end)"' <<<"$tm"
    if [ "$(jq -r --arg k "heax-${id}" '[.apps[]?|select(.app==$k)|.tool_count//0][0]' <<<"$tm")" = "0" ]; then
      warn "도구가 0개입니다 — 붙었지만 list_tools 가 비었습니다(앱이 도구를 노출하지 않음)"
      rc=1
    fi
  else
    ng "게이트웨이에 없습니다"
    dim "레지스트리에 있다면 최대 ${REVIVE_S}초 뒤 재폴링에서 합류합니다 — --watch 로 추적하세요"
    rc=1
  fi

  printf '\n%s전파 예산%s — 레지스트리 즉시 / 게이트웨이 최대 %s초 / 포털 챗 캐시 최대 %s초 (합계 약 %s분)\n' \
    "$C_DIM" "$C_0" "$REVIVE_S" "$AGENT_CACHE_S" "$(( (REVIVE_S + AGENT_CACHE_S + 59) / 60 ))"
  return $rc
}

watch_until() {
  local id="$1" deadline=$(( $(date +%s) + 480 )) n=0
  printf '앱 %s 등록을 추적합니다(최대 8분, 15초 간격). Ctrl-C 로 중단.\n\n' "$id"
  while [ "$(date +%s)" -lt "$deadline" ]; do
    n=$((n+1))
    local tm cnt
    tm=$(fetch_toolsmap)
    cnt=$(jq -r --arg k "heax-${id}" '[.apps[]?|select(.app==$k)|.tool_count//0][0] // "없음"' <<<"$tm" 2>/dev/null)
    printf '[%s] %2d회 — 게이트웨이: %s\n' "$(date +%H:%M:%S)" "$n" "$cnt"
    if [ "$cnt" != "없음" ] && [ "$cnt" != "0" ]; then
      printf '\n%s합류 확인%s — 도구 %s개\n' "$C_OK" "$C_0" "$cnt"
      printf '%s포털 챗에 보이기까지 캐시 TTL 로 최대 %s초 더 걸립니다.%s\n' "$C_DIM" "$AGENT_CACHE_S" "$C_0"
      return 0
    fi
    sleep 15
  done
  printf '\n%s8분 안에 합류하지 않았습니다%s — 상세 점검을 돌리세요: %s %s\n' \
    "$C_NG" "$C_0" "$(basename "$0")" "$id"
  return 1
}

case "${1:-}" in
  "")        summary ;;
  --watch)   [ -n "${2:-}" ] || { echo "사용법: $(basename "$0") --watch <app_id>" >&2; exit 2; }
             watch_until "$2" ;;
  -h|--help) sed -n '2,28p' "$0" | sed 's/^# \?//' ;;
  *)         detail "$1" ;;
esac
