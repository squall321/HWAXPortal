#!/usr/bin/env bash
# LLM 라우터(infra/llm-router/llm_router.py)를 포털 SIF 로 앞에서 띄우고(run) 그 포트를 듣는 라우터만 내린다(stop) — docs/llm-pool PLAN §3
#
#   ./infra/scripts/llm-router.sh run    # 앞에서 돈다(services.py 가 떼어 띄운다 — services.yaml llm-router)
#   ./infra/scripts/llm-router.sh stop   # 그 포트를 LISTEN 하는 프로세스만, 명령줄이 라우터인지 확인한 뒤 TERM → 기다림 → KILL
#   LLM_ROUTER_PORT=9131 ./infra/scripts/llm-router.sh stop    # stop 만 환경의 포트가 infra/.env 보다 먼저다(옛 포트에 남은 라우터를 내릴 때)
#
# 포트 — run 은 늘 infra/.env 의 LLM_ROUTER_PORT(기본 9130)다. 사본·update-all 1i·§6 은 infra/.env 만 읽으므로 운영자 셸에 export 된 값으로
#   띄우면 아무 사본도 가리키지 않는 포트에 라우터가 뜬다 — 환경의 값이 다르면 경고 한 줄을 찍고 infra/.env 로 띄운다.
#   stop 은 환경의 LLM_ROUTER_PORT 를 먼저 본다 — update-all 이 옛 포트에 남은 라우터를 내릴 때 **그 호출에만** 주는 값이다. 그래서
#   update-all · update-sites 는 시작할 때 물려받은 LLM_ROUTER_PORT 를 지운다(운영자 셸에 export 된 옛 포트가 남으면 재기동의 stop 이
#   지금 라우터 대신 옛 포트를 내리고, 지금 라우터는 그대로 남아 run 이 포트를 못 잡는다 — 검토 2라운드 LOW 6).
#
# run — 리포를 /workspace 로 바인드하고 127.0.0.1:<포트> 에만 듣는다. 새 이미지가 없다(포털 SIF 의 python·httpx·uvicorn).
#   설정은 라우터가 infra/.env 를 **직접** 읽는다 — 키를 argv·환경으로 넘기지 않으려고 --cleanenv 로 띄운다(띄운 셸의 http_proxy·비밀이
#   딸려 들어가지 않는다). 넘기는 것은 듣는 포트뿐이다(비밀이 아니다 — 라우터가 자기 자신을 가리키는 칸을 거르는 데 쓴다).
#   띄우기 전에 LLM_UPSTREAMS 를 lib/llm-pool.sh 의 정본 규칙으로 본다 — 틀린 줄로는 띄우지 않는다(라우터는 같은 규칙으로 503 을 낼 뿐이고,
#   부팅 유닛·services.sh up 은 이 스크립트로 띄운다). 서버 목록은 라우터가 다시 읽어 재기동 없이 바꾼다 — 다시 부를 일은 코드가 바뀔 때뿐이다.
# stop — 포트로 죽일 때 연결 중인 클라이언트까지 잡으면 남을 죽인다(docs/gotchas.md §1 — 포털 재기동이 게이트웨이를 죽였다). 그래서
#   `ss -ltnp` 의 리스너만 보고, 그 명령줄에 llm_router 가 없으면 손대지 않고 실패로 끝난다. 아무도 안 들으면 이미 내려간 것이다(0).
#   pid 가 안 보이는 리스너(다른 계정의 프로세스)와 ss 가 없는 박스는 '모른다' 라 실패(1)다 — '내려갔다' 로 말하지 않는다(그 포트에 남이 떠 있으면
#   사본들이 키와 프롬프트를 그 프로세스로 보낸다).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/infra/.env"

# infra/.env 값 하나 — 정본 규칙(update-all `_envfile_value` · services.py `_infra_value` · 라우터 read_env)과 같은 한 줄이다.
# 마지막 활성 줄이 이기고, `export` 허용, 공백 뒤 `#` 이후·양끝 공백·따옴표 문자·CR 을 벗긴다. 파일이 없으면 빈 값이다.
# 첫 sed 도 LC_ALL=C — 공백은 ASCII 여섯뿐이다(UTF-8 로케일이면 U+3000 으로 시작하는 줄도 활성 줄이 되어 라우터와 갈린다).
envv() { LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=//p" "$2" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'; }

_port_ok() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ "${#1}" -le 5 ] && [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le 65535 ]; }

if [ "${1:-}" = stop ] && [ -n "${LLM_ROUTER_PORT:-}" ]; then
  PORT="$LLM_ROUTER_PORT"; _FROM="환경변수"
else
  PORT="$(envv LLM_ROUTER_PORT "$ENV_FILE" || true)"; PORT="${PORT:-9130}"; _FROM="infra/.env"
fi
case "$PORT" in
  ''|*[!0-9]*) echo "✗ LLM_ROUTER_PORT='$PORT'($_FROM) 는 포트 번호가 아니다 — 수만 적는다(기본 9130)" >&2; exit 2 ;;
esac
if ! _port_ok "$PORT"; then
  echo "✗ LLM_ROUTER_PORT=$PORT($_FROM) 는 1~65535 밖이다" >&2; exit 2
fi
PORT="$((10#$PORT))"
if [ "${1:-}" = run ] && [ -n "${LLM_ROUTER_PORT:-}" ] && { ! _port_ok "$LLM_ROUTER_PORT" || [ "$((10#$LLM_ROUTER_PORT))" != "$PORT" ]; }; then
  echo "⚠ 환경변수 LLM_ROUTER_PORT=$LLM_ROUTER_PORT 는 run 에서 쓰지 않는다 — 사본·update-all 은 infra/.env 만 보므로 infra/.env 의 포트 $PORT 로 띄운다" >&2
fi

case "${1:-}" in
  run)
    # shellcheck source=lib/llm-pool.sh
    . "$ROOT/infra/scripts/lib/llm-pool.sh"
    _ups_rc=0; _ups="$(hwax_llm_pool_upstreams "$ENV_FILE" "$PORT")" || _ups_rc=$?
    case "$_ups_rc" in
      0) ;;
      1) echo "✗ infra/.env 에 LLM_UPSTREAMS 가 없다(비어 있다) — 보낼 서버가 없어 라우터를 띄우지 않는다." >&2
         echo "  켜려면 infra/.env 에 한 줄: LLM_UPSTREAMS=<서버1 /v1 주소>,<서버2 /v1 주소>  (docs/llm-pool)" >&2
         exit 2 ;;
      *) echo "✗ infra/.env 의 LLM_UPSTREAMS 를 쓸 수 없어 라우터를 띄우지 않는다 — $_ups" >&2
         exit 2 ;;
    esac
    SIF="$ROOT/infra/apptainer/portal.sif"
    [ -f "$SIF" ] || { echo "✗ 포털 SIF 가 없다: $SIF — ./infra/scripts/images-from-drive.sh 로 받는다" >&2; exit 1; }
    # apptainer 찾기는 _common.sh 와 같다(리포 안 bin-*/ 의 가장 새 것 → PATH). _common.sh 를 소싱하지 않는 것은 그쪽이 infra/.env 를
    # set -a 로 통째로 export 하기 때문이다 — 그러면 비밀이 라우터 환경으로 넘어간다.
    A="${APPTAINER:-}"
    if [ -z "$A" ]; then
      for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
    fi
    A="${A:-apptainer}"
    command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A) — ./infra/scripts/bootstrap.sh" >&2; exit 1; }
    # PYTHONDONTWRITEBYTECODE — 지문(services.yaml fp: infra/llm-router)은 __pycache__ 를 보지 않지만 리포에 바이트코드를 남기지 않는다.
    exec "$A" exec --cleanenv --bind "$ROOT:/workspace" \
      --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONUNBUFFERED=1 --env PYTHONUTF8=1 --env "LLM_ROUTER_PORT=$PORT" \
      "$SIF" python3 -m uvicorn --app-dir /workspace/infra/llm-router llm_router:app \
      --host 127.0.0.1 --port "$PORT" --no-access-log
    ;;
  stop)
    command -v ss >/dev/null 2>&1 || {
      echo "✗ ss(iproute2)가 없어 :$PORT 를 듣는 프로세스를 볼 수 없다 — 라우터가 내려갔는지 모른다(내리지 않았다)" >&2; exit 1; }
    _ss_rc=0; _ls="$(ss -ltnpH "sport = :$PORT" 2>/dev/null)" || _ss_rc=$?
    if [ "$_ss_rc" != 0 ]; then
      echo "✗ ss 가 실패했다(rc $_ss_rc) — :$PORT 를 듣는 프로세스를 모른다(내리지 않았다)" >&2; exit 1
    fi
    if [ -z "$_ls" ]; then
      echo "· :$PORT 를 듣는 프로세스가 없다 — 라우터는 이미 내려가 있다"; exit 0
    fi
    # 리스너 줄마다 pid 가 보여야 한다 — 남의 계정 프로세스는 ss -p 가 pid 를 보여 주지 않는다(그 리스너는 이 계정의 라우터가 아니다)
    _blind="$(printf '%s\n' "$_ls" | grep -vc 'pid=' || true)"
    PIDS="$(printf '%s\n' "$_ls" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true)"
    if [ "${_blind:-0}" != 0 ] || [ -z "$PIDS" ]; then
      echo "✗ :$PORT 를 듣는 리스너가 있는데 pid 가 안 보인다(다른 계정의 프로세스 — LLM 라우터가 아니다) — 건드리지 않는다" >&2; exit 1
    fi
    for p in $PIDS; do
      # 명령줄을 먼저 받고 본다 — `… | grep -q` 는 pipefail 아래서 맞은 것을 '아니다' 로 읽을 수 있다(판정 파이프 함정)
      _cmd="$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null || true)"
      case "$_cmd" in
        *llm_router*) ;;
        *) echo "✗ :$PORT 를 듣는 pid $p 는 LLM 라우터가 아니다(${_cmd:0:120}) — 건드리지 않는다" >&2; exit 1 ;;
      esac
    done
    # 산 것 — 프로세스가 있고 좀비가 아니다. 리스너가 사라졌는지로 보면 안 된다: uvicorn 은 TERM 을 받으면 듣기부터 닫고 도는 요청을
    # 끝까지 보낸다 — 그 사이를 '내려갔다' 로 읽으면 기다림·KILL 이 무의미해진다. 상태 글자는 마지막 ") " 뒤에 있다(이름에 빈칸이 있을 수 있다).
    _alive() { local s; s="$(sed -n 's/.*) //p' "/proc/$1/stat" 2>/dev/null || true)"; [ -n "$s" ] && [ "${s%% *}" != Z ]; }
    _left() { local p out=""; for p in $PIDS; do _alive "$p" && out="$out $p"; done; echo "${out# }"; }
    echo "→ LLM 라우터 정지(:$PORT, pid $(echo $PIDS))"
    kill -TERM $PIDS 2>/dev/null || true
    for _ in $(seq 1 100); do                  # 10초 — uvicorn 은 도는 요청이 끝나길 기다린다(update-sites 가 inflight 를 보고 미룬다)
      [ -z "$(_left)" ] && { echo "✓ 내려갔다"; exit 0; }
      sleep 0.1
    done
    LEFT="$(_left)"
    echo "  ⚠ 10초 안에 내려가지 않아 KILL 한다(pid $LEFT — 도는 요청이 끊긴다)"
    kill -KILL $LEFT 2>/dev/null || true
    for _ in $(seq 1 30); do [ -z "$(_left)" ] && { echo "✓ 내려갔다(KILL)"; exit 0; }; sleep 0.1; done
    echo "✗ KILL 뒤에도 pid $(_left) 가 남았다" >&2; exit 1
    ;;
  *)
    echo "사용법: $(basename "$0") {run|stop}" >&2; exit 2 ;;
esac
