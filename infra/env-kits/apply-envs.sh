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
  [agent-server]="HWAXAgentServer:.env"
  [paper-ingest]="PaperIngest:.env"
)

find_repo() {  # $1=디렉토리 이름 → 절대경로 or 실패
  local name="$1" root
  for root in "$PARENT" "$HOME/Projects" "$HOME/claude"; do
    [ -d "$root/$name" ] && { echo "$root/$name"; return 0; }
  done
  return 1
}

# 형제 ReportArchive 의 .env 에서 키 값을 읽는다(없으면 빈값) — agent-server 가 RA 의 상암 LLM 설정을
# '그대로' 상속하는 용도(@FROM_RA:KEY@ 마커). RA 는 읽기 전용(수정하지 않음).
ra_env_value() {  # $1=키(LLM_BASE_URL 등) → stdout 값
  # 정본은 **포털 infra/.env** 다(2026-09-27). RA 가 포털 박스를 떠나 그 .env 는 관리되지 않는 사본이 됐고,
  # 지우는 날 이 함수가 빈 값을 돌려 챗·심의·PaperIngest 의 LLM 이 조용히 비었을 것이다(RA 요청서 §3-5).
  # update-all 1e 가 RA .env 에서 infra/.env 로 한 번 옮긴다. 형제 RA .env 는 그 전까지의 폴백(레거시)이다.
  local v radir raenv
  # update-all 1e 의 _upsert_kv·_ra_envv 와 같은 줄을 본다 — 마지막 활성 줄, `export` 허용, 인라인 주석·따옴표 제거(LC_ALL=C: UTF-8 sed 함정)
  v="$(sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=[[:space:]]*//p" "$ROOT/infra/.env" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r')"
  [ -n "$v" ] && { printf '%s' "$v"; return 0; }
  radir="$(find_repo ReportArchive)" || return 1
  for raenv in "$radir/backend/.env" "$radir/.env"; do
    [ -f "$raenv" ] || continue
    grep -E "^$1=" "$raenv" 2>/dev/null | head -1 | cut -d= -f2- && return 0
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
    case "$val" in
      @GENERATE_HEX32@) val="$(openssl rand -hex 32)" ;;
      @FROM_RA:*@)  # ReportArchive .env 의 해당 키를 상속 — 없으면(dev=mock) 이 키는 건너뜀
        rak="${val#@FROM_RA:}"; rak="${rak%@}"
        val="$(ra_env_value "$rak")"
        # 문구에 서비스 이름을 박아 두면 다른 kit 에서 거짓말이 된다 — 실제로 agent-server 가
        # 아닌 kit 에서도 "agent-server 기본값" 이라고 찍혔다. 무엇이 없어서 무엇이 되는지만 말한다.
        [ -n "$val" ] || { echo "   · $key: RA .env 에 $rak 없음 → 건너뜀(대상 앱의 자체 기본값을 쓴다)"; continue; } ;;
    esac
    if [ "$DRY" = 1 ]; then
      case "$key" in *KEY*|*TOKEN*|*SECRET*|*PASSWORD*) echo "   (dry-run) + $key=****(가림)" ;; *) echo "   (dry-run) + $key=$val" ;; esac
    else
      printf '%s=%s\n' "$key" "$val" >> "$target"
    fi
    added=$((added+1))
  done < "$kit"
  echo "   추가 $added개 / 기존 보존 $kept개"
  return 0
}

# 기본 목록에 agent-server·paper-ingest 가 빠져 있어, 인자 없이 돌리면 LLM 주입이 절반만
# 됐다. LLM 을 쓰는 서비스가 하나라도 빠지면 그 앱만 조용히 dev 폴백(127.0.0.1:8000)으로
# 떨어지고, cae00 에서는 Errno 111 로 죽는다. 등록된 것은 전부 기본으로 돈다.
SVCS=("$@"); [ ${#SVCS[@]} -gt 0 ] || SVCS=("${!MAP[@]}")
RC=0
for s in "${SVCS[@]}"; do apply_one "$s" || RC=1; done
echo
echo "▶ 완료. 적용 서비스 재시작:  $ROOT/infra/scripts/services.sh down <svc> && $ROOT/infra/scripts/services.sh up <svc>"
exit "$RC"
