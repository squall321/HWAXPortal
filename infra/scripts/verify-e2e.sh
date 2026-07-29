#!/usr/bin/env bash
# 사용자가 실제로 타는 경로를 브라우저와 같은 방식으로 끝까지 확인하는 검증기.
#
# 왜 필요한가: 지금까지 나온 장애는 전부 "실패가 성공처럼 보이거나 로그에만 남는" 부류였다.
#   · 자산 자리에 포털 SPA HTML 이 200 으로 반환   → 상태코드만 보면 정상
#   · 도구 로딩 실패 → 도구 0개 에이전트           → 오류 없이 모델이 말만 함
#   · 도구 호출문이 텍스트로 누출                  → 응답은 오니 정상으로 보임
#   · 옛 코드 워커가 45초마다 고친 설정을 되돌림   → 고친 직후엔 정상
#   · 앱이 45초마다 기동 실패                      → 로그에만 있고 아무도 안 봄
#   · 좀비 인스턴스가 새 SIF 를 가림               → 빌드는 성공이라 정상으로 보임
# 그래서 상태코드가 아니라 **내용**(Content-Type·본문)과 **지속성**(반복 실패·코드 드리프트)을 본다.
#
# 사용:  bash infra/scripts/verify-e2e.sh          # 전체
#        VERIFY_SKIP_CHAT=1 bash …                 # LLM 호출 생략(빠른 점검)
# ⚠ pipefail 주의: `printf … | grep -q` 는 grep 이 첫 매칭에서 즉시 끝나 printf 가 SIGPIPE 를
# 받고 파이프라인이 실패로 판정된다(실측: 도구가 정상 호출됐는데 0/3 으로 오보). 문자열 검사에는
# 파이프 대신 herestring(<<<)을 쓴다.
set -uo pipefail

NGINX="${VERIFY_NGINX:-http://127.0.0.1:8088}"
AGENT="${VERIFY_AGENT:-http://127.0.0.1:9009}"
HEAX_ROOT="${VERIFY_HEAX_ROOT:-$HOME/claude/HEAXHub}"
FAIL=0; WARN=0; PASS=0

red()  { printf '  \033[31m✗ %s\033[0m\n' "$*"; FAIL=$((FAIL+1)); }
yel()  { printf '  \033[33m! %s\033[0m\n' "$*"; WARN=$((WARN+1)); }
grn()  { printf '  \033[32m✓ %s\033[0m\n' "$*"; PASS=$((PASS+1)); }
sec()  { printf '\n\033[1m── %s\033[0m\n' "$*"; }

# 자산 URL 을 브라우저와 동일하게 환산해 받아 본다. HTML 이 오면 SPA 폴백에 먹힌 것 = 파손.
check_page_assets() {  # $1=라벨  $2=페이지 URL  $3=베이스(상대경로 기준)
  local label="$1" url="$2" base="$3" html asset aurl ctype
  html="$(curl -s -L -m 10 "$url" 2>/dev/null)" || { red "$label — 응답 없음"; return; }
  asset="$(printf '%s' "$html" | grep -oE '(src|href)="[^"]+\.(js|css)[^"]*"' \
           | grep -vE '="https?://' | head -1 | sed -E 's/^(src|href)="//; s/"$//')"
  if [ -z "$asset" ]; then grn "$label — 페이지 정상(외부 자산 없음)"; return; fi
  case "$asset" in
    /*)  aurl="$NGINX$asset" ;;
    ./*) aurl="$base/${asset#./}" ;;
    *)   aurl="$base/$asset" ;;
  esac
  ctype="$(curl -s -o /dev/null -w '%{content_type}' -m 10 "$aurl" 2>/dev/null)"
  case "$ctype" in
    *text/html*) red "$label — 자산이 HTML 로 반환(SPA 폴백에 먹힘): $asset" ;;
    "")          red "$label — 자산 응답 없음: $asset" ;;
    *)           grn "$label — 자산 $ctype" ;;
  esac
}

sec "1. 시스템 경로 (사용자가 타는 nginx 경유)"
for r in "포털|$NGINX/|$NGINX" "heax-hub|$NGINX/heax-hub/|$NGINX/heax-hub" \
         "ai-data-hub|$NGINX/ai-data-hub/|$NGINX/ai-data-hub" \
         "signalforge|$NGINX/signalforge/|$NGINX/signalforge" \
         "mx-white-paper|$NGINX/mx-white-paper/|$NGINX/mx-white-paper" \
         "report-archive|$NGINX/report-archive/|$NGINX/report-archive"; do
  IFS='|' read -r n u b <<<"$r"
  code="$(curl -s -o /dev/null -w '%{http_code}' -L -m 10 "$u" 2>/dev/null)"
  case "$code" in
    200|304) check_page_assets "$n" "$u" "$b" ;;
    401|403) grn "$n — $code (인증 요구, 서비스 정상)" ;;
    *)       red "$n — $code" ;;
  esac
done

sec "2. heax 호스팅 앱 (등록된 전부)"
if [ -d "$HEAX_ROOT/var/integration_state" ]; then
  for f in "$HEAX_ROOT"/var/integration_state/*.json; do
    [ -e "$f" ] || continue
    a="$(basename "$f" .json)"
    code="$(curl -s -o /dev/null -w '%{http_code}' -L -m 10 "$NGINX/apps/$a/" 2>/dev/null)"
    case "$code" in
      200|304) check_page_assets "앱 $a" "$NGINX/apps/$a/" "$NGINX/apps/$a" ;;
      401|403) grn "앱 $a — $code (비공개/UI 없음)" ;;
      *)       red "앱 $a — $code (미기동/라우트 없음)" ;;
    esac
  done
else
  yel "heax integration_state 없음 — 앱 점검 생략 ($HEAX_ROOT)"
fi

sec "3. WebSocket 업그레이드 (101 이어야 함 — 200/403 은 파손)"
for a in heax_demo_streamlit; do
  [ -f "$HEAX_ROOT/var/integration_state/$a.json" ] || continue
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 10 \
    -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
    -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
    "$NGINX/apps/$a/_stcore/stream" 2>/dev/null)"
  [ "$code" = "101" ] && grn "WS $a — 101" || red "WS $a — $code (업그레이드 실패)"
done

sec "4. 반복 실패 (로그에만 남아 아무도 안 보던 것)"
# ⚠ 로그 전체를 세면 이미 고친 과거 기록이 계속 실패로 잡혀 거짓경보가 된다(실측: 고친 지
# 23분 지난 앱이 '반복 실패 중'으로 뜸). 반드시 **현재 워커가 뜬 이후**만 본다.
WLOG="$HEAX_ROOT/var/logs/worker.log"
if [ -f "$WLOG" ]; then
  wpid="$(pgrep -f 'celery -A app.workers.celery_app worker' | head -1)"
  since=""
  [ -n "$wpid" ] && since="$(date -d "$(ps -o lstart= -p "$wpid" 2>/dev/null)" '+%H:%M:%S' 2>/dev/null)"
  # 중첩 heredoc 은 command substitution 안에서 since 가 비는 사고가 났다(실측: 전체 로그를
  # 세어 이미 고친 문제를 계속 실패로 보고). awk 한 줄로 단순화한다.
  since="${since:-00:00:00}"
  n_put=$(awk -v s="$since" '$0 ~ /PUT http:\/\/127.0.0.1:2019\/id\/app-/ && /400/ { if (match($0,/[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/) && substr($0,RSTART,8) >= s) n++ } END{print n+0}' "$WLOG")
  n_patch=$(awk -v s="$since" '$0 ~ /PATCH http:\/\/127.0.0.1:2019\/id\/app-/ { if (match($0,/[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/) && substr($0,RSTART,8) >= s) n++ } END{print n+0}' "$WLOG")
  n_del=$(awk -v s="$since" '$0 ~ /DELETE http:\/\/127.0.0.1:2019\/id\/app-/ { if (match($0,/[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/) && substr($0,RSTART,8) >= s) n++ } END{print n+0}' "$WLOG")
  n_failed=$(awk -v s="$since" '{ if (match($0,/[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/) && substr($0,RSTART,8) >= s && match($0,/reconcile: [a-z0-9-]+ failed/)) { t=substr($0,RSTART+11); sub(/ failed.*/,"",t); print t } }' "$WLOG" | sort -u | paste -sd, -)
  if [ -n "${n_failed:-}" ]; then
    for b in ${n_failed//,/ }; do red "앱 $b — reconcile 이 반복 실패시키는 중 (현재 워커 기준)"; done
  else
    grn "reconcile 반복 실패 없음 (현재 워커 기준)"
  fi
  if [ "${n_put:-0}" -gt 0 ]; then
    red "Caddy 라우트가 PUT 400 폴백으로 DELETE+재삽입 중 (PUT400=$n_put, DELETE=$n_del) — 삭제 창 발생"
  else
    grn "Caddy 라우트 재등록 정상 (PATCH=$n_patch, DELETE=$n_del)"
  fi
fi

sec "5. 실행 코드 드리프트 (배포했는데 옛 코드가 도는 경우)"
if [ -d "$HEAX_ROOT/.git" ]; then
  head_rev="$(git -C "$HEAX_ROOT" rev-parse HEAD 2>/dev/null)"
  run_rev="$(cat "$HEAX_ROOT/var/run/backend.rev" 2>/dev/null || echo '')"
  if [ -z "$run_rev" ]; then
    yel "heax 백엔드 rev 기록 없음 — start.sh 경유로 기동되지 않았다(수동 기동). 코드 신선도 미확인"
  elif [ "$run_rev" = "$head_rev" ]; then
    grn "heax 백엔드 = HEAD(${head_rev:0:8})"
  else
    red "heax 백엔드가 옛 코드로 실행 중 (실행=${run_rev:0:8} / HEAD=${head_rev:0:8}) — start.sh 재실행 필요"
  fi
  # celery 는 별도 프로세스라 백엔드만 재기동하면 옛 코드가 남는다. 다만 '프로세스 나이'로
  # 재면 코드가 안 바뀌었는데도 계속 경고한다 — 마지막 **코드 변경 시각**과 비교한다.
  wpid="$(pgrep -f 'celery -A app.workers.celery_app worker' | head -1)"
  if [ -n "$wpid" ]; then
    w_epoch="$(date -d "$(ps -o lstart= -p "$wpid" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
    code_epoch="$(git -C "$HEAX_ROOT" log -1 --format=%ct -- backend/app 2>/dev/null || echo 0)"
    if [ "$w_epoch" -lt "$code_epoch" ]; then
      red "celery worker 가 마지막 코드 변경보다 오래됨 — 옛 코드로 라우트를 덮어쓸 수 있음"
    else
      grn "celery worker 가 최신 코드 이후 기동됨"
    fi
  fi
fi

sec "6. 좀비 인스턴스 (새 SIF 를 가리는 옛 인스턴스)"
APPT="$(command -v apptainer || true)"
for c in "$HOME"/claude/HWAXPortal/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$c" ] && APPT="$c" && break; done
if [ -n "$APPT" ]; then
  zombies=0
  while read -r name _pid _ip sif; do
    case "$name" in heax_app_*) ;; *) continue ;; esac
    [ -f "$sif" ] || continue
    # 인스턴스 시작 시각보다 SIF 파일이 더 새것이면, 그 인스턴스는 옛 rootfs 를 붙들고 있다.
    ist="$(ps -o lstart= -p "$_pid" 2>/dev/null)"; [ -n "$ist" ] || continue
    if [ "$(stat -c %Y "$sif")" -gt "$(date -d "$ist" +%s 2>/dev/null || echo 9999999999)" ]; then
      red "좀비 인스턴스 $name — SIF 가 인스턴스보다 새것(재기동 필요)"; zombies=$((zombies+1))
    fi
  done < <("$APPT" instance list 2>/dev/null | awk 'NR>1{print $1, $2, $3, $4}')
  [ "$zombies" = 0 ] && grn "좀비 인스턴스 없음"
fi

sec "7. 도구 호출 (실제로 실행되는지 — 간헐 실패까지 잡는다)"
# 1회만 보면 간헐 실패를 놓치고, 타임아웃을 '미실행'으로 오판한다(실측: 1회 검사에서
# 거짓 실패 → 재측정 6/6 성공). 여러 번 돌려 성공률로 판정하고 타임아웃은 따로 센다.
if [ "${VERIFY_SKIP_CHAT:-0}" = "1" ]; then
  yel "VERIFY_SKIP_CHAT=1 — 생략"
else
  tries="${VERIFY_CHAT_TRIES:-3}"; ran=0; leaked=0; timeout_n=0
  for _i in $(seq 1 "$tries"); do
    out="$(curl -s -N -m "${VERIFY_CHAT_TIMEOUT:-300}" -X POST "$AGENT/chat" \
          -H 'Content-Type: application/json' -H 'X-HWAX-Groups: ai-data-hub,heax-hub' \
          -d '{"message":"열충격 데이터셋 요약을 조회해줘"}' 2>/dev/null)"
    if [ -z "$out" ]; then timeout_n=$((timeout_n+1)); continue; fi
    # SSE 종료 표식은 'event: done' 이다. '"done"' 으로 찾으면 정상 완료를 타임아웃으로
    # 오판한다(실측: 4초에 끝난 응답을 3/3 타임아웃으로 보고).
    grep -q '^event: done' <<<"$out" || { timeout_n=$((timeout_n+1)); continue; }
    grep -q '"tool": "[a-z]' <<<"$out" && ran=$((ran+1))
    grep -qE '</tool_call>|"arguments":' <<<"$out" && leaked=$((leaked+1))
    grep -q '불러오지 못했습니다' <<<"$out" && red "도구 목록 로딩 실패(게이트웨이 인증/연결)"
  done
  [ "$timeout_n" -gt 0 ] && yel "챗 미완료 $timeout_n/$tries (타임아웃 — 도구 실패와 구분)"
  done_n=$((tries - timeout_n))
  if [ "$done_n" -eq 0 ]; then
    red "챗이 한 번도 완료되지 않음 — 에이전트/LLM 확인"
  elif [ "$ran" -eq "$done_n" ]; then
    grn "도구 실행 $ran/$done_n"
  else
    red "도구 실행 $ran/$done_n — 간헐적으로 호출되지 않음"
  fi
  [ "$leaked" -eq 0 ] && grn "호출문 누출 없음" || red "호출문 누출 $leaked/$done_n — 스트리밍 파서 문제"
fi

sec "결과"
printf '  통과 %d · 경고 %d · 실패 %d\n' "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
