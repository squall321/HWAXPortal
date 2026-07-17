#!/usr/bin/env bash
# ONE-SHOT cae00 deploy — for ALL services, in one command:
#   git pull  →  auto-fill the Drive remote in each .env  →  pull the prebuilt artifact from Google
#   Drive  →  START the service.  Nothing is built here (cae00 can't reach npm / Docker Hub).
#
#   ./infra/scripts/deploy-all-from-drive.sh                 # pull + start ALL (portal mxwp heax aidh signalforge)
#   ./infra/scripts/deploy-all-from-drive.sh portal heax     # only the named ones
#   ./infra/scripts/deploy-all-from-drive.sh --remote=MyDrive # use a specific rclone remote alias
#   MXWP_DIR=~/Projects/MXWhitePaper ./infra/scripts/deploy-all-from-drive.sh   # override a repo path
#   SF_RESTORE_DB=1 ./infra/scripts/deploy-all-from-drive.sh signalforge  # 최초 시드/갱신 시에만 DB 복원
#
# Prereqs (once): an rclone remote configured on cae00 (likely ALREADY there from another project —
# we auto-detect ApptainerImages:, else the first remote, else pass --remote=). You do NOT need to
# hand-edit any .env — this fills *_DRIVE_REMOTE / *_IMAGES_REMOTE for you. The sub-path is already
# baked into each artifact (web.sif, HEAXHub dist) / handled by AIDH_ROOT_PATH.
set -euo pipefail
# apptainer rootless cgroups 는 D-Bus 사용자 세션 필요 — 비로그인 셸에 XDG_RUNTIME_DIR 가 비면
# 'couldn't create cgroup manager' 로 죽는다. 사용자 세션 버스가 있으면 잡아준다.
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"; export XDG_RUNTIME_DIR
[ -S "$XDG_RUNTIME_DIR/bus" ] && export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

# ── Repo locations (override via env). Default: siblings of this repo, then ~/Projects. ─────────
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() {  # $1=env-override  $2=dirname
  local v="$1" name="$2"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  for cand in "$PARENT/$name" "$HOME/Projects/$name" "$HOME/claude/$name"; do
    [ -d "$cand" ] && { printf '%s' "$cand"; return; }
  done
}
PORTAL_DIR="${PORTAL_DIR:-$SELF_REPO}"
MXWP_DIR="$(find_repo "${MXWP_DIR:-}" MXWhitePaper)"
HEAX_DIR="$(find_repo "${HEAX_DIR:-}" HEAXHub)"
AIDH_DIR="$(find_repo "${AIDH_DIR:-}" AIDataHub)"
SF_DIR="$(find_repo "${SF_DIR:-}" SignalForge)"

# Pick the rclone remote ALIAS: --remote=Name, else $RCLONE_REMOTE, else auto (ApptainerImages if
# present, else the first configured remote). cae00 likely already has it (another project set it up).
REMOTE_ALIAS=""
ARGS=()
for a in "$@"; do case "$a" in --remote=*) REMOTE_ALIAS="${a#*=}";; *) ARGS+=("$a");; esac; done
set -- "${ARGS[@]+"${ARGS[@]}"}"
RCLONE_BIN="$(command -v rclone || echo "$SELF_REPO/infra/bin/rclone")"
if [ -z "$REMOTE_ALIAS" ]; then REMOTE_ALIAS="${RCLONE_REMOTE:-}"; fi
if [ -z "$REMOTE_ALIAS" ] && [ -x "$RCLONE_BIN" ]; then
  if "$RCLONE_BIN" listremotes 2>/dev/null | grep -qx "ApptainerImages:"; then
    REMOTE_ALIAS="ApptainerImages"
  else
    REMOTE_ALIAS="$("$RCLONE_BIN" listremotes 2>/dev/null | head -1 | sed 's/:$//')"
  fi
fi
[ -n "$REMOTE_ALIAS" ] && printf '\033[1;36mℹ rclone remote: %s:\033[0m\n' "$REMOTE_ALIAS" \
  || printf '\033[1;33m⚠ no rclone remote detected — configure one (rclone config / copy rclone.conf) or pass --remote=NAME\033[0m\n'

# Robust git update: a plain `git pull --ff-only || true` silently leaves a repo on STALE code when
# the tree is dirty or diverged (that's how cae00 kept an old routes.env → wrong nginx routing). This
# stashes local junk and hard-resets to origin so the repo is ALWAYS current. Set NO_GIT_RESET=1 to
# only do a soft pull (and just warn if it can't fast-forward).
git_update() {  # run inside the repo dir
  local branch; branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
  git fetch origin "$branch" --quiet 2>/dev/null || { echo "  ⚠ git fetch failed (offline?) — using current checkout"; return 0; }
  if [ "${NO_GIT_RESET:-0}" = "1" ]; then
    git merge --ff-only "origin/$branch" 2>/dev/null \
      || echo "  ⚠ can't fast-forward (local changes/diverged) — NOT updated. Resolve, or unset NO_GIT_RESET."
  else
    local before after; before="$(git rev-parse --short HEAD 2>/dev/null)"
    git stash push -u -q -m "deploy-all auto-stash" 2>/dev/null || true
    git reset --hard "origin/$branch" --quiet 2>/dev/null || true
    after="$(git rev-parse --short HEAD 2>/dev/null)"
    [ "$before" = "$after" ] && echo "  · git: up to date ($after)" || echo "  · git: $before → $after (reset to origin/$branch)"
  fi
}

# Write KEY=<alias>:<path> into a repo's env file IF not already a non-empty value (idempotent).
set_remote() {  # $1=envfile  $2=KEY  $3=path
  local f="$1" key="$2" val="${REMOTE_ALIAS}:$3"
  [ -n "$REMOTE_ALIAS" ] || return 0
  [ -f "$f" ] || return 0
  if grep -qE "^${key}=.+" "$f" 2>/dev/null; then return 0; fi   # already set → respect it
  if grep -qE "^${key}=" "$f" 2>/dev/null; then
    sed -i "s#^${key}=.*#${key}=${val}#" "$f"
  else
    printf '\n%s=%s\n' "$key" "$val" >> "$f"
  fi
  printf '  · set %s=%s\n' "$key" "$val"
}

WANT="${*:-portal mxwp heax aidh signalforge}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }
hr() { printf '\n\033[1;36m── %s ───────────────────────────────────────\033[0m\n' "$*"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
skip() { printf '  \033[1;33m⚠ skip:\033[0m %s\n' "$*"; }

# We RESTART each service (stop → start) so freshly pulled images / nginx conf / code actually take
# effect. `start.sh` alone skips already-running instances, leaving stale config live (that's what
# caused the 502 / JSON / CSS-MIME issues). Set NO_RESTART=1 to only start what's down.
RESTART="${NO_RESTART:-0}"

# ── 1. Portal (the hub) ─────────────────────────────────────────────────────
if want portal; then
  hr "HWAX Portal  ($PORTAL_DIR)"
  ( cd "$PORTAL_DIR"
    git_update
    [ -f infra/.env ] || cp infra/.env.example infra/.env
    set_remote infra/.env HWAX_DRIVE_REMOTE HWAXPortal/images
    ./infra/scripts/images-from-drive.sh      # portal.sif + nginx.sif + frontend/dist
    [ "$RESTART" = 1 ] || ./infra/scripts/stop.sh 2>/dev/null || true   # stop → start = pick up new conf/images
    HWAX_NO_BUILD=1 ./infra/scripts/start.sh ) && ok "portal up" || skip "portal failed (see above)"
fi

# ── 2. MX White Paper (web.sif has the prebuilt dist baked in) ───────────────
if want mxwp; then
  if [ -n "$MXWP_DIR" ]; then
    hr "MX White Paper  ($MXWP_DIR)"
    ( cd "$MXWP_DIR"
      git_update
      [ -f .env ] || cp .env.example .env
      set_remote .env MXWP_IMAGES_REMOTE MXWhitePaper/images
      ./infra/scripts/images-from-drive.sh    # web.sif (dist baked) — postgres/meili/minio already present
      # Force-bounce the web instance so the NEW web.sif (baked dist) replaces the running one.
      # Resolve an extracted (no-D-Bus) apptainer directly (don't source _common — its set -e can
      # abort under odd shells); fall back to system apptainer.
      _appt="apptainer"
      for _c in infra/apptainer/bin-*/usr/bin/apptainer \
                ../HWAXPortal/infra/apptainer/bin-*/usr/bin/apptainer \
                "$HOME"/Projects/HWAXPortal/infra/apptainer/bin-*/usr/bin/apptainer \
                "$HOME"/claude/HWAXPortal/infra/apptainer/bin-*/usr/bin/apptainer; do
        [ -x "$_c" ] && { _appt="$_c"; break; }
      done
      # Bounce EVERY instance whose SIF may have been replaced by images-from-drive (it copies
      # *.sif). A live instance whose SIF is overwritten underneath keeps a broken squashfs
      # mount — every exec inside dies with "error while loading shared libraries: libc.so.6"
      # (bit cae00's mxwp_api → mxwp-mcp). start.sh re-creates them cleanly from the new SIFs.
      if [ "$RESTART" != 1 ]; then
        for _i in mxwp_web mxwp_api; do "$_appt" instance stop "$_i" 2>/dev/null || true; done
      fi
      ./infra/scripts/start.sh ) && ok "mxwp up" || skip "mxwp failed (see above)"
      # mxwp_api 를 재기동했으면 그 안에서 돌던 mxwp-mcp 도 다시 올린다(있으면).
      [ -x "$PORTAL_DIR/infra/scripts/services.sh" ] && \
        "$PORTAL_DIR/infra/scripts/services.sh" up mxwp-mcp 2>/dev/null | tail -2 || true
  else skip "MXWhitePaper repo not found (set MXWP_DIR=)"; fi
fi

# ── 3. HEAX Hub (Caddy serves the pulled dist) ──────────────────────────────
if want heax; then
  if [ -n "$HEAX_DIR" ]; then
    hr "HEAX Hub  ($HEAX_DIR)"
    ( cd "$HEAX_DIR"
      git_update
      [ -f .env ] || { [ -f .env.example ] && cp .env.example .env; }
      set_remote .env HEAX_DRIVE_REMOTE HEAXHub/dist
      ./deploy/apptainer/dist-from-drive.sh   # frontend/dist (+ optional caddy sif)
      bash deploy/apptainer/appdata-from-drive.sh || true   # 앱 데이터(materialtwin 재료 DB 등) 복원(비치명적)
      [ "$RESTART" = 1 ] || bash deploy/apptainer/stop.sh 2>/dev/null || true
      if ! HEAX_NO_BUILD=1 bash deploy/apptainer/start.sh; then
        echo "  ── last lines of var/logs/postgres-start.log (the hidden error) ──"
        tail -15 var/logs/postgres-start.log 2>/dev/null | sed 's/^/    /'
        exit 1
      fi ) && ok "heax up" || skip "heax failed (see the log lines above)"
  else skip "HEAXHub repo not found (set HEAX_DIR=)"; fi
fi

# ── 3b. SignalForge (SIF + DATA) — sync-from-drive pulls SIF+DB dump, up.sh starts, DB 는 안전하게 ──
# ⚠ 데이터: cae00 가 크롤로 축적한 DB 를 재배포가 덮어쓰지 않도록, DB 복원은 기본적으로 하지 않는다.
#   · 최초 시드/명시적 갱신:  SF_RESTORE_DB=1 deploy-all-from-drive.sh signalforge
#     → drive-sync/sync-from-drive.sh 가 Drive 최신 덤프를 sha256 검증 후 restore(직전 상태는 자동 안전백업).
#   · 기본(재배포):  DB 손대지 않음 — 축적 데이터 보존.
if want signalforge; then
  if [ -n "$SF_DIR" ]; then
    hr "SignalForge  ($SF_DIR)"
    ( cd "$SF_DIR"
      git_update
      [ -f .env ] || { [ -f .env.example ] && cp .env.example .env; }   # 최초엔 example → 시크릿은 별도 채움
      ./scripts/sync-from-drive.sh                # SIF(+.env.example) — Drive→apptainer/sif/ (SF 자체 remote 자동감지)
      [ "$RESTART" = 1 ] || bash scripts/down.sh 2>/dev/null || true
      ./scripts/up.sh                             # SIF 있으면 build skip; postgres+backend+mcp+crawler+frontend
      # ── DATA: 기본 보존, SF_RESTORE_DB=1 일 때만 Drive 최신 덤프로 복원(안전백업 후) ──
      if [ "${SF_RESTORE_DB:-0}" = "1" ]; then
        echo "  · SF_RESTORE_DB=1 → Drive 최신 DB 덤프 복원(직전 상태 안전백업)"
        bash scripts/drive-sync/sync-from-drive.sh || echo "  ⚠ DB 복원 실패 — backups/ 안전백업 확인"
      else
        echo "  · DB 보존(기존 cae00 데이터 유지). 최초 시드/갱신은:  SF_RESTORE_DB=1 $0 signalforge"
      fi ) && ok "signalforge up" || skip "signalforge failed (see above)"
  else skip "SignalForge repo not found (set SF_DIR=)"; fi
fi

# ── 4. AI Data Hub (no build, no Drive artifact — git pull + root_path) ──────
# boot.sh restarts uvicorn itself, so the redirect/root_path code is picked up.
if want aidh; then
  if [ -n "$AIDH_DIR" ]; then
    hr "AI Data Hub  ($AIDH_DIR)"
    # --force restarts even if the port is busy (start_api.sh kills the old api.pid + relaunches),
    # so the new redirect/root_path code is picked up.
    ( cd "$AIDH_DIR"
      git_update
      AIDH_ROOT_PATH=/ai-data-hub ./boot.sh --force ) && ok "aidh up" || skip "aidh failed (see above)"
  else skip "AIDataHub repo not found (set AIDH_DIR=)"; fi
fi

# ── Always refresh the portal routing: regenerate nginx conf + restart nginx so the per-service
#    strip/proxy rules are live (a service deploy that didn't touch the portal would otherwise leave
#    nginx on a stale conf → /mx-white-paper/assets etc. served wrong). Cheap; nginx-only bounce.
if [ "${NO_NGINX_REFRESH:-0}" != "1" ] && [ -d "$PORTAL_DIR" ]; then
  hr "Portal routing refresh (nginx)"
  ( cd "$PORTAL_DIR"
    APPT="apptainer"; for c in infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$c" ] && { APPT="$c"; break; }; done
    ./infra/scripts/gen-nginx-conf.sh >/dev/null 2>&1 || true
    "$APPT" instance stop hwax_nginx >/dev/null 2>&1 || true
    HWAX_NO_BUILD=1 ./infra/scripts/start.sh >/dev/null 2>&1 || true ) && ok "nginx reloaded with current routes" || skip "nginx refresh failed"
fi

# ── Health summary (everything that was started) ────────────────────────────
hr "Health"
probe() {  # $1=label  $2=url
  local code; code="$(curl -sk -m4 -o /dev/null -w '%{http_code}' "$2" 2>/dev/null || echo 000)"
  if [ "$code" = 200 ] || [ "$code" = 401 ] || [ "$code" = 302 ]; then ok "$1 → $code  ($2)"
  else skip "$1 → $code  ($2)"; fi
}
want portal && { probe "portal /health   " "http://127.0.0.1:8723/health"
                 probe "nginx  /health   " "http://127.0.0.1:8088/health"; }
want mxwp        && probe "mxwp   web      " "http://127.0.0.1:5173/"
want heax        && probe "heax   :4180    " "http://127.0.0.1:4180/"
want aidh        && probe "aidh   /health  " "http://127.0.0.1:8001/api/system/health"
want signalforge && probe "sf     :17370   " "http://127.0.0.1:17370/"

hr "Done"
echo "  Portal:  https://hwax.sec.samsung.net/   (tiles: /heax-hub/ /ai-data-hub/ /mx-white-paper/ /signalforge/)"
echo "  If a service shows a non-2xx above, re-run just it:  $0 <portal|mxwp|heax|aidh|signalforge>"
