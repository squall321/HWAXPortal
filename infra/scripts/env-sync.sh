#!/usr/bin/env bash
# .env.example 에 새로 생긴 설정이 **이미 있는 .env** 에 없으면 채운다(멱등·백업·값 보존).
#
# 왜 필요한가 — 코드에 옵션이 하나 늘면 `.env.example` 에는 적히지만, 이미 배포된 박스의 `.env` 는
# 그대로다. 그 차이는 **조용하다**: 앱은 기본값으로 뜨고(또는 기능만 빠지고) 아무도 모른다.
# 실제로 09-19 에 그 모양이 났다 — StepForge 공개주소(`APPTAINERENV_STEPFORGE_PUBLIC_BASE`)가
# dev 에만 있고 cae00 에는 없어 앱이 자리표시자 URL 을 냈다. 사람이 문서를 보고 손으로 넣는 방식은
# 박스가 늘수록 반드시 어긋난다.
#
# 규율
#   · **있는 값은 절대 건드리지 않는다.** 순서도 안 바꾼다. 없는 것만 **끝에 덧붙인다.**
#   · 쓰기 전에 `.env.bak-<타임스탬프>` 로 백업한다.
#   · 값이 **사람이 정해야 하는 것**(비밀·자리표시자·빈 값)이면 주석으로 넣고 크게 알린다 —
#     예시값을 그대로 활성화하면 "그럴듯하게 틀린 설정" 이 되어 자리표시자 URL 사고를 반복한다.
#   · 주석으로 선언된 키(`# KEY=`)도 **선언된 것**으로 본다 — 다시 붙이지 않는다(매번 늘어나지 않게).
#
# 사용:
#   ./infra/scripts/env-sync.sh              # 발견되는 모든 .env 를 채운다
#   ./infra/scripts/env-sync.sh --check      # 보고만(빠진 것이 있으면 종료코드 1)
#   ./infra/scripts/env-sync.sh <리포루트> …  # 대상을 직접 지정
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # HWAXPortal 루트
# "값을 정해야 한다" 로 남긴 키는 그 설정이 켜는 기능이 아직 꺼져 있다는 뜻이다 — update-all 의
# "있는데 안 켠 기능" 장부(○)에도 적는다(HWAX_SKIP_LEDGER 가 있을 때만; 단독 실행이면 아무 일도 없다).
_LEDGER_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/skip-ledger.sh"
if [ -f "$_LEDGER_LIB" ]; then . "$_LEDGER_LIB"; else hwax_skip_record() { :; }; fi
CHECK=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --check) CHECK=1 ;;
    *) ARGS+=("$a") ;;
  esac
done

TS="$(date +%Y%m%dT%H%M%SZ)"
ADDED=0; NEEDS=0; PAIRS=0

# 대상 찾기 — 리포 루트와 흔한 하위 배치(infra/·platform/)를 본다. `.env` 가 없으면 건너뛴다
# (그건 최초 설치의 일이지 동기화의 일이 아니다).
# 기본 대상은 **이 스택이 운영하는 리포만**이다. 형제 디렉터리를 통째로 훑으면 남의 프로젝트
# (.env 를 자기 규칙으로 쓰는) 까지 건드린다 — 실제로 첫 판이 KooRemapper·MXWhitePaper 등
# 다섯 개를 잡았다. 그 밖은 인자로 **명시할 때만** 본다.
STACK_REPOS=(HWAXPortal HWAXMcpGateway HEAXHub HWAXAgentServer SignalForge AIDataHub StepForge)

discover() {
  local roots=() r sub seen=""
  if [ "${#ARGS[@]}" -gt 0 ]; then
    roots=("${ARGS[@]}")
  else
    for r in "${STACK_REPOS[@]}"; do
      [ -d "$ROOT/../$r" ] && roots+=("$(cd "$ROOT/../$r" && pwd)")
    done
  fi
  for r in "${roots[@]}"; do
    for sub in "" "/infra" "/platform"; do
      [ -f "$r$sub/.env.example" ] && [ -f "$r$sub/.env" ] || continue
      # 같은 경로가 두 번 나오지 않게(리포 루트와 형제 목록에 동시에 걸릴 수 있다)
      case "$seen" in *"|$r$sub|"*) continue ;; esac
      seen="$seen|$r$sub|"
      printf '%s\n' "$r$sub"
    done
  done
}

# 사람이 정해야 하는 값인가 — 비밀·자리표시자·빈 값
needs_human() {
  local key="$1" val="$2"
  [ -z "$val" ] && return 0
  case "$key" in
    *SECRET*|*PASSWORD*|*TOKEN*|*_KEY|*APIKEY*|*_PAT|*CREDENTIAL*) return 0 ;;
  esac
  case "$val" in
    *CHANGE_ME*|*REPLACE*|*TODO*|*'<'*'>'*|your-*|*example.com*|*xxx*) return 0 ;;
  esac
  return 1
}

for DIR in $(discover); do
  EX="$DIR/.env.example"; EN="$DIR/.env"
  PAIRS=$((PAIRS+1))
  # 선언된 키 — 활성(KEY=)과 주석(# KEY=) 둘 다 "선언" 으로 본다
  declared="$(sed -nE 's/^[[:space:]]*#?[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/\1/p' "$EN" | sort -u)"
  add_active=(); add_commented=(); add_needval=(); add_optional=()
  while IFS= read -r line; do
    case "$line" in '') continue ;; esac
    optional=0
    # **주석으로 선언된 옵션도 본다** — "이런 설정이 있다" 는 사실이 안 보이면 없는 것과 같다.
    # (예: StepForge 공개주소는 박스마다 달라 예시에 주석으로만 적힌다 — 그게 cae00 에서 빠진 바로 그 값이다.)
    case "$line" in
      '#'*)
        line="${line#\#}"; line="${line#"${line%%[![:space:]]*}"}"
        case "$line" in [A-Za-z_]*=*) optional=1 ;; *) continue ;; esac ;;
    esac
    key="${line%%=*}"
    # ⚠ **산문을 키로 읽지 않는다.** 설명문이 KEY=VALUE 모양을 띠면 종전 파서가 키로 삼았다
    #   (실측 2026-09-25: `# Empty = standalone …`·`# public_base_url = the origin …`·
    #    `# provider=local일 때 사용.` 셋이 "안 켠 설정" 목록에 섞여 나왔다 — 키 뒤 공백을 지우고
    #    대소문자를 안 봤기 때문이다). 규칙 하나로 셋 다 걸러진다 — **키는 UPPER_SNAKE 이고 공백이 없다.**
    #   이 리포군의 실제 키는 전부 그렇다(전 리포 .env.example 전수 확인). 소문자 키를 쓰는 리포가
    #   생기면 여기를 고친다 — 조용히 흘리지 말고.
    case "$key" in *[!A-Z0-9_]*|'') continue ;; esac
    printf '%s\n' "$declared" | grep -qx "$key" && continue
    val="${line#*=}"
    # 값이 필요한가(비밀·자리표시자·빈 값)를 **먼저** 본다 — 주석으로 적힌 비밀은 둘 다 참인데,
    # 사람이 할 일은 "값을 정한다" 쪽이다(예시니까 놔둬도 된다고 읽히면 안 된다).
    if needs_human "$key" "$val"; then
      add_commented+=("$key=$val"); add_needval+=("$key")
    elif [ "$optional" = "1" ]; then
      add_commented+=("$key=$val"); add_optional+=("$key")
    else
      add_active+=("$key=$val")
    fi
  done < "$EX"

  n_a="${#add_active[@]}"; n_c="${#add_commented[@]}"
  # ⚠ **밀린 양이 크면 사람에게 넘긴다.** 평상시 드리프트는 한두 개다 — 수십 개가 한꺼번에 나오면
  # 그건 "새 옵션이 하나 늘었다" 가 아니라 "이 박스가 오래 안 맞춰졌다" 이고, 그때 기본값을 통째로
  # 활성화하면 **도는 서비스의 동작이 한 번에 바뀐다**(예: 역할 기본값·동시성·SMTP). 보고만 한다.
  if [ "$n_a" -gt "${HWAX_ENV_SYNC_MAX:-10}" ]; then
    echo "· ${DIR#"$ROOT/.."/} — 자동 후보가 $n_a 개(상한 ${HWAX_ENV_SYNC_MAX:-10}) — **사람이 봐야 한다**"
    echo "    한꺼번에 켜면 도는 서비스의 동작이 바뀐다. 목록만 낸다(적용은 HWAX_ENV_SYNC_MAX 를 올리거나 손으로)."
    for kv in "${add_active[@]}";    do echo "    ? ${kv%%=*}=${kv#*=}"; done
    for k in "${add_needval[@]}";  do echo "    ⚠ $k — 값을 정해야 한다"; done
    for k in "${add_optional[@]}"; do echo "    · $k — 선택 설정(예시로만 적혀 있다)"; done
    _rel="${DIR#"$ROOT/.."/}"
    hwax_skip_record "설정값 (상한)" "$_rel 의 새 설정 $n_a 개가 상한(${HWAX_ENV_SYNC_MAX:-10})을 넘어 적용하지 않았다" "HWAX_ENV_SYNC_MAX 를 올리거나 $_rel/.env 에 손으로 넣고 재실행"
    for k in "${add_needval[@]}";  do hwax_skip_record "설정값 $k" "값을 정해야 켜진다(비밀·자리표시자·빈 값, $_rel)" "$_rel/.env 에서 $k 값을 정하고 재실행"; done
    for k in "${add_optional[@]}"; do hwax_skip_record "선택설정 $k" "예시 주석으로만 들어갔다 — 필요하면 켠다($_rel)" "$_rel/.env 에서 $k 주석을 풀고 값을 정하고 재실행"; done
    NEEDS=$((NEEDS + n_a + n_c))
    continue
  fi
  [ "$n_a" = "0" ] && [ "$n_c" = "0" ] && continue
  rel="${DIR#"$ROOT/.."/}"
  echo "· $rel — 새 설정 $((n_a + n_c))개(자동 $n_a · 사람이 정할 것 $n_c)"
  for kv in "${add_active[@]}";    do echo "    + ${kv%%=*}"; done
  for k in "${add_needval[@]}";  do echo "    ⚠ $k — 값을 정해야 한다"; done
  for k in "${add_optional[@]}"; do echo "    · $k — 선택 설정(예시로만 적혀 있다)"; done
  for k in "${add_needval[@]}";  do hwax_skip_record "설정값 $k" "값을 정해야 켜진다(비밀·자리표시자·빈 값, $rel)" "$rel/.env 에서 $k 값을 정하고 재실행"; done
  for k in "${add_optional[@]}"; do hwax_skip_record "선택설정 $k" "예시 주석으로만 들어갔다 — 필요하면 켠다($rel)" "$rel/.env 에서 $k 주석을 풀고 값을 정하고 재실행"; done
  ADDED=$((ADDED + n_a)); NEEDS=$((NEEDS + n_c))
  [ "$CHECK" = "1" ] && continue

  cp -p "$EN" "$EN.bak-$TS" || { echo "  ✗ 백업 실패 — 건드리지 않는다" >&2; continue; }
  {
    printf '\n# ── env-sync %s — `.env.example` 에는 있는데 여기 없던 설정 ──\n' "$(date +%F)"
    for kv in "${add_active[@]}"; do printf '%s\n' "$kv"; done
    for kv in "${add_commented[@]}"; do
      printf '# %s   # ⚠ 값을 운영자가 정해야 한다(예시값은 그대로 쓰면 안 된다)\n' "$kv"
    done
  } >> "$EN"
  echo "    → 채웠다(백업 $(basename "$EN.bak-$TS"))"
done

echo "✓ env-sync: 대상 $PAIRS 쌍 · 자동 추가 $ADDED · 사람이 정할 것 $NEEDS"
if [ "$NEEDS" -gt 0 ]; then
  echo "  ⚠ 위 ⚠ 항목은 **주석으로** 넣었다 — 값을 채우고 해당 서비스를 재기동해야 반영된다." >&2
fi
if [ "$CHECK" = "1" ] && [ $((ADDED + NEEDS)) -gt 0 ]; then exit 1; fi
exit 0
