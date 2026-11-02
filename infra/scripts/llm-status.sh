#!/usr/bin/env bash
# LLM/GPU 현황 수집기(infra/llm-status/collector.py)를 시스템 python3 로 루프백 한 포트에 띄우고(run · start) 그 포트를 듣는 수집기만 내린다(stop) — docs/ops-dashboard
#
#   ./infra/scripts/llm-status.sh run     # 앞에서 돈다(services.py 가 떼어 띄운다 — services.yaml llm-status)
#   ./infra/scripts/llm-status.sh start   # 손으로 — 뒤에서 띄우고 곧바로 돌아온다(nohup + disown · 로그 /tmp/hwax-services/llm-status.log)
#   ./infra/scripts/llm-status.sh stop    # 그 포트를 LISTEN 하는 프로세스만, 명령줄이 수집기인지 확인한 뒤 TERM → 기다림 → KILL
#   LLM_STATUS_PORT=8762 ./infra/scripts/llm-status.sh stop    # stop 만 환경의 포트가 infra/.env 보다 먼저다(포트를 바꾼 뒤 옛 포트의 것을 내릴 때)
#   ./infra/scripts/llm-status.sh probe   # 그 포트의 /health 가 수집기의 답인가(종료코드 0 · 아니면 1) — update-all 5d 가 내리기 전에 묻는다
#   ./infra/scripts/llm-status.sh check   # 그 포트를 LISTEN 하는 것이 수집기인가(명령줄 — stop 과 같은 판정, 0 · 아니면 1) — update-sites 가 재기동을 생략하기 전에 묻는다
#
# 포트 — run · start 는 늘 infra/.env 의 LLM_STATUS_PORT(기본 8760)다. 매니페스트 health 와 포털(start.sh 가 넘기는 LLM_STATUS_URL)이 infra/.env
#   만 읽으므로 운영자 셸에 export 된 값으로 띄우면 아무도 보지 않는 포트에 뜬다 — 환경의 값이 다르면 경고 한 줄을 찍고 infra/.env 로 띄운다.
# run — 환경을 비우고(env -i) 시스템 python3 을 격리 모드(-I)로 exec 한다. 띄운 셸의 프록시 · 비밀이 수집기 환경(과 그 자식)에 딸려 들어가지
#   않는다 — 키는 수집기가 infra/.env 에서 스스로 읽는다(라우터 규칙 LP-D11). 넘기는 것은 PATH · HOME · LANG 과 듣는 포트(인자)뿐이다. 시험 · 손
#   점검용 LLM_STATUS_STATE_DIR · LLM_STATUS_ENV_FILE 은 있을 때만 넘긴다(비밀이 아니다). 바이트코드는 남기지 않는다(-B — 지문은 원래 보지 않는다).
# start — `( … & )` 서브셸로 감싸지 않는다(호출자가 자식 수명만큼 매달린다 — 메모리 노트 bash-background-launch-blocks-caller). 리스너가 뜨기를
#   5초까지만 기다리고 돌아온다. 이 박스에 LLM_STATUS 가 없으면 띄우되 알린다(다음 update-all 5d 가 내린다). 그 포트에 이미 듣는 것이 있으면
#   stop 과 같은 명령줄 판정으로 수집기인지 보고, 남이면 '이미 떠 있다' 가 아니라 실패(1)다.
# stop — 포트로 죽일 때 연결 중인 클라이언트까지 잡으면 남을 죽인다(docs/gotchas.md §1). `ss -ltnp` 의 리스너만 보고, 그 명령줄이 수집기
#   (`…/infra/llm-status/collector.py serve`)가 아니면 손대지 않고 실패로 끝난다. 아무도 안 들으면 이미 내려간 것이다(0). pid 가 안 보이는
#   리스너(다른 계정)와 ss 가 없는 박스는 '모른다' 라 실패(1)다 — '내려갔다' 로 말하지 않는다.
# probe — /health 의 몸에 `"service":"hwax-llm-status"` 가 있을 때만 0 이다(상태 코드는 보지 않는다 — 멈춘 수집기는 503 이다). 그 포트에서 남의 앱이
#   200 을 내도 1 이다 — 꺼진 박스의 update-all 5d 가 그 앱을 두고 ○ 한 줄만 남긴다(docs/ops-dashboard OD-28). 못 물으면(curl 없음 · 안 닿음) 1 이다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/infra/.env"
SELF="$ROOT/infra/scripts/llm-status.sh"
COLLECTOR="$ROOT/infra/llm-status/collector.py"
# 로그 — services.py 가 띄울 때와 같은 자리(/tmp/hwax-services/<이름>.log · 폴더 700 · 파일 600). LLM_STATUS_LOG 는 시험 · 손 점검용 다른 자리다.
LOG="${LLM_STATUS_LOG:-/tmp/hwax-services/llm-status.log}"
LOG_DIR="$(dirname "$LOG")"
SYS_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# infra/.env 값 하나 — 정본 규칙(update-all `_envfile_value` · services.py `_infra_value` · call-trace.sh envv)과 같은 한 줄이다.
envv() { LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=//p" "$2" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'; }

_port_ok() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ "${#1}" -le 5 ] && [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le 65535 ]; }

if [ "${1:-}" = stop ] && [ -n "${LLM_STATUS_PORT:-}" ]; then
  PORT="$LLM_STATUS_PORT"; _FROM="환경변수"
else
  PORT="$(envv LLM_STATUS_PORT "$ENV_FILE" || true)"; PORT="${PORT:-8760}"; _FROM="infra/.env"
fi
if ! _port_ok "$PORT"; then
  echo "✗ LLM_STATUS_PORT='$PORT'($_FROM) 는 1~65535 의 포트 번호가 아니다(기본 8760)" >&2; exit 2
fi
PORT="$((10#$PORT))"
case "${1:-}" in
  run|start)
    if [ -n "${LLM_STATUS_PORT:-}" ] && { ! _port_ok "$LLM_STATUS_PORT" || [ "$((10#$LLM_STATUS_PORT))" != "$PORT" ]; }; then
      echo "⚠ 환경변수 LLM_STATUS_PORT=$LLM_STATUS_PORT 는 ${1} 에서 쓰지 않는다 — 매니페스트 · 포털은 infra/.env 만 보므로 infra/.env 의 포트 $PORT 로 띄운다" >&2
    fi ;;
esac

# 그 포트를 듣는 리스너 줄(없으면 빈 값). ss 가 없거나 실패하면 1.
_listeners() {
  command -v ss >/dev/null 2>&1 || return 1
  ss -ltnpH "sport = :$PORT" 2>/dev/null
}

# 그 포트를 LISTEN 하는 것이 수집기인가 — stop · start · check 가 같은 판정을 쓴다(docs/ops-dashboard OD-29). PIDS 에 리스너 pid 들을 둔다.
#   0 = 모두 수집기 · 1 = 남이다(pid 가 안 보이는 리스너 — 다른 계정 — 도 남이다, ✗ 한 줄을 표준 오류에) · 2 = ss 가 없거나 실패해 모른다(SS_RC)
#   · 3 = 아무도 듣지 않는다
_owned() {
  local _ls _blind p _cmd
  command -v ss >/dev/null 2>&1 || { SS_RC=missing; return 2; }
  SS_RC=0; _ls="$(ss -ltnpH "sport = :$PORT" 2>/dev/null)" || SS_RC=$?
  [ "$SS_RC" = 0 ] || return 2
  [ -n "$_ls" ] || return 3
  _blind="$(printf '%s\n' "$_ls" | grep -vc 'pid=' || true)"
  PIDS="$(printf '%s\n' "$_ls" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true)"
  if [ "${_blind:-0}" != 0 ] || [ -z "$PIDS" ]; then
    echo "✗ :$PORT 를 듣는 리스너가 있는데 pid 가 안 보인다(다른 계정의 프로세스 — 수집기가 아니다) — 건드리지 않는다" >&2; return 1
  fi
  for p in $PIDS; do
    # 명령줄을 먼저 받고 본다 — `… | grep -q` 는 pipefail 아래서 맞은 것을 '아니다' 로 읽을 수 있다(판정 파이프 함정)
    _cmd="$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null || true)"
    # 인자 하나가 수집기 경로로 끝나고 바로 뒤가 serve 여야 한다 — `*llm-status*` 면 인자 어딘가에 그 낱말이 든 남의 프로세스를 죽인다
    case " $_cmd " in
      *"/infra/llm-status/collector.py serve "*) ;;
      *) echo "✗ :$PORT 를 듣는 pid $p 는 LLM/GPU 현황 수집기가 아니다(${_cmd:0:120}) — 건드리지 않는다" >&2; return 1 ;;
    esac
  done
  return 0
}

case "${1:-}" in
  run)
    PY="$(PATH="$SYS_PATH" command -v python3 || true)"
    [ -n "$PY" ] || { echo "✗ 시스템 python3 을 찾지 못했다($SYS_PATH) — 수집기는 표준 라이브러리만 쓰는 시스템 python3 으로 돈다" >&2; exit 1; }
    "$PY" -I -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
      || { echo "✗ $PY 가 3.10 보다 낡았다 — 수집기는 3.10 이상이 필요하다" >&2; exit 1; }
    [ -f "$COLLECTOR" ] || { echo "✗ 수집기가 없다: $COLLECTOR" >&2; exit 1; }
    exec env -i PATH="$SYS_PATH" HOME="${HOME:-/}" LANG=C.UTF-8 \
      ${LLM_STATUS_STATE_DIR:+"LLM_STATUS_STATE_DIR=$LLM_STATUS_STATE_DIR"} ${LLM_STATUS_ENV_FILE:+"LLM_STATUS_ENV_FILE=$LLM_STATUS_ENV_FILE"} \
      "$PY" -I -B "$COLLECTOR" serve --port "$PORT"
    ;;
  start)
    # 이미 듣는 것이 있으면 수집기인지 본다 — 남의 앱이면 '이미 떠 있다' 로 0 을 내지 않고 크게 실패한다(OD-29). ss 를 못 쓰면(2) 종전대로 띄운다.
    _orc=0; _owned || _orc=$?
    case "$_orc" in
      0) echo "· :$PORT 에 이미 듣는 수집기가 있다(pid $(echo $PIDS)) — 띄우지 않는다(다시 띄우려면 stop 뒤 start)"; exit 0 ;;
      1) echo "✗ :$PORT 를 수집기가 아닌 프로세스가 듣는다(위 ✗ 줄) — 띄우지 않았다. 그 포트를 비우거나 infra/.env 의 LLM_STATUS_PORT 를 바꾼다(docs/PORT-MAP.md)" >&2
         exit 1 ;;
    esac
    [ -n "$(envv LLM_STATUS "$ENV_FILE" || true)" ] \
      || echo "⚠ infra/.env 에 LLM_STATUS 가 없다 — 띄우기는 하지만 다음 update-all(5d)이 내린다. 늘 돌리려면 LLM_STATUS=1 을 적는다" >&2
    ( umask 077; mkdir -p "$LOG_DIR" ); chmod 700 "$LOG_DIR" 2>/dev/null || true
    ( umask 077; : >> "$LOG" ); chmod 600 "$LOG" 2>/dev/null || true
    printf '\n=== start %s: llm-status.sh start\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$LOG"
    nohup bash "$SELF" run >> "$LOG" 2>&1 < /dev/null &
    _pid=$!
    disown "$_pid" 2>/dev/null || true
    for _ in $(seq 1 50); do
      if ! kill -0 "$_pid" 2>/dev/null; then
        echo "✗ 수집기가 곧바로 끝났다 — 로그 $LOG 끝을 본다:" >&2; tail -n 5 "$LOG" >&2 || true; exit 1
      fi
      _ls="$(_listeners || true)"
      [ -n "$_ls" ] && { echo "✓ LLM/GPU 현황 수집기를 뒤에서 띄웠다 — 127.0.0.1:$PORT (pid $_pid · 로그 $LOG)"; exit 0; }
      sleep 0.1
    done
    echo "⚠ 수집기(pid $_pid)가 5초 안에 :$PORT 를 듣지 않는다 — 로그 $LOG 를 본다(뒤에서는 계속 돈다)" >&2; exit 1
    ;;
  probe)
    _body="$(curl -s --noproxy '*' -m 3 "http://127.0.0.1:$PORT/health" 2>/dev/null || true)"
    case "$_body" in
      *'"service":"hwax-llm-status"'*) echo "✓ :$PORT 의 /health 는 LLM/GPU 현황 수집기의 답이다"; exit 0 ;;
      '') echo "· :$PORT 의 /health 가 답하지 않는다"; exit 1 ;;
      *) echo "· :$PORT 의 /health 는 수집기의 답이 아니다(그 포트에 다른 것이 떠 있다 — docs/PORT-MAP.md)"; exit 1 ;;
    esac
    ;;
  check)
    _orc=0; _owned || _orc=$?
    case "$_orc" in
      0) echo "✓ :$PORT 를 듣는 것은 LLM/GPU 현황 수집기다(pid $(echo $PIDS))"; exit 0 ;;
      2) echo "✗ :$PORT 를 듣는 프로세스를 볼 수 없다(ss ${SS_RC}) — 수집기인지 모른다" >&2; exit 1 ;;
      3) echo "✗ :$PORT 를 듣는 프로세스가 없다" >&2; exit 1 ;;
      *) exit 1 ;;
    esac
    ;;
  stop)
    _orc=0; _owned || _orc=$?
    case "$_orc" in
      2) if [ "$SS_RC" = missing ]; then
           echo "✗ ss(iproute2)가 없어 :$PORT 를 듣는 프로세스를 볼 수 없다 — 수집기가 내려갔는지 모른다(내리지 않았다)" >&2
         else
           echo "✗ ss 가 실패했다(rc $SS_RC) — :$PORT 를 듣는 프로세스를 모른다(내리지 않았다)" >&2
         fi
         exit 1 ;;
      3) echo "· :$PORT 를 듣는 프로세스가 없다 — 수집기는 이미 내려가 있다"; exit 0 ;;
      1) exit 1 ;;
    esac
    # 산 것 — 프로세스가 있고 좀비가 아니다(리스너가 사라졌는지로 보지 않는다 — 듣기부터 닫고 정리하는 사이를 '내려갔다' 로 읽는다).
    _alive() { local s; s="$(sed -n 's/.*) //p' "/proc/$1/stat" 2>/dev/null || true)"; [ -n "$s" ] && [ "${s%% *}" != Z ]; }
    _left() { local p out=""; for p in $PIDS; do _alive "$p" && out="$out $p"; done; echo "${out# }"; }
    echo "→ LLM/GPU 현황 수집기 정지(:$PORT, pid $(echo $PIDS))"
    kill -TERM $PIDS 2>/dev/null || true
    for _ in $(seq 1 100); do
      [ -z "$(_left)" ] && { echo "✓ 내려갔다"; exit 0; }
      sleep 0.1
    done
    LEFT="$(_left)"
    echo "  ⚠ 10초 안에 내려가지 않아 KILL 한다(pid $LEFT)"
    kill -KILL $LEFT 2>/dev/null || true
    for _ in $(seq 1 30); do [ -z "$(_left)" ] && { echo "✓ 내려갔다(KILL)"; exit 0; }; sleep 0.1; done
    echo "✗ KILL 뒤에도 pid $(_left) 가 남았다" >&2; exit 1
    ;;
  *)
    echo "사용법: $(basename "$0") {run|start|stop|probe|check}" >&2; exit 2 ;;
esac
