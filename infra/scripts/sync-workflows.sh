#!/usr/bin/env bash
# 정본 워크플로(infra/pipeline/*.js)를 이름호출 런타임이 읽는 .claude/workflows/ 로 동기화한다.
#
# 왜 필요한가: Workflow({name:'hwax-sim-deliberate'}) 같은 이름 호출은 .claude/workflows/ 를
# 읽는데 그 디렉토리는 gitignore 라 git pull 로 갱신되지 않는다(정본은 추적되는 infra/pipeline/).
# 그래서 pull 후 이 스크립트로 정본을 사본에 덮어 둘을 맞춘다. update-all 이 매 실행 앞에서 부른다.
#
#   infra/scripts/sync-workflows.sh            # 정본→사본 복사(변경분만 보고)
#   infra/scripts/sync-workflows.sh --check    # 복사 없이 어긋난 파일만 보고(종료코드 1=어긋남)
set -euo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$SELF/infra/pipeline"
DST="$SELF/.claude/workflows"
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

mkdir -p "$DST"
changed=0
for f in "$SRC"/*.js; do
  [ -f "$f" ] || continue
  # 워크플로만(meta 있는 것). viz_module 등 비워크플로 js 는 건너뛴다.
  grep -qE "export const meta" "$f" || continue
  b="$(basename "$f")"
  if [ -f "$DST/$b" ] && cmp -s "$f" "$DST/$b"; then
    continue
  fi
  changed=$((changed + 1))
  if [ "$CHECK" = 1 ]; then
    echo "  ⚠ 어긋남: $b (정본과 다름)"
  else
    cp "$f" "$DST/$b"
    echo "  ✓ 동기화: $b"
  fi
done

if [ "$changed" = 0 ]; then
  echo "  워크플로 동기 상태 — 변경 없음"
elif [ "$CHECK" = 1 ]; then
  echo "  → infra/scripts/sync-workflows.sh 로 맞춘다"
  exit 1
fi
