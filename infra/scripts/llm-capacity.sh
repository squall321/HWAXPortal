#!/usr/bin/env bash
# LLM 풀 용량 측정 — GuideLLM SIF 로 서버 하나 직결 대 측정용 라우터 경유(붙임 문턱 변형)를 동시 수마다 재고 표와 세 손잡이 권장을 낸다(docs/llm-pool/capacity.md)
#
#   python3 infra/scripts/llm-lengths.py --out /tmp/lengths.json                 # 먼저 — 길이 분포(본문 없이 수만)
#   ./infra/scripts/llm-capacity.sh --lengths /tmp/lengths.json --dry-run       # 무엇을 몇 건 보낼지만 본다(아무것도 부르지 않는다)
#   ./infra/scripts/llm-capacity.sh --lengths /tmp/lengths.json                 # 잰다(심의·카드 대조가 없을 때 — GPU 를 차지한다)
#
# 운영 라우터·infra/.env 를 건드리지 않는다. 라우터 경로는 이 실행만의 라우터를 루프백 임시 포트에 따로 띄워 잰다 — 그 라우터는 자기 설정
# 파일(LLM_ROUTER_ENV_FILE, 임시 디렉터리 700 · 파일 600, 끝나면 지운다)만 읽는다. 서버 목록은 --upstreams, 없으면 infra/.env 의 LLM_UPSTREAMS 다
# (정본 규칙 lib/llm-pool.sh hwax_llm_pool_upstreams 로 본다 — 운영 라우터 자신(127.0.0.1:<LLM_ROUTER_PORT>)은 받지 않는다).
#
# 키 — infra/.env 의 LLM_API_KEY 를 읽어 환경으로만 넘긴다. GuideLLM 에는 APPTAINERENV_GUIDELLM__SPEC__BACKEND__API_KEY(컨테이너 안에서
# GUIDELLM__SPEC__BACKEND__API_KEY — 보고서에는 ********** 로 남는다), 측정용 라우터에는 그 설정 파일(운영 라우터가 infra/.env 를 읽는 것과
# 같은 길 — /v1/models 대조에만 쓴다). 명령줄(argv)에는 어디에도 싣지 않고 찍지도 않는다.
#
# 붙임 문턱(LLM_ROUTER_STICKY_SLACK) — 붙인 서버가 가장 한가한 서버보다 이만큼 이상 바쁘면 떨어진다. 0 은 붙임 끔(늘 가장 한가한 서버),
# 기본 2, 큰 값은 늘 붙임(부하를 보지 않는다). 기본 변형은 '2 0' 이다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/infra/.env"
CAP="$ROOT/infra/scripts/llm-capacity.py"
GUIDELLM_SIF="$ROOT/infra/apptainer/guidellm.sif"
PORTAL_SIF="$ROOT/infra/apptainer/portal.sif"
AGENT_HEALTH="http://127.0.0.1:9009/health"
# shellcheck source=lib/llm-pool.sh
. "$ROOT/infra/scripts/lib/llm-pool.sh"

usage() {
  cat <<'EOF'
사용법: ./infra/scripts/llm-capacity.sh --lengths <lengths.json> [옵션]
  --lengths FILE        llm-lengths.py 의 길이 분포(필수)
  --kind K              어느 카드 대조 호출의 분포로 부하를 만드나 — all(기본) · sweep · verdict · offcard · noinput · summary
  --upstreams U1,U2     잴 서버들의 /v1 주소(기본 infra/.env 의 LLM_UPSTREAMS) — 라우터 경로가 이 전부를 쓴다
  --direct URL          직결로 잴 서버(기본 위 목록의 첫 서버)
  --paths "direct router"  잴 경로(기본 둘 다)
  --slack "2 0"         라우터 경로의 붙임 문턱 변형(기본 2 와 0 — 0 은 붙임 끔)
  --levels "1 2 4 8 12 16 24"  동시 수 단계
  --requests N          단계마다 요청 수(기본 0 = max(10, 3 × 동시 수) — 앞 1/3 은 데우기로 빼고 잰다)
  --max-seconds S       단계 하나의 상한 초(기본 900 — 넘으면 그 단계를 끊는다)
  --prefix-share F      프롬프트 가운데 같은 전문가끼리 공유하는 앞부분 몫(기본 0.5)
  --prefix-count K      서로 다른 앞부분 수(기본 길이 분포의 '돌던 전문가 수' 중앙값, 없으면 4)
  --ttft-ratio R        권장 규칙의 TTFT p95 한도 = 가장 낮은 단계 TTFT p50 × R(기본 3)
  --ttft-max-s S        한도를 절대 초로(주면 위 비율 대신)
  --growth G            권장 규칙의 요청/초 증가 하한(기본 0.05)
  --out DIR             결과 디렉터리(기본 infra/.state/llm-capacity/<UTC 시각> — 비어 있지 않으면 멈춘다)
  --agent-health URL    도는 심의·카드 대조를 물을 에이전트 서버 /health(기본 http://127.0.0.1:9009/health)
  --dry-run             계획만 찍는다(서버·라우터·GuideLLM 을 부르지 않는다)
  --force               도는 심의·카드 대조 검사를 건너뛴다(그 호출들과 GPU 를 나눠 잰다 — 결과가 흐려진다)
EOF
}

LENGTHS="" KIND="all" UPS_ARG="" DIRECT="" PATHS_="direct router" SLACKS="2 0" LEVELS="1 2 4 8 12 16 24"
REQUESTS=0 MAX_SECONDS=900 PREFIX_SHARE=0.5 PREFIX_COUNT=0 TTFT_RATIO=3 TTFT_MAX="" GROWTH=0.05 OUT="" DRY=0 FORCE=0
_need() { [ "$2" -ge 2 ] || { echo "✗ $1 에 값이 없다" >&2; usage >&2; exit 2; }; }
while [ $# -gt 0 ]; do
  case "$1" in
    --lengths)      _need "$1" $#; LENGTHS="$2"; shift 2 ;;
    --kind)         _need "$1" $#; KIND="$2"; shift 2 ;;
    --upstreams)    _need "$1" $#; UPS_ARG="$2"; shift 2 ;;
    --direct)       _need "$1" $#; DIRECT="$2"; shift 2 ;;
    --paths)        _need "$1" $#; PATHS_="$2"; shift 2 ;;
    --slack)        _need "$1" $#; SLACKS="$2"; shift 2 ;;
    --levels)       _need "$1" $#; LEVELS="$2"; shift 2 ;;
    --requests)     _need "$1" $#; REQUESTS="$2"; shift 2 ;;
    --max-seconds)  _need "$1" $#; MAX_SECONDS="$2"; shift 2 ;;
    --prefix-share) _need "$1" $#; PREFIX_SHARE="$2"; shift 2 ;;
    --prefix-count) _need "$1" $#; PREFIX_COUNT="$2"; shift 2 ;;
    --ttft-ratio)   _need "$1" $#; TTFT_RATIO="$2"; shift 2 ;;
    --ttft-max-s)   _need "$1" $#; TTFT_MAX="$2"; shift 2 ;;
    --growth)       _need "$1" $#; GROWTH="$2"; shift 2 ;;
    --out)          _need "$1" $#; OUT="$2"; shift 2 ;;
    --agent-health) _need "$1" $#; AGENT_HEALTH="$2"; shift 2 ;;
    --dry-run)      DRY=1; shift ;;
    --force)        FORCE=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "✗ 모르는 인자: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# ── 인자 검사(무엇이든 부르기 전에) ──
_bad() { echo "✗ $1" >&2; exit 2; }
_num='^[0-9]+([.][0-9]+)?$'
[ -n "$LENGTHS" ] || _bad "--lengths 가 없다 — 먼저 python3 infra/scripts/llm-lengths.py --out <파일> 로 길이 분포를 만든다"
[ -f "$LENGTHS" ] || _bad "--lengths $LENGTHS 가 없다"
case "$KIND" in all|sweep|verdict|offcard|noinput|summary) ;; *) _bad "--kind $KIND 는 all·sweep·verdict·offcard·noinput·summary 가운데 하나다" ;; esac
_seen=" "
for x in $LEVELS; do
  [[ "$x" =~ ^[1-9][0-9]{0,3}$ ]] || _bad "--levels 의 '$x' 는 1~9999 의 정수가 아니다"
  case "$_seen" in *" $x "*) _bad "--levels 에 $x 가 두 번 있다" ;; esac
  _seen="$_seen$x "
done
[ "$_seen" != " " ] || _bad "--levels 가 비었다"
WANT_DIRECT=0 WANT_ROUTER=0
for p in $PATHS_; do
  case "$p" in direct) WANT_DIRECT=1 ;; router) WANT_ROUTER=1 ;; *) _bad "--paths 의 '$p' 는 direct·router 가 아니다" ;; esac
done
[ $((WANT_DIRECT + WANT_ROUTER)) -gt 0 ] || _bad "--paths 가 비었다"
if [ "$WANT_ROUTER" = 1 ]; then
  _seen=" "
  for s in $SLACKS; do
    [[ "$s" =~ $_num ]] || _bad "--slack 의 '$s' 는 0 이상의 수가 아니다"
    case "$_seen" in *" $s "*) _bad "--slack 에 $s 가 두 번 있다" ;; esac
    _seen="$_seen$s "
  done
  [ "$_seen" != " " ] || _bad "--slack 이 비었다(라우터 경로를 재려면 문턱이 하나 이상 있어야 한다)"
fi
[[ "$REQUESTS" =~ ^[0-9]+$ ]] || _bad "--requests 는 0 이상의 정수다"
[[ "$MAX_SECONDS" =~ $_num ]] && [ "${MAX_SECONDS%%.*}" -ge 1 ] || _bad "--max-seconds 는 1 이상의 수다"
[[ "$PREFIX_SHARE" =~ $_num ]] || _bad "--prefix-share 는 0 이상 1 미만의 수다"
[[ "$PREFIX_COUNT" =~ ^[0-9]+$ ]] || _bad "--prefix-count 는 0 이상의 정수다(0 = 길이 분포에서)"
[[ "$TTFT_RATIO" =~ $_num ]] || _bad "--ttft-ratio 는 수다"
[ -z "$TTFT_MAX" ] || [[ "$TTFT_MAX" =~ $_num ]] || _bad "--ttft-max-s 는 수다"
[[ "$GROWTH" =~ $_num ]] || _bad "--growth 는 0 이상의 수다"

# ── 서버 목록 — 정본 규칙으로 본다. 운영 라우터 포트는 고리로 거른다(운영 라우터를 거쳐 재지 않는다) ──
# hwax_llm_envv 는 파일이 없으면(dev 의 새 작업 트리) sed 가 실패해 pipefail 아래 0 이 아니다 — set -e 가 말없이 끝내지 않게 || true
PROD_PORT="$(hwax_llm_envv "$ENV_FILE" LLM_ROUTER_PORT || true)"; PROD_PORT="${PROD_PORT:-9130}"
_ups_from() {  # $1=값 → 줄마다 주소 하나(틀리면 사유와 2)
  local f rc=0 out
  f="$(mktemp)"; printf 'LLM_UPSTREAMS=%s\n' "$1" > "$f"
  out="$(hwax_llm_pool_upstreams "$f" "$PROD_PORT")" || rc=$?
  rm -f "$f"; printf '%s\n' "$out"; return "$rc"
}
_rc=0
if [ -n "$UPS_ARG" ]; then UPS="$(_ups_from "$UPS_ARG")" || _rc=$?
else UPS="$(hwax_llm_pool_upstreams "$ENV_FILE" "$PROD_PORT")" || _rc=$?; fi
case "$_rc" in
  0) ;;
  1) _bad "잴 서버가 없다 — --upstreams <서버1 /v1>,<서버2 /v1> 로 주거나 infra/.env 에 LLM_UPSTREAMS 를 적는다" ;;
  *) _bad "서버 목록을 쓸 수 없다 — $UPS" ;;
esac
mapfile -t UPS_LIST <<<"$UPS"
N_UPS=${#UPS_LIST[@]}
if [ -n "$DIRECT" ]; then
  _rc=0; _d="$(_ups_from "$DIRECT")" || _rc=$?
  [ "$_rc" = 0 ] && [ "$(printf '%s\n' "$_d" | wc -l)" = 1 ] || _bad "--direct 는 서버 /v1 주소 하나다 — ${_d:-빈 값}"
  DIRECT="$_d"
else
  DIRECT="${UPS_LIST[0]}"
fi

# 키 — 값은 이 셸 변수에만 든다(내보내지 않는다 · 찍지 않는다). 없으면 키 없이 부른다(키를 받지 않는 vLLM).
KEY="$(hwax_llm_envv "$ENV_FILE" LLM_API_KEY || true)"

A="${APPTAINER:-}"
if [ -z "$A" ]; then
  for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
fi
A="${A:-apptainer}"

VARIANTS=()        # "이름|경로|대상|문턱"
[ "$WANT_DIRECT" = 1 ] && VARIANTS+=("direct|direct|$DIRECT|")
if [ "$WANT_ROUTER" = 1 ]; then for s in $SLACKS; do VARIANTS+=("router-slack$s|router||$s"); done; fi

TMPD="$(mktemp -d)"      # 700 — 측정용 라우터 설정(키가 든다)과 계획용 시나리오. 끝나면 통째로 지운다
RPID="" RURL=""
stop_router() {
  [ -n "$RPID" ] || return 0
  kill -TERM -- "-$RPID" 2>/dev/null || kill -TERM "$RPID" 2>/dev/null || true
  for _ in $(seq 1 100); do kill -0 "$RPID" 2>/dev/null || break; sleep 0.1; done
  if kill -0 "$RPID" 2>/dev/null; then kill -KILL -- "-$RPID" 2>/dev/null || kill -KILL "$RPID" 2>/dev/null || true; fi
  wait "$RPID" 2>/dev/null || true
  RPID=""
}
cleanup() { stop_router; rm -rf "$TMPD"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP      # ssh 가 끊겨도 측정용 라우터를 내리고 임시 디렉터리를 지운다

_scenario() {  # $1=대상 $2=보고서 $3=시나리오 파일 $4…=라벨
  local target="$1" report="$2" out="$3"; shift 3
  local labels=() l
  for l in "$@"; do labels+=(--label "$l"); done
  python3 "$CAP" scenario --lengths "$LENGTHS" --kind "$KIND" --target "$target" --levels "$LEVELS" --requests "$REQUESTS" \
    --max-seconds "$MAX_SECONDS" --prefix-share "$PREFIX_SHARE" --prefix-count "$PREFIX_COUNT" --report "$report" \
    "${labels[@]}" --out "$out"
}

# ── 계획 — 길이 분포로 부하를 한 번 만들어 본다(틀린 분포면 여기서 멈춘다) ──
echo "── LLM 풀 용량 측정 계획"
echo "· 서버 ${N_UPS}곳 — $(printf '%s ' "${UPS_LIST[@]}")· 직결 대상 $DIRECT"
echo "· 변형 — $(for v in "${VARIANTS[@]}"; do printf '%s ' "${v%%|*}"; done)"
echo "· 키 — $([ -n "$KEY" ] && echo 'infra/.env 의 LLM_API_KEY 를 환경으로만 넘긴다' || echo '없다(키 없이 부른다)')"
_scenario "$DIRECT" "$TMPD/plan.json" "$TMPD/plan-scenario.json" "variant=plan" || exit 2
N_REQ="$(python3 -c 'import json,sys; print(sum(json.load(open(sys.argv[1]))["spec"]["constraints"][0]["count"]))' "$TMPD/plan-scenario.json")"
echo "· 요청 — 변형마다 최대 ${N_REQ}건 × 변형 ${#VARIANTS[@]} = 최대 $((N_REQ * ${#VARIANTS[@]}))건 · 단계마다 최대 ${MAX_SECONDS}초"

if [ "$DRY" = 1 ]; then
  [ -f "$GUIDELLM_SIF" ] || echo "⚠ $GUIDELLM_SIF 가 없다 — 재기 전에 ./infra/scripts/images-from-drive.sh(dev 는 build-guidellm.sh)"
  [ "$WANT_ROUTER" = 0 ] || [ -f "$PORTAL_SIF" ] || echo "⚠ $PORTAL_SIF 가 없다 — 측정용 라우터가 이 이미지로 돈다"
  echo "✓ dry-run — 아무것도 부르지 않았다"
  exit 0
fi

[ -f "$GUIDELLM_SIF" ] || { echo "✗ $GUIDELLM_SIF 가 없다 — ./infra/scripts/images-from-drive.sh 로 받는다(dev 는 ./infra/scripts/build-guidellm.sh)" >&2; exit 1; }
[ "$WANT_ROUTER" = 0 ] || [ -f "$PORTAL_SIF" ] || { echo "✗ $PORTAL_SIF 가 없다 — 측정용 라우터가 이 이미지로 돈다(images-from-drive.sh)" >&2; exit 1; }
command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A)" >&2; exit 1; }

if [ -z "$OUT" ]; then OUT="$ROOT/infra/.state/llm-capacity/$(date -u +%Y%m%dT%H%M%SZ)"; fi
if [ -d "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then _bad "결과 디렉터리 $OUT 가 비어 있지 않다 — 다른 --out 을 준다(지난 결과를 덮지 않는다)"; fi

# ── 심의·카드 대조가 돌면 재지 않는다(그 호출과 GPU 를 나눠 재면 둘 다 흐려진다) ──
if [ "$FORCE" = 1 ]; then
  echo "⚠ --force — 도는 심의·카드 대조를 보지 않고 잰다"
else
  _rc=0; _msg="$(python3 "$CAP" busy "$AGENT_HEALTH")" || _rc=$?
  case "$_rc" in
    0) echo "· 에이전트 서버 — $_msg" ;;
    *) echo "✗ $_msg — 재지 않았다(강행은 --force)" >&2; exit 3 ;;
  esac
fi
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
python3 "$CAP" metrics --out "$OUT/metrics-start.json" "${UPS_LIST[@]}"
python3 - "$OUT/metrics-start.json" <<'PY'
import json, sys
for s in json.load(open(sys.argv[1])):
    if "error" in s:
        print(f"⚠ 서버 {s['server']} 의 /metrics 를 못 읽었다({s['error']}) — 접두 캐시 적중률을 셀 수 없다")
    elif (s.get("running") or 0) + (s.get("waiting") or 0) > 0:
        print(f"⚠ 서버 {s['server']} 가 지금 도는 {s.get('running', 0):g} · 기다림 {s.get('waiting', 0):g} — 다른 호출과 섞여 잰다(조용할 때 다시)")
    else:
        print(f"· 서버 {s['server']} — 비어 있다")
PY

# 측정용 라우터의 수명 상한 — 변형 하나가 걸릴 수 있는 가장 긴 시간(단계마다 상한 + GuideLLM 기동·마감) + 라우터 기동 대기
_n_levels=0; for _x in $LEVELS; do _n_levels=$((_n_levels + 1)); done
ROUTER_MAX_S=$(( _n_levels * (${MAX_SECONDS%%.*} + 61) + 300 ))

start_router() {  # $1=문턱 $2=변형 디렉터리 — RPID · RURL 을 채운다
  local slack="$1" vdir="$2" port envf k v
  port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
  [ "$port" != "$PROD_PORT" ] || { echo "✗ 임시 포트가 운영 라우터 포트($PROD_PORT)와 같다 — 다시 돌린다" >&2; return 1; }
  envf="$TMPD/router-$slack.env"
  ( umask 077
    { printf 'LLM_UPSTREAMS=%s\n' "$(IFS=,; printf '%s' "${UPS_LIST[*]}")"
      [ -z "$KEY" ] || printf 'LLM_API_KEY=%s\n' "$KEY"
      for k in LLM_ROUTER_SCRAPE_S LLM_ROUTER_PREFIX_CHARS LLM_ROUTER_CONNECT_TIMEOUT_S LLM_ROUTER_COOLDOWN_S; do
        v="$(hwax_llm_envv "$ENV_FILE" "$k" || true)"; [ -z "$v" ] || printf '%s=%s\n' "$k" "$v"
      done
      printf 'LLM_ROUTER_STICKY_SLACK=%s\n' "$slack"; } > "$envf" )
  # 운영 llm-router.sh run 과 같은 띄우기(포털 SIF · --cleanenv · 리포를 /workspace 로) — 포트와 설정 파일만 이 실행의 것이다.
  # setsid — 자기 프로세스 묶음으로 띄워 끝낼 때 그 묶음만 내린다(포트로 찾아 죽이지 않는다 — gotchas §1).
  # timeout — 이 스크립트가 KILL 로 죽어(정리 trap 이 못 돈다) 라우터가 홀로 남아도 변형 하나의 최대 시간 뒤에는 내려간다.
  setsid timeout --kill-after=10 "$ROUTER_MAX_S" "$A" exec --cleanenv --bind "$ROOT:/workspace" --bind "$TMPD" \
    --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONUNBUFFERED=1 --env PYTHONUTF8=1 --env PYTHONNOUSERSITE=1 \
    --env "LLM_ROUTER_PORT=$port" --env "LLM_ROUTER_ENV_FILE=$envf" \
    "$PORTAL_SIF" python3 -m uvicorn --app-dir /workspace/infra/llm-router llm_router:app \
    --host 127.0.0.1 --port "$port" --no-access-log > "$vdir/router.log" 2>&1 &
  RPID=$!
  RURL="http://127.0.0.1:$port"
  local msg rc=0
  msg="$(python3 "$CAP" wait-router "$RURL" --expect "$N_UPS" --timeout 90)" || rc=$?
  if [ "$rc" != 0 ]; then
    echo "  ✗ 측정용 라우터가 서버 ${N_UPS}곳을 올라옴으로 보지 못했다($msg) — 로그 $vdir/router.log" >&2
    return 1
  fi
  # 라우터가 설정을 읽었으니(서버가 올라왔다고 답했다) 키가 든 파일을 곧바로 지운다 — 라우터는 파일이 없어지면 마지막으로 읽은 설정으로
  # 계속 보낸다(LP-D11 ④ · 로그에 한 줄). 그래서 키는 띄우는 몇 초 동안만 디스크에 있다.
  rm -f "$envf"
  echo "  · 측정용 라우터 :$port — $msg"
}

FAILED=0
for v in "${VARIANTS[@]}"; do
  IFS='|' read -r name path target slack <<<"$v"
  vdir="$OUT/$name"; mkdir -p "$vdir"
  echo "── $name"
  servers=("${UPS_LIST[@]}")
  if [ "$path" = router ]; then
    if ! start_router "$slack" "$vdir"; then stop_router; FAILED=1; continue; fi
    target="$RURL/v1"
  else
    servers=("$target")
  fi
  labels=("variant=$name" "path=$path" "upstreams=${#servers[@]}")
  [ -z "$slack" ] || labels+=("slack=$slack")
  _scenario "$target" "$vdir/benchmarks.json" "$vdir/scenario.json" "${labels[@]}" || { stop_router; FAILED=1; continue; }
  python3 "$CAP" metrics --out "$vdir/metrics-before.json" "${servers[@]}"
  python3 "$CAP" activity "$AGENT_HEALTH" --out "$vdir/agent-before.json"
  cmd=("$A" exec --cleanenv --env PYTHONNOUSERSITE=1 --bind "$OUT" "$GUIDELLM_SIF" guidellm run --scenario "$vdir/scenario.json"
       --disable-console-interactive)
  grc=0
  if [ -n "$KEY" ]; then
    APPTAINERENV_GUIDELLM__SPEC__BACKEND__API_KEY="$KEY" "${cmd[@]}" 2>&1 | tee "$vdir/guidellm.log" || grc=$?
  else
    "${cmd[@]}" 2>&1 | tee "$vdir/guidellm.log" || grc=$?
  fi
  python3 "$CAP" metrics --out "$vdir/metrics-after.json" "${servers[@]}"
  python3 "$CAP" activity "$AGENT_HEALTH" --out "$vdir/agent-after.json"
  if [ "$path" = router ]; then
    python3 -c 'import json,sys,urllib.request as u; print(json.dumps(json.load(u.build_opener(u.ProxyHandler({})).open(sys.argv[1], timeout=5))))' \
      "$RURL/stats" > "$vdir/router-stats.json" 2>/dev/null || rm -f "$vdir/router-stats.json"
    stop_router
  fi
  if [ "$grc" != 0 ] || [ ! -f "$vdir/benchmarks.json" ]; then
    echo "  ✗ $name — GuideLLM 이 실패했다(rc $grc) — 로그 $vdir/guidellm.log" >&2; FAILED=1
  fi
done

# ── 표와 권장 — 세 손잡이의 지금 값은 정본 독자로 읽어 넘긴다(적혀 있지 않으면 코드 기본값으로 본다) ──
NOW=()
for kf in "CARD_REVIEW_CONCURRENCY|$ROOT/../HWAXAgentServer/.env" \
          "HWAXRISK_REVIEW_CONCURRENCY|$ROOT/../HEAXHub/var/app_data/hwax_risk/knobs.env" \
          "CARD_REVIEW_MAX_STREAMS|$ROOT/backend/.env"; do
  _v="$(hwax_llm_envv "${kf#*|}" "${kf%%|*}" || true)"
  [ -z "$_v" ] || NOW+=(--now "${kf%%|*}=$_v")
done
ZARGS=(--ttft-ratio "$TTFT_RATIO" --growth "$GROWTH")
[ -z "$TTFT_MAX" ] || ZARGS+=(--ttft-max-s "$TTFT_MAX")
echo
_zrc=0; python3 "$CAP" summarize "$OUT" "${ZARGS[@]}" ${NOW[@]+"${NOW[@]}"} || _zrc=$?
echo
echo "결과 — $OUT (summary.md · summary.json · 변형마다 benchmarks.json · guidellm.log)"
echo "기록 — 표와 권장을 docs/llm-pool/capacity.md 7절에 옮겨 적는다(내부 주소는 빼고)"
[ "$_zrc" = 0 ] && [ "$FAILED" = 0 ] || exit 1
