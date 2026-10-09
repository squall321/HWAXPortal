#!/usr/bin/env bash
# 리스크 심사 재설계 M0-a — 이 박스의 재고를 읽기 전용으로 찍는다(아무것도 바꾸지 않는다)
#
# 쓰는 법   ./infra/scripts/risk-review-inventory.sh
# 찍는 것   모델 창을 읽은 방식 · 시간·출력 한도 설정 · 리스크 앱의 타깃·변경 수·패널 수 · 두 번째 패널 저장 실패의 흔적
# 출력을 통째로 dev 에 넘기면 된다. 비밀은 찍지 않는다(설정은 아래에 적은 이름의 값만 읽는다).
# 근거      docs/risk-review-redesign/PLAN.md 3절 M0
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"      # HWAXPortal
AGENT="$ROOT/../HWAXAgentServer"
HEAX="$ROOT/../HEAXHub"
DB="$HEAX/var/app_data/hwax_risk/risk_review.db"

say() { printf '%s\n' "$*"; }

say "== 리스크 심사 재고 ($(date '+%Y-%m-%d %H:%M %Z'))"

say ""
say "-- 1. 에이전트 서버가 모델 창을 읽은 방식 (마지막 한 줄)"
if [ -f "$AGENT/agent-server.log" ]; then
  line="$(grep -a -E '문서 예산 기준 컨텍스트|모델 컨텍스트 조회 실패' "$AGENT/agent-server.log" | tail -1)"
  say "${line:-(그 문구가 로그에 없다 — 기동한 뒤 심의·챗을 한 번도 안 불렀을 수 있다)}"
else
  say "(agent-server.log 가 없다 — $AGENT)"
fi

say ""
say "-- 2. 시간·출력 한도 설정 (에이전트 서버 .env 에서 아래 이름만 읽는다. 없으면 코드 기본값이다)"
if [ -f "$AGENT/.env" ]; then
  found="$(grep -a -E '^(DELIB_MAX_TOKENS|DELIB_TIMEOUT_S|DELIB_LLM_MAX_RETRIES|LLM_CONTEXT_TOKENS|LLM_MAX_TOKENS|DELIB_REASONING_EFFORT|LLM_REASONING_EFFORT|DELIB_JOB_MAX_RUNNING)=' "$AGENT/.env")"
  say "${found:-(해당 이름이 하나도 없다 — 전부 기본값)}"
else
  say "(.env 가 없다 — $AGENT)"
fi
health="$(curl -s --noproxy '*' -m 5 http://127.0.0.1:9009/health 2>/dev/null)"
if [ -n "$health" ]; then
  say "health: $(printf '%s' "$health" | grep -o -E '"(delib_active|delib_queued|evid_budget|model)": *[^,}]*' | tr '\n' ' ')"
else
  say "health: (에이전트 서버 9009 가 답하지 않는다)"
fi

say ""
say "-- 3. 리스크 앱 원장 (읽기 전용)"
if [ -f "$DB" ]; then
  python3 - "$DB" <<'PY'
import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
def q(sql, args=()):
    try:
        return c.execute(sql, args).fetchall()
    except sqlite3.Error as e:      # 표가 없거나 잠겼으면 그 사실을 찍고 넘어간다
        return [("오류", str(e))]
print("스키마 버전:", q("PRAGMA user_version")[0][0])
print("타깃 종류별:", q("SELECT kind, COUNT(*) FROM rr_targets GROUP BY kind"))
print("패널 상태별:", q("SELECT status, COUNT(*) FROM rr_panels GROUP BY status"))
print("잡 상태별:", q("SELECT state, COUNT(*) FROM rr_jobs GROUP BY state"))
print("변경 비교(diff) 수:", q("SELECT COUNT(*) FROM rr_diffs")[0][0])
rows = q("SELECT d.id, LENGTH(d.diff_json), (SELECT COUNT(*) FROM rr_diff_events e WHERE e.diff_id = d.id),"
         " (SELECT COUNT(*) FROM rr_targets t WHERE t.kind = 'diff' AND t.ref_id = d.id)"
         " FROM rr_diffs d ORDER BY 3 DESC LIMIT 10")
print("변경이 많은 비교 10건 (id 앞 12자 · diff_json 글자 수 · 의미 이벤트 수 · 타깃 수):")
for r in rows:
    print("  ", str(r[0])[:12], *r[1:])
print("타깃별 패널 수 상위 5:", q("SELECT COUNT(*) FROM rr_panels GROUP BY target_key ORDER BY 1 DESC LIMIT 5"))
print("타깃별 running 에 머문 패널:", q("SELECT COUNT(*) FROM rr_panels WHERE status = 'running'")[0][0])
print("로스터 좌석 수(타깃별 상위 3):", q("SELECT COUNT(*) FROM rr_roster GROUP BY target_key ORDER BY 1 DESC LIMIT 3"))
print("보류(deferred) 좌석:", q("SELECT COUNT(*) FROM rr_coverage WHERE status = 'deferred'")[0][0])
PY
else
  say "(원장이 없다 — $DB)"
fi

say ""
say "-- 4. 두 번째 패널 저장 실패의 흔적 (앱 로그)"
LOG="$HEAX/var/logs/integration_hwax_risk.log"
if [ -f "$LOG" ]; then
  n="$(grep -a -c 'UNIQUE constraint failed: rr_seat_opinions' "$LOG")"
  say "UNIQUE constraint failed: rr_seat_opinions — ${n}줄"
  grep -a 'UNIQUE constraint failed: rr_seat_opinions' "$LOG" | tail -1 | cut -c1-200
else
  say "(앱 로그가 없다 — $LOG)"
fi
