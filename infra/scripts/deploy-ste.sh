#!/usr/bin/env bash
# cae00 에서 STE(헤드노드 stc, 에어갭) 코드 갱신 배포를 트리거한다 — 메커니즘은 STE 소유
#
#   infra/scripts/deploy-ste.sh                 # STE 배포(저장소 없으면 Drive 에서 받아와 클론까지)
#   STE_REPO=~/SmartTwinExplorer deploy-ste.sh   # STE 레포 위치 지정(기본 ~/SmartTwinExplorer)
#   STE_DRIVE_REMOTE=MyDrive: STE_STAGING_PATH=SmartTwinExplorer/staging deploy-ste.sh  # 리모트/경로 지정
#
# 의도적·비정기 작업이다(주 단위 코드 갱신). update-all 의 프로브 실행과 분리해 둔 이유는
# 실제 stc 배포가 routine 프로브(크론 포함)에 섞여 발화하지 않게 하기 위함이다.
# 배포 로직 자체는 SmartTwinExplorer/deploy/refresh-code.sh(런북 §11)에 있다 — 여기선 트리거만 한다.
# 저장소가 없으면(최초) Drive 스테이징 번들에서 rclone 으로 받아 git clone 한다 — 단 Teleport 접속
# 설정(transport.env)만은 클러스터 비밀이라 자동 못 채우고, 한 번 채우라 안내하고 멈춘다(그 뒤 재실행).
set -euo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*" >&2; }
die() { bad "$*"; exit 1; }

STE_REPO="${STE_REPO:-$HOME/SmartTwinExplorer}"
STAGING="${STE_STAGING:-$HOME/ste-staging}"
DEPLOY="$STE_REPO/deploy/refresh-code.sh"
SKIP_PULL=""

# ── STE 저장소가 없으면 Drive 스테이징 번들에서 부트스트랩 ──────────────────────
# STE 는 에어갭(헤드노드 stc)이라 코드가 github 이 아니라 dev→Drive 번들로 온다. 저장소가
# 통째로 없는 cae00 에서도 이 스크립트 하나로 받아오게 한다(dev 가 pack-staging+push-to-drive 선행).
if [ ! -x "$DEPLOY" ]; then
  printf '\033[1;36m▶ STE 저장소 없음(%s) — Drive 스테이징에서 부트스트랩\033[0m\n' "$STE_REPO"
  RCLONE="$(command -v rclone || echo "$SELF/infra/bin/rclone")"
  [ -x "$RCLONE" ] || die "rclone 이 없다 (HWAXPortal infra/bin/rclone 또는 PATH)"
  # 리모트: STE_DRIVE_REMOTE 우선, 없으면 pull-from-drive 와 같은 규칙(ApptainerImages: → 첫 리모트)
  REMOTE="${STE_DRIVE_REMOTE:-}"
  [ -z "$REMOTE" ] && "$RCLONE" listremotes 2>/dev/null | grep -qx 'ApptainerImages:' && REMOTE="ApptainerImages:"
  [ -z "$REMOTE" ] && REMOTE="$("$RCLONE" listremotes 2>/dev/null | head -1)"
  [ -n "$REMOTE" ] || die "rclone remote 가 없다 — STE_DRIVE_REMOTE 로 지정하라"
  STE_PATH="${STE_STAGING_PATH:-SmartTwinExplorer/staging}"
  echo "  Drive: ${REMOTE}${STE_PATH} → $STAGING"
  "$RCLONE" copy "${REMOTE}${STE_PATH}" "$STAGING" --progress \
    || die "스테이징 수신 실패 — dev 가 push-to-drive 했는지, 리모트/경로가 맞는지 확인"
  [ -f "$STAGING/ste-code.bundle" ] || die "스테이징에 ste-code.bundle 이 없다: $STAGING"
  ( cd "$STAGING" && sha256sum -c SHA256SUMS >/dev/null ) || die "무결성(sha256) 실패 — 깨진 파일 재수신(런북 §9-B)"
  ok "스테이징 수신·검증"
  mkdir -p "$STE_REPO"
  git clone "$STAGING/ste-code.bundle" "$STE_REPO" >/dev/null 2>&1 || die "번들 클론 실패: $STAGING/ste-code.bundle"
  ok "STE 저장소 클론 → $STE_REPO"
  # 접속 설정 — Teleport 값은 클러스터 비밀이라 자동으로 못 채운다. 예시 복사 후 채우라 안내하고 멈춘다.
  if [ ! -f "$STE_REPO/deploy/transport.env" ]; then
    cp "$STAGING/transport.env.example" "$STE_REPO/deploy/transport.env" 2>/dev/null \
      || cp "$STE_REPO/deploy/transport.env.example" "$STE_REPO/deploy/transport.env" 2>/dev/null || true
    die "접속 설정을 채워라: $STE_REPO/deploy/transport.env
    teleport 블록(REMOTE_USER·TP_PROXY·TP_CLUSTER·HEAD_NODE)을 채운 뒤 이 스크립트를 다시 실행하면 배포까지 이어진다(런북 §4)."
  fi
  SKIP_PULL="--skip-pull"   # 방금 받은 스테이징을 재사용(중복 pull 방지)
  ok "부트스트랩 완료 — 배포로 진행"
fi

printf '\033[1;36m▶ STE 코드 갱신 배포 트리거 — %s\033[0m\n' "$STE_REPO"
STE_STAGING="$STAGING" "$DEPLOY" $SKIP_PULL "$@" || die "STE 배포 실패 — 위 로그와 런북 §9(실패 대처) 참조"

# 포털 프록시 경유로 살아났는지 확인
HTTP_PORT=8088
[ -f "$SELF/infra/.env" ] && HTTP_PORT="$(sed -n 's/^HTTP_PORT=\([0-9]*\).*/\1/p' "$SELF/infra/.env" | head -1)"
HTTP_PORT="${HTTP_PORT:-8088}"
# 상태코드만 보면 안 된다 — /ste/ 라우트 미반영 시 포털 catch-all 이 SPA(index.html)를 200 으로
# 돌려줘 배포 성공으로 오판한다(update-all.sh 가 실측·정리한 문제). 본문으로 백엔드 응답을 확인한다.
resp="$(curl -sk -m 5 -w '\n%{http_code}' "http://127.0.0.1:$HTTP_PORT/ste/api/health" 2>/dev/null || true)"
code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
if printf '%s' "$body" | grep -q 'smart-twin-explorer'; then
  ok "포털 프록시 :$HTTP_PORT/ste/api/health → 백엔드 응답 확인"
else
  bad "포털 프록시 :$HTTP_PORT/ste/api/health → [$code] 백엔드 응답 아님 (포털 SPA 폴백/미도달 — nginx /ste/ 라우트·ste-tunnel 확인)"
fi
