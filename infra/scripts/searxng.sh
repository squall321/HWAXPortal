#!/usr/bin/env bash
# SearxNG 기동 — 일반 웹 검색 공급자(WEB_PROVIDER=searxng). 루프백 전용.
#
# 왜 이런 모양인가.
#   · 이미지 기본 서버(granian)는 mp 워커에서 'No module named searx' 로 죽는다. searx 는
#     venv 에 설치돼 있지 않고 /usr/local/searxng 에 놓여 있을 뿐이라, cwd 에 기대는 도커와
#     달리 콘솔 스크립트로 뜨는 granian 은 못 찾는다. venv 에 .pth 를 넣어도 워커까지는
#     전달되지 않았다(실측). 그래서 Flask 내장 서버(threaded)로 띄운다 — 루프백 전용이고
#     앞단에서 인증이 끝난 저동시성 내부 브로커라 이것으로 충분하다.
#   · JSON 출력은 SearxNG 기본이 꺼짐이다. settings.yml 의 search.formats 에 json 이
#     없으면 format=json 이 403 이고, 부르는 쪽에는 '결과 없음'처럼 보인다.
set -euo pipefail

SIF="${SEARXNG_SIF:-$HOME/serviceApptainers/searxng-fixed.sif}"
CONF_DIR="${SEARXNG_CONF_DIR:-/data/hwax/secrets/searxng}"
PORT="${SEARXNG_PORT:-8888}"
APPT="$(command -v apptainer || echo "$HOME/claude/HWAXPortal/infra/apptainer/bin-1.3.6/usr/bin/apptainer")"

[ -f "$SIF" ] || { echo "✗ SIF 없음: $SIF — infra/scripts/build-searxng.sh 로 굽는다"; exit 1; }
[ -f "$CONF_DIR/settings.yml" ] || { echo "✗ 설정 없음: $CONF_DIR/settings.yml"; exit 1; }
grep -q '^\s*- json' "$CONF_DIR/settings.yml" || echo "⚠ settings.yml 에 json 형식이 없다 — format=json 이 403 이 된다"

pkill -f "$SIF" 2>/dev/null || true
sleep 1
exec env APPTAINERENV_SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml \
  "$APPT" exec \
    --bind "$CONF_DIR/settings.yml:/etc/searxng/settings.yml:ro" \
    --bind "$CONF_DIR/serve.py:/opt/serve.py:ro" \
    "$SIF" /usr/local/searxng/.venv/bin/python /opt/serve.py
