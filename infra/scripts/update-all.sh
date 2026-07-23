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

# ── 1b) 배포 전 로컬 안전 백업 — merge/복원이 데이터를 건드리기 전에 /data/backups 스냅샷.
#        비치명적(백업 실패가 배포를 막지 않음). 일일 cron(03:30)도 여기서 멱등 보장 —
#        운영자가 --install-cron 을 따로 기억할 필요 없게 update-all 이 챙긴다. ──
if [ -x "$SELF_REPO/infra/scripts/backup-local.sh" ]; then
  hr "1b) 배포 전 로컬 백업(/data/backups)"
  "$SELF_REPO/infra/scripts/backup-local.sh" 2>&1 | tail -6 || echo "  ⚠ 사전 백업 실패(비치명적) — 배포는 계속"
  "$SELF_REPO/infra/scripts/backup-local.sh" --install-cron 2>&1 | sed 's/^/  /' || true
fi

# ── 2) 전 서비스 배포(코드+Drive 아티팩트+기동+nginx). SF DB는 기본 보존, SF_RESTORE_DB=1이면 복원 ──
hr "2) deploy-all-from-drive (portal·mxwp·heax·signalforge·aidh)"
SF_RESTORE_DB="${SF_RESTORE_DB:-0}" "$SELF_REPO/infra/scripts/deploy-all-from-drive.sh" \
  || echo "  ⚠ deploy-all 일부 실패 — 아래 헬스게이트에서 판정"

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
else
  echo "  · HWAXAgentServer 레포 미발견 — 건너뜀"
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
probe "signalforge    :17370" http://127.0.0.1:17370/ 0 "200 302 401"
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
    print("  · ⚠ heax_registry 미설정 — HEAX Hub 앱 자동발견 비활성(§5 재프로비저닝 확인).")
PY
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
