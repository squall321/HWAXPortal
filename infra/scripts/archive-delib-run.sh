#!/usr/bin/env bash
# 심의 실행 기록을 영구 보관한다 — 세션 스크래치패드(/tmp)는 지워지므로 /data 로 옮긴다.
# 보관 대상: 발행한 HTML, 의장 결정문(md), 원본 저널(jsonl), 워크플로 스크립트.
#
#   bash infra/scripts/archive-delib-run.sh <run-name> <workflow-run-id> [<workflow-run-id> ...]
#   예) bash infra/scripts/archive-delib-run.sh salt-corrosion-drop wf_1aefdaa0-c92 wf_c88694f2-424
#
# 재실행 안전 — 같은 이름으로 다시 돌리면 새 파일만 추가하고 기존 것은 덮어쓴다(누적).
set -uo pipefail

NAME="${1:?사용: archive-delib-run.sh <run-name> <workflow-run-id> ...}"; shift
[ $# -gt 0 ] || { echo "✗ 워크플로 run id 를 하나 이상 주세요"; exit 1; }

ROOT="${DELIB_ARCHIVE_ROOT:-/data/delib-runs}"
SESSION_DIR="$(ls -td /tmp/claude-*/*/*/ 2>/dev/null | head -1)"
# 세션 디렉터리는 환경마다 다르므로 저널 경로에서 역산하는 쪽이 확실하다.
PROJ_DIR="${CLAUDE_PROJECT_DIR:-$HOME/.claude/projects}"

DEST="$ROOT/$(date -u +%Y-%m-%d)_$NAME"
mkdir -p "$DEST"/{html,decisions,raw} || { echo "✗ $DEST 생성 실패"; exit 1; }

echo "→ 보관소: $DEST"

# ── 1. 워크플로 저널 + 스크립트 ──────────────────────────────────────────────
for RID in "$@"; do
  SRC="$(find "$PROJ_DIR" -maxdepth 5 -type d -name "$RID" 2>/dev/null | head -1)"
  if [ -z "$SRC" ]; then echo "  ⚠ $RID — 트랜스크립트 디렉터리를 못 찾음(건너뜀)"; continue; fi
  if [ -f "$SRC/journal.jsonl" ]; then
    cp -f "$SRC/journal.jsonl" "$DEST/raw/$RID.journal.jsonl"
    n=$(grep -c '"type":"result"' "$DEST/raw/$RID.journal.jsonl" 2>/dev/null || echo 0)
    echo "  · $RID 저널 ($n result)"
  else
    echo "  ⚠ $RID — journal.jsonl 없음"
  fi
  # 워크플로 스크립트 정본(같은 세션 디렉터리의 workflows/scripts/*<rid>.js)
  find "$PROJ_DIR" -maxdepth 5 -type f -name "*$RID.js" -exec cp -f {} "$DEST/raw/" \; 2>/dev/null
done

# ── 2. 의장 결정문 추출 ──────────────────────────────────────────────────────
# 저널의 문자열 result 가 의장 산출(결정문·쉬운 설명)이다. 순서대로 번호를 붙여 저장한다.
for J in "$DEST"/raw/*.journal.jsonl; do
  [ -f "$J" ] || continue
  RID="$(basename "$J" .journal.jsonl)"
  python3 - "$J" "$DEST/decisions" "$RID" <<'PY'
import json, os, sys
journal, out, rid = sys.argv[1], sys.argv[2], sys.argv[3]
rows = [json.loads(l) for l in open(journal, encoding="utf-8", errors="replace") if l.strip()]
res = [r.get("result") for r in rows if r.get("type") == "result"]
n = 0
for i, v in enumerate(res):
    if isinstance(v, str) and len(v) > 800:          # 의장 산출만(좌석 발언은 dict)
        n += 1
        open(os.path.join(out, f"{rid}_{i:02d}.md"), "w", encoding="utf-8").write(v)
print(f"  · {rid} 결정문 {n}건 추출")
PY
done

# ── 3. HTML ─────────────────────────────────────────────────────────────────
# 세션 스크래치패드의 HTML 전부. 빌드 중간산물도 남긴다 — 어떻게 만들었는지가 기록이다.
if [ -n "$SESSION_DIR" ] && [ -d "$SESSION_DIR" ]; then
  cnt=0
  while IFS= read -r f; do
    case "$f" in */dist/*|*/node_modules/*) continue ;; esac   # 빌드 산출물 제외
    cp -f "$f" "$DEST/html/$(basename "$f")" 2>/dev/null && cnt=$((cnt+1))
  done < <(find "$SESSION_DIR" -name '*.html' -size +2k 2>/dev/null)
  echo "  · HTML $cnt 개"
else
  echo "  ⚠ 세션 디렉터리를 못 찾음 — HTML 은 수동 복사 필요"
fi

echo "✓ 완료 — $(du -sh "$DEST" | cut -f1)"
echo "  목록: find $DEST -type f | sort"
