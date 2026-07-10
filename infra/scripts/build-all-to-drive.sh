#!/usr/bin/env bash
# ONLINE build host: build every service for the HWAX portal sub-path and push the artifacts to
# Google Drive, so cae00 can deploy with `deploy-all-from-drive.sh` (no build there).
# Run on a machine that CAN reach npm + Docker Hub and has pnpm + apptainer + rclone.
#
#   ./infra/scripts/build-all-to-drive.sh                 # all
#   ./infra/scripts/build-all-to-drive.sh portal mxwp     # only named
set -euo pipefail
# apptainer rootless cgroups 는 D-Bus 사용자 세션이 필요하다 — 비로그인/스크립트 셸엔 XDG_RUNTIME_DIR
# 가 비어 'couldn't create cgroup manager: rootless cgroups require a D-Bus session' 로 죽는다
# (예: SF DB dump 의 apptainer exec pg_dump). 사용자 세션 버스가 있으면 잡아준다.
: "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"; export XDG_RUNTIME_DIR
[ -S "$XDG_RUNTIME_DIR/bus" ] && export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local v="$1" n="$2"; [ -n "$v" ] && { printf '%s' "$v"; return; }
  for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
PORTAL_DIR="${PORTAL_DIR:-$SELF_REPO}"
MXWP_DIR="$(find_repo "${MXWP_DIR:-}" MXWhitePaper)"
HEAX_DIR="$(find_repo "${HEAX_DIR:-}" HEAXHub)"
SF_DIR="$(find_repo "${SF_DIR:-}" SignalForge)"
WANT="${*:-portal mxwp heax signalforge}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }
hr() { printf '\n\033[1;36m── %s ───────────────────────────────────────\033[0m\n' "$*"; }

if want portal; then
  hr "HWAX Portal — build SPA + sif → Drive"
  ( cd "$PORTAL_DIR"
    pnpm --dir frontend install --frozen-lockfile=false && pnpm --dir frontend build
    ./infra/scripts/build.sh                       # portal.sif + nginx.sif (skips if present)
    ./infra/scripts/images-to-drive.sh )
fi

if want mxwp && [ -n "$MXWP_DIR" ]; then
  hr "MX White Paper — build dist + bake web.sif → Drive"
  ( cd "$MXWP_DIR"
    pnpm install --frozen-lockfile=false && pnpm schema:gen
    VITE_BASE_PATH=/mx-white-paper/ pnpm --filter @mx/web build
    apptainer build --force infra/apptainer/web.sif infra/apptainer/web.def   # bakes dist
    ./infra/scripts/images-to-drive.sh )
fi

if want heax && [ -n "$HEAX_DIR" ]; then
  hr "HEAX Hub — build dist → Drive"
  ( cd "$HEAX_DIR"
    pnpm --dir frontend install --frozen-lockfile=false
    HEAX_BASE_PATH=/heax-hub/ pnpm --dir frontend build
    ./deploy/apptainer/dist-to-drive.sh )
fi

# SignalForge: dist 는 frontend.sif 에 베이크되고(별도 dist 배송 없음), DATA(postgres) 까지 함께
# 나른다. scripts/sync-to-drive.sh 가 SF 의 통합 업로드 진입점 — DB 덤프 + SIF + env 를 한 번에 Drive 로.
if want signalforge && [ -n "$SF_DIR" ]; then
  hr "SignalForge — build dist→sif + DB dump → Drive"
  ( cd "$SF_DIR"
    VITE_BASE_PATH=/signalforge/ pnpm --dir frontend install --frozen-lockfile=false
    VITE_BASE_PATH=/signalforge/ pnpm --dir frontend build   # frontend.sif 가 이 dist 를 베이크
    ./scripts/build.sh                                       # SIF 6종(있으면 skip)
    ./scripts/sync-to-drive.sh )                             # DB 덤프 + SIF + env → Drive(통합)
fi

hr "Done — AIDataHub has no build (cae00 just git pulls). Now on cae00: deploy-all-from-drive.sh"
