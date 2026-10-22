#!/usr/bin/env bash
# 에이전트 서버에 도는·줄 선 심의가 있는지 묻는다 — update-all 이 그 서버를 재기동하기 전에 본다(§4 update-sites · §5 재프로비저닝).
#
# 왜 — 좌석 20석 넘는 심의는 몇 시간 돈다. 에이전트 서버의 재기동은 2초 유예 뒤 강제 종료라, 코드나 설정이 바뀐 update-all 한 번이
# 도는 심의와 줄 선 심의를 말없이 지운다(재개가 없다 — 줄은 메모리에만 있다). 유예를 늘려서는 몇 시간짜리를 살리지 못한다.
# 그래서 무인 경로는 끊지 않고, 건너뛴 사실을 ○ 로 남긴다. 한도를 아무리 넉넉히 잡아도 배포 한 번이 가장 흔한 절단이 된다.
#
#   . "$ROOT/infra/scripts/lib/delib-busy.sh"
#   hwax_delib_busy [health url]   도는·줄 선 심의가 있으면 "<진행> <대기>" 를 찍고 0 · 없으면 1 · **알 수 없으면 2 또는 4**.
#       줄이 재기동을 넘기는 엔진(/health 의 delib_queue_durable 이 참 — HWAXPortal docs/delib-ops R2)이면 줄 선 수는 막는 수로 세지 않는다
#       (재기동 뒤 같은 차례로 다시 선다) — 도는 것이 있을 때만 0 이다(찍는 수는 그대로 둘 다).
#       2 = 서버가 받지 않는다(내려가 있다 — 끊을 심의가 없다) 또는 /health 에 delib_active·delib_queued 가 없다(옛 판·깨진 응답).
#       4 = 듣고는 있는데 **연속으로** 탐침 한도(4초)를 넘겼다 — 매달린 것으로 본다.
#       부르는 쪽은 **0 일 때만** 건너뛴다 — 모르는데 건너뛰면 죽은·매달린 서버를 영영 못 띄우고, 옛 판은 영영 못 올린다.
#   AGENT_RESTART_FORCE=1 이면 묻지 않고 1 을 낸다(재기동한다) — 사람이 끊기로 한 것이다.
#   HWAX_DELIB_PROBE_STRIKES(기본 3) 시간 초과를 몇 번 내리 봐야 매달렸다고 읽는가 · HWAX_DELIB_PROBE_GAP_S(기본 3) 그 사이 쉬는 초.
#       매달린 서버의 최악은 3×4 + 2×3 = 18초다. 내려간 서버(거절)는 종전대로 곧바로 2 다 — 다시 묻지 않는다.
#
# ⚠ `set -e` 스크립트에서는 `_b="$(hwax_delib_busy …)" || _rc=$?` 로 받는다 — 맨 문장이면 1·2·4 에서 스크립트가 조용히 끝난다.
hwax_delib_busy() {
  local url="${1:-http://127.0.0.1:9009/health}" body rc=28 i n="${HWAX_DELIB_PROBE_STRIKES:-3}"
  [ "${AGENT_RESTART_FORCE:-0}" = 1 ] && return 1
  # 횟수는 1 이상의 수여야 한다 — 0 은 '묻지 않는다' 가 아니다(한 번도 안 묻고 '매달렸다' 가 되면 도는 심의가 있어도 재기동한다).
  case "$n" in ''|*[!0-9]*|0) n=3 ;; esac
  # 거절과 시간 초과를 가른다. 에이전트 서버의 이벤트 루프는 동기 조회로 몇 초씩 막힌다(게이트웨이가 매달린 순간의 /tools-map
  # 5초 · LLM 서버가 매달린 순간의 /models 5초) — 그 순간에 **한 번** 물어 '모름 = 재기동' 이 되면 살아서 몇 시간짜리 패널을
  # 돌리는 서버가 죽은 서버 취급을 받는다(사본 재현: 막힌 지 0.2초에 물으면 4.1초 뒤 2, 그 직후에는 0). 탐침 4초는 늘리지
  # 않는다 — 죽은 상대를 재는 값이다. 시간 초과(curl 28)만 다시 묻고, 그 밖의 실패(거절 7 등)는 곧바로 2 다.
  # 로컬 health 다 — 운영자 셸의 http_proxy 를 타면 프록시가 이 박스의 루프백에 못 닿아 '모름' 이 되고, 모름은 재기동이다.
  for i in $(seq 1 "$n"); do
    rc=0; body="$(curl -s --noproxy '*' -m 4 "$url" 2>/dev/null)" || rc=$?
    [ "$rc" = 0 ] && break
    [ "$rc" = 28 ] || return 2
    if [ "$i" -lt "$n" ]; then sleep "${HWAX_DELIB_PROBE_GAP_S:-3}"; fi
  done
  [ "$rc" = 0 ] || return 4
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
durable = h.get("delib_queue_durable") is True        # 참일 때만 — 모르면(옛 판 · 거짓 · 다른 모양) 줄 선 것도 재기동에 사라진다
if a + (0 if durable else q) <= 0:
    sys.exit(1)
print(a, q)
PY
}

# ── 새 심의 멈춤(엔진 R1 — POST /drain {scope: "delib"}) · 도는 심의 기다리기(update-sites 의 에이전트 서버 재기동 앞 — O1) ──────────
#   hwax_delib_pause <on|off> <health url> <by> [ttl_s] [reason]   한 줄 설명을 찍는다.
#       0 = 됐다(세웠다 · 늘렸다 · 내렸다 — 없던 것을 내린 것도 0) · 2 = 받지 않는다(내려가 있다) · 3 = 멈춤을 모르는 엔진(/health 에
#       delib_paused 가 없다 — **보내지 않는다**: 옛 엔진은 /drain 의 scope 를 보지 않아 {on:false, scope:"delib"} 을 카드 대조 깃발 끄기로
#       읽는다) · 4 = 매달렸다 · 5 = 사람이 고정한 멈춤(409, hold) · 7 = 다른 주체의 멈춤(409) · 6 = 거절(422 · 503 · 그 밖).
#   hwax_delib_pause_state <health url>   "<켜짐 0|1> <by>" 를 찍는다. 0 = 읽었다 · 2 · 3 · 4 는 위와 같다.
#   hwax_delib_durable <health url>       줄이 재기동을 넘기는 엔진이면(delib_queue_durable 이 참) 0, 아니면(모름 · 옛 판 포함) 1.
#   hwax_delib_requeued [health url]      "<다시 선 줄 수> <멈춤 0|1>" 를 찍는다(엔진 R2 — /health.delib_requeued). 0 = 읽었다 · 2 · 4 는 위와 같다 ·
#       3 = 그 칸이 없다(옛 판).
#   hwax_agent_ident [health url]         그 주소의 포트를 듣는 프로세스 "<pid>:<시작 시각>"(가장 작은 pid) — 듣는 것이 없으면(또는 ss 가 없으면) "?".
#       재기동 판정은 rc 가 아니라 리스너로 한다(update-all §4 의 O2 — 이번에 다시 떴나). change-detect.sh 의 hwax_listener_ids 와 같은 식이다 —
#       이 lib 만 읽는 쪽(update-all 머리 · 시험 사본)에서도 돌게 따로 둔다.
#   hwax_delib_wait <health url> <max_s>  hwax_delib_busy 가 '없다'(1) · '내려갔다'(2)가 될 때까지 HWAX_DELIB_WAIT_POLL_S(기본 10)초마다 본다.
#       마지막에 본 "<진행> <대기>" 를 찍는다. 0 = 비었다 · 1 = 시간이 다 됐다(또는 매달렸다 — 4 — 기다릴 수 없다).
#   주소는 health url 에서 /health 를 뗀 것이다. health url 을 비우면 ${HWAX_AGENT_URL:-http://127.0.0.1:9009}/health 다(update-all 이 이 꼴로
#   부른다 — 시험이 HWAX_AGENT_URL 로 바꿔 끼운다). 호출은 전부 --noproxy '*' · -m 4 다(위 hwax_delib_busy 와 같은 까닭).
# ⚠ 0 아닌 값을 정상으로 돌려준다 — `set -e` 스크립트에서는 `_out="$(hwax_delib_pause …)" || _rc=$?` 로 받는다.
_hwax_delib_health() {   # <health url> — 본문을 찍는다. 0 · 2(거절 · 200 아님) · 4(시간 초과)
  local rc=0 resp
  resp="$(curl -s --noproxy '*' -m 4 -w '\n%{http_code}' "$1" 2>/dev/null)" || rc=$?
  [ "$rc" = 28 ] && return 4
  [ "$rc" = 0 ] || return 2
  [ "${resp##*$'\n'}" = 200 ] || return 2
  printf '%s' "${resp%$'\n'*}"
}

hwax_delib_durable() {
  local body
  body="$(_hwax_delib_health "${1:-http://127.0.0.1:9009/health}")" || return 1
  B="$body" python3 -c 'import json, os, sys
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(1)
sys.exit(0 if isinstance(h, dict) and h.get("delib_queue_durable") is True else 1)'
}

hwax_delib_requeued() {
  local body rc=0
  body="$(_hwax_delib_health "${1:-${HWAX_AGENT_URL:-http://127.0.0.1:9009}/health}")" || rc=$?
  [ "$rc" = 0 ] || return "$rc"
  B="$body" python3 - <<'PY'
import json, os, sys
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(2)
v = h.get("delib_requeued") if isinstance(h, dict) else None
if not isinstance(v, int) or isinstance(v, bool) or v < 0:
    sys.exit(3)                       # 줄을 넘기지 않는 엔진(옛 판)
print(v, 1 if h.get("delib_paused") is True else 0)
PY
}

hwax_agent_ident() {
  local url="${1:-${HWAX_AGENT_URL:-http://127.0.0.1:9009}/health}" hp p pid st
  hp="${url#*://}"; hp="${hp%%/*}"; p="${hp##*:}"
  case "$p" in ''|*[!0-9]*) echo "?"; return 0 ;; esac
  # 듣는 것이 없으면 grep 이 1 로 끝난다 — pipefail · set -e 로 부르는 쪽이 여기서 끝나지 않게 받는다(이 함수는 늘 0 이다)
  pid="$(ss -ltnpH "sport = :$p" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -n | head -1)" || pid=""
  if [ -n "$pid" ]; then st="$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)" || st=""; echo "$pid:${st:-?}"; else echo "?"; fi
}

hwax_delib_pause_state() {
  local body rc=0
  body="$(_hwax_delib_health "${1:-${HWAX_AGENT_URL:-http://127.0.0.1:9009}/health}")" || rc=$?
  [ "$rc" = 0 ] || return "$rc"
  B="$body" python3 - <<'PY'
import json, os, sys
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(2)
if not isinstance(h, dict) or "delib_paused" not in h:
    sys.exit(3)                       # 멈춤을 모르는 엔진
p = h.get("delib_pause") if isinstance(h.get("delib_pause"), dict) else {}
print(1 if h.get("delib_paused") is True else 0, str(p.get("by") or ""))
PY
}

hwax_delib_pause() {
  local op="${1:-}" url="${2:-${HWAX_AGENT_URL:-http://127.0.0.1:9009}/health}" by="${3:-}" ttl="${4:-1800}" reason="${5:-}" req resp code body rc=0
  case "$op" in on|off) ;; *) echo "hwax_delib_pause: on · off 다 — '$op'" >&2; return 6 ;; esac
  hwax_delib_pause_state "$url" >/dev/null || rc=$?
  case "$rc" in
    0) ;;
    3) echo "엔진이 새 심의 멈춤을 모른다(옛 판 — /health 에 delib_paused 가 없다)"; return 3 ;;
    4) echo "에이전트 서버가 4초 안에 답하지 않았다(매달림)"; return 4 ;;
    *) echo "에이전트 서버가 받지 않는다(내려가 있다)"; return 2 ;;
  esac
  case "$ttl" in ''|*[!0-9]*) ttl=1800 ;; esac
  [ "$ttl" -gt 0 ] || ttl=1800
  [ "$ttl" -le 21600 ] || ttl=21600                  # 엔진은 요청 하나의 ttl_s 를 6시간까지 받는다
  req="$(D_OP="$op" D_BY="$by" D_TTL="$ttl" D_REASON="$reason" python3 -c '
import json, os
e = os.environ.get
b = {"on": e("D_OP") == "on", "scope": "delib", "by": e("D_BY", "")}
if b["on"]:
    b.update(ttl_s=int(e("D_TTL")), reason=e("D_REASON", ""))
print(json.dumps(b, ensure_ascii=False))')"
  rc=0; resp="$(curl -s --noproxy '*' -m 4 -X POST -H 'content-type: application/json' --data-binary "$req" \
                   -w '\n%{http_code}' "${url%/health}/drain" 2>/dev/null)" || rc=$?
  [ "$rc" = 28 ] && { echo "에이전트 서버가 4초 안에 답하지 않았다(매달림)"; return 4; }
  [ "$rc" = 0 ] || { echo "에이전트 서버가 받지 않는다(내려가 있다)"; return 2; }
  code="${resp##*$'\n'}"; body="${resp%$'\n'*}"
  C="$code" B="$body" python3 - <<'PY'
import json, os, sys, time
code, raw = os.environ["C"], os.environ["B"]
try:
    b = json.loads(raw)
except ValueError:
    b = None
if code == "200" and isinstance(b, dict):
    if b.get("on") is True:
        left = f" · 남은 {max(0, int(b['until'] - time.time()))}초" if isinstance(b.get("until"), (int, float)) else ""
        print(f"새 심의 멈춤 on(by {str(b.get('by'))[:60]}{left}{' · 고정' if b.get('hold') is True else ''})")
    else:
        print("새 심의 멈춤 꺼짐")
    sys.exit(0)
if code == "409" and isinstance(b, dict):
    d = b.get("drain") if isinstance(b.get("drain"), dict) else b
    held = d.get("hold") is True
    print(f"{'사람이 고정한' if held else '다른 주체가 세운'} 새 심의 멈춤(by {str(d.get('by') or '?')[:60]} · {b.get('code', '409')})")
    sys.exit(5 if held else 7)
why = f"{b.get('code')} — {str(b.get('message', ''))[:160]}" if isinstance(b, dict) else raw[:160].replace("\n", " ")
print(f"HTTP {code} {why}")
sys.exit(6)
PY
}

hwax_delib_wait() {
  local url="${1:-http://127.0.0.1:9009/health}" max="${2:-600}" gap="${HWAX_DELIB_WAIT_POLL_S:-10}" t0=$SECONDS last="" b rc
  case "$max" in ''|*[!0-9]*) max=600 ;; esac
  case "$gap" in ''|*[!0-9]*|0) gap=10 ;; esac
  while :; do
    rc=0; b="$(hwax_delib_busy "$url")" || rc=$?
    case "$rc" in
      0) last="$b" ;;
      1|2) echo "${last:-0 0}"; return 0 ;;          # 비었다 · 내려갔다(끊을 심의가 없다)
      *) echo "${last:-? ?}"; return 1 ;;             # 매달렸다 — 기다려도 모른다
    esac
    [ $((SECONDS - t0)) -ge "$max" ] && { echo "$last"; return 1; }
    sleep "$gap"
  done
}
