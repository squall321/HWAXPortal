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

# apptainer: prefer a locally-extracted binary (no-sudo install via bootstrap.sh),
# else fall back to whatever is on PATH. Pick the newest bin-*/ if several exist.
if [ -z "${APPTAINER:-}" ]; then
  for _c in "$APPT_DIR"/bin-*/usr/bin/apptainer; do
    [ -x "$_c" ] && APPTAINER="$_c"
  done
fi
: "${APPTAINER:=apptainer}"

# rclone: prefer the no-sudo local binary (bootstrap-rclone.sh), else PATH.
if [ -z "${RCLONE:-}" ]; then
  [ -x "$REPO_ROOT/infra/bin/rclone" ] && RCLONE="$REPO_ROOT/infra/bin/rclone"
fi
: "${RCLONE:=rclone}"

require_apptainer() {
  command -v "$APPTAINER" >/dev/null 2>&1 || {
    echo "✗ '$APPTAINER' not found in PATH"; exit 1;
  }
}

instance_running() {
  # 출력을 **먼저 받고** 본다. `list | grep -q` 는 pipefail 아래서 grep 이 일치 즉시 파이프를 닫아 apptainer 가 SIGPIPE(141)를
  # 받으면 **떠 있는 인스턴스를 '없다'** 로 읽는다(목록이 파이프 용량보다 크면 — dev 실측 14.7%, 09-19). 그러면 start.sh 가 떠 있는
  # 포털을 다시 띄우려다 'already exists' 로 set -e 에 죽어 nginx 가 안 뜨고, stop.sh 는 '안 떠 있다' 며 멈추지 않는다.
  # 09-19 에 다른 자리는 고쳤는데 여기는 줄 이음(\) 때문에 가드 시험을 빠져나갔다(docs/update-all-skip-unchanged D-14).
  local _il
  _il="$("$APPTAINER" instance list --json 2>/dev/null)" || return 1
  grep -q "\"instance\": *\"$1\"" <<<"$_il"
}
