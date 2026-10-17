#!/usr/bin/env bash
# 상시 상태판(Gatus)을 생성 설정으로 앞에서 띄우고(run) 그 포트를 듣는 상태판만 내린다(stop) — docs/improvement-1015/status-board.md
#
#   ./infra/scripts/status-board.sh run     # 앞에서 돈다(services.py 가 떼어 띄운다 — services.yaml status-board)
#   ./infra/scripts/status-board.sh stop    # 그 포트를 LISTEN 하는 프로세스만, 명령줄이 gatus 인지 확인한 뒤 TERM → 기다림 → KILL
#   STATUS_BOARD_PORT=8741 ./infra/scripts/status-board.sh stop    # stop 만 환경의 포트가 infra/.env 보다 먼저다(포트를 바꾼 뒤 옛 포트의 상태판을 내릴 때)
#
# 설정은 이 스크립트가 만들지 않는다 — gen-status-config.py 가 infra/.state/status/config.yaml(디렉터리 700 · 파일 600)에 쓴다(update-all 5b 가
#   STATUS_BOARD 가 있으면 매번 다시 만든다). 없으면 띄우지 않는다. 그 디렉터리를 /config 로 읽기 전용 바인드한다 — 파일 하나를 바인드하면
#   생성기가 이름 바꾸기로 갈아 끼운 새 파일이 컨테이너에 안 보인다(옛 inode 가 남는다). Gatus 는 30초마다 파일 시각을 보고 다시 읽는다.
# 포트 — run 은 늘 infra/.env 의 STATUS_BOARD_PORT(기본 8740)다. 매니페스트 health 와 생성기가 infra/.env 만 읽으므로 운영자 셸에 export 된
#   값으로 띄우면 아무도 보지 않는 포트에 뜬다 — 환경의 값이 다르면 경고 한 줄을 찍고 infra/.env 로 띄운다. 설정의 web 포트·주소가 이 포트와
#   127.0.0.1 이 아니면 띄우지 않는다(생성기를 다시 돌리라고 말한다) — Gatus 의 기본 주소는 0.0.0.0 이고 화면·API 는 인증이 없다.
# run — --cleanenv 로 띄운다(띄운 셸의 프록시·비밀이 딸려 들어가지 않는다 — 검사는 전부 루프백이고, 메일은 SMTP 라 HTTP 프록시와 무관하다).
#   호스트의 CA 묶음이 있으면 이미지의 것 위에 읽기 전용으로 덮는다 — 이미지에는 공개 루트만 있어 사내 CA 로 서명한 SMTP 서버의 STARTTLS 가
#   검증에 실패하고, 그 실패는 상태판 로그 한 줄로만 남는다(경보가 조용히 안 나간다).
#   로그는 WARN 이다 — INFO 는 검사마다 한 줄이라 하루 수 MB 가 /tmp 의 서비스 로그로 쌓인다. 경보 발송 실패는 ERROR 로 남는다.
# stop — 포트로 죽일 때 연결 중인 클라이언트까지 잡으면 남을 죽인다(docs/gotchas.md §1). `ss -ltnp` 의 리스너만 보고, 그 명령줄에 gatus 가
#   없으면 손대지 않고 실패로 끝난다. 아무도 안 들으면 이미 내려간 것이다(0). pid 가 안 보이는 리스너(다른 계정)와 ss 가 없는 박스는 '모른다' 라
#   실패(1)다 — '내려갔다' 로 말하지 않는다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/infra/.env"
CONF_DIR="$ROOT/infra/.state/status"
CONF="$CONF_DIR/config.yaml"

# infra/.env 값 하나 — 정본 규칙(update-all `_envfile_value` · services.py `_infra_value` · llm-router.sh envv)과 같은 한 줄이다.
envv() { LC_ALL=C sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=//p" "$2" 2>/dev/null | tail -1 | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'; }

_port_ok() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; [ "${#1}" -le 5 ] && [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le 65535 ]; }

if [ "${1:-}" = stop ] && [ -n "${STATUS_BOARD_PORT:-}" ]; then
  PORT="$STATUS_BOARD_PORT"; _FROM="환경변수"
else
  PORT="$(envv STATUS_BOARD_PORT "$ENV_FILE" || true)"; PORT="${PORT:-8740}"; _FROM="infra/.env"
fi
if ! _port_ok "$PORT"; then
  echo "✗ STATUS_BOARD_PORT='$PORT'($_FROM) 는 1~65535 의 포트 번호가 아니다(기본 8740)" >&2; exit 2
fi
PORT="$((10#$PORT))"
if [ "${1:-}" = run ] && [ -n "${STATUS_BOARD_PORT:-}" ] && { ! _port_ok "$STATUS_BOARD_PORT" || [ "$((10#$STATUS_BOARD_PORT))" != "$PORT" ]; }; then
  echo "⚠ 환경변수 STATUS_BOARD_PORT=$STATUS_BOARD_PORT 는 run 에서 쓰지 않는다 — 매니페스트·생성기는 infra/.env 만 보므로 infra/.env 의 포트 $PORT 로 띄운다" >&2
fi

case "${1:-}" in
  run)
    [ -f "$CONF" ] || {
      echo "✗ 상태판 설정이 없다: $CONF — 만든다: python3 ./infra/scripts/gen-status-config.py (update-all 5b 가 STATUS_BOARD 가 있으면 매번 만든다)" >&2
      exit 2; }
    # 생성기가 쓰는 web 덩이(두 칸 들여쓴 address·port)를 읽는다 — 손으로 고쳐 모양이 바뀌었으면 '모름' 이라 띄우지 않는다.
    _web="$(sed -n '/^web:/,/^[^[:space:]]/p' "$CONF")"
    _addr="$(printf '%s\n' "$_web" | sed -n -E "s/^[[:space:]]+address:[[:space:]]*['\"]?([^'\"[:space:]]*).*/\1/p" | head -1)"
    _cport="$(printf '%s\n' "$_web" | sed -n -E "s/^[[:space:]]+port:[[:space:]]*['\"]?([0-9]+).*/\1/p" | head -1)"
    if [ "$_addr" != 127.0.0.1 ] || [ "$_cport" != "$PORT" ]; then
      echo "✗ 설정의 web 이 127.0.0.1:$PORT 가 아니다(address='${_addr:-없음}' · port='${_cport:-없음}') — 화면은 인증이 없어 루프백에만 띄운다." >&2
      echo "  설정을 다시 만든다: python3 ./infra/scripts/gen-status-config.py (infra/.env 의 STATUS_BOARD_PORT 를 바꿨으면 그 뒤에)" >&2
      exit 2
    fi
    SIF="$ROOT/infra/apptainer/gatus.sif"
    [ -f "$SIF" ] || {
      echo "✗ 상태판 이미지가 없다: $SIF — 운영 박스는 ./infra/scripts/images-from-drive.sh, dev 는 ./infra/scripts/build-gatus.sh" >&2
      exit 1; }
    # apptainer 찾기는 llm-router.sh 와 같다(리포 안 bin-*/ 의 가장 새 것 → PATH). _common.sh 를 소싱하지 않는 것은 그쪽이 infra/.env 를
    # set -a 로 통째로 export 하기 때문이다(--cleanenv 가 막아도 이 셸에 비밀을 올릴 까닭이 없다).
    A="${APPTAINER:-}"
    if [ -z "$A" ]; then
      for _c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$_c" ] && A="$_c"; done
    fi
    A="${A:-apptainer}"
    command -v "$A" >/dev/null 2>&1 || { echo "✗ apptainer 를 찾지 못했다($A) — ./infra/scripts/bootstrap.sh" >&2; exit 1; }
    _ca=()
    for _b in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
      [ -r "$_b" ] && { _ca=(--bind "$(readlink -f "$_b"):/etc/ssl/certs/ca-certificates.crt:ro"); break; }
    done
    exec "$A" exec --cleanenv --bind "$CONF_DIR:/config:ro" ${_ca[@]+"${_ca[@]}"} \
      --env GATUS_CONFIG_PATH=/config/config.yaml --env GATUS_LOG_LEVEL=WARN \
      "$SIF" /gatus
    ;;
  stop)
    command -v ss >/dev/null 2>&1 || {
      echo "✗ ss(iproute2)가 없어 :$PORT 를 듣는 프로세스를 볼 수 없다 — 상태판이 내려갔는지 모른다(내리지 않았다)" >&2; exit 1; }
    _ss_rc=0; _ls="$(ss -ltnpH "sport = :$PORT" 2>/dev/null)" || _ss_rc=$?
    if [ "$_ss_rc" != 0 ]; then
      echo "✗ ss 가 실패했다(rc $_ss_rc) — :$PORT 를 듣는 프로세스를 모른다(내리지 않았다)" >&2; exit 1
    fi
    if [ -z "$_ls" ]; then
      echo "· :$PORT 를 듣는 프로세스가 없다 — 상태판은 이미 내려가 있다"; exit 0
    fi
    _blind="$(printf '%s\n' "$_ls" | grep -vc 'pid=' || true)"
    PIDS="$(printf '%s\n' "$_ls" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true)"
    if [ "${_blind:-0}" != 0 ] || [ -z "$PIDS" ]; then
      echo "✗ :$PORT 를 듣는 리스너가 있는데 pid 가 안 보인다(다른 계정의 프로세스 — 상태판이 아니다) — 건드리지 않는다" >&2; exit 1
    fi
    for p in $PIDS; do
      # 명령줄을 먼저 받고 본다 — `… | grep -q` 는 pipefail 아래서 맞은 것을 '아니다' 로 읽을 수 있다(판정 파이프 함정)
      _cmd="$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null || true)"
      # 앞에 빈칸을 붙여 견준다 — 진짜 Gatus 의 명령줄은 `/gatus` 하나라(첫 인자) 앞에 빈칸이 없다. 붙이지 않으면 진짜 상태판을 '아니다' 로
      #   거부했다(2026-10-17 dev 실측 — 시험의 가짜는 `python -c … /gatus` 라 맞았다).
      case " $_cmd" in
        # 인자 하나가 정확히 /gatus 여야 한다 — `*gatus*` 면 인자 어딘가에 gatus 가 든 남의 프로세스도 죽였다(호출 추적 반대 검토 LOW-6 과 같은 꼴).
        *" /gatus "*) ;;
        *) echo "✗ :$PORT 를 듣는 pid $p 는 상태판(gatus)이 아니다(${_cmd:0:120}) — 건드리지 않는다" >&2; exit 1 ;;
      esac
    done
    # 산 것 — 프로세스가 있고 좀비가 아니다(리스너가 사라졌는지로 보지 않는다 — 듣기부터 닫고 정리하는 사이를 '내려갔다' 로 읽는다).
    _alive() { local s; s="$(sed -n 's/.*) //p' "/proc/$1/stat" 2>/dev/null || true)"; [ -n "$s" ] && [ "${s%% *}" != Z ]; }
    _left() { local p out=""; for p in $PIDS; do _alive "$p" && out="$out $p"; done; echo "${out# }"; }
    echo "→ 상태판 정지(:$PORT, pid $(echo $PIDS))"
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
