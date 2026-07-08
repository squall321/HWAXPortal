#!/usr/bin/env bash
# report-archive를 제외한 update-enabled 서비스를 포털부터 안전하게 최신화하는 헬퍼
# (포털 먼저 재기동+health 확인 → 실패 시 나머지 보존하고 중단, 나머지는 서비스별 순차·실패해도 계속)
set -uo pipefail   # NOTE: -e 없음 — 한 서비스 실패가 전체 실행을 끊지 않도록

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SVC="$ROOT/infra/scripts/services.sh"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
EXCLUDE="report-archive"
PORTAL="portal"

DRY=0
case "${1:-}" in
  -n|--dry-run) DRY=1; shift ;;
  -h|--help)
    echo "사용법: $(basename "$0") [-n|--dry-run] [서비스명...]"
    echo "  인자 없음 : infra/services.yaml에서 report-archive·update:false·원격을 뺀"
    echo "              update-enabled 서비스 전부(포털·게이트웨이·에이전트·MCP·사이트)."
    echo "  서비스명  : 준 목록만 대상(단 report-archive는 항상 제외)."
    echo "  방식       : 포털 먼저 down→up --update→health(실패 시 나머지 손대지 않고 중단),"
    echo "              이어서 나머지를 서비스별로 순차 재기동(하나 실패해도 계속) → 요약."
    exit 0 ;;
esac

# ── 대상 산출: 인자가 있으면 그 목록, 없으면 매니페스트에서 자동 ──
if [ "$#" -gt 0 ]; then
  TARGETS="$*"
else
  TARGETS="$("$PY" - "$ROOT/infra/services.yaml" "$EXCLUDE" <<'PY'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
svcs = data if isinstance(data, list) else data.get("services", data)
out = []
for s in (svcs or []):
    if not isinstance(s, dict): continue
    if s.get("name") == sys.argv[2]: continue        # report-archive 제외
    if s.get("update") is False: continue            # update:false(vllm·일부 MCP 등)는 존중해 skip
    if s.get("host", "local") != "local": continue   # 원격은 SSH 경로라 제외
    out.append(s["name"])
print(" ".join(out))
PY
)"
fi

# report-archive는 어떤 경우에도(명시 인자 포함) 항상 제외 — 이중 안전
TARGETS="$(printf ' %s ' "$TARGETS" | sed "s/ ${EXCLUDE} / /g" | xargs || true)"
[ -n "$TARGETS" ] || { echo "대상 없음 (report-archive 제외)."; exit 0; }

# 포털을 맨 앞으로 분리(있으면), 나머지는 매니페스트 순서(≈tier) 유지
HAS_PORTAL=0; REST=""
for s in $TARGETS; do
  if [ "$s" = "$PORTAL" ]; then HAS_PORTAL=1; else REST="$REST $s"; fi
done
REST="$(echo $REST | xargs || true)"

echo "▶ 대상: $TARGETS"
if [ "$HAS_PORTAL" = 1 ]; then echo "▶ 순서: portal(먼저·health 확인) → $REST"; else echo "▶ 순서: $REST"; fi
echo "▶ 방식: 서비스별 down→up --update→health. 포털 실패 시 중단(나머지 보존), 나머지는 실패해도 계속."
if [ "$DRY" = 1 ]; then echo "(dry-run) 실행하지 않음."; exit 0; fi

# 한 서비스 재기동: down(무시가능) → up --update. up의 rc=health 반영(정상 0 / 실패 1)
restart_svc() {
  echo "── $1 ──"
  "$SVC" down "$1" >/dev/null 2>&1 || true
  "$SVC" up --update "$1"
}

# 1) 포털 먼저 — 실패하면 나머지 손대지 않고 중단(프론트를 확인된 상태로 유지)
if [ "$HAS_PORTAL" = 1 ]; then
  if restart_svc "$PORTAL"; then
    echo "  ✓ portal 재기동·health OK"
  else
    echo "  ✗ portal 재기동 실패 → 나머지($REST)는 건드리지 않고 중단. 포털 로그 확인 후 재시도하세요."
    exit 1
  fi
fi

# 2) 나머지 — 하나 실패해도 계속, 끝에 요약(포털은 이미 확인됨)
FAILED=""
for s in $REST; do
  restart_svc "$s" || FAILED="$FAILED $s"
done

echo
echo "▶ 최종 상태:"; "$SVC" status $TARGETS || true
if [ -n "$FAILED" ]; then
  echo "▶ ⚠ 실패(포털 제외):$FAILED  — 포털은 정상. 개별 재시도:  $SVC up --update <이름>"
  exit 1
fi
echo "▶ 완료 — report-archive 제외 전부 최신화·재기동."
