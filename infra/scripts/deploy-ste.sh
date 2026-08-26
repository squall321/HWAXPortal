#!/usr/bin/env bash
# cae00 에서 STE(헤드노드 stc, 에어갭) 코드 갱신 배포를 트리거한다 — 메커니즘은 STE 소유
#
#   infra/scripts/deploy-ste.sh                 # 기본 위치의 STE 레포로 배포
#   STE_REPO=~/SmartTwinExplorer deploy-ste.sh   # STE 레포 위치 지정
#
# 의도적·비정기 작업이다(주 단위 코드 갱신). update-all 의 프로브 실행과 분리해 둔 이유는
# 실제 stc 배포가 routine 프로브(크론 포함)에 섞여 발화하지 않게 하기 위함이다.
# 배포 로직 자체는 SmartTwinExplorer/deploy/refresh-code.sh(런북 §11)에 있다 — 여기선 트리거만 한다.
set -euo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*" >&2; }
die() { bad "$*"; exit 1; }

STE_REPO="${STE_REPO:-$HOME/SmartTwinExplorer}"
DEPLOY="$STE_REPO/deploy/refresh-code.sh"

[ -x "$DEPLOY" ] || die "STE 배포 스크립트를 못 찾는다: $DEPLOY
    STE_REPO 로 위치를 지정하거나, 최초 반입(런북 §1~§8)을 먼저 끝낸다."

printf '\033[1;36m▶ STE 코드 갱신 배포 트리거 — %s\033[0m\n' "$STE_REPO"
"$DEPLOY" "$@" || die "STE 배포 실패 — 위 로그와 런북 §9(실패 대처) 참조"

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
