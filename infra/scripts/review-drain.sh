#!/usr/bin/env bash
# 리스크 검토 비우기 깃발(에이전트 서버 /drain)을 사람이 보고·세우고·내리는 얇은 감싸개
#
#   ./infra/scripts/review-drain.sh                  # = status
#   ./infra/scripts/review-drain.sh status           # 깃발(scope·세운 주체·남은 수명·고정)과 도는 카드 대조·심의 수
#   ./infra/scripts/review-drain.sh on [--ttl N]     # scope all — 새 카드 대조·새 패널을 멈춘다. 수명 N초(기본 1800, 21600 에서 자른다)
#   ./infra/scripts/review-drain.sh on --hold        # 사람의 고정 — 수명 없이 내릴 때까지. update-all 은 이 깃발을 건드리지 않는다
#   ./infra/scripts/review-drain.sh off [--force]    # 내린다. 남이 세웠거나 고정이면 --force
#
# 세운 주체는 human:<로그인 이름> 이다 — 내리는 쪽이 같은 이름이어야 하고, 아니면 --force. update-all 이 세운 깃발(by update-all)은
# update-all 이 끝에서 정리한다. 주소는 HWAX_AGENT_URL(기본 http://127.0.0.1:9009). 규칙과 종료코드는 lib/review-drain.sh 다 —
# 0 됐다 · 2 서버가 받지 않는다 · 3 /drain 을 모른다(옛 판) · 4 매달렸다 · 5 남의 깃발(건드리지 않았다) · 6 거절.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$ROOT/infra/scripts/lib/review-drain.sh"

usage() { sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }
by="human:${USER:-$(id -un)}"
cmd="${1:-status}"; [ $# -gt 0 ] && shift
ttl=1800; hold=0; force=0
while [ $# -gt 0 ]; do
  case "$1" in
    --ttl) ttl="${2:-}"; shift 2 || { usage >&2; exit 64; } ;;
    --hold) hold=1; shift ;;
    --force) force=1; shift ;;
    *) echo "✗ 모르는 인자 '$1'" >&2; usage >&2; exit 64 ;;
  esac
done

rc=0
case "$cmd" in
  status) out="$(hwax_drain status)" || rc=$? ;;
  on)
    if [ "$hold" = 1 ]; then
      out="$(hwax_drain hold "$by" "review-drain.sh on --hold")" || rc=$?
    else
      t="$(_hwax_drain_secs "$ttl" 0)"
      [ "$t" -gt 0 ] || { echo "✗ --ttl 은 0 보다 큰 초다('$ttl')" >&2; exit 64; }
      [ "$t" -le "$HWAX_DRAIN_TTL_CAP" ] \
        || echo "  · --ttl $ttl 은 엔진이 받는 상한보다 길다 — ${HWAX_DRAIN_TTL_CAP}초로 자른다(더 길게는 --hold)"
      out="$(hwax_drain on all "$ttl" "$by" "review-drain.sh on --ttl $ttl")" || rc=$?
    fi ;;
  off)
    if [ "$force" = 1 ]; then out="$(hwax_drain off "$by" force)" || rc=$?; else out="$(hwax_drain off "$by")" || rc=$?; fi ;;
  -h|--help|help) usage; exit 0 ;;
  *) echo "✗ 모르는 명령 '$cmd'" >&2; usage >&2; exit 64 ;;
esac

case "$rc" in
  0) echo "✓ $out" ;;
  2) echo "✗ $out — ${HWAX_AGENT_URL:-http://127.0.0.1:9009} 에서 에이전트 서버가 떠 있는지 본다" >&2 ;;
  3) echo "✗ 에이전트 서버가 /drain 을 모른다(옛 판) — 새 판으로 올린 뒤에 쓴다(update-all)" >&2 ;;
  4) echo "✗ $out" >&2 ;;
  5) echo "✗ $out — 건드리지 않았다. 내리려면 off --force" >&2 ;;
  *) echo "✗ 거절 — $out" >&2 ;;
esac
exit "$rc"
