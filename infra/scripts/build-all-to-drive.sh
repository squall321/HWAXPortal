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
# 못 찾으면 빈 문자열 + 성공(0)으로 끝나야 한다. `return 0` 이 없으면 for 루프 마지막
# `[ -d ]` 의 실패(1)가 함수 반환값이 되고, set -e 라 아래 대입에서 스크립트가 그 자리에서
# 죽는다 — 출력 한 글자 없이. deploy-all-from-drive.sh 에서 실제로 그 사고가 났다
# (cae00 은 레포 하나가 없어 매번 즉시 종료 → DynaForge 가 배포된 적이 없었다).
find_repo() { local v="$1" n="$2"; [ -n "$v" ] && { printf '%s' "$v"; return 0; }
  for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do [ -d "$c" ] && { printf '%s' "$c"; return 0; }; done
  return 0; }
PORTAL_DIR="${PORTAL_DIR:-$SELF_REPO}"
MXWP_DIR="$(find_repo "${MXWP_DIR:-}" MXWhitePaper)"
HEAX_DIR="$(find_repo "${HEAX_DIR:-}" HEAXHub)"
SF_DIR="$(find_repo "${SF_DIR:-}" SignalForge)"
KOOR_DIR="$(find_repo "${KOOR_DIR:-}" KooRemapper)"
WANT="${*:-portal mxwp heax signalforge kooremapper}"
want() { printf '%s ' "$WANT" | grep -qiw "$1"; }
hr() { printf '\n\033[1;36m── %s ───────────────────────────────────────\033[0m\n' "$*"; }

# 배포 빌드는 의존성을 **바꾸지 않는다**. 종전엔 --frozen-lockfile=false 라 package.json 과
# 락파일이 어긋나 있으면 빌드가 조용히 락파일을 고쳐 커밋되지 않은 의존성 변경이 산출물에
# 섞일 수 있었다(실제로 MXWhitePaper 의 recharts specifier 가 이 경로로 갱신됐다).
# 락파일이 있으면 --frozen-lockfile 로 고정하고, 어긋나면 빌드를 멈춰 사람이 보게 한다.
# 락파일이 아예 없는 프로젝트(pnpm-lock 을 커밋하지 않는 곳)는 멈추지 않되 경고를 남긴다.
pnpm_install() {  # $1=프로젝트 디렉터리(. 이면 현재)
  local d="${1:-.}"
  if [ -f "$d/pnpm-lock.yaml" ]; then
    pnpm --dir "$d" install --frozen-lockfile || {
      echo "✗ $d: 락파일이 package.json 과 불일치합니다." >&2
      echo "  배포 빌드에서 의존성을 임의로 바꾸지 않도록 여기서 멈춥니다." >&2
      echo "  해결: 해당 레포에서 'pnpm install' 로 락파일을 갱신·검토 후 커밋하고 다시 실행하세요." >&2
      return 1
    }
  else
    echo "  ⚠ $d: pnpm-lock.yaml 없음 — 의존성 고정 불가(해석 설치로 진행)" >&2
    pnpm --dir "$d" install
  fi
}

if want portal; then
  hr "HWAX Portal — build SPA + sif → Drive"
  ( cd "$PORTAL_DIR"
    pnpm_install frontend && pnpm --dir frontend build
    ./infra/scripts/build.sh                       # portal.sif + nginx.sif (skips if present)
    ./infra/scripts/images-to-drive.sh )
fi

if want mxwp && [ -n "$MXWP_DIR" ]; then
  hr "MX White Paper — build dist + bake web.sif → Drive"
  ( cd "$MXWP_DIR"
    pnpm_install . && pnpm schema:gen
    VITE_BASE_PATH=/mx-white-paper/ pnpm --filter @mx/web build
    apptainer build --force infra/apptainer/web.sif infra/apptainer/web.def   # bakes dist
    ./infra/scripts/images-to-drive.sh )
fi

if want heax && [ -n "$HEAX_DIR" ]; then
  hr "HEAX Hub — build dist + app-data → Drive"
  ( cd "$HEAX_DIR"
    pnpm_install frontend
    # heax vite.config 는 VITE_BASE_PATH 를 읽는다(HEAX_BASE_PATH 아님 — 과거 이름 불일치로
    # 루트 base dist 가 배포돼 포털 서브패스에서 자산 404가 났던 원인). 둘 다 넘겨 견고하게.
    VITE_BASE_PATH=/heax-hub/ HEAX_BASE_PATH=/heax-hub/ pnpm --dir frontend build
    ./deploy/apptainer/dist-to-drive.sh
    # 앱 런타임 데이터(materialtwin 재료 DB 등) — 코드/dist엔 없는 표면. 비치명적(실패해도 계속).
    ./deploy/apptainer/appdata-to-drive.sh || echo "  ⚠ app-data 백업 생략(비치명적)"
    # 대용량 모델 가중치(voice_recorder TTS 등) — app-data tar 밖, 별도 models/ 로 증분 업로드.
    [ -f deploy/apptainer/models-to-drive.sh ] && bash deploy/apptainer/models-to-drive.sh || true )
fi

# SignalForge: dist 는 frontend.sif 에 베이크되고(별도 dist 배송 없음), DATA(postgres) 까지 함께
# 나른다. scripts/sync-to-drive.sh 가 SF 의 통합 업로드 진입점 — DB 덤프 + SIF + env 를 한 번에 Drive 로.
if want signalforge && [ -n "$SF_DIR" ]; then
  hr "SignalForge — build dist→sif + DB dump → Drive"
  ( cd "$SF_DIR"
    VITE_BASE_PATH=/signalforge/ pnpm_install frontend
    VITE_BASE_PATH=/signalforge/ pnpm --dir frontend build   # frontend.sif 가 이 dist 를 베이크
    ./scripts/build.sh                                       # SIF 6종(있으면 skip)
    ./scripts/sync-to-drive.sh )                             # DB 덤프 + SIF + env → Drive(통합)
fi

# KooRemapper(DynaForge): compat 바이너리(glibc≤2.36, debian:12 빌더) + 듀얼 프론트
# (standalone+portal) + 서비스 SIF 를 빌드하고 Drive 로 통합 업로드. dist-to-drive 가
# bin+dist+*.sif 를 tar+checksum 후 publish 한다.
if want kooremapper && [ -n "$KOOR_DIR" ]; then
  hr "KooRemapper / DynaForge — compat 바이너리 + 듀얼 프론트 + SIF → Drive"
  ( cd "$KOOR_DIR"
    bash scripts/build_linux_compat.sh              # compat 바이너리 → platform/backend/bin
    bash platform/infra/scripts/build-frontend.sh   # 듀얼 프론트(standalone + index.portal.html)
    bash platform/infra/scripts/build.sh            # 서비스 SIF(api/mcp/postgres/nginx, skip if present)
    bash platform/infra/scripts/build-cli.sh || echo "  ⚠ cli.sif 생략(비치명)"
    bash platform/infra/scripts/dist-to-drive.sh )  # bin+dist+*.sif → Drive
fi

# 올렸다고 끝이 아니다 — 부분 실행(이름 지정)이나 중간 실패로 Drive 가 dev 보다 뒤처진 채
# 끝날 수 있고, 그건 cae00 에서 '옛 앱이 도는데 checksums 는 OK' 로 나타난다. 여기서 대조한다.
hr "publish 확인 — Drive 가 이 박스와 일치하는가"
bash "$SELF_REPO/infra/scripts/drive-drift.sh" || \
  echo "  ⚠ 위 항목이 아직 Drive 에 없다 — cae00 은 그만큼 옛것을 받는다"

hr "Done — AIDataHub has no build (cae00 just git pulls). Now on cae00: deploy-all-from-drive.sh"
