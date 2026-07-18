#!/usr/bin/env bash
# cae00 원커맨드 최신화 — 코드+아티팩트+데이터+챗스택+게이트웨이 config 정합+헬스게이트를 한 번에.
#
#   ./infra/scripts/update-all.sh                # 전부 (표준 운영 최신화)
#   SF_RESTORE_DB=1 ./infra/scripts/update-all.sh   # SignalForge DB를 Drive 최신 덤프로 시드/갱신
#   NO_GIT_RESET=1  ./infra/scripts/update-all.sh   # 로컬 수정 보존(soft pull) 모드
#
# 순서:
#   1) 포털 레포 자체 최신화(이 스크립트가 최신이 되도록) → deploy-all-from-drive.sh 재실행 위임
#   2) deploy-all-from-drive.sh  — portal·mxwp·heax·signalforge·aidh (코드+Drive 아티팩트+기동+nginx)
#   3) AIDataHub 데이터 복원     — dev가 원본(일별 덤프→Drive)이므로 항상 최신 덤프로 동기화
#   4) update-sites.sh           — repo: 가진 서비스(게이트웨이·agent-server·MCP들) pull+재기동
#   5) 게이트웨이 config 정합    — /health의 backends와 기대 목록을 비교, 빠진 백엔드가 있으면
#                                  provision-config.sh --force로 재생성(토큰은 provision.env에서) 후 재기동
#   6) 헬스게이트                — 핵심 체인(portal→agent→gateway) 실패 시 비정상 종료(exit 1)로 크게 알림
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
AIDH_DIR="$(find_repo AIDataHub)"
hr() { printf '\n\033[1;36m══ %s ══════════════════════════════════════\033[0m\n' "$*"; }
ok() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; }

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
      git stash push -u -q -m "update-all auto-stash" 2>/dev/null || true
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

# ── 3) AIDataHub 데이터 동기화 — dev가 원본이므로 prod는 항상 최신 덤프를 따라간다 ──
hr "3) AIDataHub 데이터(에이전트·레코드) 동기화"
if [ -n "$AIDH_DIR" ] && [ -x "$AIDH_DIR/deploy/apptainer/sync-from-drive.sh" ]; then
  ( cd "$AIDH_DIR" && ./deploy/apptainer/sync-from-drive.sh ) \
    && ok "AIDH 데이터 동기화" || bad "AIDH 데이터 동기화 실패(심의 페르소나 발굴에 영향)"
else
  bad "AIDataHub sync-from-drive.sh 없음 — 건너뜀"
fi

# ── 4) 챗 스택(게이트웨이·agent-server·MCP들) pull + 재기동 ──
hr "4) update-sites (게이트웨이·agent-server·MCP)"
"$SELF_REPO/infra/scripts/update-sites.sh" || echo "  ⚠ update-sites 일부 실패 — 아래에서 판정"

# ── 5) 게이트웨이 config 정합 — 기대 백엔드가 config에 아예 없으면 재프로비저닝 ──
hr "5) 게이트웨이 config 정합(reconcile)"
gw_health() { curl -s -m 4 http://127.0.0.1:9110/health 2>/dev/null; }
H="$(gw_health)"
if [ -z "$H" ]; then
  bad "게이트웨이 :9110 무응답 — services.sh up mcp-gateway 후 재시도"
else
  # 기대 목록: 상시(ai-data-hub·signalforge) + 토큰이 준비된 것(reportarchive) + mxwp(MCP가 떠 있을 때만
  # — 안 떠 있으면 config에 넣어도 무의미하고, 매 실행 재프로비저닝만 반복하게 됨)
  PROV_ENV="$GW_DIR/provision.env"
  # shellcheck disable=SC1090 — 토큰 파일은 운영 박스에만 존재(gitignore)
  [ -f "$PROV_ENV" ] && . "$PROV_ENV"
  MXWP_UP=0
  [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/mcp 2>/dev/null || echo 000)" != "000" ] && MXWP_UP=1
  MISSING="$(H="$H" RAT="${RAT_TOKEN:-}" MXWP_UP="$MXWP_UP" python3 - <<'PY'
import json, os
h = json.loads(os.environ["H"]); have = set((h.get("backends") or {}).keys())
want = {"ai-data-hub", "signalforge"}
if os.environ.get("MXWP_UP") == "1": want.add("mx-white-paper")
if os.environ.get("RAT"):           want.add("reportarchive")
# heax 백엔드는 heax-<id> 동적 이름이라 /health로 유무 판별 불가 — 재프로비저닝 시 토큰만 넘겨준다
print(" ".join(sorted(want - have)))
PY
)"
  if [ -n "$MISSING" ]; then
    echo "  · config에 없는 백엔드: $MISSING → 재프로비저닝"
    if [ -n "$GW_DIR" ] && [ -f "$GW_DIR/provision-config.sh" ]; then
      ( cd "$GW_DIR" && RAT_TOKEN="${RAT_TOKEN:-}" HEAX_MCP_TOKEN="${HEAX_MCP_TOKEN:-}" \
          HEAX_MCP_SERVERS_URL="${HEAX_MCP_SERVERS_URL:-}" HEAX_MCP_BASE="${HEAX_MCP_BASE:-}" \
          bash provision-config.sh --force )
      # --force는 GW_TOKEN을 회전하고 agent의 mcp_servers.json도 다시 쓰므로 둘 다 재기동
      "$SELF_REPO/infra/scripts/services.sh" down mcp-gateway agent-server 2>/dev/null
      "$SELF_REPO/infra/scripts/services.sh" up mcp-gateway agent-server
      H="$(gw_health)"
    else
      bad "HWAXMcpGateway 레포/provision-config.sh 없음 — 재프로비저닝 불가"
    fi
  else
    ok "config 정합 (빠진 백엔드 없음)"
  fi
  # 등록됐지만 죽어 있는(false) 백엔드는 그 서비스 up → 게이트웨이 revive(60s)가 자동 편입
  DOWN="$(H="$H" python3 -c 'import json,os;h=json.loads(os.environ["H"]);print(" ".join(sorted(k for k,v in (h.get("backends") or {}).items() if not v)))' 2>/dev/null)"
  if [ -n "$DOWN" ]; then
    echo "  · 등록됐지만 다운: $DOWN → 서비스 기동 시도(게이트웨이는 60s 내 자동 재편입)"
    "$SELF_REPO/infra/scripts/services.sh" up 2>/dev/null | tail -3
  fi
fi

# ── 6) 헬스게이트 — 핵심 체인 실패 시 exit 1로 크게 알림 ──
hr "6) 헬스게이트"
FAIL=0
probe() { # $1=라벨 $2=URL $3=critical(1/0)
  local code; code="$(curl -sk -m 4 -o /dev/null -w '%{http_code}' "$2" 2>/dev/null || echo 000)"
  if [ "$code" = 200 ] || [ "$code" = 302 ] || [ "$code" = 401 ]; then ok "$1 → $code"
  else bad "$1 → $code  ($2)"; [ "$3" = 1 ] && FAIL=1; fi
}
probe "portal-backend :8723" http://127.0.0.1:8723/health 1
probe "nginx          :8088" http://127.0.0.1:8088/health 1
probe "agent-server   :9009" http://127.0.0.1:9009/health 1
probe "gateway        :9110" http://127.0.0.1:9110/health 1
probe "aidh           :8001" http://127.0.0.1:8001/api/system/health 0
probe "signalforge    :17370" http://127.0.0.1:17370/ 0
H="$(gw_health)"
if [ -n "$H" ]; then
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
