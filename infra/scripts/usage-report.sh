#!/usr/bin/env bash
# 접속 집계 — "얼마나 많은 사람이 쓰는가"를 네 원천에서 센다(전부 읽기 전용).
#
#   ① nginx 정문(:8088)  infra/data/nginx-access.log      — 실클라이언트 IP (2026-09-02 부터)
#   ② heax Caddy(:4180)  HEAXHub/var/caddy/caddy.log      — 앱 허브 직접 접속 IP
#   ③ 포털 감사           backend/secrets/agent_audit.sqlite — SSO 신원(이메일) 단위 · IP 보다 정확
#   ④ 게이트웨이 감사      HWAXMcpGateway/audit.jsonl        — MCP 를 쓰는 신원
#
# 사용:  ./usage-report.sh [일수]     기본 7일. IP 는 127.0.0.1(프록시 내부 트래픽) 제외.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
find_repo() { for c in "$PARENT/$1" "$HOME/Projects/$1" "$HOME/claude/$1"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
DAYS="${1:-7}"
SINCE="$(date -u -d "-${DAYS} days" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%S)"
hr() { printf '\n\033[1;36m── %s ─────────────────────────\033[0m\n' "$*"; }

hr "① 포털 정문 nginx (:8088) — 최근 ${DAYS}일 실IP"
NLOG="$ROOT/infra/data/nginx-access.log"
# SSO 전면 전에는 여러 명이 데모 계정 하나를 공유하므로, 사람 수 근사의 주 원천은
# 신원(③)이 아니라 여기 IP 다. 스캐너와 실사용을 가르기 위해 '앱 경로'(auth/agent/
# api/systems 에 4xx 미만)를 접촉한 IP 를 따로 세고, IP×브라우저(UA) 조합으로
# 같은 IP(사내 NAT) 뒤의 기기 수를 근사한다.
_ngx() {  # $1: table(앱 IP 별 히트) | sum(요약 수치)
  awk -F'"' -v since="$SINCE" -v mode="$1" '
    {
      ip=$1; sub(/ +$/, "", ip)
      # XFF 는 remote 가 내부망(우리 앞단 프록시)일 때만 신뢰 — 외부인의 XFF 위조 방지.
      if ($2 != "-" && $2 != "" &&
          ip ~ /^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)/) {
        split($2, x, ","); ip=x[1]; gsub(/ /, "", ip)
      }
      t=$3; gsub(/[\[\] ]/, "", t)
      if (t < since || ip == "127.0.0.1") next
      split($5, s, " "); st=s[1]+0
      isapp = (st < 400 && $4 ~ /^[A-Z]+ \/(auth|agent|api|systems|upload)/) ? 1 : 0
      hits[ip]++; combo[ip "|" $6]=1
      if (isapp) { app[ip]++; appcombo[ip "|" $6]=1 }
    }
    END {
      if (mode == "table") { for (i in app) printf "%d %s\n", app[i], i }
      else printf "  고유 IP %d (그중 앱 경로 접촉 %d) · IP×브라우저 조합 %d (앱 %d — 대략 기기 수)\n", \
                  length(hits), length(app), length(combo), length(appcombo)
    }' "$NLOG"
}
if [ -s "$NLOG" ]; then
  T="$(_ngx table | sort -rn | head -20 | awk '{printf "  %6d  %s\n", $1, $2}')"
  [ -n "$T" ] && { echo "  [앱 경로 접촉 IP — 실사용 근사]"; echo "$T"; } \
              || echo "  (앱 경로 접촉 IP 없음)"
  _ngx sum
  echo "  (기록 시작 2026-09-02 23:20 — 그 전 정문 트래픽은 소실)"
else
  echo "  (기록 없음 — 2026-09-02 에 로깅을 켰다. 그 전 정문 트래픽은 소실)"
fi

hr "② heax Caddy (:4180) — 실IP"
CLOG="$(find_repo HEAXHub)/var/caddy/caddy.log"
if [ -s "$CLOG" ]; then
  # Caddy JSON 라인 — client_ip/remote_ip 필드만 뽑는다(파서 없이 grep, 토큰류 무출력)
  # grep 무매치(=전부 프록시 내부 트래픽)는 정상 상황이라 set -e 에서 빼준다.
  OUT="$( { grep -oE '"(client_ip|remote_ip)":"[0-9.]+"' "$CLOG" | grep -oE '[0-9.]+' \
    | grep -v '^127\.0\.0\.1$' | sort | uniq -c | sort -rn | head -15 \
    | awk '{printf "  %6d  %s\n", $1, $2}'; } || true )"
  [ -n "$OUT" ] && echo "$OUT" || echo "  (전부 127.0.0.1 — 접근로그 미설정, 에러 라인만 존재)"
else
  echo "  (로그 없음)"
fi

hr "③ 포털 SSO·PAT 신원 (agent_audit) — 사람 단위 정본"
ADB="$ROOT/backend/secrets/agent_audit.sqlite"
if [ -s "$ADB" ]; then
  python3 - "$ADB" <<'PY'
import datetime
import sqlite3, sys

def _when(v):
    try:
        return datetime.datetime.fromtimestamp(float(v), datetime.UTC).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return v or "?"
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
tabs = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
for t in tabs:
    cols = [c[1] for c in db.execute(f"PRAGMA table_info({t})")]
    who = next((c for c in cols if c in ("principal", "subject", "user", "email")), None)
    ts = next((c for c in cols if c in ("ts", "time", "created_at", "at")), None)
    if not who:
        continue
    rows = db.execute(
        f"SELECT {who}, COUNT(*), MAX({ts}) FROM {t} GROUP BY {who} ORDER BY 2 DESC" if ts
        else f"SELECT {who}, COUNT(*), '' FROM {t} GROUP BY {who} ORDER BY 2 DESC").fetchall()
    print(f"  [{t}] 신원 {len(rows)}명")
    for w, n, last in rows[:15]:
        print(f"    {n:6d}  {w}  (마지막 {_when(last)})")
PY
else
  echo "  (감사 DB 없음)"
fi

hr "④ 게이트웨이 MCP 신원 (audit.jsonl)"
GLOG="$(find_repo HWAXMcpGateway)/audit.jsonl"
if [ -s "$GLOG" ]; then
  { grep -oE '"caller": *"[^"]+"' "$GLOG" | sed 's/.*: *"//;s/"//' || true
    grep -oE '"error": *"as:[^"@]+@[^"]+"' "$GLOG" | sed 's/.*as://;s/"//' || true ; } 2>/dev/null \
    | sort | uniq -c | sort -rn | head -15 | awk '{printf "  %6d  %s\n", $1, $2}'
  echo "  (caller 없는 줄 = 내부 에이전트 서비스 계정 경유)"
else
  echo "  (감사 로그 없음)"
fi

hr "읽는 법"
echo "  · SSO 전면 전(데모 계정 공유 중)에는 ①의 IP·IP×브라우저 조합이 사람 수의 주 근사다."
echo "    ③(신원)은 계정 단위라 지금은 하한일 뿐이다. SSO 가 깔리면 ③이 정본으로 복귀한다."
echo "  · IP 의 한계 — 사내 NAT 뒤 여러 명이 한 IP 로 겹치면 과소, 한 사람이 집·회사·폰을"
echo "    오가면 과대. 그 사이를 IP×브라우저(UA) 조합(대략 기기 수)이 좁혀 준다."
echo "  · '앱 경로 접촉'(auth/agent/api/systems 4xx 미만)이 인터넷 스캐너를 걸러낸 실사용 근사다."
