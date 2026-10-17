#!/usr/bin/env bash
# 원격 없는 지식 리포(ExpertAgents · ExpertGrounding)를 git 묶음 + 커밋 안 된 변경 사본으로 Drive 에 올린다 — 매일 크론(10-17 결정 3)
#
#   ./infra/scripts/repo-bundle-to-drive.sh                    # 두 리포
#   ./infra/scripts/repo-bundle-to-drive.sh ExpertGrounding    # 하나만
#
# 왜 작업 사본도 — git 묶음은 커밋만 담는다. 10-17 ExpertGrounding 은 커밋이 8월의 1개뿐이고 그 뒤 작업(cardgen/ · 스크립트 수정)이 전부
# 작업 트리에만 있었다 — 묶음만 올리면 거의 빈 백업이다. 커밋 안 된 수정 · 추적 안 된 파일(.gitignore 존중)을 함께 싣되 비밀 꼴(.env* ·
# *.key · *.pem)과 컨테이너 이미지(*.sif)는 뺀다.
# 놓는 곳 — <포털 Drive 부모>/repo-bundles/<리포>/<리포>-<박스>-<UTC 시각>.tar (최근 HWAX_BUNDLE_RETAIN=5 벌). 바뀐 것이 없으면 올리지 않는다.
# 되살리기 — tar -xf <파일> && git clone <리포>.bundle <리포> && tar -xzf worktree-changes.tar.gz -C <리포>
# 크론(dev): 20 4 * * * cd $HOME/claude/HWAXPortal && ./infra/scripts/repo-bundle-to-drive.sh >> $HOME/.local/state/hwax/repo-bundle.log 2>&1  # hwax-repo-bundle
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$ROOT")"
STATE="${HWAX_BUNDLE_STATE:-$HOME/.local/state/hwax}"
RETAIN="${HWAX_BUNDLE_RETAIN:-5}"
BOX="${HWAX_BOX:-$(hostname -s)}"
RCLONE="$(command -v rclone || echo "$ROOT/infra/bin/rclone")"
[ -x "$RCLONE" ] || { echo "✗ rclone 이 없다"; exit 1; }
REMOTE="$(sed -n 's/^HWAX_DRIVE_REMOTE=//p' "$ROOT/infra/.env" 2>/dev/null | tail -1)"
[ -n "$REMOTE" ] || { echo "✗ infra/.env 에 HWAX_DRIVE_REMOTE 가 없다"; exit 1; }
REMOTE="${REMOTE%/}"; REMOTE="${REMOTE%/images}"
DEST="$REMOTE/repo-bundles"
mkdir -p -m 700 "$STATE"

rc=0
for name in ${*:-ExpertAgents ExpertGrounding}; do
  repo="$PARENT/$name"
  [ -d "$repo/.git" ] || { echo "○ $name: 리포 없음($repo) — 건너뜀"; continue; }
  # 커밋 안 된 수정 + 추적 안 된 파일(.gitignore 존중) — 비밀 꼴과 컨테이너 이미지는 뺀다
  # (grep -v 는 남는 줄이 없으면 1 이다 — 다 커밋한 날 pipefail · set -e 로 말없이 죽지 않게 || true)
  changes="$(git -C "$repo" ls-files -m -o --exclude-standard \
             | { grep -vE '(^|/)\.env[^/]*$|\.(key|pem|sif)$' || true; } \
             | while IFS= read -r f; do if [ -f "$repo/$f" ]; then printf '%s\n' "$f"; fi; done | LC_ALL=C sort -u)"   # 정렬은 로캘과 상관없게 — 크론(C)과 사람 셸의 지문이 갈렸다
  # 바뀐 것이 없으면 올리지 않는다 — 참조(커밋) · 바뀐 파일의 크기 · 시각이 지난번과 같으면
  fp="$( { git -C "$repo" for-each-ref --format='%(objectname) %(refname)'
           [ -z "$changes" ] || (cd "$repo" && printf '%s\n' "$changes" | tr '\n' '\0' | xargs -0 stat -c '%n %s %Y'); } | sha256sum | cut -c1-16)"
  if [ "$(cat "$STATE/repo-bundle-$name.fp" 2>/dev/null)" = "$fp" ]; then
    echo "○ $name: 바뀐 것 없음 — 마지막 묶음 그대로($fp)"; continue
  fi
  stage="$(mktemp -d)"
  ts="$(date -u +%Y%m%d-%H%M%SZ)"
  out="$stage/$name-$BOX-$ts.tar"
  if git -C "$repo" bundle create "$stage/$name.bundle" --all >/dev/null 2>&1 && git -C "$repo" bundle verify "$stage/$name.bundle" >/dev/null 2>&1; then
    n="$(printf '%s' "$changes" | grep -c . || true)"
    if [ "$n" -gt 0 ]; then
      (cd "$repo" && printf '%s\n' "$changes" | tr '\n' '\0' | tar --null -T - -czf "$stage/worktree-changes.tar.gz")
    fi
    { echo "repo=$name box=$BOX at=$ts head=$(git -C "$repo" rev-parse --short HEAD) commits=$(git -C "$repo" rev-list --all --count) changes=$n"
      printf '%s\n' "$changes"; } > "$stage/MANIFEST.txt"
    tar -cf "$out" -C "$stage" "$name.bundle" MANIFEST.txt $( [ "$n" -gt 0 ] && echo worktree-changes.tar.gz )
    if "$RCLONE" copy "$out" "$DEST/$name/"; then
      printf '%s' "$fp" > "$STATE/repo-bundle-$name.fp"
      echo "✓ $name → $DEST/$name/$(basename "$out") ($(du -h "$out" | cut -f1) · 커밋 $(git -C "$repo" rev-list --all --count) · 안 올린 변경 ${n}개)"
      mapfile -t old < <("$RCLONE" lsf --files-only "$DEST/$name/" 2>/dev/null | grep -E "^$name-.*\.tar$" | sort | head -n "-$RETAIN") || true
      for f in "${old[@]:-}"; do [ -n "$f" ] && "$RCLONE" deletefile "$DEST/$name/$f" 2>/dev/null || true; done
    else
      echo "✗ $name: Drive 업로드 실패"; rc=1
    fi
  else
    echo "✗ $name: git bundle 실패"; rc=1
  fi
  rm -rf "$stage"
done
exit "$rc"
