#!/usr/bin/env bash
# 에이전트 서버에 도는·줄 선 심의가 있는지 묻는다 — update-all 이 그 서버를 재기동하기 전에 본다(§4 update-sites · §5 재프로비저닝).
#
# 왜 — 좌석 20석 넘는 심의는 몇 시간 돈다. 에이전트 서버의 재기동은 2초 유예 뒤 강제 종료라, 코드나 설정이 바뀐 update-all 한 번이
# 도는 심의와 줄 선 심의를 말없이 지운다(재개가 없다 — 줄은 메모리에만 있다). 유예를 늘려서는 몇 시간짜리를 살리지 못한다.
# 그래서 무인 경로는 끊지 않고, 건너뛴 사실을 ○ 로 남긴다. 한도를 아무리 넉넉히 잡아도 배포 한 번이 가장 흔한 절단이 된다.
#
#   . "$ROOT/infra/scripts/lib/delib-busy.sh"
#   hwax_delib_busy [health url]   도는·줄 선 심의가 있으면 "<진행> <대기>" 를 찍고 0 · 없으면 1 · **알 수 없으면 2**.
#       2 = 서버가 답하지 않는다(내려가 있다 — 끊을 심의가 없다) 또는 /health 에 delib_active·delib_queued 가 없다(옛 판).
#       부르는 쪽은 **0 일 때만** 건너뛴다 — 모르는데 건너뛰면 죽은 서버를 영영 못 띄우고, 옛 판은 영영 못 올린다.
#   AGENT_RESTART_FORCE=1 이면 묻지 않고 1 을 낸다(재기동한다) — 사람이 끊기로 한 것이다.
#
# ⚠ `set -e` 스크립트에서는 `_b="$(hwax_delib_busy …)" || _rc=$?` 로 받는다 — 맨 문장이면 1·2 에서 스크립트가 조용히 끝난다.
hwax_delib_busy() {
  local url="${1:-http://127.0.0.1:9009/health}" body
  [ "${AGENT_RESTART_FORCE:-0}" = 1 ] && return 1
  # 로컬 health 다 — 운영자 셸의 http_proxy 를 타면 프록시가 이 박스의 루프백에 못 닿아 '모름' 이 되고, 모름은 재기동이다.
  body="$(curl -s --noproxy '*' -m 4 "$url" 2>/dev/null)" || return 2
  [ -n "$body" ] || return 2
  B="$body" python3 - <<'PY'
import json, os, sys
try:
    h = json.loads(os.environ["B"])
    a, q = h.get("delib_active"), h.get("delib_queued")
except Exception:
    sys.exit(2)
ok = lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0
if (a is None and q is None) or not all(ok(v) for v in (a, q) if v is not None):
    sys.exit(2)                       # 필드가 없거나(옛 판) 수가 아니다 — 모른다
a, q = a or 0, q or 0
if a + q <= 0:
    sys.exit(1)
print(a, q)
PY
}
