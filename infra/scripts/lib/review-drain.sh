#!/usr/bin/env bash
# 리스크 검토 비우기 깃발(에이전트 서버 /drain)을 셸에서 읽고 세우고 내리는 함수들 — update-all 1h 와 review-drain.sh 가 쓴다.
#
# 왜 — 카드 대조는 /health 의 delib_active 에 들지 않아 재기동을 막지 않고, 끊긴 호출은 리스크 앱이 차감 없이 다시 낸다. 그래도
# 끊긴 호출의 LLM 시간은 버려진다. 비우기는 그 사이를 메운다 — update-all 동안 새 카드 대조·새 패널을 멈추고, 도는 것을 잠깐
# 기다리고, 미룬 재기동이 있으면 심의가 끝난 뒤 다음 배포 창을 연다(docs/risk-review-redesign/reference/m3-engine-ops.md '비우기 의미').
# 깃발은 엔진이 파일로 쥐고 재기동을 넘긴다. 비우기는 예의지 관문이 아니다 — 실패해도 배포는 간다.
#
#   . "$ROOT/infra/scripts/lib/review-drain.sh"
#   hwax_review_state      /health 를 읽어 "<review_active> <draining 0|1> <drain_on 0|1> <delib_active> <delib_queued>" 를 찍는다.
#       0 = 읽었다 · 2 = 서버가 받지 않는다(내려가 있다·JSON 이 아니다) · 3 = 옛 판(/health 에 review_active·drain 이 없다) ·
#       4 = 매달렸다(4초 안에 답하지 않았다).
#   hwax_drain on <all|panels> <ttl_s> <by> <reason>         깃발을 세우거나 수명을 늘린다.
#   hwax_drain until-idle <grace_s> <max_s> <by> <reason>    scope panels — 심의 합이 0 이 된 뒤 grace_s 에 풀린다(세운 때부터 max_s 상한).
#   hwax_drain hold <by> <reason>                            사람의 고정(scope all, 수명 없음 — 사람이 내릴 때까지).
#   hwax_drain off <by> [force]                              내린다. 세운 주체가 아니거나 고정이면 force 가 있어야 한다.
#   hwax_drain status                                        GET /drain.
#       한 줄 설명(깃발 모양 또는 거절 사유)을 찍는다. 0 = 됐다 · 2 = 서버가 받지 않는다(연결 거절) · 3 = /drain 을 모른다(404, 옛 판) ·
#       4 = 매달렸다 · 5 = 사람의 고정(409, 깃발이 hold) · 7 = 다른 주인의 깃발(409, hold 아님 — drain_owned 등) ·
#       6 = 거절(422 bad_request · 503 drain_unavailable · 그 밖의 상태). 5·7 은 둘 다 남의 것이라 건드리지 않는다. 6 은 진짜 실패다 —
#       옛 판(3)과 섞지 않는다.
#   hwax_drain_owner           GET /drain 한 번 — 살아 있는 깃발의 "<hold 0|1> <by>" 를 찍는다(꺼져 있으면 빈 줄). 0 = 읽었다 · 2·3·4·6 은
#       위와 같다. update-all 이 § 머리에서 '누가 내렸나' 를 이것과 시각으로 짐작한다 — 그 한계는 update-all 의 _hwax_drain_tick 머리 주석.
#   hwax_review_wait <max_s>   도는 카드 대조(review_active)가 0 이 될 때까지 2초마다 본다. 마지막에 본 건수를 찍는다.
#       0 = 비었다(또는 서버가 내려갔다 — 기다릴 것이 없다) · 1 = 시간이 다 됐다.
#   hwax_review_brief          §6 헬스게이트 한 줄(깃발·도는 카드 대조·챗 첫 조각 지연)을 찍는다.
#       0 = 정상 · 1 = 챗이 느리다(load.chat.slow — ⚠ 로 낸다) · 2 = 못 읽었다 · 3 = 옛 판 · 4 = 매달렸다.
#
#   주소는 HWAX_AGENT_URL(기본 http://127.0.0.1:9009) — 시험이 실물 9009 를 두드리지 않게 바꿔 끼운다. 호출은 전부
#   --noproxy '*' · -m 4 다(운영자 셸의 http_proxy 를 타면 프록시가 이 박스의 루프백에 못 닿는다).
#   TTL 은 21,600초(6시간)에서 자른다 — 엔진이 요청 하나의 ttl_s 를 그보다 길게 받지 않는다(422). 같은 주인이 살아 있는 깃발을
#   다시 늘리면 엔진의 6시간 창도 다시 시작하므로, § 머리마다 늘리는 update-all 은 몇 시간을 돌아도 깃발이 끊기지 않는다.
#   양의 정수가 아닌 TTL 은 1800 으로 읽는다(0 은 엔진이 422 로 거절한다).
#
# ⚠ 0 아닌 값을 정상으로 돌려준다 — `set -e` 스크립트에서는 `_out="$(hwax_drain …)" || _rc=$?` 로 받는다. 맨 문장이면 3·5 에서
#   스크립트가 조용히 끝난다(images-from-drive 가 그 모양으로 사흘 동안 포털 배포를 죽였다 — f1958af).
HWAX_DRAIN_TTL_CAP=21600

# <값> <기본값> [상한] — 숫자만으로 된 값이면 그 수(0 도 그대로), 아니면 기본값. 상한을 넘으면 상한(없으면 999999999 —
# 셸 정수가 넘치지 않게).
_hwax_drain_secs() {
  local v="${1:-}" d="${2:-0}" cap="${3:-999999999}"
  case "$v" in ''|*[!0-9]*) v="$d" ;; esac
  v="${v#"${v%%[!0]*}"}"; v="${v:-0}"            # 앞의 0 을 뗀다(10# 없이 8진수로 읽히지 않게)
  if [ "${#v}" -gt "${#cap}" ] || [ "$v" -gt "$cap" ]; then v="$cap"; fi
  printf '%s' "$v"
}

# curl 한 번 — 본문을 _HWAX_DRAIN_BODY 에, 상태를 _HWAX_DRAIN_CODE 에 둔다. 0 = 답을 받았다 · 2 = 받지 않는다 · 4 = 매달렸다.
_hwax_drain_http() {  # <GET|POST> <경로> [JSON]
  local base="${HWAX_AGENT_URL:-http://127.0.0.1:9009}" resp rc=0
  base="${base%/}"
  if [ "$1" = POST ]; then
    resp="$(curl -s --noproxy '*' -m 4 -X POST -H 'content-type: application/json' --data-binary "${3:-}" \
              -w '\n%{http_code}' "$base$2" 2>/dev/null)" || rc=$?
  else
    resp="$(curl -s --noproxy '*' -m 4 -w '\n%{http_code}' "$base$2" 2>/dev/null)" || rc=$?
  fi
  _HWAX_DRAIN_CODE="${resp##*$'\n'}"; _HWAX_DRAIN_BODY="${resp%$'\n'*}"
  [ "$rc" = 28 ] && return 4
  [ "$rc" = 0 ] || return 2
  return 0
}

hwax_review_state() {
  local rc=0
  _hwax_drain_http GET /health || rc=$?
  [ "$rc" = 0 ] || return "$rc"
  [ "$_HWAX_DRAIN_CODE" = 200 ] || return 2
  B="$_HWAX_DRAIN_BODY" python3 - <<'PY'
import json, os, sys
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(2)
if not isinstance(h, dict):
    sys.exit(2)
if "review_active" not in h or "drain" not in h:
    sys.exit(3)                      # 비우기를 모르는 옛 판
n = lambda v: v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None
ra, da, dq = n(h.get("review_active")), n(h.get("delib_active", 0)), n(h.get("delib_queued", 0))
d = h.get("drain") if isinstance(h.get("drain"), dict) else {}
if None in (ra, da, dq):
    sys.exit(2)
print(ra, 1 if h.get("draining") is True else 0, 1 if d.get("on") is True else 0, da, dq)
PY
}

# 응답 본문을 한 줄로 — 깃발 모양(on·scope·by·남은 수명·고정)과 도는 수, 또는 거절 사유.
_hwax_drain_describe() {  # <상태 코드> <본문>
  C="$1" B="$2" python3 - <<'PY'
import json, os, time
code, raw = os.environ["C"], os.environ["B"]
try:
    b = json.loads(raw)
except ValueError:
    b = None

def flag(d):
    if not isinstance(d, dict) or d.get("on") is not True:
        return "깃발 꺼짐"
    now, bits = time.time(), [f"scope {d.get('scope')}", f"by {str(d.get('by'))[:60]}"]
    if isinstance(d.get("until"), (int, float)):
        bits.append(f"남은 {max(0, int(d['until'] - now))}초")
    ui = d.get("until_idle")
    if isinstance(ui, dict):
        w = f"심의가 0 이 된 뒤 {ui.get('grace_s'):g}초" if isinstance(ui.get("grace_s"), (int, float)) else "심의가 0 이 된 뒤"
        if isinstance(ui.get("max_until"), (int, float)):
            w += f"(상한까지 {max(0, int(ui['max_until'] - now))}초)"
        bits.append(w)
    if d.get("hold") is True:
        bits.append("고정(hold)")
    return "깃발 on(" + " · ".join(bits) + ")"

def counts(d):
    out = []
    if isinstance(d.get("review_active"), int):
        out.append(f"카드 대조 {d['review_active']}건")
    if isinstance(d.get("delib_active"), int):
        out.append(f"심의 {d['delib_active']}건 진행·{d.get('delib_queued', 0)}건 대기")
    return out

if code == "200" and isinstance(b, dict):
    print(" · ".join([flag(b)] + counts(b)))
elif code == "409" and isinstance(b, dict):
    d = b.get("drain") if isinstance(b.get("drain"), dict) else b
    who = d.get("by") or d.get("owner") or "?"
    held = d.get("hold") is True
    kind = "사람이 고정한 깃발" if held else "다른 주체가 세운 깃발"
    print(f"{kind}(by {str(who)[:60]} · scope {d.get('scope')} · {b.get('code', '409')})")
    raise SystemExit(5 if held else 7)
elif code == "404":
    print("HTTP 404 — /drain 이 없다(옛 판)")
else:
    why = (f"{b.get('code')} — {str(b.get('message', ''))[:160]}" if isinstance(b, dict) else raw[:160].replace("\n", " "))
    print(f"HTTP {code} {why}")
PY
}

hwax_drain() {
  local op="${1:-}" req="" rc=0 a="" b=""
  case "$op" in
    on)
      a="$(_hwax_drain_secs "${3:-}" 1800 "$HWAX_DRAIN_TTL_CAP")"; [ "$a" -gt 0 ] || a=1800
      req="$(D_OP=on D_SCOPE="${2:-}" D_TTL="$a" D_BY="${4:-}" D_REASON="${5:-}" _hwax_drain_req)" ;;
    until-idle)
      a="$(_hwax_drain_secs "${2:-}" 1800)"; [ "$a" -gt 0 ] || a=1800
      b="$(_hwax_drain_secs "${3:-}" 46800)"; [ "$b" -gt 0 ] || b=46800
      [ "$a" -le "$b" ] || a="$b"                     # 엔진은 grace_s ≤ max_s 만 받는다
      req="$(D_OP=until-idle D_GRACE="$a" D_MAX="$b" D_BY="${4:-}" D_REASON="${5:-}" _hwax_drain_req)" ;;
    hold) req="$(D_OP=hold D_BY="${2:-}" D_REASON="${3:-}" _hwax_drain_req)" ;;
    off)  req="$(D_OP=off D_BY="${2:-}" D_FORCE="${3:-}" _hwax_drain_req)" ;;
    status) ;;
    *) echo "hwax_drain: 모르는 명령 '$op' — on · until-idle · hold · off · status" >&2; return 6 ;;
  esac
  if [ "$op" = status ]; then _hwax_drain_http GET /drain || rc=$?; else _hwax_drain_http POST /drain "$req" || rc=$?; fi
  case "$rc" in
    2) echo "에이전트 서버가 받지 않는다(내려가 있다)"; return 2 ;;
    4) echo "에이전트 서버가 4초 안에 답하지 않았다(매달림)"; return 4 ;;
  esac
  rc=0; _hwax_drain_describe "$_HWAX_DRAIN_CODE" "$_HWAX_DRAIN_BODY" || rc=$?
  case "$_HWAX_DRAIN_CODE" in
    200) return 0 ;;
    404) return 3 ;;
    409) [ "$rc" = 7 ] && return 7; return 5 ;;     # 고정이 아니라는 것이 보일 때만 7 — 모르면 사람의 고정으로 읽는다
    *)   return 6 ;;
  esac
}

hwax_drain_owner() {
  local rc=0
  _hwax_drain_http GET /drain || rc=$?
  [ "$rc" = 0 ] || return "$rc"
  case "$_HWAX_DRAIN_CODE" in 200) ;; 404) return 3 ;; *) return 6 ;; esac
  B="$_HWAX_DRAIN_BODY" python3 - <<'PY'
import json, os, sys
try:
    d = json.loads(os.environ["B"])
except ValueError:
    sys.exit(6)
if not isinstance(d, dict):
    sys.exit(6)
if d.get("on") is True:
    print("1" if d.get("hold") is True else "0", str(d.get("by") or ""))
PY
}

# 요청 본문 — by·reason 은 사람이 쓴 글이라 셸에서 JSON 을 엮지 않는다(따옴표 하나에 깨진다).
_hwax_drain_req() {
  python3 - <<'PY'
import json, os
e = os.environ.get
op = e("D_OP")
if op == "on":
    body = {"on": True, "scope": e("D_SCOPE", ""), "ttl_s": int(e("D_TTL")), "by": e("D_BY", ""), "reason": e("D_REASON", "")}
elif op == "until-idle":
    body = {"on": True, "scope": "panels", "until_idle": {"grace_s": int(e("D_GRACE")), "max_s": int(e("D_MAX"))},
            "by": e("D_BY", ""), "reason": e("D_REASON", "")}
elif op == "hold":
    body = {"on": True, "scope": "all", "hold": True, "by": e("D_BY", ""), "reason": e("D_REASON", "")}
else:
    body = {"on": False, "by": e("D_BY", "")}
    if e("D_FORCE") == "force":
        body["force"] = True
print(json.dumps(body, ensure_ascii=False))
PY
}

hwax_review_wait() {
  local max t0 st rc n=0
  max="$(_hwax_drain_secs "${1:-}" 0)"; t0=$SECONDS
  while :; do
    rc=0; st="$(hwax_review_state)" || rc=$?
    case "$rc" in
      0) n="${st%% *}"; [ "$n" = 0 ] && { echo 0; return 0; } ;;
      2|3) echo 0; return 0 ;;          # 내려갔다·옛 판 — 기다릴 카드 대조가 없다(있어도 셀 수 없다)
    esac                                 # 4(매달림)는 시간이 다 될 때까지 다시 본다
    if [ $((SECONDS - t0)) -ge "$max" ]; then echo "$n"; return 1; fi
    sleep 2
  done
}

hwax_review_brief() {
  local rc=0
  _hwax_drain_http GET /health || rc=$?
  [ "$rc" = 0 ] || return "$rc"
  [ "$_HWAX_DRAIN_CODE" = 200 ] || return 2
  B="$_HWAX_DRAIN_BODY" python3 - <<'PY'
import json, os, sys, time
try:
    h = json.loads(os.environ["B"])
except ValueError:
    sys.exit(2)
if not isinstance(h, dict):
    sys.exit(2)
if "review_active" not in h or "drain" not in h:
    sys.exit(3)
d, now = h.get("drain") if isinstance(h.get("drain"), dict) else {}, time.time()
if d.get("on") is True:
    bits = [f"scope {d.get('scope')}", f"by {str(d.get('by'))[:60]}"]
    if isinstance(d.get("until"), (int, float)):
        bits.append(f"남은 {max(0, int(d['until'] - now))}초")
    ui = d.get("until_idle")
    if isinstance(ui, dict):
        bits.append(f"심의가 0 이 된 뒤 {ui.get('grace_s')}초" + ("" if ui.get("idle_since") is None else "(창이 열렸다)"))
    if d.get("hold") is True:
        bits.append("고정(hold)")
    line = "비우기 깃발 on(" + " · ".join(bits) + ")"
else:
    line = "비우기 깃발 꺼짐"
line += f" · 도는 카드 대조 {h.get('review_active')}건"
chat = ((h.get("load") or {}).get("chat") or {}) if isinstance(h.get("load"), dict) else {}
tt = chat.get("ttft_ms") if isinstance(chat.get("ttft_ms"), dict) else {}
idle, rev = tt.get("idle") or {}, tt.get("review") or {}
if chat.get("slow") is True:
    print(line + f" · 챗 첫 조각 지연이 평소의 2배를 넘는다(카드 대조 중 p50 {rev.get('p50')}ms / 평소 p50 {idle.get('p50')}ms"
          + (f", {chat.get('slow_since')} 부터" if chat.get("slow_since") else "") + ")")
    sys.exit(1)
if isinstance(idle.get("p50"), (int, float)) and isinstance(rev.get("p50"), (int, float)):
    line += f" · 챗 첫 조각 p50 {rev['p50']}ms(평소 {idle['p50']}ms)"
print(line)
PY
}
