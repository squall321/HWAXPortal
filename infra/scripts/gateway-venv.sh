#!/usr/bin/env bash
# 게이트웨이 전용 venv(MCP SDK 2.x)를 손으로 보고 · 짓고 · 꾸러미 명령을 받는 창구 — update-all 이 쓰는 lib/gateway-venv.sh 와 같은 판정(docs/mcp-modernize M4)
#
#   ./infra/scripts/gateway-venv.sh check                              # 읽기만 — 이 판이 venv 를 요구하나 · 판 일치 · 지어야 하면 Drive 꾸러미가 있나
#   ./infra/scripts/gateway-venv.sh ensure                             # 지금 짓는다(받기 · 대조 · install.sh) — 게이트웨이를 다시 띄우지는 않는다
#   ./infra/scripts/gateway-venv.sh push-cmd [--python 3.12] [--arch x86_64]   # 바깥에 닿는 박스(dev)에서 — 꾸러미 짓기 · Drive 올리기 두 줄을 찍는다(돌리지 않는다)
#
# ensure 뒤 게이트웨이를 새 venv 로 띄우려면 ./infra/scripts/update-sites.sh mcp-gateway(심의가 돌면 미룬다) 또는 update-all 을 다시 돈다.
# push-cmd 의 --python · --arch 는 받는 박스의 값이다 — update-all 의 ✗ 줄(사람 몫)이 그 박스의 값을 그대로 적어 준다.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/infra/scripts/lib/gateway-venv.sh"

cmd="${1:-}"; shift || true
case "$cmd" in
  check)
    HWAX_GW_VENV_PROBE=1 hwax_gw_venv_prepare; rc=$?
    exit "$rc" ;;
  ensure)
    hwax_gw_venv_ensure; exit $? ;;
  push-cmd)
    pyv="3.12"; arch="$(uname -m)"
    while [ $# -gt 0 ]; do
      case "$1" in
        --python) pyv="${2:-}"; shift 2 ;;
        --arch) arch="${2:-}"; shift 2 ;;
        *) echo "✗ 모르는 인자: $1 (--python · --arch)" >&2; exit 2 ;;
      esac
    done
    hwax_gw_venv_push_cmd "$pyv" "$arch"; exit $? ;;
  *)
    sed -n '2,9p' "$0"; [ -z "$cmd" ] || [ "$cmd" = -h ] || [ "$cmd" = --help ] || exit 2 ;;
esac
