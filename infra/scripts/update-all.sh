#!/usr/bin/env bash
# cae00 원커맨드 최신화 — 코드+아티팩트+데이터+챗스택+게이트웨이 config 정합+헬스게이트를 한 번에.
#
#   ./infra/scripts/update-all.sh                # 전부 (표준 운영 최신화)
#   SF_RESTORE_DB=1 ./infra/scripts/update-all.sh   # SignalForge DB를 Drive 최신 덤프로 시드/갱신
#   NO_GIT_RESET=1  ./infra/scripts/update-all.sh   # 로컬 수정 보존(soft pull) 모드
#
# 순서:
#   1) 포털 레포 자체 최신화(이 스크립트가 최신이 되도록) → 새 버전으로 1회 재실행
#   2) deploy-all-from-drive.sh  — portal·mxwp·heax·signalforge·aidh·kooremapper (코드+Drive 아티팩트+기동+nginx)
#   3) AIDataHub 데이터 동기화   — dev가 원본. 단 Drive 덤프가 지난 복원분과 같으면 복원 생략
#   4) update-sites.sh 챗 스택   — mcp-gateway·agent-server·signalforge-mcp 만(2에서 처리된 것 재기동 금지)
#   5) 게이트웨이 config 정합    — /health backends + config의 heax_registry를 기대 목록과 비교,
#                                  빠졌으면 provision-config.sh --force 재생성(토큰은 provision.env) 후
#                                  재기동 + 재검증(agent 토큰 정합 확인 포함)
#   6) 헬스게이트                — 핵심 체인(portal→agent→gateway) 실패 시 exit 1로 크게 알림
#
# 1회 준비물(재프로비저닝용 토큰, 없으면 해당 백엔드만 빠짐):
#   ~/Projects/HWAXMcpGateway/provision.env  (chmod 600, gitignore)
#     RAT_TOKEN=rat_xxx            # ReportArchive PAT (심의 보고서 저장)
#     HEAX_MCP_TOKEN=heax_xxx      # heax MCP 앱 자동연동(materialtwin·laminate)
#     ODB_HUB_TOKEN=xxxx           # ODB 자동화 허브(<ODB 서버>:8000) — cae00 에서만 도달
#     ARP_BASE=http://<ARP 서버>:3001  # AI Ready Portal — cae00 에서만 도달. infra/.env ARP_HOST 가 있으면 1f 가 채운다
#     ARP_TOKEN=xxxx                   # ARP MCP 서비스 토큰(2026-10-01 부터 인증) — 없으면 arp 백엔드만 빠진다
#     SMARTTWIN_MCP_URL=http://127.0.0.1:5013/mcp   # SmartTwinMCP 를 쓰는 박스만(dev) — 없으면 게이트웨이가 smart-twin-mcp 를 등재하지 않는다
#     PER_USER_SSO_APPS="<per_user 키>:<ENV 접두> …" # 여섯 번째 앱부터의 사람별 위임 — <접두>_SSO_SECRET · <접두>_SSO_URL 과 함께 적는다
set -uo pipefail   # -e 없음: 서비스 하나의 실패가 전체를 끊지 않게, 마지막 게이트에서 판정
# 로컬 헬스체크(127.0.0.1)는 사내망 프록시를 타면 안 된다 — 프록시가 로컬에 못 닿아 curl 000
# 이 나고 서비스를 죽은 것으로 오판한다. 바깥용 http_proxy(git·rclone)는 그대로 두고 로컬만 우회.
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

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do
                [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
GW_DIR="$(find_repo HWAXMcpGateway)"
AGENT_DIR="$(find_repo HWAXAgentServer)"
AIDH_DIR="$(find_repo AIDataHub)"
HEAX_DIR="$(find_repo HEAXHub)"   # §5 의 앱 단위 재배포에 필요 — 경로 하드코딩 금지
KNOX_DIR="$(find_repo HWAXKnoxBridge)"   # Knox 브리지(사내 사이드카) — 있는 박스에서만 §5 가 knox-bridge 백엔드를 기대한다
SVC="$SELF_REPO/infra/scripts/services.sh"
# 포털 라우팅 표. §6 의 ste 프로브가 $REPO_ROOT/$ROUTES_PATH 를 참조했는데 이 스크립트는
# _common.sh 를 source 하지도, infra/.env 를 읽지도 않아 둘 다 미정의였다 — set -u 라 그
# 명령치환만 죽고 STE_UP 이 빈 값이 돼, routes.env 에 ste 가 멀쩡히 있는데도 매번
# '라우트 미설정 — 건너뜀' 만 찍혔다(실측). ROUTES_PATH 는 infra/.env 의 설정 항목이므로
# 하드코딩하지 말고 거기서 읽는다(_common.sh 와 같은 기본값 config/routes.env).
_routes_path="$(sed -n 's/^ROUTES_PATH=//p' "$SELF_REPO/infra/.env" 2>/dev/null | tail -1 | tr -d '"'"'"' ')"
ROUTES_ENV="${ROUTES_ENV:-$SELF_REPO/backend/${_routes_path:-config/routes.env}}"
# § 머리 — 0b 본문이 kill(TERM·HUP) 또는 삼켜진 Ctrl-C 를 받으면 여기서 멈춘다(진행 중인 §는 끝낸다). 단순 명령 경계에서 죽으면 down→up 같은
# 짝이 반으로 갈린다. 플래그는 **환경변수**다 — §1 의 exec 재실행이 셸 변수를 버려 §1 중 받은 kill 이 사라졔다(4라운드 검토).
# 멈출 때 지금까지의 ✗ 와 ○ 요약을 내고 장부 파일을 지운다 — 안 그러면 '어디까지 했는지' 가 없이 끝난다.
hr() { if [ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ]; then
         # 정지 요약은 완주 요약과 같은 stdout 으로 — stderr 로 내면 `> log` 로 남긴 로그에 ○ 요약만 있어 완주처럼 보인다(5라운드).
         echo "  · 종료 요청을 받아 여기서 멈춘다 — 앞 §는 끝냈다(직전 머리: '${HWAX_UPDATE_ALL_LAST_HR:-없음}'). '$*' 머리에서 멈췄다(0b)"
         [ -n "${FAIL_ITEMS:-}" ] && printf '  지금까지의 ✗:\n%s' "$FAIL_ITEMS"
         command -v hwax_skip_summary >/dev/null 2>&1 && hwax_skip_summary
         rm -f "${HWAX_SKIP_LEDGER:-}" 2>/dev/null; exit 143; fi
       export HWAX_UPDATE_ALL_LAST_HR="$*"      # §1 exec 재실행을 넘어가야 하니 환경변수
       printf '\n\033[1;36m══ %s ══════════════════════════════════════\033[0m\n' "$*"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
# ⚠ **치명과 비치명을 눈으로 가른다.** 종전엔 둘 다 빨간 ✗ 라, 이 박스 대상도 아닌 서비스나
# '비치명' 이라고 적힌 항목까지 실패처럼 보였다(2026-09-20 cae00: ✗ 넷 중 종료코드를 세운 것은
# 하나도 없었는데 사람은 전부 고장으로 읽었다). 색이 판정과 어긋나면 사람은 로그를 안 믿게 된다.
# 경고도 끝에서 한 번 더 센다(WARN_ITEMS) — 종료코드는 그대로다. 수백 줄 사이 ⚠ 한 줄은 지나친다: cae00 이 상시 경고 둘에
# 섞여 vLLM 정지를 같은 출력에서 놓쳤다(2026-10-01, 5차 요청 §5).
bad()  { printf '  \033[1;33m⚠\033[0m %s\n' "$*"; WARN_ITEMS="${WARN_ITEMS:-}  · $1"$'\n'; }
# bad 는 경고라 종료코드에 영향이 없다 — 앱이 깨져도 update-all 이 초록으로 끝나던 원인이다.
# 배포 실패로 계상해야 하는 것은 fail 로 낸다(§6 헬스게이트의 FAIL 을 세우고, 끝에서 모아 보여 준다).
fail() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; FAIL=1; FAIL_ITEMS="${FAIL_ITEMS:-}  · $1"$'\n'; }
app_bad() { local c="$1"; shift; if [ "$c" = 1 ]; then fail "$@"; else bad "$@"; fi; }
# ○ "있는데 안 켠 기능" 장부 — 옵션·설정이 없어 건너뛴 단계는 즉시 한 줄 + 마지막 요약에 전부 다시 낸다.
#   실패(✗)·경고(⚠)와 다른 표식이다. 자식 스크립트(deploy-ste·게이트 lib·env-sync)도 같은 파일에 적는다.
. "$SELF_REPO/infra/scripts/lib/skip-ledger.sh"
HWAX_SKIP_LEDGER="$(mktemp)"; export HWAX_SKIP_LEDGER
# 도는·줄 선 심의가 있으면 에이전트 서버를 재기동하지 않는다(§4 는 update-sites 가, §5 는 재프로비저닝 앞에서 묻는다).
. "$SELF_REPO/infra/scripts/lib/delib-busy.sh"

# HTTP 코드 프로브 — curl은 실패해도 -w로 '000'을 찍으므로 종료코드가 아니라 출력값으로만 판정한다.
http_code() { curl -sk -m "${2:-4}" -o /dev/null -w '%{http_code}' "$1" 2>/dev/null; }
# 상한(timeout --foreground)에 걸려 죽은 단계가 남긴 자식들을 정리한다 — --foreground 는 명령 하나에만 TERM 을 주고 그 자식(rsync·ssh)은
# 두므로, 그대로면 본문은 '중단했다' 고 찍고 잠금을 푼 뒤 재실행이 살아 있는 전송과 겹친다(4라운드). 단계를 띄울 때 HWAX_STEP_ID=<표식> 을
# 환경에 실어 두고, 여기서 그 표식을 가진 살아 있는 프로세스를 /proc/*/environ 으로 찾아 TERM → 3초 → KILL 한다. 같은 사용자만 보인다.
_reap_step() {  # $1=표식
  local _pids
  _pids="$(grep -lsz "HWAX_STEP_ID=$1" /proc/[0-9]*/environ 2>/dev/null | cut -d/ -f3 | grep -vx "$$" | tr '\n' ' ')"
  [ -n "${_pids// /}" ] || return 0
  echo "  · 상한에 걸린 단계가 남긴 프로세스를 정리한다: $_pids" >&2
  kill -TERM $_pids 2>/dev/null; sleep 3; kill -KILL $_pids 2>/dev/null; return 0
}

# ── 0a) 인자 — `--with-<name>` 는 무거운·외부 배포 단계를 **이번 실행에 한해** 강제한다 ───────
# 첫 사용처는 ste(`--with-ste`: 에어갭 클러스터 코드 갱신). 규칙은 infra/scripts/lib/deploy-gate.sh 에
# 있고 각 단계는 이름만 등록한다 — 새 옵션이 생겨도 여기와 그 단계 한 줄이면 끝난다(docs/ste-cae00 D-13).
HWAX_WITH="${HWAX_WITH:-}"
for _a in "$@"; do
  case "$_a" in
    --with-*) HWAX_WITH="${HWAX_WITH:+$HWAX_WITH }${_a#--with-}" ;;
  esac
done
export HWAX_WITH
# ── 0b) 잠금 — update-all 두 개가 겹치면 2c 배포 중 재기동·§5 provision --force·게이트웨이 down/up 이
#   동시에 돈다(2026-09-24 적대 검토). 같은 리포 루트 기준 한 개만 돈다. 기다리지 않고 바로 알린다.
#   설계(2026-09-27 cae00 실측 + 적대 검토 세 라운드 — docs/ste-cae00 D-23·D-24·D-25):
#   · 잠금은 **이 바깥 bash 가 fd 9 로** 쥐고, 본문은 같은 스크립트를 자식으로 돈다. 자식에겐 `9>&-` 로 fd 를 닫아 넘겨 본문이
#     띄운 데몬(에이전트서버 nohup·apptainer instance)이 물려받지 못한다 — 종전 한 프로세스 모양(exec 9>lock)에선 데몬이 fd 9 를
#     쥐어 update-all 이 끝난 뒤에도 모든 실행이 "이미 돌고 있다" 였다. 바깥은 자식이 끝날 때까지 기다린다 → 잠금 수명 = 본문 수명.
#     flock(1) 을 부모로 쓰면 Ctrl-C 에 flock 만 죽어 "실행은 계속·잠금은 해제" 가 된다(검토).
#   · 신호: Ctrl-C(그룹 INT)는 본문·단계에 직접 가므로 바깥은 살아서 잠금만 쥔다(넘기면 두 번 받은 자식 bash 가 죽는다). 자식이 INT 로
#     죽었으면 바깥도 INT 로 죽어 부른 쪽의 `;` 체인이 끊긴다(관례). `kill <pid>`(TERM·HUP)는 자식에게 넘기고, **자식은 진행 중인
#     단계가 끝난 뒤 멈춘다**(bash 는 전경 명령 중 trap 을 미룬다) — 즉시 죽이면 그 단계(deploy-all·provision --force)가 고아로 끝까지
#     돌고 잠금은 먼저 풀려 재실행이 겹친다(2라운드 검토). 즉시 멈추려면 Ctrl-C.
#   · 옛 판이 물려준 fd 를 쥔 **데몬만** 잠금을 쥐고 있으면 잠금 파일을 새로 만들어 비켜 간다(그 데몬은 지워진 inode 를 쥔 채 무해).
#     옛 판의 하위 단계(deploy-all 등, fd 9 를 물려받은 채 도는 스크립트)는 데몬이 아니라 '진짜' 다 — 이름으로 가른다. 획득 단계
#     (열기→시도→스캔→치유→재시도)는 치유 잠금 아래 하나씩(둘이 동시에 치유하면 서로의 새 파일을 지우고 둘 다 진행, 10ms 창).
#     보유자가 안 보이면(다른 사용자) 한 번 더 시도한 뒤 거부한다 — 지우지 않는다.
#   · 전환: 옛 판(exec 9>lock)이 §1 에서 이 판으로 exec 재실행한 첫 회는 같은 PID 가 옛 fd 를 쥔다(닫고 다시 잡는다). 09-27 중간 판
#     (flock -o 부모)에서 온 첫 회는 부모 flock 이 잠금을 쥔 채 이 코드가 본문이 된 것이다(부모 comm=flock 이면 본문으로 간다).
#   · 가드 값은 `<잠금경로>:<바깥 PID>` — 자식은 PPID 로 대조하므로 데몬으로 새어 나간 변수로는 잠금을 건너뛰지 못한다.
#   · 잠금 경로는 TMPDIR 에 매달지 않는다(TMPDIR 이 다른 두 셸이 서로를 못 본다) — HWAX_LOCK_DIR(시험용) 아니면 /tmp.
_LOCK_DIR="${HWAX_LOCK_DIR:-/tmp}"; _LOCK_ID="$(printf '%s' "$SELF_REPO" | md5sum | cut -c1-8)"
_LOCK="$_LOCK_DIR/hwax-update-all.$_LOCK_ID.lock"
_HEAL="$_LOCK_DIR/.hwax-update-all-heal.$_LOCK_ID"     # 획득 직렬화용 — 지우지 않는다(`hwax-update-all.*` 글롭에 안 걸리게 숨김)
_lock_is_body() {  # 이 판의 자식(PPID 대조) · 중간 판(flock -o 부모)의 본문이 §1 로 이 판이 된 첫 회
  [ "${HWAX_UPDATE_ALL_LOCKED:-}" = "$_LOCK:$PPID" ] && return 0
  [ "${HWAX_UPDATE_ALL_LOCKED:-}" = "$_LOCK" ] && [ "$(cat "/proc/$PPID/comm" 2>/dev/null)" = flock ] && return 0
  return 1
}
_body_stop_traps() {  # 본문(자식)의 정지 규율 — 잠금이 있는 갈래와 flock 없는 갈래가 같이 쓴다(5라운드: 후자엔 하나도 없었다)
  # 플래그는 환경변수 — §1 의 exec 재실행을 넘어가야 한다(셸 변수는 버려진다). '내 재실행' 판정은 PID 로(exec 는 PID 를 지킨다) —
  # UPDATE_ALL_REEXEC=1 만 보면 그 값을 물려받은 데몬 후손에서 띄운 다른 update-all 이 STOP=1 을 쥔 채 첫 hr 에서 죽는다(5라운드).
  [ "${HWAX_UPDATE_ALL_REEXEC_PID:-}" = "$$" ] || export HWAX_UPDATE_ALL_STOP=0
  trap 'echo "  · 종료 요청(TERM) 을 받아 두었다 — 진행 중인 §가 끝나면 멈춘다. 즉시 멈추려면 Ctrl-C" >&2; export HWAX_UPDATE_ALL_STOP=1' TERM
  trap 'echo "  · 종료 요청(HUP) 을 받아 두었다 — 진행 중인 §가 끝나면 멈춘다" >&2; export HWAX_UPDATE_ALL_STOP=1' HUP
  # Ctrl-C: 전경 단계가 INT 로 죽었으면($? = 130) 종전처럼 바로 죽는다. 단계가 INT 를 삼키고 정상 종료했으면(rsync rc 20·rclone) 종전엔
  # 아무 표시 없이 다음 §로 이어졌다(4라운드) — 이제 받아 두고 다음 § 머리에서 멈춘다. 두 번 눌러도 빨라지지 않는다 — bash 는 전경 단계가
  # 끝나기 전엔 trap 을 미루고 신호는 쌓이지 않는다(실측). 삼키는 단계를 지금 끊으려면 그 단계 프로세스에 kill 을.
  trap 'if [ $? = 130 ]; then exit 130; fi; echo "  · Ctrl-C — 단계가 신호를 삼켰거나 명령 사이였다. 진행 중인 §가 끝나면 멈춘다" >&2; export HWAX_UPDATE_ALL_STOP=1' INT
}
if _lock_is_body; then
  _body_stop_traps
elif ! command -v flock >/dev/null 2>&1; then
  echo "  ⚠ flock(util-linux) 이 없어 단일 실행 잠금 없이 진행한다 — 겹쳐 돌리지 마라(kill 은 § 머리에서, Ctrl-C 는 즉시 — 잠금만 없다)" >&2
  _body_stop_traps
else
  _lk="$(readlink -f "$_LOCK" 2>/dev/null | sed 's/[][*?\\]/\\&/g')"   # find -lname 은 글롭이다 — 경로의 특수문자를 이스케이프
  for _fd in $(find "/proc/$$/fd" -maxdepth 1 -lname "$_lk" -printf '%f\n' 2>/dev/null); do eval "exec $_fd>&-"; done
  # 진짜 = update-all 자신·flock 부모·update-all 이 전경으로 돌리는 하위 단계(옛 판에선 fd 9 를 물려받은 채 돈다). 그 외는 고아(데몬).
  # 하위 단계는 deploy-all 이 **상대경로**로 부른다(`bash deploy/apptainer/start.sh`·`./scripts/up.sh`·`./boot.sh`) — 앞 슬래시를 요구하면 못 잡는다(3라운드).
  # 패턴은 case 에 **직접** 쓴다 — 변수에 담으면 `|` 가 대안이 아니라 글자가 되어 아무것도 안 맞는다(실측: 진짜 보유자를 전부 고아로 봤다).
  _lock_holders() {  # 잠금 파일을 연 프로세스(자기 제외) → _real / _stale. pid·comm 만 적는다(남의 인자는 토큰일 수 있다)
    _real=""; _stale=""
    # 스캔 파이프는 fd 8·9 를 닫고 돈다 — 안 닫으면 find·cut·sort 자신이 잠금 파일을 연 프로세스로 잡힌다(실측)
    for _p in $(exec 8>&- 9>&-; find /proc/[0-9]*/fd -maxdepth 1 -lname "$_lk" -printf '%h\n' 2>/dev/null | cut -d/ -f3 | sort -u); do
      [ "$_p" = "$$" ] && continue
      _comm="$(cat "/proc/$_p/comm" 2>/dev/null)"; [ -n "$_comm" ] || continue     # 스캔 중 사라진 프로세스
      case "$_comm $(tr '\0' ' ' < "/proc/$_p/cmdline" 2>/dev/null | cut -c1-300)" in
        flock*|*update-all*|*infra/scripts/*|*deploy-all-from-drive*|*provision-config*|*deploy/*.sh*|*-from-drive*|*data-migrate*|*scripts/up.sh*|*scripts/down.sh*|*boot.sh*) _real="$_real $_p" ;;
        *) _stale="$_stale $_p($_comm)" ;;
      esac
    done
  }
  _lock_bye() { echo "$1" >&2; rm -f "$HWAX_SKIP_LEDGER" 2>/dev/null; exit 3; }
  _lock_owner() { stat -c '%U' "$1" 2>/dev/null || echo '?'; }
  # 같은 리포를 sudo 로 한 번 돌리면 root 소유 파일이 남아 그 뒤 모든 실행이 여기서 막힌다(sticky /tmp 라 지우지도 못한다 — 4라운드).
  _lock_open_fail() {  # $1=파일 — 파일이 있으면 소유자(남의 것이면 **돌고 있는지 먼저**), 없으면 디렉터리 문제(5라운드: 없는 파일을 지우라 했다)
    if [ -e "$1" ]; then
      echo "✗ 잠금 파일을 열 수 없다 — $1(소유자 $(_lock_owner "$1"), 나는 $(id -un)). 먼저 'ps -ef | grep update-all' 로 그 사용자의 update-all 이 도는지 본다 — 돌면 기다린다. 끝난 흔적(sudo 로 한 번 돌림)이면: sudo rm -f $_HEAL $_LOCK 뒤 재실행"
    else
      echo "✗ 잠금 파일을 만들 수 없다 — $_LOCK_DIR 에 쓸 수 없다(없음·읽기전용·가득). 디렉터리를 보라(HWAX_LOCK_DIR 로 다른 곳을 줄 수 있다)"
    fi
  }
  exec 8>"$_HEAL" || _lock_bye "$(_lock_open_fail "$_HEAL")"
  flock -w 15 8 || _lock_bye "✗ 다른 update-all 이 잠금 획득 단계에서 15초 넘게 멈춰 있다($_HEAL) — ps -ef | grep update-all 로 확인(그 실행에 Ctrl-Z/STOP 이 걸렸을 수 있다)"
  exec 9>"$_LOCK" || _lock_bye "$(_lock_open_fail "$_LOCK")"
  if ! flock -n 9; then
    _lock_holders
    if [ -z "$_real" ] && [ -n "$_stale" ]; then
      echo "  · 잠금을 쥔 것은 update-all 이 아니라 옛 판이 fd 를 물려준 데몬이다:$_stale — 잠금 파일을 새로 만든다"
      exec 9>&-; rm -f "$_LOCK"
      exec 9>"$_LOCK" && flock -n 9 && echo "    → 잠금을 새로 잡았다 — 진행한다" \
        || _lock_bye "✗ update-all 이 이미 돌고 있다($_LOCK) — 겹쳐 돌리지 않는다. 끝나면 다시 실행하라."
    elif [ -z "$_real" ]; then
      # 보유자가 안 보인다 — 스캔 사이에 앞 실행이 끝났을 수 있다(스캔 60ms 창). 한 번 더 시도한 뒤에만 거부한다.
      flock -n 9 || _lock_bye "✗ 잠금($_LOCK)이 잡혀 있는데 쥔 프로세스가 이 사용자에게 보이지 않는다(다른 사용자의 프로세스?) — 확인: sudo ls -l /proc/*/fd 2>/dev/null | grep hwax-update-all ; update-all 이 아니면 그 .lock 파일만 지우고 재실행"
    else
      _lock_bye "✗ update-all 이 이미 돌고 있다($_LOCK) — 겹쳐 돌리지 않는다. 끝나면 다시 실행하라(즉시 멈추려면 그 실행에 Ctrl-C)."
    fi
  fi
  exec 8>&-
  _child=""; _got_int=0
  _fwd() { [ -n "$_child" ] && { echo "  · $1 받음 — 본문에 넘긴다. 진행 중인 §가 끝나면 멈춘다(즉시 멈추려면 Ctrl-C)" >&2; kill -"$1" "$_child" 2>/dev/null; }; }
  trap '_got_int=1' INT; trap '_fwd TERM' TERM; trap '_fwd HUP' HUP
  # `&` 로 띄운 자식은 job control 없는 셸이 INT·QUIT 를 **무시**로 물려준다(POSIX) — 그대로면 Ctrl-C 가 본문 어디에도 닿지 않는다
  # (실측: sleep 이 INT 를 받고도 살았다). python3 이 기본 처리로 되돌린 뒤 같은 PID 로 bash 를 exec 한다. <&0 은 & 의 /dev/null stdin 을 막는다.
  if command -v python3 >/dev/null 2>&1; then
    HWAX_UPDATE_ALL_LOCKED="$_LOCK:$$" python3 -c 'import os, signal, sys
signal.signal(signal.SIGINT, signal.SIG_DFL); signal.signal(signal.SIGQUIT, signal.SIG_DFL); os.execvp(sys.argv[1], sys.argv[1:])' \
      bash "${BASH_SOURCE[0]}" "$@" 9>&- <&0 & _child=$!
  else
    echo "  ⚠ python3 이 없어 본문이 Ctrl-C 를 못 받을 수 있다 — 멈추려면 kill $$ (진행 중 단계 뒤에 멈춘다)" >&2
    HWAX_UPDATE_ALL_LOCKED="$_LOCK:$$" bash "${BASH_SOURCE[0]}" "$@" 9>&- <&0 & _child=$!
  fi
  wait "$_child"; _rc=$?
  while kill -0 "$_child" 2>/dev/null; do wait "$_child"; _rc=$?; done   # 신호로 깨어났으면 자식이 끝날 때까지 다시 기다린다
  rm -f "$HWAX_SKIP_LEDGER" 2>/dev/null    # 바깥이 만든 장부는 쓰이지 않는다(본문이 자기 것을 만든다)
  # 자식이 Ctrl-C 로 죽었거나(130) Ctrl-C 를 받아 두고 § 머리에서 멈췄으면(143) 우리도 신호로 죽어 부른 쪽의 `;` 체인이 끊긴다 — TERM 으로 멈춘 143 은 _got_int=0.
  if [ "$_got_int" = 1 ] && { [ "$_rc" = 130 ] || [ "$_rc" = 143 ]; }; then trap - INT; kill -INT $$; fi
  exit "$_rc"
fi

# ── 0) git 자격증명 기본값 — private 레포 HTTPS pull 이 'Username for github' 를 반복해서 묻지
#    않게 한다. 미설정일 때만 username=squall321 + credential.helper store 를 심는다(기존 설정
#    보존). 토큰(PAT)은 보안상 스크립트에 넣지 않는다 — store 라 최초 1회만 입력하면
#    ~/.git-credentials 에 저장돼 이후 모든 레포·모든 실행에서 무프롬프트.
if [ -z "$(git config --global credential.helper 2>/dev/null)" ]; then
  git config --global credential.helper store && ok "git credential.helper=store (PAT 1회 입력 후 영속)"
fi
if [ -z "$(git config --global 'credential.https://github.com.username' 2>/dev/null)" ]; then
  git config --global 'credential.https://github.com.username' squall321 \
    && ok "git username 기본값=squall321 (github — 이제 username 은 안 물음)"
fi

# ── 1) 자기 자신 최신화 — 스크립트가 구버전이면 갱신 후 새 버전으로 재실행(1회 한정) ──
hr "1) 포털 레포 최신화"
if [ "${UPDATE_ALL_REEXEC:-0}" != "1" ]; then
  ( cd "$SELF_REPO"
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    git fetch origin "$branch" --quiet 2>/dev/null || echo "  ⚠ git fetch 실패(오프라인?) — 현재 체크아웃으로 진행"
    before="$(git rev-parse --short HEAD 2>/dev/null)"
    if [ "${NO_GIT_RESET:-0}" = "1" ]; then
      git merge --ff-only "origin/$branch" 2>/dev/null || echo "  ⚠ fast-forward 불가 — 현재 체크아웃 유지"
    else
      nstash_before="$(git stash list 2>/dev/null | wc -l)"
      git stash push -u -q -m "update-all auto-stash" 2>/dev/null || true
      # 로컬 수정이 stash로 치워졌으면 조용히 넘어가지 않고 크게 알린다(복구: git stash pop).
      if [ "$(git stash list 2>/dev/null | wc -l)" -gt "$nstash_before" ]; then
        echo "  ⚠ 로컬 수정이 stash로 보관됨(복구: git stash pop). 대상:"
        git stash show --name-only 'stash@{0}' 2>/dev/null | sed 's/^/      /'
      fi
      git reset --hard "origin/$branch" --quiet 2>/dev/null || true
    fi
    after="$(git rev-parse --short HEAD 2>/dev/null)"
    [ "$before" = "$after" ] && echo "  · git: 최신 ($after)" || echo "  · git: $before → $after" )
  # 스크립트 자신이 바뀌었을 수 있으므로 새 버전으로 1회 재실행
  rm -f "$HWAX_SKIP_LEDGER" 2>/dev/null     # 재실행 전의 장부 — 새 판이 자기 것을 만든다(안 지우면 실행마다 하나 남는다)
  exec env UPDATE_ALL_REEXEC=1 HWAX_UPDATE_ALL_REEXEC_PID=$$ bash "$SELF_REPO/infra/scripts/update-all.sh" "$@"   # PID 결합 — 0b 가 '내 재실행' 을 이것으로 판정한다
fi
ok "포털 레포 최신 (재실행 완료)"

# ── 1a) 이름호출 워크플로 동기화 — 정본(infra/pipeline)을 gitignore 런타임 사본(.claude/workflows)에
#        맞춘다. pull 로 정본이 바뀌어도 사본은 안 따라오므로(이름호출이 옛 사본을 쓴다) 여기서 덮는다. ──
if [ -x "$SELF_REPO/infra/scripts/sync-workflows.sh" ]; then
  "$SELF_REPO/infra/scripts/sync-workflows.sh" 2>&1 | sed 's/^/  /' || true
fi

# ── 1b) 배포 전 로컬 안전 백업 — merge/복원이 데이터를 건드리기 전에 /data/backups 스냅샷.
#        비치명적(백업 실패가 배포를 막지 않음). 일일 cron(03:30)도 여기서 멱등 보장 —
#        운영자가 --install-cron 을 따로 기억할 필요 없게 update-all 이 챙긴다. ──
if [ -x "$SELF_REPO/infra/scripts/backup-local.sh" ]; then
  hr "1b) 배포 전 로컬 백업(/data/backups)"
  # tail -6 을 쓰면 안 된다 — 백업 출력은 24줄이고 실패(✗)는 앞쪽에 찍혀 정확히 잘려나간다.
  # 그래서 signalforge·mxwp 백업이 22회 내내 실패하는 동안 화면엔 '✓ 백업 완료'만 보였다.
  # 성공하면 꼬리만, 실패하면 실패 줄을 전부 보여준다.
  BK_LOG="$(mktemp)"
  if "$SELF_REPO/infra/scripts/backup-local.sh" >"$BK_LOG" 2>&1; then
    tail -4 "$BK_LOG" | sed 's/^/  /'
  else
    bad "사전 백업 실패 — 아래 항목이 백업되지 않았다(배포는 계속한다)"
    grep -E '✗' "$BK_LOG" | sed 's/^/    /'
    tail -3 "$BK_LOG" | sed 's/^/  /'
  fi
  rm -f "$BK_LOG"
  "$SELF_REPO/infra/scripts/backup-local.sh" --install-cron 2>&1 | sed 's/^/  /' || true
  # 로그 회전(data-migration D0 ⑦) — infra/.env 에 HWAX_LOGROTATE=1 일 때만. 기본은 안 켠다:
  # D0 항목 중 유일하게 박스 운영 동작(회전)을 바꾸는 것이라 env 게이트 없이 cae00 에 퍼지지 않게 한다.
  if grep -qE '^HWAX_LOGROTATE=1' "$SELF_REPO/infra/.env" 2>/dev/null && [ -x "$SELF_REPO/infra/scripts/install-logrotate.sh" ]; then
    "$SELF_REPO/infra/scripts/install-logrotate.sh" 2>&1 | sed 's/^/  /' || true
  fi
fi

# ── 1c) .env 옵션 동기화 — 새로 생긴 설정이 **이미 있는 .env** 에 없으면 채운다 ──────────
# 왜 여기인가 — 배포·기동 **전**이어야 서비스가 새 설정을 들고 뜬다. 뒤에 두면 다음 회차까지 미반영이다.
# 있는 값은 건드리지 않고 없는 것만 끝에 덧붙이며, 비밀·자리표시자·박스별 값은 **주석으로** 넣고 크게 알린다
# (예시값을 그대로 켜면 "그럴듯하게 틀린 설정" 이 된다 — 09-19 StepForge 자리표시자 URL 이 그 모양이었다).
# 밀린 양이 상한(HWAX_ENV_SYNC_MAX, 기본 10)을 넘으면 **자동으로 켜지 않고** 사람에게 넘긴다.
hr "1c) .env 옵션 동기화"
if [ -x "$SELF_REPO/infra/scripts/env-sync.sh" ]; then
  "$SELF_REPO/infra/scripts/env-sync.sh" 2>&1 | sed 's/^/  /' || true
else
  hwax_skip ".env 옵션 동기화" "env-sync.sh 가 없다(구버전 체크아웃)" "git pull 뒤 재실행"
fi

# ── 1d) ste 라우트 자동 기록 — teleport 박스는 값이 관례로 고정이다 ──────────────────────
# `routes.local.env` 는 gitignore 라 새 클론에 없다. 없으면 STE_ROUTED=0 → §5 가 ste 를 기대하지 않고
# /ste/ 라우트가 안 생기며 §6 은 "라우트 미설정 — 건너뜀" 초록이다(2026-09-03 /ste/ 두절 실사고).
# 주소 자체는 박스마다 다르지만 **teleport 박스의 값은 관례가 고정**(SSH 터널 루프백 127.0.0.1:15810)이라
# 안전하게 적을 수 있다. 사용자 결정(2026-09-25): 기본 켬, HWAX_STE_AUTOROUTE=0 으로만 끈다.
# §2(deploy-all)가 nginx 를 다시 만들기 **전**에 적어야 라우트가 생긴다 — 그래서 여기다.
# `ste=`(빈 값)은 "이 박스에서 서빙 안 함" 이라는 명시라 건드리지 않는다(활성·빈 값 모두 '있다').
# STE 리포 위치 — deploy-ste.sh 와 **같은 규칙**(형제 `../SmartTwinExplorer` → `~/SmartTwinExplorer`). cae00 실측(2026-09-27):
# 리포가 ~/SmartTwinExplorer 에 있어 형제만 보던 1d 가 transport.env 를 못 찾았다(doctor·deploy-ste 는 찾았다).
_ste_repo_dir() {
  if [ -d "$SELF_REPO/../SmartTwinExplorer/deploy" ]; then (cd "$SELF_REPO/../SmartTwinExplorer" && pwd)
  elif [ -d "$HOME/SmartTwinExplorer/deploy" ]; then printf '%s' "$HOME/SmartTwinExplorer"
  else printf '%s' "$SELF_REPO/../SmartTwinExplorer"; fi
}
_STE_TENV="$(_ste_repo_dir)/deploy/transport.env"
_ROUTES_LOCAL_W="$SELF_REPO/backend/config/routes.local.env"
if [ -f "$_STE_TENV" ] \
   && grep -qE '^[[:space:]]*TRANSPORT_MODE=[[:space:]]*teleport' "$_STE_TENV" \
   && ! grep -qE '^[[:space:]]*ste=' "$_ROUTES_LOCAL_W" 2>/dev/null; then
  hr "1d) ste 라우트 자동 기록"
  if [ "${HWAX_STE_AUTOROUTE:-1}" = 1 ]; then
    [ -f "$_ROUTES_LOCAL_W" ] || printf '# 이 박스 전용 라우트 오버레이 — gitignore. 주소는 추적 파일에 적지 않는다.\n' > "$_ROUTES_LOCAL_W"
    printf '# ste — teleport 박스는 SSH 터널(루프백) 경유. update-all 1d 가 적었다(HWAX_STE_AUTOROUTE=0 으로 끈다).\nste=http://127.0.0.1:15810/\n' >> "$_ROUTES_LOCAL_W"
    ok "routes.local.env 에 ste=http://127.0.0.1:15810/ 를 적었다 — §2 가 nginx 를 다시 만든다"
  else
    hwax_skip "ste 라우트 자동 기록" "HWAX_STE_AUTOROUTE=0 으로 꺼 두어 routes.local.env 에 ste= 를 적지 않았다" "HWAX_STE_AUTOROUTE=1(기본) 로 재실행, 또는 routes.local.env 에 ste=http://127.0.0.1:15810/ 직접"
  fi
fi

# ── 1e) Report Archive 재연결 — RA 가 다른 서버쌍으로 이사한 박스(cae00) ─────────────────────────
# 운영자 값은 infra/.env 의 RA_HOST 하나다(RA 요청서 §1·§3 — ReportArchive/docs/[참고] HWAX포탈_연동_요청서.md).
# 그 값으로 ① routes.local.env 의 report-archive=(끝 / = 접두어 STRIP) ② backend/.env 의 RA_BASE_URL
# ③ 게이트웨이 provision.env 의 RA_MCP_URL 을 **유도해 적는다**(멱등 — 있으면 같은 값으로 바꾼다). 세 파일에
# 주소를 손으로 각각 적게 하면 하나가 빠지고 그 하나가 조용히 옛 주소를 본다(ste 의 STE_SSO_URL 이 그렇게
# 죽어 있었다 — docs/one-token D-12). services.yaml 의 로컬 RA 두 항목은 unless_env: RA_HOST 라 이 박스 대상이
# 아니게 된다(구 RA 를 되살리지 않는다). ④ LLM 설정 정본을 RA .env 에서 포털 infra/.env 로 한 번 옮긴다 —
# RA 가 떠난 뒤 그 .env 를 지우면 env-kit 의 @FROM_RA 마커가 조용히 건너뛰어져 챗·심의·PaperIngest 의 LLM 이
# 빈다(요청서 §3-5). 비어 있으면(같은 박스에서 RA 가 도는 dev) 종전대로 — ○ 장부에 적고 넘어간다.
# 주소는 추적 파일에 적지 않는다 — 셋 다 gitignore 파일이다. 2) 앞인 이유: §2 가 nginx 를 다시 만들고 3.5 가 apply-envs 를 돈다.
# infra/.env 의 값 — **bash 가 읽는 것과 같게**: 인라인 주석(공백 뒤 `#`)·양끝 공백·따옴표·CR 을 벗기고 마지막 줄이 이긴다.
# 종전엔 공백을 전부 지워 `RA_HOST=x   # 설명` 이 `x#설명` 이 됐고, 그 값이 세 파일에 ✓ 로 적혔다(2라운드 검토 실측 —
# env-sync 가 넣는 `# RA_HOST=   # ⚠ …` 줄의 `# ` 만 지우는 자연스러운 편집이 정확히 그 모양이다).
# ⚠ LC_ALL=C — UTF-8 로케일의 GNU sed 는 한글 주석이 든 줄에서 `.*$` 를 못 맞추는 경우가 있다(실측 2026-09-27: 같은 명령이
#   Bash 툴에선 벗겨지고 파이썬 자식 셸에선 안 벗겨졌다). 바이트 단위면 결정적이다.
# `=` 뒤 공백은 **주석을 벗긴 뒤에** 지운다 — 먼저 지우면 `KEY=   # 설명`(값 없이 주석만, env-sync 가 넣는 줄의 `# ` 만 지운
# 모양)에서 `#` 앞 공백이 사라져 주석 문구가 값이 된다(4라운드: 네 독자가 모두 그렇게 읽어 일치 시험은 통과했다).
_envfile_value() {  # $1=파일 $2=키 → 마지막 활성 줄의 값, 없거나 빈 값이면 빈 문자열. `export KEY=` 도 같은 줄이다(_common.sh 가 set -a 로 소싱).
                    #   services.py _infra_value·ste-doctor envv·apply-envs ra_env_value 와 같은 규칙 — RA .env·provision.env 도 이것으로 읽는다.
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" 2>/dev/null | tail -1 \
    | LC_ALL=C sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//' | LC_ALL=C tr -d '"'"'"'\r'
}
_ra_envv() { _envfile_value "$SELF_REPO/infra/.env" "$1"; }
_upsert_kv() {  # $1=파일 $2=키 $3=값 [$4=새 파일 권한, 기본 644] — 실패하면 0 이 아닌 값을 돌린다(호출자가 ✓ 를 찍지 않게).
                #   활성 줄이 있으면 **마지막 활성 줄**을 바꾸고(_ra_envv 가 읽는 줄과 같다), 없으면 주석 선언(`# KEY=`, env-sync 가
                #   넣은 것)을 활성값으로 바꾸고, 그것도 없으면 덧붙인다(끝에 개행이 없는 파일이면 먼저 개행 — 안 그러면
                #   `RAT_TOKEN=…RA_MCP_URL=…` 한 줄이 되어 §5 가 그 토큰을 그대로 소싱한다). 다른 줄은 그대로.
  local f="$1" k="$2" v="$3" mode="${4:-644}"
  if [ ! -f "$f" ]; then
    ( umask 077; : > "$f" ) && chmod "$mode" "$f" || return 1     # 비밀 파일(backend/.env·provision.env)은 600 으로 태어난다
  fi
  if grep -qE "^[[:space:]]*#?[[:space:]]*(export[[:space:]]+)?$k=" "$f"; then
    K="$k" V="$v" python3 - "$f" <<'PY' || return 1
import os, re, sys, pathlib
p, k, v = pathlib.Path(sys.argv[1]), os.environ["K"], os.environ["V"]
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
active = [i for i, ln in enumerate(lines) if re.match(r"^\s*(export\s+)?" + re.escape(k) + r"=", ln)]
commented = [i for i, ln in enumerate(lines) if re.match(r"^\s*#\s*(export\s+)?" + re.escape(k) + r"=", ln)]
idx = active[-1] if active else commented[0]          # 읽는 쪽(tail -1, export 허용)과 같은 줄을 고친다 — 아니면 export 줄의 옛 값이 이긴다(4라운드)
exp = "export " if re.match(r"^\s*#?\s*export\s", lines[idx]) else ""
lines[idx] = f"{exp}{k}={v}\n"
p.write_text("".join(lines), encoding="utf-8")
PY
  else
    { [ -s "$f" ] && [ -n "$(tail -c1 "$f")" ] && printf '\n' >> "$f"; printf '%s=%s\n' "$k" "$v" >> "$f"; } || return 1
  fi
}
RA_HOST="$(_ra_envv RA_HOST)"; RA_PORT="$(_ra_envv RA_PORT)"; RA_MCP_PORT="$(_ra_envv RA_MCP_PORT)"
RA_PORT="${RA_PORT:-3000}"; RA_MCP_PORT="${RA_MCP_PORT:-3002}"
if [ -z "$RA_HOST" ]; then
  hwax_skip "Report Archive 원격 재연결" "RA_HOST 미설정 — 이 박스는 RA 를 같은 박스의 :$RA_PORT 로 본다(dev 는 이것이 정상)" "RA 가 다른 서버로 이사한 박스는 infra/.env 에 RA_HOST=<RA 주 서버 주소>(RA 요청서 §1) 를 적고 재실행"
else
  hr "1e) Report Archive 재연결 (RA_HOST → 라우트·RA_BASE_URL·RA_MCP_URL 유도)"
  # 모양 검사 — 문자 집합만 보면 `-x`·`.`·`ra.` 가 통과해 nginx 가 [emerg] host not found 로 죽고, `localhost`/127.x 는 로컬 RA 를
  # 끄면서 자기 자신을 가리켜 RA 가 죽는다(3라운드). IPv4 또는 라벨(영숫자, 안쪽 하이픈)을 점으로 이은 호스트명만. IPv6 미지원.
  _ra_shape='^([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)*[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$'
  # 거부한 값은 **비운다** — 남겨 두면 §5(드리프트·재프로비저닝·재검증)·§6(원격 판정)이 `[ -n "$RA_HOST" ]` 로 그 값을 믿어
  # 원인 하나에 ✗ 가 셋으로 분다(4라운드). 비교는 소문자로(LOCALHOST·Localhost 도 같은 것).
  case "${RA_HOST,,}" in
    localhost|localhost.*|127.*|0.0.0.0|ip6-localhost|ip6-loopback) fail "RA_HOST 는 **원격** 주소여야 한다 — localhost/127.x 를 적으면 로컬 RA 항목은 꺼지고 주소는 자기 자신을 가리켜 RA 가 죽는다. 같은 박스에서 RA 가 돌면 RA_HOST 를 비운다: '$RA_HOST'"; RA_HOST="" ;;
    *)
      if [[ ! "$RA_HOST" =~ $_ra_shape ]]; then
        fail "RA_HOST 는 IPv4 주소 또는 호스트명이어야 한다(스킴·포트·경로·주석 없이, 라벨은 영숫자로 시작·끝나고 하이픈은 안쪽만, 점으로 시작·끝나지 않고, IPv6 미지원. 포트는 RA_PORT·RA_MCP_PORT): '$RA_HOST'"; RA_HOST=""
      else
      RA_BASE_URL="http://$RA_HOST:$RA_PORT"
      RA_MCP_URL="http://$RA_HOST:$RA_MCP_PORT/mcp"
      _RL="$SELF_REPO/backend/config/routes.local.env"
      [ -f "$_RL" ] || printf '# 이 박스 전용 라우트 오버레이 — gitignore. 주소는 추적 파일에 적지 않는다.\n' > "$_RL"
      if _upsert_kv "$_RL" report-archive "$RA_BASE_URL/"; then
        ok "routes.local.env: report-archive=$RA_BASE_URL/  (끝 / = 접두어 STRIP — RA 화면이 그것을 기대한다. §2 가 nginx 를 다시 만든다)"
      else fail "routes.local.env 에 report-archive= 를 못 적었다($_RL) — 권한·소유자를 보라"; fi
      if _upsert_kv "$SELF_REPO/backend/.env" RA_BASE_URL "$RA_BASE_URL" 600; then
        ok "backend/.env: RA_BASE_URL=$RA_BASE_URL  (PAT 연결 검증·챗 PPT 가져오기 — §2 가 포털을 stop→start 하며 읽는다)"
      else fail "backend/.env 에 RA_BASE_URL 을 못 적었다 — 권한·소유자를 보라"; fi
      if [ -n "$GW_DIR" ]; then
        if _upsert_kv "$GW_DIR/provision.env" RA_MCP_URL "$RA_MCP_URL" 600; then
          ok "게이트웨이 provision.env: RA_MCP_URL=$RA_MCP_URL  (§5 가 config 와 다르면 재프로비저닝한다)"
        else fail "게이트웨이 provision.env 에 RA_MCP_URL 을 못 적었다 — 권한·소유자를 보라"; fi
      else
        bad "HWAXMcpGateway 리포를 못 찾아 RA_MCP_URL 을 못 적었다 — 챗의 RA 도구가 옛 주소(같은 박스 :$RA_MCP_PORT)를 본다"
      fi
      # ④ LLM 정본 이관 — infra/.env 에 없고 RA .env 가 아직 있으면 한 번 가져온다. 이미 있으면 건드리지 않는다.
      if [ -z "$(_ra_envv LLM_BASE_URL)" ]; then
        _RA_ENV=""
        for _c in "$SELF_REPO/../ReportArchive/backend/.env" "$SELF_REPO/../ReportArchive/.env"; do
          [ -f "$_c" ] && { _RA_ENV="$_c"; break; }
        done
        if [ -n "$_RA_ENV" ] && [ -n "$(_envfile_value "$_RA_ENV" LLM_BASE_URL)" ]; then   # 사전검사도 루프와 같은 독자로(4라운드: grep 첫 줄 규칙이 달랐다)
          # "RA .env 에 없다"(키 없는 LLM 이면 정상)와 "infra/.env 에 못 썼다"(고장)는 다른 일이다 — 한 칸에 두지 않는다(3라운드).
          _moved=""; _absent=""; _failed=""
          for _k in LLM_BASE_URL LLM_MODEL LLM_API_KEY; do
            _v="$(_envfile_value "$_RA_ENV" "$_k")"
            if [ -z "$_v" ]; then _absent="$_absent $_k"
            elif _upsert_kv "$SELF_REPO/infra/.env" "$_k" "$_v"; then _moved="$_moved $_k"
            else _failed="$_failed $_k"; fi
          done
          [ -n "$_failed" ] && fail "LLM 설정을 infra/.env 에 못 적었다($_failed ) — 권한·소유자를 보라(RA 설치본을 지우면 그 키들의 LLM 이 빈다)"
          for _k in $_moved; do hwax_skip_forget "설정값 $_k"; done     # 1c 가 "값 미정" 으로 적은 것을 여기서 채웠다 — 장부에서 지운다
          if [ -z "$_absent" ] && [ -z "$_failed" ]; then
            ok "LLM 설정을 RA .env 에서 infra/.env 로 옮겼다($_moved ) — 이제 RA 설치본을 지워도 챗·심의·PaperIngest 의 LLM 이 비지 않는다"
          elif [ -n "$_absent" ] && [ -z "$_failed" ]; then     # 못 적은 것은 위 fail 하나로 — '직접 적어라' 는 못 적는 파일에 할 말이 아니다(4라운드)
            bad "LLM 설정 중 RA .env 에 없는 키가 있다:$_absent (키 없는 LLM 이면 정상. 아니면 infra/.env 에 직접 적는다)${_moved:+ — 옮긴 것:$_moved}"
          fi
        else
          hwax_skip "LLM 설정 정본" "infra/.env 에 LLM_BASE_URL 이 없고 형제 ReportArchive/.env 에서도 못 읽었다 — env-kit 의 @FROM_RA 가 건너뛰어져 각 앱 기본값을 쓴다" "infra/.env 에 LLM_BASE_URL·LLM_MODEL·LLM_API_KEY 를 적고 재실행"
        fi
      fi
      # RA MCP 도구(챗의 보고서 검색·저장)는 게이트웨이가 RAT_TOKEN 이 있을 때만 RA 백엔드를 기대한다(§5 calc_missing).
      # RA_HOST 를 적은 박스에서 그 토큰이 없으면 RA 는 살아 있는데 챗에서 안 보인다 — 조용히 지나가지 않게 장부에.
      _rat_now="${RAT_TOKEN:-}"
      [ -z "$_rat_now" ] && [ -n "$GW_DIR" ] && _rat_now="$(_envfile_value "$GW_DIR/provision.env" RAT_TOKEN)"
      [ -n "$_rat_now" ] || hwax_skip "RA MCP 도구(챗의 보고서 검색·저장)" "RAT_TOKEN 이 없어 게이트웨이가 RA 백엔드를 기대하지 않는다(RA 는 원격에 살아 있어도 챗에 안 붙는다)" "RA 에서 PAT(rat_…)를 발급해 HWAXMcpGateway/provision.env 에 RAT_TOKEN=<값> 을 적고 재실행(§5 가 재프로비저닝한다)"
      # RA 서버가 받아 갈 포털 JWKS 주소(요청서 §4-2) — RA 서버에서 닿는 주소라 포털이 확정할 수 없다. 후보와 로컬 프로브를 찍는다.
      _jw="$(http_code http://127.0.0.1:8088/.well-known/jwks.json 3)"
      _lan="$(hostname -I 2>/dev/null | awk '{print $1}')"
      _pub="$(_ra_envv TLS_SERVER_NAME)"
      echo "  · RA 담당에게 줄 JWKS 주소(요청서 §4-2, RA A·B 의 PORTAL_JWKS_URL) — 로컬 프로브 $_jw:"
      echo "      사내망 http : http://${_lan:-<이 박스 주소>}:8088/.well-known/jwks.json   (RA 쪽 CA 불필요 — 요청서가 '더 간단' 이라 한 쪽)"
      [ -n "$_pub" ] && echo "      공개 https  : https://$_pub/.well-known/jwks.json   (인증서가 사내 CA·자체서명이면 RA 서버에 http://127.0.0.1:8088/tls/ca.crt 의 체인을 둔다)"
      fi ;;
  esac
fi

# ── 1f) AI Ready Portal(ARP) 연결 — ARP_HOST 로 게이트웨이 ARP_BASE 를 맞춘다 ─────────────
# 1e(RA_HOST)와 같은 방식 — 값은 infra/.env(gitignore)에만, 추적 파일에는 적지 않는다(docs/arp-binding).
# 타일은 2026-10-07 부터 포털 경유(/aireadyportal/)다. D-1(「ARP 가 절대경로로 이동해 보류」)은 ARP 가 그 이동을
# 고쳐(arp_base.js 신규 · stripMiddleware · go() 접두어 부착, 2026-09-28~10-06) 해소됐다. 목적지는 routes.local.env 의
# `aireadyportal=` 이고 systems.local.yaml 에는 쓰지 않는다 — 타일 id 가 aireadyportal 이라 `arp:` 는 고아 항목이 된다.
ARP_HOST="$(_ra_envv ARP_HOST)"; ARP_PORT="$(_ra_envv ARP_PORT)"; ARP_PORT="${ARP_PORT:-3001}"
if [ -z "$ARP_HOST" ]; then
  hwax_skip "AI Ready Portal 주소 묶기" "infra/.env 에 ARP_HOST 가 없다 — 게이트웨이 ARP_BASE(HWAXMcpGateway/provision.env)를 손으로 둔 그대로 쓴다(타일 목적지는 routes.local.env 의 aireadyportal=)" "infra/.env 에 ARP_HOST=<ARP 서버 주소>(포트가 3001 이 아니면 ARP_PORT) 를 적으면 update-all 이 게이트웨이 ARP_BASE 를 맞춘다"
else
  hr "1f) AI Ready Portal 연결 (ARP_HOST → 게이트웨이 ARP_BASE)"
  # 모양 검사는 1e(RA_HOST)와 같은 규칙 — IPv4 또는 라벨(영숫자, 안쪽 하이픈)을 점으로 이은 호스트명만. 거부한 값은 비운다.
  _arp_shape='^([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)*[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$'
  case "${ARP_HOST,,}" in
    localhost|localhost.*|127.*|0.0.0.0|ip6-localhost|ip6-loopback)
      fail "ARP_HOST 는 ARP 서버 주소여야 한다(localhost/127.x 아님): '$ARP_HOST'"; ARP_HOST="" ;;
    *) if [[ ! "$ARP_HOST" =~ $_arp_shape ]] || [[ ! "$ARP_PORT" =~ ^[0-9]{1,5}$ ]]; then
         fail "ARP_HOST 는 IPv4 주소 또는 호스트명, ARP_PORT 는 숫자여야 한다(스킴·경로·주석 없이): '$ARP_HOST' / '$ARP_PORT'"; ARP_HOST=""
       fi ;;
  esac
  if [ -n "$ARP_HOST" ]; then
    ARP_BASE="http://$ARP_HOST:$ARP_PORT"
    ok "타일 주소는 routes.local.env 의 aireadyportal= 이 정본이다 — systems.local.yaml 에 쓰지 않는다"
    # 그 라우트는 손으로 적는다 — ARP 서버 주소가 infra/.env(ARP_HOST)와 라우트 파일 두 곳에 있다. 한쪽만 고치거나 라우트를 빼먹어도
    # 오류가 나지 않는다 — 없으면 타일이 숨어 ARP 를 붙인 박스인데 타일만 안 보이고, 다르면 타일과 챗의 ARP 도구가 서로 다른 서버를 본다.
    # 여기서 적어 주지는 않는다(적을지는 정하지 않았다) — 어긋나거나 없으면 말한다. local 이 base 를 이긴다(gen-nginx-conf 와 같다).
    # 키도 gen-nginx-conf 가 읽는 대로 읽는다 — 키 둘레의 공백을 떼고(`aireadyportal = …` 도 라우트다), 박스 파일이 그 키를 **정의했으면**
    # 값이 비어도 추적 파일로 넘어가지 않는다(빈 값은 '이 박스에서 끔' 이고 생성기는 그 키의 추적 줄을 버린다). 종전엔 붙여 적은
    # 줄만 읽어, 라우트가 멀쩡한 박스에서 매 실행 '라우트가 없다' 가 떴다. 파일을 직접 읽는다(파이프가 아니다 — pipefail 과 무관).
    _arp_route=""
    for _f in "$SELF_REPO/backend/config/routes.local.env" "${ROUTES_ENV:-}"; do
      [ -n "$_f" ] && [ -f "$_f" ] || continue
      grep -qE '^[[:space:]]*aireadyportal[[:space:]]*=' "$_f" || continue
      _arp_route="$(sed -n 's|^[[:space:]]*aireadyportal[[:space:]]*=[[:space:]]*\(.*\)|\1|p' "$_f" | tail -1 | tr -d '[:space:]')"
      break
    done
    _arp_route_host="$(printf '%s' "$_arp_route" | sed -n 's|^[A-Za-z][A-Za-z0-9+.-]*://\([^/:]*\).*|\1|p' | tr 'A-Z' 'a-z')"
    if [ -z "$_arp_route" ]; then
      bad "ARP 타일 라우트가 없다 — backend/config/routes.local.env 에 aireadyportal=$ARP_BASE/ 를 적는다(없으면 포털이 타일을 숨긴다 — 챗의 ARP 도구만 붙고 타일은 안 보인다)"
    elif [ "$_arp_route_host" != "${ARP_HOST,,}" ]; then
      bad "ARP 주소가 두 곳에서 다르다 — infra/.env 의 ARP_HOST 와 라우트 파일의 aireadyportal= 이 다른 서버를 가리킨다(타일과 챗의 ARP 도구가 갈린다). ARP 서버가 이사했으면 둘 다 고친다"
    fi
    if [ -n "$GW_DIR" ]; then
      if _upsert_kv "$GW_DIR/provision.env" ARP_BASE "$ARP_BASE" 600; then
        ok "게이트웨이 provision.env: ARP_BASE=$ARP_BASE  (§5 가 config 와 다르면 재프로비저닝한다)"
      else fail "게이트웨이 provision.env 에 ARP_BASE 를 못 적었다 — 권한·소유자를 보라"; fi
    else
      bad "HWAXMcpGateway 리포를 못 찾아 ARP_BASE 를 못 적었다 — 챗의 ARP 도구가 옛 주소를 본다"
    fi
  fi
fi

# ── 1g) 내부 목적지를 NO_PROXY 에 더한다 — 이 뒤에 뜨는 서비스(§2 포털 · §4·§5 게이트웨이·에이전트서버)가 물려받는다 ──────
# RA·ARP 는 사내망의 다른 서버다. 이 셸에 http_proxy 가 있으면(git·rclone 용) 서비스의 httpx 가 그 호출까지 프록시로 보내고 상대의
# IP 허용목록에 걸린다 — RA 사람별 위임이 그렇게 403 이었다(2026-10-03 cae00 실측, 9차 요청 §4-(2)). 운영자 ~/.bashrc 의 임시 블록에
# 기대면 새 박스·cron 에서 다시 뚫린다. 값은 1e·1f 가 방금 읽어 모양을 본 것이다(거부한 값은 비워 두었다) — 있는 것만 더한다.
# 있던 항목·순서는 그대로 두고 없는 것만 뒤에 붙인다(no_proxy 는 맨 위에서 NO_PROXY 와 같게 맞춰 두었다). 주소는 찍지 않는다.
# ⚠ 목록에는 **위에서 값을 읽어 둔 변수만** 적는다 — ODB_HOST·TESTSCOPE_HOST 는 리포 어디에서도 읽지 않는다. 값은 `${!k:-}` 로
#   읽는다(미정의는 빈 값) — `$ODB_HOST` 처럼 그대로 쓰면 set -u 라 그 줄에서 실행이 통째로 죽는다.
#   update-all 밖에서 뜨는 포털(restart.sh·부팅 유닛)은 이 export 를 못 받는다 — start.sh 가 infra/.env 의 같은 두 값을 직접 더한다
#   (그쪽은 파일을 다시 소싱하므로 1e·1f 와 같은 식으로 모양을 다시 본다 — 여기서 거부한 값이 그리로 돌아오면 포털이 안 뜬다).
_np_added=""
for _np_k in RA_HOST ARP_HOST; do
  _np_h="${!_np_k:-}"
  [ -n "$_np_h" ] || continue
  case ",${NO_PROXY:-}," in *",$_np_h,"*) ;; *) NO_PROXY="${NO_PROXY:+$NO_PROXY,}$_np_h"; _np_added="$_np_added $_np_k" ;; esac
done
export NO_PROXY="${NO_PROXY:-}"; export no_proxy="$NO_PROXY"
if [ -n "$_np_added" ]; then echo "  · NO_PROXY 에 내부 목적지를 더했다:$_np_added (이 뒤에 뜨는 서비스가 물려받는다)"; fi

# ── 2) 전 서비스 배포(코드+Drive 아티팩트+기동+nginx). SF DB는 기본 보존, SF_RESTORE_DB=1이면 복원 ──
hr "2) deploy-all-from-drive (portal·mxwp·heax·signalforge·aidh·kooremapper)"
# 종료코드 3 = 소스 갱신 실패(git fetch/reset). 서비스는 떠 있어도 옛 코드라 가장 위험한
# 상태다 — "✓ up" 만 보고 끝내면 오늘 올린 변경이 하나도 반영되지 않은 채 정상으로 읽힌다.
# (예전 주석은 'skip 건수를 종료코드로 낸다'였으나 실제로는 그런 코드가 없었다.)
# ⚠ set -e 를 켜면 안 된다. 이 스크립트는 5행에서 의도적으로 -e 를 껐다 — 서비스 하나의
# 실패가 전체를 끊지 않고 마지막 게이트에서 판정하는 설계다. 여기서 켜면 그 아래 400여
# 줄이 첫 비영점에서 그냥 죽는다(게이트웨이가 내려가 있기만 해도 진단 없이 중단된다).
# -e 가 꺼져 있으므로 rc 는 그냥 받으면 된다.
SF_RESTORE_DB="${SF_RESTORE_DB:-0}" "$SELF_REPO/infra/scripts/deploy-all-from-drive.sh"
_DA_RC=$?
if [ "$_DA_RC" = "3" ]; then
  # bad 가 아니라 fail 이다 — 코드가 안 올라간 상태를 '경고' 로 두면 마지막 요약이
  # '✓ 전체 최신화 완료' 로 끝나 그대로 운영에 들어간다.
  fail "소스 갱신 실패 — 코드는 옛것이다. 위 '✗ git' 줄의 원인을 먼저 해결하고 다시 돌려라"
elif [ "$_DA_RC" = "4" ]; then
  # 배포 항목 skip 도 실패다 — 그 서비스는 옛것으로 돌고 있다.
  fail "deploy-all 에서 배포 항목이 skip/실패했다 — 위 '⚠ skip:' 줄의 원인을 해결하라"
elif [ "$_DA_RC" != "0" ]; then
  fail "deploy-all 이 rc=$_DA_RC 로 끝났다 — 위 ⚠ 줄과 아래 헬스게이트를 함께 보라"
fi

# ── 3) AIDataHub 데이터 동기화 — dev가 원본. Drive 덤프가 지난 복원분과 같으면 restore 생략
#      (prod 챗도 create_agent 등 쓰기 도구를 노출하므로, 새 덤프 없는데 매번 DROP+restore 하지 않는다) ──
# ── 2b) /data 이관(docs/data-migration) — infra/.env 에 HWAX_DATA_ROOT 가 있을 때만. 아직 현행 경로에 있는
#        데이터만 옮기고(멱등) 이미 옮긴 건 건너뛴다. 실패는 자동 롤백. 없으면 이 절은 아무것도 안 한다. ──
if grep -qE '^HWAX_DATA_ROOT=/' "$SELF_REPO/infra/.env" 2>/dev/null && [ -x "$SELF_REPO/infra/scripts/data-migrate.sh" ]; then   # 절대경로만(상대값 'data' 실사고)
  hr "2b) /data 이관 (HWAX_DATA_ROOT 설정됨 — 미이동 클래스만)"
  "$SELF_REPO/infra/scripts/data-migrate.sh" run --yes 2>&1 | sed 's/^/  /' || bad "/data 이관 일부 실패 — 위 ✗·↩ 줄 확인(자동 롤백됨)"
fi

hr "3) AIDataHub 데이터(에이전트·레코드) 동기화"
if [ -n "$AIDH_DIR" ] && [ -x "$AIDH_DIR/deploy/apptainer/sync-from-drive.sh" ]; then
  # AIDH_DRIVE_REMOTE 자동 프로비저닝 — 미설정이면 박스의 rclone remote 로 채운다(기존 값은 존중).
  # setup-drive-sync.sh 는 rclone remote 가 없는 새 박스용 대화형 설치라, remote 가 이미 있는
  # 박스(cae00)에서는 env 한 줄이면 충분하다. (dev 원본 덤프 경로: <remote>:AIDataHub/db-dumps)
  AIDH_ENV="$AIDH_DIR/deploy/apptainer/.env"
  [ -f "$AIDH_ENV" ] || { [ -f "$AIDH_ENV.example" ] && cp "$AIDH_ENV.example" "$AIDH_ENV"; } || true
  if ! grep -qE '^AIDH_DRIVE_REMOTE=.+' "$AIDH_ENV" 2>/dev/null; then
    RCLONE_BIN="$(command -v rclone || echo "$SELF_REPO/infra/bin/rclone")"
    AIDH_ALIAS=""
    if [ -x "$RCLONE_BIN" ]; then
      if "$RCLONE_BIN" listremotes 2>/dev/null | grep -qx 'ApptainerImages:'; then
        AIDH_ALIAS="ApptainerImages"
      else
        AIDH_ALIAS="$("$RCLONE_BIN" listremotes 2>/dev/null | head -1 | sed 's/:$//')"
      fi
    fi
    if [ -n "$AIDH_ALIAS" ]; then
      printf 'AIDH_DRIVE_REMOTE=%s:AIDataHub/db-dumps\n' "$AIDH_ALIAS" >> "$AIDH_ENV"
      ok "AIDH_DRIVE_REMOTE 자동 설정: $AIDH_ALIAS:AIDataHub/db-dumps"
    else
      bad "rclone remote 미탐지 — AIDH_DRIVE_REMOTE 수동 설정 필요($AIDH_ENV)"
    fi
  fi
  # 스택 보장 + 임베딩 모델 확보(sync-from-drive 의 [2]/[2b] 만, restore 는 안 함 = 비파괴)
  ( cd "$AIDH_DIR" && AIDH_SKIP_MODEL=0 ./deploy/apptainer/sync-from-drive.sh --dry-run --skip-git >/dev/null 2>&1 ) || true
  LATEST_LINK="$(find "$AIDH_DIR/deploy" -maxdepth 3 -name latest.sql.gz 2>/dev/null | head -1)"
  LATEST_DUMP="$(readlink "$LATEST_LINK" 2>/dev/null || true)"
  MARKER="${LATEST_LINK:+$(dirname "$LATEST_LINK")/.last-merged}"
  if [ -n "$LATEST_DUMP" ] && [ -n "$MARKER" ] && [ "$(cat "$MARKER" 2>/dev/null)" = "$LATEST_DUMP" ]; then
    ok "AIDH 덤프 변화 없음($(basename "$LATEST_DUMP")) — merge 생략"
  elif [ -x "$AIDH_DIR/deploy/apptainer/merge-from-drive.sh" ] \
       && ( cd "$AIDH_DIR" && AIDH_MERGE_DUMP="$(readlink -f "$LATEST_LINK" 2>/dev/null)" ./deploy/apptainer/merge-from-drive.sh ); then
    # MERGE(비파괴): dev 신규는 추가, cae00 자체 등록분은 유지(updated_at 최신 우선). DROP 안 함.
    [ -n "$MARKER" ] && printf '%s' "$(readlink "$LATEST_LINK" 2>/dev/null)" > "$MARKER" 2>/dev/null
    ok "AIDH 데이터 merge(dev 신규 반영 + cae00 데이터 보존)"
  else
    bad "AIDH 데이터 merge 실패 또는 merge-from-drive 없음 — cae00 데이터는 무손상"
  fi
else
  hwax_skip "AIDataHub 동기화" "AIDataHub 리포 또는 sync-from-drive.sh 가 없다" "../AIDataHub 를 클론(update-all 이 다음 실행부터 동기화한다)"
fi

# ── 2c) ste(SmartTwinExplorer) 코드 최신화 ───────────────────────────────────
# ste 웹은 이 리포가 배포하는 사이트가 아니다 — 형제 리포(SmartTwinExplorer)가 자기 헤드노드에
# 배포한다. 그래서 종전에는 update-all 이 **힌트 한 줄만** 찍었다. 그 결과 소스에는 기능이 있는데
# 박스에는 없는 상태가 조용히 생겼다 — 포털→ste 자격 중계(/api/auth/sso)가 배포된 빌드에 아예
# 없어서, 시크릿을 맞게 줘도 401 이었다(2026-09-23 실측, docs/one-token/context-notes.md D-12).
# 게이트웨이의 ste per_user 위임도 같은 엔드포인트를 쓰므로 함께 죽어 있었다.
#
# 그래서 **최신화를 여기서 한다.** 단 위험이 다른 두 대상을 가른다(판정은 deploy-ste.sh 가 한다) —
#   · direct(같은 박스 ssh, dev 의 ste VM) : 매번 대조해서 **다를 때만** 배포한다. Drive 왕복이
#     없어 싸고, 재기동도 다를 때만 하므로 돌던 잡을 끊지 않는다.
#   · teleport(에어갭 운영 클러스터)        : **공용 게이트 세 신호**를 통과할 때만 돈다(lib/deploy-gate.sh) —
#     사람 호출(대화형 터미널 ∨ `--with-ste` ∨ `STE_DEPLOY=1`) ∧ 신선도(Drive 커밋 ≠ 헤드 마커) ∧
#     Teleport 세션. 크론·파이프에서는 첫 신호가 거짓이라 안 돌고 "안 켠 기능" 장부(○)에 적힌다.
#     (옛 주석은 "STE_DEPLOY=1 없이는 안 돈다" 였다 — 게이트 도입 뒤로는 그 하나만이 조건이 아니다.)
# 리포나 접속 설정이 없는 박스에서는 한 줄 말하고 건너뛴다(부트스트랩을 발화시키지 않는다).
#
# ⚠ 여기서 실패해도 update-all 전체를 죽이지 않는다 — 다른 서비스 갱신까지 막을 이유가 없고,
#   "됐다/안 됐다" 의 최종 판정은 §6 의 ste 헬스게이트(자격 중계 양쪽 확인)가 한다.
hr "2c) ste 코드 최신화 (다를 때만)"
if [ -x "$SELF_REPO/infra/scripts/deploy-ste.sh" ]; then
  # ⚠ 상한을 둔다. ssh 쪽에도 ConnectTimeout 이 있지만 전송 자체가 늘어질 수 있고,
  #   ste 하나 때문에 갱신 전체가 멈추면 안 된다. 900초면 코드 전송(수십 MB)에 충분하다.
  # --foreground — GNU timeout 은 기본으로 명령을 **새 프로세스 그룹**에 넣어 터미널 Ctrl-C 가 닿지 않는다(3라운드 실측: 900초 동안 Ctrl-C 무효,
  #   그 뒤 본문은 '정상 종료' 로 읽어 끝까지 진행). --foreground 면 같은 그룹이라 Ctrl-C 가 닿고, 타임아웃 시 deploy-ste.sh 자체엔 TERM 이 간다.
  _ste_step="ste-$$-$(date +%s%N)"
  HWAX_STEP_ID="$_ste_step" timeout --foreground 900 "$SELF_REPO/infra/scripts/deploy-ste.sh" --if-stale
  case $? in
    0)   : ;;
    3)   : ;;   # 게이트가 막았다(옵션 없음·전제 미충족) — 사유는 위에 찍혔고 장부(○)에 적혔다. 실패가 아니다
    124) bad "ste 최신화 900초 초과 — 중단했다. 헤드노드 도달성을 확인하라(§6 ste 게이트 참조)"; _reap_step "$_ste_step" ;;
    *)   bad "ste 최신화 실패 — §6 ste 게이트가 다시 판정한다(위 사유 참조)" ;;
  esac
else
  hwax_skip "ste 코드 최신화" "deploy-ste.sh 가 없다(구버전 체크아웃)" "git pull 뒤 재실행"
fi

# ── 2d) ste 터널 정합 — cae00(teleport)은 15810·15812 를 SSH 터널로 받는다. 그 터널을 **배포가 세운다**.
# 종전엔 §6 이 "15812 에 아무것도 없다" 고 **보고만** 했다. 배포를 다시 돌려도 터널은 아무도 손대지 않으니
# 같은 빨강이 매번 반복됐다(사용자 실측: "여전히 배포하면 …"). 자동 복구가 이 자리다 —
# 읽기 검사(--check)가 통과하면 아무것도 건드리지 않고, 실패했을 때만 리포 유닛으로 다시 세운다.
# 옛 손 터널이 15810 을 쥐고 있으면 유닛의 -L 바인드가 실패해 영원히 재시도하는데(ExitOnForwardFailure),
# 사람 눈에는 "15810 은 되는데 15812 만 안 된다" 로 보인다 — install-ste-tunnel.sh 가 그것을 내리고 다시 세운다.
hr "2d) ste 터널 정합 (teleport 박스만)"
_tenv=""
for _c in "$SELF_REPO/../SmartTwinExplorer/deploy/transport.env" "$HOME/SmartTwinExplorer/deploy/transport.env"; do
  [ -f "$_c" ] && { _tenv="$_c"; break; }
done
_tmode=""; [ -n "$_tenv" ] && _tmode="$(_envfile_value "$_tenv" TRANSPORT_MODE)"
if [ ! -x "$SELF_REPO/infra/scripts/install-ste-tunnel.sh" ]; then
  hwax_skip "ste 터널 정합" "install-ste-tunnel.sh 가 없다(구버전 체크아웃)" "git pull 뒤 재실행"
elif [ "$_tmode" != teleport ]; then
  hwax_skip "ste 터널 정합" "이 박스는 teleport 가 아니다(transport=${_tmode:-설정 없음}) — 포털이 헤드에 직결이라 터널이 필요 없다" \
    "teleport 박스라면 SmartTwinExplorer/deploy/transport.env 에 TRANSPORT_MODE=teleport (런북 §4)"
elif STE_TUNNEL_NONINTERACTIVE=1 "$SELF_REPO/infra/scripts/install-ste-tunnel.sh" --check >/dev/null 2>&1; then
  ok "ste 터널 15810·15812 둘 다 응답"
else
  echo "  · 터널 점검 실패 — 리포 유닛으로 다시 세운다(옛 손 터널이 포트를 쥐고 있으면 내린다)"
  if STE_TUNNEL_NONINTERACTIVE=1 timeout --foreground 240 "$SELF_REPO/infra/scripts/install-ste-tunnel.sh"; then
    ok "ste 터널 복구 — 15810·15812 둘 다 응답"
  else
    # 여기서 끊지 않는다. 남은 원인은 헤드 쪽(ste-mcp 미기동·Teleport 세션 만료)이라 위 출력이 그것을 가른다.
    fail "ste 터널 복구 실패 — 위의 '로컬 리스너'·journal 을 보라. 진단 한 화면: ./infra/scripts/ste-doctor.sh"
  fi
fi

# ── 3.5) agent-server .env 자동 보정 — 챗 스택 재기동 전에 vLLM 주소를 확정한다.
#   ① .env 없으면 apply-envs 로 신규 생성(@FROM_RA 마커를 RA .env 의 LLM_* 값으로 치환)
#   ② @FROM_RA 마커가 남아있으면(킷 raw 복사/수동편집 흔적 — apply-envs 는 기존키 보존이라 못 고침)
#      그 줄을 지우고 재치환 → '@FROM_RA:LLM_BASE_URL@' 로 붙으려다 APIConnectionError 로 죽던 사고 차단.
hr "3.5) agent-server .env 보정 (@FROM_RA 치환 확인)"
if [ -n "${AGENT_DIR:-}" ]; then
  AGENT_ENV="$AGENT_DIR/.env"
  if [ -f "$AGENT_ENV" ] && grep -q '@FROM_RA:' "$AGENT_ENV"; then
    bad "미치환 @FROM_RA 마커 발견 — 제거 후 재치환"
    sed -i '/@FROM_RA:/d' "$AGENT_ENV"
  fi
  [ -f "$AGENT_ENV" ] || echo "  · .env 없음 — apply-envs 로 신규 생성"
  bash "$SELF_REPO/infra/env-kits/apply-envs.sh" agent-server || echo "  ⚠ apply-envs agent-server 실패"
  VB="$(grep -E '^VLLM_BASE_URL=' "$AGENT_ENV" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  case "${VB:-}" in
    '')          bad "VLLM_BASE_URL 미설정 — RA .env 에 LLM_BASE_URL 없음? (상암 GLM 주소 필요, start.sh 는 로컬 기본으로 폴백)" ;;
    *@FROM_RA:*) bad "VLLM_BASE_URL 아직 마커 — apply-envs 치환 실패(RA .env 의 LLM_BASE_URL 확인)" ;;
    *)           ok "VLLM_BASE_URL=$VB" ;;
  esac
  # TOOL_MAX 정리(prod) — dev 전용 소형 캡(40 등)을 제거해 agent-server 기본값(80)을 쓰게 한다.
  # 80 은 '무조건 절단'이 아니라 질의 관련도(어휘+시맨틱 RRF) 상위 80개 선택이라, 도구가 수백 개로
  # 늘어도 필요한 도구가 남고 컨텍스트도 보호된다. 전량 바인딩이 필요하면 .env 에 TOOL_MAX=0 명시.
  # 원격 LLM(상암 GLM 등 대형 컨텍스트)이면 캡을 아예 푼다(TOOL_MAX=0). 기본 80 을 두면
  # 게이트웨이 도구가 100 개를 넘는 순간 heax-hub 계열이 챗에 안 실려, 아래 헬스게이트가
  # "TOOL_MAX=80 < 게이트웨이 N개" 경고를 내면서도 스크립트는 계속 80 을 강제하는 자기모순이
  # 된다. 로컬 vLLM(작은 컨텍스트)에서는 종전대로 기본값에 맡긴다.
  TM="$(grep -E '^TOOL_MAX=' "$AGENT_ENV" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  case "${VB:-}" in
    ''|*127.0.0.1*|*localhost*) REMOTE_LLM=0 ;;
    *)                          REMOTE_LLM=1 ;;
  esac
  if [ "$REMOTE_LLM" = "1" ]; then
    if [ "${TM:-}" != "0" ]; then
      sed -i '/^TOOL_MAX=/d' "$AGENT_ENV"
      printf 'TOOL_MAX=0\n' >> "$AGENT_ENV"
      ok "원격 LLM 감지 → TOOL_MAX=0(전량 바인딩) 설정${TM:+ (이전 $TM)}"
    else
      ok "TOOL_MAX=0 (전량 바인딩)"
    fi
  elif [ -n "${TM:-}" ] && [ "${TM:-0}" -gt 0 ] 2>/dev/null; then
    sed -i '/^TOOL_MAX=/d' "$AGENT_ENV"
    ok "TOOL_MAX=$TM 제거 → 기본 80(질의 관련도 상위 선택)"
  else
    ok "TOOL_MAX 미설정 → 기본 80(질의 관련도 상위 선택)"
  fi
  # 옛 킷이 심은 심의 호출 타임아웃 — 킷은 없는 키만 더하므로, DELIB_TIMEOUT_S=600 이 박힌 박스는 킷 값을 올려도(1800) 그대로다.
  # 좌석 20석 넘는 패널은 공유 LLM 의 큐 대기가 호출 시계에 들어가 그 600초에 좌석이 빠진다 — 한도를 넉넉히 올린 것이 그 박스에서만
  # 조용히 안 먹는다. 고쳐 쓰지는 않는다(박스가 일부러 정한 값일 수 있다) — 킷의 값(코드 기본값과 같다)보다 짧으면 알린다.
  # 줄 끝 설명이 붙은 값은 숫자가 아니라 여기서 보지 않는다(서버가 경고와 함께 기본값으로 돈다).
  _dto="$(sed -n 's/^DELIB_TIMEOUT_S=//p' "$AGENT_ENV" 2>/dev/null | tail -1 | tr -d '"'"'"' \r')"; _dto="${_dto%%.*}"
  _dto_kit="$(sed -n 's/^DELIB_TIMEOUT_S=//p' "$SELF_REPO/infra/env-kits/agent-server.env" 2>/dev/null | tail -1)"
  if [[ "$_dto" =~ ^[0-9]+$ ]] && [[ "$_dto_kit" =~ ^[0-9]+$ ]] && [ "$((10#$_dto))" -lt "$((10#$_dto_kit))" ]; then
    bad "agent-server .env 의 DELIB_TIMEOUT_S=$_dto 는 권장값(${_dto_kit}초)보다 짧다 — 좌석이 많은 심의에서 LLM 호출이 이 값에 걸려 좌석이 빠진다. 옛 킷이 심은 값이면 $AGENT_ENV 에서 그 줄을 지우고(코드 기본값이 걸린다) agent-server 를 재기동한다"
  fi
else
  hwax_skip "agent-server .env 보정" "HWAXAgentServer 리포가 없다(챗·심의 스택)" "../HWAXAgentServer 를 클론하고 재실행"
fi

# ── 4) 챗 스택만 pull+재기동 — 2)에서 이미 재기동한 사이트들을 다시 내리지 않는다
#      (mxwp-mcp는 deploy-all이 재기동, reportarchive-mcp는 RA 레포 공유라 update 금지 — 기동은 5에서) ──
# §4 는 서비스 지문(git HEAD + .env 내용)을 마지막 기동 시점과 비교한다 — §1c·§3.5·운영자가 .env 를 언제 고쳤든 재기동으로 이어진다(docs/update-all-skip-unchanged D-8)
hr "4) update-sites (챗 스택: mcp-gateway·agent-server·signalforge-mcp)"
# 순서가 중요하다: 백엔드(signalforge-mcp) → 게이트웨이 → 소비자(agent-server).
# 종전엔 게이트웨이를 먼저 올려서, 그 시점에 아직 내려가 있던 signalforge-mcp 에 붙지 못하고
# 6단계 헬스게이트가 'signalforge=DOWN' 을 찍었다(cae00 실측 — 게이트웨이 06:54:46 기동,
# signalforge-mcp 는 06:54:51~54 재기동). _revive_loop 가 60초 안에 스스로 재편입하므로
# 실제 장애는 아니었지만, 매 배포마다 가짜 DOWN 이 뜨면 진짜 장애와 구분이 안 된다.
# ⚠ 갱신 실패를 **실패로 센다.** 헬스게이트는 "떠 있나" 만 보므로, git pull 이 막혀 옛 코드로 떠도
# 초록이었다(2026-09-17 cae00 점검 — 절차가 옛 게이트웨이에 걸려 있었다).
# 3 은 실패가 아니다 — 도는·줄 선 심의가 있어 에이전트 서버 재기동을 미뤘다(update-sites 가 사유를 찍고 장부 ○ 에 적었다).
# 몇 시간 돈 패널을 배포 한 번이 말없이 지우지 않게 한다. 강행은 AGENT_RESTART_FORCE=1 을 주고 재실행.
"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server; _us_rc=$?
case "$_us_rc" in
  0|3) ;;
  *) fail "update-sites 실패 — 갱신 안 된 서비스가 있다(옛 코드로 떠 있을 수 있다). 위 FAIL 줄과 리포의 git status 를 본다" ;;
esac

# ste 를 이 박스가 쓰는가 — **`ste=` 라우트가 설정돼 있으면 쓴다**(ARP_BASE 와 같은 신호 방식).
# 주석(`#ste=`)은 세지 않는다. 아래 기대 백엔드 판정과 프로비저닝 인자 둘 다 이 값을 본다.
_ste_routed() {
  local f
  for f in "$SELF_REPO/backend/config/routes.local.env" "$ROUTES_ENV"; do
    [ -f "$f" ] || continue
    grep -qE '^[[:space:]]*ste=[[:space:]]*[^[:space:]]' "$f" && { echo 1; return; }
  done
  echo 0
}
STE_ROUTED="$(_ste_routed)"
# ste 가 **어디 있는지**의 정본은 이 박스의 `ste=` 라우트다(local 오버레이 우선 — §6 프로브와 같은
# 우선순위). 자격 중계 sso_url 과 MCP url 을 여기서 유도한다. 종전에는 STE_SSO_URL 을 **환경변수로만**
# 받아서, 손으로 export 하지 않고 update-all 을 돌리면 provision 이 `127.0.0.1:15810` 기본값으로
# **멀쩡하던 주소를 덮어썼다**(dev 의 ste 는 VM 192.168.130.x 라 그 순간 위임·REST 다리가 함께 죽는다).
# provision.env 에 명시한 값이 있으면 그것이 이긴다(아래 `${VAR:-}` 가 빈 값일 때만 채운다).
_ste_route_url() {
  local f u
  for f in "$SELF_REPO/backend/config/routes.local.env" "$ROUTES_ENV"; do
    [ -f "$f" ] || continue
    u="$(sed -n 's|^[[:space:]]*ste=[[:space:]]*\(.*\)|\1|p' "$f" | head -1 | xargs)"
    [ -n "$u" ] && { printf '%s' "$u"; return; }
  done
}
_STE_ROUTE="$(_ste_route_url)"
if [ -n "$_STE_ROUTE" ]; then
  # 라우트는 웹 백엔드 자체다(예: http://<헤드 주소>:15810/). origin 만 떼어 경로를 붙인다.
  _STE_ORIGIN="$(printf '%s' "$_STE_ROUTE" | sed -n 's|^\(https\?://[^/]*\).*|\1|p')"
  if [ -n "$_STE_ORIGIN" ]; then
    [ -z "${STE_SSO_URL:-}" ] && STE_SSO_URL="$_STE_ORIGIN/api/auth/sso"
    # MCP 는 같은 호스트의 STE_MCP_PORT(기본 15812)다. 포트를 바꾼 박스는 provision.env 의
    # STE_MCP_URL 이 이긴다 — 여기서는 기본 관례만 채운다.
    [ -z "${STE_MCP_URL:-}" ] && STE_MCP_URL="$(printf '%s' "$_STE_ORIGIN" | sed 's|:[0-9]*$||'):15812/mcp"
    echo "  · ste 주소 유도: $_STE_ORIGIN → sso=$STE_SSO_URL · mcp=$STE_MCP_URL"
  fi
fi
# 시크릿은 infra/.env 에만 있다(update-all 은 그 파일을 통째로 소싱하지 않는다 — 필요한 키만 읽는다).
# ⚠ 비밀에는 **기본값 확장**(`:-` 폴백)을 쓰지 않는다 — 명시적 if 로 본다. 그 관용구를 허용하면
#   다음 사람이 거기 리터럴 값을 적어도 통과하고, 비어 있는 박스가 공개값으로 뜬다.
#   `test_no_tracked_secrets` 가 그래서 그 꼴을 통째로 막는다(이 주석도 그 검사를 지나간다).
# 2c) 가 배포하는 대상(ste 리포 transport.env)과 포털이 프록시하는 대상(`ste=` 라우트)은 **따로 설정**된다.
# 앞은 있고 뒤가 없으면 VM 은 최신인데 포털 /ste 와 게이트웨이 ste 백엔드는 비어 있다 — 조용히
# "ste 를 안 쓰는 박스" 로 판정되므로 여기서 말한다(하드 실패는 아니다 — 정말 안 쓰는 박스일 수 있다).
_STE_TENV="$(_ste_repo_dir)/deploy/transport.env"
if [ "$STE_ROUTED" != 1 ] && [ -f "$_STE_TENV" ]; then
  echo "  ⚠ ste 접속 설정은 있는데($_STE_TENV) 이 박스의 \`ste=\` 라우트가 없다 —"
  echo "    2c) 는 헤드에 배포하지만 포털 /ste 와 게이트웨이 ste 백엔드는 생기지 않는다."
  echo "    쓰려면 backend/config/routes.local.env 에 \`ste=http://<헤드>:15810/\` 을 적는다."
fi
if [ -z "${STE_SSO_SECRET:-}" ] && [ -f "$SELF_REPO/infra/.env" ]; then
  STE_SSO_SECRET="$(sed -n 's/^STE_SSO_SECRET=//p' "$SELF_REPO/infra/.env" | tail -1 | tr -d '"'"'"' ')"
fi
# RA 사람별 위임(ste 방식, docs/sso-delegation) — 같은 자리에서 읽되 **만들지 않는다**(start.sh 2d). 독자는 1e 의
# _ra_envv(bash 가 소싱하는 것과 같은 규칙 — 인라인 주석·따옴표를 벗긴다). env-sync 가 넣은 `# RA_SSO_SECRET=` 주석은 빈 값이다.
if [ -z "${RA_SSO_SECRET:-}" ]; then RA_SSO_SECRET="$(_ra_envv RA_SSO_SECRET)"; fi
# RA 위임 주소 — 포털·게이트웨이가 RA 에 닿는 주소(1e 가 RA_HOST 로 정한 RA_BASE_URL, 없으면 backend/.env 의 값)에 /api/auth/sso.
# 비워 두면 게이트웨이가 직전 config 값, 그것도 없으면 같은 박스 :3000 을 쓴다 — RA 가 원격인 박스(cae00)에서는 틀린 곳이다.
if [ -n "${RA_SSO_SECRET:-}" ] && [ -z "${RA_SSO_URL:-}" ]; then
  _ra_base="${RA_BASE_URL:-$(_envfile_value "$SELF_REPO/backend/.env" RA_BASE_URL)}"
  [ -n "$_ra_base" ] && RA_SSO_URL="${_ra_base%/}/api/auth/sso" && echo "  · RA 위임 주소 유도: $RA_SSO_URL"
fi
# TestScope(다른 조직 포털) — 기본은 사람이 '외부 연결' 에 등록한 그쪽 토큰으로 부른다(RA 와 같은 토큰 등록, 위임 갈래는 아래, docs/sso-delegation).
# 이 박스가 TestScope 를 쓰는 신호는 게이트웨이 provision.env 의 TESTSCOPE_MCP_URL 이다(주소가 있다 = 쓴다).
# §5 가 그 파일을 나중에 소싱하지만 기대 여부(calc_missing)는 여기서 정한다 — 안 보면 백엔드가 빠져도 초록이다.
if [ -z "${TESTSCOPE_MCP_URL:-}" ] && [ -n "$GW_DIR" ]; then TESTSCOPE_MCP_URL="$(_envfile_value "$GW_DIR/provision.env" TESTSCOPE_MCP_URL)"; fi
TESTSCOPE_EXPECTED=0
if [ -n "${TESTSCOPE_MCP_URL:-}" ]; then
  TESTSCOPE_EXPECTED=1
else
  hwax_skip "TestScope MCP 도구" "게이트웨이 provision.env 에 TESTSCOPE_MCP_URL 이 없어 게이트웨이가 TestScope 를 기대하지 않는다(다른 조직 포털 — 안 쓰는 박스가 보통이다)" "TestScope 를 쓰는 박스는 HWAXMcpGateway/provision.env 에 TESTSCOPE_MCP_URL=<TestScope MCP 주소> 를 적고 재실행(§5 가 재프로비저닝한다)"
fi
# ARP(AI Ready Portal) MCP — 주소(ARP_BASE)는 있는데 토큰(ARP_TOKEN)이 없으면 게이트웨이가 arp 를 등재하지 않는다(2026-10-01 부터 인증,
# docs/change-request-8-10 D-5). 조용히 빠지지 않게 장부에 남긴다 — RA 의 RAT_TOKEN(1e)과 같은 자리다. §5 가 provision.env 를
# 소싱하기 전이라 파일에서 읽는다. 기대 여부 자체는 calc_missing 이 소싱된 값으로 정한다.
_arp_b="${ARP_BASE:-}"; _arp_t="${ARP_TOKEN:-}"
if [ -z "$_arp_b" ] && [ -n "$GW_DIR" ]; then _arp_b="$(_envfile_value "$GW_DIR/provision.env" ARP_BASE)"; fi
if [ -z "$_arp_t" ] && [ -n "$GW_DIR" ]; then _arp_t="$(_envfile_value "$GW_DIR/provision.env" ARP_TOKEN)"; fi
if [ -n "$_arp_b" ] && [ -z "$_arp_t" ]; then
  hwax_skip "ARP MCP 도구(챗의 AI Ready Portal)" "ARP 주소는 있는데 ARP_TOKEN 이 없어 게이트웨이가 arp 백엔드를 등재하지 않는다(ARP 는 2026-10-01 부터 인증이 켜져 있다 — 토큰 없이 등재된 옛 항목이 config 에 남아 있으면 §5 가 걷어낸다)" "ARP 담당에게 MCP 서비스 토큰을 받아 HWAXMcpGateway/provision.env 에 ARP_TOKEN=<값> 을 적고 재실행(§5 가 재프로비저닝한다)"
fi
unset _arp_t
# SmartTwinMCP(해석 잡 제출·후처리·수집 도구) — 게이트웨이는 주소가 **설정된** 박스에서만 smart-twin-mcp 를 등재한다
# (docs/change-request-8-10 D-4): provision.env 의 SMARTTWIN_MCP_URL, 또는 지금 config 에 든 **기본값이 아닌** 주소.
# 기본값(같은 박스 :5013)은 설정이 아니라 옛 프로비저너가 무조건 박던 값이다 — cae00 은 그 포트를 듣는 것이 없어 가짜 DOWN 이
# 계속 떠 있었고(2026-10-01·10-08 실측), 게이트웨이는 다음 재프로비저닝에서 그 항목을 뺀다(그 재프로비저닝은 §5 의 _gw_stale 이 당긴다).
# ⚠ 이 조건은 게이트웨이 provision-config.sh 의 등재 조건과 **글자까지 같아야 한다**. 여기만 기대하면 매 실행 재프로비저닝이
#   헛돌고, 여기만 기대하지 않으면 주소를 적은 박스(dev)에서 config 에서 빠져도 초록이다.
_ST_DEFAULT="http://127.0.0.1:5013/mcp"
if [ -z "${SMARTTWIN_MCP_URL:-}" ] && [ -n "$GW_DIR" ]; then SMARTTWIN_MCP_URL="$(_envfile_value "$GW_DIR/provision.env" SMARTTWIN_MCP_URL)"; fi
_st_cfg=""
if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
  _st_cfg="$(python3 -c 'import json,sys;print((json.load(open(sys.argv[1])).get("smart-twin-mcp") or {}).get("url") or "")' "$GW_DIR/gateway_config.json" 2>/dev/null || true)"
fi
SMARTTWIN_EXPECTED=0
if [ -n "${SMARTTWIN_MCP_URL:-}" ] || { [ -n "$_st_cfg" ] && [ "$_st_cfg" != "$_ST_DEFAULT" ]; }; then
  SMARTTWIN_EXPECTED=1
elif [ -n "$_st_cfg" ]; then
  hwax_skip "SmartTwinMCP 도구(해석 잡 제출·후처리)" "게이트웨이 config 에 옛 기본 주소로만 등재돼 있다($_ST_DEFAULT) — 설정한 주소가 아니다. 그 주소에 듣는 것이 없으면 §5 가 이번 실행에서 걷어내고(가짜 DOWN), 듣고 있으면 그대로 두되 다음 재프로비저닝에서 이 백엔드가 빠진다" "이 박스에서 SmartTwinMCP 를 쓰면 HWAXMcpGateway/provision.env 에 SMARTTWIN_MCP_URL=<SmartTwinMCP 주소>(같은 박스면 $_ST_DEFAULT) 를 적는다"
else
  hwax_skip "SmartTwinMCP 도구(해석 잡 제출·후처리)" "게이트웨이 provision.env 에 SMARTTWIN_MCP_URL 이 없어 게이트웨이가 smart-twin-mcp 를 등재하지 않는다(띄운 적 없는 박스가 보통이다)" "SmartTwinMCP 를 쓰는 박스는 HWAXMcpGateway/provision.env 에 SMARTTWIN_MCP_URL=<SmartTwinMCP 주소> 를 적고 재실행(§5 가 재프로비저닝한다)"
fi
# Knox 브리지(사내 사이드카 — 챗의 메일·메신저 도구) — 형제 리포와 그 설정(config/secrets.yaml, gitignore)이 있는 박스에서만 기대한다.
# 게이트웨이 config 의 knox-bridge 는 사람이 붙인 키다 — provision 은 만들지 않고 보존만 한다. 그래서 빠지면 재프로비저닝으로
# 되살아나지 않는다 — §5 가 재프로비저닝 없이 ✗ 로 알린다. 조용히 넘어가지 않는 것이 목적이다(UPSTREAM-ASKS §2).
KNOX_BRIDGE_UP=0
if [ -n "${KNOX_DIR:-}" ] && [ -f "$KNOX_DIR/config/secrets.yaml" ]; then
  KNOX_BRIDGE_UP=1
else
  hwax_skip "Knox 브리지 MCP 도구(챗의 메일·메신저)" "형제 리포 HWAXKnoxBridge 와 그 config/secrets.yaml 이 없어 게이트웨이의 knox-bridge 백엔드를 기대하지 않는다(사내 박스 전용 사이드카)" "HWAXKnoxBridge 를 형제 리포로 두고 config/secrets.yaml 을 채운 뒤 재실행(게이트웨이 config 의 knox-bridge 항목은 그 리포의 안내대로 붙인다)"
fi
# TestScope 사람별 위임(ste 방식) — RA 와 같은 두 갈래다(docs/sso-delegation). 비밀이 없으면 위 토큰 등록 그대로, 있으면 게이트웨이가
# per_user_sso.testscope 로 그 사람 토큰을 TestScope 의 /api/auth/sso 에서 받는다. RA 와 같은 독자로 읽되 **만들지 않는다**(start.sh 2d).
if [ -z "${TESTSCOPE_SSO_SECRET:-}" ]; then TESTSCOPE_SSO_SECRET="$(_ra_envv TESTSCOPE_SSO_SECRET)"; fi
# 위임 주소 — 포털이 토큰 주인을 확인할 때 부르는 TestScope 주소(backend/.env 의 TESTSCOPE_BASE_URL)에 /api/auth/sso.
# RA 와 달리 게이트웨이에 기본 호스트가 없다 — 유도하지 못하면 provision 이 직전 config 값을 잇고, 그것도 없으면 위임을 못 만든다.
if [ -n "${TESTSCOPE_SSO_SECRET:-}" ] && [ -z "${TESTSCOPE_SSO_URL:-}" ]; then
  _ts_base="${TESTSCOPE_BASE_URL:-$(_envfile_value "$SELF_REPO/backend/.env" TESTSCOPE_BASE_URL)}"
  if [ -n "$_ts_base" ]; then
    TESTSCOPE_SSO_URL="${_ts_base%/}/api/auth/sso"; echo "  · TestScope 위임 주소 유도: $TESTSCOPE_SSO_URL"
  else
    echo "  ⚠ TESTSCOPE_SSO_SECRET 은 있는데 TestScope 위임 주소를 모른다 — backend/.env 에 TESTSCOPE_BASE_URL 을 적는다(server-setup.md)."
  fi
fi

# ── 5) 게이트웨이 config 정합 — 기대 백엔드가 config에 아예 없으면 재프로비저닝 ──
hr "5) 게이트웨이 config 정합(reconcile)"
gw_health() { curl -s -m 4 http://127.0.0.1:9110/health 2>/dev/null; }
json_ok() { printf '%s' "$1" | python3 -c 'import json,sys; json.load(sys.stdin)' >/dev/null 2>&1; }
H="$(gw_health)"
if [ -n "$H" ] && ! json_ok "$H"; then
  bad "게이트웨이 /health 응답이 JSON이 아님 — 정합 판정 불가(기동 중이거나 프록시 오류)"
  H=""
fi

calc_missing() {  # $1=health JSON → 기대 목록에서 빠진 백엔드(공백 구분). heax는 config 파일로 별도 판정.
  H="$1" RAT="${RAT_TOKEN:-}" ODB="${ODB_HUB_TOKEN:-}" ARP="${ARP_TOKEN:+${ARP_BASE:-}}" MXWP_UP="$MXWP_UP" \
  SMARTTWIN_EXPECTED="${SMARTTWIN_EXPECTED:-0}" \
  KNOX_BRIDGE_UP="${KNOX_BRIDGE_UP:-0}" STE_ROUTED="$STE_ROUTED" TESTSCOPE_EXPECTED="${TESTSCOPE_EXPECTED:-0}" python3 - <<'PY'
import json, os
h = json.loads(os.environ["H"]); have = set((h.get("backends") or {}).keys())
# hwax-deliberation 은 agent-server(:9009/mcp) 내장이라 이 스택이면 항상 있어야 한다.
# ⚠ 기대 목록에 없으면 재프로비저닝이 안 돈다. gateway_config.json 은 gitignore 라 git pull 로도
#   안 오므로, 코드만 최신이고 게이트웨이는 이 백엔드를 모르는 상태로 남는다 — 그러면 MCP
#   클라이언트에서 심의 진입점(deliberate_*)이 통째로 사라진다(도구 목록에 0개).
want = {"ai-data-hub", "signalforge", "hwax-deliberation"}
if os.environ.get("MXWP_UP") == "1": want.add("mx-white-paper")
if os.environ.get("RAT"):           want.add("reportarchive")
# ODB 자동화 허브는 cae00 에서만 도달한다(dev 는 포트 차단 — 실측). 토큰이 있는 박스에서만
# 기대 목록에 넣는다 — RAT_TOKEN 과 같은 방식이라 dev 에서 가짜 DOWN 이 뜨지 않는다.
if os.environ.get("ODB"):           want.add("odb-hub")
# ARP 도 cae00 전용이다. 인증이 켜져 있어(2026-10-01) 주소와 토큰이 둘 다 있어야 이 박스에서 쓴다는 신호다.
# ⚠ 게이트웨이 provision-config.sh 의 등재 조건(ARP_BASE 와 ARP_TOKEN 둘 다)과 **같아야 한다** — 여기만 주소로 기대하면
#   토큰 없는 박스가 매 실행 arp 를 '빠짐' 으로 보고 재프로비저닝을 헛돌린다(docs/change-request-8-10 D-5).
if os.environ.get("ARP"):           want.add("arp")
# ste(SmartTwinExplorer) MCP — **`ste=` 라우트가 설정된 박스에서만** 기대한다(ARP 와 같은 방식).
# ⚠ 이게 없으면 ste 백엔드가 config 에서 빠져 있어도 "빠진 백엔드 없음" 초록을 받고
#   재프로비저닝이 안 돈다. 그러면 도구 목록에 ste 가 통째로 안 보이는데 게이트는 전부 초록이다 —
#   hwax-deliberation 을 기대 목록에 넣은 것과 정확히 같은 이유다.
if os.environ.get("STE_ROUTED") == "1": want.add("ste")
# TestScope MCP — 게이트웨이 provision.env 에 TESTSCOPE_MCP_URL 이 있는 박스에서만 기대한다(ARP 와 같은 방식, docs/sso-delegation).
if os.environ.get("TESTSCOPE_EXPECTED") == "1": want.add("testscope")
# SmartTwinMCP — 주소가 설정된 박스에서만(위 판정, 게이트웨이의 등재 조건과 같다). 무조건 기대하면 띄운 적 없는 박스가 매 실행 재프로비저닝한다.
if os.environ.get("SMARTTWIN_EXPECTED") == "1": want.add("smart-twin-mcp")
# Knox 브리지 — gateway_config.json 은 gitignore 라 pull 로 오지 않는다. 사라지면 챗의 메일·메신저 도구 6개가 통째로 없어진다.
if os.environ.get("KNOX_BRIDGE_UP") == "1": want.add("knox-bridge")
print(" ".join(sorted(want - have)))
PY
}

# RA·TestScope 사람별 위임이 게이트웨이 config 에 **이 비밀 그대로** 있나(docs/sso-delegation). heax_registry 안의 항목이라 /health 에
# 안 나오고 calc_missing 이 못 본다 — infra/.env 에 비밀을 넣고 돌려도 빠진 백엔드가 없으면 재프로비저닝이 안 돌아 위임이 영영 안
# 켜진다(비밀을 바꿨을 때도 같다). 비밀은 argv 가 아니라 환경변수로 넘기고, 출력은 키 이름뿐이다. TestScope 는 백엔드를 기대할 때만
# 본다(TESTSCOPE_EXPECTED) — 백엔드가 없는 박스에서는 위임이 할 일이 없고, provision 이 만들지 않으면 매 실행 헛된 재프로비저닝을 돈다.
# 거꾸로 비밀을 비웠는데 위임이 남아 있으면 `<키>_sso_off` — 되돌리기(토큰 등록으로)도 재프로비저닝이 있어야 반영된다.
#
# 일반 앱(게이트웨이 PER_USER_SSO_APPS="<per_user 키>:<ENV 접두> …", 8차 요청 §4-(2)) — 게이트웨이는 여섯 번째 앱부터 이 목록으로 위임을
# 만든다(<접두>_SSO_SECRET·<접두>_SSO_URL). 그 값들은 게이트웨이 provision.env 에 있고 여기서는 그 파일을 소싱만 한다. 접두가 박스마다
# 달라 아래 대입어 사슬에 이름을 적을 수 없다 — 넘기지 않으면 '적었는데 손으로 돌릴 때만 켜지는' 설정이 된다. 방아쇠·끄기 규칙은
# RA·TestScope 와 같다. 쌍을 읽는 규칙은 게이트웨이와 같다(콜론이 있고 접두는 환경변수 이름 꼴, 게이트웨이가 직접 만드는 다섯은
# 건너뛴다). 키는 이름 꼴(영숫자·_·.·-)만 다룬다 — 아래에서 따옴표 없이 도는 목록에 실린다. 못 읽은 쌍은 게이트웨이 provision 이 말한다.
# 한 키는 **먼저 적힌 쌍 하나만** 쓴다 — per_user 키 하나에 위임은 하나다. `dup:FOO dup:BAR` 처럼 두 번 적힌 것을 쌍마다 따로 판정하면
# 서로 맞을 수가 없다: 비밀이 한쪽에만 있으면 방아쇠(dup_sso)와 끄기(PER_USER_SSO_OFF=dup)가 한 실행에 같이 나가 게이트웨이가 위임을
# 만들고 곧바로 지우고, 다음 실행도 같다 — 매 실행 재프로비저닝·게이트웨이·에이전트서버 재기동에 '재프로비저닝 후에도 누락' ✗ 까지
# 붙었다(사본에서 세 실행 연속 재현). 못 읽은 쌍은 '먼저' 로 치지 않는다(게이트웨이도 읽은 쌍만 그 키의 것으로 삼는다).
# 인자 dups 를 주면 쌍 대신 **두 번 이상 적힌 키**를 한 번씩 낸다 — §5 가 알리는 데 쓴다.
_sso_generic_pairs() {  # → 줄마다 "<per_user 키> <ENV 접두>"  ($1=dups 면 줄마다 겹친 키)
  local pairs pair k p seen=" " dup=" "
  read -ra pairs <<<"$(printf '%s' "${PER_USER_SSO_APPS:-}" | tr '\t\n' '  ')"
  for pair in ${pairs[@]+"${pairs[@]}"}; do
    k="${pair%%:*}"; p="${pair#*:}"
    [ "$p" != "$pair" ] && [[ "$k" =~ ^[A-Za-z0-9_.-]+$ ]] && [[ "$p" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    case "$k" in kooremapper_mcp|hwax_risk|ste|reportarchive|testscope) continue ;; esac
    case "$seen" in *" $k "*)
      case "$dup" in *" $k "*) ;; *) dup="$dup$k "; if [ "${1:-}" = dups ]; then printf '%s\n' "$k"; fi ;; esac
      continue ;;
    esac
    seen="$seen$k "
    if [ "${1:-}" != dups ]; then printf '%s %s\n' "$k" "$p"; fi
  done
}
_sso_generic_names() {  # → 자식에게 넘길 변수 **이름**(값은 다루지 않는다) — 접두마다 <접두>_SSO_SECRET <접두>_SSO_URL
  local _k p
  while read -r _k p; do
    if [ -n "$p" ]; then printf '%s_SSO_SECRET %s_SSO_URL ' "$p" "$p"; fi
  done <<<"$(_sso_generic_pairs)"
}
# 목록에서 **뺀** 일반 앱 — 앱을 걷을 때 사람은 PER_USER_SSO_APPS 의 쌍과 <접두>_SSO_* 줄을 지운다. 그러면 위 쌍 목록에 그 앱이 없어
# 방아쇠도 끄기도 그 위임을 보지 못했고, 게이트웨이는 옛 비밀로 그 앱에 계속 사람별 토큰을 청했다 — 끌 길이 없었다.
# 게이트웨이는 순회가 쓴 항목에 `"managed_by": "PER_USER_SSO_APPS"` 표지를 남기고(HWAXMcpGateway cff32c3), 표지가 있고 이번 목록의
# 어느 쌍도 그 이름이 아닌 항목은 PER_USER_SSO_OFF 에 **이름이 오면** 지운다. 스스로는 지우지 않는다 — 그 스크립트는 provision.env 를
# 읽지 않아, 손으로 돌린 --force 에는 목록이 없다. '목록에 없다 = 껐다' 는 provision.env 를 읽은 이쪽이 판정해 이름을 넘긴다.
# 규칙은 게이트웨이 provision-config.sh 와 같아야 한다(더 넓으면 매 실행 재프로비저닝이 헛돌고, 더 좁으면 꺼지지 않는다):
#   · 이름은 쌍의 콜론 앞이다 — **못 읽은 쌍도** 센다(접두를 잘못 적은 것을 '뺐다' 로 읽어 위임을 끄지 않게).
#   · 표지 없는 항목은 내지 않는다(ste·hwax_risk·손으로 붙인 위임 — 그 비밀의 출처를 이 실행이 모른다).
#   · 키는 이름 꼴(영숫자·_·.·-)만 — 아래에서 따옴표 없이 도는 목록과, 공백으로 가르는 PER_USER_SSO_OFF 에 실린다.
_sso_generic_unlisted() {  # $1=gateway_config.json → 목록에서 빠졌는데 위임이 남은 일반 앱의 키(공백 구분). 읽지 못하면 빈 값.
  APPS="${PER_USER_SSO_APPS:-}" python3 - "$1" <<'PY' 2>/dev/null || true
import json, os, re, sys
try: d = json.load(open(sys.argv[1]))
except Exception: raise SystemExit(0)
pu = (d.get("heax_registry") or {}).get("per_user_sso") or {}
listed = {t.partition(":")[0] for t in (os.environ.get("APPS") or "").split()}
print(" ".join(k for k in sorted(pu) if isinstance(pu[k], dict) and pu[k].get("managed_by") == "PER_USER_SSO_APPS"
               and k not in listed and re.fullmatch(r"[A-Za-z0-9_.-]+", k)))
PY
}
# 일반 앱의 비밀은 이름이 정해져 있지 않아 대입어로 못 넘긴다 — 서브셸 안에서만 export 한다(이 뒤에 뜨는 서비스가 물려받지 않게).
# 주소가 없어 게이트웨이가 만들지 못하는 일반 앱은 `<키>_sso_nourl` 로 따로 표지한다 — 방아쇠로 삼으면 매 실행 재프로비저닝이 헛돈다.
_sso_deleg_drift() {  # $1=gateway_config.json → 어긋난 위임(공백 구분, 예: reportarchive_sso). 읽지 못하면 빈 값.
  ( export PER_USER_SSO_APPS $(_sso_generic_names)
  RA_S="${RA_SSO_SECRET:-}" TS_S="${TESTSCOPE_SSO_SECRET:-}" TS_X="${TESTSCOPE_EXPECTED:-0}" GEN="$(_sso_generic_pairs)" UNL="$(_sso_generic_unlisted "$1")" python3 - "$1" <<'PY' 2>/dev/null || true
import json, os, sys
try: d = json.load(open(sys.argv[1]))
except Exception: raise SystemExit(0)
pu = (d.get("heax_registry") or {}).get("per_user_sso") or {}
out = []
for k, s in sorted({"reportarchive": os.environ.get("RA_S") or "", "testscope": os.environ.get("TS_S") or ""}.items()):
    cur = pu.get(k) if isinstance(pu.get(k), dict) else None
    if not s:
        if cur is not None: out.append(f"{k}_sso_off")   # 비밀을 비웠는데 위임이 남았다 — provision 이 PER_USER_SSO_OFF 로 지운다
    elif (k != "testscope" or os.environ.get("TS_X") == "1") and (cur or {}).get("secret") != s:
        out.append(f"{k}_sso")
for k, p in sorted(ln.split() for ln in (os.environ.get("GEN") or "").splitlines() if ln.strip()):
    s, u = os.environ.get(f"{p}_SSO_SECRET") or "", os.environ.get(f"{p}_SSO_URL") or ""
    cur = pu.get(k) if isinstance(pu.get(k), dict) else None
    if not s:
        if cur is not None: out.append(f"{k}_sso_off")
    elif not (u or (cur or {}).get("sso_url")):
        out.append(f"{k}_sso_nourl")   # 주소는 env 가 먼저고 없으면 게이트웨이가 지금 config 의 것을 잇는다. 둘 다 없으면 만들지 못한다
    elif (cur or {}).get("secret") != s or (u and (cur or {}).get("sso_url") != u):
        out.append(f"{k}_sso")         # 위임이 없거나 비밀이 다르다, 또는 주소를 바꿨다(게이트웨이가 env 의 주소로 고쳐 쓴다)
# 목록에서 뺀 일반 앱(_sso_generic_unlisted) — 비밀도 접두도 이 실행에는 없다. 표지가 붙은 채 남은 위임이 곧 방아쇠다.
out += [t for t in (f"{k}_sso_off" for k in (os.environ.get("UNL") or "").split()) if t not in out]
print(" ".join(out))
PY
  )
}

# ARP 토큰이 게이트웨이 config 의 arp 항목에 **이 토큰 그대로** 실려 있나 — 아니면 0(어긋남), 맞거나 판정할 수 없으면 1.
# 키(arp)가 config 에 없는 것은 calc_missing 이 본다. 토큰은 argv 가 아니라 환경변수로 넘기고 아무것도 찍지 않는다.
_arp_token_drift() {  # $1=gateway_config.json  (ARP_TOKEN 을 읽는다)
  ARP_T="${ARP_TOKEN:-}" python3 - "$1" <<'PY' 2>/dev/null
import json, os, sys
try: arp = json.load(open(sys.argv[1])).get("arp")
except Exception: raise SystemExit(1)
if not isinstance(arp, dict) or not os.environ.get("ARP_T"): raise SystemExit(1)
raise SystemExit(0 if ((arp.get("headers") or {}).get("Authorization") or "") != "Bearer " + os.environ["ARP_T"] else 1)
PY
}

# 걷어낼 옛 항목 — 게이트웨이가 재프로비저닝 때 **빼는** 관리 키 둘이 config 에 남아 있나. 기대 목록(calc_missing)과 드리프트 판정들은
# '있어야 할 것이 없다·다르다' 만 본다. **없어야 할 것이 남은** 박스에는 방아쇠가 없었다 — #10·#11 이 겨냥한 그 박스(cae00)에서 반영 뒤에도
# 재프로비저닝이 한 번도 안 돌아 가짜 DOWN 둘(arp 401 · smart-twin-mcp 연결 실패)이 그대로였고, 매 실행 "다운 백엔드 … *_MCP_URL 을
# 명시하고 --force" 라는 거꾸로 된 안내가 붙었다(그 주소를 적으면 가짜 DOWN 이 기대값으로 굳는다).
#   smart-twin-mcp — SMARTTWIN_MCP_URL 이 없고 config 의 주소가 옛 기본값이며 **그 주소에 듣는 것이 없을 때**. 듣고 있으면(주소를 안 적은
#     dev 가 그렇게 돈다) 가짜 DOWN 이 아니다 — 여기서 걷어내면 update-all 이 멀쩡한 도구 18종을 제 손으로 뺀다. /health 가 아니라 그
#     주소를 직접 찔러 본다(§4 가 게이트웨이를 막 다시 띄웠으면 /health 는 잠깐 false 다).
#   arp — ARP_TOKEN 이 없고 config 의 arp 가 Authorization 없이 등재돼 있을 때(옛 프로비저너의 모양 — ARP 는 2026-10-01 부터 인증이다).
#     ARP 주소(ARP_BASE)가 provision.env·1f 어디에도 없으면 걷어내지 않고 `arp-keep` 으로 알리기만 한다 — 게이트웨이는 주소를 직전
#     config 의 그 항목에서 잇는다. 유일한 사본을 빼면 나중에 토큰을 적어도 arp 가 등재되지 않는다.
# ⚠ 옆의 provision-config.sh 가 **그 항목을 빼는 판일 때만** 낸다(조건식의 글자를 본다). update-sites 가 게이트웨이를 못 당긴 박스의
#   옛 프로비저너는 둘 다 되살린다 — 방아쇠를 당기면 매 실행 재프로비저닝이 헛돌고 게이트웨이·에이전트서버가 그때마다 내려갔다 올라온다.
# ⚠ config 는 **부를 때마다 다시 읽는다** — §5 앞에서 읽어 둔 _st_cfg 는 재프로비저닝 뒤에도 옛 주소다(재검증에 쓰면 방금 걷어낸
#   항목을 '남았다' 고 한다). 토큰·주소는 넘기지 않는다(있고 없음만).
_gw_stale() {  # $1=gateway_config.json $2=provision-config.sh → 걷어낼 키(공백 구분 — arp-keep 은 알리기만). 판정할 수 없으면 빈 값.
  local k cand out=""
  cand="$(ST_ENV="${SMARTTWIN_MCP_URL:+1}" ST_DEFAULT="$_ST_DEFAULT" ARP_T="${ARP_TOKEN:+1}" ARP_B="${ARP_BASE:+1}" python3 - "$1" <<'PY' 2>/dev/null || true
import json, os, sys
try: d = json.load(open(sys.argv[1]))
except Exception: raise SystemExit(0)
out = []
st = d.get("smart-twin-mcp")
if not os.environ.get("ST_ENV") and isinstance(st, dict) and st.get("url") == os.environ["ST_DEFAULT"]:
    out.append("smart-twin-mcp")
arp = d.get("arp")
if not os.environ.get("ARP_T") and isinstance(arp, dict) and arp.get("url") and not (arp.get("headers") or {}).get("Authorization"):
    out.append("arp" if os.environ.get("ARP_B") else "arp-keep")
print(" ".join(out))
PY
)"
  for k in $cand; do
    case "$k" in
      smart-twin-mcp) grep -qF '_ST_PREV != _ST_DEFAULT' "$2" 2>/dev/null && [ "$(http_code "$_ST_DEFAULT" 3)" = "000" ] || continue ;;
      arp|arp-keep)   grep -qF 'if _ARP_BASE and _ARP:' "$2" 2>/dev/null || continue ;;
    esac
    out="${out:+$out }$k"
  done
  printf '%s' "$out"
}

if [ -z "$H" ]; then
  bad "게이트웨이 :9110 무응답/판정불가 — $SVC up mcp-gateway 후 재시도"
else
  PROV_ENV="${GW_DIR:+$GW_DIR/provision.env}"
  # shellcheck disable=SC1090 — 토큰 파일은 운영 박스에만 존재(gitignore)
  [ -n "$PROV_ENV" ] && [ -f "$PROV_ENV" ] && . "$PROV_ENV"

  # mxwp 기대 여부 — 프로비저너의 전제(mxwp_api 인스턴스)와 동일 조건 + MCP(:8765) 응답까지 확인.
  # (인스턴스 없이 :8765만 보면 매 실행 재프로비저닝 루프가 된다 — 민팅이 인스턴스 안에서 돌기 때문)
  MXWP_UP=0
  # pipefail + 조기종료(grep -q)는 SIGPIPE(141) 오판을 만든다 — 목록을 먼저 받는다(실측 14.7%).
  _il="$(apptainer instance list 2>/dev/null || true)"
  case $'\n'"$(printf '%s\n' "$_il" | awk 'NR>1{print $1}')"$'\n' in
    *$'\n'mxwp_api$'\n'*) _mx_up=1 ;;
    *) _mx_up=0 ;;
  esac
  if [ "$_mx_up" = "1" ]; then
    case "$(http_code http://127.0.0.1:8765/mcp 2)" in ''|000) ;; *) MXWP_UP=1 ;; esac
  fi

  # 프로비저닝보다 먼저 — DynaForge 의 kr_ PAT 발급이 이 시크릿에 걸려 있다. 불일치 상태로
  # provision 을 돌리면 "발급 실패"만 찍히고 도구 22개가 목록에만 뜨는 상태가 유지된다.
  if [ -f "$SELF_REPO/infra/scripts/sync-gateway-secret.sh" ]; then
    bash "$SELF_REPO/infra/scripts/sync-gateway-secret.sh" --write
    case $? in 0|1) ;; *) fail "게이트웨이 공유 시크릿을 맞추지 못했다 — DynaForge SSO·kr_ PAT 가 막힌다." ;; esac
  fi

  MISSING="$(calc_missing "$H")"
  # knox-bridge 는 사람이 config 에 붙인 키다 — provision 은 만들지 못하고 보존만 한다. 빠졌다고 재프로비저닝 방아쇠로 삼으면 되살아나지는
  # 않으면서 **매 실행** 게이트웨이·에이전트서버만 내려갔다 올라온다(도는 챗·심의가 그때마다 끊긴다). 그래서 방아쇠에서 빼고 여기서
  # ✗ 로 알린다 — 기대 목록에 넣은 목적은 '빠져도 초록' 을 막는 것이다(UPSTREAM-ASKS §2: 되살아나지 않고 보고만 된다).
  KNOX_MISSING=0
  case " $MISSING " in *" knox-bridge "*)
    KNOX_MISSING=1
    MISSING="$(for _k in $MISSING; do [ "$_k" = knox-bridge ] || printf '%s ' "$_k"; done)"; MISSING="${MISSING% }"
    fail "knox-bridge 백엔드가 게이트웨이 config 에 없다 — 챗의 메일·메신저 도구가 빠져 있다. 재프로비저닝으로는 되살아나지 않는다(provision 은 이 키를 만들지 않는다) — HWAXKnoxBridge 리포의 안내대로 HWAXMcpGateway/gateway_config.json 에 knox-bridge 항목을 다시 붙이고 게이트웨이를 재기동한다" ;;
  esac
  # kr_ PAT 는 백엔드가 아니라 heax_registry 안의 예외표라 calc_missing 이 못 본다.
  # 이게 없으면 DynaForge MCP 는 '연결됨·도구 22개'인 채로 호출만 전량 실패한다.
  #
  # ⚠ 예전엔 `grep -q '"kooremapper_mcp"'` 로 **키 존재만** 봤다. 그런데 취소·만료된 kr_ PAT 도
  #   키는 그대로 있으므로 이 검사가 통과해 버린다 — 실패 출력이 성공 출력과 같아지는 그 부류다.
  #   (실측: 저장 토큰으로 /api/v1/operations 가 401, 같은 순간 새 토큰은 200.)
  #   그래서 키가 아니라 **토큰이 실제로 인증되는지**로 본다. 죽어 있으면 재프로비저닝 대상이고,
  #   provision-config.sh 가 살아 있는지 확인한 뒤 재발급한다.
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] \
     && grep -q '"heax_registry"' "$GW_DIR/gateway_config.json" 2>/dev/null \
     && [ -n "$(find_repo KooRemapper)" ]; then
    _KR_TOK="$(python3 - "$GW_DIR/gateway_config.json" <<'PY' 2>/dev/null || true
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: raise SystemExit(0)
print(((d.get("heax_registry") or {}).get("app_tokens") or {}).get("kooremapper_mcp",""))
PY
)"
    if [ -z "$_KR_TOK" ]; then
      MISSING="kr_pat(DynaForge:없음)${MISSING:+ $MISSING}"
    elif [ "$(curl -s -o /dev/null -m 8 -w '%{http_code}' \
                -H "Authorization: Bearer $_KR_TOK" \
                "${KOORM_BASE:-http://127.0.0.1:8700}/api/v1/operations" 2>/dev/null)" != "200" ]; then
      # 업스트림(:8700)이 죽어 있어도 여기로 온다 — 재프로비저닝은 그 경우에도 무해하다
      # (provision 이 발급을 못 하면 기존 값을 그대로 두고 경고만 남긴다).
      MISSING="kr_pat(DynaForge:만료·취소)${MISSING:+ $MISSING}"
    fi
    unset _KR_TOK
  fi
  # heax_registry는 /health에 안 나오는 config 전용 항목 — config에 없으면 재프로비저닝 대상.
  # provision-config.sh 가 heax MCP 토큰을 자동 발급하므로, 명시 토큰이 없어도 heax-hub 백엔드(venv)만
  # 있으면 재프로비저닝 → 자동 발급 → heax_registry 활성. (토큰 명시돼 있으면 그것으로.)
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] \
     && ! grep -q '"heax_registry"' "$GW_DIR/gateway_config.json" 2>/dev/null \
     && { [ -n "${HEAX_MCP_TOKEN:-}" ] || [ -x "$(find_repo HEAXHub)/backend/.venv/bin/python" ]; }; then
    MISSING="heax_registry${MISSING:+ $MISSING}"
  fi
  # 리스크 심사 앱 사용자 위임도 heax_registry 안의 항목이라 /health 에 안 나온다. 없으면 MCP 가
  # 서비스 계정 시야로만 돌아 '과제 0건'을 답한다 — 도구는 다 뜨는데 내용이 비는 부류라 눈에 안 띈다.
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] \
     && [ -s "$(find_repo HEAXHub)/var/app_data/hwax_risk/secrets.env" ] \
     && ! python3 - "$GW_DIR/gateway_config.json" <<'PY' 2>/dev/null
import json, sys
try: d = json.load(open(sys.argv[1]))
except Exception: raise SystemExit(1)
sso = ((d.get("heax_registry") or {}).get("per_user_sso") or {}).get("hwax_risk") or {}
raise SystemExit(0 if sso.get("secret") and sso.get("sso_url") else 1)
PY
  then
    MISSING="hwax_risk_sso${MISSING:+ $MISSING}"
  fi

  # 키는 있는데 **주소가 틀려서** 계속 죽는 백엔드 — calc_missing 은 '키 없음' 만 본다.
  # ⚠ 2026-09-19 cae00: SignalForge MCP 는 8008 인데 게이트웨이는 8013 을 들고 있어
  #   `signalforge: false` 가 09-18 부터 떠 있었다. 키가 있으니 여기(재프로비저닝)에 안 걸렸고,
  #   아래 '다운 백엔드' 가 멀쩡한 서비스를 재기동만 반복했다 — 영원히 안 고쳐지는 모양.
  #   형제 서비스가 자기 .env 에 선언한 포트와 config 의 로컬 주소를 비교한다(게이트웨이 리포의
  #   provision_urls.py — 프로비저너와 **같은 판정**을 쓴다. 따로 쓰면 둘이 어긋난다).
  DRIFT=""
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/provision_urls.py" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
    DRIFT="$(python3 "$GW_DIR/provision_urls.py" drift "$GW_DIR/gateway_config.json" "$(dirname "$GW_DIR")" 2>/dev/null || true)"
    if [ -n "$DRIFT" ]; then
      while IFS=$'\t' read -r _k _cur _want; do
        [ -n "$_k" ] || continue
        echo "  · 주소 드리프트: $_k — config 는 $_cur 인데 서비스는 $_want 로 선언했다"
        MISSING="${MISSING:+$MISSING }$_k"
      done <<< "$DRIFT"
    fi
  fi

  # RA 가 원격인 박스(RA_HOST)에서 config 의 reportarchive 주소가 다른 호스트를 가리키면 — 키가 있어 calc_missing 이
  # 못 잡고, provision_urls 의 드리프트도 형제 .env 선언 기반이라 못 잡는다(RA 는 이제 형제가 아니다). 여기서 본다.
  if [ -n "${RA_HOST:-}" ] && [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
    _ra_cfg_host="$(python3 -c 'import json,sys;from urllib.parse import urlparse;d=json.load(open(sys.argv[1]));print(urlparse(((d.get("reportarchive") or {}).get("url") or "")).hostname or "")' "$GW_DIR/gateway_config.json" 2>/dev/null)"
    if [ -n "$_ra_cfg_host" ] && [ "$_ra_cfg_host" != "$(printf '%s' "$RA_HOST" | tr 'A-Z' 'a-z')" ]; then   # hostname 은 소문자로 온다
      echo "  · 주소 드리프트: reportarchive — config 는 $_ra_cfg_host 인데 RA_HOST 는 $RA_HOST 다(1e)"
      MISSING="${MISSING:+$MISSING }reportarchive"
    fi
  fi
  # ARP — 키(arp)는 있으니 calc_missing 이 못 잡는다. ARP_HOST(1f)와 config 의 주소가 다르면 재프로비저닝(docs/arp-binding).
  if [ -n "${ARP_HOST:-}" ] && [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
    _arp_cfg="$(python3 -c 'import json,sys;from urllib.parse import urlparse;u=urlparse(((json.load(open(sys.argv[1])).get("arp") or {}).get("url") or ""));print(f"{u.hostname}:{u.port}" if u.hostname else "")' "$GW_DIR/gateway_config.json" 2>/dev/null)"
    if [ -n "$_arp_cfg" ] && [ "$_arp_cfg" != "$(printf '%s' "$ARP_HOST" | tr 'A-Z' 'a-z'):$ARP_PORT" ]; then
      echo "  · 주소 드리프트: arp — config 는 $_arp_cfg 인데 ARP_HOST:ARP_PORT 는 $ARP_HOST:$ARP_PORT 다(1f)"
      MISSING="${MISSING:+$MISSING }arp"
    fi
  fi
  # ARP 토큰 — 키(arp)가 있으면 calc_missing 은 '빠짐 없음' 으로 본다. 옛 프로비저너는 arp 를 토큰 없이 등재했고 그 항목이 config 에
  # 남아 있다(cae00). 거기서 ARP_TOKEN 을 처음 적어도, 토큰을 바꿔 적어도 방아쇠가 없어 arp 가 401(가짜 DOWN)인 채 남았다 —
  # "토큰을 적고 update-all" 이 통하지 않았다. 기대하는 박스(주소·토큰 둘 다)에서 config 의 arp 가 이 토큰을 싣고 있지 않으면
  # 재프로비저닝한다(게이트웨이는 env 의 토큰으로 고쳐 쓴다 — 그 뒤에는 조용하다).
  if [ -n "${ARP_TOKEN:-}" ] && [ -n "${ARP_BASE:-}" ] && [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] \
     && _arp_token_drift "$GW_DIR/gateway_config.json"; then
    echo "  · 토큰 드리프트: arp — 게이트웨이 config 의 arp 가 provision.env 의 ARP_TOKEN 을 싣고 있지 않다(토큰 없이 등재됐거나 토큰을 바꿨다)"
    case " $MISSING " in *" arp "*) ;; *) MISSING="${MISSING:+$MISSING }arp" ;; esac
  fi
  # 걷어낼 옛 항목(위 _gw_stale) — 키가 있으니 calc_missing 은 '빠짐 없음' 이고, 기대하지 않는 박스라 위의 어느 드리프트 판정도 보지
  # 않는다. 한 번 재프로비저닝하면 그 항목이 사라져 다음 실행부터 조용하다. 기대 목록(calc_missing 의 want)에는 넣지 않는다 — 게이트웨이가
  # 등재하지 않을 것을 기대하면 매 실행 헛돈다(docs/change-request-8-10 D-4·D-5).
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] && [ -f "$GW_DIR/provision-config.sh" ]; then
    for _k in $(_gw_stale "$GW_DIR/gateway_config.json" "$GW_DIR/provision-config.sh"); do
      if [ "$_k" = arp-keep ]; then
        echo "  · 옛 항목 arp(토큰 없이 등재)는 걷어내지 않는다 — ARP 주소가 게이트웨이 config 에만 있어 빼면 주소까지 잃는다. infra/.env 에 ARP_HOST 를 적으면(1f 가 ARP_BASE 를 적는다) 다음 실행이 걷어낸다"
        continue
      fi
      echo "  · 옛 항목 걷어내기: $_k — 게이트웨이가 더는 등재하지 않는 항목이 config 에 남아 가짜 DOWN 을 낸다"
      MISSING="${MISSING:+$MISSING }${_k}_stale"
    done
  fi
  # ste 사용자 위임 — 게이트웨이 config 에 없거나 시크릿이 infra/.env 와 다르면 재프로비저닝(docs/ste-cae00 D-30).
  # 키(ste)는 있으니 calc_missing 이 못 잡는다. 위임이 한 번 빠지면(예: heax 토큰 자동 발급 실패로 옛 provision 이 통째로 생략)
  # 게이트웨이가 ste 를 토큰 없이 불러 REST 가 401 인 채 남았다 — 도구는 "Error executing tool …", 점검은 전부 초록.
  if [ "${STE_ROUTED:-0}" = 1 ] && [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] && [ -n "${STE_SSO_SECRET:-}" ]; then
    _ste_deleg="$(STE_SSO_SECRET="$STE_SSO_SECRET" GATEWAY_CONFIG="$GW_DIR/gateway_config.json" \
                  python3 "$SELF_REPO/infra/scripts/ste-gateway-check.py" deleg --no-verify --json 2>/dev/null \
                  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("state",""))' 2>/dev/null)"
    case "$_ste_deleg" in
      missing) echo "  · 사용자 위임 드리프트: ste — 게이트웨이 설정에 위임이 없다(토큰 없이 부르고 있다)"; MISSING="${MISSING:+$MISSING }ste" ;;
      stale)   echo "  · 사용자 위임 드리프트: ste — 게이트웨이가 쥔 시크릿이 infra/.env 와 다르다"; MISSING="${MISSING:+$MISSING }ste" ;;
    esac
  fi
  # 한 키를 두 번 적은 PER_USER_SSO_APPS — 먼저 적힌 쌍만 쓴다(_sso_generic_pairs). 방아쇠로 삼지 않고 알리기만 한다: 앞 쌍에 비밀이
  # 없으면 위임이 안 만들어지고 재프로비저닝도 안 돌아, 조용하면 '적었는데 왜 안 켜지나' 를 로그에서 찾을 수 없다. 키만 찍는다 —
  # 쌍점 뒤는 비밀을 잘못 적은 것일 수 있다(docs/change-request-8-10 D-10 #8).
  for _k in $(_sso_generic_pairs dups); do
    bad "사람별 위임 $_k: PER_USER_SSO_APPS 에 두 번 적혔다 — 먼저 적힌 쌍만 쓴다(뒤 쌍의 비밀·주소는 보지 않는다). HWAXMcpGateway/provision.env 에서 한 쌍만 남긴다"
  done
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
    for _k in $(_sso_deleg_drift "$GW_DIR/gateway_config.json"); do
      case "$_k" in
        *_sso_nourl) bad "사람별 위임 ${_k%_sso_nourl}: 비밀은 있는데 위임 주소가 없어 게이트웨이가 만들지 못한다 — HWAXMcpGateway/provision.env 에 그 앱의 <접두>_SSO_URL 을 적는다(PER_USER_SSO_APPS 의 접두)"
                     continue ;;
        # 끄기의 사유와 되돌아가는 곳은 앱마다 다르다. RA·TestScope 의 비밀은 infra/.env 에 있고 끄면 '토큰 등록' 으로 돌아간다. 일반 앱의
        # 비밀은 게이트웨이 provision.env 에 있고, 포털 등록 토큰 길이 없어 끄면 서비스 계정으로 나간다 — 한 문구로 묶으면 일반 앱을 끈
        # 사람이 없는 값을 infra/.env 에서 찾고, 사람별 호출이 서비스 계정으로 바뀐 것을 모른다.
        *_sso_off)
          case "${_k%_sso_off}" in
            reportarchive|testscope) echo "  · 사람별 위임 끄기: ${_k%_sso_off} — infra/.env 의 비밀이 비었는데 게이트웨이는 아직 위임으로 부른다(토큰 등록으로 되돌린다)" ;;
            *) echo "  · 사람별 위임 끄기: ${_k%_sso_off} — HWAXMcpGateway/provision.env 에서 그 앱의 비밀을 비웠거나 PER_USER_SSO_APPS 에서 뺐는데 게이트웨이는 아직 위임으로 부른다(일반 앱은 사람별 호출이 서비스 계정으로 되돌아간다)" ;;
          esac ;;
        *) echo "  · 사람별 위임 드리프트: ${_k%_sso} — 게이트웨이 설정에 위임이 없거나 비밀이 infra/.env 와 다르다(일반 앱은 provision.env 의 비밀·주소)" ;;
      esac
      MISSING="${MISSING:+$MISSING }$_k"
    done
  fi
  # 도는·줄 선 심의가 있으면 이번 실행에서는 재프로비저닝하지 않는다 — 재프로비저닝은 게이트웨이·에이전트서버 재기동까지가 한 벌이고
  # (토큰이 두 설정 파일에 같이 적힌다), 그 재기동이 몇 시간 돈 패널과 줄 선 심의를 말없이 지운다. config 만 고치고 재기동을 빼면
  # 떠 있는 프로세스와 파일이 갈린다 — 통째로 미루고 ○ 로 남긴다. 다음 실행이 같은 어긋남을 다시 본다.
  _reprov_deferred=""
  if [ -n "$MISSING" ] && _dbusy="$(hwax_delib_busy http://127.0.0.1:9009/health)"; then
    hwax_skip "게이트웨이 재프로비저닝 건너뜀" "심의 ${_dbusy% *}건 진행 중, ${_dbusy#* }건 대기 — 고칠 것($MISSING)은 게이트웨이·에이전트서버를 재기동해야 반영되는데 재기동하면 심의가 전부 끊긴다" "심의가 끝난 뒤 update-all 을 다시 돌린다 · 지금 강행하려면 AGENT_RESTART_FORCE=1 을 주고 재실행"
    _reprov_deferred="$MISSING"; MISSING=""
  fi
  if [ -n "$MISSING" ]; then
    echo "  · config에 없거나 주소가 어긋난 백엔드: $MISSING → 재프로비저닝"
    if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/provision-config.sh" ]; then
      # provision.env 는 `. ` 로 소싱만 하므로(export 아님) 자식 프로세스가 못 본다.
      # 그래서 여기서 하나하나 명시해 넘긴다 — ODB_HUB_* 를 빠뜨려서 cae00 에서
      # ODB_HUB_TOKEN 이 설정돼 있는데도 provision 이 '미설정'으로 건너뛰었다(실측).
      # ⚠ 대입어 사슬 **안에** 주석을 두지 않는다 — 백틱 주석(`# …`)은 bash 파서가 명령어 자리로 잡아, 그 뒤의 대입어가
      #   명령 이름이 되어 `RA_MCP_URL=…: No such file or directory`(rc 127) 로 끝난다. 그 모양으로 2026-09-22 부터 이
      #   호출이 **한 번도 실행되지 않았고** 아래 STILL 재검증은 키 존재만 봐 '✓ 재프로비저닝 완료' 를 찍었다(3라운드 검토).
      #   주석은 여기 위에, 대입어는 붙여서, 명령은 마지막에. rc 도 본다.
      #   · RA_MCP_URL — RA 가 원격이면(1e) 이 값이 없을 때 provision 이 127.0.0.1:3002 기본값으로 덮는다.
      #   · ARP_TOKEN — ARP MCP 서비스 토큰(provision.env). 빠뜨리면 토큰을 적어도 arp 가 등재되지 않는데 위 calc_missing 은 기대해, 매 실행 재프로비저닝이 헛돈다.
      #   · STE_SSO_SECRET/STE_*_URL — 없으면 per_user_sso["ste"] 가 안 생겨 ste 도구 호출이 서비스 계정으로 나간다(잡 소유자가 한 명으로 뭉침).
      #   · RA_SSO_* — RA 사람별 위임(docs/sso-delegation). 비면 provision 이 직전 config 를 이어받는다.
      #   · TESTSCOPE_MCP_URL — TestScope 백엔드 주소(provision.env 에서 읽은 값).
      #   · SMARTTWIN_MCP_URL — SmartTwinMCP 주소(provision.env 에서 읽은 값). 빠뜨리면 게이트웨이가 직전 config 의 기본 주소를 이어받지 않아 백엔드를 뺀다.
      #   · TESTSCOPE_SSO_* — TestScope 사람별 위임(RA 와 같은 두 갈래). 비면 토큰 등록 그대로, provision 이 직전 config 를 이어받는다.
      #   · PER_USER_SSO_OFF — 비밀이 빈 RA·TestScope. provision 의 이어받기는 비밀을 못 읽은 실행용이라, 이것 없이는 infra/.env 에서
      #     비밀을 비워도 위임이 남아 포털 화면('토큰 등록')과 게이트웨이가 어긋났다. 여기서는 infra/.env 를 읽었으니 빈 값이 곧 '끔' 이다.
      #   · PER_USER_SSO_APPS 와 그 접두들의 <접두>_SSO_SECRET·_SSO_URL — 일반 앱의 사람별 위임(위 _sso_generic_names). 이름이 박스마다
      #     달라 대입어로 못 적는다 — 서브셸 안에서 export 표지만 붙인다(값을 argv 에 싣지 않는다 — ps 에 보인다). `export` 뒤에는 언제나
      #     PER_USER_SSO_APPS 가 온다 — 인자 없는 export 는 환경 전체(비밀 포함)를 이 로그에 찍는다. 목록에 남기고 비밀만 비운 앱은
      #     RA·TestScope 처럼 PER_USER_SSO_OFF 에 더한다. 목록에서 **뺀** 앱(_sso_generic_unlisted — 순회가 쓴 표지가 붙은 채 남은
      #     위임)의 이름도 더한다 — 게이트웨이는 이름이 와야 끈다(목록이 비었다고 스스로 지우지 않는다).
      _sso_off="$([ -n "${RA_SSO_SECRET:-}" ] || printf 'reportarchive ')$([ -n "${TESTSCOPE_SSO_SECRET:-}" ] || printf 'testscope')"
      _sso_off="$_sso_off$(while read -r _gk _gp; do _gv="${_gp:+${_gp}_SSO_SECRET}"; if [ -n "$_gv" ] && [ -z "${!_gv:-}" ]; then printf ' %s' "$_gk"; fi; done <<<"$(_sso_generic_pairs)")"
      _sso_off="$_sso_off$(for _gk in $(_sso_generic_unlisted "$GW_DIR/gateway_config.json"); do printf ' %s' "$_gk"; done)"
      if ( cd "$GW_DIR" && export PER_USER_SSO_APPS $(_sso_generic_names) && RAT_TOKEN="${RAT_TOKEN:-}" HEAX_MCP_TOKEN="${HEAX_MCP_TOKEN:-}" \
          HEAX_MCP_SERVERS_URL="${HEAX_MCP_SERVERS_URL:-}" HEAX_MCP_BASE="${HEAX_MCP_BASE:-}" \
          ODB_HUB_TOKEN="${ODB_HUB_TOKEN:-}" ODB_HUB_BASE="${ODB_HUB_BASE:-}" \
          ARP_BASE="${ARP_BASE:-}" ARP_TOKEN="${ARP_TOKEN:-}" \
          RA_MCP_URL="${RA_MCP_URL:-}" RA_WORKSPACE_SLUG="${RA_WORKSPACE_SLUG:-}" \
          STE_SSO_SECRET="${STE_SSO_SECRET:-}" STE_MCP_URL="${STE_MCP_URL:-}" \
          STE_SSO_URL="${STE_SSO_URL:-}" \
          RA_SSO_SECRET="${RA_SSO_SECRET:-}" RA_SSO_URL="${RA_SSO_URL:-}" \
          TESTSCOPE_SSO_SECRET="${TESTSCOPE_SSO_SECRET:-}" TESTSCOPE_SSO_URL="${TESTSCOPE_SSO_URL:-}" \
          TESTSCOPE_MCP_URL="${TESTSCOPE_MCP_URL:-}" SMARTTWIN_MCP_URL="${SMARTTWIN_MCP_URL:-}" PER_USER_SSO_OFF="${_sso_off:-}" \
          bash provision-config.sh --force ); then
        _prov_ok=1
      else
        _rc=$?; _prov_ok=0     # 대입 뒤의 $? 는 0 이다 — rc 는 else 첫 명령으로 받아 둔다(4라운드: 매번 '(rc 0)' 으로 찍혔다)
        fail "재프로비저닝(provision-config.sh --force) 자체가 실패했다(rc $_rc) — config 는 옛 값 그대로다. 위 provision 출력을 보라"
      fi
      if [ "$_prov_ok" = 1 ]; then
        "$SVC" down mcp-gateway agent-server 2>/dev/null
        "$SVC" up mcp-gateway agent-server
      else
        echo "  · provision 이 실패해 게이트웨이·에이전트서버는 다시 띄우지 않는다 — 옛 config 로 튕겨 봐야 챗 도구 공백만 생긴다"
      fi

      # 재검증 ① 게이트웨이-에이전트 토큰 정합(레포 배치가 어긋나면 agent가 옛 토큰으로 남는다)
      gwtok="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["_gateway"]["token"])' \
               "$GW_DIR/gateway_config.json" 2>/dev/null)"
      agtok="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["gateway"]["headers"]["Authorization"].split()[-1])' \
               "${AGENT_DIR:-/nonexistent}/mcp_servers.json" 2>/dev/null)"
      if [ -n "$gwtok" ] && [ "$gwtok" = "$agtok" ]; then ok "게이트웨이·에이전트 토큰 정합"
      else bad "게이트웨이·에이전트 토큰 불일치 — $AGENT_DIR/mcp_servers.json 확인(챗이 도구를 못 받는다)"; fi

      # 재검증 ② 재프로비저닝으로 실제 해소됐는지 — 남아 있으면 민팅 실패 등(provision 출력 확인)
      sleep 2; H="$(gw_health)"
      if [ -n "$H" ] && json_ok "$H"; then
        STILL="$(calc_missing "$H")"
        # knox-bridge 는 위에서 이미 ✗ 로 알렸다 — 재프로비저닝이 만들 수 없는 키를 '재프로비저닝 후에도 누락' 으로 다시 세지 않는다.
        STILL="$(for _k in $STILL; do [ "$_k" = knox-bridge ] || printf '%s ' "$_k"; done)"
        STILL="${STILL% }"
        # RA 드리프트는 calc_missing 이 못 본다(키는 있다) — 재프로비저닝 뒤에도 config 의 RA 호스트가 옛 것이면 여기서 잡는다.
        if [ -n "${RA_HOST:-}" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
          _ra_after="$(python3 -c 'import json,sys;from urllib.parse import urlparse;d=json.load(open(sys.argv[1]));print(urlparse(((d.get("reportarchive") or {}).get("url") or "")).hostname or "")' "$GW_DIR/gateway_config.json" 2>/dev/null)"
          [ -n "$_ra_after" ] && [ "$_ra_after" != "$(printf '%s' "$RA_HOST" | tr 'A-Z' 'a-z')" ] && STILL="${STILL:+$STILL }reportarchive(주소 $_ra_after ≠ RA_HOST)"
        fi
        # ARP 토큰도 calc_missing 이 못 본다(키는 있다) — 재프로비저닝 뒤에도 안 실렸으면 게이트웨이가 ARP_TOKEN 을 모르는 옛 판이다.
        if [ -n "${ARP_TOKEN:-}" ] && [ -n "${ARP_BASE:-}" ] && _arp_token_drift "$GW_DIR/gateway_config.json"; then
          STILL="${STILL:+$STILL }arp(토큰 미반영 — 게이트웨이 리포가 ARP_TOKEN 을 싣는 판인지 보라)"
        fi
        # 걷어낼 옛 항목도 calc_missing 이 못 본다(키가 **남은** 것이라) — 재프로비저닝 뒤에도 남았으면 말한다. 조용하면 매 실행 헛돈다.
        for _k in $(_gw_stale "$GW_DIR/gateway_config.json" "$GW_DIR/provision-config.sh"); do
          [ "$_k" = arp-keep ] || STILL="${STILL:+$STILL }$_k(옛 항목이 남았다)"
        done
        # 사람별 위임도 calc_missing 이 못 본다 — 재프로비저닝 뒤에도 어긋나 있으면 여기서 잡는다.
        _sso_left="$(_sso_deleg_drift "$GW_DIR/gateway_config.json")"
        # 주소가 없어 만들지 못하는 일반 앱(…_sso_nourl)은 위에서 이미 알렸다 — 재프로비저닝이 고칠 수 없는 것을 '누락' 으로 다시 세지 않는다.
        _sso_left="$(for _k in $_sso_left; do case "$_k" in *_sso_nourl) ;; *) printf '%s ' "$_k" ;; esac; done)"; _sso_left="${_sso_left% }"
        [ -n "$_sso_left" ] && STILL="${STILL:+$STILL }$_sso_left"
        if [ "${_prov_ok:-1}" != 1 ]; then echo "  · provision 실패는 위 ✗ 하나로 계상한다 — 재검증은 참고만: ${STILL:-없음}"
        elif [ -z "$STILL" ]; then ok "재프로비저닝으로 백엔드 정합 완료"
        else fail "재프로비저닝 후에도 누락/어긋남: $STILL (mxwp 토큰 민팅 실패 등 — 위 provision 출력 확인)"; fi
        if [ -n "$DRIFT" ]; then
          _left="$(python3 "$GW_DIR/provision_urls.py" drift "$GW_DIR/gateway_config.json" "$(dirname "$GW_DIR")" 2>/dev/null || true)"
          [ -z "$_left" ] && ok "주소 드리프트 해소" \
            || bad "재프로비저닝 후에도 주소 드리프트: $(printf '%s' "$_left" | cut -f1 | xargs) — provision.env 의 *_MCP_URL 이 옛 주소를 박고 있지 않은지 확인"
        fi
      fi
    else
      bad "HWAXMcpGateway 레포/provision-config.sh 없음 — 재프로비저닝 불가"
    fi
  else
    if [ "${KNOX_MISSING:-0}" != 1 ] && [ -z "${_reprov_deferred:-}" ]; then ok "config 정합 (빠진 백엔드 없음)"; fi
  fi

  # 등록됐지만 죽어 있는(false) 백엔드 → 해당 서비스만 지정 기동(전 스택 무인자 up 금지 —
  # hands-off RA·vllm 등 의도적으로 내려둔 것을 되살리지 않기 위함). 게이트웨이는 60s 내 자동 재편입.
  DOWN="$(H="$H" python3 -c 'import json,os;h=json.loads(os.environ["H"]);print(" ".join(sorted(k for k,v in (h.get("backends") or {}).items() if not v)))' 2>/dev/null)"
  if [ -n "$DOWN" ]; then
    UP_SVCS=""
    for b in $DOWN; do
      case "$b" in
        # signalforge-mcp 는 웹(:18000)이 아니라 **SignalForge postgres(:5432)에 직결**한다
        # (mcp-server/db.py: postgresql+asyncpg://…/signalforge). 그 postgres 를 띄우는 건
        # signalforge 서비스의 scripts/up.sh 다. MCP 만 띄우면 FastMCP 는 응답하고 health 도
        # 통과하는데 도구 호출은 전량 DB 오류가 된다 — mxwp 와 같은 '초록인데 안 되는' 모양.
        signalforge)    UP_SVCS="$UP_SVCS signalforge signalforge-mcp" ;;
        # ⚠ mxwp-mcp 만 띄우면 안 된다. 브리지는 instance://mxwp_api 안에서 :8800 으로
        #   포워딩할 뿐이라, API 가 죽어 있어도 브리지는 뜨고 health(406)도 통과한다 —
        #   '초록인데 도구는 안 나오는' 상태가 된다. API(:8800)를 함께 띄운다.
        #   tier 가 다르므로(10 vs 15) services.py 가 API → 브리지 순서로 세운다.
        mx-white-paper)
          # 그리고 API 를 되살리려면 **껍데기 인스턴스를 먼저 내려야 한다.** MXWhitePaper
          # start.sh 는 인스턴스 존재만 보고 'mxwp_api already running' 으로 건너뛰는데,
          # 안의 uvicorn 이 죽은 경우가 실제로 있다(2026-09-02: appinit 만 남아 있었고
          # 그대로 up 하면 120초 기다리다 FAIL 했다). 살아 있는데 불건강하면 재활용이 맞다.
          # ⚠ 이 스크립트는 _common.sh 를 source 하지 않는다(36행) — $APPTAINER 를 쓰면
          #   set -u 에서 unbound variable 로 죽는다. 280행처럼 여기서 직접 잡는다.
          _appt="$(ls "$SELF_REPO"/infra/apptainer/bin-*/usr/bin/apptainer 2>/dev/null | tail -1)"
          [ -x "$_appt" ] || _appt="$(command -v apptainer || true)"
          if [ -n "$_appt" ] \
             && [ "$(http_code http://127.0.0.1:8800/api/v1/healthz 3)" != "200" ] \
             && { _il2="$("$_appt" instance list 2>/dev/null || true)"; \
                  case $'\n'"$(printf '%s\n' "$_il2" | awk 'NR>1{print $1}')"$'\n' in \
                    *$'\n'mxwp_api$'\n'*) true ;; *) false ;; esac; }; then
            echo "  · mxwp_api 인스턴스는 있는데 API 가 응답 없음 — 껍데기 인스턴스를 먼저 내린다"
            "$_appt" instance stop mxwp_api >/dev/null 2>&1 || true
            sleep 2
          fi
          UP_SVCS="$UP_SVCS mx-white-paper mxwp-mcp" ;;
        # reportarchive-mcp(:3002)는 RA 백엔드(:3000)로 요청을 넘긴다(mcp_server/server.py
        # REPORTARCHIVE_API_BASE). 그런데 **RA 는 hands-off** 라 자동 기동하지 않는다 —
        # 이 블록이 무인자 up 을 금지하는 이유가 바로 RA·vllm 을 되살리지 않기 위함이다.
        # 대신 MCP 만 띄우고 끝내지 않고, 백엔드가 죽어 있으면 크게 말한다. 안 그러면
        # ':3002 초록 + 호출 전량 실패' 로 끝나고 원인이 안 보인다.
        reportarchive)
          if [ -n "${RA_HOST:-}" ]; then
            # RA 는 다른 서버쌍에서 돈다(1e) — 여기서 띄울 것이 없다(RA 요청서 §3-6). 도달성만 판정해 크게 말한다.
            # 운영자가 RA_HOST 로 "RA 는 저기 있다" 고 선언한 박스다 — 게이트웨이가 못 붙으면 챗의 RA 도구가 전량 죽는다.
            # ste MCP(15812)와 같은 등급으로 **fail** 이다(⚠ 로 두면 '✓ 전체 최신화 완료' 로 끝난다 — 2라운드 검토).
            if [ "$(http_code "http://$RA_HOST:${RA_PORT:-3000}/api/health" 4)" != "200" ]; then
              fail "ReportArchive(원격 $RA_HOST:${RA_PORT:-3000}) /api/health 불통 — 방화벽(:${RA_PORT:-3000}·:${RA_MCP_PORT:-3002})·RA 서버 상태를 RA 담당과 확인"
            else
              fail "RA 백엔드(원격)는 살았는데 게이트웨이가 MCP(:${RA_MCP_PORT:-3002})에 못 붙는다 — RA 서버의 MCP 프로세스·방화벽 :${RA_MCP_PORT:-3002}·provision.env 의 RA_MCP_URL"
            fi
          else
            if [ "$(http_code http://127.0.0.1:3000/api/health 3)" != "200" ]; then
              bad "ReportArchive 백엔드(:3000)가 죽어 있다 — reportarchive-mcp 를 띄워도 호출은 전량 실패한다."
              echo "      RA 는 hands-off 라 자동 기동하지 않는다. 살리려면: $SVC up report-archive"
            fi
            UP_SVCS="$UP_SVCS reportarchive-mcp"
          fi ;;
        # STC MCP(:5012)는 services.yaml 밖이다 — systemd 데몬으로 상시 기동하며
        # dashboard-backend(:5010)를 Wants 한다. 여기서 sudo systemctl 을 부르지 않는다.
        # 할 일을 사람이 바로 알 수 있게 남긴다(전엔 '매핑된 서비스 없음' 만 찍혔다).
        smart-twin-cluster)
          bad "STC MCP(:5012) 다운 — services.yaml 밖(systemd 데몬)이라 여기서 못 살린다."
          echo "      확인: systemctl status mcp-slurm  (없으면 KooSlurmInstallAutomationRefactory/"
          echo "            dashboard/mcp_slurm 의 install_offline.sh · mcp-slurm.service.example 참조)"
          echo "      수동: cd <repo>/dashboard/mcp_slurm && SLURM_MCP_BACKEND=http://127.0.0.1:5010 ./venv/bin/python server.py" ;;
        ai-data-hub)    UP_SVCS="$UP_SVCS ai-data-hub" ;;
        # 심의 MCP(:9009/mcp)는 agent-server 에 내장이다 — 이 백엔드가 죽었다는 건 에이전트 서버가 죽은 것.
        # 살리지 않으면 MCP 클라이언트에서 심의를 시작할 진입점이 도구 목록에서 통째로 사라진다.
        hwax-deliberation) UP_SVCS="$UP_SVCS agent-server" ;;
        # heax-<slug> 는 '앱 하나'가 죽은 것이다. 여기서 heax-hub 통기동으로 접으면 안 된다 —
        # 허브가 살아 있으면 services.py 가 'already-up' 으로 돌려보내 아무것도 안 하고,
        # 화면엔 '✓ heax-hub already-up' 이 찍혀 복구된 것처럼 보인다(무동작을 복구로 표시).
        # 앱 단위 조치를 직접 부른다. 스크립트가 없으면 할 일을 사람이 알 수 있게 남긴다.
        # DynaForge MCP 는 **프록시**다 — heax 앱이 :8701(KooRemapper mcp_server)로 넘긴다.
        # 앱만 재배포하면 프록시는 살아나고 업스트림은 그대로라 '도구는 뜨는데 호출은 실패'가
        # 된다(update-all 자신이 §6에서 그 모양을 설명하고 있다). 업스트림을 함께 띄운다 —
        # kooremapper start.sh 가 :8700 과 :8701 을 같이 세운다. 아래 heax-* 보다 먼저 온다.
        heax-kooremapper_mcp)
          if [ "$(http_code http://127.0.0.1:8701/mcp 3)" = "000" ]; then
            echo "  · DynaForge 업스트림(:8701)이 죽었다 — kooremapper 를 함께 띄운다"
            UP_SVCS="$UP_SVCS kooremapper"
          fi
          _rd="${HEAX_DIR:-}/deploy/apptainer/redeploy-app.sh"
          if [ -x "$_rd" ]; then
            echo "  · heax 앱 kooremapper_mcp 다운 → redeploy-app.sh kooremapper-mcp"
            bash "$_rd" kooremapper-mcp 2>&1 | tail -3 | sed 's/^/      /' \
              || bad "heax 앱 kooremapper_mcp 재배포 실패 — 수동 확인 필요"
          else
            bad "heax 앱 kooremapper_mcp 다운 — redeploy-app.sh 없음($_rd)."
          fi ;;
        heax-*)
          _slug="${b#heax-}"
          _rd="${HEAX_DIR:-}/deploy/apptainer/redeploy-app.sh"
          if [ -x "$_rd" ]; then
            echo "  · heax 앱 $_slug 다운 → redeploy-app.sh $(echo "$_slug" | tr '_' '-')"
            bash "$_rd" "$(echo "$_slug" | tr '_' '-')" 2>&1 | tail -3 | sed 's/^/      /' \
              || bad "heax 앱 $_slug 재배포 실패 — 수동 확인 필요"
          else
            bad "heax 앱 $_slug 다운 — redeploy-app.sh 없음($_rd). 허브 통기동으로는 안 살아난다."
          fi ;;
        # 복구 수단이 없는 다운도 경고로 센다 — echo 한 줄이면 끝 요약에 안 남아 지나친다(5차 요청 §5, 종료코드는 그대로).
        *) bad "다운 백엔드 $b — 매핑된 서비스 없음(수동 확인)" ;;
      esac
    done
    UP_SVCS="$(echo "$UP_SVCS" | xargs -n1 2>/dev/null | sort -u | xargs || true)"
    if [ -n "$UP_SVCS" ]; then
      echo "  · 등록됐지만 다운: $DOWN → 기동: $UP_SVCS (게이트웨이는 60s 내 자동 재편입)"
      "$SVC" up $UP_SVCS
    fi
    # 서비스를 띄운 뒤에도 **게이트웨이가 아는 주소**에 아무것도 없으면, 서비스가 아니라 주소가
    # 틀린 것이다. 재기동을 반복해도 안 고쳐진다 — 그 사실을 사람이 볼 자리에 남긴다.
    # (형제 .env 가 포트를 선언하는 백엔드는 위 드리프트 판정이 이미 자동으로 고쳤다.)
    if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
      for b in $DOWN; do
        _u="$(python3 -c 'import json,sys;print((json.load(open(sys.argv[1])).get(sys.argv[2]) or {}).get("url") or "")' \
               "$GW_DIR/gateway_config.json" "$b" 2>/dev/null)"
        [ -n "$_u" ] || continue
        if [ "$(http_code "$_u" 3)" = "000" ]; then
          bad "$b: 게이트웨이 설정 주소 $_u 에 아무것도 없다(연결 실패) — 서비스가 다른 포트에 떠 있으면 재기동으로는 안 고쳐진다. 게이트웨이 provision.env 에 이 백엔드의 *_MCP_URL 을 명시하고 provision-config.sh --force"
        fi
      done
    fi
  fi
fi

# ── 6) 헬스게이트 — 핵심 체인 실패 시 exit 1로 크게 알림 ──
hr "6) 헬스게이트"
# ⚠ 여기서 FAIL 을 리셋하면 안 된다. 헬스게이트 이전에 세워진 실패(소스 갱신 실패,
# 게이트웨이 시크릿 불일치 등)가 통째로 지워져, 프로브만 통과하면 "✓ 전체 최신화 완료"
# 로 끝나고 exit 0 이 된다 — bad→fail 로 올린 것이 화면 색만 바꾸고 끝났던 이유다.
# 이전 실패를 보존한다.
FAIL="${FAIL:-0}"
probe() { # $1=라벨 $2=URL $3=critical(1/0) $4=허용코드(공백구분)
  local code; code="$(http_code "$2")"
  case " $4 " in
    *" ${code:-000} "*) ok "$1 → $code" ;;
    *) if [ "$3" = 1 ]; then fail "$1 → ${code:-000}  ($2)"; else bad "$1 → ${code:-000}  ($2)"; fi ;;
  esac
}
# 핵심 4종은 전부 무인증 /health — 정상이면 200 외의 코드가 나올 수 없다(401/302는 오설정 신호).
probe "portal-backend :8723" http://127.0.0.1:8723/health 1 "200"
probe "nginx          :8088" http://127.0.0.1:8088/health 1 "200"
probe "agent-server   :9009" http://127.0.0.1:9009/health 1 "200"
probe "gateway        :9110" http://127.0.0.1:9110/health 1 "200"
probe "aidh           :8001" http://127.0.0.1:8001/api/system/health 0 "200"
# ── 관리자 화면을 열 사람이 있는가 — 포털 /health/ready 의 temporary 에 no_active_admin 이 실리면 0명이다 ─────────────────────
# 관리자는 원장의 표지와 PORTAL_ADMIN_EMAILS 만 본다(docs/change-request-8-10 D-3). 관리자를 IdP 그룹으로 받던 박스(mock·oidc)는 이
# 배포로 올라온 순간 관리자 화면을 열 사람이 없어지는데, 위 프로브는 전부 초록이고 배선 설정은 관리자에게만 보인다 — 아무도 모른다.
# **경고**다(bad) — 로그인·챗은 되는 박스라 배포 판정(FAIL)은 건드리지 않는다. 포털이 안 떴거나 응답을 못 읽으면 조용하다
# (위 프로브가 이미 말했다 — 여기서 '0명' 을 지어내지 않는다). 본문은 환경변수로 넘긴다(파이프는 pipefail 아래서 판정을 흔든다).
_rdy="$(curl -s -m 4 http://127.0.0.1:8723/health/ready 2>/dev/null || true)"
if RDY="$_rdy" python3 -c 'import json,os,sys; sys.exit(0 if "no_active_admin" in (json.loads(os.environ["RDY"]).get("temporary") or []) else 1)' 2>/dev/null; then
  bad "포털 관리자      활성 관리자 0명 — 관리자 화면을 열 사람이 없다(원장에 사람은 있다). infra/.env 의 PORTAL_ADMIN_EMAILS 에 관리자로 둘 사람의 로그인 이메일을 적고 포털을 다시 띄운다(비치명)"
fi
# ── 내부 목적지가 프록시를 타지 않는가(9차 요청 §4-(4)) — 이 셸의 NO_PROXY 가 이번 실행이 띄운 서비스가 물려받은 값이다 ──────
# RA·ARP 는 1g 가 더했다. 그 밖에 이 박스가 부르는 다른 서버(라우트의 원격 호스트 · TestScope)가 빠져 있으면 그 호출만 사내 프록시로
# 새 상대의 IP 허용목록에 걸린다 — 기능 하나가 403·Connection error 인데 위 프로브는 전부 초록이다. 목적지는 check-egress.sh 가
# 리포가 아는 설정에서 유도하고 이름으로만 말한다(주소를 여기 적지도, 찍지도 않는다). --internal 은 네트워크를 건드리지 않는다 —
# 상한은 그 약속이 깨졌을 때를 위한 것이다. **경고**다(bad) — 점검이 깨져도 배포 판정(FAIL)은 건드리지 않는다.
if [ -x "$SELF_REPO/infra/scripts/check-egress.sh" ]; then
  _eg_rc=0; _eg="$(timeout --foreground 20 "$SELF_REPO/infra/scripts/check-egress.sh" --internal 2>/dev/null)" || _eg_rc=$?
  case "$_eg_rc" in
    0) ok "프록시 우회      ${_eg:-내부 목적지가 NO_PROXY 에 있다}" ;;
    1) bad "프록시 우회      NO_PROXY 에 없는 내부 목적지: ${_eg:-?} — 그 호출이 사내 프록시로 샌다(상대의 IP 허용목록에 걸리면 403). 운영자 셸의 NO_PROXY 에 그 호스트를 더하고 부르는 서비스를 재기동한다(비치명)" ;;
    *) bad "프록시 우회      check-egress.sh --internal 이 rc $_eg_rc 로 끝나 판정하지 못했다(비치명)" ;;
  esac
else
  hwax_skip "프록시 우회 점검" "check-egress.sh 가 없다(구버전 체크아웃)" "git pull 뒤 재실행"
fi
# 절차 모듈 — 상태코드로는 못 본다. 저장소가 안 열리면 포털은 뜨고 /health 는 200 인데 절차 API 만
# 503 이고, 라우터 등록이 실패하면 SPA catch-all 이 200 HTML 을 돌려준다. 본문으로 판정한다
# (2026-09-17 cae00: 절차가 안 보이는데 모든 게이트가 초록이었다).
PROC_H="$(curl -s -m 4 http://127.0.0.1:8723/procedures-api/health 2>/dev/null || true)"
if printf '%s' "$PROC_H" | grep -q '"ok"[[:space:]]*:[[:space:]]*true'; then
  ok "절차 모듈 → $(printf '%s' "$PROC_H" | tr -d '{}"' | cut -c1-60)"
else
  fail "절차 모듈 미기동 — /procedures-api/health 가 ok:true 가 아니다: $(printf '%s' "$PROC_H" | cut -c1-120)"
fi
# ── RA 포털 로그인(jwt-handoff) 콜백이 **끝까지** 열려 있나 — RA 가 원격인 박스(RA_HOST)만 ────────────────
# 타일 SSO 는 포털 → nginx /report-archive/ → RA :3000 → RA 의 콜백 → 포털 JWKS 검증, 네 조각이 다 서야 한다. 어느 조각이 빠졌는지는
# 콜백에 아무 토큰이나 던져 **상태코드와 본문 모양**으로 갈린다(RA 담당이 준 표, 2026-09-27 — 사람이 curl 로 재던 것을 여기서 찍는다):
#   200 + HTML     → 라우트가 없어 요청이 포털 SPA 로 떨어졌다            (포털 몫: routes.local.env report-archive= · §2 nginx)
#   404 + HTML     → nginx 가 냈다 — 라우트 경로가 어긋났다                 (포털 몫)
#   405            → RA 가 옛 판(콜백 경로 없음)                            (RA 몫: -portal 번들로 RA 서버 update)
#   404 + JSON     → RA 는 새 판인데 포털 SSO 가 꺼져 있다(JWKS 미설정)     (RA 몫: RA .env PORTAL_JWKS_URL=<포털 JWKS> 후 재시작)
#   502/503/504/000→ 포털이 RA_HOST:3000 에 못 닿는다                      (방화벽 :3000 · RA 프로세스)
#   3xx/400/401    → 콜백이 살아 있고 가짜 토큰을 거절했다 = 정상
# RA 몫은 ⚠(bad) — 포털이 고칠 수 없는 것을 ✗ 로 두면 매 실행이 빨갛다. 포털 몫과 불통은 ✗(fail). 숫자는 RA 담당에게 그대로 전한다.
# RA 사용자 위임 점검의 판정 — 포털 /internal/connections 가 게이트웨이 GW_TOKEN 에 준 코드 → "ok|fail<TAB>문구".
# 포털 쪽 정본: backend/app/auth/routes/connections.py internal_connection(503 미설정 · 403 불일치 · 404 미등록).
_ra_conn_verdict() {
  case "$1" in
    404) printf 'ok\tRA 사용자 위임    게이트웨이가 포털 연결 조회에 통과(공유 시크릿 짝 맞음) — 등록한 사람은 본인 명의로 쓴다\n' ;;
    403) printf 'fail\tRA 사용자 위임    게이트웨이 GW_TOKEN ≠ 포털 GATEWAY_SHARED_TOKEN(403) — 지금 신원 있는 RA 호출(읽기·쓰기)이 전부 거부된다. ./infra/scripts/wire-gateway-shared-token.sh 후 포털 재기동\n' ;;
    503) printf 'fail\tRA 사용자 위임    포털에 GATEWAY_SHARED_TOKEN 이 없다(503) — 지금 신원 있는 RA 호출(읽기·쓰기)이 전부 거부된다. ./infra/scripts/wire-gateway-shared-token.sh 후 포털 재기동\n' ;;
    *)   printf 'fail\tRA 사용자 위임    포털 연결 조회 응답 %s — 포털(:8723)이 떠 있는지·이 라우트가 있는지 확인\n' "$1" ;;
  esac
}
_ra_cb_verdict() {  # $1=코드 $2=본문 파일 → "ok|bad|fail<TAB>문구"
  local code="$1" body="$2" jwks="http://${_lan:-<이 박스 주소>}:8088/.well-known/jwks.json" html=0
  grep -qiE '<!doctype html|<html' "$body" 2>/dev/null && html=1
  case "$code/$html" in
    30[1-8]/*|400/*|401/*) printf 'ok\tRA 포털 로그인 콜백 살아 있음(%s) — 라우트·RA 새 판·SSO 켜짐·도달 네 조각이 다 섰다\n' "$code" ;;
    200/1) printf 'fail\tRA 포털 로그인 콜백이 **포털 SPA 로 떨어진다**(200 HTML) — nginx 에 report-archive 라우트가 없다. routes.local.env 의 report-archive= 와 §2 gen-nginx 출력을 보라\n' ;;
    200/0) printf 'bad\tRA 포털 로그인 콜백이 200 을 냈다(리다이렉트가 아니다) — 표에 없는 모양. RA 담당에게 본문을 전한다: %s\n' "$(head -c 120 "$body" 2>/dev/null | tr -d '\n')" ;;
    404/1) printf 'fail\tRA 라우트가 nginx 404 로 끝난다 — 경로가 어긋났다(routes.local.env 의 report-archive= 끝 / 와 §2 nginx 확인)\n' ;;
    404/0) printf 'bad\tRA 는 새 판인데 **포털 SSO 가 꺼져 있다**(404) — RA 담당 몫: RA .env 에 PORTAL_JWKS_URL=%s 를 적고 재시작(그 주소가 RA 서버에서 닿는지 먼저)\n' "$jwks" ;;
    405/*) printf 'bad\tRA 가 **옛 판**이다(콜백 경로 없음, 405) — RA 담당 몫: -portal 번들로 RA 서버 update. 포털은 할 일이 없다\n' ;;
    502/*|503/*|504/*|000/*) printf 'fail\t포털이 RA(%s:%s)에 못 닿는다(%s) — RA 서버 방화벽 :%s · RA 프로세스 상태를 RA 담당과 확인\n' "${RA_HOST:-?}" "${RA_PORT:-3000}" "$code" "${RA_PORT:-3000}" ;;
    *) printf 'bad\tRA 포털 로그인 콜백 응답 %s — 표에 없는 값. RA 담당에게 이 숫자를 전한다\n' "$code" ;;
  esac
}
if [ -n "${RA_HOST:-}" ]; then
  _lan="$(hostname -I 2>/dev/null | awk '{print $1}')"
  _ra_cb_body="$(mktemp)"
  _ra_cb_code="$(curl -s -o "$_ra_cb_body" -w '%{http_code}' -m 8 -X POST "http://127.0.0.1:8088/report-archive/api/auth/portal-callback" -d token=probe-not-a-token 2>/dev/null || echo 000)"
  IFS=$'\t' read -r _ra_cb_lvl _ra_cb_msg <<< "$(_ra_cb_verdict "${_ra_cb_code:-000}" "$_ra_cb_body")"
  case "$_ra_cb_lvl" in ok) ok "$_ra_cb_msg" ;; bad) bad "$_ra_cb_msg" ;; *) fail "$_ra_cb_msg" ;; esac
  echo "      RA 담당에게 줄 숫자: portal-callback → ${_ra_cb_code:-000} · 포털 JWKS: http://${_lan:-<이 박스 주소>}:8088/.well-known/jwks.json"
  rm -f "$_ra_cb_body"
fi
# 서빙 중인 SPA 가 지금 소스로 빌드된 것인가 — dist 는 git 이 아니라 Drive 로 온다. 낡으면 화면이
# 옛 API 를 불러 조용히 깨진다(2026-09-14 워크벤치→절차 개명 뒤 실제로 그랬다). 빌드 때 박아 둔
# frontend 트리 해시와 지금 체크아웃의 트리 해시를 대조한다.
_dist_src="$(cat "$SELF_REPO/frontend/dist/.build-src" 2>/dev/null || true)"
_head_src="$(git -C "$SELF_REPO" rev-parse HEAD:frontend 2>/dev/null || true)"
if [ -z "$_dist_src" ]; then
  bad "SPA dist 에 빌드 표식(.build-src)이 없다 — dev 에서 ./infra/scripts/build-all-to-drive.sh portal 로 다시 빌드해 올린다(비치명)"
elif [ -n "$_head_src" ] && [ "$_dist_src" != "$_head_src" ]; then
  fail "SPA dist 가 지금 소스와 다르다(dist=${_dist_src:0:12} · HEAD=${_head_src:0:12}) — dev 에서 pnpm build + images-to-drive.sh 뒤 다시 배포한다"
else
  ok "SPA dist 가 지금 소스와 같다 (${_head_src:0:12})"
fi
# aidh MCP 드리프트 스모크 — 코드는 최신인데 구버전 프로세스가 살아있는 경우를 감지(비치명 경고).
# 판정 앵커: list_agents 스키마의 compact 파라미터(2026-07 additive 보강)가 tools/list 에 보이는가.
mcpj() { curl -sk -m 4 -X POST http://127.0.0.1:8001/mcp/ \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$1" 2>/dev/null; }
mcpj '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"update-all","version":"1"}}}' >/dev/null
mcpj '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null
AIDH_TL="$(mcpj '{"jsonrpc":"2.0","id":1,"method":"tools/list"}')"
if printf '%s' "$AIDH_TL" | grep -q '"list_agents"'; then
  if printf '%s' "$AIDH_TL" | grep -q '"compact"'; then
    ok "aidh MCP 스키마 최신 (list_agents.compact 노출)"
  else
    bad "aidh MCP 스키마 구버전 — 배포 드리프트 (AIDataHub update.sh 재실행 필요)"
  fi
else
  bad "aidh MCP tools/list 무응답 — /mcp/ 상태 확인 (비치명)"
fi
# heax MCP 앱 실효성 — '등록됨'과 '쓸 수 있음'은 다르다. 앱의 MCP 프로세스가 죽으면 Caddy 가
# 같은 경로에서 앱 정적 HTML 을 200 으로 돌려주고, 레지스트리는 기동 이력만 보므로 계속 노출한다.
# 그러면 게이트웨이에 도구 0개 백엔드가 붙고, 사용자에겐 앱 목록에 이름만 있고 쓸 기능이 없다
# (실측: web_design_agents 가 mcp 2.0 의 fastmcp 제거로 8/3~8/8 죽은 채 등록돼 있었다).
# 앱 하나의 장애로 포털 배포를 막지는 않는다 — 대신 이름과 조치 명령을 찍는다.
# 웹 리서치 브로커 — 이 조직의 유일한 외부 출구다. 조용히 죽으면 "인터넷 검색이 안 되네"로만
# 보이고 원인을 못 찾는다. 전역 모드와 소스 가용성을 함께 찍는다.
WRC="$(curl -s -m 6 http://127.0.0.1:9009/search-capability 2>/dev/null || true)"
if [ -n "$WRC" ]; then
  WRC="$WRC" python3 - <<'PYWR' || true
import json, os
try:
    src = (json.loads(os.environ["WRC"]).get("sources") or {})
except Exception:
    raise SystemExit
if not src:
    print("  \u00b7 \u26a0 \uc6f9 \ub9ac\uc11c\uce58 \uc18c\uc2a4 \uc815\ubcf4 \uc5c6\uc74c \u2014 web-research-mcp \uac00 \uac8c\uc774\ud2b8\uc6e8\uc774\uc5d0 \uc548 \ubd99\uc5c8\uc744 \uc218 \uc788\ub2e4")
    raise SystemExit
on = [k for k, v in src.items() if v.get("available")]
off = [k for k, v in src.items() if not v.get("available")]
print("  \u00b7 \uc6f9 \ub9ac\uc11c\uce58 \uc18c\uc2a4 \u2014 \uc0ac\uc6a9\uac00\ub2a5 %s / \ubbf8\uc81c\uacf5 %s" % (on or "\uc5c6\uc74c", off or "\uc5c6\uc74c"))
if not on:
    print("  \u00b7 \u26a0 \uc778\ud130\ub137 \uac80\uc0c9\uc774 \uc804\ubd80 \uaebc\uc838 \uc788\ub2e4. \uc758\ub3c4\ud55c \uac83\uc774\uba74 \ubb34\uc2dc, \uc544\ub2c8\uba74 web-research-mcp \ub9e4\ub2c8\ud398\uc2a4\ud2b8\uc758 SEARCH_MODE \ub97c \ud655\uc778\ud558\ub77c")
PYWR
fi
TM="$(curl -s -m 6 http://127.0.0.1:9110/tools-map 2>/dev/null || true)"
if [ -n "$TM" ]; then
  TM="$TM" python3 - <<'PY' || true
import json, os
try:
    apps = (json.loads(os.environ["TM"]).get("apps") or [])
except Exception:
    raise SystemExit
heax = [a for a in apps if str(a.get("app", "")).startswith("heax-")]
if not heax:
    print("  · ⚠ heax MCP 앱이 게이트웨이에 하나도 없다 — heax_registry 폴링/PAT 확인")
    raise SystemExit
dead = [a for a in heax if not (a.get("tool_count") or 0)]
print("  · heax MCP 앱 %d개 중 도구 노출 %d개" % (len(heax), len(heax) - len(dead)))
for a in dead:
    slug = str(a["app"])[len("heax-"):]
    print("  · ⚠ %s — 도구 0개(%s). 앱 MCP 프로세스 확인: "
          "infra/scripts/check-mcp-registration.sh %s"
          % (a["app"], "연결안됨" if not a.get("reachable") else "연결됨", slug))
PY
fi
# ⚠ :17370 은 **정적 프론트**라 API 가 죽어도 200 이 나온다(services.yaml 주석에도
#   "프론트(:17370)도 정적이라 /zzz 가 200 이다" 라고 적혀 있다). 그것만 보면 '초록인데
#   안 되는' 판정이 된다. 실제로 무엇이 도는지는 API 헬스가 말한다 — 둘 다 본다.
probe "signalforge    :17370(프론트)" http://127.0.0.1:17370/ 0 "200 302 401"
probe "signalforge    :18000(API)" http://127.0.0.1:18000/health 0 "200"
# searxng — 종전엔 프로브도 복구도 없었다. 죽으면 웹 리서치가 조용히 멈추는데
# update-all 은 아무 말도 안 했다(WEB_PROVIDER=searxng 일 때 앱이 이 주소로만 나간다).
# ⚠ **이 박스 대상인지 먼저 묻는다.** searxng 는 `only_on: smarttwincluster` 라 cae00 엔 없는데,
# 검사 쪽이 그걸 안 보고 두드려 `✗ searxng → 000` 을 찍고 바로 다음 줄에서 복구 쪽이
# "이 박스 대상 아님" 으로 건너뛰었다(2026-09-20 cae00 로그). 한 화면에서 같은 서비스를 두고
# "죽었다" 와 "여기 얘기 아니다" 가 동시에 찍히면, 사람은 그걸 진짜 고장으로 읽는다.
# 판정은 셸에 호스트명 비교를 복제하지 않고 **정본(services.yaml)에 묻는다**.
if "$SVC" enabled searxng; then
  probe "searxng        :8888" http://127.0.0.1:8888/ 0 "200 302"
  if [ "$(http_code http://127.0.0.1:8888/ 4)" = "000" ]; then
    echo "  · searxng 다운 → 기동"
    "$SVC" up searxng || bad "searxng 기동 실패 — 웹 리서치가 막힌다(수동 확인)"
  fi
else
  ok "searxng — 이 박스 대상 아님(services.yaml only_on). 검사하지 않는다."
fi
# Smart Twin Explorer — 백엔드가 이 박스에 없다(헤드노드에 있다). 그래서 둘 다 비치명이다:
# 헤드노드가 꺼져 있거나 망이 닫힌 상태는 포털 배포의 실패가 아니다.
#   ① 헤드노드 백엔드 직결 — /api/health 는 무인증 공개 경로다(update-all 이 토큰 없이 부른다)
#   ② 포털 프록시 경유 — 여기서는 상태코드를 보면 안 된다. nginx location 이 안 붙어도
#      포털 catch-all 이 SPA(index.html)를 200 으로 돌려주므로 코드만으로는 라우트가 먹었는지
#      알 수 없다(실측 확인: 반영 전 /ste/api/health 가 200 + HTML). 그래서 본문을 본다.
# ⚠ 주소는 박스마다 다르다. gen-nginx-conf.sh 는 routes.local.env 오버레이를 반영해 라우트를
#   만드는데, 이 프로브만 base routes.env 를 보면 서로 다른 주소를 검사하게 된다 — cae00 에서
#   오버레이로 바꿔 놔도 dev 주소를 찔러 매번 경고가 뜬다. 같은 우선순위를 쓴다.
#   local 에 `ste=` 를 빈 값으로 두면 '이 박스에서는 STE 를 서빙하지 않음' 이다(라우트도 안 생긴다).
_ROUTES_LOCAL="$SELF_REPO/backend/config/routes.local.env"
if grep -q '^[[:space:]]*ste=' "$_ROUTES_LOCAL" 2>/dev/null; then
  _STE_URL="$(sed -n 's|^[[:space:]]*ste=[[:space:]]*\(.*\)|\1|p' "$_ROUTES_LOCAL" | head -1 | xargs)"
  _STE_SRC="routes.local.env"
else
  _STE_URL="$(sed -n 's|^[[:space:]]*ste=[[:space:]]*\(.*\)|\1|p' "$ROUTES_ENV" 2>/dev/null | head -1 | xargs)"
  _STE_SRC="routes.env"
fi
STE_UP="$(printf '%s' "$_STE_URL" | sed -n 's|^http://\([^/]*\)/\?.*|\1|p')"
if [ -n "$STE_UP" ]; then
  echo "  · ste 주소 출처: $_STE_SRC ($STE_UP)"
  # R4 — cae00 은 ste 헤드노드로 직결 경로가 없어 SSH 터널(127.0.0.1:15810)을 쓴다. 루프백이면 "직결"이
  #   실경로를 오해시키므로 "터널 경유"로 라벨하고, 실패 시 터널 서비스 상태를 힌트로 붙인다.
  case "$STE_UP" in
    127.0.0.1:*|localhost:*|\[::1\]:*)
      _stecode="$(http_code "http://$STE_UP/api/health")"
      if [ "${_stecode:-000}" = "200" ]; then
        ok "ste 백엔드      터널 경유 → $_stecode"
      else
        bad "ste 백엔드      터널 경유 → ${_stecode:-000}  (http://$STE_UP/api/health)"
        echo "    힌트: ste-tunnel = $(systemctl --user is-active ste-tunnel 2>/dev/null || echo unknown)"
        echo "    코드 갱신: 2c) 가 direct 박스는 자동으로 한다. 에어갭(teleport)은 명시 실행이다 —"
        echo "               STE_DEPLOY=1 infra/scripts/deploy-ste.sh  (Drive 스테이징 경유, 런북 §11)"
      fi ;;
    *)
      probe "ste 백엔드      직결" "http://$STE_UP/api/health" 0 "200" ;;
  esac
  # ── ste 자격 중계가 **양쪽 다** 설정됐나 ────────────────────────────────
  # 포털에 로그인하면 ste 도 열리는 기능은 **같은 시크릿을 양쪽이 쥐어야** 성립한다. 포털 쪽은
  # start.sh 가 만들어 채우고, ste 헤드노드 쪽은 2c) 가 `sync-sso-secret.sh` 로 심는다.
  # 여기는 **심은 결과를 판정하는 자리**다 — 심는 쪽과 판정하는 쪽을 갈라 둔다. 같은 코드가
  # 심고 판정하면 "심었다고 했으니 됐다" 가 되고, 실제로 열리는지는 아무도 안 본다.
  #
  # 아무 값이나 보내 **상태코드와 헤더**로 판정한다(비밀을 알 필요도, 남길 필요도 없다).
  #   · 404                         → 엔드포인트는 있는데 시크릿이 없다(그 경로가 꺼져 있다)
  #   · 401 (www-authenticate 없음)  → 핸들러가 틀린 시크릿을 거절했다 = **설정됨**
  #   · 401 (www-authenticate 있음)  → 인증 **미들웨어**가 낸 것이다. 그 경로를 모르는
  #                                    옛 판이 떠 있다는 뜻 → 아직 배포 안 됨
  #
  # ⚠ 처음엔 401 을 그냥 "설정됨" 으로 읽었다가 **가짜 초록**을 낼 참이었다. dev 의 옛 ste 가
  #   그 경로를 몰라 미들웨어 401 을 냈고, 겉모습이 똑같았다. 헤더로 갈라야 한다(실측 확인).
  _ste_sso_hdr="$(curl -s -D - -o /dev/null -m 4 -X POST \
      -H 'X-Heax-Gateway-Secret: probe-not-a-secret' -H 'X-Heax-User-Email: probe@invalid' \
      "http://127.0.0.1:8088/ste/api/auth/sso" 2>/dev/null || true)"
  _ste_sso_code="$(printf '%s' "$_ste_sso_hdr" | sed -n 's|^HTTP/[0-9.]* \([0-9]*\).*|\1|p' | tail -1)"
  if printf '%s' "$_ste_sso_hdr" | grep -qi '^www-authenticate:'; then _ste_sso_mw=1; else _ste_sso_mw=0; fi
  case "${_ste_sso_code:-000}/$_ste_sso_mw" in
    401/0) # 1차: 핸들러가 살아 있고 시크릿이 **어떤 값이든** 설정돼 있다. 그런데 이것만으로는
           # **포털과 같은 값인지** 모른다 — 포털 start.sh 와 헤드 installer 가 각자 난수를 만드므로
           # 불일치는 정상 경로에서 생기고, 그 상태면 "로그인은 되는데 ste 만 401" 인 채로 초록이었다
           # (2026-09-24 적대 검토). 그래서 2차로 **실제 값**을 verify 에 친다(루프백 8088 — 박스 밖으로
           # 안 나간다). 204 = 같다 · 401 = 다르다 · 404 = 헤드에 verify 가 없는 옛 판.
           if [ -n "${STE_SSO_SECRET:-}" ]; then
             # 시크릿은 argv 로 넘기지 않는다(ps 에 보인다) — curl 설정을 stdin 으로 준다(-K -).
             _ste_vfy="$(printf 'header = "X-Heax-Gateway-Secret: %s"\n' "$STE_SSO_SECRET" \
                 | curl -s -o /dev/null -w '%{http_code}' -m 4 -X POST -K - \
                 "http://127.0.0.1:8088/ste/api/auth/sso/verify" 2>/dev/null || echo 000)"
             case "$_ste_vfy" in
               204) ok "ste 자격중계    양쪽 설정됨 **그리고 같은 값** (verify 204)" ;;
               401) fail "ste 자격중계    **양쪽 시크릿이 다르다**(verify 401) — 로그인은 되는데 ste 만 401 인 상태"
                    echo "    맞추기: FORCE_SSO_SECRET=1 SmartTwinExplorer/deploy/sync-sso-secret.sh  (포털 값으로 덮는다)" ;;
               404) bad "ste 자격중계    설정은 됐는데 헤드 판이 verify 를 모른다(404) — 일치 여부 미확인. 헤드 코드 갱신 뒤 다시 본다" ;;
               *)   bad "ste 자격중계    verify 응답 $_ste_vfy — 일치 여부 미확인" ;;
             esac
           else
             bad "ste 자격중계    핸들러는 살아 있는데 포털 쪽 값이 비어 일치 여부를 못 본다"
           fi ;;
    401/1) fail "ste 자격중계    ste 에 **옛 판이 떠 있다** — /api/auth/sso 를 모른다(미들웨어가 401)"
           echo "    (cae00) infra/scripts/deploy-ste.sh — Drive 스테이징의 새 코드를 헤드노드에 반영" ;;
    404/*) fail "ste 자격중계    **ste 헤드노드에 시크릿이 없다**(404) — 포털 로그인으로 ste 가 열리지 않는다"
           echo "    (cae00) SmartTwinExplorer/deploy/refresh-code.sh 가 포털 infra/.env 의 값을 헤드에 심는다" ;;
    000/*) bad "ste 자격중계    확인 못 함(프록시 무응답) — 위 ste 라우트 항목을 먼저 본다" ;;
    *)     bad "ste 자격중계    예상 못 한 응답 ${_ste_sso_code:-000} — 401/404 가 아니다" ;;
  esac
  if [ -z "${STE_SSO_SECRET:-}" ]; then
    fail "ste 자격중계    **포털 쪽 시크릿이 비었다** — 포털을 재기동하면 start.sh 가 만든다"
  fi

  # R1 — 프록시 프로브는 본문만 보면 서로 다른 실패(라우트 미반영 vs upstream 도달불가)를 한
  #   메시지로 뭉갠다. 상태코드로 분기해 오진을 막는다.
  STE_RESP="$(curl -s -m 4 -w '\n%{http_code}' http://127.0.0.1:8088/ste/api/health 2>/dev/null || true)"
  STE_CODE="${STE_RESP##*$'\n'}"; STE_BODY="${STE_RESP%$'\n'*}"
  if printf '%s' "$STE_BODY" | grep -q 'smart-twin-explorer'; then
    ok  "ste 프록시      :8088 → 백엔드 응답 확인"
  elif [ -z "$STE_CODE" ] || [ "$STE_CODE" = "000" ] || { [ "$STE_CODE" -ge 502 ] 2>/dev/null; }; then
    bad "ste 프록시      :8088 → upstream($STE_UP) 도달 불가 [$STE_CODE]. nginx 라우트는 정상. 비치명"
  else
    bad "ste 프록시      :8088 → 포털 SPA 가 돌아온다 (nginx /ste/ location 미반영, 비치명)"
  fi
elif [ "$_STE_SRC" = "routes.local.env" ]; then
  ok "ste — 이 박스에서는 서빙 안 함(routes.local.env 에서 비활성). 라우트도 만들지 않는다."
else
  hwax_skip "ste(SmartTwinExplorer)" "라우트 미설정 — routes.local.env 에 ste= 가 없어 프록시·자격중계·MCP 위임을 셋업하지 않았다" "teleport 박스: 1d 자동 기록(HWAX_STE_AUTOROUTE=1 기본, transport.env 필요) · direct 박스: routes.local.env 에 ste=http://<헤드>:15810/ 를 적고 재실행"
fi
H="$(gw_health)"
if [ -n "$H" ] && json_ok "$H"; then
  H="$H" python3 - <<'PY'
import json, os
h = json.loads(os.environ["H"])
backends = h.get("backends") or {}
parts = " ".join(k + "=" + ("up" if v else "DOWN") for k, v in sorted(backends.items()))
print(f"  · gateway {h.get('tools')} tools | {parts}")
# HEAX Hub 앱은 heax_registry 폴링으로 heax-* 백엔드로 동적 발견된다 — 하나도 없으면 등록/폴링 문제.
heax = {k: v for k, v in backends.items() if k.startswith("heax") and k != "heax_registry"}
if heax:
    print("  · HEAX Hub 앱 발견: " + ", ".join(f"{k}={'up' if v else 'DOWN'}" for k, v in sorted(heax.items())))
elif "heax_registry" in backends:
    print("  · ⚠ HEAX Hub 앱 0개 발견 — heax_registry 는 있으나 폴링이 앱을 못 찾음(레지스트리에 앱 미등록/미기동?). 챗에 열충격·재료·적층 도구가 안 뜬다.")
else:
    print("  · ⚠ HEAX Hub 앱 0개 — heax_registry 미구성(열충격·재료·적층 도구 없음).")
    print("      §5 가 heax-hub 에서 MCP 토큰을 자동 발급해 heax_registry 를 만드는데 실패했을 수 있다:")
    print("      heax-hub 백엔드(:4040)·DB 기동과 admin 유저 존재를 확인하라(provision-config.sh 로그의")
    print("      'heax MCP 토큰' 라인). 최후 수동: provision.env 에 HEAX_MCP_TOKEN 설정 후 재실행.")
PY
  # ── ste 가 이 박스에서 쓰이면(STE_ROUTED=1) 게이트웨이 ste 백엔드가 **떠 있어야** 한다 ──────
  # /health.backends[k] 는 DOWN 이어도 **키는 남고 값만 false** 다. §5 는 키 유무만 봐서 "빠진 백엔드
  # 없음" 을 내고, DOWN 분기는 "매핑된 서비스 없음(수동 확인)" 에 그친다 — 그래서 cae00 에서 ste MCP 가
  # 죽어 있어도 exit 0 이었다(2026-09-24 적대 검토). 여기서 값을 보고 fail 을 세운다.
  if [ "${STE_ROUTED:-0}" = 1 ]; then
    _ste_gw="$(H="$H" python3 -c 'import json,os;b=(json.loads(os.environ["H"]).get("backends") or {});print("up" if b.get("ste") is True else ("absent" if "ste" not in b else "down"))' 2>/dev/null || echo unknown)"
    case "$_ste_gw" in
      up)     ok "ste MCP         게이트웨이가 ste 백엔드에 붙어 있다 (도구 8종)" ;;
      down|absent)
        # 원인 대부분은 게이트웨이가 ste MCP(:15812)에 못 닿는 것이다. cae00 은 SSH 터널이라
        # 15810 만 열고 15812 를 안 열면 **정확히 이 모양**이다 — 그래서 포트를 직접 찔러 가른다.
        # 살아 있으면 GET /mcp 가 406(Accept 없음) 또는 200, 죽었으면 000 (dev 실측).
        # `|| echo 000` 을 붙이지 않는다 — curl 은 연결 실패에도 -w 로 이미 000 을 찍어 둘이 겹쳐 '000000' 이 됐다(사용자 화면 실측).
        _mcp_probe="$(curl -s -o /dev/null -w '%{http_code}' -m 4 "${STE_MCP_URL:-http://127.0.0.1:15812/mcp}" 2>/dev/null)" || true
        _mcp_probe="${_mcp_probe:-000}"
        case "$_mcp_probe" in
          200|405|406) fail "ste MCP         :15812 는 살아 있는데 게이트웨이 ste 백엔드가 $_ste_gw — 게이트웨이 재기동 필요(정적 백엔드는 /refresh 로 안 붙는다)" ;;
          *) fail "ste MCP         ${STE_MCP_URL:-http://127.0.0.1:15812/mcp} 에 아무것도 없다($_mcp_probe) — ste 도구 8종이 통째로 안 뜬다"
             case "${STE_MCP_URL:-}" in *127.0.0.1*|*localhost*)
               # §2d 가 이미 터널을 세우려 시도했다. 그래도 000 이면 남은 원인은 로컬 리스너 유무로 갈린다 —
               # 리스너가 없으면 터널이 그 포트를 못 열었고(§2d 출력), 있으면 헤드에서 15812 로 가는 연결이 거부된 것이다.
               echo "    (cae00) §2d 가 터널을 세우려 했는데도 000 이다. 로컬 리스너: $(ss -ltn 2>/dev/null | grep -c '127.0.0.1:15812 ')개"
               echo "    · 0개면 터널이 그 포트를 못 열었다 — 위 §2d 의 journal·'유닛이 아닌 pid' 줄을 보라"
               echo "    · 1개면 헤드에서 127.0.0.1:15812 로 가는 연결이 거부됐다 — 진단 한 화면: ./infra/scripts/ste-doctor.sh"
               echo "      (그 화면이 헤드의 listen 주소와 '헤드 자기 자신 curl /mcp' 결과를 같이 보여 준다)" ;;
             esac ;;
        esac ;;
      *) bad "ste MCP         게이트웨이 /health 를 못 읽어 판정 불가" ;;
    esac
    # ── 게이트웨이의 ste 사용자 위임·사람 신분 실호출(docs/ste-cae00 D-30) ────────────────────────────
    # 위 '자격중계' 는 **포털**의 시크릿이다. 게이트웨이는 provision 때 복사한 값을 쥔다 — 위임이 없거나 값이 갈리면
    # ste 도구가 "Error executing tool …" 로 실패하는데 위 항목은 전부 초록이었다. 실호출은 그 사람 명의로 ste 토큰을
    # 받으므로 이메일이 있어야 한다 — 없으면 안 켠 기능으로 남긴다.
    if [ "$_ste_gw" = up ]; then
      _dj="$(STE_SSO_SECRET="${STE_SSO_SECRET:-}" GATEWAY_CONFIG="${GW_DIR:-/nonexistent}/gateway_config.json" \
             python3 "$SELF_REPO/infra/scripts/ste-gateway-check.py" deleg --json 2>/dev/null)"; _drc=$?
      _dd="$(printf '%s' "$_dj" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("detail",""))' 2>/dev/null)"
      case "$_drc" in
        0) ok "ste 사용자 위임  게이트웨이 설정 있음 · $_dd" ;;
        1) fail "ste 사용자 위임  $_dd" ;;
        *) bad "ste 사용자 위임  판정 불가 — ${_dd:-ste-gateway-check.py 출력 없음}" ;;
      esac
      _probe_as="$(_ra_envv HWAX_STE_PROBE_EMAIL)"
      _mcppy="${AGENT_DIR:+$AGENT_DIR/.venv/bin/python}"
      if [ -z "$_probe_as" ]; then
        hwax_skip "ste 사람 신분 실호출" "infra/.env 에 HWAX_STE_PROBE_EMAIL 이 없어 잡 목록·cluster_info 를 사람 명의로 불러 보지 않았다(토큰 경로·slurm 경로 미확인)" "infra/.env 에 HWAX_STE_PROBE_EMAIL=<ste 권한이 있는 본인 이메일>"
      elif [ ! -x "${_mcppy:-/nonexistent}" ]; then
        bad "ste 사람 신분   mcp 모듈이 있는 python(${_mcppy:-HWAXAgentServer/.venv})을 못 찾아 실호출을 못 했다"
      else
        _pj="$(GATEWAY_CONFIG="${GW_DIR:-/nonexistent}/gateway_config.json" "$_mcppy" "$SELF_REPO/infra/scripts/ste-gateway-check.py" probe --as "$_probe_as" --json 2>/dev/null)"
        while IFS=$'\t' read -r _pk _pv _pd; do
          [ -n "$_pk" ] || continue
          if [ "$_pv" = ok ]; then ok "ste 사람 신분   $_pk — $_probe_as 로 실호출 성공 $_pd"
          else fail "ste 사람 신분   $_pk — $_probe_as: $_pv $_pd"; fi
        done <<<"$(printf '%s' "$_pj" | python3 -c '
import json,sys
d=json.load(sys.stdin)
if d.get("error"): print("접속\tfail\t"+d["error"][:300])
for s in d.get("steps",[]):
    print(("토큰 경로" if s["what"]=="token" else "slurm 경로")+"\t"+s["verdict"]+"\t"+(s.get("detail") or "").replace("\t"," ")[:300])
' 2>/dev/null)"
        [ -n "$_pj" ] || fail "ste 사람 신분   ste-gateway-check.py probe 가 아무것도 내지 않았다"
      fi
    fi
  fi
  # ── 포털 권한 정책이 게이트웨이에 **실려 있어야** 한다 ────────────────────────────────
  # 안 실리면 `_backend_allowed` 가 정책 없음 = 전원 허용으로 판정한다. 그 상태에서 per_user 백엔드
  # (ste·kooremapper)를 부르면 시크릿을 쥔 게이트웨이가 **임의 이메일로 계정을 JIT 생성**한다.
  # 새 클론(캐시 파일 없음)·옛 포털(404) 에서 생기고, 아무도 이 값을 안 봤다.
  _pol="$(H="$H" python3 -c 'import json,os;print(int(json.loads(os.environ["H"]).get("access_policy_loaded") or 0))' 2>/dev/null || echo -1)"
  if [ "$_pol" = "0" ]; then
    fail "권한 정책        게이트웨이에 포털 권한 정책이 **안 실렸다**(access_policy_loaded=0) — 전 백엔드가 전원에게 열린다"
    echo "    포털 /internal/access/policy 가 200 인지, 게이트웨이가 GATEWAY_SHARED_TOKEN 으로 그것을 받는지 본다(60초마다 재시도)"
  fi
  # ── 이 박스의 게이트웨이 백엔드가 **전부** 권한 표(access.yaml)에 있어야 한다 ─────────────────────
  # 표에 없는 백엔드는 allowed_groups 가 비면 **아무나**, 있으면 그 키를 발급할 수 없어 **아무도** 못 쓴다(2026-10-01 cae00:
  # simflow 도구 21개 전원 공개 · plm-defect 전원 차단, 5차 요청 §2). CI 시험은 dev 백엔드만 본다 — cae00 에만 있는 백엔드는 여기서만
  # 잡힌다. 대조 상대는 게이트웨이의 60초 캐시가 아니라 **포털의 지금 표**다(방금 표를 고친 실행이 옛 캐시로 빨개지지 않게).
  if [ -n "${GW_DIR:-}" ] && [ -f "$GW_DIR/gateway_config.json" ]; then
    # 시크릿은 argv 에 싣지 않는다 — curl 설정을 stdin(-K -)으로 준다
    _apol="$(python3 -c 'import json,sys;print("header = \"Authorization: Bearer %s\"" % json.load(open(sys.argv[1]))["_gateway"]["token"])' \
               "$GW_DIR/gateway_config.json" 2>/dev/null \
             | curl -s -m 5 -K - http://127.0.0.1:8723/internal/access/policy 2>/dev/null || true)"
    _unlisted="$(H="$H" P="$_apol" python3 -c '
import json, os
pol = (json.loads(os.environ["P"]) or {}).get("backends")
if not isinstance(pol, dict): raise SystemExit(1)
print(" ".join(sorted(set(json.loads(os.environ["H"]).get("backends") or {}) - set(pol))))' 2>/dev/null)" || _unlisted="?"
    case "$_unlisted" in
      "?") bad "권한 표 대조     포털 /internal/access/policy 를 못 읽었다(공유 시크릿·포털 상태) — 표에 없는 백엔드를 못 본다" ;;
      "")  ok "권한 표 대조     게이트웨이 백엔드가 전부 access.yaml 에 있다" ;;
      *)   fail "권한 표 구멍     access.yaml 에 없는 게이트웨이 백엔드: $_unlisted — 아무나 쓰거나 아무도 못 쓴다"
           echo "    backend/config/access.yaml 의 플랫폼 gateway: 에 더한다(재기동 불필요 — 게이트웨이가 60초 안에 받는다)"
           echo "    이 박스에만 있는 백엔드면 추적 파일 대신 backend/config/access.local.yaml(gitignore 오버레이)에 적는다" ;;
    esac
  else
    hwax_skip "권한 표 대조" "게이트웨이 리포(gateway_config.json)를 못 찾았다 — 공유 시크릿 없이는 포털 정책을 못 읽는다" "HWAXMcpGateway 를 형제 리포로 두고 재실행"
  fi
  # ── RA 사용자 위임 — 게이트웨이가 포털에 '이 사람의 RA 토큰' 을 물을 수 있어야 한다 ───────────────
  # 못 물으면 연결을 등록한 사람의 RA 글도 서비스 토큰 주인 명의로 올라갔다(2026-09-29 — config 의 portal.api_base 가
  # --force 로 사라져 게이트웨이가 묻지도 않았다). 지금 게이트웨이는 못 물으면 RA 호출을 **거부**한다 — 그래서 배포가
  # 공유 시크릿 짝(게이트웨이 GW_TOKEN = 포털 GATEWAY_SHARED_TOKEN)을 직접 본다. 없는 이메일로 물어 404 면 통과다.
  if [ -n "${GW_DIR:-}" ] && [ -f "$GW_DIR/gateway_config.json" ] \
     && python3 -c 'import json,sys;sys.exit(0 if "reportarchive" in json.load(open(sys.argv[1])) else 1)' "$GW_DIR/gateway_config.json" 2>/dev/null; then
    # 게이트웨이가 실제로 묻는 주소 — gateway.py _portal_api_base() 와 같은 규칙(api_base, 없으면 jwks_url 의 origin)
    _conn_base="$(python3 -c 'import json,re,sys;p=json.load(open(sys.argv[1])).get("portal") or {};b=p.get("api_base");m=re.match(r"^(https?://[^/]+)",p.get("jwks_url") or "");print(str(b).rstrip("/") if b else (m.group(1) if m else ""))' \
                    "$GW_DIR/gateway_config.json" 2>/dev/null)"
    # 시크릿은 argv 에 싣지 않는다 — curl 설정을 stdin(-K -)으로 준다
    _conn_code="$(python3 -c 'import json,sys;print("header = \"Authorization: Bearer %s\"" % json.load(open(sys.argv[1]))["_gateway"]["token"])' \
                    "$GW_DIR/gateway_config.json" 2>/dev/null \
                  | curl -s -o /dev/null -w '%{http_code}' -m 5 -K - \
                      "${_conn_base:-http://127.0.0.1:8723}/internal/connections/reportarchive?email=hwax-probe%40invalid" 2>/dev/null)"
    IFS=$'\t' read -r _cv _ct <<<"$(_ra_conn_verdict "${_conn_code:-000}")"
    # 짝이 맞아도 떠 있는 게이트웨이가 옛 판이면(§4 의 갱신 실패 — 살아 있으면 재기동을 생략한다) 못 물을 때 조용히
    # 공용 토큰으로 폴백한다. ✓ 는 두 조건이 다 설 때만 — §4 뒤에는 디스크 코드가 떠 있는 코드다(지문·리스너 판정).
    if [ "$_cv" = ok ] && ! grep -q '_ConnLookupError' "$GW_DIR/gateway.py" 2>/dev/null; then
      _cv=fail; _ct="RA 사용자 위임    공유 시크릿 짝은 맞지만 게이트웨이가 옛 판이다(못 물으면 공용 토큰으로 폴백) — §4 의 mcp-gateway 갱신 실패부터 고친다"
    fi
    case "$_cv" in ok) ok "$_ct" ;; *) fail "$_ct" ;; esac
  else
    hwax_skip "RA 사용자 위임 점검" "게이트웨이 config 에 reportarchive 백엔드가 없다(또는 게이트웨이 리포를 못 찾았다)" "RA 에서 PAT(rat_…)를 발급해 HWAXMcpGateway/provision.env 에 RAT_TOKEN=<값> 을 적고 재실행(§5)"
  fi
  # ste 관련 빨강이 하나라도 있으면 한 화면 진단을 가리킨다 — 항목마다 어떻게 쟀는지까지 찍는다.
  if [ "${STE_ROUTED:-0}" = 1 ] && printf '%s' "${FAIL_ITEMS:-}" | grep -q "ste"; then
    echo "    진단 한 화면: ./infra/scripts/ste-doctor.sh   (--report 로 JSON)"
  elif [ "$_pol" != "-1" ]; then
    ok "권한 정책        게이트웨이에 백엔드 ${_pol}개분 적재됨"
  fi
fi

# heax-hub dist base 검증 — 앱 '열기'는 window.open(BASE_URL + '/apps/<id>/') 로 열린다.
# dist 가 base=/ 로 잘못 빌드되면 BASE_URL=/ → '/apps/<id>/' 로 포털 루트에서 열려 404 가 난다
# (정상은 base=/heax-hub/ → '/heax-hub/apps/<id>/'). 서빙 HTML 의 자산 경로로 base 를 판정한다.
HH="$(curl -s -m 4 http://127.0.0.1:4180/ 2>/dev/null || true)"
if [ -n "$HH" ]; then
  if printf '%s' "$HH" | grep -q '/heax-hub/assets/'; then
    ok "heax-hub dist base=/heax-hub/ — 앱 '열기' 링크 정상"
  elif printf '%s' "$HH" | grep -q '"/assets/\|src="/assets'; then
    bad "heax-hub dist base=/ 로 잘못 빌드 — 앱 '열기'가 /apps/<id>/ 로 열려 포털 루트 404."
    echo "      해결: (빌드호스트) VITE_BASE_PATH=/heax-hub/ pnpm --dir frontend build →"
    echo "            build-all-to-drive.sh heax → cae00 에서 deploy-all-from-drive.sh 재배포."
  fi
fi

# 호스팅 웹앱 실제 서빙 프로브 — MCP 앱(thermal_shock·laminate)은 위 gateway backend 로 판정되지만,
# 순수 웹앱(materialtwin_web·voice_recorder)은 Caddy 가 /apps/<id>/ 로 직접 서빙해 게이트웨이엔
# 안 잡힌다. SIF 교체 후 앱 인스턴스가 미기동이면 여기서 404 로 잡힌다(과거엔 루트만 봐서 조용히 통과).
# reconcile 이 부팅 직후 도는 데 시간이 걸릴 수 있어 몇 번 재시도.
# 과거엔 (a) 하드코딩한 2개만, (b) Caddy(:4180) 직접만, (c) HTML 루트만 봤다. 그래서 실제
# 파손 — 브라우저가 요청하는 자산이 nginx(:8088)에서 포털 SPA 로 떨어져 JS 자리에 HTML 이
# 200 으로 오던 것 — 을 전부 통과시켰다. 이제 (a) 등록된 앱 전체를, (b) 사용자와 같은
# nginx 경유로, (c) 첫 자산까지 받아 Content-Type 이 HTML 로 바뀌지 않는지 본다.
# 경로를 하드코딩하면 안 된다 — cae00 은 ~/Projects/HEAXHub 라 여기가 어긋나 폴백 목록
# ("materialtwin_web voice_recorder") 2개만 검사했다(cae00 실행 로그로 확인).
HEAX_STATE_DIR="${HEAX_STATE_DIR:-${HEAX_DIR:-$HOME/claude/HEAXHub}/var/integration_state}"
heax_apps=""
[ -d "$HEAX_STATE_DIR" ] && heax_apps="$(ls "$HEAX_STATE_DIR"/*.json 2>/dev/null | while read -r f; do basename "$f" .json; done)"
[ -n "$heax_apps" ] || heax_apps="materialtwin_web voice_recorder"

# ── 외부 MCP 카탈로그 최신화 ─────────────────────────────────────────────────
# 앱을 재배포해도 게이트웨이 카탈로그는 재활 주기(기본 60s)가 돌아야 바뀐다. 그 전에
# 판정하면 **옛 도구 목록으로 초록을 찍는다.** 실제로 그렇게 놓쳤다 — StepForge 가 intake·
# set_project_meta 를 추가했는데 배포된 SIF 가 낡아 게이트웨이에 없었고, 포털이 그 도구를
# 부르다 'unknown tool: intake' 로 터졌다(2026-09-01).
#
# 그래서 여기서 즉시 갱신시키고(POST /refresh — 주기 루프와 같은 코드), 무엇이 늘고
# 줄었는지 **도구 이름으로** 보고한다. 수만 보면 1개 추가 + 1개 삭제가 '변화 없음'이 된다.
# 트리거가 없는 옛 게이트웨이면 한 주기를 기다렸다가 넘어간다(기능 저하 없이 동작).
_tm_snapshot() { curl -s -m 6 http://127.0.0.1:9110/tools-map 2>/dev/null || true; }
TM_BEFORE="$(_tm_snapshot)"
GW_TOK="$(python3 - "$GW_DIR/gateway_config.json" <<'PY' 2>/dev/null || true
import json, sys
try: print(json.load(open(sys.argv[1]))["_gateway"].get("token", ""))
except Exception: pass
PY
)"
if [ -n "$GW_TOK" ]; then
  # ⚠ 타임아웃을 넉넉히 잡는다. /refresh 는 백엔드마다 liveness(10s) + 재연결(10s)을 쓸 수
  #   있어 14개가 모두 불통이면 최악 280s 다 — 그리고 **배포 직후가 정확히 그 상황**이라
  #   이 스크립트가 가장 자주 만나는 조건이다. 90s 로 자르면 성공할 갱신을 '실패'로 보고
  #   폴백 sleep 까지 더 하게 된다(느려지고 결과도 틀린다).
  RF="$(curl -s -m "${GATEWAY_REFRESH_TIMEOUT:-300}" -X POST -H "Authorization: Bearer $GW_TOK" \
        http://127.0.0.1:9110/refresh 2>/dev/null || true)"
  if [ -n "$RF" ] && json_ok "$RF"; then
    echo "  · MCP 카탈로그 갱신: $(RF="$RF" python3 -c '
import json, os
d = json.loads(os.environ["RF"])
if not d.get("ok"): print("실패 —", d.get("error", "?")); raise SystemExit
down = [k for k, v in (d.get("backends") or {}).items() if not v]
# f-string 안 \" 는 셸 홑따옴표 래핑을 거치면 SyntaxError 다(cae00 실측) — 문자열 조립로 회피.
msg = "도구 %s→%s" % (d.get("tools_before"), d.get("tools"))
if d.get("changed"): msg += " (변화 있음)"
if down: msg += " · 불통 백엔드 %d: %s" % (len(down), " ".join(sorted(down)))
print(msg)')"
  else
    echo "  · /refresh 미지원 또는 실패 — 재활 주기를 기다린다(${GATEWAY_REVIVE_WAIT:-65}s)"
    sleep "${GATEWAY_REVIVE_WAIT:-65}"
  fi
else
  echo "  · 게이트웨이 토큰을 못 읽어 카탈로그 갱신을 생략했다(gateway_config.json 확인)"
fi

# MCP 노출 앱은 /apps/<id>/ 루트 코드로 판정할 수 없다 — MCP 는 하위경로(/mcp)라 루트가
# 404/401 인 게 정상이다(실측: kooremapper_mcp·web_research_mcp 404, laminate·thermal 401).
# 그래서 게이트웨이 /tools-map 의 도구 수로 본다. DynaForge 처럼 프록시 대상 업스트림이
# 죽으면 '등록은 멀쩡한데 도구가 0개'가 되는데, 루트 코드만 보면 이걸 영영 못 잡는다.
TM="$(_tm_snapshot)"

# 갱신 전후 도구 **이름** 차이 — 외부 MCP 가 무엇을 새로 내놓았고 무엇을 거뒀는지.
if [ -n "$TM_BEFORE" ] && [ -n "$TM" ] && json_ok "$TM_BEFORE" && json_ok "$TM"; then
  BEFORE_TM="$TM_BEFORE" AFTER_TM="$TM" python3 - <<'PY' | sed 's/^/  /'
import json, os
a = json.loads(os.environ["BEFORE_TM"]).get("map") or {}
b = json.loads(os.environ["AFTER_TM"]).get("map") or {}
added, gone = sorted(set(b) - set(a)), sorted(set(a) - set(b))
if not added and not gone:
    raise SystemExit
by = {}
for n in added: by.setdefault(b[n], {"+": [], "-": []})["+"].append(n)
for n in gone:  by.setdefault(a[n], {"+": [], "-": []})["-"].append(n)
print("· 도구 변화:")
for bk, d in sorted(by.items()):
    bits = []
    if d["+"]: bits.append("+" + " +".join(d["+"][:8]) + (" …" if len(d["+"]) > 8 else ""))
    if d["-"]: bits.append("-" + " -".join(d["-"][:8]) + (" …" if len(d["-"]) > 8 else ""))
    print(f"    {bk}: " + "  ".join(bits))
PY
fi
MCP_COUNTS=""   # "<id> <도구수> <연결1/0>" 줄 목록
TM_OK=1
if [ -n "$TM" ] && json_ok "$TM"; then
  MCP_COUNTS="$(TM="$TM" python3 - <<'PY'
import json, os
for a in json.loads(os.environ["TM"]).get("apps") or []:
    name = a.get("app") or ""
    if name.startswith("heax-"):
        print(name[5:], a.get("tool_count") or 0, 1 if a.get("reachable") else 0)
PY
)"
else
  TM_OK=0
  fail "게이트웨이 /tools-map 을 읽지 못함 — MCP 앱 도구 수를 판정할 수 없다(게이트웨이 확인)."
fi

# 도구 수는 tools/list 의 응답 길이일 뿐이다 — tools/list 는 답하면서 tools/call 은 전부
# 거절하는 백엔드가 실재한다(DynaForge MCP: 도구 22개 표시, 호출 성공 0건, 2026-08-01~08-12).
# 그래서 백엔드마다 읽기 전용 도구를 실제로 몇 개 불러 본다. 판정은 백엔드 단위 '0성공'이다 —
# 개별 도구가 인자 없이 실패하는 건 정상일 수 있어서다(예: plot_curves).
SMOKE_PY="$AGENT_DIR/.venv/bin/python"    # mcp 모듈이 있는 venv(게이트웨이가 쓰는 것과 동일)

# 스모크 1회 실행 — 출력은 들여쓰기해 찍고, rc 를 그대로 돌려준다.
run_smoke() {
  local out rc
  out="$(mktemp)"
  "$SMOKE_PY" "$SELF_REPO/infra/scripts/mcp-smoke.py" >"$out" 2>&1
  rc=$?
  sed 's/^/  /' "$out"
  rm -f "$out"
  return $rc
}

# 0성공 백엔드를 고쳐 본다. 지금까지 확인된 원인은 둘이다.
#   ① kr_ PAT 만료·취소 → 재프로비저닝이 살아있는지 확인 후 재발급(provision-config.sh)
#   ② 게이트웨이가 옛 토큰을 물고 있음 → config 는 기동 시 1회만 읽으므로 재기동이 필요
# 둘 다 무해한 조치라 조건 없이 순서대로 시도하고, 마지막에 다시 검증한다.
repair_mcp() {
  echo "  · 자동 복구 시도 — 재프로비저닝 → 게이트웨이 재기동 → 재검증"
  # ⚠ 순서가 중요하다. --force 는 .bak 을 덮어쓰므로, 직전 config 에서 토큰을 건져 오는
  #   sync-provision-env 를 **먼저** 돌려야 한다. 반대로 하면 RAT/ODB 토큰을 못 건져
  #   reportarchive·odb-hub 가 통째로 빠진다(cae00 실사고 2026-08-12).
  if [ -n "$GW_DIR" ] && [ -x "$GW_DIR/sync-provision-env.sh" ]; then
    bash "$GW_DIR/sync-provision-env.sh" --write 2>&1 | sed 's/^/      /' || true
  fi
  if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/provision-config.sh" ]; then
    ( [ -f "$GW_DIR/provision.env" ] && set -a && . "$GW_DIR/provision.env" && set +a
      bash "$GW_DIR/provision-config.sh" --force ) 2>&1 | sed 's/^/      /' || true
  fi
  if [ -n "$GW_DIR" ] && [ -x "$GW_DIR/start.sh" ]; then
    local pid port
    # 포트를 9110 으로 가정하면 안 된다 — 다른 포트를 쓰는 박스에서는 PID 를 못 찾아 kill 이
    # 조용히 지나가고, start.sh 가 "이미 응답 중"이라며 기동을 생략해 옛 토큰이 그대로 남는다.
    port="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1]))["_gateway"].get("port",9110))
except Exception: print(9110)' "$GW_DIR/gateway_config.json" 2>/dev/null || echo 9110)"
    pid="$(ss -tlnpH "sport = :$port" 2>/dev/null | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)"
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do ss -tlnH "sport = :$port" 2>/dev/null | grep -q . || break; sleep 0.5; done
    bash "$GW_DIR/start.sh" --bg 2>&1 | sed 's/^/      /' || true
    sleep 5
  fi
}

if [ -x "$SMOKE_PY" ] && [ -f "$SELF_REPO/infra/scripts/mcp-smoke.py" ]; then
  echo "  · MCP 도구 실호출 스모크"
  if run_smoke; then
    :
  else
    rc=$?
    if [ "$rc" = 3 ]; then
      # 드리프트는 토큰 문제가 아니다 — 재프로비저닝으로 안 고쳐진다. 배포본이 낡은 것이라
      # 그 앱을 재기동/재빌드해야 한다. 엉뚱한 복구를 돌리지 않고 조치만 정확히 알린다.
      fail "MCP 앱이 코드보다 오래된 배포본으로 돌고 있다(위 ✗ 줄) — 호출은 되지만 새 도구가 빠져 있다."
      echo "      DynaForge(kooremapper_mcp): (KooRemapper) apptainer instance stop koorm_mcp && bash platform/infra/scripts/start.sh"
      echo "      heax 등록 앱:              (HEAXHub) bash deploy/apptainer/redeploy-app.sh <slug> --rebuild"
      echo "      둘 다 소스가 bind-mount 라 재기동만으로 최신 코드가 물린다(빌드형은 --rebuild)."
    elif [ "$rc" = 1 ]; then
      # 검출만 하고 끝내면 사람이 손으로 고칠 때까지 죽어 있다 — 여기서 고쳐 본다.
      repair_mcp
      echo "  · 복구 후 재검증"
      if run_smoke; then
        ok "자동 복구 성공 — 0성공 백엔드가 사라졌다"
      else
        rc=$?
        case "$rc" in
          1) fail "MCP 백엔드 중 호출이 전량 실패하는 것이 있다(위 ✗ 줄) — 자동 복구로도 못 살렸다." ;;
          3) fail "토큰은 살아났지만 배포본이 코드보다 오래됐다(위 ✗ 줄) — 해당 앱을 재기동/재빌드하라." ;;
          *) fail "복구 후 MCP 스모크를 돌리지 못했다(rc=$rc) — 도구 동작 여부는 판정되지 않았다." ;;
        esac
      fi
    else
      fail "MCP 도구 스모크를 돌리지 못했다(rc=$rc) — 도구 동작 여부는 판정되지 않았다."
    fi
  fi
else
  # 검사를 못 돌린 것과 통과한 것은 다르다 — 조용히 넘어가면 '항상 통과'가 된다.
  # 예전엔 echo 만 했다. 그래서 cae00 처럼 venv 경로가 다른 박스에서는 스모크가 통째로
  # 생략된 채 초록으로 끝났고, DynaForge 가 죽어 있는 걸 아무도 못 봤다. 이제 실패로 센다.
  fail "MCP 실호출 스모크를 생략했다(python=$SMOKE_PY, script=$SELF_REPO/infra/scripts/mcp-smoke.py) — 도구 동작 미확인"
fi

# 등록 안 된 /apps/<id>/ 는 404 가 아니라 200 이 나온다 — Caddy catch-all 이 허브 SPA 를
# 돌려주기 때문이다. 자산 검사도 못 잡는다(그 SPA 의 /assets/*.js 는 실재해서 정상 판정).
# 그래서 '첫 화면 title 이 그대로 오면 미서빙'으로 본다. 제목을 하드코딩하지 않고 실제
# 첫 화면에서 읽어 둔다 — 문구가 바뀌어도 검사가 조용히 죽지 않게.
# 부분일치는 쓸 수 없다: 데모들이 'HEAXHub Dash Demo' 처럼 접두사를 공유한다(실측). 완전일치다.
_title_of() { curl -s -L -m 6 "$1" 2>/dev/null | grep -oiE '<title>[^<]*' | head -1; }
FALLBACK_TITLES="$(printf '%s\n%s\n' "$(_title_of http://127.0.0.1:4180/)" "$(_title_of http://127.0.0.1:8088/)" | grep -v '^$')"

for app in $heax_apps; do
  # 데모는 참고용이라 실패해도 배포를 막지 않는다. 그 외 앱은 실패를 종료코드로 올린다.
  case "$app" in heax_demo_*) crit=0 ;; *) crit=1 ;; esac
  tools="$(printf '%s\n' "$MCP_COUNTS" | awk -v id="$app" '$1==id {print $2; exit}')"
  reach="$(printf '%s\n' "$MCP_COUNTS" | awk -v id="$app" '$1==id {print $3; exit}')"
  is_mcp=0; [ -n "$tools" ] && is_mcp=1

  # ① MCP 면 도구 수로 먼저 판정 — 웹 UI 유무와 무관하다(materialtwin_web 은 둘 다 갖는다).
  if [ "$is_mcp" = 1 ]; then
    if [ "$reach" != "1" ] || [ "${tools:-0}" -eq 0 ]; then
      app_bad "$crit" "heax MCP 앱 $app → 도구 ${tools:-0}개 / 연결 $([ "$reach" = 1 ] && echo O || echo X) — 등록은 됐으나 기능이 0개다."
      echo "      프록시형 앱은 업스트림 서버가 죽으면 이 모양이 된다(DynaForge=kooremapper_mcp → :8701)."
      echo "      진단: $SELF_REPO/infra/scripts/check-mcp-registration.sh $app"
    else
      ok "heax MCP 앱 $app → 도구 ${tools}개 (정상)"
    fi
  fi

  code=000; spa=0
  for _try in 1 2 3 4 5; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -L -m 6 "http://127.0.0.1:8088/apps/$app/" 2>/dev/null || echo 000)
    if [ "$code" = "200" ] || [ "$code" = "304" ]; then
      atitle="$(_title_of "http://127.0.0.1:8088/apps/$app/")"
      if [ -n "$FALLBACK_TITLES" ] && [ -n "$atitle" ] \
         && printf '%s\n' "$FALLBACK_TITLES" | grep -qxF "$atitle"; then
        spa=1
      else
        spa=0; break
      fi
    fi
    # MCP 전용 앱의 루트 404/401 은 정상이라 재시도할 이유가 없다(앱마다 15초씩 버리던 것).
    { [ "$is_mcp" = 1 ] && { [ "$code" = "404" ] || [ "$code" = "401" ] || [ "$code" = "403" ]; }; } && break
    sleep 3
  done
  if [ "$spa" = 1 ]; then
    app_bad "$crit" "heax 앱 $app → 200 이지만 허브 첫 화면이 돌아왔다 — 실제로는 미서빙(route 미등록/앱 미기동)."
    echo "      상태코드는 200 이라 겉으론 정상으로 보인다. 등록/기동을 확인하라."
    continue
  fi
  if [ "$code" != "200" ] && [ "$code" != "304" ]; then
    # 401/403 = 비공개(visibility) 앱이거나 UI 없는 MCP 전용 — 파손이 아니라 정책이다.
    if [ "$code" = "401" ] || [ "$code" = "403" ]; then
      # ⚠ 다만 '정책 401' 로 넘기면 그 뒤가 죽어도 안 보인다. portal_auth 앱(DynaForge)은
      #   익명이면 게이트에서 401 이 나므로, 업스트림이 통째로 죽어 있어도 똑같이 401 이다.
      #   그래서 Caddy 에 등록된 업스트림 주소를 꺼내 직접 두드려 본다. 게이트 앞에서 막힌
      #   401 과, 뒤가 죽어서 못 쓰는 401 을 구분하지 못하면 '초록인데 안 되는' 상태가 된다.
      _up="$(curl -s -m 5 http://127.0.0.1:2019/config/ 2>/dev/null | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: raise SystemExit(0)
app=sys.argv[1]; found=[]
def walk(o):
    if isinstance(o,dict):
        if o.get("@id")==f"app-{app}":
            found.append(json.dumps(o))
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(d)
if not found: raise SystemExit(0)
o=json.loads(found[0])
dials=[]
def w2(x):
    if isinstance(x,dict):
        if "dial" in x and isinstance(x["dial"],str): dials.append(x["dial"])
        for v in x.values(): w2(v)
    elif isinstance(x,list):
        for v in x: w2(v)
w2(o)
# forward_auth 서브리퀘스트(:4040)는 업스트림이 아니다 — 마지막 dial 이 실제 앱이다.
print(dials[-1] if dials else "")' "$app" 2>/dev/null)"
      if [ -n "$_up" ]; then
        _uc="$(curl -s -o /dev/null -m 6 -w '%{http_code}' "http://$_up/" 2>/dev/null || echo 000)"
        if [ "$_uc" = "000" ]; then
          app_bad "$crit" "heax 앱 $app → $code 인데 업스트림($_up)이 응답하지 않는다 — 정책이 아니라 죽은 것이다."
          echo "      조치: bash $SELF_REPO/infra/scripts/deploy-all-from-drive.sh $(echo "$app" | tr '_' '-')"
        else
          ok "heax 앱 $app → $code (로그인 필요 — 정상 정책, 업스트림 $_up 응답 $_uc)"
        fi
      else
        ok "heax 앱 $app → $code (비공개/UI 없음 — 정상 정책)"
      fi
    elif [ "$is_mcp" = 1 ] && [ "$code" = "404" ]; then
      ok "heax 앱 $app → 404 (MCP 전용, UI 없음 — 위 도구 수로 판정함)"
    elif [ "$code" = "502" ] || [ "$code" = "503" ] || [ "$code" = "504" ]; then
      # 502/503/504 는 404 와 원인이 정반대다 — 라우트는 살아 있고 그 너머가 죽은 것이다.
      # 같은 문구를 주면 없는 라우트를 찾아 헤매게 된다.
      app_bad "$crit" "heax 앱 $app → $code — 라우트는 살아 있고 업스트림이 죽었다(등록 문제 아님)."
      echo "      프록시형 앱이면 SIF 가 아니라 별도로 떠 있어야 할 서버가 없는 것이다."
      echo "      DynaForge(kooremapper/kooremapper_mcp) → :8700 웹 / :8701 MCP."
      echo "      조치: bash $SELF_REPO/infra/scripts/deploy-all-from-drive.sh kooremapper"
    elif [ "$TM_OK" = 0 ] && [ "$code" = "404" ]; then
      # 게이트웨이가 죽어 MCP 여부를 모르는 상태다. MCP 전용 앱은 루트 404 가 정상이므로
      # 여기서 '미서빙'이라 단정하면 멀쩡한 앱을 범인으로 지목하게 된다(게이트웨이는 이미 위에서 계상).
      bad "heax 앱 $app → 404 — MCP 전용인지 판정 불가(게이트웨이 미응답). 게이트웨이부터 살려라."
    else
      app_bad "$crit" "heax 앱 $app → $code — /apps/$app/ 미서빙(앱 인스턴스 미기동/route 미등록)."
      echo "      재기동: (heax 레포) bash deploy/apptainer/stop.sh && HEAX_NO_BUILD=1 bash deploy/apptainer/start.sh"
      echo "              또는 앱 하나만: bash deploy/apptainer/redeploy-app.sh $(echo "$app" | tr '_' '-')"
    fi
    continue
  fi
  # 첫 자산을 브라우저와 동일하게 환산해 받아 본다 — HTML 이 오면 SPA 폴백에 먹힌 것이다.
  html="$(curl -s -L -m 6 "http://127.0.0.1:8088/apps/$app/" 2>/dev/null || true)"
  # 외부 CDN 자산(https://…, //…)은 제외하고 첫 동일출처 자산을 고른다 — 절대 URL 을 그대로
  # 로컬 경로에 이어붙이면 SPA 폴백 HTML 이 돌아와 멀쩡한 앱을 파손으로 오판한다(실측: 데모 2건).
  asset="$(printf '%s' "$html" | grep -oE '(src|href)="[^"]+\.(js|css)[^"]*"' | sed -E 's/^(src|href)="//; s/"$//' | grep -vE '^(https?:)?//' | head -1)"
  if [ -z "$asset" ]; then
    ok "heax 앱 $app → $code (외부 자산 없음 — 서빙 정상)"
    continue
  fi
  case "$asset" in
    /*)  aurl="http://127.0.0.1:8088$asset" ;;
    ./*) aurl="http://127.0.0.1:8088/apps/$app/${asset#./}" ;;
    *)   aurl="http://127.0.0.1:8088/apps/$app/$asset" ;;
  esac
  actype="$(curl -s -o /dev/null -w '%{content_type}' -m 6 "$aurl" 2>/dev/null || true)"
  case "$actype" in
    *text/html*)
      app_bad "$crit" "heax 앱 $app — 자산이 HTML 로 반환됨(SPA 폴백에 먹힘): $asset"
      echo "      원인: 앱이 /apps/<id>/ 루트절대 URL 을 쓰는데 nginx 에 /apps/ 라우트가 없거나,"
      echo "            Next 처럼 basePath 가 빌드에 안 구워진 경우. routes.env 의 apps= 라인 확인."
      ;;
    *) ok "heax 앱 $app → $code, 자산 $actype (서빙 정상)" ;;
  esac
done

# ── 6b) 등록 정합 — 배포·라우팅되는데 services.yaml 에 없는 서비스를 경고 ──
#   kooremapper 가 정확히 이 구멍으로 빠져 있었다. deploy-all 에만 있고 등록부엔 없어서, 죽어도
#   services.sh status 에 안 잡히고 '없다는 사실' 자체가 안 보였다(cae00 에서 502 로 드러남).
#   목록을 여기 하드코딩하면 같은 종류로 또 썩는다 — 실제 정의에서 읽어 대조한다.
hr "6b) 등록 정합 (services.yaml 누락 검사)"
REG="$(grep -oP '^\s+- name: \K\S+' "$SELF_REPO/infra/services.yaml" 2>/dev/null | sort -u)"
registered() { printf '%s\n' "$REG" | grep -qx "$1"; }
if [ -z "$REG" ]; then
  bad "services.yaml 을 읽지 못함 — 정합 검사 생략"
else
  MISS=0
  # ① deploy-all 이 실제로 배포하는 것. WANT 는 축약명이라 등록부 이름으로 환산한다.
  #    환산표에 없는 새 이름은 그대로 대조돼, 등록도 별칭도 없으면 여기서 걸린다.
  for w in $(sed -n 's/^WANT="\${\*:-\(.*\)}"/\1/p' "$SELF_REPO/infra/scripts/deploy-all-from-drive.sh"); do
    case "$w" in mxwp) n=mx-white-paper ;; heax) n=heax-hub ;; aidh) n=ai-data-hub ;; *) n="$w" ;; esac
    registered "$n" || { bad "deploy-all 이 배포하는 '$w' → services.yaml 에 '$n' 없음(죽어도 status 에 안 잡힌다)"; MISS=1; }
  done
  # ② 포털이 프록시하는 것. apps= 는 HEAX 하위경로라 서비스가 아니고, ste 는 원격 박스다.
  for k in $(sed -n 's/^\([a-z][a-z0-9-]*\)\(\/[a-z]*\)\?=.*/\1/p' "$ROUTES_ENV" 2>/dev/null | sort -u); do
    case "$k" in apps|ste) continue ;; esac
    registered "$k" || { bad "포털이 라우팅하는 '$k' 가 services.yaml 에 없음"; MISS=1; }
  done
  [ "$MISS" = 0 ] && ok "배포·라우팅 대상이 모두 services.yaml 에 등록돼 있다 (등록 $(printf '%s\n' "$REG" | wc -l)건)"
fi

# ── 7) 챗 스모크 — /health 는 프로세스 생존만 본다. 실제 문장 하나를 보내 AI 응답이 오는지
#      (agent → gateway 도구 로딩 → vLLM 전 체인)를 태운다. 실패 시 로그 꼬리를 함께 출력. ──
hr "7) 챗 스모크 (실제 응답 검증)"
CHAT_RES="$(python3 - <<'PY'
import json, urllib.request, sys
body = json.dumps({"message": "한 문장으로 자기소개 해주세요.",
                   "groups": ["ai-data-hub"], "history": []}).encode()
req = urllib.request.Request("http://127.0.0.1:9009/chat", data=body,
                             headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8", "replace")
except Exception as e:
    print("FAIL|요청 실패: %s" % e); sys.exit()
has_result = ('"type": "text"' in raw) or ("event: result" in raw)
has_error = "event: error" in raw
content = ""
for line in raw.splitlines():
    if line.startswith("data:") and '"content"' in line:
        try: content = json.loads(line[5:].strip()).get("content", "") or content
        except Exception: pass
if has_result and not has_error and content.strip():
    print("OK|%s" % content[:80].replace("\n", " "))
else:
    print("FAIL|error=%s result=%s len=%d | %s" % (has_error, has_result, len(content), raw[:400].replace("\n", " ")))
PY
)"
if [ "${CHAT_RES%%|*}" = "OK" ]; then
  ok "챗 응답 수신 — ${CHAT_RES#*|}"
else
  fail "챗 응답 실패 — ${CHAT_RES#*|}"
  echo "  --- agent-server 로그 꼬리 ---"
  tail -n 40 /tmp/hwax-services/agent-server.log 2>/dev/null \
    || tail -n 40 /tmp/agent-server.log 2>/dev/null \
    || echo "  (로그 파일 없음 — /tmp/hwax-services/agent-server.log 확인)"
fi
# 챗 도구 바인딩 가시성 — TOOL_MAX 가 게이트웨이 도구를 캡하면 heax-hub 등 일부 도구가
# 챗 에이전트에 안 실린다(프로드는 TOOL_MAX=0 무제한 권장 — 대형 컨텍스트 GLM 이라 전부 실림).
AH="$(curl -s -m 4 http://127.0.0.1:9009/health 2>/dev/null || true)"
if [ -n "$AH" ]; then
  AH="$AH" GH="$H" python3 - <<'PY' || true
import json, os
try:
    ah = json.loads(os.environ["AH"]); gh = json.loads(os.environ.get("GH") or "{}")
    tmax = ah.get("tool_max", 0); gtools = gh.get("tools")
    if tmax and gtools and tmax < gtools:
        print("  · ⚠ 챗 도구 캡: TOOL_MAX=%s < 게이트웨이 %s개 → 일부 도구(heax-hub 등) 챗 미바인딩. 프로드는 TOOL_MAX=0 권장" % (tmax, gtools))
    elif gtools:
        print("  · 챗 도구: TOOL_MAX=%s (0=무제한) → 게이트웨이 %s개 전부 바인딩 가능" % (tmax, gtools))
except Exception:
    pass
PY
fi

# ○ 옵션·설정이 없어 안 켠 기능은 성공·실패 어느 쪽 끝에서도 다시 말한다 — 조용히 지나가면 그 기능이
#   있는 줄도 모른다(사용자 지시 2026-09-25). 실패 목록과 섞이지 않게 먼저, 다른 표식으로 낸다.
[ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ] && echo "  · 종료 요청이 있었지만 남은 §가 없어 끝까지 갔다 — 아래 요약은 전부 실제로 한 것이다" >&2
hwax_skip_summary
rm -f "$HWAX_SKIP_LEDGER"
# ⚠ 경고 요약 — 종료코드에는 안 들어가지만 실패 목록처럼 끝에 다시 낸다(위로 거슬러 올라가지 않아도 보이게).
if [ -n "${WARN_ITEMS:-}" ]; then
  printf '  \033[1;33m⚠\033[0m 경고 %s건 — 아래는 종료코드에 들어가지 않는 비치명 항목이다\n' "$(printf '%s' "$WARN_ITEMS" | grep -c '^  · ' || true)"
  printf '%s' "$WARN_ITEMS"
fi
if [ "$FAIL" = 1 ]; then
  # ⚠ **무엇이 실패했는지 여기서 다시 말한다.** "위의 ✗ 를 보라" 는 수백 줄을 거슬러 올라가라는
  # 뜻이라, 사람은 대개 안 올라간다(그리고 ⚠ 경고와 ✗ 실패를 섞어 읽는다). fail 이 모아 둔 목록을 낸다.
  printf '  \033[1;31m✗\033[0m %s\n' "핵심 체인 실패 — 아래가 종료코드를 세운 항목이다(⚠ 경고는 포함되지 않는다)"
  printf '%s' "${FAIL_ITEMS:-  · (목록이 비었다 — fail 을 거치지 않고 FAIL 이 세워졌다)}"
  echo "  재시도: 같은 명령 재실행"
  exit 1
fi
ok "전체 최신화 완료 — 운영 준비 상태"
