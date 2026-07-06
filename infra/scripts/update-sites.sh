#!/usr/bin/env bash
# report-archive를 제외한 서버사이드 연동 사이트를 한 번에 git pull + 재기동하는 오케스트레이터 헬퍼
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SVC="$ROOT/infra/scripts/services.sh"
PY="$ROOT/backend/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
EXCLUDE="report-archive"

DRY=0
case "${1:-}" in
  -n|--dry-run) DRY=1; shift ;;
  -h|--help)
    echo "사용법: $(basename "$0") [-n|--dry-run] [서비스명...]"
    echo "  인자 없음 : infra/services.yaml의 tier10 연동 사이트 중"
    echo "              report-archive·update:false·원격을 뺀 것을 자동 선택."
    echo "  서비스명  : 준 목록만 대상(단 report-archive는 항상 제외)."
    echo "  동작       : down → up --update(git pull + 재기동, health 폴링) → status."
    exit 0 ;;
esac

# 대상 산출: 인자가 있으면 그 목록, 없으면 매니페스트에서 자동
if [ "$#" -gt 0 ]; then
  SITES="$*"
else
  SITES="$("$PY" - "$ROOT/infra/services.yaml" "$EXCLUDE" <<'PY'
import sys, yaml
data = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
svcs = data if isinstance(data, list) else data.get("services", data)
out = []
for s in (svcs or []):
    if not isinstance(s, dict): continue
    if s.get("tier") != 10: continue                 # tier10 = 연동 사이트
    if s.get("name") == sys.argv[2]: continue        # report-archive 제외
    if s.get("update") is False: continue            # 매니페스트가 스킵 지정한 것 존중
    if s.get("host", "local") != "local": continue   # 원격은 SSH 경로라 제외
    out.append(s["name"])
print(" ".join(out))
PY
)"
fi

# report-archive는 어떤 경우에도(명시 인자 포함) 항상 제외 — 이중 안전
SITES="$(printf ' %s ' "$SITES" | sed "s/ ${EXCLUDE} / /g" | xargs || true)"
[ -n "$SITES" ] || { echo "대상 사이트 없음 (report-archive 제외)."; exit 0; }

echo "▶ 대상: $SITES"
echo "▶ 제외: $EXCLUDE (+ update:false · 원격)"
if [ "$DRY" = 1 ]; then echo "(dry-run) 실행하지 않음."; exit 0; fi

echo "▶ down $SITES";        "$SVC" down $SITES
echo "▶ up --update $SITES"; "$SVC" up --update $SITES
echo "▶ status";             "$SVC" status $SITES
