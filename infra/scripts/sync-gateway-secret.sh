#!/usr/bin/env bash
# HEAXHub 와 KooRemapper 가 공유해야 하는 게이트웨이 시크릿을 한 값으로 맞춘다(불일치=SSO 조용히 막힘)
#
# HEAXHub Caddy 는 portal_auth 라우트에 X-Heax-Gateway-Secret 을 주입하고
# (backend/app/services/proxy_manager.py — 값은 backend/.env 의 GATEWAY_SHARED_SECRET),
# KooRemapper 는 그 헤더로 SSO PAT 자동발급을 연다
# (platform/backend/app/config.py:heax_gateway_secret — 값은 platform/.env 의 KOORM_HEAX_GATEWAY_SECRET).
# 두 값이 다르면 아무 로그 없이 403 이고, 포탈에서 DynaForge 자동 로그인이 막히며
# 게이트웨이용 kr_ PAT 도 발급되지 않는다(도구 22개가 목록에만 뜨는 상태 — cae00 2026-08-12).
#
# 이 헤더를 검증하는 앱은 KooRemapper 하나뿐이라(전 레포 확인) 값을 맞춰도 다른 앱에 영향이 없다.
#
#   sync-gateway-secret.sh          # 지문만 비교(파일 안 건드림)
#   sync-gateway-secret.sh --write  # 한 값으로 맞추고, 바뀐 쪽 서비스를 재기동
#
# 규칙 — 값이 있는 쪽이 이긴다. 둘 다 있고 다르면 HEAXHub(주입하는 쪽)가 이긴다.
# 둘 다 비었으면 새로 만든다(그 상태에선 헤더가 아예 안 나가므로 아무도 쓰고 있지 않다).
set -uo pipefail

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do
                [ -d "$c" ] && { printf '%s' "$c"; return 0; }; done; return 0; }
HEAX_DIR="${HEAX_DIR:-$(find_repo HEAXHub)}"
KOORM_DIR="${KOORM_DIR:-$(find_repo KooRemapper)}"
HEAX_ENV="$HEAX_DIR/backend/.env"
KOORM_ENV="$KOORM_DIR/platform/.env"
WRITE=0; [ "${1:-}" = "--write" ] && WRITE=1

for f in "$HEAX_ENV" "$KOORM_ENV"; do
  [ -f "$f" ] || { echo "  · 시크릿 정합 생략 — $f 없음"; exit 0; }
done

_get() { awk -F= -v k="$2" '$1==k{sub(/^[^=]*=/,"");gsub(/^["'\'']|["'\'']$/,"");print;exit}' "$1"; }
_fp()  { [ -n "$1" ] && printf '%s' "$1" | sha256sum | cut -c1-12 || printf '(없음)'; }
# 키가 있으면 치환, 없으면 추가 — sed 만 쓰면 키가 없는 파일에 조용히 아무 일도 안 한다.
_put() {
  local f="$1" k="$2" v="$3"
  if grep -q "^${k}=" "$f"; then
    python3 - "$f" "$k" "$v" <<'PY'
import sys
f, k, v = sys.argv[1], sys.argv[2], sys.argv[3]
out = [f"{k}={v}\n" if l.split("=", 1)[0].strip() == k else l for l in open(f)]
open(f, "w").writelines(out)
PY
  else
    printf '%s=%s\n' "$k" "$v" >> "$f"
  fi
}

H="$(_get "$HEAX_ENV" GATEWAY_SHARED_SECRET)"
K="$(_get "$KOORM_ENV" KOORM_HEAX_GATEWAY_SECRET)"

if [ -n "$H" ] && [ "$H" = "$K" ]; then
  echo "  ✓ 게이트웨이 공유 시크릿 일치 ($(_fp "$H"))"
  exit 0
fi

echo "  ⚠ 게이트웨이 공유 시크릿 불일치 — HEAXHub=$(_fp "$H") KooRemapper=$(_fp "$K")"
if [ -n "$H" ]; then WANT="$H"; SRC="HEAXHub"
elif [ -n "$K" ]; then WANT="$K"; SRC="KooRemapper"
else WANT="$(openssl rand -hex 24)"; SRC="신규생성"; fi

if [ "$WRITE" != 1 ]; then
  echo "    → $SRC 값으로 맞춘다(실제 반영은 --write). 맞추기 전엔 DynaForge SSO·kr_ PAT 가 막힌다."
  exit 1
fi

CHANGED=""
[ "$H" != "$WANT" ] && { _put "$HEAX_ENV"  GATEWAY_SHARED_SECRET     "$WANT"; CHANGED="$CHANGED heax-hub"; }
[ "$K" != "$WANT" ] && { _put "$KOORM_ENV" KOORM_HEAX_GATEWAY_SECRET "$WANT"; CHANGED="$CHANGED kooremapper"; }

# 되짚어 읽어 확인한다 — _put 이 실패해도 조용하면 "맞췄다"는 거짓말이 된다.
H2="$(_get "$HEAX_ENV" GATEWAY_SHARED_SECRET)"; K2="$(_get "$KOORM_ENV" KOORM_HEAX_GATEWAY_SECRET)"
if [ "$H2" != "$WANT" ] || [ "$K2" != "$WANT" ]; then
  echo "  ✗ 시크릿 기록 실패 — HEAXHub=$(_fp "$H2") KooRemapper=$(_fp "$K2") (기대 $(_fp "$WANT"))"
  exit 2
fi
echo "  ✓ $SRC 값으로 맞춤 ($(_fp "$WANT")) — 반영 대상:$CHANGED"

# 프로세스는 기동 시점 값을 들고 있으므로 재기동해야 실제로 바뀐다.
SVC="$SELF_REPO/infra/scripts/services.sh"
if [ -x "$SVC" ] || [ -f "$SVC" ]; then
  for s in $CHANGED; do
    echo "    · $s 재기동(새 시크릿 적용)"
    bash "$SVC" down "$s" >/dev/null 2>&1
    bash "$SVC" up   "$s" >/dev/null 2>&1 || echo "    ⚠ $s 재기동 실패 — 수동 확인 필요"
  done
else
  echo "    ⚠ services.sh 없음 — 다음 서비스를 직접 재기동하라:$CHANGED"
fi
