#!/usr/bin/env bash
# 임시 포털(mock 로그인·임시 저장소)을 띄워 화면 점검(e2e/ui.spec.ts)을 권한 층마다 돌리고 캡처를 e2e/.shots 에 남긴다
#
#   ./frontend/scripts/ui-check.sh              # 빌드 → 관리자·기본 권한 두 층 점검
#   UI_TIERS='admin basic caeg' ./frontend/scripts/ui-check.sh   # CAEG 소속 층까지(관리자 아님 · 소속 grants '*')
#   UI_TIERS=admin UI_SKIP_BUILD=1 ./frontend/scripts/ui-check.sh
#   ./frontend/scripts/ui-check.sh -g '/tokens'   # 나머지 인자는 playwright test 로 넘긴다(한 화면만 다시 보기)
#
# 실 저장소는 하나도 안 건드린다 — 포털이 쓰는 경로를 전부 임시 디렉토리로 돌린다(docs/ui-refresh D-1).
# 라우트도 임시 사본이다 — 리포의 backend/config/routes.env 만 옮기고 박스 오버레이(routes.local.env)는 읽지 않는다. 목적지가 있어야
# 열리는 타일(사내 연계 knox-bridge 등)이 이 박스 설정에 따라 열리고 닫히면 같은 점검이 박스마다 다른 화면을 본다.
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
STATE="$TMP/state"   # 층 사이에 견줄 값(층마다 /apps 타일 수) — 시험이 UI_STATE 에 적고 끝에서 견준다
mkdir -p "$STATE"
PID=""
cleanup() { if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi; rm -rf "$TMP"; }
trap cleanup EXIT

rc=0
for tier in $TIERS; do
  # 관리자 층은 고정 목록(PORTAL_ADMIN_EMAILS)으로 만든다. 포털은 IdP 가 준 그룹으로는 관리자를 인정하지 않는다(원장과 이 목록만
  # 본다) — 종전처럼 MOCK_USER_GROUPS=portal-admin 만 주면 관리자 층이 조용히 기본 권한으로 돌아 관리 화면을 한 번도 안 본다.
  admins=""
  [ "$tier" = admin ] && admins="hong.gildong@corp.com"
  # CAEG 층은 소속으로 만든다 — 빈 임시 원장에 기본 소속을 주면 mock 사용자가 처음 로그인할 때 그 소속으로 생긴다(auth/routes/session.py
  # complete_login). 다른 층은 빈 값을 명시한다 — 부른 셸이나 backend/.env 의 값이 새면 기본 층이 조용히 CAEG 로 돈다.
  aff=""
  [ "$tier" = caeg ] && aff="CAEG"
  D="$TMP/$tier"
  mkdir -p "$D/stage"
  cp "$ROOT/backend/config/routes.env" "$D/routes.env"
  (cd "$ROOT/backend" && exec env AUTH_PROVIDER=mock APP_ENV=dev SERVE_FRONTEND=1 \
      PUBLIC_BASE_URL="http://127.0.0.1:$PORT" FRONTEND_URL="http://127.0.0.1:$PORT" \
      SESSION_SECRET="ui-check-session-secret-not-a-real-one-000000" COOKIE_SECURE=false \
      MOCK_USER_EMAIL=hong.gildong@corp.com MOCK_USER_NAME=홍길동 MOCK_USER_GROUPS="" PORTAL_ADMIN_EMAILS="$admins" \
      SSO_DEFAULT_AFFILIATION="$aff" ROUTES_PATH="$D/routes.env" \
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
  (cd "$FE" && UI_BASE="http://127.0.0.1:$PORT" UI_TIER="$tier" UI_STATE="$STATE" pnpm exec playwright test "$@") || rc=1
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  PID=""
done
# 층 사이 견주기 — CAEG 층은 소속 grants '*' 라 기본 층보다 /apps 타일이 많아야 한다. 같으면 소속이 안 들어간 것이다.
if [ -s "$STATE/basic.apps" ] && [ -s "$STATE/caeg.apps" ]; then
  _b="$(cat "$STATE/basic.apps")"; _c="$(cat "$STATE/caeg.apps")"
  if [ "$_c" -gt "$_b" ]; then
    echo "✓ /apps 타일 — CAEG 층 ${_c}개 > 기본 층 ${_b}개"
  else
    echo "✗ /apps 타일 — CAEG 층 ${_c}개가 기본 층 ${_b}개보다 많지 않다(CAEG 소속이 원장에 안 들어갔다)" >&2
    rc=1
  fi
elif [[ " $TIERS " == *" basic "* && " $TIERS " == *" caeg "* ]]; then
  echo "○ /apps 타일 견주기 건너뜀 — 기본 · CAEG 두 층의 타일 수가 다 남지 않았다(-g 로 그 시험을 뺐거나 한 층이 먼저 실패했다)"
fi
echo "캡처: $FE/e2e/.shots/<층>/<폭>_<경로>.png"
exit $rc
