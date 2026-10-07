#!/usr/bin/env bash
# Start the HWAX stack: portal + nginx as Apptainer instances (host network, rootless).
# Order: build images → build SPA (host) → generate nginx conf → portal → nginx.
set -euo pipefail
# Rootless apptainer derives the cgroup/instance owner from XDG_RUNTIME_DIR; on bare SSH sessions
# it can be unset, which surfaces as "could not detect the OwnerUID". Provide a sane default.
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
export XDG_RUNTIME_DIR

# Ensure apptainer exists (no-op if present; downloads/extracts it no-sudo otherwise).
# Runs BEFORE _common.sh so the freshly-extracted binary is picked up.
"$(dirname "$0")/bootstrap.sh"
. "$(dirname "$0")/_common.sh"
require_apptainer

"$(dirname "$0")/build.sh"

# 1. SPA must be present (built ONLINE, shipped via Drive). Skip if dist already there.
# On cae00 (corp TLS-intercept: npm unreachable) NEVER build here — pull the dist instead.
if [ ! -f "$REPO_ROOT/frontend/dist/index.html" ]; then
  if [ "${HWAX_NO_BUILD:-0}" != "1" ] && command -v pnpm >/dev/null 2>&1; then
    echo "→ building SPA (frontend/dist)…"
    ( cd "$REPO_ROOT/frontend" && pnpm install --frozen-lockfile=false && pnpm build ) \
      > "$LOG_DIR/spa-build.log" 2>&1 \
      || { echo "✗ SPA build failed (see $LOG_DIR/spa-build.log)"; exit 1; }
  else
    echo "✗ frontend/dist missing. Don't build on a corp-network server — fetch the prebuilt SPA"
    echo "  (built once on a machine that can reach npm, shipped via Google Drive):"
    echo "    ./infra/scripts/images-from-drive.sh    # pulls frontend/dist (+ the .sif images)"
    echo "  or copy frontend/dist here manually, then re-run start.sh."
    exit 1
  fi
fi
echo "✓ SPA ready (frontend/dist)"

# 2. Generate nginx conf from routes.env
"$(dirname "$0")/gen-nginx-conf.sh"

# 2b. 세션 서명 키 — 비었거나 공개됐거나 짧으면 새로 만들어 infra/.env 에 **저장**한다(재기동에도 유지).
# ⚠ infra/.env.example 을 복사한 그대로인 박스가 GitHub 에 공개된 키(change-me-infra-dev)로 세션에
#   서명하고 있었다(2026-09-16 dev 실측). 이 키를 알면 아무 사용자·관리자로 로그인 토큰을 위조한다.
#   예전엔 비어 있으면 그 공개 값으로 **조용히** 떴다. 포털도 이제 이런 키로는 기동을 거부한다
#   (backend/app/config.py startup_problems — 공개값 목록은 그쪽 PUBLIC_SESSION_SECRETS 와 같아야 한다).
_ss="${SESSION_SECRET:-}"
case "$_ss" in change-me-dev-only|change-me-infra-dev|REPLACE_WITH_openssl_rand_hex_32|@GENERATE_HEX32@) _ss="" ;; esac
if [ "${#_ss}" -lt 32 ]; then
  SESSION_SECRET="$(openssl rand -hex 32 2>/dev/null || od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  export SESSION_SECRET
  if grep -q '^SESSION_SECRET=' "$REPO_ROOT/infra/.env"; then
    sed -i "s|^SESSION_SECRET=.*|SESSION_SECRET=${SESSION_SECRET}|" "$REPO_ROOT/infra/.env"
  else
    printf 'SESSION_SECRET=%s\n' "$SESSION_SECRET" >> "$REPO_ROOT/infra/.env"
  fi
  chmod 600 "$REPO_ROOT/infra/.env"   # 비밀이 든 파일이다 — 644 였다
  echo "⚠ SESSION_SECRET 이 비었거나 공개된 값이라 새 키를 만들어 infra/.env 에 저장했다 — 로그인은 다시 해야 한다"
  if instance_running "$INST_PORTAL"; then
    echo "  ⚠ 포털은 아직 옛 키로 떠 있다 — 재기동해야 새 키가 든다: apptainer instance stop $INST_PORTAL && ./infra/scripts/start.sh"
  fi
fi

# 2c. ste 자격 중계 시크릿 — **없으면 만들어 infra/.env 에 저장한다**(SESSION_SECRET 과 같은 방식).
#
# 왜 만들어도 되나 — 이 값은 바깥이 정해 주는 것이 아니라 **우리 두 서비스(포털·ste) 사이에서만
# 쓰는 난수**다. 그런 값은 비워 두는 것보다 만들어 두는 편이 낫다. 비어 있으면 기능이 조용히
# 꺼지고(ste 는 404 로 답한다) 아무도 그 사실을 모른다.
#
# ⚠ 다만 **양쪽이 같아야 한다.** 그래서 여기서 만든 값을 ste 헤드노드로 옮기는 일까지가 한 벌이다
#   — cae00 에서 `SmartTwinExplorer/deploy/refresh-code.sh` 가 그 값을 헤드 .env 에 넣는다.
#   포털이 임의로 새 값을 만들어 덮으면 그 짝이 어긋나므로, **있으면 절대 건드리지 않는다.**
if [ -z "${STE_SSO_SECRET:-}" ]; then
  STE_SSO_SECRET="$(openssl rand -hex 32 2>/dev/null || od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  export STE_SSO_SECRET
  if grep -q '^STE_SSO_SECRET=' "$REPO_ROOT/infra/.env"; then
    sed -i "s|^STE_SSO_SECRET=.*|STE_SSO_SECRET=${STE_SSO_SECRET}|" "$REPO_ROOT/infra/.env"
  else
    printf 'STE_SSO_SECRET=%s\n' "$STE_SSO_SECRET" >> "$REPO_ROOT/infra/.env"
  fi
  chmod 600 "$REPO_ROOT/infra/.env"
  echo "· STE_SSO_SECRET 이 없어 새로 만들어 infra/.env 에 저장했다"
  echo "  → ste 헤드노드에도 **같은 값**이 있어야 한다: (cae00) SmartTwinExplorer/deploy/refresh-code.sh"
fi

# 2d. RA·TestScope 사람별 위임 비밀(RA_SSO_SECRET·TESTSCOPE_SSO_SECRET, docs/sso-delegation) — **만들지 않는다**(2c 와 다른 점).
#   ste 는 우리가 같은 값을 헤드에 심지만 RA 는 남의 서버라 심을 수 없다. 그런데 이 박스에 비밀이 먼저 생기면
#   게이트웨이가 RA 를 사람별 위임으로만 불러, RA 쪽이 준비되기 전의 호출이 **전부 거부된다**. RA 담당이 켠 뒤
#   사람이 infra/.env 에 같은 값을 넣는다. 포털 프로세스도 쓴다(PPT 가져오기) — 아래 --env 로 넘긴다.
#   TestScope 도 같다(TESTSCOPE_SSO_SECRET — RA 와 다른 값, 그쪽 HEAX_SSO_SECRET 과 같은 값). 비면 종전 '토큰 등록', 있으면 위임.
#   포털은 TestScope 를 이 비밀로 부르지 않는다 — '외부 연결' 화면의 갈래(testscope_mode)를 정하는 데만 쓴다(그래서 넘긴다).

# 3. Portal (single-origin: serves SPA + API). All config via --env (overrides backend/.env).
if instance_running "$INST_PORTAL"; then
  echo "✓ $INST_PORTAL already running"
else
  echo "→ start $INST_PORTAL (:$PORTAL_PORT)"
  # 업로드 스테이징 — 호스트 영속 경로를 컨테이너 /var/upload-staging 에 바인드.
  # 파일은 여기 잠깐 머물다 확정 후·TTL 후 삭제된다(레포 안에 두지 않는다).
  STAGING_HOST="${HWAX_UPLOAD_STAGING:-$HOME/.hwax/upload-staging}"
  mkdir -p "$STAGING_HOST"
  # /data 레지스트리 바인드(docs/data-migration D9) — 컨테이너는 호스트 /data 를 못 본다(실측). 대상 디렉터리가
  # **존재하면** 동일경로로 바인드한다(env 조건 없이 — 이관 도구가 디렉터리를 만든 뒤 재기동해 가시성을 확인한다).
  # 없으면 바인드 0개·env 0개 = 종전과 동일. 레지스트리가 주입한 경로 env 는 있을 때만 컨테이너에 전달.
  DATA_BINDS=(); DATA_ENVS=()
  _DR="${HWAX_DATA_ROOT:-/data}"; case "$_DR" in /*) ;; *) _DR=/data ;; esac   # 상대값('data')이면 apptainer 가 --bind 를 거부해 기동 자체가 죽는다(cae00 실사고)
  for d in "$_DR/svc/portal" "$_DR/hwax/secrets/portal" "$_DR/delib-runs"; do
    [ -d "$d" ] && DATA_BINDS+=(--bind "$d:$d")
  done
  for k in USER_STORE_PATH CONV_STORE_PATH TOKEN_STORE_PATH AGENT_AUDIT_LOG_PATH JWT_KEYS_DIR DELIB_ARCHIVE_ROOT \
           PROCEDURES_STORE_PATH PROCEDURES_ARTIFACT_ROOT; do
    [ -n "${!k:-}" ] && DATA_ENVS+=(--env "$k=${!k}")
  done
  # SAML_* 는 **명시해서** 넘긴다 — 호스트 env 상속에만 기대면 --cleanenv 나 다른 기동 경로에서 운영 SAML 설정이 통째로
  # 코드 기본값(mock IdP 메타데이터·entityId .../sp·추적 sp.crt)으로 조용히 되돌아간다(4차 변경 요청 §4(2)).
  # SAML_MOCK_IDP_ENABLED 는 아래에서 false 로 고정하므로 뺀다.
  SAML_ENVS=()
  for k in $(compgen -e | grep '^SAML_' || true); do
    [ "$k" = SAML_MOCK_IDP_ENABLED ] || SAML_ENVS+=(--env "$k=${!k}")
  done
  # 신원·권한 설정도 **명시해서** 넘긴다 — 위 SAML 과 같은 이유다(8·9·10차 요청 #1·#5). 접두가 SAML_ 이 아니라 위 순회에 걸리지 않는다.
  # 상속이 끊기면 고정 관리자(PORTAL_ADMIN_EMAILS)가 조용히 일반 사용자가 되고 SSO 기본 소속(SSO_DEFAULT_AFFILIATION)이 조용히 꺼진다 —
  # infra/.env 에는 값이 적혀 있어 켜진 줄 안다. **값이 있을 때만** 넘긴다(위 DATA_ENVS 와 같다): `--env` 는 backend/.env 를 이기므로
  # 빈 값을 명시하면 그 파일에 적어 둔 값까지 덮어 끈다.
  IDENT_ENVS=()
  for k in PORTAL_ADMIN_EMAILS SSO_DEFAULT_AFFILIATION; do
    [ -n "${!k:-}" ] && IDENT_ENVS+=(--env "$k=${!k}")
  done
  # NO_PROXY 도 **명시해서** 넘긴다 — 위 SAML 과 같은 이유다(9차 변경 요청 §4-(5)). 상속이 끊기면 포털의 RA·TestScope 호출이 사내
  # 프록시를 타고 상대의 IP 허용목록에 걸린다(게이트웨이는 그 모양으로 사람별 위임이 403 이었다 — 2026-10-03 실측).
  # 두 철자를 **합쳐**(중복 없이) 같은 값으로 넘긴다 — 대문자만 읽어 넘기면 소문자(no_proxy)만 둔 박스에서 빈 값이 넘어가고,
  # apptainer 는 명시한 값이 있으면 호스트 값을 물려주지 않아(실측 1.3.6) 있던 우회까지 지운다.
  # APPTAINERENV_NO_PROXY 로 컨테이너용 값을 따로 주던 박스도 합친다 — apptainer 는 `--env` > `APPTAINERENV_*` > 호스트 env 순이라
  # (실측 1.3.6) 합치지 않으면 여기서 명시한 값이 그 박스의 값을 조용히 덮는다.
  # read -a 로 쪼갠다 — 따옴표 없는 for 는 `*`(전부 우회)를 현재 디렉터리의 파일 이름으로 푼다.
  # RA_HOST·ARP_HOST(infra/.env — _common.sh 가 소싱했다)도 여기서 더한다. update-all 은 1g 에서 더해 물려주지만, restart.sh·부팅
  # 유닛으로 띄운 포털은 그 export 를 못 받는다 — 운영자 셸에 두 주소가 없으면 RA 호출이 다시 프록시를 탄다(9차 요청 §4-(2)).
  _np=""
  IFS=', ' read -ra _np_parts <<<"${APPTAINERENV_NO_PROXY:-},${APPTAINERENV_no_proxy:-},${NO_PROXY:-},${no_proxy:-},${RA_HOST:-},${ARP_HOST:-}"
  for _h in ${_np_parts[@]+"${_np_parts[@]}"}; do
    [ -n "$_h" ] || continue
    case ",$_np," in *",$_h,"*) ;; *) _np="${_np:+$_np,}$_h" ;; esac
  done
  "$APPTAINER" instance start \
    ${DATA_BINDS[@]+"${DATA_BINDS[@]}"} ${DATA_ENVS[@]+"${DATA_ENVS[@]}"} ${SAML_ENVS[@]+"${SAML_ENVS[@]}"} \
    ${IDENT_ENVS[@]+"${IDENT_ENVS[@]}"} \
    --bind "$REPO_ROOT:/workspace" \
    --bind "$STAGING_HOST:/var/upload-staging" \
    --env "UPLOAD_STAGING_DIR=/var/upload-staging" \
    `# 같은 스테이징의 호스트 경로 — 다른 컨테이너(StepForge)에 파일을 넘길 때 필요하다.` \
    `# MCP upload_step/intake 는 "서버가 읽을 수 있는 절대경로"를 받는데, 컨테이너 경로를` \
    `# 그대로 주면 상대는 못 읽는다. apptainer 가 $HOME 을 자동 마운트해 호스트 경로는` \
    `# 양쪽에서 같게 보인다(heax_app_step_forge 인스턴스에서 실측 확인, 2026-09-01).` \
    --env "UPLOAD_STAGING_HOST_DIR=$STAGING_HOST" \
    --env "APP_ENV=${APP_ENV:-prod}" \
    --env "SERVE_FRONTEND=true" \
    --env "JWT_AUTOGEN_KEYS=true" \
    --env "FRONTEND_DIST=../frontend/dist" \
    --env "PORT=${PORTAL_PORT}" \
    --env "PUBLIC_BASE_URL=${PUBLIC_BASE_URL}" \
    --env "FRONTEND_URL=${PUBLIC_BASE_URL}" \
    --env "COOKIE_SECURE=${COOKIE_SECURE:-false}" \
    --env "SESSION_SECRET=${SESSION_SECRET}" \
    --env "STE_SSO_SECRET=${STE_SSO_SECRET:-}" \
    --env "RA_SSO_SECRET=${RA_SSO_SECRET:-}" \
    --env "TESTSCOPE_SSO_SECRET=${TESTSCOPE_SSO_SECRET:-}" \
    --env "AUTH_PROVIDER=${AUTH_PROVIDER:-mock}" \
    --env "MOCK_USER_EMAIL=${MOCK_USER_EMAIL:-hwax.demo@samsung.com}" \
    --env "MOCK_USER_NAME=${MOCK_USER_NAME:-HWAX Demo User}" \
    --env "MOCK_USER_GROUPS=${MOCK_USER_GROUPS:-portal-admin}" \
    --env "ROUTES_PATH=${ROUTES_PATH}" \
    --env "NO_PROXY=${_np}" \
    --env "no_proxy=${_np}" \
    --env "SAML_MOCK_IDP_ENABLED=false" \
    "$PORTAL_SIF" "$INST_PORTAL"
fi

# 안 뜬 이유를 배포 출력에 바로 보인다 — 종전엔 "로그를 보라" 로 끝나 사람이 로그 위치를 찾아야 했고, deploy-all 에는
# 'portal failed (see above)' 한 줄만 남았다(SAML_ACS_PATH 오입력으로 기동 거부된 cae00 2026-09-29).
# apptainer 인스턴스 로그: ~/.apptainer/instances/logs/<호스트>/<사용자>/<인스턴스>.err
_instance_log_tail() {  # $1=인스턴스 이름 $2=줄 수(기본 25)
  local f
  f="$(ls -t "$HOME"/.apptainer/instances/logs/*/"$(id -un)"/"$1".err 2>/dev/null | head -1 || true)"
  if [ -n "$f" ] && [ -s "$f" ]; then
    echo "    ── $f 끝 ${2:-25}줄 ──"
    tail -n "${2:-25}" "$f" | sed 's/^/    /'
  else
    echo "    (인스턴스 로그를 못 찾았다: ~/.apptainer/instances/logs/*/$(id -un)/$1.err)"
  fi
}

echo "→ waiting for portal…"
ok=0
for _ in $(seq 1 30); do
  if curl -fsS -m 2 "http://127.0.0.1:${PORTAL_PORT}/health" >/dev/null 2>&1; then
    ok=1; echo "✓ portal ready"; break
  fi
  sleep 1
done
[ "$ok" = 1 ] || { echo "  ⚠ portal not ready in 30s — check: $APPTAINER instance list / logs $INST_PORTAL"
                   _instance_log_tail "$INST_PORTAL" 25; }

# 4. nginx (path-routing). When TLS is on: ensure the cert exists and that :HTTPS_PORT is
#    bindable rootless (else print the one-time sudo hint instead of a cryptic nginx failure).
if [ "${ENABLE_TLS:-false}" = "true" ]; then
  [ -f "$REPO_ROOT/${TLS_CERT_PATH:-infra/tls/hwax.crt}" ] || "$(dirname "$0")/gen-tls-cert.sh"
  hp="${HTTPS_PORT:-443}"
  ups="$(cat /proc/sys/net/ipv4/ip_unprivileged_port_start 2>/dev/null || echo 1024)"
  if [ "$hp" -lt "$ups" ]; then
    echo "  ⚠ rootless can't bind :$hp yet (unprivileged ports start at $ups)."
    echo "    Run ONCE:  sudo ./infra/scripts/grant-net-bind.sh $hp   then re-run start.sh"
  fi
fi

if instance_running "$INST_NGINX"; then
  echo "✓ $INST_NGINX already running"
else
  echo "→ start $INST_NGINX (:$HTTP_PORT${ENABLE_TLS:+, TLS :${HTTPS_PORT:-443}})"
  "$APPTAINER" instance start --bind "$REPO_ROOT:/workspace" "$NGINX_SIF" "$INST_NGINX"
fi

echo
echo "✓ HWAX up"
echo "  portal (direct) : http://127.0.0.1:${PORTAL_PORT}"
echo "  via nginx       : http://127.0.0.1:${HTTP_PORT}"
[ "${ENABLE_TLS:-false}" = "true" ] && echo "  TLS (https)     : https://127.0.0.1:${HTTPS_PORT:-443}   (public: ${PUBLIC_BASE_URL})"
echo "  routes          : edit backend/${ROUTES_PATH} → ./infra/scripts/restart.sh"
