#!/usr/bin/env bash
# 임시 포털(mock 로그인·임시 저장소)을 띄워 화면 점검(e2e/ui.spec.ts)을 권한 층마다 돌리고 캡처를 e2e/.shots 에 남긴다
#
#   ./frontend/scripts/ui-check.sh              # 빌드 → 관리자·기본 권한 두 층 점검
#   UI_TIERS=admin UI_SKIP_BUILD=1 ./frontend/scripts/ui-check.sh
#
# 실 저장소는 하나도 안 건드린다 — 포털이 쓰는 경로를 전부 임시 디렉토리로 돌린다(docs/ui-refresh D-1).
# 포털 프로세스는 이 스크립트가 띄운 PID 로만 내린다(pkill -f 금지 — 자기 명령줄을 맞힌다).
set -euo pipefail
FE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$FE/.." && pwd)"
PORT="${UI_PORT:-8794}"
TIERS="${UI_TIERS:-admin basic}"

_listening="$(ss -ltnH "sport = :$PORT" 2>/dev/null || true)"
[ -z "$_listening" ] || { echo "✗ 포트 $PORT 가 이미 쓰이고 있다 — UI_PORT 로 다른 포트를 준다" >&2; exit 2; }
[ "${UI_SKIP_BUILD:-0}" = 1 ] || (cd "$FE" && pnpm build >/dev/null)

TMP="$(mktemp -d)"
PID=""
cleanup() { if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi; rm -rf "$TMP"; }
trap cleanup EXIT

rc=0
for tier in $TIERS; do
  groups=""
  [ "$tier" = admin ] && groups="portal-admin"
  D="$TMP/$tier"
  mkdir -p "$D/stage"
  (cd "$ROOT/backend" && exec env AUTH_PROVIDER=mock APP_ENV=dev SERVE_FRONTEND=1 \
      PUBLIC_BASE_URL="http://127.0.0.1:$PORT" FRONTEND_URL="http://127.0.0.1:$PORT" \
      SESSION_SECRET="ui-check-session-secret-not-a-real-one-000000" COOKIE_SECURE=false \
      MOCK_USER_EMAIL=hong.gildong@corp.com MOCK_USER_NAME=홍길동 MOCK_USER_GROUPS="$groups" \
      USER_STORE_PATH="$D/users.sqlite" TOKEN_STORE_PATH="$D/tok.sqlite" CONV_STORE_PATH="$D/conv.sqlite" \
      PROCEDURES_STORE_PATH="$D/proc.sqlite" AGENT_AUDIT_LOG_PATH="$D/audit.sqlite" JWT_KEYS_DIR="$D/jwt" \
      JWT_AUTOGEN_KEYS=true PROCEDURES_ARTIFACT_ROOT="$D/art" DELIB_ARCHIVE_ROOT="$D/delib" UPLOAD_STAGING_DIR="$D/stage" \
      .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT") >"$D/portal.log" 2>&1 &
  PID=$!
  _up=""
  for _ in $(seq 1 40); do
    _code="$(curl -s -o /dev/null -w '%{http_code}' -m 2 --noproxy '*' "http://127.0.0.1:$PORT/health" || true)"
    [ "$_code" = 200 ] && { _up=1; break; }
    sleep 0.5
  done
  [ -n "$_up" ] || { echo "✗ 임시 포털이 안 떴다($tier) — 로그 끝:" >&2; tail -20 "$D/portal.log" >&2; exit 2; }
  echo "── 권한 층: $tier ──────────────────────────────"
  (cd "$FE" && UI_BASE="http://127.0.0.1:$PORT" UI_TIER="$tier" pnpm exec playwright test) || rc=1
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  PID=""
done
echo "캡처: $FE/e2e/.shots/<층>/<폭>_<경로>.png"
exit $rc
