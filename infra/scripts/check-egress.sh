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
set -uo pipefail

TIMEOUT="${EGRESS_TIMEOUT:-8}"
SIF=""
JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sif) SIF="${2:?--sif 뒤에 SIF 경로}"; shift 2 ;;
    --json) JSON=1; shift ;;
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

sec "1) 프록시 환경"
PROXY="${HTTPS_PROXY:-${https_proxy:-${HTTP_PROXY:-${http_proxy:-}}}}"
if [ -n "$PROXY" ]; then
  ok "프록시 설정됨: $PROXY"
  NP="${NO_PROXY:-${no_proxy:-}}"
  if [ -n "$NP" ]; then
    ok "NO_PROXY: $NP"
    # 내부 목적지가 프록시로 새면 사내 LLM·게이트웨이 호출이 통째로 깨진다(실사고 기록 있음).
    for h in 127.0.0.1 localhost; do
      case ",$NP," in *",$h,"*) ;; *) warn "NO_PROXY 에 $h 없음 — 내부 호출이 프록시로 샐 수 있다" ;; esac
    done
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
