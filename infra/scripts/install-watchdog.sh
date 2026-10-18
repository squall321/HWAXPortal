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
if [ "${1:-}" = "--remove" ]; then
  crontab -l 2>/dev/null | grep -vF "$MARK" | crontab -
  echo "✓ hwax-watchdog 크론 제거 (상태 $STATE_DIR/watchdog · 로그 $LOG 는 남김)"; exit 0
fi
mkdir -p -m 755 "$STATE_DIR"
LINE="* * * * * $ROOT/infra/scripts/services.sh heal >> $LOG 2>&1  $MARK"
if crontab -l 2>/dev/null | grep -qxF "$LINE"; then
  echo "· 서비스 감시 크론 이미 최신"
else
  ( crontab -l 2>/dev/null | grep -vF "$MARK"; echo "$LINE" ) | crontab -
  echo "✓ 서비스 감시 크론 등록/갱신: 매분 services.sh heal (로그 $LOG — 일이 있을 때만 쓴다)"
fi
