#!/usr/bin/env bash
# 표적 최신화 — update-all(전체 배포)이 무거울 때, 갱신이 잦은 것만 골라 올린다.
# (이름은 역사적 — forge 2종으로 시작해 ste·chat 이 추가됐다.)
#
#   ./infra/scripts/update-forges.sh                 # 기본: stepforge dynaforge ste chat 전부
#     (기본 실행의 ste 는 **게이트 경유**다 — 다를 때만·Teleport 세션 있을 때만. 전면 갱신은 이름을 댄다)
#   ./infra/scripts/update-forges.sh portal          # ★ 포털만 — 가장 자주 쓰는 부분 갱신
#   ./infra/scripts/update-forges.sh dynaforge       # 경량 표적: stepforge|dynaforge|ste|chat
#   ./infra/scripts/update-forges.sh portal chat     # 여러 개 나열 가능
#   ./infra/scripts/update-forges.sh restart         # 갱신 없이 전 서비스 재시작만(+nginx 부검)
#
# 대상 어휘는 **한 벌**이다. update-all(§2) 이 소유한 서비스
# (portal·mxwp·heax·aidh·signalforge·kooremapper)도 여기서 이름을 대면 되고, 그때는 흉내내지 않고
# `deploy-all-from-drive.sh <이름>` 에 **위임**한다 — 지문 기반 재기동 생략·영구 캐시·`set_remote`
# 까지 정본 하나로 돈다. 예전에는 이 스크립트가 dynaforge 절을 손으로 베낀 축약판이어서 뒤처졌다.
# `dynaforge` 는 `kooremapper` 의 별칭으로 남긴다(기존 문서·습관 보호).
#
# ⚠ **dev 에서는 위임하지 않는다.** deploy-all 의 `git_update` 가 `git stash push -u` +
#   `git reset --hard origin/<branch>` 를 해서 그 리포의 WIP 를 날린다. dev 에 로컬 경로가 있는 것은
#   `portal`(프런트 빌드+재기동)과 `dynaforge`(이중 빌드+재기동)뿐이고, 나머지는 그 사실을 말하고
#   건너뛴다(조용히 넘기지 않는다).
#
# 포함하지 않는 것 — AIDataHub 데이터 병합(update-all §3 의 몫).
#
# 박스 자동 감지 — 리포 루트가 */Projects/* 면 cae00(운영: git pull + Drive 반입),
# 아니면 dev(로컬 소스 그대로 — 타 세션 WIP 를 pull/reset 으로 건드리지 않는다).
#
# 무엇을 하나.
#   stepforge : HEAXHub redeploy-app.sh step_forge --rebuild
#               (--rebuild 가 upstream git fetch→SIF 빌드→재기동까지. 게이트웨이는
#                지문 감지가 60초 내 자동 재집계 — 재기동 불필요)
#   dynaforge : [cae00] **update-all 의 kooremapper 절에 위임**
#                       (`deploy-all-from-drive.sh kooremapper`) — clone·git_update·
#                       `platform/.env` 부트스트랩·`set_remote`·Drive 반입·지문 기반 재기동·
#                       autostart·프로브까지 정본 하나로 돈다. 예전에는 이 함수가 그것을 손으로
#                       베낀 축약판이어서 뒤처졌다(루트 프로브·`set_remote` 누락·지문 없음).
#               [dev]   build-frontend.sh → stop/start → install-autostart (⚠ plain 'pnpm build'
#                       는 포털용 index.portal.html 을 안 만들어 포털 경유가 깨진다 — 실사고)
#                       ⚠ dev 는 **위임하지 않는다** — `git_update` 가 `git stash push -u` +
#                         `git reset --hard origin/<branch>` 를 해서 타 세션 WIP 를 날린다.
#                       프로브는 `:8700/api/health` · `:8701/mcp` 다(루트가 아니다 — 루트는 SPA 라
#                       백엔드가 고장나도 200 이고 MCP 루트는 404 다). 끝에 **무엇이 올라갔는지**
#                       (revision·published·gmsh) 찍는다 — "재기동했다" 는 근거가 아니다.
#               ⚠ `start.sh` 가 postgres → alembic upgrade head → api 순서라 스키마가 API 보다
#                 먼저 선다. 반입만 하고 `start.sh` 를 부르는 **수동** 경로는 살아 있는 api 를
#                 건너뛰므로 `dist-from-drive.sh --restart` 를 써야 한다.
set -uo pipefail
# 로컬 헬스체크(127.0.0.1)는 사내망 프록시를 타면 안 된다 — 프록시가 로컬에 못 닿아 curl 000
# 이 나고 서비스를 죽은 것으로 오판한다(실사고). 바깥용 http_proxy 는 그대로 두고 로컬만 우회.
# 두 철자(NO_PROXY·no_proxy)를 **합쳐** 같은 값으로 둔다 — 순서를 지키고 이미 있는 항목은 다시 붙이지 않는다. 종전엔 대문자만 읽어
# 소문자를 그 값으로 덮었다 — 소문자만 둔 박스에서는 운영자의 우회 목록이 이 실행 내내(이 실행이 띄운 서비스까지) 사라졌고,
# 이 머리를 지날 때마다(update-all 은 바깥 bash → 본문 → §1 재실행 → deploy-all 로 여러 번 지난다) 루프백 셋이 앞에 또 붙었다.
# read -a 로 쪼갠다 — 따옴표 없는 for 는 `*`(전부 우회)를 현재 디렉터리의 파일 이름으로 푼다. 같은 블록이 update-all ·
# deploy-all-from-drive · update-forges 머리에 있다(리포 위치를 알기 전이라 lib 를 소싱하지 않는다) — 고치면 셋 다 고친다.
_np=""; IFS=', ' read -ra _np_parts <<<"127.0.0.1,localhost,::1,${NO_PROXY:-},${no_proxy:-}"
for _h in ${_np_parts[@]+"${_np_parts[@]}"}; do
  [ -n "$_h" ] || continue
  case ",$_np," in *",$_h,"*) ;; *) _np="${_np:+$_np,}$_h" ;; esac
done
export NO_PROXY="$_np"; export no_proxy="$_np"; unset _np _np_parts _h
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
find_repo() { for c in "$PARENT/$1" "$HOME/Projects/$1" "$HOME/claude/$1"; do [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
case "$ROOT" in */Projects/*) BOX=cae00 ;; *) BOX=dev ;; esac
hr() { printf '\n\033[1;36m── %s ─────────────────────\033[0m\n' "$*"; }
FAIL=0
# agent-server 재기동 — 그쪽 start.sh 는 도는·줄 선 심의가 있으면 떠 있는 인스턴스를 내리지 않고 **3 으로 나간다**(몇 시간 돈 패널을
# 재기동 한 번이 말없이 지우지 않게. 사유와 강행법 AGENT_RESTART_FORCE=1 은 그 스크립트가 찍는다). 3 을 실패로 세면 그 '○ 재기동
# 건너뜀' 바로 아래에 '✗ 재기동 실패' 가 찍히고 실행 전체가 실패로 끝난다 — 건너뛴 것은 건너뛴 것으로 말한다.
restart_agent() {  # $1 = HWAXAgentServer 리포
  local rc=0
  ( cd "$1" && ./start.sh -d ) || rc=$?
  case "$rc" in
    0) ;;
    3) echo "○ agent-server 는 그대로 둔다 — 도는·줄 선 심의가 있다(위 줄). 새 코드·설정은 그 심의가 끝난 뒤 다시 돌려야 반영된다" ;;
    *) echo "✗ agent-server 재기동 실패"; FAIL=1 ;;
  esac
}

# update-all(§2) 이 **소유한** 서비스 — 여기서는 위임만 한다. 베끼면 갈라지고, 갈라진 쪽이
# 하필 초록을 찍는다(노트: dynaforge 축약판이 `set_remote` 누락·루트 프로브로 뒤처져 있었다).
DELEGATED="portal mxwp heax aidh signalforge kooremapper"

do_delegate() {   # $1 = deploy-all 대상 이름
  local tgt="$1"
  hr "$tgt — update-all(§2) 의 해당 절에 위임"
  # ⚠ **dev 에서는 위임하지 않는다.** `git_update` 가 기본으로 `git stash push -u` +
  #   `git reset --hard origin/<branch>` 를 한다(`NO_GIT_RESET=1` 이 escape hatch) — 그 리포에
  #   타 세션 WIP 가 있으면 날아가고 공용 stash 스택까지 건드린다. 조용히 넘기지 않고 말한다.
  if [ "$BOX" != cae00 ]; then
    echo "· dev 에서는 $tgt 위임을 하지 않는다 — deploy-all 의 git_update 가 reset --hard 를 한다."
    echo "  cae00 에서 하거나, 정말 원하면: NO_GIT_RESET=1 bash infra/scripts/deploy-all-from-drive.sh $tgt"
    return 0
  fi
  if bash "$ROOT/infra/scripts/deploy-all-from-drive.sh" "$tgt"; then
    echo "✓ $tgt 갱신 완료"
  else
    echo "✗ $tgt 갱신 실패 — 위 ✗/skip 항목 확인"; FAIL=1
  fi
}

do_portal_dev() {
  hr "포털 — dev 모드(프런트 빌드 + 재기동)"
  # do_chat 의 포털 부분과 같은 동작이다 — 새 동작을 발명하지 않는다.
  ( cd "$ROOT/frontend" && pnpm build ) || { echo "✗ 프론트 빌드 실패"; FAIL=1; return; }
  apptainer instance stop hwax_portal >/dev/null 2>&1 || true
  bash "$ROOT/infra/scripts/start.sh" >/dev/null || { echo "✗ 포털 재기동 실패"; FAIL=1; return; }
  sleep 3
  local hp; hp="$(sed -n 's/^HTTP_PORT=//p' "$ROOT/infra/.env" 2>/dev/null | tail -1)"
  for pp in "8723 /health 포털" "${hp:-8088} /health nginx"; do
    set -- $pp
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$1$2" 2>/dev/null)" || true
    case "${c:-000}" in
      200) echo "✓ $3 :$1 → 200" ;;
      *)   echo "✗ $3 :$1 → ${c:-000}"; FAIL=1 ;;
    esac
  done
}

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
  if [ "$BOX" = cae00 ]; then
    # ⚠ **흉내내지 않고 위임한다.** update-all(§2) 의 `if want kooremapper` 절이 정본이고, 이
    #   함수는 그것을 손으로 베낀 축약판이었다 — 그래서 실제로 뒤처졌다. 베낀 쪽에 없던 것:
    #   리포 없으면 clone · `platform/.env` 부트스트랩 · `set_remote KOORM_DRIVE_REMOTE` ·
    #   **지문 기반 재기동**(안 바뀌면 내리지 않는다) · 반입 실패를 `mark_stale` 로 판정에 남기기.
    #   프로브도 루트(`:8700/`·`:8701/`)를 봐서 '떠 있지만 고장난' 상태가 합격했다.
    #   `deploy-all-from-drive.sh` 는 대상 선택(`want`)을 지원하므로 kooremapper 만 고른다 —
    #   이제 update-all 에서 설정한 것이 여기서도 **같게** 돈다(두 벌이 갈릴 자리가 없다).
    if bash "$ROOT/infra/scripts/deploy-all-from-drive.sh" kooremapper; then
      echo "✓ DynaForge — update-all 의 kooremapper 절을 그대로 돌렸다"
    else
      echo "✗ DynaForge 갱신 실패 — 위 ✗/skip 항목 확인"; FAIL=1
    fi
    return
  fi
  # ── dev — 위임하지 않는다 ────────────────────────────────────────────────────
  # `git_update` 가 기본으로 `git stash push -u` + `git reset --hard origin/<branch>` 를 한다
  # (`NO_GIT_RESET=1` 이 escape hatch). dev 는 타 세션 WIP 가 있는 작업 트리이고 stash 스택도
  # 공용이라, 그것을 여기서 걸면 안 된다. 그래서 dev 는 프론트만 정식 이중 빌드로 갱신한다.
  local koor; koor="$(find_repo KooRemapper)"
  [ -n "$koor" ] || { echo "✗ KooRemapper 리포 없음"; FAIL=1; return; }
  ( cd "$koor"
    # ⚠ plain 'pnpm build' 는 포털용 index.portal.html 을 안 만들어 포털 경유가 깨진다 — 실사고.
    bash platform/infra/scripts/build-frontend.sh
    bash platform/infra/scripts/stop.sh 2>/dev/null || true
    bash platform/infra/scripts/start.sh
    bash platform/infra/scripts/install-autostart.sh || echo "  ⚠ autostart 설치 실패(비치명)"
  ) || { FAIL=1; return; }
  # 업스트림 생존 — rc 가 아니라 출력값으로 판정한다(000 폴백 덧붙임 함정, deploy-all 주석 참조).
  #
  # ⚠ **루트를 보지 않는다.** 예전엔 `:8700/` 과 `:8701/` 을 보고 000 만 아니면 통과했는데 둘 다
  #    틀렸다 — `:8700/` 은 SPA 라 백엔드가 고장나도 200 을 주므로 "떠 있지만 고장난" 상태가
  #    합격하고, `:8701/` 은 MCP 루트라 404 여서 매 회 죽은 것처럼 보였다.
  #    `deploy-all-from-drive.sh:402` 이 이미 쓰는 짝(`/api/health` · `/mcp`)을 그대로 쓴다.
  for pp in "8700 /api/health" "8701 /mcp"; do
    set -- $pp
    c="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$1$2" 2>/dev/null)" || true
    case "${c:-000}" in
      200|302|401|405|406) echo "✓ :$1$2 → $c" ;;
      *) echo "✗ :$1$2 → ${c:-000} — /apps/kooremapper* 가 깨진다"; FAIL=1 ;;
    esac
  done
  # **무엇이 올라갔는지** 말한다. "재기동했다" 는 근거가 아니다 — 이 빌드가 돈다는 것이 근거다.
  curl -s -m 5 "http://127.0.0.1:8700/api/health" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin).get('data', {})
except Exception:
    sys.exit(0)
print('    revision %s · published %s · gmsh %s' % (
    (d.get('revision') or '?')[:12], d.get('published_utc'), (d.get('gmsh') or {}).get('version')))
if d.get('revision_matches_binary') is False:
    print('    ⚠ BUILD_INFO 와 실제 바이너리가 어긋난다 — revision 을 믿을 수 없다(반입이 반쪽이다).')
" || true
}

do_ste() {
  hr "STE(SmartTwinExplorer) — $BOX 모드"
  # ⚠ **박스로 가르지 않는다.** 여기서 "dev 스킵 — deploy-ste 는 cae00 전용" 으로 막아 뒀는데
  #   그게 틀렸다. 가르는 축은 박스가 아니라 **전송 방식**(ste 리포 deploy/transport.env)이다 —
  #   dev 의 ste 는 같은 박스 위 libvirt VM(ste-head01)이라 ssh 로 직접 닿고 배포도 된다.
  #   Drive·Teleport 가 필요한 것은 에어갭 운영 클러스터뿐이다. 박스로 막아 둔 탓에 dev 의 ste 가
  #   낡은 채로 남아 포털→ste 자격 중계가 조용히 죽어 있었다(2026-09-23, docs/one-token D-13).
  #   deploy-ste.sh 가 transport.env 를 읽어 스스로 경로를 고르므로 그대로 넘긴다.
  #
  # **이름을 댔는가**로 가른다(2026-09-26 문서 감사에서 잡혔다).
  #   · `update-forges.sh ste` — 사람이 ste 를 콕 집었다. `--if-stale` 없이 간다: 지문이 같아도
  #     유닛·venv·시크릿까지 다시 맞춘다(deploy-ste.sh 는 인자 없으면 게이트도 안 본다).
  #   · 인자 없는 기본 실행 — ste 는 "경량 표적 갱신" 에 **딸려 온 것**이다. 그런데 에어갭(teleport)
  #     박스에서 그 길은 Drive 왕복 + 헤드 재배포·재기동이라 "수 분" 이 아니고, 돌던 잡을 끊는다.
  #     그래서 `--if-stale` 을 줘 공용 게이트(사람 호출 ∧ 신선도 ∧ Teleport 세션)를 통과할 때만 간다.
  #     dev(direct)는 지문 대조라 다를 때만 배포되고 — ste 를 기본 대상에 넣은 이유(낡은 채 방치되어
  #     자격 중계가 조용히 죽던 2026-09-23 사고)는 그대로 지켜진다.
  local _stale=""
  [ "${STE_NAMED:-0}" = 1 ] || _stale="--if-stale"
  if bash "$ROOT/infra/scripts/deploy-ste.sh" $_stale; then
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
    restart_agent "$aserver"
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
  [ -n "$aserver" ] && restart_agent "$aserver"
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
# ste 를 **이름으로** 댔는지 기억한다 — do_ste 가 전면 갱신(이름 댐)과 게이트 경유(딸려 옴)를 가른다.
STE_NAMED=0
for _a in "$@"; do case "$_a" in ste) STE_NAMED=1 ;; esac; done
export STE_NAMED
for t in $WANT; do
  case "$t" in
    stepforge) do_stepforge ;;
    dynaforge|kooremapper) do_dynaforge ;;
    # 포털은 자주 이것만 올린다 — cae00 은 정본에 위임, dev 는 빌드+재기동.
    portal)    if [ "$BOX" = cae00 ]; then do_delegate portal; else do_portal_dev; fi ;;
    mxwp|heax|aidh|signalforge) do_delegate "$t" ;;
    ste)       do_ste ;;
    chat|delib) do_chat ;;
    restart|bounce) do_restart ;;
    *) echo "✗ 모르는 대상: $t"
       echo "   경량 표적 : stepforge | dynaforge(=kooremapper) | ste | chat | restart"
       echo "   정본 위임 : $DELEGATED"
       FAIL=1 ;;
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
