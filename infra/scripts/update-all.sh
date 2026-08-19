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
#     ODB_HUB_TOKEN=xxxx           # ODB 자동화 허브(10.252.38.121:8000) — cae00 에서만 도달
#     ARP_BASE=http://10.252.38.97:3001  # AI Ready Portal — 무인증, cae00 에서만 도달
set -uo pipefail   # -e 없음: 서비스 하나의 실패가 전체를 끊지 않게, 마지막 게이트에서 판정

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do
                [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
GW_DIR="$(find_repo HWAXMcpGateway)"
AGENT_DIR="$(find_repo HWAXAgentServer)"
AIDH_DIR="$(find_repo AIDataHub)"
HEAX_DIR="$(find_repo HEAXHub)"   # §5 의 앱 단위 재배포에 필요 — 경로 하드코딩 금지
SVC="$SELF_REPO/infra/scripts/services.sh"
# 포털 라우팅 표. §6 의 ste 프로브가 $REPO_ROOT/$ROUTES_PATH 를 참조했는데 이 스크립트는
# _common.sh 를 source 하지도, infra/.env 를 읽지도 않아 둘 다 미정의였다 — set -u 라 그
# 명령치환만 죽고 STE_UP 이 빈 값이 돼, routes.env 에 ste 가 멀쩡히 있는데도 매번
# '라우트 미설정 — 건너뜀' 만 찍혔다(실측). ROUTES_PATH 는 infra/.env 의 설정 항목이므로
# 하드코딩하지 말고 거기서 읽는다(_common.sh 와 같은 기본값 config/routes.env).
_routes_path="$(sed -n 's/^ROUTES_PATH=//p' "$SELF_REPO/infra/.env" 2>/dev/null | tail -1 | tr -d '"'"'"' ')"
ROUTES_ENV="${ROUTES_ENV:-$SELF_REPO/backend/${_routes_path:-config/routes.env}}"
hr() { printf '\n\033[1;36m══ %s ══════════════════════════════════════\033[0m\n' "$*"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }
# bad 는 경고라 종료코드에 영향이 없다 — 앱이 깨져도 update-all 이 초록으로 끝나던 원인이다.
# 배포 실패로 계상해야 하는 것은 fail 로 낸다(§6 헬스게이트의 FAIL 을 세운다).
fail() { bad "$@"; FAIL=1; }
app_bad() { local c="$1"; shift; if [ "$c" = 1 ]; then fail "$@"; else bad "$@"; fi; }

# HTTP 코드 프로브 — curl은 실패해도 -w로 '000'을 찍으므로 종료코드가 아니라 출력값으로만 판정한다.
http_code() { curl -sk -m "${2:-4}" -o /dev/null -w '%{http_code}' "$1" 2>/dev/null; }

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
  exec env UPDATE_ALL_REEXEC=1 bash "$SELF_REPO/infra/scripts/update-all.sh" "$@"
fi
ok "포털 레포 최신 (재실행 완료)"

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
fi

# ── 2) 전 서비스 배포(코드+Drive 아티팩트+기동+nginx). SF DB는 기본 보존, SF_RESTORE_DB=1이면 복원 ──
hr "2) deploy-all-from-drive (portal·mxwp·heax·signalforge·aidh·kooremapper)"
# 종료코드 3 = 소스 갱신 실패(git fetch/reset). 서비스는 떠 있어도 옛 코드라 가장 위험한
# 상태다 — "✓ up" 만 보고 끝내면 오늘 올린 변경이 하나도 반영되지 않은 채 정상으로 읽힌다.
# (예전 주석은 'skip 건수를 종료코드로 낸다'였으나 실제로는 그런 코드가 없었다.)
set +e
SF_RESTORE_DB="${SF_RESTORE_DB:-0}" "$SELF_REPO/infra/scripts/deploy-all-from-drive.sh"
_DA_RC=$?
set -e
if [ "$_DA_RC" = "3" ]; then
  bad "소스 갱신 실패 — 코드는 옛것이다. 위 '✗ git' 줄의 원인을 먼저 해결하고 다시 돌려라"
elif [ "$_DA_RC" != "0" ]; then
  bad "deploy-all 에서 일부 항목이 skip/실패(rc=$_DA_RC) — 위 ⚠ 줄과 아래 헬스게이트를 함께 보라"
fi

# ── 3) AIDataHub 데이터 동기화 — dev가 원본. Drive 덤프가 지난 복원분과 같으면 restore 생략
#      (prod 챗도 create_agent 등 쓰기 도구를 노출하므로, 새 덤프 없는데 매번 DROP+restore 하지 않는다) ──
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
  bad "AIDataHub sync-from-drive.sh 없음 — 건너뜀"
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
else
  echo "  · HWAXAgentServer 레포 미발견 — 건너뜀"
fi

# ── 4) 챗 스택만 pull+재기동 — 2)에서 이미 재기동한 사이트들을 다시 내리지 않는다
#      (mxwp-mcp는 deploy-all이 재기동, reportarchive-mcp는 RA 레포 공유라 update 금지 — 기동은 5에서) ──
hr "4) update-sites (챗 스택: mcp-gateway·agent-server·signalforge-mcp)"
# 순서가 중요하다: 백엔드(signalforge-mcp) → 게이트웨이 → 소비자(agent-server).
# 종전엔 게이트웨이를 먼저 올려서, 그 시점에 아직 내려가 있던 signalforge-mcp 에 붙지 못하고
# 6단계 헬스게이트가 'signalforge=DOWN' 을 찍었다(cae00 실측 — 게이트웨이 06:54:46 기동,
# signalforge-mcp 는 06:54:51~54 재기동). _revive_loop 가 60초 안에 스스로 재편입하므로
# 실제 장애는 아니었지만, 매 배포마다 가짜 DOWN 이 뜨면 진짜 장애와 구분이 안 된다.
"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server \
  || echo "  ⚠ update-sites 일부 실패 — 아래에서 판정"

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
  H="$1" RAT="${RAT_TOKEN:-}" ODB="${ODB_HUB_TOKEN:-}" ARP="${ARP_BASE:-}" MXWP_UP="$MXWP_UP" python3 - <<'PY'
import json, os
h = json.loads(os.environ["H"]); have = set((h.get("backends") or {}).keys())
want = {"ai-data-hub", "signalforge"}
if os.environ.get("MXWP_UP") == "1": want.add("mx-white-paper")
if os.environ.get("RAT"):           want.add("reportarchive")
# ODB 자동화 허브는 cae00 에서만 도달한다(dev 는 포트 차단 — 실측). 토큰이 있는 박스에서만
# 기대 목록에 넣는다 — RAT_TOKEN 과 같은 방식이라 dev 에서 가짜 DOWN 이 뜨지 않는다.
if os.environ.get("ODB"):           want.add("odb-hub")
# ARP 도 cae00 전용이다. 토큰이 없는 서버라 '주소가 설정돼 있다'가 이 박스에서 쓴다는 신호다.
if os.environ.get("ARP"):           want.add("arp")
print(" ".join(sorted(want - have)))
PY
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
  if apptainer instance list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx mxwp_api; then
    case "$(http_code http://127.0.0.1:8765/mcp 2)" in ''|000) ;; *) MXWP_UP=1 ;; esac
  fi

  # 프로비저닝보다 먼저 — DynaForge 의 kr_ PAT 발급이 이 시크릿에 걸려 있다. 불일치 상태로
  # provision 을 돌리면 "발급 실패"만 찍히고 도구 22개가 목록에만 뜨는 상태가 유지된다.
  if [ -f "$SELF_REPO/infra/scripts/sync-gateway-secret.sh" ]; then
    bash "$SELF_REPO/infra/scripts/sync-gateway-secret.sh" --write
    case $? in 0|1) ;; *) fail "게이트웨이 공유 시크릿을 맞추지 못했다 — DynaForge SSO·kr_ PAT 가 막힌다." ;; esac
  fi

  MISSING="$(calc_missing "$H")"
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

  if [ -n "$MISSING" ]; then
    echo "  · config에 없는 백엔드: $MISSING → 재프로비저닝"
    if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/provision-config.sh" ]; then
      # provision.env 는 `. ` 로 소싱만 하므로(export 아님) 자식 프로세스가 못 본다.
      # 그래서 여기서 하나하나 명시해 넘긴다 — ODB_HUB_* 를 빠뜨려서 cae00 에서
      # ODB_HUB_TOKEN 이 설정돼 있는데도 provision 이 '미설정'으로 건너뛰었다(실측).
      ( cd "$GW_DIR" && RAT_TOKEN="${RAT_TOKEN:-}" HEAX_MCP_TOKEN="${HEAX_MCP_TOKEN:-}" \
          HEAX_MCP_SERVERS_URL="${HEAX_MCP_SERVERS_URL:-}" HEAX_MCP_BASE="${HEAX_MCP_BASE:-}" \
          ODB_HUB_TOKEN="${ODB_HUB_TOKEN:-}" ODB_HUB_BASE="${ODB_HUB_BASE:-}" \
          ARP_BASE="${ARP_BASE:-}" \
          bash provision-config.sh --force )
      "$SVC" down mcp-gateway agent-server 2>/dev/null
      "$SVC" up mcp-gateway agent-server

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
        [ -z "$STILL" ] && ok "재프로비저닝으로 백엔드 정합 완료" \
          || bad "재프로비저닝 후에도 누락: $STILL (mxwp 토큰 민팅 실패 등 — 위 provision 출력 확인)"
      fi
    else
      bad "HWAXMcpGateway 레포/provision-config.sh 없음 — 재프로비저닝 불가"
    fi
  else
    ok "config 정합 (빠진 백엔드 없음)"
  fi

  # 등록됐지만 죽어 있는(false) 백엔드 → 해당 서비스만 지정 기동(전 스택 무인자 up 금지 —
  # hands-off RA·vllm 등 의도적으로 내려둔 것을 되살리지 않기 위함). 게이트웨이는 60s 내 자동 재편입.
  DOWN="$(H="$H" python3 -c 'import json,os;h=json.loads(os.environ["H"]);print(" ".join(sorted(k for k,v in (h.get("backends") or {}).items() if not v)))' 2>/dev/null)"
  if [ -n "$DOWN" ]; then
    UP_SVCS=""
    for b in $DOWN; do
      case "$b" in
        signalforge)    UP_SVCS="$UP_SVCS signalforge-mcp" ;;
        mx-white-paper) UP_SVCS="$UP_SVCS mxwp-mcp" ;;
        reportarchive)  UP_SVCS="$UP_SVCS reportarchive-mcp" ;;
        ai-data-hub)    UP_SVCS="$UP_SVCS ai-data-hub" ;;
        # heax-<slug> 는 '앱 하나'가 죽은 것이다. 여기서 heax-hub 통기동으로 접으면 안 된다 —
        # 허브가 살아 있으면 services.py 가 'already-up' 으로 돌려보내 아무것도 안 하고,
        # 화면엔 '✓ heax-hub already-up' 이 찍혀 복구된 것처럼 보인다(무동작을 복구로 표시).
        # 앱 단위 조치를 직접 부른다. 스크립트가 없으면 할 일을 사람이 알 수 있게 남긴다.
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
        *) echo "  · 다운 백엔드 $b — 매핑된 서비스 없음(수동 확인)" ;;
      esac
    done
    UP_SVCS="$(echo "$UP_SVCS" | xargs -n1 2>/dev/null | sort -u | xargs || true)"
    if [ -n "$UP_SVCS" ]; then
      echo "  · 등록됐지만 다운: $DOWN → 기동: $UP_SVCS (게이트웨이는 60s 내 자동 재편입)"
      "$SVC" up $UP_SVCS
    fi
  fi
fi

# ── 6) 헬스게이트 — 핵심 체인 실패 시 exit 1로 크게 알림 ──
hr "6) 헬스게이트"
FAIL=0
probe() { # $1=라벨 $2=URL $3=critical(1/0) $4=허용코드(공백구분)
  local code; code="$(http_code "$2")"
  case " $4 " in
    *" ${code:-000} "*) ok "$1 → $code" ;;
    *) bad "$1 → ${code:-000}  ($2)"; [ "$3" = 1 ] && FAIL=1 ;;
  esac
}
# 핵심 4종은 전부 무인증 /health — 정상이면 200 외의 코드가 나올 수 없다(401/302는 오설정 신호).
probe "portal-backend :8723" http://127.0.0.1:8723/health 1 "200"
probe "nginx          :8088" http://127.0.0.1:8088/health 1 "200"
probe "agent-server   :9009" http://127.0.0.1:9009/health 1 "200"
probe "gateway        :9110" http://127.0.0.1:9110/health 1 "200"
probe "aidh           :8001" http://127.0.0.1:8001/api/system/health 0 "200"
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
probe "signalforge    :17370" http://127.0.0.1:17370/ 0 "200 302 401"
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
  probe "ste 백엔드      직결" "http://$STE_UP/api/health" 0 "200"
  STE_BODY="$(curl -s -m 4 http://127.0.0.1:8088/ste/api/health 2>/dev/null || true)"
  if printf '%s' "$STE_BODY" | grep -q 'smart-twin-explorer'; then
    ok "ste 프록시      :8088 → 백엔드 응답 확인"
  else
    bad "ste 프록시      :8088 → 포털 SPA 가 돌아온다 (nginx /ste/ location 미반영, 비치명)"
  fi
elif [ "$_STE_SRC" = "routes.local.env" ]; then
  ok "ste — 이 박스에서는 서빙 안 함(routes.local.env 에서 비활성). 라우트도 만들지 않는다."
else
  ok "ste 라우트 미설정 — 건너뜀"
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

# MCP 노출 앱은 /apps/<id>/ 루트 코드로 판정할 수 없다 — MCP 는 하위경로(/mcp)라 루트가
# 404/401 인 게 정상이다(실측: kooremapper_mcp·web_research_mcp 404, laminate·thermal 401).
# 그래서 게이트웨이 /tools-map 의 도구 수로 본다. DynaForge 처럼 프록시 대상 업스트림이
# 죽으면 '등록은 멀쩡한데 도구가 0개'가 되는데, 루트 코드만 보면 이걸 영영 못 잡는다.
TM="$(curl -s -m 6 http://127.0.0.1:9110/tools-map 2>/dev/null || true)"
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
  bad "챗 응답 실패 — ${CHAT_RES#*|}"
  echo "  --- agent-server 로그 꼬리 ---"
  tail -n 40 /tmp/hwax-services/agent-server.log 2>/dev/null \
    || tail -n 40 /tmp/agent-server.log 2>/dev/null \
    || echo "  (로그 파일 없음 — /tmp/hwax-services/agent-server.log 확인)"
  FAIL=1
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

if [ "$FAIL" = 1 ]; then
  bad "핵심 체인 실패 — 위의 ✗ 항목을 확인하세요 (재시도: 같은 명령 재실행)"
  exit 1
fi
ok "전체 최신화 완료 — 운영 준비 상태"
