#!/usr/bin/env bash
# 연결 사이트들의 포털 SSO .env 블록을 일괄 배포 — 없는 키만 추가(기존 값은 절대 안 건드림).
#
# 새 서버에서:  bash infra/env-kits/apply-envs.sh          # 전부
#               bash infra/env-kits/apply-envs.sh -n        # dry-run(변경 없이 계획만)
#               bash infra/env-kits/apply-envs.sh heax-hub  # 지정 서비스만
#
# 동작:
#   · 서비스 레포는 포털의 형제 디렉토리에서 자동 탐색(<portal 상위>/, ~/Projects/, ~/claude/)
#   · 킷(<service>.env)의 각 KEY=VALUE 를 대상 .env 에 병합 — 이미 있는 키는 보존(skip),
#     없는 키만 append. 값이 @GENERATE_HEX32@ 면 openssl 로 박스 로컬 시크릿을 생성.
#   · 대상 .env 가 없으면 새로 만든다(600).
#   · 적용 후엔 해당 서비스 재시작 필요: ./infra/scripts/services.sh down <svc> && up <svc>
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"          # infra/env-kits
ROOT="$(cd "$HERE/../.." && pwd)"                              # 포털 레포 루트
PARENT="$(dirname "$ROOT")"

DRY=0
case "${1:-}" in -n|--dry-run) DRY=1; shift ;; esac

# 서비스 → "레포디렉토리이름:.env 상대경로"
declare -A MAP=(
  [heax-hub]="HEAXHub:.env"
  [signalforge]="SignalForge:.env"
  [mx-white-paper]="MXWhitePaper:.env"
  [ai-data-hub]="AIDataHub:deploy/apptainer/.env"
)

find_repo() {  # $1=디렉토리 이름 → 절대경로 or 실패
  local name="$1" root
  for root in "$PARENT" "$HOME/Projects" "$HOME/claude"; do
    [ -d "$root/$name" ] && { echo "$root/$name"; return 0; }
  done
  return 1
}

apply_one() {  # $1=서비스명
  local svc="$1" spec repo rel kit dir target added=0 kept=0 key val line
  spec="${MAP[$svc]:-}"
  [ -n "$spec" ] || { echo "✗ 알 수 없는 서비스: $svc (지원: ${!MAP[*]})"; return 1; }
  repo="${spec%%:*}"; rel="${spec#*:}"
  kit="$HERE/$svc.env"
  [ -f "$kit" ] || { echo "✗ $svc: 킷 파일 없음($kit)"; return 1; }
  dir="$(find_repo "$repo")" || { echo "⚠ $svc: 레포($repo) 미발견 — skip (클론 후 재실행)"; return 0; }
  target="$dir/$rel"

  echo "── $svc → $target"
  if [ ! -f "$target" ]; then
    if [ "$DRY" = 1 ]; then echo "   (dry-run) .env 신규 생성 예정"; else
      mkdir -p "$(dirname "$target")"; : > "$target"; chmod 600 "$target"
      echo "   .env 신규 생성"
    fi
  fi
  while IFS= read -r line; do
    case "$line" in ''|'#'*) continue ;; esac
    key="${line%%=*}"; val="${line#*=}"
    if [ -f "$target" ] && grep -qE "^${key}=" "$target"; then
      kept=$((kept+1)); continue                       # 기존 값 보존
    fi
    [ "$val" = "@GENERATE_HEX32@" ] && val="$(openssl rand -hex 32)"
    if [ "$DRY" = 1 ]; then
      echo "   (dry-run) + $key"
    else
      printf '%s=%s\n' "$key" "$val" >> "$target"
    fi
    added=$((added+1))
  done < "$kit"
  echo "   추가 $added개 / 기존 보존 $kept개"
  return 0
}

SVCS=("$@"); [ ${#SVCS[@]} -gt 0 ] || SVCS=(heax-hub signalforge mx-white-paper ai-data-hub)
RC=0
for s in "${SVCS[@]}"; do apply_one "$s" || RC=1; done
echo
echo "▶ 완료. 적용 서비스 재시작:  $ROOT/infra/scripts/services.sh down <svc> && $ROOT/infra/scripts/services.sh up <svc>"
exit "$RC"
