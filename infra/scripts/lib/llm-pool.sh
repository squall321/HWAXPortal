#!/usr/bin/env bash
# LLM 서버 풀(LLM_UPSTREAMS)의 규칙 한 곳 — 목록 검사 · 라우터 주소 · 지금 써야 할 주소 · 관리하는 사본 목록 · 사본 바꾸기(백업 먼저).
#
# 왜 — LLM 주소의 정본은 포털 infra/.env 의 LLM_BASE_URL 하나인데, 서비스마다 자기 .env 에 사본을 든다(에이전트 서버 VLLM_BASE_URL ·
# AIDataHub OPENAI_BASE_URL·LLM_BASE_URL · SignalForge · 허브 앱 · MXWhitePaper …). 설정 킷(apply-envs)은 없는 키만 더하므로 정본만
# 바꾸면 사본들은 조용히 옛 주소로 돈다(docs/llm-pool LP-D4 — 무음 결함 다섯째 '앱은 정상, env 만 빠졌다' 와 같은 꼴). 그래서 풀을 켜고
# 끌 때 사본을 함께 바꾸는 규칙을 여기 한 곳에 두고 update-all 1i · apply-envs 의 @FROM_RA:LLM_BASE_URL@ · update-sites 의 라우터 재기동
# 미룸 · §6 이 같은 규칙을 쓴다. 정의만 있다 — 소싱해도 아무 일도 하지 않는다.
#
#   . "$ROOT/infra/scripts/lib/llm-pool.sh"
#   hwax_llm_envv <파일> <키>               값 하나 — update-all 의 _envfile_value 와 **글자 단위로 같은 규칙**(마지막 활성 줄 · `export` 허용 ·
#                                            공백 뒤 `#` 주석 · 따옴표·CR 제거). 없거나 빈 값이면 빈 문자열. 라우터도 infra/.env 를 이 규칙으로 읽는다.
#   hwax_llm_pool_upstreams <infra.env>     LLM_UPSTREAMS 를 검사해 서버 주소를 한 줄에 하나 찍는다(끝 `/` 는 뗀다). 쉼표·공백으로 나눈다.
#       0 = 켜짐 · 1 = 없다(꺼짐) · 2 = 모양이 틀렸다 — 사유 한 줄을 찍는다. **하나라도 틀리면 줄 전체를 버린다**(반만 맞는 목록으로
#       라우터를 띄우거나 사본을 바꾸지 않게 — 부르는 쪽은 아무것도 바꾸지 않는다).
#   hwax_llm_router_url <infra.env>         라우터 주소 http://127.0.0.1:<LLM_ROUTER_PORT, 기본 9130>/v1 · 2 = 포트가 틀렸다(사유를 찍는다).
#   hwax_llm_router_health_url <infra.env>  라우터 /health 주소(같은 포트).
#   hwax_llm_router_health <health url>     라우터 /health 를 읽어 "<status> <올라온 서버> <전체> <도는 요청> <모델 같음>" 을 찍는다(모르는 칸은 ?).
#       0 = 라우터가 답했다(down 의 503 도 답이다) · 2 = 답이 없다 · JSON 이 아니다 · 라우터의 답이 아니다(upstreams_total 이 없다 —
#       같은 포트에 다른 것이 떠 있다).
#   hwax_llm_router_busy <health url>       라우터를 지나는 요청(inflight)이 **확실한** 양의 정수면 그 수를 찍고 0 · 0 이면 1 · 모르면 2.
#       LLM_ROUTER_RESTART_FORCE=1 이면 묻지 않고 1 — 사람이 끊기로 한 것이다. 부르는 쪽은 **0 일 때만** 미룬다 — 모르는데 미루면 죽은·
#       매달린 라우터를 영영 못 띄우고 새 코드를 영영 못 올린다(delib-busy 와 같은 규율).
#   hwax_llm_effective_url <infra.env> [직접 주소]   LLM 클라이언트가 **지금** 써야 할 주소 — 풀이 켜져 있고 라우터가 서버 하나 이상이
#       올라왔고 모델이 같다고 답하면 라우터 주소, 아니면 직접 주소(주지 않으면 infra/.env 의 LLM_BASE_URL). 0 = 찍었다 · 1 = 빈 값.
#       1i 가 사본을 라우터로 바꾸는 조건과 같다 — 라우터가 그렇게 답하지 않을 때 새로 더한 키만 라우터를 보지 않게(stderr 에 한 줄).
#   hwax_llm_router_recorded <포털 루트>    1i 가 마지막으로 사본에 적은 라우터 주소(infra/.state/llm-pool.router) — 0 = 찍었다 · 1 = 없다
#       (기록이 없거나 루프백 /v1 주소 모양이 아니다). 포트를 바꾸거나 포트 줄을 풀과 함께 지워도 옛 라우터를 가리키는 사본을 찾는 데 쓴다.
#   hwax_llm_router_record <포털 루트> <주소>   그 기록을 바꾼다(임시 파일 + 이름 바꾸기). 0 = 적었다 · 1 = 못 적었다.
#   hwax_llm_pool_copies <포털 루트>         관리하는 사본 — 줄마다 "<서비스>\t<리포 이름>\t<.env 상대경로>\t<키>". apply-envs 의 MAP 과 킷의
#       `<키>=@FROM_RA:LLM_BASE_URL@` 줄에서 유도하고(킷에 줄이 늘면 저절로 따라온다), 서비스 코드가 직접 읽는 키(_HWAX_LLM_EXTRA)를 더한다.
#   hwax_llm_pool_rewrite <포털 루트> <dry|write> <새 값> <관리하는 값…>
#       사본 가운데 지금 값(끝 `/` 무시)이 관리하는 값인 것만 새 값으로 바꾼다. 바꾸기 **전에** 그 파일을 **포털의** gitignore 된
#       `infra/.state/llm-pool-backups/<리포 이름>/<.env 상대경로>.<UTC 시각>[-n]` 으로 백업한다(디렉터리 700 · 파일 600 — 만드는 순간부터).
#       서비스 리포 안에 두지 않는다 — 그쪽은 gitignore 밖이라 추적 안 된 비밀 파일로 남고 deploy-all 의 `git stash push -u` 가 비밀째
#       stash 로 쓸어 간다(반대 검토 H1). 바꾸기는 원자적이다 — 같은 디렉터리의 임시 파일에 쓰고 fsync 한 뒤 이름을 바꾼다(심링크면 링크는 두고
#       가리키는 파일을 바꾼다 · 권한·소유자 그대로 — 소유자를 지킬 수 없으면 바꾸지 않는다). 그 값의 글자 말고는 파일을 한 바이트도 바꾸지
#       않는다(따옴표·`export`·줄 끝 주석·CRLF·다른 줄 그대로). 줄은 `\n` 으로만 나눈다(홀로 선 `\r` 은 줄바꿈이 아니다 — 읽는 쪽 sed 와 같다).
#       같은 파일에 키가 둘이면 백업은 한 번이다. 쓸 수 없는 파일(읽기 전용)은 백업도 만들지 않고, 쓰다 실패하면 만든 백업을 지운다.
#       줄마다 "<상태>\t<서비스>\t<리포 경로>\t<.env 상대경로>\t<키>\t<지금 값>\t<백업 경로>" — 상태는
#       changed(바꿨다) · would(dry — 바꿀 것이다) · same(이미 새 값) · foreign(관리하는 값이 아니다 — 사람이 적은 다른 주소, 그대로 둔다) ·
#       absent(파일·키가 없다) · error(못 바꿨다 — 지금 값 칸에 사유, 파일은 그대로). 리포가 없는 사본은 줄을 내지 않는다(이 박스 대상이
#       아니다). 리포는 apply-envs·update-all 의 find_repo 와 같은 순서로 찾는다(<포털 상위>/ → ~/Projects/ → ~/claude/). 줄은 파일마다
#       처리하는 대로 낸다 — 뒤 파일에서 죽어도 앞 파일의 결과는 남는다(부르는 쪽은 종료코드를 본다). 값은 바이트 그대로 다룬다(UTF-8 이
#       아닌 값도 어느 LANG 에서나 죽지 않는다).
#   hwax_llm_pool_at <포털 루트> <주소>      지금 그 주소를 가리키는 사본 수(끝 `/` 무시).
#
# ⚠ 0 아닌 값을 정상으로 돌려준다 — `set -e` 스크립트에서는 `_x="$(hwax_llm_… )" || _rc=$?` 로 받는다. 맨 문장이면 1·2 에서 조용히 끝난다.

# 서비스 코드가 직접 읽는데 킷의 @FROM_RA:LLM_BASE_URL@ 줄에는 없는 사본 — 코드로 확인한 것만 적는다(2026-10-15).
#   ai-data-hub    LLM_BASE_URL — api_server chat_svc.py 가 OPENAI_BASE_URL 보다 **먼저** 읽는다(데이터 챗). deploy/apptainer/.env 는
#                  start_api.sh(load_env)가 set -a 로 소싱해 프로세스 환경이 된다.
#   mx-white-paper LLM_BASE_URL — apps/api config.py 의 llm_base_url(pydantic env_file .env · 인스턴스는 --env-file .env).
#   HEAXHub 자신은 LLM_BASE_URL 을 읽지 않는다(자기 LLM 은 LLM_LOCAL_ENDPOINT — OpenAI /v1 이 아니다). 허브 앱은 HEAX_APP_LLM_BASE_URL
#   (킷 줄)을 LLM_BASE_URL 로 바꿔 받는다. HWAXRisk 는 LLM 을 직접 부르지 않는다(카드 대조는 에이전트 서버가 부른다).
_HWAX_LLM_EXTRA=(
  $'ai-data-hub\tAIDataHub\tdeploy/apptainer/.env\tLLM_BASE_URL'
  $'mx-white-paper\tMXWhitePaper\t.env\tLLM_BASE_URL'
)

hwax_llm_envv() {  # $1=파일 $2=키 — update-all _envfile_value 와 같은 줄(그 머리 주석의 까닭 그대로: LC_ALL=C · 주석을 벗긴 뒤에 공백)
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'
}

_hwax_llm_raw() {  # $1=파일 $2=키 — 같은 줄의 원문(주석·양끝 공백·CR 만 벗긴다 — 따옴표는 남긴다)
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '\r'
}

_hwax_llm_port() {  # $1=infra.env → 라우터 포트(기본 9130) · 2 = 틀렸다(사유)
  local p
  p="$(hwax_llm_envv "$1" LLM_ROUTER_PORT)"
  if [ -z "$p" ]; then printf '9130\n'; return 0; fi
  if [[ "$p" =~ ^[0-9]{1,5}$ ]] && [ "$((10#$p))" -ge 1 ] && [ "$((10#$p))" -le 65535 ]; then
    printf '%s\n' "$((10#$p))"; return 0
  fi
  printf "LLM_ROUTER_PORT 는 1~65535 의 수여야 한다: '%s'\n" "$p"; return 2
}

hwax_llm_router_url() {  # $1=infra.env
  local p rc=0
  p="$(_hwax_llm_port "$1")" || rc=$?
  if [ "$rc" != 0 ]; then printf '%s\n' "$p"; return 2; fi
  printf 'http://127.0.0.1:%s/v1\n' "$p"
}

hwax_llm_router_health_url() {  # $1=infra.env
  local u rc=0
  u="$(hwax_llm_router_url "$1")" || rc=$?
  if [ "$rc" != 0 ]; then printf '%s\n' "$u"; return 2; fi
  printf '%s/health\n' "${u%/v1}"
}

hwax_llm_pool_upstreams() {  # $1=infra.env
  local v raw u host port rport re out="" seen=" " n=0
  local -a items
  v="$(hwax_llm_envv "$1" LLM_UPSTREAMS)"
  [ -n "$v" ] || return 1
  # 따옴표 밖의 공백은 받지 않는다 — infra/.env 는 포털 start.sh(_common.sh)가 `set -a; . infra/.env` 로 소싱한다. `A=x y` 는 bash 에서
  # 'y' 를 명령으로 돌리고(그 대입은 남지 않는다) set -e 인 기동이 그 자리에서 죽는다. 이 독자는 공백을 나눔표로 읽어 맞는 목록으로 볼 것이라
  # 여기서 막지 않으면 update-all 은 초록인데 다음 포털 기동이 죽는다.
  raw="$(_hwax_llm_raw "$1" LLM_UPSTREAMS)"
  case "$raw" in
    \"*|\'*) ;;
    *[[:space:]]*) printf '%s\n' "LLM_UPSTREAMS 의 공백이 따옴표 밖에 있다 — infra/.env 는 포털 start.sh 가 bash 로 소싱해 공백 뒤가 명령이 되고 기동이 죽는다. 쉼표로만(공백 없이) 나누거나 값 전체를 큰따옴표로 감싼다"
                   return 2 ;;
  esac
  rport="$(_hwax_llm_port "$1")" || rport=""
  # 호스트 규칙은 1e(RA_HOST)와 같다 — IPv4 또는 라벨(영숫자, 안쪽 하이픈)을 점으로 이은 이름. 경로는 vLLM(OpenAI 호환)의 /v1 로 끝난다.
  # 계정(user@)·질의(?)·조각(#)·IPv6 은 받지 않는다.
  re='^https?://([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*)(:([0-9]{1,5}))?(/[A-Za-z0-9._~-]+)*/v1$'
  IFS=$', \t' read -ra items <<<"$v"
  for u in ${items[@]+"${items[@]}"}; do
    [ -n "$u" ] || continue
    while [ "${u%/}" != "$u" ]; do u="${u%/}"; done
    if ! [[ "$u" =~ $re ]]; then
      printf '%s\n' "LLM_UPSTREAMS 에 쓸 수 없는 주소가 있다: '$u' — vLLM 의 /v1 주소(http(s)://<호스트>[:<포트>]/…/v1)여야 한다(계정·질의·IPv6 은 받지 않는다)"
      return 2
    fi
    host="${BASH_REMATCH[1],,}"; port="${BASH_REMATCH[6]}"
    if [ -n "$port" ] && { [ "$((10#$port))" -lt 1 ] || [ "$((10#$port))" -gt 65535 ]; }; then
      printf '%s\n' "LLM_UPSTREAMS 의 포트가 1~65535 밖이다: '$u'"; return 2
    fi
    case "$host" in
      localhost|127.*)
        if [ -n "$rport" ] && [ -n "$port" ] && [ "$((10#$port))" = "$rport" ]; then
          printf '%s\n' "LLM_UPSTREAMS 가 라우터 자신을 가리킨다: '$u' — 서버(vLLM)의 /v1 주소를 적는다(라우터 주소는 update-all 이 사본에 적는다)"; return 2
        fi ;;
    esac
    case "$seen" in
      *" $u "*) printf '%s\n' "LLM_UPSTREAMS 에 같은 주소가 두 번 있다: '$u' — 서버마다 한 번씩 적는다"; return 2 ;;
    esac
    seen="$seen$u "; out="$out$u"$'\n'; n=$((n + 1))
  done
  if [ "$n" = 0 ]; then printf '%s\n' "LLM_UPSTREAMS 에 주소가 하나도 없다: '$v'"; return 2; fi
  printf '%s' "$out"
}

hwax_llm_router_health() {  # $1=health url
  local body rc=0
  # 로컬 health 다 — 운영자 셸의 http_proxy 를 타면 프록시가 이 박스의 루프백에 못 닿아 '모름' 이 된다(delib-busy 와 같다).
  body="$(curl -s --noproxy '*' -m 4 "$1" 2>/dev/null)" || rc=$?
  { [ "$rc" = 0 ] && [ -n "$body" ]; } || return 2
  B="$body" python3 - <<'PY'
import json, os, sys
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(2)
if not isinstance(h, dict) or "upstreams_total" not in h:
    sys.exit(2)                        # 라우터의 답이 아니다 — 같은 포트에 다른 것이 떠 있다
def n(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else "?"
models = h.get("models") if isinstance(h.get("models"), dict) else {}
match = models.get("match")
match = "true" if match is True else ("false" if match is False else "?")
status = h.get("status") if h.get("status") in ("ok", "degraded", "down") else "?"
print(status, n(h.get("upstreams_up")), n(h.get("upstreams_total")), n(h.get("inflight")), match)
PY
}

hwax_llm_router_busy() {  # $1=health url
  local h rc=0 st up tot inf m
  [ "${LLM_ROUTER_RESTART_FORCE:-0}" = 1 ] && return 1
  h="$(hwax_llm_router_health "$1")" || rc=$?
  [ "$rc" = 0 ] || return 2
  read -r st up tot inf m <<<"$h"
  case "${inf:-}" in ''|*[!0-9]*) return 2 ;; esac
  [ "$inf" -gt 0 ] || return 1
  printf '%s\n' "$inf"
}

hwax_llm_effective_url() {  # $1=infra.env [$2=직접 주소]
  local direct rurl h rc=0 st up tot inf m
  if [ "$#" -ge 2 ]; then direct="$2"; else direct="$(hwax_llm_envv "$1" LLM_BASE_URL)"; fi
  if hwax_llm_pool_upstreams "$1" >/dev/null && rurl="$(hwax_llm_router_url "$1")"; then
    h="$(hwax_llm_router_health "$(hwax_llm_router_health_url "$1")")" || rc=$?
    read -r st up tot inf m <<<"$h"
    if [ "$rc" = 0 ] && [[ "${up:-}" =~ ^[0-9]+$ ]] && [ "$up" -ge 1 ] && [ "${m:-}" = true ]; then
      printf '%s\n' "$rurl"; return 0
    fi
    printf '%s\n' "   · LLM 풀이 켜져 있는데 라우터($rurl)가 올라온 서버와 같은 모델을 답하지 않는다 — 직접 주소를 쓴다(라우터가 그렇게 답하면 update-all 1i 가 사본을 라우터로 바꾼다)" >&2
  fi
  [ -n "$direct" ] || return 1
  printf '%s\n' "$direct"
}

hwax_llm_router_recorded() {  # $1=포털 루트
  local v
  v="$(head -n 1 "$1/infra/.state/llm-pool.router" 2>/dev/null)" || v=""
  [[ "$v" =~ ^http://127\.0\.0\.1:[0-9]{1,5}/v1$ ]] || return 1
  printf '%s\n' "$v"
}

hwax_llm_router_record() {  # $1=포털 루트 $2=라우터 주소
  local f="$1/infra/.state/llm-pool.router" tmp=""
  if mkdir -p "${f%/*}" 2>/dev/null && tmp="$(mktemp "$f.XXXXXX" 2>/dev/null)" && printf '%s\n' "$2" > "$tmp" && mv -f "$tmp" "$f"; then
    return 0
  fi
  [ -n "$tmp" ] && rm -f "$tmp"
  return 1
}

hwax_llm_pool_copies() {  # $1=포털 루트
  local root="$1" svc repo rel key kit x
  {
    while read -r svc repo rel; do
      kit="$root/infra/env-kits/$svc.env"
      [ -f "$kit" ] || continue
      while read -r key; do
        [ -n "$key" ] && printf '%s\t%s\t%s\t%s\n' "$svc" "$repo" "$rel" "$key"
      done < <(sed -n -E 's/^([A-Z_][A-Z0-9_]*)=@FROM_RA:LLM_BASE_URL@[[:space:]]*$/\1/p' "$kit")
    done < <(sed -n -E '/^declare -A MAP=\(/,/^\)/ s/^[[:space:]]*\[([A-Za-z0-9_-]+)\]="([^":]+):([^"]+)".*$/\1 \2 \3/p' \
               "$root/infra/env-kits/apply-envs.sh" 2>/dev/null)
    for x in "${_HWAX_LLM_EXTRA[@]}"; do printf '%s\n' "$x"; done
  } | LC_ALL=C sort -u
}

hwax_llm_pool_rewrite() {  # $1=포털 루트 $2=dry|write $3=새 값 $4…=관리하는 값
  local root="$1" mode="$2" new="$3"
  shift 3
  case "$mode" in dry|write) ;; *) echo "hwax_llm_pool_rewrite: dry 또는 write 다 — '$mode'" >&2; return 2 ;; esac
  [ -n "$new" ] || { echo "hwax_llm_pool_rewrite: 새 값이 비었다 — 사본을 빈 주소로 바꾸지 않는다" >&2; return 2; }
  HWAX_LLM_COPIES="$(hwax_llm_pool_copies "$root")" HWAX_LLM_ROOT="$root" HWAX_LLM_MODE="$mode" HWAX_LLM_NEW="$new" \
    python3 - "$@" <<'PY'
import os, re, stat, sys, tempfile, time
from pathlib import Path

# 값은 **바이트로** 다룬다 — 사본에 UTF-8 이 아닌 값이 하나라도 있으면 str 로 풀어 찍다가 ko_KR.UTF-8 에서 UnicodeEncodeError 로
# 죽었다(그때는 이미 파일을 다 쓴 뒤라 바꾼 줄이 하나도 안 나왔다 — 반대 검토 L4). 환경·인자도 바이트로 받고, 출력도 바이트로 낸다.
root = Path(os.environ["HWAX_LLM_ROOT"]).resolve()
mode, new = os.environ["HWAX_LLM_MODE"], os.environb[b"HWAX_LLM_NEW"]
norm = lambda s: s.rstrip(b"/")
managed = {norm(os.fsencode(m)) for m in sys.argv[1:] if m.strip()}
home = Path(os.environ.get("HOME") or "/nonexistent")
bases = (root.parent, home / "Projects", home / "claude")      # find_repo 와 같은 순서
bkroot = root / "infra/.state/llm-pool-backups"               # 포털의 gitignore 된 상태 디렉터리 — 서비스 리포 안에 두지 않는다(H1)
out = sys.stdout.buffer


def repo_dir(name):
    for b in bases:
        if (b / name).is_dir():
            return b / name
    return None


def enc(x) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, Path):
        return os.fsencode(x)
    return str(x).encode("utf-8", "surrogateescape")          # 사유 글은 UTF-8 로(스크립트의 다른 글과 같게) — LANG 과 무관하다


def emit(rows):
    """파일마다 처리하는 대로 낸다 — 뒤 파일에서 죽어도 앞 파일의 결과(바꿨다 · 백업 경로)는 부르는 쪽에 남는다."""
    for r in rows:
        out.write(b"\t".join(enc(x) for x in r) + b"\n")
    out.flush()


# update-all _envfile_value 와 같은 규칙 — 줄 머리([[:space:]]*, export 허용), 공백 뒤 # 주석, 양끝 공백, 따옴표·CR
WS = rb" \t\v\f\r"
def value_of(body: bytes) -> bytes:
    v = re.sub(rb"[" + WS + rb"]+#.*$", b"", body)
    return v.strip(WS).replace(b'"', b"").replace(b"'", b"").replace(b"\r", b"")


def split_lines(data: bytes) -> list:
    """`\\n` 으로만 나눈다 — bytes.splitlines 는 홀로 선 `\\r` 에서도 나눠, 읽는 쪽(sed — 줄은 `\\n` 뿐)이 보지 않는 줄을 고쳤다(L5)."""
    parts = data.split(b"\n")
    return [p + b"\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def backup(repo: str, rel: str, data: bytes) -> Path:
    """<bkroot>/<리포>/<상대경로>.<UTC>[-n] — 디렉터리 700 · 파일 600(만드는 순간부터). 같은 초에 다시 돌아도 앞 백업을 덮지 않는다."""
    stem = bkroot / repo / rel
    old = os.umask(0o077)                                      # 새로 만드는 디렉터리는 전부 700(중간 디렉터리까지)
    try:
        stem.parent.mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(old)
    os.chmod(bkroot, 0o700)                                    # 먼저 있던 백업 뿌리도 700 — 그 아래 전부가 이 하나로 닫힌다
    for k in range(100):
        cand = stem.with_name(f"{stem.name}.{ts}" + (f"-{k}" if k else ""))
        try:
            fd = os.open(cand, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except OSError:
            cand.unlink(missing_ok=True)
            raise
        return cand
    raise OSError(0, "이름이 다 찼다")


def replace(path: Path, content: bytes) -> None:
    """원자적으로 바꾼다(L3) — 가리키는 파일 옆의 임시 파일에 쓰고 fsync 한 뒤 이름을 바꾼다. 제자리 쓰기는 디스크가 차면 반쯤 잘린 .env 를
    남겼다. 심링크면 링크는 그대로 두고 가리키는 파일을 바꾼다. 권한·소유자는 원본 그대로 — 소유자를 지킬 수 없으면(남의 파일) 바꾸지 않는다."""
    real = Path(os.path.realpath(path))
    st = real.stat()
    fd, tmp = tempfile.mkstemp(dir=real.parent, prefix=f"{real.name}.tmp-")   # 같은 디렉터리 — 이름 바꾸기가 원자적인 자리
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chown(tmp, st.st_uid, st.st_gid)                    # 남의 소유면 PermissionError — 아래에서 '그대로다' 로 끝난다
        os.chmod(tmp, stat.S_IMODE(st.st_mode))
        os.replace(tmp, real)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:                                                       # 이름 바꾸기를 디스크에 — 실패해도 파일은 이미 새 내용이다
        dfd = os.open(real.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


groups = {}                                                   # 파일 → [(서비스, 리포, 리포 이름, 상대경로, 키)] — 백업은 파일마다 한 번
for ln in os.environ.get("HWAX_LLM_COPIES", "").splitlines():
    parts = ln.split("\t")
    if len(parts) != 4:
        continue
    svc, repo, rel, key = parts
    d = repo_dir(repo)
    if d is None:
        continue                                              # 이 박스에 그 리포가 없다 — 대상 아님
    groups.setdefault(d / rel, []).append((svc, d, repo, rel, key))

ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
for path, entries in groups.items():
    if not path.is_file():
        emit([["absent", s, d, r, k, b"", b""] for s, d, _, r, k in entries])
        continue
    try:
        data = path.read_bytes()
    except OSError as e:
        emit([["error", s, d, r, k, f"읽지 못했다({e.strerror})", b""] for s, d, _, r, k in entries])
        continue
    lines = split_lines(data)
    edits, mine = {}, []
    for svc, d, repo, rel, key in entries:
        pat = re.compile(rb"^[" + WS + rb"]*(?:export[" + WS + rb"]+)?" + re.escape(key.encode()) + rb"=")
        idx = [i for i, l in enumerate(lines) if pat.match(l)]
        if not idx:
            mine.append(["absent", svc, d, rel, key, b"", b""])
            continue
        i = idx[-1]                                            # 읽는 쪽(tail -1)과 같은 줄을 고친다
        line = lines[i]
        head = pat.match(line).end()
        body = line[head:]
        eol = b""
        for e in (b"\r\n", b"\n", b"\r"):                      # 끝의 `\r` 만 남은 줄은 파일 끝의 마지막 줄뿐이다(줄은 `\n` 으로만 나눴다)
            if body.endswith(e):
                eol, body = e, body[: -len(e)]
                break
        cur = value_of(body)
        shown = cur.replace(b"\t", b" ")                       # 출력 칸은 탭으로 갈린다 — 값 속 탭이 칸을 밀지 않게(보여 주기만)
        if cur and norm(cur) == norm(new):
            mine.append(["same", svc, d, rel, key, shown, b""])
            continue
        if not cur or norm(cur) not in managed:
            mine.append(["foreign", svc, d, rel, key, shown, b""])  # 사람이 일부러 적은 다른 주소(또는 빈 값) — 건드리지 않는다
            continue
        # 값의 글자만 바꾼다 — 앞뒤 공백·감싼 따옴표·줄 끝 주석·줄 끝은 그대로
        cm = re.search(rb"[ \t\v\f]+#.*$", body)
        comment = body[cm.start():] if cm else b""
        core = body[: cm.start()] if cm else body
        lead = core[: len(core) - len(core.lstrip(b" \t"))]
        core = core[len(lead):]
        stripped = core.rstrip(b" \t")
        trail, core = core[len(stripped):], stripped
        q = core[:1] if len(core) >= 2 and core[:1] in (b'"', b"'") and core[-1:] == core[:1] else b""
        edits[i] = line[:head] + lead + q + new + q + trail + comment + eol
        mine.append(["changed" if mode == "write" else "would", svc, d, rel, key, shown, b""])
    if edits and mode == "write":
        repo0, rel0 = entries[0][2], entries[0][3]                # 한 파일의 키들은 같은 리포 · 같은 경로다
        why, bak = None, None
        if not os.access(os.path.realpath(path), os.W_OK):     # 이름 바꾸기는 디렉터리 권한만 본다 — 읽기 전용 파일도 갈아 끼울 수 있어 먼저 본다
            why = "쓸 수 없는 파일이다(권한) — 백업도 만들지 않았다. 파일은 그대로다"
        else:
            try:
                bak = backup(repo0, rel0, data)
            except OSError as e:
                why = f"백업을 만들지 못했다({e.strerror or e}) — 파일은 그대로다"
        if bak is not None:
            try:
                replace(path, b"".join(edits.get(i, l) for i, l in enumerate(lines)))
            except OSError as e:
                why = f"쓰지 못했다({e.strerror or e}) — 파일은 그대로다"
                try:
                    bak.unlink()                               # 쓰지 못한 바꾸기의 백업은 남기지 않는다(비밀 사본이 하나 더 남을 뿐이다)
                    why += "(만든 백업은 지웠다)"
                except OSError:
                    why += f"(백업 {bak} 이 남았다)"
                bak = None
        if bak is None:
            mine = [["error", *r[1:5], why, b""] if r[0] == "changed" else r for r in mine]
        else:
            mine = [[*r[:6], bak] if r[0] == "changed" else r for r in mine]
    emit(mine)
PY
}

hwax_llm_pool_at() {  # $1=포털 루트 $2=주소
  hwax_llm_pool_rewrite "$1" dry "$2" "$2" | awk -F'\t' '$1 == "same" { n++ } END { print n + 0 }'
}
