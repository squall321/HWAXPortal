#!/usr/bin/env bash
# 호출 추적(Phoenix)을 루프백 한 포트로 앞에서 띄우고(run) 그 포트를 듣는 Phoenix 만 내린다(stop) — docs/improvement-1015/call-trace.md
#
#   ./infra/scripts/call-trace.sh run     # 앞에서 돈다(services.py 가 떼어 띄운다 — services.yaml call-trace)
#   ./infra/scripts/call-trace.sh stop    # 그 포트를 LISTEN 하는 프로세스만, 명령줄이 Phoenix 인지 확인한 뒤 TERM → 기다림 → KILL
#   CALL_TRACE_PORT=8752 ./infra/scripts/call-trace.sh stop    # stop 만 환경의 포트가 infra/.env 보다 먼저다(포트를 바꾼 뒤 옛 포트의 것을 내릴 때)
#
# 포트 — run 은 늘 infra/.env 의 CALL_TRACE_PORT(기본 8750)다. 매니페스트 health 가 infra/.env 만 읽으므로 운영자 셸에 export 된 값으로 띄우면
#   아무도 보지 않는 포트에 뜬다 — 환경의 값이 다르면 경고 한 줄을 찍고 infra/.env 로 띄운다(status-board.sh 와 같다).
# 듣는 곳 — 127.0.0.1 하나뿐이다. 화면·API·수신에 로그인이 없다(PHOENIX_ENABLE_AUTH 를 켜지 않는다 — 사람은 SSH 터널로 본다). Phoenix 의
#   gRPC 수신기는 늘 모든 인터페이스([::])에 열리므로 띄우는 셈(infra/call-trace/phoenix_serve.py)이 끈다 — 기록기는 웹 포트로만 보낸다.
# 저장 — infra/.state/call-trace/(700, gitignore)의 SQLite 하나다(PHOENIX_WORKING_DIR). 홈은 붙이지 않는다(--no-home).
# 보존 — CALL_TRACE_RETENTION_DAYS(기본 30일). Phoenix 는 이 값을 **DB 를 처음 만들 때만** 기본 정책으로 넣고(매주 일요일 0시 UTC 에 지운다),
#   정책이 이미 있으면 보지 않는다 — 나중에 바꾸려면 Phoenix 화면의 설정에서 바꾼다(docs/improvement-1015/call-trace.md).
# run — --cleanenv 로 띄운다(띄운 셸의 프록시·비밀이 딸려 들어가지 않는다). Phoenix 가 스스로 공용 인터넷으로 나가는 것(글꼴·원격 측정·
#   WASM 받기)을 끄고, 쓰지 않는 기능(에이전트 도우미와 그 서버 쪽 bash · /mcp · 코드 샌드박스)을 끈다. 로그는 WARNING 부터다 — INFO 는
#   수신마다 한 줄이고 DB 이행은 SQL 을 통째로 찍어 /tmp 의 서비스 로그로 쌓인다.
# stop — 포트로 죽일 때 연결 중인 클라이언트까지 잡으면 남을 죽인다(docs/gotchas.md §1). `ss -ltnp` 의 리스너만 보고, 그 명령줄에
#   phoenix 가 없으면 손대지 않고 실패로 끝난다. 아무도 안 들으면 이미 내려간 것이다(0). pid 가 안 보이는 리스너(다른 계정)와 ss 가 없는
#   박스는 '모른다' 라 실패(1)다 — '내려갔다' 로 말하지 않는다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/infra/.env"
STATE="$ROOT/infra/.state/call-trace"

# infra/.env 값 하나 — 정본 규칙(update-all `_envfile_value` · services.py `_infra_value` · status-board.sh envv)과 같은 한 줄이다.
envv() { LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=//p" "$2" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'; }

_port_ok() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ "${#1}" -le 5 ] && [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le 65535 ]; }

if [ "${1:-}" = stop ] && [ -n "${CALL_TRACE_PORT:-}" ]; then
  PORT="$CALL_TRACE_PORT"; _FROM="환경변수"
else
  PORT="$(envv CALL_TRACE_PORT "$ENV_FILE" || true)"; PORT="${PORT:-8750}"; _FROM="infra/.env"
fi
if ! _port_ok "$PORT"; then
  echo "✗ CALL_TRACE_PORT='$PORT'($_FROM) 는 1~65535 의 포트 번호가 아니다(기본 8750)" >&2; exit 2
fi
PORT="$((10#$PORT))"
if [ "${1:-}" = run ] && [ -n "${CALL_TRACE_PORT:-}" ] && { ! _port_ok "$CALL_TRACE_PORT" || [ "$((10#$CALL_TRACE_PORT))" != "$PORT" ]; }; then
  echo "⚠ 환경변수 CALL_TRACE_PORT=$CALL_TRACE_PORT 는 run 에서 쓰지 않는다 — 매니페스트는 infra/.env 만 보므로 infra/.env 의 포트 $PORT 로 띄운다" >&2
fi

case "${1:-}" in
  run)
    DAYS="$(envv CALL_TRACE_RETENTION_DAYS "$ENV_FILE" || true)"; DAYS="${DAYS:-30}"
    case "$DAYS" in
      ''|*[!0-9]*) echo "✗ CALL_TRACE_RETENTION_DAYS='$DAYS' 는 날 수(0 이상의 정수 — 0 은 지우지 않는다)가 아니다(기본 30)" >&2; exit 2 ;;
    esac
    [ "${#DAYS}" -le 5 ] || { echo "✗ CALL_TRACE_RETENTION_DAYS=$DAYS 는 너무 크다(5자리까지)" >&2; exit 2; }
    DAYS="$((10#$DAYS))"
    SIF="$ROOT/infra/apptainer/phoenix.sif"
    [ -f "$SIF" ] || {
      echo "✗ 호출 추적 이미지가 없다: $SIF — 운영 박스는 ./infra/scripts/images-from-drive.sh, dev 는 ./infra/scripts/build-phoenix.sh" >&2
      exit 1; }
    # apptainer 찾기는 status-board.sh 와 같다(리포 안 bin-*/ 의 가장 새 것 → PATH). _common.sh 를 소싱하지 않는 것은 그쪽이 infra/.env 를
    # set -a 로 통째로 export 하기 때문이다(--cleanenv 가 막아도 이 셸에 비밀을 올릴 까닭이 없다).
    A="${APPTAINER:-}"
    if [ -z "$A" ]; then
      for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
    fi
    A="${A:-apptainer}"
    command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A) — ./infra/scripts/bootstrap.sh" >&2; exit 1; }
    ( umask 077; mkdir -p "$STATE" ) && chmod 700 "$STATE"
    # 상태 디렉터리(SQLite 하나)는 Phoenix 하나만 쓴다 — 포트를 바꾸고 옛 것을 안 내리면 update-sites 가 새 포트에 둘째를 띄워 둘이 같은 DB 를
    # 쓰게 된다(반대 검토 LOW-5). 잠금 fd 는 아래 exec 로 Phoenix 가 물려받아 사는 동안 쥔다(2026-10-16 dev — apptainer 1.3.6 로 확인).
    exec 9>>"$STATE/.lock"
    if ! flock -n 9; then
      echo "✗ 다른 Phoenix 가 이 상태 디렉터리($STATE)를 쓰고 있다 — 포트를 바꿨다면 옛 포트의 것을 먼저 내린다:" \
           "CALL_TRACE_PORT=<옛 포트> ./infra/scripts/call-trace.sh stop" >&2
      exit 1
    fi
    exec "$A" exec --cleanenv --no-home --bind "$STATE:/state" --bind "$ROOT/infra/call-trace:/hwax:ro" \
      --env PHOENIX_HOST=127.0.0.1 --env "PHOENIX_PORT=$PORT" --env PHOENIX_WORKING_DIR=/state \
      --env "PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=$DAYS" \
      --env PHOENIX_ALLOW_EXTERNAL_RESOURCES=false --env PHOENIX_TELEMETRY_ENABLED=false \
      --env PHOENIX_DISABLE_AGENT_ASSISTANT=true --env PHOENIX_AGENTS_DISABLE_BASH=true --env PHOENIX_ENABLE_MCP_SERVER=false \
      --env PHOENIX_ALLOWED_SANDBOX_PROVIDERS=NONE \
      --env PHOENIX_LOGGING_LEVEL=warning --env PHOENIX_LOG_MIGRATIONS=false --env PYTHONNOUSERSITE=1 --env PYTHONDONTWRITEBYTECODE=1 \
      "$SIF" /usr/bin/python3.13 /hwax/phoenix_serve.py serve
    ;;
  stop)
    command -v ss >/dev/null 2>&1 || {
      echo "✗ ss(iproute2)가 없어 :$PORT 를 듣는 프로세스를 볼 수 없다 — 호출 추적이 내려갔는지 모른다(내리지 않았다)" >&2; exit 1; }
    _ss_rc=0; _ls="$(ss -ltnpH "sport = :$PORT" 2>/dev/null)" || _ss_rc=$?
    if [ "$_ss_rc" != 0 ]; then
      echo "✗ ss 가 실패했다(rc $_ss_rc) — :$PORT 를 듣는 프로세스를 모른다(내리지 않았다)" >&2; exit 1
    fi
    if [ -z "$_ls" ]; then
      echo "· :$PORT 를 듣는 프로세스가 없다 — 호출 추적은 이미 내려가 있다"; exit 0
    fi
    _blind="$(printf '%s\n' "$_ls" | grep -vc 'pid=' || true)"
    PIDS="$(printf '%s\n' "$_ls" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true)"
    if [ "${_blind:-0}" != 0 ] || [ -z "$PIDS" ]; then
      echo "✗ :$PORT 를 듣는 리스너가 있는데 pid 가 안 보인다(다른 계정의 프로세스 — 호출 추적이 아니다) — 건드리지 않는다" >&2; exit 1
    fi
    for p in $PIDS; do
      # 명령줄을 먼저 받고 본다 — `… | grep -q` 는 pipefail 아래서 맞은 것을 '아니다' 로 읽을 수 있다(판정 파이프 함정)
      _cmd="$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null || true)"
      # 인자 하나가 정확히 띄우는 셈의 경로여야 한다 — `*phoenix*` 면 인자 어딘가에 phoenix 가 든 남의 프로세스(예 --directory …/phoenix-notes)를
      # 죽였다(반대 검토 LOW-6).
      case " $_cmd" in
        *" /hwax/phoenix_serve.py "*) ;;
        *) echo "✗ :$PORT 를 듣는 pid $p 는 호출 추적(phoenix)이 아니다(${_cmd:0:120}) — 건드리지 않는다" >&2; exit 1 ;;
      esac
    done
    # 산 것 — 프로세스가 있고 좀비가 아니다(리스너가 사라졌는지로 보지 않는다 — 듣기부터 닫고 정리하는 사이를 '내려갔다' 로 읽는다).
    _alive() { local s; s="$(sed -n 's/.*) //p' "/proc/$1/stat" 2>/dev/null || true)"; [ -n "$s" ] && [ "${s%% *}" != Z ]; }
    _left() { local p out=""; for p in $PIDS; do _alive "$p" && out="$out $p"; done; echo "${out# }"; }
    echo "→ 호출 추적 정지(:$PORT, pid $(echo $PIDS))"
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
    echo "사용법: $(basename "$0") {run|stop}" >&2; exit 2 ;;
esac
