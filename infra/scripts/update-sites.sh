#!/usr/bin/env bash
# report-archive를 제외한 update-enabled 서비스를 포털부터 안전하게 최신화하는 헬퍼
# (repo: 있는데 없는/원격없는 서비스는 portal 상위로 자동 clone/remote → 포털 먼저 재기동+health
#  → 실패 시 나머지 보존하고 중단, 나머지는 서비스별 순차·실패해도 계속)
set -uo pipefail   # NOTE: -e 없음 — 한 서비스 실패가 전체 실행을 끊지 않도록

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SVC="$ROOT/infra/scripts/services.sh"
SVCPY="$ROOT/infra/scripts/services.py"
MANIFEST="$ROOT/infra/services.yaml"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
EXCLUDE="report-archive"
PORTAL="portal"

DRY=0
case "${1:-}" in
  -n|--dry-run) DRY=1; shift ;;
  -h|--help)
    echo "사용법: $(basename "$0") [-n|--dry-run] [서비스명...]"
    echo "  인자 없음 : report-archive·update:false·원격을 뺀 update-enabled 서비스 전부"
    echo "              (포털·게이트웨이·에이전트·MCP·사이트)."
    echo "  서비스명  : 준 목록만 대상(단 report-archive는 항상 제외)."
    echo "  사전작업  : 매니페스트에 repo: URL이 있는데 디렉토리가 없으면 portal 상위(형제)로 clone,"
    echo "              있으나 origin 미설정이면 remote 지정(경로 하드코딩 없이 discover 위치 사용)."
    echo "  방식       : 포털 먼저 down→up --update→health(실패 시 나머지 손대지 않고 중단),"
    echo "              이어서 나머지를 서비스별 순차 재기동(하나 실패해도 계속) → 요약."
    exit 0 ;;
esac

# ── 대상 산출: 인자가 있으면 그 목록, 없으면 매니페스트에서 자동 ──
if [ "$#" -gt 0 ]; then
  TARGETS="$*"
else
  TARGETS="$("$PY" - "$MANIFEST" "$EXCLUDE" <<'PY'
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

# ── 사전작업 계획: repo: 있는 서비스의 discover 위치를 오케스트레이터와 동일 로직으로 확인 ──
# (services.py resolve_dir/PARENT 재사용 → 경로 하드코딩 없음. 없으면 CLONE, 있으나 origin 없으면 SETREMOTE)
PLAN="$("$PY" - "$SVCPY" "$MANIFEST" $TARGETS <<'PY'
import sys, importlib.util, yaml
spec = importlib.util.spec_from_file_location("svcmod", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
targets = set(sys.argv[3:])
data = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
svcs = data if isinstance(data, list) else data.get("services", data)
for s in (svcs or []):
    if not isinstance(s, dict) or s.get("name") not in targets: continue
    repo = s.get("repo")
    if not repo: continue
    d = m.resolve_dir(s)
    if d is None:
        print("CLONE\t%s\t%s" % (repo, m.PARENT / (s.get("discover") or s["name"])))
    else:
        print("SETREMOTE\t%s\t%s" % (repo, d))
PY
)"

# 포털을 맨 앞으로 분리(있으면), 나머지는 매니페스트 순서(≈tier) 유지
HAS_PORTAL=0; REST=""
for s in $TARGETS; do
  if [ "$s" = "$PORTAL" ]; then HAS_PORTAL=1; else REST="$REST $s"; fi
done
REST="$(echo $REST | xargs || true)"

echo "▶ 대상: $TARGETS"
if [ "$HAS_PORTAL" = 1 ]; then echo "▶ 순서: portal(먼저·health 확인) → $REST"; else echo "▶ 순서: $REST"; fi
echo "▶ 방식: (사전 clone/remote) → 서비스별 down→up --update→health. 포털 실패 시 중단, 나머지는 실패해도 계속."

# ── 사전작업 실행(또는 dry-run 표시) ──
run_preflight() {
  [ -n "$PLAN" ] || { echo "  (사전작업 없음 — 모든 repo 준비됨)"; return 0; }
  while IFS=$'\t' read -r kind url dest; do
    [ -n "${kind:-}" ] || continue
    case "$kind" in
      CLONE)
        echo "  clone  $url → $dest"
        [ "$DRY" = 1 ] || git clone "$url" "$dest" || echo "  ⚠ clone 실패: $url" ;;
      SETREMOTE)
        if ! git -C "$dest" remote get-url origin >/dev/null 2>&1; then
          echo "  set-remote  $dest → origin=$url"
          if [ "$DRY" != 1 ]; then
            git -C "$dest" remote add origin "$url"
            git -C "$dest" fetch -q origin || true
            b="$(git -C "$dest" rev-parse --abbrev-ref HEAD 2>/dev/null)"
            [ -n "$b" ] && git -C "$dest" branch -u "origin/$b" "$b" 2>/dev/null || true
          fi
        fi ;;
    esac
  done <<< "$PLAN"
}

echo "▶ 사전작업:"; run_preflight
if [ "$DRY" = 1 ]; then echo "(dry-run) 재기동은 실행하지 않음."; exit 0; fi

# 실패 원인 노출: up 출력의 FAIL 라인 + 서비스 로그 꼬리(크래시/헬스실패/빌드오류 원인)
show_cause() {
  local name="$1" out="$2" log
  echo "  ── ⚠ 실패 원인: $name ──"
  printf '%s\n' "$out" | grep -iE 'FAIL|✗|error|traceback|exception' | sed 's/^/    /' | head -6
  # up 출력이 알려주는 로그 경로(services.py "see <path>") 우선, 없으면 규약 경로
  log="$(printf '%s\n' "$out" | grep -oE '/[^ )]+\.log' | head -1)"
  [ -n "$log" ] || log="/tmp/hwax-services/${name}.log"
  if [ -s "$log" ]; then
    echo "    ↳ 로그 꼬리($log):"
    tail -n 30 "$log" | grep -vE '^[[:space:]]*$' | tail -20 | sed 's/^/      /'
  else
    echo "    ↳ 로그 없음/빈 파일: $log"
  fi
}

# 한 서비스 재기동: down(무시가능) → up --update. up의 rc=health 반영(정상 0 / 실패 1)
# 실패 시 원인을 인라인으로 노출.
restart_svc() {
  local name="$1" out rc
  echo "── $name ──"
  "$SVC" down "$name" >/dev/null 2>&1 || true
  out="$("$SVC" up --update "$name" 2>&1)"; rc=$?
  printf '%s\n' "$out"
  [ "$rc" -ne 0 ] && show_cause "$name" "$out"
  return "$rc"
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
