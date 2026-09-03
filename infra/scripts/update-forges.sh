#!/usr/bin/env bash
# 표적 최신화 — update-all(전체 배포)이 무거울 때, 갱신이 잦은 것만 골라 올린다.
# (이름은 역사적 — forge 2종으로 시작해 ste·chat 이 추가됐다.)
#
#   ./infra/scripts/update-forges.sh                 # 기본: stepforge dynaforge ste chat 전부
#   ./infra/scripts/update-forges.sh dynaforge       # 골라서: stepforge|dynaforge|ste|chat
#   ./infra/scripts/update-forges.sh chat            # 챗+심의 스택만(포털·agent-server·게이트웨이)
#   ./infra/scripts/update-forges.sh restart         # 갱신 없이 전 서비스 재시작만(+nginx 부검)
#
# 포함하지 않는 것 — 포털 외 서비스(mxwp·heax·aidh·signalforge)와 AIDataHub 데이터 병합.
# 그건 update-all §2·§3 의 몫이다.
#
# 박스 자동 감지 — 리포 루트가 */Projects/* 면 cae00(운영: git pull + Drive 반입),
# 아니면 dev(로컬 소스 그대로 — 타 세션 WIP 를 pull/reset 으로 건드리지 않는다).
#
# 무엇을 하나.
#   stepforge : HEAXHub redeploy-app.sh step_forge --rebuild
#               (--rebuild 가 upstream git fetch→SIF 빌드→재기동까지. 게이트웨이는
#                지문 감지가 60초 내 자동 재집계 — 재기동 불필요)
#   dynaforge : [cae00] KooRemapper git pull --ff-only + dist-from-drive(비치명)
#               [dev]   build-frontend.sh (⚠ plain 'pnpm build' 는 포털용
#                       index.portal.html 을 안 만들어 포털 경유가 깨진다 — 실사고)
#               → stop/start → install-autostart(멱등) → :8700/:8701 프로브
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
find_repo() { for c in "$PARENT/$1" "$HOME/Projects/$1" "$HOME/claude/$1"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
case "$ROOT" in */Projects/*) BOX=cae00 ;; *) BOX=dev ;; esac
hr() { printf '\n\033[1;36m── %s ─────────────────────\033[0m\n' "$*"; }
FAIL=0

do_stepforge() {
  hr "StepForge — upstream fetch + SIF 리빌드 + 재기동"
  local heax; heax="$(find_repo HEAXHub)"
  [ -n "$heax" ] || { echo "✗ HEAXHub 리포 없음"; FAIL=1; return; }
  # ⚠ heax Settings 가 CWD 상대 .env 를 읽는다 — 포털 루트에서 부르면 포털의
  #   backend/.env(APP_ENV=dev)를 집어 ValidationError 로 죽는다(실측). heax 루트에서 실행.
  if ( cd "$heax" && bash deploy/apptainer/redeploy-app.sh step_forge --rebuild ); then
    echo "✓ step_forge 재배포 — 게이트웨이 지문 재집계는 60초 내 자동"
  else
    echo "✗ step_forge 재배포 실패"; FAIL=1
  fi
}

do_dynaforge() {
  hr "DynaForge(KooRemapper) — $BOX 모드"
  local koor; koor="$(find_repo KooRemapper)"
  [ -n "$koor" ] || { echo "✗ KooRemapper 리포 없음"; FAIL=1; return; }
  ( cd "$koor"
    if [ "$BOX" = cae00 ]; then
      git pull --ff-only || { echo "✗ git pull 실패(로컬 변경?) — 수동 확인 필요"; exit 1; }
      bash platform/infra/scripts/dist-from-drive.sh \
        || echo "  ⚠ dist-from-drive 실패(비치명) — 로컬 아티팩트로 진행"
    else
      # dev: pull 하지 않는다(타 세션 WIP 보호). 프론트만 정식 이중 빌드로 갱신.
      bash platform/infra/scripts/build-frontend.sh
    fi
    bash platform/infra/scripts/stop.sh 2>/dev/null || true
    bash platform/infra/scripts/start.sh
    bash platform/infra/scripts/install-autostart.sh || echo "  ⚠ autostart 설치 실패(비치명)"
  ) || { FAIL=1; return; }
  # 업스트림 생존 — rc 가 아니라 출력값으로 판정한다(000 폴백 덧붙임 함정, deploy-all 주석 참조).
  for p in 8700 8701; do
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$p/" 2>/dev/null)" || true
    case "${c:-000}" in
      000) echo "✗ :$p 무응답 — /apps/kooremapper* 는 502 가 된다"; FAIL=1 ;;
      *)   echo "✓ :$p → $c" ;;
    esac
  done
}

do_ste() {
  hr "STE(SmartTwinExplorer) — $BOX 모드"
  if [ "$BOX" != cae00 ]; then
    echo "· dev 스킵 — STE 웹은 헤드노드(stc) 배포라 deploy-ste 는 cae00 전용이다."
    echo "  (dev 쪽 선행은 STE 리포의 pack-staging + push-to-drive — 가이드 §4 참조)"
    return
  fi
  # deploy-ste.sh → refresh-code.sh 체인 — transport.env 존재·헤드노드 도달 같은
  # 런타임 게이트를 스스로 검사하고 명확한 메시지로 fail-fast 한다(가이드 §4).
  if bash "$ROOT/infra/scripts/deploy-ste.sh"; then
    echo "✓ STE 코드 갱신 완료"
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 6 "http://127.0.0.1:8088/ste/api/health" 2>/dev/null)" || true
    case "${c:-000}" in
      000) echo "✗ /ste/api/health 무응답 — 터널(ste-tunnel)·라우트 확인"; FAIL=1 ;;
      *)   echo "✓ /ste/api/health → $c" ;;
    esac
  else
    echo "✗ STE 갱신 실패(위 게이트 메시지 확인)"; FAIL=1
  fi
}

do_chat() {
  hr "챗·심의 스택 — 포털 + agent-server + 게이트웨이 ($BOX 모드)"
  local aserver gw
  aserver="$(find_repo HWAXAgentServer)"; gw="$(find_repo HWAXMcpGateway)"
  # ① 코드 최신화 — cae00 만 pull(dev 는 로컬 소스 보호)
  if [ "$BOX" = cae00 ]; then
    for r in "$ROOT" "$aserver" "$gw"; do
      [ -n "$r" ] && { git -C "$r" pull --ff-only || { echo "✗ $r pull 실패"; FAIL=1; }; }
    done
  fi
  # ② 심의 워크플로 정본→사본 동기화(이름호출 런타임이 사본을 읽는다)
  bash "$ROOT/infra/scripts/sync-workflows.sh" || { echo "✗ 워크플로 동기화 실패"; FAIL=1; }
  # ③ 프론트(챗·심의 UI) — cae00 은 Drive 산출물(빌드 불가 박스), dev 는 로컬 빌드
  if [ "$BOX" = cae00 ]; then
    bash "$ROOT/infra/scripts/images-from-drive.sh"       || echo "  ⚠ images-from-drive 실패(비치명) — 기존 dist 로 진행"
  else
    ( cd "$ROOT/frontend" && pnpm build ) || { echo "✗ 프론트 빌드 실패"; FAIL=1; }
  fi
  # ④ 재기동 — 포털 백엔드(챗 라우트) → 게이트웨이 → agent-server(소비자 순서 아님에 주의:
  #    게이트웨이가 먼저 떠야 agent-server 바인딩이 도구를 본다)
  apptainer instance stop hwax_portal >/dev/null 2>&1 || true
  bash "$ROOT/infra/scripts/start.sh" >/dev/null || { echo "✗ 포털 재기동 실패"; FAIL=1; }
  if [ -n "$gw" ]; then
    ( cd "$gw" && ./start.sh restart ) || { echo "✗ 게이트웨이 재기동 실패"; FAIL=1; }
  fi
  if [ -n "$aserver" ]; then
    ( cd "$aserver" && ./start.sh -d ) || { echo "✗ agent-server 재기동 실패"; FAIL=1; }
  fi
  sleep 3
  for pp in "8723 /health 포털" "9009 /health agent-server" "9110 /health 게이트웨이"; do
    set -- $pp
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$1$2" 2>/dev/null)" || true
    case "${c:-000}" in
      200) echo "✓ $3 :$1 → 200" ;;
      *)   echo "✗ $3 :$1 → ${c:-000}"; FAIL=1 ;;
    esac
  done
}

do_restart() {
  hr "재시작 전용 — 코드·아티팩트 갱신 없이 서비스만 재기동"
  local APPT="apptainer"
  for c in "$ROOT"/infra/apptainer/bin-*/usr/bin/apptainer; do [ -x "$c" ] && { APPT="$c"; break; }; done
  # ① nginx — 내리고 start.sh(멱등)로 올린다. 안 뜨면 그 자리에서 부검한다.
  "$APPT" instance stop hwax_nginx >/dev/null 2>&1 || true
  "$APPT" instance stop hwax_portal >/dev/null 2>&1 || true
  local SLOG; SLOG="$(mktemp)"
  HWAX_NO_BUILD=1 bash "$ROOT/infra/scripts/start.sh" >"$SLOG" 2>&1 || true
  local port; port="$(sed -n 's/^HTTP_PORT=//p' "$ROOT/infra/.env" 2>/dev/null | tail -1)"
  local c; c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:${port:-8088}/health" 2>/dev/null)" || true
  if [ "${c:-000}" = 200 ]; then
    echo "✓ nginx+포털 :${port:-8088} → 200"
  else
    echo "✗ nginx /health → ${c:-000} — 부검:"
    tail -8 "$SLOG" | sed 's/^/    /'
    # conf 자체 검증(인스턴스 없이 SIF 단발 실행 — 죽은 인스턴스에는 exec 이 안 된다)
    "$APPT" exec --bind "$ROOT:/workspace" "$ROOT/infra/apptainer/nginx.sif"       nginx -c /workspace/infra/nginx/hwax.conf -t 2>&1 | sed 's/^/    conf: /' || true
    # rootless TLS 저포트 — Drive 로 apptainer 바이너리가 갱신되면 setcap 이 벗겨져
    # :443 바인드 실패로 죽는다(grant-net-bind.sh 재실행 필요).
    if grep -q '^ENABLE_TLS=true' "$ROOT/infra/.env" 2>/dev/null; then
      local hp; hp="$(sed -n 's/^HTTPS_PORT=//p' "$ROOT/infra/.env" | tail -1)"
      if [ "${hp:-443}" -lt 1024 ]; then
        echo "    힌트: TLS :${hp:-443} 은 rootless 저포트 — apptainer 바이너리가 갱신됐다면"
        echo "          sudo ./infra/scripts/grant-net-bind.sh ${hp:-443} 를 1회 재실행하라."
        getcap "$APPT" 2>/dev/null | sed 's/^/    cap: /' || true
      fi
    fi
    FAIL=1
  fi
  # ② 게이트웨이·agent-server
  local gw aserver
  gw="$(find_repo HWAXMcpGateway)"; aserver="$(find_repo HWAXAgentServer)"
  [ -n "$gw" ] && { ( cd "$gw" && ./start.sh restart ) || { echo "✗ 게이트웨이 재기동 실패"; FAIL=1; }; }
  [ -n "$aserver" ] && { ( cd "$aserver" && ./start.sh -d ) || { echo "✗ agent-server 재기동 실패"; FAIL=1; }; }
  # ③ DynaForge 스택(갱신 없이 stop/start) + StepForge 인스턴스(리빌드 없이 전환)
  local koor heax
  koor="$(find_repo KooRemapper)"
  [ -n "$koor" ] && ( cd "$koor" && bash platform/infra/scripts/stop.sh 2>/dev/null || true
                      bash platform/infra/scripts/start.sh )     || { echo "✗ DynaForge 재기동 실패"; FAIL=1; }
  heax="$(find_repo HEAXHub)"
  [ -n "$heax" ] && { ( cd "$heax" && bash deploy/apptainer/redeploy-app.sh step_forge )     || { echo "✗ step_forge 재기동 실패"; FAIL=1; }; }
  sleep 3
  for pp in "8723 /health 포털" "9009 /health agent-server" "9110 /health 게이트웨이" "8700 / DynaForge"; do
    set -- $pp
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$1$2" 2>/dev/null)" || true
    case "${c:-000}" in
      000) echo "✗ $3 :$1 → 000"; FAIL=1 ;;
      *)   echo "✓ $3 :$1 → $c" ;;
    esac
  done
}

WANT="${*:-stepforge dynaforge ste chat}"
for t in $WANT; do
  case "$t" in
    stepforge) do_stepforge ;;
    dynaforge) do_dynaforge ;;
    ste)       do_ste ;;
    chat|delib) do_chat ;;
    restart|bounce) do_restart ;;
    *) echo "✗ 모르는 대상: $t (stepforge|dynaforge|ste|chat|restart)"; FAIL=1 ;;
  esac
done

hr "게이트웨이 확인"
curl -s -m 5 http://127.0.0.1:9110/health | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    down = [k for k, v in d['backends'].items() if not v]
    print(f\"도구 {d['tools']}개 · 백엔드 {sum(d['backends'].values())}/{len(d['backends'])}\"
          + (f' · DOWN: {down}' if down else ''))
except Exception:
    print('게이트웨이 응답 해석 실패')" || echo "게이트웨이 무응답"
[ "$FAIL" = 0 ] && echo "완료 — 전 대상 성공" || echo "일부 실패 — 위 ✗ 항목 확인"
exit "$FAIL"
