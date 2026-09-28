#!/usr/bin/env bash
# ste 헤드노드 SSH 터널(15810·15812)을 systemd 유저 유닛으로 설치한다 — teleport 박스(cae00) 전용
#
#   ./infra/scripts/install-ste-tunnel.sh            # 설치 + enable --now + 두 포트 확인
#   ./infra/scripts/install-ste-tunnel.sh remove     # disable + 제거
#   ./infra/scripts/install-ste-tunnel.sh --check    # 설치 여부·포트 두 개만 확인(쓰기 없음)
#
# 값은 SmartTwinExplorer/deploy/transport.env(gitignore) 에서 읽는다 — 이 리포에 박스 고유값을 두지 않는다.
# direct 박스(dev VM)는 포털이 헤드에 직결이라 터널이 필요 없다 → 아무것도 안 하고 0 으로 끝난다.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UNIT_SRC="$ROOT/infra/systemd/ste-tunnel.service"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/ste-tunnel.service"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*" >&2; }
die() { bad "$*"; exit 1; }

# ⚠ `|| echo 000` 을 붙이지 않는다 — curl 은 연결 실패에도 -w 로 이미 000 을 찍어서, 둘이 겹쳐 '000000' 이 됐다
# (사용자 화면 실측). 값은 curl 이 찍은 것을 쓰고 rc 만 삼킨다.
_code() { local c; c="$(curl -s -o /dev/null -w '%{http_code}' -m "${2:-4}" "$1" 2>/dev/null)" || true; printf '%s' "${c:-000}"; }

# 그 포트를 **누가** 듣고 있나 — 주소까지 보여 준다. 개수만 세면 '있다/없다' 만 알고 원인을 못 가른다.
_port_line() { ss -ltnpH "sport = :$1" 2>/dev/null | sed "s/^/      :$1 /" ; }
_port_pids() { ss -ltnpH "sport = :$1" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || true; }   # 무일치(=아무도 안 듣는다)는 실패가 아니다

# 유닛이 아닌 **우리 소유 ssh 터널**이 그 포트를 잡고 있나. 이게 있으면 유닛의 -L 바인드가 실패하고
# (ExitOnForwardFailure=yes) 유닛은 영원히 재시도한다 — 그동안 옛 프로세스가 15810 만 열고 있어
# "15810 은 200, 15812 는 000, 유닛은 active" 라는 정확히 헷갈리는 모양이 된다.
# 판정을 좁게 잡는다(포트킬 오살 방지 규율): LISTEN · 그 루프백 포트 · comm=ssh · cmdline 에 -L 127.0.0.1:1581 · 유닛 MainPID 아님.
# 아래 셋은 시험에서 바꿔 끼운다 — 고르는 규칙이 이 스크립트에서 가장 위험한 부분이라(남의 프로세스를
# 죽이면 안 된다) 실제 프로세스 없이도 규칙을 검사할 수 있어야 한다.
_unit_mainpid() { systemctl --user show -p MainPID --value ste-tunnel.service 2>/dev/null || echo 0; }
_pid_comm()     { cat "/proc/$1/comm" 2>/dev/null; }
_pid_cmdline()  { tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null; }
_stray_pids() {
  local main p out=""
  main="$(_unit_mainpid)"
  for p in $(_port_pids 15810) $(_port_pids 15812); do
    [ "$p" = "${main:-0}" ] && continue
    [ "$(_pid_comm "$p")" = ssh ] || continue
    _pid_cmdline "$p" | grep -q -- '-L 127.0.0.1:1581' || continue
    case " $out " in *" $p "*) ;; *) out="$out $p" ;; esac
  done
  printf '%s' "${out# }"
}

# 터널 두 포트가 실제로 답하나 — 살아 있으면 15810 /api/health 200, 15812 /mcp 406(Accept 없음) 또는 200.
# 죽었으면 000. 유닛이 active 라도 포워딩이 안 된 상태를 여기서 가른다(dev 실측 기준).
check_ports() {
  local h m
  h="$(_code http://127.0.0.1:15810/api/health)"
  m="$(_code http://127.0.0.1:15812/mcp)"
  [ "$h" = 200 ] && ok "15810 (웹/REST) → 200" || bad "15810 (웹/REST) → $h"
  case "$m" in 200|405|406) ok "15812 (MCP) → $m" ;; *) bad "15812 (MCP) → $m  ← 게이트웨이 ste 도구 8종이 안 뜨는 원인" ;; esac
  [ "$h" = 200 ] && case "$m" in 200|405|406) return 0 ;; esac
  return 1
}

# 15812 가 안 되는 두 가지를 가른다 — (a) 로컬에 리스너가 없다(유닛이 그 포트를 안 연다/못 연다)
# (b) 리스너는 있는데 000(터널은 열렸고 **헤드 쪽 연결**이 거부됐다). 종전엔 둘 다 '000' 하나로 보였다.
explain_15812() {
  local n; n="$(_port_pids 15812 | wc -l)"
  echo "    로컬 리스너:"; _port_line 15810; _port_line 15812
  if [ "$n" = 0 ]; then
    echo "    → 127.0.0.1:15812 를 **아무도 듣지 않는다**. 유닛이 그 포트를 안 열거나(옛 손 유닛) 바인드에 실패했다."
  else
    echo "    → 포트는 열려 있는데 000 이다. 터널은 섰고 **헤드에서 127.0.0.1:15812 로 가는 연결이 거부**된 것이다."
    echo "       헤드에서 볼 것: systemctl is-active ste-mcp · ss -ltn | grep 15812 (주소가 0.0.0.0 인가) ·"
    echo "       curl -o /dev/null -w '%{http_code}' http://127.0.0.1:15812/mcp  (헤드 자기 자신에서 406/200 이면 터널 문제다)"
  fi
  journalctl --user -u ste-tunnel -n 8 --no-pager -o cat 2>/dev/null | sed 's/^/    journal: /'
}

# ── transport.env — --check 도 이것을 본다(direct 박스는 터널이 필요 없는데 '유닛 없음·000' 빨강을 냈다, 2026-09-28 dev 실측) ──
TENV=""
for c in "$ROOT/../SmartTwinExplorer/deploy/transport.env" "$HOME/SmartTwinExplorer/deploy/transport.env"; do
  [ -f "$c" ] && { TENV="$c"; break; }
done
# 값 읽기는 **정본 규칙**(update-all `_envfile_value`·services.py `_infra_value`·ste-doctor `envv`)과 같다 — 마지막 줄이 이기고
# `export `·인라인 주석·따옴표·CR 을 벗긴다. 종전 `_v` 는 첫 줄·주석 미처리라 `TRANSPORT_MODE=teleport  # 운영` 이
# `teleport#운영` 으로 읽혀 "모른다" 로 죽었다(transport.sh 는 bash 로 소싱해 teleport 로 읽는다 — 두 독자가 달랐다).
_v() {
  [ -n "$TENV" ] || return 0
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$1=//p" "$TENV" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'
}
MODE="$(_v TRANSPORT_MODE)"

if [ "${1:-}" = "remove" ]; then
  systemctl --user disable --now ste-tunnel.service 2>/dev/null || true
  rm -f "$UNIT"; systemctl --user daemon-reload
  ok "removed ste-tunnel.service"; exit 0
fi
if [ "${1:-}" = "--check" ]; then
  if [ "$MODE" = direct ]; then
    ok "transport 가 direct 다 — 포털이 헤드에 직결이라 터널이 필요 없다($TENV)"; exit 0
  fi
  if [ -f "$UNIT" ]; then
    ok "유닛 설치됨: $UNIT ($(systemctl --user is-active ste-tunnel 2>/dev/null || echo unknown))"
    # 파일이 있어도 옛 손 유닛이면 15810 만 연다 — -L 목록을 본다(cae00 실측 2026-09-27)
    if grep -q -- '-L 127.0.0.1:15812:' "$UNIT"; then ok "유닛에 -L 15812 있음"
    else bad "유닛에 -L 15812 포워딩이 없다(옛 손 유닛) — 인자 없이 다시 실행하면 리포 유닛으로 덮어쓰고 재기동한다"; fi
  else bad "유닛 없음: $UNIT"; fi
  # ⚠ `check_ports; _cp=$?` 로 쓰면 안 된다 — 이 스크립트는 set -e 라 check_ports 가 1 을 내는 순간 **여기서 끝나고**
  #   아래 진단(리스너·원인 분기·옛 터널)이 한 번도 안 돌았다(2026-09-28 dev 실측: rc 1 인데 진단 0줄). 종전 판의
  #   '로컬 리스너' 줄도 같은 이유로 죽은 코드였다.
  _cp=0; check_ports || _cp=$?
  if [ "$_cp" != 0 ]; then
    explain_15812
    _st="$(_stray_pids)"
    [ -n "$_st" ] && bad "유닛이 아닌 ssh 가 그 포트를 잡고 있다(pid $_st) — 인자 없이 실행하면 그것을 내리고 유닛으로 다시 세운다"
  fi
  exit $_cp
fi

# ── 설치 — transport.env 가 있어야 한다(값은 위에서 읽었다) ─────────────────────────────
[ -n "$TENV" ] || die "SmartTwinExplorer/deploy/transport.env 가 없다 — 런북 §4(접속 설정)가 먼저다"
case "$MODE" in
  direct)
    ok "transport 가 direct 다 — 포털이 헤드에 직결이라 터널이 필요 없다(아무것도 안 함)"; exit 0 ;;
  teleport) ;;
  *) die "transport.env 의 TRANSPORT_MODE 가 비었거나 모른다: '$MODE'" ;;
esac
REMOTE_USER="$(_v REMOTE_USER)"; HEAD_NODE="$(_v HEAD_NODE)"; TP_CLUSTER="$(_v TP_CLUSTER)"
SSH_CONFIG="$(_v TELEPORT_SSH_CONFIG)"
[ -n "$REMOTE_USER" ] && [ -n "$HEAD_NODE" ] && [ -n "$TP_CLUSTER" ] && [ -n "$SSH_CONFIG" ] \
  || die "transport.env 의 teleport 값이 비었다(REMOTE_USER·HEAD_NODE·TP_CLUSTER·TELEPORT_SSH_CONFIG)"
SSH_CONFIG="${SSH_CONFIG/#\~/$HOME}"
[ -f "$SSH_CONFIG" ] || die "Teleport ssh_config 가 없다: $SSH_CONFIG  (tsh login → tsh config > 그 경로, 런북 §4)"
# transport.sh 와 같은 규칙 — 접미사를 빠뜨리면 Host *.<클러스터> 에 안 잡혀 DNS 로 새어 조용히 실패한다.
TARGET="$REMOTE_USER@$HEAD_NODE.$TP_CLUSTER"

# ── 설치 ────────────────────────────────────────────────────────────────────
# $USER 는 로그인 셸이 세운다 — cron·systemd 타이머 같은 축소된 환경에는 없어서 set -u 가 여기서 스크립트를 죽였다
# (2026-09-28 진입점 시험 실측: 'USER: unbound variable'). 이름은 id 로 직접 묻는다.
_me="${USER:-$(id -un)}"
if [ ! -e "/var/lib/systemd/linger/$_me" ]; then
  # 비대화식(update-all 안)에서는 sudo 프롬프트로 갱신을 매달지 않는다 — 건너뛰고 무엇이 남았는지 말한다.
  if [ -t 0 ] && [ "${STE_TUNNEL_NONINTERACTIVE:-0}" != 1 ]; then
    echo "→ linger 켜기(sudo, 1회) — 로그아웃·재부팅에도 터널이 산다"
    sudo loginctl enable-linger "$_me"
  else
    echo "  ○ linger 미설정 — 지금은 건너뛴다(비대화식). 로그아웃·재부팅 뒤에도 터널이 살게 하려면 한 번:"
    echo "      sudo loginctl enable-linger $_me"
  fi
fi
mkdir -p "$UNIT_DIR"
sed -e "s#__SSH_CONFIG__#$SSH_CONFIG#g" -e "s#__TARGET__#$TARGET#g" "$UNIT_SRC" > "$UNIT"
systemctl --user daemon-reload
systemctl --user enable --now ste-tunnel.service
# 방금 설치했으면 바뀐 -L 목록이 반영되게 재기동한다(enable --now 는 이미 떠 있으면 안 바꾼다).
systemctl --user restart ste-tunnel.service
ok "ste-tunnel.service 설치·기동 (→ $TARGET, 15810·15812)"
sleep 3
if check_ports; then ok "터널 두 포트 확인"; else
  # 가장 흔한 뿌리를 여기서 직접 걷어낸다 — 옛 손 터널이 15810 을 쥐고 있으면 유닛은 바인드에 실패해
  # 영원히 재시도하고, 사람 눈에는 "15810 은 되는데 15812 만 안 된다" 로 보인다(cae00 증상과 일치).
  _st="$(_stray_pids)"
  if [ -n "$_st" ] && [ "${STE_TUNNEL_NO_KILL:-0}" != 1 ]; then
    bad "유닛이 아닌 ssh 터널이 포트를 쥐고 있다(pid $_st) — 내리고 유닛으로 다시 세운다"
    ps -o pid,lstart,args -p $_st 2>/dev/null | sed 's/^/      /' || true
    kill $_st 2>/dev/null || true
    for _i in 1 2 3 4 5 6 7 8 9 10; do
      [ -z "$(_stray_pids)" ] && break; sleep 1
    done
    systemctl --user restart ste-tunnel.service; sleep 3
    if check_ports; then ok "옛 터널을 걷어내고 두 포트 확인"; echo "관리:  systemctl --user {status|restart|stop} ste-tunnel"; exit 0; fi
  elif [ -n "$_st" ]; then
    bad "유닛이 아닌 ssh 터널이 포트를 쥐고 있다(pid $_st) — STE_TUNNEL_NO_KILL=1 이라 손대지 않았다. 수동: kill $_st"
  fi
  bad "터널이 포트를 못 열었다 — Teleport 세션(tsh status)과 아래를 본다"
  explain_15812
  exit 1
fi
echo "관리:  systemctl --user {status|restart|stop} ste-tunnel   로그: journalctl --user -u ste-tunnel -f"
