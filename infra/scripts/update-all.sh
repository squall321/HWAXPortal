#!/usr/bin/env bash
# cae00 원커맨드 최신화 — 코드+아티팩트+데이터+챗스택+게이트웨이 config 정합+헬스게이트를 한 번에.
#
#   ./infra/scripts/update-all.sh                # 전부 (표준 운영 최신화)
#   SF_RESTORE_DB=1 ./infra/scripts/update-all.sh   # SignalForge DB를 Drive 최신 덤프로 시드/갱신
#   NO_GIT_RESET=1  ./infra/scripts/update-all.sh   # 로컬 수정 보존(soft pull) 모드
#
# 순서:
#   1) 포털 레포 자체 최신화(이 스크립트가 최신이 되도록) → 새 버전으로 1회 재실행
#   2) deploy-all-from-drive.sh  — portal·mxwp·heax·signalforge·aidh (코드+Drive 아티팩트+기동+nginx)
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
set -uo pipefail   # -e 없음: 서비스 하나의 실패가 전체를 끊지 않게, 마지막 게이트에서 판정

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do
                [ -d "$c" ] && { printf '%s' "$c"; return; }; done; }
GW_DIR="$(find_repo HWAXMcpGateway)"
AGENT_DIR="$(find_repo HWAXAgentServer)"
AIDH_DIR="$(find_repo AIDataHub)"
SVC="$SELF_REPO/infra/scripts/services.sh"
hr() { printf '\n\033[1;36m══ %s ══════════════════════════════════════\033[0m\n' "$*"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }

# HTTP 코드 프로브 — curl은 실패해도 -w로 '000'을 찍으므로 종료코드가 아니라 출력값으로만 판정한다.
http_code() { curl -sk -m "${2:-4}" -o /dev/null -w '%{http_code}' "$1" 2>/dev/null; }

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

# ── 2) 전 서비스 배포(코드+Drive 아티팩트+기동+nginx). SF DB는 기본 보존, SF_RESTORE_DB=1이면 복원 ──
hr "2) deploy-all-from-drive (portal·mxwp·heax·signalforge·aidh)"
SF_RESTORE_DB="${SF_RESTORE_DB:-0}" "$SELF_REPO/infra/scripts/deploy-all-from-drive.sh" \
  || echo "  ⚠ deploy-all 일부 실패 — 아래 헬스게이트에서 판정"

# ── 3) AIDataHub 데이터 동기화 — dev가 원본. Drive 덤프가 지난 복원분과 같으면 restore 생략
#      (prod 챗도 create_agent 등 쓰기 도구를 노출하므로, 새 덤프 없는데 매번 DROP+restore 하지 않는다) ──
hr "3) AIDataHub 데이터(에이전트·레코드) 동기화"
if [ -n "$AIDH_DIR" ] && [ -x "$AIDH_DIR/deploy/apptainer/sync-from-drive.sh" ]; then
  # dry-run(다운로드+검증만)으로 Drive 최신 덤프를 받아 이름 확인 → 마커와 비교
  ( cd "$AIDH_DIR" && ./deploy/apptainer/sync-from-drive.sh --dry-run --skip-git --skip-restart >/dev/null 2>&1 ) || true
  LATEST_LINK="$(find "$AIDH_DIR/deploy" -maxdepth 3 -name latest.sql.gz 2>/dev/null | head -1)"
  LATEST_DUMP="$(readlink "$LATEST_LINK" 2>/dev/null || true)"
  MARKER="${LATEST_LINK:+$(dirname "$LATEST_LINK")/.last-restored}"
  if [ -n "$LATEST_DUMP" ] && [ -n "$MARKER" ] && [ "$(cat "$MARKER" 2>/dev/null)" = "$LATEST_DUMP" ]; then
    ok "AIDH 덤프 변화 없음($(basename "$LATEST_DUMP")) — 복원 생략(프로드 데이터 보존)"
  elif ( cd "$AIDH_DIR" && ./deploy/apptainer/sync-from-drive.sh --skip-git ); then
    [ -n "$MARKER" ] && printf '%s' "$(readlink "$LATEST_LINK" 2>/dev/null)" > "$MARKER" 2>/dev/null
    ok "AIDH 데이터 동기화(새 덤프 복원)"
  else
    bad "AIDH 데이터 동기화 실패(심의 페르소나 발굴에 영향)"
  fi
else
  bad "AIDataHub sync-from-drive.sh 없음 — 건너뜀"
fi

# ── 4) 챗 스택만 pull+재기동 — 2)에서 이미 재기동한 사이트들을 다시 내리지 않는다
#      (mxwp-mcp는 deploy-all이 재기동, reportarchive-mcp는 RA 레포 공유라 update 금지 — 기동은 5에서) ──
hr "4) update-sites (챗 스택: mcp-gateway·agent-server·signalforge-mcp)"
"$SELF_REPO/infra/scripts/update-sites.sh" mcp-gateway agent-server signalforge-mcp \
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
  H="$1" RAT="${RAT_TOKEN:-}" MXWP_UP="$MXWP_UP" python3 - <<'PY'
import json, os
h = json.loads(os.environ["H"]); have = set((h.get("backends") or {}).keys())
want = {"ai-data-hub", "signalforge"}
if os.environ.get("MXWP_UP") == "1": want.add("mx-white-paper")
if os.environ.get("RAT"):           want.add("reportarchive")
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

  MISSING="$(calc_missing "$H")"
  # heax_registry는 /health에 안 나오는 config 전용 항목 — 토큰이 준비됐는데 config에 없으면 재프로비저닝 대상.
  if [ -n "${HEAX_MCP_TOKEN:-}" ] && [ -n "$GW_DIR" ] && [ -f "$GW_DIR/gateway_config.json" ] \
     && ! grep -q '"heax_registry"' "$GW_DIR/gateway_config.json" 2>/dev/null; then
    MISSING="heax_registry${MISSING:+ $MISSING}"
  fi

  if [ -n "$MISSING" ]; then
    echo "  · config에 없는 백엔드: $MISSING → 재프로비저닝"
    if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/provision-config.sh" ]; then
      ( cd "$GW_DIR" && RAT_TOKEN="${RAT_TOKEN:-}" HEAX_MCP_TOKEN="${HEAX_MCP_TOKEN:-}" \
          HEAX_MCP_SERVERS_URL="${HEAX_MCP_SERVERS_URL:-}" HEAX_MCP_BASE="${HEAX_MCP_BASE:-}" \
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
        heax-*)         UP_SVCS="$UP_SVCS heax-hub" ;;
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
probe "signalforge    :17370" http://127.0.0.1:17370/ 0 "200 302 401"
H="$(gw_health)"
if [ -n "$H" ] && json_ok "$H"; then
  H="$H" python3 - <<'PY'
import json, os
h = json.loads(os.environ["H"])
parts = " ".join(k + "=" + ("up" if v else "DOWN") for k, v in sorted((h.get("backends") or {}).items()))
print(f"  · gateway {h.get('tools')} tools | {parts}")
PY
fi

if [ "$FAIL" = 1 ]; then
  bad "핵심 체인 실패 — 위의 ✗ 항목을 확인하세요 (재시도: 같은 명령 재실행)"
  exit 1
fi
ok "전체 최신화 완료 — 운영 준비 상태"
