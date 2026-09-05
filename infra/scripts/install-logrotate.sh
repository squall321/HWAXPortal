#!/usr/bin/env bash
# HWAX 로그 회전 설치(멱등, 비-root) — 템플릿을 박스 경로로 렌더하고 매시 크론 + 사용자 상태파일을 건다.
#
#   ./infra/scripts/install-logrotate.sh            # 설치/갱신 (logrotate 없으면 skip, rc 0)
#   ./infra/scripts/install-logrotate.sh --remove   # 크론 줄 제거(렌더 파일·상태는 남김)
#   ./infra/scripts/install-logrotate.sh --dry      # 렌더 + `logrotate -d` 만(회전 안 함)
#
# 비-root 함정(사전점검): /var/lib/logrotate/status 를 못 써 -s 로 사용자 상태파일이 필수, 설정 파일이
# group/other 쓰기 가능이면 'bad file mode' 로 거부 — 0644 로 install. 대상은 템플릿 주석대로 O_APPEND 쓰기자만.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
TMPL="$ROOT/infra/logrotate/hwax.conf.tmpl"
CONF_DIR="$HOME/.config/hwax"; CONF="$CONF_DIR/logrotate.conf"
STATE_DIR="$HOME/.local/state/hwax"; STATE="$STATE_DIR/logrotate.status"; LOG="$STATE_DIR/logrotate.log"
MARK="# hwax-logrotate"

if [ "${1:-}" = "--remove" ]; then
  ( crontab -l 2>/dev/null | grep -vF "$MARK" ) | crontab - 2>/dev/null || true
  echo "✓ hwax-logrotate 크론 제거 (렌더 파일 $CONF 와 상태 $STATE 는 남김)"; exit 0
fi
LR="$(command -v logrotate || true)"
[ -n "$LR" ] || { echo "· logrotate 없음 — skip(이 박스는 회전 없이 간다)"; exit 0; }

mkdir -p -m 755 "$CONF_DIR" "$STATE_DIR"
TMP="$(mktemp)"
sed -e "s#__ROOT__#$PARENT#g" -e "s#__HOME__#$HOME#g" -e "s#__USER__#$USER#g" "$TMPL" > "$TMP"
install -m 0644 "$TMP" "$CONF"; rm -f "$TMP"

# 문법·모드·대상 검증 — 회전 없이(-d). 'error' 한 줄이라도 있으면 설치하지 않는다.
if ! OUT="$("$LR" -d -s "$STATE" "$CONF" 2>&1)"; then
  echo "✗ logrotate -d 실패:"; printf '%s\n' "$OUT" | grep -iE 'error|bad' | head -5 | sed 's/^/    /'; exit 1
fi
if printf '%s\n' "$OUT" | grep -qiE '^error|bad file mode'; then
  echo "✗ 설정 오류:"; printf '%s\n' "$OUT" | grep -iE 'error|bad' | head -5 | sed 's/^/    /'; exit 1
fi
N="$(printf '%s\n' "$OUT" | grep -c '^considering log' || true)"
echo "✓ 렌더 $CONF · 대상 로그 ${N}개(-d 검증 통과)"
[ "${1:-}" = "--dry" ] && exit 0

# 매시 17분 — maxsize 는 실행 시점에만 평가된다. 치환형 멱등(마커).
LINE="17 * * * * $LR -s $STATE $CONF >> $LOG 2>&1  $MARK"
if crontab -l 2>/dev/null | grep -qxF "$LINE"; then
  echo "· 크론 이미 최신"
else
  ( crontab -l 2>/dev/null | grep -vF "$MARK"; echo "$LINE" ) | crontab -
  echo "✓ 크론 등록/갱신: 매시 17분 → $CONF (상태 $STATE, 로그 $LOG)"
fi
