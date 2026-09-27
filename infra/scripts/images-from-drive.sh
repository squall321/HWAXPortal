#!/usr/bin/env bash
# Pull pre-built .sif images (+ SPA dist) from Google Drive into infra/apptainer/, so start.sh
# skips the Docker-Hub build entirely. Mirror of MXWhitePaper's data-merge-from-drive.sh.
#
# Needs in infra/.env:  HWAX_DRIVE_REMOTE=ApptainerImages:HWAXPortal/images
# After this:  ./infra/scripts/start.sh   (build will "skip — exists")
set -euo pipefail
"$(dirname "$0")/bootstrap-rclone.sh"   # ensure rclone (no-op if present; installs no-sudo otherwise)
. "$(dirname "$0")/_common.sh"

"$RCLONE" version >/dev/null 2>&1 \
  || { echo "✗ rclone unavailable — run ./infra/scripts/bootstrap-rclone.sh"; exit 1; }
REMOTE="${HWAX_DRIVE_REMOTE:-}"
[ -n "$REMOTE" ] \
  || { echo "✗ HWAX_DRIVE_REMOTE not set in infra/.env (e.g. ApptainerImages:HWAXPortal/images)"; exit 1; }
REMOTE="${REMOTE%/}"

# Source = latest/ if it has the images, else the newest images-<TS>/ dir.
SRC="$REMOTE/latest"
if ! "$RCLONE" lsf "$SRC/" 2>/dev/null | grep -q '^portal\.sif$'; then
  NEWEST="$("$RCLONE" lsf --dirs-only "$REMOTE/" 2>/dev/null \
    | sed 's#/$##' | grep -E '^images-' | sort | tail -n 1 || true)"
  [ -n "$NEWEST" ] \
    || { echo "✗ no images on $REMOTE (no latest/ or images-*/). Push from a build host first:"; \
         echo "    ./infra/scripts/images-to-drive.sh"; exit 1; }
  SRC="$REMOTE/$NEWEST"
fi
echo "→ source: $SRC"

# 영구 캐시 — 임시 디렉터리에 받으면 rclone 이 비교할 것이 없어 매번 전량 전송이다(Drive ~2MB/s, SIF 수백 MB). 캐시에 받으면 안 바뀐
# 파일은 전송 0 이고 modtime 이 원격 것으로 보존돼 아래 지문(deploy-all)이 안정된다. docs/update-all-skip-unchanged D-2.
. "$(dirname "$0")/lib/change-detect.sh"
STAGE="${HWAX_DRIVE_CACHE:-$APPT_DIR/.drive-cache}"; mkdir -p "$STAGE"
"$RCLONE" copy --progress "$SRC/" "$STAGE/"

# Verify integrity before staging.
if [ -f "$STAGE/SHA256SUMS" ]; then
  ( cd "$STAGE" && sha256sum -c SHA256SUMS ) \
    || { echo "✗ checksum verification failed — not staging"; exit 1; }
  echo "  ✓ checksums OK"
else
  echo "  ⚠ no SHA256SUMS on remote — skipping integrity check"
fi
[ -f "$STAGE/portal.sif" ] && [ -f "$STAGE/nginx.sif" ] \
  || { echo "✗ portal.sif/nginx.sif missing in $SRC"; exit 1; }

mkdir -p "$APPT_DIR"
# 같은 내용이면 손대지 않는다 — 살아 있는 인스턴스 밑의 SIF 를 덮어쓰면 squashfs 가 깨지고(mxwp 실사고), cp 는 mtime 을 리셋해 지문이 매번 달라진다.
for _f in portal.sif nginx.sif; do
  if hwax_install_if_changed "$STAGE/$_f" "$APPT_DIR/$_f"; then echo "  ✓ staged $_f → $APPT_DIR"; else echo "  · $_f 같음 — 그대로"; fi
done
# SearxNG(일반 웹 검색) SIF — 올리는 쪽(images-to-drive)만 고치고 여기를 빼먹으면
# "SIF 는 Drive 로 간다" 는 안내가 거짓이 된다. 없을 수도 있으므로 있을 때만 옮긴다.
if [ -f "$STAGE/searxng-fixed.sif" ]; then
  if hwax_install_if_changed "$STAGE/searxng-fixed.sif" "$APPT_DIR/searxng-fixed.sif"; then echo "  ✓ staged searxng-fixed.sif → $APPT_DIR"; else echo "  · searxng-fixed.sif 같음 — 그대로"; fi
fi

if [ -f "$STAGE/frontend-dist.tar.gz" ]; then
  # 마지막으로 푼 tar 의 사본과 같으면 다시 풀지 않는다(수천 파일 rewrite 생략) — 다르면 풀고 사본을 갱신
  if [ -f "$APPT_DIR/.frontend-dist.applied.tar.gz" ] && cmp -s "$STAGE/frontend-dist.tar.gz" "$APPT_DIR/.frontend-dist.applied.tar.gz"; then
    echo "  · frontend/dist 같음 — 그대로"
  else
    ( cd "$REPO_ROOT/frontend" && tar -xzf "$STAGE/frontend-dist.tar.gz" ) && cp -p "$STAGE/frontend-dist.tar.gz" "$APPT_DIR/.frontend-dist.applied.tar.gz"
    echo "  ✓ extracted frontend/dist"
  fi
fi

echo
echo "✓ images ready — now run:  ./infra/scripts/start.sh   (build skips, boots from these images)"
