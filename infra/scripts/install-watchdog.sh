#!/usr/bin/env bash
# 서비스 감시 크론 설치(멱등, 비-root) — 매분 services.sh heal 이 `watch: true` 서비스가 죽었으면(포트 연결 거부 세 번) down · up 한다.
#
#   ./infra/scripts/install-watchdog.sh            # 설치/갱신
#   ./infra/scripts/install-watchdog.sh --remove   # 크론 줄 제거(상태 · 로그는 남김)
#
# 왜: 10-18 07:11 UTC dev 의 earlyoom 이 포털 · 게이트웨이 · mxwp-mcp · searxng 를 내렸고 14시간 아무도 다시 띄우지 않았다
# (docs/followups-1017 FU-D22 · 사용자 결정 10-19 '감시 보강만'). 판정 · 백오프 · update-all 동안 건너뛰기는 services.py cmd_heal 주석.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_DIR="$HOME/.local/state/hwax"; LOG="$STATE_DIR/watchdog.log"
MARK="# hwax-watchdog"
# 'no crontab' 만 빈 목록이다 — 못 읽었는데 다시 쓰면 백업 · 터널 줄이 함께 지워진다(docs/request-1027 HP-18)
. "$ROOT/infra/scripts/lib/crontab-safe.sh"
if [ "${1:-}" = "--remove" ]; then
  hwax_crontab_replace "$MARK" || { echo "✗ crontab 을 읽지 못해 감시 크론을 지우지 않았다(지금 줄은 그대로) — 위 까닭을 보고 다시 실행"; exit 1; }
  echo "✓ hwax-watchdog 크론 제거 (상태 $STATE_DIR/watchdog · 로그 $LOG 는 남김)"; exit 0
fi
mkdir -p -m 755 "$STATE_DIR"
LINE="* * * * * $ROOT/infra/scripts/services.sh heal >> $LOG 2>&1  $MARK"
_cur="$(hwax_crontab_get)" || { echo "✗ crontab 을 읽지 못해 감시 크론을 고치지 않았다(지금 줄은 그대로) — 위 까닭을 보고 다시 실행"; exit 1; }
if grep -qxF -- "$LINE" <<<"$_cur"; then
  echo "· 서비스 감시 크론 이미 최신"
elif hwax_crontab_replace "$MARK" "$LINE"; then
  echo "✓ 서비스 감시 크론 등록/갱신: 매분 services.sh heal (로그 $LOG — 일이 있을 때만 쓴다)"
else
  echo "✗ 감시 크론을 쓰지 못했다 — crontab -l 로 지금 줄을 확인"; exit 1
fi
