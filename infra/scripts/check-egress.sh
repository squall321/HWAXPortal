#!/usr/bin/env bash
# 이 박스에서 인터넷으로 무엇이 실제로 나가는지 재는 진단 스크립트 — 웹 검색 기능 도입의 0단계.
#
# 왜 필요한가. dev 박스는 인터넷 직결이고 TLS 가로채기도 없다(실측 2026-08-08). 반면 cae00 은
# 사내 프록시 뒤에 있고, 과거 공개 레지스트리 접근이 MITM 으로 깨져 '네트워크를 안 쓰는' 우회로
# 넘어갔다. 웹 검색은 그 우회가 불가능하다 — 그러니 계획을 세우기 전에 그 박스에서 실제로
# 무엇이 되고 무엇이 안 되는지를 숫자로 알아야 한다.
#
# 특히 세 가지를 구분해서 판정한다. 이 셋은 서로 다른 문제이고 처방도 다르다.
#   (1) 연결 자체가 되는가            — 프록시 CONNECT 가 열려 있는가
#   (2) TLS 인증서가 검증되는가       — MITM 재서명이면 사내 CA 를 신뢰해야 한다
#   (3) 컨테이너 안에서도 되는가      — 앱은 Apptainer 안에서 돈다. 호스트 CA 신뢰가 자동 상속되지 않는다
#
# 사용법
#   check-egress.sh              # 요약 진단
#   check-egress.sh --sif <경로> # 그 SIF 안에서도 같은 검사(앱 런타임 기준 판정)
#   check-egress.sh --json       # 기계 판독용
#   check-egress.sh --internal   # 내부 목적지가 NO_PROXY 에 있는지만(네트워크를 건드리지 않는다 — update-all §6 이 부른다)
set -uo pipefail

TIMEOUT="${EGRESS_TIMEOUT:-8}"
SIF=""
JSON=0
INTERNAL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sif) SIF="${2:?--sif 뒤에 SIF 경로}"; shift 2 ;;
    --json) JSON=1; shift ;;
    --internal) INTERNAL=1; shift ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

C_OK=$'\033[32m'; C_NG=$'\033[31m'; C_WARN=$'\033[33m'; C_DIM=$'\033[2m'; C_0=$'\033[0m'
{ [ -t 1 ] && [ "$JSON" = 0 ]; } || { C_OK=; C_NG=; C_WARN=; C_DIM=; C_0=; }
ok()   { [ "$JSON" = 1 ] || printf '  %s✔%s %s\n' "$C_OK" "$C_0" "$1"; }
ng()   { [ "$JSON" = 1 ] || printf '  %s✘%s %s\n' "$C_NG" "$C_0" "$1"; }
warn() { [ "$JSON" = 1 ] || printf '  %s!%s %s\n' "$C_WARN" "$C_0" "$1"; }
dim()  { [ "$JSON" = 1 ] || printf '    %s%s%s\n' "$C_DIM" "$1" "$C_0"; }
sec()  { [ "$JSON" = 1 ] || printf '\n%s\n' "$1"; }

# 검사 대상 — 검색 백엔드 후보와 본문 수집 대상을 실제로 찔러 본다.
# 이름|URL|용도
TARGETS='
duckduckgo|https://html.duckduckgo.com/html/?q=test|검색(무키·폴백 후보)
brave-api|https://api.search.brave.com/res/v1/web/search|검색(유료 API 후보)
google|https://www.google.com|일반 도달성 기준선
wikipedia|https://en.wikipedia.org|본문 수집 대상
arxiv|https://arxiv.org|논문 수집 대상
pypi|https://pypi.org/simple/|패키지(빌드 의존)
'

RES_JSON=""
add_json() { RES_JSON="${RES_JSON}${RES_JSON:+,}{\"name\":\"$1\",\"code\":\"$2\",\"verified\":$3}"; }

# ── 이 박스가 실제로 부르는 **내부** 목적지 — 프록시를 타면 안 되는 곳(9차 요청 §4-(4)) ─────────────────────
# 종전엔 NO_PROXY 에 루프백 둘만 있는지 봤다. 그런데 사고는 다른 서버에서 났다 — RA 호출이 사내 프록시를 타 상대의 IP 허용목록에
# 걸려 사람별 위임이 403 이었다(2026-10-03 cae00). 목적지는 **리포가 아는 설정에서 유도한다**(주소를 여기 적지 않는다):
#   infra/.env 의 RA_HOST·ARP_HOST · routes(.local).env 의 원격 호스트 · backend/.env 의 TESTSCOPE_BASE_URL.
# 출력에는 주소가 아니라 **어느 설정인지**만 낸다 — 이 출력은 update-all 로그에 그대로 남는다.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# update-all 의 _envfile_value 와 같은 규칙(인라인 주석·따옴표·CR 을 벗기고 마지막 줄이 이긴다) — ste-doctor.sh 의 envv 와 같은 한 줄이다.
envv() { sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=//p" "$2" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'; }
_url_host() {  # URL → 호스트(소문자). 스킴·계정·포트·경로를 벗긴다
  local u="${1#*://}"; u="${u%%/*}"; u="${u##*@}"; u="${u%%:*}"
  printf '%s' "${u,,}"
}
_url_port() {  # URL → 적힌 포트(없으면 빈 값). 스킴의 기본 포트(http 80 · https 443)는 빈 값이다 — httpx 가 '포트 없음' 으로 다룬다
  local scheme="" u="$1" port=""
  case "$u" in *://*) scheme="${u%%://*}"; u="${u#*://}" ;; esac
  u="${u%%/*}"; u="${u##*@}"
  if [[ "$u" =~ :([0-9]+)$ ]]; then port="${BASH_REMATCH[1]}"; fi
  case "${scheme,,}:$port" in http:80|https:443) port="" ;; esac
  printf '%s' "$port"
}
# 포트는 그 설정이 주소에 적은 것만 안다(라우트·TESTSCOPE_BASE_URL). RA_HOST·ARP_HOST 는 포트가 없다 — update-all 1e 가 RA_HOST 한 줄에서
# :3000 과 :3002 를 함께 만든다. 같은 호스트가 다른 포트로 또 나오면 포트를 비운다 — 포트 하나를 적은 NO_PROXY 항목으로는 둘을 못 덮는다.
internal_dests() {  # "<이름>|<호스트>|<포트>" 줄들. 루프백은 뺀다(아래에서 따로 본다). 같은 호스트는 먼저 나온 이름 하나로.
  local k h f line _rp _v
  declare -A _route=() _rport=() _seen=() _port=()
  local -a _order=() _hosts=()
  _add() { case "$2" in ''|localhost|127.*|0.0.0.0|::1|\[*) return 0 ;; esac
           if [ -n "${_seen[$2]:-}" ]; then [ "${_port[$2]}" = "${3:-}" ] || _port[$2]=""; return 0; fi
           _seen[$2]="$1"; _port[$2]="${3:-}"; _hosts+=("$2"); }
  for k in RA_HOST ARP_HOST; do h="$(envv "$k" "$ROOT/infra/.env")"; _add "$k" "${h,,}"; done
  # 라우트 — 추적 파일 위에 박스 오버레이가 같은 키를 덮는다(gen-nginx-conf.sh 와 같다). 빈 값은 '이 박스에서 끔' 이다.
  _rp="$(envv ROUTES_PATH "$ROOT/infra/.env")"
  for f in "$ROOT/backend/${_rp:-config/routes.env}" "$ROOT/backend/config/routes.local.env"; do
    [ -f "$f" ] || continue
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line#"${line%%[![:space:]]*}"}"
      case "$line" in ''|\#*) continue ;; *=*) ;; *) continue ;; esac
      k="${line%%=*}"; k="${k%"${k##*[![:space:]]}"}"
      [ -n "${_route[$k]+x}" ] || _order+=("$k")
      _v="$(printf '%s' "${line#*=}" | tr -d '[:space:]')"
      _route[$k]="$(_url_host "$_v")"; _rport[$k]="$(_url_port "$_v")"
    done < "$f"
  done
  for k in ${_order[@]+"${_order[@]}"}; do _add "라우트 $k" "${_route[$k]}" "${_rport[$k]}"; done
  h="$(envv TESTSCOPE_BASE_URL "$ROOT/backend/.env")"; [ -n "$h" ] && _add TESTSCOPE_BASE_URL "$(_url_host "$h")" "$(_url_port "$h")"
  for h in ${_hosts[@]+"${_hosts[@]}"}; do printf '%s|%s|%s\n' "${_seen[$h]}" "$h" "${_port[$h]}"; done
  return 0
}
_ip4() {  # 점 네 칸 십진 주소 → 정수. 아니면 실패
  local a b c d x
  IFS=. read -r a b c d x <<<"$1"
  [ -z "${x:-}" ] || return 1
  for x in "${a:-}" "${b:-}" "${c:-}" "${d:-}"; do [[ "$x" =~ ^[0-9]{1,3}$ ]] && [ "$((10#$x))" -le 255 ] || return 1; done
  printf '%s' $(( (10#$a << 24) | (10#$b << 16) | (10#$c << 8) | 10#$d ))
}
# 초록이 거짓이면 이 점검은 없느니만 못하다 — 이 NO_PROXY 를 물려받는 서비스(포털·게이트웨이·에이전트서버)가 부를 때 쓰는
# **httpx 가 읽는 대로만** 덮인 것으로 본다. 종전엔 "curl·httpx·requests 가 받는 모양을 넓게" 인정해 대역 안의 주소를 덮였다고
# 봤는데, httpx 0.28.1 은 대역을 대역으로 읽지 않는다(9차 요청 §5 실측, docs/change-request-8-10 D-9) — 운영자 셸의 NO_PROXY 가
# /24 인 박스에서 그 호출은 여전히 프록시로 새는데 이 점검만 초록이었다. curl 은 대역·공백을 읽지만 서비스는 curl 로 부르지 않는다.
#   덮는다     — 같은 주소·이름 · `*` 하나(전부) · 도메인 꼬리(`corp` 는 자신과 하위, `.corp` 는 하위만 — 점 경계에서만).
#                포트가 붙은 항목(`호스트:포트`)은 **그 포트로 가는 호출만** 덮는다 — 목적지의 포트를 모르거나 다르면 덮지 않는다.
#   덮지 않는다 — 대역 `a.b.c.d/n`(슬래시 앞 `a.b.c.d` 한 주소로만 읽힌다) · `*.corp`(별표를 글자로 읽어 아무것과도 안 맞는다) ·
#                공백으로만 나눈 항목(쉼표로만 나눈다 — `a b` 는 통째로 한 항목이다).
# 주소인 호스트는 꼬리로 맞추지 않는다(httpx 는 `113.10` 같은 항목도 꼬리로 받지만 일부러 적을 모양이 아니다 — 틀려도 '빠졌다' 쪽이다).
_np_entries() {  # $1=NO_PROXY 목록 → 항목을 줄마다(소문자, 쉼표로 나누고 둘레 공백을 뗀다 — httpx 가 나누는 방식 그대로)
  local e
  local -a _es=()
  IFS=',' read -ra _es <<<"${1,,}"         # read 로 쪼갠다 — 따옴표 없는 for 는 `*` 를 파일 이름으로 푼다
  for e in ${_es[@]+"${_es[@]}"}; do
    e="${e#"${e%%[![:space:]]*}"}"; e="${e%"${e##*[![:space:]]}"}"
    [ -n "$e" ] && printf '%s\n' "$e"
  done
  return 0
}
np_covers() {  # $1=호스트 $2=NO_PROXY 목록 $3=목적지 포트(모르면 빈 값) → 0 이면 프록시를 타지 않는다
  local h="${1,,}" e
  while IFS= read -r e; do
    [ "$e" = "*" ] && return 0
    case "$e" in
      \**) continue ;;
      */*) [ "$h" = "${e%%/*}" ] && return 0; continue ;;
    esac
    if [[ "$e" =~ ^[^:]+:([0-9]+)$ ]]; then
      [ -n "${3:-}" ] && [ "${BASH_REMATCH[1]}" = "$3" ] || continue
      e="${e%:*}"
    fi
    [ "$h" = "$e" ] && return 0
    _ip4 "$h" >/dev/null || { [[ "$h" == *".${e#.}" ]] && return 0; }
  done < <(_np_entries "$2")
  return 1
}
# 덮지 못하는 모양의 항목이 몇 개인가 — 빠졌다고만 하면 운영자는 NO_PROXY 에 대역이 있는 것을 보고 점검이 틀렸다고 읽는다.
# 값은 내지 않는다(주소다 — 이 출력은 update-all 로그에 남는다). `/32` 는 그 주소 하나로 읽히므로 세지 않는다.
np_dead_note() {  # $1=NO_PROXY 목록 → 안내 한 구절(없으면 빈 값)
  local e n=0
  while IFS= read -r e; do
    case "$e" in
      \*) ;;
      \**|*[[:space:]]*) n=$((n + 1)) ;;
      */32) ;;
      */*) _ip4 "${e%%/*}" >/dev/null && n=$((n + 1)) ;;
    esac
  done < <(_np_entries "$1")
  [ "$n" -gt 0 ] && printf 'NO_PROXY 의 항목 %s개는 httpx 가 읽지 못하는 모양이다(대역 a.b.c.d/n · *.도메인 · 공백으로 나눈 항목) — 쉼표로 나눠 주소·이름을 그대로 적는다' "$n"
  return 0
}
internal_missing() {  # $1=NO_PROXY 목록 → 목록이 덮지 못하는 내부 목적지의 이름(", " 로 이음). 다 덮이면 빈 값.
  local name host port out=""
  while IFS='|' read -r name host port; do
    [ -n "$host" ] || continue
    np_covers "$host" "$1" "$port" || out="${out:+$out, }$name"
  done < <(internal_dests)
  printf '%s' "$out"
}

PROXY="${HTTPS_PROXY:-${https_proxy:-${HTTP_PROXY:-${http_proxy:-}}}}"
# NO_PROXY 는 **소문자를 먼저** 읽는다 — 파이썬(urllib·httpx)과 curl 이 그렇게 읽고, 파이썬은 '있지만 빈' 소문자가 대문자를 지운다
# (그래서 `:-` 가 아니라 `-` 다). 종전엔 대문자를 먼저 읽어, 손으로 돌릴 때 두 값이 다르면 서비스가 읽는 것과 다른 목록으로 판정했다.
# update-all 안에서는 두 철자를 같게 맞춰 두므로 그 게이트의 출력은 달라지지 않는다. 값은 찍지 않는다.
NP_EFF="${no_proxy-${NO_PROXY-}}"
NP_SPLIT=""
if [ -n "${NO_PROXY+x}" ] && [ -n "${no_proxy+x}" ] && [ "$NO_PROXY" != "$no_proxy" ]; then
  NP_SPLIT="NO_PROXY 와 no_proxy 가 다르다 — 파이썬·curl 이 읽는 소문자(no_proxy)로 판정한다. 둘을 같게 맞춘다"
fi
if [ "$INTERNAL" = 1 ]; then
  # update-all §6 이 매 실행 부른다 — 네트워크를 건드리지 않고(멈출 일이 없다), 프록시·NO_PROXY 값도 찍지 않는다(프록시 주소에
  # 계정이 섞여 있을 수 있다). 종료코드: 0 = 볼 것이 없거나 전부 덮였다 · 1 = 덮이지 않은 목적지가 있다(이름을 stdout 한 줄로).
  if [ -z "$PROXY" ]; then echo "프록시 환경변수 없음 — 직결 구성이라 볼 것이 없다"; exit 0; fi
  [ -z "$NP_SPLIT" ] || echo "$NP_SPLIT" >&2      # stdout 은 한 줄이다(update-all 이 그대로 싣는다) — 이 말은 stderr 로
  _miss="$(internal_missing "$NP_EFF")"
  # 읽지 못하는 항목은 덮였든 빠졌든 같은 줄 끝에 붙인다(stdout 은 한 줄이다 — update-all 이 그대로 싣는다). 종료코드는 바꾸지 않는다.
  _note="$(np_dead_note "$NP_EFF")"; _note="${_note:+ ($_note)}"
  if [ -n "$_miss" ]; then echo "$_miss$_note"; exit 1; fi
  _n="$(internal_dests | grep -c . || true)"
  if [ "${_n:-0}" = 0 ]; then echo "이 박스의 설정에 다른 서버의 내부 목적지가 없다$_note"; else echo "내부 목적지 ${_n}곳이 전부 NO_PROXY 에 있다$_note"; fi
  exit 0
fi

sec "1) 프록시 환경"
if [ -n "$PROXY" ]; then
  ok "프록시 설정됨: $PROXY"
  NP="$NP_EFF"
  [ -z "$NP_SPLIT" ] || warn "$NP_SPLIT"
  if [ -n "$NP" ]; then
    ok "NO_PROXY: $NP"
    # 내부 목적지가 프록시로 새면 사내 LLM·게이트웨이 호출이 통째로 깨진다(실사고 기록 있음).
    for h in 127.0.0.1 localhost; do
      case ",$NP," in *",$h,"*) ;; *) warn "NO_PROXY 에 $h 없음 — 내부 호출이 프록시로 샐 수 있다" ;; esac
    done
    # 다른 서버의 내부 목적지(RA·ARP·라우트의 원격 호스트·TestScope) — 이름만 낸다
    _miss="$(internal_missing "$NP")"
    [ -n "$_miss" ] && warn "NO_PROXY 에 없는 내부 목적지: $_miss — 그 호출이 프록시로 샌다(상대의 IP 허용목록에 걸리면 403)"
    _note="$(np_dead_note "$NP")"
    [ -n "$_note" ] && warn "$_note"
  else
    warn "NO_PROXY 없음 — 내부 IP 요청도 프록시로 흘러 Connection error 가 난다(cae00 실사고 패턴)"
  fi
else
  ok "프록시 환경변수 없음 — 직결 구성"
fi

sec "2) 도달성과 TLS 검증 (호스트)"
[ "$JSON" = 1 ] || printf '   %-12s %-6s %-8s %s\n' 대상 코드 TLS검증 비고
printf '%s' "$TARGETS" | while IFS='|' read -r name url note; do
  [ -n "$name" ] || continue
  code=$(curl -s -o /dev/null -m "$TIMEOUT" -w '%{http_code}' "$url" 2>/dev/null)
  # -k 로는 되는데 그냥은 안 되면 = 인증서 검증 실패(= MITM 재서명인데 CA 미신뢰).
  code_k=$(curl -sk -o /dev/null -m "$TIMEOUT" -w '%{http_code}' "$url" 2>/dev/null)
  if [ "$code" != "000" ]; then verified=true; mark="${C_OK}검증OK${C_0}"
  elif [ "$code_k" != "000" ]; then verified=false; mark="${C_NG}검증실패${C_0}"
  else verified=false; mark="${C_NG}연결불가${C_0}"; fi
  [ "$JSON" = 1 ] || printf '   %-12s %-6s %-17s %s\n' "$name" "${code:-000}" "$mark" "$note"
  echo "$name|${code:-000}|$verified" >> "${TMP_RES:-/dev/null}"
done

# 위 while 은 서브셸이라 변수를 못 물고 나온다 — 판정에 필요한 값만 다시 계산한다.
BASE_CODE=$(curl -s -o /dev/null -m "$TIMEOUT" -w '%{http_code}' https://www.google.com 2>/dev/null)
BASE_CODE_K=$(curl -sk -o /dev/null -m "$TIMEOUT" -w '%{http_code}' https://www.google.com 2>/dev/null)

sec "3) TLS 가로채기(MITM) 판정"
ISSUER=$(echo | timeout "$TIMEOUT" openssl s_client -connect www.google.com:443 \
         -servername www.google.com 2>/dev/null | sed -n 's/^issuer=//p' | head -1)
if [ -z "$ISSUER" ]; then
  ng "인증서를 가져오지 못했습니다 — 연결 자체가 막혀 있거나 프록시가 CONNECT 를 거부합니다"
  MITM="unknown"
elif printf '%s' "$ISSUER" | grep -qiE "google trust|digicert|let's encrypt|globalsign|sectigo|amazon"; then
  ok "공인 CA 발급 — TLS 가로채기 없음"
  dim "issuer: $ISSUER"
  MITM="no"
else
  warn "사내 CA 로 재서명됨 — TLS 가로채기 있음"
  dim "issuer: $ISSUER"
  MITM="yes"
fi

if [ "$MITM" = "yes" ] && [ "$BASE_CODE" = "000" ] && [ "$BASE_CODE_K" != "000" ]; then
  ng "재서명 CA 가 신뢰되지 않습니다 — HTTPS 요청이 전부 검증 실패합니다"
  dim "처방: 사내 루트 CA 를 /usr/local/share/ca-certificates/ 에 넣고 update-ca-certificates,"
  dim "      그리고 런타임에 REQUESTS_CA_BUNDLE / SSL_CERT_FILE / NODE_EXTRA_CA_CERTS 를 지정"
  dim "      (검증을 끄는 것은 금지 — 사내망에서 MITM 을 무조건 신뢰하는 셈이 된다)"
fi

sec "4) 컨테이너 안에서의 도달성"
if [ -z "$SIF" ]; then
  dim "--sif <경로> 를 주면 앱 런타임(Apptainer) 기준으로도 검사합니다."
  dim "호스트에서 되는 것이 컨테이너에서도 된다는 보장은 없습니다 — CA 저장소가 이미지 안에 따로 있습니다."
elif [ ! -f "$SIF" ]; then
  ng "SIF 없음: $SIF"
elif ! command -v apptainer >/dev/null; then
  ng "apptainer 명령이 없어 컨테이너 검사를 건너뜁니다"
else
  # 도구 유무와 망 상태를 구분한다. 앱 SIF 에는 curl 이 없는 경우가 흔해서(실측: thermal-shock-mcp)
  # curl 결과만 보면 멀쩡한 컨테이너를 '연결 불가'로 오진한다. python 으로 판정하고 curl 은 보조로 쓴다.
  IN=$(apptainer exec "$SIF" python3 - <<'PY' 2>/dev/null
import ssl, urllib.request
def probe(ctx=None):
    try:
        return str(urllib.request.urlopen("https://www.google.com", timeout=8, context=ctx).status)
    except ssl.SSLError:
        return "TLS"
    except Exception:
        return "000"
verified = probe()
if verified not in ("000", "TLS"):
    print("OK " + verified)
else:
    lax = ssl.create_default_context(); lax.check_hostname = False; lax.verify_mode = ssl.CERT_NONE
    print(("CERT" if probe(lax) not in ("000", "TLS") else "NET"))
PY
)
  case "${IN:-}" in
    OK\ *) ok "컨테이너 안에서도 검증 통과 (HTTP ${IN#OK })" ;;
    CERT)
      ng "컨테이너 안에서 인증서 검증 실패 — 이미지의 CA 저장소에 사내 CA 가 없습니다"
      dim "처방: SIF 빌드 def 에 사내 CA 를 복사하고 update-ca-certificates 를 넣거나,"
      dim "      실행 시 CA 번들을 bind mount 하고 SSL_CERT_FILE 로 지정" ;;
    NET)
      ng "컨테이너 안에서 연결 불가 — 프록시 환경변수가 컨테이너로 전달되지 않았을 수 있습니다"
      dim "처방: APPTAINERENV_HTTPS_PROXY / APPTAINERENV_NO_PROXY 로 전달" ;;
    *)
      warn "컨테이너 안에 python3 가 없어 판정할 수 없습니다 — 앱 런타임 기준 확인은 별도로 하세요" ;;
  esac
fi

sec "판정"
if [ "$BASE_CODE" != "000" ]; then
  ok "이 박스에서 HTTPS 외부 호출이 검증까지 통과합니다 — 웹 검색 기능을 얹을 수 있습니다"
  [ "$MITM" = "yes" ] && dim "다만 트래픽은 사내 프록시가 복호화해 봅니다. 어떤 질의가 나가는지에 대한 승인 판단이 필요합니다."
elif [ "$BASE_CODE_K" != "000" ]; then
  ng "연결은 되나 인증서 검증이 실패합니다 — 사내 CA 신뢰 설정이 선행 과제입니다"
else
  ng "외부 HTTPS 자체가 막혀 있습니다 — 프록시 허용 목록(allowlist) 신청이 선행 과제입니다"
fi

if [ "$JSON" = 1 ]; then
  printf '{"proxy":"%s","mitm":"%s","base_code":"%s","base_code_insecure":"%s"}\n' \
    "${PROXY:-}" "$MITM" "${BASE_CODE:-000}" "${BASE_CODE_K:-000}"
fi
