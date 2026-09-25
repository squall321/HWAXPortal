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

# 터널 두 포트가 실제로 답하나 — 살아 있으면 15810 /api/health 200, 15812 /mcp 406(Accept 없음) 또는 200.
# 죽었으면 000. 유닛이 active 라도 포워딩이 안 된 상태를 여기서 가른다(dev 실측 기준).
check_ports() {
  local h m
  h="$(curl -s -o /dev/null -w '%{http_code}' -m 4 http://127.0.0.1:15810/api/health 2>/dev/null || echo 000)"
  m="$(curl -s -o /dev/null -w '%{http_code}' -m 4 http://127.0.0.1:15812/mcp 2>/dev/null || echo 000)"
  [ "$h" = 200 ] && ok "15810 (웹/REST) → 200" || bad "15810 (웹/REST) → $h"
  case "$m" in 200|405|406) ok "15812 (MCP) → $m" ;; *) bad "15812 (MCP) → $m  ← 게이트웨이 ste 도구 8종이 안 뜨는 원인" ;; esac
  [ "$h" = 200 ] && case "$m" in 200|405|406) return 0 ;; esac
  return 1
}

if [ "${1:-}" = "remove" ]; then
  systemctl --user disable --now ste-tunnel.service 2>/dev/null || true
  rm -f "$UNIT"; systemctl --user daemon-reload
  ok "removed ste-tunnel.service"; exit 0
fi
if [ "${1:-}" = "--check" ]; then
  if [ -f "$UNIT" ]; then ok "유닛 설치됨: $UNIT ($(systemctl --user is-active ste-tunnel 2>/dev/null || echo unknown))"
  else bad "유닛 없음: $UNIT"; fi
  check_ports; exit $?
fi

# ── transport.env 에서 값 읽기 ─────────────────────────────────────────────
TENV=""
for c in "$ROOT/../SmartTwinExplorer/deploy/transport.env" "$HOME/SmartTwinExplorer/deploy/transport.env"; do
  [ -f "$c" ] && { TENV="$c"; break; }
done
[ -n "$TENV" ] || die "SmartTwinExplorer/deploy/transport.env 가 없다 — 런북 §4(접속 설정)가 먼저다"
_v() { sed -n "s/^[[:space:]]*$1=[[:space:]]*//p" "$TENV" | head -1 | tr -d '"'"'"' \r'; }
MODE="$(_v TRANSPORT_MODE)"
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
if [ ! -e "/var/lib/systemd/linger/$USER" ]; then
  echo "→ linger 켜기(sudo, 1회) — 로그아웃·재부팅에도 터널이 산다"
  sudo loginctl enable-linger "$USER"
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
  bad "터널이 포트를 못 열었다 — Teleport 세션(tsh status)과 아래 로그를 본다"
  journalctl --user -u ste-tunnel -n 8 --no-pager 2>/dev/null | sed 's/^/    /' || true
  exit 1
fi
echo "관리:  systemctl --user {status|restart|stop} ste-tunnel   로그: journalctl --user -u ste-tunnel -f"
